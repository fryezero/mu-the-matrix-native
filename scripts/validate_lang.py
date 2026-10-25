#!/usr/bin/env python3
"""Run the client's own consumers of the Lang.mpr tables over a live snapshot (NATIVE-LANG-001).

The pinned restored text (0x00401000) and second image section run in
Unicorn (scripts/client_ui_machine.py).  The langread snapshot
(live-readers/langread) is mapped at its original addresses: the
script-table manager 0x06fbaa60 in the uninitialised data, the map nodes
and buffers in their heap pages.  A read of a byte the snapshot did not copy
stops the case.  Each consumer's result is compared with the native module
native/core/mu_lang.c (built here as a shared library) loading the
plaintext that scripts/live_lang_to_plain.py wrote from the same snapshot.

Families:

* text: GlobalText 0x0095f027 (this 0x06fbab48) for every key;
* skill_lookup: the skill lookup 0x00961620 (this 0x06fbb138) returns the
  record of every key (the converter's tree walk) and the default record
  +0x38 for absent keys;
* skill_info: GetSkillInformation 0x01696458 (name, mana, distance, AG) for
  every skill and master levels 0 and a random 1..40; GetSkillDistance
  0x01696630 runs with a character whose class takes no class branch;
* gate, move, npc: the lookups 0x0110cbaf, 0x0113c3f5 and the Npcname
  getters 0x011427c7 / 0x011427e0 / 0x011427f9 / 0x01142812;
* enchant_first / enchant_mesh: 0x010ffd7a and 0x010ffddb for every code
  (meshes -1..9) and absent codes;
* map_names: the map-name function 0x016baaa6 for worlds 0..299 with the
  real GlobalText; map_table: the same function with a GlobalText that
  returns its index, which gives native/core/mu_lang_maps.h (--write-maps
  regenerates it; otherwise the committed header must match).

NATIVE-LANG-002 families (the same snapshot):

* buff: the BuffEffect lookup 0x010de66f (this 0x06fbb2a4) for every key,
  absent keys and keys >= 0x1cb (the default record +0x40): every field
  the client's consumers read; buff_item: 0x010de6d3 for every item code of
  the table and absent codes; buff_getters: 0x010de759 (+0x28), 0x010de7a3
  (+0x40), 0x010de772 / 0x010de78a (+0 / +4 by item);
* buff_tooltip: the InfoPopup line builder 0x01298a54 for every buff and
  hero buff values {0, random} (value kind 2 with the option singleton's
  three states): the lines it pushes (the client's sprintf runs);
* addbuff: the bufflist's addBuff handler 0x00c5f278 for buffs -2..0x1cf:
  the object members it sets and the invoke;
* soulconv: the MonsterSoulConversion lookup 0x01135146 (this 0x06fbbe1c)
  for its codes and absent codes (ItemValue prices a listed code);
* charinfo: the CharacterInfoSetup lookup 0x010e5203 (this 0x06fbad18) for
  every key and absent keys; charinfo_rows: the character window's row
  builder 0x00b3dedc for every class index: the SetName invokes (type, id,
  sort, label, colours, button) in order.

Modelled (not client code): the import slots (any import call stops the
case); thread-safe local statics as already constructed (their TLS guards
0 and the TLS epoch maximal); the map-name function's state: the current
world 0x01cf15fc equal to the argument, the event singletons 0x1ec8eb8 and
0x1ec9118 zero, the pointer singleton 0x00c7dfcc's predicate 0x009d3e63
false, a zero hero 0x0a39d754, and 0x00b9e03b (world 115's runtime name)
returning a marker; for skill_info the master-skill and class managers
(0x00ac3bf7, 0x0095f998, 0x0095fb5b, 0x0095fb49, 0x0095f5cc) return dummies,
0x00bb1d9d returns the case's master level, 0x00c354b7 returns -1 and
0x00c2a236 returns 0 (no skill-tree distance bonus).
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
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402

DEFAULT_TEXT = pins.TEXT.default()
DEFAULT_DATA = pins.DATA.default()
TEXT_SHA256 = pins.TEXT.sha256
DATA_SHA256 = pins.DATA.sha256
MAPS_HEADER = ROOT/'native/core/mu_lang_maps.h'

GLOBAL_TEXT, GLOBAL_TEXT_STRING = 0x0095f027, 0x011753c3
SKILL_LOOKUP, SKILL_INFO = 0x00961620, 0x01696458
GATE_LOOKUP, MOVE_LOOKUP = 0x0110cbaf, 0x0113c3f5
NPC_NAME, NPC_1C, NPC_20, NPC_24 = 0x011427c7, 0x011427e0, 0x011427f9, 0x01142812
ENCHANT_FIRST, ENCHANT_MESH = 0x010ffd7a, 0x010ffddb
MAP_NAME = 0x016baaa6
BUFF_GET, BUFF_BY_ITEM, BUFF_TYPE, BUFF_VALUE_KIND, BUFF_ITEM_INDEX, BUFF_ITEM_GROUP = (
    0x010de66f, 0x010de6d3, 0x010de759, 0x010de7a3, 0x010de772, 0x010de78a)
BUFF_TOOLTIP, HERO_BUFF_VALUE, OPTION_SINGLETON, OPTION_HIDDEN, OPTION_VALUE = (
    0x01298a54, 0x01295d1c, 0x00c5cc97, 0x010702e1, 0x010702bd)
ITEM_CACHE, SPRINTF, TO_UTF8, ADDBUFF, SOUL_LOOKUP = 0x01298996, 0x0098d0a9, 0x00a99d93, 0x00c5f278, 0x01135146
CHARINFO_GET, CHARINFO_ROWS, INVOKE, LINE_BUILDER, CLASS_INDEX = 0x010e5203, 0x00b3dedc, 0x00aae7e0, 0x00ab4dc0, 0x0095f5cc
CRT_NEW, CRT_MALLOC, CRT_FREE, CRT_DELETE = 0x0191ba7b, 0x0191bab9, 0x0191bac2, 0x0191ba5f
STRING_CSTR = 0x008e7940
CURRENT_WORLD, HERO, FTOL_LEVEL = 0x01cf15fc, 0x0a39d754, 0x0bdcb280
TLS_INDEX, TLS_BLOCK = 0x0bdcaf58, 0x7ff00800
EVENT_OBJECTS = (0x1ec8eb8, 0x1ec9118)
DUMMY = 0x0bf00000
RESERVED = ((0, 0x10000), (cm.STACK_BASE, cm.STACK_BASE + cm.STACK_SIZE), (cm.TEXT_BASE, cm.BSS_BASE),
            (cm.BSS_BASE, cm.BSS_END), (cm.HEAP_BASE, cm.HEAP_BASE + cm.HEAP_SIZE), (cm.STUB_BASE, 1 << 32))
TLS_PATTERN = re.compile(rb'\xa1\x58\xaf\xdc\x0b\x64\x8b\x0d\x2c\x00\x00\x00\x8b\x04\x81\x8b\x0d(....)', re.S)


def sha256_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LangMachine(cm.Machine):
    """The client machine with the snapshot mapped and coverage-checked."""

    def __init__(self, text, data, snap, check_reads=True):
        """check_reads=False skips the per-page read hooks that report reads outside the snapshot's blocks (one
        Python hook per page run: slow on sparse heap snapshots; such reads then see zeros)."""
        super().__init__(text, data)
        self.snap = snap
        self.allow((cm.TEXT_BASE, cm.TEXT_BASE + len(text)))
        self.guards = sorted({struct.unpack('<I', g.group(1))[0] for g in TLS_PATTERN.finditer(text)})
        self.bss_blocks, intervals, pages, self.skipped = [], [], set(), 0
        for address, block in snap.blocks.items():
            end = address + len(block)
            if cm.BSS_BASE <= address and end <= cm.BSS_END:
                self.bss_blocks.append((address, block))
                continue
            if any(a < end and address < b for a, b in RESERVED):
                self.skipped += 1     # shape-chase copies that land on the machine's own regions
                continue
            intervals.append((address, end))
            pages.update(range(address & ~0xfff, (end + 0xfff) & ~0xfff, 0x1000))
        runs, start, prev = [], None, None
        for page in sorted(pages):
            if start is None:
                start = prev = page
            elif page == prev + 0x1000:
                prev = page
            else:
                runs.append((start, prev + 0x1000))
                start = prev = page
        if start is not None:
            runs.append((start, prev + 0x1000))
        for a, b in runs:
            self.uc.mem_map(a, b - a, cm.UC_PROT_ALL)
        for address, end in sorted(intervals, key=lambda iv: iv[1] - iv[0]):
            self.uc.mem_write(address, snap.blocks[address])
        intervals.sort()
        merged = []
        for a, b in intervals:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        self.covered_starts = [a for a, _ in merged]
        self.covered = merged
        for a, b in runs if check_reads else ():
            self.uc.hook_add(cm.UC_HOOK_MEM_READ, self._snap_read, begin=a, end=b - 1)
        self.snapshot_reads = self.tail_reads = 0

    def _snap_read(self, uc, access, address, size, value, user):
        import bisect
        self.snapshot_reads += 1
        i = bisect.bisect_right(self.covered_starts, address) - 1
        if i >= 0 and address < self.covered[i][1] < address + size and address % 4 == 0 and size == 4:
            self.tail_reads += 1      # the CRT string routines read whole aligned dwords past a NUL
            return
        if i < 0 or address + size > self.covered[i][1]:
            self.errors.append(f'read of {size} bytes at {address:#x} outside the snapshot '
                               f'(eip {uc.reg_read(cm.UC_X86_REG_EIP):#x})')
            uc.emu_stop()

    def prepare(self, force=False):
        """reset() plus the snapshot's static range and the modelled statics.  The consumers only
        read the tables, so the state is rebuilt when forced or once the case heap has grown."""
        if not force and getattr(self, '_prepared', False) and self.heap_next - cm.HEAP_BASE < 0x100000:
            self.calls, self.errors = [], []
            return
        self._prepared = True
        self.reset()
        for address, block in self.bss_blocks:
            self.write(address, block)
        self.put32(TLS_INDEX, 0)
        self.uc.mem_write(cm.TEB_BASE + 0x2c, struct.pack('<I', TLS_BLOCK))
        self.uc.mem_write(TLS_BLOCK, struct.pack('<II', TLS_BLOCK + 0x100, 0))
        self.uc.mem_write(TLS_BLOCK + 0x100, struct.pack('<II', 0, 0x7fffffff))
        for guard in self.guards:
            self.put32(guard, 0)
        self.put32(FTOL_LEVEL, 2)

    def cstr(self, address, limit=1 << 16):
        out = bytearray()
        while len(out) < limit:
            chunk = self.read(address + len(out), 64)
            nul = chunk.find(b'\0')
            if nul >= 0:
                return bytes(out + chunk[:nul])
            out += chunk
        raise cm.CaseError('unterminated string')

    def std_string(self, address):
        size, cap = struct.unpack('<II', self.read(address + 0x10, 8))
        return self.read(address if cap < 16 else self.u32(address), size)

    def import_guard(self):
        def stop(mm, words):
            return mm.fail('import call')
        for name in {spec[0] for spec in cm.SLOTS.values() if spec}:
            self.handlers[name] = stop


# ---- native module ------------------------------------------------------

I32 = ctypes.c_int32


class GateC(ctypes.Structure):
    _fields_ = [(n, I32) for n in ('index', 'flag', 'world', 'x1', 'y1', 'x2', 'y2', 'target', 'dir',
                                    'min_level', 'max_level')]

    def values(self):
        return [getattr(self, n) for n, _ in self._fields_]


class MoveC(ctypes.Structure):
    _fields_ = [('index', I32), ('name', ctypes.c_char_p), ('server_name', ctypes.c_char_p)] + \
               [(n, I32) for n in ('id', 'zen', 'min_level', 'max_level', 'gate', 'x44', 'x48', 'x4c')]


class NpcC(ctypes.Structure):
    _fields_ = [('index', I32), ('name', ctypes.c_char_p), ('x1c', I32), ('x20', I32), ('x24', ctypes.c_uint8)]

class BuffC(ctypes.Structure):
    _fields_ = [(n, I32) for n in ('index', 'group', 'item_group', 'item_index', 'type', 'x2c', 'x30', 'value_kind')] + \
               [('name', ctypes.c_char_p), ('lines', ctypes.c_char_p*8), ('nlines', I32)]

    def values(self):
        return [self.index, self.group, self.item_group, self.item_index, self.name, self.type, self.x2c, self.x30,
                self.value_kind, [self.lines[i] for i in range(self.nlines)]]


class CharinfoC(ctypes.Structure):
    _fields_ = [(n, I32) for n in ('id', 'color', 'group', 'type', 'sort', 'value_color', 'button')] + \
               [('classes', ctypes.c_uint8*16), ('nclasses', I32), ('label', ctypes.c_char_p),
                ('prefix', ctypes.c_char_p), ('suffix', ctypes.c_char_p)]

    def values(self):
        return [self.id, self.color, self.label, self.group, [self.classes[i] for i in range(self.nclasses)],
                self.type, self.sort, self.value_color, self.prefix, self.suffix, self.button]


class BuffValuesC(ctypes.Structure):
    _fields_ = [('hero_value', I32), ('value2_hidden', ctypes.c_int), ('value2_kind', I32), ('value2_int', I32),
                ('value2_float', ctypes.c_float)]


class AddBuffC(ctypes.Structure):
    _fields_ = [('buff', I32), ('is_debuff', ctypes.c_int), ('is_cash', ctypes.c_int), ('has_detail', ctypes.c_int),
                ('detail', I32)]


class Native:
    def __init__(self, work):
        cc = shutil.which('cc') or shutil.which('clang')
        if not cc:
            raise SystemExit('a C compiler is needed for the native module')
        ext = 'dylib' if sys.platform == 'darwin' else 'so'
        lib = Path(work)/f'libmulang.{ext}'
        subprocess.run([cc, '-std=c11', '-O2', '-fPIC', '-shared', str(ROOT/'native/core/mu_lang.c'), '-o', str(lib)],
                       check=True)
        self.lib = L = ctypes.CDLL(str(lib))
        L.mu_lang_load.restype = ctypes.c_void_p
        L.mu_lang_load.argtypes = [ctypes.c_char_p]
        L.mu_lang_free.argtypes = [ctypes.c_void_p]
        for name in ('mu_lang_text', 'mu_lang_npc_name', 'mu_lang_map_name', 'mu_lang_dialog'):
            getattr(L, name).restype = ctypes.c_char_p
            getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_lang_skill_info.restype = ctypes.c_char_p
        L.mu_lang_skill_info.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32] + [ctypes.POINTER(ctypes.c_int32)]*3
        for name in ('mu_lang_gate_get', 'mu_lang_move_get', 'mu_lang_npc_get', 'mu_lang_skill_get'):
            getattr(L, name).restype = ctypes.c_void_p
            getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_lang_enchant_first.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float)]
        L.mu_lang_enchant_mesh.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_float)]
        L.mu_lang_map_text_index.argtypes = [ctypes.c_int32]
        L.mu_lang_map_text_index.restype = ctypes.c_int32
        for name in ('mu_lang_buff_get', 'mu_lang_buff_by_item', 'mu_lang_charinfo_get'):
            getattr(L, name).restype = ctypes.c_void_p
            getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_lang_buff_tooltip.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(BuffValuesC),
                                           ctypes.c_void_p, ctypes.c_int]
        L.mu_lang_charinfo_rows.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_int]
        L.mu_lang_buff_addbuff.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p]
        L.mu_lang_soul_conversion.argtypes = [ctypes.c_void_p, ctypes.c_int32]

    def load(self, directory):
        handle = self.lib.mu_lang_load(str(directory).encode())
        if not handle:
            raise SystemExit(f'mu_lang_load({directory}) failed')
        return handle

    def gate(self, h, index):
        p = self.lib.mu_lang_gate_get(h, index)
        return None if not p else list(GateC.from_address(p).values())

    def move(self, h, index):
        p = self.lib.mu_lang_move_get(h, index)
        if not p:
            return None
        c = MoveC.from_address(p)
        return [c.index, c.name, c.server_name, c.id, c.zen, c.min_level, c.max_level, c.gate, c.x44, c.x48, c.x4c]

    def npc(self, h, index):
        p = self.lib.mu_lang_npc_get(h, index)
        if not p:
            return None
        c = NpcC.from_address(p)
        return [c.name, c.x1c, c.x20, c.x24]

    def skill_info(self, h, skill, master):
        mana, dist, ag = ctypes.c_int32(), ctypes.c_int32(), ctypes.c_int32()
        name = self.lib.mu_lang_skill_info(h, skill, master, ctypes.byref(mana), ctypes.byref(dist), ctypes.byref(ag))
        return None if name is None else [name, mana.value, dist.value, ag.value]

    def buff(self, h, index, by_item=False):
        p = (self.lib.mu_lang_buff_by_item if by_item else self.lib.mu_lang_buff_get)(h, index)
        return None if not p else BuffC.from_address(p).values()

    def buff_tooltip(self, h, index, values):
        out = ctypes.create_string_buffer(256*16)
        n = self.lib.mu_lang_buff_tooltip(h, index, ctypes.byref(values), out, 16)
        return [out.raw[256*i:256*(i+1)].split(b'\0')[0] for i in range(n)]

    def charinfo(self, h, key):
        p = self.lib.mu_lang_charinfo_get(h, key)
        return None if not p else CharinfoC.from_address(p).values()

    def charinfo_rows(self, h, class_index):
        out = (ctypes.c_void_p*256)()
        n = self.lib.mu_lang_charinfo_rows(h, class_index, out, 256)
        return [CharinfoC.from_address(out[i]) for i in range(n)]

    def enchant(self, h, code, mesh=None):
        out = (ctypes.c_float*3)()
        if mesh is None:
            ok = self.lib.mu_lang_enchant_first(h, code, out)
        else:
            ok = self.lib.mu_lang_enchant_mesh(h, code, mesh, out)
        return [struct.unpack('<I', struct.pack('<f', v))[0] for v in out] if ok else None


# ---- families -----------------------------------------------------------

def first_diff(client, native):
    if isinstance(client, list) and isinstance(native, list):
        for i, (a, b) in enumerate(zip(client, native)):
            if a != b:
                return [i, repr(a)[:160], repr(b)[:160]]
        return ['length', len(client), len(native)]
    return None


class Family:
    def __init__(self, name):
        self.name, self.cases, self.mismatches, self.examples = name, 0, 0, []

    def check(self, label, client, native):
        self.cases += 1
        if client != native:
            self.mismatches += 1
            if len(self.examples) < 5:
                self.examples.append({"case": label, "client": repr(client)[:120], "native": repr(native)[:120], "first_diff": first_diff(client, native)})

    def summary(self):
        return {'cases': self.cases, 'mismatches': self.mismatches, 'examples': self.examples}


def run_text(m, nat, h, snap, fam):
    for key, _ in snap.tree(plain.TEXT + 0x38):
        m.prepare()
        m.import_guard()
        client = m.cstr(m.call(GLOBAL_TEXT, [key], ecx=plain.TEXT))
        fam.check(key, client, nat.lib.mu_lang_text(h, key))


def run_skill_lookup(m, snap, rng, fam):
    nodes = snap.tree(plain.SKILL + 0x108)
    keys = {k for k, _ in nodes}
    for key, node in nodes:
        m.prepare()
        fam.check(key, m.call(SKILL_LOOKUP, [key], ecx=plain.SKILL), node + 0x14)
    absent = [k for k in rng.sample(range(-50, 5000), 400) if k not in keys][:100]
    for key in absent:
        m.prepare()
        fam.check(('absent', key), m.call(SKILL_LOOKUP, [key], ecx=plain.SKILL), plain.SKILL + 0x38)


def run_skill_info(m, nat, h, snap, rng, fam):
    state = {'master': 0}
    m.stub(0x00ac3bf7, lambda mm: DUMMY, 0)
    for getter in (0x0095f998, 0x0095fb5b, 0x0095fb49):
        m.stub(getter, lambda mm: DUMMY, cm.stdcall_cleanup(m.text, getter))
    m.stub(0x0095f5cc, lambda mm: 0, 0)
    m.stub(0x00bb1d9d, lambda mm: state['master'], cm.stdcall_cleanup(m.text, 0x00bb1d9d))
    m.stub(0x00c354b7, lambda mm: 0xffffffff, cm.stdcall_cleanup(m.text, 0x00c354b7))
    m.stub(0x00c2a236, lambda mm: 0, cm.stdcall_cleanup(m.text, 0x00c2a236))
    for key, _ in snap.tree(plain.SKILL + 0x108):
        for master in (0, rng.randint(1, 40)):
            m.prepare()
            state['master'] = master
            hero = m.alloc(0x400, define=True)
            m.put32(HERO, hero)
            out = m.alloc(0x400, define=True)
            m.call(SKILL_INFO, [key, 0, out, out + 0x200, out + 0x204, out + 0x208])
            client = [m.cstr(out), m.u32(out + 0x200), m.u32(out + 0x204), m.u32(out + 0x208)]
            client[1:] = [struct.unpack('<i', struct.pack('<I', v))[0] for v in client[1:]]
            fam.check((key, master), client, nat.skill_info(h, key, master))
    for address in (0x00ac3bf7, 0x0095f998, 0x0095fb5b, 0x0095fb49, 0x0095f5cc, 0x00bb1d9d, 0x00c354b7, 0x00c2a236):
        m.stubs.pop(address, None)


def run_gates(m, nat, h, snap, fam):
    for key, node in snap.tree(plain.GATE + 0x38):
        m.prepare()
        address = m.call(GATE_LOOKUP, [key], ecx=plain.GATE)
        client = [key] + [struct.unpack('<i', m.read(address + off, 4))[0] for _, off in plain.GATE_COLUMNS]
        fam.check(key, (address, client), (node + 0x14, nat.gate(h, key)))


def run_moves(m, nat, h, snap, fam):
    for key, node in snap.tree(plain.MOVEREQ + 0x38):
        m.prepare()
        address = m.call(MOVE_LOOKUP, [key], ecx=plain.MOVEREQ)
        client = [key, m.std_string(address + 4), m.std_string(address + 0x1c)]
        client += [struct.unpack('<i', m.read(address + off, 4))[0] for _, off in plain.MOVE_COLUMNS]
        fam.check(key, (address, client), (node + 0x14, nat.move(h, key)))


def run_npcs(m, nat, h, snap, fam):
    for key, _ in snap.tree(plain.NPCNAME + 0x38):
        m.prepare()
        name = m.std_string(m.call(NPC_NAME, [key], ecx=plain.NPCNAME))
        values = []
        for getter in (NPC_1C, NPC_20, NPC_24):
            m.prepare()
            values.append(m.call(getter, [key], ecx=plain.NPCNAME))
        client = [name, struct.unpack('<i', struct.pack('<I', values[0]))[0],
                  struct.unpack('<i', struct.pack('<I', values[1]))[0], values[2] & 0xff]
        fam.check(key, client, nat.npc(h, key))


def run_enchant(m, nat, h, snap, rng, first, mesh):
    codes = [k for k, _ in snap.tree(plain.ENCHANT + 0x38)]
    present = set(codes)
    absent = [k for k in rng.sample(range(0, 0x3000), 600) if k not in present][:200]
    for code in codes + absent:
        m.prepare()
        address = m.call(ENCHANT_FIRST, [code], ecx=plain.ENCHANT)
        first.check(code, list(struct.unpack('<3I', m.read(address, 12))), nat.enchant(h, code))
        for k in range(-1, 10):
            m.prepare()
            address = m.call(ENCHANT_MESH, [code, k], ecx=plain.ENCHANT)
            mesh.check((code, k), list(struct.unpack('<3I', m.read(address, 12))), nat.enchant(h, code, k))


def heap_stubs(m):
    def new(mm):
        return mm.alloc(mm.args(1)[0] or 1, define=True)
    m.stub(CRT_NEW, new)
    m.stub(CRT_MALLOC, new)
    for address in (CRT_FREE, CRT_DELETE, 0x019a4d50):
        m.stub(address, lambda mm: 0)


def crt_state(m):
    """The CRT words the string and sprintf code reads (as scripts/validate_fidelity.py): __favor 0x0bdcb284 (no
    ERMS), the CPU feature word 0x01cf6618, __security_cookie 0x01cf65c0 (any value) and the printf options
    0x01d1db70 (zero, as at start)."""
    m.put32(0x0bdcb284, 0)
    m.put32(0x01cf6618, 0)
    m.put32(0x01cf65c0, 0xc179bffe)
    m.write(0x01d1db70, bytes(8))     # the CRT's printf options word (a zero-initialised static)


def c_sprintf(m):
    """Model of the client's sprintf 0x0098d0a9(buf, fmt, ...) (the UCRT's vsprintf needs locale state this
    machine does not hold): C conversions d i u x X (one word) and f F g G e E (a double) through Python's %."""
    words = m.args(16)
    buf, fmt = words[0], m.cstr(words[1]).decode('latin1')
    out, i, arg = [], 0, 2
    spec = re.compile(r'%([-+ #0]*\d*(?:\.\d+)?)([diuxXfFgGeE%])')
    while i < len(fmt):
        mt = spec.match(fmt, i) if fmt[i] == '%' else None
        if not mt:
            out.append(fmt[i])
            i += 1
            continue
        flags, conv = mt.groups()
        if conv == '%':
            out.append('%')
        elif conv in 'diuxX':
            v = words[arg]
            arg += 1
            v = v if conv in 'uxX' else struct.unpack('<i', struct.pack('<I', v))[0]
            out.append(('%' + flags + ('d' if conv in 'iu' else conv)) % v)
        else:
            v = struct.unpack('<d', struct.pack('<II', words[arg], words[arg + 1]))[0]
            arg += 2
            out.append(('%' + flags + conv) % v)
        i = mt.end()
    data = ''.join(out).encode('latin1')
    m.write(buf, data + b'\0')
    return len(data)


