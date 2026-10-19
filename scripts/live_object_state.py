#!/usr/bin/env python3
"""Compare reconstructed CreateObject (reconstructed/objects mu_obj_create) with objects read from a running client.

NATIVE-OBJECTS-002. Input: snapshots written by mac-play/diagnostics/objread (see
scripts/live_objects_to_plain.py for the format). Each object's loader record is rebuilt from the fields
CreateObject copies (type, start position, angle, scale, flags, light, the two values), mu_obj_create runs
on a copy of the live bytes, and the fields CreateObject writes are compared with the live object.

Fields the running game changes after creation are excluded and listed in the report: the animation
state, bounding boxes (BMD::Transform rewrites them while drawing), and per type the values MoveObject
or RenderObjectVisual drive (Lorencia's blend-mesh flicker and scroll, the light markers it hides).

--velocity-out writes `type velocity` lines for the types whose live animation speed differs from the
reconstructed creation value (Tormenta Island: set outside CreateObject and the world handler; source
not traced). The native drawer reads that sidecar next to the plaintext. Outputs are decoded game
data: keep them local.
"""
import argparse
import collections
import ctypes
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from live_objects_to_plain import read_snapshot  # noqa: E402

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
OBJ = 0x3d8


class Record(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int16), ('pad', ctypes.c_uint8 * 2), ('position', ctypes.c_float * 3),
                ('angle', ctypes.c_float * 3), ('vector', ctypes.c_float * 3), ('scale', ctypes.c_float),
                ('flag_2c', ctypes.c_uint8), ('flag_2d', ctypes.c_uint8), ('flag_2e', ctypes.c_uint8),
                ('hidden', ctypes.c_uint8), ('value_30', ctypes.c_float), ('value_34', ctypes.c_float)]


# (offset, size, label) of the fields CreateObject writes that are compared
FIELDS = [(0x00, 1, 'live'), (0x02, 1, '+2'), (0x05, 1, 'light enable'), (0x06, 1, 'light full'),
          (0x07, 1, 'light dynamic'), (0x0a, 1, 'after character'), (0x0c, 1, 'alpha linear'), (0x0d, 1, 'bone buffer'),
          (0x0e, 1, '+0xe'), (0x14, 4, '+0x14'), (0x18, 4, '+0x18'), (0x1c, 4, '+0x1c'), (0x28, 1, '+0x28'),
          (0x2a, 2, 'action'), (0x46, 1, 'sector'), (0x68, 4, 'hidden mesh'), (0x74, 4, 'blend mesh'),
          (0xa0, 4, 'scale'), (0xa8, 4, 'blend light'), (0xac, 4, 'blend u'), (0xb0, 4, 'blend v'), (0xb4, 4, 'timer'),
          (0xbc, 4, 'velocity'), (0xc0, 4, 'range'), (0xc4, 4, '+0xc4'), (0xd8, 4, 'alpha target'), (0xdc, 4, 'alpha'),
          (0xe4, 4, '+0xe4'), (0xe8, 4, '+0xe8'), (0xec, 12, 'light'), (0xf8, 12, 'direction'), (0x110, 12, 'start'),
          (0x164, 12, 'angle'), (0x170, 12, 'head angle'), (0x368, 4, '+0x368')]
