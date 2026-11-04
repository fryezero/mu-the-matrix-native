#!/usr/bin/env python3
"""RENDER-WORLDS-AFTER5 instruction comparisons (docs/research/client-worlds-after5.md).

The object action registry 0x01ec7d5c against reconstructed/objects/action_registry.c:

set_action: SetAction 0x00ce4a17 (thiscall registry, object, action) and its nine handlers 0x00ce1460..0x00ce15de.
tick: the registry tick 0x00ce4b5b (thiscall registry, object) and the tick handlers 0, 1, 2, 3, 5 and 7
(0x00ce1646, 0x00ce165c, 0x00ce1737, 0x00ce1830, 0x00ce1b61, 0x00ce20c2), whose action changes call SetAction back
through the std::function the tick builds (0x00ce536e, invoked by 0x00ce3c2f). Tick handlers 4, 6 and 8 test the
hero's box against the object's (0x018500bf) and are not ported.
live_rows (private, --lang-dir): every row of the local mapanim.tsv (the live MapObjectAnimationInfo tables) through
SetAction and the tick, in its own world's table, over objects at the action's start, end and between.

The registry itself is built by its original constructor 0x00ce38a8 (the two handler vectors of std::function
objects: 0x00ce4f39, 0x00ce4d20) once, with operator new 0x0191ba7b as a bump allocator and the CRT free
0x019a4d50 a no-op; its map +0x10 is then pointed at a case tree of MSVC nodes (head _Isnil 1; node key +0x10,
entry +0x14) built from the case's entries. Stubbed: the registry getter 0x00ce3dad (a thread-safe static), GetModel
0x00966cc4 / 0x00eaa8cf (the case model: action count +0x26, records +0x30 with keys +8 and lock +0xa), rand
0x01989721 (the MSVC LCG, the same sequence on both sides). sqrt 0x00961a07 and the hero position accessor
0x00cfc922 over [0x0a39d754] + 0x33ac run as client code. All OBJECT bytes, the tick's return value and the rand
sequence are compared.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import actor_machine as am
import validate_object_render as v
import pins

ROOT = Path(__file__).resolve().parents[1]
SET_ACTION, TICK, CONSTRUCTOR = 0x00ce4a17, 0x00ce4b5b, 0x00ce38a8
GETTER, MODEL_MANAGER, GET_MODEL, RAND = 0x00ce3dad, 0x00966cc4, 0x00eaa8cf, 0x01989721
NEW, FREE = 0x0191ba7b, 0x019a4d50
HERO_POINTER, HERO_POSITION = 0x0a39d754, 0x33ac
COOKIE, MATHERR = 0x01cf65c0, 0x0bdcf8e0   # the CRT sqrt's NaN path (as RENDER-WORLDS-AFTER4)
ISA = 0x0bdcb280          # __isa_available 0: __ftol2's non-FISTTP path (as validate_crypto)
KEY_FACTOR = 0x06fbaa58   # 0x0112bbba's cached factor: 0, so each case computes (int)pow(10, digits of 300)
HEAP, HEAP_BYTES = 0x42000000, 0x100000
FEATURE = pins.FEATURE09.read()   # memcpy's CPU feature word 0x01cf6618 (the entry copy 0x00ce60f3)
REGISTRY = HEAP
MODEL, RECORDS, TABLE, HERO = 0x43000000, 0x43001000, 0x44000000, 0x45000000
TABLE_BYTES = 0x20000
MANAGER_COOKIE = 0x46000000
BODIES = {'set_action': (0x00ce1460, 0x00ce1646), 'tick_handlers': (0x00ce1646, 0x00ce2497),
          'set_action_tick': (0x00ce4a17, 0x00ce4c8f), 'registry': (0x00ce38a8, 0x00ce3931)}


class AnimEntry(C.Structure):
    _fields_ = [('type', C.c_int32), ('action', C.c_int32), ('speed', C.c_float), ('handler', C.c_int32),
                ('param', C.c_int32), ('extra_count', C.c_int32), ('extra', C.POINTER(C.c_int32))]


MODEL_FN = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int32, C.c_int32, C.POINTER(C.c_int32), C.POINTER(C.c_int16),
                       C.POINTER(C.c_uint8))


class AnimInputs(C.Structure):
    _fields_ = [('entries', C.POINTER(AnimEntry)), ('count', C.c_int32), ('model', MODEL_FN),
                ('rand_fn', v.RAND_FN), ('context', C.c_void_p), ('hero', C.c_float * 2)]


def bind(path):
    lib = v.Library(path)
    d = lib.dll
    d.mu_action_set.argtypes = [C.c_void_p, C.c_int32, C.POINTER(AnimInputs)]
    d.mu_action_set.restype = C.c_int
    d.mu_action_tick.argtypes = [C.c_void_p, C.POINTER(AnimInputs), C.POINTER(C.c_int)]
    d.mu_action_tick.restype = C.c_int
    return lib


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    return bind(root / 'objects' / ('libobjects.' + v.SUFFIX))


def key(kind, action):
    return (1000 * action + kind) & 0xffffffff


# ---------------------------------------------------------------- the client side

class Registry:
    """The registry as its constructor leaves it (heap bytes), plus the bump pointer after it."""

    def __init__(self, machine):
        self.next = HEAP + 0x100
        heap = am.defined_region('heap', HEAP, b'\xcd' * HEAP_BYTES)
        r = v.run(machine, CONSTRUCTOR, [], [heap], self.stubs(), ecx=REGISTRY)
        if v.stopped_reason(r):
            raise RuntimeError(('registry constructor', v.stopped_reason(r)))
        self.heap, self.heap_end = r['regions']['heap'], self.next

    def stubs(self):
        def new(m):
            n = m.argument(0)
            a = (self.next + 15) & ~15
            self.next = a + max(n, 1)
            if self.next > HEAP + HEAP_BYTES:
                m.stop(('heap exhausted', n))
            return a, 0
        return {NEW: new, FREE: lambda m: (0, 0)}


def tree(entries):
    """MSVC map nodes for entries (sorted by key), balanced, in the TABLE region: (bytes, head)."""
    out = bytearray(TABLE_BYTES)
    head = TABLE
    nodes, extras = [], TABLE + 0x10000
    items = sorted(entries, key=lambda e: key(e['type'], e['action']))
    for i, e in enumerate(items):
        nodes.append(TABLE + 0x40 + 0x40 * i)
    def put(address, fmt, *values):
        struct.pack_into(fmt, out, address - TABLE, *values)
    def link(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        n = nodes[mid]
        left, right = link(lo, mid, n), link(mid + 1, hi, n)
        put(n, '<IIIBB', left, parent, right, 1, 0)
        return n
    root = link(0, len(items), head)
    for i, e in enumerate(items):
        n = nodes[i]
        begin = extras
        for x in e['extra']:
            put(extras, '<i', x)
            extras += 4
        put(n + 0x10, '<I', key(e['type'], e['action']))
        put(n + 0x14, '<iifii', e['type'], e['action'], e['speed'], e['handler'], e['param'])
        put(n + 0x28, '<III', begin, extras, extras)
    put(head, '<IIIBB', nodes[0] if nodes else head, root, nodes[-1] if nodes else head, 1, 1)
    return bytes(out), head, len(items)


def client(machine, registry, case, call):
    """Runs SetAction or the tick as client code: (result, OBJECT bytes, rand seed)."""
    heap = bytearray(registry.heap)
    table, head, size = tree(case['entries'])
    struct.pack_into('<II', heap, 0x10, head, size)   # the registry map +0x10 -> the case tree
    model = bytearray(0x40)
    struct.pack_into('<h', model, 0x26, case['count'])
    struct.pack_into('<I', model, 0x30, RECORDS)
    records = am.Region('records', RECORDS, bytearray(b'\xcd' * 0x400), defined=bytearray(0x400))
    for a, (keys, lock) in enumerate(case['records']):
        records.define(RECORDS + 16 * a + 8, struct.pack('<hB', keys, lock))
    hero = bytearray(0x3400)
    struct.pack_into('<3f', hero, HERO_POSITION, case['hero'][0], case['hero'][1], 0.0)
    registry.next = registry.heap_end
    rand = v.MsvcRand(case['seed'])
    stubs = registry.stubs()
    stubs.update({GETTER: lambda m: (REGISTRY, 0), MODEL_MANAGER: lambda m: (MANAGER_COOKIE, 0),
                  GET_MODEL: lambda m: ((MODEL if case['has_model'] and m.argument(0) == case['type'] else 0), 4),
                  RAND: lambda m: (rand(), 0)})
    regions = v.global_regions(0, 6, [
        am.Region('heap', HEAP, heap),
        am.defined_region('object', v.OBJECTS, case['object']),
        am.defined_region('model', MODEL, bytes(model), writable=False),
        records,
        am.defined_region('table', TABLE, table, writable=False),
        am.defined_region('hero-pointer', HERO_POINTER, struct.pack('<I', HERO), writable=False),
        am.defined_region('hero', HERO, bytes(hero), writable=False),
        am.defined_region('feature', pins.FEATURE09.base, FEATURE, writable=False),
        am.defined_region('isa', ISA, struct.pack('<I', 0), writable=False),
        am.defined_region('key-factor', KEY_FACTOR, struct.pack('<I', 0)),
        am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
        am.defined_region('matherr', MATHERR, struct.pack('<I', 0xbb40e64e), writable=False)])
    if call == 'set':
        r = v.run(machine, SET_ACTION, [v.OBJECTS, case['action']], regions, stubs, ecx=REGISTRY, cleanup=8)
    else:
        r = v.run(machine, TICK, [v.OBJECTS], regions, stubs, ecx=REGISTRY, cleanup=4)
    return r, rand.seed


# ---------------------------------------------------------------- the C side

def native(lib, case, call):
    entries = (AnimEntry * max(1, len(case['entries'])))()
    keep = []
    for i, e in enumerate(case['entries']):
        extra = (C.c_int32 * max(1, len(e['extra'])))(*e['extra'])
        keep.append(extra)
        entries[i] = AnimEntry(e['type'], e['action'], e['speed'], e['handler'], e['param'], len(e['extra']),
                               C.cast(extra, C.POINTER(C.c_int32)))
    rand = v.MsvcRand(case['seed'])

    def model(ctx, kind, action, count, keys, lock):
        if not case['has_model'] or kind != case['type']:
            return 0
        count[0] = case['count']
        if 0 <= action < len(case['records']):
            keys[0], lock[0] = case['records'][action]
        return 1
    model_fn, rand_fn = MODEL_FN(model), v.RAND_FN(lambda c: rand())
    inputs = AnimInputs(C.cast(entries, C.POINTER(AnimEntry)), len(case['entries']), model_fn, rand_fn, None,
                        (C.c_float * 2)(*case['hero']))
    obj = C.create_string_buffer(case['object'], v.OBJ_SIZE)
    found = C.c_int(0)
    if call == 'set':
        status = lib.dll.mu_action_set(obj, case['action'], C.byref(inputs))
    else:
        status = lib.dll.mu_action_tick(obj, C.byref(inputs), C.byref(found))
    return status, found.value, obj.raw, rand.seed


# ---------------------------------------------------------------- cases

SET_HANDLERS = list(range(9))
TICK_HANDLERS = [0, 1, 2, 3, 5, 7]


def speed(g):
    return v.f32(g.choice([0.16, 0.3, 0.07, 0.5, 4.0, 10.0, 0.21, 0.0, -0.1, g.uniform(0.0, 1.0)]))


def extras(g, handler, count):
    act = lambda: g.choice(list(range(-1, count + 2)) + list(range(count)) * 3)   # noqa: E731
    if handler in (2, 3):   # SetAction: [lo, hi) of the first loop limit; tick 3: random actions from [2]
        lo = g.randrange(0, 8)
        out = [lo, lo + g.choice([1, 2, 3, 5, -1, -3])] + [act() for _ in range(g.randrange(1, 4))]
        return out
    if handler == 8:
        return [g.randrange(-50, 900) for _ in range(g.choice([0, 3, 6, 7, 7, 7, 8]))]
    if handler in (5, 7):
        return [g.choice([0, 1, 2, 3, 0, 2, 4, -1])] + [act() for _ in range(g.randrange(0, 3))]
    return [act() for _ in range(g.randrange(1, 4))]


def entry(g, kind, action, handlers, count):
    h = g.choice(handlers)
    return {'type': kind, 'action': action, 'speed': speed(g), 'handler': h,
            'param': g.choice([0, 300, 400, 500, g.randrange(-50, 2000)]), 'extra': extras(g, h, count)}


def case_object(g, kind, action, frame, poison=True):
    raw = bytearray(v.poison_object(g) if poison else bytes(v.OBJ_SIZE))
    v.put_i(raw, 0x5c, kind)
    struct.pack_into('<HH', raw, 0x2a, action & 0xffff, g.randrange(0, 6))
    v.put_f(raw, 0xd0, frame)
    v.put_f(raw, 0xd4, v.f32(g.uniform(0, 30)))
    v.put_f(raw, 0xbc, v.f32(g.choice([0.16, 0.3, g.uniform(0, 1)])))
    v.put_f(raw, 0xe0, 0.1)
    struct.pack_into('<ii', raw, 0x30, g.randrange(-2, 9), g.randrange(-2, 9))
    v.put_f(raw, 0x158, v.f32(g.uniform(0, 25600)), v.f32(g.uniform(0, 25600)))
    return raw


def random_case(g, call, handlers):
    kind = g.choice([13, 30, 66, 147, 177, 0, 299, g.randrange(0, 300)])
    count = g.choice([1, 2, 3, 4, 4, 5, 8, 0, -1])
    records = [(g.choice([1, 2, 10, 20, 32, g.randrange(1, 60)]), g.choice([0, 0, 1])) for _ in range(max(count, 0))]
    action = g.choice(list(range(max(count, 1))) * 3 + [-1, count, count - 1, 7, 0])
    current = g.choice([action, 0, 1, 2, 3]) if call == 'set' else g.randrange(0, max(count, 1))
    entries = []
    for a in range(0, max(count, 1) + 1):
        if g.random() < 0.92:
            entries.append(entry(g, kind, a, handlers, count))
    for _ in range(g.randrange(0, 4)):   # other types, and a key alias 1000 * 1 + k == 1000 * 0 + (1000 + k)
        other = g.choice([kind + 1, kind - 1, kind + 1000, g.randrange(0, 300)])
        entries.append(entry(g, other, g.randrange(0, 4), handlers, count))
    seen, unique = set(), []
    for e in entries:
        if key(e['type'], e['action']) not in seen:
            seen.add(key(e['type'], e['action']))
            unique.append(e)
    keys = records[current][0] if 0 <= current < len(records) else 10
    own = next((e for e in unique if e['type'] == kind and e['action'] == current), None)
    if call == 'tick' and own and count <= 0:   # no action record: only handler 0 reads none
        own['handler'] = 0
    end = keys - (own['speed'] if own else 0.16)
    frame = v.f32(g.choice([end, end, end - 1e-3, end + 1e-3, end - 1.0, end - 1.0 + 1e-3, end - 1.0 - 1e-3, end - 0.5, end + 0.5, 0.0, keys,
                            keys - 1, math.nan, g.uniform(0, max(keys, 1))]))
    obj = case_object(g, kind, current, frame)
    ox, oy = struct.unpack_from('<2f', obj, 0x158)
    param = own['param'] if own else 300
    dist = g.choice([param - 0.5, param + 0.5, param, 0.0, param * 2.0, g.uniform(0, 3000)])
    ang = g.uniform(0, 2 * math.pi)
    hero = [v.f32(ox + dist * math.cos(ang)), v.f32(oy + dist * math.sin(ang))]
    if g.random() < 0.03:
        hero[g.randrange(2)] = v.f32(math.nan)
    return {'type': kind, 'count': count, 'records': records, 'action': action, 'entries': unique,
            'has_model': g.random() < 0.93, 'object': bytes(obj), 'hero': hero, 'seed': g.getrandbits(32)}


def compare(machine, registry, lib, case, call, tally, label):
    r, client_seed = client(machine, registry, case, call)
    stop = v.stopped_reason(r)
    if stop:
        tally.add(False, {'case': label}, stop)
        return
    status, found, obj, seed = native(lib, case, call)
    cobj = r['regions']['object']
    diff = [hex(k) for k in range(v.OBJ_SIZE) if obj[k] != cobj[k]]
    ok = not diff and seed == client_seed and status != 2 and (call == 'set' or found == (r['eax'] & 0xff))
    tally.count('status %d' % status)
    tally.count('changed', int(cobj != case['object']))
    tally.count('rand', int(seed != case['seed']))
    if call == 'tick':
        tally.count('found', found)
        own = next((e for e in case['entries'] if e['type'] == case['type'] and
                    e['action'] == struct.unpack_from('<H', case['object'], 0x2a)[0]), None)
        if own and found:
            tally.count('handler %d' % own['handler'])
            tally.count('action changed', int(cobj[0x2a:0x2c] != case['object'][0x2a:0x2c]))
    else:
        own = next((e for e in case['entries'] if e['type'] == case['type'] and e['action'] == case['action']), None)
        if own and status == 1:
            tally.count('handler %d' % own['handler'])
    tally.add(ok, {'case': label, 'diff': diff[:8], 'status': status, 'found': found, 'eax': r['eax'] & 0xff,
                   'seed': [seed, client_seed]})


def family(machine, registry, lib, g, cases, call):
    tally = v.Tally('set_action' if call == 'set' else 'tick')
    handlers = SET_HANDLERS if call == 'set' else TICK_HANDLERS
    for n in range(cases):
        compare(machine, registry, lib, random_case(g, call, handlers), call, tally, n)
    return tally


def read_rows(lang_dir):
    rows = []
    for line in (Path(lang_dir) / 'mapanim.tsv').read_text().splitlines():
        if not line or line[0] == '#':
            continue
        c = line.split('\t')
        rows.append({'world': int(c[0]), 'type': int(c[1]), 'action': int(c[2]), 'speed': v.f32(float(c[3])),
                     'handler': int(c[4]), 'param': int(c[5]),
                     'extra': [] if c[6] == '-' else [int(x) for x in c[6].split(',')]})
    return rows


def live_rows(machine, registry, lib, g, lang_dir):
    """Every live row through SetAction and the tick, in its world's table (handlers 4, 6, 8: SetAction only)."""
    tally = v.Tally('live_rows')
    rows = read_rows(lang_dir)
    for row in rows:
        world = [dict(r) for r in rows if r['world'] == row['world']]
        actions = [r['action'] for r in world if r['type'] == row['type']]
        targets = [r['extra'][-1] for r in world if r['type'] == row['type'] and r['extra'] and
                   r['handler'] in (1, 2, 3, 5, 7)]
        count = min(max(actions + targets + [0]) + 1, 60)
        records = [(g.choice([10, 20, 32, 40]), g.choice([0, 1])) for _ in range(count)]
        keys = records[row['action']][0]
        for k, frame in enumerate([0.0, keys - row['speed'], keys - row['speed'] - 0.01, v.f32(keys / 2.0)]):
            for call in ('set', 'tick') if row['handler'] not in (4, 6, 8) else ('set',):
                obj = case_object(g, row['type'], row['action'] if call == 'tick' else g.choice([0, row['action']]),
                                  v.f32(frame))
                ox, oy = struct.unpack_from('<2f', obj, 0x158)
                d = [row['param'] - 1.0, row['param'] + 1.0][k % 2]
                case = {'type': row['type'], 'count': count, 'records': records, 'action': row['action'],
                        'entries': world, 'has_model': True, 'object': bytes(obj),
                        'hero': [v.f32(ox + d), v.f32(oy)], 'seed': g.getrandbits(32)}
                compare(machine, registry, lib, case, call, tally, '%d/%d/%d %s' % (row['world'], row['type'],
                                                                                  row['action'], call))
    tally.count('rows', len(rows))
    return tally


