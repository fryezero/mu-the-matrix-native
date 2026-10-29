#!/usr/bin/env python3
"""Abyss of Atlans 1-3 (worlds 128-130) primary slots against pinned instructions.

Nine families: create, move and visual of each of the three classes. Full AL,
all OBJECT bytes, ordered CreateParticle arguments and final MSVC RNG (none of
these bodies draw it). The sine helper 0x009681bd and the CRT sine it calls run
as original instructions. Null object/model arguments and foreign worlds are
sampled; each class compares its own world constant with the world global.
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
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'abyss1_create': (0xd5cf32, 0xd5d014), 'abyss1_move': (0xd5d04a, 0xd5d2f6),
          'abyss1_visual': (0xd5d564, 0xd5d5ad),
          'abyss2_create': (0xd5ebd2, 0xd5ecb4), 'abyss2_move': (0xd5ecea, 0xd5ef96),
          'abyss2_visual': (0xd5f1f1, 0xd5f23a),
          'abyss3_create': (0xd60316, 0xd603f8), 'abyss3_move': (0xd6042e, 0xd606da),
          'abyss3_visual': (0xd60948, 0xd60991)}
# The create bodies end with a 13-entry jump table; it is read as data.
TABLES = {'abyss1_create': (0xd5d016, 0xd5d04a), 'abyss2_create': (0xd5ecb6, 0xd5ecea),
          'abyss3_create': (0xd603fa, 0xd6042e)}
CLASS = {'abyss1': 128, 'abyss2': 129, 'abyss3': 130}
TYPES = [-2147483648, -1, 0, 7, 21, 22, 23, 24, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 49, 50, 51,
         52, 65, 66, 67, 68, 69, 70, 71, 160, 161, 162, 165, 166, 167, 168, 170, 172, 173, 174, 175, 178, 180, 181,
         200, 2147483647]
TIMERS = [0.0, -0.0, 4.9, 4.9000001, 5.0, 5.05, 9.9, 9.9000001, 9.95, 10.0, 10.05, -1.0, math.nan, math.inf, -math.inf]
PARTICLE = 0x168fafd


def bind(lib):
    d = lib.dll
    d.mu_abyss_create.argtypes = [C.c_int32, C.c_void_p, C.c_int32]
    d.mu_abyss_move.argtypes = [C.c_int32, C.c_void_p, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_abyss_visual.argtypes = [C.c_int32, C.c_void_p, C.c_int32, C.c_int]
    return lib


def family(machine, lib, name, cases):
    g = random.Random('worlds-o-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    cls = CLASS[prefix]
    for n in range(cases):
        typ = TYPES[n % len(TYPES)] if n % 11 else g.randrange(-50, 400)
        if method == 'move' and n % 3 == 1:
            typ = 22   # the only requesting branch: a third of the move cases, over directed timers
        world = cls if n % 5 else [0, 127, 128, 129, 130, 131][(n // 5) % 6]
        null_object = n % 37 == 36
        present = n % 7 != 0
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        v.put_f(raw, 0xb4, v.f32(g.choice(TIMERS + [g.uniform(-2, 12)])))
        time = v.f32(g.choice([0, -0.0, -1000, 1000, 392.69908142089844, 1570.79638671875, g.uniform(-1e6, 1e6)]))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[7] == 0
            calls.append((PARTICLE, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                           am.defined_region('model', v.MODEL, bytes(0x100))])
        args = [0 if null_object else v.OBJECTS]
        if method == 'visual':
            args.append(v.MODEL if present else 0)
        result = v.run(machine, BODIES[name][0], args, regs, {PARTICLE: particle, 0x1989721: lambda m: rnd()},
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        target = None if null_object else co
        if method == 'create':
            handled = lib.dll.mu_abyss_create(cls, target, world)
        elif method == 'move':
            inputs = v.MoveInputs()
            inputs.world, inputs.time, inputs.has_model = world, time, present
            inputs.rand_fn = v.RAND_FN(lambda ctx: crnd())
            handled = lib.dll.mu_abyss_move(cls, target, 0, C.byref(inputs), C.byref(log))
        else:
            handled = lib.dll.mu_abyss_visual(cls, target, world, int(present))
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null object', int(null_object))
        tally.count('events', len(calls))
        if method == 'visual':
            tally.count('model absent', int(not present))
        ok = (not diff and handled == (result['eax'] & 255) and calls == v.log_events(log) and rnd.seed == crnd.seed)
        tally.add(ok, {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                       'c_al': handled, 'calls': calls[:3], 'c': v.log_events(log)[:3]})
    return tally.report()


F = 'abyss_atlans.c'
MUTANTS = [
    (F, 'if (world != cls || !o) return 0;\n    const int32_t t', 'if (world < cls || !o) return 0;\n    const int32_t t', 'abyss1_create'),
    (F, 'case 41: case 44:', 'case 42: case 44:', 'abyss2_create'),
    (F, 'AFTER_CHARACTER] = 1', 'AFTER_CHARACTER] = 2', 'abyss3_create'),
    (F, 't >= 161 && t <= 180', 't >= 162 && t <= 180', 'abyss1_create'),
    (F, 't != 173 && t != 174', 't != 173', 'abyss2_create'),
    (F, 't <= 180 &&', 't <= 181 &&', 'abyss3_create'),
    (F, 'if (in->world != cls || !o)', 'if (in->world > cls || !o)', 'abyss1_move'),
    (F, 'MU_OBJF_TIMER) + 0.1f', 'MU_OBJF_TIMER) + 0.11f', 'abyss2_move'),
    (F, 'MU_OBJF_TIMER) > 10.0f', 'MU_OBJF_TIMER) >= 10.0f', 'abyss3_move'),
    (F, 'MU_OBJF_TIMER) > 5.0f', 'MU_OBJF_TIMER) > 6.0f', 'abyss1_move'),
    (F, 'wb_arg(e, 0x7fcd);', 'wb_arg(e, 0x7fce);', 'abyss2_move'),
    (F, 'wb_get(o, MU_OBJF_LIGHT, v);', 'wb_get(o, MU_OBJF_ANGLE, v);', 'abyss3_move'),
    (F, 'wb_float(e, 1.0f);', 'wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE));', 'abyss1_move'),
    (F, 'pulse(in->time, 0.002f, 0.3f)', 'pulse(in->time, 0.004f, 0.3f)', 'abyss2_move'),
    (F, '* amplitude + 0.5f', '* amplitude + 0.4f', 'abyss3_move'),
    (F, 'case 32: case 34:', 'case 32: case 33:', 'abyss1_move'),
    (F, 'case 69: case 70:', 'case 69:', 'abyss2_move'),
    (F, 'MU_OBJF_VELOCITY, 0.05f', 'MU_OBJF_VELOCITY, 0.06f', 'abyss3_move'),
    (F, 'case 38:\n        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);', 'case 38:\n        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1);', 'abyss1_move'),
    (F, 'mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);\n        mu_obj_set_f32(o, MU_OBJF_TIMER', 'mu_obj_set_f32(o, MU_OBJF_TIMER', 'abyss2_move'),
    (F, '(float)sin((double)(time * rate))', '(float)sin((double)time * rate)', 'abyss3_move'),
    (F, '!o || !model_present', '!o || model_present < 0', 'abyss1_visual'),
    (F, 'MU_OBJF_TYPE) == 39', 'MU_OBJF_TYPE) == 38', 'abyss2_visual'),
    (F, 'if (world != cls || !o || !model_present)', 'if (world != (cls | 1) || !o || !model_present)', 'abyss3_visual')]


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
    sha = lambda s, e: hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)} for n, (s, e) in BODIES.items()},
              'tables': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)} for n, (s, e) in TABLES.items()},
              'families': {}, 'mutants': []}
    for name in BODIES:
        r = report['families'][name] = family(machine, lib, name, a.cases)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-o-') as tmp:
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
                m = {'family': name, 'file': file, 'change': new, 'detected': r['mismatch_count'],
                     'stopped': r['stopped']}
                report['mutants'].append(m)
                print('mutant', m, flush=True)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
