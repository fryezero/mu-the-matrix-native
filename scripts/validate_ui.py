#!/usr/bin/env python3
"""Compare the reconstructed 2D interface layer with the client (NATIVE-UI-001).

Each case runs an actual client routine in Unicorn over the pinned restored
text and second image section (scripts/client_ui_machine.py) and the
reconstruction in reconstructed/ui through ctypes, then compares the two
streams of platform calls (OpenGL, GLU, GDI) word for word: floats by bit
pattern, texture uploads by the SHA-256 of the uploaded pixels.

Client routines run unmodified:
  ConvertX/Y 0x01850636/0x01850679, BindTexture 0x0184acf6, the GL state
  wrappers 0x0184a6b7..0x0184aa2b, BeginBitmap/EndBitmap 0x0184f793/0x0184f8d7,
  RenderBitmap 0x0184dcb1, RenderColor 0x0184d9bb, EndRenderColor 0x0184dc62,
  CSprite 0x010ad7b2/0x010ad847/0x010add3c/0x010adfe4/0x010ae63d/0x00986f8a,
  CGaugeBar 0x00aac91b/0x00aac99a/0x00aacbdd/0x00aacceb/0x00aacf9e/0x00aacfd6,
  CreateTitleSceneUI 0x011e230d, RenderTitleSceneUI 0x011e2c8c,
  CUIRenderTextOriginal::RenderText/WriteText/UploadText
  0x0119ff3e/0x011a0431/0x011a054e, OpenTga 0x00c988fc.

Modelled explicitly (not client code): the uncaptured globals (window size,
screen rates, GL cache flags, projection parameters), BITMAP_t records
returned by the texture-table lookups 0x00ebbec8/0x00c97ce3, C runtime
helpers (operator new/delete, memset, memcpy, strlen, fopen/fseek/ftell/
fread/fclose), MSVC std::string/std::map bookkeeping in OpenTga, the 3D
camera setup 0x0184adc7, the loading timer, GFx hooks and the cursor update
0x0184b6dd (recorded as markers), and GDI text metrics/rasterisation
(a deterministic synthetic font shared by both sides).
"""
import argparse
import ctypes
from ctypes import (CFUNCTYPE, POINTER, Structure, c_float, c_int, c_int32, c_size_t, c_uint8, c_uint32,
                    c_void_p, c_char_p)
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import model_hierarchy_common as common  # noqa: E402

OPS = [None, 'glMatrixMode', 'glPushMatrix', 'glPopMatrix', 'glLoadIdentity', 'glViewport', 'glBegin', 'glEnd',
       'glVertex2f', 'glTexCoord2f', 'glColor4f', 'glColor3f', 'glColor4ub', 'glBindTexture', 'glEnable',
       'glDisable', 'glBlendFunc', 'glDepthMask', 'glTexImage2D', 'glTexParameteri', 'glTexEnvf',
       'glGenTextures', 'glClear', 'glClearColor', 'gluPerspective', 'gluOrtho2D', 'SetBkColor',
       'SetTextColor', 'TextOut', 'GetTextExtent']
F = cm.fbits

# --------------------------------------------------------------------------
# ctypes view of reconstructed/ui

SINKFN = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_uint32), c_int, c_void_p, c_size_t)
LOOKUPFN = CFUNCTYPE(c_void_p, c_void_p, c_uint32)
EXTENTFN = CFUNCTYPE(None, c_void_p, c_char_p, c_int, POINTER(c_int32), POINTER(c_int32))
TEXTOUTFN = CFUNCTYPE(None, c_void_p, POINTER(c_uint8), c_int32, c_int32, c_int32, c_int32, c_int32, c_char_p,
                      c_int)


class Sink(Structure):
    _fields_ = [('user', c_void_p), ('call', SINKFN)]


class Bitmap(Structure):
    _fields_ = [('index', c_uint32), ('width', c_float), ('height', c_float), ('image_width', c_int32),
                ('image_height', c_int32), ('components', c_uint8), ('texture', c_uint32),
                ('buffer', POINTER(c_uint8))]


class State(Structure):
    _fields_ = [('sink', Sink), ('window_width', c_uint32), ('window_height', c_uint32), ('znear', c_float),
                ('zfar', c_float), ('fov', c_float), ('bound_texture', c_int32), ('alpha_test', c_uint8),
                ('fog', c_uint8), ('texture_2d', c_uint8), ('depth_test', c_uint8), ('cull_face', c_uint8),
                ('depth_mask', c_uint8), ('blend_mode', c_int32), ('screen_rate_x', c_float),
                ('screen_rate_y', c_float), ('lookup', LOOKUPFN), ('lookup_user', c_void_p)]


class LoginText(Structure):
    _fields_ = [('text454', c_char_p), ('text455', c_char_p), ('format456', c_char_p),
                ('version_bytes', c_uint8*5)]


class Gdi(Structure):
    _fields_ = [('user', c_void_p), ('extent', EXTENTFN), ('text_out', TEXTOUTFN)]


class Text(Structure):
    _fields_ = [('gdi', Gdi), ('dib', POINTER(c_uint8)), ('dib_width', c_int32), ('dib_height', c_int32),
                ('text_color', c_uint32), ('back_color', c_uint32)]


def library(path=None):
    path = path or ROOT/'reconstructed/ui'/('libmu_ui.dylib' if sys.platform == 'darwin' else 'libmu_ui.so')
    lib = ctypes.CDLL(str(path))
    P = c_void_p
    sigs = {
        'mu_ui_state_init': [P, c_uint32, c_uint32], 'mu_ui_begin_bitmap': [P], 'mu_ui_end_bitmap': [P],
        'mu_ui_render_bitmap': [P, c_int32] + [c_float]*8 + [c_int, c_int, c_float],
        'mu_ui_render_color': [P] + [c_float]*5 + [c_int32], 'mu_ui_end_render_color': [P],
        'mu_ui_enable_alpha_test': [P, c_int], 'mu_ui_enable_alpha_blend': [P], 'mu_ui_disable_alpha_blend': [P],
        'mu_ui_disable_texture': [P, c_int], 'mu_ui_bind_texture': [P, c_int32],
        'mu_ui_sprite_init': [P],
        'mu_ui_sprite_create': [P, P, c_int32, c_int32, c_int32, c_int32, c_int32, c_int, c_int32, c_float, c_float],
        'mu_ui_sprite_set_position': [P, c_int32, c_int32, c_int32],
        'mu_ui_sprite_set_size': [P, c_int32, c_int32, c_int32], 'mu_ui_sprite_render': [P, P],
        'mu_ui_title_create': [P, P, c_int32, c_int32], 'mu_ui_title_render': [P, P, c_uint32, c_uint32],
        'mu_ui_text_init': [P, P], 'mu_ui_text_dib_stride': [c_int32],
        'mu_ui_render_text': [P, P, c_int32, c_int32, c_char_p, c_int32, c_int32, c_int32, P],
        'mu_ui_open_tga': [P, P, c_size_t, c_uint32, c_uint32, c_uint32, c_uint32, P],
        'mu_ui_font_height': [c_uint32],
        'mu_ui_render_color_bitmap': [P, c_int32] + [c_float]*8 + [c_uint32],
        'mu_ui_login_overlay': [P, P, P, c_uint32, P],
    }
    for name, args in sigs.items():
        getattr(lib, name).argtypes = args
        getattr(lib, name).restype = None
    lib.mu_ui_text_dib_stride.restype = c_int32
    lib.mu_ui_open_tga.restype = c_int
    lib.mu_ui_font_height.restype = c_int32
    return lib


