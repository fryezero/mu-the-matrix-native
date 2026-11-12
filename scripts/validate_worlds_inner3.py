#!/usr/bin/env python3
"""Compare complete Aida and Kanturu Remain inline calls, RNG, bones, writes and model state with original instructions."""
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
import validate_worlds_slots2 as w2
import validate_worlds_slots3 as w3

ROOT = Path(__file__).resolve().parents[1]
AIDA, REMAIN, TRIALS = 0xd622dd, 0xe7df87, 0xdfc095
ALPHA, PUSH, POP = 0x1a7c6d0, 0x12b7e53, 0x12b7e65
BODY, MESH, PARTICLE, SPRITE, EFFECT, JOINT = 0x966def, 0x966e4a, 0x168fafd, 0x1692eb7, 0x13c0eaa, 0x153b02c
NAMES = ['Box07','Box08','Box09','Box13','Box14','Box18','Bone01','Bip01 R UpperArm','Bip01 L UpperArm']
RTYPES = [4,8,0xa,0x2d,0x2e,0x2f,0x30,0x31,0x32,0x34,0x35,0x36,0x37,0x38,0x41]
TYPES = [0x1e,0x38,0x39,0x3a,0x3b,0x3c,0x3e,0x3f,0x41,0x42,0x43,0x46,0x47,0x4b,0x4d,0x4e]

class Machine(w2.Machine):
    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_ALL
        self.imports = {}
        for slot in (ALPHA, 0x1a7c9a4):
            target = struct.unpack_from('<I', data, slot - am.DATA_BASE)[0]
            self.imports[slot] = target
            page = target & ~0xfff
            if not any(a <= target <= b for a, b, _ in self.uc.mem_regions()):
                self.uc.mem_map(page, 0x1000, UC_PROT_ALL)
                self.uc.mem_write(page, b'\xc3' * 0x1000)

class Library:
    def __init__(self, path):
        self.dll = C.CDLL(str(path))
        d, P, I, F, L = self.dll, C.c_void_p, C.c_int32, C.c_float, C.POINTER(v.Log)
        d.mu_aida_inner.argtypes = [P, P, I, I, F, C.c_uint32, v.RAND_FN, w3.NAMED_FN, P, L]
        d.mu_aida_inner.restype = C.c_int
        d.mu_kanturu_remain_inner.argtypes = [P, I, I, F, v.RAND_FN, w2.BONE_FN, P, L]
        d.mu_kanturu_remain_inner.restype = C.c_int
        d.mu_trials_inner.argtypes = [P, I, I, F, v.RAND_FN, w2.BONE_FN, P, L]
        d.mu_trials_inner.restype = C.c_int
        d.mu_devil_square_inner.argtypes = [P,I,I,v.RAND_FN,w3.NAMED_FN,P,L]
        d.mu_devil_square_inner.restype = C.c_int


def bone_point(k, local):
    return tuple(v.f32(local[q] + (k + 1) * (q + 2) * 7.25) for q in range(3))


