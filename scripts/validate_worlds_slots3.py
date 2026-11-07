#!/usr/bin/env python3
"""RENDER-WORLDS-SLOTS3 instruction comparisons (docs/research/client-worlds-slots3.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  rng_<world>   RenderObjectVisual 0x017f9758 from its entry for one object of a world without a class registration
                (Tormenta 141: through its class slot 0x34 0x00e4ef4b, entered as the world manager calls it): the
                model lookup, the outer rand() % 30 (0x017f9797), the world switch 0x017f97e2, then the inline case or
                the default branch's hooks as client code (the world manager stubbed). Every rand() call is labelled
                outer (its return address 0x017f979c) or inner. The native side is the object runtime's composition
                on one generator: mu_obj_visual_flicker's draw, then the world's native visual with the same stream
                (the particle visual with the drawn value as outer_rand: 0..3, 141; mu_builtin_visual, whose first
                draw is the outer one: 4, 7, 8; mu_kanturu_flames, with a model: 37, 40; Icarus 10 and every other
                world: nothing that draws). RENDER-WORLDS-121: Devias 2 runs with a model whose action table
                (+0x30), action count (+0x26) and whole frame (+0xb4) reach type 0x67's action choice 0x017f9d79
                (SetAction 0x012affa4 as client code); the native composition adds mu_devias_action_pick after
                the outer draw, and the object after the call is compared too.
                A branch the native ports: the whole labelled sequence and the generator after it. A branch the
                native does not port (the world has no native visual, or NOT_PORTED): the sequence up to the world
                switch, i.e. the outer draw and the generator after it; the client's further draws are counted
                ('inner draws not ported'), and a client run that stops after the switch (a hook reads an input
                that is not mapped) is counted, not compared further.
  rng_other     the same for every other world id 0..145 without a class registration (the sequence up to the
                switch).
The first 301 cases of a family sweep the object type 0..300; the rest draw the world's named types or any type. One
case in eight has no model (the client returns before the draw).
"""
import argparse, ctypes as C, json, math, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_slots2 as w2
from unicorn.x86_const import UC_X86_REG_ESP

ROOT = Path(__file__).resolve().parents[1]
VISUAL, OUTER_SITE, SWITCH, EPILOGUE = 0x17f9758, 0x17f979c, 0x17f97e2, 0x17fccc1
TORMENTA_SLOT = 0xe4ef4b
HEAP = 0x2a800000
NAMED_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p, C.POINTER(C.c_float), C.POINTER(C.c_float))
CLASS_WORLDS = {57, 58, 62, 63, 64, 69, 70, 71, 72, 79, 80, 81, 82, 91, 92, 93, 94, 95, 96, 100, 101} | \
    set(range(110, 146))
# worlds whose native composition draws after the outer draw (all their branches compared whole, but NOT_PORTED)
FULL = [0, 1, 2, 3, 4, 7, 8, 10, 37, 40, 141]
# the worlds without a class that have a terrain (Data/World<n + 1>) and no native visual that draws
OUTER = [6, 9, 11, 18, 24, 30, 31, 33, 34, 38, 39, 41, 42, 46, 51, 56, 65, 66, 67, 68, 73, 74, 98, 102]
OTHER = [w for w in range(146) if w not in CLASS_WORLDS and w not in FULL and w not in OUTER]
# branches of a FULL world that the native visual does not port (their draws after the outer one are counted)
NOT_PORTED = {37: {0x25, 0x3e, 0x51, 0x53, 0x5c, 0x62, 0x69},     # the Kanturu hook 0x00e75089 past its flames
              40: {0x25, 0x3e, 0x51, 0x53, 0x5c, 0x62, 0x69}}
