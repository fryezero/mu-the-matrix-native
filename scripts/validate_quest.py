#!/usr/bin/env python3
"""Run the client's quest routines in Unicorn and compare them with reconstructed/quest (NATIVE-QUEST-001).

The pinned restored text (0x00401000) and second image section run in
Unicorn (scripts/client_ui_machine.py through validate_lang.LangMachine).
The langread snapshot (mac-play/diagnostics/langread with
node:0x137c=0x118 and the quest system maps, see docs/research/client-quests.md)
is mapped at its original addresses: the Lang tables (MUQuest, MUQuestString,
GlobalText, Npcname, ItemLevelTooltip) and the client's own quest system
singleton [0x01ec2e60] as the running client built it.  libquest (ctypes)
loads the plaintext scripts/live_lang_to_plain.py writes from the same
snapshot.

Families:

* category: 0x00fe1a06 for indices -10..1100;
* runtime: the live quest system of the snapshot (every quest object, every
  dialogue with its pages, the categories) against libquest's build;
* build: the client's builder 0x00fe249e + 0x00fe138b + 0x00fe15e9 (and the
  dialogue scan 0x00fe764a) run for every MUQuest record on a fresh object,
  then walked like the live one;
* lookup: 0x00fe14d4, 0x00fe1695, 0x00fe1506 and 0x00fe1555 for every index,
  absent indices and codes;
* text: the goal line 0x00fe1a52 and the reward lines 0x00fe1e92 for every
  quest x random states, counts and item answers;
* html: the line formatter 0x0096fe90 on random texts and colours;
* packets: random sequences of the quest packets (F6 0x6f 0x70 0x71 0x72 0x73
  0x74 0x75 0x81 0x82 0x83) through the dispatcher's handlers with the windows
  (NpcQuestProgress, MyQuestInfo, npcdialogue) constructed by their own
  constructors: after each packet the quest objects, the category sets, the
  maps +0x1c / +0x24 and every effect (GFx invokes with their arguments,
  show / hide, packets sent, message boxes, notices, the summary HUD);
* windows: the windows' routines driven directly (NpcQuestProgress pages,
  select, confirm, open, close, callbacks; npcdialogue's quest list and its
  choice; MyQuestInfo open, tabs, list, select, give up, actions).

Modelled (not client code): operator new / delete (a bump heap), the
iostreams (std::stringstream as a byte string: constructor 0x00969613,
str 0x0096a5b7 / 0x0096a583, << 0x00944605 / 0x0094437f, clear 0x0094f781),
sprintf 0x009619dd (C conversions), the ANSI -> UTF-8 conversion 0x00a99d93
(bytes copied), the GDI font selection 0x011a07b2 / 0x011a0a4e, the text
wrap 0x011ff794 (one line, the text cut to 0x7f bytes) and fit 0x011ff6fc
(cut to 63 bytes), the item manager (0x00cd4ea8 / 0x00cd61a8 names,
0x00cd5fac / 0x00cd6017 kind answers: random per case, given to both
sides), the map-name function 0x016baaa6 ("Map <n>"), the GFx manager and
its windows' Scaleform side (0x00ac3bf7, IsVisible 0x00aae6f9, show
0x00aae420, hide 0x00aae470, invoke 0x00aae7e0, invoke-with-value
0x00aaf3ef and the GFx value calls), the packet send 0x00d51d4f (the built
bytes recorded), the message boxes 0x00b3967c / 0x00b39648, the chat notice
0x0095f4ec, the quest summary HUD (0x00be5cd7 lock, 0x00c89ff9 add,
0x00c8a072 remove, 0x00c8a0ce clear, 0x00c8a0eb update), the dialogue
manager's QuestWords lookup 0x00fdc9c1 (fixed texts), the hero's name
0x00a00358 and the classic quest manager call 0x009f4c3f.  The XOR layer of
sub-codes 0x70 / 0x71 runs with its hash routines (0x00d50954, 0x00d509b6,
0x00d50b0b) stubbed, so the key is zero and the payload passes unchanged.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402

QS_PTR = 0x01ec2e60
MUQUEST, MUQUESTSTRING = 0x06fbbddc, 0x06fbbd9c
FONT_A, FONT_B = 0x06fc9ca4, 0x06fc9ca8
FONT_A_VALUE, FONT_B_VALUE = 0x11110000, 0x22220000

CATEGORY, QS_CTOR, ADD_QUEST, ADD_DIALOGUE = 0x00fe1a06, 0x00fe249e, 0x00fe138b, 0x00fe15e9
GET_QUEST, GET_DIALOGUE, GET_CATEGORY, ITEM_VALUE = 0x00fe14d4, 0x00fe1695, 0x00fe1506, 0x00fe1555
CONDITION, REWARD, HTML_LINE = 0x00fe1a52, 0x00fe1e92, 0x0096fe90
SPRINTF, STRCPY, NEW, MALLOC = 0x009619dd, 0x01983a90, 0x0191ba7b, 0x0191bab9
DUMMY = 0x0bf00000
ITEM_MANAGER = 0x0bf10000


def i32(v):
    return struct.unpack('<i', struct.pack('<I', v & 0xffffffff))[0]


# ---- client memory helpers ----------------------------------------------------------------------

def std_string(m, address):
    size, cap = struct.unpack('<II', m.read(address + 0x10, 8))
    if size > 0x100000 or cap < size:
        raise cm.CaseError(f'bad std::string at {address:#x}')
    return m.read(address if cap < 16 else m.u32(address), size)


def write_std_string(m, address, payload):
    payload = bytes(payload)
    if len(payload) < 16:
        m.write(address, payload + bytes(16 - len(payload)) + struct.pack('<II', len(payload), 15))
    else:
        buf = m.cstring(payload)
        m.write(address, struct.pack('<I', buf) + bytes(12) + struct.pack('<II', len(payload), len(payload)))


def tree(m, container):
    """(key, node) of an MSVC std::map in emulated memory (head pointer at container, size at +4)."""
    head, size = m.u32(container), m.u32(container + 4)
    out, stack = [], []
    root = m.u32(head + 4)
    if root != head:
        stack.append(root)
    while stack:
        node = stack.pop()
        left, _, right = struct.unpack('<III', m.read(node, 12))
        out.append((i32(m.u32(node + 0x10)), node))
        if left != head:
            stack.append(left)
        if right != head:
            stack.append(right)
        if len(out) > size + 1:
            raise cm.CaseError(f'map {container:#x} is not a tree')
    if len(out) != size:
        raise cm.CaseError(f'map {container:#x}: {len(out)} nodes for size {size}')
    out.sort()
    return out


def deque_strings(m, d):
    """MSVC std::deque<std::string> (proxy +0, map +4, mapsize +8, offset +0xc, size +0x10; 1 element / block)."""
    block_map, map_size, off, size = struct.unpack('<IIII', m.read(d + 4, 16))
    out = []
    for k in range(size):
        idx = off + k
        block = m.u32(block_map + 4 * (idx % map_size))
        out.append(std_string(m, block))
    return out


# ---- the machine ----------------------------------------------------------------------------------

class QuestMachine(vl.LangMachine):
    def __init__(self, text, data, snap):
        super().__init__(text, data, snap)
        self.ss = {}            # stringstream base -> bytearray
        self.items = {}         # code -> name bytes
        self.kinds = {}         # (code, kind) -> 0/1
        self.bytes_ = {}        # (code, value) -> 0/1
        self.strings = {}       # address -> bytes (stub-made C strings kept alive)

    def cstring(self, payload):
        """A C string on the case heap, defined to the next 16 bytes (the CRT reads whole dwords)."""
        size = (len(payload) + 1 + 15) & ~15
        buf = self.alloc(size, define=True)
        self.write(buf, payload + bytes(size - len(payload)))
        return buf

    def setup(self):
        """prepare(force) plus the modelled statics and stubs."""
        self.prepare(force=True)
        vl.crt_state(self)
        self.put32(FONT_A, FONT_A_VALUE)
        self.put32(FONT_B, FONT_B_VALUE)
        self.ss.clear()
        self.vb_ss = self.alloc(16, define=True)
        self.write(self.vb_ss, struct.pack('<II', 0, 0x68))
        self.vb_os = self.alloc(16, define=True)
        self.write(self.vb_os, struct.pack('<II', 0, 0x58))

    def ss_base(self, address):
        for base in (address, address - 0x10, address - 0x18, address - 0x68):
            if base in self.ss:
                return base
        raise cm.CaseError(f'no stringstream at {address:#x}')


def install_stubs(m):
    vl.heap_stubs(m)

    # iostreams (modelled)
    def ss_ctor(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        mm.ss[this] = bytearray()
        mm.write(this, struct.pack('<I', mm.vb_ss))
        mm.write(this + 0x10, struct.pack('<I', mm.vb_os))
        return this
    m.stub(0x00969613, ss_ctor, 4)

    def ss_dtor(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        mm.ss.pop(this, None)
        return 0
    m.stub(0x00969a1b, ss_dtor, 0)

    def ss_str(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        out, = mm.args(1)
        write_std_string(mm, out, mm.ss[mm.ss_base(this)])
        return out
    m.stub(0x0096a5b7, ss_str, 4)

    def ss_set(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        src, = mm.args(1)
        mm.ss[mm.ss_base(this)] = bytearray(std_string(mm, src))
        return 0
    m.stub(0x0096a583, ss_set, 4)

    def ss_put_cstr(mm):
        os_, s = mm.args(2)
        mm.ss[mm.ss_base(os_)] += mm.cstr(s)
        return os_
    m.stub(0x00944605, ss_put_cstr, 0)

    def ss_put_string(mm):
        os_, s = mm.args(2)
        mm.ss[mm.ss_base(os_)] += std_string(mm, s)
        return os_
    m.stub(0x0094437f, ss_put_string, 0)
    m.stub(0x0094f781, lambda mm: 0, 8)

    # sprintf (modelled)
    def sprintf(mm):
        words = mm.args(24)
        buf, fmt = words[0], mm.cstr(words[1])
        out = c_format(mm, fmt, words[2:])
        mm.write(buf, out + b'\0')
        return len(out)
    m.stub(SPRINTF, sprintf, 0)

    def to_utf8(mm):
        dst, src = mm.args(2)
        write_std_string(mm, dst, std_string(mm, src))
        return dst
    m.stub(vl.TO_UTF8, to_utf8, 0)

    # fonts
    m.stub(0x011a07b2, lambda mm: DUMMY, 0)
    m.stub(0x011a0a4e, lambda mm: 0, 4)

    # the item manager
    m.stub(0x00cd4ea8, lambda mm: ITEM_MANAGER, 0)

    def item_name(mm):
        code, buf = mm.args(2)
        name = mm.items.get(code)
        mm.write(buf, (name or b'') + b'\0')
        return 1 if name is not None else 0
    m.stub(0x00cd61a8, item_name, 8)
    m.stub(0x00cd5fac, lambda mm: mm.kinds.get(tuple(mm.args(2)), 0), 8)
    m.stub(0x00cd6017, lambda mm: mm.bytes_.get(tuple(mm.args(2)), 0), 8)

    # boost::format in the line formatter 0x0096fe90 (modelled): constructor 0x0096e8c7(fmt), % unsigned
    # 0x0096c6ea, % std::string 0x0096c702, str 0x0097258c, destructor 0x0096f4ae
    formats = {}

    def fmt_ctor(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        fmt, = mm.args(1)
        formats[this] = (mm.cstr(fmt), [])
        return this
    m.stub(0x0096e8c7, fmt_ctor, 4)

    def fmt_uint(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        p, = mm.args(1)
        formats[this][1].append(('i', mm.u32(p)))
        return this
    m.stub(0x0096c6ea, fmt_uint, 4)

    def fmt_string(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        p, = mm.args(1)
        formats[this][1].append(('s', std_string(mm, p)))
        return this
    m.stub(0x0096c702, fmt_string, 4)

    def fmt_str(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        out, = mm.args(1)
        fmt, args = formats[this]
        write_std_string(mm, out, typed_format(fmt, args))
        return out
    m.stub(0x0097258c, fmt_str, 4)

    def fmt_dtor(mm):
        formats.pop(mm.uc.reg_read(cm.UC_X86_REG_ECX), None)
        return 0
    m.stub(0x0096f4ae, fmt_dtor, 0)

    def map_name(mm):
        world, = mm.args(1)
        return mm.cstring(b'Map %d' % i32(world))
    m.stub(0x016baaa6, map_name, 0)


def c_format(m, fmt, words):
    """The modelled sprintf: d i u x X c (one word), s (a C string), with flags, width, precision, l/h."""
    out = bytearray()
    i, arg = 0, 0
    spec = re.compile(rb'%([-+ #0]*)(\d*)(?:\.(\d+))?([lh]*)([diuxXcs%])')
    while i < len(fmt):
        mt = spec.match(fmt, i) if fmt[i:i + 1] == b'%' else None
        if not mt:
            out.append(fmt[i])
            i += 1
            continue
        flags, width, prec, _, conv = mt.groups()
        i = mt.end()
        if conv == b'%':
            out += b'%'
            continue
        w = words[arg] if arg < len(words) else 0
        arg += 1
        pyspec = '%' + flags.decode() + width.decode() + ('.' + prec.decode() if prec is not None else '')
        if conv == b's':
            s = m.cstr(w) if w else b''
            if prec is not None:
                s = s[:int(prec)]
            pad = int(width) if width else 0
            s = (s.ljust(pad) if b'-' in flags else s.rjust(pad))
            out += s
        elif conv == b'c':
            out += bytes([w & 0xff])
        elif conv in (b'u', b'x', b'X'):
            out += (pyspec + ('d' if conv == b'u' else conv.decode())) .__mod__(w & 0xffffffff).encode()
        else:
            out += (pyspec + 'd').__mod__(i32(w)).encode()
    return bytes(out)


def typed_format(fmt, args):
    """printf directives over typed arguments (('i', word) or ('s', bytes)), for the boost::format model."""
    out = bytearray()
    i, k = 0, 0
    spec = re.compile(rb'%([-+ #0]*)(\d*)(?:\.(\d+))?([lh]*)([diuxXs%])')
    while i < len(fmt):
        mt = spec.match(fmt, i) if fmt[i:i + 1] == b'%' else None
        if not mt:
            out.append(fmt[i])
            i += 1
            continue
        flags, width, prec, _, conv = mt.groups()
        i = mt.end()
        if conv == b'%':
            out += b'%'
            continue
        kind, value = args[k] if k < len(args) else ('s', b'')
        k += 1
        pyspec = '%' + flags.decode() + width.decode() + ('.' + prec.decode() if prec is not None else '')
        if conv == b's':
            out += value if kind == 's' else str(value).encode()
        elif conv in (b'u', b'x', b'X'):
            out += (pyspec + ('d' if conv == b'u' else conv.decode())).__mod__(value & 0xffffffff).encode()
        else:
            out += (pyspec + 'd').__mod__(i32(value)).encode()
    return bytes(out)


# ---- the native library ------------------------------------------------------------------------------

TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)   # returns a kept buffer's address
KIND_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
UTF8_FN = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t)


class Host(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('data', ctypes.c_void_p), ('text', TEXT_FN), ('npc_name', TEXT_FN),
                ('map_name', TEXT_FN), ('item_name', TEXT_FN), ('item_kind', KIND_FN), ('item_byte', KIND_FN),
                ('to_utf8', ctypes.c_void_p)]


class QuestData(ctypes.Structure):
    _fields_ = [('records', ctypes.c_void_p), ('nrecords', ctypes.c_size_t), ('strings', ctypes.c_void_p),
                ('nstrings', ctypes.c_size_t), ('level_tips', ctypes.c_void_p), ('nlevel_tips', ctypes.c_size_t)]


class Dialogue(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('title', ctypes.c_char_p), ('progress', ctypes.c_char_p),
                ('complete', ctypes.c_char_p), ('summary', ctypes.c_char_p),
                ('pages', ctypes.POINTER(ctypes.c_char_p)), ('npages', ctypes.c_int32)]


class QuestLine(ctypes.Structure):
    _fields_ = [('font', ctypes.c_uint32), ('color', ctypes.c_uint32), ('text', ctypes.c_char * 1024)]


def build_variant(mutation, out_dir):
    """libquest with a planted mistake (-DMU_QUEST_MUTATION=k)."""
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = Path(out_dir)/f'libquest-m{mutation}.{suffix}'
    src = sorted(str(p) for p in (ROOT/'reconstructed/quest').glob('quest_*.c'))
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-shared', f'-DMU_QUEST_MUTATION={mutation}', *src,
                    '-o', str(lib)], check=True)
    return lib


class Native:
    """libquest with the snapshot's tables as plaintext and Python-side host lookups."""

    def __init__(self, snap, plain_dir, lib_path=None):
        suffix = 'dylib' if sys.platform == 'darwin' else 'so'
        if lib_path is None:
            subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/quest')], check=True)
            lib_path = ROOT/f'reconstructed/quest/libquest.{suffix}'
        L = self.lib = ctypes.CDLL(str(lib_path))
        L.mu_quest_load_dir.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.mu_quest_load_dir.restype = ctypes.c_long
        L.mu_quest_client_size.restype = ctypes.c_size_t
        L.mu_quest_client_init.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        L.mu_quest_client_free.argtypes = [ctypes.c_void_p]
        L.mu_quest_log_text.argtypes = [ctypes.c_void_p]
        L.mu_quest_log_text.restype = ctypes.c_char_p
        L.mu_quest_log_clear.argtypes = [ctypes.c_void_p]
        L.mu_quest_client_field.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int32]
        L.mu_quest_client_field.restype = ctypes.c_int32
        L.mu_quest_fields.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        L.mu_quest_set_fields.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                                          ctypes.c_int32]
        L.mu_quest_maps_text.argtypes = [ctypes.c_void_p]
        L.mu_quest_maps_text.restype = ctypes.c_char_p
        L.mu_quest_category.argtypes = [ctypes.c_int32]
        L.mu_quest_category.restype = ctypes.c_int32
        L.mu_quest_receive.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_quest_condition.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(QuestLine)]
        L.mu_quest_reward.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                       ctypes.POINTER(QuestLine)]
        L.mu_quest_get.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_quest_get.restype = ctypes.c_void_p
        L.mu_quest_html_line.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                         ctypes.c_size_t]
        L.mu_quest_client_log_clear.argtypes = [ctypes.c_void_p]
        L.mu_quest_dialogue_get.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_quest_dialogue_get.restype = ctypes.c_void_p
        L.mu_quest_set_hero.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.mu_quest_set_dialogue_words.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        L.mu_quest_dialog_set_text.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32]
        self.data = QuestData()
        n = L.mu_quest_load_dir(ctypes.byref(self.data), str(plain_dir).encode())
        if n <= 0:
            raise SystemExit('validate_quest: the snapshot has no full MUQuest records (langread node:0x137c=0x118)')
        self.texts = {k: v for k, v in plain.read_text(snap)}
        self.npcs = {r['index']: r['name'] for r in plain.read_npcs(snap)}
        self.items, self.kinds, self.bytes_ = {}, {}, {}
        self.keep = {}
        self.host = Host()
        self.host.text = TEXT_FN(lambda u, i: self._keep(('t', i), self.texts.get(i)))
        self.host.npc_name = TEXT_FN(lambda u, i: self._keep(('n', i), self.npcs.get(i, b'')))
        self.host.map_name = TEXT_FN(lambda u, i: self._keep(('m', i), b'Map %d' % i))
        self.host.item_name = TEXT_FN(lambda u, c: self._keep(('i', c), self.items.get(c, b'')))
        self.host.item_kind = KIND_FN(lambda u, c, k: self.kinds.get((c, k), 0))
        self.host.item_byte = KIND_FN(lambda u, c, k: self.bytes_.get((c, k), 0))
        self.host.data = ctypes.cast(ctypes.byref(self.data), ctypes.c_void_p)
        self.words_fn = TEXT_FN(lambda u, i: self._keep(('w', i), DIALOGUE_WORDS.get(i)))
        self.client = ctypes.create_string_buffer(L.mu_quest_client_size())
        self.reset()

    def _keep(self, key, value):
        if value is None:
            return None
        if key not in self.keep or self.keep[key].value != value:
            self.keep[key] = ctypes.create_string_buffer(value)
        return ctypes.addressof(self.keep[key])

    def reset(self):
        if getattr(self, '_inited', False):
            self.lib.mu_quest_client_free(self.client)
        if self.lib.mu_quest_client_init(self.client, ctypes.byref(self.data), ctypes.byref(self.host)):
            raise SystemExit('libquest: client init failed')
        self._inited = True
        self.lib.mu_quest_set_hero(self.client, HERO_NAME)
        self.lib.mu_quest_set_dialogue_words(self.client, ctypes.cast(self.words_fn, ctypes.c_void_p))

    def field(self, name, value=None):
        return self.lib.mu_quest_client_field(self.client, name.encode(), value is not None, value or 0)

    def log(self):
        return self.lib.mu_quest_log_text(self.client).decode('latin1').splitlines()

    def clear_log(self):
        self.lib.mu_quest_client_log_clear(self.client)

    def dialogue(self, index):
        p = self.lib.mu_quest_dialogue_get(self.client, index)
        if not p:
            return None
        g = Dialogue.from_address(p)
        pages = [g.pages[i] for i in range(g.npages)]
        return (g.index, g.title, g.progress, g.complete, g.summary, pages)

    def quest_fields(self, index):
        out = (ctypes.c_int32 * 4)()
        ok = self.lib.mu_quest_fields(self.client, index, out)
        return list(out) if ok else None


