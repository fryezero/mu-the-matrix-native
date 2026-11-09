#!/usr/bin/env python3
"""RENDER-EFFECTS-022: mace particles and their retained OBJECT points against pinned instructions.

Create/move/render use the original full particle routines. The owned render family supplies all three
OBJECT +0x1f4 points and argument 8 in 0..2, compares the GL-call stream and the record writes, including NULL
owner death. points compares the complete mace RenderObjDraw with op 50's externally visible stores.
Bitmap registration checks read the original startup loader. Rank-5 owner arithmetic is unchanged and covered
by validate_render_effects5; installed-world tests verify the new callers. No live client or client-byte output.
"""
import argparse
from collections import defaultdict
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import time

import actor_machine as am
import pins
import validate_particles as pt
import validate_render_effects11 as re11
import validate_item_predraw as pre
import validate_renderchar as rc
import validate_item_quality as quality

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x810a, 0x25), (0x855d, 1), (0x84d1, 1)]
MUTANTS = [
    ('admit', 'subtype == 0x25', 'subtype == 0x26', 'create', KINDS[0]),
    ('owner', 'if (p->owner == MU_PT_NO_OWNER) {', 'if (p->owner != MU_PT_NO_OWNER) {', 'create', KINDS[0]),
    ('life', '% 11 + 20', '% 11 + 21', 'create', KINDS[0]),
    ('half_scale', 'scale / (float)(p->lifetime / 2)', 'scale / (float)p->lifetime', 'create', KINDS[0]),
    ('start', 'copy3(p->start, p->position);', 'copy3(p->start, p->light);', 'create', KINDS[0]),
    ('red_life', 'p->type == 0x855d ? 20 : 50', 'p->type == 0x855d ? 21 : 50', 'create', KINDS[1]),
    ('moving', 'p->moving = 1;', 'p->moving = 0;', 'create', KINDS[1]),
    ('radius', 'radius = 1.0f', 'radius = 0.5f', 'create', KINDS[1]),
    ('theta', '180.0f * radians, 100', '90.0f * radians, 100', 'create', KINDS[1]),
    ('phi', '360.0f * radians, 100', '180.0f * radians, 100', 'create', KINDS[1]),
    ('speed', 'rand_range(h, 1.5f, 3.0f, 100)', 'rand_range(h, 1.5f, 3.0f, 10)', 'create', KINDS[1]),
    ('smoke_life', 'p->type == 0x855d ? 20 : 50', 'p->type == 0x855d ? 20 : 40', 'create', KINDS[2]),
    ('smoke_velocity', 'rand_range(h, 1.8f, 2.5f, 100)', 'rand_range(h, 1.8f, 2.5f, 10)', 'create', KINDS[2]),
    ('smoke_fade', 'if (p->lifetime > half) p->alpha', 'if (p->lifetime >= half) p->alpha', 'move', KINDS[2]),
    ('grow', 'p->type == 0x810a && p->lifetime > half', 'p->type == 0x810a && p->lifetime >= half', 'move', KINDS[0]),
    ('fade', '1.0f / (float)p->initial_lifetime;', '0.5f / (float)p->initial_lifetime;', 'move', KINDS[1]),
    ('follow', 'point[k] + p->start[k]', 'point[k] - p->start[k]', 'render', KINDS[0]),
    ('colour', 'k < 3; ++k) s->light[k]', 'k < 2; ++k) s->light[k]', 'render', KINDS[2]),
]


def family(text, data, lib, name, kinds, cases, report):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle
    pt.KINDS, pt.OWNED_KINDS = kinds, set()

    def boundary(rng, kind):
        p = saved[2](rng, kind)
        p.live = 1
        p.lifetime, p.initial_lifetime = rng.choice([(30, 30), (16, 30), (15, 30), (14, 30), (11, 21),
                                                    (10, 21), (1, 1), (1, 0), (1, -1), (1, 50), (25, 50)])
        return p
    pt.random_particle = boundary
    try:
        r = pt.Report()
        if name == 'render':
            # The shared harness cycles arg8 by n % 3. Run one kind at a time so the three-kind
            # selection cannot lock 0x810a/0x25 to index zero. Each kind still gets exactly `cases`.
            for kind in kinds:
                pt.KINDS = [kind]
                pt.family_render(pt.PtMachine(text, data), lib, random.Random('effects22-' + name),
                                 cases, r, defaultdict(int), owned_points=True)
        else:
            args = (pt.PtMachine(text, data), lib, random.Random('effects22-' + name), cases * len(kinds),
                    r, defaultdict(int))
            dict(pt.FAMILIES)[name](*args)
        report.families['mace_' + name] = r.families[name]
        report.coverage['mace_' + name] = r.coverage.get(name, {})
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle = saved


