#!/usr/bin/env python3
"""Execute the pinned client's item/mix rules in Unicorn (NATIVE-MIX-001).

Window visibility, memset, empty-vector clears, readiness in the quote
wrappers, and the packet-builder/transport boundary are modelled. The
ingredient predicates and their helpers execute as captured instructions.
No protection code, live game, encryption or network operations are used.
Synthetic cases deliberately include valid mixes, duplicate ingredients,
leftovers, bounds and every jewel category. --mutations requires all
eleven planted mistakes to be caught.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm
import pins

TEXT_SHA = pins.TEXT.sha256
DATA_SHA = pins.DATA.sha256
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
JEWEL, MATCH, READY, REPEAT, EXTRA = 0xad50b4, 0xd06e3c, 0xd04fc3, 0xd05394, 0xd051b8
FORMULA, RATE, COST, REQUEST = 0xd09bbb, 0xd098da, 0xd099f2, 0x960420

class Target(C.Structure):
    _fields_ = [('code',C.c_int32),('level',C.c_int32),('option',C.c_int32),
                ('kind_a',C.c_uint8),('kind_b',C.c_uint8),('type',C.c_uint8),
                ('durability',C.c_uint8),('period',C.c_uint8)]

class Values(C.Structure):
    _fields_ = [('max_rate',C.c_int32),('first_level',C.c_int32)] + [
        (k,C.c_uint32) for k in ('total','excellent','equipment','ancient','other','first_value','bonus','wing')]

def put(b, at, value):
    struct.pack_into('<I',b,at,value & 0xffffffff)

def native(path):
    lib=C.CDLL(str(path))
    lib.mu_jewel_allowed.argtypes=[C.c_int32,C.POINTER(Target),C.c_int]
    lib.mu_jewel_request.argtypes=[C.c_void_p,C.c_uint8,C.c_uint8,C.c_uint8]
    lib.mu_mix_matches.argtypes=[C.c_void_p,C.c_void_p]
    lib.mu_mix_source_make.argtypes=[C.c_void_p]*3+[C.c_uint32]
    lib.mu_mix_repeats.argtypes=[C.c_void_p,C.c_int32,C.c_void_p]
    lib.mu_mix_ready.argtypes=[C.c_void_p,C.c_int32,C.c_void_p]
    lib.mu_mix_extra.argtypes=[C.c_int32,C.c_void_p]
    lib.mu_mix_formula.argtypes=[C.c_void_p,C.POINTER(Values),C.POINTER(C.c_float),C.POINTER(C.c_int32)]
    lib.mu_mix_rate.argtypes=[C.c_uint32]*5+[C.c_int]*3
    lib.mu_mix_rate.restype=C.c_uint32
    lib.mu_mix_cost.argtypes=[C.c_uint8]+[C.c_uint32]*3
    lib.mu_mix_cost.restype=C.c_uint32
    return lib

class Client:
    def __init__(self,text,data):
        self.m=m=cm.Machine(text,data)
        funcs=[JEWEL,MATCH,READY,REPEAT,0x95c61f,0xd07138,0xd07147,0xd07156,0xd0716b,0xd0717f,0xd07129,
               0x95fc2e,0x987982,0x95fbeb,0xccc591,0xcd0995,0xcd1dfc,0xcd1e65,0xcd1e85,0xcd1ed8,
               FORMULA,0xd09c9b,0xd09d8c,RATE,COST,0xd07528,0xd0746f,0x995231,0xd07c95,0xd07dec,
               0xcd241f,0xcbc2e6,0xcb7192,0xbc87e5,0xbc62ff,0x191c720,REQUEST,0x191c5a0]
        for f in funcs: m.allow((f,cm.function_extent(text,f)))
        m.allow((EXTRA,0xd05364))
        m.stub(0xac3bf7,lambda _:self.manager)
        m.stub(0xa98c22,lambda _:self.window)
        m.stub(0xaae6f9,lambda _:self.visible)
        m.stub(0x194cd00,self.memset)
        # Empty std::vector clears. Harmony-bearing summaries are outside
        # this scalar adapter's accepted domain and are rejected natively.
        m.stub(0xd08c6b,lambda _:0)
        self.visible=0
        self.manager=m.alloc(0x100,True); self.window=m.alloc(0x100,True)
        self.jewel=m.alloc(0x200,True); self.item=m.alloc(0x200,True); self.record=m.alloc(708,True)
        self.sources=m.alloc(3200,True);self.recipe=m.alloc(928,True);self.state=m.alloc(0xd20,True)
        self.index=m.alloc(4,True);self.out=m.alloc(4,True)
        m.put32(0xbdcb280,0)   # CRT's non-FISTTP path executes; no conversion stub.
        # Authored wrapper stores the x87 return. The formula is client code.
        self.wrapper=cm.STUB_BASE+0x90000
        self.vtable=m.alloc(0x100,True);m.put32(self.window,self.vtable)
        lookup=cm.STUB_BASE+0x80000;m.write(lookup,b'\xc3');m.stub(lookup,lambda _:0,4)
        m.put32(self.vtable+0x68,lookup)
        m.stub(0x95f965,lambda _:self.window)
        m.stub(0x16bd791,lambda _:1)  # sender's environment eligibility input
        for f in (0xd51b91,0xd51ba6):m.stub(f,lambda _:0)
        m.stub(0xd51baf,self.begin,8);m.stub(0x95c204,self.add_byte,4);m.stub(0xd51d4f,lambda _:0,8)
        self.packet=[]

    def memset(self,m):
        dst,value,n=m.args(3);m.write(dst,bytes([value&255])*n);return dst

    def begin(self,m):
        header,opcode=m.args(2);self.packet=[header&255,0,opcode&255];return 0

    def add_byte(self,m):
        self.packet.append(m.args(1)[0]&255)
        from unicorn.x86_const import UC_X86_REG_ECX
        return m.uc.reg_read(UC_X86_REG_ECX)

    def request(self,source_slot,target_slot,mode,throttle):
        self.packet=[];m=self.m;m.put32(0x6fca014,throttle);m.write(0xb449b45,bytes([mode]))
        m.call(REQUEST,[source_slot,target_slot])
        if self.packet:self.packet[1]=len(self.packet)
        return bytes(self.packet),m.u32(0x6fca014)

    def jewel_case(self,j,t,visible):
        m=self.m
        item=bytearray(0x200);record=bytearray(708);source=bytearray(0x200)
        put(item,0,self.record);put(item,0x10,t.code);put(item,0x14,(t.level<<3)|(t.option&3))
        item[0x3a]=(t.option&4)<<4;item[0x38]=t.durability;item[0x92]=t.period
        record[0x250:0x253]=bytes([t.kind_a,t.kind_b,t.type]);put(source,0x10,j)
        m.write(self.item,item);m.write(self.record,record);m.write(self.jewel,source);self.visible=visible
        return m.call(JEWEL,[self.jewel,self.item],ecx=self.manager)&255

    def source_case(self,it,record,value):
        m=self.m;item=bytearray(it);put(item,0,self.record)
        m.write(self.item,item);m.write(self.record,record);m.write(self.sources,bytes(100))
        m.call(0xd07528,[self.item,value,0xffffffff],ecx=self.sources)
        return m.read(self.sources,0x4c)

    def rule(self,address,s,r,n=1,k=0):
        m=self.m;m.write(self.sources,s);m.write(self.recipe,r)
        args={MATCH:[self.recipe],READY:[self.sources,n,self.recipe],REPEAT:[self.sources,n,self.recipe],
              EXTRA:[k,self.recipe]}[address]
        result=m.call(address,args,ecx=self.sources)
        if address!=REPEAT: result &=255
        return result,m.read(self.sources,len(s))

    def formula(self,r,v):
        m=self.m;m.write(self.recipe,r);m.put32(self.index,0)
        state=bytearray(0xd20)
        for at,x in ((0xcc4,v.total),(0xcc8,v.excellent),(0xccc,v.equipment),(0xcd0,v.wing),
                     (0xcd4,v.ancient),(0xcd8,v.other),(0xcdc,v.bonus),(0xce4,v.first_value),(0xce8,v.first_level)):
            put(state,at,x)
        m.write(self.state,state)
        # Push the three arguments in the authored wrapper, then execute original code.
        w=b'\x68'+struct.pack('<I',self.index)+b'\x68'+struct.pack('<I',self.recipe+0x48)+b'\x68'+struct.pack('<I',self.recipe)
        callat=self.wrapper+len(w)
        w+=b'\xe8'+struct.pack('<i',FORMULA-callat-5)+b'\xd9\x1d'+struct.pack('<I',self.out)+b'\xc3'
        m.write(self.wrapper,w);m.call(self.wrapper,ecx=self.state)
        return m.read(self.out,4),m.u32(self.index)

    def quote(self,r,state):
        m=self.m;m.write(self.recipe,r);m.write(self.state,state)
        # Readiness has its own instruction comparison; the expression and
        # CRT integer conversion execute as client code here.
        m.stub(READY,lambda _:1)
        m.call(RATE,[self.recipe],ecx=self.state)
        rate=m.u32(self.state+0xca4)
        m.call(COST,[self.recipe],ecx=self.state)
        return rate,m.u32(self.state+0xca8)

def condition(code=1,minimum=1,maximum=1):
    c=bytearray(72);struct.pack_into('<hh',c,0,code,code)
    for at in (0x1c,0x24,0x2c,0x34):put(c,at+4,255)
    put(c,0x3c,minimum);put(c,0x40,maximum);return c

def source(code=1,count=1,kind=0):
    s=bytearray(100);put(s,0,code);put(s,0x20,count);put(s,0x48,kind);return s

def recipe(cs):
    r=bytearray(928);r[0x15b]=1;put(r,0x39c,len(cs))
    for j,c in enumerate(cs):r[0x15c+j*72:0x1a4+j*72]=c
    return r

def run(client,lib,cases):
    rng=random.Random(0x4d4958);counts={};observations=[]
    def check(family,got,want,obs):
        counts[family]=counts.get(family,0)+1
        if got!=want:raise AssertionError(f'{family} case {counts[family]}: client {got!r}, native {want!r}')
        observations.append((family,obs,got))
    for k in range(cases+1024):
        it=bytearray(300);record=bytearray(708)
        put(it,0x10,rng.choice([1,0x406,0x1c35,0x1c60,0x1cbd,0x1cbe,0x2610,0x1a25,0x289d]))
        put(it,0x14,rng.randrange(128));it[0x38]=rng.randrange(256);it[0x3b]=rng.randrange(4);it[0x98]=rng.randrange(3)
        it[0x3a]=rng.randrange(256);it[0x72]=rng.randrange(256);put(it,0x120,rng.randrange(200))
        record[0x250:0x253]=bytes([rng.choice([1,3,6,9,0x1d,0x17,0x20,0x39,0x3a,0x2d,0x2e,0x2f,0x30,0x31,0x38]),
                                         rng.choice([0,0x15,0x67,0x7a,0x38,0x3a,0x5c,0x17,0x18,0x4c,0x6a,0x2b,0x4d]),rng.randrange(9)])
        # Exhaustive byte kinds under plain/socket and plain/archangel
        # states. In particular 0x37 is equipment, not compound equipment.
        if k<512:record[0x250:0x253]=bytes([k%256,0,0 if k<256 else 3]);it[0x3b]=1
        elif k<1024:record[0x250:0x253]=bytes([1,(k-512)%256,0 if k<768 else 6]);it[0x3b]=1
        record[0x2af]=rng.randrange(5)
        for j in range(16):record[0x291+j]=rng.randrange(4)
        it[0x3d]=rng.randrange(9)
        for j in range(it[0x3d]):struct.pack_into('<H',it,0x3e+j*2,rng.randrange(9));struct.pack_into('<H',it,0x4e+j*2,rng.randrange(30))
        value=rng.randrange(1000000);got=client.source_case(bytes(it),bytes(record),value)
        out=C.create_string_buffer(100)
        if not lib.mu_mix_source_make(out,bytes(it),bytes(record),value):raise AssertionError('source rejected')
        check('source',got,out.raw[:0x4c],(bytes(it),bytes(record),value))
    for k in range(cases*4+48):
        t=Target(rng.choice([0,0x29,0x1b0c,0x1800,0x2c00,-1,0x2c01]),rng.randrange(16),rng.randrange(8),
                 rng.choice([1,3,6,0x19,0xe,0xf,0x12,0x1b,0x21,0x37,0x2d,0x2e,0x38,0]),
                 rng.choice([0,0xa,0xb,0x2c,0x2b]),rng.choice([0,2,4,5]),rng.choice([0,1,254,255]),rng.choice([0,0,0,1,2]))
        j=rng.choice([0x1c0d,0x1c0e,0x1c10,0x1c0f]);v=rng.randrange(2)
        if k<48:t=Target(1,k%16,0,1,0,0,100,0);j=[0x1c0d,0x1c0e,0x1c10][k//16];v=0
        check('jewel',client.jewel_case(j,t,v),lib.mu_jewel_allowed(j,C.byref(t),v),(j,bytes(t),v))
    for k in range(cases):
        source_slot=rng.randrange(256);target_slot=rng.randrange(256);mode=rng.randrange(256);throttle=rng.choice([0,0,1,10])
        got=client.request(source_slot,target_slot,mode,throttle)
        out=C.create_string_buffer(6);lib.mu_jewel_request(out,(source_slot+12)&255,target_slot,mode)
        want=(out.raw,10) if throttle==0 else (b'',throttle)
        check('request',got,want,(source_slot,target_slot,mode,throttle))
    for k in range(cases):
        c=condition(rng.randrange(20));s=source(struct.unpack_from('<h',c)[0])
        for at in (4,8,0xc,0x10,0x14,0x18,0x1c):put(s,at,rng.randrange(16))
        for at in (0x1c,0x24,0x2c,0x34):
            off={0x1c:0x10,0x24:0x14,0x2c:0x18,0x34:0x1c}[at];val=struct.unpack_from('<i',s,off)[0]
            if rng.randrange(2):put(c,at,max(0,val-rng.randrange(3)));put(c,at+4,val+rng.randrange(3))
        if k%4==0:put(c,0x2c,0);put(c,0x30,255)
        flags=rng.randrange(256);put(s,0x2c,flags);put(c,0x44,flags if k%2 else rng.randrange(256))
        if k==0:
            c=condition(1);s=source(1);put(c,0x44,0x80)
        if k%3==0:put(c,0xc,struct.unpack_from('<I',s,8)[0]);put(c,0x10,struct.unpack_from('<I',s,8)[0])
        if k%3==1:put(c,0x14,struct.unpack_from('<I',s,0xc)[0]);put(c,0x18,struct.unpack_from('<I',s,0xc)[0])
        if k%5==0:put(c,4,struct.unpack_from('<I',s,4)[0]);put(c,8,struct.unpack_from('<I',s,4)[0])
        got,_=client.rule(MATCH,bytes(s),bytes(c));check('match',got,lib.mu_mix_matches(bytes(s),bytes(c)),(bytes(s),bytes(c)))
    for k in range(cases):
        n=rng.randrange(1,8);cs=[condition(j+1,1,rng.randrange(1,5)) for j in range(rng.randrange(1,5))]
        r=recipe(cs);r[0x15b]=rng.choice([1,2,4]);r[0x14d:0x152]=bytes(rng.choice([65,85]) for _ in range(5))
        s=b''.join(source(rng.randrange(1,len(cs)+2),rng.randrange(1,4),rng.randrange(4)) for _ in range(n))
        if k%4==0:s=b''.join(source(j+1) for j in range(len(cs)));n=len(cs)
        rep,_=client.rule(REPEAT,s,bytes(r),n);check('repeat',rep,lib.mu_mix_repeats(s,n,bytes(r)),(s,n,bytes(r)))
        got,after=client.rule(READY,s,bytes(r),n);buf=C.create_string_buffer(s)
        want=lib.mu_mix_ready(buf,n,bytes(r));check('ready',(got,after),(want,buf.raw[:len(s)]),(s,n,bytes(r)))
        kind=rng.randrange(14);got,_=client.rule(EXTRA,s,bytes(r),n,kind)
        check('extra',got,lib.mu_mix_extra(kind,bytes(r)),(kind,bytes(r)))
    # Every selector gets an accepting case and neighboring rejections.
    for kind in range(14):
        for flag in (64,65,66):
            for special in (0x14,0x15,0x16,0x66,0x67,0x68,0x79,0x7a,0x7b):
                r=recipe([]);r[0x14d:0x152]=bytes([flag])*5;r[0x158:0x15b]=bytes([flag])*3;put(r,0x154,special)
                got,_=client.rule(EXTRA,bytes(source()),bytes(r),1,kind)
                check('extra',got,lib.mu_mix_extra(kind,bytes(r)),(kind,bytes(r)))
    for k in range(cases):
        v=Values(rng.randrange(101),rng.randrange(16),*[rng.choice([0x80000000,0xffffffff,rng.randrange(0x10000000)]) for _ in range(8)])
        r=bytearray(928);put(r,0x148,v.max_rate)
        # A precedence / grouping expression, with every variable token exercised.
        types=[0,0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x40]
        tok=[(5,0),(rng.choice(types),rng.randrange(100)),(rng.choice([1,2]),0),(0,rng.randrange(100)),(6,0),
             (rng.choice([3,4]),0),(0,rng.randrange(1,5)),(1,0),(0,rng.randrange(100))]
        if k%3==0:tok=[(7,0),(5,0)]+tok+[(6,0)]
        if k<8:tok=[(7,0),(5,0),(0,[-2147483904.,-2147483648.,-1.5,1.5,2147483520.,2147483648.,4294967296.,1e30][k]),(6,0)]
        put(r,0x44,len(tok))
        for j,(t,x) in enumerate(tok):put(r,0x48+j*8,t);struct.pack_into('<f',r,0x4c+j*8,x)
        got=client.formula(bytes(r),v);out=C.c_float();at=C.c_int32()
        if not lib.mu_mix_formula(bytes(r),C.byref(v),C.byref(out),C.byref(at)):raise AssertionError('formula rejected')
        check('formula',got,(struct.pack('<f',out.value),at.value),(bytes(r),bytes(v)))
    for k in range(cases):
        r=recipe([condition()]);state=bytearray(0xd20)
        integer=rng.randrange(400);cap=rng.randrange(101);bless=rng.randrange(20);life=rng.randrange(30);charm=rng.randrange(2)
        flags=[rng.randrange(2) for _ in range(3)];costtype=rng.choice(b'ABC');base=rng.randrange(0x10000000);reps=rng.randrange(1,50)
        put(r,0x44,1);struct.pack_into('<If',r,0x48,0,integer);put(r,0x148,cap)
        r[0x14d]=65 if flags[0] else 85;r[0x14f]=65 if flags[1] else 85;r[0x151]=65 if flags[2] else 85
        r[0x3c]=costtype;put(r,0x40,base)
        for at,x in ((0xcac,bless),(0xcb0,life),(0xcbc,charm),(0xc94,reps)):put(state,at,x)
        got=client.quote(bytes(r),bytes(state))
        rate=lib.mu_mix_rate(integer,cap,bless,life,charm,*flags)
        cost=lib.mu_mix_cost(costtype,base,reps,rate)
        check('quote',got,(rate,cost),(integer,cap,bless,life,charm,*flags,costtype,base,reps))
    return counts,observations

def installed(client,lib,game_root):
    """Use every installed recipe on synthetic summaries, without exports."""
    import validate_data_tables as tables
    path=next(p for p in (game_root/'Data/Local').iterdir() if p.name.lower()=='mix.bmd')
    data=path.read_bytes()
    def decode(b):return bytes(x^tables.KEY3[j%3] for j,x in enumerate(b))
    groups=struct.unpack('<22i',decode(data[:88]));at=88;counts={'installed_match':0,'installed_ready':0,'installed_repeat':0}
    # The synthetic run replaces this entry only for wrapper tests.
    client.m.stubs.pop(READY,None)
    for group,count in enumerate(groups):
        if count<0 or count>3000:raise ValueError('installed recipe count outside client domain')
        for index in range(count):
            r=decode(data[at:at+928]);at+=928
            if len(r)!=928:raise ValueError('truncated installed recipe')
            n=struct.unpack_from('<i',r,0x39c)[0]
            if n<0 or n>8:raise ValueError('installed conditions exceed native domain')
            sources=[]
            for j in range(n):
                c=r[0x15c+j*72:0x1a4+j*72];s=source(struct.unpack_from('<h',c)[0],max(1,struct.unpack_from('<i',c,0x3c)[0]))
                for src,cond in ((4,4),(8,0xc),(0xc,0x14),(0x10,0x1c),(0x14,0x24),(0x18,0x2c),(0x1c,0x34),(0x2c,0x44)):
                    put(s,src,struct.unpack_from('<i',c,cond)[0])
                got,_=client.rule(MATCH,bytes(s),c)
                if got!=lib.mu_mix_matches(bytes(s),c):raise AssertionError(f'installed match {group}/{index}/{j}')
                counts['installed_match']+=1;sources.append(s)
            for present in (sources,sources[:-1]):
                s=b''.join(present);num=len(present)
                got,_=client.rule(REPEAT,s,r,num)
                if got!=lib.mu_mix_repeats(s,num,r):raise AssertionError(f'installed repeat {group}/{index}')
                counts['installed_repeat']+=1
                # A nonnull pointer with count 0 follows the client's no-items gate.
                got,after=client.rule(READY,s,r,num);buf=C.create_string_buffer(s)
                want=lib.mu_mix_ready(buf,num,r)
                if (got,after)!=(want,buf.raw[:len(s)]):raise AssertionError(f'installed readiness {group}/{index}')
                counts['installed_ready']+=1
    return counts,{'sha256':hashlib.sha256(data).hexdigest(),'recipes':sum(groups)}

def mutation(lib,observations):
    found=0
    for family,args,want in observations:
        if family=='source':
            it,r,v=args;out=C.create_string_buffer(100);lib.mu_mix_source_make(out,it,r,v);got=out.raw[:0x4c]
        elif family=='jewel':
            j,t,v=args;got=lib.mu_jewel_allowed(j,C.byref(Target.from_buffer_copy(t)),v)
        elif family=='request':
            src,dst,mode,throttle=args;out=C.create_string_buffer(6);lib.mu_jewel_request(out,(src+12)&255,dst,mode)
            got=(out.raw,10) if throttle==0 else (b'',throttle)
        elif family=='match':got=lib.mu_mix_matches(*args)
        elif family=='extra':got=lib.mu_mix_extra(*args)
        elif family=='formula':
            r,v=args;out=C.c_float();at=C.c_int32()
            if not lib.mu_mix_formula(r,C.byref(Values.from_buffer_copy(v)),C.byref(out),C.byref(at)):got=None
            else:got=(struct.pack('<f',out.value),at.value)
        elif family=='ready':
            s,n,r=args;buf=C.create_string_buffer(s);x=lib.mu_mix_ready(buf,n,r);got=(x,buf.raw[:len(s)])
        elif family=='quote':
            x,cap,b,l,c,ab,al,sc,t,base,repeat=args
            rate=lib.mu_mix_rate(x,cap,b,l,c,ab,al,sc);got=(rate,lib.mu_mix_cost(t,base,repeat,rate))
        else:continue
        found+=got!=want
    return found

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--text',type=Path,default=pins.TEXT.default())
    ap.add_argument('--data',type=Path,default=pins.DATA.default())
    ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output',type=Path)
    ap.add_argument('--game-root',type=Path,default=os.environ.get('MU_GAME_ROOT'))
    args=ap.parse_args()
    text=pins.TEXT.read(args.text,mismatch=ValueError('private input digest mismatch'))
    data=pins.DATA.read(args.data,mismatch=ValueError('private input digest mismatch'))
    subprocess.run(['make','-C',str(ROOT/'reconstructed/mix')],check=True,capture_output=True)
    lib=native(ROOT/f'reconstructed/mix/libmix.{SUFFIX}');client=Client(text,data)
    counts,observations=run(client,lib,args.cases)
    report={'cases':counts,'total':sum(counts.values()),'mismatches':0,'inputs':{'text':TEXT_SHA,'data':DATA_SHA},'mutations':{}}
    if args.game_root:
        more,identity=installed(client,lib,args.game_root);report['cases'].update(more);report['inputs']['mix']=identity
        report['total']=sum(report['cases'].values())
    if args.mutations:
        with tempfile.TemporaryDirectory() as tmp:
            for n in range(1,12):
                path=Path(tmp)/f'mutant{n}.{SUFFIX}'
                subprocess.run(['clang','-std=c11','-O2','-ffp-contract=off','-fno-fast-math','-shared','-fPIC',
                                f'-DMU_MIX_MUTANT={n}',str(ROOT/'reconstructed/mix/item_actions.c'),
                                str(ROOT/'reconstructed/mix/mix_rules.c'),str(ROOT/'reconstructed/mix/mix_source.c'),'-lm','-o',str(path)],check=True)
                got=mutation(native(path),observations);report['mutations'][str(n)]=got
                if not got:raise AssertionError(f'mutant {n} escaped')
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
