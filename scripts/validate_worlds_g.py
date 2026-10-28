#!/usr/bin/env python3
"""Santa Village/Vulcanus production C versus pinned original class instructions.

Full method entry/return, byte-for-byte OBJECT, AL, ordered engine arguments and
RNG state. Model is only a non-null gate. Engine allocation calls are recording
stubs; vector accessors, world predicates and client sine execute as instructions.
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
import validate_object_render as v
import pins

ROOT = Path(__file__).resolve().parents[1]
BODIES = {'santa_create': (0xe4231c, 0xe4236e), 'santa_move': (0xe42370, 0xe423d6),
          'santa_visual': (0xe423d8, 0xe426cf), 'vulcanus_create': (0xe8ec09, 0xe8ec80),
          'vulcanus_move': (0xe8ec80, 0xe8ece1), 'vulcanus_visual': (0xe8ece1, 0xe8f515)}
TYPES = {'santa': list(range(0xb, 0x1e)) + [-1, 0, 0x7fffffff, -2147483648],
         'vulcanus': [-2147483648, -1, 0, 1, 2, 3, 4, 5, 6, 7, 0x45, 0x46, 0x47, 0x49, 0x4a, 0x4b, 0x7fffffff]}


def bind(lib):
    for name in BODIES:
        args = [C.c_void_p]
        if name == 'santa_move' or name in ('vulcanus_create', 'vulcanus_move'):
            args += [C.c_int32]
        elif name == 'santa_visual':
            args += [C.c_int32, C.c_int, C.c_float, C.POINTER(v.Log)]
        elif name == 'vulcanus_visual':
            args += [C.c_int32, C.c_int32, C.c_int, C.c_float, v.RAND_FN, C.c_void_p, C.POINTER(v.Log)]
        getattr(lib.dll, 'mu_' + name).argtypes = args
    return lib


def family(machine, lib, name, cases):
    g = random.Random('worlds-g-' + name)
    tally = v.Tally(name)
    prefix, method = name.split('_')
    own_world = 62 if prefix == 'santa' else 63
    for n in range(cases):
        typ = TYPES[prefix][n % len(TYPES[prefix])]
        world = own_world if n % 5 else [0, 61, 62, 63, 64][(n // 5) % 5]
        present = n % 7 != 0
        raw = bytearray(v.poison_object(g))
        v.put_i(raw, 0x5c, typ)
        # Finite inputs, signed coordinates and invalid float->int conversions.
        x = g.choice([-2147483648.0, 2147483648.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 20000.25])
        v.put_f(raw, 0x158, x, v.f32(g.uniform(-1000, 25000)), v.f32(g.uniform(-1000, 1000)))
        v.put_f(raw, 0x164, *[v.f32(g.uniform(-360, 360)) for _ in range(3)])
        v.put_f(raw, 0xa0, g.choice([0.0, -0.0, 0.25, 1.0, 8.0]))
        time = g.choice([0.0, -0.0, -1000.0, 1000.0, 1570.79638671875, 3141.5927734375,
                         v.f32(g.uniform(-1e6, 1e6))])
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6] in (0, v.OBJECTS) and a[7] == 0
            calls.append((0x168fafd, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) +
                         v.read_vec(m, a[3]) + (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0

        def sprite(m):
            a = [m.argument(k) for k in range(9)]
            assert a[4] == v.OBJECTS and a[5:8] == [0, 0, 4]
            assert v.read_vec(m, a[8]) == (1, 1, v.bits(1.0))
            calls.append((0x1692eb7, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) +
                         v.read_vec(m, a[3]) + (a[5], 1, a[6], a[7]))
            return 0

        def joint(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == v.OBJECTS and a[7:] == [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]
            calls.append((0x153b02c, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) +
                         v.read_vec(m, a[3]) + (a[4], 1, a[6]))
            return 0

        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                          am.defined_region('time', v.TIME, v.pack_f(time), writable=False)])
        result = v.run(machine, BODIES[name][0], [v.OBJECTS] + ([v.FAKE if present else 0] if method == 'visual' else []),
                       regs, {0x168fafd: particle, 0x1692eb7: sprite, 0x153b02c: joint,
                              0x1989721: lambda m: rnd()},
                       ecx=v.FAKE, cleanup=8 if method == 'visual' else 4)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        args = [co]
        if name == 'santa_move' or name in ('vulcanus_create', 'vulcanus_move'):
            args += [world]
        elif name == 'santa_visual':
            args += [0, present, time, C.byref(log)]
        elif name == 'vulcanus_visual':
            args += [0, world, present, time, fn, None, C.byref(log)]
        handled = getattr(lib.dll, 'mu_' + name)(*args)
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        tally.count('type ' + str(typ))
        tally.count('off_world' if world != own_world else 'own_world')
        tally.count('events', len(calls))
        tally.count('handled ' + str(handled))
        tally.add(not diff and handled == (result['eax'] & 255) and calls == v.log_events(log) and rnd.seed == crnd.seed,
                  {'case': n, 'type': typ, 'world': world, 'time': time, 'diff': diff[:8],
                   'al': result['eax'] & 255, 'c_al': handled, 'calls': calls[:2], 'c': v.log_events(log)[:2],
                   'rng_equal': rnd.seed == crnd.seed})
    return tally.report()


MUTANTS = [
    ('santa_village.c', 'case 0x0c:', 'case 0x0b:', 'santa_create'),
    ('santa_village.c', '0.06f', '0.07f', 'santa_move'),
    ('santa_village.c', 'world != 62', 'world != 61', 'santa_move'),
    ('santa_village.c', '8.0f *', '7.0f *', 'santa_visual'),
    ('santa_village.c', 'if (!model_present ||', 'if (model_present < 0 ||', 'santa_visual'),
    ('vulcanus.c', 'type <= 6', 'type < 6', 'vulcanus_create'),
    ('vulcanus.c', 'o[MU_OBJF_AFTER_CHARACTER] = 1', 'o[MU_OBJF_AFTER_CHARACTER] = 0', 'vulcanus_create'),
    ('vulcanus.c', 'type <= 6) {\n        mu_obj_set_i32', 'type < 6) {\n        mu_obj_set_i32', 'vulcanus_move'),
    ('vulcanus.c', 'k < 20', 'k < 19', 'vulcanus_visual'),
    ('vulcanus.c', 'random(context) % 4 == 0', 'random(context) % 3 == 0', 'vulcanus_visual'),
    ('vulcanus.c', 'wb_arg(e, 4);', 'wb_arg(e, 3);', 'vulcanus_visual'),
    ('vulcanus.c', '{0.3f, 0.3f, 0.3f}', '{0.2f, 0.3f, 0.3f}', 'vulcanus_visual'),
    ('vulcanus.c', '0x8085', '0x8084', 'vulcanus_visual'),
]


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
              'bodies': {n: {'start': hex(s), 'end': hex(e), 'sha256': hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()}, 'families': {}, 'mutants': []}
    for name in BODIES:
        report['families'][name] = family(machine, lib, name, a.cases)
        print(name, report['families'][name], flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-g-') as tmp:
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
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
