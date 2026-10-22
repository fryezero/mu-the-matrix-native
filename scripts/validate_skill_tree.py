#!/usr/bin/env python3
"""Run the client's master skill tree routines in Unicorn and compare them with reconstructed/skill/master_tree.c
(NATIVE-SKILL-002).

Same machine as scripts/validate_skill.py (the pinned restored text and second section, the langread snapshot of
the Lang.mpr tables).  The MasterSkillTree handler (0xd8 bytes; maps +0xb8 learned, +0xc0 nodes, +0xc8 tooltips,
+0xd0 positions) is built in the machine's memory for each case.

Families:

* class: the class switch 0x00baf92c for every code 0..0xff (mask, tree-name and title GlobalText ids);
* build: 0x00bb0250 / 0x00bb02fe (the class's MasterSkillTreeData / MasterSkillTooltip records copied to 0x01d22d70
  / 0x01d2ed70; synthetic, or the installed tables with MU_GAME_ROOT) and 0x00bb04ac (SetArrowDirection,
  SetSkillSlot) — the maps read back and the invokes recorded;
* access: the accessors 0x00bb1d9d, 0x00bb1ca1, 0x00bb1df9, 0x00bb1e55, 0x00bb1ea1, 0x00bb1ed0 and 0x00bb1cfd over
  random learned maps and the snapshot's brand chains;
* click: OnClickBtnSkillSlot 0x00bb22e1 (0x00bb194c, 0x00bb1a19, 0x00bb1b06 with its side effect, 0x00bb1b76, the
  special-item answer) end to end with the message and confirm boxes recorded, then the box answer 0x00baf47b with
  the request packet's fields recorded;
* answer: the A0 10 list 0x012863c5 (0x00bb0644, SetRank, SetText 0x00bb0803 running for real) and the A0 14 learn
  answer 0x01285995 (0x00bb25f3 over the hero's list, 0x00bb26a8, results 6 and 7);
* text: SetText 0x00bb0803 for random masks and hero values;
* position: RequestPositionInfo 0x00bb03bc;
* damage: the skill damage 0x00a01692 with the master manager's real accessors over random learned maps.

Modelled (not client code): import calls stop a case; the heap; the client's sprintf (validate_skill's statement);
the ostringstream (validate_skill's StreamModel); ToUTF8 is the identity; Invoke 0x00aae7e0, the message and confirm
boxes 0x00b3967c / 0x00b39648, the sound 0x00a6ac96, the special-item answer 0x0109260c, the stamp / hotkey adds
(verified by validate_skill_server.py), the packet builder (verified by validate_protocol.py), the hero's getters and
FormulaData's 0x0117b5eb are recording stubs answering with case values.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402
import validate_skill as vs  # noqa: E402
import validate_skill_server as vss  # noqa: E402
from validate_skill import I32, U8, U16, s32  # noqa: E402

DUMMY = vl.DUMMY
GFX = DUMMY + 0x800
BOX = DUMMY + 0xc00
TREE4 = DUMMY + 0xd00
CHARINFO = DUMMY + 0xe00
NODES_AT, TIPS_AT = 0x01d22d70, 0x01d2ed70
CLASS_SWITCH, BUILD_NODES, BUILD_TIPS, BUILD_SLOTS = 0x00baf92c, 0x00bb0250, 0x00bb02fe, 0x00bb04ac
ACC_LEVEL, ACC_VALUE, ACC_FLAG, ACC_HAS, ACC_IS, ACC_CHAIN, ACC_KIND = (0x00bb1d9d, 0x00bb1ca1, 0x00bb1df9,
                                                                        0x00bb1e55, 0x00bb1ea1, 0x00bb1ed0, 0x00bb1cfd)
CLICK, CONFIRM, LIST_RECV, LEARN_RECV, SET_TEXT, POSITION = (0x00bb22e1, 0x00baf47b, 0x012863c5, 0x01285995,
                                                             0x00bb0803, 0x00bb03bc)
DAMAGE = 0x00a01692
INVOKE, TO_UTF8 = 0x00aae7e0, 0x00a99d93


def _write_std_string(m, obj, value):
    """validate_skill.write_hero's std::string writer with whole 16-byte blocks defined (strlen reads aligned dwords
    past the NUL)."""
    if len(value) < 16:
        m.write(obj, value + b'\0'*(16 - len(value)))
        m.write(obj + 0x10, struct.pack('<II', len(value), 15))
    else:
        size = (len(value) + 16) & ~15
        buf = m.alloc(size, define=True)
        m.write(buf, value + b'\0'*(size - len(value)))
        m.write(obj, struct.pack('<I', buf) + bytes(12))
        m.write(obj + 0x10, struct.pack('<II', len(value), len(value)))


vs.write_std_string = _write_std_string


# ---- ctypes ------------------------------------------------------------------------------------------------

class EntryC(ctypes.Structure):
    _fields_ = [('level', U8), ('value', ctypes.c_float), ('next', ctypes.c_float), ('flag', U8)]


class NodeC(ctypes.Structure):
    _fields_ = [('slot', U8), ('x1', U8), ('mask', U16), ('group', U8), ('cost', U8), ('max_level', U8), ('arrow', U8),
                ('prereq1', I32), ('prereq2', I32), ('skill', I32), ('formula', I32)]


class TipC(ctypes.Structure):
    _fields_ = [('skill', I32), ('mask', ctypes.c_int16), ('rank_line', ctypes.c_char*64), ('desc', ctypes.c_char*256),
                ('cost_line', ctypes.c_char*32), ('brand_line', ctypes.c_char*64), ('rank_req', ctypes.c_char*128),
                ('pre1', ctypes.c_char*128), ('pre2', ctypes.c_char*128)]


class LearnedC(ctypes.Structure):
    _fields_ = [('skill', I32), ('e', EntryC)]


class PosC(ctypes.Structure):
    _fields_ = [('has', U8), ('x', ctypes.c_float), ('y', ctypes.c_float)]


class TreeC(ctypes.Structure):
    _fields_ = [('state', U8*0x24), ('pending_cost', U8), ('pad9d', U8*3), ('pending_skill', I32), ('mask', I32), ('gt_names', I32),
                ('gt_title', I32), ('icon_w', ctypes.c_float), ('icon_h', ctypes.c_float),
                ('learned', LearnedC*1024), ('nlearned', ctypes.c_int), ('nodes', NodeC*256), ('nnodes', ctypes.c_int),
                ('tips', ctypes.c_void_p*1024), ('ntips', ctypes.c_int), ('pos', PosC*256)]


TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, I32)
INVOKE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p)
BOX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)
SPECIAL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, I32)
EVENT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, I32)
FORMULA_FN = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_void_p, I32, I32, I32)


class MEnvC(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('skills', ctypes.POINTER(vs.EnvC)), ('text', TEXT_FN), ('invoke', INVOKE_FN),
                ('msgbox', BOX_FN), ('confirm', BOX_FN), ('special_item', SPECIAL_FN), ('event', EVENT_FN),
                ('points', I32), ('level_sum', I32), ('exp', ctypes.c_uint64), ('next_exp', ctypes.c_uint64)]


class TreeNative(vss.ServerNative):
    def __init__(self, work, lib=None):
        super().__init__(work, lib)
        L = self.lib
        L.mu_master_init.argtypes = [ctypes.POINTER(TreeC)]
        L.mu_master_class.argtypes = [ctypes.POINTER(TreeC), ctypes.c_int]
        L.mu_master_build.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(MEnvC), ctypes.POINTER(NodeC), ctypes.c_int,
                                      ctypes.POINTER(TipC), ctypes.c_int]
        for name in ('mu_master_level', 'mu_master_flag'):
            getattr(L, name).argtypes = [ctypes.POINTER(TreeC), I32]
            getattr(L, name).restype = U8
        L.mu_master_value.argtypes = [ctypes.POINTER(TreeC), I32]
        L.mu_master_value.restype = ctypes.c_float
        L.mu_master_find.argtypes = [ctypes.POINTER(TreeC), I32]
        L.mu_master_find.restype = ctypes.c_void_p
        L.mu_master_is_master.argtypes = [I32]
        L.mu_master_chain.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(vs.EnvC), I32, I32]
        L.mu_master_chain.restype = ctypes.c_float
        L.mu_master_kind_sum.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(vs.EnvC), I32, ctypes.c_int]
        L.mu_master_kind_sum.restype = ctypes.c_float
        L.mu_master_click.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(MEnvC), ctypes.POINTER(vs.HeroC), ctypes.c_int]
        L.mu_master_confirm.argtypes = [ctypes.POINTER(TreeC), ctypes.c_int, ctypes.c_int, ctypes.POINTER(I32)]
        L.mu_master_receive_list.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(MEnvC), ctypes.c_char_p, ctypes.c_size_t]
        L.mu_master_receive_learn.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(MEnvC), ctypes.POINTER(vss.WorldC),
                                              ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int, ctypes.POINTER(I32)]
        L.mu_master_set_text.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(MEnvC), ctypes.c_int]
        L.mu_master_position.argtypes = [ctypes.POINTER(TreeC), ctypes.c_int, ctypes.c_float, ctypes.c_float,
                                         ctypes.c_float, ctypes.c_float, ctypes.c_float]
        L.mu_master_skill_damage.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(vs.EnvC), I32, FORMULA_FN,
                                             ctypes.c_void_p]
        L.mu_master_skill_damage.restype = I32


# ---- the case state -----------------------------------------------------------------------------------------

def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def node_bytes(n):
    return struct.pack('<BBHBBBBiiii', n['slot'], n['x1'], n['mask'], n['group'], n['cost'], n['max'], n['arrow'],
                       n['p1'], n['p2'], n['skill'], n['formula'])


def node_c(n):
    return NodeC(n['slot'], n['x1'], n['mask'], n['group'], n['cost'], n['max'], n['arrow'], n['p1'], n['p2'],
                 n['skill'], n['formula'])


def tip_bytes(t):
    rec = bytearray(808)
    struct.pack_into('<ih', rec, 0, t['skill'], t['mask'])
    for off, size, key in ((6, 64, 'rank'), (0x46, 256, 'desc'), (0x146, 32, 'cost'), (0x166, 64, 'brand'),
                           (0x1a6, 128, 'rankreq'), (0x226, 128, 'pre1'), (0x2a6, 128, 'pre2')):
        v = t[key][:size - 1]
        rec[off:off + len(v)] = v
    return bytes(rec)


def tip_c(t):
    return TipC(t['skill'], t['mask'], t['rank'][:63], t['desc'][:255], t['cost'][:31], t['brand'][:63],
                t['rankreq'][:127], t['pre1'][:127], t['pre2'][:127])


def random_nodes(rng, keys, n):
    out = []
    masks = [1 << i for i in range(16)]
    for _ in range(n):
        out.append({'slot': rng.choice([rng.randint(1, 108), rng.randint(1, 255)]), 'x1': 0,
                    'mask': rng.choice([rng.choice(masks), rng.choice(masks) | rng.choice(masks), 0xffff, 0]),
                    'group': rng.choice([0, 1, 2, 2, 3]), 'cost': rng.choice([1, 1, 10, rng.randint(0, 255)]),
                    'max': rng.choice([20, 10, rng.randint(0, 255)]), 'arrow': rng.choice([0, 1, 2, 3, 4, 9]),
                    'p1': rng.choice([0, 0, rng.choice(keys)]), 'p2': rng.choice([0, 0, 0, rng.choice(keys)]),
                    'skill': rng.choice(keys), 'formula': rng.choice([0, rng.randint(1, 600)])})
    return out


def random_tips(rng, keys, n):
    words = b'Rank %d, Skill Level: %d/%d'
    out = []
    for _ in range(n):
        mask = rng.choice([-1, 1 << rng.randint(0, 15), 0])
        out.append({'skill': rng.choice(keys), 'mask': mask - 0x10000 if mask >= 0x8000 else mask,
                    'rank': words, 'desc': b'Increase by %d#more', 'cost': b'Required Points: %d', 'brand': b'b',
                    'rankreq': b'r', 'pre1': b'p1', 'pre2': b'p2'})
    return out


def installed_tables(game_root):
    """The installed MasterSkillTreeData / MasterSkillTooltip records (decoded locally by mu-data)."""
    if not game_root:
        return None
    tool = ROOT/'native/build/mu-data'
    if not tool.exists():
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/mu-data'], check=True)
    out = []
    for name, size in (('masterskilltreedata.bmd', 24), ('masterskilltooltip.bmd', 808)):
        path = next((p for p in (Path(game_root)/'Data/Local').glob('*') if p.name.lower() == name), None)
        if path is None:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp)/'t.bin'
            r = subprocess.run([str(tool), 'dump', str(path), '--out', str(dump)], capture_output=True)
            if r.returncode or not dump.exists():
                return None
            raw = dump.read_bytes()
        out.append([raw[i:i + size] for i in range(0, len(raw) - size + 1, size)])
    return out


# ---- client handler ---------------------------------------------------------------------------------------

def map_build(m, items, node_size, key_fmt='<i'):
    """An MSVC std::map with the value bytes at node +0x14 (key at +0x10)."""
    head = vs.empty_map(m, node_size)
    items = sorted(items, key=lambda kv: kv[0] & 0xffffffff)

    def build(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        node = m.alloc(node_size, define=True)
        left = build(lo, mid, node)
        right = build(mid + 1, hi, node)
        key, value = items[mid]
        m.write(node, struct.pack('<III', left, parent, right) + b'\x01\x00\0\0' + struct.pack('<I', key & 0xffffffff) +
                value + bytes(node_size - 0x14 - len(value)))
        return node
    root = build(0, len(items), head)
    if items:
        lm = root
        while m.u32(lm) != head:
            lm = m.u32(lm)
        rm = root
        while m.u32(rm + 8) != head:
            rm = m.u32(rm + 8)
        m.write(head, struct.pack('<III', lm, root, rm))
    return head, len(items)


def map_read(m, container, key_bytes=4):
    head, size = struct.unpack('<II', m.read(container, 8))
    out, stack = [], []
    root = m.u32(head + 4)
    if root != head:
        stack.append(root)
    while stack and len(out) <= size:
        node = stack.pop()
        left, _, right = struct.unpack('<III', m.read(node, 12))
        key = m.u32(node + 0x10) & ((1 << (8*key_bytes)) - 1)
        out.append((key, node))
        if left != head:
            stack.append(left)
        if right != head:
            stack.append(right)
    out.sort()
    return out


def entry_bytes(e):
    return struct.pack('<B3xffB3x', e[0], e[1], e[2], e[3])


class Tree:
    """A case's handler state, written into both machines."""

    def __init__(self, rng, keys, nodes=(), learned=None):
        self.state = bytes(rng.choice([0, 0, rng.randint(0, 25)]) for _ in range(0x24))
        self.pending = (rng.randint(0, 255), rng.choice(keys))
        self.mask = rng.choice([1 << rng.randint(0, 15), 0xffff])
        self.names, self.title = rng.randint(0, 0x1a99), rng.randint(0, 0x1a99)
        self.nodes = list(nodes)
        self.learned = learned if learned is not None else {}
        self.pos = {}

    def client(self, m):
        h = m.alloc(0xd8, define=True)
        m.write(h + 0x78, self.state)
        m.write(h + 0x9c, bytes([self.pending[0], 0, 0, 0]))
        m.put32(h + 0xa0, self.pending[1])
        m.write(h + 0xa4, struct.pack('<iii', self.mask, self.names, self.title))
        m.write(h + 0xb0, bytes(8))
        hd, n = map_build(m, [(k, entry_bytes(e)) for k, e in self.learned.items()], 0x24)
        m.write(h + 0xb8, struct.pack('<II', hd, n))
        hd, n = map_build(m, [(nd['slot'], node_bytes(nd)) for nd in self.nodes], 0x2c)
        m.write(h + 0xc0, struct.pack('<II', hd, n))
        hd, n = map_build(m, [], 0x33c)
        m.write(h + 0xc8, struct.pack('<II', hd, n))
        hd, n = map_build(m, [(k, struct.pack('<ff', *v)) for k, v in self.pos.items()], 0x1c)
        m.write(h + 0xd0, struct.pack('<II', hd, n))
        return h

    def native(self, nat):
        t = TreeC()
        nat.lib.mu_master_init(ctypes.byref(t))
        for i, b in enumerate(self.state):
            t.state[i] = b
        t.pending_cost, t.pending_skill = self.pending
        t.pad9d[0] = t.pad9d[1] = t.pad9d[2] = 0
        t.mask, t.gt_names, t.gt_title = self.mask, self.names, self.title
        for i, (k, e) in enumerate(sorted(self.learned.items(), key=lambda kv: kv[0] & 0xffffffff)):
            t.learned[i].skill = k
            t.learned[i].e = EntryC(*e)
        t.nlearned = len(self.learned)
        for i, nd in enumerate(sorted(self.nodes, key=lambda x: x['slot'])):
            t.nodes[i] = node_c(nd)
        t.nnodes = len(self.nodes)
        for k, v in self.pos.items():
            t.pos[k] = PosC(1, *v)
        return t


