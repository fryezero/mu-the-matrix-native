#!/usr/bin/env python3
"""RENDER-WORLDS-AFTER instruction comparisons (docs/research/client-worlds-after.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  after_pass       RenderObjects_AfterCharacter 0x016d6949 for every world -1..150: the world test (list,
                   predicates and the current handler's byte +5 through slot 8), sector/object loop, the
                   selector 0x017fe909 with the real class slot 0x14 (handler = a record carrying the class's
                   real vtable), the tower branch 0x009a645f, the world-2 level branch, counter and visibility.
  select           0x017fe909 alone, one object per case, all worlds (including 142's range writes).
  abyss_custom     custom render slot 0x38 of worlds 128..130 (type-7 action gate with rand, meshes, bodies).
  abyss_after      after render slot 0x3c of worlds 128..130.
  chain_predicates the world tests of every world-group hook CreateObject/MoveObject call before the world
                   manager, for worlds -1..200, against mu_world_chain_predicate.
  chain_noop       those hooks run whole where the C says none of their tests pass: no write, no answer.
  frame_time       the timing routine 0x012aeb2b up to 0x012aec9f (timeGetTime at its four call sites).
Leaves recorded: the after draw 0x016d6791, RenderBody 0x00966def, RenderMesh 0x00966e4a, rand 0x01989721,
the world manager 0x00ea594b (answers a harness record), 0x009a6ef3, 0x0139d89f, 0x00a00066.
"""
import argparse, ctypes as C, hashlib, json, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import world_handler_coverage as whc

ROOT = Path(__file__).resolve().parents[1]
BODIES = {'after_pass': (0x16d6949, 0x16d6e87), 'select': (0x17fe909, 0x17ff238),
          'abyss1_custom': (0xd5d2f6, 0xd5d564), 'abyss2_custom': (0xd5ef96, 0xd5f1f1),
          'abyss3_custom': (0xd606da, 0xd60948), 'abyss1_after': (0xd5d5ad, 0xd5d703),
          'abyss2_after': (0xd5f23a, 0xd5f390), 'abyss3_after': (0xd60991, 0xd60ae7),
          'timing': (0x12aeb2b, 0x12aeca4)}
CUSTOM = {128: 0xd5d2f6, 129: 0xd5ef96, 130: 0xd606da}
AFTER = {128: 0xd5d5ad, 129: 0xd5f23a, 130: 0xd60991}
BASE_VTABLE = 0x1aa517c
MGR, HANDLER, TOWER, HERO = 0x41020000, 0x41021000, 0x41022000, 0x41023000
LEVEL_OWNER = 0x01d1df1c
# hook -> (predicates, calling convention): 'c' cdecl(object), 't' thiscall(object) on FAKE
CHAIN = {0x9dafa8: ([0x9dacb8], 'c'), 0xdef3ac: ([], 'c'), 0xd8e18f: ([0x95fb7c], 'c'),
         0xdfbc3f: ([0xdfbbbb], 'c'), 0xd6200e: ([0xd61f81], 'c'), 0xdabeb4: ([0xdabe97], 'c'),
         0xe74a58: ([0xe74a3b], 'c'), 0xe7dcf4: ([0xe843df], 'c'), 0xe84530: ([0xe84513], 'c'),
         0xd53d53: ([0xd53d11], 't'), 0xd53d7d: ([0xd53d32], 't'), 0xdbba0c: ([0x95fba9], 't'),
         0xe30a02: ([0xe309a7, 0xe309d9], 'c'), 0xe5f617: ([0xe5f48a], 'c'),
         0xdef6fb: ([0x9b0418], 'c'), 0xd8e38c: ([0x95fb7c], 'c'), 0xdfbc92: ([0xdfbbbb], 'c'),
         0xd6202f: ([0xd61f81], 'c'), 0xdabed5: ([0xdabe97], 'c'), 0xe74ae0: ([0xe74a3b, 0xe7dcd7], 'c'),
         0xe7dd29: ([0xe843df], 'c'), 0xe845d0: ([0xe84513], 'c'), 0xd53da7: ([0xd53d11, 0xd53d32], 't'),
         0xdbba8c: ([0x95fba9], 't'), 0xe30b86: ([0xe309a7, 0xe309d9], 'c'), 0xe5f629: ([0xe5f48a], 'c')}
