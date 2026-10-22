#!/usr/bin/env python3
"""Compare reconstructed/helpers/mount_render.c with the mounts' registry functors (NATIVE-HELPERS-002).

The mount render loop 0x0106bc2b draws a mount's after-pass through RenderObject's draw 0x017edf43, which hands
the mount models to their functors in the render registry 0x01d1e010 (filled by the 0x00a16273 calls). Each
functor runs here in Unicorn (scripts/actor_machine.py through validate_helpers.Machine: declared regions with a
defined-byte mask; an undefined read, an undeclared access or an unmapped access stops a case) and the authored C
(libclient_helpers: mu_hp_mount_after) runs on the same inputs. Compared: the ordered calls with their arguments
and the model fields +0x54 (colour) and +0x94 at each RenderBodyDefault / RenderMeshDefault call, the rand() count
and the return value.

Client code: the functors, the glow wave 0x0185bdc4, the world predicate 0x016a88ae, the vector accessors and
setters, the sprite sheet constructor 0x00a0c1d0. Recording stubs: RenderBodyDefault 0x00966def, RenderMeshDefault
0x00966e4a, the pose push/pop 0x012b7e53 / 0x012b7e65, TransformPosition 0x012b6ef1 (a synthetic answer from the
bone index and the vector), CreateSprite 0x01692eb7, CreateParticle 0x0168fafd, CreateEffect 0x013c0eaa,
EnableAlphaTest 0x0184a990, glColor4f, RenderBodyShadow 0x012bc07a, rand() 0x01989721, the CRT sine and cosine
wrappers 0x009681bd / 0x009fa223 (host libm, binary32 results), the world predicate 0x009b0418 and the event
check 0x009a6ef3 / 0x009a645f (case answers). Negative controls plant mistakes into the C's inputs or answers.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import validate_helpers as vh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
f32, bits, from_bits, same = vh.f32, vh.bits, vh.from_bits, vh.same

REGISTRY_INSERT = 0x00a16273
FUNCTORS = {
    0x410: 0x00a2eaa2, 0x417: 0x00a2f501, 0x473: 0x00a318b8, 0x4a8: 0x00a335e9, 0x4a9: 0x00a34652,
    0x4aa: 0x00a356bb, 0x4ab: 0x00a36724, 0x671: 0x00a477ec, 0x69a: 0x00a480f9, 0x69b: 0x00a48462,
    0x6cb: 0x00a4cd20, 0x6cc: 0x00a4cfed, 0x6f4: 0x00a4f699, 0x6f5: 0x00a4fa6d, 0x736: 0x00a527d1,
    0x737: 0x00a52da0, 0x749: 0x00a54b97, 0x74a: 0x00a54e60, 0x77c: 0x00a551fe, 0x77d: 0x00a55883,
    0x753: 0x00a5aee8, 0x73f: 0x00a53c44, 0x740: 0x00a540ba, 0x741: 0x00a54490,
}
BODY, MESH, PUSH, POP = 0x00966def, 0x00966e4a, 0x012b7e53, 0x012b7e65
TRANSFORM, SPRITE, PARTICLE, EFFECT = 0x012b6ef1, 0x01692eb7, 0x0168fafd, 0x013c0eaa
ALPHA_TEST, SHADOW, RAND, SINE, COSINE = 0x0184a990, 0x012bc07a, 0x01989721, 0x009681bd, 0x009fa223
WORLD_9B0418, EVENT_OBJ, EVENT_CHECK = 0x009b0418, 0x009a6ef3, 0x009a645f
WORLD, TIME = 0x01cf15fc, 0x06fce370
BONES = 0x06fce398
MODEL, OBJECT, EVENT = 0x29000000, 0x29100000, 0x29200000

C_KINDS = {1: 'body', 2: 'mesh', 3: 'push', 4: 'pop', 5: 'alpha', 6: 'color4', 7: 'shadow', 8: 'bone', 9: 'sprite',
           10: 'particle', 11: 'effect'}


class AfterCall(ctypes.Structure):
    F3 = ctypes.c_float*3
    _fields_ = [('kind', ctypes.c_int32), ('mesh', ctypes.c_int32), ('flags', ctypes.c_uint32), ('alpha', ctypes.c_float),
                ('blend_mesh', ctypes.c_int32), ('blend_light', ctypes.c_float), ('u', ctypes.c_float),
                ('v', ctypes.c_float), ('hidden', ctypes.c_int32), ('texture', ctypes.c_int32), ('color', F3),
                ('model_94', ctypes.c_uint8), ('type', ctypes.c_int32), ('subtype', ctypes.c_int32),
                ('position', F3), ('angle', F3), ('light', F3), ('scale', ctypes.c_float)]


class AfterInputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('world_time', ctypes.c_float), ('world_9b0418', ctypes.c_uint8),
                ('event_block', ctypes.c_uint8), ('color', ctypes.c_float*3), ('model_94', ctypes.c_uint8),
                ('object_a4', ctypes.c_float), ('object_u', ctypes.c_float), ('object_v', ctypes.c_float)]


BONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                           ctypes.POINTER(ctypes.c_float))


class AfterHost(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('bone', BONE_FN)]


def bone_answer(index, vec):
    """The synthetic TransformPosition both sides use."""
    return [f32(f32(vec[0]*f32(1.25)) + f32(index*10.0 + 1000.0)), f32(f32(vec[1]*f32(-0.5)) + f32(index*3.0)),
            f32(f32(vec[2]) + f32(150.0 + index))]


def load_library(path):
    lib = vh.load_library(path)
    lib.mu_hp_mount_after.argtypes = [ctypes.POINTER(vh.Helpers), ctypes.POINTER(vh.Obj), ctypes.POINTER(AfterInputs),
                                      ctypes.POINTER(AfterHost), ctypes.POINTER(AfterCall), ctypes.c_int32,
                                      ctypes.POINTER(ctypes.c_int32)]
    lib.mu_hp_mount_after.restype = ctypes.c_int
    lib.mu_hp_wave.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]
    lib.mu_hp_wave.restype = ctypes.c_float
    return lib


def object_bytes(case):
    raw = bytearray(am.poison(0x3d8, 0x2f))
    struct.pack_into('<H', raw, 0x2a, case['action'])
    struct.pack_into('<i', raw, 0x5c, case['type'])
    struct.pack_into('<i', raw, 0x60, case['subtype'])
    struct.pack_into('<i', raw, 0x68, case['o68'])
    struct.pack_into('<i', raw, 0x74, case['blend_mesh'])
    for off, key in ((0xa4, 'a4'), (0xa8, 'blend_light'), (0xac, 'u'), (0xb0, 'v'), (0xd0, 'frame'), (0xdc, 'alpha')):
        struct.pack_into('<f', raw, off, case[key])
    struct.pack_into('<3f', raw, 0x158, *case['position'])
    struct.pack_into('<3f', raw, 0x164, *case['angle'])
    return bytes(raw)


def random_case(rng, typ):
    def rf(lo, hi, specials=()):
        if specials and rng.random() < 0.3:
            return f32(rng.choice(specials))
        return f32(rng.uniform(lo, hi))
    return {
        'type': typ,
        'subtype': rng.choice([0, 0, 1, 2, 3, 10, 15, rng.randrange(-3, 16)]),
        'action': rng.choice([0, 1, 2, 3, 4, 4, rng.randrange(0, 12)]),
        'frame': rf(0.0, 12.0, (0.0, 1.0, 1.2, 1.4, 1.5, 1.50001, 4.8, 5.0, 5.2, 5.2001, -0.0001)),
        'alpha': rf(0.0, 1.0, (1.0, 0.0, 0.5)),
        'blend_mesh': rng.choice([-1, -1, 0, 2, rng.randrange(-2, 8)]),
        'blend_light': rf(0.0, 2.0, (1.0,)),
        'a4': rf(0.0, 2.0, (1.0,)),
        'u': rf(-1.0, 1.0, (0.0,)), 'v': rf(-1.0, 1.0, (0.0,)),
        'o68': rng.choice([-1, -1, -2, rng.randrange(0, 8)]),
        'position': [rf(0, 25600), rf(0, 25600), rf(-100, 800)],
        'angle': [rf(-360, 360), rf(-360, 360), rf(-360, 360)],
        'world': rng.choice([0, 0, 2, 7, 0x80, 0x82, 10, 0x84, rng.randrange(0, 0x100)]),
        'time': f32(rng.choice([0.0, 39.0, 1234.5, rng.uniform(0, 4.0e6), rng.uniform(0, 3.0e5)])),
        'w9b0418': rng.randrange(4) == 0,
        'event': rng.randrange(4) == 0,
        'color': [rf(0, 1.5), rf(0, 1.5), rf(0, 1.5)],
        'm94': rng.choice([0xff, 0, 1, rng.randrange(256)]),
        'rand': [rng.randrange(0, 32768) for _ in range(16)],
    }


class Run:
    def __init__(self, m, case):
        self.m, self.case = m, case
        self.log, self.rand_calls = [], 0

    def model_fields(self):
        raw = bytes(self.m.uc.mem_read(MODEL + 0x54, 12))
        m94 = self.m.uc.mem_read(MODEL + 0x94, 1)[0]
        return tuple(struct.unpack('<3f', raw)), m94

    def stubs(self):
        m, case = self.m, self.case

        def body(mm):
            a = [mm.argument(i) for i in range(8)]
            color, m94 = self.model_fields()
            self.log.append(('body', a[0], from_bits(a[1]), a[2] - (1 << 32) if a[2] >> 31 else a[2], from_bits(a[3]),
                             from_bits(a[4]), from_bits(a[5]), sx(a[6]), sx(a[7]), color, m94))
            return 0, 0x20

        def mesh(mm):
            a = [mm.argument(i) for i in range(8)]
            color, m94 = self.model_fields()
            self.log.append(('mesh', sx(a[0]), a[1], from_bits(a[2]), sx(a[3]), from_bits(a[4]), from_bits(a[5]),
                             from_bits(a[6]), sx(a[7]), color, m94))
            return 0, 0x20

        def push(mm):
            self.log.append(('push', from_bits(mm.argument(0))))
            return 0, 4

        def pop(mm):
            self.log.append(('pop',))
            return 0, 0

        def transform(mm):
            matrix, vin, vout, translate = (mm.argument(i) for i in range(4))
            index = (matrix - BONES) // 0x30 if (matrix - BONES) % 0x30 == 0 else ('raw', matrix)
            vec = list(mm.read_floats(vin, 3))
            self.log.append(('bone', index, tuple(vec), translate))
            out = bone_answer(index if isinstance(index, int) else 0, vec)
            mm.local_write(vout, struct.pack('<3f', *out))
            return 0, 0x10

        def sprite(mm):
            a = [mm.argument(i) for i in range(8)]
            self.log.append(('sprite', a[0], tuple(mm.read_floats(a[1], 3)), from_bits(a[2]),
                             tuple(mm.read_floats(a[3], 3)), a[4] == OBJECT, from_bits(a[5]), a[6], a[7]))
            return 0

        def particle(mm):
            a = [mm.argument(i) for i in range(8)]
            self.log.append(('particle', a[0], tuple(mm.read_floats(a[1], 3)), tuple(mm.read_floats(a[2], 3)),
                             tuple(mm.read_floats(a[3], 3)), sx(a[4]), from_bits(a[5]), a[6], a[7]))
            return 0

        def effect(mm):
            a = [mm.argument(i) for i in range(7)]
            self.log.append(('effect', a[0], tuple(mm.read_floats(a[1], 3)), tuple(mm.read_floats(a[2], 3)),
                             tuple(mm.read_floats(a[3], 3)), sx(a[4]), a[5] == OBJECT, sx(a[6])))
            return 0

        def alpha(mm):
            self.log.append(('alpha', mm.argument(0)))
            return 0

        def color4(mm):
            a = [from_bits(mm.argument(i)) for i in range(4)]
            self.log.append(('color4', tuple(a)))
            return 0, 16

        def shadow(mm):
            a = [sx(mm.argument(i)) for i in range(5)]
            self.log.append(('shadow', tuple(a)))
            return 0, 0x14

        def rand(mm):
            v = case['rand'][self.rand_calls % len(case['rand'])]
            self.rand_calls += 1
            return v

        def sine(mm):
            x = mm.float_argument(0)
            return mm.return_float(f32(math.sin(x)) if math.isfinite(x) else float('nan'))

        def cosine(mm):
            x = mm.float_argument(0)
            return mm.return_float(f32(math.cos(x)) if math.isfinite(x) else float('nan'))

        def w9b0418(mm):
            return int(case['w9b0418'])

        def event_obj(mm):
            return EVENT

        def event_check(mm):
            return int(case['event'])
        return {BODY: body, MESH: mesh, PUSH: push, POP: pop, TRANSFORM: transform, SPRITE: sprite,
                PARTICLE: particle, EFFECT: effect, ALPHA_TEST: alpha, self.m.gl_color4: color4, SHADOW: shadow,
                RAND: rand, SINE: sine, COSINE: cosine, WORLD_9B0418: w9b0418, EVENT_OBJ: event_obj,
                EVENT_CHECK: event_check}

    def regions(self):
        case = self.case
        model = bytearray(am.poison(0x200, 0x3c))
        struct.pack_into('<3f', model, 0x54, *case['color'])
        model[0x94] = case['m94']
        return [am.defined_region('model', MODEL, bytes(model)),
                am.defined_region('object', OBJECT, object_bytes(case), writable=False),
                am.defined_region('event', EVENT, am.poison(0x100, 0x11), writable=False),
                am.defined_region('world', WORLD, struct.pack('<i', case['world']), writable=False),
                am.defined_region('time', TIME, struct.pack('<f', case['time']), writable=False)]


def sx(v):
    v &= 0xffffffff
    return v - (1 << 32) if v >> 31 else v


def native_log(lib, case, plant=None):
    h = vh.Helpers()
    h.rand_state = 0
    o = vh.Obj()
    o.type = case['type']
    o.subtype = case['subtype']
    o.action = case['action']
    o.frame = case['frame']
    o.alpha = case['alpha']
    o.blend_mesh = case['blend_mesh']
    o.blend_light = case['blend_light']
    o.field_68 = case['o68']
    for k in range(3):
        o.position[k] = case['position'][k]
        o.angle[k] = case['angle'][k]
    i = AfterInputs()
    i.world = case['world']
    i.world_time = case['time'] if plant != 'time' else f32(case['time'] + 40.0)
    i.world_9b0418 = int(case['w9b0418'])
    i.event_block = int(case['event'])
    for k in range(3):
        i.color[k] = case['color'][k]
    i.model_94 = case['m94']
    i.object_a4 = case['a4']
    i.object_u = case['u']
    i.object_v = case['v'] if plant != 'v' else f32(case['v'] + 0.25)
    rands = list(case['rand'])
    counter = [0]

    def bone(ctx, index, vin, vout):
        out = bone_answer(index, [vin[0], vin[1], vin[2]])
        for k in range(3):
            vout[k] = out[k]
    fn = BONE_FN(bone)
    host = AfterHost(None, fn)
    # rand() goes through the helpers' LCG: drive it from the case values instead
    calls = (AfterCall*512)()
    n = ctypes.c_int32(0)
    r = lib.mu_hp_mount_after(ctypes.byref(h), ctypes.byref(o), ctypes.byref(i), ctypes.byref(host), calls, 512,
                              ctypes.byref(n))
    del counter, rands
    out = []
    for k in range(n.value):
        c = calls[k]
        kind = C_KINDS[c.kind]
        color = tuple(c.color)
        if kind == 'body':
            out.append(('body', c.flags, c.alpha, c.blend_mesh, c.blend_light, c.u, c.v, c.hidden, c.texture, color,
                        c.model_94))
        elif kind == 'mesh':
            out.append(('mesh', c.mesh, c.flags, c.alpha, c.blend_mesh, c.blend_light, c.u, c.v, c.texture, color,
                        c.model_94))
        elif kind == 'push':
            out.append(('push', 1.0))
        elif kind == 'pop':
            out.append(('pop',))
        elif kind == 'alpha':
            out.append(('alpha', c.mesh))
        elif kind == 'color4':
            out.append(('color4', (0.0, 0.0, 0.0, c.scale)))
        elif kind == 'shadow':
            out.append(('shadow', (-1, -1, c.mesh, c.texture, 0)))
        elif kind == 'bone':
            out.append(('bone', c.mesh, tuple(c.position), 0))
        elif kind == 'sprite':
            out.append(('sprite', c.type, tuple(c.position), c.scale, tuple(c.light), True, 0.0, 0, 4))
        elif kind == 'particle':
            out.append(('particle', c.type, tuple(c.position), tuple(c.angle), tuple(c.light), c.subtype, c.scale, 0, 0))
        elif kind == 'effect':
            out.append(('effect', c.type, tuple(c.position), tuple(c.angle), tuple(c.light), c.subtype, True, -1))
    return r, out, h.rand_calls


def run_case(m, lib, case, plant=None):
    run = Run(m, case)
    res = m.execute(FUNCTORS[case['type']], [MODEL, OBJECT, 1, 0, 0, 0xffffffff, 0xffffffff], run.regions(),
                    run.stubs(), ecx=0)
    if not res['ok']:
        return {'ok': False, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
    # the C draws rand() from its LCG: replay the client's values by seeding per call is not possible, so the
    # case's rand values are the LCG outputs of a seed (see seeded_rand below)
    r, mine, rand_calls = native_log(lib, case, plant)
    theirs = run.log
    al = res['eax'] & 0xff
    if r != al:
        return {'ok': False, 'why': 'return', 'client': al, 'native': r}
    if run.rand_calls != rand_calls:
        return {'ok': False, 'why': 'rand calls', 'client': run.rand_calls, 'native': rand_calls}
    if len(mine) != len(theirs) or not all(same_call(a, b) for a, b in zip(theirs, mine)):
        first = next((k for k, (a, b) in enumerate(zip(theirs, mine)) if not same_call(a, b)), min(len(mine), len(theirs)))
        return {'ok': False, 'why': 'calls', 'at': first, 'client': theirs[first:first+2], 'native': mine[first:first+2],
                'lengths': (len(theirs), len(mine))}
    return {'ok': True, 'calls': len(theirs), 'kinds': sorted({c[0] for c in theirs})}


def same_call(a, b):
    if len(a) != len(b):
        return False
    return all(same_value(x, y) for x, y in zip(a, b))


def same_value(x, y):
    if isinstance(x, (tuple, list)) and isinstance(y, (tuple, list)):
        return len(x) == len(y) and all(same_value(p, q) for p, q in zip(x, y))
    if isinstance(x, float) or isinstance(y, float):
        x, y = float(x), float(y)
        return (math.isnan(x) and math.isnan(y)) or bits(x) == bits(y)
    return x == y


def seeded_rand(seed, count):
    """The helpers library's rand(): the MSVC LCG from rand_state 0."""
    state, out = seed, []
    for _ in range(count):
        state = (state * 214013 + 2531011) & 0xffffffff
        out.append((state >> 16) & 0x7fff)
    return out


