#!/usr/bin/env python3
"""RENDER-EFFECTS-009 original-instruction families and compiled production mutants.

The named-bone arrows 0x615 (lightning_arrow) and 0x617 (Imperial_arrow): CreateEffect 0x013c0f19 and MoveEffect
0x0142fd09 (cases 0x0146a1f9 / 0x0146af38) for the subtypes CreateArrow passes, compared with
reconstructed/combat/arrow_fx.inc through libcombat. validate_render_effects7's harness, with a synthetic model
that has bone records (names at +0 of 0x8c-byte records, +0x2c / +0x22): the bone lookups 0x0129f18a and
0x012bd35a, the std::string helpers and the sprite helper 0x0150e746 run as client code; TransformPosition
0x012b6ef1 is the recording service of both sides (validate_skill_fx's synthetic answer). The C answers
env->bone_named from the same records.

The named-bone service itself, compiled from native/core/mu_named_bones.c: the search 0x012bd35a(name, fallback)
and 0x0129f18a(name, own) on synthetic models, and the owner bone getter 0x0129f12c(bone) (OBJECT +0x318 and the
model's bone count), against the client instructions. No client bytes or decoded data are written by this tool.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile

import actor_machine as am
import pins
import validate_skill_fx as fx
import validate_combat as vc
import validate_particles as pt
import validate_render_effects7 as re7
import validate_render_effects as base

ROOT = Path(__file__).resolve().parents[1]
f32 = fx.f32
KINDS = [(t, s) for t in (0x615, 0x617) for s in (0, 2, 0x63)]
NAMED = {0x615: ['Line003'], 0x617: ['red_01', 'red_02', 't1', 't2', 't3', 't4', 't5']}
DECOYS = ['Line0030', 'line003', 'Line00', 'red_0', 'red_011', 'Red_01', 't', 't6', 't1 ', 'Group001', 'z003',
          'Sphere002', 'Object007', '']
BONES = 0x2d000000           # synthetic bone records (0x8c bytes each, the name at +0)
STRING_SCRATCH = 0x2e000000  # heap for std::string (unused by these short names)
OBJ_BONES = 0x2f000000       # an object's own bone buffer (+0x318)
NAMED_FIND, NAMED_INDEX, OWNER_BONE = 0x0129f18a, 0x012bd35a, 0x0129f12c

MUTANTS = [
    # (name, old, new, family, kind) on reconstructed/combat/arrow_fx.inc
    ('line_name', 'arrow_bone_named(env, e, "Line003", -1)', 'arrow_bone_named(env, e, "Line004", -1)',
     'effect_move', (0x615, 0)),
    ('line_translate', 'arrow_bone_transform(env, e, bone, zero, 0, b);', 'arrow_bone_transform(env, e, bone, zero, 1, b);',
     'effect_move', (0x615, 0)),
    ('lightning_tint', 'set3(c, F_0_4 * g, 0.45f * g, 1.0f * g);', 'set3(c, F_0_4 * g, 0.5f * g, 1.0f * g);',
     'effect_move', (0x615, 0)),
    ('lightning_steps', 'const float n = 10.0f;', 'const float n = 8.0f;', 'effect_move', (0x615, 0)),
    ('lightning_jitter', 'p[k] = arrow_rand_range(env, -5.0f, 5.0f) + p[k];', 'p[k] = arrow_rand_range(env, -4.0f, 4.0f) + p[k];',
     'effect_move', (0x615, 0)),
    ('lightning_spark', '0x8081 + smod(env_rand(env), 3), p, e->angle, c, 8, 0.35f',
     '0x8081 + smod(env_rand(env), 2), p, e->angle, c, 8, 0.35f', 'effect_move', (0x615, 0)),
    ('imperial_order', 'arrow_bone_sprite(env, e, "red_01", 0x80ba, 0.15f, c);', 'arrow_bone_sprite(env, e, "red_02", 0x80ba, 0.15f, c);',
     'effect_move', (0x617, 0)),
    ('imperial_scale', 'arrow_bone_sprite(env, e, "t4", 0x7f7a, F_0_4, c);', 'arrow_bone_sprite(env, e, "t4", 0x7f7a, F_0_3, c);',
     'effect_move', (0x617, 0)),
    ('imperial_tint', 'set3(c, 0.6f, F_0_2, 1.0f);', 'set3(c, 0.6f, F_0_3, 1.0f);', 'effect_move', (0x617, 0)),
    ('imperial_axis', 'd[k] = e->impact[k] - e->position[k];', 'd[k] = e->position[k] - e->impact[k];',
     'effect_move', (0x617, 0)),
    ('imperial_sub', 'call_particle(env, e, 0x8450, e->position, d, c, 4, F_0_1, -1);',
     'call_particle(env, e, 0x8450, e->position, d, c, 3, F_0_1, -1);', 'effect_move', (0x617, 0)),
]
SERVICE_MUTANTS = [
    # (name, old, new) on native/core/mu_named_bones.c
    ('svc_fallback', 'return fallback;   /* 0x012bd3b1 */', 'return -1;   /* 0x012bd3b1 */'),
    ('svc_first', 'return i;   /* the first equal name */', 'fallback = i;   /* the first equal name */'),
    ('svc_count', 'if (bone < 0 || bone >= count)', 'if (bone < 0 || bone > count)'),
    ('svc_own', 'return own && own_bones ? 2 : 1;', 'return own_bones ? 2 : 1;'),
]


def names_bytes(names):
    out = b''
    for n in names:
        raw = n.encode()[:31] + b'\0'
        out += raw + bytes((0x13 * (len(out) + 7)) & 0xff for _ in range(0x8c - len(raw)))   # junk after the name
    return out


def random_names(rng, kind):
    wanted = NAMED.get(kind, [])
    pool = DECOYS + wanted
    names = [rng.choice(pool) for _ in range(rng.randrange(0, 14))]
    for w in wanted:
        if rng.random() < 0.8:
            names.insert(rng.randrange(0, len(names) + 1), w)
        if rng.random() < 0.15:
            names.insert(rng.randrange(0, len(names) + 1), w)   # a duplicate (the first one wins)
    return names


class Case(re7.Case):
    """validate_render_effects7's case with the synthetic bone names on the C side."""

    def __init__(self, *a, names=None, records=True, **kw):
        super().__init__(*a, **kw)
        self.names = names or []
        self.records = records

    def stubs(self, m):
        s = super().stubs(m)

        def transform_position(mm):   # the caller's out vector is a stack local (written directly)
            matrix, vin, vout = mm.argument(0), mm.argument(1), mm.argument(2)
            index = (matrix - 0x06fce398) // 0x30
            vec = mm.floats(vin, 3)
            self.client_calls.append(('owner_bone', index, vec, mm.argument(3) & 0xff))
            mm.uc.mem_write(vout, struct.pack('<3f', *fx.owner_bone_answer(index, vec)))
            return 0, 0x10
        s[fx.TRANSFORM_POSITION] = transform_position
        return s

    def env(self, *args, **kwargs):
        env = super().env(*args, **kwargs)

        def bone_named(ctx, ep, name, fallback):
            n = name.decode()
            if self.records:
                for i, x in enumerate(self.names):
                    if x == n:
                        return i
            return fallback

        def bone_transform(ctx, ep, index, vin, translate, vout):
            vec = [vin[0], vin[1], vin[2]]
            self.c_calls.append(('owner_bone', index, vec, translate))
            out = fx.owner_bone_answer(index, vec)
            for k in range(3):
                vout[k] = out[k]
        self._bones9 = (fx.BONE_NAMED_FN(bone_named), fx.BONE_TRANSFORM_FN(bone_transform))
        env.bone_named, env.bone_transform = self._bones9
        return env


