#!/usr/bin/env python3
"""Part 7 stress gear, ranked bodies, pulse links and rank-5 pose boundary."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import gen_item_bodies as gen
import gen_item_pulse_links as pulse
import item_pose_machine as pose
import pins
import validate_item_clusters as clusters
import validate_item_ranked as ranked
import validate_renderchar as v

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={0x0eee:[('gl','glPushMatrix',[]),('gl','glPopMatrix',[])]}


def link_cases(wa,lib):
    rng=random.Random(0x2002a7)
    vectors=[]
    for t in (0x0afa, 0x0eed, 0x0eee):
        for k in range(100):
            values=[k]*32 if k<30 else [rng.randrange(32768) for _ in range(32)]
            for variant,time in enumerate((0,700.25,123456,-150.5)):
                expected=ranked.original_link(wa,t,values,time,variant)
                actual=clusters.c_effects(lib,t,values,time)
                if actual!=expected:raise AssertionError(('pulse link',hex(t),k,time,expected,actual))
                if not lib.mu_rc_link_supported(t):raise AssertionError(('native admission',hex(t)))
                vectors.append((t,values,time,expected))
    return {'cases':len(vectors),'mismatches':0},vectors


def clock_cases(wa,lib):
    vectors=[]
    clocks=(-500.5,-1,0,1999.75,2000,2000.25,2147483520,2147483648,-2147483648,-2147483904)
    for t in (0x0eee,0x18fe,0x1cfe,0x218a):
        for time in clocks:
            case=v.classify_case(t,v.CLASSIFY[8])
            case['time']=v.f2u(time)
            result,stream,other,_=v.client_stream(wa,case)
            if not result['ok'] or other!=ALLOWED.get(t,[]) or v.c_stream(lib,case)!=(0,stream):
                raise AssertionError(('signed item clock',hex(t),time,result,other,stream,v.c_stream(lib,case)))
            vectors.append((case,stream))
    return {'cases':len(vectors),'mismatches':0},vectors


def mutations(directory,bodies,links,poses):
    source=(ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes={
        'mesh-index':('d.mesh = (int32_t)words[0];','d.mesh = (int32_t)words[0] + 1;'),
        'object-alpha':('&s->item->object_alpha, 4','&base.alpha, 4'),
        'body-sine':('time * 0.0015f','time * 0.0016f'),
        'armour-clamp':('if (value > 0.65f) value = 0.65f;','if (value > 0.65f) value = 0.64f;'),
        'uv-period':('tick % 2000','tick % 1999'),
        'link-bone':('rule->bone, rule->bitmap','rule->bone + 1, rule->bitmap'),
        'link-scale':('value *= rule->mul;','value *= rule->mul + 0.1f;'),
        'link-rotation':('client_sin(time * 0.01f) * 360.0f','client_sin(time * 0.02f) * 360.0f'),
    }
    caught={}
    for name,(old,new) in changes.items():
        if source.count(old)!=1:raise AssertionError(('mutant anchor',name,source.count(old)))
        path,library=directory/(name+'.c'),directory/(name+'.dylib')
        path.write_text(source.replace(old,new))
        subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off','-I',str(ROOT/'reconstructed/renderchar'),str(path),str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(library)],check=True)
        lib=C.CDLL(str(library))
        detected=sum(v.c_stream(lib,case)!=(0,expected) for case,expected in bodies)
        detected+=sum(clusters.c_effects(lib,t,values,time)!=expected for t,values,time,expected in links)
        if not detected:raise AssertionError(('surviving mutant',name))
        caught[name]=detected
    source=(ROOT/'reconstructed/model-codec/pose_builder.c').read_text()
    class Snapshot:
        def __init__(self,snapshot):
            self.spans=dict(zip((v.MODEL,pose.pose.WINDOW,0x06fce398,pose.pose.QUATERNIONS,pose.pose.ROOT_MATRIX,v.OBJ),snapshot[:6]))
        def read(self,address,size):
            for base,data in self.spans.items():
                if base<=address and address+size<=base+len(data):return data[address-base:address-base+size]
            raise AssertionError(('snapshot read',hex(address),size))
    for name,old,new in (
        ('pose-root','(uint8_t)arguments->keep_root == 0','(uint8_t)arguments->keep_root != 0'),
        ('pose-prior-frame','bits_float(arguments->prior_frame)','bits_float(arguments->frame)')):
        if source.count(old)!=1:raise AssertionError(('pose mutant anchor',name))
        path,library=directory/(name+'.c'),directory/(name+'.dylib');path.write_text(source.replace(old,new))
        subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off','-I',str(ROOT/'reconstructed/model-codec'),str(path),str(ROOT/'reconstructed/model-codec/bone_tracks.c'),str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(library)],check=True)
        lib=C.CDLL(str(library))
        detected=sum(not pose.compare_pose(Snapshot(snapshot),lib,v.MODEL,snapshot[6],expected) for snapshot,expected in poses)
        if not detected:raise AssertionError(('surviving pose mutant',name))
        caught[name]=detected
    return caught


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--mutations',action='store_true');a=p.parse_args()
    wa=tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    for d in ('renderchar','model-codec','particles'):subprocess.run(['make','-s','-C',str(ROOT/'reconstructed'/d)],check=True)
    lib=C.CDLL(str(v.LIBRARY))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    report['families']['bodies'],bodies,failures=clusters.body_cases(wa,lib,gen.EXPANDED_TYPES,allowed_services=ALLOWED)
    assert not failures
    report['families']['links'],links=link_cases(wa,lib)
    report['families']['clocks'],clocks=clock_cases(wa,lib)
    report['families']['rank5_pose'],poses=pose.cases(wa)
    points=report['families']['rank5_pose'].pop('posed_point_cases')
    report['families']['rank5_points']={'cases':points,'mismatches':0,
        'boundary':'two authored points per pose, real TransformPosition versus production C'}
    if gen.generate()!=(ROOT/'reconstructed/renderchar/item_bodies.h').read_text():raise AssertionError('body table drift')
    if pulse.generate()!=(ROOT/'reconstructed/renderchar/item_pulse_links.h').read_text():raise AssertionError('pulse links drift')
    if a.mutations:
        with tempfile.TemporaryDirectory() as tmp:report['mutants']=mutations(Path(tmp),bodies+clocks,links,poses)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
