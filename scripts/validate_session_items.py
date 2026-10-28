#!/usr/bin/env python3
"""Pinned instruction checks for recorded ground-delete, pickup builder and sound/label tail.
No dispatcher, decode, transform or send wrap is executed. Mid-function slices have
explicit synthetic EBP locals and terminate before unrelated MoveHero/UI branches.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import client_ui_machine as cm
import pins
from unicorn import UC_HOOK_CODE
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'native/session/domains/items_wire.c'
SLICES={'delete':(0x12338bc,0x12339dd),'pickup_zen':(0x16983d6,0x1698485),
        'pickup_item':(0x1698f65,0x1699017),'pickup_tail':(0x1242b3c,0x1242c2b)}
def buf(b):return (C.c_uint8*len(b)).from_buffer_copy(b)
def run(text,data,lib,n):
    m=cm.Machine(text,data);m.allow(*SLICES.values()); rng=random.Random(20261028)
    log=[]; packet=[]; sends=[]
    ecx=lambda:m.uc.reg_read(cm.UC_X86_REG_ECX)
    def stop(mm):mm.uc.reg_write(cm.UC_X86_REG_EIP,cm.RETURN_SENTINEL);return cm.REDIRECT
    def reset_item(mm):log.append(('reset',(ecx()-0xb4780cc)//0x560));return 0
    def live(mm):log.append(('live',(ecx()-0xb4781f8)//0x560,mm.args(1)[0]));return 0
    def label(mm):mm.write(mm.args(1)[0],struct.pack('<II',int(has_label),0));return 0
    def remove(mm):log.append(('label',(mm.args(1)[0]-0xb4780c8)//0x560));return 0
    m.stub(0xccc144,reset_item);m.stub(0x129f4a5,live,4);m.stub(0x9a19ae,label,4)
    m.stub(0xc84152,remove,4);m.stub(0x9617c6,lambda mm:0)
    m.stub(0xd51b91,lambda mm:0);m.stub(0xd51ba6,lambda mm:0)
    def begin(mm):head,op=mm.args(2);packet[:]=[head,0,op];return 0
    def add(mm):
        ptr,size,encoded=mm.args(3);assert encoded==1;packet.extend(mm.read(ptr,size));return ecx()
    m.stub(0xd51baf,begin,8);m.stub(0xd51c9b,add,12)
    m.stub(0xd51d4f,lambda mm:sends.append(mm.args(2)) or 0,8)
    m.stub(0xa6ac96,lambda mm:log.append(('sound',mm.args(3)[0])) or 0)
    # Slice stops preserve all instructions inside each bounded branch.
    for a in (0x1698485,0x1699017,0x1242c2b):m.stub(a,stop)
    frame=0
    for name,(start,end) in SLICES.items():
        if name != "delete":
            m.uc.hook_add(UC_HOOK_CODE,lambda uc,a,z,u: uc.reg_write(cm.UC_X86_REG_EBP,frame),begin=start,end=start)
    counts={}
    for family,(start,end) in SLICES.items():
        for i in range(n):
            m.reset();log.clear();packet.clear();sends.clear();has_label=i%2==0
            if family=='delete':
                keys=[0,999,1000,65535]+[rng.randrange(65536) for _ in range(i%20)]
                if i==0:keys=[]
                p=bytes([0xc2,0,5+2*len(keys),0x21,len(keys)])+b''.join(k.to_bytes(2,'big') for k in keys)
                ptr=m.alloc(len(p),define=True);m.write(ptr,p);m.call(start,[ptr]);out=(C.c_uint16*255)()
                count=lib.mu_items_delete_parse(buf(p),len(p),out);assert count==len(keys)
                expected=[]
                for j in range(count):expected.extend([('reset',out[j]),('live',out[j],0)]+([('label',out[j])] if has_label else []))
                assert log==expected,(family,i,log,expected)
            else:
                frame=m.alloc(0x10000,define=True)+0xf000
                m.uc.reg_write(cm.UC_X86_REG_EBP,frame)
                # m.call keeps EBP, uses a separate normal call stack.
                if family.startswith('pickup_') and family!='pickup_tail':
                    slot=rng.randrange(1000);pending=-1 if i%3 else rng.randrange(1000)
                    m.put32(0xb437c18,slot);m.put32(0x1cf1028,pending&0xffffffff)
                    m.call(start);out=buf(bytes(5));size=lib.mu_items_pickup_request(out,slot,pending)
                    assert size==(5 if pending==-1 else 0)
                    assert m.u32(0x1cf1028)==(slot if pending==-1 else pending)
                    if size:
                        assert sends==[[1,0]] and bytes(out)==bytes([packet[0],len(packet),*packet[2:]])
                    else:assert not sends and not packet
                else:
                    codes=[0x1c0d,0x1c0e,0x1c10,0x180f,0x1c16,0x1c1f,0x1c29,1,0x1c0f]
                    code=codes[i%len(codes)] if i%2 else rng.randrange(0x2c01)
                    slot=i%1000;m.put32(frame-0x14,code);m.put32(frame-0xe0,slot);m.put32(0xa39d754,0x30000000)
                    m.call(start);sound=lib.mu_items_pickup_tail(code)
                    assert log==[('sound',sound)]+([('label',slot)] if has_label else []),(family,i,log,sound)
        counts[family]=n
    return counts

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--text',default=pins.TEXT.default_str());p.add_argument('--data',default=pins.DATA.default_str());p.add_argument('--cases',type=int,default=300);p.add_argument('--mutants',action='store_true');p.add_argument('--output',required=True);a=p.parse_args()
    text=pins.load_pinned(a.text,pins.TEXT.size,pins.TEXT.sha256,'text');data=pins.load_pinned(a.data,pins.DATA.size,pins.DATA.sha256,'data')
    with tempfile.TemporaryDirectory() as tmp:
        def build(source,name):
            src=Path(tmp)/(name+'.c');src.write_text(source);out=Path(tmp)/(name+'.dylib')
            subprocess.run(['cc','-shared','-fPIC','-O2','-I',str(SRC.parent),str(src),'-o',str(out)],check=True,capture_output=True)
            l=C.CDLL(str(out));l.mu_items_delete_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(C.c_uint16)];return l
        source=SRC.read_text();counts=run(text,data,build(source,'base'),a.cases);caught=[]
        if a.mutants:
            for name,old,new in [('delete_clamp','key < 1000','key <= 1000'),('builder_endian','slot >> 8','slot >> 7'),('builder_pending','pending != -1','pending == -1'),('pickup_sound','return 0x45','return 0x1d')]:
                assert old in source
                try:run(text,data,build(source.replace(old,new),name),max(40,min(a.cases,80)))
                except AssertionError:caught.append(name)
                else:raise AssertionError('surviving mutant '+name)
    r={'cases':counts,'total':sum(counts.values()),'mismatches':0,'mutants_caught':caught,'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,
       'slices':{k:{'start':hex(x),'end':hex(y),'sha256':hashlib.sha256(text[x-cm.TEXT_BASE:y-cm.TEXT_BASE]).hexdigest()} for k,(x,y) in SLICES.items()}}
    Path(a.output).write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