def family_move(m, lib, rng, cases, report, kinds):
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = re7.random_arrow(rng, kind)
        objects = [fx.random_object(rng) for _ in range(2)]
        e.owner = rng.choice([-1, 0, 1])
        hero_obj = rng.choice([-1, 0, 1, e.owner])
        keys = rng.choice([1, 7, 10, 30])
        has_model = rng.random() < 0.9
        names = random_names(rng, kind[0])
        records = rng.random() < 0.92
        case = Case(rng, objects, fx.rand_values(rng, 120), vc.rfloat(rng, 0.1, 600.0), rng.choice([0, 1, 1]), keys,
                    has_model, names=names, records=records)
        raw, mask = fx.effect_to_bytes(e, re7.MOVE_DEFINED)
        record = am.Region('record', fx.POOL, raw, mask)
        model = am.Region('model', fx.MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(fx.MODEL + 0x30, struct.pack('<I', fx.MODEL + 0x1000))
        model.define(fx.MODEL + 0x22, struct.pack('<h', len(names)))
        model.define(fx.MODEL + 0x2c, struct.pack('<I', BONES if records else 0))
        for a in range(0x100):
            model.define(fx.MODEL + 0x1000 + 16 * a + 8, struct.pack('<h', keys))
        table = names_bytes(names) or b'\0'
        bones = am.defined_region('bones', BONES, table, writable=False)
        clock = f32(rng.choice([0.0, 1000.0, rng.uniform(0.0, 1.0e5)]))
        hero_char = (fx.object_address(hero_obj) - 0x3254) & 0xffffffff if hero_obj >= 0 else 0x5000000
        regions = [record, fx.object_region(objects), model, bones,
                   am.Region('quake', fx.QUAKE, am.poison(4, 0x21), bytes(4)),
                   am.defined_region('world', fx.WORLD, struct.pack('<i', 0), writable=False),
                   am.defined_region('clock', 0x06fce370, struct.pack('<f', clock), writable=False),
                   am.defined_region('hero', fx.HERO_POINTER, struct.pack('<I', hero_char), writable=False)]
        r = m.execute(fx.MOVE_EFFECT, [fx.POOL, 0], regions, case.stubs(m))
        env = case.env(hero_object=hero_obj)
        env.world_time = clock
        supported = lib.mu_sfx_effect_move(C.byref(e), C.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = fx.compare_effect(e, out, record.defined, re7.MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = re7.compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        found = sum(1 for w in NAMED[kind[0]] if records and w in names)
        report.add('effect_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'names': names[:8],
                                          'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error']})
        made = sorted({c[0] for c in case.client_calls if c[0] in ('particle', 'sprite', 'owner_bone')})
        report.cover('effect_move', f'{kind[0]:#x}/{kind[1]}/' + ('model' if has_model else 'no model') +
                     f'/{found} names/' + ('+'.join(made) or 'none'))


def service_library(directory, source=None):
    src = Path(source or ROOT/'native/core/mu_named_bones.c')
    tag = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
    out = Path(directory)/('nb_' + tag + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(ROOT/'native/core'), str(src), '-o', str(out)], check=True, capture_output=True)
    lib = C.CDLL(str(out))
    lib.mu_named_bone_index.argtypes = [C.POINTER(C.c_char_p), C.c_int32, C.c_int, C.c_char_p, C.c_int32]
    lib.mu_named_bone_index.restype = C.c_int32
    lib.mu_named_bone_matrix.argtypes = [C.POINTER(C.c_char_p), C.c_int32, C.c_int, C.c_int, C.c_int, C.c_char_p,
                                         C.c_int, C.POINTER(C.c_int32)]
    lib.mu_named_bone_matrix.restype = C.c_int
    lib.mu_owner_bone_valid.argtypes = [C.c_int, C.c_int, C.c_int32, C.c_int32]
    lib.mu_owner_bone_valid.restype = C.c_int
    return lib