VOID_HOOKS = {0xe30a02, 0xe5f617}
ARG_PREDICATES = {0x9dacb8, 0x9b0418, 0x95fb7c}   # take the world as their argument
THIS_PREDICATES = {0xd53d11, 0xd53d32, 0x95fba9}
TIME_CALLS = (0x12aeb41, 0x12aeb6c, 0x12aeb9b, 0x12aec3a)


class AfterInputs(C.Structure):
    _fields_ = [('class_flag', C.c_uint8), ('tower_state', C.c_int32), ('master_class', C.c_uint8),
                ('level', C.c_int32)]


class FrameTime(C.Structure):
    _fields_ = [('started', C.c_uint8), ('base', C.c_uint32), ('next_base', C.c_uint32), ('now', C.c_uint32),
                ('prior', C.c_uint32), ('frames', C.c_int32), ('next_frames', C.c_int32), ('fps', C.c_float),
                ('world_time', C.c_float), ('frame_time', C.c_float), ('delta', C.c_int32)]


TIME_FN = C.CFUNCTYPE(C.c_uint32, C.c_void_p)


class Library(v.Library):
    def __init__(self, path, frame_path):
        super().__init__(path)
        d = self.dll
        P, I, F, L = C.c_void_p, C.c_int32, C.c_float, C.POINTER(v.Log)
        d.mu_world_after_pass_ex.argtypes = [C.POINTER(v.World), C.POINTER(v.RenderInputs), C.POINTER(AfterInputs),
                                             C.POINTER(I), L]
        d.mu_world_after_select.argtypes = [P, C.POINTER(v.RenderInputs)]
        d.mu_abyss_custom.argtypes = [I, P, I, I, F, v.RAND_FN, P, L]
        d.mu_abyss_after.argtypes = [I, P, I, I, L]
        d.mu_world_chain_predicate.argtypes = [C.c_uint32, I]
        d.mu_world_class_after.argtypes = [I]
        self.frame = C.CDLL(str(frame_path))
        self.frame.mu_frame_time_init.argtypes = [C.POINTER(FrameTime)]
        self.frame.mu_frame_time_update.argtypes = [C.POINTER(FrameTime), TIME_FN, P]


def class_vtables(text, data):
    out = {}
    for row in whc.inventory(text, data):
        for w in row['worlds']:
            out[w] = int(row['vtable'], 16)
    return out


def handler_regions(world, vtables, flag, g, force=False):
    """The world manager (0x00ea594b) and its current handler (+0x10)."""
    vt = vtables.get(world)
    mgr = bytearray(0x20)
    if vt is None and not force and g.random() < 0.3:
        handler = None
    else:
        handler = bytearray(0x40)
        struct.pack_into('<I', handler, 0, vt if vt is not None else BASE_VTABLE)
        handler[5] = flag
        struct.pack_into('<I', mgr, 0x10, HANDLER)
    regions = [am.defined_region('manager', MGR, bytes(mgr), writable=False)]
    if handler is not None:
        regions.append(am.defined_region('handler', HANDLER, bytes(handler), writable=False))
    return regions, (flag if handler is not None else 0)


SELECT_TYPES = [0x13, 0x19, 0x29, 0x59, 0x5f, 0x74, 0x4c, 0x10, 0x43, 0x44, 0x1b, 0x3c, 0x3d, 0x3e, 6, 0x11,
                0x96, 0x2b, 0x33, 0x4b, 0x51, 0x57, 0x72, 0x99, 0x9b, 0x6a, 0x58, 0x86, 0x17, 0x28, 0x2c, 0xb2,
                0, 0x18, 0x2d, 0x1f, 0x20, 0x36, 0x39, 0x3e, 0xa2, 0xab, 0xae, 0xc5, 4, 0x1c, 0x21, 0x85, 0x40,
                0x2e, 0x31, 0x88, 0x8c, 0x8e, 0x4be, 0x64]


