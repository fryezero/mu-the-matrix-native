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


# --------------------------------------------------------------------------
# The class visuals (vtable +0x1c) and steps (mount_class.c).

ST_VISUALS, ST_MOVE_STEPS = 0x01057fb0, 0x0105a0bb
OBJECT_BONE, NAMED_BONE, CREATE_JOINT, EYES, DECAL = 0x012b678d, 0x012b6a2b, 0x0153b02c, 0x0137a948, 0x016cdd5f
BLEND_ON, BLEND_OFF = 0x0184aa2b, 0x0184a7f3
STRING_CTOR, STRING_DTOR = 0x0094997e, 0x008e83a0
MOUNT = 0x29300000
CLASS_KINDS = {20: 'obone', 21: 'joint', 22: 'decal', 23: 'blend', 24: 'eyes', 25: 'nbone'}
STEP_NAMES = ['leg_nailfront', 'leg_nailfront001', 'leg_rear', 'leg_rear001']


class ClassState(ctypes.Structure):
    _fields_ = [('a4', ctypes.c_float), ('flag_48', ctypes.c_uint8)]


class ClassInputs(ctypes.Structure):
    _fields_ = [('world_time', ctypes.c_float), ('action', ctypes.c_uint16), ('frame', ctypes.c_float),
                ('alpha', ctypes.c_float), ('position', ctypes.c_float*3), ('angle', ctypes.c_float*3)]


OBONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float))
NBONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_float))


class ClassHost(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('object_bone', OBONE_FN), ('named_bone', NBONE_FN)]


def object_bone_answer(bone):
    return [f32(1000.0 + bone*7.5), f32(2000.0 - bone*3.25), f32(150.0 + bone*0.5)]


def named_bone_answer(name):
    k = STEP_NAMES.index(name) if name in STEP_NAMES else 9
    return [f32(500.0 + k*11.0), f32(600.0 - k*5.0), f32(40.0 + k)]


def read_msvc_string(mm, address):
    raw = bytes(mm.uc.mem_read(address, 0x20))
    for off in (0, 4):
        size = struct.unpack('<I', raw[off+16:off+20])[0]
        cap = struct.unpack('<I', raw[off+20:off+24])[0]
        if size < 64 and cap >= size:
            if cap < 16:
                return raw[off:off+size].decode('latin1')
            ptr = struct.unpack('<I', raw[off:off+4])[0]
            return bytes(mm.uc.mem_read(ptr, size)).decode('latin1')
    return raw.hex()


def class_case(rng):
    case = random_case(rng, 0x6f4)
    case['a4'] = f32(rng.choice([0.0, 1.0, 0.05, 0.95, 1.02, -0.01, rng.uniform(-0.1, 1.1)]))
    case['flag48'] = rng.choice([0, 0, 1])
    case['action'] = rng.choice([0, 1, 2, 3, 2, 3, 4, rng.randrange(0, 12)])
    case['frame'] = f32(rng.choice([4.0, 4.5, 5.0, 5.0001, 9.0, 9.9, 10.0, 3.999, rng.uniform(0, 12)]))
    case['time'] = f32(rng.choice([0.0, 1000.0, 1050.0, 59999.0, rng.uniform(0, 4.0e6), float(rng.randrange(0, 600)*100)]))
    return case


