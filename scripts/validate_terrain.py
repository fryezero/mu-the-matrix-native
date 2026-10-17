#!/usr/bin/env python3
"""Compare the authored terrain C (reconstructed/terrain) with the client.

Two independent references are used:

* Pure-Python models of every rule (binary32 emulated through struct), used by
  the portable tests against the authored library.
* The pinned restored client text, executed under Unicorn (private). Routines
  compared on synthetic inputs: the three-byte XOR 0x00976855, FaceNormalize
  0x00d01206, CreateTerrainNormal 0x016c8ab6, CreateTerrainLight 0x016c8ce6,
  the face texture coordinates 0x016cfd4c, the tile corner build of 0x016ccda5,
  the full per-tile GL call stream of 0x016ccda5 -> 0x016cff65 for both passes,
  and RenderTerrain 0x016cd468 up to the end of its grass pass. With
  --game-root the installed worlds are decoded and selected worlds' normals,
  light and tile streams are compared on real data.

GL imports are recorded at stub addresses written into the copied import
slots. Three calls are substituted, and only these: the texture manager
lookups 0x00ebbec8 / 0x00c97ce3 (return a synthetic bitmap whose +0x204/+0x208
hold the width/height floats, or null) and the singleton getter 0x00db747f
(thread-local static initialisation; its result is only passed to a world
predicate that does not read it). Raw text, data and reports stay local.
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE = 0x401000
TEXT_BYTES = 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE = 0x01a7c000
DATA_BYTES = 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
FLAG_ADDRESS = 0x0bdd1cc8
CELLS = 65536
KEY = bytes((0xfc, 0xcf, 0xab))

# Client globals (docs/research/client-terrain.md).
G = dict(world=0x01cf15fc, world2=0x01cf1600, layer1=0x0b735420, layer2=0x0b745420, alpha=0x0b755420,
         att=0x0b795420, height=0x0b6f5420, light=0x0b9f5430, light2=0x0bc35430, wave=0x0b634ea8,
         grass_offset=0x0b5f4ea8, grass_map=0x0b5e4ea8, water=0x01cf15dc, time=0x06fce370,
         grass_disabled=0x0b7f5428, config=0x01d22c7c, pass_=0x0b5e3ea0, normal=0x0b7f5430,
         light_map=0x0bb75430, primary=0x0bab5430, uv=0x0b6b5384, corner=0x0b6b5318, idx0=0x0b6b4eac,
         idx1=0x0b6b52e8, idx2=0x0b6b52ec, idx3=0x0b6b52f0, key=0x01cf0448, force=0x0bdc58b7,
         xmin=0x0b6b53f8, ymin=0x0b6b53fc, xmax=0x01cf15e0, ymax=0x01cf15e4, alpha_flag=0x01cf15d8)
XOR3, FACE_NORMAL, NORMALS, LIGHT, UV, TILE, FACE, RENDER = (0x00976855, 0x00d01206, 0x016c8ab6, 0x016c8ce6,
                                                             0x016cfd4c, 0x016ccda5, 0x016cff65, 0x016cd468)
RENDER_STOP = 0x016cd61d
STATE_WRAPPERS = {0x0184a7f3: 1, 0x0184a990: 2, 0x0184aa2b: 3}
BIND = 0x0184acf6
LOOKUPS = (0x00ebbec8, 0x00c97ce3)
SINGLETON = 0x00db747f
GL = {0x01a7c750: ('glBegin', 4), 0x01a7c760: ('glEnd', 0), 0x01a7c774: ('glTexCoord2f', 8),
      0x01a7c770: ('glColor3fv', 4), 0x01a7c754: ('glColor4f', 16), 0x01a7c778: ('glVertex3fv', 4),
      0x01a7c77c: ('glBindTexture', 8), 0x01a7c75c: ('glEnable', 4), 0x01a7c758: ('glDisable', 4),
      0x01a7c748: ('glBlendFunc', 8), 0x01a7c740: ('glDepthMask', 4)}
OPENGL_SLOTS = (0x01a7c64c, 0x01a7c790)
GENERIC_WORLDS = (0, 1, 2, 3, 4, 8)


# --------------------------------------------------------------------------
# binary32 helpers and Python models.

def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def fbits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def frombits(b):
    return struct.unpack('<f', struct.pack('<I', b & 0xffffffff))[0]


def fadd(a, b): return f32(a + b)
def fsub(a, b): return f32(a - b)
def fmul(a, b): return f32(a * b)


def fdiv(a, b):
    if b == 0.0:
        if a == 0.0 or a != a:
            return float('nan')
        return math.copysign(float('inf'), a) * math.copysign(1.0, b)
    return f32(a / b)


def gt(a, b): return a == a and b == b and a > b
def ge(a, b): return a == a and b == b and a >= b


def index(x, y): return y * 256 + x
def index_repeat(x, y): return (y & 255) * 256 + (x & 255)


def py_xor3(buffer, key=KEY):
    return bytes(c ^ key[i % 3] for i, c in enumerate(buffer))


def py_parse_map(plain):
    if len(plain) < 2 + 3 * CELLS:
        return None
    alpha = [f32(b / 255.0) for b in plain[2 + 2 * CELLS:2 + 3 * CELLS]]
    return plain[1], bytes(plain[2:2 + CELLS]), bytes(plain[2 + CELLS:2 + 2 * CELLS]), alpha


def py_parse_attributes(plain, key=KEY):
    if len(plain) not in (0x20004, 0x10004):
        return 'bad-size', None, None
    p = py_xor3(plain, key)
    if len(plain) == 0x20004:
        cells = [p[4 + 2 * i] | p[5 + 2 * i] << 8 for i in range(CELLS)]
    else:
        cells = list(p[4:4 + CELLS])
    cells = [c & 0xfaff for c in cells]
    corrupt = not (p[0] == 0 and p[2] == 0xff and p[3] == 0xff) or any((c & 0xff) >= 0x80 for c in cells)
    return ('corrupt' if corrupt else 'ok'), p[1], cells


def py_height_bytes(file, scale):
    start = 4 + 0x438
    if len(file) < start + CELLS:
        return None
    return [fmul(float(b), scale) for b in file[start:start + CELLS]]


def py_height_rgb(file):
    start = 58
    if len(file) < start + 3 * CELLS:
        return None
    out = []
    for i in range(CELLS):
        p = file[start + 3 * i:start + 3 * i + 3]
        out.append(fadd(f32(float(p[2] | p[1] << 8 | p[0] << 16)), -500.0))
    return out


def py_light(file, offset=False):
    if len(file) < 58:
        return None
    width, height = struct.unpack_from('<ii', file, 22)
    count = width * height
    if width < 0 or height < 0 or count * 3 > len(file) - 58:
        return None
    out = []
    for i in range(count):
        p = file[58 + 3 * i:61 + 3 * i]
        for k in range(3):
            v = fdiv(float(p[2 - k]), 255.0)
            out.append(fsub(fmul(v, 2.0), 1.0) if offset else v)
    return out


def py_face_normal(a, b, c):
    t10 = fsub(b[1], a[1])
    nx = fsub(fmul(t10, fsub(c[2], a[2])), fmul(fsub(c[1], a[1]), fsub(b[2], a[2])))
    ny = fsub(fmul(fsub(b[2], a[2]), fsub(c[0], a[0])), fmul(fsub(c[2], a[2]), fsub(b[0], a[0])))
    nz = fsub(fmul(fsub(b[0], a[0]), fsub(c[1], a[1])), fmul(fsub(c[0], a[0]), fsub(b[1], a[1])))
    s = fadd(fadd(fmul(nx, nx), fmul(ny, ny)), fmul(nz, nz))
    length = f32(math.sqrt(s)) if s >= 0 else float('nan')
    if length == 0.0:
        return [0.0, 0.0, 0.0]
    return [f32(nx / length) if length == length else float('nan') for nx in (nx, ny, nz)]


def py_normals(height):
    out = []
    for y in range(256):
        for x in range(256):
            b = [fmul(float(x + 1), 100.0), fmul(float(y), 100.0), height[index_repeat(x + 1, y)]]
            c = [fmul(float(x + 1), 100.0), fmul(float(y + 1), 100.0), height[index_repeat(x + 1, y + 1)]]
            d = [fmul(float(x), 100.0), fmul(float(y + 1), 100.0), height[index_repeat(x, y + 1)]]
            out.extend(py_face_normal(b, c, d))
    return out


def py_primary_light(normal, light_map, world):
    l = (0.5, -1.0, 1.0) if world == 30 else (0.5, -0.5, 0.5)
    out = []
    for i in range(CELLS):
        n = normal[3 * i:3 * i + 3]
        lum = fadd(fadd(fadd(fmul(n[0], l[0]), fmul(n[1], l[1])), fmul(n[2], l[2])), 0.5)
        if lum == lum and 0.0 > lum:
            lum = 0.0
        elif gt(lum, 1.0):
            lum = 1.0
        out.extend(fmul(light_map[3 * i + k], lum) for k in range(3))
    return out


def py_tile_uv(width, height, xf, yf, small, offset, wave, k, idx):
    scale = 16.0 if small else 64.0
    su, sv = fdiv(scale, width), fdiv(scale, height)
    u0, v0 = fmul(xf, su), fmul(yf, sv)
    w0, w1 = fmul(wave[idx[0]], k), fmul(wave[idx[1]], k)
    return [fadd(u0, offset[0]), fadd(fadd(v0, offset[1]), w0),
            fadd(fadd(u0, su), offset[0]), fadd(fadd(v0, offset[1]), w1),
            fadd(fadd(u0, su), offset[0]), fadd(fadd(fadd(v0, sv), offset[1]), w1),
            fadd(u0, offset[0]), fadd(fadd(fadd(v0, sv), offset[1]), w0)]


def py_tile_corners(att, height, water, xf, yf, xi, yi, lod=1, picking=0):
    idx = [index(xi, yi), index(xi + lod, yi), index(xi + lod, yi + lod), index(xi, yi + lod)]
    if not 0 <= idx[0] < CELLS:
        return 'bad-index', idx, None
    if (att[idx[0]] & 8) and not picking:
        return 'skip', idx[:1], None
    if any(not 0 <= i < CELLS for i in idx):
        return 'bad-index', idx, None
    x, y = fmul(xf, 100.0), fmul(yf, 100.0)
    c = [[x, y, height[idx[0]]], [fadd(x, 100.0), y, height[idx[1]]],
         [fadd(x, 100.0), fadd(y, 100.0), height[idx[2]]], [x, fadd(y, 100.0), height[idx[3]]]]
    for k in range(4):
        if att[idx[k]] & 0x40:
            c[k][2] = water
    return 'built', idx, c


SPECIAL = set([0x1e, 0x5e, 0x7a, 0x8d, 0x22, 0x3f, 0x64, 0x65, 0x6e, 0x6f, 0x70, 0x8a, 0x8c, 7, 0x85, 0x27, 0x62,
               0x63, 0x33, 0x50, 0x51, 0x5b, 0x5c, 0x71, 0x91, 0x35, 0x61] + list(range(0x52, 0x5b)) +
              list(range(0x80, 0x83)) + list(range(0x2d, 0x33)) + list(range(0x45, 0x4b)) + list(range(0x12, 0x18)))


def py_draw_tile(scene, pass_, xf, yf, xi, yi, out):
    """Appends the GL-shaped stream; returns the status like the C."""
    status, idx, c = py_tile_corners(scene['att'], scene['height'], scene['water'], xf, yf, xi, yi)
    if status == 'bad-index':
        return 3
    if status == 'skip':
        return 0
    light, light2, alpha, w = scene['light'], scene['light2'], scene['alpha'], scene['world']
    sizes = scene['sizes']
    if pass_ == 2:
        if any(gt(alpha[i], 0.0) for i in idx):
            return 0
        if scene['grass_disabled'] or 0x0b <= w <= 0x11 or w == 0x34 or scene['layer1'][idx[0]] >= 0x63:
            return 0
        if not scene['grass_map'][idx[0]]:
            return 0
        texture = 0x7694 + scene['layer1'][idx[0]]
        if texture not in sizes:
            return 0
        if w in (0x3f, 0x50, 0x51, 0x90, 0x6e, 0x6f, 0x8d, 0x8e) or 0x52 <= w <= 0x5a:
            return 4
        blade = fmul(sizes[texture][1], 2.0)
        out.append(('bind', texture))
        u = fadd(fmul(xf, 0.25), scene['grass_offset'][yi & 0xff])
        uv = [u, 0.0, fadd(u, 0.25), 0.0, fadd(u, 0.25), 1.0, u, 1.0]
        c[3] = list(c[0])
        c[2] = list(c[1])
        c[0][2] = fadd(c[0][2], blade)
        c[1][2] = fadd(c[1][2], blade)
        c[0][0] = fadd(c[0][0], -50.0)
        c[1][0] = fadd(c[1][0], -50.0)
        c[0][1] = fadd(c[0][1], scene['wave'][idx[0]])
        c[1][1] = fadd(c[1][1], scene['wave'][idx[1]])
        out.append(('begin', 7))
        for k in range(4):
            out.append(('tex', fbits(uv[2 * k]), fbits(uv[2 * k + 1])))
            out.append(('c3',) + tuple(fbits(v) for v in light[3 * idx[k]:3 * idx[k] + 3]))
            out.append(('v',) + tuple(fbits(v) for v in c[k]))
        out.append(('end',))
        return 0
    i0 = idx[0]
    neighbour = bool(scene['att'][i0] & 0x4000)
    offset, k = [0.0, 0.0], 0.0
    if all(ge(alpha[i], 1.0) for i in idx) and not neighbour:
        layer, layer1_drawn = scene['layer2'][i0], False
    else:
        layer, layer1_drawn = scene['layer1'][i0], True
        if layer == 5:
            if w in (0x1e, 0x5e, 0x7a, 0x8d):
                return 4
            t = int(scene['time'])
            offset[0] = fdiv(f32(float(int(math.fmod(t, 20000)))), 20000.0)
            cv = f32(math.cos(fmul(scene['time'], f32(0.0001))))
            offset[1] = fmul(fmul(fadd(cv, 1.0), 0.5), 0.5)
            k = f32(0.0015)
        if w == 0x22:
            return 4
    if w in SPECIAL:
        return 4
    texture = 0x7630 + layer
    if texture not in sizes:
        return 4

    def emit(texture, uv, alpha_face):
        out.append(('state', 2, 1) if (alpha_face or layer == 0xe and texture == 0x7630 + layer and
                                       not alpha_face) else ('state', 1, 0))
        out.append(('bind', texture))
        out.append(('begin', 6))
        for q in range(4):
            i = idx[q]
            out.append(('tex', fbits(uv[2 * q]), fbits(uv[2 * q + 1])))
            rgb = [fadd(light[3 * i + j], light2[3 * i + j]) for j in range(3)]
            if alpha_face:
                out.append(('c4',) + tuple(fbits(v) for v in rgb) + (fbits(alpha[i]),))
            else:
                out.append(('c3',) + tuple(fbits(v) for v in rgb))
            out.append(('v',) + tuple(fbits(v) for v in c[q]))
        out.append(('end',))

    uv = py_tile_uv(sizes[texture][0], sizes[texture][1], xf, yf, 0, offset, scene['wave'], k, idx)
    emit(texture, uv, False)
    status = 4 if (scene['detail'] >= 4 and neighbour) else 0
    if not any(gt(alpha[i], 0.0) for i in idx) or not layer1_drawn:
        return status
    layer2 = scene['layer2'][i0]
    if layer2 != 5:
        offset = [0.0, 0.0]
    if layer2 == 0xff:
        return status
    texture2 = 0x7630 + layer2
    if texture2 not in sizes:
        return 4
    uv = py_tile_uv(sizes[texture2][0], sizes[texture2][1], xf, yf, 0, offset, scene['wave'], 0.0, idx)
    emit(texture2, uv, True)
    return status


def py_walk(scene, pass_, box, out):
    x0, y0, x1, y1 = box
    by = float(y0)
    for y in range(y0, y1 + 1, 4):
        bx = float(x0)
        for x in range(x0, x1 + 1, 4):
            for j in range(4):
                for i in range(4):
                    py_draw_tile(scene, pass_, fadd(bx, float(i)), fadd(by, float(j)), x + i, y + j, out)
            bx = fadd(bx, 4.0)
        by = fadd(by, 4.0)


def py_draw(scene, box, alpha_layers, out):
    out.append(('state', 1, 0))
    py_walk(scene, 0, box, out)
    out.append(('state', 2, 1))
    w = scene['world']
    if alpha_layers and not (w == 7 or 0x80 <= w <= 0x82) and w != 0x5e:
        py_walk(scene, 2, box, out)


# --------------------------------------------------------------------------
# Authored C through ctypes.

SIZE_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                                 ctypes.POINTER(ctypes.c_float))


class Scene(ctypes.Structure):
    _fields_ = [('world_index', ctypes.c_int32), ('layer1', ctypes.c_void_p), ('layer2', ctypes.c_void_p),
                ('alpha', ctypes.c_void_p), ('attributes', ctypes.c_void_p), ('height', ctypes.c_void_p),
                ('light', ctypes.c_void_p), ('light2', ctypes.c_void_p), ('wave', ctypes.c_void_p),
                ('grass_offset', ctypes.c_void_p), ('grass_map', ctypes.c_void_p), ('water_height', ctypes.c_float),
                ('time', ctypes.c_float), ('detail', ctypes.c_int32), ('grass_disabled', ctypes.c_uint8),
                ('texture_size', SIZE_CALLBACK), ('texture_context', ctypes.c_void_p)]


class Stats(ctypes.Structure):
    _fields_ = [(name, ctypes.c_long) for name in ('faces', 'alpha_faces', 'grass', 'skipped', 'unsupported')]


VOIDP = ctypes.c_void_p
STATE_CB = ctypes.CFUNCTYPE(None, VOIDP, ctypes.c_int32, ctypes.c_int32)
INT_CB = ctypes.CFUNCTYPE(None, VOIDP, ctypes.c_int32)
TEX_CB = ctypes.CFUNCTYPE(None, VOIDP, ctypes.c_float, ctypes.c_float)
C3_CB = ctypes.CFUNCTYPE(None, VOIDP, ctypes.POINTER(ctypes.c_float))
C4_CB = ctypes.CFUNCTYPE(None, VOIDP, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
END_CB = ctypes.CFUNCTYPE(None, VOIDP)


class Sink(ctypes.Structure):
    _fields_ = [('context', VOIDP), ('state', STATE_CB), ('bind', INT_CB), ('begin', INT_CB), ('texcoord', TEX_CB),
                ('color3', C3_CB), ('color4', C4_CB), ('vertex', C3_CB), ('end', END_CB)]


def floats(values):
    return (ctypes.c_float * len(values))(*values)


class Authored:
    def __init__(self, library):
        self.lib = lib = ctypes.CDLL(str(library))
        lib.mu_terrain_xor3.argtypes = [VOIDP, ctypes.c_int32, VOIDP]
        lib.mu_terrain_face_normal.argtypes = [VOIDP, VOIDP, VOIDP, VOIDP]
        lib.mu_terrain_normals.argtypes = [VOIDP, VOIDP]
        lib.mu_terrain_primary_light.argtypes = [VOIDP, VOIDP, ctypes.c_int32, VOIDP]
        lib.mu_terrain_tile_uv.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                           ctypes.c_int, VOIDP, VOIDP, ctypes.c_float, VOIDP, VOIDP]
        lib.mu_terrain_tile_corners.argtypes = [VOIDP, VOIDP, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                                ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int, VOIDP,
                                                VOIDP]
        for name in ('mu_terrain_parse_map',):
            getattr(lib, name).argtypes = [VOIDP, ctypes.c_size_t, VOIDP, VOIDP, VOIDP, VOIDP]
        lib.mu_terrain_parse_attributes.argtypes = [VOIDP, ctypes.c_size_t, VOIDP, VOIDP, VOIDP]
        lib.mu_terrain_height_bytes.argtypes = [VOIDP, ctypes.c_size_t, ctypes.c_float, VOIDP]
        lib.mu_terrain_height_rgb.argtypes = [VOIDP, ctypes.c_size_t, VOIDP]
        lib.mu_terrain_light_bmp.argtypes = [VOIDP, ctypes.c_size_t, VOIDP, ctypes.c_int32, VOIDP]
        lib.mu_terrain_light_offset_bmp.argtypes = [VOIDP, ctypes.c_size_t, VOIDP, ctypes.c_int32, VOIDP]
        lib.mu_terrain_draw_tile.argtypes = [ctypes.POINTER(Scene), ctypes.c_int32, ctypes.c_float, ctypes.c_float,
                                             ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(Sink),
                                             ctypes.POINTER(Stats)]
        lib.mu_terrain_draw.argtypes = [ctypes.POINTER(Scene), ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                                        ctypes.c_int32, ctypes.c_int, ctypes.POINTER(Sink), ctypes.POINTER(Stats)]
        lib.mu_terrain_height_scale.restype = ctypes.c_float

    def xor3(self, data, key=KEY):
        buffer = ctypes.create_string_buffer(bytes(data), len(data))
        self.lib.mu_terrain_xor3(buffer, len(data), ctypes.create_string_buffer(bytes(key), 3))
        return buffer.raw

    def face_normal(self, a, b, c):
        out = floats([7.0] * 3)
        self.lib.mu_terrain_face_normal(floats(a), floats(b), floats(c), out)
        return list(out)

    def normals(self, height):
        out = (ctypes.c_float * (3 * CELLS))()
        self.lib.mu_terrain_normals(floats(height), out)
        return list(out)

    def primary_light(self, normal, light_map, world):
        out = (ctypes.c_float * (3 * CELLS))()
        self.lib.mu_terrain_primary_light(floats(normal), floats(light_map), world, out)
        return list(out)

    def tile_uv(self, width, height, xf, yf, small, offset, wave, k, idx):
        out = floats([0.0] * 8)
        self.lib.mu_terrain_tile_uv(width, height, xf, yf, small, floats(offset), wave, k,
                                    (ctypes.c_int32 * 4)(*idx), out)
        return list(out)

    def tile_corners(self, att, height, water, xf, yf, xi, yi, lod=1, picking=0):
        idx = (ctypes.c_int32 * 4)()
        corner = floats([0.0] * 12)
        result = self.lib.mu_terrain_tile_corners(att, height, water, xf, yf, xi, yi, lod, picking, idx, corner)
        return result, list(idx), list(corner)

    def parse_map(self, plain):
        l1, l2 = ctypes.create_string_buffer(CELLS), ctypes.create_string_buffer(CELLS)
        alpha, number = (ctypes.c_float * CELLS)(), ctypes.c_int32()
        status = self.lib.mu_terrain_parse_map(bytes(plain), len(plain), l1, l2, alpha, ctypes.byref(number))
        return status, number.value, l1.raw, l2.raw, list(alpha)

    def parse_attributes(self, plain, key=KEY):
        buffer = ctypes.create_string_buffer(bytes(plain), len(plain))
        att, number = (ctypes.c_uint16 * CELLS)(), ctypes.c_int32()
        status = self.lib.mu_terrain_parse_attributes(buffer, len(plain), bytes(key), att, ctypes.byref(number))
        return status, number.value, list(att)

    def height_bytes(self, file, scale):
        out = (ctypes.c_float * CELLS)()
        return self.lib.mu_terrain_height_bytes(bytes(file), len(file), scale, out), list(out)

    def height_rgb(self, file):
        out = (ctypes.c_float * CELLS)()
        return self.lib.mu_terrain_height_rgb(bytes(file), len(file), out), list(out)

    def light(self, file, offset=False, capacity=CELLS):
        out, pixels = (ctypes.c_float * (3 * capacity))(), ctypes.c_int32()
        function = self.lib.mu_terrain_light_offset_bmp if offset else self.lib.mu_terrain_light_bmp
        status = function(bytes(file), len(file), out, capacity, ctypes.byref(pixels))
        return status, list(out)[:3 * pixels.value]

    def scene(self, s):
        keep = []

        def arr(kind, values):
            a = (kind * len(values))(*values)
            keep.append(a)
            return ctypes.cast(a, VOIDP)
        sizes = s['sizes']

        def size(context, texture, width, height):
            if texture not in sizes:
                return 0
            width[0], height[0] = sizes[texture]
            return 1
        callback = SIZE_CALLBACK(size)
        keep.append(callback)
        scene = Scene(s['world'], arr(ctypes.c_uint8, s['layer1']), arr(ctypes.c_uint8, s['layer2']),
                      arr(ctypes.c_float, s['alpha']), arr(ctypes.c_uint16, s['att']),
                      arr(ctypes.c_float, s['height']), arr(ctypes.c_float, s['light']),
                      arr(ctypes.c_float, s['light2']), arr(ctypes.c_float, s['wave']),
                      arr(ctypes.c_float, s['grass_offset']), arr(ctypes.c_uint8, s['grass_map']), s['water'],
                      s['time'], s['detail'], s['grass_disabled'], callback, None)
        return scene, keep

    @staticmethod
    def recorder(out):
        def c3(context, p):
            out.append(('c3', fbits(p[0]), fbits(p[1]), fbits(p[2])))

        def vertex(context, p):
            out.append(('v', fbits(p[0]), fbits(p[1]), fbits(p[2])))
        sink = Sink(None, STATE_CB(lambda c, s, a: out.append(('state', s, a))),
                    INT_CB(lambda c, t: out.append(('bind', t))), INT_CB(lambda c, m: out.append(('begin', m))),
                    TEX_CB(lambda c, s, t: out.append(('tex', fbits(s), fbits(t)))), C3_CB(c3),
                    C4_CB(lambda c, r, g, b, a: out.append(('c4', fbits(r), fbits(g), fbits(b), fbits(a)))),
                    C3_CB(vertex), END_CB(lambda c: out.append(('end',))))
        return sink

    def draw_tile(self, scene_built, pass_, xf, yf, xi, yi):
        out = []
        sink = self.recorder(out)
        stats = Stats()
        status = self.lib.mu_terrain_draw_tile(ctypes.byref(scene_built[0]), pass_, xf, yf, xi, yi,
                                               ctypes.byref(sink), ctypes.byref(stats))
        return status, out

    def draw(self, scene_built, box, alpha_layers):
        out = []
        sink = self.recorder(out)
        stats = Stats()
        status = self.lib.mu_terrain_draw(ctypes.byref(scene_built[0]), *box, alpha_layers, ctypes.byref(sink),
                                          ctypes.byref(stats))
        return status, out


# --------------------------------------------------------------------------
# Synthetic scenes.

def synthetic_scene(seed, world=0):
    g = random.Random(seed)
    layer_pool = [0, 1, 2, 3, 4, 5, 6, 7, 8, 0xe, 0xff]
    scene = {'world': world, 'water': 1201.0, 'time': g.choice([0.0, 12345.5, 250000.0]), 'detail': g.choice([0, 4]),
             'grass_disabled': 0}
    scene['layer1'] = bytes(g.choice(layer_pool[:-1]) for _ in range(CELLS))
    scene['layer2'] = bytes(g.choice(layer_pool) for _ in range(CELLS))
    alpha_pool = [0.0, 0.0, 0.0, 1.0, f32(128 / 255.0), f32(1 / 255.0), f32(254 / 255.0)]
    scene['alpha'] = [g.choice(alpha_pool) for _ in range(CELLS)]
    att_pool = [0, 0, 0, 1, 4, 8, 0x40, 0x44, 0x80 & 0, 0x0100 & 0xfaff, 0x1000, 0x2000]
    scene['att'] = [g.choice(att_pool) for _ in range(CELLS)]
    scene['height'] = [f32(g.uniform(-50.0, 400.0)) for _ in range(CELLS)]
    scene['light'] = [f32(g.random()) for _ in range(3 * CELLS)]
    scene['light2'] = [f32(g.uniform(-0.25, 0.25)) if seed & 1 else 0.0 for _ in range(3 * CELLS)]
    scene['wave'] = [f32(g.uniform(-10.0, 10.0)) for _ in range(CELLS)]
    scene['grass_offset'] = [f32((g.randrange(32768) % 4) / 4.0) for _ in range(CELLS)]
    scene['grass_map'] = bytes(g.choice((1, 1, 1, 0)) for _ in range(CELLS))
    sizes = {}
    for layer in layer_pool[:-1]:
        sizes[0x7630 + layer] = (float(g.choice((64, 128, 256, 512))), float(g.choice((64, 128, 256))))
    for layer in (0, 1):
        sizes[0x7694 + layer] = (256.0, 64.0)
    scene['sizes'] = sizes
    return scene


# --------------------------------------------------------------------------
# Client execution under Unicorn.

def check_identity(path, size, digest, label):
    payload = Path(path).read_bytes()
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input does not match the pinned {label}')
    return payload


def descriptor(base, limit, access=0x93, flags=0xc):
    return struct.pack('<Q', (limit & 0xffff) | ((base & 0xffffff) << 16) | (access << 40) |
                       (((limit >> 16) & 0xf) << 48) | (flags << 52) | ((base >> 24) << 56))


class Client:
    STUBS, BITMAPS, CONFIG, TEB, GDT, STACK = 0x00100000, 0x00180000, 0x001f0000, 0x00280000, 0x00290000, 0x00300000
    SENTINEL = 0x00100ff0
    BSS = ((0x01cf0000, 0x01d30000), (0x01ec3000, 0x01ec4000), (0x06fce000, 0x06fcf000), (0x0b5e0000, 0x0bde0000))

    def __init__(self, text, data, flag=None):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED,
                             UC_HOOK_MEM_FETCH_UNMAPPED, UC_PROT_ALL)
        from unicorn import x86_const as x86
        self.x86 = x86
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES + 0xfff) & ~0xfff, UC_PROT_ALL)
        uc.mem_write(DATA_BASE, data)
        for low, high in self.BSS:
            uc.mem_map(low, high - low, UC_PROT_ALL)
        if flag is not None:
            uc.mem_write(FLAG_ADDRESS, flag)
        for base, size in ((self.STUBS, 0x10000), (self.BITMAPS, 0x60000), (self.CONFIG, 0x1000),
                           (self.TEB, 0x1000), (self.GDT, 0x1000), (self.STACK, 0x40000)):
            uc.mem_map(base, size, UC_PROT_ALL)
        gdt = b'\0' * 8 + descriptor(self.TEB, 0xfff)
        uc.mem_write(self.GDT, gdt)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, self.GDT, len(gdt) - 1, 0))
        uc.reg_write(x86.UC_X86_REG_FS, 0x8)
        uc.mem_write(self.TEB, struct.pack('<I', 0xffffffff))
        # Import stubs: recorded GL calls; every other OpenGL slot traps.
        self.stub_names = {}
        for i, slot in enumerate(range(OPENGL_SLOTS[0], OPENGL_SLOTS[1], 4)):
            stub = self.STUBS + 8 * i
            name, args = GL.get(slot, (None, None))
            uc.mem_write(stub, b'\xc3' if not args else b'\xc2' + struct.pack('<H', args))
            uc.mem_write(slot, struct.pack('<I', stub))
            self.stub_names[stub] = name
        uc.hook_add(UC_HOOK_CODE, self.on_stub, begin=self.STUBS, end=self.STUBS + 0x7ff)
        for address in list(STATE_WRAPPERS) + [BIND] + list(LOOKUPS) + [SINGLETON]:
            uc.hook_add(UC_HOOK_CODE, self.on_entry, begin=address, end=address)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.on_unmapped)
        uc.mem_write(G['config'], struct.pack('<I', self.CONFIG - 0x20 + 0x20 - 0x20))
        self.bitmaps = {}
        self.stream = []
        self.error = None

    # -- hooks
    def esp(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_ESP)

    def arg(self, n):
        return struct.unpack('<I', self.uc.mem_read(self.esp() + 4 + 4 * n, 4))[0]

    def farg(self, n):
        return struct.unpack('<I', self.uc.mem_read(self.esp() + 4 + 4 * n, 4))[0]

    def read_floats(self, address, count):
        return struct.unpack(f'<{count}I', self.uc.mem_read(address, 4 * count))

    def ret(self, value, argument_bytes):
        uc, x86 = self.uc, self.x86
        esp = self.esp()
        address = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        uc.reg_write(x86.UC_X86_REG_EAX, value)
        uc.reg_write(x86.UC_X86_REG_ESP, esp + 4 + argument_bytes)
        uc.reg_write(x86.UC_X86_REG_EIP, address)

    def on_stub(self, uc, address, size, ignored):
        if address == self.SENTINEL:
            return
        name = self.stub_names.get(address)
        if name is None:
            self.error = ('unexpected-gl-import', hex(address))
            uc.emu_stop()
            return
        if name == 'glBegin':
            self.stream.append(('begin', self.arg(0)))
        elif name == 'glEnd':
            self.stream.append(('end',))
        elif name == 'glTexCoord2f':
            self.stream.append(('tex', self.farg(0), self.farg(1)))
        elif name == 'glColor3fv':
            self.stream.append(('c3',) + self.read_floats(self.arg(0), 3))
        elif name == 'glColor4f':
            self.stream.append(('c4', self.farg(0), self.farg(1), self.farg(2), self.farg(3)))
        elif name == 'glVertex3fv':
            self.stream.append(('v',) + self.read_floats(self.arg(0), 3))
        else:
            self.gl_state.append((name, self.arg(0)))

    def on_entry(self, uc, address, size, ignored):
        if address in STATE_WRAPPERS:
            argument = self.arg(0) & 0xff if STATE_WRAPPERS[address] == 2 else 0
            self.stream.append(('state', STATE_WRAPPERS[address], argument))
        elif address == BIND:
            self.stream.append(('bind', self.arg(0)))
        elif address in LOOKUPS:
            self.ret(self.bitmaps.get(self.arg(0), 0), 4)
        elif address == SINGLETON:
            self.ret(self.CONFIG + 0x800, 0)

    def on_unmapped(self, uc, access, address, size, value, ignored):
        self.error = ('unmapped', hex(address), size, hex(uc.reg_read(self.x86.UC_X86_REG_EIP)))
        return False

    # -- memory
    def write(self, name, fmt, values):
        self.uc.mem_write(G[name], struct.pack(f'<{len(values)}{fmt}', *values))

    def read(self, name, fmt, count, offset=0):
        return list(struct.unpack(f'<{count}{fmt}', self.uc.mem_read(G[name] + offset, struct.calcsize(fmt) * count)))

    def set_bitmaps(self, sizes):
        self.bitmaps = {}
        for slot, (texture, (width, height)) in enumerate(sorted(sizes.items())):
            base = self.BITMAPS + 0x400 * slot
            self.uc.mem_write(base, b'\0' * 0x400)
            self.uc.mem_write(base + 0x204, struct.pack('<ff', width, height))
            self.uc.mem_write(base + 0x215, struct.pack('<I', 1000 + slot))
            self.bitmaps[texture] = base

    def load_scene(self, s):
        self.write('world', 'i', [s['world']])
        self.write('world2', 'i', [s['world']])
        self.uc.mem_write(G['layer1'], s['layer1'])
        self.uc.mem_write(G['layer2'], s['layer2'])
        self.write('alpha', 'f', s['alpha'])
        self.write('att', 'H', s['att'])
        self.write('height', 'f', s['height'])
        self.write('light', 'f', s['light'])
        self.write('light2', 'f', s['light2'])
        self.write('wave', 'f', s['wave'])
        self.write('grass_offset', 'f', s['grass_offset'])
        self.uc.mem_write(G['grass_map'], s['grass_map'])
        self.write('water', 'f', [s['water']])
        self.write('time', 'f', [s['time']])
        self.uc.mem_write(G['grass_disabled'], bytes([s['grass_disabled']]))
        self.uc.mem_write(self.CONFIG + 0x2c, struct.pack('<i', s['detail']))
        self.uc.mem_write(G['config'], struct.pack('<I', self.CONFIG))
        self.set_bitmaps(s['sizes'])

    # -- execution
    def call(self, start, words, until=None, ecx=0):
        uc, x86 = self.uc, self.x86
        self.stream, self.gl_state, self.error = [], [], None
        top = self.STACK + 0x3f000
        frame = struct.pack('<I', self.SENTINEL) + b''.join(struct.pack('<I', w & 0xffffffff) for w in words)
        uc.mem_write(top, frame)
        uc.reg_write(x86.UC_X86_REG_ESP, top)
        uc.reg_write(x86.UC_X86_REG_EBP, 0x13579bdf)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, 0x27f)
        uc.reg_write(x86.UC_X86_REG_FPSW, 0)
        uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x86.UC_X86_REG_MXCSR, 0x1f80)
        try:
            uc.emu_start(start, until or self.SENTINEL, timeout=0, count=0)
        except Exception as failure:  # UcError
            self.error = self.error or ('uc', str(failure))
        pc = uc.reg_read(x86.UC_X86_REG_EIP)
        ok = self.error is None and pc == (until or self.SENTINEL)
        if until is None and ok:
            ok = self.esp() == top + 4
        return ok


def u32(x):
    return fbits(x)


def compare_lists(a, b):
    return len(a) == len(b) and all(fbits(x) == fbits(y) for x, y in zip(a, b))


def run_client(args, authored):
    text = check_identity(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = check_identity(args.data, DATA_BYTES, DATA_SHA256, 'image data')
    flag = Path(args.flag).read_bytes() if args.flag else None
    client = Client(text, data, flag)
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'substitutions':
              ['0x00ebbec8 texture lookup', '0x00c97ce3 texture lookup', '0x00db747f singleton getter']}
    g = random.Random(0x7e44a1)

    # XOR3
    cases = matches = 0
    for length in (0, 1, 2, 3, 4, 5, 7, 64, 255, 1000):
        for key in (KEY, bytes(g.randrange(256) for _ in range(3))):
            buffer = bytes(g.randrange(256) for _ in range(max(length, 1)))
            client.uc.mem_write(G['key'], key)
            client.uc.mem_write(Client.CONFIG + 0x100, buffer)
            ok = client.call(XOR3, [Client.CONFIG + 0x100, length])
            got = bytes(client.uc.mem_read(Client.CONFIG + 0x100, len(buffer)))
            cases += 1
            matches += int(ok and got == authored.xor3(buffer[:length], key) + buffer[length:])
    report['xor3'] = {'cases': cases, 'matches': matches}

    # FaceNormalize
    cases = matches = 0
    specials = [0.0, -0.0, 1.0, 100.0, 1e-20, 3.4e38, float('nan'), float('inf')]
    for case in range(400):
        pick = lambda: g.choice(specials) if case % 5 == 0 else f32(g.uniform(-500, 500))
        a, b, c = ([f32(pick()) for _ in range(3)] for _ in range(3))
        if case % 7 == 0:
            b = list(a)
        base = Client.CONFIG + 0x200
        client.uc.mem_write(base, struct.pack('<9f', *a, *b, *c) + struct.pack('<3I', 0x7fc0dead, 1, 2))
        ok = client.call(FACE_NORMAL, [base, base + 12, base + 24, base + 36])
        got = list(struct.unpack('<3f', client.uc.mem_read(base + 36, 12)))
        cases += 1
        matches += int(ok and compare_lists(got, authored.face_normal(a, b, c)))
    report['face_normal'] = {'cases': cases, 'matches': matches}

    # CreateTerrainNormal and CreateTerrainLight on synthetic grids
    grids = []
    for seed in range(3):
        gg = random.Random(seed)
        if seed == 0:
            height = [0.0] * CELLS
        elif seed == 1:
            height = [fmul(float(gg.randrange(256)), 1.5) for _ in range(CELLS)]
        else:
            height = [f32(gg.uniform(-500.0, 16000.0)) for _ in range(CELLS)]
        grids.append(height)
    report['normals'] = {'cases': 0, 'matches': 0}
    report['primary_light'] = {'cases': 0, 'matches': 0}
    for height in grids[:args.grids]:
        client.write('height', 'f', height)
        ok = client.call(NORMALS, [])
        got = client.read('normal', 'f', 3 * CELLS)
        expected = authored.normals(height)
        report['normals']['cases'] += 1
        report['normals']['matches'] += int(ok and compare_lists(got, expected))
        light_map = [f32(random.Random(len(report)).random()) for _ in range(3 * CELLS)]
        client.write('light_map', 'f', light_map)
        for world in (0, 30):
            client.write('world', 'i', [world])
            ok = client.call(LIGHT, [])
            got = client.read('primary', 'f', 3 * CELLS)
            report['primary_light']['cases'] += 1
            report['primary_light']['matches'] += int(
                ok and compare_lists(got, authored.primary_light(expected, light_map, world)))

    # Face texture coordinates
    scene = synthetic_scene(11)
    client.load_scene(scene)
    wave_c = floats(scene['wave'])
    cases = matches = 0
    for case in range(300):
        texture = g.choice(sorted(scene['sizes']))
        xi, yi = g.randrange(255), g.randrange(255)
        idx = [index(xi, yi), index(xi + 1, yi), index(xi + 1, yi + 1), index(xi, yi + 1)]
        client.write('idx0', 'i', [idx[0]])
        client.write('idx1', 'i', [idx[1]])
        client.write('idx2', 'i', [idx[2]])
        client.write('idx3', 'i', [idx[3]])
        offset = [f32(g.uniform(-1, 1)), f32(g.uniform(-1, 1))] if case % 2 else [0.0, 0.0]
        k = g.choice((0.0, f32(0.0015), f32(g.uniform(-2, 2))))
        small = case % 3 == 0
        base = Client.CONFIG + 0x300
        client.uc.mem_write(base, struct.pack('<2f', *offset))
        ok = client.call(UV, [texture - 0x7630, fbits(float(xi)), fbits(float(yi)), int(small), base, fbits(k)])
        got = client.read('uv', 'f', 8)
        width, height_ = scene['sizes'][texture]
        cases += 1
        matches += int(ok and compare_lists(got, authored.tile_uv(width, height_, float(xi), float(yi), small, offset,
                                                                  wave_c, k, idx)))
    report['tile_uv'] = {'cases': cases, 'matches': matches}

    # Tile corners: run 0x016ccda5 until its call of the face routine.
    att_c = (ctypes.c_uint16 * CELLS)(*scene['att'])
    height_c = floats(scene['height'])
    cases = matches = skipped = 0
    for case in range(300):
        xi, yi = g.randrange(255), g.randrange(255)
        client.write('corner', 'f', [0.0] * 12)
        ok = client.call(TILE, [fbits(float(xi)), fbits(float(yi)), xi, yi, fbits(1.0), 1, 0], until=0x016cd0af)
        result, idx, corner = authored.tile_corners(att_c, height_c, scene['water'], float(xi), float(yi), xi, yi)
        if result == 0:
            skipped += 1
            ok = not ok  # the client returns before the face call
            same = ok
        else:
            same = ok and compare_lists(client.read('corner', 'f', 12), corner) and \
                [client.read(n, 'i', 1)[0] for n in ('idx0', 'idx1', 'idx2', 'idx3')] == idx
        cases += 1
        matches += int(same)
    report['tile_corners'] = {'cases': cases, 'matches': matches, 'skipped_tiles': skipped}

    # Per-tile GL streams.
    streams = {'cases': 0, 'matches': 0, 'unsupported': 0, 'calls': 0, 'kinds': {}}
    for seed, world in enumerate(GENERIC_WORLDS[:args.worlds]):
        scene = synthetic_scene(100 + seed, world)
        client.load_scene(scene)
        built = authored.scene(scene)
        for case in range(args.tiles):
            xi, yi = g.randrange(255), g.randrange(255)
            for pass_ in (0, 2):
                client.write('pass_', 'i', [pass_])
                ok = client.call(TILE, [fbits(float(xi)), fbits(float(yi)), xi, yi, fbits(1.0), 1, 0])
                status, expected = authored.draw_tile(built, pass_, float(xi), float(yi), xi, yi)
                streams['cases'] += 1
                if status == 4:
                    streams['unsupported'] += 1
                    continue
                same = ok and client.stream == expected
                streams['matches'] += int(same)
                streams['calls'] += len(expected)
                for item in expected:
                    streams['kinds'][item[0]] = streams['kinds'].get(item[0], 0) + 1
                if not same and 'first_mismatch' not in streams:
                    streams['first_mismatch'] = {'world': world, 'tile': [xi, yi], 'pass': pass_, 'ok': ok,
                                                 'error': client.error, 'client': client.stream[:12],
                                                 'authored': expected[:12]}
    report['tile_streams'] = streams

    # RenderTerrain over a small box, through the end of the grass pass.
    frames = {'cases': 0, 'matches': 0}
    for seed, box in ((7, (8, 12, 19, 23)), (8, (0, 0, 11, 7))):
        scene = synthetic_scene(200 + seed, 0)
        client.load_scene(scene)
        client.write('xmin', 'i', [box[0]])
        client.write('ymin', 'i', [box[1]])
        client.write('xmax', 'i', [box[2]])
        client.write('ymax', 'i', [box[3]])
        client.uc.mem_write(G['force'], b'\1')
        client.uc.mem_write(G['alpha_flag'], b'\1')
        ok = client.call(RENDER, [0], until=RENDER_STOP)
        status, expected = authored.draw(authored.scene(scene), box, 1)
        frames['cases'] += 1
        same = ok and client.stream == expected
        frames['matches'] += int(same)
        frames.setdefault('calls', []).append(len(expected))
        if not same and 'first_mismatch' not in frames:
            diff = next((i for i, (a, b) in enumerate(zip(client.stream, expected)) if a != b),
                        min(len(client.stream), len(expected)))
            frames['first_mismatch'] = {'box': box, 'ok': ok, 'error': client.error, 'at': diff,
                                        'client': client.stream[diff:diff + 6], 'authored': expected[diff:diff + 6],
                                        'lengths': [len(client.stream), len(expected)]}
    report['render_terrain'] = frames

    # Negative control: the "natural" uv corner rule (index 2/3 instead of 1/0) must differ.
    report['negative_controls'] = negative_controls(authored)
    if args.game_root:
        report['installed'] = installed(args, authored, client)
    return report


def negative_controls(authored):
    g = random.Random(5)
    wave = [f32(g.uniform(-10, 10)) for _ in range(CELLS)]
    differ = 0
    for case in range(50):
        xi, yi = g.randrange(255), g.randrange(255)
        idx = [index(xi, yi), index(xi + 1, yi), index(xi + 1, yi + 1), index(xi, yi + 1)]
        exact = py_tile_uv(256.0, 256.0, float(xi), float(yi), 0, [0.0, 0.0], wave, 0.5, idx)
        natural = py_tile_uv(256.0, 256.0, float(xi), float(yi), 0, [0.0, 0.0], wave, 0.5,
                             [idx[0], idx[1], idx[2], idx[3]])
        natural[5] = fadd(fadd(fmul(float(yi), 0.25), 0.25), fmul(wave[idx[2]], 0.5))
        differ += int(exact != natural)
    return {'uv_natural_index_differs': differ == 50}


# --------------------------------------------------------------------------
# Installed worlds (private).

def decrypt_file(raw, magic):
    sys.path.insert(0, str(ROOT / 'model-recovery'))
    from bmd_encrypted import decrypt_modulus
    if raw[:4] == magic:
        return 'modulus', decrypt_modulus(raw[4:])
    library = ROOT / 'reconstructed/model-codec' / ('libmodelcodec.dylib' if sys.platform == 'darwin'
                                                     else 'libmodelcodec.so')
    decoder = ctypes.CDLL(str(library)).mu_bmd12_decode
    decoder.argtypes = [VOIDP, VOIDP, ctypes.c_int32]
    out = ctypes.create_string_buffer(len(raw))
    decoder(out, bytes(raw), len(raw))
    return 'v12', out.raw


def find(directory, name):
    if not directory.is_dir():
        return None
    lowered = name.lower()
    for entry in directory.iterdir():
        if entry.name.lower() == lowered:
            return entry
    return None


def installed(args, authored, client):
    data = Path(args.game_root) / 'Data'
    worlds = sorted(int(p.name[5:]) for p in data.iterdir() if p.name.lower().startswith('world') and
                    p.name[5:].isdigit())
    out = {'worlds': len(worlds), 'map': {}, 'att': {}, 'height': {}, 'light': {}, 'obj': {}, 'compared': {}}

    def count(group, key):
        out[group][key] = out[group].get(key, 0) + 1
    decoded = {}
    for number in worlds:
        folder = data / f'World{number}'
        world = number - 1
        entry = {}
        path = find(folder, f'EncTerrain{number}.map')
        if path:
            kind, plain = decrypt_file(path.read_bytes(), b'MAP\x01')
            status, map_number, l1, l2, alpha = authored.parse_map(plain)
            count('map', f'{kind}-{"ok" if status == 0 and map_number == number else "mismatch"}')
            py = py_parse_map(plain)
            count('map', 'python-equal' if py and (py[0], py[1], py[2]) == (map_number, l1, l2) and
                  compare_lists(py[3], alpha) else 'python-differs')
            entry.update(layer1=l1, layer2=l2, alpha=alpha)
        path = find(folder, f'EncTerrain{number}.att')
        if path:
            kind, plain = decrypt_file(path.read_bytes(), b'ATT\x01')
            status, att_number, att = authored.parse_attributes(plain)
            count('att', f'{kind}-{len(plain):#x}-{["ok", "bad-size", "corrupt"][status] if status < 3 else status}'
                  f'{"" if att_number == number else "-number-mismatch"}')
            py = py_parse_attributes(plain)
            count('att', 'python-equal' if py[2] == att else 'python-differs')
            entry['att'] = att
        path = find(folder, 'TerrainHeight.OZB')
        if path:
            raw = path.read_bytes()
            rgb, unresolved = world_is_rgb(world)
            if rgb:
                status, height = authored.height_rgb(raw)
                key = 'rgb'
            else:
                status, height = authored.height_bytes(raw, f32(3.0 if world == 0x37 else 1.5))
                key = 'bytes'
            count('height', f'{key}-{len(raw)}{"-unresolved-world" if unresolved else ""}-'
                  f'{"ok" if status == 0 else "refused"}')
            entry['height'] = height
        path = find(folder, 'TerrainLight.OZB')
        if path:
            status, light = authored.light(path.read_bytes())
            count('light', f'{"ok" if status == 0 and len(light) == 3 * CELLS else "other"}')
            entry['light'] = light
        path = find(folder, f'EncTerrain{number}.obj')
        if path:
            raw = path.read_bytes()
            kind, plain = decrypt_file(raw, b'\0\0\0\0')
            version, objects = plain[0], struct.unpack_from('<h', plain, 2)[0]
            sizes = {0: 30, 1: 32, 2: 33, 3: 45, 4: 46, 5: 54}
            fits = version in sizes and 4 + objects * sizes[version] == len(plain)
            count('obj', 'header-fits' if fits else 'header-does-not-fit')
        decoded[number] = entry
    # Client comparison on selected installed worlds.
    for number in args.installed_worlds:
        entry = decoded.get(number, {})
        if not all(k in entry for k in ('layer1', 'att', 'height', 'light')):
            continue
        world = number - 1
        result = {}
        client.write('height', 'f', entry['height'])
        ok = client.call(NORMALS, [])
        normal = authored.normals(entry['height'])
        result['normals'] = bool(ok and compare_lists(client.read('normal', 'f', 3 * CELLS), normal))
        client.write('light_map', 'f', entry['light'])
        client.write('world', 'i', [world])
        ok = client.call(LIGHT, [])
        primary = authored.primary_light(normal, entry['light'], world)
        result['primary_light'] = bool(ok and compare_lists(client.read('primary', 'f', 3 * CELLS), primary))
        scene = {'world': world, 'layer1': entry['layer1'], 'layer2': entry['layer2'], 'alpha': entry['alpha'],
                 'att': entry['att'], 'height': entry['height'], 'light': primary, 'light2': [0.0] * (3 * CELLS),
                 'wave': [0.0] * CELLS, 'grass_offset': [0.0] * CELLS, 'grass_map': bytes([1]) * CELLS,
                 'water': 1201.0, 'time': 0.0, 'detail': 0, 'grass_disabled': 0,
                 'sizes': installed_sizes(data / f'World{number}')}
        client.load_scene(scene)
        built = authored.scene(scene)
        g = random.Random(number)
        tiles = matches = unsupported = 0
        for case in range(args.installed_tiles):
            xi, yi = g.randrange(252), g.randrange(252)
            for pass_ in (0, 2):
                client.write('pass_', 'i', [pass_])
                ok = client.call(TILE, [fbits(float(xi)), fbits(float(yi)), xi, yi, fbits(1.0), 1, 0])
                status, expected = authored.draw_tile(built, pass_, float(xi), float(yi), xi, yi)
                if status == 4:
                    unsupported += 1
                    continue
                tiles += 1
                matches += int(ok and client.stream == expected)
        result['tile_streams'] = {'cases': tiles, 'matches': matches, 'unsupported': unsupported}
        out['compared'][str(number)] = result
    return out


def world_is_rgb(world):
    static = (world in (0x2a, 0x3f, 0x64, 0x65, 0x6e, 0x6f, 0x70, 0x7a) or 0x52 <= world <= 0x5a or
              0x7b <= world <= 0x85)
    return static, not static


TILE_FILES = ['TileGrass01.OZJ', 'TileGrass02.OZJ', 'TileGround01.OZJ', 'TileGround02.OZJ', 'TileGround03.OZJ',
              'TileWater01.OZJ', 'TileWood01.OZJ', 'TileRock01.OZJ', 'TileRock02.OZJ', 'TileRock03.OZJ',
              'TileRock04.OZJ', 'TileRock05.OZJ', 'TileRock06.OZJ', 'TileRock07.OZJ', 'AlphaTile01.OZT']
GRASS_FILES = ['TileGrass01.OZT', 'TileGrass02.OZT', 'TileGrass03.OZT', 'TileGrass04.OZT', 'TileGrass05.OZT']


def image_size(path):
    raw = path.read_bytes()
    if path.suffix.lower() == '.ozj':
        payload = raw[24:]
        if payload[:2] == b'\xff\xd8':
            i = 2
            while i + 9 < len(payload):
                if payload[i] != 0xff:
                    i += 1
                    continue
                marker = payload[i + 1]
                length = struct.unpack('>H', payload[i + 2:i + 4])[0]
                if marker in (0xc0, 0xc1, 0xc2):
                    h, w = struct.unpack('>HH', payload[i + 5:i + 9])
                    return float(w), float(h)
                i += 2 + length
            return None
    else:
        payload = raw[4:]
    if len(payload) >= 18:
        w, h = struct.unpack_from('<HH', payload, 12)
        return float(w), float(h)
    return None


def installed_sizes(folder):
    sizes = {}
    for i, name in enumerate(TILE_FILES):
        path = find(folder, name)
        if path:
            size = image_size(path)
            if size:
                sizes[0x7630 + i] = size
    for i in range(1, 85):
        path = find(folder, f'ExtTile{i:02d}.OZJ')
        if path:
            size = image_size(path)
            if size:
                sizes[0x763e + i] = size
    for i, name in enumerate(GRASS_FILES):
        path = find(folder, name)
        if path:
            size = image_size(path)
            if size:
                sizes[0x7694 + i] = size
    return sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--flag', help='captured trigonometric dispatch flag (4 bytes at 0x0bdd1cc8)')
    parser.add_argument('--library', default=str(ROOT / 'reconstructed/terrain' /
                                                  ('libterrain.dylib' if sys.platform == 'darwin' else
                                                   'libterrain.so')))
    parser.add_argument('--game-root')
    parser.add_argument('--grids', type=int, default=3)
    parser.add_argument('--worlds', type=int, default=len(GENERIC_WORLDS))
    parser.add_argument('--tiles', type=int, default=150)
    parser.add_argument('--installed-worlds', type=lambda s: [int(x) for x in s.split(',') if x], default=[1])
    parser.add_argument('--installed-tiles', type=int, default=400)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        authored = Authored(args.library)
        report = run_client(args, authored)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    summary = {k: v for k, v in report.items() if isinstance(v, dict) and 'cases' in v}
    print(json.dumps({k: [v['cases'], v['matches']] for k, v in summary.items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
