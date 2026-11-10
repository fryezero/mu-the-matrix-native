#!/usr/bin/env python3
"""MUUN-VISUAL-001 base slot against pinned original instructions.

Setup runs 0x009a9516 with an allocated, dead OBJECT. Allocation, time, live setter, bounds, auxiliary creation
and attach are named stubs. Select runs 0x009a9e29: model/action lookup and SetAction are recording stubs,
rand and float sqrt/atan are host math services. Spring 0x009aafd4 and follow 0x009aa268 run whole, including
CreateAngle and TurnAngle2. Render 0x009a9ae2 and logic 0x009a99a9 compare base owner/visibility gates,
with model/effect/auxiliary services stubbed. No packet handler or opaque module runs.
"""
import argparse
import ctypes as C
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time

import actor_machine as am
import pins
import validate_combat as vc

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
SLOT, OBJ, OWNER, INFO, MODEL, ACTION = 0x20000000, 0x20100000, 0x20200000, 0x20300000, 0x20400000, 0x20500000
BODIES = {'setup': (0x9a9516, 0x9a99a9), 'select': (0x9a9e29, 0x9aa1b9),
          'spring': (0x9aafd4, 0x9ab41e), 'follow': (0x9aa268, 0x9aa509),
          'logic_gate': (0x9a99a9, 0x9a9ae2), 'render_gate': (0x9a9ae2, 0x9a9c88)}
F3 = C.c_float * 3


class Info(C.Structure):
    _fields_ = [('code', C.c_int32), ('item', C.c_int32), ('scale', C.c_float), ('offset', F3),
                ('speed', C.c_float * 5)]


class Owner(C.Structure):
    _fields_ = [('key', C.c_int32), ('live', C.c_uint8), ('moving', C.c_uint8), ('position', F3), ('angle', F3)]


class State(C.Structure):
    _fields_ = [('model', C.c_int32), ('key', C.c_int32), ('state', C.c_int32), ('action', C.c_uint16),
                ('prior_action', C.c_uint16), ('scale', C.c_float), ('radius', C.c_float), ('frame', C.c_float),
                ('prior_frame', C.c_float)] + [(n, F3) for n in
                ('position', 'angle', 'offset', 'target', 'step', 'acceleration', 'velocity', 'force', 'delta')]


# Native field -> client container, offset, count, format.
FIELDS = {'model': ('object', 0x5c, 1, 'i'), 'key': ('slot', 0x1c, 1, 'i'), 'state': ('slot', 0x18, 1, 'i'),
          'action': ('object', 0x2a, 1, 'H'), 'prior_action': ('object', 0x2c, 1, 'H'),
          'scale': ('object', 0xa0, 1, 'f'), 'radius': ('slot', 0x20, 1, 'f'),
          'frame': ('object', 0xd0, 1, 'f'), 'prior_frame': ('object', 0xd4, 1, 'f'),
          'position': ('object', 0x158, 3, 'f'), 'angle': ('object', 0x164, 3, 'f'),
          **{n: ('slot', o, 3, 'f') for n, o in [('offset', 0x24), ('target', 0x30), ('step', 0x3c),
              ('acceleration', 0x48), ('velocity', 0x54), ('force', 0x60), ('delta', 0x6c)]}}


def bind(path):
    lib = C.CDLL(str(path))
    lib.mu_mv_setup.argtypes = [C.POINTER(State), C.POINTER(Info), C.POINTER(Owner)]
    lib.mu_mv_select.argtypes = [C.POINTER(State), C.POINTER(Info), C.POINTER(Owner), C.c_int32, C.c_int32]
    lib.mu_mv_spring.argtypes = [C.POINTER(State), C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(C.c_float)]
    lib.mu_mv_follow.argtypes = [C.POINTER(State), C.POINTER(Info), C.POINTER(Owner)]
    lib.mu_mv_alive.argtypes = [C.c_int] * 6
    lib.mu_mv_visible.argtypes = [C.c_int] * 5
    return lib


