#!/usr/bin/env python3
"""Authored Muun rider/secondary callers against pinned instructions.

Services are named in each family. No original scene, packet or live process is executed.
"""
import argparse
import ctypes as C
import hashlib
import itertools
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import time
import actor_machine as am
import pins
import validate_combat as vc
from validate_muun_passes import Pass
from validate_muun_secondary import SLOT,OBJ,OWNER,INFO,MODEL,BASE,region,put,vector
ROOT=Path(__file__).resolve().parents[1]
F3=C.c_float*3
class Particle(C.Structure):
    _fields_=[('type',C.c_int32),('subtype',C.c_int32),('scale',C.c_float),('light',F3)]
BODIES={'lift':(0x9c046a,0x9c0518),'placement':(0x13639a7,0x1363a62),
        'fade':(0x9bf225,0x9bf31e),'render':(0x9bf31e,0x9bf58b),
        'particles':(0x9bfe13,0x9c0443),'transition':(0x9c2371,0x9c2539),
        'buff_mesh':(0x17f746f,0x17f76ec)}
def build(folder,source):
    p=Path(folder);(p/'riding.c').write_text(source)
    out=p/('riding.dylib' if sys.platform=='darwin' else 'riding.so')
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wconversion','-fPIC',
        '-ffp-contract=off','-fno-fast-math','-shared','-I',str(ROOT/'reconstructed/muun'),str(p/'riding.c'),
        '-o',str(out)],check=True,capture_output=True)
    lib=C.CDLL(str(out));lib.mu_mv_rider_lifts.argtypes=[C.c_uint16]
    lib.mu_mv_rider_position.argtypes=[C.POINTER(C.c_float)]*3
    lib.mu_mv_owner_fade.argtypes=[C.c_int,C.c_float];lib.mu_mv_owner_fade.restype=C.c_float
    lib.mu_mv_mount_mode.argtypes=[C.c_int,C.c_int]
    lib.mu_mv_mount_counter.argtypes=[C.c_int32,C.c_int]
    lib.mu_mv_mount_particles.argtypes=[C.c_int32,C.c_int32,C.POINTER(Particle)]
    lib.mu_mv_transition_step.argtypes=[C.POINTER(C.c_int),C.POINTER(C.c_float),C.c_float,C.c_float]
    lib.mu_mv_mount_buff_pass.argtypes=[C.c_int32,C.c_float,C.c_float,C.c_float,C.POINTER(Pass),C.POINTER(C.c_float)]
    return lib

def read(m,address,size): return bytes(m.uc.mem_read(address,size))

