#!/usr/bin/env python3
"""RENDER-EFFECTS-025: missing-name sprite state, Ferea clouds/28 and two bow pairs.

Original instructions run on declared offline records. A separate pre-bone record
models the original -1 access without indexing before a native bone allocation.
"""
import argparse
import io
import subprocess
import sys
from collections import defaultdict
import ctypes as C
import json
from pathlib import Path
import random
import re
import tempfile
import time

import pins
import actor_machine as am
import validate_particles as pt
import validate_item_predraw as pre
import validate_item_quality as quality
import validate_render_effects11 as re11
import validate_render_effects23 as re23
import validate_renderchar as rc

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x7f89, 28), (0x8109, 7), (0x810a, 9)]
CLOCKS = [0.0, 39.0, 123456.0, 1000000.0, -98765.0]
# The 96 programs present at this lane's baseline. Later admissions remain in the
# reported inventory without silently becoming a claim that this lane ported them.
CENSUS_PROGRAMS = frozenset({
    0xb27, 0xb2a, 0xb4b, 0xb4c, 0xb4f, 0xb50, 0xb53, 0xb57, 0xb59, 0xf1c, 0xf1d, 0xf1f,
    0xf20, 0xf24, 0xf28, 0xf29, 0xf2a, 0xf2b, 0xf2c, 0xf2e, 0x130d, 0x1311, 0x1312, 0x1313,
    0x1316, 0x1317, 0x1319, 0x131d, 0x1748, 0x1749, 0x1758, 0x19f4, 0x19fa, 0x1a00, 0x1a1f, 0x1a78,
    0x1bc3, 0x1bc4, 0x1bc5, 0x1bc6, 0x1bc7, 0x1bc8, 0x1bc9, 0x1bca, 0x1bcb, 0x1bcc, 0x1bcd, 0x1bce,
    0x1bcf, 0x1bd0, 0x1bdd, 0x1bde, 0x1bef, 0x1bf0, 0x1bf4, 0x1bf5, 0x1bf6, 0x1bf7, 0x1bf8, 0x1bf9,
    0x1bfa, 0x1bfb, 0x1bfc, 0x1bfd, 0x1bfe, 0x1bff, 0x1c00, 0x1c01, 0x1c1e, 0x1c1f, 0x1c41, 0x1c42,
    0x1c77, 0x1c78, 0x22ec, 0x230b, 0x230c, 0x2311, 0x2382, 0x2383, 0x2384, 0x2385, 0x2394, 0x2395,
    0x23ef, 0x2400, 0x2405, 0x248f, 0x2494, 0x2496, 0x2499, 0x24cf, 0x24d6, 0x26f8, 0x26f9, 0x2713,
})


