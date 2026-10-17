#!/usr/bin/env python3
"""Compare the reconstructed window/widget layer with the client (NATIVE-UI-002).

Every case runs actual client code in Unicorn over the pinned restored text
and second image section (scripts/client_ui_machine.py) and the
reconstruction in reconstructed/ui through ctypes, then compares:

* the streams of platform calls (OpenGL, GDI, sounds, client events) word
  for word, floats by bit pattern and texture uploads by SHA-256;
* the objects' state (every sprite corner, texture coordinate, frame,
  button state, window rectangle, list counter and notice-box row),
  read from the client's objects at the client offsets and from the
  reconstruction through reconstructed/ui/ui_probe.c.

Client code run unmodified: CServerSelWin's constructor 0x01075387, Create
0x01075554, SetPosition 0x0107592f, UpdateDisplay 0x01075bc2 and its helpers,
CursorInWin 0x010760d4, UpdateWhileActive 0x01076a24, RenderControls
0x01076c1e; CWin (vtable 0x01ac7468), CWinEx (vtable 0x01ac74a4), CButton,
CSprite (frames, PtInSprite), CGaugeBar, the client's pointer list, the text
facade and CUIRenderTextOriginal (RenderText/WriteText/UploadText), the C
runtime's array constructor iterator and CutText 0x01859f23.

Modelled explicitly (not client code): CInput (cursor, button edges, screen
size), the server list (CServerListManager and its groups and servers as
synthetic objects behind the manager's accessor functions), GlobalText,
operator new/delete, memset/memcpy/strlen/strcpy/_mbclen, PtInRect/SetRect,
GDI text metrics (UI-001's synthetic font), the texture table lookups,
and the sound, packet and connect calls (recorded as markers).  One
instruction site is modelled: the pinned capture has a runtime patch at
0x01076018 (a jump out of the image, from a protection or customisation
module); the case executes the original instruction it replaced, read from
the bytes left behind (movzx eax, byte [server+0x14]).
"""
import argparse
import ctypes
from ctypes import (CFUNCTYPE, POINTER, Structure, c_char, c_double, c_int, c_int32, c_size_t, c_uint8, c_uint32,
                    c_void_p, c_char_p)
import json
import os
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import model_hierarchy_common as common  # noqa: E402
import validate_ui as vu  # noqa: E402

F = cm.fbits
OPS = vu.OPS + ['SelectObject', 'Sound', 'Event']

# --------------------------------------------------------------------------
# ctypes view of the new reconstruction

GLOBALTEXTFN = CFUNCTYPE(c_void_p, c_void_p, c_int32)


class Input(Structure):
    _fields_ = [('cursor_x', c_int32), ('cursor_y', c_int32), ('lbutton_down', c_uint8), ('lbutton_up', c_uint8),
                ('screen_width', c_int32), ('screen_height', c_int32)]


class Fonts(Structure):
    _fields_ = [('normal', c_uint32), ('bold', c_uint32), ('big', c_uint32), ('fixed', c_uint32)]


class Ctx(Structure):
    _fields_ = [('state', c_void_p), ('text', c_void_p), ('input', Input), ('fonts', Fonts), ('held_button', c_void_p),
                ('global_text', GLOBALTEXTFN), ('global_text_user', c_void_p)]


class Server(Structure):
    _fields_ = [('slot', c_int32), ('percent', c_int32), ('type', c_uint8), ('name', c_char*64)]


class Group(Structure):
    _fields_ = [('id', c_int32), ('type', c_uint8), ('position', c_int32), ('button', c_int32), ('name', c_char*64),
                ('description', c_char*256), ('server_count', c_int), ('servers', Server*20)]


class ServerList(Structure):
    _fields_ = [('group_count', c_int), ('groups', Group*64), ('notice', c_char*256)]


def library(path=None):
    lib = vu.library(path)
    P = c_void_p
    sigs = {
        'mu_ui_probe_sizeof': ([c_int], c_size_t),
        'mu_ui_probe_sprite': ([P, P], c_int), 'mu_ui_probe_button': ([P, P], c_int),
        'mu_ui_probe_win': ([P, P], c_int), 'mu_ui_probe_winex': ([P, P], c_int),
        'mu_ui_probe_server_win': ([P, P], c_int), 'mu_ui_probe_held': ([P, P], c_int32),
        'mu_ui_probe_select': ([P, c_int32], None),
        'mu_ui_server_win_init': ([P, P], None), 'mu_ui_server_win_create': ([P, P], None),
        'mu_ui_server_win_set_position': ([P, P, c_int32, c_int32], None),
        'mu_ui_server_win_update_display': ([P, P], None),
        'mu_ui_server_win_cursor_in_win': ([P, P, c_int32], c_int),
        'mu_ui_win_update': ([P, P, c_double], None), 'mu_ui_win_render': ([P, P], None),
        'mu_ui_win_show': ([P, P, c_int], None), 'mu_ui_win_set_active': ([P, c_int], None),
        'mu_ui_winex_init': ([P], None), 'mu_ui_winex_create': ([P, P, P, c_int32, c_int32], None),
        'mu_ui_winex_set_line': ([P, c_int32], c_int32),
        'mu_ui_cut_text': ([c_char_p, P, c_int32, c_int32], c_int32),
        'mu_ui_sprite_init': ([P], None),
        'mu_ui_sprite_create_frames': ([P, P, c_int32, c_int32, c_int32, c_int32, P, c_int32, c_int32, c_int, c_int32,
                                        ctypes.c_float, ctypes.c_float], None),
        'mu_ui_sprite_set_action': ([P, c_int32, c_int32, c_double, c_int], None),
        'mu_ui_sprite_set_now_frame': ([P, c_int32], None),
        'mu_ui_sprite_update': ([P, c_double], None),
        'mu_ui_sprite_contains': ([P, c_int32, c_int32], c_int),
        'mu_ui_winex_set_position': ([P, P, c_int32, c_int32], None), 'mu_ui_winex_show': ([P, P, c_int], None),
        'mu_ui_winex_render': ([P, P], None),
    }
    for name, (args, res) in sigs.items():
        getattr(lib, name).argtypes = args
        getattr(lib, name).restype = res
    return lib


