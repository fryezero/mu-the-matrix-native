#!/usr/bin/env python3
"""SYS-MISC-001a WIP: BossHPUI arithmetic against pinned original instructions.
CRT ceil and its x87-to-int bridge are modeled services. No dispatcher, packet,
keyed transform, native-window registration or live client is executed here.
"""
import argparse
import ctypes as C
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import client_ui_machine as cm
import pins

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'reconstructed/misc/misc.c'


class Bar(C.Structure):
    _fields_ = [(x, C.c_int32) for x in ('unit', 'segments', 'remaining', 'current_colour', 'next_colour')]


def library(source, path):
    subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', '-O2', '-ffp-contract=off', '-fno-fast-math',
                    '-Wall', '-Wextra', '-Werror', '-Wconversion', '-I', str(SRC.parent),
                    str(source), '-lm', '-o', str(path)], check=True, capture_output=True)
    lib = C.CDLL(str(path))
    lib.mu_misc_boss_init.argtypes = [C.POINTER(Bar)]
    lib.mu_misc_boss_colour.argtypes = [C.c_int32]
    lib.mu_misc_boss_gauge.argtypes = [C.POINTER(Bar), C.c_int32, C.c_int32]
    lib.mu_misc_boss_update.argtypes = [C.POINTER(Bar), C.c_int32]
    lib.mu_misc_boss_set_maximum.argtypes = [C.POINTER(Bar), C.c_int32]
    return lib


def compare(text, data, lib, cases):
    counts = {}
    rng = random.Random(20261028)
    # Fresh machines and stubs per family, also for every compiled mutant.
    for family in ('init', 'colour', 'gauge', 'update', 'maximum'):
        m = cm.Machine(text, data)
        m.allow((0xb360b1, 0xb360ed), (0xb35d65, 0xb35dff), (0xb35c40, 0xb35d65),
                (0xb35b1d, 0xb35b37))
        ceil_result = [0]

        def ceil_service(machine):
            sp = machine.uc.reg_read(cm.UC_X86_REG_ESP)
            value = struct.unpack('<d', machine.read(sp + 4, 8))[0]
            ceil_result[0] = math.ceil(value)
            return 0

        m.stub(0x1990d30, ceil_service)
        m.stub(0x191c5e0, lambda _: ceil_result[0])
        # Bounded interior at 0xb35b1d compares only the maximum/unit write.
        # End is an existing instruction; redirect to the test return sentinel.
        def stop(machine):
            machine.uc.reg_write(cm.UC_X86_REG_EIP, cm.RETURN_SENTINEL)
            return cm.REDIRECT
        m.stub(0xb35b37, stop)
        for i in range(cases):
            m.reset()
            a = m.alloc(0xa0, define=True)
            bar = Bar(0, 10, 10, 0, 1)
            if family == 'init':
                m.write(a, bytes(20))
                m.call(0xb360b1, ecx=a)
                lib.mu_misc_boss_init(C.byref(bar))
                assert m.read(a, 20) == bytes(bar), (family, i)
            elif family == 'colour':
                index = [-1, 0, 1, 2, 3, 4][i % 6] if i < 6 else rng.randint(-10000, 10000)
                expected = C.c_int32(m.call(0xb35d65, [index], ecx=a)).value
                assert lib.mu_misc_boss_colour(index) == expected, (family, i)
            elif family == 'maximum':
                maximum = rng.randint(10, 2147483647)
                bar.segments = rng.randint(1, min(maximum, 100))
                m.write(a + 0x78, bytes(bar))
                # The slice uses its caller's frame. Supply args at EBP offsets.
                frame = m.alloc(0x40, define=True)
                m.put32(frame + 0x24, maximum)
                m.put32(frame + 0x28, i % 2)
                m.put32(frame - 0x10, a - (i % 2) * 20)
                # call() clears EBP; use a tiny authored entry trampoline to set it.
                shim = m.alloc(16, define=True)
                m.write(shim, b'\xbd' + struct.pack('<I', frame) + b'\xe9' + struct.pack('<i', 0xb35b1d - (shim + 10)))
                m.call(shim)
                assert lib.mu_misc_boss_set_maximum(C.byref(bar), maximum) == 1
                assert m.read(a + 0x78, 20) == bytes(bar), (family, i)
            else:
                maximum = rng.randint(10, 2147483647)
                bar.unit = maximum // bar.segments
                choices = [0, 1, bar.unit, bar.unit * 2, maximum, maximum - 1, -1]
                hp = choices[i % len(choices)] if i < len(choices) else rng.randint(-100, maximum + 10)
                slot = i % 2
                m.write(a + 0x78, bytes(bar))
                obj = a - slot * 20
                if family == 'gauge':
                    expected = C.c_int32(m.call(0xb35d89, [hp, maximum, slot], ecx=obj)).value
                    assert lib.mu_misc_boss_gauge(C.byref(bar), hp, maximum) == expected, (family, i)
                else:
                    m.call(0xb35c40, [hp, slot], ecx=obj)
                    assert lib.mu_misc_boss_update(C.byref(bar), hp) == 1
                    assert m.read(a + 0x78, 20) == bytes(bar), (family, i, hp, list(m.read(a+0x78,20)), list(bytes(bar)))
        counts[family] = cases
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=500)
    ap.add_argument('--text', type=Path, default=pins.TEXT.default())
    ap.add_argument('--data', type=Path, default=pins.DATA.default())
    ap.add_argument('--output', type=Path)
    ap.add_argument('--mutants', action='store_true')
    args = ap.parse_args()
    if args.cases < 10:
        ap.error('--cases must be at least 10')
    text = pins.load_pinned(args.text, pins.TEXT.size, pins.TEXT.sha256, 'text')
    data = pins.load_pinned(args.data, pins.DATA.size, pins.DATA.sha256, 'data')
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        counts = compare(text, data, library(SRC, tmp/'normal.dylib'), args.cases)
        caught = []
        if args.mutants:
            mutants = [
                ('initial_count', '{0, 10, 10, 0, 1}', '{0, 10, 9, 0, 1}'),
                ('colour_cycle', 'index == 0 ? 3', 'index == 0 ? 2'),
                ('full_gauge', 'gauge = 100;', 'gauge = 99;'),
                ('remainder', 'hp % bar->unit', 'hp / bar->unit'),
                ('last_colour', 'bar->remaining == 2', 'bar->remaining == 3'),
                ('maximum_unit', 'maximum / bar->segments', 'maximum / bar->segments + 1'),
            ]
            for name, old, new in mutants:
                assert SRC.read_text().count(old) == 1, name
                source = tmp/f'{name}.c'
                source.write_text(SRC.read_text().replace(old, new))
                lib = library(source, tmp/f'{name}.dylib')
                try:
                    compare(text, data, lib, 40)
                except AssertionError:
                    caught.append(name)
                else:
                    raise AssertionError('surviving mutant ' + name)
    report = {'cases': counts, 'total': sum(counts.values()), 'mismatches': 0,
              'mutants_caught': caught, 'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'boundary': 'window arithmetic only; CRT ceil and float-to-int modeled; maximum write is an interior slice'}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
