#!/usr/bin/env python3
"""Part 17 bodies (RENDER-ITEMS-002Q): owner-effect programs of the armour bodies 0x1bc3..0x1c78 and five helm
bodies versus the pinned instructions.

bodies: the 292 survey states of every type, client RenderObjDraw 0x0176ce74 against mu_rc_item_draws_context
  (no owner host). The client's effect requests are set aside; the library creates none and draws no rand.
owner: the complete RenderObjDraw with an OBJECT owner skeleton: OBJECT +0x318 points at authored bone matrices,
  the model's bone count (+0x22, read by 0x012b678d and 0x0129f12c), its scale (+0x74), the OBJECT position
  (+0x158) and angle (+0x164) are random; rand() returns a scripted sequence. The real 0x012b678d, 0x011ff622
  and vec3 helpers run; CreateSprite 0x01692eb7 and CreateParticle 0x0168fafd are recording stubs. The C runs
  mu_rc_item_draws_owner with a host whose transform is 0x012b678d's arithmetic (TransformPosition of the owner
  bone with the model scale and the OBJECT position, reconstructed/particles). The draw stream, every effect
  request (all arguments bit for bit, including the fixed owner/rotation/sheet/axes words) and the number of
  rand() calls must agree. Directed states repeat bone matrices so a normalized difference is zero.
refusal: owner bone counts at or below the program's highest bone and states without OBJECT +0x318: the client
  reads stale positions or BoneTransform 0x06fce398, so the library must create no effect and draw no rand,
  while the draw stream still equals the client's.
The body table (gen_item_bodies) and the owner-effect table (gen_item_owner_fx) must reproduce from the pins.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile

import gen_item_bodies as gen
import gen_item_owner_fx as fxgen
import pins
import validate_item_quality as quality
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = fxgen.OWNER_FX_TYPES
OWNER_BONES = 0x2e000000
OBJ_ANGLE, OBJ_POSITION = 0x164, 0x158


class Fx(C.Structure):
    _fields_ = [('kind', C.c_int32), ('bitmap', C.c_int32), ('subtype', C.c_int32),
                ('position', C.c_float * 3), ('light', C.c_float * 3), ('scale', C.c_float),
                ('angle', C.c_float * 3),
                ('rotation', C.c_float), ('blend', C.c_int32), ('owner', C.c_int32),   # RENDER-ITEMS-002R
                ('target', C.c_float * 3),   # RENDER-ITEMS-002S: CreateJoint's target position
                ('extra', C.c_int32)]   # RENDER-ITEMS-002T: CreateParticle argument 8


TRANSFORM = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float))
EMIT = C.CFUNCTYPE(None, C.c_void_p, C.POINTER(Fx))
RANDOM = C.CFUNCTYPE(C.c_int32, C.c_void_p)
NAMED = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p)
ITEM_TRANSFORM = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.c_int32, C.POINTER(C.c_float))
OBJECT_TRANSFORM = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float))


class Host(C.Structure):
    _fields_ = [('bones', C.c_int32), ('black_mesh', C.c_int32), ('transform', TRANSFORM),
                ('random', RANDOM), ('emit', EMIT), ('context', C.c_void_p),
                ('item_bones', C.c_int32), ('angle', C.c_float * 3),
                # RENDER-ITEMS-002R pre-draw programs (NULL here: no item host)
                ('bone_named', NAMED), ('item_transform', ITEM_TRANSFORM), ('refuse', EMIT), ('visible', C.c_int32),
                ('position', C.c_float * 3),   # RENDER-ITEMS-002S: OBJECT +0x158
                # RENDER-ITEMS-002T: 0x012b678d on an item bone, the rendered-frame counter
                ('object_transform', OBJECT_TRANSFORM), ('frame', C.c_uint32), ('frame_known', C.c_int32)]


def u(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def need(t):
    return LIB.mu_rc_item_owner_fx(t)


def particles_library():
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/particles')], check=True)
    lib = C.CDLL(str(ROOT/'reconstructed/particles/libclient_particles.dylib'))
    lib.mu_pt_transform_position.argtypes = [C.POINTER(C.c_float)] * 3 + [C.c_int, C.c_float, C.POINTER(C.c_float)]
    return lib


def owner_setup(rng, t, k, refuse=False):
    """Owner skeleton, model scale, OBJECT position/angle and rand sequence of one state."""
    n = need(t)
    if refuse:
        bones = (n - 1, max(n - 5, 1), 0, n - 1)[k % 4]
        attached = k % 4 != 2
    else:
        bones = (n, n + 1, 40, 64, rng.randrange(n, 80))[k % 5]
        attached = True
    matrices = [rng.uniform(-1.5, 1.5) if c % 4 != 3 else rng.uniform(-200, 200)
                for _ in range(max(bones, 1)) for c in range(12)]
    if k % 7 == 3 and bones > 26:
        # Directed: bones 19 and 26 share a matrix, so the normalized difference of their positions is zero.
        matrices[12 * 19:12 * 20] = matrices[12 * 26:12 * 27]
    if k % 11 == 5:
        matrices = [round(x) for x in matrices]   # exact small integers: repeated positions, zero jitter sums
    return dict(bones=bones, attached=attached, matrices=matrices,
                scale=rng.choice((1.0, 0.75, 1.3, rng.uniform(0.5, 2))),
                position=[rng.uniform(-3000, 3000) for _ in range(3)],
                angle=[rng.choice((0.0, 90.0, rng.uniform(-360, 360))) for _ in range(3)],
                stream=quality.sequence_for(rng) + [rng.randrange(32768) for _ in range(64)])


def original(wa, reset, case, o):
    """Client stream, effect requests and rand() count of one owner state."""
    effects, calls = [], []

    def factory(*args):
        world = reset(*args)
        m = world.m
        world.sequence, world.drawn = o['stream'], 0
        m.write(OWNER_BONES, struct.pack('<%df' % len(o['matrices']), *o['matrices']))
        world.owner = o
        world.effects = effects
        return world
    result, stream, other, m = v.client_stream(wa, case, factory)
    unexpected = [c for c in other if c[0] != 'effect']
    if not result['ok'] or unexpected:
        raise AssertionError(('owner original', hex(case['type']), result, unexpected[:3]))
    return stream, list(effects), reset.world.drawn


class OwnerWorld(quality.RandomWorld):
    """RandomWorld with the owner skeleton fields and recording effect stubs (all arguments)."""
    def __init__(self, *args):
        super().__init__(*args)
        self.m.map(OWNER_BONES, 0x10000)
        self.owner, self.effects = None, []

    def install(self):
        super().install()
        m = self.m

        def vec(mm, a):
            return list(struct.unpack('<3I', mm.read(a, 12)))

        def particle(mm):
            a = [mm.arg(i) for i in range(8)]
            self.effects.append(('particle', a[0], vec(mm, a[1]), vec(mm, a[2]), vec(mm, a[3]), a[4], a[5], a[6], a[7]))
            return 0
        m.stub(0x0168fafd, particle, 0)

        def sprite(mm):
            a = [mm.arg(i) for i in range(9)]
            self.effects.append(('sprite', a[0], vec(mm, a[1]), a[2], vec(mm, a[3]), a[4], a[5], a[6], a[7],
                                 vec(mm, a[8])))
            return 0
        m.stub(0x01692eb7, sprite, 0)

    def add_model(self, model_type, address, *args, **kwargs):
        super().add_model(model_type, address, *args, **kwargs)
        o, m = self.owner, self.m
        if o is None or address != v.MODEL:
            return
        m.write(v.MODEL + 0x22, struct.pack('<h', o['bones']))
        m.wf(v.MODEL + 0x74, o['scale'])
        m.w32(v.OBJ + 0x318, OWNER_BONES if o['attached'] else 0)
        m.write(v.OBJ + OBJ_POSITION, struct.pack('<3f', *o['position']))
        m.write(v.OBJ + OBJ_ANGLE, struct.pack('<3f', *o['angle']))


def run_c(lib, plib, case, o):
    """C stream, effect requests and rand() count of one owner state."""
    used, effects = [0], []
    stream_values = o['stream']

    def draw():
        used[0] += 1
        return stream_values[used[0] - 1] if used[0] <= len(stream_values) else 0

    @RANDOM
    def rand(_):
        return draw()

    @TRANSFORM
    def transform(_, bone, local, out):
        matrix = (C.c_float * 12)(*o['matrices'][12 * bone:12 * bone + 12])
        origin = (C.c_float * 3)(*o['position'])
        plib.mu_pt_transform_position(matrix, local, out, 1, o['scale'], origin)

    @EMIT
    def emit(_, fx):
        f = fx.contents
        light = [u(x) for x in f.light]
        if f.kind == 1:
            effects.append(('particle', f.bitmap, [u(x) for x in f.position], [u(x) for x in f.angle], light,
                            f.subtype, u(f.scale), 0, 0))
        else:
            effects.append(('sprite', f.bitmap, [u(x) for x in f.position], u(f.scale), light, v.OBJ, 0, 0, 4,
                            [1, 1, u(1.0)]))

    context = v.CContext(0, -1, v.RANDOM_FN(lambda _: draw()), None)
    host = Host(o['bones'] if o['attached'] else 0, -1, transform, rand, emit, None, o['bones'],
                (C.c_float * 3)(*o['angle']))

    class Adapter:
        def mu_rc_item_draws(self, *args):
            return lib.mu_rc_item_draws_owner(*args, C.byref(context), C.byref(host))
    status, stream = v.c_stream(Adapter(), case)
    return status, stream, effects, used[0]


def body_cases(wa, lib):
    """292 survey states per type without an owner host: client draws (effects set aside) against the C."""
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, quality.RandomWorld), []
    for t in TYPES:
        rng = random.Random(0x20050 + t)
        for k, case in quality.state_cases(t):
            sequence = quality.sequence_for(rng)

            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = sequence, 0
                return world
            result, expected, other, _ = v.client_stream(wa, case, factory)
            unexpected = [c for c in other if c[0] != 'effect']
            status, actual, used = quality.run_c(lib, case, sequence)
            if not result['ok'] or unexpected or status or actual != expected or used:
                raise AssertionError(('body', hex(t), k, case, expected, (result, unexpected[:3], status, actual, used)))
            vectors.append(('body', case, sequence, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


def owner_cases(wa, lib, plib, per_type, refuse=False):
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, OwnerWorld), []
    coverage = {'sprites': 0, 'particles': 0, 'rand': 0}
    for t in TYPES:
        rng = random.Random((0x20051 if not refuse else 0x20052) + t)
        cases = [case for _, case in quality.state_cases(t)]
        for k in range(per_type):
            case = dict(cases[(k * 37) % len(cases)])
            o = owner_setup(rng, t, k, refuse)
            expected = original(wa, reset, case, o)
            actual = run_c(lib, plib, case, o)
            if refuse:
                ok = actual[0] == 0 and actual[1] == expected[0] and actual[2] == [] and actual[3] == 0
            else:
                ok = actual[0] == 0 and actual[1:] == expected
            if not ok:
                raise AssertionError(('refusal' if refuse else 'owner', hex(t), k, o['bones'], expected, actual))
            if not refuse:
                coverage['sprites'] += sum(e[0] == 'sprite' for e in expected[1])
                coverage['particles'] += sum(e[0] == 'particle' for e in expected[1])
                coverage['rand'] += expected[2]
            vectors.append(('refusal' if refuse else 'owner', case, o, expected))
    result = {'cases': len(vectors), 'mismatches': 0}
    if not refuse:
        result['coverage'] = coverage
    return result, vectors


MUTANTS = {
    'gate-modulus': ('owner_random(h) % (int32_t)o->a != 0', 'owner_random(h) % ((int32_t)o->a + 1) != 0'),
    'gate-target': ('o->a != 0)\n                pc = (int)o->k;', 'o->a != 0)\n                pc = (int)o->k + 1;'),
    'range-low': ('fx_trunc(s * lo), b', 'fx_trunc(s * lo) + 1, b'),
    # The two clamps cannot change a result for the programs' constant bounds (truncation keeps a/steps >= lo
    # and b/steps <= hi), so they have no mutant here; the span is the reachable part.
    'range-span': ('(uint32_t)b - (uint32_t)a + 1u', '(uint32_t)b - (uint32_t)a + 2u'),
    'normalize-zero': ('out[0] = out[1] = out[2] = 0.0f;', 'out[0] = out[1] = out[2] = 1.0f;'),
    'normalize-scale': ('out[k] = in[k] * inverse;', 'out[k] = in[k] / length;'),
    'transform-bone': ('h->transform(h->context, (int32_t)o->k,', 'h->transform(h->context, (int32_t)o->k + 1,'),
    'add': ('r[o->a] = r[o->b] + r[o->c];', 'r[o->a] = r[o->b] - r[o->c];'),
    'subtract': ('r[o->a] = r[o->b] - r[o->c];\n            bad[o->a] = bad[o->b] | bad[o->c];\n            break;\n        case 6',
                 'r[o->a] = r[o->c] - r[o->b];\n            bad[o->a] = bad[o->b] | bad[o->c];\n            break;\n        case 6'),
    'angle': ('memcpy(&r[o->a], h->angle, sizeof h->angle);', 'memset(&r[o->a], 0, sizeof h->angle);'),
    'sprite-scale': ('fx.scale = r[o->b];', 'fx.scale = r[o->b + 1];'),
    'particle-subtype': ('fx.subtype = o->e;', 'fx.subtype = o->e + 1;'),
    'bone-domain': ('if (need > h->bones || need > h->item_bones)', 'if (need > h->bones + 1 || need > h->item_bones + 1)'),
    'phase': ('(phase == 0 || phase == 5 || phase == 6 || phase == 7)', '(phase == 0 || phase == 6 || phase == 7)'),
}


def mutations(vectors, plib):
    source = (ROOT/'reconstructed/renderchar/owner_fx.inc').read_text()
    body = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    caught = {}
    with tempfile.TemporaryDirectory(prefix='item-ownerfx-') as tmp:
        for name, (old, new) in MUTANTS.items():
            text = body if name == 'phase' else source
            if text.count(old) != 1:
                raise AssertionError(('mutant anchor', name, text.count(old)))
            folder = Path(tmp)/name
            folder.mkdir()
            (folder/'owner_fx.inc').write_text(source.replace(old, new) if text is source else source)
            (folder/'renderchar.c').write_text(body.replace(old, new) if text is body else body)
            library = folder/'lib.dylib'
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(folder/'renderchar.c'),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)],
                           check=True)
            lib = C.CDLL(str(library))
            lib.mu_rc_item_owner_fx.restype = C.c_int
            detected = 0
            for family, case, extra, expected in vectors:
                if family == 'body':
                    status, actual, used = quality.run_c(lib, case, extra)
                    detected += bool(status) or actual != expected or bool(used)
                    continue
                status, stream, effects, used = run_c(lib, plib, case, extra)
                if family == 'refusal':
                    detected += bool(status) or stream != expected[0] or bool(effects) or bool(used)
                else:
                    detected += bool(status) or (stream, effects, used) != expected
            if not detected:
                raise AssertionError(('surviving mutant', name))
            caught[name] = detected
    return caught


LIB = None


def main():
    global LIB
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--owner-cases', type=int, default=48, help='owner states per type')
    parser.add_argument('--refusal-cases', type=int, default=8, help='refusal states per type')
    parser.add_argument('--skip-bodies', action='store_true', help='iteration only: no body family or table check')
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    LIB = lib = C.CDLL(str(v.LIBRARY))
    lib.mu_rc_item_owner_fx.restype = C.c_int
    plib = particles_library()
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}}
    vectors = []
    if not args.skip_bodies:
        report['families']['bodies'], bodies = body_cases(wa, lib)
        vectors += bodies
    report['families']['owner'], owner = owner_cases(wa, lib, plib, args.owner_cases)
    report['families']['refusal'], refusal = owner_cases(wa, lib, plib, args.refusal_cases, refuse=True)
    vectors += owner + refusal
    if args.mutations:
        report['mutants'] = mutations(vectors, plib)
    if fxgen.generate() != (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text():
        raise AssertionError(('table drift', 'item_owner_fx.h'))
    if not args.skip_bodies and gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError(('table drift', 'item_bodies.h'))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