def family_service(m, slib, rng, cases, report):
    """0x012bd35a(name, fallback), 0x0129f18a(name, own) and 0x0129f12c(bone) against mu_named_bones.c."""
    for n in range(cases):
        wanted = rng.choice(NAMED[0x617] + NAMED[0x615] + DECOYS[:4])
        names = [rng.choice(DECOYS + [wanted]) for _ in range(rng.randrange(0, 12))]
        if rng.random() < 0.6:
            names.insert(rng.randrange(0, len(names) + 1), wanted)
        records = rng.random() < 0.9
        has_model = rng.random() < 0.9
        own = rng.random() < 0.5
        own_bones = rng.random() < 0.6
        fallback = rng.choice([-1, 0, 7, 0x7fffffff])
        bone = rng.choice([-5, -1, 0, 1, len(names) - 1, len(names), len(names) + 3, 40])
        count = len(names) if rng.random() < 0.9 else rng.choice([0, -1, len(names) + 2])
        model = am.Region('model', fx.MODEL, am.poison(0x100, 0x55), bytes(0x100))
        model.define(fx.MODEL + 0x22, struct.pack('<h', count))
        model.define(fx.MODEL + 0x2c, struct.pack('<I', BONES if records else 0))
        bones = am.defined_region('bones', BONES, names_bytes(names) or b'\0', writable=False)
        obj = am.Region('object', re7.OBJ, am.poison(0x400, 0x29), bytes(0x400))
        obj.define(re7.OBJ + 0x5c, struct.pack('<i', 0x617))
        obj.define(re7.OBJ + 0x318, struct.pack('<I', OBJ_BONES if own_bones else 0))
        sname = am.Region('string', fx.INPUTS, am.poison(0x40, 0x33), bytes(0x40))
        enc = wanted.encode()
        sname.define(fx.INPUTS + 0x20, enc + bytes(0x20 - len(enc)))
        case = re7.Case(rng, [], [], 0.0, has_model=has_model)
        stubs = case.stubs(m)
        c_names = (C.c_char_p * max(1, len(names)))(*[x.encode() for x in names])
        mine_index = slib.mu_named_bone_index(c_names, count, records, enc, fallback) if has_model else None
        # std::string(name) at INPUTS through the client's constructor, then the lookups
        regions = [model, bones, obj, sname]
        r0 = m.execute(0x0094997e, [fx.INPUTS + 0x20], regions, stubs, ecx=fx.INPUTS, cleanup=4)
        mismatch = None
        ok = vc.ok(r0)
        if ok and has_model:
            string = am.defined_region('string', fx.INPUTS, r0['regions']['string'], writable=True)
            regions = [model, bones, obj, string]
            r = m.execute(NAMED_INDEX, [fx.INPUTS, fallback & 0xffffffff], regions, stubs, ecx=fx.MODEL, cleanup=8)
            ok = ok and vc.ok(r)
            theirs = r['eax'] - (1 << 32) if ok and r['eax'] & 0x80000000 else (r['eax'] if ok else None)
            if ok and theirs != mine_index:
                mismatch = ('index', theirs, mine_index)
            r = m.execute(NAMED_FIND, [fx.INPUTS, int(own)], regions, stubs, ecx=re7.OBJ, cleanup=8)
            ok = ok and vc.ok(r)
            idx = C.c_int32(-9)
            where = slib.mu_named_bone_matrix(c_names, count, records, has_model, own, enc, own_bones, C.byref(idx))
            if ok and mismatch is None:
                base = {0: 0, 1: 0x06fce398, 2: OBJ_BONES}[where]
                mine = base + 0x30 * idx.value if where else 0
                if r['eax'] != (mine & 0xffffffff):
                    mismatch = ('matrix', hex(r['eax']), hex(mine & 0xffffffff))
        if ok and mismatch is None:
            r = m.execute(OWNER_BONE, [bone & 0xffffffff], [model, bones, obj], stubs, ecx=re7.OBJ, cleanup=4)
            ok = vc.ok(r)
            valid = slib.mu_owner_bone_valid(has_model, own_bones, count, bone)
            mine = (OBJ_BONES + 0x30 * bone) & 0xffffffff if valid else 0
            if ok and r['eax'] != mine:
                mismatch = ('owner bone', hex(r['eax']), hex(mine))
        report.add('named_bones', ok and mismatch is None,
                   {'case': n, 'names': names, 'wanted': wanted, 'mismatch': mismatch, 'stopped': r0['stopped'],
                    'error': r0['error']})
        report.cover('named_bones', ('found' if mine_index is not None and mine_index >= 0 else 'fallback') +
                     ('/own' if own else '/global') + ('/records' if records else '/no records'))


