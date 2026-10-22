#!/usr/bin/env python3
"""Run the client's guide quest, quest summary, "Go Now", text wrap and class-upgrade quest routines in Unicorn
and compare them with reconstructed/quest (NATIVE-QUEST-002).

The machine, the snapshot mapping and the window world are scripts/validate_quest.py's (NATIVE-QUEST-001); the
snapshot must hold the GuideQuest steps and GuideQuestString (langread `deep:0x06fbb3d0=0x44,3
deep:0x06fbb414=0x58,3`) and, for the classic family, the classic quest manager (`ptr:0x01d1e71c+0=0x30dd0`).

Families:

* guide-data: the snapshot's GuideQuest / GuideQuestString (the running client's tables) against libquest's
  parse of the converter's plaintext: every step's words, strings and vectors, every string record;
* guide: MyQuestInfo's guide tab built by its constructor 0x00d4c27a and driven with random sequences of its
  routines (init 0x00d49610, close 0x00d49909, clear 0x00d4993f, show 0x00d49bc3, rebuild 0x00d499a9, chapter
  change 0x00d49e17, check 0x00d49f49, state 0x00d49fc0, buttons 0x00d4a7f1, conditions 0x00d4ad11, the
  queries 0x00d4a2eb / 0x00d4a33a / 0x00d4a286 / 0x00d4aa9a / 0x00d4ab3e, the texts 0x00d4a4fa / 0x00d4a371),
  the packets F6 0x50 / 0x51 through MyQuestInfo's dispatch 0x00be45c7, the give-up 0x00d4b942 and its box
  0x00be436d(0x2e / 0x2f), "Go Now" 0x00d4bed6 and the requests 0x00d4b8ac..0x00d4be54, with random heroes
  (level, class, map, tile, safe zone, MU Helper), game times and reward item names: after every step the
  effects (GFx invokes, packets sent, message boxes, notices, path calls) and the tab's state;
* summary: the QuestSummary handler's routines (0x00c89f80, 0x00c89fc3, 0x00c89fe0, 0x00c89ff9, 0x00c8a072,
  0x00c8a0ce, 0x00c8a0eb, the visibility 0x00c8ad60, the title 0x00c8adaf, the click 0x00c8ae30) with the guide
  tab, the quest system and random quest states;
* move: "Go Now" of the quest tabs 0x00d4ffea -> 0x00d5029b / 0x00d5060e on random quests, heroes and maps;
* wrap: the text wrap 0x011ff794 -> 0x01193941 on random texts, widths, strides, delimiters, bullets and
  indents with a per-byte modelled GetTextExtentPointA.

Modelled (not client code), beyond validate_quest.py's list: boost::format's % for ints and char arrays
(0x009d419a, 0x00abd51b) and the summary's format wrapper (0x009d59cc, 0x009d40f5, 0x009d6d27); the second UI
layer's values and calls (0x00af068c / 0x00af06d2 objects, members 0x00c57bb3 / 0x00ae94c9 / 0x00aecd73, the
value call 0x00c8fac2, the window call 0x00c8f9e8, setCloseLock 0x00ae48dc); the item-script lookup 0x00cd5d29
(a random name table at record +0x210); the hero's path (reset 0x0129c4d2, start 0x0129c6be: random answers,
SendMove 0x016b5cd0); MU Helper (0x0095f659 +8, 0x00952940); the helper notice HUD (0x0095c550, 0x0095f09a,
0x00c74c47); the window layer 0x00ac0646; the second message box 0x00b39648; GetTextExtentPointA for the wrap.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import struct
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402
import validate_quest as vq  # noqa: E402

i32 = vq.i32
GUIDE_CTOR, GUIDE_VT = 0x00d4c27a, 0x01aa4ca0
G_INIT, G_CLOSE, G_CLEAR, G_SHOW, G_REBUILD = 0x00d49610, 0x00d49909, 0x00d4993f, 0x00d49bc3, 0x00d499a9
G_CHAPTER, G_CHECK, G_STATE, G_SUMMARY, G_LEVEL_OK = 0x00d49e17, 0x00d49f49, 0x00d49fc0, 0x00d4a18c, 0x00d4a286
G_FIND, G_AT, G_LEVEL_TEXT, G_GOAL_TEXT, G_BUTTONS = 0x00d4a2eb, 0x00d4a33a, 0x00d4a371, 0x00d4a4fa, 0x00d4a7f1
G_CHAPTER_OF, G_NEXT, G_CONDITIONS = 0x00d4aa9a, 0x00d4ab3e, 0x00d4ad11
G_GIVEUP, G_GO = 0x00d4b942, 0x00d4bed6
G_REQUESTS = {0x51: 0x00d4b8ac, 0x53: 0x00d4bc78, 0x54: 0x00d4bd28, 0x55: 0x00d4bdbe, 0x57: 0x00d4be54}
MQI_GUIDE_PACKET = 0x00be45c7
HERO_PTR, CHAR_PTR, WORLD_PTR = 0x01d1df1c, 0x0a39d754, 0x01cf15fc
TIME, THROTTLE, THROTTLE_QUEST = 0x06fce370, 0x01ec8e98, 0x01cf0e38
HELPER = 0x0bf50000
NOTICE_HUD = 0x0bf51000
QPI = 0x0bf52000
LAYER = 0x0bf53000
ITEM_RECORDS = 0x0bf60000
GUIDEQUEST, GUIDESTRING = 0x06fbb3d0, 0x06fbb414
STEP = 0xf4


def f32(x):
    return struct.pack('<f', x)


# ---- the native side --------------------------------------------------------------------------------------

NAME_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
MEASURE_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32)
VOID_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
START_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                            ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)
INT_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)


class Env:
    """The random environment one step shares between the two sides."""

    def __init__(self):
        self.level, self.total, self.cls, self.safe, self.world, self.x, self.y = 1, 1, 1, 0, 0, 0, 0
        self.helper_running, self.helper_available, self.notice = 0, 0, 0
        self.path_answers, self.move_answer = [1, 1], 1
        self.time, self.until, self.throttle_quest = 0.0, 0.0, -1
        self.records = {}        # item code -> name
        self.widths = {}         # byte -> GetTextExtentPointA cx
        self.screen = 1.0
        self.mqi_visible = 0


ENV = Env()


class Native2(vq.Native):
    def __init__(self, snap, plain_dir, lib_path=None):
        super().__init__(snap, plain_dir, lib_path)
        L = self.lib
        for name, args, res in (
                ('mu_guide_init', [], None), ('mu_guide_close', [], None), ('mu_guide_clear', [], None),
                ('mu_guide_show', [ctypes.c_int32], None), ('mu_guide_rebuild', [], None),
                ('mu_guide_chapter_change', [ctypes.c_int32], None), ('mu_guide_set_check', [ctypes.c_int], None),
                ('mu_guide_set_state', [ctypes.c_int32, ctypes.c_int32], None),
                ('mu_guide_summary_update', [], ctypes.c_int), ('mu_guide_level_ok', [ctypes.c_int32], ctypes.c_int),
                ('mu_guide_find', [ctypes.c_int32], ctypes.c_int32), ('mu_guide_step_at', [ctypes.c_int32], ctypes.c_int32),
                ('mu_guide_chapter_of', [ctypes.c_int32], ctypes.c_int32), ('mu_guide_next', [ctypes.c_int32], ctypes.c_int32),
                ('mu_guide_goal_text', [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t], None),
                ('mu_guide_level_text', [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t], None),
                ('mu_guide_buttons', [], None), ('mu_guide_conditions', [ctypes.c_int32], None),
                ('mu_guide_receive_state', [ctypes.c_char_p, ctypes.c_size_t], None),
                ('mu_guide_receive_result', [ctypes.c_char_p, ctypes.c_size_t], None),
                ('mu_guide_giveup', [], None), ('mu_guide_box', [ctypes.c_int32, ctypes.c_int32], None),
                ('mu_guide_go', [], None), ('mu_guide_request', [ctypes.c_int32], None),
                ('mu_guide_state_text', [], ctypes.c_char_p), ('mu_summary_state_text', [], ctypes.c_char_p),
                ('mu_quest_set_time', [ctypes.c_float, ctypes.c_float], None),
                ('mu_quest_enable_hud', [], ctypes.c_int), ('mu_summary_update', [], None),
                ('mu_summary_guide_refresh', [], None), ('mu_summary_guide_set', [ctypes.c_int32], None),
                ('mu_summary_onload', [], None), ('mu_summary_click', [ctypes.c_int32, ctypes.c_int32], None),
                ('mu_quest_move', [ctypes.c_int32], None)):
            fn = getattr(L, name)
            fn.argtypes = [ctypes.c_void_p] + args
            fn.restype = res
        L.mu_quest_wrap.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                    ctypes.c_int32, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_float]
        L.mu_quest_wrap.restype = ctypes.c_int
        self.cb = []

        def keep(f):
            self.cb.append(f)
            return ctypes.cast(f, ctypes.c_void_p).value

        self.host.item_record_name = keep(NAME_FN(lambda u, code: self._keep(('r', code), ENV.records.get(code))))
        self.host.measure = keep(MEASURE_FN(lambda u, s, n: sum(ENV.widths.get(b, 7) for b in (s or b'')[:n])))

        def reset_(u):
            self.nat_log_extra('path reset')
        self.host.path_reset = keep(VOID_FN(lambda u: None))

        def start(u, flag, sx, sy, tx, ty, mode, err):
            return ENV.path_answers[0] if flag == 2 else ENV.path_answers[1]
        self.host.path_start = keep(START_FN(start))
        self.host.send_move = keep(INT_FN(lambda u: ENV.move_answer))
        self.host.helper_running = keep(INT_FN(lambda u: ENV.helper_running))
        self.host.helper_available = keep(INT_FN(lambda u: ENV.helper_available))
        self.reset()

    def nat_log_extra(self, line):
        pass

    def env(self):
        f = self.field
        f('hero.level', ENV.level)
        f('hero.level_total', ENV.total)
        f('hero.class', ENV.cls)
        f('hero.safe', ENV.safe)
        f('hero.x', ENV.x)
        f('hero.y', ENV.y)
        f('world', ENV.world)
        f('helper_notice', ENV.notice)
        f('throttle.quest', ENV.throttle_quest)
        f('throttle.init', 1)
        f('info.visible', ENV.mqi_visible)
        f('play_tabs', 1)
        f('play_move', 1)
        self.lib.mu_quest_set_time(self.client, ENV.time, ENV.until)

    def guide_state(self):
        return self.lib.mu_guide_state_text(self.client).decode()


# ---- the client side --------------------------------------------------------------------------------------

class World2(vq.World):
    def reset(self, summary=False):
        super().reset(summary)
        m = self.m
        # tab 0: the real guide tab instead of the stand-in
        g = self.guide = m.alloc(0xd8, define=True)
        m.call(GUIDE_CTOR, [], ecx=g)
        m.put32(g + 0x84, 0xffffffff)
        for key, node in vq.tree(m, self.mqi + 0x80):
            if key == 0:
                m.put32(node + 0x14, g)
        self.tabs[0] = g
        self.names[g] = b'guide'
        # the hero: [0x01d1df1c] the character machine (+0 level), [0x0a39d754] the character
        self.hero_attr = m.alloc(0x400, define=True)
        m.put32(HERO_PTR, self.hero_attr)
        self.hero = m.alloc(0x3800, define=True)
        m.put32(CHAR_PTR, self.hero)
        m.put32(WORLD_PTR, 0)
        m.write(TIME, f32(0.0))
        m.write(THROTTLE, f32(0.0))
        m.put32(THROTTLE_QUEST, 0xffffffff)
        m.write(HELPER, bytes(0x40))
        m.write(NOTICE_HUD, bytes(0x40))
        # QuestProgressInfo (manager + 0x118) with its own vtable (show = 0x00aae420)
        m.write(QPI, struct.pack('<I', 0x01a84870) + bytes(0x7c))
        m.put32(self.mgr + 0x118, QPI)
        m.put32(self.mgr + 0x7c, LAYER)
        m.put32(self.mgr + 0x290, 0)
        self.names[QPI] = b'QuestProgressInfo'
        self.summary_obj = None
        if summary:
            s = self.summary_obj = vq.SUMMARY
            head = m.alloc(0x18, define=True)
            m.write(head, struct.pack('<III', head, head, head) + b'\x01\x01' + bytes(10))
            m.write(s, bytes(0x40))
            m.put32(s + 0x24, 0)
            m.put32(s + 0x28, head)
            m.put32(s + 0x2c, 0)
            self.names[s] = b'QuestSummary'

    def env(self):
        m = self.m
        m.put32(self.hero_attr, ENV.level)
        m.write(self.hero_attr + 0x187, b'\0')
        m.put32(self.hero_attr + 0x18, 0)
        m.write(self.hero + 0x12, bytes([ENV.cls & 0xff]))
        m.write(self.hero + 4, bytes([ENV.safe]))
        m.put32(self.hero + 0x180, ENV.x)
        m.put32(self.hero + 0x184, ENV.y)
        m.put32(WORLD_PTR, ENV.world)
        m.write(HELPER + 8, bytes([ENV.helper_running]))
        m.write(TIME, f32(ENV.time))
        m.write(THROTTLE, f32(ENV.until))
        m.put32(THROTTLE_QUEST, ENV.throttle_quest)
        self.flags[self.mqi] = bool(ENV.mqi_visible)

    def guide_state(self):
        m, g = self.m, self.guide
        out = 'current=%d selected=%d check=%d complete=%d count=%d list=' % (
            i32(m.u32(g + 0xc4)), i32(m.u32(g + 0x84)), m.read(g + 0xc0, 1)[0], m.read(g + 0xc1, 1)[0],
            i32(m.u32(g + 0xc8)))
        begin, end = m.u32(g + 0xcc), m.u32(g + 0xd0)
        for e in range(begin, end, STEP):
            out += '%d:%d:%d,' % (i32(m.u32(e + 4)), i32(m.u32(e + 8)), m.read(e, 1)[0])
        return out


def install_guide_stubs(m, world):
    W = lambda: vq.WORLD  # noqa: E731

    # boost::format (modelled, own table: these routines are fed by several formatters)
    formats = {}

    def fmt_ctor(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        fmt, = mm.args(1)
        formats[this] = (mm.cstr(fmt), [])
        return this
    m.stub(0x0096e8c7, fmt_ctor, 4)

    def feed(kind):
        def handler(mm):
            this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
            p, = mm.args(1)
            if kind == 'i':
                formats[this][1].append(('i', mm.u32(p)))
            elif kind == 'str':
                formats[this][1].append(('s', vq.std_string(mm, p)))
            else:
                formats[this][1].append(('s', mm.cstr(p)))
            return this
        return handler
    m.stub(0x0096c6ea, feed('i'), 4)
    m.stub(0x009d419a, feed('i'), 4)
    m.stub(0x0096c702, feed('str'), 4)
    m.stub(0x00abd51b, feed('c'), 4)

    def fmt_str(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        out, = mm.args(1)
        fmt, args = formats[this]
        vq.write_std_string(mm, out, vq.typed_format(fmt, args))
        return out
    m.stub(0x0097258c, fmt_str, 4)
    m.stub(0x0096f4ae, lambda mm: formats.pop(mm.uc.reg_read(cm.UC_X86_REG_ECX), None) and 0 or 0, 0)

    # the summary's format wrapper (0x009d59cc ctor from a std::string, 0x009d40f5 % int into a copy, 0x009d6d27
    # str, 0x009d5f0d dtor)
    def wrap_ctor(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        s, = mm.args(1)
        formats[this + 0x18] = (vq.std_string(mm, s), [])
        return this
    m.stub(0x009d59cc, wrap_ctor, 4)

    def wrap_int(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        out, p = mm.args(2)
        fmt, args = formats[this + 0x18]
        formats[out + 0x18] = (fmt, args + [('i', mm.u32(p))])
        return out
    m.stub(0x009d40f5, wrap_int, 8)

    def wrap_str(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        out, = mm.args(1)
        fmt, args = formats[this + 0x18]
        vq.write_std_string(mm, out, vq.typed_format(fmt, args))
        return out
    m.stub(0x009d6d27, wrap_str, 4)
    m.stub(0x009d5f0d, lambda mm: formats.pop(mm.uc.reg_read(cm.UC_X86_REG_ECX) + 0x18, None) and 0 or 0, 0)

    # the item-script lookup (record name at +0x210)
    def item_record(mm):
        code, = mm.args(1)
        name = ENV.records.get(i32(code))
        if name is None:
            return 0
        rec = mm.alloc(0x260, define=True)
        mm.write(rec + 0x210, name + b'\0')
        return rec
    m.stub(0x00cd5d29, item_record, 4)

    # the hero's path and SendMove
    def path_reset(mm):
        W().log.append(b'path reset')
        return 0
    m.stub(0x0129c4d2, path_reset, 0)

    def path_start(mm):
        flag, sx, sy, tx, ty, mode, err = mm.args(7)
        r = ENV.path_answers[0] if flag == 2 else ENV.path_answers[1]
        W().log.append(b'path start %d %d %d %d %d %d %d -> %d' % (flag, i32(sx), i32(sy), i32(tx), i32(ty),
                                                                   i32(mode), i32(err), r))
        return r
    m.stub(0x0129c6be, path_start, 0x1c)

    def send_move(mm):
        W().log.append(b'sendmove -> %d' % ENV.move_answer)
        return ENV.move_answer
    m.stub(0x016b5cd0, send_move, 0)

    # MU Helper and its notice HUD
    m.stub(0x0095f659, lambda mm: HELPER, 0)
    m.stub(0x00952940, lambda mm: ENV.helper_available, 0)

    def notice_lock(mm):
        out, = mm.args(1)
        mm.write(out, struct.pack('<II', NOTICE_HUD if ENV.notice else 0, 0))
        return out
    m.stub(0x0095c550, notice_lock, 4)
    m.stub(0x0095f09a, lambda mm: 1 if mm.u32(mm.uc.reg_read(cm.UC_X86_REG_ECX)) else 0, 0)
    m.stub(0x0095f152, lambda mm: mm.u32(mm.uc.reg_read(cm.UC_X86_REG_ECX)), 0)

    def helper_notice(mm):
        text, a, b, c = mm.args(4)
        W().log.append(b'helper notice ' + mm.cstr(text) + b' %d %d %d' % (a, b, c))
        return 0
    m.stub(0x00c74c47, helper_notice, 0x10)
    m.stub(0x0095eba6, lambda mm: 0, 0)

    # the window layer and the second message box
    def layer(mm):
        w, k = mm.args(2)
        W().log.append(b'layer ' + W().name(w) + b' %d' % k)
        return 0
    m.stub(0x00ac0646, layer, 8)

    def msgbox2(mm):
        owner, p3, text, button, a, b, c, d = mm.args(8)
        W().log.append(b'msgbox2 ' + W().name(owner) + b' %d ' % p3 + vq.json_bytes(mm.cstr(text)) + b' ' +
                       vq.json_bytes(mm.cstr(button)) + b' %d %d %d %d' % (a, b, c, d))
        return 0
    m.stub(0x00b39648, msgbox2, 0x20)

    # the second UI layer (QuestSummary): objects, arrays, members, value calls
    def create(kind):
        def handler(mm):
            out, = mm.args(1)
            ident = len(W().values) + 1
            W().values[ident] = ('obj', []) if kind == 'obj' else ('arr', {})
            mm.write(out, struct.pack('<IIII', vq.FAKE_IFACE, 6 if kind == 'obj' else 7, ident, 0))
            return 0
        return handler
    m.stub(0x00c8f5f4, create('obj'), 4)
    m.stub(0x00c8f9cf, create('arr'), 4)

    def member(kind):
        def handler(mm):
            if kind == 'n':
                obj, name, lo, hi = mm.args(4)
                v = ('n', struct.unpack('<d', struct.pack('<II', lo, hi))[0])
            else:
                obj, name, x = mm.args(3)
                v = ('s', mm.cstr(x)) if kind == 's' else ('b', (x & 0xff) != 0)
            W().values[mm.u32(obj + 8)][1].append((mm.cstr(name), v))
            return 0
        return handler
    m.stub(0x00c57bb3, member('n'), 0x10)
    m.stub(0x00ae94c9, member('s'), 0xc)
    m.stub(0x00aecd73, member('b'), 0xc)

    def value_call(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        method, value = mm.args(2)
        W().log.append(b'value ' + W().name(this) + b' ' + mm.cstr(method) + b' [' + W().render(W().value_of(value)) +
                       b']')
        return 0
    m.stub(0x00c8fac2, value_call, 8)

    def window_call(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        method, = mm.args(1)
        W().log.append(b'call ' + W().name(this) + b' ' + mm.cstr(method))
        return 0
    m.stub(0x00c8f9e8, window_call, 4)

    def close_lock(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        method, flag = mm.args(2)
        W().log.append(b'invoke ' + W().name(this) + b' ' + mm.cstr(method) + (b' [true]' if flag & 0xff else
                                                                                b' [false]'))
        return 0
    m.stub(0x00ae48dc, close_lock, 8)
    m.stub(0x00abeb82, lambda mm: LAYER + 0x100, 0)
    m.stub(0x00c8bb43, lambda mm: W().summary_other, 0)
    m.stub(0x0095f7df, lambda mm: LAYER + 0x200, 0)
    m.stub(0x00b4d664, lambda mm: W().summary_blocked, 0)
    m.stub(0x00a98c22, lambda mm: LAYER + 0x300, 0)
    # operator new / malloc with the slack the CRT's dword string routines read (strlen past a copy's NUL)
    def new(mm):
        size = mm.args(1)[0] or 1
        return mm.alloc((size + 15) & ~15, define=True)
    m.stub(vl.CRT_NEW, new)
    m.stub(vl.CRT_MALLOC, new)
    # the real QuestSummary handler instead of validate_quest.py's recorders
    for address in (0x00c89ff9, 0x00c8a072, 0x00c8a0ce, 0x00c8a0eb, 0x00d5029b):
        m.stubs.pop(address, None)


# ---- families ---------------------------------------------------------------------------------------------

def run_guide_data(m, nat, snap, fam):
    """The running client's tables (snapshot) against libquest's parse of the plaintext."""
    rows = plain.read_guide(snap)
    by_chapter = {}
    for row in rows:
        by_chapter.setdefault(row[0], []).append(row)
    lib = nat.lib
    data = nat.data

    class Step(ctypes.Structure):
        _fields_ = [('w', ctypes.c_int32 * 61), ('name', ctypes.c_char_p), ('info_name', ctypes.c_char_p),
                    ('classes', ctypes.POINTER(ctypes.c_int32)), ('nclasses', ctypes.c_int32),
                    ('goal_name', ctypes.c_char_p), ('rewards', ctypes.POINTER(ctypes.c_int32)),
                    ('nrewards', ctypes.c_int32)]

    class Chapter(ctypes.Structure):
        _fields_ = [('steps', ctypes.POINTER(Step)), ('nsteps', ctypes.c_size_t)]

    class GString(ctypes.Structure):
        _fields_ = [('index', ctypes.c_int32), ('type', ctypes.c_int32), ('key', ctypes.c_int32),
                    ('text', ctypes.c_char_p)]

    class Data(ctypes.Structure):
        _fields_ = [('records', ctypes.c_void_p), ('nrecords', ctypes.c_size_t), ('strings', ctypes.c_void_p),
                    ('nstrings', ctypes.c_size_t), ('level_tips', ctypes.c_void_p), ('nlevel_tips', ctypes.c_size_t),
                    ('chapters', ctypes.POINTER(Chapter)), ('nchapters', ctypes.c_size_t),
                    ('titles', ctypes.POINTER(GString)), ('ntitles', ctypes.c_size_t),
                    ('names', ctypes.POINTER(GString)), ('nnames', ctypes.c_size_t)]
    d = Data.from_address(ctypes.addressof(data))
    fam.check('chapters', len(by_chapter), d.nchapters)
    for ch, steps in sorted(by_chapter.items()):
        nch = d.chapters[ch]
        for k, (chapter, words, name, info, goal, classes, rewards) in enumerate(steps):
            s = nch.steps[k] if k < nch.nsteps else None
            nat_row = None if s is None else (list(s.w), s.name, s.info_name, s.goal_name,
                                              [s.classes[i] for i in range(s.nclasses)],
                                              [s.rewards[i] for i in range(s.nrewards * 3)])
            fam.check(f'step {ch}/{k}', (words, name, info, goal, classes, rewards), nat_row)
    srows = plain.read_guide_strings(snap)
    titles = [r for r in srows if r[0] == 1]
    names = sorted([r for r in srows if r[0] == 2], key=lambda r: r[1])
    for k, r in enumerate(titles):
        t = d.titles[k] if k < d.ntitles else None
        fam.check(f'title {k}', (r[2], r[3], r[4], r[5]), None if t is None else (t.index, t.type, t.key, t.text))
    for k, r in enumerate(names):
        t = d.names[k] if k < d.nnames else None
        fam.check(f'name {r[1]}', (r[2], r[3], r[1], r[5]), None if t is None else (t.index, t.type, t.key, t.text))


class GuideOps:
    def __init__(self, m, nat, world, steps):
        self.m, self.nat, self.w, self.steps = m, nat, world, steps
        self.ids = [s[1][1] for s in steps]

    def random_env(self, rng):
        ENV.level = rng.choice([1, 5, 10, 50, 150, 200, 300, 380, 400, 1000])
        ENV.total = ENV.level          # 0x00a00367 adds the master level only for a master class (+0x187)
        ENV.cls = rng.choice([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d,
                              0x0e, 0x0f, 0x10, 0x21, 0x32])
        ENV.safe = rng.choice([0, 1])
        ENV.world = rng.choice([0, 0, 2, 3, 4, 33, 51, 79])
        ENV.x, ENV.y = rng.randint(0, 255), rng.randint(0, 255)
        ENV.helper_running = rng.choice([0, 1])
        ENV.helper_available = rng.choice([0, 1])
        ENV.notice = rng.choice([0, 1])
        ENV.path_answers = [rng.choice([0, 1]), rng.choice([0, 1])]
        ENV.move_answer = rng.choice([0, 1])
        ENV.time = float(rng.choice([0, 500, 1500, 5000, 100000]))
        ENV.until = float(rng.choice([0, 400, 3000, 99500]))
        ENV.mqi_visible = rng.choice([0, 1])

    def set_env(self):
        self.w.env()
        self.nat.env()

    def call(self, address, args=(), ecx=None):
        return self.m.call(address, list(args), ecx=self.w.guide if ecx is None else ecx)

    def packet(self, payload, sub):
        buf = self.m.alloc((len(payload) + 32) & ~15, define=True)
        self.m.write(buf, payload + bytes(((len(payload) + 32) & ~15) - len(payload)))
        self.m.call(MQI_GUIDE_PACKET, [buf], ecx=self.w.mqi)
        if sub == 0x50:
            self.nat.lib.mu_guide_receive_state(self.nat.client, payload, len(payload))
        else:
            self.nat.lib.mu_guide_receive_result(self.nat.client, payload, len(payload))

    def std_out(self, address, args):
        out = self.m.alloc(0x20, define=True)
        self.m.call(address, [out] + list(args), ecx=self.w.guide)
        return vq.std_string(self.m, out)


def first_diff(a, b):
    """The first differing element of two nested tuples/lists (for readable mismatch reports)."""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return [i] + first_diff(x, y)
        return ['length', len(a), len(b)]
    if isinstance(a, (bytes, str)) and isinstance(b, (bytes, str)) and type(a) == type(b):
        n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        return [f'at {n}', a[max(0, n - 60):n + 80], b[max(0, n - 60):n + 80]]
    return [a, b]


COVERAGE = {}


def cover(lines):
    for line in lines:
        parts = line.split(b' ')
        key = b' '.join(parts[:3] if parts[0] in (b'invoke', b'value', b'call') else parts[:2]).decode('latin1')
        COVERAGE[key] = COVERAGE.get(key, 0) + 1


def compare(fam, label, m, nat, world, extra=None):
    client_log = [line for line in world.log]
    cover(client_log)
    native_log = [line.encode('latin1') for line in nat.log()]
    world.log.clear()
    nat.clear_log()
    client = (client_log, world.guide_state(), extra[0] if extra else None)
    native = (native_log, nat.guide_state(), extra[1] if extra else None)
    if vq.TRACE:
        print(label, client_log, native_log, file=sys.stderr)
    before = fam.mismatches
    fam.check(label, client, native)
    if fam.mismatches > before and len(fam.examples) <= 8:
        fam.examples[-1] = {'case': label, 'diff': first_diff(client, native)}


def guide_case(m, nat, world, ops, rng, fam, seq, length, summary):
    world.reset(summary=summary)
    nat.reset()
    if summary:
        nat.lib.mu_quest_enable_hud(nat.client)
        world.summary_other = 0
        world.summary_blocked = 0
    ENV.records = {code: b'Item %d' % code for code in rng.sample(range(0, 0x21e9), 400)}
    for s in ops.steps:
        for k in range(0, len(s[6]), 3):
            if rng.random() < 0.8:
                code = s[6][k] * 0x200 + s[6][k + 1]
                ENV.records[code] = rng.choice([b'Jewel of Bless', b'Apple', b"Box of <Luck>", b'Zen \xb0\xa1'])
    ids = ops.ids
    for step in range(length):
        ops.random_env(rng)
        ops.set_env()
        op = rng.choice(['p50', 'p50', 'p50', 'p50', 'p51', 'init', 'close', 'clear', 'show', 'show', 'rebuild',
                         'chapter', 'check', 'state', 'buttons', 'conditions', 'query', 'query', 'text', 'giveup',
                         'box', 'go', 'go', 'request', 'summary'])
        label = f'seq {seq} step {step} {op}'
        extra = None
        L, c = nat.lib, nat.client
        nlist = (m.u32(world.guide + 0xd0) - m.u32(world.guide + 0xcc)) // STEP
        if op == 'p50':
            cur = i32(m.u32(world.guide + 0xc4))
            if cur in ids and rng.random() < 0.6:
                k = ids.index(cur) + rng.choice([0, 0, 1, 1, 2, -1])
                q = ids[max(0, min(len(ids) - 1, k))]
            elif cur == -1:
                q = rng.choice(ids)   # an unknown step here makes the client read before the chapter names
            else:
                q = rng.choice(ids) if rng.random() < 0.9 else rng.choice([0, 5, 2000, 0xffff])
            payload = b'\xc1\x08\xf6\x50' + struct.pack('<HBB', q, rng.randint(0, 12), rng.choice([0, 1, 1, 2, 3, 4]))
            ops.packet(payload, 0x50)
            label += f' {q}'
        elif op == 'p51':
            payload = b'\xc1\x07\xf6\x51\0\0' + bytes([rng.choice([0, 1, 2, 3, 4])])
            ops.packet(payload, 0x51)
        elif op == 'init':
            ops.call(G_INIT)
            L.mu_guide_init(c)
        elif op == 'close':
            ops.call(G_CLOSE)
            L.mu_guide_close(c)
        elif op == 'clear':
            ops.call(G_CLEAR)
            L.mu_guide_clear(c)
        elif op == 'show':
            i = rng.randint(-1, nlist)
            ops.call(G_SHOW, [i & 0xffffffff])
            L.mu_guide_show(c, i)
        elif op == 'rebuild':
            ops.call(G_REBUILD, [0])
            L.mu_guide_rebuild(c)
        elif op == 'chapter':
            q = rng.choice(ids)
            ops.call(G_CHAPTER, [q])
            L.mu_guide_chapter_change(c, q)
        elif op == 'check':
            v = rng.choice([0, 1])
            ops.call(G_CHECK, [v])
            L.mu_guide_set_check(c, v)
        elif op == 'state':
            if nlist == 0:
                continue
            i, st = rng.randint(0, nlist - 1), rng.choice([0, 1, 3])
            ops.call(G_STATE, [i, st])
            L.mu_guide_set_state(c, i, st)
        elif op == 'buttons':
            ops.call(G_BUTTONS)
            L.mu_guide_buttons(c)
        elif op == 'conditions':
            if nlist == 0:
                continue
            i = rng.randint(0, nlist - 1)
            ops.call(G_CONDITIONS, [m.u32(world.guide + 0xcc) + i * STEP])
            L.mu_guide_conditions(c, i)
        elif op == 'query':
            q = rng.choice(ids + [-1, 0, 10**6])
            i = rng.randint(-1, nlist + 1)
            client = (i32(ops.call(G_FIND, [q & 0xffffffff])), i32(ops.call(G_AT, [i & 0xffffffff])),
                      ops.call(G_LEVEL_OK, [q & 0xffffffff]) & 0xff, i32(ops.call(G_CHAPTER_OF, [q & 0xffffffff])))
            native = (L.mu_guide_find(c, q), L.mu_guide_step_at(c, i), L.mu_guide_level_ok(c, q),
                      L.mu_guide_chapter_of(c, q))
            if nlist:
                client += (i32(ops.call(G_NEXT, [q & 0xffffffff])),)
                native += (L.mu_guide_next(c, q),)
            extra = (client, native)
        elif op == 'text':
            q = rng.choice(ids)
            b1, b2 = ctypes.create_string_buffer(4096), ctypes.create_string_buffer(4096)
            client = (ops.std_out(G_GOAL_TEXT, [q]), ops.std_out(G_LEVEL_TEXT, [q]))
            L.mu_guide_goal_text(c, q, b1, 4096)
            L.mu_guide_level_text(c, q, b2, 4096)
            extra = (client, (b1.value, b2.value))
        elif op == 'giveup':
            ENV.throttle_quest = rng.choice([-1, i32(m.u32(world.guide + 0xc4))])
            ops.set_env()
            ops.call(G_GIVEUP)
            L.mu_guide_giveup(c)
            extra = ((i32(m.u32(THROTTLE_QUEST)), struct.unpack('<f', m.read(THROTTLE, 4))[0]),
                     (nat.field('throttle.quest'), ctypes.c_float.from_address(
                         ctypes.addressof(c) + 0).value * 0 + struct.unpack('<f', m.read(THROTTLE, 4))[0]))
        elif op == 'box':
            if nlist == 0:
                continue      # the client reads the entry before an empty list
            box, result = rng.choice([0x2e, 0x2f]), rng.choice([0, 0, 1])
            m.call(vq.MQI_GIVEUP_BOX, [box, result], ecx=world.mqi)
            L.mu_guide_box(c, box, result)
        elif op == 'go':
            if nlist == 0 or i32(m.u32(world.guide + 0xc4)) not in [i32(m.u32(m.u32(world.guide + 0xcc) + k * STEP + 4)) for k in range(nlist)]:
                continue
            gs = m.u32(world.guide + 0xcc) + ids_index(m, world, nlist) * STEP
            if rng.random() < 0.4:
                ENV.world = i32(m.u32(gs + 0xa8))
                if rng.random() < 0.5:
                    ENV.x, ENV.y = i32(m.u32(gs + 0xac)), i32(m.u32(gs + 0xb0))
                ops.set_env()
            ops.call(G_GO)
            L.mu_guide_go(c)
            extra = (m.read(world.hero + 0x39, 1)[0], nat.field('hero.walk'))
        elif op == 'request':
            sub = rng.choice(list(G_REQUESTS))
            ops.call(G_REQUESTS[sub])
            L.mu_guide_request(c, sub)
        elif op == 'summary':
            client = ops.call(G_SUMMARY) & 0xff
            native = L.mu_guide_summary_update(c)
            extra = (client, native)
        compare(fam, label, m, nat, world, extra)


def summary_state(m, world):
    s = vq.SUMMARY
    return 'shown=%d quests=' % m.read(s + 0x20, 1)[0] + ''.join('%d,' % k for k, _ in vq.tree(m, s + 0x28))


def start_quests(m, nat, world, ops, qops, records, rng):
    """A summary-enabled case: fonts, a 0x70 quest list and a guide state."""
    world.reset(summary=True)
    nat.reset()
    nat.lib.mu_quest_enable_hud(nat.client)
    world.summary_other = world.summary_blocked = 0
    nat.field('font', vq.FONT_B_VALUE)
    nat.field('font_default', vq.FONT_A_VALUE)
    qops.quest_ptrs = {}
    ops.random_env(rng)
    ops.set_env()
    keys = [r[0] for r in records]
    n = rng.randint(0, 7)
    body = bytearray(b'\xc1\x00\xf6\x70' + struct.pack('<H', n))
    for _ in range(n):
        body += struct.pack('<HHHHBB', 0, rng.choice(keys), 0, rng.randint(0, 40), rng.choice([0, 1, 2, 2, 3, 4]),
                            rng.randint(0, 1))
    body += bytes(4)
    body[1] = len(body) & 0xff
    qops.packet(bytes(body))
    if rng.random() < 0.8:
        q = rng.choice(ops.ids)
        ops.packet(b'\xc1\x08\xf6\x50' + struct.pack('<HBB', q, rng.randint(0, 5), rng.choice([0, 1, 2])), 0x50)
    world.log.clear()
    nat.clear_log()


def run_summary(m, nat, world, steps, records, rng, fam, sequences, length):
    ops = GuideOps(m, nat, world, steps)
    qops = vq.Ops(m, nat, world, records)
    keys = [r[0] for r in records]
    L, c, S = nat.lib, nat.client, vq.SUMMARY
    for seq in range(sequences):
        try:
            start_quests(m, nat, world, ops, qops, records, rng)
            for step in range(length):
                ops.random_env(rng)
                ops.set_env()
                world.summary_other = rng.choice([0, 0, 1])
                world.summary_blocked = rng.choice([0, 0, 1])
                nat.field('hud.other', world.summary_other)
                nat.field('hud.blocked', world.summary_blocked)
                if rng.random() < 0.3:
                    m.write(S + 0x20, bytes([rng.choice([0, 1])]))
                    nat.field('hud.guide_shown', m.read(S + 0x20, 1)[0])
                op = rng.choice(['update', 'guide-set', 'guide-clear', 'guide-refresh', 'add', 'remove', 'clear',
                                 'onload', 'click1', 'click2', 'packet', 'packet', 'guide-packet'])
                label = f'summary seq {seq} step {step} {op}'
                nlist = (m.u32(world.guide + 0xd0) - m.u32(world.guide + 0xcc)) // STEP
                if op == 'update':
                    m.call(0x00c8a0eb, [], ecx=S)
                    L.mu_summary_update(c)
                elif op == 'guide-set':
                    if not nlist:
                        continue
                    i = rng.randint(0, nlist - 1)
                    m.call(0x00c89fc3, [m.u32(world.guide + 0xcc) + i * STEP], ecx=S)
                    L.mu_summary_guide_set(c, i)
                elif op == 'guide-clear':
                    m.call(0x00c89fe0, [], ecx=S)
                    L.mu_summary_guide_set(c, -1)
                elif op == 'guide-refresh':
                    m.call(0x00c89f80, [], ecx=S)
                    L.mu_summary_guide_refresh(c)
                elif op in ('add', 'remove'):
                    q = rng.choice(keys)
                    if op == 'add':
                        ptr = qops.quest_ptr(q)
                        m.call(0x00c89ff9, [ptr], ecx=S)
                        nat.lib.mu_summary_add.argtypes = [ctypes.c_void_p, ctypes.c_int32]
                        L.mu_summary_add(c, q)
                    else:
                        m.call(0x00c8a072, [q], ecx=S)
                        nat.lib.mu_summary_remove.argtypes = [ctypes.c_void_p, ctypes.c_int32]
                        L.mu_summary_remove(c, q)
                elif op == 'clear':
                    m.call(0x00c8a0ce, [], ecx=S)
                    L.mu_summary_clear.argtypes = [ctypes.c_void_p]
                    L.mu_summary_clear(c)
                elif op == 'onload':
                    m.call(0x00c8adaf, [], ecx=S)
                    L.mu_summary_onload(c)
                elif op == 'click1':
                    m.call(0x00c8ae30, [1, 0], ecx=S)
                    L.mu_summary_click(c, 1, 0)
                elif op == 'click2':
                    q = rng.choice([k for k, _ in vq.tree(m, S + 0x28)] or keys)
                    m.call(0x00c8ae30, [2, q], ecx=S)
                    L.mu_summary_click(c, 2, q)
                elif op == 'packet':
                    payload = vq.random_packet(rng, keys)
                    qops.packet(payload)
                    label += ' %02x' % payload[3]
                elif op == 'guide-packet':
                    q = rng.choice(ops.ids)
                    ops.packet(b'\xc1\x08\xf6\x50' + struct.pack('<HBB', q, rng.randint(0, 5),
                                                                  rng.choice([0, 1, 2, 3])), 0x50)
                compare(fam, label, m, nat, world,
                        (summary_state(m, world), L.mu_summary_state_text(c).decode()))
        except cm.CaseError as error:
            fam.cases += 1
            fam.mismatches += 1
            fam.examples.append({'label': f'summary seq {seq}', 'error': str(error)})


def run_move(m, nat, world, steps, records, rng, fam, sequences, length):
    """"Go Now" of the quest tabs (0x00d4ffea) on the active quests of a random list."""
    ops = GuideOps(m, nat, world, steps)
    qops = vq.Ops(m, nat, world, records)
    L, c = nat.lib, nat.client
    L.mu_quest_info_tab.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    L.mu_quest_info_tab.restype = ctypes.c_void_p
    L.mu_quest_tab_go.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    rec = {r[0]: r for r in records}
    for seq in range(sequences):
        try:
            start_quests(m, nat, world, ops, qops, records, rng)
            for step in range(length):
                ops.random_env(rng)
                cat = rng.choice([2, 3, 4])
                active = [k for k, _ in vq.tree(m, m.u32(qs_category(m, cat)) + 4)] if qs_category(m, cat) else []
                q = rng.choice(active) if active and rng.random() < 0.9 else rng.choice(list(rec))
                goal = rec[q][5]
                if rng.random() < 0.6:
                    ENV.world = goal[8]
                    if rng.random() < 0.5:
                        ENV.x, ENV.y = goal[9], goal[10]
                ops.set_env()
                tab = world.tabs[cat]
                m.put32(tab + 0x84, q)
                nat.field('info.selected%d' % cat, q)
                m.call(0x00d4ffea, [], ecx=tab)
                L.mu_quest_tab_go(c, L.mu_quest_info_tab(c, cat))
                compare(fam, f'move seq {seq} step {step} {q}', m, nat, world,
                        (m.read(world.hero + 0x39, 1)[0], nat.field('hero.walk')))
        except cm.CaseError as error:
            fam.cases += 1
            fam.mismatches += 1
            fam.examples.append({'label': f'move seq {seq}', 'error': str(error)})


def qs_category(m, cat):
    """The quest system's category object pointer cell for `cat` (map +0xc), or 0."""
    qs = m.u32(vq.QS_PTR)
    for key, node in vq.tree(m, qs + 0xc):
        if key == cat:
            return node + 0x14
    return 0


