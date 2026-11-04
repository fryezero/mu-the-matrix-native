#!/usr/bin/env python3
"""RENDER-EFFECTS-010 original-instruction families and compiled production mutants.

* The pets' particle kinds (the visuals 0x00eaeaf8): Clud64 0x7ffd/0xb, firehik03 0x8085/1, Impack01 0x7efa/1 and
  firehik_mono 0x8086/4, 0x8087/8, 0x8089/5 (owner = the pet), with 0x7efa/2 that shares Impack01's body.
* Arrows 0x615 / 0x617's particle kinds: 0x8081..0x8083/8, 0x85fb/2 and 0x8450/4.
* The other bows' most requested kinds: 0x7fcd/1, 0x7f73..0x7f75/0, 0x7f5a/0x86, 0x810a/0x24 and 0xe, 0x7f26/0x1e.
  Both through validate_particles' create (CreateParticle 0x015ae7b0), move (MoveParticles 0x01616c80) and render
  (RenderParticles 0x0159123f) families against reconstructed/particles (pet_kinds.inc, arrow_kinds.inc,
  world_owned_fx.inc).
* The render-registry functors of 0x613..0x617 (0x00a4269f, 0x00a42984, 0x00a42b8c, 0x00a42f55, 0x00a43160): the
  animation tick 0x012b4dd3, SetAction 0x012affa4 and RenderMeshDefault 0x00966e4a are recording stubs (the model
  colour +0x54 is read at each mesh call); the vec3 helpers run as client code. Compared with
  mu_sfx_arrow_render_passes (reconstructed/combat/arrow_fx.inc).

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import ctypes as C
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
import validate_combat as vc
import validate_particles as pt
import validate_skill_fx as fx
import validate_render_effects7 as re7
import validate_render_effects9 as re9
import validate_render_effects as base

ROOT = Path(__file__).resolve().parents[1]
f32 = fx.f32
PET_KINDS = [(0x7ffd, 0xb), (0x8085, 1), (0x7efa, 1), (0x7efa, 2), (0x8086, 4), (0x8087, 8), (0x8089, 5)]
ARROW_KINDS = [(0x8081, 8), (0x8082, 8), (0x8083, 8), (0x85fb, 2), (0x8450, 4)]
# the most requested kinds of the other bows' arrows (drop01 0x7fcd/1: ArrowWing/ArrowBomb; flower1..3: ArrowNature;
# smoke01/0x86 and 0x810a/0x24: 0x616; 0x810a/0xe: 0x60a/0x60e; Spark03/0x1e: 0x525)
BOW_KINDS = [(0x7fcd, 1), (0x7f73, 0), (0x7f74, 0), (0x7f75, 0), (0x7f5a, 0x86), (0x810a, 0x24), (0x810a, 0xe),
             (0x7f26, 0x1e)]
OWNED = {(0x8086, 4), (0x8087, 8), (0x8089, 5)}   # their create and move read the owner OBJECT's +0x158
FUNCTORS = {0x613: 0x00a4269f, 0x614: 0x00a42984, 0x615: 0x00a42b8c, 0x616: 0x00a42f55, 0x617: 0x00a43160}
TICK, SET_ACTION, RENDER_MESH = 0x012b4dd3, 0x012affa4, 0x00966e4a
TIME = 0x06fce370

PT_MUTANTS = [
    # (name, file, old, new, family, kind) on reconstructed/particles
    ('cloud_tex', 'pet_kinds.inc', 'if (mu_pt_rand(h) % 4 != 0)\n            p->tex_type', 'if (mu_pt_rand(h) % 3 != 0)\n            p->tex_type',
     'create', (0x7ffd, 0xb)),
    ('cloud_sink', 'pet_kinds.inc', 'p->gravity = p->gravity - 0.01f;', 'p->gravity = p->gravity - 0.02f;', 'move', (0x7ffd, 0xb)),
    ('cloud_blend', 'particles.c', 'if (p->type == 0x7ffd && p->subtype == 0xb)\n        state(out, MU_PT_STATE_SUBTRACT',
     'if (p->type == 0x7ffd && p->subtype == 0xc)\n        state(out, MU_PT_STATE_SUBTRACT', 'render', (0x7ffd, 0xb)),
    ('flame_life', 'pet_kinds.inc', 'p->lifetime = mu_pt_rand(h) % 5 + 34;', 'p->lifetime = mu_pt_rand(h) % 5 + 33;', 'create', (0x8085, 1)),
    ('flame_fade', 'pet_kinds.inc', 'pet_flame_fade(p, h, 15, 0.2f);', 'pet_flame_fade(p, h, 14, 0.2f);', 'move', (0x8085, 1)),
    ('flame_out', 'pet_kinds.inc', 'pet_flame_fade(p, h, 15, 0.2f);', 'pet_flame_fade(p, h, 15, 0.25f);', 'move', (0x8085, 1)),
    ('flame_spin', 'pet_kinds.inc', 'p->rotation = p->rotation + 3.0f;', 'p->rotation = p->rotation + 4.0f;', 'move', (0x8085, 1)),
    ('puff_start', 'world_owned_fx.inc', 'p->start[0] = p->subtype == 2 ? scale : p->scale;', 'p->start[0] = scale;',
     'create', (0x7efa, 1)),
    ('puff_sine', 'world_owned_fx.inc', 'if (p->subtype == 2)\n            p->scale = p->scale * p->start[0];',
     'if (p->subtype != 3)\n            p->scale = p->scale * p->start[0];', 'move', (0x7efa, 1)),
    ('puff_draw', 'world_owned_fx.inc', '(p->subtype == 1 || p->subtype == 2));', '(p->subtype == 2));', 'render', (0x7efa, 1)),
    ('mono_owner', 'pet_kinds.inc', 'copy3(p->start, o);                        /* the owner',
     'copy3(p->start, p->owner_position);                        /* the owner', 'create', (0x8086, 4)),
    ('mono_below', 'pet_kinds.inc', 'p->type == 0x8089 ? 4 : 5', 'p->type == 0x8089 ? 5 : 5', 'move', (0x8089, 5)),
    ('mono_push', 'pet_kinds.inc', 'd[k] = 8.0f * d[k];', 'd[k] = 7.0f * d[k];', 'move', (0x8087, 8)),
    ('mono_follow', 'pet_kinds.inc', 'p->position[k] = p->position[k] - p->start[k];', 'p->position[k] = p->position[k] - o[k];',
     'move', (0x8086, 4)),
    ('mono_grow', 'pet_kinds.inc', 'p->scale = (float)(10 - p->lifetime) * 0.02f + p->scale;',
     'p->scale = (float)(9 - p->lifetime) * 0.02f + p->scale;', 'move', (0x8087, 8)),
    ('spark_life', 'arrow_kinds.inc', 'p->initial_lifetime = 5;\n        p->lifetime = 5;', 'p->initial_lifetime = 6;\n        p->lifetime = 5;',
     'create', (0x8082, 8)),
    ('spark_shrink', 'arrow_kinds.inc', 'p->scale = p->scale - 0.018f;', 'p->scale = p->scale - 0.02f;', 'move', (0x8081, 8)),
    ('trail_speed', 'arrow_kinds.inc', 'rand_range(h, 7.0f, 10.0f, 10)', 'rand_range(h, 7.0f, 11.0f, 10)', 'create', (0x85fb, 2)),
    ('trail_angle', 'arrow_kinds.inc', 'p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;', 'p->angle[0] = p->angle[1] = 0.0f;',
     'create', (0x8450, 4)),
    ('trail_grow', 'arrow_kinds.inc', '(p->type == 0x85fb ? 0.4f : 0.2f)', '(p->type == 0x85fb ? 0.4f : 0.25f)', 'move', (0x8450, 4)),
    ('trail_blend', 'arrow_kinds.inc', 'if (p->type == 0x8450)\n        state(out', 'if (p->type == 0x85fb)\n        state(out',
     'render', (0x8450, 4)),
    ('drop_rise', 'particles.c', '(float)(mu_pt_rand(h) % 20 + 10) * 0.3f * p->scale', '(float)(mu_pt_rand(h) % 20 + 10) * 0.25f * p->scale',
     'move', (0x7fcd, 1)),
    ('leaf_fall', 'arrow_kinds.inc', 'p->velocity[2] = (float)(mu_pt_rand(h) % 32 - 32) * 0.1f;',
     'p->velocity[2] = (float)(mu_pt_rand(h) % 32 - 16) * 0.1f;', 'create', (0x7f74, 0)),
    ('leaf_rest', 'arrow_kinds.inc', 'p->frame = 1;\n        }', 'p->frame = 2;\n        }', 'move', (0x7f73, 0)),
    ('smoke_grow', 'bow_kinds.inc', 'p->scale = p->scale + 0.04f;', 'p->scale = p->scale + 0.05f;', 'move', (0x7f5a, 0x86)),
    ('star_back', 'bow_kinds.inc', 'p->angle[2] = p->angle[2] - 180.0f;', 'p->angle[2] = p->angle[2] - 90.0f;', 'create', (0x810a, 0x24)),
    ('star_size', 'bow_kinds.inc', 'p->scale = (float)p->lifetime * p->initial_scale / (float)p->initial_lifetime;',
     'p->scale = (float)p->lifetime * p->initial_scale / (float)(p->initial_lifetime + 1);', 'move', (0x810a, 0x24)),
    ('glint_spin', 'bow_kinds.inc', 'p->rotation = p->rotation - 10.0f;', 'p->rotation = p->rotation - 12.0f;', 'move', (0x810a, 0xe)),
    ('glint_alpha', 'bow_kinds.inc', 's->light[k] = p->light[k] * p->alpha;\n}', 's->light[k] = p->light[k];\n}', 'render', (0x810a, 0xe)),
    ('spark_wander', 'bow_kinds.inc', 'if (p->lifetime <= 45) {', 'if (p->lifetime < 45) {', 'move', (0x7f26, 0x1e)),
    ('spark_age', 'bow_kinds.inc', 'p->lifetime = p->lifetime - 1;\n        if (p->lifetime <= 0)',
     'p->lifetime = p->lifetime - 0;\n        if (p->lifetime <= 0)', 'move', (0x7f26, 0x1e)),
    ('arrow_alpha', 'arrow_kinds.inc', 's->light[k] = p->light[k] * p->alpha;', 's->light[k] = p->light[k];', 'render', (0x8083, 8)),
]
FN_MUTANTS = [
    # (name, old, new, type) on reconstructed/combat/arrow_fx.inc
    ('f613_tint', '{2, 2, 2, 0.4f, 0.5f, 1.0f},\n        {3, 2, 3, 0.4f, 0.5f, 1.0f}};',
     '{2, 2, 2, 0.4f, 0.5f, 1.0f},\n        {3, 2, 3, 0.4f, 0.6f, 1.0f}};', 0x613),
    ('f614_select', '{1, 2, -1, 1.0f, 1.0f, 1.0f}', '{1, 2, 1, 1.0f, 1.0f, 1.0f}', 0x614),
    ('f615_chrome', '{1, 0x44, 1, 0.5f, 0.4f, 1.0f}', '{1, 0x42, 1, 0.5f, 0.4f, 1.0f}', 0x615),
    ('f615_blend_mesh', '{0, 0x42, MU_SFX_PASS_BLEND_MESH, 1.0f, 1.0f, 1.0f}, {2, 0x42, 2',
     '{0, 0x42, 0, 1.0f, 1.0f, 1.0f}, {2, 0x42, 2', 0x615),
    ('f615_sheet', 'trunc_i32(world_time) % (6 * 25) / 25', 'trunc_i32(world_time) % (6 * 25) / 30', 0x615),
    ('f615_bitmap', 'out[3].texture = 0x8551;', 'out[3].texture = 0x8550;', 0x615),
    ('f616_order', '{0, 0x42, 0, 1.0f, 1.0f, 1.0f}, {2, 0x42, 2, 1.0f, 1.0f, 1.0f}, {1, 0x42, 1, 0.3f, 0.7f, 1.0f}};',
     '{0, 0x42, 0, 1.0f, 1.0f, 1.0f}, {1, 0x42, 1, 0.3f, 0.7f, 1.0f}, {2, 0x42, 2, 1.0f, 1.0f, 1.0f}};', 0x616),
    ('f617_chrome', '{2, 6, 2, 0.6f, 0.6f, 0.8f}', '{2, 2, 2, 0.6f, 0.6f, 0.8f}', 0x617),
    ('f617_tint', '{4, 0x42, 4, 0.7f, 0.2f, 1.0f}', '{4, 0x42, 4, 0.7f, 0.3f, 1.0f}', 0x617),
    ('f617_alpha', 'p->alpha = e->alpha;                       /* +0xdc */', 'p->alpha = 1.0f;                       /* +0xdc */', 0x617),
    ('f614_speed', 'e->type == 0x614 ? f32bits(0x3b449ba6u)', 'e->type == 0x613 ? f32bits(0x3b449ba6u)', 0x614),
]

PATH_MUTANTS = [
    # (name, file: arrow_fx.inc or skill_fx.c, old, new, family, arrow type)
    ('arc_life', 'arrow', 'e->lifetime = 40;\n        e->direction[1] = -(', 'e->lifetime = 30;\n        e->direction[1] = -(',
     'arc_create', 0x60a),
    ('arc_pitch', 'arrow', 'e->angle[0] = -((float)smod(env_rand(env), 60) + 32.0f);',
     'e->angle[0] = -((float)smod(env_rand(env), 60) + 30.0f);', 'arc_create', 0x43c),
    ('arc_gravity', 'arrow', '* F_0_1 + 26.0f;', '* F_0_1 + 25.0f;', 'arc_create', 0x617),
    ('ground_margin', 'fx', 'if (ground + 20.0f > e->position[2]) {', 'if (ground + 10.0f > e->position[2]) {',
     'ground_move', 0x43c),
    ('ground_high', 'fx', 'if (e->position[2] > ground + 600.0f)', 'if (e->position[2] > ground + 500.0f)',
     'ground_move', 0x441),
    ('ground_sound', 'fx', 'call_sound(env, e, 0x55e);', 'call_sound(env, e, 0x55f);', 'ground_move', 0x43b),
    ('ground_spot', 'fx', 'const float p[3] = {e->position[0], e->position[1], ground};',
     'const float p[3] = {e->position[0], e->position[1], e->position[2]};', 'ground_move', 0x60e),
    ('ground_skill', 'fx', 'e->skill == 0x7fc || e->skill == 0x7fd) {', 'e->skill == 0x7fc) {', 'ground_move', 0x471),
    ('lob_pitch', 'fx', 'if (e->angle[0] > 50.0f)\n                e->angle[0] = 50.0f;', 'if (e->angle[0] > 45.0f)\n                e->angle[0] = 45.0f;',
     'ground_move', 0x43b),
    ('lob_wall', 'fx', 'if (!(attribute & 8)) {\n                const float ground', 'if (!(attribute & 4)) {\n                const float ground',
     'ground_move', 0x43b),
    ('lob_check', 'fx', 'call_particle(env, e, MU_SFX_BITMAP_FIRE, e->position, e->angle, light, 5, 1.0f, MU_SFX_NO_OWNER);\n            break;',
     'call_particle(env, e, MU_SFX_BITMAP_FIRE, e->position, e->angle, light, 5, 1.0f, MU_SFX_NO_OWNER);\n            check(env, e, MU_SFX_CALL_CHECK_ARROW);\n            break;',
     'ground_move', 0x43b),
]


# ---------------------------------------------------------------- particle families

_random_particle = pt.random_particle


def random_particle(rng, kind):
    """validate_particles' record, with the lifetimes these kinds branch on (the fades below 15, 5, 4 and 3 steps)."""
    p = _random_particle(rng, kind)
    if kind in PET_KINDS or kind in ARROW_KINDS or kind in BOW_KINDS:
        p.lifetime = rng.choice([30, 20, 16, 15, 14, 14, 8, 6, 5, 5, 4, 4, 4, 3, 3, 2, 1, 0, -1, 46, 45, 44,
                                 rng.randrange(-2, 55)])
        p.initial_lifetime = rng.choice([5, 20, 8, 1, 25, rng.randrange(1, 30)])
        p.frame = rng.choice([0, 0, 1, p.frame])
    return p


