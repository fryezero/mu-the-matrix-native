#!/usr/bin/env python3
"""RENDER-EFFECTS-002: focused original-instruction comparisons and compiled mutants.

Uses the strict existing skill/particle machines, each family in a fresh machine.
Cases are per effect kind for create/move and per smoke/1 particle family. Engine
services remain recorded stubs; model drawing and session integration are tested
separately. No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile

import actor_machine as am
import pins
import validate_skill_fx as fx
import validate_particles as pt

ROOT = Path(__file__).resolve().parents[1]
EFFECTS = [(0x412, 0), (0x414, 0), (0x41b, 0), (0x41f, 0)]
# A mutant must alter compiled production C and be caught by the same comparator.
MUTANTS = [
    ('ice_lifetime', 'fx', 'e->lifetime = 50;', 'e->lifetime = 49;', 'effect_create', (0x412, 0)),
    ('poison_blend', 'fx', '/* 0x013d71c9 */\n        e->blend_mesh = 1;',
     '/* mutant */\n        e->blend_mesh = 0;', 'effect_create', (0x414, 0)),
    ('wave_speed', 'fx', '/* 0x013cf050 */\n        e->blend_mesh = 0;\n        e->lifetime = 20;\n        e->direction[1] = -60.0f;',
     '/* mutant */\n        e->blend_mesh = 0;\n        e->lifetime = 20;\n        e->direction[1] = -50.0f;', 'effect_create', (0x41f, 0)),
    ('ice_fade', 'fx', 'e->alpha = e->alpha - f32bits(0x3d4ccccd)',
     'e->alpha = e->alpha - 0.1f', 'effect_move', (0x412, 0)),
    ('debris_bounce', 'fx', 'e->lifetime -= 4;\n            e->angle[0] = e->angle[0] - e->scale * 128.0f;',
     'e->lifetime -= 4;\n            e->angle[0] = e->angle[0] - e->scale * 32.0f;', 'effect_move', (0x41b, 0)),
    ('wave_emission', 'fx', 'for (int k = 0; k < 4; ++k)\n            call_particle(env, e, 0x7f5a',
     'for (int k = 0; k < 3; ++k)\n            call_particle(env, e, 0x7f5a', 'effect_move', (0x41f, 0)),
    ('poison_particle_life', 'pt', '/* 0x015c5f15: Poison burst */\n            p->lifetime = 50;',
     '/* mutant */\n            p->lifetime = 16;', 'create', (0x7f5a, 1)),
    ('poison_particle_tint', 'pt', 'p->light[2] = l * 0.8f;\n                for (int k',
     'p->light[2] = l * 0.5f;\n                for (int k', 'move', (0x7f5a, 1)),
]


def compare(text, data, lib, domain, name, kinds, cases):
    module = fx if domain == 'fx' else pt
    if domain == 'fx':
        fx.EFFECT_KINDS = kinds
        am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    else:
        pt.KINDS = kinds
    # New machine for every family and every mutant: no retained service stubs.
    machine = module.FxMachine(text, data) if domain == 'fx' else module.PtMachine(text, data)
    report = pt.Report()
    family = dict(module.FAMILIES)[name]
    family(machine, lib, random.Random('render-effects-002-' + name), cases, report, defaultdict(int))
    return {'families': report.families, 'coverage': report.coverage}


def compile_mutant(directory, name, domain, old, new):
    base = ROOT/'reconstructed'/('combat' if domain == 'fx' else 'particles')
    source = base/('skill_fx.c' if domain == 'fx' else 'particles.c')
    original = source.read_text()
    if original.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    path = directory/(name + '.c')
    path.write_text(original.replace(old, new))
    others = (['combat.c', '../objects/world_warp.c', '../joints/joints.c', '../record-math/record_math.c',
               '../movement/client_movement.c'] if domain == 'fx' else
              ['world_flames.c', 'elbeland.c', 'sprites.c', 'shadow.c', 'visual.c', 'layout.c',
               '../record-math/record_math.c'])
    out = directory/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math',
                    '-shared', '-I', str(base), str(path), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return (fx if domain == 'fx' else pt).load_library(out)


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    for domain, names, kinds in [('fx', ['effect_create', 'effect_move'], EFFECTS),
                                  ('pt', ['create', 'move', 'render'], [(0x7f5a, 1)])]:
        module = fx if domain == 'fx' else pt
        lib = module.load_library(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX if domain == 'fx'
                                                       else 'particles/libclient_particles.' + fx.SUFFIX))
        for name in names:
            result['comparisons'][domain + '_' + name] = compare(text, data, lib, domain, name, kinds,
                                                                 cases * len(kinds))
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects-mutants-') as tmp:
            for name, domain, old, new, family, kind in MUTANTS:
                lib = compile_mutant(Path(tmp), name, domain, old, new)
                report = compare(text, data, lib, domain, family, [kind], max(60, cases // 5))
                f = report['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                         'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in {**fx.BODIES, **pt.BODIES}.items()
                        if name in ('create_effect', 'move_effect', 'create_particle_core', 'move_particles',
                                    'render_particles')}
    result['all_equal'] = all(f['cases'] == f['equal'] for r in result['comparisons'].values()
                              for f in r['families'].values())
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