# per world: type -> labels changed by the running game (MoveObject / RenderObjectVisual)
DYNAMIC = {0: {0x34: {'blend light'}, 0x75: {'blend light'}, 0x7a: {'blend light'}, 0x76: {'blend v'},
               0x77: {'blend v'}, 0x69: {'blend v', 'blend light'}, 0x82: {'hidden mesh'}, 0x83: {'hidden mesh'},
               0x84: {'hidden mesh'}, 0x7d: {'alpha target', 'alpha'}, 0x7e: {'alpha target', 'alpha'}},
           # login world (NATIVE-LOGIN-001): CGMLogInScene_Ex's move scroll and pulse, its custom render's +0xa
           0x5e: {0x01: {'blend v'}, 0x0d: {'blend light', 'after character'}, 0x05: {'after character'}},
           # character select (NATIVE-CHARSEL-002): CGMCharacterScene_Ex's scroll and its custom render's +0xa
           0x5d: {0x18: {'blend v', 'after character'}, 0x19: {'blend v', 'after character'},
                  0x1a: {'blend v', 'after character'}, 4: {'after character'}, 7: {'after character'},
                  8: {'after character'}, 0xc: {'after character'}, 0x1f: {'after character'},
                  0x21: {'after character'}, 0x24: {'after character'}, 0x3c: {'after character'},
                  0x3d: {'after character'}, 0x47: {'after character'}}}


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def light_check(lib, objects, grid_path):
    """Body-light copy +0x1e8 of the objects drawn in the snapshot's frame (+0xb set) whose flags select
    the plain case (+6, +7: frame light, unscaled, copy written) against RequestTerrainLight on the primary
    light (exported by `mu-terrain export`, NATIVE-TERRAIN-001) plus the object light. Where no
    AddTerrainLight source reached the tile the frame light equals the primary light and the copy must be
    bit-identical; elsewhere the sources only add light, so every difference must be positive."""
    grid = ctypes.create_string_buffer(Path(grid_path).read_bytes(), 12 * 65536)
    out = (ctypes.c_float * 3)()
    equal, brighter, darker = 0, 0, 0
    for address, sector, raw in objects:
        if not (raw[6] and raw[7] and raw[0x0b]):
            continue
        x, y = struct.unpack_from('<2f', raw, 0x158)
        lib.mu_obj_terrain_light(ctypes.cast(grid, ctypes.c_void_p), 6, 1, x, y, out)
        light = struct.unpack_from('<3f', raw, 0xec)
        expect = [f32(f32(out[k]) + light[k]) for k in range(3)]
        live = struct.unpack_from('<3f', raw, 0x1e8)
        if raw[0x1e8:0x1f4] == struct.pack('<3f', *expect):
            equal += 1
        elif all(live[k] >= expect[k] for k in range(3)):
            brighter += 1
        else:
            darker += 1
    return {'drawn_objects_compared': equal + brighter + darker, 'bit_identical': equal,
            'brighter_by_light_sources': brighter, 'darker': darker}


def compare(lib, path, velocity_out=None, grid=None):
    world, world2, count, objects = read_snapshot(path)
    stats = collections.Counter()
    mismatch = collections.Counter()
    examples = []
    velocity = collections.defaultdict(collections.Counter)
    created_velocity = {}
    tormenta_dynamic = collections.Counter()
    for address, sector, raw in objects:
        f = lambda o, n=1: struct.unpack_from('<%df' % n, raw, o)
        r = Record()
        r.type = struct.unpack_from('<i', raw, 0x5c)[0]
        r.position[:] = f(0x110, 3)
        r.angle[:] = f(0x164, 3)
        r.vector[:] = f(0xec, 3)
        r.scale = f(0xa0)[0]
        r.flag_2c, r.flag_2d, r.flag_2e = raw[5], raw[6], raw[7]
        if world == 0x8d and 0x24 <= r.type <= 0x2a:
            tormenta_dynamic[raw[7]] += 1      # the handler clears +7 for these types
            r.flag_2e = 1
        r.hidden = 0
        r.value_30, r.value_34 = f(0xe4)[0], f(0xe8)[0]
        buf = ctypes.create_string_buffer(raw, OBJ)
        sec = ctypes.c_int32(-1)
        status = lib.mu_obj_create(ctypes.byref(r), world, buf, ctypes.byref(sec), 0, None)
        if status != 0:
            stats[f'status {status}'] += 1
            continue
        c = buf.raw[:OBJ]
        skip = DYNAMIC.get(world, {}).get(r.type, set())
        bad = []
        for offset, size, label in FIELDS:
            if label in skip:
                stats['excluded ' + label] += 1
                continue
            if raw[offset:offset + size] != c[offset:offset + size]:
                if label == 'velocity':
                    velocity[r.type][f(0xbc)[0]] += 1
                    created_velocity[r.type] = struct.unpack_from('<f', c, 0xbc)[0]
                    continue
                bad.append(label)
        if sec.value != sector:
            bad.append('sector index')
        stats['objects'] += 1
        if bad:
            stats['objects with a differing field'] += 1
            for b in bad:
                mismatch[b] += 1
            if len(examples) < 6:
                examples.append({'type': r.type, 'fields': bad})
        else:
            stats['objects equal'] += 1
    uniform = {t: list(v)[0] for t, v in velocity.items() if len(v) == 1}
    out = {'snapshot': str(Path(path).name), 'world': world, 'objects': len(objects), 'stats': dict(stats),
           'mismatched_fields': dict(mismatch), 'examples': examples,
           'velocity_types_differing': len(velocity), 'velocity_uniform_per_type': len(uniform),
           'velocity_objects_differing': sum(sum(v.values()) for v in velocity.values())}
    if world == 0x8d:
        out['tormenta_types_0x24_0x2a_light_dynamic'] = dict(tormenta_dynamic)
    if grid:
        out['body_light_copy'] = light_check(lib, objects, grid)
    if velocity_out and velocity:
        lines = [f'{t} {uniform[t]!r}' for t in sorted(uniform)]
        Path(velocity_out).write_text('\n'.join(lines) + '\n')
        out['velocity_out'] = str(velocity_out)
    return out


