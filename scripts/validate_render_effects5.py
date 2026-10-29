#!/usr/bin/env python3
"""RENDER-EFFECTS-005: rank-5 item owner effects and their particle kinds.

owner: the complete RenderObjDraw 0x0176ce74 for all nineteen rank-5 types runs
under Unicorn (the validate_item_next harness), with the real pose call, the
real bone lookup 0x0129f12c and the real TransformPosition 0x012b6ef1. OBJECT
+0x318 and the model bone count are installed after the pose call. rand() is a
scripted stream; the named-mesh lookup, CreateParticle 0x0168fafd and
CreateSprite 0x01692eb7 are recording stubs. The authored C runs the existing
rank-5 body (mu_rc_item_draws_context) followed by mu_rc_rank5_owner. The
complete mesh stream, every emitted effect (fields bit for bit, including the
fixed angle/owner/sheet arguments) and the number of rand() calls must agree.

pt_create/pt_move/pt_render: the CreateParticle core, MoveParticles and
RenderParticles record bodies for 0x84e2/0 and 0x83de/4 (validate_particles).
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile

import actor_machine as am
import pins
import item_pose_machine as pose
import validate_renderchar as v
import validate_item_next as nxt
import validate_particles as pt
import validate_worlds_m as wm

ROOT = Path(__file__).resolve().parents[1]
OWNER_BONES = 0x2e000000
KINDS = [(0x84e2, 0), (0x83de, 4)]
BONE_COUNTS = (0, 26, 35, 36, 40, 64)
LEVELS = (-1, 0, 8 << 3, 9 << 3, (9 << 3) | 5, 13 << 3, 15 << 3, 0x7f, -8)


class Fx(C.Structure):
    _fields_ = [('kind', C.c_int32), ('bitmap', C.c_int32), ('subtype', C.c_int32),
                ('position', C.c_float * 3), ('light', C.c_float * 3), ('scale', C.c_float)]


TRANSFORM = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))
EMIT = C.CFUNCTYPE(None, C.c_void_p, C.POINTER(Fx))


class Host(C.Structure):
    _fields_ = [('bones', C.c_int32), ('black_mesh', C.c_int32), ('transform', TRANSFORM),
                ('random', nxt.clusters.RANDOM), ('emit', EMIT), ('context', C.c_void_p)]


def u(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def particles_library():
    lib = C.CDLL(str(ROOT/'reconstructed/particles/libclient_particles.dylib'))
    lib.mu_pt_transform_position.argtypes = [C.POINTER(C.c_float)]*3 + [C.c_int, C.c_float, C.POINTER(C.c_float)]
    return lib


LIFETIMES = [-1, 0, 1, 2, 4, 5, 6, 9, 10, 11, 19, 20, 21, 3, 7]


def compare_particles(text, data, lib, family, kinds, cases):
    """validate_particles over the two kinds with directed fade boundaries
    (lifetime*2 against the initial lifetime 10/20)."""
    original = pt.random_particle
    index = 0

    def directed(rng, kind):
        nonlocal index
        p = original(rng, kind)
        step = index // len(kinds)
        p.lifetime = LIFETIMES[step % len(LIFETIMES)]
        p.initial_lifetime = (10, 20, 2 * p.lifetime, 2 * p.lifetime + 1, p.initial_lifetime)[(step // len(LIFETIMES)) % 5]
        index += 1
        return p
    try:
        pt.random_particle = directed
        return wm.base.compare(text, data, lib, 'pt', family, kinds, cases)
    finally:
        pt.random_particle = original


def owner_case(t, k):
    """One authored state: body record inputs, owner bones, named meshes and rand()."""
    rng = random.Random(t*7919 + k)
    case = v.random_case_any(rng, t)
    case.update(a10=0xffffffff, a11=0xffffffff, record=None, quality=(5, 5, 1, 2, 3, 4)[k % 6])
    case['item_level'] = LEVELS[k % len(LEVELS)] & 0xffffffff if k % 3 else rng.randrange(16) << 3
    if case['item_level'] >= 0x80000000:
        case['item_level'] -= 1 << 32
    bones = BONE_COUNTS[(k // 2) % len(BONE_COUNTS)] if k % 2 else rng.choice((36, 40, 64))
    # Records 0x26/0x5b force glow level 9 independent of the raw level word.
    case['record'] = (None, None, (0, 0x26, 0), (0, 0x5b, 0), (6, 0, 0))[(k // 5) % 5]
    lighting = 0 if k % 11 == 10 else 1
    blue, black = ((-1, -1), (3, 1), (4, 5), (0, -1))[(k // 3) % 4]
    stream = [rng.randrange(32768) for _ in range(64)]
    if k % 10 == 4:
        # Raw +8 with record kind B 0x26 (glow 9): the level word, not the glow level, gates the overlays.
        case.update(item_level=8 << 3, record=(0, 0x26, 0), quality=5)
        lighting, bones = 1, 40
    matrices = [rng.uniform(-1.5, 1.5) if c % 4 != 3 else rng.uniform(-200, 200)
                for _ in range(max(bones, 1)) for c in range(12)]
    scale = rng.choice((1.0, 0.75, 1.3, rng.uniform(0.5, 2)))
    origin = [rng.uniform(-300, 300) for _ in range(3)]
    return case, dict(bones=bones, lighting=lighting, blue=blue, black=black, stream=stream,
                      matrices=matrices, scale=scale, origin=origin)


def original_owner(wa, case, o):
    payload = pose.seed()
    calls = []
    effects = []

    def rand(mm):
        value = o['stream'][len(calls) % len(o['stream'])]
        calls.append(value)
        return value

    class World(v.World):
        def __init__(self, *args):
            super().__init__(*args)
            m = self.m
            m.write(pose.pose.WINDOW, payload)
            m.heap = pose.pose.WINDOW + 0x100000
            m.ensure(pose.pose.ROOT_MATRIX, 48)
            m.write(pose.pose.ROOT_MATRIX, struct.pack('<12f', 1, 0, 0, 4, 0, 1, 0, 5, 0, 0, 1, 6))
            m.ensure(0x06fce398, 0x1000)
            m.ensure(pose.pose.QUATERNIONS, 32)
            m.map(OWNER_BONES, 0x4000)
            m.write(OWNER_BONES, struct.pack('<%df' % len(o['matrices']), *o['matrices']))
            m.stub(0x01989721, rand, 0)

            def named(mm):
                addr = mm.arg(0)
                n = mm.r32(addr + 16)
                data = addr if mm.r32(addr + 20) < 16 else mm.r32(addr)
                name = mm.read(data, n)
                return (o['blue'] if b'Blue' in name else o['black']) & 0xffffffff
            m.stub(0x012bd4a6, named, 4)

            def vec(mm, a):
                return list(struct.unpack('<3I', mm.read(a, 12)))

            def particle(mm):
                a = [mm.arg(i) for i in range(8)]
                effects.append(('particle', a[0], vec(mm, a[1]), vec(mm, a[2]), vec(mm, a[3]), a[4], a[5], a[6], a[7]))
                return 0
            m.stub(0x0168fafd, particle, 0)

            def sprite(mm):
                a = [mm.arg(i) for i in range(9)]
                effects.append(('sprite', a[0], vec(mm, a[1]), a[2], vec(mm, a[3]), a[4], a[5], a[6], a[7],
                                vec(mm, a[8])))
                return 0
            m.stub(0x01692eb7, sprite, 0)

            from unicorn import UC_HOOK_CODE

            def install(uc, address, size, context):
                # After the real pose call: the OBJECT owner's skeleton.
                m.write(v.MODEL + 0x22, struct.pack('<h', o['bones']))
                m.w32(v.OBJ + 0x318, OWNER_BONES if o['bones'] else 0)
                m.wf(v.MODEL + 0x74, o['scale'])
                m.write(v.MODEL + 0x78, struct.pack('<3f', *o['origin']))
            m.uc.hook_add(UC_HOOK_CODE, install, begin=0x01747a0a, end=0x01747a0a)

        def add_model(self, *args, **kwargs):
            super().add_model(*args, **kwargs)
            m = self.m
            m.write(v.MODEL + 0x22, struct.pack('<hhh', 2, 6, 2))
            m.write(v.MODEL + 0x2c, payload[0x2c:0x34])
            m.w32(v.MODEL + 0x60, 0xffffffff)
            m.write(v.MODEL + 0x50, bytes([o['lighting']]))
            m.wf(v.MODEL + 0x74, 1)
            m.write(v.OBJ + 0x2c, struct.pack('<H', 1))
            m.write(v.OBJ + 0xd0, struct.pack('<2f', 0.5, 1.0))

    result, stream, other, _ = v.client_stream(wa, case, World)
    unexpected = [c for c in other if c[0] not in ('transform',)]
    if not result['ok'] or unexpected:
        raise AssertionError(('owner original', hex(case['type']), result, unexpected[:3]))
    return stream, effects, len(calls)


def c_owner(lib, plib, case, o):
    calls = []
    effects = []

    @nxt.clusters.RANDOM
    def rand(_):
        value = o['stream'][len(calls) % len(o['stream'])]
        calls.append(value)
        return value

    @TRANSFORM
    def transform(_, bone, local, out):
        matrix = (C.c_float * 12)(*o['matrices'][12*bone:12*bone+12])
        origin = (C.c_float * 3)(*o['origin'])
        plib.mu_pt_transform_position(matrix, local, out, 1, o['scale'], origin)

    @EMIT
    def emit(_, fx):
        f = fx.contents
        light = [u(x) for x in f.light]
        if f.kind == 1:
            effects.append(('particle', f.bitmap, [u(x) for x in f.position], [0, 0, 0], light, f.subtype,
                            u(f.scale), 0, 0))
        else:
            effects.append(('sprite', f.bitmap, [u(x) for x in f.position], u(f.scale), light, v.OBJ, 0, 0, 4,
                            [1, 1, u(1.0)]))

    context = nxt.Context(o['lighting'], o['blue'], rand, None)
    host = Host(o['bones'], o['black'], transform, rand, emit, None)

    class Adapter:
        def mu_rc_item_draws(self, *args):
            return lib.mu_rc_item_draws_owner(*args, C.byref(context), C.byref(host))
    status, stream = v.c_stream(Adapter(), case)
    return status, stream, effects, len(calls)


def owner_family(wa, lib, cases):
    plib = particles_library()
    vectors = []
    coverage = {'effects': 0, 'overlays': 0, 'stopped': 0}
    for t in pose.TYPES:
        for k in range(cases):
            case, o = owner_case(t, k)
            expected = original_owner(wa, case, o)
            status, stream, effects, consumed = c_owner(lib, plib, case, o)
            if status or (stream, effects, consumed) != expected:
                raise AssertionError(('owner', hex(t), k, o['bones'], case['item_level'], expected, (status, stream, effects, consumed)))
            coverage['effects'] += len(effects)
            coverage['stopped'] += not effects
            coverage['overlays'] += len(stream) - len(c_body(lib, case, o))
            vectors.append((case, o, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'coverage': coverage}, vectors


def c_body(lib, case, o):
    calls = []

    @nxt.clusters.RANDOM
    def rand(_):
        value = o['stream'][len(calls) % len(o['stream'])]
        calls.append(value)
        return value
    context = nxt.Context(o['lighting'], o['blue'], rand, None)

    class Adapter:
        def mu_rc_item_draws(self, *args):
            return lib.mu_rc_item_draws_context(*args, C.byref(context))
    return v.c_stream(Adapter(), case)[1]


OWNER_MUTANTS = {
    'jitter-modulo': ('{24, 20, 10}', '{24, 20, 11}'),
    'jitter-centre': ('{12.0f, 10.0f, 5.0f}', '{12.0f, 10.0f, 6.0f}'),
    'jitter-axes': ('targets[t][0] = targets[t][0] + x;', 'targets[t][0] = targets[t][0] + z;'),
    'particle-order': ('0x84e2, 0, b, bolt', '0x84e2, 0, a, bolt'),
    'bone-26': ('h->transform(h->context, 26,', 'h->transform(h->context, 25,'),
    'bone-gate': ('h->bones <= 35', 'h->bones <= 34'),
    'variant-b-scale': ('{20, 10, 20}, {10.0f, 5.0f, 10.0f}, 0.5f', '{20, 10, 20}, {10.0f, 5.0f, 10.0f}, 0.4f'),
    'glint': ('% 5) / 1.0f / 5.0f + 0.5f', '% 4) / 1.0f / 5.0f + 0.5f'),
    'smoke-light': ('{0.2f, 0.2f, 0.4f}', '{0.2f, 0.4f, 0.2f}'),
    'level-gate': ('& 15) < 9', '& 15) < 8'),
    'level-word': ('mu_rc_item_glow_level(it) < 9', 'mu_rc_item_glow_level(it) < 10'),
    'overlay-uv': ('it->time * 0.0001f', 'it->time * 0.00011f'),
    'black-alpha': ('6, 0.26f', '6, 0.25f'),
    'variant-list': ('case 0x1c2b: return 1;', 'case 0x1c2b: return 3;'),
}
PARTICLE_MUTANTS = [
    ('bolt-life', 'p->initial_lifetime = 10;', 'p->initial_lifetime = 11;', 'create', (0x84e2, 0)),
    ('smoke-alpha', 'p->alpha = 1.0f;', 'p->alpha = 0.9f;', 'create', (0x83de, 4)),
    ('bolt-fade', 'p->initial_lifetime < p->lifetime * 2', 'p->initial_lifetime <= p->lifetime * 2', 'move', (0x84e2, 0)),
    ('smoke-fade', 'p->alpha = p->alpha - step;', 'p->alpha = p->alpha - step * 0.5f;', 'move', (0x83de, 4)),
    ('alpha-light', 'p->light[k] * p->alpha;', 'p->light[k];', 'render', (0x84e2, 0)),
]


def owner_mutants(vectors):
    source = (ROOT/'reconstructed/renderchar/rank5_owner.inc').read_text()
    plib = particles_library()
    caught = {}
    with tempfile.TemporaryDirectory(prefix='render-effects5-') as tmp:
        for name, (old, new) in OWNER_MUTANTS.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor', name, source.count(old)))
            folder = Path(tmp)/name
            folder.mkdir()
            (folder/'rank5_owner.inc').write_text(source.replace(old, new))
            (folder/'renderchar.c').write_text((ROOT/'reconstructed/renderchar/renderchar.c').read_text())
            library = folder/'lib.dylib'
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(folder/'renderchar.c'),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)],
                           check=True)
            lib = C.CDLL(str(library))
            detected = 0
            for case, o, expected in vectors:
                status, stream, effects, consumed = c_owner(lib, plib, case, o)
                detected += bool(status) or (stream, effects, consumed) != expected
            caught[name] = {'cases': len(vectors), 'caught': detected}
    return caught


def particle_mutants(text, data, cases):
    caught = {}
    source = ROOT/'reconstructed/particles'
    original = (source/'owner_fx.inc').read_text()
    with tempfile.TemporaryDirectory(prefix='render-effects5-pt-') as tmp:
        for name, old, new, family, kind in PARTICLE_MUTANTS:
            if original.count(old) != 1:
                raise AssertionError(('mutant anchor', name))
            folder = Path(tmp)/name
            folder.mkdir()
            (folder/'owner_fx.inc').write_text(original.replace(old, new))
            (folder/'particles.c').write_text((source/'particles.c').read_text())
            out = folder/'lib.dylib'
            subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared',
                            '-I', str(source), str(folder/'particles.c'),
                            *[str(source/p) for p in ('world_flames.c', 'elbeland.c', 'sprites.c', 'shadow.c',
                              'visual.c', 'layout.c', '../record-math/record_math.c')], '-lm', '-o', str(out)],
                           check=True, capture_output=True)
            r = compare_particles(text, data, pt.load_library(out), family, [kind], cases)
            f = r['families'][family]
            caught[name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    return caught


def registrations(text, data):
    """LoadBitmap calls for the two particle bitmaps (0x0182509b / 0x0182eb8e)."""
    import validate_render_effects as base
    out = []
    for start, site, bitmap, path, wrap in ((0x0182508d, 0x018250a5, 0x83de, 'Effect\\smoke_line03.jpg', 0x2900),
                                            (0x0182eb80, 0x0182eb98, 0x84e2,
                                             'Item\\texture\\lighting01_10cha.jpg', 0x2901)):
        m = base.fx.FxMachine(text, data)
        calls = []

        def load(mm):
            args = [mm.argument(i) for i in range(6)]
            at = args[0] - am.DATA_BASE
            calls.append([data[at:at+256].split(b'\0')[0].decode('ascii'), *args[1:]])
            return 1
        r = m.execute(start, [], [], {0x0185baac: load, site + 8: lambda mm: 0})
        out.append({'call': hex(site), 'path': path, 'bitmap': hex(bitmap), 'wrap': hex(wrap),
                    'equal': base.fx.vc.ok(r) and calls == [[path, bitmap, 0x2601, wrap, 1, 0]]})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=60, help='owner cases per rank-5 type')
    p.add_argument('--particle-cases', type=int, default=500)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    for d in ('renderchar', 'model-codec', 'particles'):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed'/d)], check=True)
    wa = tuple(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}, 'mutants': {}}
    report['families']['owner'], vectors = owner_family(wa, lib, a.cases)
    plib = pt.load_library(ROOT/'reconstructed/particles/libclient_particles.dylib')
    for name in ('create', 'move', 'render'):
        r = compare_particles(text, data, plib, name, KINDS, a.particle_cases)
        f = r['families'][name]
        report['families']['pt_' + name] = {'cases': f['cases'], 'mismatches': f['cases'] - f['equal'],
                                            'coverage': r['coverage'][name]}
    report['registrations'] = registrations(text, data)
    if a.mutations:
        report['mutants'].update(owner_mutants(vectors))
        report['mutants'].update(particle_mutants(text, data, max(100, a.particle_cases // 5)))
    bodies = {'owner_blue': (0x01747d6d, 0x01748625), 'owner_1c2b': (0x0174888d, 0x0174902c),
              'owner_b': (0x01749294, 0x01749a5d), 'owner_a': (0x01749cc5, 0x0174a489),
              'bone_lookup': (0x0129f12c, 0x0129f18a), 'random_scale': (0x0185caa4, 0x0185cb01),
              'bolt_create': (0x0160eb26, 0x0160ebdd), 'smoke_create': (0x015d1f29, 0x015d1fc3),
              'bolt_move': (0x01686f81, 0x016870b6), 'smoke_move': (0x0164455b, 0x016445f6),
              'bolt_render': (0x015a7521, 0x015a761d), 'smoke_render': (0x015a3c58, 0x015a3d35)}
    report['bodies'] = {k: hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()[:16]
                        for k, (s, e) in bodies.items()}
    report['instruction_cases'] = sum(f['cases'] for f in report['families'].values())
    report['all_equal'] = all(f['mismatches'] == 0 for f in report['families'].values()) and all(
        r['equal'] for r in report['registrations'])
    report['all_mutants_caught'] = all(m['caught'] > 0 for m in report['mutants'].values())
    text_out = json.dumps(report, indent=2) + '\n'
    if a.output:
        a.output.write_text(text_out)
    print(text_out)
    raise SystemExit(not (report['all_equal'] and (not a.mutations or report['all_mutants_caught'])))


if __name__ == '__main__':
    main()
