#!/usr/bin/env python3
"""RENDER-EFFECTS-003 consumers requested by the RENDER-WORLDS-K producer lane.

Strict original create/move/render bodies, independent of the frozen historical
particle corpus. Move includes explicit native head-removal cases. All five
subtypes use the existing fixed-pool native path; the world producer is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import actor_machine as am
import pins
import validate_particles as pt
import validate_render_effects as base

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x7ef7, 0)] + [(0x7f5a, s) for s in (4, 6, 7, 8)]
MUTANTS = [
    ('flare_life', 'mu_pt_rand(h) % 10 + 10;', 'mu_pt_rand(h) % 10 + 9;', 'create', (0x7ef7, 0)),
    ('flare_wind', 'drift[k] + (h ? h->wind_sum[k] : 0.0f)', 'drift[k] + 0.0f', 'move', (0x7ef7, 0)),
    ('tarkan_tint', '(l * 120.0f) / 255.0f', '(l * 100.0f) / 255.0f', 'move', (0x7f5a, 4)),
    ('tarkan_refresh', '/* 0x0163583a */\n                p->lifetime = 10;', '/* mutant */\n                p->lifetime = 9;', 'move', (0x7f5a, 6)),
    ('tarkan_rotation', 'if (p->subtype == 6) s->rotation = 0.0f;', 'if (p->subtype == 6) s->rotation = 1.0f;', 'render', (0x7f5a, 6)),
    ('tarkan_speed', '(float)(mu_pt_rand(h) % 4 + 6) * p->scale;', '(float)(mu_pt_rand(h) % 4 + 5) * p->scale;', 'create', (0x7f5a, 7)),
    ('tarkan_scale', 'p->scale *= 0.8f;', 'p->scale *= 0.7f;', 'create', (0x7f5a, 8)),
]


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    lib = pt.load_library(ROOT/'reconstructed/particles'/('libclient_particles.' + base.fx.SUFFIX))
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    for name in ('create', 'move', 'render'):
        result['comparisons'][name] = base.compare(text, data, lib, 'pt', name, KINDS, cases * len(KINDS))
    if mutations:
        with tempfile.TemporaryDirectory(prefix='world-particle-consumers-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                mutant = base.compile_mutant(Path(tmp), name, 'pt', old, new)
                report = base.compare(text, data, mutant, 'pt', family, [kind], max(60, cases // 5))
                f = report['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    bodies = {'flare_create': (0x015eec34, 0x015eeccd), 'flare_move': (0x01662886, 0x0166599e),
              'smoke4_create': (0x015c4c7b, 0x015c4d8d), 'smoke6_create': (0x015c639e, 0x015c657d),
              'smoke7_create': (0x015c657d, 0x015c66df), 'smoke8_create': (0x015c66df, 0x015c67e5),
              'smoke_moves': (0x01635535, 0x0163605e), 'render_particles': pt.BODIES['render_particles']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                              'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in bodies.items()}
    result['all_equal'] = all(f['cases'] == f['equal'] for r in result['comparisons'].values() for f in r['families'].values())
    result['all_mutants_caught'] = all(m['caught'] > 0 for m in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=1000)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1: parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output: args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
