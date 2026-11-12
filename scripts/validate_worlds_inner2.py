#!/usr/bin/env python3
"""Strict original call comparison for Elbeland 51 and Swamp of Calmness 56 inline visuals.

Full RenderObjectVisual entry proves model/outer-RNG composition. A separate Elbeland 0x3a family starts at
0xe31358 with an authored prior stack colour, because the caller never initialises that local. Production
refuses that request. Engine leaves alone are stubbed; vector helpers and world guards run as instructions.
"""
import argparse
import ctypes as C
import json
import math
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_inner as inner
import validate_worlds_slots2 as w2
import validate_worlds_slots3 as w3

ROOT = Path(__file__).resolve().parents[1]
TYPES = {51: [0, 0x36, 0x3b, 0x3c, 0x3d, 0x3f, 0x6e, 0x79],
         56: [0x39, 0x47, 0x48, 0x4a, 0x4d, 0x4e, 0x63, 0x64, 0x65, 0x66, 0x67]}

class Machine(w2.Machine):
    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EBP
        self.stack_light = None
        def prior_stack(uc, address, size, context):
            if self.stack_light is not None:
                uc.mem_write(uc.reg_read(UC_X86_REG_EBP) - 0x10, v.pack_f(*self.stack_light))
        self.uc.hook_add(UC_HOOK_CODE, prior_stack, begin=0xe31358, end=0xe31358)

class Library:
    def __init__(self, path):
        self.dll = C.CDLL(str(path))
        self.dll.mu_later_world_inner.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_float, v.RAND_FN,
                                                 w2.BONE_FN, C.c_void_p, C.POINTER(C.c_float), C.POINTER(v.Log)]
        self.dll.mu_later_world_inner.restype = C.c_int