def pick_world(g):
    r = g.random()
    if r < 0.35:
        return g.randrange(128, 146)
    if r < 0.85:
        return g.choice([-1, 2, 3, 8, 10, 0x21, 0x25, 0x27, 0x2d, 0x33, 0x36, 0x38, 0x39, 0x3a, 0x3f, 0x45, 0x4f,
                         0x50, 0x52, 0x5b, 0x5c, 0x5e, 0x62, 0x6e, 0x6f, 0x70, 0x71, 0x7a, 0x7b, 0x7f, 0x80, 0x82,
                         0x83, 0x84, 0x85, 0x86, 0x87, 0x8d])
    return g.randrange(-1, 151)


WORLD_TYPES = {3: [0x13], 0x21: [0x19, 0x29], 0x36: [0x19, 0x29], 0x25: [0x59, 0x5f, 0x74], 0x33: [0x59],
               0x39: [0x4c], 0x3a: [0x4c], 0x3f: [0x10, 0x43, 0x44], 0x52: [0x10, 0x43, 0x44],
               0x5b: [0x1b, 0x3c, 0x3d, 0x3e], 0x5c: [0x1b, 0x3c, 0x3d, 0x3e], 0x6e: [6, 0x11, 0x96],
               0x6f: [6, 0x11, 0x96], 0x70: [0x2b, 0x33, 0x4b, 0x51, 0x57, 0x72, 0x99, 0x9b], 0x71: [0x6a],
               0x7a: [0x58], 0x7b: [0x86], 0x7f: [0x86], 0x80: [0x17, 0x28, 0x29, 0x2c, 0x26],
               0x81: [0x17, 0x28, 0x29, 0x2c], 0x82: [0x17, 0x28, 0x29, 0x2c], 0x83: [0xb2, 0x6a], 0x85: [6, 7],
               134: [0, 1], 136: [0x18], 138: [0x2d], 141: [0x1f, 0x20], 142: [0x36, 0x3e, 0xa3, 0xab, 0xc5, 0x40],
               143: [0, 4, 0x1c, 0x21, 0x72, 0x85], 144: [0x40, 0x20], 145: [0x13, 0x2d, 0x89, 0x8e], 2: [0x64],
               0x27: [0x4be]}


def object_fields(g, cx, cy, world=None, spread=45):
    types = WORLD_TYPES.get(world)

    def fields(g, o, k):
        o[0] = g.choice([0, 1, 1, 1])
        o[0xa] = g.choice([0, 1, 1, 2])
        o[0xb] = g.choice([0, 1])
        v.put_i(o, 0x5c, g.choice(types) if types and g.random() < 0.5 else
                g.choice(SELECT_TYPES) if g.random() < 0.8 else g.randrange(0, 300))
        v.put_f(o, 0x158, v.f32((cx + g.uniform(-spread, spread)) * 100), v.f32((cy + g.uniform(-spread, spread)) * 100),
                v.f32(g.uniform(0, 300)))
        v.put_f(o, 0xc0, v.f32(g.choice([-30.0, -100.0, -428.571, g.uniform(-600, 50)])))
    return fields


def render_inputs(world, scene, top, x2d, y2d):
    xs, ys = (C.c_float * 4)(*x2d), (C.c_float * 4)(*y2d)
    i = v.RenderInputs(world, scene, top, xs, ys, v.ANSWER_FN(lambda c, k: 0), v.ANSWER_FN(lambda c, k: 0), None,
                       0.0)
    i._keep = (xs, ys)
    return i


