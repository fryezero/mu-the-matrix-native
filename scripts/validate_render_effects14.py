#!/usr/bin/env python3
"""RENDER-EFFECTS-014: Flare/b (arrow 0x459), Flare02/e (arrow 0x45a), smoke01 0x22/0x23 and Spark03 0xa
against the pinned instructions.

Joint 0x7f78/b moves on the ambient clock [0x0bdc5eb0] and the pool ordinal, pulls toward its owner's +0x110,
plays sound 0x42 at lifetime 30 and, for the joint created with skill 1, writes the owner's +0x158 and runs
CheckClientArrow 0x013bd374. The stub of that routine reads the owner's position when it is called, so the
write-back is compared through the reported call, and the rest of the object region must stay unchanged.
"""
import argparse
import ctypes
import json
from pathlib import Path
import random
import struct
import tempfile
import time
import validate_joints as jt
import validate_particles as pt
import validate_render_effects12 as re12
import validate_render_effects11 as re11

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x7f78, 11), (0x7f79, 14)]
PT_KINDS = [(0x7f5a, 0x22), (0x7f5a, 0x23), (0x7f26, 0xa)]
CLOCK = 0x0bdc5eb0
MUTANTS = [
    ('bow_joints.inc', 'j->lifetime = 30; /* Flare/b */', 'j->lifetime = 31; /* Flare/b */', 'joint_create'),
    ('bow_joints.inc', 'j->max_tails = 15; /* Flare/b */', 'j->max_tails = 16; /* Flare/b */', 'joint_create'),
    ('bow_joints.inc', 'j->scale = 30.0f; /* Flare/b */', 'j->scale = 10.0f; /* Flare/b */', 'joint_create'),
    ('bow_joints.inc', 'j->light[0] = 0.2f; j->light[1] = 0.2f; j->light[2] = 1.0f; /* Flare/b */',
     'j->light[0] = 0.2f; j->light[1] = 0.2f; j->light[2] = 0.5f; /* Flare/b */', 'joint_create'),
    ('bow_joints.inc', 'j->jitter[0] = (float)imod(jrand(env), 3000);', 'j->jitter[0] = (float)imod(jrand(env), 300);',
     'joint_create'),
    ('bow_joints.inc', 'j->light[0] = j->light[1] = j->light[2] = 1.0f;\n            j->max_tails = 16;',
     'j->light[0] = j->light[1] = j->light[2] = 0.5f;\n            j->max_tails = 16;', 'joint_create'),
    ('bow_joints.inc', '(uint32_t)(index % 2 != 0 ? clock : -(int64_t)clock)', '(uint32_t)clock', 'joint_move'),
    ('bow_joints.inc', 'v[k] = v[k] * 1.5f; /* Flare/b rates */', 'v[k] = v[k] * 1.0f; /* Flare/b rates */', 'joint_move'),
    ('bow_joints.inc', 'd[1] = s * r1 + co * r2;', 'd[1] = s * r1 - co * r2;', 'joint_move'),
    ('bow_joints.inc', 'float blend = 20.0f > q ? q * 4.0f : q * 1.0f + 60.0f;',
     'float blend = 10.0f > q ? q * 7.0f : q * 1.0f + 60.0f;', 'joint_move'),
    ('bow_joints.inc', '(float)(int32_t)((uint32_t)j->phase + 30u) * 30.0f', '(float)30 * 30.0f', 'joint_move'),
    ('bow_joints.inc', 'if (j->lifetime == 30) {', 'if (j->lifetime == 29) {', 'joint_move'),
    ('bow_joints.inc', 'reach = 150.0f > reach * 5.0f ? reach * 5.0f : 150.0f; /* Flare/b reach */',
     'reach = 150.0f > reach * 15.0f ? reach * 15.0f : 150.0f; /* Flare/b reach */', 'joint_move'),
    ('bow_joints.inc', '(fcos((float)w * 0.01f) * 25.0f + t->impact[k])', '(fcos((float)w * 0.01f) * 25.0f + t->position[k])',
     'joint_move'),
    ('bow_joints.inc', '(uint32_t)((int32_t)c / 10)', '(uint32_t)((int32_t)c / 100)', 'joint_move'),
    ('bow_joints.inc', 'if (j->skill == 1) {', 'if (j->skill != 0) {', 'joint_move'),
    ('bow_joints.inc', 'const float light[3] = {0.3f, 0.3f, 0.5f}; /* Flare/b sprites */',
     'const float light[3] = {0.5f, 0.5f, 1.0f}; /* Flare/b sprites */', 'joint_move'),
    ('bow_joints.inc', '(n == 0 ? F_0_1 : f32bits(0x3e3851ecu))', '(n == 0 ? F_0_1 : F_0_1)', 'joint_move'),
    ('bow_joints.inc', 'if (!t->live) { j->live = 0; j->lifetime = -1; return; }',
     'if (!t->live) { j->live = 0; return; }', 'joint_move'),
    ('bow_joints.inc', '    /* 0x0157c24e: subtypes 5, 7 and 0xb skip the last-ten-steps fade */',
     '    if (j->lifetime < 10) for (int k = 0; k < 3; ++k) j->light[k] = j->light[k] / 1.3f;', 'joint_move'),
    ('bow_joints.inc', 'c.subtype = 0x23; jcall(env, &c); /* Flare02/e smoke */', '/* Flare02/e smoke */', 'joint_move'),
    ('bow_joints.inc', 'j->light[0] = 0.7f; j->light[1] = 0.3f; j->light[2] = 0.3f; /* Flare02/e spark colour */',
     'j->light[0] = 0.3f; j->light[1] = 0.3f; j->light[2] = 0.7f; /* Flare02/e spark colour */', 'joint_move'),
    ('bow_joints.inc', 'j->light[0] = 1.0f; j->light[1] = 1.0f; j->light[2] = 0.2f; /* Flare02/e after */',
     '/* Flare02/e after */', 'joint_move'),
    ('bow_joints.inc', 'c.routine = MU_JT_CALL_SPRITE; c.type = 0x7f26; c.scale = 5.0f;',
     'c.routine = MU_JT_CALL_SPRITE; c.type = 0x7f26; c.scale = 4.0f;', 'joint_move'),
]
PT_MUTANTS = [
    ('smoke_light', 'p->light[0] = 1.0f; p->light[1] = 0.2f; p->light[2] = 0.2f; /* smoke01/0x22 */',
     '/* smoke01/0x22 */', 'create'),
    ('smoke_life', 'p->lifetime = 30; /* smoke01/0x22 */', 'p->lifetime = 20; /* smoke01/0x22 */', 'create'),
    ('smoke_velocity', 'p->velocity[1] = subtype == 0x23 ? -5.0f : 0.0f; /* smoke01/0x23 */',
     'p->velocity[1] = subtype == 0x23 ? 5.0f : 0.0f; /* smoke01/0x23 */', 'create'),
    ('smoke_fade', 'p->light[k] /= 1.04f; /* smoke01/0x22 */', 'p->light[k] /= 1.05f; /* smoke01/0x22 */', 'move'),
    ('smoke_grow', 'p->scale += 0.06f; /* smoke01/0x22 */', 'p->scale += 0.05f; /* smoke01/0x22 */', 'move'),
    ('spark_alpha', 'p->alpha = 1.0f; /* Spark03/0xa */', 'p->alpha = 0.5f; /* Spark03/0xa */', 'create'),
    ('spark_z', 'p->velocity[2] = (float)(mu_pt_rand(h) % 8) + -4.0f; /* Spark03/0xa z */',
     'p->velocity[2] = (float)(mu_pt_rand(h) % 4); /* Spark03/0xa z */', 'create'),
    ('spark_life', 'p->lifetime = 20; /* Spark03/0xa */', 'p->lifetime = 30; /* Spark03/0xa */', 'create'),
    ('spark_size', 'p->scale = (float)(mu_pt_rand(h) % 5) / 10.0f + 1.0f; /* Spark03/0xa */',
     'p->scale = (float)(mu_pt_rand(h) % 5) / 20.0f + 1.0f; /* Spark03/0xa */', 'create'),
    ('spark_fade', 'p->light[k] /= 1.08f; /* Spark03/0xa */', 'p->light[k] /= 1.05f; /* Spark03/0xa */', 'move'),
    ('spark_shrink', 'p->scale -= 0.03f; /* Spark03/0xa */', 'p->scale -= 0.04f; /* Spark03/0xa */', 'move'),
    ('spark_alpha_step', 'p->alpha -= 0.001f; /* Spark03/0xa */', 'p->alpha -= 0.002f; /* Spark03/0xa */', 'move'),
    ('spark_death', 'if (0.0f >= p->alpha) p->live = 0; /* Spark03/0xa */', 'if (0.0f > p->alpha) p->live = 0; /* Spark03/0xa */',
     'move'),
]


