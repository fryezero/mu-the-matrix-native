#!/usr/bin/env python3
"""RENDER-ITEMS-002Z: early whole bodies that bypass the level and tail helpers."""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess

import gen_item_bodies as gen
import pins
import validate_item_groups as groups
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.DIRECT_TYPES
MUTANTS = {
    'early-body-gate': ('if (parameters && type_row >= 0 && mu_rc_body_types[type_row].direct)', 'if (0)'),
    'entry-model-level': (
        '        emit_parameter_body(&s, 0, it->render_type, it->alpha, it->a10, it->a11);',
        '        model->level_field = 0;\n'
        '        emit_parameter_body(&s, 0, it->render_type, it->alpha, it->a10, it->a11);'),
    'recipe-last-draw': ('i < recipe->count; ++i', 'i < recipe->count - 1; ++i'),
}


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
    groups.TYPES = TYPES
    families, vectors = groups.compare(wa, C.CDLL(str(v.LIBRARY)), args.cases)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        groups.MUTANTS = MUTANTS
        report['mutants'] = groups.mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
