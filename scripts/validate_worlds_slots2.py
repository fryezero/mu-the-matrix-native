#!/usr/bin/env python3
"""RENDER-WORLDS-SLOTS2 instruction comparisons (docs/research/client-worlds-slots2.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  rng_<world>   RenderObjectVisual 0x017f9758 from its entry for one object of the world: the model lookup, the outer
                rand() % 30 (0x017f9797), the world switch, every hook of the default branch (0x017fcb5c..) run as
                client code, and the world manager 0x00ea2dc1 entered as the class's slot 0x34 (thiscall on the
                class handler, ret 8, as the manager calls it). The sequence of rand() calls (each labelled outer /
                hook / slot by its call site and phase) and the generator state after the call against the native
                composition: mu_obj_visual_flicker (the runtime's draw at the top of its class visual), then the
                slot 0x34 routine the runtime calls for that world, with the same rand stream.
  rng_empty     the same for the class worlds whose slot 0x34 answers no (113, 115..120 0x00d5cc9b, 138, 139):
                natively only the flicker draw.
  rng_drawn     every other class world (the native branches that drew the outer rand before this lane, and
                Tormenta 141, whose particle visual draws it): RenderObjectVisual up to the world manager; the rand
                calls before it against mu_obj_visual_flicker (141: none, the particle visual draws it).
The first 301 cases of an rng family sweep the object type 0..300; the rest draw the world's slot types. One case in
eight has no model (the client returns before the draw).
"""
import argparse, ctypes as C, hashlib, json, math, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_after3 as a3
import validate_worlds_s2 as s2
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP

ROOT = Path(__file__).resolve().parents[1]
VISUAL, OUTER_SITE, MANAGER, MANAGER_GET = 0x17f9758, 0x17f979c, 0xea2dc1, 0xea594b
SINGLETON, SINGLETON_VISUAL = 0xdb747f, 0xdb7656
STATIC_GET, STATIC, STATIC_CTOR = 0xd53c8f, 0x1ec8eb8, 0xd53c61
RAND = 0x1989721
SING, HANDLER = 0x41030000, 0x41031000
WEATHER = 0x1cf15ec
BONE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))
FORWARD_FN = s2.FORWARD_FN
# world: (slot 0x34, the types its branches name)
SLOT34 = {
    57: (0xe946a8, [0x46, 0x50]), 58: (0xe946a8, [0x46, 0x50]),
    62: (0xe423d8, [0x1a, 0x1b, 0x1c]),
    63: (0xe8ece1, [0, 1, 2, 3, 4, 5, 6]),
    64: (0xdc6790, [34, 35, 36]),
    82: (0xe2c002, [0, 1, 2, 3, 4, 5, 6, 47, 48]),
    100: (0xe6f3d5, []), 101: (0xd7be80, [0x59b, 0x88a, 0x88b, 0x88c, 0x88d, 0x88e, 0x889, 0x88f]),
    128: (0xd5d564, [39]), 129: (0xd5f1f1, [39]), 130: (0xd60948, [39]),
    137: (0xe0a4bb, [8, 54, 120, 65, 121, 66, 122, 92, 93, 94, 95, 96]),
    93: (0xdaa9dd, [0x1f]), 94: (0xe24be1, [5]),
}
EMPTY = {113: 0xd5cc9b, 115: 0xd5cc9b, 116: 0xd5cc9b, 117: 0xd5cc9b, 118: 0xd5cc9b, 119: 0xd5cc9b, 120: 0xd5cc9b,
         138: 0xe07081, 139: 0xd9c1a7}
DRAWN = [69, 70, 71, 72, 79, 80, 81, 91, 92, 95, 96, 110, 111, 112, 114, 121, 122, 123, 124, 125, 126, 127, 131,
         132, 133, 134, 135, 136, 140, 141, 142, 143, 144, 145]
# the types of Uruk's visual (0x00e6f3d5) cases, read from uruk.c's switch
URUK_TYPES = [20, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
              60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
              85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107,
              108, 109, 110]


class Machine(vp.PtMachine):
    """PtMachine whose stubs may enter a routine as a thiscall on a given `this` (jump_this)."""

    def stub_entry(self, uc, address, size, ignored):
        handler = self.stubs.get(address)
        target = getattr(handler, 'jump_this', None)
        if target is not None:
            handler(None)
            uc.reg_write(UC_X86_REG_ECX, target[1])
            uc.reg_write(UC_X86_REG_EIP, target[0])
            return
        super().stub_entry(uc, address, size, ignored)


def enter(address, this, note):
    def stub(m):
        if m is None:
            note()
        return 0
    stub.jump_this = (address, this)
    return stub


