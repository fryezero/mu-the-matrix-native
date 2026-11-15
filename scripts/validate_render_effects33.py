#!/usr/bin/env python3
"""RENDER-EFFECTS-033: table-driven learned-skill consumers, pinned instructions."""
import ctypes as C
import argparse
import struct
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import tempfile
import time
import pins
import validate_combat as vc
import validate_particles as pt
import validate_skill_fx as fx
import validate_render_effects31 as previous
import validate_joints as jt
from validate_render_effects12 import BowRandom

ROOT=Path(__file__).resolve().parents[1]
EFFECTS=[(0x7f84,3),(0x46c,0),(0x412,1),(0x412,2)]
JOINTS=[(0x7fd8,3)]+[(0x7f79,s) for s in range(4)]
MUTANTS=[('summon_ground', 'skill_fx.c', 'sub == 1 || sub == 3 || sub == 4',
          'sub == 1 || sub == 4', 'effect_create', (0x7f84,3))]

def owner_region(original, objects):
    r=original(objects)
    for i,o in enumerate(objects):
        r.define(fx.OBJECTS+0x400*i+0x110,struct.pack('<3f',*o.impact))
        r.define(fx.OBJECTS+0x400*i+0x170,struct.pack('<3f',*o.heading))
        r.define(fx.OBJECTS+0x400*i+0x2a,struct.pack('<H',o.action))
    return r

def effect_family(text,data,lib,name,cases,report,kinds=None):
    saved=fx.EFFECT_KINDS,fx.OWNED_KINDS,fx.object_region,fx.MOVE_DEFINED,fx.Case
    class Machine(fx.FxMachine):
        def execute(self,address,args,regions,*a,**kw):
            if address==fx.CREATE_EFFECT and args[0]==0x412 and args[1] in (1,2):
                for r in regions:
                    if r.name=='inputs':r.writable=True
            return super().execute(address,args,regions,*a,**kw)
    class Case(saved[4]):
        def __init__(self,rng,objects,*a,**kw):
            for o in objects:
                o.action=rng.choice([0,2,0x31,0x32,0x6e,0x6f])
                o.heading[:]=[rng.uniform(-180,180) for _ in range(3)]
                o.impact[:]=[rng.uniform(-200,200) for _ in range(3)]
            self.presence=rng.choice([0,1])
            super().__init__(rng,objects,*a,**kw)
        def stubs(self,m):
            stubs=super().stubs(m);stubs[0x1295ade]=lambda mm:(self.presence,4)
            return stubs
        def env(self,*a,**kw):
            env=super().env(*a,**kw);base=self._keep[3]
            def call(ctx,cp,ep):
                if cp.contents.routine==0x1295ade:return self.presence
                return base(ctx,cp,ep)
            self.presence_call=fx.CALL_FN(call);env.call=self.presence_call;return env
    try:
        fx.EFFECT_KINDS=kinds or EFFECTS
        fx.OWNED_KINDS=saved[1] | {0x46c}
        fx.object_region=lambda objects:owner_region(saved[2],objects)
        fx.MOVE_DEFINED=saved[3] | {'impact','heading_yz','field_68'}
        fx.Case=Case
        getattr(fx,'family_'+name)(Machine(text,data),lib,random.Random('effects33-'+name),
            cases*len(fx.EFFECT_KINDS),report,defaultdict(int))
    finally:fx.EFFECT_KINDS,fx.OWNED_KINDS,fx.object_region,fx.MOVE_DEFINED,fx.Case=saved

def joint_family(text,data,lib,name,cases,report,kinds=None):
    saved=jt.KINDS,jt.random_joint,jt.object_region
    def record(rng,kind):
        j=saved[1](rng,kind)
        if kind[0]==0x7f79:
            j.max_tails=50; j.num_tails=rng.choice([0,1,47,48,49]);j.velocity=float(240 if kind[1]==3 else kind[1]*90)
            j.jitter[:]=[rng.uniform(-50,50),0,0]
        return j
    try:
        jt.KINDS=kinds or JOINTS; jt.random_joint=record
        jt.object_region=lambda objects:owner_region(saved[2],objects)
        getattr(jt,'family_'+name)(fx.FxMachine(text,data),lib,BowRandom('effects33-'+name),
            cases*len(jt.KINDS),report,defaultdict(int))
    finally:jt.KINDS,jt.random_joint,jt.object_region=saved

def run(cases,mutations=False):
    start=time.monotonic();text,data=pins.TEXT.read(),pins.DATA.read();report=pt.Report()
    lib=fx.load_library(ROOT/('reconstructed/combat/libcombat.'+fx.SUFFIX))
    for name in ('effect_create','effect_move'):effect_family(text,data,lib,name,cases,report)
    jlib=jt.load_library(ROOT/('reconstructed/joints/libclient_joints.'+fx.SUFFIX))
    for name in ('joint_create','joint_move','joint_render'):joint_family(text,data,jlib,name,cases,report)
    mutants=[]
    if mutations and all(f['cases']==f['equal'] for f in report.families.values()):
        with tempfile.TemporaryDirectory(prefix='effects33-mutants-') as tmp:
            for label,file,old,new,family,kind in MUTANTS:
                mutant=previous.compile_mutant(tmp,'fx',label,file,old,new);r=pt.Report()
                effect_family(text,data,mutant,family,100,r,[kind]);f=r.families[family]
                mutants.append(dict(name=label,detected=f['cases']-f['equal'],
                    stopped=sum(bool(x.get('stopped') or x.get('error')) for x in f['first_failures'])))
    return dict(families=report.families,coverage=report.coverage,
        all_equal=all(f['cases']==f['equal'] for f in report.families.values()),
        mutants=mutants,all_mutants_caught=(not mutations or len(mutants)==len(MUTANTS)) and
            all(m['detected'] and not m['stopped'] for m in mutants),
        seconds=time.monotonic()-start,text_sha256=pins.TEXT.sha256,data_sha256=pins.DATA.sha256,
        bodies={name:hashlib.sha256(text[a-0x401000:b-0x401000]).hexdigest() for name,(a,b) in
            dict(ground_create=(0x13c80a3,0x13c829e),ground_move=(0x143fbda,0x14400b6)).items()})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--output');args=p.parse_args()
    if args.cases<1:p.error('--cases must be positive')
    result=run(args.cases,args.mutations)
    if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['all_equal'] and result['all_mutants_caught'] else 1
if __name__=='__main__':raise SystemExit(main())
