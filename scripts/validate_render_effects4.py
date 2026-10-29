#!/usr/bin/env python3
"""RENDER-EFFECTS-004 original-instruction families and compiled production mutants.

Rageful Blow, ordinary worlds: CreateEffect 0x461 (flying weapon) and its pieces 0x462..0x46b,
their MoveEffect cases (0x01450a73 and the piece bodies), the item object initialiser 0x016da00b
and the weapon draw RenderEffects 0x01532bd2. Fresh strict machines per family/mutant. Terrain
height, TerrainWall words, rand, sine, CreateEffect/Particle/Joint, PlayBuffer, the animation
player, RequestTerrainLight, the model pose and RenderPartObject are recorded services; the
special-world predicate 0x009b0418 is false (ordinary worlds). GPU and session routing have
separate native tests. No client bytes or decoded data are written by this tool.
"""
import argparse
import ctypes as C
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import tempfile

import actor_machine as am
import pins
import validate_render_effects as base
import validate_skill_fx as fx
import validate_combat as vc
import validate_particles as pt

ROOT = Path(__file__).resolve().parents[1]
f32 = fx.f32
CREATE_KINDS = [(0x461, 0), (0x462, 0), (0x462, 1), (0x463, 0), (0x463, 1), (0x463, 2), (0x464, 0), (0x465, 0),
                (0x466, 0), (0x466, 1), (0x468, 0), (0x469, 0), (0x469, 1), (0x46a, 0), (0x46b, 0), (0x460, 4)]
MOVE_KINDS = [(0x461, 0)] * 6 + [(0x462, 0), (0x463, 0), (0x464, 0), (0x465, 0), (0x466, 0), (0x468, 0),
                                 (0x469, 0), (0x46a, 0), (0x46b, 0), (0x460, 4)]
WALL_ROUTINE, ITEM_LINKS = 0x016d34cd, 0x01295f18
TERRAIN_COLOR, RENDER_PART, POSE = 0x016cb08d, 0x017e63f4, 0x012b5064
WEAPON_DRAW, ITEM_INIT = 0x01532bd2, 0x016da00b
HERO_CHAR = 0x2a000000
ITEM_TYPES = [0xa99, 0xa9d, 0xaa1, 0xaa2, 0xae6, 0xaeb, 0xaf0, 0xaf3, 0xaf4, 0xb05, 0xb0d, 0xeea, 0xeeb, 0xeec,
              0xeed, 0xf0b, 0x10e6, 0x10ef, 0x10f0, 0x12ec, 0x12f3, 0x12f4, 0x12f6, 0x14e6, 0x14eb, 0x14ec, 0x14ed,
              0x14ee, 0x14ef, 0x14f1, 0x14f3, 0x150c, 0x1513, 0x1516, 0x16f1, 0x16f2, 0x16f3, 0x16f4, 0x16f6,
              0x1701, 0x1702, 0x170b, 0x1711, 0x18fe, 0x1cfe, 0x22e6, 0x22e9, 0x236a, 0x248e, 0x24e6, 0x26e7,
              0x26fb, 0x28e6, 0x1200, 0x0b00]
RB_MOVE_DEFINED = fx.MOVE_DEFINED | {'impact', 'heading_yz', 'field_80', 'spin'}
INIT_FIELDS = {'live', 'flag5', 'flag_c', 'action', 'prior_action', 'type', 'field_68', 'blend_mesh', 'scale',
               'blend_light', 'blend_u', 'blend_v', 'velocity', 'gravity', 'frame', 'prior_frame', 'alpha', 'light',
               'field_4', 'field_c0'}
ALL_DEFINED = RB_MOVE_DEFINED | INIT_FIELDS

