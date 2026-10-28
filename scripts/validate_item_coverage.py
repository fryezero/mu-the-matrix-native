#!/usr/bin/env python3
"""Part 9 ranked body clusters and the nine-bone shield link, offline."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import gen_item_bodies as gen
import pins
import validate_item_clusters as clusters
import validate_item_ranked as ranked
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]


def link_cases(wa, lib):
    vectors = []
    rng = random.Random(0x2002f9)
    for k in range(100):
        values = [k]*32 if k < 30 else [rng.randrange(32768) for _ in range(32)]
        for variant, time in enumerate((0,700.25,123456,-150.5)):
            expected = ranked.original_link(wa,0x16fa,values,time,variant)
            actual = clusters.c_effects(lib,0x16fa,values,time)
            if actual != expected:
                raise AssertionError(('shield link',k,variant,expected,actual))
            vectors.append((0x16fa,values,time,expected))
    return {'cases':len(vectors),'mismatches':0}, vectors


def clock_cases(wa,lib):
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa), []
    for t in gen.CLOCK_TYPES[::7]:
        for time in (-2147483648,-6283,-6282.5,-1,0,6282.9,6283,6284,2147483520,2147483648):
            for flags in (2,0x40042):
                case = v.classify_case(t,v.CLASSIFY[0])
                case.update(time=v.f2u(time),render_type=flags,item_level=13<<3)
                result,expected,other,_=v.client_stream(wa,case,reset)
                actual=v.c_stream(lib,case)
                if not result['ok'] or other or actual!=(0,expected):
                    raise AssertionError(('clock',hex(t),time,flags,result,other,expected,actual))
                vectors.append((case,expected))
    return {'cases':len(vectors),'mismatches':0},vectors


def mutations(bodies,links):
    source=(ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes={
        'cosine-period':('tick % -6283','tick % -6282'),
        'overlay-quality':('s->item->quality > 1 && mu_rc_item_glow_level','s->item->quality > 2 && mu_rc_item_glow_level'),
        'overlay-level':('((s->item->item_level >> 3) & 15) >= 9','((s->item->item_level >> 3) & 15) >= 10'),
        'overlay-scroll':('s->item->time * 0.0001f','s->item->time * 0.0002f'),
        'mesh-index':('d.mesh = (int32_t)words[0];','d.mesh = (int32_t)words[0] + 1;'),
        'object-alpha':('&s->item->object_alpha, 4','&base.alpha, 4'),
        'ancient-phase':('recipe[phase]','recipe[phase == 4 ? 3 : phase]'),
        'shield-absolute':('fabsf(sin1) + 0.1f','sin1 + 0.1f'),
        'link-bone':('rule->bone, rule->bitmap','rule->bone + 1, rule->bitmap'),
    }
    caught={}
    with tempfile.TemporaryDirectory() as tmp:
        for name,(old,new) in changes.items():
            if source.count(old)!=1:
                raise AssertionError(('mutant anchor',name,source.count(old)))
            path,library=Path(tmp)/(name+'.c'),Path(tmp)/(name+'.dylib')
            path.write_text(source.replace(old,new))
            subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off',
                            '-I',str(ROOT/'reconstructed/renderchar'),str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(library)],check=True)
            lib=C.CDLL(str(library))
            detected=sum(v.c_stream(lib,case)!=(0,expected) for case,expected in bodies)
            detected+=sum(clusters.c_effects(lib,t,values,time)!=expected for t,values,time,expected in links)
            if not detected: raise AssertionError(('surviving mutant',name))
            caught[name]=detected
    return caught


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mutations',action='store_true')
    p.add_argument('--screen',action='store_true',help='candidate rejection only; not a passing validation')
    a=p.parse_args()
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/renderchar')],check=True)
    wa=tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    lib=C.CDLL(str(v.LIBRARY))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    report['families']['bodies'],bodies,failures=clusters.body_cases(wa,lib,gen.CLOCK_TYPES+gen.CLUSTER_TYPES,a.screen)
    if a.screen:
        report.update(rejected=[hex(f[0]) for f in failures],failures=failures)
    else:
        assert not failures
        report['families']['clocks'],clocks=clock_cases(wa,lib)
        report['families']['links'],links=link_cases(wa,lib)
        if a.mutations: report['mutants']=mutations(bodies+clocks,links)
        import gen_item_pulse_links as pulse
        if gen.generate()!=(ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError('body table drift')
        if pulse.generate()!=(ROOT/'reconstructed/renderchar/item_pulse_links.h').read_text():
            raise AssertionError('link table drift')
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='failures'}))

if __name__=='__main__': main()
