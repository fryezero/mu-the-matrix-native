#!/usr/bin/env python3
"""RENDER-EFFECTS-012: bow joint records and full GL streams against pinned instructions."""
import argparse
import ctypes
import json
from pathlib import Path
import random
import time
import tempfile
import validate_render_effects7 as re7
import validate_joints as jt

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x80e3, 4), (0x80e4, 1), (0x814c, 10), (0x8182, 10), (0x8185, 10),
         (0x85cc, 0), (0x828c, 2), (0x7f79, 12), (0x7f79, 18), (0x7f79, 22)]
MUTANTS = [
    ('joints.c', '(float)j->max_tails * 2.0f;', '(float)j->max_tails * 1.5f;', 'joint_render'),
    ('bow_joints.inc', 'j->num_tails = -1;', 'j->num_tails = 0;', 'joint_create'),
    ('bow_joints.inc', 'd[k] * 15.0f;', 'd[k] * 14.0f;', 'joint_move'),
    ('bow_joints.inc', 'j->lifetime = 20;', 'j->lifetime = 21;', 'joint_create'),
    ('bow_joints.inc', 'j->velocity = 40.0f;', 'j->velocity = 41.0f;', 'joint_create'),
    ('bow_joints.inc', 'j->field_a25 = 2;', 'j->field_a25 = 1;', 'joint_create'),
    ('bow_joints.inc', 'j->faces = 2;', 'j->faces = 3;', 'joint_create'),
    ('bow_joints.inc', 'j->velocity = 60.0f;', 'j->velocity = 61.0f;', 'joint_create'),
    ('bow_joints.inc', 'j->lifetime = 30;', 'j->lifetime = 31;', 'joint_create'),
    ('bow_joints.inc', 'j->type == 0x814c ? 8 : 10;', 'j->type == 0x814c ? 9 : 10;', 'joint_create'),
    ('bow_joints.inc', 'j->field_a25 = 5;', 'j->field_a25 = 4;', 'joint_create'),
    ('bow_joints.inc', 'j->lifetime = (int16_t)j->key;', 'j->lifetime = j->key;', 'joint_create'),
    ('bow_joints.inc', 'j->key = 0;', 'j->key = 1;', 'joint_create'),
    ('bow_joints.inc', 'j->subtype == 12 ? 4 : 1;', 'j->subtype == 12 ? 1 : 1;', 'joint_create'),
    ('bow_joints.inc', 'if (!t || !t->live) j->lifetime = 0;', 'if (!t) j->lifetime = 0;', 'joint_move'),
    ('bow_joints.inc', 'j->live = 0; return 1;', 'j->live = 0; return 0;', 'joint_move'),
    ('bow_joints.inc', 'if (j->lifetime < 15)', 'if (j->lifetime < 14)', 'joint_move'),
    ('bow_joints.inc', 'if (j->subtype != 18)', 'if (j->subtype == 18)', 'joint_move'),
    ('bow_joints.inc', 'l * 0.8f;', 'l * 0.7f;', 'joint_move'),
]


class BowRandom(random.Random):
    def choice(self, values):
        # The shared create family normally samples unrelated skill keys. Include the bow
        # callers' skill 0 and the Flare02 skill-1 palette; skill 3 needs a non-null owner.
        if values == [0x7f5, 9, 0x123]:
            values = [0, 1, 9, 0x123]
        return super().choice(values)


def configure():
    """Use the existing instruction families, adding null/coloured creates and the actual UV modes.

    0x814c/0x8182/0x8185 move calls a method through the target unconditionally;
    their move domain requires an owner, both live and dead. Other kinds include null owners.
    """
    jt.KINDS = list(KINDS)
    jt.KANTURU_KINDS = list(KINDS)
    jt.kanturu_width = lambda rng, kind, create: jt.f32(rng.choice([0.0, 5.0, 20.0, 80.0, 100.0]))
    original = jt.random_joint
    def record(rng, kind):
        j = original(rng, (0x7fd3, 0))
        j.type, j.tex_type, j.subtype = kind[0], kind[0], kind[1]
        j.lifetime = rng.choice([30, 20, 15, 14, 1, 0, -1, rng.randrange(1, 40)])
        j.max_tails = rng.choice([7, 8, 9, 10, 16])
        j.num_tails = rng.randrange(0, j.max_tails)
        j.faces = rng.choice([1, 2, 3])
        j.render_type = 4 if kind == (0x7f79, 12) else 1
        j.field_a25 = 2 if kind[0] in (0x80e3, 0x828c) else 5 if kind[0] == 0x85cc else 0
        if kind[0] in (0x814c, 0x8182, 0x8185): j.target = rng.choice([0, 1])
        return j
    jt.random_joint = record


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
    lib = jt.load_library(ROOT / f'reconstructed/joints/libclient_joints.{jt.SUFFIX}')
    report = jt.vc.Report()
    start = time.monotonic()
    for name, family in jt.FAMILIES:
        family(m, lib, BowRandom('effects12-' + name), a.cases * len(KINDS), report, jt.collections_default())
    fxlib = jt.sf.load_library(ROOT / f'reconstructed/combat/libcombat.{jt.SUFFIX}')
    for name, family in [('effect_create', re7.family_create), ('effect_move', re7.family_move)]:
        family(m, fxlib, random.Random('effects12-' + name), a.cases, report, [(0x38b5, 1)])
    equal = all(f['equal'] == f['cases'] for f in report.families.values())
    mutants = []
    if a.mutations and equal:
        jt.MUTANTS = MUTANTS
        mutants = jt.run_mutants(m, 180, 20261107)
        with tempfile.TemporaryDirectory(prefix='effects12-mutants-') as tmp:
            for name, old, new, family in [
                ('multishot_life', 'e->lifetime = 13;', 'e->lifetime = 12;', re7.family_create),
                ('multishot_growth', 'e->scale = e->scale + 0.1f;', 'e->scale = e->scale + 0.2f;', re7.family_move),
                ('multishot_fade', 'e->blend_light = (float)e->lifetime / 18.0f;',
                 'e->blend_light = (float)e->lifetime / 17.0f;', re7.family_move),
            ]:
                mutant = re7.compile_mutant(Path(tmp), name, old, new)
                rr = jt.vc.Report()
                family(m, mutant, random.Random('effects12-mutant'), 40, rr, [(0x38b5, 1)])
                fam = next(iter(rr.families.values()))
                mutants.append(dict(name=name, cases=fam['cases'], detected=fam['cases']-fam['equal'],
                                    stopped=sum(bool(f.get('stopped')) for f in fam['first_failures'])))
    result = dict(families=report.families, coverage=report.coverage,
                  instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                  mutants=mutants, all_mutants_caught=all(x['detected'] and not x['stopped'] for x in mutants),
                  seconds=round(time.monotonic()-start, 3), text_sha256=jt.am.TEXT_SHA256, data_sha256=jt.am.DATA_SHA256)
    print(json.dumps(result, indent=1))
    if a.output: Path(a.output).write_text(json.dumps(result, indent=1))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
