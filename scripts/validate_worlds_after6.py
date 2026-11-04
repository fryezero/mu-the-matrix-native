#!/usr/bin/env python3
"""RENDER-WORLDS-AFTER6 instruction comparisons (docs/research/client-worlds-after6.md).

The action registry's tick handlers 4, 6 and 8 against reconstructed/objects/action_registry.c, run through the
registry tick 0x00ce4b5b exactly as validate_worlds_after5 runs the others (the registry built by its constructor
0x00ce38a8, a case tree of MSVC map nodes, the nested SetAction through std::function):

hover: tick handlers 4 (0x00ce1947) and 6 (0x00ce1e4b). By extra[0]: 0 and 2 test the mouse segment
MousePosition 0x0bdc5984 -> MouseTarget 0x0bdc5990 against the object's OBB +0x31c with 0x018500bf (six
separating axes 0x01850d88); 1, 3 (and 2 of handler 6, with the record's lock) wait for the end of the action.
camera: tick handler 8 (0x00ce23ad). With exactly seven extras the segment CameraPosition 0x0bdc5ab4 -> the hero
([[0x0a39d754] + 0x33ac], x, y, z) is tested against a coarse box (0x018500bf), then against the six faces of
the object's box, turned by 0x0185c113 (sin/cos 0x009681bd/0x009fa223) and placed: FaceNormalize 0x00d01206,
CollisionDetectLineToFace 0x0184f96c with InsideTest 0x018506bc after 0x0184f957. A face hit sets +0xd8 = 0.1,
a miss 1.0.
sprite_visible: 0x01692887 (thiscall on the sprite array 0x0a3da070) against mu_pt_sprites_mark_visible
(reconstructed/particles): over the 1000 records of 0x3d8 bytes, +0xb = 1 where the byte +0 (0x0095f977) is not 0.
It has no frustum test of its own (SPRITE-DRAW-001 named one as left).
prime: 0x0129f4cb (thiscall on a map object), the dt-0 update the attach 0x0183067e runs once per object after its
table entries: over the object's +0x3d0 std::list (MSVC nodes; record +0 effect, +0x10 follow), the node update
0xa75708(0.0, external matrix, object) of every effect (stubbed and recorded), the matrix being 0x0129faee's world
matrix for a following record and the scale (+0xa0) / position (+0x158) matrix otherwise. Native: the matrix of
mu_effect_prime_matrix (native/core/mu_effect_scene.c, its text compiled alone with the two matrices it calls).
live_rows (private, --lang-dir): every handler 8 row of the local mapanim.tsv (world 145) in its world's table,
over camera/hero placements around the object.

Every routine named above runs as client code; stubbed as in validate_worlds_after5 (registry getter, GetModel,
rand). All OBJECT bytes, the tick's return value and the rand sequence are compared. The picking globals
0x0bdc58c8 / 0x0bdc58e4 the client writes are not native state and are not compared.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import tempfile
import actor_machine as am
import validate_object_render as v
import validate_worlds_after5 as a5
import validate_particles as vp
import pins

ROOT = Path(__file__).resolve().parents[1]
VIEW, VIEW_BYTES = 0x0bdc5800, 0x400
MOUSE_START, MOUSE_END, CAMERA = 0x0bdc5984, 0x0bdc5990, 0x0bdc5ab4
NEAREST = 0x0bdc58c8
MARK_VISIBLE, SPRITES, SPRITE_BYTES = 0x01692887, 0x0a3da070, 0x3d8
PRIME, NODE_UPDATE, PRIME_OBJECT, PRIME_LIST = 0x0129f4cb, 0x00a75708, 0x22000000, 0x23000000
OBB = 0x31c
BODIES = {'tick_4': (0x00ce1947, 0x00ce1b61), 'tick_6': (0x00ce1e4b, 0x00ce20c2), 'tick_8': (0x00ce23ad, 0x00ce2ee2),
          'line_face': (0x0184f96c, 0x018500bf), 'segment_box': (0x018500bf, 0x0185038d),
          'axis': (0x01850d88, 0x01851174), 'turn': (0x0185c113, 0x0185c354), 'face_normal': (0x00d01206, 0x00d014c9),
          'mark_visible': (0x01692887, 0x016928cd), 'live': (0x0095f977, 0x0095f986),
          'prime': (0x0129f4cb, 0x0129f671), 'world_matrix': (0x0129faee, 0x0129fbaa)}

FPTR = C.POINTER(C.c_float)


class AnimInputs(C.Structure):
    _fields_ = [('entries', C.POINTER(a5.AnimEntry)), ('count', C.c_int32), ('model', a5.MODEL_FN),
                ('rand_fn', v.RAND_FN), ('context', C.c_void_p), ('hero', C.c_float * 3),
                ('camera', FPTR), ('mouse_start', FPTR), ('mouse_end', FPTR)]


def bind(path):
    lib = a5.bind(path)
    lib.dll.mu_action_tick.argtypes = [C.c_void_p, C.POINTER(AnimInputs), C.POINTER(C.c_int)]
    return lib


def build(root, scene_source=None):
    import subprocess
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    subprocess.run(['make', '-s', '-C', str(root / 'particles')], check=True)
    lib = bind(root / 'objects' / ('libobjects.' + v.SUFFIX))
    lib.particles = vp.load_library(root / 'particles' / ('libclient_particles.' + v.SUFFIX))
    lib.scene = scene_library(root / 'objects', scene_source or ROOT / 'native/core/mu_effect_scene.c')
    return lib


# ---------------------------------------------------------------- the client side

def client(machine, registry, case):
    heap = bytearray(registry.heap)
    table, head, size = a5.tree(case['entries'])
    struct.pack_into('<II', heap, 0x10, head, size)
    model = bytearray(0x40)
    struct.pack_into('<h', model, 0x26, case['count'])
    struct.pack_into('<I', model, 0x30, a5.RECORDS)
    records = am.Region('records', a5.RECORDS, bytearray(b'\xcd' * 0x400), defined=bytearray(0x400))
    for a, (keys, lock) in enumerate(case['records']):
        records.define(a5.RECORDS + 16 * a + 8, struct.pack('<hB', keys, lock))
    hero = bytearray(0x3400)
    struct.pack_into('<3f', hero, a5.HERO_POSITION, *case['hero'])
    view = bytearray(VIEW_BYTES)
    struct.pack_into('<f', view, NEAREST - VIEW, case['nearest'])
    struct.pack_into('<3f', view, MOUSE_START - VIEW, *case['mouse'][0])
    struct.pack_into('<3f', view, MOUSE_END - VIEW, *case['mouse'][1])
    struct.pack_into('<3f', view, CAMERA - VIEW, *case['camera'])
    registry.next = registry.heap_end
    rand = v.MsvcRand(case['seed'])
    stubs = registry.stubs()
    stubs.update({a5.GETTER: lambda m: (a5.REGISTRY, 0), a5.MODEL_MANAGER: lambda m: (a5.MANAGER_COOKIE, 0),
                  a5.GET_MODEL: lambda m: ((a5.MODEL if case['has_model'] and m.argument(0) == case['type'] else 0),
                                           4),
                  a5.RAND: lambda m: (rand(), 0)})
    regions = v.global_regions(0, 6, [
        am.Region('heap', a5.HEAP, heap),
        am.defined_region('object', v.OBJECTS, case['object']),
        am.defined_region('model', a5.MODEL, bytes(model), writable=False),
        records,
        am.defined_region('table', a5.TABLE, table, writable=False),
        am.defined_region('hero-pointer', a5.HERO_POINTER, struct.pack('<I', a5.HERO), writable=False),
        am.defined_region('hero', a5.HERO, bytes(hero), writable=False),
        am.defined_region('view', VIEW, bytes(view)),
        am.defined_region('feature', pins.FEATURE09.base, a5.FEATURE, writable=False),
        am.defined_region('isa', a5.ISA, struct.pack('<I', 0), writable=False),
        am.defined_region('key-factor', a5.KEY_FACTOR, struct.pack('<I', 0)),
        am.defined_region('cookie', a5.COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
        am.defined_region('matherr', a5.MATHERR, struct.pack('<I', 0xbb40e64e), writable=False)])
    r = v.run(machine, a5.TICK, [v.OBJECTS], regions, stubs, ecx=a5.REGISTRY, cleanup=4)
    return r, rand.seed


# ---------------------------------------------------------------- the C side

def native(lib, case):
    entries = (a5.AnimEntry * max(1, len(case['entries'])))()
    keep = []
    for i, e in enumerate(case['entries']):
        extra = (C.c_int32 * max(1, len(e['extra'])))(*e['extra'])
        keep.append(extra)
        entries[i] = a5.AnimEntry(e['type'], e['action'], e['speed'], e['handler'], e['param'], len(e['extra']),
                                  C.cast(extra, C.POINTER(C.c_int32)))
    rand = v.MsvcRand(case['seed'])

    def model(ctx, kind, action, count, keys, lock):
        if not case['has_model'] or kind != case['type']:
            return 0
        count[0] = case['count']
        if 0 <= action < len(case['records']):
            keys[0], lock[0] = case['records'][action]
        return 1
    model_fn, rand_fn = a5.MODEL_FN(model), v.RAND_FN(lambda c: rand())
    camera = (C.c_float * 3)(*case['camera'])
    start, end = (C.c_float * 3)(*case['mouse'][0]), (C.c_float * 3)(*case['mouse'][1])
    inputs = AnimInputs(C.cast(entries, C.POINTER(a5.AnimEntry)), len(case['entries']), model_fn, rand_fn, None,
                        (C.c_float * 3)(*case['hero']), C.cast(camera, FPTR), C.cast(start, FPTR), C.cast(end, FPTR))
    obj = C.create_string_buffer(case['object'], v.OBJ_SIZE)
    found = C.c_int(0)
    status = lib.dll.mu_action_tick(obj, C.byref(inputs), C.byref(found))
    return status, found.value, obj.raw, rand.seed


# ---------------------------------------------------------------- geometry

f32 = v.f32


def rotation(g):
    """A random orthonormal frame (rows)."""
    yaw, pitch, roll = (g.uniform(0, 2 * math.pi) for _ in range(3))
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), \
        math.sin(roll)
    return [[cp * cy, cp * sy, -sp], [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, sr * cp],
            [cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp]]


def obb(g, centre):
    """StartPos and three axes (12 floats) around centre; sometimes degenerate or axis-aligned."""
    if g.random() < 0.3:
        axes = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    else:
        axes = rotation(g)
    sizes = [g.choice([g.uniform(20, 400), 100.0, 0.0 if g.random() < 0.05 else 50.0]) for _ in range(3)]
    axes = [[a * s for a in axis] for axis, s in zip(axes, sizes)]
    start = [centre[k] - 0.5 * (axes[0][k] + axes[1][k] + axes[2][k]) for k in range(3)]
    return [f32(x) for x in start + axes[0] + axes[1] + axes[2]]


def through(g, box, inside=True):
    """A segment through a point of the box (or just outside it), from far away."""
    s, x, y, z = box[0:3], box[3:6], box[6:9], box[9:12]
    u = [g.choice([g.random(), 0.0, 1.0, 0.5]) if inside else g.choice([-0.05, 1.05, g.uniform(-1, 2)])
         for _ in range(3)]
    p = [s[k] + u[0] * x[k] + u[1] * y[k] + u[2] * z[k] for k in range(3)]
    d = [g.uniform(-1, 1), g.uniform(-1, 1), g.uniform(0.2, 1)]
    n = math.sqrt(sum(c * c for c in d))
    a, b = g.uniform(300, 3000), g.choice([g.uniform(-200, 3000), 0.0, -50.0])
    return [f32(p[k] + d[k] / n * a) for k in range(3)], [f32(p[k] - d[k] / n * b) for k in range(3)]


def segment(g, box):
    kind = g.random()
    if kind < 0.55:
        return through(g, box)
    if kind < 0.85:
        return through(g, box, inside=False)
    p = [f32(g.uniform(-500, 26000)) for _ in range(3)]
    if kind < 0.9:
        return p, list(p)   # a point
    q = [f32(g.uniform(-500, 26000)) for _ in range(3)]
    if kind < 0.93:
        q[g.randrange(3)] = f32(math.nan)
    return p, q


def angles(g):
    z = g.choice([0.0, 90.0, 180.0, 270.0, 45.0, g.uniform(0, 360), g.uniform(-720, 720)])
    if g.random() < 0.7:
        return [0.0, 0.0, f32(z)]
    return [f32(g.uniform(-90, 90)), f32(g.uniform(-90, 90)), f32(z)]


def camera_extras(g):
    n = g.choice([7] * 10 + [0, 6, 8])
    out = [g.choice([g.randrange(30, 900), 100, 150, 250]) for _ in range(3)]
    out += [g.choice([0, 0, 0, g.randrange(-120, 120)]) for _ in range(3)]
    out += [g.choice([7, 5, 10])]
    out += [g.randrange(0, 5) for _ in range(max(0, n - 7))]
    return out[:n]


def in_box(g, position, extra, scale, angle_z):
    """A point inside the object's turned box (turned about z only; the case keeps x, y turns at 0 for these)."""
    hx, hy, hz = extra[0] * scale * 0.5, extra[1] * scale * 0.5, extra[2] * scale
    local = [g.uniform(-0.95, 0.95) * hx + extra[3] * scale, g.uniform(-0.95, 0.95) * hy + extra[4] * scale,
             g.uniform(0.05, 0.95) * hz + extra[5] * scale]
    c, s = math.cos(math.radians(angle_z)), math.sin(math.radians(angle_z))
    return [position[0] + c * local[0] - s * local[1], position[1] + s * local[0] + c * local[1],
            position[2] + local[2]]


