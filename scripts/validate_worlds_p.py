#!/usr/bin/env python3
"""Old Kethotum, Burning Kethotum and Bloody Tarkan primary methods against original instructions, with
compiled mutants. The clamped AddTerrainLight 0x016caeae of Bloody Tarkan is a tenth family."""
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
BODIES = {'ok_create': (0xe3a4dc, 0xe3a719), 'ok_move': (0xe3a719, 0xe3ae5e), 'ok_visual': (0xe3c137, 0xe3c739),
          'bk_create': (0xd9381e, 0xd93b31), 'bk_move': (0xd93b31, 0xd94eef), 'bk_visual': (0xd97186, 0xd97384),
          'bt_create': (0xd9a022, 0xd9a0ad), 'bt_move': (0xd9a0ad, 0xd9a2ed), 'bt_visual': (0xd9ac33, 0xd9ac50),
          'bt_clamped_light': (0x16caeae, 0x16cb08d)}
WORLD = {'ok': 0x87, 'bk': 0x88, 'bt': 0x8c}
EDGES = [-2147483648, -1, 0, 2147483647]
TYPES = {
    'ok_create': [0xf, 0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x26, 0x29, 0x3b, 0x5a, 0x5c, 0x66, 0x6a, 0x74, 0x77, 0x81,
                  0x87, 0x89, 0x8a, 0x9f, 0xa0, 0xa5, 0xaa, 0xab, 0x88, 2],
    'bk_create': [2, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x26, 0x29, 0x3b, 0x5a, 0x5c, 0x66, 0x6a, 0x6c, 0x74, 0x77,
                  0x81, 0x86, 0x87, 0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9f, 0xa0, 0xaa, 0xab, 0xb3, 0xb5, 0xf],
    'bt_create': [0x10, 0x11, 0x12, 0x44, 0x45, 0x46, 0x50, 0x51, 0x52, 0x5f, 0x64, 0x65, 0x66, 0x13],
    'ok_move': [0x16, 0x17, 0x28, 0x29, 0x5c, 0x74, 0x77, 0x81, 0xa0, 0xa5, 0x19, 0xb5, 0x10],
    'bk_move': [0x16, 0x19, 0x28, 0x29, 0x5c, 0x74, 0x77, 0x81, 0xa0, 0xa5, 0xb5, 0xb5, 0xb5, 0x17, 0x10],
    'bt_move': [0x13, 0x51, 0x12, 0x50, 0x52],
    'ok_visual': [0xf, 0x10, 0xa5, 0xa5, 0x11, 0xe],
    'bk_visual': [0xa5, 0xa4, 0xf, 0x10],
    'bt_visual': [0x13, 0x51, 0],
}
NEEDS_MODEL = {0x16, 0x29, 0x5c, 0x74, 0x77, 0x81, 0xb5}
EIN = ['Data\\Effect\\fire09-red01.ein', 'Data\\Effect\\Sparkle21-red01.ein', 'Data\\Effect\\smoke17-red01.ein',
       'Data\\Effect\\twinkle10-red02.ein']
FRAME_TIME, MANAGER, LIGHT_BUFFER = 0x01cf103c, 0x41006000, 0x42000000
MODEL_ACTIONS = 8
BONE = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))


class Model(C.Structure):
    _fields_ = [('action_count', C.c_int32), ('speed', C.POINTER(C.c_float)), ('keys', C.POINTER(C.c_int16))]


class Inputs(C.Structure):
    _fields_ = [('world', C.c_int32), ('hero', C.c_float * 3), ('frame_time', C.c_float),
                ('model', C.POINTER(Model)), ('rand_fn', v.RAND_FN), ('context', C.c_void_p),
                ('has_effects', C.c_uint8), ('effects_valid', C.c_uint8)]


