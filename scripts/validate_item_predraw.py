#!/usr/bin/env python3
"""Part 18 bodies (RENDER-ITEMS-002R): pre-draw effect programs versus the pinned instructions.

RenderObjDraw 0x0176ce74 creates these bodies' effects in its own type case, before the body draws: bone sprites
0x0150e746 and TransformPosition 0x012b6ef1 positions on the item's own posed bones (BoneTransform 0x06fce398, by
name through 0x012bd35a or by constant index), lights from the clock, the wave 0x0185bdc4, the CRT sine, the
alpha argument and rand(), behind the TestFrustrum2D flag [ebp-0xd].

bodies: the 292 survey states of every type, client RenderObjDraw against mu_rc_item_draws_context (no host). The
  client's effect requests are set aside; the library creates none and draws no rand.
predraw: the complete RenderObjDraw with an item skeleton: the model's bone count (+0x22) and bone records (+0x2c,
  0x8c bytes, the name at +0) hold the program's names at random indices among decoys and duplicates (some
  missing), BoneTransform holds authored matrices, the model scale (+0x74) and origin (+0x78) are random, the
  OBJECT angle (+0x164) too; some states place the 2D frustum away from the OBJECT (the flag clears). rand()
  returns a scripted sequence. The real 0x0150e746, 0x012bd35a, 0x012b6ef1, wave, sine and vec3 helpers run;
  CreateSprite 0x01692eb7 and CreateParticle 0x0168fafd are recording stubs. The C runs mu_rc_item_draws_owner
  with an item host (TransformPosition with the authored matrix, scale and origin; the named-bone search over the
  same names; the flag the client computed). The draw stream, every request (all arguments bit for bit) and the
  rand() count must agree. A request on a bone outside 0..count-1 (the client reads another matrix) must reach
  the host's refuse callback with the client's kind and bitmap, in order.
The body table (gen_item_bodies) and the effect table (gen_item_owner_fx) must reproduce from the pins.
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
import validate_item_ownerfx as ownerfx
import validate_item_quality as quality
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = fxgen.PRE_FX_TYPES
BONE_TRANSFORM = 0x06fce398
RECORDS = 0x2f000000         # synthetic bone records (0x8c bytes each, the name at +0)
FRUSTUM = (0x0b6b5400, 0x0b6b5410)   # TestFrustrum2D corner x[4] and y[4]
SCENE = 0x01d1df70
FLAG_SITE = 0x0176cef5       # after `mov byte ptr [ebp-0xd], al`

Fx = ownerfx.Fx
RANDOM, TRANSFORM, EMIT = ownerfx.RANDOM, ownerfx.TRANSFORM, ownerfx.EMIT
NAMED = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p)
ITEM_TRANSFORM = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.c_int32, C.POINTER(C.c_float))
Host = ownerfx.Host
DECOYS = ['Bip01', 'Bone01', 'Box01', 'aw00', 'Point', 'zx00', 'sw0', 'center', 'g001']


def u(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def program_names():
    """Names each type's program looks up (from the generator's reading)."""
    programs, refused = fxgen.extract_pre_all()
    if refused:
        raise AssertionError(('pre-draw reading', refused))
    return {t: p['names'] for t, p in programs.items()}, {t: p['bones'] for t, p in programs.items()}


def item_setup(rng, t, k, names, consts):
    """Item skeleton, names, model scale/origin, OBJECT angle, frustum and rand sequence of one state."""
    wanted = list(names)
    need = max(consts, default=-1) + 1
    count = (max(need, 8), need + rng.randrange(0, 4), 40, 64, rng.randrange(1, 80), max(need - 2, 1))[k % 6]
    if k % 6 == 5 and consts:
        count = max(min(consts) - 1, 1) if rng.random() < 0.5 else max(need - 1, 1)  # constant bones refused
    count = max(count, 1)
    table = [rng.choice(DECOYS) + str(rng.randrange(10)) for _ in range(count)]
    for name in wanted:
        r = rng.random()
        if r < 0.82:
            table[rng.randrange(count)] = name       # present (a later write may overwrite an earlier name)
        elif r < 0.9 and count > 1:
            i = rng.randrange(count)
            table[i] = name                           # and a duplicate after it: the first one wins
            table[rng.randrange(i, count)] = name
        # else missing: index -1, the request is refused
    if k % 13 == 7:
        table = [rng.choice(DECOYS) for _ in range(count)]   # every name missing
    matrices = [rng.uniform(-1.5, 1.5) if c % 4 != 3 else rng.uniform(-200, 200)
                for _ in range(count) for c in range(12)]
    if k % 11 == 5:
        matrices = [round(x) for x in matrices]
    hidden = k % 9 == 4                       # the frustum lies away from the OBJECT: [ebp-0xd] = 0
    return dict(count=count, names=table, matrices=matrices, records=k % 17 != 3,
                scale=rng.choice((1.0, 0.75, 1.3, rng.uniform(0.5, 2))),
                origin=[rng.uniform(-3000, 3000) for _ in range(3)],
                angle=[rng.choice((0.0, 90.0, rng.uniform(-360, 360))) for _ in range(3)],
                hidden=hidden, stream=quality.sequence_for(rng) + [rng.randrange(32768) for _ in range(64)])


def names_bytes(names):
    out = b''
    for n in names:
        raw = n.encode() + b'\0'
        out += raw + bytes((0x13 * (len(out) + 7)) & 0xff for _ in range(0x8c - len(raw)))
    return out


class ItemWorld(ownerfx.OwnerWorld):
    """OwnerWorld with the item skeleton: bone records, BoneTransform matrices, scale/origin and the frustum."""
    def __init__(self, *args):
        super().__init__(*args)
        self.m.map(RECORDS, 0x10000)
        self.item, self.flag = None, None

    def install(self):
        super().install()
        from unicorn import UC_HOOK_CODE
        m = self.m
        # The real bone sprite 0x0150e746 runs (TransformPosition, then the CreateSprite stub).
        m.uc.hook_del(m.hooks.pop(fxgen.BONE_SPRITE))
        del m.stubs[fxgen.BONE_SPRITE]

        def flag(uc, address, size, context):
            ebp = uc.reg_read(m.x86.UC_X86_REG_EBP)
            self.flag = m.read(ebp - 0xd, 1)[0]
        m.uc.hook_add(UC_HOOK_CODE, flag, begin=FLAG_SITE, end=FLAG_SITE)

    def add_model(self, model_type, address, *args, **kwargs):
        super().add_model(model_type, address, *args, **kwargs)
        o, m = self.item, self.m
        if o is None or address != v.MODEL:
            return
        m.write(v.MODEL + 0x22, struct.pack('<h', o['count']))
        m.w32(v.MODEL + 0x2c, RECORDS if o['records'] else 0)
        m.write(RECORDS, names_bytes(o['names']) or b'\0')
        m.wf(v.MODEL + 0x74, o['scale'])
        m.write(v.MODEL + 0x78, struct.pack('<3f', *o['origin']))
        m.ensure(BONE_TRANSFORM - 0x30, 0x30 * 260)
        # Bones past the count and the word before BoneTransform hold junk the C must never read.
        m.write(BONE_TRANSFORM - 0x30, struct.pack('<12f', *([7.0] * 12)))
        m.write(BONE_TRANSFORM, struct.pack('<%df' % len(o['matrices']), *o['matrices']))
        m.write(BONE_TRANSFORM + 0x30 * o['count'], struct.pack('<12f', *([-3.0] * 12)) * 8)
        m.write(v.OBJ + 0x164, struct.pack('<3f', *o['angle']))
        m.ensure(SCENE, 4)
        m.w32(SCENE, 0)
        m.ensure(FRUSTUM[0], 0x20)
        corners = (1000.0, 1010.0, 1010.0, 1000.0), (1000.0, 1000.0, 1010.0, 1010.0)
        for base, values in zip(FRUSTUM, corners if o['hidden'] else ((0.0,) * 4, (0.0,) * 4)):
            m.write(base, struct.pack('<4f', *values))


def original(wa, reset, case, o):
    """Client stream, effect requests, rand() count and the TestFrustrum2D flag of one state."""
    effects = []

    def factory(*args):
        world = reset(*args)
        world.sequence, world.drawn = o['stream'], 0
        world.item, world.effects, world.owner, world.flag = o, effects, None, None
        return world
    result, stream, other, m = v.client_stream(wa, case, factory)
    unexpected = [c for c in other if c[0] != 'effect']
    if not result['ok'] or unexpected:
        raise AssertionError(('predraw original', hex(case['type']), result, unexpected[:3]))
    return stream, list(effects), reset.world.drawn, reset.world.flag


def run_c(lib, plib, case, o, flag):
    """C stream, effect requests (refused ones as ('refused', kind, bitmap)) and rand() count of one state."""
    used, effects = [0], []
    stream_values = o['stream']

    def draw():
        used[0] += 1
        return stream_values[used[0] - 1] if used[0] <= len(stream_values) else 0

    @RANDOM
    def rand(_):
        return draw()

    @NAMED
    def named(_, name):
        if not o['records']:
            return -1
        text = name.decode()
        return next((i for i, x in enumerate(o['names']) if x == text), -1)

    @ITEM_TRANSFORM
    def item_transform(_, bone, local, translate, out):
        matrix = (C.c_float * 12)(*o['matrices'][12 * bone:12 * bone + 12])
        origin = (C.c_float * 3)(*o['origin'])
        plib.mu_pt_transform_position(matrix, local, out, translate, o['scale'], origin)

    def record(fx):
        f = fx.contents
        light = [u(x) for x in f.light]
        if f.kind == 1:
            return ('particle', f.bitmap, [u(x) for x in f.position], [u(x) for x in f.angle], light,
                    f.subtype, u(f.scale), v.OBJ if f.owner else 0, 0)
        return ('sprite', f.bitmap, [u(x) for x in f.position], u(f.scale), light, v.OBJ, u(f.rotation), f.blend,
                4, [1, 1, u(1.0)])

    @EMIT
    def emit(_, fx):
        effects.append(record(fx))

    @EMIT
    def refuse(_, fx):
        f = fx.contents
        effects.append(('refused', 'particle' if f.kind == 1 else 'sprite', f.bitmap))

    context = v.CContext(0, -1, v.RANDOM_FN(lambda _: draw()), None)
    host = Host(0, -1, TRANSFORM(), rand, emit, None, o['count'], (C.c_float * 3)(*o['angle']),
                named, item_transform, refuse, flag)

    class Adapter:
        def mu_rc_item_draws(self, *args):
            return lib.mu_rc_item_draws_owner(*args, C.byref(context), C.byref(host))
    status, stream = v.c_stream(Adapter(), case)
    return status, stream, effects, used[0]


def same(expected, actual):
    """Client requests against the C's: equal, except that a refused C request matches the client's kind/bitmap."""
    stream, client, drawn, _ = expected
    status, cstream, mine, used = actual
    if status or cstream != stream or used != drawn or len(client) != len(mine):
        return False, 0
    refused = 0
    for a, b in zip(client, mine):
        if b[0] == 'refused':
            refused += 1
            if (a[0], a[1]) != b[1:]:
                return False, refused
        elif a != b:
            return False, refused
    return True, refused


def predraw_cases(wa, lib, plib, per_type, names, consts):
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, ItemWorld), []
    coverage = {'sprites': 0, 'particles': 0, 'refused': 0, 'rand': 0, 'hidden': 0}
    for t in TYPES:
        rng = random.Random(0x20060 + t)
        cases = [case for _, case in quality.state_cases(t)]
        for k in range(per_type):
            case = dict(cases[(k * 37) % len(cases)])
            o = item_setup(rng, t, k, names[t], consts[t])
            expected = original(wa, reset, case, o)
            actual = run_c(lib, plib, case, o, expected[3])
            ok, refused = same(expected, actual)
            if not ok:
                raise AssertionError(('predraw', hex(t), k, o['count'], 'status', actual[0],
                                      'stream', expected[0] == actual[1], len(expected[0]), len(actual[1]),
                                      'effects', len(expected[1]), len(actual[2]), expected[1] == actual[2],
                                      'rand', expected[2], actual[3], 'flag', expected[3]))
            coverage['sprites'] += sum(e[0] == 'sprite' for e in expected[1]) - sum(
                e[0] == 'refused' and e[1] == 'sprite' for e in actual[2])
            coverage['particles'] += sum(e[0] == 'particle' for e in expected[1])
            coverage['refused'] += refused
            coverage['rand'] += expected[2]
            coverage['hidden'] += not expected[3]
            vectors.append(('predraw', case, o, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'coverage': coverage}, vectors


def body_cases(wa, lib):
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, quality.RandomWorld), []
    for t in TYPES:
        rng = random.Random(0x20061 + t)
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


MUTANTS = {
    'wave': ('r[o->a] = client_wave(fx_float(o->k), it->time);', 'r[o->a] = client_wave(fx_float(o->k), -it->time);'),
    'named': ('h->bone_named(h->context, mu_rc_fx_names[o->k])', 'h->bone_named(h->context, mu_rc_fx_names[0])'),
    'visible': ('if (!h->visible)', 'if (h->visible)'),
    'alpha': ('r[o->a] = it->alpha;', 'r[o->a] = it->object_alpha * 0.5f;'),
    'sine': ('r[o->a] = client_sin(r[o->b]);', 'r[o->a] = (float)cos((double)r[o->b]);'),
    'abs': ('if (0.0f > r[o->b])', 'if (0.0f < r[o->b])'),
    'randmod': ('(float)(owner_random(h) % (int32_t)o->k)', '(float)(owner_random(h) % ((int32_t)o->k + 1))'),
    'transform-domain': ('bone < 0 || bone >= h->item_bones || !h->item_transform) {',
                         'bone < 0 || bone > h->item_bones || !h->item_transform) {'),
    # Every item transform of the 26 programs translates (k = 1), so the translate word has no mutant here.
    'transform-bone': ('h->item_transform(h->context, bone, &r[o->c]', 'h->item_transform(h->context, bone ^ 1, &r[o->c]'),
    'sprite-domain': ('refused = bad[o->a] || bone < 0 ||', 'refused = bad[o->a] || bone < -1 ||'),
    # The 90 bone sprites pass rotation 0 and blend 0 (copied, not mutated); 0x0150e746 translates.
    'sprite-translate': ('h->item_transform(h->context, bone, zero, 1, fx.position);',
                         'h->item_transform(h->context, bone, zero, 0, fx.position);'),
    # No program computes arithmetic on a transformed position; a request reads it directly or through movs.
    'position-refusal': ('refused = bad[o->a] | bad[o->a + 1] | bad[o->a + 2];', 'refused = 0;'),
    'particle-owner': ('fx.owner = o->op == 25;', 'fx.owner = 0;'),
    'pre-hook': ('if (host && host->item_transform && it->select == 0', 'if (host && host->item_transform && it->select == 1'),
}


def mutations(vectors, plib):
    sources = {name: (ROOT/'reconstructed/renderchar'/name).read_text()
               for name in ('owner_fx.inc', 'rank5_owner.inc', 'renderchar.c')}
    caught = {}
    with tempfile.TemporaryDirectory(prefix='item-predraw-') as tmp:
        for name, (old, new) in MUTANTS.items():
            hits = [f for f, text in sources.items() if text.count(old)]
            if len(hits) != 1 or sources[hits[0]].count(old) != 1:
                raise AssertionError(('mutant anchor', name, {f: t.count(old) for f, t in sources.items()}))
            folder = Path(tmp)/name
            folder.mkdir()
            for f, text in sources.items():
                (folder/f).write_text(text.replace(old, new) if f == hits[0] else text)
            library = folder/'lib.dylib'
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(folder/'renderchar.c'),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)],
                           check=True)
            lib = C.CDLL(str(library))
            detected = 0
            for family, case, extra, expected in vectors:
                if family == 'body':
                    status, actual, used = quality.run_c(lib, case, extra)
                    detected += bool(status) or actual != expected or bool(used)
                    continue
                detected += not same(expected, run_c(lib, plib, case, extra, expected[3]))[0]
            if not detected:
                raise AssertionError(('surviving mutant', name))
            caught[name] = detected
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--predraw-cases', type=int, default=64, help='item states per type')
    parser.add_argument('--skip-bodies', action='store_true', help='iteration only: no body family or table check')
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    lib = C.CDLL(str(v.LIBRARY))
    lib.mu_rc_item_pre_fx.restype = C.c_int
    plib = ownerfx.particles_library()
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}}
    vectors = []
    if not args.skip_bodies:
        report['families']['bodies'], bodies = body_cases(wa, lib)
        vectors += bodies
    names, consts = program_names()
    if any(not lib.mu_rc_item_pre_fx(t) for t in TYPES) or lib.mu_rc_item_pre_fx(0x0ae6):
        raise AssertionError('mu_rc_item_pre_fx disagrees with PRE_FX_TYPES')
    report['families']['predraw'], predraw = predraw_cases(wa, lib, plib, args.predraw_cases, names, consts)
    vectors += predraw
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
