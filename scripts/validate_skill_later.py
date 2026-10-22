#!/usr/bin/env python3
"""Run the client's fourth skill tree routines in Unicorn and compare them with reconstructed/skill/tree4.c
(NATIVE-SKILL-003, docs/research/client-skills.md section 12).

Inputs: the pinned restored text and second image section (as validate_skill.py) and a langread snapshot that
holds 4ThTreeData's nested maps (graph:0x06fbb8ec, NATIVE-SKILL-003) and Skill(Kor).  The handler (0xfc bytes) is
built by its real constructor 0x00c22e0b; the group states, nodes and lists are the client's own allocations.

Families:

* table: every record of the snapshot's 4ThTreeData through the getter 0x010b4406 (the class / group / index maps)
  against the C table rebuilt from the exported rows, plus absent keys (the default record);
* row: the row parser 0x010b4506 on synthetic rows (short rows, unknown classes, repeated indices) against
  mu_t4_table_row, the class objects' maps read back;
* build: per class, the window build 0x00c24024 (0x0109ee60 group states, 0x0109fc40 links, tabs, RequestSlotUIInfo,
  SetTabInfo 0x00c246b2) with random hero answers; the invokes and the whole runtime state compared;
* list: the 7E 02 list 0x0127f539 with random entries (0x00c26224 levels with 0x0109f0a2's propagation, 0x00c2632a
  links, 0x00c23dc2 the page, 0x00c24922 slots, 0x00c26e11 / 0x0109f6e1 / 0x00c25173 the refresh);
* page: OnChangeTab 0x00c25b6c and 0x00c23dc2 on random states;
* click: OnMouseClickSlot 0x00c25bda on random states (messages, the branch popup, the confirm box) and the
  confirm answer 0x00b3771c (id 0x73) with the request 0x00b3b703 recorded;
* answer: the 7E 01 answer 0x0125051f (results 1, 4, 7) and 7E 03 0x0127f679.

Modelled (not client code): import calls stop a case; the heap; GFx (CreateObject / CreateArray on the movie,
the ObjectInterface's SetMember / SetElement / SetArraySize, Invoke 0x00aaf3ef and the formatted Invoke 0x00aae7e0
whose %d %u %s %b %f arguments become typed values); ToUTF8 is the identity; the hero's skill list 0x00a00287, the
Master tree's level 0x00bb1d9d, the side-option key 0x010b6f79, the message and confirm boxes, the popup and the
character window, the packet builder (verified by validate_protocol.py) are recording stubs with case answers.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402
import validate_skill as vs  # noqa: E402
import validate_skill_tree as vst  # noqa: E402
from validate_skill import s32  # noqa: E402

TREE4, TIPS4, SIDE4 = 0x06fbb8ec, 0x06fbb930, 0x06fbbaec
GET_RECORD, ROW_PARSE, GET_CLASS = 0x010b4406, 0x010b4506, 0x010b4465
CTOR, BUILD, TAB_INFO, SHOW_PAGE, SLOTS = 0x00c22e0b, 0x00c24024, 0x00c246b2, 0x00c23dc2, 0x00c24922
ENTRY, ENTRY_LINKS, REFRESH_ALL, CHANGE_TAB, CLICK = 0x00c26224, 0x00c2632a, 0x00c26e11, 0x00c25b6c, 0x00c25bda
SET_POINTS, LIST_RECV, ANSWER_RECV, POINTS_RECV, BOX_ANSWER = 0x00c23a96, 0x0127f539, 0x0125051f, 0x0127f679, 0x00b3771c
SKILL_LOOKUP, SKILL_TABLE = 0x00961620, plain.SKILL
GFX_MGR, TREE4_GET = 0x00ac3bf7, 0x0095fb49
INVOKE_V, INVOKE_F = 0x00aaf3ef, 0x00aae7e0
VT_NUMBER, VT_STRING, VT_OBJECT, VT_ARRAY, VT_BOOL = 3, 4, 6, 7, 2


# ---- machine placement ---------------------------------------------------------------------------------------

def relocate(snap):
    """Move the machine's case heap and stack to holes the snapshot leaves (its heap blocks are mapped at their
    live addresses).  validate_lang.RESERVED follows."""
    used = sorted((a, a + len(b)) for a, b in snap.blocks.items())

    def free(base, size):
        return not any(a < base + size and base < b for a, b in used)
    heap = next(b for b in range(0x30000000, 0x7a000000, 0x01000000) if free(b, cm.HEAP_SIZE))
    stack = next(b for b in range(heap + cm.HEAP_SIZE, 0x7e000000, 0x00100000) if free(b, cm.STACK_SIZE))
    cm.HEAP_BASE, cm.STACK_BASE = heap, stack
    vl.RESERVED = ((0, 0x10000), (cm.STACK_BASE, cm.STACK_BASE + cm.STACK_SIZE), (cm.TEXT_BASE, cm.BSS_BASE),
                   (cm.BSS_BASE, cm.BSS_END), (cm.HEAP_BASE, cm.HEAP_BASE + cm.HEAP_SIZE), (cm.STUB_BASE, 1 << 32))
    return heap, stack


# ---- GFx model -----------------------------------------------------------------------------------------------

class Gfx:
    """The movie (vtable +0x34 CreateObject, +0x38 CreateArray), the ObjectInterface methods and both Invokes."""

    def __init__(self, m, log):
        self.m, self.log, self.objs = m, log, {}
        self.oi = m.alloc(0x40, define=True)
        self.vt = m.alloc(0x100, define=True)
        self.movie = m.alloc(0x40, define=True)
        m.put32(self.movie, self.vt)

        def at(fn, cleanup):
            a = m._new_stub()
            m.stub(a, fn, cleanup)
            return a
        m.put32(self.vt + 0x34, at(self._object, 0x10))
        m.put32(self.vt + 0x38, at(self._array, 4))
        m.stub(0x00404dd0, self._set_member, 0x10)
        m.stub(0x00405060, self._set_element, 0xc)
        m.stub(0x00405010, self._set_size, 8)
        m.stub(INVOKE_V, self._invoke_v, 8)
        m.stub(INVOKE_F, self._invoke_f, 0)

    def _new(self, kind):
        oid = len(self.objs) + 1
        self.objs[oid] = {} if kind == VT_OBJECT else []
        return oid

    def _object(self, mm):
        v = mm.args(1)[0]
        mm.write(v, struct.pack('<III', self.oi, VT_OBJECT, self._new(VT_OBJECT)))
        return 0

    def _array(self, mm):
        v = mm.args(1)[0]
        mm.write(v, struct.pack('<III', self.oi, VT_ARRAY, self._new(VT_ARRAY)))
        return 0

    def value(self, v):
        _, kind, data = struct.unpack('<III', self.m.read(v, 12))
        kind &= 0x8f
        if kind == VT_NUMBER:
            return struct.unpack('<d', self.m.read(v + 8, 8))[0]
        if kind == VT_STRING:
            return self.m.cstr(data).decode('latin1')
        if kind == VT_BOOL:
            return bool(data & 0xff)
        if kind in (VT_OBJECT, VT_ARRAY):
            return ('ref', data)
        return None

    def resolve(self, x):
        if isinstance(x, tuple) and x[0] == 'ref':
            o = self.objs[x[1]]
            if isinstance(o, dict):
                return {k: self.resolve(v) for k, v in o.items()}
            return [self.resolve(v) for v in o]
        return x

    def _set_member(self, mm):
        data, name, val, _ = mm.args(4)
        self.objs[data][mm.cstr(name).decode()] = self.value(val)
        return 1

    def _set_element(self, mm):
        data, idx, val = mm.args(3)
        arr = self.objs[data]
        arr.extend([None] * (idx + 1 - len(arr)))
        arr[idx] = self.value(val)
        return 1

    def _set_size(self, mm):
        data, n = mm.args(2)
        arr = self.objs[data]
        del arr[n:]
        arr.extend([None] * (n - len(arr)))
        return 1

    def _invoke_v(self, mm):
        name, val = mm.args(2)
        self.log.append(('invoke', mm.cstr(name).decode(), self.resolve(self.value(val))))
        return 1

    def _invoke_f(self, mm):
        w = mm.args(24)
        fmt = mm.cstr(w[2]).decode()
        args, k, i = [], 3, 0
        while i < len(fmt):
            if fmt[i] != '%':
                i += 1
                continue
            conv = fmt[i + 1]
            if conv == 'd':
                args.append(float(s32(w[k])))
                k += 1
            elif conv == 'u':
                args.append(float(w[k]))
                k += 1
            elif conv == 's':
                args.append(mm.cstr(w[k]).decode('latin1'))
                k += 1
            elif conv == 'b':
                args.append(bool(w[k] & 0xff))
                k += 1
            elif conv == 'f':
                args.append(struct.unpack('<d', struct.pack('<II', w[k], w[k + 1]))[0])
                k += 2
            i += 2
        self.log.append(('invoke', mm.cstr(w[1]).decode(), args))
        return 0


def norm(v):
    """Numbers as floats (GFx numbers are doubles), the rest as is."""
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    return [norm(x) for x in v]


# ---- the snapshot's table ---------------------------------------------------------------------------------

def table_rows(snap):
    """(class, [27 file columns], hidden) for every record of 4ThTreeData, plus the class list and min columns."""
    classes, rows = [], []
    for cls, cn in snap.tree(TREE4 + 0x3c):
        classes.append(s32(cls))
        for gk, gn in snap.tree(cn + 0x14 + 8):
            for ik, nn in snap.tree(gn + 0x14 + 8):
                f = list(struct.unpack('<27i', snap.read(nn + 0x14, 27*4)))
                hidden = snap.read(nn + 0x14 + 0x6c, 1)[0]
                cols = f[:8]
                for i in range(5):
                    cols += [f[8 + i], f[13 + i]]
                cols += f[18:27]
                rows.append((s32(cls), cols, hidden))
    return classes, rows, s32(snap.u32(TREE4 + 0x38))


def skill_info_of(snap):
    info = {s32(k): (snap.read(n + 0x14, 1)[0], s32(snap.u32(n + 0x14 + 0x58)))
            for k, n in snap.tree(SKILL_TABLE + 0x108)}
    default = 0x06fbb170
    dflt = (snap.read(default, 1)[0], s32(snap.u32(default + 0x58)))
    return lambda skill: info.get(skill, dflt)


def side_keys(snap):
    """4thTreeSideOption +0x44: key -> [(index, group)] as 0x0109b60e searches it (modelled in the C side's
    callback; the client runs its own)."""
    out = {}
    try:
        for k, n in snap.tree(SIDE4 + 0x44):
            out[s32(k)] = n
    except Exception:
        pass
    return out


# ---- native side ------------------------------------------------------------------------------------------

SKILL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int),
                            ctypes.POINTER(ctypes.c_int))
HAS_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)
TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int32)
INVOKE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p)
BOX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
CONFIRM_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)
EVENT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32)
SIDE_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
POPUP_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)


class EnvC(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('skill_info', SKILL_FN), ('hero_has', HAS_FN), ('master_level', HAS_FN),
                ('text', TEXT_FN), ('invoke', INVOKE_FN), ('msgbox', BOX_FN), ('confirm', CONFIRM_FN),
                ('event', EVENT_FN), ('side_category', SIDE_FN), ('popup_shows_tree', POPUP_FN)]


class Native:
    def __init__(self, work, lib=None):
        path = lib or (ROOT/'reconstructed/skill'/('libclientskill.dylib' if sys.platform == 'darwin' else
                                                    'libclientskill.so'))
        if lib is None:
            subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill')], check=True)
        self.lib = L = ctypes.CDLL(str(path))
        L.mu_t4_table_init.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_table_free.argtypes = [ctypes.c_void_p]
        L.mu_t4_table_class.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_table_row.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.c_int]
        L.mu_t4_table_get.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
        L.mu_t4_table_get.restype = ctypes.POINTER(ctypes.c_int32 * 28)
        for name, args in (('mu_t4_window_init', [ctypes.c_void_p, ctypes.c_void_p]),
                           ('mu_t4_window_free', [ctypes.c_void_p]),
                           ('mu_t4_set_class', [ctypes.c_void_p, ctypes.c_int32]),
                           ('mu_t4_set_points', [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]),
                           ('mu_t4_build', [ctypes.c_void_p, ctypes.c_void_p]),
                           ('mu_t4_show_page', [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]),
                           ('mu_t4_change_tab', [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]),
                           ('mu_t4_entry', [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32,
                                            ctypes.c_int32, ctypes.c_float, ctypes.c_float]),
                           ('mu_t4_entry_links', [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]),
                           ('mu_t4_refresh_all', [ctypes.c_void_p, ctypes.c_void_p])):
            getattr(L, name).argtypes = args
        L.mu_t4_click.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_confirm.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint8),
                                    ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint16)]
        L.mu_t4_request.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint8, ctypes.c_uint16,
                                    ctypes.c_uint16]
        L.mu_t4_request.restype = ctypes.c_size_t
        L.mu_t4_receive.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_t4_dump.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_t4_dump.restype = ctypes.c_size_t
        self.table = ctypes.create_string_buffer(64)
        self.window = ctypes.create_string_buffer(1024)

    def load_table(self, classes, rows, min_columns):
        L = self.lib
        L.mu_t4_table_free(self.table)
        L.mu_t4_table_init(self.table, min_columns)
        for c in classes:
            L.mu_t4_table_class(self.table, c)
        for cls, cols, hidden in rows:
            arr = (ctypes.c_int32 * len(cols))(*cols)
            L.mu_t4_table_row(self.table, cls, arr, len(cols))

    def dump(self):
        n = self.lib.mu_t4_dump(self.window, None, 0)
        buf = ctypes.create_string_buffer(n + 1)
        self.lib.mu_t4_dump(self.window, buf, n + 1)
        return json.loads(buf.value.decode())


class Case:
    """The outside answers of one case."""

    def __init__(self, rng, skill_info, keys):
        self.skill_info = skill_info
        easy = rng.random() < 0.4
        self.has = {k: easy or rng.random() < 0.5 for k in keys}
        self.master = {k: 255 if easy else rng.choice([0, rng.randint(0, 20), 10, 9]) for k in keys}
        self.side = {}

    def env(self, nat, log, texts):
        bufs = {}

        def skill(u, s, b0, use):
            a, b = self.skill_info(s)
            b0[0], use[0] = a, b
            return 1

        def text(u, i):
            if i not in bufs:
                bufs[i] = texts(i)
            return bufs[i]

        def invoke(u, name, args):
            a = args.decode('latin1')
            log.append(('invoke', name.decode(), json.loads(a) if a[:1] in '[{' else a))

        cbs = [SKILL_FN(skill), HAS_FN(lambda u, s: int(self.has.get(s, False))),
               HAS_FN(lambda u, s: self.master.get(s, 0)), TEXT_FN(text), INVOKE_FN(invoke),
               BOX_FN(lambda u, t: log.append(('msgbox', t.decode('latin1')))),
               CONFIRM_FN(lambda u, i, t: log.append(('confirm', i, t.decode('latin1')))),
               EVENT_FN(lambda u, w, a: log.append(('event', w.decode(), a))),
               SIDE_FN(lambda u, i, g: self.side.get((i, g), -1)), POPUP_FN(lambda u: 0)]
        env = EnvC(None, *cbs)
        env._keep = cbs
        return env


# ---- client side ------------------------------------------------------------------------------------------

class Client:
    """The machine with the snapshot and one handler per case."""

    def __init__(self, text, data, snap, texts, strict=False):
        self.snap = snap
        self.m = vl.LangMachine(text, data, snap, check_reads=strict)
        self.m.heap_checks(strict)
        if not strict:      # the allowlist is the whole text here: the per-block check only costs time
            self.m.uc.hook_del(self.m.block_hook)
        self.texts = texts
        self.log = []

    def new_case(self, case, cls):
        m = self.m
        m.prepare(force=True)
        vs.common_stubs(m)
        self.log = log = []
        self.gfx = Gfx(m, log)
        h = m.alloc(0x100, define=True)
        gfxmgr = m.alloc(0x300, define=True)
        master = m.alloc(0xd8, define=True)
        for off in (0xb8, 0xc0, 0xc8, 0xd0):
            hd, n = vst.map_build(m, [], 0x24)
            m.write(master + off, struct.pack('<II', hd, n))
        m.put32(gfxmgr + 0x1f4, master)
        m.put32(gfxmgr + 0x1f8, h)
        m.stub(GFX_MGR, lambda mm: gfxmgr, 0)
        movie = self.gfx.movie

        def base_ctor(mm):
            obj = mm.uc.reg_read(cm.UC_X86_REG_ECX)
            mm.write(obj, bytes(0x78))
            mm.put32(obj + 8, movie)
            return obj
        m.stub(0x00aad53a, base_ctor, 0)
        m.stub(0x00ab02b7, lambda mm: 0, 0)               # the callback table (not used by the families)
        m.stub(0x00ab02fd, lambda mm: 0, 4)
        attrs = m.alloc(0x100, define=True)
        m.put32(vs.ATTR, attrs)
        m.stub(0x00a00287, lambda mm: int(case.has.get(s32(mm.args(1)[0]), False)), 4)
        m.stub(0x00bb1d9d, lambda mm: case.master.get(s32(mm.args(1)[0]), 0) & 0xff, 4)
        m.stub(0x009e819e, lambda mm: vl.DUMMY + 0x80, 0)
        m.stub(0x00aae6f9, lambda mm: 0, 0)               # the popup and the character window are closed
        m.stub(0x010b6f79, lambda mm: case.side.get(tuple(s32(v) for v in mm.args(2)), -1) & 0xffffffff, 8)

        m.stub(0x00b3967c, lambda mm: log.append(('msgbox', mm.cstr(mm.args(3)[2]).decode('latin1'))) or 0, 0x1c)
        m.stub(0x00b39648, lambda mm: log.append(('confirm', s32(mm.args(2)[1]), mm.cstr(mm.args(3)[2])
                                                  .decode('latin1'))) or 0, 0x20)
        m.stub(0x0095f5d7, lambda mm: vl.DUMMY + 0x40, 0)
        m.stub(0x009619dd, lambda mm: vs.sprintf_model(mm, *(lambda w: (w[0], mm.cstr(w[1]), w[2:]))(mm.args(16))), 0)

        self.stream = vs.StreamModel(m)
        m.stub(0x0094f781, lambda mm: 0, 8)
        vbt = m.alloc(8, define=True)
        m.write(vbt, struct.pack('<ii', 0, 0x40))
        ctor = m.stubs[vs.STREAM_CTOR][1][0]
        streams, pos = self.stream.streams, {}

        def stream_ctor(mm):                            # the ostringstream's vbtable pointer (ios at +0x40)
            obj = mm.uc.reg_read(cm.UC_X86_REG_ECX)
            pos.pop(obj, None)
            r = ctor(mm)
            mm.put32(obj, vbt)
            return r
        m.stub(vs.STREAM_CTOR, stream_ctor, 4)
        # the branch popup's text: operator<<(ostream&, char) 0x009443a1, std::getline(istream&, string&, char)
        # 0x00948afe and the stream's bool 0x0096996a over the same modelled buffer

        def put_char(mm):
            stream, ch = mm.args(2)
            streams[stream].append(ch & 0xff)
            return stream

        def getline(mm):
            stream, out, delim = mm.args(3)
            data, at = streams[stream], pos.get(stream, 0)
            if at >= len(data):
                pos[stream] = -1
                vs.write_std_string(mm, out, b'')
                return stream
            end = data.find(bytes([delim & 0xff]), at)
            stop = len(data) if end < 0 else end
            vs.write_std_string(mm, out, bytes(data[at:stop]))
            pos[stream] = len(data) if end < 0 else end + 1
            return stream
        m.stub(0x009443a1, put_char, 0)
        m.stub(0x00948afe, getline, 0)
        m.stub(0x0096996a, lambda mm: int(pos.get(mm.uc.reg_read(cm.UC_X86_REG_ECX) - 0x40, 0) >= 0), 0)

        def utf8(mm):
            out, src = mm.args(2)
            vs.write_std_string(mm, out, mm.std_string(src))
            return out
        m.stub(vst.TO_UTF8, utf8, 0)
        m.call(CTOR, [], ecx=h)
        m.put32(h + 0x78, cls)
        self.h = h
        return h

    def call(self, address, args=(), ecx=None):
        return self.m.call(address, list(args), ecx=self.h if ecx is None else ecx)

    def dump(self):
        m, h = self.m, self.h
        out = {'cls': s32(m.u32(h + 0x78)), 'points': s32(m.u32(h + 0x7c)),
               'pend': [s32(m.u32(h + 0x80)), s32(m.u32(h + 0x84))], 'tab': s32(m.u32(h + 0x88))}
        cur = m.u32(h + 0x8c)
        out['cur'] = s32(m.u32(cur)) if cur else -1
        groups = []
        for gid, gn in vst.map_read(m, h + 0x90):
            g = m.u32(gn + 0x14)
            nodes = []
            for idx, nn in vst.map_read(m, g + 0xc):
                n = m.u32(nn + 0x14)
                skill, level, value, nxt = struct.unpack('<iiff', m.read(n + 8, 16))
                avail, opened = m.read(n + 0x18, 2)

                def lst(at):
                    head, size = struct.unpack('<II', m.read(at, 8))
                    items, p = [], m.u32(head)
                    while p != head and len(items) <= size:
                        items.append(s32(m.u32(m.u32(p + 8))))
                        p = m.u32(p)
                    return items
                enh = [[s32(k), s32(m.u32(e + 0x14))] for k, e in vst.map_read(m, n + 0x2c)]
                nodes.append([s32(m.u32(n)), m.read(n + 4, 1)[0], skill, level, value, nxt, avail, opened,
                              lst(n + 0x38), lst(n + 0x40), enh])
            roots = [s32(k) for k, _ in vst.map_read(m, g + 0x14)]
            groups.append({'id': s32(m.u32(g)), 'rows': s32(m.u32(g + 4)), 'kind': s32(m.u32(g + 8)), 'roots': roots,
                           'nodes': nodes})
        out['groups'] = groups
        tabs = []
        for key, tn in vst.map_read(m, h + 0xa8):
            t = m.u32(tn + 0x14)
            tabs.append([s32(m.u32(t)), s32(m.u32(t + 4)), s32(m.u32(t + 8)),
                         [s32(m.u32(n + 0x14)) for _, n in vst.map_read(m, t + 0xc)]])
        out['tabs'] = tabs
        out['skill8'] = [[s32(k), s32(m.u32(m.u32(n + 0x14)))] for k, n in vst.map_read(m, h + 0xa0)]
        out['branch'] = self.branch()
        out['branch_visible'] = m.read(h + 0xec, 1)[0]
        return out

    def branch(self):
        m, h = self.m, self.h
        first, last = struct.unpack('<II', m.read(h + 0xf0, 8))
        if not first:
            return []
        return [s32(v) for v in struct.unpack(f'<{(last - first)//4}I', m.read(first, last - first))]


# ---- families -------------------------------------------------------------------------------------------------

def first_diff(a, b, path=''):
    if type(a) != type(b):
        return f'{path}: {a!r:.300} != {b!r:.300}'
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f'{path}.{k}: missing on one side'
            d = first_diff(a[k], b[k], f'{path}.{k}')
            if d:
                return d
        return None
    if isinstance(a, (list, tuple)):
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f'{path}[{i}]')
            if d:
                return d
        if len(a) != len(b):
            return f'{path}: length {len(a)} != {len(b)}; next {a[len(b):len(b)+1]!r:.300} / {b[len(a):len(a)+1]!r:.300}'
        return None
    return None if a == b else f'{path}: {a!r:.300} != {b!r:.300}'


class Family:
    def __init__(self, name):
        self.name, self.cases, self.mismatches, self.examples = name, 0, 0, []
        self.coverage = {}

    def check(self, key, client, native):
        self.cases += 1
        if isinstance(client, tuple) and client and isinstance(client[0], list):
            tags = sorted({e[1] if e[0] == 'invoke' else e[0] for e in client[0]})
            for t in tags:
                self.coverage[t] = self.coverage.get(t, 0) + 1
        a, b = norm(client), norm(native)
        if a != b:
            self.mismatches += 1
            if len(self.examples) < 3:
                diff = first_diff(a, b)
                if isinstance(client, tuple) and client and client[0] == 'error':
                    diff = 'client: ' + str(client[1])
                self.examples.append({'case': repr(key)[:300], 'diff': diff})

    def report(self):
        return {'cases': self.cases, 'mismatches': self.mismatches, 'coverage': self.coverage,
                'examples': self.examples}


def run_build(cl, nat, rng, fam, classes, case_of, texts, cases):
    for n in range(cases):
        cls = classes[n % len(classes)]   # an absent class reads the static default object (not in the snapshot)
        case = case_of(rng)
        cl.new_case(case, cls)
        try:
            cl.call(BUILD)
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        log = []
        env = case.env(nat, log, texts)
        L = nat.lib
        L.mu_t4_window_free(nat.window)
        L.mu_t4_window_init(nat.window, nat.table)
        L.mu_t4_set_class(nat.window, cls)
        L.mu_t4_build(nat.window, ctypes.byref(env))
        fam.check(('build', cls), client, (log, nat.dump()))


def list_packet(rng, rows, cls, points):
    recs = [r for r in rows if r[0] == cls]
    entries = []
    for _ in range(rng.choice([0, 1, 3, 8, 20, 40])):
        if recs and rng.random() < 0.9:
            cols = rng.choice(recs)[1]
            group, index, top = cols[1], cols[0], cols[18 + 1]
        else:
            group, index, top = rng.randint(0, 5), rng.randint(0, 70), 20
        level = rng.choice([0, 1, rng.randint(0, max(1, top)), top, top + 1, rng.randint(0, 255)])
        entries.append(struct.pack('<BHBff', group & 0xff, index & 0xffff, level & 0xff,
                                   rng.choice([0.0, rng.uniform(0, 500)]), rng.choice([0.0, rng.uniform(0, 500)])))
    body = struct.pack('<BBHI', 0, 0, points & 0xffff, len(entries))[1:] + b''.join(entries)
    head = bytes([0xc2, 0, 0, 0x7e, 2]) if False else bytes([0xc1, 0, 0x7e, 2])
    pkt = bytearray(head + bytes([0]) + struct.pack('<HI', points & 0xffff, len(entries)) + b''.join(entries))
    pkt[1] = len(pkt) & 0xff
    return bytes(pkt)


def native_window(nat, case, log, texts, cls):
    env = case.env(nat, log, texts)
    L = nat.lib
    L.mu_t4_window_free(nat.window)
    L.mu_t4_window_init(nat.window, nat.table)
    L.mu_t4_set_class(nat.window, cls)
    return env


def client_packet(cl, address, pkt):
    buf = cl.m.alloc(len(pkt) + 16, define=True)
    cl.m.write(buf, pkt + bytes(16))
    cl.m.call(address, [buf])


def run_list(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    for n in range(cases):
        cls = rng.choice(classes)
        case = case_of(rng)
        pkt = list_packet(rng, rows, cls, rng.choice([0, 1, 5, rng.randint(0, 65535)]))
        cl.new_case(case, cls)
        if os.environ.get('T4_TRACE'):
            print('case', n, cls, pkt.hex(), flush=True)
        try:
            client_packet(cl, LIST_RECV, pkt)
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        if os.environ.get('T4_TRACE'):
            print(' client done', flush=True)
        log = []
        env = native_window(nat, case, log, texts, cls)
        nat.lib.mu_t4_receive(nat.window, ctypes.byref(env), pkt, len(pkt))
        if os.environ.get('T4_TRACE'):
            print(' native done', flush=True)
        fam.check(('list', cls, pkt.hex()), client, (log, nat.dump()))


def prepared(cl, nat, rng, rows, classes, case_of, texts):
    """A case after a random 7E 02 list on both sides (the click / page / answer families start here)."""
    cls = rng.choice(classes)
    case = case_of(rng)
    pkt = list_packet(rng, rows, cls, rng.choice([0, 1, 3, 10, rng.randint(0, 400)]))
    cl.new_case(case, cls)
    client_packet(cl, LIST_RECV, pkt)
    m = cl.m
    m.stub(0x00b3b703, lambda mm: cl.log.append(('request',) + tuple(v & mask for v, mask in
                                                                     zip(mm.args(3), (0xff, 0xffff, 0xffff)))) or 0, 0)
    log = []
    env = native_window(nat, case, log, texts, cls)
    nat.lib.mu_t4_receive(nat.window, ctypes.byref(env), pkt, len(pkt))
    return cls, case, env, log, pkt


def pick_index(rng, cl):
    st = cl.dump()
    cur = [g for g in st['groups'] if g['id'] == st['cur']]
    idx = [n[0] for n in cur[0]['nodes']] if cur else []
    branch = [i for i in idx if i % 10 == 0 and i not in cur[0]['roots']] if cur else []
    if branch and rng.random() < 0.2:
        return rng.choice(branch)
    avail = [n[0] for n in cur[0]['nodes'] if n[6]] if cur else []
    if avail and rng.random() < 0.6:
        return rng.choice(avail)
    return rng.choice(idx) if idx and rng.random() < 0.9 else rng.randint(-1, 80)


def run_click(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    L = nat.lib
    for n in range(cases):
        cls, case, env, log, pkt = prepared(cl, nat, rng, rows, classes, case_of, texts)
        points = rng.choice([0, 1, 5, 30, rng.randint(-3, 100)])
        cl.m.put32(cl.h + 0x7c, points)
        # the native window takes the same points without the invoke (the client field is written directly)
        nat_points = ctypes.c_int32.from_buffer(nat.window, ctypes.sizeof(ctypes.c_void_p) + 4)
        nat_points.value = points
        index = pick_index(rng, cl)
        cl.log.clear()
        log.clear()
        try:
            cl.call(CLICK, [index])
            answer = rng.choice([0, 0, 1])
            if any(e[0] == 'confirm' for e in cl.log):
                cl.call(BOX_ANSWER, [0x73, answer], ecx=vl.DUMMY + 0x40)
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        opened = L.mu_t4_click(nat.window, ctypes.byref(env), index)
        if opened:
            g, sk, ix = ctypes.c_uint8(), ctypes.c_uint16(), ctypes.c_uint16()
            if L.mu_t4_confirm(nat.window, answer, ctypes.byref(g), ctypes.byref(sk), ctypes.byref(ix)):
                log.append(('request', g.value, sk.value, ix.value))
        fam.check(('click', cls, pkt.hex(), points, index), client, (log, nat.dump()))


def answer_packet(rng, rows, cls, st):
    kind = rng.choice([1, 1, 1, 4, 7, 9, 3])
    if kind == 3:
        return bytes([0xc1, 6, 0x7e, 3]) + struct.pack('<H', rng.randint(0, 65535))
    cur = [n for g in st['groups'] for n in g['nodes']]
    # a learn answer for a node the tree lacks makes the client read a null node (0x00c26c5c): not generated
    if cur and (kind == 1 or rng.random() < 0.85):
        g = rng.choice([g for g in st['groups'] if g['nodes']])
        node = rng.choice(g['nodes'])
        group, index = g['id'], node[0]
    else:
        group, index = rng.randint(0, 5), rng.randint(0, 70)
    level = rng.choice([0, 1, 2, 10, 20, rng.randint(0, 255)])
    body = bytes([kind]) + struct.pack('<HBBHff', rng.randint(0, 500), group & 0xff, level, index & 0xffff,
                                       rng.uniform(0, 300), rng.uniform(0, 300))
    pkt = bytearray([0xc1, 0, 0x7e, 1]) + body
    pkt[1] = len(pkt)
    return bytes(pkt)


def run_answer(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    L = nat.lib
    for n in range(cases):
        cls, case, env, log, pkt = prepared(cl, nat, rng, rows, classes, case_of, texts)
        ans = answer_packet(rng, rows, cls, cl.dump())
        cl.log.clear()
        log.clear()
        try:
            client_packet(cl, {1: ANSWER_RECV, 3: POINTS_RECV}[ans[3]], ans)
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        L.mu_t4_receive(nat.window, ctypes.byref(env), ans, len(ans))
        fam.check(('answer', cls, pkt.hex(), ans.hex()), client, (log, nat.dump()))


def run_page(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    L = nat.lib
    for n in range(cases):
        cls, case, env, log, pkt = prepared(cl, nat, rng, rows, classes, case_of, texts)
        ops = []
        for _ in range(rng.randint(1, 3)):
            ops.append(rng.choice([('tab', rng.choice([0, 2, 2, 1, -1])), ('page', rng.randint(-1, 6))]))
        cl.log.clear()
        log.clear()
        try:
            for op, arg in ops:
                cl.call(CHANGE_TAB if op == 'tab' else SHOW_PAGE, [arg])
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        for op, arg in ops:
            (L.mu_t4_change_tab if op == 'tab' else L.mu_t4_show_page)(nat.window, ctypes.byref(env), arg)
        fam.check(('page', cls, pkt.hex(), ops), client, (log, nat.dump()))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    p.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    p.add_argument('--snapshot', required=True)
    p.add_argument('--cases', type=int, default=200)
    p.add_argument('--seed', type=int, default=3)
    p.add_argument('--families', default='build')
    p.add_argument('--lib')
    p.add_argument('--strict', action='store_true', help='report reads outside the snapshot (slow)')
    p.add_argument('--output')
    a = p.parse_args()
    for path, digest in ((a.text, vl.TEXT_SHA256), (a.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    snap = plain.Snapshot.load(a.snapshot)
    relocate(snap)
    texts_table = dict(plain.read_text(snap))

    def texts(i):
        v = texts_table.get(i, b'')
        return v if isinstance(v, bytes) else v.encode('latin1')
    cl = Client(Path(a.text).read_bytes(), Path(a.data).read_bytes(), snap, texts, a.strict)
    nat = Native(None, a.lib)
    classes, rows, min_columns = table_rows(snap)
    nat.load_table(classes, rows, min_columns)
    info = skill_info_of(snap)
    keys = sorted({r[1][4] for r in rows} | {r[1][21] for r in rows} | {r[1][23] for r in rows} |
                  {r[1][25] for r in rows})

    def case_of(rng):
        return Case(rng, info, keys)
    rng = random.Random(a.seed)
    report = {}
    for name in a.families.split(','):
        fam = Family(name)
        if name == 'build':
            run_build(cl, nat, rng, fam, classes, case_of, texts, a.cases)
        elif name in ('list', 'click', 'answer', 'page'):
            globals()['run_' + name](cl, nat, rng, fam, classes, rows, case_of, texts, a.cases)
        report[name] = fam.report()
    out = json.dumps(report, indent=2)
    if a.output:
        Path(a.output).write_text(out + '\n')
    print(out)
    return int(any(f['mismatches'] for f in report.values()))


if __name__ == '__main__':
    raise SystemExit(main())
