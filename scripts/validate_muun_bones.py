#!/usr/bin/env python3
"""Whole Muun mesh caller, including all four installed bone-effect rows.

Bone lookup/posed-zero transforms, RangedRandom and CRT trig/sqrt are supplied services.
Vector arithmetic, normalization, atlas, bone-sprite helper and caller ordering execute as original code.
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
import validate_muun_special as vs
ROOT=Path(__file__).resolve().parents[1]
F3=C.c_float*3
POINTS=F3*7
F12=C.c_float*12
BONES=(11,18,12,13,22,23,52)
class Op(C.Structure):
    _fields_=[(n,C.c_int32) for n in ('particle','type','subtype')]+[('position',F3),('light',F3),('scale',C.c_float),('rotation',C.c_float)]
OPS=Op*8

def build(folder,source=None):
    p=Path(folder);s=p/'bone_fx.c';s.write_text(source or (ROOT/'reconstructed/muun/bone_fx.c').read_text())
    libpath=p/('bones.dylib' if sys.platform=='darwin' else 'bones.so')
    base=ROOT/'reconstructed/muun'
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wconversion','-fPIC',
        '-ffp-contract=off','-fno-fast-math','-shared','-I',str(base),str(s),str(base/'passes.c'),str(base/'special.c'),'-lm','-o',str(libpath)],check=True,capture_output=True)
    lib=C.CDLL(str(libpath))
    lib.mu_mv_mesh_pass.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_float,C.c_int32,C.c_float,C.c_int32,C.c_float,C.POINTER(vp.Pass)]
    lib.mu_mv_special_pass.argtypes=[C.c_int32,C.c_int32,C.c_void_p,C.c_float,C.c_float,C.c_float,C.c_float,C.POINTER(C.c_float),C.POINTER(vp.Pass),C.POINTER(C.c_float)]
    lib.mu_mv_bone_mesh.argtypes=[C.c_int32,C.c_int32,C.c_float,C.c_float,C.c_float,C.POINTER(vp.Pass),C.POINTER(C.c_float)]
    lib.mu_mv_bone_effects.argtypes=[C.c_int32,C.c_int32,C.c_float,C.c_float,C.POINTER(F3),C.POINTER(C.c_float),C.c_int32,C.c_int32,C.POINTER(Op)]
    return lib

def samples(count,installed):
    rng=random.Random('muun-bones-005')
    for k in range(count):
        model,mesh=((0x2b8d,1),(0x2b8e,2),(0x2b90,4))[k%3]
        row=bytearray(300);struct.pack_into('<ii',row,0,123,mesh)
        struct.pack_into('<7fI',row,0x108,.3,.6,.8,.7,2.5,.2,.9,0x42)
        row[0x128:0x12c]=bytes((k>>b)&1 for b in range(4))
        yield model,[bytes(row)],rng.choice([-1000,-20,-1,0,19,20,259,260,299,300,123456]),k,'synthetic'
    if installed:
        records=vp.decoded('MuunRenderInfo.bmd');meshes=vp.decoded('MuunMeshInfo.bmd')
        for model in (0x2b8d,0x2b8e,0x2b90):
            item=model-0xae6
            assert any(struct.unpack_from('<i',r,4)[0]==item for r in records)
            rows=[r for r in meshes if struct.unpack_from('<i',r)[0]==item]
            for clock in (0,260,123456):
                for r in rows:
                    if lib_dummy_bone_row(model,struct.unpack_from('<i',r,4)[0]):yield model,[r],clock,clock,'installed'
                yield model,rows,clock,clock,'ordered'

def lib_dummy_bone_row(model,mesh):return (model,mesh) in vs.BLOCKED

def compare(lib,machine,count,installed):
    families={n:{'cases':0,'mismatches':0} for n in ('synthetic','installed','ordered')}
    rng=random.Random('muun-bones-context-005')
    read=lambda m,a,n:bytes(m.uc.mem_read(a,n))
    for model,records,clock,ordinal,tag in samples(count,installed):
        obj,mdl,item,info=bytearray(0x3d8),bytearray(0x100),bytearray(0x260),bytearray(0x27c)
        color=F3(.7,.5,.3);alpha,light,scale=.8,.75,.7
        struct.pack_into('<i',obj,0x5c,model);struct.pack_into('<i',obj,0x74,-1)
        struct.pack_into('<f',obj,0xa8,light);struct.pack_into('<f',obj,0xdc,alpha);struct.pack_into('<f',obj,0xa0,scale)
        struct.pack_into('<3f',obj,0x164,10,20,30);struct.pack_into('<3f',mdl,0x54,*color)
        item[0x250:0x252]=bytes([12,1]);info[0x258]=1
        points=POINTS(*[F3(*[am.f32(rng.uniform(-500,500)) for _ in range(3)]) for _ in BONES])
        if ordinal%11==0:points[1]=points[0] # zero-length normalization boundary
        elif ordinal%11==1:points[0]=F3();points[1]=F3(1e-7,1e-7,1e-7)
        fractions=F12(*[rng.choice([0.0,.25,.5,1.0]) for _ in range(12)])
        randoms=[ordinal%15,ordinal%6];rr=[];ri=[];calls=[];transforms=[];bone_requests=[]
        def mesh(m,which):
            calls.append(('mesh' if which else 'body',[m.argument(k) for k in range(8)],read(m,vp.MODEL+0x54,12)));return 0,32
        def bone(m):
            b=m.argument(0);bone_requests.append(b)
            return 0x31000000+48*b,4
        def transform(m):
            b=(m.argument(0)-0x31000000)//48
            transforms.append((b,read(m,m.argument(1),12),m.argument(3)))
            m.uc.mem_write(m.argument(2),bytes(points[BONES.index(b)]));return 0,16
        def rand_range(m):
            idx=len(rr)%12;lo,hi=m.float_argument(0),m.float_argument(1)
            rr.append((lo,hi));return m.x87_return(am.f32(fractions[idx]*(hi-lo)+lo))
        def rand(m):
            value=randoms[len(ri)%2];ri.append(value);return value
        def particle(m):
            calls.append(('particle',m.argument(0),read(m,m.argument(1),12),read(m,m.argument(3),12),
                m.argument(4),m.argument(5),read(m,m.argument(2),12),m.argument(6),m.argument(7)))
            return 0
        def sprite(m):
            calls.append(('sprite',m.argument(0),read(m,m.argument(1),12),read(m,m.argument(3),12),
                0,m.argument(2),m.argument(5),m.argument(4),m.argument(6),m.argument(7),read(m,m.argument(8),12)))
            return 0
        ptr=bytearray(max(4,len(records)*4));rs=[];textures=[-1 if k%2 else 0xa000+k for k in range(len(records))]
        for k,row in enumerate(records):
            struct.pack_into('<I',ptr,4*k,vp.ROW+0x1000*k)
            rs.append(am.defined_region(f'row{k}',vp.ROW+0x1000*k,row+struct.pack('<i',textures[k])))
        stubs={0xcd4ea8:lambda m:0,0xcd5d29:lambda m:(vp.ITEM,4),0x1807c1f:lambda m:0,
            0x9c2aea:lambda m:0,0x1807c32:lambda m:(vp.INFO,4),0x9beaa7:lambda m:len(records),
            0x9bca89:lambda m:(vp.POINTER+4*m.argument(0),4),0x966def:lambda m:mesh(m,False),0x966e4a:lambda m:mesh(m,True),
            0x9fa223:lambda m:m.x87_return(am.f32(math.cos(m.float_argument(0)))),
            0x9681bd:lambda m:m.x87_return(am.f32(math.sin(m.float_argument(0)))),
            0x961a07:lambda m:m.x87_return(am.f32(math.sqrt(m.float_argument(0)))),
            0x129f12c:bone,0x12b6ef1:transform,0x11ff622:rand_range,0x1989721:rand,
            0x168fafd:particle,0x1692eb7:sprite,0x966cc4:lambda m:(vp.MODEL,4),0xeaa8cf:lambda m:vp.MODEL}
        regions=[am.defined_region(n,a,p) for n,a,p in [('object',vp.OBJ,obj),('model',vp.MODEL,mdl),('item',vp.ITEM,item),
            ('info',vp.INFO,info),('pointers',vp.POINTER,ptr),('clock',0x6fce370,struct.pack('<f',clock)),('delta',0x1cf103c,struct.pack('<f',.04))]]+rs
        result=machine.execute(0x17f76ec,[vp.MODEL,vp.OBJ,1,0,0,0xffffffff,0xffffffff],regions,stubs)
        expected=[('body',[2,am.bits(alpha),0xffffffff,am.bits(light),0,0,0,0xffffffff],bytes(color))]
        c8=C.c_float(0);expected_bones=[]
        for k,row in enumerate(records):
            p=vp.Pass();uv=(C.c_float*2)()
            lib.mu_mv_mesh_pass(row,color,alpha,-1,light,textures[k],clock,C.byref(p))
            lib.mu_mv_special_pass(model,0,row,.04,clock,alpha,light,C.byref(c8),C.byref(p),uv)
            b=lib.mu_mv_bone_row(model,p.mesh);which=p.mesh
            if not b or lib.mu_mv_bone_mesh(model,p.mesh,clock,alpha,light,C.byref(p),uv):
                expected.append(('mesh',[p.mesh&0xffffffff,p.flags&0xffffffff,am.bits(p.alpha),p.blend&0xffffffff,
                    am.bits(p.light),am.bits(uv[0]),am.bits(uv[1]),p.texture&0xffffffff],bytes(p.color)))
            if b:
                ops=OPS();n=lib.mu_mv_bone_effects(model,which,clock,scale,points,fractions,*randoms,ops)
                expected_bones.extend([11,18] if model==0x2b8d else [12,12,13,13,22,22,23,23] if model==0x2b8e else [52])
                for op in ops[:n]:
                    if op.particle:expected.append(('particle',op.type,bytes(op.position),bytes(op.light),op.subtype,
                        am.bits(op.scale),struct.pack('<3f',10,20,30),vp.OBJ if model==0x2b8d else 0,0))
                    else:expected.append(('sprite',op.type,bytes(op.position),bytes(op.light),0,am.bits(op.scale),
                        am.bits(op.rotation),vp.OBJ,0,4,struct.pack('<iif',1,1,1)))
        equal=result['ok'] and calls==expected and bone_requests==expected_bones and all(t[1:]==(bytes(12),1) for t in transforms)
        equal &= result['regions']['model'][0x54:0x60]==bytes(color)
        fam=families[tag];fam['cases']+=1
        if not equal:
            fam['mismatches']+=1
            fam.setdefault('models',{}).setdefault(hex(model),{'got':repr(calls),'expected':repr(expected),'checks':result['checks'],'error':str(result.get('error')),'stopped':str(result['stopped'])})
            if 'first' not in fam:fam['first']={'model':hex(model),'clock':clock,'checks':result['checks'],'stopped':str(result['stopped']),
                'error':str(result.get('error')),'got':repr(calls),'expected':repr(expected),'bones':bone_requests,'expected_bones':expected_bones,'ranges':rr}
    return families

MUTANTS=[
 ('row_model','return (model == 0x2b8d','return (model == 0x2b8c'),
 ('row_mesh','return (model == 0x2b8d && mesh == 1)','return (model == 0x2b8d && mesh == 0)'),
 ('normal_epsilon','length >= 0.000001f','length > 0.0f'),
 ('normal_product','d[k] * (1.0f / length)','d[k] / length'),
 ('illusion_mesh','pass->blend = 1','pass->blend = 2'),('illusion_atlas','clock % 260','clock % 240'),
 ('illusion_color','pass->color[1] = 0.2f','pass->color[1] = 0.3f'),
 ('illusion_length','d[2]*d[2]','d[2]*d[2]*2.0f'),('illusion_half','distance) * 0.7f','distance) * 0.6f'),
 ('illusion_jitter','j * 0.9f','j * 0.8f'),('illusion_particle','1,0x8084,28','1,0x8084,29'),
 ('rage_pulse','* 0.07f','* 0.08f'),('rage_second','0x810d','0x810c'),('rage_order','points[2+i]','points[3+i]'),
 ('dark_no_mesh','return 0; /* This branch','return 1; /* This branch'),
 ('dark_rotation','time * 0.0006f','time * 0.0005f'),('dark_random','random0 % 15','random0 % 14'),
 ('dark_tint','0,0.8f,1,s','0,0.7f,1,s'),('dark_wave','pass.light*7.0f','pass.light*6.0f'),
 ('dark_chance','random1 % 6','random1 % 5'),('dark_child','1,0x7efa,3','1,0x7efa,4')]

def run(cases,mutations,installed):
    start=time.monotonic();text=pins.TEXT.read();data=pins.DATA.read();machine=vc.Combat(text,data)
    source=(ROOT/'reconstructed/muun/bone_fx.c').read_text()
    with tempfile.TemporaryDirectory() as td:
        p=Path(td);(p/'base').mkdir();families=compare(build(p/'base'),machine,cases,installed);mutants={}
        if mutations:
            for name,old,new in MUTANTS:
                if source.count(old)<1:raise ValueError(name+' missing anchor')
                (p/name).mkdir();rows=compare(build(p/name,source.replace(old,new)),machine,60,False)
                mutants[name]={'caught':sum(r['mismatches'] for r in rows.values())}
    return {'families':families,'cases':sum(r['cases'] for r in families.values()),'all_equal':all(not r['mismatches'] for r in families.values()),
        'mutants':mutants,'all_mutants_caught':all(r['caught'] for r in mutants.values()),
        'body_sha256':hashlib.sha256(text[0x17f76ec-am.TEXT_BASE:0x17f919e-am.TEXT_BASE]).hexdigest(),'wall_seconds':time.monotonic()-start}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=200);p.add_argument('--installed',action='store_true')
    p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();r=run(a.cases,a.mutations,a.installed)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));sys.exit(0 if r['all_equal'] and r['all_mutants_caught'] else 1)
