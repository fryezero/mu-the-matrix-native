#!/usr/bin/env python3
"""RENDER-WORLDS-Q2 against pinned instructions: Ferea's visual slot 0x00de6405 and the class slot 0x10 of the
render pass's draw-first predicate.

ferea_visual:

The family compares AL, all 0x3d8 OBJECT bytes, the ordered recorded calls (CreateParticle, CreateSprite,
CreateEffect with its constant arguments asserted, TransformPosition with the bone index and local vector) and the
final MSVC RNG. Run as original instructions: the slot with its SEH frame, the vector helpers, the random range
0x011ff622, the CRT sine 0x009681bd (both ISA paths are not involved: SSE only), fabs 0x0184f8ff, the
std::string constructor/destructor (short-string buffer), the std::vector<std::string> constructor, push_back,
size, operator[] and destructor, and the named-bone lookup 0x0129f18a with the string compare, over a synthetic
model whose bone records (0x8c bytes, name at +0) hold the names the slot asks for at random indices among
decoys. Recording stubs: rand 0x01989721 (MSVC recurrence), the model container 0x00966cc4/0x00eaa8cf,
CreateParticle 0x0168fafd, CreateSprite 0x01692eb7, CreateEffect 0x013c0eaa, BMD::TransformPosition 0x012b6ef1
(a deterministic position per bone and local vector), timeGetTime (a code hook at the import call), and the
allocator under push_back (CRT malloc 0x019a4da0 as a bump allocator, free 0x0191c490 recorded; every block must
be freed again). A model without the named bone faults in the client (TransformPosition of a null matrix) and is not
sampled; the C refuses such objects before any request (portable test).

class_first: the slot 0x10 of the class of a sampled world (the twelve overrides of worlds 134..145 and the base
0x00d5cbc9 of the other classes; vtables from the pinned factory, scripts/world_handler_coverage.py) against
mu_class_first (zero for worlds it does not own), with TestFrustrum2D 0x016ccce7 run as original instructions over
a random frustum polygon and scene state. AL and all OBJECT bytes are compared.

render_first: the whole predicate 0x017fcd18 for the worlds that reach its default chain with every chain test false
(all classes' worlds outside the predicate's own cases, 0x27, 0x3f, 0x52..0x5a, 0x74..0x78, 0x7b..0x82), with the
manager singleton 0x00ea594b stubbed as a manager whose +0x10 is a handler with the world's class vtable (none for
unregistered worlds) and the singleton 0x009a6ef3 as a zero block; everything else runs as original instructions.
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
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ECX
import actor_machine as am
import validate_object_render as v
import validate_worlds_q as q
import pins
ROOT = Path(__file__).resolve().parents[1]
BODIES = {'ferea_visual': (0xde6405, 0xde8a10), 'render_first': (0x17fcd18, 0x17fe909)}
FIRST_SLOTS = {134: (0xd83dd1, 0xd83fd8), 135: (0xe3a304, 0xe3a3af), 136: (0xd935b4, 0xd93695),
               137: (0xe08c53, 0xe08c60), 138: (0xe05882, 0xe059c2), 139: (0xd9c11b, 0xd9c128),
               140: (0xd99f69, 0xd99f76), 141: (0xe4beaa, 0xe4bf72), 142: (0xe67005, 0xe67293),
               143: (0xe0e1fa, 0xe0e48b), 144: (0xe46042, 0xe46437), 145: (0xd752ad, 0xd7556d),
               'base': (0xd5cbc9, 0xd5cbd6)}   # bodies with their jump tables (138, 142, 143)
OWN_CASES = {0x5c, 0x38, 0, 2, 0x21, 0x25, 0x33, 0x39, 0x3a, 0x49, 0x4a, 0x5b, 0x71, 0x64, 0x65, 0x6e, 0x6f, 0x70,
             0x7a, 0x83, 0x84, 0x85}   # 0x017fcd18's own world cases (not modelled)
CHAIN = {0x27, 0x3f} | set(range(0x52, 0x5b)) | set(range(0x74, 0x79)) | set(range(0x7b, 0x83))
MANAGER, HANDLER_OBJECT, SINGLETON = 0x41040000, 0x41041000, 0x41042000
machine_data = None   # the pinned data section (vtables), set by main
HELPERS = {'named_bone': (0x129f18a, 0x129f24f)}
PARTICLE, SPRITE, EFFECT, BONE = 0x168fafd, 0x1692eb7, 0x13c0eaa, 0x12b6ef1
NEW, FREE = 0x19a4da0, 0x191c490
TIME_CALL = (0xde6557, 0xde655d)   # Ferea visual: call dword ptr [0x01a7c9a4] (timeGetTime)
BONE_TABLE, HEAP = 0x41020000, 0x41030000
BONE_RECORD = 0x8c
NAMES = {17: ['mansionA007'], 36: ['e01', 'e02', 'e03', 'e04', 'e05', 'e06'],
         75: ['Point02', 'Point03', 'objSphere002'], 81: ['Point02', 'Point03', 'objSphere002'],
         87: ['Bone21', 'Bone01'], 95: ['e01', 'e02', 'e04', 'e03', 'e05', 'e06', 'e08', 'e07'],
         123: ['Crowd01'], 129: ['Bone02'], 148: ['E01']}
DECOYS = ['e1', 'e0', 'e010', 'E02', 'e01 ', 'Bone2', 'Bone021', 'Point2', 'Crowd', 'crowd01', 'mansionA00',
          'mansionA0077', 'Bip01', 'Bone03', 'objSphere001', 'E01', 'e01', 'Bone01', '']
TYPES = [6, 9, 17, 28, 32, 33, 36, 71, 72, 75, 81, 87, 95, 123, 128, 129, 130, 140, 141, 142, 148,
         0, 1, 5, 7, 10, 34, 35, 37, 82, 131, 147, 149, 255, -1, 2147483647, -2147483648]
# first-rand residue that opens each branch: (modulus of rand() in rand_range(0, hi, 1), value)
OPEN = {9: (11, 0), 28: (5, 0), 32: (5, 0), 33: (5, 0), 71: (5, 0), 130: (5, 0), 128: (35, 0), 140: (2, 0),
        142: (3, 0), 81: (2, 1), 75: (2, 1)}
Inputs, BONE_FN, INDEX_FN = q.Inputs, q.BONE_FN, q.INDEX_FN


def bind(lib):
    d = lib.dll
    d.mu_class_first.argtypes = [C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float), C.c_int32]
    d.mu_class_first.restype = C.c_int
    d.mu_class_first_owned.argtypes = [C.c_int32]
    d.mu_class_first_owned.restype = C.c_int
    d.mu_ferea_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.POINTER(Inputs), C.POINTER(v.Log)]
    d.mu_ferea_visual.restype = C.c_int
    return lib


def position(k, local):
    return tuple(v.f32(local[n] + k * (n + 1) * 17 + 3) for n in range(3))


def bone_table(g, typ):
    """Bone names: the type's names at distinct random indices among decoys (first match wins in both)."""
    wanted = NAMES.get(typ, [])
    count = g.randrange(max(len(wanted), 1), 48)
    names = [g.choice(DECOYS + ['Bone%02d' % g.randrange(40)]) for _ in range(count)]
    names = [x for x in names]
    slots = g.sample(range(count), len(wanted))
    for name, slot in zip(wanted, slots):
        names[slot] = name
    if g.random() < 0.3 and wanted:   # a later duplicate of a wanted name: the first index is used
        names.append(g.choice(wanted))
    return names


