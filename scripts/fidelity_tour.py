#!/usr/bin/env python3
"""Side-by-side comparison of the native world with the live client, map by map (NATIVE-FIDELITY-002).

A tour manifest (JSON) names, per map, a live capture taken under the game lock and the tile the hero stood on:

    {
      "version": 1,
      "game_root": "/path/to/MuTheMatrix",           # optional; else $MU_GAME_ROOT
      "objects_dir": "/local/plain",                  # decoded EncTerrain<n>.plain files (live_objects_to_plain.py)
      "out_dir": "/local/renders/fidelity2/tour",
      "width": 1722, "height": 1048,                  # client area of the live window and of the native render
      "title_bar": 28,                                # rows above the client area in the live window shot
      "masks": [[x0, y0, x1, y1], ...],               # client-area rectangles left out of the image stats (HUD)
      "native_args": ["--no-audio"],                  # extra mu-world options (optional)
      "maps": [
        {"name": "01-dungeon", "world": 1, "tile": [108, 247],     # tile: optional, else from the snapshots
         "live_png": "live/01-dungeon.png",                         # winshot.swift window shot
         "live_obj": "live/01-dungeon-obj.bin",                     # live-readers/objread snapshot
         "live_globals": "live/01-dungeon-glob.bin",                # objread's scene globals
         "live_light": "live/01-dungeon-light.bin",                 # live-readers/lightread snapshot
         "native_png": null, "native_dump": null,                   # optional: skip the render, use these
         "note": "Dungeon 1 warp arrival"}
      ]
    }

Relative paths resolve against the manifest's directory. Every live input is optional; the scoreboard reports what it
can. `render` runs `mu-world --headless --backend gl` at the tile with `--objects-dir` and `--fidelity-dump`, which
writes the native OBJECT images and terrain light grids in the readers' own layouts. `compare` writes per map:

    <out>/<name>/side.png   live | native, same client area
    <out>/<name>/diff.png   |live - native| x 4, masks greyed
and <out>/scoreboard.json + scoreboard.md with, per map:

    camera   : live camera position/angle/FOV/far (objread globals) against the native frame report
    image    : masked mean |diff|, share of pixels off by > 24/255, mean colour of each side (colour cast),
               luminance quantiles, a 4 x 4 grid of region diffs (where the difference is)
    objects  : live objects (sector lists) matched to native ones by type and start position: missing, extra,
               position/angle/scale differences, and per field the count of objects whose static OBJECT fields
               (flags, hidden/blend mesh, render mode, light, velocity, alpha target, action, ...) differ
    light    : primary terrain light (the light map pass) over the whole map and frame light (dynamic lights) around
               the hero: mean/max difference and the tiles that differ most

The live files are decoded game data and the renders are screenshots: keep them local, never commit them.
Usage:
    scripts/fidelity_tour.py render MANIFEST [--binary native/build/mu-world] [--only NAME,...]
    scripts/fidelity_tour.py compare MANIFEST [--only NAME,...]
    scripts/fidelity_tour.py run MANIFEST            # render + compare
    scripts/fidelity_tour.py manifest CAPTURE_DIR --out MANIFEST [--objects-dir DIR] [--out-dir DIR] [--png-dir DIR]
"""
import argparse
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OBJECT_BYTES = 0x3d8
CELLS = 256 * 256
# objread scene globals (live-readers/objread.c)
G_CAMERA_ANGLE, G_CAMERA_POSITION, G_FOV, G_FAR, G_WORLD_TIME = 0x0bdc58f0, 0x0bdc5ab4, 0x01cf1634, 0x01cf1630, 0x06fce370
G_HERO = 0x0a39d754          # lightread GLOB: the hero character pointer
CHARACTER_BYTES, CHARACTER_POSITION = 0x3670, 0x33ac   # CharactersClient entry; OBJECT +0x158 at +0x3254
# The camera of the in-world scene sits at hero + this offset with the default zoom (Distance 9.1 x ... in all
# captured worlds: the live globals give it); used to pick the hero among the lightread characters.
DIFF_THRESHOLD = 24