class Authored:
    """The reconstruction with a recording sink and a bitmap table."""

    def __init__(self, lib, width, height, bitmaps, rates=None, flags=None):
        self.lib = lib
        self.calls = []
        self._sink = SINKFN(self._record)
        self._lookup = LOOKUPFN(self._find)
        self.bitmaps = {}
        self._keep = []
        for index, spec in bitmaps.items():
            bm = Bitmap(index=index, width=spec['width'], height=spec['height'], components=spec.get('components', 4),
                        texture=spec['texture'], image_width=spec.get('image_width', 0),
                        image_height=spec.get('image_height', 0))
            if 'buffer' in spec:
                buf = (c_uint8*len(spec['buffer'])).from_buffer_copy(spec['buffer'])
                self._keep.append(buf)
                bm.buffer = ctypes.cast(buf, POINTER(c_uint8))
                spec['_c_buffer'] = buf
            self.bitmaps[index] = bm
        self.state = State()
        self.state.sink.call = self._sink
        self.state.lookup = self._lookup
        lib.mu_ui_state_init(ctypes.byref(self.state), width, height)
        if rates:
            self.state.screen_rate_x, self.state.screen_rate_y = rates
        for key, value in (flags or {}).items():
            setattr(self.state, key, value)

    @property
    def sp(self):
        return ctypes.byref(self.state)

    def _find(self, user, index):
        bm = self.bitmaps.get(index)
        return ctypes.addressof(bm) if bm is not None else None

    def _record(self, user, op, words, count, data, size):
        values = [words[i] for i in range(count)]
        name = OPS[op]
        if name == 'glTexImage2D':
            values[8] = hashlib.sha256(ctypes.string_at(data, size) if data else b'').hexdigest()
        elif name in ('TextOut', 'GetTextExtent'):
            values.append(ctypes.string_at(data, size).decode('latin1'))
        self.calls.append((name, tuple(values)))


# --------------------------------------------------------------------------
# client side

BITMAP_SIZE = 0x222
SPRITE_FUNCTIONS = (0x010ad7b2, 0x010ad814, 0x010ad847, 0x010add3c, 0x010adfe4, 0x010ae63d, 0x00986f8a)
GAUGE_FUNCTIONS = (0x00aac91b, 0x00aac99a, 0x00aacb59, 0x00aacbdd, 0x00aacceb, 0x00aacf9e, 0x00aacfd6,
                   0x00aad076, 0x00aad088)
DRAW_FUNCTIONS = (0x01850636, 0x01850679, 0x0184acf6, 0x01851263, 0x0184dcb1, 0x0184d9bb, 0x0184dc62,
                  0x0184f793, 0x0184f8d7, 0x0191b3d7, 0x0191b3e3) + tuple(range(0, 0))
STATE_WRAPPERS = (0x0184a6b7, 0x0184a6da, 0x0184a6fd, 0x0184a720, 0x0184a743, 0x0184a763, 0x0184a783,
                  0x0184a7f3, 0x0184a990, 0x0184aa2b)
TEXT_FUNCTIONS = (0x0119ff3e, 0x011a0431, 0x011a054e, 0x0098d0e5, 0x00c96597, 0x011d5ea9, 0x011c4fb2,
                  0x011c4fbd, 0x011c5acc, 0x011c5db4)
TITLE_FUNCTIONS = (0x011e230d, 0x011e2c8c)
TGA_FUNCTIONS = (0x00c988fc,)
GLOBALS = {'window_width': 0x01cf1624, 'window_height': 0x01cf1628, 'znear': 0x01cf162c, 'zfar': 0x01cf1630,
           'fov': 0x01cf1634, 'bound_texture': 0x01cf1620, 'alpha_test': 0x0bdc58b5, 'fog': 0x0bdc597c,
           'texture_2d': 0x0bdc597d, 'depth_test': 0x0bdc597e, 'cull_face': 0x0bdc597f, 'depth_mask': 0x0bdc5980,
           'blend_mode': 0x0bdc58c4, 'screen_rate_x': 0x06fbcd94, 'screen_rate_y': 0x06fbcd98}
BYTE_FLAGS = {'alpha_test', 'fog', 'texture_2d', 'depth_test', 'cull_face', 'depth_mask'}
FLOAT_GLOBALS = {'znear', 'zfar', 'fov', 'screen_rate_x', 'screen_rate_y'}


class Client:
    """A Machine prepared for the UI routines."""

    def __init__(self, text, data):
        self.text = text
        self.machine = cm.Machine(text, data)
        functions = (SPRITE_FUNCTIONS + GAUGE_FUNCTIONS + DRAW_FUNCTIONS + STATE_WRAPPERS + TEXT_FUNCTIONS
                     + TITLE_FUNCTIONS + TGA_FUNCTIONS)
        for start in functions:
            self.machine.allow((start, cm.function_extent(text, start)))
        # Every state wrapper up to the cached bind is one contiguous block.
        self.machine.allow((0x0184a699, 0x0184acf6))
        self.stub_cleanup = {}

    def cleanup(self, address):
        if address not in self.stub_cleanup:
            self.stub_cleanup[address] = cm.stdcall_cleanup(self.text, address)
        return self.stub_cleanup[address]

    def stub(self, address, handler, cleanup=None):
        self.machine.stub(address, handler, self.cleanup(address) if cleanup is None else cleanup)

    def prepare(self, state, bitmaps):
        """Reset, seed globals from an Authored state, install bitmap records."""
        m = self.machine
        m.reset()
        m.calls = []
        for name, address in GLOBALS.items():
            value = getattr(state, name)
            if name in BYTE_FLAGS:
                m.write(address, bytes([value]))
            elif name in FLOAT_GLOBALS:
                m.putf(address, value)
            else:
                m.put32(address, value)
        self.bitmap_address = {}
        for index, spec in bitmaps.items():
            address = m.alloc(BITMAP_SIZE, define=True)
            record = bytearray(BITMAP_SIZE)
            struct.pack_into('<I', record, 0, index)
            struct.pack_into('<ff', record, 0x204, spec['width'], spec['height'])
            struct.pack_into('<ii', record, 0x20c, spec.get('image_width', 0), spec.get('image_height', 0))
            record[0x214] = spec.get('components', 4)
            struct.pack_into('<I', record, 0x215, spec['texture'])
            if 'buffer' in spec:
                buffer = m.alloc(len(spec['buffer']), define=True)
                m.write(buffer, spec['buffer'])
                struct.pack_into('<I', record, 0x21a, buffer)
                spec['_client_buffer'] = buffer
            m.write(address, record)
            self.bitmap_address[index] = address
        lookup = lambda mm: self.bitmap_address.get(mm.args(1)[0], 0)  # noqa: E731
        self.stub(0x00ebbec8, lookup)
        self.stub(0x00c97ce3, lookup)
        self.stub(0x0191bab9, self._new, 0)    # operator new[]
        self.stub(0x0191ba7b, self._new, 0)    # operator new
        self.stub(0x0191bac2, lambda mm: 0, 0)  # operator delete[]
        self.stub(0x0191baab, lambda mm: 0, 0)  # sized delete
        self.stub(0x0194cd00, self._memset, 0)
        self.stub(0x0194c200, self._memcpy, 0)
        self.stub(0x0195a4b0, self._strlen, 0)

    def _new(self, m):
        return m.alloc(m.args(1)[0])

    def _memset(self, m):
        address, value, size = m.args(3)
        m.write(address, bytes([value & 0xff])*size)
        return address

    def _memcpy(self, m):
        target, source, size = m.args(3)
        m.write(target, m.read(source, size))
        return target

    def _strlen(self, m):
        address = m.args(1)[0]
        length = 0
        while m.read(address + length, 1) != b'\0':
            length += 1
        return length