HERO_NAME = b'Nighty'
DIALOGUE_WORDS = {0x5dd: b'Quests of this NPC', 0x5de: b'No quest for you', 0x3ef: b'Leave'}


# ---- families ----------------------------------------------------------------------------------------

class Family:
    def __init__(self, name):
        self.name, self.cases, self.mismatches, self.examples = name, 0, 0, []
        self.last = None

    def check(self, label, client, native):
        self.cases += 1
        if client != native:
            self.mismatches += 1
            if len(self.examples) < 6:
                if isinstance(client, list) and isinstance(native, list):
                    k = next((i for i, (a, b) in enumerate(zip(client, native)) if a != b), min(len(client), len(native)))
                    self.examples.append({'case': repr(label)[:200], 'first_diff': k,
                                          'client': client[k:k + 3], 'native': native[k:k + 3],
                                          'lengths': [len(client), len(native)]})
                else:
                    self.examples.append({'case': repr(label)[:200], 'client': repr(client)[:600],
                                          'native': repr(native)[:600]})

    def summary(self):
        return {'cases': self.cases, 'mismatches': self.mismatches, 'examples': self.examples}


def run_category(m, nat, rng, fam):
    m.setup()
    for index in list(range(-10, 1101)) + [rng.randint(-100000, 100000) for _ in range(200)]:
        fam.check(index, i32(m.call(CATEGORY, [index & 0xffffffff])), nat.lib.mu_quest_category(index))


