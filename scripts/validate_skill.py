#!/usr/bin/env python3
"""Run the client's skill routines in Unicorn and compare them with reconstructed/skill (NATIVE-SKILL-001).

The pinned restored text (0x00401000) and second image section run in Unicorn (scripts/client_ui_machine.py,
through validate_lang's LangMachine, which maps the langread snapshot of the Lang.mpr tables at its original
addresses).  The C side is reconstructed/skill built as a shared library (libclientskill) and called through
ctypes with the same inputs.

Families:

* lexcast: boost::lexical_cast<int> try-parse 0x00cd8314 and lexical_cast<bool> 0x010c2ce2 on synthetic
  strings (sign, digits, range, spaces, letters);
* row: the Skill(Kor) row parser 0x01170ca5 on synthetic rows into a fresh table object, read back through
  the client's lookup 0x00961620 (every field, the two inner maps and the pair vector); rows with a bad column
  run the client's catch path (the throw helpers redirect to the handler's continuation 0x0117179c);
* req: the stat check 0x0109228f for every snapshot skill with random stats and class indices;
* mana: the mana/AG check 0x01091692 (GetSkillInformation runs for real over the snapshot) with random
  hero values and buff sets;
* delay: StartSkillDelay 0x01696aca (+ 0x01696ca6), IsSkillReady 0x016969e9 and the tick 0x01696e06 on
  random learned lists, timers and skill-tree/master answers;
* special: 0x01096e55 for every snapshot skill, class indices 0..7 and buff states;
* feed: the bar feed 0x00c58797 over random hotkeys, selections and usability answers (two calls per
  case: the change detection), the GFx object it builds recorded member by member;
* icon: the skill icon draw 0x01097130 (stamp entry, usability, cell size) with RenderBitmap recorded;
* wrap: the text wrap 0x011ff794 (-> 0x01193941) with a modelled GetTextExtentPointA;
* tooltip: the builder 0x0117da56 over the snapshot's skills with SkillTooltipText records (the installed
  file when MU_GAME_ROOT is set, else synthetic), its popup step 0x00c1f2b0 recorded;
* tiphtml: 0x00c1f2b0 on synthetic text lists (the SetInfoPopupSkillStamp invoke).

Modelled (not client code): import calls stop the case; operator new/delete and malloc/free are the
machine's heap; the C++ locale of lexical_cast is the classic one (0x0094a4b4 / 0x018ed8d8 / 0x00cd8c04);
the client's sprintf 0x009619dd / vsprintf (a Python statement of the conversions the tables use);
GetTextExtentPointA (a per-character width table, the same one the C gets as its measure); the managers
named in each family (master skills, class skill tree, buffs, inventory, GFx objects) return case values.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402

I32 = ctypes.c_int32
U8 = ctypes.c_uint8
U16 = ctypes.c_uint16

SKILL_TABLE = 0x06fbb138
PARSE_ROW, PARSE_CONTINUE, ROW_LOG = 0x01170ca5, 0x0117179c, 0x010d7e03
LEX_INT, LEX_BOOL, THROW_INT, THROW_BOOL = 0x00cd8314, 0x010c2ce2, 0x00cd828d, 0x010c2c86
LOCALE_CTOR, LOCALE_CLASSIC, LOCALE_EQ, LOCALE_DTOR = 0x0094a4b4, 0x018ed8d8, 0x00cd8c04, 0x0094aec2
SKILL_LOOKUP = 0x00961620
CRT_SIZED_DELETE = 0x0191baab


def s32(v):
    return struct.unpack('<i', struct.pack('<I', v & 0xffffffff))[0]


# ---- native library ---------------------------------------------------------------------------------

class RecordC(ctypes.Structure):
    _fields_ = [('skip', U8), ('index', I32), ('name', ctypes.c_char*128),
                ('level', I32), ('damage', I32), ('mana', I32), ('ag', I32), ('distance', I32), ('delay', I32),
                ('req_energy', I32), ('req_strength', I32), ('req_dexterity', I32), ('req_command', I32),
                ('req_vitality', I32), ('mastery', I32), ('x54', I32), ('use_type', I32), ('brand', I32),
                ('x60', I32), ('rank', I32*3), ('classes', I32*16), ('x74', I32), ('x78', I32),
                ('master_factor', I32), ('x80', I32), ('x84', I32), ('x88', I32), ('icon', I32), ('type', I32),
                ('x94', U8), ('x98', I32), ('x9c', I32), ('xa0', I32), ('xa4', I32), ('xa8', I32), ('xac', I32),
                ('xb0', I32), ('weapon', I32), ('pairs', (I32*2)*2), ('npairs', I32), ('imprint', I32),
                ('xc8', U8), ('damage_type', I32)]


# (name, record offset, kind) of every field the parser writes, in record order
RECORD_FIELDS = [('index', 0x04, 'i'), ('level', 0x20, 'i'), ('damage', 0x24, 'i'), ('mana', 0x28, 'i'),
                 ('ag', 0x2c, 'i'), ('distance', 0x34, 'i'), ('delay', 0x38, 'i'), ('req_strength', 0x3c, 'i'),
                 ('req_dexterity', 0x40, 'i'), ('req_energy', 0x44, 'i'), ('req_command', 0x48, 'i'),
                 ('req_vitality', 0x4c, 'i'), ('mastery', 0x50, 'i'), ('x54', 0x54, 'i'), ('use_type', 0x58, 'i'),
                 ('brand', 0x5c, 'i'), ('x60', 0x60, 'i'), ('x74', 0x74, 'i'), ('x78', 0x78, 'i'),
                 ('master_factor', 0x7c, 'i'), ('x80', 0x80, 'i'), ('x84', 0x84, 'i'), ('x88', 0x88, 'i'),
                 ('icon', 0x8c, 'i'), ('type', 0x90, 'i'), ('x94', 0x94, 'b'), ('x98', 0x98, 'i'),
                 ('x9c', 0x9c, 'i'), ('xa0', 0xa0, 'i'), ('xa4', 0xa4, 'i'), ('xa8', 0xa8, 'i'), ('xac', 0xac, 'i'),
                 ('xb0', 0xb0, 'i'), ('weapon', 0xb4, 'i'), ('imprint', 0xc4, 'i'), ('xc8', 0xc8, 'b'),
                 ('damage_type', 0xcc, 'i')]


def native_record(r):
    out = {'skip': r.skip, 'name': r.name}
    for name, _, _ in RECORD_FIELDS:
        out[name] = getattr(r, name)
    out['rank'] = {0x80: r.rank[0], 0x40: r.rank[1], 0x20: r.rank[2]}
    out['classes'] = {i: r.classes[i] for i in range(16)}
    out['pairs'] = [(r.pairs[i][0], r.pairs[i][1]) for i in range(r.npairs)]
    return out


class Native:
    def __init__(self, work, lib=None):
        if lib is None:
            subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill')], check=True)
            ext = 'dylib' if sys.platform == 'darwin' else 'so'
            lib = ROOT/f'reconstructed/skill/libclientskill.{ext}'
        self.lib = L = ctypes.CDLL(str(lib))
        L.mu_skill_lexical_int.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(I32)]
        L.mu_skill_lexical_bool.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(U8)]
        L.mu_skill_parse_row.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_size_t),
                                         ctypes.c_size_t, ctypes.POINTER(RecordC)]

    def lexical(self, kind, text):
        if kind == 'int':
            out = I32()
            ok = self.lib.mu_skill_lexical_int(text, len(text), ctypes.byref(out))
        else:
            out = U8()
            ok = self.lib.mu_skill_lexical_bool(text, len(text), ctypes.byref(out))
        return (1, out.value) if ok else (0, None)

    def parse(self, cols):
        n = len(cols)
        arr = (ctypes.c_char_p*n)(*cols)
        lens = (ctypes.c_size_t*n)(*[len(c) for c in cols])
        rec = RecordC()
        status = self.lib.mu_skill_parse_row(arr, lens, n, ctypes.byref(rec))
        return status, rec


# ---- machine helpers --------------------------------------------------------------------------------

class Family(vl.Family):
    """validate_lang's family with a tally of the client's scalar outcomes (branch coverage)."""

    def __init__(self, name):
        super().__init__(name)
        self.outcomes = {}
        self.samples = []

    def check(self, label, client, native):
        if isinstance(client, (int, bool)) or client is None:
            self.outcomes[str(client)] = self.outcomes.get(str(client), 0) + 1
        elif isinstance(client, tuple) and client and isinstance(client[0], (int, bool)):
            self.outcomes[str(client[0])] = self.outcomes.get(str(client[0]), 0) + 1
        if len(self.samples) < 2 and client not in (None, 0, [], ()):
            self.samples.append(repr(client)[:300])
        super().check(label, client, native)

    def summary(self):
        out = super().summary()
        if self.outcomes:
            out['outcomes'] = self.outcomes
        out['samples'] = self.samples
        return out


def std_string(m, text):
    """An MSVC std::string object (24 bytes) on the case heap."""
    a = m.alloc(0x18, define=True)
    if len(text) < 16:
        m.write(a, text + b'\0'*(16 - len(text)))
        m.write(a + 0x10, struct.pack('<II', len(text), 15))
    else:
        b = m.alloc(len(text) + 1, define=True)
        m.write(b, text + b'\0')
        m.write(a, struct.pack('<I', b) + bytes(12))
        m.write(a + 0x10, struct.pack('<II', len(text), len(text)))
    return a


def string_vector(m, items):
    """std::vector<std::string> {begin, end, capacity}."""
    block = m.alloc(0x18*max(len(items), 1), define=True)
    for i, text in enumerate(items):
        s = std_string(m, text)
        m.write(block + 0x18*i, m.read(s, 0x18))
    v = m.alloc(12, define=True)
    m.write(v, struct.pack('<III', block, block + 0x18*len(items), block + 0x18*len(items)))
    return v


def empty_map(m, node_size):
    """An empty MSVC std::map: the head node (_Left = _Parent = _Right = head, black, _Isnil) and size 0."""
    head = m.alloc(node_size, define=True)
    m.write(head, struct.pack('<III', head, head, head) + b'\x01\x01\0\0')
    return head


def read_tree(m, container):
    """(key, node) of an MSVC std::map in emulator memory (key at +0x10)."""
    head, size = struct.unpack('<II', m.read(container, 8))
    out, stack = [], []
    root = m.u32(head + 4)
    if root != head:
        stack.append(root)
    while stack and len(out) <= size:
        node = stack.pop()
        left, _, right = struct.unpack('<III', m.read(node, 12))
        out.append((s32(m.u32(node + 0x10)), node))
        if left != head:
            stack.append(left)
        if right != head:
            stack.append(right)
    out.sort()
    return out, size


def client_record(m, r):
    out = {'skip': m.read(r, 1)[0], 'name': m.std_string(r + 8)}
    for name, off, kind in RECORD_FIELDS:
        out[name] = s32(m.u32(r + off)) if kind == 'i' else m.read(r + off, 1)[0]
    rank, _ = read_tree(m, r + 0x64)
    out['rank'] = {k: s32(m.u32(node + 0x14)) for k, node in rank}
    classes, _ = read_tree(m, r + 0x6c)
    out['classes'] = {k: s32(m.u32(node + 0x14)) for k, node in classes}
    begin, end = struct.unpack('<II', m.read(r + 0xb8, 8))
    out['pairs'] = [tuple(s32(v) for v in struct.unpack('<II', m.read(a, 8))) for a in range(begin, end, 8)]
    return out


def common_stubs(m):
    vl.heap_stubs(m)

    def new(mm):      # whole 16-byte blocks are defined: the CRT string routines read aligned dwords past a NUL
        size = mm.args(1)[0] or 1
        return mm.alloc((size + 15) & ~15, define=True)
    m.stub(vl.CRT_NEW, new)
    m.stub(vl.CRT_MALLOC, new)
    m.stub(CRT_SIZED_DELETE, lambda mm: 0)
    vl.crt_state(m)
    m.import_guard()
    marker = m.alloc(16, define=True)
    m.stub(LOCALE_CTOR, lambda mm: (mm.write(mm.uc.reg_read(cm.UC_X86_REG_ECX), struct.pack('<II', marker, marker)),
                                    mm.uc.reg_read(cm.UC_X86_REG_ECX))[1], cm.stdcall_cleanup(m.text, LOCALE_CTOR))
    m.stub(LOCALE_CLASSIC, lambda mm: marker, 0)
    m.stub(LOCALE_EQ, lambda mm: 1, cm.stdcall_cleanup(m.text, LOCALE_EQ))
    m.stub(LOCALE_DTOR, lambda mm: 0, cm.stdcall_cleanup(m.text, LOCALE_DTOR))


# ---- families ---------------------------------------------------------------------------------------

LEX_STRINGS = [b'0', b'1', b'-1', b'+5', b'-0', b'+0', b'+1', b'00', b'01', b'-00', b'+001', b'10', b'2', b'007',
               b' 1', b'1 ', b'', b'-', b'+', b'--1', b'+-1', b'2147483647', b'2147483648', b'-2147483648',
               b'-2147483649', b'4294967295', b'4294967296', b'99999999999', b'0x10', b'1e3', b'12a', b'a',
               b'\t3', b'1.0', b'000000000000000000012', b'-000000000002147483648']


def lex_cases(rng):
    cases = list(LEX_STRINGS)
    for _ in range(400):
        kind = rng.random()
        if kind < 0.5:
            v = rng.choice([rng.randint(-2**31, 2**31 - 1), rng.randint(-1000, 1000), rng.randint(2**31 - 50, 2**33)])
            text = str(v).encode()
            if rng.random() < 0.1:
                text = b'+' + text.lstrip(b'-')
        else:
            alphabet = b'0123456789+- ab.\t'
            text = bytes(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        cases.append(text)
    return cases


def run_lexcast(m, nat, rng, fam):
    for kind, address in (('int', LEX_INT), ('bool', LEX_BOOL)):
        for text in lex_cases(rng):
            m.prepare(force=True)
            common_stubs(m)
            s = std_string(m, text)
            out = m.alloc(8, define=True)
            ok = m.call(address, [s, out]) & 0xff
            value = (s32(m.u32(out)) if kind == 'int' else m.read(out, 1)[0]) if ok else None
            fam.check((kind, text), (ok, value), nat.lexical(kind, text))


def row_columns(rng, index=None, bad=None):
    """61 columns of a synthetic row; bad = column index to spoil."""
    def num():
        r = rng.random()
        if r < 0.3:
            return rng.randint(0, 10)
        if r < 0.5:
            return -1
        if r < 0.9:
            return rng.randint(-1000, 100000)
        return rng.randint(-2**31, 2**31 - 1)
    cols = [str(index if index is not None else rng.randint(1, 5000)).encode()]
    name_kind = rng.random()
    name = ''.join(rng.choice('abcdefghij XYZ') for _ in range(rng.randint(0, 30))).encode()
    if name_kind < 0.6:
        cols.append(b'"' + name + b'"')
    elif name_kind < 0.7:
        cols.append(name)                                  # no quotes: the name stays empty
    elif name_kind < 0.8:
        cols.append(b'"' + name)                           # one quote
    elif name_kind < 0.9:
        cols.append(b'x"' + name + b'"')                   # quote not first
    else:
        cols.append(b'"' + name + b'"tail"')               # inner quote: up to the last one
    for i in range(2, 61):
        if i == 45:
            cols.append(rng.choice([b'0', b'1', b'+1', b'00', b'-0']))
        elif i in (54, 56) and rng.random() < 0.5:
            cols.append(b'-1')
        else:
            cols.append(str(num()).encode())
    if bad is not None:
        cols[bad] = rng.choice([b'x', b'', b'1.5', b' 7', b'2147483648']) if bad != 45 else rng.choice([b'2', b'-1', b'x'])
    return cols


def run_row(m, nat, rng, fam, cases):
    logs = []

    def throw(mm):
        # the catch funclet of 0x01170ca5: log (0x010d7e03), result byte 0, continue at 0x0117179c with
        # the frame's saved esp ([ebp-0x10])
        ebp = state['ebp']
        logs.append(s32(mm.u32(ebp + 8)))
        mm.write(ebp - 0x17, b'\0')
        mm.uc.reg_write(cm.UC_X86_REG_EBP, ebp)
        mm.uc.reg_write(cm.UC_X86_REG_ESP, mm.u32(ebp - 0x10))
        mm.uc.reg_write(cm.UC_X86_REG_EIP, PARSE_CONTINUE)
        return cm.REDIRECT
    state = {}
    for case in range(cases):
        m.prepare(force=True)
        common_stubs(m)
        m.stub(THROW_INT, throw, 0)
        m.stub(THROW_BOOL, throw, 0)
        table = m.alloc(0x110, define=True)
        head = empty_map(m, 0x14 + 0xd0)
        m.write(table + 0x108, struct.pack('<II', head, 0))
        kind = rng.random()
        bad = None
        if kind < 0.1:
            cols = row_columns(rng)[:rng.randint(0, 51)]           # too few columns
        else:
            bad = rng.randint(0, 60) if kind < 0.25 else None
            if bad in (1, 55, 57):
                bad = None                                         # never converted (name) / maybe unread
            cols = row_columns(rng, bad=bad)
            if kind > 0.97:
                cols += [b'extra'] * rng.randint(1, 5)              # more than 61: ignored
        rows = [cols]
        if kind > 0.9 and len(cols) >= 61:                         # a duplicate index keeps the first record
            dup = row_columns(rng, index=int(cols[0]))
            rows.append(dup)
        results = []
        logs.clear()
        for cols_ in rows:
            vec = string_vector(m, cols_)
            esp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000 - 4*(1 + 2)
            state['ebp'] = esp - 4
            results.append(m.call(PARSE_ROW, [case, vec], ecx=table) & 0xff)
        key = s32(int(rows[0][0])) if rows[0] and re.fullmatch(rb'[+-]?\d+', rows[0][0] or b'') else None
        client = {'results': results, 'size': m.u32(table + 0x10c)}
        if key is not None and -2**31 <= int(rows[0][0]) < 2**31:
            address = m.call(SKILL_LOOKUP, [key & 0xffffffff], ecx=table)
            client['record'] = client_record(m, address) if address != table + 0x38 else None
        # native: the same rows into a table
        native_results, first = [], None
        for cols_ in rows:
            status, rec = nat.parse(cols_)
            native_results.append(1 if status == 1 else 0)
            if status == 1 and first is None:
                first = native_record(rec)
        native = {'results': native_results, 'size': int(first is not None)}
        if 'record' in client:
            native['record'] = first
        fam.check(case, client, native)


# ---- the hero's skills (skill_use) ------------------------------------------------------------------

HERO, ATTR, ATTR8, HOTKEYS = 0x0a39d754, 0x01d1df1c, 0x01d1df18, 0x01d1df5c
GFX_MGR, CLASS_INDEX, BASE_SKILL = 0x00ac3bf7, 0x0095f5cc, 0x00bb1c32
MASTER_GET, TREE_GET_MAP, TREE_GET_NODE = 0x0095f998, 0x0095fb5b, 0x0095fb49
MASTER_HAS, MASTER_VALUE, TREE_MAP, TREE_NODE, TREE_VALUE, TREE_LEARNED = (
    0x00bb1ea1, 0x00bb1ed0, 0x00c354b7, 0x00c2a236, 0x00b48a9e, 0x00c2a37a)
STATS_OK, MANA_OK, DELAY_START, DELAY_READY, DELAY_TICK, SPECIAL_OK = (
    0x0109228f, 0x01091692, 0x01696aca, 0x016969e9, 0x01696e06, 0x01096e55)
BUFF, BUFF_HERO = 0x01295ade, 0x0139f66e
BAR_FEED, ICON_DRAW = 0x00c58797, 0x01097130
DUMMY = vl.DUMMY
NODE = 0x0bf10000


class TableC(ctypes.Structure):
    _fields_ = [('records', ctypes.c_void_p), ('count', ctypes.c_size_t), ('capacity', ctypes.c_size_t)]


BASE_FN = ctypes.CFUNCTYPE(I32, ctypes.c_void_p, I32)
HAS_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, I32)
VALUE_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, I32, I32)
MAP_FN = ctypes.CFUNCTYPE(I32, ctypes.c_void_p, I32, I32)
TVALUE_FN = ctypes.CFUNCTYPE(I32, ctypes.c_void_p, I32, I32)
BUFF_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, I32)
USABLE_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, I32)


class EnvC(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('table', ctypes.POINTER(TableC)), ('class_index', I32),
                ('base_skill', BASE_FN), ('master_has_delay', HAS_FN), ('master_value', VALUE_FN),
                ('tree_map', MAP_FN), ('tree_node', HAS_FN), ('tree_value', TVALUE_FN), ('tree_learned', HAS_FN),
                ('buff', BUFF_FN)]


class HeroC(ctypes.Structure):
    _fields_ = [('class_index', I32), ('strength', U16), ('agility', U16), ('vitality', U16), ('energy', U16),
                ('command', U16), ('mana', I32), ('ag', I32), ('mana_bonus', U8), ('elemental', I32),
                ('current', U8), ('mounted', U8), ('mount_kind', U8), ('count', ctypes.c_int),
                ('skills', U16*0x3a1), ('timers', I32*0x3a1)]


class HotkeysC(ctypes.Structure):
    _fields_ = [('selected', I32), ('slots', I32*10)]


class BarSlotC(ctypes.Structure):
    _fields_ = [('skill', I32), ('use', U8), ('damage_type', I32)]


class BarC(ctypes.Structure):
    _fields_ = [('dirty', U8), ('select_skill', I32), ('select_use', U8), ('select_slot', I32), ('elemental', I32),
                ('slots', BarSlotC*10)]


class IconC(ctypes.Structure):
    _fields_ = [('bitmap', I32), ('u', ctypes.c_float), ('v', ctypes.c_float), ('uw', ctypes.c_float),
                ('vh', ctypes.c_float)]


def snapshot_records(snap):
    """RecordC of every Skill(Kor) record of the snapshot (the scalar fields; the inner containers are not
    in the snapshot)."""
    out = []
    for key, node in snap.tree(SKILL_TABLE + 0x108):
        r = node + 0x14
        rec = RecordC()
        rec.skip = snap.read(r, 1)[0]
        for name, off, kind in RECORD_FIELDS:
            setattr(rec, name, snap.i32(r + off) if kind == 'i' else snap.read(r + off, 1)[0])
        rec.index = key
        out.append(rec)
    return out


class Case:
    """The answers a case gives to the stubbed managers, shared by the client stubs and the C callbacks."""

    def __init__(self, rng, keys):
        self.rng = rng
        self.class_index = rng.randint(0, 7)
        self.base = {}
        self.master_has = {}
        self.master_value = {}
        self.tree_map = {}
        self.tree_node = {}
        self.tree_values = {}
        self.tree_learned = {}
        self.buffs = {0: set(), 1: set(), 2: set()}
        self.usable = {}
        self.special = {}
        self.keys = keys

    def mapped(self, skill):
        return self.tree_map.get(skill, -1)

    def base_of(self, skill):
        return self.base.get(skill, skill)

    def callbacks(self):
        self._keep = [
            BASE_FN(lambda u, s: self.base_of(s)),
            HAS_FN(lambda u, s: int(self.master_has.get(s, 0))),
            VALUE_FN(lambda u, s, w: self.master_value.get(s, 0.0)),
            MAP_FN(lambda u, c, s: self.mapped(s)),
            HAS_FN(lambda u, s: int(s in self.tree_node)),
            TVALUE_FN(lambda u, s, i: self.tree_values.get((s, i), 0)),
            HAS_FN(lambda u, s: int(self.tree_learned.get(s, 1))),
            BUFF_FN(lambda u, l, b: int(b in self.buffs[l])),
        ]
        return self._keep


def make_env(table, case):
    cb = case.callbacks()
    env = EnvC(None, ctypes.pointer(table), case.class_index, *cb)
    return env


class SkillNative(Native):
    def __init__(self, work, lib=None):
        super().__init__(work, lib)
        L = self.lib
        L.mu_skill_table_add.argtypes = [ctypes.POINTER(TableC), ctypes.POINTER(RecordC)]
        L.mu_skill_stats_ok.argtypes = [ctypes.POINTER(EnvC), ctypes.POINTER(HeroC), I32]
        L.mu_skill_mana_ok.argtypes = [ctypes.POINTER(EnvC), ctypes.POINTER(HeroC), I32, I32, I32, I32,
                                       ctypes.POINTER(ctypes.c_int)]
        L.mu_skill_info_skill.argtypes = [I32]
        L.mu_skill_info_skill.restype = I32
        L.mu_skill_delay_start.argtypes = [ctypes.POINTER(EnvC), ctypes.POINTER(HeroC), I32, ctypes.POINTER(I32*4)]
        L.mu_skill_ready.argtypes = [ctypes.POINTER(EnvC), ctypes.POINTER(HeroC), ctypes.c_int]
        L.mu_skill_delay_tick.argtypes = [ctypes.POINTER(HeroC), I32]
        L.mu_skill_special_ok.argtypes = [ctypes.POINTER(EnvC), I32]
        L.mu_skill_bar_feed.argtypes = [ctypes.POINTER(EnvC), ctypes.POINTER(BarC), ctypes.POINTER(HeroC),
                                        ctypes.POINTER(HotkeysC), USABLE_FN, ctypes.c_void_p, ctypes.c_char_p,
                                        ctypes.c_size_t]
        L.mu_skill_icon_of.argtypes = [ctypes.POINTER(EnvC), I32, I32, ctypes.c_int, ctypes.c_float, ctypes.c_float,
                                       ctypes.POINTER(IconC)]
        L.mu_skill_tip_text_decode.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        L.mu_skill_tooltip_build.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        L.mu_skill_wrap.argtypes = [ctypes.c_void_p, ctypes.c_char_p, I32, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        L.mu_skill_tooltip_html.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p,
                                            ctypes.c_size_t]

    def table(self, records):
        t = TableC()
        for rec in records:
            self.lib.mu_skill_table_add(ctypes.byref(t), ctypes.byref(rec))
        return t


def float_stub(m, value_box, cleanup):
    """A client stub returning a float in st(0): fld dword [slot]; ret cleanup (a trampoline in the stub page,
    one per (call site of this helper, cleanup), reused across cases)."""
    import inspect
    key = (inspect.stack()[1].lineno, cleanup)
    cache = m.__dict__.setdefault('_float_trampolines', {})
    if key not in cache:
        slot = m._next_stub
        code = slot + 16
        m._next_stub += 32
        m.uc.mem_write(code, b'\xd9\x05' + struct.pack('<I', slot) +
                       (b'\xc2' + struct.pack('<H', cleanup) if cleanup else b'\xc3'))
        cache[key] = (slot, code, [None])
    slot, code, box = cache[key]
    box[0] = value_box

    def handler(mm):
        mm.uc.mem_write(slot, struct.pack('<f', box[0]()))
        mm.uc.reg_write(cm.UC_X86_REG_EIP, code)
        return cm.REDIRECT
    return handler


def skill_stubs(m, case, snap_keys=None):
    """Manager stubs shared by the skill families (answers from `case`)."""
    arg = lambda mm, i: s32(mm.args(i + 1)[i])
    m.stub(GFX_MGR, lambda mm: DUMMY, 0)
    for getter in (MASTER_GET, TREE_GET_MAP, TREE_GET_NODE):
        m.stub(getter, lambda mm: DUMMY, 0)
    m.stub(CLASS_INDEX, lambda mm: case.class_index, 0)
    m.stub(BASE_SKILL, lambda mm: case.base_of(arg(mm, 0)), 4)
    m.stub(MASTER_HAS, lambda mm: int(case.master_has.get(arg(mm, 0), 0)), 4)
    def master_value(mm):
        case._last_master = arg(mm, 0)
        return m.stubs_float_master(mm)
    m.stubs_float_master = float_stub(m, lambda: case.master_value.get(case._last_master, 0.0), 8)
    m.stub(MASTER_VALUE, master_value, 0)
    m.stub(TREE_MAP, lambda mm: case.mapped(arg(mm, 1)) & 0xffffffff, 8)

    def node(mm):
        s = arg(mm, 0)
        if s in case.tree_node:
            case._node = s
            return NODE
        return 0
    m.stub(TREE_NODE, node, 4)
    m.stub(TREE_VALUE, lambda mm: case.tree_values.get((case._node, arg(mm, 0)), 0) & 0xffffffff, 4)
    m.stub(TREE_LEARNED, lambda mm: int(case.tree_learned.get(arg(mm, 0), 1)), 4)
    m.stub(BUFF, lambda mm: int(arg(mm, 0) in case.buffs[case.list_of(mm.uc.reg_read(cm.UC_X86_REG_ECX))]), 4)
    m.stub(BUFF_HERO, lambda mm: int(arg(mm, 1) in case.buffs[2]), 0)


def write_hero(m, case, hero):
    """The hero object [0x0a39d754] and the attribute block [0x01d1df1c] / [0x01d1df18] = attr - 8."""
    h = m.alloc(0x3600, define=True)
    m.put32(HERO, h)
    m.write(h + 0x12, bytes([0]))
    m.write(h + 0x32, bytes([hero.current]))
    m.write(h + 0x38, bytes([hero.mounted, hero.mount_kind]))
    m.put32(h + 0x3268, hero.elemental)
    a = m.alloc(0x3000, define=True) + 8
    m.put32(ATTR, a)
    m.put32(ATTR8, a - 8)
    for off, value in ((0x18a, hero.strength), (0x18c, hero.agility), (0x18e, hero.vitality), (0x190, hero.energy),
                       (0x192, hero.command)):
        m.write(a + off, struct.pack('<H', value))
    m.write(a + 0x1e4, bytes([hero.count]))
    for i in range(hero.count):
        m.write(a + 0x1e6 + 2*i, struct.pack('<H', hero.skills[i]))
        m.put32(a + 0xccc + 4*i, hero.timers[i])
    m.write(a - 8 + 0x2ded, bytes([hero.mana_bonus]))
    case.character = h + 0x3254
    case.hero_buffs = h + 0x35ac
    case.list_of = lambda ecx: 0 if ecx == case.character + 0x358 else 1
    return h, a


def random_hero(rng, keys, case):
    hero = HeroC()
    hero.class_index = case.class_index
    for name in ('strength', 'agility', 'vitality', 'energy', 'command'):
        setattr(hero, name, rng.choice([0, rng.randint(0, 2000), rng.randint(0, 65535)]))
    hero.mana, hero.ag = rng.randint(0, 3000), rng.randint(0, 300)
    hero.mana_bonus = rng.randint(0, 255)
    hero.elemental = rng.randint(0, 6)
    hero.count = rng.randint(0, 40)
    for i in range(hero.count):
        hero.skills[i] = rng.choice(keys) if rng.random() < 0.9 else rng.randint(0, 3000)
        hero.timers[i] = rng.choice([0, 0, rng.randint(1, 30000), -rng.randint(1, 100)])
    hero.current = rng.randint(0, max(0, hero.count - 1)) if hero.count else 0
    hero.mounted = int(rng.random() < 0.2)
    hero.mount_kind = rng.choice([7, 7, 3])
    return hero


def run_req(m, nat, table, keys, rng, fam):
    for skill in keys + [0, 99999]:
        for _ in range(3):
            case = Case(rng, keys)
            case.class_index = rng.choice([0, 1, 1, 2, 3, 4, 5])
            m.prepare()
            skill_stubs(m, case)
            hero = random_hero(rng, keys, case)
            rec = next((r for r in table_records(table) if r.index == skill), None)
            if rec is not None and rng.random() < 0.5:    # stats around the requirements
                hero.strength = max(0, rec.req_strength + rng.randint(-1, 1)) & 0xffff
                hero.energy = max(0, rec.req_energy + rng.randint(-1, 1)) & 0xffff
                hero.agility = max(0, rec.req_dexterity + rng.randint(-1, 0)) & 0xffff
                hero.command = max(0, rec.req_command + rng.randint(-1, 0)) & 0xffff
                hero.vitality = max(0, rec.req_vitality + rng.randint(-1, 0)) & 0xffff
            write_hero(m, case, hero)
            client = m.call(STATS_OK, [skill], ecx=DUMMY) & 0xff
            env = make_env(table, case)
            fam.check((skill, case.class_index), client, nat.lib.mu_skill_stats_ok(env, hero, skill))


_records_cache = {}


def table_records(table):
    key = id(table)
    if key not in _records_cache:
        arr = ctypes.cast(table.records, ctypes.POINTER(RecordC))
        _records_cache[key] = [arr[i] for i in range(table.count)]
    return _records_cache[key]


def run_mana(m, nat, lang, h, table, keys, rng, fam):
    potions = []
    m.stub(0x00bb1d9d, lambda mm: 0, cm.stdcall_cleanup(m.text, 0x00bb1d9d))
    m.stub(0x0095f965, lambda mm: DUMMY, 0)
    for skill in keys + [0x3a, 0x28, 0x18b, 0x188]:
        case = Case(rng, keys)
        m.prepare()
        skill_stubs(m, case)
        m.stub(0x00bb1d9d, lambda mm: 0, cm.stdcall_cleanup(m.text, 0x00bb1d9d))
        hero = random_hero(rng, keys, case)
        base = rng.choice([skill, 0x18, case.base_of(skill)])
        for lst in (0,):
            for b in (6, 0x8f, 0x125, 0x127, 0x128, 0x126, 0x12a, 0x12b):
                if rng.random() < 0.2:
                    case.buffs[lst].add(b)
        h_obj, a = write_hero(m, case, hero)
        m.stub(0x0096169b, lambda mm: hero.mana & 0xffffffff, 0)
        m.stub(0x009616ba, lambda mm: hero.ag & 0xffffffff, 0)
        idx = rng.choice([-1, 3])
        m.stub(0x00b920bc, lambda mm: idx & 0xffffffff, 0)
        potions.clear()
        m.stub(0x00960420, lambda mm: potions.append(tuple(mm.args(2))) or 0, 0)
        this = m.alloc(0x20, define=True)
        m.write(this, struct.pack('<IIII', h_obj, case.character, skill, base))
        ok = m.call(MANA_OK, [], ecx=this) & 0xff
        client = (ok, potions[0] if potions else None)
        info = vl.Native.skill_info(lang, h, nat.lib.mu_skill_info_skill(skill), 0)
        mana, ag = (info[1], info[3]) if info else (0, 0)
        potion = ctypes.c_int()
        env = make_env(table, case)
        native_ok = nat.lib.mu_skill_mana_ok(env, hero, skill, base, mana, ag, ctypes.byref(potion))
        native = (native_ok, (idx & 0xffffffff, 0) if potion.value and idx != -1 else None)
        fam.check(skill, client, native)


def random_tree(case, rng, keys):
    for s in rng.sample(keys, min(len(keys), 40)):
        r = rng.random()
        if r < 0.3:
            case.master_has[s] = 1
            case.master_value[s] = rng.choice([0.5, 1.25, 3.0, rng.uniform(0, 20)])
        if r > 0.6:
            case.tree_node[s] = 1
            case.tree_values[(s, 0x3fb)] = rng.choice([0, 1, 2])
            case.tree_values[(s, 0x3fa)] = rng.choice([0, 500, 1000, rng.randint(0, 40000)])
        if 0.4 < r < 0.5:
            case.tree_map[s] = rng.choice(keys)
    for s in rng.sample(keys, min(len(keys), 20)):
        case.base[s] = rng.choice([0xdd, 0xde, s, rng.choice(keys)])


def delay_stubs(m, events):
    container = 0x0bf20000
    m.stub(0x0095c50b, lambda mm: mm.args(1)[0], 4)
    m.stub(0x00a06d72, lambda mm: 1, 0)
    m.stub(0x0095f144, lambda mm: container, 0)
    m.stub(0x0095eb91, lambda mm: 0, 0)
    m.stub(0x00c5870d, lambda mm: events.append(tuple(s32(v) for v in mm.args(2))) or 0, 8)
    m.stub(0x00a9a686, lambda mm: DUMMY, 0)
    m.stub(0x00a9b17f, lambda mm: 0, 4)


def read_timers(m, a, count):
    return [s32(m.u32(a + 0xccc + 4*i)) for i in range(count)]


def run_delay(m, nat, table, keys, rng, fams, cases):
    start, ready, tick = fams
    events = []
    for n in range(cases):
        case = Case(rng, keys)
        random_tree(case, rng, keys)
        m.prepare()
        skill_stubs(m, case)
        delay_stubs(m, events)
        hero = random_hero(rng, keys, case)
        if hero.count and rng.random() < 0.7:     # repeat a learned skill (several entries of one skill)
            for i in rng.sample(range(hero.count), min(3, hero.count)):
                hero.skills[i] = hero.skills[0]
        _, a = write_hero(m, case, hero)
        env = make_env(table, case)
        kind = n % 3
        if kind == 0:
            skill = hero.skills[0] if hero.count and rng.random() < 0.8 else rng.choice(keys)
            events.clear()
            m.call(DELAY_START, [skill])
            client = (read_timers(m, a, hero.count), events[:])
            out = (I32*4)()
            k = nat.lib.mu_skill_delay_start(env, hero, skill, ctypes.byref(out))
            native = ([hero.timers[i] for i in range(hero.count)], [(out[2*i], out[2*i + 1]) for i in range(k)])
            start.check((n, skill), client, native)
        elif kind == 1:
            if not hero.count:
                continue
            index = rng.randint(0, hero.count - 1)
            client = m.call(DELAY_READY, [index]) & 0xff
            ready.check((n, index), client, nat.lib.mu_skill_ready(env, hero, index))
        else:
            dt = rng.choice([1, 40, 100, rng.randint(0, 5000), -rng.randint(1, 50)])
            m.call(DELAY_TICK, [dt & 0xffffffff])
            client = read_timers(m, a, hero.count)
            nat.lib.mu_skill_delay_tick(hero, dt)
            tick.check((n, dt), client, [hero.timers[i] for i in range(hero.count)])


def run_special(m, nat, table, keys, rng, fam):
    specials = [0xdf, 0xe0, 0xe1, 0x120, 0x80b, 0x80c, 0x5df]
    for skill in keys + specials:
        for cls in (1, 5, rng.randint(0, 7)):
            case = Case(rng, keys)
            case.class_index = cls
            if rng.random() < 0.3:
                case.base[skill] = rng.choice(specials)
            if rng.random() < 0.5:
                case.buffs[2].update([0x12d, 0x145][:rng.randint(1, 2)])
            m.prepare()
            skill_stubs(m, case)
            write_hero(m, case, random_hero(rng, keys, case))
            mgr = m.alloc(0x100, define=True)
            client = m.call(SPECIAL_OK, [skill], ecx=mgr) & 0xff
            fam.check((skill, cls), client, nat.lib.mu_skill_special_ok(make_env(table, case), skill))


def build_map(m, items, node_size=0x18):
    """A valid MSVC std::map<int,int> (key +0x10, value +0x14) with parent links: (head, size)."""
    head = empty_map(m, node_size)
    items = sorted(items)
    nodes = []

    def build(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        node = m.alloc(node_size, define=True)
        nodes.append(node)
        left = build(lo, mid, node)
        right = build(mid + 1, hi, node)
        m.write(node, struct.pack('<III', left, parent, right) + b'\x01\x00\0\0' +
                struct.pack('<ii', items[mid][0], items[mid][1]))
        return node
    root = build(0, len(items), head)
    if items:
        leftmost = root
        while m.u32(leftmost) != head:
            leftmost = m.u32(leftmost)
        rightmost = root
        while m.u32(rightmost + 8) != head:
            rightmost = m.u32(rightmost + 8)
        m.write(head, struct.pack('<III', leftmost, root, rightmost))
    return head, len(items)


class GfxRecorder:
    """The GFx value helpers the bar feed calls, recorded as nested Python values."""

    def __init__(self, m):
        self.values = {}
        self.invokes = []
        arg = lambda mm, i: mm.args(i + 1)[i]
        m.stub(0x00aad26b, lambda mm: self.values.__setitem__(mm.uc.reg_read(cm.UC_X86_REG_ECX), None)
               or mm.uc.reg_read(cm.UC_X86_REG_ECX), 0)
        m.stub(0x00aad299, lambda mm: 0, 0)
        m.stub(0x00c8f5f4, lambda mm: self.values.__setitem__(arg(mm, 0), {}) or arg(mm, 0), 4)
        m.stub(0x00c8f9cf, lambda mm: self.values.__setitem__(arg(mm, 0), []) or arg(mm, 0), 4)

        def member(mm, kind):
            obj, name, value = mm.args(3)
            name = mm.cstr(name).decode()
            if kind == 'int':
                v = s32(value)
            elif kind == 'bool':
                v = bool(value & 0xff)
            else:
                v = self.values.get(value)
            self.values[obj][name] = v
            return 0
        m.stub(0x00ae957f, lambda mm: member(mm, 'int'), 12)
        m.stub(0x00aecd73, lambda mm: member(mm, 'bool'), 12)
        m.stub(0x00ae497d, lambda mm: member(mm, 'value'), 12)

        def push(mm):
            index, value = mm.args(2)
            arr = self.values[mm.uc.reg_read(cm.UC_X86_REG_ECX)]
            while len(arr) <= index:
                arr.append(None)
            arr[index] = self.values.get(value)
            return 0
        m.stub(0x00ab27a6, push, 8)

        def invoke(mm):
            name, value = mm.args(2)
            self.invokes.append((mm.cstr(name).decode(), self.values.get(value)))
            return 0
        m.stub(0x00c8fac2, invoke, 8)


def run_feed(m, nat, table, keys, rng, fam, cases):
    for n in range(cases):
        case = Case(rng, keys)
        m.prepare(force=True)
        common_stubs(m)
        skill_stubs(m, case)
        rec = GfxRecorder(m)
        hero = random_hero(rng, keys, case)
        write_hero(m, case, hero)
        pool = rng.sample(keys, 12) + [0, 0, 0, 99999]
        hot = HotkeysC()
        slots = {}
        for i in range(10):
            if rng.random() < 0.8:
                hot.slots[i] = rng.choice(pool)
                slots[i] = hot.slots[i]
        hot.selected = rng.choice([0, rng.choice(pool), hot.slots[rng.randint(0, 9)]])
        for s in pool:
            case.usable[s] = rng.random() < 0.7
            case.special[s] = rng.random() < 0.9
        # the hotkey manager: +0 selected, +0xc map<slot, skill> (only the assigned slots)
        hk_head, hk_size = build_map(m, list(slots.items()))
        m.put32(HOTKEYS, hot.selected)
        m.write(HOTKEYS + 0xc, struct.pack('<II', hk_head, hk_size))
        m.stub(0x0107e918, lambda mm: DUMMY, 0)
        m.stub(0x010918c7, lambda mm: int(case.usable.get(s32(mm.args(1)[0]), False)), 4)
        m.stub(0x0095f861, lambda mm: DUMMY, 0)
        m.stub(0x01096e55, lambda mm: int(case.special.get(s32(mm.args(1)[0]), True)), 4)
        bar = m.alloc(0x40, define=True)
        vec = m.alloc(12*10, define=True)
        m.put32(bar + 0x30, vec)
        m.put32(bar + 0x34, vec + 120)
        m.put32(bar + 0x38, vec + 120)
        nbar = BarC()
        usable = USABLE_FN(lambda u, s: int(case.usable.get(s, False) and case.special.get(s, True)))
        client_calls, native_calls = [], []
        for step in range(3):
            if step == 2:          # change one input: a usability, the elemental or a slot
                what = rng.randint(0, 2)
                if what == 0:
                    s = rng.choice(pool)
                    case.usable[s] = not case.usable.get(s, False)
                elif what == 1:
                    hero.elemental = (hero.elemental + 1) % 7
                    m.put32(m.u32(HERO) + 0x3268, hero.elemental)
            rec.invokes.clear()
            m.call(BAR_FEED, [], ecx=bar)
            client_calls.append(json.dumps(rec.invokes[0][1], separators=(',', ':')) if rec.invokes else None)
            buf = ctypes.create_string_buffer(4096)
            changed = nat.lib.mu_skill_bar_feed(make_env(table, case), nbar, hero, hot, usable, None, buf, 4096)
            native_calls.append(json.dumps(json.loads(buf.value.decode()), separators=(',', ':')) if changed else None)
        fam.check(n, client_calls, native_calls)


def run_icon(m, nat, table, keys, rng, fam):
    draws = []
    for skill in keys:
        case = Case(rng, keys)
        m.prepare()
        skill_stubs(m, case)
        hero = random_hero(rng, keys, case)
        if rng.random() < 0.3 and hero.count:
            hero.skills[0] = skill
        write_hero(m, case, hero)
        learned = skill if rng.random() < 0.7 else 0
        base = rng.choice([skill, rng.choice(keys)])
        if rng.random() < 0.05:
            base, learned = rng.randint(0x78, 0x7c), 0
        usable = rng.random() < 0.7
        case.tree_learned[learned or base] = int(rng.random() < 0.7)
        entry = m.alloc(16, define=True)
        m.write(entry, struct.pack('<II', base, learned) + b'\x00' * 8)
        m.stub(0x01096aa7, lambda mm: entry, 4)
        m.stub(0x0107e918, lambda mm: DUMMY, 0)
        m.stub(0x010918c7, lambda mm: int(usable), 4)
        m.stub(0x01096e55, lambda mm: 1, 4)
        draws.clear()
        m.stub(0x0184dcb1, lambda mm: draws.append(('bitmap', mm.args(1)[0],
                                                     [cm.bits_f(w) for w in mm.args(12)[1:]])) or 0, 0)
        m.stub(0x00f2bb92, lambda mm: DUMMY, 0)
        m.stub(0x00f2bf9a, lambda mm: DUMMY, 0)
        m.stub(0x00f18574, lambda mm: draws.append(('delay', s32(mm.args(1)[0]))) or 0, 20)
        cw, ch = rng.choice([(20.0, 28.0), (32.0, 32.0), (25.6, 25.6)])
        x, y, w, h = 100.0, 200.0, rng.choice([0.0, 40.0]), rng.choice([0.0, 50.0])
        mgr = m.alloc(0x100, define=True)
        m.call(ICON_DRAW, [0, cm.fbits(x), cm.fbits(y), cm.fbits(cw), cm.fbits(ch), cm.fbits(w), cm.fbits(h)], ecx=mgr)
        icon = IconC()
        native = []
        if nat.lib.mu_skill_icon_of(make_env(table, case), base, learned, int(usable), cw, ch, ctypes.byref(icon)):
            dw, dh = (w if w != 0.0 else cw), (h if h != 0.0 else ch)
            native.append(('bitmap', icon.bitmap, [x, y, dw, dh, icon.u, icon.v, icon.uw, icon.vh, 1.0, 1.0, 0.0]))
        index = -1
        shown = learned or base
        if learned:
            for i in range(hero.count):
                if hero.skills[i] == learned:
                    index = i
                    break
        if index >= 0:
            native.append(('delay', index))
        client = [(d[0], d[1], [cm.f32(v) for v in d[2]]) if d[0] == 'bitmap' else d for d in draws]
        # RenderBitmap's words: x, y, w, h, u, v, uw, vh as floats, then two ints and a float
        client = [(d[0], d[1], d[2][:8] + [float(cm.fbits(d[2][8]) if False else d[2][8])] + d[2][9:]) if d[0] == 'bitmap'
                  else d for d in client]
        fam.check((skill, base, learned, usable), normalise_draws(client), normalise_draws(native))


def normalise_draws(draws):
    out = []
    for d in draws:
        if d[0] == 'bitmap':
            vals = list(d[2])
            out.append(('bitmap', d[1], [round(v, 6) if isinstance(v, float) else v for v in vals[:8]]))
        else:
            out.append(d)
    return out


# ---- tooltip (skill_tooltip) ------------------------------------------------------------------------

TIP_BUILD, TIP_POPUP, TIP_HEADER, TIP_HANDLER = 0x0117da56, 0x00c1f2b0, 0x10b3efb0, 0x00ba9278
TEXT_LIST, TEXT_COLOR, TEXT_BOLD = 0x10c76988, 0x10c7b938, 0x10c7ba78
TIP_SPRINTF, MBCLEN, FONT_GET, FONT_DC, STRTOK = 0x009619dd, 0x01994240, 0x011a07b2, 0x011a08fd, 0x01983c08
WRAP_CUT, TEXT_SCALE, DAMAGE_BONUS = 0x011ff794, 0x06fbcd94, 0x06fb4528
SENTINEL = 77
STREAM_CTOR, STREAM_PUT_STRING, STREAM_PUT_CSTR, STREAM_STR, STREAM_DTOR = 0x969613, 0x94437f, 0x944605, 0x96a5b7, 0x969a1b


class TipTextC(ctypes.Structure):
    _fields_ = [('skill', U16), ('name', ctypes.c_char*256), ('name_color', I32), ('condition1', I32),
                ('text1', ctypes.c_char*256), ('color1', I32), ('condition2', I32), ('text2', ctypes.c_char*256),
                ('color2', I32), ('value_a', I32), ('value_b', I32), ('value_float', I32), ('value_cap', I32)]


TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, I32)
TIP_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, U16)
INFO_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, I32, ctypes.POINTER(I32), ctypes.POINTER(I32), ctypes.POINTER(I32))
FLOAT1_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, I32)
FORMULA_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, I32, I32, I32)
MEASURE_FN = ctypes.CFUNCTYPE(I32, ctypes.c_void_p, ctypes.c_char_p, I32)


class TipEnvC(ctypes.Structure):
    _fields_ = [('skills', ctypes.POINTER(EnvC)), ('user', ctypes.c_void_p), ('text', TEXT_FN), ('tip', TIP_FN),
                ('info', INFO_FN), ('master_is', HAS_FN), ('master_kind', HAS_FN), ('master_float', FLOAT1_FN),
                ('formula', FORMULA_FN), ('measure', MEASURE_FN), ('text_scale', ctypes.c_float)]


class TipInputC(ctypes.Structure):
    _fields_ = [('base', I32), ('learned', I32), ('stamped', U8), ('imprint_level', I32), ('weapon_index', ctypes.c_int16),
                ('weapon_word', U16), ('skill_damage', I32), ('option_13', ctypes.c_float), ('option_7e', ctypes.c_float),
                ('damage_bonus', I32), ('strength', U16), ('agility', U16), ('vitality', U16), ('energy', U16),
                ('command', U16), ('stat_19c', U16)]


class TipC(ctypes.Structure):
    _fields_ = [('lines', (ctypes.c_char*256)*80), ('color', I32*80), ('bold', I32*80), ('set', U8*80),
                ('count', ctypes.c_int), ('mastery', I32)]


def char_width(byte):
    """The modelled GetTextExtentPointA advance of a byte (the client asks the interface font)."""
    return 4 + (byte * 7) % 5


def measure_bytes(text):
    return sum(char_width(b) for b in text)


def sprintf_model(m, buf, fmt, args):
    """The client's sprintf (0x009619dd -> vsprintf) for the conversions the tables use: d i u x X o c (a
    word), e E f F g G (a double), s (a pointer), %%; flags, width and precision.  args: the stack words."""
    out, i, k = [], 0, 0
    spec = re.compile(rb'%([-+ #0]*\d*(?:\.\d+)?)(?:l|h)*([diuxXocfFeEgGs%])')
    while i < len(fmt):
        mt = spec.match(fmt, i) if fmt[i:i + 1] == b'%' else None
        if not mt:
            if fmt[i:i + 1] == b'%':          # a lone '%' at the end: nothing
                break
            out.append(fmt[i:i + 1])
            i += 1
            continue
        flags, conv = mt.group(1).decode(), mt.group(2).decode()
        if conv == '%':
            out.append(b'%')
        elif conv in 'diuxXoc':
            v = args[k]
            k += 1
            if conv in 'di':
                v = s32(v)
                out.append(('%' + flags + 'd') % v).encode() if False else out.append((('%' + flags + 'd') % v).encode())
            elif conv == 'c':
                out.append((('%' + flags + 'c') % chr(v & 0xff)).encode('latin1'))
            else:
                out.append((('%' + flags + conv) % v).encode())
        elif conv in 'fFeEgG':
            v = struct.unpack('<d', struct.pack('<II', args[k], args[k + 1]))[0]
            k += 2
            out.append((('%' + flags + conv) % v).encode())
        else:
            s = m.cstr(args[k]) if args[k] else b'(null)'
            k += 1
            out.append((('%' + flags + 's') % s.decode('latin1')).encode('latin1'))
        i = mt.end()
    data = b''.join(out)
    m.write(buf, data + b'\0')
    return len(data)


def tip_records(game_root, records, rng):
    """SkillTooltipText records: the installed file's (decoded locally) or synthetic ones."""
    if game_root:
        path = Path(game_root)/'Data/Local/skilltooltiptext.bmd'
        tool = ROOT/'native/build/mu-data'
        if path.exists():
            if not tool.exists():
                subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/mu-data'], check=True)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'stt.bin'
                subprocess.run([str(tool), 'decode', str(path), '--out', str(out)], check=True, capture_output=True)
                raw = out.read_bytes()
            count = struct.unpack_from('<I', raw)[0]
            return [raw[4 + 808*i:4 + 808*(i + 1)] for i in range(count)], 'installed'
    out = []
    words = ['fire', 'deal', 'damage', 'to', 'the', 'target', 'party', 'members', '%', 'Rate', '#']
    for r in rng.sample(records, min(300, len(records))):
        rec = bytearray(808)
        struct.pack_into('<H', rec, 0, r.index)
        name = ('Skill %d' % r.index).encode()
        rec[2:2 + len(name)] = name
        struct.pack_into('<ii', rec, 0x104, rng.randint(0, 22), rng.choice([0, 0, 1, 2, 3]))
        text = ' '.join(rng.choice(words) for _ in range(rng.randint(0, 40))).replace('%', '%d%%')
        text = text[:250].encode()
        rec[0x10c:0x10c + len(text)] = text
        struct.pack_into('<ii', rec, 0x20c, rng.randint(0, 22), rng.choice([0, 1, 2, -1]))
        text2 = ' '.join(rng.choice(words[:8]) for _ in range(rng.randint(0, 20))).encode()[:250]
        rec[0x214:0x214 + len(text2)] = text2
        struct.pack_into('<iiiii', rec, 0x314, rng.randint(0, 22), rng.choice([-1, -1, 70057, 10001]),
                         rng.choice([-1, 0, 0]), rng.choice([0, 1]), rng.choice([-1, 100, 5]))
        out.append(bytes(rec))
    return out, 'synthetic'


