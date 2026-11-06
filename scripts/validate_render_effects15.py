#!/usr/bin/env python3
"""RENDER-EFFECTS-015: the ground skills' rain 0x70a, its rings 0x700..0x702 and 0x707, and RenderEffects' terrain
decals of 0x70a, 0x70c and 0x45e (subtypes 3..7) against the pinned instructions.

* CreateEffect 0x013c0eaa and MoveEffect 0x0142fd09 for 0x70a/0, /1, 0x700..0x702/0, /1 and 0x707/0
  (reconstructed/combat/bow_fx.inc), through validate_render_effects7's record comparison with
  validate_render_effects11's pow. CreateEffect 0x70a's sound is compared with its call site (the return address
  of PlayBuffer 0x00a6ac96). MoveEffect 0x70a looks up its caster by key (0x0137c724, 0x0095f6db, 0x009a13f4: a
  synthetic character whose +0x23 byte is defined) and fires CreateArrow 0x0158cf57 with itself as the object; the
  stub records the arguments and the record's position, angle and light at the call (the record is restored after).
* RenderEffects 0x015181fa entered at its cases 0x70a (0x0152dc88), 0x70c (0x0152e296) and 0x45e (0x01518f49),
  left at the loop's next record: the blend wrappers and RenderTerrainAlphaBitmap 0x016cdd5f are recording stubs,
  compared in order with mu_sfx_effect_render_ops.

No client bytes or decoded data are written by this tool.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import time

import actor_machine as am
import pins
import validate_combat as vc
import validate_particles as pt
import validate_render_effects7 as re7
import validate_render_effects9 as re9
import validate_render_effects11 as re11
import validate_skill_fx as fx

ROOT = Path(__file__).resolve().parents[1]
f32 = fx.f32
KINDS = [(0x70a, 0), (0x70a, 1), (0x700, 0), (0x700, 1), (0x701, 0), (0x701, 1), (0x702, 0), (0x702, 1),
         (0x707, 0)]
RENDER_KINDS = [(0x70a, 0), (0x70a, 1), (0x70c, 0)]
CASTER_INDEX, CHAR_TABLE, CHAR_GET, CREATE_ARROW = 0x0137c724, 0x0095f6db, 0x009a13f4, 0x0158cf57
CHAR = 0x25000000          # the caster character (its +0x23 byte)
TABLE = 0x13572468         # CharactersClient (opaque to the stubs)
CASTER_SLOT = 7
RENDER_CASES = {0x70a: 0x0152dc88, 0x70c: 0x0152e296}
DECAL, BLEND_ADD, BLEND_ALPHA, BLEND_OFF = 0x016cdd5f, 0x0184aa2b, 0x0184a990, 0x0184a7f3
MOVE_DEFINED = re7.MOVE_DEFINED | {'spin', 'field_d8'}

FX_MUTANTS = [
    # (name, old, new, family) on bow_fx.inc
    ('rain_life', 'e->lifetime = 20; /* rain life */', 'e->lifetime = 21; /* rain life */', 'create'),
    ('rain_ring_lift', 'lifted(p, e->position, 300.0f);', 'lifted(p, e->position, 200.0f);', 'create'),
    ('rain_signed_zero', 'out[1] = position[1] + 0.0f;', 'out[1] = position[1];', 'create'),
    ('rain_ring_scale', 'light, 0, MU_SFX_NO_OWNER, 0xffff, 2.5f);', 'light, 0, MU_SFX_NO_OWNER, 0xffff, 2.0f);',
     'create'),
    ('rain_707_light', 'call_effect_ks(env, e, 0x707, e->position, e->angle, e->light,',
     'call_effect_ks(env, e, 0x707, e->position, e->angle, light,', 'create'),
    ('rain_stack', 'e->position[2] = e->position[2] + 100.0f;', 'e->position[2] = e->position[2] + 50.0f;', 'create'),
    ('rain_sound_site', '{0x55d, 0x013c0f19u, 0x0141953eu},', '{0x55d, 0x013c0f19u, 0x0141953fu},', 'create'),
    ('ring_life', 'e->field_70 = 25;\n        e->lifetime = 25;', 'e->field_70 = 25;\n        e->lifetime = 24;',
     'create'),
    ('ring1_start', 'e->scale = e->type == 0x701 ? 0.0f : 1.0f; /* ring 1 start */',
     'e->scale = e->type == 0x701 ? 1.0f : 1.0f; /* ring 1 start */', 'create'),
    ('rain_fade', 'e->field_d8 = (float)(10 - e->lifetime); /* rain fade */',
     'e->field_d8 = (float)(9 - e->lifetime); /* rain fade */', 'move'),
    ('rain_height', 'env_height(env, e->position[0], e->position[1]) + 500.0f; /* rain height */',
     'env_height(env, e->position[0], e->position[1]) + 400.0f; /* rain height */', 'move'),
    ('rain_spread', 'target[0] = dx * 2.0f + target[0];', 'target[0] = dx * 1.0f + target[0];', 'move'),
    ('rain_pitch', 'angle[0] = 360.0f - mu_create_angle(p[2], h, t[2], 0.0f);',
     'angle[0] = 360.0f - mu_create_angle(p[2], h, t[2], 1.0f);', 'move'),
    ('rain_count', 'if (e->lifetime > 9)                       /* subtype 1: eleven aimed shots */',
     'if (e->lifetime > 10)                       /* subtype 1: eleven aimed shots */', 'move'),
    ('rain_up_turn', 'e->angle[1] = arrow_rand_range(env, -10.0f, 10.0f);',
     'e->angle[1] = arrow_rand_range(env, -10.0f, 11.0f);', 'move'),
    ('rain_caster', 'c.range = (int16_t)e->key;', 'c.range = (uint16_t)e->key;', 'move'),
    ('ring_sink', 'e->position[2] = e->position[2] - 3.0f; /* ring sink */',
     'e->position[2] = e->position[2] - 2.0f; /* ring sink */', 'move'),
    ('ring_kill', 'if (!(0.0f < e->alpha) && !isnan(e->alpha))', 'if (!(0.0f < e->alpha))', 'move'),
    ('ring_702_rate', '(e->type == 0x702 ? F_0_1 : f32bits(0x3cf5c28fu))', '(e->type == 0x702 ? F_0_1 : F_0_1)',
     'move'),
    ('ring_pulse_shift', '(float)(int32_t)((uint32_t)e->lifetime << 1);', '(float)(int32_t)((uint32_t)e->lifetime);',
     'move'),
    ('ring_707_turn', 'e->angle[2] = e->angle[2] + 5.0f;', 'e->angle[2] = e->angle[2] + 4.0f;', 'move'),
]
SITE_MUTANTS = [
    ('site_96_other', '{0x96, 0x0142fd09u, 0x014520f4u},', '{0x96, 0x0142fd09u, 0x0148e286u},'),
    ('site_42_push', '{0x42, 0x01556c26u, 0x01579fa1u},', '{0x42, 0x01556c26u, 0x01579f9bu},'),
    ('site_55e_routine', '{0x55e, 0x0142fd09u, 0x014eca9au},', '{0x55e, 0x013c0f19u, 0x014eca9au},'),
]
# The case each sound is played in (PlayBuffer 0x00a6ac96 follows a push of the sound), and its routine. 0x40e's
# CreateEffect case runs from its jump-table entry (0x0142b5e5[0x15]) to the next case start.
PLAYBUFFER = 0x00a6ac96
SOUND_CASES = {0x582: (0x013c0f19, 0x013c3eab, 0x013c4631), 0x55d: (0x013c0f19, 0x01418f78, 0x0141955d),
               0x97: (0x0142fd09, 0x01450a73, 0x01452410), 0x96: (0x0142fd09, 0x01450a73, 0x01452410),
               0x55e: (0x0142fd09, 0x014eca00, 0x014ecb6e), 0x42: (0x01556c26, 0x01579b40, 0x0157ab78)}
RENDER_MUTANTS = [
    ('decal_ring_size', 'render_decal(out, &n, e, 0x7f87, 3.0f, light, 0.0f, 1.0f); /* rain ring */',
     'render_decal(out, &n, e, 0x7f87, 2.0f, light, 0.0f, 1.0f); /* rain ring */'),
    ('decal_rain_late', 'if (e->lifetime <= 10) {                            /* the last ten steps widen by +0xd8 */',
     'if (e->lifetime < 10) {                            /* the last ten steps widen by +0xd8 */'),
    ('decal_wave_size', 'render_decal(out, &n, e, 0x824c, d * F_0_2 + 2.0f, light, 0.0f, 1.0f);',
     'render_decal(out, &n, e, 0x824c, d * F_0_2 + 1.0f, light, 0.0f, 1.0f);'),
    ('decal_marks', 'scaled3(light, 0.75f, 0.75f, F_0_8, e->alpha);', 'scaled3(light, 0.75f, 0.75f, 0.75f, e->alpha);'),
    ('decal_crater_alpha', 'render_decal(out, &n, e, 0x7fe9, 2.25f, e->light, e->angle[2], e->light[0]);',
     'render_decal(out, &n, e, 0x7fe9, 2.25f, e->light, e->angle[2], 1.0f);'),
    ('decal_flash_life', 'if (e->lifetime > 30) {                             /* landing flash */',
     'if (e->lifetime >= 30) {                             /* landing flash */'),
    ('decal_flash_turn', 'render_decal(out, &n, e, 0x8013, e->scale * 3.5f, light, e->angle[2], 1.0f);',
     'render_decal(out, &n, e, 0x8013, e->scale * 3.5f, light, 0.0f, 1.0f);'),
    ('decal_crater_blend', 'render_op(out, &n, MU_SFX_RENDER_BLEND_ALPHA, 1);',
     'render_op(out, &n, MU_SFX_RENDER_BLEND_ALPHA, 0);'),
    ('decal_45e_range', 'if (e->type == 0x45e && e->subtype >= 3 && e->subtype <= 7) {',
     'if (e->type == 0x45e && e->subtype >= 3 && e->subtype <= 6) {'),
    ('decal_45e_turn', 'render_decal(out, &n, e, 0x8002, 2.0f, light, world_time, 1.0f);',
     'render_decal(out, &n, e, 0x8002, 2.0f, light, 0.0f, 1.0f);'),
]


class RenderOp(C.Structure):
    _fields_ = [('routine', C.c_int32), ('argument', C.c_int32), ('texture', C.c_int32), ('x', C.c_float),
                ('y', C.c_float), ('size_x', C.c_float), ('size_y', C.c_float), ('light', C.c_float*3),
                ('rotation', C.c_float), ('alpha', C.c_float), ('height', C.c_float), ('follow', C.c_int32),
                ('flip', C.c_int32)]


def bind(lib):
    lib.mu_sfx_effect_render_ops.argtypes = [C.POINTER(fx.Effect), C.c_float, C.POINTER(RenderOp)]
    lib.mu_sfx_effect_render_ops.restype = C.c_int
    lib.mu_sfx_sound_site.argtypes = [C.c_int32, C.POINTER(C.c_uint32)]
    lib.mu_sfx_sound_site.restype = C.c_uint32
    return re11.bind_render(lib)


class Case(re11.PowCase):
    """re11's case plus the caster lookup, CreateArrow and PlayBuffer's call site on both sides."""

    def __init__(self, *a, caster=1, flag23=0, **kw):
        super().__init__(*a, **kw)
        self.caster, self.flag23 = caster, flag23

    def stubs(self, m):
        s = super().stubs(m)

        def sound(mm):
            site = mm.read32(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP)) - 5
            self.client_calls.append(('sound', mm.argument(0), fx.owner_of(mm.argument(1)), mm.argument(2), site))
            return 0

        def caster_index(mm):
            self.client_calls.append(('caster', re7.sx(mm.argument(0))))
            return CASTER_SLOT

        def char_get(mm):
            ok = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX) == TABLE and mm.argument(0) == CASTER_SLOT
            return (CHAR if self.caster and ok else 0), 4

        def create_arrow(mm):
            a = [mm.argument(i) for i in range(7)]
            o = a[1]
            self.client_calls.append(('arrow', a[0] == CHAR, fx.owner_of(o), a[2], a[3], a[4], a[5], a[6],
                                      mm.floats(o + 0x158, 3), mm.floats(o + 0x164, 3), mm.floats(o + 0xec, 3)))
            return 0
        s.update({fx.PLAY_BUFFER: sound, CASTER_INDEX: caster_index, CHAR_TABLE: lambda mm: TABLE,
                  CHAR_GET: char_get, CREATE_ARROW: create_arrow})
        return s

    def env(self, *args, **kwargs):
        env = super().env(*args, **kwargs)
        inner = self._call7   # validate_render_effects7's recorder (this env's call before the one below)

        def call(ctx, cp, ep):
            c = cp.contents
            if c.routine == fx.PLAY_BUFFER:
                self.c_calls.append(('sound', c.type, c.owner, 0, c.arg8))
                return 0
            if c.routine == CASTER_INDEX:
                self.c_calls.append(('caster', c.range))
                return 1 if self.caster and self.flag23 == 0 else 0
            if c.routine == CREATE_ARROW:
                self.c_calls.append(('arrow', True, c.owner, 0, c.type, c.subtype, c.range, 0, list(c.position),
                                     list(c.angle), list(c.light)))
                return 0
            return inner(ctx, cp, ep)
        self._call15 = fx.CALL_FN(call)
        env.call = self._call15
        return env


def character_region(flag23):
    r = am.Region('character', CHAR, am.poison(0x100, 0x5a), bytes(0x100))
    r.define(CHAR + 0x23, bytes([flag23]))
    return r


def random_record(rng, kind):
    e = re11.random_effect(rng, kind)
    e.type, e.subtype = kind
    e.key = rng.choice([0, 1, 0x7fff, 0x8000, 0xffff, rng.randrange(0, 0x10000)])
    if kind[0] == 0x70a:
        e.lifetime = rng.choice([20, 19, 17, 16, 15, 14, 11, 10, 9, 5, 1, 0, -1, rng.randrange(-2, 22)])
        e.field_70 = rng.choice([20, 20, 20, 7, rng.randrange(1, 40)])
    else:
        e.lifetime = rng.choice([25, 24, 20, 13, 12, 2, 1, 0, rng.randrange(-2, 27), 0x40000001])
        e.field_70 = rng.choice([25, 25, 20, 9, rng.randrange(1, 40)])
        e.alpha = f32(rng.choice([1.0, 0.05, 0.0, -0.0, -0.02, float('nan'), rng.uniform(-0.1, 1.0)]))
        e.scale_arg = f32(rng.choice([1.8, 2.5, 0.0, rng.uniform(0.0, 3.0)]))
    return e


def family_create(m, lib, rng, cases, report):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        objects = [fx.random_object(rng) for _ in range(2)]
        owner = rng.choice([-1, 0, 1])
        pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
        if n // len(KINDS) % 4 == 1:
            pos[n // len(KINDS) % 8 // 4] = -0.0   # every fourth round: a signed zero in x or y (the rings' lift)
        angle = [vc.rfloat(rng, 0.1, 360.0) if k == 2 or rng.random() < 0.3 else 0.0 for k in range(3)]
        light = [vc.rfloat(rng, 0.1, 1.5) for _ in range(3)]
        scale = f32(rng.choice([0.0, 1.0, 1.0, 1.8, -1.0, vc.rfloat(rng, 0.2, 3.0)]))
        info = re7.random_info(rng)
        case = Case(rng, objects, fx.rand_values(rng), vc.rfloat(rng, 0.1, 400.0))
        inputs = am.defined_region('inputs', fx.INPUTS, struct.pack('<9f', *pos, *angle, *light) + fx.info_bytes(info),
                                   writable=True)
        record = am.Region('record', fx.POOL, am.poison(0x3d8, 0x31), bytes(0x3d8))
        record.define(fx.POOL, b'\0')
        hero = am.Region('hero-data', fx.HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
        regions = [inputs, record, fx.object_region(objects), hero,
                   am.defined_region('hero-ptr', fx.HERO_DATA_PTR, struct.pack('<I', fx.HERO_DATA), writable=False),
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', 0x5000000), writable=False)]
        r = m.execute(fx.CREATE_EFFECT, [kind[0], kind[1], fx.INPUTS, fx.INPUTS + 12, fx.INPUTS + 24,
                                         fx.object_address(owner), fx.bits(scale), fx.INPUTS + 36],
                      regions, case.stubs(m), ecx=fx.POOL, cleanup=0x20)
        e = fx.Effect()
        F3 = C.c_float * 3
        env = case.env()
        source_light = F3(*light)
        supported = lib.mu_sfx_effect_create(C.byref(e), kind[0], kind[1], F3(*pos), F3(*angle), source_light, owner,
                                             scale, C.byref(info), C.byref(env))
        mismatch = None
        if vc.ok(r):
            raw = r['regions']['record']
            mismatch = fx.compare_effect(e, raw, record.defined)
            if mismatch is None and struct.unpack('<I', raw[0x34c:0x350])[0] != fx.object_address(owner):
                mismatch = ('owner',)
            if mismatch is None:   # +0x38: the common part's 0, 1 for 0x70a (0x01418f7b); not modelled in C
                want = 1 if kind[0] == 0x70a else 0
                if raw[0x38] != want:
                    mismatch = ('+0x38', raw[0x38], want)
            if mismatch is None:
                mismatch = re7.compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = bool(supported) and vc.ok(r) and mismatch is None
        report.add('fx_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                        'stopped': r['stopped'], 'error': r['error']})
        report.cover('fx_create', f'{kind[0]:#x}/{kind[1]}/' +
                     '+'.join(sorted({c[0] for c in case.client_calls if c[0] != 'init'})))


def family_move(m, lib, rng, cases, report):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        e = random_record(rng, kind)
        objects = [fx.random_object(rng) for _ in range(2)]
        e.owner = rng.choice([-1, 0, 1])
        caster = rng.choice([1, 1, 1, 0])
        flag23 = rng.choice([0, 0, 0, 1, 0x80])
        animation = rng.choice([0, 1, 1])
        keys = rng.choice([1, 7, 10, 30])
        has_model = rng.random() < 0.85
        case = Case(rng, objects, fx.rand_values(rng, 120), vc.rfloat(rng, 0.1, 600.0), animation, keys, has_model,
                    caster=caster, flag23=flag23)
        raw, mask = fx.effect_to_bytes(e, MOVE_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(fx.MODEL + 0x30, struct.pack('<I', fx.MODEL + 0x1000))
        for a in range(0x100):
            model.define(fx.MODEL + 0x1000 + 16 * a + 8, struct.pack('<h', keys))
        quake = am.Region('quake', fx.QUAKE, am.poison(4, 0x21), bytes(4))
        regions = [record, fx.object_region(objects), model, quake, character_region(flag23),
                   am.defined_region('world', fx.WORLD, struct.pack('<i', 0), writable=False),
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', 1000.0), writable=False),
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', 0x5000000), writable=False)]
        r = m.execute(fx.MOVE_EFFECT, [fx.POOL, 0], regions, case.stubs(m))
        env = case.env()
        env.world_time = 1000.0
        supported = lib.mu_sfx_effect_move(C.byref(e), C.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = fx.compare_effect(e, out, record.defined, MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = re7.compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = bool(supported) and vc.ok(r) and mismatch is None
        report.add('fx_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'lifetime': e.lifetime,
                                      'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        made = sorted({c[0] for c in case.client_calls if c[0] in ('arrow', 'caster', 'kill', 'height')})
        report.cover('fx_move', f'{kind[0]:#x}/{kind[1]}/' + ('+'.join(made) or 'none'))


def render_stubs(record):
    def decal(mm):
        a = [mm.argument(i) for i in range(11)]
        record.append(('decal', a[0], fx.from_bits(a[1]), fx.from_bits(a[2]), fx.from_bits(a[3]), fx.from_bits(a[4]),
                       mm.floats(a[5], 3), fx.from_bits(a[6]), fx.from_bits(a[7]), fx.from_bits(a[8]), a[9], a[10]))
        return 0

    def blend(name, argument=False):
        def stub(mm):
            record.append((name, mm.argument(0) if argument else 0))
            return 0
        return stub
    return {DECAL: decal, BLEND_ADD: blend('add'), BLEND_ALPHA: blend('alpha', True), BLEND_OFF: blend('off')}


def ops_calls(ops, count):
    names = {BLEND_ADD: 'add', BLEND_ALPHA: 'alpha', BLEND_OFF: 'off'}
    out = []
    for op in ops[:count]:
        if op.routine == DECAL:
            out.append(('decal', op.texture, op.x, op.y, op.size_x, op.size_y, list(op.light), op.rotation, op.alpha,
                        op.height, op.follow, op.flip))
        else:
            out.append((names.get(op.routine, op.routine), op.argument))
    return out


def same_calls(a, b):
    if len(a) != len(b):
        return ('count', a[:4], b[:4])
    for x, y in zip(a, b):
        if x[0] != y[0] or not vc._same_call(list(x[1:]), list(y[1:])):
            return ('value', x, y)
    return None


def family_render(m, lib, rng, cases, report):
    """RenderEffects entered at the case of 0x70a / 0x70c with the record at [ebp-0x10]."""
    for n in range(cases):
        kind = RENDER_KINDS[n % len(RENDER_KINDS)]
        e = random_record(rng, kind)
        e.type, e.subtype = kind
        e.lifetime = rng.choice([50, 40, 31, 30, 29, 25, 20, 11, 10, 9, 1, 0, -3, rng.randrange(-2, 60)])
        e.field_d8 = f32(rng.choice([0.0, 1.0, 9.0, 10.0, rng.uniform(0.0, 11.0)]))
        e.alpha = f32(rng.choice([1.0, 0.0, 0.5, rng.uniform(0.0, 1.0)]))
        e.scale = f32(rng.choice([0.0, 0.05, 1.0, 2.5, rng.uniform(0.0, 3.0)]))
        for k in range(3):
            e.light[k] = f32(rng.choice([1.0, 0.96, 0.0, -0.04, rng.uniform(-0.2, 1.0)]))
        e.angle[2] = f32(rng.choice([0.0, 90.0, rng.uniform(0.0, 360.0)]))
        record = []
        stubs = render_stubs(record)
        stubs[re11.RENDER_NEXT] = fx.jump_stub(re11.RENDER_END)
        raw, mask = fx.effect_to_bytes(e, MOVE_DEFINED | {'velocity'})
        region = am.Region('record', fx.POOL, raw, mask)
        clock = f32(rng.uniform(0.0, 1.0e5))
        regions = [region, am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False)]
        r = m.execute(RENDER_CASES[kind[0]], [0], regions, stubs,
                      frame=pt.mid_frame(re11.RENDER_FRAME, {-0x10: fx.POOL}), cleanup=4)
        ops = (RenderOp * 12)()
        count = lib.mu_sfx_effect_render_ops(C.byref(e), clock, ops)
        mismatch = same_calls(record, ops_calls(ops, count)) if vc.ok(r) else None
        equal = vc.ok(r) and mismatch is None
        report.add('render_decals', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'lifetime': e.lifetime,
                                            'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('render_decals', f'{kind[0]:#x}/' + ('young' if e.lifetime > 30 else 'late' if e.lifetime <= 10
                                                          else 'mid') + f'/{sum(x[0] == "decal" for x in record)}')


def family_render45e(m, lib, rng, cases, report):
    """validate_render_effects11's entry at RenderEffects' case 0x45e (0x01518f49), with the decal's arguments
    recorded in full and compared with mu_sfx_effect_render_ops (re11 compares the rest of the case)."""
    for n in range(cases):
        sub = rng.choice([0, 2, 3, 4, 5, 6, 7, 8, 9, 0xb, 0x63, 3, 7])
        e = re7.random_arrow(rng, (0x45e, sub))
        e.type, e.subtype = 0x45e, sub
        e.lifetime = rng.choice([e.lifetime, 0x45, 0x46, 0x44, 100])
        e.velocity = f32(rng.choice([0.3, 0.0, 0.25]))
        objects = [fx.random_object(rng) for _ in range(2)]
        case = re9.Case(rng, objects, fx.rand_values(rng, 40), vc.rfloat(rng, 0.1, 400.0), 1, 10, True)
        stubs = case.stubs(m)
        record = []
        rs = render_stubs(record)
        stubs.update({re11.RENDER_OBJECT: lambda mm: 0, DECAL: rs[DECAL], pt.STATE_ADD: rs[BLEND_ADD],
                      re11.RENDER_NEXT: fx.jump_stub(re11.RENDER_END)})
        raw, mask = fx.effect_to_bytes(e, re7.MOVE_DEFINED | {'velocity'})
        region = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        clock = f32(rng.choice([0.0, 1000.0, rng.uniform(0.0, 1.0e5)]))
        regions = [region, fx.object_region(objects), model,
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False)]
        r = m.execute(re11.RENDER_45E, [0], regions, stubs, frame=pt.mid_frame(re11.RENDER_FRAME, {-0x10: fx.POOL}),
                      cleanup=4)
        ops = (RenderOp * 12)()
        count = lib.mu_sfx_effect_render_ops(C.byref(e), clock, ops)
        mismatch = same_calls(record, ops_calls(ops, count)) if vc.ok(r) else None
        equal = vc.ok(r) and mismatch is None
        report.add('render_45e_decal', equal, {'case': n, 'subtype': sub, 'mismatch': mismatch,
                                               'stopped': r['stopped'], 'error': r['error']})
        report.cover('render_45e_decal', f'sub {sub:#x}/{len(record)}')


def family_sound_sites(text, lib, report):
    """mu_sfx_sound_site against the pinned text: the site is a CALL to PlayBuffer right after a push of the sound,
    inside the case that plays it, and the routine is that case's routine; any other sound has no site."""
    def u8(a):
        return text[a - 0x00401000]

    def u32(a):
        return struct.unpack('<I', text[a - 0x00401000:a - 0x00401000 + 4])[0]
    for sound in list(SOUND_CASES) + [0x55f, 0x41, 0x583]:
        routine = C.c_uint32(0)
        site = lib.mu_sfx_sound_site(sound, C.byref(routine))
        mismatch = None
        if sound not in SOUND_CASES:
            if site or routine.value:
                mismatch = ('site for an unplayed sound', hex(site))
        else:
            want_routine, lo, hi = SOUND_CASES[sound]
            pushed = (u8(site - 5) == 0x68 and u32(site - 4) == sound) or \
                     (sound < 0x80 and u8(site - 2) == 0x6a and u8(site - 1) == sound)
            if not (lo <= site < hi):
                mismatch = ('outside the case', hex(site))
            elif u8(site) != 0xe8 or (site + 5 + struct.unpack('<i', text[site - 0x00400fff:site - 0x00400ffb])[0]) \
                    & 0xffffffff != PLAYBUFFER:
                mismatch = ('not a PlayBuffer call', hex(site))
            elif not pushed:
                mismatch = ('sound not pushed', hex(site))
            elif routine.value != want_routine:
                mismatch = ('routine', hex(routine.value))
        report.add('sound_sites', mismatch is None, {'sound': hex(sound), 'site': hex(site), 'mismatch': mismatch})
        report.cover('sound_sites', hex(sound))