def live_system(m_or_snap, qs, read_string, u32):
    """The quest system's maps as comparable values (works on the snapshot or on emulated memory)."""
    return None


def walk_system(m, qs):
    """Quest objects, dialogues and categories of a quest system object in emulated memory."""
    quests = {}
    for key, node in tree(m, qs + 4):
        q = m.u32(node + 0x14)
        rec = m.u32(q)
        quests[key] = (m.u32(rec) if rec else None, i32(m.u32(q + 4)), std_string(m, q + 8),
                       i32(m.u32(q + 0x20)), i32(m.u32(q + 0x24)), i32(m.u32(q + 0x28)), i32(m.u32(q + 0x2c)),
                       i32(m.u32(q + 0x30)), m.read(q + 0x34, 1)[0])
    dialogues = {}
    for key, node in tree(m, qs + 0x14):
        g = m.u32(node + 0x14)
        pages = [(k, std_string(m, n + 0x14)) for k, n in tree(m, g + 0x64)]
        dialogues[key] = (i32(m.u32(g)), std_string(m, g + 4), std_string(m, g + 0x1c), std_string(m, g + 0x34),
                          std_string(m, g + 0x4c), [p for _, p in pages])
    categories = {}
    for key, node in tree(m, qs + 0xc):
        c = m.u32(node + 0x14)
        categories[key] = (i32(m.u32(c)), [k for k, _ in tree(m, c + 4)])
    return quests, dialogues, categories


def native_system(nat, data_records, strings):
    """libquest's build expressed like walk_system: its quest objects (fields through mu_quest_fields, the record
    name and +0x1c/+0x20 copies) and its dialogues (mu_quest_dialogue_get)."""
    quests, dialogues = {}, {}
    for r in data_records:
        index = r[0]
        f = nat.quest_fields(index)
        if f is not None:
            quests[index] = (index, index, r[1], r[2], r[3], f[3], f[0], f[1], f[2])
        g = nat.dialogue(index)
        if g is not None:
            dialogues[index] = g
    categories = {k: (k, []) for k in (2, 3, 4)}
    return quests, dialogues, categories


def run_runtime(m, nat, snap, records, strings, fam):
    """The running client's quest system (snapshot) against libquest's build.  The C side's dialogue texts come
    from its own build; native_system re-derives them the same way, so this family compares the structure the
    client built at run time with the plaintext tables libquest builds from."""
    m.setup()
    qs = m.u32(QS_PTR)
    client = walk_system(m, qs)
    native = native_system(nat, records, strings)
    for part, c_map, n_map in zip(('quest', 'dialogue', 'category'), client, native):
        fam.check((part, 'keys'), sorted(c_map), sorted(n_map))
        for key in sorted(c_map):
            fam.check((part, key), c_map[key], n_map.get(key))