def tip_machine_setup(m):
    """The text list (outside the image: a runtime module's) and the runtime header page."""
    if not getattr(m, '_tip_mapped', False):
        m.uc.mem_map(0x10c76000, 0x6000, cm.UC_PROT_ALL)
        m.uc.mem_map(0x10b3e000, 0x1000, cm.UC_PROT_ALL)
        m.uc.mem_write(0x10b3e000, b'\xc3'*0x1000)
        m._tip_mapped = True


class StreamModel:
    def __init__(self, m):
        self.streams = {}
        ecx = lambda: m.uc.reg_read(cm.UC_X86_REG_ECX)  # noqa: E731

        def ctor(mm):
            self.streams[ecx()] = bytearray()
            self.streams[ecx() + 0x10] = self.streams[ecx()]
            return ecx()

        def put_string(mm):
            stream, string = mm.args(2)
            self.streams[stream] += mm.std_string(string)
            return stream

        def put_cstr(mm):
            stream, text = mm.args(2)
            self.streams[stream] += mm.cstr(text)
            return stream

        def str_(mm):
            ret = mm.args(1)[0]
            write_std_string(mm, ret, bytes(self.streams[ecx()]))
            return ret
        # the Boost.Format-style formatter the HTML line builder 0x00ab4dc0 uses (as scripts/validate_hud.py)
        self.formats = {}

        def format_ctor(mm):
            self.formats[ecx()] = [mm.cstr(mm.args(1)[0]), []]
            return ecx()

        def format_arg(mm):
            self.formats[ecx()][1].append(mm.std_string(mm.args(1)[0]))
            return ecx()

        def format_str(mm):
            fmt, args = self.formats[ecx()]
            parts = fmt.split(b'%s')
            if len(parts) != len(args) + 1:
                return mm.fail('format arity')
            ret = mm.args(1)[0]
            write_std_string(mm, ret, parts[0] + b''.join(a + p for a, p in zip(args, parts[1:])))
            return ret
        for address, fn, cleanup in ((STREAM_CTOR, ctor, 4), (STREAM_PUT_STRING, put_string, 0),
                                     (STREAM_PUT_CSTR, put_cstr, 0), (STREAM_STR, str_, 4),
                                     (STREAM_DTOR, lambda mm: 0, 0), (0x96e8c7, format_ctor, 4),
                                     (0x96c702, format_arg, 4), (0x97258c, format_str, 4), (0x96f4ae, lambda mm: 0, 0)):
            m.stub(address, fn, cleanup)


