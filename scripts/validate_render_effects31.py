#!/usr/bin/env python3
"""RENDER-EFFECTS-031: existing world producers' refused native consumers."""
import argparse
import io
import ctypes as C
import subprocess
import sys
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
KINDS = [(0x801c, 3), (0x801c, 4), (0x801c, 7), (0x7f89, 7), (0x7f89, 10), (0x7f89, 26), (0x7f89, 16), (0x7f42, 7), (0x802a, 1), (0x7f42, 12), (0x7f26, 2)]
JOINTS = [(0x7f7d, 8), (0x7f7d, 9), (0x7f7d, 10), (0x7fd5, 5), (0x7fd3, 2), (0x7f78, 2)]
MUTANTS = []


def particle_family(text, data, lib, name, cases, report, kinds=None):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case, pt.globals_region
    def particle(rng, kind):
        p = saved[2](rng, kind)
        if kind in ((0x7f89, 7), (0x7f89, 26), (0x7f26, 2)): p.owner = 0
        return p
    class Case(re11.OwnerCase):
        def host(self, world=0, world_time=0.0, *a, **kw):
            host = super().host(world, world_time, *a, **kw)
            host.world_time = 123456.0 if name == 'move' else world_time
            return host
    def globals_region(world=0, world_time=0.0, *a, **kw):
        return saved[4](world, 123456.0 if name == 'move' else world_time, *a, **kw)
    try:
        pt.KINDS = kinds or KINDS
        pt.OWNED_KINDS = {(0x7f89, 7), (0x7f89, 26), (0x7f26, 2)}
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


def bitmap_fixture(directory):
    from PIL import Image
    root = Path(directory)/'game'
    effect = root/'Data/Effect'
    effect.mkdir(parents=True)
    names = ['WATERFALL3','clouds','Flame01','water','JointThunder01','Spark01','JointSpirit01','Flare','flare01','Spark03','Shiny02']
    for name in names:
        buf = io.BytesIO()
        grey = 64 if name=='Flame01' else 192 if name=='water' else 128
        Image.new('RGB',(32,32),(grey,grey,grey)).save(buf,format='JPEG',quality=100)
        (effect/(name+'.OZJ')).write_bytes(bytes(24)+buf.getvalue())
    return root


def build_host(directory):
    directory = Path(directory)
    native = ROOT/'native'
    obj, host = directory/'host.o', directory/'host'
    subprocess.run(['clang','-std=c11','-O1','-ffp-contract=off','-I',str(native/'build/gen'),
        '-I',str(native/'session'),'-c',str(native/'tests/effects31_host.c'),'-o',str(obj)],
        check=True,capture_output=True)
    command=['clang++',str(obj),str(native/'build/libmunative.a'),str(native/'build/libmusession_world.a'),'-lm','-o',str(host)]
    if sys.platform=='darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp','-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
                    '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation']
    else: command += ['-lcryptopp','-ljpeg']
    subprocess.run(command,check=True,capture_output=True)
    return host


def native_checks(host, root, report, images=None):
    run=subprocess.run([str(host),str(root)]+([str(images)] if images else []),capture_output=True,text=True)
    if run.returncode:
        report.add('native_particles',False,dict(exit=run.returncode,stderr=run.stderr[-2000:]))
        return
    for line in run.stdout.splitlines():
        row=json.loads(line)
        report.add('native_joints' if row.get('joint') else 'native_particles',row['fragments']>0,row)


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
    flib = fx.load_library(ROOT/('reconstructed/combat/libcombat.'+pt.SUFFIX))
    saved = fx.EFFECT_KINDS
    try:
        fx.EFFECT_KINDS = [(0x7f84, 4), (0x47a, 0), (0x47a, 1), (0x7fd0, 0), (0x7f42, 6)]
        for name in ('effect_create', 'effect_move'):
            getattr(fx, 'family_'+name)(fx.FxMachine(text, data), flib,
                random.Random('effects31-'+name), cases*len(fx.EFFECT_KINDS), report, defaultdict(int))
    finally:
        fx.EFFECT_KINDS = saved
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
