#!/usr/bin/env python3
"""RENDER-ITEMS-002Y: additional clock/product bodies with independent record and counter states."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess

import gen_item_bodies as gen
import pins
import validate_item_groups as groups
import validate_item_predraw as pre
import validate_item_quality as quality
import validate_item_read_programs as read
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.OTHER_TYPES
MUTANTS = {
    'light-product': ('value = value * other;', 'value = value + other;'),
    'helper-carry': ('mu_rc_body_types[type].carry)', '0)'),
}


def compare(wa, lib, count=292):
    groups.TYPES = TYPES
    families, original_vectors = groups.compare(wa, lib, count)
    vectors = [('body', *vector) for vector in original_vectors]
    reset = ResetWorld(wa, quality.RandomWorld)
    for family in ('clocks', 'frame'):
        before = len(vectors)
        for t in TYPES:
            rng = random.Random(0x2007b + t)
            cases = [case for _, case in quality.state_cases(t)]
            for k in range(len(read.CLOCKS) if family == 'clocks' else 64):
                case = dict(cases[(k * 37) % len(cases)])
                if family == 'clocks':
                    case['time'] = v.f2u(read.CLOCKS[k])
                else:
                    case['frame'] = pre.FRAME_VALUES[k] if k < len(pre.FRAME_VALUES) else rng.randrange(1 << 32)
                sequence = quality.sequence_for(rng)
                ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError((family, hex(t), k, case, expected, detail))
                vectors.append(('body', case, sequence, expected))
        families[family] = {'cases': len(vectors) - before, 'mismatches': 0}
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
        pre.MUTANTS = MUTANTS
        report['mutants'] = pre.mutations(vectors, None)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
