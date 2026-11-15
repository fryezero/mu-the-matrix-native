#!/usr/bin/env python3
"""RENDER-ITEMS-002AB: bodies split by the helper's level word, packed (>= 9) or guarded and decoded (>= 11)."""
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
TYPES = gen.GUARD_TYPES
PACKED_WORDS = tuple(range(128)) + (-1, -128, -2147483648, 128, 129, 255, 256, 257, 2147483647)
MUTANTS = {
    'decoded-threshold': ('(mu_rc_body_types[type].level_split == 3 ? 11 : 9)',
                          '(mu_rc_body_types[type].level_split == 3 ? 12 : 9)'),
    'decoded-as-nine': ('(mu_rc_body_types[type].level_split == 3 ? 11 : 9)', '9'),
    'decoded-as-packed': ('level_split == 2 ? s->item->item_level >= 9 :', 'level_split >= 2 ? s->item->item_level >= 9 :'),
    'packed-decode': ('level_split == 2 ? s->item->item_level >= 9 :',
                      'level_split == 2 ? ((s->item->item_level >> 3) & 15) >= 9 :'),
    'packed-low-bits': ('level_split == 2 ? s->item->item_level >= 9 :', 'level_split == 2 ? s->item->item_level >= 16 :'),
    'guard-quality': ('s->item->quality > 1 && mu_rc_item_glow_level(s->item) >= 9 &&',
                      's->item->quality > 2 && mu_rc_item_glow_level(s->item) >= 9 &&'),
    'guard-record': ('s->item->quality > 1 && mu_rc_item_glow_level(s->item) >= 9 &&',
                     's->item->quality > 1 && mu_rc_item_glow_level(s->item) >= 11 &&'),
    'upper-clamp': ('case 7: if (value > k) value = k; break;', 'case 7: break;'),
    'clamp-direction': ('case 7: if (value > k) value = k; break;', 'case 7: if (value < k) value = k; break;'),
    'wide-tail': ('case 2: wide = wide + k64; break;', 'case 2: wide = (double)((float)wide + (float)k64); break;'),
    'ping-pong': ('case 39: if (i >= ki) i = (int32_t)((uint32_t)ki * 2u - 1u - (uint32_t)i); break;', 'case 39: break;'),
    'ping-pong-edge': ('case 39: if (i >= ki) i', 'case 39: if (i > ki) i'),
    'minimum-helper': ('case 38: f = kf > f ? f : kf; break;', 'case 38: break;'),
    'minimum-order': ('case 38: f = kf > f ? f : kf; break;', 'case 38: f = kf > f ? kf : f; break;'),
    'reverse-derived': ('x = c - x;   /* 0x0171945c', 'x = x - c;   /* 0x0171945c'),
    'model-carry': ('mu_rc_body_types[type].carry)', '0)'),
}


def original_guards(wa):
    """The read guard of each type executes with the caller's word: -1 from the low callers, otherwise the
    unshifted RenderObjDraw argument. The branch taken matches the list's predicate in every probe."""
    from unicorn import UC_HOOK_CODE
    sites = gen.level_guards(wa)
    seen = []

    class World(quality.RandomWorld):
        def install(self):
            super().install()

            def guard(uc, address, size, context):
                ebp = uc.reg_read(self.m.x86.UC_X86_REG_EBP)
                seen.append((address, gen._i32(self.m.r32(ebp + 0x28))))
            for address in sorted({site for _, site in sites.values()}):
                self.m.uc.hook_add(UC_HOOK_CODE, guard, begin=address, end=address)
    reset = ResetWorld(wa, World)
    rows = []
    probes = ((0, (0, 0, 0), 9, -1), (56, (0, 0, 0), 9, -1), (72, (0, 0, 0), 9, 72), (80, (0, 0, 0), 9, 80),
              (88, (0, 0, 0), 9, 88), (104, (0, 0, 0), 9, 104), (9, (0, 0x26, 0), 2, 9), (8, (0, 0x5b, 0), 2, 8),
              (95, (0, 0x26, 0), 1, -1), (-1, (0, 0, 0), 9, -1))
    for t in TYPES:
        form, site = sites[t]
        for packed, record, q, expected in probes:
            case = v.classify_case(t, v.CLASSIFY[0])
            case.update(item_level=packed, record=record, quality=q)
            seen.clear()

            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = [0] * 64, 0
                return world
            result, stream, other, _ = v.client_stream(wa, case, factory)
            high = (expected >= 9 if form == 'packed' else
                    expected != -1 and ((expected >> 3) & 15) >= gen.DECODED_GUARD_LEVEL)
            status, actual = v.c_stream(C.CDLL(str(v.LIBRARY)), case)
            if (not result['ok'] or other or seen != [(site, expected)] or status or actual != stream):
                raise AssertionError(('original guard', hex(t), packed, expected, seen, result, other, status))
            rows.append({'type': hex(t), 'form': form, 'site': hex(site), 'packed': packed, 'word': expected,
                         'high': bool(high), 'draws': len(stream)})
        # The predicate separates the two recorded bodies: high and low probes never share a draw count
        # unless the stream itself is equal (checked against C above).
        if len({row['high'] for row in rows[-len(probes):]}) != 2:
            raise AssertionError(('one-sided guard probes', hex(t)))
    return {'cases': len(rows), 'mismatches': 0, 'rows': rows}


