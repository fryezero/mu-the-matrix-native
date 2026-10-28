#!/usr/bin/env python3
"""RENDER-WORLDS-C: compiled C versus pinned client sky/object instructions.
Engine light/effect/sprite/joint calls are recording stubs. Vector/matrix helpers execute.
MSVC rand is a seeded recording callback, compared through its final state.
"""
import argparse
import ctypes as C
import json
import hashlib
from pathlib import Path
import random
import shutil
import struct
import sys
import subprocess
import tempfile
from collections import defaultdict
import validate_joints as vj
import validate_environment as ve
import actor_machine as am
import pins
import validate_object_render as v
ROOT=Path(__file__).resolve().parents[1]
SUFFIX='dylib' if sys.platform=='darwin' else 'so'
F3=C.c_float*3
HERO=0x41010000
OBJ=0x41020000
COUNT=0x41030000
ORD=COUNT+4

def library(path):
    lib=C.CDLL(str(path))
    lib.mu_icarus_sky.argtypes=[F3,C.c_int32,v.RAND_FN,C.c_void_p,C.POINTER(v.Log)]
    lib.mu_icarus_object.argtypes=[C.c_void_p,C.c_int32,C.c_int32,C.POINTER(C.c_int32),v.RAND_FN,C.c_void_p,C.POINTER(v.Log)]
    return lib

def family(machine,lib,kind,cases):
    g=random.Random(20261027)
    tally=v.Tally(kind)
    for n in range(cases):
        seed=g.getrandbits(32)
        # Directed seeds make rare lightning branches and all four sides routine cases.
        if kind=='sky' and n%2==0:
            while True:
                r=v.MsvcRand(seed)
                if r()%50==0: break
                seed=(seed+1)&0xffffffff
        rnd=v.MsvcRand(seed); crnd=v.MsvcRand(seed); calls=[]
        hero=[v.f32(g.uniform(-4000,20000)) for _ in range(3)]
        count=g.choice([0,1,50,419]); ordinal=g.randrange(30); selected=g.choice([0,1,17])
        o=bytearray(0x3d8); v.put_i(o,0x5c,g.choice([-1,0,1,2,3,4,5,6,30]))
        v.put_f(o,0x158,*hero);v.put_f(o,0x164,0,0,v.f32(g.uniform(0,360)))
        def vec(m,a): return list(struct.unpack('<3I',m.uc.mem_read(a,12)))
        def light(m):
            calls.append([0x16cacfc,-1,[m.argument(0),m.argument(1)]+vec(m,m.argument(2))+[m.argument(3)]])
            assert m.argument(4)==0xb9f5430
            return 0
        def effect(m):
            a=[m.argument(i) for i in range(14)]
            assert a[4:]==[0,0,0xffffffff,0,0,0,0,0xffffffff,0,0],a
            calls.append([0x13c0eaa,-1,[a[0]]+vec(m,a[1])+vec(m,a[2])+vec(m,a[3])+[0,0]])
            return 0
        def joint(m):
            a=[m.argument(i) for i in range(14)]
            assert a[7:]==[0xffffffff,0,0,0xffffffff,0,0xffffffff,0],a
            calls.append([0x153b02c,0 if kind=='object' else -1,[a[0]]+vec(m,a[1])+vec(m,a[2])+vec(m,a[3])+[a[4],int(a[5]!=0),a[6]]])
            return 0
        def sprite(m):
            a=[m.argument(i) for i in range(9)]
            assert a[4]==HERO+0x3254
            calls.append([0x1692eb7,0,[a[0]]+vec(m,a[1])+[a[2]]+vec(m,a[3])+[a[5],2,a[6],a[7]]])
            return 0
        stubs={0x1989721:lambda m:rnd(),0x16cacfc:light,0x13c0eaa:effect,0x153b02c:joint,0x1692eb7:sprite}
        regions=v.global_regions(10,6,[am.defined_region('hero-ptr',0xa39d754,struct.pack('<I',HERO)),am.defined_region('hero',HERO+0x33ac,struct.pack('<3f',*hero)),am.defined_region('object',OBJ,o),am.defined_region('object-count',0xbdc5890,struct.pack('<i',count)),am.defined_region('counters',COUNT,struct.pack('<ii',selected,ordinal))])
        result=v.run(machine,0x18016b0 if kind=='sky' else 0x180249e,[] if kind=='sky' else [OBJ,COUNT,ORD],regions,stubs)
        stop=v.stopped_reason(result)
        if stop:
            tally.add(False,{'case':n},stop);continue
        log=v.new_log();cb=v.RAND_FN(lambda _:crnd())
        if kind=='sky':
            got=lib.mu_icarus_sky(F3(*hero),count,cb,None,C.byref(log))
            ret=result['eax'];ok=got==ret
        else:
            co=C.c_int32(ordinal);buf=C.create_string_buffer(bytes(o))
            lib.mu_icarus_object(buf,0,selected,C.byref(co),cb,None,C.byref(log))
            ok=co.value==struct.unpack('<i',machine.uc.mem_read(ORD,4))[0]
        native=[[e.call,e.object,list(e.args)[:e.count]] for e in log.events[:log.count]]
        ok=ok and calls==native and rnd.seed==crnd.seed and not log.overflow
        tally.count('emissions',len(calls));tally.count('joint calls',sum(e[0]==0x153b02c for e in calls))
        tally.add(ok,{'case':n,'client':calls,'native':native,'rand':[rnd.seed,crnd.seed]})
    return tally

