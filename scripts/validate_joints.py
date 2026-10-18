#!/usr/bin/env python3
"""Compare reconstructed/joints with the client's instructions (NATIVE-JOINT-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case),
with the machine, stubs and x87 helpers of scripts/validate_skill_fx.py. The
authored C (libclient_joints) runs on the same inputs.

Families (client routine -> authored function):

* joint_create  CreateJoint 0x0153b02c -> mu_jt_create, every supported kind,
                on a record holding a former joint's bytes (its width and, for
                the kinds that return early, its lifetime and tail count are
                read or kept). The manager hook 0x01095a0a answers 0; rand()
                is a recording stub; AngleMatrix 0x00cff32a, VectorRotate
                0x00d000ad and the vector accessors run as client code.
* joint_move    MoveJoint 0x01556c26 -> mu_jt_move on a random record of each
                kind. CreateSprite, CreateEffect, AddTerrainLight, the area
                request, RequestTerrainHeight, the wall attribute 0x016d348d,
                rand(), the C runtime sin/cos/sqrt (host libm) are stubs; the
                tail shift 0x01553ba6, MoveHumming, the vector class helpers
                (normalise 0x00cfd0cc, scale 0x00cfcd74, the near-zero test
                0x00a72592), the degree conversion 0x00cee2cb, the float
                sin/cos wrappers 0x00968117 / 0x009fa20d and the sign helper
                0x0185ca80 run as client code.
* joint_render  RenderJoints 0x01589b56(mode) over a pool holding the case
                record -> mu_jt_render: the blend wrappers, BindTexture and
                the OpenGL imports are recording stubs; the whole GL stream
                (colour per tail, texture coordinates, corners) is compared.

Every case compares the record fields the C models (bit for bit; any two NaNs
are equal, as in validate_combat.py), the calls in client order with the
values the client passes, and the number of rand() calls. Negative controls
(a planted mistake, emulated in Python on the C result) must disagree.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import validate_combat as vc  # noqa: E402
import validate_skill_fx as sf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
f32, bits, from_bits, same = vc.f32, vc.bits, vc.from_bits, vc.same

CREATE_JOINT_CORE, MOVE_JOINT, RENDER_JOINTS = 0x0153b02c, 0x01556c26, 0x01589b56
WORLD_TIME = 0x06fce370
OBJECTS = sf.OBJECTS
JOINT_POOL, JOINT_BYTES = sf.JOINT_POOL, sf.JOINT_BYTES
BODIES = {
    'create_joint': (0x0153b02c, 0x01553644), 'move_joint': (0x01556c26, 0x01589800),
    'render_joints': (0x01589b56, 0x0158ba40), 'tail_shift': (0x01553ba6, 0x01553d40),
    'move_humming': (0x012af2f1, 0x012af52d), 'normalise': (0x00cfd15f, 0x00cfd203),
    'near_zero': (0x00a72592, 0x00a725c5), 'radians': (0x00cee2cb, 0x00cee2ea), 'sign': (0x0185ca80, 0x0185caa4),
}
KINDS = [(0x7f7d, s) for s in range(0x10, 0x1b)] + [(0x7fd5, 0), (0x7fd8, 1), (0x7fd3, 0)]


# --------------------------------------------------------------------------
# Library.

Joint = sf.Joint      # mu_jt_joint
Object = sf.Object    # mu_jt_object


Call = sf.Call


class MoveInputs(ctypes.Structure):
    _fields_ = [('time_step', ctypes.c_float), ('wall_scene', ctypes.c_int), ('wall', ctypes.c_uint16),
                ('is_hero_target', ctypes.c_int)]


RAND_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
OBJECT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
CALL_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Call))


class Env(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('rand', RAND_FN), ('height', HEIGHT_FN), ('object', OBJECT_FN),
                ('call', CALL_FN), ('serial', ctypes.c_uint8), ('world_time', ctypes.c_float)]


STATE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
BIND_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
COLOR_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float)
BEGIN_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
TEX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
VERTEX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
END_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


class Gl(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('state', STATE_FN), ('bind', BIND_FN), ('color3', COLOR_FN),
                ('begin', BEGIN_FN), ('texcoord', TEX_FN), ('vertex', VERTEX_FN), ('end', END_FN)]


def load_library(path):
    lib = ctypes.CDLL(str(path))
    P = ctypes.POINTER
    F3 = ctypes.c_float*3
    lib.mu_jt_create.argtypes = [P(Joint), ctypes.c_int32, F3, F3, F3, ctypes.c_int32, ctypes.c_int32, ctypes.c_float,
                                 ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_int32,
                                 P(Env)]
    lib.mu_jt_create.restype = ctypes.c_int
    lib.mu_jt_move.argtypes = [P(Joint), P(Env), P(MoveInputs)]
    lib.mu_jt_move.restype = ctypes.c_int
    lib.mu_jt_render.argtypes = [P(Joint), ctypes.c_uint8, ctypes.c_float, P(Gl)]
    lib.mu_jt_render.restype = ctypes.c_int
    lib.mu_jt_kind_supported.argtypes = [ctypes.c_int32, ctypes.c_int32]
    lib.mu_jt_kind_supported.restype = ctypes.c_int
    return lib


JOINT_FIELDS = sf.JOINT_FIELDS
ALL_NAMES = {f[0] for f in JOINT_FIELDS}


def joint_values(j, name, count):
    v = getattr(j, name)
    return list(v) if count > 1 else [v]


def joint_to_bytes(j, names):
    data = bytearray(am.poison(JOINT_BYTES, 0x2f))
    mask = bytearray(JOINT_BYTES)
    for name, offset, fmt, count in JOINT_FIELDS:
        if name not in names:
            continue
        raw = b''.join(struct.pack('<'+fmt, v) for v in joint_values(j, name, count))
        data[offset:offset+len(raw)] = raw
        mask[offset:offset+len(raw)] = b'\1'*len(raw)
    if 'target' in names:
        struct.pack_into('<I', data, 0x54, object_address(j.target))
        mask[0x54:0x58] = b'\1'*4
    return bytes(data), bytes(mask)


def joint_from_bytes(raw, j):
    for name, offset, fmt, count in JOINT_FIELDS:
        size = struct.calcsize('<'+fmt)
        values = [struct.unpack('<'+fmt, bytes(raw[offset+k*size:offset+(k+1)*size]))[0] for k in range(count)]
        if count > 1:
            arr = getattr(j, name)
            for k, v in enumerate(values):
                arr[k] = v
        else:
            setattr(j, name, values[0])
    owner = sf.owner_of(struct.unpack('<I', bytes(raw[0x54:0x58]))[0])
    j.target = owner if isinstance(owner, int) else -9


def compare_joint(j, raw, mask, names):
    for name, offset, fmt, count in JOINT_FIELDS:
        if name not in names:
            continue
        size = struct.calcsize('<'+fmt)
        mine = joint_values(j, name, count)
        for k in range(count):
            o = offset+k*size
            if not all(mask[o:o+size]):
                return (name, k, 'client left undefined', mine[k])
            theirs = struct.unpack('<'+fmt, bytes(raw[o:o+size]))[0]
            if fmt == 'f':
                if not same(theirs, mine[k]):
                    return (name, k, theirs, mine[k])
            elif theirs != mine[k]:
                return (name, k, theirs, mine[k])
    return None


def object_address(index):
    return 0 if index < 0 else OBJECTS + 0x400*index


def random_object(rng):
    o = Object()
    o.live = rng.choice([0, 1, 1, 1, 2])
    o.visible = rng.choice([0, 1, 1, 1])
    o.weapon = rng.choice([0, 9, 0x600])
    for k in range(3):
        o.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 500.0)
        o.light[k] = f32(rng.choice([0.59, 1.0, 0.0, rng.uniform(0.0, 2.0)]))
    return o


def object_region(objects):
    size = 0x400*max(1, len(objects))
    data = bytearray(am.poison(size, 0x29))
    mask = bytearray(size)
    for i, o in enumerate(objects):
        base = 0x400*i
        data[base] = o.live
        data[base+0x0b] = o.visible
        struct.pack_into('<h', data, base+0x56, o.weapon)
        struct.pack_into('<3f', data, base+0x158, *o.position)
        struct.pack_into('<3f', data, base+0xec, *o.light)
        for a, n in ((0, 1), (0x0b, 1), (0x56, 2), (0x158, 12), (0xec, 12)):
            mask[base+a:base+a+n] = b'\1'*n
    return am.Region('objects', OBJECTS, bytes(data), bytes(mask), False)


class Case(sf.Case):
    """validate_skill_fx's stubs; the C side through mu_jt_env."""

    def __init__(self, rng, objects, rand_values, height, world_time):
        super().__init__(rng, [], rand_values, height)
        self.jobjects = objects
        self.c_jobjects = (Object*max(1, len(objects)))(*objects) if objects else (Object*1)()
        self.world_time = world_time

    def stubs(self, m):
        s = super().stubs(m)

        def sprite(mm):
            a = [mm.argument(i) for i in range(8)]
            self.client_calls.append(('sprite', a[0], mm.floats(a[1], 3), from_bits(a[2]), mm.floats(a[3], 3),
                                      sf.owner_of(a[4]), from_bits(a[5]), a[6], a[7]))
            return 0
        s[sf.CREATE_SPRITE] = sprite
        return s

    def jenv(self, serial=0):
        def rand(ctx):
            v = self.rand_values[self.c_rand] if self.c_rand < len(self.rand_values) else 0
            self.c_rand += 1
            return v

        def height(ctx, x, y):
            self.c_calls.append(('height', x, y))
            return self.height_value

        def obj(ctx, index):
            if 0 <= index < len(self.jobjects):
                return ctypes.addressof(self.c_jobjects[index])
            return None

        def call(ctx, cp):
            c = cp.contents
            if c.routine == sf.TERRAIN_LIGHT:
                self.c_calls.append(('light', c.position[0], c.position[1], list(c.light), c.range, sf.FRAME_LIGHT))
            elif c.routine == sf.CREATE_EFFECT_WRAPPER:
                self.c_calls.append(('effect', c.type, list(c.position), list(c.angle), list(c.light), c.subtype,
                                     c.owner, None))
            elif c.routine == sf.CREATE_SPRITE:
                self.c_calls.append(('sprite', c.type, list(c.position), c.scale, list(c.light), c.owner,
                                     c.angle[0], c.subtype, c.range))
            elif c.routine == sf.AREA_ATTACK:
                self.c_calls.append(('area', c.type, c.scale, list(c.position), c.subtype))
        self._jkeep = (RAND_FN(rand), HEIGHT_FN(height), OBJECT_FN(obj), CALL_FN(call))
        env = Env()
        env.rand, env.height, env.object, env.call = self._jkeep
        env.serial = serial
        env.world_time = self.world_time
        return env


