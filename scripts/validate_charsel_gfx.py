#!/usr/bin/env python3
"""Compare the character-select GFx window with the client (NATIVE-CHARSEL-003).

The client routines of the CharacterSelect movie's game side run in Unicorn
over the pinned restored text and second image section
(scripts/client_ui_machine.py); reconstructed/charsel/charsel_gfx.c runs
through ctypes from the same state.  Both report every GFx invoke (method and
JSON arguments) and every call into another subsystem as text lines; the
lines, the window fields (+0xa0 row, +0xa4 count, +0xa8 row -> slot map),
SelectedHero 0x01cf1864, the shown character 0x01cf1154 and the return value
are compared.

Families (client entry points):

* list      0x00b4b927  SetSelectText from ten rows of CharactersClient
* show      0x00b4b848 (and 0x00b4b82c = list + show(1))
* select    0x00b4bd6c  a row clicked / double-clicked
* index     0x00b4bed3  SelectIndex
* arrow     0x00b4bfc2  the reorder arrows
* dispatch  0x00b4c1df  the movie's callbacks (OnCharSelectedClick, ...)
* init      0x00b4915b  InitText, InitStat, InitClassInfo (0x00b4aef1,
                        0x00b4b546) and the other set-up invokes

Run as client code: the routines above, the swap 0x00b4bf4e, the table lookup
0x009a13f4, the record getters 0x0095f977/0x0129deaa/0x0095f5cc, the manager
field getters 0x009a5949/0x009a5937/0x009a59f6/0x0095fb99/0x010a5dca, the
std::string accessors 0x008e7940/0x008e6d00/0x008e83a0, the GFx value
getters 0x00ab06fb/0x00aad487/0x00aad2f3/0x00aad334/0x00aad370 and the float
conversions 0x0191c5e0/0x0191c720.

Modelled (not client code): the GFx value API (value constructor/destructor,
NewObject 0x00aaf1c5, NewArray 0x00aaf205 and the movie's +0x38, the member
setters 0x00b0809d/0x00b2ced7/0x00b0bc6f, the array setter 0x00b48b7e, the
invokes 0x00aaf3ef/0x00aaf23f/0x00aae7e0), GlobalText ("GT<n>"), the class
name 0x0139cc2e ("CLASS<n>"), std::string construction and appends, sprintf,
the code-page conversions 0x00a99d93/0x00b0c2f0 (identity), and the two HTML
helpers 0x00ab4dc0/0x0096fe90 (implemented here from their static reading,
independently of the C file).  Every other call is a recording stub; any
call outside them stops the case.
"""
import argparse
import ctypes
from ctypes import CFUNCTYPE, POINTER, Structure, c_char_p, c_double, c_int, c_int32, c_uint8, c_void_p
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

TEXT_BYTES, TEXT_SHA256 = 23572480, '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BYTES, DATA_SHA256 = 2557764, 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'

RUN = (   # client code executed (pinned by SHA-256 in validate_charsel_gfx.pins.json)
    0x00b4b82c, 0x00b4b848, 0x00b4b927, 0x00b4bd6c, 0x00b4bed3, 0x00b4bf4e, 0x00b4bfc2, 0x00b4c1df,
    0x00b4915b, 0x00b4aef1, 0x00b4b546, 0x00b4c6aa,
    0x009a13f4, 0x0095f977, 0x0129deaa, 0x0095f5cc,
    0x009a5949, 0x009a5937, 0x009a59f6, 0x0095fb99, 0x010a5dca,
    0x008e7940, 0x008e6d00, 0x008e83a0,
    0x00ab06fb, 0x00aad487, 0x00aad2f3, 0x00aad334, 0x00aad370,
    0x0191c5e0, 0x0191c720)
PINNED_FILE = Path(__file__).with_suffix('.pins.json')
EVIDENCE = ROOT / 'evidence' if (ROOT / 'evidence').exists() else Path.home() / 'Documents/main-exe-study/evidence'

