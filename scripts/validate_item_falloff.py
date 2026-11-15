#!/usr/bin/env python3
"""RENDER-ITEMS-002AA: checked clock falloff branches and complete item bodies."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess

import gen_item_bodies as gen
import pins
import validate_item_groups as groups
import validate_item_quality as quality
import validate_item_read_programs as read
import validate_item_direct_bodies as direct
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.FALLOFF_TYPES
# Every tick of every period read by these bodies, including their unbranched UV chains.
PERIODS = {0x0b47: 5001, 0x0b49: 2301, 0x1323: 4001, 0x154a: 5001}
MUTANTS = {
    'falloff-threshold': ('f = f >= kf ? top - f : 1.0f;', 'f = f >= kf + 0.1f ? top - f : 1.0f;'),
    'falloff-reverse': ('f = f >= kf ? top - f : 1.0f;', 'f = f >= kf ? f - top : 1.0f;'),
    'falloff-default': ('f = f >= kf ? top - f : 1.0f;', 'f = f >= kf ? top - f : 0.0f;'),
    'falloff-zero': ('if (f <= 0.0f) f = 0.0f;', 'if (f <= 0.0f) f = -f;'),
}


def reader_controls(wa):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    start = 0x01723b8c
    code = list(md.disasm(wa[0][start-0x401000:0x01723c39-0x401000], start))
    selected = [i for i in code if i.mnemonic == 'jb' or
                (i.mnemonic in ('divss', 'movss') and i.address in (0x1723c0d, 0x1723be4, 0x1723c15))]
    assert len(selected) == 5
    def has_falloff(words):
        gen._slices.clear()
        return any(op == gen.C_F_FALLOFF for p in gen.slice_block(words, start)[1] for op, _ in p[2])
    assert has_falloff(wa)
    for insn in selected:
        raw = bytearray(wa[0])
        raw[insn.address - 0x401000 + insn.size - 1] ^= 1
        if has_falloff((raw,) + wa[1:]):
            raise AssertionError(('reader accepted altered branch', hex(insn.address)))
    gen._slices.clear()
    return len(selected)


def compare(wa, lib, count):
    groups.TYPES = TYPES
    families, vectors = groups.compare(wa, lib, count)
    reset = ResetWorld(wa, quality.RandomWorld)
    for family in ('clocks', 'ticks'):
        before = len(vectors)
        for t in TYPES:
            rng = random.Random(0x200ab + t)
            clocks = read.CLOCKS if family == 'clocks' else range(PERIODS[t] if count == 292 else min(count, PERIODS[t]))
            for index, clock in enumerate(clocks):
                case = v.random_case_any(rng, t)
                case.update(time=v.f2u(clock), item_level=(0, 7, 13)[index % 3] << 3,
                            quality=9, record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff,
                            frame=rng.randrange(1 << 32))
                sequence = quality.sequence_for(rng)
                ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError((family, hex(t), index, case, expected, detail))
                vectors.append((case, sequence, expected))
        families[family] = {'cases': len(vectors) - before, 'mismatches': 0}
    exits = []
    for t in TYPES:
        for _, case in list(quality.state_cases(t))[:64]:
            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = [0] * 64, 0
                return world
            result, original_stream, other, machine = v.client_stream(wa, case, factory)
            expected = (tuple(machine.r32(v.MODEL + 0x54 + 4*k) for k in range(3)) +
                        (machine.r32(v.MODEL + 0x40),) +
                        tuple(machine.r32(v.MODEL + 0x44 + 4*k) for k in range(3)) +
                        (machine.read(v.MODEL + 0xca, 1)[0],))
            status, stream, actual = direct.c_model(lib, case)
            if not result['ok'] or other or status or stream != original_stream or actual != expected:
                raise AssertionError(('exits', hex(t), expected, actual))
            exits.append((case, expected))
    families['exits'] = {'cases': len(exits), 'mismatches': 0}
    return families, vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=292)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.cases <= 292:
        parser.error('--cases must be in 1..292')
    subprocess.run(['make', '-s', '-j4', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    families, vectors = compare(wa, C.CDLL(str(v.LIBRARY)), args.cases)
    families['reader_refusals'] = {'cases': reader_controls(wa), 'mismatches': 0}
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        groups.MUTANTS = MUTANTS
        report['mutants'] = groups.mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
