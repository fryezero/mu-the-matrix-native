#!/usr/bin/env python3
"""RENDER-WORLDS-G3: RenderObject for the environment objects (Atlans fish blend mesh) against the client.

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  object_init  ObjectInit 0x0129eb81 up to its first call 0x0129ee24 on a poisoned object: the start state of
               the bytes the environment module never writes (+0x03 shadow, +0x80 render mode, +0xac/+0xb0 blend
               texture offsets) equals the constants mu_env_render_body uses; +0x68/+0x74/+0xa8 start at 0.
  env_render   RenderObject 0x016d4fe4(o, 0, 0, 0, -1, -1) on an environment object image (zero bytes, as the
               static boid/fish arrays start (inference), ObjectInit's head over them, then the C object's modelled fields at their client offsets) in the boid/fish worlds, the
               Chaos Castle worlds and others: whether RenderBody 0x00966def is called, its eight arguments and
               the object bytes afterwards (the setup's Chaos Castle alpha step) against mu_env_render_body.
               The custom render 0x017f76ec and the render registry are stubbed to "not taken" (see below).
  abyss_fish   the Abyss of Atlans class slots 0x38 (custom render) and 0x3c (after) of classes 128..130 for
               the fish/boid model types 0x196..0x1a0 and 0x1b3: answer, calls and object bytes against the C
               (reconstructed/objects/world_abyss_visual.c), so the class slot that ends 0x017f76ec's chain does
               not take them.

Static (reported, not executed): 0x017f76ec..0x017f9758 contains no compare against 0x196..0x1a0 or 0x1b3.

Usage: scripts/validate_worlds_g3.py [--cases N] [--only a,b] [--mutations] [--output report.json]
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import actor_machine as am  # noqa: E402
import validate_object_render as v  # noqa: E402
import validate_particles as vp  # noqa: E402
import validate_worlds_after as wa  # noqa: E402

OBJECT_INIT, OBJECT_INIT_FIRST_CALL = 0x0129eb81, 0x0129ee24
CUSTOM_RENDER = (0x017f76ec, 0x017f9758)
BODIES = {'object_init_head': (0x0129eb81, 0x0129ee24), 'render_object': (0x016d4fe4, 0x016d5020),
          'render_object_setup': (0x017ec896, 0x017edd1d), 'render_object_draw': (0x017edf43, 0x017ee292),
          'custom_render': CUSTOM_RENDER}
FISH_TYPES = [0x196, 0x197, 0x198, 0x199, 0x19a, 0x19b, 0x19c, 0x19d, 0x19e, 0x19f, 0x1a0, 0x1b3]
CHAOS = [0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x35, 0x61]
WORLDS = [7, 0x80, 0x81, 0x82, 7, 0x80, 0x81, 0x82, 0, 1, 3, 4, 6, 8, 10, 0x21, 0x33, 0x74, 0x85, 0x86] + CHAOS
OBJ = 0x3d8
ENV_BYTES = 4096   # larger than mu_env_object; the C reads and writes only modelled fields


class EnvLib:
    def __init__(self, path):
        d = self.dll = C.CDLL(str(path))
        d.mu_env_render_body.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.POINTER(C.c_uint32)]
        d.mu_env_render_body.restype = C.c_int
        d.mu_env_object_load.argtypes = [C.c_void_p, C.c_char_p]
        d.mu_env_object_store.argtypes = [C.c_void_p, C.c_void_p]
        d.mu_env_object_mask.argtypes = [C.c_void_p]

    def mask(self):
        m = C.create_string_buffer(OBJ)
        self.dll.mu_env_object_mask(m)
        return m.raw[:OBJ]


def object_init_image(machine, g, zero=False):
    """ObjectInit's stores before its first call, over a poisoned object (or the zero bytes of a static array)."""
    o = bytes(OBJ) if zero else bytes(v.poison_object(g))
    regions = v.global_regions(0, 6, [am.defined_region('object', v.OBJECTS, o)])
    r = v.run(machine, OBJECT_INIT, [], regions, {}, ecx=v.OBJECTS, until=OBJECT_INIT_FIRST_CALL)
    return r, o


