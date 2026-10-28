#!/usr/bin/env python3
"""Part 8 ranked bodies, rank-5 no-owner mesh streams and further links."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import pins
import gen_item_bodies as gen
import item_pose_machine as pose
import validate_renderchar as v
import validate_item_clusters as clusters
import validate_item_ranked as ranked

ROOT = Path(__file__).resolve().parents[1]
LINKS = (0x10f0, 0x16f5)

class Context(C.Structure):
    _fields_ = [('lighting',C.c_int32),('blue',C.c_int32),('black',C.c_int32),
                ('random',clusters.RANDOM),('context',C.c_void_p)]


def rank5_cases(wa, lib):
    payload = pose.seed()
    vectors = []
    for t in pose.TYPES:
        for k in range(584):
            rng = random.Random(t*1000+k)
            case = v.random_case_any(rng,t)
            case.update(a10=0xffffffff,a11=0xffffffff,record=None,
                        item_level=((k%16)<<3),quality=5)
            lighting, value = k//292, (k*31)%32768
            state=k%292
            if state<192:
                variant,level=divmod(state,16)
                case.update(item_level=(level<<3)|(variant%8),quality=(0,1,2,3,4,5)[variant%6],
                            render_type=(2,0x102,0x402,0x40042)[variant%4],
                            option1=variant%3,ext=(0,1,2,0x10,0x20,0x33)[variant%6])
            blue,black = (-1,-1) if k%4<2 else (3,1)
            calls=[]
            class World(v.World):
                def __init__(self,*args):
                    super().__init__(*args)
                    m=self.m
                    m.write(pose.pose.WINDOW,payload)
                    m.heap=pose.pose.WINDOW+0x100000
                    m.ensure(pose.pose.ROOT_MATRIX,48)
                    m.write(pose.pose.ROOT_MATRIX,struct.pack('<12f',1,0,0,4,0,1,0,5,0,0,1,6))
                    m.ensure(0x06fce398,0x1000);m.ensure(pose.pose.QUATERNIONS,32)
                    m.stub(0x01989721,lambda mm:calls.append(value) or value,0)
                    # Engine name lookup is supplied independently of the mesh stream.
                    def named(mm):
                        addr=mm.arg(0)
                        n=mm.r32(addr+16)
                        data=addr if mm.r32(addr+20)<16 else mm.r32(addr)
                        name=mm.read(data,n)
                        return blue if b'Blue' in name else black
                    m.stub(0x012bd4a6,named,4)
                def add_model(self,*args,**kwargs):
                    super().add_model(*args,**kwargs)
                    m=self.m
                    m.write(v.MODEL+0x22,struct.pack('<hhh',2,6,2))
                    m.write(v.MODEL+0x2c,payload[0x2c:0x34])
                    m.w32(v.MODEL+0x60,0xffffffff)
                    m.write(v.MODEL+0x50,bytes([lighting]))
                    m.wf(v.MODEL+0x74,1)
                    m.write(v.OBJ+0x2c,struct.pack('<H',k%2))
                    m.write(v.OBJ+0xd0,struct.pack('<2f',(k%5)*0.5,(k%3)*0.5))
            result, stream, other, _ = v.client_stream(wa,case,World)
            actual, consumed = rank5_c(lib,case,lighting,blue,black,value)
            if not result['ok'] or other or actual!=(0,stream) or consumed!=len(calls):
                raise AssertionError(('rank5 mesh',hex(t),k,case,result,other,stream,actual,consumed,len(calls)))
            vectors.append((case,lighting,blue,black,value,stream,len(calls)))
        print(f'rank5 {t:#x}: 584/584',flush=True)
    return {'cases':len(vectors),'mismatches':0,'boundary':'real pose; mesh streams with absent OBJECT owner bones'},vectors


def rank5_c(lib,case,lighting,blue,black,value):
    calls=[]
    @clusters.RANDOM
    def rand(_):calls.append(value);return value
    context=Context(lighting,blue,black,rand,None)
    class Adapter:
        def mu_rc_item_draws(self,*args):
            return lib.mu_rc_item_draws_context(*args,C.byref(context))
    return v.c_stream(Adapter(),case),len(calls)


def link_cases(wa,lib):
    vectors=[]
    for t in LINKS:
        rng=random.Random(t)
        for k in range(100):
            values=[k]*32 if k<30 else [rng.randrange(32768) for _ in range(32)]
            for variant,time in enumerate((0,700.25,123456,-150.5)):
                expected=ranked.original_link(wa,t,values,time,variant)
                actual=clusters.c_effects(lib,t,values,time)
                if actual!=expected:raise AssertionError(('next link',hex(t),expected,actual))
                vectors.append((t,values,time,expected))
    return {'cases':len(vectors),'mismatches':0},vectors


def mutations(bodies,poses,links):
    source=(ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes={
        'rank5-count':('mesh < (blue ? 4 : 2)','mesh < (blue ? 3 : 1)'),
        'rank5-lighting':('!s->context->lighting','s->context->lighting'),
        'rank5-pulse':('tick % -6283','tick % -6282'),
        'rank5-uv':('time / 80.0f','time / 81.0f'),
        'rank5-random':('rank5_random(s) % 5','rank5_random(s) % 4'),
        'rank5-named':('blue ? s->context->blue_mesh : 1','blue ? s->context->black_mesh : 1'),
        'body-alpha':('&s->item->object_alpha, 4','&base.alpha, 4'),
        'link-bone':('rule->bone, rule->bitmap','rule->bone + 1, rule->bitmap'),
        'link-scale':('value *= rule->mul;','value *= rule->mul + 0.1f;'),
    }
    caught={}
    with tempfile.TemporaryDirectory() as tmp:
        for name,(old,new) in changes.items():
            # The rank-5 random helper appears at its two original call sites.
            if source.count(old)!=(2 if name in ('rank5-random','rank5-named') else 1):
                raise AssertionError(('mutant anchor',name,source.count(old)))
            path,library=Path(tmp)/(name+'.c'),Path(tmp)/(name+'.dylib')
            path.write_text(source.replace(old,new))
            subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off','-I',str(ROOT/'reconstructed/renderchar'),str(path),str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(library)],check=True)
            lib=C.CDLL(str(library))
            detected=sum(rank5_c(lib,case,light,blue,black,value)!=((0,expected),count)
                         for case,light,blue,black,value,expected,count in poses)
            detected+=sum(v.c_stream(lib,case)!=(0,expected) for case,expected in bodies)
            detected+=sum(clusters.c_effects(lib,t,values,time)!=expected for t,values,time,expected in links)
            if not detected:raise AssertionError(('surviving mutant',name))
            caught[name]=detected
    return caught


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mutations',action='store_true');a=p.parse_args()
    for d in ('renderchar','model-codec'):subprocess.run(['make','-s','-C',str(ROOT/'reconstructed'/d)],check=True)
    wa=tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    lib=C.CDLL(str(v.LIBRARY))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    report['families']['rank5'],poses=rank5_cases(wa,lib)
    report['families']['bodies'],bodies,failures=clusters.body_cases(wa,lib,gen.NEXT_TYPES)
    assert not failures
    report['families']['links'],links=link_cases(wa,lib)
    if a.mutations:
        report['mutants']=mutations(bodies,poses,links)
    import gen_item_pulse_links as pulse
    if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError('body table drift')
    if pulse.generate() != (ROOT/'reconstructed/renderchar/item_pulse_links.h').read_text():
        raise AssertionError('pulse table drift')
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
