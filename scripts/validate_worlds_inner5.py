#!/usr/bin/env python3
"""Instruction comparisons for Kalima helpers and tower type 0 with authored context."""
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
from validate_worlds_inner3 import Machine, bone_point
ROOT=Path(__file__).resolve().parents[1]
HERO=0x43000000
WATER=C.CFUNCTYPE(C.c_float,C.c_void_p,C.c_float,C.c_float)
class Kalima(C.Structure):
    _fields_=[('action',C.c_uint16),('hero',C.c_float*3),('water',WATER)]
class Tower(C.Structure):
    _fields_=[(n,C.c_int32) for n in ('mode','stage','phase','burst','sequence')]+[(n,C.c_uint8) for n in ('active','rising','emit','timer0','timer1','timer2')]+[('shake',C.c_float),('hero',C.c_float*3)]
class Library:
    def __init__(self,path):
        self.dll=C.CDLL(str(path));P,I,F,L=C.c_void_p,C.c_int32,C.c_float,C.POINTER(v.Log)
        self.dll.mu_kalima_helpers.argtypes=[P,I,I,F,C.POINTER(Kalima),w3.NAMED_FN,P,L]
        self.dll.mu_tower_zero.argtypes=[P,I,I,C.POINTER(Tower),v.RAND_FN,w2.BONE_FN,P,L]

def build(root):
    subprocess.run(['make','-s','-j4','-C',str(root/'objects')],check=True)
    return Library(root/'objects'/('libobjects.'+v.SUFFIX))

