#!/usr/bin/env python3
"""Part 16 bodies (kind-6 derived programs: a draw word one binary32 operation from another input) versus
pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import gen_item_bodies as gen
import pins
import validate_item_quality as quality
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.DERIVED_TYPES
# The extended sine reader folds these former derived programs into one exact clock chain.
CLOCK_REPLACEMENTS = frozenset((0x0b0c, 0x16fc, 0x16fd, 0x16fe, 0x1b33))
# Clock values for the derived family: zero, small, period edges of the wave/sin/clock programs, large.
TIMES = (0.0, 1.0, 999.0, 1570.0, 2000.0, 6283.0, 123456.0, 1999999.0)


def derived_programs(t):
    return [a for kind, a in quality.table_programs(t) if kind == 6]


def derived_cases(wa, lib):
    """Each type in the eleven survey states at eight clocks, with record kinds B 0x26/0x5b (glow level 9) and
    none, and random model fields, so every kind-6 program reads varying inputs."""
    from item_body_machine import ResetWorld
    reset, vectors, programs = ResetWorld(wa, quality.RandomWorld), [], 0
    for t in TYPES:
        if t in CLOCK_REPLACEMENTS:
            if quality.table_programs(t) != [(3, 0)]:
                raise AssertionError(('clock replacement differs', hex(t), quality.table_programs(t)))
        elif not derived_programs(t):
            raise AssertionError(('no derived program', hex(t)))
        programs += len(derived_programs(t))
        rng = random.Random(0x20040 + t)
        for config in v.CLASSIFY:
            for k, time in enumerate(TIMES):
                case = v.classify_case(t, config)
                case.update(time=v.f2u(time), record=((0, 0, 0), (0, 0x26, 0), (0, 0x5b, 0), None)[k % 4])
                case['model_light'] = [v.f2u(rng.uniform(0, 1)) for _ in range(3)]
                case['light'] = [v.f2u(rng.uniform(0, 1.5)) for _ in range(3)]
                case['object_alpha'] = v.f2u(rng.uniform(0, 1))
                sequence = quality.sequence_for(rng)
                ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError(('derived', hex(t), config, time, detail))
                vectors.append((case, sequence, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'programs': programs}, vectors


def record_cases(wa, lib):
    """Kind-B 0x26/0x5b records at every level, qualities 0-2 and 9, with and without the tail options: the
    phases where the carried types' later helpers start from the body's last draw."""
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, quality.RandomWorld), []
    for t in TYPES:
        rng = random.Random(0x20041 + t)
        for kind_b in (0x26, 0x5b):
            for q in (0, 1, 2, 9):
                for level in range(16):
                    for option1, ext in ((0, 0), (1, 1)):
                        case = v.random_case_any(rng, t)
                        case.update(item_level=level << 3, quality=q, option1=option1, ext=ext,
                                    render_type=(2, 0x40042)[level & 1], record=(rng.choice((0, 6)), kind_b, 0),
                                    a10=0xffffffff, a11=0xffffffff)
                        sequence = quality.sequence_for(rng)
                        ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                        if not ok:
                            raise AssertionError(('record', hex(t), kind_b, q, level, detail))
                        vectors.append((case, sequence, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


MUTANTS = {
    'derived-off': ('value = derived_program(p, value);', 'value = value + 0.0f;'),
    'derived-source': ('memcpy(&value, &input[p->a], 4);', 'memcpy(&value, &input[p->a + 1], 4);'),
    'derived-kind': ('} else if (p->kind == 6) {', '} else if (p->kind == 7) {'),
    'derived-mul': ('            x = x * c;', '            x = x * c * 1.5f;'),
    'derived-add': ('            x = x + c;', '            x = x - c;'),
    'derived-count': ('    for (int i = 0; i < p->count; ++i) {\n        float c;',
                      '    for (int i = 0; i < p->count - 1; ++i) {\n        float c;'),
    'carry-off': ('&last) &&\n        mu_rc_body_types[type].carry)', '&last) &&\n        0)'),
}


def mutations(vectors):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    reference = C.CDLL(str(v.LIBRARY))
    counts = [quality.run_c(reference, case, sequence)[2] for case, sequence, _ in vectors]
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (old, new) in MUTANTS.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor', name, source.count(old)))
            path, library = Path(tmp)/(name + '.c'), Path(tmp)/(name + '.dylib')
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
            lib = C.CDLL(str(library))
            detected = 0
            for (case, sequence, expected), count in zip(vectors, counts):
                status, actual, used = quality.run_c(lib, case, sequence)
                detected += status != 0 or actual != expected or used != count
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
    report['families']['bodies'], bodies, failures = quality.body_cases(wa, lib, TYPES, args.screen)
    if args.screen:
        report.update(rejected=[hex(f[0]) for f in failures])
    else:
        assert not failures
        report['families']['derived'], derived = derived_cases(wa, lib)
        report['families']['records'], records = record_cases(wa, lib)
        if args.mutations:
            report['mutants'] = mutations(bodies + derived + records)
        if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError(('table drift', 'item_bodies.h'))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
