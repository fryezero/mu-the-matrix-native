#!/usr/bin/env python3
"""Compare the NPC interaction reconstruction with the client (NATIVE-NPC-001).

The client routines run in Unicorn over the pinned restored text and second
image section (scripts/client_ui_machine.py).  The authored C is
reconstructed/npc (built as libnpc, called through ctypes).

Sections:

* talk: ReceiveTalk 0x01280659(packet, encrypted), the handler of the
  server's talk answer, for every result byte 0..255 and random case state
  (encrypted or not, EventMapEntranceUI visible, null manager slots, hero
  tile, cursor lock, mouse and screen values, the packet bytes the cases
  read).  Every call the routine makes leaves through a stub that records
  (callee, self, arguments); GFx windows are fake objects in the manager's
  slots whose vtables are stubs.  The C's mu_npc_talk_result emits the same
  list; they must be equal, including the two memory writes and EAX.
* axis, segment: the projection test 0x01850d88 and the segment/OBB test
  0x018500bf against mu_pick_axis_overlap / mu_pick_segment_obb.
* pick: the character pick 0x016b47bf(kind) on synthetic scenes of up to
  400 characters (most of them one shared dead character): the returned
  index, every candidate's o+5 byte, o+0xec light and in-place OBB
  adjustments against mu_npc_pick.
* box: executes the box section of the character create 0x0137d8a1
  (0x0137dfe1..0x0137ed7e: default box, then the switch on the model type)
  for every model index 0..0x3af6 and compares o+0x128/o+0x134 with
  mu_character_box.  --emit-box writes reconstructed/npc/character_box_table.h.

Modelled, not client code: the GFx manager getter 0x00ac3bf7 and the
NewUI getter 0x00f2bb92 (fixed fake objects), the called window methods,
SND_Play, the packet builder, SetCursorPos (recorded), the character getters
0x0095f6db/0x009a13f4 and the buff test 0x01295ade (case values).  Anything
else outside the allowlisted bodies stops a case.

  python scripts/validate_npc.py [--cases N] [--mutations] [--emit-box]
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
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402

DEFAULT_TEXT = pins.TEXT.default()
DEFAULT_DATA = pins.DATA.default()
TEXT_SHA256 = pins.TEXT.sha256
DATA_SHA256 = pins.DATA.sha256
LIB_DIR = ROOT/'reconstructed/npc'

RECEIVE_TALK = 0x01280659
CHKSTK = 0x0191c5a0
MANAGER_GET, NEWUI_GET = 0x00ac3bf7, 0x00f2bb92
SET_CURSOR_SLOT = 0x01a7c870
SELF = {'NONE': 0, 'MANAGER': 0xffff, 'NEWUI': 0xfffe, 'DIALOGUE': 0xfffd, '6FC9EB0': 0xfffc, 'SHOP_FLAG': 0xfffb,
        'NEWUI_WINDOW': 0xfffa, 'PACKET': 0xfff9, 'LOCAL': 0xfff8}
VTABLE = 0x80000000
WRITE = 0x90000000
MIX_TYPE = 0x01ec8d78
# callee -> (argument words, stack bytes the callee pops)
TALK_CALLEES = {
    0x00aae6f9: (0, 0), 0x00ac9c74: (0, 0), 0x00f2b53d: (0, 0), 0x00f2abcd: (1, 4), 0x00f2c102: (0, 0),
    0x00ef00b4: (1, 4), 0x00b04bd2: (1, 4), 0x00b04ded: (5, 20), 0x011e04c7: (1, 4), 0x00bd0006: (1, 4),
    0x00bd72a3: (0, 0), 0x00bd7408: (0, 0), 0x00bd709c: (0, 0), 0x00baeb44: (0, 0), 0x00b54793: (0, 0),
    0x00aae767: (0, 0), 0x00fdc96c: (1, 4), 0x00be842c: (0, 0), 0x0121405e: (1, 0), 0x01287617: (0, 0),
    0x00aabe9b: (0, 0), 0x00bf17c2: (1, 4), 0x00a6ac96: (3, 0),
    0x00d51baf: (2, 8), 0x00d51c9b: (3, 12), 0x00d51d4f: (2, 8)}
PACKET_CTOR, PACKET_DTOR = 0x00d51b91, 0x00d51ba6
TALK_SLOTS = (0x0a8, 0x0ac, 0x0b0, 0x0b4, 0x0e0, 0x0ec, 0x0f0, 0x0f4, 0x100, 0x164, 0x1ac, 0x1d4, 0x1fc, 0x204,
              0x208, 0x20c, 0x260, 0x264, 0x270, 0x2ac)

PICK = 0x016b47bf
PICK_BODIES = (0x016b47bf, 0x018500bf, 0x01850d88, 0x00cfc922, 0x00cfc94a, 0x00cfeff3, 0x00ce3931, 0x009f410c,
               0x00a5fbf0, 0x0095eda9, 0x0184f93f, 0x0184f927)
CHAR_INDEX, CHAR_GET, HAS_BUFF = 0x0095f6db, 0x009a13f4, 0x01295ade
SCENE, WORLD, HERO, MAP, MAP_VALUE = 0x01d1df70, 0x01cf15fc, 0x0a39d754, 0x0b735420, 0x0b437c10
RAY_START, RAY_END, CAMERA = 0x0bdc5984, 0x0bdc5990, 0x0bdc5ab4
OBJ = 0x3254
BOX_BEGIN, BOX_END = 0x0137dfe1, 0x0137ed7e
BOX_TYPES = 0x3af7


def sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


# --------------------------------------------------------------------------- native library

class TalkInput(ctypes.Structure):
    _fields_ = [('packet', ctypes.POINTER(ctypes.c_uint8)), ('length', ctypes.c_size_t), ('encrypted', ctypes.c_int),
                ('entrance_visible', ctypes.c_int), ('has_b0', ctypes.c_int), ('has_b4', ctypes.c_int),
                ('has_ac', ctypes.c_int), ('hero_x', ctypes.c_int32), ('hero_y', ctypes.c_int32),
                ('cursor_lock', ctypes.c_int32), ('mouse_x', ctypes.c_int32), ('mouse_y', ctypes.c_int32),
                ('screen_w', ctypes.c_int32), ('screen_h', ctypes.c_int32)]


class TalkEvent(ctypes.Structure):
    _fields_ = [('callee', ctypes.c_uint32), ('self', ctypes.c_uint32), ('n', ctypes.c_int32),
                ('args', ctypes.c_uint32*6)]


class TalkOutput(ctypes.Structure):
    _fields_ = [('events', TalkEvent*24), ('count', ctypes.c_int32), ('returned', ctypes.c_int32)]


class Obb(ctypes.Structure):
    _fields_ = [('v', ctypes.c_float*12)]


class PickCharacter(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('alpha', ctypes.c_float),
                ('kind', ctypes.c_uint8), ('type', ctypes.c_int32), ('highlight', ctypes.c_uint16),
                ('c1f', ctypes.c_uint8), ('dead', ctypes.c_uint8), ('c10', ctypes.c_uint8), ('buff_1b', ctypes.c_uint8),
                ('is_hero', ctypes.c_uint8), ('position', ctypes.c_float*3), ('obb', Obb), ('marked', ctypes.c_uint8),
                ('light', ctypes.c_float*3), ('light_set', ctypes.c_uint8)]


class PickScene(ctypes.Structure):
    _fields_ = [('scene', ctypes.c_int32), ('world', ctypes.c_int32), ('ray_start', ctypes.c_float*3),
                ('ray_end', ctypes.c_float*3), ('camera', ctypes.c_float*3), ('map', ctypes.POINTER(ctypes.c_uint8)),
                ('map_value', ctypes.c_int32)]


def load_library(extra_flags=()):
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    tag = ''.join(f[2:].lower() for f in extra_flags) or 'plain'
    out = LIB_DIR/f'libnpc_validate_{tag}.{suffix}'   # one file per variant: dlopen caches by path
    sources = [LIB_DIR/'npc_talk.c', LIB_DIR/'npc_pick.c']
    cmd = ['cc', '-std=c11', '-O2', '-ffp-contract=off', '-fno-fast-math', '-fPIC', '-shared', *extra_flags,
           *map(str, sources), '-o', str(out)]
    subprocess.run(cmd, check=True)
    lib = ctypes.CDLL(str(out))
    lib.mu_npc_talk_result.argtypes = [ctypes.POINTER(TalkInput), ctypes.POINTER(TalkOutput)]
    lib.mu_pick_axis_overlap.argtypes = [ctypes.POINTER(ctypes.c_float)]*3 + [ctypes.POINTER(Obb)]
    lib.mu_pick_segment_obb.argtypes = [ctypes.POINTER(ctypes.c_float)]*2 + [ctypes.POINTER(Obb)]
    lib.mu_npc_pick.argtypes = [ctypes.POINTER(PickCharacter), ctypes.c_int32, ctypes.c_uint8, ctypes.POINTER(PickScene)]
    lib.mu_npc_pick.restype = ctypes.c_int32
    lib.mu_character_box.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
    return lib


# --------------------------------------------------------------------------- talk

class TalkMachine:
    def __init__(self, text, data):
        cm.SLOTS[SET_CURSOR_SLOT] = ('SetCursorPos', 'ii')
        self.m = m = cm.Machine(text, data)
        self.text = text
        m.allow((RECEIVE_TALK, cm.function_extent(text, RECEIVE_TALK)), (CHKSTK, cm.function_extent(text, CHKSTK)))
        self.manager = 0x20000000
        self.newui = 0x20010000
        self.newui_window = 0x20020000
        self.obj_6fc9eb0 = 0x20030000
        self.shop_flag = 0x20040000
        m.uc.mem_map(0x20000000, 0x00100000)
        self.tags = {self.manager: SELF['MANAGER'], self.newui: SELF['NEWUI'], self.newui_window: SELF['NEWUI_WINDOW'],
                     self.obj_6fc9eb0: SELF['6FC9EB0'], self.shop_flag: SELF['SHOP_FLAG'], 0x01ec9858: SELF['DIALOGUE']}
        self.windows = {}
        for k, slot in enumerate(TALK_SLOTS):
            obj = 0x20050000 + k*0x100
            self.windows[slot] = obj
            self.tags[obj] = slot
        self.vtable = 0x20060000
        self.events = []
        for slot in range(0, 0x100, 4):   # every vtable entry: a recording stub
            stub = cm.STUB_BASE + 0x80000 + slot*4
            m.uc.mem_write(stub, b'\xc3')
            m.stub(stub, self._vt(slot), 0)
        for callee, (words, cleanup) in TALK_CALLEES.items():
            m.stub(callee, self._rec(callee, words), cleanup)
        m.stub(MANAGER_GET, lambda mm: self.manager, 0)
        m.stub(NEWUI_GET, lambda mm: self.newui, 0)
        m.stub(PACKET_CTOR, lambda mm: mm.uc.reg_read(cm.UC_X86_REG_ECX), 0)
        m.stub(PACKET_DTOR, lambda mm: 0, 0)
        m.handlers = {}
        m.uc.hook_add(cm.UC_HOOK_MEM_WRITE, self._write_hook, begin=MIX_TYPE, end=MIX_TYPE + 3)
        m.uc.hook_add(cm.UC_HOOK_MEM_WRITE, self._write_hook, begin=self.shop_flag, end=self.shop_flag + 0xff)

    def _tag(self, ecx):
        if ecx in self.tags:
            return self.tags[ecx]
        if cm.STACK_BASE <= ecx < cm.STACK_BASE + cm.STACK_SIZE:
            return SELF['LOCAL'] if self._local else SELF['PACKET']
        return ecx

    def _vt(self, slot):
        def handler(m):
            self.events.append((VTABLE | slot, self._tag(m.uc.reg_read(cm.UC_X86_REG_ECX)), ()))
            return 0
        return handler

    def _rec(self, callee, words):
        def handler(m):
            ecx = m.uc.reg_read(cm.UC_X86_REG_ECX)
            args = m.args(words)
            self._local = callee in (0x0121405e, 0x01287617)
            if callee == 0x00d51c9b:      # AddData(pointer, 1, 1): record the byte
                args = [m.read(args[0], 1)[0]] + args[1:]
            elif callee == 0x0121405e:
                args = [SELF['LOCAL']]
            self_tag = SELF['NONE'] if callee in (0x00a6ac96, 0x0121405e, 0x00aabe9b) else self._tag(ecx)
            self.events.append((callee, self_tag, tuple(args)))
            self._local = False
            if callee == 0x00aae6f9:
                return self.case['entrance_visible']
            if callee == 0x00f2c102:
                return self.newui_window
            if callee == 0x00aabe9b:
                return self.shop_flag
            return 0
        return handler

    def _write_hook(self, uc, access, address, size, value, user):
        if address == MIX_TYPE:
            self.events.append((WRITE, SELF['NONE'], (MIX_TYPE, value & 0xffffffff)))
        elif self.shop_flag <= address < self.shop_flag + 0x100:
            self.events.append((WRITE, SELF['NONE'], (SELF['SHOP_FLAG'], value & 0xff)))

    def run(self, case):
        m = self.m
        m.reset()
        self.case = case
        self.events = []
        self._local = False
        m.handlers = {'SetCursorPos': self._cursor}
        uc = m.uc
        # manager slots: fake windows (zero for the null cases)
        uc.mem_write(self.manager, b'\0'*0x400)
        for slot, obj in self.windows.items():
            present = case['has'].get(slot, 1)
            uc.mem_write(self.manager + slot, struct.pack('<I', obj if present else 0))
            uc.mem_write(obj, struct.pack('<I', self.vtable))
        for slot in range(0, 0x100, 4):
            uc.mem_write(self.vtable + slot, struct.pack('<I', cm.STUB_BASE + 0x80000 + slot*4))
        packet = m.alloc(16, define=True)
        m.write(packet, bytes(case['packet']))
        hero = m.alloc(0x200, define=True)
        m.write(hero + 0x180, struct.pack('<ii', case['hero_x'], case['hero_y']))
        m.put32(HERO, hero)
        m.put32(0x01cf0fc0, case['cursor_lock'])
        m.put32(0x0bdc5ad8, case['mouse_x'])
        m.put32(0x0bdc5adc, case['mouse_y'])
        m.put32(0x01cf1624, case['screen_w'])
        m.put32(0x01cf1628, case['screen_h'])
        m.put32(0x06fc9eb0, self.obj_6fc9eb0)
        m.put32(MIX_TYPE, 0x5a5a5a5a)
        self.events = []
        eax = m.call(RECEIVE_TALK, (packet, case['encrypted']))
        return {'events': [(c, s, tuple(a)) for c, s, a in self.events], 'returned': eax}

    def _cursor(self, m, words):
        self.events.append((SET_CURSOR_SLOT, SELF['NONE'], tuple(words)))
        return 1


def native_talk(lib, case):
    buf = (ctypes.c_uint8*16)(*case['packet'])
    has = case['has']
    inp = TalkInput(ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8)), 16, case['encrypted'], case['entrance_visible'],
                    has.get(0x0b0, 1), has.get(0x0b4, 1), has.get(0x0ac, 1), case['hero_x'], case['hero_y'],
                    case['cursor_lock'], case['mouse_x'], case['mouse_y'], case['screen_w'], case['screen_h'])
    out = TalkOutput()
    lib.mu_npc_talk_result(ctypes.byref(inp), ctypes.byref(out))
    events = []
    for k in range(out.count):
        e = out.events[k]
        events.append((e.callee, e.self, tuple(e.args[i] for i in range(e.n))))
    return {'events': events, 'returned': out.returned}


def talk_cases(rng, count):
    cases = []
    for result in range(256):
        for k in range(count):
            packet = [0xc1, 16, 0xdf, result] + [rng.randrange(256) for _ in range(12)]
            if k == 0:
                packet[0xc] = 0
            hero = (rng.randrange(0x30, 0x50), rng.randrange(0xe0, 0x100)) if k % 2 else (rng.randrange(256),
                                                                                         rng.randrange(256))
            has = {}
            if k % 3 == 2:
                has = {0x0b0: 0, 0x0b4: 0, 0x0ac: 0}
            cases.append({'packet': packet, 'encrypted': 0 if (k == 1 and result % 16 == 0) else 1,
                          'entrance_visible': int(k % 4 == 3), 'has': has, 'hero_x': hero[0], 'hero_y': hero[1],
                          'cursor_lock': int(k % 5 == 4), 'mouse_x': rng.randrange(-200, 2000),
                          'mouse_y': rng.randrange(-200, 1500), 'screen_w': rng.choice((640, 800, 1024, 1280, 1722)),
                          'screen_h': rng.choice((480, 600, 768, 800, 1048))})
    return cases


def run_talk(text, data, lib, count, rng):
    tm = TalkMachine(text, data)
    mismatches, results = [], {}
    cases = talk_cases(rng, count)
    for case in cases:
        client = tm.run(case)
        native = native_talk(lib, case)
        if client != native:
            mismatches.append({'case': case, 'client': client, 'native': native})
        results.setdefault(case['packet'][3], set()).add(tuple(e[0] for e in client['events']))
    return {'cases': len(cases), 'mismatches': len(mismatches), 'first': mismatches[:2],
            'distinct_paths': sum(len(v) for v in results.values())}


# --------------------------------------------------------------------------- axis / segment

def rand_vec(rng, scale=500.0):
    kind = rng.random()
    if kind < 0.05:
        return [0.0, 0.0, 0.0]
    return [f32(rng.uniform(-scale, scale)) for _ in range(3)]


def rand_obb(rng):
    start = [f32(rng.uniform(-300, 300)) for _ in range(3)]
    if rng.random() < 0.6:   # axis-aligned like the transform builds
        ext = [f32(rng.uniform(0, 300)) for _ in range(3)]
        axes = [[ext[0], 0.0, 0.0], [0.0, ext[1], 0.0], [0.0, 0.0, ext[2]]]
    else:
        axes = [rand_vec(rng, 300) for _ in range(3)]
    return start + axes[0] + axes[1] + axes[2]


class PickMachine:
    def __init__(self, text, data):
        self.m = m = cm.Machine(text, data)
        for body in PICK_BODIES:
            m.allow((body, cm.function_extent(text, body)))
        self.chars = {}
        m.stub(CHAR_INDEX, lambda mm: mm.args(1)[0], 0)
        m.stub(CHAR_GET, lambda mm: self.chars.get(mm.uc.reg_read(cm.UC_X86_REG_ECX), self.dead), 0)
        m.stub(HAS_BUFF, self._buff, 4)
        self.buff = {}

    def _buff(self, m):
        ecx = m.uc.reg_read(cm.UC_X86_REG_ECX)
        return self.buff.get(ecx - 0x358 - OBJ, 0)

    def axis(self, axis, p1, p2, obb):
        m = self.m
        m.reset()
        a = m.alloc(12, define=True)
        b = m.alloc(12, define=True)
        c = m.alloc(12, define=True)
        m.write(a, struct.pack('<3f', *axis))
        m.write(b, struct.pack('<3f', *p1))
        m.write(c, struct.pack('<3f', *p2))
        words = list(struct.unpack('<12I', struct.pack('<12f', *obb)))
        return m.call(0x01850d88, (a, b, c, *words)) & 0xff

    def segment(self, p1, p2, obb):
        m = self.m
        m.reset()
        b = m.alloc(12, define=True)
        c = m.alloc(12, define=True)
        m.write(b, struct.pack('<3f', *p1))
        m.write(c, struct.pack('<3f', *p2))
        words = list(struct.unpack('<12I', struct.pack('<12f', *obb)))
        return m.call(0x018500bf, (b, c, *words)) & 0xff

    def pick(self, scene, chars, kind):
        m = self.m
        m.reset()
        self.chars, self.buff = {}, {}
        self.dead = m.alloc(OBJ + 0x400, define=False)
        m.write(self.dead + OBJ, b'\0'*0x400)
        m.write(self.dead + OBJ + 0x3b, bytes([0xff]))
        m.write(self.dead, b'\0'*0x200)
        addresses = []
        for i, c in enumerate(chars):
            base = m.alloc(OBJ + 0x400, define=False)
            m.write(base, b'\0'*0x200)
            m.write(base + OBJ, b'\0'*0x400)
            o = base + OBJ
            m.write(base + 0x10, bytes([c['c10']]))
            m.write(base + 0x1f, bytes([c['c1f']]))
            m.write(base + 0x23, bytes([c['dead']]))
            m.write(base + 0x144, struct.pack('<H', c['highlight']))
            m.write(o + 0, bytes([c['live']]))
            m.write(o + 0xb, bytes([c['visible']]))
            m.write(o + 0x3b, bytes([c['kind']]))
            m.write(o + 0x5c, struct.pack('<i', c['type']))
            m.write(o + 0xdc, struct.pack('<f', c['alpha']))
            m.write(o + 0xec, struct.pack('<3f', 7.0, 7.0, 7.0))
            m.write(o + 0x158, struct.pack('<3f', *c['position']))
            m.write(o + 0x31c, struct.pack('<12f', *c['obb']))
            self.chars[c['index']] = base
            self.buff[base] = c['buff']
            addresses.append(base)
        hero = next((addresses[i] for i, c in enumerate(chars) if c['hero']), self.dead + 0x100000)
        m.put32(HERO, hero)
        m.put32(SCENE, scene['scene'])
        m.put32(WORLD, scene['world'])
        m.write(RAY_START, struct.pack('<3f', *scene['ray_start']))
        m.write(RAY_END, struct.pack('<3f', *scene['ray_end']))
        m.write(CAMERA, struct.pack('<3f', *scene['camera']))
        m.put32(MAP_VALUE, scene['map_value'])
        if scene['map'] is not None:
            m.write(MAP, scene['map'])
        index = m.call(PICK, (kind,))
        state = []
        for c, base in zip(chars, addresses):
            o = base + OBJ
            state.append({'marked': m.read(o + 5, 1)[0], 'light': list(struct.unpack('<3f', m.read(o + 0xec, 12))),
                          'obb': list(struct.unpack('<12f', m.read(o + 0x31c, 48)))})
        return (index if index < 0x80000000 else index - 0x100000000), state


def native_pick(lib, scene, chars, kind):
    arr = (PickCharacter*400)()
    count = 0
    for c in chars:
        p = arr[c['index']]
        p.live, p.visible, p.alpha, p.kind, p.type = c['live'], c['visible'], c['alpha'], c['kind'], c['type']
        p.highlight, p.c1f, p.dead, p.c10, p.buff_1b, p.is_hero = (c['highlight'], c['c1f'], c['dead'], c['c10'],
                                                                   c['buff'], c['hero'])
        p.position = (ctypes.c_float*3)(*c['position'])
        p.obb.v = (ctypes.c_float*12)(*c['obb'])
        count = max(count, c['index'] + 1)
    for i in range(400):            # the shared dead character everywhere else
        if not any(c['index'] == i for c in chars):
            arr[i].kind = 0xff
    mp = None
    if scene['map'] is not None:
        mp = (ctypes.c_uint8*65536).from_buffer_copy(scene['map'])
    sc = PickScene(scene['scene'], scene['world'], (ctypes.c_float*3)(*scene['ray_start']),
                   (ctypes.c_float*3)(*scene['ray_end']), (ctypes.c_float*3)(*scene['camera']),
                   ctypes.cast(mp, ctypes.POINTER(ctypes.c_uint8)) if mp is not None else None, scene['map_value'])
    index = lib.mu_npc_pick(arr, 400, kind, ctypes.byref(sc))
    state = []
    for c in chars:
        p = arr[c['index']]
        light = list(p.light) if p.light_set else [f32(7.0)]*3
        state.append({'marked': p.marked, 'light': [f32(v) for v in light], 'obb': [f32(v) for v in p.obb.v]})
    return index, state


def pick_case(rng, k):
    world = rng.choice((0, 2, 0x5d, 1, 4))
    n = rng.randrange(1, 12)
    indices = rng.sample(range(400), n)
    target = [f32(rng.uniform(10000, 20000)), f32(rng.uniform(10000, 20000)), f32(rng.uniform(0, 300))]
    camera = [f32(target[0] + rng.uniform(-900, 900)), f32(target[1] + rng.uniform(-900, 900)), f32(rng.uniform(800, 1500))]
    end = [f32(target[0] + (target[0]-camera[0])*0.5), f32(target[1] + (target[1]-camera[1])*0.5),
           f32(target[2] - (camera[2] - target[2])*0.5)]
    chars = []
    for j, idx in enumerate(indices):
        pos = [f32(target[0] + rng.uniform(-250, 250)), f32(target[1] + rng.uniform(-250, 250)), f32(rng.uniform(0, 200))]
        typ = rng.choice((0xa40, 0x81b, 0x81c, 0xa3e, 0xa64, 0x9fe, 0xa0a, 0x7a5, 0xa91))
        mn, mx = [-60.0, -60.0, 0.0], [50.0, 50.0, 150.0]
        if rng.random() < 0.3:
            obb = rand_obb(rng)
            obb[0:3] = [f32(pos[i] + obb[i]) for i in range(3)]
        else:
            obb = [f32(pos[i] + mn[i]) for i in range(3)] + [f32(mx[0]-mn[0]), 0.0, 0.0, 0.0, f32(mx[1]-mn[1]), 0.0,
                                                             0.0, 0.0, f32(mx[2]-mn[2])]
        chars.append({'index': idx, 'live': int(rng.random() > 0.05), 'visible': int(rng.random() > 0.05),
                      'alpha': rng.choice((1.0, 0.5, 0.0, -0.1)) if rng.random() < 0.2 else 1.0,
                      'kind': rng.choice((4, 4, 4, 2, 1, 0x20, 0, 6)), 'type': typ,
                      'highlight': rng.choice((0, 1, 2, 3, 4, 5, 0x100)), 'c1f': rng.randrange(0, 9),
                      'dead': int(rng.random() < 0.1), 'c10': int(rng.random() > 0.1), 'buff': int(rng.random() < 0.1),
                      'hero': int(j == 0 and rng.random() < 0.3), 'position': pos, 'obb': obb})
    if k % 3 == 0:   # a stack of candidates on the segment at one ground point, different heights
        for j, c in enumerate(chars):
            h = f32(rng.uniform(0, 600))
            c['position'] = [target[0], target[1], h]
            c['obb'] = [f32(target[0] - 300), f32(target[1] - 300), f32(-400.0), 600.0, 0.0, 0.0, 0.0, 600.0, 0.0,
                        0.0, 0.0, 1600.0]
            c.update(live=1, visible=1, alpha=1.0, dead=0, c10=1, buff=0, hero=0, kind=4, type=0x9fe)
    mp = None
    if world in (0, 2):
        mp = bytes(rng.choice((0, 3, 4, 3, 4, 1)) for _ in range(65536))
    scene = {'scene': rng.choice((6, 6, 5)), 'world': world, 'ray_start': camera, 'ray_end': end, 'camera': camera,
             'map': mp, 'map_value': rng.choice((0, 3, 4, 0xb))}
    return scene, chars, rng.choice((4, 0x22, 1, 6))


# --------------------------------------------------------------------------- box

def run_box(text, data):
    m = cm.Machine(text, data)
    m.allow((BOX_BEGIN, BOX_END + 1), (0x00cfc922, 0x00cfc934))
    boxes = {}
    stack = cm.STACK_BASE + cm.STACK_SIZE - 0x2000
    obj = m.alloc(0x400, define=True)
    for t in range(BOX_TYPES):
        m.write(obj + 0x128, b'\xcc'*24)
        ebp = stack
        m.write(ebp - 0x40, b'\0'*0x40)
        m.write(ebp - 4, struct.pack('<I', obj))
        m.write(ebp + 0xc, struct.pack('<I', t))
        m.uc.reg_write(cm.UC_X86_REG_EBP, ebp)
        m.uc.reg_write(cm.UC_X86_REG_ESP, ebp - 0x80)
        m.uc.emu_start(BOX_BEGIN, BOX_END, count=100000)
        if m.errors:
            raise SystemExit(f'box section, type {t:#x}: {m.errors[:2]}')
        mn = struct.unpack('<3f', m.read(obj + 0x128, 12))
        mx = struct.unpack('<3f', m.read(obj + 0x134, 12))
        boxes[t] = (mn, mx)
    return boxes


def emit_box(boxes, path):
    default = ((-60.0, -60.0, 0.0), (50.0, 50.0, 150.0))
    rows = [(t, b) for t, b in sorted(boxes.items()) if b != default]
    lines = ['/* Generated by scripts/validate_npc.py --emit-box (NATIVE-NPC-001): the object box',
             ' * (o + 0x128 min, o + 0x134 max) that the box section of the character create',
             ' * routine 0x0137d8a1 (0x0137dfe1..0x0137ed7e) gives each model index, read by',
             ' * executing that section in Unicorn for every index 0..0x3af6.  Only indices that',
             ' * differ from the default (-60, -60, 0)..(50, 50, 150) are listed.  Constants only. */',
             '#ifndef MU_CHARACTER_BOX_TABLE_H', '#define MU_CHARACTER_BOX_TABLE_H', '',
             'static const struct { int32_t type; float min[3], max[3]; } MU_CHARACTER_BOXES[] = {']
    for t, (mn, mx) in rows:
        lines.append(f'    {{{t:#06x}, {{{mn[0]!r}f, {mn[1]!r}f, {mn[2]!r}f}}, {{{mx[0]!r}f, {mx[1]!r}f, {mx[2]!r}f}}}},')
    lines += ['};', '', '#endif', '']
    Path(path).write_text('\n'.join(lines).replace('.0f', '.0f'))
    return len(rows)


def native_box(lib, t):
    mn, mx = (ctypes.c_float*3)(), (ctypes.c_float*3)()
    lib.mu_character_box(t, mn, mx)
    return tuple(mn), tuple(mx)


# --------------------------------------------------------------------------- main

MUTATIONS = {
    'talk_storage_slot': ['-DMU_MUT_TALK_STORAGE'],
    'talk_sound': ['-DMU_MUT_TALK_SOUND'],
    'axis_strict': ['-DMU_MUT_AXIS_STRICT'],
    'pick_distance': ['-DMU_MUT_PICK_DISTANCE'],
    'box_default': ['-DMU_MUT_BOX_DEFAULT'],
}


def run_all(text, data, lib, args, rng, report):
    report['talk'] = run_talk(text, data, lib, args.talk_cases, random.Random(args.seed))
    pm = PickMachine(text, data)
    mism = 0
    first = None
    for k in range(args.cases):
        axis, p1, p2, obb = rand_vec(rng), rand_vec(rng, 800), rand_vec(rng, 800), rand_obb(rng)
        client = pm.axis(axis, p1, p2, obb)
        native = lib.mu_pick_axis_overlap((ctypes.c_float*3)(*axis), (ctypes.c_float*3)(*p1), (ctypes.c_float*3)(*p2),
                                          ctypes.byref(Obb((ctypes.c_float*12)(*obb))))
        if client != native:
            mism += 1
            first = first or {'axis': axis, 'p1': p1, 'p2': p2, 'obb': obb, 'client': client, 'native': native}
    report['axis'] = {'cases': args.cases, 'mismatches': mism, 'first': first}
    mism, first, hits = 0, None, 0
    for k in range(args.cases):
        obb = rand_obb(rng)
        centre = [obb[i] + 0.5*(obb[3+i] + obb[6+i] + obb[9+i]) for i in range(3)]
        p1 = [f32(centre[i] + rng.uniform(-900, 900)) for i in range(3)]
        p2 = [f32(centre[i] + rng.uniform(-900, 900)) for i in range(3)] if k % 2 else \
             [f32(2*centre[i] - p1[i] + rng.uniform(-60, 60)) for i in range(3)]
        client = pm.segment(p1, p2, obb)
        native = lib.mu_pick_segment_obb((ctypes.c_float*3)(*p1), (ctypes.c_float*3)(*p2),
                                         ctypes.byref(Obb((ctypes.c_float*12)(*obb))))
        hits += client
        if client != native:
            mism += 1
            first = first or {'p1': p1, 'p2': p2, 'obb': obb, 'client': client, 'native': native}
    report['segment'] = {'cases': args.cases, 'mismatches': mism, 'hits': hits, 'first': first}
    mism, first, picked = 0, None, 0
    for k in range(args.pick_cases):
        scene, chars, kind = pick_case(rng, k)
        client = pm.pick(scene, chars, kind)
        native = native_pick(lib, scene, chars, kind)
        picked += client[0] >= 0
        if client != native:
            mism += 1
            first = first or {'kind': kind, 'client': client[0], 'native': native[0]}
    report['pick'] = {'cases': args.pick_cases, 'mismatches': mism, 'picked': picked, 'first': first}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--text', default=pins.TEXT.default_str())
    ap.add_argument('--data', default=pins.DATA.default_str())
    ap.add_argument('--cases', type=int, default=1000, help='axis and segment cases')
    ap.add_argument('--talk-cases', type=int, default=8, help='cases per talk result byte')
    ap.add_argument('--pick-cases', type=int, default=300)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--emit-box', action='store_true')
    ap.add_argument('--json', help='write the report here')
    args = ap.parse_args()
    text, data = pins.TEXT.read(args.text, exit=True), pins.DATA.read(args.data, exit=True)
    report = {}
    boxes = run_box(text, data)
    if args.emit_box:
        report['box_rows'] = emit_box(boxes, LIB_DIR/'character_box_table.h')
    lib = load_library()
    bm = [t for t in range(BOX_TYPES) if native_box(lib, t) != boxes[t]]
    report['box'] = {'types': BOX_TYPES, 'mismatches': len(bm), 'first': bm[:5],
                     'non_default': sum(1 for b in boxes.values() if b != ((-60.0, -60.0, 0.0), (50.0, 50.0, 150.0)))}
    run_all(text, data, lib, args, random.Random(args.seed), report)
    if args.mutations:
        report['mutations'] = {}
        for name, flags in MUTATIONS.items():
            mlib = load_library(flags)
            sub = {}
            small = argparse.Namespace(**{**vars(args), 'cases': min(args.cases, 300), 'talk_cases': 2,
                                          'pick_cases': min(args.pick_cases, 120)})
            run_all(text, data, mlib, small, random.Random(args.seed), sub)
            bmm = sum(1 for t in range(BOX_TYPES) if native_box(mlib, t) != boxes[t])
            total = sub['talk']['mismatches'] + sub['axis']['mismatches'] + sub['segment']['mismatches'] + \
                sub['pick']['mismatches'] + bmm
            report['mutations'][name] = {'detected': total > 0, 'mismatches': total}
    load_library()   # leave the unmutated library
    text_out = json.dumps(report, indent=1, default=str)
    if args.json:
        Path(args.json).write_text(text_out)
    summary = {k: ({kk: v[kk] for kk in ('cases', 'types', 'mismatches', 'picked', 'hits', 'non_default') if kk in v}
                   if isinstance(v, dict) and k != 'mutations' else v) for k, v in report.items()}
    print(json.dumps(summary, indent=1, default=str))
    failed = any(isinstance(v, dict) and v.get('mismatches') for k, v in report.items() if k != 'mutations')
    if args.mutations:
        failed = failed or not all(v['detected'] for v in report['mutations'].values())
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