def compare(machine,lib,g,cases,tower=False,focused=False):
    tally=v.Tally(('tower' if tower else 'kalima')+('_focus' if focused else ''))
    for n in range(cases):
        world=39 if tower else [24,25,26,27,28,29,36][n%7]
        if not focused and n%5==0:world=g.choice([0,23,30,38,40,98])
        typ=0 if tower else [15,29,32][n%3]
        o=bytearray(w2.case_object(g,world,typ));b=bytes(0x100)
        v.put_f(o,0xd0,g.choice([0,4.99,5,6,12.49,12.5,13]))
        v.put_f(o,0x160,g.choice([-3000,-2749.5,-750,-749.5,-749,0,500]))
        action=g.choice([0,49,50,80,110,111,65535]);hero=[g.uniform(-100,100) for _ in range(3)]
        if n%2==0:
            v.put_f(o,0x158,hero[0]+g.choice([0,1,49,50,51]),hero[1],hero[2])
            v.put_f(o,0xf8,g.choice([-1,0,0.099,0.1,1]),2,3)
        water_present=n%2==0;sample=v.f32(g.uniform(-300,500));time=g.choice([0,1000,3141.5927734375,9000,w2.case_time(g)])
        fixture=Tower();fixture.mode=g.choice([0,1,2]);fixture.stage=g.choice([0,2,3,17,18,19]);fixture.phase=g.choice([-1,0,1,2,3]);fixture.burst=g.choice([0,1,3,4]);fixture.sequence=g.choice([0,1,2,3,4,5,6,-1])
        fixture.active=g.choice([0,1,2,255]);fixture.rising=g.choice([0,1,2,255]);fixture.emit=g.choice([0,1,2,255]);fixture.timer0=g.randrange(2);fixture.timer1=g.randrange(2);fixture.timer2=g.randrange(2);fixture.shake=1.25;fixture.hero[:]=hero
        if tower and focused:
            # Deterministically exercise every sequence form, including inactive phase 0/1.
            forms=[(0,-1,0),(0,0,0),(0,1,0),(1,2,0),(1,2,1),(1,2,2),(1,2,3),(1,2,4),(1,2,5)]
            fixture.active,fixture.phase,fixture.sequence=forms[n%len(forms)]
        sing=bytearray(0x100);v.put_i(sing,0x7c,fixture.mode);v.put_i(sing,0x80,fixture.stage);sing[0x89]=fixture.active;sing[0x8a]=fixture.rising
        state=bytearray(12);state[0]=fixture.emit;v.put_i(state,2,fixture.burst);v.put_i(state,6,fixture.sequence)
        hero_bytes=bytearray(0x33c0);struct.pack_into('<H',hero_bytes,0x327e,action);v.put_f(hero_bytes,0x33ac,*hero)
        seed=g.randrange(2**32);a,cb=v.MsvcRand(seed),v.MsvcRand(seed)
        calls=[];bones=[];native_bones=[];waters=[];native_waters=[];heap=[w3.HEAP]
        def named(m):
            at=m.argument(0);size,cap=struct.unpack('<II',bytes(m.uc.mem_read(at+16,8)));ptr=at if cap<16 else m.read32(at)
            name=bytes(m.uc.mem_read(ptr,size)).decode();assert name=='Bone02';bones.append(('name',name));return 0x6fce398+96,8
        def transform(m):
            k=(m.argument(0)-0x6fce398)//48;local=struct.unpack('<3f',bytes(m.uc.mem_read(m.argument(1),12)));assert m.argument(3)==0
            bones.append(('bone',k,*local));m.uc.mem_write(m.argument(2),v.pack_f(*bone_point(k,local)));return 0,16
        def bone(c,k,local,out):
            native_bones.append(('bone',k,*local[:3]))
            for q,x in enumerate(bone_point(k,local[:3])):out[q]=x
        def named_bone(c,name,local,out):
            native_bones.append(('name',name.decode()));bone(c,2,local,out)
        def particle(m):
            x=[m.argument(k) for k in range(8)];assert x[6:]==[0,0]
            calls.append((0x168fafd,x[0],*v.read_vec(m,x[1]),*v.read_vec(m,x[2]),*v.read_vec(m,x[3]),x[4],x[5],0));return 0
        def effect(m):
            x=[m.argument(k) for k in range(14)];assert x[5:8]==[0,0xffffffff,0] and x[8:10]==[0,0] and x[11:]==[0xffffffff,0,0],x
            calls.append((0x13c0eaa,x[0],*v.read_vec(m,x[1]),*v.read_vec(m,x[2]),*v.read_vec(m,x[3]),x[4],0,x[10]));return 0
        def sprite(m):
            x=[m.argument(k) for k in range(9)];assert x[4]==v.OBJECTS and x[6:8]==[0,4]
            assert bytes(m.uc.mem_read(x[8],12))==struct.pack('<IIf',1,1,1)
            calls.append((0x1692eb7,x[0],*v.read_vec(m,x[1]),x[2],*v.read_vec(m,x[3]),x[5],1,0,4));return 0
        def allocate(m):
            at=heap[0];heap[0]+=max(16,(m.argument(0)+15)&~15);return at
        def water(m):
            waters.append((v.from_bits(m.argument(0)),v.from_bits(m.argument(1))))
            esp=m.uc.reg_read(m.x86.UC_X86_REG_ESP);ret=m.read32(esp)
            m.uc.mem_write(esp+8,struct.pack("<I",ret));m.uc.reg_write(m.x86.UC_X86_REG_ESP,esp+8)
            return m.x87_return(sample)
        def native_water(c,x,y):native_waters.append((x,y));return sample
        def sound(m):
            assert m.argument(0) in (0x2bf,0x2c0,0x2c1) and m.argument(1)==m.argument(2)==0;return 0
        def timer(m):
            k=m.argument(0);assert k in (0,1,2) and m.argument(1)==(1000 if k==0 else 1200);return 0x44000000+k,8
        def timer_answer(m):return [fixture.timer0,fixture.timer1,fixture.timer2][m.uc.reg_read(m.x86.UC_X86_REG_ECX)-0x44000000]
        stubs={w2.RAND:lambda m:a(),vp.BONE_MATRIX:named,vp.TRANSFORM_POSITION:transform,vp.CRT_MALLOC:allocate,vp.CRT_FREE:lambda m:0,
               0x168fafd:particle,0x13c0eaa:effect,0x1692eb7:sprite,0x9a6ef3:lambda m:w2.SING,0xa6ac96:sound,
               0x9f9b67:water,0xc74245:timer,0x1185396:timer_answer,
               0x961a07:lambda m:m.x87_return(v.f32(math.sqrt(v.from_bits(m.argument(0))))),
               vp.SINE:lambda m:m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0)))))}
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(o)),am.defined_region('model',v.MODEL,b),
          am.defined_region('time',v.TIME,v.pack_f(time),writable=False),am.defined_region('heap',w3.HEAP,bytes(0x10000)),
          am.defined_region('hero-pointer',0xa39d754,struct.pack('<I',HERO),writable=False),am.defined_region('hero',HERO,hero_bytes,writable=False),
          am.defined_region('water-manager',0x1ec9188,struct.pack('<I',0x45000000 if water_present else 0),writable=False),
          am.defined_region('singleton',w2.SING,sing),am.defined_region('phase',0x1cf0e98,struct.pack('<i',fixture.phase)),
          am.defined_region('state',0x1ec91ae,state),am.defined_region('shake',0xbdb588c,v.pack_f(fixture.shake))])
        result=v.run(machine,0xe84941 if tower else 0xdef747,[v.OBJECTS,v.MODEL],regions,stubs)
        stop=v.stopped_reason(result)
        if stop:tally.add(False,{'case':n,'world':world,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(o),v.OBJ_SIZE);log=v.new_log();original_fixture=bytes(fixture)
        if tower:answer=lib.dll.mu_tower_zero(co,0,world,C.byref(fixture),v.RAND_FN(lambda c:cb()),w2.BONE_FN(bone),None,C.byref(log))
        else:answer=lib.dll.mu_kalima_helpers(co,0,world,time,C.byref(Kalima(action,(C.c_float*3)(*hero),WATER(native_water) if water_present else WATER())),w3.NAMED_FN(named_bone),None,C.byref(log))
        native=[(e[0],*e[2:]) for e in v.log_events(log)]
        state_ok=True
        if tower:
            want=Tower.from_buffer_copy(original_fixture);s=result['regions']['singleton'];st=result['regions']['state']
            want.active=s[0x89];want.rising=s[0x8a];want.emit=st[0];want.burst=struct.unpack_from('<i',st,2)[0];want.sequence=struct.unpack_from('<i',st,6)[0]
            want.phase=struct.unpack('<i',result['regions']['phase'])[0];want.shake=struct.unpack('<f',result['regions']['shake'])[0]
            state_ok=bytes(want)==bytes(fixture)
        ok=calls==native and bones==native_bones and waters==native_waters and a.seed==cb.seed and result['regions']['object']==co.raw[:v.OBJ_SIZE] and state_ok and (result['eax']&255)==answer
        tally.count('world %d type %d'%(world,typ));tally.count('requests',len(calls))
        tally.add(ok,{'case':n,'world':world,'type':typ,'client':calls[:2],'native':native[:2], 'bones':bones==native_bones,'object':result['regions']['object']==co.raw[:v.OBJ_SIZE],'state':state_ok,'rng':a.seed==cb.seed,'waters':[waters,native_waters]})
    return tally
FAMILIES={'kalima':lambda m,l,g,n:compare(m,l,g,n),'kalima_focus':lambda m,l,g,n:compare(m,l,g,n,focused=True),
          'tower':lambda m,l,g,n:compare(m,l,g,n,tower=True),'tower_focus':lambda m,l,g,n:compare(m,l,g,n,tower=True,focused=True)}
MUTATIONS=[
 ('Kalima world36','||world==36','||world==35','kalima_focus'),
 ('Kalima action low','hero_action < 0x32','hero_action < 0x33','kalima_focus'),
 ('Kalima action high','hero_action >= 0x6f','hero_action >= 0x6e','kalima_focus'),
 ('Kalima radius','sqrtf(dx*dx+dy*dy)<50.0f','sqrtf(dx*dx+dy*dy)<49.0f','kalima_focus'),
 ('Kalima direction gate','MU_OBJF_DIRECTION)<0.1f','MU_OBJF_DIRECTION)<0.0f','kalima_focus'),
 ('Kalima direction sign','-dx*0.6f','dx*0.6f','kalima_focus'),
 ('Kalima damping','mu_obj_f32(o,d)*0.6f','mu_obj_f32(o,d)*0.5f','kalima_focus'),
 ('Kalima head damping','mu_obj_f32(o,h)*0.6f','mu_obj_f32(o,h)*0.5f','kalima_focus'),
 ('Kalima bone','"Bone02"','"Bone01"','kalima_focus'),
 ('Kalima pulse','csin(time*0.001f)','csin(time*0.002f)','kalima_focus'),
 ('Kalima sample clamp','if (x<0) x=0','if (x<0) x=1','kalima_focus'),
 ('Kalima water offset','water+180.0f','water+181.0f','kalima_focus'),
 ('Tower world','world!=39','world!=38','tower_focus'),
 ('Tower hidden','MU_OBJF_HIDDEN_MESH,0','MU_OBJF_HIDDEN_MESH,-1','tower_focus'),
 ('Tower stage low','stage>=3','stage>=4','tower_focus'),
 ('Tower stage high','stage<=18','stage<=17','tower_focus'),
 ('Tower rising stop','>=-749.5f','>-749.5f','tower_focus'),
 ('Tower shake','rnd(c)%6-3','rnd(c)%5-3','tower_focus'),
 ('Tower rise','+13.0f','+12.0f','tower_focus'),
 ('Tower puff bone','bone,c,34,local,p);\n        const float frame','bone,c,33,local,p);\n        const float frame','tower_focus'),
 ('Tower puff frame','frame<12.5f','frame<=12.5f','tower_focus'),
 ('Tower lower mode','f->mode==1','f->mode==2','tower_focus'),
 ('Tower sequence phase','f->phase=2','f->phase=1','tower_focus'),
 ('Tower burst count','k<100','k<99','tower_focus'),
 ('Tower burst pair','0x419+rnd(c)%2','0x419+rnd(c)%3','tower_focus'),
 ('Tower phase1 emit','if(!f->emit)','if(f->emit==1)','tower_focus'),
 ('Tower phase1 count','k<10;++k)','k<9;++k)','tower_focus'),
 ('Tower phase1 scale','/3.0f+5.0f','/4.0f+5.0f','tower_focus'),
 ('Tower phase1 linked subtype','0x4c5,id,p','0x4c5,0,p','tower_focus'),
 ('Tower phase1 reset','f->burst>3','f->burst>4','tower_focus'),
 ('Tower sequence0 RNG','(void)rnd(c);(void)rnd(c);(void)rnd(c);','(void)rnd(c);(void)rnd(c);','tower_focus'),
 ('Tower sequence0 bone','rnd(c)%42+33','rnd(c)%41+33','tower_focus'),
 ('Tower sequence1 bone','indices[3]={11,21,24}','indices[3]={11,22,24}','tower_focus'),
 ('Tower sequence terminal','f->sequence>=5','f->sequence>=6','tower_focus'),
 ('Tower sequence body bone','{3,5,18,19,23,25,26,27,28,29,30}','{3,5,18,19,23,25,26,27,28,29,31}','tower_focus'),
 ('Tower sequence fire','0x7f5a,47,p','0x7f5a,46,p','tower_focus'),
 ('Tower sequence timer','if(f->timer2)','if(!f->timer2)','tower_focus'),
]

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
            with tempfile.TemporaryDirectory(prefix='worlds-inner5-mut-') as td:
                root = Path(td)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                path = root / 'objects/world_inner5_visual.c'; s = path.read_text()
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
