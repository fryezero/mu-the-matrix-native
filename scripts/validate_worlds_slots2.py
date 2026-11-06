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


FAMILIES = {}
for _w in SLOT34:
    FAMILIES[f'rng_{_w}'] = (lambda w: lambda m, l, g, n: rng_family(m, l, g, n, [w]))(_w)
FAMILIES['rng_empty'] = lambda m, l, g, n: rng_family(m, l, g, n, list(EMPTY))
FAMILIES['rng_drawn'] = lambda m, l, g, n: rng_family(m, l, g, n, DRAWN)
S = 'world_slots2_visual.c'
MUTATIONS = [
    # the outer draw's model gate and world set
    ('Flicker without the model gate', S, 'if(!has_model)return0;', 'if (0) return 0;', 'rng_57'),
    ('Flicker misses Raklion 57', S, 'returnworld==57||', 'return ', 'rng_57'),
    ('Flicker misses Raklion 58', S, 'world==58||(world>=62', '(world >= 62', 'rng_58'),
    ('Flicker misses Santa 62', S, '(world>=62&&world<=64)', '(world >= 63 && world <= 64)', 'rng_62'),
    ('Flicker misses Duel 64', S, '(world>=62&&world<=64)', '(world >= 62 && world <= 63)', 'rng_64'),
    ('Flicker misses 82', S, '(world>=79&&world<=82)', '(world >= 79 && world <= 81)', 'rng_82'),
    ('Flicker misses Uruk 100', S, 'world==100||world==101', 'world == 101', 'rng_100'),
    ('Flicker misses Arca 101', S, 'world==100||world==101', 'world == 100', 'rng_101'),
    ('Flicker misses character scene 93', S, '(world>=91&&world<=96)', '(world >= 94 && world <= 96) || world == 91 || world == 92', 'rng_93'),
    ('Flicker misses login 94', S, '(world>=91&&world<=96)', '(world >= 95 && world <= 96) || (world >= 91 && world <= 93)', 'rng_94'),
    ('Flicker misses Abyss 128', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 127) || (world >= 129 && world <= 140)', 'rng_128'),
    ('Flicker misses Abyss 130', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 129) || (world >= 131 && world <= 140)', 'rng_130'),
    ('Flicker misses Kanturu 137', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 136) || (world >= 138 && world <= 140)', 'rng_137'),
    ('Flicker misses Ignis 138', S, '(world>=110&&world<=140)', '(world >= 110 && world <= 137) || (world >= 139 && world <= 140)', 'rng_empty'),
    ('Flicker draws for Tormenta 141', S, '(world>=142&&world<=145)', '(world >= 141 && world <= 145)', 'rng_drawn'),
    ('Flicker misses 145', S, '(world>=142&&world<=145)', '(world >= 142 && world <= 144)', 'rng_drawn'),
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