def client_buff(m, r):
    i = lambda o: struct.unpack('<i', m.read(r + o, 4))[0]
    begin, end, _ = struct.unpack('<III', m.read(r + 0x34, 12))
    lines = [m.std_string(a) for a in range(begin, end, 0x18)]
    return [i(0), i(4), i(8), i(0xc), m.std_string(r + 0x10), i(0x28), i(0x2c), i(0x30), i(0x40), lines]


def run_buffs(m, nat, h, snap, rng, fam, items, getters):
    nodes = snap.tree(plain.BUFF + 0x38)
    keys = {k for k, _ in nodes}
    absent = [k for k in rng.sample(range(-100, 0x1cb), 300) if k not in keys][:60] + [0x1cb, 0x1cc, 0x7fffffff]
    for key in [k for k, _ in nodes] + absent:
        m.prepare()
        r = m.call(BUFF_GET, [key & 0xffffffff], ecx=plain.BUFF)
        fam.check(key, client_buff(m, r), nat.buff(h, key))
        m.prepare()
        getters.check(('type', key), struct.unpack('<i', struct.pack('<I', m.call(BUFF_TYPE, [key & 0xffffffff],
                                                                                     ecx=plain.BUFF)))[0],
                      nat.buff(h, key)[5])
        m.prepare()
        getters.check(('value_kind', key), struct.unpack('<i', struct.pack('<I', m.call(BUFF_VALUE_KIND, [key & 0xffffffff],
                                                                                           ecx=plain.BUFF)))[0],
                      nat.buff(h, key)[8])
    codes = sorted({(snap.i32(node + 0x14 + 8) << 9) + snap.i32(node + 0x14 + 0xc) for _, node in nodes})
    present = set(codes)
    codes += [c for c in rng.sample(range(0, 0x3000), 200) if c not in present][:50]
    for code in codes:
        m.prepare()
        r = m.call(BUFF_BY_ITEM, [code & 0xffffffff], ecx=plain.BUFF)
        native = nat.buff(h, code, by_item=True)
        items.check(code, client_buff(m, r), native)
        for getter, field in ((BUFF_ITEM_INDEX, 0), (BUFF_ITEM_GROUP, 1)):
            m.prepare()
            v = struct.unpack('<i', struct.pack('<I', m.call(getter, [code & 0xffffffff], ecx=plain.BUFF)))[0]
            getters.check((getter, code), v, native[field])