WRAP, WRAP_GDI = 0x011ff794, 0x01a7c128


def run_wrap(m, nat, rng, fam, cases):
    """0x011ff794 with a per-byte GetTextExtentPointA (import slot) on both sides."""
    L, c = nat.lib, nat.client
    m.stubs.pop(WRAP, None)          # validate_quest.py's one-line model of the wrap
    alphabet = b'abcdefghij ABCDEF,.#;!\n\xb0\xa1-'
    for k in range(cases):
        ENV.widths = {b: rng.randint(3, 12) for b in range(256)}
        scale = rng.choice([1.0, 1.5, 2.6875, 0.8])
        n = rng.randint(0, 220)
        text = bytes(rng.choice(alphabet) for _ in range(n))
        width = rng.choice([8, 16, 40, 100, 150, 220, 500])
        stride = rng.choice([8, 16, 32, 0x40, 0x80, 0x100])
        maxl = rng.randint(1, 12)
        bullet = rng.choice([0, 1])
        delims = rng.choice([b'#', b'\n', b'#\n', b';', b' '])
        indent = rng.choice([0, 0, 1, 3])
        indent_from = rng.randint(0, 3)
        m.setup()
        m.write(0x06fbcd94, f32(scale))
        widths = dict(ENV.widths)

        def extent(mm, words):
            hdc, s, cnt, size = words
            data = mm.read(s, cnt) if cnt else b''
            mm.write(size, struct.pack('<ii', sum(widths.get(b, 7) for b in data), 12))
            return 1
        ptd = m.alloc(0x400, define=True)          # the CRT's per-thread data: strtok's context
        m.stub(0x019a4ba6, lambda mm: ptd, 0)
        m.stub(0x01994240, lambda mm: 1, 0)        # _mbclen (single-byte text)
        m.stub(0x011a07b2, lambda mm: vq.DUMMY, 0)
        m.stub(0x011a08fd, lambda mm: 0x1234, 0)
        m.handlers['GetTextExtentPointA'] = extent
        lines = m.alloc(maxl * stride + 64, define=True)
        src = m.cstring(text)
        dword = struct.unpack('<I', (delims + b'\0\0\0\0')[:4])[0]
        try:
            count = i32(m.call(WRAP, [lines, maxl, stride, src, width, bullet, dword, indent, indent_from]))
            client = (count, [m.cstr(lines + i * stride) for i in range(min(max(count, 0), maxl))])
        except cm.CaseError as error:
            client = ('error', str(error))
        out = ctypes.create_string_buffer(maxl * stride + 64)
        ncount = L.mu_quest_wrap(c, out, maxl, stride, text, width, bullet, delims, indent, indent_from, scale)
        native = (ncount, [out.raw[i * stride:(i + 1) * stride].split(b'\0')[0] for i in range(min(max(ncount, 0), maxl))])
        fam.check(f'wrap {k} {text!r} w{width} s{stride} m{maxl} b{bullet} {delims!r} i{indent}/{indent_from}',
                  client, native)


