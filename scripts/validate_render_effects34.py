#!/usr/bin/env python3
"""RENDER-EFFECTS-034: consumer pairs that world, item and Muun producers already request.

One grouped, table-driven comparison with the client's instructions (Unicorn over the pinned text/data):

* create / move / render   CreateParticle core 0x015ae7b0, MoveParticles' record body 0x01616f7c and
                           RenderParticles' record body 0x015912e9 for every particle pair of
                           reconstructed/particles/consumer34_kinds.inc (and 0x7f54/1): record fields, ordered
                           calls, rand() counts and the draw calls. The follow pair 0x855d/2 also compares the
                           owner-point position write of RenderParticles.
* joint_create / joint_move / joint_render   the joint pairs through scripts/validate_joints.py's families.
* census                   every pair is admitted by the authored library.

Compiled mutants (--mutations): per pair a removed create, a changed move and a removed draw, plus the form
controls listed in MUTANTS; each must be detected without stopping the original side.
"""
import argparse
import ctypes
import io
import re
import subprocess
from collections import defaultdict
import json
from pathlib import Path
import random
import struct
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import pins  # noqa: E402
import validate_combat as vc  # noqa: E402
import validate_particles as pt  # noqa: E402
import validate_render_effects11 as re11  # noqa: E402
import validate_joints as jt  # noqa: E402
import validate_skill_fx as fx  # noqa: E402
import validate_render_effects31 as re31  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLAIN = [(0x8016, 5), (0x7ef7, 11), (0x7f5a, 43), (0x7f5a, 47), (0x7f54, 1), (0x7efa, 3)]
# requested by the actor caller services (RENDER-ACTORS-008's request table)
ACTOR = [(0x7f26, 3), (0x7f5a, 50), (0x7ef7, 12), (0x7ef7, 13), (0x806e, 0), (0x807e, 0)]
ITEM = [(0x8616, 0), (0x7fe0, 10), (0x84d1, 2), (0x850b, 5), (0x807e, 14), (0x807f, 14), (0x8080, 14)]
FOLLOW = [(0x855d, 2)]
PULSE = [(0x8081, 1), (0x8082, 1), (0x7ef7, 19)]
KINDS = PLAIN + ITEM + FOLLOW + PULSE + ACTOR
GROUPS = {'plain': PLAIN, 'item': ITEM, 'follow': FOLLOW, 'pulse': PULSE, 'actor': ACTOR}
JOINTS = [(0x7f7c, 8), (0x7f7c, 19), (0x7fd5, 4), (0x7f7d, 11)]

# Per-pair controls are compiled production changes at the group's three entry points.
MUTANTS = []
for kind in KINDS:
    cond = f'p->type == {kind[0]} && p->subtype == {kind[1]}'
    in_table = kind != (0x7f54, 1)
    create_anchor = ('static void mu_pt_consumer34_create(mu_pt_particle *p, const mu_pt_host *h, float scale)\n{'
                     if in_table else '    owner_position(p, h);\n    if (!mu_pt_kind_supported(type, subtype))')
    move_anchor = ('static void mu_pt_consumer34_move(mu_pt_particle *p, const mu_pt_host *h)\n{'
                   if in_table else '            p->frame = (20 - p->lifetime) / 2;')
    for family, anchor, body, file in [
            ('create', create_anchor, 'p->lifetime = 0; return;' if in_table else 'p->rotation = 1.0f;',
             'consumer34_kinds.inc' if in_table else 'particles.c'),
            ('move', move_anchor, 'p->scale = p->scale + 1.0f; return;' if in_table else 'p->scale = p->scale + 1.0f;',
             'consumer34_kinds.inc' if in_table else 'particles.c'),
            ('render', '    memset(out, 0, sizeof *out);', 'return 0;', 'particles.c')]:
        if in_table or family != 'create':
            new = anchor + f'\n    if ({cond}) {{ {body} }}'
        else:
            new = f'    owner_position(p, h);\n    if ({cond}) {{ {body} }}\n    if (!mu_pt_kind_supported(type, subtype))'
        MUTANTS.append((f'p{kind[0]:x}_{kind[1]}_{family}', file, anchor, new, family, kind))