def read_client_tree(m, h):
    out = {'state': list(m.read(h + 0x78, 0x24)), 'pending': (m.read(h + 0x9c, 1)[0], s32(m.u32(h + 0xa0))),
           'pad': list(m.read(h + 0x9d, 3)),
           'class': tuple(s32(v) for v in struct.unpack('<iii', m.read(h + 0xa4, 12)))}
    learned = []
    for k, node in map_read(m, h + 0xb8):
        lv, val, nxt, fl = struct.unpack('<B3xffB', m.read(node + 0x14, 13))
        learned.append((s32(k), lv, val, nxt, fl))
    out['learned'] = learned
    out['nodes'] = [m.read(node + 0x14, 24) for _, node in map_read(m, h + 0xc0, 1)]
    out['tips'] = [s32(k) for k, _ in map_read(m, h + 0xc8)]
    out['pos'] = [(k,) + struct.unpack('<ff', m.read(node + 0x14, 8)) for k, node in map_read(m, h + 0xd0, 1)]
    out['icon'] = struct.unpack('<ff', m.read(h + 0xb0, 8))
    return out


def read_native_tree(t):
    out = {'state': list(t.state), 'pending': (t.pending_cost, t.pending_skill), 'pad': list(t.pad9d),
           'class': (t.mask, t.gt_names, t.gt_title)}
    out['learned'] = [(t.learned[i].skill, t.learned[i].e.level, t.learned[i].e.value, t.learned[i].e.next,
                       t.learned[i].e.flag) for i in range(t.nlearned)]
    out['nodes'] = [bytes(t.nodes[i]) for i in range(t.nnodes)]
    out['nodes'] = [struct.pack('<BBHBBBBiiii', n.slot, n.x1, n.mask, n.group, n.cost, n.max_level, n.arrow, n.prereq1,
                                n.prereq2, n.skill, n.formula) for n in (t.nodes[i] for i in range(t.nnodes))]
    out['tips'] = [ctypes.cast(t.tips[i], ctypes.POINTER(TipC))[0].skill for i in range(t.ntips)]
    out['pos'] = [(i, t.pos[i].x, t.pos[i].y) for i in range(256) if t.pos[i].has]
    out['icon'] = (t.icon_w, t.icon_h)
    return out