def run_build(m, nat, records, strings, fam):
    """The client's builder on a fresh object: 0x00fe249e, then 0x00fe138b / 0x00fe15e9 for every record."""
    m.setup()
    obj = m.alloc(0x2c, define=True)
    m.call(QS_CTOR, [], ecx=obj)
    m.put32(QS_PTR, obj)
    for r in records:
        m.call(ADD_QUEST, [r[0]], ecx=obj)
        m.call(ADD_DIALOGUE, [r[0]], ecx=obj)
    client = walk_system(m, obj)
    native = native_system(nat, records, strings)
    for part, c_map, n_map in zip(('quest', 'dialogue', 'category'), client, native):
        fam.check((part, 'keys'), sorted(c_map), sorted(n_map))
        for key in sorted(c_map):
            fam.check((part, key), c_map[key], n_map.get(key))


def run_lookup(m, nat, records, rng, fam):
    m.setup()
    qs = m.u32(QS_PTR)
    keys = [r[0] for r in records]
    present = set(keys)
    absent = [k for k in rng.sample(range(-50, 2000), 400) if k not in present][:150]
    quests = {k: m.u32(n + 0x14) for k, n in tree(m, qs + 4)}
    dialogues = {k: m.u32(n + 0x14) for k, n in tree(m, qs + 0x14)}
    for index in keys + absent:
        q = m.call(GET_QUEST, [index & 0xffffffff], ecx=qs)
        fam.check(('quest', index), (q != 0, q == quests.get(index, 0)), (nat.quest_fields(index) is not None, True))
        g = m.call(GET_DIALOGUE, [index & 0xffffffff], ecx=qs)
        fam.check(('dialogue', index), g, dialogues.get(index, 0))
    cats = {k: m.u32(n + 0x14) for k, n in tree(m, qs + 0xc)}
    for c in range(-3, 9):
        fam.check(('category', c), m.call(GET_CATEGORY, [c & 0xffffffff], ecx=qs) != 0, c in cats)
    for code in rng.sample(range(0, 0x3000), 200):
        fam.check(('item', code), i32(m.call(ITEM_VALUE, [code], ecx=qs)), -1)


def line_of(m, out):
    return (m.u32(out), m.u32(out + 4), std_string(m, out + 8))


def randomize_items(m, nat, rng, codes):
    m.items, m.kinds, m.bytes_ = {}, {}, {}
    for code in codes:
        if rng.random() < 0.9:
            m.items[code] = b'Item %d' % code if rng.random() < 0.8 else b'Ancient <Sword> %d' % code
        for kind in (0x19, 0x1a, 1, 3):
            m.kinds[(code, kind)] = 1 if rng.random() < 0.15 else 0
        m.bytes_[(code, 0x2c)] = 1 if rng.random() < 0.1 else 0
    nat.items, nat.kinds, nat.bytes_ = dict(m.items), dict(m.kinds), dict(m.bytes_)


def quest_codes(record):
    goal = record[5]
    codes = [goal[2] * 0x200 + goal[3]]
    for i in range(3):
        codes.append(goal[14 + 3 * i] * 0x200 + goal[15 + 3 * i])
    return codes


def run_text(m, nat, records, rng, fam, rounds):
    m.setup()
    qs = m.u32(QS_PTR)
    quests = {k: m.u32(n + 0x14) for k, n in tree(m, qs + 4)}
    native_ptr = {r[0]: nat.lib.mu_quest_get(nat.client, r[0]) for r in records}
    for r in records:
        index = r[0]
        q = quests[index]
        for k in range(rounds):
            state = rng.choice([0, 1, 2, 3, 4, rng.randint(-2, 9)])
            count = rng.choice([0, 1, rng.randint(0, 200), rng.randint(0, 65535)])
            randomize_items(m, nat, rng, quest_codes(r))
            m.uc.mem_write(q + 0x2c, struct.pack('<ii', state, count))   # snapshot memory: not a case page
            nat.lib.mu_quest_set_fields(nat.client, index, state, count, 0)
            for routine, fn in ((CONDITION, 'condition'), (REWARD, 'reward')):
                out = m.alloc(0x40, define=True)
                m.call(routine, [out, q])
                client = line_of(m, out)
                line = QuestLine()
                if fn == 'condition':
                    nat.lib.mu_quest_condition(ctypes.byref(nat.host), native_ptr[index], FONT_A_VALUE, ctypes.byref(line))
                else:
                    nat.lib.mu_quest_reward(ctypes.byref(nat.host), native_ptr[index], FONT_A_VALUE, FONT_B_VALUE, ctypes.byref(line))
                fam.check((fn, index, state, count), client, (line.font, line.color, line.text))
            if m.heap_next - cm.HEAP_BASE > 0x2000000:
                m.setup()


def run_html(m, nat, rng, fam, cases):
    m.setup()
    samples = [b'', b'\n', b'Hunt <boss> x 3/5', b'plain', b'a<b<c', b'Exp.: 50\nZen: 50', b'<', b'x' * 300]
    for k in range(cases):
        text = rng.choice(samples) if k < 64 else bytes(rng.choice(b'ab <>\n&;#xyz') for _ in range(rng.randint(0, 40)))
        color = rng.choice([0xff67bfdf, 0xff1e1eff, rng.getrandbits(32)])
        bold, br = rng.randint(0, 2), rng.randint(0, 2)
        m.setup()
        out = m.alloc(0x40, define=True)
        write_std_string(m, out, b'')
        src = m.cstring(text)
        m.call(HTML_LINE, [out, src, color, bold, br])
        client = std_string(m, out)
        buf = ctypes.create_string_buffer(8192)
        nat.lib.mu_quest_html_line(text, color, bold, br, buf, 8192)
        fam.check((text, hex(color), bold, br), client, buf.value)



# ---- the windows' world ----------------------------------------------------------------------------------

NQP_VTABLE, MQI_VTABLE = 0x01a95784, 0x01a94f70
MGR_SIZE = 0x400
HERO = 0x01d1df1c
SUMMARY_REF = 0x01d22c60
SUMMARY = 0x0bf20000
MSGBOX = 0x0bf30000
FAKE_VIEW = 0x0bf40000
FAKE_IFACE = 0x77777770
DLG_QUESTWORDS = 0x00fdc9c1
SET_CONTENTS, SHOW_PAGE, REFRESH = 0x00bee2b3, 0x00bee333, 0x00bee997
NQP_OPEN, NQP_CLOSE, NQP_ONLOAD, NQP_SELECT, NQP_CONFIRM, NQP_BUTTON = (0x00bedfb4, 0x00bee1fa, 0x00bedd69,
                                                                       0x00beebc2, 0x00beec0b, 0x00beea7a)
DLG_QUESTS, DLG_CHOICE = 0x00be9c75, 0x00be906d
MQI_OPEN, MQI_CLOSE, MQI_ONLOAD, MQI_TABS, MQI_CHECKED = 0x00be420e, 0x00be42dc, 0x00be3ab5, 0x00be4922, 0x00be4732
MQI_GIVEUP_BOX = 0x00be436d
TAB_CTOR, TAB_INIT, TAB_SHOW, TAB_SELECT, TAB_LIST, TAB_ACTION = (0x00d4f16e, 0x00d4f285, 0x00d4f2e0, 0x00d4f3ac,
                                                                 0x00d4f485, 0x00d50067)
HANDLERS = {0x6f: 0x012510fe, 0x70: 0x0125313f, 0x71: 0x0126d65c, 0x72: 0x01222933, 0x73: 0x0122287a,
            0x74: 0x0122adf5, 0x75: 0x01253577, 0x81: 0x012533c9, 0x82: 0x01253713, 0x83: 0x01253113}


def json_bytes(b):
    out = bytearray(b'"')
    for c in b:
        if c in (0x22, 0x5c):
            out += b'\\' + bytes([c])
        elif c < 0x20:
            out += b'\\u%04x' % c
        else:
            out.append(c)
    out += b'"'
    return bytes(out)


def json_number(v):
    t = format(v, '.17g')
    return t.encode()


