#!/usr/bin/env python3
"""Death Stab caller, trail records and ordered GL streams against pinned instructions.

RENDER-EFFECTS-027. Only synthetic CHARACTER/OBJECT/model state is supplied.
Model, bone, target lookup and world predicate are declared services. The original
step branch, rand scatter, trigonometry, joint creation/movement/tail shift and
render stream execute under the strict existing Unicorn machines.
"""
import argparse
from collections import defaultdict
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import time

import actor_machine as am
import pins
import validate_combat as vc
import validate_skill_fx as fx
import validate_joints as jt
import validate_render_effects7 as r7
import validate_particles as pt

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x472, 2), (0x7f78, 12)]
F3 = C.c_float * 3
CHAR = 0x28000000


class Stab(C.Structure):
    _fields_ = [('attack_time', C.c_uint8), ('has_model', C.c_uint8), ('has_bone', C.c_uint8),
                ('quiet_world', C.c_uint8), ('position', F3), ('angle', F3), ('weapon_point', F3),
                ('sword_position', F3), ('owner', C.c_int32)]


def configure():
    jt.KINDS = KINDS
    original_record, original_objects = jt.random_joint, jt.object_region

    def record(rng, kind):
        j = original_record(rng, (0x7fd3, 0))
        j.type, j.tex_type, j.subtype = kind[0], 0x7fde if kind[0] == 0x472 else kind[0], kind[1]
        j.lifetime = rng.choice([70, 60, 24, 21, 20, 19, 15, 12, 11, 10, 9, 8, 1, 0, -1])
        j.max_tails = 5 if kind[0] == 0x472 else 50
        j.num_tails = rng.randrange(j.max_tails)
        j.scale = rng.choice([0.0, 10.0, 40.0, 60.0, 100.0])
        j.velocity = 0.0
        j.jitter[0] = float(rng.randrange(360))
        return j

    def objects(objs):
        r = original_objects(objs)
        for i, o in enumerate(objs):
            r.define(fx.OBJECTS + i * 0x400 + 0x104, struct.pack('<3f', *o.sword_position))
        return r

    jt.random_joint, jt.object_region = record, objects


def load(path):
    lib = fx.load_library(path)
    lib.mu_sfx_death_stab_step.argtypes = [C.POINTER(Stab), C.POINTER(fx.Env)]
    lib.mu_sfx_death_stab_step.restype = C.c_int
    return lib