def normalize_client(calls, machine=None):
    """Map recorded import calls onto the authored op names."""
    out = []
    for name, words in calls:
        if name in ('GetTextExtentPointA', 'GetTextExtentPoint32A'):
            out.append(('GetTextExtent', (words[2], words[-1])))
        elif name == 'TextOutA':
            out.append(('TextOut', (words[1], words[2], words[4], words[-1])))
        elif name in ('SetBkColor', 'SetTextColor'):
            out.append((name, (words[1],)))
        elif name == 'glGenTextures':
            out.append((name, (words[0],)))
        elif name in ('CreateDIBSection', 'CreateCompatibleDC', 'SelectObject', 'lstrlenA'):
            continue
        else:
            out.append((name, tuple(words)))
    return out


def diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f'call {i}: client {x} != authored {y}'
    if len(a) != len(b):
        return f'length client {len(a)} != authored {len(b)}'
    return None


# --------------------------------------------------------------------------
# synthetic GDI font shared by both sides

def glyph_width(ch):
    return 4 + (ch*7) % 6


def text_extent(text, height=13):
    return sum(glyph_width(c) for c in text), height


def rasterize(text, dib_write, stride, width, height, cell=13):
    """Opaque black cells, white glyph pixels from a hash pattern."""
    x = 0
    for ch in text:
        w = glyph_width(ch)
        for row in range(min(cell, height)):
            line = bytearray()
            for col in range(w):
                on = ((ch*31 + row*7 + col*13) % 5) < 2 and 1 <= row < cell - 2
                line += b'\xff\xff\xff' if on else b'\0\0\0'
            if x + w <= width:
                dib_write(row*stride + 3*x, bytes(line))
        x += w


class SyntheticGdi:
    def __init__(self):
        self._extent = EXTENTFN(self.extent)
        self._text_out = TEXTOUTFN(self.text_out)

    def extent(self, user, text, length, cx, cy):
        w, h = text_extent(ctypes.string_at(text, length))
        cx[0], cy[0] = w, h

    def text_out(self, user, dib, stride, width, height, x, y, text, length):
        base = ctypes.addressof(dib.contents)
        rasterize(ctypes.string_at(text, length),
                  lambda off, data: ctypes.memmove(base + off, data, len(data)), stride, width, height)


# --------------------------------------------------------------------------
# cases

WINDOWS = [(640, 480), (800, 600), (1024, 768), (1280, 1024), (1366, 768), (1600, 900), (1920, 1080),
           (2560, 1440)]


def base_bitmaps(rng=None):
    sizes = {0x7b81: (512, 128), 0x7b82: (512, 128), 0x7b83: (256, 256), 0x7b84: (256, 256), 0x7b85: (64, 64),
             0x7b86: (16, 16), 0x7b87: (512, 128), 0x7b88: (512, 128), 0x7b89: (512, 512), 0x7b8a: (512, 512),
             0x7b8b: (256, 512), 0x7b8c: (512, 256), 0x7b8d: (512, 256), 0x7b8e: (256, 256), 5: (64, 32),
             0x7532: (256, 32)}
    out = {}
    for index, (w, h) in sizes.items():
        out[index] = {'width': float(w), 'height': float(h), 'texture': 1000 + index % 997, 'components': 4}
    out[0x7532]['buffer'] = bytes((i*37) & 0xff for i in range(256*32*4))
    return out


def run_pair(client, lib, window, bitmaps, client_fn, authored_fn, flags=None, rates=None):
    authored = Authored(lib, window[0], window[1], bitmaps, rates=rates, flags=flags)
    client.prepare(authored.state, bitmaps)
    client_fn(client.machine)
    authored_fn(authored)
    return normalize_client(client.machine.calls), authored.calls, authored


def render_bitmap_cases(rng):
    for window in WINDOWS[:4]:
        for _ in range(12):
            alpha = rng.choice([0.0, -0.5, 0.25, 1.0, rng.random()])
            args = (rng.choice([5, 0x7532, -7, 0x7b81]), rng.uniform(-50, 700), rng.uniform(-50, 500),
                    rng.uniform(0, 640), rng.uniform(0, 480), rng.random(), rng.random(), rng.random(),
                    rng.random(), rng.randint(0, 1), rng.randint(0, 1), alpha)
            yield window, args


def validate_draw(client, lib, rng, report):
    count = 0
    for window, args in render_bitmap_cases(rng):
        tex, x, y, w, h, u, v, uw, vh, scale, start, alpha = args
        words = [tex & 0xffffffff] + [F(a) for a in (x, y, w, h, u, v, uw, vh)] + [scale, start, F(alpha)]

        def cfn(m):
            m.call(0x0184dcb1, words)
            m.call(0x0184d9bb, [F(x), F(y), F(w), F(h), F(alpha), scale])
            m.call(0x0184dc62)

        def afn(a):
            lib.mu_ui_render_bitmap(a.sp, tex, *[cm.f32(t) for t in (x, y, w, h, u, v, uw, vh)], scale, start,
                                    cm.f32(alpha))
            lib.mu_ui_render_color(a.sp, *[cm.f32(t) for t in (x, y, w, h, alpha)], scale)
            lib.mu_ui_end_render_color(a.sp)
        got, want, _ = run_pair(client, lib, window, base_bitmaps(), cfn, afn)
        problem = diff(got, want)
        if problem:
            raise AssertionError(f'RenderBitmap/RenderColor {window} {args}: {problem}')
        count += 1
    report['render_bitmap_color_cases'] = count

    # state wrappers and the projection from every cache-flag combination
    count = 0
    sequences = [(0x0184f793,), (0x0184f8d7,), (0x0184a990, 1), (0x0184a990, 0), (0x0184aa2b,), (0x0184a7f3,),
                 (0x0184a783, 1), (0x0184a783, 0)]
    for bits in range(64):
        flags = {name: (bits >> i) & 1 for i, name in enumerate(sorted(BYTE_FLAGS))}
        for blend in (0, 2, 3):
            flags_all = dict(flags, blend_mode=blend)
            order = list(sequences)
            rng.shuffle(order)

            def cfn(m):
                for entry in order:
                    m.call(entry[0], list(entry[1:]))
                for index in (5, 5, -3, 0x7532):
                    m.call(0x0184acf6, [index & 0xffffffff])

            def afn(a):
                calls = {0x0184f793: lambda: lib.mu_ui_begin_bitmap(a.sp),
                         0x0184f8d7: lambda: lib.mu_ui_end_bitmap(a.sp)}
                for entry in order:
                    if entry[0] in calls:
                        calls[entry[0]]()
                    elif entry[0] == 0x0184a990:
                        lib.mu_ui_enable_alpha_test(a.sp, entry[1])
                    elif entry[0] == 0x0184aa2b:
                        lib.mu_ui_enable_alpha_blend(a.sp)
                    elif entry[0] == 0x0184a7f3:
                        lib.mu_ui_disable_alpha_blend(a.sp)
                    elif entry[0] == 0x0184a783:
                        lib.mu_ui_disable_texture(a.sp, entry[1])
                for index in (5, 5, -3, 0x7532):
                    lib.mu_ui_bind_texture(a.sp, index)
            window = rng.choice(WINDOWS)
            got, want, authored = run_pair(client, lib, window, base_bitmaps(), cfn, afn, flags=flags_all)
            problem = diff(got, want)
            if problem:
                raise AssertionError(f'state wrappers {flags_all} {order}: {problem}')
            # final cache flags must agree too
            m = client.machine
            for name in BYTE_FLAGS:
                if m.read(GLOBALS[name], 1)[0] != getattr(authored.state, name):
                    raise AssertionError(f'flag {name} differs after {order}')
            if struct.unpack('<i', m.read(GLOBALS['blend_mode'], 4))[0] != authored.state.blend_mode:
                raise AssertionError(f'blend mode differs after {order}')
            count += 1
    report['state_projection_cases'] = count