def compile_mutant(directory, name, old, new):
    base = ROOT/'reconstructed'/'combat'
    if (base/'bow_fx.inc').read_text().count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    work = Path(directory)/name
    work.mkdir()
    for f in ('skill_fx.c', 'pet_fx.inc', 'arrow_fx.inc'):
        shutil.copy(base/f, work/f)
    (work/'bow_fx.inc').write_text((base/'bow_fx.inc').read_text().replace(old, new))
    others = ['combat.c', '../objects/world_warp.c', '../joints/joints.c', '../record-math/record_math.c',
              '../movement/client_movement.c']
    out = Path(directory)/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(base), str(work/'skill_fx.c'), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return bind(fx.load_library(out))


def check_anchors():
    """Every mutant anchor must occur exactly once in bow_fx.inc."""
    text = (ROOT/'reconstructed'/'combat'/'bow_fx.inc').read_text()
    bad = [(m[0], text.count(m[1])) for m in FX_MUTANTS + SITE_MUTANTS + RENDER_MUTANTS if text.count(m[1]) != 1]
    return bad


FAMILIES = [('fx_create', family_create), ('fx_move', family_move), ('render_decals', family_render),
            ('render_45e_decal', family_render45e)]


def run_families(m, lib, cases, report, seed='effects15-', only=None):
    for name, family in FAMILIES:
        if only and name != only:
            continue
        n = cases * (len(KINDS) if name.startswith('fx_') else len(RENDER_KINDS) if name == 'render_decals' else 4)
        family(m, lib, random.Random(seed + name), n, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=300)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    bad = check_anchors()
    if bad:
        raise SystemExit(f'mutant anchors not unique: {bad}')
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    start = time.monotonic()
    m = re9.machine(text, data)
    lib = bind(fx.load_library(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}'))
    report = pt.Report()
    run_families(m, lib, a.cases, report)
    family_sound_sites(text, lib, report)
    equal = all(f['equal'] == f['cases'] for f in report.families.values())
    print(json.dumps(dict(instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                          families={k: (v['cases'], v['equal']) for k, v in report.families.items()})), flush=True)
    mutants = []
    if a.mutations and equal:
        with tempfile.TemporaryDirectory(prefix='effects15-mutants-') as tmp:
            for name, old, new, family in FX_MUTANTS:
                ml = compile_mutant(tmp, name, old, new)
                rr = pt.Report()
                run_families(m, ml, 15, rr, seed='effects15-mutant-', only='fx_' + family)
                f = rr.families['fx_' + family]
                mutants.append(dict(name=name, family='fx_' + family, cases=f['cases'], detected=f['cases']-f['equal'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
            for name, old, new in SITE_MUTANTS:
                rr = pt.Report()
                family_sound_sites(text, compile_mutant(tmp, name, old, new), rr)
                f = rr.families['sound_sites']
                mutants.append(dict(name=name, family='sound_sites', cases=f['cases'], detected=f['cases']-f['equal'],
                                    stopped=0))
                print('mutant', json.dumps(mutants[-1]), flush=True)
            for name, old, new in RENDER_MUTANTS:
                ml = compile_mutant(tmp, name, old, new)
                rr = pt.Report()
                family = 'render_45e_decal' if '45e' in name else 'render_decals'
                run_families(m, ml, 40 if family == 'render_decals' else 30, rr, seed='effects15-mutant-', only=family)
                f = rr.families[family]
                mutants.append(dict(name=name, family=family, cases=f['cases'], detected=f['cases']-f['equal'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
    result = dict(families=report.families, coverage=report.coverage,
                  instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                  mutants=mutants, all_mutants_caught=all(x['detected'] and not x['stopped'] for x in mutants),
                  nan_pairs=vc.NAN_COUNT[0], seconds=round(time.monotonic()-start, 3), text_sha256=am.TEXT_SHA256,
                  data_sha256=am.DATA_SHA256)
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ('families', 'coverage')}, indent=1))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