def seed_for(g, modulus, value):
    want = g.randrange(modulus) if value is None else value
    while True:
        seed = g.getrandbits(32)
        if v.MsvcRand(seed)() % modulus == want:
            return seed


def family(machine, lib, name, cases):
    g = random.Random('worlds-q2-' + name)
    tally = v.Tally(name)
    for n in range(cases):
        typ = TYPES[n % len(TYPES)] if n % 7 else g.randrange(-3, 160)
        if n % 3 == 1:
            typ = g.choice(list(NAMES) + list(OPEN))
        world = g.choice([112, 112, 112, 111, 0])
        null_object = n % 41 == 40
        present = n % 13 != 0
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        v.put_i(raw, 0x64, g.choice([-2, -1, 0, 1, 5, 100, 2147483647, g.randrange(-10**6, 10**6)]))
        v.put_f(raw, 0xa0, v.f32(g.choice([1.0, 0.0, -1.0, 2.5, 0.75, 1e10, math.nan, g.uniform(0, 4)])))
        v.put_f(raw, 0x16c, v.f32(g.choice([0.0, 90.0, -45.0, 180.0, 1e9, math.nan, g.uniform(-720, 720)])))
        if n % 17 == 0:
            struct.pack_into('<I', raw, 0x158 + 4 * g.randrange(3), g.choice([0x80000000, 0x7fc00000, 0xff800000]))
        time = v.f32(g.choice([0.0, -0.0, 1000.0, -1000.0, 3599.9, 3600.0, 2147483520.0, 3e9, -3e9, 1e12,
                               math.nan, g.uniform(-1e6, 1e6), g.uniform(0, 1e5)]))
        now = g.choice([0, 29, 30, 99, 100, 129, g.getrandbits(32)])
        state = g.choice([0, 1, 2, 3, 3, 2, -1, 7])
        seed = g.getrandbits(32)
        if typ in OPEN and g.random() < 0.6:
            seed = seed_for(g, *OPEN[typ])
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        names = bone_table(g, typ)
        table = bytearray()
        for label in names:
            record = bytearray(b'\xcc' * BONE_RECORD)
            record[:33] = label.encode().ljust(33, b'\0')[:33]
            table += record
        model = bytearray(0x100)
        struct.pack_into('<h', model, 0x22, len(names))
        struct.pack_into('<I', model, 0x2c, BONE_TABLE)
        handler = bytearray(0x100)
        struct.pack_into('<iI', handler, 0x48, state, 0)
        calls, heap = [], {'next': HEAP, 'live': set(), 'allocated': 0}

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6] in (0, v.OBJECTS) and a[7] == 0, a
            calls.append((PARTICLE, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0

        def sprite(m):
            a = [m.argument(k) for k in range(9)]
            assert a[4] == v.OBJECTS and a[6:8] == [0, 4] and v.read_vec(m, a[8]) == (1, 1, v.bits(1.0)), a
            calls.append((SPRITE, 0, a[0]) + v.read_vec(m, a[1]) + (a[2],) + v.read_vec(m, a[3]) + (a[5], 1, 0, 4))
            return 0

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == 0 and a[6:10] == [0xffffffff, 0, 0, 0] and a[11:] == [0xffffffff, 0, 0], a
            calls.append((EFFECT, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], 0, a[10]))
            return 0

        def bone(m):
            a = [m.argument(k) for k in range(4)]
            assert m.uc.reg_read(UC_X86_REG_ECX) == v.MODEL
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + k * 0x30 and 0 <= k < len(names) and a[3] == 0, a
            local = tuple(struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12))))
            calls.append(('bone', k) + tuple(v.bits(x) for x in local))
            m.uc.mem_write(a[2], v.pack_f(*position(k, local)))
            return (0, 16)

        def new(m):   # operator new(size): 16-byte aligned bump blocks
            size = m.argument(0)
            assert 0 < size <= 0x1000, size
            address = heap['next']
            heap['next'] += (size + 15) & ~15
            heap['live'].add(address)
            heap['allocated'] += 1
            return address

        def free(m):
            address = m.argument(0)
            assert address in heap['live'], hex(address)
            heap['live'].remove(address)
            return 0

        def lookup(m):
            assert m.argument(0) == struct.unpack_from('<I', raw, 0x5c)[0]
            return (v.MODEL, 4)

        regs = v.global_regions(world, 6, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
            am.defined_region('cookie', q.COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            am.defined_region('isa', q.ISA, struct.pack('<I', 2 * (n % 2)), writable=False),
            am.defined_region('model', v.MODEL, bytes(model)),
            am.defined_region('bones', BONE_TABLE, bytes(table), writable=False),
            am.defined_region('heap', HEAP, bytes(0x4000)),
            am.defined_region('handler', q.HANDLER, bytes(handler))])
        stubs = {PARTICLE: particle, SPRITE: sprite, EFFECT: effect, BONE: bone, NEW: new, FREE: free,
                 0x1989721: lambda m: rnd(), 0x966cc4: lambda m: v.FAKE, 0xeaa8cf: lookup}

        def now_hook(u, address, size, ignored):
            u.reg_write(UC_X86_REG_EAX, now)
            u.reg_write(UC_X86_REG_EIP, TIME_CALL[1])
        hook = machine.uc.hook_add(UC_HOOK_CODE, now_hook, begin=TIME_CALL[0], end=TIME_CALL[0])
        machine.uc.ctl_flush_tb()
        try:
            result = v.run(machine, BODIES[name][0], [0 if null_object else v.OBJECTS, v.MODEL if present else 0],
                           regs, stubs, ecx=q.HANDLER, cleanup=8)
        finally:
            machine.uc.hook_del(hook)
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()

        def bone_cb(ctx, k, local, out):
            local = tuple(local[:3])
            ccalls.append(('bone', k) + tuple(v.bits(x) for x in local))
            for i, value in enumerate(position(k, local)):
                out[i] = value

        def index_cb(ctx, label):
            label = label.decode()
            return names.index(label) if label in names else -1
        ccalls = []
        ch = q.Handler(state, None, 1, None)
        inputs = Inputs(world, time, 0.0, now, (C.c_float * 3)(), (C.c_int32 * 2)(), q.ACTIONS_FN(0),
                        v.RAND_FN(lambda ctx: crnd()), BONE_FN(bone_cb), None, C.pointer(ch), INDEX_FN(index_cb))
        handled = lib.dll.mu_ferea_visual(None if null_object else co, 0, int(present), C.byref(inputs),
                                          C.byref(log))
        # the C reports its bone transforms through the callback, in order with the recorded requests
        merged, events, bi = [], v.log_events(log), 0
        c_all = ccalls
        orig_requests = [c for c in calls if c[0] != 'bone']
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        orig_bones = [c for c in calls if c[0] == 'bone']
        ok = (not diff and handled == (result['eax'] & 255) and orig_requests == events and orig_bones == c_all and
              rnd.seed == crnd.seed and not heap['live'])
        tally.count('type ' + str(typ))
        tally.count('world ' + str(world))
        tally.count('null object', int(null_object))
        tally.count('model absent', int(not present))
        tally.count('requests', len(orig_requests))
        tally.count('bone transforms', len(orig_bones))
        tally.count('heap blocks', heap['allocated'])
        for c in orig_requests:
            tally.count('call ' + hex(c[0]) + ' ' + hex(c[2]))
        tally.add(ok, {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': result['eax'] & 255,
                       'c_al': handled, 'calls': orig_requests[:3], 'c': events[:3], 'bones': orig_bones[:3],
                       'c_bones': c_all[:3], 'rng_equal': rnd.seed == crnd.seed, 'leak': len(heap['live'])})
    return tally.report()