def write_std_string(m, obj, value):
    if len(value) < 16:
        m.write(obj, value + b'\0'*(16 - len(value)))
        m.write(obj + 0x10, struct.pack('<II', len(value), 15))
    else:
        buf = m.alloc(len(value) + 1, define=True)
        m.write(buf, value + b'\0')
        m.write(obj, struct.pack('<I', buf) + bytes(12))
        m.write(obj + 0x10, struct.pack('<II', len(value), len(value)))


def wrap_stubs(m, scale):
    ptd = m.alloc(0x400, define=True)          # the CRT's per-thread data (__acrt_getptd): strtok's context
    m.stub(0x019a4ba6, lambda mm: ptd, 0)
    m.stub(TIP_SPRINTF, lambda mm: sprintf_model(mm, *(lambda w: (w[0], mm.cstr(w[1]), w[2:]))(mm.args(16))), 0)
    m.stub(MBCLEN, lambda mm: 1, 0)
    m.stub(FONT_GET, lambda mm: DUMMY, 0)
    m.stub(FONT_DC, lambda mm: 0x1234, 0)

    def extent(mm, words):
        hdc, text, n, size = words
        mm.write(size, struct.pack('<ii', measure_bytes(mm.read(text, n)), 12))
        return 1
    m.handlers['GetTextExtentPointA'] = extent
    m.putf(TEXT_SCALE, scale)