def dragon_sessions(machine, lib, count, ticks=20, fuzz=True):
    results=[]
    g=random.Random(20261027)
    for n in range(count):
        case=ve.make_case(g,n,lib,[10],fuzz=fuzz and n%2==1)
        if n%8==0: case['teleport']=5
        results.append(ve.run_case(machine,lib,case,ticks,4,random.Random(case['seed'])))
    return {'cases':count,'equal':sum(not r['mismatch'] and not r['stopped'] for r in results),
            'mismatch_count':sum(bool(r['mismatch']) for r in results),
            'stopped':sum(bool(r['stopped']) for r in results),
            'steps':sum(r['steps'] for r in results),'host_calls':sum(r['events'] for r in results),
            'rand_calls':sum(r['rand_calls'] for r in results),
            'examples':[r for r in results if r['mismatch'] or r['stopped']][:4]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--text',type=Path,default=pins.TEXT.default_str());ap.add_argument('--data',type=Path,default=pins.DATA.default_str());ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output');args=ap.parse_args()
    text=am.load_pinned(args.text,am.TEXT_BYTES,am.TEXT_SHA256,'text')
    data=am.load_pinned(args.data,am.DATA_BYTES,am.DATA_SHA256,'data')
    machine=am.ActorMachine(text,data)
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/objects')],check=True)
    lib=library(ROOT/f'reconstructed/objects/libobjects.{SUFFIX}')
    report={'pins':{'text':am.TEXT_SHA256,'data':am.DATA_SHA256},'families':{}, 'bodies':{name:{'start':hex(a),'end':hex(z),'sha256':hashlib.sha256(text[a-am.TEXT_BASE:z-am.TEXT_BASE]).hexdigest()} for name,a,z in [('sky',0x18016b0,0x1802168),('object',0x180249e,0x1802692)]}}
    for k in ['sky','object']:
        t=family(machine,lib,k,args.cases);report['families'][k]=t.report();print(k,t.report())
    # These are the two Icarus kinds, separated from the broad joint regression corpus.
    vj.KINDS=[(0x7f7c,6),(0x7f7d,0)]
    jm=vj.sf.FxMachine(text,data)
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/joints')],check=True)
    jlib=vj.load_library(ROOT/f'reconstructed/joints/libclient_joints.{SUFFIX}')
    for name,fn in vj.FAMILIES:
        r=vj.vc.Report()
        fn(jm,jlib,random.Random(20261027),min(args.cases,400),r,defaultdict(int))
        t=r.families[name]
        report['families']['icarus_'+name]={'cases':t['cases'],'equal':t['equal'],'mismatch_count':t['cases']-t['equal'],'stopped':0,'details':t}
        print('icarus_'+name,t['equal'],t['cases'])
    report['mutants']=[]
    if args.mutations:
        for name,old,new,k in [('cloud offset','- 150.0f','- 140.0f','sky'),('lightning height','p[2]-=300','p[2]-=200','sky'),('sprite scale','bits(0.5f)','bits(1.0f)','object'),('swirl subtype','p,p,a,6,','p,p,a,7,','object')]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td)/'reconstructed';shutil.copytree(ROOT/'reconstructed/objects',root/'objects');shutil.copytree(ROOT/'reconstructed/record-math',root/'record-math')
                p=root/'objects/icarus.c';s=p.read_text();assert old in s; p.write_text(s.replace(old,new))
                out=root/'mutant.dylib'
                subprocess.run(['clang','-std=c11','-O2','-shared','-ffp-contract=off','-fPIC',str(p),str(root/'record-math/record_math.c'),'-lm','-o',str(out)],check=True)
                t=family(machine,library(out),k,min(args.cases,500));report['mutants'].append({'name':name,'caught':t.equal<t.cases and not t.stopped,'cases':t.cases,'differences':t.cases-t.equal})
    if args.mutations:
        for name,old,new,which in [('swirl lifetime','j->lifetime=jrand(env)%20+6','j->lifetime=jrand(env)%20+5','joint_create'),('bolt fade','j->brightness-=10.12f','j->brightness-=9.12f','joint_move')]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td)/'reconstructed'
                for folder in ['joints','record-math','movement']:
                    shutil.copytree(ROOT/'reconstructed'/folder,root/folder)
                p=root/'joints'/('joints.c' if which=='joint_create' else 'icarus_joints.inc')
                source=p.read_text();assert old in source;p.write_text(source.replace(old,new))
                out=root/'mutant.dylib'
                subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC','-ffp-contract=off',str(root/'joints/joints.c'),str(root/'record-math/record_math.c'),str(root/'movement/client_movement.c'),'-lm','-o',str(out)],check=True)
                r=vj.vc.Report()
                dict(vj.FAMILIES)[which](jm,vj.load_library(out),random.Random(20261027),100,r,defaultdict(int))
                t=r.families[which]
                report['mutants'].append({'name':name,'caught':t['equal']<t['cases'],'cases':t['cases'],'differences':t['cases']-t['equal']})
    # Freeze the environment sources before compiling: sibling merges and other builds cannot alter
    # a long-running comparison or its mutants halfway through the run.
    with tempfile.TemporaryDirectory() as td:
        frozen=Path(td)
        for folder in ['environment','record-math']:
            shutil.copytree(ROOT/'reconstructed'/folder,frozen/'reconstructed'/folder)
        ve.ROOT=frozen
        em=ve.EnvMachine(text,data)
        elib=ve.Library(ve.build_library(0,frozen/f'env.{SUFFIX}'))
        t=dragon_sessions(em,elib,40)
        report['families']['dragons']=t
        print('dragons',t)
        if args.mutations:
            for mid,name in [(11,'dragon height'),(12,'dragon scale')]:
                mutant=ve.Library(ve.build_library(mid,frozen/f'env-mut{mid}.{SUFFIX}'))
                t=dragon_sessions(em,mutant,8,ticks=10,fuzz=False)
                report['mutants'].append({'name':name,'caught':t['mismatch_count']>0 and not t['stopped'],'cases':t['cases'],'differences':t['mismatch_count']})
    if args.output: Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    return int(any(t['mismatch_count'] or t['stopped'] for t in report['families'].values()) or any(not t['caught'] for t in report['mutants']))
if __name__=='__main__':raise SystemExit(main())
