#!/usr/bin/env python3
"""AUDIO-005: one whole-owner instruction verifier for the scalar sound table.

No foreign service is stubbed except SND_Play. The full method must return,
restore registers and read only the declared model/action/frame fields. Original
return addresses supply provenance independently of the native table. Every row
is executed, with edge, silent-action, model, world and unordered controls.
"""
import argparse
import ctypes as C
import json
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import time
import actor_machine as am
import monster_audio_static as lift
import pins
ROOT=Path(__file__).resolve().parents[1]
OBJ=0x41000000
class Sound(C.Structure):_fields_=[('routine',C.c_uint32),('site',C.c_uint32),('id',C.c_int32),('object',C.c_int32),('loop',C.c_int32)]
class Plan(C.Structure):_fields_=[('known',C.c_int),('handled',C.c_int),('count',C.c_int),('sound',Sound*4)]
WRAPPER='''#include "monster_audio.h"
#include "NATIVE_HEADER"
#include <stdlib.h>
#include <string.h>
static mu_monster_sound_plan *sink;
uint16_t mu_actor_action(const mu_actor *a){uint16_t v;memcpy(&v,a->object+0x2a,2);return v;}
float mu_actor_frame(const mu_actor *a){float v;memcpy(&v,a->object+0xd0,4);return v;}
void mu_session_sound_emit(mu_session *s,uint32_t r,uint32_t site,int32_t id,int16_t key,int loop){
 (void)s;if(sink->count<4)sink->sound[sink->count++]=(mu_monster_sound){r,site,id,key==-2?0:1,loop};}
void caller_audio(int kind,int world,int model,unsigned short action,float frame,float played,int random,float distance,mu_monster_sound_plan *p){
 static mu_combat c;mu_world_actors actors={0};mu_world_actor actor={0};mu_world map={0};mu_walk walk={0};
 *p=(mu_monster_sound_plan){0};sink=p;c.session=(mu_session *)1;c.actors=&actors;c.walk=&walk;c.map=&map;
 actors.count=1;actors.list=&actor;actor.actor.loaded=1;actor.actor.spec.model_index=model;actor.session_key=7;
 memcpy(actor.actor.object+0x2a,&action,2);memcpy(actor.actor.object+0xd0,&frame,4);actor.position[0]=distance;
 map.world=world;walk.map=&map;c.monsters[0].voice_3324=played;
 int fallback=kind==1?223:221+random%2;
 if(kind==3){mu_rp_character record={0};record.live=1;record.movement=1;record.position[0]=distance;
  mu_monster_audio_motion(c.session,&walk,&actor,&record);return;}
 int result=mu_monster_audio_combat(&c,0,played,fallback);
 if(played==0.0f)mu_session_sound_emit(c.session,kind==0?0x138f92f:kind==1?0x1393a61:0x1392bde,
  kind==0?0x138fc68:kind==1?0x13943e5:0x1393917,result,7,0);
 if(kind==1)mu_monster_audio_die_complete(&c,0);
 p->handled=c.monsters[0].voice_3324!=0.0f;
}
void select_sound(int w,int m,unsigned short a,float f,mu_monster_sound_plan *p){
 mu_monster_sound_plan q=mu_monster_sound_select(w,m,a,f);*p=q;p->count=0;sink=p;
 mu_monster_audio_emit((mu_session *)1,&q,7);}
void select_plan(int w,int m,unsigned short a,float f,const float *position,const float *hero,mu_monster_sound_plan *p){*p=mu_monster_audio_plan(w,m,a,f,position,hero);}
'''

def build(folder,header=None,table=None,adapter=None):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'monster_audio.h').write_text(header or (ROOT/'reconstructed/audio/monster_audio.h').read_text())
    (folder/'monster_audio_table.inc').write_text(table or (ROOT/'reconstructed/audio/monster_audio_table.inc').read_text())
    (folder/'core').mkdir()
    for path in (ROOT/'native/core').glob('*.h'):
        if path.name!='mu_monster_audio.h':(folder/'core'/path.name).symlink_to(path)
    (folder/'core/mu_monster_audio.h').write_text(adapter or (ROOT/'native/core/mu_monster_audio.h').read_text())
    (folder/'session').symlink_to(ROOT/'native/session')
    if not (folder.parent/'reconstructed').exists():(folder.parent/'reconstructed').symlink_to(ROOT/'reconstructed')
    (folder/'host.c').write_text(WRAPPER.replace('NATIVE_HEADER',str(folder/'core/mu_monster_audio.h')))
    lib=folder/'host.dylib'
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/build/gen'),'-I',str(ROOT/'native/session'),'-shared',str(folder/'host.c'),'-o',str(lib)],check=True,capture_output=True)
    dll=C.CDLL(str(lib));dll.select_sound.argtypes=[C.c_int,C.c_int,C.c_uint16,C.c_float,C.POINTER(Plan)]
    dll.caller_audio.argtypes=[C.c_int,C.c_int,C.c_int,C.c_uint16,C.c_float,C.c_float,C.c_int,C.c_float,C.POINTER(Plan)]
    dll.select_plan.argtypes=[C.c_int,C.c_int,C.c_uint16,C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(Plan)]
    return dll