def compare(machine, lib, g, cases, focused=False, remain=False, trials=False, devil=False):
    t = v.Tally(('devil' if devil else 'trials' if trials else 'remain' if remain else 'aida') + ('_focus' if focused else ''))
    for n in range(cases):
        world = [33,54][n % 2] if focused else g.choice([33,54,33,54,0,31,38])
        if remain: world = 38 if focused else g.choice([38,38,38,0,33,37,39])
        if trials: world = 31 if focused else g.choice([31,31,31,0,33,38])
        if devil: world = 9
        types = [2] if devil else [3,0x31,0x35] if trials else RTYPES if remain else TYPES
        typ = types[n % len(types)] if focused or n > 300 else n
        o = bytearray(w2.case_object(g, world, typ))
        v.put_i(o, 0x68, g.choice([-2, -1, 0, 3]))
        b = bytearray(0x100); b[0x94] = g.choice([0, 1, 0xff]); v.put_f(b, 0x54, 0.25, 0.5, 0.75)
        present = not devil or focused or n % 8 != 0
        time = w2.case_time(g)
        clock = g.choice([0, 1, 9, 10, 29, 30, 1023, 1024, 1025, 1033, 1034, 0xffffffff, g.randrange(2**32)])
        if focused and not remain and not trials and not devil and typ in (0x3c,0x46):
            clock = [0,1,9,10,29,30,1023,1024,1033,1034][(n // len(TYPES)) % 10]
        seed = g.randrange(2**32)
        if focused and remain and n % 2 == 0:
            for _ in range(10000):
                r = v.MsvcRand(seed)
                if typ == 8:
                    for _ in range(4): r()
                modulus = 20 if typ in (8,0x36) else 10 if typ in (0x38,0x41) else 5 if typ == 0x37 else 6 if typ in (0xa,0x34) else 3
                if r() % modulus == 0: break
                seed = g.randrange(2**32)
        if focused and not remain and not trials and not devil and typ == 0x46:
            for _ in range(10000):
                if v.MsvcRand(seed)() % 5 == 1: break
                seed = g.randrange(2**32)
        a, cb = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones, clock_calls = [], [], [0]
        heap = [w3.HEAP]
        def allocate(m):
            at = heap[0]; heap[0] += max(16, (m.argument(0) + 15) & ~15); return at
        def clock_get(m):
            clock_calls[0] += 1; return clock
        def named(m):
            at = m.argument(0)
            size, cap = struct.unpack('<II', bytes(m.uc.mem_read(at + 16, 8)))
            ptr = at if cap < 16 else m.read32(at)
            text = bytes(m.uc.mem_read(ptr, size)).decode('ascii')
            bones.append(('name', text))
            return 0x6fce398 + 48 * NAMES.index(text), 8
        def transform(m):
            k = (m.argument(0) - 0x6fce398) // 48
            local = struct.unpack('<3f', bytes(m.uc.mem_read(m.argument(1), 12)))
            assert m.argument(3) == 0
            bones.append(('bone', k, *local))
            m.uc.mem_write(m.argument(2), v.pack_f(*bone_point(k, local)))
            return 0, 16
        def particle(m):
            x = [m.argument(k) for k in range(8)]
            assert x[6] in (0, v.OBJECTS) and x[7] == 0
            calls.append((PARTICLE, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]),
                          x[4], x[5], int(x[6] == v.OBJECTS)))
            return 0
        def sprite(m):
            x = [m.argument(k) for k in range(9)]
            assert x[4] in (0,v.OBJECTS) and x[6:8] == [0,4]
            assert bytes(m.uc.mem_read(x[8], 12)) == struct.pack('<IIf', 1, 1, 1.0)
            calls.append((SPRITE, x[0], *v.read_vec(m, x[1]), x[2], *v.read_vec(m, x[3]), x[5], int(x[4] == v.OBJECTS), x[6], x[7]))
            return 0
        def effect(m):
            x = [m.argument(k) for k in range(14)]
            assert x[5] == v.OBJECTS and x[6:8] == [0xffffffff, 0] and x[9:] == [0, 0, 0xffffffff, 0, 0], x
            calls.append((EFFECT, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]), x[4], 1, *([x[8]] if x[0] == 0x199 else [])))
            return 0
        def joint(m):
            x = [m.argument(k) for k in range(14)]
            assert x[5] == 0 and x[7:] == [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0], x
            calls.append((JOINT, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]),
                          x[4], 0, x[6]))
            return 0
        def mesh(m):
            calls.append((MESH, *(m.argument(k) for k in range(8)), bytes(m.uc.mem_read(v.MODEL + 0x94, 1))[0]))
            return 0, 32
        def push(m):
            calls.append((PUSH, m.argument(0))); return 0, 4
        def pop(m):
            calls.append((POP,)); return 0
        def alpha(m):
            calls.append((ALPHA, m.argument(0), m.argument(1))); return 0, 8
        stubs = {w2.RAND: lambda m: a(), vp.MODEL_CONTAINER: lambda m: v.FAKE,
                 vp.MODEL_GET: lambda m: (v.MODEL if present else 0, 4),
                 vp.BONE_MATRIX: named, vp.TRANSFORM_POSITION: transform, vp.CRT_MALLOC: allocate,
                 vp.CRT_FREE: lambda m: 0, PARTICLE: particle, SPRITE: sprite, EFFECT: effect, JOINT: joint,
                 MESH: mesh, PUSH: push, POP: pop,
                 machine.imports[ALPHA]: alpha, machine.imports[0x1a7c9a4]: clock_get,
                 w2.STATIC_GET: lambda m: w2.STATIC, w2.SINGLETON: lambda m: w2.SING,
                 w2.MANAGER_GET: lambda m: w2.s2.REGISTRY, w2.MANAGER: lambda m: (0,8),
                 vp.SINE: lambda m: m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0)))))}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                     am.defined_region('model', v.MODEL, bytes(b)),
                     am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                     am.defined_region('heap', w3.HEAP, bytes(0x10000)),
                     am.defined_region('static',w2.STATIC,w2.static_region(machine)),
                     am.defined_region('singleton',w2.SING,w2.singleton(),writable=False),
                     am.defined_region('handler',w2.HANDLER,v.fake_object(),writable=False)])
        result = v.run(machine, w3.VISUAL if devil else TRIALS if trials else REMAIN if remain else AIDA, [v.OBJECTS] if devil else [v.OBJECTS, v.MODEL], regions, stubs)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': hex(typ)}, stop); continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE); model = C.create_string_buffer(bytes(b), 0x100)
        log = v.new_log(); native_bones = []
        def bone(c, k, local, out):
            native_bones.append(('bone', k, *local[:3]))
            for q, value in enumerate(bone_point(k, local[:3])): out[q] = value
        def named_bone(c, text, local, out):
            text = text.decode('ascii'); native_bones.append(('name', text))
            bone(c, NAMES.index(text), local, out)
        rnd, bone_fn, named_fn = v.RAND_FN(lambda c: cb()), w2.BONE_FN(bone), w3.NAMED_FN(named_bone)
        if devil:
            answer = 1
            if present:
                cb()
                lib.dll.mu_devil_square_inner(co,0,world,rnd,named_fn,None,C.byref(log))
        elif trials:
            answer = lib.dll.mu_trials_inner(co, 0, world, time, rnd, bone_fn, None, C.byref(log))
        elif remain:
            answer = lib.dll.mu_kanturu_remain_inner(co, 0, world, time, rnd, bone_fn, None, C.byref(log))
        else:
            answer = lib.dll.mu_aida_inner(co, model, 0, world, time, clock, rnd, named_fn, None, C.byref(log))
        native, stream = [], b[0x94]
        for e in v.log_events(log):
            call, _, *args = e
            if call == 0x17ffef3: stream = args[0] & 0xff
            elif call == MESH: native.append((call, *args, stream))
            else: native.append((EFFECT if call == 0x00e68c23 else call, *args))
        ok = calls == native and bones == native_bones and a.seed == cb.seed and \
            result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == model.raw[:0x100]
        ok = ok and (devil or (result['eax'] & 0xff) == answer) and clock_calls[0] == int(not remain and not trials and not devil and world in (33,54) and typ in (0x3c,0x46))
        t.count('world %d type %#x' % (world, typ)); t.count('draw/request calls', len(calls))
        for call in (PARTICLE, SPRITE, EFFECT, JOINT, MESH): t.count(hex(call), sum(x[0] == call for x in calls))
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': calls[:4], 'native': native[:4],
                  'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                  'model': result['regions']['model'] == model.raw[:0x100], 'rng': a.seed == cb.seed,
                  'bones': (bones[:8], native_bones[:8])})
    return t

