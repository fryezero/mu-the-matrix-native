#!/usr/bin/env python3
"""Compare remaining classless world producers with pinned original instructions and compiled mutants."""
import argparse
import ctypes as C
import json
import math
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_slots2 as w2
import validate_worlds_slots3 as w3
from validate_worlds_inner3 import bone_point
from validate_worlds_inner3 import Machine
ROOT = Path(__file__).resolve().parents[1]
PARTICLE, EFFECT, JOINT = 0x168fafd, 0x13c0eaa, 0x153b02c
TYPES = [2,3,5,6,0x3a,0x3b,0x3c,0x55,0x58,0x59,0x5a,0x5c]
class Library:
    def __init__(self,path):
        self.dll=C.CDLL(str(path)); P,I,F,L=C.c_void_p,C.c_int32,C.c_float,C.POINTER(v.Log)
        self.dll.mu_crywolf_inner.argtypes=[P,I,I,I,F,C.c_uint8,v.RAND_FN,P,L]
        self.dll.mu_barracks_inner.argtypes=[P,I,I,I,F,v.RAND_FN,P,L]
        self.dll.mu_kalima_inner.argtypes=[P,I,I,F,v.RAND_FN,w3.NAMED_FN,P,L]
        self.dll.mu_tower_inner.argtypes=[P,I,I,F,C.c_uint8,v.RAND_FN,w2.BONE_FN,P,L]
        self.dll.mu_kalima_inner.restype=self.dll.mu_tower_inner.restype=C.c_int
        self.dll.mu_crywolf_inner.restype=self.dll.mu_barracks_inner.restype=C.c_int

