#!/usr/bin/env python3
"""RENDER-EFFECTS-008: the map-object effect table's attach routine 0x0183067e.

The client routine runs in Unicorn over the pinned text (actor_machine) with the table built in memory the way
the client keeps it: the std::map at 0x06fbb7b0 (world -> record, record +0x3c the type map), the type map's
vectors of 0x54-byte entries (std::string paths inline and on the heap, action vectors), the world word
[0x01cf15fc], the sector table 0x0bdb61f0 (+4 the first object) and objects linked through +0x354. The std::map
lookups (0x010fa24c, 0x010fa28a, 0x010f4ae9, 0x01849a27, 0x018499fd, 0x010f8305, 0x018499b3, 0x01849a75,
0x01849998) and the shared-pointer test 0x00a78918 run as client code. Stubs record the engine calls: the list
clear 0x009b0451, the manager getter 0x00aee554, the action-vector copy 0x00a781ef, the factory 0x00a797a0 (every
argument read back from memory; a null effect for the case's invalid paths), the attach 0x0129f9c6, the
shared-pointer release 0x00965b01 and the first update 0x0129f4cb. reconstructed/objects/map_effects.c makes the
same calls through its ops; the two call lists must be equal.

Family `attach`: random tables and objects (absent worlds, empty and negative keys, type words with a high half,
inline and heap paths, empty and filled action vectors, NaN and denormal fields, invalid templates).
Family `live` (with --snapshot and --objects, local captures): the decoded live table over a captured world's
real sector lists; besides the equal call lists, the attach count of every object must equal the captured
object's +0x3d0 list size.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import pins  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'reconstructed/objects'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
START, END = 0x0183067e, 0x018308d6
WORLD_WORD, TABLE, SECTORS = 0x01cf15fc, 0x06fbb7b0, 0x0bdb61f0
HEAP, OBJECTS = 0x20000000, 0x28000000
MANAGER = 0x2f000000
CLEAR, GETTER, COPY, FACTORY, ATTACH, RELEASE, PRIME = (0x009b0451, 0x00aee554, 0x00a781ef, 0x00a797a0,
                                                        0x0129f9c6, 0x00965b01, 0x0129f4cb)
OBJ_SIZE = 0x3d8


# ---------------------------------------------------------------- the C side
class Entry(ctypes.Structure):
    _fields_ = [('path', ctypes.c_char_p), ('position', ctypes.c_uint32 * 3), ('rotation', ctypes.c_uint32 * 3),
                ('scale', ctypes.c_uint32), ('bone', ctypes.c_int32), ('follow', ctypes.c_uint8),
                ('tint', ctypes.c_uint8), ('start_bits', ctypes.c_uint32), ('actions', ctypes.POINTER(ctypes.c_int32)),
                ('action_count', ctypes.c_int32)]


class Type(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('entries', ctypes.POINTER(Entry)), ('count', ctypes.c_int32)]


class World(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('types', ctypes.POINTER(Type)), ('count', ctypes.c_int32)]


class Table(ctypes.Structure):
    _fields_ = [('worlds', ctypes.POINTER(World)), ('count', ctypes.c_int32)]


class ObjWorld(ctypes.Structure):
    _fields_ = [('objects', ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8))), ('count', ctypes.c_int32),
                ('head', ctypes.c_int32 * 256), ('next', ctypes.POINTER(ctypes.c_int32)),
                ('block_visible', ctypes.c_uint8 * 256)]


CLEAR_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
CREATE_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(Entry), ctypes.c_uint16)
ATTACH_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int,
                             ctypes.c_int, ctypes.c_float)
RELEASE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
PRIME_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)


class Ops(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('clear', CLEAR_FN), ('create', CREATE_FN), ('attach', ATTACH_FN),
                ('release', RELEASE_FN), ('prime', PRIME_FN)]


def build_library(folder, source_text=None):
    folder = Path(folder)
    for name in ('map_effects.c', 'map_effects.h', 'object_render.h', 'objects.h'):
        (folder/name).write_text((SOURCE/name).read_text())
    if source_text is not None:
        (folder/'map_effects.c').write_text(source_text)
    out = folder/('libmapeffects.' + SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                    '-ffp-contract=off', '-I', str(folder), str(folder/'map_effects.c'), '-o', str(out)],
                   check=True, capture_output=True)
    lib = ctypes.CDLL(str(out))
    lib.mu_map_effects_attach.argtypes = [ctypes.POINTER(Table), ctypes.c_int32, ctypes.POINTER(ObjWorld),
                                          ctypes.POINTER(Ops)]
    lib.mu_map_effects_attach.restype = None
    return lib


def f32bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def run_c(lib, case):
    keep, calls, handles = [], [], [0]
    worlds = (World * max(1, len(case['table'])))()
    for wi, (world, types) in enumerate(case['table']):
        ts = (Type * max(1, len(types)))()
        for ti, (kind, entries) in enumerate(types):
            es = (Entry * max(1, len(entries)))()
            for ei, e in enumerate(entries):
                acts = (ctypes.c_int32 * max(1, len(e['actions'])))(*e['actions'])
                path = ctypes.c_char_p(e['path'])
                keep += [acts, path]
                es[ei].path = path.value
                es[ei].position[:] = e['position']
                es[ei].rotation[:] = e['rotation']
                es[ei].scale, es[ei].bone, es[ei].follow, es[ei].tint = e['scale'], e['bone'], e['follow'], e['tint']
                es[ei].start_bits, es[ei].actions, es[ei].action_count = e['start'], acts, len(e['actions'])
            keep.append(es)
            ts[ti].type, ts[ti].entries, ts[ti].count = kind, es, len(entries)
        keep.append(ts)
        worlds[wi].world, worlds[wi].types, worlds[wi].count = world, ts, len(types)
    table = Table(worlds, len(case['table']))
    objects = case['objects']
    images = [(ctypes.c_uint8 * OBJ_SIZE)() for _ in objects]
    for img, o in zip(images, objects):
        struct.pack_into('<i', img, 0x5c, o['key'])
    w = ObjWorld()
    pointers = (ctypes.POINTER(ctypes.c_uint8) * max(1, len(objects)))(
        *[ctypes.cast(img, ctypes.POINTER(ctypes.c_uint8)) for img in images])
    nxt = (ctypes.c_int32 * max(1, len(objects)))(*([-1] * max(1, len(objects))))
    w.objects, w.count, w.next = pointers, len(objects), nxt
    for s in range(256):
        w.head[s] = -1
    last = {}
    for k, o in enumerate(objects):   # CreateObject appends to the sector list
        if o['sector'] in last:
            nxt[last[o['sector']]] = k
        else:
            w.head[o['sector']] = k
        last[o['sector']] = k
    invalid = case['invalid']

    def create(ctx, obj, entry, word):
        e = entry.contents
        acts = [e.actions[i] for i in range(e.action_count)]
        calls.append(('create', obj, e.path, tuple(e.position), tuple(e.rotation), e.scale, 0, word, e.tint,
                      tuple(acts), e.start_bits))
        if e.path in invalid:
            return -1
        handles[0] += 1
        return handles[0]

    def attach(ctx, obj, handle, bone, follow, timed, lifetime):
        calls.append(('attach', obj, handle, bone & 0xffffffff, follow, timed, f32bits(lifetime)))

    ops = Ops(None, CLEAR_FN(lambda c, k: calls.append(('clear', k))), CREATE_FN(create), ATTACH_FN(attach),
              RELEASE_FN(lambda c, h: calls.append(('release', h))), PRIME_FN(lambda c, k: calls.append(('prime', k))))
    lib.mu_map_effects_attach(ctypes.byref(table), case['world'], ctypes.byref(w), ctypes.byref(ops))
    return calls


# ---------------------------------------------------------------- the client side
class Heap:
    def __init__(self, base, size):
        self.region = am.undefined_region('heap', base, size, 0x33)
        self.top = base + 0x10

    def alloc(self, size, payload=None):
        address = self.top
        self.top = (self.top + size + 0xf) & ~0xf
        if payload is not None:
            self.region.define(address, payload)
        return address

    def define(self, address, payload):
        self.region.define(address, payload)


def build_tree(heap, items, value_bytes):
    """MSVC std::map: head (_Isnil 1) and a balanced tree of nodes (left +0, parent +4, right +8, colour +0xc,
    _Isnil +0xd, key +0x10, value +0x14). Returns (head, nodes by key)."""
    head = heap.alloc(0x14 + value_bytes)
    nodes = {key: heap.alloc(0x14 + value_bytes) for key, _ in items}
    keys = sorted(nodes)

    def link(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        node = nodes[keys[mid]]
        left, right = link(lo, mid, node), link(mid + 1, hi, node)
        heap.define(node, struct.pack('<IIIBB', left, parent, right, 1, 0) + b'\0\0' + struct.pack('<i', keys[mid]))
        return node
    root = link(0, len(keys), head)
    heap.define(head, struct.pack('<IIIBB', nodes[keys[0]] if keys else head, root,
                                  nodes[keys[-1]] if keys else head, 1, 1) + b'\0\0')
    return head, nodes


def build_string(heap, text):
    if len(text) < 16:
        return text.ljust(16, b'\0') + struct.pack('<II', len(text), 15)
    buffer = heap.alloc(len(text) + 1, text + b'\0')
    return struct.pack('<I', buffer) + bytes(12) + struct.pack('<II', len(text), len(text) | 0xf)


def build_entry(heap, address, e):
    heap.define(address + 4, build_string(heap, e['path']))
    heap.define(address + 0x1c, struct.pack('<7Ii', *e['position'], *e['rotation'], e['scale'], e['bone']))
    heap.define(address + 0x3c, bytes([e['follow'], e['tint']]))
    heap.define(address + 0x44, struct.pack('<I', e['start']))
    if e['actions']:
        buffer = heap.alloc(4 * len(e['actions']) + 8, struct.pack(f"<{len(e['actions'])}i", *e['actions']))
        heap.define(address + 0x48, struct.pack('<III', buffer, buffer + 4 * len(e['actions']),
                                                buffer + 4 * len(e['actions']) + 8))
    else:
        heap.define(address + 0x48, bytes(12))


def client_regions(case):
    worlds = case['table']
    heap = Heap(HEAP, 0x10000 + 0x200 * sum(1 + len(e) for _, types in worlds for _, e in types))
    head, nodes = build_tree(heap, worlds, 0x44)
    for world, types in worlds:
        node = nodes[world]
        inner_head, inner_nodes = build_tree(heap, types, 0xc)
        heap.define(node + 0x14 + 0x3c, struct.pack('<II', inner_head, len(types)))
        for kind, entries in types:   # one vector buffer per type, entries in place (0x01849998)
            block = heap.alloc(0x54 * len(entries)) if entries else 0
            end = block + 0x54 * len(entries)
            for k, e in enumerate(entries):
                build_entry(heap, block + 0x54 * k, e)
            heap.define(inner_nodes[kind] + 0x14, struct.pack('<III', block, end, end))
    table = am.defined_region('table', TABLE, struct.pack('<II', head, len(worlds)))
    world = am.defined_region('world', WORLD_WORD, struct.pack('<i', case['world']))
    objects = case['objects']
    objs = am.undefined_region('objects', OBJECTS, max(1, len(objects)) * OBJ_SIZE, 0x44)
    sectors = am.undefined_region('sectors', SECTORS, 256 * 16, 0x55)
    address = [OBJECTS + k * OBJ_SIZE for k in range(len(objects))]
    last = {}
    for k, o in enumerate(objects):
        objs.define(address[k] + 0x5c, struct.pack('<i', o['key']))
        objs.define(address[k] + 0x354, struct.pack('<I', 0))
        if o['sector'] in last:
            objs.define(address[last[o['sector']]] + 0x354, struct.pack('<I', address[k]))
        else:
            sectors.define(SECTORS + 16 * o['sector'] + 4, struct.pack('<I', address[k]))
        last[o['sector']] = k
    for s in range(256):
        if s not in last:
            sectors.define(SECTORS + 16 * s + 4, struct.pack('<I', 0))
    manager = am.defined_region('manager', MANAGER, bytes(16))
    return [heap.region, table, world, objs, sectors, manager], address


def run_client(machine, case):
    regions, address = client_regions(case)
    index = {a: k for k, a in enumerate(address)}
    calls, handles, effects = [], [0], {}
    invalid = case['invalid']
    ecx = lambda m: m.uc.reg_read(m.x86.UC_X86_REG_ECX)  # noqa: E731

    def string(m, at):
        size, cap = struct.unpack('<II', bytes(m.uc.mem_read(at + 0x10, 8)))
        return bytes(m.uc.mem_read(at if cap < 16 else m.read32(at), size))

    def factory(m):
        out = m.argument(0)
        path = string(m, m.argument(1))
        pos = struct.unpack('<3I', bytes(m.uc.mem_read(m.argument(2), 12)))
        rot = struct.unpack('<3I', bytes(m.uc.mem_read(m.argument(3), 12)))
        begin, end = m.argument(8), m.argument(9)
        acts = struct.unpack(f'<{(end - begin) // 4}i', bytes(m.uc.mem_read(begin, end - begin))) if end > begin else ()
        word = struct.unpack('<H', bytes(m.uc.mem_read(m.argument(6), 2)))[0]
        calls.append(('create', index[ecx_object[0]], path, pos, rot, m.argument(4), m.argument(5), word,
                      m.argument(7), tuple(acts), m.argument(11)))
        if path in invalid:
            effect = 0
        else:
            handles[0] += 1
            effect = 0x2e000000 + 0x100 * handles[0]
            effects[effect] = handles[0]
        m.uc.mem_write(out, struct.pack('<II', effect, effect and effect + 0x40))
        return out, 0x30

    ecx_object = [0]

    def clear(m):
        ecx_object[0] = ecx(m)
        calls.append(('clear', index[ecx(m)]))
        return 0

    def copy(m):   # thiscall: the by-value vector argument, a shallow copy of the entry's +0x48
        m.uc.mem_write(ecx(m), bytes(m.uc.mem_read(m.argument(0), 12)))
        return ecx(m), 4

    def attach(m):
        effect = m.read32(m.argument(0))
        calls.append(('attach', index[ecx(m)], effects.get(effect, -2), m.argument(1), m.argument(2),
                      m.argument(3), m.argument(4)))
        return 0, 0x14

    def release(m):
        effect = m.read32(ecx(m))
        calls.append(('release', effects.get(effect, -1) if effect else -1))
        return 0

    def prime(m):
        calls.append(('prime', index[ecx(m)]))
        return 0

    stubs = {CLEAR: clear, GETTER: lambda m: MANAGER, COPY: copy, FACTORY: factory, ATTACH: attach,
             RELEASE: release, PRIME: prime}
    result = machine.execute(START, [], regions, stubs)
    return calls, result


# ---------------------------------------------------------------- cases
SPECIAL = [0, 0x80000000, 0x7fc00000, 0xffc00001, 0x00220000, 0x3f800000, 0xbf800000, 0x7f800000, 0x00000001,
           0x42480000]


def rbits(rng):
    return rng.choice(SPECIAL) if rng.random() < 0.3 else f32bits(rng.uniform(-500.0, 500.0))


def random_entry(rng):
    n = rng.choice([4, 9, 15, 16, 22, 30])
    path = b'Data\\Effect\\' + bytes(rng.choice(b'abcdefgh0123-') for _ in range(n)) + b'.ein'
    if rng.random() < 0.3:
        path = path[:rng.choice([0, 3, 15])]   # inline strings of up to 15 characters
    return {'path': path, 'position': [rbits(rng) for _ in range(3)], 'rotation': [rbits(rng) for _ in range(3)],
            'scale': rbits(rng), 'bone': rng.choice([0, 1, 7, 29, 44, -1, rng.randrange(-5, 60)]),
            'follow': rng.choice([0, 1, 1, 2, 0xff]), 'tint': rng.choice([0, 0, 1, 0x80]),
            'start': rbits(rng), 'actions': [rng.randrange(-3, 70000) for _ in range(rng.choice([0, 0, 1, 2, 4]))]}


def random_case(rng):
    world = rng.choice([116, 118, 136, 63, 0, -1, rng.randrange(0, 150)])
    keys = set(rng.sample(range(-4, 200), rng.choice([0, 1, 3, 6])))
    if rng.random() < 0.8:
        keys.add(world)
    paths = []
    table = []
    for w in sorted(keys):
        kinds = sorted(set(rng.choice([-0x10000, -2, 0, 62, 63, 67, 0x10043, 160, 299, rng.randrange(-5, 400)])
                           for _ in range(rng.choice([0, 1, 4, 9]))))
        types = []
        for t in kinds:
            entries = [random_entry(rng) for _ in range(rng.choice([0, 1, 1, 2, 3, 5]))]
            paths += [e['path'] for e in entries]
            types.append((t, entries))
        table.append((w, types))
    used = [t for w, types in table if w == world for t, _ in types] or [0]
    objects = []
    hot = rng.sample(range(256), 4)
    for _ in range(rng.choice([0, 1, 5, 20, 45])):
        key = rng.choice(used) if rng.random() < 0.6 else rng.randrange(-3, 320)
        if rng.random() < 0.15:
            key = (key & 0xffff) | (rng.choice([1, 0xffff, 0x7fff]) << 16)
            key = key - (1 << 32) if key >= 1 << 31 else key
        objects.append({'key': key, 'sector': rng.choice(hot) if rng.random() < 0.7 else rng.randrange(256)})
    invalid = set(rng.sample(paths, len(paths) // 3)) if paths and rng.random() < 0.5 else set()
    return {'world': world, 'table': table, 'objects': objects, 'invalid': invalid}


def coverage_of(case, counts):
    found = {t for w, types in case['table'] if w == case['world'] for t, _ in types}
    present = any(w == case['world'] for w, _ in case['table'])
    counts['world_absent'] += not present
    counts['objects'] += len(case['objects'])
    counts['objects_found'] += present and sum(o['key'] in found for o in case['objects'])
    counts['high_half_keys'] += sum(o['key'] >> 16 not in (0, -1) for o in case['objects'])
    counts['negative_table_keys'] += sum(t < 0 for w, types in case['table'] for t, _ in types)
    counts['empty_vectors'] += sum(not e for w, types in case['table'] for t, e in types)
    counts['invalid_paths'] += len(case['invalid'])


def compare(lib, machine, cases, seed=0x8008):
    rng = random.Random(seed)
    out = {'cases': 0, 'equal': 0, 'calls': 0, 'attaches': 0, 'first_failures': [],
           'coverage': {k: 0 for k in ('world_absent', 'objects', 'objects_found', 'high_half_keys',
                                       'negative_table_keys', 'empty_vectors', 'invalid_paths')}}
    for _ in range(cases):
        case = random_case(rng)
        coverage_of(case, out['coverage'])
        expected, result = run_client(machine, case)
        got = run_c(lib, case)
        ok = result['ok']
        out['cases'] += 1
        out['calls'] += len(expected)
        out['attaches'] += sum(c[0] == 'attach' for c in expected)
        if ok and expected == got:
            out['equal'] += 1
        elif len(out['first_failures']) < 2:
            first = next((k for k, (a, b) in enumerate(zip(expected, got)) if a != b), min(len(expected), len(got)))
            out['first_failures'].append({'checks': result.get('checks'), 'stopped': str(result.get('stopped')),
                                          'at': first, 'client': [repr(c) for c in expected[first:first + 2]],
                                          'native': [repr(c) for c in got[first:first + 2]]})
    return out


# ---------------------------------------------------------------- live family (local captures only)
def live_case(snapshot, objects_path):
    import live_effect_table_to_plain as plain
    from live_lang_to_plain import Snapshot
    rows = plain.read_table(Snapshot.load(snapshot))
    table = {}
    for world, kind, entries in rows:
        table.setdefault(world, []).append((kind, [
            {'path': e['path'], 'position': [f32bits(v) for v in e['position']],
             'rotation': [f32bits(v) for v in e['rotation']], 'scale': f32bits(e['scale']), 'bone': e['bone'],
             'follow': e['follow'], 'tint': e['tint'], 'start': e['start'], 'actions': e['actions']}
            for e in entries]))
    raw = Path(objects_path).read_bytes()
    world = struct.unpack_from('<i', raw, 8)[0]
    objects, sizes, o = [], [], 24
    while o + 8 + OBJ_SIZE <= len(raw):
        sector = struct.unpack_from('<I', raw, o + 4)[0]
        image = raw[o + 8:o + 8 + OBJ_SIZE]
        objects.append({'key': struct.unpack_from('<i', image, 0x5c)[0], 'sector': sector})
        sizes.append(struct.unpack_from('<I', image, 0x3d4)[0])
        o += 8 + OBJ_SIZE
    return {'world': world, 'table': sorted(table.items()), 'objects': objects, 'invalid': set()}, sizes


def compare_live(lib, machine, snapshot, objects_path):
    case, sizes = live_case(snapshot, objects_path)
    expected, result = run_client(machine, case)
    got = run_c(lib, case)
    attached = [0] * len(case['objects'])
    for c in expected:
        if c[0] == 'attach':
            attached[c[1]] += 1
    return {'cases': 1, 'equal': int(result['ok'] and expected == got), 'world': case['world'],
            'objects': len(case['objects']), 'calls': len(expected), 'attaches': sum(attached),
            'objects_matching_live_list_size': sum(a == s for a, s in zip(attached, sizes)),
            'objects_with_live_effects': sum(1 for s in sizes if s)}


# ---------------------------------------------------------------- mutants
MUTANTS = [
    ('sector-order', 'w->head[i * 16 + j]', 'w->head[j * 16 + i]'),
    ('no-clear', 'ops->clear(ops->context, k);', '(void)0;'),
    ('type-short', 'const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);',
     'const int32_t type = (int16_t)mu_obj_i32(o, MU_OBJF_TYPE);'),
    ('prime-unfound', 'if (!found)\n                    continue;',
     'if (!found) {\n                    ops->prime(ops->context, k);\n'
     '                    continue;\n                }'),
    ('attach-invalid', 'if (handle >= 0)', 'if (handle >= -1)'),
    ('follow-forced', 'entry->bone, entry->follow, 0, 0.0f', 'entry->bone, 1, 0, 0.0f'),
    ('timed', 'entry->follow, 0, 0.0f', 'entry->follow, 1, 0.0f'),
    ('lifetime', ', 0, 0.0f);', ', 0, 1.0f);'),
    ('release-valid-only', 'ops->release(ops->context, handle);',
     'if (handle >= 0)\n                        ops->release(ops->context, handle);'),
    ('entry-order', 'const mu_map_effect_entry *entry = &found->entries[e];',
     'const mu_map_effect_entry *entry = &found->entries[found->count - 1 - e];'),
    ('type-word', '(uint16_t)type);', '(uint16_t)(type >> 1));'),
    ('type-unsigned', 'if (world->types[mid].type < type)', 'if ((uint32_t)world->types[mid].type < (uint32_t)type)'),
    ('world-absent-clears', 'if (!types)\n        return;',
     'if (!types) {\n        for (int32_t k = 0; k < w->count; ++k)\n            ops->clear(ops->context, k);\n'
     '        return;\n    }'),
    ('prime-before', 'ops->prime(ops->context, k);\n            }', '}'),
]


def mutants(machine, cases):
    original = (SOURCE/'map_effects.c').read_text()
    caught = {}
    with tempfile.TemporaryDirectory(prefix='map-effects-') as tmp:
        for name, old, new in MUTANTS:
            if original.count(old) != 1:
                raise AssertionError(('mutant anchor', name, original.count(old)))
            text = original.replace(old, new)
            if name == 'prime-before':
                text = text.replace('if (!found)\n                    continue;',
                                    'if (!found)\n                    continue;\n'
                                    '                ops->prime(ops->context, k);')
            folder = Path(tmp)/name
            folder.mkdir()
            r = compare(build_library(folder, text), machine, cases)
            caught[name] = {'cases': r['cases'], 'caught': r['cases'] - r['equal']}
    return caught


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cases', type=int, default=400)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--snapshot', type=Path, help='local langread snapshot with graph:0x06fbb7b0 (live family)')
    p.add_argument('--objects', type=Path, action='append', default=[], help='local objread capture(s)')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = am.ActorMachine(text, data)
    report = {'text_sha256': pins.TEXT.sha256, 'body_sha256': hashlib.sha256(text[START - am.TEXT_BASE:
                                                                                END - am.TEXT_BASE]).hexdigest()[:16],
              'families': {}, 'mutants': {}}
    with tempfile.TemporaryDirectory(prefix='map-effects-') as tmp:
        lib = build_library(tmp)
        r = compare(lib, machine, a.cases)
        report['families']['attach'] = dict(r, mismatches=r['cases'] - r['equal'])
        if a.snapshot and a.objects:
            for path in a.objects:
                r = compare_live(lib, machine, a.snapshot, path)
                report['families'].setdefault('live', {'cases': 0, 'equal': 0, 'worlds': []})
                f = report['families']['live']
                f['cases'] += 1
                f['equal'] += r['equal']
                f['worlds'].append(r)
            f['mismatches'] = f['cases'] - f['equal']
    if a.mutations:
        report['mutants'] = mutants(machine, a.cases)
    report['instruction_cases'] = sum(f['cases'] for f in report['families'].values())
    report['all_equal'] = all(f['mismatches'] == 0 for f in report['families'].values())
    report['all_mutants_caught'] = all(m['caught'] > 0 for m in report['mutants'].values())
    out = json.dumps(report, indent=2) + '\n'
    if a.output:
        a.output.write_text(out)
    print(out)
    raise SystemExit(not (report['all_equal'] and (not a.mutations or report['all_mutants_caught'])))


if __name__ == '__main__':
    main()
