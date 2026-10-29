#!/usr/bin/env python3
"""World-142, 143 and 144 primary slots against pinned instructions.

Twisted Karutan create/move/visual (predicate 0x00e6bd5a), Kardamahal
create/move/visual (predicate 0x00e136f3) and Swamp of Destruction
create/move/visual (predicate 0x00e4bb8d). Full AL, all OBJECT bytes, ordered
output calls with their constant arguments asserted and the final MSVC RNG are
compared. rand, AddTerrainLight, PlayBuffer, CreateSprite, CreateParticle,
CreateJoint, CreateEffect, the model lookup, Animation, TransformPosition, the
named-bone lookup 0x0129f18a, the std::string constructor 0x0094997e and the
EH vector destructor 0x0191b937 are recording boundaries; the predicates, the
CRT sine wrapper, fabs, the vector helpers, the sprite descriptor and the SEH
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
import pins
from unicorn.x86_const import UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'twisted_create': (0xe67546, 0xe6766a), 'twisted_move': (0xe6766a, 0xe677a9),
          'twisted_visual': (0xe6841f, 0xe68c6a), 'kardamahal_create': (0xe0ea04, 0xe0ed1c),
          'kardamahal_move': (0xe0ed1c, 0xe0f4bc), 'kardamahal_visual': (0xe117e8, 0xe118fd),
          'swamp_create': (0xe46625, 0xe4696f), 'swamp_move': (0xe4696f, 0xe46a9f),
          'swamp_visual': (0xe47bc2, 0xe48f1c)}
WORLD = {'twisted': 142, 'kardamahal': 143, 'swamp': 144}
EXTREMES = [-2147483648, -1, 2147483647, 1000, 0x7dc]
TYPES = {'twisted': list(range(-1, 201)) + EXTREMES, 'kardamahal': list(range(-1, 176)) + EXTREMES,
         'swamp': list(range(-1, 203)) + EXTREMES}
DIRECTED = {'twisted_move': [160], 'twisted_visual': [72, 113, 114, 115, 116, 118, 196],
            'kardamahal_move': [113, 115, 126, 127, 128, 129, 130, 133, 146, 149, 150, 151, 152, 167, 169],
            'kardamahal_visual': [161], 'swamp_move': [183],
            'swamp_visual': list(range(160, 170)) + [185] + list(range(187, 194))}
# first-rand residue that opens each visual branch: (modulus, value)
OPEN = {('twisted', 113): (3, None), ('twisted', 114): (3, 0), ('twisted', 116): (8, 0), ('twisted', 196): (50, 1),
        ('kardamahal', 161): (80, 1), ('swamp', 185): (200, 0)}
OPEN.update({('swamp', t): (50, 0) for t in list(range(160, 170)) + list(range(187, 194))})
NULL = 0
COOKIE = 0x01cf65c0   # CRT security cookie (the sine wrapper's error path for huge arguments)
BONES = 0x6fce398
BONE = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))
SPRITE_DESCRIPTOR = (1, 1, v.bits(1.0))
JOINT_TAIL = [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]
LIGHT, SOUND, PARTICLE, SPRITE, JOINT = 0x16cacfc, 0xa6ac96, 0x168fafd, 0x1692eb7, 0x153b02c
EFFECT, BONE_LIGHTS, ANIMATION = 0xe68c23, 0xe0f0d9, 0x12b5064
STRING_CTOR, STRING_ARRAY_DTOR, STRING_DTOR, NAMED_BONE = 0x94997e, 0x191b937, 0x8e83a0, 0x129f18a
NAME_TABLE = 0x1aa989c   # "E002".."E009", 8 bytes apart


def bind(lib):
    d = lib.dll
    P = C.c_void_p
    d.mu_twisted_karutan_create.argtypes = [P, C.c_int32]
    d.mu_twisted_karutan_move.argtypes = [P, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_twisted_karutan_visual.argtypes = [P, C.c_int32, C.c_int, C.c_float, v.RAND_FN, BONE, P, C.POINTER(v.Log)]
    d.mu_kardamahal_create.argtypes = [P, C.c_int32]
    d.mu_kardamahal_move.argtypes = d.mu_twisted_karutan_move.argtypes
    d.mu_kardamahal_visual.argtypes = [P, C.c_int32, C.c_int, v.RAND_FN, P, C.POINTER(v.Log)]
    d.mu_kardamahal_bone_name.argtypes = [C.c_int32]
    d.mu_kardamahal_bone_name.restype = C.c_char_p
    d.mu_swamp_create.argtypes = [P, C.c_int32]
    d.mu_swamp_move.argtypes = d.mu_twisted_karutan_move.argtypes
    d.mu_swamp_visual.argtypes = d.mu_kardamahal_visual.argtypes
    return lib


def time_sample(g):
    return v.f32(g.choice([0.0, -0.0, 1000.0, -3000.0, 3926.9908, 7853.9816, 12345.0, 2147483520.0, 3e9, -1e12,
                           math.nan, g.uniform(-1e6, 1e6), g.uniform(0, 1e7), g.uniform(0, 1e5)]))


def bone_position(k):
    return (float(k * 17 + 5), float(k * -13 + 7), float(k * 11 - 3))


def seed_for(g, modulus, value):
    """A seed whose first MSVC rand has the residue (any other residue when value is None: spread)."""
    want = g.randrange(modulus) if value is None else value
    while True:
        seed = g.getrandbits(32)
        if v.MsvcRand(seed)() % modulus == want:
            return seed


def family(machine, lib, name, cases):
    g = random.Random('worlds-r2-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    cls = WORLD[prefix]
    types = TYPES[prefix]
    for n in range(cases):
        typ = types[n % len(types)] if n % 9 else g.randrange(-50, 400)
        if name in DIRECTED and n % 3 == 1:
            typ = g.choice(DIRECTED[name])
        world = cls if n % 4 else [0, 80, 141, 142, 143, 144, 145][(n // 4) % 7]
        null = n % 23 == 0
        present = n % 7 != 0
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        struct.pack_into('<H', raw, 0x2a, g.choice([0, 1, 2, 3, 2, 4, 7]))
        if n % 5 == 0:
            v.put_f(raw, 0xa0, v.f32(g.choice([-2.0, 0.1, 3.7, 65537.5, 1e10, -1e10, math.nan, 100.0, -0.0])))
        if n % 6 == 0:
            v.put_i(raw, 0x68, g.choice([-2, -1, 0, 3]))
        if prefix == 'kardamahal' and method == 'create' and n % 8 == 0:   # z - 0.0: signed zero, NaNs
            typ = g.randrange(33, 49)
            v.put_i(raw, 0x5c, typ)
            struct.pack_into('<I', raw, 0x160, g.choice([0x80000000, 0x7f800001, 0xff812345, 0xffc00000, 0x7f800000]))
        time = time_sample(g)
        seed = g.getrandbits(32)
        if method == 'visual' and (prefix, typ) in OPEN and g.random() < 0.6:
            seed = seed_for(g, *OPEN[(prefix, typ)])
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        named = {k: g.randrange(0, 12) for k in range(8) if g.random() < 0.7}   # E002+k -> bone index
        calls, bones, cbones = [], [], []

        def lookup(m):
            assert m.argument(0) == struct.unpack_from('<I', raw, 0x5c)[0]
            return (v.MODEL if present else 0, 4)

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL and a[3] == 0
            k = (a[0] - BONES) // 0x30
            assert a[0] == BONES + k * 0x30
            local = v.read_vec(m, a[1])
            bones.append((k,) + local)
            calls.append(('bone', k) + local)
            m.uc.mem_write(a[2], v.pack_f(*bone_position(k)))
            return (0, 16)

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((LIGHT, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0

        def sound(m):
            a = [m.argument(k) for k in range(3)]
            assert a[1:] == [0, 0]
            calls.append((SOUND, 0, a[0], 0, 0))
            return 0

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6] in (0, v.OBJECTS) and a[7] == 0
            calls.append((PARTICLE, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0

        def sprite(m):
            a = [m.argument(k) for k in range(9)]
            assert a[4] == v.OBJECTS and a[6:8] == [0, 4] and v.read_vec(m, a[8]) == SPRITE_DESCRIPTOR
            calls.append((SPRITE, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) + (a[5], 1, 0, 4))
            return 0

        def joint(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] in (0, v.OBJECTS) and a[7:] == JOINT_TAIL
            calls.append((JOINT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], int(a[5] == v.OBJECTS), a[6]))
            return 0

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == v.OBJECTS and a[6:8] == [0xffffffff, 0] and a[9:] == [0, 0, 0xffffffff, 0, 0]
            assert a[8] <= 0xffff
            calls.append((EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], 1, a[8]))
            return 0

        def animation(m):
            a = [m.argument(k) for k in range(8)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL
            assert a == [BONES, struct.unpack_from('<I', raw, 0xd0)[0], struct.unpack_from('<I', raw, 0xd4)[0],
                         struct.unpack_from('<H', raw, 0x2c)[0], v.OBJECTS + 0x164, v.OBJECTS + 0x170, 0, 1]
            calls.append(('animation',))
            return (0, 32)

        def string_ctor(m):   # std::string(const char *): the harness keeps the source pointer
            this, source = m.uc.reg_read(UC_X86_REG_ECX), m.argument(0)
            m.uc.mem_write(this, struct.pack('<I', source))
            return (this, 4)

        def string_array_dtor(m):
            assert [m.argument(k) for k in range(1, 4)] == [0x18, 8, STRING_DTOR]
            calls.append(('strings freed',))
            return (0, 16)

        def named_bone(m):
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.OBJECTS and m.argument(1) == 1
            source = struct.unpack('<I', bytes(m.uc.mem_read(m.argument(0), 4)))[0]
            k = (source - NAME_TABLE) // 8
            assert source == NAME_TABLE + 8 * k and 0 <= k < 8
            label = bytes(m.uc.mem_read(source, 8)).split(b'\0')[0].decode()
            calls.append(('lookup', label))
            return (BONES + 0x30 * named[k] if k in named else 0, 8)
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                           am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e)),
                                           am.defined_region('model', v.MODEL, bytes(0x100))])
        args = [NULL if null else v.OBJECTS] + ([NULL if not present else v.MODEL] if method == 'visual' else [])
        result = v.run(machine, BODIES[name][0], args, regs,
                       {0x966cc4: lambda m: v.FAKE, 0xeaa8cf: lookup, 0x12b6ef1: bone, LIGHT: light, SOUND: sound,
                        PARTICLE: particle, SPRITE: sprite, JOINT: joint, 0x13c0eaa: effect, ANIMATION: animation,
                        STRING_CTOR: string_ctor, STRING_ARRAY_DTOR: string_array_dtor, NAMED_BONE: named_bone,
                        0x1989721: lambda m: rnd()},
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())

        def cb(ctx, k, local, out):
            cbones.append((k,) + tuple(v.bits(x) for x in local[:3]))
            for q, value in enumerate(bone_position(k)):
                out[q] = value
        c_bone = BONE(cb)
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.time = time
        inputs.rand_fn = fn
        inputs.has_model = int(present)
        obj = None if null else co
        d = lib.dll
        fname = {'twisted': 'mu_twisted_karutan_', 'kardamahal': 'mu_kardamahal_', 'swamp': 'mu_swamp_'}[prefix]
        f = getattr(d, fname + method)
        if method == 'create':
            handled = f(obj, world)
        elif method == 'move':
            handled = f(obj, 0, C.byref(inputs), C.byref(log))
        elif prefix == 'twisted':
            handled = f(obj, 0, int(present), time, fn, c_bone, None, C.byref(log))
        else:
            handled = f(obj, 0, int(present), fn, None, C.byref(log))
        events = []
        for e in v.log_events(log):
            if e[0] == BONE_LIGHTS:   # the host's posed named-bone service, expanded with the same lookup
                events.append(('animation',))
                for k in range(8):
                    events.append(('lookup', d.mu_kardamahal_bone_name(k).decode()))
                    if k in named:
                        events.append(('bone', named[k], 0, 0, 0))
                        x, y = bone_position(named[k])[:2]
                        events.append((LIGHT, 0, v.bits(x), v.bits(y)) + e[2:6])
                events.append(('strings freed',))
            else:
                events.append(e)
        if prefix == 'twisted' and method == 'visual':
            calls = [c for c in calls if c[0] != 'bone']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null' if null else 'handled' if handled else 'unhandled')
        tally.count('model' if present else 'no model')
        tally.count('events', len([c for c in calls if isinstance(c[0], int)]))
        for c in calls:
            if isinstance(c[0], int):
                tally.count('call ' + hex(c[0]))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == events and
                  rnd.seed == crnd.seed and (prefix != 'twisted' or bones == cbones),
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': calls[:4], 'c': events[:4], 'rng_equal': rnd.seed == crnd.seed,
                   'bones': bones[:3], 'c_bones': cbones[:3]})
    return tally.report()


MUTANTS = [
    ('twisted_karutan.c', 'world != 142 ||', 'world != 143 ||', 'twisted_create'),
    ('twisted_karutan.c', 'case 62: case 66:', 'case 62: case 67:', 'twisted_create'),
    ('twisted_karutan.c', 'case 162: case 163: case 167:', 'case 162: case 163: case 166:', 'twisted_create'),
    ('twisted_karutan.c', 'case 197: case 198:', 'case 197: case 199:', 'twisted_create'),
    ('twisted_karutan.c', 'in->world != 142', 'in->world != 141', 'twisted_move'),
    ('twisted_karutan.c', '% 4 + 3) * 0.1f;', '% 4 + 2) * 0.1f;', 'twisted_move'),
    ('twisted_karutan.c', 's * 0.2f, 2);', 's * 0.2f, 3);', 'twisted_move'),
    ('twisted_karutan.c', 'if (!o || !has_model) return 0;', 'if (!o || has_model < 0) return 0;', 'twisted_visual'),
    ('twisted_karutan.c', '* 0.0004)', '* 0.0005)', 'twisted_visual'),
    ('twisted_karutan.c', 's * 1.9f', 's * 1.3f', 'twisted_visual'),
    ('twisted_karutan.c', 'bone(ctx, 7, local, b);', 'bone(ctx, 8, local, b);', 'twisted_visual'),
    ('twisted_karutan.c', '{20.0f, 0.0f, 0.0f}', '{0.0f, 20.0f, 0.0f}', 'twisted_visual'),
    ('twisted_karutan.c', '0x806e, p, a, white, 4,', '0x806e, p, a, white, 0,', 'twisted_visual'),
    ('twisted_karutan.c', 'k < 20;', 'k < 19;', 'twisted_visual'),
    ('twisted_karutan.c', '0x1d, scale, 1);', '0x1d, scale, 0);', 'twisted_visual'),
    ('twisted_karutan.c', 'random(ctx) % 8 == 0', 'random(ctx) % 7 == 0', 'twisted_visual'),
    ('twisted_karutan.c', 'scale * 2.0f, 1);', 'scale * 1.0f, 1);', 'twisted_visual'),
    ('twisted_karutan.c', 'random(ctx) % 50 == 1', 'random(ctx) % 50 == 0', 'twisted_visual'),
    ('twisted_karutan.c', '(uint16_t)wb_int(scale)', '(uint16_t)wb_int(scale + 1.0f)', 'twisted_visual'),
    ('kardamahal.c', 'world != 143 ||', 'world != 144 ||', 'kardamahal_create'),
    ('kardamahal.c', 'POSITION + 8, 64.0f', 'POSITION + 8, 63.0f', 'kardamahal_create'),
    ('kardamahal.c', 'o[MU_OBJF_LIGHT_FULL] = 0;', 'o[MU_OBJF_LIGHT_FULL] = 1;', 'kardamahal_create'),
    ('kardamahal.c', 'case 106: case 107: case 109:', 'case 106: case 107: case 108:', 'kardamahal_create'),
    ('kardamahal.c', 'RANGE, -230.0f', 'RANGE, -200.0f', 'kardamahal_create'),
    ('kardamahal.c', '-2);\n        mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f);',
     '-2);\n        mu_obj_set_f32(o, MU_OBJF_RANGE, -51.0f);', 'kardamahal_create'),
    ('kardamahal.c', 'volatile float zero = 0.0f;', 'volatile float zero = 0.0f; (void)zero; return 1;',
     'kardamahal_create'),
    ('kardamahal.c', 'in->world != 143', 'in->world != 142', 'kardamahal_move'),
    ('kardamahal.c', 's * 0.1f, 3);', 's * 0.1f, 2);', 'kardamahal_move'),
    ('kardamahal.c', '(1.0f - base)', '(1.0f - 0.5f)', 'kardamahal_move'),
    ('kardamahal.c', 'wb_arg(e, 4);', 'wb_arg(e, 3);', 'kardamahal_move'),
    ('kardamahal.c', 'if (!in->has_model) return 1;', 'if (!in->has_model) return 0;', 'kardamahal_move'),
    ('kardamahal.c', '"E009"', '"E010"', 'kardamahal_move'),
    ('kardamahal.c', '{0.1f, 0.41f, 0.8f}', '{0.1f, 0.42f, 0.8f}', 'kardamahal_move'),
    ('kardamahal.c', 'if (t == 128) wb_light', 'if (t == 129) wb_light', 'kardamahal_move'),
    ('kardamahal.c', 'ACTION) == 2)', 'ACTION) == 1)', 'kardamahal_move'),
    ('kardamahal.c', '? 0x5a7 : 0x5a8', '? 0x5a8 : 0x5a7', 'kardamahal_move'),
    ('kardamahal.c', 'case 169: wb_sound', 'case 168: wb_sound', 'kardamahal_move'),
    ('kardamahal.c', '% 80 == 1', '% 80 == 0', 'kardamahal_visual'),
    ('kardamahal.c', 'wb_arg(e, 0x195);', 'wb_arg(e, 0x199);', 'kardamahal_visual'),
    ('kardamahal.c', 'wb_get(o, MU_OBJF_LIGHT, l);', 'wb_get(o, MU_OBJF_ANGLE, l);', 'kardamahal_visual'),
    ('swamp_destruction.c', 'world != 144 ||', 'world != 143 ||', 'swamp_create'),
    ('swamp_destruction.c', 'case 32: case 64:', 'case 32: case 65:', 'swamp_create'),
    ('swamp_destruction.c', 'case 76:\n        o[MU_OBJF_AFTER_CHARACTER] = 1;',
     'case 75:\n        o[MU_OBJF_AFTER_CHARACTER] = 1;', 'swamp_create'),
    ('swamp_destruction.c', 'case 140: case 141: case 142:', 'case 140: case 141: case 143:', 'swamp_create'),
    ('swamp_destruction.c', 'case 181: case 183: case 200:', 'case 181: case 183: case 201:', 'swamp_create'),
    ('swamp_destruction.c', 'in->world != 144', 'in->world != 145', 'swamp_move'),
    ('swamp_destruction.c', '== 183', '== 182', 'swamp_move'),
    ('swamp_destruction.c', 's * 0.1f, 3);', 's * 0.1f, 4);', 'swamp_move'),
    ('swamp_destruction.c', '% 200 != 0', '% 199 != 0', 'swamp_visual'),
    ('swamp_destruction.c', '* 0.005 + 0.2', '* 0.005 + 0.25', 'swamp_visual'),
    ('swamp_destruction.c', 'wb_arg(e, 1); wb_arg(e, 1);', 'wb_arg(e, 0); wb_arg(e, 1);', 'swamp_visual'),
    ('swamp_destruction.c', '{169, 0x19, {1.0f, 0.8f, 0.4f}}', '{169, 0x19, {1.0f, 0.8f, 0.3f}}', 'swamp_visual'),
    ('swamp_destruction.c', '{190, 0x18,', '{190, 0x19,', 'swamp_visual'),
    ('swamp_destruction.c', '{193, 0x13,', '{194, 0x13,', 'swamp_visual'),
    ('swamp_destruction.c', '% 50 != 0', '% 50 != 1', 'swamp_visual'),
    ('swamp_destruction.c', 'wb_vec(e, p); wb_vec(e, p); wb_vec(e, a);', 'wb_vec(e, p); wb_vec(e, a); wb_vec(e, a);',
     'swamp_visual')]


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
    for name in BODIES:
        if a.only and a.only != name:
            continue
        r = report['families'][name] = family(machine, lib, name, a.cases)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, r['examples'][:1], flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-r2-') as tmp:
            for n, (file, old, new, name) in enumerate(MUTANTS):
                if a.only and a.only != name:
                    continue
                dest = Path(tmp) / str(n)
                for directory in ('objects', 'terrain', 'model-codec', 'record-math', 'movement'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
                shutil.copy(ROOT / 'reconstructed/deps.mk', dest / 'deps.mk')
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
                shutil.rmtree(dest)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