def run_buff_tooltip(m, nat, h, snap, rng, fam):
    """0x01298a54(out vector<std::string>, buff) with the hero's buff value (0x01295d1c) and, for value kind 2,
    the option singleton 0x00c5cc97 (0x010702e1 hidden, 0x010702bd {int, float, kind}) modelled."""
    heap_stubs(m)
    state = {}
    m.stub(HERO_BUFF_VALUE, lambda mm: state['value'], 4)
    m.stub(OPTION_SINGLETON, lambda mm: DUMMY, 0)
    m.stub(OPTION_HIDDEN, lambda mm: state['hidden'], 0)

    def option_value(mm):
        out = mm.args(1)[0]
        mm.write(out, struct.pack('<ifi', state['int'], state['float'], state['kind']))
        return out
    m.stub(OPTION_VALUE, option_value, 4)

    def item_cache(mm):
        # 0x01298996(out, buff): the buff's item-icon cache in this+4 (a map the lines never read): 12 zero bytes
        out = mm.args(1)[0]
        mm.write(out, bytes(12))
        return out
    m.stub(ITEM_CACHE, item_cache, 8)
    m.stub(SPRINTF, c_sprintf, 0)
    for key, node in snap.tree(plain.BUFF + 0x38):
        kind = snap.i32(node + 0x14 + 0x40)
        cases = [dict(value=0, hidden=0, kind=-1), dict(value=rng.randint(1, 500), hidden=0, kind=-1)]
        if kind == 2:
            # the option's kind as the format expects it (an int for %d, a double for %f: the server's data is
            # consistent; a mismatched pair reads stack words in the client's varargs)
            begin, end, _ = struct.unpack('<III', snap.read(node + 0x14 + 0x34, 12))
            joined = b''.join(snap.string(a) for a in range(begin, end, 0x18))
            floaty = re.search(rb'%[-+ #0]*\d*(?:\.\d+)?[fFgGeE]', joined) is not None
            cases += [dict(value=0, hidden=1, kind=0), dict(value=0, hidden=0, kind=1 if floaty else 0),
                      dict(value=0, hidden=0, kind=7)]
        for case in cases:
            state.update(case, int=rng.randint(1, 900), float=cm.f32(rng.uniform(0.5, 90.0)))
            m.prepare(force=True)
            crt_state(m)
            m.put32(HERO, m.alloc(0x4000, define=True))
            out = m.alloc(16, define=True)
            m.call(BUFF_TOOLTIP, [out, key], ecx=DUMMY)
            begin, end = m.u32(out), m.u32(out + 4)
            client = [m.std_string(a) for a in range(begin, end, 0x18)]
            values = BuffValuesC(case['value'], case['hidden'], case['kind'], state['int'], state['float'])
            fam.check((key, tuple(sorted(case.items()))), client, nat.buff_tooltip(h, key, values))
    for address in (HERO_BUFF_VALUE, OPTION_SINGLETON, OPTION_HIDDEN, OPTION_VALUE, ITEM_CACHE, SPRINTF):
        m.stubs.pop(address, None)


