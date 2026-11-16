#!/usr/bin/env python3
"""RENDER-WORLDS-PICK-001 instruction comparisons (docs/research/client-worlds-pick.md).

The map object's box OBJECT +0x31c and the mouse-over tick handlers that read it, against
reconstructed/objects/object_pick.c and action_registry.c.

box: BMD::Transform through its wrapper 0x00966ea5 (-> 0x012b5bde), called as RenderObject's setup calls it at
0x017edc95 / 0x017edd08: Transform(bones, o + 0x128, o + 0x134, o + 0x31c, translate, 0, 0.4, +0xe4, +0xe8) on
a synthetic model of 0..2 meshes whose bones carry the object's turn, scale and position (the pose the setup's
Animation call builds). The whole wrapper and transform run as client code; the box bytes and every other
OBJECT byte are compared with mu_obj_obb_write. Bounds mode 0x0b437bfc is 0 (the client's value: the text only
compares it), other non-2 values, and 2 (the editor branch): there the running vertex bounds are rebuilt by
mu_obj_vertex_bounds_begin/add from the positions the client's transform wrote (their skinning is
validate_skinning's subject; mode 2 uses the static-object call's translate 0, where the stored position is the
bounded one).
segment: 0x018500bf(p1, p2, the box by value) with its six axis tests 0x01850d88, against mu_obj_segment_obb on a box written
by the family above: segments through the box, beside it, and on its boundary (an end exactly on a face, an edge
or a corner, a segment lying in a face plane, a point on the surface; integer-valued boxes keep those exact).
One case in twelve keeps the all-zero box of the object's initialiser 0x0129ef45 (an object not drawn yet): all
six projections are 0 and the client reports every finite segment as over it.
pick: the chain. The client's box write (mode 0), then the registry tick 0x00ce4b5b on the same OBJECT with a
handler 4 (0x00ce1947) or 6 (0x00ce1e4b) row and a mouse segment MousePosition 0x0bdc5984 -> MouseTarget
0x0bdc5990 of the same three classes. Native: mu_obj_obb_write, then mu_action_tick with the segment. All OBJECT
bytes, the tick's return value and the rand sequence are compared.

Stubs: the registry getter, GetModel and rand, as validate_worlds_after5/6. The picking globals the client
writes are not native state.
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
import subprocess
import tempfile
import actor_machine as am
import validate_object_render as v
import validate_worlds_after5 as a5
import validate_worlds_after6 as a6
import pins

ROOT = Path(__file__).resolve().parents[1]
WRAPPER, TRANSFORM, SEGMENT, AXIS = 0x00966ea5, 0x012b5bde, 0x018500bf, 0x01850d88
BOX_MIN, BOX_MAX, OBB = 0x128, 0x134, 0x31c
BONE_SCALE, LIGHT_OVERRIDE = 0x01cf104c, 0x01cf1048
VERTICES, VERTEX_STRIDE = 0x078978a0, 0x2bf20
MODEL, MESHES, RECORDS, BONES, POINTS = 0x47000000, 0x47001000, 0x47002000, 0x47004000, 0x47006000
BODIES = {'wrapper': (0x00966ea5, 0x00966f03), 'transform': (0x012b5bde, 0x012b678d),
          'box_tail': (0x012b6479, 0x012b678d), 'bounds_begin': (0x012b5da3, 0x012b5e22),
          'bounds_add': (0x012b6164, 0x012b61cc), 'setup_calls': (0x017edc62, 0x017edd0e),
          'segment_box': (0x018500bf, 0x0185038d), 'axis': (0x01850d88, 0x01851174),
          'tick_4': (0x00ce1947, 0x00ce1b61), 'tick_6': (0x00ce1e4b, 0x00ce20c2),
          'object_init_box': (0x0129ef3d, 0x0129ef50)}
f32 = v.f32
FPTR = C.POINTER(C.c_float)


def bind(path):
    lib = a6.bind(path)
    d = lib.dll
    d.mu_obj_obb_write.argtypes = [C.c_void_p, FPTR, C.c_int32, FPTR, FPTR]
    d.mu_obj_obb_write.restype = None
    d.mu_obj_vertex_bounds_begin.argtypes = [FPTR, FPTR]
    d.mu_obj_vertex_bounds_begin.restype = None
    d.mu_obj_vertex_bounds_add.argtypes = [FPTR, FPTR, FPTR]
    d.mu_obj_vertex_bounds_add.restype = None
    d.mu_obj_segment_obb.argtypes = [C.c_void_p, FPTR, FPTR]
    d.mu_obj_segment_obb.restype = C.c_int
    return lib


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    return bind(root / 'objects' / ('libobjects.' + v.SUFFIX))


def vec(values):
    return C.cast((C.c_float * 3)(*values), FPTR)


# ---------------------------------------------------------------- the box write

def turn_matrix(angle, scale, position):
    """Rows of the 3x4 bone matrix the pose builder gives a translated root: AngleMatrix(angle) * scale, with
    the position in the fourth column (binary32 terms)."""
    a, b, c = (math.radians(x) for x in angle)   # x, y, z
    sa, ca, sb, cb, sc, cc = math.sin(a), math.cos(a), math.sin(b), math.cos(b), math.sin(c), math.cos(c)
    rows = [[cb * cc, sa * sb * cc - ca * sc, ca * sb * cc + sa * sc],
            [cb * sc, sa * sb * sc + ca * cc, ca * sb * sc - sa * cc],
            [-sb, sa * cb, ca * cb]]
    return [[f32(x * scale) for x in rows[k]] + [position[k]] for k in range(3)]


def box_case(g, mode=None, exact=False):
    """An OBJECT with a box, a turn, a scale and a position, and a small model posed by them."""
    obj = bytearray(v.poison_object(g))
    if exact:   # integer-valued: every boundary coordinate of the written box is exact in binary32
        position = [float(g.randrange(200, 25400)), float(g.randrange(200, 25400)), float(g.randrange(-100, 600))]
        low = [float(-g.choice([40, 150, 30, g.randrange(1, 300)])), float(-g.choice([40, 150, g.randrange(1, 300)])),
               float(g.choice([0, 0, -10, g.randrange(-50, 50)]))]
        high = [float(g.choice([40, 150, 100, g.randrange(1, 300)])), float(g.choice([40, 150, g.randrange(1, 300)])),
                float(g.choice([80, 160, 500, g.randrange(51, 600)]))]
    else:
        position = [f32(g.uniform(0, 25600)), f32(g.uniform(0, 25600)), f32(g.choice([0.0, g.uniform(-200, 800)]))]
        kind = g.random()
        if kind < 0.35:
            low, high = g.choice([([-40.0, -40.0, 0.0], [40.0, 40.0, 80.0]), ([-150.0, -150.0, 0.0], [150.0, 150.0, 500.0]),
                                  ([-40.0, -40.0, 0.0], [40.0, 40.0, 160.0]), ([-40.0, -40.0, 0.0], [100.0, 100.0, 160.0])])
        else:
            low = [f32(g.uniform(-400, 100)) for _ in range(3)]
            high = [f32(low[k] + g.choice([g.uniform(0, 600), 0.0, -g.uniform(0, 50)])) for k in range(3)]
        if g.random() < 0.03:
            (low if g.random() < 0.5 else high)[g.randrange(3)] = f32(g.choice([math.nan, math.inf, -math.inf, 1e30]))
    angle = [f32(g.choice([0.0, 0.0, g.uniform(-90, 90)])), f32(g.choice([0.0, 0.0, g.uniform(-90, 90)])),
             f32(g.choice([0.0, 90.0, 180.0, 270.0, 45.0, g.uniform(-720, 720)]))]
    scale = f32(g.choice([1.0, 1.0, 0.8, 1.2, 0.23, 14.84, g.uniform(0.2, 3.0)]))
    v.put_f(obj, 0x158, *position)
    v.put_f(obj, 0x164, *angle)
    v.put_f(obj, 0xa0, scale)
    v.put_f(obj, BOX_MIN, *low)
    v.put_f(obj, BOX_MAX, *high)
    if mode is None:
        mode = g.choice([0] * 12 + [2] * 5 + [1, 3, -1, 0x102])
    meshes = []
    for _ in range(g.choice([0, 1, 1, 2])):
        meshes.append([[f32(g.uniform(-300, 300)), f32(g.uniform(-300, 300)), f32(g.uniform(-50, 600))]
                       for _ in range(g.choice([0, 1, 2, 4, 6]))])
    filled = [m for m in meshes if m]
    if mode == 2 and g.random() < 0.2 and filled:   # a NaN position: first or last (a later vertex would hide it)
        g.choice([filled[0][0], filled[-1][-1], filled[-1][-1]])[g.randrange(3)] = f32(math.nan)
    origin = list(position) if g.random() < 0.9 else [f32(g.uniform(-3e4, 3e4)) for _ in range(3)]
    return {'object': bytes(obj), 'position': position, 'angle': angle, 'scale': scale, 'mode': mode,
            'meshes': meshes, 'origin': origin, 'translate': 0 if mode == 2 else g.choice([0, 0, 1]),
            'e4': f32(g.uniform(0, 2)), 'e8': f32(g.uniform(0, 1)), 'model_scale': f32(g.uniform(0.5, 2.0))}


def client_box(machine, case):
    """The wrapper 0x00966ea5 on the case's model: returns the run and the positions the transform stored."""
    model = bytearray(am.poison(0x100, 0x33))
    struct.pack_into('<h', model, 0x24, len(case['meshes']))
    struct.pack_into('<I', model, 0x28, MESHES)
    model[0x50] = 0   # no lighting: the light vectors are validate_skinning's subject
    struct.pack_into('<f', model, 0x74, case['model_scale'])
    struct.pack_into('<3f', model, 0x78, *case['origin'])
    mesh = bytearray(am.poison(0x20 * max(1, len(case['meshes'])), 0x35))
    points = bytearray()
    for i, vertices in enumerate(case['meshes']):
        struct.pack_into('<hh', mesh, 0x20 * i + 4, len(vertices), 0)
        struct.pack_into('<II', mesh, 0x20 * i + 0xc, POINTS + len(points), 0)
        for p in vertices:
            points += struct.pack('<hxx3f', 0, *p)
    bone = b''.join(struct.pack('<4f', *row) for row in turn_matrix(case['angle'], case['scale'], case['position']))
    span = VERTEX_STRIDE * max(0, len(case['meshes']) - 1) + 0x100
    regions = v.global_regions(0, 6, [
        am.defined_region('object', v.OBJECTS, case['object']),
        am.defined_region('model', MODEL, bytes(model)),
        am.defined_region('meshes', MESHES, bytes(mesh), writable=False),
        am.defined_region('points', POINTS, bytes(points) or b'\0' * 16, writable=False),
        am.defined_region('bones', BONES, bone, writable=False),
        am.defined_region('bounds', v.BOUNDS, struct.pack('<i', case['mode']), writable=False),
        am.defined_region('bone-scale', BONE_SCALE, struct.pack('<f', 1.0), writable=False),
        am.undefined_region('vertices', VERTICES, span)])
    arguments = [BONES, v.OBJECTS + BOX_MIN, v.OBJECTS + BOX_MAX, v.OBJECTS + OBB, case['translate'], 0,
                 v.bits(0.4), v.bits(case['e4']), v.bits(case['e8'])]
    r = v.run(machine, WRAPPER, arguments, regions, {}, ecx=MODEL, cleanup=0x24)
    stored = []
    if r['ok']:
        out = r['regions']['vertices']
        for i, vertices in enumerate(case['meshes']):
            stored += [struct.unpack_from('<3f', out, VERTEX_STRIDE * i + 12 * j) for j in range(len(vertices))]
    return r, stored