def tip_stubs(m, case, tip_state):
    arg = lambda mm, i: mm.args(i + 1)[i]
    m.stub(TIP_SPRINTF, lambda mm: sprintf_model(mm, *(lambda w: (w[0], mm.cstr(w[1]), w[2:]))(mm.args(16))), 0)
    m.stub(TIP_HEADER, lambda mm: 0, 0)
    m.stub(TIP_HANDLER, lambda mm: DUMMY + 0x100, 0)
    m.stub(TIP_POPUP, lambda mm: tip_state.update(popup=tuple(mm.args(2))) or 0, 8)
    m.stub(0x00a01692, lambda mm: tip_state['damage'] & 0xffffffff, 4)
    m.stub(0x009953ef, lambda mm: DUMMY, 0)
    opt = float_stub(m, lambda: tip_state['options'].get(tip_state['_opt'], 0.0), 4)
    m.stub(0x009e0782, lambda mm: (tip_state.__setitem__('_opt', arg(mm, 0)), opt(mm))[1], 0)
    m.stub(0x00bb1e55, lambda mm: int(case.master_is.get(s32(arg(mm, 0)), 0)), 4)
    m.stub(0x00bb1df9, lambda mm: case.master_kind.get(s32(arg(mm, 0)), 0), 4)
    mf = float_stub(m, lambda: case.master_float.get(case._mf, 0.0), 4)
    m.stub(0x00bb1ca1, lambda mm: (setattr(case, '_mf', s32(arg(mm, 0))), mf(mm))[1], 0)
    m.stub(0x00bb1f4a, lambda mm: 0, 12)
    m.stub(0x00966c42, lambda mm: DUMMY, 0)
    fm = float_stub(m, lambda: formula_model(*case._fm), 0)
    m.stub(0x0117b5eb, lambda mm: (setattr(case, '_fm', tuple(s32(v) for v in mm.args(4)[1:])), fm(mm))[1], 0)
    m.stub(0x00bb1d9d, lambda mm: 0, cm.stdcall_cleanup(m.text, 0x00bb1d9d))