def far(g, point):
    b = g.uniform(0, 2 * math.pi)
    r = g.uniform(300, 2500)
    return [point[0] + r * math.cos(b), point[1] + r * math.sin(b), point[2] + g.uniform(-300, 1500)]


def camera_scene(g, position, extra, scale, angle_z=None):
    """Hero near the object and the camera behind/above it, aimed so the segment often crosses the box; with the
    turn about z only, sometimes the hero or the camera inside the box (the segment then crosses one face)."""
    size = max(extra[:3]) if len(extra) >= 3 else 300
    if angle_z is not None and len(extra) >= 6 and g.random() < 0.35:
        inner = in_box(g, position, extra, scale, angle_z)
        hero, camera = (inner, far(g, inner)) if g.random() < 0.7 else (far(g, inner), inner)
        return [f32(c) for c in hero], [f32(c) for c in camera]
    hero_d = g.choice([g.uniform(0, 2.0 * size), g.uniform(0, 600), size * 0.5])
    a = g.uniform(0, 2 * math.pi)
    hero = [position[0] + hero_d * math.cos(a), position[1] + hero_d * math.sin(a),
            position[2] + g.choice([0.0, g.uniform(-50, 300)])]
    kind = g.random()
    if kind < 0.6:   # the camera beyond the object, seen from the hero
        aim = [position[0] + g.uniform(-0.6, 0.6) * size * scale, position[1] + g.uniform(-0.6, 0.6) * size * scale,
               position[2] + g.uniform(0, 1.1) * size * scale]
        d = [aim[k] - hero[k] for k in range(3)]
        n = math.sqrt(sum(c * c for c in d)) or 1.0
        k = g.uniform(1.0, 4.0) * max(n, 200.0)
        camera = [hero[i] + d[i] / n * k for i in range(3)]
    elif kind < 0.9:   # the client's usual camera: about 1,000 back and 1,000 up
        b = g.uniform(0, 2 * math.pi)
        camera = [hero[0] + 1000 * math.cos(b), hero[1] + 1000 * math.sin(b), hero[2] + g.uniform(600, 1300)]
    else:
        camera = [g.uniform(0, 25600), g.uniform(0, 25600), g.uniform(-100, 2000)]
    if g.random() < 0.02:
        camera[g.randrange(3)] = math.nan
    return [f32(c) for c in hero], [f32(c) for c in camera]