def native(dll,world,model,action,frame):
    p=Plan();dll.select_sound(world,model,action,frame,C.byref(p))
    return p.known,p.handled,[(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]]


def original(machine,entry,model,action,frame,world):
    obj=am.undefined_region('object',OBJ,0x400)
    obj.define(OBJ+0x5c,struct.pack('<i',model));obj.define(OBJ+0x2a,struct.pack('<H',action));obj.define(OBJ+0xd0,struct.pack('<f',frame));obj.writable=False
    sounds=[]
    def sound(m):
        site=struct.unpack('<I',m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4))[0]-5
        ptr=m.argument(1);assert ptr in (0,OBJ)
        sounds.append((entry,site,m.argument(0),int(bool(ptr)),m.argument(2)))
        return 0
    result=machine.execute(entry,[OBJ],[obj,am.defined_region('world',0x1cf15fc,struct.pack('<i',world),writable=False)],{lift.PLAY:sound},ecx=0x42000000,cleanup=4)
    if not result['ok']:
        raise AssertionError(result)
    return 1,result['eax']&255,sounds


def corpus(accepted,cases):
    rng=random.Random(0xa005)
    for entry,group in sorted(accepted.items()):
        controls=set();models={r['model'] for r in group['rows']}
        for row in group['rows']:
            lo,hi=row['lo'],row['hi']
            probe=math.nan if row['nan'] else lo if row['lc'] else hi if row['hc'] else (lo+hi)/2
            if not row['nan'] and not math.isfinite(probe):probe=lo+1 if math.isfinite(lo) else hi-1 if math.isfinite(hi) else 0.
            controls.add((row['model'],row['action'],probe))
            for f in (lo,hi):
                if math.isfinite(f):
                    bits=struct.unpack('<I',struct.pack('<f',f))[0]
                    controls.update((row['model'],row['action'],struct.unpack('<f',struct.pack('<I',v))[0]) for v in (max(0,bits-1),bits,min(0x7f800000,bits+1)))
        for model in sorted(models|{-1,0,0x840,0xa91,0x7fffffff}):
            for action in (0,1,2,3,4,5,6,7,8,9,11,31,32,65535):
                for frame in (math.nan,-math.inf,0.,math.inf):controls.add((model,action,frame))
        for _ in range(cases):controls.add((rng.choice(sorted(models|{-1,0,0xa91})),rng.choice(list(range(15))+[65535]),am.f32(rng.uniform(-2,30))))
        for model,action,frame in controls:
            yield entry,group['worlds'][0],model,action,frame
        # Every world alias is compared, not just the first member of a group.
        for world in group['worlds'][1:]:
            for row in group['rows']:
                yield entry,world,row['model'],row['action'],math.nan if row['nan'] else 0. if not math.isfinite(row['lo']) else row['lo']


def dispatch(machine,entry,world,model,action,frame,distance):
    import validate_object_render as v
    coverage=json.loads((ROOT/'docs/research/world-handler-coverage.json').read_text())
    row=next(r for r in coverage['classes'] if world in r['worlds'])
    obj=bytearray(0x400);struct.pack_into('<i',obj,0x5c,model);struct.pack_into('<H',obj,0x2a,action)
    struct.pack_into('<f',obj,0xd0,frame);struct.pack_into('<3f',obj,0x158,distance,0,0)
    handler=0x42000000
    regions=v.global_regions(world,6,[am.defined_region('object',OBJ,bytes(obj),writable=False),
        am.defined_region('hero-pointer',v.HERO_PTR,struct.pack('<I',v.HERO),writable=False),
        am.defined_region('hero',v.HERO+0x33ac,struct.pack('<3f',0,0,0),writable=False),
        am.defined_region('handler',handler,struct.pack('<I',int(row['vtable'],16)),writable=False)])
    sounds=[];fallback=[]
    def sound(m):
        site=struct.unpack('<I',m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4))[0]-5
        sounds.append((entry,site,m.argument(0),int(bool(m.argument(1))),m.argument(2)));return 0
    result=machine.execute(0x13a084d,[0x43000000,OBJ],regions,{lift.PLAY:sound,0x95c652:lambda m:handler,
        0xea594b:lambda m:handler,0xea419d:lambda m:(fallback.append(1) or 0,8)})
    assert result['ok'],result
    return result['eax']&255,sounds


