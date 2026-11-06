#!/usr/bin/env python3
"""World-145, 95, 139 and 115 primary slots against pinned instructions.

Aquila's Temple create/move/visual (no world predicate), Debenter create/move/visual (predicate 0x00dbd14d,
worlds 95 and 96), Boss Battle create/move/visual and world 115's create/move (the BaseMap defaults). Full AL,
all OBJECT bytes, ordered output calls with their constant arguments asserted and the final MSVC RNG are
compared. rand, AddTerrainLight, CreateParticle, CreateSprite, CreateJoint, CreateEffect, SetAction, the model
lookup, Animation, TransformPosition and the bone matrix 0x0129fd4f are recording boundaries; the predicates,
the CRT sine wrapper, the vector helpers, the matrix accessor/destructor, the sprite descriptor and the SEH
frames execute as original code.
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
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'aquila_create': (0xd75a6c, 0xd75ac6), 'aquila_move': (0xd75ac6, 0xd76059),
          'aquila_visual': (0xd77b3e, 0xd77d18),
          'boss_create': (0xd9c180, 0xd9c18d), 'boss_move': (0xd9c18d, 0xd9c19a),
          'boss_visual': (0xd9c1a7, 0xd9c1b4),
          'w115_create': (0xd5cb99, 0xd5cba6), 'w115_move': (0xd5cc16, 0xd5cc23),
          'debenter_create': (0xdbd210, 0xdbd4e6), 'debenter_move': (0xdbd4e6, 0xdbd735),
          'debenter_visual': (0xdbd735, 0xdbedf9)}
WORLD = {'aquila': 145, 'boss': 139, 'w115': 115, 'debenter': 95}
SIBLINGS = {'aquila': [0, 95, 96, 139, 144, 145], 'boss': [0, 138, 139, 140, 145],
            'w115': [0, 113, 115, 116, 145], 'debenter': [0, 94, 95, 96, 97, 145]}
EXTREMES = [-2147483648, -1, 2147483647, 1000, 0x7dc]
TYPES = {'aquila': list(range(-1, 160)) + EXTREMES, 'boss': list(range(-1, 40)) + EXTREMES,
         'w115': list(range(-1, 40)) + EXTREMES, 'debenter': list(range(-1, 80)) + EXTREMES}
DIRECTED = {'aquila_create': [51, 99, 120, 143, 148], 'aquila_move': [90, 136, 137, 138, 139, 140, 142, 152],
            'aquila_visual': [136, 137, 138, 139, 140, 141, 142], 'debenter_move': [9, 11, 50, 9, 11],
            'debenter_visual': [9, 11, 21, 27, 31, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]}
# Debenter visual: the first rand residue that opens each type's branch, (modulus, value)
OPEN = {9: (4, 0), 11: (10, 0), 56: (10, 0), 57: (6, 0), 58: (5, 0), 59: (5, 0), 60: (5, 0), 61: (5, 0),
        62: (35, 5), 64: (10, 0), 65: (5, 1), 66: (5, 0), 67: (2, 0)}
TIME_CALL = (0xdbeba3, 0xdbeba9)   # Debenter visual type 65: call dword ptr [0x01a7c9a4] (timeGetTime)
UNINIT_LOCAL = {11, 21}   # their TransformPosition local is uninitialized stack in the original: zero here
JOINT = 0x153b02c
JOINT_TAIL = [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]
POSE = 0x00dbd399   # MU_DEBENTER_POSE
NULL = 0
NO_NULL = {'aquila_move'}   # the original dereferences the object without a test
COOKIE = 0x01cf65c0
BONE_MATRIX = 0x129fd4f
LIGHT = 0x16cacfc
MATRIX_SPECIALS = [0.0, -0.0, 1.0, -1.0, 1e10, -1e10, math.nan, 25600.0, 3.5e-39]


def bind(lib):
    d = lib.dll
    P = C.c_void_p
    d.mu_aquila_create.argtypes = [P, C.c_int32]
    d.mu_aquila_move.argtypes = [P, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_aquila_visual.argtypes = [P, C.c_int, C.POINTER(C.c_float)]
    d.mu_aquila_bone_type.argtypes = [C.c_int32]
    In, L = C.POINTER(q.Inputs), C.POINTER(v.Log)
    for name in ('create', 'move', 'visual'):
        getattr(d, 'mu_debenter_' + name).argtypes = [P, C.c_int32, In, L]
        getattr(d, 'mu_debenter_' + name).restype = C.c_int
    for name in ('boss_battle_create', 'boss_battle_move', 'boss_battle_visual', 'world115_create',
                 'world115_move'):
        getattr(d, 'mu_' + name).argtypes = [P, C.c_int32]
    return lib


def matrix_sample(g):
    out = []
    for _ in range(16):
        x = g.choice(MATRIX_SPECIALS) if g.random() < 0.15 else g.uniform(-30000.0, 30000.0)
        out.append(v.f32(x))
    return out


def seed_for(g, modulus, value):
    while True:
        seed = g.getrandbits(32)
        if v.MsvcRand(seed)() % modulus == value:
            return seed


def time_sample(g):
    return v.f32(g.choice([0.0, -0.0, 1000.0, -1000.0, 2999.5, 3600.0, 1963.4954, 2147483520.0, 3e9, -1e12,
                           math.nan, g.uniform(-1e6, 1e6), g.uniform(0, 1e5)]))


def debenter_family(machine, lib, name, cases):
    g = random.Random('worlds-s-' + name)
    tally = v.Tally(name)
    method = name.split('_')[1]
    for n in range(cases):
        typ = TYPES['debenter'][n % len(TYPES['debenter'])] if n % 9 else g.randrange(-50, 400)
        if name in DIRECTED and n % 3 == 1:
            typ = g.choice(DIRECTED[name])
        world = 95 if n % 4 else SIBLINGS['debenter'][(n // 4) % len(SIBLINGS['debenter'])]
        present = True if method == 'visual' else n % 7 != 0
        count = g.choice([0, 1, 2, 3, 4, 4, 5, 8])
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        key = g.choice([9, 9, 0, 56, 61, 67, 55, 68, 8, 10, g.randrange(-5, 80), g.getrandbits(32) - (1 << 31)])
        v.put_i(raw, 0x60, key)
        if method == 'create' and key == 9:
            present = True   # the original writes model +0x78 without a test
        v.put_i(raw, 0x64, g.choice([-2, -1, 0, 0, 1, 1, 2, 5]))
        action = g.choice([0, 0, 1, 1, 2, 3, g.randrange(0, 10)])
        struct.pack_into('<HH', raw, 0x2a, action, g.randrange(4))
        v.put_f(raw, 0xd0, v.f32(g.choice([0.0, 0.5, 1.0, 2.0, 2.5, 4.0, 8.0, 23.5, 24.0, math.nan,
                                           g.uniform(-1, 30)])), v.f32(g.uniform(0, 10)))
        v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 0.0, -1.0, 2.5, 65535.9, 70000.0, math.nan, -0.0, g.uniform(0, 4)])))
        if method == 'move' and typ in (9, 11) and world in (95, 96):   # the record is read without a test
            present = True
            count = max(count, 1)
            if action >= count:
                action = g.randrange(count)
                struct.pack_into('<H', raw, 0x2a, action)
        table = q.action_table(g, count)
        model = bytearray(0x100)
        struct.pack_into('<h', model, 0x26, count)
        struct.pack_into('<I', model, 0x30, v.ACTIONS)
        time = time_sample(g)
        now = g.choice([0, 29, 30, 1023, 1024 + 5, 1024 * g.randrange(1 << 20) + g.randrange(30), g.getrandbits(32)])
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
            assert a[5] == v.OBJECTS and a[6] == 0xffffffff and a[7] == 0 and a[9:] == [0, 0, 0xffffffff, 0, 0], a
            calls.append((q.Q_KEYED_EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) +
                         v.read_vec(m, a[3]) + (a[4], a[8]))
            return 0

        def joint(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == v.OBJECTS and a[7:] == JOINT_TAIL, a
            calls.append((JOINT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], 1, a[6]))
            return 0

        def animation(m):
            a = [m.argument(k) for k in range(8)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL
            assert a == [0x6fce398, struct.unpack_from('<I', raw, 0xd0)[0], struct.unpack_from('<I', raw, 0xd4)[0],
                         struct.unpack_from('<H', raw, 0x2c)[0], v.OBJECTS + 0x164, v.OBJECTS + 0x170, 0, 0], a
            calls.append((POSE, 0) + struct.unpack('<3I', bytes(m.uc.mem_read(v.MODEL + 0x78, 12))))
            return (0, 32)

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL
            k = (a[0] - 0x6fce398) // 0x30
            # create's calls pass Translate = 1 (the BodyOrigin it just set), the visual's 0
            assert a[0] == 0x6fce398 + k * 0x30 and 0 <= k < 64 and a[3] == int(method == 'create'), a
            if method == 'visual' and typ in UNINIT_LOCAL:
                local = (0.0, 0.0, 0.0)
            else:
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
        stubs = {q.PARTICLE: particle, q.SPRITE: sprite, LIGHT: light, q.EFFECT: effect, JOINT: joint,
                 q.BONE: bone, 0x12b5064: animation, 0x1989721: lambda m: rnd(), 0x966cc4: lambda m: v.FAKE,
                 0xeaa8cf: lambda m: (v.MODEL if present else 0, 4)}
        hook = None
        if method == 'visual':
            def now_hook(u, address, size, ignored):
                u.reg_write(UC_X86_REG_EAX, now)
                u.reg_write(UC_X86_REG_EIP, TIME_CALL[1])
            hook = machine.uc.hook_add(UC_HOOK_CODE, now_hook, begin=TIME_CALL[0], end=TIME_CALL[0])
            machine.uc.ctl_flush_tb()
        try:
            result = v.run(machine, BODIES[name][0], args, regs, stubs, ecx=v.FAKE,
                           cleanup=8 if method == 'visual' else 4)
        finally:
            if hook is not None:
                machine.uc.hook_del(hook)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world, 'key': key}, stop)
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
        inputs = q.Inputs(world, time, v.f32(0.1), now, (C.c_float * 3)(), (C.c_int32 * 2)(), q.ACTIONS_FN(actions_cb),
                          v.RAND_FN(lambda ctx: crnd()), q.BONE_FN(bone_cb), None, None)
        handled = getattr(lib.dll, 'mu_' + name)(co, 0, C.byref(inputs), C.byref(log))
        events = v.log_events(log)
        regions = result['regions']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != regions['object'][k]]
        model_ok = bytes(regions['model'][0x78:0x84]) == (bytes(raw[0x158:0x164]) if events and events[0][0] == POSE
                                                         else bytes(12))
        table_ok = ctable.raw == bytes(regions['actions'])
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('key ' + str(key) if method == 'create' else 'action ' + str(action))
        tally.count('handled' if handled == 1 else 'unhandled' if handled == 0 else 'refused')
        if method == 'move':
            tally.count('rest/action changed', int(bytes(regions['object'][0x64:0x68]) != bytes(raw[0x64:0x68]) or
                                                  bytes(regions['object'][0x2a:0x2c]) != bytes(raw[0x2a:0x2c])))
        for c in calls:
            tally.count('call ' + hex(c[0]))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == events and bones == cbones and
                  model_ok and table_ok and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'key': key, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': calls[:4], 'c': events[:4], 'bones': bones[:3], 'c_bones': cbones[:3],
                   'model_ok': model_ok, 'table_ok': table_ok, 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


def family(machine, lib, name, cases):
    if name.startswith('debenter_'):
        return debenter_family(machine, lib, name, cases)
    g = random.Random('worlds-s-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    cls = WORLD[prefix]
    types = TYPES[prefix]
    for n in range(cases):
        typ = types[n % len(types)] if n % 9 else g.randrange(-50, 400)
        if name in DIRECTED and n % 3 == 1:
            typ = g.choice(DIRECTED[name])
        world = cls if n % 4 else SIBLINGS[prefix][(n // 4) % len(SIBLINGS[prefix])]
        null = n % 23 == 0 and name not in NO_NULL
        present = n % 7 != 0
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        struct.pack_into('<H', raw, 0x2a, g.choice([0, 1, 2, 3, 2, 4, 7]))
        if n % 5 == 0:   # alpha around the after-character threshold 0.9, NaN included
            v.put_f(raw, 0xdc, v.f32(g.choice([0.9, 0.8999999, 0.90000004, -0.0, math.nan, 1.0, 0.0, 5.0])))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        matrix = matrix_sample(g)
        calls = []

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((LIGHT, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0

        def bone_matrix(m):
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.OBJECTS and m.argument(1) == 6
            out = m.argument(0)
            m.uc.mem_write(out, struct.pack('<16f', *matrix))
            calls.append(('matrix', 6))
            return (out, 8)
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e)),
                                           am.defined_region('model', v.MODEL, bytes(0x100))])
        args = [NULL if null else v.OBJECTS] + ([NULL if not present else v.MODEL] if method == 'visual' else [])
        result = v.run(machine, BODIES[name][0], args, regs,
                       {LIGHT: light, BONE_MATRIX: bone_matrix, 0x1989721: lambda m: rnd()},
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.rand_fn = fn
        inputs.has_model = int(present)
        obj = None if null else co
        d = lib.dll
        if prefix == 'aquila':
            if method == 'create':
                handled = d.mu_aquila_create(obj, world)
            elif method == 'move':
                handled = d.mu_aquila_move(obj, 0, C.byref(inputs), C.byref(log))
            else:
                m16 = (C.c_float * 16)(*matrix)
                handled = d.mu_aquila_visual(obj, int(present), m16)
        else:
            fname = {'boss': 'mu_boss_battle_', 'w115': 'mu_world115_'}[prefix] + method
            handled = getattr(d, fname)(obj, world)
        events = v.log_events(log)
        if name == 'aquila_visual' and not null and present and d.mu_aquila_bone_type(typ):
            events = [('matrix', 6), ('matrix', 6)]   # the method asks 0x0129fd4f twice for the same bone
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null' if null else 'handled' if handled else 'unhandled')
        tally.count('model' if present else 'no model')
        for c in calls:
            tally.count('call ' + (hex(c[0]) if isinstance(c[0], int) else c[0]))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == events and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': calls[:4], 'c': events[:4], 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


MUTANTS = [
    ('aquila.c', 'case 51: case 99:', 'case 52: case 99:', 'aquila_create'),
    ('aquila.c', 'case 143: case 148:', 'case 143: case 149:', 'aquila_create'),
    ('aquila.c', 'RANGE, -150.0f', 'RANGE, -300.0f', 'aquila_create'),
    ('aquila.c', '0.9f > mu_obj_f32(o, MU_OBJF_ALPHA) ? 1 : 0', '0.9f >= mu_obj_f32(o, MU_OBJF_ALPHA) ? 1 : 0',
     'aquila_move'),
    ('aquila.c', 'if (t == 90)', 'if (t == 91)', 'aquila_move'),
    ('aquila.c', 's * 0.41f, s * 0.8f, 2);', 's * 0.41f, s * 0.8f, 3);', 'aquila_move'),
    ('aquila.c', 'if (t == 152)', 'if (t == 151)', 'aquila_move'),
    ('aquila.c', '% 2 + 4) / 5.0f', '% 2 + 3) / 5.0f', 'aquila_move'),
    ('aquila.c', 'const float base = 0.6f;', 'const float base = 0.5f;', 'aquila_move'),
    ('aquila.c', 'l[0] = s * 0.74f;', 'l[0] = s * 0.75f;', 'aquila_move'),
    ('aquila.c', 'l[1] = s * 0.84f;', 'l[1] = s * 0.85f;', 'aquila_move'),
    ('aquila.c', 'l[0] = s; l[1] = s * 0.22f;', 'l[0] = s; l[1] = s * 0.2f;', 'aquila_move'),
    ('aquila.c', 'l[2] = s * 0.32f;', 'l[2] = s * 0.3f;', 'aquila_move'),
    ('aquila.c', 'range = 3; l[0] = s; l[1] = s;', 'range = 2; l[0] = s; l[1] = s;', 'aquila_move'),
    ('aquila.c', 'wb_float(e, mu_obj_f32(o, MU_OBJF_POINT_A + 4));', 'wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION + 4));',
     'aquila_move'),
    ('aquila.c', 'type <= 140) || type == 142', 'type <= 140) || type == 141', 'aquila_visual'),
    ('aquila.c', 'if (!o || !has_model) return 0;', 'if (!o) return 0;', 'aquila_visual'),
    ('aquila.c', 'bone6[13]);', 'bone6[14]);', 'aquila_visual'),
    ('worlds_s_stubs.c', 'mu_boss_battle_create(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }',
     'mu_boss_battle_create(const uint8_t *o, int32_t world) { (void)o; return world == 139; }', 'boss_create'),
    ('worlds_s_stubs.c', 'mu_boss_battle_move(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }',
     'mu_boss_battle_move(const uint8_t *o, int32_t world) { (void)world; return o != 0; }', 'boss_move'),
    ('worlds_s_stubs.c', 'mu_boss_battle_visual(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }',
     'mu_boss_battle_visual(const uint8_t *o, int32_t world) { (void)o; (void)world; return 1; }', 'boss_visual'),
    ('worlds_s_stubs.c', 'mu_world115_create(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }',
     'mu_world115_create(const uint8_t *o, int32_t world) { (void)o; return world == 115; }', 'w115_create'),
    ('worlds_s_stubs.c', 'mu_world115_move(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }',
     'mu_world115_move(const uint8_t *o, int32_t world) { (void)world; return o != 0; }', 'w115_move'),
    ('debenter.c', 'in->world == 95 || in->world == 96', 'in->world == 95 || in->world == 97', 'debenter_create'),
    ('debenter.c', 'if (key == 9) {', 'if (key == 10) {', 'debenter_create'),
    ('debenter.c', 'key >= 56 && key <= 67', 'key >= 56 && key <= 66', 'debenter_create'),
    ('debenter.c', 'bone_into(in, 22, o, MU_OBJF_POINT_B);\n        joint(', 'bone_into(in, 21, o, MU_OBJF_POINT_B);\n        joint(', 'debenter_create'),
    ('debenter.c', 'wb_float(e, 40.0f);', 'wb_float(e, 30.0f);', 'debenter_create'),
    ('debenter.c', 'joint(log, index, p, a, 0x3d);', 'joint(log, index, p, a, 0x3e);', 'debenter_create'),
    ('debenter.c', 'wb_vec(e, p);\n        bone_into', 'wb_vec(e, a);\n        bone_into', 'debenter_create'),
    ('debenter.c', 'if (t == 9 || t == 11) {', 'if (t == 9 || t == 12) {', 'debenter_move'),
    ('debenter.c', '% 3 + 4);', '% 3 + 3);', 'debenter_move'),
    ('debenter.c', 'q_set_action(in, o, 1);', 'q_set_action(in, o, 2);', 'debenter_move'),
    ('debenter.c', 'DEBENTER_REST) <= 0) {', 'DEBENTER_REST) < 0) {', 'debenter_move'),
    ('debenter.c', '* 0.001)));', '* 0.002)));', 'debenter_move'),
    ('debenter.c', 's = s * 0.4f + 0.3f;', 's = s * 0.4f + 0.35f;', 'debenter_move'),
    ('debenter.c', 'MU_OBJF_POSITION + 4), l, 2);', 'MU_OBJF_POSITION + 4), l, 3);', 'debenter_move'),
    ('debenter.c', 'fabsf(q_sin(', '(q_sin(', 'debenter_move'),
    ('debenter.c', '% 41 - 20)', '% 41 - 21)', 'debenter_visual'),
    ('debenter.c', 'p[2] = p[2] - 10.0f;', 'p[2] = p[2] - 11.0f;', 'debenter_visual'),
    ('debenter.c', '0x52, scale, 0);', '0x52, scale, 1);', 'debenter_visual'),
    ('debenter.c', '* 0.0008))) * 0.6f + 0.1f;', '* 0.0009))) * 0.6f + 0.1f;', 'debenter_visual'),
    ('debenter.c', '* 0.0008))) * 0.6f + 0.1f;', '* 0.0008))) * 0.6f + 0.2f;', 'debenter_visual'),
    ('debenter.c', '% 3000)', '% 3001)', 'debenter_visual'),
    ('debenter.c', '% 7 == 0', '% 7 == 1', 'debenter_visual'),
    ('debenter.c', '0x7ef7, p, 1.5f + s,', '0x7ef7, p, 1.4f + s,', 'debenter_visual'),
    ('debenter.c', 'MU_OBJF_ACTION) == 1)', 'MU_OBJF_ACTION) == 2)', 'debenter_visual'),
    ('debenter.c', 'in->bone(in->context, 3, zero3, p);', 'in->bone(in->context, 5, zero3, p);', 'debenter_visual'),
    ('debenter.c', '% 5) * 0.03 +', '% 5) * 0.04 +', 'debenter_visual'),
    ('debenter.c', '0x21, scale, 0);', '0x21, scale * 0.5f, 0);', 'debenter_visual'),
    ('debenter.c', '% 6 == 0', '% 6 == 1', 'debenter_visual'),
    ('debenter.c', 't == 59 ? 0.02f : 0.01f', 't == 59 ? 0.03f : 0.01f', 'debenter_visual'),
    ('debenter.c', '0.86328125f * s', '0.86f * s', 'debenter_visual'),
    ('debenter.c', '{1.2f * s, 1.2f * s, 1.2f * s}', '{1.2f * s, 1.25f * s, 1.2f * s}', 'debenter_visual'),
    ('debenter.c', '% 35 == 5', '% 35 == 6', 'debenter_visual'),
    ('debenter.c', 'm[3] = {0.39f, 0.65f, 0.39f}', 'm[3] = {0.39f, 0.6f, 0.39f}', 'debenter_visual'),
    ('debenter.c', '% 1024u)', '% 1000u)', 'debenter_visual'),
    ('debenter.c', 'phase < 30', 'phase < 31', 'debenter_visual'),
    ('debenter.c', '0x807e + (uint32_t)', '0x807f + (uint32_t)', 'debenter_visual'),
    ('debenter.c', 'l[0] = 0.12f * s; l[1] = 0.12f * s;', 'l[0] = 0.12f * s; l[1] = 0.1f * s;', 'debenter_visual'),
    ('debenter.c', 'q_effect(log, i, o, 0x199, l, 0,', 'q_effect(log, i, o, 0x199, l, 1,', 'debenter_visual')]


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
        with tempfile.TemporaryDirectory(prefix='worlds-s-') as tmp:
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
