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
import shutil
import subprocess
import tempfile

import actor_machine as am
import pins
import validate_combat as vc
import validate_skill_fx as fx
import validate_joints as jt
import validate_render_effects7 as r7
import validate_particles as pt
import validate_render_effects as base

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x472, 2), (0x7f78, 12)]
F3 = C.c_float * 3
CHAR = 0x28000000

# Each edit changes compiled production C, with the same original comparator.
# A mutant must disagree without stopping the original instruction machine.
MUTANTS = [
    ('skill_fx.c', 's->attack_time >= 2 && s->attack_time <= 8', 's->attack_time >= 3 && s->attack_time <= 8', 'caller'),
    ('skill_fx.c', 'n < 3; ++n', 'n < 2; ++n', 'caller'),
    ('skill_fx.c', 'smod(env_rand(env), 601) - 300', 'smod(env_rand(env), 600) - 300', 'caller'),
    ('skill_fx.c', '-1400.0f * sn + p[0]', '-1300.0f * sn + p[0]', 'caller'),
    ('skill_fx.c', 'sn * 300.0f + s->sword_position[0]', 'sn * 290.0f + s->sword_position[0]', 'caller'),
    ('skill_fx.c', 's->attack_time >= 6 && s->attack_time <= 12', 's->attack_time >= 7 && s->attack_time <= 12', 'caller'),
    ('skill_fx.c', 'if (s->attack_time >= 12)', 'if (s->attack_time > 12)', 'caller'),
    ('skill_fx.c', 'e->lifetime = 10;\n        break;\n    case MU_SFX_MODEL_ARROW: {',
     'e->lifetime = 9;\n        break;\n    case MU_SFX_MODEL_ARROW: {', 'effect_create'),
    ('skill_fx.c', 'c.routine = MU_SFX_CALL_JOINT; c.type = 0x7f78; c.subtype = 12;',
     'c.routine = MU_SFX_CALL_JOINT; c.type = 0x7f78; c.subtype = 11;', 'effect_move'),
    ('joints.c', 'j->lifetime = 20; j->max_tails = 0x5;', 'j->lifetime = 19; j->max_tails = 0x5;', 'joint_create'),
    ('joints.c', 'j->max_tails = 0x5;', 'j->max_tails = 0x6;', 'joint_create'),
    ('joints.c', 'j->scale = scale; j->lifetime = 70;', 'j->scale = scale; j->lifetime = 60;', 'joint_create'),
    ('joints.c', 'j->jitter[1] = fsin(radians) * -4.0f;', 'j->jitter[1] = fsin(radians) * -3.0f;', 'joint_create'),
    ('death_stab_joints.inc', 'j->scale = (float)j->lifetime * 3.0f;', 'j->scale = (float)j->lifetime * 2.0f;', 'joint_move'),
    ('death_stab_joints.inc', '(float)(j->lifetime - 10) / 10.0f', '(float)(j->lifetime - 10) / 9.0f', 'joint_move'),
    ('death_stab_joints.inc', 'f32bits(0x3fb33333u)', 'f32bits(0x3fc00000u)', 'joint_move'),
    ('death_stab_joints.inc', 'j->jitter[0]) * F_0_1;', 'j->jitter[0]) * F_0_2;', 'joint_move'),
    ('death_stab_joints.inc', 'j->light[k] / f32bits(0x3fa66666u)', 'j->light[k] / 1.2f', 'joint_move'),
    ('joints.c', 'j->subtype == 12 && j->lifetime % 12 != 0', 'j->subtype == 12 && j->lifetime % 10 != 0', 'joint_move'),
    ('joints.c', 'j->lifetime < 20 ? j->lifetime : 20', 'j->lifetime < 19 ? j->lifetime : 19', 'joint_render'),
]


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


