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
RENDER-ITEMS-002S (part 19) adds fourteen programs to both families: integer clock chains with a float branch,
CreateJoint 0x0153b02c loops (a recording stub with all fourteen arguments; the C's joint requests carry the same
words), a rotated CreateSprite behind rand() % 15, bones at rand() % bone count, names built with _itoa and the
OBJECT position (+0x158, random in every state).
RENDER-ITEMS-002T (part 21) adds three maces: the rendered-frame counter [0x0bdc5ebc] (random in every state; the C
host gets the same word), 0x012b678d on item bones with a NULL local point (some states give the OBJECT its own bone
array +0x318, which the client then reads instead of BoneTransform; the C host's object_transform does the same),
the random spherical vector 0x00d01fc6, rand() % 3 array selects, and CreateParticle with a computed bitmap and
argument 8 (compared word for word). The two post programs (gen_item_owner_fx.POST_FX_TYPES: owner blocks after the
draws in RenderPartObjectBody) join both families: bow 0x130d's TransformPosition on the OBJECT's own bone 4 (every
state of it gives the OBJECT a bone array with more than four bones: without one the client dereferences a NULL
matrix) and a register bitmap, 0x2713's item bones and OBJECT light. hidden: the wings 0x2382..0x2385 with OBJECT +0x68
= 1, 2, 3, 7 over the 292 states (the library used to refuse them; their streams equal the client's).
RENDER-ITEMS-002U (part 23): frame: the bodies whose draws read the rendered-frame counter (gen_item_bodies.FRAME_TYPES,
51 earlier bodies plus 0x0f2a), each survey state with a counter value (the boundaries 0..0xffffffff, then random),
client RenderObjDraw against the library with mu_rc_item.frame. The predraw family's C bodies read its counter too.
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
# Later read programs have their own record/clock and owned-stream row.
TYPES = [t for t in fxgen.PRE_FX_TYPES if t not in fxgen.LATER_READ_PROGRAM_TYPES] + fxgen.POST_FX_TYPES
HIDDEN_TYPES = [0x2382, 0x2383, 0x2384, 0x2385]
HIDDEN_VALUES = (1, 2, 3, 7)
OWNER_NEED = {}     # post programs: 1 + the highest OBJECT bone (0x0129f12c), filled by program_names
BONE_TRANSFORM = 0x06fce398
RECORDS = 0x2f000000         # synthetic bone records (0x8c bytes each, the name at +0)
FRUSTUM = (0x0b6b5400, 0x0b6b5410)   # TestFrustrum2D corner x[4] and y[4]
SCENE = 0x01d1df70
FLAG_SITE = 0x0176cef5       # after `mov byte ptr [ebp-0xd], al`
FRAME_COUNTER = fxgen.FRAME_COUNTER

Fx = ownerfx.Fx
RANDOM, TRANSFORM, EMIT = ownerfx.RANDOM, ownerfx.TRANSFORM, ownerfx.EMIT
NAMED = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p)
ITEM_TRANSFORM = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.c_int32, C.POINTER(C.c_float))
OBJECT_TRANSFORM = ownerfx.OBJECT_TRANSFORM
Host = ownerfx.Host
DECOYS = ['Bip01', 'Bone01', 'Box01', 'aw00', 'Point', 'zx00', 'sw0', 'center', 'g001']