MUTANTS = [('pt',) + m for m in MUTANTS]
for kind in JOINTS:
    cond = f'j->type == {kind[0]} && j->subtype == {kind[1]}'
    for family, anchor, body, file in [
            ('joint_create', 'static void create_consumer34_joint(mu_jt_joint *j, float scale, const float target_position[3], const mu_jt_env *env)\n{',
             'j->lifetime = 0; return;', 'consumer34_joints.inc'),
            ('joint_move', 'static void move_consumer34_joint(mu_jt_joint *j, const mu_jt_env *env)\n{\n    float m[12];',
             'j->scale = j->scale + 1.0f; return;', 'consumer34_joints.inc'),
            ('joint_render', 'int mu_jt_render(const mu_jt_joint *j, uint8_t mode, float world_time, const mu_jt_gl *gl)\n{',
             'return 0;', 'joints.c')]:
        MUTANTS.append(('jt', f'j{kind[0]:x}_{kind[1]}_{family[6:]}', file, anchor,
                        anchor + f'\n    if ({cond}) {{ {body} }}', family, kind))
MUTANTS += [('jt',) + m for m in [
    ('spark4_width', 'consumer34_joints.inc', 'j->scale = scale * 2.0f + 4.0f;', 'j->scale = scale * 2.0f;', 'joint_create', (0x7fd5, 4)),
    ('spark4_colour', 'consumer34_joints.inc', 'j->light[1] = j->light[2] = F_0_2;\n        return;',
     'j->light[1] = j->light[2] = 1.0f;\n        return;', 'joint_create', (0x7fd5, 4)),
    ('bolt11_far_end', 'consumer34_joints.inc', '            mu_jt_tail_shift(j, m);\n            copy3(j->target_position, j->position);',
     '            mu_jt_tail_shift(j, m);', 'joint_move', (0x7f7d, 11)),
    ('bolt11_jitter', 'consumer34_joints.inc', 'const int32_t a = trunc_i32(j->scale / 8.0f);', 'const int32_t a = trunc_i32(j->scale / 4.0f);',
     'joint_move', (0x7f7d, 11)),
    ('bolt11_blue', 'consumer34_joints.inc', 'j->light[2] = j->light[2] + F_0_2;', 'j->light[2] = j->light[2] + F_0_1;',
     'joint_create', (0x7f7d, 11)),
    ('arc19_turn', 'consumer34_joints.inc', '25.0f + j->scale);', '110.0f);', 'joint_move', (0x7f7c, 19)),
    ('arc19_jitter_axis', 'consumer34_joints.inc', 'for (int k = 0; k < 3; ++k)\n            j->jitter[k] = (float)(imod(jrand(env), 1024) - 512) / j->scale;',
     'for (int k = 0; k < 3; k += 2)\n            j->jitter[k] = (float)(imod(jrand(env), 1024) - 512) / j->scale;', 'joint_move', (0x7f7c, 19)),
    ('arc19_speed', 'consumer34_joints.inc', 'j->velocity = j->scale * 3.0f;', 'j->velocity = j->scale * 2.0f;', 'joint_create', (0x7f7c, 19)),
    ('thunder8_tails', 'consumer34_joints.inc', 'j->lifetime = jrand(env) % 8 + 8;\n        j->max_tails = 2;\n        j->light[0] = j->light[1] = j->light[2] = 1.0f;',
     'j->lifetime = jrand(env) % 8 + 8;\n        j->max_tails = 3;\n        j->light[0] = j->light[1] = j->light[2] = 1.0f;', 'joint_create', (0x7f7c, 8)),
]]
MUTANTS += [('pt',) + m for m in [
    ('swamp_life', 'consumer34_kinds.inc', 'p->lifetime = 20;\n        p->velocity[0] = (float)(mu_pt_rand(h) % 10 - 5) * 0.4f;',
     'p->lifetime = 24;\n        p->velocity[0] = (float)(mu_pt_rand(h) % 10 - 5) * 0.4f;', 'create', (0x8016, 5)),
    ('flare11_rise', 'consumer34_kinds.inc', 'p->position[2] = p->position[2] + p->gravity;\n            p->scale = p->scale - 0.0005f;',
     'p->position[2] = p->position[2] - p->gravity;\n            p->scale = p->scale - 0.0005f;', 'move', (0x7ef7, 11)),
    ('clud_texture', 'consumer34_kinds.inc', 'p->tex_type = 0x7ffd;', 'p->tex_type = 0x7f5a;', 'create', (0x7f5a, 43)),
    ('burst_end', 'consumer34_kinds.inc', 'if (0.05f >= p->light[0])', 'if (0.05f > p->light[0])', 'move', (0x7f5a, 47)),
    ('explosion1_light', 'particles.c', 'if (p->subtype == 1) break;           /* RENDER-EFFECTS-034',
     'if (p->subtype == 2) break;           /* RENDER-EFFECTS-034', 'move', (0x7f54, 1)),
    ('impack3_turn', 'consumer34_kinds.inc', 'if (p->lifetime > 10)\n            p->scale = p->scale + 0.02f;',
     'if (p->lifetime >= 10)\n            p->scale = p->scale + 0.02f;', 'move', (0x7efa, 3)),
    ('impack3_draws', 'consumer34_kinds.inc', 'if (row->form == MU_PT34_NODRAW)\n        return 0;',
     'if (row->form == MU_PT34_NODRAW)\n        return 1;', 'render', (0x7efa, 3)),
    ('item_alpha_draw', 'consumer34_kinds.inc', 'if (row->form == MU_PT34_ITEM || row->form == MU_PT34_FOLLOW)',
     'if (row->form == MU_PT34_FOLLOW)', 'render', (0x8616, 0)),
    ('smoke_half', 'consumer34_kinds.inc', 'if (p->lifetime < half)\n            p->alpha = p->alpha - 1.0f / (float)half;',
     'if (p->lifetime <= half)\n            p->alpha = p->alpha - 1.0f / (float)half;', 'move', (0x8080, 14)),
    ('grow_factor', 'consumer34_kinds.inc', "(p->type == 0x84d1 ? 1.2f : 2.0f)", "(p->type == 0x84d1 ? 2.0f : 1.2f)",
     'create', (0x850b, 5)),
    ('follow_start', 'consumer34_kinds.inc', 'p->position[k] = point[k] + p->start[k];', 'p->position[k] = point[k];',
     'render', (0x855d, 2)),
    ('follow_null', 'particles.c', 'if (p->type == 0x855d && p->subtype == 2 && p->owner == MU_PT_NO_OWNER) {\n        p->live = 0;',
     'if (p->type == 0x855d && p->subtype == 2 && p->owner == MU_PT_NO_OWNER) {\n        p->live = 1;', 'render', (0x855d, 2)),
    ('pulse_life', 'consumer34_kinds.inc', 'p->initial_lifetime = p->type == 0x7ef7 ? 7 : 5;',
     'p->initial_lifetime = p->type == 0x7ef7 ? 5 : 7;', 'create', (0x7ef7, 19)),
    ('pulse_floor', 'consumer34_kinds.inc', 'p->alpha = t * 0.9f + 0.1f;', 'p->alpha = t * 0.9f;', 'move', (0x8081, 1)),
    ('pulse_colour', 'consumer34_kinds.inc', 'p->light[1] = p->field_80 * p->alpha;\n    p->light[2] = p->field_84 * p->alpha;\n}\n\n/* RenderParticles',
     'p->light[1] = p->field_7c * p->alpha;\n    p->light[2] = p->field_84 * p->alpha;\n}\n\n/* RenderParticles', 'move', (0x8082, 1)),
    ('actor_alpha_ceiling', 'consumer34_kinds.inc', 'mu_pt34_alpha_colour(p, h, 0.5f, 3);', 'mu_pt34_alpha_colour(p, h, 0.6f, 3);',
     'move', (0x7f5a, 50)),
    ('actor_alpha_fall', 'consumer34_kinds.inc', 'if (p->lifetime < 10)\n        p->alpha = p->alpha - 0.1f;',
     'if (p->lifetime <= 10)\n        p->alpha = p->alpha - 0.1f;', 'move', (0x807e, 0)),
    ('smoke0_world', 'consumer34_kinds.inc', 'h && h->world == 0x3f ? 25 : 35', 'h && h->world == 0x3f ? 35 : 35', 'create', (0x807e, 0)),
    ('flare12_turn', 'consumer34_kinds.inc', 'if (p->lifetime > 80)', 'if (p->lifetime >= 80)', 'move', (0x7ef7, 12)),
    ('flare13_drift', 'consumer34_kinds.inc', 'p->position[1] = p->position[1] - p->gravity;', 'p->position[1] = p->position[1] + p->gravity;',
     'move', (0x7ef7, 13)),
    ('fire0_rise', 'consumer34_kinds.inc', 'p->gravity * 10.0f + p->position[2]', 'p->gravity * 1.0f + p->position[2]', 'move', (0x806e, 0)),
    ('glow3_shrink', 'consumer34_kinds.inc', 'p->scale = p->scale * 0.8f;', 'p->scale = p->scale * 0.9f;', 'move', (0x7f26, 3)),
]]


