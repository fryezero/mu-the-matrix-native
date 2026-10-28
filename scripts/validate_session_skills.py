#!/usr/bin/env python3
"""SESSION-SKILL-001: original key serialization and plaintext packet-tail slices.
No keyed AddData, settings reconstruction, crypto, decode or dispatch-table walk.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import client_ui_machine as cm
import pins
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'native/session/domains/skills_wire.c'

def build(source,out):
    subprocess.run(['cc','-shared','-fPIC','-O2','-I',str(SRC.parent),str(source),'-o',str(out)],check=True,capture_output=True)
def load(path):
    l=C.CDLL(str(path));l.mu_skills_save_request.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(C.c_int32),C.POINTER(C.c_uint8)]
    l.mu_skills_save_request.restype=C.c_size_t
    l.mu_skills_master_points_apply.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(C.c_uint8),C.c_size_t]
    return l

def run(text,data,lib,n):
    rng=random.Random(20261028)
    # One fresh machine per run, including each compiled mutant.
    m=cm.Machine(text,data)
    m.allow((0x182ff60,0x182ffdf),(0x18304cc,0x183052c),(0x1285995,0x12859b4),(0xa00192,0xa001a6))
    slots=[];packet=[];sends=[]
    m.stub(0x95f861,lambda m:0x11111111)
    m.stub(0x1096a19,lambda m:slots[m.args(1)[0]]&0xffffffff,4)
    m.stub(0xd51b91,lambda m:0)
    m.stub(0xd51ba6,lambda m:0)
    def begin(m):
        head,op=m.args(2);packet[:]=[head,0,op];return 0
    m.stub(0xd51baf,begin,8)
    m.stub(0x95c204,lambda m:packet.append(m.args(1)[0]&255) or 0,4)
    def add(m):
        ptr,size,keyed=m.args(3)
        assert keyed==1 # record pre-transform fields; never execute AddData
        packet.extend(m.read(ptr,size));return 0
    m.stub(0xd51c9b,add,12)
    m.stub(0xd51d4f,lambda m:sends.append(m.args(2)) or 0,8)
    for i in range(n):
        m.reset();slots[:]=[rng.choice([-1,0,19,330,1000,65535,rng.randrange(65536)]) for _ in range(10)]
        settings=bytes(rng.randrange(256) for _ in range(17))
        frame=m.alloc(0x2000,define=True)+0x1800
        m.write(frame-0x58,bytes(37));m.put32(frame-0x24,0)
        def execute(start,end):
            m.uc.reg_write(cm.UC_X86_REG_EBP,frame)
            m.uc.reg_write(cm.UC_X86_REG_ESP,cm.STACK_BASE+cm.STACK_SIZE-0x1000)
            m.uc.emu_start(start,end,count=100000)
            assert not m.errors,m.errors
            assert m.uc.reg_read(cm.UC_X86_REG_EIP)==end
        execute(0x182ff60,0x182ffdf)
        keys=m.read(frame-0x58,20)
        m.write(frame-0x44,settings);sends.clear();packet.clear()
        execute(0x18304cc,0x183052c)
        out=(C.c_uint8*41)();a=(C.c_int32*10)(*slots);tail=(C.c_uint8*17).from_buffer_copy(settings)
        size=lib.mu_skills_save_request(out,41,a,tail)
        assert size==41 and bytes(out)[4:24]==keys
        assert sends==[[0,0]]
        packet[1]=len(packet)
        assert bytes(out)==bytes(packet),(i,bytes(out).hex(),bytes(packet).hex())
        assert lib.mu_skills_save_request(out,40,a,tail)==0
    # Execute the answer prefix and its real +0x34 setter, comparing the whole attribute record.
    for i in range(n):
        m.reset()
        raw=bytes(rng.randrange(256) for _ in range(0x200))
        packet=bytearray(0x1d);struct.pack_into('<H',packet,6,rng.choice([0,1,99,32767,32768,65535,rng.randrange(65536)]))
        attr=m.alloc(len(raw),define=True);m.write(attr,raw);m.put32(0x1d1df1c,attr)
        p=m.alloc(len(packet),define=True);m.write(p,packet)
        esp=cm.STACK_BASE+cm.STACK_SIZE-0x1000
        m.write(esp,struct.pack('<II',cm.RETURN_SENTINEL,p))
        m.uc.reg_write(cm.UC_X86_REG_ESP,esp)
        m.uc.reg_write(cm.UC_X86_REG_EBP,0)
        m.uc.emu_start(0x1285995,0x12859b4,count=1000)
        assert not m.errors,m.errors
        assert m.uc.reg_read(cm.UC_X86_REG_EIP)==0x12859b4
        a=(C.c_uint8*len(raw)).from_buffer_copy(raw);b=(C.c_uint8*len(packet)).from_buffer_copy(packet)
        assert lib.mu_skills_master_points_apply(a,len(a),b,len(b))==1
        assert bytes(a)==m.read(attr,len(raw)),i
        assert lib.mu_skills_master_points_apply(a,0x37,b,len(b))==0
    return {'keys':n,'packet_tail':n,'master_points':n}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=500);p.add_argument('--mutants',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    text=pins.TEXT.read(exit=True);data=pins.DATA.read(exit=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);path=tmp/'clean.dylib';build(SRC,path);families=run(text,data,load(path),a.cases);caught=[]
        if a.mutants:
            for i,(name,old,new) in enumerate([('rotation','(i+1)%10','i'),('endian','(id>>8)','id'),('opcode','out[3]=0x30','out[3]=0x31'),('points_offset','attr + 0x34','attr + 0x30'),('points_sign','(int16_t)((uint16_t)frame[6]','(uint16_t)((uint16_t)frame[6]')]):
                source=tmp/f'm{i}.c';s=SRC.read_text();assert s.count(old)==1;source.write_text(s.replace(old,new));path=tmp/f'm{i}.dylib';build(source,path)
                try:run(text,data,load(path),32)
                except AssertionError:caught.append(name)
                else:raise AssertionError('survived '+name)
    report={'families':families,'total':sum(families.values()),'mismatches':0,'mutants_caught':caught,'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256}
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
