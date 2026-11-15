#!/usr/bin/env python3
"""Compare all admitted low-level callers with the pinned RenderObjDraw instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess

import gen_item_bodies as gen
import item_caller_groups as callers
import pins
import validate_item_groups as groups
import validate_item_quality as quality
import validate_item_read_programs as read
import validate_item_direct_bodies as direct
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = callers.TYPES
MUTANTS = {
    'caller-threshold': ('if (level < 3 && caller_light != 0.0f)', 'if (level < 2 && caller_light != 0.0f)'),
    'caller-light': ('L[k] * caller_light;', 'L[k];'),
    'caller-first-alpha': ('body_color(&s, 1.5f, keep | 0x240u, 1.5f, -1);', 'body_color(&s, 1.0f, keep | 0x240u, 1.5f, -1);'),
    'caller-first-bright': ('body_color(&s, 1.5f, keep | 0x240u, 1.5f, -1);', 'body_color(&s, 1.5f, keep | 0x240u, 1.0f, -1);'),
    'caller-flags': ('body_color(&s, 1.0f, keep | 0x1040u, 1.0f, -1);', 'body_color(&s, 1.0f, 0x1040u, 1.0f, -1);'),
    'caller-order': ('body_color(&s, 1.0f, keep | 0x1040u, 1.0f, -1);', ''),
    'helper-carry': ('mu_rc_body_types[type].carry)', '0)'),
}


def reader_controls(wa):
    """Changes to the caller gate, member, light and ordered call must all refuse."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    offsets = []
    for start, end, mnemonic, operand in (
        (0x17de3e4, 0x17de3fd, 'cmp', '3'),
        (0x17de5d9, 0x17de5f5, 'cmp', '0x2710'),
        (0x17de718, 0x17de873, 'mulss', '[0x1a7edac]'),
        (0x17de4d2, 0x17de5d9, 'or', '0x240'),
        (0x17de4d2, 0x17de5d9, 'call', '0x16dec15'),
    ):
        insn = next(i for i in md.disasm(wa[0][start-0x401000:end-0x401000], start)
                    if i.mnemonic == mnemonic and i.op_str.endswith(operand))
        offsets.append(insn.address - 0x401000 + insn.size - 1)
    for offset in offsets:
        text = bytearray(wa[0])
        text[offset] ^= 1
        try:
            callers.read((text, wa[1]))
        except ValueError:
            continue
        raise AssertionError(('reader accepted altered instruction', hex(offset + 0x401000)))
    return len(offsets)


def compare(wa, lib, count):
    groups.TYPES = TYPES
    families, vectors = groups.compare(wa, lib, count)
    reset = ResetWorld(wa, quality.RandomWorld)
    before = len(vectors)
    exits = []
    for t in TYPES:
        rng = random.Random(0x200aa + t)
        for level in range(16):
            for q in (0, 1, 2, 9):
                case = v.random_case_any(rng, t)
                case.update(item_level=level << 3, quality=q, time=v.f2u(read.CLOCKS[(level*4+q) % len(read.CLOCKS)]),
                            frame=rng.randrange(1 << 32), record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff)
                sequence = quality.sequence_for(rng)
                ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError(('clocks', hex(t), level, q, case, expected, detail))
                vectors.append((case, sequence, expected))
                # Explicit model-exit comparison with zero scripted random values.
                def factory(*args):
                    world = reset(*args)
                    world.sequence, world.drawn = [0] * 64, 0
                    return world
                result, original_stream, other, machine = v.client_stream(wa, case, factory)
                original = (tuple(machine.r32(v.MODEL + 0x54 + 4*k) for k in range(3)) +
                            (machine.r32(v.MODEL + 0x40),) +
                            tuple(machine.r32(v.MODEL + 0x44 + 4*k) for k in range(3)) +
                            (machine.read(v.MODEL + 0xca, 1)[0],))
                status, stream, actual = direct.c_model(lib, case)
                if not result['ok'] or other or status or stream != original_stream or actual != original:
                    raise AssertionError(('exits', hex(t), level, q, original, actual))
                exits.append((case, original))
    families['clocks'] = {'cases': len(vectors) - before, 'mismatches': 0}
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
    rows = callers.read(wa)
    assert (ROOT/'reconstructed/renderchar/item_caller_groups.h').read_text() == callers.render(rows)
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
