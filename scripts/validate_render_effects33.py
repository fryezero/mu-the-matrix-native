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
import re
import subprocess
import sys
import tempfile
import time
import actor_machine as am
import validate_render_effects30 as caller
import pins
import validate_combat as vc
import validate_particles as pt
import validate_skill_fx as fx
import validate_render_effects31 as previous
import validate_joints as jt
from validate_render_effects12 import BowRandom

ROOT=Path(__file__).resolve().parents[1]
EFFECTS=[(0x7f84,3),(0x46c,0),(0x412,1),(0x412,2),(0x583,0),(0x584,0)]
PARTICLES=[(0x7f3e,10)]
JOINTS=[(0x7fd8,3)]+[(0x7f79,s) for s in range(4)]
MUTANTS = [
    ('fx', 'summon_ground', 'skill_fx.c', 'sub == 1 || sub == 3 || sub == 4', 'sub == 1 || sub == 4', 'effect_create', (32644, 3)),
    ('fx', 'piercing_life', 'skill_fx.c', 'e->lifetime = 100; e->blend_mesh = 0;', 'e->lifetime = 99; e->blend_mesh = 0;', 'effect_create', (1132, 0)),
    ('fx', 'piercing_width', 'skill_fx.c', 'e->gravity = 0.0f; e->scale = 12.0f;', 'e->gravity = 0.0f; e->scale = 11.0f;', 'effect_create', (1132, 0)),
    ('fx', 'piercing_four', 'skill_fx.c', 'n < 4; ++n) { c.subtype = n;', 'n < 3; ++n) { c.subtype = n;', 'effect_create', (1132, 0)),
    ('fx', 'piercing_key', 'skill_fx.c', 'c.owner = -2; c.scale = e->scale; c.arg7 = 30;', 'c.owner = -2; c.scale = e->scale; c.arg7 = 31;', 'effect_create', (1132, 0)),
    ('fx', 'piercing_spin', 'skill_fx.c', 'e->gravity += 90.0f;', 'e->gravity += 80.0f;', 'effect_move', (1132, 0)),
    ('fx', 'piercing_prior', 'skill_fx.c', 'copy3(e->impact,e->position); copy3(e->position,o->position);', 'copy3(e->impact,o->position); copy3(e->position,o->position);', 'effect_move', (1132, 0)),
    ('fx', 'ground_joint_key', 'skill_fx.c', 'e->subtype == 3) c.arg7 = -1;', 'e->subtype == 3) c.arg7 = 0;', 'effect_move', (32644, 3)),
    ('jt', 'orange_palette', 'joints.c', 'l * (j->subtype == 3 ? 1.0f : F_0_4);', 'l * F_0_4;', 'joint_move', (32728, 3)),
    ('jt', 'trail_radius', 'bow_joints.inc', 'j->jitter[0] = scale * 1.5f;', 'j->jitter[0] = scale * 1.4f;', 'joint_create', (32633, 0)),
    ('jt', 'trail_steps', 'bow_joints.inc', 'n < 3; ++n) {\n                float m[12], v[3];', 'n < 2; ++n) {\n                float m[12], v[3];', 'joint_move', (32633, 0)),
    ('jt', 'trail_turn', 'bow_joints.inc', 'a[1] += 30.0f;', 'a[1] += 20.0f;', 'joint_move', (32633, 1)),
    ('jt', 'trail_fade', 'bow_joints.inc', 'j->light[k] /= 1.5f;', 'j->light[k] /= 1.2f;', 'joint_move', (32633, 2)),
    ('jt', 'trail_cap', 'bow_joints.inc', 'j->num_tails < j->max_tails - 1 || j->skill != 0', 'j->num_tails < j->max_tails - 2 || j->skill != 0', 'joint_move', (32633, 0)),
    ('fx', 'ice_enable', 'demo_skill_fx.c', 'if (!enabled) return;', 'if (enabled) return;', 'target_ice', None),
    ('fx', 'ice_angle', 'demo_skill_fx.c', 's.angle[2] += 180.0f;', 's.angle[2] += 90.0f;', 'target_ice', None),
    ('fx', 'ice_light', 'demo_skill_fx.c', 's.light[0] = 0.4f; s.light[1] = 0.3f;', 's.light[0] = 0.5f; s.light[1] = 0.3f;', 'target_ice', None),
    ('fx', 'ice_life', 'skill_fx.c', 'e->lifetime = 20; e->velocity = F_0_3; e->angle[0] = -20.0f;', 'e->lifetime = 19; e->velocity = F_0_3; e->angle[0] = -20.0f;', 'effect_create', (1042, 1)),
    ('fx', 'ice_presence', 'skill_fx.c', 'if (o->live && env_call(env,&presence,e))', 'if (o->live)', 'effect_move', (1042, 1)),
    ('fx', 'ice_hold', 'skill_fx.c', 'if (e->frame >= 4.0f) e->frame = 4.0f;', 'if (e->frame >= 4.0f) e->frame = 3.0f;', 'effect_move', (1042, 2)),
    ('fx', 'ice_expiry', 'skill_fx.c', '} else e->alpha -= 0.05f;', '} else e->alpha -= 0.04f;', 'effect_move', (1042, 2)),
    ('fx', 'ice_orbit', 'skill_fx.c', '{60.0f,0,0}, m[12], p[3];', '{50.0f,0,0}, m[12], p[3];', 'effect_move', (1042, 1)),
    ('pt', 'fire03_life', 'particles.c', 'p->lifetime = 24;\n            p->velocity[1] = -(float)(mu_pt_rand(h) % 16 + 32)', 'p->lifetime = 23;\n            p->velocity[1] = -(float)(mu_pt_rand(h) % 16 + 32)', 'create', (32574, 10)),
    ('pt', 'fire03_shrink', 'particles.c', 'p->subtype == 10) p->scale *= 0.95f;', 'p->subtype == 10) p->scale *= 0.9f;', 'move', (32574, 10)),
    ('pt', 'fire03_strip', 'particles.c', 'case 0x7f3e:\n        /* 0x015978bb', 'case 0x7f3f:\n        /* 0x015978bb', 'render', (32574, 10)),
]