def family_object_init(machine, envlib, g, cases):
    t = v.Tally('object_init')
    for n in range(cases):
        r, o = object_init_image(machine, g)
        stop = v.stopped_reason(r)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        # mu_env_render_body: flags 2 (+0x80 != 0x80), U = V = 0.0f, no shadow block (+0x03 == 0); the C's U/V
        # are the client's start values only if ObjectInit leaves them at 0 (the module never writes them)
        out = bytearray(r['regions']['object'])
        struct.pack_into('<f', out, 0xdc, 1.0)
        env = C.create_string_buffer(ENV_BYTES)
        envlib.dll.mu_env_object_load(env, bytes(out))
        args = (C.c_uint32 * 8)()
        drawn = envlib.dll.mu_env_render_body(env, 7, 0, args)
        ok = (out[3] == 0 and struct.unpack_from('<i', out, 0x80)[0] != 0x80 and drawn == 1 and
              args[0] == 2 and out[0xac:0xb0] == struct.pack('<I', args[4]) and
              out[0xb0:0xb4] == struct.pack('<I', args[5]) and
              struct.unpack_from('<i', out, 0x68)[0] == 0 and struct.unpack_from('<i', out, 0x74)[0] == 0 and
              out[0xa8:0xac] == bytes(4))
        t.count('start +0x80 %#x' % struct.unpack_from('<i', out, 0x80)[0])
        t.add(ok, {'case': n, 'shadow': out[3], 'mode': out[0x80:0x84].hex(), 'uv': out[0xac:0xb4].hex(),
                   'args': list(args)})
    return t


def env_object(g, start):
    """An environment object image: ObjectInit's start state, then modelled fields as the creators write them."""
    o = bytearray(start)
    typ = g.choice(FISH_TYPES + [g.randrange(0, 0x800), 0x7c4, 0x1a3, 0x1a4, -1])
    struct.pack_into('<i', o, 0x5c, typ)
    o[0] = 1
    o[5] = g.choice([0, 1])
    o[0xc] = g.choice([0, 1])
    struct.pack_into('<i', o, 0x68, g.choice([-1, -1, -1, -2, 0, 1, g.randrange(-2**31, 2**31)]))
    struct.pack_into('<i', o, 0x74, g.choice([-1, -1, 0, 0, 1, 2, g.randrange(-2**31, 2**31)]))
    struct.pack_into('<f', o, 0xa8, am.f32(g.choice([1.0, 0.5, 0.9, 0.1, 0.0, g.uniform(-1, 2)])))
    struct.pack_into('<f', o, 0xdc, am.f32(g.choice([1.0, 0.0, 0.01, 0.009999, 0.16, 0.15, 0.1600001,
                                                       g.uniform(0, 1), g.uniform(-1, 2)])))
    struct.pack_into('<f', o, 0xd8, am.f32(g.uniform(0, 1)))
    struct.pack_into('<f', o, 0xbc, am.f32(g.uniform(0.1, 3)))
    struct.pack_into('<f', o, 0xa0, am.f32(g.uniform(0.4, 1.4)))
    struct.pack_into('<3f', o, 0x158, *(am.f32(g.uniform(0, 25600)) for _ in range(3)))
    struct.pack_into('<3f', o, 0x164, *(am.f32(g.uniform(0, 360)) for _ in range(3)))
    struct.pack_into('<3f', o, 0xec, *(am.f32(g.uniform(0, 1)) for _ in range(3)))
    struct.pack_into('<2f', o, 0xd0, am.f32(g.uniform(0, 20)), am.f32(g.uniform(0, 20)))
    struct.pack_into('<H', o, 0x2a, g.choice([0, 0, 1, 2]))
    return bytes(o)