def family_after_pass(machine, lib, ctx, g, cases):
    t = v.Tally('after_pass')
    for n in range(cases):
        world = pick_world(g)
        forced = g.random() < 0.12   # worlds 10 (bias) and 2 (level branch) through an answering handler
        if forced:
            world = g.choice([2, 10, 0x27])
        scene = g.choice([3, 5, 6])
        top = 1 if g.random() < 0.1 else 0
        count = g.randrange(0, 50)
        x2d, y2d = v.frustum_polygon(g)
        objects, heads, nxt = v.object_list(g, count, object_fields(g, sum(x2d) / 4, sum(y2d) / 4, world))
        counter = g.choice([0, 5, 40, 41, 100])
        default_flag = 1 if 134 <= world <= 145 else 0
        flag = default_flag if g.random() < 0.7 else g.choice([0, 1])
        tower = g.choice([0, 1, 2, 3, 4, 5, 6, -1])
        master = g.choice([0, 1])
        level = g.choice([0x34, 0x35, 0x4f, 0x50]) if world == 2 else g.choice([0, 0x35, 400])
        if forced:
            flag = 1
        mregions, flag = handler_regions(world, ctx['vtables'], flag, g, force=forced)
        calls = []
        index = lambda a: (a - v.OBJECTS) // 0x400

        def draw(m):
            calls.append((0x016d6791, index(m.argument(0))) + tuple(m.argument(i) for i in range(1, 4)))
            return 0
        hero = bytearray(0x40)
        hero[0x12] = g.randrange(0, 8)
        stubs = {0x016d6791: draw, 0x00db747f: lambda m: v.FAKE, 0x00ea594b: lambda m: MGR,
                 0x009a6ef3: lambda m: TOWER, 0x0139d89f: lambda m: master, 0x00a00066: lambda m: level}
        tower_rec = bytearray(0x100)
        struct.pack_into('<i', tower_rec, 0x7c, tower)
        regions = v.global_regions(world, scene, [
            am.defined_region('sectors', v.SECTORS, bytes(v.sector_bytes(heads))),
            am.defined_region('x2d', v.X2D, v.pack_f(*x2d), writable=False),
            am.defined_region('y2d', v.Y2D, v.pack_f(*y2d), writable=False),
            am.defined_region('top-view', v.TOP_VIEW, bytes([top]), writable=False),
            am.defined_region('counter', v.COUNTER, struct.pack('<i', counter)),
            am.defined_region('fake', v.FAKE, v.fake_object(), writable=False),
            am.defined_region('tower', TOWER, bytes(tower_rec), writable=False),
            am.defined_region('hero-ptr', v.HERO_PTR, struct.pack('<I', HERO), writable=False),
            am.defined_region('hero', HERO, bytes(hero), writable=False),
            am.defined_region('level-owner', LEVEL_OWNER, struct.pack('<I', 0), writable=False)] + mregions +
            [am.defined_region(f'object{k}', v.OBJECTS + 0x400 * k, bytes(o)) for k, o in enumerate(objects)])
        result = v.run(machine, 0x016d6949, [], regions, stubs)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world}, stop)
            continue
        w, bufs = v.c_world(objects, heads, nxt)
        inputs = render_inputs(world, scene, top, x2d, y2d)
        a = AfterInputs(flag, tower, 1 if master == 1 else 0, level)
        cc = C.c_int32(counter)
        log = v.new_log()
        lib.dll.mu_world_after_pass_ex(C.byref(w), C.byref(inputs), C.byref(a), C.byref(cc), C.byref(log))
        native = v.log_events(log)
        table = result['regions']['sectors']
        blocks = all(table[s * 16 + 0xc] == w.block_visible[s] for s in range(256))
        objs = all(result['regions'][f'object{k}'] == bufs[k].raw[:v.OBJ_SIZE] for k in range(count))
        counter_ok = struct.unpack('<i', result['regions']['counter'])[0] == cc.value
        gate = result['regions']['counter'] != struct.pack('<i', counter)
        t.count('gate open' if gate else 'gate closed')
        t.count('class worlds' if 128 <= world <= 145 else 'other worlds')
        t.count('drawn', len(calls))
        t.add(calls == native and blocks and objs and counter_ok,
              {'case': n, 'world': world, 'flag': flag, 'calls': calls[:4], 'c': native[:4], 'blocks': blocks,
               'objects': objs, 'counter': counter_ok})
    return t


