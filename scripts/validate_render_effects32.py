#!/usr/bin/env python3
"""RENDER-EFFECTS-032: authored combat callers, ordered requests and poses.

Only visual fragments execute. Receive parsers, network, power, item eligibility,
actor construction and effect consumers are outside this comparison.
"""
import argparse
import ctypes as C
import json
import hashlib
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import time
import actor_machine as am
import pins
import validate_combat as vc
import validate_particles as pt
import validate_skill_fx as fx
import validate_render_effects30 as r30

ROOT = Path(__file__).resolve().parents[1]
SKILLS = [18,30,31,32,33,34,35,36,44,49]
BODIES = {
    'step': (0x13966ea,0x139b5d5), 'area_selector': (0x13a90c0,0x13a9449),
    'summon': (0x13a9449,0x13a94a4), 'crescent_end': (0x13ad798,0x13ad7f9),
    'fire_end': (0x13aba0c,0x13aba81), 'shield_pose': (0x1222f89,0x1222fb0),
    'crescent_pose': (0x1256cf6,0x1256d25), 'summon_start': (0x125594d,0x125599c),
    'mount_pose': (0x106c453,0x106c4b6), 'arrow_pose': (0x13946ee,0x1394870),
}
class Context(C.Structure):
    _fields_ = [(n,C.c_int32) for n in ['bow_kind','wing','shield','mount']]
class Input(C.Structure):
    _fields_ = [('cast',r30.Input),('object_key',C.c_uint16),('skill_word',C.c_uint16),('random',C.c_int32*6)]
class Call(C.Structure):
    _fields_ = [('call',r30.Call),('skill',C.c_int32)]
class Plan(C.Structure):
    _fields_ = [(n,C.c_int32) for n in ['count','limit','random_used']] + [('calls',Call*10)]
class Machine(r30.Machine):
    def stub_entry(self,uc,address,size,ignored):
        if address in (0x122373b,0x125c47c) and address in self.stubs:
            for reg,value in self.preserved.items():uc.reg_write(reg,value)
            uc.mem_write(am.TIB,struct.pack('<I',am.SEH_HEAD))
            uc.reg_write(self.x86.UC_X86_REG_ESP,am.ENTRY_ESP+4)
            uc.reg_write(self.x86.UC_X86_REG_EIP,am.SENTINEL)
            return
        super().stub_entry(uc,address,size,ignored)
def load(path):
    lib=C.CDLL(str(path));lib.mu_skill32_plan_cast.argtypes=[C.POINTER(Input),C.c_int,C.POINTER(Plan)]
    lib.mu_skill32_select.argtypes=[C.c_int32,C.c_int32]
    lib.mu_skill32_action.argtypes=[C.c_int32,C.c_int32,C.POINTER(Context)]
    return lib

def normalized(call):
    c=call.call.visual
    if c.routine==fx.CREATE_PARTICLE:
        return ['particle',c.type,list(c.position),list(c.angle),list(c.light),c.subtype,c.scale,fx.object_address(c.owner),0]
    result=r30.normalized(c,call.call.site)
    if result[0]=='effect':result[-1][1]=call.skill
    return result