def request_census(lib):
    inventory = re23.request_census(lib)
    header = (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text()
    present = set()
    for name in ('mu_rc_fx_types', 'mu_rc_fx_pre_types'):
        present.update(int(t, 0) for t in re.findall(r'^    \{([^,]+),',
                       header.split(name+'[] = {')[1].split('};')[0], re.M))
    pairs = {}
    for key, entry in inventory['pairs'].items():
        programs = [t for t in entry['programs'] if int(t, 0) in CENSUS_PROGRAMS]
        if programs:
            pairs[key] = dict(entry, programs=programs)
    return dict(programs=len(present & CENSUS_PROGRAMS), particle_pairs=len(pairs), pairs=pairs,
                unresolved=[r for r in inventory['unresolved'] if int(r['type'], 0) in CENSUS_PROGRAMS],
                missing_programs=[hex(t) for t in sorted(CENSUS_PROGRAMS - present)],
                later_programs=[hex(t) for t in sorted(present - CENSUS_PROGRAMS)], inventory=inventory)


def particle_family(text, data, lib, name, cases, report):
    saved = pt.KINDS, pt.random_particle, pt.Case, pt.globals_region
    ordinal = 0
    clock = 0.0

    def particle(rng, kind):
        nonlocal ordinal
        p = saved[1](rng, kind)
        p.live = 1
        p.lifetime, p.initial_lifetime = [(300, 300), (151, 300), (150, 300), (149, 300), (1, 300),
                                         (0, 300), (1, 0), (1, -1), (500, 300), (7, 12), (6, 12),
                                         (5, 12), (10, 10), (1, 10)][(ordinal // len(KINDS)) % 14]
        p.owner = -1 if (ordinal // len(KINDS)) % 2 else 0
        if kind == (0x810a, 9):
            p.scale = pt.f32([0.01, 0.035, 0.04, 0.0, -0.1, 1.0][(ordinal // len(KINDS)) % 6])
        ordinal += 1
        return p

    class Case(saved[2]):
        def host(self, world=0, world_time=0.0, *a, **kw):
            return super().host(world, clock if name == 'move' else world_time, *a, **kw)

    def globals_region(world=0, world_time=0.0, *a, **kw):
        nonlocal clock
        clock = CLOCKS[ordinal % len(CLOCKS)]
        return saved[3](world, clock if name == 'move' else world_time, *a, **kw)

    try:
        pt.KINDS, pt.random_particle, pt.Case, pt.globals_region = KINDS, particle, Case, globals_region
        r = pt.Report()
        getattr(pt, 'family_'+name)(pt.PtMachine(text, data), lib, random.Random('effects25-'+name),
                                    cases * len(KINDS), r, defaultdict(int))
        report.families['particle_'+name] = r.families[name]
        report.coverage['particle_'+name] = r.coverage.get(name, {})
    finally:
        pt.KINDS, pt.random_particle, pt.Case, pt.globals_region = saved


def missing_name(cases, report, lib=None):
    from item_body_machine import ResetWorld
    lib = lib or C.CDLL(str(rc.LIBRARY))
    plib = pre.ownerfx.particles_library()
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    reset = ResetWorld(wa, pre.ItemWorld)
    names, consts = pre.program_names()
    rng = random.Random('effects25-missing-name')
    t = 0x0f29
    states = [c for _, c in quality.state_cases(t)]
    for n in range(cases):
        case = dict(states[n % len(states)])
        o = pre.item_setup(rng, t, 3, names[t], consts[t])
        o['records'], o['hidden'], o['frame'] = True, n % 7 == 1, n % 16
        o['names'] = ['decoy'] * o['count']
        for i, name in enumerate(names[t]):
            o['names'][i] = name if name != 'up01' else 'up01 '
        o['before_matrix'] = ([0.0] * 12 if n % 4 == 0 else
                              [pre.f32(rng.uniform(-200, 200)) for _ in range(12)])
        case['frame'] = o['frame']
        expected = pre.original(wa, reset, case, o)
        actual = pre.run_c(lib, plib, case, o, expected[3])
        ok, refused = pre.same(expected, actual)
        report.add('missing_name', ok and refused == 0, {'case': n, 'refused': refused,
                   'stream_equal': expected[0] == actual[1], 'requests_equal': expected[1] == actual[2],
                   'client': expected[1][:3] if not ok else [], 'native': actual[2][:3] if not ok else []})
        report.cover('missing_name', 'hidden' if o['hidden'] else 'visible')
        report.cover('missing_name', 'zero record' if n % 4 == 0 else 'arbitrary record')


def build_host(directory, renderchar=None):
    native = ROOT/'native'
    directory = Path(directory)
    source = (native/'tests/effects25_host.c').read_text().replace(
        '#include "../core/mu_renderchar.c"', f'#include "{renderchar or native/"core/mu_renderchar.c"}"')
    (directory/'host.c').write_text(source)
    obj, host = directory/'host.o', directory/'host'
    subprocess.run(['clang', '-std=c11', '-O1', '-ffp-contract=off', '-I', str(native/'build/gen'),
                    '-I', str(native/'session'), '-iquote', str(native/'core'), '-c', str(directory/'host.c'),
                    '-o', str(obj)], check=True, capture_output=True)
    command = ['clang++', str(obj), str(native/'build/libmunative.a'),
               str(native/'build/libmusession_world.a'), '-lm', '-o', str(host)]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    subprocess.run(command, check=True, capture_output=True)
    return host


def cloud_fixture(directory):
    from PIL import Image
    root = Path(directory)/'game'
    effect = root/'Data/Effect'
    effect.mkdir(parents=True)
    buf = io.BytesIO()
    Image.new('RGB', (32, 32), (128,128,128)).save(buf, format='JPEG', quality=100)
    (effect/'clouds.OZJ').write_bytes(bytes(24)+buf.getvalue())
    return root


def native_check(host, root, report):
    p = subprocess.run([str(host), str(root)], capture_output=True, text=True)
    report.add('native', p.returncode == 0 and 'clouds/28 raster routing OK' in p.stdout,
               dict(exit=p.returncode, stderr=p.stderr[-1000:]))


PT_MUTANTS = [
    ('cloud_admission', 'ferea_clouds.inc', 'subtype == 28;', 'subtype == 27;', 'create'),
    ('cloud_life', 'ferea_clouds.inc', 'p->lifetime = 300;', 'p->lifetime = 301;', 'create'),
    ('cloud_jitter', 'ferea_clouds.inc', 'const float dx = rand_range(h, -250.0f, 250.0f, 10) * scale;',
     'const float dx = rand_range(h, -240.0f, 250.0f, 10) * scale;', 'create'),
    ('cloud_start', 'ferea_clouds.inc', 'copy3(p->start, p->position);', '', 'create'),
    ('cloud_size', 'ferea_clouds.inc', 'rand_range(h, 0.5f, 1.5f, 100)',
     'rand_range(h, 0.6f, 1.5f, 100)', 'create'),
    ('cloud_pulse', 'ferea_clouds.inc', '* 360.0f + 180.0f)', '* 360.0f + 0.0f)', 'move'),
    ('cloud_clock', 'ferea_clouds.inc', '* 0.00019999999494757503f;', '* 0.002f;', 'move'),
    ('cloud_orbit_axis', 'ferea_clouds.inc', 'p->angle[2] * 0.01745329238474369f;',
     'p->angle[1] * 0.01745329238474369f;', 'move'),
    ('cloud_spin', 'ferea_clouds.inc', 'p->rotation + 0.7f;', 'p->rotation + 0.6f;', 'move'),
    ('cloud_render', 'particles.c', 'p->subtype == 0x14 || p->subtype == 28', 'p->subtype == 0x14', 'render'),
    ('bow7_life', 'item_bow_kinds.inc', 'p->type == 0x8109 ? 10 : 12', 'p->type == 0x8109 ? 11 : 12', 'create'),
    ('bow9_life', 'item_bow_kinds.inc', 'p->type == 0x8109 ? 10 : 12', 'p->type == 0x8109 ? 10 : 13', 'create'),
    ('bow7_velocity', 'item_bow_kinds.inc', 'rand_range(h, -2.5f, 2.5f, 1)',
     'rand_range(h, -2.5f, 2.5f, 10)', 'create'),
    ('bow7_axis', 'item_bow_kinds.inc', 'const int32_t axis = mu_pt_rand(h) % 3;',
     'const int32_t axis = (mu_pt_rand(h), 0);', 'move'),
    ('bow7_scale', 'item_bow_kinds.inc', 'p->scale = p->initial_scale * ratio;',
     'p->scale = p->scale * ratio;', 'move'),
    ('bow9_pulse', 'item_bow_kinds.inc', 'ratio > 0.5f', 'ratio > 0.6f', 'move'),
    ('bow9_step', 'item_bow_kinds.inc', 'p->scale - 0.035f;', 'p->scale - 0.03f;', 'move'),
    ('bow9_clamp', 'item_bow_kinds.inc', 'if (0.0f > p->scale)', 'if (0.0f < p->scale)', 'move'),
]
RC_MUTANTS = [
    ('missing_disabled', 'bone == -1 && h->item_before_transform', 'bone == -2 && h->item_before_transform'),
    ('missing_wrong_index', 'bone == -1 && h->item_before_transform', 'bone == 0 && h->item_before_transform'),
    ('missing_position', 'h->item_before_transform(h->context, fx.position);',
     'h->item_before_transform(h->context, fx.position); fx.position[0] += 1.0f;'),
]
NATIVE_MUTANTS = [
    ('native_default', 'env->item_before_matrix = before_bones;', 'env->item_before_matrix = NULL;'),
    ('native_translate', 'o->item_before_matrix, zero, out, 1,', 'o->item_before_matrix, zero, out, 0,'),
    ('native_route', 'host.item_before_transform = item_before_transform;', 'host.item_before_transform = NULL;'),
]


def renderchar_mutant(directory, name, old, new):
    folder = Path(directory)/name
    folder.mkdir()
    base = ROOT/'reconstructed/renderchar'
    for file in ('renderchar.c', 'owner_fx.inc', 'rank5_owner.inc'):
        source = (base/file).read_text()
        if file == 'owner_fx.inc':
            if source.count(old) != 1:
                raise ValueError(f'{name}: nonunique anchor')
            source = source.replace(old, new)
        (folder/file).write_text(source)
    lib = folder/('lib.'+pt.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-fPIC', '-ffp-contract=off',
                    '-I', str(base), str(folder/'renderchar.c'),
                    str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(lib)],
                   check=True, capture_output=True)
    return C.CDLL(str(lib))


def mutation_checks(directory, text, data, root):
    mutants = []
    def result(name, report, family):
        f = report.families[family]
        mutants.append(dict(name=name, detected=f['cases']-f['equal'],
                            stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
        print('mutant', json.dumps(mutants[-1]), flush=True)
    for name, file, old, new, family in PT_MUTANTS:
        lib = re11.compile_pt_mutant(directory, name, file, old, new)
        report = pt.Report()
        particle_family(text, data, lib, family, 120, report)
        result(name, report, 'particle_'+family)
    for name, old, new in RC_MUTANTS:
        report = pt.Report()
        missing_name(40, report, renderchar_mutant(directory, name, old, new))
        result(name, report, 'missing_name')
    for name, old, new in NATIVE_MUTANTS:
        folder = Path(directory)/name
        folder.mkdir()
        source = (ROOT/'native/core/mu_renderchar.c').read_text()
        if source.count(old) != 1:
            raise ValueError(f'{name}: nonunique anchor')
        path = folder/'mu_renderchar.c'
        path.write_text(source.replace(old, new))
        report = pt.Report()
        native_check(build_host(folder, path), root, report)
        result(name, report, 'native')
    return mutants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=1000)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    start = time.monotonic()
    text, data = pins.TEXT.read(), pins.DATA.read()
    report = pt.Report()
    lib = pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX))
    for name in ('create', 'move', 'render'):
        particle_family(text, data, lib, name, args.cases, report)
    missing_name(args.cases, report)
    census = request_census(lib)
    report.add('census', not census['missing_programs'] and not census['unresolved'] and
               all(p['supported'] for p in census['pairs'].values()),
               census)
    with tempfile.TemporaryDirectory(prefix='effects25-native-') as tmp:
        root = cloud_fixture(tmp)
        native_check(build_host(tmp), root, report)
        equal = all(f['cases'] == f['equal'] for f in report.families.values())
        mutants = mutation_checks(tmp, text, data, root) if args.mutations and equal else []
    equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result = dict(families=report.families, coverage=report.coverage, all_equal=equal,
                  request_census=census,
                  cases=sum(f['cases'] for f in report.families.values()), mutants=mutants,
                  all_mutants_caught=all(m['detected'] and not m['stopped'] for m in mutants), seconds=round(time.monotonic()-start, 3),
                  text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