# ---------------------------------------------------------------- cases

def entry_for(g, kind, action, handler, count):
    e = a5.entry(g, kind, action, [handler], count)
    if handler in (4, 6):
        e['extra'] = [g.choice([0, 1, 2, 3, 0, 2, 0, 2, 4, -1])] + [g.choice(list(range(-1, count + 2)) +
                                                                            list(range(count)) * 3)
                                                                   for _ in range(g.randrange(0, 3))]
    elif handler == 8:
        e['extra'] = camera_extras(g)
    return e


def random_case(g, handlers):
    handler = g.choice(handlers)
    kind = g.choice([13, 14, 17, 50, 107, 158, g.randrange(0, 300)])
    count = g.choice([1, 2, 3, 4, 4, 5, 8])
    records = [(g.choice([1, 2, 10, 20, 32, g.randrange(1, 60)]), g.choice([0, 0, 1])) for _ in range(count)]
    current = g.randrange(0, count)
    entries = [entry_for(g, kind, current, handler, count)]
    for a in range(0, count + 1):
        if a != current and g.random() < 0.9:
            entries.append(a5.entry(g, kind, a, g.choice([[0], [1], [2], [4], [6], [8], [3]]), count))
    for _ in range(g.randrange(0, 3)):
        entries.append(a5.entry(g, g.choice([kind + 1, kind + 1000, g.randrange(0, 300)]), g.randrange(0, 4), [1, 8],
                                count))
    seen, unique = set(), []
    for e in entries:
        if a5.key(e['type'], e['action']) not in seen:
            seen.add(a5.key(e['type'], e['action']))
            unique.append(e)
    own = unique[0]
    keys = records[current][0]
    end = keys - own['speed']
    frame = f32(g.choice([end, end - 1e-3, end + 1e-3, end - 1.0, end - 1.0 + 1e-3, end - 1.0 - 1e-3, 0.0, keys,
                          math.nan, g.uniform(0, max(keys, 1))]))
    obj = a5.case_object(g, kind, current, frame)
    struct.pack_into('<ii', obj, 0x30, g.randrange(-2, 4), g.choice([0, 0, 1, 2, -1]))
    position = [f32(g.uniform(0, 25600)), f32(g.uniform(0, 25600)), f32(g.choice([0.0, g.uniform(-100, 600)]))]
    v.put_f(obj, 0x158, *position)
    turn = angles(g)
    v.put_f(obj, 0x164, *turn)
    scale = f32(g.choice([1.0, 1.0, 0.8, 1.2, g.uniform(0.3, 2.5)]))
    v.put_f(obj, 0xa0, scale)
    v.put_f(obj, 0xd8, 0.5)   # neither 0.1 nor 1.0: the tally sees which branch wrote it
    box = obb(g, [position[0], position[1], position[2] + g.uniform(0, 300)])
    v.put_f(obj, OBB, *box)
    mouse = segment(g, box)
    if own['handler'] == 8:
        hero, camera = camera_scene(g, position, own['extra'], scale, turn[2] if turn[:2] == [0.0, 0.0] else None)
    else:
        hero = [f32(position[0] + g.uniform(-900, 900)), f32(position[1] + g.uniform(-900, 900)), 0.0]
        camera = [f32(g.uniform(0, 25600)), f32(g.uniform(0, 25600)), f32(g.uniform(0, 1500))]
    return {'type': kind, 'count': count, 'records': records, 'entries': unique, 'has_model': g.random() < 0.97,
            'object': bytes(obj), 'hero': hero, 'camera': camera, 'mouse': mouse,
            'nearest': f32(g.choice([0.0, 9999999.0, 123.0])), 'seed': g.getrandbits(32)}