# ---- recorders -------------------------------------------------------------------------------------------

class Recorder:
    """Client stubs at the routines' boundaries; native callbacks producing the same record."""

    def __init__(self, m, h, case):
        self.log = []
        self.case = case
        arg = lambda mm, i: mm.args(i + 1)[i]
        vs.common_stubs(m)

        def new(mm):    # the CRT's memcpy reads whole 16-byte chunks past a copy's end: define a slack
            size = mm.args(1)[0] or 1
            return mm.alloc((size + 47) & ~15, define=True)
        m.stub(vl.CRT_NEW, new)
        m.stub(vl.CRT_MALLOC, new)
        self.stream = vs.StreamModel(m)
        m.stub(0x0094f781, lambda mm: 0, 8)
        vbt = m.alloc(8, define=True)
        m.write(vbt, struct.pack('<ii', 0, 0x40))
        ctor = m.stubs[vs.STREAM_CTOR][1][0]

        def stream_ctor(mm):                            # the ostringstream's vbtable pointer (ios at +0x40)
            obj = mm.uc.reg_read(cm.UC_X86_REG_ECX)
            r = ctor(mm)
            mm.put32(obj, vbt)
            return r
        m.stub(vs.STREAM_CTOR, stream_ctor, 4)
        m.stub(vs.TIP_SPRINTF, lambda mm: vs.sprintf_model(mm, *(lambda w: (w[0], mm.cstr(w[1]), w[2:]))(mm.args(16))), 0)
        m.stub(vs.GFX_MGR, lambda mm: GFX, 0)
        for off, v in ((0x1f4, h), (0x1f8, TREE4), (0x21c, CHARINFO), (0x88, BOX)):
            m.put32(GFX + off, v)
        m.stub(0x0095f5d7, lambda mm: BOX, 0)
        m.put32(vs.ATTR, DUMMY + 0x600)              # the hero's getters are stubs (write_hero may replace it)
        m.put32(vs.ATTR8, DUMMY + 0x5f8)
        m.stub(0x0095f998, lambda mm: h, 0)
        m.stub(0x0095fbdc, lambda mm: 0, 0)
        m.stub(0x0094b030, self.put_int, 4)

        def invoke(mm):
            w = mm.args(16)
            fmt = mm.cstr(w[2])
            buf = m.alloc(4096, define=True)
            vs.sprintf_model(mm, buf, fmt, w[3:])
            self.log.append(('invoke', mm.cstr(w[1]).decode(), mm.cstr(buf)))
            return 0
        m.stub(INVOKE, invoke, 0)

        def utf8(mm):
            out, src = mm.args(2)
            vs.write_std_string(mm, out, mm.std_string(src))
            return out
        m.stub(TO_UTF8, utf8, 0)
        m.stub(0x00b3967c, lambda mm: self.log.append(('msgbox', 1 if arg(mm, 0) == h else int(arg(mm, 0) != 0),
                                                       mm.cstr(arg(mm, 2)))) or 0, 0x1c)
        m.stub(0x00b39648, lambda mm: self.log.append(('confirm', s32(arg(mm, 1)), mm.cstr(arg(mm, 2)))) or 0, 0x20)
        m.stub(0x00a6ac96, lambda mm: self.log.append(('sound', s32(arg(mm, 0)))) or 0, 0)
        m.stub(0x0107e918, lambda mm: DUMMY, 0)
        m.stub(0x0109260c, lambda mm: int(case.special.get(s32(arg(mm, 0)), 1)), 4)
        m.stub(0x00a001a6, lambda mm: case.points & 0xffffffff, 0)
        m.stub(0x00a00367, lambda mm: case.level_sum & 0xffffffff, 0)

        def u64(value):
            def handler(mm):
                mm.uc.reg_write(cm.UC_X86_REG_EDX, (value() >> 32) & 0xffffffff)
                return value() & 0xffffffff
            return handler
        from unicorn.x86_const import UC_X86_REG_XMM0

        def ultod(mm):                                  # __ultod3: ecx:edx (u64) -> xmm0 (CRT, modelled)
            v = mm.uc.reg_read(cm.UC_X86_REG_ECX) | mm.uc.reg_read(cm.UC_X86_REG_EDX) << 32
            mm.uc.reg_write(UC_X86_REG_XMM0, struct.unpack('<Q', struct.pack('<d', float(v)))[0])
            return mm.uc.reg_read(cm.UC_X86_REG_EAX)
        m.stub(0x0191c350, ultod, 0)
        m.stub(0x00a00131, u64(lambda: case.exp), 0)
        m.stub(0x00a0015d, u64(lambda: case.next_exp), 0)
        m.stub(0x00a00fb7, lambda mm: self.log.append(('event', 'stats', 0)) or 0, 0)
        m.stub(0x00a00192, lambda mm: self.log.append(('points', s32(arg(mm, 0)))) or 0, 4)
        m.stub(0x00c26ad8, lambda mm: self.log.append(('event', 'tree_add', s32(arg(mm, 0)))) or 0, 4)
        m.stub(0x00b40661, lambda mm: self.log.append(('event', 'charinfo', 0)) or 0, 0)
        m.stub(0x0095f861, lambda mm: DUMMY, 0)
        m.stub(0x01095f5c, lambda mm: self.log.append(('stamp_add', s32(arg(mm, 0)))) or 0, 4)
        m.stub(0x00a07c8a, lambda mm: self.log.append(('keys_add', s32(arg(mm, 0)))) or 0, 4)
        m.stub(0x009e819e, lambda mm: DUMMY + 0x80, 0)
        m.stub(0x00aae6f9, lambda mm: int(case.popup), 0)
        m.stub(0x00bb1183, lambda mm: self.log.append(('event', 'tooltip', s32(arg(mm, 0)))) or 0, 4)

        def gt_str(mm):                                   # GlobalText as a std::string (thiscall, the table)
            obj = mm.alloc(0x18, define=True)
            vs.write_std_string(mm, obj, case.texts(s32(arg(mm, 0))))
            return obj
        m.stub(0x011753c3, gt_str, 4)

    def put_int(self, mm):
        stream = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        v = s32(mm.args(1)[0])
        self.stream.streams[stream] += str(v).encode()
        return stream

    # native side
    def callbacks(self, case, nat_log):
        def text(u, i):
            return case.text_ptr(i)

        def invoke(u, name, args):
            nat_log.append(('invoke', name.decode(), args))

        def box(kind):
            return lambda u, owner, text: nat_log.append((kind, owner, text)) if kind == 'msgbox' \
                else nat_log.append((kind, owner, text))

        def event(u, what, a):
            what = what.decode()
            if what == 'sound':
                nat_log.append(('sound', a))
            else:
                nat_log.append(('event', what, a))
        self._keep = [TEXT_FN(text), INVOKE_FN(invoke), BOX_FN(box('msgbox')), BOX_FN(box('confirm')),
                      SPECIAL_FN(lambda u, s: int(case.special.get(s, 1))), EVENT_FN(event)]
        return self._keep


