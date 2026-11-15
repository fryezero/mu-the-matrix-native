#!/usr/bin/env python3
"""RENDER-WORLDS-PICK-001 step 3: chain hook 11 against pinned original instructions and compiled mutants.

The hook is the visual slot +0x34 = 0x00db7656 of the singleton 0x01ec9118, which RenderObjectVisual's common chain
calls at 0x017fcc58..0x017fcc77 (getter 0x00db747f, then `call [vtable + 0x34]`). The whole slot runs as client
code, with its world test 0x0095fba9 (worlds 45..50 and 98..99) and the sprite's default-argument constructor
0x00a0c1d0. Stubs: rand, CreateParticle, CreateSprite, CreateEffect and the imported clock. Compared: the ordered
requests with every argument, all OBJECT and model bytes, the rand state and AL, against mu_chain11_inner
(reconstructed/objects/world_inner6_visual.c).

chain11:        any world and type, the model sometimes absent
chain11_focus:  the eight worlds and the eleven named types; type 78's clock is placed around its random window
"""
import argparse
import ctypes as C
import json
import random
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_worlds_slots2 as w2
from validate_worlds_inner3 import Machine
ROOT = Path(__file__).resolve().parents[1]
ENTRY, WORLD_TEST, INSTANCE = 0x00db7656, 0x0095fba9, 0x01ec9118
PARTICLE, EFFECT, SPRITE, CLOCK = 0x168fafd, 0x13c0eaa, 0x1692eb7, 0x1a7c9a4
TYPES = [0x36, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f]
WORLDS = [45, 46, 47, 48, 49, 50, 98, 99]
GATES = {0x46: (3, 0), 0x47: (3, 0), 0x48: (3, 0), 0x49: (3, 0), 0x4a: (2, 0), 0x4b: (35, 5)}   # type: rand % n == k
BODIES = {'visual': (0x00db7656, 0x00db84d5), 'world_test': (0x0095fba9, 0x0095fbdc),
          'chain_call': (0x017fcc58, 0x017fcc83), 'getter': (0x00db747f, 0x00db7501)}


class Library:
    def __init__(self, path):
        self.dll = C.CDLL(str(path))
        P, I = C.c_void_p, C.c_int32
        self.dll.mu_chain11_inner.argtypes = [P, I, I, I, C.c_uint32, v.RAND_FN, P, C.POINTER(v.Log)]
        self.dll.mu_chain11_inner.restype = C.c_int
        self.dll.mu_chain11_world.argtypes = [I]
        self.dll.mu_chain11_world.restype = C.c_int


def compare(machine, lib, g, cases, focused=False):
    t = v.Tally('chain11_focus' if focused else 'chain11')
    for n in range(cases):
        if focused:
            world, typ = WORLDS[(n // 22) % len(WORLDS)], TYPES[(n // 2) % len(TYPES)]
        else:
            world = g.choice(WORLDS + [44, 51, 97, 100, 0, 37, g.randrange(0, 160)])
            typ = g.choice(TYPES + [0x35, 0x37, 0x45, 0x50, n % 300, g.randrange(0, 2000)])
        o = bytearray(w2.case_object(g, world, typ))
        model = bytes(0x100)
        present = focused or n % 7 != 0
        seed = g.randrange(2 ** 32)
        gate = GATES.get(typ)
        if focused and gate and n % 2:   # half of the gated cases start with a roll that passes the gate
            while v.MsvcRand(seed)() % gate[0] != gate[1]:
                seed = g.randrange(2 ** 32)
        a, cb = v.MsvcRand(seed), v.MsvcRand(seed)
        clock = g.randrange(2 ** 32)
        if typ == 0x4e and g.random() < 0.8:   # around the window [start + rand % 5, start + rand % 10 + 5)
            clock = 500 * g.randrange(0, 8000000) + (v.MsvcRand(seed)() % 485 + g.randrange(-3, 17)) % 500
        calls = []

        def particle(m):
            x = [m.argument(k) for k in range(8)]
            assert x[6] in (0, v.OBJECTS) and x[7] == 0, x
            calls.append((PARTICLE, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]), x[4],
                          x[5], int(x[6] == v.OBJECTS)))
            return 0

        def sprite(m):
            x = [m.argument(k) for k in range(9)]
            assert x[4] == v.OBJECTS and x[6:8] == [0, 4], x
            assert bytes(m.uc.mem_read(x[8], 12)) == struct.pack('<IIf', 1, 1, 1.0)
            calls.append((SPRITE, x[0], *v.read_vec(m, x[1]), x[2], *v.read_vec(m, x[3]), x[5], 1, 0, 4))
            return 0

        def effect(m):
            x = [m.argument(k) for k in range(14)]
            assert x[5] == 0 and x[6:8] == [0xffffffff, 0] and x[9:] == [0, 0, 0xffffffff, 0, 0], x
            calls.append((EFFECT, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]), x[4], 0,
                          x[8]))
            return 0
        stubs = {w2.RAND: lambda m: a(), PARTICLE: particle, SPRITE: sprite, EFFECT: effect,
                 machine.imports[CLOCK]: lambda m: clock}
        regions = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(o)), am.defined_region('model', v.MODEL, model),
            am.defined_region('instance', INSTANCE, bytes(0x48), writable=False)])
        result = v.run(machine, ENTRY, [v.OBJECTS, v.MODEL if present else 0], regions, stubs, ecx=INSTANCE, cleanup=8)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': hex(typ)}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        log = v.new_log()
        answer = lib.dll.mu_chain11_inner(co, 0, world, int(present), clock, v.RAND_FN(lambda c: cb()), None,
                                          C.byref(log))
        native = [(EFFECT if e[0] == 0xe68c23 else e[0], *e[2:]) for e in v.log_events(log)]
        same = result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == model
        ok = calls == native and a.seed == cb.seed and same and (result['eax'] & 255) == answer
        taken = result['eax'] & 255
        t.count('taken' if taken else 'not taken')
        if taken:
            t.count('type %#x' % typ)
            t.count('type %#x with requests' % typ, int(bool(calls)))
        t.count('requests', len(calls))
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': calls[:3], 'native': native[:3],
                   'object': same, 'rng': a.seed == cb.seed, 'al': [taken, answer]})
    return t