MUTANTS = [
    ('rb_lifetime', '        e->lifetime = 20;\n        e->subtype = smod', '        e->lifetime = 21;\n        e->subtype = smod',
     'effect_create', (0x461, 0)),
    ('rb_impact_depth', 'e->impact[2] = e->impact[2] - 27.0f;', 'e->impact[2] = e->impact[2] - 26.0f;',
     'effect_move', (0x461, 0)),
    ('rb_ring_step', '(float)e->subtype + (float)k * 72.0f', '(float)e->subtype + (float)k * 70.0f',
     'effect_move', (0x461, 0)),
    ('rb_wall_gate', 'if ((wall & 4) && (wall & 8) && (wall & 0x10))', 'if ((wall & 4) || (wall & 8) || (wall & 0x10))',
     'effect_move', (0x461, 0)),
    ('rb_hop_height', 'e->position[2] = e->position[2] + 200.0f;\n        }', 'e->position[2] = e->position[2] + 190.0f;\n        }',
     'effect_move', (0x461, 0)),
    ('quake_sink', '        if (e->lifetime < 13)\n            e->position[2] = e->position[2] - 0.5f;',
     '        if (e->lifetime < 12)\n            e->position[2] = e->position[2] - 0.5f;', 'effect_move', (0x464, 0)),
    ('quake_red_light', '                light[0] = lum * 1.0f;\n                light[1] = lum * 0.0f;',
     '                light[0] = lum * 0.5f;\n                light[1] = lum * 0.0f;', 'effect_move', (0x463, 0)),
    ('tail_gravity', 'e->gravity = e->gravity + 60.0f;', 'e->gravity = e->gravity + 50.0f;', 'effect_move', (0x46b, 0)),
    ('flash_scale', '        e->scale = 0.5f;\n        e->lifetime = 15;', '        e->scale = 0.6f;\n        e->lifetime = 15;',
     'effect_create', (0x46a, 0)),
    ('wing_fade', 'e->alpha = e->alpha * f32bits(0x3f7851ecu);', 'e->alpha = e->alpha * f32bits(0x3f75c28fu);',
     'effect_move', (0x460, 4)),
    ('wing_drift', '(float)(smod(env_rand(env), 20) - 10) * 4.0f + e->position[k];',
     '(float)(smod(env_rand(env), 20) - 10) * 3.0f + e->position[k];', 'effect_create', (0x460, 4)),
    ('triple_spread', '            angle[2] = angle[2] + 15.0f;\n            arrow_shot(out, angle, last);\n            angle[2] = angle[2] - 30.0f;',
     '            angle[2] = angle[2] + 8.0f;\n            arrow_shot(out, angle, last);\n            angle[2] = angle[2] - 16.0f;', 'arrows', None),
    ('arrow_table', '    case 0x12e8: return 0x43f;', '    case 0x12e8: return 0x43b;', 'arrow', None),
    ('item_scale', '    e->scale = F_0_8;\n    call_plain(env, e, MU_SFX_CALL_ITEM_LINKS);',
     '    e->scale = F_0_9;\n    call_plain(env, e, MU_SFX_CALL_ITEM_LINKS);', 'item_init', None),
    ('weapon_level', 'out->level = (int32_t)(o ? o->level : 0) << 3;', 'out->level = (int32_t)(o ? o->level : 0) << 2;',
     'weapon', None),
]


def load(path):
    lib = fx.load_library(path)
    P = C.POINTER
    lib.mu_sfx_item_object_init.argtypes = [P(fx.Effect), P(fx.Env)]
    lib.mu_sfx_item_object_init.restype = None
    lib.mu_sfx_rageful_weapon.argtypes = [P(fx.Effect), C.c_float*3, C.c_uint8, P(fx.Env), P(WeaponDraw)]
    lib.mu_sfx_rageful_weapon.restype = C.c_int
    lib.mu_sfx_create_arrows.argtypes = [P(Archer), C.c_float*3, C.c_uint16, C.c_uint16, C.c_uint16, P(Shots)]
    lib.mu_sfx_create_arrows.restype = C.c_int
    lib.mu_sfx_create_arrow.argtypes = [P(Archer), C.c_float*3, C.c_float*3, C.c_uint16, C.c_uint16, C.c_uint16,
                                        C.c_int32, P(fx.Env), P(ArrowEffect)]
    lib.mu_sfx_create_arrow.restype = C.c_int
    return lib


class WeaponDraw(C.Structure):
    _fields_ = [('model', C.c_int32), ('origin', C.c_float*3), ('angle', C.c_float*3), ('head_angle', C.c_float*3),
                ('frame', C.c_float), ('prior_frame', C.c_float), ('prior_action', C.c_uint16),
                ('action', C.c_uint16), ('hero_class', C.c_uint8), ('light', C.c_float*3), ('alpha', C.c_float),
                ('level', C.c_int32)]


