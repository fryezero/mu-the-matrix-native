#!/usr/bin/env python3
"""RENDER-WORLDS-L: strict original particle bodies and bitmap loader calls.

Each family and mutant gets a fresh Unicorn machine. The shared comparator
checks all defined particle fields, ordered services, RNG draws, GL state and
sprite arguments. Head removal is a separate native check in the move family.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import actor_machine as am
import pins
import validate_particles as pt
import validate_render_effects as base
import validate_world_particle_consumers as loaders

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x801c, 16), (0x8086, 2), (0x8087, 6), (0x8089, 2),
         (0x801e, 0), (0x801c, 8), (0x801b, 4)]
REGISTRATIONS = [(0x018220ad, 0x018220c5, 0x7f6b, 'Effect\\Shiny04.jpg'),
                 (0x01821b61, 0x01821b79, 0x8086, 'Effect\\firehik_mono01.jpg'),
                 (0x01821b81, 0x01821b99, 0x8087, 'Effect\\firehik_mono02.jpg'),
                 (0x01821bc1, 0x01821bd9, 0x8089, 'Effect\\firehik_mono03.jpg'),
                 (0x01822aad, 0x01822ac5, 0x801e, 'Effect\\WATERFALL5.jpg')]
# All are compiled authored production C, never altered original instructions.
MUTANTS = [
    ('karutan_scale', 'p->scale = 0.6f + scale;', 'p->scale = 0.5f + scale;', 'create', (0x801c, 16)),
    ('karutan_fade', 'p->lifetime < 8', 'p->lifetime < 7', 'move', (0x801c, 16)),
    ('raklion_life', 'p->type == 0x8086 ? 27', 'p->type == 0x8086 ? 26', 'create', (0x8086, 2)),
    ('raklion_drift', '? -7.0f : -5.0f', '? -6.0f : -5.0f', 'create', (0x8086, 2)),
    ('raklion_fade', 'if (p->lifetime < 10) p->alpha', 'if (p->lifetime < 9) p->alpha', 'move', (0x8087, 6)),
    ('raklion_shrink', '? 6 : 7', '? 5 : 7', 'move', (0x8087, 6)),
    ('raklion_color', 'p->field_84 * p->alpha', 'p->field_80 * p->alpha', 'move', (0x8089, 2)),
    ('raklion_short_life', '? 24 : 17', '? 24 : 16', 'create', (0x8089, 2)),
    ('market_spray', 'p->scale = 1.6f;', 'p->scale = 1.5f;', 'create', (0x801e, 0)),
    ('market_mist', 'p->velocity[2] -= 0.6f;', 'p->velocity[2] -= 0.5f;', 'move', (0x801c, 8)),
    ('market_pool_life', 'p->lifetime = 70;', 'p->lifetime = 60;', 'create', (0x801b, 4)),
    ('market_rotation', 'p->rotation -= 1.1f;', 'p->rotation -= 1.0f;', 'move', (0x801b, 4)),
]


def compare(text, data, lib, family, kinds, cases):
    # Every kind exercises the exact fade/head thresholds even in short private runs.
    original = pt.random_particle
    index = 0
    def directed(rng, kind):
        nonlocal index
        p = original(rng, kind)
        lifetimes = [-1, 0, 1, 7, 8, 9, 10, 11, 20, 21, 30, 70]
        p.lifetime = lifetimes[(index // len(kinds)) % len(lifetimes)]
        p.live = 0 if (index // len(kinds)) % 13 == 12 else 1
        index += 1
        return p
    try:
        pt.random_particle = directed
        return base.compare(text, data, lib, 'pt', family, kinds, cases)
    finally:
        pt.random_particle = original


def mutant(directory, name, old, new):
    source = ROOT/'reconstructed/particles'
    original = (source/'worlds_l.inc').read_text()
    if old not in original: raise ValueError(f'{name}: missing mutation site')
    folder = directory/name
    folder.mkdir()
    (folder/'worlds_l.inc').write_text(original.replace(old, new))
    (folder/'particles.c').write_text((source/'particles.c').read_text())
    out = folder/('libmutant.' + base.fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math',
                    '-shared', '-I', str(source), str(folder/'particles.c'),
                    *[str(source/p) for p in ('world_flames.c', 'elbeland.c', 'sprites.c', 'shadow.c',
                      'visual.c', 'layout.c', '../record-math/record_math.c')], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return pt.load_library(out)


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    lib = pt.load_library(ROOT/'reconstructed/particles'/('libclient_particles.' + base.fx.SUFFIX))
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {},
              'coverage': {}, 'mutants': {}}
    for name in ('create', 'move', 'render'):
        r = compare(text, data, lib, name, KINDS, cases * len(KINDS))
        result['families'].update(r['families'])
        result['coverage'].update(r['coverage'])
    # Native loop-head removals are counted separately from original-instruction cases.
    result['native_removals'] = result['coverage']['move'].get('erased at the head', 0)
    result['instruction_cases'] = sum(f['cases'] for f in result['families'].values()) - result['native_removals']
    if mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-l-mutants-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                lib = mutant(Path(tmp), name, old, new)
                r = compare(text, data, lib, family, [kind], max(100, cases // 5))
                f = r['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
            lib = base.compile_mutant(Path(tmp), 'render_rotation', 'pt',
                                      's->height = height;\n    s->rotation = p->rotation;',
                                      's->height = height;\n    s->rotation = p->rotation + 1.0f;')
            r = compare(text, data, lib, 'render', KINDS, max(140, cases))
            f = r['families']['render']
            result['mutants']['render_rotation'] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    previous = loaders.REGISTRATIONS
    try:
        loaders.REGISTRATIONS = REGISTRATIONS
        result['registrations'] = loaders.registrations(text, data)
    finally:
        loaders.REGISTRATIONS = previous
    bodies = {**pt.BODIES, 'karutan_create': (0x015f3a6a, 0x015f3b1c),
              'karutan_move': (0x0166a8ca, 0x0166aabd),
              'raklion_fire_create': (0x015d4350, 0x015d45a8),
              'raklion_smoke_create': (0x015b911e, 0x015b9412),
              'raklion_short_create': (0x015d9243, 0x015d949b)}
    result['bodies'] = {k: {'start': hex(a), 'end': hex(b),
                          'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
                        for k, (a, b) in bodies.items()}
    result['all_equal'] = all(f['cases'] == f['equal'] for f in result['families'].values()) and all(
        r['equal'] for r in result['registrations'])
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