# Static OBJECT fields compared object by object (reconstructed/objects/object_render.h). Time-varying fields
# (frame, alpha, timer, blend texture offsets, visibility) are left out.
FIELDS = [
    ('live', 0x00, 'B'), ('shadow', 0x03, 'B'), ('light_enable', 0x05, 'B'), ('light_full', 0x06, 'B'),
    ('light_dynamic', 0x07, 'B'), ('after_character', 0x0a, 'B'), ('alpha_linear', 0x0c, 'B'),
    ('bone_buffer', 0x0d, 'B'), ('flag_e', 0x0e, 'B'), ('action', 0x2a, 'H'), ('hidden_mesh', 0x68, 'i'),
    ('blend_mesh', 0x74, 'i'), ('render_mode', 0x80, 'i'), ('scale', 0xa0, 'f'), ('blend_light', 0xa8, 'f'),
    ('bone_scale', 0xb8, 'f'), ('velocity', 0xbc, 'f'), ('range', 0xc0, 'f'), ('alpha_target', 0xd8, 'f'),
    ('alpha_rate', 0xe0, 'f'), ('value_e4', 0xe4, 'f'), ('value_e8', 0xe8, 'f'), ('light', 0xec, '3f'),
    ('angle', 0x164, '3f'), ('position', 0x158, '3f'),
]


# ---------------------------------------------------------------- snapshot readers

def read_objects(path):
    """objread MUOBJLV1 (or mu-world --fidelity-dump): (world, count, [(address, sector, bytes)])."""
    data = Path(path).read_bytes()
    if data[:8] != b'MUOBJLV1':
        raise ValueError(f'{path}: not an object snapshot')
    world, _world2, count, n = struct.unpack_from('<iiiI', data, 8)
    out, offset = [], 24
    for _ in range(n):
        address, sector = struct.unpack_from('<II', data, offset)
        out.append((address, sector, data[offset + 8:offset + 8 + OBJECT_BYTES]))
        offset += 8 + OBJECT_BYTES
    return world, count, out


def read_globals(path):
    data = Path(path).read_bytes()
    if data[:8] != b'MUGLBLV1':
        raise ValueError(f'{path}: not a globals snapshot')
    out, offset = {}, 8
    while offset + 8 <= len(data):
        address, size = struct.unpack_from('<II', data, offset)
        out[address] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    return out


def read_light(path):
    """lightread MULITLV1: {'globals': {addr: bytes}, 'characters': [(index, bytes)], 'primary': [...], 'frame': [...]}"""
    data = Path(path).read_bytes()
    if data[:8] != b'MULITLV1':
        raise ValueError(f'{path}: not a light snapshot')
    out, offset = {'globals': {}, 'characters': [], 'primary': None, 'frame': None}, 8
    while offset + 8 <= len(data):
        tag, size = data[offset:offset + 4], struct.unpack_from('<I', data, offset + 4)[0]
        body = data[offset + 8:offset + 8 + size]
        offset += 8 + size
        if tag == b'GLOB':
            p = 0
            while p + 8 <= len(body):
                address, length = struct.unpack_from('<II', body, p)
                out['globals'][address] = body[p + 8:p + 8 + length]
                p += 8 + length
        elif tag == b'CHAR':
            for p in range(0, len(body) - 3, 4 + CHARACTER_BYTES):
                out['characters'].append((struct.unpack_from('<I', body, p)[0], body[p + 4:p + 4 + CHARACTER_BYTES]))
        elif tag == b'LITE':   # lightread: two sections (primary, frame); the native dump: one with both
            grid = 3 * CELLS
            for k in range(len(body) // (4 * grid)):
                values = struct.unpack_from('<%df' % grid, body, 4 * grid * k)
                out['frame' if out['primary'] is not None else 'primary'] = values
    return out


def floats(raw, n):
    return struct.unpack('<%df' % n, raw[:4 * n])


def live_camera(globals_):
    if not globals_:
        return None
    cam = {}
    if G_CAMERA_POSITION in globals_:
        cam['eye'] = floats(globals_[G_CAMERA_POSITION], 3)
    if G_CAMERA_ANGLE in globals_:
        cam['angle'] = floats(globals_[G_CAMERA_ANGLE], 3)
    if G_FOV in globals_:
        cam['fov'] = floats(globals_[G_FOV], 1)[0]
    if G_FAR in globals_:
        cam['far'] = floats(globals_[G_FAR], 1)[0]
    if G_WORLD_TIME in globals_:
        cam['world_time'] = floats(globals_[G_WORLD_TIME], 1)[0]
    return cam


def hero_position(light, camera, offset=(707.1068, -707.1068)):
    """The hero among the lightread characters: the one under the camera's default offset (else entry 0)."""
    chars = [floats(c[CHARACTER_POSITION:CHARACTER_POSITION + 12], 3) for _, c in light['characters']] if light else []
    if not chars:
        return None
    if camera and 'eye' in camera:
        tx, ty = camera['eye'][0] - offset[0], camera['eye'][1] - offset[1]
        return min(chars, key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)
    return chars[0]


# ---------------------------------------------------------------- object comparison

def field_value(obj, offset, fmt):
    if fmt == '3f':
        return struct.unpack_from('<3f', obj, offset)
    return struct.unpack_from('<' + fmt, obj, offset)[0]


def _close(a, b, fmt, tolerance):
    if fmt == '3f':
        return all(_close(x, y, 'f', tolerance) for x, y in zip(a, b))
    if fmt == 'f':
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))
    return a == b