def load_library(path):
    lib = pt.load_library(path)
    lib.mu_pt_consumer34_follow.argtypes = [pt.P(pt.Particle), pt.FP]
    lib.mu_pt_consumer34_follow.restype = ctypes.c_int
    return lib


def render_family(m, lib, rng, cases, report, kinds):
    """validate_particles.family_render with RenderParticles' owner-point write for the follow pair."""
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        p = pt.random_particle(rng, kind)
        p.live = 1
        p.owner = -1
        mode = rng.choice([0, 0, 1, 2, 3])
        bm = pt.Bitmap(pt.f32(rng.choice([64.0, 128.0, 256.0, 32.0])), pt.f32(rng.choice([64.0, 128.0, 32.0])),
                       rng.choice([3, 3, 4]))
        if rng.random() < 0.3:
            p.position[2] = pt.f32(rng.choice([300.0, 350.0, 299.99997, 350.00003, 1e9]))
        case = pt.Case(rng)
        owner_regions = []
        point = None
        follow = kind in FOLLOW
        if follow:
            p.owner = rng.choice([-1, 0, 0, 0])
            p.arg8 = n % 3
            points = [pt.rf(rng, -100, 500) for _ in range(9)]
            case.owners = [[0.0, 0.0, 0.0]]
            owner_regions = case.owner_regions()
            owner_regions[0].define(pt.OBJECTS + 0x1f4, struct.pack('<9f', *points))
            point = pt.F3(*points[3*p.arg8:3*p.arg8+3]) if p.owner >= 0 else None
        world_time = pt.f32(rng.uniform(0, 1e6))
        record = pt.particle_region(lib, p)
        bmr = am.Region('bitmap', pt.BITMAP_RECORD, am.poison(0x220, 0x44), bytes(0x220), writable=False)
        bmr.define(pt.BITMAP_RECORD+0x204, struct.pack('<ff', bm.width, bm.height))
        bmr.define(pt.BITMAP_RECORD+0x214, struct.pack('<b', bm.components))
        calls = []

        def bitmap_get(mm):
            calls.append(('bitmap', mm.argument(0)))
            return pt.BITMAP_RECORD, 4

        def wrapper(address, args):
            def stub(mm):
                calls.append(('state', address, mm.argument(0) if args else 0))
                return 0
            return stub

        def sprite(mm):
            a = [mm.argument(i) for i in range(11)]
            calls.append(('sprite', a[0], mm.floats(a[1], 3), pt.from_bits(a[2]), pt.from_bits(a[3]), mm.floats(a[4], 3),
                          pt.from_bits(a[5]), pt.from_bits(a[6]), pt.from_bits(a[7]), pt.from_bits(a[8]),
                          pt.from_bits(a[9]), a[10]))
            return 0
        stubs = pt.shared_stubs(case, m, {0x015ae351: pt.jump_stub(0x015ae363), 0x01591282: pt.jump_stub(0x015ae363),
                                          pt.BITMAP_GET: bitmap_get, pt.RENDER_SPRITE: sprite,
                                          pt.STATE_ADD: wrapper(pt.STATE_ADD, 0), pt.STATE_ALPHA: wrapper(pt.STATE_ALPHA, 1),
                                          pt.STATE_SUB: wrapper(pt.STATE_SUB, 0), pt.STATE_6B7: wrapper(pt.STATE_6B7, 0),
                                          pt.STATE_6DA: wrapper(pt.STATE_6DA, 0),
                                          pt.STATE_BLEND: wrapper(pt.STATE_BLEND, 0)})
        r = m.execute(0x015912e9, [0x5500 | mode], [record, bmr] + owner_regions + pt.globals_region(world_time=world_time),
                      stubs, ecx=pt.POOL, frame=pt.mid_frame(pt.RENDER_FRAME, {-0x60: n}), cleanup=4)
        rc = pt.RenderCall()
        mode_for_c = mode
        if follow and not ((mode == 1 and p.position[2] > 350.0) or (mode == 2 and 300.0 >= p.position[2])):
            # The split-pass height test precedes RenderParticles' owner-relative position write.
            lib.mu_pt_consumer34_follow(ctypes.byref(p), point)
            mode_for_c = 0
        drawn = lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), mode_for_c, world_time, n, ctypes.byref(rc))
        mine = []
        if drawn == 1:
            mine.append(('bitmap', p.tex_type))
            for k in range(rc.state_count):
                if rc.state[k] != pt.STATE_SUB:
                    mine.append(('state', rc.state[k], rc.state_arg[k]))
            for k in range(rc.state_count):
                if rc.state[k] == pt.STATE_SUB:
                    mine.append(('state', rc.state[k], rc.state_arg[k]))
            sp = rc.sprite
            if rc.sprites:
                mine.append(('sprite', sp.bitmap, list(sp.position), sp.width, sp.height, list(sp.light),
                             sp.rotation, sp.u, sp.v, sp.uw, sp.vh, sp.axes))
        mismatch = None
        if vc.ok(r) and (len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine))):
            mismatch = ('calls', calls, mine)
        if follow and vc.ok(r):
            raw, mask = pt.particle_bytes(lib, p)
            mismatch = mismatch or pt.compare_masked(raw, r['regions']['particle'], record.defined, mask,
                                                     pt.PARTICLE_FLOATS)
        equal = drawn != 2 and vc.ok(r) and mismatch is None
        report.add('render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode, 'mismatch': mismatch,
                                     'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('render', f'{kind[0]:#x}/{kind[1]}' + ('' if drawn == 1 and rc.sprites else ' no sprite'))


def particle_family(text, data, lib, name, cases, report, kinds=None):
    kinds = kinds or KINDS
    if name == 'render':
        render_family(pt.PtMachine(text, data), lib, random.Random('effects34-render'), cases * len(kinds), report, kinds)
        return
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle
    seen = defaultdict(int)

    def particle(rng, kind):
        index = seen[kind]
        seen[kind] += 1
        p = saved[2](rng, kind)
        if name == 'move':
            # The item and pulse forms divide by the constructor's lifetime words: keep them in the constructor's range
            # and sweep the record's lifetime across the halfway branch.
            life = {0x8616: 4, 0x7fe0: 16, 0x84d1: 30, 0x850b: 20, 0x807e: 20, 0x807f: 20, 0x8080: 20, 0x8081: 5,
                    0x8082: 5}.get(kind[0])
            if kind == (0x7ef7, 19): life = 7
            if kind == (0x855d, 2): life = 20 + index % 11
            if life:
                p.initial_lifetime = life
                p.lifetime = index % (life + 2)
                p.live = 1
            if kind == (0x7f5a, 47) and index % 3 == 0:
                p.light[0] = pt.f32(rng.choice([0.05, 0.051, 0.0509, 0.0511, 0.0]))
            if kind == (0x7efa, 3): p.lifetime = rng.choice([9, 10, 11, 12, 1, 20])
            if kind == (0x7ef7, 12): p.lifetime = rng.choice([81, 80, 79, 100, 50, 82, 2])
            if kind in ((0x7f5a, 50), (0x807e, 0)):
                p.lifetime = rng.choice([9, 10, 11, 20, 1, 30])
                p.alpha = pt.f32(rng.choice([0.0, 0.05, 0.1, 0.15, 0.45, 0.5, 0.55, 0.65, 0.7, 0.75, 0.3]))
            if kind == (0x8016, 5) and index % 4 == 0: p.scale = pt.f32(rng.choice([0.02, 0.01, 0.0199, 0.0201]))
        return p
    saved_world = pt.globals_region, pt.Case

    # CreateParticle's 0x807e/0 case reads the world (0x3f): one of the family's six worlds stands in for it.
    def globals_region(world=0, *a, **k):
        return saved_world[0](0x3f if world == 0x5d else world, *a, **k)

    class Case(saved_world[1]):
        def host(self, world=0, *a, **k):
            return super().host(0x3f if world == 0x5d else world, *a, **k)
    try:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle = kinds, set(), particle
        if name == 'create':
            pt.globals_region, pt.Case = globals_region, Case
        getattr(pt, 'family_'+name)(pt.PtMachine(text, data), lib, random.Random('effects34-'+name),
                                    cases * len(kinds), report, defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle = saved
        pt.globals_region, pt.Case = saved_world


def joint_family(text, data, lib, name, cases, report, kinds=None):
    kinds = kinds or JOINTS
    saved = jt.KINDS, jt.random_joint, jt.random_create_args

    def joint(rng, kind):
        j = saved[1](rng, kind)
        if kind == (0x7f7d, 11):
            # MoveJoint divides rand() by 2 * (int)(width / 8): the client faults below 8; the producers pass 15 * scale
            j.scale = pt.f32(rng.choice([15.0, 8.0, 16.0, 9.5, 40.0, rng.uniform(8.0, 60.0)]))
            j.max_tails = rng.choice([30, 30, 30, rng.randrange(6, 51)])
            j.lifetime = rng.choice([5, 4, 3, 1, 0])
        elif kind == (0x7f7c, 19):
            j.scale = pt.f32(rng.choice([10.0, 50.0, 49.5, 60.0, 5.0, rng.uniform(1.0, 80.0)]))
            j.max_tails = rng.choice([30, 30, rng.randrange(2, 51)])
            j.lifetime = rng.choice([2, 1, 0])
            j.velocity = pt.f32(j.scale * pt.f32(3.0))
        elif kind == (0x7f7c, 8):
            j.scale = pt.f32(5.0)
            j.max_tails = 2
            j.num_tails = rng.randrange(0, 2)
            j.lifetime = rng.randrange(-1, 16)
            j.velocity = pt.f32(rng.choice([6.0, 15.0, 0.0, rng.uniform(6.0, 15.0)]))
        elif kind == (0x7fd5, 4):
            j.max_tails = 4
            j.num_tails = rng.randrange(0, 4)
            j.scale = pt.f32(rng.choice([6.0, 5.0, 8.0]))
            j.velocity = pt.f32(rng.choice([4.0, 8.0, rng.uniform(4.0, 8.0)]))
        return j

    def create_args(rng, kind):
        pos, target, angle, scale = saved[2](rng, kind)
        if kind == (0x7f7d, 11):
            scale = pt.f32(rng.choice([15.0, 8.0, 30.0, rng.uniform(8.0, 60.0)]))
        return pos, target, angle, scale
    try:
        jt.KINDS, jt.random_joint, jt.random_create_args = kinds, joint, create_args
        getattr(jt, 'family_'+name)(fx.FxMachine(text, data), lib, random.Random('effects34-'+name),
                                    cases * len(kinds), report, defaultdict(int))
    finally:
        jt.KINDS, jt.random_joint, jt.random_create_args = saved


# Distinct greys per bitmap file: a swapped binding changes the uploaded image the host reports.
BITMAP_FILES = {
    'Effect/fantaF.OZJ': 100, 'Effect/flare01.OZJ': 104, 'Effect/smoke01.OZJ': 108, 'Effect/Clud64.OZJ': 112,
    'Effect/Explotion01.OZJ': 116, 'Effect/FireSphere1.OZJ': 120, 'Effect/flareRed.OZJ': 124,
    'Item/texture/smoke01_strong_red.OZJ': 132, 'Item/texture/smoke_line03_1.OZJ': 136,
    'Effect/smokelines01.OZJ': 140, 'Effect/smokelines02.OZJ': 144, 'Effect/smokelines03.OZJ': 148,
    'Effect/pin_star03_red.OZJ': 152, 'Effect/lighting_mega01.OZJ': 156, 'Effect/lighting_mega02.OZJ': 160,
    'Effect/pin_star02_yellow.OZJ': 164, 'Effect/Hole.OZJ': 168, 'Effect/JointThunder01.OZJ': 172,
    'Effect/Spark01.OZJ': 176, 'Effect/Magic_Ground2.OZJ': 180, 'Effect/Spark03.OZJ': 184, 'Effect/firehik01.OZJ': 188,
    'Effect/firehik02.OZJ': 192, 'Effect/firehik03.OZJ': 196,
}
SPRITE_GREYS = {0x810d: 164, 0x8003: 168, 0x8616: 120, 0x850b: 136}


def bitmap_fixture(directory):
    from PIL import Image
    root = Path(directory)/'game'
    for name, grey in BITMAP_FILES.items():
        path = root/'Data'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        Image.new('RGB', (32, 32), (grey, grey, grey)).save(buf, format='JPEG', quality=100)
        path.write_bytes(bytes(24) + buf.getvalue())
    return root


def build_host(directory, mutation=None):
    directory = Path(directory)
    native = ROOT/'native'
    obj, host = directory/'host.o', directory/'host'
    source = native/'tests/effects34_host.c'
    if mutation:
        old, new = mutation
        original = native/'core/mu_particles.c'
        code = original.read_text()
        if code.count(old) != 1:
            raise ValueError(old)
        code = code.replace(old, new)
        code = re.sub(r'#include "(\.\./[^"\n]+)"', lambda m: '#include "'+str((original.parent/m[1]).resolve())+'"', code)
        core = directory/'mutant.c'
        core.write_text(code)
        source = directory/'host.c'
        source.write_text((native/'tests/effects34_host.c').read_text().replace('../core/mu_particles.c', str(core))
                          .replace('../core/mu_png.h', str(native/'core/mu_png.h')))
    subprocess.run(['clang', '-std=c11', '-O1', '-ffp-contract=off', '-I', str(native/'build/gen'),
                    '-I', str(native/'session'), '-I', str(native/'core'), '-c', str(source), '-o', str(obj)],
                   check=True, capture_output=True)
    command = ['clang++', str(obj), str(native/'build/libmunative.a'), str(native/'build/libmusession_world.a'), '-lm',
               '-o', str(host)]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    subprocess.run(command, check=True, capture_output=True)
    return host


def native_checks(host, root, report, images=None):
    run = subprocess.run([str(host), str(root)] + ([str(images)] if images else []), capture_output=True, text=True)
    if run.returncode:
        report.add('native_particles', False, dict(exit=run.returncode, stderr=run.stderr[-2000:]))
        return
    for line in run.stdout.splitlines():
        row = json.loads(line)
        equal = bool(row.get('equal'))
        if row.get('sprite'):
            equal = equal and abs(row['grey'] - SPRITE_GREYS[row['kind']]) <= 2
        report.add('native_ledger' if row.get('ledger') else 'native_sprites' if row.get('sprite') else
                   'native_joints' if row.get('joint') else 'native_particles', equal, row)


NATIVE_MUTANTS = [
    ('native_follow_hook', 'else if (follow34) mu_pt_consumer34_follow(record, point);', 'else if (follow34) (void)point;'),
    ('native_sphere_file', '"Data/Effect/FireSphere1.OZJ", "Data/Item/texture/smoke_line03_1.OZJ",',
     '"Data/Item/texture/smoke_line03_1.OZJ", "Data/Effect/FireSphere1.OZJ",'),
    ('native_star_file', '"Data/Effect/pin_star02_yellow.OZJ", "Data/Effect/Hole.OZJ",',
     '"Data/Effect/Hole.OZJ", "Data/Effect/pin_star02_yellow.OZJ",'),
    ('native_ledger', "        refused_kind(p, 'p', type, subtype);", "        refused_kind(p, 'p', type, subtype + 1);"),
]


def census(lib, report):
    rows = []
    for group, kinds in GROUPS.items():
        for kind in kinds:
            supported = bool(lib.mu_pt_kind_supported(*kind))
            row = dict(category='particle', group=group, type=hex(kind[0]), subtype=kind[1], supported=supported)
            rows.append(row)
            report.add('census', supported, row)
    return rows


def run(cases, mutations=False, only_mutants=None):
    start = time.monotonic()
    text, data = pins.TEXT.read(), pins.DATA.read()
    lib = load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX))
    report = pt.Report()
    for name in ('create', 'move', 'render'):
        particle_family(text, data, lib, name, cases, report)
    jlib = jt.load_library(ROOT/('reconstructed/joints/libclient_joints.'+pt.SUFFIX))
    for name in ('joint_create', 'joint_move', 'joint_render'):
        joint_family(text, data, jlib, name, cases, report)
    with tempfile.TemporaryDirectory(prefix='effects34-native-') as tmp:
        native_checks(build_host(tmp), bitmap_fixture(tmp), report)
    rows = census(lib, report)
    for kind in JOINTS:
        supported = bool(jlib.mu_jt_kind_supported(*kind))
        row = dict(category='joint', group='joint', type=hex(kind[0]), subtype=kind[1], supported=supported)
        rows.append(row)
        report.add('census', supported, row)
    mutants = []
    if mutations and all(f['cases'] == f['equal'] for f in report.families.values()):
        with tempfile.TemporaryDirectory(prefix='effects34-mutants-') as tmp:
            for category, label, file, old, new, family, kind in MUTANTS:
                if only_mutants and label not in only_mutants:
                    continue
                r = pt.Report()
                if category == 'pt':
                    mutant = re11.compile_pt_mutant(tmp, label, file, old, new)
                    mutant.mu_pt_consumer34_follow.argtypes = [pt.P(pt.Particle), pt.FP]
                    mutant.mu_pt_consumer34_follow.restype = ctypes.c_int
                    particle_family(text, data, mutant, family, 120, r, [kind])
                else:
                    mutant = re31.compile_mutant(tmp, 'jt', label, file, old, new)
                    joint_family(text, data, mutant, family, 120, r, [kind])
                f = r.families[family]
                row = dict(name=label, detected=f['cases']-f['equal'],
                           stopped=sum(bool(v.get('stopped') or v.get('error')) for v in f['first_failures']))
                mutants.append(row)
                print('mutant', json.dumps(row), flush=True)
            for label, old, new in NATIVE_MUTANTS:
                if only_mutants and label not in only_mutants:
                    continue
                directory = Path(tmp)/label
                directory.mkdir()
                r = pt.Report()
                native_checks(build_host(directory, (old, new)), bitmap_fixture(directory), r)
                row = dict(name=label, detected=sum(f['cases']-f['equal'] for f in r.families.values()), stopped=0)
                mutants.append(row)
                print('mutant', json.dumps(row), flush=True)
    expected = sum(not only_mutants or m[1] in only_mutants for m in MUTANTS) + \
        sum(not only_mutants or m[0] in only_mutants for m in NATIVE_MUTANTS)
    return dict(mutant_subset=sorted(only_mutants) if only_mutants else None, families=report.families,
                coverage=report.coverage, census=rows,
                all_equal=all(f['cases'] == f['equal'] for f in report.families.values()),
                cases=sum(f['cases'] for f in report.families.values()), mutants=mutants,
                all_mutants_caught=(not mutations or len(mutants) == expected) and
                all(m['detected'] and not m['stopped'] for m in mutants),
                seconds=round(time.monotonic()-start, 3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cases', type=int, default=200, help='cases per pair and family')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    p.add_argument('--only-mutant', action='append', help='rerun one control without recompiling the others')
    args = p.parse_args()
    if args.cases < 1:
        p.error('--cases must be positive')
    if args.only_mutant and not args.mutations:
        p.error('--only-mutant requires --mutations')
    if args.only_mutant and set(args.only_mutant) - {m[1] for m in MUTANTS} - {m[0] for m in NATIVE_MUTANTS}:
        p.error('unknown mutant name')
    r = run(args.cases, args.mutations, set(args.only_mutant or []))
    if args.output:
        Path(args.output).write_text(json.dumps(r, indent=2))
    summary = {k: v for k, v in r.items() if k not in ('coverage', 'census')}
    print(json.dumps(summary, indent=2))
    return 0 if r['all_equal'] and r['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