def bind(lib):
    d = lib.dll
    for name in ('mu_old_kethotum_create', 'mu_burning_kethotum_create'):
        getattr(d, name).argtypes = [C.c_void_p, C.c_int32, C.POINTER(Model), v.RAND_FN, C.c_void_p]
    d.mu_bloody_tarkan_create.argtypes = [C.c_void_p, C.c_int32]
    for name in ('mu_old_kethotum_move', 'mu_burning_kethotum_move'):
        getattr(d, name).argtypes = [C.c_void_p, C.c_int32, C.POINTER(Inputs), C.POINTER(v.Log)]
    d.mu_bloody_tarkan_move.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_float, v.RAND_FN, C.c_void_p,
                                        C.POINTER(v.Log)]
    d.mu_old_kethotum_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.c_float, v.RAND_FN, BONE, C.c_void_p,
                                         C.POINTER(v.Log)]
    d.mu_burning_kethotum_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, v.RAND_FN, C.c_void_p, C.POINTER(v.Log)]
    d.mu_bloody_tarkan_visual.argtypes = [C.c_void_p, C.c_int]
    d.mu_bloody_tarkan_add_light_clamped.argtypes = [C.c_float, C.c_float, C.POINTER(C.c_float), C.c_int32,
                                                     C.POINTER(C.c_float)]
    return lib


def model_case(g, need):
    count = g.choice([2, 3, 4, 4, 5, 6, 8] + ([0, 1] if not need else []))
    speeds = [v.f32(g.choice([0.3, 0.25, 0.5, g.uniform(0.01, 1.5)])) for _ in range(MODEL_ACTIONS)]
    keys = [g.choice([2, 5, 8, 10, 12, 20, g.randrange(-3, 40)]) for _ in range(MODEL_ACTIONS)]
    return count, speeds, keys


def model_regions(count, speeds, keys, writable):
    model = bytearray(0x100)
    struct.pack_into('<hxxxxxxxxI', model, 0x26, count, v.ACTIONS)
    table = bytearray(16 * MODEL_ACTIONS)
    for k in range(MODEL_ACTIONS):
        struct.pack_into('<fh', table, 16 * k + 4, speeds[k], keys[k])
    return [am.defined_region('model', v.MODEL, bytes(model), writable=False),
            am.defined_region('actions', v.ACTIONS, bytes(table), writable=writable)]


def c_model(count, speeds, keys):
    sp = (C.c_float * MODEL_ACTIONS)(*speeds)
    ks = (C.c_int16 * MODEL_ACTIONS)(*keys)
    m = Model(count, C.cast(sp, C.POINTER(C.c_float)), C.cast(ks, C.POINTER(C.c_int16)))
    m._keep = (sp, ks)
    return m


def actions_speeds(region):
    return [struct.unpack_from('<f', region, 16 * k + 4)[0] for k in range(MODEL_ACTIONS)]


def common_stubs(calls, rnd, has_model):
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

    def light(address):
        def stub(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((address, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0
        return stub

    def effect(m):
        a = [m.argument(k) for k in range(14)]
        assert a[6:10] == [0xffffffff, 0, 0, 0] and a[10] == 0 and a[11:] == [0xffffffff, 0, 0]
        calls.append((0x13c0eaa, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                     (a[4], int(a[5] == v.OBJECTS), a[10]))
        return 0

    def sound(m):
        calls.append((0xa6ac96, 0) + tuple(m.argument(k) for k in range(3)))
        return 0
    return {0x168fafd: particle, 0x1692eb7: sprite, 0x16cacfc: light(0x16cacfc), 0x16caeae: light(0x16caeae),
            0x13c0eaa: effect, 0xa6ac96: sound, 0x1989721: lambda m: rnd(), 0x966cc4: lambda m: v.FAKE,
            0xeaa8cf: lambda m: (v.MODEL if has_model else 0, 4)}


def ein_stubs(calls, has_effects, valid):
    names = {}

    def string(m):
        names[m.uc.reg_read(UC_X86_REG_ECX)] = m.cstring(m.argument(0))
        return (m.uc.reg_read(UC_X86_REG_ECX), 4)

    def create(m):
        a = [m.argument(k) for k in range(12)]
        assert m.uc.reg_read(UC_X86_REG_ECX) == MANAGER and a[5] == 0 and a[7] == 0 and a[11] == 0
        assert struct.unpack('<H', bytes(m.uc.mem_read(a[6], 2)))[0] == 0
        k = EIN.index(names[a[1]])
        calls.append((0xa797a0, 0, k) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) + (a[4],))
        m.uc.mem_write(a[0], struct.pack('<II', 0x5000 + k if valid >> k & 1 else 0, 0))
        return (a[0], 0x30)

    def attach(m):
        a = [m.argument(k) for k in range(5)]
        assert m.uc.reg_read(UC_X86_REG_ECX) == v.OBJECTS
        calls.append((0x129f9c6, 0, m.read32(a[0]) - 0x5000) + tuple(a[1:]))
        return (0, 0x14)
    this = lambda m: m.uc.reg_read(UC_X86_REG_ECX)
    return {0xd99e3f: lambda m: int(has_effects), 0x94997e: string, 0x95e433: this, 0xaee554: lambda m: MANAGER,
            0xa797a0: create, 0x129f9c6: attach, 0x965b01: lambda m: 0, 0x8e83a0: lambda m: 0,
            0x95eda9: lambda m: 0}


def object_case(g, typ):
    raw = bytearray(v.poison_object(g))
    v.put_i(raw, 0x5c, typ)
    v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 1.15, 1.1499999, 1.35, 1.3499999, 1.3, 1.32, 2.0, 0.5, -1.0, g.uniform(0, 3)])))
    v.put_f(raw, 0x158, v.f32(g.uniform(0, 25600)), v.f32(g.uniform(0, 25600)), v.f32(g.uniform(-100, 500)))
    v.put_f(raw, 0x164, *(v.f32(g.uniform(-360, 360)) for _ in range(3)))
    v.put_f(raw, 0xb0, v.f32(g.uniform(-2, 2)))
    return raw


