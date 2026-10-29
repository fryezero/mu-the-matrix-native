#!/usr/bin/env python3
"""RENDER-EFFECTS-007 original-instruction families and compiled production mutants.

The bow arrows other than Arrow01: CreateEffect 0x013c0f19 (the shared arrow body 0x013cb34d..0x013cd66f and the
separate bodies of 0x471/0x458, 0x459, 0x442 and 0x474) and MoveEffect 0x0142fd09 for 30 arrow types and the
subtypes CreateArrow passes (0, 2, 0x63), compared with reconstructed/combat/arrow_fx.inc through libcombat. The
harness is validate_skill_fx's: rand, terrain height, the trigonometric wrappers, CreateEffect/Particle/Joint/
Sprite, AddTerrainLight, the model getters, pose and bone, the hit checks and the area request are recording
services; AngleMatrix, VectorRotate, the vector helpers, 0x011ff622 and the Inferno burst 0x013c07f4 run as client
code. On top of validate_skill_fx's comparison this tool compares CreateJoint's arguments 7..13 (the colour behind
argument 11 by value), CreateEffect's key and scale, and lets the client write the caller's position and angle
vectors (CreateArrow's locals). No client bytes or decoded data are written by this tool.
"""
import argparse
import ctypes as C
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile

import actor_machine as am
import pins
import validate_skill_fx as fx
import validate_combat as vc
import validate_particles as pt
import validate_render_effects4 as re4

ROOT = Path(__file__).resolve().parents[1]
f32 = fx.f32
ARROWS = [0x43c, 0x43d, 0x43e, 0x43f, 0x440, 0x441, 0x442, 0x443, 0x458, 0x459, 0x45a, 0x45b, 0x45c, 0x45d, 0x45e,
          0x471, 0x474, 0x47f, 0x525, 0x5b0, 0x5b1, 0x60a, 0x60d, 0x60e, 0x60f, 0x610, 0x612, 0x613, 0x614, 0x616]
NOT_RECONSTRUCTED = [0x615, 0x617]   # their moves place sprites at bones looked up by name
KINDS = [(t, s) for t in ARROWS for s in (0, 2, 0x63)] + [(0x43b, 0x63)]
HERO_CHAR = 0x2a000000
STRAIGHT = [0x2d7, 0x7e7, 0x7fc, 0x7fd, 0x7fe]
MOVE_DEFINED = fx.MOVE_DEFINED | {'impact', 'field_188', 'field_70', 'field_78'}
JOINT_TAIL = (0, -1, None, -1, 0)   # CreateJoint arguments 9, 10, (11 the colour), 12, 13

