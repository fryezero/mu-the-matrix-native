#!/usr/bin/env python3
"""Built-in world producers and Lost Tower push against pinned original instructions.

Bone lookup/TransformPosition supply synthetic positions. Lost Tower type23 has an
uninitialized transform input in the original; that service records only the selected
name and supplies an origin, as the earlier Lorencia comparison does. No particle
lifecycle or image equivalence follows from the producer comparisons.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import actor_machine as am
import pins
import validate_object_render as v
import validate_particles as p
ROOT=Path(__file__).resolve().parents[1]
BONE=C.CFUNCTYPE(None,C.c_void_p,C.c_char_p,C.POINTER(C.c_float),C.POINTER(C.c_float))
BODIES={'losttower_visual':(0x17fa92b,0x17fb1a2),'tarkan_visual':(0x17fb2a4,0x17fb7e7),
        'icarus_flare':(0x17fbf34,0x17fc01e),'losttower_push':(0x17f6ca7,0x17f71d5),
        'atlans_dispatch':(0x17f9758,0x17fccce)}
TYPES={4:[-1,0,18,19,20,21,23,24,38,39,40,41,42],8:[-1,0,59,60,61,62,63,64,69,70,71,75,76,77,82,83,84],
       10:[-1,6,9,10,11,100],7:[-1,0,1,9,20,34,35,36,37,38,39,40,41,42,43,2147483647]}
def bind(lib):
    lib.mu_builtin_visual.argtypes=[C.c_void_p,C.c_int32,C.c_int32,C.c_int,C.c_float,v.RAND_FN,BONE,C.c_void_p,C.POINTER(v.Log)]
    lib.mu_losttower_push.argtypes=[C.c_void_p,C.c_int32,C.POINTER(C.c_float),C.c_uint16,C.POINTER(v.Log)]
    return lib

class Machine(p.PtMachine):
    def stub_entry(self,uc,address,size,ignored):
        if address==0x17fcb5c:self.default_hits+=1
        super().stub_entry(uc,address,size,ignored)

def family(machine,lib,name,cases):
    g=random.Random('worlds-k-'+name);tally=v.Tally(name)
    world={'losttower_visual':4,'tarkan_visual':8,'icarus_flare':10,'atlans_dispatch':7}.get(name,4)
    for n in range(cases):
        typ=TYPES[world][n%len(TYPES[world])];raw=bytearray(v.OBJ_SIZE);v.put_i(raw,0x5c,typ)
        v.put_i(raw,0x68,[-2,-1,0,4][n//len(TYPES[world])%4])
        for offset in (0x158,0x164,0xec,0xf8,0x170):v.put_f(raw,offset,*[v.f32(g.uniform(-50,50)) for _ in range(3)])
        v.put_f(raw,0xa0,v.f32(g.uniform(.1,3)))
        time=v.f32(g.choice([-10001,-1,0,3500,3501,3999,4000,4500,4501,4999,5000,1e6,g.uniform(-1e5,1e5)]))
        # Direct the narrow type-83 phase window as well as its two boundaries.
        if typ==83:
            ordinal=n//len(TYPES[world]);angle=[0,1.75,-2.75,45,-45,359][ordinal%6]
            v.put_f(raw,0x16c,angle)
            time=int(angle)*10+[3500,3501,3700,3999,4000,4501,-1][ordinal%7]
        present=n%11!=0;seed=g.getrandbits(32);rnd=v.MsvcRand(seed);crnd=v.MsvcRand(seed)
        calls=[];bones=[];cbones=[];names={}
        hero=[v.f32(g.uniform(-100,100)) for _ in range(3)];action=[0,49,50,51,110,111,65535][n%7]
        if name=='losttower_push':
            hero=[0,0,0];v.put_f(raw,0x158,*g.choice([(0,0,0),(30,40,0),(0,49,10),(0,50,10),(0,51,0),(10,10,0)]));v.put_f(raw,0xf8,g.choice([-1,0,.099,.1,1]))
        def lookup(m):
            label=p.read_msvc_string(m,m.argument(0));assert m.argument(1)==0
            bones.append(label);names[p.MATRIX]=label;return p.MATRIX,8
        def position(label):return [float(len(label)*3+1),float(len(label)*-5-2),float(len(label)*7+3)]
        def transform(m):
            a=[m.argument(k) for k in range(4)];assert a[0]==p.MATRIX and a[3]==0
            # Type23's input local is unwritten, so it is not read at this service boundary.
            if not(world==4 and typ==23):assert m.floats(a[1],3)==[0,0,0]
            m.uc.mem_write(a[2],v.pack_f(*position(names[a[0]])));return 0,16
        def vec(m,addr):return tuple(struct.unpack('<3I',m.uc.mem_read(addr,12)))
        def particle(m):
            a=[m.argument(k) for k in range(8)];assert a[6:]==[0,0]
            calls.append((0x168fafd,0,a[0])+vec(m,a[1])+vec(m,a[2])+vec(m,a[3])+(a[4],a[5],0));return 0
        def sprite(m):
            a=[m.argument(k) for k in range(9)];assert a[4]==p.OBJECTS and a[6:8]==[0,4]
            assert tuple(struct.unpack('<3I',m.uc.mem_read(a[8],12)))==(1,1,v.bits(1))
            calls.append((0x1692eb7,0,a[0])+vec(m,a[1])+(a[2],)+vec(m,a[3])+(a[5],1,0,4));return 0
        def effect(m):
            a=[m.argument(k) for k in range(14)];assert a[4:]==[0,0,0xffffffff,0,0,0,0,0xffffffff,0,0]
            calls.append((0x13c0eaa,0,a[0])+vec(m,a[1])+vec(m,a[2])+vec(m,a[3])+(0,0));return 0
        def sound(m):
            assert [m.argument(k) for k in range(3)]==[0x7c,p.OBJECTS,0]
            calls.append((0xa6ac96,0,0x7c));return 0
        regions=v.global_regions(world,6,[am.defined_region('time',p.TIME,v.pack_f(time))])+[am.defined_region('object',p.OBJECTS,raw)]
        stubs={p.MODEL_CONTAINER:lambda m:(0x29500000,0),p.MODEL_GET:lambda m:(p.MODEL if present else 0,4),
               p.RAND:lambda m:rnd(),p.BONE_MATRIX:lookup,p.TRANSFORM_POSITION:transform,
               p.CREATE_PARTICLE:particle,p.CREATE_SPRITE:sprite,p.CREATE_EFFECT:effect,0xa6ac96:sound,
               p.SINE:lambda m:m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0))))),
               0x961a07:lambda m:m.x87_return(v.f32(math.sqrt(v.from_bits(m.argument(0)))))}
        if name=='atlans_dispatch':
            # Observe the original switch landing. The common hook chain is outside this family.
            stubs[0x17fcb5c]=p.jump_stub(0x17fccc1)
        if name=='losttower_push':
            actor=bytearray(0x3670);v.put_f(actor,0x33ac,*hero);struct.pack_into('<H',actor,0x327e,action)
            regions += [am.defined_region('hero',0x23000000,actor),am.defined_region('hero-pointer',0xa39d754,struct.pack('<I',0x23000000))]
        machine.default_hits=0
        result=machine.execute(0x17f6ca7 if name=='losttower_push' else p.VISUAL,[p.OBJECTS],regions,stubs)
        stop=v.stopped_reason(result);buf=C.create_string_buffer(bytes(raw));log=v.new_log();fn=v.RAND_FN(lambda c:crnd())
        def cb(ctx,label,local,out):
            label=label.decode();cbones.append(label);assert list(local[:3])==[0,0,0]
            for k,value in enumerate(position(label)):out[k]=value
        c_bone=BONE(cb)
        if name=='losttower_push':lib.mu_losttower_push(buf,0,(C.c_float*3)(*hero),action,C.byref(log))
        else:
            handled=lib.mu_builtin_visual(buf,0,world,present,time,fn,c_bone,None,C.byref(log))
            assert handled in (0,1)
            if handled!=1: calls.append(("missing dispatch",))
        native=v.log_events(log)
        diff=[hex(k) for k in range(v.OBJ_SIZE) if buf.raw[k]!=result.get('regions',{}).get('object',bytes(v.OBJ_SIZE))[k]]
        tally.count('type '+str(typ));tally.count('events',len(calls));tally.count('model '+str(present))
        tally.add(not stop and not diff and native==calls and bones==cbones and rnd.seed==crnd.seed and not log.overflow and (name!='atlans_dispatch' or machine.default_hits==int(present)),
                  {'case':n,'type':typ,'time':time,'diff':diff[:10],'calls':calls[:2],'native':native[:2],'bones':bones,'cbones':cbones,'rng':(rnd.seed,crnd.seed)},stop)
    return tally.report()
MUTANTS=[('0.3f,light,rotation','0.4f,light,rotation','losttower_visual'),
('t==19?0x7f84:0x7f37','t==19?0x7f37:0x7f84','losttower_visual'),
('p[2]+=260.0f','p[2]+=250.0f','losttower_visual'),
('k ? -rotation : rotation','k ? rotation : rotation','losttower_visual'),
('k<20','k<19','tarkan_visual'),('random(ctx)%5==0','random(ctx)%4==0','tarkan_visual'),
('%5000>4500','%5000>=4500','tarkan_visual'),('clock>','clock>=','tarkan_visual'),
('particle(o,index,0x7f5a,8','particle(o,index,0x7f5a,7','tarkan_visual'),
('size*0.5f','size*0.6f','tarkan_visual'),('v/1.7f','v/1.5f','tarkan_visual'),
('particle(o,index,0x7ef7,0','particle(o,index,0x7ef7,1','icarus_flare'),
('bone(ctx,"Bone01",zero,p);particle','bone(ctx,"Bone02",zero,p);particle','icarus_flare'),
('action<111','action<110','losttower_push'),('sqrtf(x*x+y*y)<50.0f','sqrtf(x*x+y*y)<=50.0f','losttower_push'),
('0.6f*mu_obj_f32','0.5f*mu_obj_f32','losttower_push'),('-x*4.0f','-x*3.0f','losttower_push'),
('world!=7','world!=6','atlans_dispatch'),
(')*10u',')*9u','tarkan_visual'),('clock<','clock<=','tarkan_visual'),
('mu_obj_f32(o,0xf8)<0.1f','mu_obj_f32(o,0xf8)<=0.1f','losttower_push')]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1200);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output');a=ap.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read();machine=Machine(text,data)
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/objects')],check=True)
    lib=bind(C.CDLL(str(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}')))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'bodies':{n:{'start':hex(s),'end':hex(e),'sha256':hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()} for n,(s,e) in BODIES.items()},'families':{},'mutants':[]}
    for name in BODIES:
        r=report['families'][name]=family(machine,lib,name,a.cases);print(name,r,flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-k-') as tmp:
            for n,(old,new,name) in enumerate(MUTANTS):
                dest=Path(tmp)/str(n)
                for directory in ('objects','terrain','model-codec','record-math','movement'):
                    shutil.copytree(ROOT/'reconstructed'/directory,dest/directory,ignore=shutil.ignore_patterns('*.dylib','*.so','__pycache__'))
                file=dest/'objects/world_builtin_visual.c';s=file.read_text();assert old in s,old;file.write_text(s.replace(old,new,1))
                mutant=bind(C.CDLL(str(v.build_library(dest))));r=family(machine,mutant,name,a.cases)
                m={'family':name,'change':new,'detected':r['mismatch_count'],'stopped':r['stopped']};report['mutants'].append(m);print('mutant',m,flush=True)
    if a.output:Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
    return int(any(r['equal']!=r['cases'] for r in report['families'].values()) or any(not m['detected'] or m['stopped'] for m in report['mutants']))
if __name__=='__main__':raise SystemExit(main())