def object_key(obj):
    t = struct.unpack_from('<i', obj, 0x5c)[0]
    sx, sy, sz = struct.unpack_from('<3f', obj, 0x110)
    return (t, round(sx, 1), round(sy, 1), round(sz, 1))


def compare_objects(live, native, hero=None, radius=2000.0, tolerance=1e-4, examples=3):
    """Matches live and native OBJECT images by (type, start position) and compares the static fields.

    `live`/`native`: lists of object byte strings. Returns counts of missing (live only), extra (native only),
    per-field mismatches over the matched objects, the same restricted to objects within `radius` of the hero, and
    the types behind them."""
    def index(objects):
        table = {}
        for o in objects:
            table.setdefault(object_key(o), []).append(o)
        return table
    li, ni = index(live), index(native)
    missing, extra, pairs = [], [], []
    for key, objs in li.items():
        others = ni.get(key, [])
        for k, o in enumerate(objs):
            (pairs.append((o, others[k])) if k < len(others) else missing.append(o))
    for key, objs in ni.items():
        extra.extend(objs[len(li.get(key, [])):])

    def near(o):
        if hero is None:
            return True
        x, y = struct.unpack_from('<2f', o, 0x158)
        return (x - hero[0]) ** 2 + (y - hero[1]) ** 2 <= radius * radius

    fields, fields_near = {}, {}
    for lo, no in pairs:
        for name, offset, fmt in FIELDS:
            a, b = field_value(lo, offset, fmt), field_value(no, offset, fmt)
            if _close(a, b, fmt, tolerance):
                continue
            t = struct.unpack_from('<i', lo, 0x5c)[0]
            for table, ok in ((fields, True), (fields_near, near(lo))):
                if not ok:
                    continue
                e = table.setdefault(name, {'objects': 0, 'types': {}, 'examples': []})
                e['objects'] += 1
                e['types'][t] = e['types'].get(t, 0) + 1
                if len(e['examples']) < examples:
                    e['examples'].append({'type': t, 'live': _plain(a), 'native': _plain(b)})

    def types(objs):
        out = {}
        for o in objs:
            t = struct.unpack_from('<i', o, 0x5c)[0]
            out[t] = out.get(t, 0) + 1
        return dict(sorted(out.items()))

    def tidy(table):
        return {k: {'objects': v['objects'], 'types': dict(sorted(v['types'].items())), 'examples': v['examples']}
                for k, v in sorted(table.items(), key=lambda kv: -kv[1]['objects'])}
    return {
        'live': len(live), 'native': len(native), 'matched': len(pairs),
        'missing': len(missing), 'missing_types': types(missing),
        'missing_near': sum(1 for o in missing if near(o)),
        'extra': len(extra), 'extra_types': types(extra),
        'fields': tidy(fields), 'fields_near': tidy(fields_near),
        'near_matched': sum(1 for lo, _ in pairs if near(lo)),
    }


def _plain(v):
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    if isinstance(v, float):
        return None if math.isnan(v) else round(v, 5)
    return v


# ---------------------------------------------------------------- light grids