def run_addbuff(m, nat, h, fam):
    """The bufflist's addBuff handler 0x00c5f278(buff): the GFx object calls are recorded (value ctor/dtor and
    the object creator 0x00c8f5f4 modelled as no-ops; the member setters 0x00ae957f int / 0x00aecd73 bool and the
    invoke 0x00c8fac2 recorded)."""
    heap_stubs(m)
    calls = []

    def member(kind):
        def handler(mm):
            _, name, value = mm.args(3)
            calls.append((kind, mm.cstr(name), struct.unpack('<i', struct.pack('<I', value))[0] if kind == 'int'
                          else value & 0xff))
            return 0
        return handler

    def invoke(mm):
        name, _ = mm.args(2)
        calls.append(('invoke', mm.cstr(name)))
        return 0
    stubs = {0x00aad26b: (lambda mm: 0, 0), 0x00aad299: (lambda mm: 0, 0), 0x00c8f5f4: (lambda mm: 0, 4),
             0x00ae957f: (member('int'), 0xc), 0x00aecd73: (member('bool'), 0xc), 0x00c8fac2: (invoke, 8)}
    for address, (handler, cleanup) in stubs.items():
        m.stub(address, handler, cleanup)
    for buff in range(-2, 0x1d0):
        calls.clear()
        m.prepare(force=True)
        crt_state(m)
        m.call(ADDBUFF, [buff & 0xffffffff], ecx=DUMMY)
        out = AddBuffC()
        native = []
        if nat.lib.mu_lang_buff_addbuff(h, buff, ctypes.byref(out)):
            native = [('int', b'BuffType', out.buff), ('bool', b'isDebuff', out.is_debuff),
                      ('bool', b'isCashBuff', out.is_cash)]
            if out.has_detail:
                native.append(('int', b'BuffDetailType', out.detail))
            native.append(('invoke', b'addBuff'))
        fam.check(buff, list(calls), native)
    for address in stubs:
        m.stubs.pop(address, None)