class Case:
    def __init__(self, rng, snap_texts):
        self.points = rng.choice([0, 1, 5, 10, rng.randint(0, 400), rng.randint(-5, 0)])
        self.level_sum = rng.randint(1, 1200)
        self.exp = rng.choice([0, rng.randint(0, 2**40), rng.randint(0, 2**63)])
        self.next_exp = rng.choice([0, rng.randint(0, 2**40), self.exp])
        self.special = {}
        self.popup = rng.random() < 0.5
        self.texts = snap_texts
        self._bufs = {}

    def text_ptr(self, i):
        if i not in self._bufs:
            self._bufs[i] = ctypes.create_string_buffer(self.texts(i))
        return ctypes.addressof(self._bufs[i])

    def text_addr(self, i):
        raise NotImplementedError


def menv(case, rec, nat_log, table):
    cb = rec.callbacks(case, nat_log)
    rec._env = vss.master_env(table)
    env = MEnvC(None, ctypes.pointer(rec._env), *cb)
    env.points, env.level_sum, env.exp, env.next_exp = case.points, case.level_sum, case.exp, case.next_exp
    return env


def snapshot_text(snap):
    """GlobalText bytes from the snapshot (the map 0x0095f027 reads; missing keys read as the empty text here —
    the cases only use present ones)."""
    table = dict(plain.read_text(snap))

    def text(i):
        v = table.get(i, b'')
        return v if isinstance(v, bytes) else v.encode('latin1')
    return text


# ---- families ---------------------------------------------------------------------------------------------

def run_class(m, nat, rng, fam, keys):
    for code in range(256):
        tree = Tree(rng, keys)
        m.prepare()
        vs.common_stubs(m)
        h = tree.client(m)
        m.call(CLASS_SWITCH, [code], ecx=h)
        client = tuple(s32(v) for v in struct.unpack('<iii', m.read(h + 0xa4, 12)))
        t = tree.native(nat)
        nat.lib.mu_master_class(ctypes.byref(t), code)
        fam.check(code, client, (t.mask, t.gt_names, t.gt_title))


def run_build(m, nat, rng, fam, keys, texts, cases, installed):
    for n in range(cases):
        if installed and n % 2 == 0:
            nodes_raw, tips_raw = installed
            nodes = [dict(zip(('slot', 'x1', 'mask', 'group', 'cost', 'max', 'arrow', 'p1', 'p2', 'skill', 'formula'),
                              struct.unpack('<BBHBBBBiiii', r))) for r in nodes_raw[:0x800]]
            tips = []
            for r in tips_raw[:0x800]:
                t = {'skill': struct.unpack_from('<i', r)[0], 'mask': struct.unpack_from('<h', r, 4)[0]}
                for off, size, key in ((6, 64, 'rank'), (0x46, 256, 'desc'), (0x146, 32, 'cost'), (0x166, 64, 'brand'),
                                       (0x1a6, 128, 'rankreq'), (0x226, 128, 'pre1'), (0x2a6, 128, 'pre2')):
                    t[key] = r[off:off + size].split(b'\0')[0]
                tips.append(t)
        else:
            nodes = random_nodes(rng, keys, rng.randint(0, 120))
            tips = random_tips(rng, keys, rng.randint(0, 120))
            if rng.random() < 0.3 and nodes:
                nodes.insert(rng.randint(0, len(nodes)), dict(nodes[0]))     # a repeated slot stops the build
            if rng.random() < 0.3:
                nodes.insert(rng.randint(0, len(nodes)), dict(random_nodes(rng, keys, 1)[0], slot=0))
        case = Case(rng, texts)
        tree = Tree(rng, keys)
        m.prepare(force=True)
        h = tree.client(m)
        rec = Recorder(m, h, case)
        block = b''.join(node_bytes(x) for x in nodes[:0x800]) + bytes(24)
        m.write(NODES_AT, block[:24*0x800])
        tblock = b''.join(tip_bytes(x) for x in tips[:0x800]) + bytes(808)
        m.write(TIPS_AT, tblock[:808*0x800])
        m.call(BUILD_NODES, [], ecx=h)
        m.call(BUILD_TIPS, [], ecx=h)
        m.call(BUILD_SLOTS, [], ecx=h)
        client = read_client_tree(m, h)
        client['log'] = rec.log
        t = tree.native(nat)
        log = []
        env = menv(case, rec, log, nat.table_c)
        narr = (NodeC*max(1, len(nodes)))(*[node_c(x) for x in nodes])
        tarr = (TipC*max(1, len(tips)))(*[tip_c(x) for x in tips])
        nat.lib.mu_master_build(ctypes.byref(t), ctypes.byref(env), narr, len(nodes), tarr, len(tips))
        native = read_native_tree(t)
        native['log'] = [(a, b, c) for a, b, c in log]
        fam.check(n, client, native)