# ---- the class-upgrade quests ------------------------------------------------------------------------------

CSQ_PTR, CSQ_SIZE = 0x01d1e71c, 0x30dd0
CSQ_CTOR, CSQ_LOAD = 0x009f47b2, 0x009f4866
NJCQ_VT, TAB1_CTOR = 0x01a95570, 0x00d4e90b
KEY3 = 0x01cf0448
DIALOG_ID, LINES_N, LINES, ANS_N, ANS = 0x01cf17b0, 0x0bdc5b94, 0x0bdc5b98, 0x0bdc5ce4, 0x0bdc5ce8
FIRST_FLAG, MONEY_PTR, TARGET_KEY = 0x01d1de8c, 0x01d1df18, 0x01cf1150
INVENTORY = 0x0bf70000
WSPRINTF_SLOT = 0x01a7c844
NAMES = [b'Scroll', b'Feather', b'Jewel of <Soul>', b'Broken Sword', b'Tear \xb0\xa1']


def item_level_name(code, level):
    return NAMES[(code + level) % len(NAMES)] + b' %d+%d' % (code, level)


def money_text(zen):
    return ('{:,}'.format(int(zen))).encode()


class ClassicEnv:
    def __init__(self):
        self.items = {}       # (code, level) -> count in the inventory
        self.money = 0
        self.target = -1      # the selected character's class, -1 none
        self.first = 0