def sprite_object(m):
    address = m.alloc(0xa8)
    m.call(0x010ad7b2, ecx=address)
    return address


def validate_sprites(client, lib, rng, report):
    count = 0
    for case in range(160):
        window = rng.choice(WINDOWS)
        texture = rng.choice([0x7b81, 0x7b85, 0x7b8b, 5, -1])
        w, h = rng.randint(1, 600), rng.randint(1, 400)
        datum = (rng.randint(-20, 20), rng.randint(-20, 20))
        tile = rng.randint(0, 1)
        sizing = rng.randint(0, 3)
        scale = (cm.f32(rng.choice([1.0, rng.uniform(0.3, 2.5)])), cm.f32(rng.choice([1.0, rng.uniform(0.3, 2.5)])))
        ops = []
        for _ in range(rng.randint(1, 4)):
            if rng.random() < 0.5:
                ops.append(('pos', rng.randint(-100, 900), rng.randint(-100, 700), rng.randint(0, 3)))
            else:
                ops.append(('size', rng.randint(0, 500), rng.randint(0, 400), rng.randint(0, 3)))
        color = [rng.randint(0, 255) for _ in range(4)] if rng.random() < 0.3 else None
        show = rng.random() < 0.9
        sprite_c = ctypes.create_string_buffer(512)

        def cfn(m):
            sp = sprite_object(m)
            m.call(0x010ad847, [w, h, texture & 0xffffffff, 0, 0, datum[0] & 0xffffffff, datum[1] & 0xffffffff,
                                tile, sizing, F(scale[0]), F(scale[1])], ecx=sp)
            for op in ops:
                m.call(0x010add3c if op[0] == 'pos' else 0x010adfe4, [op[1] & 0xffffffff, op[2] & 0xffffffff, op[3]],
                       ecx=sp)
            if color:
                m.write(sp + 0x64, bytes(color))
            m.call(0x00986f8a, [int(show)], ecx=sp)
            m.call(0x010ae63d, ecx=sp)

        def afn(a):
            lib.mu_ui_sprite_init(sprite_c)
            lib.mu_ui_sprite_create(a.sp, sprite_c, w, h, texture, datum[0], datum[1], tile, sizing, *scale)
            for op in ops:
                (lib.mu_ui_sprite_set_position if op[0] == 'pos' else lib.mu_ui_sprite_set_size)(sprite_c, *op[1:])
            raw = SpriteView.from_buffer(sprite_c)
            if color:
                raw.alpha, raw.red, raw.green, raw.blue = color
            raw.show = int(show)
            lib.mu_ui_sprite_render(a.sp, sprite_c)
        got, want, _ = run_pair(client, lib, window, base_bitmaps(), cfn, afn)
        problem = diff(got, want)
        if problem:
            raise AssertionError(f'sprite case {case} {window} tex {texture} {w}x{h} tile {tile} sizing {sizing} '
                                 f'{ops}: {problem}')
        count += 1
    report['sprite_cases'] = count


class SpriteView(Structure):
    _fields_ = [('screen_height', c_float), ('bitmap', c_void_p), ('texture', c_int32), ('width', c_float),
                ('height', c_float), ('position', c_float*8), ('texcoord', c_float*8), ('datum_x', c_float),
                ('datum_y', c_float), ('alpha', c_uint8), ('red', c_uint8), ('green', c_uint8), ('blue', c_uint8),
                ('max_frame', c_int32), ('now_frame', c_int32), ('tile', c_uint8), ('sizing_datums', c_int32),
                ('scale_x', c_float), ('scale_y', c_float), ('show', c_uint8)]


def title_client_stubs(client, screen):
    m = client.machine
    markers = m.calls
    dummy = m.alloc(0x100, define=True)
    timer = m.alloc(0x40, define=True)
    m.put32(0x06fc9c7c, timer)
    elapsed = m.alloc(8, define=True)
    m.write(elapsed, struct.pack('<d', 5000.0))
    snippet = cm.STUB_BASE + 0x80000
    m.uc.mem_write(snippet, b'\xdd\x05' + struct.pack('<I', elapsed) + b'\xc3')   # fld qword [elapsed]; ret

    def marker(name, value=0):
        def handler(mm):
            markers.append((name, ()))
            return value
        return handler

    def elapsed_stub(mm):
        mm.uc.reg_write(cm.UC_X86_REG_EIP, snippet)
        return cm.REDIRECT
    def vector_constructor(mm):
        # eh vector constructor iterator 0x0191b8be(array, size, count, ctor, dtor): its SEH/CFG
        # prologue is runtime code; the stub performs the three stores of the CSprite
        # constructor 0x010ad7b2 (which the sprite cases run unmodified) on each element.
        array, size, count, ctor, dtor = mm.args(5)
        if ctor != 0x010ad7b2 or size != 0xa8:
            return mm.fail(f'unexpected vector constructor {ctor:#x} size {size:#x}')
        for i in range(count):
            element = array + i*size
            mm.put32(element, 0x01ab9ba8)
            mm.put32(element + 0x78, 0)
            mm.put32(element + 0xc, 0)
        return 0
    client.stub(0x0191b8be, vector_constructor, 0x14)
    client.stub(0x011e2bc3, marker('ReleaseTitleSceneUI'))
    client.stub(0x00aac00c, marker('LoadingManager', dummy))
    client.stub(0x00aac688, marker('LoadingManager.688'))
    client.stub(0x00aac6b4, marker('LoadingManager.6b4'))
    client.stub(0x00aac477, marker('LoadingManager.Render'))
    client.stub(0x00cc3564, lambda mm: dummy)
    client.stub(0x009828b5, lambda mm: screen[0])
    client.stub(0x009828a6, lambda mm: screen[1])
    client.stub(0x0184adc7, marker('Camera'))
    client.stub(0x0184b6dd, marker('0x0184b6dd'))
    client.stub(0x011865d8, marker('TimerReset'))
    m.stub(0x01186606, elapsed_stub, 0)