FAMILIES = {'chain11': lambda m, l, g, n: compare(m, l, g, n),
            'chain11_focus': lambda m, l, g, n: compare(m, l, g, n, True)}
MUTATIONS = [
    ('world 98', 'world >= 0x62 && world <= 0x63', 'world >= 0x63 && world <= 0x63'),
    ('world 99', 'world >= 0x62 && world <= 0x63', 'world >= 0x62 && world <= 0x62'),
    ('world 45', 'world >= 0x2d && world <= 0x32', 'world >= 0x2e && world <= 0x32'),
    ('world 50', 'world >= 0x2d && world <= 0x32', 'world >= 0x2d && world <= 0x31'),
    ('model', 'if (!model || !mu_chain11_world(world))', 'if (!mu_chain11_world(world))'),
    ('default answer', '    default:\n        return 0;', '    default:\n        return 1;'),
    ('type 54 drop', 'position[2] = position[2] - 100.0f;', 'position[2] = position[2] - 10.0f;'),
    ('type 54 light write', 'mu_obj_set_f32(o, MU_OBJF_LIGHT + 4 * k, 0.15f);', 'mu_obj_set_f32(o, MU_OBJF_LIGHT + 4 * k, 0.25f);'),
    ('type 54 second subtype', 'particle(o, i, 0x8022, position, light, 3, 1.0f, 0, l);', 'particle(o, i, 0x8022, position, light, 2, 1.0f, 0, l);'),
    ('smoke gate', 'case 0x46: case 0x47: case 0x48:   /* 0x00db7859 / 0x00db7926 / 0x00db79f3 */\n        if (rnd(c) % 3 == 0) {',
     'case 0x46: case 0x47: case 0x48:   /* 0x00db7859 / 0x00db7926 / 0x00db79f3 */\n        if (rnd(c) % 4 == 0) {'),
    ('smoke factor', '* 0.007f + 0.03f', '* 0.008f + 0.03f'),
    ('type 71 colour', 'if (t != 0x47)\n                smoke(o, i, teal, f, 15, l);', 'if (t != 0x48)\n                smoke(o, i, teal, f, 15, l);'),
    ('type 72 second', 'if (t != 0x46)\n                smoke(o, i, pink, f, 15, l);', 'if (t == 0x47)\n                smoke(o, i, pink, f, 15, l);'),
    ('pink green', '0.47265625f', '0.46875f'),
    ('smoke owner', 'particle(o, i, 0x7f89, position, light, sub, mu_obj_f32(o, MU_OBJF_SCALE), 1, l);',
     'particle(o, i, 0x7f89, position, light, sub, mu_obj_f32(o, MU_OBJF_SCALE), 0, l);'),
    ('type 73 factor', '* 0.002f + 0.03f', '* 0.003f + 0.03f'),
    ('type 73 grey', '{1.2f, 1.2f, 1.2f}', '{1.2f, 1.1f, 1.2f}'),
    ('type 74 gate', 'if (rnd(c) % 2 == 0) {\n            static const float black', 'if (rnd(c) % 3 == 0) {\n            static const float black'),
    ('type 74 subtype', 'black, 16, scale, 1, l);', 'black, 15, scale, 1, l);'),
    ('type 75 gate', 'rnd(c) % 35 == 5', 'rnd(c) % 35 == 0'),
    ('type 75 bitmap', 'particle(o, i, 0x7dea,', 'particle(o, i, 0x7dec,'),
    ('type 76 double', '(double)(rnd(c) % 100) * 0.01)', '(double)(rnd(c) % 100) * 0.02)'),
    ('type 77 channel', '{0.21484375f, 0.27734375f, 0.703125f + r}', '{0.21484375f + r, 0.27734375f, 0.703125f}'),
    ('ember lift', 'position[2] = position[2] + 20.0f;', 'position[2] = position[2] + 30.0f;'),
    ('ember glow scale', 'a[4] = wv_bits(scale * 6.0f);', 'a[4] = wv_bits(scale * 5.0f);'),
    ('ember order', '    particle(o, i, 0x7dec, position, light, 0, scale, 1, l);\n    position[2]',
     '    position[2] = position[2] + 0.0f;\n    particle(o, i, 0x7dec, position, light, 0, scale, 0, l);\n    position[2]'),
    ('type 78 cycle', 'clock % 500u', 'clock % 512u'),
    ('type 78 window start', 'if (phase < start + rnd(c) % 5)', 'if (phase <= start + rnd(c) % 5)'),
    ('type 78 window end', 'if (phase >= start + rnd(c) % 10 + 5)', 'if (phase > start + rnd(c) % 10 + 5)'),
    ('type 78 effect count', 'for (int k = 0; k < 4; ++k)\n            effect', 'for (int k = 0; k < 3; ++k)\n            effect'),
    ('type 78 last effect', 'effect(o, i, flash, 1, l);', 'effect(o, i, flash, 0, l);'),
    ('type 78 scatter', 'near[1] = (float)(rnd(c) % 80 - 40) + near[1];', 'near[1] = (float)(rnd(c) % 80 - 30) + near[1];'),
    ('type 78 random bitmap', '0x801c + rnd(c) % 2, near', '0x801c + rnd(c) % 3, near'),
    ('type 78 red scale', 'red, 0, 1.5f, 0, l);', 'red, 0, 1.0f, 0, l);'),
    ('type 79 call', 'if (rnd(c) % 1 == 0) {', 'if (1) {'),
    ('type 79 count', 'for (int k = 0; k < 5; ++k)\n                smoke', 'for (int k = 0; k < 4; ++k)\n                smoke'),
    ('type 79 factor', '* 0.03f + 0.008f', '* 0.03f + 0.009f'),
]


