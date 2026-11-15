#!/usr/bin/env python3
"""RENDER-ITEMS-002Z: signed piecewise body colour and its complete owned program."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
from unittest import mock

import gen_item_bodies as gen
import pins
import validate_item_read_programs as read
import validate_item_quality as quality
import validate_item_predraw as pre
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
CLOCKS = read.CLOCKS
CLOCKS += tuple(base + delta for base in (-12000, -9000, -6000, -3000, 3000, 6000, 9000, 12000)
                for delta in (-1.0, -0.5, 0.0, 0.5, 1.0))
MUTANTS = {
    'cycle-signed-remainder': ('int32_t rem = clock_trunc((double)time) % (int32_t)p->a;',
                               'int32_t rem = (int32_t)((uint32_t)clock_trunc((double)time) % p->a);'),
    'cycle-half-threshold': ('int first_branch = rem < half;', 'int first_branch = rem < half - 1;'),
    'cycle-upper-offset': ('first_branch ? rem : rem - half', 'first_branch ? rem : rem'),
    'cycle-reverse-subtract': ('add - value : value + add', 'value - add : value + add'),
    'cycle-wave': ('value = value * client_wave(a, time);', 'value = value * a;'),
}
MUTANTS.update({key: pre.MUTANTS[key] for key in ('pre-hook', 'sprite-translate')})


def compare(wa, lib, count=292):
    read.TYPES, read.CLOCKS = [0x0b51], CLOCKS
    families, vectors, particles = read.compare(wa, lib, count)
    reset = ResetWorld(wa, quality.RandomWorld)
    rng = random.Random(0x20080)
    case = v.random_case_any(rng, 0x0b51)
    case.update(item_level=0, quality=9, option1=0, ext=0, record=(0, 0, 0),
                a10=0xffffffff, a11=0xffffffff)
    for tick in range(6000 if count == 292 else count):
        state = dict(case, time=v.f2u(float(tick)))
        sequence = [0] * 64
        def factory(*args):
            world = reset(*args)
            world.sequence, world.drawn = sequence, 0
            return world
        result, expected, other, _ = v.client_stream(wa, state, factory)
        status, actual, used = quality.run_c(lib, state, sequence)
        if not result['ok'] or any(c[0] != 'effect' for c in other) or status or actual != expected:
            raise AssertionError(('cycle', tick, result, status, expected, actual))
        vectors.append(('body', state, sequence, expected))
    families['cycle'] = {'cases': 6000 if count == 292 else count, 'mismatches': 0}
    if len(gen.piecewise_colour(wa)) != 4:
        raise AssertionError('piecewise reader refused the pinned colour program')
    # Reject neighbouring branch, subtraction, setter and wave-call instructions.
    source = gen._text(wa, 0x0175f2e6, 0x0175f469 - 0x0175f2e6)
    for site in (0x0175f326, 0x0175f3b6, 0x0175f426, 0x0175f464):
        altered = bytearray(source)
        altered[site - 0x0175f2e6] = 0x90
        with mock.patch.object(gen, '_text', return_value=bytes(altered)):
            if gen.piecewise_colour(wa):
                raise AssertionError(('reader accepted a changed instruction', hex(site)))
    families['reader_refusals'] = {'cases': 4, 'mismatches': 0}
    return families, vectors, particles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=292)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--mutant-only', choices=tuple(MUTANTS), help='iteration: compile only this changed control')
    args = parser.parse_args()
    if not 1 <= args.cases <= 292:
        parser.error('--cases must be in 1..292')
    subprocess.run(['make', '-s', '-j4', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    families, vectors, particles = compare(wa, C.CDLL(str(v.LIBRARY)), args.cases)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        pre.MUTANTS = {args.mutant_only: MUTANTS[args.mutant_only]} if args.mutant_only else MUTANTS
        report['mutants'] = pre.mutations(vectors, particles)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