PARTICLE_KINDS = [(0x7f5a, 0xd)]   # Carow 0x474's trail (bow 0x12f9)
PT_MUTANTS = [
    ('trail_life', 'p->lifetime = 20;\n            p->scale = (float)(mu_pt_rand(h) % 64 + 64) * 0.01f;',
     'p->lifetime = 24;\n            p->scale = (float)(mu_pt_rand(h) % 64 + 64) * 0.01f;', 'create'),
    ('trail_rise', 'p->gravity = (float)(mu_pt_rand(h) % 32 + 60) * 0.1f;\n        } else if (subtype == 21) {',
     'p->gravity = (float)(mu_pt_rand(h) % 32 + 50) * 0.1f;\n        } else if (subtype == 21) {', 'create'),
    ('trail_fade', 'const float l = (float)p->lifetime / 20.0f;', 'const float l = (float)p->lifetime / 25.0f;', 'move'),
    ('trail_grow', 'p->scale += 0.09f;\n            } else if (p->subtype == 21)', 'p->scale += 0.08f;\n            } else if (p->subtype == 21)',
     'move'),
]
JOINT_KINDS = [(0x7fd5, 3), (0x7fd6, 5)]   # bow 0x12f9's spark joint, the arrows' trail
JOINT_MUTANTS = [
    # (name, old, new, family) on reconstructed/joints/joints.c
    ('spark_speed', 'j->velocity = j->velocity + F_0_1;', 'j->velocity = j->velocity + F_0_2;', 'joint_move'),
    ('spark_fade', 'j->light[0] = j->light[0] / f32bits(0x3f8ccccdu);   /* 1.1 */',
     'j->light[0] = j->light[0] / 1.2f;   /* 1.1 */', 'joint_move'),
    ('spark_kind', 'return subtype == 0 || subtype == 3;   /* 3: RENDER-EFFECTS-009, bow 0x12f9\'s sparks */',
     'return subtype == 0;   /* 3: RENDER-EFFECTS-009, bow 0x12f9\'s sparks */', 'joint_create'),
    ('trail_lifetime', 'j->lifetime = 999999999;', 'j->lifetime = 99999999;', 'joint_create'),
    ('trail_tails', 'j->max_tails = 10;\n            j->scale = scale;\n            const mu_jt_object *t',
     'j->max_tails = 12;\n            j->scale = scale;\n            const mu_jt_object *t', 'joint_create'),
    ('trail_follow', 'copy3(j->position, t->eye_188);\n            break;\n        }\n        copy3(j->position, j->subtype == 0x43',
     'copy3(j->position, t->eye_194);\n            break;\n        }\n        copy3(j->position, j->subtype == 0x43', 'joint_move'),
]