def pt_compare(text, data, lib, name, kinds, cases):
    pt.KINDS, pt.OWNED_KINDS, pt.random_particle = kinds, OWNED, random_particle
    m = pt.PtMachine(text, data)   # a fresh machine for every family and mutant
    report = pt.Report()
    dict(pt.FAMILIES)[name](m, lib, random.Random('render-effects-010-' + name), cases, report, defaultdict(int))
    return {'families': {'pt_' + name: report.families[name]}, 'coverage': report.coverage}


def compile_pt_mutant(directory, name, file, old, new):
    work = Path(directory)/name
    for sub in ('particles', 'record-math'):
        shutil.copytree(ROOT/'reconstructed'/sub, work/sub,
                        ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
    path = work/'particles'/file
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    path.write_text(source.replace(old, new))
    base = work/'particles'
    others = ['world_flames.c', 'elbeland.c', 'sprites.c', 'shadow.c', 'visual.c', 'layout.c',
              '../record-math/record_math.c']
    out = Path(directory)/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(base), str(base/'particles.c'), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return pt.load_library(out)


# ---------------------------------------------------------------- the render-registry functors

class Pass(C.Structure):
    _fields_ = [('mesh', C.c_int32), ('flags', C.c_uint32), ('alpha', C.c_float), ('select', C.c_int32),
                ('color_scale', C.c_float), ('u', C.c_float), ('v', C.c_float), ('texture', C.c_int32),
                ('color', C.c_float*3)]


def bind(lib):
    lib.mu_sfx_arrow_render_passes.argtypes = [C.POINTER(fx.Effect), C.c_float, C.POINTER(Pass*8)]
    lib.mu_sfx_arrow_render_passes.restype = C.c_int
    lib.mu_sfx_arrow_tick_speed.argtypes = [C.POINTER(fx.Effect)]
    lib.mu_sfx_arrow_tick_speed.restype = C.c_float
    return lib


FUNCTOR_DEFINED = {'type', 'subtype', 'blend_mesh', 'blend_light', 'blend_u', 'blend_v', 'velocity', 'frame',
                   'prior_frame', 'prior_action', 'alpha', 'position', 'angle', 'action', 'live'}


def special(rng, value):
    return f32(rng.choice([value, 0.0, 1.0, 0.5, -0.0, vc.rfloat(rng, 0.01, 4.0)]))


def family_functor(m, lib, rng, cases, report, types):
    for n in range(cases):
        kind = types[n % len(types)]
        e = re7.random_arrow(rng, (kind, rng.choice([0, 2, 0x63])))
        e.type = kind
        e.blend_mesh = rng.choice([-1, -1, -2, 0, 1, 2, 3, 5, rng.randrange(-4, 9)])
        e.alpha = special(rng, 1.0)
        e.blend_light = special(rng, 1.0)
        e.blend_u = special(rng, 0.0)
        e.blend_v = special(rng, 0.0)
        e.velocity = special(rng, 0.3)
        clock = f32(rng.choice([0.0, 24.0, 25.0, 149.0, 150.0, 1e5 + rng.randrange(150), -60.0,
                                rng.uniform(0.0, 3.0e6), float('nan')]))
        tick_answer = rng.choice([1, 1, 1, 0])
        colour = [f32(rng.uniform(-0.5, 2.0)) for _ in range(3)]
        raw, mask = fx.effect_to_bytes(e, FUNCTOR_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x200, 0x55), bytes(0x200))
        model.define(fx.MODEL + 0x54, struct.pack('<3f', *colour))
        calls = []

        def tick(mm):
            calls.append(('tick', mm.uc.reg_read(mm.x86.UC_X86_REG_ECX), *[mm.argument(i) for i in range(6)]))
            return tick_answer, 0x18

        def set_action(mm):
            calls.append(('set_action', mm.argument(0), mm.argument(1)))
            return 0

        def render_mesh(mm):
            a = [mm.argument(i) for i in range(8)]
            signed = [x - (1 << 32) if x >> 31 else x for x in a]
            calls.append(('mesh', mm.uc.reg_read(mm.x86.UC_X86_REG_ECX), signed[0], a[1], vc.from_bits(a[2]), signed[3],
                          vc.from_bits(a[4]), vc.from_bits(a[5]), vc.from_bits(a[6]), signed[7],
                          mm.floats(fx.MODEL + 0x54, 3)))
            return 0, 0x20
        regions = [record, model, am.defined_region('clock', TIME, struct.pack('<f', clock), writable=False)]
        r = m.execute(FUNCTORS[kind], [fx.MODEL, fx.POOL], regions, {TICK: tick, SET_ACTION: set_action,
                                                                    RENDER_MESH: render_mesh})
        passes = (Pass*8)()
        count = lib.mu_sfx_arrow_render_passes(C.byref(e), clock, C.byref(passes))
        mine = [('tick', fx.MODEL, fx.POOL + 0xd0, fx.POOL + 0xd4, fx.POOL + 0x2c, vc.bits(lib.mu_sfx_arrow_tick_speed(C.byref(e))),
                 fx.POOL + 0x158, fx.POOL + 0x164)]
        if tick_answer == 0:
            mine.append(('set_action', fx.POOL, 0))
        for p in passes[:count]:
            mine.append(('mesh', fx.MODEL, p.mesh, p.flags, p.alpha, p.select, p.color_scale, p.u, p.v, p.texture,
                         list(p.color)))
        mismatch = None
        if vc.ok(r):
            if len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine)):
                mismatch = ('calls', calls, mine)
            elif r['eax'] & 0xff != 1:
                mismatch = ('result', r['eax'])
            elif not all(vc.same(a, b) for a, b in zip(struct.unpack('<3f', r['regions']['model'][0x54:0x60]), colour)):
                mismatch = ('colour not restored', struct.unpack('<3f', r['regions']['model'][0x54:0x60]), colour)
        report.add('functor', vc.ok(r) and mismatch is None and count > 0,
                   {'case': n, 'type': hex(kind), 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                    'checks': r['checks']})
        report.cover('functor', f'{kind:#x}/' + ('ticked' if tick_answer else 'ended') +
                     ('/blend mesh %d' % e.blend_mesh if kind in (0x615, 0x617) else ''))