MUTANTS += [
    ('fx','blood_life','skill_fx.c','e->lifetime = 70; e->field_64 = 0;','e->lifetime = 69; e->field_64 = 0;','effect_create',(0x583,0)),
    ('fx','blood_sword','skill_fx.c','c.type = 0x584;','c.type = 0x585;','effect_create',(0x583,0)),
    ('fx','blood_jitter','skill_fx.c','smod(env_rand(env),401)-200','smod(env_rand(env),400)-200','effect_move',(0x583,0)),
    ('fx','blood_scale','skill_fx.c','0.9f,0.9f,0.7f,0.7f','0.8f,0.9f,0.7f,0.7f','effect_move',(0x583,0)),
    ('fx','blood_center','skill_fx.c','} else if (e->lifetime == 35) {','} else if (e->lifetime == 34) {','effect_move',(0x583,0)),
    ('fx','sword_life','skill_fx.c','e->lifetime = 36; e->blend_light = 0.0f;','e->lifetime = 35; e->blend_light = 0.0f;','effect_create',(0x584,0)),
    ('fx','sword_owner','skill_fx.c','!o || o->client_hit != 1','!o || o->client_hit == 1','effect_move',(0x584,0)),
    ('fx','sword_pose','skill_fx.c','posed.frame = e->frame - 0.35f;','posed.frame = e->frame;','effect_move',(0x584,0)),
    ('fx','sword_samples','skill_fx.c','sample < 5; ++sample','sample < 4; ++sample','effect_move',(0x584,0)),
    ('fx','sword_bone','skill_fx.c','{61,53,50,44,39,14,19,24,29,34,10}','{60,53,50,44,39,14,19,24,29,34,10}','effect_move',(0x584,0)),
    ('fx','sword_end','skill_fx.c','n == 10 ? -40.0f : -20.0f','n == 10 ? -30.0f : -20.0f','effect_move',(0x584,0)),
    ('fx','sword_fade','skill_fx.c','e->lifetime > 24) e->blend_light += 0.0416f;','e->lifetime > 24) e->blend_light += 0.04f;','effect_move',(0x584,0)),
]
MUTANTS += [
    ('fx','piercing_sound_site','skill_fx.c','c.arg8 = 0x013ca7cc;','c.arg8 = 0x013ca7cd;','effect_create',(0x46c,0)),
    ('fx','blood_sound_site','skill_fx.c','c.arg8 = 0x013f2c46;','c.arg8 = 0x013f2c47;','effect_create',(0x583,0)),
]
MUTANTS += [('fx','arrow_child_word8','arrow_fx.inc','if (type == 0x46c) c.arg7 = -1;','if (type == 0x46c) c.arg7 = 0;','effect_create',(0x43b,2))]
MUTANTS += [('fx','arrow_child_key','arrow_fx.inc','c.range = type == 0x46c ? (int16_t)key : (int32_t)key;','c.range = key;','effect_create',(0x43b,2))]
NATIVE_MUTANTS = [
    ('self_owner','e->type == 0x10e6 || e->type == 0x46c))','e->type == 0x10e6))'),
    ('joint_key','stab || arrow ? call->arg7 : c->hero_key & 0xffff','stab ? call->arg7 : c->hero_key & 0xffff'),
    ('owner_heading','o->heading[1] = e->heading_yz[0];','o->heading[1] = 0;'),
    ('same_step_owner','c->effects[i].type == 0x70a || mu_sfx_is_arrow(c->effects[i].type)','c->effects[i].type == 0x70a'),
]

