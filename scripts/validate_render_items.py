#!/usr/bin/env python3
"""RENDER-ITEMS-002 part 1: compiled C vs original RenderItem3D in Unicorn.

Records every RenderObjectScreen argument and the angle global, bit for bit.
Engine/UI/TRS queries are synthetic inputs. No runtime jump is repaired.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

import gen_item3d as gen
import pins
import validate_hud as vh

ROOT = Path(__file__).resolve().parents[1]
CODES = sorted(set(gen.CODES) | set(range(0x1a47, 0x1a4c)) | {0x1c64})


def authored(lib, inp):
    out = vh.Item3dOut()
    status = lib.mu_item3d(ctypes.byref(inp), ctypes.byref(out))
    if status != 1:
        return status, []
    return status, [tuple(v & 0xffffffff for v in (out.model, out.level_word, out.excellent, out.set_bits)) +
                    tuple(vh.F(v) for v in out.position) +
                    tuple(v & 0xffffffff for v in (out.select, out.a28, out.a2c, out.a30)) +
                    (vh.F(out.scale), out.a44 & 0xffffffff, out.a48 & 0xffffffff) +
                    tuple(vh.F(v) for v in out.angle)]


def compare(text, data, lib, repeats):
    client = vh.Client(text, data)
    stops = vh.ITEM3D_STOPS | {0xf2c0d5}
    client.prepare((0x16c154e,), stops)
    client.common_stubs()
    m = client.machine
    rng, vectors = random.Random(0x2002), []
    families = {}
    for code in CODES + [-1, 0, 0x1a46, 0x1a4c, 0x1c2d, 0x1c31, 0x1c65]:
        family = ('spin' if 0x1a47 <= code <= 0x1a4b else 'window' if code == 0x1c64 else
                  'box' if code == 0x1c0b else 'overrides' if code in CODES else 'generic')
        tally = families.setdefault(family, {'cases': 0, 'mismatches': 0})
        for level in [-1] + list(range(18)) + [31]:
            if code == 0x1c0b and level > 7:
                continue  # the jump is outside restored text; separately tested refusal
            for variation in range(repeats):
                client.reset()
                inp = vh.Item3dIn()
                inp.code, inp.level_word = code, level * 8 | rng.randrange(8)
                inp.x, inp.y, inp.w, inp.h = 40.125, 60.25, 24.5, 43.75
                inp.excellent, inp.set_bits = rng.randrange(3), rng.randrange(256)
                inp.a28, inp.a2c, inp.a30, inp.a44, inp.a48 = 1, -1, 23, 4, 5
                inp.code2 = 123
                inp.trs = vh.ItemTRS(0.37, 0.81, (ctypes.c_float*3)(27, -19, 48), 0.0043)
                inp.scale_override = [0, 0.02, -0.01][variation % 3]
                inp.select, inp.no_select, inp.flip_y = variation & 1, (variation >> 1) & 1, (variation >> 2) & 1
                inp.gfx_busy, inp.cursor_in = rng.randrange(2), rng.randrange(2)
                inp.ui_3e_visible, inp.ui_b602 = rng.randrange(2), rng.randrange(2)
                inp.kind_a_22, inp.kind_b_6a, inp.code2_kind_b_6a = (rng.randrange(2) for _ in range(3))
                inp.time = rng.uniform(-1000, 1000000)
                inp.special_window_active = (variation >> 1) & 1
                inp.frame_scale, inp.rate_x, inp.rate_y = 1.25, 640/1722, 480/1048
                gfx, scale, trs, ui, win = (m.alloc(0x300, define=True) for _ in range(5))
                m.put32(gfx + 0xd4, ui)
                m.put32(gfx + 0xa0, scale)
                m.putf(scale + 0x58, inp.frame_scale)
                m.putf(gfx + 0x2cc, inp.rate_x)
                m.putf(gfx + 0x2d0, inp.rate_y)
                m.write(trs, bytes(inp.trs))
                m.write(win + 0x1c, bytes([inp.special_window_active]))
                m.putf(0x6fce370, inp.time)
                m.stub(0xac3bf7, lambda mm: gfx, 0)
                m.stub(0xc08654, lambda mm: inp.gfx_busy, 0)
                m.stub(0xec4bf2, lambda mm: inp.cursor_in, 0)
                m.stub(0xf2bb92, lambda mm: ui, 0)
                m.stub(0xf2aba9, lambda mm: inp.ui_3e_visible, 4)
                m.stub(0xf2b602, lambda mm: inp.ui_b602, 0)
                m.stub(0xf2c0d5, lambda mm: win, 0)
                m.stub(0x11204db, lambda mm: trs, 4)
                m.stub(0xcd4ea8, lambda mm: ui, 0)
                m.stub(0xcd6017, lambda mm: (inp.kind_b_6a if mm.args(2)[0] == code & 0xffffffff else
                                            inp.code2_kind_b_6a) if mm.args(2)[1] == 0x6a else 0, 8)
                m.stub(0xcd5fac, lambda mm: inp.kind_a_22 if mm.args(2)[1] == 0x22 else 0, 8)
                observed = []

                def ros(mm):
                    args = mm.args(12)
                    observed.append(tuple(args[:4]) + struct.unpack('<3I', mm.read(args[4], 12)) +
                                    tuple(args[5:]) + struct.unpack('<3I', mm.read(vh.ITEM_ANGLE, 12)))
                    return 0
                m.stub(0x16c2d82, ros, 0)
                args = [vh.F(v) for v in (inp.x, inp.y, inp.w, inp.h)] + [
                    code, inp.level_word, inp.excellent, inp.set_bits, inp.a28, inp.a2c, inp.a30,
                    inp.select, vh.F(inp.scale_override), inp.flip_y, inp.no_select, inp.a44, inp.a48, inp.code2]
                m.call(0x16c154e, tuple(a & 0xffffffff for a in args))
                expected_status = 0 if code == -1 else 1
                result = authored(lib, inp)
                tally['cases'] += 1
                if result != (expected_status, observed):
                    tally['mismatches'] += 1
                    raise AssertionError((hex(code), level, variation, observed, result))
                vectors.append((bytes(inp), result))
    return families, vectors


def mutants(vectors):
    source = (ROOT/'reconstructed/hud/item_slots.c').read_text()
    changes = {
        'model': ('model = r->model;', 'model = r->model + 1;'),
        'level_word': ('level_word = r->level_word;', 'level_word = in->level_word;'),
        'spin': ('angle[1] = in->time * 0.2f', 'angle[1] = in->time * 0.1f'),
        'selection': ('in->special_window_active)', 'in->special_window_active && !in->no_select)'),
        'offset': ('fx = r->values[0];', 'fx = in->trs.offset_x;'),
        'scale': ('scale = r->values[5];', 'scale = in->scale_override;'),
    }
    caught = {}
    with tempfile.TemporaryDirectory(prefix='mu-render-items-mutants-') as tmp:
        for name, (before, after) in changes.items():
            assert source.count(before) == 1
            path = Path(tmp)/f'{name}.c'
            path.write_text(source.replace(before, after))
            output = Path(tmp)/f'{name}.dylib'
            subprocess.run(['clang', '-std=c11', '-O2', '-ffp-contract=off', '-fno-fast-math', '-shared', '-fPIC',
                            '-I', str(ROOT/'reconstructed/hud'), str(path), '-o', str(output)], check=True)
            lib = vh.slot_lib(ctypes.CDLL(str(output)))
            count = sum(authored(lib, vh.Item3dIn.from_buffer_copy(raw)) != expected for raw, expected in vectors)
            caught[name] = count
            assert count > 0, f'undetected mutant {name}'
    return caught


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repeats', type=int, default=8)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    assert args.repeats >= 8, 'at least 8 variants cover select/no_select/flip'
    text, data = pins.TEXT.read(), pins.DATA.read()
    assert gen.generate(text, data) == (ROOT/'reconstructed/hud/item3d_overrides.h').read_text()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/hud')], check=True)
    lib = vh.slot_lib(ctypes.CDLL(str(ROOT/('reconstructed/hud/libmu_hud.' + ('dylib' if sys.platform == 'darwin' else 'so')))))
    families, vectors = compare(text, data, lib, args.repeats)
    report = {'families': families, 'special_codes': len(CODES),
              'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'routine_sha256': hashlib.sha256(text[0x16c154e-0x401000:0x16c23d5-0x401000]).hexdigest(),
              'unsupported': '0x1c0b signed level >7: 0x016c1afc -> 0x10b3f080, not executed',
              'mutants': mutants(vectors) if args.mutations else {}}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
