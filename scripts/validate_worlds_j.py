#!/usr/bin/env python3
"""Captured-world primary methods against original instructions, with compiled mutants."""
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
import actor_machine as am
import validate_object_render as v
import validate_worlds_b as vb
import pins
from unicorn.x86_const import UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'karutan_create': (0xe13a87,0xe13a9e), 'karutan_move': (0xe13a9e,0xe13be4),
          'karutan_visual': (0xe13be4,0xe14596), 'raklion_visual': (0xe946a8,0xe949f8),
          'raklion_create': vb.BODIES['raklion_create'], 'raklion_move': vb.BODIES['raklion']}
TYPES = {'karutan': [-2147483648,-1,0,65,66,67,71,72,73,112,113,114,115,116,117,118,119,135,2147483647],
         'raklion': [-2147483648,-1,0,69,70,71,79,80,81,2147483647]}
BONE = C.CFUNCTYPE(None,C.c_void_p,C.c_int32,C.POINTER(C.c_float),C.POINTER(C.c_float))
def bind(lib):
    vb.bind(lib)
    lib.dll.mu_karutan_create.argtypes=[C.c_void_p]
    lib.dll.mu_karutan_move.argtypes=[C.c_void_p,C.c_int32,C.POINTER(v.MoveInputs),C.POINTER(v.Log)]
    lib.dll.mu_karutan_visual.argtypes=[C.c_void_p,C.c_int32,C.c_int32,C.c_float,v.RAND_FN,BONE,C.c_void_p,C.POINTER(v.Log)]
    lib.dll.mu_raklion_visual.argtypes=[C.c_void_p,C.c_int32,C.c_int,v.RAND_FN,C.c_void_p,C.POINTER(v.Log)]
    return lib

