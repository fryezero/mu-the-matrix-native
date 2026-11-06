#!/usr/bin/env python3
"""Imperial Guardian (69..72), Event square (114) and Test Area (121) primary slots against pinned instructions.

Every create, move and visual body of the six classes. AL, all OBJECT bytes, ordered output calls with their
constant arguments asserted, the Imperial Guardian class static (type 20's shared frame) and the final MSVC RNG
are compared. rand, CreateParticle, CreateSprite, CreateJoint, CreateEffect, the model lookup, the animation tick
0x012b4dd3, TransformPosition, Animation and AddTerrainLight are recording boundaries; the predicates, the alpha
step 0x012af883, AngleMatrix 0x00cff32a, VectorRotate 0x00d000ad, the CRT sine wrapper, fabs, the vector
accessors, the sprite descriptor and Test Area's empty base call execute as original code.
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
CREATE = {69: (0xdc6fab, 0xdc7136), 70: (0xdd3c76, 0xdd3e01), 71: (0xdd8d6d, 0xdd8ef8), 72: (0xdde9e0, 0xddeb8a)}
MOVE = {69: (0xdc7136, 0xdc73d0), 70: (0xdd3e01, 0xdd4097), 71: (0xdd8ef8, 0xdd9192), 72: (0xddeb8a, 0xddee5e)}
VISUAL = {69: (0xdc73d0, 0xdc8b33), 70: (0xdd4097, 0xdd57fa), 71: (0xdd9192, 0xdda8f5), 72: (0xddee5e, 0xde08df)}
BODIES = {}
for cls in (69, 70, 71, 72):
    BODIES['ig%d_create' % cls] = CREATE[cls]
    BODIES['ig%d_move' % cls] = MOVE[cls]
# the big visuals split by type group (each family runs the whole body; the groups steer its samples)
for name in ('ig69_visual_bones', 'ig69_visual_frames', 'ig69_visual_emitters', 'ig70_visual', 'ig71_visual',
             'ig72_visual_bones', 'ig72_visual_frames', 'ig72_visual_emitters'):
    BODIES[name] = VISUAL[int(name[2:4])]
BODIES.update({'square_create': (0xe1e989, 0xe1ea5c), 'square_move': (0xe1ea5c, 0xe1ef15),
               'square_visual': (0xe1ef15, 0xe1f6ca),   # through the custom-render slot
               'test_create': (0xd585b0, 0xd58809), 'test_move': (0xd58809, 0xd58888),
               'test_visual': (0xd58888, 0xd58bd8)})
GROUPS = {'bones': [12, 37, 50, 157], 'frames': [20, 51, 64],
          'emitters': [79, 80, 82, 83, 84, 85, 86, 129, 130, 131, 132, 158]}
IG_TYPES = sorted(set(sum(GROUPS.values(), [])) | {10, 0x14, 0x24, 0x40, 0x4f, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56,
                                                   0x73, 0x75, 0x7a, 0x7b, 0x7c, 0x80, 0x81, 0x82, 0x83, 0x84})
EXTREMES = [-2147483648, -1, 0, 2147483647, 1000]
DIRECTED_MOVE = [20, 20, 20, 10, 0x40, 0x24, 0x51, 0x52, 0x84, 122, 128]   # move cases, type 20's class static first
SIBLINGS = [0, 68, 69, 70, 71, 72, 73, 74, 79, 114, 121]
LOCK = 0x1ec9164   # the classes' statics, 4 bytes each from 69
TICK, ANGLE_EFFECT = 0x12b4dd3, 0x13c0eaa
JOINT, R2_EFFECT, CREATE_EFFECT = 0x153b02c, 0x00e68c23, 0x013c0eaa
JOINT_TAIL = [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]
UNINIT_LIGHT = {82, 158}   # their particle light is uninitialized stack in the original: zero on both sides
COOKIE = 0x01cf65c0
SQUARE_TYPES = [-2147483648, -1, 0, 8, 29, 30, 31, 34, 35, 36, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 66, 67,
                68, 69, 2147483647]
TEST_TYPES = [-1, 0, 21, 22, 23, 69, 70, 71, 79, 80, 81, 0x1a7, 0x1a8, 0x1a9, 0x1aa, 0x1ab, 0x1ac, 2147483647]
FRAMES = [5.4, 5.4000001, 5.5, 6.4999995, 6.5, 15.4, 15.5, 16.4999, 16.5, 9.5, 10.0, 11.5, 23.5, 24.0, 25.4999, 25.5,
          0.0, -0.0, math.nan, 100.0]


def bind(lib):
    d = lib.dll
    P, I, L = C.c_void_p, C.c_int32, C.POINTER(v.Log)
    d.mu_imperial_create.argtypes = [P, I, v.RAND_FN, P]
    d.mu_imperial_move.argtypes = [P, I, I, I, C.c_int, C.POINTER(C.c_float), L]
    d.mu_imperial_visual.argtypes = [P, I, I, C.POINTER(q.Inputs), L]
    d.mu_imperial_visual_bones.argtypes = [I, I]
    d.mu_market_create.argtypes = [P, I, L]
    d.mu_event_square_move.argtypes = [P, I, C.POINTER(v.MoveInputs), L]
    bone = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))
    d.mu_event_square_visual.argtypes = [P, I, I, C.c_float, v.RAND_FN, bone, P, L]
    d.mu_test_area_create.argtypes = [P, I, L]
    d.mu_test_area_move.argtypes = [P, C.c_float]
    d.mu_test_area_visual.argtypes = [P, I, C.c_int, v.RAND_FN, P, L]
    for name in ('mu_imperial_create', 'mu_imperial_move', 'mu_imperial_visual', 'mu_market_create',
                 'mu_event_square_move', 'mu_event_square_visual', 'mu_test_area_create', 'mu_test_area_move',
                 'mu_test_area_visual'):
        getattr(d, name).restype = C.c_int
    return lib


def time_sample(g):
    return v.f32(g.choice([0.0, -0.0, 1.0, 2.0, 2.5, 199.5, 200.0, 201.0, 202.0, 401.5, -199.0, 1000.0, -1000.0,
                           1963.4954, 40000.0, 2147483520.0, 3e9, -1e12, math.nan, g.uniform(-1e6, 1e6),
                           g.uniform(0, 1e5)]))


def seed_open(g, typ):
    """A seed whose first rand opens the type's 1-in-N branch (or a random seed)."""
    modulus = {84: 8, 86: 6, 129: 6, 130: 6, 131: 3, 132: 3}.get(typ)
    while True:
        seed = g.getrandbits(32)
        if modulus is None or v.MsvcRand(seed)() % modulus == 0:
            return seed


