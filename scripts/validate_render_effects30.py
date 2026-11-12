#!/usr/bin/env python3
"""Bounded DK/Elf visual caller streams against pinned original instructions.

Synthetic base selectors and learned-list indices are explicit services. No
packet parser, target-state writer or character power routine is executed.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import time
import actor_machine as am
import pins
import validate_skill_fx as fx
import validate_combat as vc
import validate_particles as pt

ROOT = Path(__file__).resolve().parents[1]
CHAR = 0x28000000
F3 = C.c_float * 3
PAIRS = [(24,24),(48,48),(51,51),(52,52),(344,344),(416,52),(424,51)]
class Input(C.Structure):
    _fields_ = [(n,C.c_int32) for n in ['skill','base','learned_index','owner','model','action']] + [
        ('attack_time',C.c_uint8),('tile',C.c_uint8*2),('target_index',C.c_uint16),
        ('frame',C.c_float),('prior_frame',C.c_float),('position',F3),('angle',F3),('light',F3)]
class Call(C.Structure):
    _fields_ = [('visual',fx.Call),('site',C.c_uint32)]
class Plan(C.Structure):
    _fields_ = [('count',C.c_int32),('limit',C.c_int32),('target_index',C.c_int32),('calls',Call*40)]
class Machine(fx.FxMachine):
    def stub_entry(self,uc,address,size,ignored):
        if address in (0x13aea7a,0x13b1911) and address in self.stubs:
            for reg,value in self.preserved.items():uc.reg_write(reg,value)
            uc.mem_write(am.TIB,struct.pack('<I',am.SEH_HEAD))
            uc.reg_write(self.x86.UC_X86_REG_ESP,am.ENTRY_ESP+4)
            uc.reg_write(self.x86.UC_X86_REG_EIP,am.SENTINEL)
            return
        super().stub_entry(uc,address,size,ignored)
def load(path):
    lib=C.CDLL(str(path));lib.mu_skill30_plan_cast.argtypes=[C.POINTER(Input),C.c_int,C.POINTER(Plan)]
    lib.mu_skill30_select.argtypes=[C.c_int32,C.c_int32]
    return lib

def normalized(c,site):
    if c.routine==0x158d5bd:return ['arrow',c.range,c.subtype,c.type]
    if c.routine==fx.PLAY_BUFFER:return ['sound',c.type,fx.object_address(c.owner),0,site]
    if c.routine==fx.CREATE_EFFECT_WRAPPER:
        return ['effect',c.type,list(c.position),list(c.angle),list(c.light),c.subtype,fx.object_address(c.owner),
            [c.range&0xffffffff,0,0,0,fx.bits(c.scale),c.arg7&0xffffffff,0,0]]
    if c.routine==fx.CREATE_JOINT:
        return ['joint',c.type,list(c.position),list(c.target),list(c.angle),c.subtype,fx.object_address(c.owner),c.scale,
            [c.arg7&0xffffffff,c.arg8&0xffffffff,0,0xffffffff,0,0xffffffff,0]]
    raise ValueError(c.routine)

def compare(text,data,lib,cases):
    report=pt.Report();rng=random.Random(20261111)
    for end in (0,1):
        m=Machine(text,data)
        for n in range(cases):
            raw,base=PAIRS[n%len(PAIRS)]
            if not end and base not in (48,52,344):continue
            s=Input();s.skill,s.base=raw,base;s.owner=0;s.model=rng.choice([0xa91,0x7b7])
            s.action=rng.choice([0x6e,0x6f,0x9c,0x11d,0x132,0x133]);s.attack_time=n%18
            s.frame=rng.choice([0.,4.,4.999,5.,6.,float('nan')]);s.prior_frame=3.
            s.tile[:]=[rng.randrange(256),rng.randrange(256)];s.target_index=rng.randrange(65536)
            s.learned_index=rng.choice([0,1,7,13,149])
            for k in range(3):
                s.position[k]=fx.f32(rng.uniform(0,25000));s.angle[k]=fx.f32(rng.uniform(0,360));s.light[k]=fx.f32(rng.uniform(0,1))
            char=am.undefined_region('character',CHAR,0x3670)
            for off,b in [(0x21,bytes([s.attack_time])),(0x26,struct.pack('<H',raw)),(0x40,struct.pack('<H',s.target_index)),
                          (0x2f,bytes(s.tile))]:char.define(CHAR+off,b)
            obj=am.undefined_region('object',fx.OBJECTS,0x400)
            for off,b in [(0x5c,struct.pack('<i',s.model)),(0x2a,struct.pack('<H',s.action)),
                (0xd0,struct.pack('<f',s.frame)),(0xd4,struct.pack('<f',s.prior_frame)),(0x364,b'\xff\xff'),
                (0x158,struct.pack('<3f',*s.position)),(0x164,struct.pack('<3f',*s.angle)),(0xec,struct.pack('<3f',*s.light))]:
                obj.define(fx.OBJECTS+off,b)
            cutoff=am.defined_region('cutoff',0x1cf1050,struct.pack('<i',15))
            client=[]
            def arrows(mm):
                assert mm.argument(0)==CHAR and mm.argument(1)==fx.OBJECTS and mm.argument(2)==0
                client.append(['arrow',mm.argument(3),mm.argument(4),mm.argument(5)]);return 0
            def learned(mm):
                assert mm.argument(0)==raw
                return s.learned_index
            def effect(mm):
                client.append(['effect',mm.argument(0),mm.floats(mm.argument(1),3),mm.floats(mm.argument(2),3),
                    mm.floats(mm.argument(3),3),mm.argument(4),mm.argument(5),[mm.argument(i) for i in range(6,14)]]);return 0
            def joint(mm):
                client.append(['joint',mm.argument(0),mm.floats(mm.argument(1),3),mm.floats(mm.argument(2),3),
                    mm.floats(mm.argument(3),3),mm.argument(4),mm.argument(5),mm.float_argument(6),
                    [mm.argument(i) for i in range(7,14)]]);return 0
            def sound(mm):
                ret=struct.unpack('<I',mm.uc.mem_read(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP),4))[0]
                client.append(['sound',mm.argument(0),mm.argument(1),mm.argument(2),ret-5]);return 0
            stubs={0x158d5bd:arrows,0x16a782e:learned,fx.CREATE_EFFECT_WRAPPER:effect,
                fx.CREATE_JOINT:joint,fx.PLAY_BUFFER:sound,0x13aea7a:lambda mm:0,0x13b1911:lambda mm:0,
                0x13a5658:lambda mm:0,0xac3bf7:lambda mm:(fx.CONTAINER,4),0x95f998:lambda mm:fx.CONTAINER,
                0xbb1c32:lambda mm:base}
            entry=0x13966ea if not end else {24:0x13af9db,51:0x13afa2c,52:0x13af9fe,48:0x13aa0e1,344:0x13a9f25}[base]
            kw={} if not end else {'frame':(0x1000,{-0x10:fx.OBJECTS})}
            result=m.execute(entry,[CHAR,fx.OBJECTS],[char,obj,cutoff],stubs,**kw)
            plan=Plan();supported=lib.mu_skill30_plan_cast(C.byref(s),end,C.byref(plan))
            mine=[normalized(plan.calls[i].visual,plan.calls[i].site) for i in range(plan.count)]
            error=None
            if vc.ok(result):
                cr=result['regions']['character'];ob=result['regions']['object']
                fields=[(s.attack_time,cr[0x21]),(s.frame,struct.unpack_from('<f',ob,0xd0)[0]),
                    (s.prior_frame,struct.unpack_from('<f',ob,0xd4)[0]),
                    (plan.target_index if plan.target_index>=0 else 65535,struct.unpack_from('<H',ob,0x364)[0])]
                if any(not fx.same(a,b) for a,b in fields):error=('state',fields)
                if not vc._same_call(client,mine):error=('calls',client[:3],mine[:3],len(client),len(mine))
                if not end and plan.limit!=struct.unpack('<i',result['regions']['cutoff'])[0]:error=('limit',plan.limit)
            report.add('end' if end else 'step',supported and vc.ok(result) and error is None,
                dict(case=n,skill=raw,base=base,error=error,stopped=result['stopped'],machine_error=result['error']))
    # Every other pair is refused even when its base is known.
    for raw in [0,18,24,47,48,51,52,344,416,424,2044,2045,9999]:
        for base in [24,48,51,52,344,2044]:
            expected=(raw,base) in PAIRS
            report.add('selector',bool(lib.mu_skill30_select(raw,base))==expected,dict(skill=raw,base=base))
    return report
def lifecycle(text,data,report):
    """Original records persist independently from creation until removal."""
    import validate_render_effects4 as r4
    lib=r4.load(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}')
    rng=random.Random(30030);m=fx.FxMachine(text,data)
    for raw,base in [(51,51),(52,52),(416,52),(424,51)]:
        for dies in [False,True]:
            objects=[fx.random_object(rng)];objects[0].live=1
            pos=[12000.,12000.,80.];angle=[0.,0.,90.];light=[1.,1.,1.]
            archer=r4.Archer();archer.weapon=0x12e6;archer.hero_weapon=0x800;archer.is_hero=1;archer.key=1234
            archer.mastery=base;archer.field_364=5678
            out=r4.ArrowEffect();case=fx.Case(rng,objects,fx.rand_values(rng,200),60.,1,8,True)
            env=case.env()
            lib.mu_sfx_create_arrow(C.byref(archer),F3(*pos),F3(*angle),7,0,raw,0,C.byref(env),C.byref(out))
            info=out.info;pos=list(out.position);angle=list(out.angle)
            record=am.defined_region('record',fx.POOL,bytes(0x3d8))
            inputs=am.defined_region('inputs',fx.INPUTS,struct.pack('<9f',*pos,*angle,*light)+fx.info_bytes(info))
            hero=am.defined_region('hero-data',fx.HERO_DATA,bytes(0x3000))
            regions=[record,inputs,fx.object_region(objects),hero,
                am.defined_region('hero-ptr',fx.HERO_DATA_PTR,struct.pack('<I',fx.HERO_DATA)),
                am.defined_region('hero',fx.HERO_POINTER,struct.pack('<I',0x5000000))]
            # Recreate the service stream after the standalone selector above.
            case=fx.Case(rng,objects,fx.rand_values(rng,200),60.,1,8,True)
            r=m.execute(fx.CREATE_EFFECT,[out.type,out.subtype,fx.INPUTS,fx.INPUTS+12,fx.INPUTS+24,
                fx.OBJECTS,fx.bits(0.),fx.INPUTS+36],regions,case.stubs(m),ecx=fx.POOL,cleanup=0x20)
            e=fx.Effect();env=case.env()
            lib.mu_sfx_effect_create(C.byref(e),out.type,out.subtype,F3(*pos),F3(*angle),F3(*light),0,0.,C.byref(info),C.byref(env))
            mismatch=fx.compare_effect(e,r['regions']['record'],record.defined) if vc.ok(r) else None
            if mismatch is None:mismatch=fx.compare_calls(case.client_calls,case.c_calls)
            report.add('lifecycle',vc.ok(r) and mismatch is None,dict(skill=raw,step='create',error=mismatch,stopped=r['stopped']))
            if not vc.ok(r):continue
            original=r['regions']['record']
            for tick in range(64):
                if dies and tick==4:objects[0].live=0
                record=am.defined_region('record',fx.POOL,original)
                model=bytearray(0x2000);struct.pack_into('<I',model,0x30,fx.MODEL+0x1000)
                for a in range(0x100):struct.pack_into('<h',model,0x1000+16*a+8,8)
                regions=[record,fx.object_region(objects),am.defined_region('model',fx.MODEL,model),
                    am.defined_region('quake',fx.QUAKE,bytes(4)),am.defined_region('world',fx.WORLD,bytes(4)),
                    am.defined_region('clock',0x6fce370,struct.pack('<f',1000.+tick*40.))]
                case=fx.Case(rng,objects,fx.rand_values(rng,200),60.,1,8,True)
                r=m.execute(fx.MOVE_EFFECT,[fx.POOL,0],regions,case.stubs(m));env=case.env();env.world_time=1000.+tick*40.
                lib.mu_sfx_effect_move(C.byref(e),C.byref(env))
                mismatch=fx.compare_effect(e,r['regions']['record'],record.defined,fx.MOVE_DEFINED|{'frame'}) if vc.ok(r) else None
                if mismatch is None:mismatch=fx.compare_calls(case.client_calls,case.c_calls)
                if mismatch is None and case.client_rand!=case.c_rand:mismatch=('rng',case.client_rand,case.c_rand)
                report.add('lifecycle',vc.ok(r) and mismatch is None,dict(skill=raw,step=tick,error=mismatch,stopped=r['stopped'],machine_error=r['error']))
                if not vc.ok(r):break
                original=r['regions']['record']
                if not original[0]:
                    report.add('retirement',not e.live,dict(skill=raw,step=tick));break
            else:report.add('retirement',False,dict(skill=raw,error='not retired within 64 ticks'))


MUTANTS=[('s->attack_time == 3','s->attack_time == 2'),('p->limit = 5;','p->limit = 6;'),
    ('s->frame >= 5.0f','s->frame >= 6.0f'),('s->prior_frame = 4.0f','s->prior_frame = 3.0f'),
    ('s->attack_time > 9','s->attack_time > 10'),('s->attack_time = 15; /*','s->attack_time = 14; /*'),
    ('if (s->base == 24) arrow(p, s, 1);','if (s->base == 24) arrow(p, s, 0);'),
    ('c->range = s->learned_index;','c->range = s->skill;'),('n < 36','n < 35'),
    ('n % 20 == 0','n % 19 == 0'),('(float)n * 10.0f','(float)n * 9.0f'),
    ('c->scale = 60.0f','c->scale = 50.0f'),('c->position[2] += 100.0f','c->position[2] += 90.0f'),
    ('c->arg7 = 0;','c->arg7 = -1;'),('p->target_index = s->target_index','p->target_index = 0'),
    ('+ 0.5f) * 100.0f','+ 0.4f) * 100.0f'),('0x583, 0','0x584, 0'),
    ('skill == 416 && base == 52','skill == 416 && base == 51')]
def run(cases,mutations):
    start=time.monotonic();text=pins.TEXT.read();data=pins.DATA.read()
    rep=compare(text,data,load(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}'),cases)
    lifecycle(text,data,rep)
    out={'families':rep.families,'mutants':[],'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256}
    out['all_equal']=all(f['cases']==f['equal'] for f in rep.families.values())
    if mutations and out['all_equal']:
        src=(ROOT/'reconstructed/combat/demo_skill_fx.c').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);dest=tmp/'demo_skill_fx.c'
            for i,(old,new) in enumerate(MUTANTS):
                lib=tmp/f'mutant-{i}.{fx.SUFFIX}'
                assert old in src,old
                dest.write_text(src.replace(old,new))
                subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC','-ffp-contract=off','-fno-fast-math',
                    '-I',str(ROOT/'reconstructed/combat'),str(dest),'-o',str(lib)],check=True,capture_output=True)
                r=compare(text,data,load(lib),210)
                fail=[f for f in r.families.values() if f['equal']!=f['cases']]
                stops=sum(bool(e.get('stopped')) for f in fail for e in f['first_failures'])
                out['mutants'].append(dict(index=i,detected=sum(f['cases']-f['equal'] for f in fail),stopped=stops))
                lib.unlink()
    out['all_mutants_caught']=(not mutations or len(out['mutants'])==len(MUTANTS)) and all(m['detected'] and not m['stopped'] for m in out['mutants'])
    out['cases']=sum(f['cases'] for f in rep.families.values());out['seconds']=time.monotonic()-start
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.cases<1:p.error('positive --cases required')
    out=run(a.cases,a.mutations)
    if a.output:a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2));raise SystemExit(not(out['all_equal'] and out['all_mutants_caught']))