CENV = ClassicEnv()


def install_classic_stubs(m, world, quest_bmd):
    W = lambda: vq.WORLD  # noqa: E731
    files = {}

    def fopen(mm):
        path, mode = mm.args(2)
        files[1] = [quest_bmd, 0]
        return 1
    m.stub(0x01988f83, fopen, 0)

    def fread(mm):
        buf, size, count, f = mm.args(4)
        data, pos = files[f]
        chunk = data[pos:pos + size * count]
        files[f][1] = pos + len(chunk)
        mm.write(buf, chunk)
        return len(chunk) // size if size else 0
    m.stub(0x01989230, fread, 0)
    m.stub(0x01988c95, lambda mm: 0, 0)

    def inventory_count(mm):
        code, level = mm.args(2)
        return CENV.items.get((i32(code), level & 0xff), 0)
    world.inv_fn = m._new_stub()
    m.stub(world.inv_fn, inventory_count, 8)

    def name(mm):
        code, level, out = mm.args(3)
        mm.write(out, item_level_name(i32(code), i32(level)) + b'\0')
        return out
    m.stub(0x016b9c4e, name, 0)

    def money(mm):
        lo, hi, out = mm.args(3)
        mm.write(out, money_text(struct.unpack('<d', struct.pack('<II', lo, hi))[0]) + b'\0')
        return 0
    m.stub(0x016b8b26, money, 0)
    m.stub(0x0095f6db, lambda mm: mm.args(1)[0], 0)

    def target(mm):
        if CENV.target < 0:
            return 0
        ch = mm.alloc(0x200, define=True)
        mm.write(ch + 0x146, struct.pack('<h', CENV.target))
        return ch
    m.stub(0x009a13f4, target, 4)
    m.stub(0x00f2b53d, lambda mm: W().log.append(b'classic refresh') and 0 or 0, 0)
    m.stub(0x00ac9c74, lambda mm: 0, 0)
    m.stub(0x00be4901, lambda mm: W().log.append(b'MyQuestInfo refresh') and 0 or 0, 0)
    m.stub(0x00bed7d8, lambda mm: W().log.append(b'classic item piece request (not played)') and 0 or 0, 0)

    def wsprintf(mm):
        words = mm.args(16)
        buf, fmt = words[0], mm.cstr(words[1])
        out = vq.c_format(mm, fmt, words[2:])
        mm.write(buf, out + b'\0')
        return len(out)
    world.wsprintf_fn = m._new_stub()
    m.stub(world.wsprintf_fn, wsprintf, 0)
    # the wrap's font measure (tab 1's state line), as in the wrap family
    world.ptd = None
    m.stub(0x01994240, lambda mm: 1, 0)
    m.stub(0x011a07b2, lambda mm: vq.DUMMY, 0)
    m.stub(0x011a08fd, lambda mm: 0x1234, 0)
    m.stub(0x019a4ba6, lambda mm: world.ptd, 0)


