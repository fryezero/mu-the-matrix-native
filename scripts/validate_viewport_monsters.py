#!/usr/bin/env python3
"""Bounded 0x13 handler and extracted CreateMonster record comparisons, VIEWPORT-MONSTER-001."""
import argparse
import ctypes as C
import json
import random
import struct
import subprocess
import tempfile
from pathlib import Path
import validate_players as vp
import validate_actors as actors

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'reconstructed/actors/viewport_monsters.c'
class Viewport(C.Structure):
    _fields_ = [('size',C.c_int32),('key',C.c_uint16),('server_class',C.c_uint16),('level',C.c_uint16),
        ('max_hp',C.c_uint32),('hp',C.c_uint32),('created',C.c_uint8),('special',C.c_uint8),
        ('x',C.c_uint8),('y',C.c_uint8),('target',C.c_uint8*2),('direction',C.c_uint8),('elemental',C.c_uint8),
        ('flag_34',C.c_uint8),('object_43',C.c_uint8),('state',C.c_uint8),('effect',C.c_uint8),('buff_count',C.c_uint8),
        ('words',C.c_uint16*4),('buff_type',C.c_uint16*56),('buff_value',C.c_uint32*56)]
def library(path):
    lib=C.CDLL(str(path)); P=C.POINTER
    lib.mu_monster_viewport_record.argtypes=[C.c_char_p,C.c_int32,P(Viewport)]
    lib.mu_monster_character_create.argtypes=[P(vp.Character),P(Viewport)]
    lib.mu_monster_viewport_apply.argtypes=[P(vp.Character),P(Viewport),P(vp.Env)]
    return lib

def compile_library(source, path):
    subprocess.run(['cc','-shared','-fPIC','-O2','-ffp-contract=off','-I',str(SOURCE.parent),str(source),
        str(ROOT/'native/build/libmunative.a'),'-lm','-o',str(path)],check=True,capture_output=True)

def handler(text,data,lib,n):
    cl=vp.Client(text,data); m=cl.m
    m.allow((0x122c426,0x122d413))
    # Engine/table/effect services are explicit host answers, never original implementations.
    for address,cleanup in [(0x9dacb8,0),(0xd034b0,0),(0x95c652,0),(0xd7b373,0),(0xdb747f,0),
        (0x1219a94,0),(0x95f6db,0),(0x9a16a6,0),(0xa6ac96,0),(0x13c0eaa,0),
        (0x142c7b5,0),(0x13c0e39,0),(0xd5c9d5,0),(0x13bf480,0),(0x13bfa10,0)]: m.stub(address,lambda mm:0,cleanup)
    m.stub(0x10de7a3,lambda mm:mm.args(1)[0]&1,4)
    observed=[]
    m.stub(0x128723b,lambda mm:observed.append((mm.args(4)[0],mm.args(4)[3])) or 0,0)
    def create(mm):
        cls,x,y,key,level=mm.args(5);cl.create_args=(cls,x,y,key,level)
        addr=mm.alloc(0x3700,define=True);mm.write(addr,bytes(0x3700))
        # Fixed model host independent of the class table; creation is compared separately.
        model=cl.model
        for off,fmt,value in [(0x3e,'H',key),(0x146,'H',cls),(0x180,'i',x),(0x184,'i',y),
            (0x32b0,'i',model),(0x33ac,'f',x*100+50),(0x33b0,'f',y*100+50)]:
            mm.write(addr+off,struct.pack('<'+fmt,value))
        cl.char=addr;return addr
    m.stub(0x137fbac,create,0)
    rng=random.Random(20261028)
    models=[0x7ae,0xa01,0x808,0xa3e,0xa57,0xa5c,0xa62,0xa6c,0xa4d]
    for i in range(n):
        cl.reset(world=0x52 if i%3==0 else 0);cl.model=models[i%len(models)];observed.clear()
        b=bytearray(rng.randbytes(28+56*8));b[26]=i%57;b[9]=b[15]=0
        # Include special tile overrides and both successful and failed path placements.
        if i%9==2: b[4]=[62,183,1][i%3];b[5]=90
        cl.path_answers=[i%3==1,i%3==2]
        v=Viewport();assert lib.mu_monster_viewport_record(bytes(b),len(b),C.byref(v))==28+8*b[26]
        c=vp.Character();c.model=cl.model;c.tile[:]=[v.x,v.y];c.position[:]=[v.x*100+50,v.y*100+50,0]
        env=vp.Env();env.world=0x52 if i%3==0 else 0;answers=iter(cl.path_answers)
        callback=vp.PATHFN(lambda *args:int(next(answers,False)));env.path_finding2=callback
        lib.mu_monster_viewport_apply(C.byref(c),C.byref(v),C.byref(env))
        packet=bytes([0xc2,0,(5+v.size)&255,0x13,1])+b[:v.size]
        a=m.alloc(len(packet),define=True);m.write(a,packet);m.call(0x122c426,[a])
        assert cl.create_args==(v.server_class,v.x,v.y,v.key,v.level),(i,'create args',cl.create_args)
        for off,fmt,value in [(0x14e,'H',c.level),(0x150,'I',c.max_hp),(0x154,'I',c.hp),
            (0x180,'i',c.tile[0]),(0x184,'i',c.tile[1]),(0x2d,'B',c.target[0]),(0x2e,'B',c.target[1]),
            (0x33c0,'f',c.angle[2]),(0x3297,'B',c.byte_43),(0x38,'B',c.movement),
            (0x33ac,'f',c.position[0]),(0x33b0,'f',c.position[1]),(0x34,'B',v.flag_34)]:
            assert m.read(cl.char+off,struct.calcsize('<'+fmt))==struct.pack('<'+fmt,value),(i,hex(off),value)
        assert observed==[(v.buff_type[k],v.buff_value[k] if v.buff_type[k]&1 else 0) for k in range(v.buff_count)],(i,'buff')
        assert m.read(cl.char+0x3274,8)==struct.pack('<4H',*v.words),(i,'words')
        for short in (0,27,v.size-1): assert lib.mu_monster_viewport_record(bytes(b),short,C.byref(Viewport()))==0
    return n

