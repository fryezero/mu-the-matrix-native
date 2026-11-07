#!/usr/bin/env python3
"""RENDER-EFFECTS-018 original-instruction families and compiled production mutants
(docs/research/client-render-effects-018.md).

The Muun effect table's consumers, reconstructed/objects/muun_effects.c, against the client run in Unicorn:

* muun_attach: 0x0114203d(object, code) with ecx = MuunEffectInfo 0x06fbb46c, the std::multimap at +0x38 built in
  memory (MSVC nodes, equal keys in insertion order, inline and heap path strings). equal_range 0x00aed702, the
  iterator helpers (0x00aecc42, 0x00aecc71, 0x00aecc9a), the empty action vector 0x0095e433 and the shared-pointer
  test 0x00a78918 run as client code; the manager getter 0x00aee554, the factory 0x00a797a0 (every argument read
  back), the attach 0x0129f9c6 and the release 0x00965b01 are recording stubs. Synthetic tables: random codes with
  duplicates, negative codes, absent codes, empty tables, invalid templates.
* muun_records (private, opt-in: --lang-dir naming a directory with muuneffects.tsv): the decoded 16-record table (never
  written out), every code it holds and absent neighbours, valid and invalid templates.
* muun_gate: the slot methods 0x009af699 (the owner key 0x009a1b49 runs as client code; 0x0114203d is a recording
  stub) and 0x009af6f6 (0x009b0451 a recording stub) over slots with and without owner, OBJECT and record, the
  byte +0x10 and matching and other keys.
* muun_update: 0x0129f671(dt) on a Muun-like OBJECT whose +0x3d0 std::list (MSVC nodes) holds records with bones,
  follow flags, timed lifetimes; the list helpers, erase 0x012a1417, the bone matrix 0x0129fd4f, the bone position
  0x012a0030, the world matrix 0x0129faee, the matrix helpers (0x00cef956, 0x00cf2679, 0x00cf0db8, 0x00cfccae,
  0x00a72313) and the sector predicate 0x012a0d29 run as client code with the OBJECT's own bone transforms (+0x318)
  and the shared pose buffer 0x06fce398; the model getter, sin/cos, the effect's scale setter 0x012a0d5c, the node
  update 0x00a75708 and operator delete are stubs. Compared: every scale and node update (dt, the 16 matrix words,
  the OBJECT), the records left in the list and their lifetimes.

Uruk Mountain's weather-driven effect:

* uruk_reader: Uruk's RenderObjectVisual 0x00e6f3d5 for types 108 and 109 against reconstructed/objects/uruk.c
  over every value the reader distinguishes in [0x01cf15ec]: the client's -1 default, 0, 1, 2, 36 (the other
  server value) and the int32 extremes; all OBJECT bytes, the RNG and the ordered calls.
* uruk_fx_create / uruk_fx_move: CreateEffect 0x013c0eaa / MoveEffect 0x0142fd09 for 0x806e/12
  (reconstructed/combat/uruk_fx.inc) through validate_render_effects7's families.
* uruk_pt_create / _move / _render: its particles 0x8084/1, 0x806e/5 (reconstructed/particles/uruk_flames.inc)
  and 0x8085/1 (RENDER-EFFECTS-010's pet_kinds.inc, compared here in this context) through validate_particles'
  families.

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import pins  # noqa: E402
import validate_object_render as v  # noqa: E402
import validate_particles as pt  # noqa: E402
import validate_render_effects11 as r11  # noqa: E402
import validate_skill_fx as fx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
f32 = fx.f32

ATTACH_MUUN, SLOT_ATTACH, SLOT_CLEAR, UPDATE = 0x0114203d, 0x009af699, 0x009af6f6, 0x0129f671
INFO, TABLE_OFFSET = 0x06fbb46c, 0x38
GETTER, FACTORY, ATTACH, RELEASE, CLEAR = 0x00aee554, 0x00a797a0, 0x0129f9c6, 0x00965b01, 0x009b0451
NODE_UPDATE, SET_SCALE, MODELS, GET_MODEL = 0x00a75708, 0x012a0d5c, 0x00966cc4, 0x00eaa8cf
SINE, COSINE = 0x009681bd, 0x009fa223
SHARED_POSE, SHARED_BONES = 0x06fce398, 64
HEAP, OBJECTS, MANAGER, SLOT, OWNER, RECORD = 0x20000000, 0x28000000, 0x2f000000, 0x2f100000, 0x2f200000, 0x2f300000
OBJ, BONES, MODEL, FAKE, EFFECTS = 0x30000000, 0x30100000, 0x30200000, 0x30300000, 0x30400000
OBJ_SIZE = 0x3d8

BODIES = {'attach_muun': (0x0114203d, 0x01142181), 'slot_attach': (0x009af699, 0x009af6f6),
          'slot_clear': (0x009af6f6, 0x009af71f), 'owner_key': (0x009a1b49, 0x009a1b5b),
          'update': (0x0129f671, 0x0129f9c6), 'bone_source': (0x0129f12c, 0x0129f18a),
          'bone_matrix': (0x0129fd4f, 0x012a0030), 'bone_position': (0x012a0030, 0x012a011e),
          'in_sector': (0x012a0d29, 0x012a0d5c), 'place_matrix': (0x00cf2679, 0x00cf28f6),
          'matrix_product': (0x00cf0db8, 0x00cf1691), 'scale_matrix': (0x00cef956, 0x00cefa7a),
          'weather_reset': (0x017ebfd2, 0x017ebffc), 'weather_set': (0x017ebffc, 0x017ec026),
          'uruk_108_109': (0x00e70014, 0x00e702e4), 'create_806e_12': (0x013c4a45, 0x013c4a5a),
          'move_806e_12': (0x01439417, 0x0143964b), 'create_8084_1': (0x015d41ab, 0x015d4350),
          'create_806e_5': (0x015b8f64, 0x015b9109), 'create_8085_1': (0x015d9089, 0x015d922e),
          'move_8084_1': (0x016466a9, 0x01646965), 'move_806e_5': (0x01625e90, 0x01626157),
          'move_8085_1': (0x0164b839, 0x0164bb00)}


# ---------------------------------------------------------------- the C side (muun_effects.c alone)
class Entry(C.Structure):
    _fields_ = [('code', C.c_int32), ('path', C.c_char_p), ('position', C.c_uint32 * 3),
                ('rotation', C.c_uint32 * 3), ('scale', C.c_uint32), ('bone', C.c_int32), ('follow', C.c_uint8)]


class Table(C.Structure):
    _fields_ = [('entries', C.POINTER(Entry)), ('count', C.c_int32)]


CREATE_FN = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_int32, C.POINTER(Entry))
ATTACH_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.c_int32, C.c_int32, C.c_int, C.c_int, C.c_float)
HANDLE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32)


class Ops(C.Structure):
    _fields_ = [('context', C.c_void_p), ('create', CREATE_FN), ('attach', ATTACH_FN), ('release', HANDLE_FN),
                ('clear', HANDLE_FN)]


class Slot(C.Structure):
    _fields_ = [('has_owner', C.c_int32), ('owner_key', C.c_int32), ('object', C.c_int32), ('has_info', C.c_int32),
                ('code', C.c_int32), ('active', C.c_uint8), ('key', C.c_int32)]


class Record(C.Structure):
    _fields_ = [('handle', C.c_int32), ('template_scale', C.c_uint32), ('bone', C.c_int32), ('follow', C.c_uint8),
                ('timed', C.c_uint8), ('lifetime', C.c_uint32)]


class EffectObject(C.Structure):
    _fields_ = [('position', C.c_uint32 * 3), ('angle', C.c_uint32 * 3), ('scale', C.c_uint32),
                ('in_sector', C.c_int32), ('bones', C.c_void_p), ('model_bones', C.c_int32), ('shared', C.c_void_p)]


SCALE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.c_float)
UPDATE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.c_float, C.POINTER(C.c_uint32))


class ObjOps(C.Structure):
    _fields_ = [('context', C.c_void_p), ('expire', HANDLE_FN), ('scale', SCALE_FN), ('update', UPDATE_FN)]


def build_muun(folder, source_text=None):
    folder = Path(folder)
    source = ROOT/'reconstructed/objects'
    for name in ('muun_effects.c', 'muun_effects.h'):
        shutil.copy(source/name, folder/name)
    if source_text is not None:
        (folder/'muun_effects.c').write_text(source_text)
    out = folder/('libmuuneffects.' + SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                    '-ffp-contract=off', '-fno-fast-math', '-I', str(folder), str(folder/'muun_effects.c'), '-lm',
                    '-o', str(out)], check=True, capture_output=True)
    lib = C.CDLL(str(out))
    lib.mu_muun_effects_attach.argtypes = [C.POINTER(Table), C.c_int32, C.c_int32, C.POINTER(Ops)]
    lib.mu_muun_effects_attach.restype = C.c_int32
    lib.mu_muun_slot_attach.argtypes = [C.POINTER(Slot), C.POINTER(Table), C.POINTER(Ops)]
    lib.mu_muun_slot_clear.argtypes = [C.POINTER(Slot), C.POINTER(Ops)]
    lib.mu_object_effects_update.argtypes = [C.POINTER(Record), C.c_int32, C.POINTER(EffectObject), C.c_float,
                                             C.POINTER(ObjOps)]
    lib.mu_object_effects_update.restype = C.c_int32
    return lib


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def c_table(entries, keep):
    arr = (Entry * max(1, len(entries)))()
    for k, e in enumerate(entries):
        path = C.c_char_p(e['path'])
        keep.append(path)
        arr[k].code, arr[k].path = e['code'], path.value
        arr[k].position[:], arr[k].rotation[:] = e['position'], e['rotation']
        arr[k].scale, arr[k].bone, arr[k].follow = e['scale'], e['bone'], e['follow']
    keep.append(arr)
    return Table(arr, len(entries))


def muun_ops(calls, invalid, keep, code_events=False):
    handles = [-1]

    def create(ctx, obj, entry):
        e = entry.contents
        if code_events:
            calls.append(('consumer', obj, e.code))
            return -1
        calls.append(('create', obj, e.path, tuple(e.position), tuple(e.rotation), e.scale, 0, 0, 0, (), 0))
        if e.path in invalid:
            return -1
        handles[0] += 1
        return handles[0]

    def attach(ctx, obj, handle, bone, follow, timed, lifetime):
        calls.append(('attach', obj, handle, bone & 0xffffffff, follow, timed, bits(lifetime)))

    def release(ctx, handle):
        if not code_events:
            calls.append(('release', handle))

    def clear(ctx, obj):
        calls.append(('clear', obj))
    fns = [CREATE_FN(create), ATTACH_FN(attach), HANDLE_FN(release), HANDLE_FN(clear)]
    keep.extend(fns)
    return Ops(None, *fns)


def run_c_attach(lib, case):
    keep, calls = [], []
    table = c_table(case['entries'], keep)
    ops = muun_ops(calls, case['invalid'], keep)
    lib.mu_muun_effects_attach(C.byref(table), case['object'], case['code'], C.byref(ops))
    return calls


# ---------------------------------------------------------------- the client side: the multimap
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


def build_string(heap, text):
    if len(text) < 16:
        return text.ljust(16, b'\0') + struct.pack('<II', len(text), 15)
    buffer = heap.alloc(len(text) + 1, text + b'\0')
    return struct.pack('<I', buffer) + bytes(12) + struct.pack('<II', len(text), len(text) | 0xf)


def build_multimap(heap, entries):
    """MSVC std::multimap<int, entry>: head (_Isnil 1) and a balanced tree over the entries in order (left +0,
    parent +4, right +8, colour +0xc, _Isnil +0xd, value +0x10: key, then the entry from value +4)."""
    head = heap.alloc(0x60)
    nodes = [heap.alloc(0x60) for _ in entries]

    def link(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        node = nodes[mid]
        left, right = link(lo, mid, node), link(mid + 1, hi, node)
        e = entries[mid]
        value = node + 0x10
        heap.define(node, struct.pack('<IIIBB', left, parent, right, 1, 0) + b'\0\0' + struct.pack('<i', e['code']))
        heap.define(value + 4, build_string(heap, e['path']))
        heap.define(value + 0x1c, struct.pack('<7Ii', *e['position'], *e['rotation'], e['scale'], e['bone']))
        heap.define(value + 0x3c, bytes([e['follow']]))
        return node
    root = link(0, len(entries), head)
    heap.define(head, struct.pack('<IIIBB', nodes[0] if nodes else head, root, nodes[-1] if nodes else head, 1, 1) +
                b'\0\0')
    return head


def read_string(m, at):
    size, cap = struct.unpack('<II', bytes(m.uc.mem_read(at + 0x10, 8)))
    return bytes(m.uc.mem_read(at if cap < 16 else m.read32(at), size))


def attach_stubs(calls, invalid, objects):
    handles, effects = [-1], {}
    ecx = lambda m: m.uc.reg_read(m.x86.UC_X86_REG_ECX)  # noqa: E731
    state = {'object': None}

    def factory(m):
        out = m.argument(0)
        path = read_string(m, m.argument(1))
        pos = struct.unpack('<3I', bytes(m.uc.mem_read(m.argument(2), 12)))
        rot = struct.unpack('<3I', bytes(m.uc.mem_read(m.argument(3), 12)))
        begin, end = m.argument(8), m.argument(9)
        acts = struct.unpack(f'<{(end - begin) // 4}i', bytes(m.uc.mem_read(begin, end - begin))) if end > begin else ()
        word = struct.unpack('<H', bytes(m.uc.mem_read(m.argument(6), 2)))[0]
        calls.append(('create', state['object'], path, pos, rot, m.argument(4), m.argument(5), word, m.argument(7),
                      tuple(acts), m.argument(11)))
        if path in invalid:
            effect = 0
        else:
            handles[0] += 1
            effect = 0x2e000000 + 0x100 * (handles[0] + 1)
            effects[effect] = handles[0]
        m.uc.mem_write(out, struct.pack('<II', effect, effect and effect + 0x40))
        return out, 0x30

    def attach(m):
        effect = m.read32(m.argument(0))
        calls.append(('attach', objects.get(ecx(m), -9), effects.get(effect, -2), m.argument(1), m.argument(2),
                      m.argument(3), m.argument(4)))
        return 0, 0x14

    def release(m):
        effect = m.read32(ecx(m))
        calls.append(('release', effects.get(effect, -1) if effect else -1))
        return 0
    return {GETTER: lambda m: MANAGER, FACTORY: factory, ATTACH: attach, RELEASE: release}, state


def run_client_attach(machine, case):
    heap = Heap(HEAP, 0x8000 + 0x100 * len(case['entries']))
    head = build_multimap(heap, case['entries'])
    info = am.undefined_region('info', INFO, 0x40, 0x21)
    info.define(INFO + TABLE_OFFSET, struct.pack('<II', head, len(case['entries'])))
    objs = am.undefined_region('objects', OBJECTS, 0x40 * 8, 0x44)
    manager = am.defined_region('manager', MANAGER, bytes(16))
    calls = []
    objects = {OBJECTS + 0x40 * k: k for k in range(8)}
    stubs, state = attach_stubs(calls, case['invalid'], objects)
    state['object'] = case['object']
    r = machine.execute(ATTACH_MUUN, [OBJECTS + 0x40 * case['object'], case['code']],
                        [heap.region, info, objs, manager], stubs, ecx=INFO, cleanup=8)
    return calls, r


# ---------------------------------------------------------------- cases
SPECIAL = [0, 0x80000000, 0x7fc00000, 0x3f800000, 0xbf800000, 0x00000001, 0x42480000, 0x3fc90fdb, 0x3f7eaee9]


def rbits(rng):
    return rng.choice(SPECIAL) if rng.random() < 0.3 else bits(f32(rng.uniform(-100.0, 100.0)))


def random_path(rng):
    n = rng.choice([3, 9, 15, 16, 22])
    path = b'Data\\Effect\\' + bytes(rng.choice(b'abcdefgh0123_') for _ in range(n)) + b'.ein'
    return path[:rng.choice([0, 3, 15])] if rng.random() < 0.2 else path


def random_entry(rng, code):
    return {'code': code, 'path': random_path(rng), 'position': [rbits(rng) for _ in range(3)],
            'rotation': [rbits(rng) for _ in range(3)], 'scale': rbits(rng),
            'bone': rng.choice([3, 5, 26, 50, 0, -1, rng.randrange(-4, 70)]), 'follow': rng.choice([0, 1, 1, 2, 0xff])}


def random_attach_case(rng):
    codes = sorted(rng.choice([173, 174, 183, 189, 214, 363, -5, 0, -0x80000000, 0x7fffffff, rng.randrange(-300, 600)])
                   for _ in range(rng.choice([0, 1, 3, 8, 16, 24])))
    entries = [random_entry(rng, c) for c in codes]   # sorted() is stable: equal codes keep insertion order
    present = [e['code'] for e in entries]
    code = rng.choice(present) if present and rng.random() < 0.7 else rng.choice(
        [rng.randrange(-300, 600), -0x80000000, 0x7fffffff, 172, 364])
    paths = [e['path'] for e in entries]
    invalid = set(rng.sample(paths, len(paths) // 3)) if paths and rng.random() < 0.4 else set()
    return {'entries': entries, 'code': code, 'object': rng.randrange(8), 'invalid': invalid}


def compare_attach(lib, machine, cases_list, family, report):
    for n, case in enumerate(cases_list):
        expected, r = run_client_attach(machine, case)
        got = run_c_attach(lib, case)
        ok = r['ok'] and expected == got
        detail = None
        if not ok:
            first = next((k for k, (a, b) in enumerate(zip(expected, got)) if a != b), min(len(expected), len(got)))
            detail = {'case': n, 'stopped': str(r.get('stopped')), 'error': str(r.get('error')), 'at': first,
                      'client': [repr(c) for c in expected[first:first + 2]],
                      'native': [repr(c) for c in got[first:first + 2]]}
        report.add(family, ok, detail)
        hits = sum(c[0] == 'create' for c in expected)
        report.cover(family, 'absent code' if not hits else f'{min(hits, 3)}+ entries' if hits >= 3 else
                     f'{hits} entries')
        if any(c[0] == 'attach' for c in expected) and any(c[0] == 'release' and c[1] == -1 for c in expected):
            report.cover(family, 'valid and invalid templates')


def family_attach(lib, machine, rng, cases, report):
    compare_attach(lib, machine, [random_attach_case(rng) for _ in range(cases)], 'muun_attach', report)


def load_records(lang_dir):
    """muuneffects.tsv (RENDER-EFFECTS-008's export): code, path, x, y, z, rx, ry, rz, scale, bone, follow."""
    path = Path(lang_dir)/'muuneffects.tsv'
    rows = []
    for line in path.read_text(encoding='ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        col = line.split('\t')
        rows.append({'code': int(col[0]), 'path': col[1].replace('\\\\', '\\').encode('ascii'),
                     'position': [bits(f32(float(x))) for x in col[2:5]],
                     'rotation': [bits(f32(float(x))) for x in col[5:8]], 'scale': bits(f32(float(col[8]))),
                     'bone': int(col[9]), 'follow': int(col[10])})
    return sorted(rows, key=lambda e: e['code'])


def family_records(lib, machine, records, report):
    codes = sorted({e['code'] for e in records})
    cases = []
    for code in codes + [codes[0] - 1, codes[-1] + 1, 0, -1, 179, 213]:
        for invalid in (set(), {e['path'] for e in records if e['code'] == code}):
            for obj in (0, 5):
                cases.append({'entries': records, 'code': code, 'object': obj, 'invalid': invalid})
    compare_attach(lib, machine, cases, 'muun_records', report)
    attached = set()
    for case in cases:
        if not case['invalid']:
            attached.update(k for k, e in enumerate(records) if e['code'] == case['code'])
    return {'records': len(records), 'codes': len(codes), 'records_attached': len(attached),
            'bones': sorted({e['bone'] for e in records}), 'follow': sorted({e['follow'] for e in records})}


# ---------------------------------------------------------------- muun_gate
def family_gate(lib, machine, rng, cases, report):
    for n in range(cases):
        has_owner, has_object, has_info = (rng.random() < 0.85 for _ in range(3))
        active = rng.choice([1, 1, 1, 0, 2, 0xff])
        owner_key = rng.choice([0, 7, -1, 0x7fffffff, rng.randrange(-1000, 1000)])
        key = owner_key if rng.random() < 0.7 else rng.choice([owner_key + 1, owner_key ^ 0x10000, -owner_key - 1])
        key = ((key + 0x80000000) & 0xffffffff) - 0x80000000
        code = rng.choice([173, 189, 363, 0, -7, rng.randrange(-500, 500)])
        obj = rng.randrange(8)
        slot = am.undefined_region('slot', SLOT, 0x40, 0x61)
        slot.define(SLOT + 4, struct.pack('<III', OWNER if has_owner else 0, OBJECTS + 0x40 * obj if has_object else 0,
                                          RECORD if has_info else 0))
        slot.define(SLOT + 0x10, bytes([active]))
        slot.define(SLOT + 0x1c, struct.pack('<i', key))
        owner = am.undefined_region('owner', OWNER, 0x3300, 0x62)
        owner.define(OWNER + 0x3244, struct.pack('<i', owner_key))
        record = am.undefined_region('record', RECORD, 0x40, 0x63)
        record.define(RECORD, struct.pack('<i', code))
        objs = am.undefined_region('objects', OBJECTS, 0x40 * 8, 0x44)
        objects = {OBJECTS + 0x40 * k: k for k in range(8)}
        calls = []

        def consumer(m):
            assert m.uc.reg_read(m.x86.UC_X86_REG_ECX) == INFO
            calls.append(('consumer', objects.get(m.argument(0), -9), struct.unpack('<i', struct.pack('<I', m.argument(1)))[0]))
            return 0, 8

        def clear(m):
            calls.append(('clear', objects.get(m.uc.reg_read(m.x86.UC_X86_REG_ECX), -9)))
            return 0
        regions = [slot, owner, record, objs]
        r1 = machine.execute(SLOT_ATTACH, [], regions, {ATTACH_MUUN: consumer}, ecx=SLOT)
        r2 = machine.execute(SLOT_CLEAR, [], regions, {CLEAR: clear}, ecx=SLOT)
        keep, mine = [], []
        s = Slot(int(has_owner), owner_key, obj if has_object else -1, int(has_info), code, active, key)
        table = c_table([{'code': code, 'path': b'x', 'position': [0] * 3, 'rotation': [0] * 3, 'scale': 0,
                          'bone': 0, 'follow': 0}], keep)
        ops = muun_ops(mine, set(), keep, code_events=True)
        done = lib.mu_muun_slot_attach(C.byref(s), C.byref(table), C.byref(ops))
        cleared = lib.mu_muun_slot_clear(C.byref(s), C.byref(ops))
        ok = r1['ok'] and r2['ok'] and calls == mine and done == any(c[0] == 'consumer' for c in calls) and \
            cleared == any(c[0] == 'clear' for c in calls)
        report.add('muun_gate', ok, None if ok else {'case': n, 'client': calls, 'native': mine,
                                                     'stopped': [str(r1.get('stopped')), str(r2.get('stopped'))]})
        report.cover('muun_gate', ('attached' if done else 'refused') + '/' + ('cleared' if cleared else 'kept'))
        if has_owner and has_object and has_info and active and key != owner_key:
            report.cover('muun_gate', 'other owner key')


# ---------------------------------------------------------------- muun_update
def random_bones(rng, count):
    return [f32(rng.choice([0.0, 1.0, -1.0, rng.uniform(-2.0, 2.0), rng.uniform(-300.0, 300.0)]))
            for _ in range(12 * count)]


def random_update_case(rng):
    model_bones = rng.choice([-1, 0, 27, 51, 60, rng.randrange(1, 64)])
    own = rng.random() < 0.75
    records = []
    for k in range(rng.choice([0, 1, 2, 3, 5, 8])):
        follow = rng.choice([0, 1, 1, 2, 0xff])
        bone = rng.choice([3, 5, 26, 50, 0, -1, rng.randrange(0, 62), model_bones, model_bones - 1])
        if not follow and rng.random() < 0.15:
            bone = rng.choice([-2, -7])   # no-follow below -1: the scale alone (a follower there is undefined)
        bone = max(bone, -1) if follow else bone
        bone = min(bone, SHARED_BONES - 2)   # the shared_index mutant reads bone + 1
        timed = rng.choice([0, 0, 1, 1, 2])
        records.append({'handle': k, 'template': bits(f32(rng.choice([9.0, 10.0, 30.0, 1.0, rng.uniform(0.0, 50.0)]))),
                        'bone': bone, 'follow': follow, 'timed': timed,
                        'lifetime': bits(f32(rng.choice([0.0, 0.1, 0.05, 0.2, 1.0, -1.0, rng.uniform(-1.0, 3.0)])))})
    sector = rng.choice([(0, 0), (0, 0), (OBJECTS, 0), (0, OBJECTS)])
    return {'records': records, 'model_bones': model_bones, 'own': own, 'sector': sector,
            'bones': random_bones(rng, max(model_bones, 1) + 2), 'shared': random_bones(rng, SHARED_BONES),
            'position': [bits(f32(rng.uniform(-30000.0, 30000.0))) for _ in range(3)],
            'angle': [bits(f32(rng.choice([0.0, 90.0, -45.0, rng.uniform(-720.0, 720.0)]))) for _ in range(3)],
            'scale': bits(f32(rng.choice([1.0, 0.5, 1.3, 0.0, rng.uniform(0.01, 4.0)]))),
            'dt': bits(f32(rng.choice([0.1, 0.1, 0.0, 0.05, 1.0, rng.uniform(0.0, 0.5)]))),
            'type': rng.randrange(0, 1200)}


def run_client_update(machine, case):
    heap = Heap(HEAP, 0x4000 + 0x40 * len(case['records']))
    head = heap.alloc(0x20)
    nodes = [heap.alloc(0x20) for _ in case['records']]
    ring = [head] + nodes
    for k, node in enumerate(ring):
        nxt, prv = ring[(k + 1) % len(ring)], ring[k - 1]
        heap.define(node, struct.pack('<II', nxt, prv))
    for node, rec in zip(nodes, case['records']):
        heap.define(node + 8, struct.pack('<IIIiBBxxI', EFFECTS + 0x100 * rec['handle'], 0, rec['template'],
                                          rec['bone'], rec['follow'], rec['timed'], rec['lifetime']))
    obj = am.undefined_region('object', OBJ, OBJ_SIZE + 0x10, 0x29)
    obj.define(OBJ + 0x5c, struct.pack('<i', case['type']))
    obj.define(OBJ + 0xa0, struct.pack('<I', case['scale']))
    obj.define(OBJ + 0x158, struct.pack('<6I', *case['position'], *case['angle']))
    obj.define(OBJ + 0x318, struct.pack('<I', BONES if case['own'] else 0))
    obj.define(OBJ + 0x350, struct.pack('<II', *case['sector']))
    obj.define(OBJ + 0x3d0, struct.pack('<II', head, len(nodes)))
    bones = am.defined_region('bones', BONES, struct.pack(f"<{len(case['bones'])}f", *case['bones']), writable=False)
    shared = am.defined_region('shared', SHARED_POSE, struct.pack(f"<{len(case['shared'])}f", *case['shared']),
                               writable=False)
    model = am.undefined_region('model', MODEL, 0x40, 0x31)
    model.define(MODEL + 0x22, struct.pack('<h', max(case['model_bones'], 0)))
    effects = am.undefined_region('effects', EFFECTS, 0x100 * max(1, len(nodes)), 0x35)
    calls, freed = [], []

    def handle(address):
        return (address - EFFECTS) // 0x100

    def node_update(m):
        matrix = struct.unpack('<16I', bytes(m.uc.mem_read(m.argument(1), 64)))
        calls.append(('update', handle(m.uc.reg_read(m.x86.UC_X86_REG_ECX)), m.argument(0), matrix,
                      m.argument(2) == OBJ))
        return 0, 0xc

    def set_scale(m):
        calls.append(('scale', handle(m.uc.reg_read(m.x86.UC_X86_REG_ECX)), m.argument(0)))
        return 0, 4

    def get_model(m):
        assert m.argument(0) == case['type']
        return (MODEL if case['model_bones'] >= 0 else 0), 4

    def sine(m):
        x = m.float_argument(0)
        return m.x87_return(f32(math.sin(x)) if math.isfinite(x) else float('nan'))

    def cosine(m):
        x = m.float_argument(0)
        return m.x87_return(f32(math.cos(x)) if math.isfinite(x) else float('nan'))

    def delete(m):
        freed.append(m.argument(0))
        return 0
    stubs = {NODE_UPDATE: node_update, SET_SCALE: set_scale, MODELS: lambda m: FAKE, GET_MODEL: get_model,
             SINE: sine, COSINE: cosine}
    stubs.update({address: delete for address in DELETE})
    r = machine.execute(UPDATE, [case['dt']], [heap.region, obj, bones, shared, model, effects], stubs, ecx=OBJ,
                        cleanup=4)
    left = []
    if r['ok']:
        raw = r['regions']
        heap_bytes, base = raw['heap'], HEAP
        node = struct.unpack_from('<I', heap_bytes, head - base)[0]
        while node != head and len(left) <= len(nodes):
            effect, _, _, _, _, _, life = struct.unpack_from('<IIIiBBxxI', heap_bytes, node + 8 - base)
            left.append((handle(effect), life))
            node = struct.unpack_from('<I', heap_bytes, node - base)[0]
        size = struct.unpack_from('<I', raw['object'], 0x3d4)[0]
        left.append(('size', size))
    return calls, left, r


DELETE = (0x019a4d50,)   # the CRT free reached by operator delete from erase 0x012a1417


def run_c_update(lib, case):
    recs = (Record * max(1, len(case['records'])))()
    for k, rec in enumerate(case['records']):
        recs[k].handle, recs[k].template_scale, recs[k].bone = rec['handle'], rec['template'], rec['bone']
        recs[k].follow, recs[k].timed, recs[k].lifetime = rec['follow'], rec['timed'], rec['lifetime']
    bones = (C.c_float * len(case['bones']))(*case['bones'])
    shared = (C.c_float * len(case['shared']))(*case['shared'])
    o = EffectObject()
    o.position[:], o.angle[:], o.scale = case['position'], case['angle'], case['scale']
    o.in_sector = int(any(case['sector']))
    o.bones = C.cast(bones, C.c_void_p).value if case['own'] else None
    o.model_bones, o.shared = case['model_bones'], C.cast(shared, C.c_void_p).value
    calls = []

    def scale(ctx, h, value):
        calls.append(('scale', h, bits(value)))

    def update(ctx, h, dt, matrix):
        calls.append(('update', h, bits(dt), tuple(matrix[k] for k in range(16)), True))
    fns = [HANDLE_FN(lambda c, h: None), SCALE_FN(scale), UPDATE_FN(update)]
    ops = ObjOps(None, *fns)
    kept = lib.mu_object_effects_update(recs, len(case['records']), C.byref(o), am.from_bits(case['dt']), C.byref(ops))
    left = [(recs[k].handle, recs[k].lifetime) for k in range(kept)] + [('size', kept)]
    return calls, left


def same_call(a, b):
    if a[:2] != b[:2] or a[0] != b[0]:
        return False
    fa = [a[2]] + list(a[3]) if a[0] == 'update' else [a[2]]
    fb = [b[2]] + list(b[3]) if b[0] == 'update' else [b[2]]
    return all(fx.same(am.from_bits(x), am.from_bits(y)) for x, y in zip(fa, fb)) and a[4:] == b[4:]


def family_update(lib, machine, rng, cases, report):
    for n in range(cases):
        case = random_update_case(rng)
        client, client_left, r = run_client_update(machine, case)
        mine, mine_left = run_c_update(lib, case)
        ok = r['ok'] and len(client) == len(mine) and all(same_call(a, b) for a, b in zip(client, mine)) and \
            client_left == mine_left
        detail = None
        if not ok:
            first = next((k for k, (a, b) in enumerate(zip(client, mine)) if not same_call(a, b)),
                         min(len(client), len(mine)))
            detail = {'case': n, 'stopped': str(r.get('stopped')), 'error': str(r.get('error')), 'at': first,
                      'client': [repr(c) for c in client[first:first + 1]], 'native': [repr(c) for c in mine[first:first + 1]],
                      'left': [client_left, mine_left]}
        report.add('muun_update', ok, detail)
        for rec in case['records']:
            path = ('follow ' if rec['follow'] else 'place ') + (
                'world' if rec['bone'] == -1 else 'scale only' if rec['bone'] < -1 else
                'own bone' if case['own'] and 0 <= rec['bone'] < case['model_bones'] else 'shared bone')
            report.cover('muun_update', path + (' sector' if any(case['sector']) else ''))
        report.cover('muun_update', f"expired {sum(1 for c in client_left if c[0] != 'size') < len(case['records'])}")


# ---------------------------------------------------------------- uruk_reader
WEATHER = [-1, 0, 1, 2, 36, -0x80000000, 0x7fffffff, 1]


def family_reader(machine, lib, cases, report):
    """Uruk's visual for types 108 and 109 over the weather domain (validate_worlds_i's boundaries)."""
    g = random.Random('render-effects-018-reader')
    vi_bind(lib)
    for n in range(cases):
        typ = (108, 109)[n % 2]
        weather = WEATHER[(n // 2) % len(WEATHER)]
        world = (100, 101)[(n // 16) % 2]
        raw = bytearray(v.move_object(g, world, 'full'))
        v.put_i(raw, 0x5c, typ)
        time = v.f32(g.choice([0, 1000, g.uniform(-1e6, 1e6)]))
        seed = g.getrandbits(32)
        rnd, crnd = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            calls.append((0x168fafd, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], int(a[6] == v.OBJECTS)))
            return 0

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            assert a[4:8] == [12, v.OBJECTS, 0xffffffff, 0] and a[9:] == [0, v.bits(0), 0xffffffff, 0, 0]
            calls.append((0xe701e5, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (12, 1, a[8]))
            return 0

        def joint(m):
            a = [m.argument(k) for k in range(14)]
            calls.append((0xe70274, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (13, 0, a[6]) + v.read_vec(m, a[11]))
            return 0
        regs = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(raw)),
                                           am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                           am.defined_region('weather', 0x1cf15ec, struct.pack('<i', weather)),
                                           am.defined_region('model', v.MODEL, bytes(0x100))])
        result = v.run(machine, 0xe6f3d5, [v.OBJECTS, v.FAKE], regs,
                       {0x966cc4: lambda m: v.FAKE, 0xeaa8cf: lambda m: (v.MODEL, 4), 0x168fafd: particle,
                        0x1989721: lambda m: rnd(), 0x13c0eaa: effect, 0x153b02c: joint}, ecx=v.FAKE, cleanup=8)
        stop = v.stopped_reason(result)
        co = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: crnd())
        handled = lib.dll.mu_uruk_visual(co, 0, world, weather, time, fn, None, C.byref(log))
        diff = [hex(k) for k in range(v.OBJ_SIZE) if not stop and co.raw[k] != result['regions']['object'][k]]
        ok = not stop and not diff and handled == (result['eax'] & 255) and calls == v.log_events(log) and \
            rnd.seed == crnd.seed
        report.add('uruk_reader', ok, None if ok else {'case': n, 'type': typ, 'weather': weather, 'stop': stop,
                                                       'diff': diff[:6], 'calls': calls[:2],
                                                       'native': v.log_events(log)[:2]})
        report.cover('uruk_reader', f"type {typ} weather {weather}: " +
                     ('keyed effect' if any(c[0] == 0xe701e5 for c in calls) else
                      'joint' if any(c[0] == 0xe70274 for c in calls) else
                      'particles only' if calls else 'silent'))


def vi_bind(lib):
    d = lib.dll
    d.mu_uruk_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int32, C.c_float, v.RAND_FN, C.c_void_p,
                                 C.POINTER(v.Log)]
    return lib


# ---------------------------------------------------------------- Uruk's effect and particles
URUK_PT = [(0x8084, 1), (0x806e, 5), (0x8085, 1)]
URUK_FX = [(0x806e, 12)]
PT_THRESHOLDS = {0x8084: [21, 20, 19], 0x806e: [16, 15, 14], 0x8085: [16, 15, 14]}


def random_flame(rng, kind):
    p = r11._random_particle(rng, kind)   # validate_particles' record
    p.lifetime = rng.choice(PT_THRESHOLDS[kind[0]] * 3 + [30, 2, 1, 0, -1, rng.randrange(-5, 40)])
    p.live = rng.choice([1, 1, 1, 1, 0, 2])
    p.alpha = f32(rng.choice([1.0, 0.9, 0.81, 0.8, 0.1, 0.11, 0.09, 0.3, 0.0, rng.uniform(-0.2, 1.2)]))
    p.scale = f32(rng.choice([p.scale, 0.0, -0.0, 0.03, 0.06, -0.01, rng.uniform(0.0, 2.0)]))
    return p


def pt_compare(text, data, lib, name, kinds, cases, seed='render-effects-018-pt-'):
    pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case = kinds, set(), random_flame, r11.OwnerCase
    pt.globals_region = r11.globals_region
    m = pt.PtMachine(text, data)
    report = pt.Report()
    dict(pt.FAMILIES)[name](m, lib, random.Random(seed + name), cases, report, defaultdict(int))
    return report.families[name], report.coverage.get(name, {})


def fx_compare(text, data, lib, name, cases):
    r = r11.fx_compare(text, data, lib, name, URUK_FX, cases, seed='render-effects-018-fx-')
    return r['families']['fx_' + name], r['coverage'].get('fx_' + name, {})


# ---------------------------------------------------------------- mutants
MUUN_MUTANTS = [
    # (name, old, new, family)
    ('upper_bound', 'upper ? !(code < t->entries[mid].code)', 'upper ? !(code <= t->entries[mid].code)', 'muun_attach'),
    ('lower_bound', ': t->entries[mid].code < code)', ': t->entries[mid].code <= code)', 'muun_attach'),
    ('attach_null', '        if (handle >= 0)\n            ops->attach', '        if (handle >= -1)\n            ops->attach',
     'muun_attach'),
    ('follow_forced', 'e->bone, e->follow, 0, 0.0f)', 'e->bone, 1, 0, 0.0f)', 'muun_attach'),
    ('release_valid', '        ops->release(ops->context, handle);\n    }\n    return last - first;',
     '        if (handle >= 0)\n            ops->release(ops->context, handle);\n    }\n    return last - first;', 'muun_attach'),
    ('gate_key', 's->key != s->owner_key', 's->key == s->owner_key', 'muun_gate'),
    ('gate_active', 'if (!s->active || s->key', 'if (s->key', 'muun_gate'),
    ('gate_info', 'if (s->object < 0 || !s->has_owner || !s->has_info)', 'if (s->object < 0 || !s->has_owner)',
     'muun_gate'),
    ('clear_owner', '    if (s->object < 0 || !s->has_owner)\n        return 0;\n    ops->clear',
     '    if (s->object < 0)\n        return 0;\n    ops->clear', 'muun_gate'),
    ('own_bone_count', 'bone >= 0 && bone < o->model_bones', 'bone >= 0 && bone <= o->model_bones', 'muun_update'),
    ('shared_index', 'return o->shared + 12 * bone;', 'return o->shared + 12 * (bone + 1);', 'muun_update'),
    ('sector', '    if (!o->in_sector) {\n        const float zero', '    if (1) {\n        const float zero', 'muun_update'),
    ('product_order', 'product[r + 4 * c] = place[r] * m[4 * c]', 'product[r + 4 * c] = m[r] * place[4 * c]',
     'muun_update'),
    ('place_sign', 'm[4] = -(cy * sz) * s;', 'm[4] = (cy * sz) * s;', 'muun_update'),
    ('bone_offset', '            out[k] = out[k] + o->position[k];', '            out[k] = out[k] * o->position[k];',
     'muun_update'),
    ('expire_edge', 'if (0.0f >= rec.lifetime)', 'if (0.0f > rec.lifetime)', 'muun_update'),
    ('expire_add', 'rec.lifetime = rec.lifetime - dt;', 'rec.lifetime = rec.lifetime + dt;', 'muun_update'),
    ('scale_owner', 'rec.template_scale * o->scale);', 'rec.template_scale);', 'muun_update'),
    ('place_world', '    if (rec->bone == -1) {\n        out[12]', '    if (rec->bone == -2) {\n        out[12]', 'muun_update'),
    ('world_rad', 'const float to_rad = 0.017453292f;', 'const float to_rad = 0.0174533f;', 'muun_update'),
    ('transpose', 'm[4 * c + r] = b[4 * r + c];', 'm[4 * r + c] = b[4 * r + c];', 'muun_update'),
]
FX_MUTANTS = [
    ('fx_life', 'e->lifetime = 20;\n    return 1;', 'e->lifetime = 21;\n    return 1;', 'create'),
    ('fx_spread', 'p[1] = (float)(smod(env_rand(env), 50) - 25)', 'p[1] = (float)(smod(env_rand(env), 50) - 24)', 'move'),
    ('fx_lift', '(float)(smod(env_rand(env), 10) + 5)', '(float)(smod(env_rand(env), 10) + 4)', 'move'),
    ('fx_size', '(smod(env_rand(env), 5) + 13)', '(smod(env_rand(env), 5) + 12)', 'move'),
    ('fx_kind', 'e->light, 5, scale, MU_SFX_NO_OWNER', 'e->light, 4, scale, MU_SFX_NO_OWNER', 'move'),
    ('fx_order', 'case 0: call_particle(env, e, 0x8084', 'case 0: call_particle(env, e, 0x8085', 'move'),
]
PT_MUTANTS = [
    ('pt_life', '(p->type == 0x8084 ? 20 : 24)', '(p->type == 0x8084 ? 20 : 25)', 'create', (0x806e, 5)),
    ('pt_rise', '% 24 + 74) * 0.1f;', '% 24 + 64) * 0.1f;', 'create', (0x8084, 1)),
    ('pt_dim', 'if (p->lifetime < (p->type == 0x8084 ? 20 : 15))', 'if (p->lifetime < (p->type == 0x8084 ? 15 : 15))',
     'move', (0x8084, 1)),
    ('pt_brighten', 'p->alpha += (float)(mu_pt_rand(h) % 2 + 2) * 0.1f;', 'p->alpha += (float)(mu_pt_rand(h) % 2 + 1) * 0.1f;',
     'move', (0x806e, 5)),
    ('pt_shrink', '(p->type == 0x8084 ? 4 : 5)) * 0.01f;', '(p->type == 0x8084 ? 4 : 6)) * 0.01f;', 'move', (0x806e, 5)),
    ('pt_turn', '    p->rotation += 3.0f;\n}', '    p->rotation += 2.0f;\n}', 'move', (0x8084, 1)),
]
READER_MUTANTS = [
    # uruk.c's reader is RENDER-WORLDS-I's; these show the weather domain is needed (values 2, 36 and -1)
    ('reader_108_positive', 'if (weather==1 && random(ctx)%2 != 0)', 'if (weather>0 && random(ctx)%2 != 0)'),
    ('reader_109_nonzero', '        if (weather==1) {\n            const float color', '        if (weather!=0) {\n            const float color'),
]


def compile_combat_mutant(directory, name, old, new):
    base = ROOT/'reconstructed'/'combat'
    if (base/'uruk_fx.inc').read_text().count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    work = Path(directory)/name
    work.mkdir()
    for f in ('skill_fx.c', 'pet_fx.inc', 'arrow_fx.inc', 'bow_fx.inc'):
        shutil.copy(base/f, work/f)
    (work/'uruk_fx.inc').write_text((base/'uruk_fx.inc').read_text().replace(old, new))
    others = ['combat.c', '../objects/world_warp.c', '../joints/joints.c', '../record-math/record_math.c',
              '../movement/client_movement.c']
    out = Path(directory)/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(base), str(work/'skill_fx.c'), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return fx.load_library(out)


def compile_reader_mutant(directory, name, old, new):
    work = Path(directory)/name
    shutil.copytree(ROOT/'reconstructed', work, ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '*.o',
                                                                              '__pycache__', 'build'))
    path = work/'objects'/'uruk.c'
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    path.write_text(source.replace(old, new))
    subprocess.run(['make', '-s', '-C', str(work/'objects')], check=True, capture_output=True)
    return v.Library(work/'objects'/f'libobjects.{v.SUFFIX}')


class Report:
    def __init__(self):
        self.families, self.coverage = {}, defaultdict(lambda: defaultdict(int))

    def add(self, family, ok, detail=None):
        f = self.families.setdefault(family, {'cases': 0, 'equal': 0, 'first_failures': []})
        f['cases'] += 1
        f['equal'] += bool(ok)
        if not ok and len(f['first_failures']) < 3:
            f['first_failures'].append(detail)

    def cover(self, family, label):
        self.coverage[family][label] += 1


def run(cases, mutations, lang_dir=None):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'coverage': {},
              'mutants': {}}
    machine = fx.FxMachine(text, data)
    report = Report()
    with tempfile.TemporaryDirectory(prefix='render-effects18-') as tmp:
        lib = build_muun(tmp)
        family_attach(lib, machine, random.Random('render-effects-018-attach'), cases * 4, report)
        family_gate(lib, machine, random.Random('render-effects-018-gate'), cases * 4, report)
        family_update(lib, machine, random.Random('render-effects-018-update'), cases * 4, report)
        records = None
        if lang_dir and (Path(lang_dir)/'muuneffects.tsv').is_file():
            records = family_records(lib, machine, load_records(lang_dir), report)
            result['records'] = records
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/objects')], check=True)
    objects = v.Library(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}')
    family_reader(v.Machine(text, data), vi_bind(objects), cases * 2, report)
    result['families'].update(report.families)
    result['coverage'].update({k: dict(c) for k, c in report.coverage.items()})
    plib = pt.load_library(ROOT/'reconstructed'/('particles/libclient_particles.' + fx.SUFFIX))
    for name in ('create', 'move', 'render'):
        f, cov = pt_compare(text, data, plib, name, URUK_PT, cases * len(URUK_PT))
        result['families']['uruk_pt_' + name], result['coverage']['uruk_pt_' + name] = f, cov
    clib = fx.load_library(ROOT/'reconstructed'/('combat/libcombat.' + fx.SUFFIX))
    for name in ('create', 'move'):
        f, cov = fx_compare(text, data, clib, name, cases * 2)
        result['families']['uruk_fx_' + name], result['coverage']['uruk_fx_' + name] = f, cov
    if mutations:
        machine = fx.FxMachine(text, data)   # the effect families above resize actor_machine's stack
        source = (ROOT/'reconstructed/objects/muun_effects.c').read_text()
        with tempfile.TemporaryDirectory(prefix='render-effects18-mut-') as tmp:
            for name, old, new, family in MUUN_MUTANTS:
                if source.count(old) != 1:
                    raise ValueError(f'{name}: expected exactly one mutation site')
                folder = Path(tmp)/name
                folder.mkdir()
                mlib = build_muun(folder, source.replace(old, new))
                rep = Report()
                fn = {'muun_attach': family_attach, 'muun_gate': family_gate, 'muun_update': family_update}[family]
                fn(mlib, machine, random.Random('render-effects-018-' + family.split('_')[1]), max(40, cases * 4), rep)
                f = rep.families[family]
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
            for name, old, new, family in FX_MUTANTS:
                mlib = compile_combat_mutant(tmp, name, old, new)
                f, _ = fx_compare(text, data, mlib, family, max(40, cases * 2))
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
            for name, old, new, family, kind in PT_MUTANTS:
                mlib = r11.compile_pt_mutant(tmp, name, 'uruk_flames.inc', old, new)
                f, _ = pt_compare(text, data, mlib, family, [kind], max(40, cases))
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
            for name, old, new in READER_MUTANTS:
                mlib = compile_reader_mutant(tmp, name, old, new)
                rep = Report()
                family_reader(v.Machine(text, data), vi_bind(mlib), max(32, cases * 2), rep)
                f = rep.families['uruk_reader']
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                               'sha256': hashlib.sha256(text[a - am.TEXT_BASE:b - am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in BODIES.items()}
    result['instruction_cases'] = sum(f['cases'] for f in result['families'].values())
    result['all_equal'] = all(f['cases'] == f['equal'] for f in result['families'].values())
    result['all_mutants_caught'] = all(m['caught'] > 0 for m in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cases', type=int, default=20, help='cases per family unit')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--lang-dir', type=Path,
                        help='lang directory with muuneffects.tsv: adds the private family muun_records')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations, args.lang_dir)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, default=str))
    summary = {name: (f['cases'], f['equal']) for name, f in result['families'].items()}
    print(json.dumps({'summary': summary, 'instruction_cases': result['instruction_cases'],
                      'records': result.get('records'), 'mutants': result['mutants'],
                      'all_equal': result['all_equal'], 'all_mutants_caught': result['all_mutants_caught']}, indent=1))
    if not result['all_equal']:
        for name, f in result['families'].items():
            for failure in f['first_failures'][:2]:
                print(name, str(failure)[:1500])
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