class Authored(vu.Authored):
    """The reconstruction with a recording sink that also knows the UI-002 ops."""

    def _record(self, user, op, words, count, data, size):
        values = [words[i] for i in range(count)]
        name = OPS[op]
        if name == 'glTexImage2D':
            import hashlib
            values[8] = hashlib.sha256(ctypes.string_at(data, size) if data else b'').hexdigest()
        elif name in ('TextOut', 'GetTextExtent'):
            values.append(ctypes.string_at(data, size).decode('latin1'))
        self.calls.append((name, tuple(values)))


def normalize(calls):
    out = []
    for name, words in calls:
        if name in ('PtInRect', 'SetRect', 'IsBadReadPtr'):
            continue
        if name == 'SelectObject':
            out.append(('SelectObject', (words[1],)))
            continue
        out.extend(vu.normalize_client([(name, words)]))
    return out


def normalize_authored(calls):
    out = []
    for name, words in calls:
        if name == 'Event':
            code, argument = words
            if code == 1:
                out += [('Packet', ()), ('SendRequest', ())]
            elif code == 3:
                out.append(('HideWin', ()))
            elif code == 2:
                out.append(('Connect', (argument,)))
            continue
        out.append((name, words))
    return out


# --------------------------------------------------------------------------
# client side

SSW_SIZE = 0x3b98
SSW_VTABLE, CWIN_VTABLE, CWINEX_VTABLE = 0x01ab7398, 0x01ac7468, 0x01ac74a4
HELD_BUTTON = 0x01d1dc2c
FONT_GLOBALS = (0x06fc9ca4, 0x06fc9ca8, 0x06fc9cac, 0x06fc9cb0)
FONTS = (0x0f0f0001, 0x0f0f0002, 0x0f0f0003, 0x0f0f0004)
PATCHED_SITE = 0x01076018
ROOTS = (0x01075387, 0x01075554, 0x0107592f, 0x01075bc2, 0x010760d4, 0x010760bd, 0x010763a6, 0x01076a24,
         0x01076c1e, 0x0120d0ce, 0x0120d26d, 0x0120d37a, 0x0120cc8a, 0x01859f23, 0x010ae557,
         0x00986569, 0x00aac91b)     # the last two run through the array constructor iterator
EXTENTS = {0x01075bc2: 0x010760bd}     # UpdateDisplay: the patched site defeats the linear extent scan
STOPS = {0x0191bab9, 0x0191ba7b, 0x0191bac2, 0x0191baab, 0x0194cd00, 0x0194c200, 0x0195a4b0, 0x01983a90,
         0x00c97ce3, 0x00ebbec8, 0x00c97c2d, 0x01072152, 0x011e228b, 0x009da1ed, 0x009da253, 0x00a6ac96,
         0x01994240, 0x011a07b2, 0x00a7d68e, 0x0095f75d, 0x0107712d, 0x0107706e, 0x0107293c, 0x010713f8,
         0x01072928, 0x01072838, 0x01072859, 0x010728b9, 0x01072821, 0x010713e1, 0x0107134f, 0x01071376,
         0x0095f027, 0x00cc3564, 0x011e3510, 0x0191bac7, 0x0191b9eb}
VTABLES = (SSW_VTABLE, CWIN_VTABLE, CWINEX_VTABLE)
RT_IMPL_VTABLE = 0x01ac4c68