def u(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def program_names():
    """Names each type's program looks up (from the generator's reading)."""
    programs, refused = fxgen.extract_pre_all()
    if refused:
        raise AssertionError(('pre-draw reading', refused))
    names, consts = {t: p['names'] for t, p in programs.items()}, {t: p['bones'] for t, p in programs.items()}
    post, refused = fxgen.extract(fxgen.POST_FX_TYPES)
    if refused:
        raise AssertionError(('post reading', refused))
    for t, p in post.items():
        names[t], consts[t] = [], p['item_bones']
        OWNER_NEED[t] = max(p['bones'], default=-1) + 1
    return names, consts


def item_setup(rng, t, k, names, consts, owner_need=0):
    """Item skeleton, names, model scale/origin, OBJECT angle, frustum and rand sequence of one state."""
    wanted = list(names)
    need = max(consts, default=-1) + 1
    count = (max(need, 8), need + rng.randrange(0, 4), 40, 64, rng.randrange(1, 80), max(need - 2, 1))[k % 6]
    if k % 6 == 5 and consts:
        count = max(min(consts) - 1, 1) if rng.random() < 0.5 else max(need - 1, 1)  # constant bones refused
    count = max(count, 1, owner_need)     # owner_need: the OBJECT bones a post program reaches through 0x0129f12c
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
    # RENDER-ITEMS-002T: the rendered-frame counter, and in some states an OBJECT bone array (+0x318).
    frame = rng.choice((0, 1, 2, 3, 4, 5, 15, rng.randrange(1 << 32), 0xffffffff))
    attached = k % 5 == 2 or owner_need > 0
    owner = [f32(rng.uniform(-1.5, 1.5)) if c % 4 != 3 else f32(rng.uniform(-200, 200))
             for _ in range(count) for c in range(12)] if attached else []
    return dict(count=count, names=table, matrices=matrices, records=k % 17 != 3,
                scale=rng.choice((1.0, 0.75, 1.3, rng.uniform(0.5, 2))),
                origin=[rng.uniform(-3000, 3000) for _ in range(3)],
                position=[rng.uniform(-3000, 3000) for _ in range(3)],
                angle=[rng.choice((0.0, 90.0, rng.uniform(-360, 360))) for _ in range(3)],
                hidden=hidden, frame=frame, attached=attached, owner_matrices=owner, stream=quality.sequence_for(rng) + [rng.randrange(32768) for _ in range(64)])


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

        def joint(mm):
            a = [mm.arg(i) for i in range(14)]
            self.effects.append(('joint', a[0]) + tuple(list(struct.unpack('<3I', mm.read(a[i], 12))) for i in (1, 2, 3)) +
                                tuple(a[4:]))
            return 0
        m.stub(fxgen.JOINT, joint, 0)   # RENDER-ITEMS-002S: CreateJoint 0x0153b02c, recorded

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
        # Without an explicit pre-bone record, the C must refuse that slot. Bones past the count stay unavailable.
        m.write(BONE_TRANSFORM - 0x30, struct.pack('<12f', *o.get('before_matrix', [7.0] * 12)))
        m.write(BONE_TRANSFORM, struct.pack('<%df' % len(o['matrices']), *o['matrices']))
        m.write(BONE_TRANSFORM + 0x30 * o['count'], struct.pack('<12f', *([-3.0] * 12)) * 8)
        m.write(v.OBJ + 0x1f4, bytes(4 * o.get('point_words', 9)))
        m.write(v.OBJ + 0x164, struct.pack('<3f', *o['angle']))
        m.write(v.OBJ + 0x158, struct.pack('<3f', *o['position']))
        m.ensure(FRAME_COUNTER, 4)
        m.w32(FRAME_COUNTER, o['frame'])
        m.w32(v.OBJ + 0x318, ownerfx.OWNER_BONES if o['attached'] else 0)
        if o['attached']:
            m.write(ownerfx.OWNER_BONES, struct.pack('<%df' % len(o['owner_matrices']), *o['owner_matrices']))
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
    o["client_points"] = reset.world.m.read(v.OBJ + 0x1f4, 4 * o.get('point_words', 9))
    return stream, list(effects), reset.world.drawn, reset.world.flag


def run_c(lib, plib, case, o, flag):
    """C stream, effect requests (refused ones as ('refused', kind, bitmap)) and rand() count of one state."""
    used, effects = [0], []
    o["native_points"] = bytearray(4 * o.get('point_words', 9))
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

    def valid_bone(kind, matrices, bone, out):
        if 0 <= bone < len(matrices) // 12:
            return True
        # Planted invalid calls must fail deterministically, not escape a ctypes callback.
        effects.append(('invalid-transform', kind, bone))
        for k in range(3):
            out[k] = 0.0
        return False

    @ITEM_TRANSFORM
    def item_transform(_, bone, local, translate, out):
        if not valid_bone('item', o['matrices'], bone, out):
            return
        matrix = (C.c_float * 12)(*o['matrices'][12 * bone:12 * bone + 12])
        origin = (C.c_float * 3)(*o['origin'])
        plib.mu_pt_transform_position(matrix, local, out, translate, o['scale'], origin)

    @ITEM_TRANSFORM
    def owner_item_transform(_, bone, local, translate, out):
        if not valid_bone('owner-item', o['owner_matrices'], bone, out):
            return
        matrix = (C.c_float * 12)(*o['owner_matrices'][12 * bone:12 * bone + 12])
        origin = (C.c_float * 3)(*o['origin'])
        plib.mu_pt_transform_position(matrix, local, out, translate, o['scale'], origin)

    @OBJECT_TRANSFORM
    def object_transform(_, bone, out):
        # 0x012b678d(out, OBJECT, bone, NULL): the OBJECT's own bone array when it has one (its model is the item
        # model here, so the bone is in range), else BoneTransform; translation * scale + OBJECT position.
        source = o['owner_matrices'] if o['attached'] else o['matrices']
        if not valid_bone('object', source, bone, out):
            return
        for k in range(3):
            out[k] = f32(f32(f32(o['scale']) * f32(source[12 * bone + 4 * k + 3])) + f32(o['position'][k]))

    @ownerfx.BEFORE_TRANSFORM
    def before_transform(_, out):
        matrix = (C.c_float * 12)(*o['before_matrix'])
        plib.mu_pt_transform_position(matrix, (C.c_float * 3)(0, 0, 0), out, 1, o['scale'],
                                      (C.c_float * 3)(*o['origin']))

    def record(fx):
        f = fx.contents
        light = [u(x) for x in f.light]
        if f.kind == 1:
            return ('particle', f.bitmap, [u(x) for x in f.position], [u(x) for x in f.angle], light,
                    f.subtype, u(f.scale), v.OBJ if f.owner else 0, f.extra & 0xffffffff)
        if f.kind == 3:
            return ('joint', f.bitmap, [u(x) for x in f.position], [u(x) for x in f.target], [u(x) for x in f.angle],
                    f.subtype, v.OBJ, u(f.scale), 0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0)
        return ('sprite', f.bitmap, [u(x) for x in f.position], u(f.scale), light, v.OBJ, u(f.rotation), f.blend,
                4, [1, 1, u(1.0)])

    @EMIT
    def emit(_, fx):
        if fx.contents.kind == 4:
            # Legacy families observe nine words; EFFECTS-026 explicitly opts into all twelve.
            if 4 * fx.contents.subtype >= len(o['native_points']):
                return
            struct.pack_into('<f', o['native_points'], 4 * fx.contents.subtype, fx.contents.position[0])
            return
        effects.append(record(fx))

    @EMIT
    def refuse(_, fx):
        f = fx.contents
        effects.append(('refused', {1: 'particle', 2: 'sprite', 3: 'joint'}[f.kind], f.bitmap))

    context = v.CContext(0, -1, v.RANDOM_FN(lambda _: draw()), None)
    # bones: the OBJECT model's bone count (its model is the item model here) when the OBJECT has a bone array.
    host = Host(o['count'] if o['attached'] else 0, -1, TRANSFORM(), rand, emit, None, o['count'], (C.c_float * 3)(*o['angle']),
                named, item_transform, refuse, flag, (C.c_float * 3)(*o['position']),
                object_transform, o['frame'], 1, owner_item_transform)
    if 'before_matrix' in o:
        host.item_before_transform = before_transform

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
    coverage = {'sprites': 0, 'particles': 0, 'joints': 0, 'refused': 0, 'rand': 0, 'hidden': 0}
    for t in TYPES:
        rng = random.Random(0x20060 + t)
        cases = [case for _, case in quality.state_cases(t)]
        for k in range(per_type):
            case = dict(cases[(k * 37) % len(cases)])
            o = item_setup(rng, t, k, names[t], consts[t], OWNER_NEED.get(t, 0))
            case['frame'] = o['frame']   # RENDER-ITEMS-002U: the C body reads the same counter (0x0f2a's atlas)
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
            coverage['joints'] += sum(e[0] == 'joint' for e in expected[1]) - sum(
                e[0] == 'refused' and e[1] == 'joint' for e in actual[2])
            coverage['refused'] += refused
            coverage['rand'] += expected[2]
            coverage['hidden'] += not expected[3]
            vectors.append(('predraw', case, o, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'coverage': coverage}, vectors


def body_cases(wa, lib):
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, quality.RandomWorld), []
    for t in TYPES + [0x1588]:
        rng = random.Random(0x20061 + t)
        for k, case in quality.state_cases(t):
            # Without an item host the native pre-program is absent. Zero rand results keep the body
            # independent of how many pre-program calls the original consumed. The owned family below
            # checks the full shared rand stream, including its exact consumption order.
            sequence = [0] * 64 if t in gen.COUNTER_RANGE_TYPES and t in fxgen.PRE_FX_TYPES else quality.sequence_for(rng)

            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = sequence, 0
                return world
            result, expected, other, _ = v.client_stream(wa, case, factory)
            unexpected = [c for c in other if c[0] != 'effect']
            status, actual, used = quality.run_c(lib, case, sequence)
            if not result['ok'] or unexpected or status or actual != expected or \
                    (used != reset.world.drawn if t == 0x1588 else
                     bool(used) if t not in gen.COUNTER_RANGE_TYPES else False):
                raise AssertionError(('body', hex(t), k, case, expected, (result, unexpected[:3], status, actual, used)))
            vectors.append(('body', case, sequence, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


FRAME_VALUES = (0, 1, 2, 3, 15, 31, 32, 59, 60, 61, 119, 0x7ffffffe, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)


def frame_cases(wa, lib, states):
    """RENDER-ITEMS-002U: the bodies whose draws read the rendered-frame counter [0x0bdc5ebc]
    (gen_item_bodies.FRAME_TYPES), each state with a counter value (boundaries and random), client vs C."""
    from item_body_machine import ResetWorld
    reset, vectors, values = ResetWorld(wa, quality.RandomWorld), [], set()
    for t in gen.FRAME_TYPES:
        rng = random.Random(0x20063 + t)
        for k, case in quality.state_cases(t):
            if k >= states:
                break
            frame = FRAME_VALUES[k] if k < len(FRAME_VALUES) else rng.choice(
                (rng.randrange(1 << 32), rng.randrange(1000), rng.randrange(0x7fffff00, 0x80000100) & 0xffffffff))
            case = dict(case, frame=frame)
            sequence = [0] * 64 if t in gen.COUNTER_RANGE_TYPES and t in fxgen.PRE_FX_TYPES else quality.sequence_for(rng)

            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = sequence, 0
                return world
            result, expected, other, _ = v.client_stream(wa, case, factory)
            unexpected = [c for c in other if c[0] != 'effect']
            status, actual, used = quality.run_c(lib, case, sequence)
            if not result['ok'] or unexpected or status or actual != expected or \
                    (used != reset.world.drawn if t not in fxgen.PRE_FX_TYPES else
                     bool(used) if t not in gen.COUNTER_RANGE_TYPES else False):
                raise AssertionError(('frame', hex(t), k, frame, status, len(expected), len(actual),
                                      next((i for i, (a, b) in enumerate(zip(expected, actual)) if a != b), None)))
            values.add(frame)
            vectors.append(('body', case, sequence, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'types': len(gen.FRAME_TYPES), 'counter_values': len(values)}, vectors


def hidden_cases(wa, lib):
    """RENDER-ITEMS-002T: OBJECT +0x68 outside -1/0 for the wings 0x2382..0x2385 (292 states each value)."""
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, quality.RandomWorld), []
    for t in HIDDEN_TYPES:
        rng = random.Random(0x20062 + t)
        for k, case in quality.state_cases(t):
            case = dict(case, object_hidden=HIDDEN_VALUES[k % len(HIDDEN_VALUES)])
            sequence = quality.sequence_for(rng)

            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = sequence, 0
                return world
            result, expected, other, _ = v.client_stream(wa, case, factory)
            unexpected = [c for c in other if c[0] != 'effect']
            status, actual, used = quality.run_c(lib, case, sequence)
            if not result['ok'] or unexpected or status or actual != expected or used:
                raise AssertionError(('hidden', hex(t), k, case['object_hidden'], status, len(expected), len(actual)))
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
    'position-refusal': ('refused |= bad[o->a] | bad[o->a + 1] | bad[o->a + 2];', 'refused |= 0;'),
    'particle-owner': ('fx.owner = o->op == 25 || o->op == 47;', 'fx.owner = 0;'),
    'pre-hook': ('if (host && host->item_transform && it->select == 0', 'if (host && host->item_transform && it->select == 1'),
    # RENDER-ITEMS-002S (part 19)
    'irand': ('fx_set_int(&r[o->a], owner_random(h));', 'fx_set_int(&r[o->a], owner_random(h) + 1);'),
    'imod': ('o->op == 28 ? x % y : x / y', 'o->op == 28 ? x / y : x % y'),
    'ftoi': ('fx_set_int(&r[o->a], fx_trunc(r[o->b]));', 'fx_set_int(&r[o->a], (int32_t)lrintf(r[o->b]));'),
    'itof': ('r[o->a] = (float)fx_int(&r[o->b]);', 'r[o->a] = (float)(fx_int(&r[o->b]) + 1);'),
    'cond-int': ('sf_of_lt = a < b;', 'sf_of_lt = a <= b;'),
    # No float branch is mutated: the only one (0x0b53's jb) computes a value no request reads (the body draws do).
    # Nor the join jump (op 35): its one use is in that branch; no admitted program joins a value across a branch.
    'bones': ('fx_set_int(&r[o->a], h->item_bones);', 'fx_set_int(&r[o->a], h->item_bones - 1);'),
    'position': ('memcpy(&r[o->a], h->position, sizeof h->position);', 'memcpy(&r[o->a], h->angle, sizeof h->angle);'),
    'joint-target': ('memcpy(fx.target, &r[o->b], sizeof fx.target);', 'memcpy(fx.target, &r[o->a], sizeof fx.target);'),
    'joint-subtype': ('fx.subtype = (int32_t)o->e;', 'fx.subtype = 0;'),
    'joint-scale': ('fx.scale = r[o->d];\n            const int refused', 'fx.scale = r[o->c];\n            const int refused'),
    'sprite-rotation': ('rotation r[d], blend e, 4, axes) */\n                fx.rotation = r[o->d];',
                        'rotation r[d], blend e, 4, axes) */\n                fx.rotation = 0.0f;'),
    # RENDER-ITEMS-002T (part 21)
    'frame': ('fx_set_int(&r[o->a], (int32_t)h->frame);', 'fx_set_int(&r[o->a], (int32_t)(h->frame + 1u));'),
    'object-domain': ('if (bad[o->b] || bone < 0 || bone >= h->item_bones || !h->object_transform) {',
                      'if (bad[o->b] || bone < -1 || bone >= h->item_bones || !h->object_transform) {'),
    'object-bone': ('h->object_transform(h->context, bone, &r[o->a]);', 'h->object_transform(h->context, bone ^ 1, &r[o->a]);'),
    'vector-radius': ('rmin >= rmax ? rmin : fx_range(h, rmin, rmax, 50);', 'rmin >= rmax ? rmin : fx_range(h, rmin, rmax, 49);'),
    'vector-floor': ('if (floor_radius > r) {', 'if (floor_radius < r) {'),
    'vector-cos': ('out[0] = x * (float)cos((double)phi);', 'out[0] = x * client_sin(phi);'),
    'vector-theta': ('out[2] = (float)cos((double)theta) * r;', 'out[2] = (float)cos((double)phi) * r;'),
    'select': ('r[o->a] = r[o->c + off / 4];', 'r[o->a] = r[o->c];'),
    'particle-bitmap': ('fx.bitmap = fx_int(&r[o->k]);', 'fx.bitmap = (int32_t)o->k;'),
    'particle-extra': ('fx.extra = fx_int(&r[o->k + 1]);', 'fx.extra = 0;'),
    'bitmap': ('next_bitmap = fx_int(&r[o->a]);', 'next_bitmap = fx_int(&r[o->a]) + 1;'),
    'owner-item-translate': ('h->owner_item_transform(h->context, (int32_t)o->k, &r[o->c], (int32_t)o->e, &r[o->a]);',
                             'h->owner_item_transform(h->context, (int32_t)o->k, &r[o->c], 0, &r[o->a]);'),
    'post-host': ('(host->item_transform && mu_rc_item_post_fx(it->type))', '(host->item_transform && 0)'),
    'hidden-wings': ('!(it->type >= 0x2382 && it->type <= 0x2385))', '!(it->type >= 0x2382 && it->type <= 0x2384))'),
    # RENDER-ITEMS-002U (part 23): the counter in the body chains (frame family)
    'frame-source': ('case 30: i = (int32_t)frame; break;', 'case 30: i = (int32_t)(frame + 1u); break;'),
    'frame-umod': ('case 31: i = (int32_t)((uint32_t)i % word); break;', 'case 31: i = (int32_t)((uint32_t)i % (word + 1u)); break;'),
    'frame-udiv': ('case 32: i = (int32_t)((uint32_t)i / word); break;', 'case 32: i = (int32_t)((uint32_t)i / (word + 1u)); break;'),
    'frame-u2d': ('case 33: d = (double)(uint32_t)i; break;', 'case 33: d = (double)i; break;'),
    'frame-item': ('value = body_scalar(p, s->item->time, s->item->frame);', 'value = body_scalar(p, s->item->time, 0u);'),
    'range-offset': ('integer = (int32_t)((uint32_t)integer + (uint32_t)p->k[0]);',
                     'integer = (int32_t)((uint32_t)integer + (uint32_t)p->k[0] + 1u);'),
    'range-product': ('value = value * other;', 'value = value + other;'),
    'range-product-left': ('memcpy(&value, input + p->a, 4);', 'memcpy(&value, input + p->a + 1, 4);'),
    'range-product-right': ('memcpy(&other, &input[p->k[0]], 4);', 'memcpy(&other, &input[p->k[0] + 1], 4);'),
    'body-carry': ('&last) &&\n        mu_rc_body_types[type].carry)', '&last) &&\n        0)'),
    # Not mutated: the unknown-counter refusal (frame_known; a C refusal that matches the client's kind and bitmap
    # passes the comparison by design, so only test_item_predraw's frame-counter test catches it), op 49's bone guard
    # (unreachable: the owner gate already requires bone < bones), the post gate's item-bone exemption (here the OBJECT's model is the item model, so both counts
    # are equal) and the random vector's clamps (every call passes constants inside the clamp ranges).
}


def mutations(vectors, plib):
    sources = {name: (ROOT/'reconstructed/renderchar'/name).read_text()
               for name in ('owner_fx.inc', 'rank5_owner.inc', 'renderchar.c')}
    caught = {}
    reference = C.CDLL(str(v.LIBRARY))
    counts = {i: quality.run_c(reference, case, extra)[2]
              for i, (family, case, extra, _) in enumerate(vectors) if family == 'body'}
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
            for i, (family, case, extra, expected) in enumerate(vectors):
                if family == 'body':
                    status, actual, used = quality.run_c(lib, case, extra)
                    detected += bool(status) or actual != expected or used != counts[i]
                    continue
                detected += not same(expected, run_c(lib, plib, case, extra, expected[3]))[0]
            caught[name] = detected
    survivors = [name for name, detected in caught.items() if not detected]
    if survivors:
        raise AssertionError(('surviving mutants', survivors))
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--predraw-cases', type=int, default=64, help='item states per type')
    parser.add_argument('--frame-cases', type=int, default=292, help='RENDER-ITEMS-002U: counter states per type')
    parser.add_argument('--skip-bodies', action='store_true', help='iteration only: no body family or table check')
    parser.add_argument('--types', help='iteration only: comma-separated hex types (no table check)')
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    global TYPES
    if args.types:
        TYPES = [int(x, 16) for x in args.types.split(',')]
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
        report['families']['hidden'], hidden = hidden_cases(wa, lib)
        vectors += hidden
        report['families']['frame'], frame = frame_cases(wa, lib, args.frame_cases)
        vectors += frame
    names, consts = program_names()
    lib.mu_rc_item_post_fx.restype = C.c_int
    if any(not lib.mu_rc_item_pre_fx(t) for t in TYPES if t in fxgen.PRE_FX_TYPES) or lib.mu_rc_item_pre_fx(0x0ae6):
        raise AssertionError('mu_rc_item_pre_fx disagrees with PRE_FX_TYPES')
    if [t for t in range(0x0ae6, 0x3a00) if lib.mu_rc_item_post_fx(t)] != sorted(fxgen.POST_FX_TYPES):
        raise AssertionError('mu_rc_item_post_fx disagrees with POST_FX_TYPES')
    report['families']['predraw'], predraw = predraw_cases(wa, lib, plib, args.predraw_cases, names, consts)
    vectors += predraw
    if args.mutations:
        report['mutants'] = mutations(vectors, plib)
    if not args.types and fxgen.generate() != (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text():
        raise AssertionError(('table drift', 'item_owner_fx.h'))
    if not args.skip_bodies and not args.types and \
            gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError(('table drift', 'item_bodies.h'))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
