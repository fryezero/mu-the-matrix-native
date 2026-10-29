#!/usr/bin/env python3
"""Scorched Canyon, Red Smoke Icarus, Temple of Arnil and Gray Aida primary methods against original instructions,
with compiled mutants."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import tempfile
import actor_machine as am
import validate_object_render as v
import pins
from unicorn.x86_const import UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'sc_create': (0xe432d9, 0xe4370c), 'sc_move': (0xe4370c, 0xe43842), 'sc_visual': (0xe43f8e, 0xe43fab),
          'rs_create': (0xe00b4a, 0xe00cfe), 'rs_move': (0xe00cfe, 0xe00d4c), 'rs_visual': (0xe00e97, 0xe010b6),
          'ta_create': (0xd809fc, 0xd80c9c), 'ta_move': (0xd80c9c, 0xd80cea), 'ta_visual': (0xd81c2c, 0xd81c49),
          'ga_create': (0xd84821, 0xd849e4), 'ga_move': (0xd849e4, 0xd84d0e), 'ga_visual': (0xd84dd8, 0xd868f7)}
WORLD = {'sc': 0x83, 'rs': 0x84, 'ta': 0x85, 'ga': 0x86}
EDGES = [-2147483648, -1, 0, 2147483647]
LISTED = {
    'sc_create': [0, 2, 3, 5, 8, 0xa, 0xc, 0x16, 0x19, 0x1a, 0x1c, 0x22, 0x26, 0x27, 0x28, 0x2c, 0x2d, 0x32, 0x3b, 0x3c,
                  0x3d, 0x3f, 0x43, 0x46, 0x4b, 0x4e, 0x4f, 0x52, 0x53, 0x54, 0x55, 0x58, 0x5a, 0x5f, 0x60, 0x62, 0x6a,
                  0x72, 0x77, 0x78, 0x79, 0x7f, 0x80, 0x83, 0x85, 0x88, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x93, 0x94,
                  0x95, 0x98, 0x9a, 0x9b, 0x9f, 0xa0, 0xa7, 0xa8, 0xaa, 0xac, 0xad, 0xae, 0xb2, 0xb3, 0xb5, 0xba, 0xc5, 0xc7],
    'rs_create': [5, 6, 0xb, 0x16, 0x17, 0x1c, 0x1d, 0x1e, 0x2b, 0x2c, 0x2e, 0x2f, 0x3c, 0x3d],
    'ta_create': [1, 2, 3, 5, 6, 7, 8, 0xa, 0xb, 0xe, 0x10, 0x11, 0x16, 0x17, 0x1d, 0x1e, 0x1f, 0x3d, 0x40, 0x41, 0x42,
                  0x43, 0x4b, 0x50, 0x51, 0x73, 0x7b, 0x7e, 0x80, 0x81, 0x84, 0x85, 0x86, 0x88, 0x89, 0x8f, 0x91, 0x94,
                  0x9d, 0x9f, 0xa0, 0xa1, 0xa2, 0xa9, 0xaa, 0xac],
    'ga_create': [0, 4, 6, 7, 8, 9, 0x10, 0x11, 0x13, 0x16, 0x18, 0x19, 0x1f, 0x21, 0x22, 0x23, 0x24, 0x29, 0x2a, 0x2e,
                  0x37, 0x3b, 0x3e, 0x4f, 0x50, 0x53, 0x5c, 0x6d, 0x85],
    'sc_move': [0xa0], 'rs_move': [0, 0x1e], 'ta_move': [0, 6],
    'ga_move': [0x19, 0x1c, 0x29, 0x38, 0x3a, 0x3f, 0x40, 0x43, 0x46, 0x48, 0x49, 0x4a],
    'sc_visual': [0], 'ta_visual': [0],
    'rs_visual': [0, 1, 2, 3, 4, 0xa],
    'ga_visual': [0x1e, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3e, 0x41, 0x42, 0x43, 0x46, 0x47, 0x49, 0x4a, 0x4d, 0x4e, 0x5c,
                  0x84, 0x85, 0x3c, 0x46, 0x3c, 0x46, 0x3c, 0x46],
}
TYPES = {k: sorted({t + d for t in ts for d in (-1, 0, 1)} | set(ts)) for k, ts in LISTED.items()}
MODEL_SIZE, STREAM = 0x100, 0x94
MU_WR_STREAM, MU_WR_EFFECT_SCALED, MESH, EFFECT = 0x00d85c26, 0x00d85e29, 0x00966e4a, 0x013c0eaa
BONE = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))


def bind(lib):
    d = lib.dll
    d.mu_scorched_canyon_create.argtypes = [C.c_void_p, C.c_int32, v.RAND_FN, C.c_void_p]
    for name in ('mu_red_smoke_icarus_create', 'mu_temple_arnil_create', 'mu_gray_aida_create'):
        getattr(d, name).argtypes = [C.c_void_p, C.c_int32]
    d.mu_scorched_canyon_move.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int, v.RAND_FN, C.c_void_p,
                                          C.POINTER(v.Log)]
    for name in ('mu_red_smoke_icarus_move', 'mu_temple_arnil_move'):
        getattr(d, name).argtypes = [C.c_void_p, C.c_int32, C.c_int]
    d.mu_gray_aida_move.argtypes = [C.c_void_p, C.c_int32, C.c_int32, v.RAND_FN, C.c_void_p, C.POINTER(v.Log)]
    for name in ('mu_scorched_canyon_visual', 'mu_temple_arnil_visual'):
        getattr(d, name).argtypes = [C.c_void_p, C.c_int]
    d.mu_red_smoke_icarus_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, BONE, C.c_void_p, C.POINTER(v.Log)]
    d.mu_gray_aida_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.c_float, v.RAND_FN, BONE, C.c_void_p,
                                      C.POINTER(v.Log)]
    return lib


def stubs(calls, rnd, has_model):
    def particle(m):
        a = [m.argument(k) for k in range(8)]
        assert a[6] in (0, v.OBJECTS) and a[7] == 0
        calls.append((0x168fafd, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                     (a[4], a[5], int(a[6] == v.OBJECTS)))
        return 0

    def sprite(m):
        a = [m.argument(k) for k in range(9)]
        assert a[4:8] == [v.OBJECTS, 0, 0, 4] and v.read_vec(m, a[8]) == (1, 1, v.bits(1))
        calls.append((0x1692eb7, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) + (0, 1, 0, 4))
        return 0

    def light(m):
        a = [m.argument(k) for k in range(5)]
        assert a[4] == v.FRAME_LIGHT
        calls.append((0x16cacfc, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
        return 0

    def effect(m):   # neutral form: type, position, angle, light, subtype, owner, eighth argument, float eleventh
        a = [m.argument(k) for k in range(14)]
        assert a[6:8] == [0xffffffff, 0] and a[9] == 0 and a[11:] == [0xffffffff, 0, 0]
        calls.append((EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                     (a[4], int(a[5] == v.OBJECTS), a[8], a[10]))
        return 0

    def mesh(m):
        assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL
        calls.append((MU_WR_STREAM, 0, m.uc.mem_read(v.MODEL + STREAM, 1)[0]))
        calls.append((MESH, 0) + tuple(m.argument(k) for k in range(8)))
        return (0, 0x20)
    return {0x168fafd: particle, 0x1692eb7: sprite, 0x16cacfc: light, EFFECT: effect, MESH: mesh,
            0x1989721: lambda m: rnd(), 0x966cc4: lambda m: v.FAKE,
            0xeaa8cf: lambda m: (v.MODEL if has_model else 0, 4)}


def c_events(log):
    """C events in the stub's form: both CreateEffect kinds become the neutral effect tuple."""
    out = []
    for e in v.log_events(log):
        if e[0] == EFFECT:
            out.append(e[:2] + e[2:13] + (e[13], 0, e[14]))
        elif e[0] == MU_WR_EFFECT_SCALED:
            out.append((EFFECT, e[1]) + e[2:13] + (e[13], e[14], 0))
        else:
            out.append(e)
    return out