def formula_model(quotient, remainder, stat):
    return struct.unpack('<f', struct.pack('<f', quotient * 0.5 + remainder * 0.25 + stat / 7.0))[0]


def build_tip_map(m, raws):
    """The SkillTooltipText object: map<u16, record*> at +4 (insert: the first record of a key stays)."""
    seen = {}
    for raw in raws:
        key = struct.unpack_from('<H', raw)[0]
        if key not in seen:
            address = m.alloc(808, define=True)
            m.write(address, raw)
            seen[key] = address
    head, size = build_map(m, list(seen.items()))
    obj = m.alloc(0x20, define=True)
    m.write(obj + 4, struct.pack('<II', head, size))
    return obj, seen


def run_tooltip(m, nat, lang, h, snap, table, keys, records, rng, fam, args):
    raws, source = tip_records(args.game_root, records, rng)
    fam.source = source
    decoded = {}
    for raw in raws:
        t = TipTextC()
        nat.lib.mu_skill_tip_text_decode(raw, ctypes.byref(t))
        decoded.setdefault(t.skill, t)
    text_cache = {}

    def gtext(u, index):
        if index not in text_cache:
            text_cache[index] = ctypes.c_char_p(lang.lib.mu_lang_text(h, index))
        return ctypes.cast(text_cache[index], ctypes.c_void_p).value

    tip_skills = sorted(decoded)
    for n, skill_key in enumerate(tip_skills):
        case = Case(rng, keys)
        case.class_index = rng.choice([0, 0, 2])
        case.master_is, case.master_kind, case.master_float = {}, {}, {}
        state = {'damage': rng.choice([0, rng.randint(1, 5000)]), 'options': {0x13: rng.choice([0.0, 12.5]),
                                                                            0x7e: rng.choice([0.0, 3.75])}}
        if rng.random() < 0.3:
            case.tree_node[skill_key] = 1
            case.tree_values[(skill_key, 0x3fb)] = rng.choice([0, 1])
            case.tree_values[(skill_key, 0x3fa)] = rng.choice([0, 500, 99999])
        elif rng.random() < 0.3:
            case.master_is[skill_key] = 1
            case.master_kind[skill_key] = rng.choice([1, 2])
            case.master_float[skill_key] = rng.choice([0.5, 2.0, 7.25])
        m.prepare(force=True)
        tip_machine_setup(m)
        common_stubs(m)
        skill_stubs(m, case)
        tip_stubs(m, case, state)
        wrap_stubs(m, 1.0)
        tip_obj, _ = build_tip_map(m, raws)
        hero = random_hero(rng, keys, case)
        h_obj, a = write_hero(m, case, hero)
        inp = TipInputC()
        inp.base = skill_key if rng.random() < 0.8 else rng.choice(keys)
        inp.learned = rng.choice([0, skill_key, skill_key])
        if inp.learned == 0:
            inp.base = skill_key
        inp.stamped = rng.choice([0, 1])
        inp.imprint_level = rng.choice([0, 0, rng.randint(1, 300)])
        inp.weapon_index, inp.weapon_word = rng.choice([(-1, 0), (3, 0x42), (3, 7)])
        inp.skill_damage = state['damage']
        inp.option_13, inp.option_7e = state['options'][0x13], state['options'][0x7e]
        inp.damage_bonus = rng.choice([0, 17])
        inp.strength, inp.agility, inp.vitality = hero.strength, hero.agility, hero.vitality
        inp.energy, inp.command = hero.energy, hero.command
        inp.stat_19c = rng.randint(0, 100)
        m.write(h_obj + 0x19ac, struct.pack('<h', inp.weapon_index))
        m.write(a - 8 + 0x1bb8, struct.pack('<H', inp.weapon_word))
        m.write(a + 0x19c, struct.pack('<H', inp.stat_19c))
        m.put32(DAMAGE_BONUS, inp.damage_bonus)
        m.uc.mem_write(TEXT_LIST, b'\xab'*(80*0xff))
        m.uc.mem_write(TEXT_COLOR, struct.pack('<i', SENTINEL)*80)
        m.uc.mem_write(TEXT_BOLD, struct.pack('<i', SENTINEL)*80)
        entry = m.alloc(16, define=True)
        m.write(entry, struct.pack('<II', inp.base, inp.learned) + bytes([inp.stamped]) + bytes(7))
        state.pop('popup', None)
        m.call(TIP_BUILD, [entry, inp.imprint_level & 0xffffffff], ecx=tip_obj)
        if 'popup' in state:
            count, mastery = state['popup']
            lines = [m.read(TEXT_LIST + 0xff*i, 0xff).split(b'\0')[0] for i in range(count)]
            colors = list(struct.unpack('<80i', m.read(TEXT_COLOR, 320)))[:count]
            bolds = list(struct.unpack('<80i', m.read(TEXT_BOLD, 320)))[:count]
            client = {'count': count, 'mastery': mastery & 0xff, 'lines': lines, 'colors': colors, 'bolds': bolds}
        else:
            client = None
        # native
        env = make_env(table, case)
        cbs = [TEXT_FN(gtext), TIP_FN(lambda u, k: ctypes.addressof(decoded[k]) if k in decoded else None),
               INFO_FN(lambda u, s, pm, pd, pa: info_cb(lang, h, s, pm, pd, pa)),
               HAS_FN(lambda u, s: int(case.master_is.get(s, 0))), HAS_FN(lambda u, s: case.master_kind.get(s, 0)),
               FLOAT1_FN(lambda u, s: case.master_float.get(s, 0.0)), FORMULA_FN(lambda u, q, r, s: formula_model(q, r, s)),
               MEASURE_FN(lambda u, t, k: measure_bytes(ctypes.string_at(t, k)))]
        tenv = TipEnvC(ctypes.pointer(env), None, *cbs, 1.0)
        tip = TipC()
        if nat.lib.mu_skill_tooltip_build(ctypes.byref(tenv), ctypes.byref(inp), ctypes.byref(tip)):
            count = tip.count
            native = {'count': count, 'mastery': tip.mastery,
                      'lines': [bytes(tip.lines[i]).split(b'\0')[0][:0xfe] for i in range(count)],
                      'colors': [tip.color[i] if tip.set[i] & 1 else SENTINEL for i in range(count)],
                      'bolds': [tip.bold[i] if tip.set[i] & 2 else SENTINEL for i in range(count)]}
        else:
            native = None
        fam.check((skill_key, inp.base, inp.learned), client, native)


