#!/usr/bin/env python3
"""RENDER-WORLDS-M: Uruk nested particle bodies and bitmap loader calls.

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
KINDS = [(0x7f5a, 69), (0x7f89, 25), (0x801b, 7), (0x8184, 2), (0x7f5a, 22), (0x7fd5, 0)]
# (first push, LoadBitmap call, index, path): the world loader 0x01841184 and the two other
# flare_mono sites, plus the existing Spark01 slot the spiral draws.
REGISTRATIONS = [(0x01841184, 0x0184119c, 0x8184, 'Effect\\flare_mono.jpg'),
                 (0x0184130b, 0x01841323, 0x8184, 'Effect\\flare_mono.jpg'),
                 (0x01833b68, 0x01833b80, 0x8184, 'Effect\\flare_mono.jpg'),
                 (0x0182236d, 0x01822385, 0x7fd5, 'Effect\\Spark01.jpg')]
# All are compiled authored production C, never altered original instructions.
MUTANTS = [
    ('glow_life', 'p->lifetime = 60;', 'p->lifetime = 59;', 'create', (0x7f5a, 69)),
    ('glow_gravity', '% 16 + 30) * 0.1f', '% 16 + 31) * 0.1f', 'create', (0x7f5a, 69)),
    ('glow_saved_light', 'p->light[k] = l * p->angle[k];', 'p->light[k] = l * p->light[k];', 'move', (0x7f5a, 69)),
    ('glow_fall', 'p->gravity -= 0.04f;', 'p->gravity -= 0.05f;', 'move', (0x7f5a, 69)),
    ('ember_tint', 'p->light[0] = l * 0.9f;', 'p->light[0] = l * 0.8f;', 'move', (0x7f5a, 22)),
    ('mist_spread', '% 200 - 100) + p->position[0]', '% 500 - 250) + p->position[0]', 'create', (0x7f89, 25)),
    ('mist_rise', 'p->position[2] + 2.0f;', 'p->position[2] + 1.0f;', 'move', (0x7f89, 25)),
    ('mist_alpha', 'if (p->type == 0x7f89 && p->subtype == 25)', 'if (p->type == 0x7f89 && p->subtype == 24)', 'render', (0x7f89, 25)),
    ('burst_life', '% 50 + 20;', '% 50 + 21;', 'create', (0x801b, 7)),
    ('burst_push', '(20.0f / (float)p->lifetime) * 100.0f', '(20.0f / (float)p->lifetime) * 90.0f', 'move', (0x801b, 7)),
    ('burst_tint', 'p->light[1] *= 0.77f;', 'p->light[1] *= 0.8f;', 'move', (0x801b, 7)),
    ('flare_scale', '/ 300.0f + 0.2f', '/ 300.0f + 0.25f', 'create', (0x8184, 2)),
    ('flare_cap', 'if (p->velocity[2] > 8.0f) p->velocity[2] = 8.0f;', 'if (p->velocity[2] > 9.0f) p->velocity[2] = 9.0f;', 'move', (0x8184, 2)),
    ('flare_fade', 'if (p->lifetime < 15)', 'if (p->lifetime < 14)', 'move', (0x8184, 2)),
    ('spiral_scale', '* 0.0075 *', '* 0.0080 *', 'create', (0x7fd5, 0)),
    ('spiral_euler', 't[2] = -s[1] * in[0]', 't[2] = s[1] * in[0]', 'move', (0x7fd5, 0)),
    ('spiral_spin', 't * ratio * 4.0f', 't * ratio * 3.0f', 'move', (0x7fd5, 0)),
]
LIFETIMES = [-1, 0, 1, 2, 9, 10, 11, 14, 15, 16, 149, 150, 151, 299, 300, 60, 70, 89]


def compare(text, data, lib, family, kinds, cases):
    # Every kind exercises the exact fade/head thresholds even in short private runs.
    original = pt.random_particle
    index = 0
    def directed(rng, kind):
        nonlocal index
        p = original(rng, kind)
        step = index // len(kinds)
        p.lifetime = LIFETIMES[step % len(LIFETIMES)]
        p.live = 0 if step % 19 == 18 else 1
        if kind == (0x7fd5, 0) and step % 3:
            p.initial_lifetime = rng.choice([70, 80, 89, p.lifetime + 1])
        index += 1
        return p
    try:
        pt.random_particle = directed
        return base.compare(text, data, lib, 'pt', family, kinds, cases)
    finally:
        pt.random_particle = original


def mutant(directory, name, old, new):
    source = ROOT/'reconstructed/particles'
    original = (source/'worlds_m.inc').read_text()
    if original.count(old) != 1: raise ValueError(f'{name}: mutation site must be unique')
    folder = directory/name
    folder.mkdir()
    (folder/'worlds_m.inc').write_text(original.replace(old, new))
    for keep in ('particles.c', 'worlds_l.inc', 'icarus_clouds.inc'):
        (folder/keep).write_text((source/keep).read_text())
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
        with tempfile.TemporaryDirectory(prefix='worlds-m-mutants-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                lib = mutant(Path(tmp), name, old, new)
                r = compare(text, data, lib, family, [kind], max(100, cases // 5))
                f = r['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    previous = loaders.REGISTRATIONS
    try:
        loaders.REGISTRATIONS = REGISTRATIONS
        result['registrations'] = loaders.registrations(text, data)
    finally:
        loaders.REGISTRATIONS = previous
    bodies = {'glow_create': (0x015c92c4, 0x015c9409), 'ember_create': (0x015c6af3, 0x015c6bcd),
              'mist_create': (0x015ed94f, 0x015edbef), 'burst_create': (0x015f29c6, 0x015f2aea),
              'flare_create': (0x015f96f1, 0x015f9835), 'spiral_create': (0x015faa34, 0x015fabbd),
              'glow_move': (0x0163a666, 0x0163a877), 'ember_move': (0x0163685b, 0x01636a33),
              'mist_move': (0x01661b07, 0x01661c56), 'burst_move': (0x0166920a, 0x016696f4),
              'flare_move': (0x016725c5, 0x0167276e), 'spiral_move': (0x01673f85, 0x0167440d),
              'euler_rotate': (0x0185c113, 0x0185c354)}
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