def native_box(lib, case, stored):
    obj = C.create_string_buffer(case['object'], v.OBJ_SIZE)
    # the running bounds are built in every mode (the write reads them only in mode 2), so a planted mistake in
    # the mode test shows as a difference
    low, high = (C.c_float * 3)(), (C.c_float * 3)()
    lib.dll.mu_obj_vertex_bounds_begin(low, high)
    for p in stored:
        lib.dll.mu_obj_vertex_bounds_add(low, high, vec(p))
    lib.dll.mu_obj_obb_write(obj, vec(case['origin']), case['mode'], low, high)
    return obj.raw[:v.OBJ_SIZE]


def family_box(machine, lib, g, cases):
    tally = v.Tally('box')
    for n in range(cases):
        case = box_case(g)
        r, stored = client_box(machine, case)
        stop = v.stopped_reason(r)
        if stop:
            tally.add(False, {'case': n, 'mode': case['mode']}, stop)
            continue
        mine, theirs = native_box(lib, case, stored), r['regions']['object']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if mine[k] != theirs[k]]
        box = struct.unpack_from('<12f', theirs, OBB)
        tally.count('mode 2 (vertex bounds)' if case['mode'] == 2 else 'mode %s' % ('0' if case['mode'] == 0 else 'other'))
        tally.count('turned or scaled', int(case['angle'] != [0.0, 0.0, 0.0] or case['scale'] != 1.0))
        tally.count('off-diagonal terms all zero', int(all(box[k] == 0.0 for k in (4, 5, 6, 8, 9, 10))))
        if case['mode'] != 2:   # the claim the port rests on: neither turn nor scale enters the box
            low, high = struct.unpack_from('<3f', case['object'], BOX_MIN), struct.unpack_from('<3f', case['object'], BOX_MAX)
            plain = [f32(low[k] + case['origin'][k]) for k in range(3)] + [f32(high[0] - low[0]), 0.0, 0.0, 0.0,
                                                                         f32(high[1] - low[1]), 0.0, 0.0, 0.0,
                                                                         f32(high[2] - low[2])]
            tally.count('axis-aligned from box and origin', int(struct.pack('<12f', *plain) == theirs[OBB:OBB + 48]))
        tally.add(not diff, {'case': n, 'mode': case['mode'], 'diff': diff[:12],
                             'client': box, 'native': struct.unpack_from('<12f', mine, OBB)})
    return tally


