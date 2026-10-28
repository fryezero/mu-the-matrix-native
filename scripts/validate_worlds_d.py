#!/usr/bin/env python3
"""RENDER-WORLDS-D: production C warp lifecycle/render selection and Noria placement.

Pinned original instructions, defined-memory Unicorn execution, recording engine
stubs. Shared create/move families compare fields, caller-light mutation, ordered
calls and RNG consumption. Render runs the live/frustum/alpha gates and original
switch; RenderObject itself is a recording stub. No live client is used.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import validate_skill_fx as fx
import validate_object_render as obj
import actor_machine as am

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(t, s) for t in range(0x1a8, 0x1ae) for s in (0, 1, 2)]


def render(machine, lib, rng, cases, report):
    lib.mu_world_warp_render.argtypes = [C.POINTER(fx.Effect), C.c_void_p, C.c_void_p, C.c_int, C.c_int]
    for n in range(cases):
        e = fx.random_effect(rng, KINDS[n % len(KINDS)])
        e.live = rng.choice([0, 1, 1, 2, 3])
        e.blend_mesh = rng.choice([-3, -2, -1, 0, 2, 4])
        alpha, meshes = rng.randrange(2), rng.randrange(4)
        normals = [rng.choice([-1.0, 0.0, 1.0]) for _ in range(15)]
        distances = [fx.f32(rng.uniform(-30000, 30000)) for _ in range(5)]
        # Include exact plane boundaries as well as either side of the sphere.
        if n % 3 == 0:
            normals = [0.0] * 15
            distances = [400.0] * 5
            distances[n % 5] = rng.choice([-400.0, -400.00003, -399.99997])
        raw, mask = fx.effect_to_bytes(e, fx.MOVE_DEFINED | {'visible'})
        regions = [am.Region('record', fx.POOL, raw, mask),
                   am.defined_region('world', fx.WORLD, struct.pack('<i', 3), writable=False),
                   am.defined_region('normals', 0x0bdb546c, struct.pack('<15f', *normals), writable=False),
                   am.defined_region('distances', 0x0b6b53e4, struct.pack('<5f', *distances), writable=False),
                   am.defined_region('model', fx.MODEL, bytes(0x24) + struct.pack('<h', meshes), writable=False)]
        calls = []
        def draw(m):
            calls.append([m.argument(k) for k in range(6)])
            return 0
        stubs = {fx.MODEL_CONTAINER: lambda m: fx.CONTAINER,
                 fx.MODEL_GETTER: lambda m: (fx.MODEL, 0), 0x16d4fe4: draw,
                 0x15324fc: lambda m: m.stop(('end',)), 0x151826a: lambda m: m.stop(('end',)),
                 0x1532501: lambda m: m.stop(('end',))}
        r = machine.execute(0x15182c6, [alpha], regions, stubs,
                            frame=(0x1c04, {-0x10: fx.POOL}))
        selected = lib.mu_world_warp_render(C.byref(e), (C.c_float * 15)(*normals),
                                             (C.c_float * 5)(*distances), alpha, meshes)
        expected = [[fx.POOL, 0, 0, 0, 0xffffffff, 0xffffffff]] if selected else []
        diff = fx.compare_effect(e, r['regions']['record'], mask, {'visible'}) if r.get('regions') else 'stopped'
        ok = r['stopped'] == ('end',) and diff is None and calls == expected
        report.add('warp_render', ok, {'case': n, 'type': e.type, 'stopped': r['stopped'],
                   'error': r['error'], 'checks': r['checks'], 'calls': calls, 'c': expected, 'diff': diff})
        report.cover('warp_render', hex(e.type))


def noria(machine, lib, rng, cases, report):
    lib.mu_noria_records.argtypes = [C.POINTER(obj.Record)]
    for n in range(cases):
        calls = []
        def ctor(m):
            a = [m.argument(k) for k in range(10)]
            r = obj.Record()
            r.type = a[0]
            r.position[:] = [fx.from_bits(x) for x in obj.read_vec(m, a[1])]
            r.angle[:] = [fx.from_bits(x) for x in obj.read_vec(m, a[2])]
            r.scale = fx.from_bits(a[3])
            r.flag_2c, r.flag_2d, r.flag_2e, r.hidden = a[4:8]
            r.value_30, r.value_34 = map(fx.from_bits, a[8:])
            calls.append(bytes(r))
            return obj.RECORD, 40
        stubs = {0xd7fb55: ctor, 0x16d8538: lambda m: 0,
                 0x1839952: lambda m: m.stop(('end',))}
        r = machine.execute(0x1839870, [], obj.global_regions(3), stubs, frame=(0x2500, {}))
        record = obj.Record()
        count = lib.mu_noria_records(C.byref(record))
        report.add('noria_placement', r['stopped'] == ('end',) and count == 1 and calls == [bytes(record)],
                   {'case': n, 'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks'],
                    'c': bytes(record).hex(), 'calls': [x.hex() for x in calls]})


class Report(fx.vc.Report):
    def add(self, family, equal, failure=None):
        super().add(family, equal, failure)
        entry = self.families[family]
        entry.setdefault('stopped', 0)
        entry['stopped'] += failure is not None and failure.get('stopped') not in (None, ('end',))


def run(machine, lib, cases):
    report = Report()
    fx.EFFECT_KINDS = KINDS
    for name, fn in [('effect_create', fx.family_effect_create), ('effect_move', fx.family_effect_move)]:
        # These families' old negative controls target other effect kinds.
        from collections import defaultdict
        fn(machine, lib, random.Random('worlds-d-' + name), cases, report, defaultdict(int))
    render(machine, lib, random.Random('worlds-d-render'), cases, report)
    noria(machine, lib, random.Random(1), cases, report)
    return report


MUTANTS = [
    ('warp lifetime', 'world_warp.c', 'e->lifetime = 0xffffff;', 'e->lifetime = 100;'),
    ('warp blend mesh', 'world_warp.c', 'e->blend_mesh = -2;', 'e->blend_mesh = -1;'),
    ('caller light write', 'world_warp.c', 'source_light[0] = source_light[1] = source_light[2] = 0.0f;', '(void)source_light;'),
    ('warp pulse clock', 'world_warp.c', 'world_time * 0.0017f', 'world_time * 0.0011f'),
    ('warp rotation', 'world_warp.c', '(2.0f + e->gravity)', '(4.0f + e->gravity)'),
    ('warp visibility', 'world_warp.c', 'if (-400.0f > distance)', 'if (-200.0f > distance)'),
    ('warp alpha gate', 'world_warp.c', 'model_meshes < e->blend_mesh', 'model_meshes <= e->blend_mesh'),
    ('Noria coordinate', 'noria.c', '22300.0f', '22400.0f'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=600)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    text = am.load_pinned(ROOT/'evidence/x86-text-capture-09/client-text.bin', am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin', am.DATA_BYTES, am.DATA_SHA256, 'data')
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    machine = fx.FxMachine(text, data)
    with tempfile.TemporaryDirectory(prefix='worlds-d-') as td:
        tmp = Path(td)
        def build(mutant=None):
            sources = [ROOT/'reconstructed/combat/combat.c', ROOT/'reconstructed/combat/skill_fx.c', ROOT/'reconstructed/objects/world_warp.c',
                       ROOT/'reconstructed/objects/noria.c', ROOT/'reconstructed/objects/objects.c',
                       ROOT/'reconstructed/model-codec/model_codec.c', ROOT/'reconstructed/joints/joints.c',
                       ROOT/'reconstructed/record-math/record_math.c', ROOT/'reconstructed/movement/client_movement.c']
            if mutant:
                name, filename, old, new = mutant
                src = next(s for s in sources if s.name == filename)
                content = src.read_text()
                assert content.count(old) == 1, name
                path = tmp/filename
                path.write_text(content.replace(old, new))
                sources[sources.index(src)] = path
            libpath = tmp/('lib'+str(len(list(tmp.glob('*.dylib'))))+'.dylib')
            subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-fPIC', '-ffp-contract=off', '-fno-fast-math',
                            '-I', str(ROOT/'reconstructed/objects'), '-I', str(ROOT/'reconstructed/combat'),
                            *map(str, sources), '-lm', '-o', str(libpath)], check=True, capture_output=True)
            return fx.load_library(libpath)
        baseline = run(machine, build(), a.cases)
        mutants = []
        if a.mutations:
            for mutant in MUTANTS:
                result = run(machine, build(mutant), min(a.cases, 180))
                detected = sum(f['cases'] - f['equal'] for f in result.families.values())
                stopped = sum(f['stopped'] for f in result.families.values())
                mutants.append({'name': mutant[0], 'detected': detected, 'stopped': stopped})
    spans = {'create': (0x13c38ef,0x13c39d9), 'move': (0x1435834,0x1435aed),
             'render': (0x15182c6,0x1518d8d), 'noria': (0x1839870,0x1839952)}
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256,
              'bodies': {k: {'start': hex(x), 'end': hex(y), 'sha256': hashlib.sha256(text[x-am.TEXT_BASE:y-am.TEXT_BASE]).hexdigest()} for k,(x,y) in spans.items()},
              'families': baseline.families, 'coverage': baseline.coverage, 'mutants': mutants}
    Path(a.output).write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: {'cases':v['cases'], 'equal':v['equal'], 'first_failures':v['first_failures'][:1]} for k,v in baseline.families.items()}, default=str))
    print(json.dumps(mutants))
    return 0 if all(v['cases'] == v['equal'] for v in baseline.families.values()) and all(m['detected'] > 0 and m['stopped'] == 0 for m in mutants) else 1


if __name__ == '__main__':
    raise SystemExit(main())
