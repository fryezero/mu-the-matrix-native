#!/usr/bin/env python3
"""AUDIO-006: extend the table-driven whole-owner comparison with RNG leaves.

World predicates, vector access and sqrt execute as original instructions.
Only CRT rand and sound requests are recorded services. Original return sites,
AL, the strict read/write guard and RNG consumption are independent oracles.
Every emitted decision and leaf has an original comparison. No live client.
"""
import argparse
import ctypes as C
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import time
import actor_machine as am
import monster_audio_extended as lift
import pins
import validate_audio_monsters as base
import validate_object_render as v
ROOT=Path(__file__).resolve().parents[1]
OBJ,HERO=base.OBJ,0x42010000
WRAPPER=base.WRAPPER.replace('#include "NATIVE_HEADER"','#include "NATIVE_HEADER"\n#include "EXTRA_HEADER"')
WRAPPER=WRAPPER.replace('mu_monster_audio_motion(c.session,&walk,&actor,&record);return;', 'mu_monster_audio_extra_motion(c.session,&walk,&actor,&record,&c.audio_rng);return;')
WRAPPER=WRAPPER.replace('int result=mu_monster_audio_combat(&c,0,played,fallback);','mu_monster_audio_extra_combat(&c,0,played);int result=fallback;')
WRAPPER=WRAPPER.replace('*p=(mu_monster_sound_plan){0};sink=p;', '*p=(mu_monster_sound_plan){0};sink=p;c.audio_rng=(uint32_t)random;')
WRAPPER=WRAPPER.replace('mu_monster_audio_extra_combat(&c,0,played);int result=fallback;', 'mu_monster_audio_extra_combat(&c,0,played);(void)fallback;int result=kind==1?223:221+mu_monster_audio_random(&c.audio_rng)%2;')
WRAPPER+='''
static int32_t tape[8];static int used;
static int32_t scripted(void *ctx){(void)ctx;return tape[used++%8];}
void extended(int w,int m,unsigned short a,float f,float distance,int r0,int r1,int outer,mu_monster_sound_plan *p,int *consumed){
 tape[0]=r0;tape[1]=r1;used=0;
 if(outer){float pos[3]={distance,0,0},hero[3]={0};*p=mu_monster_audio_extra_plan(w,m,a,f,pos,hero,scripted,0);}
 else *p=mu_monster_sound_extended(w,m,a,f,distance,scripted,0);
 *consumed=used;
}
'''


def build(folder,header=None,adapter=None,completion=None):
    folder.mkdir(parents=True)
    ext=folder/'extended.h'
    source=header or (ROOT/'reconstructed/audio/monster_audio_extended.h').read_text()
    source=source.replace('"monster_audio.h"','"'+str(ROOT/'reconstructed/audio/monster_audio.h')+'"').replace('"monster_audio_extended.inc"','"'+str(ROOT/'reconstructed/audio/monster_audio_extended.inc')+'"')
    ext.write_text(source)
    ordinary=ROOT/'native/core/mu_monster_audio.h'
    if completion is not None:
        ordinary=folder/'ordinary.h'
        for include in ('../../reconstructed/audio/monster_audio.h','../../reconstructed/audio/monster_audio_extended.h','mu_combat.h','../session/mu_audio_cue.h'):
            completion=completion.replace(chr(34)+include+chr(34),chr(34)+str((ROOT/'native/core'/include).resolve())+chr(34))
        ordinary.write_text(completion)
    extra=folder/'extra.h';source=adapter or (ROOT/'native/core/mu_monster_audio_extra.h').read_text()
    source=source.replace('"mu_monster_audio.h"','"'+str(ordinary)+'"').replace('"../../reconstructed/audio/monster_audio_extended.h"','"'+str(ext)+'"')
    # Include the mutated extension before the ordinary adapter's guarded include.
    extra.write_text('#include "'+str(ext)+'"\n'+source)
    host=folder/'host.c';host.write_text(WRAPPER.replace('"monster_audio.h"','"'+str(ROOT/'reconstructed/audio/monster_audio.h')+'"').replace('NATIVE_HEADER',str(extra)).replace('EXTRA_HEADER',str(extra)))
    lib=folder/'host.dylib'
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/build/gen'),'-I',str(ROOT/'native/session'),'-shared',str(host),'-o',str(lib)],check=True,capture_output=True)
    dll=C.CDLL(str(lib));dll.extended.argtypes=[C.c_int,C.c_int,C.c_uint16,C.c_float,C.c_float,C.c_int,C.c_int,C.c_int,C.POINTER(base.Plan),C.POINTER(C.c_int)]
    dll.caller_audio.argtypes=[C.c_int,C.c_int,C.c_int,C.c_uint16,C.c_float,C.c_float,C.c_int,C.c_float,C.POINTER(base.Plan)]
    dll.fixture_action_count.argtypes=[C.c_int]
    return dll


