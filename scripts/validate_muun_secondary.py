#!/usr/bin/env python3
"""Kind-1 visual helpers against pinned instructions. No packet, stat or live process inputs.

Executes full secondary setup with named allocation/model/pose/string services, full action dispatcher,
full secondary render caller with recorded RenderObject, and full attachment caller with a supplied named
bone zero-point service. The latter tests caller scaling, not the already verified bone transform itself.
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

ROOT=Path(__file__).resolve().parents[1]
SLOT,OBJ,OWNER,INFO,MODEL,ACTIONS,BASE= [0x22000000+0x10000*k for k in range(7)]
F3=C.c_float*3
BODIES={'setup':(0x9bec34,0x9bf225),'action':(0x9bfabd,0x9bfd63),
        'speed':(0x9bf9a9,0x9bfa9d),'render_gate':(0x9bf31e,0x9bf58b),'attachment':(0x9bf820,0x9bf9a9)}

def build(folder,source):
    p=Path(folder);(p/'secondary.c').write_text(source)
    out=p/('secondary.dylib' if sys.platform=='darwin' else 'secondary.so')
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wconversion','-fPIC',
        '-ffp-contract=off','-fno-fast-math','-shared','-I',str(ROOT/'reconstructed/muun'),str(p/'secondary.c'),
        '-o',str(out)],check=True,capture_output=True)
    lib=C.CDLL(str(out));lib.mu_mv_riding_action.argtypes=[C.c_int32]
    lib.mu_mv_riding_scale.argtypes=[C.c_int32];lib.mu_mv_riding_scale.restype=C.c_float
    lib.mu_mv_riding_speed.argtypes=[C.c_int32,C.c_int32];lib.mu_mv_riding_speed.restype=C.c_float
    lib.mu_mv_riding_admit.argtypes=[C.c_int]*8
    lib.mu_mv_riding_attachment.argtypes=[C.POINTER(C.c_float),C.c_float,C.POINTER(C.c_float)]
    return lib

def region(n,a,p):return am.defined_region(n,a,p)
def put(b,o,fmt,*x):struct.pack_into('<'+fmt,b,o,*x)
def vector(m):return m.uc.reg_read(m.x86.UC_X86_REG_ECX)+4*m.argument(0),4

def compare(lib,machine,count):
    rows={n:{'cases':0,'mismatches':0} for n in ('setup','action','render_gate','attachment')}
    def check(n,result,equal,detail=None):
        row=rows[n];row['cases']+=1
        if not result['ok'] or not equal:
            row['mismatches']+=1
            if 'first' not in row:row['first']={'checks':result['checks'],'error':result.get('error'),
                'stopped':result.get('stopped'),'detail':detail}
    # Complete signed dispatcher domain used by the owner action map plus out-of-range controls.
    for action in list(range(-2,402))+[65535,2**31-1,-2**31]:
        r=machine.execute(0x9bfabd,[action],[],{})
        check('action',r,r['eax']==lib.mu_mv_riding_action(action)&0xffffffff,action)
    # Run secondary constructor through all scale/speed models, with an already allocated OBJECT.
    time_import=vc.HELPER+0x600
    machine.uc.mem_write(0x1a7c49c,struct.pack('<I',time_import))
    for model in range(0x5ca,0x5d4):
        slot=bytearray(244);obj=bytearray(0x3d8);info=bytearray(0x27c)
        owner=bytearray(0x3670);mdl=bytearray(0x100);actions=bytearray(80)
        put(slot,8,'II',BASE,INFO);put(slot,0xbc,'I',OBJ)
        put(info,4,'i',0x20e7);put(info,0x268,'i',model)
        put(owner,0x33ac,'6f',100,200,300,10,20,30);put(mdl,0x22,'h',4);put(mdl,0x30,'I',ACTIONS)
        calls=[]
        def live(m):m.write(OBJ,b'\1');return 0,4
        def zero(m):m.write(m.uc.reg_read(m.x86.UC_X86_REG_ECX),bytes(12));return 0
        def string(m):calls.append(m.cstring(m.argument(0)));return 0,4
        stubs={0x9a9516:lambda m:(1,16),0x966cc4:lambda m:(MODEL,4),0xeaa8cf:lambda m:MODEL,
            time_import:lambda m:123,0x129f4a5:live,0xcfc922:vector,0x9ab41e:lambda m:0,
            0x129f06f:lambda m:(0,4),0xcfcf7b:zero,0x94afda:string,0x94af7d:string,
            0xcfc94a:lambda m:m.uc.reg_read(m.x86.UC_X86_REG_ECX),
            0x129f11a:lambda m:BASE,0x12b5064:lambda m:(0,32)}
        r=machine.execute(0x9bec34,[INFO,OWNER,77,1],[region(n,a,p) for n,a,p in
            [('slot',SLOT,slot),('object',OBJ,obj),('info',INFO,info),('owner',OWNER,owner),
             ('model',MODEL,mdl),('actions',ACTIONS,actions)]],stubs,ecx=SLOT,cleanup=16)
        got=r['regions']['object'];speeds=r['regions']['actions']
        equal=(got[0x158:0x170]==owner[0x33ac:0x33c4] and struct.unpack_from('<f',got,0xa0)[0]==lib.mu_mv_riding_scale(model)
            and struct.unpack_from('<i',got,0x5c)[0]==model and got[0]==1
            and struct.unpack_from('<I',got,0x34c)[0]==OWNER+0x3254 and calls[-1:]==['Bip01 Spine1']
            and all(struct.unpack_from('<f',speeds,16*a+4)[0]==lib.mu_mv_riding_speed(model,a) for a in range(5)))
        check('setup',r,equal,{'model':model,'calls':calls,'scale':struct.unpack_from('<f',got,0xa0)[0]})
    # Whole render caller, with synthetic flags. Stubs record rendering, never infer a live selection.
    for owner_on,hidden,obj_on,live,buff,selected,predicate,frustum in itertools.product((0,1),repeat=8):
        slot=bytearray(244);obj=bytearray(0x3d8);owner=bytearray(0x3670);info=bytearray(0x27c)
        put(slot,4,'I',OWNER if owner_on else 0);put(slot,0xc,'I',INFO);put(slot,0xbc,'I',OBJ if obj_on else 0)
        put(info,4,'i',8423);owner[0x31e8]=hidden;calls=[]
        def draw(m):calls.append([m.argument(k) for k in range(6)]);return 0
        stubs={0x9a9ae2:lambda m:0,0x95f977:lambda m:live,0x1295ade:lambda m:(buff,4),
            0x129dcda:lambda m:8423 if selected else 8424,0x106ccd5:lambda m:predicate,
            0x9c10d0:lambda m:0,0xcfc922:vector,0x16ccce7:lambda m:frustum,0x16d4fe4:draw,
            0x9c104e:lambda m:0,0x106c382:lambda m:0}
        r=machine.execute(0x9bf31e,[],[region(n,a,p) for n,a,p in
            [('slot',SLOT,slot),('object',OBJ,obj),('owner',OWNER,owner),('info',INFO,info)]],stubs,ecx=SLOT)
        admitted=lib.mu_mv_riding_admit(owner_on,hidden,obj_on,live,buff,8423 if selected else 8424,8423,predicate)
        expected=[[OBJ,1,0,0,0xffffffff,0xffffffff]] if admitted and frustum else []
        check('render_gate',r,calls==expected,{'got':calls,'expected':expected})
    rng=random.Random('muun-secondary')
    for k in range(count):
        slot=bytearray(244);obj=bytearray(0x3d8);mdl=bytearray(0x100)
        put(slot,0xbc,'I',OBJ);put(obj,0x5c,'i',0x5cd)
        scale=rng.uniform(.1,2);point=[rng.uniform(-300,300) for _ in range(3)];put(obj,0xa0,'f',scale)
        matrix=(C.c_float*12)(*[rng.uniform(-2,2) for _ in range(12)])
        for a in range(3):matrix[a*4+3]=point[a]
        def transform(m):m.write(m.argument(2),struct.pack('<3f',*point));return 0,16
        stubs={0x966cc4:lambda m:(MODEL,4),0xeaa8cf:lambda m:MODEL,0x9a1983:lambda m:1,
            0xcfc94a:lambda m:m.uc.reg_read(m.x86.UC_X86_REG_ECX),0x129f18a:lambda m:(BASE,8),
            0x12b6ef1:transform,0xcfc922:vector}
        r=machine.execute(0x9bf820,[],[region(n,a,p) for n,a,p in
            [('slot',SLOT,slot),('object',OBJ,obj),('model',MODEL,mdl)]],stubs,ecx=SLOT)
        out=F3();lib.mu_mv_riding_attachment(matrix,scale,out);out[2]+=30.0
        expected=struct.pack('<3f',*out)
        check('attachment',r,r['regions']['slot'][0xe4:0xf0]==expected)
    return rows

MUTANTS=[('action_idle','case 327: return 0','case 327: return 2'),
 ('action_run','case 109: return 2','case 109: return 0'),('action_skill','case 303: return 4','case 303: return 2'),
 ('scale_wolf','return 0.6f','return 0.7f'),('scale_later','return 0.9f','return 0.8f'),
 ('speed_wolf','return 0.8f','return 0.4f'),('speed_later','return 0.4f','return 0.8f'),
 ('owner_gate','return owner &&','return !owner &&'),('hidden_gate','!hidden','hidden'),
 ('object_gate','&& object &&','&& !object &&'),('live_gate','live == 1','live != 1'),
 ('buff_gate','!buff26','buff26'),('selection','selected == item','selected != item'),
 ('predicate','!predicate','predicate'),('attachment_scale','* scale','* -scale'),
 ('attachment_axis','k * 4 + 3','k * 4 + 2')]

def run(count,mutations):
    start=time.monotonic();text=pins.load_pinned(pins.TEXT.default_str(),pins.TEXT.size,pins.TEXT.sha256,'text')
    data=pins.load_pinned(pins.DATA.default_str(),pins.DATA.size,pins.DATA.sha256,'data');machine=vc.Combat(text,data)
    source=(ROOT/'reconstructed/muun/secondary.c').read_text()
    with tempfile.TemporaryDirectory(prefix='muun-secondary-') as td:
        p=Path(td);(p/'base').mkdir();families=compare(build(p/'base',source),machine,count);mutants={}
        if mutations:
            for name,old,new in MUTANTS:
                if source.count(old)!=1:raise ValueError(name+' ambiguous anchor')
                (p/name).mkdir();rows=compare(build(p/name,source.replace(old,new)),machine,min(count,50))
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