def family_env_render(machine, envlib, g, cases):
    t = v.Tally('env_render')
    grids = (v.light_grid(g), v.light_grid(g))
    for n in range(cases):
        r, _ = object_init_image(machine, g, zero=True)
        stop = v.stopped_reason(r)
        if stop:
            t.add(False, {'case': n, 'step': 'object_init'}, stop)
            continue
        o = env_object(g, r['regions']['object'])
        world = g.choice(WORLDS)
        chaos_flag = g.choice([0, 1, 1, 2])
        time = am.f32(g.uniform(0, 3e7))
        model = bytes(g.getrandbits(8) for _ in range(0x100))
        bodies = []

        def body(m):
            bodies.append(tuple(m.argument(i) for i in range(8)))
            return (0, 0x20)

        stubs = {0x00966cc4: lambda m: v.FAKE, 0x00eaa8cf: lambda m: (v.MODEL, 4),
                 0x012b5064: lambda m: (0, 0x20), 0x0129f11a: lambda m: v.BONES, 0x00966ea5: lambda m: (0, 0x24),
                 0x017f9375: lambda m: 0, 0x017f76ec: lambda m: 0,
                 0x00a170f2: lambda m: (m.argument(0), 4), 0x00a1711c: lambda m: (m.argument(0), 8),
                 0x01807a11: lambda m: (0, 4), 0x00a16bc0: lambda m: (v.FAKE + 0x10, 4),
                 0x00966def: body, 0x017f919e: lambda m: 0, 0x012bc07a: lambda m: (0, 0x14),
                 0x0184a990: lambda m: 0, 0x009a6ef3: lambda m: v.FAKE, 0x009a645f: lambda m: 0,
                 0x0103ec05: lambda m: 0, 0x016a88ae: lambda m: 0, 0x017f746f: lambda m: 0}
        hero = bytearray(0x3300)
        hero[0x325c] = chaos_flag
        regions = v.global_regions(world, 6, [
            am.defined_region('frame-light', v.FRAME_LIGHT, grids[0], writable=False),
            am.defined_region('primary-light', v.PRIMARY_LIGHT, grids[1], writable=False),
            am.defined_region('terrain-ready', v.TERRAIN_READY, b'\1', writable=False),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('bounds', v.BOUNDS, struct.pack('<i', 0), writable=False),
            am.defined_region('hero-pointer', v.HERO_PTR, struct.pack('<I', v.HERO), writable=False),
            am.defined_region('hero', v.HERO, bytes(hero), writable=False),
            am.undefined_region('bone-scale', 0x01cf104c, 4),
            am.defined_region('object', v.OBJECTS, o),
            am.defined_region('model', v.MODEL, model),
            am.defined_region('fake', v.FAKE, v.fake_object(), writable=False),
            am.undefined_region('gl-color', 0x41030000, 16)])
        result = v.run(machine, v.RENDER, [v.OBJECTS, 0, 0, 0, 0xffffffff, 0xffffffff], regions, stubs)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': struct.unpack_from('<i', o, 0x5c)[0]}, stop)
            continue
        env = C.create_string_buffer(ENV_BYTES)
        envlib.dll.mu_env_object_load(env, o)
        args = (C.c_uint32 * 8)()
        drawn = envlib.dll.mu_env_render_body(env, world, chaos_flag, args)
        stored = C.create_string_buffer(o, OBJ)
        envlib.dll.mu_env_object_store(env, stored)
        mask = envlib.mask()
        client_obj = result['regions']['object']
        same_fields = all(client_obj[k] == stored.raw[k] for k in range(OBJ) if mask[k])
        c_bodies = [tuple(args)] if drawn else []
        t.count('drawn' if bodies else 'skipped')
        t.count('blend mesh 0' if bodies and bodies[0][2] == 0 else 'other')
        if world in CHAOS and chaos_flag == 1:
            t.count('chaos step')
        t.add(bodies == c_bodies and same_fields,
              {'case': n, 'world': world, 'flag': chaos_flag, 'type': struct.unpack_from('<i', o, 0x5c)[0],
               'client': [list(map(hex, b)) for b in bodies], 'c': [list(map(hex, b)) for b in c_bodies],
               'fields': same_fields})
    return t