def owner_region(original, objects):
    r=original(objects)
    for i,o in enumerate(objects):
        r.define(fx.OBJECTS+0x400*i+0x110,struct.pack('<3f',*o.impact))
        r.define(fx.OBJECTS+0x400*i+0x170,struct.pack('<3f',*o.heading))
        r.define(fx.OBJECTS+0x400*i+0x2a,struct.pack('<H',o.action))
        r.define(fx.OBJECTS+0x400*i+0x3b,bytes([o.client_hit]))
    return r

def effect_family(text,data,lib,name,cases,report,kinds=None):
    saved=fx.EFFECT_KINDS,fx.OWNED_KINDS,fx.object_region,fx.MOVE_DEFINED,fx.Case,fx.random_effect
    def record(rng,kind):
        e=saved[5](rng,kind)
        if kind[0]==0x583:
            e.field_64=rng.randrange(10);e.lifetime=rng.choice([70,51,50,49,41,40,35,34,1,0])
        if kind[0]==0x584:
            e.action=0;e.frame=rng.choice([0.,2.,2.01,15.,29.99,30.]);e.lifetime=rng.choice([36,35,25,24,13,12,1,0])
        return e
    class Machine(fx.FxMachine):
        def execute(self,address,args,regions,*a,**kw):
            if address==fx.CREATE_EFFECT and args[0]==0x412 and args[1] in (1,2):
                for r in regions:
                    if r.name=='inputs':r.writable=True
            if address==fx.MOVE_EFFECT:
                for r in regions:
                    if r.name=='model':
                        for action in range(256):r.define(fx.MODEL+0x1000+16*action+4,struct.pack('<f',0.35))
            return super().execute(address,args,regions,*a,**kw)
    class Case(saved[4]):
        def __init__(self,rng,objects,*a,**kw):
            for o in objects:
                o.action=rng.choice([0,2,0x31,0x32,0x6e,0x6f]);o.client_hit=rng.choice([0,1,1,2])
                o.heading[:]=[rng.uniform(-180,180) for _ in range(3)]
                o.impact[:]=[rng.uniform(-200,200) for _ in range(3)]
            self.presence=rng.choice([0,1])
            super().__init__(rng,objects,*a,**kw)
        def stubs(self,m):
            stubs=super().stubs(m);stubs[0x1295ade]=lambda mm:(self.presence,4)
            def blur(mm):
                self.client_calls.append(('blur',fx.owner_of(mm.argument(0)),mm.floats(mm.argument(1),3),
                    mm.floats(mm.argument(2),3),mm.floats(mm.argument(3),3),*[mm.argument(i) for i in range(4,9)]));return 0
            stubs[0x1534ea1]=blur
            def transform(mm):
                index=(mm.argument(0)-0x6fce398)//0x30;vec=mm.floats(mm.argument(1),3)
                self.client_calls.append(('owner_bone',index,vec,mm.argument(3)))
                mm.uc.mem_write(mm.argument(2),struct.pack('<3f',*fx.owner_bone_answer(index,vec)))
                return 0,0x10
            stubs[fx.TRANSFORM_POSITION]=transform
            base_bone=stubs[fx.MODEL_BONE]
            def bone(mm):
                if mm.read32(fx.POOL+0x5c)!=0x584:return base_bone(mm)
                out,o,index,relative=[mm.argument(i) for i in range(4)]
                self.client_calls.append(('bone',fx.owner_of(o),index,mm.floats(relative,3)))
                p=mm.floats(o+0x158,3)
                mm.uc.mem_write(out,struct.pack('<3f',*[fx.f32(p[k]+fx.BONE_OFFSET[k]) for k in range(3)]))
                return 0,0x10
            stubs[fx.MODEL_BONE]=bone
            base_pose=stubs[fx.MODEL_POSE]
            def pose(mm):
                if mm.read32(fx.POOL+0x5c)!=0x584:return base_pose(mm)
                self.client_calls.append(('pose_full',hex(mm.argument(0)),mm.float_argument(1),mm.float_argument(2),
                    mm.argument(3),mm.floats(mm.argument(4),3),mm.floats(mm.argument(5),3),mm.argument(6),mm.argument(7)))
                return 0,0x20
            stubs[fx.MODEL_POSE]=pose
            base_sound=stubs[fx.PLAY_BUFFER]
            def sound(mm):
                if mm.read32(fx.POOL+0x5c) not in (0x46c,0x583):return base_sound(mm)
                esp=mm.uc.reg_read(mm.x86.UC_X86_REG_ESP)
                self.client_calls.append(('sound',mm.argument(0),fx.owner_of(mm.argument(1)),mm.argument(2),mm.read32(esp)-5))
                return 0
            stubs[fx.PLAY_BUFFER]=sound
            return stubs
        def env(self,*a,**kw):
            env=super().env(*a,**kw);base=self._keep[3]
            def call(ctx,cp,ep):
                c=cp.contents
                if c.routine==0x1295ade:return self.presence
                if c.routine==0x1534ea1:
                    self.c_calls.append(('blur',c.owner,list(c.position),list(c.target),list(c.light),c.type,c.subtype,c.arg7,c.arg8,0));return 0
                if c.routine==fx.MODEL_BONE and ep.contents.type==0x584:
                    self.c_calls.append(('bone',c.owner,c.range,[0.,0.,0.]));return 0
                if c.routine==fx.MODEL_POSE:
                    e=ep.contents
                    self.c_calls.append(('pose_full',hex(0x6fce398),e.frame,e.prior_frame,e.prior_action,
                        list(e.angle),[e.heading,*e.heading_yz],0,c.arg7));return 0
                if c.routine==fx.CREATE_EFFECT_WRAPPER and (ep.contents.type in (0x583,0x584) or c.type==0x46c):
                    self.c_calls.append(('effect',c.type,list(c.position),list(c.angle),list(c.light),c.subtype,
                        c.owner,[c.range&0xffffffff,0,0,0,fx.bits(c.scale),c.arg7&0xffffffff,0,0]));return 0
                if c.routine==fx.PLAY_BUFFER and ep.contents.type in (0x46c,0x583):
                    self.c_calls.append(('sound',c.type,c.owner,0,c.arg8));return 0
                if c.routine==fx.CREATE_JOINT:
                    self.c_calls.append(('joint',c.type,list(c.position),list(c.target),list(c.angle),c.subtype,
                        c.owner,c.scale,[c.arg7&0xffffffff,c.arg8&0xffffffff,0,0xffffffff,0,0xffffffff,0]))
                    return 0
                return base(ctx,cp,ep)
            self.presence_call=fx.CALL_FN(call);env.call=self.presence_call
            def transform(ctx,ep,index,vin,translate,out):
                vec=[vin[k] for k in range(3)]
                self.c_calls.append(('owner_bone',index,vec,translate))
                for k,v in enumerate(fx.owner_bone_answer(index,vec)):out[k]=v
            self.transform=fx.BONE_TRANSFORM_FN(transform);env.bone_transform=self.transform
            return env
    try:
        fx.EFFECT_KINDS=kinds or EFFECTS
        fx.OWNED_KINDS=saved[1] | {0x46c,0x583}
        fx.object_region=lambda objects:owner_region(saved[2],objects)
        fx.MOVE_DEFINED=saved[3] | {'impact','heading_yz','field_68'}
        fx.Case=Case;fx.random_effect=record
        getattr(fx,'family_'+name)(Machine(text,data),lib,random.Random('effects33-'+name),
            cases*len(fx.EFFECT_KINDS),report,defaultdict(int))
    finally:fx.EFFECT_KINDS,fx.OWNED_KINDS,fx.object_region,fx.MOVE_DEFINED,fx.Case,fx.random_effect=saved