def objects_for(rng):
    objects = [fx.random_object(rng) for _ in range(2)]
    for o in objects:
        o.type = rng.choice([0x804, 0x962, 0x461, 0, 0x4a8, 0x4a8])
        o.level = rng.choice([0, 1, 7, 13, 15, -3])
        o.weapon = rng.choice([0, 5, 10, 0x0d, 0x1f, 0x400, 0x404, 0x1d0])
        for k in range(3):
            o.angle[k] = f32(rng.choice([0.0, 90.0, 180.0, rng.uniform(0.0, 360.0)])) if k == 2 or rng.random() < 0.2 \
                else 0.0
    return objects


def wall_words(rng):
    mode = rng.choice(['clear', 'random', 'blocked'])
    if mode == 'clear':
        return [0] * 0x10000
    if mode == 'blocked':
        return [0x1c] * 0x10000
    return [rng.choice([0, 0, 0, 4, 8, 0x10, 0x0c, 0x1c, 0x14, 1, 0x100]) for _ in range(0x10000)]


def with_rb_calls(case, env):
    """Wrap the C call hook: TerrainWall words (unmasked index) and the CreateEffect key."""
    original = case._keep[3]
    case.c_keys = []

    def call(ctx, cp, ep):
        c = cp.contents
        if c.routine == WALL_ROUTINE:
            index = (c.range << 8) + c.subtype
            return case.attributes[index] if case.attributes and 0 <= index < 0x10000 else 0
        if c.routine == fx.CREATE_EFFECT_WRAPPER:
            case.c_keys.append(c.range & 0xffff)
        return original(ctx, cp, ep)
    case._rb_call = fx.CALL_FN(call)
    env.call = case._rb_call
    return env


def client_keys(case):
    return [c[7][0] & 0xffff for c in case.client_calls if c[0] == 'effect']


def random_rb(rng, kind):
    e = fx.random_effect(rng, kind)
    e.owner = rng.choice([0, 1])
    if kind[0] != 0x461:
        e.owner = rng.choice([-1, 0, 1])
    for k in range(2):
        e.position[k] = f32(rng.uniform(400.0, 25000.0))
        e.impact[k] = f32(rng.uniform(400.0, 25000.0)) if rng.random() < 0.7 else e.position[k]
    e.impact[2] = f32(rng.uniform(0.0, 600.0))
    e.heading = f32(rng.choice([0.0, 80.0, rng.uniform(0.0, 720.0)]))
    for k in range(3):
        e.spin[k] = f32(rng.choice([-5.0, 0.0, 4.0, rng.uniform(-5.0, 5.0)]))
    for k in range(2):
        e.heading_yz[k] = f32(rng.choice([0.0, 180.0, rng.uniform(0.0, 360.0)]))
    e.client_hit = rng.choice([0, 0, 0, 1, 3])
    e.skill = rng.choice([42, 42, 42, 0x7fb, 0x7f8, 0])
    e.subtype = rng.randrange(0, 100) if kind[0] == 0x461 else kind[1]
    e.scale = f32(rng.choice([0.4, 1.0, 1.5, 51.0, rng.uniform(0.3, 3.0)]))
    if kind[0] == 0x461:
        e.lifetime = rng.choice([20, 16, 15, 14, 13, 12, 11, 11, 10, 10, 9, 5, 4, 1, 0, rng.randrange(-2, 22)])
        e.gravity = f32(rng.choice([50.0, -50.0, 58.0, rng.uniform(-80.0, 80.0)]))
    elif kind[0] == 0x46b:
        e.lifetime = rng.choice([6, 5, 1, 0, rng.randrange(-1, 7)])
        e.gravity = f32(rng.choice([80.0, 140.0, rng.uniform(0.0, 300.0)]))
    else:
        e.lifetime = rng.choice([60, 40, 35, 31, 30, 29, 20, 16, 15, 14, 13, 12, 11, 10, 9, 5, 4, 1, 0,
                                 rng.randrange(-1, 61)])
    return e


