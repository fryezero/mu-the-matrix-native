#!/usr/bin/env python3
"""Part 6 ranked bodies and sprite-chain link callers versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import pins
import validate_item_clusters as clusters
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
LINKS = (0x0af9, 0x12f9)


def original_link(wa, t, values, time, variant=0):
    w = v.link_world(wa, t)
    m = w.m
    sequence, consumed, calls, bone = iter(values), [], [], []
    def rand(mm):
        value = next(sequence)
        consumed.append(value)
        return value
    def position(mm):
        assert mm.arg(3) == 1
        bone[:] = [(mm.arg(0)-0x06fce398)//48]
        mm.write(mm.arg(2), mm.read(mm.arg(1), 12))
        return 0
    def sprite(mm):
        assert mm.arg(4) == v.CHAR + 0x3254
        assert mm.read(mm.arg(8), 12) == struct.pack('<iif', 1, 1, 1)
        calls.append((mm.arg(0), bone[0], struct.unpack('<3I', mm.read(mm.arg(1), 12)),
                      mm.arg(2), struct.unpack('<3I', mm.read(mm.arg(3), 12)),
                      mm.arg(5), mm.arg(6), mm.arg(7), 0))
        return 0
    m.stub(0x01989721, rand, 0)
    m.stub(0x012b6ef1, position, 16)
    m.stub(0x01692eb7, sprite, 0)
    m.wf(0x06fce370, time)
    part = v.CHAR + 0x19ac
    m.write(part, struct.pack('<hBBBB', t, variant*4, variant&1, 0, 47))
    result = m.run(0x012bd910, [0, 0, v.f2u(15), v.CHAR, part, t, variant*4,
                              variant&1, variant&1, 1, 0, variant>>1])
    if not result['ok']:
        raise AssertionError((hex(t), result))
    # Other engine calls are the established link setup boundary, not effects.
    if any(c[0] not in ('rotpos', 'pose', 'tick', 'transform', 'objdraw') for c in w.calls):
        raise AssertionError(('unexpected link service', w.calls))
    return 0, calls, len(consumed)


def link_cases(wa, lib):
    rng, vectors = random.Random(0x2002f), []
    for t in LINKS:
        for k in range(100):
            values = [k]*32 if k < 30 else [rng.randrange(32768) for _ in range(32)]
            for variant, time in enumerate((0, 700.25, 123456, -150.5)):
                expected = original_link(wa, t, values, time, variant)
                if clusters.c_effects(lib, t, values, time) != expected:
                    raise AssertionError((hex(t), k, variant, expected, clusters.c_effects(lib,t,values,time)))
                vectors.append((t, values, time, expected))
    return {'cases':len(vectors), 'mismatches':0}, vectors


def mutations(directory, bodies, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'ancient-phase': ('recipe[phase]', 'recipe[phase == 4 ? 3 : phase]'),
        'body-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
        'chain-bone': ('first + i;', 'first + i + 1;'),
        'chain-scale': ('bone, 0x7f67, 1.0f,', 'bone, 0x7f67, 1.1f,'),
        'chain-choice': ('chain->flash && random(context) % 3 == 0', 'chain->flash && random(context) % 3 == 1'),
        'chain-white': ('chain->white && i == chain->count - 1', 'chain->white && i == chain->count - 2'),
    }
    caught = {}
    for name, (old,new) in changes.items():
        if source.count(old) != 1:
            raise AssertionError(('mutant anchor', name, source.count(old)))
        path, library = directory/f'{name}.c', directory/f'{name}.dylib'
        path.write_text(source.replace(old,new))
        subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off',
                        '-I',str(ROOT/'reconstructed/renderchar'),str(path),
                        str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(library)],check=True)
        lib = C.CDLL(str(library))
        detected = sum(v.c_stream(lib,case)!=(0,expected) for case,expected in bodies)
        detected += sum(clusters.c_effects(lib,t,values,time)!=expected for t,values,time,expected in links)
        if not detected:
            raise AssertionError(('surviving mutant',name))
        caught[name] = detected
    return caught


def main():
    import gen_item_bodies as gen
    import gen_item_links as chains
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mutations',action='store_true')
    a = p.parse_args()
    wa = tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/renderchar')],check=True)
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    report['families']['bodies'], bodies, failures = clusters.body_cases(wa,lib,gen.RANKED_TYPES)
    assert not failures
    report['families']['links'], links = link_cases(wa,lib)
    if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError('body table drifted')
    if chains.generate() != (ROOT/'reconstructed/renderchar/item_links.h').read_text():
        raise AssertionError('link table drifted')
    if a.mutations:
        with tempfile.TemporaryDirectory() as tmp:
            report['mutants'] = mutations(Path(tmp),bodies,links)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