def joint_family(text,data,lib,name,cases,report,kinds=None):
    saved=jt.KINDS,jt.random_joint,jt.object_region,jt.random_object
    def record(rng,kind):
        j=saved[1](rng,kind)
        if kind[0]==0x7f79:
            j.max_tails=50; j.num_tails=rng.choice([0,1,47,48,49]);j.velocity=float(240 if kind[1]==3 else kind[1]*90)
            j.jitter[:]=[rng.uniform(-50,50),0,0]
        return j
    def obj(rng):
        o=saved[3](rng)
        o.heading[:]=[rng.uniform(-180,180) for _ in range(3)]
        o.impact[:]=[rng.uniform(-200,200) for _ in range(3)]
        return o
    try:
        jt.random_object=obj
        jt.KINDS=kinds or JOINTS; jt.random_joint=record
        jt.object_region=lambda objects:owner_region(saved[2],objects)
        getattr(jt,'family_'+name)(fx.FxMachine(text,data),lib,BowRandom('effects33-'+name),
            cases*len(jt.KINDS),report,defaultdict(int))
    finally:jt.KINDS,jt.random_joint,jt.object_region,jt.random_object=saved

def particle_family(text,data,lib,name,cases,report,kinds=None):
    saved=pt.KINDS
    try:
        pt.KINDS=kinds or PARTICLES
        getattr(pt,'family_'+name)(pt.PtMachine(text,data),lib,random.Random('effects33-'+name),
            cases*len(pt.KINDS),report,defaultdict(int))
    finally:pt.KINDS=saved