def compare(machine,lib,g,cases,crywolf=False,focused=False,kalima=False,tower=False):
    t=v.Tally(('tower' if tower else 'kalima' if kalima else 'crywolf' if crywolf else 'barracks')+('_focus' if focused else ''))
    types=[0,0x29,0x2a,0x34,0x35,0x36] if crywolf else TYPES
    if kalima:types=[12,35,36,37,38,39,40]
    if tower:types=[1,5,11,0x20,0x2e,0x2f,0x30,0x31,0x32,0x34,0x35,0x36,0x4a]
    for n in range(cases):
        world=30 if crywolf else [41,42][n%2]
        if kalima:world=[24,25,26,27,28,29,36][n%7]
        if tower:world=39
        if not focused and n%5==0:world=g.choice([0,29,31,40,43,98])
        typ=types[n%len(types)] if focused or n>300 else n
        # Deferred helper contexts are tested as explicit production refusals, not call equivalence.
        if kalima and typ in (15,29,32):typ=11
        if tower and typ==0:typ=2
        o=bytearray(w2.case_object(g,world,typ)); b=bytes(0x100)
        v.put_f(o,0xb4,g.choice([-4.01,-4,-3,-2,-1,0,1,1.99,2,2.01,3,4,8,2147483648.0,-2147483904.0,math.nan]))
        present=focused or n%7!=0
        time=g.choice([0.0,1000.0,3141.5927734375,9000.0,w2.case_time(g)])
        event=g.choice([0,1,2,255])
        seed=g.randrange(2**32);a,cb=v.MsvcRand(seed),v.MsvcRand(seed)
        calls=[]; bones=[];native_bones=[];heap=[w3.HEAP]
        def allocate(m):
            at=heap[0];heap[0]+=max(16,(m.argument(0)+15)&~15);return at
        def named(m):
            at=m.argument(0);size,cap=struct.unpack('<II',bytes(m.uc.mem_read(at+16,8)))
            ptr=at if cap<16 else m.read32(at);name=bytes(m.uc.mem_read(ptr,size)).decode('ascii')
            assert name=='Bone02',name
            bones.append(('name',name));return 0x6fce398+48*2,8
        def transform(m):
            k=(m.argument(0)-0x6fce398)//48;local=struct.unpack('<3f',bytes(m.uc.mem_read(m.argument(1),12)))
            assert m.argument(3)==0;bones.append(('bone',k,*local))
            m.uc.mem_write(m.argument(2),v.pack_f(*bone_point(k,local)));return 0,16
        def bone(c,k,local,out):
            native_bones.append(('bone',k,*local[:3]))
            for q,x in enumerate(bone_point(k,local[:3])):out[q]=x
        def named_bone(c,name,local,out):
            name=name.decode('ascii');native_bones.append(('name',name));bone(c,2,local,out)
        def sprite(m):
            x=[m.argument(k) for k in range(9)]
            assert x[4]==v.OBJECTS and x[6:8]==[0,4]
            assert bytes(m.uc.mem_read(x[8],12))==struct.pack('<IIf',1,1,1.0)
            calls.append((0x1692eb7,x[0],*v.read_vec(m,x[1]),x[2],*v.read_vec(m,x[3]),x[5],1,0,4));return 0
        def sound(m):
            # AUDIO-004 owns native audio additions; producer call equivalence here is visual only.
            assert [m.argument(k) for k in range(3)]==[0x1d6,0,0];return 0
        def particle(m):
            x=[m.argument(k) for k in range(8)]
            assert x[6] in (0,v.OBJECTS) and x[7]==0,x
            calls.append((PARTICLE,x[0],*v.read_vec(m,x[1]),*v.read_vec(m,x[2]),*v.read_vec(m,x[3]),x[4],x[5],int(x[6]==v.OBJECTS)))
            return 0
        def effect(m):
            x=[m.argument(k) for k in range(14)]
            assert x[5]==0 and x[6:8]==[0xffffffff,0] and x[9:]==[0,0,0xffffffff,0,0],x
            calls.append((EFFECT,x[0],*v.read_vec(m,x[1]),*v.read_vec(m,x[2]),*v.read_vec(m,x[3]),x[4],0,x[8]))
            return 0
        def joint(m):
            x=[m.argument(k) for k in range(14)]
            assert x[5]==(0 if tower else v.OBJECTS) and x[7:]==[0xffffffff,0,0,0xffffffff,0,0xffffffff,0],x
            calls.append((JOINT,x[0],*v.read_vec(m,x[1]),*v.read_vec(m,x[2]),*v.read_vec(m,x[3]),x[4],int(x[5]==v.OBJECTS),x[6]))
            return 0
        stubs={w2.RAND:lambda m:a(),PARTICLE:particle,EFFECT:effect,JOINT:joint,0x1692eb7:sprite,
               vp.BONE_MATRIX:named,vp.TRANSFORM_POSITION:transform,vp.CRT_MALLOC:allocate,vp.CRT_FREE:lambda m:0,
               0xa6ac96:sound,
               vp.SINE:lambda m:m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0)))))}
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(o)),
            am.defined_region('model',v.MODEL,b),am.defined_region('time',v.TIME,v.pack_f(time),writable=False),
            am.defined_region('static',w2.STATIC,w2.static_region(machine),writable=False),
            am.defined_region('heap',w3.HEAP,bytes(0x10000)),
            am.defined_region('tower-hidden',0x1ec91ac,bytes([event]),writable=False),
            am.defined_region('event',0x1ec8ee7,bytes([event]),writable=False)])
        result=v.run(machine,0xe84941 if tower else 0xdef747 if kalima else 0xd8e640 if crywolf else 0xd5404b,[v.OBJECTS,v.MODEL if present or kalima or tower else 0],
                     regions,stubs,ecx=0 if crywolf or kalima or tower else w2.STATIC,cleanup=0 if crywolf or kalima or tower else 8)
        stop=v.stopped_reason(result)
        if stop:t.add(False,{'case':n,'world':world,'type':hex(typ)},stop);continue
        co=C.create_string_buffer(bytes(o),v.OBJ_SIZE);log=v.new_log();rnd=v.RAND_FN(lambda c:cb())
        if kalima:answer=lib.dll.mu_kalima_inner(co,0,world,time,rnd,w3.NAMED_FN(named_bone),None,C.byref(log))
        elif tower:answer=lib.dll.mu_tower_inner(co,0,world,time,event,rnd,w2.BONE_FN(bone),None,C.byref(log))
        elif crywolf:answer=lib.dll.mu_crywolf_inner(co,0,world,present,time,event,rnd,None,C.byref(log))
        else:answer=lib.dll.mu_barracks_inner(co,0,world,present,time,rnd,None,C.byref(log))
        native=[(EFFECT if e[0]==0xe68c23 else e[0],*e[2:]) for e in v.log_events(log)]
        ok=calls==native and bones==native_bones and a.seed==cb.seed and result['regions']['object']==co.raw[:v.OBJ_SIZE] and result['regions']['model']==b and (result['eax']&255)==answer
        t.count('world %d type %#x'%(world,typ));t.count('draw/request calls',len(calls))
        t.add(ok,{'case':n,'world':world,'type':hex(typ),'client':calls[:4],'native':native[:4],
                  'object':result['regions']['object']==co.raw[:v.OBJ_SIZE],'rng':a.seed==cb.seed})
    return t
