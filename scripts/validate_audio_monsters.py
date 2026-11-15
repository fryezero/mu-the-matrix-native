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
void select_sound(int w,int m,unsigned short a,float f,mu_monster_sound_plan *p){*p=mu_monster_sound_select(w,m,a,f);}
'''

def build(folder,header=None,table=None):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'monster_audio.h').write_text(header or (ROOT/'reconstructed/audio/monster_audio.h').read_text())
    (folder/'monster_audio_table.inc').write_text(table or (ROOT/'reconstructed/audio/monster_audio_table.inc').read_text())
    (folder/'host.c').write_text(WRAPPER)
    lib=folder/'host.dylib'
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared',str(folder/'host.c'),'-o',str(lib)],check=True,capture_output=True)
    dll=C.CDLL(str(lib));dll.select_sound.argtypes=[C.c_int,C.c_int,C.c_uint16,C.c_float,C.POINTER(Plan)]
    return dll

def native(dll,world,model,action,frame):
    p=Plan();dll.select_sound(world,model,action,frame,C.byref(p))
    return p.known,p.handled,[(s.routine,s.site,s.id,s.object,s.loop) for s in p.sound[:p.count]]


def original(machine,entry,model,action,frame):
    obj=am.undefined_region('object',OBJ,0x400)
    obj.define(OBJ+0x5c,struct.pack('<i',model));obj.define(OBJ+0x2a,struct.pack('<H',action));obj.define(OBJ+0xd0,struct.pack('<f',frame));obj.writable=False
    sounds=[]
    def sound(m):
        site=struct.unpack('<I',m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4))[0]-5
        ptr=m.argument(1);assert ptr in (0,OBJ)
        sounds.append((entry,site,m.argument(0),int(bool(ptr)),m.argument(2)))
        return 0
    result=machine.execute(entry,[OBJ],[obj],{lift.PLAY:sound},ecx=0x42000000,cleanup=4)
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

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--report',type=Path,required=True);a=ap.parse_args();start=time.monotonic()
    text,data=pins.TEXT.read(),pins.DATA.read();accepted,refused=lift.recover(text,data)
    assert (ROOT/'reconstructed/audio/monster_audio_table.inc').read_text()==lift.emit(accepted),'table does not reproduce'
    m=am.ActorMachine(text,data);seen=set();rows=[];families={}
    with tempfile.TemporaryDirectory(prefix='audio-005-') as temp:
        folder=Path(temp);dll=build(folder/'base')
        for entry,world,model,action,frame in corpus(accepted,a.cases):
            want=original(m,entry,model,action,frame);got=native(dll,world,model,action,frame)
            assert got==want,(hex(entry),world,hex(model),action,frame,want,got)
            seen.update(s[1] for s in want[2]);rows.append((world,model,action,frame,want))
            key=hex(entry);families[key]=families.get(key,0)+1
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
    report=dict(cases=len(rows),sites=len(seen),owners=len(accepted),families=families,mismatches=0,stops=0,mutants=mutants,refused={hex(k):v for k,v in refused.items()},wall_seconds=round(time.monotonic()-start,3))
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='refused'},indent=2))
if __name__=='__main__':main()