# ---------------------------------------------------------------- mutants

A = 'action_registry.c'
MUTATIONS = [
    ('key factor', A, 'return 1000u * (uint32_t)action', 'return 100u * (uint32_t)action'),
    ('set speed', A, '    case 0: case 1: case 4: case 5: case 6: case 7:\n        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);',
     '    case 0: case 1: case 4: case 5: case 6:\n        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);'),
    ('set loops', A, '        mu_obj_set_i32(o, OBJ_LOOPS, 0);\n', ''),
    ('set limit span', A, 'r % (e->extra[1] - e->extra[0])', 'r % (e->extra[1] - e->extra[0] + 1)'),
    ('set limit base', A, 'e->extra[0] + r %', 'r %'),
    ('set 8 size', A, 'e->extra_count > 6', 'e->extra_count >= 6'),
    ('set 8 scale', A, '(float)e->extra[6] * 0.00999999978f', '(float)e->extra[6] * 0.01001f'),
    ('set 8 speed', A, '    case 8:   /* 0x00ce15de: the alpha rate from extra[6] when the vector has more than six */\n',
     '    case 8:   /* 0x00ce15de: the alpha rate from extra[6] when the vector has more than six */\n'
     '        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);\n'),
    ('count signed', A, '!(action < (int32_t)(int16_t)count)', '!(action < count) || action < 0'),
    ('switch prior', A, 'mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, mu_obj_u16(o, MU_OBJF_ACTION));\n', ''),
    ('switch frame', A, '        mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);\n    }', '    }'),
    ('switch prior frame', A, 'mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, mu_obj_f32(o, MU_OBJF_FRAME));\n', ''),
    ('end lock', A, 'limit = limit - 1.0f;', 'limit = limit - 0.5f;'),
    ('end compare', A, 'return mu_obj_f32(o, MU_OBJF_FRAME) >= limit - e->speed;',
     'return mu_obj_f32(o, MU_OBJF_FRAME) > limit - e->speed;'),
    ('end speed', A, 'return mu_obj_f32(o, MU_OBJF_FRAME) >= limit - e->speed;',
     'return mu_obj_f32(o, MU_OBJF_FRAME) >= limit + 0.0f * e->speed;'),
    ('tick 2 compare', A, '    case 2:   /* 0x00ce1737: after +0x34 loops */\n        if (at_end(o, e, r, 0)) {\n            if (mu_obj_i32(o, OBJ_LOOPS) >= mu_obj_i32(o, OBJ_LIMIT)) {',
     '    case 2:   /* 0x00ce1737: after +0x34 loops */\n        if (at_end(o, e, r, 0)) {\n            if (mu_obj_i32(o, OBJ_LOOPS) > mu_obj_i32(o, OBJ_LIMIT)) {'),
    ('tick 2 count', A, '                mu_action_set(o, back(e), in);\n            }\n            mu_obj_set_i32(o, OBJ_LOOPS, mu_obj_i32(o, OBJ_LOOPS) + 1);\n        }\n        return MU_ANIM_APPLIED;\n    case 3:',
     '                mu_action_set(o, back(e), in);\n            }\n        }\n        return MU_ANIM_APPLIED;\n    case 3:'),
    ('tick 3 index', A, '% (uint32_t)(e->extra_count - 2) + 2]', '% (uint32_t)(e->extra_count - 1) + 1]'),
    ('tick 1 target', A, '                return MU_ANIM_UNSUPPORTED;\n            mu_action_set(o, back(e), in);\n        }\n        return MU_ANIM_APPLIED;\n    case 2:',
     '                return MU_ANIM_UNSUPPORTED;\n            mu_action_set(o, e->extra[0], in);\n        }\n        return MU_ANIM_APPLIED;\n    case 2:'),
    ('tick 5 near', A, '                if (p > d)\n', '                if (p >= d)\n'),
    ('tick 5 far', A, 'if (hero_distance(o, in) > (float)e->param)', 'if (hero_distance(o, in) < (float)e->param)'),
    ('tick 7 latch', A, '                if (mu_obj_i32(o, OBJ_LIMIT) == 0)\n', ''),
    ('tick 7 reset', A, '            } else if (d > p) {\n                mu_obj_set_i32(o, OBJ_LIMIT, 0);', '            } else {\n                mu_obj_set_i32(o, OBJ_LIMIT, 0);'),
    ('tick 7 lock', A, 'at_end(o, e, r, 1)', 'at_end(o, e, r, 0)'),
    ('tick 7 count', A, '                mu_obj_set_i32(o, OBJ_LIMIT, mu_obj_i32(o, OBJ_LIMIT) + 1);\n', ''),
    ('distance axis', A, 'in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4)', 'in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION)'),
    ('distance sum', A, 'const float sum = dx * dx + dy * dy;', 'const float sum = dx * dx + dy * dy + 1.0f;'),
    ('tick model', A, '    if (!in->model(in->context, type, action, &count, &keys, &lock))\n        return MU_ANIM_NONE;\n    *found = 1;',
     '    in->model(in->context, type, action, &count, &keys, &lock);\n    *found = 1;'),
    ('tick 5 case 3', A, '        case 1: case 3:\n', '        case 1:\n'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=4000)
    p.add_argument('--only')
    p.add_argument('--lang-dir', help='local lang directory with mapanim.tsv (live_rows)')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    registry = Registry(machine)
    families = ['set_action', 'tick'] + (['live_rows'] if a.lang_dir else [])
    names = [n for n in families if not a.only or n in a.only.split(',')]
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(s), 'end': hex(e), 'sha256': hashlib.sha256(
                  text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()} for k, (s, e) in BODIES.items()}}
    if a.lang_dir:
        report['mapanim_sha256'] = hashlib.sha256((Path(a.lang_dir) / 'mapanim.tsv').read_bytes()).hexdigest()
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random('worlds-after5-' + name)   # noqa: E731

    def run_all(library, only=None):
        out = {}
        for name in only or names:
            if name == 'live_rows':
                out[name] = live_rows(machine, registry, library, seed(name), a.lang_dir)
            else:
                out[name] = family(machine, registry, library, seed(name), a.cases,
                                   'set' if name == 'set_action' else 'tick')
        return out
    for name, tally in run_all(lib).items():
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:3000], flush=True)
    if a.mutations:
        for label, file, old, new in MUTATIONS:
            with tempfile.TemporaryDirectory(prefix='worlds-after5-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects' / file
                s = path.read_text()
                assert s.count(old) == 1, (label, old)
                path.write_text(s.replace(old, new, 1))
                tallies = run_all(build(root), [n for n in names if n != 'live_rows'])
                cases = sum(t.cases for t in tallies.values())
                detected = sum(t.cases - t.equal - t.stopped for t in tallies.values())
                stopped = sum(t.stopped for t in tallies.values())
                item = {'name': label, 'cases': cases, 'detected': detected, 'stopped': stopped}
                report['mutants'].append(item)
                print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 and not x['stopped'] for x in report['mutants'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