def compare(machine, registry, lib, case, tally, label):
    r, client_seed = client(machine, registry, case)
    stop = v.stopped_reason(r)
    if stop:
        tally.add(False, {'case': label}, stop)
        return
    status, found, obj, seed = native(lib, case)
    cobj = r['regions']['object']
    diff = [hex(k) for k in range(v.OBJ_SIZE) if obj[k] != cobj[k]]
    ok = not diff and seed == client_seed and status != 2 and found == (r['eax'] & 0xff)
    own = case['entries'][0]
    if found:
        tally.count('handler %d' % own['handler'])
        if own['handler'] in (4, 6):
            tally.count('h%d step %s' % (own['handler'], own['extra'][0]))
            tally.count('action changed', int(cobj[0x2a:0x2c] != case['object'][0x2a:0x2c]))
            tally.count('latch changed', int(cobj[0x34:0x38] != case['object'][0x34:0x38]))
        else:
            alpha = struct.unpack_from('<f', cobj, 0xd8)[0]
            tally.count('fade %s' % {0.5: 'no coarse hit', 1.0: 'coarse only'}.get(alpha, 'face hit' if alpha < 0.2
                                                                                  else 'other'))
    tally.add(ok, {'case': label, 'diff': diff[:8], 'status': status, 'found': found, 'eax': r['eax'] & 0xff,
                   'seed': [seed, client_seed]})