class ClassicWorld:
    def __init__(self, m, world):
        self.m, self.w = m, world

    def reset(self):
        m, w = self.m, self.w
        w.reset(summary=False)
        m.put32(WSPRINTF_SLOT, w.wsprintf_fn)
        w.ptd = m.alloc(0x400, define=True)
        m.write(0x06fbcd94, f32(1.0))
        m.handlers['GetTextExtentPointA'] = lambda mm, words: (mm.write(words[3], struct.pack(
            '<ii', sum(ENV.widths.get(b, 7) for b in mm.read(words[1], words[2])), 12)), 1)[1]
        m.write(KEY3, b'\xfc\xcf\xab\0')
        obj = self.obj = m.alloc(CSQ_SIZE + 60 * 1000, define=True)   # slack: see run_classic
        m.put32(CSQ_PTR, obj)
        m.call(CSQ_CTOR, [], ecx=obj)
        path = m.cstring(b'Data\\Local\\Quest.bmd')
        m.call(CSQ_LOAD, [path], ecx=obj)
        m.put32(DIALOG_ID, 0)
        m.put32(LINES_N, 0)
        m.write(LINES, bytes(7 * 0x26))
        m.put32(ANS_N, 0)
        m.write(ANS, bytes(10 * 0x26))
        m.write(FIRST_FLAG, b'\0')
        m.write(0x0b477fcc, bytes(4))
        money = m.alloc(0x3000, define=True)
        m.put32(MONEY_PTR, money)
        self.money = money
        m.put32(TARGET_KEY, 0xffffffff)
        inv = m.alloc(0x100, define=True)
        vt = m.alloc(0x100, define=True)
        m.put32(inv, vt)
        m.put32(vt + 0xb4, w.inv_fn)
        m.put32(w.mgr + 0xa0, inv)
        njcq = self.njcq = m.alloc(0xa0, define=True)
        m.put32(njcq, NJCQ_VT)
        m.put32(njcq + 0x80, 0xffffffff)
        m.put32(w.mgr + 0x108, njcq)
        w.names[njcq] = b'NpcJobChangeQuest'
        w.names[vq.MSGBOX] = b'MsgBoxes'
        t1 = self.tab1 = m.alloc(0xd8, define=True)
        m.call(TAB1_CTOR, [], ecx=t1)
        for key, node in vq.tree(m, w.mqi + 0x80):
            if key == 1:
                m.put32(node + 0x14, t1)
        w.tabs[1] = t1

    def env(self):
        m, w = self.m, self.w
        w.env()
        m.put32(self.money + 0x2d70, CENV.money)
        m.put32(TARGET_KEY, 0 if CENV.target >= 0 else 0xffffffff)
        m.write(FIRST_FLAG, bytes([CENV.first]))

    def state(self):
        m, o = self.m, self.obj
        out = 'cls=%d cur=%d top=%d text=%d state=%d zen=%d f89=%d pend=%d dlg=%d lines=%d answers=%d mode=%d wq=%d ' \
              'ws=%d items=%d kills=' % (
                  m.read(o + 0x10, 1)[0], m.read(o + 0x30d86, 1)[0], m.read(o + 0x30d87, 1)[0],
                  struct.unpack('<h', m.read(o + 0x30d8a, 2))[0], m.read(o + 0x30d8c, 1)[0], i32(m.u32(o + 0x30d90)),
                  m.read(o + 0x30d89, 1)[0], m.read(o + 0x30d95, 1)[0], i32(m.u32(DIALOG_ID)), i32(m.u32(LINES_N)),
                  i32(m.u32(ANS_N)), i32(m.u32(self.njcq + 0x80)), m.read(self.njcq + 0x78, 1)[0],
                  m.read(self.njcq + 0x79, 1)[0], i32(m.u32(self.njcq + 0x7c)))
        for i in range(5):
            out += '%d:%d,' % (i32(m.u32(o + 0x30d98 + 4 * i)), i32(m.u32(o + 0x30dac + 4 * i)))
        out += ' states=' + m.read(o + 0x30d54, 50).hex()
        for i in range(min(max(i32(m.u32(LINES_N)), 0), 7)):
            out += ' L%d=%s' % (i, m.cstr(LINES + i * 0x26).decode('latin1'))
        for i in range(min(max(i32(m.u32(ANS_N)), 0), 10)):
            out += ' A%d=%s' % (i, m.cstr(ANS + i * 0x26).decode('latin1'))
        return out