def compare(text,data,lib,cases):
    rep=pt.Report();rng=random.Random(20261114)
    m=Machine(text,data)
    for phase in [0,1,2]:
        for n in range(cases):
            skill=SKILLS[n%len(SKILLS)];s=Input();s.cast.skill=s.cast.base=skill;s.cast.owner=0
            s.cast.model=rng.choice([0xa91,0x7b7]);s.cast.action=rng.choice([0xf8,0xf9,0xfa,0x98])
            s.cast.attack_time=n%18;s.cast.frame=rng.choice([0.,4.999,5.,5.001,6.,float('nan')])
            s.object_key=rng.randrange(65536);s.skill_word=rng.randrange(65536)
            s.random[:]=[rng.randrange(32768) for _ in range(6)]
            for k in range(3):
                s.cast.position[k]=fx.f32(rng.uniform(-1000,25000));s.cast.angle[k]=fx.f32(rng.uniform(-360,360));s.cast.light[k]=fx.f32(rng.random())
            char=am.undefined_region('character',r30.CHAR,0x3670)
            char.define(r30.CHAR+0x21,bytes([s.cast.attack_time]));char.define(r30.CHAR+0x26,struct.pack('<H',skill))
            char.define(r30.CHAR+0x146,bytes(2)) # Player fixture, never NPC class 77
            obj=am.undefined_region('object',fx.OBJECTS,0x400)
            for off,b in [(0x5c,struct.pack('<i',s.cast.model)),(0x2a,struct.pack('<H',s.cast.action)),
                (0xd0,struct.pack('<f',s.cast.frame)),(0x54,struct.pack('<H',s.object_key)),
                (0x158,struct.pack('<3f',*s.cast.position)),(0x164,struct.pack('<3f',*s.cast.angle)),
                (0xec,struct.pack('<3f',*s.cast.light))]:obj.define(fx.OBJECTS+off,b)
            regions=[char,obj,am.defined_region('cutoff',0x1cf1050,struct.pack('<i',15)),
                am.defined_region('skill-word',0x6fca278,struct.pack('<H',s.skill_word)),
                am.defined_region('hero',0xa39d754,struct.pack('<I',r30.CHAR))]
            client=[];rand_used=0;pose=[]
            def effect(mm):
                client.append(['effect',mm.argument(0),mm.floats(mm.argument(1),3),mm.floats(mm.argument(2),3),
                    mm.floats(mm.argument(3),3),mm.argument(4),mm.argument(5),[mm.argument(i) for i in range(6,14)]]);return 0
            def joint(mm):
                client.append(['joint',mm.argument(0),mm.floats(mm.argument(1),3),mm.floats(mm.argument(2),3),
                    mm.floats(mm.argument(3),3),mm.argument(4),mm.argument(5),mm.float_argument(6),
                    [mm.argument(i) for i in range(7,14)]]);return 0
            def particle(mm):
                client.append(['particle',mm.argument(0),mm.floats(mm.argument(1),3),mm.floats(mm.argument(2),3),
                    mm.floats(mm.argument(3),3),mm.argument(4),mm.float_argument(5),mm.argument(6),mm.argument(7)]);return 0
            def sound(mm):
                ret=struct.unpack('<I',mm.uc.mem_read(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP),4))[0]
                client.append(['sound',mm.argument(0),mm.argument(1),mm.argument(2),ret-5]);return 0
            def rand(mm):
                nonlocal rand_used
                v=s.random[rand_used];rand_used+=1;return v
            def action(mm):
                pose.append([mm.argument(i) for i in range(4)]);return 0
            stubs={fx.CREATE_EFFECT_WRAPPER:effect,fx.CREATE_JOINT:joint,fx.CREATE_PARTICLE:particle,fx.PLAY_BUFFER:sound,
                0x1989721:rand,0x13aea7a:lambda mm:0,0x13b1911:lambda mm:0,0x13a5658:lambda mm:0,
                0xac3bf7:lambda mm:(fx.CONTAINER,4),0x95f998:lambda mm:fx.CONTAINER,0xbb1c32:lambda mm:skill,
                0x122373b:lambda mm:0,0x125c47c:lambda mm:0,0x12b001a:action}
            kw={};args=[r30.CHAR,fx.OBJECTS]
            if phase==0:entry=0x13966ea
            elif phase==1:
                entry=0x13a90c0;kw={'frame':(0x1000,{-0x14:skill,-0x10:fx.OBJECTS,
                    -0x30:fx.bits(1.),-0x2c:fx.bits(1.),-0x28:fx.bits(1.)})}
            else:
                if skill==49:continue # mount helper is exercised by poses()
                entry=0x1222f89 if skill==18 else 0x1256cf6 if skill==44 else 0x125594d
                kw={'frame':(0x2000,{-0x18:r30.CHAR,-0x10:fx.OBJECTS,-0x1c:skill})}
            result=m.execute(entry,args,regions,stubs,**kw)
            plan=Plan();supported=lib.mu_skill32_plan_cast(C.byref(s),phase,C.byref(plan))
            mine=[normalized(plan.calls[i]) for i in range(plan.count)]
            error=None
            if vc.ok(result):
                actual=result['regions']['character'][0x21]
                expected=1 if phase==2 and skill!=18 else s.cast.attack_time
                if actual!=expected:error=('time',actual,expected)
                if not vc._same_call(client,mine):error=('calls',client,mine)
                if phase==0 and rand_used!=plan.random_used:error=('rng',rand_used,plan.random_used)
                if phase==0 and plan.limit!=struct.unpack('<i',result['regions']['cutoff'])[0]:error=('limit',plan.limit)
                expected_pose=[] if phase!=2 or skill not in [18,44] else [[r30.CHAR,skill,0xd7 if skill==18 else 0x98,0xffffffff]]
                if pose!=expected_pose:error=('pose',pose,expected_pose)
            rep.add(['step','end','start'][phase],supported and vc.ok(result) and error is None,
                dict(case=n,skill=skill,error=error,stopped=result['stopped'],machine_error=result['error']))
    return rep

