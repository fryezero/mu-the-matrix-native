#!/usr/bin/env python3
"""RENDER-WORLDS-AFTER4 instruction comparisons (docs/research/client-worlds-after4.md).

draw_first: the render pass's whole draw-first predicate 0x017fcd18 (to 0x017fe909) for every world, run as
original instructions under the strict machine against mu_draw_first. It extends RENDER-WORLDS-Q2's render_first
family (which took only the worlds reaching the default chain with every chain test false) to the predicate's own
world cases and the true branches of its default chain. Stubbed: the manager singleton 0x00ea594b (a manager whose
+0x10 is a handler with the world's class vtable, as in Q2) and the event singleton 0x009a6ef3 (a block whose
+0x78 +4 is the tower state). TestFrustrum2D 0x016ccce7, the vector accessor 0x00cfc922, the live byte 0x0095f977,
the chain's world tests, sqrt 0x00961a07 with the CRT sqrt and the class slots 0x10 run as original code. The camera
position [0x0bdc5ab4] (world 0x49's fade) is a defined region. AL and all OBJECT bytes are compared. The first cases
sweep, for every world 0..0x91 and 0xff, every type the predicate lists (and its neighbours) inside the polygon,
with live bytes 0, 1 and 2; the rest draw worlds, types, ranges, positions, camera, tower state and fade fields.

action_keys: action record +8 (the frame limit Tormenta Island 141's type 0x2c reads through model +0x30) against
the native BMD key count. The model reader 0x012b3812 (validate_model_edge's machine: original instructions) reads
every installed Data/Object142 model of world 141; for each action, the int16 it leaves at action +8 must equal
mu_bmd's actions[a].keys (native/core/mu_bmd.c, built into a temporary library) and the client layout walk's key
count; the reader must also consume the whole stream (which only happens if each bone track holds keys entries).
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
import sys
import tempfile
import actor_machine as am
import validate_object_render as v
import validate_worlds_q2 as q2
import pins

ROOT = Path(__file__).resolve().parents[1]
PREDICATE = (0x17fcd18, 0x17fe909)
MANAGER, HANDLER_OBJECT, SINGLETON = q2.MANAGER, q2.HANDLER_OBJECT, q2.SINGLETON
CAMERA = 0x0bdc5ab4   # SceneCameraPosition
COOKIE = 0x01cf65c0   # MSVC security cookie (the CRT sqrt's error path for NaN)
MATHERR = 0x0bdcf8e0  # the CRT's encoded user-matherr pointer: the cookie itself decodes to none (CRT default)
# the types each world case and chain step lists (sampling aid; the C has its own copies)
LISTS = {
    0: [0x3c, 0x37], 2: [0x7a, 0x7b], 0x21: [0x21, 0x23], 0x25: [0x4b, 0x20, 0x7c, 0x75, 0x55, 0x38],
    0x33: list(range(5, 0xf)) + [0x57, 0x58, 4, 0x81, 0x73, 0x39, 0xa6, 0xa7, 0x7e, 0x5b, 0x26, 0x20, 0x1e, 0x80],
    0x38: [0x10, 0x27, 0x33, 0x38, 0x46, 0x4c, 0x55], 0x39: [0x1e, 0x1f], 0x3a: [0x1e, 0x1f], 0x4a: [0x81, 0x62],
    0x49: [0x7a, 0x7b, 0x7c, 0x9f, 0x7e, 0x81, 0x7f, 0, 5, 0x50, 299, 300, 301],
    0x5b: [0x1d, 0x1b, 0x3c], 0x5c: [0x1d, 0x1b, 0x3c],
    0x64: [0x14, 0x1d, 0x21, 0x22, 0x23, 0x27, 0x36, 0x37, 0x38, 0x60, 0x61],
    0x6e: [0, 8, 9, 0x13, 0x1c, 0xc, 0xb, 6, 0x23, 0x24, 0x25, 0x26, 0x3c, 0x40, 0x9a],
    0x70: [0xa, 0x12, 0x16, 0x1a, 0x1d, 0x1f, 0x22, 0x25, 0x3c, 0x41, 0x54, 0x61, 0x62, 0x6a, 0x72, 0x7e, 0x7f, 0x89,
           0x98, 0x99, 0x9a],
    0x71: [0, 1, 2, 3, 7, 8, 0xa, 0xb, 0x17, 0x21, 0x33, 0x34, 0x46, 0x47, 0x4e, 0x50, 0x54, 0x55, 0x63, 0x66, 0x6a,
           0x73, 0x76, 0x80, 0x82, 0x85, 0x92, 0x96, 0x9d, 0x9f],
    0x7a: [0, 1, 2, 3, 8, 9, 0xe, 0xf, 0x10, 0x11, 0x13, 0x1b, 0x1e, 0x21, 0x24, 0x30, 0x31, 0x32, 0x33, 0x35, 0x3a,
           0x3d, 0x3f, 0x40, 0x44, 0x4a, 0x4b, 0x4e, 0x58, 0x5c, 0x5d, 0x5e, 0x5f, 0x64, 0x67, 0x69, 0x6d, 0x6e, 0x6f,
           0x71, 0x74, 0x75, 0x7c, 0x83, 0x84, 0x85, 0xad, 0xae],
    0x83: [0xc, 0x16, 0x19, 0x1a, 0x1c, 0x22, 0x26, 0x27, 0x2c, 0x2d, 0x32, 0x3b, 0x3c, 0x3d, 0x3f, 0x43, 0x52, 0x53,
           0x54, 0x55, 0x58, 0x5f, 0x60, 0x62, 0x6a, 0x72, 0x77, 0x78, 0x79, 0x7f, 0x80, 0x83, 0x85, 0x8d, 0x98, 0x9a,
           0x9b, 0xac, 0xad, 0, 2, 3, 5, 8, 0xa, 0x46, 0x4b, 0x4e],
    0x84: [0x1e],
    0x85: [1, 2, 3, 5, 7, 8, 0xa, 0xb, 0x10, 0x11, 0x16, 0x17, 0x1d, 0x1e, 0x1f, 0x3d, 0x40, 0x41, 0x42, 0x43, 0x4b,
           0x50, 0x51, 0x73, 0x7e, 0x80, 0x81, 0x85, 0x88, 0x89, 0x91, 0x94, 0x9d, 0xac],
    0x27: [0, 0x4bc], 0x3f: [0x10, 0x43, 0x44, 0x45],
}
LISTS.update({w: LISTS[0x64] for w in (0x65,)})
LISTS.update({w: LISTS[0x6e] for w in (0x6f,)})
LISTS.update({w: [0x10, 0x43, 0x44, 0x45] for w in range(0x52, 0x5b)})
LISTS.update({w: [0, 1, 0x17, 0x23, 0x25, 0x2b, 0x2c, 0x2d, 0x40, 0x4f, 0x51, 0x55, 0x5d, 0x60, 0x67, 0x6b, 0x6f,
                  0x7d, 0x86, 0x91, 0x9a, 0x9e] for w in range(0x7b, 0x80)})
LISTS.update({w: [1, 4, 5, 6, 7, 8] + list(range(9, 0x15)) + list(range(0x18, 0x25)) +
              [0x2a, 0x2d, 0x31, 0x33, 0x34, 0x38, 0x39, 0x3a, 0x3c, 0x3e] + list(range(0x40, 0x48))
              for w in range(0x80, 0x83)})
WORLDS = list(range(0, 0x92)) + [0xff, 0x92, -1]


class DrawFirstInputs(C.Structure):
    _fields_ = [('x2d', C.POINTER(C.c_float)), ('y2d', C.POINTER(C.c_float)), ('scene_state', C.c_int32),
                ('eye', C.POINTER(C.c_float)), ('tower_state', C.c_int32)]


def bind(path):
    lib = v.Library(path)
    lib.dll.mu_draw_first.argtypes = [C.c_void_p, C.c_int32, C.POINTER(DrawFirstInputs)]
    lib.dll.mu_draw_first.restype = C.c_int
    return lib


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    return bind(root / 'objects' / ('libobjects.' + v.SUFFIX))


def sweep_cases():
    out = []
    for w in WORLDS:
        types = sorted({t + d for t in LISTS.get(w, []) for d in (-1, 0, 1)} | {0, 0x3c})
        for t in types:
            for live in (1, 0, 2):
                out.append((w, t, live, 0))
            out.append((w, t, 1, 1))   # once more near a polygon edge, where the range decides
    return out


SWEEP = sweep_cases()


def draw_first(machine, lib, g, cases, vtables):
    tally = v.Tally('draw_first')
    for n in range(cases):
        swept = n < len(SWEEP)
        edge = 0
        if swept:
            world, typ, live, edge = SWEEP[n]
        else:
            world = g.choice(WORLDS + [0x49, 0x27, 0x74, 0x76, 0x78, 0x80, 0x81, 0x82] * 3 +
                             list(range(134, 146)))
            typ = g.choice(list(range(-2, 205)) + [255, 300, 301, 0x4bc, 1000, -1, 2147483647])
            if LISTS.get(world) and n % 2:
                typ = g.choice(LISTS[world])
            live = g.choice([1, 1, 1, 0, 2, 0xff])
        raw = bytearray(v.move_object(g, 0, 'speed'))
        v.put_i(raw, 0x5c, typ)
        raw[0] = live
        v.put_f(raw, 0xc0, v.f32(g.choice([-30.0, -300.0, -399.99, -400.0, -400.01, -500.0, -800.0, 0.0, 50.0, -1e9,
                                           math.nan, g.uniform(-2000, 100)])))
        x2d, y2d = v.frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4
        spread = 0 if swept else 30 if n % 4 == 0 else 6
        px, py = (cx + g.uniform(-spread, spread)) * 100, (cy + g.uniform(-spread, spread)) * 100
        if edge or (not swept and n % 4 == 1):   # near an edge: the range decides
            k = g.randrange(4)
            f = g.uniform(0.2, 0.8)
            ex = x2d[k] + f * (x2d[k - 1] - x2d[k])
            ey = y2d[k] + f * (y2d[k - 1] - y2d[k])
            # TestFrustrum2D's edge value d is affine along the outward direction: solve for a d next to one of
            # the predicate's ranges (or the object's own), so the range decides the answer
            dx, dy = ex - cx, ey - cy
            cross = lambda x, y: ((x2d[k] - x) * (y2d[k - 1] - y) - (x2d[k - 1] - x) * (y2d[k] - y))   # noqa: E731
            slope = cross(ex + dx, ey + dy) - cross(ex, ey)
            target = g.choice([-1500.0, -600.0, -500.0, -400.0, 0.0, struct.unpack_from('<f', raw, 0xc0)[0]])
            target = (target if math.isfinite(target) else -500.0) + g.uniform(-120, 120)
            t = target / slope if slope else 0.0
            px, py = (ex + t * dx) * 100, (ey + t * dy) * 100
        v.put_f(raw, 0x158, v.f32(px), v.f32(py))
        if not swept and n % 19 == 0:
            struct.pack_into('<I', raw, 0x158 + 4 * g.randrange(2), g.choice([0x7fc00000, 0xff800000, 0x80000000]))
        # world 0x49's fade: camera distance around 2000 / 4000, fade fields at and around their limits
        dist = g.choice([0.0, 500.0, 1999.0, 2000.0, 2001.0, 3999.0, 4000.0, 4001.0, 9000.0, g.uniform(0, 5000)])
        a = g.uniform(0, 2 * math.pi)
        eye = [v.f32(px + dist * math.cos(a)), v.f32(py + dist * math.sin(a)), v.f32(g.uniform(0, 1500))]
        if not swept and n % 23 == 0:
            eye[g.randrange(2)] = v.f32(g.choice([math.nan, math.inf]))
        for field in (0xa8, 0xd8, 0xdc):
            v.put_f(raw, field, v.f32(g.choice([0.0, 0.0, 1.0, 0.98, 0.99, 0.5, 1.5, -0.0, math.nan,
                                                 g.uniform(-0.2, 1.2)])))
        tower = g.choice([0, 1, 2, 3, 4, 5, 6, -1])
        scene = 6 if swept else g.choice([6, 6, 6, 5, 2, 1, 4])
        vt = vtables.get(world)
        singleton = bytearray(0x100)
        struct.pack_into('<i', singleton, 0x78 + 4, tower)
        regs = v.global_regions(world, scene, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('x2d', v.X2D, v.pack_f(*x2d), writable=False),
            am.defined_region('y2d', v.Y2D, v.pack_f(*y2d), writable=False),
            am.defined_region('camera', CAMERA, v.pack_f(*eye), writable=False),
            am.defined_region('manager', MANAGER, struct.pack('<5I', 0, 0, 0, 0, HANDLER_OBJECT if vt else 0),
                              writable=False),
            am.defined_region('handler', HANDLER_OBJECT, struct.pack('<I', vt or 0) + bytes(0x7c), writable=False),
            am.defined_region('singleton', SINGLETON, bytes(singleton), writable=False),
            am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('matherr', MATHERR, struct.pack('<I', 0xbb40e64e), writable=False)])
        result = v.run(machine, PREDICATE[0], [v.OBJECTS], regs,
                       {0xea594b: lambda m: (MANAGER, 0), 0x9a6ef3: lambda m: (SINGLETON, 0)})
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        xs, ys, es = (C.c_float * 4)(*x2d), (C.c_float * 4)(*y2d), (C.c_float * 3)(*eye)
        inputs = DrawFirstInputs(xs, ys, scene, es, tower)
        answer = lib.dll.mu_draw_first(co, world, C.byref(inputs))
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        al = result['eax'] & 255
        tally.count('answer %d' % al)
        tally.count('world %s answered yes' % world, int(al == 1))
        tally.count('fields written', int(bytes(raw) != bytes(result['regions']['object'])))
        tally.add(not diff and answer == al, {'case': n, 'type': typ, 'world': world, 'live': live, 'diff': diff[:8],
                                              'al': al, 'c': answer})
    return tally


# ---------------------------------------------------------------- action keys

class BmdAction(C.Structure):
    _fields_ = [('keys', C.c_int32), ('lock_positions', C.c_uint8)]


class Bmd(C.Structure):
    _fields_ = [('version', C.c_int), ('name', C.c_char * 33), ('payload', C.c_void_p), ('payload_size', C.c_uint32),
                ('parsed_size', C.c_uint32), ('bone_stream', C.c_uint32), ('mesh_count', C.c_int32),
                ('bone_count', C.c_int32), ('action_count', C.c_int32), ('meshes', C.c_void_p),
                ('actions', C.POINTER(BmdAction)), ('bones', C.c_void_p), ('anomalies', C.c_void_p),
                ('anomaly_count', C.c_int32), ('strict_anomalies', C.c_int32)]


def native_bmd(scratch):
    out = Path(scratch) / ('libbmd.' + v.SUFFIX)
    sources = [ROOT / 'native/core/mu_bmd.c', ROOT / 'reconstructed/model-codec/client_lea.c',
               ROOT / 'reconstructed/model-codec/model_codec.c']
    # v14 files decrypt through model-recovery/modulus.cpp (Crypto++): the native build's object (build = native)
    modulus = ROOT / 'native/build/modulus.o'
    subprocess.run(['make', '-s', '-C', str(ROOT / 'native'), 'build/modulus.o'], check=True)
    prefix = subprocess.run(['brew', '--prefix', 'cryptopp'], capture_output=True, text=True).stdout.strip() \
        if shutil.which('brew') else '/usr'
    objects = []
    for n, src in enumerate(sources):
        objects.append(str(Path(scratch) / ('bmd%d.o' % n)))
        subprocess.run(['cc', '-std=c11', '-O1', '-fPIC', '-c', str(src), '-o', objects[-1]], check=True)
    subprocess.run(['c++', '-shared', '-o', str(out)] + objects + [str(modulus), '-L' + prefix + '/lib', '-lcryptopp',
                    '-lm'], check=True)
    dll = C.CDLL(str(out))
    dll.mu_bmd_load_file.argtypes = [C.c_char_p, C.POINTER(Bmd), C.c_char_p, C.c_size_t]
    dll.mu_bmd_free.argtypes = [C.POINTER(Bmd)]
    return dll


def action_keys(game_root, every=1):
    import validate_model_edge as me
    sys.path.insert(0, str(ROOT / 'model-recovery'))
    import bmd_encrypted
    tally = v.Tally('action_keys')
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = me.EdgeMachine(text, data, pins.FLAG.read(), pins.FEATURE09.read())
    with tempfile.TemporaryDirectory(prefix='worlds-after4-bmd-') as scratch:
        dll = native_bmd(scratch)
        files = sorted(p for p in (Path(game_root) / 'Data/Object142').iterdir() if p.suffix.lower() == '.bmd')
        for index, path in enumerate(files):
            if index % every and path.name != 'Object45.bmd':   # Object45: type 0x2c
                continue
            raw = path.read_bytes()
            if raw[:3] != b'BMD' or raw[3] not in (12, 14, 15):
                tally.count('other version')
                continue
            payload = {12: bmd_encrypted.decrypt_map, 14: bmd_encrypted.decrypt_modulus,
                       15: bmd_encrypted.decrypt_lea}[raw[3]](raw[8:])
            machine.reset()
            result = machine.run_reader(payload, raw[3])
            layout = me.client_layout(payload)
            model = C.pointer(Bmd())
            err = C.create_string_buffer(256)
            status = dll.mu_bmd_load_file(str(path).encode(), model, err, 256)
            if not result['match'] or status:
                tally.add(False, {'file': path.name, 'reader': result['match'], 'native': err.value.decode()},
                          None if result['match'] else str(result['error']))
                continue
            actions = machine.u32(result['model'] + 0x30)
            count = struct.unpack('<h', machine.read(result['model'] + 0x26, 2))[0]
            client = [struct.unpack('<h', machine.read(actions + 16 * i + 8, 2))[0] for i in range(max(count, 0))]
            native = [model.contents.actions[i].keys for i in range(model.contents.action_count)]
            walk = [a['keys'] for a in layout['actions']]
            dll.mu_bmd_free(model)
            ok = client == native == walk and result['offset'] == layout['end']
            tally.count('actions', len(client))
            tally.count('keys > 1', sum(1 for k in client if k > 1))
            if path.name == 'Object45.bmd':
                tally.count('type 0x2c keys %s' % client)
            tally.add(ok, {'file': path.name, 'client': client[:8], 'native': native[:8], 'walk': walk[:8]})
    return tally


# ---------------------------------------------------------------- mutants

D = 'world_draw_first_visual.c'
MUTATIONS = [
    ('w0 list', D, 'w0[] = {0x3c, 0x37, END}', 'w0[] = {0x3c, END}'),
    ('w2 range', D, 'case 2: return listed(t, w2) && frustum(o, in, range_of(o));',
     'case 2: return listed(t, w2) && frustum(o, in, -500.0f);'),
    ('w25 list', D, '0x55, 0x38, END};', '0x55, END};'),
    ('w33 span', D, '(t >= 5 && t <= 0xe)', '(t >= 5 && t <= 0xd)'),
    ('w33 live', D, 'listed(t, w33)) && live == 1', 'listed(t, w33)) && live'),
    ('w33 range', D, 'frustum(o, in, -400.0f);\n    case 0x38', 'frustum(o, in, -500.0f);\n    case 0x38'),
    ('w38 range', D, '-1500.0f', '-1400.0f'),
    ('w38 live', D, 'listed(t, w38) && live &&', 'listed(t, w38) &&'),
    ('w39 range', D, 'listed(t, w39) && frustum(o, in, -600.0f)', 'listed(t, w39) && frustum(o, in, -500.0f)'),
    ('w4a list', D, 'w4a[] = {0x81, 0x62, END}', 'w4a[] = {0x81, END}'),
    ('w5c world', D, 'case 0x5b: case 0x5c:', 'case 0x5b:'),
    ('w64 list', D, '0x60, 0x61, END};\nstatic const int32_t w6e', '0x60, END};\nstatic const int32_t w6e'),
    ('w6e list', D, '0x3c, 0x40, 0x9a, END}', '0x3c, 0x40, END}'),
    ('w70 live', D, 'listed(t, w70) && live == 1', 'listed(t, w70)'),
    ('w71 list', D, '0x96, 0x9d, 0x9f, END}', '0x96, 0x9d, END}'),
    ('w7a list', D, '0x85, 0xad, 0xae,', '0x85, 0xad,'),
    ('w83 list', D, '0x46, 0x4b,\n                              0x4e, END}', '0x46, 0x4b, END}'),
    ('w84 list', D, 'w84[] = {0x1e, END}', 'w84[] = {0x1f, END}'),
    ('w85 live', D, 'frustum(o, in, range_of(o)) && live;', 'frustum(o, in, range_of(o));'),
    ('w85 list', D, '0x9d,\n                              0xac, END}', '0x9d, END}'),
    ('49 near', D, 'r * 2.0f > d', 'r > d'),
    ('49 far', D, 'r > d && t <= 300', 'r > d && t < 300'),
    ('49 fade step', D, 'v + 0.0299999993f', 'v + 0.03125f'),
    ('49 fade cap', D, '1.0f > v ?', '1.0f >= v ?'),
    ('49 near alpha', D, '        fade_in(o, MU_OBJF_BLEND_LIGHT);\n', ''),
    ('49 clear', D, '!(target == 0.0f) && d > r', 'target > 0.0f && d > r'),
    ('49 clear alpha', D, '        mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.0f);\n', ''),
    ('49 range', D, 'frustum(o, in, -500.0f) && r > d', 'frustum(o, in, range_of(o)) && r > d'),
    ('49 eye', D, 'in->eye[1] - mu_obj_f32', 'in->eye[0] - mu_obj_f32'),
    ('49 list', D, '0x7e, 0x81, 0x7f, END}', '0x7e, 0x81, END}'),
    ('tower state', D, 'in->tower_state != 5 &&', ''),
    ('tower list', D, 'c_tower[] = {0, 0x4bc, END}', 'c_tower[] = {0, END}'),
    ('3f list', D, 'c_3f[] = {0x10, 0x43, 0x44, 0x45, END}', 'c_3f[] = {0x10, 0x43, 0x44, END}'),
    ('52 span', D, 'world >= 0x52 && world <= 0x5a', 'world >= 0x52 && world <= 0x59'),
    ('74 limit', D, '-400.0f >= range_of(o)', '-400.0f > range_of(o)'),
    ('74 span', D, 'world >= 0x74 && world <= 0x78', 'world >= 0x74 && world <= 0x77'),
    ('7b list', D, '0x9a, 0x9e, END}', '0x9a, END}'),
    ('80 live', D, 'o[MU_OBJF_LIVE] && listed(t, c_80)', 'listed(t, c_80)'),
    ('80 list', D, '0x45, 0x46, 0x47,\n                               END}', '0x45, 0x46, END}'),
    ('chain tail', D, 'return mu_class_first_owned(world) ? mu_class_first(o, world, in->x2d, in->y2d, in->scene_state) : 0;',
     'return 0;'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=6000)
    p.add_argument('--only')
    p.add_argument('--game-root')
    p.add_argument('--every', type=int, default=1, help='action_keys: every n-th Object142 model (and Object45)')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    q2.machine_data = data
    vtables = q2.class_vtables(text, data)
    families = ['draw_first'] + (['action_keys'] if a.game_root else [])
    names = [n for n in families if not a.only or n in a.only.split(',')]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}, 'mutants': [],
              'bodies': {'draw_first': {'start': hex(PREDICATE[0]), 'end': hex(PREDICATE[1]), 'sha256': hashlib.sha256(
                  text[PREDICATE[0] - am.TEXT_BASE:PREDICATE[1] - am.TEXT_BASE]).hexdigest()}},
              'sweep_cases': len(SWEEP)}
    lib = build(ROOT / 'reconstructed')
    seed = lambda: random.Random('worlds-after4-draw-first')   # noqa: E731
    for name in names:
        tally = draw_first(machine, lib, seed(), a.cases, vtables) if name == 'draw_first' else \
            action_keys(a.game_root, a.every)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:3000], flush=True)
    if a.mutations and 'draw_first' in names:
        for label, file, old, new in MUTATIONS:
            with tempfile.TemporaryDirectory(prefix='worlds-after4-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects' / file
                s = path.read_text()
                assert s.count(old) == 1, (label, old)
                path.write_text(s.replace(old, new, 1))
                tally = draw_first(machine, build(root), seed(), a.cases, vtables)
                item = {'name': label, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped, 'stopped': tally.stopped}
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