def compare_grids(live, native, hero=None, radius=12, top=5):
    """Mean and max |difference| of two 256 x 256 x 3 light grids, over the whole map and within `radius`
    tiles of the hero; the tiles that differ most (x, y, live rgb, native rgb)."""
    if live is None or native is None:
        return None

    def stats(cells):
        total, worst, n, signed = 0.0, [], 0, [0.0, 0.0, 0.0]
        for c in cells:
            a, b = live[3 * c:3 * c + 3], native[3 * c:3 * c + 3]
            d = max(abs(a[k] - b[k]) for k in range(3))
            for k in range(3):
                signed[k] += b[k] - a[k]
            total += d
            n += 1
            worst.append((d, c))
        worst.sort(reverse=True)
        return {
            'cells': n, 'mean_abs': round(total / n, 5) if n else 0.0,
            'mean_native_minus_live': [round(s / n, 5) for s in signed] if n else [0, 0, 0],
            'max_abs': round(worst[0][0], 5) if worst else 0.0,
            'over_0.05': sum(1 for d, _ in worst if d > 0.05),
            'worst': [{'tile': [c % 256, c // 256], 'live': [round(v, 4) for v in live[3 * c:3 * c + 3]],
                       'native': [round(v, 4) for v in native[3 * c:3 * c + 3]]} for d, c in worst[:top] if d > 0],
        }
    out = {'map': stats(range(CELLS))}
    if hero is not None:
        hx, hy = int(hero[0] // 100), int(hero[1] // 100)
        near = [y * 256 + x for y in range(max(0, hy - radius), min(256, hy + radius + 1))
                for x in range(max(0, hx - radius), min(256, hx + radius + 1))]
        out['near_hero'] = stats(near)
    return out


# ---------------------------------------------------------------- images

def client_area(png, width, height, title_bar):
    im = Image.open(png).convert('RGB')
    if im.size != (width, height):
        if im.width == width and im.height >= height + title_bar:
            im = im.crop((0, title_bar, width, title_bar + height))
        else:   # e.g. a Retina capture: scale to the client size after removing the title bar
            scale = im.width / width
            top = int(round(title_bar * scale))
            im = im.crop((0, top, im.width, top + int(round(height * scale)))).resize((width, height), Image.BILINEAR)
    return im


def mask_image(size, masks):
    m = Image.new('L', size, 255)
    d = ImageDraw.Draw(m)
    for x0, y0, x1, y1 in masks:
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=0)
    return m


def luminance_quantiles(im, mask, qs=(0.05, 0.5, 0.95)):
    hist = im.convert('L').histogram(mask)
    total = sum(hist)
    out, acc, k = [], 0, 0
    for q in qs:
        target = q * total
        while k < 255 and acc + hist[k] < target:
            acc += hist[k]
            k += 1
        out.append(k)
    return out


def compare_images(live, native, masks, grid=4):
    if live.size != native.size:
        native = native.resize(live.size, Image.BILINEAR)
    mask = mask_image(live.size, masks)
    diff = ImageChops.difference(live, native)
    gray = diff.convert('L')
    ds = ImageStat.Stat(diff, mask)
    off = gray.point(lambda v: 255 if v > DIFF_THRESHOLD else 0)
    off_share = ImageStat.Stat(off, mask).mean[0] / 255.0
    ls, ns = ImageStat.Stat(live, mask), ImageStat.Stat(native, mask)
    regions = []
    w, h = live.size
    for j in range(grid):
        row = []
        for i in range(grid):
            box = (i * w // grid, j * h // grid, (i + 1) * w // grid, (j + 1) * h // grid)
            m = mask.crop(box)
            if not m.getbbox():
                row.append(None)
                continue
            row.append(round(sum(ImageStat.Stat(diff.crop(box), m).mean) / 3, 2))
        regions.append(row)
    return {
        'mean_abs_diff': round(sum(ds.mean) / 3, 3),
        'mean_abs_diff_rgb': [round(v, 3) for v in ds.mean],
        'share_off': round(off_share, 4),
        'live_mean_rgb': [round(v, 2) for v in ls.mean], 'native_mean_rgb': [round(v, 2) for v in ns.mean],
        'colour_cast_native_minus_live': [round(n - l, 2) for n, l in zip(ns.mean, ls.mean)],
        'live_luma_q05_50_95': luminance_quantiles(live, mask), 'native_luma_q05_50_95': luminance_quantiles(native, mask),
        'regions': regions,
    }, diff, mask


def write_visuals(out, live, native, diff, mask):
    side = Image.new('RGB', (live.width * 2 + 8, live.height), (255, 255, 255))
    side.paste(live, (0, 0))
    side.paste(native.resize(live.size), (live.width + 8, 0))
    side.save(out / 'side.png')
    amp = diff.point(lambda v: min(255, v * 4))
    grey = Image.new('RGB', live.size, (64, 64, 64))
    Image.composite(amp, grey, mask).save(out / 'diff.png')


# ---------------------------------------------------------------- manifest, render, compare

def load_manifest(path):
    path = Path(path)
    m = json.loads(path.read_text())
    if m.get('version') != 1:
        raise ValueError('manifest version must be 1')
    base = path.parent

    def resolve(v):
        return str((base / v).resolve()) if v and not os.path.isabs(v) else v
    for key in ('objects_dir', 'out_dir', 'game_root'):
        if m.get(key):
            m[key] = resolve(m[key])
    m.setdefault('width', 1722)
    m.setdefault('height', 1048)
    m.setdefault('title_bar', 28)
    m.setdefault('masks', [])
    m.setdefault('native_args', [])
    m.setdefault('frames', 25)
    if not m.get('out_dir'):
        raise ValueError('manifest needs out_dir')
    for e in m.get('maps', []):
        if 'name' not in e or 'world' not in e:
            raise ValueError('every map needs name and world')
        for key in ('live_png', 'live_obj', 'live_globals', 'live_light', 'native_png', 'native_dump'):
            e[key] = resolve(e.get(key))
    return m


def selected(m, only):
    names = set(only.split(',')) if only else None
    return [e for e in m['maps'] if not names or e['name'] in names]


def map_tile(e):
    if e.get('tile'):
        return tuple(e['tile'])
    camera = live_camera(read_globals(e['live_globals'])) if e.get('live_globals') and Path(e['live_globals']).exists() else None
    light = read_light(e['live_light']) if e.get('live_light') and Path(e['live_light']).exists() else None
    hero = hero_position(light, camera)
    if hero is None:
        raise ValueError(f"{e['name']}: no tile and no hero in the snapshots")
    return int(hero[0] // 100), int(hero[1] // 100)


def render(m, binary, only=None):
    root = m.get('game_root') or os.environ.get('MU_GAME_ROOT')
    if not root:
        raise SystemExit('game_root or MU_GAME_ROOT needed')
    results = []
    for e in selected(m, only):
        out = Path(m['out_dir']) / e['name']
        frames = out / 'frames'
        frames.mkdir(parents=True, exist_ok=True)
        tx, ty = map_tile(e)
        cmd = [binary, '--game-root', root, '--world', str(e['world']), '--tile', f'{tx},{ty}', '--headless',
               '--backend', m.get('backend', 'gl'), '--frames', str(m['frames']), '--every', str(m['frames'] - 1),
               '--width', str(m['width']), '--height', str(m['height']), '--out-dir', str(frames),
               '--fidelity-dump', str(out / 'native')] + list(m['native_args']) + list(e.get('native_args', []))
        if m.get('objects_dir'):
            cmd += ['--objects-dir', m['objects_dir']]
        run = subprocess.run(cmd, capture_output=True, text=True)
        (out / 'native.jsonl').write_text(run.stdout)
        (out / 'native.log').write_text(run.stderr)
        results.append((e['name'], run.returncode))
        print(json.dumps({'render': e['name'], 'tile': [tx, ty], 'exit': run.returncode}))
    return results


def native_report(out):
    path = out / 'native.jsonl'
    frames, summary = [], {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if 'frame' in j and 'eye' in j:
                frames.append(j)
            elif 'objects' in j and 'objects_drawn' in j:
                summary['objects'] = j
            elif j.get('env') is True:
                summary['env'] = j
            elif j.get('particles') is True:
                summary['particles'] = j
    return (frames[-1] if frames else None), summary


def compare_camera(live, frame):
    if not live or not frame:
        return None
    out = {'live': {k: _plain(tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in live.items()},
           'native': {'eye': frame.get('eye'), 'pitch': frame.get('pitch'), 'fov': frame.get('fov'),
                      'far': frame.get('far')}}
    if 'eye' in live and frame.get('eye'):
        out['eye_distance'] = round(math.dist(live['eye'], frame['eye']), 3)
    if 'angle' in live and frame.get('pitch') is not None:
        out['pitch_difference'] = round(frame['pitch'] - live['angle'][0], 4)
    if 'fov' in live and frame.get('fov') is not None:
        out['fov_difference'] = round(frame['fov'] - live['fov'], 4)
    if 'far' in live and frame.get('far') is not None:
        out['far_difference'] = round(frame['far'] - live['far'], 3)
    return out


def compare_map(m, e):
    out = Path(m['out_dir']) / e['name']
    out.mkdir(parents=True, exist_ok=True)
    result = {'name': e['name'], 'world': e['world'], 'note': e.get('note', '')}
    frame, summary = native_report(out)
    globals_ = read_globals(e['live_globals']) if e.get('live_globals') and Path(e['live_globals']).exists() else None
    camera = live_camera(globals_)
    light = read_light(e['live_light']) if e.get('live_light') and Path(e['live_light']).exists() else None
    hero = hero_position(light, camera)
    result['hero'] = _plain(tuple(hero)) if hero else None
    result['tile'] = list(e['tile']) if e.get('tile') else ([int(hero[0] // 100), int(hero[1] // 100)] if hero else None)
    result['camera'] = compare_camera(camera, frame)
    if summary.get('objects'):
        o = summary['objects']
        result['native_objects'] = {k: o.get(k) for k in ('objects', 'object_models_missing', 'objects_drawn',
                                                          'object_lights', 'object_particles', 'objects_animated')}
    if summary.get('env'):
        result['native_env'] = {k: summary['env'].get(k) for k in ('max_boids', 'max_fishs', 'max_leaves', 'leaf_bitmap')}

    native_png = e.get('native_png')
    if not native_png:
        pngs = sorted((out / 'frames').glob('frame-*.png')) if (out / 'frames').exists() else []
        native_png = str(pngs[-1]) if pngs else None
    if e.get('live_png') and native_png and Path(e['live_png']).exists():
        live_im = client_area(e['live_png'], m['width'], m['height'], m['title_bar'])
        native_im = Image.open(native_png).convert('RGB')
        result['image'], diff, mask = compare_images(live_im, native_im, m['masks'])
        write_visuals(out, live_im, native_im.resize(live_im.size), diff, mask)

    dump = e.get('native_dump') or str(out / 'native')
    if e.get('live_obj') and Path(e['live_obj']).exists() and Path(dump + '-obj.bin').exists():
        lw, lcount, lobjs = read_objects(e['live_obj'])
        nw, ncount, nobjs = read_objects(dump + '-obj.bin')
        result['objects'] = compare_objects([o for _, _, o in lobjs], [o for _, _, o in nobjs], hero)
        result['objects'].update({'live_world': lw, 'native_world': nw, 'live_file_count': lcount,
                                  'native_file_count': ncount})
    if light and Path(dump + '-light.bin').exists():
        nl = read_light(dump + '-light.bin')
        result['light'] = {'primary': compare_grids(light['primary'], nl['primary'], hero),
                           'frame': compare_grids(light['frame'], nl['frame'], hero)}
    (out / 'score.json').write_text(json.dumps(result, indent=1))
    return result


def markdown(results):
    lines = ['# World fidelity tour', '',
             '| Map | World | Tile | Eye Δ | Mean \\|Δ\\| | Off >24 | Cast (native−live) | Objects live/native/missing/extra | '
             'Field mismatches near hero | Primary light Δ (near) | Frame light Δ (near) |',
             '|---|---:|---|---:|---:|---:|---|---|---|---:|---:|']
    for r in results:
        img = r.get('image') or {}
        obj = r.get('objects') or {}
        cam = r.get('camera') or {}
        li = r.get('light') or {}

        def g(kind):
            v = (li.get(kind) or {}).get('near_hero') or {}
            return f"{v.get('mean_abs', '')}" if v else ''
        fields = ', '.join(f"{k} {v['objects']}" for k, v in list((obj.get('fields_near') or {}).items())[:4])
        lines.append(
            f"| {r['name']} | {r['world']} | {','.join(map(str, r.get('tile') or []))} | {cam.get('eye_distance', '')} | "
            f"{img.get('mean_abs_diff', '')} | {img.get('share_off', '')} | {img.get('colour_cast_native_minus_live', '')} | "
            f"{obj.get('live', '')}/{obj.get('native', '')}/{obj.get('missing', '')}/{obj.get('extra', '')} | {fields} | "
            f"{g('primary')} | {g('frame')} |")
    lines.append('')
    for r in results:
        obj = r.get('objects') or {}
        if obj.get('missing_types') or obj.get('fields_near'):
            lines.append(f"## {r['name']}")
            if obj.get('missing_types'):
                lines.append(f"- live objects with no native counterpart, by type: {obj['missing_types']}")
            for k, v in (obj.get('fields_near') or {}).items():
                lines.append(f"- `{k}`: {v['objects']} objects near the hero, types {v['types']}, e.g. {v['examples'][:2]}")
            lines.append('')
    return '\n'.join(lines) + '\n'


def compare(m, only=None):
    results = [compare_map(m, e) for e in selected(m, only)]
    out = Path(m['out_dir'])
    out.mkdir(parents=True, exist_ok=True)
    if not only:
        (out / 'scoreboard.json').write_text(json.dumps(results, indent=1))
        (out / 'scoreboard.md').write_text(markdown(results))
    for r in results:
        img, obj = r.get('image') or {}, r.get('objects') or {}
        print(json.dumps({'map': r['name'], 'mean_abs_diff': img.get('mean_abs_diff'), 'share_off': img.get('share_off'),
                          'missing': obj.get('missing'), 'extra': obj.get('extra'),
                          'fields_near': {k: v['objects'] for k, v in (obj.get('fields_near') or {}).items()}}))
    return results


def build_manifest(capture_dir, objects_dir=None, out_dir=None, png_dir=None):
    """A manifest from a capture directory holding NAME-obj.bin, NAME-glob.bin, NAME-light.bin (and NAME.png, here
    or in png_dir), where NAME starts with digits (e.g. 01-dungeon); the world comes from the object snapshot."""
    capture_dir = Path(capture_dir)
    png_dir = Path(png_dir) if png_dir else capture_dir
    maps = []
    for obj in sorted(capture_dir.glob('*-obj.bin')):
        name = obj.name[:-len('-obj.bin')]
        if not name[:2].isdigit():
            continue
        entry = {'name': name, 'world': read_objects(obj)[0], 'live_obj': str(obj)}
        for key, path in (('live_png', png_dir / f'{name}.png'), ('live_globals', capture_dir / f'{name}-glob.bin'),
                          ('live_light', capture_dir / f'{name}-light.bin')):
            if path.exists():
                entry[key] = str(path)
        maps.append(entry)
    return {'version': 1, 'objects_dir': objects_dir, 'out_dir': out_dir or str(capture_dir / 'tour'),
            'width': 1722, 'height': 1048, 'title_bar': 28, 'masks': DEFAULT_MASKS_1722x1048,
            'native_args': ['--no-audio'], 'maps': maps}


# HUD of the live client at a 1722 x 1048 client area (the GFx base movie): top-left status and buttons, the
# quest tracker and menu button top right, the chat box, the bottom bar; and the hero with its wings and pet
# (other players cannot be masked generically and count as difference).
DEFAULT_MASKS_1722x1048 = [[0, 0, 360, 200], [1240, 0, 1722, 420], [0, 720, 430, 900], [420, 900, 1300, 1048],
                           [700, 160, 1060, 560]]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('render', 'compare', 'run'):
        s = sub.add_parser(name)
        s.add_argument('manifest')
        s.add_argument('--only')
        s.add_argument('--binary', default=str(ROOT / 'native/build/mu-world'))
    s = sub.add_parser('manifest')
    s.add_argument('capture_dir')
    s.add_argument('--out', required=True)
    s.add_argument('--objects-dir')
    s.add_argument('--out-dir')
    s.add_argument('--png-dir')
    a = p.parse_args(argv)
    if a.command == 'manifest':
        Path(a.out).write_text(json.dumps(build_manifest(a.capture_dir, a.objects_dir, a.out_dir, a.png_dir), indent=1))
        return 0
    m = load_manifest(a.manifest)
    if a.command in ('render', 'run'):
        failed = [n for n, rc in render(m, a.binary, a.only) if rc]
        if failed:
            print(json.dumps({'render_failed': failed}), file=sys.stderr)
    if a.command in ('compare', 'run'):
        compare(m, a.only)
    return 0


if __name__ == '__main__':
    sys.exit(main())
