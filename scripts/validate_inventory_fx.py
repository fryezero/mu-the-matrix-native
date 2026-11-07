#!/usr/bin/env python3
"""INVENTORY-FX: the inventory window's item render against the pinned client.

The Inventory frame's item render 0x00b913a2 runs the grid's slot pass 0x00ab6130, then draws the hero's equipment:
the ITEMs CharacterMachine [0x01d1df18] + 0x1b58 + s * 0x12c (s = 0..14) in the rectangles the movie reports
through EQUIPrequestSlotInfo (stored by 0x00b958e1), each through the slot wrapper 0x016c23d5. Every icon then
goes RenderItem3D -> RenderObjectScreen -> RenderPartObject -> RenderObjDraw like a ground item. Families:

* equip_pass  the client's 0x00b913a2 (its slot pass with no grid pages, the frame/scale/rate getters, the class
              rule 0x00b99205 and 0x0095f5cc executed) against reconstructed/hud mu_inventory_item_pass: return value
              and every slot-wrapper call (item, x, y, w, h bit for bit, the ten other words). Random screens,
              alignments 0..9, movie positions, scales, rates, slot rectangles (also unreported zero ones), item
              codes (-1 empty), hero class bytes, frame +0xcc, a null CharacterMachine and invisible frames.
* equip_info  0x00b958e1(slot, x, y, w, h) against mu_equip_slot_info: the 30 stored words after random calls,
              slots -3..18 and the int32 extremes.
* part_args   RenderPartObject's two RenderObjDraw call sequences (0x017e7932..0x017e7960, 0x017e796a..0x017e7997):
              arguments 5..7 are RenderObjectScreen's level word, excellent flag and set bits unchanged; native
              mu_icon_glow_of(ros) gives the renderchar level (word >> 3) & 15, the option and the ext byte of them.
* inv_flag    RenderObjDraw's flag for an icon: RenderPartObject's copy of the OBJECT +0x158 (the icon's screen
              position, z -100/-130/-140) into model +0x78 and RenderObjDraw's TestFrustrum2D store, against
              native/world/world_item_pre.h on the same position, with world polygons around the map and near
              its origin (where screen positions / 100 fall inside), scene states 6 and 5.
* sinks       static: the icon's chain of direct calls (0x00b913a2 -> slot wrapper -> RenderItem3D ->
              RenderObjectScreen -> RenderPartObject -> RenderObjDraw, whose 0x389c skin case calls CreateSprite);
              RenderSprites 0x0169270e, the only routine that draws the sprite list, has four call sites, all in the
              scene renders 0x018576b3, 0x01857ed9 and 0x0185916b, which only the frame driver (and 0x010b3963 for
              the main game) calls: icon sprites join the world's list and the world draws them. The other two
              RenderObjDraw sites (0x00a497c6/0x00a49bc9) lie in 0x00a49266, the render callback 0x00a16273
              registers for object type 0x67a at 0x00a13f54, not an inventory path.

--mutations compiles planted mistakes into reconstructed/hud's item_slots.c (separately) and requires each to be
caught, with every anchor matching exactly once.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import POINTER, Structure, c_float, c_int, c_int32, c_uint8, c_uint16, c_uint32, c_void_p
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402
import validate_item_callers as ic  # noqa: E402

INVENTORY_PASS, EQUIP_INFO, WRAPPER = 0x00b913a2, 0x00b958e1, 0x016c23d5
CHARACTER_MACHINE, HERO = 0x01d1df18, 0x0a39d754
SCREEN_W, SCREEN_H = 0x01cf1624, 0x01cf1628
OP_NEW, OP_NEW_ARRAY, OP_DELETE, OP_DELETE_ARRAY = 0x0191ba7b, 0x0191bab9, 0x0191baab, 0x0191bac2
MEMSET, MEMMOVE, MEMCPY = 0x0194cd00, 0x0194c200, 0x0194c780
SECURITY_COOKIE = 0x01cf65c0
STOPS = {0xac3bf7, 0xaadd42, 0xaaeadc, WRAPPER, 0xc94193, 0xad86dc, 0xadaccf, 0xc06911, 0xccc51e,
         OP_NEW, OP_NEW_ARRAY, OP_DELETE, OP_DELETE_ARRAY, MEMSET, MEMMOVE, MEMCPY}
PART_SEQUENCES = ((0x017e7932, 0x017e7960), (0x017e796a, 0x017e7997))
RENDER_OBJ_DRAW, CREATE_SPRITE, RENDER_SPRITES = 0x0176ce74, 0x01692eb7, 0x0169270e
SCENE_RENDERS = (0x018576b3, 0x01857ed9, 0x0185916b)
UI_SITES, UI_CALLBACK, UI_REGISTER = (0x00a497c6, 0x00a49bc9), 0x00a49266, 0x00a13f54
HUD = ROOT / 'reconstructed/hud'
# validate_item_callers' flag library sources (literal here so the affected-input analysis can read them)
TERRAIN = ['reconstructed/terrain/terrain.c', 'reconstructed/terrain/world_haze.c',
           'reconstructed/record-math/record_math.c']
HUD_SOURCES = ['inv_grid.c', 'item_slots.c', 'item_pass.c', 'tooltip_html.c', 'tooltip_format.c', '../ui/ui2d.c']
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
SCREENS = [(640, 480), (800, 600), (1024, 768), (1280, 800), (1366, 768), (1600, 1000), (1722, 1048), (1920, 1080),
           (2560, 1440)]
MUTANTS = {
    'rate_swap': ('float y = (fy + frame->scale * slots[s].y) * rate_y;',
                  'float y = (fy + frame->scale * slots[s].y) * rate_x;'),
    'scale_order': ('float w = rate_x * slots[s].w * frame->scale;', 'float w = rate_x * (slots[s].w * frame->scale);'),
    'armour_slot': ('if (s == 3 && mu_equip_short_armour(hero_class))', 'if (s == 2 && mu_equip_short_armour(hero_class))'),
    'armour_factor': ('h = h * 0.75f;', 'h = h * 0.7f;'),
    'class_set': ('case 2: case 5: case 7: case 8: case 9: case 12: case 14:', 'case 2: case 5: case 7: case 8: case 9: case 12:'),
    'class_nibble': ('switch (class_byte & 0xf) {', 'switch (class_byte & 0x1f) {'),
    'a20': ('const uint8_t a20 = frame_cc == 1;', 'const uint8_t a20 = frame_cc != 0;'),
    'empty': ('if (codes[s] < 0)\n            continue;', 'if (codes[s] <= 0)\n            continue;'),
    'no_machine': ('if (!codes)\n        return 1;', 'if (!codes)\n        return 0;'),
    'info_bound': ('if (slot >= MU_EQUIP_SLOTS || slot < 0)', 'if (slot > MU_EQUIP_SLOTS || slot < 0)'),
    'info_swap': ('slots[slot].w = w;\n    slots[slot].h = h;', 'slots[slot].w = h;\n    slots[slot].h = w;'),
    'glow_shift': ('{(ros->level_word >> 3) & 15,', '{(ros->level_word >> 2) & 15,'),
    'glow_mask': ('{(ros->level_word >> 3) & 15,', '{(ros->level_word >> 3) & 7,'),
    'glow_swap': ('ros->excellent, ros->set_bits};', 'ros->set_bits, ros->excellent};'),
}

F = cm.fbits


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class SlotPage(Structure):
    _fields_ = [('grid', c_void_p), ('x', c_float), ('y', c_float), ('cell_w', c_float), ('cell_h', c_float),
                ('gap_x', c_float), ('gap_y', c_float)]


class SlotFrame(Structure):
    _fields_ = [('visible', c_int), ('align', c_int32), ('movie_x', c_float), ('movie_y', c_float),
                ('alpha', c_float), ('scale', c_float), ('pages', POINTER(SlotPage)), ('page_count', c_int32),
                ('frame_id', c_uint32)]


class EquipSlot(Structure):
    _fields_ = [('x', c_float), ('y', c_float), ('w', c_float), ('h', c_float)]


class EquipCall(Structure):
    _fields_ = [('slot', c_int32), ('x', c_float), ('y', c_float), ('w', c_float), ('h', c_float), ('a20', c_uint8),
                ('frame_id', c_uint32)]


class RosOut(Structure):
    _fields_ = [('drawn', c_int32), ('spin', c_int32), ('spin_angle', c_float), ('pose_model', c_int32),
                ('render_type', c_int32), ('height', c_float), ('action', c_uint16), ('anim_frame', c_float),
                ('anim_prior_frame', c_float), ('anim_prior_action', c_uint16), ('ticked', c_int32),
                ('tick_speed', c_float), ('position', c_float * 3), ('scale', c_float), ('alpha', c_float),
                ('light', c_float * 3), ('lighting', c_uint8), ('level_word', c_int32), ('excellent', c_int32),
                ('set_bits', c_int32), ('a2c', c_int32), ('a30', c_int32)]


class IconGlow(Structure):
    _fields_ = [('level', c_int32), ('option', c_int32), ('ext', c_int32)]


COLORFN = ctypes.CFUNCTYPE(None, c_void_p, c_float, c_float, c_float, c_float)
EMITFN = ctypes.CFUNCTYPE(None, c_void_p, c_void_p)
EQUIPFN = ctypes.CFUNCTYPE(None, c_void_p, POINTER(EquipCall))


def build_hud(source_dir: Path, out: Path):
    result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                             '-ffp-contract=off', '-fno-fast-math', '-shared', *HUD_SOURCES, '-o', str(out)],
                            cwd=source_dir, capture_output=True, text=True)
    if result.returncode:
        return None, result.stderr[-2000:]
    lib = ctypes.CDLL(str(out))
    lib.mu_inventory_item_pass.restype = c_int
    lib.mu_inventory_item_pass.argtypes = [POINTER(SlotFrame), POINTER(EquipSlot), POINTER(c_int32), c_uint8,
                                           c_int32, c_int32, c_int32, c_float, c_float, COLORFN, EMITFN, EQUIPFN,
                                           c_void_p]
    lib.mu_equip_slot_info.restype = c_int
    lib.mu_equip_slot_info.argtypes = [POINTER(EquipSlot), c_int32, c_float, c_float, c_float, c_float]
    lib.mu_icon_glow_of.restype = IconGlow
    lib.mu_icon_glow_of.argtypes = [POINTER(RosOut)]
    return lib, None


def rand_float(g, lo, hi, step=None):
    v = g.uniform(lo, hi)
    if step:
        v = round(v / step) * step
    return f32(v)


# ---- equip_pass / equip_info: the client machine ------------------------------------------------------------

class Machine:
    def __init__(self, text, data):
        self.text = text
        self.m = cm.Machine(text, data)
        import validate_hud as vh
        functions, noreturn = vh.closure(text, (INVENTORY_PASS, EQUIP_INFO), STOPS)
        for start, end in functions.items():
            self.m.allow((start, end))
        for start in noreturn:
            self.m.stub(start, lambda mm, s=start: mm.fail(f'client throw helper {s:#x} reached'))
        self.m.allow((0x0191d71e, 0x0191d721))
        self.functions = functions

    def reset(self):
        self.m.reset()
        self.m.put32(SECURITY_COOKIE, 0xbb40e64e)


def equip_pass_family(machine, lib, cases, seed):
    g = random.Random(seed)
    m = machine.m
    fam = {'cases': 0, 'mismatches': 0, 'calls': 0, 'short_armour': 0, 'invisible': 0, 'no_machine': 0}
    first = None
    for case in range(cases):
        machine.reset()
        sw, sh = g.choice(SCREENS)
        m.put32(SCREEN_W, sw)
        m.put32(SCREEN_H, sh)
        gfx = m.alloc(0x300, define=True)
        rate_x, rate_y = f32(640.0 / sw), f32(480.0 / sh)
        m.putf(gfx + 0x2cc, rate_x)
        m.putf(gfx + 0x2d0, rate_y)
        m.stub(0xac3bf7, lambda mm: gfx, 0)
        visible = 1 if g.random() < 0.95 else 0
        align = g.randrange(10)
        m.stub(0xaadd42, lambda mm: visible, 0)
        m.stub(0xaaeadc, lambda mm: align, 0)
        frame = m.alloc(0x200, define=True)
        movie_x, movie_y = rand_float(g, -200, 1100, 0.25), rand_float(g, -200, 800, 0.25)
        alpha = rand_float(g, 0, 1)
        scale = g.choice([f32(1.0), f32(0.83), rand_float(g, 0.5, 2.0)])
        cc = g.choice([0, 1, 1, 2, -1, 0x101])
        m.putf(frame + 0x50, alpha)
        m.putf(frame + 0x58, scale)
        m.putf(frame + 0x70, movie_x)
        m.putf(frame + 0x74, movie_y)
        m.put32(frame + 0x78, 0)       # no grid pages: the equipment loop alone
        m.put32(frame + 0x7c, 0)
        m.put32(frame + 0xcc, cc & 0xffffffff)
        slots = (EquipSlot * 15)()
        for s in range(15):
            if g.random() < 0.1:
                geo = (0.0, 0.0, 0.0, 0.0)
            else:
                geo = (rand_float(g, -20, 400, 0.5), rand_float(g, -20, 500, 0.5), rand_float(g, 10, 90, 0.25),
                       rand_float(g, 10, 130, 0.25))
            slots[s] = EquipSlot(*geo)
            m.write(frame + 0x110 + s * 8, struct.pack('<2f', geo[0], geo[1]))
            m.write(frame + 0x188 + s * 8, struct.pack('<2f', geo[2], geo[3]))
        has_machine = g.random() < 0.95
        codes = (c_int32 * 15)()
        machine_c = 0
        if has_machine:
            machine_c = m.alloc(0x1b58 + 15 * 0x12c, define=True)
            for s in range(15):
                code = -1 if g.random() < 0.3 else g.choice([g.randrange(0, 0x2c00), 0, g.randrange(-5, 0),
                                                               0x7fffffff])
                codes[s] = code
                m.put32(machine_c + 0x1b58 + s * 0x12c + 0x10, code & 0xffffffff)
        m.put32(CHARACTER_MACHINE, machine_c)
        hero = m.alloc(0x40, define=True)
        hero_class = g.randrange(256)
        m.write(hero + 0x12, bytes([hero_class]))
        m.put32(HERO, hero)
        calls_c = []
        m.stub(WRAPPER, lambda mm: (calls_c.append(tuple(mm.args(16))), 0)[1], 0)
        rc = m.call(INVENTORY_PASS, (), ecx=frame) & 0xff
        stream_c = []
        for w in calls_c:
            slot = (w[0] - machine_c - 0x1b58) // 0x12c if machine_c else '?'
            stream_c.append((slot,) + tuple(w[1:]))
        stream_a = []

        def emit(user, call):
            c = call.contents
            stream_a.append((c.slot, F(c.x), F(c.y), F(c.w), F(c.h), 0, c.a20, 0, 0, c.frame_id, 0, F(0.0),
                             0xffffffff, 0, 1, 0))
        fa = SlotFrame(visible, align, movie_x, movie_y, alpha, scale, None, 0, frame)
        ef = EQUIPFN(emit)
        ra = lib.mu_inventory_item_pass(ctypes.byref(fa), slots, codes if has_machine else None, hero_class, cc, sw,
                                        sh, rate_x, rate_y, COLORFN(0), EMITFN(0), ef, None)
        fam['cases'] += 1
        fam['calls'] += len(stream_c)
        fam['invisible'] += int(not visible)
        fam['no_machine'] += int(not has_machine)
        fam['short_armour'] += int(any(c[0] == 3 for c in stream_c) and (hero_class & 15) in (2, 5, 7, 8, 9, 12, 14))
        if rc != ra or stream_c != stream_a:
            fam['mismatches'] += 1
            if first is None:
                diff = next(((k, x, y) for k, (x, y) in enumerate(zip(stream_c, stream_a)) if x != y), None)
                first = {'case': case, 'rc': [rc, ra], 'lengths': [len(stream_c), len(stream_a)],
                         'first_difference': diff}
    if first:
        fam['first_mismatch'] = first
    return fam


def equip_info_family(machine, lib, cases, seed):
    g = random.Random(seed + 1)
    m = machine.m
    fam = {'cases': 0, 'mismatches': 0, 'stored': 0}
    first = None
    for case in range(cases):
        machine.reset()
        ctrl = m.alloc(0x200, define=True)
        start = [rand_float(g, -1000, 1000) for _ in range(60)]
        m.write(ctrl + 0x110, struct.pack('<30f', *start[:30]))
        m.write(ctrl + 0x188, struct.pack('<30f', *start[30:]))
        # one spare element: a mutant that stores slot 15 must not write outside the array
        mine = (EquipSlot * 16)(*[EquipSlot(start[2 * s], start[2 * s + 1], start[30 + 2 * s], start[31 + 2 * s])
                                  for s in range(15)])
        spare = bytes(mine[15])
        stored = stores_c = 0
        for _ in range(g.randrange(1, 6)):
            slot = g.choice([g.randrange(-3, 19), g.randrange(0, 15), -2 ** 31, 2 ** 31 - 1, 15, 14, 0, -1])
            x, y, w, h = (rand_float(g, -500, 2000, g.choice([None, 0.25])) for _ in range(4))
            before = m.read(ctrl, 0x200)
            m.call(EQUIP_INFO, (slot & 0xffffffff, F(x), F(y), F(w), F(h)), ecx=ctrl)
            stores_c += int(m.read(ctrl, 0x200) != before)   # the client stored this call
            stored += lib.mu_equip_slot_info(mine, slot, x, y, w, h)
        if stores_c != stored or bytes(mine[15]) != spare:
            fam['mismatches'] += 1
            if first is None:
                first = {'case': case, 'client_stores': stores_c, 'c_stores': stored}
        words_c = struct.unpack('<30I', m.read(ctrl + 0x110, 120)) + struct.unpack('<30I', m.read(ctrl + 0x188, 120))
        words_a = tuple(F(v) for s in range(15) for v in (mine[s].x, mine[s].y)) + \
            tuple(F(v) for s in range(15) for v in (mine[s].w, mine[s].h))
        fam['cases'] += 1
        fam['stored'] += stored
        if words_c != words_a:
            fam['mismatches'] += 1
            if first is None:
                k = next(i for i, (a, b) in enumerate(zip(words_c, words_a)) if a != b)
                first = {'case': case, 'word': k, 'client': words_c[k], 'c': words_a[k]}
    if first:
        fam['first_mismatch'] = first
    return fam


# ---- part_args / inv_flag: the light Unicorn of validate_item_callers -----------------------------------------

def part_args_family(client, lib, cases, seed):
    g = random.Random(seed + 2)
    uc, x86 = client.uc, client.x86
    fam = {'cases': 0, 'mismatches': 0, 'levels': {}}
    first = None
    ebp = client.FRAME
    for case in range(cases):
        args = [g.getrandbits(32) for _ in range(16)]
        word = g.choice([g.randrange(0, 128), g.getrandbits(32), (g.randrange(16) << 3) | g.randrange(8),
                         0x84 | (g.randrange(16) << 3) | 3])
        exc, setb = g.choice([0, 1, g.getrandbits(32)]), g.choice([0, g.randrange(256), g.getrandbits(32)])
        args[5], args[6], args[7] = word, exc, setb      # [ebp+0x1c], +0x20, +0x24
        uc.mem_write(ebp + 8, struct.pack('<16I', *args))
        ros = RosOut()
        ros.level_word, ros.excellent, ros.set_bits = (ctypes.c_int32(word).value, ctypes.c_int32(exc).value,
                                                       ctypes.c_int32(setb).value)
        glow = lib.mu_icon_glow_of(ctypes.byref(ros))
        for start, call in PART_SEQUENCES:
            fam['cases'] += 1
            error = client.run(start, call, client.STACK + 0x20000, ebp)
            esp = uc.reg_read(x86.UC_X86_REG_ESP)
            pushed = struct.unpack('<13I', uc.mem_read(esp, 52)) if error is None else None
            ok = (pushed is not None and pushed[4] == word and pushed[5] == exc and pushed[6] == setb and
                  (glow.level, glow.option & 0xffffffff, glow.ext & 0xffffffff) == ((pushed[4] >> 3) & 15, pushed[5],
                                                                                   pushed[6]))
            level = (word >> 3) & 15
            fam['levels'][level] = fam['levels'].get(level, 0) + 1
            if not ok:
                fam['mismatches'] += 1
                if first is None:
                    first = {'case': case, 'start': hex(start), 'error': error, 'word': word,
                             'pushed': list(pushed[4:7]) if pushed else None,
                             'c': [glow.level, glow.option, glow.ext]}
    fam['levels'] = dict(sorted(fam['levels'].items()))
    if first:
        fam['first_mismatch'] = first
    return fam


def icon_polygon(g):
    xs, ys = ic.polygon(g)
    if g.random() < 0.5:   # near the map origin, where an icon's screen position / 100 can fall inside
        dx, dy = g.uniform(-30, 5) - min(xs), g.uniform(-30, 5) - min(ys)
        xs, ys = [f32(x + dx) for x in xs], [f32(y + dy) for y in ys]
    return xs, ys


def icon_positions(g, xs, ys, count):
    out = []
    for k in range(count):
        z = g.choice([-100.0, -130.0, -140.0, f32(g.uniform(-200, 0))])
        if k % 5 == 0:   # the polygon's own region in screen units, also on its edges
            x, y = g.uniform(min(xs) - 3, max(xs) + 3) * 100.0, g.uniform(min(ys) - 3, max(ys) + 3) * 100.0
        elif k % 5 == 1:
            out.extend(o for o in ic.origins(g, xs, ys, 1))
            continue
        else:
            x, y = g.uniform(0, 2560), g.uniform(0, 1440)
        out.append((f32(x), f32(y), f32(z)))
    return out[:count]


def inv_flag_family(client, flag_lib, cases, seed):
    g = random.Random(seed + 3)
    fam = {'cases': 0, 'mismatches': 0, 'clear': 0, 'set': 0, 'copy_mismatches': 0}
    first = None
    per_polygon = 30
    for start in range(0, cases, per_polygon):
        xs, ys = icon_polygon(g)
        state = 6 if g.random() < 0.8 else 5
        client.setup(xs, ys, state)
        for position in icon_positions(g, xs, ys, min(per_polygon, cases - start)):
            junk = tuple(f32(g.uniform(-1e4, 1e4)) for _ in range(3))
            mine = 0 if flag_lib.shim_out_of_view(ic.farr(xs), ic.farr(ys), ic.farr(list(position))) else 1
            fam['cases'] += 1
            error = client.part_copy(position, junk)
            if error or not ic.same_bits(client.vec(ic.Client.MODEL + 0x78), position):
                fam['copy_mismatches'] += 1
            got, error = client.flag(ic.Client.OBJ)
            fam['clear'] += int(got == 0)
            fam['set'] += int(got == 1)
            if error or got != mine:
                fam['mismatches'] += 1
                if first is None:
                    first = {'xs': xs, 'ys': ys, 'state': state, 'position': list(position), 'client': got,
                             'c': mine, 'error': error}
    fam['mismatches'] += fam['copy_mismatches']
    if first:
        fam['first_mismatch'] = first
    return fam


# ---- sinks: static ------------------------------------------------------------------------------------------

def direct_callers(text, target):
    out = []
    for off in range(len(text) - 5):
        if text[off] == 0xe8 and (cm.TEXT_BASE + off + 5 + struct.unpack_from('<i', text, off + 1)[0]) & 0xffffffff \
                == target:
            out.append(cm.TEXT_BASE + off)
    return out


CHAIN = ((0x00b915ec, WRAPPER, 'the inventory item render calls the slot wrapper'),
         (0x016c2681, 0x016c154e, 'the slot wrapper calls RenderItem3D'),
         (0x016c23bd, 0x016c2d82, 'RenderItem3D calls RenderObjectScreen'),
         (0x016c33d1, 0x017e63f4, 'RenderObjectScreen calls RenderPartObject'),
         (0x017e7960, RENDER_OBJ_DRAW, 'RenderPartObject calls RenderObjDraw (first)'),
         (0x017e7997, RENDER_OBJ_DRAW, 'RenderPartObject calls RenderObjDraw (second)'),
         (0x017701f9, CREATE_SPRITE, 'RenderObjDraw\'s 0x389c/0x389d skin case (0x0176ffe3) calls CreateSprite'))
SCENE_CALLERS = {0x018576b3: (0x0185254b,), 0x01857ed9: (0x0185253a,), 0x0185916b: (0x010b3ab8, 0x018525bb)}


def call_target(text, site):
    off = site - cm.TEXT_BASE
    if text[off] != 0xe8:
        return None
    return (site + 5 + struct.unpack_from('<i', text, off + 1)[0]) & 0xffffffff


def prologues(text, lo, hi):
    out, off = [], lo - cm.TEXT_BASE
    while True:
        off = text.find(b'\x55\x8b\xec', off, hi - cm.TEXT_BASE)
        if off < 0:
            return out
        out.append(cm.TEXT_BASE + off)
        off += 1


def sinks_family(text):
    """Static: the icon's draw chain, and where sprites are drawn. CreateSprite only appends to the global sprite
    list; RenderSprites, the only routine that draws it, is called from the three scene renders alone, which the
    frame driver 0x01851d39 (and 0x010b3963 for the main game) calls: no icon path draws a sprite."""
    checks = [(f'{label} ({site:#010x} -> {target:#010x})', call_target(text, site) == target)
              for site, target, label in CHAIN]
    sites = direct_callers(text, RENDER_SPRITES)
    checks.append(('RenderSprites 0x0169270e has four direct call sites', len(sites) == 4))
    owners = {}
    for site in sites:
        owner = max((s for s in SCENE_RENDERS if s <= site), default=None)
        owners[f'{site:#010x}'] = f'{owner:#010x}' if owner else None
        # no other function prologue between the scene render's entry and the call site
        checks.append((f'RenderSprites call {site:#010x} lies in scene render {owner:#010x}' if owner else
                       f'RenderSprites call {site:#010x} lies in a scene render',
                       owner is not None and prologues(text, owner + 1, site) == []))
    for render, expected in SCENE_CALLERS.items():
        checks.append((f'scene render {render:#010x} is called only from {", ".join(f"{c:#010x}" for c in expected)}',
                       tuple(direct_callers(text, render)) == expected))
    ui_owner = {s: max(a for a in (UI_CALLBACK, 0x00a49bf4) if a <= s) for s in UI_SITES}
    checks.append(('0x00a497c6/0x00a49bc9 lie in 0x00a49266 (before 0x00a49bf4)',
                   all(v == UI_CALLBACK and prologues(text, UI_CALLBACK + 1, s) == [] for s, v in ui_owner.items())))
    register = struct.unpack_from('<I', text, UI_REGISTER + 1 - cm.TEXT_BASE)[0]
    register_type = struct.unpack_from('<I', text, UI_REGISTER + 6 - cm.TEXT_BASE)[0]
    checks.append(('0x00a13f54 passes 0x00a49266 for object type 0x67a to 0x00a16273',
                   text[UI_REGISTER - cm.TEXT_BASE] == 0x68 and register == UI_CALLBACK and register_type == 0x67a and
                   call_target(text, UI_REGISTER + 10) == 0x00a16273))
    return {'cases': len(checks), 'mismatches': sum(not ok for _, ok in checks), 'render_sprites_sites': owners,
            'checks': [{'check': c, 'ok': bool(ok)} for c, ok in checks]}


# ---- driver -------------------------------------------------------------------------------------------------

def families_for(machine, client, lib, flag_lib, args, text=None):
    fams = {'equip_pass': equip_pass_family(machine, lib, args.cases, args.seed),
            'equip_info': equip_info_family(machine, lib, max(1, args.cases // 3), args.seed),
            'part_args': part_args_family(client, lib, max(1, args.cases // 6), args.seed),
            'inv_flag': inv_flag_family(client, flag_lib, args.cases, args.seed)}
    if text is not None:
        fams['sinks'] = sinks_family(text)
    return fams


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=3000, help='equip_pass and inv_flag cases (equip_info a third, '
                                                                 'part_args a sixth, two sequences each)')
    parser.add_argument('--seed', type=int, default=0x1f7e0001)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--text')
    parser.add_argument('--data')
    args = parser.parse_args(argv)
    started = time.time()
    text = pins.TEXT.read(args.text, exit=True)
    data = pins.DATA.read(args.data, exit=True)
    work = Path(tempfile.mkdtemp(prefix='inventory-fx-'))
    try:
        objects = []
        for src in TERRAIN:
            obj = work / (Path(src).stem + '.o')
            result = subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-c', str(ROOT / src),
                                     '-o', str(obj)], capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(f'{src}: {result.stderr[-2000:]}')
            objects.append(obj)
        flag_lib, error = ic.build_c(work, ROOT, objects, 'inventory_flag')
        if flag_lib is None:
            raise SystemExit(error)
        lib, error = build_hud(HUD, work / f'libinvfx.{SUFFIX}')
        if lib is None:
            raise SystemExit(error)
        machine = Machine(text, data)
        client = ic.Client(text, data)
        families = families_for(machine, client, lib, flag_lib, args, text)
        report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'seed': args.seed,
                  'families': families}
        if args.mutations:
            source = (HUD / 'item_slots.c').read_text()
            results = {}
            for name, (old, new) in MUTANTS.items():
                count = source.count(old)
                if count != 1:
                    raise SystemExit(f'mutant {name}: anchor matches {count} times, expected exactly once')
                tree = work / f'm_{name}'
                shutil.copytree(ROOT / 'reconstructed/hud', tree / 'hud')
                shutil.copytree(ROOT / 'reconstructed/ui', tree / 'ui')
                (tree / 'hud/item_slots.c').write_text(source.replace(old, new))
                mlib, error = build_hud(tree / 'hud', work / f'libm_{name}.{SUFFIX}')
                if mlib is None:
                    raise SystemExit(f'mutant {name} does not compile: {error}')
                fam = families_for(machine, client, mlib, flag_lib, args)
                results[name] = sum(f['mismatches'] for f in fam.values())
            report['mutants'] = results
    finally:
        shutil.rmtree(work, ignore_errors=True)
    report['seconds'] = round(time.time() - started, 1)
    bad = sum(f['mismatches'] for f in report['families'].values())
    missed = [k for k, v in report.get('mutants', {}).items() if not v]
    report['ok'] = not bad and not missed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + '\n')
    summary = {k: {'cases': v['cases'], 'mismatches': v['mismatches']} for k, v in report['families'].items()}
    print(json.dumps({'families': summary, 'mutants': report.get('mutants'), 'seconds': report['seconds']}))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