def info_cb(lang, h, skill, pm, pd, pa):
    info = vl.Native.skill_info(lang, h, skill, 0)
    pm[0], pd[0], pa[0] = (info[1], info[2], info[3]) if info else (0, 0, 0)


def run_wrap(m, nat, rng, fam, cases):
    words = ['a', 'deal', 'damage', 'to', 'targets', 'Wizard', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', '#', '##', ' ', '%']
    for n in range(cases):
        m.prepare(force=True)
        tip_machine_setup(m)
        common_stubs(m)
        scale = rng.choice([1.0, 0.75, 1.3333])
        wrap_stubs(m, scale)
        text = ' '.join(rng.choice(words) for _ in range(rng.randint(0, 60))).encode()[:0x1ff]
        width = rng.choice([0x96, 0xc8, 0x10, 40, 300])
        out = m.alloc(11*0x100, define=True)
        m.write(out, bytes(11*0x100))
        src = m.alloc(len(text) + 16, define=True)
        m.write(src, text + b'\0'*16)
        count = s32(m.call(WRAP_CUT, [out, 10, 0x100, src, width, 1, 0x23, 0, 0]))
        client = (count, [m.read(out + 0x100*i, 0x100).split(b'\0')[0] for i in range(min(max(count, 0), 11))])
        buf = ctypes.create_string_buffer(11*0x100)
        cbs = TipEnvC(None, None, TEXT_FN(), TIP_FN(), INFO_FN(), HAS_FN(), HAS_FN(), FLOAT1_FN(), FORMULA_FN(),
                      MEASURE_FN(lambda u, t, k: measure_bytes(ctypes.string_at(t, k))), scale)
        k = nat.lib.mu_skill_wrap(ctypes.byref(cbs), text, width, buf, 10, 0x100)
        native = (k, [buf.raw[0x100*i:0x100*(i + 1)].split(b'\0')[0] for i in range(min(max(k, 0), 11))])
        fam.check((n, width, scale), client, native)


def run_tiphtml(m, nat, rng, fam, cases):
    invokes = []
    m.stubs.pop(TIP_POPUP, None)          # the tooltip family records this routine instead of running it
    words = ['Mana 12', 'Range 6 / Cooldown: 1.5 sec.', '<b>', 'a<b', '  ', 'Fire']
    for n in range(cases):
        m.prepare(force=True)
        tip_machine_setup(m)
        common_stubs(m)
        StreamModel(m)

        def to_utf8(mm):
            dst, src = mm.args(2)
            write_std_string(mm, dst, mm.std_string(src).decode('latin1').encode('utf-8'))
            return dst
        m.stub(0x00a99d93, to_utf8, 0)

        def invoke(mm):
            words_ = mm.args(11)
            invokes.append((mm.cstr(words_[1]), mm.cstr(words_[2]), [s32(v) for v in words_[3:7]],
                            mm.cstr(words_[7]), mm.cstr(words_[8]), s32(words_[9])))
            return 0
        m.stub(0x00aae7e0, invoke, 0)
        m.stub(GFX_MGR, lambda mm: DUMMY, 0)
        rate_x, rate_y = rng.choice([(1.0, 1.0), (0.625, 0.625), (1.6, 1.25)])
        m.stub(0x00966d99, float_stub(m, lambda: rate_x, 0), 0)
        m.stub(0x00966d87, float_stub(m, lambda: rate_y, 0), 0)
        handler = m.alloc(0x100, define=True)
        vtable = m.alloc(0x80, define=True)
        opened = []
        if not hasattr(m, '_open_stub'):
            m._open_stub = m._next_stub
            m._next_stub += 16
        stub_open = m._open_stub
        m.stub(stub_open, lambda mm: opened.append(1) or 0, 0)
        for i in range(0x20):
            m.put32(vtable + 4*i, stub_open)
        m.put32(handler, vtable)
        r = [rng.randint(0, 800), rng.randint(0, 600)]
        r += [r[0] + rng.randint(0, 50), r[1] + rng.randint(0, 50)]
        m.write(handler + 0x7c, struct.pack('<4i', *r))
        count = rng.randint(1, 12)
        tip = TipC()
        tip.count = count
        m.uc.mem_write(TEXT_LIST, bytes(80*0xff))
        for i in range(count):
            t = rng.choice(words + ['\n', '', 'line %d' % i]).encode()
            m.uc.mem_write(TEXT_LIST + 0xff*i, t + b'\0')
            tip.lines[i].value = t
            c = rng.randint(0, 24)
            m.uc.mem_write(TEXT_COLOR + 4*i, struct.pack('<i', c))
            tip.color[i] = c
        invokes.clear()
        m.call(TIP_POPUP, [count, rng.randint(0, 6)], ecx=handler)
        title, body = ctypes.create_string_buffer(8192), ctypes.create_string_buffer(65536)
        nat.lib.mu_skill_tooltip_html(ctypes.byref(tip), title, 8192, body, 65536)
        utf = lambda b: b.decode('latin1').encode('utf-8')  # noqa: E731
        div = lambda v, rate: int(cm.f32(cm.f32(float(v)) / cm.f32(rate)))  # noqa: E731  cvttss2si(v / rate)
        rect = [div(r[0], rate_x), div(r[1], rate_y), div(r[2] - r[0], rate_x), div(r[3] - r[1], rate_y)]
        client = (invokes[0], len(opened)) if invokes else None
        native = ((b'SetInfoPopupSkillStamp', b'%d %d %d %d %s %s %d', rect, utf(title.value), utf(body.value), 0), 1)
        fam.check(n, client, native)


# ---- main -------------------------------------------------------------------------------------------

FAMILIES = ['lexcast', 'row', 'req', 'mana', 'delay', 'special', 'feed', 'icon', 'wrap', 'tooltip', 'tiphtml']


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', default=os.environ.get('SNAP'), help='langread snapshot (local)')
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--families', default=','.join(FAMILIES))
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes are caught')
    parser.add_argument('--output')
    parser.add_argument('--verbose', action='store_true', help='print sample client values')
    args = parser.parse_args()
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    if vl.sha256_file(args.text) != vl.TEXT_SHA256 or vl.sha256_file(args.data) != vl.DATA_SHA256:
        raise SystemExit('the pinned captures are required (MU_CLIENT_TEXT / MU_IMAGE_DATA)')
    if not args.snapshot:
        raise SystemExit('--snapshot (or SNAP) is required')
    snap = plain.Snapshot.load(args.snapshot)
    m = vl.LangMachine(text, data, snap)
    families = [f for f in args.families.split(',') if f]
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256, 'seed': args.seed, 'families': {}}
    with tempfile.TemporaryDirectory() as work:
        args.work = work
        nat = SkillNative(work)
        run_all(m, nat, snap, args, families, report, random.Random(args.seed))
        if args.mutations:
            report['mutations'] = mutations(m, snap, args, families, work)
            print('mutations', json.dumps(report['mutations']))
    report['mismatches'] = sum(f['mismatches'] for f in report['families'].values())
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    for name, fam in report['families'].items():
        if fam['mismatches']:
            print(name, json.dumps(fam['examples'][:2])[:1500])
    print('total cases', sum(f['cases'] for f in report['families'].values()), 'mismatches', report['mismatches'])
    if report['mismatches'] or (args.mutations and not all(report['mutations'].values())):
        sys.exit(1)