MUTANTS = [
    # (name, old, new, family, kind)
    ('bow_offset', 'static const float offset[3] = {-10.0f, -60.0f, 135.0f};\n        float p[3];\n        rotate_by(offset, e->angle, p);\n        for (int k = 0; k < 3; ++k)\n            e->position[k] = e->position[k] + p[k];\n    }',
     'static const float offset[3] = {-10.0f, -50.0f, 135.0f};\n        float p[3];\n        rotate_by(offset, e->angle, p);\n        for (int k = 0; k < 3; ++k)\n            e->position[k] = e->position[k] + p[k];\n    }', 'effect_create', (0x43c, 0)),
    ('blend_43f', 'type == 0x43f || type == 0x443)', 'type == 0x443)', 'effect_create', (0x43f, 0)),
    ('scale_443', 'e->scale = 1.8f;\n        e->direction[1] = -50.0f;', 'e->scale = 1.6f;\n        e->direction[1] = -50.0f;',
     'effect_create', (0x443, 0)),
    ('lift_471', 'e->position[2] = e->position[2] + 130.0f;\n        set3(e->direction, 0.0f, -70.0f, 0.0f);\n        copy3(e->field_188, e->position);\n        call_joint_args(env, e, 0x7fd6, e->position, e->position, e->angle, 5, 100.0f, -1, 0, NULL);\n        if (subtype != 0)\n            arrow_trail(env, e);\n        e->serial',
     'e->position[2] = e->position[2] + 120.0f;\n        set3(e->direction, 0.0f, -70.0f, 0.0f);\n        copy3(e->field_188, e->position);\n        call_joint_args(env, e, 0x7fd6, e->position, e->position, e->angle, 5, 100.0f, -1, 0, NULL);\n        if (subtype != 0)\n            arrow_trail(env, e);\n        e->serial', 'effect_create', (0x471, 0)),
    ('rings_459', 'const int n = subtype == 1 ? 3 : subtype == 3 ? 8 : 4;', 'const int n = subtype == 1 ? 3 : subtype == 3 ? 8 : 3;',
     'effect_create', (0x459, 0)),
    ('life_442', 'e->gravity = -10.0f;\n        e->lifetime = 40;', 'e->gravity = -10.0f;\n        e->lifetime = 30;', 'effect_create', (0x442, 0)),
    ('tint_60d', 'static const float tint[3] = {1.0f, 0.7f, 0.4f};', 'static const float tint[3] = {0.4f, 0.7f, 1.0f};',
     'effect_create', (0x60d, 0)),
    ('turn_47f', 'e->angle[1] = (float)smod(env_rand(env), 360);\n        call_joint_args(env, e, 0x7f79, e->position, e->position, e->angle, 0xc',
     'e->angle[1] = (float)smod(env_rand(env), 180);\n        call_joint_args(env, e, 0x7f79, e->position, e->position, e->angle, 0xc', 'effect_create', (0x47f, 0)),
    ('key_45b', 'e->angle, 0xf, 50.0f, 0x28, 0, NULL);', 'e->angle, 0xf, 50.0f, -1, 0, NULL);', 'effect_create', (0x45b, 0)),
    ('trail_sub', 'if (subtype == 2 || subtype == 6)\n        arrow_trail(env, e);', 'if (subtype == 6)\n        arrow_trail(env, e);',
     'effect_create', (0x43c, 2)),
    ('spin_rate', '(float)t * F_0_1);', '(float)t * F_0_2);', 'effect_move', (0x441, 0)),
    ('scatter_441', 'arrow_scatter(env, e->position, 16, 32, p);\n                call_particle(env, e, 0x7f73',
     'arrow_scatter(env, e->position, 32, 16, p);\n                call_particle(env, e, 0x7f73', 'effect_move', (0x441, 0)),
    ('light_443', 'call_particle(env, e, 0x7f5a, e->position, e->angle, e->light, 0, 1.0f, -1);\n        else if',
     'call_particle(env, e, 0x7f5a, e->position, e->angle, light, 0, 1.0f, -1);\n        else if', 'effect_move', (0x443, 0)),
    ('even_47f', 'if ((e->lifetime & 1) == 0) {\n            for (int k = 0; k < 3; ++k) {',
     'if ((e->lifetime & 1) == 1) {\n            for (int k = 0; k < 3; ++k) {', 'effect_move', (0x47f, 0)),
    ('bounce_442', 'e->gravity = -e->gravity * F_0_4;', 'e->gravity = -e->gravity * F_0_2;', 'effect_move', (0x442, 0)),
    ('fade_471', ': 1.0f;\n            if (!straight)', ': 0.9f;\n            if (!straight)', 'effect_move', (0x471, 0)),
    ('glow_45d', 't = t * 6.0f;', 't = t * 5.0f;', 'effect_move', (0x45d, 0)),
    ('jitter_y', 'out[1] = arrow_rand_range(env, -d * 2.0f, d) + out[1];', 'out[1] = arrow_rand_range(env, -d, d) + out[1];',
     'effect_move', (0x612, 0)),
    ('glint_610', 'arrow_rand_range(env, 0.0f, 15.0f) / 70.0f + 0.5f;\n        set3(c, g, g, g);',
     'arrow_rand_range(env, 0.0f, 15.0f) / 60.0f + 0.5f;\n        set3(c, g, g, g);', 'effect_move', (0x610, 0)),
    ('spark_60e', '(float)(smod(env_rand(env), 60) + 10) * F_0_01', '(float)(smod(env_rand(env), 60) + 20) * F_0_01',
     'effect_move', (0x60e, 0)),
    ('rate_5b1', 'if (smod(env_rand(env), 3) == 0) {\n            set3(c, F_0_4, 0.95f, 1.0f);',
     'if (smod(env_rand(env), 3) != 0) {\n            set3(c, F_0_4, 0.95f, 1.0f);', 'effect_move', (0x5b1, 0)),
    ('spark_offset', 'static const float offset[3] = {0.0f, 10.0f, -130.0f};', 'static const float offset[3] = {0.0f, 10.0f, -120.0f};',
     'sparks', None),
    ('spark_joint', 'if (smod(env_rand(env), 2) == 0) {\n            mu_sfx_call c;', 'if (smod(env_rand(env), 2) != 0) {\n            mu_sfx_call c;',
     'sparks', None),
    ('beam_45c', 'call_joint_args(env, e, 0x7f79, p, p, e->angle, 0x12, 90.0f', 'call_joint_args(env, e, 0x7f79, p, p, e->angle, 0x12, 80.0f',
     'effect_move', (0x45c, 0)),
]


