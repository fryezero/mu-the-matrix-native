#!/usr/bin/env python3
"""Five special Muun models: per-row admission, render alpha and atlas arguments.

Executes the complete original mesh caller for admitted rows. Three bone-effect branch entries are
observed/refused, never replaced with ordinary passes. No particle consumer is changed.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
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
import validate_muun_passes as vp
ROOT=Path(__file__).resolve().parents[1]
MODELS=(0x2b7a,0x2b7b,0x2b8d,0x2b8e,0x2b90)
BLOCKED={(0x2b8d,1),(0x2b8e,2),(0x2b90,4)}
BRANCHES=(0x17f7caa,0x17f815d,0x17f8872)
F3=C.c_float*3

def build(folder,source):
    p=Path(folder);(p/'special.c').write_text(source)
    out=p/('special.dylib' if sys.platform=='darwin' else 'special.so')
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wconversion','-fPIC',
        '-ffp-contract=off','-fno-fast-math','-shared','-I',str(ROOT/'reconstructed/muun'),str(p/'special.c'),
        str(ROOT/'reconstructed/muun/passes.c'),'-lm','-o',str(out)],check=True,capture_output=True)
    lib=C.CDLL(str(out));lib.mu_mv_special_admit.argtypes=[C.c_int32,C.c_int32]
    lib.mu_mv_mesh_pass.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_float,C.c_int32,C.c_float,C.c_int32,C.c_float,C.POINTER(vp.Pass)]
    lib.mu_mv_special_pass.argtypes=[C.c_int32,C.c_int32,C.c_void_p,C.c_float,C.c_float,C.c_float,C.c_float,
        C.POINTER(C.c_float),C.POINTER(vp.Pass),C.POINTER(C.c_float)]
    return lib

def samples(count,installed):
    rng=random.Random('muun-special-004')
    for model in MODELS:
        for mesh in range(9):
            for action in (0,2,4):
                r=bytearray(300);struct.pack_into('<ii',r,0,8347,mesh)
                struct.pack_into('<7fI',r,0x108,.3,.6,.8,.7,2.5,.2,.9,0x42)
                r[0x128:0x12c]=bytes([1,1,1,1])
                yield model,[bytes(r)],action,260.0,1.0,.5,'synthetic'
    for k in range(count):
        r=bytearray(300);model=rng.choice(MODELS);mesh=rng.randrange(9)
        struct.pack_into('<ii',r,0,8347,mesh)
        struct.pack_into('<7fI',r,0x108,*[rng.uniform(0,1) for _ in range(4)],rng.choice([1,2.5,4]),.1,.8,rng.choice([2,0x42,4,8]))
        r[0x128:0x12c]=bytes((k>>b)&1 for b in range(4))
        yield model,[bytes(r)],rng.randrange(5),rng.choice([-1000,-20,-1,0,19,20,259,260,299,300,123456]),rng.choice([0,.04,.5,1,2]),rng.uniform(-1,2),'synthetic'
    for mesh in (5,6):
        for clock in (2147483648.0,-2147483904.0,float('nan'),float('inf'),-float('inf')):
            r=bytearray(300);struct.pack_into('<ii',r,0,8347,mesh);struct.pack_into('<I',r,0x124,2)
            yield 0x2b8e,[bytes(r)],0,clock,1.0,0.0,'synthetic'
    if installed:
        records=vp.decoded('MuunRenderInfo.bmd');meshes=vp.decoded('MuunMeshInfo.bmd')
        for model in MODELS:
            info=next(r for r in records if struct.unpack_from('<i',r,4)[0]+0xae6==model)
            item=struct.unpack_from('<i',info,4)[0]
            actual=[r for r in meshes if struct.unpack_from('<i',r)[0]==item]
            for clock in (0,260,123456):
                for r in actual:yield model,[r],2,clock,1.0,.5,'installed'
                good=[r for r in actual if (model,struct.unpack_from('<i',r,4)[0]) not in BLOCKED]
                yield model,good,0,clock,1.0,.5,'ordered'

def compare(lib,machine,count,installed):
    rows={n:{'cases':0,'mismatches':0} for n in ('mesh','refusal','installed','ordered')}
    for model,records,action,clock,delta,initial,tag in samples(count,installed):
        obj,mdl,item,info=bytearray(0x3d8),bytearray(0x100),bytearray(0x260),bytearray(0x27c)
        color=F3(.7,.5,.3);alpha,light=.8,.75
        struct.pack_into('<i',obj,0x5c,model);struct.pack_into('<H',obj,0x2a,action)
        struct.pack_into('<i',obj,0x74,-1);struct.pack_into('<f',obj,0xa8,light);struct.pack_into('<f',obj,0xdc,alpha)
        struct.pack_into('<f',obj,0xc8,initial);struct.pack_into('<3f',mdl,0x54,*color)
        item[0x250:0x252]=bytes([12,1]);info[0x258]=1;calls=[]
        def record(m,mesh):calls.append((mesh,[m.argument(k) for k in range(8)],bytes(m.uc.mem_read(vp.MODEL+0x54,12))));return 0,32
        ptr=bytearray(max(4,len(records)*4));rs=[];textures=[-1 if k%2 else 0xa000+k for k in range(len(records))]
        for k,r in enumerate(records):
            struct.pack_into('<I',ptr,k*4,vp.ROW+0x1000*k)
            rs.append(am.defined_region(f'row{k}',vp.ROW+0x1000*k,r+struct.pack('<i',textures[k])))
        stubs={0xcd4ea8:lambda m:0,0xcd5d29:lambda m:(vp.ITEM,4),0x1807c1f:lambda m:0,
            0x9c2aea:lambda m:0,0x1807c32:lambda m:(vp.INFO,4),0x9beaa7:lambda m:len(records),
            0x9bca89:lambda m:(vp.POINTER+4*m.argument(0),4),0x966def:lambda m:record(m,False),
            0x966e4a:lambda m:record(m,True),0x9fa223:lambda m:m.x87_return(vc.f32(math.cos(m.float_argument(0))))}
        regions=[am.defined_region(n,a,p) for n,a,p in [('object',vp.OBJ,obj),('model',vp.MODEL,mdl),
            ('item',vp.ITEM,item),('info',vp.INFO,info),('pointers',vp.POINTER,ptr),
            ('clock',0x6fce370,struct.pack('<f',clock)),('delta',0x1cf103c,struct.pack('<f',delta))]]+rs
        hit=[]
        def refuse(uc,address,size,ignored):hit.append(address);machine.stop(('authored-refusal',hex(address)))
        hooks=[machine.uc.hook_add(machine.UC_HOOK_CODE,refuse,begin=a,end=a) for a in BRANCHES]
        try:r=machine.execute(0x17f76ec,[vp.MODEL,vp.OBJ,1,0,0,0xffffffff,0xffffffff],regions,stubs)
        finally:
            for h in hooks:machine.uc.hook_del(h)
        if hit:
            family='refusal';equal=len(records)==1 and lib.mu_mv_special_admit(model,struct.unpack_from('<i',records[0],4)[0])==0
            ok=r['stopped']==('authored-refusal',hex(hit[0]))
        else:
            family=tag if tag in rows else 'mesh';expected=[(False,[2,am.bits(alpha),0xffffffff,am.bits(light),0,0,0,0xffffffff],struct.pack('<3f',*color))]
            c8=C.c_float(initial)
            for k,raw in enumerate(records):
                p=vp.Pass();uv=(C.c_float*2)()
                lib.mu_mv_mesh_pass(raw,color,alpha,-1,light,textures[k],float(clock),C.byref(p))
                admitted=lib.mu_mv_special_admit(model,p.mesh)
                lib.mu_mv_special_pass(model,action,raw,delta,float(clock),alpha,light,C.byref(c8),C.byref(p),uv)
                expected.append((True,[p.mesh&0xffffffff,p.flags&0xffffffff,am.bits(p.alpha),p.blend&0xffffffff,
                    am.bits(p.light),am.bits(uv[0]),am.bits(uv[1]),p.texture&0xffffffff],struct.pack('<3f',*p.color)))
                if not admitted:expected=[];break
            equal=calls==expected and r['regions']['object'][0xc8:0xcc]==struct.pack('<f',c8.value) and r['regions']['model'][0x54:0x60]==struct.pack('<3f',*color)
            ok=r['ok']
        row=rows[family];row['cases']+=1
        if not ok or not equal:
            row['mismatches']+=1
            if 'first' not in row:row['first']={'model':model,'tag':tag,'checks':r['checks'],'error':r.get('error'),'stopped':r.get('stopped'),
                'got':repr(calls),'expected':repr(expected) if not hit else 'refusal','clock':clock,'delta':delta}
    return rows

MUTANTS=[('clock_guard','? INT32_MIN :','? 0 :'),('bone1','model == 0x2b8d && mesh == 1','model == 0x2b8d && mesh == 0'),
 ('bone2','model == 0x2b8e && mesh == 2','model == 0x2b8e && mesh == 3'),
 ('bone4','model == 0x2b90 && mesh == 4','model == 0x2b90 && mesh == 3'),
 ('pair','model == 0x2b7a || model == 0x2b7b','model == 0x2b7a || model == 0x2b8d'),
 ('fade_action','action == 2','action == 1'),('fade_speed','delta * 2.5f','delta * 2.0f'),
 ('rise_speed','delta * 0.35f','delta * 0.5f'),('rise_limit','*c8 > limit','*c8 < limit'),
 ('fade_alpha','pass->alpha = 1.0f','pass->alpha = 0.5f'),('atlas_frames','? 13 : 15','? 12 : 16'),
 ('atlas_period','(20 * frames)) / 20','(20 * frames)) / 10'),('atlas_u','frame % 4','frame % 3'),
 ('atlas_v','frame / 4','frame / 3'),('atlas_flags','pass->flags = 0x42','pass->flags = 2'),
 ('atlas_blend','pass->blend = pass->mesh','pass->blend = -1'),('atlas_texture','pass->texture = -1','pass->texture = 0')]
def run(count,mutations,installed):
    start=time.monotonic();text=pins.load_pinned(pins.TEXT.default_str(),pins.TEXT.size,pins.TEXT.sha256,'text')
    data=pins.load_pinned(pins.DATA.default_str(),pins.DATA.size,pins.DATA.sha256,'data');machine=vc.Combat(text,data)
    source=(ROOT/'reconstructed/muun/special.c').read_text()
    with tempfile.TemporaryDirectory(prefix='muun-special-') as td:
        p=Path(td);(p/'base').mkdir();families=compare(build(p/'base',source),machine,count,installed);mutants={}
        if mutations:
            for name,old,new in MUTANTS:
                if source.count(old)!=1:raise ValueError(name+' ambiguous anchor')
                (p/name).mkdir();rows=compare(build(p/name,source.replace(old,new)),machine,min(count,40),False)
                mutants[name]={'caught':sum(r['mismatches'] for r in rows.values())}
    return {'families':families,'cases':sum(r['cases'] for r in families.values()),'all_equal':all(r['mismatches']==0 for r in families.values()),
        'mutants':mutants,'all_mutants_caught':all(r['caught']>0 for r in mutants.values()),'installed':installed,
        'body_sha256':hashlib.sha256(text[0x17f76ec-am.TEXT_BASE:0x17f919e-am.TEXT_BASE]).hexdigest(),
        'wall_seconds':time.monotonic()-start}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=200);p.add_argument('--installed',action='store_true')
    p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    r=run(a.cases,a.mutations,a.installed)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));sys.exit(0 if r['all_equal'] and r['all_mutants_caught'] else 1)