def run_all(m, nat, snap, args, families, report, rng, quiet=False):
    records = snapshot_records(snap)
    keys = [r.index for r in records]
    table = nat.table(records)
    lang = h = None
    for name in families:
        fams = [Family(name)]
        if name == 'lexcast':
            run_lexcast(m, nat, rng, fams[0])
        elif name == 'row':
            run_row(m, nat, rng, fams[0], args.cases)
        elif name == 'req':
            run_req(m, nat, table, keys, rng, fams[0])
        elif name == 'mana':
            if lang is None:
                lang, h = lang_native(snap, args.work)
            run_mana(m, nat, lang, h, table, keys, rng, fams[0])
        elif name == 'delay':
            fams = [Family('delay_start'), Family('delay_ready'), Family('delay_tick')]
            run_delay(m, nat, table, keys, rng, fams, args.cases*3)
        elif name == 'special':
            run_special(m, nat, table, keys, rng, fams[0])
        elif name == 'feed':
            run_feed(m, nat, table, keys, rng, fams[0], args.cases)
        elif name == 'icon':
            run_icon(m, nat, table, keys, rng, fams[0])
        elif name == 'wrap':
            run_wrap(m, nat, rng, fams[0], args.cases)
        elif name == 'tooltip':
            if lang is None:
                lang, h = lang_native(snap, args.work)
            run_tooltip(m, nat, lang, h, snap, table, keys, records, rng, fams[0], args)
        elif name == 'tiphtml':
            run_tiphtml(m, nat, rng, fams[0], args.cases)
        else:
            raise SystemExit(f'unknown family {name}')
        for fam in fams:
            report['families'][fam.name] = fam.summary()
            if not quiet:
                print(fam.name, json.dumps({k: v for k, v in fam.summary().items()
                                            if k not in ('examples', 'samples') or args.verbose}), flush=True)