def dispatch_corpus(machine,dll,accepted):
    count=0
    for entry,g in accepted.items():
        # One independently executed whole dispatcher per row and all distance
        # edges. The preceding generic service and both world predicates run.
        for row in g['rows']:
            if row['model']<0x7a5 or row['model'] in (0x90a,0x90b,0x90c):continue
            f=math.nan if row['nan'] else row['lo'] if math.isfinite(row['lo']) else 0.
            for distance in (0.,500.,am.f32(500.001)):
                want=dispatch(machine,entry,g['worlds'][0],row['model'],row['action'],f,distance)
                p=Plan();position=(C.c_float*3)(distance,0,0);hero=(C.c_float*3)(0,0,0)
                dll.select_plan(g['worlds'][0],row['model'],row['action'],f,position,hero,C.byref(p))
                got=p.handled,[(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]]
                assert got==want,(hex(entry),row,distance,want,got)
                count+=1
    return count


def caller_corpus(text,data,dll,accepted):
    from validate_audio import Machine,ARENA,STACK,STACK_SIZE
    m=Machine(text,data);char,model,handler,hero=ARENA,ARENA+0x8000,ARENA+0x9000,ARENA+0x10000
    obj=char+0x3254
    ebp=STACK+STACK_SIZE-0x8000
    m.write32(0xbdcfbc8,0);m.write32(0xbdd1cc8,0)
    m.write32(0xa39d754,hero);m.write(hero+0x33ac,struct.pack('<3f',0,0,0))
    m.hook(0x966cc4,lambda m:(model,0));m.hook(0xeaa8cf,lambda m:(model,0))
    m.hook(0x95c652,lambda m:(handler,0));m.hook(0xea594b,lambda m:(handler,0));m.hook(0xea419d,lambda m:(0,8))
    m.hook(0x139f3db,lambda m:(0,0));m.hook(0x1989721,lambda m:(random_value,0))
    sounds=[]
    def sound(m):
        site=m.read32(m.reg('esp'))-5
        routine=entry if entry<=site<group['end'] else (0x138f92f,0x1393a61,0x1392bde,0x139002a)[kind]
        sounds.append((routine,site,m.arg(0),int(bool(m.arg(1))),m.arg(2)));return 0,0
    m.hook(lift.PLAY,sound)
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
            if typ<0x7a5 or typ in (0x90a,0x90b,0x90c) or action not in (2,3,4,5,6):continue
            frame=math.nan if row['nan'] else row['lo'] if math.isfinite(row['lo']) else 0.
            cell=(typ,action,struct.pack('<f',frame) if action==2 else b'caller-frame')
            if cell in seen:continue
            seen.add(cell);kind=0 if action==5 else 1 if action==6 else 3 if action==2 else 2
            start,end,local=[(0x138fb7a,0x138fd33,-4),(0x13942fa,0x139447f,-0x10),(0x1393819,0x1393a47,-0x14),(0x1391c19,0x1391c26,-4)][kind]
            for played in (0.,.001):
                for random_value in (0,1):
                    for distance in (0.,501.):
                        sounds.clear();m.write32(ebp+8,char);m.write32(ebp+local,obj)
                        m.write32(obj+0x5c,typ);m.write32(obj+0x60,0);m.write(obj+0x2a,struct.pack('<H',action));m.write(obj+0xd0,struct.pack('<f',frame));m.write(obj+0x158,struct.pack('<3f',distance,0,0))
                        caller_frame=frame if kind==3 else played
                        m.write(char+0x3324,struct.pack('<f',caller_frame));m.write(model+0xba,struct.pack('<hhh',11,12,13))
                        m.run(start,end,ebp=ebp,esp=ebp-0x1000)
                        assert m.reg('eip')==end
                        want=list(sounds);p=Plan();dll.caller_audio(kind,world,typ,action,caller_frame,played,random_value,distance,C.byref(p))
                        got=[(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]]
                        assert got==want,(hex(entry),kind,typ,action,frame,played,distance,want,got)
                        if kind==1:assert p.handled==int(struct.unpack('<f',m.uc.mem_read(char+0x3324,4))[0]!=0)
                        count+=1
    return count