class Case(fx.Case):
    """validate_skill_fx's case with CreateJoint's tail and CreateEffect's key/scale recorded on both sides."""

    def stubs(self, m):
        s = super().stubs(m)

        def joint(mm):
            a = [mm.argument(i) for i in range(14)]
            light = mm.floats(a[11], 3) if a[11] else None
            self.client_calls.append(('joint', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3), a[4],
                                      fx.owner_of(a[5]), fx.from_bits(a[6]), sx(a[7]), sx(a[8]),
                                      (sx(a[9]), sx(a[10]), light, sx(a[12]), sx(a[13]))))
            return 0

        def effect(mm):
            a = [mm.argument(i) for i in range(14)]
            self.client_calls.append(('effect', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      sx(a[4]), fx.owner_of(a[5]), a[6] & 0xffff, fx.from_bits(a[10]),
                                      (a[7], a[8], a[9], a[11], a[12], a[13])))
            return 0
        s[fx.CREATE_JOINT] = joint
        s[fx.CREATE_EFFECT_WRAPPER] = effect
        return s

    def env(self, *args, **kwargs):
        env = super().env(*args, **kwargs)
        inner = self._keep[3]

        def call(ctx, cp, ep):
            c = cp.contents
            if c.routine == fx.CREATE_JOINT:
                light = list(c.light) if any(c.light) else None
                self.c_calls.append(('joint', c.type, list(c.position), list(c.target), list(c.angle), c.subtype,
                                     c.owner, c.scale, c.arg7, c.arg8, (0, -1, light, -1, 0)))
                return 0
            if c.routine == fx.CREATE_EFFECT_WRAPPER:
                self.c_calls.append(('effect', c.type, list(c.position), list(c.angle), list(c.light), c.subtype,
                                     c.owner, c.range & 0xffff, c.scale, (0, 0, 0, 0, 0, 0)))
                return 0
            return inner(ctx, cp, ep)
        self._call7 = fx.CALL_FN(call)
        env.call = self._call7
        return env


def sx(v):
    return v - (1 << 32) if v & 0x80000000 else v


def compare_calls(client, mine):
    client = [c for c in client if c[0] != 'init']
    if len(client) != len(mine):
        return ('count', len(client), len(mine), client[:6], mine[:6])
    for a, b in zip(client, mine):
        if a[0] != b[0]:
            return ('kind', a, b)
        if a[0] == 'effect':
            if not vc._same_call(list(a[1:9]), list(b[1:9])):
                return ('value', a, b)
            continue
        if a[0] == 'joint':
            if not vc._same_call(list(a[1:10]), list(b[1:10])):
                return ('value', a, b)
            ta, tb = a[10], b[10]
            if ta[:2] != tb[:2] or ta[3:] != tb[3:] or (ta[2] is None) != (tb[2] is None) or \
                    (ta[2] is not None and not vc._same_call(ta[2], tb[2])):
                return ('joint tail', a, b)
            continue
        for x, y in zip(a[1:], b[1:]):
            if y is None:
                continue
            if not vc._same_call([x], [y]):
                return ('value', a, b)
    return None


def random_info(rng):
    info = fx.Info()
    info.key = rng.randrange(0, 0x10000)
    info.skill = rng.choice([0, 0x18, 0x18, 0x34, 0x1a0, 0x33] + STRAIGHT)
    info.word4 = rng.choice([0, 1, 1, 2, 0x101] + STRAIGHT)
    info.word6 = rng.randrange(0, 0x10000)
    info.field8 = rng.randrange(0, 0x10000)
    info.field18 = rng.randrange(-2**31, 2**31)
    info.field1c = rng.randrange(-2**31, 2**31)
    return info


