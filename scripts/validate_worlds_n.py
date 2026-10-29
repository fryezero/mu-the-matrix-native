#!/usr/bin/env python3
"""World-113 and world-116..120 primary slots against pinned instructions.

Nixies Lake create/move with predicate 0x00e34404, the five Deep Dungeon
create/move methods and their shared visual slot 0x00d5cc9b. Full AL, all
OBJECT bytes, ordered output calls and final MSVC RNG are compared. Register,
AddTerrainLight, CreateEffect and rand are recording boundaries; the client's
vector helpers and the predicate execute as original instructions.
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
DD = {116: ((0xe3e34b, 0xe3e46d), (0xe3e46d, 0xe3e94a)), 117: ((0xe3efe6, 0xe3f125), (0xe3f125, 0xe3f602)),
      118: ((0xe3fce8, 0xe3fe3c), (0xe3fe3c, 0xe40319)), 119: ((0xe409e8, 0xe40b38), (0xe40b38, 0xe41015)),
      120: ((0xe41823, 0xe41a1f), (0xe41a1f, 0xe41efc))}
BODIES = {'nixies_create': (0xe3441c, 0xe3473f), 'nixies_move': (0xe3473f, 0xe347a8),
          **{f'dd{w}_create': c for w, (c, _) in DD.items()}, **{f'dd{w}_move': m for w, (_, m) in DD.items()},
          'shared_visual': (0xd5cc9b, 0xd5cca8)}
EXTREMES = [-2147483648, -1, 2147483647, 1000, 0x7dc]
TYPES = {'nixies': list(range(-1, 165)) + EXTREMES, 'dd': list(range(-1, 72)) + [77, 100, 160] + EXTREMES}
NULL = 0
KEYED = 0xe3e8f8


def bind(lib):
    d = lib.dll
    d.mu_nixies_create.argtypes = [C.c_void_p, C.c_int32]
    d.mu_nixies_move.argtypes = [C.c_void_p, C.POINTER(v.MoveInputs)]
    d.mu_deep_dungeon_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.POINTER(v.Log)]
    d.mu_deep_dungeon_move.argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_worlds_n_visual.argtypes = [C.c_void_p, C.c_int32]
    return lib


def time_sample(g):
    return v.f32(g.choice([0.0, -0.0, 1000.0, 2000.0, -3000.0, 999.5, 1999.75, 12345.0, 2147483520.0,
                           -2147483648.0, 3e9, -1e12, math.inf, -math.inf, math.nan,
                           g.uniform(-1e6, 1e6), g.uniform(0, 1e7), g.uniform(0, 1e7)]))


def family(machine, lib, name, cases):
    g = random.Random('worlds-n-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    cls = 113 if prefix == 'nixies' else int(prefix[2:]) if prefix.startswith('dd') else 116
    types = TYPES['nixies' if prefix == 'nixies' else 'dd']
    for n in range(cases):
        typ = types[n % len(types)] if n % 9 else g.randrange(-50, 400)
        if method == 'move' and n % 3 == 1:   # directed: the handled move types
            typ = g.choice([77] if prefix == 'nixies' else [22, 23, 24, 41, 42, 52, 52, 62, 63, 64, 65, 66, 67])
        world = cls if n % 4 else [0, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121][(n // 4) % 11]
        null = prefix == 'nixies' and n % 23 == 0
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        if n % 5 == 0:
            v.put_f(raw, 0xa0, v.f32(g.choice([-1.0, 0.0, 65535.9, 65536.0, 70000.0, 1e10, math.nan])))
        time = time_sample(g)
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []

        def light(m):
            a = [m.argument(k) for k in range(5)]
            assert a[4] == v.FRAME_LIGHT
            calls.append((0x16cacfc, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            return 0

        def register(m):
            assert [m.argument(k) for k in range(2)] == [v.OBJECTS, 1]
            calls.append((0x16d9f51, 0, 1))
            return 0

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[1:4] == [v.OBJECTS + 0x158, v.OBJECTS + 0x164, v.OBJECTS + 0xec]
            assert a[6:8] == [0xffffffff, 0] and a[9:] == [0, v.bits(0.0), 0xffffffff, 0, 0]
            calls.append((KEYED, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], a[8]))
            return 0
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('time', v.TIME, v.pack_f(time), writable=False)])
        args = [NULL if null else v.OBJECTS] + ([0] if method == 'visual' else [])
        result = v.run(machine, BODIES[name][0], args, regs,
                       {0x16cacfc: light, 0x16d9f51: register, 0x13c0eaa: effect, 0x1989721: lambda m: rnd()},
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.time = time
        inputs.rand_fn = fn
        obj = None if null else co
        if name == 'nixies_create':
            handled = lib.dll.mu_nixies_create(obj, world)
        elif name == 'nixies_move':
            handled = lib.dll.mu_nixies_move(obj, C.byref(inputs))
        elif method == 'create':
            handled = lib.dll.mu_deep_dungeon_create(obj, 0, cls, C.byref(log))
        elif method == 'move':
            handled = lib.dll.mu_deep_dungeon_move(obj, 0, C.byref(inputs), C.byref(log))
        else:
            handled = lib.dll.mu_worlds_n_visual(obj, 0)
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null' if null else 'handled' if handled else 'unhandled')
        tally.count('events', len(calls))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == v.log_events(log) and
                  rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                   'c_al': handled, 'calls': calls[:3], 'c': v.log_events(log)[:3], 'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


MUTANTS = [
    ('nixies_lake.c', 'world != 113 ||', 'world != 112 ||', 'nixies_create'),
    ('nixies_lake.c', 'case 159:', 'case 158:', 'nixies_create'),
    ('nixies_lake.c', 'case 123: case 161:', 'case 123: case 160:', 'nixies_create'),
    ('nixies_lake.c', 'o[MU_OBJF_AFTER_CHARACTER] = 1;\n        break;', 'break;', 'nixies_create'),
    ('nixies_lake.c', 'in->world != 113', 'in->world != 114', 'nixies_move'),
    ('nixies_lake.c', '!= 77', '!= 76', 'nixies_move'),
    ('nixies_lake.c', '% 2000', '% 1000', 'nixies_move'),
    ('nixies_lake.c', '0.0005f', '0.0004f', 'nixies_move'),
    ('deep_dungeon.c', 'return t == 6;', 'return t == 7;', 'dd116_create'),
    ('deep_dungeon.c', 'case 59:', 'case 58:', 'dd116_create'),
    ('deep_dungeon.c', 't == 1 || t == 3 || t == 50', 't == 1 || t == 4 || t == 50', 'dd117_create'),
    ('deep_dungeon.c', 'MU_OBJF_BOX_MAX + 8, 160.0f', 'MU_OBJF_BOX_MAX + 8, 150.0f', 'dd117_create'),
    ('deep_dungeon.c', 't == 23 || t == 50', 't == 24 || t == 50', 'dd118_create'),
    ('deep_dungeon.c', 'case 66: case 67:\n        mu_obj_set_i32', 'case 66: case 68:\n        mu_obj_set_i32', 'dd118_create'),
    ('deep_dungeon.c', 't == 18 || t == 35', 't == 18 || t == 36', 'dd119_create'),
    ('deep_dungeon.c', 'default:\n        return 0;\n    }\n}\nint mu_deep_dungeon_move',
     'default:\n        return 1;\n    }\n}\nint mu_deep_dungeon_move', 'dd119_create'),
    ('deep_dungeon.c', 't == 48 ||', 't == 47 ||', 'dd120_create'),
    ('deep_dungeon.c', '(t >= 20 && t <= 24)', '(t >= 20 && t <= 23)', 'dd120_create'),
    ('deep_dungeon.c', 't >= 62 && t <= 67', 't >= 62 && t <= 66', 'dd116_move'),
    ('deep_dungeon.c', '% 3 == 0', '% 3 == 1', 'dd116_move'),
    ('deep_dungeon.c', '0.41f', '0.42f', 'dd117_move'),
    ('deep_dungeon.c', 'wb_arg(e, 0x43a)', 'wb_arg(e, 0x43b)', 'dd117_move'),
    ('deep_dungeon.c', '% 4 + 3', '% 4 + 2', 'dd118_move'),
    ('deep_dungeon.c', 'wb_arg(e, 0); wb_arg(e, 0);', 'wb_arg(e, 0); wb_arg(e, 1);', 'dd118_move'),
    ('deep_dungeon.c', '% 1000', '% 999', 'dd119_move'),
    ('deep_dungeon.c', 's * c[2], 3);', 's * c[2], 2);', 'dd119_move'),
    ('deep_dungeon.c', '-(float)(wb_int', '(float)(wb_int', 'dd120_move'),
    ('deep_dungeon.c', 'case 41: case 42:', 'case 41: case 43:', 'dd120_move'),
    ('deep_dungeon.c', '(void)o; (void)index;\n    return 0;', '(void)o; (void)index;\n    return 1;', 'shared_visual')]


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
        with tempfile.TemporaryDirectory(prefix='worlds-n-') as tmp:
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
