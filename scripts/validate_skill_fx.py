#!/usr/bin/env python3
"""Compare reconstructed/combat/skill_fx.c with the client's instructions (NATIVE-COMBAT-002).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case),
with the x87 helpers of scripts/validate_combat.py. The authored C (libcombat)
runs on the same inputs.

Families (client routine -> authored function):

* effect_create  CreateEffect 0x013c0f19 -> mu_sfx_effect_create. The object
                 initialiser 0x0129eb81 is a stub that defines the record as
                 zero; the effect-manager hooks 0x01094ff1 / 0x01095279 answer
                 0; rand(), RequestTerrainHeight, the trigonometric wrappers
                 (host libm) and nested CreateEffect are recording stubs; the
                 live setter, the vector accessors, AngleMatrix 0x00cff32a and
                 VectorRotate 0x00d000ad run as client code.
* effect_move    MoveEffect 0x0142fd09 -> mu_sfx_effect_move. AddTerrainLight,
                 CreateParticle, CreateJoint, CreateEffect, the model getters
                 (a synthetic model with an action table), PlayAnimation, the
                 two hit checks and DeleteEffect (modelled as clearing the live
                 byte) are recording stubs; the generic motion 0x0150df8e runs
                 as client code.
* check_magic    the spell hit check 0x013be199 -> mu_sfx_check_magic (CRT
                 sqrt is a stub returning the host double square root).

Every case compares the record fields the C models (bit for bit; any two NaNs
are equal, as in validate_combat.py), the calls in client order with the
values the client passes, and the number of rand() calls. Negative controls
(the C with one planted mistake, emulated in Python) must disagree on some
cases.
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

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

CREATE_EFFECT, MOVE_EFFECT, CHECK_MAGIC, CHECK_ARROW = 0x013c0f19, 0x0142fd09, 0x013be199, 0x013bd374
CREATE_EFFECT_WRAPPER, CREATE_PARTICLE, CREATE_JOINT = 0x013c0eaa, 0x0168fafd, 0x0153b02c
TERRAIN_LIGHT, TERRAIN_HEIGHT, RAND = 0x016cacfc, 0x016cc9e2, 0x01989721
SINE, COSINE, CRT_SQRT = 0x009681bd, 0x009fa223, 0x019856f0
OBJECT_INIT, MANAGER_A, MANAGER_B = 0x0129eb81, 0x01094ff1, 0x01095279
MODEL_CONTAINER, MODEL_GETTER, PLAY_ANIMATION, DELETE_EFFECT = 0x00966cc4, 0x00eaa8cf, 0x012b4dd3, 0x0142eea4
POOL = 0x0a4ca430
HERO_DATA_PTR = 0x01d1df18
FRAME_LIGHT = 0x0b9f5430
BODIES = {
    'create_effect': (0x013c0f19, 0x0142b5d8), 'move_effect': (0x0142fd09, 0x0150cc95),
    'effect_advance': (0x0150df8e, 0x0150e1b9), 'check_magic': (0x013be199, 0x013bec7c),
    'heal_joints': (0x0142d83b, 0x0142da3e), 'angle_matrix': (0x00cff32a, 0x00cff4a0),
    'vector_rotate': (0x00d000ad, 0x00d001a0),
}
INPUTS = 0x21000000       # case argument vectors
OBJECTS = 0x22000000      # owner / target objects, 0x400 apart
MODEL = 0x23000000        # synthetic model (getter result) and its action table
HERO_DATA = 0x24000000    # [0x01d1df18] points here (+0x2dec skill serial)
CONTAINER = 0x25000000    # model container (only passed as `this`)
LIGHT_SCRATCH = 0x26000000

f32, bits, from_bits, same = vc.f32, vc.bits, vc.from_bits, vc.same


# --------------------------------------------------------------------------
# Library.

class Effect(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('flag5', ctypes.c_uint8), ('visible', ctypes.c_uint8),
                ('flag_c', ctypes.c_uint8), ('action', ctypes.c_uint16), ('prior_action', ctypes.c_uint16),
                ('client_hit', ctypes.c_uint8), ('skill', ctypes.c_uint16), ('info6', ctypes.c_uint8),
                ('key', ctypes.c_uint16), ('serial', ctypes.c_uint16), ('type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('field_68', ctypes.c_int32), ('lifetime', ctypes.c_int32),
                ('blend_mesh', ctypes.c_int32), ('field_78', ctypes.c_int32), ('field_80', ctypes.c_int32),
                ('scale', ctypes.c_float), ('scale_arg', ctypes.c_float), ('blend_light', ctypes.c_float),
                ('blend_u', ctypes.c_float), ('blend_v', ctypes.c_float), ('velocity', ctypes.c_float),
                ('gravity', ctypes.c_float), ('frame', ctypes.c_float), ('prior_frame', ctypes.c_float),
                ('alpha', ctypes.c_float), ('light', ctypes.c_float*3), ('direction', ctypes.c_float*3),
                ('position', ctypes.c_float*3), ('angle', ctypes.c_float*3), ('start', ctypes.c_float*3),
                ('owner', ctypes.c_int32), ('field_364', ctypes.c_uint16), ('field_58', ctypes.c_int32),
                ('field_2e4', ctypes.c_int32)]


class Info(ctypes.Structure):
    _fields_ = [('key', ctypes.c_uint16), ('skill', ctypes.c_uint16), ('word4', ctypes.c_uint16),
                ('word6', ctypes.c_uint16), ('field8', ctypes.c_uint16), ('field18', ctypes.c_int32),
                ('field1c', ctypes.c_int32)]


class Object(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('position', ctypes.c_float*3)]


class Call(ctypes.Structure):
    _fields_ = [('routine', ctypes.c_int32), ('type', ctypes.c_int32), ('subtype', ctypes.c_int32),
                ('owner', ctypes.c_int32), ('range', ctypes.c_int32), ('scale', ctypes.c_float),
                ('position', ctypes.c_float*3), ('target', ctypes.c_float*3), ('angle', ctypes.c_float*3),
                ('light', ctypes.c_float*3)]


RAND_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
OBJECT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
CALL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(Call), ctypes.POINTER(Effect))
MODEL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint16,
                            ctypes.POINTER(ctypes.c_int16))


class Env(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('rand', RAND_FN), ('height', HEIGHT_FN), ('object', OBJECT_FN),
                ('call', CALL_FN), ('model', MODEL_FN), ('serial', ctypes.c_uint8),
                ('report_checks', ctypes.c_uint8)]


def load_library(path):
    lib = ctypes.CDLL(str(path))
    P = ctypes.POINTER
    F3 = ctypes.c_float*3
    lib.mu_sfx_effect_create.argtypes = [P(Effect), ctypes.c_int32, ctypes.c_int32, F3, F3, F3, ctypes.c_int32,
                                         ctypes.c_float, P(Info), P(Env)]
    lib.mu_sfx_effect_create.restype = ctypes.c_int
    lib.mu_sfx_effect_move.argtypes = [P(Effect), P(Env)]
    lib.mu_sfx_effect_move.restype = ctypes.c_int
    lib.mu_sfx_check_magic.argtypes = [P(Effect), P(Env)]
    lib.mu_sfx_check_magic.restype = None
    return lib


# Record fields: (C name, client offset, struct format, component count).
EFFECT_FIELDS = [
    ('live', 0x00, 'B', 1), ('flag5', 0x05, 'B', 1), ('flag_c', 0x0c, 'B', 1),
    ('action', 0x2a, 'H', 1), ('prior_action', 0x2c, 'H', 1), ('client_hit', 0x3b, 'B', 1), ('skill', 0x3c, 'H', 1),
    ('info6', 0x45, 'B', 1), ('key', 0x54, 'H', 1), ('serial', 0x56, 'H', 1), ('type', 0x5c, 'i', 1),
    ('subtype', 0x60, 'i', 1), ('field_68', 0x68, 'i', 1), ('lifetime', 0x6c, 'i', 1), ('blend_mesh', 0x74, 'i', 1),
    ('field_78', 0x78, 'i', 1), ('field_80', 0x80, 'i', 1), ('scale', 0xa0, 'f', 1), ('scale_arg', 0xa4, 'f', 1),
    ('blend_light', 0xa8, 'f', 1), ('blend_u', 0xac, 'f', 1), ('blend_v', 0xb0, 'f', 1), ('velocity', 0xbc, 'f', 1),
    ('gravity', 0xc8, 'f', 1), ('frame', 0xd0, 'f', 1), ('prior_frame', 0xd4, 'f', 1), ('alpha', 0xdc, 'f', 1),
    ('light', 0xec, 'f', 3), ('direction', 0xf8, 'f', 3), ('position', 0x158, 'f', 3), ('angle', 0x164, 'f', 3),
    ('start', 0x1d0, 'f', 3), ('field_364', 0x364, 'H', 1), ('field_58', 0x58, 'i', 1), ('field_2e4', 0x2e4, 'i', 1),
]
# visible (+0x0b) is an input of the hit checks only; owner (+0x34c) is a pointer handled separately.


def object_address(index):
    return 0 if index < 0 else OBJECTS + 0x400*index


def effect_to_bytes(e, defined_names):
    """Client bytes of a record from the C struct; fields in defined_names are defined."""
    data = bytearray(am.poison(0x3d8, 0x47))
    mask = bytearray(0x3d8)
    for name, offset, fmt, count in EFFECT_FIELDS + [('visible', 0x0b, 'B', 1)]:
        if name not in defined_names:
            continue
        value = getattr(e, name)
        values = list(value) if count > 1 else [value]
        raw = b''.join(struct.pack('<'+fmt, v) for v in values)
        data[offset:offset+len(raw)] = raw
        mask[offset:offset+len(raw)] = b'\1'*len(raw)
    if 'owner' in defined_names:
        struct.pack_into('<I', data, 0x34c, object_address(e.owner))
        mask[0x34c:0x350] = b'\1'*4
    return bytes(data), bytes(mask)


def compare_effect(e, raw, mask, names=None):
    """Every modelled field the client defined must equal C (and C must not
    have changed a field the client left undefined: those keep the case input)."""
    for name, offset, fmt, count in EFFECT_FIELDS:
        if names is not None and name not in names:
            continue
        size = struct.calcsize('<'+fmt)
        mine = getattr(e, name)
        mine = list(mine) if count > 1 else [mine]
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


def owner_of(address):
    if address == 0:
        return -1
    if OBJECTS <= address < OBJECTS + 0x400*64 and (address-OBJECTS) % 0x400 == 0:
        return (address-OBJECTS)//0x400
    if POOL <= address < POOL + 0x3d8*200:
        return -2
    return ('pointer', hex(address))


def random_object(rng):
    o = Object()
    o.live = rng.choice([0, 1, 1, 1, 2])
    o.visible = rng.choice([0, 1, 1, 1])
    for k in range(3):
        o.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 500.0)
    return o


def object_region(objects, writable=False):
    size = 0x400*max(1, len(objects))
    data = bytearray(am.poison(size, 0x29))
    mask = bytearray(size)
    for i, o in enumerate(objects):
        base = 0x400*i
        data[base] = o.live
        data[base+0x0b] = o.visible
        struct.pack_into('<3f', data, base+0x158, *o.position)
        for a, n in ((0, 1), (0x0b, 1), (0x158, 12)):
            mask[base+a:base+a+n] = b'\1'*n
    return am.Region('objects', OBJECTS, bytes(data), bytes(mask), writable)


class Case:
    """Shared stubs and C callbacks for one case."""

    def __init__(self, rng, objects, rand_values, height, animation=1, keys=1, has_model=True):
        self.objects = objects
        self.rand_values = list(rand_values)
        self.height_value = height
        self.client_calls, self.c_calls = [], []
        self.client_rand = self.c_rand = 0
        self.animation, self.keys, self.has_model = animation, keys, has_model
        self.c_objects = (Object*max(1, len(objects)))(*objects) if objects else (Object*1)()

    # ---- client side
    def stubs(self, m):
        def rand(mm):
            v = self.rand_values[self.client_rand] if self.client_rand < len(self.rand_values) else 0
            self.client_rand += 1
            return v

        def height(mm):
            self.client_calls.append(('height', mm.float_argument(0), mm.float_argument(1)))
            return mm.x87_return(self.height_value)

        def sine(mm):
            return mm.x87_return(f32(math.sin(mm.float_argument(0))))

        def cosine(mm):
            return mm.x87_return(f32(math.cos(mm.float_argument(0))))

        def sqrt(mm):
            lo, hi = mm.argument(0), mm.argument(1)
            v = struct.unpack('<d', struct.pack('<II', lo, hi))[0]
            return mm.x87_return(math.sqrt(v) if v >= 0 else float('nan'), double=True)

        def terrain_light(mm):
            light = mm.floats(mm.argument(2), 3)
            self.client_calls.append(('light', mm.float_argument(0), mm.float_argument(1), light,
                                      mm.argument(3), mm.argument(4)))
            return 0

        def particle(mm):
            a = [mm.argument(i) for i in range(8)]
            self.client_calls.append(('particle', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      a[4], from_bits(a[5]), owner_of(a[6]), a[7]))
            return 0

        def joint(mm):
            a = [mm.argument(i) for i in range(14)]
            self.client_calls.append(('joint', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      a[4], owner_of(a[5]), from_bits(a[6]), a[7:14]))
            return 0

        def effect(mm):
            a = [mm.argument(i) for i in range(14)]
            self.client_calls.append(('effect', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      a[4], owner_of(a[5]), a[6:14]))
            return 0

        def init(mm):
            o = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
            self.client_calls.append(('init', hex(o)))
            mm.write(o, b'\0'*0x3d8)
            return 0

        def zero8(mm):
            return 0, 8

        def container(mm):
            return CONTAINER, 0

        def getter(mm):
            return (MODEL if self.has_model else 0), 4

        def play(mm):
            a = [mm.argument(i) for i in range(6)]
            self.client_calls.append(('animation', [hex(x) for x in a[:3]], from_bits(a[3]), hex(a[4]), hex(a[5])))
            return self.animation, 0x18

        def check(name):
            def stub(mm):
                self.client_calls.append(('check', name, hex(mm.argument(0))))
                return 0
            return stub

        def delete(mm):
            o = mm.argument(0)
            self.client_calls.append(('delete', hex(o)))
            mm.write(o, b'\0')
            return 0

        return {RAND: rand, TERRAIN_HEIGHT: height, SINE: sine, COSINE: cosine, CRT_SQRT: sqrt,
                TERRAIN_LIGHT: terrain_light, CREATE_PARTICLE: particle, CREATE_JOINT: joint,
                CREATE_EFFECT_WRAPPER: effect, OBJECT_INIT: init, MANAGER_A: zero8, MANAGER_B: zero8,
                MODEL_CONTAINER: container, MODEL_GETTER: getter, PLAY_ANIMATION: play,
                CHECK_ARROW: check('arrow'), CHECK_MAGIC: check('magic'), DELETE_EFFECT: delete}

    # ---- C side
    def env(self, serial=0, report_checks=1):
        def rand(ctx):
            v = self.rand_values[self.c_rand] if self.c_rand < len(self.rand_values) else 0
            self.c_rand += 1
            return v

        def height(ctx, x, y):
            self.c_calls.append(('height', x, y))
            return self.height_value

        def obj(ctx, index):
            if 0 <= index < len(self.objects):
                return ctypes.addressof(self.c_objects[index])
            return None

        def call(ctx, cp, ep):
            c = cp.contents
            if c.routine == TERRAIN_LIGHT:
                self.c_calls.append(('light', c.position[0], c.position[1], list(c.light), c.range, FRAME_LIGHT))
            elif c.routine == CREATE_PARTICLE:
                self.c_calls.append(('particle', c.type, list(c.position), list(c.angle), list(c.light), c.subtype,
                                     c.scale, c.owner, 0))
            elif c.routine == CREATE_JOINT:
                self.c_calls.append(('joint', c.type, list(c.position), list(c.target), list(c.angle), c.subtype,
                                     c.owner, c.scale, None))
            elif c.routine == CREATE_EFFECT_WRAPPER:
                self.c_calls.append(('effect', c.type, list(c.position), list(c.angle), list(c.light), c.subtype,
                                     c.owner, None))
            elif c.routine == PLAY_ANIMATION:
                self.c_calls.append(('animation', None, c.scale, None, None))
                return self.animation
            elif c.routine in (CHECK_ARROW, CHECK_MAGIC):
                self.c_calls.append(('check', 'arrow' if c.routine == CHECK_ARROW else 'magic', None))
            elif c.routine == DELETE_EFFECT:
                self.c_calls.append(('delete', None))
            return 0

        def model(ctx, t, action, keys):
            keys[0] = self.keys
            return 1 if self.has_model else 0
        self._keep = (RAND_FN(rand), HEIGHT_FN(height), OBJECT_FN(obj), CALL_FN(call), MODEL_FN(model))
        env = Env()
        env.rand, env.height, env.object, env.call, env.model = self._keep
        env.serial = serial
        env.report_checks = report_checks
        return env


def compare_calls(client, mine, skip_tail=True):
    """Calls in order. Tail fields the C does not model (raw pointer arguments,
    constant trailing arguments) are None on the C side and skipped."""
    client = [c for c in client if c[0] != 'init']
    if len(client) != len(mine):
        return ('count', len(client), len(mine), client[:6], mine[:6])
    for a, b in zip(client, mine):
        if a[0] != b[0]:
            return ('kind', a, b)
        for x, y in zip(a[1:], b[1:]):
            if y is None:
                continue
            if not vc._same_call([x], [y]):
                return ('value', a, b)
    return None


# --------------------------------------------------------------------------
# Families.

EFFECT_KINDS = [(0x43b, 0), (0x43b, 2), (0x413, 1), (0x7f2b, 0), (0x7f84, 1)]
ARROW_SKILLS = [0, 0, 0, 0x7e7, 0x2d7, 0x7fe, 0x18, 0x34]


def rand_values(rng, n=40):
    return [rng.choice([0, 1, 2, 3, 5, 89, 90, 359, 360, 0x7fff, rng.randrange(0, 0x8000)]) for _ in range(n)]


def random_info(rng, kind):
    info = Info()
    info.key = rng.randrange(0, 0x10000)
    info.skill = rng.choice([0, 0x18, 0x34, 4, 17, 26])
    info.word4 = rng.choice(ARROW_SKILLS + [1, 2, 0x101])
    info.word6 = rng.randrange(0, 0x10000)
    info.field8 = rng.randrange(0, 0x10000)
    info.field18 = rng.randrange(-2**31, 2**31)
    info.field1c = rng.randrange(-2**31, 2**31)
    return info


def info_bytes(info):
    raw = bytearray(0x20)
    struct.pack_into('<HHHHH', raw, 0, info.key, info.skill, info.word4, info.word6, info.field8)
    struct.pack_into('<iiiii', raw, 0x0c, 0, 0, 0, info.field18, info.field1c)
    return bytes(raw)


def family_effect_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = EFFECT_KINDS[n % len(EFFECT_KINDS)]
        objects = [random_object(rng) for _ in range(2)]
        owner = rng.choice([-1, 0, 1])
        pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
        angle = [vc.rfloat(rng, 0.1, 360.0) if k == 2 or rng.random() < 0.3 else 0.0 for k in range(3)]
        light = [vc.rfloat(rng, 0.1, 1.5) for _ in range(3)]
        scale = rng.choice([0.0, -1.0, 1.0, 0.5, 2.0, float('nan'), vc.rfloat(rng, 0.2, 3.0)])
        scale = f32(scale)
        info = random_info(rng, kind)
        serial = rng.randrange(0, 256)
        case = Case(rng, objects, rand_values(rng), vc.rfloat(rng, 0.1, 400.0))
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<9f', *pos, *angle, *light) + info_bytes(info),
                                   writable=False)
        record = am.Region('record', POOL, am.poison(0x3d8, 0x31), bytes(0x3d8))
        record.define(POOL, b'\0')        # slot 0 is free
        hero = am.Region('hero-data', HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
        hero.define(HERO_DATA+0x2dec, bytes([serial]))
        regions = [inputs, record, object_region(objects), hero,
                   am.defined_region('hero-ptr', HERO_DATA_PTR, struct.pack('<I', HERO_DATA), writable=False)]
        r = m.execute(CREATE_EFFECT, [kind[0], kind[1], INPUTS, INPUTS+12, INPUTS+24, object_address(owner),
                                      bits(scale), INPUTS+36], regions, case.stubs(m), ecx=POOL, cleanup=0x20)
        e = Effect()
        F3 = ctypes.c_float*3
        env = case.env(serial=serial)
        supported = lib.mu_sfx_effect_create(ctypes.byref(e), kind[0], kind[1], F3(*pos), F3(*angle), F3(*light),
                                              owner, scale, ctypes.byref(info), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            raw = r['regions']['record']
            mismatch = compare_effect(e, raw, record.defined)
            if mismatch is None:
                theirs = struct.unpack('<I', raw[0x34c:0x350])[0]
                if theirs != object_address(owner):
                    mismatch = ('owner', hex(theirs), owner)
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('effect_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                            'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('effect_create', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r):
            raw = r['regions']['record']
            # negative control: the arrow flies 60 units per step (COMBAT-001's viewer choice)
            if kind[0] == 0x43b:
                d = struct.unpack('<f', raw[0xfc:0x100])[0]
                negatives['create_arrow_speed_60'] += not same(d, -60.0)
            # negative control: Energy Ball without the +100 lift
            if kind[0] == 0x7f2b:
                z = struct.unpack('<f', raw[0x160:0x164])[0]
                negatives['create_energy_no_lift'] += not same(z, pos[2])


def random_effect(rng, kind):
    e = Effect()
    e.live = 1
    e.type, e.subtype = kind
    e.flag5 = 1
    e.action = rng.choice([0, 0, 1, 0xff, 3])
    e.prior_action = rng.randrange(0, 0x10000)
    e.client_hit = rng.choice([0, 1])
    # arrows of skills 0x7e7 / 0x7fc / 0x7fd (ground test) and 0x2d8 (arc) are not reconstructed
    e.skill = rng.choice([0, 0, 0x18, 0x34, 0x2d7]) if kind[0] == 0x43b else rng.choice([0, 4, 17, 26])
    e.lifetime = rng.choice([30, 29, 6, 5, 4, 1, 0, -1, 60, 20, 2, rng.randrange(-5, 70)])
    e.blend_mesh = rng.choice([-1, 1])
    e.scale = vc.rfloat(rng, 0.1, 2.0)
    e.blend_light = vc.rfloat(rng, 0.2, 1.0)
    e.velocity = vc.rfloat(rng, 0.1, 1.0)
    e.frame = vc.rfloat(rng, 0.1, 10.0)
    e.prior_frame = vc.rfloat(rng, 0.1, 10.0)
    e.alpha = 1.0
    for k in range(3):
        e.light[k] = vc.rfloat(rng, 0.1, 1.0)
        e.direction[k] = rng.choice([0.0, -50.0, -60.0, -70.0, vc.rfloat(rng, 0.1, 100.0)])
        e.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        e.angle[k] = vc.rfloat(rng, 0.1, 360.0) if k == 2 or rng.random() < 0.3 else 0.0
        e.start[k] = vc.rfloat(rng, 0.1, 30000.0)
    e.owner = rng.choice([-1, 0, 1])
    return e


MOVE_DEFINED = {'live', 'flag5', 'action', 'prior_action', 'client_hit', 'skill', 'type', 'subtype', 'lifetime',
                'blend_mesh', 'scale', 'blend_light', 'velocity', 'frame', 'prior_frame', 'alpha', 'light',
                'direction', 'position', 'angle', 'start', 'owner'}


def family_effect_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = EFFECT_KINDS[n % len(EFFECT_KINDS)]
        e = random_effect(rng, kind)
        objects = [random_object(rng) for _ in range(2)]
        animation = rng.choice([0, 1, 1])
        keys = rng.choice([1, 7, 10, 30, -3])
        has_model = rng.random() < 0.9
        case = Case(rng, objects, rand_values(rng), vc.rfloat(rng, 0.1, 400.0), animation, keys, has_model)
        raw, mask = effect_to_bytes(e, MOVE_DEFINED)
        record = am.Region('record', POOL, raw, mask)
        model = am.Region('model', MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(MODEL+0x30, struct.pack('<I', MODEL+0x1000))
        for a in range(0x100):
            model.define(MODEL+0x1000+16*a+8, struct.pack('<h', keys))
        regions = [record, object_region(objects), model]
        before = Effect.from_buffer_copy(e)
        r = m.execute(MOVE_EFFECT, [POOL, 0], regions, case.stubs(m))
        env = case.env()
        supported = lib.mu_sfx_effect_move(ctypes.byref(e), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = compare_effect(e, out, record.defined, MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('effect_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                          'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('effect_move', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r):
            out = r['regions']['record']
            # negative control: the lifetime check after the decrement for every type
            lt = struct.unpack('<i', out[0x6c:0x70])[0]
            if kind[0] != 0x413 and has_model:
                wrong_live = 0 if before.lifetime - 1 <= 0 else 1
                negatives['move_decrement_first'] += (out[0] != 0) != bool(wrong_live)
            # negative control: straight motion without the angle rotation
            if has_model or kind[0] >= 0x7a4:
                px = struct.unpack('<f', out[0x158:0x15c])[0]
                negatives['move_unrotated'] += not same(px, f32(before.position[0] + before.direction[0]))
            del lt


def family_check_magic(m, lib, rng, cases, report, negatives):
    kinds = [(0x413, 1), (0x7f2b, 0), (0x413, 1), (0x7f2b, 0), (0x43b, 0)]
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = random_effect(rng, kind)
        objects = [random_object(rng) for _ in range(2)]
        e.owner = rng.choice([-1, 0, 1, 1])
        if e.owner >= 0 and rng.random() < 0.6:
            t = objects[e.owner]
            for k in range(2):
                e.position[k] = f32(t.position[k] + rng.choice([0.0, 50.0, -70.0, 99.0, 100.0, 101.0, -150.0]))
        case = Case(rng, objects, rand_values(rng), 0.0)
        raw, mask = effect_to_bytes(e, MOVE_DEFINED)
        record = am.Region('record', POOL, raw, mask)
        regions = [record, object_region(objects)]
        stubs = case.stubs(m)
        del stubs[CHECK_MAGIC]
        r = m.execute(CHECK_MAGIC, [POOL], regions, stubs)
        env = case.env(report_checks=0)
        before_lifetime = e.lifetime
        lib.mu_sfx_check_magic(ctypes.byref(e), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = compare_effect(e, out, record.defined, MOVE_DEFINED)
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = vc.ok(r) and mismatch is None
        hit = vc.ok(r) and struct.unpack('<i', r['regions']['record'][0x6c:0x70])[0] == 1 and before_lifetime != 1
        report.add('check_magic', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                          'stopped': r['stopped'], 'error': r['error']})
        report.cover('check_magic', 'hit' if hit else 'miss')
        if vc.ok(r) and e.owner >= 0:
            # negative control: a 3D distance test
            t = objects[e.owner]
            if t.live and t.visible:
                d3 = math.sqrt(sum((f32(e.position[k]) - t.position[k])**2 for k in range(3)))
                negatives['check_magic_3d'] += (d3 <= 100.0) != hit


FAMILIES = [('effect_create', family_effect_create), ('effect_move', family_effect_move),
            ('check_magic', family_check_magic)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
    parser.add_argument('--data', default=str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--only', action='append')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = vc.Combat(text, data)
    bodies = {name: {'start': hex(a), 'end': hex(b),
                     'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    report = vc.Report()
    negatives = {k: 0 for k in ['create_arrow_speed_60', 'create_energy_no_lift', 'move_decrement_first',
                                'move_unrotated', 'check_magic_3d']}
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
    print(json.dumps({'summary': summary, 'negative_controls': negatives, 'coverage': report.coverage,
                      'seconds': timing, 'all_equal': all_equal}, indent=1))
    for k, v in report.families.items():
        if v['first_failures']:
            print(k, json.dumps(v['first_failures'][:3], default=str))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, default=str))
    return 0 if all_equal else 1


if __name__ == '__main__':
    sys.exit(main())