# ---------------------------------------------------------------- segments against a written box

def segments(g, box):
    """(class, p1, p2) for a written axis-aligned box (start, X.x, Y.y, Z.z), integer-valued."""
    s, e = box[0:3], [box[3], box[7], box[11]]
    inner = [s[k] + e[k] * g.choice([0.5, 0.25, 0.75]) for k in range(3)]
    kind = g.random()
    axis = g.randrange(3)
    side = g.choice([0.0, 1.0])
    if kind < 0.25:   # through the interior, both ends outside
        d = [g.choice([-1.0, 1.0]) * g.choice([0.0, 1.0, 2.0, 0.5]) for _ in range(3)]
        if d == [0.0, 0.0, 0.0]:
            d[axis] = 1.0
        k = float(g.choice([1024, 2048, 4096]))
        return 'hit', [inner[i] + d[i] * k for i in range(3)], [inner[i] - d[i] * k for i in range(3)]
    if kind < 0.45:   # parallel to an axis, beside the box by a margin
        p = list(inner)
        other = (axis + g.choice([1, 2])) % 3
        p[other] = s[other] + (e[other] + float(g.choice([1, 8, 300])) if side else -float(g.choice([1, 8, 300])))
        q = list(p)
        p[axis], q[axis] = s[axis] - 500.0, s[axis] + e[axis] + 500.0
        return 'miss', p, q
    if kind < 0.6:    # ends exactly on a face plane, coming from outside
        p = list(inner)
        p[axis] = s[axis] + side * e[axis]
        q = list(p)
        q[axis] = p[axis] + (1.0 if side else -1.0) * float(g.choice([1, 64, 2000]))
        return 'boundary face end', q, p
    if kind < 0.72:   # grazes an edge or a corner: parallel to an axis, on the edge line / through a corner
        p = [s[k] + g.choice([0.0, 1.0]) * e[k] for k in range(3)]
        q = list(p)
        if g.random() < 0.5:
            p[axis], q[axis] = s[axis] - 300.0, s[axis] + e[axis] + 300.0   # along an edge line
            return 'boundary edge line', p, q
        out = [(1.0 if p[k] > s[k] else -1.0) for k in range(3)]   # a diagonal touching the corner from outside
        d = [out[0], -out[1], 0.0] if g.random() < 0.5 else [out[0] * 2.0, out[1], -out[2]]
        return 'boundary corner', [p[i] - d[i] * 256.0 for i in range(3)], [p[i] + d[i] * 256.0 for i in range(3)]
    if kind < 0.82:   # lies in a face plane, across the face
        p = list(inner)
        p[axis] = s[axis] + side * e[axis]
        q = list(p)
        other = (axis + 1) % 3
        p[other], q[other] = s[other] - 128.0, s[other] + e[other] + 128.0
        return 'boundary in face plane', p, q
    if kind < 0.9:    # a point: inside, on the surface, or outside by one unit
        p = list(inner)
        where = g.choice(['inside', 'surface', 'outside'])
        if where != 'inside':
            p[axis] = s[axis] + side * e[axis] + (0.0 if where == 'surface' else (1.0 if side else -1.0))
        return 'point ' + where, p, list(p)
    if kind < 0.95:   # one unit short of a face / one unit past it
        p = list(inner)
        gap = g.choice([1.0, -1.0])
        p[axis] = s[axis] + side * e[axis] + (gap if side else -gap)
        q = list(p)
        q[axis] = p[axis] + (1.0 if side else -1.0) * 512.0
        return ('miss' if gap > 0 else 'hit'), q, p
    p = [f32(g.uniform(-500, 26000)) for _ in range(3)]
    q = [f32(g.uniform(-500, 26000)) for _ in range(3)]
    q[g.randrange(3)] = f32(math.nan)
    return 'nan', p, q