class World:
    """The emulated windows, the GFx manager and the effect log of one case."""

    def __init__(self, m, snap):
        self.m = m
        self.texts = dict(plain.read_text(snap))
        self.restore = self._quest_system_blocks(snap)
        self.log = []
        self.flags = {}
        self.values = {}
        self.packets = {}
        self.summary = False
        self.names = {}

    def _quest_system_blocks(self, snap):
        """The bytes of the live quest system the handlers modify: the object, its map heads, the category
        objects and their heads, every quest object."""
        qs = snap.u32(QS_PTR)
        blocks = [(qs, snap.read(qs, 0x2c))]
        for off in (4, 0xc, 0x14, 0x1c, 0x24):
            head = snap.u32(qs + off)
            blocks.append((head, snap.read(head, 0x10)))
        for _, node in snap.tree(qs + 0xc):
            c = snap.u32(node + 0x14)
            blocks.append((c, snap.read(c, 0xc)))
            head = snap.u32(c + 4)
            blocks.append((head, snap.read(head, 0x10)))
        for _, node in snap.tree(qs + 4):
            q = snap.u32(node + 0x14)
            blocks.append((q, snap.read(q, 0x38)))
        return blocks

    def reset(self, summary=False):
        m = self.m
        m.setup()
        for address, payload in self.restore:
            m.uc.mem_write(address, payload)
        self.log, self.flags, self.values, self.packets, self.sizes = [], {}, {}, {}, {}
        self.summary = summary
        m.put32(HERO, m.alloc(0x400, define=True))
        m.put32(0x01d22c6c, DUMMY)       # the chat window the notices go to
        m.write(0x06fca280, bytes(16))   # the XOR key bytes of sub-codes 0x70 / 0x71 (the hash is stubbed)
        self.view = m.alloc(0x10, define=True)
        vt = m.alloc(0x80, define=True)
        m.put32(self.view, vt)
        for slot, fn in self.view_fns.items():
            m.put32(vt + slot, fn)
        mgr = self.mgr = m.alloc(MGR_SIZE, define=True)
        # NpcQuestProgress (0x168 bytes): the fields its routines use
        nqp = self.nqp = m.alloc(0x168, define=True)
        m.put32(nqp, NQP_VTABLE)
        m.call(0x00beef32, [], ecx=nqp + 0x80)
        m.call(0x008e6d00, [], ecx=nqp + 0x94)
        m.call(0x00969613, [1], ecx=nqp + 0xb0)
        m.put32(nqp + 0x7c, 0)
        m.put32(nqp + 0x160, 0xffffffff)
        # npcdialogue (0x1d80 bytes)
        dlg = self.dlg = m.alloc(0x1d80, define=True)
        m.call(0x008e6d00, [], ecx=dlg + 0x1d68)
        # MyQuestInfo (0x88 bytes): the tab map with the quest tabs (their constructor) and stand-ins for 0, 1
        mqi = self.mqi = m.alloc(0x88, define=True)
        m.put32(mqi, MQI_VTABLE)
        m.call(0x00be6959, [], ecx=mqi + 0x80)
        self.tabs = {}
        for tab in range(5):
            if tab >= 2:
                obj = m.alloc(0xc4, define=True)
                m.call(TAB_CTOR, [tab], ecx=obj)
            else:
                obj = self.dummy_tab(tab)
            self.tabs[tab] = obj
            pair = m.alloc(16, define=True)
            key = m.alloc(16, define=True)
            val = m.alloc(16, define=True)
            m.put32(key, tab)
            m.put32(val, obj)
            m.call(0x00be6767, [pair, key, val])
            out = m.alloc(16, define=True)
            m.call(0x00be6744, [out, pair], ecx=mqi + 0x80)
        m.write(mqi + 0x7c, b'\1')
        m.put32(mgr + 0xf0, dlg)
        m.put32(mgr + 0x10c, nqp)
        m.put32(mgr + 0x114, mqi)
        m.put32(mgr + 0x88, MSGBOX)
        self.names = {nqp: b'NpcQuestProgress', mqi: b'MyQuestInfo', dlg: b'npcdialogue'}

    def dummy_tab(self, tab):
        """Tabs 0 (guide quest) and 1 (class upgrade) are not played: a vtable of recorders."""
        m = self.m
        obj = m.alloc(0xc4, define=True)
        vt = m.alloc(0x40, define=True)
        m.put32(obj, vt)
        m.put32(obj + 0xbc, tab)
        for slot, what in ((4, 'init'), (8, 'close')):
            m.put32(vt + slot, self.tab_fns[(tab, what)])
        # their constructors (0x00d4c27a, 0x00d4e90b) name them with GlobalText 0x1479 / 0xb05
        write_std_string(m, obj + 0xa4, self.texts.get(0x1479 if tab == 0 else 0xb05, b''))
        return obj

    def name(self, window):
        return self.names.get(window, b'?%x' % window)

    # value model
    def value_of(self, address):
        m = self.m
        kind = m.u32(address + 4)
        if kind == 2:
            return ('b', m.read(address + 8, 1)[0] != 0)
        if kind == 3:
            return ('n', struct.unpack('<d', m.read(address + 8, 8))[0])
        if kind == 4:
            return ('s', m.cstr(m.u32(address + 8)))
        if m.u32(address) == FAKE_IFACE:
            return ('r', m.u32(address + 8))
        return ('u', None)

    def render(self, v):
        kind, x = v
        if kind == 'b':
            return b'true' if x else b'false'
        if kind == 'n':
            return json_number(x)
        if kind == 's':
            return json_bytes(x)
        if kind == 'r':
            node = self.values[x]
            if node[0] == 'obj':
                return b'{' + b','.join(json_bytes(k)[0:] + b':' + self.render(val) for k, val in node[1]) + b'}'
            items = node[1]
            n = max(max(items) + 1 if items else 0, self.sizes.get(x, 0))
            return b'[' + b','.join(self.render(items[i]) if i in items else b'null' for i in range(n)) + b']'
        return b'null'


WORLD = None