def family_move(m, lib, rng, cases, report, kinds):
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = random_rb(rng, kind)
        objects = objects_for(rng)
        animation = rng.choice([0, 1, 1])
        keys = rng.choice([1, 7, 30])
        case = fx.Case(rng, objects, fx.rand_values(rng, 400), vc.rfloat(rng, 0.1, 400.0), animation, keys, True)
        case.attributes = wall_words(rng)
        raw, mask = fx.effect_to_bytes(e, RB_MOVE_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(fx.MODEL+0x30, struct.pack('<I', fx.MODEL+0x1000))
        for a in range(0x100):
            model.define(fx.MODEL+0x1000+16*a+8, struct.pack('<h', keys))
        quake = am.Region('quake', fx.QUAKE, am.poison(4, 0x21), bytes(4))
        regions = [record, fx.object_region(objects), model, quake,
                   am.defined_region('world', fx.WORLD, struct.pack('<i', 0), writable=False),
                   am.defined_region('terrain-wall', fx.TERRAIN_WALL, struct.pack('<65536H', *case.attributes),
                                     writable=False),
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', 1000.0), writable=False)]
        r = m.execute(fx.MOVE_EFFECT, [fx.POOL, 0], regions, case.stubs(m))
        env = with_rb_calls(case, case.env())
        env.world_time = 1000.0
        supported = lib.mu_sfx_effect_move(C.byref(e), C.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = fx.compare_effect(e, out, record.defined, RB_MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = fx.compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and client_keys(case) != case.c_keys:
                mismatch = ('effect keys', client_keys(case), case.c_keys)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None and case.c_quake is not None:
                q = struct.unpack('<f', r['regions']['quake'])[0]
                if not fx.same(q, case.c_quake):
                    mismatch = ('quake', q, case.c_quake)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('effect_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'lifetime': e.lifetime,
                                          'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        made = {c[1] for c in case.client_calls if c[0] == 'effect'}
        tag = ('impact' if 0x46a in made or 0x465 in made or 0x462 in made else 'quake ring' if 0x468 in made
               else 'tail' if 0x46b in made else 'stones' if made else 'step')
        report.cover('effect_move', f'{kind[0]:#x}/{tag}')


def family_create(m, lib, rng, cases, report, kinds):
    fx.EFFECT_KINDS = kinds
    fx.family_effect_create(m, lib, rng, cases, report, defaultdict(int))


def family_item_init(m, lib, rng, cases, report):
    for n in range(cases):
        e = fx.random_effect(rng, (0x461, 0))
        e.type = ITEM_TYPES[n % len(ITEM_TYPES)]
        case = fx.Case(rng, [], fx.rand_values(rng), 0.0)
        clock = f32(rng.choice([0.0, 1000.0, 1999.5, 2000.0, 123456.0, rng.uniform(-5000.0, 5.0e6)]))
        raw, mask = fx.effect_to_bytes(e, ALL_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        regions = [record, am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False)]
        stubs = case.stubs(m)
        stubs[ITEM_LINKS] = lambda mm: (case.client_calls.append(('links', hex(mm.uc.reg_read(mm.x86.UC_X86_REG_ECX))))
                                        or 0)
        r = m.execute(ITEM_INIT, [fx.POOL], regions, stubs)
        env = case.env()
        env.world_time = clock
        lib.mu_sfx_item_object_init(C.byref(e), C.byref(env))
        mismatch = None
        if vc.ok(r):
            mismatch = fx.compare_effect(e, r['regions']['record'], record.defined, ALL_DEFINED)
            links = [c for c in case.client_calls if c[0] == 'links']
            if mismatch is None and links != [('links', hex(fx.POOL + 0x358))]:
                mismatch = ('links', links)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        report.add('item_init', vc.ok(r) and mismatch is None,
                   {'case': n, 'type': hex(e.type), 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('item_init', hex(e.type))


def family_weapon(m, lib, rng, cases, report):
    for n in range(cases):
        e = random_rb(rng, (0x461, 0))
        e.type = 0x461
        e.lifetime = rng.choice([20, 15, 12, 11, 11, 10, 9, rng.randrange(-1, 21)])
        e.client_hit = rng.choice([0, 0, 0, 1])
        e.skill = rng.choice([42, 42, 0x7f8, 0x7fb])
        e.alpha = f32(rng.choice([1.0, 0.5, rng.uniform(0.0, 1.0)]))
        objects = objects_for(rng)
        has_model = rng.random() < 0.85
        case = fx.Case(rng, objects, fx.rand_values(rng), 0.0, has_model=has_model)
        clock = f32(rng.uniform(0.0, 1.0e5))
        terrain = [f32(rng.uniform(0.0, 1.0)) for _ in range(3)]
        hero_byte = rng.randrange(0, 256)
        raw, mask = fx.effect_to_bytes(e, ALL_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        hero = am.Region('hero-char', HERO_CHAR, am.poison(0x40, 0x17), bytes(0x40))
        hero.define(HERO_CHAR + 0x12, bytes([hero_byte]))
        regions = [record, fx.object_region(objects), model, hero,
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', HERO_CHAR), writable=False),
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False)]
        calls = case.client_calls
        stubs = case.stubs(m)

        def color(mm):
            calls.append(('terrain_light', mm.float_argument(0), mm.float_argument(1)))
            mm.uc.mem_write(mm.argument(2), struct.pack('<3f', *terrain))   # the caller's frame
            return 0

        def pose(mm):
            a = [mm.argument(i) for i in range(8)]
            calls.append(('pose', hex(a[0]), fx.from_bits(a[1]), fx.from_bits(a[2]), a[3] & 0xffff,
                          mm.floats(a[4], 3), mm.floats(a[5], 3), a[6], a[7]))
            return 0, 0x20

        def part(mm):
            a = [mm.argument(i) for i in range(16)]
            calls.append(('part', fx.owner_of(a[0]), a[1], a[2], mm.floats(a[3], 3), fx.from_bits(a[4]), a[5],
                          a[6:16]))
            return 0
        stubs.update({TERRAIN_COLOR: color, POSE: pose, RENDER_PART: part,
                      ITEM_LINKS: lambda mm: (calls.append(('links',)) or 0)})
        r = m.execute(WEAPON_DRAW, [fx.POOL], regions, stubs)
        env = case.env()
        env.world_time = clock
        out = WeaponDraw()
        drawn = lib.mu_sfx_rageful_weapon(C.byref(e), (C.c_float*3)(*terrain), hero_byte, C.byref(env), C.byref(out))
        mismatch = None
        if vc.ok(r):
            rec = r['regions']['record']
            mismatch = fx.compare_effect(e, rec, record.defined, ALL_DEFINED)
            mine = []
            if drawn:
                mine = [('links',), ('terrain_light', out.origin[0], out.origin[1]),
                        ('pose', hex(0x06fce398), out.frame, out.prior_frame, out.prior_action, list(out.angle),
                         list(out.head_angle), 0, 0),
                        ('part', -2, out.model, 0, list(out.light), out.alpha, out.level & 0xffffffff,
                         (0, 0, 1, 1, 1, 0, 2, 0xffffffff, 0xffffffff, 0))]
            theirs = [c if c[0] != 'part' else c[:7] + (tuple(c[7]),) for c in calls
                      if c[0] in ('links', 'terrain_light', 'pose', 'part')]
            if mismatch is None:
                mismatch = fx.compare_calls(theirs, mine)
            if mismatch is None and drawn:
                mdl = r['regions']['model']
                if mdl[0xa4] != out.hero_class or struct.unpack('<H', mdl[0xa8:0xaa])[0] != out.action:
                    mismatch = ('model state', mdl[0xa4], out.hero_class)
                elif not all(fx.same(x, y) for x, y in zip(struct.unpack('<3f', mdl[0x78:0x84]), out.origin)):
                    mismatch = ('body origin',)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        report.add('weapon', vc.ok(r) and mismatch is None,
                   {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('weapon', 'drawn' if drawn else 'skipped')


CREATE_ARROWS, CREATE_ARROW, ARROW_EFFECT = 0x0158d5bd, 0x0158cf57, 0x013c0e0a
ARCHER_CHAR, ARCHER_OBJ, TARGET_OBJ, SKILL_LIST = 0x2b000000, 0x2c000000, 0x2c800000, 0x06fca278
BOWS = [0x12e6, 0x12e7, 0x12e8, 0x12ee, 0x12f0, 0x12f6, 0x12f8, 0x12fc, 0x1300, 0x1305, 0x132f, 0x12e5, 0x1400,
        -1, 0xae6]
INDICES = [0x18, 0x18, 0, 0x34, 0x1a0, 0x33, 0x1a8, 0x2e, 0x7e7, 0x7fc, 0x2d7, 0x16]
SKILLS = [0x18, 0x18, 0x7fc, 0x7ff, 0, 0x1a0]


class Archer(C.Structure):
    _fields_ = [('weapon', C.c_int16), ('hero_weapon', C.c_int32), ('is_hero', C.c_uint8), ('master_1a2', C.c_uint8),
                ('tree_value', C.c_int32), ('mastery', C.c_int32), ('special', C.c_uint8), ('key', C.c_uint16),
                ('field_364', C.c_uint16)]


class Shots(C.Structure):
    _fields_ = [('count', C.c_int), ('angle', (C.c_float*3)*8), ('last', C.c_int32*8), ('serial_steps', C.c_int),
                ('bow_sparks', C.c_int)]


class ArrowEffect(C.Structure):
    _fields_ = [('routine', C.c_int32), ('type', C.c_int32), ('subtype', C.c_int32), ('owner', C.c_int32),
                ('position', C.c_float*3), ('angle', C.c_float*3), ('info', fx.Info), ('sounds', C.c_int32*3),
                ('sound_count', C.c_int)]


def random_archer(rng):
    a = Archer()
    a.weapon = rng.choice(BOWS)
    a.hero_weapon = rng.choice([-1, 0x800, 0x808, 0x812, a.weapon - 0xae6])
    a.is_hero = rng.choice([0, 1])
    a.master_1a2 = rng.choice([0, 1])
    a.tree_value = rng.choice([0, 1, 7, rng.randrange(-5, 1000)])
    a.mastery = rng.choice([0, 0x33, 0x2d7, 0x7fe, 0x18])
    a.special = rng.choice([0, 0, 0, 1])
    a.key = rng.randrange(0, 0x10000)
    a.field_364 = rng.randrange(0, 0x10000)
    return a


def archer_regions(a, angle, position, serial, light):
    char = am.Region('char', ARCHER_CHAR, am.poison(0x4000, 0x19), bytes(0x4000))
    char.define(ARCHER_CHAR + 0x19ac, struct.pack('<h', a.weapon))
    obj = am.Region('obj', ARCHER_OBJ, am.poison(0x400, 0x1b), bytes(0x400))
    obj.define(ARCHER_OBJ + 0x164, struct.pack('<3f', *angle))
    obj.define(ARCHER_OBJ + 0x158, struct.pack('<3f', *position))
    obj.define(ARCHER_OBJ + 0xec, struct.pack('<3f', *light))
    obj.define(ARCHER_OBJ + 0x54, struct.pack('<H', a.key))
    obj.define(ARCHER_OBJ + 0x364, struct.pack('<H', a.field_364))
    hero = am.Region('hero-data', fx.HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
    hero.define(fx.HERO_DATA + 0x2dec, bytes([serial]))
    hero.define(fx.HERO_DATA + 0x1b68, struct.pack('<i', a.hero_weapon))
    return [char, obj, hero,
            am.defined_region('hero-ptr', fx.HERO_DATA_PTR, struct.pack('<I', fx.HERO_DATA), writable=False),
            am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', ARCHER_CHAR if a.is_hero else 0x2d000000),
                              writable=False),
            am.Region('skill-global', SKILL_LIST, am.poison(4, 0x2f), bytes(4))]


def family_arrows(m, lib, rng, cases, report):
    for n in range(cases):
        a = random_archer(rng)
        skill, index = rng.choice(SKILLS), rng.choice(INDICES)
        flag = rng.choice([1, 1, 0, 2])
        angle = [0.0, 0.0, f32(rng.choice([0.0, 45.0, 359.0, rng.uniform(0.0, 360.0)]))]
        serial = rng.randrange(0, 256)
        regions = archer_regions(a, angle, [1000.0, 2000.0, 100.0], serial, [1.0, 1.0, 1.0])
        calls = []

        def arrow(mm):
            args = [mm.argument(i) for i in range(7)]
            calls.append((mm.floats(ARCHER_OBJ + 0x164, 3), args[6] - (1 << 32) if args[6] & 0x80000000 else args[6],
                          args[:6]))
            return 0
        stubs = {CREATE_ARROW: arrow, 0x01094039: lambda mm: a.tree_value & 0xffffffff,
                 0x00ac3bf7: lambda mm: 0x0a000000, 0x0095f998: lambda mm: 0x0a000100,
                 0x00bb1e55: lambda mm: (a.master_1a2, 4)}
        if a.weapon == 0x12f9:
            continue
        r = m.execute(CREATE_ARROWS, [ARCHER_CHAR, ARCHER_OBJ, TARGET_OBJ, skill, flag, index], regions, stubs)
        shots = Shots()
        ang = (C.c_float*3)(*angle)
        lib.mu_sfx_create_arrows(C.byref(a), ang, skill, flag, index, C.byref(shots))
        mismatch = None
        if vc.ok(r):
            mine = [(list(shots.angle[k]), shots.last[k]) for k in range(shots.count)]
            theirs = [(c[0], c[1]) for c in calls]
            if [(list(map(f32, x)), y) for x, y in theirs] != [(list(map(f32, x)), y) for x, y in mine]:
                mismatch = ('shots', theirs, mine)
            elif any(c[2] != [ARCHER_CHAR, ARCHER_OBJ, TARGET_OBJ, skill, flag, index] for c in calls):
                mismatch = ('shot arguments', calls)
            elif r['regions']['hero-data'][0x2dec] != (serial + shots.serial_steps) & 0xff:
                mismatch = ('serial', shots.serial_steps)
            elif list(struct.unpack('<3f', r['regions']['obj'][0x164:0x170])) != [f32(v) for v in ang]:
                mismatch = ('angle restored', list(ang))
        report.add('arrows', vc.ok(r) and mismatch is None,
                   {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('arrows', f'{shots.count} shots')


def family_arrow(m, lib, rng, cases, report):
    for n in range(cases):
        a = random_archer(rng)
        skill, index = rng.choice(SKILLS), rng.choice(INDICES)
        flag = rng.choice([1, 0, 2, 1])
        last = rng.choice([0, 3, rng.randrange(-100, 100)])
        angle = [f32(rng.uniform(0.0, 360.0)) if k == 2 else 0.0 for k in range(3)]
        position = [f32(rng.uniform(100.0, 25000.0)), f32(rng.uniform(100.0, 25000.0)), f32(rng.uniform(0.0, 500.0))]
        light = [f32(rng.uniform(0.1, 1.0)) for _ in range(3)]
        regions = archer_regions(a, angle, position, 0, light)
        case = fx.Case(rng, [], [], f32(rng.uniform(0.0, 400.0)))
        calls = case.client_calls

        def effect2(mm):
            args = [mm.argument(i) for i in range(8)]
            info = bytes(mm.uc.mem_read(args[7], 0x20))
            calls.append(('arrow', args[0], args[1], mm.floats(args[2], 3), mm.floats(args[3], 3), mm.floats(args[4], 3),
                          args[5], fx.from_bits(args[6]), struct.unpack('<5H2x5i', info)))
            return 0

        def effect(mm):
            a_ = [mm.argument(i) for i in range(14)]
            calls.append(('target', a_[0], a_[4], mm.floats(a_[1], 3), mm.floats(a_[2], 3), mm.floats(a_[3], 3),
                          a_[5], fx.from_bits(a_[10]), (a_[6] & 0xffff, a_[7] & 0xffff, a_[8] & 0xffff,
                                                       a_[9] & 0xffff, a_[11] & 0xffff, 0, 0, 0, a_[12], a_[13])))
            return 0
        stubs = case.stubs(m)
        stubs.update({ARROW_EFFECT: effect2, fx.CREATE_EFFECT_WRAPPER: effect,
                      0x00ac3bf7: lambda mm: 0x0a000000, 0x0095f998: lambda mm: 0x0a000100,
                      0x00bb1c32: lambda mm: (a.mastery & 0xffffffff, 4),
                      0x00cd4ea8: lambda mm: 0x0a000200, 0x00cd60da: lambda mm: (0x0a000300, 4),
                      0x00cd6017: lambda mm: (a.special, 8),
                      0x00a6ad76: lambda mm: (calls.append(('sound2', mm.argument(0), mm.argument(1))) or 0)})
        r = m.execute(CREATE_ARROW, [ARCHER_CHAR, ARCHER_OBJ, TARGET_OBJ, skill, flag, index, last], regions, stubs)
        env = case.env()
        out = ArrowEffect()
        lib.mu_sfx_create_arrow(C.byref(a), (C.c_float*3)(*position), (C.c_float*3)(*angle), skill, flag, index, last,
                                C.byref(env), C.byref(out))
        mismatch = None
        if vc.ok(r):
            sounds = [out.sounds[k] for k in range(out.sound_count)]
            mine = [('sound', snd, fx.owner_of(ARCHER_OBJ), 0) for snd in sounds if snd in (0x55, 0x82)]
            mine += [c for c in case.c_calls if c[0] == 'height']
            owner = {0: ARCHER_OBJ, 1: ARCHER_CHAR + 0x3254, 2: TARGET_OBJ}[out.owner]
            i = out.info
            if out.routine == 0x013c0e0a:
                mine.append(('arrow', out.type, out.subtype, list(out.position), list(out.angle), light, owner, 0.0,
                             (i.key, i.skill, i.word4, i.word6, i.field8, 0, 0, 0, i.field18, i.field1c)))
            elif out.routine:
                mine.append(('target', out.type, out.subtype, list(out.position), list(out.angle), light, owner, 0.0,
                             (i.key, i.skill, i.word4, i.word6, i.field8, 0, 0, 0, i.field18, i.field1c)))
            mine += [('sound2', -snd, 1) if snd < 0 else ('sound', snd, -1, 0) for snd in sounds if snd not in (0x55, 0x82)]
            theirs = [c if c[0] != 'sound' else ('sound', c[1], c[2], c[3]) for c in calls]
            theirs = [c if c[0] not in ('arrow', 'target') else c[:6] + (c[6] if isinstance(c[6], int) else c[6],) + c[7:]
                      for c in theirs]
            mismatch = fx.compare_calls(theirs, mine)
            if mismatch is None and r['regions']['skill-global'] != struct.pack('<I', index):
                mismatch = ('skill global', r['regions']['skill-global'])
        report.add('arrow', vc.ok(r) and mismatch is None,
                   {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('arrow', hex(out.type) if out.routine else 'none')


def compare(text, data, lib, name, kinds, cases):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    m = fx.FxMachine(text, data)
    report = pt.Report()
    rng = random.Random('render-effects-004-' + name)
    if name == 'effect_create':
        family_create(m, lib, rng, cases, report, kinds)
    elif name == 'effect_move':
        family_move(m, lib, rng, cases, report, kinds)
    elif name == 'item_init':
        family_item_init(m, lib, rng, cases, report)
    elif name == 'arrows':
        family_arrows(m, lib, rng, cases, report)
    elif name == 'arrow':
        family_arrow(m, lib, rng, cases, report)
    else:
        family_weapon(m, lib, rng, cases, report)
    return {'families': report.families, 'coverage': report.coverage}


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    lib = load(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX))
    plan = [('effect_create', CREATE_KINDS, cases * len(CREATE_KINDS)), ('effect_move', MOVE_KINDS, cases * 10),
            ('item_init', None, cases), ('weapon', None, cases), ('arrows', None, cases * 2), ('arrow', None, cases * 2)]
    for name, kinds, n in plan:
        result['comparisons'][name] = compare(text, data, lib, name, kinds, n)
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects4-mutants-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                mlib = base.compile_mutant(Path(tmp), name, 'fx', old, new)
                mlib = load(Path(tmp)/(name + '.' + fx.SUFFIX))
                report = compare(text, data, mlib, family, [kind] if kind else None, max(60, cases // 5))
                f = report['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    bodies = {'rb_create': (0x013ce830, 0x013cec46), 'rb_move': (0x01450a73, 0x01452410),
              'rb_pieces_move': (0x01452410, 0x01453033), 'flash_tail_move': (0x0144e1d7, 0x0144e44c),
              'flash_tail_create': (0x013c94a8, 0x013c9647), 'wing_create': (0x013e4f55, 0x013e53ff),
              'wing_move': (0x0146b64c, 0x0146b809), 'normalize': (0x00cff0d3, 0x00cff1c9),
              'create_arrows': (0x0158d5bd, 0x0158e1aa), 'create_arrow': (0x0158cf57, 0x0158d5bd), 'item_init': (0x016da00b, 0x016daa01),
              'weapon_draw': (0x01532bd2, 0x01532f27)}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                               'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in bodies.items()}
    result['all_equal'] = all(f['cases'] == f['equal'] for r in result['comparisons'].values()
                              for f in r['families'].values())
    result['all_mutants_caught'] = all(m['caught'] > 0 for m in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=200)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