def class_vtables(text, data):
    import world_handler_coverage as cov
    out = {}
    for row in cov.inventory(text, data):
        for w in row['worlds']:
            out[w] = int(row['vtable'], 16)
    return out


def listed_types(machine, world, start):
    """Sampling aid: the types 0..300 for which the original slot reaches TestFrustrum2D (stubbed to yes)."""
    out = []
    for typ in range(301):
        raw = bytearray(v.OBJ_SIZE)
        raw[0] = 1
        v.put_i(raw, 0x5c, typ)
        r = v.run(machine, start, [v.OBJECTS], v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS,
                  bytes(raw))]), {0x16ccce7: lambda m: 1}, ecx=v.FAKE, cleanup=4)
        if r['ok'] and r['eax'] & 255:
            out.append(typ)
    return out


def first_family(machine, lib, name, cases, vtables):
    g = random.Random('worlds-q2-' + name)
    tally = v.Tally(name)
    listed = {w: listed_types(machine, w, FIRST_SLOTS[w][0]) for w in range(134, 146)}
    # a sweep first: every listed type of every override (and, for class_first, its neighbours) inside the polygon
    sweep = [(w, t + d) for w in range(134, 146) for t in listed[w]
             for d in ((-1, 0, 1) if name == 'class_first' else (0,))]
    worlds = sorted(vtables)
    chain_worlds = [w for w in worlds if w not in OWN_CASES and w not in CHAIN] + [146, 200, 255]
    for n in range(cases):
        if name == 'class_first':
            world = g.choice(list(range(134, 146)) * 3 + worlds)
        else:
            world = g.choice(list(range(134, 146)) * 2 + chain_worlds)
        typ = g.choice(list(range(-2, 205)) + [255, 300, 1000, -1, 2147483647])
        if listed.get(world) and n % 2:
            typ = g.choice(listed[world])
        if n < len(sweep):
            world, typ = sweep[n]
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        raw[0] = 1 if n < len(sweep) else g.choice([0, 1, 1, 1])
        v.put_f(raw, 0xc0, v.f32(g.choice([-30.0, -300.0, -800.0, 0.0, 50.0, -1e9, math.nan, g.uniform(-2000, 100)])))
        x2d, y2d = v.frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4
        spread = 0 if n < len(sweep) else 30 if n % 4 == 0 else 6   # mostly inside the polygon: draw-first answers
        v.put_f(raw, 0x158, v.f32((cx + g.uniform(-spread, spread)) * 100), v.f32((cy + g.uniform(-spread, spread)) * 100))
        if n % 19 == 0:
            struct.pack_into('<I', raw, 0x158 + 4 * g.randrange(2), g.choice([0x7fc00000, 0xff800000, 0x80000000]))
        scene = g.choice([6, 6, 6, 5, 2, 1, 4])
        vt = vtables.get(world)
        regs = v.global_regions(world, scene, [
            am.defined_region('object', v.OBJECTS, bytes(raw)),
            am.defined_region('x2d', v.X2D, v.pack_f(*x2d), writable=False),
            am.defined_region('y2d', v.Y2D, v.pack_f(*y2d), writable=False),
            am.defined_region('manager', MANAGER, struct.pack('<5I', 0, 0, 0, 0, HANDLER_OBJECT if vt else 0),
                              writable=False),
            am.defined_region('handler', HANDLER_OBJECT, struct.pack('<I', vt or 0) + bytes(0x7c), writable=False),
            am.defined_region('singleton', SINGLETON, bytes(0x100), writable=False)])
        if name == 'class_first':
            if vt is None:
                continue
            start = struct.unpack_from('<I', machine_data, vt + 0x10 - 0x1a7c000)[0]
            result = v.run(machine, start, [v.OBJECTS], regs, {}, ecx=HANDLER_OBJECT, cleanup=4)
        else:
            result = v.run(machine, BODIES['render_first'][0], [v.OBJECTS], regs,
                           {0xea594b: lambda m: (MANAGER, 0), 0x9a6ef3: lambda m: (SINGLETON, 0)})
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n, 'type': typ, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        xs, ys = (C.c_float * 4)(*x2d), (C.c_float * 4)(*y2d)
        d = lib.dll
        answer = d.mu_class_first(co, world, xs, ys, scene) if d.mu_class_first_owned(world) else 0
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result['regions']['object'][k]]
        al = result['eax'] & 255
        tally.count('world ' + str(world))
        tally.count('answer ' + str(al))
        tally.count('range written', int(bytes(raw[0xc0:0xc4]) != bytes(result['regions']['object'][0xc0:0xc4])))
        tally.add(not diff and answer == al, {'case': n, 'type': typ, 'world': world, 'diff': diff[:8], 'al': al,
                                              'c': answer})
    return tally.report()