def random_learned(rng, keys, extra=()):
    out = {}
    for s in list(rng.sample(keys, rng.randint(0, 30))) + list(extra):
        if rng.random() < 0.9:
            out[s] = (rng.choice([0, 1, 9, 10, 20, rng.randint(0, 255)]), f32(rng.uniform(-50, 500)),
                      f32(rng.uniform(0, 600)), rng.choice([0, 1, 1, 2, rng.randint(0, 255)]))
    return out


def run_access(m, nat, rng, fam, keys, table, cases):
    master = [k for k in keys if 300 <= k <= 929]
    for n in range(cases):
        learned = random_learned(rng, master + keys)
        tree = Tree(rng, keys, learned=learned)
        m.prepare(force=True)
        vs.common_stubs(m)
        h = tree.client(m)
        t = tree.native(nat)
        env = vss.master_env(table)
        for _ in range(8):
            s = rng.choice(list(learned) + master + [0, rng.randint(0, 2000)]) if learned else rng.choice(master)
            flag, kind = rng.choice([0, 1, 2]), rng.choice([0, 1, 2, 3, 4, 5, 255])
            client = (m.call(ACC_LEVEL, [s], ecx=h) & 0xff, f32(struct.unpack('<f', struct.pack('<I', float_call(m, ACC_VALUE, [s], h)))[0]),
                      m.call(ACC_FLAG, [s], ecx=h) & 0xff, m.call(ACC_HAS, [s], ecx=h) & 0xff,
                      m.call(ACC_IS, [s & 0xffffffff], ecx=h) & 0xff,
                      struct.unpack('<f', struct.pack('<I', float_call(m, ACC_CHAIN, [s, flag], h)))[0],
                      struct.unpack('<f', struct.pack('<I', float_call(m, ACC_KIND, [s, kind], h)))[0])
            native = (nat.lib.mu_master_level(t, s), f32(nat.lib.mu_master_value(t, s)), nat.lib.mu_master_flag(t, s),
                      int(bool(nat.lib.mu_master_find(t, s))), int(bool(nat.lib.mu_master_is_master(s))),
                      f32(nat.lib.mu_master_chain(t, env, s, flag)), f32(nat.lib.mu_master_kind_sum(t, env, s, kind)))
            fam.check((n, s, flag, kind), client, native)


TRAMPOLINE = 0x7e800000


def float_call(m, address, args, ecx):
    """Call a routine returning a float in st(0): a trampoline page of our own stores it (fstp dword [slot]).  The
    code is fixed per argument count (Unicorn caches translated blocks); the arguments sit in a data slot."""
    data = TRAMPOLINE
    if not getattr(m, '_tramp_mapped', False):
        m.uc.mem_map(TRAMPOLINE, 0x1000, cm.UC_PROT_ALL)
        m.allow((TRAMPOLINE, TRAMPOLINE + 0x1000))
        for n in range(4):
            code = TRAMPOLINE + 0x100 * (n + 1)
            body = b''
            for i in reversed(range(n)):
                body += b'\xff\x35' + struct.pack('<I', data + 0x10 + 4*i)    # push dword [data+0x10+4i]
            body += b'\x8b\x0d' + struct.pack('<I', data + 4)                 # mov ecx, [data+4]
            body += b'\xff\x15' + struct.pack('<I', data + 8)                 # call [data+8]
            body += b'\xd9\x1d' + struct.pack('<I', data) + b'\xc3'           # fstp dword [data]; ret
            m.uc.mem_write(code, body)
        m._tramp_mapped = True
    m.uc.mem_write(data + 4, struct.pack('<II', ecx, address))
    m.uc.mem_write(data + 0x10, b''.join(struct.pack('<I', a & 0xffffffff) for a in args))
    m.call(TRAMPOLINE + 0x100 * (len(args) + 1), [])
    return struct.unpack('<I', bytes(m.uc.mem_read(data, 4)))[0]


def run_click(m, nat, rng, fam, keys, table, records, texts, cases):
    by = {r.index: r for r in records}
    master = [k for k in keys if 300 <= k <= 929]
    for n in range(cases):
        nodes = random_nodes(rng, master or keys, rng.randint(1, 12))
        uniq = {}
        for nd in nodes:
            uniq.setdefault(nd['slot'], nd)
        nodes = list(uniq.values())
        target = rng.choice(nodes)
        extra = [target['skill'], target['p1'], target['p2']]
        learned = random_learned(rng, master, [x for x in extra if x])
        tree = Tree(rng, keys, nodes=nodes, learned=learned)
        tree.state = bytes(rng.choice([0, 9, 10, 11, rng.randint(0, 30)]) for _ in range(0x24))
        case = Case(rng, texts)
        case.points = rng.choice([target['cost'] - 1, target['cost'], target['cost'] + 3, rng.randint(-3, 300)])
        if target['skill'] in learned and rng.random() < 0.3:
            lv = list(learned[target['skill']])
            lv[0] = target['max'] & 0xff
            learned[target['skill']] = tuple(lv)
        case.special = {target['skill']: rng.random() < 0.8}
        hero = vs.HeroC()
        brand = by[target['skill']].brand if target['skill'] in by else 0
        hero.count = rng.randint(0, 20)
        for i in range(hero.count):
            hero.skills[i] = rng.choice(keys)
        if brand and rng.random() < 0.5:
            hero.skills[rng.randint(0, 0x95)] = brand
        slot = target['slot'] if rng.random() < 0.95 else 0
        m.prepare(force=True)
        h = tree.client(m)
        rec = Recorder(m, h, case)
        hcase = argparse.Namespace()
        _, a = vs.write_hero(m, hcase, hero)
        for i in range(0x96):
            m.write(a + 0x1e6 + 2*i, struct.pack('<H', hero.skills[i]))
        case.text_addr = lambda i: 0
        builder = []
        m.stub(0x00d51b91, lambda mm: mm.uc.reg_read(cm.UC_X86_REG_ECX), 0)
        m.stub(0x00d51baf, lambda mm: builder.append(('begin',) + tuple(mm.args(2))) or 0, 8)
        m.stub(0x0095c204, lambda mm: builder.append(('u8', mm.args(1)[0] & 0xff)) or 0, 4)
        m.stub(0x009eb22b, lambda mm: builder.append(('u32', s32(mm.args(1)[0]))) or 0, 4)
        m.stub(0x00d51d4f, lambda mm: builder.append(('send',)) or 0, 8)
        m.stub(0x00d51ba6, lambda mm: 0, 0)
        m.call(CLICK, [slot], ecx=h)
        result = rng.choice([0, 0, 1])
        box = rng.choice([0x47, 0x47, 0x46])
        m.call(CONFIRM, [box, result, 0, 0], ecx=h)
        client = read_client_tree(m, h)
        client['log'] = rec.log + builder
        t = tree.native(nat)
        log = []
        env = menv(case, rec, log, nat.table_c)
        nat.lib.mu_master_click(ctypes.byref(t), ctypes.byref(env), ctypes.byref(hero), slot)
        sk = I32()
        if nat.lib.mu_master_confirm(ctypes.byref(t), box, result, ctypes.byref(sk)):
            log += [('begin', 0xc1, 0x01), ('u8', 0x16), ('u32', sk.value), ('send',)]
        native = read_native_tree(t)
        native['log'] = log
        fam.check((n, slot), client, native)