def create_family(machine, lib, name, cases):
    g = random.Random('worlds-p-' + name)
    tally = v.Tally(name)
    prefix = name.split('_')[0]
    fn = {'ok': lib.dll.mu_old_kethotum_create, 'bk': lib.dll.mu_burning_kethotum_create,
          'bt': lib.dll.mu_bloody_tarkan_create}[prefix]
    types = TYPES[name] + EDGES
    for n in range(cases):
        typ = types[n % len(types)]
        world = [WORLD[prefix]] * 4 + [0x87, 0x88, 0x8c, 0x86, 0]
        world = world[(n // len(types)) % len(world)]
        null = n % 41 == 40
        has_model = typ in NEEDS_MODEL or n % 5 != 0
        count, speeds, keys = model_case(g, typ in NEEDS_MODEL)
        raw = object_case(g, typ)
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw))] +
                                model_regions(count, speeds, keys, True))
        result = v.run(machine, BODIES[name][0], [0 if null else v.OBJECTS], regs,
                       common_stubs([], rnd, has_model), ecx=v.FAKE, cleanup=4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        obj = None if null else co
        if prefix == 'bt':
            al = fn(obj, world)
            cs = speeds
        else:
            cm = c_model(count, speeds, keys)
            al = fn(obj, world, C.byref(cm) if has_model else None, v.RAND_FN(lambda ctx: crnd()), None)
            cs = [cm.speed[k] for k in range(MODEL_ACTIONS)]
        guest = actions_speeds(result['regions']['actions'])
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        same_speeds = [v.bits(x) for x in guest] == [v.bits(x) for x in cs]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('model' if has_model else 'no model')
        tally.add(not diff and al == (result['eax'] & 255) and same_speeds and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255, 'c_al': al,
                   'speeds': guest[:4], 'c_speeds': cs[:4], 'rng': rnd.seed == crnd.seed})
    return tally.report()


THRESHOLDS = [300.0, 400.0, 800.0, 1000.0, 1200.0, 1300.0]


TYPE_THRESHOLD = {0x17: 800.0, 0x19: 800.0, 0x28: 1300.0, 0xa0: 400.0, 0xa5: 400.0, 0x16: 1000.0, 0x29: 1000.0,
                  0x5c: 1000.0, 0x74: 1000.0, 0x77: 300.0, 0x81: 300.0, 0xb5: 1200.0}