def build(folder, source=None):
    folder = Path(folder)
    (folder/'muun').mkdir()
    shutil.copy(ROOT/'reconstructed/muun/visual.h', folder/'muun/visual.h')
    (folder/'muun/visual.c').write_text(source or (ROOT/'reconstructed/muun/visual.c').read_text())
    for d in ('movement', 'record-math'):
        shutil.copytree(ROOT/'reconstructed'/d, folder/d, ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
    out = folder/f'muun.{SUFFIX}'
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                    '-ffp-contract=off', '-fno-fast-math', str(folder/'muun/visual.c'),
                    str(folder/'movement/client_movement.c'), str(folder/'record-math/record_math.c'), '-lm',
                    '-o', str(out)], check=True, capture_output=True)
    return bind(out)


def raw_state(state, info, owner):
    payloads = {'slot': bytearray(0xbc), 'object': bytearray(0x3d8), 'owner': bytearray(0x3670),
                'info': bytearray(0x27c), 'model': bytearray(0x100), 'action': bytearray(16)}
    for name, (region, offset, count, fmt) in FIELDS.items():
        value = getattr(state, name)
        values = list(value) if count > 1 else [value]
        struct.pack_into('<' + fmt * count, payloads[region], offset, *values)
    struct.pack_into('<III', payloads['slot'], 4, OWNER, OBJ, INFO)
    struct.pack_into('<I', payloads['object'], 0x34c, OWNER + 0x3254)
    struct.pack_into('<i', payloads['info'], 0, info.code)
    struct.pack_into('<i', payloads['info'], 0x264, info.item + 0xae6)
    struct.pack_into('<f', payloads['info'], 0x110, info.scale)
    struct.pack_into('<3f', payloads['info'], 0x114, *info.offset)
    struct.pack_into('<5f', payloads['info'], 0x238, *info.speed)
    struct.pack_into('<i', payloads['owner'], 0x3244, owner.key)
    payloads['owner'][0x38] = owner.moving
    struct.pack_into('<3f', payloads['owner'], 0x3254 + 0x158, *owner.position)
    struct.pack_into('<3f', payloads['owner'], 0x3254 + 0x164, *owner.angle)
    return payloads


def regions(payloads):
    return [am.defined_region(n, a, payloads[n]) for n, a in
            [('slot', SLOT), ('object', OBJ), ('owner', OWNER), ('info', INFO), ('model', MODEL), ('action', ACTION)]]


def same_state(s, result, names):
    for name in names:
        region, offset, count, fmt = FIELDS[name]
        got = getattr(s, name)
        expected = result['regions'][region][offset:offset + struct.calcsize(fmt) * count]
        actual = struct.pack('<' + fmt * count, *(list(got) if count > 1 else [got]))
        if expected != actual:
            return [name, expected.hex(), actual.hex()]
    return None


def base_stubs():
    return {0x961a07: lambda m: m.x87_return(vc.f32(math.sqrt(m.float_argument(0)))),
            0x12b2bca: lambda m: m.x87_return(vc.f32(math.atan(m.float_argument(0))))}


def cases(n):
    rng = random.Random('muun-visual-001')
    for k in range(n):
        i = Info(173, rng.randrange(0x2000, 0x2200), rng.choice([0.5, 1, 1.25]),
                 F3(*[rng.uniform(-200, 200) for _ in range(3)]),
                 (C.c_float * 5)(*[rng.choice([0.0, 0.1, 0.25, 0.5, 1.0]) for _ in range(5)]))
        o = Owner(rng.randrange(-300, 300), 1, k % 2,
                  F3(*[rng.uniform(-1000, 1000) for _ in range(3)]), F3(0, 0, rng.randrange(360)))
        s = State()
        s.model, s.key, s.scale, s.radius = i.item + 0xae6, o.key, i.scale, rng.choice([0.0, 10.0, 100.0, 250.0])
        s.state = k % 6
        s.action = s.state
        s.position[:] = [vc.f32(o.position[c] + rng.choice([-250, -100, 0, 10, 100, 250])) for c in range(3)]
        s.angle[:], s.offset[:] = o.angle[:], i.offset[:]
        s.frame = rng.choice([0.0, 2.0, 9.5, 10.0, 11.0])
        for name in ('target', 'step', 'acceleration', 'velocity', 'force', 'delta'):
            getattr(s, name)[:] = [rng.uniform(-1, 1) for _ in range(3)]
        yield s, i, o, rng.choice([0, 1, 2, 10, 500, 1000]), rng.choice([1, 10, 20])