def family(machine, registry, lib, g, cases, name):
    tally = v.Tally(name)
    handlers = [4, 6] if name == 'hover' else [8]
    for n in range(cases):
        compare(machine, registry, lib, random_case(g, handlers), tally, n)
    return tally


def live_rows(machine, registry, lib, g, lang_dir, per_row):
    """Every handler 8 row of the local table in its world's table, over camera and hero placements."""
    tally = v.Tally('live_rows')
    rows = a5.read_rows(lang_dir)
    eights = [r for r in rows if r['handler'] in (4, 6, 8)]
    for row in eights:
        world = [dict(r) for r in rows if r['world'] == row['world']]
        count = max([r['action'] for r in world if r['type'] == row['type']] + [0]) + 1
        records = [(g.choice([10, 20, 32, 40]), g.choice([0, 1])) for _ in range(count)]
        for k in range(per_row):
            obj = a5.case_object(g, row['type'], row['action'], f32(g.uniform(0, 10)))
            position = [f32(g.uniform(1000, 24000)), f32(g.uniform(1000, 24000)), f32(g.uniform(0, 400))]
            v.put_f(obj, 0x158, *position)
            angle_z = f32(g.choice([0.0, 90.0, 180.0, 270.0, g.uniform(0, 360)]))
            v.put_f(obj, 0x164, 0.0, 0.0, angle_z)
            scale = f32(g.choice([1.0, 0.8, 1.2, g.uniform(0.6, 1.6)]))
            v.put_f(obj, 0xa0, scale)
            v.put_f(obj, 0xd8, 0.5)
            hero, camera = camera_scene(g, position, row['extra'], scale, angle_z)
            case = {'type': row['type'], 'count': count, 'records': records,
                    'entries': [row] + [r for r in world if r is not row and
                                        (r['type'], r['action']) != (row['type'], row['action'])],
                    'has_model': True, 'object': bytes(obj), 'hero': hero, 'camera': camera,
                    'mouse': ([0.0] * 3, [0.0] * 3), 'nearest': 9999999.0, 'seed': g.getrandbits(32)}
            compare(machine, registry, lib, case, tally, '%d/%d/%d #%d' % (row['world'], row['type'], row['action'],
                                                                          k))
    tally.count('rows', len(eights))
    return tally


# ---------------------------------------------------------------- sprite_visible