def hero_case(g, raw, typ):
    x, y = struct.unpack_from('<2f', raw, 0x158)
    r = g.random()
    if r < 0.3:   # exact distances: integer positions along one axis
        x, y = float(g.randrange(2000, 23000)), float(g.randrange(2000, 23000))
        v.put_f(raw, 0x158, x, y)
        d = TYPE_THRESHOLD.get(typ, g.choice(THRESHOLDS)) + g.choice([-1.0, 0.0, 0.0, 1.0])
        return ((x + d, y, 0.0), (x - d, y, 0.0), (x, y + d, 0.0), (x, y - d, 0.0))[g.randrange(4)]
    if r < 0.6:
        d = g.choice(THRESHOLDS) + g.choice([-0.01, 0.0, 0.01, -5.0, 5.0])
    else:
        d = g.uniform(0, 2000)
    a = g.uniform(0, 6.283185307)
    import math
    return (v.f32(x + d * math.cos(a)), v.f32(y + d * math.sin(a)), 0.0)


def move_family(machine, lib, name, cases):
    g = random.Random('worlds-p-' + name)
    tally = v.Tally(name)
    prefix = name.split('_')[0]
    types = TYPES[name] + EDGES
    for n in range(cases):
        typ = types[n % len(types)]
        worlds = [WORLD[prefix]] * 5 + [0x87, 0x88, 0x8c, 0]
        world = worlds[(n // len(types)) % len(worlds)]
        null = n % 43 == 42
        has_model = n % 7 != 3
        count, speeds, keys = model_case(g, True)
        raw = object_case(g, typ)
        action = g.choice([0, 0, 1, 1, 2, 2, 3, 3, 5])
        dt = v.f32(g.choice([0.0, 0.0, 0.1, 0.25, 1.0, 1.5, g.uniform(0, 2.5)]))
        s = v.f32(speeds[action] + dt)
        f = g.random()
        if f < 0.45:
            frame = v.f32(v.f32(keys[action] - (1 if prefix == 'bk' and typ == 0xb5 else 0)) - (s if g.random() < 0.7 else 0)
                          + g.choice([-0.01, 0.0, 0.01, -1.0, 1.0]))
        else:
            frame = v.f32(g.choice([0.0, 0.5, 0.86, 0.85, 1.0, 3.0, 3.5, 7.0, 7.5, 8.0, g.uniform(0, 25)]))
        struct.pack_into('<HH', raw, 0x2a, action, g.choice([0, 1, 2]))
        v.put_f(raw, 0xd0, frame, v.f32(g.uniform(0, 10)))
        swings = g.randrange(0, 6)
        v.put_i(raw, 0x30, swings)
        v.put_i(raw, 0x34, swings + g.choice([0, 0, -1, 1, 3]))
        v.put_f(raw, 0xc8, v.f32(g.choice([0.0, 0.05, 0.1, 0.5, 0.65, 0.9, 1.0, g.uniform(-0.5, 1.5)])))
        if typ == 0x5c and g.random() < 0.5:
            v.put_f(raw, 0xd0, v.f32(g.choice([0.85, 0.86, 0.9, 1.0, 0.84])))
        if typ == 0xb5 and g.random() < 0.5:
            last = keys[action] - 1
            v.put_f(raw, 0xd0, v.f32(g.choice([last / 4.5, last / 5.0, last / 3.0, 3.0, 7.0, 7.5, 8.0])))
            v.put_f(raw, 0xc8, v.f32(g.choice([0.65, 0.65 - dt * 0.5, 0.1, 1.0, 1.0 - dt * 0.1])))
        hero = hero_case(g, raw, typ)
        has_effects = g.random() < 0.5
        valid = 15 if g.random() < 0.6 else g.randrange(0, 16)
        time = v.f32(g.choice([0.0, -0.0, 1000.0, g.uniform(-1e6, 1e6)]))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []
        stubs = common_stubs(calls, rnd, has_model)
        stubs.update(ein_stubs(calls, has_effects, valid))
        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('frame-time', FRAME_TIME, v.pack_f(dt), writable=False),
            am.defined_region('hero-pointer', v.HERO_PTR, struct.pack('<I', v.HERO), writable=False),
            am.defined_region('hero', v.HERO + 0x33ac, v.pack_f(*hero), writable=False)] +
            model_regions(count, speeds, keys, False))
        result = v.run(machine, BODIES[name][0], [0 if null else v.OBJECTS], regs, stubs, ecx=v.FAKE, cleanup=4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        obj = None if null else co
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        if prefix == 'bt':
            al = lib.dll.mu_bloody_tarkan_move(obj, 0, world, time, fn, None, C.byref(log))
        else:
            cm = c_model(count, speeds, keys)
            inputs = Inputs(world, (C.c_float * 3)(*hero), dt, C.pointer(cm) if has_model else None, fn, None,
                            int(has_effects), valid)
            move = lib.dll.mu_old_kethotum_move if prefix == 'ok' else lib.dll.mu_burning_kethotum_move
            al = move(obj, 0, C.byref(inputs), C.byref(log))
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('action %d' % action)
        tally.count('events', len(calls))
        for c in calls:
            tally.count('call %#x' % c[0])
        events = v.log_events(log)
        tally.add(not diff and al == (result['eax'] & 255) and calls == events and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'action': action, 'diff': diff[:8],
                   'al': result['eax'] & 255, 'c_al': al, 'calls': calls[:6], 'c': events[:6],
                   'rng': rnd.seed == crnd.seed})
    return tally.report()