F = 'ferea.c'
MUTANTS = [
    (F, 'if (!o || !model_present)\n        return 0;\n    const int32_t type',
     'if (!o || model_present < 0)\n        return 0;\n    const int32_t type', 'ferea_visual'),
    (F, 'phase < 30u', 'phase <= 30u', 'ferea_visual'),
    (F, 'ferea_zero(in, 10.0f)', 'ferea_zero(in, 9.0f)', 'ferea_visual'),
    (F, '0.579999983f, 0.75999999f, 100', '0.579999983f, 0.75999999f, 10', 'ferea_visual'),
    (F, 'b[2] + 25.0f', 'b[2] + 20.0f', 'ferea_visual'),
    (F, 'white, 0xa, s);', 'white, 0xb, s);', 'ferea_visual'),
    (F, 'q_sprite(log, index, 0x7ef7, top, 2.0f * scale', 'q_sprite(log, index, 0x7ef7, top, scale', 'ferea_visual'),
    (F, 'pos[2] + 110.0f', 'pos[2] + 100.0f', 'ferea_visual'),
    (F, '{0.0299999993f, 0.0f, 0.0599999987f}', '{0.0299999993f, 0.0f, 0.0500000007f}', 'ferea_visual'),
    (F, '{"e01", "e02", "e03", "e04", "e05", "e06", NULL}', '{"e01", "e02", "e03", "e04", "e05", NULL}',
     'ferea_visual'),
    (F, '* 0.0002 * (double)k', '* 0.0002 * (double)(k + 1)', 'ferea_visual'),
    (F, '(sine < 0.0f ? -sine : sine)', 'fabsf(sine)', 'ferea_visual'),
    (F, 'q_sprite(log, index, 0x7f26, b, 1.5f, dim', 'q_sprite(log, index, 0x7f26, b, 1.0f, dim', 'ferea_visual'),
    (F, 'if (!ferea_zero(in, 1.0f))', 'if (ferea_zero(in, 1.0f))', 'ferea_visual'),
    (F, 'type == 81 ? orange : blue', 'type == 75 ? orange : blue', 'ferea_visual'),
    (F, 'q_sprite(log, index, 0x7ef7, b, 1.5f, blue', 'q_sprite(log, index, 0x7ef7, b, 1.5f, orange',
     'ferea_visual'),
    (F, 'b[2] + 30.0f}, at', 'b[2] + 45.0f}, at', 'ferea_visual'),
    (F, 'at[3] = {b[0], b[1], b[2]}', 'at[3] = {b[0], b[1], b[2] + 30.0f}', 'ferea_visual'),
    (F, '"e05", "e06", "e08", "e07"', '"e05", "e06", "e07", "e08"', 'ferea_visual'),
    (F, 'up[3] = {b[0], b[1], b[2] + 15.0f};', 'up[3] = {b[0], b[1], b[2] + 16.0f};', 'ferea_visual'),
    (F, 'ferea_state == 3 || in->handler->ferea_state == 2', 'ferea_state == 3', 'ferea_visual'),
    (F, '0.546000004f, 0.713999987f, 1000', '0.546000004f, 0.713999987f, 100', 'ferea_visual'),
    (F, 'b[2] + 40.0f', 'b[2] + 45.0f', 'ferea_visual'),
    (F, 'ferea_zero(in, 34.0f)', 'ferea_zero(in, 33.0f)', 'ferea_visual'),
    (F, '{w / 1.70000005f, w, w}', '{w, w, w / 1.70000005f}', 'ferea_visual'),
    (F, 'angle[2] * 5.0f', 'angle[1] * 5.0f', 'ferea_visual'),
    (F, 'q_particle(log, index, 0x801a, pos, angle, white, 2', 'q_particle(log, index, 0x801a, pos, angle, white, 3',
     'ferea_visual'),
    (F, 'q_particle(log, index, 0x801c, pos, angle, white, 4, scale, 0);',
     'q_particle(log, index, 0x801c, pos, angle, white, 4, scale, 1);', 'ferea_visual'),
    (F, '% 3600) * 0.100000001f', '% 3000) * 0.100000001f', 'ferea_visual'),
    (F, 'l, -r);', 'l, r);', 'ferea_visual'),
    (F, 'b[2] += 15.0f;', 'b[2] += 16.0f;', 'ferea_visual'),
    (F, '+ 0.300000012f + 0.5f, 0.400000006f}', '+ 0.300000012f + 0.400000006f, 0.400000006f}', 'ferea_visual'),
    (F, 'case 140:\n        if (ferea_zero(in, 1.0f))', 'case 140:\n        if (!ferea_zero(in, 1.0f))',
     'ferea_visual'),
    (F, 'case 6:\n        return 1;', 'case 6:\n        return 0;', 'ferea_visual'),
]