def lang_native(snap, work):
    """core/mu_lang over the snapshot's plaintext (GetSkillInformation's values for the mana family)."""
    plain_dir = Path(work)/'lang'
    plain_dir.mkdir(exist_ok=True)
    plain.convert(snap, plain_dir)
    lang = vl.Native(work)
    return lang, lang.load(plain_dir)


MUTANTS = {1: 'lexcast', 2: 'row', 3: 'req', 4: 'feed', 5: 'tooltip', 6: 'delay', 7: 'mana', 8: 'wrap', 9: 'icon',
           10: 'tiphtml', 11: 'special'}


def mutations(m, snap, args, families, work):
    out = {}
    for number, family in MUTANTS.items():
        if family not in families:
            continue
        ext = 'dylib' if sys.platform == 'darwin' else 'so'
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill'), f'mutant{number}.{ext}'], check=True)
        nat = SkillNative(work, ROOT/f'reconstructed/skill/mutant{number}.{ext}')
        report = {'families': {}}
        small = argparse.Namespace(**vars(args))
        small.cases = min(args.cases, 200)
        run_all(m, nat, snap, small, [family], report, random.Random(args.seed + number), quiet=True)
        out[f'mutant{number}:{family}'] = sum(f['mismatches'] for f in report['families'].values()) > 0
    return out


if __name__ == '__main__':
    main()
