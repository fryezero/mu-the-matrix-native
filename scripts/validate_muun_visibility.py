#!/usr/bin/env python3
"""Whole 400-owner buff-render caller with authored raw byte/predicate inputs."""
import argparse
import ctypes as C
import hashlib
import itertools
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
import actor_machine as am
import pins
import validate_combat as vc
import validate_muun_bones as bones
import validate_muun_riding as riding
ROOT=Path(__file__).resolve().parents[1]
MODEL,OBJ,OWNER,HERO,DECOY=[0x24000000+0x10000*k for k in range(5)]

def samples():
    values=(0,6,7,8,9,10,11,12,13,255)
    for i,(local,remote) in enumerate(itertools.product(values,repeat=2)):
        yield local,remote,1,1,1,0,i%400
    for local_owner,found,predicate,buff,remote,index in itertools.product((0,1),(0,1),(0,1,2),(0,1,2),(0,6,9,255),(0,399)):
        yield 9,remote,predicate,buff,found,local_owner,index

def compare(lib,machine):
    lib.mu_mv_remote_buff_visible.argtypes=[C.c_int,C.c_uint8,C.c_uint8,C.c_uint8,C.c_uint8]
    row={'cases':0,'mismatches':0}
    for local,remote,predicate,buff,found,local_owner,index in samples():
        mdl=bytearray(0x100);obj=bytearray(0x3d8);owner=bytearray(0x3670);hero=bytearray(0x3670);decoy=bytearray(0x3670)
        struct.pack_into('<h',mdl,0x24,3);struct.pack_into('<3f',mdl,0x54,.3,.5,.7)
        struct.pack_into('<I',obj,0x34c,OWNER+0x3254 if found else 0x25003254)
        struct.pack_into('<i',obj,0x74,-1);struct.pack_into('<3f',obj,0xa8,.75,.2,.3)
        owner[0x16]=remote;hero[0x16]=local
        calls=[];lookups=[]
        def lookup(m):
            k=m.argument(0);lookups.append(k)
            return (OWNER if k==index else DECOY),4
        def mesh(m):calls.append([m.argument(k) for k in range(8)]);return 0,32
        stubs={0x95f6db:lookup,0x9a13f4:lambda m:m.uc.reg_read(m.x86.UC_X86_REG_ECX),
            0xd8b3e3:lambda m:predicate,0x1295ade:lambda m:(buff,4),0x966e4a:mesh}
        regions=[am.defined_region(n,a,p) for n,a,p in [('model',MODEL,mdl),('object',OBJ,obj),('owner',OWNER,owner),
            ('local',HERO,hero),('decoy',DECOY,decoy),('hero',0xa39d754,struct.pack('<I',OWNER if local_owner else HERO))]]
        result=machine.execute(0x17f746f,[MODEL,OBJ],regions,stubs)
        local_byte=remote if local_owner else local
        visible=lib.mu_mv_remote_buff_visible(found and not local_owner,predicate,buff,local_byte,remote)
        expected=[[k,0x4040,am.bits(.5),0xffffffff,am.bits(.75),am.bits(am.f32(.2)*8),am.bits(am.f32(.3)*2),0x7fcf] for k in range(3)] if visible else []
        colour=struct.pack('<3f',1,1,1) if visible else bytes(mdl[0x54:0x60])
        equal=result['ok'] and result['eax']&255==visible and calls==expected and result['regions']['model'][0x54:0x60]==colour
        equal &= lookups==list(range(400 if visible else index+1))
        row['cases']+=1
        if not equal:
            row['mismatches']+=1
            if 'first' not in row:row['first']={'input':[local,remote,predicate,buff,found,local_owner,index],
                'got':calls,'expected':expected,'eax':result['eax'],'checks':result['checks'],'error':str(result['error']),
                'lookup_count':len(lookups),'visible':visible}
    return {'visibility':row}

def compare_seat(lib,machine):
    row={'cases':0,'mismatches':0}
    for action in range(279,308):
        slot=bytearray(244);owner=bytearray(0x3670)
        struct.pack_into('<I',slot,4,OWNER);struct.pack_into('<H',owner,0x327e,action)
        result=machine.execute(0x9c046a,[],[am.defined_region('slot',OBJ,slot),
            am.defined_region('owner',OWNER,owner)],{},ecx=OBJ)
        equal=result['ok'] and result['eax']&255==lib.mu_mv_rider_lifts(action)
        row['cases']+=1
        if not equal:row['mismatches']+=1
    return {'seat_phase':row}

SEAT_MUTANTS=[('seat_lower','a >= 0x118','a > 0x118'),('seat_upper','a < 0x133','a <= 0x133')]

MUTANTS=[('remote','if (!remote_found || predicate','if (remote_found || predicate'),
 ('predicate','predicate != 1','predicate == 1'),('buff','|| !buff18','|| buff18'),
 ('group69','{{6,9}','{{6,8}'),('group710','{7,10}','{7,11}'),('group811','{8,11}','{8,10}'),
 ('group1213','{12,13}','{12,14}'),
 ('unknown','return 1; /* Unclassified','return 0; /* Unclassified')]
def run(mutations,only=None):
    if only is not None and not only <= {m[0] for m in MUTANTS+SEAT_MUTANTS}:raise ValueError('unknown mutant')
    start=time.monotonic();text=pins.TEXT.read();machine=vc.Combat(text,pins.DATA.read())
    source=(ROOT/'reconstructed/muun/bone_fx.c').read_text()
    seat_source=(ROOT/'reconstructed/muun/riding.c').read_text()
    with tempfile.TemporaryDirectory() as td:
        p=Path(td);(p/'base').mkdir();families=compare(bones.build(p/'base',source),machine);mutants={}
        (p/'seat').mkdir();families.update(compare_seat(riding.build(p/'seat',seat_source),machine))
        if mutations:
            for name,old,new in MUTANTS:
                if only is not None and name not in only:continue
                if source.count(old)!=1:raise ValueError(name+' ambiguous anchor')
                (p/name).mkdir();r=compare(bones.build(p/name,source.replace(old,new)),machine)
                mutants[name]={'caught':sum(f['mismatches'] for f in r.values())}
            for name,old,new in SEAT_MUTANTS:
                if only is not None and name not in only:continue
                if seat_source.count(old)!=1:raise ValueError(name+' ambiguous anchor')
                (p/name).mkdir();r=compare_seat(riding.build(p/name,seat_source.replace(old,new)),machine)
                mutants[name]={'caught':sum(f['mismatches'] for f in r.values())}
    return {'families':families,'cases':sum(f['cases'] for f in families.values()),'all_equal':all(not f['mismatches'] for f in families.values()),
        'mutants':mutants,'all_mutants_caught':all(m['caught'] for m in mutants.values()),
        'body_sha256':hashlib.sha256(text[0x17f746f-am.TEXT_BASE:0x17f76ec-am.TEXT_BASE]).hexdigest(),'wall_seconds':time.monotonic()-start}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mutations',action='store_true');p.add_argument('--only-mutants');p.add_argument('--output',type=Path);a=p.parse_args()
    r=run(a.mutations or bool(a.only_mutants),set(a.only_mutants.split(',')) if a.only_mutants else None)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['all_equal'] and r['all_mutants_caught'] else 1)
