#!/usr/bin/env python3
"""RENDER-EFFECTS-013: owner lifetime, Flare02/f and Shiny01/3 against pinned instructions."""
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
KINDS = [(0x80e3, 5), (0x7f79, 15)]
MUTANTS = [
    ('bow_joints.inc', 'if (j->subtype == 5) j->velocity = 70.0f;', 'if (j->subtype == 5) j->velocity = 40.0f;', 'joint_create'),
    ('bow_joints.inc', 'if (j->subtype == 4) {', 'if (1) {', 'joint_create'),
    ('bow_joints.inc', 'if (j->subtype == 15) j->max_tails = 16;', 'if (j->subtype == 15) j->max_tails = 9;', 'joint_create'),
    ('bow_joints.inc', 't->lifetime <= 0)', 't->lifetime < 0)', 'joint_move'),
    ('bow_joints.inc', 't->lifetime <= 0)', 't->lifetime <= 1)', 'joint_move'),
    ('bow_joints.inc', 'if (j->subtype == 15 && j->live == 1)', 'if (j->subtype == 15)', 'joint_move'),
    ('bow_joints.inc', 'for (int n = 0; n < 2; ++n)', 'for (int n = 0; n < 1; ++n)', 'joint_move'),
    ('bow_joints.inc', 'c.subtype = 3; c.owner = -1; c.scale = 0.5f;', 'c.subtype = 3; c.owner = -1; c.scale = 1.0f;', 'joint_move'),
]
PT_MUTANTS = [
    ('shiny_alpha', 'p->alpha = 1.0f; /* Shiny01/3 */', 'p->alpha = 0.5f; /* Shiny01/3 */'),
    ('shiny_velocity', '(float)(mu_pt_rand(h) % 8) - 4.0f;', '(float)(mu_pt_rand(h) % 8) - 3.0f;'),
    ('shiny_life', 'p->lifetime = 30; /* Shiny01/3 */', 'p->lifetime = 29; /* Shiny01/3 */'),
    ('shiny_size', '(float)(mu_pt_rand(h) % 10) / 20.0f + 0.5f;', '(float)(mu_pt_rand(h) % 10) / 10.0f + 0.5f;'),
    ('shiny_fade', 'p->light[k] /= 1.05f; /* Shiny01/3 */', 'p->light[k] /= 1.04f; /* Shiny01/3 */'),
    ('shiny_shrink', 'p->scale -= 0.04f; /* Shiny01/3 */', 'p->scale -= 0.03f; /* Shiny01/3 */'),
    ('shiny_alpha_step', 'p->alpha -= 0.001f; /* Shiny01/3 */', 'p->alpha -= 0.002f; /* Shiny01/3 */'),
    ('shiny_death', 'if (0.0f >= p->alpha) p->live = 0; /* Shiny01/3 */', 'if (0) p->live = 0; /* Shiny01/3 */'),
]


def configure():
    re12.configure()
    jt.KINDS = list(KINDS)
    jt.KANTURU_KINDS = list(KINDS)
    old_object = jt.random_object
    def object_record(rng):
        o = old_object(rng)
        o.lifetime = rng.choice([-2147483648, -1, 0, 1, 2, 20, 2147483647])
        return o
    jt.random_object = object_record
    old_region = jt.object_region
    def region(objects):
        r = old_region(objects)
        for i, o in enumerate(objects):
            r.define(jt.OBJECTS + 0x400*i + 0x6c, struct.pack('<i', o.lifetime))
        return r
    jt.object_region = region
    pt.KINDS = [(0x7f66, 3)]


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
    start = time.monotonic()
    for name, family in jt.FAMILIES:
        family(m, lib, re12.BowRandom('effects13-' + name), a.cases*len(KINDS), r, jt.collections_default())
    for name in ('create', 'move', 'render'):
        getattr(pt, 'family_' + name)(pm, plib, random.Random('effects13-' + name), a.cases, r, jt.collections_default())
    equal = all(f['equal'] == f['cases'] for f in r.families.values())
    mutants = []
    if a.mutations and equal:
        jt.MUTANTS = MUTANTS
        mutants = jt.run_mutants(m, 180, 20261108)
        with tempfile.TemporaryDirectory(prefix='effects13-mutants-') as tmp:
            for name, old, new in PT_MUTANTS:
                ml = re11.compile_pt_mutant(Path(tmp), name, 'particles.c', old, new)
                rr = jt.vc.Report()
                family = 'move' if name in ('shiny_fade','shiny_shrink','shiny_alpha_step','shiny_death') else 'create'
                getattr(pt, 'family_' + family)(pm, ml, random.Random(name), 60, rr, jt.collections_default())
                f = rr.families[family]
                mutants.append(dict(name=name, cases=f['cases'], detected=f['cases']-f['equal'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
    result = dict(families=r.families, coverage=r.coverage, instruction_cases=sum(f['cases'] for f in r.families.values()),
                  all_equal=equal, mutants=mutants,
                  all_mutants_caught=all(x['detected'] and not x['stopped'] for x in mutants),
                  seconds=round(time.monotonic()-start,3), text_sha256=jt.am.TEXT_SHA256, data_sha256=jt.am.DATA_SHA256)
    if a.output: Path(a.output).write_text(json.dumps(result,indent=1))
    print(json.dumps(result,indent=1))
    return 0 if equal and result['all_mutants_caught'] else 1

if __name__ == '__main__': raise SystemExit(main())
