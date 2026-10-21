#!/usr/bin/env python3
"""Compare the create-character panel, the delete flow and the system menu with the client
(NATIVE-CHARCREATE-001).

The client routines run in Unicorn over the pinned restored text and second image section
(scripts/client_ui_machine.py); reconstructed/charsel/charcreate.c runs through ctypes from the same
state.  Both report every GFx invoke and every call into another subsystem as text lines (see
charcreate.h); the lines, the window fields, the creation-preview record, the character records and the
globals are compared.

Families (client entry points):

* show        0x00b49bf4  the create panel shown / hidden (with the list's show 0x00b4b848)
* restrict    0x00b4b684  the rename mode's class restriction (dead code: nothing happens)
* klass       0x00b4a442  SetSelectedClass and the preview pose 0x00b4a4a1 (every class byte)
* board       0x00b4a349  SetCreateBoardInfo (window origin and scale getters as client code)
* name        0x00b49eca  OnEnterCharacterName: limit, length, the two name filters, allowed
                          characters (SBCS and CP949 lead bytes), the create and rename requests
* input       0x00b4b31a  UpdateInput (cut at 10 bytes)
* count       0x00b49d0d  UpdateCreateCount
* created     0x0122b648  the server's answer to a create request
* message     0x00b49967  message-box results (create errors, the delete steps, the password)
* deleted     0x012326c4  the server's answer to a delete request
* render      0x00b49cd7  the window's render hook and the preview render 0x00b4a14c
* classname   0x0139cc2e  every class byte, flags 0 and 1
* serverclass 0x0139ca62  every server class code
* menu        0x00c8c8b1 (toggle), 0x00c8ce3d (scene windows), 0x00c8c6be (events)

Modelled (not client code): the GFx value API and invokes, GlobalText ("GT<n>"), std::string
construction, operator new/delete, the CRT string routines (strlen, strncpy, memmove, sprintf), the
formatter of 0x00b49d0d (boost-like, "%d"), the output string stream of 0x00b49967, _ismbblead
0x019ac155 (the code page: none, or CP949 lead bytes 0x81..0xfe), the packet objects and their send
routines, and every call reported as a line.
"""
import argparse
import ctypes
from ctypes import (CFUNCTYPE, POINTER, Structure, c_char_p, c_float, c_int, c_int32, c_uint8, c_uint16,
                    c_void_p, c_char)
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import client_ui_machine as cm  # noqa: E402

TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
PINNED_FILE = Path(__file__).with_suffix('.pins.json')
EVIDENCE = ROOT / 'evidence' if (ROOT / 'evidence').exists() else Path.home() / 'Documents/main-exe-study/evidence'

RUN = (   # client code executed (pinned by SHA-256 in validate_charcreate.pins.json)
    0x00b49bf4, 0x00b4b684, 0x00b4a442, 0x00b4a4a1, 0x00b4a349, 0x00b49eca, 0x00b4b29d, 0x0110cb45,
    0x0110c9f2, 0x0110c960, 0x0185c95d, 0x00cdb9af, 0x01994240, 0x00b4b31a, 0x00b49d0d, 0x00b4b2d6,
    0x00b4b278, 0x00b4bf25, 0x00b4c697, 0x0122b648, 0x0139ca62, 0x00b49967, 0x00b49cba, 0x00b4a0da, 0x012326c4,
    0x00b49ca0, 0x00b49cd7, 0x00b4a14c, 0x009a5a06, 0x0139cc2e, 0x0139cab9, 0x0095f5cc, 0x0139cb8a,
    0x0139d6a2, 0x00c8c8b1, 0x00c8ce3d, 0x00c8cd17, 0x00c8c6be, 0x00c8cb13, 0x00c8cc8e, 0x00c8cccb,
    0x00c8ccf4, 0x00acd949, 0x00b6b21e, 0x00be7079, 0x00b4c117,
    # the list routines the panel calls (charsel_gfx.c, compared by validate_charsel_gfx.py)
    0x00b4b848, 0x00b4bed3,
    # getters and std::string helpers
    0x009a13f4, 0x0095f977, 0x0129deaa, 0x009a5949, 0x009a5937, 0x009a59f6, 0x0095fb99,
    0x008e7940, 0x008e6d00, 0x008e83a0, 0x008e6d80, 0x008e7f90, 0x00950d4d, 0x0096a4d8, 0x00b3b292,
    0x00a8cc6f, 0x00968f81, 0x0096a1b1, 0x00950d3f, 0x0096a197, 0x008e7b00, 0x008e7410,
    0x009516a8, 0x0094c606, 0x008e5830, 0x008e8300, 0x0094f4af, 0x00cfc922, 0x00cfc94a,
    0x00aae509, 0x00aae601, 0x00abedc3, 0x00aaeadc)

RECORD, OBJECT = 0x3670, 0x3254
PREVIEW = 0x0a39d780
FAKE_BASE, FAKE_SIZE = 0x7e000000, 0x00100000
MANAGER, GFXMGR, MOVIE, UIMNG, SLOTMODE, LIMIT, MOVIEOBJ, MOVIEVT = (FAKE_BASE + (n << 12) for n in range(1, 9))
HANDLER94, OPTIONWIN, MENUWIN, SCENEOBJ, COUNTDOWN, SAVEOBJ, VT10, CAUTION = (FAKE_BASE + (n << 12)
                                                                               for n in range(9, 17))