W = 'world_first_visual.c'
MUTANTS += [
    (W, 'if (world == 142)\n        mu_obj_set_f32(o, MU_OBJF_RANGE, -800.0f);', '', 'class_first'),
    (W, 'MU_OBJF_RANGE, -800.0f', 'MU_OBJF_RANGE, -700.0f', 'class_first'),
    (W, '{1, 3, 4, 6,', '{3, 4, 6,', 'class_first'),
    (W, '{23, 38, 59, 90, 102, 106, -1}', '{23, 38, 59, 90, 102, 105, -1}', 'class_first'),
    (W, '106, 134, 135, 179, -1}', '106, 134, 135, 178, -1}', 'class_first'),
    (W, '\n                                    173, -1};', '\n                                    172, -1};', 'class_first'),
    (W, '125, 127, 128, 199, -1}', '125, 127, 128, 198, -1}', 'class_first'),
    (W, '158, 160, 161, 165, -1}', '158, 160, 161, -1}', 'class_first'),
    (W, '152, 156, 166, 168, -1}', '152, 156, 166, -1}', 'class_first'),
    (W, '153, 181, 183, 200, -1}', '153, 181, 183, 201, -1}', 'class_first'),
    (W, '160, 161, 165, 166, -1}', '160, 161, 165, 167, -1}', 'class_first'),
    (W, ' || (world == 145 && !o[MU_OBJF_LIVE])', '', 'class_first'),
    (W, 'MU_OBJF_POSITION) * 0.01f', 'MU_OBJF_POSITION) * 0.1f', 'class_first'),
    (W, 'world >= 134 && world <= 145', 'world >= 134 && world <= 144', 'render_first'),
    (W, 'MU_OBJF_POSITION + 4) * 0.01f', 'MU_OBJF_POSITION + 4) * 0.011f', 'render_first'),
    (W, 'case 138: return first_138;', 'case 137: return first_138;', 'render_first'),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=1000)
    ap.add_argument('--only', help='comma-separated families')
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    lib = bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}'))
    sha = lambda s, e: hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()
    global machine_data
    machine_data = data
    vtables = class_vtables(text, data)
    families = ['ferea_visual', 'class_first', 'render_first']
    names = [n for n in families if not a.only or n in a.only.split(',')]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)} for n, (s, e) in BODIES.items()},
              'helpers': {n: {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)} for n, (s, e) in HELPERS.items()},
              'first_slots': {str(w): {'start': hex(s), 'end': hex(e), 'sha256': sha(s, e)}
                              for w, (s, e) in FIRST_SLOTS.items()},
              'families': {}, 'mutants': []}
    run_family = lambda lib_, name: (family(machine, lib_, name, a.cases) if name == 'ferea_visual' else
                                     first_family(machine, lib_, name, a.cases * (2 if name == 'class_first' else 1),
                                                  vtables))
    for name in names:
        r = report['families'][name] = run_family(lib, name)
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='worlds-q2-') as tmp:
            for n, (file, old, new, name) in enumerate(MUTANTS):
                if name not in names:
                    continue
                dest = Path(tmp) / str(n)
                for directory in ('objects', 'terrain', 'model-codec', 'record-math', 'movement'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__', '*.d'))
                p = dest / 'objects' / file
                s = p.read_text()
                assert old in s, old
                p.write_text(s.replace(old, new, 1))
                mutated = bind(v.Library(v.build_library(dest)))
                r = run_family(mutated, name)
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
