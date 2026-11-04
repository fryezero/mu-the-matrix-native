#!/usr/bin/env python3
"""Part 15 bodies (body random scaling a constant body-light vector) versus pinned instructions."""
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
TYPES = gen.PRODUCT_TYPES


def product_cases(wa, lib):
    """Every product type in the eleven survey states with rand results across each modulus:
    0..n-1, the largest multiples of n near 32767 and random values, so every random level
    of the light product is compared."""
    from item_body_machine import ResetWorld
    reset, vectors, draws, values = ResetWorld(wa, quality.RandomWorld), [], 0, set()
    for t in TYPES:
        moduli = [a for kind, a in quality.table_programs(t) if kind == 4]
        if not moduli or not any(kind == 5 for kind, _ in quality.table_programs(t)):
            raise AssertionError(('no product program', hex(t)))
        rng = random.Random(0x20032 + t)
        for config in v.CLASSIFY:
            for k in range(max(moduli) + 2):
                case = v.classify_case(t, config)
                if k < max(moduli):
                    sequence = [k + n * rng.randrange(32768 // n) for n in moduli[:1]] * 48
                else:
                    sequence = quality.sequence_for(rng) if k > max(moduli) else [32767] * 48
                case['record'] = ((0, 0, 0), (0, 0x26, 0), (None))[k % 3]
                ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError(('product', hex(t), config, k, detail))
                draws += detail[4]
                values.update(x % moduli[0] for x in sequence[:detail[4]])
                vectors.append((case, sequence, expected))
    if not draws:
        raise AssertionError('no rand result was compared')
    return {'cases': len(vectors), 'mismatches': 0, 'rand_draws': draws, 'residues': len(values)}, vectors


MUTANTS = {
    'product-off': ('value = k * r;', 'value = r;'),
    'product-constant': ('memcpy(&k, &bits, 4);\n            memcpy(&r, &input[35 + p->a], 4);',
                         'memcpy(&k, &bits, 4);\n            k = k + 0.125f;\n            memcpy(&r, &input[35 + p->a], 4);'),
    'product-source': ('memcpy(&r, &input[35 + p->a], 4);', 'memcpy(&r, &input[34 + p->a], 4);'),
    'product-op': ('value = k * r;', 'value = k + r;'),
    'product-kind': ('} else if (p->kind == 5) {', '} else if (p->kind == 6) {'),
    'random-phase': ('if (p->phases & (1u << phase))', 'if (p->phases)'),
    'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
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
        report['families']['products'], products = product_cases(wa, lib)
        if args.mutations:
            report['mutants'] = mutations(bodies + products)
        if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError(('table drift', 'item_bodies.h'))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