def native(dll,w,m,a,f,distance,tape,outer=0):
    p=base.Plan();used=C.c_int();dll.extended(w,m,a,f,distance,*(tuple(tape)+(0,0))[:2],outer,C.byref(p),C.byref(used))
    return p.known,p.handled,[(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]],used.value


def original(machine,entry,world,model,action,frame,distance,tape,outer=False):
    obj=am.undefined_region('object',OBJ,0x400)
    for off,payload in ((0x5c,struct.pack('<i',model)),(0x2a,struct.pack('<H',action)),(0xd0,struct.pack('<f',frame)),(0x158,struct.pack('<3f',distance,0,0))):obj.define(OBJ+off,payload)
    obj.writable=False;sounds=[];used=0
    def sound(m):
        site=m.read32(m.uc.reg_read(m.x86.UC_X86_REG_ESP))-5
        assert m.argument(1) in (0,OBJ)
        sounds.append((entry,site,m.argument(0),int(bool(m.argument(1))),m.argument(2)));return 0
    def rnd(m):
        nonlocal used
        value=tape[used];used+=1;return value
    regions=v.global_regions(world,6,[obj,am.defined_region('hero-pointer',v.HERO_PTR,struct.pack('<I',HERO),writable=False),am.defined_region('hero-position',HERO+0x33ac,struct.pack('<3f',0,0,0),writable=False)])
    stubs={lift.lift.PLAY:sound,0x1989721:rnd}
    start,args,this,cleanup=entry,[OBJ],0x43000000,4
    if outer:
        coverage=json.loads((ROOT/'docs/research/world-handler-coverage.json').read_text())
        row=next(r for r in coverage['classes'] if world in r['worlds'])
        regions.append(am.defined_region('handler',this,struct.pack('<I',int(row['vtable'],16)),writable=False))
        stubs.update({0x95c652:lambda m:this,0xea594b:lambda m:this,0xea419d:lambda m:(0,8)})
        start,args,cleanup=0x13a084d,[0x44000000,OBJ],0
    result=machine.execute(start,args,regions,stubs,ecx=this,cleanup=cleanup)
    assert result['ok'],(hex(entry),model,action,frame,distance,tape,result)
    return 1,result['eax']&255,sounds,used


def paths(nodes,root,tape=()):
    n=nodes[root]
    if n[0]=='leaf':yield tape;return
    # One path to every edge outcome, plus signed-remainder edge controls.
    for residue,child in zip(range(1-n[1],n[1]),n[2]):
        yield from paths(nodes,child,tape+(residue,))


def corpus(groups,nodes,cases):
    rng=random.Random(0xa006)
    for entry,g in groups.items():
        models={r['model'] for r in g['rows']}|{-1,0,0x7fffffff}
        for world in g['worlds']:
            for row in g['rows']:
                f=math.nan if row['nan'] else row['lo'] if row['lc'] else row['hi'] if row['hc'] else (row['lo']+row['hi'])/2
                if not row['nan'] and not math.isfinite(f):f=row['lo']+1 if math.isfinite(row['lo']) else row['hi']-1 if math.isfinite(row['hi']) else 0.
                fs=[f]
                for edge in (row['lo'],row['hi']):
                    if math.isfinite(edge):fs.extend([edge,am.f32(edge-.0001),am.f32(edge+.0001)])
                for tape in paths(nodes,row['node']):
                    for frame in fs:yield entry,world,row['model'],max(0,row['action']),frame,0.,tape+(0,0)
            for model in models:
                for action in (0,1,2,3,4,5,6,10,31,65535):
                    for f in (math.nan,-math.inf,0.,math.inf):
                        yield entry,world,model,action,f,0.,(0,1)
            for _ in range(cases):
                yield entry,world,rng.choice(sorted(models)),rng.randrange(32),am.f32(rng.uniform(-2,20)),rng.choice((0.,499.999,500.,500.001,599.999,600.,600.001,math.inf)),(rng.randint(-2147483648,2147483647),rng.randint(-2147483648,2147483647))