def compare(machine, lib, g, cases, world, focused=False, stack=False):
    tally = v.Tally('stack_light' if stack else 'world_%d%s' % (world, '_focus' if focused else ''))
    for n in range(cases):
        typ = 0x3a if stack else TYPES[world][n % len(TYPES[world])] if focused or n > 300 else n
        if typ == 0x3a and not stack: typ = 0x3b   # unwritten stack local has its own explicit-input family
        o = bytearray(w2.case_object(g, world, typ))
        v.put_i(o, 0x68, g.choice([-2, -1, 0, 3]))
        b = bytearray(0x100); v.put_f(b, 0x54, 0.25, 0.5, 0.75)
        time, seed = w2.case_time(g), g.randrange(2**32)
        present = stack or focused or n % 8 != 0
        if focused:
            modulus = 50 if world == 56 and typ >= 0x63 else 6 if world == 56 and typ in (0x48, 0x4d, 0x4e) else \
                      4 if typ == 0x36 else 2 if typ == 0x6e else 3
            if n % 2 == 0:
                for _ in range(10000):
                    r = v.MsvcRand(seed); r()  # outer
                    if r() % modulus == 0: break
                    seed = g.randrange(2**32)
        a, cb = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones = [], []
        def particle(m):
            x = [m.argument(k) for k in range(8)]
            assert x[6] in (0, v.OBJECTS) and x[7] == 0
            calls.append((inner.PARTICLE, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]),
                          *v.read_vec(m, x[3]), x[4], x[5], int(x[6] == v.OBJECTS)))
            return 0
        def sprite(m):
            x = [m.argument(k) for k in range(9)]
            assert x[4] == v.OBJECTS and x[5:8] == [0, 0, 4]
            assert bytes(m.uc.mem_read(x[8], 12)) == struct.pack('<IIf', 1, 1, 1.0)
            calls.append((inner.SPRITE, x[0], *v.read_vec(m, x[1]), x[2], *v.read_vec(m, x[3]), 0, 1, 0, 4))
            return 0
        def joint(m):
            x = [m.argument(k) for k in range(14)]
            assert x[5] == v.OBJECTS and x[7:] == [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]
            calls.append((inner.JOINT, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]),
                          x[4], 1, x[6]))
            return 0
        def transform(m):
            k = (m.argument(0) - 0x6fce398) // 48
            local = struct.unpack('<3f', bytes(m.uc.mem_read(m.argument(1), 12)))
            assert m.argument(3) == 0
            bones.append((k, *local))
            m.uc.mem_write(m.argument(2), v.pack_f(*inner.bone_point(k, local)))
            return 0, 16
        stubs = {w2.RAND: lambda m: a(), vp.MODEL_CONTAINER: lambda m: v.FAKE,
                 vp.MODEL_GET: lambda m: (v.MODEL if present else 0, 4),
                 vp.TRANSFORM_POSITION: transform, inner.PARTICLE: particle, inner.SPRITE: sprite,
                 inner.JOINT: joint, w2.STATIC_GET: lambda m: w2.STATIC,
                 w2.SINGLETON: lambda m: w2.SING, w2.MANAGER_GET: lambda m: w2.s2.REGISTRY,
                 w2.MANAGER: lambda m: (0, 8),
                 vp.SINE: lambda m: m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0))))),
                 vp.COSINE: lambda m: m.x87_return(v.f32(math.cos(v.from_bits(m.argument(0)))))}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                     am.defined_region('model', v.MODEL, bytes(b)),
                     am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                     am.defined_region('static', w2.STATIC, w2.static_region(machine)),
                     am.defined_region('singleton', w2.SING, w2.singleton(), writable=False),
                     am.defined_region('handler', w2.HANDLER, v.fake_object(), writable=False)])
        light = (C.c_float * 3)(g.uniform(-1, 2), g.uniform(-1, 2), g.uniform(-1, 2)) if stack else None
        machine.stack_light = tuple(light) if stack else None
        result = v.run(machine, 0xe3116a if stack else w3.VISUAL,
                       [v.OBJECTS, v.MODEL] if stack else [v.OBJECTS], regions, stubs)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'world': world, 'type': hex(typ)}, stop); continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE); log = v.new_log(); native_bones = []
        def bone(c, k, local, out):
            native_bones.append((k, *local[:3]))
            for q, value in enumerate(inner.bone_point(k, local[:3])): out[q] = value
        rnd, bone_fn = v.RAND_FN(lambda c: cb()), w2.BONE_FN(bone)
        if present:
            if not stack: cb()   # outer rand, already owned by the runtime
            lib.dll.mu_later_world_inner(co, 0, world, time, rnd, bone_fn, None, light, C.byref(log))
        native = [(call, *args) for call, index, *args in v.log_events(log)]
        ok = calls == native and bones == native_bones and a.seed == cb.seed and \
             result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == bytes(b)
        tally.count('type %#x' % typ); tally.count('calls', len(calls))
        tally.count('particles', sum(x[0] == inner.PARTICLE for x in calls))
        tally.count('sprites', sum(x[0] == inner.SPRITE for x in calls))
        tally.count('joints', sum(x[0] == inner.JOINT for x in calls))
        tally.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': calls[:6], 'native': native[:6],
                      'rng': a.seed == cb.seed, 'bones': (bones, native_bones),
                      'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE]})
    return tally

FAMILIES = {**{'world_%d' % w: lambda m,l,g,n,w=w: compare(m,l,g,n,w) for w in TYPES},
            **{'world_%d_focus' % w: lambda m,l,g,n,w=w: compare(m,l,g,n,w,True) for w in TYPES},
            'stack_light': lambda m,l,g,n: compare(m,l,g,n,51,stack=True)}