def validate_title(client, lib, rng, report):
    count = 0
    markers = {'TimerReset', 'LoadingManager.Render'}
    for window in WINDOWS:
        for progress in ((0, 100), (37, 100), (100, 100), (250, 100), (5, 0)):
            screen = window

            def cfn(m):
                title_client_stubs(client, screen)
                ui = m.alloc(0x6600, define=True)
                m.call(0x011e230d, ecx=ui)
                m.calls.append(('--render--', ()))
                m.call(0x011e2c8c, [0x1234, progress[0], progress[1]], ecx=ui)
            title_c = ctypes.create_string_buffer(8192)

            def afn(a):
                lib.mu_ui_title_create(a.sp, title_c, screen[0], screen[1])
                lib.mu_ui_title_render(a.sp, title_c, progress[0], progress[1])
            got, want, _ = run_pair(client, lib, window, base_bitmaps(), cfn, afn)
            split = got.index(('--render--', ()))
            create_calls, render_calls = got[:split], got[split + 1:]
            if any(name not in ('ReleaseTitleSceneUI', 'LoadingManager', 'LoadingManager.688', 'LoadingManager.6b4')
                   for name, _ in create_calls):
                raise AssertionError(f'title create emitted platform calls: {create_calls}')
            begin = next(i for i, c in enumerate(render_calls) if c == ('glMatrixMode', (0x1701,)))
            end = max(i for i, c in enumerate(render_calls) if c[0] == 'glPopMatrix')
            outer = render_calls[:begin] + [('<2d>', ())] + render_calls[end + 1:]
            expected_outer = [('Camera', ()), ('glClear', (0x4100,)), ('<2d>', ()), ('0x0184b6dd', ()),
                              ('SwapBuffers', (0x1234,))]
            if outer != expected_outer:
                raise AssertionError(f'title outer sequence {window} {progress}: {outer}')
            inner = render_calls[begin:end + 1]
            seen = [c[0] for c in inner if c[0] in markers]
            if seen != (['TimerReset'] if progress[0] == 0 else []):
                raise AssertionError(f'title markers {window} {progress}: {seen}')
            problem = diff([c for c in inner if c[0] not in markers], want)
            if problem:
                raise AssertionError(f'title {window} {progress}: {problem}')
            count += 1
    report['title_scene_cases'] = count


def validate_text(client, lib, rng, report):
    count = 0
    gdi = SyntheticGdi()
    strings = [b'Version 1.04.05', b'', b'\nnewline', b'A', b'Mu The Matrix - server select',
               bytes(range(33, 127)), bytes(range(40, 127))*2, b'0123456789'*9]
    for case in range(140):
        window = rng.choice(WINDOWS)
        rates = (cm.f32(window[0]/640.0), cm.f32(window[1]/480.0))
        string = rng.choice(strings)
        box = (rng.choice([0, 0, 40, 100, 300, 700]), rng.choice([0, 0, 10, 20]))
        sort = rng.choice([0, 1, 2, 3, 4, 5, 7, 8])
        pos = (rng.randint(-200, 700), rng.randint(-30, 500))
        color = [rng.randint(0, 255) for _ in range(4)]
        back = [rng.randint(0, 255) for _ in range(4)] if rng.random() < 0.4 else [0, 0, 0, 0]
        want_size = rng.random() < 0.5
        bitmaps = base_bitmaps()
        dib_w = cm.f32(640.0*rates[0])
        width_px = int(dib_w)
        height_px = int(cm.f32(480.0*rates[1]))
        stride = ((width_px*24 + 31) & ~31) >> 3
        dib_init = bytes((i*11) & 0xff for i in range(stride*height_px))

        def cfn(m):
            impl = m.alloc(0x18, define=True)
            dib = m.alloc(len(dib_init), define=True)
            m.write(dib, dib_init)
            m.put32(impl + 4, 0x4444)
            m.put32(impl + 0xc, dib)
            m.put32(impl + 0x10, color[0] | color[1] << 8 | color[2] << 16 | color[3] << 24)
            m.put32(impl + 0x14, back[0] | back[1] << 8 | back[2] << 16 | back[3] << 24)
            text_ptr = m.alloc(len(string) + 1, define=True)
            m.write(text_ptr, string + b'\0')
            m.write(0x01ac3bb4, b'0\0')

            def extent(mm, words):
                w, h = text_extent(mm.read(words[1], words[2]))
                mm.write(words[3], struct.pack('<ii', w, h))
                return 1

            def text_out(mm, words):
                rasterize(mm.read(words[3], words[4]), lambda off, data: mm.write(dib + off, data), stride,
                          width_px, height_px)
                return 1
            m.handlers['GetTextExtentPointA'] = extent
            m.handlers['TextOutA'] = text_out
            out = m.alloc(8, define=True) if want_size else 0
            m.call(0x0119ff3e, [pos[0] & 0xffffffff, pos[1] & 0xffffffff, text_ptr, box[0], box[1], sort, out],
                   ecx=impl)
            m._text_out_size = m.read(out, 8) if out else None
            m._dib = m.read(dib, len(dib_init))

        def afn(a):
            text = Text()
            text.gdi.extent = gdi._extent
            text.gdi.text_out = gdi._text_out
            lib.mu_ui_text_init(ctypes.byref(text), ctypes.byref(a.state))
            buf = (c_uint8*len(dib_init)).from_buffer_copy(dib_init)
            text.dib = ctypes.cast(buf, POINTER(c_uint8))
            text.text_color = color[0] | color[1] << 8 | color[2] << 16 | color[3] << 24
            text.back_color = back[0] | back[1] << 8 | back[2] << 16 | back[3] << 24
            out = (c_int32*2)()
            lib.mu_ui_render_text(a.sp, ctypes.byref(text), pos[0], pos[1], string, box[0], box[1], sort,
                                  out if want_size else None)
            a._out = bytes(out) if want_size else None
            a._dib = bytes(buf)
            a._text = text
        got, want, authored = run_pair(client, lib, window, bitmaps, cfn, afn, rates=rates)
        problem = diff(got, want)
        if problem:
            raise AssertionError(f'text case {case} {window} {string[:20]!r} box {box} sort {sort} pos {pos}: {problem}')
        if authored._text.dib_width != width_px or authored._text.dib_height != height_px:
            raise AssertionError('DIB size differs')
        if want_size and client.machine._text_out_size != authored._out:
            raise AssertionError(f'text size output differs: {client.machine._text_out_size} {authored._out}')
        if client.machine._dib != authored._dib:
            raise AssertionError('DIB contents differ')
        font_client = client.machine.read(bitmaps[0x7532]['_client_buffer'], 256*32*4)
        if font_client != bytes(bitmaps[0x7532]['_c_buffer']):
            raise AssertionError(f'font texture buffer differs in case {case}')
        count += 1
    report['text_cases'] = count
    report['font_heights'] = {w: lib.mu_ui_font_height(w) for w in (640, 799, 800, 1023, 1024, 1279, 1280,
                                                                     1679, 1680, 1920)}


# ---- login overlay ---------------------------------------------------------

LOGIN_FUNCTIONS = (0x01857ed9, 0x00ec52a9, 0x0184e01a, 0x011a08fd, 0x011a0998, 0x011a09f3, 0x011a0a4e,
                   0x011a0a77, 0x0119fe5f, 0x0119fe9b, 0x0119fedf, 0x0119ff23)
LOGIN_MARKERS = {'UIManager.Render', 'Cursor'}