def closure(text, roots, extra=()):
    """Static call closure of `roots` (direct calls) without STOPS."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    engine = Cs(CS_ARCH_X86, CS_MODE_32)
    seen, todo = {}, list(roots) + list(extra)
    while todo:
        start = todo.pop()
        if start in seen or start in STOPS:
            continue
        end = EXTENTS.get(start) or cm.function_extent(text, start)
        seen[start] = end
        offset = start - cm.TEXT_BASE
        for _, _, mnemonic, operands in engine.disasm_lite(text[offset:end - cm.TEXT_BASE], start):
            if mnemonic == 'call' and operands.startswith('0x'):
                todo.append(int(operands, 16))
    return seen


class WidgetClient(vu.Client):
    def __init__(self, text, data):
        super().__init__(text, data)
        entries = []
        for table, count in ((SSW_VTABLE, 14), (CWIN_VTABLE, 14), (CWINEX_VTABLE, 14)):
            entries += [struct.unpack('<I', data[table - cm.DATA_BASE + 4*i:table - cm.DATA_BASE + 4*i + 4])[0]
                        for i in range(count)]
        self.functions = closure(text, ROOTS, entries + list(vu.TEXT_FUNCTIONS) + [0x0119fecb, 0x0119ff0f,
                                                                                  0x0119ff23, 0x0119fe5f])
        for start, end in self.functions.items():
            self.machine.allow((start, end))
        self.machine.allow((0x0191d71e, 0x0191d721))     # guard-check-icall no-op behind [0x01a7cc38]
        self.machine.uc.hook_add(cm.UC_HOOK_CODE, self._patched_site, begin=PATCHED_SITE, end=PATCHED_SITE)

    def _patched_site(self, uc, address, size, user):
        # the original instruction pair at this site: mov eax, [ebp-0x10]; movzx eax, byte [eax+0x14]
        ebp = uc.reg_read(cm.UC_X86_REG_EBP)
        server = struct.unpack('<I', self.machine.read(ebp - 0x10, 4))[0]
        uc.reg_write(cm.UC_X86_REG_EAX, self.machine.read(server + 0x14, 1)[0])
        uc.reg_write(cm.UC_X86_REG_EIP, 0x0107601f)

    def setup(self, state, bitmaps, window, strings, server_list, fonts=FONTS):
        """Prepare a case: globals, CInput, text facade, GlobalText, the server list."""
        self.prepare(state, bitmaps)
        m = self.machine
        calls = m.calls
        marker = lambda name, value=0: (lambda mm: (calls.append((name, ())), value)[1])  # noqa: E731
        m.put32(0x01cf65c0, 0xbb40e64e)                         # __security_cookie (SEH prolog)
        m.put32(HELD_BUTTON, 0)
        for address, value in zip(FONT_GLOBALS, fonts):
            m.put32(address, value)
        m.write(0x01ac3bb4, b'0\0')
        self.input = m.alloc(0x40, define=True)
        self.stub(0x00cc3564, lambda mm: self.input, 0)
        # the text facade (g_pRenderText) and its CUIRenderTextOriginal
        width_px = int(cm.f32(640.0*state.screen_rate_x))
        height_px = int(cm.f32(480.0*state.screen_rate_y))
        self.stride = ((width_px*24 + 31) & ~31) >> 3
        self.dib_size = (width_px, height_px)
        self.impl = m.alloc(0x18, define=True)
        self.dib = m.alloc(self.stride*height_px, define=True)
        m.put32(self.impl, RT_IMPL_VTABLE)
        m.put32(self.impl + 4, 0x4444)
        m.put32(self.impl + 0xc, self.dib)
        m.put32(self.impl + 0x10, 0xffffffff)
        m.put32(self.impl + 0x14, 0)
        facade = m.alloc(0x10, define=True)
        m.put32(facade + 4, self.impl)
        self.stub(0x011a07b2, lambda mm: facade, 0)

        def extent(mm, words):
            w, h = vu.text_extent(mm.read(words[1], words[2]))
            mm.write(words[3], struct.pack('<ii', w, h))
            return 1

        def text_out(mm, words):
            vu.rasterize(mm.read(words[3], words[4]), lambda off, d: mm.write(self.dib + off, d), self.stride,
                         width_px, height_px)
            return 1

        def pt_in_rect(mm, words):
            left, top, right, bottom = struct.unpack('<iiii', mm.read(words[0], 16))
            x, y = struct.unpack('<ii', struct.pack('<II', words[1], words[2]))
            return 1 if left <= x < right and top <= y < bottom else 0

        def set_rect(mm, words):
            mm.write(words[0], struct.pack('<IIII', *words[1:5]))
            return 1
        m.handlers.update({'GetTextExtentPointA': extent, 'GetTextExtentPoint32A': extent, 'TextOutA': text_out,
                           'PtInRect': pt_in_rect, 'SetRect': set_rect, 'IsBadReadPtr': lambda mm, w: 0})
        # GlobalText
        self.strings = {}
        for index, value in strings.items():
            address = m.alloc(len(value) + 1, define=True)
            m.write(address, value + b'\0')
            self.strings[index] = address
        empty = m.alloc(1, define=True)
        self.stub(0x0095f027, lambda mm: self.strings.get(mm.args(1)[0], empty))
        self.stub(0x01994240, lambda mm: 1, 0)                  # _mbclen: single-byte code page
        self.stub(0x01983a90, self._strcpy, 0)
        self.stub(0x00a6ac96, lambda mm: (calls.append(('Sound', (mm.args(1)[0],))), 0)[1], 0)
        self.stub(0x009da1ed, lambda mm: (calls.append(('Packet', ())), mm.uc.reg_read(cm.UC_X86_REG_ECX))[1])
        self.stub(0x009da253, marker('SendRequest'))
        ui = m.alloc(0x10, define=True)
        self.stub(0x011e228b, lambda mm: ui, 0)
        self.stub(0x011e3510, marker('HideWin'))
        self.stub(0x00a7d68e, lambda mm: 1, 0)
        self.stub(0x0095f75d, lambda mm: ui, 0)
        self.stub(0x0107712d, lambda mm: 0)
        self.stub(0x0107706e, lambda mm: (calls.append(('Connect', (self.slot_by_code.get(mm.args(1)[0], -1),))),
                                           0)[1], 0)
        self.stub(0x0107293c, lambda mm: 0)
        self._install_server_list(server_list)

    def _strcpy(self, m):
        target, source = m.args(2)
        m.write(target, self.cstr(source) + b'\0')
        return target

    def cstr(self, address, limit=4096):
        out = b''
        while len(out) < limit:
            byte = self.machine.read(address + len(out), 1)
            if byte == b'\0':
                break
            out += byte
        return out

    def _install_server_list(self, server_list):
        """Synthetic CServerListManager: groups and servers at the client offsets."""
        m = self.machine
        self.manager = m.alloc(0x200, define=True)
        notice = m.alloc(len(server_list['notice']) + 1, define=True)
        m.write(notice, server_list['notice'] + b'\0')
        self.groups, self.group_servers, self.slot_by_code = [], {}, {}
        for gi, group in enumerate(server_list['groups']):
            address = m.alloc(0x240, define=True)
            m.put32(address + 4, group['id'])
            m.write(address + 8, bytes([group['type']]))
            m.put32(address + 0xc, group['position'])
            m.put32(address + 0x10, group['button'] & 0xffffffff)
            m.write(address + 0x30, group['name'][:0xfe] + b'\0')
            m.write(address + 0x12f, group['description'][:0x100] + b'\0')
            servers = []
            for si, server in enumerate(group['servers']):
                s = m.alloc(0x60, define=True)
                m.put32(s + 4, server['slot'])
                m.put32(s + 8, 0x1000 + si)
                code = 0x100*gi + si
                m.write(s + 0xc, struct.pack('<H', code))
                self.slot_by_code[code] = server['slot']
                m.put32(s + 0x10, server['percent'])
                m.write(s + 0x14, bytes([server['type']]))
                m.write(s + 0x15, server['name'][:0x40] + b'\0')
                servers.append(s)
            self.groups.append(address)
            self.group_servers[address] = servers
        cursor = {'manager': 0}
        group_cursor = {}

        def get_next(mm):
            out = mm.args(1)[0]
            if cursor['manager'] < len(self.groups):
                mm.put32(out, self.groups[cursor['manager']])
                cursor['manager'] += 1
                return 1
            mm.put32(out, 0)
            return 0

        def by_button(mm):
            want = mm.args(1)[0]
            for address in self.groups:
                if mm.u32(address + 0x10) == want:
                    return address
            return 0

        def group_next(mm):
            this, out = mm.uc.reg_read(cm.UC_X86_REG_ECX), mm.args(1)[0]
            index = group_cursor.get(this, 0)
            servers = self.group_servers[this]
            if index < len(servers):
                mm.put32(out, servers[index])
                group_cursor[this] = index + 1
                return 1
            mm.put32(out, 0)
            return 0

        def group_server(mm):
            this, want = mm.uc.reg_read(cm.UC_X86_REG_ECX), mm.args(1)[0]
            for s in self.group_servers[this]:
                if mm.u32(s + 4) == want:
                    return s
            return 0
        self.stub(0x01072152, lambda mm: self.manager, 0)
        self.stub(0x01072928, lambda mm: len(self.groups))
        self.stub(0x01072838, lambda mm: cursor.__setitem__('manager', 0))
        self.stub(0x01072859, get_next)
        self.stub(0x010728b9, by_button)
        self.stub(0x01072821, lambda mm: notice)
        self.stub(0x010713e1, lambda mm: len(self.group_servers[mm.uc.reg_read(cm.UC_X86_REG_ECX)]))
        self.stub(0x0107134f, lambda mm: group_cursor.__setitem__(mm.uc.reg_read(cm.UC_X86_REG_ECX), 0))
        self.stub(0x01071376, group_next)
        self.stub(0x010713f8, group_server)

    def set_input(self, x, y, down, up, screen):
        m = self.machine
        m.put32(self.input + 0xc, x & 0xffffffff)
        m.put32(self.input + 0x10, y & 0xffffffff)
        m.write(self.input + 0x1c, bytes([down, 0, up]))
        m.put32(self.input + 0x28, screen[0])
        m.put32(self.input + 0x2c, screen[1])

    # ---- client object snapshots (same order as ui_probe.c) -----------------
    def snap_sprite(self, s):
        m = self.machine
        u = lambda off: m.u32(s + off)  # noqa: E731
        out = [u(0x10), u(0x08), u(0x14), u(0x18)] + [u(0x1c + 4*i) for i in range(8)]
        out += [u(0x3c + 4*i) for i in range(8)] + [u(0x5c), u(0x60), u(0x64), u(0x68), u(0x6c), u(0x70), u(0x74),
                                                    m.read(s + 0x98, 1)[0], u(0x9c), u(0x90), u(0x94),
                                                    m.read(s + 0xa0, 1)[0]]
        frames = u(0x78)
        out.append(1 if frames else 0)
        if frames:
            out += [m.u32(frames + 4*i) for i in range(2*min(u(0x68), 16))]
        return out

    def snap_button(self, b):
        m = self.machine
        out = self.snap_sprite(b) + [m.u32(b + 0xa8)] + [m.u32(b + 0xac + 4*i) for i in range(8)]
        text = m.u32(b + 0xcc)
        out.append(1 if text else 0)
        if text:
            value = self.cstr(text)
            count = 8 if struct.unpack('<i', m.read(b + 0xac + 16, 4))[0] > -1 else 4
            colors = m.u32(b + 0xd0)
            out += [len(value)] + list(value) + [count] + [m.u32(colors + 4*i) for i in range(count)]
            out.append(m.u32(b + 0xd4))
        out.append(m.u32(b + 0xd8))
        return out

    def snap_win(self, w):
        m = self.machine
        return [m.u32(w + 0xc) & 0xffffff] + [m.u32(w + off) for off in (0x10, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 4,
                                                                          8, 0x38)]

    def snap_winex(self, w):
        m = self.machine
        out = self.snap_win(w)
        sprites = m.u32(w + 0x14)
        for i in range(5):
            out += self.snap_sprite(sprites + 0xa8*i)
        return out + [m.u32(w + 0x3c), m.u32(w + 0x40), m.u32(w + 0x44)]

    def snap_server_win(self, w):
        m = self.machine
        out = self.snap_win(w)
        for i in range(25):
            out += self.snap_button(w + 0x40 + 0xe0*i)
        for i in range(20):
            out += self.snap_button(w + 0x1620 + 0xe0*i)
            gauge = w + 0x27a0 + 0xd0*i
            out += self.snap_sprite(gauge + 8) + [m.u32(gauge + off) for off in (0xb0, 0xb4, 0xb8, 0xbc, 0xc8, 0xcc)]
        for i in range(2):
            out += self.snap_sprite(w + 0x37e0 + 0xa8*i)
        for i in range(2):
            out += self.snap_sprite(w + 0x3930 + 0xa8*i)
        out += self.snap_winex(w + 0x3a80)
        out += [m.u32(w + off) for off in (0x3acc, 0x3ad0, 0x3ad4, 0x3ad8, 0x3ae0, 0x3ae4)]
        group = m.u32(w + 0x3ae8)
        out.append(self.groups.index(group) if group in self.groups else (0xffffffff if not group else 0xfffffffe))
        out += list(m.read(w + 0x3aec, 2*0x53))
        return out

    def held_index(self, w):
        held = self.machine.u32(HELD_BUTTON)
        if not held:
            return -1
        buttons = [w + 0x40 + 0xe0*i for i in range(25)] + [w + 0x1620 + 0xe0*i for i in range(20)]
        return buttons.index(held) if held in buttons else -2


# --------------------------------------------------------------------------
# the reconstruction side of a case

class Side:
    """Authored objects for one case: state, text, ctx, server list."""

    def __init__(self, lib, window, bitmaps, rates, strings, server_list, dib_init):
        self.lib = lib
        self.authored = Authored(lib, window[0], window[1], bitmaps, rates=rates)
        self.gdi = vu.SyntheticGdi()
        text = self.text = vu.Text()
        text.gdi.extent = self.gdi._extent
        text.gdi.text_out = self.gdi._text_out
        lib.mu_ui_text_init(ctypes.byref(text), ctypes.byref(self.authored.state))
        self.dib = (c_uint8*len(dib_init)).from_buffer_copy(dib_init)
        text.dib = ctypes.cast(self.dib, POINTER(c_uint8))
        self._strings = {k: ctypes.create_string_buffer(v) for k, v in strings.items()}
        self._empty = ctypes.create_string_buffer(b'')
        self._gt = GLOBALTEXTFN(lambda user, index: ctypes.addressof(self._strings.get(index, self._empty)))
        ctx = self.ctx = Ctx()
        ctx.state = ctypes.addressof(self.authored.state)
        ctx.text = ctypes.addressof(text)
        ctx.input.screen_width, ctx.input.screen_height = window
        ctx.fonts = Fonts(*FONTS)
        ctx.global_text = self._gt
        self.list = ServerList()
        self.list.group_count = len(server_list['groups'])
        self.list.notice = server_list['notice']
        for gi, group in enumerate(server_list['groups']):
            g = self.list.groups[gi]
            g.id, g.type, g.position, g.button = group['id'], group['type'], group['position'], group['button']
            g.name, g.description = group['name'][:63], group['description'][:255]
            g.server_count = len(group['servers'])
            for si, server in enumerate(group['servers']):
                s = g.servers[si]
                s.slot, s.percent, s.type, s.name = server['slot'], server['percent'], server['type'], server['name'][:63]
        self.win = ctypes.create_string_buffer(lib.mu_ui_probe_sizeof(4))
        lib.mu_ui_server_win_init(self.win, ctypes.byref(self.list))

    @property
    def calls(self):
        return self.authored.calls

    def set_input(self, x, y, down, up):
        self.ctx.input.cursor_x, self.ctx.input.cursor_y = x, y
        self.ctx.input.lbutton_down, self.ctx.input.lbutton_up = down, up

    def snapshot(self):
        out = (c_uint32*60000)()
        n = self.lib.mu_ui_probe_server_win(self.win, out)
        return list(out[:n])

    def held(self):
        return self.lib.mu_ui_probe_held(ctypes.byref(self.ctx), self.win)


# --------------------------------------------------------------------------
# synthetic inputs

WINDOWS = [(640, 480), (800, 600), (1024, 768), (1280, 1024), (1366, 768), (1600, 900), (1722, 1048), (1920, 1080)]
TEXT_INDICES = (0x235, 0x236, 0x237, 0x10f3, 0x10f4, 0x1225, 0x1226)


def ssw_bitmaps(rng):
    out = vu.base_bitmaps()
    sizes = {0x7b0e: (128, 128), 0x7b0f: (256, 128), 0x7b10: (256, 8), 0x7b11: (256, 128), 0x7b19: (4, 4),
             0x7b1a: (512, 16), 0x7b1b: (8, 4)}
    for index, (w, h) in sizes.items():
        if rng.random() < 0.3:
            w, h = w*2, h*rng.choice([1, 2])
        out[index] = {'width': float(w), 'height': float(h), 'texture': 2000 + index % 991, 'components': 4}
    return out


WORDS = [b'MTM', b'PvP', b'NoPvP', b'Bosses', b'VIP', b'[NoPvP]', b'Season', b'21', b'Powered', b'by', b'Glitch',
         b'Games', b'Network-Online', b'Game', b'Servers', b'/', b'OffJewelFarm', b'1600+']


def phrase(rng, count):
    return b' '.join(rng.choice(WORDS) for _ in range(count))


def server_list(rng, groups=None):
    out = {'groups': [], 'notice': phrase(rng, rng.randint(0, 30)) if rng.random() < 0.7 else b''}
    for gi in range(groups if groups is not None else rng.randint(0, 9)):
        servers = []
        for si in range(rng.choice([0, 1, 3, 7, 12, 19, 20]) if rng.random() < 0.95 else 0):
            servers.append({'slot': si if rng.random() < 0.95 else si + 30, 'percent': rng.choice([0, 7, 33, 64, 99,
                                                                                                   100, 128, 200]),
                            'type': rng.randint(0, 3), 'name': b'MTM-%d ' % (si + 1) + phrase(rng, rng.randint(0, 3))})
        out['groups'].append({'id': rng.choice([1, 2, 0x11, 0x27, 5, 9]), 'type': rng.choice([0, 1, 2]),
                              'position': rng.choice([0, 0, 1, 2, 2, 3]), 'button': rng.choice([0, -1, 7]),
                              'name': phrase(rng, rng.randint(1, 2)), 'description': phrase(rng, rng.randint(0, 40)),
                              'servers': servers})
    return out


def global_strings(rng):
    return {index: phrase(rng, rng.randint(1, 5)) for index in TEXT_INDICES if rng.random() < 0.9}


# --------------------------------------------------------------------------
# server-select window cases

class Case:
    """One client/reconstruction pair driven through the same steps."""

    def __init__(self, client, lib, rng, window, servers, strings, render_text=True):
        self.client, self.lib = client, lib
        self.window = window
        rates = (cm.f32(window[0]/640.0), cm.f32(window[1]/480.0))
        bitmaps = ssw_bitmaps(rng)
        width_px, height_px = int(cm.f32(640.0*rates[0])), int(cm.f32(480.0*rates[1]))
        stride = ((width_px*24 + 31) & ~31) >> 3
        dib_init = bytes(stride*height_px)
        self.side = Side(lib, window, bitmaps, rates, strings, servers, dib_init)
        client.setup(self.side.authored.state, bitmaps, window, strings, servers)
        m = client.machine
        self.m = m
        m.write(client.dib, dib_init)
        client.set_input(0, 0, 0, 0, window)
        self.ssw = m.alloc(SSW_SIZE, define=True)   # CUIMng is a static singleton: zero-initialised storage
        self.bitmaps = bitmaps

    def both(self, label, client_fn, authored_fn, compare_calls=True):
        self.m.calls.clear()
        del self.side.calls[:]
        client_fn(self.m)
        authored_fn(self.side)
        if compare_calls:
            got, want = normalize(self.m.calls), normalize_authored(self.side.calls)
            problem = vu.diff(got, want)
            if problem:
                raise AssertionError(f'{label}: {problem}')
        return len(self.m.calls)

    def compare_state(self, label):
        got, want = self.client.snap_server_win(self.ssw), self.side.snapshot()
        if got != want:
            index = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            raise AssertionError(f'{label}: object state differs at word {index} (client {got[index:index+4]} '
                                 f'authored {want[index:index+4]}, lengths {len(got)} {len(want)})')
        held_client, held_authored = self.client.held_index(self.ssw), self.side.held()
        if held_client != held_authored:
            raise AssertionError(f'{label}: held button {held_client} != {held_authored}')
        return len(got)

    def build(self):
        lib, side = self.lib, self.side
        sp, ctx = side.authored.sp, ctypes.byref(side.ctx)
        self.both('ctor+Create', lambda m: (m.call(0x01075387, ecx=self.ssw), m.call(0x01075554, ecx=self.ssw)),
                  lambda s: lib.mu_ui_server_win_create(ctx, s.win))
        x = (self.window[0] - self.client.machine.u32(self.ssw + 0x20)) // 2
        y = (self.window[1] - self.client.machine.u32(self.ssw + 0x24)) // 2
        self.both('SetPosition', lambda m: m.call(0x0107592f, [x & 0xffffffff, y & 0xffffffff], ecx=self.ssw),
                  lambda s: lib.mu_ui_server_win_set_position(ctx, s.win, x, y))
        del sp

    def show(self, show=1, active=1):
        lib, side = self.lib, self.side
        ctx = ctypes.byref(side.ctx)
        self.both('Show', lambda m: (m.call(0x010760bd, [show], ecx=self.ssw),
                                     m.call(0x0098285a, [active], ecx=self.ssw)),
                  lambda s: (lib.mu_ui_win_show(ctx, s.win, show), lib.mu_ui_win_set_active(s.win, active)))

    def select(self, index):
        self.m.put32(self.ssw + 0x3ae4, index & 0xffffffff)
        self.lib.mu_ui_probe_select(self.side.win, index)

    def update_display(self):
        lib, side = self.lib, self.side
        ctx = ctypes.byref(side.ctx)
        return self.both('UpdateDisplay', lambda m: m.call(0x01075bc2, ecx=self.ssw),
                         lambda s: lib.mu_ui_server_win_update_display(ctx, s.win))

    def render(self):
        lib, side = self.lib, self.side
        ctx = ctypes.byref(side.ctx)
        n = self.both('Render', lambda m: m.call(0x0120d26d, ecx=self.ssw), lambda s: lib.mu_ui_win_render(ctx, s.win))
        dib_client = self.m.read(self.client.dib, len(side.dib))
        if dib_client != bytes(side.dib):
            raise AssertionError('Render: DIB contents differ')
        return n

    def frame(self, x, y, down, up, delta=40.0):
        lib, side = self.lib, self.side
        ctx = ctypes.byref(side.ctx)
        self.client.set_input(x, y, down, up, self.window)
        side.set_input(x, y, down, up)
        lo, hi = struct.unpack('<II', struct.pack('<d', delta))
        return self.both(f'Update({x},{y},{down},{up})', lambda m: m.call(0x0120d0ce, [lo, hi], ecx=self.ssw),
                         lambda s: lib.mu_ui_win_update(ctx, s.win, delta))


def button_points(case, rng, count):
    """Cursor positions: on buttons (visible or hidden), on edges, and random."""
    m, ssw = case.m, case.ssw
    points = []
    for _ in range(count):
        kind = rng.random()
        if kind < 0.7:
            buttons = [ssw + 0x40 + 0xe0*i for i in range(25)] + [ssw + 0x1620 + 0xe0*i for i in range(20)]
            visible = [b for b in buttons if m.read(b + 0xa0, 1)[0]]
            base = rng.choice(visible if visible and rng.random() < 0.85 else buttons)
            x0 = struct.unpack('<f', m.read(base + 0x1c, 4))[0]
            y0 = struct.unpack('<f', m.read(base + 8, 4))[0] - struct.unpack('<f', m.read(base + 0x20, 4))[0]
            w = struct.unpack('<f', m.read(base + 0x14, 4))[0]
            h = struct.unpack('<f', m.read(base + 0x18, 4))[0]
            if not (abs(x0) < 1e6 and abs(y0) < 1e6):
                x0, y0 = 0, 0
            x = int(x0) + rng.choice([0, 1, int(w) // 2, int(w) - 1, int(w), -1])
            y = int(y0) + rng.choice([0, 1, int(h) // 2, int(h) - 1, int(h), -1])
        else:
            x, y = rng.randint(-5, case.window[0] + 5), rng.randint(-5, case.window[1] + 5)
        points.append((x, y))
    return points


def interaction(case, rng):
    """Mouse frames: clicks, presses released elsewhere, hovering, random edges."""
    frames = []
    for _ in range(rng.choice([0, 2, 5, 9])):
        p = button_points(case, rng, 1)[0]
        q = button_points(case, rng, 1)[0]
        delta = rng.choice([40.0, 40.0, 16.5, 0.0, -1.0])
        kind = rng.random()
        if kind < 0.45:      # click: hover, press, hold, release on the same spot
            frames += [(p[0], p[1], 0, 0, delta), (p[0], p[1], 1, 0, delta), (p[0], p[1], 0, 0, delta),
                       (p[0], p[1], 0, 1, delta), (p[0], p[1], 0, 0, delta)]
        elif kind < 0.6:     # press on one spot, release on another
            frames += [(p[0], p[1], 1, 0, delta), (q[0], q[1], 0, 0, delta), (q[0], q[1], 0, 1, delta)]
        elif kind < 0.75:    # down and up in the same frame
            frames += [(p[0], p[1], 1, 1, delta), (p[0], p[1], 0, 0, delta)]
        else:
            frames += [(p[0], p[1], rng.randint(0, 1), rng.randint(0, 1), delta)]
    return frames


def validate_server_win(client, lib, rng, report, cases):
    counts = {'cases': 0, 'render_calls': 0, 'update_frames': 0, 'state_words': 0, 'events': 0, 'clicks': 0,
              'event_codes': {}}
    started = time.time()
    for number in range(cases):
        window = WINDOWS[number % len(WINDOWS)] if number < len(WINDOWS) else rng.choice(WINDOWS)
        servers = server_list(rng, groups=rng.choice([None, 0, 1, 3, 6, 30]))
        strings = global_strings(rng)
        case = Case(client, lib, rng, window, servers, strings)
        label = f'server window case {number} {window}'
        try:
            case.build()
            counts['state_words'] += case.compare_state('after Create/SetPosition')
            if rng.random() < 0.9:
                case.show(1, 1 if rng.random() < 0.85 else 0)
            groups = [g for g in range(25)]
            if rng.random() < 0.6 and servers['groups']:
                case.select(rng.choice(groups + [-1, 40]))
            case.update_display()
            counts['state_words'] += case.compare_state('after UpdateDisplay')
            if number % 3 == 0 or number < 8:
                counts['render_calls'] += case.render()
            for step, (x, y, down, up, delta) in enumerate(interaction(case, rng)):
                case.frame(x, y, down, up, delta)
                counts['update_frames'] += 1
                for name, words in case.side.calls:
                    if name == 'Event':
                        counts['events'] += 1
                        counts['event_codes'][str(words[0])] = counts['event_codes'].get(str(words[0]), 0) + 1
                    elif name == 'Sound':
                        counts['clicks'] += 1
                counts['state_words'] += case.compare_state(f'after frame {step}')
                if any(name == 'Event' and words[0] == 1 for name, words in case.side.calls):
                    case.update_display()      # what the server-list reply triggers
                    counts['state_words'] += case.compare_state(f'after group reply {step}')
            if number % 3 == 0:
                counts['render_calls'] += case.render()
        except AssertionError as error:
            summary = [(g['position'], g['type'], g['button'], len(g['servers'])) for g in servers['groups']]
            raise AssertionError(f'{label}: {error}; groups (position, type, button, servers) {summary}') from None
        counts['cases'] += 1
    counts['seconds'] = round(time.time() - started, 1)
    report['server_window'] = counts


def snapshot_sprite(lib, sprite):
    out = (c_uint32*256)()
    return list(out[:lib.mu_ui_probe_sprite(sprite, out)])


def validate_sprites(client, lib, rng, report):
    """CSprite frames: Create with a frame table, SetAction, SetNowFrame, Update, PtInSprite."""
    counts = {'cases': 0, 'operations': 0, 'hit_tests': 0, 'hits': 0}
    for case in range(120):
        window = rng.choice(WINDOWS)
        rates = (cm.f32(window[0]/640.0), cm.f32(window[1]/480.0))
        bitmaps = ssw_bitmaps(rng)
        side = Side(lib, window, bitmaps, rates, {}, {'groups': [], 'notice': b''}, b'')
        client.setup(side.authored.state, bitmaps, window, {}, {'groups': [], 'notice': b''})
        m = client.machine
        texture = rng.choice([0x7b0e, 0x7b0f, 0x7b11, -1, 0x7b1a])
        max_frame = rng.choice([0, 1, 2, 3, 4, 7])
        frames = [(rng.choice([0, 3, 64, 68, 136]), rng.randint(0, 200)) for _ in range(max_frame)]
        table = m.alloc(8*max(max_frame, 1), define=True)
        for i, (fx, fy) in enumerate(frames):
            m.write(table + 8*i, struct.pack('<ii', fx, fy))
        args = [rng.randint(1, 300), rng.randint(1, 120), texture, max_frame, table if max_frame and rng.random() < 0.8
                else 0, rng.randint(0, 9), rng.randint(0, 9), rng.randint(0, 1), rng.randint(0, 3),
                rng.choice([1.0, cm.f32(window[0]/800.0), 0.5]), rng.choice([1.0, cm.f32(window[1]/600.0)])]
        sprite = m.alloc(0xa8, define=True)
        m.call(0x010ad7b2, ecx=sprite)
        m.call(0x010ad847, args[:9] + [F(args[9]), F(args[10])], ecx=sprite)
        mine = ctypes.create_string_buffer(lib.mu_ui_probe_sizeof(6))
        lib.mu_ui_sprite_init(mine)
        frame_array = (c_int32*(2*max(max_frame, 1)))(*[v for f in frames for v in f])
        lib.mu_ui_sprite_create_frames(side.authored.sp, mine, args[0], args[1], texture, max_frame,
                                       frame_array if args[4] else None, *args[5:9], args[9], args[10])
        for step in range(rng.randint(1, 12)):
            op = rng.random()
            if op < 0.2:
                start, end = rng.randint(-1, max_frame - 1), rng.randint(-1, max_frame - 1)   # inside the table
                interval, repeat = rng.choice([0.0, 40.0, 100.0]), rng.randint(0, 1)
                lo, hi = struct.unpack('<II', struct.pack('<d', interval))
                m.call(0x010ae3a1, [start & 0xffffffff, end & 0xffffffff, lo, hi, repeat], ecx=sprite)
                lib.mu_ui_sprite_set_action(mine, start, end, interval, repeat)
            elif op < 0.4:
                frame = rng.randint(-1, max_frame)
                m.call(0x010ae3eb, [frame & 0xffffffff], ecx=sprite)
                lib.mu_ui_sprite_set_now_frame(mine, frame)
            elif op < 0.6:
                delta = rng.choice([0.0, 16.0, 40.0, 120.0])
                lo, hi = struct.unpack('<II', struct.pack('<d', delta))
                m.call(0x010ae557, [lo, hi], ecx=sprite)
                lib.mu_ui_sprite_update(mine, delta)
            elif op < 0.75:
                show = rng.randint(0, 1)
                m.call(0x00986f8a, [show], ecx=sprite)
                _sprite_show(lib, mine, show)
            else:
                pos = (rng.randint(-10, 400), rng.randint(-10, 300))
                if rng.random() < 0.7:
                    m.call(0x00986f8a, [1], ecx=sprite)
                    _sprite_show(lib, mine, 1)
                sx, sy = args[9], args[10]
                x = int(pos[0]*sx) + rng.choice([-1, 0, 1, int(args[0]*sx) // 2, int(args[0]*sx) - 1, int(args[0]*sx)])
                y = int(pos[1]*sy) + rng.choice([-1, 0, 1, int(args[1]*sy) // 2, int(args[1]*sy) - 1, int(args[1]*sy)])
                m.call(0x010add3c, [pos[0] & 0xffffffff, pos[1] & 0xffffffff, 3], ecx=sprite)
                _sprite_position(lib, mine, pos)
                got = m.call(0x010ae2a5, [x & 0xffffffff, y & 0xffffffff], ecx=sprite)
                want = lib.mu_ui_sprite_contains(mine, x, y)
                counts['hit_tests'] += 1
                counts['hits'] += 1 if want else 0
                if bool(got) != bool(want):
                    raise AssertionError(f'sprite case {case}: PtInSprite({x},{y}) {got} != {want}')
            counts['operations'] += 1
            if client.snap_sprite(sprite) != snapshot_sprite(lib, mine):
                raise AssertionError(f'sprite case {case} step {step}: state differs '
                                     f'{client.snap_sprite(sprite)} {snapshot_sprite(lib, mine)}')
        counts['cases'] += 1
    report['sprites'] = counts


def _sprite_show(lib, sprite, show):
    lib.mu_ui_sprite_show.argtypes = [c_void_p, c_int]
    lib.mu_ui_sprite_show(sprite, show)


def _sprite_position(lib, sprite, pos):
    lib.mu_ui_sprite_set_position.argtypes = [c_void_p, c_int32, c_int32, c_int32]
    lib.mu_ui_sprite_set_position(sprite, pos[0], pos[1], 3)


def validate_winex(client, lib, rng, report):
    """CWinEx: Create, SetLine, SetPosition, Show, Render, and CWin::Update driving move and resize."""
    counts = {'cases': 0, 'frames': 0, 'render_calls': 0, 'states': {}, 'line_changes': 0}
    for case in range(60):
        window = rng.choice(WINDOWS)
        rates = (cm.f32(window[0]/640.0), cm.f32(window[1]/480.0))
        bitmaps = ssw_bitmaps(rng)
        side = Side(lib, window, bitmaps, rates, {}, {'groups': [], 'notice': b''}, b'')
        client.setup(side.authored.state, bitmaps, window, {}, {'groups': [], 'notice': b''})
        m = client.machine
        info = [(0x7b19, 0, 0, rng.choice([4, 32]), rng.choice([4, 16])),
                (0x7b1a, 0, 0, rng.choice([0x200, 0x100]), 6), (0x7b1a, 0, rng.choice([0, 6]), 0x200, 6),
                (0x7b1b, 0, 0, 3, rng.choice([4, 8])), (0x7b1b, rng.choice([0, 3]), 0, 3, 4)]
        table = m.alloc(0x14*5, define=True)
        mine_info = (c_int32*25)()
        for i, row in enumerate(info):
            m.write(table + 0x14*i, struct.pack('<5i', *row))
            for j, v in enumerate(row):
                mine_info[5*i + j] = v
        line_min, line_max = rng.choice([(1, 10), (2, 5), (1, 1), (3, 30)])
        lines = rng.randint(0, 12)
        pos = (rng.randint(0, window[0] - 100), rng.randint(0, window[1] - 100))
        win = m.alloc(0x4c, define=True)
        mine = ctypes.create_string_buffer(lib.mu_ui_probe_sizeof(3))
        ctx = ctypes.byref(side.ctx)
        m.calls.clear()
        m.call(0x0120d37a, ecx=win)
        m.call(0x0120d3df, [table, line_min, line_max], ecx=win)
        old_client = m.call(0x0120d861, [lines], ecx=win)
        m.call(0x0120d73c, [pos[0], pos[1]], ecx=win)
        m.call(0x0120db2c, [1], ecx=win)
        m.call(0x0098285a, [1], ecx=win)
        m.call(0x0120db7e, ecx=win)
        lib.mu_ui_winex_init(mine)
        lib.mu_ui_winex_create(ctx, mine, mine_info, line_min, line_max)
        old_mine = lib.mu_ui_winex_set_line(mine, lines)
        lib.mu_ui_winex_set_position(ctx, mine, pos[0], pos[1])
        lib.mu_ui_winex_show(ctx, mine, 1)
        lib.mu_ui_win_set_active(mine, 1)
        lib.mu_ui_winex_render(ctx, mine)
        if old_client != old_mine & 0xffffffff:
            raise AssertionError(f'winex case {case}: SetLine returned {old_client} != {old_mine}')
        problem = vu.diff(normalize(m.calls), normalize_authored(side.calls))
        if problem:
            raise AssertionError(f'winex case {case} render: {problem}')
        counts['render_calls'] += len(m.calls)
        out = (c_uint32*2048)()

        def compare(label):
            want = list(out[:lib.mu_ui_probe_winex(mine, out)])
            got = client.snap_winex(win)
            if got != want:
                index = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), 0)
                raise AssertionError(f'winex case {case} {label}: state differs at {index}: {got[index:index+3]} '
                                     f'{want[index:index+3]}')
        compare('after create')
        x0, y0 = pos
        width, height = m.u32(win + 0x20), m.u32(win + 0x24)
        for step in range(rng.randint(2, 14)):
            x = x0 + rng.choice([0, 5, width // 2, width - 1, width + 3])
            y = rng.choice([y0, y0 + 1, y0 + 3, y0 + 4, y0 + 20, y0 + height - 5, y0 + height - 1, y0 + height,
                            y0 + height + 40, y0 - 30, rng.randint(0, window[1])])
            down, up = rng.choice([(1, 0), (0, 0), (0, 0), (0, 1)])
            client.set_input(x, y, down, up, window)
            side.set_input(x, y, down, up)
            lo, hi = struct.unpack('<II', struct.pack('<d', 40.0))
            m.call(0x0120d0ce, [lo, hi], ecx=win)
            lib.mu_ui_win_update(ctx, mine, 40.0)
            compare(f'frame {step} ({x},{y},{down},{up})')
            counts['frames'] += 1
            state = m.u32(win + 0x10)
            counts['states'][str(state)] = counts['states'].get(str(state), 0) + 1
            counts['line_changes'] += 1 if m.u32(win + 0x44) != lines else 0
        counts['cases'] += 1
    report['winex'] = counts


def validate_cut_text(client, lib, rng, report):
    m = client.machine
    count = 0
    for case in range(400):
        width = rng.choice([1, 2, 3, 8, 20, 21, 40, 0x53, 100])
        lines = rng.choice([1, 2, 3, 5])
        text = phrase(rng, rng.randint(0, 40)) if rng.random() < 0.8 else bytes(rng.choice(b'ab  c') for _ in
                                                                                 range(rng.randint(0, 200)))
        state = vu.State()
        client.setup(state, {}, (640, 480), {}, {'groups': [], 'notice': b''}) if case == 0 else None
        source = m.alloc(len(text) + 1, define=True)
        m.write(source, text + b'\0')
        target = m.alloc(lines*width + 16, define=True)
        m.write(target, b'\xcc'*(lines*width + 16))
        result = m.call(0x01859f23, [source, target, lines, width])
        buf = ctypes.create_string_buffer(b'\xcc'*(lines*width + 16), lines*width + 16)
        mine = lib.mu_ui_cut_text(text, buf, lines, width)
        if result != mine or m.read(target, lines*width + 16) != buf.raw:
            raise AssertionError(f'CutText {text!r} lines {lines} width {width}: {result} vs {mine}')
        count += 1
    report['cut_text_cases'] = count


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', default=ROOT/'evidence/x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', default=ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin')
    parser.add_argument('--library')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--cases', type=int, default=60)
    parser.add_argument('--only', choices=['server', 'cut', 'sprites', 'winex'], action='append')
    parser.add_argument('--output')
    args = parser.parse_args()
    text = common.load_pinned(args.text, common.TEXT_BYTES, common.TEXT_SHA256)
    data = common.load_pinned(args.data, common.DATA_BYTES, common.DATA_SHA256)
    lib = library(args.library)
    client = WidgetClient(text, data)
    rng = random.Random(args.seed)
    report = {'text_sha256': common.TEXT_SHA256, 'data_sha256': common.DATA_SHA256, 'seed': args.seed,
              'allowlisted_functions': len(client.functions)}
    only = set(args.only or ['server', 'cut', 'sprites', 'winex'])
    if 'cut' in only:
        validate_cut_text(client, lib, rng, report)
    if 'sprites' in only:
        validate_sprites(client, lib, rng, report)
    if 'winex' in only:
        validate_winex(client, lib, rng, report)
    if 'server' in only:
        validate_server_win(client, lib, rng, report, args.cases)
    print(json.dumps(report, indent=1))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