def poses(text,data,lib,rep):
    m=Machine(text,data)
    for skill in [24,51,52,416,424,49]:
        for kind in [0,1,2]:
            for wing in [-1,0,0x2301]:
                char=am.undefined_region('character',r30.CHAR,0x3670);obj=r30.CHAR+0x3254
                char.define(obj+0x5c,struct.pack('<i',0xa91));char.define(r30.CHAR+0x12,bytes([2]))
                char.define(r30.CHAR+0x21a4,struct.pack('<h',wing))
                actions=[]
                def action(mm):
                    actions.append(mm.argument(1));return 0
                def skillaction(mm):
                    assert [mm.argument(i) for i in [0,1,3]]==[r30.CHAR,skill,0xffffffff]
                    actions.append(mm.argument(2));return 0
                stubs={0x12affa4:action,0x12b001a:skillaction,0x138d9cf:lambda mm:0,0x1392afd:lambda mm:0,
                    0x139d8f8:lambda mm:kind,0x95f5cc:lambda mm:2,0x95fb27:lambda mm:0}
                entry=0x106c453 if skill==49 else 0x13947d8 if skill in [52,416] else 0x13946ee
                result=m.execute(entry,[r30.CHAR,skill],[char],stubs)
                ctx=Context(kind,wing,0,1);mine=lib.mu_skill32_action(skill,1 if skill==49 else 2,C.byref(ctx))
                rep.add('poses',vc.ok(result) and actions==([] if mine<0 else [mine]),
                    dict(skill=skill,kind=kind,wing=wing,actions=actions,mine=mine,stopped=result['stopped'],error=result['error']))
    for skill in SKILLS+[24,51,52,416,424,47,432,9999]:
        for cls in [0,1,2,0x11,0x12]:
            for kind in [0,1,2]:
                for shield,mount in [(0,0),(1,0),(0,1)]:
                    ctx=Context(kind,-1,shield,mount);action=lib.mu_skill32_action(skill,cls,C.byref(ctx))
                    c=cls&15
                    expected=0xd7 if skill==18 and c==1 and shield else 0x98 if skill==44 and c==1 else 0xf9 if skill==49 and c==1 and mount else 0xa5 if 30<=skill<=36 and c==2 else (0x93 if skill in [52,416] else 0x7e)+(kind-1) if skill in [24,51,52,416,424] and c==2 and kind in [1,2] else -1
                    rep.add('admission',action==expected,dict(skill=skill,cls=cls,kind=kind,shield=shield,mount=mount))
    for raw in SKILLS+[47,432,9999]:
        for base in SKILLS:
            rep.add('selector',bool(lib.mu_skill32_select(raw,base))==(raw==base and raw in SKILLS),dict(raw=raw,base=base))

