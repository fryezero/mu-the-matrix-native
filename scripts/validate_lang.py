#!/usr/bin/env python3
"""Run the client's own consumers of the Lang.mpr tables over a live snapshot (NATIVE-LANG-001).

The pinned restored text (0x00401000) and second image section run in
Unicorn (scripts/client_ui_machine.py).  The langread snapshot
(mac-play/diagnostics/langread) is mapped at its original addresses: the
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
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402

DEFAULT_TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DEFAULT_DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
MAPS_HEADER = ROOT/'native/core/mu_lang_maps.h'

GLOBAL_TEXT, GLOBAL_TEXT_STRING = 0x0095f027, 0x011753c3
SKILL_LOOKUP, SKILL_INFO = 0x00961620, 0x01696458
GATE_LOOKUP, MOVE_LOOKUP = 0x0110cbaf, 0x0113c3f5
NPC_NAME, NPC_1C, NPC_20, NPC_24 = 0x011427c7, 0x011427e0, 0x011427f9, 0x01142812
ENCHANT_FIRST, ENCHANT_MESH = 0x010ffd7a, 0x010ffddb
MAP_NAME = 0x016baaa6
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

    def __init__(self, text, data, snap):
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
        for a, b in runs:
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

    def enchant(self, h, code, mesh=None):
        out = (ctypes.c_float*3)()
        if mesh is None:
            ok = self.lib.mu_lang_enchant_first(h, code, out)
        else:
            ok = self.lib.mu_lang_enchant_mesh(h, code, mesh, out)
        return [struct.unpack('<I', struct.pack('<f', v))[0] for v in out] if ok else None


# ---- families -----------------------------------------------------------

class Family:
    def __init__(self, name):
        self.name, self.cases, self.mismatches, self.examples = name, 0, 0, []

    def check(self, label, client, native):
        self.cases += 1
        if client != native:
            self.mismatches += 1
            if len(self.examples) < 5:
                self.examples.append({'case': label, 'client': repr(client)[:120], 'native': repr(native)[:120]})

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
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(DEFAULT_DATA)))
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--families', default='map_table,text,skill_lookup,skill_info,gate,move,npc,enchant,map_names')
    parser.add_argument('--write-maps', action='store_true', help='regenerate native/core/mu_lang_maps.h')
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes are caught')
    parser.add_argument('--output')
    args = parser.parse_args()
    for path, digest in ((args.text, TEXT_SHA256), (args.data, DATA_SHA256)):
        if sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
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
        }
        for name in families:
            if name in runs:
                fam = Family(name)
                runs[name](fam)
                report['families'][name] = fam.summary()
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
    return caught


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
