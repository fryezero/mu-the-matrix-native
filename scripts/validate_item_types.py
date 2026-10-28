#!/usr/bin/env python3
"""RENDER-ITEMS-002b: scalar remaps, complete body streams and bow link sprites.

Compiled production reconstruction versus pinned original instructions. Engine
services retain validate_renderchar's declared synthetic state. Link effects
are compared at 0x0150e746, including dereferenced colours and sheet contents.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

import gen_item_glow as gen
import pins
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
BODY = (0x12ed, 0x12f5, *range(0x22e6, 0x22ec), 0x22f1, 0x248c, 0x248d)
LINK = (0x12ea, 0x12eb, 0x12ec, 0x12f7, 0x1301, 0x1303)


class Sprite(C.Structure):
    _fields_ = [('bone', C.c_int32), ('bitmap', C.c_int32), ('scale', C.c_float),
                ('light', C.c_float * 3), ('rotation', C.c_float), ('blend', C.c_int32), ('axes', C.c_int32)]


def c_link(lib, t, rand):
    out, n = (Sprite * 10)(), C.c_int32()
    status = lib.mu_rc_link_sprites(t, rand, out, 10, C.byref(n))
    return status, [(s.bitmap, s.bone, v.f2u(s.scale), tuple(v.f2u(x) for x in s.light),
                     v.f2u(s.rotation), s.blend, s.axes) for s in out[:n.value]]


def scalar_cases(text, lib, types=range(0xae6, 0x2ae6)):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_EIP
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(0x401000, (len(text) + 4095) & ~4095)
    u.mem_write(0x401000, text)
    u.mem_map(0x20000000, 8192)
    bp = 0x20001000
    u.reg_write(UC_X86_REG_EBP, bp)
    tally = {'cases': 0, 'mismatches': 0}
    for t in types:
        u.mem_write(bp + 12, struct.pack('<i', t))
        it = v.CItem(type=t, render_type=2, quality=9)
        for level in range(16):
            u.mem_write(bp - 0xa8, struct.pack('<i', level))
            u.emu_start(gen.START, gen.END, count=256)
            if u.reg_read(UC_X86_REG_EIP) != gen.END:
                raise RuntimeError('scalar chain did not close')
            expected = struct.unpack('<i', u.mem_read(bp - 0xa8, 4))[0]
            it.item_level = level << 3
            actual = lib.mu_rc_item_glow_level(C.byref(it))
            tally['cases'] += 1
            tally['mismatches'] += actual != expected
    return tally


def body_cases(wa, lib):
    rng, vectors = random.Random(0x2002b), []
    tally = {'cases': 0, 'mismatches': 0, 'types': len(BODY)}
    for t in BODY:
        for k in range(292):  # 16 levels x 12 states, then 100 random states
            case = v.random_case_any(rng, t)
            if k < 192:
                state, level = divmod(k, 16)
                case.update(item_level=(level << 3) | (state % 8), quality=(0, 1, 2, 3, 4, 5)[state % 6],
                            render_type=(2, 0x102, 0x402, 0x40042)[state % 4],
                            option1=state % 3, ext=(0, 1, 2, 0x10, 0x20, 0x33)[state % 6])
            case['record'] = rng.choice([None, (0, 0, 0), (6, 0, 0), (0, 0x26, 0), (0, 0x5b, 0)])
            result, stream, other, m = v.client_stream(wa, case)
            status, actual = v.c_stream(lib, case)
            good = result['ok'] and status == 0 and actual == stream and not other
            tally['cases'] += 1
            tally['mismatches'] += not good
            if not good:
                raise AssertionError((hex(t), k, result, case, stream, actual, other))
            vectors.append((case, stream))
    return tally, vectors


def link_cases(wa, lib):
    vectors = []
    tally = {'cases': 0, 'mismatches': 0, 'types': len(LINK)}
    for t in LINK:
        for rand in [*range(30), 30, 59, 32767]:
            for variant in range(4):
                w = v.link_world(wa, t)
                m = w.m
                observed = []
                m.stub(0x01989721, lambda mm: rand, 0)
                def sprite(mm):
                    a = [mm.arg(i) for i in range(9)]
                    sheet = mm.read(a[8], 12)
                    if sheet != struct.pack('<iif', 1, 1, 1.0):
                        raise AssertionError(('sheet', sheet.hex()))
                    if a[0] != v.MODEL:
                        raise AssertionError(('model/owner', a))
                    observed.append((a[1], a[2], a[3], struct.unpack('<3I', mm.read(a[4], 12)), a[6], a[7], 4))
                    return 0
                m.stub(0x0150e746, sprite, 0)
                part = v.CHAR + 0x19ac
                m.write(part, struct.pack('<hBBBB', t, variant * 4, variant & 1, 0, 47))
                result = m.run(0x012bd910, [0, 0, v.f2u(15), v.CHAR, part, t, variant * 4,
                                           variant & 1, variant & 1, 1, 0, variant >> 1])
                status, actual = c_link(lib, t, rand)
                good = result['ok'] and status == 0 and actual == observed
                tally['cases'] += 1
                tally['mismatches'] += not good
                if not good:
                    raise AssertionError((hex(t), rand, variant, result, observed, actual))
                vectors.append((t, rand, observed))
    return tally, vectors


def helper_cases(wa):
    """Execute 0x0150e746 including real TransformPosition; compare shared C math."""
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/particles')], check=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = C.CDLL(str(ROOT/f'reconstructed/particles/libclient_particles.{suffix}'))
    lib.mu_pt_transform_position.argtypes = [C.POINTER(C.c_float)] * 3 + [C.c_int, C.c_float, C.POINTER(C.c_float)]
    rng, tally = random.Random(0x150e746), {'cases': 0, 'mismatches': 0}
    for _ in range(100):
        w = v.World(*wa)
        m = w.m
        m.uc.hook_del(m.hooks.pop(0x0150e746))
        del m.stubs[0x0150e746]
        w.add_model(0x12ec, v.MODEL, bones=32)
        bone = rng.randrange(32)
        matrix = [rng.uniform(-30, 30) for _ in range(12)]
        origin = [rng.uniform(-100, 100) for _ in range(3)]
        scale = v.u2f(v.f2u(rng.uniform(0.1, 3)))
        m.ensure(0x06fce398, 32 * 48)
        m.write(0x06fce398 + bone * 48, struct.pack('<12f', *matrix))
        m.wf(v.MODEL + 0x74, scale)  # TransformPosition's BodyScale
        m.write(v.MODEL + 0x78, struct.pack('<3f', *origin))
        observed = []
        m.stub(0x01692eb7, lambda mm: observed.append(struct.unpack('<3I', mm.read(mm.arg(1), 12))) or 0, 0)
        m.write(v.LIGHT, struct.pack('<3f', 0.4, 0.5, 0.6))
        m.write(v.ENCH, struct.pack('<iif', 1, 1, 1))
        result = m.run(0x0150e746, [v.MODEL, 0x7f67, bone, v.f2u(1), v.LIGHT, v.CHAR, 0, 0, v.ENCH])
        out = v.F3()
        lib.mu_pt_transform_position((C.c_float*12)(*matrix), v.F3(), out, 1, scale, v.F3(*origin))
        good = result['ok'] and observed == [tuple(v.f2u(x) for x in out)]
        tally['cases'] += 1
        tally['mismatches'] += not good
        if not good:
            raise AssertionError(('helper', result, observed, list(out)))
    return tally


def mutants(directory, bodies, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'remap-order': ('level = mu_rc_glow_rows[i].levels[level];', 'level = 0;'),
        'wing-pulse': ('pulse + 1.1f;', 'pulse + 1.0f;'),
        'weapon-hidden': ('emit(s, MU_RC_ENTRY_BODY, 0, flags, alpha, -1, -1);\n        return;',
                          'emit(s, MU_RC_ENTRY_BODY, 0, flags, alpha, a6, -1);\n        return;'),
        'link-bone': ('13 + i : 5 + i - 6', '12 + i : 5 + i - 6'),
        'link-intensity': ('* 0.005f;', '* 0.01f;'),
        'link-extra': ('extra ? 10 : 6', 'extra ? 9 : 6'),
    }
    results = {}
    for name, (old, new) in changes.items():
        if source.count(old) != 1:
            raise AssertionError(('mutant anchor', name, source.count(old)))
        path = directory/f'{name}.c'
        path.write_text(source.replace(old, new))
        dylib = directory/f'{name}.dylib'
        subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                        '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                        str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(dylib)], check=True)
        lib = C.CDLL(str(dylib))
        detected = sum(v.c_stream(lib, case) != (0, expected) for case, expected in bodies)
        detected += sum(c_link(lib, t, r) != (0, expected) for t, r, expected in links)
        results[name] = detected
        if not detected:
            raise AssertionError(('surviving mutant', name))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    text, data, flag, feature = pins.TEXT.read(), pins.DATA.read(), pins.FLAG.read(), pins.FEATURE.read()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    if gen.generate(text) != (ROOT/'reconstructed/renderchar/item_glow.h').read_text():
        raise AssertionError('generated table drift')
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'remap_sha256': hashlib.sha256(text[gen.START-0x401000:gen.END-0x401000]).hexdigest(),
              'body_types': list(BODY), 'link_types': list(LINK), 'remap_rows': 103, 'families': {}}
    families = report['families']
    families['remaps'] = scalar_cases(text, lib)
    families['bodies'], bodies = body_cases((text, data, flag, feature), lib)
    families['links'], links = link_cases((text, data, flag, feature), lib)
    families['bone_helper'] = helper_cases((text, data, flag, feature))
    if args.mutations:
        with tempfile.TemporaryDirectory() as tmp:
            report['mutants'] = mutants(Path(tmp), bodies, links)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(any(f['mismatches'] for f in families.values()))


if __name__ == '__main__':
    raise SystemExit(main())
