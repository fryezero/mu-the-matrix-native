#!/usr/bin/env python3
"""Part 5 item bodies, remaining skins and link callers versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import gen_item_bodies as gen
import gen_skin_bodies as skins
import pins
import validate_item_clusters as clusters
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
SKINS = (0x3895, 0x3896, 0x389b, 0x389c, 0x389d, 0x389e)
LINKS = (0x0afd, 0x0afe)


class SkinWorld(v.World):
    """Record deep sprite inputs; retain the original code before/after each service."""
    def install(self):
        super().install()
        def position(m):
            assert m.arg(0) == 0x06fce398 and m.arg(3) == 0
            self.offset = tuple(struct.unpack('<3I', m.read(m.arg(1), 12)))
            m.write(m.arg(2), m.read(m.arg(1), 12))
            return 0
        def sprite(m):
            assert m.arg(4) == v.OBJ
            assert m.read(m.arg(8), 12) == struct.pack('<iif', 1, 1, 1)
            self.calls.append(('skin_sprite', (m.arg(0), 0, self.offset, m.arg(2),
                tuple(struct.unpack('<3I', m.read(m.arg(3), 12))), m.arg(5), m.arg(6), m.arg(7), 0)))
            return 0
        self.m.stub(0x012b6ef1, position, 16)
        self.m.stub(0x01692eb7, sprite, 0)


def c_skin_effect(lib, t, time):
    out = clusters.Effect()
    if not lib.mu_rc_skin_effect(t, C.c_float(time), C.byref(out)):
        return []
    s = out.sprite
    return [(s.bitmap, s.bone, tuple(v.f2u(x) for x in out.offset), v.f2u(s.scale),
             tuple(v.f2u(x) for x in s.light), v.f2u(s.rotation), s.blend, s.axes, out.particle)]


def skin_cases(wa, lib):
    reset = ResetWorld(wa, SkinWorld)
    vectors = []
    for t in SKINS:
        rng = random.Random(0x2002e + t)
        for k in range(512):
            case = v.random_case_any(rng, t)
            if k < 384:
                state, level = divmod(k, 16)
                case.update(item_level=(level << 3) | (state % 8), quality=(0,1,2,3,4,5)[state % 6],
                            render_type=(2,0x102,0x402,0x40042)[state % 4], option1=state % 3,
                            ext=(0,1,2,0x10,0x20,0x33)[state % 6])
            case.update(record=rng.choice([None,(0,0,0),(6,0,0),(0,0x26,0),(0,0x5b,0)]),
                        a10=0xffffffff, a11=0xffffffff)
            result, stream, other, _ = v.client_stream(wa, case, reset)
            effects = [c[1] for c in other if c[0] == 'skin_sprite']
            if not result['ok'] or len(effects) != len(other) or v.c_stream(lib, case) != (0, stream) or \
                    c_skin_effect(lib, t, v.u2f(case['time'])) != effects:
                raise AssertionError((hex(t), k, case, result, stream, v.c_stream(lib,case), other,
                                      c_skin_effect(lib,t,v.u2f(case['time']))))
            vectors.append((case, stream, effects))
        print(f'skin {t:#x}: 512/512', flush=True)
    return {'cases':len(vectors),'mismatches':0}, vectors


def mutations(directory, bodies, skin_vectors, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'blend-pulse': ('* 0.7 + (double)0.3f', '* 0.6 + (double)0.3f'),
        'skin-raw-level': ('(it->item_level >> 3) & 15;', '((it->item_level >> 3) + 1) & 15;'),
        'skin-scroll': ('tick % 4000', 'tick % 4001'),
        'skin-sprite-colour': ('pulse * 0.32f', 'pulse * 0.33f'),
        'skin-sprite-offset': ('? 15.0f : -15.0f', '? 16.0f : -15.0f'),
        'sword-bone': ('i < 4 ? 4 : i + 2', 'i < 4 ? 5 : i + 2'),
        'sword-rotation': ('time * 0.0006f * 360.0f', 'time * 0.0005f * 360.0f'),
        'sword-flare-offset': ('i ? -3.0f : 3.0f', 'i ? -4.0f : 3.0f'),
    }
    caught = {}
    for name, (old, new) in changes.items():
        if old not in source:
            raise AssertionError(('mutant anchor',name))
        path, library = directory/f'{name}.c', directory/f'{name}.dylib'
        path.write_text(source.replace(old,new))
        subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off',
                        '-I',str(ROOT/'reconstructed/renderchar'),str(path),
                        str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(library)],check=True)
        lib = C.CDLL(str(library))
        detected = sum(v.c_stream(lib,case)!=(0,expected) for case,expected in bodies)
        detected += sum(v.c_stream(lib,case)!=(0,expected) or c_skin_effect(lib,case['type'],v.u2f(case['time']))!=effects
                        for case,expected,effects in skin_vectors)
        detected += sum(clusters.c_effects(lib,t,values,time)!=expected for t,values,time,expected in links)
        if not detected:
            raise AssertionError(('surviving mutant',name))
        caught[name] = detected
    return caught


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mutations',action='store_true')
    a = p.parse_args()
    wa = tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/renderchar')],check=True)
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    report['families']['bodies'], bodies, failures = clusters.body_cases(wa,lib,gen.CONTINUATION_TYPES)
    assert not failures
    report['families']['skins'], skin_vectors = skin_cases(wa,lib)
    report['families']['links'], links = clusters.link_cases(wa,lib,LINKS)
    if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError('body table drifted')
    if skins.generate() != (ROOT/'reconstructed/renderchar/skin_bodies.h').read_text():
        raise AssertionError('skin body table drifted')
    if a.mutations:
        with tempfile.TemporaryDirectory() as tmp:
            report['mutants'] = mutations(Path(tmp),bodies,skin_vectors,links)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