def compare(lib, machine, count):
    rows = {name: {'cases': 0, 'equal': 0, 'mismatches': 0, 'first': None} for name in BODIES}
    def record(name, result, detail):
        row = rows[name]; row['cases'] += 1
        ok = result['ok'] and detail is None
        row['equal'] += int(ok); row['mismatches'] += int(not ok)
        if not ok and row['first'] is None:
            row['first'] = {'detail': detail, 'stopped': str(result.get('stopped')), 'checks': result['checks'],
                            'error': result.get('error')}
    for original, info, owner, random_value, keys in cases(count):
        for family in ('setup', 'select', 'spring', 'follow'):
            s = State.from_buffer_copy(original)
            p = raw_state(s, info, owner)
            stubs = base_stubs()
            args, cleanup = [], 0
            if family == 'setup':
                # The allocated OBJECT starts dead; constructors already supplied zero action/state/velocity.
                s = State(); p = raw_state(s, info, owner)
                p['slot'][0x1c:0x20] = bytes(4)
                stubs.update({0x95f977: lambda m: 0, 0x129f4a5: lambda m: (0, 4),
                              0x9ab41e: lambda m: 0, 0x9a9c88: lambda m: 0, 0x9af699: lambda m: 0})
                # The clock import, only a stored setup timestamp.
                clock = 0x2f000000
                from unicorn import UC_PROT_ALL
                if not getattr(machine, 'clock_mapped', False):
                    machine.uc.mem_map(clock, 0x1000, UC_PROT_ALL)
                    machine.uc.mem_write(0x1a7c49c, struct.pack('<I', clock))
                    machine.clock_mapped = True
                stubs[clock] = lambda m: 12345
                args, cleanup = [INFO, OWNER, owner.key, 1], 16
                lib.mu_mv_setup(C.byref(s), C.byref(info), C.byref(owner))
                names = tuple(FIELDS)
            elif family == 'select':
                struct.pack_into('<h', p['action'], 8, keys)
                stubs.update({0x1989721: lambda m: random_value, 0x966cc4: lambda m: MODEL,
                              0xeaaa44: lambda m: (ACTION, 8), 0x12affa4: lambda m: 0})
                lib.mu_mv_select(C.byref(s), C.byref(info), C.byref(owner), keys, random_value)
                names = ('state',)
            elif family == 'spring':
                # In-place alias is the production caller's contract.
                args, cleanup = [OBJ + 0x158, SLOT + 0x30, OBJ + 0x158], 12
                lib.mu_mv_spring(C.byref(s), s.position, s.target, s.position)
                names = ('position', 'step', 'acceleration', 'velocity', 'force', 'delta')
            else:
                lib.mu_mv_follow(C.byref(s), C.byref(info), C.byref(owner))
                names = ('position', 'angle', 'target', 'step', 'acceleration', 'velocity', 'force', 'delta')
            result = machine.execute(BODIES[family][0], args, regions(p), stubs, ecx=SLOT, cleanup=cleanup)
            record(family, result, same_state(s, result, names))
    # Exhaustive base gates. Services are recording stubs, no auxiliary exception.
    for has, live, frustum, match in itertools.product((0, 1), repeat=4):
        s, info, owner, _, _ = next(cases(1)); p = raw_state(s, info, owner)
        struct.pack_into('<I', p['slot'], 8, OBJ if has else 0)
        struct.pack_into('<I', p['slot'], 0, MODEL)
        struct.pack_into('<I', p['model'], 0x18, 0x9aa509)
        p['slot'][0x10] = 0
        if not match: struct.pack_into('<i', p['slot'], 0x1c, owner.key + 1)
        calls = []
        def draw(m): calls.append('draw'); return 0
        stubs = {0x95f977: lambda m: live, 0x16ccce7: lambda m: frustum, 0x1295ade: lambda m: (0, 4),
                 0x17ec896: draw, 0x9aa509: lambda m: 0, 0x129f671: lambda m: (0, 4), 0x17edf43: lambda m: 0}
        global_dt = am.defined_region('dt', 0x1cf103c, struct.pack('<f', 0.04), writable=False)
        result = machine.execute(0x9a9ae2, [], regions(p) + [global_dt], stubs, ecx=SLOT)
        got = lib.mu_mv_visible(has, live, frustum, s.key, s.key if match else s.key + 1)
        record('render_gate', result, None if bool(got) == bool(calls) else ['visible', calls, got])
    for has, host, live, scene, owner_live, kind in itertools.product((0, 1), (0, 1), (0, 1), (5, 6), (0, 1), (0, 1, 2)):
        s, info, owner, _, _ = next(cases(1)); p = raw_state(s, info, owner)
        struct.pack_into('<I', p['slot'], 8, OBJ if has else 0)
        struct.pack_into('<I', p['object'], 0x34c, OWNER + 0x3254 if host else 0)
        p['owner'][0x3254 + 0x3b] = kind
        calls = []
        def is_live(m): return live if m.uc.reg_read(m.x86.UC_X86_REG_ECX) == OBJ else owner_live
        def select(m): calls.append('select'); return 0
        stubs = {0x95f977: is_live, 0x9b0bc1: lambda m: scene, 0x129f4a5: lambda m: (0, 4),
                 0x12af883: lambda m: 0, 0x9a9e29: select, 0x9aa1b9: lambda m: 0,
                 0x9aa268: lambda m: 0}
        result = machine.execute(0x9a99a9, [], regions(p), stubs, ecx=SLOT)
        got = lib.mu_mv_alive(has, host, live, scene, owner_live, kind)
        record('logic_gate', result, None if bool(got) == bool(calls) else ['alive', calls, got])
    return rows