# types the world's branches name (drawn more often than the sweep)
TYPES = {0: [0x38, 0x69], 1: [0x3d], 2: [0x64, 0x67], 3: [1, 9, 0x11, 0x23, 0x27], 4: [19, 20, 23, 40, 41],
         8: [60, 63, 70, 76, 83], 10: [10], 37: [0x3b, 0x3d, 0x46, 0x25, 0x3e, 0x51, 0x53, 0x5c, 0x62, 0x69],
         40: [0x3b, 0x3d, 0x46, 0x25, 0x51, 0x53, 0x5c, 0x62, 0x69],
         141: [2, 3, 4, 5, 9, 0xbf, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5]}


class Library(w2.Library):
    def __init__(self, path, particles):
        super().__init__(path)
        d, P, I, F = self.dll, C.c_void_p, C.c_int32, C.c_float
        d.mu_builtin_visual.argtypes = [P, I, I, C.c_int, F, v.RAND_FN, NAMED_FN, P, C.POINTER(v.Log)]
        d.mu_builtin_visual.restype = C.c_int
        d.mu_kanturu_flames.argtypes = [P, I, I, F, v.RAND_FN, w2.BONE_FN, P, C.POINTER(v.Log)]
        d.mu_kanturu_flames.restype = C.c_int
        d.mu_devias_action_pick.argtypes = [P, C.c_int16, C.c_int16, I, v.RAND_FN, P]   # RENDER-WORLDS-121
        d.mu_devias_action_pick.restype = C.c_int
        self.particles = vp.load_library(particles)


DEVIAS_ACTIONS = 8   # RENDER-WORLDS-121: Devias 2's model action table (16-byte records, keys at +8)


def devias_case(g, raw):
    """Devias 2: the object's action inside the table, and a model (+0x26 action count, +0x30 the table, +0xb4 the
    whole frame) whose frame is the action's last key in most cases. Returns (raw, model, table)."""
    raw = bytearray(raw)
    action = g.choice([0, 0, 1, 1, 2, g.randrange(DEVIAS_ACTIONS)])
    struct.pack_into('<H', raw, 0x2a, action)
    table = bytearray(16 * DEVIAS_ACTIONS)
    for k in range(DEVIAS_ACTIONS):
        struct.pack_into('<h', table, 16 * k + 8, g.choice([1, 2, 10, 30, g.randrange(-3, 60)]))
    keys = struct.unpack_from('<h', table, 16 * action + 8)[0]
    model = bytearray(0x100)
    struct.pack_into('<h', model, 0x26, g.choice([DEVIAS_ACTIONS, 2, 1, 0, g.randrange(-2, 10)]))
    struct.pack_into('<I', model, 0x30, v.ACTIONS)
    struct.pack_into('<h', model, 0xb4, keys - 1 if g.random() < 0.6 else g.choice([keys, keys - 2, 0, -1]))
    return raw, bytes(model), bytes(table)


