#!/usr/bin/env python3
"""RENDER-ITEMS-002AA: optional packed-level words and quantized body colour programs."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import re
import subprocess

import gen_item_bodies as gen
import pins
import validate_item_groups as groups
import validate_item_direct_bodies as direct
import validate_item_quality as quality
import validate_item_read_programs as read
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.RANDOM_LEVEL_TYPES
MUTANTS = {
    'packed-decode': ('level_split == 2 ? s->item->item_level >= 9 :', 'level_split == 2 ? ((s->item->item_level >> 3) & 15) >= 9 :'),
    'packed-low-bits': ('level_split == 2 ? s->item->item_level >= 9 :', 'level_split == 2 ? s->item->item_level >= 16 :'),
    'packed-zero': ('level_split == 2 ? s->item->item_level >= 9 :', 'level_split == 2 ? s->item->item_level >= 0 :'),
    'packed-quality': ('s->item->quality > 1 && mu_rc_item_glow_level(s->item) >= 9 &&', 's->item->quality > 2 && mu_rc_item_glow_level(s->item) >= 9 &&'),
    'packed-record': ('s->item->quality > 1 && mu_rc_item_glow_level(s->item) >= 9 &&', 's->item->quality > 1 && mu_rc_item_glow_level(s->item) >= 11 &&'),
    'random-phase': ('if (p->phases & (1u << phase))', 'if (p->phases)'),
    'random-source': ('random_program(p, rank5_random(s))', 'random_program(p, 0)'),
}


def caller_guards(wa):
    """Each admitted type reaches the original signed packed-word guard.

    Both high-level callers push the unshifted RenderObjDraw argument +0x18.
    The low path supplies -1. The explicit packed-nine forcing case separates
    this ABI word from the decoded level and from the effective glow level.
    """
    from unicorn import UC_HOOK_CODE
    for at in (0x017e1f12, 0x017e25ea):
        assert gen._text(wa, at, 3) == bytes.fromhex('ff7518')
    addresses = []
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for match in re.finditer(re.escape(bytes.fromhex('837d2809')), wa[0]):
        at = match.start() + 0x401000
        if not 0x016e036c <= at < 0x0176cb3b:
            continue
        code = list(md.disasm(wa[0][match.start():match.start()+24], at))
        if len(code) < 3 or (code[0].mnemonic, code[0].op_str) != ('cmp', 'dword ptr [ebp + 0x28], 9'):
            continue
        if code[1].mnemonic == 'jl':
            # The lower-level path joins the enclosing vector restore/cleanup.
            target = code[1].operands[0].imm if md.detail else int(code[1].op_str, 16)
            if at < target < 0x0176cb3b:
                addresses.append(at)
        elif (code[1].mnemonic == 'jge' and code[2].mnemonic == 'jmp' and
              int(code[1].op_str, 16) == code[2].address + code[2].size and
              0x016e036c <= int(code[2].op_str, 16) < 0x0176cb3b):
            addresses.append(at)
    assert addresses
    seen = []
    class World(quality.RandomWorld):
        def install(self):
            super().install()
            def guard(uc, address, size, context):
                ebp = uc.reg_read(self.m.x86.UC_X86_REG_EBP)
                seen.append((address, gen._i32(self.m.r32(ebp + 0x28))))
            for address in addresses:
                self.m.uc.hook_add(UC_HOOK_CODE, guard, begin=address, end=address)
    reset = ResetWorld(wa, World)
    rows = []
    for t in TYPES:
        observed = set()
        for packed, record, q, expected in ((0, (0, 0, 0), 9, -1), (104, (0, 0, 0), 9, 104),
                                            (9, (0, 0x26, 0), 2, 9)):
            case = v.classify_case(t, v.CLASSIFY[0])
            case.update(item_level=packed, record=record, quality=q)
            seen.clear()
            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = [0] * 64, 0
                return world
            result, _, other, _ = v.client_stream(wa, case, factory)
            if not result['ok'] or other or not seen or seen[0][1] != expected:
                raise AssertionError(('original packed caller', hex(t), packed, expected, seen, result, other))
            observed.update(address for address, _ in seen)
            rows.append({'type': hex(t), 'packed': packed, 'guards': [(hex(a), n) for a, n in seen]})
        if len(observed) != 1:
            raise AssertionError(('nonuniform guard', hex(t), observed))
    return {'cases': len(rows), 'mismatches': 0, 'rows': rows}


def compare(wa, lib, count):
    groups.TYPES = TYPES
    families, vectors = groups.compare(wa, lib, count)
    reset = ResetWorld(wa, quality.RandomWorld)
    before = len(vectors)
    packed_values = tuple(range(128)) + (-1, -128, -2147483648, 128, 129, 255, 256, 257, 2147483647) if count == 292 else (0, 1, 8, 9, 10, 15, 16, 55, 56, 63, 64, 71, 72, 95, 96, 103, 104, 127)
    for t in TYPES:
        rng = random.Random(0x200ac + t)
        for packed in packed_values:
            for q in (0, 1, 2, 9):
                for b in (0, 0x26, 0x5b):
                    case = v.random_case_any(rng, t)
                    case.update(item_level=packed, quality=q, record=((packed & 1)*6, b, 0),
                                render_type=(2, 0x102, 0x40042, 0x402)[(packed+q+b) % 4],
                                a10=0xffffffff, a11=0xffffffff, frame=rng.randrange(1 << 32))
                    sequence = quality.sequence_for(rng)
                    ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                    if not ok:
                        raise AssertionError(('packed', hex(t), packed, q, b, case, expected, detail))
                    vectors.append((case, sequence, expected))
    families['packed'] = {'cases': len(vectors) - before, 'mismatches': 0}
    quality.TYPES = TYPES
    families['random'], extra = quality.random_cases(wa, lib)
    vectors += extra
    before = len(vectors)
    for t in TYPES:
        rng = random.Random(0x200ad + t)
        for clock in read.CLOCKS:
            case = v.random_case_any(rng, t)
            case.update(time=v.f2u(clock), item_level=13 << 3, quality=9, record=(0, 0, 0),
                        a10=0xffffffff, a11=0xffffffff)
            sequence = quality.sequence_for(rng)
            ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
            if not ok:
                raise AssertionError(('clocks', hex(t), clock, case, expected, detail))
            vectors.append((case, sequence, expected))
    families['clocks'] = {'cases': len(vectors) - before, 'mismatches': 0}
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
    families['caller_guards'] = caller_guards(wa)
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
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        groups.MUTANTS = MUTANTS
        report['mutants'] = groups.mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