def creation(text,data,lib,limit=None):
    machine=actors.am.ActorMachine(text,data);count=0;unavailable=[]
    for cls in range(1024 if limit is None else limit):
        original=actors.extract_class(machine,cls)
        if 'error' in original or original.get('model') is None: unavailable.append(cls);continue
        v=Viewport();v.key=1000+cls;v.server_class=cls;v.x=10;v.y=20
        c=vp.Character()
        if not lib.mu_monster_character_create(C.byref(c),C.byref(v)): continue
        assert c.model==original['model'],(cls,'model',c.model,original['model'])
        assert c.key==v.key and c.class_word==cls and list(c.tile)==[10,20],(cls,'identity')
        assert c.class_byte==original['class_byte'],(cls,'class byte')
        for k,(type_,level) in enumerate(original['slots']):
            if type_: assert (c.slots[k].type&65535,c.slots[k].level)==(type_,level),(cls,k)
        count+=1
    return count,unavailable

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--text',default=str(vp.DEFAULT_TEXT));ap.add_argument('--data',default=str(vp.DEFAULT_DATA))
    ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--output',type=Path);args=ap.parse_args()
    text,data=vp.pins.TEXT.read(args.text),vp.pins.DATA.read(args.data)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/('monsters.'+vp.SUFFIX);compile_library(SOURCE,path);lib=library(path)
        result={'text_sha256':vp.TEXT_SHA256,'data_sha256':vp.DATA_SHA256,'handler_cases':handler(text,data,lib,args.cases),'mismatches':0}
        result['creation_cases'],result['creation_unavailable']=creation(text,data,lib)
        if args.mutations:
            source=SOURCE.read_text();plants=[('class_mask','p[2] & 3','p[2] & 1'),('hp_order','p[0x14] << 16','p[0x13] << 16'),
                ('direction','* factor','* (factor + 1)'),('target','v->target[0]; c->tile[1]','v->target[1]; c->tile[1]'),
                ('stride','v->size = 0x1c + 8','v->size = 0x1c + 4'),('buff_offset','b[4] |','b[3] |'),
                ('create_model','c->class_word = (int16_t)v->server_class','c->model += 1; c->class_word = (int16_t)v->server_class'),
                ('create_slot','r->slots[k].level;','r->slots[k].level + 1;')]
            caught=[]
            for name,old,new in plants:
                assert old in source,old
                src=Path(tmp)/'viewport_monsters.c';src.write_text(source.replace(old,new));path=Path(tmp)/(name+'.'+vp.SUFFIX);compile_library(src,path)
                try:
                    if name.startswith('create_'): creation(text,data,library(path),40)
                    else: handler(text,data,library(path),60)
                except AssertionError: caught.append(name)
            result['mutants']={'planted':len(plants),'caught':len(caught),'names':caught};assert len(caught)==len(plants),result
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