def object_case(g, typ):
    raw = bytearray(v.poison_object(g))
    v.put_i(raw, 0x5c, typ)
    v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 0.5, 1.3, 2.0, 3.7, 65535.9, 65536.5, 70000.0, -1.0, -0.5,
                                        g.uniform(0, 5)])))
    v.put_f(raw, 0x158, v.f32(g.uniform(0, 25600)), v.f32(g.uniform(0, 25600)), v.f32(g.uniform(-100, 500)))
    v.put_f(raw, 0x164, *(v.f32(g.uniform(-360, 360)) for _ in range(3)))
    v.put_f(raw, 0xbc, v.f32(g.choice([0.16, 0.3, 1.0, 0.0, -0.0, g.uniform(-2, 2)])))
    v.put_i(raw, 0x68, g.choice([-2, -1, -1, 0, 3, g.getrandbits(32) - 2 ** 31]))
    return raw


def model_bytes(g):
    return bytes(g.getrandbits(8) for _ in range(MODEL_SIZE))


def compare(tally, result, co, al, calls, events, rnd, crnd, info, extra=True):
    diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
    ok = not diff and al == (result['eax'] & 255) and calls == events and rnd.seed == crnd.seed and extra
    tally.count('events', len(calls))
    for c in calls:
        tally.count('call %#x' % c[0])
    tally.add(ok, dict(info, diff=diff[:8], al=result['eax'] & 255, c_al=al, calls=calls[:4], c=events[:4],
                       rng=rnd.seed == crnd.seed))