def functor_machine(text, data):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    return fx.FxMachine(text, data)


# ---------------------------------------------------------------- the arrow paths of the arc and ground skills

ARROWS = [0x43b, 0x43c, 0x43d, 0x43e, 0x43f, 0x440, 0x441, 0x442, 0x443, 0x458, 0x459, 0x45a, 0x45b, 0x45c, 0x45d,
          0x45e, 0x471, 0x474, 0x47f, 0x525, 0x5b0, 0x5b1, 0x60a, 0x60d, 0x60e, 0x60f, 0x610, 0x612, 0x613, 0x614,
          0x615, 0x616, 0x617]
GROUND_SKILLS = [0x2d8, 0x7e7, 0x7fc, 0x7fd]
OWNER_FLAG = 0x014eca8b


class GroundCase(re9.Case):
    """validate_render_effects9's case with the owners' +0x64 flag on the C side (MU_SFX_CALL_OWNER_FLAG)."""

    def __init__(self, *a, flags=(), **kw):
        super().__init__(*a, **kw)
        self.c_flags = list(flags)

    def env(self, *args, **kwargs):
        env = super().env(*args, **kwargs)
        inner = self._call7   # validate_render_effects7's callback (a struct field read back would not dispatch)

        def call(ctx, cp, ep):
            c = cp.contents
            if c.routine == OWNER_FLAG:
                old = self.c_flags[c.owner]
                if old == 0:
                    self.c_flags[c.owner] = 1
                return old
            return inner(ctx, cp, ep)
        self._ground = fx.CALL_FN(call)
        env.call = self._ground
        return env