def visual_family(machine, lib, name, cases):
    g = random.Random('worlds-p-' + name)
    tally = v.Tally(name)
    prefix = name.split('_')[0]
    types = TYPES[name] + EDGES
    for n in range(cases):
        typ = types[n % len(types)]
        present = n % 9 != 4
        has_model = n % 6 != 5
        null = n % 47 == 46
        raw = object_case(g, typ)
        v.put_i(raw, 0x64, g.choice([0, 300, 2700, g.randrange(-100000, 100000)]))
        time = v.f32(g.choice([0.0, -0.0, 1000.0, 2999.0, 3000.0, -2999.5, 3926.99072265625, g.uniform(-1e6, 1e6)]))
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
        stubs = common_stubs(calls, rnd, has_model)
        stubs[0x12b6ef1] = bone
        regs = v.global_regions(WORLD[prefix], 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                                  am.defined_region('time', v.TIME, v.pack_f(time), writable=False)])
        result = v.run(machine, BODIES[name][0], [0 if null else v.OBJECTS, v.FAKE if present else 0], regs, stubs,
                       ecx=v.FAKE, cleanup=8)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
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
        if prefix == 'ok':
            al = lib.dll.mu_old_kethotum_visual(obj, 0, present, time, fn, c_bone if has_model else BONE(), None,
                                                C.byref(log))
        elif prefix == 'bk':
            al = lib.dll.mu_burning_kethotum_visual(obj, 0, present, fn, None, C.byref(log))
        else:
            al = lib.dll.mu_bloody_tarkan_visual(obj, present)
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        events = v.log_events(log)
        tally.count('type ' + str(typ))
        tally.count('events', len(calls))
        tally.add(not diff and al == (result['eax'] & 255) and calls == events and rnd.seed == crnd.seed and
                  bones == cbones,
                  {'case': n, 'type': typ, 'diff': diff[:8], 'al': result['eax'] & 255, 'c_al': al,
                   'calls': calls[:4], 'c': events[:4], 'bones': bones[:3], 'cbones': cbones[:3],
                   'rng': rnd.seed == crnd.seed})
    return tally.report()


def light_family(machine, lib, name, cases):
    g = random.Random('worlds-p-' + name)
    tally = v.Tally(name)
    size = 256 * 256 * 3
    base = [v.f32(g.uniform(-0.5, 1.5)) for _ in range(size)]
    packed = struct.pack('<%df' % size, *base)
    for n in range(cases):
        r = g.random()
        if r < 0.1:
            x, y = v.f32(g.choice([-150.0, -1.0, 0.0, 25599.0, 25700.0])), v.f32(g.uniform(-200, 25800))
        else:
            x, y = v.f32(g.uniform(0, 25600)), v.f32(g.uniform(0, 25600))
        rng = g.choice([0, 1, 2, 3, 3, 3, 5])
        light = [v.f32(g.choice([0.0, 1.0, -1.0, g.uniform(-1.5, 1.5)])) for _ in range(3)]
        regs = [am.defined_region('light', 0x41007000, v.pack_f(*light), writable=False),
                am.defined_region('buffer', LIGHT_BUFFER, packed),
                am.defined_region('crt-math-mode', v.CRT_MATH_MODE, struct.pack('<I', 0))]
        result = v.run(machine, BODIES[name][0], [v.bits(x), v.bits(y), 0x41007000, rng, LIGHT_BUFFER], regs, {})
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n}, stop)
            continue
        buf = (C.c_float * size).from_buffer_copy(packed)
        lib.dll.mu_bloody_tarkan_add_light_clamped(x, y, (C.c_float * 3)(*light), rng, buf)
        same = bytes(buf) == result['regions']['buffer']
        tally.count('range %d' % rng)
        tally.count('changed' if result['regions']['buffer'] != packed else 'unchanged')
        tally.add(same, {'case': n, 'x': x, 'y': y, 'range': rng})
    return tally.report()