class Library(a3.Library):
    def __init__(self, path):
        super().__init__(path)
        d, P, I, F, L, R = self.dll, C.c_void_p, C.c_int32, C.c_float, C.POINTER(v.Log), v.RAND_FN
        d.mu_obj_visual_flicker.argtypes = [I, C.c_int]
        d.mu_raklion_visual.argtypes = [P, I, C.c_int, R, P, L]
        d.mu_santa_visual.argtypes = [P, I, C.c_int, F, L]
        d.mu_vulcanus_visual.argtypes = [P, I, I, C.c_int, F, R, P, L]
        d.mu_duel_visual.argtypes = [P, I, C.c_int, R, P, L]
        d.mu_world82_visual.argtypes = [P, I, I, C.c_int, F, R, P, L]
        d.mu_uruk_visual.argtypes = [P, I, I, I, F, R, P, L]
        d.mu_arca_visual.argtypes = [P, I, I, I, I, BONE_FN, P, FORWARD_FN, P, L]
        d.mu_abyss_visual.argtypes = [I, P, I, C.c_int]
        d.mu_kanturu_ug_visual.argtypes = [P, I, C.c_int, F, R, BONE_FN, P, L]
        d.mu_csw_visual.argtypes = [P, I, F, R, BONE_FN, P, P, L]
        d.mu_login_visual.argtypes = [P, I, R, BONE_FN, P, L]


def bone_point(k, local):
    return tuple(v.f32(local[q] + k * (q + 1) * 17 + 3) for q in range(3))


_STATIC = None


def static_region(machine):
    """The static 0x01ec8eb8 its constructor builds (the hook 0x00d5404b's `this`, returned by 0x00d53c8f)."""
    global _STATIC
    if _STATIC is None:
        built = v.run(machine, STATIC_CTOR, [], v.global_regions(0, 6, [am.defined_region('inst', STATIC, bytes(0x60))]),
                      {}, ecx=STATIC, cleanup=0)
        assert not v.stopped_reason(built), v.stopped_reason(built)
        _STATIC = built['regions']['inst']
    return _STATIC


def singleton():
    """The world singleton 0x00db747f returns: its slot 0x34 is the client's 0x00db7656 (no other field read)."""
    s = bytearray(0x400)
    struct.pack_into('<I', s, 0, SING + 0x200)
    struct.pack_into('<I', s, 0x200 + 0x34, SINGLETON_VISUAL)
    return bytes(s)


def uruk_base():
    """Uruk Mountain's handler as Arca War's registry lookup returns it: its slot 0x34 is the client's 0x00e6f3d5."""
    h = bytearray(s2.base_handler())
    struct.pack_into('<I', h, 0x200 + 0x34, SLOT34[100][0])
    return bytes(h)


def case_object(g, world, typ):
    o = bytearray(v.move_object(g, world, 'full'))
    v.put_i(o, 0x5c, typ)
    v.put_i(o, 0x68, g.choice([-1, -1, -2, 0, 1]))
    return o


def case_time(g):
    k = g.randrange(0, 50000)
    return v.f32(g.choice([0.0, 1000.0, 1570.79638671875, float(200 * k + g.randrange(0, 7)),
                           float(200 * k + g.randrange(0, 200)), g.uniform(-1e6, 1e6), g.uniform(0, 3e7)]))


def run_original(machine, world, typ, raw, present, time, weather, stage, seed, slot, g):
    """RenderObjectVisual for one object: the labelled rand calls, the generator, whether the manager was reached."""
    rnd = v.MsvcRand(seed)
    phase, labels, bones = ['pre'], [], []

    def rand(m):
        ret = struct.unpack('<I', bytes(m.uc.mem_read(m.uc.reg_read(UC_X86_REG_ESP), 4)))[0]
        labels.append('outer' if ret == OUTER_SITE else 'hook' if phase[0] == 'pre' else 'slot')
        return rnd()

    def reached():
        phase[0] = 'slot'

    def manager_stop(m):
        phase[0] = 'manager'
        return (0, 8)

    def transform(m):
        a = [m.argument(k) for k in range(4)]
        k = (a[0] - 0x6fce398) // 0x30
        local = struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12)))
        bones.append(k)
        m.uc.mem_write(a[2], v.pack_f(*bone_point(k, local)))
        return (0, 16)

    def named(m):
        return (0x6fce398, 8)
    regions = v.global_regions(world, 6, [
        am.defined_region('object', v.OBJECTS, bytes(raw)),
        am.defined_region('model', v.MODEL, bytes(0x100)),
        am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
        am.defined_region('weather', WEATHER, struct.pack('<i', weather)),
        am.defined_region('static', STATIC, static_region(machine)),
        am.defined_region('singleton', SING, singleton(), writable=False),
        am.defined_region('handler', HANDLER, v.fake_object(), writable=False)])
    if world == 101:
        regions += [am.defined_region('arca', s2.ARCA, s2.arca_handler(100, stage)),
                    am.defined_region('list', s2.LIST, struct.pack('<4i', *s2.ARCA_WORLDS)),
                    am.defined_region('base', s2.BASE, uruk_base())]
    stubs = {vp.MODEL_CONTAINER: lambda m: v.FAKE, vp.MODEL_GET: lambda m: (v.MODEL if present else 0, 4),
             RAND: rand, STATIC_GET: lambda m: STATIC, SINGLETON: lambda m: SING,
             MANAGER_GET: lambda m: s2.REGISTRY,
             MANAGER: manager_stop if slot is None else enter(slot, s2.ARCA if world == 101 else HANDLER, reached),
             0x95c652: lambda m: s2.CLASS92, 0xea4679: lambda m: (s2.BASE, 4),
             vp.TRANSFORM_POSITION: transform, vp.BONE_MATRIX: named,
             0x168fafd: lambda m: 0, 0x1692eb7: lambda m: 0, 0x13c0eaa: lambda m: 0, 0x153b02c: lambda m: 0,
             0xa6ac96: lambda m: 0, 0x16cacfc: lambda m: 0, 0x16d9f51: lambda m: 0,
             vp.SINE: lambda m: m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0))))),
             vp.COSINE: lambda m: m.x87_return(v.f32(math.cos(v.from_bits(m.argument(0))))),
             0x961a07: lambda m: m.x87_return(v.f32(math.sqrt(abs(v.from_bits(m.argument(0))))))}
    result = machine.execute(VISUAL, [v.OBJECTS], regions, stubs)
    return labels, rnd.seed, phase[0], v.stopped_reason(result)