def family_select(machine, lib, ctx, g, cases):
    t = v.Tally('select')
    for n in range(cases):
        world = pick_world(g) if g.random() < 0.75 else g.choice([0x25, 0x80, 0x85, 134, 136, 138, 141, 142, 143, 144, 145])
        scene = g.choice([3, 5, 6])
        x2d, y2d = v.frustum_polygon(g)
        o = bytearray(v.poison_object(g))
        object_fields(g, sum(x2d) / 4, sum(y2d) / 4, world, g.choice([10, 45]))(g, o, 0)
        mregions, _ = handler_regions(world, ctx['vtables'], 1 if 134 <= world <= 145 else 0, g)
        if 134 <= world <= 145 and 'handler' not in [r.name for r in mregions if hasattr(r, 'name')]:
            pass
        regions = v.global_regions(world, scene, [
            am.defined_region('x2d', v.X2D, v.pack_f(*x2d), writable=False),
            am.defined_region('y2d', v.Y2D, v.pack_f(*y2d), writable=False),
            am.defined_region('object', v.OBJECTS, bytes(o))] + mregions)
        result = v.run(machine, 0x017fe909, [v.OBJECTS], regions, {0x00ea594b: lambda m: MGR})
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        inputs = render_inputs(world, scene, 0, x2d, y2d)
        answer = lib.dll.mu_world_after_select(co, C.byref(inputs))
        client = result['eax'] & 0xff
        t.count(f'answer {client}')
        t.add(client == (1 if answer else 0) and result['regions']['object'] == co.raw[:v.OBJ_SIZE],
              {'case': n, 'world': world, 'type': struct.unpack_from('<i', o, 0x5c)[0], 'client': client,
               'c': answer})
    return t


def abyss_object(g, typ):
    o = bytearray(v.poison_object(g))
    v.put_i(o, 0x5c, typ)
    struct.pack_into('<H', o, 0x2a, g.choice([0, 0, 1, 1, 2, g.randrange(0, 0x10000)]))
    v.put_f(o, 0xd0, v.f32(g.choice([0.0, 18.9, 19.0, 19.5, 19.969, 19.97, 20.0, g.uniform(0, 30)])))
    v.put_i(o, 0x74, g.choice([-1, 0, 1, 2, 3, 0x7fffffff, -0x80000000, 16777217, g.randrange(-2**31, 2**31)]))
    v.put_i(o, 0x68, g.choice([-1, -2, 0, 1, 2]))
    for off in (0xa8, 0xac, 0xb0, 0xdc):
        v.put_f(o, off, v.f32(g.uniform(-2, 2)))
    return o


ABYSS_TYPES = [7, 7, 7, 7, 7, 7, 0x17, 0x26, 0x28, 0x29, 0x2c, 0x32, 0x34, 0x34, 0x27, 0, 0x16, 0x42]


def recorder(calls, address):
    def stub(m):
        calls.append((address, 0) + tuple(m.argument(k) for k in range(8)))
        return (0, 32)
    return stub


def abyss_family(machine, lib, g, cases, after):
    t = v.Tally('abyss_after' if after else 'abyss_custom')
    for n in range(cases):
        cls = (128, 129, 130)[n % 3]
        world = cls if g.random() < 0.85 else g.choice([128, 129, 130, 0, 0x50])
        typ = g.choice(ABYSS_TYPES) if g.random() < 0.9 else g.randrange(0, 200)
        o = abyss_object(g, typ)
        time = v.f32(g.choice([0.0, g.uniform(0, 100000), g.uniform(0, 1e7)]))
        seed = g.randrange(2**32)
        a, b = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []
        stubs = {0x966def: recorder(calls, 0x966def), 0x966e4a: recorder(calls, 0x966e4a), 0x1989721: lambda m: a()}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(0x100)),
                                              am.defined_region('time', v.TIME, v.pack_f(time), writable=False)])
        start = (AFTER if after else CUSTOM)[cls]
        result = v.run(machine, start, [v.OBJECTS, v.MODEL, 0], regions, stubs, ecx=v.FAKE, cleanup=12)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'cls': cls, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        log = v.new_log()
        if after:
            answer = lib.dll.mu_abyss_after(cls, co, 0, world, C.byref(log))
        else:
            answer = lib.dll.mu_abyss_custom(cls, co, 0, world, time, v.RAND_FN(lambda c: b()), None, C.byref(log))
        native = v.log_events(log)
        client = result['eax'] & 0xff
        same_answer = after or client == (1 if answer else 0)
        t.count(f'cls {cls} type {typ:#x}')
        t.add(calls == native and same_answer and result['regions']['object'] == co.raw[:v.OBJ_SIZE]
              and a.seed == b.seed,
              {'case': n, 'cls': cls, 'world': world, 'type': typ, 'client': calls, 'native': native,
               'answer': (client, answer), 'rand': (a.seed, b.seed)})
    return t