def heal_sprite_tail(calls):
    """skill_fx's Heal arrival sprite passes (rotation, ...) without the blend and axes; pad to compare."""
    out = []
    for c in calls:
        if c[0] == 'sprite' and len(c) == 7:
            c = c + (0, 0)
        out.append(c)
    return out


def rand_values(rng, n=600):
    return [rng.choice([0, 1, 2, 3, 5, 89, 90, 359, 360, 0x7fff, rng.randrange(0, 0x8000)]) for _ in range(n)]


def world_time_value(rng):
    return f32(rng.choice([0.0, 999.0, 1000.0, 123456.0, float(rng.randrange(0, 5000000)),
                           rng.uniform(0.0, 5e6)]))


# --------------------------------------------------------------------------
# Families.

def random_create_args(rng, kind):
    pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
    target = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
    angle = [vc.rfloat(rng, 0.1, 360.0) for _ in range(3)]
    if kind[0] == 0x7f7d:
        scale = f32(rng.choice([1.0, 0.8, 1.2, 0.5, 2.0, 0.0, -1.0, rng.uniform(0.05, 3.0)]))
    else:
        scale = f32(rng.choice([5.0, 80.0, 20.0, 10.0, vc.rfloat(rng, 0.2, 100.0)]))
    return pos, target, angle, scale