def points(cases, report, lib=None):
    from item_body_machine import ResetWorld
    lib = lib or C.CDLL(str(rc.LIBRARY))
    plib = pre.ownerfx.particles_library()
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    reset = ResetWorld(wa, pre.ItemWorld)
    names, consts = pre.program_names()
    rng = random.Random('effects22-points')
    for n in range(cases):
        t = (0x0f1f, 0x0f20, 0x0f2a)[n % 3]
        case = dict(list(quality.state_cases(t))[n % 292][1])
        o = pre.item_setup(rng, t, 3, names[t], consts[t])  # 64 bones, complete anchor domain
        o['records'] = True
        for i, name in enumerate(names[t]):
            o['names'][i] = name
        o['attached'] = n % 2 == 1
        o['owner_matrices'] = [pre.f32(-x) for x in o['matrices']]
        o['hidden'] = n % 7 == 6
        case['frame'] = o['frame']
        expected = pre.original(wa, reset, case, o)
        actual = pre.run_c(lib, plib, case, o, expected[3])
        ok, refused = pre.same(expected, actual)
        report.add('points', ok and o['client_points'] == o['native_points'],
                   {'case': n, 'type': hex(t), 'requests_equal': ok,
                    'points_equal': o['client_points'] == o['native_points']})


def registrations(text, data, report):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for start, end, bitmap, path, wrap in [
            (0x01825c89, 0x01825ca6, 0x855d, b'Effect\\pin_star03_red.jpg', 0x2900),
            (0x0182e960, 0x0182e97d, 0x84d1, b'Item\\texture\\smoke01_strong_red.jpg', 0x2901)]:
        ins = list(md.disasm(text[start-am.TEXT_BASE:end-am.TEXT_BASE], start))
        pushes = [int(i.op_str, 0) for i in ins if i.mnemonic == 'push']
        off = pushes[-1] - am.DATA_BASE
        name = data[off:off+100].split(b'\0')[0]
        report.add('bitmaps', pushes[:5] == [0, 1, wrap, 0x2601, bitmap] and name == path and
                   ins[-1].op_str == '0x185baac', {'bitmap': hex(bitmap), 'path_matches': name == path})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    if a.cases < 1:
        p.error('--cases must be positive')
    source = (ROOT/'reconstructed/particles/item_counter_kinds.inc').read_text()
    bad = [name for name, old, *_ in MUTANTS if source.count(old) != 1]
    if bad:
        raise SystemExit(f'nonunique mutant anchors: {bad}')
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    start = time.monotonic()
    lib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{re11.fx.SUFFIX}')
    r = pt.Report()
    for mode in ('create', 'move', 'render'):
        family(text, data, lib, mode, KINDS, a.cases, r)
    points(max(20, a.cases), r)
    registrations(text, data, r)
    equal = all(f['cases'] == f['equal'] for f in r.families.values())
    mutants = []
    if a.mutations and equal:
        with tempfile.TemporaryDirectory(prefix='effects22-') as tmp:
            for name, old, new, mode, kind in MUTANTS:
                ml = re11.compile_pt_mutant(tmp, name, 'item_counter_kinds.inc', old, new)
                rr = pt.Report()
                family(text, data, ml, mode, [kind], max(120, a.cases), rr)
                f = rr.families['mace_' + mode]
                mutants.append(dict(name=name, detected=f['cases'] - f['equal'], cases=f['cases'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
            # A production interpreter mutant must be caught by the original OBJECT writes, even if all
            # particle/sprite requests still agree. Keep the source copied beside its two local includes.
            folder = Path(tmp)/'point_store'
            folder.mkdir()
            base = ROOT/'reconstructed/renderchar'
            old, new = 'fx.position[0] = r[o->a];', 'fx.position[0] = -r[o->a];'
            for name in ('renderchar.c', 'rank5_owner.inc', 'owner_fx.inc'):
                source = (base/name).read_text()
                if name == 'owner_fx.inc':
                    if source.count(old) != 1:
                        raise AssertionError('point mutant anchor')
                    source = source.replace(old, new)
                (folder/name).write_text(source)
            library = folder/'lib.dylib'
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off', '-I', str(base),
                            str(folder/'renderchar.c'), str(ROOT/'reconstructed/record-math/record_math.c'),
                            '-lm', '-o', str(library)], check=True, capture_output=True)
            rr = pt.Report()
            points(max(20, a.cases), rr, C.CDLL(str(library)))
            f = rr.families['points']
            mutants.append(dict(name='point_store', detected=f['cases']-f['equal'], cases=f['cases'], stopped=0))
            print('mutant', json.dumps(mutants[-1]), flush=True)
    result = dict(families=r.families, coverage=r.coverage, instruction_cases=sum(f['cases'] for f in r.families.values()),
                  all_equal=equal, mutants=mutants, all_mutants_caught=all(m['detected'] and not m['stopped'] for m in mutants),
                  seconds=round(time.monotonic()-start, 3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