def run_native(lib, world, typ, raw, present, time, weather, stage, seed):
    """The runtime's class visual: mu_obj_visual_flicker's draw, then the slot 0x34 routine it calls for `world`."""
    rnd = v.MsvcRand(seed)
    labels, phase = [], ['outer']

    def draw(ctx):
        labels.append(phase[0])
        return rnd()
    fn = v.RAND_FN(draw)
    d = lib.dll
    o = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
    log = v.new_log()

    def bone_cb(ctx, k, local, out):
        for q, value in enumerate(bone_point(k, tuple(local[:3]))):
            out[q] = value
    bone = BONE_FN(bone_cb)
    if d.mu_obj_visual_flicker(world, present):
        fn(None)
    phase[0] = 'slot'
    if world in (57, 58):
        d.mu_raklion_visual(o, 0, present, fn, None, C.byref(log))
    elif world == 62:
        d.mu_santa_visual(o, 0, present, time, C.byref(log))
    elif world == 63:
        d.mu_vulcanus_visual(o, 0, world, present, time, fn, None, C.byref(log))
    elif world == 64:
        d.mu_duel_visual(o, 0, present, fn, None, C.byref(log))
    elif world == 82:
        d.mu_world82_visual(o, 0, world, present, time, fn, None, C.byref(log))
    elif world == 100:
        if present:
            d.mu_uruk_visual(o, 0, world, weather, time, fn, None, C.byref(log))
    elif world == 101:
        def forward(ctx, slot, base):   # the runtime's uruk_arca_visual
            if slot != 0x34 or base != 100 or not present:
                return 0
            return d.mu_uruk_visual(o, 0, world, weather, time, fn, None, C.byref(log))
        fwd = FORWARD_FN(forward)
        d.mu_arca_visual(o, 0, world, 100, stage, bone if present else BONE_FN(), None, fwd, None, C.byref(log))
    elif world in (128, 129, 130):
        d.mu_abyss_visual(world, o, world, present)
    elif world == 137:
        d.mu_kanturu_ug_visual(o, 0, present, time, fn, bone, None, C.byref(log))
    elif world == 93 and present:   # the runtime calls the scene visuals only with a model
        d.mu_csw_visual(o, 0, time, fn, bone if present else BONE_FN(), None, None, C.byref(log))
    elif world == 94 and present:
        d.mu_login_visual(o, 0, fn, bone if present else BONE_FN(), None, C.byref(log))
    return labels, rnd.seed


def rng_family(machine, lib, g, cases, worlds):
    name = 'rng_' + (str(worlds[0]) if len(worlds) == 1 else 'empty' if worlds[0] in EMPTY else 'drawn')
    t = v.Tally(name)
    for n in range(cases):
        world = worlds[n % len(worlds)]
        types = SLOT34[world][1] if world in SLOT34 else []
        if world in (100, 101):
            types = types + URUK_TYPES
        typ = n if n <= 300 and len(worlds) == 1 else g.choice(types) if types and g.random() < 0.85 else \
            g.randrange(0, 301)
        present = g.random() >= 0.125
        raw = case_object(g, world, typ)
        time, weather, stage = case_time(g), g.choice([0, 1, 2, g.randrange(-3, 6)]), g.randrange(6)
        seed = g.randrange(2**32)
        slot = SLOT34[world][0] if world in SLOT34 else EMPTY.get(world)
        labels, state, phase, stop = run_original(machine, world, typ, raw, present, time, weather, stage, seed,
                                                  slot, g)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': typ, 'present': present}, stop)
            continue
        if slot is None:   # rng_drawn: up to the world manager
            native = ['outer'] if lib.dll.mu_obj_visual_flicker(world, present) else []
            cstate = v.MsvcRand(seed)
            for _ in native:
                cstate()
            ok = labels == native and state == cstate.seed and phase == ('manager' if present else 'pre')
            if world == 141:   # the particle visual draws it (validate_particles, family visual): none here
                ok = labels == (['outer'] if present else []) and not native and \
                    phase == ('manager' if present else 'pre')
            t.count('world %d' % world)
        else:
            native, cstate = run_native(lib, world, typ, raw, present, time, weather, stage, seed)
            ok = labels == native and state == cstate and phase == ('slot' if present else 'pre')
            t.count('slot draws %d' % min(labels.count('slot'), 3))
        t.count('model' if present else 'no model')
        t.count('outer drawn' if 'outer' in labels else 'no outer draw')
        if 'hook' in labels:
            t.count('hook draws')
        t.add(ok, {'case': n, 'world': world, 'type': typ, 'present': present, 'client': labels[:8],
                   'native': (native if isinstance(native, list) else native)[:8], 'phase': phase})
    return t



