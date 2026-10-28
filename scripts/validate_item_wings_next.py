#!/usr/bin/env python3
"""Part 10 visible wings, ranked bodies and shield callers versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import gen_item_bodies as gen
import item_shield_machine as shields
import pins
import validate_item_clusters as clusters
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]


class BodyWorld(v.World):
    def install(self):
        super().install()
        # Any body random consumption is an unexpected service in this subset.
        self.m.stub(0x01989721, lambda m: self.calls.append(('body-random',)) or 17, 0)


def link_cases(wa, lib):
    vectors = []
    rng = random.Random(0x2002a)
    for t in shields.TYPES:
        for k in range(100):
            values = [k]*32 if k < 30 else [rng.randrange(32768) for _ in range(32)]
            for variant, time in enumerate((0, 700.25, 123456, -150.5)):
                expected = shields.original_link(wa, t, values, time, variant)
                if clusters.c_effects(lib, t, values, time) != expected:
                    raise AssertionError(('shield', hex(t), k, variant))
                vectors.append((t, values, time, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


def position_cases(wa):
    """Execute 0x012b678d with absent per-owner overrides, translate/scale/origin."""
    import renderchar_machine as machine
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/particles')],check=True)
    lib = C.CDLL(str(ROOT/'reconstructed/particles/libclient_particles.dylib'))
    lib.mu_pt_transform_position.argtypes = [C.POINTER(C.c_float)]*3 + [C.c_int,C.c_float,C.POINTER(C.c_float)]
    rng = random.Random(0x12b678d)
    w = v.link_world(wa, 0x16fb)
    m = w.m
    w.add_model(0x16fb, v.MODEL, bones=20)
    obj = v.CHAR + 0x19d0
    m.write(obj, bytes(0x400))
    for k in range(200):
        bone = k % 20
        xyz = [rng.uniform(-100, 100) for _ in range(3)]
        origin = [rng.uniform(-1000, 1000) for _ in range(3)]
        scale = C.c_float(rng.uniform(0.1, 3)).value
        matrix = [1,0,0,xyz[0],0,1,0,xyz[1],0,0,1,xyz[2]]
        m.write(0x06fce398+bone*48, struct.pack('<12f', *matrix))
        m.write(obj+0x158, struct.pack('<3f', *origin))
        m.wf(v.MODEL+0x74, scale)
        result = m.run(0x012b678d, [v.LIGHT, obj, bone, 0], v.MODEL)
        checks = dict(result['checks'])
        checks['esp'] = m.uc.reg_read(m.x86.UC_X86_REG_ESP) == machine.ENTRY_ESP + 20
        output = v.F3()
        lib.mu_pt_transform_position((C.c_float*12)(*matrix),v.F3(),output,1,scale,v.F3(*origin))
        expected = bytes(output)
        if result['error'] or result['stopped'] or not all(checks.values()) or m.read(v.LIGHT,12) != expected:
            raise AssertionError(('shield position', k, result, checks))
    return {'cases': 200, 'mismatches': 0}


def clock_cases(wa, lib):
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa), []
    # Every atlas wrap/division edge, signed conversion and all new scalar families.
    for t in (0x2002, 0x2004, 0x1d7c, 0x1f9f, 0x1d8b):
        for time in (-2147483648,-6283,-1047,-600,-455,-35,-20,-1,-0.0,0,19.9,20,34.9,35,454.9,455,599.9,600,1047,2147483520,2147483648):
            for flags in (2,0x40042):
                case = v.classify_case(t,v.CLASSIFY[0])
                case.update(time=v.f2u(time),render_type=flags,item_level=13<<3)
                result,expected,other,_ = v.client_stream(wa,case,reset)
                if not result['ok'] or other or v.c_stream(lib,case) != (0,expected):
                    raise AssertionError(('clock',hex(t),time,flags,result,other))
                vectors.append((case,expected))
    return {'cases':len(vectors),'mismatches':0},vectors


def mutations(bodies, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'wing-level': ('mu_rc_body_types[type_row].plain)', 'mu_rc_body_types[type_row].plain && it->type < 0x2322)'),
        'atlas-period': ('tick % 600', 'tick % 601'),
        'atlas-frame': ('(tick % 455) / 35', '(tick % 455) / 36'),
        'fast-pulse': ('tick % -1047', 'tick % -1046'),
        'abs-sine': ('if (0.0f > value) value = -value;', 'if (0.0f < value) value = -value;'),
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'object-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
        'ancient-phase': ('recipe[phase]', 'recipe[phase == 4 ? 3 : phase]'),
        'shield-pulse': ('client_sin(time * 0.0005f)', 'client_sin(time * 0.0006f)'),
        'shield-bone': ('rule->bone, rule->bitmap', 'rule->bone + 1, rule->bitmap'),
    }
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name,(old,new) in changes.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor',name,source.count(old)))
            path,library = Path(tmp)/(name+'.c'),Path(tmp)/(name+'.dylib')
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mutations',action='store_true')
    parser.add_argument('--screen',action='store_true',help='candidate rejection, not a passing validation')
    args = parser.parse_args()
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/renderchar')],check=True)
    wa = tuple(p.read() for p in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    types = gen.WING_TYPES + gen.VISIBLE_TYPES
    report['families']['bodies'],bodies,failures = clusters.body_cases(wa,lib,types,args.screen,world_class=BodyWorld)
    if args.screen:
        report.update(rejected=[hex(f[0]) for f in failures],failures=failures)
    else:
        assert not failures
        report['families']['clocks'],clocks = clock_cases(wa,lib)
        report['families']['links'],links = link_cases(wa,lib)
        report['families']['position'] = position_cases(wa)
        if args.mutations:
            report['mutants'] = mutations(bodies+clocks,links)
        import gen_item_pulse_links as pulse
        if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError('body table drift')
        if pulse.generate() != (ROOT/'reconstructed/renderchar/item_pulse_links.h').read_text():
            raise AssertionError('link table drift')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='failures'}))


if __name__ == '__main__':
    main()
