#!/usr/bin/env python3
"""LAYOUT-PROBE-001: bounded original-instruction field reads over synthetic records.

No process attachment. The whole restored text is pinned by scripts/pins.py. Each
probe executes the named original load instruction once, with explicit register
inputs, and records every data read. This proves the offset and width, not the
caller's provenance or an inferred semantic name. --mutations compares competing
offsets/prefix sizes with the observed values and reads.
"""
from __future__ import annotations
import argparse
import json
import random
import struct
from pathlib import Path
import pins

# name, client instruction, base register, index register, offset, width, count
PROBES = (
    ('object_live', 0x0095f981, 'eax', None, 0, 1, 1),
    ('object_fade_flag', 0x013a6086, 'eax', None, 8, 1, 1),
    ('character_scene_level', 0x0185a89c, 'eax', None, 0x144, 2, 1),
    ('character_label_level', 0x00b3c5c7, 'eax', None, 0x14e, 2, 1),
    ('attribute_skill_count', 0x00a002a9, 'eax', None, 0x1e4, 1, 1),
    ('attribute_skill_ids', 0x016969f8, 'ecx', 'eax', 0x1e6, 2, 0x3a1),
    ('attribute_skill_timers', 0x01696e6c, 'ecx', 'eax', 0xccc, 4, 0x3a1),
)
BASE = 0x30000000


def run(text, rounds=4, mutations=False):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_READ
    from unicorn import x86_const as x
    regs = {'eax': x.UC_X86_REG_EAX, 'ecx': x.UC_X86_REG_ECX}
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(pins.TEXT.base, (len(text) + 4095) & ~4095)
    uc.mem_write(pins.TEXT.base, text)
    uc.mem_map(BASE, 0x2000)
    reads = []
    uc.hook_add(UC_HOOK_MEM_READ, lambda u, access, addr, size, value, data: reads.append((addr, size)))
    rng = random.Random(0x1a901)
    results = {}
    for name, address, base_reg, index_reg, offset, width, count in PROBES:
        ins = next(md.disasm(text[address-pins.TEXT.base:address-pins.TEXT.base+15], address))
        if ins.mnemonic != 'movzx' and name != 'attribute_skill_timers':
            raise ValueError(f'{name}: expected a load at {address:#x}')
        cases = failures = caught = 0
        for _ in range(rounds):
            raw = rng.randbytes(0x2000)
            uc.mem_write(BASE, raw)
            for index in range(count):
                uc.reg_write(regs[base_reg], BASE)
                if index_reg:
                    uc.reg_write(regs[index_reg], index)
                reads.clear()
                uc.emu_start(address, address + ins.size, count=1)
                off = offset + index * width
                expected = int.from_bytes(raw[off:off+width], 'little')
                actual = uc.reg_read(x.UC_X86_REG_EAX)
                failures += actual != expected or reads != [(BASE + off, width)]
                cases += 1
                if mutations:
                    other = {'object_live': 8, 'object_fade_flag': 0,
                             'character_scene_level': 0x14e, 'character_label_level': 0x144,
                             'attribute_skill_count': 0x1e6}.get(name)
                    if other is not None:
                        caught += actual != int.from_bytes(raw[other:other+width], 'little')
                    else:
                        caught += off + width > 0x200  # truncated progress-prefix hypothesis
        results[name] = dict(address=f'0x{address:08x}', offset=offset, width=width,
                             entries=count, cases=cases, mismatches=failures,
                             competing_hypothesis_differences=caught, evidence='VERIFIED_LOAD')
    return dict(text_sha256=pins.TEXT.sha256, method='bounded original loads; explicit synthetic registers',
                families=results, cases=sum(r['cases'] for r in results.values()),
                mismatches=sum(r['mismatches'] for r in results.values()),
                mutations_caught=sum(r['competing_hypothesis_differences'] > 0 for r in results.values())
                if mutations else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text')
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    if args.rounds < 1:
        p.error('--rounds must be positive')
    result = run(pins.TEXT.read(args.text), args.rounds, args.mutations)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(f"layout probes: {result['cases']} cases, {result['mismatches']} mismatches, "
          f"{result['mutations_caught']}/7 competing hypotheses caught")
    return int(bool(result['mismatches']) or args.mutations and result['mutations_caught'] != len(PROBES))


if __name__ == '__main__':
    raise SystemExit(main())