# ---------------------------------------------------------------- the custom (0x38) and after (0x3c) slots
import validate_worlds_after2 as a2
import validate_worlds_slots as ws
IG_TYPES = [0, 1, 3, 0x25, 0x29, 0x2c, 0x2f, 0x30, 0x31, 0x37, 0x40, 0x46, 0x51, 0x73, 0x75]
ACHERON_TYPES = [0x11, 0x30, 0x42, 0x44, 0x4f, 0x6e, 0x1c, 0x1d, 0x1e, 0x2d, 0x2e, 0x50]
DEBENTER_TYPES = [0xb, 0x25, 0x32] + list(range(0x37, 0x45))
URUK_SLOT_TYPES = [0x10, 0x2c, 0x31, 0x39, 0x3a, 0x46, 0x47, 0x48, 0x49, 0x54, 0x55, 0x56]
NARS_TYPES = [0, 6, 0x10, 0x11, 0x15, 0x16, 0x17, 0x18, 0x1b, 0x22, 0x23, 0x24, 0x25, 0x26, 0x4d, 0x8e, 0x96]
# class: (custom 0x38, after 0x3c (None: empty/base, compared by validate_worlds_slots' trivial family),
#         worlds the slot is tried in, case types)
SLOTS2 = {
    62: (0xe426cf, None, [62, 62, 61, 63, 0], [0x10, 0xf, 0x11]),
    69: (0xdc8b33, 0xdc9f33, [69, 69, 70, 71, 72, 73, 74, 68, 75, 0], IG_TYPES),
    70: (0xdd57fa, 0xdd5888, [70, 70, 69, 71, 72, 0], IG_TYPES),
    71: (0xdda8f5, 0xdda93e, [71, 71, 70, 72, 69, 0], IG_TYPES),
    72: (0xde08df, 0xde0ff6, [72, 72, 73, 74, 71, 75, 69, 0], IG_TYPES + [0x60, 0x61, 0x64, 0x62, 0x63]),
    82: (0xe2caaf, 0xe2d4a8, [82, 82, 83, 90, 91, 81, 0], [0xa, 0xf, 0x10, 0x13, 0x14, 0x1f, 0x21, 0x46, 0x48]),
    95: (0xdbee19, None, [95, 95, 96, 94, 97, 0], DEBENTER_TYPES),
    100: (0xe702eb, None, [100, 100, 101, 99, 102, 0], URUK_SLOT_TYPES),
    110: (0xe28bb2, 0xe28faf, [110, 110, 111, 109, 112, 0], NARS_TYPES),
    92: (0xd7c02e, 0xd7de81, [92, 96, 101, 111, 92, 96, 101, 111, 91, 95, 100, 110, 0],
         ACHERON_TYPES + DEBENTER_TYPES + URUK_SLOT_TYPES + NARS_TYPES),
}
ARCA_MEMBERS = [92, 96, 101, 111]
# the base classes Arca War's slots reach through the registry (custom, after)
ARCA_BASES = {91: (0xd6c427, 0xd6d3d7), 95: (0xdbee19, 0xd5cc60), 100: (0xe702eb, 0xd5cc60), 110: (0xe28bb2, 0xe28faf)}
IG69_GET = 0xdd8a3c   # the world-69 handler (0x45), whose slot 0x38 70..72 forward to
PUSH, POP = 0x12b7e53, 0x12b7e65   # glPushMatrix / glPopMatrix wrappers (Nars after)
EFFECT = 0x13c0eaa
BASES = {w: 0x41040000 + 0x1000 * k for k, w in enumerate(list(ARCA_BASES) + [69])}


def handler_with(custom, after):
    h = bytearray(v.fake_object())
    struct.pack_into('<I', h, 0x200 + 0x38, custom)
    struct.pack_into('<I', h, 0x200 + 0x3c, after)
    struct.pack_into('<I', h, 0, 0)   # vtable pointer set by the caller (the region's base)
    return h


def base_regions():
    out = []
    for w, address in BASES.items():
        custom, after = ARCA_BASES.get(w, (0xdc8b33, 0xdc9f33))
        h = handler_with(custom, after)
        struct.pack_into('<I', h, 0, address + 0x200)
        out.append(am.defined_region(f'base{w}', address, bytes(h), writable=False))
    return out


