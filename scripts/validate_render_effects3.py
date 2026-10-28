#!/usr/bin/env python3
"""RENDER-EFFECTS-003 original-instruction families and compiled production mutants.

Ordinary-world Meteorite, Inferno subtype-zero burst, Spark02/2 and Explosion01/0.
Fresh strict machines per family/mutant. Terrain, model, audio and creator services
are recorded stubs; GPU and session routing have separate native tests.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import tempfile

import actor_machine as am
import pins
import validate_render_effects as base
import validate_skill_fx as fx
import validate_particles as pt

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = [
    ('aqua_speed', 'fx', 'const float v[3] = {0.0f, -50.0f, 0.0f};', 'const float v[3] = {0.0f, -40.0f, 0.0f};', 'effect_create', (0x7f4e, 0)),
    ('aqua_count', 'fx', 'for (int k = 0; k < 20; ++k) {\n        mu_sfx_call c;', 'for (int k = 0; k < 19; ++k) {\n        mu_sfx_call c;', 'aqua_render', None),
    ('meteor_life', 'fx', 'e->lifetime = 40;\n            e->scale', 'e->lifetime = 39;\n            e->scale', 'effect_create', (0x413, 0)),
    ('meteor_fall', 'fx', 'e->direction[2] = -50.0f;', 'e->direction[2] = -40.0f;', 'effect_create', (0x413, 0)),
    ('meteor_stones', 'fx', 'for (int k = 0; k < 6; ++k)\n                    call_effect', 'for (int k = 0; k < 5; ++k)\n                    call_effect', 'effect_move', (0x413, 0)),
    ('inferno_sparks', 'fx', 'for (int k = 0; k < 20; ++k) {\n        angle[0]', 'for (int k = 0; k < 19; ++k) {\n        angle[0]', 'burst', None),
    ('inferno_height', 'fx', 'float p[3] = {position[0], position[1], position[2] + 80.0f};', 'float p[3] = {position[0], position[1], position[2] + 70.0f};', 'burst', None),
    ('spark_speed', 'pt', 'v[k] = 3.0f * v[k]', 'v[k] = 2.0f * v[k]', 'create', (0x7f25, 2)),
    ('explosion_frames', 'pt', 'p->frame = (20 - p->lifetime) / 2;', 'p->frame = (20 - p->lifetime) / 3;', 'move', (0x7f54, 0)),
    ('explosion_sheet', 'pt', 's->u = (float)(p->frame % 4) * 0.25f + 0.005f;', 's->u = (float)(p->frame % 4) * 0.25f;', 'render', (0x7f54, 0)),
]


def burst(text, data, lib, cases):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    m = fx.FxMachine(text, data)
    rng = random.Random('render-effects-003-burst')
    report = pt.Report()
    lib.mu_sfx_inferno_burst.argtypes = [C.POINTER(C.c_float), C.c_uint8, C.POINTER(fx.Env)]
    lib.mu_sfx_inferno_burst.restype = None
    for n in range(cases):
        pos = [fx.f32(rng.uniform(-30000, 30000)) for _ in range(3)]
        visible = rng.choice([0, 1, 2, 255])
        case = fx.Case(rng, [], fx.rand_values(rng), 0.0)
        region = am.defined_region('inputs', fx.INPUTS, struct.pack('<3f', *pos), writable=False)
        r = m.execute(0x013c07f4, [fx.INPUTS, visible, 0], [region], case.stubs(m))
        env = case.env()
        lib.mu_sfx_inferno_burst((C.c_float*3)(*pos), visible, C.byref(env))
        mismatch = fx.compare_calls(case.client_calls, case.c_calls) if fx.vc.ok(r) else r['stopped']
        equal = fx.vc.ok(r) and mismatch is None and case.c_rand == case.client_rand
        report.add('burst', equal, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped']})
        report.cover('burst', 'visible' if visible else 'sparks only')
    return {'families': report.families, 'coverage': report.coverage}


def aqua_render(text, data, lib, cases):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    m = fx.FxMachine(text, data)
    rng = random.Random('render-effects-003-aqua-render')
    report = pt.Report()
    lib.mu_sfx_aqua_render.argtypes = [C.POINTER(fx.Effect), C.POINTER(fx.Env)]
    lib.mu_sfx_aqua_render.restype = None
    for n in range(cases):
        e = fx.random_effect(rng, (0x7f4e, 0))
        e.owner = -1
        case = fx.Case(rng, [], fx.rand_values(rng), 0.0)
        raw, mask = fx.effect_to_bytes(e, fx.MOVE_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        stubs = case.stubs(m)
        stubs.update({0x015324fc: fx.jump_stub(0x01532501), 0x00d8b3e3: lambda mm: 0})
        r = m.execute(0x01519c06, [0], [record], stubs,
                      frame=pt.mid_frame(0xc+0x1bf0+8, {-0x10: fx.POOL}), cleanup=4)
        env = case.env()
        lib.mu_sfx_aqua_render(C.byref(e), C.byref(env))
        mismatch = fx.compare_calls(case.client_calls, case.c_calls) if fx.vc.ok(r) else r['stopped']
        if fx.vc.ok(r) and mismatch is None:
            mismatch = fx.compare_effect(e, r['regions']['record'], record.defined, fx.MOVE_DEFINED)
        report.add('aqua_render', fx.vc.ok(r) and mismatch is None,
                   {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        report.cover('aqua_render', '20 sprites and 20 lights')
    return {'families': report.families, 'coverage': report.coverage}


def compare(text, data, lib, domain, name, kinds, cases):
    if name == 'aqua_render': return aqua_render(text, data, lib, cases)
    return (burst(text, data, lib, cases) if name == 'burst' else
            base.compare(text, data, lib, domain, name, kinds, cases))


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    for domain, names, kinds in [('fx', ['effect_create', 'effect_move', 'burst', 'aqua_render'], [(0x413, 0), (0x7f4e, 0)]),
                                  ('pt', ['create', 'move', 'render'], [(0x7f25, 2), (0x7f54, 0)])]:
        lib = (fx if domain == 'fx' else pt).load_library(ROOT/'reconstructed'/
            ('combat/libcombat.' + fx.SUFFIX if domain == 'fx' else 'particles/libclient_particles.' + fx.SUFFIX))
        for name in names:
            result['comparisons'][domain + '_' + name] = compare(text, data, lib, domain, name, kinds,
                                                                 cases * (1 if name in ('burst', 'aqua_render') else len(kinds)))
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects3-mutants-') as tmp:
            for name, domain, old, new, family, kind in MUTANTS:
                lib = base.compile_mutant(Path(tmp), name, domain, old, new)
                report = compare(text, data, lib, domain, family, [kind], max(60, cases // 5))
                f = report['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    bodies = {'aqua_render': (0x01519c06, 0x0151a406), 'aqua_create': (0x013c6a04, 0x013c702a), 'inferno_burst': (0x013c07f4, 0x013c0e0a),
              'meteor_create': (0x013d2f05, 0x013d306c), 'meteor_impact': (0x0146c821, 0x0146cd97),
              'spark_create': (0x015dc098, 0x015dc87d), 'explosion_create': (0x015e42eb, 0x015e43cd),
              'explosion_move': (0x01622ea1, 0x01623c2e), 'explosion_render': (0x015925e6, 0x015926cd)}
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
