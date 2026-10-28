#!/usr/bin/env python3
"""Compare the production Tarkan/Raklion haze with pinned client instructions, offline."""
import argparse
import ctypes as C
import hashlib
import json
import random
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import pins
import validate_terrain as v

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reconstructed/terrain/world_haze.c'
RANGES={'tarkan':(0x16b247c,0x16b2627), 'raklion':(0xe9eae8,0xe9ec6a),
        'quad':(0x184f4ba,0x184f793), 'tarkan_load':(0x1839ac1,0x1839b01),
        'raklion_load':(0x183f494,0x183f4d4)}


def compare(library, cases):
    from unicorn import UC_HOOK_CODE
    text,data=pins.TEXT.read(),pins.DATA.read()
    client=v.Client(text,data)
    uc=client.uc
    lib=C.CDLL(str(library))
    lib.mu_world_haze_draw.argtypes=[C.c_int32,C.c_float,C.c_uint32,C.c_uint32,C.POINTER(v.Sink)]
    lib.mu_world_haze_quad.argtypes=[C.c_int32]+[C.c_float]*8+[C.c_uint32,C.c_uint32,C.POINTER(v.Sink)]
    lib.mu_world_haze_texture.argtypes=[C.c_int32,C.c_int];lib.mu_world_haze_texture.restype=C.c_char_p
    def recorder():
        out=[]
        return out,v.Authored.recorder(out),None
    # glVertex2f is outside the terrain validator's recorded subset.
    stub=client.STUBS+0x3000
    uc.mem_write(0x1a7c684,struct.pack('<I',stub));uc.mem_write(stub,b'\xc2\x08\x00')
    def vertex(uc_,a,n,u):client.stream.append(('v',client.arg(0),client.arg(1),0))
    uc.hook_add(UC_HOOK_CODE,vertex,begin=stub,end=stub)
    client.set_bitmaps({0x7f21:(128,128),0x7f22:(128,128)})
    # Screen geometry executes through original width/height converters and Vector2.
    # Only the bitmap lookup, GL calls and wrappers use the existing terrain harness.
    report={}
    rng=random.Random(27106)
    def check(family,got,want,ok=True):
        row=report.setdefault(family,dict(cases=0,equal=0,mismatches=0,stopped=0))
        row['cases']+=1;row['stopped']+=int(not ok)
        row['equal']+=int(ok and got==want);row['mismatches']+=int(got!=want)
        if (not ok or got!=want) and 'first' not in row:
            row['first']={'original':repr(got)[:1600],'authored':repr(want)[:1600],'error':client.error}
    times=[0,1,-1,99999,100000,100001,-99999,-100000,-100001,2147483520,-2147483648,float('nan'),float('inf')]
    for family,world,start,end in [('tarkan',8,0x16b247c,0x16b2eb6),('raklion',57,0xe9eae8,None)]:
        for k in range(cases):
            t=v.f32(times[k] if k<len(times) else rng.uniform(-2000000,2000000))
            w,h=[(640,480),(1722,1048),(1920,1080),(321,199)][k%4]
            uc.mem_write(0x1cf1624,struct.pack('<II',w,h));client.write('world','i',[world])
            uc.mem_write(0x6fce370,struct.pack('<f',t))
            ok=client.call(start,[],until=end)
            got=list(client.stream)
            stream,sink,keep=recorder()
            lib.mu_world_haze_draw(world,t,w,h,C.byref(sink))
            check(family,got,stream,ok)
    for k in range(cases):
        w,h=[(640,480),(1722,1048),(1920,1080)][k%3]
        args=[0x7f21+k%2]+[v.f32(rng.uniform(-200,800)) for _ in range(4)]+[v.f32(rng.uniform(-10,10)) for _ in range(4)]
        uc.mem_write(0x1cf1624,struct.pack('<II',w,h))
        ok=client.call(0x184f4ba,[args[0]]+[v.fbits(f) for f in args[1:]])
        stream,sink,keep=recorder();lib.mu_world_haze_quad(*args,w,h,C.byref(sink))
        check('quad',client.stream,stream,ok)
    # Stop at the end of the two relevant loader calls, not later object loading.
    loads=[]
    def loader(uc_,a,n,u):
        address=client.arg(0)
        name=bytes(uc.mem_read(address,100)).split(b'\0')[0].decode().replace('\\','/')
        loads.append((name,*[client.arg(i) for i in range(1,6)]));client.ret(1,0)
    uc.hook_add(UC_HOOK_CODE,loader,begin=0x185baac,end=0x185baac)
    for world,start,end in [(8,0x1839ac1,0x1839b01),(57,0x183f494,0x183f4d4),(58,0x183f494,0x183f4d4)]:
        loads.clear();ok=client.call(start,[],until=end)
        expected=[(lib.mu_world_haze_texture(world,i).decode(),0x7f21+i,0x2601,0x2901,1,0) for i in range(2)]
        check('load',list(loads),expected,ok)
    # Out-of-lane worlds must stay silent; 58 must share Raklion's exact stream.
    for world in [0,1,2,3,7,10,33,37,51,56,59,80,142,-1,58]:
        stream,sink,keep=recorder();lib.mu_world_haze_draw(world,1234,640,480,C.byref(sink))
        if world==58:
            other,osink,okeep=recorder();lib.mu_world_haze_draw(57,1234,640,480,C.byref(osink));want=other
        else:want=[]
        check('world_gate',stream,want)
    return {'families':report,'provenance':{name:{'start':hex(a),'end':hex(b),'sha256':hashlib.sha256(text[a-0x401000:b-0x401000]).hexdigest()} for name,(a,b) in RANGES.items()}}


MUTANTS=[('tarkan','phase*0.0002f','phase*0.0003f'),('raklion','(-phase)*0.0006f','phase*0.0006f'),
         ('quad','dv*0.25f','dv*0.5f'),('tarkan','s->context,3,0','s->context,2,0'),
         ('raklion','0.4f,0.4f,0.45f','0.3f,0.3f,0.45f'),('load','Object9/sand01.jpg','Object9/sand02.jpg'),
         ('world_gate','world!=58','world!=59')]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=600);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output',required=True)
    args=ap.parse_args()
    if args.cases<20:ap.error('--cases must be at least 20')
    source=SOURCE.read_text()
    # Freeze authored input for the whole comparison and all compiled mutants.
    with tempfile.TemporaryDirectory(prefix='mu-worlds-f-') as tmp:
        tmp=Path(tmp)
        def build(code,index):
            c=tmp/f'haze{index}.c';lib=tmp/f'haze{index}.dylib';c.write_text(code)
            subprocess.run(['clang','-std=c11','-O2','-ffp-contract=off','-fPIC','-shared','-I'+str(SOURCE.parent),str(c),'-o',str(lib)],check=True,capture_output=True)
            return lib
        report=compare(build(source,0),args.cases)
        report['mutants']=[]
        if args.mutations:
            for k,(family,old,new) in enumerate(MUTANTS):
                assert old in source,old
                result=compare(build(source.replace(old,new),k+1),max(20,min(args.cases,60)))['families'][family]
                report['mutants'].append(dict(family=family,caught=result['mismatches']>0,stopped=result['stopped']))
    Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    return int(any(r['equal']!=r['cases'] for r in report['families'].values()) or any(not r['caught'] or r['stopped'] for r in report['mutants']))

if __name__=='__main__':sys.exit(main())
