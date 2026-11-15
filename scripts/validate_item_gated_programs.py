#!/usr/bin/env python3
"""RENDER-ITEMS-002AB: pre-draw producers behind RenderObjDraw's decoded item level, and their body streams."""
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
import validate_item_remainder_programs as remainder
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = fxgen.GATED_PROGRAM_TYPES
# Packed level words around every decoded level, with low option bits and the domains outside one byte.
LEVEL_WORDS = tuple(level << 3 | low for level in range(16) for low in (0, 7)) + (-1, -8, -9, 128, 199, 200, 0x7fffffff, -0x80000000)
# The five programs pass constant item bones, so the sprite domain's -1 edge has no mutant here.
MUTANTS = {name: pre.MUTANTS[name] for name in (
    'body-carry', 'pre-hook', 'visible', 'alpha', 'randmod', 'cond-int', 'sprite-translate')}
MUTANTS.update({
    'level-decode': ('fx_set_int(&r[o->a], (it->item_level >> 3) & 15);', 'fx_set_int(&r[o->a], it->item_level & 15);'),
    'level-mask': ('fx_set_int(&r[o->a], (it->item_level >> 3) & 15);', 'fx_set_int(&r[o->a], it->item_level >> 3);'),
    'level-shift': ('fx_set_int(&r[o->a], (it->item_level >> 3) & 15);', 'fx_set_int(&r[o->a], (it->item_level >> 4) & 15);'),
})


def level_cases(wa, lib, plib, names, consts, per_word):
    """Owned comparisons at every packed level word: the original requests nothing below the case's constant
    and the same ordered requests from it on, in both the original and the C program."""
    reset, vectors = ResetWorld(wa, pre.ItemWorld), []
    coverage = {'requests': 0, 'silent': 0}
    for t in TYPES:
        rng = random.Random(0x200af + t)
        cases = [case for _, case in quality.state_cases(t)]
        sides = set()
        for word in LEVEL_WORDS:
            for k in range(per_word):
                case = dict(cases[rng.randrange(len(cases))], item_level=word)
                o = pre.item_setup(rng, t, k, names[t], consts[t], 0)
                case['frame'] = o['frame']
                expected = pre.original(wa, reset, case, o)
                actual = pre.run_c(lib, plib, case, o, expected[3])
                ok, _ = pre.same(expected, actual)
                if not ok:
                    raise AssertionError(('levels', hex(t), word, k, len(expected[1]), len(actual[2]), expected[3]))
                if expected[3]:      # the frustum flag: a hidden case requests nothing at any level
                    decoded = (word >> 3) & 15
                    sides.add((decoded, bool(expected[1])))
                coverage['requests' if expected[1] else 'silent'] += 1
                vectors.append(('predraw', case, o, expected))
        on = sorted(level for level, requested in sides if requested)
        off = sorted(level for level, requested in sides if not requested)
        if not on or not off or max(off) >= min(on) or set(on) | set(off) != set(range(16)):
            raise AssertionError(('level gate is not one threshold', hex(t), on, off))
        coverage[hex(t)] = min(on)
    return {'cases': len(vectors), 'mismatches': 0, 'coverage': coverage}, vectors


def exit_cases(wa, lib):
    """The model fields RenderObjDraw leaves (body light, level field, shade, flag) against the C model."""
    import validate_item_direct_bodies as direct
    reset, exits = ResetWorld(wa, quality.RandomWorld), []
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
            if (not result['ok'] or any(call[0] != 'effect' for call in other) or status or
                    stream != original_stream or actual != expected):
                raise AssertionError(('exits', hex(t), case, expected, actual))
            exits.append((case, expected))
    return {'cases': len(exits), 'mismatches': 0}


def reader_refusals(wa):
    """A changed level store, a second store and an ungated type are refused."""
    refused = 0
    address, payload = fxgen.LEVEL_STORE

    def patched(at, data):
        copy = bytearray(wa[0])
        copy[at - 0x401000:at - 0x401000 + len(data)] = data
        return (bytes(copy),) + tuple(wa[1:])
    start = fxgen.survey_pre(wa, TYPES[0])[0]
    trials = [patched(address + 5, b'\x04'),                                 # sar eax, 4
              patched(address + 8, b'\x07'),                                 # and eax, 7
              patched(start, bytes.fromhex('898554ffffff'))]                 # a second store inside a case
    for trial in trials:
        try:
            fxgen.level_local(trial)
        except fxgen.Refused:
            refused += 1
        else:
            raise AssertionError('level local reader accepted a neighbouring form')
    saved = list(fxgen.GATED_PROGRAM_TYPES)
    try:
        fxgen.GATED_PROGRAM_TYPES[:] = [0x0f22]     # an ungated producer never reads the level local
        try:
            fxgen.extract_pre(wa, 0x0f22)
        except fxgen.Refused:
            refused += 1
        else:
            raise AssertionError('an ungated case read as a gated program')
    finally:
        fxgen.GATED_PROGRAM_TYPES[:] = saved
    return {'cases': refused, 'mismatches': 0}


def compare(wa, lib, count=292):
    remainder.TYPES = TYPES
    saved = pre.TYPES
    try:
        families, vectors, plib = remainder.compare(wa, lib, count)
        programs = {t: fxgen.extract_pre(wa, t) for t in TYPES}
        names = {t: p['names'] for t, p in programs.items()}
        consts = {t: p['bones'] for t, p in programs.items()}
        families['levels'], levels = level_cases(wa, lib, plib, names, consts, 3 if count == 292 else 1)
        vectors += levels
    finally:
        pre.TYPES = saved
    families['exits'] = exit_cases(wa, lib)
    families['reader_refusals'] = reader_refusals(wa)
    return families, vectors, plib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=292)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.cases <= 292:
        parser.error('--cases must be in 1..292')
    subprocess.run(['make', '-s', '-j2', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
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