def run_answer(m, nat, rng, fam, keys, table, records, texts, cases):
    by = {r.index: r for r in records}
    master = [k for k in keys if 300 <= k <= 929]
    upg = [k for k in master if by[k].use_type == 4 and by[k].brand]
    for n in range(cases):
        nodes = random_nodes(rng, master, rng.randint(1, 20))
        uniq = {}
        for nd in nodes:
            uniq.setdefault(nd['slot'], nd)
        nodes = list(uniq.values())
        if upg and rng.random() < 0.5:
            nodes[0]['skill'] = rng.choice(upg)
        learned = random_learned(rng, master)
        tree = Tree(rng, keys, nodes=nodes, learned=learned)
        tree.names = rng.choice([0x6d7, 0x6db, 0xc40])
        case = Case(rng, texts)
        hero = vs.HeroC()
        hero.count = rng.randint(0, 30)
        for i in range(hero.count):
            hero.skills[i] = rng.choice(keys)
        kind = n % 2
        if kind == 0:               # A0 10
            entries = []
            for _ in range(rng.randint(0, 12)):
                nd = rng.choice(nodes) if rng.random() < 0.85 else {'slot': rng.randint(1, 255)}
                entries.append(struct.pack('<BB2xffB3x', nd['slot'], rng.choice([0, 1, 10, 20, 255]),
                                           f32(rng.uniform(0, 99)), f32(rng.uniform(0, 99)), rng.randint(0, 3)))
            packet = b'\xc2\x00\x00\xa0\x10\x00\x00\x00' + struct.pack('<I', len(entries)) + b''.join(entries)
        else:                       # A0 14
            nd = rng.choice(nodes)
            skill = nd['skill']
            if skill in by and by[skill].brand and rng.random() < 0.7 and hero.count:
                for i in rng.sample(range(hero.count), min(2, hero.count)):
                    hero.skills[i] = by[skill].brand
            packet = bytearray(0x20)
            packet[0:4] = b'\xc1\x20\xa0\x14'
            packet[4] = rng.choice([1, 1, 1, 6, 7, 0])
            struct.pack_into('<hBxxxiBxxxffB', packet, 6, rng.randint(-5, 400), nd['slot'], skill,
                             rng.choice([1, 2, 10, 20]), f32(rng.uniform(0, 99)), f32(rng.uniform(0, 99)),
                             rng.randint(0, 2))
            packet = bytes(packet)
        m.prepare(force=True)
        h = tree.client(m)
        rec = Recorder(m, h, case)
        hcase = argparse.Namespace()
        _, a = vs.write_hero(m, hcase, hero)
        texts_at = {}

        def text_addr(i):
            if i not in texts_at:
                b = m.alloc(len(texts(i)) + 1, define=True)
                m.write(b, texts(i) + b'\0')
                texts_at[i] = b
            return texts_at[i]
        case.text_addr = text_addr
        pk = m.alloc(len(packet) + 0x20, define=True)
        m.write(pk, packet + bytes(0x20))
        m.call(LIST_RECV if kind == 0 else LEARN_RECV, [pk])
        client = read_client_tree(m, h)
        client['log'] = rec.log
        client['hero'] = list(struct.unpack('<30H', m.read(a + 0x1e6, 60)))
        t = tree.native(nat)
        log = []
        env = menv(case, rec, log, nat.table_c)
        if kind == 0:
            nat.lib.mu_master_receive_list(ctypes.byref(t), ctypes.byref(env), packet, len(packet))
        else:
            ws = vss.WorldC(ctypes.pointer(vss.master_env(nat.table_c)), ctypes.pointer(hero), None, None,
                            vs.USABLE_FN(lambda u, s: 0), None)
            pts = I32()
            log_hook = log
            stamp, keysc = vss.StampC(), vss.KeysC()
            nat.lib.mu_skill_stamp_init(ctypes.byref(stamp))
            ws.stamp, ws.keys = ctypes.pointer(stamp), ctypes.pointer(keysc)
            if packet[4] == 1:
                pass
            nat.lib.mu_master_receive_learn(ctypes.byref(t), ctypes.byref(env), ctypes.byref(ws), packet, len(packet),
                                            int(case.popup), ctypes.byref(pts))
            log_hook.insert(0, ('points', pts.value))
            if packet[4] == 1:       # the stamp / hotkey adds the client makes (verified by validate_skill_server)
                skill = struct.unpack_from('<i', packet, 0xc)[0]
                i = 1
                log_hook[i:i] = [('stamp_add', skill), ('keys_add', skill)]
        native = read_native_tree(t)
        native['log'] = log
        native['hero'] = [hero.skills[i] for i in range(30)]
        fam.check((n, kind), client, native)


def run_text(m, nat, rng, fam, keys, texts, cases):
    for n in range(cases):
        tree = Tree(rng, keys)
        tree.names = rng.choice([0x6d7, 0x6db, 0x6df, 0xc40, 0x1a99])
        tree.title = rng.choice([0x685, 0x142b, 0x188e])
        case = Case(rng, texts)
        mask = rng.randint(0, 0x7f)
        m.prepare(force=True)
        h = tree.client(m)
        rec = Recorder(m, h, case)
        m.call(SET_TEXT, [mask], ecx=h)
        t = tree.native(nat)
        log = []
        env = menv(case, rec, log, nat.table_c)
        nat.lib.mu_master_set_text(ctypes.byref(t), ctypes.byref(env), mask)
        fam.check((n, mask), rec.log, log)


def run_position(m, nat, rng, fam, keys, cases):
    for n in range(cases):
        tree = Tree(rng, keys)
        tree.pos = {rng.randint(0, 255): (f32(rng.uniform(0, 900)), f32(rng.uniform(0, 600))) for _ in range(rng.randint(0, 5))}
        scale, rx, ry = f32(rng.choice([1.0, 0.83, rng.uniform(0.5, 2)])), f32(rng.uniform(0.3, 2)), f32(rng.uniform(0.3, 2))
        slot = rng.choice(list(tree.pos) + [rng.randint(0, 255)]) if tree.pos else rng.randint(0, 255)
        x, y = f32(rng.uniform(0, 900)), f32(rng.uniform(0, 600))
        m.prepare(force=True)
        vs.common_stubs(m)
        h = tree.client(m)
        m.stub(vs.GFX_MGR, lambda mm: GFX, 0)
        m.stub(0x00abedc3, vs.float_stub(m, lambda: scale, 0), 0)
        m.stub(0x00966d99, vs.float_stub(m, lambda: rx, 0), 0)
        m.stub(0x00966d87, vs.float_stub(m, lambda: ry, 0), 0)
        m.call(POSITION, [slot, cm.fbits(x), cm.fbits(y)], ecx=h)
        client = read_client_tree(m, h)
        t = tree.native(nat)
        nat.lib.mu_master_position(ctypes.byref(t), slot, x, y, scale, rx, ry)
        native = read_native_tree(t)
        fam.check(n, (client['pos'], client['icon']), (native['pos'], tuple(f32(v) for v in native['icon'])))


def run_damage(m, nat, rng, fam, keys, table, records, cases):
    by = {r.index: r for r in records}
    master = [k for k in keys if 300 <= k <= 929]
    chained = [k for k in keys if by[k].brand not in (0, 0x4b)]
    for n in range(cases):
        skill = rng.choice(chained + master + keys + [0, 99999])
        chain, s = [], skill
        while s in by and len(chain) < 20:
            chain.append(s)
            if by[s].brand in (0, 0x4b):
                break
            s = by[s].brand
        learned = random_learned(rng, master, [c for c in chain if rng.random() < 0.7])
        tree = Tree(rng, keys, learned=learned)
        formulas = {}

        def formula(group, a, b):
            key = (group, a, b)
            if key not in formulas:
                formulas[key] = rng.choice([0.0, 12.5, float(rng.randint(0, 5000)), rng.uniform(-10, 1e4)])
            return formulas[key]
        m.prepare(force=True)
        vs.common_stubs(m)
        h = tree.client(m)
        m.stub(vs.GFX_MGR, lambda mm: GFX, 0)
        m.put32(GFX + 0x1f4, h)
        m.stub(0x0095f998, lambda mm: h, 0)       # (other families leave their stub)
        m.stub(0x00966c42, lambda mm: DUMMY, 0)
        m.stub(0x0117b5eb, double_stub(m, lambda mm: formula(*[s32(v) for v in mm.args(4)[1:4]])), 0)
        client = s32(m.call(DAMAGE, [skill], ecx=DUMMY))
        t = tree.native(nat)
        fn = FORMULA_FN(lambda u, g, a, b: formula(g, a, b))
        native = nat.lib.mu_master_skill_damage(ctypes.byref(t), ctypes.byref(vss.master_env(table)), skill, fn, None)
        fam.check((n, skill), client, native)