UIWIN_AB0, UIWIN_4BB0 = UIMNG + 0xab0, UIMNG + 0x4bb0
WINDOW = FAKE_BASE + 0x20000
FILTER_OBJ, FILTERNAME_OBJ = 0x06fbac88, 0x06fbacd0
SELECTED, SHOWN, STATE, INIT_SCENE, FOV = 0x01cf1864, 0x01cf1154, 0x06fca2c4, 0x0bdc5ca2, 0x01cf1634
SCREEN_W, SCREEN_H, SSE3 = 0x01cf1624, 0x01cf1628, 0x0bdcb280
HERO_PTR = 0x0a39d754
NEW_ARRAY_VT = 0x008e0480


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def dumps(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def fhex(v):
    return '%08x' % struct.unpack('<I', struct.pack('<f', v))[0]


def i32(w):
    return struct.unpack('<i', struct.pack('<I', w & 0xffffffff))[0]


def cp949_lead(c):
    return 0x81 <= c <= 0xfe


def window_origin(mode, field, screen, base, axis):
    """0x00aae509 (x) / 0x00aae601 (y) by the movie's alignment mode (jump tables 0x00aae5dd /
    0x00aae6d5; static reading, an independent statement for the C side's inputs)."""
    s = f32(float(screen & 0xffffffff))
    groups = ({0, 1, 2}, {3, 5, 7}, {4, 6, 8}) if axis == 'x' else ({0, 3, 4}, {1, 5, 6}, {2, 7, 8})
    if mode in groups[0]:
        return f32(field - f32(f32(base - s) / 2.0))
    if mode in groups[1]:
        return field
    if mode in groups[2]:
        return f32(field - f32(base - s))
    return 0.0


# --------------------------------------------------------------------------- the C side

EMIT = CFUNCTYPE(None, c_void_p, c_char_p)
CHARFN = CFUNCTYPE(c_void_p, c_void_p, c_int32)
TEXTFN = CFUNCTYPE(c_void_p, c_void_p, c_int32)
LEADFN = CFUNCTYPE(c_int, c_void_p, c_uint8)


class Window(Structure):
    _fields_ = [('row', c_int32), ('count', c_int32), ('slots', c_uint8 * 10)]


class GfxEnv(Structure):
    _fields_ = [('context', c_void_p), ('character', CHARFN), ('global_text', TEXTFN), ('class_name', TEXTFN),
                ('name', c_void_p), ('emit', EMIT), ('selected', POINTER(c_int32)), ('shown', POINTER(c_int32)),
                ('slot_mode', c_uint8), ('slot_limit', c_int32), ('enter_refused', c_uint8), ('gfx_busy', c_uint8),
                ('window_flag_79', c_uint8), ('base_ready', c_uint8)]


class CcrWindow(Structure):
    _fields_ = [('create_open', c_uint8), ('flag_79', c_uint8), ('created', c_int32), ('limit', c_int32),
                ('board', c_int32 * 4), ('delete_target', c_int32), ('rename_mode', c_uint8),
                ('camera_offset', c_float * 3)]


class CcrEnv(Structure):
    _fields_ = [('gfx', POINTER(GfxEnv)), ('preview', c_void_p), ('protocol_state', POINTER(c_int32)),
                ('init_scene', POINTER(c_uint8)), ('camera_fov', POINTER(c_float)),
                ('filter', POINTER(c_char_p)), ('filter_count', c_int32),
                ('filter_name', POINTER(c_char_p)), ('filter_name_count', c_int32), ('lead_byte', LEADFN),
                ('window_x', c_float), ('window_y', c_float), ('window_scale', c_float),
                ('screen_width', c_int32), ('screen_height', c_int32), ('animation_running', c_uint8),
                ('base_render', c_uint8), ('scene', c_int32), ('menu_open', c_uint8), ('menu_check', c_uint8),
                ('shutdown_blocked', c_uint8)]


class Created(Structure):
    _fields_ = [('result', c_uint8), ('name', c_char * 10), ('slot', c_uint8), ('level', c_uint16),
                ('class_code', c_uint8), ('limit', c_uint8), ('created', c_uint8)]


def load_library():
    import subprocess
    directory = ROOT / 'reconstructed' / 'charsel'
    subprocess.run(['make', '-s', '-C', str(directory)], check=True)
    lib = ctypes.CDLL(str(directory / ('libcharsel.dylib' if sys.platform == 'darwin' else 'libcharsel.so')))
    W, C, E = POINTER(Window), POINTER(CcrWindow), POINTER(CcrEnv)
    sig = {
        'mu_ccr_show_create': [W, C, E, c_uint8], 'mu_ccr_restrict_classes': [C, E],
        'mu_ccr_set_selected_class': [C, E, c_uint8], 'mu_ccr_board_info': [C, E, c_int32, c_int32, c_int32, c_int32],
        'mu_ccr_enter_name': [C, E, c_char_p, ctypes.c_size_t, c_int32], 'mu_ccr_update_input': [E, c_char_p],
        'mu_ccr_update_count': [C, E, c_int32, c_int32], 'mu_ccr_reset_create': [E],
        'mu_ccr_created_answer': [W, C, E, POINTER(Created)],
        'mu_ccr_message_result': [W, C, E, c_int32, c_int32, c_char_p],
        'mu_ccr_delete_answer': [W, C, E, c_uint8], 'mu_ccr_render_hook': [C, E],
        'mu_ccr_class_from_server': [c_uint8], 'mu_ccr_class_name_text': [c_uint8, c_uint8],
        'mu_csm_toggle': [W, E], 'mu_csm_scene_windows': [W, E, c_uint8], 'mu_csm_event': [W, E, c_char_p]}
    for name, args in sig.items():
        getattr(lib, name).argtypes = args
    lib.mu_ccr_render_hook.restype = c_int
    lib.mu_ccr_class_from_server.restype = c_uint8
    lib.mu_ccr_class_name_text.restype = c_int32
    return lib


class CSide:
    def __init__(self, lib, case):
        self.lib, self.case, self.lines = lib, case, []
        self.buffers = {i: ctypes.create_string_buffer(bytes(img), RECORD) for i, img in case['records'].items()}
        self.preview = ctypes.create_string_buffer(bytes(case['preview']), RECORD)
        self.strings = []
        self._char = CHARFN(self.character)
        self._gt = TEXTFN(lambda ctx, n: self.cstr(f'GT{n}'))
        self._cls = TEXTFN(lambda ctx, n: self.cstr(f'CLASS{n}'))
        self._emit = EMIT(lambda ctx, s: self.lines.append(s.decode('latin1')))
        self._lead = LEADFN(lambda ctx, c: 1 if case['cp949'] and cp949_lead(c) else 0)
        self.selected, self.shown = c_int32(case['selected']), c_int32(case['shown'])
        self.list = Window(case['row'], case['count'], (c_uint8 * 10)(*case['slots']))
        self.gfx = GfxEnv(None, self._char, self._gt, self._cls, None, self._emit, ctypes.pointer(self.selected),
                          ctypes.pointer(self.shown), 0, 10, 0, 0, 0, 1)
        w = case['window']
        self.window = CcrWindow(w['open'], w['f79'], w['created'], w['limit'], (c_int32 * 4)(*w['board']),
                                w['target'], w['rename'], (c_float * 3)(*w['offset']))
        self.state, self.init_scene, self.fov = c_int32(case['state']), c_uint8(case['init']), c_float(case['fov'])
        self.filter = (c_char_p * max(1, len(case['filter'])))(*[s for s in case['filter']])
        self.filter_name = (c_char_p * max(1, len(case['filter_name'])))(*[s for s in case['filter_name']])
        ox = window_origin(case['align'], case['wx'], case['screen'][0], 1024.0, 'x')
        oy = window_origin(case['align'], case['wy'], case['screen'][1], 768.0, 'y')
        self.env = CcrEnv(ctypes.pointer(self.gfx), ctypes.addressof(self.preview), ctypes.pointer(self.state),
                          ctypes.pointer(self.init_scene), ctypes.pointer(self.fov),
                          self.filter, len(case['filter']), self.filter_name, len(case['filter_name']), self._lead,
                          ox, oy, case['wscale'], case['screen'][0], case['screen'][1], case['anim'], case['base'],
                          case['scene'], case['menu_open'], case['menu_check'], case['shutdown'])

    def cstr(self, s):
        b = ctypes.create_string_buffer(s.encode('latin1'))
        self.strings.append(b)
        return ctypes.addressof(b)

    def character(self, ctx, index):
        b = self.buffers.get(index)
        if b is None:
            b = self.buffers[index] = ctypes.create_string_buffer(RECORD)
        return ctypes.addressof(b)

    def run(self, family, args):
        L, w, c, e, lib = (ctypes.byref(self.list), ctypes.byref(self.window), None, ctypes.byref(self.env),
                           self.lib)
        ret = 0
        if family == 'show':
            lib.mu_ccr_show_create(L, w, e, args['flag'])
        elif family == 'restrict':
            lib.mu_ccr_restrict_classes(w, e)
        elif family == 'klass':
            lib.mu_ccr_set_selected_class(w, e, args['class'])
        elif family == 'board':
            lib.mu_ccr_board_info(w, e, *args['rect'])
        elif family == 'name':
            raw = args['name']
            lib.mu_ccr_enter_name(w, e, raw, len(raw), args['class'])
        elif family == 'input':
            lib.mu_ccr_update_input(e, args['text'])
        elif family == 'count':
            lib.mu_ccr_update_count(w, e, args['created'], args['limit'])
        elif family == 'created':
            p = args['packet']
            pk = Created(p['result'], p['name'], p['slot'], p['level'], p['class'], p['limit'], p['created'])
            lib.mu_ccr_created_answer(L, w, e, ctypes.byref(pk))
        elif family == 'message':
            lib.mu_ccr_message_result(L, w, e, args['id'], args['button'], args['text'])
        elif family == 'deleted':
            lib.mu_ccr_delete_answer(L, w, e, args['result'])
        elif family == 'render':
            ret = lib.mu_ccr_render_hook(w, e)
        elif family == 'menu':
            if args['op'] == 'toggle':
                lib.mu_csm_toggle(L, e)
            elif args['op'] == 'scene':
                lib.mu_csm_scene_windows(L, e, args['flag'])
            else:
                lib.mu_csm_event(L, e, args['event'].encode())
        win = self.window
        return {'lines': self.lines, 'list': [self.list.row, self.list.count, list(self.list.slots)],
                'window': [win.create_open, win.flag_79, win.created, win.limit, list(win.board), win.delete_target,
                           win.rename_mode, [fhex(v) for v in win.camera_offset]],
                'preview': sha256(self.preview.raw), 'records': {i: sha256(b.raw) for i, b in
                                                                 sorted(self.buffers.items())},
                'globals': [self.selected.value, self.shown.value, self.state.value, self.init_scene.value,
                            fhex(self.fov.value)], 'ret': ret & 0xff}


# --------------------------------------------------------------------------- the client side

class Harness:
    def __init__(self, text, data):
        self.text = text
        m = self.m = cm.Machine(text, data)
        m.uc.mem_map(FAKE_BASE, FAKE_SIZE, cm.UC_PROT_ALL)
        self.extent = {}
        for start in RUN:
            end = cm.function_extent(text, start)
            self.extent[start] = (end, sha256(text[start - cm.TEXT_BASE:end - cm.TEXT_BASE]))
            m.allow((start, end))
        self._stubs()

    def pins(self):
        return {f'{a:#010x}': h for a, (_, h) in sorted(self.extent.items())}

    # ---- memory helpers
    def ecx(self):
        return self.m.uc.reg_read(cm.UC_X86_REG_ECX)

    def cbytes(self, address, limit=8192):
        out = bytearray()
        while len(out) < limit:
            b = self.m.read(address + len(out), 1)[0]
            if not b:
                break
            out.append(b)
        return bytes(out)

    def cstr(self, address):
        return self.cbytes(address).decode('latin1')

    def heap_bytes(self, b):
        a = self.m.alloc(len(b) + 1, define=True)
        self.m.write(a, b + b'\0')
        return a

    def heap_cstr(self, s):
        key = ('c', s)
        if key not in self.c.strings:
            self.c.strings[key] = self.heap_bytes(s.encode('latin1'))
        return self.c.strings[key]

    def put_string(self, address, b):
        if isinstance(b, str):
            b = b.encode('latin1')
        if len(b) < 16:
            self.m.write(address, b + b'\0' * (16 - len(b)))
            cap = 15
        else:
            p = self.m.alloc(len(b) + 1, define=True)
            self.m.write(p, b + b'\0')
            self.m.write(address, struct.pack('<I', p) + b'\0' * 12)
            cap = len(b)
        self.m.write(address + 0x10, struct.pack('<II', len(b), cap))

    def get_bytes(self, address):
        size, cap = struct.unpack('<II', self.m.read(address + 0x10, 8))
        p = self.m.u32(address) if cap >= 16 else address
        return self.m.read(p, size)

    def get_string(self, address):
        return self.get_bytes(address).decode('latin1')

    def string_words(self, b):
        """A std::string passed by value: its six words."""
        tmp = self.m.alloc(0x18, define=True)
        self.put_string(tmp, b)
        return list(struct.unpack('<6I', self.m.read(tmp, 0x18)))

    def ref(self, address):
        t = self.c.table
        if t <= address < t + 400 * RECORD:
            index, offset = divmod(address - t, RECORD)
            return f'r{index}' if offset == 0 else f'r{index}+{offset:#x}'
        if PREVIEW <= address < PREVIEW + RECORD:
            return 'p' if address == PREVIEW else f'p+{address - PREVIEW:#x}'
        if address == WINDOW:
            return 'w'
        return f'{address:#x}' if address else '0'

    # ---- stubs
    def stub(self, address, handler, cdecl=False):
        cleanup = 0 if cdecl else cm.stdcall_cleanup(self.text, address)
        self.m.stub(address, lambda m: handler(), cleanup)

    def line(self, s):
        self.c.lines.append(s)

    def _stubs(self):
        m, s = self.m, self.stub
        args = m.args
        s(0x0095f6db, lambda: MANAGER, cdecl=True)
        s(0x00ac3bf7, lambda: GFXMGR, cdecl=True)
        s(0x011e228b, lambda: UIMNG, cdecl=True)
        s(0x0095f75d, lambda: SLOTMODE, cdecl=True)
        s(0x010a5cf2, lambda: LIMIT, cdecl=True)
        s(0x0185bdbd, lambda: 0, cdecl=True)
        nodes = lambda: self.c.nodes  # noqa: E731

        def ctor():
            nodes()[self.ecx()] = None
        s(0x00aad26b, ctor)
        s(0x00aad299, lambda: 0)

        def invoke_fmt():
            window, method, fmt = args(3)
            spec = self.cstr(fmt).split()
            words = args(3 + 2 * len(spec))[3:]
            out, k = [], 0
            for token in spec:
                if token == '%d':
                    out.append(i32(words[k]))
                    k += 1
                elif token == '%s':
                    out.append(self.cstr(words[k]))
                    k += 1
                elif token == '%f':
                    out.append(struct.unpack('<d', struct.pack('<II', words[k], words[k + 1]))[0])
                    k += 2
                else:
                    raise cm.CaseError(f'format {token}')
            self.line(f'invoke {self.cstr(method)} {dumps(out)}')
        s(0x00aae7e0, invoke_fmt, cdecl=True)
        s(0x00aaf23f, lambda: self.line(f'invoke {self.cstr(args(1)[0])} []'))
        s(0x00ab03cf, lambda: MOVIEOBJ)
        s(0x00ab041b, lambda: MOVIEOBJ)
        m.stub(NEW_ARRAY_VT, lambda mm: self.c.case['align'], 0)   # the movie's +0x78 (alignment mode)
        s(0x0095f027, lambda: self.heap_cstr(f'GT{args(1)[0]}'))

        def gt_string():
            n = args(1)[0]
            key = ('s', n)
            if key not in self.c.strings:
                a = m.alloc(0x18, define=True)
                self.put_string(a, f'GT{n}')
                self.c.strings[key] = a
            return self.c.strings[key]
        s(0x011753c3, gt_string)

        def str_ctor():
            self.put_string(self.ecx(), self.cbytes(args(1)[0]))
            return self.ecx()
        s(0x0094997e, str_ctor)

        def copy_ctor():
            self.put_string(self.ecx(), self.get_bytes(args(1)[0]))
            return self.ecx()
        s(0x008e80e0, copy_ctor)
        s(0x0191c490, lambda: 0, cdecl=True)   # operator delete
        s(0x0191c5a0, lambda: 0, cdecl=True)   # __chkstk (not reached by the stubbed senders)

        def strlen():
            return len(self.cbytes(args(1)[0]))
        s(0x0195a4b0, strlen, cdecl=True)

        def strncpy():
            dst, src, n = args(3)
            b = self.cbytes(src, n)[:n]
            m.write(dst, b + b'\0' * (n - len(b)))
            return dst
        s(0x0194c200, strncpy, cdecl=True)

        def memmove():
            dst, src, n = args(3)
            m.write(dst, m.read(src, n))
            return dst
        s(0x0194c780, memmove, cdecl=True)

        def memset():
            dst, value, n = args(3)
            m.write(dst, bytes([value & 0xff]) * n)
            return dst
        s(0x0194cd00, memset, cdecl=True)

        def memcmp():   # 0x0096120b(a, b, n): char_traits::compare -> 0x0194d65f
            a_, b_, n = args(3)
            x, y = m.read(a_, n), m.read(b_, n)
            return 0 if x == y else (1 if x > y else 0xffffffff)
        s(0x0096120b, memcmp, cdecl=True)

        def memchr():
            p, ch, n = args(3)
            data = m.read(p, n) if n else b''
            k = data.find(bytes([ch & 0xff]))
            return 0 if k < 0 else p + k
        s(0x019507c0, memchr, cdecl=True)

        def strcmp_eq():   # 0x0096c6da(a, b): 1 when equal
            a_, b_ = args(2)
            return 1 if self.cbytes(a_) == self.cbytes(b_) else 0
        s(0x0096c6da, strcmp_eq, cdecl=True)

        def sprintf():
            buf, fmt, value = args(3)
            f = self.cstr(fmt)
            text = f.replace('%d', str(i32(value)), 1).encode('latin1')
            m.write(buf, text + b'\0')
            return len(text)
        s(0x009619dd, sprintf, cdecl=True)

        def convert():
            dst, src = args(2)
            self.put_string(dst, self.get_bytes(src))
            return dst
        s(0x00a99d93, convert, cdecl=True)

        def convert_cstr():
            dst, src = args(2)
            self.put_string(dst, self.cbytes(src))
            return dst
        s(0x00b0c2f0, convert_cstr, cdecl=True)
        s(0x019ac155, lambda: 1 if self.c.case['cp949'] and cp949_lead(args(1)[0] & 0xff) else 0, cdecl=True)

        # recorded calls
        s(0x00af0ce9, lambda: self.line('call 00af0ce9'))
        s(0x009a4dd7, lambda: self.line('call 009a4dd7'))
        s(0x009a23d7, lambda: self.line('call 009a23d7'))
        s(0x01287a66, lambda: self.line('call 01287a66'), cdecl=True)
        s(0x0129debb, lambda: 0)

        def create_character():
            c, model, x, y, angle = args(5)
            self.line(f'call 0137d8a1 {self.ref(c)} {model} {i32(x)} {i32(y)} {angle:08x}')
        s(0x0137d8a1, create_character, cdecl=True)
        s(0x012affa4, lambda: self.line('call 012affa4 %s %d' % (self.ref(args(2)[0]), i32(args(2)[1]))), cdecl=True)
        s(0x0137c457, lambda: self.line(f'call 0137c457 {i32(args(1)[0])}'), cdecl=True)
        s(0x0137c276, lambda: self.line(f'call 0137c276 {i32(args(1)[0])}'), cdecl=True)

        def create_hero():
            w = args(6)
            self.line('call 0137f824 %d %d %d %08x %08x %08x' % (i32(w[0]), w[1], w[2], w[3], w[4], w[5]))
        s(0x0137f824, create_hero, cdecl=True)
        s(0x0129de8d, lambda: self.line('call 0129de8d %s %s' % (self.ref(self.ecx()),
                                                                 dumps(self.get_string(args(1)[0])))))
        s(0x0094f183, lambda: 0)   # the name's string destructor
        s(0x0121469f, lambda: HANDLER94, cdecl=True)
        s(0x00da9ff3, lambda: self.line(f'call 00da9ff3 {i32(args(1)[0])}'))

        def msg(kind):
            def h():
                if kind == 1:      # 0x00b3967c(owner, id, text, title, button, texttype, mode)
                    w = args(7)
                    self.line('call 00b3967c %s %d %s %s %d %d %d' % (
                        self.ref(w[0]), i32(w[1]), dumps(self.cstr(w[2])), dumps(self.cstr(w[3])), w[4], w[5], w[6]))
                elif kind == 2:    # 0x00b39648(owner, id, text, title, button1, button2, texttype, mode)
                    w = args(8)
                    self.line('call 00b39648 %s %d %s %s %d %d %d %d' % (
                        self.ref(w[0]), i32(w[1]), dumps(self.cstr(w[2])), dumps(self.cstr(w[3])), w[4], w[5], w[6],
                        w[7]))
                else:              # 0x00b3974a(owner, id, text, title, length, texttype, mode)
                    w = args(7)
                    self.line('call 00b3974a %s %d %s %s %d %d %d' % (
                        self.ref(w[0]), i32(w[1]), dumps(self.cstr(w[2])), dumps(self.cstr(w[3])), w[4], w[5], w[6]))
            return h
        s(0x00b3967c, msg(1))
        s(0x00b39648, msg(2))
        s(0x00b3974a, msg(4))
        s(0x00b399db, lambda: self.line('call 00b399db'))

        # create / rename / delete requests
        def packet_ctor(size):
            def h():
                m.write(self.ecx(), b'\0' * size)
                return self.ecx()
            return h
        s(0x009a4588, packet_ctor(0x10))
        s(0x00b4c5e2, packet_ctor(0x24))

        def send_create():
            p = self.ecx()
            name = m.read(p + 4, 10).split(b'\0')[0].decode('latin1')
            self.line(f'call 009a466c {dumps(name)} {m.read(p + 0xe, 1)[0]}')
        s(0x009a466c, send_create)
        s(0x009a4708, lambda: self.line('call 009a4708 %s %s' % (dumps(self.cstr(args(2)[0])),
                                                                 dumps(self.cstr(args(2)[1])))), cdecl=True)

        def send_delete():
            p = self.ecx()
            name = m.read(p + 4, 10).split(b'\0')[0].decode('latin1')
            pw = m.read(p + 0xe, 20).split(b'\0')[0].decode('latin1')
            self.line(f'call 00b4c76a {dumps(name)} {dumps(pw)}')
        s(0x00b4c76a, send_delete)

        # the create count's formatter: 0x009d59cc(fmt string, argument object, &int, out) and its str()
        def fmt_ctor():
            w = args(4)
            text = self.get_string(w[0])
            value = i32(m.u32(w[2]))
            self.c.formatted = text.replace('%d', str(value), 1)
            return self.ecx()
        s(0x009d59cc, fmt_ctor)
        s(0x009d40f5, lambda: self.ecx())

        def fmt_str():
            a = m.alloc(0x18, define=True)
            self.put_string(a, self.c.formatted)
            return a
        s(0x009d6d27, fmt_str)
        s(0x009d5f0d, lambda: 0)

        # the delete warning's string stream (0x00969613 ctor, 0x00944605 <<, 0x0096a5b7 str, 0x00969a1b dtor)
        def ss_ctor():
            self.c.stream = ''
            return self.ecx()
        s(0x00969613, ss_ctor)

        def ss_put():
            stream, text = args(2)
            self.c.stream += self.cstr(text)
            return stream
        s(0x00944605, ss_put, cdecl=True)

        def ss_str():
            out = args(1)[0]
            self.put_string(out, self.c.stream)
            return out
        s(0x0096a5b7, ss_str)
        s(0x00969a1b, lambda: 0)

        # delete answer callees
        s(0x0129f4a5, lambda: self.line('call 0129f4a5 %s %d' % (self.ref(self.ecx()), args(1)[0])))
        s(0x00c9ea70, lambda: self.line(f'call 00c9ea70 {self.ref(args(1)[0])}'), cdecl=True)
        s(0x009c104e, lambda: SCENEOBJ)
        s(0x0106ba49, lambda: self.line('call 0106ba49'))

        # render
        s(0x013960d2, lambda: (self.line('call 013960d2'), self.c.case['anim'])[1], cdecl=True)

        def walk():
            origin, offset, angle = args(3)
            o = m.read(offset, 12)
            a = m.read(angle, 12)
            self.line('call 01854879 %s %s' % (self.ref(origin), ' '.join(
                '%08x' % v for v in struct.unpack('<3I', o) + struct.unpack('<3I', a))))
        s(0x01854879, walk, cdecl=True)
        s(0x0184b27e, lambda: self.line('call 0184b27e %d %d %d %d' % tuple(i32(v) for v in args(4))), cdecl=True)
        s(0x016d4fe4, lambda: self.line('call 016d4fe4 %s %d %d %d %d %d' % (
            (self.ref(args(6)[0]),) + tuple(i32(v) for v in args(6)[1:]))), cdecl=True)
        s(0x01849ec4, lambda: self.line('call 01849ec4 %d %d %d %d' % tuple(i32(v) for v in args(4))), cdecl=True)
        s(0x0184b6dd, lambda: self.line('call 0184b6dd'), cdecl=True)
        s(0x00aadcbf, lambda: (self.line('call 00aadcbf'), self.c.case['base'])[1])

        # menu
        s(0x009b0bc1, lambda: self.c.case['scene'])

        def key_invoke():   # 0x00c8f9e8(method) on a KeyWindow
            method = self.cstr(args(1)[0])
            if self.ecx() == OPTIONWIN:
                self.line('call 00be7079')
            else:
                self.line(f'invoke {method} []')
        s(0x00c8f9e8, key_invoke)

        def new_object():
            nodes()[args(1)[0]] = {}
        s(0x00c8f5f4, new_object)

        def set_member():
            obj, name, value = args(3)
            nodes()[obj][self.cstr(name)] = self.cstr(value)
        s(0x00ae94c9, set_member)
        s(0x00c8fac2, lambda: self.line('invoke %s %s' % (self.cstr(args(2)[0]), dumps([nodes()[args(2)[1]]]))))
        s(0x00c5cd60, lambda: self.line('invoke %s [%d]' % (self.cstr(args(2)[0]), i32(args(2)[1]))))

        def vt10():
            which = {UIWIN_AB0: 'ab0', UIWIN_4BB0: '4bb0'}.get(self.ecx(), '?')
            self.line(f'call 00000010 {which} {args(1)[0]}')
        m.stub(VT10, lambda mm: vt10(), 4)
        s(0x00c8cbe2, lambda: (self.line('call 00c8cbe2'), self.c.case['menu_check'])[1])
        s(0x00b4c5a9, lambda: self.ecx())

        def save_order():
            p = self.ecx()
            self.line('call 00b4c6ce ' + ','.join(str(b) for b in m.read(p + 4, 10)))
        s(0x00b4c6ce, save_order)
        s(0x009a5ab2, lambda: self.line(f'call 009a5ab2 {i32(args(1)[0])}'), cdecl=True)
        s(0x00acd6ff, lambda: COUNTDOWN)
        s(0x00b39b2f, lambda: self.line('call 00b39b2f %s %d %s %s %d %d %d' % (
            self.ref(args(7)[0]), i32(args(7)[1]), dumps(self.cstr(args(7)[2])), dumps(self.cstr(args(7)[3])),
            args(7)[4], args(7)[5], args(7)[6])))
        s(0x009a595b, lambda: SAVEOBJ, cdecl=True)
        s(0x00c8cfa6, lambda: (self.line('call 00c8cfa6'), self.c.case['shutdown'])[1])
        s(0x00c8cfb9, lambda: self.line(f'call 00c8cfb9 {args(1)[0]}'))
        s(0x01206598, lambda: self.line('call 01206598'), cdecl=True)
        s(0x0095f160, lambda: OPTIONWIN)
        s(0x0095fbdc, lambda: 0)

    # ---- one case
    def run(self, case, family, args):
        m = self.m
        m.reset()
        m.uc.mem_write(FAKE_BASE, b'\0' * FAKE_SIZE)
        c = self.c = type('C', (), {})()
        c.case, c.lines, c.nodes, c.strings, c.formatted, c.stream = case, [], {}, {}, '', ''
        table = c.table = m.alloc(400 * RECORD, align=0x1000)
        m.write(MANAGER + 8, struct.pack('<I', table))
        for index, image in case['records'].items():
            m.write(table + index * RECORD, image)
        m.write(PREVIEW, case['preview'])
        m.write(GFXMGR + 0x22c, struct.pack('<I', WINDOW))
        m.write(GFXMGR + 0x90, struct.pack('<I', MOVIE))
        m.write(MOVIE, b'\0' * 0x100)
        m.write(SLOTMODE + 4, b'\0')
        m.write(LIMIT + 0x44, struct.pack('<i', 10))
        m.write(MOVIEOBJ, struct.pack('<I', MOVIEVT))
        m.write(MOVIEVT + 0x78, struct.pack('<I', NEW_ARRAY_VT))
        w = case['window']
        m.write(WINDOW, b'\0' * 0x100)
        m.write(WINDOW + 8, struct.pack('<I', MOVIEOBJ))
        m.write(WINDOW + 0x58, struct.pack('<f', case['wscale']))
        m.write(WINDOW + 0x70, struct.pack('<ff', case['wx'], case['wy']))
        m.write(WINDOW + 0x78, bytes([w['open'], w['f79']]))
        m.write(WINDOW + 0x7c, struct.pack('<ii', w['created'], w['limit']))
        m.write(WINDOW + 0x88, struct.pack('<4i', *w['board']) + struct.pack('<i', w['target']))
        m.write(WINDOW + 0x9c, bytes([w['rename']]))
        m.write(WINDOW + 0xa0, struct.pack('<ii', case['row'], case['count']) + bytes(case['slots']))
        m.write(WINDOW + 0xb4, struct.pack('<3f', *w['offset']))
        m.write(SELECTED, struct.pack('<i', case['selected']))
        m.write(SHOWN, struct.pack('<i', case['shown']))
        m.write(STATE, struct.pack('<i', case['state']))
        m.write(INIT_SCENE, bytes([case['init']]))
        m.write(FOV, struct.pack('<f', case['fov']))
        m.write(SCREEN_W, struct.pack('<ii', *case['screen']))
        m.write(HERO_PTR, struct.pack('<I', 0))
        m.write(SSE3, struct.pack('<I', 2))
        m.write(0x01cf65c0, struct.pack('<I', 0xbb40e64e))   # security cookie
        # the name tables: std::vector<std::string> at +0x38 (begin, end)
        for obj, words in ((FILTER_OBJ, case['filter']), (FILTERNAME_OBJ, case['filter_name'])):
            vec = m.alloc(0x18 * max(1, len(words)), define=True)
            for k, wd in enumerate(words):
                self.put_string(vec + 0x18 * k, wd)
            m.write(obj + 0x38, struct.pack('<III', vec, vec + 0x18 * len(words), vec + 0x18 * len(words)))
        # menu
        m.write(MENUWIN, b'\0' * 0x40)
        m.write(MENUWIN + 0x1c, bytes([case['menu_open']]))
        for obj in (UIWIN_AB0, UIWIN_4BB0):
            m.write(obj, struct.pack('<I', VT10 - 0x10))
        m.write(VT10 - 0x10, b'\0' * 0x10 + struct.pack('<I', VT10))
        ret = 0
        if family == 'show':
            m.call(0x00b49bf4, [args['flag']], ecx=WINDOW)
        elif family == 'restrict':
            m.call(0x00b4b684, ecx=WINDOW)
        elif family == 'klass':
            m.call(0x00b4a442, [args['class']], ecx=WINDOW)
        elif family == 'board':
            m.call(0x00b4a349, [v & 0xffffffff for v in args['rect']], ecx=WINDOW)
        elif family == 'name':
            m.call(0x00b49eca, self.string_words(args['name']) + [args['class']], ecx=WINDOW)
        elif family == 'input':
            m.call(0x00b4b31a, self.string_words(args['text']), ecx=WINDOW)
        elif family == 'count':
            m.call(0x00b49d0d, [args['created'], args['limit']], ecx=WINDOW)
        elif family == 'created':
            p = args['packet']
            pk = bytearray(0x30)
            pk[4] = p['result']
            pk[5:15] = p['name'].ljust(10, b'\0')[:10]
            pk[0xf] = p['slot']
            struct.pack_into('<H', pk, 0x10, p['level'])
            pk[0x12], pk[0x2b], pk[0x2c] = p['class'], p['limit'], p['created']
            a = m.alloc(len(pk), define=True)
            m.write(a, bytes(pk))
            m.call(0x0122b648, [a])
        elif family == 'message':
            text = self.heap_bytes(args['text']) if args['text'] is not None else 0
            m.call(0x00b49967, [args['id'], args['button'], text, 0], ecx=WINDOW)
        elif family == 'deleted':
            a = m.alloc(8, define=True)
            m.write(a, bytes([0, 0, 0, 0, args['result'], 0, 0, 0]))
            m.call(0x012326c4, [a])
        elif family == 'render':
            ret = m.call(0x00b49cd7, ecx=WINDOW)
        elif family == 'menu':
            if args['op'] == 'toggle':
                m.call(0x00c8c8b1, ecx=MENUWIN)
            elif args['op'] == 'scene':
                m.call(0x00c8ce3d, [args['flag']], ecx=MENUWIN)
            else:
                m.call(0x00c8c6be, [self.heap_cstr(args['event']), 0], ecx=MENUWIN)
        win = m.read(WINDOW, 0x100)
        row, count = struct.unpack_from('<ii', win, 0xa0)
        return {'lines': c.lines, 'list': [row, count, list(win[0xa8:0xb2])],
                'window': [win[0x78], win[0x79], *struct.unpack_from('<ii', win, 0x7c),
                           list(struct.unpack_from('<4i', win, 0x88)), struct.unpack_from('<i', win, 0x98)[0],
                           win[0x9c], ['%08x' % v for v in struct.unpack_from('<3I', win, 0xb4)]],
                'preview': sha256(m.read(PREVIEW, RECORD)),
                'records': {i: sha256(m.read(table + i * RECORD, RECORD)) for i in sorted(case['records'])},
                'globals': [i32(m.u32(SELECTED)), i32(m.u32(SHOWN)), i32(m.u32(STATE)), m.read(INIT_SCENE, 1)[0],
                            '%08x' % m.u32(FOV)], 'ret': ret & 0xff}


# --------------------------------------------------------------------------- cases

NAMES = [b'Nighty', b'DarkLord', b'abc', b'Ab', b'webzenGM', b'Ten1Letter', b'ElevenChars', b'with space',
         b'sym!bol', b'under_line', b'\xb0\xa1\xb0\xa2Kim', b'\xa1\xa1sym', b'\xc6\x60bad', b'\xc7\xa1ok',
         b'\xc8\x41oops', b'\x80x', b'Z9z0', b'GMadmin', b'fuckoff', b'Ad min', b'\xb0', b'a\xb0', b'TwentyCharacterName1']
FILTERS = [b'GM', b'admin', b'fuck', b'webzen', b'\xb0\xa2', b'', b'Ad', b'zz']


def record(g, index, live=None):
    r = bytearray(RECORD)
    r[OBJECT] = (g.random() < 0.7) if live is None else live
    r[0x12] = g.choice([0, 1, 2, 3, 5, 9, 10, 0x10, 0x21, g.randrange(256)])
    r[0x13] = g.randrange(4)
    r[0x14] = g.choice([0, 0, 1, 0x10, g.randrange(256)])
    r[0x17] = g.choice([0xff, 0, 0x20])
    r[0x3e] = g.randrange(256) if g.random() < 0.2 else index & 0xff
    r[0x3f] = g.choice([0, 0, 0xff])
    struct.pack_into('<H', r, 0x144, g.choice([1, 50, 400]))
    name = g.choice(NAMES)[:15]
    r[0x3658:0x3658 + 16] = name + b'\0' * (16 - len(name))
    struct.pack_into('<II', r, 0x3658 + 0x10, len(name), 15)
    return bytes(r)


def make_case(g, family):
    slots = [i if g.random() < 0.85 else 0xff for i in range(10)]
    selected = g.choice([-1, g.randrange(10), g.randrange(10), g.randrange(400)])
    records = {i: record(g, i) for i in range(10)}
    if 0 <= selected < 400:
        records.setdefault(selected, record(g, selected))
    records.setdefault(255, record(g, 255, live=0))
    for img in list(records.values()):
        records.setdefault(img[0x3e], record(g, img[0x3e]))
    preview = bytearray(RECORD)
    for k in range(0, RECORD, 64):
        preview[k] = g.randrange(256)
    preview[0x12] = g.randrange(20)
    preview[0x13] = g.randrange(4)
    window = {'open': g.choice([0, 1, 2]), 'f79': g.choice([0, 1]), 'created': g.choice([0, 1, 3, 5]),
              'limit': g.choice([3, 5, 10, 0]), 'board': [g.randrange(-50, 900) for _ in range(4)],
              'target': g.choice([-1, g.randrange(10)]), 'rename': g.choice([0, 0, 0, 1, 2]),
              'offset': [f32(g.uniform(-20, 20)) for _ in range(3)]}
    return {'records': records, 'preview': bytes(preview), 'slots': slots, 'row': g.randrange(10),
            'count': g.choice([10, 5, g.randrange(11)]), 'selected': selected,
            'shown': g.choice([-1, selected]), 'window': window, 'state': g.choice([0x33, 0x34]),
            'init': g.choice([0, 1]), 'fov': f32(g.choice([35.0, 10.0])), 'cp949': g.choice([0, 1]),
            'filter': g.sample(FILTERS, g.randrange(0, 4)), 'filter_name': g.sample(FILTERS, g.randrange(0, 4)),
            'align': g.randrange(10), 'wx': f32(g.uniform(-100, 400)), 'wy': f32(g.uniform(-100, 300)),
            'wscale': f32(g.choice([1.0, 2.0, 0.75, g.uniform(0.5, 2)])),
            'screen': [g.choice([640, 1024, 1722, 2560, 800]), g.choice([480, 768, 1048, 1440])],
            'anim': g.choice([0, 1]), 'base': g.choice([0, 1]), 'scene': g.choice([3, 5, 5, 6]),
            'menu_open': g.choice([0, 1]), 'menu_check': g.choice([0, 1]), 'shutdown': g.choice([0, 1])}


def make_args(g, family, case):
    if family == 'show':
        return {'flag': g.choice([0, 1, 2])}
    if family == 'klass':
        return {'class': g.choice([g.randrange(16), g.randrange(256)])}
    if family == 'board':
        return {'rect': [g.randrange(-100, 1500) for _ in range(4)]}
    if family == 'name':
        name = g.choice(NAMES)
        if g.random() < 0.2:
            name = bytes(g.choice(b'abcXYZ019 _\xb0\xa1\xc7\xa2') for _ in range(g.randrange(0, 14)))
        return {'name': name, 'class': g.randrange(16)}
    if family == 'input':
        return {'text': g.choice(NAMES)}
    if family == 'count':
        return {'created': g.randrange(-2, 8), 'limit': g.randrange(0, 8)}
    if family == 'created':
        return {'packet': {'result': g.choice([1, 1, 0, 2, 5, 3]), 'name': g.choice(NAMES)[:10],
                           'slot': g.randrange(5), 'level': g.choice([1, 400]),
                           'class': g.choice([0, 0x10, 0x20, 0x90, 0xa0, g.randrange(256)]),
                           'limit': g.randrange(6), 'created': g.randrange(6)}}
    if family == 'message':
        return {'id': g.choice([0x64, 0x65, 0x66, 0x67, 0x77, 0x68, 0]), 'button': g.choice([0, 1, 2]),
                'text': g.choice([b'secret', b'', b'p' * 25])}
    if family == 'deleted':
        case['window']['target'] = g.randrange(10)
        return {'result': g.choice([1, 1, 0, 2, 3, 4])}
    if family == 'menu':
        op = g.choice(['toggle', 'scene', 'event', 'event'])
        return {'op': op, 'flag': g.choice([0, 1]),
                'event': g.choice(['onLoad', 'onUnload', 'onClose', 'onExit', 'onServerSelectClick',
                                   'onCharSelectClick', 'onOptionClick', 'onOpenWindow'])}
    return {}


FAMILIES = ('show', 'restrict', 'klass', 'board', 'name', 'input', 'count', 'created', 'message', 'deleted',
            'render', 'menu')


def compare(a, b):
    if a == b:
        return None
    for k in a:
        if a[k] != b[k]:
            if k == 'lines':
                for i, (x, y) in enumerate(zip(a[k], b[k])):
                    if x != y:
                        return f'line {i}: client {x!r} / C {y!r}'
                return f'line count client {len(a[k])} {a[k][len(b[k]):][:2]} / C {len(b[k])} {b[k][len(a[k]):][:2]}'
            return f'{k}: client {a[k]!r} / C {b[k]!r}'
    return 'differs'


def run_cases(h, lib, count, seed, families=FAMILIES, mutate=None):
    g = random.Random(seed)
    results, coverage = {}, {}
    for family in families:
        r = results.setdefault(family, {'cases': 0, 'mismatches': 0, 'first': None})
        for _ in range(count):
            case = make_case(g, family)
            args = make_args(g, family, case)
            client = h.run(case, family, args)
            cside = CSide(lib, case)
            if mutate:
                mutate(cside, family, args)
            mine = cside.run(family, args)
            diff = compare(client, mine)
            r['cases'] += 1
            for ln in client['lines']:
                key = ln.split(' ')[1]
                coverage[f'{family}:{key}'] = coverage.get(f'{family}:{key}', 0) + 1
            if diff:
                r['mismatches'] += 1
                if r['first'] is None:
                    r['first'] = {'diff': diff, 'args': {k: (v if not isinstance(v, bytes) else v.hex())
                                                          for k, v in args.items()}}
    return results, coverage


def run_tables(h, lib):
    """Every class byte through 0x0139cc2e (flags 0, 1) and 0x0139ca62."""
    m = h.m
    out = {'classname': {'cases': 0, 'mismatches': 0, 'first': None},
           'serverclass': {'cases': 0, 'mismatches': 0, 'first': None}}
    case = make_case(random.Random(1), 'classname')
    for flag in (0, 1):
        for c in range(256):
            h.run(case, 'restrict', {})   # resets the machine with a case state
            ptr = m.call(0x0139cc2e, [c, flag])
            got = h.cstr(ptr)
            want = 'GT%d' % lib.mu_ccr_class_name_text(c, flag)
            r = out['classname']
            r['cases'] += 1
            if got != want:
                r['mismatches'] += 1
                r['first'] = r['first'] or f'class {c} flag {flag}: client {got} / C {want}'
    for c in range(256):
        h.run(case, 'restrict', {})
        got = m.call(0x0139ca62, [c]) & 0xff
        want = lib.mu_ccr_class_from_server(c)
        r = out['serverclass']
        r['cases'] += 1
        if got != want:
            r['mismatches'] += 1
            r['first'] = r['first'] or f'code {c}: client {got} / C {want}'
    return out


def emit_poses(h):
    m = h.m
    case = make_case(random.Random(2), 'klass')
    for c in range(16):
        h.run(case, 'restrict', {})
        m.write(PREVIEW + 0x12, bytes([c]))
        m.write(PREVIEW + OBJECT + 0x164, b'\xee' * 12)   # a sentinel: unwritten angles stay
        m.call(0x00b4a4a1, ecx=WINDOW)
        off = struct.unpack('<3f', m.read(WINDOW + 0xb4, 12))
        raw = m.read(PREVIEW + OBJECT + 0x164, 12)
        sets = raw != b'\xee' * 12
        ang = struct.unpack('<3f', raw) if sets else (0.0, 0.0, 0.0)
        sc = struct.unpack('<f', m.read(PREVIEW + OBJECT + 0xa0, 4))[0]
        f = lambda v: repr(f32(v)) + 'f'  # noqa: E731
        print('    {{%s, %s, %s}, {%s, %s, %s}, %s, %d},' % (*map(f, off), *map(f, ang), f(sc), sets))


def run_mutations(h, lib, count, seed):
    """Planted mistakes on the C side's inputs: each must be detected."""
    def no_lead(cside, family, args):            # the code page ignored (SBCS always)
        cside.case = dict(cside.case)
        cside.env.lead_byte = LEADFN(lambda ctx, c: 0)
        cside._lead = cside.env.lead_byte

    def filters_swapped(cside, family, args):     # FilterName read as Filter
        e = cside.env
        e.filter, e.filter_name = e.filter_name, e.filter
        e.filter_count, e.filter_name_count = e.filter_name_count, e.filter_count

    def wrong_offset(cside, family, args):       # the preview camera offset not subtracted
        for k in range(3):
            cside.window.camera_offset[k] = 0.0

    def server_class_raw(cside, family, args):   # the server's class code taken as the class byte
        p = args.get('packet')
        if p:
            p['class'] = cside.lib.mu_ccr_class_from_server(p['class']) if False else (p['class'] ^ 0x10)

    def scale_ignored(cside, family, args):
        cside.env.window_scale = 1.0

    def menu_scene(cside, family, args):
        cside.env.scene = 5 if cside.env.scene != 5 else 3

    plans = {'code page': ('name', no_lead), 'filter tables': ('name', filters_swapped),
             'camera offset': ('render', wrong_offset), 'server class code': ('created', server_class_raw),
             'window scale': ('board', scale_ignored), 'menu scene': ('menu', menu_scene)}
    out = {}
    for name, (family, mutate) in plans.items():
        results, _ = run_cases(h, lib, count, seed, (family,), mutate)
        out[name] = results[family]['mismatches'] > 0
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', type=Path, default=EVIDENCE / 'x86-text-capture-09/client-text.bin')
    ap.add_argument('--data', type=Path, default=EVIDENCE / 'image-data-run10/data-capture-10/client-image-data.bin')
    ap.add_argument('--cases', type=int, default=200, help='cases per family')
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--family', action='append', choices=FAMILIES)
    ap.add_argument('--mutations', action='store_true', help='also check that planted mistakes are detected')
    ap.add_argument('--emit-poses', action='store_true', help='print the 0x00b4a4a1 pose table and exit')
    ap.add_argument('--write-pins', action='store_true')
    ap.add_argument('--report', type=Path)
    a = ap.parse_args(argv)
    text, data = a.text.read_bytes(), a.data.read_bytes()
    if sha256(text) != TEXT_SHA256 or sha256(data) != DATA_SHA256:
        print('pinned inputs differ', file=sys.stderr)
        return 2
    h = Harness(text, data)
    pins = h.pins()
    if a.write_pins:
        PINNED_FILE.write_text(json.dumps(pins, indent=1) + '\n')
    elif PINNED_FILE.exists() and json.loads(PINNED_FILE.read_text()) != pins:
        print('executed routine bytes differ from the pins', file=sys.stderr)
        return 2
    if a.emit_poses:
        emit_poses(h)
        return 0
    lib = load_library()
    t0 = time.time()
    results, coverage = run_cases(h, lib, a.cases, a.seed, tuple(a.family or FAMILIES))
    if not a.family:
        results.update(run_tables(h, lib))
    report = {'cases_per_family': a.cases, 'results': results, 'coverage': coverage,
              'seconds': round(time.time() - t0, 1), 'pins': pins}
    if a.mutations:
        report['mutations'] = run_mutations(h, lib, max(20, a.cases // 5), a.seed + 1)
    total = sum(r['cases'] for r in results.values())
    bad = sum(r['mismatches'] for r in results.values())
    for family, r in results.items():
        first = r['first']
        print(f"{family:11s} {r['cases']:5d} cases {r['mismatches']:4d} mismatches"
              + (f"  first: {first['diff'] if isinstance(first, dict) else first}" if first else ''))
    print(f'total {total} cases, {bad} mismatches, {report["seconds"]} s')
    if a.mutations:
        caught = sum(1 for v in report['mutations'].values() if v)
        print(f'mutations detected: {caught}/{len(report["mutations"])}')
    if a.report:
        a.report.write_text(json.dumps(report, indent=1) + '\n')
    ok = bad == 0 and (not a.mutations or all(report['mutations'].values()))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
