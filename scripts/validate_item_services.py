#!/usr/bin/env python3
"""Execute the pinned personal-store predicates and repair UI builder.

Stable record lookups execute, string/notification and packet transport
boundaries are modelled. No original client process or network is used.
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
from validate_mix import ROOT, TEXT_SHA, DATA_SHA, Client, put
import client_ui_machine as cm
import pins


def bind(path):
    lib=C.CDLL(str(path))
    for name in ('mu_personal_store_ban','mu_personal_store_register'):
        getattr(lib,name).argtypes=[C.c_void_p,C.c_void_p]
    lib.mu_repair_request.argtypes=[C.c_void_p,C.c_uint8,C.c_uint8]
    return lib

class Services(Client):
    def __init__(self,text,data):
        super().__init__(text,data)
        m=self.m
        for a in (0x16be0dc,0x16b823e,0xc00b38,0xbf1765,0xbf1916,0xab83e4,0xad47a3,0xad4c7d,0xad95c8,0x16be1d9):
            m.allow((a,cm.function_extent(text,a)))
        for a in (0x95f027,0x94997e,0x95f136,0x95f4ec,0x8e83a0):
            m.stub(a,lambda _:self.window,4 if a in (0x95f027,0x94997e,0x95f136) else 0)
        m.stub(0xabce9f,lambda _:0,16)
        m.stub(0x195a3d0,lambda _:0 if m.args(2)[1]==0x1a958c0 else 1)
        m.stub(0xb95a14,lambda _:setattr(self,'repair_mode',m.args(1)[0]) or 0,4)
        self.page=m.alloc(0x100,True)
        m.stub(0xabf970,lambda _:1)
        m.stub(0xab73e6,lambda _:self.page,4)
        m.stub(0xabeca4,lambda _:1)
        m.stub(0xabed32,lambda _:1)
        m.stub(0xad5094,lambda _:1)
        m.stub(0xad3fd9,lambda _:self.item if m.args(1)[0]==self.cell else 0,4)
        m.stub(0xabecfb,lambda _:self.window)
        m.stub(0xabee1a,lambda _:self.visible)

    def single_repair(self,cell,npc):
        m=self.m;self.cell=cell;self.visible=npc;self.packet=[]
        m.write(self.page,bytes(0x100));m.put32(self.page+0x2c,8);m.put32(self.page+0x44,1)
        m.write(self.item,bytes(300));m.put32(self.item,self.record);m.put32(self.item+0x10,1)
        m.write(self.item+0x69,bytes([cell%8,cell//8]));m.write(self.record,bytes(708));m.write(self.record+0x2ae,b'\x01')
        m.put32(self.manager+0x8c,8);m.put32(self.manager+0x90,8)
        m.call(0xab83e4,[cell],ecx=self.manager)
        if self.packet:self.packet[1]=len(self.packet)
        return bytes(self.packet)

    def predicate(self,address,rec,it):
        m=self.m;m.write(self.record,rec)
        if it is None:p=0
        else:
            raw=bytearray(it);put(raw,0,self.record);m.write(self.item,raw);p=self.item
        return m.call(address,[p],ecx=self.manager)&255
    def toggle(self,state):
        m=self.m;m.put32(self.window+0xa8,state)
        m.call(0xbf1765,ecx=self.window)
        return m.u32(self.window+0xa8),self.repair_mode
    def repair_all(self):
        self.packet=[];self.m.call(0xbf1916,[1,1,0,0],ecx=self.manager)
        if self.packet:self.packet[1]=len(self.packet)
        return bytes(self.packet)

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=10000)
    p.add_argument('--evidence',type=Path,default=pins.evidence_dir());p.add_argument('--report',type=Path);p.add_argument('--mutations',action='store_true')
    a=p.parse_args()
    base=a.evidence
    text=pins.TEXT.read(base/pins.TEXT.relative)
    data=pins.DATA.read(base/pins.DATA.relative)
    client=Services(text,data);rng=random.Random(0x53544f52);corpus=[];counts={}
    src=ROOT/'reconstructed/mix/item_services.c'
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        def compile_to(source,name):
            path=td/(name+'.dylib');f=td/(name+'.c');f.write_text(source)
            subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC','-I',str(src.parent),str(f),'-o',str(path)],check=True)
            return bind(path)
        lib=compile_to(src.read_text(),'services')
        def check(name,got,want):
            counts[name]=counts.get(name,0)+1
            if got!=want:raise AssertionError((name,counts[name],got,want))
        for k in range(a.cases):
            rec=bytearray(708);it=bytearray(300)
            code=rng.choice([-1,0x2c01,0x1a14,0x1c0b,0x1c1a,0x1c15,rng.randrange(0x2c01)])
            put(it,0x10,code);put(it,0x14,rng.randrange(16)<<3)
            rec[0x250]=rng.choice([5,8,25,26,rng.randrange(256)])
            rec[0x251]=rng.choice([0x2b,0x2e,0x2f,0x4f,rng.randrange(256)])
            rec[0x2aa]=rng.choice([0,1,2,255]);it[0x38]=rng.choice([0,1,254,255])
            it[0x92]=rng.randrange(3);struct.pack_into('<H',it,0x70,rng.choice([0,1,2,257]))
            raw=None if k%53==0 else bytes(it)
            for name,address in (('ban',0x16be0dc),('register',0xc00b38)):
                want=client.predicate(address,bytes(rec),raw)
                fn=getattr(lib,'mu_personal_store_'+name)
                check(name,fn(bytes(rec),raw),want);corpus.append((name,bytes(rec),raw,want))
            # Execute the apparently contradictory helper across all record kinds.
            if raw is not None:
                check('stable_helper',client.predicate(0x16b823e,bytes(rec),raw),1)
        for state in (0,1,2,3,-1,0x7fffffff):
            want,flag=client.toggle(state)
            check('toggle',lib.mu_repair_toggle(state)&0xffffffff,want)
            check('toggle_flag',int(want==2),flag)
        packet=C.create_string_buffer(5);lib.mu_repair_request(packet,255,0)
        check('repair_all_packet',packet.raw,client.repair_all())
        packet_corpus=[]
        for cell in range(64):
            for npc in (0,1):
                want=client.single_repair(cell,npc)
                lib.mu_repair_request(packet,cell+12,not npc)
                check('single_repair_packet',packet.raw,want)
                packet_corpus.append((cell+12,not npc,want))
        mutations={}
        if a.mutations:
            changes=[('period','it[0x92]==1','it[0x92]!=0'),
                     ('flag','return !r[0x2aa];','return !r[0x2ab];'),
                     ('bound','bound==1','bound!=0'),
                     ('level','code==0x1c15 && level==3','code==0x1c15 && level==4')]
            for name,before,after in changes:
                mutated=compile_to(src.read_text().replace(before,after),'mutant_'+name)
                caught=sum(getattr(mutated,'mu_personal_store_'+family)(rec,it)!=want for family,rec,it,want in corpus)
                assert caught,(name,'undetected mutation');mutations[name]=caught
            for name,before,after in [('packet_slot','out[3]=slot','out[3]=(uint8_t)(slot+1)'),
                                      ('packet_mode','out[4]=mode','out[4]=(uint8_t)!mode')]:
                mutated=compile_to(src.read_text().replace(before,after),'mutant_'+name)
                caught=0
                for slot,mode,want in packet_corpus:
                    mutated.mu_repair_request(packet,slot,mode);caught+=packet.raw!=want
                assert caught,(name,'undetected mutation');mutations[name]=caught
        report={'comparisons' :sum(counts.values()),'counts':counts,'mismatches':0,'mutations':mutations,
                'text_sha256':TEXT_SHA,'data_sha256':DATA_SHA,
                'limitations':['Stable record lookups; notification/string/transport boundaries modelled.',
                                'Repair-all and single-item request branches execute; grid lookup and window flags are modelled, slot offset executes.',
                                'Native UI transactions and server answers are authored demo policy.']}
        print(json.dumps(report,indent=2))
        if a.report:a.report.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