def slot2_events(events, model):
    """validate_worlds_slots' draws (with the StreamMesh byte and colour at the call), plus CreateEffect (type,
    position, angle, light, subtype, owner, scale), in order."""
    stream, colour, out = model[0x94], list(struct.unpack_from('<3I', model, 0x54)), []
    for e in events:
        call, args = e[0], list(e[2:])
        if call == a2.STREAM:
            stream = args[0] & 0xff
        elif call == a2.COLOR:
            colour = args[:3]
        elif call in (ws.BODY, ws.MESH):
            out.append((call,) + tuple(args[:8]) + (stream,) + tuple(colour))
        elif call == EFFECT:
            out.append((EFFECT,) + tuple(args[:13]))
        else:
            out.append(('unexpected', call))
    return out


def slot2_family(machine, lib, g, cases, cls, after):
    custom, after_addr, worlds, types = SLOTS2[cls]
    t = v.Tally(('after2_' if after else 'custom2_') + str(cls))
    for n in range(cases):
        world = (g.choice(ARCA_MEMBERS) if cls == 92 else cls) if g.random() < 0.75 else g.choice(worlds)
        typ = n if n <= 300 else g.choice(types + ([0x73, 0x75] * 4 if cls in (69, 70, 71, 72) else []))\
            if g.random() < 0.9 else g.randrange(0, 301)
        count, subs, array, records = a2.slot_meshes(g)
        o, b = a2.slot_object(g, typ), a2.slot_model(g, count)
        o[0] = g.choice([0, 1, 1, 1])
        if typ in (0x73, 0x75):   # the bone-9 effect latch: frame windows (0, 0.4) and (7, 7.5), state +0x60
            v.put_f(o, 0xd0, v.f32(g.choice([1e-6, 0.2, 0.39999, 0.0, 0.4, 7.0, 7.0001, 7.2, 7.4999, 7.5]) if g.random() < 0.6 else
                                   g.choice([0.0, 0.4, 0.41, 6.99, 7.0, 7.5, 7.6, -0.1, float('nan'), g.uniform(-1, 10)])))
            v.put_i(o, 0x60, g.choice([0x64, 0x65]) if g.random() < 0.7 else
                    g.choice([0x63, 0x66, 0, g.randrange(-5, 300)]))
        if g.random() < 0.05:
            v.put_f(o, 0xb0, v.f32(g.choice([float('nan'), 1e30, -1e30, 0.0])))
        actions = bytearray(g.getrandbits(8) for _ in range(16 * a2.ACTION_COUNT))
        time = v.f32(g.choice([0.0, g.uniform(0, 100000), g.uniform(0, 1e7), g.uniform(1e7, 3e9),
                               g.uniform(-3e9, 0), 2147483648.0, -2147483904.0]))
        seed = g.randrange(2**32)
        ra, rb = v.MsvcRand(seed), v.MsvcRand(seed)
        calls, bones = [], []
        base = world - 1   # Arca War's handler +0x1c (production: the world below)
        stage = g.randrange(6)

        def recorder(address):
            def stub(m):
                model = bytes(m.uc.mem_read(v.MODEL, 0x100))
                calls.append((address,) + tuple(m.argument(k) for k in range(8)) + (model[0x94],) +
                             struct.unpack_from('<3I', model, 0x54))
                return (0, 32)
            return stub

        def transform(m):
            a = [m.argument(k) for k in range(4)]
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + 0x30 * k and a[3] == 0 and m.uc.reg_read(m.x86.UC_X86_REG_ECX) == v.MODEL
            local = struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12)))
            bones.append(k)
            m.uc.mem_write(a[2], v.pack_f(*(v.f32(x + d) for x, d in zip(local, ws.bone_offset(k)))))
            return (0, 16)

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[5] == v.OBJECTS and a[6] == 0xffffffff and a[7:10] == [0, 0, 0] and a[11:] == [0xffffffff, 0, 0], a
            calls.append((EFFECT, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], 1, a[10]))
            return 0

        def lookup(m):
            assert m.uc.reg_read(m.x86.UC_X86_REG_ECX) == s2.REGISTRY
            w = struct.unpack('<i', struct.pack('<I', m.argument(0)))[0]
            return (BASES[w], 4)
        stubs = {ws.BODY: recorder(ws.BODY), ws.MESH: recorder(ws.MESH), RAND: lambda m: ra(),
                 ws.TRANSFORM: transform, EFFECT: effect, PUSH: lambda m: (0, 4), POP: lambda m: (0, 0),
                 MANAGER_GET: lambda m: s2.REGISTRY, 0xea4679: lookup,
                 IG69_GET: lambda m: BASES[69] if m.argument(0) == 0x45 else 0}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(b)),
                                              am.defined_region('actions', v.ACTIONS, bytes(actions),
                                                                writable=False),
                                              am.defined_region('meshes', a2.MESHES, bytes(array), writable=False),
                                              am.defined_region('subs', a2.SUBS, bytes(records), writable=False),
                                              am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                              am.defined_region('fake', v.FAKE, v.fake_object(), writable=False),
                                              am.defined_region('arca', s2.ARCA, s2.arca_handler(base, stage),
                                                                writable=False),
                                              am.defined_region('list', s2.LIST, struct.pack('<4i', *s2.ARCA_WORLDS),
                                                                writable=False)] + base_regions())
        start = after_addr if after else custom
        result = v.run(machine, start, [v.OBJECTS, v.MODEL, 0], regions, stubs,
                       ecx=s2.ARCA if cls == 92 else v.FAKE, cleanup=12)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': hex(typ)}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        cb = C.create_string_buffer(bytes(b), 0x100)
        log = v.new_log()
        flags = (C.c_int16 * 16)(*(subs + [0] * (16 - len(subs))))
        act = struct.unpack_from('<H', o, 0x2a)[0]
        frames = struct.unpack_from('<h', actions, 16 * act + 8)[0]
        rand_fn = v.RAND_FN(lambda c: rb())
        cbones = []

        def c_bone(ctx, k, local, out):
            cbones.append(k)
            for q, d in enumerate(ws.bone_offset(k)):
                out[q] = v.f32(local[q] + d)
        bone_fn = ws.BONE(c_bone)
        model = ws.SlotModel(count, flags, frames, rand_fn, None, 0, bone_fn, None)
        ccls = world if cls == 92 and world in ARCA_MEMBERS else cls
        if after:
            lib.dll.mu_class_after(ccls, co, cb, 0, world, time, C.byref(model), C.byref(log))
            answer, client = 0, 0
        else:
            answer = 1 if lib.dll.mu_class_custom(ccls, co, cb, 0, world, time, C.byref(model), C.byref(log)) else 0
            client = result['eax'] & 0xff
        mine = slot2_events(v.log_events(log), b)
        named = (C.c_int32 * 36)()
        listed = set(named[:lib.dll.mu_world_slot_bitmaps(world, typ, named)])
        textures = {c[8] for c in calls if c[0] in (ws.BODY, ws.MESH) and c[8] != 0xffffffff}
        bitmaps_ok = all(x in listed for x in textures if 0x7000 <= x < 0x9000)
        if textures:
            t.count('bitmap meshes')
        if any(c[0] == EFFECT for c in calls):
            t.count('effects')
        ok = (bitmaps_ok and calls == mine and bones == cbones and client == answer and ra.seed == rb.seed and
              result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == cb.raw[:0x100])
        t.count(f'answer {client}')
        t.count('drawn' if calls else 'no draw')
        if (world == cls or (cls == 92 and world in ARCA_MEMBERS)) and typ in types:
            t.count('case types')
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': [tuple(hex(x) for x in c) for c in calls[:6]],
                   'native': [tuple(hex(x) for x in c) for c in mine[:6]], 'answer': (client, answer),
                   'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                   'model': result['regions']['model'] == cb.raw[:0x100], 'rand': ra.seed == rb.seed,
                   'bones': (bones, cbones), 'bitmaps': (sorted(textures), sorted(listed))})
    return t


