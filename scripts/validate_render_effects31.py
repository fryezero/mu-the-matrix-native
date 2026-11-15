#!/usr/bin/env python3
"""RENDER-EFFECTS-031: existing world producers' refused native consumers."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import tempfile
import time

import actor_machine as am
import pins
import validate_joints as jt
import validate_skill_fx as fx
import validate_particles as pt
import validate_render_effects11 as re11

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x801c, 3), (0x801c, 4), (0x801c, 7), (0x7f89, 7), (0x7f89, 10), (0x7f89, 26), (0x7f42, 7), (0x802a, 1)]
JOINTS = [(0x7f7d, 8), (0x7f7d, 9), (0x7f7d, 10), (0x7fd5, 5)]
MUTANTS = []


def particle_family(text, data, lib, name, cases, report, kinds=None):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case, pt.globals_region
    def particle(rng, kind):
        p = saved[2](rng, kind)
        if kind in ((0x7f89, 7), (0x7f89, 26)): p.owner = 0
        return p
    class Case(saved[3]):
        def host(self, world=0, world_time=0.0, *a, **kw):
            return super().host(world, 123456.0 if name == 'move' else world_time, *a, **kw)
    def globals_region(world=0, world_time=0.0, *a, **kw):
        return saved[4](world, 123456.0 if name == 'move' else world_time, *a, **kw)
    try:
        pt.KINDS = kinds or KINDS
        pt.OWNED_KINDS = {(0x7f89, 7), (0x7f89, 26)}
        pt.random_particle, pt.Case, pt.globals_region = particle, Case, globals_region
        getattr(pt, 'family_'+name)(pt.PtMachine(text, data), lib,
            random.Random('effects31-'+name), cases * len(pt.KINDS), report, defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case, pt.globals_region = saved


def joint_family(text, data, lib, name, cases, report, kinds=None):
    saved = jt.KINDS
    try:
        jt.KINDS = kinds or JOINTS
        getattr(jt, 'family_joint_'+name)(fx.FxMachine(text, data), lib,
            random.Random('effects31-joint-'+name), cases*len(jt.KINDS), report, defaultdict(int))
    finally:
        jt.KINDS = saved


def run(cases, mutations=False):
    start = time.monotonic()
    text, data = pins.TEXT.read(), pins.DATA.read()
    lib = pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX))
    report = pt.Report()
    for name in ('create', 'move', 'render'):
        particle_family(text, data, lib, name, cases, report)
    jlib = jt.load_library(ROOT/('reconstructed/joints/libclient_joints.'+pt.SUFFIX))
    for name in ('create', 'move', 'render'):
        joint_family(text, data, jlib, name, cases, report)
    mutants = []
    if mutations and all(f['cases'] == f['equal'] for f in report.families.values()):
        with tempfile.TemporaryDirectory(prefix='effects31-mutants-') as tmp:
            for label, old, new, family, kind in MUTANTS:
                mutant = re11.compile_pt_mutant(tmp, label, 'world_inner_kinds.inc', old, new)
                r = pt.Report()
                particle_family(text, data, mutant, family, 100, r, [kind])
                f = r.families[family]
                mutants.append(dict(name=label, detected=f['cases']-f['equal'], failures=f['first_failures']))
    return dict(families=report.families, coverage=report.coverage,
        all_equal=all(f['cases'] == f['equal'] for f in report.families.values()),
        cases=sum(f['cases'] for f in report.families.values()), mutants=mutants,
        all_mutants_caught=all(m['detected'] for m in mutants),
        seconds=round(time.monotonic()-start,3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true')
    p.add_argument('--output')
    args=p.parse_args()
    if args.cases < 1: p.error('--cases must be positive')
    r=run(args.cases,args.mutations)
    if args.output: Path(args.output).write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2))
    return 0 if r['all_equal'] and r['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