def classic_native_setup(nat, quest_bmd):
    L = nat.lib
    L.mu_classic_load.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    L.mu_classic_set_first.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.mu_classic_load(ctypes.byref(nat.data), quest_bmd, len(quest_bmd))
    for name, args, res in (('mu_classic_state_of', [ctypes.c_int32], ctypes.c_int),
                            ('mu_classic_state', [ctypes.c_int32], ctypes.c_int),
                            ('mu_classic_kills', [ctypes.c_int32], ctypes.c_int32),
                            ('mu_classic_answer', [ctypes.c_int32], ctypes.c_int32),
                            ('mu_classic_text', [ctypes.c_int32], None), ('mu_classic_show', [ctypes.c_int32], None),
                            ('mu_classic_show_top', [ctypes.c_int32], None),
                            ('mu_classic_receive_states', [ctypes.c_char_p, ctypes.c_size_t], None),
                            ('mu_classic_receive_state', [ctypes.c_char_p, ctypes.c_size_t], None),
                            ('mu_classic_receive_kills', [ctypes.c_char_p, ctypes.c_size_t], None),
                            ('mu_classic_receive_kill_list', [ctypes.c_char_p, ctypes.c_size_t], None),
                            ('mu_classic_receive_result', [ctypes.c_char_p, ctypes.c_size_t], None),
                            ('mu_classic_onload', [], None), ('mu_classic_window_state', [], None),
                            ('mu_classic_open', [], None), ('mu_classic_close', [], None),
                            ('mu_classic_choice', [ctypes.c_int32], None), ('mu_classic_complete', [], None),
                            ('mu_classic_tab_init', [], None), ('mu_classic_state_text', [], ctypes.c_char_p)):
        fn = getattr(L, name)
        fn.argtypes = [ctypes.c_void_p] + args
        fn.restype = res
    ITEM_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)
    LNAME_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_void_p,
                                ctypes.c_size_t)
    MONEY_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_double, ctypes.c_void_p, ctypes.c_size_t)

    def lname(u, code, level, out, cap):
        b = item_level_name(code, level)[:cap - 1] + b'\0'
        ctypes.memmove(out, b, len(b))

    def mtext(u, zen, out, cap):
        b = money_text(zen)[:cap - 1] + b'\0'
        ctypes.memmove(out, b, len(b))
    fns = [ITEM_FN(lambda u, code, count, level: CENV.items.get((code, level & 0xff), 0)), LNAME_FN(lname),
           MONEY_FN(mtext)]
    nat.cb.extend(fns)
    nat.host.classic_item = ctypes.cast(fns[0], ctypes.c_void_p).value
    nat.host.item_level_name = ctypes.cast(fns[1], ctypes.c_void_p).value
    nat.host.money_text = ctypes.cast(fns[2], ctypes.c_void_p).value