class Recorder:
    """Recording stubs of the output services; `typ` and `uninit` steer the uninitialized-light substitution."""
    def __init__(self, raw, typ, rnd):
        self.calls, self.bones, self.raw, self.typ, self.rnd = [], [], raw, typ, rnd

    def particle(self, m):
        a = [m.argument(k) for k in range(8)]
        assert a[6] in (0, v.OBJECTS) and a[7] == 0, a
        light = (0, 0, 0) if self.typ in UNINIT_LIGHT else v.read_vec(m, a[3])
        self.calls.append((q.PARTICLE, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + light +
                          (a[4], a[5], int(a[6] == v.OBJECTS)))
        return 0

    def sprite(self, m):
        a = [m.argument(k) for k in range(9)]
        assert a[4] == v.OBJECTS and a[6:8] == [0, 4] and v.read_vec(m, a[8]) == (1, 1, v.bits(1.0)), a
        self.calls.append((q.SPRITE, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) + (a[5], 1, 0, 4))
        return 0

    def joint(self, m):
        a = [m.argument(k) for k in range(14)]
        assert a[5] == v.OBJECTS and a[7:] == JOINT_TAIL, a
        self.calls.append((JOINT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                          (a[4], 1, a[6]))
        return 0

    def effect(self, m):
        a = [m.argument(k) for k in range(14)]
        assert a[5] in (0, v.OBJECTS) and a[6] == 0xffffffff and a[7] == 0 and a[9:] == [0, 0, 0xffffffff, 0, 0], a
        self.calls.append((R2_EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                          (a[4], int(a[5] == v.OBJECTS), a[8]))
        return 0

    def create_effect(self, m):
        a = [m.argument(k) for k in range(14)]
        assert a[2] == v.OBJECTS + 0x164 and a[3] == v.OBJECTS + 0xec, a
        assert a[4:] == [1, 0, 0xffffffff, 0, 0, 0, 0, 0xffffffff, 0, 0], a
        self.calls.append((CREATE_EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + (0x164, 0xec) + tuple(a[4:]))
        return 0

    def bone(self, m):
        a = [m.argument(k) for k in range(4)]
        assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL and a[3] == 0, a
        k = (a[0] - 0x6fce398) // 0x30
        assert a[0] == 0x6fce398 + k * 0x30 and 0 <= k < 64, a
        local = tuple(struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12))))
        self.bones.append((k,) + tuple(v.bits(x) for x in local))
        m.uc.mem_write(a[2], v.pack_f(*q.position(k, local)))
        return (0, 16)

    def tick(self, m):
        a = [m.argument(k) for k in range(6)]
        assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL, hex(m.uc.reg_read(UC_X86_REG_ECX))
        assert a[:3] == [v.OBJECTS + 0xd0, v.OBJECTS + 0xd4, v.OBJECTS + 0x2c] and \
            a[4:] == [v.OBJECTS + 0x158, v.OBJECTS + 0x164], a
        self.calls.append((TICK, 0, a[3]))
        return (0, 24)


def ig_object(g, world, typ, family):
    raw = bytearray(v.move_object(g, world, 'full'))
    v.put_i(raw, 0x5c, typ)
    v.put_i(raw, 0x60, g.choice([-1, 0, 0, 1, 2, 50, 99, g.randrange(-5, 200)]))
    if g.random() < 0.6:
        v.put_f(raw, 0xd0, v.f32(g.choice(FRAMES)), v.f32(g.uniform(0, 30)))
    else:
        v.put_f(raw, 0xd0, v.f32(g.uniform(-1, 30)), v.f32(g.uniform(0, 30)))
    if g.random() < 0.3:   # alpha around the 0.01 gate, NaN included; target equal, so the step keeps it
        alpha = v.f32(g.choice([0.01, 0.01, 0.0099999998, 0.010000001, 0.0, -0.0, math.nan, 1.0]))
        v.put_f(raw, 0xd8, alpha, alpha)
    if g.random() < 0.3:   # angle z around the modulus, extremes and NaN
        v.put_f(raw, 0x164 + 8, v.f32(g.choice([359.9, 360.0, -360.0, 720.5, -0.0, 3e9, -3e9, math.nan, 1e-30,
                                                g.uniform(-1e5, 1e5)])))
    if g.random() < 0.2:
        v.put_f(raw, 0xa0, v.f32(g.choice([0.0, -0.0, 65535.9, 65536.0, 70000.0, -1.0, math.nan, 3e9])))
    if g.random() < 0.15:
        v.put_f(raw, 0xb0, v.f32(g.choice([math.nan, 1e30, -0.0, g.uniform(-10, 10)])))
    return raw


def ig_family(machine, lib, name, cases):
    g = random.Random('worlds-s3-' + name)
    tally = v.Tally(name)
    cls, method = int(name[2:4]), name.split('_')[1]
    group = name.split('_')[2] if name.count('_') == 2 else None
    lo, hi = BODIES[name]
    for n in range(cases):
        if group and n % 4:
            typ = g.choice(GROUPS[group])
        elif method == 'move' and n % 4 == 1:
            typ = g.choice(DIRECTED_MOVE)
        elif n % 3 == 0:
            typ = g.choice(IG_TYPES)
        else:
            typ = g.choice(IG_TYPES + EXTREMES + [g.randrange(-20, 300)])
        world = cls if n % 5 else SIBLINGS[(n // 5) % len(SIBLINGS)]
        if cls == 72 and n % 5 == 2 and g.random() < 0.5:   # class 72's predicate also accepts 73 and 74
            world = g.choice([73, 74])
        present = n % 11 != 0
        raw = ig_object(g, world, typ, name)
        time = time_sample(g)
        seed = seed_open(g, typ) if method == 'visual' and g.random() < 0.6 else g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        near = struct.unpack_from('<f', raw, 0xd0)[0] + g.choice([-10.0, 10.0, 10.5, 10.9, 11.0, -0.5, 0.0, 0.0])
        lock_value = v.f32(near if typ == 20 and g.random() < 0.7 else
                           g.choice([0.0, 0.0, -0.0, 5.0, 10.0, 20.0, math.nan, g.uniform(-5, 40), near]))
        if typ == 20 and g.random() < 0.1:   # frame and lock opposite zeros: only the bits tell who copies whom
            zero = g.choice([0.0, -0.0])
            v.put_f(raw, 0xd0, zero)
            lock_value = -zero
        lock = bytearray(16)
        for k in range(4):
            struct.pack_into('<f', lock, 4 * k, v.f32(g.uniform(-5, 40)))
        struct.pack_into('<f', lock, 4 * (cls - 69), lock_value)
        rec = Recorder(raw, typ, rnd)
        model = bytearray(0x100)
        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('isa', q.ISA, struct.pack('<I', 2 * (n % 2)), writable=False),
            am.defined_region('lock', LOCK, bytes(lock)),
            am.defined_region('model', v.MODEL, bytes(model))])
        stubs = {0x1989721: lambda m: rnd(), q.PARTICLE: rec.particle, q.SPRITE: rec.sprite, JOINT: rec.joint,
                 ANGLE_EFFECT: rec.effect, q.BONE: rec.bone, TICK: rec.tick, 0x966cc4: lambda m: v.FAKE,
                 0xeaa8cf: lambda m: (v.MODEL if present else 0, 4)}
        args = [v.OBJECTS] + ([v.MODEL] if method == 'visual' else [])
        result = v.run(machine, lo, args, regs, stubs, ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        d = lib.dll
        crand = v.RAND_FN(lambda ctx: crnd())
        cbones = []
        clock = C.c_float(lock_value)
        if method == 'create':
            handled = d.mu_imperial_create(co, cls, crand, None)
        elif method == 'move':
            handled = d.mu_imperial_move(co, 0, cls, world, int(present), C.byref(clock), C.byref(log))
        else:
            def bone_cb(ctx, k, local, out):
                local = tuple(local[:3])
                cbones.append((k,) + tuple(v.bits(x) for x in local))
                for qq, value in enumerate(q.position(k, local)):
                    out[qq] = value
            inputs = q.Inputs(world, time, v.f32(0.1), 0, (C.c_float * 3)(), (C.c_int32 * 2)(), q.ACTIONS_FN(),
                              crand, q.BONE_FN(bone_cb), None, None)
            handled = d.mu_imperial_visual(co, 0, cls, C.byref(inputs), C.byref(log))
        events = v.log_events(log)
        regions = result['regions']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != regions['object'][k]]
        lock_after = bytes(regions['lock'])
        expected_lock = bytearray(lock)
        struct.pack_into('<f', expected_lock, 4 * (cls - 69), clock.value)
        lock_ok = lock_after == bytes(expected_lock)
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('handled' if handled == 1 else 'unhandled' if handled == 0 else 'refused')
        for c in rec.calls:
            tally.count('call ' + hex(c[0]))
        tally.add(not diff and handled == (result['eax'] & 255) and rec.calls == events and rec.bones == cbones and
                  lock_ok and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': rec.calls[:3], 'c': events[:3], 'bones': rec.bones[:2],
                   'c_bones': cbones[:2], 'lock_ok': lock_ok, 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


def square_family(machine, lib, name, cases):
    """Event square: Loren Market's bodies behind world 114 (the light service as in validate_worlds_i)."""
    g = random.Random('worlds-s3-' + name)
    tally = v.Tally(name)
    method = name.split('_')[1]
    for n in range(cases):
        typ = SQUARE_TYPES[n % len(SQUARE_TYPES)] if n % 7 else g.randrange(-10, 120)
        world = 114 if n % 5 else [0, 79, 113, 114, 115, 121][(n // 5) % 6]
        present = n % 7 != 3
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        time = v.f32(g.choice([0, -1000, 1000, 1570.79638671875, math.nan, g.uniform(-1e6, 1e6)]))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        rec = Recorder(raw, None, rnd)
        bones, cbones = [], []

        def position(k):
            return (float(k * 17 + 5), float(k * -13 + 7), float(k * 11 - 3))

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) in (v.MODEL, v.FAKE)
            assert a[3] == 0 and v.read_vec(m, a[1]) == (0, 0, 0)
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + k * 0x30 and k in (1, 2, 3)
            bones.append(k)
            m.uc.mem_write(a[2], v.pack_f(*position(k)))
            return (0, 16)

        def animation(m):
            a = [m.argument(k) for k in range(8)]
            assert a == [0x6fce398, struct.unpack_from('<I', raw, 0xd0)[0], struct.unpack_from('<I', raw, 0xd4)[0],
                         struct.unpack_from('<H', raw, 0x2c)[0], v.OBJECTS + 0x164, v.OBJECTS + 0x170, 0, 1]
            assert bytes(m.uc.mem_read(v.MODEL + 0x74, 16)) == raw[0xa0:0xa4] + raw[0x158:0x164]
            return (0, 32)

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            k = 1 if typ == 30 else 2
            assert bones == [k] and (a[0], a[1]) == tuple(v.bits(x) for x in position(k)[:2])
            rec.calls.append((0xe6c29d, 0, k) + v.read_vec(m, a[2]) + (a[3],))   # MU_MARKET_BONE_LIGHT
            return 0

        def register(m):
            assert [m.argument(k) for k in range(2)] == [v.OBJECTS, 1]
            rec.calls.append((0x16d9f51, 0, 1))
            return 0
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                           am.defined_region('model', v.MODEL, bytes(0x100))])
        stubs = {0x966cc4: lambda m: v.FAKE, 0xeaa8cf: lambda m: (v.MODEL if present else 0, 4),
                 0x12b5064: animation, 0x12b6ef1: bone, 0x16cacfc: light, 0x16d9f51: register,
                 q.PARTICLE: rec.particle, q.SPRITE: rec.sprite, 0x1989721: lambda m: rnd()}
        result = v.run(machine, BODIES[name][0], [v.OBJECTS] + ([v.FAKE] if method == 'visual' else []), regs, stubs,
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        d = lib.dll
        if method == 'create':
            handled = d.mu_market_create(co, 0, C.byref(log))
        elif method == 'move':
            inputs = v.MoveInputs()
            inputs.world, inputs.time, inputs.has_model, inputs.rand_fn = world, time, present, fn
            handled = d.mu_event_square_move(co, 0, C.byref(inputs), C.byref(log))
        else:
            def cb(ctx, k, local, out):
                assert list(local[:3]) == [0, 0, 0]
                cbones.append(k)
                for qq, value in enumerate(position(k)):
                    out[qq] = value
            bone_fn = d.mu_event_square_visual.argtypes[5](cb)
            handled = d.mu_event_square_visual(co, 0, world, time, fn, bone_fn, None, C.byref(log))
        events = v.log_events(log)
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('events', len(rec.calls))
        tally.add(not diff and handled == (result['eax'] & 255) and rec.calls == events and rnd.seed == crnd.seed and
                  (method != 'visual' or bones == cbones),
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': rec.calls[:3], 'c': events[:3], 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


def test_family(machine, lib, name, cases):
    g = random.Random('worlds-s3-' + name)
    tally = v.Tally(name)
    method = name.split('_')[1]
    for n in range(cases):
        typ = TEST_TYPES[n % len(TEST_TYPES)] if n % 5 else g.randrange(-10, 500)
        world = 121 if n % 3 else g.choice([0, 69, 114, 120, 121, 122])
        present = n % 7 != 0
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        if n % 6 == 0:
            v.put_f(raw, 0x158, *(v.f32(g.choice([0.0, -0.0, math.nan, 1e30, -1e30, 3e-39, g.uniform(-1e5, 1e5)]))
                                  for _ in range(3)))
        time = time_sample(g)
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        rec = Recorder(raw, None, rnd)
        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('isa', q.ISA, struct.pack('<I', 2 * (n % 2)), writable=False),
            am.defined_region('model', v.MODEL, bytes(0x100))])
        stubs = {0x1989721: lambda m: rnd(), q.PARTICLE: rec.particle, CREATE_EFFECT: rec.create_effect}
        args = [v.OBJECTS] + ([v.MODEL if present else 0] if method == 'visual' else [])
        result = v.run(machine, BODIES[name][0], args, regs, stubs, ecx=v.FAKE,
                       cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        d = lib.dll
        if method == 'create':
            handled = d.mu_test_area_create(co, 0, C.byref(log))
        elif method == 'move':
            handled = d.mu_test_area_move(co, time)
        else:
            handled = d.mu_test_area_visual(co, 0, int(present), v.RAND_FN(lambda ctx: crnd()), None, C.byref(log))
        events = v.log_events(log)
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('handled' if handled else 'unhandled')
        for c in rec.calls:
            tally.count('call ' + hex(c[0]))
        tally.add(not diff and handled == (result['eax'] & 255) and rec.calls == events and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': rec.calls[:3], 'c': events[:3], 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


def family(machine, lib, name, cases):
    if name.startswith('ig'):
        return ig_family(machine, lib, name, cases)
    if name.startswith('square'):
        return square_family(machine, lib, name, cases)
    return test_family(machine, lib, name, cases)


MUTANTS = [
    ('imperial_guardian.c', 't == 0x73 || t == 0x75', 't == 0x73 || t == 0x76', 'ig69_create'),
    ('imperial_guardian.c', 'mu_obj_set_i32(o, 0x60, 100);', 'mu_obj_set_i32(o, 0x60, 101);', 'ig70_create'),
    ('imperial_guardian.c', 'rnd(context) % 50);', 'rnd(context) % 49);', 'ig72_create'),
    ('imperial_guardian.c', 'if (cls == 72 && t == 10) {   /* class 72 only */',
     'if (cls >= 71 && t == 10) {   /* class 72 only */', 'ig71_create'),
    ('imperial_guardian.c', 'if (t < 0x81 || t > 0x84)', 'if (t < 0x81 || t > 0x83)', 'ig69_create'),
    ('imperial_guardian.c', ') % 360));', ') % 359));', 'ig71_create'),
    ('imperial_guardian.c', 'memcpy(o + MU_OBJF_POSITION_COPY, o + MU_OBJF_POSITION, 12);',
     'memcpy(o + MU_OBJF_POSITION_COPY, o + MU_OBJF_POSITION, 8);', 'ig72_create'),
    ('imperial_guardian.c', 'world == cls;\n}', 'world == cls || world == 0;\n}', 'ig69_move'),
    ('imperial_guardian.c', 'world >= 72 && world <= 74 :', 'world >= 72 && world <= 73 :', 'ig72_move'),
    ('imperial_guardian.c', 'mu_obj_alpha_step(o);   /* again', '/* omitted */   /* again', 'ig70_move'),
    ('imperial_guardian.c', 'if (0.01f > mu_obj_f32(o, MU_OBJF_ALPHA) || !has_model)',
     'if (0.01f >= mu_obj_f32(o, MU_OBJF_ALPHA) || !has_model)', 'ig71_move'),
    ('imperial_guardian.c', 'speed = speed * 2.0f;', 'speed = speed * 2.5f;', 'ig69_move'),
    ('imperial_guardian.c', 't >= 122 && t <= 124', 't >= 122 && t <= 123', 'ig70_move'),
    ('imperial_guardian.c', 'speed = speed * 6.0f;', 'speed = speed * 5.0f;', 'ig71_move'),
    ('imperial_guardian.c', 'mu_obj_set_i32(o, 0x60, mu_obj_i32(o, 0x60) - 1);',
     'mu_obj_set_i32(o, 0x60, mu_obj_i32(o, 0x60) - 2);', 'ig72_move'),
    ('imperial_guardian.c', 'mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, 0.0f);', '/* prior frame kept */', 'ig72_move'),
    ('imperial_guardian.c', '*frame_lock - frame > 10.0f', '*frame_lock - frame > 11.0f', 'ig69_move'),
    ('imperial_guardian.c', '|| frame > *frame_lock)', '|| frame >= *frame_lock)', 'ig72_move'),
    ('imperial_guardian.c', 'cls == 71 ? 0.44f : 0.64f', 'cls == 70 ? 0.44f : 0.64f', 'ig71_move'),
    ('imperial_guardian.c', 'MU_OBJF_VELOCITY, 0.02f);', 'MU_OBJF_VELOCITY, 0.03f);', 'ig70_move'),
    ('imperial_guardian.c', 'case 0x55: case 0x56:', 'case 0x55: case 0x57:', 'ig69_move'),
    ('imperial_guardian.c', 'if (cls != 70)\n            return 1;', 'if (cls != 71)\n            return 1;',
     'ig70_move'),
    ('imperial_guardian.c', 'MU_OBJF_BLEND_V) + 0.015f);', 'MU_OBJF_BLEND_V) + 0.016f);', 'ig72_move'),
    ('imperial_guardian.c', 'if (!imperial_world(cls, in->world))\n        return 0;\n    const int32_t t',
     'if (!imperial_world(cls, in->world) && in->world != 0)\n        return 0;\n    const int32_t t', 'ig70_visual'),
    ('imperial_guardian.c', 'if (in->world == 73 || in->world == 74)', 'if (in->world == 73)', 'ig72_visual_bones'),
    ('imperial_guardian.c', '* 0.0008))) * 0.9f + 0.1f;', '* 0.0008))) * 0.8f + 0.1f;', 'ig69_visual_bones'),
    ('imperial_guardian.c', 'local3[3] = {3.0f, -3.0f, -3.5f}', 'local3[3] = {3.0f, -3.0f, -3.0f}',
     'ig69_visual_bones'),
    ('imperial_guardian.c', 'q_sprite(log, i, 0x7f6b, p, 0.5f, red, 0.0f);',
     'q_sprite(log, i, 0x7f6b, p, 0.4f, red, 0.0f);', 'ig72_visual_bones'),
    ('imperial_guardian.c', 'in->time * 0.039f) + 1.0f) * 0.2f', 'in->time * 0.039f) + 1.0f) * 0.3f',
     'ig69_visual_bones'),
    ('imperial_guardian.c', 'for (int k = 2; k <= 7; ++k)', 'for (int k = 2; k <= 6; ++k)', 'ig72_visual_bones'),
    ('imperial_guardian.c', 'blue[3] = {0.05f, 0.1f, 0.3f}', 'blue[3] = {0.05f, 0.1f, 0.35f}', 'ig71_visual'),
    ('imperial_guardian.c', 'first[3] = {22, 23, 25}', 'first[3] = {22, 23, 24}', 'ig72_visual_bones'),
    ('imperial_guardian.c', 'for (int n = 0; n < 4; ++n)', 'for (int n = 0; n < 3; ++n)', 'ig72_visual_bones'),
    ('imperial_guardian.c', '(float)((double)scale * 0.1), 1);', '(float)((double)scale * 0.12), 1);',
     'ig72_visual_bones'),
    ('imperial_guardian.c', 'if (frame > 5.4f && 6.5f > frame)', 'if (frame > 5.5f && 6.5f > frame)',
     'ig69_visual_frames'),
    ('imperial_guardian.c', 't == 20 && frame > 15.4f', 't == 20 && frame > 15.5f', 'ig72_visual_frames'),
    ('imperial_guardian.c', '% 60 + 150);', '% 60 + 151);', 'ig69_visual_frames'),
    ('imperial_guardian.c', 'ANGLE + 8) + 180.0f :', 'ANGLE + 8) + 90.0f :', 'ig69_visual_frames'),
    ('imperial_guardian.c', 'wb_arg(e, 5); wb_arg(e, 1); wb_float(e, 10.0f);',
     'wb_arg(e, 5); wb_arg(e, 1); wb_float(e, 12.0f);', 'ig70_visual'),
    ('imperial_guardian.c', 'q_particle(log, i, 0x7f25, p, a, l, 0xb, 1.0f, 0);',
     'q_particle(log, i, 0x7f25, p, a, l, 0xb, 1.0f, 1);', 'ig72_visual_frames'),
    ('imperial_guardian.c', 'if (t == 51 && cls == 72)', 'if (t == 51 && cls == 71)', 'ig72_visual_frames'),
    ('imperial_guardian.c', '(frame > 23.5f && 25.5f > frame)', '(frame > 23.5f && 25.0f > frame)',
     'ig69_visual_frames'),
    ('imperial_guardian.c', 'a[2] + 90.0f}', 'a[2] + 80.0f}', 'ig72_visual_frames'),
    ('imperial_guardian.c', 'p[k] = v[k] + p[k];', 'p[k] = v[0] + p[k];', 'ig69_visual_frames'),
    ('imperial_guardian.c', 'q_particle(log, i, 0x7f89, p, a, l, 0x16, scale, 1);',
     'q_particle(log, i, 0x7f89, p, a, l, 0x16, scale, 0);', 'ig71_visual'),
    ('imperial_guardian.c', 'orange[3] = {1.0f, 0.2f, 0.0f}', 'orange[3] = {1.0f, 0.25f, 0.0f}',
     'ig69_visual_emitters'),
    ('imperial_guardian.c', 'else if (r == 1) here(log, i, o, 0x806e, white, 4, scale, 0);',
     'else if (r == 1) here(log, i, o, 0x806e, white, 5, scale, 0);', 'ig72_visual_emitters'),
    ('imperial_guardian.c', 'in->time * 0.04f) + 1.0f) * 0.3f + 0.4f', 'in->time * 0.04f) + 1.0f) * 0.3f + 0.5f',
     'ig69_visual_emitters'),
    ('imperial_guardian.c', 'here(log, i, o, 0x801e, zero, 9, scale, 0);',
     'here(log, i, o, 0x801e, zero, 8, scale, 0);', 'ig70_visual'),
    ('imperial_guardian.c', 'here(log, i, o, 0x801c, white, 0xe, scale, 0);',
     'here(log, i, o, 0x801c, white, 0xd, scale, 0);', 'ig69_visual_emitters'),
    ('imperial_guardian.c', 'rand_fn(in->context) % 8 == 0', 'rand_fn(in->context) % 8 == 1',
     'ig72_visual_emitters'),
    ('imperial_guardian.c', 'wb_int(in->time) % 200;', 'wb_int(in->time) % 300;', 'ig69_visual_emitters'),
    ('imperial_guardian.c', 'phase < 0 || phase > 1', 'phase < 0 || phase > 2', 'ig72_visual_emitters'),
    ('imperial_guardian.c', 'rand_fn(in->context) % 4 + 4;', 'rand_fn(in->context) % 4 + 3;',
     'ig69_visual_emitters'),
    ('imperial_guardian.c', 'wb_arg(e, (uint16_t)wb_int(scale));', 'wb_arg(e, (uint16_t)wb_int(scale) + 1u);',
     'ig71_visual'),
    ('imperial_guardian.c', 'rand_fn(in->context) % 6 != 0', 'rand_fn(in->context) % 5 != 0',
     'ig69_visual_emitters'),
    ('imperial_guardian.c', 't == 130 ? 0.05f : 0.02f', 't == 129 ? 0.05f : 0.02f', 'ig72_visual_emitters'),
    ('imperial_guardian.c', 'here(log, i, o, 0x7f5a, white, 0x16, scale, 0);',
     'here(log, i, o, 0x7f5a, white, 0x16, scale, 1);', 'ig69_visual_emitters'),
    ('imperial_guardian.c', 'here(log, i, o, 0x7f5a, white, 0x15, scale * 2.0f, 1);',
     'here(log, i, o, 0x7f5a, white, 0x15, scale * 3.0f, 1);', 'ig72_visual_emitters'),
    ('imperial_guardian.c', 'here(log, i, o, 0x7f5a, zero, 0x40, scale, 1);',
     'here(log, i, o, 0x7f5a, zero, 0x41, scale, 1);', 'ig72_visual_emitters'),
    ('loren_market.c', 'if (in->world != 114)', 'if (in->world != 113)', 'square_move'),
    ('loren_market.c', 'if (world != 114)', 'if (world != 115)', 'square_visual'),
    ('loren_market.c', 'case 50: case 51: case 52: case 53: case 59:', 'case 50: case 51: case 52: case 53: case 58:',
     'square_create'),
    ('loren_market.c', 'mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.2f);', 'mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.25f);',
     'square_move'),
    ('loren_market.c', 'wv_sprite(index, 0x7ef7, p, 20.0f * scale, l, log);',
     'wv_sprite(index, 0x7ef7, p, 19.0f * scale, l, log);', 'square_visual'),
    ('test_area.c', 'if (t == 0x1a8)', 'if (t == 0x1a9)', 'test_create'),
    ('test_area.c', 'warp_effect(log, i, o, 0x1ac, 36.0f);', 'warp_effect(log, i, o, 0x1ac, 35.0f);', 'test_create'),
    ('test_area.c', '+ 520.0f);', '+ 500.0f);', 'test_create'),
    ('test_area.c', '{MU_OBJF_ANGLE, MU_OBJF_LIGHT, 1, 0,', '{MU_OBJF_ANGLE, MU_OBJF_LIGHT, 2, 0,', 'test_create'),
    ('test_area.c', 'q_sin(time * 0.001f) + 1.0f);', 'q_sin(time * 0.002f) + 1.0f);', 'test_move'),
    ('test_area.c', 'case 70: case 80:\n        mu_obj_set_i32', 'case 70: case 81:\n        mu_obj_set_i32',
     'test_move'),
    ('test_area.c', 'if (!has_model)\n        return 0;', 'if (has_model < 0)\n        return 0;', 'test_visual'),
    ('test_area.c', 'red[3] = {0.7f, 0.2f, 0.1f}', 'red[3] = {0.7f, 0.2f, 0.15f}', 'test_visual'),
    ('test_area.c', 'else if (r == 1) q_particle(log, i, 0x8087, p, a, l, 6, scale, 0);',
     'else if (r == 1) q_particle(log, i, 0x8087, p, a, l, 5, scale, 0);', 'test_visual'),
    ('test_area.c', 'rnd(context) % 3;', 'rnd(context) % 2;', 'test_visual')]


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
        with tempfile.TemporaryDirectory(prefix='worlds-s3-') as tmp:
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