MUTANTS=[
 ('base >= 30 && base <= 36','base >= 30 && base < 36'),
 ('base == 18 ||','base == 47 ||'),
 ('&& c->shield ?','&& !c->shield ?'),('&& c->mount ?','&& !c->mount ?'),
 ('? 0xd7 :','? 0xd6 :'),('? 0xf9 :','? 0xf8 :'),('? 0x98 :','? 0x99 :'),
 ('c->wing != -1 ? 2 : 0','c->wing != -1 ? 1 : 0'),
 ('s->cast.frame >= 5.0f','s->cast.frame > 5.0f'),
 ('s->cast.frame > 5.0f','s->cast.frame >= 5.0f'),
 ('s->cast.action == 0xf9','s->cast.action == 0xf8'),
 ('s->random[0] % 30','s->random[0] % 29'),('n < 4;','n < 3;'),
 ('s->random[n+2] % 60 + 150','s->random[n+2] % 60 + 149'),
 ('c->scale = 10.0f','c->scale = 11.0f'),('c->scale = 1.5f','c->scale = 0.5f'),
 ('0x7f84, 3','0x7f84, 1'),('0x8001, 0','0x8001, 1'),
 ('c->range = s->object_key','c->range = s->skill_word'),
 ('.skill = s->skill_word','.skill = s->object_key'),
 ('0x49e, 0','0x49e, 2'),('= 1.0f;\n        c = request32','= 0.5f;\n        c = request32'),
 ('0x013aba74','0x013aba75'),('skill == 44 ? 0x71','skill == 44 ? 0x70')]
def run(cases,mutants):
    start=time.monotonic();text=pins.TEXT.read();data=pins.DATA.read()
    lib=load(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}');rep=compare(text,data,lib,cases);poses(text,data,lib,rep)
    out=dict(families=rep.families,mutants=[],text_sha256=pins.TEXT.sha256,data_sha256=pins.DATA.sha256,
        bodies={name:dict(start=hex(a),end=hex(b),sha256=hashlib.sha256(text[a-0x401000:b-0x401000]).hexdigest()) for name,(a,b) in BODIES.items()})
    out['all_equal']=all(f['cases']==f['equal'] for f in rep.families.values())
    if mutants and out['all_equal']:
        source=(ROOT/'reconstructed/combat/demo_skill_fx.c').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);dest=tmp/'demo_skill_fx.c'
            for i,(old,new) in enumerate(MUTANTS):
                assert old in source,old
                dest.write_text(source.replace(old,new));path=tmp/f'm{i}.{fx.SUFFIX}'
                subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC','-ffp-contract=off','-fno-fast-math','-I',str(ROOT/'reconstructed/combat'),str(dest),'-o',str(path)],check=True,capture_output=True)
                ml=load(path);r=compare(text,data,ml,200);poses(text,data,ml,r)
                failures=[f for f in r.families.values() if f['equal']!=f['cases']]
                stops=sum(bool(e.get('stopped')) for f in failures for e in f['first_failures'])
                out['mutants'].append(dict(index=i,detected=sum(f['cases']-f['equal'] for f in failures),stopped=stops))
                path.unlink()
    out['all_mutants_caught']=(not mutants or len(out['mutants'])==len(MUTANTS)) and all(m['detected'] and not m['stopped'] for m in out['mutants'])
    out['cases']=sum(f['cases'] for f in rep.families.values());out['seconds']=time.monotonic()-start
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000);p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.cases<1:p.error('positive --cases required')
    out=run(a.cases,a.mutations)
    if a.output:a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2));raise SystemExit(not(out['all_equal'] and out['all_mutants_caught']))