def reader_refusals(wa):
    """Neighbouring forms are refused: a moved threshold, a missing -1 guard, a second guard in a case and a
    type without its own case."""
    text = bytearray(wa[0])
    refused = 0

    def patched(address, payload):
        copy = bytearray(text)
        copy[address - 0x401000:address - 0x401000 + len(payload)] = payload
        return (bytes(copy),) + tuple(wa[1:])
    sites = gen.level_guards(wa)
    packed = next(site for form, site in sites.values() if form == 'packed')
    decoded = next(site for form, site in sites.values() if form == 'decoded')
    trials = [patched(packed + 3, b'\x0a'),                 # cmp word, 10
              patched(decoded + 3, b'\x09'),                # cmp word, 9 in a decoded case
              patched(decoded + 16, b'\x0c'),               # cmp eax, 12
              patched(decoded + 4, b'\x75'),                # jne instead of je
              patched(gen.LEVEL_DECODE + 8, b'\x04')]       # sar eax, 4
    for trial in trials:
        try:
            gen.level_guards(trial)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('level guard reader accepted a neighbouring form')
    saved = list(gen.GUARD_TYPES)
    try:
        gen.GUARD_TYPES.append(0x1712)   # a shield range case without its own compare
        try:
            gen.level_guards(wa)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('level guard reader accepted a shared case')
    finally:
        gen.GUARD_TYPES[:] = saved
    return {'cases': refused, 'mismatches': 0}


def compare(wa, lib, count):
    groups.TYPES = TYPES
    families, vectors = groups.compare(wa, lib, count)
    reset = ResetWorld(wa, quality.RandomWorld)
    before = len(vectors)
    words = PACKED_WORDS if count == 292 else (0, 8, 9, 10, 55, 56, 72, 80, 87, 88, 95, 96, 104, 127, -1)
    for t in TYPES:
        rng = random.Random(0x200ab + t)
        for packed in words:
            for q in (0, 1, 2, 9):
                for b in (0, 0x26, 0x5b):
                    case = v.random_case_any(rng, t)
                    case.update(item_level=packed, quality=q, record=((packed & 1) * 6, b, 0),
                                render_type=(2, 0x102, 0x40042, 0x402)[(packed + q + b) % 4],
                                a10=0xffffffff, a11=0xffffffff, frame=rng.randrange(1 << 32))
                    sequence = quality.sequence_for(rng)
                    ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                    if not ok:
                        raise AssertionError(('packed', hex(t), packed, q, b, case, expected, detail))
                    vectors.append((case, sequence, expected))
    families['packed'] = {'cases': len(vectors) - before, 'mismatches': 0}
    for family, clocks in (('clocks', read.CLOCKS),
                           ('ticks', tuple(float(tick) for tick in range(-1300, 2700, 5 if count == 292 else 97)))):
        before = len(vectors)
        for t in TYPES:
            rng = random.Random(0x200ac + t)
            for k, clock in enumerate(clocks):
                case = v.random_case_any(rng, t)
                case.update(time=v.f2u(clock), item_level=(13, 11, 7)[k % 3] << 3, quality=9, record=(0, 0, 0),
                            a10=0xffffffff, a11=0xffffffff)
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
    families['original_guards'] = original_guards(wa)
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
    print(json.dumps({k: (v if k != 'families' else {n: {a: b for a, b in f.items() if a != 'rows'}
                                                    for n, f in v.items()}) for k, v in report.items()}))


if __name__ == '__main__':
    main()
