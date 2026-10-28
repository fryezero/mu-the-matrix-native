#!/usr/bin/env python3
"""Compare bounded combat record bodies and pre-transform request bytes with pinned instructions.
No client decode, keyed AddData or send wrap is executed. Engine and UI services are stubs.
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
import validate_players as vp
import pins
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'native/session/domains/combat_wire.c'
class Damage(C.Structure):
    _fields_=[('key',C.c_uint16),('shock',C.c_uint8),('type',C.c_uint8),('flags',C.c_uint8*8),('amount',C.c_int32),('shield',C.c_int32)]
def lib(path):
    l=C.CDLL(str(path));B=C.POINTER(C.c_uint8)
    l.mu_combat_damage_body.argtypes=[B,C.c_size_t,B,B,C.c_uint16,C.POINTER(Damage)]
    l.mu_combat_die_body.argtypes=[B,C.c_size_t,B]
    l.mu_combat_action_body.argtypes=[B,C.c_size_t,B,C.c_int16,C.c_int,C.c_float]
    l.mu_combat_attack_request.argtypes=[B,C.c_uint16,C.c_uint8,C.c_int]
    l.mu_combat_cast_request.argtypes=[B,C.c_uint8,C.c_uint8,C.c_uint8,C.c_int]
    l.mu_combat_move_request.argtypes=[B,C.c_uint16,B,B,C.c_uint8,C.c_uint8,C.c_uint8,C.c_float,C.c_int,C.POINTER(C.c_int32)]
    return l

def buf(b):return (C.c_uint8*len(b)).from_buffer_copy(b)
def build(src,out):subprocess.run(['cc','-shared','-fPIC','-O2','-ffp-contract=off','-I',str(SRC.parent),str(src),'-o',str(out)],check=True,capture_output=True)
class Machine:
    def __init__(self,t,d):
        self.cl=vp.Client(t,d);self.m=self.cl.m
        self.m.allow((0x191c5a0,0x191c5e0),(0x1224455,0x1224b62),(0x1234585,0x1234c08),(0x1222b6d,0x1222cba),
                     (0x1222e9b,0x1222f45),(0x1222f53,0x1222f89),(0x122373b,0x122374d),
                     (0x16b6214,0x16b6361),(0x16b6361,0x16b6602),(0x16b5cd0,0x16b617f))
        self.m.stubs.pop(0x16b5cd0, None)
        self.packet=[];self.sends=[];self.shock=[];self.infos=[]
        # All called services are answered independently from synthetic cases.
        self.cl.stub(0x137c724,lambda m:self.target if m.args(1)[0]==self.target_key else 0xffff)
        self.cl.stub(0x95f6db,lambda m:0)
        self.cl.stub(0x9a13f4,lambda m:self.char if m.args(1)[0]==self.target else 0)
        for a in [0x1989721,0x9dacb8,0x9dacec,0xd03d0c,0x1295ade,0xcd6017,0xfdc2d4,0xdb747f,0x129debb,0xaca4bc]:
            self.cl.stub(a,lambda m:0)
        for a in [0xd038db,0x9c104e,0xcd4ea8,0x106ba49,0x9fd699,0xc6b292,0x9617c6,0x94997e,0x94f183,0xd51b91,0xd51ba6]:
            self.cl.stub(a,lambda m:0)
        self.cl.stub(0x194cd00,lambda m:m.write(m.args(3)[0],bytes([m.args(3)[1]&255])*m.args(3)[2]) or m.args(3)[0])
        self.cl.stub(0x138f92f,lambda m:self.shock.append(m.args(3)) or 0)
        self.cl.stub(0x1392bde,lambda m:0)
        self.cl.stub(0x1691738,lambda m:0)
        self.cl.stub(0xa02e4c,lambda m:m.write(self.ecx(),bytes(16)) or 0)
        self.cl.stub(0xa01a25,lambda m:self.infos.append(m.read(m.args(5)[4],16)) or 0)
        for a in [0xa019be,0xa021e0,0x16912ae]:self.cl.stub(a,lambda m:0)
        # Use flag8, avoiding x87 scale getter; scale family already verified separately.
        self.cl.stub(0x95c50b,lambda m:m.write(m.args(1)[0],bytes(8)) or 0)
        self.cl.stub(0x95f659,lambda m:self.manager)
        self.cl.stub(0xac3bf7,lambda m:self.manager)
        self.cl.stub(0xc08654,lambda m:1)
        self.cl.stub(0xc086e8,lambda m:self.skill)
        self.cl.stub(0xc08645,lambda m:0)
        self.cl.stub(0xc08687,lambda m:self.kind)
        self.cl.stub(0xd51baf,self.begin)
        self.cl.stub(0xd51c9b,self.add)
        self.cl.stub(0xd51d4f,lambda m:self.sends.append((bytes(self.packet),m.args(2))) or 0)
    def ecx(self):return self.m.uc.reg_read(vp.cm.UC_X86_REG_ECX)
    def begin(self,m):
        head,op=m.args(2);self.packet[:]=[head,0,op];return 0
    def add(self,m):
        ptr,n,encode=m.args(3)
        assert encode==1
        self.packet.extend(m.read(ptr,n));return self.ecx()
    def reset(self):
        self.cl.reset();m=self.m;self.target=7;self.target_key=0x400
        self.char=m.alloc(0x3700,define=True);m.write(self.char,bytes(0x3700));self.manager=m.alloc(0x500,define=True)
        self.attr=m.alloc(0x1000,define=True);m.write(self.attr,bytes(0x1000));m.put32(0x1d1df1c,self.attr)
        m.put32(0x1d1df18,self.manager);m.put32(0xa39d754,self.char+0x4000);m.put32(0x6fca288,0x7777)
        m.put32(0x1cf15fc,0);self.packet.clear();self.sends.clear();self.shock.clear();self.infos.clear()
        self.skill=17;self.kind=0
    def call(self,a,b):
        p=self.m.alloc(len(b),define=True);self.m.write(p,b);self.m.call(a,[p]);return p

def run(t,d,l,n):
    machine=Machine(t,d);m=machine.m;rng=random.Random(20261028);counts={}
    for family in ['damage','die','action','attack','cast','move']:
        for i in range(n):
            machine.reset();c=buf(bytes(0x3700));a=buf(bytes(0x1000));out=buf(bytes(16))
            if family=='damage':
                p=bytearray(24);p[:5]=bytes([0xc1,24,0x15,0x84 if i%2 else 4,0]);p[13]=0x80|((i*17)%128);p[12]=i%8;p[16]=i%3
                damage=rng.randrange(0,100000);shield=rng.randrange(0,10000)
                if i%3==0:
                    m.put32(0x6fca288,0x400)
                    hp,sd=rng.randrange(100000),rng.randrange(10000)
                    m.put32(machine.attr+0x68,hp);m.put32(machine.attr+0x78,sd)
                    struct.pack_into('<i',a,0x68,hp);struct.pack_into('<i',a,0x78,sd)
                struct.pack_into('<i',p,8,damage);struct.pack_into('<i',p,20,shield)
                machine.call(0x1224455,p);info=Damage();assert l.mu_combat_damage_body(buf(p),len(p),c,a,0x400 if i%3==0 else 0x7777,C.byref(info))
                assert m.read(machine.char+0x14a,2)==bytes(c)[0x14a:0x14c]
                assert info.key==0x400 and info.amount==damage and info.type==(p[13]&15)
                assert len(machine.shock)==i%2
                assert m.read(machine.attr+0x68,4)==bytes(a)[0x68:0x6c]
                assert m.read(machine.attr+0x78,4)==bytes(a)[0x78:0x7c]
                if machine.infos:
                    raw=machine.infos[0];assert struct.unpack_from('<ii',raw)==(info.amount,info.type)
                    assert raw[8:14]==bytes([info.flags[3],info.flags[2],info.flags[4],info.flags[7],info.flags[5],info.flags[6]])
            elif family=='die':
                skill=[0,40,59,392,65535][i%5]
                p=bytearray([0xc1,9,0x17,4,0,skill>>8,skill&255,0,0]);machine.call(0x1234585,p)
                assert l.mu_combat_die_body(buf(p),len(p),c)
                for off,size in [(0x23,1),(0x38,1),(0x2a,1),(0x3230,4),(0x3234,1),(0x325c,1)]:assert m.read(machine.char+off,size)==bytes(c)[off:off+size],(family,i,hex(off))
            elif family=='action':
                x,y=rng.randrange(256),rng.randrange(256)
                m.put32(machine.char+0x180,x);m.put32(machine.char+0x184,y);struct.pack_into('<ii',c,0x180,x,y)
                p=bytes([0xc1,9,0x18,4,0,i%256,0x78+i%2,0xff,0xff]);machine.call(0x1222b6d,p)
                assert l.mu_combat_action_body(buf(p),len(p),c,-1,0,0)
                for off,size in [(0x21,1),(0x38,1),(0x40,2),(0x3324,4),(0x33ac,8),(0x33c0,4)]:assert m.read(machine.char+off,size)==bytes(c)[off:off+size],(family,i,hex(off))
            elif family=='attack':
                key=rng.randrange(65536);direction=i%256
                blocked=i%3==0;machine.cl.stub(0x129debb,lambda m:int(blocked))
                m.call(0x16b6214,[key,direction])
                size=l.mu_combat_attack_request(out,key,direction,blocked)
                if blocked:
                    assert size==0 and not machine.sends
                    continue
                raw,args=machine.sends[0]
                assert size==len(raw) and out[0]==raw[0] and out[1]==size
                assert args==[0,0] and bytes(out)[2:size]==raw[2:]
            elif family=='cast':
                machine.skill=i%256;machine.kind=11 if i%2 else 0
                x,y=rng.randrange(256),rng.randrange(256);p=m.alloc(12,define=True);m.write(p,struct.pack('<fff',x*100,y*100,0));m.call(0x16b6361,[p])
                size=l.mu_combat_cast_request(out,x,y,machine.skill,machine.kind);raw,args=machine.sends[0]
                assert size==len(raw) and out[0]==raw[0] and out[1]==size
                assert args==[1,0] and bytes(out)[2:size]==raw[2:]
            else:
                machine.cl.stub(0x129debb,lambda m:0)
                count=i%16;x=[120];y=[120]
                deltas=[(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]
                for j in range(14):
                    dx,dy=rng.choice(deltas);x.append(x[-1]+dx);y.append(y[-1]+dy)
                m.write(machine.char+0x3196,bytes([count]));m.write(machine.char+0x3197,bytes(x));m.write(machine.char+0x31a6,bytes(y))
                m.put32(0xa39d754,machine.char);m.write(machine.char+0x3e,b'\x01\0');m.put32(0xb449ac0,x[13]+1);m.put32(0xb449ac4,y[13]+1)
                m.put32(0xb477fcc,0);m.putf(machine.char+0x33c0,float(i%360))
                # Direction offsets are data, never a code jump table.
                for k,(dx,dy) in enumerate(deltas):m.write(0x1cf0fc8+k*8,struct.pack('<ii',dx,dy))
                m.call(0x16b5cd0,[machine.char,machine.char+0x3254])
                delay=C.c_int32();size=l.mu_combat_move_request(out,1,buf(bytes(x)),buf(bytes(y)),count,x[13]+1,y[13]+1,float(i%360),0,C.byref(delay))
                assert delay.value==m.u32(0x1cf1148),(i,'delay')
                if count:raw,args=machine.sends[0];assert args==[0,0] and bytes(out)[2:size]==raw[2:],(i,bytes(out)[2:size].hex(),raw.hex())
                else:assert not machine.sends
        counts[family]=n
    return counts

def verify_static_routes(text):
    """Read only the two authorized slots and their selected call sites, never export a table."""
    base=0x401000
    for opcode,block,call,handler in [(0xf3,0x12885f7,0x12885fa,0x1224455),
                                       (0xc5,0x1288613,0x1288619,0x1222b6d)]:
        assert struct.unpack_from('<I',text,0x128e59d+4*opcode-base)[0]==block
        assert text[call-base]==0xe8
        assert call+5+struct.unpack_from('<i',text,call+1-base)[0]==handler


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=300);ap.add_argument('--text',type=Path,default=pins.TEXT.default());ap.add_argument('--data',type=Path,default=pins.DATA.default());ap.add_argument('--output',type=Path);ap.add_argument('--mutants',action='store_true');args=ap.parse_args()
    t=pins.load_pinned(args.text,pins.TEXT.size,pins.TEXT.sha256,'text');d=pins.load_pinned(args.data,pins.DATA.size,pins.DATA.sha256,'data')
    verify_static_routes(t)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'combat.dylib';build(SRC,path);counts=run(t,d,lib(path),args.cases)
        caught=[]
        if args.mutants:
            for j,(name,old,new) in enumerate([('damage_word','c+0x14a','c+0x148'),('die','c[0x23]=1','c[0x23]=0'),('action','c[0x21]=1','c[0x21]=2'),('attack','0x43,','0x44,'),('cast','0xd7,','0xd6,'),('move','out[3]=x[0]','out[3]=y[1]')]):
                source=Path(tmp)/f'mutant{j}.c';source.write_text(SRC.read_text().replace(old,new));target=Path(tmp)/f'mutant{j}.dylib';build(source,target)
                try:run(t,d,lib(target),max(32,args.cases//10))
                except AssertionError:caught.append(name)
                else:raise AssertionError('survived '+name)
        report={'cases':counts,'total':sum(counts.values()),'mismatches':0,'mutants_caught':caught,'text_sha256':hashlib.sha256(t).hexdigest(),'data_sha256':hashlib.sha256(d).hexdigest()}
        if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
if __name__=='__main__':main()
