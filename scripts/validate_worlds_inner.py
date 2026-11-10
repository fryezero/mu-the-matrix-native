#!/usr/bin/env python3
"""Compare the classless Kanturu and Blood Castle visual call streams with pinned original instructions.

Kanturu runs 0x00e75089 whole, including world tests and field writes. Blood Castle runs RenderObjectVisual
0x017f9758 from entry in worlds 11..17 and 52, including its model gate and outer rand before 0x017fc023.
Only engine leaves (draw/emitter, model and named-bone lookup, posed transform, clock, CRT heap and sin) are
recorded/stubbed. String/vector construction runs as client code. The full object/model result, ordered calls,
transform inputs, RNG state and clock call count are compared. Fixtures are synthetic, with no event feed.
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
import validate_worlds_slots2 as w2
import validate_worlds_slots3 as w3

ROOT = Path(__file__).resolve().parents[1]
KANTURU, BLOOD = 0xe75089, 0x17f9758
ALPHA, PUSH, POP = 0x1a7c6d0, 0x12b7e53, 0x12b7e65
BODY, MESH, PARTICLE, SPRITE, EFFECT, JOINT = 0x966def, 0x966e4a, 0x168fafd, 0x1692eb7, 0x13c0eaa, 0x153b02c
KTYPES = [0x25, 0x3b, 0x3d, 0x3e, 0x46, 0x51, 0x52, 0x53, 0x55, 0x5c, 0x60, 0x62, 0x69, 0x6b, 0x6c, 0x6e]
BTYPES = [0x0b, 0x0d, 0x2a]
NAMES = ['light', 'light01', 'light02', 'light03', 'light04', 'light05', 'light06']

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
        d.mu_kanturu_inner.argtypes = [P, P, I, I, F, C.c_uint32, v.RAND_FN, w2.BONE_FN, P, L]
        d.mu_blood_castle_inner.argtypes = [P, I, I, F, v.RAND_FN, w3.NAMED_FN, P, L]
        d.mu_kanturu_inner.restype = d.mu_blood_castle_inner.restype = C.c_int


def bone_point(k, local):
    return tuple(v.f32(local[q] + (k + 1) * (q + 2) * 7.25) for q in range(3))


def compare(machine, lib, g, cases, blood=False, focused=False):
    name = ('blood_focus' if blood else 'kanturu_focus') if focused else 'blood' if blood else 'kanturu'
    t = v.Tally(name)
    for n in range(cases):
        world = g.choice(list(range(11, 18)) + [52]) if blood else g.choice([37, 40, 37, 40, 0, 38, 41])
        typ = (0x2a if blood else KTYPES[n % len(KTYPES)]) if focused else n if n <= 300 else g.choice(BTYPES if blood else KTYPES)
        if focused and not blood: world = [37, 40][(n // len(KTYPES)) % 2]
        o = bytearray(w2.case_object(g, world, typ))
        v.put_i(o, 0x68, g.choice([-2, -1, 0, 3]))
        v.put_f(o, 0xb4, v.f32(g.choice([-4.01, -4, -3, -2, -1, 0, 1, 1.99, 2, 2.01, 3, 4, 5, 7, 8,
                                        2147483648.0, -2147483904.0, math.nan, g.uniform(-40, 40)])))
        b = bytearray(0x100); b[0x94] = g.choice([0, 1, 0xff]); v.put_f(b, 0x54, 0.25, 0.5, 0.75)
        present = not blood or n % 8 != 0
        time = w2.case_time(g)
        clock = g.choice([0, 1, 9, 10, 1023, 1024, 1025, 1033, 1034, 0xffffffff, g.randrange(2**32)])
        seed = g.randrange(2**32)
        if focused and not blood and typ in (0x5c, 0x69):
            for _ in range(4000):
                r = v.MsvcRand(seed)
                if typ == 0x69:
                    for _ in range(4): r()
                if r() % (20 if typ == 0x69 else 30) == (0 if typ == 0x69 else 1): break
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
            assert x[4] == v.OBJECTS
            calls.append((SPRITE, x[0], *v.read_vec(m, x[1]), x[2], *v.read_vec(m, x[3]), x[5], 1, x[6], x[7]))
            return 0
        def effect(m):
            x = [m.argument(k) for k in range(14)]
            assert x[5] == v.OBJECTS and x[6:] == [0xffffffff, 0, 0, 0, 0, 0xffffffff, 0, 0], x
            calls.append((EFFECT, x[0], *v.read_vec(m, x[1]), *v.read_vec(m, x[2]), *v.read_vec(m, x[3]), x[4], 1))
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
                 vp.SINE: lambda m: m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0)))))}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                     am.defined_region('model', v.MODEL, bytes(b)),
                     am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                     am.defined_region('heap', w3.HEAP, bytes(0x10000))])
        result = v.run(machine, BLOOD if blood else KANTURU, [v.OBJECTS] if blood else [v.OBJECTS, v.MODEL],
                       regions, stubs)
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
        if blood:
            if present:
                cb()  # the outer draw, before the bounded switch
                lib.dll.mu_blood_castle_inner(co, 0, world, time, rnd, named_fn, None, C.byref(log))
            answer = 1
        else:
            answer = lib.dll.mu_kanturu_inner(co, model, 0, world, time, clock, rnd, bone_fn, None, C.byref(log))
        native, stream = [], b[0x94]
        for e in v.log_events(log):
            call, _, *args = e
            if call == 0x17ffef3: stream = args[0] & 0xff
            elif call == MESH: native.append((call, *args, stream))
            else: native.append((call, *args))
        ok = calls == native and bones == native_bones and a.seed == cb.seed and \
            result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == model.raw[:0x100]
        if not blood:
            ok = ok and (result['eax'] & 0xff) == answer and clock_calls[0] == int(world in (37, 40) and typ == 0x25)
        t.count('world %d type %#x' % (world, typ)); t.count('draw/request calls', len(calls))
        for call in (PARTICLE, SPRITE, EFFECT, JOINT, MESH): t.count(hex(call), sum(x[0] == call for x in calls))
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': calls[:4], 'native': native[:4],
                  'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                  'model': result['regions']['model'] == model.raw[:0x100], 'rng': a.seed == cb.seed,
                  'bones': (bones[:8], native_bones[:8])})
    return t

FAMILIES = {'kanturu': lambda m, l, g, n: compare(m, l, g, n),
            'kanturu_focus': lambda m, l, g, n: compare(m, l, g, n, False, True),
            'blood': lambda m, l, g, n: compare(m, l, g, n, True),
            'blood_focus': lambda m, l, g, n: compare(m, l, g, n, True, True)}
MUTATIONS = [
    ('World 40 omitted', 'world!=37&&world!=40', 'world != 37', 'kanturu_focus'),
    ('Clock window 9', 'clock%1024u<10u', 'clock % 1024u < 9u', 'kanturu_focus'),
    ('Clock modulus 1023', 'clock%1024u<10u', 'clock % 1023u < 10u', 'kanturu_focus'),
    ('Effect wrong kind', '{0x193}', '{0x194}', 'kanturu_focus'),
    ('Type 25 not hidden', 'mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);', '(void)o;', 'kanturu_focus'),
    ('World 37 smoke roll', 'rnd(c)%6==0', 'rnd(c) % 5 == 0', 'kanturu_focus'),
    ('World 40 smoke 19', 'inner_particle(o,i,0x7f89,12,p,dark', 'inner_particle(o, i, 0x7f89, 11, p, dark', 'kanturu_focus'),
    ('Smoke dark colour', '{0.04f,0.04f,0.04f}', '{0.05f, 0.04f, 0.04f}', 'kanturu_focus'),
    ('Type 51 roll', 'rnd(c)%2==0)wv_particle(o,i,0x801a', 'rnd(c) % 3 == 0) wv_particle(o, i, 0x801a', 'kanturu_focus'),
    ('Type 52 subtype', 'wv_particle(o,i,0x801c,4', 'wv_particle(o, i, 0x801c, 5', 'kanturu_focus'),
    ('Type 53 roll', 'rnd(c)%3==0)wv_particle(o,i,0x801b', 'rnd(c) % 4 == 0) wv_particle(o, i, 0x801b', 'kanturu_focus'),
    ('Type 55 mesh', 'mesh_std(&s,3,0x42', 'mesh_std(&s, 2, 0x42', 'kanturu_focus'),
    ('Type 55 chrome', 'mesh_std(&s,3,0x84,0x7f1f)', 'mesh_std(&s, 3, 0x84, -1)', 'kanturu_focus'),
    ('Type 5c bone', 'bone(c,2,zero,q)', 'bone(c, 3, zero, q)', 'kanturu_focus'),
    ('Type 5c joint subtype', 'p,q,18,50.0f', 'p, q, 17, 50.0f', 'kanturu_focus'),
    ('Type 60 stream', 'stream(&s,0);', 'stream(&s, 1);', 'kanturu_focus'),
    ('Type 60 alpha reference', '{0x204,wv_bits(0.0f)}', '{0x204, wv_bits(0.25f)}', 'kanturu_focus'),
    ('Type 60 scroll sign', 'tmod(&s,20000,0.00005f,1)', 'tmod(&s, 20000, 0.00005f, 0)', 'kanturu_focus'),
    ('Type 62 light', '{0.5f,0.6f,0.1f}', '{0.5f, 0.7f, 0.1f}', 'kanturu_focus'),
    ('Type 69 pulse', 'csin(time*0.001f)+1.0f', 'csin(time * 0.002f) + 1.0f', 'kanturu_focus'),
    ('Type 69 random order', 'rnd(c)%100', 'rnd(c) % 80', 'kanturu_focus'),
    ('Type 69 joint subtype', 'p,q,8,40.0f', 'p, q, 9, 40.0f', 'kanturu_focus'),
    ('Type 6b owner', 't==0x6b?2:7,p,light,mu_obj_f32(o,MU_OBJF_SCALE),1', 't == 0x6b ? 2 : 7, p, light, mu_obj_f32(o, MU_OBJF_SCALE), 0', 'kanturu_focus'),
    ('Type 6e sprite scale', 'p,1.1f,light', 'p, 1.2f, light', 'kanturu_focus'),
    ('Blood world 52 omitted', '||world==52', '|| world == 53', 'blood'),
    ('Blood upper world 16', 'world<=17', 'world <= 16', 'blood'),
    ('Blood named local z', 'local[3]={0,0,2}', 'local[3] = {0, 0, 3}', 'blood'),
    ('Blood light06 omitted', 'k<7;', 'k < 6;', 'blood'),
    ('Blood angle phase', 'MU_OBJF_ANGLE+8)*20.0f', 'MU_OBJF_ANGLE + 8) * 5.0f', 'blood'),
    ('Blood d scale', 'pulse+0.5f', 'pulse + 0.6f', 'blood'),
    ('Blood first counter phase', 'mu_obj_f32(o,0xb4)+2.0f', 'mu_obj_f32(o, 0xb4) + 1.0f', 'blood_focus'),
    ('Blood second counter phase', 'n=cvtt(mu_obj_f32(o,0xb4))%4', 'n = cvtt(mu_obj_f32(o, 0xb4) + 1.0f) % 4', 'blood_focus'),
    ('Blood red particle scale', 'red,0.19f', 'red, 0.2f', 'blood_focus'),
]

def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
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
        print(name, json.dumps(row)[:3000], flush=True)
    if a.mutations:
        for label, old, new, family in MUTATIONS:
            if family not in names: continue
            with tempfile.TemporaryDirectory(prefix='worlds-inner-mut-') as td:
                root = Path(td)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                path = root / 'objects/world_inner_visual.c'; s = path.read_text()
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
