#!/usr/bin/env python3
"""World-110 (Nars) and Arca War (92, 96, 101, 111) primary slots against pinned instructions.

Nars create/move/visual (predicate 0x00e2602d: worlds 110 and 111), the visual split into four families by type
(fire, glow, emit, orbit), and the Arca War class 0x01aa6154: its base world 0x00d7b225 (with the class-list
predicate 0x00d806b0 over a harness handler whose world vector holds the registered 92, 96, 101, 111), create,
move and visual. Full AL (EAX for the base world), all OBJECT bytes, the model's BodyOrigin/scale and action
table, ordered recorded calls with their constant arguments asserted and the final MSVC RNG are compared.

Recording boundaries: rand, AddTerrainLight, CreateParticle, CreateSprite, CreateEffect, the model container,
Animation, TransformPosition, the class registry 0x00ea594b/0x00ea4679 (a harness base handler whose vtable
slots 0x2c/0x30/0x34 record the forward and return a sampled AL) and 0x0095c652 (the world-92 class lookup;
0x00d7b373 then runs as original code). Executed as original code: the predicates and the class-list vector
helpers, SetAction 0x012affa4, the action lookup 0x00eaaa44, the CRT sine wrapper, fabs 0x0184f8ff,
AngleMatrix 0x00cff32a, VectorRotate 0x00d000ad, the vector accessors and the sprite descriptor.
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
import validate_worlds_q as q
import pins
from unicorn.x86_const import UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
NARS_VISUAL = (0xe26ae7, 0xe28bb2)   # through the custom-render slot
BODIES = {'nars_create': (0xe260f0, 0xe26668), 'nars_move': (0xe26668, 0xe26ae7),   # create with its jump table
          'nars_visual_fire': NARS_VISUAL, 'nars_visual_glow': NARS_VISUAL, 'nars_visual_emit': NARS_VISUAL,
          'nars_visual_orbit': NARS_VISUAL,
          'arca_base': (0xd7b225, 0xd7b24b), 'arca_create': (0xd7bd7d, 0xd7be29), 'arca_move': (0xd7be29, 0xd7be80),
          'arca_visual': (0xd7be80, 0xd7c02e)}
EXTREMES = [-2147483648, -1, 2147483647, 1000, 0x59b, 0x88a]
ALL_TYPES = list(range(-1, 161)) + EXTREMES
GROUPS = {'nars_create': [0, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27, 28, 29, 30, 31, 32,
                          33, 34, 37, 38, 39, 59, 60, 64, 66, 79, 85, 87, 134, 142, 146, 150, 154],
          'nars_move': [1, 2, 1, 2, 4, 116, 146, 134, 77, 3, 78],
          'nars_visual_fire': [4, 116, 134, 146], 'nars_visual_glow': [11, 133, 85, 87],
          'nars_visual_emit': [10, 14, 15, 29, 30, 39, 59, 66, 79], 'nars_visual_orbit': [25, 26, 32]}
NARS_WORLDS = [0, 92, 109, 110, 111, 112]
OPEN = {10: (12, 0), 14: (8, 0), 79: (8, 0), 15: (6, 0), 29: (6, 0), 39: (6, 0), 59: (6, 0), 66: (6, 0), 30: (3, 0),
        25: (5, 0), 26: (5, 0), 85: (7, 0)}
COOKIE = 0x01cf65c0
POSE = 0x00e264a1   # MU_NARS_POSE
R2_EFFECT, CALL_EFFECT = 0x00e68c23, 0x013c0eaa
LIGHT = 0x16cacfc
ARCA_WORLDS = [92, 96, 101, 111]
ARCA_SIBLINGS = [0, 91, 93, 95, 97, 100, 102, 110, 112, 145]
ARCA_TYPES = [0x59b, 0x59b, 0x88a, 0x88b, 0x88c, 0x88d, 0x88e, 0x889, 0x88f, 0x59a, 0x59c, 0, 4, 9, 85, 134]
STAGE_LIGHT = [(1.0, 0.37, 0.66), (1.0, 0.37, 0.66), (0.58, 1.0, 0.86), (0.08, 1.0, 0.86), (0.6, 0.9, 0.95),
               (0.88, 0.4, 0.86)]   # handler +0x40, constructor 0x00d7a185
ARCA, REGISTRY, BASE, LIST = 0x41020000, 0x41021000, 0x41022000, 0x41023000
CLASS92 = 0x41024000   # what the 0x0095c652 stub returns (0x00d7b373 ignores it)
FORWARD_FN = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int32, C.c_int32)


def bind(lib):
    d = lib.dll
    P, I, In, L = C.c_void_p, C.c_int32, C.POINTER(q.Inputs), C.POINTER(v.Log)
    for name in ('create', 'move', 'visual'):
        getattr(d, 'mu_nars_' + name).argtypes = [P, I, In, L]
        getattr(d, 'mu_nars_' + name).restype = C.c_int
    d.mu_nars_visual_bones.argtypes = [I]
    d.mu_arca_base_world.argtypes = [I]
    d.mu_arca_base_world.restype = C.c_int32
    d.mu_arca_create.argtypes = [P, I, I, FORWARD_FN, P]
    d.mu_arca_move.argtypes = [I, I, FORWARD_FN, P]
    d.mu_arca_visual.argtypes = [P, I, I, I, I, q.BONE_FN, P, FORWARD_FN, P, L]
    for name in ('create', 'move', 'visual'):
        getattr(d, 'mu_arca_' + name).restype = C.c_int
    return lib


def seed_for(g, modulus, value):
    while True:
        seed = g.getrandbits(32)
        if v.MsvcRand(seed)() % modulus == value:
            return seed


def time_sample(g):
    return v.f32(g.choice([0.0, -0.0, 1000.0, -1000.0, 2999.5, 3600.0, 1963.4954, 2147483520.0, 3e9, -1e12,
                           math.nan, g.uniform(-1e6, 1e6), g.uniform(0, 1e5), g.uniform(0, 7000)]))


def pick_type(g, name, n):
    if n % 3 != 2:
        return g.choice(GROUPS[name])
    return ALL_TYPES[(n // 3) % len(ALL_TYPES)] if n % 9 != 8 else g.randrange(-50, 400)


def nars_family(machine, lib, name, cases):
    g = random.Random('worlds-s2-' + name)
    tally = v.Tally(name)
    method = name.split('_')[1]
    for n in range(cases):
        typ = pick_type(g, name, n)
        world = 110 if n % 4 else NARS_WORLDS[(n // 4) % len(NARS_WORLDS)]
        if n % 4 == 1:
            world = 111
        present = True if method == 'visual' else n % 7 != 0
        count = g.choice([0, 1, 2, 3, 4, 4, 5, 8])
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        if method == 'create' and typ == 134:
            present = True   # the original writes the model without a test
        v.put_i(raw, 0x64, g.choice([-2, -1, 0, 0, 1, 1, 2, 5, 300, 2700, g.randrange(-5000, 5000)]))
        action = g.choice([0, 0, 1, 1, 2, 3, g.randrange(0, 10)])
        struct.pack_into('<HH', raw, 0x2a, action, g.randrange(4))
        v.put_f(raw, 0xd0, v.f32(g.choice([0.0, 0.5, 1.0, 2.0, 2.5, 4.0, 8.0, 23.5, 24.0, math.nan,
                                           g.uniform(-1, 30)])), v.f32(g.uniform(0, 10)))
        v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 0.0, -1.0, 2.5, 65535.9, 70000.0, 1e6, math.nan, -0.0,
                                           g.uniform(0, 4)])))
        v.put_f(raw, 0xb0, v.f32(g.choice([0.0, 0.25, -1.0, math.nan, g.uniform(-3, 3)])))
        if g.random() < 0.15:   # the band of type 32 reads (int)x
            v.put_f(raw, 0x158, v.f32(g.choice([math.nan, math.inf, -1.0, 3e9, 0.5, 2.0])))
        table = q.action_table(g, count)
        model = bytearray(0x100)
        struct.pack_into('<h', model, 0x26, count)
        struct.pack_into('<I', model, 0x30, v.ACTIONS)
        time = time_sample(g)
        seed = g.getrandbits(32)
        if method == 'visual' and typ in OPEN and g.random() < 0.6:
            seed = seed_for(g, *OPEN[typ])
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones, cbones = [], [], []

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6] in (0, v.OBJECTS) and a[7] == 0, a
            calls.append((q.PARTICLE, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0

        def sprite(m):
            a = [m.argument(k) for k in range(9)]
            assert a[4] == v.OBJECTS and a[6:8] == [0, 4] and v.read_vec(m, a[8]) == (1, 1, v.bits(1.0)), a
            calls.append((q.SPRITE, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) + (a[5], 1, 0, 4))
            return 0

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((LIGHT, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == 0 and a[6] == 0xffffffff and a[7] == 0 and a[9:] == [0, 0, 0xffffffff, 0, 0], a
            calls.append((R2_EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], 0, a[8]))
            return 0

        def animation(m):
            a = [m.argument(k) for k in range(8)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL
            assert a == [0x6fce398, struct.unpack_from('<I', raw, 0xd0)[0], struct.unpack_from('<I', raw, 0xd4)[0],
                         struct.unpack_from('<H', raw, 0x2c)[0], v.OBJECTS + 0x164, v.OBJECTS + 0x170, 0, 1], a
            calls.append((POSE, 0) + struct.unpack('<3I', bytes(m.uc.mem_read(v.MODEL + 0x78, 12))) +
                         struct.unpack('<I', bytes(m.uc.mem_read(v.MODEL + 0x74, 4))))
            return (0, 32)

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL and a[3] == 0, a
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + k * 0x30 and 0 <= k < 64, a
            local = tuple(struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12))))
            bones.append((k,) + tuple(v.bits(x) for x in local))
            m.uc.mem_write(a[2], v.pack_f(*q.position(k, local)))
            return (0, 16)

        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('isa', q.ISA, struct.pack('<I', 2 * (n % 2)), writable=False),
            am.defined_region('model', v.MODEL, bytes(model)),
            am.defined_region('actions', v.ACTIONS, bytes(table))])
        args = [v.OBJECTS] + ([v.MODEL] if method == 'visual' else [])
        stubs = {q.PARTICLE: particle, q.SPRITE: sprite, LIGHT: light, q.EFFECT: effect, q.BONE: bone,
                 0x12b5064: animation, 0x1989721: lambda m: rnd(), 0x966cc4: lambda m: v.FAKE,
                 0xeaa8cf: lambda m: (v.MODEL if present else 0, 4)}
        result = v.run(machine, BODIES[name][0], args, regs, stubs, ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        ctable = C.create_string_buffer(bytes(table), len(table))
        log = v.new_log()

        def actions_cb(ctx, t, out):
            out[0] = count
            return C.addressof(ctable) if present else None

        def bone_cb(ctx, k, local, out):
            local = tuple(local[:3])
            cbones.append((k,) + tuple(v.bits(x) for x in local))
            for qq, value in enumerate(q.position(k, local)):
                out[qq] = value
        inputs = q.Inputs(world, time, v.f32(0.1), 0, (C.c_float * 3)(), (C.c_int32 * 2)(), q.ACTIONS_FN(actions_cb),
                          v.RAND_FN(lambda ctx: crnd()), q.BONE_FN(bone_cb), None, None)
        handled = getattr(lib.dll, 'mu_nars_' + method)(co, 0, C.byref(inputs), C.byref(log))
        events = v.log_events(log)
        regions = result['regions']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != regions['object'][k]]
        posed = bool(events) and events[0][0] == POSE
        model_ok = bytes(regions['model'][0x74:0x84]) == (bytes(raw[0xa0:0xa4]) + bytes(raw[0x158:0x164]) if posed
                                                         else bytes(16))
        table_ok = ctable.raw == bytes(regions['actions'])
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('handled' if handled == 1 else 'unhandled' if handled == 0 else 'refused')
        if method == 'move':
            tally.count('phase/action changed', int(bytes(regions['object'][0x64:0x68]) != bytes(raw[0x64:0x68]) or
                                                    bytes(regions['object'][0x2a:0x2c]) != bytes(raw[0x2a:0x2c])))
        for c in calls:
            tally.count('call ' + hex(c[0]))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == events and bones == cbones and
                  model_ok and table_ok and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': calls[:4], 'c': events[:4], 'bones': bones[:3], 'c_bones': cbones[:3],
                   'model_ok': model_ok, 'table_ok': table_ok, 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


def arca_handler(base, stage):
    h = bytearray(0x100)
    struct.pack_into('<III', h, 8, LIST, LIST + 16, LIST + 16)   # the class's world vector (begin, end, capacity)
    struct.pack_into('<i', h, 0x1c, base)
    struct.pack_into('<i', h, 0x30, stage)
    for k, rgb in enumerate(STAGE_LIGHT):
        struct.pack_into('<3f', h, 0x40 + 12 * k, *rgb)
    return bytes(h)


def base_handler():
    h = bytearray(0x400)
    struct.pack_into('<I', h, 0, BASE + 0x200)
    struct.pack_into('<III', h, 0x200 + 0x2c, v.VSTUB_A, v.VSTUB_B, v.VSTUB_C)
    return bytes(h)


def arca_family(machine, lib, name, cases):
    g = random.Random('worlds-s2-' + name)
    tally = v.Tally(name)
    method = name.split('_')[1]
    d = lib.dll
    for n in range(cases):
        world = ARCA_WORLDS[n % 4] if n % 5 else g.choice(ARCA_SIBLINGS + [g.randrange(-3, 200)])
        if method == 'base':
            world = world if n % 3 else g.choice(list(range(85, 120)) + [-1, 0, -2147483648, 2147483647])
            regs = v.global_regions(110, 6, [am.defined_region('arca', ARCA, arca_handler(-1, 0)),
                                             am.defined_region('list', LIST, struct.pack('<4i', *ARCA_WORLDS))])
            result = v.run(machine, BODIES[name][0], [world], regs, {}, ecx=ARCA, cleanup=4)
            stop = v.stopped_reason(result)
            if stop:
                tally.add(False, {'case': n, 'world': world}, stop)
                continue
            got = d.mu_arca_base_world(world)
            tally.count('listed' if world in ARCA_WORLDS else 'other')
            tally.add((result['eax'] & 0xffffffff) == (got & 0xffffffff),
                      {'case': n, 'world': world, 'eax': result['eax'], 'c': got})
            continue
        base = world - 1 if g.random() < 0.75 else g.choice([-1, -1, 0, 91, 95, 100, 110, g.randrange(-5, 150)])
        stage = g.randrange(6)
        typ = g.choice(ARCA_TYPES) if n % 3 else g.choice(ALL_TYPES + [g.randrange(-50, 3000)])
        model_ptr = v.MODEL if (typ == 0x59b or n % 6) else 0
        al = g.choice([0, 1, 0x80, 0xff, g.randrange(256)]) | (g.getrandbits(24) << 8)
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 0.0, -1.0, 2.5, 70000.0, math.nan, -0.0, g.uniform(0, 4)])))
        calls, bones, cbones, lookups = [], [], [], []

        def class92(m):
            assert m.argument(0) == 0x5c
            return CLASS92

        def registry(m):
            lookups.append(m.argument(0))
            return REGISTRY

        def lookup(m):
            assert m.uc.reg_read(UC_X86_REG_ECX) == REGISTRY
            lookups.append(('get', m.argument(0)))
            return (BASE, 4)

        def slot(index, argc):
            def stub(m):
                assert m.uc.reg_read(UC_X86_REG_ECX) == BASE and m.argument(0) == v.OBJECTS
                if argc == 2:
                    assert m.argument(1) == model_ptr
                calls.append(('forward', index, struct.unpack('<i', struct.pack('<I', lookups[-1][1]))[0]))
                return (al, 4 * argc)
            return stub

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == 0 and a[6] == 0xffffffff and a[7:10] == [0, 0, 0] and a[11:] == [0xffffffff, 0, 0], a
            calls.append((CALL_EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], 0, a[10]))
            return 0

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == model_ptr and a[3] == 0, a
            k = (a[0] - 0x6fce398) // 0x30
            local = tuple(struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12))))
            bones.append((k,) + tuple(v.bits(x) for x in local))
            m.uc.mem_write(a[2], v.pack_f(*q.position(k, local)))
            return (0, 16)
        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('model', v.MODEL, bytes(0x100)),
            am.defined_region('arca', ARCA, arca_handler(base, stage)),
            am.defined_region('list', LIST, struct.pack('<4i', *ARCA_WORLDS)),
            am.defined_region('base', BASE, base_handler())])
        args = [v.OBJECTS] + ([model_ptr] if method == 'visual' else [])
        stubs = {0x95c652: class92, 0xea594b: registry, 0xea4679: lookup, v.VSTUB_A: slot(0x2c, 1),
                 v.VSTUB_B: slot(0x30, 1), v.VSTUB_C: slot(0x34, 2), q.EFFECT: effect, q.BONE: bone}
        result = v.run(machine, BODIES[name][0], args, regs, stubs, ecx=ARCA, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world, 'base': base}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        ccalls = []

        def forward(ctx, slot_index, base_world):
            ccalls.append(('forward', slot_index, base_world))
            return al & 0xff

        def bone_cb(ctx, k, local, out):
            local = tuple(local[:3])
            cbones.append((k,) + tuple(v.bits(x) for x in local))
            for qq, value in enumerate(q.position(k, local)):
                out[qq] = value
        fwd, bcb = FORWARD_FN(forward), q.BONE_FN(bone_cb)
        if method == 'create':
            handled = d.mu_arca_create(co, world, base, fwd, None)
        elif method == 'move':
            handled = d.mu_arca_move(world, base, fwd, None)
        else:
            handled = d.mu_arca_visual(co, 0, world, base, stage, bcb, None, fwd, None, C.byref(log))
        events = [e for e in v.log_events(log)]
        mixed = ccalls + events   # the visual's own case never forwards
        regions = result['regions']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != regions['object'][k]]
        tally.count('type ' + hex(typ & 0xffffffff))
        tally.count('world ' + str(world))
        tally.count('base ' + ('world-1' if base == world - 1 else str(base)))
        tally.count('stage %d' % stage)
        tally.count('handled' if handled == 1 else 'unhandled' if handled == 0 else 'refused')
        for c in calls:
            tally.count('call ' + (c[0] if isinstance(c[0], str) else hex(c[0])))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == mixed and bones == cbones,
                  {'case': n, 'type': typ, 'world': world, 'base': base, 'stage': stage, 'diff': diff[:8],
                   'al': result['eax'] & 255, 'c_al': handled, 'calls': calls[:3], 'c': mixed[:3],
                   'bones': bones, 'c_bones': cbones})
    return tally.report()


def family(machine, lib, name, cases):
    return (nars_family if name.startswith('nars_') else arca_family)(machine, lib, name, cases)


MUTANTS = [
    ('nars.c', 'in->world == 110 || in->world == 111', 'in->world == 110 || in->world == 112', 'nars_create'),
    ('nars.c', 'NARS_HEIGHT, -2800.0f', 'NARS_HEIGHT, -2600.0f', 'nars_create'),
    ('nars.c', 'MU_OBJF_ANGLE + 8, 340.0f', 'MU_OBJF_ANGLE + 4, 340.0f', 'nars_create'),
    ('nars.c', 'case 6: case 11: case 12: case 28:', 'case 6: case 11: case 12: case 27:', 'nars_create'),
    ('nars.c', '== 6); break;', '== 11); break;', 'nars_create'),
    ('nars.c', 'case 8: case 9: mu_obj_set_f32(o, MU_OBJF_RANGE, -800.0f)', 'case 8: case 9: mu_obj_set_f32(o, MU_OBJF_RANGE, -700.0f)', 'nars_create'),
    ('nars.c', 'case 79:\n    case 146:', 'case 78:\n    case 146:', 'nars_create'),
    ('nars.c', 'case 16: case 21: case 22: case 23: case 24: case 27:', 'case 16: case 20: case 22: case 23: case 24: case 27:', 'nars_create'),
    ('nars.c', 'case 37: case 38: case 142: case 150:', 'case 37: case 38: case 142: case 151:', 'nars_create'),
    ('nars.c', 'case 19: case 60: case 64: case 154:', 'case 19: case 60: case 63: case 154:', 'nars_create'),
    ('nars.c', '% 10 * 300);', '% 10 * 30);', 'nars_create'),
    ('nars.c', 'in->bone(in->context, 4, zero3, out);', 'in->bone(in->context, 5, zero3, out);', 'nars_create'),
    ('nars.c', 'wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE));\n        float out', 'wb_float(e, mu_obj_f32(o, MU_OBJF_RANGE));\n        float out', 'nars_create'),
    ('nars.c', 's + 0.8f, s + 0.3f, s + 0.2f', 's + 0.8f, s + 0.3f, s + 0.25f', 'nars_move'),
    ('nars.c', '% 5) * 0.04f;', '% 5) * 0.05f;', 'nars_move'),
    ('nars.c', 'MU_OBJF_POSITION, 1, log); break;', 'MU_OBJF_POSITION, 2, log); break;', 'nars_move'),
    ('nars.c', 'case 134: flame_light(o, index, in, MU_OBJF_START, 2, log)', 'case 134: flame_light(o, index, in, MU_OBJF_POSITION, 2, log)', 'nars_move'),
    ('nars.c', 'MU_OBJF_BLEND_V) - 0.015f', 'MU_OBJF_BLEND_V) + 0.015f', 'nars_move'),
    ('nars.c', '% 3 + 5);', '% 3 + 4);', 'nars_move'),
    ('nars.c', 'NARS_PHASE) <= 0) {', 'NARS_PHASE) < 0) {', 'nars_move'),
    ('nars.c', 'q_set_action(in, o, 0);', 'q_set_action(in, o, 2);', 'nars_move'),
    ('nars.c', 'case 4: case 116: case 146: flame', 'case 4: case 117: case 146: flame', 'nars_move'),
    ('nars.c', 'mu_obj_f32(o, MU_OBJF_SCALE) * 0.4f;', 'mu_obj_f32(o, MU_OBJF_SCALE) * 0.5f;', 'nars_visual_fire'),
    ('nars.c', '% 5 + 13) * 0.1f', '% 5 + 12) * 0.1f', 'nars_visual_fire'),
    ('nars.c', 'flame[3] = {1.0f, 0.2f, 0.0f}', 'flame[3] = {1.0f, 0.25f, 0.0f}', 'nars_visual_fire'),
    ('nars.c', 'wb_arg(e, 0xa); wb_arg(e, 0);', 'wb_arg(e, 0xb); wb_arg(e, 0);', 'nars_visual_fire'),
    ('nars.c', '0x7ef7, p, 2.0f *', '0x7ef7, p, 1.0f *', 'nars_visual_fire'),
    ('nars.c', 'bone_at(in, 7, p);', 'bone_at(in, 6, p);', 'nars_visual_fire'),
    ('nars.c', 'bone_at(in, 3, p);', 'bone_at(in, 2, p);', 'nars_visual_fire'),
    ('nars.c', '* 0.0008))) * 0.6f + 0.1f;', '* 0.0008))) * 0.6f + 0.2f;', 'nars_visual_glow'),
    ('nars.c', 'warm[3] = {0.2f + s, 0.1f, 0.1f}', 'warm[3] = {0.25f + s, 0.1f, 0.1f}', 'nars_visual_glow'),
    ('nars.c', 'bone <= 2; ++bone', 'bone <= 1; ++bone', 'nars_visual_glow'),
    ('nars.c', '% 3000) * 0.0010466667590662837f', '% 3001) * 0.0010466667590662837f', 'nars_visual_glow'),
    ('nars.c', '% 7 == 0) {', '% 7 == 1) {', 'nars_visual_glow'),
    ('nars.c', '0x7ef7, p, 1.5f + s', '0x7ef7, p, 1.4f + s', 'nars_visual_glow'),
    ('nars.c', 'NARS_PHASE)) - 0.5f;', 'NARS_PHASE)) - 0.4f;', 'nars_visual_glow'),
    ('nars.c', 'up[3] = {0.0f, 0.0f, 1.0f}', 'up[3] = {0.0f, 1.0f, 0.0f}', 'nars_visual_glow'),
    ('nars.c', '{6, 5, 6, 7, 11, 14, 15}', '{6, 5, 6, 7, 12, 14, 15}', 'nars_visual_glow'),
    ('nars.c', '* 0.0002 * (double)k', '* 0.0003 * (double)k', 'nars_visual_glow'),
    ('nars.c', 's * 1.3f, s * 1.9f}', 's * 1.3f, s * 1.8f}', 'nars_visual_glow'),
    ('nars.c', '0x7f26, p, 1.5f, dim', '0x7f26, p, 1.0f, dim', 'nars_visual_glow'),
    ('nars.c', 'emit(o, i, in, 12, 0x822a', 'emit(o, i, in, 11, 0x822a', 'nars_visual_emit'),
    ('nars.c', '{0.78f, 0.0f, 1.0f}', '{0.78f, 0.0f, 0.9f}', 'nars_visual_emit'),
    ('nars.c', '{0.9f, 0.5f, 0.5f}', '{0.9f, 0.5f, 0.6f}', 'nars_visual_emit'),
    ('nars.c', '0x15, scale * 2.0f, 1);', '0x15, scale * 2.0f, 0);', 'nars_visual_emit'),
    ('nars.c', '{0.05f, 0.02f, 0.01f}', '{0.05f, 0.02f, 0.02f}', 'nars_visual_emit'),
    ('nars.c', '{0.06f, 0.05f, 0.0f}', '{0.06f, 0.04f, 0.0f}', 'nars_visual_emit'),
    ('nars.c', '{0.03f, 0.0f, 0.04f}', '{0.03f, 0.0f, 0.05f}', 'nars_visual_emit'),
    ('nars.c', 'emit(o, i, in, 3, 0x7f5a', 'emit(o, i, in, 4, 0x7f5a', 'nars_visual_emit'),
    ('nars.c', '% 8) return;', '% 9) return;', 'nars_visual_emit'),
    ('nars.c', 'v[1] = (float)(in->rand_fn(in->context) % 100);', 'v[0] = (float)(in->rand_fn(in->context) % 100);', 'nars_visual_orbit'),
    ('nars.c', 'yaw[2] = (float)', 'yaw[1] = (float)', 'nars_visual_orbit'),
    ('nars.c', 'MU_OBJF_LIGHT + 4, 0.5f', 'MU_OBJF_LIGHT + 4, 0.6f', 'nars_visual_orbit'),
    ('nars.c', 'orbit(o, i, in, 0x7fdd, 3, log)', 'orbit(o, i, in, 0x7fdd, 4, log)', 'nars_visual_orbit'),
    ('nars.c', '30 * (wb_int', '20 * (wb_int', 'nars_visual_orbit'),
    ('nars.c', '90.0f ? 10 : 40', '90.0f ? 10 : 30', 'nars_visual_orbit'),
    ('nars.c', 'k < 20; ++k', 'k < 19; ++k', 'nars_visual_orbit'),
    ('nars.c', '* 0.5f * 100.0f', '* 0.5f * 90.0f', 'nars_visual_orbit'),
    ('arca.c', 'world == 101 || world == 111', 'world == 101 || world == 110', 'arca_base'),
    ('arca.c', '? world - 1 : -1', '? world - 1 : 0', 'arca_base'),
    ('arca.c', 'type <= 0x88e ? type - 0x889', 'type <= 0x88d ? type - 0x889', 'arca_create'),
    ('arca.c', '|| base_world == -1) return 0;', '|| base_world == -2) return 0;', 'arca_create'),
    ('arca.c', 'MU_OBJF_SCALE, 0.85f', 'MU_OBJF_SCALE, 0.8f', 'arca_create'),
    ('arca.c', 'MU_ARCA_CREATE_SLOT, base_world)', 'MU_ARCA_CREATE_SLOT, base_world + 1)', 'arca_create'),
    ('arca.c', 'MU_ARCA_MOVE_SLOT, base_world)', 'MU_ARCA_MOVE_SLOT, base_world - 1)', 'arca_move'),
    ('arca.c', 'r < 0 ? -1 : (uint8_t)r != 0', 'r < 0 ? -1 : r > 1', 'arca_move'),
    ('arca.c', 'bone(bone_context, 3, zero3, p);', 'bone(bone_context, 4, zero3, p);', 'arca_visual'),
    ('arca.c', 'stage < 4 ? 10 : 11', 'stage < 3 ? 10 : 11', 'arca_visual'),
    ('arca.c', '{0.08f, 1.0f, 0.86f}', '{0.58f, 1.0f, 0.86f}', 'arca_visual'),
    ('arca.c', '{0.88f, 0.4f, 0.86f}', '{0.88f, 0.4f, 0.8f}', 'arca_visual'),
    ('arca.c', 'if (mu_arca_type_index(type)) return 1;', 'if (mu_arca_type_index(type) > 1) return 1;', 'arca_visual'),
    ('arca.c', 'MU_ARCA_VISUAL_SLOT, base_world)', 'MU_ARCA_MOVE_SLOT, base_world)', 'arca_visual')]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=1000)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--output')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    lib = bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}'))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()}, 'families': {}, 'mutants': []}
    only = set(a.only.split(',')) if a.only else None
    for name in BODIES:
        if only and name not in only:
            continue
        r = report['families'][name] = family(machine, lib, name, a.cases)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, r['examples'][:1], flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-s2-') as tmp:
            for n, (file, old, new, name) in enumerate(MUTANTS):
                if only and name not in only:
                    continue
                dest = Path(tmp) / str(n)
                for directory in ('objects', 'terrain', 'model-codec', 'record-math', 'movement'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
                shutil.copy(ROOT / 'reconstructed/deps.mk', dest / 'deps.mk')
                p = dest / 'objects' / file
                s = p.read_text()
                assert s.count(old) == 1, old
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
