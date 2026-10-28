#!/usr/bin/env python3
"""Compare item-linked Spark03/11's lifecycle with pinned original instructions."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import tempfile
import pins
import validate_particles as p

ROOT = Path(__file__).resolve().parents[1]


def compare(library, machine, cases):
    lib = p.load_library(str(library))
    report = p.Report()
    p.KINDS = [(0x7f26, 11)]
    for name, family in [('create', p.family_create), ('move', p.family_move), ('render', p.family_render)]:
        family(machine, lib, random.Random('items-002d-' + name), cases, report, {})
    return report.families


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/particles')], check=True)
    machine = p.PtMachine(pins.TEXT.read(), pins.DATA.read())
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'families': compare(ROOT/f'reconstructed/particles/libclient_particles.{p.SUFFIX}', machine, args.cases)}
    if any(f['cases'] != f['equal'] for f in report['families'].values()):
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        raise SystemExit('Spark03 lifecycle differs from original instructions')
    if args.mutations:
        source = (ROOT/'reconstructed/particles/particles.c').read_text()
        changes = {
            'spark11-life': ('p->lifetime = 30; /* Spark03/11 */', 'p->lifetime = 29; /* Spark03/11 */'),
            'spark11-velocity': ('mu_pt_rand(h) % 8) - 4.0f', 'mu_pt_rand(h) % 8) - 3.0f'),
            'spark11-fade': ('p->scale -= 0.04f;', 'p->scale -= 0.03f;'),
        }
        report['mutants'] = {}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name, (old, new) in changes.items():
                if source.count(old) != 1:
                    raise AssertionError(('mutant anchor', name))
                path, library = directory/f'{name}.c', directory/f'{name}.{p.SUFFIX}'
                path.write_text(source.replace(old, new))
                sources = ['world_flames.c', 'elbeland.c', 'sprites.c', 'shadow.c', 'visual.c', 'layout.c',
                           '../record-math/record_math.c']
                subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                                '-I', str(ROOT/'reconstructed/particles'), str(path),
                                *[str(ROOT/'reconstructed/particles'/s) for s in sources], '-lm', '-o', str(library)], check=True)
                families = compare(library, machine, args.cases)
                detected = sum(f['cases'] - f['equal'] for f in families.values())
                if not detected:
                    raise AssertionError(('surviving mutant', name))
                report['mutants'][name] = detected
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