MUTANTS = [
    ('model_base', 'info->item + 0xae6', 'info->item + 0xae7'),
    ('scale', 's->scale = info->scale;', 's->scale = 1.0f;'),
    ('setup_position', 'owner->position[k] + s->offset[k]', 'owner->position[k] - s->offset[k]'),
    ('radius', 'info->offset[1] * info->offset[1]', '0.0f'),
    ('idle_random', 'rand_value % 500 == 0', 'rand_value % 500 == 1'),
    ('chase_radius', 'distance > s->radius', 'distance > s->radius + 20.0f'),
    ('animation_end', 's->frame + info->speed[s->state] >= (float)keys', 's->frame >= (float)keys'),
    ('owner_motion', '!owner->moving &&', 'owner->moving &&'),
    ('chase_hysteresis', 's->radius + 10.0f >= distance', 's->radius >= distance'),
    ('spring_stiffness', '-1.4f * s->force[k]', '-1.3f * s->force[k]'),
    ('spring_damping', '20.0f * s->velocity[k]', '2.0f * s->velocity[k]'),
    ('spring_mass', '1.0f / 25.0f', '1.0f / 20.0f'),
    ('spring_memory', 's->force[k] - s->velocity[k]', 's->force[k] + s->velocity[k]'),
    ('follow_height', 's->target[2] + info->offset[2]', 's->target[2]'),
    ('follow_turn', 'heading, 10.0f', 'heading, 5.0f'),
    ('owner_life', 'owner_live && owner_kind == 1', 'owner_live || owner_kind == 1'),
    ('owner_key', 'key == owner_key', 'key != owner_key'),
    ('frustum', 'frustum == 1', 'frustum == 0'),
]


def run(count=200, mutations=False):
    started = time.monotonic()
    text = pins.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = pins.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = vc.Combat(text, data)
    with tempfile.TemporaryDirectory(prefix='muun-visual-') as td:
        baseline = Path(td)/'baseline'; baseline.mkdir()
        families = compare(build(baseline), machine, count)
        mutants = {}
        source = (ROOT/'reconstructed/muun/visual.c').read_text()
        if mutations:
            for name, old, new in MUTANTS:
                # Some branch tests deliberately occur at several action cases; mutate the first one only.
                if old not in source: raise ValueError(f'missing mutant anchor: {name}')
                folder = Path(td)/name; folder.mkdir()
                rows = compare(build(folder, source.replace(old, new, 1)), machine, count)
                mutants[name] = {'caught': sum(r['mismatches'] for r in rows.values())}
    return {'families': families, 'instruction_cases': sum(r['cases'] for r in families.values()),
            'all_equal': all(r['mismatches'] == 0 for r in families.values()), 'mutants': mutants,
            'all_mutants_caught': all(r['caught'] > 0 for r in mutants.values()),
            'bodies': {n: {'start': hex(a), 'end': hex(b), 'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
                       for n, (a, b) in BODIES.items()}, 'wall_seconds': time.monotonic() - started}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=200)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1: parser.error('--cases must be positive')
    result = run(args.cases, args.mutations)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['all_equal'] and result['all_mutants_caught'] else 1)
