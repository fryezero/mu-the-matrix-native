#!/usr/bin/env python3
"""RENDER-EFFECTS-023: remaining mace particle pairs against pinned original instructions.

Create and move use validate_particles' defined-memory machines. Render compares the ordered GL calls and
record writes, with all three retained OBJECT points, NULL owners and the split-pass height boundaries.
Bitmap checks execute no client: they inspect the pinned original LoadBitmap call instructions and strings.
"""
import argparse
from collections import defaultdict
import ctypes as C
import json
from pathlib import Path
import random
import re
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
KINDS = [(0x85bc, 5), (0x83b8, 8), (0x85fc, 1), (0x8315, 4), (0x8316, 4), (0x8317, 4),
         (0x7ffb, 0), (0x83b3, 0x13), (0x8109, 0xe), (0x8549, 1), (0x82f2, 0x1a), (0x810b, 0xa),
         (0x85fc, 2), (0x807e, 0x18), (0x807f, 0x18), (0x8080, 0x18), (0x8081, 9), (0x8082, 9), (0x8083, 9)]
POINT_KINDS = {(0x7ffb, 0), (0x85fc, 1), (0x85fc, 2)}
MUTANTS = [('admit_line',
  'case 0x85bc: return subtype == 5;',
  'case 0x85bc: return subtype == 6;',
  'create',
  (34236, 5)),
 ('admit_ground2',
  'case 0x85fc: return subtype == 1 || subtype == 2;',
  'case 0x85fc: return subtype == 1 || subtype == 3;',
  'create',
  (34300, 2)),
 ('owner_life', 'p->subtype == 2 ? 50 : 30', 'p->subtype == 2 ? 40 : 30', 'create', (34300, 2)),
 ('owner_initial_scale',
  'p->initial_scale = scale;',
  'p->initial_scale = scale * 2.0f;',
  'create',
  (34300, 1)),
 ('glow_life', 'p->lifetime = 4;', 'p->lifetime = 5;', 'create', (34121, 1)),
 ('snow_life', 'mu_pt_rand(h) % 11 + 20', 'mu_pt_rand(h) % 10 + 20', 'create', (33720, 8)),
 ('shiny_scale',
  'rand_range(h, 0.5f, 1.0f, 100) * scale',
  'rand_range(h, 0.25f, 1.0f, 100) * scale',
  'create',
  (33033, 14)),
 ('shiny_initial_scale',
  'if (p->type == 0x8109) p->initial_scale = p->scale;',
  'if (p->type == 0x8109) p->initial_scale = scale;',
  'create',
  (33033, 14)),
 ('red_step',
  'else if (p->type == 0x810b) p->initial_scale = (scale - scale * 0.5f)',
  'else if (p->type == 0x810b) p->initial_scale = (scale - scale * 0.25f)',
  'create',
  (33035, 10)),
 ('velocity_source', 'copy3(p->velocity, p->angle);', 'copy3(p->velocity, p->start);', 'create', (33720, 8)),
 ('snow_angle',
  'p->type == 0x83b8 ? 30.0f : 20.0f',
  'p->type == 0x83b8 ? 15.0f : 20.0f',
  'create',
  (33720, 8)),
 ('fire_life', 'p->lifetime = fire ? 16 : 30;', 'p->lifetime = fire ? 17 : 30;', 'create', (33557, 4)),
 ('line_step', '(scale - scale * 0.3f)', '(scale - scale * 0.4f)', 'create', (34236, 5)),
 ('fire_step',
  'else if (fire) p->initial_scale = (scale - scale * 0.5f)',
  'else if (fire) p->initial_scale = (scale - scale * 0.4f)',
  'create',
  (33558, 4)),
 ('smoke_step', '(scale * 2.0f - scale)', '(scale * 3.0f - scale)', 'create', (33715, 19)),
 ('fire_rise', 'fire ? 2.5f : 2.2f', 'fire ? 2.0f : 2.2f', 'create', (33559, 4)),
 ('smoke_spin_seed',
  'rand_range(h, -5.0f, 5.0f, 100)',
  'rand_range(h, -5.0f, 6.0f, 100)',
  'create',
  (32894, 24)),
 ('smoke_rise', 'rand_range(h, 1.0f, 2.0f, 100)', 'rand_range(h, 1.0f, 3.0f, 100)', 'create', (32895, 24)),
 ('owner_null',
  'if (p->owner == MU_PT_NO_OWNER) { p->live = 0; return; }',
  'if (p->owner == MU_PT_NO_OWNER) { p->live = 1; return; }',
  'move',
  (34300, 1)),
 ('owner_half',
  'if (p->lifetime < half) p->alpha = p->alpha - 1.0f / (float)half;\n        p->scale = p->initial_scale',
  'if (p->lifetime <= half) p->alpha = p->alpha - 1.0f / (float)half;\n        p->scale = p->initial_scale',
  'move',
  (32763, 0)),
 ('owner_grow',
  'p->initial_scale / (float)p->initial_lifetime + p->scale',
  'p->initial_scale / (float)half + p->scale',
  'move',
  (34300, 2)),
 ('glow_fade',
  'p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;',
  'p->alpha = p->alpha - 0.5f / (float)p->initial_lifetime;',
  'move',
  (32897, 9)),
 ('snow_half',
  'if (p->lifetime < half) p->alpha = p->alpha - 1.0f / (float)half;\n        if (p->type != 0x8109)',
  'if (p->lifetime <= half) p->alpha = p->alpha - 1.0f / (float)half;\n        if (p->type != 0x8109)',
  'move',
  (33720, 8)),
 ('snow_spin', 'p->rotation + p->angle[2]', 'p->rotation + p->angle[1]', 'move', (33720, 8)),
 ('shiny_drift', 'p->type == 0x83b8 ? 0.5f : 0.4f', 'p->type == 0x83b8 ? 0.5f : 0.3f', 'move', (33033, 14)),
 ('fire_jitter', 'mu_pt_rand(h) % 21 - 10', 'mu_pt_rand(h) % 20 - 10', 'move', (33557, 4)),
 ('fire_y',
  'p->position[1] = p->position[1] + jitter;',
  'p->position[1] = p->position[1] - jitter;',
  'move',
  (33558, 4)),
 ('pulse_half', 'if (p->lifetime > half) p->alpha', 'if (p->lifetime >= half) p->alpha', 'move', (34236, 5)),
 ('smoke_spin', 'p->rotation + p->field_84', 'p->rotation - p->field_84', 'move', (32896, 24)),
 ('follow',
  'point) copy3(p->position, point);',
  'point) copy3(p->position, p->start);',
  'render',
  (34300, 1)),
 ('colour', 's->light[k] = p->light[k] * p->alpha;', 's->light[k] = p->light[k];', 'render', (33522, 26))]