def double_stub(m, value):
    """A cdecl stub returning a double in st(0) (fld qword [slot]; ret)."""
    cache = m.__dict__.setdefault('_double_trampoline', None)
    if cache is None:
        slot = m._next_stub
        code = slot + 16
        m._next_stub += 32
        m.uc.mem_write(code, b'\xdd\x05' + struct.pack('<I', slot) + b'\xc3')
        m._double_trampoline = cache = (slot, code)
    slot, code = cache

    def handler(mm):
        mm.uc.mem_write(slot, struct.pack('<d', value(mm)))
        mm.uc.reg_write(cm.UC_X86_REG_EIP, code)
        return cm.REDIRECT
    return handler


TIP_BUILD, HEADER_FLAGS = 0x00bb1183, 0x0b477ef4


def run_tooltip(m, nat, rng, fam, keys, table, records, texts, cases):
    by = {r.index: r for r in records}
    master = [k for k in keys if 300 <= k <= 929]
    nat.lib.mu_master_tooltip.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(vs.TipEnvC), ctypes.POINTER(MEnvC),
                                          ctypes.POINTER(vs.HeroC), ctypes.c_int, ctypes.POINTER(vs.TipC),
                                          ctypes.POINTER(U8*80)]
    descs = [b'Increases the damage by %d.', b'Increase rate by %.1f%%#for the party', b'Raises defense %d#and more',
             b'Value: %f', b'%d%% chance']
    for n in range(cases):
        nodes = random_nodes(rng, master, rng.randint(1, 10))
        uniq = {}
        for nd in nodes:
            uniq.setdefault(nd['slot'], nd)
        nodes = list(uniq.values())
        for nd in nodes:
            nd['group'] = rng.choice([0, 1, 2])
        target = rng.choice(nodes)
        learned = random_learned(rng, master, [x for x in (target['skill'], target['p1'], target['p2']) if x])
        if target['skill'] in learned and rng.random() < 0.3:
            lv = list(learned[target['skill']])
            lv[0] = target['max'] & 0xff
            learned[target['skill']] = tuple(lv)
        tree = Tree(rng, keys, nodes=nodes, learned=learned)
        tree.state = bytes(rng.choice([0, 9, 10, 11]) for _ in range(0x24))
        tip = {'skill': target['skill'], 'mask': -1, 'rank': b'Rank %d, Skill Level: %d/%d',
               'desc': rng.choice(descs) if target['formula'] or rng.random() < 0.5 else b'No value here',
               'cost': b'Required Points: %d', 'brand': b'Needs the base skill', 'rankreq': b'Needs rank Lv. 10',
               'pre1': b'Needs the first skill', 'pre2': b'Needs the second skill'}
        if target['formula'] == 0:
            tip['desc'] = b'Static#description text'
        tips = [tip] if rng.random() < 0.95 else []
        case = Case(rng, texts)
        hero = vs.HeroC()
        hero.count = rng.randint(0, 20)
        for i in range(hero.count):
            hero.skills[i] = rng.choice(keys)
        brand = by[target['skill']].brand if target['skill'] in by else 0
        if brand and rng.random() < 0.5:
            hero.skills[rng.randint(0, 0x95)] = brand
        formulas = {}

        def formula(group, a, b):
            key = (group, a, b)
            if key not in formulas:
                formulas[key] = rng.choice([0.0, 2.5, float(rng.randint(0, 300)), rng.uniform(0, 99)])
            return formulas[key]
        slot = target['slot'] if rng.random() < 0.95 else 0
        m.prepare(force=True)
        vs.tip_machine_setup(m)
        h = tree.client(m)
        rec = Recorder(m, h, case)
        m.stubs.pop(TIP_BUILD, None)                  # (the answer family's recorder replaces it)
        vs.wrap_stubs(m, 1.0)
        m.stub(vs.TIP_HEADER, lambda mm: 0, 0)
        _, a = vs.write_hero(m, argparse.Namespace(), hero)
        for i in range(0x96):
            m.write(a + 0x1e6 + 2*i, struct.pack('<H', hero.skills[i]))
        hd, cnt = map_build(m, [(t['skill'], tip_bytes(t)) for t in tips], 0x33c)
        m.write(h + 0xc8, struct.pack('<II', hd, cnt))
        m.stub(0x00966c42, lambda mm: DUMMY, 0)
        m.stub(0x0117b5eb, double_stub(m, lambda mm: formula(*[s32(v) for v in mm.args(4)[1:4]])), 0)
        done = []
        m.stub(0x00b8d94b, lambda mm: done.append(s32(mm.args(1)[0])) or 0, 4)
        m.uc.mem_write(vs.TEXT_LIST, b'\xab'*(80*0xff))
        m.uc.mem_write(vs.TEXT_COLOR, struct.pack('<i', vs.SENTINEL)*80)
        m.uc.mem_write(vs.TEXT_BOLD, struct.pack('<i', vs.SENTINEL)*80)
        m.write(HEADER_FLAGS, bytes(4*80))
        m.put32(0x0bdcb280, 0)     # __isa_available: the CRT's scalar strstr (its SSE4.2 path misses under Unicorn)
        m.call(TIP_BUILD, [slot], ecx=h)
        if done:
            count = done[0]
            client = {'count': count,
                      'lines': [m.read(vs.TEXT_LIST + 0xff*i, 0xff).split(b'\0')[0] for i in range(count)],
                      'colors': list(struct.unpack('<80i', m.read(vs.TEXT_COLOR, 320)))[:count],
                      'bolds': list(struct.unpack('<80i', m.read(vs.TEXT_BOLD, 320)))[:count],
                      'headers': [i for i, v in enumerate(struct.unpack('<80i', m.read(HEADER_FLAGS, 320))) if v]}
        else:
            client = None
        client = (client, list(m.read(h + 0x78, 0x24)))
        t = tree.native(nat)
        ctips = (TipC*max(1, len(tips)))(*[tip_c(x) for x in tips])
        for i in range(len(tips)):
            t.tips[i] = ctypes.addressof(ctips[i])
        t.ntips = len(tips)
        log = []
        env = menv(case, rec, log, nat.table_c)
        tenv = vs.TipEnvC(ctypes.pointer(rec._env), None, vs.TEXT_FN(lambda u, i: case.text_ptr(i)),
                          vs.TIP_FN(lambda u, k: None), vs.INFO_FN(lambda *a: None), vs.HAS_FN(lambda u, s: 0),
                          vs.HAS_FN(lambda u, s: 0), vs.FLOAT1_FN(lambda u, s: 0.0),
                          vs.FORMULA_FN(lambda u, g, a, b: formula(g, a, b)),
                          vs.MEASURE_FN(lambda u, txt, k: vs.measure_bytes(ctypes.string_at(txt, k))), 1.0)
        out = vs.TipC()
        heads = (U8*80)()
        count = nat.lib.mu_master_tooltip(ctypes.byref(t), ctypes.byref(tenv), ctypes.byref(env), ctypes.byref(hero),
                                          slot, ctypes.byref(out), ctypes.byref(heads))
        if count:
            native = {'count': count, 'lines': [bytes(out.lines[i]).split(b'\0')[0][:0xfe] for i in range(count)],
                      'colors': [out.color[i] if out.set[i] & 1 else vs.SENTINEL for i in range(count)],
                      'bolds': [out.bold[i] if out.set[i] & 2 else vs.SENTINEL for i in range(count)],
                      'headers': [i for i in range(80) if heads[i]]}
        else:
            native = None
        native = (native, list(t.state))
        fam.check((n, slot), client, native)