def target_ice(text,data,lib,cases,report,kinds=None):
    lib.mu_skill33_target_ice.argtypes=[C.POINTER(caller.Input),C.c_int,C.POINTER(caller.Plan)]
    class Machine(caller.Machine):
        def stub_entry(self,uc,address,size,ignored):
            if address in (0x1256cc7,0x1256cea):
                for reg,value in self.preserved.items():uc.reg_write(reg,value)
                uc.mem_write(am.TIB,struct.pack('<I',am.SEH_HEAD))
                uc.reg_write(self.x86.UC_X86_REG_ESP,am.ENTRY_ESP+4)
                uc.reg_write(self.x86.UC_X86_REG_EIP,am.SENTINEL)
                return
            super().stub_entry(uc,address,size,ignored)
    m=Machine(text,data);rng=random.Random('effects33-ice-caller')
    for n in range(cases):
        enabled=[0,1,2,255][n%4];s=caller.Input();s.owner=0
        for k in range(3):
            s.position[k]=rng.uniform(-1000,1000);s.angle[k]=rng.uniform(-180,180);s.light[k]=rng.uniform(0,1)
        caster=am.undefined_region('caster',caller.CHAR,0x3670);caster.define(caller.CHAR+7,bytes([enabled]))
        target=am.undefined_region('target',fx.OBJECTS,0x400)
        for offset,values in [(0x158,s.position),(0x164,s.angle),(0xec,s.light)]:
            target.define(fx.OBJECTS+offset,struct.pack('<3f',*values))
        calls=[]
        def delete(mm):
            calls.append(['delete',mm.argument(0),mm.argument(1),mm.argument(2)]);return 0
        def effect(mm):
            calls.append(['effect',mm.argument(0),mm.floats(mm.argument(1),3),mm.floats(mm.argument(2),3),
                mm.floats(mm.argument(3),3),mm.argument(4),mm.argument(5),[mm.argument(i) for i in range(6,14)]])
            mm.write(mm.argument(3),struct.pack('<3f',0.4,0.3,0.2));return 0
        result=m.execute(0x1256b8a,[0],[caster,target],
            {0x142ec5c:delete,fx.CREATE_EFFECT_WRAPPER:effect,0x1256cc7:lambda m:0,0x1256cea:lambda m:0},
            frame=(0x400,{-0x18:caller.CHAR,-0x14:fx.OBJECTS}))
        plan=caller.Plan();lib.mu_skill33_target_ice(C.byref(s),enabled,C.byref(plan));mine=[]
        for row in plan.calls[:plan.count]:
            c=row.visual
            mine.append(['delete',c.type,fx.object_address(c.owner),c.subtype] if c.routine==0x142ec5c
                        else caller.normalized(c,row.site))
        report.add('target_ice',vc.ok(result) and vc._same_call(calls,mine),
            dict(enabled=enabled,calls=calls,mine=mine,stopped=result['stopped'],error=result['error'],checks=result['checks']))
        report.cover('target_ice','enabled '+str(enabled))