def run_soulconv(m, nat, h, snap, rng, fam):
    """MonsterSoulConversion 0x01135146(code) (this 0x06fbbe1c): a record or NULL, for every key and 300 absent
    codes; the native answers whether the code is listed."""
    keys = [k for k, _ in snap.tree(plain.SOULCONV + 0x44)]
    present = set(keys)
    for code in keys + [c for c in rng.sample(range(0, 0x3000), 320) if c not in present][:300]:
        m.prepare()
        fam.check(code, int(m.call(SOUL_LOOKUP, [code], ecx=plain.SOULCONV) != 0),
                  nat.lib.mu_lang_soul_conversion(h, code))


def run_charinfo(m, nat, h, snap, rng, fam):
    nodes = snap.tree(plain.CHARINFO + 0x38)
    keys = {k for k, _ in nodes}
    absent = [k for k in rng.sample(range(-20, 400), 200) if k not in keys][:40]
    for key in [k for k, _ in nodes] + absent:
        m.prepare()
        r = m.call(CHARINFO_GET, [key & 0xffffffff], ecx=plain.CHARINFO)
        i = lambda o: struct.unpack('<i', m.read(r + o, 4))[0]
        begin, end, _ = struct.unpack('<III', m.read(r + 0x24, 12))
        classes = [1 if v else 0 for v in struct.unpack(f'<{(end - begin)//4}i', m.read(begin, end - begin))] \
            if end > begin else []
        client = [i(0), i(4), m.std_string(r + 8), i(0x20), classes, i(0x30), i(0x34), i(0x38),
                  m.std_string(r + 0x3c), m.std_string(r + 0x54), i(0xa0)]
        fam.check(key, client, nat.charinfo(h, key))