def lifecycle(m, lib, rng, report):
    """Carry original record bytes through create, every tick and owner death.

    This does not reseed the original record from C between moves. Retired
    records are checked at their last tick, including their closing tail.
    """
    for kind in KINDS:
        for owner_dies in (False, True):
            objects = [jt.random_object(rng)]
            objects[0].live = 1
            objects[0].sword_position[:] = [12000.0, 12050.0, 150.0]
            pos, target, angle = [11000.0, 11500.0, 300.0], [11000.0, 11500.0, 300.0], [15.0, 0.0, 90.0]
            inputs = am.defined_region('inputs', fx.INPUTS, struct.pack('<9f', *pos, *target, *angle))
            record = am.defined_region('joint', jt.JOINT_POOL, bytes(jt.JOINT_BYTES))
            case = jt.Case(rng, objects, jt.rand_values(rng), 0.0, 1000.0)
            stubs = case.stubs(m)
            del stubs[fx.CREATE_JOINT]
            stubs[fx.JOINT_MANAGER_A] = lambda mm: (0, 12)
            result = m.execute(jt.CREATE_JOINT_CORE,
                [kind[0], fx.INPUTS, fx.INPUTS+12, fx.INPUTS+24, kind[1], fx.OBJECTS, fx.bits(40.0),
                 0xffff, 0, 0, 0xffffffff, 0, 0xffff, 0], [record, inputs, jt.object_region(objects)], stubs)
            j, env = jt.Joint(), case.jenv()
            lib.mu_jt_create(C.byref(j), kind[0], F3(*pos), F3(*target), F3(*angle), kind[1], 0, 40.0,
                             0xffff, 0, 0, 0xffff, 0, C.byref(env))
            mismatch = jt.compare_joint(j, result['regions']['joint'], record.defined, jt.ALL_NAMES) if vc.ok(result) else None
            report.add('lifecycle', vc.ok(result) and mismatch is None,
                       dict(kind=kind, step='create', mismatch=mismatch, stopped=result['stopped']))
            if not vc.ok(result):
                continue
            raw = result['regions']['joint']
            for tick in range(40):
                if not raw[0]:
                    break
                if owner_dies and tick >= 7:
                    objects[0].live = 0
                for k in range(3):
                    objects[0].sword_position[k] = fx.f32(objects[0].sword_position[k] + 2.0)
                case = jt.Case(rng, objects, jt.rand_values(rng), 0.0, 1000.0)
                record = am.Region('joint', jt.JOINT_POOL, raw, record.defined)
                clock = 1000 + tick
                regions = [record, jt.object_region(objects),
                    am.defined_region('step', fx.TIME_STEP, struct.pack('<f', 0.1)),
                    am.defined_region('clock', 0xbdc5eb0, struct.pack('<i', clock))]
                stubs = case.stubs(m)
                stubs.update({0x95f6db: lambda mm: (0, 4), 0x9a13f4: lambda mm: 0})
                result = m.execute(jt.MOVE_JOINT, [jt.JOINT_POOL, 3], regions, stubs)
                env = case.jenv(); env.ambient_clock = clock
                move = jt.MoveInputs(0.1, 0, 0, 3, 0)
                lib.mu_jt_move(C.byref(j), C.byref(env), C.byref(move))
                mismatch = None
                if vc.ok(result):
                    mismatch = jt.compare_joint(j, result['regions']['joint'], record.defined, jt.ALL_NAMES)
                    if mismatch is None and struct.unpack_from('<I', result['regions']['joint'], 0x54)[0] != jt.object_address(j.target):
                        mismatch = ('owner pointer', j.target)
                    if mismatch is None and case.client_rand != case.c_rand:
                        mismatch = ('rand calls', case.client_rand, case.c_rand)
                report.add('lifecycle', vc.ok(result) and mismatch is None,
                           dict(kind=kind, step=tick, owner_dies=owner_dies, mismatch=mismatch,
                                stopped=result['stopped'], error=result['error']))
                if not vc.ok(result):
                    break
                raw = result['regions']['joint']
            report.cover('lifecycle', f'{kind}, owner dies {owner_dies}, retired {not bool(raw[0])}')
            report.add('lifecycle', not raw[0] and not j.live, dict(kind=kind, retired=True))


def compare(text, data, lib, family, cases):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    m, report = fx.FxMachine(text, data), pt.Report()
    rng = random.Random('effects27-' + family)
    if family == 'caller':
        caller(m, lib, rng, cases, report)
    elif family == 'lifecycle':
        lifecycle(m, lib, rng, report)
    elif family.startswith('joint_'):
        dict(jt.FAMILIES)[family](m, lib, rng, cases, report, defaultdict(int))
    elif family == 'effect_create':
        r7.family_create(m, lib, rng, cases, report, [(0x10e6, 1)])
    else:
        r7.family_move(m, lib, rng, cases, report, [(0x10e6, 1)])
    return report


def mutants(text, data):
    result = []
    with tempfile.TemporaryDirectory(prefix='effects27-mutants-') as tmp:
        for i, (file, old, new, family) in enumerate(MUTANTS):
            if file == 'skill_fx.c':
                source = ROOT/'reconstructed/combat'/file
                original = source.read_text()
                assert original.count(old) == 1, (file, old, original.count(old))
                base.compile_mutant(Path(tmp), f'fx{i}', 'fx', old, new)
                lib = load(Path(tmp)/f'fx{i}.{fx.SUFFIX}')
            else:
                dest = Path(tmp)/f'joint{i}'
                for directory in ('joints', 'record-math', 'movement'):
                    shutil.copytree(ROOT/'reconstructed'/directory, dest/directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
                source = dest/'joints'/file
                original = source.read_text()
                expected = 3 if old == 'f32bits(0x3fb33333u)' else 1
                assert original.count(old) == expected, (file, old, original.count(old))
                source.write_text(original.replace(old, new))
                subprocess.run(['make', '-s', '-C', str(dest/'joints')], check=True, capture_output=True)
                lib = jt.load_library(dest/f'joints/libclient_joints.{fx.SUFFIX}')
            report = compare(text, data, lib, family, 200)
            f = report.families[family]
            result.append(dict(file=file, change=new, family=family, cases=f['cases'],
                               detected=f['cases']-f['equal'],
                               stopped=sum(bool(row.get('stopped')) for row in f['first_failures'])))
            if file != 'skill_fx.c':
                shutil.rmtree(dest)
    return result


def run(cases, mutations=False):
    configure()
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    libraries = {'fx': load(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}'),
                 'jt': jt.load_library(ROOT/f'reconstructed/joints/libclient_joints.{jt.SUFFIX}')}
    result = dict(text_sha256=pins.TEXT.sha256, data_sha256=pins.DATA.sha256, families={}, coverage={}, mutants=[])
    start = time.monotonic()
    for family in ['caller', 'joint_create', 'joint_move', 'joint_render', 'effect_create', 'effect_move', 'lifecycle']:
        report = compare(text, data, libraries['jt' if family.startswith('joint_') or family == 'lifecycle' else 'fx'], family, cases)
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
    if mutations and result['all_equal']:
        result['mutants'] = mutants(text, data)
    result['all_mutants_caught'] = (not mutations or len(result['mutants']) == len(MUTANTS)) and all(
        m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants'])
    result['seconds'] = time.monotonic() - start
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