def install_window_stubs(m, world):
    global WORLD
    WORLD = world
    m.stub(0x00ac3bf7, lambda mm: WORLD.mgr, 0)
    m.stub(0x00aae6f9, lambda mm: 1 if WORLD.flags.get(mm.uc.reg_read(cm.UC_X86_REG_ECX)) else 0, 0)

    def show(mm):
        w = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        WORLD.flags[w] = True
        WORLD.log.append(b'show ' + WORLD.name(w))
        return 0
    m.stub(0x00aae420, show, 0)

    def hide(mm):
        w = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        WORLD.flags[w] = False
        WORLD.log.append(b'hide ' + WORLD.name(w))
        return 0
    m.stub(0x00aae470, hide, 0)

    def invoke(mm):
        words = mm.args(16)
        w, method, fmt = words[0], mm.cstr(words[1]), mm.cstr(words[2])
        args, k = [], 3
        for token in fmt.split():
            v = words[k]
            k += 1
            if token == b'%s':
                args.append(json_bytes(mm.cstr(v)))
            elif token == b'%d':
                args.append(b'%d' % i32(v))
            elif token == b'%b':
                args.append(b'true' if v & 0xff else b'false')
            else:
                args.append(b'?' + token)
        WORLD.log.append(b'invoke ' + WORLD.name(w) + b' ' + method + b' [' + b','.join(args) + b']')
        return 0
    m.stub(0x00aae7e0, invoke, 0)

    def invoke_value(mm):
        w = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        method, value = mm.args(2)
        WORLD.log.append(b'value ' + WORLD.name(w) + b' ' + mm.cstr(method) + b' [' +
                         WORLD.render(WORLD.value_of(value)) + b']')
        return 0
    m.stub(0x00aaf3ef, invoke_value, 8)

    # GFx values: creation through the movie view, members, elements
    m.stub(0x00ab041b, lambda mm: WORLD.view, 0)
    m.stub(0x00acd7d8, lambda mm: WORLD.view, 0)

    def create(kind, cleanup):
        def handler(mm):
            out, = mm.args(1)
            ident = len(WORLD.values) + 1
            WORLD.values[ident] = ('obj', []) if kind == 'obj' else ('arr', {})
            mm.write(out, struct.pack('<IIII', FAKE_IFACE, 6 if kind == 'obj' else 7, ident, 0))
            return 0
        return handler, cleanup
    world.view_fns = {}
    for slot, (h, cleanup) in ((0x34, create('obj', 0x10)), (0x38, create('arr', 4))):
        fn = m._new_stub()
        m.stub(fn, h, cleanup)
        world.view_fns[slot] = fn
    world.tab_fns = {}
    for tab in (0, 1):
        for what in ('init', 'close'):
            fn = m._new_stub()
            m.stub(fn, (lambda w, t: (lambda mm: WORLD.log.append(b'tab %d %s (not played)' % (t, w.encode()))
                                       or 0))(what, tab), 0)
            world.tab_fns[(tab, what)] = fn

    def set_member(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        name, value = mm.args(2)
        node = WORLD.values[mm.u32(this + 8)]
        node[1].append((mm.cstr(name), WORLD.value_of(value)))
        return 0
    m.stub(0x00ab27c7, set_member, 8)

    def set_element(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        index, value = mm.args(2)
        WORLD.values[mm.u32(this + 8)][1][index] = WORLD.value_of(value)
        return 0
    m.stub(0x00ab27a6, set_element, 8)

    def set_size(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        size, = mm.args(1)
        node = WORLD.values[mm.u32(this + 8)]
        for k in [k for k in node[1] if k >= size]:
            del node[1][k]
        WORLD.sizes[mm.u32(this + 8)] = size
        return 0
    m.stub(0x00ab2788, set_size, 4)
    m.stub(0x00aad299, lambda mm: 0, 0)

    # packets
    def builder_init(mm):
        WORLD.packets[mm.uc.reg_read(cm.UC_X86_REG_ECX)] = bytearray()
        return 0
    m.stub(0x00d52133, builder_init, 0)

    def builder_add(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        p, n, _ = mm.args(3)
        WORLD.packets.setdefault(this, bytearray()).extend(mm.read(p, n))
        return 0
    m.stub(0x00d51c9b, builder_add, 0xc)

    def builder_send(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        a, b = mm.args(2)
        body = bytearray(WORLD.packets.get(this, b''))
        if len(body) >= 2:
            body[1] = len(body)
        WORLD.log.append(b'send ' + b' '.join(b'%02x' % x for x in body) + b' | %d %d' % (a, b))
        return 0
    m.stub(0x00d51d4f, builder_send, 8)

    def msgbox(mm):
        owner, p3, text, title, p6, p7, p8 = mm.args(7)
        WORLD.log.append(b'msgbox ' + WORLD.name(owner) + b' %d ' % p3 + json_bytes(mm.cstr(text)) + b' ' +
                         json_bytes(mm.cstr(title)) + b' %d %d %d' % (p6, p7, p8))
        return 0
    m.stub(0x00b3967c, msgbox, 0x1c)

    def notice(mm):
        s, = mm.args(1)
        WORLD.log.append(b'notice ' + json_bytes(std_string(mm, s)))
        return 0
    m.stub(0x0095f4ec, notice, 4)

    # the quest summary HUD
    def lock(mm):
        out, = mm.args(1)
        mm.write(out, struct.pack('<II', SUMMARY if WORLD.summary else 0, 0))
        return out
    m.stub(0x00be5cd7, lock, 4)
    m.stub(0x00afb9c1, lambda mm: 0, 0)
    m.stub(0x009617c6, lambda mm: 0, 0)

    def summary(kind, nargs):
        def handler(mm):
            if nargs:
                a, = mm.args(1)
                v = i32(mm.u32(a + 4)) if kind == b'add' else i32(a)
                WORLD.log.append(b'summary %s %d' % (kind, v))
            else:
                WORLD.log.append(b'summary ' + kind)
            return 0
        return handler
    m.stub(0x00c89ff9, summary(b'add', 1), 4)
    m.stub(0x00c8a072, summary(b'remove', 1), 4)
    m.stub(0x00c8a0ce, summary(b'clear', 0), 0)
    m.stub(0x00c8a0eb, summary(b'update', 0), 0)

    # the rest of the client around the windows
    def words(mm):
        i, = mm.args(1)
        text = DIALOGUE_WORDS.get(i)
        return mm.cstring(text) if text is not None else 0
    m.stub(DLG_QUESTWORDS, words, 4)
    def hero_name(mm):
        out = mm.alloc(0x18, define=True)
        write_std_string(mm, out, HERO_NAME)
        return out
    m.stub(0x00a00358, hero_name, 0)
    m.stub(0x00a99ebe, lambda mm: DUMMY, 0)

    def classic(mm):
        v, = mm.args(1)
        WORLD.log.append(b'classicquest %d' % i32(v))
        return 0
    m.stub(0x009f4c3f, classic, 4)
    m.stub(0x00f2bb92, lambda mm: DUMMY, 0)
    m.stub(0x00f2b6ce, lambda mm: DUMMY, 0)
    m.stub(0x00efd4f7, lambda mm: 1, 0)

    def wrap(mm):
        dst, _, cap, text = mm.args(4)
        try:
            mm.write(dst, mm.cstr(text)[:0x7f] + b'\0')
        except Exception as error:
            return mm.fail(f'wrap dst {dst:#x} text {text:#x}: {error}')
        return 1
    m.stub(0x011ff794, wrap, 0)

    def fit(mm):
        dst, cap, src, _ = mm.args(4)
        mm.write(dst, mm.cstr(src)[:cap - 1] + b'\0')
        return 0
    m.stub(0x011ff6fc, fit, 0)
    for a in (0x00d50954, 0x00d509b6, 0x00d50b0b):     # the 0x70 / 0x71 XOR key hash: key stays zero
        m.stub(a, lambda mm: 0, 0)


def client_state(m, records):
    qs = m.u32(QS_PTR)
    quests = {}
    for key, node in tree(m, qs + 4):
        q = m.u32(node + 0x14)
        quests[key] = [i32(m.u32(q + 0x2c)), i32(m.u32(q + 0x30)), m.read(q + 0x34, 1)[0], i32(m.u32(q + 0x28))]
    items = ''.join(f'{k}={i32(m.u32(n + 0x14))},' for k, n in tree(m, qs + 0x1c))
    values = ''.join(f'{k}={i32(m.u32(n + 0x14))},' for k, n in tree(m, qs + 0x24))
    cats = {k: [kk for kk, _ in tree(m, m.u32(n + 0x14) + 4)] for k, n in tree(m, qs + 0xc)}
    text = f'items:{items} values:{values}' + ''.join(f' active{k}:' + ''.join(f'{x},' for x in cats.get(k, []))
                                                     for k in (2, 3, 4))
    return quests, text


def native_state(nat, records):
    quests = {r[0]: nat.quest_fields(r[0]) for r in records}
    return quests, nat.lib.mu_quest_maps_text(nat.client).decode()



class Ops:
    """One action on both sides: the client routine in Unicorn and its libquest counterpart."""

    def __init__(self, m, nat, world, records):
        self.m, self.nat, self.w, self.records = m, nat, world, records
        L = nat.lib
        for name, args in (('mu_quest_progress_set', [ctypes.c_int32]), ('mu_quest_progress_show_page', []),
                           ('mu_quest_progress_refresh', []), ('mu_quest_progress_open', []),
                           ('mu_quest_progress_close', []), ('mu_quest_progress_onload', []),
                           ('mu_quest_progress_select', [ctypes.c_int32]), ('mu_quest_progress_confirm', []),
                           ('mu_quest_progress_button', [ctypes.c_int]),
                           ('mu_quest_dialog_quests', [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32]),
                           ('mu_quest_dialog_choice', [ctypes.c_int32, ctypes.POINTER(ctypes.c_int)]),
                           ('mu_quest_info_open', []), ('mu_quest_info_close', []), ('mu_quest_info_onload', []),
                           ('mu_quest_info_tab_buttons', []), ('mu_quest_info_checked', []),
                           ('mu_quest_info_select_tab', [ctypes.c_int32]), ('mu_quest_info_giveup_ok', [])):
            fn = getattr(L, name)
            fn.argtypes = [ctypes.c_void_p] + args
        for name, args in (('mu_quest_tab_init', []), ('mu_quest_tab_select', [ctypes.c_int32]),
                           ('mu_quest_tab_action', [ctypes.c_int32])):
            getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_void_p] + args
        L.mu_quest_tab_text_width.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_char_p]
        L.mu_quest_info_tab.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_quest_info_tab.restype = ctypes.c_void_p
        self.quest_ptrs = {}

    def quest_ptr(self, index):
        if not self.quest_ptrs:
            qs = self.m.u32(QS_PTR)
            self.quest_ptrs = {k: self.m.u32(n + 0x14) for k, n in tree(self.m, qs + 4)}
        return self.quest_ptrs.get(index, 0)

    def packet(self, payload):
        m, w = self.m, self.w
        m.call(HANDLERS[payload[3]], [self._bytes(payload)])
        self.nat.lib.mu_quest_receive(self.nat.client, bytes(payload), len(payload))

    def _bytes(self, payload):
        size = (len(payload) + 32) & ~15
        buf = self.m.alloc(size, define=True)
        self.m.write(buf, bytes(payload) + bytes(size - len(payload)))
        return buf

    def nqp(self, what, arg=0):
        m, w, L, c = self.m, self.w, self.nat.lib, self.nat.client
        if what == 'set':
            m.call(SET_CONTENTS, [arg], ecx=w.nqp)
            L.mu_quest_progress_set(c, arg)
        elif what == 'page':
            m.call(SHOW_PAGE, [], ecx=w.nqp)
            L.mu_quest_progress_show_page(c)
        elif what == 'refresh':
            m.call(REFRESH, [], ecx=w.nqp)
            L.mu_quest_progress_refresh(c)
        elif what == 'open':
            m.call(NQP_OPEN, [], ecx=w.nqp)
            L.mu_quest_progress_open(c)
        elif what == 'close':
            m.call(NQP_CLOSE, [], ecx=w.nqp)
            L.mu_quest_progress_close(c)
        elif what == 'onload':
            m.call(NQP_ONLOAD, [], ecx=w.nqp)
            L.mu_quest_progress_onload(c)
        elif what == 'select':
            m.call(NQP_SELECT, [arg], ecx=w.nqp)
            L.mu_quest_progress_select(c, arg)
        elif what == 'confirm':
            m.call(NQP_CONFIRM, [], ecx=w.nqp)
            L.mu_quest_progress_confirm(c)
        elif what == 'button':
            m.call(NQP_BUTTON, [arg], ecx=w.nqp)
            L.mu_quest_progress_button(c, arg)

    def dialog_quests(self, quests):
        m, w = self.m, self.w
        ptrs = [self.quest_ptr(q) for q in quests]
        vec = m.alloc(16, define=True)
        data = m.alloc(4 * max(1, len(ptrs)), define=True)
        m.write(data, b''.join(struct.pack('<I', p) for p in ptrs))
        m.write(vec, struct.pack('<III', data, data + 4 * len(ptrs), data + 4 * len(ptrs)))
        m.call(DLG_QUESTS, [vec], ecx=w.dlg)
        arr = (ctypes.c_int32 * max(1, len(quests)))(*quests)
        self.nat.lib.mu_quest_dialog_quests(self.nat.client, arr, len(quests))

    def dialog_choice(self, choice):
        m, w = self.m, self.w
        m.put32(w.dlg + 0x1cd8, choice)
        m.call(DLG_CHOICE, [], ecx=w.dlg)
        leave = ctypes.c_int()
        self.nat.lib.mu_quest_dialog_choice(self.nat.client, choice, ctypes.byref(leave))

    def mqi(self, what, arg=0):
        m, w, L, c = self.m, self.w, self.nat.lib, self.nat.client
        if what == 'open':
            m.call(MQI_OPEN, [], ecx=w.mqi)
            L.mu_quest_info_open(c)
        elif what == 'close':
            m.call(MQI_CLOSE, [], ecx=w.mqi)
            L.mu_quest_info_close(c)
        elif what == 'onload':
            m.call(MQI_ONLOAD, [], ecx=w.mqi)
            L.mu_quest_info_onload(c)
        elif what == 'tabs':
            m.call(MQI_TABS, [], ecx=w.mqi)
            L.mu_quest_info_tab_buttons(c)
        elif what == 'checked':
            m.call(MQI_CHECKED, [], ecx=w.mqi)
            L.mu_quest_info_checked(c)
        elif what == 'tab':
            m.put32(w.mqi + 0x78, arg)
            m.call(0x00be4403, [], ecx=w.mqi)
            L.mu_quest_info_select_tab(c, arg)
        elif what == 'quest':
            m.call(0x00be4641, [arg], ecx=w.mqi)
            t = L.mu_quest_info_tab(c, self.nat.field('info.tab'))
            if t:
                L.mu_quest_tab_select(c, t, arg)
        elif what == 'action':
            tab = w.tabs[self.nat.field('info.tab')]
            m.call(0x00d4ffea, [], ecx=tab)
            t = L.mu_quest_info_tab(c, self.nat.field('info.tab'))
            if t:
                L.mu_quest_tab_action(c, t, self.nat.field('info.selected%d' % self.nat.field('info.tab')))
        elif what == 'giveup':
            m.call(MQI_GIVEUP_BOX, [0x2d, 0], ecx=w.mqi)
            L.mu_quest_info_giveup_ok(c)
        elif what == 'width':
            # the tab's QuestTextWidth (0x00d4f43e(lines, std::string)): the wrapped text back to the movie
            tab = w.tabs[self.nat.field('info.tab')]
            s = m.alloc(0x20, define=True)
            text = b'wrapped <%d> text\nsecond line' % arg
            write_std_string(m, s, text)
            m.call(0x00d4f43e, [arg, s], ecx=tab)
            t = L.mu_quest_info_tab(c, self.nat.field('info.tab'))
            if t:
                L.mu_quest_tab_text_width(c, t, arg, text)


def install_more_stubs(m, world):
    m.stub(0x00aadbc3, lambda mm: 1, 0)            # the component's OnLoad base

    def state(mm):
        v, = mm.args(1)
        WORLD.log.append(b'dialogue state %d' % i32(v))
        return 0
    m.stub(0x00be86de, state, 4)

    def move(mm):
        q, = mm.args(1)
        WORLD.log.append(b'move %d (not played)' % i32(mm.u32(q + 4)))
        return 0
    m.stub(0x00d5029b, move, 0)


def random_packet(rng, keys, nat=None):
    sub = rng.choice([0x6f, 0x70, 0x71, 0x72, 0x72, 0x73, 0x74, 0x74, 0x75, 0x75, 0x75, 0x81, 0x82, 0x83])
    q = rng.choice(keys) if rng.random() < 0.92 else rng.randint(0, 2000)
    if sub == 0x70 or sub == 0x71:
        n = rng.randint(0, 6)
        body = bytearray(b'\xc1\x00\xf6' + bytes([sub]) + struct.pack('<H', n))
        for _ in range(n):
            qq = rng.choice(keys) if rng.random() < 0.9 else rng.randint(0, 2000)
            if sub == 0x70:
                body += struct.pack('<HHHHBB', 0, qq, 0, rng.randint(0, 60), rng.choice([0, 1, 1, 2, 3, 4]),
                                    rng.randint(0, 1))
            else:
                body += struct.pack('<HHBB', 0, qq, rng.choice([0, 1, 2, 3, 4]), 0)
        body += bytes(4)        # the XOR salt
        body[1] = len(body) & 0xff
        return bytes(body)
    if sub in (0x72, 0x73, 0x74):
        result = rng.choice([0, 0, 0, 1, 2, 3, 4, 5])
        return b'\xc1\x09\xf6' + bytes([sub]) + b'\0\0' + struct.pack('<HB', q, result)
    if sub == 0x75:
        return b'\xc1\x0b\xf6\x75\0\0' + struct.pack('<HHB', q, rng.randint(0, 80), rng.choice([0, 1, 1, 2, 3, 4]))
    if sub == 0x81:
        return b'\xc1\x06\xf6\x81' + struct.pack('<H', rng.randint(0, 120))
    if sub == 0x82:
        return b'\xc1\x0c\xf6\x82\0\0' + struct.pack('<HI', q, rng.getrandbits(32))
    if sub == 0x83:
        return b'\xc1\x09\xf6\x83\0\0' + struct.pack('<HB', q, 0)
    return b'\xc1\x08\xf6\x6f\0\0' + struct.pack('<H', q)


TRACE = bool(os.environ.get('MU_QUEST_TRACE'))


COVERAGE = {}


def compare_step(fam, label, m, nat, world, records, state_too=True):
    if TRACE:
        print('step', label, file=sys.stderr)
    client_log = [line.decode('latin1') for line in world.log]
    for line in client_log:
        parts = line.split(' ')
        key = ' '.join(parts[:3]) if parts[0] in ('invoke', 'value') else ' '.join(parts[:2]) if parts[0] in (
            'send', 'summary', 'show', 'hide', 'tab') else parts[0]
        if parts[0] == 'send':
            key = 'send ' + ' '.join(parts[3:5])
        COVERAGE[key] = COVERAGE.get(key, 0) + 1
    native_log = nat.log()
    fam.check((label, 'log'), client_log, native_log)
    if state_too:
        cq, ctext = client_state(m, records)
        nq, ntext = native_state(nat, records)
        diff = [(k, cq[k], nq.get(k)) for k in cq if cq[k] != nq.get(k)]
        fam.check((label, 'quests'), diff[:3], [])
        fam.check((label, 'maps'), ctext, ntext)
    world.log.clear()
    nat.clear_log()


def start_case(m, nat, world, rng, summary=None):
    summary = rng.random() < 0.4 if summary is None else summary
    world.reset(summary=summary)
    nat.reset()
    nat.field('summary', 1 if summary else 0)
    nat.field('font', FONT_B_VALUE)
    nat.field('font_default', FONT_A_VALUE)
    nat.clear_log()


def run_packets(m, nat, world, ops, records, rng, fam, sequences, length):
    keys = [r[0] for r in records]
    for seq in range(sequences):
        start_case(m, nat, world, rng)
        ops.quest_ptrs = {}
        if rng.random() < 0.5:
            tab = rng.choice([2, 3, 4, 2, 3, 4, 0, 1])
            m.put32(world.mqi + 0x78, tab)
            nat.field('info.tab', tab)
            m.write(world.mqi + 0x7c, b'\0')
            nat.field('info.first_open', 0)
            world.flags[world.mqi] = True
            nat.field('info.visible', 1)
        for step in range(length):
            payload = random_packet(rng, keys)
            try:
                ops.packet(payload)
            except cm.CaseError as error:
                raise cm.CaseError(f'{error} (sequence {seq} step {step} packet {payload.hex()} '
                                   f'mqi tab {nat.field("info.tab")} visible {nat.field("info.visible")})')
            compare_step(fam, (seq, step, payload.hex()), m, nat, world, records)
            if m.heap_next - cm.HEAP_BASE > 0x3000000:
                break


def run_windows(m, nat, world, ops, records, rng, fam, sequences, length):
    for seq in range(sequences):
        try:
            windows_sequence(m, nat, world, ops, records, rng, fam, seq, length)
        except cm.CaseError as error:
            raise cm.CaseError(f'{error} (sequence {seq}, last {fam.last})')


def native_active(nat, category):
    text = nat.lib.mu_quest_maps_text(nat.client).decode()
    mt = re.search(rf'active{category}:([0-9,]*)', text)
    return [int(x) for x in mt.group(1).split(',') if x] if mt else []


def windows_sequence(m, nat, world, ops, records, rng, fam, seq, length):
    keys = [r[0] for r in records]
    if True:
        start_case(m, nat, world, rng)
        ops.quest_ptrs = {}
        # a quest list first (0x70): some active quests in every state
        n = rng.randint(2, 9)
        body = bytearray(b'\xc1\x00\xf6\x70' + struct.pack('<H', n))
        for _ in range(n):
            body += struct.pack('<HHHHBB', 0, rng.choice(keys), 0, rng.randint(0, 40), rng.choice([0, 1, 2, 2, 3, 4]),
                                rng.randint(0, 1))
        body += bytes(4)
        body[1] = len(body) & 0xff
        ops.packet(bytes(body))
        compare_step(fam, (seq, 'list'), m, nat, world, records)
        for step in range(length):
            label = None
            r = rng.random()
            if r < 0.2:
                active = native_active(nat, rng.choice([2, 3, 4]))
                if active and rng.random() < 0.5:
                    q = rng.choice(active)
                    payload = (b'\xc1\x0b\xf6\x75\0\0' + struct.pack('<HHB', q, rng.randint(0, 80), rng.choice([1, 2, 2]))
                               if rng.random() < 0.7 else b'\xc1\x09\xf6\x74\0\0' + struct.pack('<HB', q, rng.choice([0, 0, 1, 2])))
                else:
                    payload = random_packet(rng, keys)
                fam.last = ('packet', payload.hex())
                ops.packet(payload)
                label = ('packet', payload.hex())
            elif r < 0.45:
                what = rng.choice(['set', 'set', 'page', 'refresh', 'open', 'close', 'onload', 'select', 'select',
                                   'confirm', 'button'])
                arg = 0
                if what == 'set':
                    arg = rng.choice(keys)
                    q = ops.quest_ptr(arg)
                    st, cnt = rng.choice([0, 0, 1, 2, 3, 4]), rng.randint(0, 50)
                    m.uc.mem_write(q + 0x2c, struct.pack('<ii', st, cnt))
                    nat.lib.mu_quest_set_fields(nat.client, arg, st, cnt, m.read(q + 0x34, 1)[0])
                elif what == 'select':
                    arg = rng.randint(0, 2)
                elif what == 'button':
                    arg = rng.randint(0, 1)
                if what in ('page', 'open', 'confirm', 'refresh') and nat.field('progress.quest_ptr') < 0:
                    continue
                if what == 'select' and nat.field('progress.quest_ptr') < 0 and nat.field('progress.mode') == 1:
                    continue
                fam.last = ('nqp', what, arg)
                ops.nqp(what, arg)
                label = ('nqp', what, arg)
            elif r < 0.55:
                if rng.random() < 0.6 or nat.field('dialog.list_mode') == 0:
                    quests = [rng.choice(keys) for _ in range(rng.randint(0, 6))]
                    world.flags[world.dlg] = True
                    nat.field('dialog.visible', 1)
                    fam.last = ('dlgquests', quests)
                    ops.dialog_quests(quests)
                    label = ('dlgquests', tuple(quests))
                else:
                    n = nat.field('dialog.options')
                    choice = rng.randint(1, max(1, n))
                    fam.last = ('dlgchoice', choice)
                    ops.dialog_choice(choice)
                    label = ('dlgchoice', choice)
            else:
                what = rng.choice(['open', 'close', 'onload', 'tabs', 'checked', 'tab', 'tab', 'quest', 'quest',
                                   'quest', 'action', 'action', 'giveup', 'width'])
                arg = 0
                tab = nat.field('info.tab')
                if what == 'tab':
                    arg = rng.choice([2, 3, 4, 2, 3, 4, 2, 3, 4, 0, 1])
                elif what == 'quest':
                    if tab < 2:
                        continue
                    active = native_active(nat, tab)
                    arg = rng.choice(active) if active and rng.random() < 0.9 else rng.choice(keys)
                elif what in ('action', 'giveup', 'width') and tab < 2:
                    continue
                if what == 'width':
                    arg = rng.randint(1, 9)
                fam.last = ('mqi', what, arg)
                ops.mqi(what, arg)
                label = ('mqi', what, arg)
            compare_step(fam, (seq, step, label), m, nat, world, records)
            if m.heap_next - cm.HEAP_BASE > 0x3000000:
                break


# ---- main ----------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', required=True, help='langread snapshot with the quest maps (local)')
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--families', default='category,runtime,build,lookup,text,html,packets,windows')
    parser.add_argument('--sequences', type=int, default=60)
    parser.add_argument('--length', type=int, default=25)
    parser.add_argument('--text-rounds', type=int, default=3)
    parser.add_argument('--html-cases', type=int, default=300)
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes in the C are caught')
    parser.add_argument('--output')
    args = parser.parse_args()
    for path, digest in ((args.text, vl.TEXT_SHA256), (args.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    snap = plain.Snapshot.load(args.snapshot)
    rng = random.Random(args.seed)
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256, 'seed': args.seed, 'families': {}}
    m = QuestMachine(text, data, snap)
    install_stubs(m)
    records = plain.read_quests(snap)
    strings = plain.read_queststrings(snap)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        plain_dir = Path(tmp)/'plain'
        plain.convert(snap, plain_dir)
        nat = Native(snap, plain_dir)
        world = World(m, snap)
        install_window_stubs(m, world)
        install_more_stubs(m, world)
        ops = Ops(m, nat, world, records)
        runs = {
            'packets': lambda f: run_packets(m, nat, world, ops, records, rng, f, args.sequences, args.length),
            'windows': lambda f: run_windows(m, nat, world, ops, records, rng, f, args.sequences, args.length),
            'category': lambda f: run_category(m, nat, rng, f),
            'runtime': lambda f: run_runtime(m, nat, snap, records, strings, f),
            'build': lambda f: run_build(m, nat, records, strings, f),
            'lookup': lambda f: run_lookup(m, nat, records, rng, f),
            'text': lambda f: run_text(m, nat, records, rng, f, args.text_rounds),
            'html': lambda f: run_html(m, nat, rng, f, args.html_cases),
        }
        for name in args.families.split(','):
            fam = Family(name)
            try:
                runs[name](fam)
            except cm.CaseError as error:
                fam.examples.append({'error': str(error)})
                fam.mismatches += 1
            report['families'][name] = fam.summary()
            print(f'{name}: {fam.cases} cases, {fam.mismatches} mismatches ({time.time() - t0:.1f} s)', flush=True)
        report['coverage'] = dict(sorted(COVERAGE.items()))
        if args.mutations:
            report['mutations'] = {}
            quick = {1: 'category', 2: 'text', 3: 'windows', 4: 'packets', 5: 'windows', 6: 'windows'}
            for k, family in quick.items():
                lib = build_variant(k, tmp)
                mnat = Native(snap, plain_dir, lib)
                mops = Ops(m, mnat, world, records)
                fam = Family(f'm{k}')
                mrng = random.Random(args.seed + k)
                try:
                    {'category': lambda: run_category(m, mnat, mrng, fam),
                     'text': lambda: run_text(m, mnat, records, mrng, fam, 1),
                     'windows': lambda: run_windows(m, mnat, world, mops, records, mrng, fam, 25, 30),
                     'packets': lambda: run_packets(m, mnat, world, mops, records, mrng, fam, 25, 30)}[family]()
                except cm.CaseError as error:
                    fam.mismatches += 1
                report['mutations'][f'{k}:{family}'] = fam.mismatches > 0
                print(f'mutation {k} ({family}): {"caught" if fam.mismatches else "MISSED"} '
                      f'({fam.mismatches} of {fam.cases})', flush=True)
    report['seconds'] = round(time.time() - t0, 1)
    text_out = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(text_out + '\n')
    bad = {k: v for k, v in report['families'].items() if v['mismatches']}
    if bad:
        print(json.dumps(bad, indent=2)[:6000])
        return 1
    if args.mutations and not all(report['mutations'].values()):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