def run_charinfo_rows(m, nat, h, fam):
    """The row builder 0x00b3dedc: the invoke helper 0x00aae7e0(this, name, fmt, ...) records its arguments;
    the line builder 0x00ab4dc0(out, text, colour, flag) returns the text with its colour as a marker."""
    heap_stubs(m)
    state = {}
    m.stub(CLASS_INDEX, lambda mm: state['class'], 0)
    calls = []

    def line(mm):
        out, text, colour, flag = mm.args(4)
        payload = b'%s|%d|%d' % (mm.cstr(text), struct.unpack('<i', struct.pack('<I', colour))[0], flag)
        buf = mm.alloc(len(payload) + 1, define=True)
        mm.write(buf, payload + b'\0')
        mm.write(out, struct.pack('<I', buf) + bytes(12) + struct.pack('<II', len(payload), max(len(payload), 16)))
        return out

    def invoke(mm):
        words = mm.args(10)
        name = mm.cstr(words[1])
        if name == b'SetName':
            t, i, srt, label, value, extra, button = words[3:10]
            calls.append([struct.unpack('<i', struct.pack('<I', v))[0] for v in (t, i, srt)] +
                         [mm.cstr(label), mm.cstr(value), mm.cstr(extra), button])
        else:
            calls.append([name])
        return 0
    def to_utf8(mm):
        # 0x00a99d93(dst, src): the ANSI -> UTF-8 conversion through the Win32 code-page imports (modelled: the
        # strings here are ASCII markers, so the bytes are copied)
        dst, src = mm.args(2)
        payload = mm.std_string(src)
        buf = mm.alloc(len(payload) + 1, define=True)
        mm.write(buf, payload + b'\0')
        mm.write(dst, struct.pack('<I', buf) + bytes(12) + struct.pack('<II', len(payload), max(len(payload), 16)))
        return dst
    m.stub(LINE_BUILDER, line, 0)
    m.stub(INVOKE, invoke, 0)
    m.stub(TO_UTF8, to_utf8, 0)
    for class_index in range(16):
        state['class'] = class_index
        calls.clear()
        m.prepare(force=True)
        crt_state(m)
        hero = m.alloc(0x400, define=True)
        m.put32(0x01d1df1c, hero)
        m.call(CHARINFO_ROWS, [], ecx=DUMMY)
        native = [[b'ClearItems']]
        for c in nat.charinfo_rows(h, class_index):
            native.append([c.type, c.id, c.sort, b'%s|%d|0' % (c.label, c.color), b'-|%d|0' % c.value_color, b'',
                           c.button])
        fam.check(class_index, calls, native)
    for address in (CLASS_INDEX, LINE_BUILDER, INVOKE, TO_UTF8):
        m.stubs.pop(address, None)


def map_state(m, world):
    m.prepare()
    m.put32(CURRENT_WORLD, world)
    for obj in EVENT_OBJECTS:
        m.write(obj, bytes(0x100))
    m.put32(HERO, m.alloc(0x400, define=True))