def advance(path_a, path_b):
    """Two snapshots of the same session: the animation frame advance of objects visible in both, in
    logic steps (frame delta / velocity; MoveObject ticks only visible objects, once per 40 ms step)."""
    a = {address: raw for address, sector, raw in read_snapshot(path_a)[3]}
    b = {address: raw for address, sector, raw in read_snapshot(path_b)[3]}
    steps = collections.Counter()
    for address, raw in a.items():
        other = b.get(address)
        if other is None or not (raw[0x0b] and other[0x0b]):
            continue
        fa, fb = struct.unpack_from('<f', raw, 0xd0)[0], struct.unpack_from('<f', other, 0xd0)[0]
        v = struct.unpack_from('<f', raw, 0xbc)[0]
        if fa != fb and v > 0 and fb > fa:
            steps[round((fb - fa) / v, 2)] += 1
    out = {'pair': [Path(path_a).name, Path(path_b).name], 'steps_by_object': dict(steps)}
    if read_snapshot(path_a)[0] == 0x5d:
        # CGMCharacterScene_Ex slot 0x30 (NATIVE-CHARSEL-002): blend v -0.02 (type 0x18) / -0.03 (0x19, 0x1a) per
        # step for the objects MoveObjects moved (visible in both snapshots), unchanged for the others
        scroll = collections.Counter()
        for address, raw in a.items():
            other = b.get(address)
            t = struct.unpack_from('<i', raw, 0x5c)[0]
            if other is None or t not in (0x18, 0x19, 0x1a):
                continue
            va, vb = struct.unpack_from('<f', raw, 0xb0)[0], struct.unpack_from('<f', other, 0xb0)[0]
            step = 0.02 if t == 0x18 else 0.03
            scroll[f'type {t:#x} visible {raw[0x0b]}{other[0x0b]} steps {round((va - vb) / step, 2)}'] += 1
        out['charsel_scroll_steps'] = dict(scroll)
        out['after_character_flags'] = dict(collections.Counter(
            f'type {struct.unpack_from("<i", raw, 0x5c)[0]:#x} +0xa {raw[0x0a]} visible {raw[0x0b]}'
            for raw in b.values() if raw[0x0a]))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('snapshots', nargs='+')
    p.add_argument('--library', default=str(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}'))
    p.add_argument('--velocity-out', help='sidecar for the last snapshot (type velocity lines)')
    p.add_argument('--primary-light', action='append', default=[],
                   help='raw 256x256x3 float primary light per snapshot (same order), from mu-terrain export')
    p.add_argument('--pair', nargs=2, metavar=('A', 'B'), help='frame advance between two snapshots')
    p.add_argument('--output')
    args = p.parse_args(argv)
    lib = ctypes.CDLL(args.library)
    lib.mu_obj_terrain_light.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint8, ctypes.c_float,
                                         ctypes.c_float, ctypes.c_void_p]
    lib.mu_obj_create.argtypes = [ctypes.POINTER(Record), ctypes.c_int32, ctypes.c_void_p,
                                  ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_void_p]
    reports = []
    for i, s in enumerate(args.snapshots):
        r = compare(lib, s, args.velocity_out if i == len(args.snapshots) - 1 else None,
                    args.primary_light[i] if i < len(args.primary_light) else None)
        reports.append(r)
        print(json.dumps(r, indent=1))
    if args.pair:
        r = advance(*args.pair)
        reports.append(r)
        print(json.dumps(r, indent=1))
    if args.output:
        Path(args.output).write_text(json.dumps(reports, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