FAMILIES={'barracks':lambda m,l,g,n:compare(m,l,g,n),'barracks_focus':lambda m,l,g,n:compare(m,l,g,n,False,True),
          'crywolf':lambda m,l,g,n:compare(m,l,g,n,True),'crywolf_focus':lambda m,l,g,n:compare(m,l,g,n,True,True),
          'kalima':lambda m,l,g,n:compare(m,l,g,n,kalima=True),
          'kalima_focus':lambda m,l,g,n:compare(m,l,g,n,focused=True,kalima=True),
          'tower':lambda m,l,g,n:compare(m,l,g,n,tower=True),
          'tower_focus':lambda m,l,g,n:compare(m,l,g,n,focused=True,tower=True)}
MUTATIONS=[
    ('Barracks world42','world != 41 && world != 42','world != 41','barracks_focus'),
    ('Barracks model','!model || (world','0 || (world','barracks'),
    ('Barracks type2 gate','rnd(c) % 3 == 0) particle(o,i,t == 2','rnd(c) % 4 == 0) particle(o,i,t == 2','barracks_focus'),
    ('Barracks type3 bitmap','t == 2 ? 0x7f5a : 0x8016','t == 2 ? 0x7f5a : 0x8017','barracks_focus'),
    ('Counter offset','prior + (float)offset','prior + (float)offset + 1.0f','barracks_focus'),
    ('Counter update','prior + 1.0f','prior + 2.0f','barracks_focus'),
    ('Smoke hidden gate','if (mu_obj_i32(o,MU_OBJF_HIDDEN_MESH) != -2) {','if (mu_obj_i32(o,MU_OBJF_HIDDEN_MESH) != -1) {','barracks_focus'),
    ('Smoke count','sub<=4','sub<=3','barracks_focus'),
    ('Smoke light','{0.2f,0.2f,0.2f}','{0.1f,0.2f,0.2f}','barracks_focus'),
    ('Smoke hidden write','MU_OBJF_HIDDEN_MESH,-2);\n        break;\n    case 0x3a','MU_OBJF_HIDDEN_MESH,-1);\n        break;\n    case 0x3a','barracks_focus'),
    ('White particle pair','0x801c,3,white','0x801c,4,white','barracks_focus'),
    ('Red counter particle','0x8001,1,black','0x8001,0,black','barracks_focus'),
    ('Red smoke scale','red,scale * 2','red,scale * 3','barracks_focus'),
    ('Owned smoke','0x7f89,10,white,scale,1','0x7f89,10,white,scale,0','barracks_focus'),
    ('Smoke red random','0.01f + 0.015f','0.02f + 0.015f','barracks_focus'),
    ('Joint angle RNG','rnd(c) % 40 + 120','rnd(c) % 40 + 121','barracks_focus'),
    ('Joint owner','a[10]=4; a[11]=1','a[10]=4; a[11]=0','barracks_focus'),
    ('Effect pulse','* 0.5f > 0.9f','* 0.5f > 0.8f','barracks_focus'),
    ('Effect word','(uint16_t)(uint32_t)cvtt(scale)','(uint16_t)(uint32_t)(cvtt(scale)+1)','barracks_focus'),
    ('Effect count','k<2; ++k','k<1; ++k','barracks_focus'),
    ('Crywolf world','world != 30','world != 31','crywolf_focus'),
    ('Crywolf nonzero byte','event != 0 && rnd(c)','event == 1 && rnd(c)','crywolf_focus'),
    ('Crywolf event zero','t == 0 ? event == 0','t == 0 ? event != 0','crywolf_focus'),
    ('Crywolf pulse','* 0.002f) * 0.3f','* 0.001f) * 0.3f','crywolf_focus'),
    ('Crywolf mixed random kind','event == 0) particle(o,i,0x801c + rnd(c) % 2','event == 0) particle(o,i,0x801c + rnd(c) % 3','crywolf_focus'),
    ('Kalima guard36','|| world==36','|| world==35','kalima_focus'),
    ('Kalima bone','"Bone02"','"Bone01"','kalima_focus'),
    ('Kalima light','{0.6f,0.6f,1}','{0.6f,0.5f,1}','kalima_focus'),
    ('Kalima pulse','time*0.001f','time*0.002f','kalima_focus'),
    ('Kalima particle owner','0x7ef7,6,light,1,1','0x7ef7,6,light,1,0','kalima_focus'),
    ('Kalima scale write','MU_OBJF_SCALE,0.5f);\n        if (t==36)','MU_OBJF_SCALE,0.6f);\n        if (t==36)','kalima_focus'),
    ('Kalima random pair','case 39:\n        particle(o,i,0x801c+rnd(c)%2','case 39:\n        particle(o,i,0x801c+rnd(c)%3','kalima_focus'),
    ('Tower guard','world!=39','world!=38','tower_focus'),
    ('Tower glow divisor','(double)pulse/2.4','(double)pulse/2.5','tower_focus'),
    ('Tower glow rotation','cvtt(time/4.0f)','cvtt(time/3.0f)','tower_focus'),
    ('Tower smoke colour','t==0x31?0.06f:v','t==0x31?0.07f:v','tower_focus'),
    ('Tower smoke count','t==0x2e?20:10','t==0x2e?19:10','tower_focus'),
    ('Tower fixture byte','if (hidden)','if (hidden == 1)','tower_focus'),
    ('Tower lightning scale','scale*15','scale*14','tower_focus'),
    ('Tower object light','t==0x34?0.5f:0.3f','t==0x34?0.4f:0.3f','tower_focus'),
    ('Tower unhide','MU_OBJF_HIDDEN_MESH,-1);tower_joint','MU_OBJF_HIDDEN_MESH,-2);tower_joint','tower_focus'),
    ('Tower joint subtype','0x7f7c,19,scale*10','0x7f7c,18,scale*10','tower_focus'),
]
def build(root):
    subprocess.run(['make','-s','-j4','-C',str(root/'objects')],check=True)
    return Library(root/'objects'/('libobjects.'+v.SUFFIX))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000); p.add_argument('--only'); p.add_argument('--mutations', action='store_true')
    p.add_argument('--text', default=v.pins.TEXT.default_str()); p.add_argument('--data', default=v.pins.DATA.default_str())
    p.add_argument('--output'); a = p.parse_args()
    machine = Machine(am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text'),
                      am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data'))
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    seed = lambda n: random.Random(0x511f + list(FAMILIES).index(n))
    for name in names:
        row = FAMILIES[name](machine, lib, seed(name), a.cases).report(); report['families'][name] = row
        print(name, json.dumps({k:v for k,v in row.items() if k != 'coverage'})[:5000], flush=True)
    if a.mutations:
        for label, old, new, family in MUTATIONS:
            if family not in names: continue
            with tempfile.TemporaryDirectory(prefix='worlds-inner4-mut-') as td:
                root = Path(td)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                path = root / 'objects/world_inner4_visual.c'; s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                assert len(re.findall(pattern, s)) == 1, label
                path.write_text(re.sub(pattern, lambda m: new, s, count=1))
                tally = FAMILIES[family](machine, build(root), seed(family), a.cases)
                row = {'name': label, 'cases': tally.cases, 'detected': tally.cases - tally.equal - tally.stopped,
                       'stopped': tally.stopped}; report['mutants'].append(row); print(row, flush=True)
    report['ok'] = all(r['mismatch_count'] == 0 and r['stopped'] == 0 for r in report['families'].values()) and \
                   all(r['detected'] > 0 for r in report['mutants'])
    if a.output: Path(a.output).write_text(json.dumps(report, indent=1))
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    sys.exit(main())
