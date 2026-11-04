#!/usr/bin/env python3
"""RENDER-EFFECTS-011 original-instruction families and compiled production mutants.

* The bows' remaining particle kinds (bow_kinds2.inc): Flare 0x7f78/5, Smoke_line 0x83b3/1, Spark04 0x8155/2,
  smoke01 0x7f5a/0x18, 0x4e and 0x7a, firehik03 0x8085/0x11 (dies with its owner: the owner OBJECT's live byte
  +0x00 through 0x0095f977), pin_star02_pupple 0x810c/0, Snow_Chip02_red 0x83b8/2, firehik01 0x8084/0x1e,
  flare_mono 0x8184/1 and lighting_mega01..03 0x8081..0x8083/0. Through validate_particles' create (CreateParticle
  0x015ae7b0), move (MoveParticles 0x01616c80) and render (RenderParticles 0x0159123f) families against
  reconstructed/particles; the owner OBJECT regions also define their live byte.
* The bows' effects (reconstructed/combat/bow_fx.inc): 0x477/3 and /4, 0x60b/0 and 0x611/0, through
  validate_render_effects7's CreateEffect (0x013c0eaa) and MoveEffect (0x0142fd09) families with
  validate_render_effects9's case.

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
import validate_skill_fx as fx
import validate_particles as pt
import validate_render_effects7 as re7
import validate_render_effects9 as re9

ROOT = Path(__file__).resolve().parents[1]
f32 = fx.f32
BOW2_KINDS = [(0x7f78, 5), (0x83b3, 1), (0x8155, 2), (0x7f5a, 0x18), (0x7f5a, 0x4e), (0x7f5a, 0x7a), (0x8085, 0x11),
              (0x810c, 0), (0x83b8, 2), (0x8084, 0x1e), (0x8184, 1), (0x8081, 0), (0x8082, 0), (0x8083, 0)]

PT_MUTANTS = [
    # (name, file, old, new, family, kind) on reconstructed/particles
    ('flare_life', 'bow_kinds2.inc', 'p->lifetime = 40;\n        p->gravity', 'p->lifetime = 41;\n        p->gravity',
     'create', (0x7f78, 5)),
    ('flare_sink', 'bow_kinds2.inc', '/ 100.0f * 5.0f + 1.0f;', '/ 100.0f * 5.0f + 2.0f;', 'create', (0x7f78, 5)),
    ('flare_circle', 'bow_kinds2.inc', '(float)sin((double)t) * 40.0f + p->start[0];',
     '(float)sin((double)t) * 30.0f + p->start[0];', 'move', (0x7f78, 5)),
    ('flare_drift', 'bow_kinds2.inc', 'p->start[0] = p->start[0] + 2.5f;', 'p->start[0] = p->start[0] + 2.0f;',
     'move', (0x7f78, 5)),
    ('flare_dim', 'bow_kinds2.inc', 'if (p->lifetime <= 20)                     /* 0x0162dea7 */',
     'if (p->lifetime < 20)                     /* 0x0162dea7 */', 'move', (0x7f78, 5)),
    ('flare_hide', 'bow_kinds2.inc', 'return p->lifetime != 60;', 'return p->lifetime != 40;', 'render', (0x7f78, 5)),
    ('line_alpha', 'bow_kinds2.inc', 'p->lifetime = 20;\n        p->initial_lifetime = p->lifetime;\n        p->alpha = 1.0f;\n        p->rotation = (float)(mu_pt_rand(h) % 360);\n        p->initial_scale = p->scale;',
     'p->lifetime = 20;\n        p->initial_lifetime = p->lifetime;\n        p->alpha = 0.5f;\n        p->rotation = (float)(mu_pt_rand(h) % 360);\n        p->initial_scale = p->scale;', 'create', (0x83b3, 1)),
    ('line_fade', 'bow_kinds2.inc', 'p->light[k] = p->light[k] - step;', 'p->light[k] = p->light[k] - 0.5f * step;',
     'move', (0x83b3, 1)),
    ('line_draw', 'particles.c', 'if (p->subtype != 1 || p->type != 0x83b3)', 'if (p->subtype != 2 || p->type != 0x83b3)',
     'render', (0x83b3, 1)),
    ('spark4_size', 'bow_kinds2.inc', '(float)(mu_pt_rand(h) % 5) / 10.0f + 0.2f;', '(float)(mu_pt_rand(h) % 10) / 10.0f + 0.2f;',
     'create', (0x8155, 2)),
    ('spark4_dim', 'bow_kinds2.inc', 'p->light[k] = p->light[k] / 1.05f;\n        p->scale = p->scale - 0.01f;\n        p->lifetime = p->lifetime - 1;\n        if (p->lifetime <= 0)\n            p->live = 0;\n        return;\n    case MU_PT_BITMAP_SMOKE:',
     'p->light[k] = p->light[k] / 1.06f;\n        p->scale = p->scale - 0.01f;\n        p->lifetime = p->lifetime - 1;\n        if (p->lifetime <= 0)\n            p->live = 0;\n        return;\n    case MU_PT_BITMAP_SMOKE:', 'move', (0x8155, 2)),
    ('spark4_alpha', 'bow_kinds2.inc', 'if (p->type == 0x8155 || p->type == 0x8084)', 'if (p->type == 0x8084)',
     'render', (0x8155, 2)),
    ('smoke_size', 'bow_kinds2.inc', '(float)(mu_pt_rand(h) % 32 + 48) * 0.01f * scale + scale;',
     '(float)(mu_pt_rand(h) % 32 + 48) * 0.01f * scale;', 'create', (0x7f5a, 0x18)),
    ('smoke_colour', 'bow_kinds2.inc', 'p->field_7c = p->light[0];             /* the colour',
     'p->field_7c = p->light[1];             /* the colour', 'create', (0x7f5a, 0x7a)),
    ('smoke_green', 'bow_kinds2.inc', 'p->light[1] = l * 0.5f;', 'p->light[1] = l * 0.6f;', 'move', (0x7f5a, 0x18)),
    ('smoke_sway', 'bow_kinds2.inc', '* p->gravity * 0.05f + p->position[0];', '* p->gravity * 0.06f + p->position[0];',
     'move', (0x7f5a, 0x4e)),
    ('smoke_lift', 'bow_kinds2.inc', 'p->position[2] = p->position[2] + 5.0f;', 'p->position[2] = p->position[2] + 4.0f;',
     'move', (0x7f5a, 0x7a)),
    ('fire_spin', 'bow_kinds2.inc', 'p->rotation = (float)mu_pt_rand(h);', 'p->rotation = (float)(mu_pt_rand(h) % 360);',
     'create', (0x8085, 0x11)),
    ('fire_owner', 'bow_kinds2.inc', 'if (!mu_pt_owner_alive(p, h)) {', 'if (0) {', 'move', (0x8085, 0x11)),
    ('fire_speed', 'bow_kinds2.inc', '* 300.0f;', '* 250.0f;', 'move', (0x8085, 0x11)),
    ('fire_red', 'bow_kinds2.inc', '(float)((double)a * 0.8);', '(float)((double)a * 0.7);', 'move', (0x8085, 0x11)),
    ('purple_jitter', 'bow_kinds2.inc', 'p->velocity[k] = rand_range(h, -1.0f, 1.0f, 10);',
     'p->velocity[k] = rand_range(h, -1.0f, 1.0f, 20);', 'create', (0x810c, 0)),
    ('purple_wander', 'bow_kinds2.inc', 'if (p->lifetime <= 30) {\n            p->velocity[0]', 'if (p->lifetime < 30) {\n            p->velocity[0]',
     'move', (0x810c, 0)),
    ('purple_back', 'bow_kinds2.inc', '{-p->angle[0], -p->angle[1], -p->angle[2]}', '{p->angle[0], p->angle[1], p->angle[2]}',
     'move', (0x810c, 0)),
    ('purple_life', 'bow_kinds2.inc', '(int32_t)((double)p->lifetime - 0.1);', '(int32_t)((double)p->lifetime - 2.1);',
     'move', (0x810c, 0)),
    ('purple_kill', 'bow_kinds2.inc', 'if (p->lifetime <= 0 || 0.0f >= p->scale)', 'if (p->lifetime <= 0)',
     'move', (0x810c, 0)),
    ('chip_jump', 'bow_kinds2.inc', 'const float v[3] = {a, 0.0f, b};', 'const float v[3] = {b, 0.0f, a};', 'create', (0x83b8, 2)),
    ('chip_order', 'bow_kinds2.inc', 'p->velocity[0] = x;\n        p->velocity[1] = y;', 'p->velocity[0] = y;\n        p->velocity[1] = x;',
     'create', (0x83b8, 2)),
    ('chip_turn', 'bow_kinds2.inc', 'if (p->lifetime % 8 < 4)', 'if (p->lifetime % 8 <= 4)', 'move', (0x83b8, 2)),
    ('push_len', 'bow_kinds2.inc', 'const float v[3] = {0.0f, -7.0f, 0.0f};', 'const float v[3] = {0.0f, 7.0f, 0.0f};',
     'create', (0x8084, 0x1e)),
    ('push_move', 'bow_kinds2.inc', 'p->position[k] = p->position[k] + p->velocity[k];\n        return;\n    case 0x8184:',
     'p->position[k] = p->position[k] - p->velocity[k];\n        return;\n    case 0x8184:', 'move', (0x8084, 0x1e)),
    ('push_alpha', 'bow_kinds2.inc', 'if (p->type == 0x8155 || p->type == 0x8084)', 'if (p->type == 0x8155)',
     'render', (0x8084, 0x1e)),
    ('mono_spread', 'bow_kinds2.inc', '(float)(mu_pt_rand(h) % 4 - 2);', '(float)(mu_pt_rand(h) % 4 - 1);', 'create', (0x8184, 1)),
    ('mono_turn', 'bow_kinds2.inc', 'if (p->lifetime > 20)\n            p->scale = p->scale + 0.01f;',
     'if (p->lifetime >= 20)\n            p->scale = p->scale + 0.01f;', 'move', (0x8184, 1)),
    ('mega_dark', 'bow_kinds2.inc', 'p->light[0] = p->light[1] = p->light[2] = 0.0f;\n        return;',
     'p->light[0] = p->light[1] = 0.0f;\n        return;', 'create', (0x8082, 0)),
    ('mega_fade', 'bow_kinds2.inc', 'p->alpha = p->alpha - 0.15f;', 'p->alpha = p->alpha - 0.1f;', 'move', (0x8081, 0)),
    ('mega_out', 'bow_kinds2.inc', 'if (0.1f > p->alpha)', 'if (0.15f > p->alpha)', 'move', (0x8083, 0)),
]


FX_KINDS = [(0x477, 3), (0x477, 4), (0x60b, 0), (0x611, 0)]
FX_MUTANTS = [
    # (name, old, new, family, kind) on reconstructed/combat/bow_fx.inc
    ('ring_scale', '* f32bits(0x3d4ccccdu);   /* the info key', '* f32bits(0x3dcccccdu);   /* the info key', 'create', (0x477, 3)),
    ('ring_lift', 'e->position[2] = e->position[2] - 50.0f;', 'e->position[2] = e->position[2] - 40.0f;', 'create', (0x477, 4)),
    ('ring_turn', 'e->angle[2] = angle_arg[2];', 'e->angle[2] = e->angle[2];', 'create', (0x477, 3)),
    ('ring_life', 'e->lifetime = 15;', 'e->lifetime = 20;', 'create', (0x477, 4)),
    ('ring_grow', '(three ? f32bits(0x3ba3d70au) : f32bits(0x3b03126fu))', '(three ? f32bits(0x3b03126fu) : f32bits(0x3b03126fu))',
     'move', (0x477, 3)),
    ('ring_cap', 'const float most = three ? 1.5f : 2.5f;', 'const float most = three ? 1.5f : 2.0f;', 'move', (0x477, 4)),
    ('ring_fade', '(three ? f32bits(0x3fa66666u) : f32bits(0x3f99999au))', '(three ? f32bits(0x3fa66666u) : f32bits(0x3fa66666u))',
     'move', (0x477, 4)),
    ('burst_mesh', 'e->blend_mesh = 0;', 'e->blend_mesh = -1;', 'create', (0x60b, 0)),
    ('burst_grow', 'e->scale = e->scale + f32bits(0x3f19999au);', 'e->scale = e->scale + 0.5f;', 'move', (0x60b, 0)),
    ('burst_end', 'if (F_0_2 > e->blend_light) {', 'if (F_0_1 > e->blend_light) {', 'move', (0x60b, 0)),
    ('burst_model', 'if (env && env->model && !env->model(env->context, e->type, e->action, &keys))\n            return;',
     'if (0)\n            return;', 'move', (0x60b, 0)),
    ('wave_scale', 'e->scale = scale;                          /* the argument', 'e->scale = e->scale;                          /* the argument',
     'create', (0x611, 0)),
    ('wave_pitch', 'e->angle[0] = -90.0f;', 'e->angle[0] = 90.0f;', 'create', (0x611, 0)),
    ('wave_fade', 'e->alpha = (float)e->lifetime / (float)e->field_70;', 'e->alpha = (float)(e->lifetime - 1) / (float)e->field_70;',
     'move', (0x611, 0)),
]


def fx_compare(text, data, lib, name, kinds, cases, seed='render-effects-011-fx-'):
    saved = re7.Case
    re7.Case = re9.Case
    report = pt.Report()
    try:
        getattr(re7, 'family_' + name)(re9.machine(text, data), lib, random.Random(seed + name), cases, report, kinds)
    finally:
        re7.Case = saved
    family = report.families.pop('effect_' + name)
    return {'families': {'fx_' + name: family}, 'coverage': {'fx_' + name: report.coverage.get('effect_' + name, {})}}


def compile_fx_mutant(directory, name, old, new):
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
    return fx.load_library(out)


# ---------------------------------------------------------------- particle families

WORLD_TIME = [0.0]   # the case's clock [0x06fce370] (smoke01/0x4e sways by its sine)


class OwnerCase(pt.Case):
    """validate_particles' case with the owner OBJECT's live byte +0x00 defined (0x0095f977) and a running clock
    (validate_particles' move family keeps it 0 for these kinds)."""

    def __init__(self, rng, *a, **kw):
        super().__init__(rng, *a, **kw)
        self.alive = [rng.choice([1, 1, 0, 2]) for _ in self.owners]
        WORLD_TIME[0] = f32(rng.choice([0.0, 1.5707964, 39.0, 123456.0, rng.uniform(-1e6, 3.0e6)]))

    def owner_regions(self):
        out = super().owner_regions()
        for region, alive in zip(out, self.alive):
            region.define(region.base, bytes([alive]))
        return out

    def host(self, world=0, world_time=0.0, *a, **kw):
        host = super().host(world, WORLD_TIME[0], *a, **kw)

        def owner_live(ctx, index):
            return int(self.alive[index] != 0)
        fn = pt.OWNER_LIVE_FN(owner_live)
        self._keep.append(fn)
        host.owner_live = fn
        return host


_random_particle = pt.random_particle
_globals_region = pt.globals_region


def globals_region(world=0, world_time=0.0, *a, **kw):
    return _globals_region(world, WORLD_TIME[0], *a, **kw)


# the lifetimes each kind branches on (moves at 60/20, 45, 30, 20, lifetime % 8 < 4; renders at 60)
THRESHOLDS = {0x7f78: [61, 60, 59, 21, 20, 19], 0x8155: [46, 45, 44], 0x810c: [31, 30, 29, 1, 2],
              0x8184: [21, 20, 19], 0x83b8: [3, 4, 5, 11, 12, 13], 0x8085: [10, 5, 1]}


def random_particle(rng, kind):
    """validate_particles' record, with the lifetimes, alphas and lives these kinds branch on."""
    p = _random_particle(rng, kind)
    if kind in BOW2_KINDS:
        p.lifetime = rng.choice(THRESHOLDS.get(kind[0], []) * 3 + [12, 8, 4, 3, 2, 1, 0, -1, rng.randrange(-9, 70)])
        p.live = rng.choice([1, 1, 1, 1, 1, 0, 2])
        p.initial_lifetime = rng.choice([10, 20, 32, 50, 1, 3, rng.randrange(1, 60)])
        p.alpha = f32(rng.choice([1.0, 0.25, 0.26, 0.24, 0.1, 0.11, rng.uniform(-0.2, 1.2)]))
        p.scale = f32(rng.choice([p.scale, 0.0, 0.002, -0.01, rng.uniform(0.0, 0.05)]))
    return p


def pt_compare(text, data, lib, name, kinds, cases, seed='render-effects-011-'):
    pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case = kinds, set(), random_particle, OwnerCase
    pt.globals_region = globals_region
    m = pt.PtMachine(text, data)   # a fresh machine for every family and mutant
    report = pt.Report()
    dict(pt.FAMILIES)[name](m, lib, random.Random(seed + name), cases, report, defaultdict(int))
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


BODIES = {'create_flare_5': (0x015bea78, 0x015bee03), 'move_flare_5': (0x0162d771, 0x0162d95b),
          'render_flare': (0x015983fa, 0x01598559),
          'create_83b3_1': (0x015cfe72, 0x015cff03), 'move_83b3_1': (0x0164316e, 0x0164320b),
          'create_8155_2': (0x0160b267, 0x0160b3a2), 'move_8155_2': (0x01683a73, 0x01683c70),
          'render_8155_2': (0x015a5aa0, 0x015a5b7c),
          'create_7f5a_18': (0x015c6bcd, 0x015c6c99), 'create_7f5a_7a': (0x015cb8ee, 0x015cb9fc),
          'move_7f5a_18': (0x01636a33, 0x01636b99), 'move_7f5a_4e': (0x0163e3c9, 0x0163e5cc),
          'move_7f5a_7a': (0x0163e5d1, 0x0163e772),
          'create_8085_11': (0x015da370, 0x015da408), 'move_8085_11': (0x0164dbdb, 0x0164df05),
          'create_810c_0': (0x0160844b, 0x016085bb), 'move_810c_0': (0x01681c64, 0x01682004),
          'create_83b8_2': (0x015e30d4, 0x015e333b), 'move_83b8_2': (0x01657383, 0x016574d3),
          'create_8084_1e': (0x015d6c25, 0x015d6d59), 'move_8084_1e': (0x0164a207, 0x0164a2d2),
          'render_8084_1e': (0x015a4461, 0x015a453e),
          'create_8184_1': (0x015f95ef, 0x015f96dc), 'move_8184_1': (0x0167252c, 0x016725b0),
          'create_8081_0': (0x015d2e4c, 0x015d2f79), 'move_8081_0': (0x01644e1d, 0x01644f65),
          'owner_live': (0x0095f977, 0x0095f986),
          'create_477': (0x013d9444, 0x013d9567), 'create_477_2_4': (0x013d97f4, 0x013d98a5),
          'move_477_3_4': (0x014719f8, 0x01471b7b), 'create_60b': (0x014001e3, 0x0140020c),
          'move_60b': (0x01468a1f, 0x01468ae5), 'create_611': (0x0140fea0, 0x0140ff17),
          'move_611': (0x014c4c8e, 0x014c4cd0)}


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    plib = pt.load_library(ROOT/'reconstructed'/('particles/libclient_particles.' + fx.SUFFIX))
    for name in ('create', 'move', 'render'):
        r = pt_compare(text, data, plib, name, BOW2_KINDS, cases * len(BOW2_KINDS))
        result['comparisons']['bows2_' + name] = {'families': {'bows2_' + name: r['families']['pt_' + name]},
                                                  'coverage': r['coverage']}
    lib = fx.load_library(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX))
    for name in ('create', 'move'):
        r = fx_compare(text, data, lib, name, FX_KINDS, cases * len(FX_KINDS) * 2)
        result['comparisons']['fx_' + name] = r
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects11-fx-') as tmp:
            for name, old, new, family, kind in FX_MUTANTS:
                mlib = compile_fx_mutant(tmp, name, old, new)
                f = fx_compare(text, data, mlib, family, [kind], max(40, cases))['families']['fx_' + family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
        with tempfile.TemporaryDirectory(prefix='render-effects11-pt-') as tmp:
            for name, file, old, new, family, kind in PT_MUTANTS:
                mlib = compile_pt_mutant(tmp, name, file, old, new)
                f = pt_compare(text, data, mlib, family, [kind], max(40, cases))['families']['pt_' + family]
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
            for failure in f['first_failures'][:3]:
                print(name, str(failure)[:1500])
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
