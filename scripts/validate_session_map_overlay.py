#!/usr/bin/env python3
"""E7 marker handlers and detector packet loop against pinned original instructions.
GFx values, heap, smart-pointer lookup and vector insertion are modeled. The actual
packet loops and existing marker/detector GFx helper instructions run unchanged.
No dispatcher table, decode or live client access.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import pins
import validate_map as vm
import validate_lang as vl
import live_lang_to_plain as plain
import client_ui_machine as cm
ROOT = Path(__file__).resolve().parents[1]

def run(text, data, lib, cases):
    snap = plain.Snapshot(b'MULANGV1'+struct.pack('<I',0))
    m = vl.LangMachine(text,data,snap)
    vm.install_common(m)
    rng = random.Random(20261028)
    results = {}
    for family, address in [('marker3',0x126d85c),('marker4',0x123134b),('detector_packet',0x1233c9b)]:
        for case in range(cases):
            vm.prepare(m)
            w=vm.window(m)
            def getter(mm):
                out=mm.args(1)[0];mm.write(out,struct.pack('<II',w,0));return out
            m.stub(0x9fd699,getter,4)
            m.stub(0x9617c6,lambda mm:0)
            # The vector element copy is modeled; count/offset/skip/zero-extension
            # remain in the original E7/05 packet loop.
            entries=[]
            def push(mm):
                entries.append(struct.unpack('<iii',mm.read(mm.args(1)[0],12)));return 0
            m.stub(0x121541a,push,4)
            def copy_vec(mm):
                ptr=mm.alloc(max(4,12*len(entries)),define=True)
                for i,e in enumerate(entries):mm.write(ptr+12*i,struct.pack('<iii',*e))
                dest=mm.uc.reg_read(cm.UC_X86_REG_ECX)
                mm.write(dest,struct.pack('<III',ptr,ptr+12*len(entries),ptr+12*len(entries)))
                return dest
            m.stub(0x12188f8,copy_vec,4)
            m.stub(0xc6c014,lambda mm:0)
            m.stub(0xc6b2b0,lambda mm:0,4) # show setter, outside collection comparison
            if family.startswith('marker'):
                p=bytearray([0xc1,0,0xe7,int(family[-1]),rng.randrange(256),rng.randrange(7),rng.randrange(8),case%4,rng.randrange(256),rng.randrange(256)])
                p+=('Name%d'%case).encode()+b'\0';p[1]=len(p)
            else:
                count=[0,1,2,40,256][case%5]
                p=bytearray([0xc2,0,0,0xe7,5,0,0,count&255,count>>8])
                for i in range(count):p+=struct.pack('<BHH',0 if i%4==0 else rng.choice([1,2,3,255]),rng.randrange(65536),rng.randrange(65536))
                p[1:3]=len(p).to_bytes(2,'big')
            ptr=m.alloc(len(p)+16,define=True);m.write(ptr,bytes(p)+bytes(16))
            m.call(address,[ptr])
            if family.startswith('marker'):
                u=vm.Unit();r=lib.mu_map_overlay_marker_parse(bytes(p),len(p),C.byref(u))
                got=[vm.logged_unit(e) for e in vm.W.log if e[0]=='invoke']
                expected=[]
                if r==1:expected=[('addUnit',u.type,u.key,u.state,u.text.decode('latin1'),vm.f2u(u.x),vm.f2u(u.y))]
                elif r==2:expected=[('delUnit',u.type,u.key,None,None,None,None)]
            else:
                out=(vm.Unit*256)();n=lib.mu_map_overlay_detect_parse(bytes(p),len(p),out)
                assert n>=0
                got=[(e[1],e[2]) for e in vm.W.log if e[0]=='invoke']
                arr=[]
                for u in out[:n]:arr.append((('type',('i',u.type)),('key',('i',u.key)),('state',('i',u.state)),('text',('s',u.text.decode())),('x',('f',vm.f2u(u.x))),('y',('f',vm.f2u(u.y)))))
                expected=[('AddDetectedUnit',tuple(arr))] if n else []
            assert got==expected,(family,case,got[:2],expected[:2])
        results[family]={'cases':cases,'mismatches':0}
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text',default=pins.TEXT.default_str());p.add_argument('--data',default=pins.DATA.default_str())
    p.add_argument('--cases',type=int,default=500);p.add_argument('--mutants',action='store_true');p.add_argument('--output',required=True);a=p.parse_args()
    text=pins.TEXT.read(a.text,exit=True);data=pins.DATA.read(a.data,exit=True)
    with tempfile.TemporaryDirectory() as tmp:
        def build(k):
            out=Path(tmp)/('map%d.dylib'%k)
            subprocess.run(['cc','-shared','-fPIC','-O2','-DMU_MAP_OVERLAY_MUTATION=%d'%k,
                str(ROOT/'native/session/domains/map_overlay_wire.c'),str(ROOT/'reconstructed/map/map_hud.c'),'-o',str(out)],check=True,capture_output=True)
            lib=C.CDLL(str(out));lib.mu_map_overlay_marker_parse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(vm.Unit)]
            lib.mu_map_overlay_detect_parse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(vm.Unit)];return lib
        result={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':run(text,data,build(0),a.cases),'mutants_caught':[],'mismatches':0}
        if a.mutants:
            for k in range(1,5):
                try:run(text,data,build(k),20)
                except AssertionError:result['mutants_caught'].append(k)
                else:raise RuntimeError('surviving compiled mutant %d'%k)
    result['cases']=sum(f['cases'] for f in result['families'].values())
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
