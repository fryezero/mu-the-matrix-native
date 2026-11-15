#!/usr/bin/env python3
"""RENDER-ACTORS-008: ordered effect and link requests of RenderCharacter callers.

The recorder wraps the published renderchar World. TransformPosition 0x012b6ef1
is a named recorder that returns a unique marker, so every request position is
resolved to its bone matrix and local offset instead of a synthetic pose value.
The CRT rand service returns one authored value per run and records its call
sites; the clock 0x06fce370 is an authored fixture input. Sprite, particle,
bone-effect, joint and effect creators are recorders with complete arguments.
Nothing here executes or certifies a downstream consumer.
"""
import contextlib
import struct

import validate_renderchar as vr

SPRITE, PARTICLE, BONE_EFFECT, JOINT, EFFECT = 0x01692eb7, 0x0168fafd, 0x0150e746, 0x0153b02c, 0x013c0eaa
SERVICES = {SPRITE: 'sprite', PARTICLE: 'particle', BONE_EFFECT: 'bone-effect', JOINT: 'joint', EFFECT: 'effect'}
TRANSFORM_POSITION, RAND, CLOCK, GLOBAL_BONES = 0x012b6ef1, 0x01989721, 0x06fce370, 0x06fce398
OBJECT = vr.CHAR + 0x3254
# Authored (clock ms, rand value) fixtures. The first is the published 28-context default.
VARIED = ((777.0, 7), (123456.0, 29), (5000.5, 12345), (31415.9, 16), (0.0, 59), (250.0, 30))


def bits3(m, pointer):
    try:
        return list(struct.unpack('<3I', m.read(pointer, 12)))
    except Exception:
        return None