def family_create(m, lib, rng, cases, report, kinds):
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        objects = [fx.random_object(rng) for _ in range(2)]
        owner = rng.choice([-1, 0, 1])
        pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
        angle = [vc.rfloat(rng, 0.1, 360.0) if k == 2 or rng.random() < 0.3 else 0.0 for k in range(3)]
        light = [vc.rfloat(rng, 0.1, 1.5) for _ in range(3)]
        scale = f32(rng.choice([0.0, 0.0, 1.0, vc.rfloat(rng, 0.2, 3.0)]))
        info = random_info(rng)
        serial = rng.randrange(0, 256)
        case = Case(rng, objects, fx.rand_values(rng), vc.rfloat(rng, 0.1, 400.0))
        inputs = am.defined_region('inputs', fx.INPUTS, struct.pack('<9f', *pos, *angle, *light) + fx.info_bytes(info),
                                   writable=True)
        record = am.Region('record', fx.POOL, am.poison(0x3d8, 0x31), bytes(0x3d8))
        record.define(fx.POOL, b'\0')
        hero = am.Region('hero-data', fx.HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
        hero.define(fx.HERO_DATA + 0x2dec, bytes([serial]))
        regions = [inputs, record, fx.object_region(objects), hero,
                   am.defined_region('hero-ptr', fx.HERO_DATA_PTR, struct.pack('<I', fx.HERO_DATA), writable=False),
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', 0x5000000), writable=False)]
        r = m.execute(fx.CREATE_EFFECT, [kind[0], kind[1], fx.INPUTS, fx.INPUTS + 12, fx.INPUTS + 24,
                                         fx.object_address(owner), fx.bits(scale), fx.INPUTS + 36],
                      regions, case.stubs(m), ecx=fx.POOL, cleanup=0x20)
        e = fx.Effect()
        F3 = C.c_float * 3
        env = case.env(serial=serial)
        source_light = F3(*light)
        supported = lib.mu_sfx_effect_create(C.byref(e), kind[0], kind[1], F3(*pos), F3(*angle), source_light, owner,
                                             scale, C.byref(info), C.byref(env))
        mismatch = None
        refused = kind[0] == 0x442 and info.skill in STRAIGHT or info.skill == 0x2d8
        if vc.ok(r) and not refused:
            raw = r['regions']['record']
            mismatch = fx.compare_effect(e, raw, record.defined)
            if mismatch is None and bytes(source_light) != r['regions']['inputs'][24:36]:
                mismatch = ('source light', list(source_light))
            if mismatch is None and struct.unpack('<I', raw[0x34c:0x350])[0] != fx.object_address(owner):
                mismatch = ('owner',)
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None and r['regions']['hero-data'][0x2dec] != serial:
                mismatch = ('serial changed',)
        equal = (supported if not refused else not supported) and vc.ok(r) and mismatch is None
        report.add('effect_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'skill': hex(info.skill),
                                            'word4': hex(info.word4), 'mismatch': mismatch, 'stopped': r['stopped'],
                                            'error': r['error']})
        report.cover('effect_create', f'{kind[0]:#x}/{kind[1]}' + ('/refused' if refused else ''))


def random_arrow(rng, kind):
    e = fx.random_effect(rng, kind)
    # skills 0x7e7/0x7fc/0x7fd add MoveEffect's ground test 0x014eca2e (not reconstructed, as for Arrow01)
    e.skill = rng.choice([0, 0x18, 0x18, 0x34, 0x2d7, 0x7fe])
    e.lifetime = rng.choice([30, 30, 29, 28, 26, 25, 24, 13, 12, 2, 1, 1, 0, rng.randrange(-2, 52)])
    e.field_70 = rng.choice([30, 24, 50, rng.randrange(1, 60)])
    e.gravity = f32(rng.choice([-10.0, -3.0, 0.0, 4.0, vc.rfloat(rng, 0.2, 30.0)]))
    e.serial = rng.randrange(0, 256)
    for k in range(3):
        e.impact[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        e.field_188[k] = vc.rfloat(rng, 0.05, 30000.0)
    e.direction[0] = 0.0
    e.direction[1] = f32(rng.choice([-70.0, -60.0, -40.0, -28.0, vc.rfloat(rng, -80.0, 0.0)]))
    e.direction[2] = 0.0 if rng.random() < 0.7 else vc.rfloat(rng, -5.0, 5.0)
    e.field_78 = rng.choice([0, 1, 5])
    return e


def family_move(m, lib, rng, cases, report, kinds):
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = random_arrow(rng, kind)
        objects = [fx.random_object(rng) for _ in range(2)]
        e.owner = rng.choice([-1, 0, 1])
        hero_obj = rng.choice([-1, 0, 1, e.owner])
        animation = rng.choice([0, 1, 1])
        keys = rng.choice([1, 7, 10, 30])
        has_model = rng.random() < 0.85
        case = Case(rng, objects, fx.rand_values(rng, 120), vc.rfloat(rng, 0.1, 600.0), animation, keys, has_model)
        raw, mask = fx.effect_to_bytes(e, MOVE_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(fx.MODEL + 0x30, struct.pack('<I', fx.MODEL + 0x1000))
        for a in range(0x100):
            model.define(fx.MODEL + 0x1000 + 16 * a + 8, struct.pack('<h', keys))
        quake = am.Region('quake', fx.QUAKE, am.poison(4, 0x21), bytes(4))
        clock = f32(rng.choice([0.0, 1000.0, rng.uniform(-20000.0, 3000000.0), rng.uniform(0.0, 1.0e5)]))
        hero_char = (fx.object_address(hero_obj) - 0x3254) & 0xffffffff if hero_obj >= 0 else 0x5000000
        regions = [record, fx.object_region(objects), model, quake,
                   am.defined_region('world', fx.WORLD, struct.pack('<i', 0), writable=False),
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False),
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', hero_char), writable=False)]
        r = m.execute(fx.MOVE_EFFECT, [fx.POOL, 0], regions, case.stubs(m))
        env = case.env(hero_object=hero_obj)
        env.world_time = clock
        supported = lib.mu_sfx_effect_move(C.byref(e), C.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = fx.compare_effect(e, out, record.defined, MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('effect_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'lifetime': e.lifetime,
                                          'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        made = sorted({c[0] for c in case.client_calls if c[0] in ('particle', 'sprite', 'joint', 'effect', 'area')})
        report.cover('effect_move', f'{kind[0]:#x}/{kind[1]}/' + ('+'.join(made) or 'none'))


BONE_LOOKUP = 0x0129f12c


def family_sparks(m, lib, rng, cases, report, kinds=None):
    """CreateArrows 0x0158d5bd with bow 0x12f9: the shots (CreateArrow) are recorded and skipped; what follows is
    compared with mu_sfx_bow_sparks."""
    lib.mu_sfx_bow_sparks.argtypes = [C.c_int16, C.c_int32, C.c_int, C.c_int32, C.c_int, C.POINTER(fx.Env)]
    lib.mu_sfx_bow_sparks.restype = C.c_int
    lib.mu_sfx_create_arrows.argtypes = [C.POINTER(re4.Archer), C.c_float * 3, C.c_uint16, C.c_uint16, C.c_uint16,
                                         C.POINTER(re4.Shots)]
    for n in range(cases):
        a = re4.random_archer(rng)
        a.weapon = rng.choice([0x12f9, 0x12f9, 0x12f9, 0x12f8])
        skill, index = rng.choice(re4.SKILLS), rng.choice(re4.INDICES)
        flag = rng.choice([1, 1, 0, 2])
        angle = [0.0, 0.0, f32(rng.uniform(0.0, 360.0))]
        regions = re4.archer_regions(a, angle, [1000.0, 2000.0, 100.0], 7, [1.0, 1.0, 1.0])
        slot = rng.randrange(0, 4)
        bone = rng.choice([0, 1, 33, 40, 200]) if slot else 0   # slot 0: the slot byte is the bone byte
        bone_ok = rng.random() < 0.8
        has_model = rng.random() < 0.9
        char = regions[0]
        char.define(re4.ARCHER_CHAR + 0x19b1, bytes([slot]))
        char.define(re4.ARCHER_CHAR + slot * 0x3fc + 0x19b1, bytes([bone]))
        regions[1].define(re4.ARCHER_OBJ + 0x5c, struct.pack('<i', 0x4a8))
        case = Case(rng, [], fx.rand_values(rng, 60), 0.0, has_model=has_model)
        stubs = case.stubs(m)
        stubs.update({re4.CREATE_ARROW: lambda mm: 0, 0x01094039: lambda mm: a.tree_value & 0xffffffff,
                      0x00ac3bf7: lambda mm: 0x0a000000, 0x0095f998: lambda mm: 0x0a000100,
                      0x00bb1e55: lambda mm: (a.master_1a2, 4),
                      BONE_LOOKUP: lambda mm: ((0x06fce398 + 0x30 * mm.argument(0)) if bone_ok else 0, 4)})

        def transform(mm):   # the synthetic TransformPosition into the caller's frame
            index, vec, out = (mm.argument(0) - 0x06fce398) // 0x30, mm.floats(mm.argument(1), 3), mm.argument(2)
            case.client_calls.append(('owner_bone', index, vec))
            mm.uc.mem_write(out, struct.pack('<3f', *fx.owner_bone_answer(index, vec)))
            return 0, 0x10
        stubs[fx.TRANSFORM_POSITION] = transform
        r = m.execute(re4.CREATE_ARROWS, [re4.ARCHER_CHAR, re4.ARCHER_OBJ, re4.TARGET_OBJ, skill, flag, index],
                      regions, stubs)
        shots = re4.Shots()
        lib.mu_sfx_create_arrows(C.byref(a), (C.c_float * 3)(*angle), skill, flag, index, C.byref(shots))
        env = case.env()
        made = lib.mu_sfx_bow_sparks(a.weapon, 0, has_model, bone, bone_ok, C.byref(env)) if shots.bow_sparks else 0
        mismatch = None
        if vc.ok(r):
            theirs = [c if c[0] != 'owner_bone' else c[:3] for c in case.client_calls]
            mine = [c if c[0] != 'owner_bone' else c[:3] for c in case.c_calls]
            mismatch = compare_calls(theirs, mine)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        report.add('sparks', vc.ok(r) and mismatch is None,
                   {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('sparks', f'{made} sparks')


def compile_mutant(directory, name, old, new):
    base = ROOT/'reconstructed'/'combat'
    inc = (base/'arrow_fx.inc').read_text()
    if inc.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    work = directory/name
    work.mkdir()
    shutil.copy(base/'skill_fx.c', work/'skill_fx.c')
    (work/'arrow_fx.inc').write_text(inc.replace(old, new))
    others = ['combat.c', '../objects/world_warp.c', '../joints/joints.c', '../record-math/record_math.c',
              '../movement/client_movement.c']
    out = directory/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(base), str(work/'skill_fx.c'), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return fx.load_library(out)


def compare(text, data, lib, name, kinds, cases):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    m = fx.FxMachine(text, data)
    report = pt.Report()
    rng = random.Random('render-effects-007-' + name)
    {'effect_create': family_create, 'effect_move': family_move, 'sparks': family_sparks}[name](
        m, lib, rng, cases, report, kinds)
    return {'families': report.families, 'coverage': report.coverage}


BODIES = {'arrow_create': (0x013cb34d, 0x013cd688), 'create_471': (0x013ca9f2, 0x013cac12),
          'create_458': (0x013cac12, 0x013cae32), 'create_459': (0x013cae32, 0x013cb34d),
          'create_442': (0x013ce0de, 0x013ce327), 'create_474': (0x013d8da1, 0x013d8fea),
          'move_471_458_459': (0x01464238, 0x01464abf), 'move_shared': (0x01464ece, 0x01465d5b),
          'move_45a_45b_442_45c_45d_45e': (0x01466819, 0x01467f03), 'move_525_60a': (0x014681fe, 0x01468a1f),
          'move_60d_616': (0x01468c0a, 0x0146af38), 'move_474': (0x014712e8, 0x014716e9),
          'move_5b0_5b1': (0x014abb41, 0x014abc00), 'create_5b0_5b1': (0x013f5f8c, 0x013f667f),
          'bow_sparks': (0x0158dfdc, 0x0158e1aa), 'move_459_motion': (0x014ed2ef, 0x014ed46a), 'bounce': (0x0150de66, 0x0150df8e),
          'straight_skill': (0x013bce8f, 0x013bced1)}


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {},
              'not_reconstructed': [hex(t) for t in NOT_RECONSTRUCTED]}
    lib = fx.load_library(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX))
    for name in ('effect_create', 'effect_move'):
        result['comparisons'][name] = compare(text, data, lib, name, KINDS, cases * len(KINDS))
    result['comparisons']['sparks'] = compare(text, data, lib, 'sparks', None, cases * 20)
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects7-mutants-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                mlib = compile_mutant(Path(tmp), name, old, new)
                f = compare(text, data, mlib, family, [kind], max(40, cases))['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                               'sha256': hashlib.sha256(text[a - am.TEXT_BASE:b - am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in BODIES.items()}
    result['families'] = {name: r['families'][name] for name, r in result['comparisons'].items()}
    result['instruction_cases'] = sum(f['cases'] for f in result['families'].values())
    result['all_equal'] = all(f['cases'] == f['equal'] for f in result['families'].values())
    result['all_mutants_caught'] = all(v['caught'] > 0 for v in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=20, help='cases per (type, subtype) and family')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2))
    summary = {k: {f: (v['cases'], v['equal']) for f, v in r['families'].items()}
               for k, r in result['comparisons'].items()}
    print(json.dumps({'summary': summary, 'mutants': result['mutants'], 'all_equal': result['all_equal'],
                      'all_mutants_caught': result['all_mutants_caught']}, indent=1))
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
