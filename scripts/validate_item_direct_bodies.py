#!/usr/bin/env python3
"""RENDER-ITEMS-002Z: early whole bodies that bypass the level and tail helpers."""
import argparse
import ctypes as C
import json
import itertools
import random
from pathlib import Path
import subprocess

import gen_item_bodies as gen
import pins
import validate_item_groups as groups
import validate_renderchar as v
import validate_item_quality as quality
import validate_item_predraw as pre
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.DIRECT_TYPES
LIGHTS = tuple(itertools.product((0.0, 1.0), repeat=3)) + (
    (-0.0, -0.0, -0.0), (v.u2f(0x3f7fffff),) * 3,
    (v.u2f(0x3f800001),) * 3, (-1.0, -1.0, -1.0))
MUTANTS = {
    'early-body-gate': ('if (parameters && type_row >= 0 && mu_rc_body_types[type_row].plain >= 2)', 'if (0)'),
    'entry-model-level': (
        '        emit_parameter_body(&s, phase, it->render_type, it->alpha, it->a10, it->a11);',
        '        model->level_field = 0;\n'
        '        emit_parameter_body(&s, phase, it->render_type, it->alpha, it->a10, it->a11);'),
    'white-branch': ('mu_rc_body_types[type_row].plain == 3 &&', 'mu_rc_body_types[type_row].plain == 4 &&'),
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
    lib = C.CDLL(str(v.LIBRARY))
    families, vectors = groups.compare(wa, lib, args.cases)
    reset = ResetWorld(wa, quality.RandomWorld)
    before = len(vectors)
    for t in TYPES:
        rng = random.Random(0x20081 + t)
        for light in LIGHTS:
            for q in (0, 9):
                for level in (0, 7, 15):
                    for record in ((0, 0, 0), (6, 0x26, 0)):
                        case = v.random_case_any(rng, t)
                        case.update(light=tuple(map(v.f2u, light)), quality=q, item_level=level << 3,
                                    record=record, option1=1, ext=0x33, a10=0xffffffff, a11=0xffffffff,
                                    time=v.f2u((0.0, -0.0, -6000.0, 3000.0, 12345.0)[(level + q + record[1]) % 5]))
                        sequence = quality.sequence_for(rng)
                        ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                        if not ok:
                            raise AssertionError(('lights', hex(t), light, q, level, record, expected, detail))
                        vectors.append((case, sequence, expected))
    families['lights'] = {'cases': len(vectors) - before, 'mismatches': 0}
    before = len(vectors)
    for t in TYPES:
        rng = random.Random(0x20082 + t)
        states = list(quality.state_cases(t))
        for index in range(64):
            case = dict(states[index * 37 % len(states)][1])
            case['frame'] = pre.FRAME_VALUES[index] if index < len(pre.FRAME_VALUES) else rng.randrange(1 << 32)
            if index % 3 == 0:
                case['light'] = (v.f2u(1.0),) * 3
            sequence = quality.sequence_for(rng)
            ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
            if not ok:
                raise AssertionError(('frames', hex(t), index, case, expected, detail))
            vectors.append((case, sequence, expected))
    families['frames'] = {'cases': len(vectors) - before, 'mismatches': 0}
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        groups.MUTANTS = MUTANTS
        report['mutants'] = groups.mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