def setup_map_stubs(m):
    m.stub(0x00c7dfcc, lambda mm: DUMMY, 0)
    m.stub(0x009d3e63, lambda mm: 0, 4)

    def runtime_name(mm):
        a = mm.alloc(0x40, define=True)
        mm.write(a + 0x14, b'\x03runtime'.ljust(16, b'\0'))
        mm.put32(a + 0x24, 8)
        mm.put32(a + 0x28, 15)
        return a
    m.stub(0x00b9e03b, runtime_name, 0)


def run_map_names(m, nat, h, fam, worlds):
    setup_map_stubs(m)
    for world in worlds:
        map_state(m, world)
        client = m.cstr(m.call(MAP_NAME, [world]))
        native = nat.lib.mu_lang_map_name(h, world)
        fam.check(world, None if client.startswith(b'\x03') else client, native)


def extract_map_table(m, worlds):
    """world -> (GlobalText index, kind): kind 0 GlobalText, 1 runtime name."""
    setup_map_stubs(m)

    def marker(mm):
        (index,) = mm.args(1)
        a = mm.alloc(0x40, define=True)
        mm.write(a, (b'\x01%d\x02' % index).ljust(16, b'\0'))
        mm.put32(a + 0x10, len(b'\x01%d\x02' % index))
        mm.put32(a + 0x14, 15)
        return a
    m.stub(GLOBAL_TEXT_STRING, marker, 4)
    table = []
    for world in worlds:
        map_state(m, world)
        s = m.cstr(m.call(MAP_NAME, [world]))
        match = re.fullmatch(rb'\x01(\d+)\x02', s)
        table.append((world, int(match.group(1)), 0) if match else (world, -1, 1))
    m.stubs.pop(GLOBAL_TEXT_STRING, None)
    return table


def maps_header(table):
    lines = ['#ifndef MU_LANG_MAPS_H', '#define MU_LANG_MAPS_H', '',
             '/* World -> map name GlobalText index of the map-name function 0x016baaa6',
             ' * (generated by scripts/validate_lang.py --write-maps from the client',
             ' * routine run in Unicorn with a GlobalText that returns its index; current',
             ' * world = the argument, no event running).  Past the table the function',
             ' * returns GlobalText[30 + world].  kind 1: the name comes from runtime state',
             ' * (0x00b9e03b). */', '', '#include <stdint.h>', '',
             'typedef struct mu_lang_map_entry {', '    int32_t world, text, kind;', '} mu_lang_map_entry;', '',
             'static const mu_lang_map_entry MU_LANG_MAPS[] = {']
    row = []
    for world, text, kind in table:
        if kind == 0 and text == 30 + world:
            continue          # the default branch
        row.append(f'{{{world}, {text}, {kind}}}')
    for i in range(0, len(row), 6):
        lines.append('    ' + ', '.join(row[i:i + 6]) + ',')
    lines += ['};', '', '#endif', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', required=True, help='langread snapshot (local)')
    parser.add_argument('--text', default=pins.TEXT.default_str())
    parser.add_argument('--data', default=pins.DATA.default_str())
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--families', default='map_table,text,skill_lookup,skill_info,gate,move,npc,enchant,map_names,'
                                               'buff,buff_tooltip,addbuff,soulconv,charinfo,charinfo_rows')
    parser.add_argument('--write-maps', action='store_true', help='regenerate native/core/mu_lang_maps.h')
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes are caught')
    parser.add_argument('--output')
    args = parser.parse_args()
    text, data = pins.TEXT.read(args.text, exit=True), pins.DATA.read(args.data, exit=True)
    snap = plain.Snapshot.load(args.snapshot)
    rng = random.Random(args.seed)
    families = args.families.split(',')
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'seed': args.seed, 'families': {}}
    m = LangMachine(text, data, snap)
    worlds = range(0, 300)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if 'map_table' in families:
            table = extract_map_table(m, worlds)
            header = maps_header(table)
            if args.write_maps:
                MAPS_HEADER.write_text(header)
            fam = Family('map_table')
            fam.check('header', header, MAPS_HEADER.read_text())
            report['families']['map_table'] = dict(fam.summary(), worlds=len(table),
                                                   runtime=[w for w, _, k in table if k])
        plain_dir = work/'plain'
        plain.convert(snap, plain_dir)
        nat = Native(work)
        h = nat.load(plain_dir)
        runs = {
            'text': lambda f: run_text(m, nat, h, snap, f),
            'skill_lookup': lambda f: run_skill_lookup(m, snap, rng, f),
            'skill_info': lambda f: run_skill_info(m, nat, h, snap, rng, f),
            'gate': lambda f: run_gates(m, nat, h, snap, f),
            'move': lambda f: run_moves(m, nat, h, snap, f),
            'npc': lambda f: run_npcs(m, nat, h, snap, f),
            'map_names': lambda f: run_map_names(m, nat, h, f, worlds),
            'buff_tooltip': lambda f: run_buff_tooltip(m, nat, h, snap, rng, f),
            'charinfo': lambda f: run_charinfo(m, nat, h, snap, rng, f),
            'addbuff': lambda f: run_addbuff(m, nat, h, f),
            'soulconv': lambda f: run_soulconv(m, nat, h, snap, rng, f),
            'charinfo_rows': lambda f: run_charinfo_rows(m, nat, h, f),
        }
        for name in families:
            if name in runs:
                fam = Family(name)
                runs[name](fam)
                report['families'][name] = fam.summary()
            elif name == 'buff':
                fams = [Family('buff'), Family('buff_item'), Family('buff_getters')]
                run_buffs(m, nat, h, snap, rng, *fams)
                for f in fams:
                    report['families'][f.name] = f.summary()
                    print(f.name, json.dumps({k: v for k, v in f.summary().items() if k != 'examples'}))
                continue
            elif name == 'enchant':
                first, mesh = Family('enchant_first'), Family('enchant_mesh')
                run_enchant(m, nat, h, snap, rng, first, mesh)
                report['families']['enchant_first'] = first.summary()
                report['families']['enchant_mesh'] = mesh.summary()
            else:
                continue
            for key in ([name] if name != 'enchant' else ['enchant_first', 'enchant_mesh']):
                print(key, json.dumps({k: v for k, v in report['families'][key].items() if k != 'examples'}))
        report['snapshot_reads'], report['string_tail_reads'] = m.snapshot_reads, m.tail_reads
        report['skipped_blocks'] = m.skipped
        if args.mutations:
            report['mutations'] = mutations(m, nat, snap, plain_dir, work, rng)
            print('mutations', json.dumps(report['mutations']))
        nat.lib.mu_lang_free(h)
    total = sum(f['mismatches'] for f in report['families'].values())
    report['mismatches'] = total
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    if total:
        for name, fam in report['families'].items():
            if fam['mismatches']:
                print(name, json.dumps(fam['examples'], indent=1))
        raise SystemExit(f'{total} mismatches')
    if args.mutations and not all(report['mutations'].values()):
        raise SystemExit('a planted mistake was not caught')
    print('all cases match')