def joint_families(text, data, cases, mutations):
    """validate_joints' create, move and render families (CreateJoint 0x0153b02c, MoveJoint 0x01556c26,
    RenderJoints 0x01589b56) on the kinds this lane adds; its families read the module's KINDS."""
    import validate_joints as vj
    out, mutants = {}, {}
    saved, saved_region = vj.KINDS, vj.object_region
    vj.KINDS = JOINT_KINDS

    def object_region(objects):   # MoveJoint's 0x7fd6/5 looks up the target's model: its type +0x5c
        region = saved_region(objects)
        for i in range(len(objects)):
            region.define(vj.OBJECTS + 0x400 * i + 0x5c, struct.pack('<i', 0x474))
        return region
    vj.object_region = object_region
    try:
        m = machine(text, data)
        lib = vj.load_library(ROOT/f'reconstructed/joints/libclient_joints.{fx.SUFFIX}')
        for name, family in vj.FAMILIES:
            report = pt.Report()
            family(m, lib, random.Random('render-effects-009-' + name), cases, report, vj.collections_default())
            out[name] = {'families': report.families, 'coverage': report.coverage}
        if mutations:
            families = dict(vj.FAMILIES)
            with tempfile.TemporaryDirectory(prefix='render-effects9-joints-') as tmp:
                for name, old, new, family in JOINT_MUTANTS:
                    dest = Path(tmp)/name
                    for directory in ('joints', 'record-math', 'movement'):
                        shutil.copytree(ROOT/'reconstructed'/directory, dest/directory,
                                        ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
                    if (ROOT/'reconstructed/deps.mk').exists():
                        shutil.copy(ROOT/'reconstructed/deps.mk', dest/'deps.mk')
                    path = dest/'joints'/'joints.c'
                    text_c = path.read_text()
                    assert text_c.count(old) == 1, name
                    path.write_text(text_c.replace(old, new))
                    subprocess.run(['make', '-s', '-C', str(dest/'joints')], check=True, capture_output=True)
                    mlib = vj.load_library(dest/f'joints/libclient_joints.{fx.SUFFIX}')
                    report = pt.Report()
                    families[family](m, mlib, random.Random('render-effects-009-' + family), max(40, cases), report,
                                     vj.collections_default())
                    f = report.families[family]
                    mutants[name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    finally:
        vj.KINDS, vj.object_region = saved, saved_region
    return out, mutants


def compile_mutant(directory, name, old, new):
    base = ROOT/'reconstructed'/'combat'
    if (base/'arrow_fx.inc').read_text().count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    work = directory/name
    work.mkdir()
    shutil.copy(base/'skill_fx.c', work/'skill_fx.c')
    shutil.copy(base/'pet_fx.inc', work/'pet_fx.inc')
    (work/'arrow_fx.inc').write_text((base/'arrow_fx.inc').read_text().replace(old, new))
    others = ['combat.c', '../objects/world_warp.c', '../joints/joints.c', '../record-math/record_math.c',
              '../movement/client_movement.c']
    out = directory/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(base), str(work/'skill_fx.c'), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return fx.load_library(out)


def machine(text, data):
    am.STACK_BYTES, am.ENTRY_ESP = 0x80000, am.STACK + 0x7c000
    return fx.FxMachine(text, data)


def compare(text, data, lib, name, kinds, cases):
    m = machine(text, data)
    report = pt.Report()
    rng = random.Random('render-effects-009-' + name)
    if name == 'effect_create':
        saved = re7.Case
        re7.Case = Case
        try:
            re7.family_create(m, lib, rng, cases, report, kinds)
        finally:
            re7.Case = saved
    else:
        family_move(m, lib, rng, cases, report, kinds)
    return {'families': report.families, 'coverage': report.coverage}


BODIES = {'move_615': (0x0146a1f9, 0x0146aa05), 'move_617': (0x0146af38, 0x0146b64c),
          'bone_find': (0x0129f18a, 0x0129f24f), 'bone_index': (0x012bd35a, 0x012bd3b8),
          'owner_bone': (0x0129f12c, 0x0129f18a), 'bone_sprite': (0x0150e746, 0x0150e7c9),
          'create_7fd5_3': (0x01543446, 0x015434ea), 'move_7fd5_3': (0x0156985b, 0x015698ed),
          'create_7f5a_d': (0x015c5882, 0x015c594a), 'move_7f5a_d': (0x0163533b, 0x01635435)}


def run(cases, mutations):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'comparisons': {}, 'mutants': {}}
    lib = fx.load_library(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX))
    for name in ('effect_create', 'effect_move'):
        result['comparisons'][name] = compare(text, data, lib, name, KINDS, cases * len(KINDS))
    plib = pt.load_library(ROOT/'reconstructed'/('particles/libclient_particles.' + fx.SUFFIX))
    for name in ('create', 'move', 'render'):   # CreateParticle 0x0168fafd, MoveParticles, RenderParticles
        r = base.compare(text, data, plib, 'pt', name, PARTICLE_KINDS, cases * 20)
        result['comparisons']['pt_' + name] = {'families': {'pt_' + name: r['families'][name]},
                                               'coverage': r['coverage']}
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects9-pt-') as tmp:
            for name, old, new, family in PT_MUTANTS:
                mlib = base.compile_mutant(Path(tmp), name, 'pt', old, new)
                f = base.compare(text, data, mlib, 'pt', family, PARTICLE_KINDS, max(40, cases * 20))['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    joints, joint_mutants = joint_families(text, data, cases * 20, mutations)
    result['comparisons'].update(joints)
    result['mutants'].update(joint_mutants)
    with tempfile.TemporaryDirectory(prefix='render-effects9-svc-') as tmp:
        report = pt.Report()
        family_service(machine(text, data), service_library(tmp), random.Random('render-effects-009-svc'),
                       cases * 20, report)
        result['comparisons']['named_bones'] = {'families': report.families, 'coverage': report.coverage}
        if mutations:
            src = (ROOT/'native/core/mu_named_bones.c').read_text()
            for name, old, new in SERVICE_MUTANTS:
                assert src.count(old) == 1, name
                path = Path(tmp)/(name + '.c')
                path.write_text(src.replace(old, new))
                report = pt.Report()
                family_service(machine(text, data), service_library(tmp, path),
                               random.Random('render-effects-009-svc'), max(60, cases * 4), report)
                f = report.families['named_bones']
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    if mutations:
        with tempfile.TemporaryDirectory(prefix='render-effects9-mutants-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                mlib = compile_mutant(Path(tmp), name, old, new)
                f = compare(text, data, mlib, family, [kind], max(40, cases))['families'][family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                               'sha256': hashlib.sha256(text[a - am.TEXT_BASE:b - am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in BODIES.items()}
    result['families'] = {name: r['families'][name] for name, r in result['comparisons'].items()}
    result['instruction_cases'] = sum(f['cases'] for f in result['families'].values())
    result['all_equal'] = all(f['cases'] == f['equal'] for f in result['families'].values())
    result['all_mutants_caught'] = all(v['caught'] > 0 for v in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=20, help='cases per (type, subtype) and family')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2))
    summary = {k: {f: (v['cases'], v['equal']) for f, v in r['families'].items()}
               for k, r in result['comparisons'].items()}
    print(json.dumps({'summary': summary, 'mutants': result['mutants'], 'all_equal': result['all_equal'],
                      'all_mutants_caught': result['all_mutants_caught']}, indent=1))
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