def compare(lib,machine,count):
    rows={n:{'cases':0,'mismatches':0} for n in ('lift','placement','fade','render','particles','transition','buff_mesh')}
    def check(n,r,equal,detail=None):
        row=rows[n];row['cases']+=1
        if not r['ok'] or not equal:
            row['mismatches']+=1
            if 'first' not in row:row['first']={'checks':r['checks'],'error':r.get('error'),'stopped':r.get('stopped'),'detail':detail}
    for action in list(range(402))+[65535]:
        slot=bytearray(244);owner=bytearray(0x3670);put(slot,4,'I',OWNER);put(owner,0x327e,'H',action)
        r=machine.execute(0x9c046a,[],[region('slot',SLOT,slot),region('owner',OWNER,owner)],{},ecx=SLOT)
        check('lift',r,r['eax']&255==lib.mu_mv_rider_lifts(action),action)
    rng=random.Random('muun-riding-004')
    # Bounded RenderCharacter placement block, with its existing EBP frame supplied.
    # The end hook checks the whole block then restores the supplied caller frame.
    for k in range(count):
        slot=bytearray(244);obj=bytearray(0x3d8);mdl=bytearray(0x100)
        p=F3(*[rng.uniform(-20000,20000) for _ in range(3)]);off=F3(*[rng.uniform(-100,100) for _ in range(3)])
        put(slot,0xe4,'3f',*off);put(obj,0x158,'3f',*p)
        enabled=k%3!=0;calls=[]
        def add(m):
            a=m.uc.reg_read(m.x86.UC_X86_REG_ECX);b=m.argument(0)
            x=struct.unpack('<3f',read(m,a,12));y=struct.unpack('<3f',read(m,b,12))
            m.write(a,struct.pack('<3f',*[am.f32(x[i]+y[i]) for i in range(3)]));return a,4
        def copy(m):
            m.write(m.uc.reg_read(m.x86.UC_X86_REG_ECX),read(m,m.argument(0),12));calls.append(1);return 0,4
        def finish(uc,address,size,ignored):
            uc.reg_write(machine.x86.UC_X86_REG_ESP,am.ENTRY_ESP+4)
            uc.reg_write(machine.x86.UC_X86_REG_EBP,machine.preserved[machine.x86.UC_X86_REG_EBP])
            uc.mem_write(am.TIB,struct.pack('<I',am.SEH_HEAD));uc.reg_write(machine.x86.UC_X86_REG_EIP,am.SENTINEL)
        hook=machine.uc.hook_add(machine.UC_HOOK_CODE,finish,begin=0x1363a62,end=0x1363a62)
        try:
            r=machine.execute(0x13639a7,[OWNER,OBJ],[region('slot',SLOT,slot),region('object',OBJ,obj),region('model',MODEL,mdl)],
                {0x9c0443:lambda m:int(enabled),0x9c046a:lambda m:int(enabled),0xcfc922:vector,
                 0x1094018:lambda m:SLOT+0xe4,0xcfccae:add,0xcfc8f2:copy},frame=(0x800,{-0x250:SLOT,-0x14:MODEL}))
        finally:machine.uc.hook_del(hook)
        out=F3();lib.mu_mv_rider_position(p,off,out)
        check('placement',r,r['regions']['object'][0x158:0x164]==struct.pack('<3f',*(out if enabled else p)) and bool(calls)==enabled)
    # Full update caller; FadeAlpha is an already verified service supplied here at its result boundary.
    for kind,alpha in itertools.product((0,1,2,3),(-1.0,-.05,0,.05,.1,.9,1.0)):
        slot=bytearray(244);obj=bytearray(0x3d8);base=bytearray(0x3d8);owner=bytearray(0x3670)
        put(slot,8,'I',BASE);put(slot,0xbc,'I',OBJ);put(base,0x34c,'I',OWNER+0x3254)
        put(obj,0x34c,'I',OWNER+0x3254);put(obj,0xdc,'f',alpha);owner[0x328e]=kind
        r=machine.execute(0x9bf225,[],[region('slot',SLOT,slot),region('object',OBJ,obj),region('base',BASE,base),region('owner',OWNER,owner)],
            {0x9a99a9:lambda m:1,0x95f977:lambda m:1,0x12af883:lambda m:0,
             0x9bf58b:lambda m:1,0x9bf626:lambda m:1,0x9bf6f8:lambda m:1,0x9bf820:lambda m:1},ecx=SLOT)
        expected=struct.pack('<f',lib.mu_mv_owner_fade(kind,alpha));got=r['regions']['object']
        check('fade',r,got[0xdc:0xe0]==expected and got[0xa8:0xac]==expected,{'kind':kind,'alpha':alpha,'got':struct.unpack_from('<f',got,0xdc)[0]})
    # Full render: counters advance even offscreen after the admission gates; buff12 changes the request mode.
    for admitted,frustum,buff,owner_object,counter in itertools.product((0,1),(0,1),(0,1,2),(0,1),(0,1,99,100,101)):
        slot=bytearray(244);obj=bytearray(0x3d8);owner=bytearray(0x3670);info=bytearray(0x27c)
        put(slot,4,'I',OWNER);put(slot,0xc,'I',INFO);put(slot,0xbc,'I',OBJ);put(slot,0xf0,'i',counter)
        put(info,4,'i',8423);owner[0x31e8]=1-admitted;put(obj,0x34c,'I',OWNER+0x3254 if owner_object else 0)
        calls=[];action_calls=[]
        def draw(m):calls.append([m.argument(k) for k in range(6)]);return 0
        def has_buff(m):return (0 if m.argument(0)==26 else buff),4
        stubs={0x9a9ae2:lambda m:0,0x95f977:lambda m:1,0x1295ade:has_buff,
            0x129dcda:lambda m:8423,0x106ccd5:lambda m:0,0xcfc922:vector,
            0x16ccce7:lambda m:frustum,0x16d4fe4:draw,0x9c104e:lambda m:0,
            0x106c382:lambda m:action_calls.append([m.argument(0),m.argument(1)]) or 0}
        r=machine.execute(0x9bf31e,[],[region('slot',SLOT,slot),region('object',OBJ,obj),region('owner',OWNER,owner),region('info',INFO,info)],stubs,ecx=SLOT)
        new=lib.mu_mv_mount_counter(counter,admitted)
        expected=[[OBJ,1,0,lib.mu_mv_mount_mode(owner_object,buff),0xffffffff,0xffffffff]] if admitted and frustum else []
        check('render',r,struct.unpack_from('<i',r['regions']['slot'],0xf0)[0]==new and calls==expected and action_calls==([[OWNER,0]] if new==1 else []),{'got':calls,'expected':expected})
    # Whole per-model particle producer. Model lookup / random-bone transform are supplied services.
    # Compare all eight CreateParticle arguments and the transformed zero point in order.
    for model,rand in itertools.product(range(0x5ca,0x5d4),(0,1,2,32767)):
        slot=bytearray(244);obj=bytearray(0x3d8);put(slot,0xbc,'I',OBJ);put(obj,0x5c,'i',model)
        angle=(10.0,20.0,30.0);point=(12.5,-31.25,480.0);put(obj,0x164,'3f',*angle);calls=[]
        def transform(m):
            assert m.argument(3)==1
            assert read(m,m.argument(1),12)==bytes(12)
            m.uc.mem_write(m.argument(2),struct.pack('<3f',*point));return 0,16
        def emit(m):
            calls.append([m.argument(0),list(struct.unpack('<3f',read(m,m.argument(1),12))),list(struct.unpack('<3f',read(m,m.argument(2),12))),
                list(struct.unpack('<3f',read(m,m.argument(3),12))),m.argument(4),am.from_bits(m.argument(5)),m.argument(6),m.argument(7)])
            return 0
        r=machine.execute(0x9bfe13,[0],[region('slot',SLOT,slot),region('object',OBJ,obj)],
            {0x966cc4:lambda m:(MODEL,4),0xeaa8cf:lambda m:MODEL,0x129f24f:lambda m:BASE,
             0x12b6ef1:transform,0xcfc94a:lambda m:m.uc.reg_read(m.x86.UC_X86_REG_ECX),0x1989721:lambda m:rand,0x168fafd:emit},ecx=SLOT,cleanup=4)
        out=(Particle*2)();n=lib.mu_mv_mount_particles(model,rand,out)
        expected=[[out[i].type,list(point),list(angle),list(out[i].light),out[i].subtype,out[i].scale,0,0] for i in range(n)]
        check('particles',r,calls==expected,{'model':model,'got':calls,'expected':expected})
    # Whole auxiliary update caller: periodic and pending-command clocks are named services;
    # the remote clock's add/test executes its original timer routines.
    for remote,elapsed,period,delta in itertools.product((0,1,2),(0.0,.49,2.99,3.0),(0.5,3.0),(0,.01,.04,1.0)):
        aux=bytearray(84);obj=bytearray(0x3d8);put(aux,0,'I',OBJ);put(aux,0x20,'f',delta)
        aux[0x44]=remote;put(aux,0x3c,'2f',period,elapsed);put(aux,0x48,'3f',10,20,30)
        put(obj,0x158,'3f',100,200,300);put(obj,0x164,'3f',1,2,3);put(obj,0xec,'3f',.2,.4,.6);calls=[]
        def effect(m):
            calls.append({'args':[m.argument(k) for k in range(14)],
                'position':list(struct.unpack('<3f',read(m,m.argument(1),12))),
                'angle':list(struct.unpack('<3f',read(m,m.argument(2),12))),
                'light':list(struct.unpack('<3f',read(m,m.argument(3),12)))})
            return 0
        r=machine.execute(0x9c2371,[],[region('aux',SLOT,aux),region('object',OBJ,obj)],
            {0x9c1c1e:lambda m:0,0x9c29dc:lambda m:0,0x9c29f0:lambda m:0,0xcfc922:vector,
             0xcfc94a:lambda m:m.uc.reg_read(m.x86.UC_X86_REG_ECX),0x13c0eaa:effect},ecx=SLOT)
        er=C.c_int(remote);ee=C.c_float(elapsed);n=lib.mu_mv_transition_step(C.byref(er),C.byref(ee),period,delta)
        got=r['regions']['aux'];eq=(got[0x44]==er.value and got[0x40:0x44]==struct.pack('<f',ee.value) and len(calls)==n)
        if n and calls:
            c=calls[0];point=F3();lib.mu_mv_rider_position(F3(100,200,300),F3(10,20,30),point)
            eq &= c['args'][0]==0x47a and c['args'][4:]==[0,0,0xffffffff,0,0,0,0,0xffffffff,0,0]
            eq &= c['position']==list(point) and c['angle']==[1,2,3] and c['light']==list(F3(.2,.4,.6))
        check('transition',r,eq,{'remote':remote,'elapsed':elapsed,'period':period,'delta':delta,'calls':calls})
    # Buff-0x12 local-owner mesh consumer: remote/class visibility is outside this fixture.
    for meshes in (0,1,4):
        mdl=bytearray(0x100);obj=bytearray(0x3d8);put(mdl,0x24,'h',meshes);put(obj,0x34c,'I',OWNER+0x3254)
        put(obj,0x74,'i',-1);put(obj,0xa8,'3f',.75,.2,.3);calls=[]
        def mesh(m):calls.append([m.argument(k) for k in range(8)]);return 0,32
        r=machine.execute(0x17f746f,[MODEL,OBJ],[region('model',MODEL,mdl),region('object',OBJ,obj),region('hero',0xa39d754,struct.pack('<I',OWNER))],
            {0x95f6db:lambda m:OWNER,0x9a13f4:lambda m:OWNER,0xcfc922:vector,0x966e4a:mesh},ecx=0)
        bp=Pass();uv=(C.c_float*2)();lib.mu_mv_mount_buff_pass(-1,.75,.2,.3,C.byref(bp),uv)
        expected=[[k,bp.flags,am.bits(bp.alpha),bp.blend&0xffffffff,am.bits(bp.light),am.bits(uv[0]),am.bits(uv[1]),bp.texture] for k in range(meshes)]
        expected_color=struct.pack('<3f',*bp.color)
        check('buff_mesh',r,calls==expected and r['regions']['model'][0x54:0x60]==expected_color,{'calls':calls,'expected':expected})
    return rows