def login_client_run(client, window, fade, width640, strings, dib_init, extent_fn, raster_fn, stride, size):
    m = client.machine
    calls = m.calls
    marker = lambda name, value=0: (lambda mm: (calls.append((name, ())), value)[1])  # noqa: E731
    m.write(0x0bdc5b86, b'\x01')
    m.putf(0x0bdc5b80, fade)
    m.put32(0x06fc9ca4, 0x0f0f0001)                               # g_hFont (a GDI handle)
    obj = m.alloc(0x40, define=True)
    m.put32(obj + 0xc, obj + 0x20)
    ui = m.alloc(0x4700, define=True)
    m.write(ui + 0x4648 + 0xc, b'\x01')                      # skip the 3D login world
    impl = m.alloc(0x18, define=True)
    dib = m.alloc(len(dib_init), define=True)
    m.write(dib, dib_init)
    m.put32(impl, 0x01ac4c68)
    m.put32(impl + 4, 0x4444)
    m.put32(impl + 0xc, dib)
    m.put32(impl + 0x10, 0xffffffff)
    facade = m.alloc(0x10, define=True)
    m.put32(facade + 4, impl)
    texts = {0x1c6: strings[0], 0x1c7: strings[1], 0x1c8: strings[2]}
    objects = {}
    for index, value in texts.items():
        holder = m.alloc(8, define=True)
        objects[holder] = value
        texts[index] = holder
    version_bytes = strings[3]
    m.write(0x01cf100c, bytes(version_bytes))
    streams = {}

    def global_text(mm):
        return texts[mm.args(1)[0]]

    def c_str(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        value = objects.get(this, streams.get(this, b''))
        buffer = mm.alloc(len(value) + 1, define=True)
        mm.write(buffer, value + b'\0')
        return buffer

    def stream_ctor(mm):
        streams[mm.uc.reg_read(cm.UC_X86_REG_ECX)] = b''
        return mm.uc.reg_read(cm.UC_X86_REG_ECX)

    def stream_put(mm):
        target, char = mm.args(2)
        streams[target] = streams.get(target, b'') + bytes([char & 0xff])
        return target

    def stream_str(mm):
        this, out = mm.uc.reg_read(cm.UC_X86_REG_ECX), mm.args(1)[0]
        streams[out] = streams.get(this - 4, b'')
        return out

    def read_c(mm, address):
        out = b''
        while True:
            byte = mm.read(address + len(out), 1)
            if byte == b'\0':
                return out
            out += byte

    def strcpy(mm):
        target, source = mm.args(2)
        mm.write(target, read_c(mm, source) + b'\0')
        return target

    def sprintf(mm):
        target, fmt, arg = mm.args(3)
        # C runtime sprintf for the one-%s formats used here (%% -> %)
        parts = read_c(mm, fmt).split(b'%%')
        value, used = read_c(mm, arg), False
        out = []
        for part in parts:
            if not used and b'%s' in part:
                part = part.replace(b'%s', value, 1)
                used = True
            out.append(part)
        text = b'%'.join(out)
        mm.write(target, text + b'\0')
        return len(text)
    for address, handler in ((0x011753c3, global_text), (0x008e7f90, c_str), (0x0094978c, stream_ctor),
                             (0x00951e97, stream_str), (0x0094f183, lambda mm: 0), (0x0094ba2d, lambda mm: 0)):
        client.stub(address, handler)
    client.stub(0x009443a1, stream_put, 0)
    client.stub(0x01983a90, strcpy, 0)
    client.stub(0x009619dd, sprintf, 0)
    client.stub(0x0185498e, marker('0x0185498e'))
    client.stub(0x016bc355, lambda mm: width640)
    client.stub(0x0184adc7, marker('Camera'))
    client.stub(0x0098647b, lambda mm: obj)
    client.stub(0x016cba24, marker('0x016cba24'), 0)
    client.stub(0x011e228b, lambda mm: ui)
    for address, name in ((0x0184a699, 'PushIdentity'), (0x0169270e, 'Effects.0x0169270e'),
                          (0x0159123f, 'Sprites.0x0159123f'), (0x0184a6ab, 'PopMatrix')):
        client.stub(address, marker(name))
    client.stub(0x011a07b2, lambda mm: facade)
    client.stub(0x009fe825, lambda mm: obj)
    client.stub(0x009fe955, marker('UIManager.Render'))
    client.stub(0x01858c72, marker('Cursor'))
    client.stub(0x0184b6dd, marker('0x0184b6dd'))
    client.stub(0x00c97c2d, lambda mm: client.bitmap_address.get(mm.args(1)[0], 0))

    def lstrlen(mm, words):
        return len(read_c(mm, words[0]))

    def extent(mm, words):
        w, h = extent_fn(mm.read(words[1], words[2]))
        mm.write(words[3], struct.pack('<ii', w, h))
        return 1

    def text_out(mm, words):
        raster_fn(mm.read(words[3], words[4]), lambda off, data: mm.write(dib + off, data), stride, *size)
        return 1
    m.handlers['lstrlenA'] = lstrlen
    m.handlers['GetTextExtentPointA'] = extent
    m.handlers['TextOutA'] = text_out
    result = m.call(0x01857ed9)
    return result, struct.unpack('<f', m.read(0x0bdc5b80, 4))[0], m.read(dib, len(dib_init))


def validate_login(client, lib, rng, report):
    count = 0
    gdi = SyntheticGdi()
    for function in LOGIN_FUNCTIONS:
        client.machine.allow((function, cm.function_extent(client.text, function)))
    texts = [(b'Copyright (C) WEBZEN Inc. All rights reserved.', b'MU The Matrix', b'Version %s'),
             (b'', b'0', b'v%s build'), (b'A'*90, b'right text', b'%s'),
             (b'MU Online', b'Server select', b'Ver: %s (beta) 100%%')]
    for case in range(48):
        window = WINDOWS[case % len(WINDOWS)]
        rates = (cm.f32(window[0]/640.0), cm.f32(window[1]/480.0))
        fade = cm.f32(rng.choice([0.0, 0.3, 1.0, 5.5, 9.99, 10.0, 12.0]))
        width640 = rng.choice([640, 640, 380, 450])
        t454, t455, f456 = rng.choice(texts)
        version = bytes((ord(c) + i + 1) & 0xff for i, c in enumerate(rng.choice(['10405', '20101', '9.9.9'])))
        bitmaps = base_bitmaps()
        for index, (iw, ih, tw, th) in {0x7b1e: (rng.randint(100, 512), rng.randint(40, 256), 512, 256),
                                        0x7b1f: (300, 150, 512, 256)}.items():
            bitmaps[index] = {'width': float(tw), 'height': float(th), 'texture': 2000 + index % 97,
                              'image_width': iw, 'image_height': ih, 'components': 4}
        width_px = int(cm.f32(640.0*rates[0]))
        height_px = int(cm.f32(480.0*rates[1]))
        stride = ((width_px*24 + 31) & ~31) >> 3
        dib_init = bytes((i*13) & 0xff for i in range(stride*height_px))

        def cfn(m):
            m._result = login_client_run(client, window, fade, width640, (t454, t455, f456, version), dib_init,
                                         text_extent, rasterize, stride, (width_px, height_px))

        def afn(a):
            text = Text()
            text.gdi.extent = gdi._extent
            text.gdi.text_out = gdi._text_out
            lib.mu_ui_text_init(ctypes.byref(text), ctypes.byref(a.state))
            buf = (c_uint8*len(dib_init)).from_buffer_copy(dib_init)
            text.dib = ctypes.cast(buf, POINTER(c_uint8))
            strings = LoginText(text454=t454, text455=t455, format456=f456)
            strings.version_bytes[:] = list(version)
            fade_c = c_float(fade)
            lib.mu_ui_begin_bitmap(a.sp)
            lib.mu_ui_login_overlay(a.sp, ctypes.byref(text), ctypes.byref(fade_c), width640, ctypes.byref(strings))
            lib.mu_ui_end_bitmap(a.sp)
            a._fade = fade_c.value
            a._dib = bytes(buf)
        got, want, authored = run_pair(client, lib, window, bitmaps, cfn, afn, rates=rates)
        begin = next(i for i, c in enumerate(got) if c == ('glMatrixMode', (0x1701,)))
        end = max(i for i, c in enumerate(got) if c[0] == 'glPopMatrix')
        inner = got[begin:end + 1]
        outer = got[:begin] + [('<2d>', ())] + got[end + 1:]
        expected_outer = [('0x0185498e', ()), ('glColor3f', (F(1.0),)*3), ('glClearColor', (0, 0, 0, F(1.0))),
                          ('Camera', ()), ('0x016cba24', ()), ('PushIdentity', ()), ('Effects.0x0169270e', ()),
                          ('Sprites.0x0159123f', ()), ('PopMatrix', ()), ('<2d>', ()), ('0x0184b6dd', ())]
        if outer != expected_outer:
            raise AssertionError(f'login outer sequence {window}: {outer}')
        seen = [c[0] for c in inner if c[0] in LOGIN_MARKERS]
        if seen != ['UIManager.Render', 'Cursor']:
            raise AssertionError(f'login markers {seen}')
        problem = diff([c for c in inner if c[0] not in LOGIN_MARKERS], want)
        if problem:
            raise AssertionError(f'login case {case} {window} fade {fade} w640 {width640} {t454[:12]!r}: {problem}')
        result, fade_client, dib_client = client.machine._result
        if (result & 0xff) != 1 or fade_client != authored._fade or dib_client != authored._dib:
            raise AssertionError(f'login state differs: result {result} fade {fade_client} {authored._fade}')
        count += 1
    report['login_overlay_cases'] = count


# ---- OpenTga ---------------------------------------------------------------

def tga_client_run(client, payload, index, filter_, wrap, entry=0x00c988fc):
    """Run OpenTga 0x00c988fc (or OpenJpeg 0x00c982ea) on `payload` and return (result, calls, ...)."""
    m = client.machine
    files = {}
    name = m.alloc(64, define=True)
    m.write(name, b'Data\\Interface\\case.OZT\0')
    state = {'handle': None, 'pos': 0, 'opened': []}

    def fopen(mm):
        path, mode = mm.args(2)
        state['opened'].append(mm.read(path, 24))
        state['pos'] = 0
        return 0x5150

    def fseek(mm):
        handle, offset, origin = mm.args(3)
        offset = struct.unpack('<i', struct.pack('<I', offset))[0]
        state['pos'] = {0: offset, 1: state['pos'] + offset, 2: len(payload) + offset}[origin]
        return 0

    def ftell(mm):
        return state['pos']

    def fread(mm):
        buffer, size, count, handle = mm.args(4)
        chunk = payload[state['pos']:state['pos'] + size*count]
        mm.write(buffer, chunk)
        state['pos'] += len(chunk)
        return len(chunk)//size if size else 0
    nop = lambda mm: 0  # noqa: E731
    client.stub(0x01988f83, fopen, 0)
    client.stub(0x01989dab, fseek, 0)
    client.stub(0x0198a634, ftell, 0)
    client.stub(0x01989230, fread, 0)
    client.stub(0x01988c95, nop, 0)
    for address in (0x008e6d00, 0x0094997e, 0x00c990b8, 0x008e83a0, 0x00c9b8c5, 0x00c98f9e, 0x0120b45f,
                    0x008e62b0, 0x00c992b7, 0x00c9a516, 0x00c9a5b4, 0x00c9a55f, 0x00c9af18, 0x00c9a582):
        client.stub(address, nop)
    client.stub(0x008e7940, lambda mm: name)          # std::string::c_str -> the OZT name
    counter = {'next': 501}

    def gen(mm, words):
        mm.put32(words[1], counter['next'])
        counter['next'] += 1
        return 0
    m.handlers['glGenTextures'] = gen
    table = m.alloc(0x80, define=True)
    captured = {}

    def capture_new(mm):
        size = mm.args(1)[0]
        address = mm.alloc(size)
        captured.setdefault('allocs', []).append((address, size))
        return address
    client.stub(0x0191bab9, capture_new, 0)
    result = m.call(entry, [index, 0, filter_, wrap], ecx=table) & 0xff
    return result, normalize_client(m.calls), captured, state


def tga_authored(lib, state_ref, payload, index, filter_, wrap, authored):
    bitmap = Bitmap()
    buf = ctypes.create_string_buffer(payload, len(payload))
    result = lib.mu_ui_open_tga(state_ref, buf, len(payload), index, filter_, wrap, 501, ctypes.byref(bitmap))
    return result, bitmap


def tga_mutations(payload, rng):
    yield 'original', payload
    b = bytearray(payload)
    b[2] ^= 0x08                                   # image type (ignored by the client)
    yield 'image-type', bytes(b)
    b = bytearray(payload)
    b[4 + 17] ^= 0x20                              # origin bit (ignored)
    yield 'origin-bit', bytes(b)
    b = bytearray(payload)
    b[4] = 9                                       # id length (ignored: pixels stay at 22)
    yield 'id-length', bytes(b)
    b = bytearray(payload)
    b[20] = 24                                     # 24 bits: refused
    yield 'bits-24', bytes(b)
    b = bytearray(payload)
    struct.pack_into('<h', b, 16, 1025)            # too wide: refused
    yield 'width-1025', bytes(b)
    w, h = struct.unpack_from('<hh', payload, 16)
    if w > 2 and h > 2:
        b = bytearray(payload)
        struct.pack_into('<hh', b, 16, w - 1, h - 2)   # non-power-of-two sub-image
        yield 'smaller-header', bytes(b)


def synthetic_ozt(w, h, rng):
    header = bytearray(4) + bytearray(18)
    header[4 + 2] = 2
    struct.pack_into('<hh', header, 16, w, h)
    header[20] = 32
    header[21] = 8
    return bytes(header) + bytes(rng.getrandbits(8) for _ in range(w*h*4))


def validate_tga(client, lib, rng, report, game_root=None, limit=None):
    cases = []
    for w, h in ((1, 1), (3, 5), (17, 9), (64, 32), (100, 50), (256, 256), (300, 7)):
        cases.append((f'synthetic-{w}x{h}', synthetic_ozt(w, h, rng)))
    installed = 0
    if game_root:
        files = sorted(Path(game_root, 'Data/Interface').glob('*.[oO][zZ][tT]'))
        files += sorted(Path(game_root, 'Data/Logo').glob('*.[oO][zZ][tT]'))
        if limit:
            files = files[:limit]
        for path in files:
            cases.append((str(path.relative_to(game_root)), path.read_bytes()))
            installed += 1
    count = mutated = 0
    digests = {}
    for label, payload in cases:
        for mutation, data in tga_mutations(payload, rng):
            if label.startswith('Data') and mutation != 'original' and rng.random() > 0.15:
                continue
            index = rng.choice([0x7b15, 0x7532, 0x7bd1, 0x9000])
            filter_, wrap = rng.choice([(0x2600, 0x2900), (0x2601, 0x2901)])
            authored = Authored(lib, 800, 600, {})
            client.machine.heap_checks(not label.startswith('Data'))
            client.prepare(authored.state, {})
            result_c, calls_c, captured, fstate = tga_client_run(client, data, index, filter_, wrap)
            result_a, bitmap = tga_authored(lib, authored.sp, data, index, filter_, wrap, authored)
            loaded_a = 1 if result_a == 1 else 0
            if result_c != loaded_a:
                raise AssertionError(f'OpenTga {label}/{mutation}: client {result_c} authored {result_a}')
            problem = diff(calls_c, authored.calls)
            if problem:
                raise AssertionError(f'OpenTga {label}/{mutation}: {problem}')
            if result_c:
                tw, th = int(bitmap.width), int(bitmap.height)
                digests[label if mutation == 'original' else f'{label}/{mutation}'] = calls_c[2][1][8][:16]
                if fstate['opened'] and not fstate['opened'][0].startswith(b'Data\\Interface\\case.OZT'):
                    raise AssertionError('unexpected file name')
            count += 1
            mutated += mutation != 'original'
    client.machine.heap_checks(True)
    report['tga_cases'] = count
    report['tga_mutations'] = mutated
    report['tga_installed_files'] = installed
    return digests


# ---- OpenJpeg ---------------------------------------------------------------

JPEG_RUNTIME = {0x01950ac0: 'setjmp', 0x01983110: 'malloc', 0x01983100: 'free', 0x0199afcd: 'getenv'}


def native_library(path=None):
    path = path or ROOT/'native/build'/('libmuui.dylib' if sys.platform == 'darwin' else 'libmuui.so')
    if not Path(path).exists():
        return None
    lib = ctypes.CDLL(str(path))
    lib.mu_ui_open_jpeg.argtypes = [c_void_p, c_void_p, c_size_t, c_uint32, c_uint32, c_uint32, c_uint32, c_void_p,
                                    c_void_p, c_void_p, c_void_p]
    lib.mu_ui_open_jpeg.restype = c_int
    lib.mu_ui_state_init.argtypes = [c_void_p, c_uint32, c_uint32]
    lib.mu_ui_libjpeg_available.restype = c_int
    return lib


def jpeg_client_run(client, payload, index, filter_, wrap):
    """OpenJpeg 0x00c982ea with the client's statically linked IJG libjpeg."""
    m = client.machine
    client.stub(0x01950ac0, lambda mm: 0, 0)                     # _setjmp3: first return
    client.stub(0x01983110, lambda mm: mm.alloc(mm.args(1)[0]), 0)  # malloc (jpeg_get_small/large)
    client.stub(0x01983100, lambda mm: 0, 0)                     # free
    client.stub(0x0199afcd, lambda mm: 0, 0)                     # getenv("JPEGMEM") -> NULL
    m.put32(0x01cf65c0, 0xbb40e64e)                              # __security_cookie

    def error_exit(mm):
        # the client's libjpeg error_exit 0x00c9924e: output_message, then longjmp -> OpenJpeg returns false
        cinfo = mm.args(1)[0]
        return mm.fail(f'longjmp: libjpeg message {mm.u32(mm.u32(cinfo) + 0x14)}')
    client.stub(0x00c9924e, error_exit, 0)

    def output_message(mm):
        # jpeg_std_error's output_message 0x018b4ac0 (format_message + fprintf to stderr) for warnings
        warnings.append(mm.u32(mm.u32(mm.args(1)[0]) + 0x14))
        return 0
    warnings = client.jpeg_warnings = []
    client.stub(0x018b4ac0, output_message, 0)
    return tga_client_run(client, payload, index, filter_, wrap, entry=0x00c982ea)


def validate_jpeg(client, lib, native, rng, report, game_root=None, limit=None, small_limit=None):
    if native is None or not native.mu_ui_libjpeg_available():
        report['jpeg'] = 'skipped: native/build/libmuui with libjpeg not built'
        return
    client.machine.allow((0x00c982ea, cm.function_extent(client.text, 0x00c982ea)))
    # IJG libjpeg 6b as linked into the client (jpeg_CreateDecompress version 62)
    client.machine.allow((0x018b0000, 0x018c8000), (0x0191cd7c, 0x0191cd85))
    files = []
    if game_root:
        for folder in ('Data/Interface', 'Data/Logo'):
            files += sorted(Path(game_root, folder).glob('*.[oO][zZ][jJ]'))
    rng_files = random.Random(7)
    small = [f for f in files if f.stat().st_size <= 40000]
    large = [f for f in files if f.stat().st_size > 40000]
    rng_files.shuffle(large)
    if small_limit is not None:
        rng_files.shuffle(small)
        small = sorted(small[:small_limit])
    chosen = small + large[:limit if limit is not None else 12]
    count = 0
    errors = {}
    warning_codes = {}
    for path in chosen:
        payload = path.read_bytes()
        mutations = [('original', payload)]
        if rng.random() < 0.1 and len(payload) > 200:
            mutations.append(('truncated', payload[:len(payload)*2//3]))
        for mutation, data in mutations:
            index = rng.choice([0x7b89, 0x851b, 0x9000])
            authored = Authored(lib, 800, 600, {})
            client.machine.heap_checks(False)
            client.prepare(authored.state, {})
            try:
                result_c, calls_c, _, _ = jpeg_client_run(client, data, index, 0x2601, 0x2900)
            except cm.CaseError as error:
                if 'longjmp' not in str(error):
                    raise
                result_c, calls_c = 0, []
                errors[str(error).split(': ', 1)[1]] = errors.get(str(error).split(': ', 1)[1], 0) + 1
            state = State()
            state.sink.call = authored._sink
            native.mu_ui_state_init(ctypes.byref(state), 800, 600)
            bitmap = Bitmap()
            buf = ctypes.create_string_buffer(data, len(data))
            decode = ctypes.cast(native.mu_ui_libjpeg_decode, c_void_p)
            release = ctypes.cast(native.mu_ui_libjpeg_release, c_void_p)
            result_a = native.mu_ui_open_jpeg(ctypes.byref(state), buf, len(data), index, 0x2601, 0x2900, 501,
                                              decode, release, None, ctypes.byref(bitmap))
            for code in getattr(client, 'jpeg_warnings', []):
                warning_codes[code] = warning_codes.get(code, 0) + 1
            if (result_c != 0) != (result_a != 0):
                raise AssertionError(f'OpenJpeg {path.name}/{mutation}: client {result_c} native {result_a}')
            problem = diff(calls_c, authored.calls)
            if problem:
                raise AssertionError(f'OpenJpeg {path.name}/{mutation}: {problem}')
            if result_a == 1 and bitmap.buffer:
                ctypes.CDLL(None).free(bitmap.buffer)
            count += 1
    client.machine.heap_checks(True)
    report['jpeg_cases'] = count
    report['jpeg_client_errors'] = errors
    report['jpeg_client_warning_codes'] = warning_codes
    report['jpeg_installed_files'] = len(chosen)
    report['jpeg_installed_total'] = len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', default=ROOT/'evidence/x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', default=ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin')
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--library')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--only', choices=['draw', 'sprites', 'title', 'text', 'login', 'tga', 'jpeg'],
                        action='append')
    parser.add_argument('--tga-limit', type=int)
    parser.add_argument('--jpeg-large', type=int, help='large installed OZJ files to include (default 12)')
    parser.add_argument('--jpeg-small', type=int, help='small installed OZJ files to include (default all)')
    parser.add_argument('--native-library')
    parser.add_argument('--output')
    args = parser.parse_args()
    text = common.load_pinned(args.text, common.TEXT_BYTES, common.TEXT_SHA256)
    data = common.load_pinned(args.data, common.DATA_BYTES, common.DATA_SHA256)
    lib = library(args.library)
    client = Client(text, data)
    rng = random.Random(args.seed)
    report = {'text_sha256': common.TEXT_SHA256, 'data_sha256': common.DATA_SHA256, 'seed': args.seed}
    only = set(args.only or ['draw', 'sprites', 'title', 'text', 'login', 'tga', 'jpeg'])
    if 'draw' in only:
        validate_draw(client, lib, rng, report)
    if 'sprites' in only:
        validate_sprites(client, lib, rng, report)
    if 'title' in only:
        validate_title(client, lib, rng, report)
    if 'text' in only:
        validate_text(client, lib, rng, report)
    if 'login' in only:
        validate_login(client, lib, rng, report)
    if 'tga' in only:
        validate_tga(client, lib, rng, report, args.game_root, args.tga_limit)
    if 'jpeg' in only:
        validate_jpeg(client, lib, native_library(args.native_library), rng, report, args.game_root, args.jpeg_large,
                      args.jpeg_small)
    print(json.dumps(report, indent=1))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