FAMILIES = {}
for _w in SLOT34:
    FAMILIES[f'rng_{_w}'] = (lambda w: lambda m, l, g, n: rng_family(m, l, g, n, [w]))(_w)
FAMILIES['rng_empty'] = lambda m, l, g, n: rng_family(m, l, g, n, list(EMPTY))
FAMILIES['rng_drawn'] = lambda m, l, g, n: rng_family(m, l, g, n, DRAWN)
for _c, (_cu, _af, _w, _t) in SLOTS2.items():
    FAMILIES[f'custom2_{_c}'] = (lambda c: lambda m, l, g, n: slot2_family(m, l, g, n, c, False))(_c)
    if _af:
        FAMILIES[f'after2_{_c}'] = (lambda c: lambda m, l, g, n: slot2_family(m, l, g, n, c, True))(_c)
S = 'world_slots2_visual.c'
MUTATIONS = [
    # the outer draw's model gate and world set
    ('Flicker without the model gate', S, 'if(!has_model)return0;', 'if (0) return 0;', 'rng_57'),
    ('Flicker misses Raklion 57', S, 'returnworld==57||', 'return ', 'rng_57'),
    ('Flicker misses Raklion 58', S, 'world==58||(world>=62', '(world >= 62', 'rng_58'),
    ('Flicker misses Santa 62', S, '(world>=62&&world<=64)', '(world >= 63 && world <= 64)', 'rng_62'),
    ('Flicker misses Duel 64', S, '(world>=62&&world<=64)', '(world >= 62 && world <= 63)', 'rng_64'),
    ('Flicker misses 82', S, '(world>=79&&world<=82)', '(world >= 79 && world <= 81)', 'rng_82'),
    ('Flicker misses Uruk 100', S, 'world==100||world==101||(world>=110', 'world == 101 || (world >= 110', 'rng_100'),
    ('Flicker misses Arca 101', S, 'world==100||world==101||(world>=110', 'world == 100 || (world >= 110', 'rng_101'),
    ('Flicker misses character scene 93', S, '(world>=91&&world<=96)', '(world >= 94 && world <= 96) || world == 91 || world == 92', 'rng_93'),
    ('Flicker misses login 94', S, '(world>=91&&world<=96)', '(world >= 95 && world <= 96) || (world >= 91 && world <= 93)', 'rng_94'),
    ('Flicker misses Abyss 128', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 127) || (world >= 129 && world <= 140)', 'rng_128'),
    ('Flicker misses Abyss 130', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 129) || (world >= 131 && world <= 140)', 'rng_130'),
    ('Flicker misses Kanturu 137', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 136) || (world >= 138 && world <= 140)', 'rng_137'),
    ('Flicker misses Ignis 138', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 137) || (world >= 139 && world <= 140)', 'rng_empty'),
    ('Flicker draws for Tormenta 141', S, '(world>=142&&world<=145)', '(world >= 141 && world <= 145)', 'rng_drawn'),
    ('Flicker misses 145', S, '(world>=142&&world<=145)', '(world >= 142 && world <= 144)', 'rng_drawn'),
    # Santa Village 62
    ('Santa colour', S, 'color(s,0.0f,0.5f,0.5f);', 'color(s, 0.0f, 0.5f, 0.4f);', 'custom2_62'),
    ('Santa glow flags', S, 'color(s,0.0f,0.5f,0.5f);mesh_std(s,2,0x44,-1);', 'color(s, 0.0f, 0.5f, 0.5f); mesh_std(s, 2, 0x42, -1);', 'custom2_62'),
    ('Santa world', S, 'world==62?santa_custom', 'world == 61 ? santa_custom', 'custom2_62'),
    # Imperial Guardian 69..72
    ('IG after-flag types', S, 'case0:case1:case3:case0x2c:case0x51:set_after', 'case 0: case 1: case 0x2c: case 0x51: set_after', 'custom2_69'),
    ('IG 0x29 pulse', S, 'csin(s->time*0.002f)*0.5f+0.6f', 'csin(s->time * 0.002f) * 0.5f + 0.5f', 'custom2_69'),
    ('IG 0x2f grey', S, 'grey(s,1.2f);', 'grey(s, 1.1f);', 'custom2_69'),
    ('IG 0x30 grey', S, 'grey(s,1.1f);', 'grey(s, 1.2f);', 'custom2_70'),
    ('IG 0x40 mesh order', S, 'case0x40:mesh_std(s,0,2,-1);mesh_std(s,3,2,-1);', 'case 0x40: mesh_std(s, 0, 2, -1); mesh_std(s, 2, 2, -1);', 'custom2_71'),
    ('IG effect window', S, 'if(f>0.0f&&0.4f>f){', 'if (f > 0.0f && 0.5f > f) {', 'custom2_69'),
    ('IG effect state', S, 'mu_obj_set_i32(s->o,0x60,0x65);', 'mu_obj_set_i32(s->o, 0x60, 0x66);', 'custom2_72'),
    ('IG latch reset window', S, 'f>7.0f&&7.5f>f', 'f >= 7.0f && 7.5f > f', 'custom2_69'),
    ('IG effect bone', S, '->bone_context,9,zero,p', '->bone_context, 8, zero, p', 'custom2_70'),
    ('IG 0x75 stream', S, 'stream(s,big?4:3);', 'stream(s, big ? 3 : 3);', 'custom2_71'),
    ('IG 0x73 scroll sign', S, '%25000)*-0.0004f', '% 25000) * 0.0004f', 'custom2_69'),
    ('IG 72 grey', S, 'f32b(0x3e2e789eu)', 'f32b(0x3e2e789fu)', 'custom2_72'),
    ('IG 72 types', S, 't!=0x60&&t!=0x61&&t!=0x64', 't != 0x60 && t != 0x61 && t != 0x63', 'custom2_72'),
    ('IG 70 world test', S, 'returnworld==cls&&ig69_custom', 'return ig69_custom', 'custom2_70'),
    ('IG after pulse', S, '(csin(s->time*0.0015f)+1.0f)*0.4f+0.2f', '(csin(s->time * 0.0015f) + 1.0f) * 0.4f + 0.3f', 'after2_69'),
    ('IG after 72 worlds', S, 'cls==72?!(world>=72&&world<=74):world!=cls', 'cls == 72 ? !(world >= 72 && world <= 73) : world != cls', 'after2_72'),
    # World 82
    ('82 0xf scroll sign', S, 'tmod(s,10000,0.0001f,1),-1);', 'tmod(s, 10000, 0.0001f, 0), -1);', 'custom2_82'),
    ('82 0x10 pulse', S, 'case0x10:body(s,2,0,(csin(s->time*0.002f)+1.0f)*0.3f+0.4f,U(s),V(s),H(s));return1;', 'case 0x10: body(s, 2, 0, (csin(s->time * 0.002f) + 1.0f) * 0.3f + 0.5f, U(s), V(s), H(s)); return 1;', 'custom2_82'),
    ('82 0x48 alpha', S, 'A(s)*0.1f,0,w', 'A(s) * 0.2f, 0, w', 'custom2_82'),
    ('82 world range', S, 'returnworld>=82&&world<=90;', 'return world >= 82 && world <= 89;', 'custom2_82'),
    ('82 bitmap listed', S, 'if(w82_world(world)&&type==0x48){', 'if (w82_world(world) && type == 0x47) {', 'custom2_82'),
    ('82 after 0x21 stream', S, 'stream(s,0);mesh(s,0,0x42,A(s),BM(s),BL(s),U(s),tmod', 'stream(s, 1); mesh(s, 0, 0x42, A(s), BM(s), BL(s), U(s), tmod', 'after2_82'),
    ('82 after body types', S, 'case0xa:case0x13:case0x14:case0x1f:body_std', 'case 0xa: case 0x13: case 0x14: body_std', 'after2_82'),
    # Debenter 95
    ('Debenter 0xb hidden', S, 'body(s,2,BM(s),BL(s),U(s),V(s),2);stream(s,2);', 'body(s, 2, BM(s), BL(s), U(s), V(s), 1); stream(s, 2);', 'custom2_95'),
    ('Debenter scroll at INT_MIN', S, 'mesh(s,2,2,A(s),-1,BL(s),U(s),tmod_neg_rem(s,10000,0.0001f),-1);', 'mesh(s, 2, 2, A(s), -1, BL(s), U(s), tmod(s, 10000, 0.0001f, 1), -1);', 'custom2_95'),
    ('Debenter 0x25 period', S, '%25000)*4e-05f', '% 20000) * 4e-05f', 'custom2_95'),
    ('Debenter 0x32 light', S, '*0.4f+0.3f;mesh(s,0,2,A(s),BM(s),A(s)', '* 0.4f + 0.3f; mesh(s, 0, 2, A(s), BM(s), BL(s)', 'custom2_95'),
    ('Debenter answer-only range', S, 'if(t>=0x38&&t<=0x43)', 'if (t >= 0x38 && t <= 0x42)', 'custom2_95'),
    # Uruk Mountain 100
    ('Uruk 0x10 v nudge', S, 'V(s)-0.005f', 'V(s) - 0.004f', 'custom2_100'),
    ('Uruk clamp value', S, 'returnx>1.0f?1.0f:x;', 'return x > 1.0f ? 0.99f : x;', 'custom2_100'),
    ('Uruk 0x2c hidden', S, 'set_hidden(s,2);mesh(s,0,2', 'set_hidden(s, 3); mesh(s, 0, 2', 'custom2_100'),
    ('Uruk 0x46 blend', S, 'body(s,2,4,w,U(s),V(s),H(s));', 'body(s, 2, 3, w, U(s), V(s), H(s));', 'custom2_100'),
    ('Uruk 0x49 glows', S, 'for(intk=0;k<3;++k)', 'for (int k = 0; k < 2; ++k)', 'custom2_100'),
    ('Uruk world', S, 'world==100||world==101?uruk_custom', 'world == 100 ? uruk_custom', 'custom2_100'),
    # Nars 110
    ('Nars 0x17 hidden', S, 'body_std(s,2);', 'body_std(s, 1);', 'custom2_110'),
    ('Nars 0x4d', S, 'case0:case0x4d:', 'case 0:', 'custom2_110'),
    ('Nars after chrome twice', S, 'mesh(s,3,0x20080,1.0f,3,BL(s),U(s),V(s),0x7f1f);mesh(s,3,0x20080,1.0f,3,BL(s),U(s),V(s),0x7f1f);break;', 'mesh(s, 3, 0x20080, 1.0f, 3, BL(s), U(s), V(s), 0x7f1f); break;', 'after2_110'),
    ('Nars after 0x8e pulse', S, '*0.15f+0.7f', '* 0.15f + 0.8f', 'after2_110'),
    ('Nars after 0x22 scroll sign', S, 'tmod(s,2000,0.0005f,1),-1);stream(s,0xff);mesh_std(s,3', 'tmod(s, 2000, 0.0005f, 0), -1); stream(s, 0xff); mesh_std(s, 3', 'after2_110'),
    ('Nars after 0x96', S, 'case0x1b:case0x96:', 'case 0x1b:', 'after2_110'),
    # Arca War 92/96/101/111
    ('Arca custom base', S, 'mu_class_custom(mu_arca_base_world(cls),', 'mu_class_custom(mu_arca_base_world(cls) - 1,', 'custom2_92'),
    ('Arca after forward', S, 'if(mu_arca_world(world))mu_class_after(', 'if (0) mu_class_after(', 'after2_92'),
    ('Arca bitmaps', S, 'constint32_tn=mu_world_slot_bitmaps(mu_arca_base_world(world),type,base);', 'const int32_t n = 0 * mu_world_slot_bitmaps(mu_arca_base_world(world), type, base);', 'custom2_92'),
]


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX))


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
    machine = Machine(text, data)
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0x5108 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-slots2-mut-') as mtmp:
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
                tally = FAMILIES[family](machine, build(root), seed(family), a.cases)
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
