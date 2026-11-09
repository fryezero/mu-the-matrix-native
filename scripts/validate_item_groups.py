#!/usr/bin/env python3
"""RENDER-ITEMS-002X: bodies that bypass the ordinary level-glow helper chain."""
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
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.NO_GLOW_TYPES
MUTANTS = {
    'glow-chain': ('        level = 0;\n    if (parameters)',
                   '        level = mu_rc_item_glow_level(it);\n    if (parameters)'),
    'recipe-last-draw': ('i < recipe->count; ++i', 'i < recipe->count - 1; ++i'),
}


def compare(wa, lib, count=292):
    reset, vectors, families = ResetWorld(wa, quality.RandomWorld), [], {}
    for family in ('bodies', 'records'):
        before = len(vectors)
        for t in TYPES:
            rng = random.Random(0x20078 + t)
            if family == 'bodies':
                states = list(quality.state_cases(t))
                if count < 292:
                    front = count // 2
                    states = states[:front] + states[-(count-front):]
                cases = [case for _, case in states]
            else:
                cases = []
                for kind_b in (0x26, 0x5b):
                    for q in (0, 1, 2, 9):
                        for level in range(16):
                            for option, ext in ((0, 0), (1, 1)):
                                case = v.random_case_any(rng, t)
                                case.update(item_level=level << 3, quality=q, option1=option, ext=ext,
                                            record=(rng.choice((0, 6)), kind_b, 0),
                                            a10=0xffffffff, a11=0xffffffff)
                                cases.append(case)
            for index, case in enumerate(cases):
                sequence = quality.sequence_for(rng)
                ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError((family, hex(t), index, case, expected, detail))
                vectors.append((case, sequence, expected))
        families[family] = {'cases': len(vectors) - before, 'mismatches': 0}
    return families, vectors


def mutations(vectors):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    reference = C.CDLL(str(v.LIBRARY))
    counts = [quality.run_c(reference, case, sequence)[2] for case, sequence, _ in vectors]
    caught = {}
    with tempfile.TemporaryDirectory(prefix='item-groups-') as directory:
        for name, (old, new) in MUTANTS.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor', name, source.count(old)))
            path, library = Path(directory)/(name+'.c'), Path(directory)/(name+'.dylib')
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
            lib = C.CDLL(str(library))
            detected = sum(status != 0 or actual != expected or used != consumed
                           for (case, sequence, expected), consumed in zip(vectors, counts)
                           for status, actual, used in [quality.run_c(lib, case, sequence)])
            if not detected:
                raise AssertionError(('surviving mutant', name))
            caught[name] = detected
    return caught


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
        report['mutants'] = mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