def model_loaders(text,data,report):
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32
    source=(ROOT/'native/core/mu_combat.c').read_text()
    for start,end,kind,stem in [(0x1834609,0x183461f,0x46c,'Piercing'),
                              (0x1836122,0x1836138,0x584,'blood_storm_sword')]:
        ins=list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(text[start-am.TEXT_BASE:end-am.TEXT_BASE],start))
        pushes=[int(i.op_str,0) for i in ins if i.mnemonic=='push']
        strings=[data[p-am.DATA_BASE:].split(b'\0')[0].decode() for p in pushes[1:3]]
        expected='Data/Skill/'+stem+'.bmd'
        report.add('model_loaders',pushes[0]==-1 and pushes[3]==kind and strings==[stem,'Data\\Skill\\']
            and ins[-1].mnemonic=='call' and ins[-1].op_str=='0x18202b4'
            and '{'+hex(kind)+', "'+expected+'"}' in source,
            dict(type=hex(kind),strings=strings,path=expected))

def render_dispatch(text,data,cases,report):
    import validate_render_effects11 as re11
    machine=fx.FxMachine(text,data)
    for kind in EFFECTS:
        e=fx.Effect();e.type,e.subtype=kind
        raw,mask=fx.effect_to_bytes(e,fx.MOVE_DEFINED|{'field_68','field_80','field_78'})
        calls=[]
        def draw(mm):calls.append([mm.argument(i) for i in range(6)]);return 0
        stubs=fx.Case(random.Random(33),[],[],0).stubs(machine)
        stubs.update({re11.RENDER_OBJECT:draw,re11.RENDER_NEXT:fx.jump_stub(re11.RENDER_END)})
        result=machine.execute(0x15183c2,[0],[am.Region('effect',fx.POOL,raw,mask)],stubs,
            frame=pt.mid_frame(re11.RENDER_FRAME,{-0x10:fx.POOL}),cleanup=4)
        expected=[[fx.POOL,0,0,0,0xffffffff,0xffffffff]] if kind[0]<0x7a4 else []
        report.add('effect_render_dispatch',vc.ok(result) and calls==expected,
            dict(kind=kind,calls=calls,stopped=result['stopped'],error=result['error'],checks=result['checks']))
        report.cover('effect_render_dispatch',str(kind))

def build_native_host(directory,mutation=None):
    directory=Path(directory);native=ROOT/'native';source=native/'tests/effects33_host.c'
    if mutation:
        old,new=mutation;original=native/'core/mu_combat.c';code=original.read_text()
        if code.count(old)!=1:raise ValueError(old)
        code=code.replace(old,new)
        code=re.sub(r'#include "(\.\./[^"\n]+)"',lambda m:'#include "'+str((original.parent/m[1]).resolve())+'"',code)
        core=directory/'mutant.c';core.write_text(code);source=directory/'host.c'
        source.write_text((native/'tests/effects33_host.c').read_text().replace('../core/mu_combat.c',str(core)))
    obj,host=directory/'host.o',directory/'host'
    subprocess.run(['clang','-std=c11','-O1','-ffp-contract=off','-I',str(native/'build/gen'),
        '-I',str(native/'session'),'-I',str(native/'core'),'-c',str(source),'-o',str(obj)],check=True,capture_output=True)
    command=['clang++',str(obj),str(native/'build/libmunative.a'),str(native/'build/libmusession_world.a'),'-lm','-o',str(host)]
    if sys.platform=='darwin':command+=['-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp',
        '-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg','-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation']
    else:command+=['-lcryptopp','-ljpeg']
    subprocess.run(command,check=True,capture_output=True);return host