def family_abyss_custom(m, l, ctx, g, n):
    return abyss_family(m, l, g, n, False)


def family_abyss_after(m, l, ctx, g, n):
    return abyss_family(m, l, g, n, True)


def chain_worlds():
    return list(range(-1, 201))


def family_chain_predicates(machine, lib, ctx, g, cases):
    t = v.Tally('chain_predicates')
    predicates = sorted({p for ps, _ in CHAIN.values() for p in ps})
    for world in chain_worlds():
        for p in predicates:
            regions = v.global_regions(world, 6, [am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
            args = [world & 0xffffffff] if p in ARG_PREDICATES else []
            result = v.run(machine, p, args, regions, {}, ecx=v.FAKE if p in THIS_PREDICATES else 0)
            stop = v.stopped_reason(result)
            if stop:
                t.add(False, {'world': world, 'predicate': hex(p)}, stop)
                continue
            client = result['eax'] & 0xff
            native = lib.dll.mu_world_chain_predicate(p, world)
            if client:
                t.count('true')
            t.add(client == (1 if native else 0), {'world': world, 'predicate': hex(p), 'client': client,
                                                    'c': native})
    return t


def first_ret_cleanup(text, address):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    for ins in Cs(CS_ARCH_X86, CS_MODE_32).disasm(text[address - 0x401000:address - 0x401000 + 0x800], address):
        if ins.mnemonic == 'ret':
            return int(ins.op_str, 16) if ins.op_str else 0
    raise ValueError(hex(address))


def family_chain_noop(machine, lib, ctx, g, cases):
    t = v.Tally('chain_noop')
    for world in chain_worlds():
        for hook, (predicates, conv) in CHAIN.items():
            if any(lib.dll.mu_world_chain_predicate(p, world) for p in predicates):
                continue
            o = bytearray(v.poison_object(g))
            v.put_i(o, 0x5c, g.choice([0x1b, 0x1f, 0x25, 0x26, 0x27, 0x28, 0x35, 3, 9, g.randrange(0, 200)]))
            regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                                  am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
            cleanup = ctx['cleanup'][hook]
            result = v.run(machine, hook, [v.OBJECTS], regions, {}, ecx=v.FAKE if conv == 't' else 0,
                           cleanup=cleanup)
            stop = v.stopped_reason(result)
            if stop:
                t.add(False, {'world': world, 'hook': hex(hook)}, stop)
                continue
            answer = 0 if hook in VOID_HOOKS else result['eax'] & 0xff
            t.count('class worlds' if 57 <= world <= 145 else 'other worlds')
            t.add(answer == 0 and result['regions']['object'] == bytes(o),
                  {'world': world, 'hook': hex(hook), 'answer': answer})
    return t


def family_frame_time(machine, lib, ctx, g, cases):
    t = v.Tally('frame_time')
    globals_ = 0x06fce36c
    for n in range(cases):
        state = bytearray(0x28)
        frame = FrameTime()
        lib.frame.mu_frame_time_init(C.byref(frame))
        if g.random() < 0.6:   # a running state
            frame.started = 1
            frame.base, frame.next_base, frame.prior = (g.getrandbits(32) for _ in range(3))
            frame.frames, frame.next_frames = g.randrange(0, 40), g.randrange(0, 40)
            frame.frame_time = v.f32(g.uniform(0, 1))
        struct.pack_into('<ff4xIIIIIii', state, 0, frame.fps, frame.world_time, frame.started, frame.base,
                         frame.next_base, frame.now, frame.prior, frame.frames, frame.next_frames)
        base = frame.prior if frame.started else g.getrandbits(32)
        if frame.started and g.random() < 0.5:   # an FPS window 0.1..5 s old: reaches the window reset
            frame.base = (base - g.choice([100, 1999, 2001, 2500, 5000])) & 0xffffffff
            struct.pack_into('<I', state, 0x10, frame.base)
        values = []
        for k in range(8):
            step = g.choice([0, 0, 1, 16, 40, 41, 2001, 3000, g.randrange(0, 1 << 20), -5])
            base = (base + step) & 0xffffffff
            values.append(base)
        queue = list(values)
        hooks = []

        def make(site):
            def hook(u, address, size, ignored):
                u.reg_write(machine.x86.UC_X86_REG_EAX, queue.pop(0) if queue else 0)
                u.reg_write(machine.x86.UC_X86_REG_EIP, site + 6)
            return hook
        for site in TIME_CALLS:
            hooks.append(machine.uc.hook_add(machine.UC_HOOK_CODE, make(site), begin=site, end=site))
        machine.uc.ctl_flush_tb()
        ft = struct.pack('<f', frame.frame_time)
        regions = [am.defined_region('timing', globals_, bytes(state)),
                   am.defined_region('frame-time', v.FRAME_TIME, ft)]
        try:
            result = v.run(machine, 0x12aeb2b, [], regions, {}, until=0x12aec9f)
        finally:
            for h in hooks:
                machine.uc.hook_del(h)
            machine.uc.ctl_flush_tb()
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        used = len(values) - len(queue)
        it = iter(values)
        get = TIME_FN(lambda c: next(it))
        lib.frame.mu_frame_time_update(C.byref(frame), get, None)
        mine = bytearray(0x28)
        struct.pack_into('<ff4xIIIIIii', mine, 0, frame.fps, frame.world_time, frame.started, frame.base,
                         frame.next_base, frame.now, frame.prior, frame.frames, frame.next_frames)
        client = result['regions']['timing']
        ok = client == bytes(mine) and \
            result['regions']['frame-time'] == struct.pack('<f', frame.frame_time)
        t.count(f'{used} clock reads')
        if frame.next_frames == 0:
            t.count('FPS window reset')
        if struct.pack('<f', frame.frame_time) == bytes.fromhex('18b7d138'):
            t.count('unchanged clock (0x38d1b718)')
        t.add(ok, {'case': n, 'values': values[:used], 'client': client.hex(), 'c': mine.hex(),
                   'ft': (result['regions']['frame-time'].hex(), struct.pack('<f', frame.frame_time).hex())})
    return t


FAMILIES = {'after_pass': family_after_pass, 'select': family_select, 'abyss_custom': family_abyss_custom,
            'abyss_after': family_abyss_after, 'chain_predicates': family_chain_predicates,
            'chain_noop': family_chain_noop, 'frame_time': family_frame_time}
FIXED = {'chain_predicates', 'chain_noop'}   # enumerate worlds x hooks; --cases does not apply
MUTATIONS = [
    ('Gate misses class flag', 'world_after.c', '||w==8||class_flag;', '||w==8||(class_flag&&0);', 'after_pass'),
    ('Gate misses 0x7a..0x85', 'world_after.c', '(w>=0x7a&&w<=0x85)', '(w>=0x7b&&w<=0x85)', 'after_pass'),
    ('Block range 0x86', 'world_after.c', 'in->world==0x86?-300.0f', 'in->world==0x87?-300.0f', 'after_pass'),
    ('Tower states', 'world_after.c', 'a->tower_state>5', 'a->tower_state>4', 'after_pass'),
    ('Flagged visibility bias', 'world_after.c', 'own_range(o,in,mu_obj_f32(o,MU_OBJF_RANGE)+bias);if(!o',
     'own_range(o, in, mu_obj_f32(o, MU_OBJF_RANGE)); if (!o', 'after_pass'),
    ('World 2 level', 'world_after.c', 'a->master_class?0x35:0x50', 'a->master_class?0x36:0x50', 'after_pass'),
    ('Abyss selector types', 'world_after.c', 't==0x17||t==0x28||t==0x29||t==0x2c',
     't==0x17||t==0x28||t==0x2c', 'select'),
    ('World 0x25 falls into 0x33', 'world_after.c', 'case0x25:/*', 'case 0x24: /*', 'select'),
    ('Class 142 range', 'world_after.c', '-1500.0f:-800.0f', '-1500.0f:-600.0f', 'select'),
    ('Class 145 live', 'world_after.c', 'returno[MU_OBJF_LIVE]&&in_list(t,w145', 'return in_list(t, w145', 'select'),
    ('World 0x85 type 6', 'world_after.c', 'hit=t==6||', 'hit=t==7||', 'select'),
    ('Abyss 1 rand chance', 'world_abyss_visual.c', 'cls==128?8:7', 'cls==128?7:7', 'abyss_custom'),
    ('Abyss 2/3 gate order', 'world_abyss_visual.c', 'if(cls!=128){', 'if(cls==130){', 'abyss_custom'),
    ('Abyss 2 world test', 'world_abyss_visual.c', '(cls!=129&&world!=cls)', '(world!=cls)', 'abyss_custom'),
    ('Abyss glow light', 'world_abyss_visual.c', '*0.4f+0.3f', '*0.4f+0.25f', 'abyss_custom'),
    ('Abyss other actions drawn', 'world_abyss_visual.c', 'else{return1;', 'else{', 'abyss_custom'),
    ('Abyss after blend round trip', 'world_abyss_visual.c', 'blend=float_round_trip(mu_obj_i32(o,MU_OBJF_BLEND_MESH))',
     'blend = float_round_trip(0) + mu_obj_i32(o, MU_OBJF_BLEND_MESH)', 'abyss_after'),
    ('Abyss after default flags', 'world_abyss_visual.c', 'flagged?2u:0x42u', 'flagged?2u:2u', 'abyss_after'),
    ('Abyss after glow texture', 'world_abyss_visual.c', '0x82de', '0x82df', 'abyss_after'),
    ('Chain Kanturu hook', 'world_after.c', 'case0xe74a3b:returnw==0x25;', 'case 0xe74a3b: return w == 0x26;',
     'chain_predicates'),
    ('Chain class map', 'world_after.c', 'returnw==0x2d||', 'return w == 0x2e ||', 'chain_noop'),
]


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'particles')], check=True)
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX), FRAME_LIB)