MUTANTS={
 'id':('r,s,id,obj,loop','r,s,(id)+1,obj,loop'),
 'site':('r,s,id,obj,loop','r,(s)+1,id,obj,loop'),
 'object':('r,s,id,obj,loop','r,s,id,!(obj),loop'),
 'loop':('r,s,id,obj,loop','r,s,id,obj,!(loop)'),
 'action':('action == (a) &&','action != (a) &&'),
 'world':('world == (w)','world != (w)'),
 'frame inclusive':('frame >= (lo)','frame > (lo)'),
 'handled':('p.handled = (ret);','p.handled = !(ret);'),
 'unordered':('isnan(frame) : !isnan(frame)','!isnan(frame) : !isnan(frame)'),
}

ADAPTER_MUTANTS={
 'dispatch distance':('distance > 500.0f','distance >= 500.0f'),
 'discarded return':('    return fallback;\n}', '    return p.known && p.handled ? -1 : fallback;\n}'),
 'death completion':('if (p.known) c->monsters[index].voice_3324', 'if (0 && p.known) c->monsters[index].voice_3324'),
 'walk preserved frame':('mu_actor_action(&actor->actor) == 2 ? mu_actor_frame(&actor->actor) : 0.0f','0.0f'),
 'caller frame zero':(' || !(mu_actor_frame(&actor->actor) == 0.0f)', ''),
 'missing alias':(' || model == 0x90a || model == 0x90b || model == 0x90c',''),
}


def adapter_controls(dll):
    p=Plan();dll.caller_audio(0,138,2374,5,.001,0.,0,0.,C.byref(p))
    assert [(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]]==[(0x138f92f,0x138fc68,221,1,0)]
    for model in (0x356,0x90a,0x90b,0x90c):
        dll.select_plan(131,model,3,0.,(C.c_float*3)(0,0,0),(C.c_float*3)(0,0,0),C.byref(p))
        assert not p.known and not p.count


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--report',type=Path,required=True);a=ap.parse_args();start=time.monotonic()
    text,data=pins.TEXT.read(),pins.DATA.read();accepted,refused=lift.recover(text,data)
    assert (ROOT/'reconstructed/audio/monster_audio_table.inc').read_text()==lift.emit(accepted),'table does not reproduce'
    m=am.ActorMachine(text,data);seen=set();rows=[];families={}
    with tempfile.TemporaryDirectory(prefix='audio-005-') as temp:
        folder=Path(temp);dll=build(folder/'base')
        for entry,world,model,action,frame in corpus(accepted,a.cases):
            want=original(m,entry,model,action,frame,world);got=native(dll,world,model,action,frame)
            assert got==want,(hex(entry),world,hex(model),action,frame,want,got)
            seen.update(s[1] for s in want[2]);rows.append((world,model,action,frame,want))
            key=hex(entry);families[key]=families.get(key,0)+1
        dispatcher_cases=dispatch_corpus(m,dll,accepted)
        caller_cases=caller_corpus(text,data,dll,accepted)
        adapter_controls(dll)
        expected={s[0] for g in accepted.values() for r in g['rows'] for s in r['sounds']}
        assert seen==expected,(seen^expected)
        mutants={}
        if a.mutations:
            header=(ROOT/'reconstructed/audio/monster_audio.h').read_text()
            for name,(old,new) in MUTANTS.items():
                assert old in header,name
                bad=build(folder/name,header=header.replace(old,new))
                hits=sum(native(bad,*row[:4])!=row[4] for row in rows)
                assert hits,name
                mutants[name]=hits
            adapter=(ROOT/'native/core/mu_monster_audio.h').read_text()
            for name,(old,new) in ADAPTER_MUTANTS.items():
                assert adapter.count(old)==1,(name,adapter.count(old))
                bad=build(folder/name,adapter=adapter.replace(old,new))
                caught=False
                try:
                    adapter_controls(bad)
                    dispatch_corpus(m,bad,accepted)
                    caller_corpus(text,data,bad,accepted)
                except AssertionError:caught=True
                assert caught,name
                mutants[name]=1
    report=dict(cases=len(rows)+dispatcher_cases+caller_cases,dispatcher_cases=dispatcher_cases,caller_cases=caller_cases,sites=len(seen),owners=len(accepted),families=families,mismatches=0,stops=0,mutants=mutants,refused={hex(k):v for k,v in refused.items()},wall_seconds=round(time.monotonic()-start,3))
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='refused'},indent=2))
if __name__=='__main__':main()