RECORD, OBJECT = 0x3670, 0x3254
FAKE_BASE, FAKE_SIZE = 0x7e000000, 0x00100000
MANAGER, GFXMGR, MOVIE, UIMNG, SLOTMODE, LIMIT, MOVIEOBJ, MOVIEVT = (FAKE_BASE + (n << 12) for n in range(1, 9))
WINDOW, HANDLER = FAKE_BASE + 0x20000, FAKE_BASE + 0x21000
GT_THIS, DL_THIS, FOCUS_THIS = 0x06fbab48, 0x06fba940, 0x01d22c60
SELECTED, SHOWN, SSE3 = 0x01cf1864, 0x01cf1154, 0x0bdcb280
NEW_ARRAY_VT = 0x008e0480   # int3 padding used as the stub address of the movie's vtable +0x38


def sha256(b):
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- reference strings (static readings)

HTML_COLOURS = ["#FFFFFF", "#7FB2FF", "#FF3319", "#FFCC19", "#19FF7F", "#A00000", "#FF19FF", "#0000A0", "#A06600",
                "#00FF00", "#666666", "#CC7FCC", "#B266FF", "#E56B0A", "#800080", "#FFFF00", "#00B0F0", "#00B050",
                "#CCFF00", "#00FFFF", "#BCBCBC", "#C1C469"]


def html(text, colour, bold):           # 0x00ab4dc0
    if text in ('', '\n'):
        return ''
    body = text.replace('<', '&lt;')
    c = HTML_COLOURS[colour] if 0 <= colour <= 0x15 else '#FFFFFF'
    return f"<font color='{c}'><b>{body}</b></font><br>" if bold == 1 else f"<font color='{c}'>{body}</font><br>"


def html_rgba(text, rgba, bold):        # 0x0096fe90
    if text in ('', '\n'):
        return ''
    body = text.replace('<', '&lt;')
    h = '%06x' % (((rgba & 0xff) << 16) | (rgba & 0xff00) | ((rgba & 0xff0000) >> 16))
    return f"<font color='#{h}'><b>{body}</b></font>" if bold == 1 else f"<font color='#{h}'>{body}</font>"