def written_box(machine, lib, g, tally, label):
    """A mode-0 box written by the client's transform on an exact case; None when the run stopped. One case in
    twelve keeps the box the object's initialiser 0x0129ef45 leaves (all zeros): an object not drawn yet."""
    case = box_case(g, mode=0, exact=True)
    if g.random() < 1 / 12:
        raw = bytearray(case['object'])
        raw[OBB:OBB + 48] = bytes(48)
        case['unwritten'] = True
        return case, bytes(raw), C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
    r, _ = client_box(machine, case)
    stop = v.stopped_reason(r)
    if stop:
        tally.add(False, {'case': label, 'stage': 'box'}, stop)
        return None
    theirs = bytes(r['regions']['object'])
    obj = C.create_string_buffer(case['object'], v.OBJ_SIZE)
    unused = (C.c_float * 3)()
    lib.dll.mu_obj_obb_write(obj, vec(case['origin']), 0, unused, unused)
    return case, theirs, obj


def family_segment(machine, lib, g, cases):
    tally = v.Tally('segment')
    for n in range(cases):
        got = written_box(machine, lib, g, tally, n)
        if got is None:
            continue
        case, theirs, obj = got
        box = struct.unpack_from('<12f', theirs, OBB)
        kind, p1, p2 = segments(g, box)
        if case.get('unwritten'):
            kind = 'unwritten box' if kind != 'nan' else 'unwritten box, nan'
        p1, p2 = [f32(x) for x in p1], [f32(x) for x in p2]
        regions = v.global_regions(0, 6, [
            am.defined_region('object', v.OBJECTS, theirs, writable=False),
            am.defined_region('segment', POINTS, struct.pack('<6f', *(p1 + p2)), writable=False)])
        r = v.run(machine, SEGMENT, [POINTS, POINTS + 12] + list(struct.unpack_from('<12I', theirs, OBB)), regions, {})
        stop = v.stopped_reason(r)
        if stop:
            tally.add(False, {'case': n, 'kind': kind}, stop)
            continue
        client = r['eax'] & 0xff
        mine = lib.dll.mu_obj_segment_obb(obj, vec(p1), vec(p2))
        tally.count('%s: %s' % (kind, 'over' if client else 'not over'))
        expected = {'hit': 1, 'miss': 0}.get(kind)
        tally.add(mine == client and (expected is None or client == expected),
                  {'case': n, 'kind': kind, 'client': client, 'native': mine, 'box': box, 'p1': p1, 'p2': p2})
    return tally