ICON_DRAW = 0x00bb0e2d


def run_icons(m, nat, rng, fam, keys, table, records, cases):
    master = [k for k in keys if 300 <= k <= 929]
    for n in range(cases):
        nodes = random_nodes(rng, master, rng.randint(0, 15))
        uniq = {}
        for nd in nodes:
            uniq.setdefault(nd['slot'], nd)
        nodes = list(uniq.values())
        for nd in nodes:
            nd['group'] = rng.choice([0, 1, 2])
        learned = random_learned(rng, master, [nd['p1'] for nd in nodes if nd['p1']])
        tree = Tree(rng, keys, nodes=nodes, learned=learned)
        tree.state = bytes(rng.choice([0, 9, 10, 11]) for _ in range(0x24))
        tree.pos = {nd['slot']: (f32(rng.uniform(0, 900)), f32(rng.uniform(0, 600))) for nd in nodes if rng.random() < 0.8}
        case = Case(rng, lambda i: b'')
        case.special = {nd['skill']: rng.random() < 0.8 for nd in nodes}
        hero = vs.HeroC()
        hero.count = rng.randint(0, 10)
        for i in range(hero.count):
            hero.skills[i] = rng.choice(keys)
        x0, y0 = f32(rng.uniform(0, 300)), f32(rng.uniform(0, 200))
        scale, rx, ry = f32(rng.choice([1.0, 0.9])), f32(rng.uniform(0.3, 2)), f32(rng.uniform(0.3, 2))
        iw, ih = f32(26*scale*rx), f32(37*scale*ry)
        m.prepare(force=True)
        h = tree.client(m)
        m.write(h + 0xb0, struct.pack('<ff', iw, ih))
        Recorder(m, h, case)
        _, a = vs.write_hero(m, argparse.Namespace(), hero)
        for i in range(0x96):
            m.write(a + 0x1e6 + 2*i, struct.pack('<H', hero.skills[i]))
        m.stub(0x00aae509, vs.float_stub(m, lambda: x0, 0), 0)
        m.stub(0x00aae601, vs.float_stub(m, lambda: y0, 0), 0)
        m.stub(0x00abedc3, vs.float_stub(m, lambda: scale, 0), 0)
        m.stub(0x00966d99, vs.float_stub(m, lambda: rx, 0), 0)
        m.stub(0x00966d87, vs.float_stub(m, lambda: ry, 0), 0)
        draws = []
        m.stub(0x0184e01a, lambda mm: draws.append((s32(mm.args(10)[0]),) + tuple(round(cm.bits_f(w), 5) for w in mm.args(10)[1:9])
                                                   + (mm.args(10)[9],)) or 0, 0)
        m.call(ICON_DRAW, [], ecx=h)
        client = (draws, list(m.read(h + 0x78, 0x24)))
        t = tree.native(nat)
        t.icon_w, t.icon_h = iw, ih
        log = []
        env = menv(case, Recorder.__new__(Recorder), log, nat.table_c) if False else None
        rec2 = Recorder.__new__(Recorder)
        rec2.case = case
        cb = rec2.callbacks(case, log)
        menv_env = vss.master_env(nat.table_c)
        env = MEnvC(None, ctypes.pointer(menv_env), *cb)
        ndraws = []
        DRAW_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, I32, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                   ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                   ctypes.c_uint32)
        fn = DRAW_FN(lambda u, b, x, y, w, hh, uu, vv, uw, vh, c: ndraws.append(
            (b,) + tuple(round(f32(q), 5) for q in (x, y, w, hh, uu, vv, uw, vh)) + (c,)))
        nat.lib.mu_master_icons.argtypes = [ctypes.POINTER(TreeC), ctypes.POINTER(MEnvC), ctypes.POINTER(vs.HeroC),
                                            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                            DRAW_FN, ctypes.c_void_p]
        nat.lib.mu_master_icons(ctypes.byref(t), ctypes.byref(env), ctypes.byref(hero), x0, y0, scale, rx, ry, fn, None)
        fam.check(n, client, (ndraws, list(t.state)))


FAMILIES = ['class', 'build', 'access', 'click', 'answer', 'text', 'position', 'damage', 'tooltip', 'icons']
MUTANTS = {16: 'click', 17: 'answer', 18: 'damage'}


def run_all(m, nat, snap, args, families, report, rng, quiet=False):
    records = vs.snapshot_records(snap)
    names = {row['index']: row['name'] for row in plain.read_skills(snap)}
    for r in records:
        r.name = bytes(names.get(r.index, b''))[:127]
    keys = [r.index for r in records]
    table = nat.table(records)
    nat.table_c = table
    texts = snapshot_text(snap)
    installed = installed_tables(args.game_root) if 'build' in families else None
    for name in families:
        fam = vs.Family(name)
        if name == 'class':
            run_class(m, nat, rng, fam, keys)
        elif name == 'build':
            run_build(m, nat, rng, fam, keys, texts, min(args.cases, 120), installed)
        elif name == 'access':
            run_access(m, nat, rng, fam, keys, table, args.cases)
        elif name == 'click':
            run_click(m, nat, rng, fam, keys, table, records, texts, args.cases)
        elif name == 'answer':
            run_answer(m, nat, rng, fam, keys, table, records, texts, args.cases)
        elif name == 'text':
            run_text(m, nat, rng, fam, keys, texts, args.cases)
        elif name == 'position':
            run_position(m, nat, rng, fam, keys, args.cases)
        elif name == 'damage':
            run_damage(m, nat, rng, fam, keys, table, records, args.cases)
        elif name == 'tooltip':
            run_tooltip(m, nat, rng, fam, keys, table, records, texts, args.cases)
        elif name == 'icons':
            run_icons(m, nat, rng, fam, keys, table, records, args.cases)
        else:
            raise SystemExit(f'unknown family {name}')
        report['families'][fam.name] = fam.summary()
        if not quiet:
            print(fam.name, json.dumps({k: v for k, v in fam.summary().items()
                                        if k not in ('examples', 'samples') or args.verbose}), flush=True)


def mutations(m, snap, args, families, work):
    out = {}
    for number, family in MUTANTS.items():
        if family not in families:
            continue
        ext = 'dylib' if sys.platform == 'darwin' else 'so'
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill'), f'mutant{number}.{ext}'], check=True)
        nat = TreeNative(work, ROOT/f'reconstructed/skill/mutant{number}.{ext}')
        report = {'families': {}}
        small = argparse.Namespace(**vars(args))
        small.cases = min(args.cases, 200)
        run_all(m, nat, snap, small, [family], report, random.Random(args.seed + number), quiet=True)
        out[f'mutant{number}:{family}'] = sum(f['mismatches'] for f in report['families'].values()) > 0
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', default=os.environ.get('SNAP'), help='langread snapshot (local)')
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--families', default=','.join(FAMILIES))
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--verbose', action='store_true')
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
        nat = TreeNative(work)
        run_all(m, nat, snap, args, families, report, random.Random(args.seed))
        if args.mutations:
            report['mutations'] = mutations(m, snap, args, families, work)
            print('mutations', json.dumps(report['mutations']))
    report['mismatches'] = sum(f['mismatches'] for f in report['families'].values())
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    for name, fam in report['families'].items():
        if fam['mismatches']:
            print(name, json.dumps(fam['examples'][:2])[:3000])
    print('total cases', sum(f['cases'] for f in report['families'].values()), 'mismatches', report['mismatches'])
    if report['mismatches'] or (args.mutations and not all(report['mutations'].values())):
        sys.exit(1)


if __name__ == '__main__':
    main()