def native_checks(report,mutation=None):
    with tempfile.TemporaryDirectory(prefix='effects33-native-') as tmp:
        host=build_native_host(tmp,mutation);r=subprocess.run([str(host)],capture_output=True,text=True)
        report.add('native_callbacks',r.returncode==0,dict(exit=r.returncode,stderr=r.stderr[-2000:]))

def run(cases,mutations=False,only_mutants=None):
    start=time.monotonic();text,data=pins.TEXT.read(),pins.DATA.read();report=pt.Report()
    lib=fx.load_library(ROOT/('reconstructed/combat/libcombat.'+fx.SUFFIX))
    for name in ('effect_create','effect_move'):effect_family(text,data,lib,name,cases,report)
    effect_family(text,data,lib,'effect_create',cases,report,[(0x43b,2)])
    target_ice(text,data,lib,cases,report)
    jlib=jt.load_library(ROOT/('reconstructed/joints/libclient_joints.'+fx.SUFFIX))
    for name in ('joint_create','joint_move','joint_render'):joint_family(text,data,jlib,name,cases,report)
    plib=pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+fx.SUFFIX))
    for name in ('create','move','render'):particle_family(text,data,plib,name,cases,report)
    model_loaders(text,data,report)
    render_dispatch(text,data,cases,report)
    native_checks(report)
    from validate_render_effects26 import bitmap_checks
    import validate_render_effects26 as loader
    saved=loader.BITMAPS
    try:
        loader.BITMAPS=[(0x01820f59,0x7f3e,'Effect\\Fire03.jpg')]
        bitmap_checks(text,data,report)
    finally:loader.BITMAPS=saved
    mutants=[]
    if mutations and all(f['cases']==f['equal'] for f in report.families.values()):
        with tempfile.TemporaryDirectory(prefix='effects33-mutants-') as tmp:
            for category,label,file,old,new,family,kind in MUTANTS:
                if only_mutants and label not in only_mutants:continue
                mutant=previous.compile_mutant(tmp,category,label,file,old,new);r=pt.Report()
                if family=='target_ice':target_ice(text,data,mutant,100,r)
                else:(particle_family if category=='pt' else joint_family if category=='jt' else effect_family)(text,data,mutant,family,100,r,[kind] if kind else None)
                f=r.families[family]
                mutants.append(dict(name=label,detected=f['cases']-f['equal'],
                    stopped=sum(bool(x.get('stopped') or x.get('error')) for x in f['first_failures'])))
                print('mutant',label,mutants[-1],flush=True)
            for label,old,new in NATIVE_MUTANTS:
                if only_mutants and label not in only_mutants:continue
                r=pt.Report();native_checks(r,(old,new));f=r.families['native_callbacks']
                mutants.append(dict(name=label,detected=f['cases']-f['equal'],stopped=0))
                print('mutant',label,mutants[-1],flush=True)
    return dict(families=report.families,coverage=report.coverage,
        all_equal=all(f['cases']==f['equal'] for f in report.families.values()),
        mutants=mutants,all_mutants_caught=(not mutations or len(mutants)==(len(only_mutants) if only_mutants else len(MUTANTS)+len(NATIVE_MUTANTS))) and
            all(m['detected'] and not m['stopped'] for m in mutants),
        seconds=time.monotonic()-start,text_sha256=pins.TEXT.sha256,data_sha256=pins.DATA.sha256,
        bodies={name:hashlib.sha256(text[a-0x401000:b-0x401000]).hexdigest() for name,(a,b) in
            dict(ground_create=(0x13c80a3,0x13c829e),ground_move=(0x143fbda,0x14400b6),
                piercing_create=(0x13ca40b,0x13ca7ec),piercing_move=(0x1463c5e,0x146409b),
                ice_create=(0x13d01f8,0x13d04e1),ice_move=(0x146bbb8,0x146bfef),
                blood_create=(0x13f2b83,0x13f2d82),blood_move=(0x14a18fc,0x14a2131),
                blood_loader=(0x1836157,0x1836177),ice_caller=(0x1256b8a,0x1256cc7),
                fire03_loader=(0x1820f59,0x1820f75)).items()})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--only-mutant',action='append');p.add_argument('--output');args=p.parse_args()
    if args.cases<1:p.error('--cases must be positive')
    result=run(args.cases,args.mutations,set(args.only_mutant or []))
    if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['all_equal'] and result['all_mutants_caught'] else 1
if __name__=='__main__':raise SystemExit(main())