# ---------------------------------------------------------------- the chain: box write, then the tick

def family_pick(machine, registry, lib, g, cases):
    tally = v.Tally('pick')
    for n in range(cases):
        got = written_box(machine, lib, g, tally, n)
        if got is None:
            continue
        case, theirs, obj = got
        box = struct.unpack_from('<12f', theirs, OBB)
        kind, p1, p2 = segments(g, box)
        if case.get('unwritten'):
            kind = 'unwritten box' if kind != 'nan' else 'unwritten box, nan'
        p1, p2 = [f32(x) for x in p1], [f32(x) for x in p2]
        handler = g.choice([4, 6])
        typ, count = g.choice([13, 14, 50, g.randrange(0, 300)]), g.choice([2, 3, 4])
        records = [(g.choice([2, 10, 20, 32]), g.choice([0, 0, 1])) for _ in range(count)]
        current = g.randrange(0, count)
        own = a6.entry_for(g, typ, current, handler, count)
        own['extra'] = [g.choice([0, 0, 0, 2, 2, 1, 3])] + [g.randrange(0, count) for _ in range(g.choice([1, 1, 2]))]
        entries = [own] + [a5.entry(g, typ, a, [0, 1], count) for a in range(count) if a != current]
        keys = records[current][0]
        frame = f32(g.choice([0.0, g.uniform(0, keys), keys - own['speed'], keys - 1.0 - own['speed']]))

        def stage(raw):
            """The fields the tick reads, set on both sides' OBJECT after their own box write."""
            raw = bytearray(raw)
            v.put_i(raw, 0x5c, typ)
            struct.pack_into('<HH', raw, 0x2a, current, 0)
            v.put_f(raw, 0xd0, frame)
            v.put_f(raw, 0xbc, 0.16)
            struct.pack_into('<ii', raw, 0x30, 0, g_latch)
            return bytes(raw)
        g_latch = g.choice([0, 0, 0, 1, 2, -1])
        tick_case = {'type': typ, 'count': count, 'records': records, 'entries': entries, 'has_model': True,
                     'hero': [case['position'][0], case['position'][1], 0.0], 'camera': [0.0, 0.0, 0.0],
                     'mouse': (p1, p2), 'nearest': 9999999.0, 'seed': g.getrandbits(32)}
        r, client_seed = a6.client(machine, registry, dict(tick_case, object=stage(theirs)))
        stop = v.stopped_reason(r)
        if stop:
            tally.add(False, {'case': n, 'stage': 'tick', 'kind': kind}, stop)
            continue
        status, found, mine, seed = a6.native(lib, dict(tick_case, object=stage(obj.raw[:v.OBJ_SIZE])))
        cobj = r['regions']['object']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if mine[k] != cobj[k]]
        before = stage(theirs)
        tally.count('h%d step %s' % (handler, own['extra'][0]))
        tally.count('%s: %s' % (kind, 'action changed' if cobj[0x2a:0x2c] != before[0x2a:0x2c] else 'action kept'))
        tally.count('latch changed', int(cobj[0x34:0x38] != before[0x34:0x38]))
        tally.add(not diff and seed == client_seed and status != 2 and found == (r['eax'] & 0xff),
                  {'case': n, 'kind': kind, 'handler': handler, 'extra': own['extra'], 'diff': diff[:8],
                   'status': status, 'found': found, 'eax': r['eax'] & 0xff})
    return tally