def family(machine,lib,name,cases):
    if name=='raklion_create':return vb.create(machine,lib,random.Random(777),cases).report()
    if name=='raklion_move':return vb.move(machine,lib,random.Random(778),cases,57).report()
    g=random.Random('worlds-j-'+name);tally=v.Tally(name)
    prefix,method=name.split('_')
    for n in range(cases):
        typ=TYPES[prefix][n%len(TYPES[prefix])]
        world=[80,81,79,82,57,58,0][(n//len(TYPES[prefix]))%7]
        present=n%7!=0
        raw=bytearray(v.move_object(g,world,'full'));v.put_i(raw,0x5c,typ)
        v.put_i(raw,0x68,[-2,-1,0,7][(n//3)%4])
        v.put_f(raw,0xa0,[0.0,-0.0,-2.0,0.25,1.0,3.0][(n//len(TYPES[prefix]))%6])
        time=v.f32(g.choice([0,-0.0,1000,-1000,3926.99072265625,g.uniform(-1e6,1e6)]))
        seed=g.getrandbits(32);rnd,crnd=v.MsvcRand(seed),v.MsvcRand(seed)
        calls,bones,cbones=[],[],[]
        def position(k,local):return tuple(v.f32(local[q]+k*(q+1)*17) for q in range(3))
        def bone(m):
            a=[m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX)==v.FAKE
            k=(a[0]-0x6fce398)//0x30
            assert a[0]==0x6fce398+k*0x30 and k in (7,11,13,14) and a[3]==0
            local=tuple(struct.unpack('<3f',bytes(m.uc.mem_read(a[1],12))))
            bones.append((k,local));m.uc.mem_write(a[2],v.pack_f(*position(k,local)))
            return (0,16)
        def particle(m):
            a=[m.argument(k) for k in range(8)]
            assert a[6] in (0,v.OBJECTS) and a[7]==0
            calls.append((0x168fafd,0,a[0])+v.read_vec(m,a[1])+v.read_vec(m,a[2])+v.read_vec(m,a[3])+(a[4],a[5],int(a[6]==v.OBJECTS)));return 0
        def sprite(m):
            a=[m.argument(k) for k in range(9)]
            assert a[4:8]==[v.OBJECTS,0,0,4] and v.read_vec(m,a[8])==(1,1,v.bits(1))
            calls.append((0x1692eb7,0,a[0])+v.read_vec(m,a[1])+(a[2],)+v.read_vec(m,a[3])+(0,1,0,4));return 0
        def light(m):
            a=[m.argument(k) for k in range(5)];assert a[4]==v.FRAME_LIGHT
            calls.append((0x16cacfc,0,a[0],a[1])+v.read_vec(m,a[2])+(a[3],));return 0
        def sound(m):
            calls.append((0xa6ac96,0)+tuple(m.argument(k) for k in range(3)));return 0
        regs=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(raw)),am.defined_region('time',v.TIME,v.pack_f(time),writable=False)])
        result=v.run(machine,BODIES[name][0],[v.OBJECTS]+([v.FAKE if present or prefix=='karutan' else 0] if method=='visual' else []),regs,
                     {0x168fafd:particle,0x1692eb7:sprite,0x12b6ef1:bone,0x16cacfc:light,0xa6ac96:sound,0x1989721:lambda m:rnd()},ecx=v.FAKE,cleanup=8 if method=='visual' else 4)
        stop=v.stopped_reason(result)
        if stop:tally.add(False,{'case':n,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(raw),v.OBJ_SIZE);log=v.new_log();fn=v.RAND_FN(lambda ctx:crnd())
        def cb(ctx,k,local,out):
            local=tuple(local[:3]);cbones.append((k,local))
            for q,value in enumerate(position(k,local)):out[q]=value
        c_bone=BONE(cb)
        if method=='create':handled=lib.dll.mu_karutan_create(co)
        elif method=='move':
            inputs=v.MoveInputs();inputs.world=world;inputs.time=time;inputs.rand_fn=fn
            handled=lib.dll.mu_karutan_move(co,0,C.byref(inputs),C.byref(log))
        elif prefix=='karutan':handled=lib.dll.mu_karutan_visual(co,0,world,time,fn,c_bone,None,C.byref(log))
        else:handled=lib.dll.mu_raklion_visual(co,0,present,fn,None,C.byref(log))
        diff=[hex(k) for k in range(v.OBJ_SIZE) if co.raw[k]!=result['regions']['object'][k]]
        tally.count('type '+str(typ));tally.count('world '+str(world));tally.count('events',len(calls))
        tally.add(not diff and handled==(result['eax']&255) and calls==v.log_events(log) and rnd.seed==crnd.seed and bones==cbones,
                  {'case':n,'type':typ,'world':world,'diff':diff[:8],'al':result['eax']&255,'c_al':handled,'calls':calls[:4],'c':v.log_events(log)[:4],'bones':bones,'cbones':cbones,'rng_equal':rnd.seed==crnd.seed})
    return tally.report()
MUTANTS=[
 ('raklion.c','!= 0x1ab','!= 0x1ac','raklion_create'),
 ('raklion.c','p[2] += 520','p[2] += 519','raklion_create'),
 ('raklion.c','time * 0.001f','time * 0.002f','raklion_move'),
 ('raklion.c','t == 0x50','t == 0x51','raklion_move'),
 ('world_karutan_visual.c','return 0; /* create */','return 1; /* create */','karutan_create'),
 ('world_karutan_visual.c','in->world != 81','in->world != 82','karutan_move'),
 ('world_karutan_visual.c','s * 0.6f','s * 0.7f','karutan_move'),
 ('world_karutan_visual.c','case 0x76:','case 0x77:','karutan_move'),
 ('world_karutan_visual.c','0x5a5','0x5a4','karutan_move'),
 ('world_karutan_visual.c','(world != 80 && world != 81)','(world != 80 && world != 82)','karutan_visual'),
 ('world_karutan_visual.c','wave < 0.0f ? -wave : wave','fabsf(wave)','karutan_visual'),
 ('world_karutan_visual.c','time * 0.0004','time * 0.0005','karutan_visual'),
 ('world_karutan_visual.c','13 + k','12 + k','karutan_visual'),
 ('world_karutan_visual.c','k ? 6.0f : -6.0f','k ? -6.0f : 6.0f','karutan_visual'),
 ('world_karutan_visual.c','1.2f, light','1.3f, light','karutan_visual'),
 ('world_karutan_visual.c','11 - k * 4','11 - k * 3','karutan_visual'),
 ('world_karutan_visual.c','2.0f : 4.0f','3.0f : 4.0f','karutan_visual'),
 ('world_karutan_visual.c','random(context) % 3 == 0','random(context) % 4 == 0','karutan_visual'),
 ('world_karutan_visual.c','j < 20','j < 19','karutan_visual'),
 ('world_karutan_visual.c','HIDDEN_MESH) != -2','HIDDEN_MESH) != -1','karutan_visual'),
 ('world_karutan_visual.c','random(context) % 8 == 0','random(context) % 7 == 0','karutan_visual'),
 ('world_karutan_visual.c','0x7f5a, 69','0x7f5a, 68','karutan_visual'),
 ('world_karutan_visual.c','mu_obj_f32(o, MU_OBJF_SCALE) * 2.0f','mu_obj_f32(o, MU_OBJF_SCALE) * 3.0f','karutan_visual'),
 ('world_karutan_visual.c','j < 4','j < 3','karutan_visual'),
 ('world_raklion_visual.c','if (!has_model)','if (has_model < 0)','raklion_visual'),
 ('world_raklion_visual.c','t != 0x50','t != 0x51','raklion_visual'),
 ('world_raklion_visual.c','0.7f, 0.2f, 0.1f','0.8f, 0.2f, 0.1f','raklion_visual'),
 ('world_raklion_visual.c','0x8087, 0x8089','0x8087, 0x8088','raklion_visual'),
 ('world_raklion_visual.c','choice == 1 ? 6 : 2','choice == 1 ? 5 : 2','raklion_visual'),
 ('world_raklion_visual.c','wv_particle(o, i, 0x8086, 2','wv_particle(o, i, 0x8086, 3','raklion_visual')]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output');a=ap.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read();machine=v.Machine(text,data)
    lib=bind(v.Library(v.build_library(ROOT/'reconstructed')))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'bodies':{n:{'start':hex(s),'end':hex(e),'sha256':hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()} for n,(s,e) in BODIES.items()},'families':{},'mutants':[]}
    for name in BODIES:
        r=report['families'][name]=family(machine,lib,name,a.cases);print(name,r,flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-j-') as tmp:
            for n,(file,old,new,name) in enumerate(MUTANTS):
                dest=Path(tmp)/str(n)
                for directory in ('objects','terrain','model-codec','record-math','movement'):
                    shutil.copytree(ROOT/'reconstructed'/directory,dest/directory,ignore=shutil.ignore_patterns('*.dylib','*.so','__pycache__'))
                p=dest/'objects'/file;s=p.read_text();assert old in s,old;p.write_text(s.replace(old,new,1))
                mutated=bind(v.Library(v.build_library(dest)));r=family(machine,mutated,name,a.cases)
                m={'family':name,'file':file,'change':new,'detected':r['mismatch_count'],'stopped':r['stopped']};report['mutants'].append(m);print('mutant',m,flush=True)
    if a.output:Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
    return int(any(r['equal']!=r['cases'] for r in report['families'].values()) or any(not m['detected'] or m['stopped'] for m in report['mutants']))
if __name__=='__main__':raise SystemExit(main())