@contextlib.contextmanager
def recording(clock=0.0, rand=0, state=None):
    """Patch vr.World for one original execution. state receives rand sites."""
    state = state if state is not None else {}
    state.setdefault('rand_sites', [])
    old_world = vr.World

    def world(*world_args):
        w = old_world(*world_args)
        m = w.m
        m.wf(CLOCK, clock)
        marks = {}

        def site(m):
            return m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP)) - 5

        def transform(m):
            matrix, local, out, translate = [m.arg(i) for i in range(4)]
            n = len(marks) + 1
            mark = tuple(vr.f2u(1000.0 * n + k) for k in (1, 2, 3))
            for k in range(3):
                m.w32(out + 4 * k, mark[k])
            if vr.BONES <= matrix < vr.BONES + 48 * 200 and (matrix - vr.BONES) % 48 == 0:
                anchor = dict(kind='bone', bone=(matrix - vr.BONES) // 48)
            elif GLOBAL_BONES <= matrix < GLOBAL_BONES + 48 * 200 and (matrix - GLOBAL_BONES) % 48 == 0:
                anchor = dict(kind='pose-bone', bone=(matrix - GLOBAL_BONES) // 48)
            else:
                anchor = dict(kind='matrix', pointer=matrix)
            anchor.update(offset=bits3(m, local), translate=translate)
            marks[mark] = anchor
            w.calls.append(('skip', TRANSFORM_POSITION))
            return 0
        m.stub(TRANSFORM_POSITION, transform, 0x10)

        def random(m):
            state['rand_sites'].append(site(m))
            return rand
        m.stub(RAND, random, 0)

        def where(m, pointer):
            value = bits3(m, pointer)
            if value is not None and tuple(value) in marks:
                return dict(marks[tuple(value)])
            if OBJECT <= pointer < OBJECT + 0x400:
                return dict(kind='object', offset=pointer - OBJECT, value=value)
            return dict(kind='raw', value=value)

        def owner(pointer):
            return 0 if not pointer else 1 if pointer == OBJECT else 2

        def sprite(m):
            a = [m.arg(i) for i in range(8)]
            w.calls.append(('request', dict(service='sprite', site=site(m), id=a[0], position=where(m, a[1]),
                scale=a[2], light=bits3(m, a[3]), owner=owner(a[4]), rotation=a[5], blend=a[6], axes=a[7])))
            return 0

        def particle(m):
            a = [m.arg(i) for i in range(8)]
            w.calls.append(('request', dict(service='particle', site=site(m), id=a[0], position=where(m, a[1]),
                angle=where(m, a[2]), light=bits3(m, a[3]), subtype=a[4], scale=a[5], owner=owner(a[6]), extra=a[7])))
            return 0

        def joint(m):
            a = [m.arg(i) for i in range(10)]
            w.calls.append(('request', dict(service='joint', site=site(m), id=a[0], position=where(m, a[1]),
                target=where(m, a[2]), angle=where(m, a[3]), subtype=a[4], owner=owner(a[5]), scale=a[6],
                key=a[7] & 0xffff, skill=a[8] & 0xffff)))
            return 0

        def effect(m):
            a = [m.arg(i) for i in range(8)]
            w.calls.append(('request', dict(service='effect', site=site(m), id=a[0], position=where(m, a[1]),
                angle=where(m, a[2]), light=bits3(m, a[3]), subtype=a[4], owner=owner(a[5]))))
            return 0

        def bone_effect(m):
            a = [m.arg(i) for i in range(9)]
            w.calls.append(('request', dict(service='bone-effect', site=site(m), id=None, args=a,
                receiver=m.ecx())))
            return 0
        for address, handler in ((SPRITE, sprite), (PARTICLE, particle), (JOINT, joint), (EFFECT, effect),
                                 (BONE_EFFECT, bone_effect)):
            m.stub(address, handler, 0)
        return w
    try:
        vr.World = world
        yield state
    finally:
        vr.World = old_world


def requests(calls):
    return [c[1] for c in calls if c[0] == 'request']


def anchor_key(anchor):
    if anchor is None:
        return None
    if anchor['kind'] in ('bone', 'pose-bone'):
        return (anchor['kind'], anchor['bone'], tuple(anchor['offset']), anchor['translate'])
    if anchor['kind'] == 'object':
        return ('object', anchor['offset'])
    return (anchor['kind'],)


def structure(request):
    """Identity of a request without its light and without unresolved position values."""
    r = request
    if r['service'] == 'bone-effect':
        return ('bone-effect', r['site'])
    return (r['service'], r['site'], r['id'], r.get('subtype'), anchor_key(r['position']), anchor_key(r.get('angle')),
            anchor_key(r.get('target')), r.get('scale'), r.get('owner'), r.get('rotation'), r.get('blend'),
            r.get('axes'), r.get('extra'), r.get('key'), r.get('skill'))


def uniform(request):
    """The table-driven group: one sprite at an OBJECT bone, translate 1, owner NULL or the OBJECT."""
    p = request.get('position') or {}
    return request['service'] == 'sprite' and p.get('kind') == 'bone' and p.get('translate') == 1 and \
        request['owner'] in (0, 1) and request['light'] is not None


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def flicker(rand):
    """RenderCharacter 0x0136ac06: (float)(rand() % 30 + 70) * 0.01f, binary32."""
    return f32(f32(rand % 30 + 70) * f32(0.01))


def fit_light(samples):
    """samples: [(clock, rand, light bits)]. Returns (kind, colour bits, base bits) or None.

    kind 0 constant; 1 flicker * colour; 2 (sin(clock * 0.002) * 0.3 + base) * colour.
    Only a decimal colour whose products reproduce every sample bit-for-bit is accepted;
    the compiled function is compared with the original again, independently of this fit.
    """
    import math
    lights = {tuple(s[2]) for s in samples}
    if len(lights) == 1:
        return 0, list(samples[0][2]), 0
    def colours(factor0, light0):
        out = []
        for k in range(3):
            value = vr.u2f(light0[k]) / factor0 if factor0 else 0.0
            found = None
            for digits in range(0, 5):
                c = f32(round(value, digits))
                if vr.f2u(f32(factor0 * c)) == light0[k]:
                    found = c
                    break
            if found is None:
                return None
            out.append(found)
        return out
    def pulse(clock, base):
        s = f32(math.sin(f32(f32(clock) * f32(0.002))))
        return f32(f32(s * f32(0.3)) + base)
    clock0, rand0, light0 = samples[0]
    c = colours(flicker(rand0), light0)
    if c and all([vr.f2u(f32(flicker(r) * c[k])) for k in range(3)] == list(l) for _, r, l in samples):
        return 1, [vr.f2u(v) for v in c], 0
    for base in (f32(0.7), f32(0.8)):
        c = colours(pulse(clock0, base), light0)
        if c and all([vr.f2u(f32(pulse(t, base) * c[k])) for k in range(3)] == list(l) for t, _, l in samples):
            return 2, [vr.f2u(v) for v in c], vr.f2u(base)
    return None


def link_requests(args, row, bones, slot, alpha=.375, clock=0.0, rand=0, watch_bones=False):
    """RenderLinkItem 0x012bd910 from entry for one selected hand. Returns run, names, requests, bone writes."""
    t, level = row['slots'][6 + slot]
    state = {}
    with recording(clock, rand, state):
        w = vr.link_world(args, t)
    m = w.m
    part = vr.CHAR + 0x19ac
    m.write(part, struct.pack('<hBBBB', t, level, 0, 0, bones[slot]))
    m.write(vr.CHAR + 0x32b0, struct.pack('<I', row['model']))
    w.add_model(row['model'], vr.PLAYER_MODEL, bones=60, meshes=1, actions=16)
    m.write(vr.CHAR + 0x32f4, struct.pack('<I', row['scale_bits'] or vr.f2u(.9)))
    m.write(vr.CHAR + 0x3330, struct.pack('<f', alpha))
    writes = []
    hook = None
    if watch_bones:
        from unicorn import UC_HOOK_MEM_WRITE
        hook = m.uc.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, address, size, value, data: writes.append(address),
                             begin=vr.BONES, end=vr.BONES + 48 * 200 - 1)
    run = m.run(0x012bd910, [0, 0, 0, vr.CHAR, part, t, level, 0, 0, 1, 0, 1])
    if hook is not None:
        m.uc.hook_del(hook)
    return run, w, requests(w.calls), writes, state['rand_sites']


def hexf(bits):
    return '%.9g' % vr.u2f(bits)


def describe_anchor(anchor):
    if anchor is None:
        return '', ''
    if anchor['kind'] in ('bone', 'pose-bone'):
        name = ('object bone %d' if anchor['kind'] == 'bone' else 'posed link bone %d') % anchor['bone']
        if anchor['translate'] != 1:
            name += ' translate %d' % anchor['translate']
        return name, ' '.join(hexf(v) for v in anchor['offset'])
    if anchor['kind'] == 'object':
        return 'OBJECT+%#x' % anchor['offset'], ''
    return 'computed vector', ''