FRAME_LIB = None


def build_frame(tmp):
    out = Path(tmp) / ('libframetime.' + v.SUFFIX)
    subprocess.run(['cc', '-O2', '-shared', '-fPIC', '-o', str(out), str(ROOT / 'native/core/mu_frame_time.c')],
                   check=True)
    return out


def main():
    global FRAME_LIB
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
    ctx = {'vtables': class_vtables(text, data), 'cleanup': {h: first_ret_cleanup(text, h) for h in CHAIN}}
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(b), 'end': hex(e),
                             'sha256': hashlib.sha256(text[b - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for k, (b, e) in BODIES.items()}}
    with tempfile.TemporaryDirectory(prefix='worlds-after-') as tmp:
        FRAME_LIB = build_frame(tmp)
        lib = build(ROOT / 'reconstructed')
        seed = lambda name: random.Random(0xaf7e + list(FAMILIES).index(name))
        for name in names:
            tally = FAMILIES[name](machine, lib, ctx, seed(name), a.cases)
            report['families'][name] = tally.report()
            print(name, json.dumps(tally.report())[:2000], flush=True)
        if a.mutations:
            for label, file, old, new, family in MUTATIONS:
                if family not in names:
                    continue
                with tempfile.TemporaryDirectory(prefix='worlds-after-mut-') as mtmp:
                    root = Path(mtmp)
                    for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                        shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                        ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                    if (ROOT / 'reconstructed/deps.mk').exists():
                        shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                    path = root / 'objects' / file
                    s = path.read_text()
                    pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                    s, count = re.subn(pattern, lambda m: new, s, count=1)
                    assert count == 1, (label, old)
                    path.write_text(s)
                    cases = a.cases if family not in FIXED else 0
                    tally = FAMILIES[family](machine, build(root), ctx, seed(family), cases or 1)
                    item = {'name': label, 'cases': tally.cases,
                            'detected': tally.cases - tally.equal - tally.stopped, 'stopped': tally.stopped}
                    report['mutants'].append(item)
                    print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 for x in report['mutants'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