def family_abyss_fish(machine, objlib, g, cases):
    saved = wa.ABYSS_TYPES
    wa.ABYSS_TYPES = FISH_TYPES
    try:
        a = wa.abyss_family(machine, objlib, g, (cases + 1) // 2, False)
        b = wa.abyss_family(machine, objlib, g, cases // 2, True)
    finally:
        wa.ABYSS_TYPES = saved
    t = v.Tally('abyss_fish')
    for x in (a, b):
        t.cases += x.cases
        t.equal += x.equal
        t.stopped += x.stopped
        t.mismatches += x.mismatches[:4]
        for k, c in x.cover.items():
            t.count(('after ' if x is b else 'custom ') + k, c)
    return t


def static_custom_render(text):
    lo, hi = CUSTOM_RENDER
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    hits = []
    for ins in md.disasm(text[lo - am.TEXT_BASE:hi - am.TEXT_BASE], lo):
        if ins.mnemonic == 'cmp' and re.search(r', 0x(19[6-9a-f]|1a0|1b3)$', ins.op_str):
            hits.append(f'{ins.address:#x} {ins.op_str}')
    return {'range': [hex(lo), hex(hi)], 'fish_type_compares': hits}


FAMILIES = {'object_init': ('env', family_object_init), 'env_render': ('env', family_env_render),
            'abyss_fish': ('obj', family_abyss_fish)}

# (label, file, old, new, family): planted mistakes in the compiled C
MUTATIONS = [
    ('alpha test bound', 'env_body.c', 'if (0.01f > o->alpha)', 'if (0.0f > o->alpha)', 'env_render'),
    ('alpha test inclusive', 'env_body.c', 'if (0.01f > o->alpha)', 'if (0.01f >= o->alpha)', 'env_render'),
    ('hidden -2 kept', 'env_body.c', 'if (o->field_68 == -2)', 'if (o->field_68 == -3)', 'env_render'),
    ('chaos step size', 'env_body.c', 'o->alpha - 0.15f', 'o->alpha - 0.1f', 'env_render'),
    ('chaos flag test', 'env_body.c', 'chaos_hero_flag == 1', 'chaos_hero_flag != 0', 'env_render'),
    ('chaos step ignored', 'env_body.c', 'o->alpha = o->alpha - 0.15f;', '(void)0;', 'env_render'),
    ('flags 0x82', 'env_body.c', 'args[0] = 2;', 'args[0] = 0x82;', 'object_init'),
    ('blend mesh dropped', 'env_body.c', 'args[2] = (uint32_t)o->field_74;', 'args[2] = 0xffffffffu;',
     'env_render'),
    ('blend light = alpha', 'env_body.c', 'args[3] = f32_bits(o->field_a8);', 'args[3] = f32_bits(o->alpha);',
     'env_render'),
    ('blend U one', 'env_body.c', 'args[4] = 0;', 'args[4] = 0x3f800000u;', 'object_init'),
    ('hidden mesh dropped', 'env_body.c', 'args[6] = (uint32_t)o->field_68;', 'args[6] = 0xffffffffu;',
     'env_render'),
    ('last argument', 'env_body.c', 'args[7] = 0xffffffffu;', 'args[7] = 0;', 'env_render'),
]


def build_env(root):
    subprocess.run(['make', '-s', '-C', str(root / 'environment')], check=True)
    return EnvLib(root / 'environment' / ('libclient_env.' + v.SUFFIX))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--only')
    p.add_argument('--text', default=v.pins.TEXT.default_str())
    p.add_argument('--data', default=v.pins.DATA.default_str())
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text = am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = vp.PtMachine(text, data)
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': [],
              'static': static_custom_render(text),
              'bodies': {k: {'start': hex(b), 'end': hex(e),
                             'sha256': hashlib.sha256(text[b - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for k, (b, e) in BODIES.items()}}
    print('static', json.dumps(report['static']), flush=True)
    seed = lambda name: random.Random(0x9e3 + list(FAMILIES).index(name))
    with tempfile.TemporaryDirectory(prefix='worlds-g3-') as tmp:
        wa.FRAME_LIB = wa.build_frame(tmp)
        libs = {'env': build_env(ROOT / 'reconstructed')}
        if any(FAMILIES[n][0] == 'obj' for n in names):
            libs['obj'] = wa.build(ROOT / 'reconstructed')
        for name in names:
            kind, fn = FAMILIES[name]
            tally = fn(machine, libs[kind], seed(name), a.cases)
            report['families'][name] = tally.report()
            print(name, json.dumps(tally.report())[:2000], flush=True)
        if a.mutations:
            for label, file, old, new, family in MUTATIONS:
                if family not in names:
                    continue
                with tempfile.TemporaryDirectory(prefix='worlds-g3-mut-') as mtmp:
                    root = Path(mtmp)
                    for d in ['environment', 'record-math']:
                        shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                        ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                    if (ROOT / 'reconstructed/deps.mk').exists():
                        shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                    path = root / 'environment' / file
                    s = path.read_text()
                    assert s.count(old) == 1, (label, old)
                    path.write_text(s.replace(old, new))
                    tally = FAMILIES[family][1](machine, build_env(root), seed(family), a.cases)
                    item = {'name': label, 'family': family, 'cases': tally.cases,
                            'detected': tally.cases - tally.equal - tally.stopped, 'stopped': tally.stopped}
                    report['mutants'].append(item)
                    print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 and x['stopped'] == 0 for x in report['mutants']) and \
        not report['static']['fish_type_compares']
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