def caller(m, lib, rng, cases, report):
    for n in range(cases):
        s = Stab()
        s.attack_time = n % 18
        s.has_model = int(n % 13 != 0)
        s.has_bone = int(n % 11 != 0)
        s.quiet_world = int(n % 5 == 0)
        s.owner = 0
        for k in range(3):
            s.position[k] = vc.rfloat(rng, 0.05, 30000.0)
            s.angle[k] = vc.rfloat(rng, 0.1, 360.0)
            s.weapon_point[k] = vc.rfloat(rng, 0.05, 30000.0)
            s.sword_position[k] = vc.rfloat(rng, 0.05, 30000.0)
        char = am.undefined_region('character', CHAR, 0x3670)
        for offset, value in [(0x21, bytes([s.attack_time])), (0x26, struct.pack('<H', 43)),
                              (0x19b1, bytes([0])), (0x40, struct.pack('<h', -1))]:
            char.define(CHAR + offset, value)
        obj = am.undefined_region('object', fx.OBJECTS, 0x400)
        for offset, raw in [(0x5c, struct.pack('<i', 0xa91)), (0x158, struct.pack('<3f', *s.position)),
                            (0x164, struct.pack('<3f', *s.angle)), (0x104, struct.pack('<3f', *s.sword_position))]:
            obj.define(fx.OBJECTS + offset, raw)
        model = am.undefined_region('model', fx.MODEL, 0x2000)
        model.define(fx.MODEL + 0x22, struct.pack('<h', 1))
        model.define(fx.MODEL + 0x2c, struct.pack('<I', fx.MODEL + 0x1000))
        model.define(fx.MODEL + 0x1022, bytes([0]))
        cutoff = am.defined_region('cutoff', 0x1cf1050, struct.pack('<i', -1))
        case = fx.Case(rng, [], fx.rand_values(rng, 100), 0.0)
        stubs = case.stubs(m)
        stubs.update({0x13a5658: lambda mm: 0, 0xac3bf7: lambda mm: (fx.CONTAINER, 4),
                      0x95f998: lambda mm: fx.CONTAINER, 0xbb1c32: lambda mm: 43,
                      fx.MODEL_CONTAINER: lambda mm: (fx.CONTAINER, 4),
                      fx.MODEL_GETTER: lambda mm: fx.MODEL if s.has_model else 0,
                      0x9b0bc1: lambda mm: 3 if s.quiet_world else 0,
                      0x129f12c: lambda mm: (fx.MODEL + 0x1800 if s.has_bone else 0, 4),
                      0x95f6db: lambda mm: (0, 4), 0x9a13f4: lambda mm: 0})

        def transform(mm):
            assert mm.floats(mm.argument(1), 3) == [0.0, 0.0, 0.0]
            assert mm.argument(3) == 1
            mm.uc.mem_write(mm.argument(2), struct.pack('<3f', *s.weapon_point))
            return 0, 16
        stubs[0x12b6ef1] = transform
        result = m.execute(0x13966ea, [CHAR, fx.OBJECTS], [char, obj, model, cutoff], stubs)
        env = case.env()
        supported = lib.mu_sfx_death_stab_step(C.byref(s), C.byref(env))
        mismatch = None
        if vc.ok(result):
            actual = result['regions']['character'][0x21]
            point = struct.unpack_from('<3f', result['regions']['object'], 0x104)
            if actual != s.attack_time or any(not fx.same(x, y) for x, y in zip(point, s.sword_position)):
                mismatch = ('state', actual, s.attack_time, point, list(s.sword_position))
            if mismatch is None:
                mismatch = fx.compare_calls(case.client_calls, fx.sorted_calls(case.c_calls, case.client_calls))
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        report.add('caller', vc.ok(result) and mismatch is None,
                   dict(case=n, step=n % 18, supported=supported, mismatch=mismatch,
                        stopped=result['stopped'], error=result['error']))
        report.cover('caller', f'step {n % 18}, model {s.has_model}, bone {s.has_bone}, quiet {s.quiet_world}')


def compare(text, data, lib, family, cases):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    m, report = fx.FxMachine(text, data), pt.Report()
    rng = random.Random('effects27-' + family)
    if family == 'caller':
        caller(m, lib, rng, cases, report)
    elif family.startswith('joint_'):
        dict(jt.FAMILIES)[family](m, lib, rng, cases, report, defaultdict(int))
    elif family == 'effect_create':
        r7.family_create(m, lib, rng, cases, report, [(0x10e6, 1)])
    else:
        r7.family_move(m, lib, rng, cases, report, [(0x10e6, 1)])
    return report


def run(cases, mutations=False):
    configure()
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    libraries = {'fx': load(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}'),
                 'jt': jt.load_library(ROOT/f'reconstructed/joints/libclient_joints.{jt.SUFFIX}')}
    result = dict(text_sha256=pins.TEXT.sha256, data_sha256=pins.DATA.sha256, families={}, coverage={}, mutants=[])
    start = time.monotonic()
    for family in ['caller', 'joint_create', 'joint_move', 'joint_render', 'effect_create', 'effect_move']:
        report = compare(text, data, libraries['jt' if family.startswith('joint_') else 'fx'], family, cases)
        result['families'].update(report.families)
        result['coverage'].update(report.coverage)
    result['bodies'] = {name: dict(start=hex(a), end=hex(b), sha256=hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest())
                        for name, a, b in [('caller', 0x139959c, 0x1399c9d), ('scatter', 0xd750fa, 0xd751db),
                                           ('create472', 0x1548aeb, 0x1548bac), ('move472', 0x1569e07, 0x156a160),
                                           ('direction', 0x158bac2, 0x158bdf0), ('create_flare12', 0x154a9a2, 0x154ab1a),
                                           ('move_flare12', 0x1579558, 0x1579941), ('move_tail', 0x15896fb, 0x15897e5),
                                           ('create_emitter', 0x13c465a, 0x13c4669), ('move_emitter', 0x14374f6, 0x1437553)]}
    result['seconds'] = time.monotonic() - start
    result['cases'] = sum(f['cases'] for f in result['families'].values())
    result['all_equal'] = all(f['equal'] == f['cases'] for f in result['families'].values())
    result['all_mutants_caught'] = True
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=1000)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