def dumps(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


# --------------------------------------------------------------------------- the C side

EMIT = CFUNCTYPE(None, c_void_p, c_char_p)
CHARFN = CFUNCTYPE(c_void_p, c_void_p, c_int32)
TEXTFN = CFUNCTYPE(c_void_p, c_void_p, c_int32)


class Window(Structure):
    _fields_ = [('row', c_int32), ('count', c_int32), ('slots', c_uint8 * 10)]


class Env(Structure):
    _fields_ = [('context', c_void_p), ('character', CHARFN), ('global_text', TEXTFN), ('class_name', TEXTFN),
                ('name', c_void_p), ('emit', EMIT), ('selected', POINTER(c_int32)), ('shown', POINTER(c_int32)),
                ('slot_mode', c_uint8), ('slot_limit', c_int32), ('enter_refused', c_uint8), ('gfx_busy', c_uint8),
                ('window_flag_79', c_uint8), ('base_ready', c_uint8)]


class Arg(Structure):
    _fields_ = [('type', c_int), ('number', c_double), ('string', c_char_p)]


def load_library():
    import subprocess
    directory = ROOT / 'reconstructed' / 'charsel'
    subprocess.run(['make', '-s', '-C', str(directory)], check=True)
    lib = ctypes.CDLL(str(directory / ('libcharsel.dylib' if sys.platform == 'darwin' else 'libcharsel.so')))
    for name in ('mu_csg_build_list', 'mu_csg_fill_and_show'):
        getattr(lib, name).argtypes = [POINTER(Window), POINTER(Env)]
    lib.mu_csg_show.argtypes = [POINTER(Window), POINTER(Env), c_uint8]
    lib.mu_csg_select_index.argtypes = [POINTER(Window), POINTER(Env), c_int32]
    lib.mu_csg_select_row.argtypes = [POINTER(Window), POINTER(Env), c_int32, c_uint8]
    lib.mu_csg_arrow.argtypes = [POINTER(Window), POINTER(Env), c_uint8]
    lib.mu_csg_callback.argtypes = [POINTER(Window), POINTER(Env), c_char_p, POINTER(Arg), c_int32]
    lib.mu_csg_init.argtypes = [POINTER(Window), POINTER(Env)]
    lib.mu_csg_init.restype = c_int
    return lib


class CSide:
    def __init__(self, lib, case):
        self.lib, self.case, self.lines = lib, case, []
        self.buffers = {i: ctypes.create_string_buffer(bytes(img), RECORD) for i, img in case['records'].items()}
        self.strings = []
        self.missing = []
        self._char = CHARFN(self.character)
        self._gt = TEXTFN(lambda ctx, n: self.cstr(f'GT{n}'))
        self._cls = TEXTFN(lambda ctx, n: self.cstr(f'CLASS{n}'))
        self._emit = EMIT(lambda ctx, s: self.lines.append(s.decode('utf-8')))
        self.selected, self.shown = c_int32(case['selected']), c_int32(case['shown'])
        self.window = Window(case['row'], case['count'], (c_uint8 * 10)(*case['slots']))
        self.env = Env(None, self._char, self._gt, self._cls, None, self._emit, ctypes.pointer(self.selected),
                       ctypes.pointer(self.shown), case['slot_mode'], case['slot_limit'], case['enter_refused'],
                       case['gfx_busy'], case['flag_79'], case['base_ready'])

    def cstr(self, s):
        b = ctypes.create_string_buffer(s.encode('latin1'))
        self.strings.append(b)
        return ctypes.addressof(b)

    def character(self, ctx, index):
        b = self.buffers.get(index)
        if b is None:
            self.missing.append(index)
            b = self.buffers[index] = ctypes.create_string_buffer(RECORD)
        return ctypes.addressof(b)

    def run(self, family, args):
        w, e, lib = ctypes.byref(self.window), ctypes.byref(self.env), self.lib
        ret = 0
        if family == 'list':
            lib.mu_csg_build_list(w, e)
        elif family == 'show':
            if args['fill']:
                lib.mu_csg_fill_and_show(w, e)
            else:
                lib.mu_csg_show(w, e, args['flag'])
        elif family == 'select':
            lib.mu_csg_select_row(w, e, args['row'], args['enter'])
        elif family == 'index':
            lib.mu_csg_select_index(w, e, args['slot'])
        elif family == 'arrow':
            lib.mu_csg_arrow(w, e, args['up'])
        elif family == 'dispatch':
            values = (Arg * max(1, len(args['values'])))()
            for i, (t, v) in enumerate(args['values']):
                values[i].type = t
                if t == 4:
                    values[i].string = v.encode('latin1')
                else:
                    values[i].number = float(v)
            lib.mu_csg_callback(w, e, args['name'].encode(), values, len(args['values']))
        elif family == 'init':
            ret = lib.mu_csg_init(w, e)
        return {'lines': self.lines, 'row': self.window.row, 'count': self.window.count,
                'slots': list(self.window.slots), 'selected': self.selected.value, 'shown': self.shown.value,
                'ret': ret & 0xff}


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

    def cstr(self, address):
        out = bytearray()
        while len(out) < 4096:
            b = self.m.read(address + len(out), 1)[0]
            if not b:
                break
            out.append(b)
        return out.decode('latin1')

    def heap_cstr(self, s):
        key = ('c', s)
        if key not in self.c.strings:
            a = self.m.alloc(len(s) + 1, define=True)
            self.m.write(a, s.encode('latin1') + b'\0')
            self.c.strings[key] = a
        return self.c.strings[key]

    def put_string(self, address, s):
        """An MSVC std::string (buffer/pointer +0, size +0x10, capacity +0x14)."""
        b = s.encode('latin1')
        if len(b) < 16:
            self.m.write(address, b + b'\0' * (16 - len(b)))
            cap = 15
        else:
            p = self.m.alloc(len(b) + 1, define=True)
            self.m.write(p, b + b'\0')
            self.m.write(address, struct.pack('<I', p) + b'\0' * 12)
            cap = len(b)
        self.m.write(address + 0x10, struct.pack('<II', len(b), cap))

    def get_string(self, address):
        size, cap = struct.unpack('<II', self.m.read(address + 0x10, 8))
        p = self.m.u32(address) if cap >= 16 else address
        return self.m.read(p, size).decode('latin1')

    def record_ref(self, address):
        t = self.c.table
        if t <= address < t + 400 * RECORD:
            index, offset = divmod(address - t, RECORD)
            return f'r{index}' if offset == 0 else f'r{index}+{offset:#x}'
        return f'{address:#x}'

    # ---- stubs
    def stub(self, address, handler, cdecl=False):
        cleanup = 0 if cdecl else cm.stdcall_cleanup(self.text, address)
        self.m.stub(address, lambda m: handler(), cleanup)

    def line(self, s):
        self.c.lines.append(s)

    def _stubs(self):
        m, s = self.m, self.stub
        args = m.args
        # singletons
        s(0x0095f6db, lambda: MANAGER, cdecl=True)
        s(0x00ac3bf7, lambda: GFXMGR, cdecl=True)
        s(0x011e228b, lambda: UIMNG, cdecl=True)
        s(0x0095f75d, lambda: SLOTMODE, cdecl=True)
        s(0x010a5cf2, lambda: LIMIT, cdecl=True)
        s(0x0185bdbd, lambda: 0, cdecl=True)
        # GFx values
        nodes = lambda: self.c.nodes  # noqa: E731

        def ctor():
            nodes()[self.ecx()] = None
        s(0x00aad26b, ctor)
        s(0x00aad299, lambda: 0)

        def new_object():
            nodes()[args(1)[0]] = {}
        s(0x00aaf1c5, new_object)

        def new_array():
            nodes()[args(1)[0]] = []
        s(0x00aaf205, new_array)
        self.m.stub(NEW_ARRAY_VT, lambda m: new_array(), 4)

        def set_member(kind):
            def h():
                obj, name, value = args(3)
                key = self.cstr(name)
                if kind == 's':
                    nodes()[obj][key] = self.cstr(value)
                elif kind == 'i':
                    nodes()[obj][key] = struct.unpack('<i', m.read(value, 4))[0]
                else:
                    nodes()[obj][key] = bool(m.read(value, 1)[0])
            return h
        s(0x00b0809d, set_member('s'))
        s(0x00b2ced7, set_member('i'))
        s(0x00b0bc6f, set_member('b'))

        def array_set():
            array, index, value = args(3)
            a = nodes()[array]
            while len(a) <= index:
                a.append(None)
            a[index] = nodes()[value]
        s(0x00b48b7e, array_set)

        def invoke_value():
            method, value = args(2)
            self.line(f'invoke {self.cstr(method)} {dumps([nodes()[value]])}')
        s(0x00aaf3ef, invoke_value)

        def invoke_none():
            self.line(f'invoke {self.cstr(args(1)[0])} []')
        s(0x00aaf23f, invoke_none)

        def invoke_fmt():
            window, method, fmt = args(3)
            spec = self.cstr(fmt).split()
            words = args(3 + 2 * len(spec))[3:]
            out, k = [], 0
            for token in spec:
                if token == '%d':
                    out.append(struct.unpack('<i', struct.pack('<I', words[k]))[0])
                    k += 1
                elif token == '%s':
                    out.append(self.cstr(words[k]))
                    k += 1
                else:
                    raise cm.CaseError(f'format {token}')
            self.line(f'invoke {self.cstr(method)} {dumps(out)}')
        s(0x00aae7e0, invoke_fmt, cdecl=True)
        # movie holder of the window (+8)
        s(0x00ab03cf, lambda: MOVIEOBJ)
        s(0x00ab041b, lambda: MOVIEOBJ)
        # text
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
        s(0x0139cc2e, lambda: self.heap_cstr(f'CLASS{args(2)[0]}'), cdecl=True)

        def str_ctor():
            self.put_string(self.ecx(), self.cstr(args(1)[0]))
            return self.ecx()
        s(0x0094997e, str_ctor)

        def push_back():
            a = self.ecx()
            self.put_string(a, self.get_string(a) + chr(args(1)[0] & 0xff))
        s(0x008e5910, push_back)

        def append():
            a = self.ecx()
            self.put_string(a, self.get_string(a) + self.cstr(args(1)[0]))
            return a
        s(0x0094b9f7, append)

        def copy_ctor():
            self.put_string(self.ecx(), self.get_string(args(1)[0]))
            return self.ecx()
        s(0x008e80e0, copy_ctor)
        s(0x0191c490, lambda: 0, cdecl=True)   # operator delete

        def memset():
            dst, value, n = args(3)
            m.write(dst, bytes([value & 0xff]) * n)
            return dst
        s(0x0194cd00, memset, cdecl=True)

        def strcmp():
            a_, b_ = (self.cstr(w) for w in args(2))
            return 0 if a_ == b_ else (1 if a_ > b_ else 0xffffffff)
        s(0x0195a3d0, strcmp, cdecl=True)

        def html_stub():
            out, text, colour, bold = args(4)
            self.put_string(out, html(self.cstr(text), colour, bold & 0xff))
            return out
        s(0x00ab4dc0, html_stub, cdecl=True)

        def html_rgba_stub():
            out, text, rgba, bold, _ = args(5)
            self.put_string(out, html_rgba(self.cstr(text), rgba, bold & 0xff))
            return out
        s(0x0096fe90, html_rgba_stub, cdecl=True)

        def sprintf():
            buf, fmt, value = args(3)
            if self.cstr(fmt) != '%d':
                raise cm.CaseError('sprintf format')
            text = str(struct.unpack('<i', struct.pack('<I', value))[0]).encode()
            m.write(buf, text + b'\0')
            return len(text)
        s(0x009619dd, sprintf, cdecl=True)

        def convert():
            dst, src = args(2)
            self.put_string(dst, self.get_string(src))
            return dst
        s(0x00a99d93, convert, cdecl=True)

        def convert_cstr():
            dst, src = args(2)
            self.put_string(dst, self.cstr(src))
            return dst
        s(0x00b0c2f0, convert_cstr, cdecl=True)

        # recorded calls
        def webzen():
            self.line(f'call 0129debb {self.record_ref(self.ecx())}')
            name = self.get_string(self.ecx() + 0x3658)
            return 1 if 'webzen' in name else 0
        s(0x0129debb, webzen)
        s(0x00af0ce9, lambda: self.line('call 00af0ce9'))
        s(0x009a4dd7, lambda: self.line('call 009a4dd7'))
        s(0x010b03cb, lambda: self.line(f'call 010b03cb {self.record_ref(args(1)[0])}'))
        s(0x00b49bf4, lambda: self.line(f'call 00b49bf4 {args(1)[0] & 0xff}'))
        s(0x009a5920, lambda: self.line(f'call 009a5920 {args(1)[0] & 0xff}'))
        s(0x00b4b684, lambda: self.line('call 00b4b684'))

        def refuse():
            sel = struct.unpack('<i', struct.pack('<I', args(1)[0]))[0]
            self.line(f'call 009a5029 {sel}')
            return self.c.case['enter_refused']
        s(0x009a5029, refuse)
        s(0x0185a75a, lambda: self.line(f'call 0185a75a {args(1)[0]}'), cdecl=True)
        s(0x00aaf5d3, lambda: self.line(f'call 00aaf5d3 {self.cstr(args(2)[1])}'))
        s(0x00aae6f9, lambda: self.c.case['gfx_busy'])
        s(0x00aadbc3, lambda: (self.line('call 00aadbc3'), self.c.case['base_ready'])[1])
        s(0x00b4a442, lambda: self.line(f'call 00b4a442 {struct.unpack("<i", struct.pack("<I", args(1)[0]))[0]}'))
        s(0x00b4a349, lambda: self.line('call 00b4a349 ' + ' '.join(
            str(struct.unpack('<i', struct.pack('<I', w))[0]) for w in args(4))))
        s(0x00b4c806, lambda: self.line(f'call 00b4c806 {struct.unpack("<i", struct.pack("<I", args(1)[0]))[0]}'))

        def by_value_string(extra):
            esp = m.uc.reg_read(cm.UC_X86_REG_ESP)
            text = self.get_string(esp + 4)
            if extra:
                n = struct.unpack('<i', m.read(esp + 4 + 0x18, 4))[0]
                return f'{text} {n}'
            return text
        s(0x00b49eca, lambda: self.line('call 00b49eca ' + by_value_string(True)))
        s(0x00b4b31a, lambda: self.line('call 00b4b31a ' + by_value_string(False)))

    # ---- one case
    def run(self, case, family, args):
        m = self.m
        m.reset()
        m.uc.mem_write(FAKE_BASE, b'\0' * FAKE_SIZE)
        c = self.c = type('C', (), {})()
        c.case, c.lines, c.nodes, c.strings = case, [], {}, {}
        table = c.table = m.alloc(400 * RECORD, align=0x1000)
        m.write(MANAGER + 8, struct.pack('<I', table))
        for index, image in case['records'].items():
            m.write(table + index * RECORD, image)
        m.write(GFXMGR + 0x22c, struct.pack('<I', WINDOW))
        m.write(GFXMGR + 0x90, struct.pack('<I', MOVIE))
        m.write(SLOTMODE + 4, bytes([case['slot_mode']]))
        m.write(LIMIT + 0x44, struct.pack('<i', case['slot_limit']))
        m.write(MOVIEOBJ, struct.pack('<I', MOVIEVT))
        m.write(MOVIEVT + 0x38, struct.pack('<I', NEW_ARRAY_VT))
        m.write(WINDOW + 8, struct.pack('<I', MOVIEOBJ))
        m.write(WINDOW + 0x79, bytes([case['flag_79']]))
        m.write(WINDOW + 0x9c, b'\0')
        m.write(WINDOW + 0xa0, struct.pack('<ii', case['row'], case['count']) + bytes(case['slots']))
        m.write(HANDLER + 0x10, struct.pack('<I', WINDOW))
        m.write(SELECTED, struct.pack('<i', case['selected']))
        m.write(SHOWN, struct.pack('<i', case['shown']))
        m.write(SSE3, struct.pack('<I', 2))
        m.write(0x01cf65c0, struct.pack('<I', 0xbb40e64e))   # security cookie
        ret = 0
        if family == 'list':
            m.call(0x00b4b927, ecx=WINDOW)
        elif family == 'show':
            if args['fill']:
                m.call(0x00b4b82c, ecx=WINDOW)
            else:
                m.call(0x00b4b848, [args['flag']], ecx=WINDOW)
        elif family == 'select':
            m.call(0x00b4bd6c, [args['row'], args['enter']], ecx=WINDOW)
        elif family == 'index':
            m.call(0x00b4bed3, [args['slot']], ecx=WINDOW)
        elif family == 'arrow':
            m.call(0x00b4bfc2, [args['up']], ecx=WINDOW)
        elif family == 'dispatch':
            values = args['values']
            array = m.alloc(16 * max(1, len(values)), define=True)
            for i, (t, v) in enumerate(values):
                payload = (struct.pack('<I', self.heap_cstr(v)) + b'\0' * 4 if t == 4 else
                           bytes([1 if v else 0]) + b'\0' * 7 if t == 2 else struct.pack('<d', float(v)))
                m.write(array + 16 * i, struct.pack('<II', 0, t) + payload)
            name = self.heap_cstr(args['name'])
            m.call(0x00b4c1df, [MOVIE, name, array, len(values)], ecx=HANDLER)
        elif family == 'init':
            ret = m.call(0x00b4915b, ecx=WINDOW)
        row, count = struct.unpack('<ii', m.read(WINDOW + 0xa0, 8))
        return {'lines': c.lines, 'row': row, 'count': count, 'slots': list(m.read(WINDOW + 0xa8, 10)),
                'selected': struct.unpack('<i', m.read(SELECTED, 4))[0],
                'shown': struct.unpack('<i', m.read(SHOWN, 4))[0], 'ret': ret & 0xff}


# --------------------------------------------------------------------------- cases

NAMES = ['Nighty', 'DarkLord', 'MuseElf', 'webzenGM', 'a<b>c', 'X', 'TenLetters', 'Summoner', 'webzen', 'Q']


def record(g, index, live=None):
    r = bytearray(RECORD)
    r[OBJECT] = (g.random() < 0.7) if live is None else live
    r[0x12] = g.choice([0, 1, 2, 3, 4, 5, 6, 0x10, 0x21, 0x13, 0x35, g.randrange(256)])
    r[0x14] = g.choice([0, 0, 0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, g.randrange(256)])
    r[0x17] = g.choice([0xff, 0, 0x20, 0x40, 0x80, g.randrange(256)])
    r[0x3e] = g.randrange(256) if g.random() < 0.3 else index & 0xff
    struct.pack_into('<H', r, 0x144, g.choice([1, 50, 400, 999, 1200, g.randrange(65536)]))
    name = g.choice(NAMES).encode()[:15]
    r[0x3658:0x3658 + 16] = name + b'\0' * (16 - len(name))
    struct.pack_into('<II', r, 0x3658 + 0x10, len(name), 15)
    return bytes(r)


def make_case(g, family):
    slots = [g.choice([g.randrange(10), g.randrange(400), 0xff, i]) & 0xff for i in range(10)]
    if g.random() < 0.3:
        slots = [i if g.random() < 0.8 else 0xff for i in range(10)]
    selected = g.choice([-1, g.randrange(10), g.randrange(400), 400, g.randrange(-5, 5)])
    indices = set(slots) | {k for k in (selected, ) if 0 <= k < 400}
    records = {i: record(g, i) for i in indices}
    records.setdefault(255, record(g, 255, live=g.random() < 0.1))   # row byte 0xff reads CharactersClient[255]
    if family in ('arrow', 'dispatch'):   # the arrows' rebuild reads the records behind the keys as well
        for img in list(records.values()):
            records.setdefault(img[0x3e], record(g, img[0x3e]))
    return {'records': records, 'slots': slots, 'row': g.choice([0, g.randrange(10)]),   # +0xa0 stays 0..9 (select_row and the arrow bound keep it there)
           
            'count': g.choice([10, g.randrange(12), 5]), 'selected': selected,
            'shown': g.choice([-1, selected, g.randrange(10)]), 'slot_mode': g.choice([0, 1]),
            'slot_limit': g.choice([5, 10, g.randrange(12)]), 'enter_refused': g.choice([0, 0, 1]),
            'gfx_busy': g.choice([0, 0, 1]), 'flag_79': g.choice([0, 1]), 'base_ready': g.choice([1, 1, 0])}


def make_args(g, family):
    if family == 'show':
        return {'fill': g.random() < 0.4, 'flag': g.choice([0, 1, 2])}
    if family == 'select':
        return {'row': g.choice([g.randrange(10), g.randrange(10), -1, 10, 255]), 'enter': g.choice([0, 1, 2])}
    if family == 'index':
        return {'slot': g.choice([g.randrange(10), -1, g.randrange(400)])}
    if family == 'arrow':
        return {'up': g.choice([0, 1, 2])}
    if family == 'dispatch':
        name = g.choice(['OnCharSelectedClick', 'OnCharSelectedDClick', 'onCharSelArrow', 'SetSelectedClass',
                         'SetCreateBoardInfo', 'OnEnterCharacterName', 'OnClickCreateCancel', 'UpdateInput',
                         'OnClickCreateCharacter', 'UIInit', 'requestWindowPos'])
        if name in ('OnCharSelectedClick', 'OnCharSelectedDClick'):
            values = [(3, g.choice([g.randrange(10), 0.0, 9.0, 3.7, 12.0]))]
        elif name == 'onCharSelArrow':
            values = [(2, g.choice([True, False]))]
        elif name == 'SetCreateBoardInfo':
            values = [(3, g.uniform(-50, 900)) for _ in range(4)]
        elif name == 'OnEnterCharacterName':
            values = [(4, g.choice(NAMES)), (3, g.randrange(16))]
        elif name == 'UpdateInput':
            values = g.choice([[(4, 'abc')], [(3, 1.0)], [(4, 'x'), (4, 'y')]])
        elif name == 'SetSelectedClass':
            values = [(3, g.randrange(16))]
        else:
            values = [(4, 'g_mcCharacterSelect')]
        return {'name': name, 'values': values}
    return {}


FAMILIES = ('list', 'show', 'select', 'index', 'arrow', 'dispatch', 'init')


def compare(a, b):
    if a == b:
        return None
    for k in a:
        if a[k] != b[k]:
            if k == 'lines':
                for i, (x, y) in enumerate(zip(a[k], b[k])):
                    if x != y:
                        return f'line {i}: client {x!r} / C {y!r}'
                return f'line count client {len(a[k])} / C {len(b[k])}'
            return f'{k}: client {a[k]!r} / C {b[k]!r}'
    return 'differs'


def run_cases(h, lib, count, seed, families=FAMILIES, mutate=None):
    g = random.Random(seed)
    results, coverage = {}, {}
    for family in families:
        r = results.setdefault(family, {'cases': 0, 'mismatches': 0, 'first': None})
        for _ in range(count):
            case = make_case(g, family)
            args = make_args(g, family)
            client = h.run(case, family, args)
            cside = CSide(lib, case)
            if mutate:
                mutate(cside, family, args)
            mine = cside.run(family, args)
            diff = compare(client, mine)
            r['cases'] += 1
            for ln in client['lines']:
                key = ln.split(' ')[1] if ln.startswith('invoke') else ln.split(' ')[1]
                coverage[f'{family}:{key}'] = coverage.get(f'{family}:{key}', 0) + 1
            if diff:
                r['mismatches'] += 1
                if r['first'] is None:
                    r['first'] = {'diff': diff, 'args': args}
    return results, coverage


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', type=Path, default=EVIDENCE / 'x86-text-capture-09/client-text.bin')
    ap.add_argument('--data', type=Path, default=EVIDENCE / 'image-data-run10/data-capture-10/client-image-data.bin')
    ap.add_argument('--cases', type=int, default=200, help='cases per family')
    ap.add_argument('--seed', type=int, default=20261018)
    ap.add_argument('--family', action='append', choices=FAMILIES)
    ap.add_argument('--mutations', action='store_true', help='also check that planted mistakes are detected')
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
    lib = load_library()
    t0 = time.time()
    results, coverage = run_cases(h, lib, a.cases, a.seed, tuple(a.family or FAMILIES))
    report = {'cases_per_family': a.cases, 'results': results, 'coverage': coverage,
              'seconds': round(time.time() - t0, 1), 'pins': pins}
    if a.mutations:
        report['mutations'] = run_mutations(h, lib, max(20, a.cases // 5), a.seed + 1)
    total = sum(r['cases'] for r in results.values())
    bad = sum(r['mismatches'] for r in results.values())
    for family, r in results.items():
        print(f"{family:9s} {r['cases']:5d} cases {r['mismatches']:4d} mismatches"
              + (f"  first: {r['first']['diff']}" if r['first'] else ''))
    print(f'total {total} cases, {bad} mismatches, {report["seconds"]} s')
    if a.mutations:
        caught = sum(1 for v in report['mutations'].values() if v)
        print(f'mutations detected: {caught}/{len(report["mutations"])}')
    if a.report:
        a.report.write_text(json.dumps(report, indent=1) + '\n')
    ok = bad == 0 and (not a.mutations or all(report['mutations'].values()))
    return 0 if ok else 1


def run_mutations(h, lib, count, seed):
    """Planted mistakes on the C side's inputs and outputs: each must be detected."""
    def wrong_guild(cside, family, args):         # textState from GT 0x1e8 for every status
        old = cside._gt
        cside._gt = TEXTFN(lambda ctx, n: old(ctx, 0x1e8 if n in (0x532, 0x516, 0x515, 0x514) else n))
        cside.env.global_text = cside._gt

    def swapped_selection(cside, family, args):   # selected and shown swapped by the reconstruction
        cside.env.selected, cside.env.shown = cside.env.shown, cside.env.selected

    def arrow_inverted(cside, family, args):
        if family == 'arrow':
            args['up'] = 0 if args['up'] == 1 else 1

    def enter_ignored(cside, family, args):
        if family == 'select':
            args['enter'] = 0

    def slot_limit_off(cside, family, args):
        cside.env.slot_limit = 99

    plans = {'guild status text': ('list', wrong_guild), 'selection globals': ('select', swapped_selection),
             'arrow direction': ('arrow', arrow_inverted), 'double click': ('select', enter_ignored),
             'locked rows': ('list', slot_limit_off)}
    out = {}
    for name, (family, mutate) in plans.items():
        results, _ = run_cases(h, lib, count, seed, (family,), mutate)
        out[name] = results[family]['mismatches'] > 0
    return out


if __name__ == '__main__':
    sys.exit(main())