FAMILIES = {'aida': lambda m,l,g,n: compare(m,l,g,n), 'aida_focus': lambda m,l,g,n: compare(m,l,g,n,True),
            'remain': lambda m,l,g,n: compare(m,l,g,n,False,True), 'remain_focus': lambda m,l,g,n: compare(m,l,g,n,True,True),
            'trials': lambda m,l,g,n: compare(m,l,g,n,False,False,True), 'trials_focus': lambda m,l,g,n: compare(m,l,g,n,True,False,True),
            'devil': lambda m,l,g,n: compare(m,l,g,n,False,False,False,True),
            'devil_focus': lambda m,l,g,n: compare(m,l,g,n,True,False,False,True)}
MUTATIONS = [
    ('Aida world54', 'world != 33 && world != 54', 'world != 33', 'aida'),
    ('Aida Box18', '"Box18"', '"Box14"', 'aida_focus'),
    ('Aida blue large scale', '{5.5f,4.5f,4,4.5f,4,4}', '{5.5f,4.5f,4,4.5f,4,5}', 'aida_focus'),
    ('Aida red scale', '{6,5.5f,5,5.5f,5,5}', '{6,5.5f,5,5.5f,5,6}', 'aida_focus'),
    ('Aida bone offset', '{0,2,-8}', '{0,2,-7}', 'aida_focus'),
    ('Aida blue colour', '{0.1f,0.1f,0.3f}', '{0.1f,0.1f,0.4f}', 'aida_focus'),
    ('Aida small colour', '{0.15f,0.15f,0.15f}', '{0.15f,0.15f,0.25f}', 'aida_focus'),
    ('Aida red first colour', 'k == 0 ? 0.5f : 0.25f', 'k == 0 ? 0.4f : 0.25f', 'aida_focus'),
    ('Aida type38 gate', 'rnd(c) % 2 == 0', 'rnd(c) % 3 == 0', 'aida_focus'),
    ('Aida type39 pair', '0x801c, 4, white', '0x801c, 5, white', 'aida_focus'),
    ('Aida type3a gate', 'rnd(c) % 3 == 0) aida_particle(o, i, 0x801b', 'rnd(c) % 4 == 0) aida_particle(o, i, 0x801b', 'aida_focus'),
    ('Aida smoke gate', 'if (H(&s) != -2)', 'if (H(&s) != -1)', 'aida_focus'),
    ('Aida smoke colour', 't == 0x3b ? 0.01f : 0.05f', 't == 0x3b ? 0.02f : 0.05f', 'aida_focus'),
    ('Aida smoke count', 'k < 20; ++k) aida_particle', 'k < 19; ++k) aida_particle', 'aida_focus'),
    ('Aida smoke owner', '0x7f89, 26, light, 1', '0x7f89, 26, light, 0', 'aida_focus'),
    ('Aida clock window', 'clock % 1024u < 10u', 'clock % 1024u < 9u', 'aida_focus'),
    ('Aida hidden write', 'set_hidden(&s, -2)', 'set_hidden(&s, -1)', 'aida_focus'),
    ('Aida scrolling sign', '0.0002f, t <= 0x42', '0.0002f, 0', 'aida_focus'),
    ('Aida scrolling period', 'tmod(&s, 100000', 'tmod(&s, 99999', 'aida_focus'),
    ('Aida stream restore', 'stream(&s, 0xff)', 'stream(&s, 0xfe)', 'aida_focus'),
    ('Aida light write', 'MU_OBJF_LIGHT + 4 * k, light[k]', 'MU_OBJF_LIGHT + 4 * k, 0.4f', 'aida_focus'),
    ('Aida keyed gate', 'rnd(c) % 5 == 1', 'rnd(c) % 5 == 0', 'aida_focus'),
    ('Aida keyed clock', 'clock % 1024u < 30u', 'clock % 1024u < 29u', 'aida_focus'),
    ('Aida word4', '(uint16_t)(uint32_t)cvtt(mu_obj_f32(o, MU_OBJF_SCALE))', '(uint16_t)(uint32_t)(cvtt(mu_obj_f32(o, MU_OBJF_SCALE)) + 1)', 'aida_focus'),
    ('Aida rotation', 'white, time / 10.0f', 'white, time / 11.0f', 'aida_focus'),
    ('Remain guard', 'world != 38', 'world != 37', 'remain_focus'),
    ('Remain glow bone', 'bone(c, 1, local, p)', 'bone(c, 2, local, p)', 'remain_focus'),
    ('Remain glow double divisor', '(double)pulse / 3.2', '(double)pulse / 3.0', 'remain_focus'),
    ('Remain repeated sprite', 'aida_sprite(i, 0x802b, p, scale, light, 0, l);\n            aida_sprite', 'aida_sprite(i, 0x7ef7, p, scale, light, 0, l);\n            aida_sprite', 'remain_focus'),
    ('Remain pulse', 'csin(time * 0.001f)', 'csin(time * 0.002f)', 'remain_focus'),
    ('Remain endpoint RNG', 'rnd(c) % 100', 'rnd(c) % 80', 'remain_focus'),
    ('Remain joint gate', 'rnd(c) % 20 == 0 && bone', 'rnd(c) % 19 == 0 && bone', 'remain_focus'),
    ('Remain joint subtype', '0x7f7c, 18, a, b, 40', '0x7f7c, 8, a, b, 40', 'remain_focus'),
    ('Remain raised particle', 'p[2] = 410', 'p[2] = 400', 'remain_focus'),
    ('Remain smoke count', 't == 0x31 ? 5 : 20', 't == 0x31 ? 4 : 20', 'remain_focus'),
    ('Remain smoke gate', 'MU_OBJF_HIDDEN_MESH) != -2', 'MU_OBJF_HIDDEN_MESH) != -1', 'remain_focus'),
    ('Remain smoke blue RNG', 'rnd(c) % 3) * 0.01f + 0.02f', 'rnd(c) % 4) * 0.01f + 0.02f', 'remain_focus'),
    ('Remain particle pair', '0x802a, 1, p', '0x802a, 2, p', 'remain_focus'),
    ('Remain lightning subtype', 't == 0x38 ? 9 : 10', 't == 0x38 ? 9 : 11', 'remain_focus'),
    ('Remain lightning scale', 'rnd(c) % 10) + 30.0f', 'rnd(c) % 10) + 31.0f', 'remain_focus'),
    ('Remain effect colour', '{0.8f,0.8f,1}', '{0.8f,0.7f,1}', 'remain_focus'),
    ('Trials guard', 'world != 31', 'world != 30', 'trials_focus'),
    ('Trials particle subtype', 't == 3 ? 3 : 22', 't == 3 ? 4 : 22', 'trials_focus'),
    ('Trials bone offset', 'local[3] = {0,-10,0}', 'local[3] = {0,-11,0}', 'trials_focus'),
    ('Trials pulse', '* 0.35f + 0.65f', '* 0.3f + 0.65f', 'trials_focus'),
    ('Trials sprite scale', 'pulse * 1.2f + 0.3f', 'pulse * 1.1f + 0.3f', 'trials_focus'),
    ('Trials detached sprite', 'a[8] = wv_bits(angle); a[11] = 4', 'a[8] = wv_bits(angle); a[9] = 1; a[11] = 4', 'trials_focus'),
    ('Trials sprite rotation', 'rnd(c) % 360', 'rnd(c) % 359', 'trials_focus'),
    ('Devil world', 'world != 9', 'world != 8', 'devil_focus'),
    ('Devil RNG', 'rnd(c) % 4 == 0', 'rnd(c) % 3 == 0', 'devil_focus'),
    ('Devil always branch', 'k == 2 ||', 'k == 1 ||', 'devil_focus'),
    ('Devil local', 'local[3] = {-15,0,0}', 'local[3] = {-14,0,0}', 'devil_focus'),
    ('Devil bone', '"Bip01 L UpperArm"', '"Bip01 R UpperArm"', 'devil_focus'),
    ('Devil bitmap', '0x771d, 0, p', '0x771e, 0, p', 'devil_focus'),
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
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    seed = lambda n: random.Random(0x511e + list(FAMILIES).index(n))
    for name in names:
        row = FAMILIES[name](machine, lib, seed(name), a.cases).report(); report['families'][name] = row
        print(name, json.dumps({k:v for k,v in row.items() if k != 'coverage'})[:5000], flush=True)
    if a.mutations:
        for label, old, new, family in MUTATIONS:
            if family not in names: continue
            with tempfile.TemporaryDirectory(prefix='worlds-inner3-mut-') as td:
                root = Path(td)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                path = root / 'objects/world_inner3_visual.c'; s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                assert len(re.findall(pattern, s)) == 1, label
                path.write_text(re.sub(pattern, lambda m: new, s, count=1))
                tally = FAMILIES[family](machine, build(root), seed(family), a.cases)
                row = {'name': label, 'cases': tally.cases, 'detected': tally.cases - tally.equal - tally.stopped,
                       'stopped': tally.stopped}; report['mutants'].append(row); print(row, flush=True)
    report['ok'] = all(r['mismatch_count'] == 0 and r['stopped'] == 0 for r in report['families'].values()) and \
                   all(r['detected'] > 0 for r in report['mutants'])
    if a.output: Path(a.output).write_text(json.dumps(report, indent=1))
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    sys.exit(main())