def pick_type(g, name, types, n):
    """A fifth random types, three fifths the listed cases, a fifth the listed types and their neighbours."""
    if n % 5 == 0:
        return g.randrange(-5, 0x110)
    if n % 5 < 4:
        return LISTED[name][(n // 5 * 3 + n % 5) % len(LISTED[name])]
    return types[(n // 5) % len(types)]


def worlds_for(prefix):
    return [WORLD[prefix]] * 8 + [0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0]


def create_family(machine, lib, name, cases):
    g = random.Random('worlds-r-' + name)
    tally = v.Tally(name)
    prefix = name.split('_')[0]
    types = TYPES[name] + EDGES
    worlds = worlds_for(prefix)
    for n in range(cases):
        typ = pick_type(g, name, types, n)
        world = g.choice(worlds)
        null = n % 41 == 40
        raw = object_case(g, typ)
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw))])
        result = v.run(machine, BODIES[name][0], [0 if null else v.OBJECTS], regs, stubs([], rnd, True),
                       ecx=v.FAKE, cleanup=4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        obj = None if null else co
        if prefix == 'sc':
            al = lib.dll.mu_scorched_canyon_create(obj, world, v.RAND_FN(lambda ctx: crnd()), None)
        else:
            fn = {'rs': lib.dll.mu_red_smoke_icarus_create, 'ta': lib.dll.mu_temple_arnil_create,
                  'ga': lib.dll.mu_gray_aida_create}[prefix]
            al = fn(obj, world)
        tally.count('type %d' % typ if typ in LISTED[name] else 'other type')
        tally.count('world %d' % world)
        compare(tally, result, co, al, [], [], rnd, crnd, {'case': n, 'type': typ, 'world': world})
    return tally.report()


def move_family(machine, lib, name, cases):
    g = random.Random('worlds-r-' + name)
    tally = v.Tally(name)
    prefix = name.split('_')[0]
    types = TYPES[name] + EDGES
    worlds = worlds_for(prefix)
    for n in range(cases):
        typ = pick_type(g, name, types, n)
        world = g.choice(worlds)
        null = n % 43 == 42
        has_model = n % 7 != 3
        raw = object_case(g, typ)
        v.put_f(raw, 0xb0, v.f32(g.choice([0.0, -0.0, 0.015, 1.0, g.uniform(-10, 10)])))
        v.put_f(raw, 0xdc, v.f32(g.choice([0.0, 0.5, 1.0, g.uniform(-1, 2)])))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw))])
        result = v.run(machine, BODIES[name][0], [0 if null else v.OBJECTS], regs, stubs(calls, rnd, has_model),
                       ecx=v.FAKE, cleanup=4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        obj = None if null else co
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        if prefix == 'sc':
            al = lib.dll.mu_scorched_canyon_move(obj, 0, world, has_model, fn, None, C.byref(log))
        elif prefix == 'ga':
            al = lib.dll.mu_gray_aida_move(obj, 0, world, fn, None, C.byref(log))
        else:
            move = lib.dll.mu_red_smoke_icarus_move if prefix == 'rs' else lib.dll.mu_temple_arnil_move
            al = move(obj, world, has_model)
        tally.count('type %d' % typ if typ in LISTED[name] else 'other type')
        tally.count('world %d' % world)
        tally.count('model' if has_model else 'no model')
        compare(tally, result, co, al, calls, c_events(log), rnd, crnd, {'case': n, 'type': typ, 'world': world})
    return tally.report()


SINE_SAFE = [0.0, -0.0, 1000.0, 3926.99072265625, -2999.5]


def visual_time(g, typ):
    k = g.randrange(-1000, 3000) * 1024
    near = [k + d for d in (0, 0.5, 9, 9.99, 10, 10.5, 29, 29.5, 30, -1, -0.5, -10, -29.5, -30, -31)]
    if typ in (0x3c, 0x46) and g.random() < 0.8:   # the phase windows [0, 10) and [0, 30)
        edge = (0, 0.5, 9, 9.99, 10, 10.5, -0.5, -1) if typ == 0x3c else (0, 0.5, 29, 29.5, 30, 30.5, -0.5, -1)
        return v.f32(abs(k) + g.choice(edge))
    pool = SINE_SAFE + near + [g.uniform(-1e6, 1e6), 99999.5, 100000.0, -100000.0, 199999.0]
    if typ not in (0x49, 0x4a):
        pool += [3e9, -3e9, float('inf'), float('-inf'), float('nan'), 2147483520.0, -2147483648.0]
    return v.f32(g.choice(pool))


def visual_family(machine, lib, name, cases):
    g = random.Random('worlds-r-' + name)
    tally = v.Tally(name)
    prefix = name.split('_')[0]
    types = TYPES[name] + EDGES
    for n in range(cases):
        typ = pick_type(g, name, types, n)
        present = n % 9 != 4
        null = n % 47 == 46
        raw = object_case(g, typ)
        time = visual_time(g, typ)
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones, cbones = [], [], []

        def position(k, local):
            return tuple(v.f32(local[q] + k * (q + 1) * 17) for q in range(3))

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL and a[3] == 0
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + k * 0x30
            local = tuple(struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12))))
            bones.append((k, local))
            m.uc.mem_write(a[2], v.pack_f(*position(k, local)))
            return (0, 16)
        st = stubs(calls, rnd, True)
        st[0x12b6ef1] = bone
        model = model_bytes(g)
        regs = v.global_regions(WORLD[prefix], 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                                  am.defined_region('model', v.MODEL, model),
                                                  am.defined_region('time', v.TIME, v.pack_f(time), writable=False)])
        result = v.run(machine, BODIES[name][0], [0 if null else v.OBJECTS, v.MODEL if present else 0], regs, st,
                       ecx=v.FAKE, cleanup=8)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        if any(c[0] == MESH for c in calls):
            calls.append((MU_WR_STREAM, 0, result['regions']['model'][STREAM]))
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        obj = None if null else co
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())

        def cb(ctx, k, local, out):
            local = tuple(local[:3])
            cbones.append((k, local))
            for q, value in enumerate(position(k, local)):
                out[q] = value
        c_bone = BONE(cb)
        if prefix == 'sc':
            al = lib.dll.mu_scorched_canyon_visual(obj, present)
        elif prefix == 'ta':
            al = lib.dll.mu_temple_arnil_visual(obj, present)
        elif prefix == 'rs':
            al = lib.dll.mu_red_smoke_icarus_visual(obj, 0, present, c_bone, None, C.byref(log))
        else:
            al = lib.dll.mu_gray_aida_visual(obj, 0, present, time, fn, c_bone, None, C.byref(log))
        model_ok = any(c[0] == MESH for c in calls) or result['regions']['model'] == model
        tally.count('type %d' % typ if typ in LISTED[name] else 'other type')
        tally.count('present' if present else 'absent')
        compare(tally, result, co, al, calls, c_events(log), rnd, crnd,
                {'case': n, 'type': typ, 'time': time, 'bones': bones[:2], 'cbones': cbones[:2]},
                bones == cbones and model_ok)
    return tally.report()


