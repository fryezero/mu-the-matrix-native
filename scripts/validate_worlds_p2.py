#!/usr/bin/env python3
"""World-137 and world-138 primary slots against pinned instructions.

Kanturu Underground create/move/visual (predicate 0x00e0df03) and Ignis Volcano
create/move/visual (predicate 0x00e0895c). Full AL, all OBJECT bytes, the
model's action table and StreamMesh byte, ordered output calls and the final
MSVC RNG are compared. The model lookup, TransformPosition, register,
AddTerrainLight, CreateParticle, CreateSprite, CreateJoint, PlayBuffer and rand
are recording boundaries; the predicates, SetAction 0x012affa4, the client's
vector helpers, its sine wrapper and SEH frames execute as original code.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import actor_machine as am
import validate_object_render as v
import pins
from unicorn.x86_const import UC_X86_REG_ECX
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'kanturu_create': (0xe08cd8, 0xe08f8a), 'kanturu_move': (0xe08f8a, 0xe092f4),
          'kanturu_visual': (0xe0a4bb, 0xe0ab2a), 'ignis_create': (0xe05afe, 0xe05d76),
          'ignis_move': (0xe05d76, 0xe05f25), 'ignis_visual': (0xe07081, 0xe0709e)}
EXTREMES = [-2147483648, -1, 2147483647, 1000, 0x7dc]
TYPES = {'kanturu': list(range(-1, 131)) + EXTREMES, 'ignis': list(range(-1, 181)) + EXTREMES}
DIRECTED = {'kanturu_move': [10, 38, 44, 125, 126, 127, 125, 126, 127],
            'kanturu_visual': [8, 54, 65, 66, 92, 93, 94, 95, 96, 120, 121, 122],
            'ignis_move': [88, 177, 177]}
NULL = 0
COOKIE = 0x01cf65c0   # CRT security cookie (the sine wrapper's error path for huge arguments)
ACTIONS = 8      # harness action records (the client reads the current action without a bound)
ACTION_FN = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int32, C.c_int32, C.POINTER(C.c_int32), C.POINTER(C.c_int16),
                        C.POINTER(C.c_float))
BONE = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))
SPRITE_DESCRIPTOR = (1, 1, v.bits(1.0))
JOINT_TAIL = [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]
PLAY_SPEED, MODEL_STREAM, ALL = 0xeaaa44, 0x17ffef3, 0xffffffff


def bind(lib):
    d = lib.dll
    d.mu_kanturu_ug_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, v.RAND_FN, C.c_void_p, C.POINTER(v.Log)]
    d.mu_kanturu_ug_move.argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.MoveInputs), ACTION_FN, C.c_float,
                                     C.POINTER(v.Log)]
    d.mu_kanturu_ug_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.c_float, v.RAND_FN, BONE, C.c_void_p,
                                       C.POINTER(v.Log)]
    d.mu_ignis_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int32, C.POINTER(v.Log)]
    d.mu_ignis_move.argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_ignis_visual.argtypes = [C.c_void_p, C.c_int32]
    return lib


def time_sample(g):
    return v.f32(g.choice([0.0, -0.0, 1000.0, -3000.0, 1047.1975, 3141.5927, 12345.0, 2147483520.0, 3e9, -1e12,
                           math.inf, -math.inf, math.nan, g.uniform(-1e6, 1e6), g.uniform(0, 1e7),
                           g.uniform(0, 1e5)]))


def model_bytes(g, count):
    model = bytearray(g.getrandbits(8) for _ in range(0x100))
    struct.pack_into('<h', model, 0x26, count)
    struct.pack_into('<I', model, 0x30, v.ACTIONS)
    actions = bytearray(g.getrandbits(8) for _ in range(16 * ACTIONS))
    for k in range(ACTIONS):
        struct.pack_into('<f', actions, 16 * k + 4, v.f32(g.choice([0.3, 0.25, 0.5, 0.0, g.uniform(0, 1)])))
        struct.pack_into('<h', actions, 16 * k + 8, g.choice([0, 1, 2, 10, 31, g.randrange(-5, 60)]))
    return model, actions


def bone_position(k):
    return (float(k * 17 + 5), float(k * -13 + 7), float(k * 11 - 3))


def family(machine, lib, name, cases):
    g = random.Random('worlds-p2-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    cls = 137 if prefix == 'kanturu' else 138
    types = TYPES[prefix]
    for n in range(cases):
        typ = types[n % len(types)] if n % 9 else g.randrange(-50, 400)
        if name in DIRECTED and n % 3 == 1:
            typ = g.choice(DIRECTED[name])
        world = cls if n % 4 else [0, 38, 136, 137, 138, 139, 140][(n // 4) % 7]
        null = n % 23 == 0
        present = n % 7 != 0
        if name == 'ignis_create' and not present and typ in (79, 148):
            present = True   # the client writes the StreamMesh byte through the null model there
        count = g.choice([0, 1, 2, 3, 4, 6, 8, -1, g.randrange(-3, 9)])
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        struct.pack_into('<H', raw, 0x2a, g.choice([0, 1, 2, 3, 0, 1, 2, 3, 4, 7]))
        struct.pack_into('<ii', raw, 0x30, g.choice([0, 1, 2, 24, 25, 40, g.randrange(-5, 60)]),
                         g.choice([0, 1, 2, 25, 30, g.randrange(-5, 60)]))
        if n % 5 == 0:
            v.put_f(raw, 0xa0, v.f32(g.choice([-2.0, 0.1, 0.25, 1e10, -1e10, math.nan, 100.0])))
        model, actions = model_bytes(g, count)
        action = struct.unpack_from('<H', raw, 0x2a)[0]
        keys = struct.unpack_from('<h', actions, 16 * action + 8)[0]
        speed = struct.unpack_from('<f', actions, 16 * action + 4)[0]
        frame_time = v.f32(g.choice([0.1, 0.0, 0.4, 0.25, g.uniform(0, 1)]))
        v.put_f(raw, 0xd0, v.f32(g.choice([keys - 1 - speed - frame_time, keys - 1, 0.0, 7.9, 8.0, 28.0, 28.5,
                                           g.uniform(-2, 40), math.nan])))
        time = time_sample(g)
        if prefix == 'kanturu' and method != 'create' and math.isinf(time):
            time = v.f32(3e9)   # sin(+-inf) takes the CRT domain-error path (errno), not executed here
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones, cbones = [], [], []
        scale = v.from_bits(struct.unpack_from('<I', raw, 0xa0)[0])
        if method == 'visual' and prefix == 'kanturu' and not math.isnan(scale) and abs(scale * 10.0) < 1:
            v.put_f(raw, 0xa0, 1.0)   # the client divides by (int)(scale * 10)

        def lookup(m):
            assert m.argument(0) == struct.unpack_from('<I', raw, 0x5c)[0]
            return (v.MODEL if present else 0, 4)

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL and a[3] == 0 and v.read_vec(m, a[1]) == (0, 0, 0)
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + k * 0x30
            bones.append(k)
            m.uc.mem_write(a[2], v.pack_f(*bone_position(k)))
            return (0, 16)

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((0x16cacfc, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0

        def register(m):
            a = [m.argument(k) for k in range(2)]
            assert a[0] == v.OBJECTS
            calls.append((0x16d9f51, 0, a[1]))
            return 0

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6:] == [0, 0]
            calls.append((0x168fafd, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], 0))
            return 0

        def sprite(m):
            a = [m.argument(k) for k in range(9)]
            assert a[4] == v.OBJECTS and a[6:8] == [0, 4] and v.read_vec(m, a[8]) == SPRITE_DESCRIPTOR
            calls.append((0x1692eb7, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) +
                         (a[5], 1, 0, 4))
            return 0

        def joint(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] in (0, v.OBJECTS) and a[7:] == JOINT_TAIL
            calls.append((0x153b02c, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], int(a[5] == v.OBJECTS), a[6]))
            return 0

        def sound(m):
            a = [m.argument(k) for k in range(3)]
            assert a[1] == v.OBJECTS
            calls.append((0xa6ac96, 0, a[0], 1, a[2]))
            return 0
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                           am.defined_region('frame-time', v.FRAME_TIME, v.pack_f(frame_time),
                                                             writable=False),
                                           am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e)),
                                           am.defined_region('model', v.MODEL, bytes(model)),
                                           am.defined_region('actions', v.ACTIONS, bytes(actions))])
        args = [NULL if null else v.OBJECTS] + ([NULL if not present else v.MODEL] if method == 'visual' else [])
        result = v.run(machine, BODIES[name][0], args, regs,
                       {0x966cc4: lambda m: v.FAKE, 0xeaa8cf: lookup, 0x12b6ef1: bone, 0x16cacfc: light,
                        0x16d9f51: register, 0x168fafd: particle, 0x1692eb7: sprite, 0x153b02c: joint,
                        0xa6ac96: sound, 0x1989721: lambda m: rnd()},
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())

        def table(ctx, t, a, count_out, keys_out, speed_out):
            if not present:
                return 0
            count_out[0] = count
            keys_out[0] = struct.unpack_from('<h', actions, 16 * a + 8)[0]
            speed_out[0] = struct.unpack_from('<f', actions, 16 * a + 4)[0]
            return 1
        c_table = ACTION_FN(table)

        def cb(ctx, k, local, out):
            assert list(local[:3]) == [0, 0, 0]
            cbones.append(k)
            for q, value in enumerate(bone_position(k)):
                out[q] = value
        c_bone = BONE(cb)
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.time = time
        inputs.rand_fn = fn
        obj = None if null else co
        d = lib.dll
        if name == 'kanturu_create':
            handled = d.mu_kanturu_ug_create(obj, 0, world, fn, None, C.byref(log))
        elif name == 'kanturu_move':
            handled = d.mu_kanturu_ug_move(obj, 0, C.byref(inputs), c_table, frame_time, C.byref(log))
        elif name == 'kanturu_visual':
            handled = d.mu_kanturu_ug_visual(obj, 0, int(present), time, fn, c_bone, None, C.byref(log))
        elif name == 'ignis_create':
            handled = d.mu_ignis_create(obj, 0, world, count if present else -1, C.byref(log))
        elif name == 'ignis_move':
            handled = d.mu_ignis_move(obj, 0, C.byref(inputs), C.byref(log))
        else:
            handled = d.mu_ignis_visual(obj, 0)
        # model writes requested by C, applied to the harness model
        events, cmodel, cactions = [], bytearray(model), bytearray(actions)
        for e in v.log_events(log):
            if e[0] == PLAY_SPEED and e[2:4] == (typ & 0xffffffff, ALL):
                if present:
                    for k in range(max(count, 0)):
                        struct.pack_into('<I', cactions, 16 * k + 4, e[4])
            elif e[0] == MODEL_STREAM and present:
                cmodel[0x94] = e[2] & 0xff
            else:
                events.append(e)
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        model_equal = (bytes(cmodel) == bytes(result['regions']['model']) and
                       bytes(cactions) == bytes(result['regions']['actions']))
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null' if null else 'handled' if handled else 'unhandled')
        tally.count('model' if present else 'no model')
        tally.count('events', len(calls))
        tally.add(not diff and model_equal and handled == (result['eax'] & 255) and calls == events and
                  rnd.seed == crnd.seed and bones == cbones,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'model_equal': model_equal,
                   'al': result['eax'] & 255, 'c_al': handled, 'calls': calls[:3], 'c': events[:3],
                   'rng_equal': rnd.seed == crnd.seed, 'bones': bones, 'c_bones': cbones})
    return tally.report()


MUTANTS = [
    ('kanturu_underground.c', 'world != 137 ||', 'world != 136 ||', 'kanturu_create'),
    ('kanturu_underground.c', 'o[MU_OBJF_LIGHT_DYNAMIC] = 0;', 'o[MU_OBJF_LIGHT_DYNAMIC] = 1;', 'kanturu_create'),
    ('kanturu_underground.c', 'wb_float(e, 0.3f);', 'wb_float(e, 0.25f);', 'kanturu_create'),
    ('kanturu_underground.c', 'case 121: case 122:', 'case 121: case 123:', 'kanturu_create'),
    ('kanturu_underground.c', 'if (t == 3) wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 0);',
     'if (t == 3) wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 1);', 'kanturu_create'),
    ('kanturu_underground.c', 'random(ctx) % 30 + 20);\n    switch', 'random(ctx) % 30 + 21);\n    switch',
     'kanturu_create'),
    ('kanturu_underground.c', 'case 93: case 94: case 95: case 96:\n        mu_obj_set_f32',
     'case 93: case 94: case 95: case 97:\n        mu_obj_set_f32', 'kanturu_create'),
    ('kanturu_underground.c', 'in->world != 137', 'in->world != 138', 'kanturu_move'),
    ('kanturu_underground.c', '0.0015f', '0.0016f', 'kanturu_move'),
    ('kanturu_underground.c', 'if (0.1f >= l) l = 0.1f;', 'if (0.1f >= l) l = 0.15f;', 'kanturu_move'),
    ('kanturu_underground.c', '1.0f > l ? l : 1.0f', '1.0f > l ? l : 0.9f', 'kanturu_move'),
    ('kanturu_underground.c', '0.02f);', '0.03f);', 'kanturu_move'),
    ('kanturu_underground.c', '(float)keys - 1.0f', '(float)keys - 2.0f', 'kanturu_move'),
    ('kanturu_underground.c', '{2, 25}', '{2, 24}', 'kanturu_move'),
    ('kanturu_underground.c', 'action == 3 ? 0 :', 'action == 3 ? 1 :', 'kanturu_move'),
    ('kanturu_underground.c', 'mu_obj_set_i32(o, 0x30, counter + 1);', 'mu_obj_set_i32(o, 0x30, counter);',
     'kanturu_move'),
    ('kanturu_underground.c', 'if (!o || !has_model) return 0;', 'if (!o || has_model < 0) return 0;', 'kanturu_visual'),
    ('kanturu_underground.c', '(first ? 20 : second ? 10 : 5)', '(first ? 20 : second ? 10 : 4)', 'kanturu_visual'),
    ('kanturu_underground.c', '15u : 12u', '15u : 13u', 'kanturu_visual'),
    ('kanturu_underground.c', 'bone(ctx, 4, zero, b);', 'bone(ctx, 3, zero, b);', 'kanturu_visual'),
    ('kanturu_underground.c', 'wb_float(e, 1.5f);', 'wb_float(e, 1.0f);', 'kanturu_visual'),
    ('kanturu_underground.c', '% 80) + to[0]', '% 70) + to[0]', 'kanturu_visual'),
    ('kanturu_underground.c', '0x12, 0, 40.0f', '0x12, 1, 40.0f', 'kanturu_visual'),
    ('ignis_volcano.c', 'world != 138 ||', 'world != 137 ||', 'ignis_create'),
    ('ignis_volcano.c', 'model_actions > 0', 'model_actions >= 0', 'ignis_create'),
    ('ignis_volcano.c', 'case 171: case 173:', 'case 171: case 172:', 'ignis_create'),
    ('ignis_volcano.c', 'o[MU_OBJF_AFTER_CHARACTER] = 1;', 'o[MU_OBJF_AFTER_CHARACTER] = 0;', 'ignis_create'),
    ('ignis_volcano.c', 'case 79: case 148:', 'case 79: case 149:', 'ignis_create'),
    ('ignis_volcano.c', 'case 175: case 176:', 'case 175: case 177:', 'ignis_create'),
    ('ignis_volcano.c', 'in->world != 138', 'in->world != 139', 'ignis_move'),
    ('ignis_volcano.c', '% 4 + 3', '% 4 + 2', 'ignis_move'),
    ('ignis_volcano.c', 's * 0.04f, 3);', 's * 0.04f, 2);', 'ignis_move'),
    ('ignis_volcano.c', '8.0f > frame', '8.0f >= frame', 'ignis_move'),
    ('ignis_volcano.c', 'frame > 28.0f', 'frame >= 28.0f', 'ignis_move'),
    ('ignis_volcano.c', '(void)o; (void)index;\n    return 0;', '(void)o; (void)index;\n    return 1;',
     'ignis_visual')]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=1000)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    lib = bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}'))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()}, 'families': {}, 'mutants': []}
    for name in BODIES:
        r = report['families'][name] = family(machine, lib, name, a.cases)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, r['examples'][:1], flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-p2-') as tmp:
            for n, (file, old, new, name) in enumerate(MUTANTS):
                dest = Path(tmp) / str(n)
                for directory in ('objects', 'terrain', 'model-codec', 'record-math', 'movement'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__'))
                p = dest / 'objects' / file
                s = p.read_text()
                assert old in s, old
                p.write_text(s.replace(old, new, 1))
                mutated = bind(v.Library(v.build_library(dest)))
                r = family(machine, mutated, name, a.cases)
                m = {'family': name, 'file': file, 'change': new, 'detected': r['mismatch_count'], 'stopped': r['stopped']}
                report['mutants'].append(m)
                print('mutant', m, flush=True)
                shutil.rmtree(dest)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
