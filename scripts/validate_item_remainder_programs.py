#!/usr/bin/env python3
"""RENDER-ITEMS-002AA: five complete pre-draw producers and their body streams."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess

import gen_item_owner_fx as fxgen
import pins
import validate_item_predraw as pre
import validate_item_quality as quality
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = fxgen.REMAINDER_PROGRAM_TYPES
CLOCKS = (-2147483648.0, -123456.75, -6284.0, -2001.0, -2000.0, -1999.0,
          -1001.0, -1000.0, -999.0, -1.0, -0.0, 0.0, 1.0, 999.0, 1000.0, 1001.0,
          1569.0, 1570.0, 1999.0, 2000.0, 2001.0, 123456.75, 2147483520.0, 2147483648.0)
MUTANTS = {name: pre.MUTANTS[name] for name in (
    'body-carry', 'pre-hook', 'visible', 'named', 'particle-owner', 'frame', 'sprite-domain')}



def records(t):
    rng = random.Random(0x20079 + t)
    for kind_b in (0x26, 0x5b):
        for quality_value in (0, 1, 2, 9):
            for level in range(16):
                for option, ext in ((0, 0), (1, 1)):
                    for kind_a in (0, 6):
                        case = v.random_case_any(rng, t)
                        case.update(item_level=level << 3, quality=quality_value, option1=option, ext=ext,
                                    record=(kind_a, kind_b, 0), a10=0xffffffff, a11=0xffffffff)
                        yield case


def compare(wa, lib, count=292):
    reset, vectors, families = ResetWorld(wa, quality.RandomWorld), [], {}
    for family in ('bodies', 'records', 'clocks'):
        before = len(vectors)
        for t in TYPES:
            if family == 'bodies':
                cases = [case for _, case in quality.state_cases(t)]
            elif family == 'records':
                cases = list(records(t))
            else:
                rng = random.Random(0x2007a + t)
                cases = [dict(v.random_case_any(rng, t), time=v.f2u(clock), record=(0, 0, 0),
                              a10=0xffffffff, a11=0xffffffff)
                         for clock in CLOCKS]
            if count < 292:
                cases = cases[:count]
            for index, case in enumerate(cases):
                sequence = [0] * 64
                def factory(*args):
                    world = reset(*args)
                    world.sequence, world.drawn = sequence, 0
                    return world
                result, expected, other, _ = v.client_stream(wa, case, factory)
                status, actual, used = quality.run_c(lib, case, sequence)
                if not result['ok'] or any(call[0] != 'effect' for call in other) or status or actual != expected:
                    raise AssertionError((family, hex(t), index, case, result, other, status, expected, actual))
                vectors.append(('body', case, sequence, expected))
        families[family] = {'cases': len(vectors) - before, 'mismatches': 0}
    pre.TYPES = TYPES
    programs = {t: fxgen.extract_pre(wa, t) for t in TYPES}
    names = {t: p['names'] for t, p in programs.items()}
    consts = {t: p['bones'] for t, p in programs.items()}
    plib = pre.ownerfx.particles_library()
    families['owned'], owned = pre.predraw_cases(wa, lib, plib, 64 if count == 292 else min(count, 64), names, consts)
    vectors += owned
    return families, vectors, plib


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
    families, vectors, plib = compare(wa, C.CDLL(str(v.LIBRARY)), args.cases)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        pre.MUTANTS = MUTANTS
        report['mutants'] = pre.mutations(vectors, plib)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