def family_ground(m, lib, rng, cases, report, kinds):
    """MoveEffect 0x0142fd09 for arrows of the arc skill 0x2d8 and the ground skills 0x7e7/0x7fc/0x7fd (the test
    0x014eca00..0x014ecb6e), every arrow type; CreateEffect for the arc skill (0x013cd5b6) is family arc_create."""
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = re7.random_arrow(rng, kind)
        e.skill = rng.choice(GROUND_SKILLS)
        objects = [fx.random_object(rng) for _ in range(2)]
        e.owner = rng.choice([0, 1])   # a NULL owner faults in the client's ground test
        flags = [rng.choice([0, 0, 1, 7]) for _ in objects]
        hero_obj = rng.choice([-1, 0, 1])
        keys = rng.choice([1, 7, 10, 30])
        has_model = rng.random() < 0.9
        z = e.position[2]
        height = f32(rng.choice([z - rng.uniform(-40.0, 19.0), z - 20.0, z - rng.uniform(10.0, 20.0), z - 15.0,
                                 z - rng.uniform(21.0, 599.0), z - 600.0, z - rng.uniform(601.0, 900.0),
                                 vc.rfloat(rng, 0.1, 600.0)]))
        names = re9.random_names(rng, kind[0])
        case = GroundCase(rng, objects, fx.rand_values(rng, 120), height, rng.choice([0, 1, 1]), keys, has_model,
                          names=names, records=True, flags=flags)
        raw, mask = fx.effect_to_bytes(e, re7.MOVE_DEFINED | {'skill'})
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(fx.MODEL + 0x30, struct.pack('<I', fx.MODEL + 0x1000))
        model.define(fx.MODEL + 0x22, struct.pack('<h', len(names)))
        model.define(fx.MODEL + 0x2c, struct.pack('<I', re9.BONES))
        for a in range(0x100):
            model.define(fx.MODEL + 0x1000 + 16 * a + 8, struct.pack('<h', keys))
        bones = am.defined_region('bones', re9.BONES, re9.names_bytes(names) or b'\0', writable=False)
        case.attributes = [rng.choice([0, 0, 8, 4, 0xc, 0x108]) for _ in range(0x10000)]   # TerrainWall
        objs = fx.object_region(objects, writable=True)
        for i, f in enumerate(flags):
            objs.define(fx.OBJECTS + 0x400 * i + 0x64, struct.pack('<i', f))
        clock = f32(rng.choice([0.0, 1000.0, rng.uniform(0.0, 1.0e5)]))
        hero_char = (fx.object_address(hero_obj) - 0x3254) & 0xffffffff if hero_obj >= 0 else 0x5000000
        regions = [record, objs, model, bones,
                   am.Region('quake', fx.QUAKE, am.poison(4, 0x21), bytes(4)),
                   am.defined_region('world', fx.WORLD, struct.pack('<i', 0), writable=False),
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False),
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', hero_char), writable=False),
                   am.defined_region('terrain-wall', fx.TERRAIN_WALL, struct.pack('<65536H', *case.attributes),
                                     writable=False)]
        r = m.execute(fx.MOVE_EFFECT, [fx.POOL, 0], regions, case.stubs(m))
        env = case.env(hero_object=hero_obj)
        env.world_time = clock
        supported = lib.mu_sfx_effect_move(C.byref(e), C.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = fx.compare_effect(e, out, record.defined, re7.MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = re7.compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None:
                theirs = [struct.unpack_from('<i', r['regions']['objects'], 0x400 * i + 0x64)[0] for i in range(len(flags))]
                if theirs != case.c_flags:
                    mismatch = ('owner +0x64', theirs, case.c_flags)
        report.add('ground_move', supported and vc.ok(r) and mismatch is None,
                   {'case': n, 'kind': [hex(kind[0]), kind[1]], 'skill': hex(e.skill), 'mismatch': mismatch,
                    'stopped': r['stopped'], 'error': r['error']})
        landed = any(c[0] == 'effect' and c[1] == 0x70c for c in case.client_calls)
        report.cover('ground_move', f'{e.skill:#x}/' + ('landed' if landed else
                                                        'killed high' if ('kill',) in case.client_calls else 'flying') +
                     ('/sound' if any(c[0] == 'sound' and c[1] == 0x55e for c in case.client_calls) else ''))


def family_arc_create(m, lib, rng, cases, report, kinds):
    saved = re7.random_info

    def info(r):
        i = saved(r)
        i.skill = 0x2d8
        return i
    re7.random_info, saved_case = info, re7.Case
    re7.Case = re9.Case
    try:
        re7.family_create(m, lib, rng, cases, report, kinds)
    finally:
        re7.random_info, re7.Case = saved, saved_case
    f = report.families.pop('effect_create')
    report.families['arc_create'] = f
    report.coverage['arc_create'] = report.coverage.pop('effect_create', {})


BODIES = {'functor_613': (0x00a4269f, 0x00a42984), 'functor_614': (0x00a42984, 0x00a42b8c),
          'functor_615': (0x00a42b8c, 0x00a42f55), 'functor_616': (0x00a42f55, 0x00a43160),
          'functor_617': (0x00a43160, 0x00a435ac), 'registry_calls': (0x00a13ada, 0x00a13b34),
          'create_7ffd_b': (0x015c1930, 0x015c1aaa), 'create_8085_1': (0x015d9074, 0x015d922e),
          'create_8086_4': (0x015d474d, 0x015d4994), 'create_8087_8': (0x015b95cc, 0x015b9828),
          'create_8089_5': (0x015d980f, 0x015d9a6b), 'create_8081_8': (0x015d377c, 0x015d38b9),
          'create_85fb_2': (0x01613d5d, 0x01613e5a), 'create_8450_4': (0x0160fc08, 0x0160fcff),
          'move_7ffd_b': (0x016305fa, 0x0163075d), 'move_8085_1': (0x0164b824, 0x0164bb00),
          'move_8086_4': (0x0164723f, 0x016479fa), 'move_8087_8': (0x0162679b, 0x01626f6b),
          'move_8089_5': (0x0164c420, 0x0164cbe9), 'move_8081_8': (0x01645975, 0x016459fe),
          'move_85fb_2': (0x0168bbdf, 0x0168bc78), 'move_8450_4': (0x01687e08, 0x01687e9d),
          'arc_create': (0x013cd5a4, 0x013cd66f), 'ground_test': (0x014eca00, 0x014ecb6e)}


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    plib = pt.load_library(ROOT/'reconstructed'/('particles/libclient_particles.' + fx.SUFFIX))
    for group, kinds in (('pets', PET_KINDS), ('arrows', ARROW_KINDS), ('bows', BOW_KINDS)):
        for name in ('create', 'move', 'render'):
            r = pt_compare(text, data, plib, name, kinds, cases * len(kinds))
            result['comparisons'][group + '_' + name] = {'families': {group + '_' + name: r['families']['pt_' + name]},
                                                         'coverage': r['coverage']}
    lib = bind(fx.load_library(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX)))
    report = pt.Report()
    family_functor(functor_machine(text, data), lib, random.Random('render-effects-010-functor'),
                   cases * len(FUNCTORS), report, sorted(FUNCTORS))
    result['comparisons']['functor'] = {'families': report.families, 'coverage': report.coverage}
    kinds = [(t, s) for t in ARROWS for s in (0, 2)]
    for name, family in (('arc_create', family_arc_create), ('ground_move', family_ground)):
        report = pt.Report()
        family(re9.machine(text, data), lib, random.Random('render-effects-010-' + name), cases * 6, report, kinds)
        result['comparisons'][name] = {'families': report.families, 'coverage': report.coverage}
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects10-pt-') as tmp:
            for name, file, old, new, family, kind in PT_MUTANTS:
                mlib = compile_pt_mutant(tmp, name, file, old, new)
                f = pt_compare(text, data, mlib, family, [kind], max(40, cases))['families']['pt_' + family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
        with tempfile.TemporaryDirectory(prefix='render-effects10-fn-') as tmp:
            for name, old, new, kind in FN_MUTANTS:
                mlib = bind(re9.compile_mutant(Path(tmp), name, old, new))
                report = pt.Report()
                family_functor(functor_machine(text, data), mlib, random.Random('render-effects-010-functor'),
                               max(40, cases), report, [kind])
                f = report.families['functor']
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    if mutations:
        families = {'arc_create': family_arc_create, 'ground_move': family_ground}
        with tempfile.TemporaryDirectory(prefix='render-effects10-path-') as tmp:
            for name, file, old, new, family, kind in PATH_MUTANTS:
                mlib = (bind(re9.compile_mutant(Path(tmp), name, old, new)) if file == 'arrow' else
                        bind(base.compile_mutant(Path(tmp), name, 'fx', old, new)))
                report = pt.Report()
                families[family](re9.machine(text, data), mlib, random.Random('render-effects-010-' + family),
                                 max(40, cases * 2), report, [(kind, 0), (kind, 2)])
                f = report.families[family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                               'sha256': hashlib.sha256(text[a - am.TEXT_BASE:b - am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in BODIES.items()}
    result['families'] = {name: f for r in result['comparisons'].values() for name, f in r['families'].items()}
    result['instruction_cases'] = sum(f['cases'] for f in result['families'].values())
    result['all_equal'] = all(f['cases'] == f['equal'] for f in result['families'].values())
    result['all_mutants_caught'] = all(v['caught'] > 0 for v in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=20, help='cases per kind (type, subtype) and family')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2))
    summary = {name: (f['cases'], f['equal']) for name, f in result['families'].items()}
    print(json.dumps({'summary': summary, 'instruction_cases': result['instruction_cases'],
                      'mutants': result['mutants'], 'all_equal': result['all_equal'],
                      'all_mutants_caught': result['all_mutants_caught']}, indent=1))
    if not result['all_equal']:
        for name, f in result['families'].items():
            for failure in f['first_failures'][:2]:
                print(name, str(failure)[:1500])
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
