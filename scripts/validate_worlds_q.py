#!/usr/bin/env python3
"""Acheron (91), Ferea (112), Swamp of Darkness (122) and Kubera Mine (123..127) primary slots against
pinned instructions (RENDER-WORLDS-Q).

Eleven families: create, move and visual of Acheron, Swamp of Darkness and Kubera Mine, and Ferea's create
and move. Each compares AL, all 0x3d8 OBJECT bytes, the handler members the methods touch (Ferea +0x48/+0x50,
Swamp of Darkness +0x78, Kubera +0x14), the model's action table (16-byte records), the ordered recorded
calls and the final MSVC RNG. Run as original instructions: the world predicates, SetAction 0x012affa4,
the action lookup 0x00eaaa44/0x012bcf9d, the random range 0x011ff622, ftol 0x0191c5e0, sin/cos/sqrt/fabs
and the client's vector helpers. Recording stubs: rand 0x01989721 (MSVC recurrence), the model container
0x00966cc4/0x00eaa8cf (harness model with an action table), AddTerrainLight 0x016cacfc, CreateParticle
0x0168fafd, CreateSprite 0x01692eb7, CreateEffect 0x013c0eaa, PlayBuffer 0x00a6ac96, StopBuffer 0x00a6ad76,
the operable-object table 0x016d9f51, BMD::TransformPosition 0x012b6ef1 (a deterministic position per bone
and local vector) and timeGetTime (a code hook at the import call). Cases the original cannot run are not
sampled: Acheron's move of types 16/52 dereferences the action record without a test (no model or action
outside the table), and Kubera's move reads model +0x30 + action * 16 without a bounds test. Acheron's move
of type 16 in action 1 takes sin(frame / keys * 3.14) and discards it; keys 0 (sin of an infinity, which runs
the CRT's error reporting) is not sampled there.
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
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ECX
import actor_machine as am
import validate_object_render as v
import pins
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'acheron_create': (0xd6a6d7, 0xd6a7aa), 'acheron_move': (0xd6a7aa, 0xd6ae34),
          'acheron_visual': (0xd6ae34, 0xd6c427),
          'ferea_create': (0xde5cb0, 0xde5de2), 'ferea_move': (0xde5de2, 0xde6405),
          'swamp_create': (0xe54429, 0xe54575), 'swamp_move': (0xe54646, 0xe54752),
          'swamp_visual': (0xe5540e, 0xe555d2),
          'kubera_create': (0xe19bb3, 0xe19dfb), 'kubera_move': (0xe19ed0, 0xe1a5df),
          'kubera_visual': (0xe1b5fb, 0xe1b6f5)}
# Type tables read as data: Swamp of Darkness and Kubera create (jump targets, then byte indices).
TABLES = {'swamp_create': (0xe54575, 0xe54646), 'kubera_create': (0xe19dfb, 0xe19ed0)}
PREDICATES = {'acheron': (0xd6a614, 0xd6a635), 'swamp': (0xe543a1, 0xe543b9), 'kubera': (0xe1e4b6, 0xe1e4cd)}
WORLDS = {'acheron': [91, 92, 90, 93, 0, 112], 'ferea': [112, 111, 113, 0], 'swamp': [122, 121, 123, 0],
          'kubera': [123, 124, 125, 126, 127, 122, 128, 0]}
TYPES = {
    'acheron': [9, 16, 22, 23, 24, 25, 26, 27, 29, 31, 38, 52, 54, 55, 56, 57, 60, 61, 62, 69, 73, 78, 80, 89,
                93, 100, 0, 1, 28, 63, 101, -1, 2147483647],
    'ferea': [6, 9, 10, 17, 18, 22, 26, 28, 29, 31, 32, 33, 34, 37, 39, 43, 51, 60, 65, 71, 72, 84, 97, 98, 106,
              114, 123, 126, 127, 128, 129, 130, 137, 140, 141, 142, 152, 153, 154, 0, 155, -1, 2147483647],
    'swamp': [0, 39, 41, 83, 88, 124, 117, 107, 108, 112, 131, 132, 133, 134, 161, 172, 173, 174, 175, 176, 180, 181, 4,
              -1, -2147483648, 2147483647],
    'kubera': [0, 15, 29, 47, 52, 100, 127, 132, 134, 135, 145, 158, 161, 173, 174, 180, 181, 2, -1, 2147483647]}
DIRECTED = {'acheron_visual': [57, 73, 57, 52, 57, 38], 'swamp_visual': [176, 83, 83, 83], 'kubera_visual': [161, 161, 161, 0],
            'kubera_move': [52, 47, 15, 47, 15, 100, 145],
            'ferea_move': [51, 123, 17, 72], 'swamp_create': [88, 131, 173], 'swamp_move': [131, 132, 133], 'acheron_move': [16, 52]}
NEEDS_RECORD = {'acheron_move': (16, 52), 'kubera_move': None}   # None: every type (record read unchecked)
PARTICLE, SPRITE, LIGHT, EFFECT, SOUND, STOP, REGISTER, BONE = (0x168fafd, 0x1692eb7, 0x16cacfc, 0x13c0eaa,
                                                                 0xa6ac96, 0xa6ad76, 0x16d9f51, 0x12b6ef1)
Q_KEYED_EFFECT, Q_STOP = 0x013c0eab, 0x00a6ad76
TIME_CALL = (0xe554ff, 0xe55505)   # Swamp of Darkness visual: call dword ptr [0x01a7c9a4] (timeGetTime)
FRAME_TIME, ISA, COOKIE = 0x01cf103c, 0x0bdcb280, 0x01cf65c0   # COOKIE: /GS word of the CRT sine's large-argument path
# ftol 0x0191c5e0 takes FISTTP when the CRT ISA word is >= 2;
HANDLER = v.FAKE + 0x800
ACTIONS_FN = C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_int32, C.POINTER(C.c_int32))
BONE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))


class Handler(C.Structure):
    _fields_ = [('ferea_state', C.c_int32), ('ferea_object', C.c_void_p), ('swamp_variant', C.c_uint8),
                ('kubera_object', C.c_void_p)]


class Inputs(C.Structure):
    _fields_ = [('world', C.c_int32), ('time', C.c_float), ('frame_time', C.c_float), ('now_ms', C.c_uint32),
                ('hero', C.c_float * 3), ('hero_tile', C.c_int32 * 2), ('actions', ACTIONS_FN),
                ('rand_fn', v.RAND_FN), ('bone', BONE_FN), ('context', C.c_void_p), ('handler', C.POINTER(Handler))]


def bind(lib):
    d = lib.dll
    P, I, In, L = C.c_void_p, C.c_int32, C.POINTER(Inputs), C.POINTER(v.Log)
    for name, args in {'mu_acheron_create': [P, In], 'mu_acheron_move': [P, I, In, L],
                       'mu_acheron_visual': [P, I, In, L], 'mu_ferea_create': [P, In],
                       'mu_ferea_move': [P, I, In, L], 'mu_swamp_create': [P, In], 'mu_swamp_move': [P, In],
                       'mu_swamp_visual': [P, I, C.c_int, In, L], 'mu_kubera_create': [P, I, In, L],
                       'mu_kubera_move': [P, I, In, L], 'mu_kubera_visual': [P, I, C.c_int, In, L]}.items():
        getattr(d, name).argtypes = args
        getattr(d, name).restype = C.c_int
    return lib


def position(k, local):
    return tuple(v.f32(local[q] + k * (q + 1) * 17 + 3) for q in range(3))


def action_table(g, count):
    data = bytearray()
    for _ in range(max(count, 1)):
        speed = v.f32(g.choice([0.0, 0.25, 0.3, 0.5, 1.0, g.uniform(-0.5, 2)]))
        data += struct.pack('<BBBBfhBBI', g.randrange(256), 0xee, 0xee, 0xee, speed, g.choice([0, 1, 2, 5, 9, 24,
                            g.randrange(-3, 40)]), g.randrange(2), 0xee, 0x41414141)
    return data


def family(machine, lib, name, cases):
    g = random.Random('worlds-q-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    for n in range(cases):
        typ = g.choice(TYPES[prefix]) if n % 9 else g.randrange(-5, 260)
        if n % 3 == 1 and name in DIRECTED:   # the rarely drawn branches
            typ = g.choice(DIRECTED[name])
        worlds = WORLDS[prefix]
        world = (g.randrange(123, 128) if prefix == 'kubera' else worlds[0]) if g.random() < 0.8 else g.choice(worlds)
        null_object = n % 41 == 40 and not (prefix == 'acheron')   # the Acheron bodies have no null test
        present = n % 7 != 0
        count = g.choice([0, 1, 2, 3, 4, 4, 5, 8]) if prefix != 'kubera' else g.choice([0, 2, 4, 4, 4, 5, 8])
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        v.put_i(raw, 0x64, g.choice([-2, -1, 0, 0, 1, 1, 2, 5]))
        action = g.choice([0, 0, 1, 1, 2, 3, g.randrange(0, 10)])
        struct.pack_into('<HH', raw, 0x2a, action, g.randrange(4))
        v.put_f(raw, 0xd0, v.f32(g.choice([0.0, 0.5, 1.0, 2.0, 2.5, 4.0, 8.0, 23.5, 24.0, math.nan,
                                           g.uniform(-1, 30)])), v.f32(g.uniform(0, 10)))
        v.put_f(raw, 0xb4, v.f32(g.choice([0.0, -0.0, 0.5, -1.0, 3.0, g.uniform(-2, 30), math.nan])))
        v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 0.0, -1.0, 2.5, 65535.9, 70000.0, math.nan, g.uniform(0, 4)])))
        v.put_f(raw, 0x16c, v.f32(g.choice([0.0, 90.0, -45.0, 180.0, g.uniform(-720, 720)])))
        needs = NEEDS_RECORD.get(name, ())
        if needs is not None and typ in needs:   # Acheron: no model or action outside the table faults
            present = True
        if (needs is None and present) or (needs is not None and typ in needs):   # unchecked record reads
            count = max(count, 1)
            if action >= count:
                action = g.randrange(count)
                struct.pack_into('<H', raw, 0x2a, action)
        if name == 'kubera_move' and typ == 52 and n % 2 and count > 3:   # leaving action 3 at half its keys
            action = 3
            struct.pack_into('<H', raw, 0x2a, action)
            v.put_f(raw, 0xd0, v.f32(g.choice([1.5, 2.0, 2.25, 2.5, 4.0, 4.5, 12.0])))
        table = action_table(g, count)
        if name == 'acheron_move' and typ == 16 and action == 1 and count > 1 and struct.unpack_from('<h', table, 24)[0] == 0:
            struct.pack_into('<h', table, 24, 7)   # sin(frame / 0) = sin(inf) enters the CRT error path (not seeded)
        model = bytearray(0x100)
        struct.pack_into('<h', model, 0x26, count)
        struct.pack_into('<I', model, 0x30, v.ACTIONS)
        handler = bytearray(0x100)
        ferea_state = g.choice([0, 1, 2, 3, 3, -1, 7])
        struct.pack_into('<iI', handler, 0x48, ferea_state, 0)
        handler[0x78] = g.choice([0, 1, 2, 1, 3])
        struct.pack_into('<I', handler, 0x14, 0)
        time = v.f32(g.choice([0.0, -0.0, 1000.0, -1000.0, 2999.5, 3600.0, g.uniform(-1e6, 1e6)]))
        frame_time = v.f32(g.choice([0.0, 0.04, 1.0, g.uniform(0, 2)]))
        now = g.choice([0, 29, 30, 1023, 1024 + 5, 1024 * g.randrange(1 << 20) + g.randrange(30), g.getrandbits(32)])
        v.put_f(raw, 0x158, v.f32(float(g.randrange(0, 25600))), v.f32(float(g.randrange(0, 25600))))
        hero = (v.f32(raw_f(raw, 0x158) + g.choice([0.0, 100.0, 499.5, 500.0, 500.5, 899.5, 900.0, 900.5, 2000.0])),
                v.f32(raw_f(raw, 0x15c) + g.choice([0.0, 0.0, -300.0, 30.0])), 0.0)
        hero_tile = (g.choice([20, 21, 30, 48, 49, g.randrange(0, 256)]), g.choice([105, 106, 120, 138, 139,
                                                                                     g.randrange(0, 256)]))
        if name == 'kubera_move' and typ in (47, 52) and n % 3 == 0:   # the sound radius boundaries
            hero = (v.f32(raw_f(raw, 0x158) + (900.0 if typ == 47 else 500.0)), v.f32(raw_f(raw, 0x15c)), 0.0)
            if typ == 47 and count > 3:
                action = g.choice([1, 3])
                struct.pack_into('<H', raw, 0x2a, action)
                v.put_f(raw, 0xd0, v.f32(g.choice([0.0, 1.0, 2.0])))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones, cbones = [], [], []

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6] in (0, v.OBJECTS) and a[7] == 0, a
            calls.append((PARTICLE, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0

        def sprite(m):
            a = [m.argument(k) for k in range(9)]
            assert a[4] == v.OBJECTS and a[6:8] == [0, 4] and v.read_vec(m, a[8]) == (1, 1, v.bits(1.0)), a
            calls.append((SPRITE, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) + (a[5], 1, 0, 4))
            return 0

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((LIGHT, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == v.OBJECTS and a[6] == 0xffffffff and a[7] == 0 and a[9:] == [0, 0, 0xffffffff, 0, 0], a
            calls.append((Q_KEYED_EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) +
                         v.read_vec(m, a[3]) + (a[4], a[8]))
            return 0

        def sound(m):
            calls.append((SOUND, 0) + tuple(m.argument(k) for k in range(3)))
            return 0

        def stop(m):
            calls.append((Q_STOP, 0) + tuple(m.argument(k) for k in range(2)))
            return 0

        def register(m):
            assert m.argument(0) == v.OBJECTS
            calls.append((REGISTER, 0, m.argument(1)))
            return 0

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == (v.MODEL if present else 0)
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + k * 0x30 and 0 <= k < 64 and a[3] == 0, a
            local = tuple(struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12))))
            bones.append((k, local))
            m.uc.mem_write(a[2], v.pack_f(*position(k, local)))
            return (0, 16)

        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('frame-time', FRAME_TIME, v.pack_f(frame_time), writable=False),
            am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('isa', ISA, struct.pack('<I', 2 * (n % 2)), writable=False),
            am.defined_region('model', v.MODEL, bytes(model)),
            am.defined_region('actions', v.ACTIONS, bytes(table)),
            am.defined_region('handler', HANDLER, bytes(handler)),
            am.defined_region('hero-pointer', v.HERO_PTR, struct.pack('<I', v.HERO), writable=False),
            am.defined_region('hero-tile', v.HERO + 0x180, struct.pack('<ii', *hero_tile), writable=False),
            am.defined_region('hero', v.HERO + 0x33ac, v.pack_f(*hero), writable=False)])
        args = [0 if null_object else v.OBJECTS]
        if method == 'visual':
            args.append(v.MODEL if present else 0)
        stubs = {PARTICLE: particle, SPRITE: sprite, LIGHT: light, EFFECT: effect, SOUND: sound, STOP: stop,
                 REGISTER: register, BONE: bone, 0x1989721: lambda m: rnd(), 0x966cc4: lambda m: v.FAKE,
                 0xeaa8cf: lambda m: (v.MODEL if present else 0, 4)}
        hook = None
        if name == 'swamp_visual':
            def now_hook(u, address, size, ignored):
                u.reg_write(UC_X86_REG_EAX, now)
                u.reg_write(UC_X86_REG_EIP, TIME_CALL[1])
            hook = machine.uc.hook_add(UC_HOOK_CODE, now_hook, begin=TIME_CALL[0], end=TIME_CALL[0])
            machine.uc.ctl_flush_tb()
        try:
            result = v.run(machine, BODIES[name][0], args, regs, stubs, ecx=HANDLER,
                           cleanup=8 if method == 'visual' else 4)
        finally:
            if hook is not None:
                machine.uc.hook_del(hook)
        stop_reason = v.stopped_reason(result)
        if stop_reason:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop_reason)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        ctable = C.create_string_buffer(bytes(table), len(table))
        log = v.new_log()
        target = None if null_object else co

        def actions_cb(ctx, t, out):
            out[0] = count
            return C.addressof(ctable) if present else None

        def bone_cb(ctx, k, local, out):
            local = tuple(local[:3])
            cbones.append((k, local))
            for q, value in enumerate(position(k, local)):
                out[q] = value
        ch = Handler(ferea_state, None, handler[0x78], None)
        inputs = Inputs(world, time, frame_time, now, (C.c_float * 3)(*hero), (C.c_int32 * 2)(*hero_tile),
                        ACTIONS_FN(actions_cb), v.RAND_FN(lambda ctx: crnd()), BONE_FN(bone_cb), None,
                        C.pointer(ch))
        fn = getattr(lib.dll, 'mu_' + name)
        if method == 'create':
            handled = fn(target, 0, C.byref(inputs), C.byref(log)) if prefix == 'kubera' else fn(target,
                                                                                                    C.byref(inputs))
        elif method == 'move':
            handled = fn(target, C.byref(inputs)) if prefix == 'swamp' else fn(target, 0, C.byref(inputs),
                                                                               C.byref(log))
        elif prefix == 'acheron':
            handled = fn(target, 0, C.byref(inputs), C.byref(log))
        else:
            handled = fn(target, 0, int(present), C.byref(inputs), C.byref(log))
        regions = result['regions']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != regions['object'][k]]
        h = regions['handler']
        object_address = C.addressof(co)
        handler_ok = (struct.unpack_from('<i', h, 0x48)[0] == ferea_state and
                      (struct.unpack_from('<I', h, 0x50)[0] == v.OBJECTS) == (ch.ferea_object == object_address) and
                      (struct.unpack_from('<I', h, 0x14)[0] == v.OBJECTS) == (ch.kubera_object == object_address) and
                      bool(ch.ferea_object or ch.kubera_object) <= (not null_object))
        table_ok = ctable.raw == bytes(regions['actions'])
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null object', int(null_object))
        tally.count('events', len(calls))
        tally.count('action changed', int(regions['object'][0x2a:0x2c] != bytes(raw[0x2a:0x2c])))
        tally.count('bones', len(bones))
        tally.count('requests ' + ','.join(sorted({hex(c[0]) for c in calls})) if calls else 'no requests')
        if method == 'visual':
            tally.count('model absent', int(not present))
        ok = (not diff and handled == (result['eax'] & 255) and calls == v.log_events(log) and
              rnd.seed == crnd.seed and bones == cbones and handler_ok and table_ok)
        tally.add(ok, {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                       'c_al': handled, 'calls': calls[:3], 'c': v.log_events(log)[:3], 'bones': bones[:3],
                       'cbones': cbones[:3], 'handler_ok': handler_ok, 'table_ok': table_ok,
                       'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


def raw_f(raw, offset):
    return struct.unpack_from('<f', raw, offset)[0]


A, F, S, K = 'acheron.c', 'ferea.c', 'swamp_darkness.c', 'kubera.c'
MUTANTS = [
    (A, 'world == 0x5b || world == 0x5c', 'world == 0x5b', 'acheron_create'),
    (A, 'mu_obj_set_f32(o, MU_OBJF_RANGE, -428.571442f)', 'mu_obj_set_f32(o, MU_OBJF_RANGE, -428.0f)', 'acheron_create'),
    (A, 'case 38: case 54:', 'case 54:', 'acheron_create'),
    (A, 'rgb[3] = {s * 1.2f, s * 0.5f, s * 0.7f}', 'rgb[3] = {s * 1.2f, s * 0.6f, s * 0.7f}', 'acheron_move'),
    (A, '% 3 + 4', '% 3 + 3', 'acheron_move'),
    (A, 'q_set_action(in, o, 0);\n        mu_obj_set_i32(o, 0x64, mu_obj_i32(o, 0x64) - 1);',
     'mu_obj_set_i32(o, 0x64, mu_obj_i32(o, 0x64) - 1);', 'acheron_move'),
    (A, 'BLEND_V) - 0.03f', 'BLEND_V) - 0.02f', 'acheron_move'),
    (A, 'flicker(in, 4)', 'flicker(in, 3)', 'acheron_move'),
    (A, 'bone_sprite(in, log, index, 11, 1.5f, b)', 'bone_sprite(in, log, index, 12, 1.5f, b)', 'acheron_visual'),
    (A, 'k <= 28; k += 6', 'k <= 22; k += 6', 'acheron_visual'),
    (A, '% 3000) * 0.00104666676f', '% 3600) * 0.00104666676f', 'acheron_visual'),
    (A, 'q_sprite(log, index, 0x7f67, p, 1.20000005f + s, light, -r)',
     'q_sprite(log, index, 0x7f67, p, 1.20000005f + s, light, r)', 'acheron_visual'),
    (A, 'p[2] += 15.0f;', 'p[2] += 16.0f;', 'acheron_visual'),
    (A, 'q_sprite(log, index, 0x8155, p, s, light, 0.0f);\n            q_sprite',
     'q_sprite', 'acheron_visual'),
    (A, 'k == 6 || k == 10 || k == 11', 'k == 6 || k == 10', 'acheron_visual'),
    (A, 'q_particle(log, index, 0x7f89, pos, angle, light, 0x14, scale, 1)',
     'q_particle(log, index, 0x7f89, pos, angle, light, 0x14, scale, 0)', 'acheron_visual'),
    (F, 'case 137: case 152:', 'case 152:', 'ferea_create'),
    (F, 'q_set_action(in, o, in->handler->ferea_state);', 'q_set_action(in, o, 0);', 'ferea_create'),
    (F, '0.0f, 0.159999996f, 100', '0.0f, 0.159999996f, 10', 'ferea_move'),
    (F, 'tx <= 48', 'tx < 48', 'ferea_move'),
    (F, '(y - 80.0f) - y', '(y + 80.0f) - y', 'ferea_move'),
    (F, 'ferea_state == 3', 'ferea_state == 2', 'ferea_move'),
    (F, 'colour[0] = colour[1] = colour[2] = 0.300000012f;', 'colour[1] = colour[2] = 0.300000012f;', 'ferea_move'),
    (F, 'q_cos(a) * dx + x - q_sin(a) * dy', 'q_cos(a) * dx + x + q_sin(a) * dy', 'ferea_move'),
    (S, 'case 116: case 117: case 124:', 'case 116: case 117:', 'swamp_create'),
    (S, 'case 2: mu_obj_set_i32(o, MU_OBJF_TYPE, 107)', 'case 2: mu_obj_set_i32(o, MU_OBJF_TYPE, 108)', 'swamp_create'),
    (S, 'q_rand_range(in, 4.0f, 10.0f, 1)', 'q_rand_range(in, 4.0f, 9.0f, 1)', 'swamp_create'),
    (S, 'q_rand_range(in, 15.0f, 25.0f, 1)', 'q_rand_range(in, 15.0f, 24.0f, 1)', 'swamp_move'),
    (S, 'if (mu_obj_i32(o, 0x64) <= 0) {', 'if (mu_obj_i32(o, 0x64) < 0) {', 'swamp_move'),
    (S, 'phase < 30u', 'phase <= 30u', 'swamp_visual'),
    (S, '% 5 == 1', '% 5 == 0', 'swamp_visual'),
    (S, 'q_effect(log, index, o, 0x59a, white, 3, 0)', 'q_effect(log, index, o, 0x59a, white, 2, 0)', 'swamp_visual'),
    (K, 'case 134:\n        o[MU_OBJF_AFTER_CHARACTER] = 1;', 'case 134:', 'kubera_create'),
    (K, 'case 107: case 125: case 140: case 145: case 154:', 'case 107: case 125: case 140: case 154:', 'kubera_create'),
    (K, 'memcpy(o + 0x140, o + MU_OBJF_ANGLE, 12);', '', 'kubera_create'),
    (K, 'table[16 * k + 0xa] = 0;', '', 'kubera_create'),
    (K, '<= 900.0f', '< 900.0f', 'kubera_move'),
    (K, 'action >= 3 ? 0 : action + 1', 'action >= 2 ? 0 : action + 1', 'kubera_move'),
    (K, 'context) % 10 + 5', 'context) % 10 + 4', 'kubera_move'),
    (K, '(float)(q_keys(record) / 2)', '(float)q_keys(record) / 2.0f', 'kubera_move'),
    (K, 'stop_sound(log, index, 0x4f2);\n', '', 'kubera_move'),
    (K, '% 15 + 15', '% 15 + 14', 'kubera_move'),
    (K, 'mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, 0.0f);', '', 'kubera_move'),
    (K, '% 80 == 1', '% 80 == 0', 'kubera_visual'),
    (K, '!kubera_world(in->world) || !o || !model_present)\n        return 0;\n    if',
     '!kubera_world(in->world) || !o || model_present < 0)\n        return 0;\n    if', 'kubera_visual')]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=1000)
    ap.add_argument('--only', help='comma-separated families')
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    lib = bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}'))
    sha = lambda s, e: hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()
    names = [n for n in BODIES if not a.only or n in a.only.split(',')]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)} for n, (s, e) in BODIES.items()},
              'tables': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)} for n, (s, e) in TABLES.items()},
              'predicates': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)}
                             for n, (s, e) in PREDICATES.items()},
              'families': {}, 'mutants': []}
    for name in names:
        r = report['families'][name] = family(machine, lib, name, a.cases)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-q-') as tmp:
            for n, (file, old, new, name) in enumerate(MUTANTS):
                if name not in names:
                    continue
                dest = Path(tmp) / str(n)
                for directory in ('objects', 'terrain', 'model-codec', 'record-math', 'movement'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__'))
                p = dest / 'objects' / file
                s = p.read_text()
                assert old in s, old
                p.write_text(s.replace(old, new, 1))
                mutated = bind(v.Library(v.build_library(dest)))
                r = family(machine, mutated, name, a.cases)
                m = {'family': name, 'file': file, 'change': new, 'detected': r['mismatch_count'],
                     'stopped': r['stopped']}
                report['mutants'].append(m)
                print('mutant', m, flush=True)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