def run_original(machine, world, raw, present, time, seed, model=None, table=None):
    """RenderObjectVisual for one object: the labelled rand calls, the generator after each, the stop if any, the
    object after the call."""
    rnd = v.MsvcRand(seed)
    labels, states = [], []
    brk = [HEAP]

    def rand(m):
        ret = struct.unpack('<I', bytes(m.uc.mem_read(m.uc.reg_read(UC_X86_REG_ESP), 4)))[0]
        labels.append('outer' if ret == OUTER_SITE else 'inner')
        value = rnd()
        states.append(rnd.seed)
        return value

    def transform(m):
        a = [m.argument(k) for k in range(4)]
        k = (a[0] - 0x6fce398) // 0x30
        local = struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12)))
        m.uc.mem_write(a[2], v.pack_f(*w2.bone_point(k, local)))
        return (0, 16)

    def malloc(m):   # the C runtime heap (Noria 0x27's std::vector of bone names)
        at = brk[0]
        brk[0] += max((m.argument(0) + 15) & ~15, 16)
        return at
    regions = v.global_regions(world, 6, [
        am.defined_region('object', v.OBJECTS, bytes(raw)),
        am.defined_region('model', v.MODEL, model or bytes(0x100)),
        am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
        am.defined_region('weather', w2.WEATHER, struct.pack('<i', 0)),
        am.defined_region('static', w2.STATIC, w2.static_region(machine)),
        am.defined_region('singleton', w2.SING, w2.singleton(), writable=False),
        am.defined_region('handler', w2.HANDLER, v.fake_object(), writable=False),
        am.defined_region('heap', HEAP, bytes(0x10000))] +
        ([am.defined_region('actions', v.ACTIONS, table, writable=False)] if table else []))
    manager = w2.enter(TORMENTA_SLOT, w2.HANDLER, lambda: None) if world == 141 else (lambda m: (0, 8))
    stubs = {vp.MODEL_CONTAINER: lambda m: v.FAKE, vp.MODEL_GET: lambda m: (v.MODEL if present else 0, 4),
             w2.RAND: rand, w2.STATIC_GET: lambda m: w2.STATIC, w2.SINGLETON: lambda m: w2.SING,
             w2.MANAGER_GET: lambda m: w2.s2.REGISTRY, w2.MANAGER: manager,
             vp.TRANSFORM_POSITION: transform, vp.BONE_MATRIX: lambda m: (0x6fce398, 8),
             vp.CRT_MALLOC: malloc, vp.CRT_FREE: lambda m: 0,
             vp.CREATE_PARTICLE: lambda m: 0, vp.CREATE_SPRITE: lambda m: 0, vp.CREATE_EFFECT: lambda m: 0,
             vp.CREATE_JOINT: lambda m: 0, 0xa6ac96: lambda m: 0, 0x16cacfc: lambda m: 0, 0x16d9f51: lambda m: 0,
             vp.SINE: lambda m: m.x87_return(v.f32(math.sin(v.from_bits(m.argument(0))))),
             vp.COSINE: lambda m: m.x87_return(v.f32(math.cos(v.from_bits(m.argument(0))))),
             0x961a07: lambda m: m.x87_return(v.f32(math.sqrt(abs(v.from_bits(m.argument(0))))))}
    result = machine.execute(VISUAL, [v.OBJECTS], regions, stubs)
    return labels, states, v.stopped_reason(result), result.get('regions', {}).get('object')


def run_native(lib, world, raw, present, time, seed, model=None, table=None):
    """The object runtime's composition: the outer draw, then the world's native visual, on one generator."""
    rnd = v.MsvcRand(seed)
    labels, phase = [], ['outer']

    def draw(ctx):
        labels.append(phase[0])
        phase[0] = 'inner'
        return rnd()
    fn = v.RAND_FN(draw)
    d = lib.dll
    o = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
    log = v.new_log()
    outer = fn(None) if d.mu_obj_visual_flicker(world, present) else 0
    phase[0] = 'inner'

    def named_cb(ctx, name, local, out):
        for q in range(3):
            out[q] = local[q] + 3.0

    def bone_cb(ctx, k, local, out):
        for q, value in enumerate(w2.bone_point(k, tuple(local[:3]))):
            out[q] = value
    if world in (0, 1, 2, 3, 141):
        typ, = struct.unpack_from('<i', raw, 0x5c)
        f3 = lambda at: vp.F3(*struct.unpack_from('<3f', raw, at))
        vo = vp.VisualObject(0, typ, f3(0x158), f3(0x164), f3(0xec), struct.unpack_from('<f', raw, 0xa0)[0], 0.0, 0.0)
        fns = (fn, vp.HAS_MODEL_FN(lambda c, ob: int(present)),
               vp.BONE_FN(lambda c, ob, name, vin, vout: None), vp.VPARTICLE_FN(lambda *a: None),
               vp.VSPRITE_FN(lambda *a: None), vp.VJOINT_FN(lambda *a: None), vp.VEFFECT_FN(lambda *a: None))
        host = vp.VisualHost(None, *fns, world, time, vp.BONE_INDEX_FN(lambda *a: None), outer)
        lib.particles.mu_pt_object_visual(C.byref(vo), C.byref(host))
        if world == 2 and present:   # RENDER-WORLDS-121: the object runtime's Devias 0x67 choice after the outer draw
            action = struct.unpack_from('<H', raw, 0x2a)[0]
            keys = struct.unpack_from('<h', table, 16 * action + 8)[0]
            d.mu_devias_action_pick(o, struct.unpack_from('<h', model, 0xb4)[0], keys,
                                    struct.unpack_from('<h', model, 0x26)[0], fn, None)
    elif world in (4, 7, 8):   # the runtime's handler_visual; mu_builtin_visual draws the outer rand itself
        phase[0] = 'outer'
        d.mu_builtin_visual(o, 0, world, present, time, fn, NAMED_FN(named_cb), None, C.byref(log))
    elif world in (37, 40) and present:   # world_flames: with a model only
        d.mu_kanturu_flames(o, 0, world, time, fn, w2.BONE_FN(bone_cb), None, C.byref(log))
    return labels, rnd.seed, o.raw[:v.OBJ_SIZE]


