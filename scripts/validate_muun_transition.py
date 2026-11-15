#!/usr/bin/env python3
"""Muun's 0x47a/0 consumer, full original CreateEffect/MoveEffect comparison."""
import argparse
import json
from pathlib import Path
import tempfile
import time
import pins
import validate_skill_fx as fx
import validate_render_effects as base
import validate_render_effects7 as re7
import validate_render_effects11 as re11
ROOT=Path(__file__).resolve().parents[1]
MUTANTS=[('life','e->lifetime = 10; e->scale = 0.2f; e->velocity = 0.1f;',
                   'e->lifetime = 11; e->scale = 0.2f; e->velocity = 0.1f;','create'),
 ('scale','e->lifetime = 10; e->scale = 0.2f; e->velocity = 0.1f;',
          'e->lifetime = 10; e->scale = 0.3f; e->velocity = 0.1f;','create'),
 ('rand','(void)env_rand(env); /* 0x013db373:', '(void)0; /* 0x013db373:','create'),
 ('angle','const float y = (float)subtype * -90.0f + 45.0f;',
          'const float y = (float)subtype * -90.0f + 40.0f;','create'),
 ('growth','e->velocity = e->velocity + 0.02f','e->velocity = e->velocity + 0.03f','move'),
 ('dim_gate','e->lifetime < 7','e->lifetime <= 7','move'),
 ('dim','e->blend_light / 1.8f','e->blend_light / 1.7f','move')]

def compare(text,data,lib,name,count):
    saved=re11.random_effect
    ordinal=0
    def effect(rng,kind):
        nonlocal ordinal
        e=saved(rng,kind);e.lifetime=(1,2,5,6,7,8,9,10)[ordinal%8];ordinal+=1
        return e
    re11.random_effect=effect
    try:
        result=re11.fx_compare(text,data,lib,name,[(0x47a,0)],count,seed='muun-transition-005-')
        for family in result['families'].values():family['mismatches']=family['cases']-family['equal']
        return result
    finally:re11.random_effect=saved

def run(cases,mutations):
    start=time.monotonic();text=pins.TEXT.read();data=pins.DATA.read();lib=fx.load_library(ROOT/("reconstructed/combat/libcombat."+fx.SUFFIX))
    rows={name:compare(text,data,lib,name,cases) for name in ('create','move')};mutants={}
    if mutations:
        with tempfile.TemporaryDirectory() as td:
            for name,old,new,family in MUTANTS:
                m=base.compile_mutant(Path(td),name,'fx',old,new)
                r=compare(text,data,m,family,40)
                mutants[name]={'caught':sum(x['mismatches'] for x in r['families'].values())}
    families={k:v for row in rows.values() for k,v in row['families'].items()}
    return {'families':families,'cases':sum(r['cases'] for r in families.values()),'all_equal':all(not r['mismatches'] for r in families.values()),
        'mutants':mutants,'all_mutants_caught':all(r['caught'] for r in mutants.values()),'wall_seconds':time.monotonic()-start}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=200);p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    r=run(a.cases,a.mutations)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['all_equal'] and r['all_mutants_caught'] else 1)
