#!/usr/bin/env python3
"""Compare mix selection/filter/score and scalar aggregation with client x86.

Uses validate_mix's pinned inputs and machine. Only STL allocation/copy/
iteration primitives are modelled; selection, filtering and score execute.
No live client, network, game data export or protection module is used.
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

from validate_mix import ROOT, SUFFIX, TEXT_SHA, DATA_SHA, Client, Values, native, put, source, condition, recipe
import client_ui_machine as cm
import pins
from unicorn.x86_const import UC_X86_REG_ECX


def bind(path):
    lib = native(path)
    lib.mu_mix_select.argtypes = [C.c_void_p, C.c_int32, C.c_void_p, C.c_int32, C.c_int]
    lib.mu_mix_score.argtypes = [C.c_void_p, C.c_int32, C.c_void_p]
    lib.mu_mix_values_make.argtypes = [C.POINTER(Values), C.c_void_p, C.c_int32]
    lib.mu_mix_same.argtypes = [C.c_void_p, C.c_void_p]
    lib.mu_mix_first_values.argtypes = [C.POINTER(Values), C.c_void_p, C.c_int32, C.c_void_p]
    lib.mu_mix_additions_make.argtypes = [C.c_void_p,C.c_void_p,C.c_int32,C.c_void_p]
    lib.mu_mix_group_add.argtypes = [C.c_void_p,C.c_int,C.c_void_p,C.c_uint32,C.c_uint8]
    lib.mu_mix_value.argtypes=[C.c_int32,C.c_uint32];lib.mu_mix_value.restype=C.c_uint32
    return lib


class Manager(Client):
    def __init__(self, text, data):
        super().__init__(text, data)
        m = self.m
        for f in (0xd0b2c6, 0xd0b5d7, 0xd0c374, 0xd0cf7e, 0xd08440, 0xd0d016,
                  0xd0d03c, 0xd0d04c, 0xd0a4f4, 0xd0a48c, 0xd0a4e6, 0xd096f0,
                  0xd09811, 0xd0847c, 0xd08a1d, 0xd0a4d7, 0xd0a47c, 0xd0a318,
                  0xd0960d, 0xd0a4b9, 0xd0a4c8, 0xd09366, 0xd09ba4,
                  0xd08e38,0xd07356,0xd0744f,0xd0a3c7,0xd0a462,0xd0a448,0xd07b21,0xd07e3f):
            m.allow((f, cm.function_extent(text, f)))
        self.rows = m.alloc(928*3000, True)
        self.vector = m.alloc(12, True)
        self.buffers = {}
        def ecx(): return m.uc.reg_read(UC_X86_REG_ECX)
        def values(obj):
            first, last = m.u32(obj), m.u32(obj+4)
            return [m.u32(p) for p in range(first, last, 4)]
        def assign(obj, vals):
            if obj not in self.buffers: self.buffers[obj] = m.alloc(3000*4, True)
            p = self.buffers[obj]
            for k, v in enumerate(vals): m.put32(p+k*4, v)
            m.put32(obj, p); m.put32(obj+4, p+len(vals)*4); m.put32(obj+8, p+12000)
            return obj
        self.assign = assign
        m.stub(0xd0d516, lambda _: len(values(ecx())))
        m.stub(0xd0cfad, lambda _: m.u32(ecx()) + m.args(1)[0]*4, 4)
        m.stub(0xd0ce10, lambda _: assign(ecx(), values(m.args(1)[0])), 4)
        m.stub(0xd0b129, lambda _: assign(ecx(), []))
        m.stub(0xd0cd78, lambda _: assign(ecx(), values(m.args(1)[0])), 4)
        m.stub(0xd0cebe, lambda _: assign(ecx(), values(m.args(1)[0])), 4)
        m.stub(0xd0ceac, lambda _: 0)
        m.stub(0xd0d4f7, lambda _: assign(ecx(), values(ecx())+[m.u32(m.args(1)[0])]), 4)
        def iterator(end):
            obj, out = ecx(), m.args(1)[0]
            m.put32(out, m.u32(obj+(4 if end else 0)))
            return out
        for f in (0xd0d370, 0xd0d39c): m.stub(f, lambda _: iterator(False), 4)
        for f in (0xd0d45d, 0xd0d48a): m.stub(f, lambda _: iterator(True), 4)
        m.stub(0xd0cf4f, lambda _: int(m.u32(ecx()) != m.u32(m.args(1)[0])), 4)
        m.stub(0xd0cfca, lambda _: m.u32(ecx()))
        def advance(_):
            obj=ecx(); m.put32(obj, m.u32(obj)+4); return obj
        m.stub(0xd0cfe9, advance)
        self.lookup={}
        m.stub(0xcd4ea8,lambda _:m.args(1)[0])
        m.stub(0xcd5d29,lambda _:self.lookup.get(ecx(),0))
        m.stub(0xd07e3f,lambda _:self.group_value)
        def empty(_):
            m.write(ecx(),bytes(12));return ecx()
        m.stub(0xd083d5,empty);m.stub(0xd0841e,lambda _:0)
        m.stub(0x169320b,lambda _:self.buy_value)

    def select(self, sources, rows, force):
        m=self.m
        m.write(self.sources, sources); m.write(self.rows, rows)
        self.assign(self.vector, [self.rows+j*928 for j in range(len(rows)//928)])
        m.write(self.manager, bytes(0x100))
        m.write(self.manager+4, m.read(self.vector, 12))
        result=m.call(0xd0b2c6, [self.sources, len(sources)//100, force], ecx=self.manager)
        return C.c_int32(result).value

    def score(self, sources, row):
        m=self.m; m.write(self.sources,sources); m.write(self.rows,row)
        self.assign(self.vector,[self.rows]);m.write(self.manager+4,m.read(self.vector,12))
        result=m.call(0xd0b5d7,[0,self.sources,len(sources)//100],ecx=self.manager)
        return C.c_int32(result).value, m.read(self.sources,len(sources))

    def aggregate(self, sources):
        m=self.m;m.write(self.state,bytes(0xd20));m.write(self.state+8,sources)
        m.put32(self.state+0xc88,len(sources)//100)
        m.call(0xd096f0,ecx=self.state);m.call(0xd09811,[0],ecx=self.state)
        return tuple(m.u32(self.state+at) for at in (0xcc4,0xcc8,0xccc,0xcd4,0xcd8,0xcdc,0xcd0))

    def first(self,sources,row):
        m=self.m;m.write(self.state,bytes(0xd20));m.write(self.state+8,sources)
        m.put32(self.state+0xc88,len(sources)//100);m.write(self.rows,row)
        m.call(0xd0960d,[self.rows],ecx=self.state)
        return m.u32(self.state+0xce4),C.c_int32(m.u32(self.state+0xce8)).value

    def additions(self,sources,levels):
        m=self.m;m.write(self.state,bytes(0xd20));m.write(self.state+8,sources)
        m.put32(self.state+0xc88,len(sources)//100);self.lookup={}
        for k,level in enumerate(levels):
            code=struct.unpack_from('<I',sources,k*100)[0]
            self.lookup[code]=self.record+k*708
            m.write(self.record+k*708,bytes(708));m.write(self.record+k*708+0x254,struct.pack('<H',level))
        m.call(0xd09366,ecx=self.state)
        return tuple(m.u32(self.state+at) for at in (0xcac,0xcb0,0xcbc))

    def group(self,it,record,value,previous):
        m=self.m;raw=bytearray(it);put(raw,0,self.record);m.write(self.item,raw);m.write(self.record,record)
        m.write(self.state,bytes(0xd20));m.put32(self.state+4,0xffffffff)
        m.write(self.state+8,previous);m.put32(self.state+0xc88,len(previous)//100);self.group_value=value
        m.call(0xd08e38,[self.item,0],ecx=self.state)
        n=m.u32(self.state+0xc88)
        return b''.join(m.read(self.state+8+k*100,76)+bytes(24) for k in range(n))

    def value(self,code,buy):
        m=self.m;m.write(self.item,bytes(300));m.put32(self.item+0x10,code);self.buy_value=buy
        stub=m.stubs.pop(0xd07e3f)
        try:return m.call(0xd07e3f,[self.item])
        finally:m.stubs[0xd07e3f]=stub


def run(client,lib,cases):
    rng=random.Random(0x4d495832);counts={};corpus=[]
    def check(family, got, want, args):
        counts[family]=counts.get(family,0)+1
        if got!=want: raise AssertionError(f'{family} {counts[family]}: native {got}, client {want}')
        corpus.append((family,args,want))
    for k in range(cases):
        ss=[]
        for _ in range(rng.randrange(1,7)):
            s=source(rng.choice([1,2,3,0x406,0x180f,0x1994]),rng.randrange(1,5),rng.randrange(0,12))
            put(s,0x10,rng.randrange(0,16));put(s,0x2c,rng.choice([0,1,4,8,0x80]))
            put(s,0x30,rng.getrandbits(32))
            put(s,0x38,rng.randrange(16))
            for at in (0x34,0x3c,0x3d,0x3e,0x3f,0x40):s[at]=rng.randrange(2)
            ss.append(s)
        s=bytes().join(ss);rows=[]
        for j in range(rng.randrange(1,8)):
            cs=[]
            for _ in range(rng.randrange(1,5)):
                c=condition(rng.choice([1,2,3,0x406,0x180f]),rng.randrange(2),rng.randrange(1,6))
                if rng.randrange(2):struct.pack_into('<hh',c,0,1,0x1994)
                put(c,0x44,rng.choice([0,1,4,8,0x80]));cs.append(c)
            r=recipe(cs);put(r,0,j);put(r,4,rng.choice([0,501]));r[0x15b]=rng.randrange(1,4)
            r[0x14c]=rng.choice(b'ABHIJL')
            for at in (0x14d,0x14e,0x14f,0x150,0x151,0x158,0x159,0x15a):r[at]=rng.choice(b'AB')
            put(r,0x154,rng.choice([0,0x15,0x67,0x7a]));rows.append(bytes(r))
        rows=b''.join(rows);force=rng.randrange(2)
        # Every eighth case gives equal-ranked, overlapping candidates.
        if k%8==0:
            r=recipe([condition(1)]);put(r,0,0)
            r2=bytearray(r);put(r2,0,1);rows=bytes(r+r2);s=bytes(source(1))
        check('select',lib.mu_mix_select(C.create_string_buffer(s),len(s)//100,rows,len(rows)//928,force),
              client.select(s,rows,force),(s,rows,force))
        buf=C.create_string_buffer(s);score=lib.mu_mix_score(buf,len(s)//100,rows[:928])
        check('score',(score,buf.raw[:len(s)]),client.score(s,rows[:928]),(s,rows[:928]))
        v=Values();lib.mu_mix_values_make(C.byref(v),s,len(s)//100)
        check('values',tuple(getattr(v,f) for f in ('total','excellent','equipment','ancient','other','bonus','wing')),
              client.aggregate(s),(s,))
        a=ss[0];b=bytearray(a)
        if k%2:b[rng.randrange(0,76)]^=1
        m=client.m;m.write(client.sources,a);m.write(client.sources+100,b)
        want=m.call(0xd0a318,[client.sources+100],ecx=client.sources)&255
        check('same',lib.mu_mix_same(bytes(a),bytes(b)),want,(bytes(a),bytes(b)))
        v=Values();lib.mu_mix_first_values(C.byref(v),s,len(s)//100,rows[:928])
        check('first',(v.first_value,v.first_level),client.first(s,rows[:928]),(s,rows[:928]))
        # Same code means the same record at the lookup boundary.
        by_code={struct.unpack_from('<I',s,at)[0]:rng.randrange(256) for at in range(0,len(s),100)}
        levels=[by_code[struct.unpack_from('<I',s,at)[0]] for at in range(0,len(s),100)]
        add=(C.c_uint32*3)();level_array=(C.c_uint16*len(levels))(*levels)
        lib.mu_mix_additions_make(add,s,len(s)//100,level_array)
        check('additions',tuple(add),client.additions(s,levels),(s,levels))
        it=bytearray(300);rec=bytearray(708)
        put(it,0x10,rng.choice([1,0x1c35,0x406]));put(it,0x14,rng.randrange(16)<<3)
        it[0x38]=rng.randrange(1,10);rec[0x250]=rng.choice([1,0x1d]);rec[0x251]=rng.choice([0,0x38,0x3a,0x5c])
        rec[0x2af]=rng.choice([0,2]);value=rng.getrandbits(24)
        summary=C.create_string_buffer(100);assert lib.mu_mix_source_make(summary,bytes(it),bytes(rec),value)
        previous=summary.raw if k%2 else b'';buf=C.create_string_buffer(previous,3200)
        ns=lib.mu_mix_group_add(buf,len(previous)//100,summary,value,it[0x38])
        check('group',buf.raw[:ns*100],client.group(it,rec,value,previous),(bytes(it),bytes(rec),value,previous))
        code=rng.choice([rng.randrange(-1,0x2c00),0x180f,0x1c0d,0x1c0e,0x1c10,0x1c16,0x1863,0x1994,0x1995,0x1996])
        buy=rng.getrandbits(32)
        check('value',lib.mu_mix_value(code,buy),client.value(code,buy),(code,buy))
    return counts,corpus


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--text',type=Path,default=pins.TEXT.default())
    ap.add_argument('--data',type=Path,default=pins.DATA.default())
    ap.add_argument('--cases',type=int,default=2000);ap.add_argument('--output',type=Path)
    ap.add_argument('--game-root',type=Path)
    ap.add_argument('--mutations',action='store_true');args=ap.parse_args()
    text=pins.TEXT.read(args.text,mismatch=ValueError('input digest mismatch'))
    data=pins.DATA.read(args.data,mismatch=ValueError('input digest mismatch'))
    subprocess.run(['make','-C',str(ROOT/'reconstructed/mix')],check=True,capture_output=True)
    lib=bind(ROOT/f'reconstructed/mix/libmix.{SUFFIX}')
    client=Manager(text,data);counts,corpus=run(client,lib,args.cases)
    report={'cases':counts,'total':sum(counts.values()),'mismatches':0,'mutations':{}}
    if args.game_root:
        image=(args.game_root/'Data/Local/Mix.bmd').read_bytes()
        def decode(b):return bytes(x^(0xfc,0xcf,0xab)[k%3] for k,x in enumerate(b))
        groups=struct.unpack('<22i',decode(image[:88]));at=88;checked=0
        for count in groups:
            rows=b''.join(decode(image[at+j*928:at+(j+1)*928]) for j in range(count));at+=count*928
            if not count:continue
            r=rows[(count//2)*928:(count//2+1)*928];ss=[]
            for j in range(struct.unpack_from('<I',r,0x39c)[0]):
                c=r[0x15c+j*72:0x1a4+j*72]
                s=source(struct.unpack_from('<h',c)[0],max(1,struct.unpack_from('<i',c,0x3c)[0]))
                for src,cond in ((4,4),(8,0xc),(0xc,0x14),(0x10,0x1c),(0x14,0x24),(0x18,0x2c),(0x1c,0x34),(0x2c,0x44)):
                    put(s,src,struct.unpack_from('<I',c,cond)[0])
                ss.append(s)
            s=b''.join(ss)
            got=lib.mu_mix_select(C.create_string_buffer(s),len(ss),rows,count,0)
            want=client.select(s,rows,0)
            if got!=want:raise AssertionError(f'installed selection: {got} != {want}')
            checked+=1
        report['cases']['installed_select']=checked
        report['total']=sum(report['cases'].values())
        report['installed']={'sha256':hashlib.sha256(image).hexdigest(),'candidate_rows':sum(groups)}
    if args.mutations:
        with tempfile.TemporaryDirectory() as tmp:
            for number,family in ((12,'select'),(13,'first'),(14,'additions'),(15,'score'),(16,'group'),(17,'value')):
                path=Path(tmp)/f'mutant{number}.{SUFFIX}'
                subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC',f'-DMU_MIX_MUTANT={number}',
                                *map(str,(ROOT/'reconstructed/mix').glob('*.c')),'-lm','-o',str(path)],check=True)
                mutant=bind(path);caught=0
                for fam,inputs,want in corpus:
                    if fam!=family:continue
                    s=inputs[0];n=len(s)//100 if isinstance(s,bytes) else 0
                    if family=='select':
                        s,rows,force=inputs
                        got=mutant.mu_mix_select(C.create_string_buffer(s),n,rows,len(rows)//928,force)
                    elif family=='first':
                        v=Values();mutant.mu_mix_first_values(C.byref(v),s,n,inputs[1]);got=(v.first_value,v.first_level)
                    elif family=='additions':
                        add=(C.c_uint32*3)();levels=(C.c_uint16*n)(*inputs[1]);mutant.mu_mix_additions_make(add,s,n,levels);got=tuple(add)
                    elif family=='score':
                        buf=C.create_string_buffer(s);v=mutant.mu_mix_score(buf,n,inputs[1]);got=(v,buf.raw[:len(s)])
                    elif family=='value':got=mutant.mu_mix_value(*inputs)
                    else:
                        it,rec,value,previous=inputs;summary=C.create_string_buffer(100)
                        mutant.mu_mix_source_make(summary,it,rec,value);buf=C.create_string_buffer(previous,3200)
                        ns=mutant.mu_mix_group_add(buf,len(previous)//100,summary,value,it[0x38]);got=buf.raw[:ns*100]
                    caught+=got!=want
                if not caught:raise AssertionError(f'mutant {number} escaped')
                report['mutations'][str(number)]=caught
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
