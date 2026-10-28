#!/usr/bin/env python3
"""AUDIO-002C: sound ids, gates and source sites against pinned instructions.

Player/monster families execute the unchanged whole service comparisons, then
compare the new compiled provenance adapter with the original return addresses.
Skill families execute bounded sound fragments, including the class-77 buff and
special-state-3 Twisting Slash gates. Whole skill/MoveCharacter timing and
unavailable event inputs are outside this fragment comparison.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import pins
import validate_combat as vc
import validate_skill_fx as fx
import validate_items as items
from validate_audio import Machine, STACK, STACK_SIZE, ARENA
ROOT=Path(__file__).resolve().parents[1]
WRAPPER='''
#include "mu_combat_audio.h"
mu_combat_audio voice(int kind,int monster,int id) { return mu_combat_voice_sound(kind,monster,id); }
mu_combat_audio monster(int world,float played,int model,int kind,int s2,int s3,int random) {
 return mu_combat_voice_sound(MU_COMBAT_AUDIO_ATTACK,1,mu_combat_monster_attack(world,played,model,kind,(int16_t)s2,(int16_t)s3,random));
}
mu_combat_audio skill(int id,int end,int cls,int state) { return mu_combat_skill_sound(id,end,cls,state); }
'''
class Decision(C.Structure):
    _fields_=[('routine',C.c_uint32),('site',C.c_uint32),('id',C.c_int32)]
def build(tmp,name,header=None):
    folder=tmp/name;folder.mkdir()
    (folder/'mu_combat_audio.h').write_text(header or (ROOT/'native/core/mu_combat_audio.h').read_text())
    # Preserve the production relative session include without copying sources.
    (tmp/'session').symlink_to(ROOT/'native/session') if not (tmp/'session').exists() else None
    (folder/'wrapper.c').write_text(WRAPPER)
    out=folder/'adapter.dylib'
    subprocess.run(['clang','-std=c11','-O2','-shared','-I',str(folder),'-I',str(ROOT/'native/session'),'-I',str(ROOT/'native/build/gen'),str(folder/'wrapper.c'),'-o',str(out)],check=True)
    lib=C.CDLL(str(out))
    lib.voice.argtypes=[C.c_int]*3;lib.voice.restype=Decision
    lib.skill.argtypes=[C.c_int]*4;lib.skill.restype=Decision
    lib.monster.argtypes=[C.c_int,C.c_float,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int];lib.monster.restype=Decision
    return lib
class Sites(fx.FxMachine):
    def execute(self,start,args,regions,stubs,**kwargs):
        self.sounds=[]
        original=stubs.get(0xa6ac96)
        if original:
            def sound(m):
                ret=struct.unpack('<I',m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4))[0]
                self.sounds.append((start,ret-5,m.argument(0)))
                return original(m)
            stubs=dict(stubs);stubs[0xa6ac96]=sound
        return super().execute(start,args,regions,stubs,**kwargs)
class CorpusReport(vc.Report):
    def __init__(self,m,monster):
        super().__init__();self.m=m;self.monster=monster;self.corpus=[]
    def add(self,family,equal,failure=None):
        super().add(family,equal,failure)
        assert equal,(family,failure)
        kind={'shock':0,'die':1,'attack':2}[failure['kind']]
        self.corpus.append(((kind,self.monster),self.m.sounds[:]))
def voice_corpus(text,data,cases,monster):
    m=Sites(text,data);r=CorpusReport(m,monster);neg={k:0 for k in items.NEGATIVES+['player_shock_action_5']}
    rng=random.Random(20023)
    if monster:items.family_monster_voice(m,None,rng,cases,r,neg)
    else:fx.family_player_voice(m,fx.load_library(ROOT/'reconstructed/combat/libcombat.dylib'),rng,cases,r,neg)
    return r.corpus
# Start immediately before the sound pushes, or before its deciding branch.
# The surrounding spell effects/animation services have their own families.
SKILLS=[(19,0,0x1255f16,0x1255f24),(20,0,0x1255f45,0x1255f53),
 (21,0,0x1255f74,0x1255f82),(22,0,0x1255fa3,0x1255fb1),(23,0,0x125600b,0x1256019),
 (26,0,0x125594d,0x125596a),(27,0,0x125594d,0x125596a),(28,0,0x125594d,0x125596a),
 (1,1,0x13b0093,0x13b00a1),(2,1,0x13b00fb,0x13b0109),(4,1,0x13b03e5,0x13b03f3),
 (7,1,0x13afe56,0x13afe64),(9,1,0x13ad005,0x13ad013),(10,1,0x13abc45,0x13abc53),
 (11,1,0x13b0638,0x13b0646),(12,1,0x13ac928,0x13ac936),(17,1,0x13b0e02,0x13b0e10),
 (41,1,0x13abb26,0x13abb3e),(42,1,0x13a9544,0x13a9555)]
def skill_corpus(text,data):
    m=Machine(text,data);sounds=[]
    def sound(m):
        sounds.append((0x13a763e if end else 0x1253a92,m.read32(m.reg('esp'))-5,m.arg(0)))
        assert m.arg(1)==0 and m.arg(2)==0
        return 1,0
    m.hook(0xa6ac96,sound);m.hook(0x9b0bc1,lambda m:(state,0))
    ebp=STACK+STACK_SIZE-0x8000;corpus=[]
    for skill,end,start,stop in SKILLS:
        for cls in [-1,0,0x4c,0x4d,0x4e,0x7fff]:
            for state in [0,1,2,3,4,255]:
                sounds.clear();m.write32(ebp-0x18,ARENA)
                m.write(ARENA+0x146,struct.pack('<h',cls))
                m.run(start,stop,ebp=ebp,esp=ebp-0x1000)
                assert m.reg('eip')==stop
                corpus.append(((skill,end,cls,state),sounds[:]))
    return corpus
def monster_attack_corpus(text,data):
    m=Machine(text,data);sounds=[]
    obj=ARENA;char=ARENA+0x4000;model=ARENA+0x8000;ebp=STACK+STACK_SIZE-0x8000
    m.model_page(0x1cf1000);m.write32(0x1cf15fc,0)
    m.hook(0x966cc4,lambda m:(model,0));m.hook(0xeaa8cf,lambda m:(model if has_model else 0,0))
    m.hook(0x13a084d,lambda m:(0,0));m.hook(0x139f3db,lambda m:(0,0))
    m.hook(0x1989721,lambda m:(random_value,0))
    def sound(m):
        sounds.append((0x1392bde,m.read32(m.reg('esp'))-5,m.arg(0)))
        assert m.arg(1)==obj and m.arg(2)==0
        return 1,0
    m.hook(0xa6ac96,sound);corpus=[]
    for world in [0,7,0x49]:
      for played in [0.,0.001,1.]:
       for has_model in [0,1]:
        for kind in [0,9,10]:
         for s2,s3 in [(-1,-1),(0,1),(2,3),(20,21)]:
          for random_value in [0,1,2,32767]:
            sounds.clear();m.write32(ebp+8,char);m.write32(ebp-0x14,obj)
            m.write32(obj+0x5c,0x7ae);m.write32(obj+0x60,kind)
            m.write(char+0x3324,struct.pack('<f',played));m.write32(0x1cf15fc,world)
            m.write(model+0xba,struct.pack('<hh',s2,s3))
            m.run(0x1393819,0x1393a47,stops=(0x1393a55,),ebp=ebp,esp=ebp-0x1000)
            assert m.reg('eip') in (0x1393a47,0x1393a55)
            corpus.append(((world,played,has_model,kind,s2,s3,random_value),sounds[:]))
    return corpus
def check(lib,name,corpus):
    seen=set()
    for args,want in corpus:
        if name=='monster_attack':
            d=lib.monster(*args);got=[] if not d.site else [(d.routine,d.site,d.id)]
        elif name=='skills':
            d=lib.skill(*args);got=[] if not d.site else [(d.routine,d.site,d.id)]
        else:
            got=[]
            for routine,site,id in want:
                d=lib.voice(*args,id);got.append((d.routine,d.site,d.id))
        seen.update(x[1] for x in want)
        if got!=want:return (args,want,got),seen
    return None,seen
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=6000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--report');a=p.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read()
    corpora={'player':voice_corpus(text,data,a.cases,0),'monster':voice_corpus(text,data,a.cases,1),
             'skills':skill_corpus(text,data),'monster_attack':monster_attack_corpus(text,data)}
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{},'mutants':{},'mismatches':0}
    with tempfile.TemporaryDirectory(prefix='audio-combat-') as folder:
        tmp=Path(folder);lib=build(tmp,'plain')
        for name,corpus in corpora.items():
            error,seen=check(lib,name,corpus);assert error is None,(name,error)
            report['families'][name]={'cases':len(corpus),'mismatches':0,'sites':[hex(s) for s in sorted(seen)]}
        if a.mutations:
            header=(ROOT/'native/core/mu_combat_audio.h').read_text()
            variants=[('hurt-site','player','0x0138fcf5u','0x0138fd2bu'),
                      ('bow-site','player','0x01393939u','0x0139395bu'),
                      ('die-site','player','0x0139442fu','0x01394440u'),
                      ('monster-hurt','monster','0x0138fc68u','0x013943e5u'),
                      ('monster-die','monster','0x013943e5u','0x0138fc68u'),
                      ('skill-id','skills','d.id=0x42','d.id=0x43'),
                      ('skill-site','skills','0x013b03ebu','0x013b0101u'),
                      ('buff-gate','skills','caster_class==0x4d','caster_class==0x4c'),
                      ('slash-gate','skills','special_state==3','special_state==2'),
                      ('energy-ball','skills','case 17:','case 18:'),
                      ('monster-attack-slot','monster_attack','random%2 ? slot3 : slot2','random%2 ? slot2 : slot3'),
                      ('monster-attack-world','monster_attack','world==0x49','world==0x48')]
            for name,family,old,new in variants:
                assert old in header
                bad=build(tmp,name,header.replace(old,new,1));error,_=check(bad,family,corpora[family])
                assert error is not None,name;report['mutants'][name]='caught'
    report['cases']=sum(x['cases'] for x in report['families'].values())
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
