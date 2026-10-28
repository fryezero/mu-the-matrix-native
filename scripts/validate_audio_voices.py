#!/usr/bin/env python3
"""Three reachable NPC voice decision fragments, with surrounding effects excluded.

Model routing a0b/a06/a01 comes from the compare tree at 013b33ef..013b3410.
The fragments execute rand and buff predicates as explicit inputs; sound calls
are recorded. No animation/effect output beyond the sound decision is claimed.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import sys
import pins
from validate_audio import Machine, STACK, STACK_SIZE, ARENA
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report');p.add_argument('--mutations',action='store_true');a=p.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read();m=Machine(text,data)
    m.hook(0x1989721,lambda m:(random_value,0))
    m.hook(0x1295ade,lambda m:(buff,4))
    def sound(m):
        sounds.append(m.arg(0));assert m.arg(1)==0 and m.arg(2)==0
        return 1,0
    m.hook(0xa6ac96,sound)
    ebp=STACK+STACK_SIZE-0x8000
    lib=C.CDLL(str(ROOT/'reconstructed/audio'/('libclient_audio.dylib' if sys.platform == 'darwin' else 'libclient_audio.so')))
    def native(lib,model,r,action,frame,buff):
        lib.mu_audio_npc_voice.argtypes=[C.c_int32,C.c_int32,C.c_uint16,C.c_float,C.c_int]
        return lib.mu_audio_npc_voice(model,r,action,frame,buff)
    report={'families':{},'mismatches':0,'mutants':{}};corpus=[]
    for model,start,end in [(0xa0b,0x13b53e4,0x13b540a),(0xa06,0x13b540f,0x13b5437),(0xa01,0x13b543c,0x13b549c)]:
        count=0
        values=[-2**31,-1024,-257,-256,-64,-1,0,1,63,64,255,256,2**31-1]+list(range(1024))
        inputs=[(r,0,0.,0) for r in values] if model!=0xa01 else [(0,act,f,b) for act in [0,1,65535] for f in [float('nan'),-float('inf'),0.,4.9999995,5.,7.,10.,10.000001,float('inf')] for b in [0,1,2,255]]
        for random_value,action,frame,buff in inputs:
            sounds=[];m.write32(ebp+12,ARENA);m.write(ARENA+0x2a,struct.pack('<H',action));m.write(ARENA+0xd0,struct.pack('<f',frame))
            m.run(start,end,ebp=ebp,esp=ebp-0x1000,stops=(0x13b8058,))
            assert m.reg("eip") in (end, 0x13b8058)
            want=sounds[0] if sounds else -1
            got=native(lib,model,random_value,action,frame,buff)
            assert got==want,(hex(model),random_value,action,frame,buff,want,got)
            corpus.append((model,random_value,action,frame,buff,want));count+=1
        report['families'][hex(model)]={'cases':count,'mismatches':0}
    if a.mutations:
        source=(ROOT/'reconstructed/audio/audio_world.c').read_text()
        variants={'random-divisor':('random % 64','random % 63'), 'frame-upper':('frame <= 10.0f','frame < 10.0f'), 'buff-gate':('!buff_1b && action','buff_1b && action')}
        with tempfile.TemporaryDirectory(prefix='audio-voices-') as tmp:
            for n,(old,new) in variants.items():
                src,dll=Path(tmp)/'bad.c',Path(tmp)/(n+'.dylib');src.write_text(source.replace(old,new,1))
                subprocess.run(['clang','-shared','-I',str(ROOT/'reconstructed/audio'),str(src),'-o',str(dll)],check=True)
                bad=C.CDLL(str(dll));assert any(native(bad,*row[:5])!=row[5] for row in corpus),n
                report['mutants'][n]='caught'
    report['cases']=sum(f['cases'] for f in report['families'].values());print(json.dumps(report,indent=2))
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