def family_joint_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        pos, tpos, angle, scale = random_create_args(rng, kind)
        objects = [random_object(rng) for _ in range(2)]
        target = rng.choice([0, 1]) if kind[0] == 0x7f7d else rng.choice([-1, 0, 1])
        key, skill, byte10, word13, arg14 = (rng.randrange(0, 0x10000), rng.choice([0x7f5, 9, 0x123]),
                                              rng.randrange(0, 256), rng.randrange(0, 0x10000),
                                              rng.randrange(-2**31, 2**31))
        serial = rng.randrange(0, 256)
        world_time = world_time_value(rng)
        previous = bytearray(am.poison(JOINT_BYTES, rng.randrange(0, 0x80)))
        previous[0] = 0
        struct.pack_into('<f', previous, 0x14, f32(rng.choice([0.0, 5.0, 80.0, 1.0, vc.rfloat(rng, 0.2, 90.0)])))
        struct.pack_into('<ii', previous, 0x68, rng.randrange(0, 50), rng.randrange(2, 60))
        struct.pack_into('<i', previous, 0xa00, rng.randrange(-5, 60))
        for k in range(600):
            struct.pack_into('<f', previous, 0x70+4*k, f32(rng.uniform(-1000.0, 1000.0)))
        record = am.defined_region('joint', JOINT_POOL, bytes(previous))
        case = Case(rng, objects, rand_values(rng, 40), 0.0, world_time)
        inputs = am.defined_region('inputs', sf.INPUTS, struct.pack('<9f', *pos, *tpos, *angle), writable=False)
        hero = am.Region('hero-data', sf.HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
        hero.define(sf.HERO_DATA+0x2dec, bytes([serial]))
        regions = [record, inputs, object_region(objects), hero,
                   am.defined_region('hero-ptr', sf.HERO_DATA_PTR, struct.pack('<I', sf.HERO_DATA), writable=False),
                   am.defined_region('world-time', WORLD_TIME, struct.pack('<f', world_time), writable=False)]
        stubs = case.stubs(m)
        del stubs[sf.CREATE_JOINT]
        stubs[sf.JOINT_MANAGER_A] = lambda mm: (0, 12)
        r = m.execute(CREATE_JOINT_CORE, [kind[0], sf.INPUTS, sf.INPUTS+12, sf.INPUTS+24, kind[1],
                                          object_address(target), bits(scale), key, skill, byte10, 0xffffffff, 0,
                                          word13, arg14], regions, stubs)
        j = Joint()
        joint_from_bytes(previous, j)
        F3 = ctypes.c_float*3
        env = case.jenv(serial=serial)
        supported = lib.mu_jt_create(ctypes.byref(j), kind[0], F3(*pos), F3(*tpos), F3(*angle), kind[1], target,
                                     scale, key, skill, byte10, word13, arg14, ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['joint']
            mismatch = compare_joint(j, out, record.defined, ALL_NAMES)
            if mismatch is None and struct.unpack('<I', out[0x54:0x58])[0] != object_address(target):
                mismatch = ('target', out[0x54:0x58].hex(), target)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('joint_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                           'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('joint_create', f'{kind[0]:#x}/{kind[1]:#x}' + (' early' if kind[0] == 0x7f7d and not scale > 0
                                                                        else ''))
        if vc.ok(r) and kind[0] == 0x7f7d and kind[1] in (0x16, 0x17) and scale > 0:
            # negative control: the ring's phase modulo the full tail count
            phase = struct.unpack('<i', r['regions']['joint'][0xa20:0xa24])[0]
            t = int(world_time) if math.isfinite(world_time) and abs(world_time) < 2**31 else -2**31
            negatives['create_phase_full_count'] += phase != int(math.fmod(t, 50))


def random_joint(rng, kind):
    j = Joint()
    raw = bytearray(am.poison(JOINT_BYTES, rng.randrange(0, 0x80)))
    joint_from_bytes(raw, j)
    j.live = 1
    j.type = kind[0]
    j.subtype = kind[1]
    j.tex_type = 0x7f7c if kind[0] == 0x7f7d else kind[0]
    j.render_type = {0x7fd8: 1, 0x7fd3: 3}.get(kind[0], 1)
    j.faces = 3
    for k in range(3):
        j.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        j.start[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        j.angle[k] = vc.rfloat(rng, 0.1, 360.0)
        j.light[k] = f32(rng.choice([0.59, 1.0, vc.rfloat(rng, 0.1, 5.0)]))
        j.target_position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        j.jitter[k] = vc.rfloat(rng, 0.1, 20.0)
    if rng.random() < 0.1:
        j.target_position[:] = j.start[:]
    j.target = rng.choice([-1, 0, 1, 1])
    j.field_64 = rng.choice([0, 1, 2])
    if kind[0] == 0x7f7d:
        j.scale = f32(rng.choice([1.0, 0.8, 1.2, 0.5, 2.0, rng.uniform(0.05, 3.0)]))
        j.max_tails = rng.choice([50, 50, 50, rng.randrange(3, 51)])
        j.lifetime = rng.choice([20, 19, 10, 1, 0, rng.randrange(-1, 21)])
        j.velocity = f32(rng.choice([0.0, 0.0, 0.0, 5.0]))
        j.phase = rng.randrange(0, 25)
    elif kind[0] == 0x7fd5:
        j.scale = f32(2.0)
        j.max_tails = 2
        j.lifetime = rng.randrange(-1, 16)
        j.velocity = f32(rng.choice([6.0, 25.0, rng.uniform(6.0, 25.0)]))
    else:
        j.scale = f32(rng.choice([5.0, 80.0, 20.0, 80.0, vc.rfloat(rng, 0.2, 100.0)]))
        j.max_tails = 2 if kind[0] == 0x7fd8 else 6
        j.lifetime = rng.choice([12, 11, 2, 1, 0, 49, 45, 30, 15, rng.randrange(-2, 50)])
        j.velocity = f32(rng.choice([0.0, 4.0, 70.0, vc.rfloat(rng, 0.2, 80.0)]))
    j.num_tails = rng.randrange(0, j.max_tails)
    for k in range(600):
        j.tails[k] = f32(rng.uniform(-3000.0, 3000.0))
    j.reached = rng.choice([0, 1])
    j.field_a24 = j.field_a25 = 0   # as CreateJoint leaves them for these kinds
    j.skill = rng.choice([0x7f5, 9, 0x123])
    j.tail_update = rng.choice([1, 1, 0])
    j.time = vc.rfloat(rng, 0.1, 50.0)
    j.brightness = f32(rng.choice([1.0, 0.5]))
    j.moving = 1   # CreateJoint sets it; these kinds never clear it
    return j


def family_joint_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        objects = [random_object(rng) for _ in range(2)]
        j = random_joint(rng, kind)
        step = vc.rfloat(rng, 0.1, 2.0)
        wall_scene = rng.choice([0, 1])
        wall = rng.choice([0, 0x100, 0x104, 4])
        hero_obj = rng.choice([-1, 0, 1])
        world_time = world_time_value(rng)
        case = Case(rng, objects, rand_values(rng), vc.rfloat(rng, 0.1, 400.0), world_time)
        raw, mask = joint_to_bytes(j, ALL_NAMES | {'target'})
        record = am.Region('joint', JOINT_POOL, raw, mask)
        hero_char = (object_address(hero_obj) - 0x3254) & 0xffffffff if hero_obj >= 0 else 0x5000000
        regions = [record, object_region(objects),
                   am.defined_region('time-step', sf.TIME_STEP, struct.pack('<f', step), writable=False),
                   am.defined_region('wall-scene', sf.WALL_SCENE, bytes([wall_scene]), writable=False),
                   am.defined_region('hero', sf.HERO_POINTER, struct.pack('<I', hero_char), writable=False),
                   am.defined_region('world-time', WORLD_TIME, struct.pack('<f', world_time), writable=False)]
        stubs = case.stubs(m)

        def wall_stub(mm):
            case.client_calls.append(('wall', mm.float_argument(0), mm.float_argument(1)))
            return wall, 0
        stubs[sf.WALL_ATTRIBUTE] = wall_stub
        before = Joint.from_buffer_copy(j)
        r = m.execute(MOVE_JOINT, [JOINT_POOL, 0], regions, stubs)
        env = case.jenv()
        is_hero = 1 if (hero_obj >= 0 and hero_obj == j.target) else 0
        if j.type == 0x7fd3 and j.scale == 80.0 and wall_scene:
            case.c_calls.append(('wall', None, None))
        inputs = MoveInputs(step, wall_scene, wall, is_hero)
        supported = lib.mu_jt_move(ctypes.byref(j), ctypes.byref(env), ctypes.byref(inputs))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['joint']
            mismatch = compare_joint(j, out, record.defined, ALL_NAMES)
            if mismatch is None:
                mismatch = sf.compare_calls(heal_sprite_tail(case.client_calls),
                                            heal_sprite_tail(sf.sorted_calls(case.c_calls, case.client_calls)))
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('joint_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                         'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('joint_move', f'{kind[0]:#x}/{kind[1]:#x}')
        if vc.ok(r) and kind[0] == 0x7f7d and before.max_tails >= 3:
            out = r['regions']['joint']
            # negative control: the ring and bolt widths restored without the closing tail shift (num_tails one less)
            tails = struct.unpack('<i', out[0x68:0x6c])[0]
            negatives['move_no_closing_shift'] += tails != min(before.num_tails + before.max_tails - 1 +
                                                               before.tail_update, before.max_tails - 1) - 1
            # negative control: the start flash without the record's light
            sprites = [c for c in case.client_calls if c[0] == 'sprite']
            if sprites:
                negatives['move_flash_white'] += not all(same(x, 1.0) for x in sprites[0][4])


def family_joint_render(m, lib, rng, cases, report, negatives):
    pool_bytes = 500*JOINT_BYTES
    empty = bytearray(am.poison(pool_bytes, 0x61))
    empty_mask = bytearray(pool_bytes)
    for i in range(500):
        base = i*JOINT_BYTES
        empty[base] = 0
        struct.pack_into('<ii', empty, base+4, 0, 0)
        empty_mask[base:base+0x10] = b'\1'*0x10
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        j = random_joint(rng, kind)
        j.faces = rng.choice([3, 3, 1, 2, 0])
        mode = rng.choice([0, 0, 1, 2])
        raw, mask = joint_to_bytes(j, ALL_NAMES | {'target'})
        pool = bytearray(empty)
        pmask = bytearray(empty_mask)
        pool[0:JOINT_BYTES] = raw
        pmask[0:JOINT_BYTES] = mask
        region = am.Region('joints', JOINT_POOL, bytes(pool), bytes(pmask))
        world_time = world_time_value(rng)
        wt_region = am.defined_region('world-time', WORLD_TIME, struct.pack('<f', world_time), writable=False)
        calls = []

        def rec(name):
            def stub(mm):
                calls.append((name,))
                return 0
            return stub

        def bind(mm):
            calls.append(('bind', mm.argument(0)))
            return 0

        def blend_alpha(mm):
            calls.append(('blend', 2, mm.argument(0)))
            return 0
        stubs = {sf.JOINT_MANAGER_COUNT: lambda mm: (0, 0), sf.BIND_TEXTURE: bind, sf.BLEND_ADD: rec('blend1'),
                 sf.BLEND_ALPHA: blend_alpha, sf.BLEND_SUB: rec('blend3'), sf.BLEND_INV: rec('blend4'),
                 sf.DEPTH_OFF: rec('depth_off')}
        for slot, (name, argc) in sf.GL_IMPORTS.items():
            def gl(mm, name=name, argc=argc):
                a = [mm.argument(i) for i in range(argc)]
                if name in ('glVertex3fv', 'glColor3fv'):
                    calls.append((name, mm.floats(a[0], 3)))
                elif name in ('glColor3f', 'glColor4f', 'glTexCoord2f'):
                    calls.append((name, [from_bits(x) for x in a]))
                else:
                    calls.append((name, a))
                return 0, 4*argc
            stubs[m.gl_target[slot]] = gl
        r = m.execute(RENDER_JOINTS, [0x5500 | mode], [region, wt_region], stubs)
        mine = []
        names = {0x0184aa2b: ('blend1',), 0x0184aab7: ('blend3',), 0x0184ab46: ('blend4',)}

        def c_state(ctx, wrapper, argument):
            mine.append(('blend', 2, argument) if wrapper == 0x0184a990 else names.get(wrapper, ('state', wrapper)))

        def c_bind(ctx, bitmap):
            mine.append(('bind', bitmap))

        def c_color(ctx, r_, g, b):
            mine.append(('glColor3f', [r_, g, b]))

        def c_begin(ctx, mode_):
            mine.append(('glBegin', [mode_]))

        def c_tex(ctx, u, v):
            mine.append(('glTexCoord2f', [u, v]))

        def c_vertex(ctx, p):
            mine.append(('glVertex3fv', [p[0], p[1], p[2]]))

        def c_end(ctx):
            mine.append(('glEnd', []))
        keep = (STATE_FN(c_state), BIND_FN(c_bind), COLOR_FN(c_color), BEGIN_FN(c_begin), TEX_FN(c_tex),
                VERTEX_FN(c_vertex), END_FN(c_end))
        glc = Gl(None, *keep)
        count_q = lib.mu_jt_render(ctypes.byref(j), mode, world_time, ctypes.byref(glc))
        mismatch = None
        if vc.ok(r):
            if len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine)):
                diff = next(((i, a, b) for i, (a, b) in enumerate(zip(calls, mine)) if not vc._same_call(a, b)),
                            ('count', len(calls), len(mine)))
                mismatch = ('calls', diff, calls[:4], mine[:4])
        equal = vc.ok(r) and mismatch is None
        report.add('joint_render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode,
                                           'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                                           'checks': r['checks']})
        report.cover('joint_render', f'{kind[0]:#x}/{kind[1]:#x} quads {min(count_q, 9)}')
        if vc.ok(r) and count_q and kind[0] == 0x7f7d:
            colours = [c for c in calls if c[0] == 'glColor3f']
            if len(colours) > 1:
                f = f32(j.lifetime * f32(0.08)) if kind[1] in (0x14, 0x15, 0x16, 0x17) else f32(j.lifetime * f32(0.1))
                # negative control: the ring's and the bolt's tail factors exchanged
                negatives['render_factor_swapped'] += not same(colours[1][1][0], f32(j.light[0]*f))


FAMILIES = [('joint_create', family_joint_create), ('joint_move', family_joint_move),
            ('joint_render', family_joint_render)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
    parser.add_argument('--data', default=str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/joints/libclient_joints.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--only', action='append')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = sf.FxMachine(text, data)
    bodies = {name: {'start': hex(a), 'end': hex(b),
                     'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    report = vc.Report()
    negatives = {k: 0 for k in ['create_phase_full_count', 'move_no_closing_shift', 'move_flash_white',
                                'render_factor_swapped']}
    timing = {}
    for name, family in FAMILIES:
        if args.only and name not in args.only:
            continue
        rng = random.Random(f'{args.seed}-{name}')
        start = time.time()
        family(m, lib, rng, args.cases, report, negatives)
        timing[name] = round(time.time()-start, 2)
    all_equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result = {'coverage': report.coverage, 'nan_pairs_equal': vc.NAN_COUNT[0], 'text_sha256': am.TEXT_SHA256,
              'data_sha256': am.DATA_SHA256, 'bodies': bodies, 'families': report.families,
              'negative_controls': negatives, 'seconds': timing, 'all_equal': all_equal}
    summary = {k: f"{v['equal']}/{v['cases']}" for k, v in report.families.items()}
    print(json.dumps({'summary': summary, 'negative_controls': negatives, 'seconds': timing,
                      'all_equal': all_equal}, indent=1))
    for k, v in report.families.items():
        if v['first_failures']:
            print(k, json.dumps(v['first_failures'][:3], default=str))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, default=str))
    return 0 if all_equal else 1


if __name__ == '__main__':
    sys.exit(main())
