#!/usr/bin/env python3
"""World-79 primary slots and world-100 create/move against pinned instructions.

Full AL/OBJECT/RNG and ordered output calls. Model lookup, Animation and
TransformPosition are recording boundaries; the latter supplies synthetic bone
positions. Market move's combined pose/bone/light service asserts every original
argument before normalizing it to the host's deferred command.
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
import actor_machine as am
import validate_object_render as v
import pins
from unicorn.x86_const import UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'market_create': (0xe6c0ec, 0xe6c1bf), 'market_move': (0xe6c1bf, 0xe6c678),
          'market_visual': (0xe6c678, 0xe6ce2d), 'uruk_create': (0xe6f0a2, 0xe6f1ca),
          'uruk_move': (0xe6f1ca, 0xe6f3d5), 'uruk_visual': (0xe6f3d5, 0xe702eb)}
TYPES = {'market': [-2147483648,-1,0,8,29,30,31,34,35,36,49,50,51,52,53,54,55,56,57,58,59,60,66,67,68,69,2147483647],
         'uruk': [-2147483648,-1,0,16,20,27,29,33,34,35,39,44,54,55,56,72,73,84,85,86,87,88,89,90,91,92,93,94,96,97,99,100,105,106,108,109,110,2147483647]}
BONE = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))

def bind(lib):
    d = lib.dll
    d.mu_market_create.argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.Log)]
    d.mu_market_move.argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_market_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_float, v.RAND_FN, BONE, C.c_void_p, C.POINTER(v.Log)]
    d.mu_uruk_create.argtypes = [C.c_void_p, C.c_int32]
    d.mu_uruk_move.argtypes = d.mu_market_move.argtypes
    d.mu_uruk_visual.argtypes = [C.c_void_p,C.c_int32,C.c_int32,C.c_int32,C.c_float,v.RAND_FN,C.c_void_p,C.POINTER(v.Log)]
    return lib

def family(machine, lib, name, cases):
    g = random.Random('worlds-i-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    for n in range(cases):
        typ = TYPES[prefix][n % len(TYPES[prefix])]
        world = (79 if prefix == 'market' else 100) if n % 5 else [0,78,79,80,99,100,101,102][(n//5)%8]
        present = n % 7 != 0
        weather = n % 3
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        time = v.f32(g.choice([0, -1000, 1000, 1570.79638671875, g.uniform(-1e6,1e6)]))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones, cbones = [], [], []
        model = bytearray(0x100)
        def position(k): return (float(k*17+5), float(k*-13+7), float(k*11-3))
        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) in (v.MODEL, v.FAKE)
            assert a[3] == 0 and v.read_vec(m,a[1]) == (0,0,0)
            k = (a[0] - 0x6fce398)//0x30
            assert a[0] == 0x6fce398+k*0x30 and k in (1,2,3)
            bones.append(k)
            m.uc.mem_write(a[2], v.pack_f(*position(k)))
            return (0,16)
        def animation(m):
            a=[m.argument(k) for k in range(8)]
            assert a == [0x6fce398,struct.unpack_from('<I',raw,0xd0)[0],struct.unpack_from('<I',raw,0xd4)[0],struct.unpack_from('<H',raw,0x2c)[0],v.OBJECTS+0x164,v.OBJECTS+0x170,0,1]
            assert bytes(m.uc.mem_read(v.MODEL+0x74,16)) == raw[0xa0:0xa4]+raw[0x158:0x164]
            return (0,32)
        def light(m):
            a=[m.argument(k) for k in range(5)]
            assert a[4]==v.FRAME_LIGHT
            if prefix == 'market':
                k=1 if typ==30 else 2
                assert bones==[k] and (a[0],a[1])==tuple(v.bits(x) for x in position(k)[:2])
                calls.append((0xe6c29d,0,k)+v.read_vec(m,a[2])+(a[3],))
            else:
                calls.append((0x16cacfc,0,a[0],a[1])+v.read_vec(m,a[2])+(a[3],))
            return 0
        def register(m):
            assert [m.argument(k) for k in range(2)]==[v.OBJECTS,1]
            calls.append((0x16d9f51,0,1));return 0
        def particle(m):
            a=[m.argument(k) for k in range(8)]
            assert a[6] in (0,v.OBJECTS) and a[7]==0
            calls.append((0x168fafd,0,a[0])+v.read_vec(m,a[1])+v.read_vec(m,a[2])+v.read_vec(m,a[3])+(a[4],a[5],int(a[6]==v.OBJECTS)));return 0
        def sprite(m):
            a=[m.argument(k) for k in range(9)]
            assert a[4:8]==[v.OBJECTS,0,0,4] and v.read_vec(m,a[8])==(1,1,v.bits(1))
            calls.append((0x1692eb7,0,a[0])+v.read_vec(m,a[1])+(a[2],)+v.read_vec(m,a[3])+(0,1,0,4));return 0
        def sound(m):
            a=[m.argument(k) for k in range(3)]
            calls.append((0xa6ac96,0)+tuple(a));return 0
        def effect(m):
            a=[m.argument(k) for k in range(14)]
            assert a[4:8]==[12,v.OBJECTS,0xffffffff,0] and a[9:]==[0,v.bits(0),0xffffffff,0,0]
            calls.append((0xe701e5,0,a[0])+v.read_vec(m,a[1])+v.read_vec(m,a[2])+v.read_vec(m,a[3])+(12,1,a[8]));return 0
        def joint(m):
            a=[m.argument(k) for k in range(14)]
            assert a[4:6]==[13,0] and a[7:11]==[0xffffffff,0,0,0xffffffff] and a[12:]==[0xffffffff,0]
            calls.append((0xe70274,0,a[0])+v.read_vec(m,a[1])+v.read_vec(m,a[2])+v.read_vec(m,a[3])+(13,0,a[6])+v.read_vec(m,a[11]));return 0
        regs = v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(raw)),
                    am.defined_region('time',v.TIME,v.pack_f(time),writable=False),am.defined_region('weather',0x1cf15ec,struct.pack('<i',weather)),am.defined_region('model',v.MODEL,bytes(model))])
        result=v.run(machine,BODIES[name][0],[v.OBJECTS]+([v.FAKE] if method=='visual' else []),regs,
                     {0x966cc4:lambda m:v.FAKE,0xeaa8cf:lambda m:(v.MODEL if present else 0,4),
                      0x12b5064:animation,0x12b6ef1:bone,0x16cacfc:light,0x16d9f51:register,
                      0x168fafd:particle,0x1692eb7:sprite,0x1989721:lambda m:rnd(),0xa6ac96:sound,0x13c0eaa:effect,0x153b02c:joint},
                     ecx=v.FAKE,cleanup=8 if method=='visual' else 4)
        stop=v.stopped_reason(result)
        if stop:
            tally.add(False,{'case':n,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(raw),v.OBJ_SIZE);log=v.new_log()
        fn=v.RAND_FN(lambda ctx:crnd())
        def cb(ctx,k,local,out):
            assert list(local[:3])==[0,0,0]
            cbones.append(k)
            for q,value in enumerate(position(k)): out[q]=value
        c_bone=BONE(cb)
        args=[co]
        if name=='market_create': args += [0,C.byref(log)]
        elif name=='uruk_create': args += [world]
        elif method=='move':
            inputs=v.MoveInputs();inputs.world=world;inputs.time=time;inputs.has_model=present;inputs.rand_fn=fn
            args += [0,C.byref(inputs),C.byref(log)]
        elif prefix=='uruk': args += [0,world,weather,time,fn,None,C.byref(log)]
        else: args += [0,world,time,fn,c_bone,None,C.byref(log)]
        handled=getattr(lib.dll,'mu_'+name)(*args)
        diff=[hex(k) for k in range(v.OBJ_SIZE) if co.raw[k]!=result['regions']['object'][k]]
        tally.count('type '+str(typ));tally.count('world '+str(world));tally.count('events',len(calls))
        tally.add(not diff and handled==(result['eax']&255) and calls==v.log_events(log) and rnd.seed==crnd.seed and (method!='visual' or bones==cbones),
                  {'case':n,'type':typ,'world':world,'diff':diff[:8],'al':result['eax']&255,'c_al':handled,'calls':calls[:3],'c':v.log_events(log)[:3],'rng_equal':rnd.seed==crnd.seed})
    return tally.report()
MUTANTS=[
 ('loren_market.c','case 59:', 'case 60:', 'market_create'),
 ('loren_market.c','MU_OBJF_BOX_MAX + 8, 160','MU_OBJF_BOX_MAX + 8, 150','market_create'),
 ('loren_market.c','AFTER_CHARACTER] = 1','AFTER_CHARACTER] = 0','market_create'),
 ('loren_market.c','in->world != 79','in->world != 78','market_move'),
 ('loren_market.c','mu_obj_alpha_step(o);','/* omitted alpha */','market_move'),
 ('loren_market.c','!in->has_model','in->has_model > 1','market_move'),
 ('loren_market.c','VELOCITY, 0.2f','VELOCITY, 0.3f','market_move'),
 ('loren_market.c','t == 30 ? 1u : 2u','t == 30 ? 2u : 1u','market_move'),
 ('loren_market.c','s * 0.7f','s * 0.8f','market_move'),
 ('loren_market.c','t <= 58','t < 58','market_move'),
 ('loren_market.c','if (world != 79)','if (world != 78)','market_visual'),
 ('loren_market.c','k <= (t == 30 ? 3 : 2)','k < (t == 30 ? 3 : 2)','market_visual'),
 ('loren_market.c','1.5f * scale','1.4f * scale','market_visual'),
 ('loren_market.c','wb_float(e, 1);','wb_float(e, scale);','market_visual'),
 ('loren_market.c','random(context) % 8','random(context) % 7','market_visual'),
 ('loren_market.c','20.0f * scale','21.0f * scale','market_visual'),
 ('uruk.c','world != 101','world != 102','uruk_create'),
 ('uruk.c','0x64, 0','0x64, 1','uruk_create'),
 ('uruk.c','-400.0f','-300.0f','uruk_create'),
 ('uruk.c','case 109:', 'case 110:', 'uruk_create'),
 ('uruk.c','in->world != 101','in->world != 102','uruk_move'),
 ('uruk.c','-0.0035f','-0.003f','uruk_move'),
 ('uruk.c','% 4 + 3','% 3 + 3','uruk_move'),
 ('uruk.c','s * 0.6f','s * 0.7f','uruk_move'),
 ('uruk.c','0x801a,2','0x801a,3','uruk_visual'),
 ('uruk.c','scale*2.0f','scale*3.0f','uruk_visual'),
 ('uruk.c','start == 90 ? 10 : 40','start == 90 ? 40 : 10','uruk_visual'),
 ('uruk.c','k<20','k<19','uruk_visual'),
 ('uruk.c','memcpy(o+MU_OBJF_LIGHT,l,12);','/* omit light write */','uruk_visual'),
 ('uruk.c','weather==1','weather!=1','uruk_visual'),
 ('uruk.c','(30-random(ctx)%61)','(30-random(ctx)%60)','uruk_visual'),
 ('uruk.c','wb_arg(e,12);','wb_arg(e,11);','uruk_visual'),
 ('uruk.c','scale*225.0f','scale*224.0f','uruk_visual')]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output');a=ap.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read();machine=v.Machine(text,data)
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/objects')],check=True)
    lib=bind(v.Library(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}'))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'bodies':{n:{'start':hex(s),'end':hex(e),'sha256':hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()} for n,(s,e) in BODIES.items()},'families':{},'mutants':[]}
    for name in BODIES:
        r=report['families'][name]=family(machine,lib,name,a.cases);print(name,r,flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-i-') as tmp:
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