def registry_pairs(text):
    """The (type, functor) pairs of the registry, from the 0x00a16273 call sites (push functor; push type; call)."""
    pairs = {}
    for off in range(len(text) - 5):
        if text[off] != 0xe8:
            continue
        addr = am.TEXT_BASE + off
        rel = struct.unpack_from('<i', text, off + 1)[0]
        if addr + 5 + rel != REGISTRY_INSERT:
            continue
        # the two pushes right before the call (push functor; push type), five bytes each
        if text[off - 10] == 0x68 and text[off - 5] == 0x68:
            pairs[struct.unpack_from('<I', text, off - 4)[0]] = struct.unpack_from('<I', text, off - 9)[0]
    return pairs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=vh.DEFAULT_TEXT)
    parser.add_argument('--data', default=vh.DEFAULT_DATA)
    parser.add_argument('--library', default=str(vh.LIB))
    parser.add_argument('--cases', type=int, default=200, help='cases per mount model')
    parser.add_argument('--seed', type=int, default=20261022)
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = vh.Machine(text, data)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256}
    start = time.time()
    pairs = registry_pairs(text)
    registry_ok = all(pairs.get(t) == f for t, f in FUNCTORS.items())
    report['registry'] = {'pairs': len(pairs), 'mount_models_match': registry_ok,
                          'mismatch': {hex(t): hex(pairs.get(t, 0)) for t, f in FUNCTORS.items() if pairs.get(t) != f}}
    bodies = {}
    for t, f in FUNCTORS.items():
        end = f + 0x80
        for off in range(f - am.TEXT_BASE, f - am.TEXT_BASE + 0x4000):
            if text[off] == 0xc3 and text[off + 1] in (0xcc, 0x55):
                end = am.TEXT_BASE + off + 1
                break
        bodies[hex(t)] = {'functor': hex(f), 'sha256_16': hashlib.sha256(text[f-am.TEXT_BASE:end-am.TEXT_BASE]).hexdigest()[:16]}
    report['bodies'] = bodies
    rng = random.Random(args.seed)
    totals = {'cases': 0, 'equal': 0, 'calls': 0, 'by_model': {}, 'first_failures': []}
    for t in FUNCTORS:
        ok = 0
        for n in range(args.cases):
            case = random_case(rng, t)
            case['rand'] = seeded_rand(0, 16)
            r = run_case(m, lib, case)
            totals['cases'] += 1
            if r['ok']:
                ok += 1
                totals['calls'] += r['calls']
            elif len(totals['first_failures']) < 6:
                totals['first_failures'].append(dict(r, type=hex(t), case={k: v for k, v in case.items() if k != 'rand'}))
        totals['equal'] += ok
        totals['by_model'][hex(t)] = f'{ok}/{args.cases}'
    report['functors'] = totals
    # negative controls: the C on shifted inputs must disagree
    negatives = {}
    for plant, types in (('time', [0x671, 0x6f4, 0x753, 0x4ab]), ('v', [0x410, 0x6f4, 0x77c])):
        hit = 0
        for n in range(40):
            case = random_case(rng, types[n % len(types)])
            case['rand'] = seeded_rand(0, 16)
            hit += not run_case(m, lib, case, plant)['ok']
        negatives[plant] = hit
    report['negative_controls'] = negatives
    report['seconds'] = round(time.time() - start, 1)
    report['all_equal'] = registry_ok and totals['equal'] == totals['cases'] and all(negatives.values())
    print(json.dumps({k: v for k, v in report.items() if k not in ('bodies',)}, indent=1, default=str)[:6000])
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    return 0 if report['all_equal'] else 1


if __name__ == '__main__':
    sys.exit(main())