def ported(world, typ):
    return world in FULL and typ not in NOT_PORTED.get(world, ())


def rng_family(machine, lib, g, cases, worlds, name):
    t = v.Tally(name)
    for n in range(cases):
        world = worlds[n % len(worlds)]
        typ = n if n <= 300 and len(worlds) == 1 else \
            g.choice(TYPES[world]) if world in TYPES and g.random() < 0.6 else g.randrange(0, 301)
        present = g.random() >= 0.125
        raw = w2.case_object(g, world, typ)
        model = table = None
        if world == 2:
            raw, model, table = devias_case(g, raw)
        time, seed = w2.case_time(g), g.randrange(2**32)
        labels, states, stop, client_object = run_original(machine, world, raw, present, time, seed, model, table)
        native, state, native_object = run_native(lib, world, raw, present, time, seed, model, table)
        detail = {'case': n, 'world': world, 'type': typ, 'present': present, 'client': labels[:8],
                  'native': native[:8]}
        whole = ported(world, typ)
        if stop:
            # only a stop after the world switch, with the outer draw done, in a branch compared up to the switch
            pc = int(stop['stopped'][-1], 16) if isinstance(stop.get('stopped'), tuple) else VISUAL
            if whole or not present or labels[:1] != ['outer'] or VISUAL <= pc < SWITCH:
                t.add(False, detail, stop)
                continue
            t.count('client stopped after the switch (not ported)')
        if whole:
            ok = labels == native and state == (states[-1] if states else seed)
            if world == 2:   # RENDER-WORLDS-121: SetAction's writes (action, prior action, frames)
                ok = ok and client_object == native_object
                if typ == 0x67 and present:
                    t.count('0x67 action choice drawn' if len(labels) > 1 else '0x67 not at its last key')
            t.count('compared whole')
            if len(labels) > 1:
                t.count('inner draws compared')
        else:
            first = labels[:1]
            ok = native == first and labels.count('outer') == len(first) and \
                state == (states[0] if first else seed)
            t.count('compared to the switch')
            if len(labels) > 1:
                t.count('inner draws not ported: world %d type %#x' % (world, typ))
        t.count('outer drawn' if 'outer' in labels else 'no outer draw')
        t.add(ok, detail)
    return t


def family(worlds, name):
    return lambda machine, lib, g, cases: rng_family(machine, lib, g, cases, worlds, name)


FAMILIES = {'rng_%d' % w: family([w], 'rng_%d' % w) for w in FULL + OUTER}
FAMILIES['rng_other'] = family(OTHER, 'rng_other')

