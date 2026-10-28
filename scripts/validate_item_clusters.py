#!/usr/bin/env python3
"""Part 3 compiled C versus pinned body streams and offset link branches."""
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import sys
import pins
import validate_renderchar as v
import validate_item_types as previous
from item_body_machine import ResetWorld
ROOT = Path(__file__).resolve().parents[1]
RANDOM = C.CFUNCTYPE(C.c_int32, C.c_void_p)
class Effect(C.Structure):
    _fields_ = [('sprite', previous.Sprite), ('offset', C.c_float*3), ('particle', C.c_int32)]

def c_effects(lib, t, values):
    seq = iter(values)
    consumed = []
    @RANDOM
    def rand(_):
        value = next(seq)
        consumed.append(value)
        return value
    out, n = (Effect*20)(), C.c_int32()
    status = lib.mu_rc_link_effects(t, rand, None, out, 20, C.byref(n))
    calls = []
    for e in out[:n.value]:
        s = e.sprite
        calls.append((s.bitmap, s.bone, tuple(v.f2u(x) for x in e.offset), v.f2u(s.scale),
                      tuple(v.f2u(x) for x in s.light), v.f2u(s.rotation), s.blend, s.axes, e.particle))
    return status, calls, len(consumed)

def link_cases(wa, lib):
    rng = random.Random(0x2002c)
    vectors = []
    for t in (0x14f0, 0x12fb):
        for k in range(100):
            values = [k]*32 if k<30 else [rng.randrange(32768) for _ in range(32)]
            for variant in range(4):
                w = v.link_world(wa, t)
                m = w.m
                seq, consumed, observed, transform = iter(values), [], [], []
                def rand(mm):
                    r = next(seq); consumed.append(r); return r
                m.stub(0x01989721, rand, 0)
                def position(mm):
                    transform[:] = [(mm.arg(0)-0x06fce398)//48,
                                     tuple(mm.read(mm.arg(1),12))]
                    mm.write(mm.arg(2), mm.read(mm.arg(1),12))
                    return 0
                m.stub(0x012b6ef1, position, 16)
                def sprite(mm):
                    assert mm.read(mm.arg(8),12) == struct.pack('<iif',1,1,1)
                    observed.append((mm.arg(0), transform[0], struct.unpack('<3I',mm.read(mm.arg(1),12)),
                                     mm.arg(2), struct.unpack('<3I',mm.read(mm.arg(3),12)),
                                     mm.arg(5),mm.arg(6),mm.arg(7),0))
                    return 0
                def particle(mm):
                    observed.append((mm.arg(0), transform[0], struct.unpack('<3I',mm.read(mm.arg(1),12)),
                                     mm.arg(5), struct.unpack('<3I',mm.read(mm.arg(3),12)),
                                     0,0,4,mm.arg(4)))
                    return 0
                m.stub(0x01692eb7,sprite,0)
                m.stub(0x0168fafd,particle,0)
                part=v.CHAR+0x19ac
                m.write(part,struct.pack('<hBBBB',t,variant*4,variant&1,0,47))
                result=m.run(0x012bd910,[0,0,v.f2u(15),v.CHAR,part,t,variant*4,variant&1,variant&1,1,0,variant>>1])
                actual=c_effects(lib,t,values)
                if not result['ok'] or actual!=(0,observed,len(consumed)):
                    raise AssertionError((hex(t),k,variant,result,observed,actual,len(consumed)))
                vectors.append((t,values,actual))
    return {'cases':len(vectors),'mismatches':0,'targets':['0x012c741a','0x012c761d']},vectors

def transform_cases(wa):
    """Real TransformPosition with nonzero offsets, versus production C math."""
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/particles')],check=True)
    suffix='dylib' if sys.platform=='darwin' else 'so'
    lib=C.CDLL(str(ROOT/f'reconstructed/particles/libclient_particles.{suffix}'))
    lib.mu_pt_transform_position.argtypes=[C.POINTER(C.c_float)]*3+[C.c_int,C.c_float,C.POINTER(C.c_float)]
    rng=random.Random(0x12b6ef1)
    reset=ResetWorld(wa)
    for _ in range(200):
        w=reset()
        m=w.m
        matrix=(C.c_float*12)(*[rng.uniform(-30,30) for _ in range(12)])
        offset=v.F3(*[rng.uniform(-100,100) for _ in range(3)])
        origin=v.F3(*[rng.uniform(-1000,1000) for _ in range(3)])
        scale=C.c_float(rng.uniform(0.1,3)).value
        w.add_model(0x14f0,v.MODEL,bones=1)
        m.write(v.BONES,bytes(matrix))
        m.write(v.LIGHT,bytes(offset))
        m.wf(v.MODEL+0x74,scale)
        m.write(v.MODEL+0x78,bytes(origin))
        result=m.run(0x012b6ef1,[v.BONES,v.LIGHT,v.LIGHT+0x40,1],v.MODEL)
        # The direct thiscall callee pops its four arguments, unlike run()'s cdecl default.
        checks=dict(result['checks'])
        import renderchar_machine as machine
        checks['esp']=m.uc.reg_read(m.x86.UC_X86_REG_ESP)==machine.ENTRY_ESP+20
        out=v.F3()
        lib.mu_pt_transform_position(matrix,offset,out,1,scale,origin)
        if result['error'] or result['stopped'] or result['pc']!=hex(machine.SENTINEL) or not all(checks.values()) or m.read(v.LIGHT+0x40,12)!=bytes(out):
            raise AssertionError(('offset transform',result,checks,list(out)))
    return {'cases':200,'mismatches':0}