def build(root):
    subprocess.run(['make', '-s', '-j4', '-C', str(root / 'objects')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--only')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--mutant')
    p.add_argument('--text', default=v.pins.TEXT.default_str())
    p.add_argument('--data', default=v.pins.DATA.default_str())
    p.add_argument('--output')
    a = p.parse_args()
    machine = Machine(am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text'),
                      am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data'))
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    seed = lambda n: random.Random(0x611f + list(FAMILIES).index(n))   # noqa: E731
    # the hook's world test, as client code, for every world the census walks
    worlds = []
    for world in range(0, 161):
        r = v.run(machine, WORLD_TEST, [], v.global_regions(world, 6), {}, ecx=INSTANCE)
        assert not v.stopped_reason(r), v.stopped_reason(r)
        assert (r['eax'] & 255) == lib.dll.mu_chain11_world(world), world
        if r['eax'] & 255:
            worlds.append(world)
    report['accepted_worlds'] = worlds
    for name in names:
        row = FAMILIES[name](machine, lib, seed(name), a.cases).report()
        report['families'][name] = row
        print(name, json.dumps(row)[:3000], flush=True)
    if a.mutations:
        for label, old, new in MUTATIONS:
            if a.mutant and label not in a.mutant.split(','):
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-inner6-mut-') as td:
                root = Path(td)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects/world_inner6_visual.c'
                s = path.read_text()
                assert s.count(old) == 1, label
                path.write_text(s.replace(old, new, 1))
                mutant = build(root)
                tallies = [FAMILIES[name](machine, mutant, seed(name), a.cases) for name in names]
                item = {'name': label, 'cases': sum(x.cases for x in tallies),
                        'detected': sum(x.cases - x.equal - x.stopped for x in tallies),
                        'stopped': sum(x.stopped for x in tallies)}
                report['mutants'].append(item)
                print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 and not x['stopped'] for x in report['mutants']) and worlds == [45, 46, 47, 48, 49, 50, 98, 99]
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