O, P = 'world_slots2_visual.c', 'visual.c'
OBJ, PART = 'objects', 'particles'
MUTATIONS = [
    # the one outer draw of the object runtime
    ('Flicker misses Lorencia 0', OBJ, O, 'returnworld!=4&&', 'return world != 0 && world != 4 && ', 'rng_0'),
    ('Flicker misses Dungeon 1', OBJ, O, 'returnworld!=4&&', 'return world != 1 && world != 4 && ', 'rng_1'),
    ('Flicker misses Devias 2', OBJ, O, 'returnworld!=4&&', 'return world != 2 && world != 4 && ', 'rng_2'),
    ('Flicker misses Noria 3', OBJ, O, 'returnworld!=4&&', 'return world != 3 && world != 4 && ', 'rng_3'),
    ('Flicker misses Arena 6', OBJ, O, 'returnworld!=4&&', 'return world != 6 && world != 4 && ', 'rng_6'),
    ('Flicker misses Icarus 10', OBJ, O, 'returnworld!=4&&', 'return world != 10 && world != 4 && ', 'rng_10'),
    ('Flicker misses Aida 33', OBJ, O, 'returnworld!=4&&', 'return world != 33 && world != 4 && ', 'rng_33'),
    ('Flicker misses Kanturu 37', OBJ, O, 'returnworld!=4&&', 'return world != 37 && world != 4 && ', 'rng_37'),
    ('Flicker misses Kanturu Relics 38', OBJ, O, 'returnworld!=4&&', 'return world != 38 && world != 4 && ',
     'rng_38'),
    ('Flicker misses 40', OBJ, O, 'returnworld!=4&&', 'return world != 40 && world != 4 && ', 'rng_40'),
    ('Flicker misses Elbeland 51', OBJ, O, 'returnworld!=4&&', 'return world != 51 && world != 4 && ', 'rng_51'),
    ('Flicker misses Swamp of Calmness 56', OBJ, O, 'returnworld!=4&&', 'return world != 56 && world != 4 && ',
     'rng_56'),
    ('Flicker misses Tormenta 141', OBJ, O, 'returnworld!=4&&', 'return world != 141 && world != 4 && ', 'rng_141'),
    ('Flicker misses a world past 102', OBJ, O, 'returnworld!=4&&', 'return world < 103 && world != 4 && ',
     'rng_other'),
    ('Flicker without the model gate', OBJ, O, 'if(!has_model)return0;', 'if (!has_model && world < 0) return 0;',
     'rng_6'),
    ('Flicker also in Lost Tower 4', OBJ, O, 'world!=4&&world!=7', 'world != 7', 'rng_4'),
    ('Flicker also in Atlans 7', OBJ, O, '&&world!=7&&', ' && ', 'rng_7'),
    ('Flicker also in Tarkan 8', OBJ, O, '&&world!=8;', ';', 'rng_8'),
    # the particle visual reads the drawn value; a draw of its own is the stand-in this lane removed
    ('Particle visual draws the outer rand (Lorencia)', PART, P, 'constfloatl=(float)(h->outer_rand%30+70)*0.01f;',
     'const float l = (float)(vrand(h) % 30 + 70) * 0.01f;', 'rng_0'),
    ('Particle visual draws the outer rand (Tormenta)', PART, P, 'constfloatl=(float)(h->outer_rand%30+70)*0.01f;',
     'const float l = (float)(vrand(h) % 30 + 70) * 0.01f;', 'rng_141'),
    ('Built-in visual skips its first draw', OBJ, 'world_builtin_visual.c',
     'constfloatl=(float)(random(ctx)%30+70)*0.01f;', 'const float l = 0.7f;', 'rng_8'),
    ('Kanturu flame 0x3b without its draw', OBJ, 'world_kanturu_visual.c', 'case0x3b:if(rnd(c)%3==0)',
     'case 0x3b: if (0)', 'rng_37'),
]


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    subprocess.run(['make', '-s', '-C', str(root / 'particles')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX),
                   root / 'particles' / ('libclient_particles.' + v.SUFFIX))


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
    machine = w2.Machine(text, data)
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0x5103 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:1500], flush=True)
    if a.mutations:
        for label, directory, file, old, new, fam in MUTATIONS:
            if fam not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-slots3-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / directory / file
                s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                s, count = re.subn(pattern, lambda m: new, s, count=1)
                assert count == 1, (label, old)
                assert len(re.findall(pattern, path.read_text())) == 1, (label, 'anchor not unique')
                path.write_text(s)
                tally = FAMILIES[fam](machine, build(root), seed(fam), a.cases)
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