def sprite_visible(machine, lib, g, cases):
    tally = v.Tally('sprite_visible')
    for n in range(cases):
        density = g.choice([0.0, 0.01, 0.3, 0.9, 1.0])
        live = [g.choice([1, 1, 1, 2, 0x80, 0xff]) if g.random() < density else 0 for _ in range(1000)]
        visible = [g.choice([0, 1, 0, 7]) for _ in range(1000)]
        data = bytearray(am.poison(SPRITE_BYTES * 1000, 0x27))
        for i in range(1000):
            data[i * SPRITE_BYTES] = live[i]
            data[i * SPRITE_BYTES + 0xb] = visible[i]
        r = v.run(machine, MARK_VISIBLE, [], v.global_regions(0, 6, [am.defined_region('sprites', SPRITES, bytes(data))]),
                  {}, ecx=SPRITES)
        stop = v.stopped_reason(r)
        if stop:
            tally.add(False, {'case': n}, stop)
            continue
        sp = vp.Sprites()
        for i in range(1000):
            sp.records[i].live, sp.records[i].visible = live[i], visible[i]
        lib.particles.mu_pt_sprites_mark_visible(C.byref(sp))
        out = r['regions']['sprites']
        client_visible = [out[i * SPRITE_BYTES + 0xb] for i in range(1000)]
        native_visible = [sp.records[i].visible for i in range(1000)]
        others = bytes(out[k] for k in range(len(out)) if k % SPRITE_BYTES != 0xb) == \
            bytes(data[k] for k in range(len(data)) if k % SPRITE_BYTES != 0xb)
        tally.count('live', sum(1 for x in live if x))
        tally.count('raised', sum(1 for a, b in zip(visible, client_visible) if a != b))
        diff = [i for i in range(1000) if client_visible[i] != native_visible[i]]
        tally.add(not diff and others, {'case': n, 'diff': diff[:8], 'others': others})
    return tally


# ---------------------------------------------------------------- prime

SCENE_FUNCTIONS = ('void mu_effect_object_matrix(', 'void mu_effect_object_world_matrix(', 'void mu_effect_prime_matrix(')


def scene_library(directory, source):
    """The three matrix functions of native/core/mu_effect_scene.c, their text compiled alone."""
    import subprocess
    text = Path(source).read_text()
    bodies = []
    for head in SCENE_FUNCTIONS:
        start = text.index(head)
        bodies.append(text[start:text.index('\n}\n', start) + 3])
    body = '\n'.join(bodies)
    tag = hashlib.sha256(body.encode()).hexdigest()[:12]
    src = Path(directory) / ('prime_' + tag + '.c')
    src.write_text('#include <math.h>\n#include <string.h>\n' + body)
    out = Path(directory) / ('prime_' + tag + '.' + v.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', str(src),
                    '-lm', '-o', str(out)], check=True, capture_output=True)
    lib = C.CDLL(str(out))
    lib.mu_effect_prime_matrix.argtypes = [C.c_float * 16, C.c_int, C.c_float * 3, C.c_float * 3, C.c_float]
    lib.mu_effect_prime_matrix.restype = None
    return lib


def prime_case(g):
    obj = bytearray(am.poison(0x3d8, 0x29))
    angle = [f32(g.choice([0.0, 0.0, 90.0, -45.0, 180.0, g.uniform(-720.0, 720.0)])) for _ in range(3)]
    position = [f32(g.uniform(-30000.0, 30000.0)) for _ in range(3)]
    scale = f32(g.choice([1.0, 0.5, 1.3, g.uniform(0.01, 4.0), 0.0]))
    v.put_f(obj, 0x164, *angle)
    v.put_f(obj, 0x158, *position)
    v.put_f(obj, 0xa0, scale)
    records = [{'effect': 0x24000000 + 0x100 * k, 'follow': g.choice([1, 1, 1, 0, 2, 0xff]),
                'bone': g.choice([0, 0, -1, 3]), 'timed': g.choice([0, 0, 1]), 'scale': f32(g.choice([50.0, 60.0])),
                'lifetime': f32(g.choice([0.0, 100.0]))} for k in range(g.choice([0, 1, 1, 2, 3, 5]))]
    # the list: head node at PRIME_LIST, record nodes after it (next +0, prev +4, value +8)
    nodes = bytearray(am.poison(0x20 * (len(records) + 1), 0x31))
    addr = [PRIME_LIST + 0x20 * i for i in range(len(records) + 1)]
    for i, a in enumerate(addr):
        nxt, prv = addr[(i + 1) % len(addr)], addr[(i - 1) % len(addr)]
        struct.pack_into('<II', nodes, a - PRIME_LIST, nxt, prv)
        if i:
            r = records[i - 1]
            struct.pack_into('<IIfiBBxxf', nodes, a - PRIME_LIST + 8, r['effect'], 0, r['scale'], r['bone'],
                             r['follow'], r['timed'], r['lifetime'])
    struct.pack_into('<II', obj, 0x3d0, PRIME_LIST, len(records))
    return {'object': bytes(obj), 'nodes': bytes(nodes), 'records': records, 'angle': angle, 'position': position,
            'scale': scale}