_base_object = jt.random_object


def random_object(rng):
    o = _base_object(rng)
    o.lifetime = rng.choice([-1, 0, 1, 30])
    for k in range(3):
        o.impact[k] = jt.vc.rfloat(rng, 0.05, 30000.0) if k < 2 else jt.vc.rfloat(rng, 0.05, 600.0)
    return o


def object_region(objects, writable=False):
    r = jt.object_region(objects)
    r.writable = writable
    for i, o in enumerate(objects):
        r.define(jt.OBJECTS + 0x400*i + 0x6c, struct.pack('<i', o.lifetime))
        r.define(jt.OBJECTS + 0x400*i + 0x110, struct.pack('<3f', *o.impact))
    return r


class Case(jt.Case):
    """validate_joints' case plus the sound and the owner's arrow check (with its written position)."""

    def stubs(self, m):
        s = super().stubs(m)

        def check_arrow(mm):
            o = mm.argument(0)
            self.client_calls.append(('check_arrow', jt.sf.owner_of(o), mm.floats(o + 0x158, 3)))
            return 0
        s[jt.sf.CHECK_ARROW] = check_arrow
        return s

    def jenv(self, serial=0):
        env = super().jenv(serial)
        inner = self._jkeep[3]

        def call(ctx, cp):
            c = cp.contents
            if c.routine == jt.sf.PLAY_BUFFER:
                self.c_calls.append(('sound', c.type, -1, 0))
            elif c.routine == jt.sf.CHECK_ARROW:
                self.c_calls.append(('check_arrow', c.owner, list(c.position)))
            else:
                inner(ctx, cp)
        self._jkeep = self._jkeep[:3] + (jt.CALL_FN(call), inner)
        env.call = self._jkeep[3]
        return env


