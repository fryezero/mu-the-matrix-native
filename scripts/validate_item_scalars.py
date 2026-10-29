#!/usr/bin/env python3
"""Part 11 per-type wave/sine scalar bodies versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess
import tempfile
import gen_item_bodies as gen
import pins
import validate_item_clusters as clusters
import validate_item_wings_next as previous
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]


def programs():
    """First admitted type for every distinct scalar program in the table."""
    import re
    source = (ROOT/'reconstructed/renderchar/item_bodies.h').read_text()
    table = source[source.index('mu_rc_body_scalars[] = {'):]
    table = table[:table.index('};')]
    entries = re.findall(r'\n    (\{\d, \d, 0x[0-9a-f]{8}u, \{[^}]*\}, \{[^}]*\}\}),', table)
    rows = re.findall(r'\n    \{(0x[0-9a-f]{4}), \{[^}]*\}(?:, \d+){7}, (\d+), (\d+)\},', source)
    first = {}
    for t, start, count in rows:
        for k in range(int(start), int(start) + int(count)):
            first.setdefault(entries[k], int(t, 16))
    return entries, first


def clock_cases(wa, lib, first):
    """Signed period edges of every admitted wave, INT_MIN and negative zero."""
    import struct
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa), []
    for entry, t in sorted(first.items(), key=lambda item: item[1]):
        a = struct.unpack('<f', struct.pack('<I', int(entry.split(', ')[2][:-1], 16)))[0]
        period = abs(int(C.c_float(C.c_float(6283.1855).value / a).value)) if entry[1] == '1' else 1047
        times = (-2147483648.0, -2147483520.0, -period - 1, -period, -period + 0.5, -1.0, -0.0, 0.0,
                 period - 1, period - 0.25, period, period + 1, 2 * period, 2147483520.0, 2147483648.0)
        for time in times:
            for flags in (2, 0x40042):
                case = v.classify_case(t, v.CLASSIFY[0])
                case.update(time=v.f2u(time), render_type=flags, item_level=13 << 3)
                result, expected, other, _ = v.client_stream(wa, case, reset)
                if not result['ok'] or other or v.c_stream(lib, case) != (0, expected):
                    raise AssertionError(('clock', hex(t), time, flags, result, other))
                vectors.append((case, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'programs': len(first)}, vectors


def mutations(bodies):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'wave-period': ('(int32_t)(6283.1855f / a)', '(int32_t)(6284.0f / a)'),
        'wave-sign': ('if (3.1415927f > y)', 'if (3.1415927f < y)'),
        'wave-scale': ('* 0.001f * a;', '* 0.001f * -a;'),
        'sine-argument': ('client_sin(time * a)', 'client_sin(time * a + 0.001f)'),
        'single-mul': ('case 1: value = value * k; break;', 'case 1: value = value + k; break;'),
        'single-add': ('case 2: value = value + k; break;', 'case 2: value = value - k; break;'),
        'double-form': ('(p->op[0] & 8)', '(p->op[0] & 0)'),
        'scalar-slot': ('scalar_first + k]', 'scalar_first]'),
        'scalar-count': ('k < mu_rc_body_types[type].scalar_count', 'k + 1 < mu_rc_body_types[type].scalar_count'),
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'object-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
    }
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (old, new) in changes.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor', name, source.count(old)))
            path, library = Path(tmp)/(name+'.c'), Path(tmp)/(name+'.dylib')
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
            lib = C.CDLL(str(library))
            detected = sum(v.c_stream(lib, case) != (0, expected) for case, expected in bodies)
            if not detected:
                raise AssertionError(('surviving mutant', name))
            caught[name] = detected
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--screen', action='store_true', help='candidate rejection, not a passing validation')
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}}
    report['families']['bodies'], bodies, failures = clusters.body_cases(
        wa, lib, gen.SCALAR_TYPES, args.screen, world_class=previous.BodyWorld)
    if args.screen:
        report.update(rejected=[hex(f[0]) for f in failures])
    else:
        assert not failures
        entries, first = programs()
        report['programs'] = len(entries)
        report['families']['clocks'], clocks = clock_cases(wa, lib, first)
        if args.mutations:
            report['mutants'] = mutations(bodies + clocks)
        if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError('body table drift')
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