def run_class_case(m, lib, case, routine, plant=None):
    log, rand_calls = [], [0]
    obj = bytearray(object_bytes(case))
    struct.pack_into('<f', obj, 0xa4, case['a4'])
    mount = bytearray(am.poison(0x58, 0x21))
    struct.pack_into('<II', mount, 0x1c, OBJECT, MODEL)
    mount[0x48] = case['flag48']
    regions = [am.defined_region('model', MODEL, am.poison(0x200, 0x3c)),
               am.defined_region('object', OBJECT, bytes(obj)),
               am.defined_region('mount', MOUNT, bytes(mount)),
               am.defined_region('time', TIME, struct.pack('<f', case['time']), writable=False),
               am.defined_region('world', WORLD, struct.pack('<i', case['world']), writable=False)]

    def obone(mm):
        out, o, bone = mm.argument(0), mm.argument(1), sx(mm.argument(2))
        log.append(('obone', bone))
        mm.local_write(out, struct.pack('<3f', *object_bone_answer(bone)))
        return 0, 0x10

    def nbone(mm):
        out, o, name = mm.argument(0), mm.argument(1), read_msvc_string(mm, mm.argument(2))
        log.append(('nbone', STEP_NAMES.index(name) if name in STEP_NAMES else name))
        mm.local_write(out, struct.pack('<3f', *named_bone_answer(name)))
        return 0, 0x10

    def sprite(mm):
        a = [mm.argument(i) for i in range(8)]
        log.append(('sprite', a[0], tuple(mm.read_floats(a[1], 3)), from_bits(a[2]), tuple(mm.read_floats(a[3], 3))))
        return 0

    def particle(mm):
        a = [mm.argument(i) for i in range(8)]
        log.append(('particle', a[0], tuple(mm.read_floats(a[1], 3)), tuple(mm.read_floats(a[2], 3)),
                    tuple(mm.read_floats(a[3], 3)), sx(a[4]), from_bits(a[5])))
        return 0

    def effect(mm):
        a = [mm.argument(i) for i in range(11)]
        log.append(('effect', a[0], tuple(mm.read_floats(a[1], 3)), tuple(mm.read_floats(a[2], 3)),
                    tuple(mm.read_floats(a[3], 3)), sx(a[4]), from_bits(a[10])))
        return 0

    def joint(mm):
        a = [mm.argument(i) for i in range(14)]
        log.append(('joint', a[0], tuple(mm.read_floats(a[1], 3)), tuple(mm.read_floats(a[3], 3)), sx(a[4]),
                    from_bits(a[6]), tuple(mm.read_floats(a[11], 3))))
        return 0

    def eyes(mm):
        log.append(('eyes',))
        return 0

    def decal(mm):
        a = [mm.argument(i) for i in range(11)]
        log.append(('decal', a[0], from_bits(a[1]), from_bits(a[2]), from_bits(a[3]), from_bits(a[4]),
                    tuple(mm.read_floats(a[5], 3)), from_bits(a[6]), from_bits(a[7]), from_bits(a[8]), a[9], a[10]))
        return 0

    def blend(address):
        def stub(mm):
            log.append(('blend', address))
            return 0
        return stub

    def rand(mm):
        v = case['rand'][rand_calls[0] % len(case['rand'])]
        rand_calls[0] += 1
        return v

    def sine(mm):
        x = mm.float_argument(0)
        return mm.return_float(f32(math.sin(x)) if math.isfinite(x) else float('nan'))

    def cosine(mm):
        x = mm.float_argument(0)
        return mm.return_float(f32(math.cos(x)) if math.isfinite(x) else float('nan'))
    def string_ctor(mm):
        # MSVC std::string(const char *) 0x0094997e: the pointer form at the literal (no heap in the machine)
        this, text = mm.ecx(), mm.argument(0)
        name = mm.cstring(text, 64)
        mm.local_write(this, struct.pack('<I', text) + b'\0'*12 + struct.pack('<II', len(name), max(len(name), 16)))
        return this, 4

    def string_dtor(mm):
        return 0
    stubs = {STRING_CTOR: string_ctor, STRING_DTOR: string_dtor, OBJECT_BONE: obone, NAMED_BONE: nbone, SPRITE: sprite, PARTICLE: particle, EFFECT: effect,
             CREATE_JOINT: joint, EYES: eyes, DECAL: decal, BLEND_ON: blend(BLEND_ON), BLEND_OFF: blend(BLEND_OFF),
             RAND: rand, SINE: sine, COSINE: cosine}
    res = m.execute(routine, [], regions, stubs, ecx=MOUNT)
    if not res['ok']:
        return {'ok': False, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
    a4_client = struct.unpack('<f', res['regions']['object'][0xa4:0xa8])[0]
    flag_client = res['regions']['mount'][0x48]
    # the library
    h = vh.Helpers()
    h.rand_state = 0
    st = ClassState(case['a4'], case['flag48'])
    i = ClassInputs()
    i.world_time = case['time'] if plant != 'time' else f32(case['time'] + 100.0)
    i.action = case['action']
    i.frame = case['frame']
    i.alpha = case['alpha']
    for k in range(3):
        i.position[k] = case['position'][k]
        i.angle[k] = case['angle'][k]

    def c_obone(ctx, bone, out):
        for k, x in enumerate(object_bone_answer(bone)):
            out[k] = x

    def c_nbone(ctx, name, out):
        for k, x in enumerate(named_bone_answer(name.decode())):
            out[k] = x
    host = ClassHost(None, OBONE_FN(c_obone), NBONE_FN(c_nbone))
    calls = (AfterCall*1024)()
    n = ctypes.c_int32(0)
    if routine == ST_VISUALS:
        lib.mu_hp_mount_class_visuals(ctypes.byref(h), 10, ctypes.byref(st), ctypes.byref(i), ctypes.byref(host),
                                      calls, 1024, ctypes.byref(n))
    else:
        lib.mu_hp_mount_class_step(ctypes.byref(h), 10, ctypes.byref(i), ctypes.byref(host), calls, 1024,
                                   ctypes.byref(n))
    mine = []
    for k in range(n.value):
        c = calls[k]
        kind = CLASS_KINDS.get(c.kind) or C_KINDS[c.kind]
        if kind == 'obone':
            mine.append(('obone', c.mesh))
        elif kind == 'nbone':
            mine.append(('nbone', c.mesh))
        elif kind == 'sprite':
            mine.append(('sprite', c.type, tuple(c.position), c.scale, tuple(c.light)))
        elif kind == 'particle':
            mine.append(('particle', c.type, tuple(c.position), tuple(c.angle), tuple(c.light), c.subtype, c.scale))
        elif kind == 'effect':
            sub = c.subtype
            mine.append(('effect', c.type, tuple(c.position), tuple(c.angle), tuple(c.light), sub, c.scale))
        elif kind == 'joint':
            mine.append(('joint', c.type, tuple(c.position), tuple(c.angle), c.subtype, c.scale, tuple(c.light)))
        elif kind == 'eyes':
            mine.append(('eyes',))
        elif kind == 'decal':
            mine.append(('decal', c.type, c.position[0], c.position[1], c.scale, c.scale, tuple(c.light), c.angle[0],
                         c.alpha, 5.0, 1, 0))
        elif kind == 'blend':
            mine.append(('blend', c.flags))
    if len(mine) != len(log) or not all(same_call(a, b) for a, b in zip(log, mine)):
        first = next((k for k, (a, b) in enumerate(zip(log, mine)) if not same_call(a, b)), min(len(mine), len(log)))
        return {'ok': False, 'why': 'calls', 'at': first, 'client': log[first:first+2], 'native': mine[first:first+2],
                'lengths': (len(log), len(mine))}
    if rand_calls[0] != h.rand_calls:
        return {'ok': False, 'why': 'rand calls', 'client': rand_calls[0], 'native': h.rand_calls}
    if routine == ST_VISUALS and (not same_value(a4_client, st.a4) or flag_client != st.flag_48):
        return {'ok': False, 'why': 'state', 'client': (a4_client, flag_client), 'native': (st.a4, st.flag_48)}
    return {'ok': True, 'calls': len(log)}


def section_class(m, lib, rng, cases):
    out = {}
    for name, routine in (('shining_tail_visuals', ST_VISUALS), ('shining_tail_steps', ST_MOVE_STEPS)):
        ok, calls, first = 0, 0, None
        for n in range(cases):
            case = class_case(rng)
            case['rand'] = seeded_rand(0, 64)
            if routine == ST_MOVE_STEPS:
                case['action'] = rng.choice([2, 3])   # the class move 0x01057e4d calls it for mount actions 2, 3
            r = run_class_case(m, lib, case, routine)
            if r['ok']:
                ok += 1
                calls += r['calls']
            elif first is None:
                first = dict(r, case={k: v for k, v in case.items() if k != 'rand'})
        out[name] = {'cases': cases, 'equal': ok, 'calls': calls, 'first_failure': first}
    hit = 0
    for n in range(30):
        case = class_case(rng)
        case['rand'] = seeded_rand(0, 64)
        hit += not run_class_case(m, lib, case, ST_VISUALS, 'time')['ok']
    out['negative_time'] = hit
    return out


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
    lib.mu_hp_mount_class_visuals.argtypes = [ctypes.POINTER(vh.Helpers), ctypes.c_int32, ctypes.POINTER(ClassState),
                                              ctypes.POINTER(ClassInputs), ctypes.POINTER(ClassHost),
                                              ctypes.POINTER(AfterCall), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
    lib.mu_hp_mount_class_step.argtypes = [ctypes.POINTER(vh.Helpers), ctypes.c_int32, ctypes.POINTER(ClassInputs),
                                           ctypes.POINTER(ClassHost), ctypes.POINTER(AfterCall), ctypes.c_int32,
                                           ctypes.POINTER(ctypes.c_int32)]
    report['class'] = section_class(m, lib, rng, max(1, args.cases))
    report['seconds'] = round(time.time() - start, 1)
    cls = report['class']
    report['all_equal'] = (registry_ok and totals['equal'] == totals['cases'] and all(negatives.values()) and
                           all(v['equal'] == v['cases'] for k, v in cls.items() if isinstance(v, dict)) and
                           cls['negative_time'] > 0)
    print(json.dumps({k: v for k, v in report.items() if k not in ('bodies',)}, indent=1, default=str)[:6000])
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    return 0 if report['all_equal'] else 1


if __name__ == '__main__':
    sys.exit(main())