def caller_corpus(text,data,dll,accepted):
    from validate_audio import Machine,ARENA,STACK,STACK_SIZE
    m=Machine(text,data);char,model,handler,hero=ARENA,ARENA+0x8000,ARENA+0x9000,ARENA+0x10000
    obj=char+0x3254
    ebp=STACK+STACK_SIZE-0x8000
    m.write32(0xbdcfbc8,0);m.write32(0xbdd1cc8,0)
    m.write32(0xa39d754,hero);m.write(hero+0x33ac,struct.pack('<3f',0,0,0))
    m.hook(0x966cc4,lambda m:(model,0));m.hook(0xeaa8cf,lambda m:(model,0))
    m.hook(0x95c652,lambda m:(handler,0));m.hook(0xea594b,lambda m:(handler,0));m.hook(0xea419d,lambda m:(0,8))
    m.hook(0x139f3db,lambda m:(0,0))
    def rnd(m):
        nonlocal seed
        seed=(seed*214013+2531011)&0xffffffff
        return (seed>>16)&0x7fff,0
    m.hook(0x1989721,rnd)
    sounds=[]
    def sound(m):
        site=m.read32(m.reg('esp'))-5
        routine=entry if entry<=site<group['end'] else (0x138f92f,0x1393a61,0x1392bde,0x139002a)[kind]
        sounds.append((routine,site,m.arg(0),int(bool(m.arg(1))),m.arg(2)));return 0,0
    m.hook(lift.lift.PLAY,sound)
    coverage=json.loads((ROOT/'docs/research/world-handler-coverage.json').read_text());count=0
    for entry,group in accepted.items():
        world=group['worlds'][0];vtable=int(next(r['vtable'] for r in coverage['classes'] if world in r['worlds']),16)
        m.write32(handler,vtable);m.write32(0x1cf15fc,world)
        # Unique model/action/frame cells are sufficient; aliases already have
        # full dispatcher coverage. Compare actual caller tails without replacing
        # the class dispatch. Model lookup and slots are explicit platform inputs.
        seen=set()
        for row in group['rows']:
            action=row['action'];typ=row['model']
            if typ<0x7a5 or typ in (0x90a,0x90b,0x90c) or action not in range(2,32):continue
            frame=math.nan if row['nan'] else row['lo'] if math.isfinite(row['lo']) else 0.
            cell=(typ,action,struct.pack('<f',frame) if action==2 else b'caller-frame')
            if cell in seen:continue
            seen.add(cell);kind=0 if action==5 else 1 if action==6 else 3 if action==2 else 2
            start,end,local=[(0x138fb7a,0x138fd33,-4),(0x13942fa,0x139447f,-0x10),(0x1393819,0x1393a47,-0x14),(0x1391c19,0x1391c26,-4)][kind]
            for played in (0.,.001):
                for random_value in (0,1,17):
                    for distance in (0.,501.):
                        seed=random_value
                        sounds.clear();m.write32(ebp+8,char);m.write32(ebp+local,obj)
                        m.write32(obj+0x5c,typ);m.write32(obj+0x60,0);m.write(obj+0x2a,struct.pack('<H',action));m.write(obj+0xd0,struct.pack('<f',frame));m.write(obj+0x158,struct.pack('<3f',distance,0,0))
                        caller_frame=frame if kind==3 else played
                        m.write(char+0x3324,struct.pack('<f',caller_frame));m.write(model+0xba,struct.pack('<hhh',11,12,13))
                        m.run(start,end,ebp=ebp,esp=ebp-0x1000)
                        assert m.reg('eip')==end
                        want=list(sounds);p=base.Plan();dll.caller_audio(kind,world,typ,action,caller_frame,played,random_value,distance,C.byref(p))
                        got=[(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]]
                        assert got==want,(hex(entry),kind,typ,action,frame,played,distance,want,got)
                        if kind==1:assert p.handled==int(struct.unpack('<f',m.uc.mem_read(char+0x3324,4))[0]!=0)
                        count+=1
    return count


MUTANTS={
 'id':('owner,s->site,s->id,s->object,s->loop','owner,s->site,s->id+1,s->object,s->loop'),
 'site':('owner,s->site,s->id,s->object,s->loop','owner,s->site+1,s->id,s->object,s->loop'),
 'loop':('owner,s->site,s->id,s->object,s->loop','owner,s->site,s->id,s->object,!s->loop'),
 'object':('owner,s->site,s->id,s->object,s->loop','owner,s->site,s->id,!s->object,s->loop'),
 'action':('action!=r->action','action==r->action'),
 'world':('world==(w)','world!=(w)'),
 'frame':('frame>=r->lo','frame>r->lo'),
 'distance':('distance > limit','distance >= limit'),
 'random':('random(context)%leaf->period','(random(context)^1)%leaf->period'),
 'random consumption':('p.handled=leaf->handled;','if(random)random(context);p.handled=leaf->handled;'),
 'order':('leaf->start+n','leaf->start+leaf->count-1-n'),
 'handled':('p.handled=leaf->handled;','p.handled=!leaf->handled;'),
}


ADAPTER_MUTANTS={
 'outer distance':('distance>500.0f','distance>=500.0f'),
 'caller frame zero':(' || !(mu_actor_frame(&a->actor)==0.0f)',''),
 'caller played':(' || !(played==0.0f)',' || (played!=played)'),
 'walk preserved frame':('mu_actor_action(&a->actor)==2?mu_actor_frame(&a->actor):0.0f','0.0f'),
 'walk missing action':(' ||\n        !record->movement || mu_actor_action_count(&a->actor)<=2',' ||\n        !record->movement'),
 'foreign model':('model<0x7a5 || ','')}