def prime(machine, scene, g, cases):
    tally = v.Tally('prime')
    for n in range(cases):
        case = prime_case(g)
        calls = []

        def node_update(m):
            matrix = struct.unpack('<16f', bytes(m.uc.mem_read(m.argument(1), 0x40)))
            calls.append((m.uc.reg_read(m.x86.UC_X86_REG_ECX), m.argument(0), matrix, m.argument(2)))
            return 1, 12
        regions = v.global_regions(0, 6, [
            am.defined_region('object', PRIME_OBJECT, case['object']),
            am.defined_region('list', PRIME_LIST, case['nodes'], writable=False),
            am.defined_region('cookie', a5.COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('matherr', a5.MATHERR, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('isa', a5.ISA, struct.pack('<I', 0), writable=False)])
        r = v.run(machine, PRIME, [], regions, {NODE_UPDATE: node_update}, ecx=PRIME_OBJECT)
        stop = v.stopped_reason(r)
        if stop:
            tally.add(False, {'case': n}, stop)
            continue
        mine = []
        for rec in case['records']:
            out = (C.c_float * 16)()
            scene.mu_effect_prime_matrix(out, rec['follow'], (C.c_float * 3)(*case['angle']),
                                         (C.c_float * 3)(*case['position']), case['scale'])
            mine.append((rec['effect'], 0, tuple(out), PRIME_OBJECT))
        same = len(mine) == len(calls) and all(
            a[0] == b[0] and a[1] == b[1] and a[3] == b[3] and
            struct.pack('<16f', *a[2]) == struct.pack('<16f', *b[2]) for a, b in zip(mine, calls))
        unchanged = r['regions']['object'] == case['object']
        tally.count('records', len(calls))
        tally.count('following', sum(1 for rec in case['records'] if rec['follow']))
        tally.add(same and unchanged, {'case': n, 'calls': [(hex(c[0]), c[1], c[2][:4]) for c in calls[:2]],
                                       'mine': [(hex(c[0]), c[1], c[2][:4]) for c in mine[:2]],
                                       'unchanged': unchanged})
    return tally


# ---------------------------------------------------------------- mutants

A = 'objects/action_registry.c'
MUTATIONS = [
    ('axis hi', A, 'return !(lo_segment > hi) && !(lo > hi_segment);', 'return !(lo_segment >= hi) && !(lo > hi_segment);'),
    ('axis lo', A, 'return !(lo_segment > hi) && !(lo > hi_segment);', 'return !(lo_segment > hi);'),
    ('axis sign', A, '        if (e[k] > 0.0f)\n', '        if (e[k] >= 0.0f)\n'),
    ('segment axes', A, 'overlap(a[2], p1, p2, b) && overlap(b->x, p1, p2, b)', 'overlap(b->x, p1, p2, b)'),
    ('cross', A, 'out[1] = a[2] * b[0] - a[0] * b[2];', 'out[1] = a[0] * b[2] - a[2] * b[0];'),
    ('hover box', A, 'memcpy(&b, o + MU_OBJF_OBB, sizeof b);', 'memcpy(&b, o + MU_OBJF_OBB + 4, sizeof b);'),
    ('h4 leave', A, '                if (!h)\n                    mu_action_set(o, back(e), in);',
     '                if (h)\n                    mu_action_set(o, back(e), in);'),
    ('h6 latch', A, '            } else if (h && mu_obj_i32(o, OBJ_LIMIT) == 0) {', '            } else if (h) {'),
    ('h6 reset', A, '            } else {\n                mu_obj_set_i32(o, OBJ_LIMIT, 0);\n            }\n            break;',
     '            }\n            break;'),
    ('h6 lock', A, '            } else if (at_end(o, e, r, 1)) {', '            } else if (at_end(o, e, r, 0)) {'),
    ('h8 size', A, 'if (e->extra_count != 7)', 'if (e->extra_count < 7)'),
    ('h8 coarse max', A, 'larger(larger((float)e->extra[0], (float)e->extra[1]), (float)e->extra[2])',
     'larger((float)e->extra[0], (float)e->extra[1])'),
    ('h8 coarse side', A, 'const float side = 2.0f * coarse.z[2];', 'const float side = coarse.z[2];'),
    ('h8 coarse offset', A, '        coarse.start[k] = (float)e->extra[3 + k] + coarse.start[k];\n', ''),
    ('h8 half', A, 'const float hx = (float)e->extra[0] * scale * 0.5f', 'const float hx = (float)e->extra[0] * scale'),
    ('h8 offset scale', A, 'c[i][k] = (float)e->extra[3 + k] * scale + c[i][k];', 'c[i][k] = (float)e->extra[3 + k] + c[i][k];'),
    ('turn degrees', A, 'const float k = 0.0174532924f;', 'const float k = 0.0174532f;'),
    ('turn order', A, 'out[1] = sc * cb * v[0] + (sc * sb * sa + cc * ca) * v[1]', 'out[1] = sc * cb * v[0] + (sc * sb * sa - cc * ca) * v[1]'),
    ('turn z', A, 'out[2] = -sb * v[0] + cb * sa * v[1] + cb * ca * v[2];', 'out[2] = sb * v[0] + cb * sa * v[1] + cb * ca * v[2];'),
    ('h8 face 2', A, '{0, 4, 6, 3}, {1, 5, 7, 3}', '{0, 4, 6, 2}, {1, 5, 7, 3}'),
    ('h8 normal', A, '{{0, 1, 3}, {4, 5, 6}', '{{0, 3, 1}, {4, 5, 6}'),
    ('h8 alpha', A, 'hit ? 0.100000001f : 1.0f', 'hit ? 0.0f : 1.0f'),
    ('line t', A, 'if (!(t >= 0.0f) || !(9999999.0f >= t))', 'if (!(t > 0.0f) || !(9999999.0f >= t))'),
    ('line range', A, '        ok = within(x[0], origin[0], target[0]) && within(x[1], origin[1], target[1]);',
     '        ok = within(x[0], origin[0], target[0]);'),
    ('line plane', A, 'if (-0.5f >= n[0] || n[0] >= 0.5f)', 'if (n[0] >= 0.5f)'),
    ('inside flip', A, 'if (!(sign > 0.0f) ? 0.0f >= term : term >= 0.0f)', 'if (0.0f >= term)'),
    ('normal zero', A, '    if (length == 0.0)\n        return;\n', ''),
    ('sprite live', 'particles/sprites.c', '        if (s->records[i].live)\n', '        if (s->records[i].live == 1)\n'),
    ('prime follow', 'scene/mu_effect_scene.c', '    if (follow)\n        mu_effect_object_world_matrix',
     '    if (follow == 1)\n        mu_effect_object_world_matrix'),
    ('prime scale', 'scene/mu_effect_scene.c', '    out[0] = out[5] = out[10] = scale;', '    out[0] = out[5] = scale;'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=3000)
    p.add_argument('--per-row', type=int, default=40)
    p.add_argument('--sprite-cases', type=int, default=300)
    p.add_argument('--prime-cases', type=int, default=1000)
    p.add_argument('--only')
    p.add_argument('--lang-dir', help='local lang directory with mapanim.tsv (live_rows)')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    registry = a5.Registry(machine)
    families = ['hover', 'camera', 'sprite_visible', 'prime'] + (['live_rows'] if a.lang_dir else [])
    names = [n for n in families if not a.only or n in a.only.split(',')]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(s), 'end': hex(e), 'sha256': hashlib.sha256(
                  text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()} for k, (s, e) in BODIES.items()}}
    if a.lang_dir:
        report['mapanim_sha256'] = hashlib.sha256((Path(a.lang_dir) / 'mapanim.tsv').read_bytes()).hexdigest()
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random('worlds-after6-' + name)   # noqa: E731

    def run_all(library, only=None):
        out = {}
        for name in only or names:
            if name == 'live_rows':
                out[name] = live_rows(machine, registry, library, seed(name), a.lang_dir, a.per_row)
            elif name == 'sprite_visible':
                out[name] = sprite_visible(machine, library, seed(name), a.sprite_cases)
            elif name == 'prime':
                out[name] = prime(machine, library.scene, seed(name), a.prime_cases)
            else:
                out[name] = family(machine, registry, library, seed(name), a.cases, name)
        return out
    for name, tally in run_all(lib).items():
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:3000], flush=True)
    if a.mutations:
        for label, file, old, new in MUTATIONS:
            with tempfile.TemporaryDirectory(prefix='worlds-after6-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement', 'combat',
                          'environment']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                (root / 'scene').mkdir()
                shutil.copy(ROOT / 'native/core/mu_effect_scene.c', root / 'scene' / 'mu_effect_scene.c')
                path = root / file
                s = path.read_text()
                assert s.count(old) == 1, (label, old)
                path.write_text(s.replace(old, new, 1))
                tallies = run_all(build(root, root / 'scene' / 'mu_effect_scene.c'),
                                  [n for n in names if n != 'live_rows'])
                cases = sum(t.cases for t in tallies.values())
                detected = sum(t.cases - t.equal - t.stopped for t in tallies.values())
                stopped = sum(t.stopped for t in tallies.values())
                item = {'name': label, 'cases': cases, 'detected': detected, 'stopped': stopped}
                report['mutants'].append(item)
                print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 and not x['stopped'] for x in report['mutants'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