def random_flare_joint(rng, kind):
    j = jt.random_joint(rng, kind)
    if kind == (0x7f78, 11):
        j.scale = jt.f32(30.0)
        j.max_tails = rng.choice([15, 15, rng.randrange(2, 51)])
        j.lifetime = rng.choice([30, 30, 29, 23, 15, 11, 10, 9, 8, 1, 0, rng.randrange(-1, 31)])
        j.velocity = jt.f32(rng.choice([0.0, 0.0, 0.0, 5.0]))
        j.skill = rng.choice([0, 1, 1, 2])
        j.phase = rng.choice([0, 0, 0, 1, 5, -29, rng.randrange(-5, 40)])
    else:
        j.lifetime = rng.choice([40, 39, 16, 15, 14, 1, 0, rng.randrange(-1, 41)])
        j.max_tails = rng.choice([16, 16, rng.randrange(2, 51)])
        j.velocity = jt.f32(rng.choice([70.0, 70.0, 0.0]))
        j.skill = rng.choice([0, 1, 3])
    return j


def family_joint_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = jt.KINDS[n % len(jt.KINDS)]
        objects = [random_object(rng) for _ in range(2)]
        j = random_flare_joint(rng, kind) if kind in KINDS else jt.random_joint(rng, kind)
        step = jt.vc.rfloat(rng, 0.1, 2.0)
        world_time = jt.world_time_value(rng)
        case = Case(rng, objects, jt.rand_values(rng), jt.vc.rfloat(rng, 0.1, 400.0), world_time)
        raw, mask = jt.joint_to_bytes(j, jt.ALL_NAMES | {'target'})
        record = jt.am.Region('joint', jt.JOINT_POOL, raw, mask)
        index = rng.choice([0, 1, 2, 3, 498, 499, rng.randrange(0, 500)])
        clock = rng.choice([0, 1, -1, -2147483648, 2147483647, rng.randrange(0, 200000),
                            rng.randrange(-10000000, 10000000)])
        objects_in = object_region(objects, writable=True)
        regions = [record, objects_in,
                   jt.am.defined_region('time-step', jt.sf.TIME_STEP, struct.pack('<f', step), writable=False),
                   jt.am.defined_region('wall-scene', jt.sf.WALL_SCENE, bytes([0]), writable=False),
                   jt.am.defined_region('hero', jt.sf.HERO_POINTER, struct.pack('<I', 0x5000000), writable=False),
                   jt.am.defined_region('world-time', jt.WORLD_TIME, struct.pack('<f', world_time), writable=False),
                   jt.am.defined_region('ambient-clock', CLOCK, struct.pack('<i', clock), writable=False)]
        stubs = case.stubs(m)
        before = jt.Joint.from_buffer_copy(j)
        r = m.execute(jt.MOVE_JOINT, [jt.JOINT_POOL, index], regions, stubs)
        env = case.jenv()
        env.ambient_clock = clock
        inputs = jt.MoveInputs(step, 0, 0, index, 0)
        supported = lib.mu_jt_move(ctypes.byref(j), ctypes.byref(env), ctypes.byref(inputs))
        mismatch = None
        if jt.vc.ok(r):
            out = r['regions']['joint']
            mismatch = jt.compare_joint(j, out, record.defined, jt.ALL_NAMES)
            if mismatch is None:
                mismatch = jt.sf.compare_calls(jt.heal_sprite_tail(case.client_calls), jt.heal_sprite_tail(case.c_calls))
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None:
                # the owner's +0x158 is the only object write, and only by the reported arrow check
                expect = bytearray(objects_in.data)
                for c in case.c_calls:
                    if c[0] == 'check_arrow':
                        struct.pack_into('<3f', expect, 0x400*c[1] + 0x158, *c[2])
                got = r['regions']['objects']
                if any(objects_in.defined[k] and got[k] != expect[k] for k in range(len(expect))):
                    mismatch = ('object write', next(hex(k) for k in range(len(expect))
                                                     if objects_in.defined[k] and got[k] != expect[k]))
        equal = supported and jt.vc.ok(r) and mismatch is None
        report.add('joint_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                         'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        live_owner = before.target >= 0 and objects[before.target].live
        report.cover('joint_move', f'{kind[0]:#x}/{kind[1]:#x}' + (' owner' if live_owner else ' no-owner'))
        for c in {c[0] if c[0] != 'particle' else f'particle {c[1]:#x}/{c[5]:#x}' for c in case.client_calls}:
            report.cover('joint_move', f'{kind[0]:#x}/{kind[1]:#x} {c}')
        if jt.vc.ok(r) and kind == (0x7f78, 11) and live_owner:
            arrow = [c for c in case.client_calls if c[0] == 'check_arrow']
            negatives['flare_check_without_skill1'] += bool(arrow) != (before.skill == 1)
            negatives['flare_sound_off_30'] += any(c[0] == 'sound' for c in case.client_calls) != (before.lifetime == 30)


def configure():
    re12.configure()
    jt.KINDS = list(KINDS)
    jt.KANTURU_KINDS = list(KINDS)
    jt.random_object = random_object
    jt.object_region = (lambda old: (lambda objects: _region(old, objects)))(jt.object_region)
    jt.FAMILIES = [('joint_create', jt.family_joint_create), ('joint_move', family_joint_move),
                   ('joint_render', jt.family_joint_render)]
    pt.KINDS = list(PT_KINDS)
    old_particle = pt.random_particle

    def particle_record(rng, kind):
        p = old_particle(rng, kind)
        p.alpha = pt.f32(rng.choice([-0.1, 0.0, 0.001, 0.002, 0.5, 1.0]))
        return p
    pt.random_particle = particle_record


def _region(old, objects):
    r = old(objects)
    for i, o in enumerate(objects):
        r.define(jt.OBJECTS + 0x400*i + 0x6c, struct.pack('<i', o.lifetime))
        r.define(jt.OBJECTS + 0x400*i + 0x110, struct.pack('<3f', *o.impact))
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=300)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    configure()
    text = jt.am.load_pinned(jt.pins.TEXT.default_str(), jt.am.TEXT_BYTES, jt.am.TEXT_SHA256, 'text')
    data = jt.am.load_pinned(jt.pins.DATA.default_str(), jt.am.DATA_BYTES, jt.am.DATA_SHA256, 'data')
    m = jt.sf.FxMachine(text, data)
    pm = pt.PtMachine(text, data)
    lib = jt.load_library(ROOT/f'reconstructed/joints/libclient_joints.{jt.SUFFIX}')
    plib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{jt.SUFFIX}')
    r = jt.vc.Report()
    negatives = jt.collections_default()
    start = time.monotonic()
    for name, family in jt.FAMILIES:
        family(m, lib, re12.BowRandom('effects14-' + name), a.cases*len(KINDS), r, negatives)
    for name in ('create', 'move', 'render'):
        getattr(pt, 'family_' + name)(pm, plib, random.Random('effects14-' + name), a.cases*len(PT_KINDS), r,
                                      jt.collections_default())
    equal = all(f['equal'] == f['cases'] for f in r.families.values())
    print(json.dumps(dict(instruction_cases=sum(f['cases'] for f in r.families.values()), all_equal=equal,
                          families={k: (v['cases'], v['equal']) for k, v in r.families.items()},
                          negatives=dict(negatives))), flush=True)
    mutants = []
    if a.mutations and equal:
        jt.MUTANTS = MUTANTS
        mutants = jt.run_mutants(m, 120, 20261114)
        with tempfile.TemporaryDirectory(prefix='effects14-mutants-') as tmp:
            for name, old, new, family in PT_MUTANTS:
                ml = re11.compile_pt_mutant(Path(tmp), name, 'particles.c', old, new)
                rr = jt.vc.Report()
                getattr(pt, 'family_' + family)(pm, ml, random.Random(name), 90, rr, jt.collections_default())
                f = rr.families[family]
                mutants.append(dict(name=name, family=family, cases=f['cases'], detected=f['cases']-f['equal'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
    result = dict(families=r.families, coverage=r.coverage, negatives=dict(negatives),
                  instruction_cases=sum(f['cases'] for f in r.families.values()), all_equal=equal, mutants=mutants,
                  all_mutants_caught=all(x['detected'] and not x['stopped'] for x in mutants),
                  seconds=round(time.monotonic()-start, 3), text_sha256=jt.am.TEXT_SHA256, data_sha256=jt.am.DATA_SHA256)
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ('families', 'coverage')}, indent=1))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