MUTATIONS = [
    ('Elbeland omitted', 'world != 51 && world != 56', 'world != 56', 'world_51_focus'),
    ('Swamp omitted', 'world != 51 && world != 56', 'world != 51', 'world_56_focus'),
    ('Elbeland roll 0', 'rnd(c) % 3 == 0) later_particle(o, i, 0x8016, 0', 'rnd(c) % 5 == 0) later_particle(o, i, 0x8016, 0', 'world_51_focus'),
    ('Elbeland roll 36', 'rnd(c) % 4', 'rnd(c) % 3', 'world_51_focus'),
    ('Elbeland kind 3b', '0x801c, 8', '0x801c, 7', 'world_51_focus'),
    ('Elbeland smoke count', 'k < 10', 'k < 9', 'world_51_focus'),
    ('Elbeland hidden gate', 'MU_OBJF_HIDDEN_MESH) != -2', 'MU_OBJF_HIDDEN_MESH) != -1', 'world_51_focus'),
    ('Elbeland hidden write', 'MU_OBJF_HIDDEN_MESH, -2', 'MU_OBJF_HIDDEN_MESH, -1', 'world_51_focus'),
    ('Elbeland smoke owner', 'p, light, scale, 1', 'p, light, scale, 0', 'world_51_focus'),
    ('Elbeland glow bone', 'bone(c, 5', 'bone(c, 4', 'world_51_focus'),
    ('Elbeland glow scale', 'scale * 6.0f', 'scale * 5.0f', 'world_51_focus'),
    ('Elbeland orbit RNG', 'rnd(c) % 2', 'rnd(c) % 3', 'world_51_focus'),
    ('Elbeland orbit z', '{0, 0, 70}', '{0, 0, 71}', 'world_51_focus'),
    ('Elbeland orbit radius', 'local[1] = csin(time * 0.03f)', 'local[1] = csin(time * 0.04f)', 'world_51_focus'),
    ('Elbeland six bones', 'k <= 8', 'k < 8', 'world_51_focus'),
    ('Elbeland local offset', '{5, -4, -1}', '{5, -3, -1}', 'world_51_focus'),
    ('Elbeland pulse', 'csin(time * 0.002f)', 'csin(time * 0.003f)', 'world_51_focus'),
    ('Elbeland prior stack colour', 'p, stack_light, 1.0f', 'p, white, 1.0f', 'stack_light'),
    ('Swamp paired flame', '0x8016, 5, p, white, scale, 0, l);\n                later_particle', '0x8016, 4, p, white, scale, 0, l);\n                later_particle', 'world_56_focus'),
    ('Swamp raised smoke', 'p[2] += 50.0f', 'p[2] += 40.0f', 'world_56_focus'),
    ('Swamp double scale', 'scale * 2.0f', 'scale * 3.0f', 'world_56_focus'),
    ('Swamp smoke colour', '0.04f : 0.03f', '0.05f : 0.03f', 'world_56_focus'),
    ('Swamp joint RNG', 'rnd(c) % 50', 'rnd(c) % 49', 'world_56_focus'),
    ('Swamp joint kind', '{0x7f7d}', '{0x7f7c}', 'world_56_focus'),
    ('Swamp joint subtype', 't == 0x66 ? 24 : 25', 't == 0x66 ? 23 : 25', 'world_56_focus'),
    ('Swamp joint owner', 'a[11] = 1', 'a[11] = 0', 'world_56_focus'),
    ('Swamp light write', 'MU_OBJF_LIGHT + 4, 0.65f', 'MU_OBJF_LIGHT + 4, 0.6f', 'world_56_focus'),
]

def build(root):
    subprocess.run(['make', '-s', '-j4', '-C', str(root / 'objects')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000); p.add_argument('--only'); p.add_argument('--mutations', action='store_true')
    p.add_argument('--text', default=v.pins.TEXT.default_str()); p.add_argument('--data', default=v.pins.DATA.default_str())
    p.add_argument('--output'); a = p.parse_args()
    machine = Machine(am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text'),
                         am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data'))
    names = a.only.split(',') if a.only else list(FAMILIES)
    seed = lambda name: random.Random(0x512e + list(FAMILIES).index(name))
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    for name in names:
        row = FAMILIES[name](machine, lib, seed(name), a.cases).report(); report['families'][name] = row
        print(name, json.dumps({k: val for k, val in row.items() if k != 'coverage'})[:5000], flush=True)
    if a.mutations:
        for label, old, new, family in MUTATIONS:
            if family not in names: continue
            with tempfile.TemporaryDirectory(prefix='worlds-inner2-mut-') as td:
                root = Path(td)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects/world_inner2_visual.c'; s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                assert len(re.findall(pattern, s)) == 1, label
                path.write_text(re.sub(pattern, lambda m: new, s, count=1))
                t = FAMILIES[family](machine, build(root), seed(family), a.cases)
                row = {'name': label, 'cases': t.cases, 'detected': t.cases - t.equal - t.stopped, 'stopped': t.stopped}
                report['mutants'].append(row); print(row, flush=True)
    report['ok'] = all(r['mismatch_count'] == 0 and r['stopped'] == 0 for r in report['families'].values()) and \
                   all(r['detected'] > 0 for r in report['mutants'])
    if a.output: Path(a.output).write_text(json.dumps(report, indent=1))
    return 0 if report['ok'] else 1

if __name__ == '__main__': sys.exit(main())
