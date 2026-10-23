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
import time

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

        slots = m.__dict__.setdefault('_gfx_stubs', {})

        def at(key, fn, cleanup):      # one stub address per machine: a new one per case adds a code hook each
            if key not in slots:        # time, and Unicorn walks every code hook per instruction
                slots[key] = m._new_stub()
            m.stub(slots[key], fn, cleanup)
            return slots[key]
        m.put32(self.vt + 0x34, at('object', self._object, 0x10))
        m.put32(self.vt + 0x38, at('array', self._array, 4))
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
        self.log.append(('invoke', mm.cstr(name).decode(), [self.resolve(self.value(val))]))
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
TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
INVOKE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p)
BOX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
CONFIRM_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)
EVENT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32)
SIDE_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
POPUP_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
NAME_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)


class EnvC(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('skill_info', SKILL_FN), ('hero_has', HAS_FN), ('master_level', HAS_FN),
                ('text', TEXT_FN), ('invoke', INVOKE_FN), ('msgbox', BOX_FN), ('confirm', CONFIRM_FN),
                ('event', EVENT_FN), ('side_category', SIDE_FN), ('popup_shows_tree', POPUP_FN),
                ('skill_name', NAME_FN)]


class Native:
    def __init__(self, work, lib=None):
        path = lib or (ROOT/'reconstructed/skill'/('libclientskill.dylib' if sys.platform == 'darwin' else
                                                    'libclientskill.so'))
        if lib is None:
            subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill')], check=True)
        self.path = path
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
        L.mu_t4_table_class_of.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_table_class_of.restype = ctypes.c_void_p
        self.table = ctypes.create_string_buffer(64)
        self.window = ctypes.create_string_buffer(8192)

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
                bufs[i] = ctypes.create_string_buffer(texts(i))
            return ctypes.addressof(bufs[i])

        def invoke(u, name, args):
            a = args.decode('latin1')
            log.append(('invoke', name.decode(), json.loads(a) if a[:1] in '[{' else a))

        cbs = [SKILL_FN(skill), HAS_FN(lambda u, s: int(self.has.get(s, False))),
               HAS_FN(lambda u, s: self.master.get(s, 0)), TEXT_FN(text), INVOKE_FN(invoke),
               BOX_FN(lambda u, t: log.append(('msgbox', t.decode('latin1')))),
               CONFIRM_FN(lambda u, i, t: log.append(('confirm', i, t.decode('latin1')))),
               EVENT_FN(lambda u, w, a: log.append(('event', w.decode(), a))),
               SIDE_FN(lambda u, i, g: self.side.get((i, g), -1)), POPUP_FN(lambda u: 0),
               NAME_FN(lambda u, k: ctypes.addressof(_name_buf(k)))]
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
        self.gfxmgr = gfxmgr
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
        m.put32(vs.ATTR8, attrs)
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

        # boost::format inside the RGBA HTML line 0x0096fe90 (modelled, as validate_quest.py)
        import validate_quest as vq
        formats = {}

        def fmt_ctor(mm):
            formats[mm.uc.reg_read(cm.UC_X86_REG_ECX)] = (mm.cstr(mm.args(1)[0]), [])
            return mm.uc.reg_read(cm.UC_X86_REG_ECX)

        def fmt_uint(mm):
            formats[mm.uc.reg_read(cm.UC_X86_REG_ECX)][1].append(('i', mm.u32(mm.args(1)[0])))
            return mm.uc.reg_read(cm.UC_X86_REG_ECX)

        def fmt_string(mm):
            formats[mm.uc.reg_read(cm.UC_X86_REG_ECX)][1].append(('s', vq.std_string(mm, mm.args(1)[0])))
            return mm.uc.reg_read(cm.UC_X86_REG_ECX)

        def fmt_str(mm):
            fmt, args = formats[mm.uc.reg_read(cm.UC_X86_REG_ECX)]
            out = mm.args(1)[0]
            vst._write_std_string(mm, out, vq.typed_format(fmt, args))
            return out
        m.stub(0x0096e8c7, fmt_ctor, 4)
        m.stub(0x0096c6ea, fmt_uint, 4)
        m.stub(0x0096c702, fmt_string, 4)
        m.stub(0x0097258c, fmt_str, 4)
        m.stub(0x0096f4ae, lambda mm: formats.pop(mm.uc.reg_read(cm.UC_X86_REG_ECX), None) and 0, 0)
        texts = self.texts

        def gt_str(mm):                                  # GlobalText as a std::string (modelled, as the Master validator)
            obj = mm.alloc(0x18, define=True)
            vst._write_std_string(mm, obj, texts(s32(mm.args(1)[0])))
            return obj
        m.stub(0x011753c3, gt_str, 4)

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
        side = m.u32(h + 0xb0)
        if side:
            first, last = struct.unpack('<II', m.read(side + 4, 8))
            entries = []
            for i in range((last - first) // 4):
                e = m.u32(first + 4*i)
                c, sl, lv = m.read(e, 3)
                v, nx = struct.unpack('<ff', m.read(e + 4, 8))
                entries.append([c, sl, lv, v, nx, m.read(e + 0xc, 1)[0], s32(m.u32(e + 0x10)), s32(m.u32(e + 0x14))])
            points = [[s32(k), s32(m.u32(n + 0x14))] for k, n in vst.map_read(m, side + 0x10)]
            out['side'] = {'entries': entries, 'points': points}
        else:
            out['side'] = None
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


PROGRESS = 0   # --progress N: a stderr line every N cases


class Family:
    def __init__(self, name):
        self.name, self.cases, self.mismatches, self.examples = name, 0, 0, []
        self.coverage = {}
        self.started = self.last = time.monotonic()
        self.slowest = (0.0, None)

    def check(self, key, client, native):
        self.cases += 1
        now = time.monotonic()
        if now - self.last > self.slowest[0]:
            self.slowest = (now - self.last, repr(key)[:120])
        self.last = now
        if PROGRESS and self.cases % PROGRESS == 0:
            print(f'[{self.name}] {self.cases} cases, {now - self.started:.0f} s, {self.mismatches} mismatches, '
                  f'slowest {self.slowest[0]:.1f} s', file=sys.stderr, flush=True)
        if isinstance(client, tuple) and client and isinstance(client[0], list) and \
                all(isinstance(e, tuple) for e in client[0]):
            tags = sorted({e[1] if e[0] == 'invoke' else e[0] for e in client[0]})
            for t in tags:
                self.coverage[t] = self.coverage.get(t, 0) + 1
        a, b = norm(client), norm(native)
        if a != b:
            self.mismatches += 1
            if len(self.examples) < 3:
                diff = first_diff(a, b)
                if os.environ.get('T4_FULL'):
                    diff += ' || client=' + repr(client)[:2500] + ' || native=' + repr(native)[:2500]
                if isinstance(client, tuple) and client and client[0] == 'error':
                    diff = 'client: ' + str(client[1])
                self.examples.append({'case': repr(key)[:300], 'diff': diff})

    def report(self):
        return {'cases': self.cases, 'mismatches': self.mismatches, 'coverage': self.coverage,
                'examples': self.examples, 'seconds': round(time.monotonic() - self.started, 1),
                'slowest': {'seconds': round(self.slowest[0], 1), 'case': self.slowest[1]}}


def run_build(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
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


def map_build_signed(m, items, node_size):
    """validate_skill_tree.map_build with std::map<int>'s signed order (negative keys first)."""
    head = vs.empty_map(m, node_size)
    items = sorted(items, key=lambda kv: s32(kv[0] & 0xffffffff))

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


def map_read_signed(m, container):
    return sorted(((s32(k), n) for k, n in vst.map_read(m, container)), key=lambda kn: kn[0])


def run_table(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    """Every record through 0x010b4406 (a pointer into the snapshot's maps or the default 0x06fba950) against
    mu_t4_table_get; absent class / group / index keys too."""
    m = cl.m
    m.prepare(force=True)
    vs.common_stubs(m)
    keys = [(c, cols[1], cols[0]) for c, cols, _ in rows]
    keys += [(rng.choice(classes), rng.randint(-1, 8), rng.randint(-5, 90)) for _ in range(cases)]
    for cls, group, index in keys:
        a = m.call(GET_RECORD, [cls, group, index], ecx=TREE4)
        client = None if a == 0x06fba950 else list(struct.unpack('<27i', m.read(a, 27*4))) + [m.read(a + 0x6c, 1)[0]]
        r = nat.lib.mu_t4_table_get(nat.table, cls, group, index)
        native = None
        if r:
            raw = bytes(ctypes.string_at(ctypes.cast(r, ctypes.c_void_p), 28*4))
            native = list(struct.unpack('<27i', raw[:27*4])) + [raw[27*4]]
        fam.check(('table', cls, group, index), client, native)


def run_row(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    """The row parser 0x010b4506 into a fresh table object (vtable 0x01aba1d4, the classes the loader opened)
    against mu_t4_table_row; a failed cast takes the catch path (result 0, continue at 0x010b4957).  Rows with at
    least [+0x38] but fewer than 27 columns make the client read past the vector: not generated (the C refuses
    them)."""
    m = cl.m
    state = {}

    def throw(mm):
        ebp = state['ebp']
        mm.write(ebp - 0x15, b'\0')
        mm.uc.reg_write(cm.UC_X86_REG_EBP, ebp)
        mm.uc.reg_write(cm.UC_X86_REG_ESP, mm.u32(ebp - 0x10))
        mm.uc.reg_write(cm.UC_X86_REG_EIP, 0x010b4957)
        return cm.REDIRECT
    L = nat.lib
    for n in range(cases):
        m.prepare(force=True)
        vs.common_stubs(m)
        m.stub(vs.THROW_INT, throw, 0)
        m.stub(vs.THROW_BOOL, throw, 0)
        min_cols = rng.choice([22, 22, 27, 0, rng.randint(0, 27)])
        cls_set = sorted(set(rng.sample(range(-1, 20), rng.randint(0, 6))))
        table = m.alloc(0x48, define=True)
        m.write(table, cl.snap.read(TREE4, 0x38))
        m.put32(table + 0x38, min_cols)
        objs = []
        for c in cls_set:
            hd, k = map_build_signed(m, [], 0x14 + 0x70)
            objs.append((c, struct.pack('<iiII', c, 0, hd, k) + b'\x01\0\0\0'))
        hd, k = map_build_signed(m, objs, 0x30)
        m.write(table + 0x3c, struct.pack('<II', hd, k))
        L.mu_t4_table_free(nat.table)
        L.mu_t4_table_init(nat.table, min_cols)
        for c in cls_set:
            L.mu_t4_table_class(nat.table, c)
        results = []
        for _ in range(rng.randint(1, 8)):
            if rows and rng.random() < 0.6:
                cols = [str(v).encode() for v in rng.choice(rows)[1]]
            else:
                cols = [str(rng.choice([-1, 0, 1, rng.randint(-5, 70), rng.randint(0, 2000)])).encode()
                        for _ in range(27)]
            cut = rng.random()
            if cut < 0.15:
                cols = cols[:rng.randint(0, min(min_cols, 27))] if min_cols else cols
            elif cut < 0.25:
                cols += [b'7'] * rng.randint(1, 4)
            if rng.random() < 0.08 and cols:
                cols[rng.randrange(min(len(cols), 27))] = rng.choice([b'x', b'', b'1.5', b'99999999999', b'-'])
            cls = rng.choice(cls_set + [rng.randint(-1, 20)]) if cls_set else rng.randint(-1, 20)
            vec = vs.string_vector(m, cols)
            state['ebp'] = cm.STACK_BASE + cm.STACK_SIZE - 0x1000 - 4*(1 + 3) - 4
            try:
                r = m.call(ROW_PARSE, [n, cls, vec], ecx=table) & 0xff
            except cm.CaseError as error:
                r = ('error', str(error))
            vals = [int(c) if _is_int(c) else None for c in cols]
            if len(cols) >= min_cols and len(cols) >= 27 and any(v is None for v in vals[:27]):
                nr = 0 if L.mu_t4_table_class_of(nat.table, cls) else 0   # the catch path drops the row
                if not L.mu_t4_table_class_of(nat.table, cls):
                    nr = 0
            else:
                arr = (ctypes.c_int32 * max(1, len(cols)))(*[v or 0 for v in vals])
                nr = L.mu_t4_table_row(nat.table, cls, arr, len(cols))
            results.append((r, nr))
        client_maps = []
        for c, node in map_read_signed(m, table + 0x3c):
            groups = []
            for gk, gn in map_read_signed(m, node + 0x14 + 8):
                recs = [list(struct.unpack('<27i', m.read(rn + 0x14, 27*4))) for _, rn in map_read_signed(m, gn + 0x14 + 8)]
                groups.append([s32(gk), s32(m.u32(gn + 0x18)), recs])
            client_maps.append([s32(c), groups])
        native_maps = [[c, nat_groups(nat, c)] for c in cls_set]
        fam.check(('row', n), ([r for r, _ in results], client_maps), ([nr for _, nr in results], native_maps))


def _is_int(text):
    try:
        v = int(text.decode())
    except (ValueError, UnicodeDecodeError):
        return False
    return -2**31 <= v < 2**31 and text.strip() == text and not text.startswith(b'0x')


def nat_groups(nat, cls):
    """The C table's groups of a class: [key, rows, [records]] (file order of the 27 fields as stored)."""
    class TG(ctypes.Structure):
        _fields_ = [('key', ctypes.c_int32), ('rows', ctypes.c_int32), ('rec', ctypes.c_void_p), ('nrec', ctypes.c_int),
                    ('cap', ctypes.c_int)]

    class TC(ctypes.Structure):
        _fields_ = [('cls', ctypes.c_int32), ('groups', ctypes.POINTER(TG)), ('ngroups', ctypes.c_int),
                    ('cap', ctypes.c_int)]
    addr = nat.lib.mu_t4_table_class_of(nat.table, cls)
    c = ctypes.cast(addr, ctypes.POINTER(TC)) if addr else None
    out = []
    if not c:
        return out
    for i in range(c[0].ngroups):
        g = c[0].groups[i]
        recs = []
        for k in range(g.nrec):
            raw = ctypes.string_at(g.rec + k * 28*4, 27*4)
            recs.append(list(struct.unpack('<27i', raw)))
        out.append([g.key, g.rows, recs])
    return out


# ---- tooltip, texts, icons (tree4_ui.c) ----------------------------------------------------------------------

TOOLTIP, SET_TEXT, SET_LEVEL, ICONS = 0x00c29007, 0x00c23175, 0x00c239c2, 0x00c2bb34


class TipC4(ctypes.Structure):
    _fields_ = [('id', ctypes.c_int32), ('desc', ctypes.c_char * 256), ('next', ctypes.c_char * 256),
                ('kind', ctypes.c_int32), ('show_next', ctypes.c_uint8), ('fixed', ctypes.c_uint8)]


def snapshot_tips(snap):
    out = []
    for k, n in snap.tree(TIPS4 + 0x3c):
        r = n + 0x14
        out.append((s32(k), bytes(snap.string(r + 4))[:255], bytes(snap.string(r + 0x1c))[:255], s32(snap.u32(r + 0x34)),
                    snap.read(r + 0x38, 1)[0], snap.read(r + 0x39, 1)[0]))
    return out


class SkillWorld:
    """Skill(Kor) in the C library (validate_skill's table) for the tooltip's names and the icons."""

    def __init__(self, nat, snap):
        self.sn = vs.SkillNative(None, nat.path)
        records = vs.snapshot_records(snap)
        names = {row['index']: row['name'] for row in plain.read_skills(snap)}
        for r in records:
            r.name = bytes(names.get(r.index, b''))[:127]
        self.records = records
        self.table = self.sn.table(records)
        self.env = vs.EnvC()
        self.env.table = ctypes.pointer(self.table)
        tips = snapshot_tips(snap)
        self.tips = (TipC4 * max(1, len(tips)))(*[TipC4(*t) for t in tips])
        self.ntips = len(tips)


def run_tooltip(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    world = getattr(nat, 'world', None) or SkillWorld(nat, cl.snap)
    nat.world = world
    L = nat.lib
    L.mu_t4_tooltip.argtypes = [ctypes.c_void_p, ctypes.POINTER(vs.TipEnvC), ctypes.c_void_p, ctypes.POINTER(TipC4),
                                ctypes.c_int, ctypes.c_int32, ctypes.POINTER(vs.TipC), ctypes.POINTER(ctypes.c_uint8 * 80),
                                ctypes.POINTER(ctypes.c_int32 * 2)]
    for n in range(cases):
        cls, case, env, log, pkt = prepared(cl, nat, rng, rows, classes, case_of, texts)
        m = cl.m
        points = rng.choice([0, 1, 5, rng.randint(0, 100)])
        m.put32(cl.h + 0x7c, points)
        ctypes.c_int32.from_buffer(nat.window, ctypes.sizeof(ctypes.c_void_p) + 4).value = points
        index = pick_index(rng, cl)
        formulas = {}

        def formula(group, a, b):
            key = (group, a, b)
            if key not in formulas:
                formulas[key] = rng.choice([0.0, 2.5, float(rng.randint(0, 300)), rng.uniform(0, 99)])
            return formulas[key]
        vs.tip_machine_setup(m)
        vs.wrap_stubs(m, 1.0)
        m.stub(vs.TIP_HEADER, lambda mm: 0, 0)
        m.stub(0x00966c42, lambda mm: vl.DUMMY, 0)
        m.stub(0x0117b5eb, vst.double_stub(m, lambda mm: formula(*[s32(v) for v in mm.args(4)[1:4]])), 0)
        done, pos = [], []
        m.stub(0x00b8c631, lambda mm: pos.append([s32(v) for v in mm.args(6)[1:3]]) or 0, 0x18)
        m.stub(0x00b8d41d, lambda mm: 0, 8)
        m.stub(0x00b8d94b, lambda mm: done.append(s32(mm.args(1)[0])) or 0, 4)
        m.uc.mem_write(vs.TEXT_LIST, b'\xab' * (80 * 0xff))
        m.uc.mem_write(vs.TEXT_COLOR, struct.pack('<i', vs.SENTINEL) * 80)
        m.uc.mem_write(vs.TEXT_BOLD, struct.pack('<i', vs.SENTINEL) * 80)
        m.write(vst.HEADER_FLAGS, bytes(4 * 80))
        m.put32(0x0bdcb280, 0)
        try:
            cl.call(TOOLTIP, [index])
            if done:
                count = done[0]
                untouched = lambda b: b'' if b == b'\xab' * len(b) else b   # noqa: E731  (a line the builder skips)
                client = {'count': count,
                          'lines': [untouched(m.read(vs.TEXT_LIST + 0xff*i, 0xff).split(b'\0')[0]) for i in range(count)],
                          'colors': list(struct.unpack('<80i', m.read(vs.TEXT_COLOR, 320)))[:count],
                          'bolds': list(struct.unpack('<80i', m.read(vs.TEXT_BOLD, 320)))[:count],
                          'headers': [i for i, v in enumerate(struct.unpack('<80i', m.read(vst.HEADER_FLAGS, 320))) if v],
                          'pos': pos[0] if pos else None}
            else:
                client = None
        except cm.CaseError as error:
            client = ('error', str(error))
        tenv = vs.TipEnvC(ctypes.pointer(world.env), None, vs.TEXT_FN(lambda u, i: ctypes.addressof(_text_buf(i, texts))),
                          vs.TIP_FN(lambda u, k: None), vs.INFO_FN(lambda *a: None), vs.HAS_FN(lambda u, s: 0),
                          vs.HAS_FN(lambda u, s: 0), vs.FLOAT1_FN(lambda u, s: 0.0),
                          vs.FORMULA_FN(lambda u, g, a, b: formula(g, a, b)),
                          vs.MEASURE_FN(lambda u, txt, k: vs.measure_bytes(ctypes.string_at(txt, k))), 1.0)
        out = vs.TipC()
        heads = (ctypes.c_uint8 * 80)()
        npos = (ctypes.c_int32 * 2)()
        count = L.mu_t4_tooltip(nat.window, ctypes.byref(tenv), ctypes.byref(env), world.tips, world.ntips, index,
                                ctypes.byref(out), ctypes.byref(heads), ctypes.byref(npos))
        if count:
            native = {'count': count, 'lines': [bytes(out.lines[i]).split(b'\0')[0][:0xfe] for i in range(count)],
                      'colors': [out.color[i] if out.set[i] & 1 else vs.SENTINEL for i in range(count)],
                      'bolds': [out.bold[i] if out.set[i] & 2 else vs.SENTINEL for i in range(count)],
                      'headers': [i for i in range(80) if heads[i]], 'pos': list(npos)}
        else:
            native = None
        fam.check(('tooltip', cls, pkt.hex(), points, index), client, native)


_TEXT_BUFS = {}
_NAMES = {}
_NAME_BUFS = {}


def _name_buf(skill):
    if skill not in _NAME_BUFS:
        _NAME_BUFS[skill] = ctypes.create_string_buffer(bytes(_NAMES.get(skill, b'')))
    return _NAME_BUFS[skill]


def _text_buf(i, texts):
    if i not in _TEXT_BUFS:
        _TEXT_BUFS[i] = ctypes.create_string_buffer(texts(i))
    return _TEXT_BUFS[i]


def run_text(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    L = nat.lib
    L.mu_t4_set_text.argtypes = [ctypes.c_void_p]
    L.mu_t4_show_level.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    for n in range(cases):
        cls = rng.choice(classes)
        case = case_of(rng)
        level = rng.choice([0, 1, 400, 1600, rng.randint(0, 5000), -1])
        cl.new_case(case, cls)
        m = cl.m
        m.stub(0x00a00367, lambda mm: level & 0xffffffff, 0)
        try:
            cl.call(SET_TEXT if n % 2 == 0 else SET_LEVEL)
            client = cl.log[:]
        except cm.CaseError as error:
            client = ('error', str(error))
        log = []
        env = case.env(nat, log, texts)
        if n % 2 == 0:
            L.mu_t4_set_text(ctypes.byref(env))
        else:
            L.mu_t4_show_level(ctypes.byref(env), level)
        fam.check(('text', n % 2, level), client, log)


def side_rows(snap):
    recs, pairs = [], []
    for k, n in snap.tree(SIDE4 + 0x3c):
        b, e = snap.u32(n + 0x14), snap.u32(n + 0x18)
        for at in range(b, e, 0x58):
            recs.append(struct.unpack('<22i', snap.read(at, 0x58)))
    for k, n in snap.tree(SIDE4 + 0x44):
        b, e = snap.u32(n + 0x14), snap.u32(n + 0x18)
        for at in range(b, e, 8):
            pairs.append((s32(k),) + struct.unpack('<ii', snap.read(at, 8)))
    return recs, pairs


def native_side(nat, snap):
    if getattr(nat, 'side', None) is None:
        L = nat.lib
        L.mu_t4_side_table_init.argtypes = [ctypes.c_void_p]
        L.mu_t4_side_table_record.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int32 * 22)]
        L.mu_t4_side_table_pair.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
        nat.side = ctypes.create_string_buffer(64)
        L.mu_t4_side_table_init(nat.side)
        recs, pairs = side_rows(snap)
        for r in recs:
            L.mu_t4_side_table_record(nat.side, ctypes.byref((ctypes.c_int32 * 22)(*r)))
        for p in pairs:
            L.mu_t4_side_table_pair(nat.side, *p)
    return nat.side


def side_packet(rng, entries=None):
    n = rng.choice([0, 1, 3, 8, 8, 9]) if entries is None else entries
    body = b''
    for _ in range(n):
        # index a * 4 + b: the client's bound admits 8 (one past the vector: undefined), not generated
        a, b = rng.choice([(0, rng.randint(0, 3)), (1, rng.randint(0, 3))])
        body += struct.pack('<BBBff', a, b, rng.choice([0, 1, 5, 10, 20, rng.randint(0, 60)]),
                            rng.uniform(0, 50), rng.uniform(0, 50))
    pkt = bytearray([0xc1, 0, 0x7e, 6, 0]) + struct.pack('<I', n) + body
    pkt[1] = len(pkt) & 0xff
    return bytes(pkt)


def side_answer(rng):
    kind = rng.choice([1, 1, 1, 4, 7])
    a, b = rng.choice([(0, rng.randint(0, 3)), (1, rng.randint(0, 3))])
    pkt = bytearray([0xc1, 0x12, 0x7e, 5, kind, a]) + struct.pack('<HBBff', rng.randint(0, 300),
                                                               rng.choice([0, 1, 10, rng.randint(0, 50)]), b,
                                                               rng.uniform(0, 50), rng.uniform(0, 50))
    return bytes(pkt)


def prepared_side(cl, nat, rng, rows, classes, case_of, texts):
    """prepared() then a 7E 06 side list on both sides, more levels than 7E 02 gives (the points need them)."""
    cls, case, env, log, pkt = prepared(cl, nat, rng, rows, classes, case_of, texts)
    L = nat.lib
    L.mu_t4_window_set_side.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    L.mu_t4_window_set_side(nat.window, native_side(nat, cl.snap))
    m = cl.m
    m.stub(0x00a00fb7, lambda mm: cl.log.append(('event', 'stats', 0)) or 0, 0)
    m.stub(0x00c26ed3, lambda mm: 0, 0x14)
    sp = side_packet(rng)
    client_packet(cl, 0x012225fe, sp)
    L.mu_t4_receive(nat.window, ctypes.byref(env), sp, len(sp))
    return cls, case, env, log, pkt + b'|' + sp


def run_side(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    L = nat.lib
    for n in range(cases):
        try:
            cls, case, env, log, pkt = prepared_side(cl, nat, rng, rows, classes, case_of, texts)
        except cm.CaseError as error:
            fam.check(('side', n), ('error', str(error)), None)
            continue
        answers = [side_answer(rng) for _ in range(rng.randint(0, 2))]
        try:
            for ans in answers:
                client_packet(cl, 0x012226ca, ans)
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        for ans in answers:
            L.mu_t4_receive(nat.window, ctypes.byref(env), ans, len(ans))
        fam.check(('side', pkt.hex(), [a.hex() for a in answers]), client, (log, nat.dump()))


def run_sideclick(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    """OnBtnClickSideOption 0x00c2a5ad and the confirm answer 0x79 (request 0x00b3baf7 recorded)."""
    L = nat.lib
    L.mu_t4_side_click.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
    L.mu_t4_side_confirm.argtypes = [ctypes.c_void_p, ctypes.c_int] + [ctypes.POINTER(ctypes.c_uint8)] * 3
    for n in range(cases):
        try:
            cls, case, env, log, pkt = prepared_side(cl, nat, rng, rows, classes, case_of, texts)
        except cm.CaseError as error:
            fam.check(('sideclick', n), ('error', str(error)), None)
            continue
        m = cl.m
        points = rng.choice([0, 1, 5, 20, rng.randint(0, 200)])
        m.put32(cl.h + 0x7c, points)
        ctypes.c_int32.from_buffer(nat.window, ctypes.sizeof(ctypes.c_void_p) + 4).value = points
        index = rng.choice([0, 1, 2, 3, 4, 5, 6, 7, rng.randint(-1, 9)])
        m.stub(0x00b3baf7, lambda mm: cl.log.append(('request',) + tuple(v & 0xff for v in mm.args(3))) or 0, 0)
        m.stub(0x00c26ed3, lambda mm: cl.log.append(('event', 'statpanel', 0)) or 0, 0x14)
        cl.log.clear()
        log.clear()
        answer = rng.choice([0, 0, 1])
        try:
            cl.call(0x00c2a5ad, [index])
            if any(e[0] == 'confirm' for e in cl.log):
                cl.call(BOX_ANSWER, [0x79, answer], ecx=vl.DUMMY + 0x40)
            client = (cl.log[:], cl.dump())
        except cm.CaseError as error:
            client = ('error', str(error))
        opened = L.mu_t4_side_click(nat.window, ctypes.byref(env), index)
        if opened:
            a, b, c = ctypes.c_uint8(), ctypes.c_uint8(), ctypes.c_uint8()
            if L.mu_t4_side_confirm(nat.window, answer, ctypes.byref(a), ctypes.byref(b), ctypes.byref(c)):
                log.append(('request', a.value, b.value, c.value))
        native = [('event', 'statpanel', 0) if e[:2] == ('event', 'statpanel') else e for e in log]
        fam.check(('sideclick', cls, pkt.hex(), points, index), client, (native, nat.dump()))


def run_sidetip(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    world = getattr(nat, 'world', None) or SkillWorld(nat, cl.snap)
    nat.world = world
    L = nat.lib
    L.mu_t4_side_tooltip.argtypes = [ctypes.c_void_p, ctypes.POINTER(vs.TipEnvC), ctypes.c_void_p,
                                     ctypes.POINTER(TipC4), ctypes.c_int, ctypes.c_int32, ctypes.POINTER(vs.TipC),
                                     ctypes.POINTER(ctypes.c_uint8 * 80), ctypes.POINTER(ctypes.c_int32 * 2)]
    L.mu_t4_side_rect.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_float, ctypes.c_float]
    for n in range(cases):
        try:
            cls, case, env, log, pkt = prepared_side(cl, nat, rng, rows, classes, case_of, texts)
        except cm.CaseError as error:
            fam.check(('sidetip', n), ('error', str(error)), None)
            continue
        m = cl.m
        index = rng.choice([0, 1, 2, 3, 4, 5, 6, 7])
        x, y = f32(rng.uniform(0, 900)), f32(rng.uniform(0, 600))
        fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]   # noqa: E731
        formulas = {}

        def formula(group, a, b):
            key = (group, a, b)
            if key not in formulas:
                formulas[key] = rng.choice([0.0, 2.5, float(rng.randint(0, 300)), rng.uniform(0, 99)])
            return formulas[key]
        vs.tip_machine_setup(m)
        vs.wrap_stubs(m, 1.0)
        m.stub(vs.TIP_HEADER, lambda mm: 0, 0)
        m.stub(0x00966c42, lambda mm: vl.DUMMY, 0)
        m.stub(0x0117b5eb, vst.double_stub(m, lambda mm: formula(*[s32(v) for v in mm.args(4)[1:4]])), 0)
        done, pos = [], []
        m.stub(0x00b8c631, lambda mm: pos.append([s32(v) for v in mm.args(6)[1:3]]) or 0, 0x18)
        m.stub(0x00b8d41d, lambda mm: 0, 8)
        m.stub(0x00b8d94b, lambda mm: done.append(s32(mm.args(1)[0])) or 0, 4)
        m.uc.mem_write(vs.TEXT_LIST, b'\0' * (80 * 0xff))
        m.uc.mem_write(vs.TEXT_COLOR, struct.pack('<i', vs.SENTINEL) * 80)
        m.uc.mem_write(vs.TEXT_BOLD, struct.pack('<i', vs.SENTINEL) * 80)
        m.write(vst.HEADER_FLAGS, bytes(4 * 80))
        m.put32(0x0bdcb280, 0)
        cl.log.clear()
        log.clear()
        try:
            cl.call(0x00c2b4b3, [index, fb(x), fb(y)])
            cl.call(0x00c29a29, [index])
            if done:
                count = done[0]
                untouched = lambda b: b'' if b == b'\xab' * len(b) else b   # noqa: E731  (a line the builder skips)
                client = {'count': count,
                          'lines': [untouched(m.read(vs.TEXT_LIST + 0xff*i, 0xff).split(b'\0')[0]) for i in range(count)],
                          'colors': list(struct.unpack('<80i', m.read(vs.TEXT_COLOR, 320)))[:count],
                          'bolds': list(struct.unpack('<80i', m.read(vs.TEXT_BOLD, 320)))[:count],
                          'headers': [i for i, v in enumerate(struct.unpack('<80i', m.read(vst.HEADER_FLAGS, 320))) if v],
                          'pos': pos[0] if pos else None, 'log': cl.log[:]}
            else:
                client = {'log': cl.log[:]}
        except cm.CaseError as error:
            client = ('error', str(error))
        L.mu_t4_side_rect(nat.window, index, x, y)
        tenv = vs.TipEnvC(ctypes.pointer(world.env), None, vs.TEXT_FN(lambda u, i: ctypes.addressof(_text_buf(i, texts))),
                          vs.TIP_FN(lambda u, k: None), vs.INFO_FN(lambda *a: None), vs.HAS_FN(lambda u, s: 0),
                          vs.HAS_FN(lambda u, s: 0), vs.FLOAT1_FN(lambda u, s: 0.0),
                          vs.FORMULA_FN(lambda u, g, a, b: formula(g, a, b)),
                          vs.MEASURE_FN(lambda u, txt, k: vs.measure_bytes(ctypes.string_at(txt, k))), 1.0)
        out = vs.TipC()
        heads = (ctypes.c_uint8 * 80)()
        npos = (ctypes.c_int32 * 2)()
        count = L.mu_t4_side_tooltip(nat.window, ctypes.byref(tenv), ctypes.byref(env), world.tips, world.ntips, index,
                                     ctypes.byref(out), ctypes.byref(heads), ctypes.byref(npos))
        if count:
            native = {'count': count, 'lines': [bytes(out.lines[i]).split(b'\0')[0][:0xfe] for i in range(count)],
                      'colors': [out.color[i] if out.set[i] & 1 else vs.SENTINEL for i in range(count)],
                      'bolds': [out.bold[i] if out.set[i] & 2 else vs.SENTINEL for i in range(count)],
                      'headers': [i for i in range(80) if heads[i]], 'pos': list(npos), 'log': log[:]}
        else:
            native = {'log': log[:]}
        fam.check(('sidetip', cls, pkt.hex(), index), client, native)


DRAW_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                           ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint32)


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def run_icons(cl, nat, rng, fam, classes, rows, case_of, texts, cases):
    """0x00c2bb34 (the per-frame icon pass) after random slot rectangles (0x00c2b3ec), side positions/size
    (0x00c2b4b3 / 0x00c2b580) and window origin/scale/ratios; RenderBitmap 0x0184e01a recorded."""
    world = getattr(nat, 'world', None) or SkillWorld(nat, cl.snap)
    nat.world = world
    L = nat.lib
    L.mu_t4_slot_rect.argtypes = [ctypes.c_void_p, ctypes.c_int32] + [ctypes.c_float] * 4
    L.mu_t4_side_rect.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_float, ctypes.c_float]
    L.mu_t4_side_size.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_float]
    L.mu_t4_icons.argtypes = [ctypes.c_void_p, ctypes.c_void_p] + [ctypes.c_float] * 5 + [DRAW_FN, ctypes.c_void_p]
    for n in range(cases):
        try:
            cls, case, env, log, pkt = prepared_side(cl, nat, rng, rows, classes, case_of, texts)
        except cm.CaseError as error:
            fam.check(('icons', n), ('error', str(error)), None)
            continue
        m = cl.m
        st = cl.dump()
        indices = sorted({nd[0] for g in st['groups'] for nd in g['nodes']})
        rects = {i: [f32(rng.uniform(0, 600)), f32(rng.uniform(0, 500)), f32(rng.choice([36.0, rng.uniform(1, 60)])),
                     f32(rng.choice([36.0, rng.uniform(1, 60)]))] for i in indices if rng.random() < 0.9}
        side = {i: [f32(rng.uniform(0, 800)), f32(rng.uniform(0, 600))] for i in range(8) if rng.random() < 0.9}
        size = [f32(rng.choice([34.0, rng.uniform(5, 50)])), f32(rng.choice([34.0, rng.uniform(5, 50)]))]
        x0, y0 = f32(rng.uniform(0, 300)), f32(rng.uniform(0, 200))
        scale, rx, ry = f32(rng.choice([1.0, 0.9, rng.uniform(0.5, 1.5)])), f32(rng.uniform(0.3, 2)), f32(rng.uniform(0.3, 2))
        fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]   # noqa: E731
        draws = []
        try:
            for i, r in rects.items():
                cl.call(0x00c2b3ec, [i] + [fb(v) for v in r])
            for i, p in side.items():
                cl.call(0x00c2b4b3, [i, fb(p[0]), fb(p[1])])
            cl.call(0x00c2b580, [fb(size[0]), fb(size[1])])
            m.write(cl.h + 0x58, struct.pack('<f', scale))
            gm = m.u32(m.u32(0) if False else 0) if False else None
            m.stub(0x00aae509, vst.double_stub(m, lambda mm: x0), 0)
            m.stub(0x00aae601, vst.double_stub(m, lambda mm: y0), 0)
            gfx = cl.gfxmgr
            m.write(gfx + 0x2cc, struct.pack('<ff', rx, ry))

            def render(mm):
                w = mm.args(10)
                fl = [struct.unpack('<f', struct.pack('<I', v))[0] for v in w[1:9]]
                draws.append([s32(w[0])] + fl + [w[9]])
                return 0
            m.stub(0x0184e01a, render, 0)
            cl.call(ICONS)
            client = draws
        except cm.CaseError as error:
            client = ('error', str(error))
        for i, r in rects.items():
            L.mu_t4_slot_rect(nat.window, i, *r)
        for i, p in side.items():
            L.mu_t4_side_rect(nat.window, i, *p)
        L.mu_t4_side_size(nat.window, *size)
        native = []
        cb = DRAW_FN(lambda u, b, *a: native.append([b] + list(a[:8]) + [a[8]]))
        L.mu_t4_icons(nat.window, ctypes.byref(world.env), x0, y0, scale, rx, ry, cb, None)
        fam.check(('icons', cls, pkt.hex()), client, native)


MUTANTS = {21: 'build', 22: 'build', 23: 'list', 24: 'click', 25: 'page', 26: 'answer', 27: 'page', 28: 'tooltip', 29: 'side', 30: 'icons'}
FAMILIES = ('table', 'row', 'build', 'list', 'page', 'click', 'answer', 'tooltip', 'text', 'side', 'sideclick',
            'sidetip', 'icons')


def run_family(name, cl, nat, rng, classes, rows, case_of, texts, cases):
    fam = Family(name)
    globals()['run_' + name](cl, nat, rng, fam, classes, rows, case_of, texts, cases)
    return fam.report()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    p.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    p.add_argument('--snapshot', required=True)
    p.add_argument('--cases', type=int, default=200)
    p.add_argument('--seed', type=int, default=3)
    p.add_argument('--families', default=','.join(FAMILIES))
    p.add_argument('--mutations', action='store_true', help='also run the planted mistakes 21..30')
    p.add_argument('--lib')
    p.add_argument('--strict', action='store_true', help='report reads outside the snapshot (slow)')
    p.add_argument('--output')
    p.add_argument('--progress', type=int, default=25, help='stderr progress line every N cases (0: off)')
    p.add_argument('--mutants-only', action='store_true', help='skip the clean families, run only the mutants')
    a = p.parse_args()
    global PROGRESS
    PROGRESS = a.progress
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
    _NAMES.update({row['index']: row['name'] for row in plain.read_skills(snap)})
    keys = sorted({r[1][4] for r in rows} | {r[1][21] for r in rows} | {r[1][23] for r in rows} |
                  {r[1][25] for r in rows})

    def case_of(rng):
        return Case(rng, info, keys)
    rng = random.Random(a.seed)
    report = {}
    names = a.families.split(',')
    for name in ([] if a.mutants_only else names):
        report[name] = run_family(name, cl, nat, rng, classes, rows, case_of, texts, a.cases)
        nat.load_table(classes, rows, min_columns)          # the row family leaves synthetic classes
    if a.mutations:
        ext = 'dylib' if sys.platform == 'darwin' else 'so'
        caught = {}
        for number, family in MUTANTS.items():
            if family not in names:
                continue
            subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill'), f'mutant{number}.{ext}'], check=True)
            mut = Native(None, ROOT/f'reconstructed/skill/mutant{number}.{ext}')
            mut.load_table(classes, rows, min_columns)
            r = run_family(family, cl, mut, random.Random(a.seed + number), classes, rows, case_of, texts,
                           min(a.cases, 120))
            del mut
            caught[f'mutant{number}:{family}'] = r['mismatches'] > 0
        report['mutations'] = caught
    out = json.dumps(report, indent=2)
    if a.output:
        Path(a.output).write_text(out + '\n')
    print(out)
    bad = any(f['mismatches'] for k, f in report.items() if k != 'mutations')
    return int(bad or not all(report.get('mutations', {}).values()))


if __name__ == '__main__':
    raise SystemExit(main())
