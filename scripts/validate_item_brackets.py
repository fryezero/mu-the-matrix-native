#!/usr/bin/env python3
"""RENDER-ITEMS-002AB: bodies inside a bare glPushMatrix/glPopMatrix bracket, scalar forms and flag programs."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess

import gen_item_bodies as gen
import pins
import validate_item_direct_bodies as direct
import validate_item_groups as groups
import validate_item_quality as quality
import validate_item_read_programs as read
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.MATRIX_TYPES + gen.TAIL_TYPES + gen.FLAG_TYPES
BRACKET = [('gl', 'glPushMatrix', []), ('gl', 'glPopMatrix', [])]
MUTANTS = {
    'ternary-minimum': ('case 17: value = k > value ? value : k; break;', 'case 17: break;'),
    'ternary-direction': ('case 17: value = k > value ? value : k; break;', 'case 17: value = k > value ? k : value; break;'),
    'upper-clamp': ('case 7: if (value > k) value = k; break;', 'case 7: break;'),
    'random-source': ('random_program(p, rank5_random(s))', 'random_program(p, 0)'),
    'reverse-tail': ('case 5: value = k - value; break;', 'case 5: value = value - k; break;'),
    'scaled-light': ('value = derived_program(p, value);', '(void)derived_program(p, value);'),
    'flag-mask': ('(input[p->a] & (uint32_t)p->k[0]) | (uint32_t)p->k[1];', 'input[p->a] | (uint32_t)p->k[1];'),
    'flag-constant': ('(input[p->a] & (uint32_t)p->k[0]) | (uint32_t)p->k[1];', '(input[p->a] & (uint32_t)p->k[0]);'),
    'flag-source': ('(input[p->a] & (uint32_t)p->k[0]) | (uint32_t)p->k[1];', '(input[p->a + 1] & (uint32_t)p->k[0]) | (uint32_t)p->k[1];'),
    'recipe-last-draw': ('i < recipe->count; ++i', 'i < recipe->count - 1; ++i'),
    'model-carry': ('mu_rc_body_types[type].carry)', '0)'),
}
_client_stream = v.client_stream
_brackets = {'pairs': 0, 'plain': 0}


def bracketed_stream(world_args, case, world_factory=None):
    """The client stream with the bracket of a MATRIX_TYPES body set aside: exactly one push followed by one
    pop and nothing else, or no bracket at all (the helper's 0x40000 exit). Anything else stays in others."""
    result, stream, others, machine = _client_stream(world_args, case, world_factory)
    if case['type'] in gen.MATRIX_TYPES:
        if others == BRACKET:
            _brackets['pairs'] += 1
            others = []
        elif not others:
            _brackets['plain'] += 1
    return result, stream, others, machine


def reader_refusals(wa):
    """A changed helper, a second bracket, an enclosed import and a type outside a case are refused."""
    refused = 0

    def patched(address, payload):
        copy = bytearray(wa[0])
        copy[address - 0x401000:address - 0x401000 + len(payload)] = payload
        return (bytes(copy),) + tuple(wa[1:])
    sites = gen.matrix_brackets(wa)
    begin, end = sites[gen.MATRIX_TYPES[0]]
    target = (gen.MATRIX_BEGIN - (end + 5)) & 0xffffffff
    trials = [patched(gen.MATRIX_BEGIN + 9, b'\x30'),                          # another import slot
              patched(gen.MATRIX_END + 14, b'\xc2'),                           # ret imm
              patched(end + 1, target.to_bytes(4, 'little')),                  # two begins, no end
              patched(begin, b'\xff\x15\x98\xc6\xa7\x01'[:5])]                 # a direct import in the case
    for trial in trials:
        try:
            gen.matrix_brackets(trial)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('matrix bracket reader accepted a neighbouring form')
    saved = list(gen.MATRIX_TYPES)
    try:
        gen.MATRIX_TYPES.append(0x1712)
        try:
            gen.matrix_brackets(wa)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('matrix bracket reader accepted a type without a case')
    finally:
        gen.MATRIX_TYPES[:] = saved
    return {'cases': refused, 'mismatches': 0}


def compare(wa, lib, count):
    v.client_stream = bracketed_stream
    try:
        groups.TYPES = TYPES
        families, vectors = groups.compare(wa, lib, count)
        reset = ResetWorld(wa, quality.RandomWorld)
        for family, clocks in (('clocks', read.CLOCKS),
                               ('ticks', tuple(float(tick) for tick in range(-3200, 6400, 16 if count == 292 else 331)))):
            before = len(vectors)
            for t in TYPES:
                rng = random.Random(0x200ae + t)
                for k, clock in enumerate(clocks):
                    case = v.random_case_any(rng, t)
                    case.update(time=v.f2u(clock), item_level=(13, 9, 0)[k % 3] << 3, quality=9, record=(0, 0, 0),
                                render_type=(2, 0x102, 0x402)[k % 3], a10=0xffffffff, a11=0xffffffff)
                    sequence = quality.sequence_for(rng)
                    ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                    if not ok:
                        raise AssertionError((family, hex(t), clock, case, expected, detail))
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
                    raise AssertionError(('exits', hex(t), case, expected, actual))
                exits.append((case, expected))
        families['exits'] = {'cases': len(exits), 'mismatches': 0}
    finally:
        v.client_stream = _client_stream
    if not _brackets['pairs']:
        raise AssertionError('no matrix bracket was observed')
    families['brackets'] = {'cases': _brackets['pairs'], 'mismatches': 0, 'without_bracket': _brackets['plain']}
    families['reader_refusals'] = reader_refusals(wa)
    return families, vectors


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
    families, vectors = compare(wa, C.CDLL(str(v.LIBRARY)), args.cases)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        groups.MUTANTS = MUTANTS
        report['mutants'] = groups.mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