MUTANTS=[('buff_flags','.flags = 0x4040','.flags = 2'),('buff_alpha','.alpha = 0.5f','.alpha = 0.6f'),
 ('buff_texture','.texture = 0x7fcf','.texture = 0x7f66'),('buff_u','u * 8.0f','u * 4.0f'),('buff_v','v * 2.0f','v * 3.0f'),('lift_low','a >= 0x26','a > 0x26'),('lift_high','a < 0x142','a < 0x141'),
 ('placement','position[k] + offset[k]','position[k] - offset[k]'),('fade_kind','owner_kind == 2','owner_kind == 1'),
 ('fade_zero','alpha != 0.0f','alpha > 0.0f'),('fade_step','alpha - 0.1f','alpha - 0.2f'),
 ('buff_mode','? 10 : 0','? 9 : 0'),('buff_exact','buff18 == 1','buff18 != 0'),
 ('counter_gate','if (!admitted)','if (admitted)'),('counter_wrap','counter > 100','counter > 101'),
 ('particle_kind','0x8081 +','0x8080 +'),('particle_subtype','out[1].subtype = 19','out[1].subtype = 18'),
 ('particle_scale','out[1].scale = 3.5f','out[1].scale = 3.0f'),('particle_colour','0.98f','0.88f'),
 ('transition_gate','*remote != 1','*remote == 1'),('transition_expiry','*elapsed >= period','*elapsed > period'),
 ('transition_reset','*elapsed = 0.0f','*elapsed = 1.0f')]