# ---------------------------------------------------------------- mutants

P, A = 'objects/object_pick.c', 'objects/action_registry.c'
MUTATIONS = [
    ('box origin', P, 'box.start[k] = box.start[k] + body_origin[k];', 'box.start[k] = box.start[k] + 0.0f * body_origin[k];'),
    ('box origin axis', P, 'box.start[k] = box.start[k] + body_origin[k];',
     'box.start[k] = box.start[k] + body_origin[k == 2 ? 2 : 1 - k];'),
    ('box extent sign', P, 'high[1] - low[1]', 'low[1] - high[1]'),
    ('box extent source', P, 'const float extent[3] = {high[0] - low[0],', 'const float extent[3] = {high[0],'),
    ('box z extent', P, '    box.z[2] = extent[2];', '    box.z[2] = extent[1];'),
    ('box off-diagonal', P, '    box.y[0] = 0.0f;', '    box.y[0] = extent[0];'),
    ('box minimum field', P, 'memcpy(low, o + MU_OBJF_BOX_MIN, sizeof low);', 'memcpy(low, o + MU_OBJF_BOX_MAX, sizeof low);'),
    ('box field', P, 'memcpy(o + MU_OBJF_OBB, &box, sizeof box);', 'memcpy(o + MU_OBJF_OBB + 4, &box, sizeof box);'),
    ('mode test', P, '    if (bounds_mode == 2) {', '    if (bounds_mode != 0) {'),
    ('mode 2 source', P, '        memcpy(high, vertex_maximum, sizeof high);',
     '        memcpy(high, vertex_maximum, sizeof high);\n        memcpy(high, o + MU_OBJF_BOX_MAX, sizeof high);'),
    ('bounds begin', P, '        maximum[k] = -999999.0f;', '        maximum[k] = 999999.0f;'),
    ('bounds minimum', P, '        if (minimum[k] > vertex[k])\n', '        if (vertex[k] > minimum[k])\n'),
    ('bounds maximum', P, '        if (vertex[k] > maximum[k])\n', '        if (vertex[k] > maximum[0])\n'),
    ('bounds nan', P, '        if (minimum[k] > vertex[k])\n', '        if (!(minimum[k] <= vertex[k]))\n'),
    ('segment field', A, 'memcpy(&b, o + MU_OBJF_OBB, sizeof b);\n    return segment_box(p1, p2, &b);',
     'memcpy(&b, o + MU_OBJF_OBB + 12, sizeof b);\n    return segment_box(p1, p2, &b);'),
    ('axis hi boundary', A, 'return !(lo_segment > hi) && !(lo > hi_segment);',
     'return !(lo_segment >= hi) && !(lo > hi_segment);'),
    ('axis lo boundary', A, 'return !(lo_segment > hi) && !(lo > hi_segment);',
     'return !(lo_segment > hi) && !(lo >= hi_segment);'),
    ('axis negative extent', A, '        else\n            lo = lo + e[k];', '        else\n            lo = lo - e[k];'),
    ('segment box axes', A, 'overlap(b->x, p1, p2, b) && overlap(b->y, p1, p2, b) && overlap(b->z, p1, p2, b);',
     'overlap(b->x, p1, p2, b) && overlap(b->y, p1, p2, b);'),
    ('hover box', A, 'memcpy(&b, o + MU_OBJF_OBB, sizeof b);\n    return segment_box(in->mouse_start',
     'memcpy(&b, o + MU_OBJF_OBB + 4, sizeof b);\n    return segment_box(in->mouse_start'),
    ('hover ends', A, 'return segment_box(in->mouse_start, in->mouse_end, &b);',
     'return segment_box(in->mouse_start, in->mouse_start, &b);'),
    ('h4 leave', A, '                if (!h)\n                    mu_action_set(o, back(e), in);',
     '                if (h)\n                    mu_action_set(o, back(e), in);'),
    ('h6 latch', A, '            } else if (h && mu_obj_i32(o, OBJ_LIMIT) == 0) {', '            } else if (h) {'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=3000)
    p.add_argument('--only')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--mutant', help='with --mutations: only these comma-separated mutant names')
    p.add_argument('--output')
    a = p.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    registry = a5.Registry(machine)
    names = [n for n in ('box', 'segment', 'pick') if not a.only or n in a.only.split(',')]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(s), 'end': hex(e), 'sha256': hashlib.sha256(
                  text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()} for k, (s, e) in BODIES.items()}}
    # the bounds mode 0x0b437bfc: every reference in the text is a compare (83 3d: cmp m32, imm8), none a store
    needle, at, references = struct.pack('<I', v.BOUNDS), 0, []
    while (at := text.find(needle, at)) >= 0:
        references.append((am.TEXT_BASE + at, text[at - 2:at].hex()))
        at += 1
    report['bounds_mode_references'] = {'count': len(references), 'all_compares': all(op == '833d' for _, op in references),
                                        'addresses': [hex(x) for x, _ in references],
                                        'inside_image_data': pins.DATA.base <= v.BOUNDS < pins.DATA.base + len(data)}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random('worlds-pick-' + name)   # noqa: E731

    def run_all(library, only=None):
        out = {}
        for name in only or names:
            if name == 'box':
                out[name] = family_box(machine, library, seed(name), a.cases)
            elif name == 'segment':
                out[name] = family_segment(machine, library, seed(name), a.cases)
            else:
                out[name] = family_pick(machine, registry, library, seed(name), a.cases)
        return out
    for name, tally in run_all(lib).items():
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:3000], flush=True)
    if a.mutations:
        for label, file, old, new in [m for m in MUTATIONS if not a.mutant or m[0] in a.mutant.split(',')]:
            with tempfile.TemporaryDirectory(prefix='worlds-pick-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / file
                s = path.read_text()
                assert s.count(old) == 1, (label, old)
                path.write_text(s.replace(old, new, 1))
                tallies = run_all(build(root))
                item = {'name': label, 'cases': sum(t.cases for t in tallies.values()),
                        'detected': sum(t.cases - t.equal - t.stopped for t in tallies.values()),
                        'stopped': sum(t.stopped for t in tallies.values())}
                report['mutants'].append(item)
                print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 and not x['stopped'] for x in report['mutants']) and \
        report['bounds_mode_references']['all_compares'] and not report['bounds_mode_references']['inside_image_data']
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