def family(machine, lib, name, cases):
    kind = name.split('_', 1)[1]
    return {'create': create_family, 'move': move_family, 'visual': visual_family}[kind](machine, lib, name, cases)


MUTANTS = [
    ('scorched_canyon.c', 'if (world != 0x83 || !o)\n        return 0;\n    const', 'if (world != 0x84 || !o)\n        return 0;\n    const', 'sc_create'),
    ('scorched_canyon.c', 'case 0x0c: case 0x16:', 'case 0x0d: case 0x16:', 'sc_create'),
    ('scorched_canyon.c', 'case 0xac: case 0xad:', 'case 0xac: case 0xae:', 'sc_create'),
    ('scorched_canyon.c', '-400.0f', '-401.0f', 'sc_create'),
    ('scorched_canyon.c', 'case 0x4b: case 0x4e:', 'case 0x4b: case 0x4d:', 'sc_create'),
    ('scorched_canyon.c', 't >= 0xa0 && t <= 0xa7', 't >= 0xa0 && t <= 0xa8', 'sc_create'),
    ('scorched_canyon.c', 'case 0x6a:\n        mu_obj_set_i32(o, 0x60, (rnd(c) % 18 + 1) * 10)', 'case 0x6a:\n        mu_obj_set_i32(o, 0x60, (rnd(c) % 17 + 1) * 10)', 'sc_create'),
    ('scorched_canyon.c', 'case 0x93: case 0x94: case 0x95:', 'case 0x93: case 0x94: case 0x96:', 'sc_create'),
    ('scorched_canyon.c', 'case 0xc5: case 0xc7:', 'case 0xc5: case 0xc6:', 'sc_create'),
    ('scorched_canyon.c', '/ 3.0f', '/ 2.0f', 'sc_create'),
    ('scorched_canyon.c', '|| !has_model)', '|| has_model < 0)', 'sc_move'),
    ('scorched_canyon.c', '== 0xa0) {', '== 0xa1) {', 'sc_move'),
    ('scorched_canyon.c', 's * 0.04f, 3)', 's * 0.04f, 2)', 'sc_move'),
    ('scorched_canyon.c', 'rnd(c) % 4 + 3', 'rnd(c) % 4 + 2', 'sc_move'),
    ('scorched_canyon.c', 'return o && present;', 'return o && present >= 0;', 'sc_visual'),
    ('red_smoke_icarus.c', 'if (world != 0x84 || !o)', 'if (world != 0x83 || !o)', 'rs_create'),
    ('red_smoke_icarus.c', '-1600.0f', '-1500.0f', 'rs_create'),
    ('red_smoke_icarus.c', 'mu_obj_set_f32(o, 0xcc, -3000.0f)', 'mu_obj_set_f32(o, 0xc8, -3000.0f)', 'rs_create'),
    ('red_smoke_icarus.c', 'MU_OBJF_ANGLE + 8, 340.0f', 'MU_OBJF_ANGLE + 4, 340.0f', 'rs_create'),
    ('red_smoke_icarus.c', 't >= 6 && t <= 0x3c', 't >= 6 && t <= 0x3d', 'rs_create'),
    ('red_smoke_icarus.c', '!(t >= 0x2c && t <= 0x2e)', '!(t >= 0x2c && t <= 0x2d)', 'rs_create'),
    ('red_smoke_icarus.c', 'return world == 0x84 && o && has_model;', 'return world == 0x84 && o && has_model >= 0;', 'rs_move'),
    ('red_smoke_icarus.c', 't < 3 ? 20 : 10', 't < 2 ? 20 : 10', 'rs_visual'),
    ('red_smoke_icarus.c', '{0.05f, 0.02f, 0.01f}', '{0.05f, 0.03f, 0.01f}', 'rs_visual'),
    ('red_smoke_icarus.c', 'wv_particle(o, i, 0x7f89, t, light, 1, log)', 'wv_particle(o, i, 0x7f89, t, light, 0, log)', 'rs_visual'),
    ('red_smoke_icarus.c', 'bone(c, 3, zero, pos)', 'bone(c, 2, zero, pos)', 'rs_visual'),
    ('red_smoke_icarus.c', 'if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {', 'if (1) {', 'rs_visual'),
    ('red_smoke_icarus.c', 'wb_arg(e, 0); wb_float(e, 1.0f)', 'wb_arg(e, 0); wb_float(e, 1.5f)', 'rs_visual'),
    ('temple_arnil.c', 'o[MU_OBJF_LIGHT_ENABLE] = 0;', '', 'ta_create'),
    ('temple_arnil.c', 'case 0x86: case 0x8f:', 'case 0x87: case 0x8f:', 'ta_create'),
    ('temple_arnil.c', 't >= 0xa0 && t <= 0xa9', 't >= 0xa0 && t <= 0xaa', 'ta_create'),
    ('temple_arnil.c', 'case 0x9d: case 0xac:', 'case 0x9d: case 0xab:', 'ta_create'),
    ('temple_arnil.c', '-500.0f', '-300.0f', 'ta_create'),
    ('temple_arnil.c', 'return world == 0x85 && o && has_model;', 'return world == 0x85 && o && has_model >= 0;', 'ta_move'),
    ('temple_arnil.c', 'return o && present;', 'return o && present >= 0;', 'ta_visual'),
    ('gray_aida.c', 'if (world != 0x86 || !o)\n        return 0;\n    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {\n    case 0x24', 'if (world != 0x87 || !o)\n        return 0;\n    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {\n    case 0x24', 'ga_create'),
    ('gray_aida.c', 'case 0x1f: case 0x2a: case 0x85:', 'case 0x1f: case 0x2a: case 0x86:', 'ga_create'),
    ('gray_aida.c', '-80.0f', '-50.0f', 'ga_create'),
    ('gray_aida.c', 'case 0x5c: case 0x6d:', 'case 0x5c: case 0x6e:', 'ga_create'),
    ('gray_aida.c', 'case 0:\n        mu_obj_set_f32(o, MU_OBJF_RANGE, -150.0f);\n', 'case 0:\n', 'ga_create'),
    ('gray_aida.c', 'case 0x52: case 0x53:', 'case 0x52: case 0x54:', 'ga_create'),
    ('gray_aida.c', '- 0.015f', '- 0.016f', 'ga_move'),
    ('gray_aida.c', 'MU_OBJF_ALPHA, 0.5f', 'MU_OBJF_ALPHA, 0.55f', 'ga_move'),
    ('gray_aida.c', 'case 0x43: case 0x46:\n        mu_obj_set_i32', 'case 0x43: case 0x45:\n        mu_obj_set_i32', 'ga_move'),
    ('gray_aida.c', 's + 0.6f, s + 0.4f, 2)', 's + 0.6f, s + 0.4f, 3)', 'ga_move'),
    ('gray_aida.c', 'rnd(c) % 5) * 0.01f', 'rnd(c) % 6) * 0.01f', 'ga_move'),
    ('gray_aida.c', 'MU_OBJF_VELOCITY, 0.05f', 'MU_OBJF_VELOCITY, 0.06f', 'ga_move'),
    ('gray_aida.c', 'ga_turn(o, 5.0f)', 'ga_turn(o, 10.0f)', 'ga_move'),
    ('gray_aida.c', 'MU_OBJF_ANGLE + 4, mu_obj_f32(o, MU_OBJF_ANGLE + 4)', 'MU_OBJF_ANGLE + 8, mu_obj_f32(o, MU_OBJF_ANGLE + 8)', 'ga_move'),
    ('gray_aida.c', 'MU_OBJF_ALPHA, 0.6f', 'MU_OBJF_ALPHA, 0.5f', 'ga_move'),
    ('gray_aida.c', '{6, 7, 8, 12, 13, 17}', '{6, 7, 8, 12, 13, 16}', 'ga_visual'),
    ('gray_aida.c', '{-3, -1, 0}', '{-3, -1, 1}', 'ga_visual'),
    ('gray_aida.c', '{5.5f, 4.5f, 4.0f, 4.5f, 4.0f, 4.0f}', '{5.5f, 4.5f, 4.0f, 4.5f, 4.0f, 4.5f}', 'ga_visual'),
    ('gray_aida.c', '{6.0f, 5.5f, 5.0f, 5.5f, 5.0f, 5.0f}', '{6.0f, 5.5f, 5.5f, 5.5f, 5.0f, 5.0f}', 'ga_visual'),
    ('gray_aida.c', 'k ? rest : first', 'k > 1 ? rest : first', 'ga_visual'),
    ('gray_aida.c', 'wv_sprite(i, 0x7f26, pos, 3.0f, dim, log)', 'wv_sprite(i, 0x7f26, pos, 2.5f, dim, log)', 'ga_visual'),
    ('gray_aida.c', 'rnd(c) % 2 == 0', 'rnd(c) % 2 == 1', 'ga_visual'),
    ('gray_aida.c', '0x801c, 8', '0x801c, 2', 'ga_visual'),
    ('gray_aida.c', 'rnd(c) % 3 == 0', 'rnd(c) % 4 == 0', 'ga_visual'),
    ('gray_aida.c', '{0.01f, 0.03f, 0.05f}', '{0.01f, 0.03f, 0.06f}', 'ga_visual'),
    ('gray_aida.c', 'for (int k = 0; k < 10; ++k)\n            wv_particle', 'for (int k = 0; k < 9; ++k)\n            wv_particle', 'ga_visual'),
    ('gray_aida.c', '    if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2)\n        for', '    if (1)\n        for', 'ga_visual'),
    ('gray_aida.c', 't >= 0 && t < 10', 't >= 0 && t <= 10', 'ga_visual'),
    ('gray_aida.c', 'one, 3);', 'one, 2);', 'ga_visual'),
    ('gray_aida.c', 'wb_scroll(time, 100000, 0.00005f)', 'wb_scroll(time, 100000, 0.00004f)', 'ga_visual'),
    ('gray_aida.c', '(float)(wb_int(time) % 100000) * 0.0002f', '(float)(wb_int(time) % 10000) * 0.0002f', 'ga_visual'),
    ('gray_aida.c', 'wb_arg(wb_event(log, MU_WR_STREAM, i), 0xff);', '', 'ga_visual'),
    ('gray_aida.c', 'wv_mesh(o, i, 0, 2,', 'wv_mesh(o, i, 0, 0,', 'ga_visual'),
    ('gray_aida.c', '0x7f42, 6, light, 0', '0x7f42, 6, light, 1', 'ga_visual'),
    ('gray_aida.c', 'memcpy(o + MU_OBJF_LIGHT, light, sizeof light);\n        wv_particle', 'wv_particle', 'ga_visual'),
    ('gray_aida.c', 'rnd(c) % 5 == 1 && t >= 0 && t < 30', 'rnd(c) % 5 == 1 && t >= 0 && t <= 30', 'ga_visual'),
    ('gray_aida.c', 'rnd(c) % 5 == 1 &&', 'rnd(c) % 5 == 0 &&', 'ga_visual'),
    ('gray_aida.c', 'wb_int(mu_obj_f32(o, MU_OBJF_SCALE))', 'wb_int(mu_obj_f32(o, MU_OBJF_SCALE) + 0.5f)', 'ga_visual'),
    ('gray_aida.c', 'time * 0.0017f', 'time * 0.0016f', 'ga_visual'),
    ('gray_aida.c', 'b + 0.2f}', 'b + 0.25f}', 'ga_visual'),
    ('gray_aida.c', 'wb_float(e, 1.3f)', 'wb_float(e, 1.2f)', 'ga_visual'),
    ('gray_aida.c', 'if (!o || !present)\n        return 0;\n    const float one', 'if (!o || present < 0)\n        return 0;\n    const float one', 'ga_visual'),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=1000)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--only', action='append')
    ap.add_argument('--output')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    lib = bind(v.Library(v.build_library(ROOT / 'reconstructed')))
    names = [n for n in BODIES if not a.only or n in a.only]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()}, 'families': {}, 'mutants': []}
    for name in names:
        r = report['families'][name] = family(machine, lib, name, a.cases)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, r['examples'][:1], flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-r-') as tmp:
            for n, (file, old, new, name) in enumerate(MUTANTS):
                if name not in names:
                    continue
                dest = Path(tmp) / str(n)
                for directory in ('objects', 'terrain', 'model-codec', 'record-math', 'movement'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__'))
                p = dest / 'objects' / file
                s = p.read_text()
                assert s.count(old) == 1, (file, old)
                p.write_text(s.replace(old, new, 1))
                mutated = bind(v.Library(v.build_library(dest)))
                r = family(machine, mutated, name, a.cases)
                m = {'family': name, 'file': file, 'change': new, 'detected': r['mismatch_count'],
                     'stopped': r['stopped']}
                report['mutants'].append(m)
                print('mutant', m, flush=True)
                shutil.rmtree(dest)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