def mutations(m, nat, snap, plain_dir, work, rng):
    """Planted mistakes in the plaintext: each must produce a mismatch."""
    caught = {}

    def mutated(name, edit, family):
        d = work/f'mut-{name}'
        shutil.copytree(plain_dir, d)
        edit(d)
        h = nat.load(d)
        fam = Family(name)
        family(h, fam)
        nat.lib.mu_lang_free(h)
        caught[name] = fam.mismatches > 0

    def edit_line(path, pattern, repl):
        s = path.read_text()
        s2 = re.sub(pattern, repl, s, count=1, flags=re.M)
        assert s2 != s, (path, pattern)
        path.write_text(s2)

    texts = snap.tree(plain.TEXT + 0x38)
    key = texts[len(texts)//2][0]
    mutated('text_entry_changed', lambda d: edit_line(d/'globaltext.txt', rf'^{key}\t', f'{key}\tX'),
            lambda h, f: run_text_subset(m, nat, h, [key], f))
    skills = snap.tree(plain.SKILL + 0x108)
    skey = skills[3][0]
    mutated('skill_mana_column', lambda d: edit_line(d/'skills.tsv', rf'^({skey}\t[^\t]*\t[^\t]*\t[^\t]*\t)(-?\d+)',
                                                      lambda mt: mt.group(1) + str(int(mt.group(2)) + 1)),
            lambda h, f: run_skill_subset(m, nat, h, [skey], f))
    mutated('enchant_default', lambda d: edit_line(d/'enchant.tsv', r'^default\t-1\t[^\t]*', 'default\t-1\t0.25'),
            lambda h, f: run_enchant_subset(m, nat, h, [0x2fff], f))
    codes = snap.tree(plain.ENCHANT + 0x38)
    multi = next(k for k, node in codes if snap.u32(node + 0x18) - snap.u32(node + 0x14) >= 32)
    mutated('enchant_order', lambda d: swap_first_two(d/'enchant.tsv', multi),
            lambda h, f: run_enchant_subset(m, nat, h, [multi], f, meshes=range(-1, 10)))
    world = 141
    gt = nat.lib.mu_lang_map_text_index(world)
    mutated('map_name_text', lambda d: edit_line(d/'globaltext.txt', rf'^{gt}\t', f'{gt}\tX'),
            lambda h, f: run_map_names(m, nat, h, f, [world]))
    # NATIVE-LANG-002
    buffs = snap.tree(plain.BUFF + 0x38)
    bkey = buffs[10][0]
    mutated('buff_name', lambda d: edit_line(d/'buffs.tsv', rf'^({bkey}\t(?:[^\t]*\t){{7}})([^\t]*)', r'\1X\2'),
            lambda h, f: run_buff_subset(m, nat, h, snap, [bkey], f))
    multi = next(k for k, node in buffs if snap.u32(node + 0x14 + 0x38) - snap.u32(node + 0x14 + 0x34) >= 0x30)
    mutated('buff_line_order', lambda d: edit_line(d/'buffs.tsv', rf'^({multi}\t(?:[^\t]*\t){{8}})([^\t]*)\t([^\t\n]*)',
                                                   r'\1\3\t\2'),
            lambda h, f: run_buff_tooltip_subset(m, nat, h, snap, [multi], f))
    rows = snap.tree(plain.CHARINFO + 0x38)
    rkey = next(k for k, node in rows if snap.i32(node + 0x14 + 0x30) == 2 and snap.i32(node + 0x14 + 0x34) > 3)
    mutated('charinfo_sort', lambda d: edit_line(d/'charinfo.tsv', rf'^({rkey}\t(?:[^\t]*\t){{3}})(-?\d+)', r'\g<1>0'),
            lambda h, f: run_charinfo_rows(m, nat, h, f))
    return caught


def run_buff_subset(m, nat, h, snap, keys, fam):
    for key in keys:
        m.prepare()
        fam.check(key, client_buff(m, m.call(BUFF_GET, [key], ecx=plain.BUFF)), nat.buff(h, key))


def run_buff_tooltip_subset(m, nat, h, snap, keys, fam):
    class Subset:
        def tree(self, container):
            return [(k, n) for k, n in snap.tree(container) if k in keys]

        def __getattr__(self, name):
            return getattr(snap, name)
    run_buff_tooltip(m, nat, h, Subset(), random.Random(0), fam)


def swap_first_two(path, code):
    lines = path.read_text().split('\n')
    idx = [i for i, line in enumerate(lines) if line.startswith(f'{code}\t')]
    lines[idx[0]], lines[idx[1]] = lines[idx[1]], lines[idx[0]]
    path.write_text('\n'.join(lines))


def run_text_subset(m, nat, h, keys, fam):
    for key in keys:
        m.prepare()
        fam.check(key, m.cstr(m.call(GLOBAL_TEXT, [key], ecx=plain.TEXT)), nat.lib.mu_lang_text(h, key))


def run_skill_subset(m, nat, h, keys, fam):
    class One:
        def tree(self, _):
            return [(k, 0) for k in keys]
    run_skill_info(m, nat, h, One(), random.Random(0), fam)


def run_enchant_subset(m, nat, h, codes, fam, meshes=()):
    for code in codes:
        m.prepare()
        address = m.call(ENCHANT_FIRST, [code], ecx=plain.ENCHANT)
        fam.check(code, list(struct.unpack('<3I', m.read(address, 12))), nat.enchant(h, code))
        for k in meshes:
            m.prepare()
            address = m.call(ENCHANT_MESH, [code, k], ecx=plain.ENCHANT)
            fam.check((code, k), list(struct.unpack('<3I', m.read(address, 12))), nat.enchant(h, code, k))


if __name__ == '__main__':
    main()