def family(machine, lib, name, cases):
    kind = name.split('_', 1)[1]
    if kind == 'clamped_light':
        return light_family(machine, lib, name, cases)
    return {'create': create_family, 'move': move_family, 'visual': visual_family}[kind](machine, lib, name, cases)


MUTANTS = [
    ('old_kethotum.c', 'if (world != 0x87', 'if (world != 0x86', 'ok_create'),
    ('old_kethotum.c', 'in->world != 0x87', 'in->world != 0x86', 'ok_move'),
    ('old_kethotum.c', 'm->speed[k] = 0.3f', 'm->speed[k] = 0.31f', 'ok_create', 'worlds_p_internal.h'),
    ('old_kethotum.c', 't >= 0xa0 && t <= 0xaa', 't >= 0xa0 && t <= 0xa9', 'ok_create'),
    ('old_kethotum.c', 'case 0x15: case 0x3b:', 'case 0x14: case 0x3b:', 'ok_create'),
    ('old_kethotum.c', 'rnd(c) % 10 * 300', 'rnd(c) % 10 * 301', 'ok_create'),
    ('old_kethotum.c', 'm->speed[1] * 1.03f', 'm->speed[1] * 1.02f', 'ok_create'),
    ('old_kethotum.c', '0x557', '0x556', 'ok_move'),
    ('old_kethotum.c', '- 0.02f', '- 0.03f', 'ok_move'),
    ('old_kethotum.c', '1000.0f >= wp_distance', '1000.0f > wp_distance', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', 'f > 0.85f && 1.0f > f', 'f >= 0.85f && 1.0f > f', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', '% 10 + 15);\n            mu_obj_set_i32(o, WP_SWINGS, 0)', '% 10 + 16);\n            mu_obj_set_i32(o, WP_SWINGS, 0)', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', 'if (d >= 300.0f)', 'if (d > 300.0f)', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', 'wp_set_action(o, m, 3)', 'wp_set_action(o, m, 2)', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', 'action >= m->action_count', 'action > m->action_count', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', 'const float s = m->speed[a] + in->frame_time;\n    if', 'const float s = m->speed[a];\n    if', 'ok_move', 'worlds_p_internal.h'),
    ('old_kethotum.c', '% 3000)', '% 3001)', 'ok_visual'),
    ('old_kethotum.c', 'bone(c, 4, zero, pos)', 'bone(c, 3, zero, pos)', 'ok_visual'),
    ('old_kethotum.c', 'rnd(c) % 7 == 0', 'rnd(c) % 6 == 0', 'ok_visual'),
    ('old_kethotum.c', '1.5f + wave * 0.1f', '1.5f + wave * 0.2f', 'ok_visual'),
    ('old_kethotum.c', '{5, 6, 7, 11, 14, 15}', '{5, 6, 7, 11, 14, 16}', 'ok_visual'),
    ('old_kethotum.c', 'wave < 0.0f ? -wave : wave', 'fabsf(wave)', 'ok_visual'),
    ('old_kethotum.c', '* 0.0002 *', '* 0.0003 *', 'ok_visual'),
    ('old_kethotum.c', 'rnd(c) % 100 == 0', 'rnd(c) % 99 == 0', 'ok_visual'),
    ('burning_kethotum.c', 'if (world != 0x88', 'if (world != 0x87', 'bk_create'),
    ('burning_kethotum.c', 'in->world != 0x88', 'in->world != 0x87', 'bk_move'),
    ('burning_kethotum.c', 'case 0x86: case 0x87: case 0xb3:', 'case 0x86: case 0x88: case 0xb3:', 'bk_create'),
    ('burning_kethotum.c', '(rnd(c) % 18 + 1) * 10', '(rnd(c) % 18 + 1) * 11', 'bk_create'),
    ('burning_kethotum.c', 'm->speed[1] * 0.9f', 'm->speed[1] * 0.8f', 'bk_create'),
    ('burning_kethotum.c', '0x558', '0x557', 'bk_move'),
    ('burning_kethotum.c', '1.15f > scale', '1.15f >= scale', 'bk_move'),
    ('burning_kethotum.c', '1.35 > (double)scale', '1.3 > (double)scale', 'bk_move'),
    ('burning_kethotum.c', '{35.0f, 50.0f, 50.0f, 200.0f}', '{35.0f, 50.0f, 60.0f, 200.0f}', 'bk_move'),
    ('burning_kethotum.c', '(in->effects_valid & 15) == 15', '(in->effects_valid & 7) == 7', 'bk_move'),
    ('burning_kethotum.c', 'mu_obj_f32(o, 0xc8) > 0.65f', 'mu_obj_f32(o, 0xc8) >= 0.65f', 'bk_move'),
    ('burning_kethotum.c', 'last / 5.0f', 'last / 4.0f', 'bk_move'),
    ('burning_kethotum.c', 'dt * 0.4f', 'dt * 0.5f', 'bk_move'),
    ('burning_kethotum.c', 'mu_obj_i32(o, WP_SWINGS) >= mu_obj_i32(o, WP_SWING_LIMIT)', 'mu_obj_i32(o, WP_SWINGS) > mu_obj_i32(o, WP_SWING_LIMIT)', 'bk_move'),
    ('burning_kethotum.c', 'mu_obj_set_f32(o, MU_OBJF_FRAME, s);', 'mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);', 'bk_move'),
    ('burning_kethotum.c', '> 3.0f && 1200.0f > wp_distance', '> 3.0f && 1200.0f >= wp_distance', 'bk_move'),
    ('burning_kethotum.c', 'MU_OBJF_SCALE), warm', 'MU_OBJF_SCALE) * 1.0f + 0.1f, warm', 'bk_visual'),
    ('burning_kethotum.c', 'wv_particle(o, i, 0x806e, 4', 'wv_particle(o, i, 0x806e, 3', 'bk_visual'),
    ('bloody_tarkan.c', 'case 0x11: case 0x12:', 'case 0x10: case 0x12:', 'bt_create'),
    ('bloody_tarkan.c', 'case 0x5f: case 0x64:', 'case 0x5e: case 0x64:', 'bt_create'),
    ('bloody_tarkan.c', 's * 0.04f, 3)', 's * 0.05f, 3)', 'bt_move'),
    ('bloody_tarkan.c', '* 100.0f + time) * 0.002f', '* 100.0f + time) * 0.003f', 'bt_move'),
    ('bloody_tarkan.c', '* 0.15f + 0.65f', '* 0.15f + 0.66f', 'bt_move'),
    ('bloody_tarkan.c', 'MU_OBJF_BLEND_MESH, 0)', 'MU_OBJF_BLEND_MESH, 1)', 'bt_move'),
    ('bloody_tarkan.c', '(void)o; (void)present;\n    return 0;', '(void)o;\n    return present != 0;', 'bt_visual'),
    ('bloody_tarkan.c', 'else if (p[k] > 1.0f)', 'else if (p[k] > 1.5f)', 'bt_clamped_light'),
    ('bloody_tarkan.c', '(rf - (float)sqrt((double)d)) / rf', '(rf - (float)sqrt((double)d)) / (rf + 0.5f)', 'bt_clamped_light'),
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
        with tempfile.TemporaryDirectory(prefix='worlds-p-') as tmp:
            for n, entry in enumerate(MUTANTS):
                source, old, new, name = entry[:4]
                file = entry[4] if len(entry) > 4 else source
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