def run(count,mutations):
    start=time.monotonic();text=pins.load_pinned(pins.TEXT.default_str(),pins.TEXT.size,pins.TEXT.sha256,'text')
    data=pins.load_pinned(pins.DATA.default_str(),pins.DATA.size,pins.DATA.sha256,'data');machine=vc.Combat(text,data)
    source=(ROOT/'reconstructed/muun/riding.c').read_text()
    with tempfile.TemporaryDirectory(prefix='muun-riding-') as td:
        p=Path(td);(p/'base').mkdir();families=compare(build(p/'base',source),machine,count);mutants={}
        if mutations:
            for name,old,new in MUTANTS:
                if old not in source:raise ValueError(name+' missing anchor')
                (p/name).mkdir();rows=compare(build(p/name,source.replace(old,new)),machine,min(count,20))
                mutants[name]={'caught':sum(r['mismatches'] for r in rows.values())}
    return {'families':families,'cases':sum(r['cases'] for r in families.values()),'all_equal':all(r['mismatches']==0 for r in families.values()),
        'mutants':mutants,'all_mutants_caught':all(r['caught']>0 for r in mutants.values()),
        'bodies':{n:{'start':hex(a),'end':hex(b),'sha256':hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()} for n,(a,b) in BODIES.items()},
        'wall_seconds':time.monotonic()-start}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=200)
    p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    r=run(a.cases,a.mutations)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));sys.exit(0 if r['all_equal'] and r['all_mutants_caught'] else 1)