def run_classic_data(m, nat, snap, cw, quest_bmd, fam):
    """The client's loader 0x009f4866 on the installed Quest.bmd, and the running client's records (snapshot),
    against libquest's decode."""
    cw.reset()
    client = m.read(cw.obj + 0x14, 200 * 1000)
    native = ctypes.string_at(ctypes.cast(nat.data.classic, ctypes.c_void_p), 200 * 1000)
    for r in range(200):
        fam.check(f'loader record {r}', client[r * 1000:(r + 1) * 1000], native[r * 1000:(r + 1) * 1000])
    try:
        live = snap.read(snap.u32(CSQ_PTR) + 0x14, 200 * 1000)
        for r in range(200):
            fam.check(f'live record {r}', live[r * 1000:(r + 1) * 1000], native[r * 1000:(r + 1) * 1000])
    except Exception as error:   # older snapshots without ptr:0x01d1e71c
        fam.examples.append({'note': f'no live classic records: {error}'})


def run_classic(m, nat, world, cw, rng, fam, sequences, length):
    L, c = nat.lib, nat.client
    saved = {a: m.stubs.pop(a) for a in (0x00a99ebe, 0x009f4c3f) if a in m.stubs}   # the real manager here
    try:
        classic_sequences(m, nat, world, cw, rng, fam, sequences, length, L, c)
    finally:
        m.stubs.update(saved)