def render(m, lib, rng, cases, report, negatives, owned_points=False):
    for n in range(cases):
        kind = pt.KINDS[n % len(pt.KINDS)]
        p = pt.random_particle(rng, kind)
        p.live = 1
        p.owner = -1
        mode = rng.choice([0, 0, 1, 2, 3])
        bm = pt.Bitmap(pt.f32(rng.choice([64.0, 128.0, 256.0, 32.0])), pt.f32(rng.choice([64.0, 128.0, 32.0])),
                    rng.choice([3, 3, 4]))
        if rng.random() < 0.3:
            p.position[2] = pt.f32(rng.choice([300.0, 350.0, 299.99997, 350.00003, 1e9]))
        case = pt.Case(rng)
        owner_regions = []
        point = None
        if owned_points and kind in POINT_KINDS:
            p.owner = rng.choice([-1, 0, 0, 0])
            p.arg8 = n % 3
            points = [pt.rf(rng, -100, 500) for _ in range(9)]
            case.owners = [[0.0, 0.0, 0.0]]
            owner_regions = case.owner_regions()
            owner_regions[0].define(pt.OBJECTS + 0x1f4, pt.struct.pack('<9f', *points))
            point = pt.F3(*points[3*p.arg8:3*p.arg8+3]) if p.owner >= 0 else None
        world_time = pt.f32(rng.uniform(0, 1e6))
        record = pt.particle_region(lib, p)
        bmr = pt.am.Region('bitmap', pt.BITMAP_RECORD, pt.am.poison(0x220, 0x44), bytes(0x220), writable=False)
        bmr.define(pt.BITMAP_RECORD+0x204, pt.struct.pack('<ff', bm.width, bm.height))
        bmr.define(pt.BITMAP_RECORD+0x214, pt.struct.pack('<b', bm.components))
        calls = []

        def bitmap_get(mm):
            calls.append(('bitmap', mm.argument(0)))
            return pt.BITMAP_RECORD, 4

        def wrapper(address, args):
            def stub(mm):
                calls.append(('state', address, mm.argument(0) if args else 0))
                return 0
            return stub

        def sprite(mm):
            a = [mm.argument(i) for i in range(11)]
            calls.append(('sprite', a[0], mm.floats(a[1], 3), pt.from_bits(a[2]), pt.from_bits(a[3]), mm.floats(a[4], 3),
                          pt.from_bits(a[5]), pt.from_bits(a[6]), pt.from_bits(a[7]), pt.from_bits(a[8]), pt.from_bits(a[9]), a[10]))
            return 0
        stubs = pt.shared_stubs(case, m, {0x015ae351: pt.jump_stub(0x015ae363), 0x01591282: pt.jump_stub(0x015ae363),
                                         pt.BITMAP_GET: bitmap_get, pt.RENDER_SPRITE: sprite,
                                         pt.STATE_ADD: wrapper(pt.STATE_ADD, 0), pt.STATE_ALPHA: wrapper(pt.STATE_ALPHA, 1),
                                         pt.STATE_SUB: wrapper(pt.STATE_SUB, 0), pt.STATE_6B7: wrapper(pt.STATE_6B7, 0),
                                         pt.STATE_6DA: wrapper(pt.STATE_6DA, 0), pt.STATE_BLEND: wrapper(pt.STATE_BLEND, 0)})
        r = m.execute(0x015912e9, [0x5500 | mode], [record, bmr] + owner_regions + pt.globals_region(world_time=world_time), stubs, ecx=pt.POOL, frame=pt.mid_frame(pt.RENDER_FRAME, {-0x60: n}),
                      cleanup=4)
        rc = pt.RenderCall()
        if owned_points and kind in POINT_KINDS and not (
                (mode == 1 and p.position[2] > 350.0) or (mode == 2 and 300.0 >= p.position[2])):
            # The split-pass height test precedes RenderParticles' owner-relative position write.
            lib.mu_pt_item_mace_follow(pt.ctypes.byref(p), point)
            # mu_pt_render_record repeats the filter, so draw the already selected record in mode 0.
            mode_for_c = 0
        else:
            mode_for_c = mode
        drawn = lib.mu_pt_render_record(pt.ctypes.byref(p), pt.ctypes.byref(bm), mode_for_c, world_time, n, pt.ctypes.byref(rc))
        mine = []
        if drawn == 1:
            mine.append(('bitmap', p.tex_type))
            for k in range(rc.state_count):
                if rc.state[k] == pt.STATE_SUB:
                    continue
                mine.append(('state', rc.state[k], rc.state_arg[k]))
            for k in range(rc.state_count):
                if rc.state[k] == pt.STATE_SUB:
                    mine.append(('state', rc.state[k], rc.state_arg[k]))
            sp = rc.sprite
            if rc.sprites:   # RENDER-EFFECTS-006: a kind may set its blend state and draw nothing
                mine.append(('sprite', sp.bitmap, list(sp.position), sp.width, sp.height, list(sp.light),
                             sp.rotation, sp.u, sp.v, sp.uw, sp.vh, sp.axes))
        mismatch = None
        if pt.vc.ok(r) and (len(calls) != len(mine) or not all(pt.vc._same_call(a, b) for a, b in zip(calls, mine))):
            mismatch = ('calls', calls, mine)
        if owned_points and pt.vc.ok(r):
            raw, mask = pt.particle_bytes(lib, p)
            mismatch = mismatch or pt.compare_masked(raw, r['regions']['particle'], record.defined, mask, pt.PARTICLE_FLOATS)
        equal = drawn != 2 and pt.vc.ok(r) and mismatch is None
        report.add('render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode, 'mismatch': mismatch,
                                     'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('render', f'{kind[0]:#x}/{kind[1]}' + ('' if drawn == 1 else ' skipped'))


def family(text, data, lib, name, kinds, cases, report):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle
    ordinal = 0

    def boundary(rng, kind):
        nonlocal ordinal
        p = saved[2](rng, kind)
        p.live = 1
        p.lifetime, p.initial_lifetime = [(30, 30), (16, 30), (15, 30), (14, 30), (11, 21), (10, 21),
                                         (1, 1), (1, 0), (1, -1), (1, 50), (25, 50)][ordinal % 11]
        p.owner = 0 if ordinal % 3 else -1
        ordinal += 1
        return p

    pt.OWNED_KINDS, pt.random_particle = set(), boundary
    lib.mu_pt_item_mace_follow.argtypes = [C.POINTER(pt.Particle), C.POINTER(C.c_float)]
    lib.mu_pt_item_mace_follow.restype = None
    r = pt.Report()
    try:
        for kind in kinds:
            # A separate cycle per pair ensures the three-kind groups cannot lock the point index or boundaries.
            ordinal = 0
            pt.KINDS = [kind]
            args = (pt.PtMachine(text, data), lib, random.Random('effects23-' + name), cases, r, defaultdict(int))
            if name == 'render':
                render(*args, owned_points=True)
            else:
                getattr(pt, 'family_' + name)(*args)
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
    rng = random.Random('effects23-points')
    for n in range(cases):
        t = (0x0f24, 0x0f28, 0x0f2a, 0x0f2c)[n % 4]
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
    rows = [
        (0x01823fd4, 0x7f7a, 'Effect\\flare03.jpg', 0x2900),
        (0x01823914, 0x80ba, 'effect\\flare01_red.jpg', 0x2900),
        (0x0182ee66, 0x85bc, 'Effect\\smoke_line03_red.jpg', 0x2900),
        (0x01826804, 0x85fc, 'Effect\\magic_ground12_red.jpg', 0x2900),
        (0x01824ab8, 0x8315, 'Effect\\firehik01.jpg', 0x2900),
        (0x01824ad8, 0x8316, 'Effect\\firehik02.jpg', 0x2900),
        (0x01824af8, 0x8317, 'Effect\\firehik03.jpg', 0x2900),
        (0x01822005, 0x7ffb, 'Effect\\Shockwave.jpg', 0x2900),
        (0x0182ebed, 0x8549, 'Effect\\Glow_26.jpg', 0x2900),
        (0x01824839, 0x82f2, 'Effect\\smoke01_strong.jpg', 0x2900),
        (0x0182e2bf, 0x810b, 'Effect\\pin_star02_red.jpg', 0x2900),
        (0x01821a79, 0x807e, 'Effect\\smokelines01.jpg', 0x2901),
        (0x01821a99, 0x807f, 'Effect\\smokelines02.jpg', 0x2901),
        (0x01821ab9, 0x8080, 'Effect\\smokelines03.jpg', 0x2901),
    ]
    for call, bitmap, path, wrap in rows:
        ins = list(md.disasm(text[call-24-am.TEXT_BASE:call+5-am.TEXT_BASE], call-24))
        pushes = [int(i.op_str, 0) for i in ins if i.mnemonic == 'push']
        off = pushes[-1] - am.DATA_BASE
        actual = data[off:off+100].split(b'\0')[0]
        ok = pushes[:5] == [0, 1, wrap, 0x2601, bitmap] and actual == path.encode() and ins[-1].op_str == '0x185baac'
        report.add('bitmaps', ok, {'bitmap': hex(bitmap), 'call': hex(call), 'path_matches': actual == path.encode()})



def request_census(lib):
    """Static request inventory over both tables, separate from the original-instruction case count.

    Follow the constant/rand/remainder/add bitmap expressions only. Unknown expressions stay unresolved;
    an unsupported future request is reported here, not silently treated as reconstructed behavior.
    """
    header = (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text()
    ops = [tuple(int(x.strip().rstrip('u'), 0) for x in row.split(',')) for row in
           re.findall(r'^    \{([^{}]+)\},', header.split('mu_rc_fx_ops[] = {')[1].split('};')[0], re.M)]
    pairs, unresolved, programs = {}, [], 0
    for name in ('mu_rc_fx_types', 'mu_rc_fx_pre_types'):
        for row in re.findall(r'^    \{([^{}]+)\},', header.split(name+'[] = {')[1].split('};')[0], re.M):
            t, first, count, *_ = [int(x.strip(), 0) for x in row.split(',')]
            registers = {}
            programs += 1

            def put(a, value):
                if value is None or (a in registers and registers[a] is None):
                    registers[a] = None
                else:
                    registers[a] = registers.get(a, set()) | set(value)

            def binary(a, b, f):
                x, y = registers.get(a), registers.get(b)
                if x is None or y is None or len(x) * len(y) > 500000:
                    return None
                return {f(i, j) & 0xffffffff for i in x for j in y}

            for n, (op, a, b, c, d, e, k) in enumerate(ops[first:first+count]):
                if op == 1:
                    put(a, [k])
                elif op == 2:
                    put(a, registers.get(b))
                elif op == 33:
                    put(a, range(32768))
                elif op in (28, 29, 30, 31, 32, 41):
                    operation = {28: lambda i, j: i % j if j else 0,
                                 41: lambda i, j: i % j if j else 0,
                                 29: lambda i, j: i // j if j else 0,
                                 30: lambda i, j: i + j, 31: lambda i, j: i - j, 32: lambda i, j: i * j}[op]
                    divisor = registers.get(c)
                    numerator = registers.get(b)
                    valid = op not in (28, 29, 41) or (divisor and 0 not in divisor)
                    if op in (28, 29) and valid:
                        valid = numerator is not None and max(numerator) < 0x80000000 and max(divisor) < 0x80000000
                    put(a, binary(b, c, operation) if valid else None)
                if op in (14, 25, 46, 47):
                    bitmaps = {k} if op in (14, 25) else registers.get(k)
                    if bitmaps is None or len(bitmaps) > 16:
                        unresolved.append(dict(type=hex(t), op=n))
                        continue
                    for bitmap in bitmaps:
                        key = f'{bitmap:#x}/{e:#x}'
                        entry = pairs.setdefault(key, dict(programs=set(), supported=bool(lib.mu_pt_kind_supported(bitmap, e))))
                        entry['programs'].add(hex(t))
    for entry in pairs.values():
        entry['programs'] = sorted(entry['programs'])
    return dict(programs=programs, particle_pairs=len(pairs), pairs=pairs, unresolved=unresolved)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    if a.cases < 1:
        p.error('--cases must be positive')
    text, data = pins.TEXT.read(), pins.DATA.read()
    source = (ROOT/'reconstructed/particles/item_mace_kinds.inc').read_text()
    bad = [name for name, old, *_ in MUTANTS if source.count(old) != 1]
    if bad:
        raise SystemExit(f'nonunique mutant anchors: {bad}')
    start = time.monotonic()
    lib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{re11.fx.SUFFIX}')
    r = pt.Report()
    for name in ('create', 'move', 'render'):
        family(text, data, lib, name, KINDS, a.cases, r)
    points(max(20, a.cases), r)
    registrations(text, data, r)
    equal = all(f['cases'] == f['equal'] for f in r.families.values())
    mutants = []
    if a.mutations and equal:
        with tempfile.TemporaryDirectory(prefix='effects23-') as tmp:
            for name, old, new, mode, kind in MUTANTS:
                ml = re11.compile_pt_mutant(tmp, name, 'item_mace_kinds.inc', old, new)
                rr = pt.Report()
                family(text, data, ml, mode, [kind], max(120, a.cases), rr)
                f = rr.families['mace_' + mode]
                mutants.append(dict(name=name, detected=f['cases']-f['equal'], cases=f['cases'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
    result = dict(families=r.families, coverage=r.coverage, instruction_cases=sum(f['cases'] for f in r.families.values()),
                  all_equal=equal, mutants=mutants, all_mutants_caught=all(m['detected'] and not m['stopped'] for m in mutants),
                  seconds=round(time.monotonic()-start, 3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    result['request_census'] = request_census(lib)
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