def adapter_controls(dll):
    p=base.Plan()
    dll.fixture_action_count(2)
    try:
        dll.caller_audio(3,80,2168,2,1.5,0.,0,0.,C.byref(p))
        assert not p.count
    finally:dll.fixture_action_count(8)
    dll.caller_audio(0,80,2166,5,.001,0.,0,0.,C.byref(p))
    assert p.count==1 and p.sound[0].site==0x138fc68
    # Native retains a separate death latch while animation can stay at zero.
    dll.caller_audio(1,80,2166,6,0.,.001,0,0.,C.byref(p))
    assert not p.count
    assert native(dll,80,2166,3,0.,500.,(0,0),1)[2]
    assert native(dll,80,0x356,3,0.,0.,(0,0),1)==(0,0,[],0)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--report',type=Path,required=True);a=ap.parse_args();start=time.monotonic()
    text,data=pins.TEXT.read(),pins.DATA.read();groups,nodes=lift.recover(text,data)
    assert (ROOT/'reconstructed/audio/monster_audio_extended.inc').read_text()==lift.emit(groups,nodes)
    machine=am.ActorMachine(text,data);rows=[];seen=set();families={};dispatch_cases=0
    with tempfile.TemporaryDirectory(prefix='audio-006-') as temp:
        folder=Path(temp);dll=build(folder/'base')
        for e,w,m,ac,f,d,tape in corpus(groups,nodes,a.cases):
            want=original(machine,e,w,m,ac,f,d,tape);got=native(dll,w,m,ac,f,d,tape)
            assert want==got,(hex(e),w,m,ac,f,d,tape,want,got)
            rows.append((w,m,ac,f,d,tape,want));seen.update(s[1] for s in want[2]);families[hex(e)]=families.get(hex(e),0)+1
        # Full outer dispatch for every row and every world alias, with the
        # real near/far boundaries. Original and table RNG use the same tape.
        for e,g in groups.items():
            for world in g['worlds']:
                for row in g['rows']:
                    frame=0. if row['nan']==2 else row['lo'] if math.isfinite(row['lo']) else 0.
                    for tape in paths(nodes,row['node']):
                        tape=tape+(0,0)
                        for distance in (0.,500.,am.f32(500.001)):
                            want=original(machine,e,world,row['model'],max(0,row['action']),frame,distance,tape,True)
                            got=native(dll,world,row['model'],max(0,row['action']),frame,distance,tape,1)
                            assert want==got,(hex(e),world,row,frame,distance,tape,want,got)
                            dispatch_cases+=1
        assert seen=={s for g in groups.values() for s in g['sites']}
        caller_cases=caller_corpus(text,data,dll,groups)
        adapter_controls(dll)
        mutants={}
        if a.mutations:
            header=(ROOT/'reconstructed/audio/monster_audio_extended.h').read_text()
            for name,(old,new) in MUTANTS.items():
                assert old in header,name
                bad=build(folder/name,header=header.replace(old,new));hits=0
                for w,m,ac,f,d,tape,want in rows:
                    # Extra-consumption control permits a third draw safely.
                    if name=='random consumption' and want[3]>=2:continue
                    hits+=native(bad,w,m,ac,f,d,tape)!=want
                assert hits,name
                mutants[name]=hits
            adapter=(ROOT/'native/core/mu_monster_audio_extra.h').read_text()
            for name,(old,new) in ADAPTER_MUTANTS.items():
                assert old in adapter,name
                bad=build(folder/name,adapter=adapter.replace(old,new,1))
                caught=False
                try:
                    adapter_controls(bad)
                    caller_corpus(text,data,bad,groups)
                except AssertionError:caught=True
                assert caught,name
                mutants[name]=1
            completion=(ROOT/'native/core/mu_monster_audio.h').read_text()
            old=' || mu_monster_audio_extended_known(c->map->world)'
            assert old in completion
            completion=completion.replace(chr(34)+include+chr(34),chr(34)+str((ROOT/'native/core'/include).resolve())+chr(34))
            caught=False
            try:caller_corpus(text,data,bad,groups)
            except AssertionError:caught=True
            assert caught,'death completion'
            mutants['death completion']=1
        report=dict(cases=len(rows)+dispatch_cases+caller_cases,caller_cases=caller_cases,whole_owner_cases=len(rows),dispatcher_cases=dispatch_cases,sites=len(seen),owners=len(groups),families=families,mismatches=0,stops=0,mutants=mutants,wall_seconds=round(time.monotonic()-start,3))
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