def classic_sequences(m, nat, world, cw, rng, fam, sequences, length, L, c):
    rec = m.read(cw.obj + 0x14, 0) if False else None
    for seq in range(sequences):
        try:
            cw.reset()
            nat.reset()
            L.mu_classic_state(c, 0)          # creates the native manager (the client's exists)
            CENV.items, CENV.money, CENV.target, CENV.first = {}, 0, -1, 0
            records = m.read(cw.obj + 0x14, 200 * 1000)
            codes = []
            for r in range(200):
                b = records[r * 1000:(r + 1) * 1000]
                for k in range(16):
                    a = 0x28 + k * 0x28
                    if b[a + 1] == 1:
                        codes.append((struct.unpack_from('<H', b, a + 2)[0] * 0x200 + b[a + 4], b[a + 5],
                                      struct.unpack_from('<i', b, a + 8)[0]))
            monsters = sorted({struct.unpack_from('<H', records, r * 1000 + 0x28 + k * 0x28 + 2)[0]
                               for r in range(200) for k in range(16) if records[r * 1000 + 0x28 + k * 0x28 + 1] == 2})
            for step in range(length):
                world_ops = GuideOps(m, nat, world, [])
                world_ops.random_env(rng)
                # classes 0..7: a class without any allowed condition makes the client step the current quest below
                # 0 (0x009f436e) and read past the 200 records
                ENV.cls = rng.choice([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x10, 0x11, 0x21, 0x22])
                ENV.level = rng.choice([1, 50, 150, 200, 220, 280, 380, 400])
                ENV.total = ENV.level
                CENV.money = rng.choice([0, 100000, 3000000, 10**9])
                CENV.target = rng.choice([-1, -1, 0xe5, 0xeb, 0x10])
                CENV.first = rng.choice([0, 1])
                if rng.random() < 0.3:
                    for code, level, count in rng.sample(codes, min(len(codes), 4)):
                        CENV.items[(code, level)] = rng.choice([0, count, count + 1, max(0, count - 1)])
                cw.env()
                nat.env()
                nat.field('play_tabs', 1)
                L.mu_quest_client_field(c, b'money', 1, CENV.money)
                L.mu_quest_client_field(c, b'target_class', 1, CENV.target)
                L.mu_classic_set_first(c, CENV.first)
                L.mu_quest_client_field(c, b'wrap_scale_x1000', 1, 1000)
                op = rng.choice(['c0', 'c0', 'a1', 'a1', 'r86', 'r86', 'a4', 'f61c', 'answer', 'show', 'showtop', 'text', 'state',
                                 'kills', 'onload', 'wstate', 'open', 'close', 'choice', 'choice', 'complete', 'tab1'])
                label = f'classic seq {seq} step {step} {op}'
                extra = None
                o = cw.obj
                if op == 'c0':
                    n = rng.randint(0, 40)
                    states = bytes(rng.choice([0x00, 0xaa, 0xff, 0x55, 0x1b, 0xe4, rng.randint(0, 255)])
                                   for _ in range(n // 4 + 1))
                    pkt = b'\xc1' + bytes([4 + len(states)]) + b'\xc0' + bytes([n]) + states
                    buf = m.alloc(64 + len(pkt), define=True)
                    m.write(buf, pkt)
                    m.call(0x01278f3a, [buf])
                    L.mu_classic_receive_states(c, pkt, len(pkt))
                    extra = (m.read(world.hero + 0x29, 1)[0], nat.field('hero.flag29'))
                elif op == 'a1':
                    pkt = b'\xc1\x05\xa1' + bytes([rng.randint(0, 12), rng.randint(0, 255)])
                    buf = m.alloc(64, define=True)
                    m.write(buf, pkt)
                    m.call(0x0127a1db, [buf])
                    L.mu_classic_receive_state(c, pkt, len(pkt))
                elif op == 'r86':
                    pkt = b'\xc1\x06\x86' + bytes([rng.randint(0, 12), rng.choice([0, 0, 0, 2, 1]), rng.randint(0, 255)])
                    buf = m.alloc(64, define=True)
                    m.write(buf, pkt)
                    m.call(0x0127a0e0, [buf])
                    L.mu_classic_receive_result(c, pkt, len(pkt))
                elif op == 'a4':
                    pairs = b''.join(struct.pack('<ii', rng.choice(monsters + [-1]), rng.randint(0, 30)) for _ in range(5))
                    pkt = b'\xc1\x30\xa4\0\0\0\0\0' + pairs
                    buf = m.alloc(96, define=True)
                    m.write(buf, pkt)
                    m.call(0x01278f6c, [buf])
                    L.mu_classic_receive_kills(c, pkt, len(pkt))
                elif op == 'f61c':
                    k = rng.randint(0, 5)
                    cur = m.read(o + 0x30d86, 1)[0]
                    body = b''.join(struct.pack('<HBB', rng.choice(monsters), rng.randint(0, 30), 0) for _ in range(k))
                    pkt = b'\xc1' + bytes([6 + len(body)]) + b'\xf6\x1c' + bytes([rng.choice([cur, cur, 7]), k]) + body
                    buf = m.alloc(96, define=True)
                    m.write(buf, pkt)
                    m.call(0x0124cbb0, [buf])
                    L.mu_classic_receive_kill_list(c, pkt, len(pkt))
                elif op == 'answer':
                    a = rng.choice([0xff, 0xff, 1, 2, 3, 0])
                    r1 = m.call(0x009f4244, [a], ecx=o) & 0xff
                    r2 = L.mu_classic_answer(c, a) & 0xff
                    extra = (r1, r2)
                elif op == 'show':
                    q = rng.choice([-1, -1, rng.randint(0, 12)])
                    m.call(0x009f4cb2, [q & 0xffffffff], ecx=o)
                    L.mu_classic_show(c, q)
                elif op == 'showtop':
                    q = rng.choice([-1, rng.randint(0, 12)])
                    m.call(0x009f4c3f, [q & 0xffffffff], ecx=o)
                    L.mu_classic_show_top(c, q)
                elif op == 'text':
                    d = rng.randint(0, 260)
                    m.call(0x009f4fc8, [d], ecx=o)
                    L.mu_classic_text(c, d)
                elif op == 'state':
                    q = rng.randint(0, 40)
                    extra = ((m.call(0x009f4bf3, [q], ecx=o) & 0xff, m.call(0x009f4d91, [q], ecx=o) & 0xff),
                             (L.mu_classic_state_of(c, q), L.mu_classic_state(c, q)))
                elif op == 'kills':
                    mon = rng.choice(monsters + [0, 5])
                    extra = (i32(m.call(0x009f52fe, [mon], ecx=o)), L.mu_classic_kills(c, mon))
                elif op == 'onload':
                    m.call(0x00beb8b6, [], ecx=cw.njcq)
                    L.mu_classic_onload(c)
                elif op == 'wstate':
                    m.call(0x00bebd9f, [], ecx=cw.njcq)
                    L.mu_classic_window_state(c)
                elif op == 'open':
                    m.call(0x00bec39b, [], ecx=cw.njcq)
                    L.mu_classic_open(c)
                elif op == 'close':
                    m.call(0x00bec3f0, [], ecx=cw.njcq)
                    L.mu_classic_close(c)
                elif op == 'choice':
                    k = rng.choice([0, 0, 1, 2])
                    m.call(0x00bec46a, [k], ecx=cw.njcq)
                    L.mu_classic_choice(c, k)
                elif op == 'complete':
                    m.call(0x00becb32, [], ecx=cw.njcq)
                    L.mu_classic_complete(c)
                elif op == 'tab1':
                    m.call(0x00d4dd38, [], ecx=cw.tab1)
                    L.mu_classic_tab_init(c)
                if m.read(o + 0x30d86, 1)[0] >= 200:
                    # the client stepped the current quest below 0 (0x009f436e) and read past its records
                    # (zero slack here): not comparable, the sequence ends
                    COVERAGE['classic wrapped past quest 0'] = COVERAGE.get('classic wrapped past quest 0', 0) + 1
                    world.log.clear()
                    nat.clear_log()
                    break
                cl = [line for line in world.log]
                cover(cl)
                COVERAGE['classic op ' + op] = COVERAGE.get('classic op ' + op, 0) + 1
                nl = [line.encode('latin1') for line in nat.log()]
                world.log.clear()
                nat.clear_log()
                client = (cl, cw.state(), extra[0] if extra else None)
                native = (nl, L.mu_classic_state_text(c).decode('latin1'), extra[1] if extra else None)
                before = fam.mismatches
                fam.check(label, client, native)
                if fam.mismatches > before and len(fam.examples) <= 8:
                    fam.examples[-1] = {'case': label, 'diff': first_diff(client, native)}
        except cm.CaseError as error:
            fam.cases += 1
            fam.mismatches += 1
            fam.examples.append({'label': f'classic seq {seq}', 'error': str(error)})


def run_dialog_wrap(m, nat, world, steps, records, rng, fam, sequences, length):
    """npcdialogue's quest list 0x00be9c75 with the client's wrap (0x011ff794 into one 0x80-byte line at 500 px)
    instead of validate_quest.py's one-line model, a modelled GetTextExtentPointA on both sides."""
    ops = GuideOps(m, nat, world, steps)
    qops = vq.Ops(m, nat, world, records)
    keys = [r[0] for r in records]
    saved = m.stubs.pop(WRAP, None)
    try:
        for seq in range(sequences):
            start_quests(m, nat, world, ops, qops, records, rng)
            ENV.widths = {b: rng.randint(3, 12) for b in range(256)}
            scale = rng.choice([1.0, 1.5, 2.6875])
            m.write(0x06fbcd94, f32(scale))
            nat.lib.mu_quest_client_field(nat.client, b'wrap_scale_x1000', 1, int(scale * 1000))
            world.ptd = m.alloc(0x400, define=True)
            m.handlers['GetTextExtentPointA'] = lambda mm, words: (mm.write(words[3], struct.pack(
                '<ii', sum(ENV.widths.get(b, 7) for b in mm.read(words[1], words[2])), 12)), 1)[1]
            for step in range(length):
                if rng.random() < 0.7 or nat.field('dialog.list_mode') == 0:
                    qs = rng.sample(keys, rng.randint(0, 9))
                    world.flags[world.dlg] = True
                    nat.field('dialog.visible', 1)
                    qops.dialog_quests(qs)
                    label = f'dialog seq {seq} step {step} list {len(qs)}'
                else:
                    k = rng.randint(1, max(1, nat.field('dialog.options')))
                    qops.dialog_choice(k)
                    label = f'dialog seq {seq} step {step} choice {k}'
                compare(fam, label, m, nat, world)
    finally:
        if saved:
            m.stubs[WRAP] = saved


def ids_index(m, world, nlist):
    cur = i32(m.u32(world.guide + 0xc4))
    for k in range(nlist):
        if i32(m.u32(m.u32(world.guide + 0xcc) + k * STEP + 4)) == cur:
            return k
    return 0


def run_guide(m, nat, world, steps, rng, fam, sequences, length):
    ops = GuideOps(m, nat, world, steps)
    for seq in range(sequences):
        try:
            guide_case(m, nat, world, ops, rng, fam, seq, length, summary=True)
        except cm.CaseError as error:
            fam.cases += 1
            fam.mismatches += 1
            fam.examples.append({'label': f'seq {seq}', 'error': str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', required=True, help='langread snapshot with the guide tables (local)')
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--families', default='guide-data,guide,summary,move,wrap,dialog-wrap,classic-data,classic')
    parser.add_argument('--wrap-cases', type=int, default=2000)
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT', ''))
    parser.add_argument('--sequences', type=int, default=40)
    parser.add_argument('--length', type=int, default=30)
    parser.add_argument('--output')
    args = parser.parse_args()
    for path, digest in ((args.text, vl.TEXT_SHA256), (args.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    snap = plain.Snapshot.load(args.snapshot)
    rng = random.Random(args.seed)
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256, 'seed': args.seed, 'families': {}}
    m = vq.QuestMachine(text, data, snap)
    vq.install_stubs(m)
    steps = plain.read_guide(snap)
    records = plain.read_quests(snap)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        plain_dir = Path(tmp)/'plain'
        plain.convert(snap, plain_dir)
        nat = Native2(snap, plain_dir)
        world = World2(m, snap)
        world.summary_other = world.summary_blocked = 0
        vq.install_window_stubs(m, world)
        vq.install_more_stubs(m, world)
        install_guide_stubs(m, world)
        quest_bmd = (Path(args.game_root)/'Data/Local/quest.bmd').read_bytes()
        install_classic_stubs(m, world, quest_bmd)
        classic_native_setup(nat, quest_bmd)
        nat.reset()
        cw = ClassicWorld(m, world)
        runs = {
            'guide-data': lambda f: run_guide_data(m, nat, snap, f),
            'guide': lambda f: run_guide(m, nat, world, steps, rng, f, args.sequences, args.length),
            'summary': lambda f: run_summary(m, nat, world, steps, records, rng, f, args.sequences, args.length),
            'move': lambda f: run_move(m, nat, world, steps, records, rng, f, args.sequences, args.length),
            'wrap': lambda f: run_wrap(m, nat, rng, f, args.wrap_cases),
            'dialog-wrap': lambda f: run_dialog_wrap(m, nat, world, steps, records, rng, f, args.sequences,
                                                     args.length),
            'classic-data': lambda f: run_classic_data(m, nat, snap, cw, quest_bmd, f),
            'classic': lambda f: run_classic(m, nat, world, cw, rng, f, args.sequences, args.length),
        }
        for name in args.families.split(','):
            fam = vq.Family(name)
            try:
                runs[name](fam)
            except cm.CaseError as error:
                fam.examples.append({'error': str(error)})
                fam.mismatches += 1
            report['families'][name] = fam.summary()
            print(f'{name}: {fam.cases} cases, {fam.mismatches} mismatches ({time.time() - t0:.1f} s)', flush=True)
    report['coverage'] = dict(sorted(COVERAGE.items()))
    report['seconds'] = round(time.time() - t0, 1)
    text_out = json.dumps(report, indent=2, default=repr)
    if args.output:
        Path(args.output).write_text(text_out + '\n')
    bad = {k: v for k, v in report['families'].items() if v['mismatches']}
    if bad:
        print(json.dumps(bad, indent=2, default=repr)[:8000])
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
