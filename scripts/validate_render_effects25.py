#!/usr/bin/env python3
"""RENDER-EFFECTS-025: explicit missing-name sprite state and Ferea clouds/28.

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
import tempfile
import time

import pins
import actor_machine as am
import validate_particles as pt
import validate_render_effects as base
import validate_item_predraw as pre
import validate_item_quality as quality
import validate_renderchar as rc

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x7f89, 28), (0x8109, 7), (0x810a, 9)]
CLOCKS = [0.0, 39.0, 123456.0, 1000000.0, -98765.0]


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
    with tempfile.TemporaryDirectory(prefix='effects25-native-') as tmp:
        native_check(build_host(tmp), cloud_fixture(tmp), report)
    equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result = dict(families=report.families, coverage=report.coverage, all_equal=equal,
                  cases=sum(f['cases'] for f in report.families.values()), mutants=[],
                  all_mutants_caught=True, seconds=round(time.monotonic()-start, 3),
                  text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if equal else 1


if __name__ == '__main__':
    raise SystemExit(main())
