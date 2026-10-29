#!/usr/bin/env python3
"""RENDER-EFFECTS-006: the owned world-object effects and their particle kinds.

fx_create/fx_move: CreateEffect 0x013c0f19 and MoveEffect 0x0142fd09 for the
effects the world objects create with themselves as owner (validate_skill_fx's
harness): the bat 0x195/0 (Kubera and Kardamahal type 161), the shoal 0x199/0
and /1 (Swamp of Darkness 176, Gray Aida 0x46, Twisted Karutan 196, Swamp of
Destruction 185) and the sea leaf 0x59a/3 (Acheron 57, Swamp of Darkness 83,
Old Kethotum 0xa5). The owner is always an object (0x195 and 0x59a read its
scale +0xa0 without a test); the record's +0x110 start point and +0xcc swing are
defined inputs of the move family.

pt_create/pt_move/pt_render: the CreateParticle core, MoveParticles and
RenderParticles record bodies (validate_particles) for the kinds those effects
and Old Kethotum type 15 emit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import pins  # noqa: E402
import validate_skill_fx as fx  # noqa: E402
import validate_render_effects as base  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EFFECT_KINDS = [(0x195, 0), (0x199, 0), (0x199, 1), (0x59a, 3)]
PARTICLE_KINDS = []
OWNED = {0x195, 0x59a}


def _patch_harness():
    """The new kinds' inputs: an owner object with a scale, and the move family's start point and swing."""
    fx.OWNED_KINDS = set(fx.OWNED_KINDS) | OWNED
    fx.MOVE_DEFINED = set(fx.MOVE_DEFINED) | {'impact', 'field_cc'}
    if getattr(fx.random_object, 'effects6', False):
        return
    plain_object, plain_effect, plain_case = fx.random_object, fx.random_effect, fx.Case
    _leaf_height = [None]

    def random_object(rng):
        o = plain_object(rng)
        o.scale = fx.f32(rng.choice([1.0, 0.8, 1.3, 0.0, -1.0, float('nan'), fx.vc.rfloat(rng, 0.1, 3.0)]))
        return o

    def random_effect(rng, kind):
        e = plain_effect(rng, kind)
        if kind[0] == 0x199:
            e.lifetime = rng.choice([1000, 999, 51, 50, 5, 1, 0, rng.randrange(-2, 1001)])
            e.client_hit = rng.choice([0, 0, 1, 2])
            e.velocity = fx.f32(rng.choice([1.0, -1.0, 0.5, -0.5, fx.vc.rfloat(rng, 0.1, 2.0)]))
            e.field_cc = fx.f32(rng.choice([1.0, -1.0, 2.0, -3.0, fx.vc.rfloat(rng, 0.1, 4.0)]))
            for k in range(3):   # within and beyond the 500-unit turn-back radius
                e.impact[k] = fx.f32(e.position[k] + rng.choice([0.0, 100.0, -280.0, 290.0, 400.0, 600.0,
                                                                rng.uniform(-700.0, 700.0)]))
        else:
            e.field_cc = fx.vc.rfloat(rng, 0.1, 4.0)
            for k in range(3):
                e.impact[k] = fx.vc.rfloat(rng, 0.1, 30000.0)
        if kind[0] == 0x59a:
            e.client_hit = rng.choice([0, 1, 2])
            e.lifetime = rng.choice([250, 249, 5, 1, 0, rng.randrange(-2, 251)])
            # the next Case's terrain height sits the leaf at the 50 / 150 bounds (directed samples)
            gap = rng.choice([None, 50.0, 49.75, 50.25, 150.0, 149.75, 150.25, 100.0, 10.0, 300.0])
            _leaf_height[0] = None if gap is None else fx.f32(e.position[2] - gap)
        return e

    class Case(plain_case):
        def __init__(self, rng, objects, rand_values, height, *rest, **named):
            if _leaf_height[0] is not None:
                height, _leaf_height[0] = _leaf_height[0], None
            super().__init__(rng, objects, rand_values, height, *rest, **named)
    random_object.effects6 = True
    fx.random_object, fx.random_effect, fx.Case = random_object, random_effect, Case


MUTANTS = [
    # (name, old, new, family)
    ('shoal-life', 'e->lifetime = 1000;', 'e->lifetime = 999;', 'effect_create'),
    ('shoal-spread', '((float)smod(env_rand(env), 200) - 100.0f)', '((float)smod(env_rand(env), 200) - 99.0f)',
     'effect_create'),
    ('shoal-order', 'for (int k = 2; k >= 0; --k)\n            e->position[k] = ((float)',
     'for (int k = 0; k < 3; ++k)\n            e->position[k] = ((float)', 'effect_create'),
    ('shoal-light', 'e->light[2] = e->blend_light / 4.0f;', 'e->light[2] = e->blend_light / 10.0f;',
     'effect_create'),
    ('shoal-sub1', 'if (subtype == 1)\n            copy3(e->light, light);', 'if (subtype == 0)\n            copy3(e->light, light);',
     'effect_create'),
    ('bat-turn', '(float)smod(env_rand(env), 60) + e->angle[2]', '(float)smod(env_rand(env), 64) + e->angle[2]',
     'effect_create'),
    ('bat-drift', 'e->direction[1] = -20.0f * o->scale;', 'e->direction[1] = -20.0f;', 'effect_create'),
    ('leaf-drift', 'e->direction[1] = -5.0f * o->scale;', 'e->direction[1] = -5.0f * o->scale * 2.0f;',
     'effect_create'),
    ('leaf-unlit', 'e->flag5 = 0;\n        e->client_hit', 'e->flag5 = 1;\n        e->client_hit', 'effect_create'),
    ('shoal-radius', 'length >= 500.0f && e->client_hit == 0', 'length > 600.0f && e->client_hit == 0',
     'effect_move'),
    ('shoal-swing', 'e->gravity = ((float)smod(env_rand(env), 3) + 5.0f) * e->velocity;',
     'e->gravity = ((float)smod(env_rand(env), 3) + 4.0f) * e->velocity;', 'effect_move'),
    ('shoal-pitch', '* e->field_cc / 3.0f + e->angle[0]', '* e->field_cc / 2.0f + e->angle[0]', 'effect_move'),
    ('shoal-trail', 'e->light, 9, e->scale, MU_SFX_NO_OWNER);', 'e->light, 9, 1.0f, MU_SFX_NO_OWNER);',
     'effect_move'),
    ('bat-climb', 'e->position[2] = (float)smod(env_rand(env), 15) * F_0_3 + e->position[2];',
     'e->position[2] = (float)smod(env_rand(env), 16) * F_0_3 + e->position[2];', 'effect_move'),
    ('bat-generic', 'mu_sfx_effect_advance(e, 1);\n        e->position[2] = (float)smod',
     'mu_sfx_effect_advance(e, 0);\n        e->position[2] = (float)smod', 'effect_move'),
    ('leaf-floor', 'if (h + 50.0f > e->position[2]) {', 'if (h + 60.0f > e->position[2]) {', 'effect_move'),
    ('leaf-ceiling', 'if (e->position[2] > h + 150.0f) {', 'if (e->position[2] >= h + 160.0f) {', 'effect_move'),
    ('leaf-glow', 'light[0] = lum * f32bits(0x3f19999au);', 'light[0] = lum * F_1_2;', 'effect_move'),
    ('leaf-spark', 'if (env_rand(env) % 3 != 0)\n        return;', 'if (env_rand(env) % 4 != 0)\n        return;',
     'effect_move'),
    ('leaf-spark-owner', '1.1, 0x01a889d0 */, -2);', '1.1, 0x01a889d0 */, -1);', 'effect_move'),
]


def effect_families(text, data, lib, cases):
    _patch_harness()
    out = {}
    for name in ('effect_create', 'effect_move'):
        r = base.compare(text, data, lib, 'fx', name, EFFECT_KINDS, cases)
        f = r['families'][name]
        out['fx_' + name.split('_')[1]] = {'cases': f['cases'], 'mismatches': f['cases'] - f['equal'],
                                            'coverage': r['coverage'][name],
                                            'first': f['first_failures'][:2]
                                            if f['cases'] != f['equal'] else []}
    return out


def effect_mutants(text, data, cases):
    _patch_harness()
    caught = {}
    with tempfile.TemporaryDirectory(prefix='render-effects6-fx-') as tmp:
        for name, old, new, family in MUTANTS:
            lib = base.compile_mutant(Path(tmp), name, 'fx', old, new)
            f = base.compare(text, data, lib, 'fx', family, EFFECT_KINDS, cases)['families'][family]
            caught[name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    return caught


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=400, help='cases per effect family')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    for d in ('combat', 'particles'):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed'/d)], check=True)
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    lib = fx.load_library(ROOT/'reconstructed/combat'/('libcombat.' + fx.SUFFIX))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}, 'mutants': {}}
    report['families'].update(effect_families(text, data, lib, a.cases))
    if a.mutations:
        report['mutants'].update(effect_mutants(text, data, max(100, a.cases // 2)))
    bodies = {'shoal_create': (0x013c39d9, 0x013c3d67), 'bat_create': (0x013c3d67, 0x013c3eab),
              'leaf_create': (0x013f5b63, 0x013f5c21), 'shoal_move': (0x01435aed, 0x01435e18),
              'bat_move': (0x01435e18, 0x01435ef3), 'leaf_move': (0x014ed512, 0x014eda52),
              'skip_list': (0x014ecb6e, 0x014ecd35), 'effect_wrapper': (0x013c0eaa, 0x013c0f19)}
    report['bodies'] = {k: hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()[:16]
                        for k, (s, e) in bodies.items()}
    report['instruction_cases'] = sum(f['cases'] for f in report['families'].values())
    report['all_equal'] = all(f['mismatches'] == 0 for f in report['families'].values())
    report['all_mutants_caught'] = all(m['caught'] > 0 for m in report['mutants'].values())
    text_out = json.dumps(report, indent=2) + '\n'
    if a.output:
        a.output.write_text(text_out)
    print(text_out)
    raise SystemExit(not (report['all_equal'] and (not a.mutations or report['all_mutants_caught'])))


if __name__ == '__main__':
    main()