def body_cases(wa, lib, types, screen=False):
    vectors, failed = [], []
    reset = ResetWorld(wa)
    # Fresh-machine controls cover all eleven survey states and diverse branches.
    for t in types[::max(1,len(types)//12)]:
        for config in v.CLASSIFY:
            case = v.classify_case(t,config)
            fresh = v.client_stream(wa,case)
            reused = v.client_stream(wa,case,reset)
            if fresh[:3] != reused[:3]:
                raise AssertionError(('reset-world control',hex(t),config,fresh[:3],reused[:3]))
    for t in types:
        rng = random.Random(0x2002c + t)
        pending = []
        for k in range(292):
            case = v.random_case_any(rng, t)
            if k < 192:
                state, level = divmod(k, 16)
                case.update(item_level=(level << 3) | (state % 8), quality=(0,1,2,3,4,5)[state % 6],
                            render_type=(2,0x102,0x402,0x40042)[state % 4],
                            option1=state % 3, ext=(0,1,2,0x10,0x20,0x33)[state % 6])
            case.update(record=rng.choice([None,(0,0,0),(6,0,0),(0,0x26,0),(0,0x5b,0)]),
                        a10=0xffffffff, a11=0xffffffff)
            result, stream, other, machine = v.client_stream(wa, case, reset)
            status, actual = v.c_stream(lib, case)
            if not result['ok'] or status or actual != stream or other:
                failure = (t, k, case, stream, actual, result, other)
                if not screen:
                    raise AssertionError(failure)
                failed.append(failure)
                break
            pending.append((case, stream))
        else:
            vectors.extend(pending)
        print(f'body {t:#x}: {len(pending)}/292', flush=True)
    return {'cases':len(vectors),'mismatches':0,'types':len(vectors)//292}, vectors, failed


def mutations(directory, bodies, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'body-object-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
        'body-flag-branch': ('flags & 0x40000u ? 5 : 0', '0'),
        'armour-dim-count': ('i < 3; ++i)\n                body_color', 'i < 2; ++i)\n                body_color'),
        'staff-offset': ('(float)i * 30.0f - 180.0f', '(float)i * 31.0f - 180.0f'),
        'staff-choice': ('random(context) % 3 == 0', 'random(context) % 3 == 1'),
        'bow-bone': ('i == 0 ? 7 : 15', 'i == 0 ? 8 : 15'),
        'bow-scale': ('{0.8f, 1.3f, 2.0f}', '{0.8f, 1.2f, 2.0f}'),
    }
    caught = {}
    for name, (old, new) in changes.items():
        if source.count(old) != 1:
            raise AssertionError(('mutant anchor',name,source.count(old)))
        path, dylib = directory/f'{name}.c', directory/f'{name}.dylib'
        path.write_text(source.replace(old,new))
        subprocess.run(['clang','-shared','-fPIC','-O2','-std=c11','-ffp-contract=off',
                        '-I',str(ROOT/'reconstructed/renderchar'),str(path),
                        str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(dylib)],check=True)
        lib = C.CDLL(str(dylib))
        detected = sum(v.c_stream(lib,case)!=(0,expected) for case,expected in bodies)
        detected += sum(c_effects(lib,t,values)!=expected for t,values,expected in links)
        if not detected:
            raise AssertionError(('surviving mutant',name))
        caught[name] = detected
    return caught


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mutations',action='store_true')
    p.add_argument('--screen',action='store_true',help='locally screen candidates; not a passing validation report')
    a=p.parse_args()
    wa=tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/renderchar')],check=True)
    lib=C.CDLL(str(v.LIBRARY))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{}}
    import gen_item_bodies as gen
    report['families']['links'],links=link_cases(wa,lib)
    report['families']['transforms']=transform_cases(wa)
    report['families']['bodies'],bodies,failed=body_cases(wa,lib,gen.REVIEWED_TYPES,a.screen)
    report['body_types']=sorted({case['type'] for case,_ in bodies})
    report['screen_failures']=failed
    if not a.screen and gen.generate()!=(ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError('generated body recipes drifted')
    if a.mutations:
        with tempfile.TemporaryDirectory() as temp:
            report['mutants']=mutations(Path(temp),bodies,links)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'families':report['families'],'body_types':len(report['body_types']),
                      'screen_failures':len(failed),'mutants':report.get('mutants',{})}))
if __name__=='__main__':main()
