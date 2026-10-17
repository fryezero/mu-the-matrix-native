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

NATIVE-TERRAIN-002 (skip with --skip-002, scale with --scale-002 N): the
24-bit height selector 0x016c9868 for every world index with handler objects
built by their own constructors, AddTerrainLight 0x016cacfc, the world tile
streams of 36 worlds (scrolls, blend states, animated layer, neighbour face,
world-0x22 particles), CreateFrustrum 0x016cba24, CreateFrustrum2D
0x016d20d9, TestFrustrum2D 0x016ccce7, RenderTerrain with live frustum tests
and RenderTerrainAlphaBitmap 0x016cdd5f, plus Python models and negative
controls (docs/research/client-terrain-frame.md). Their substitutions are
listed in the report under 'substitutions'.

GL imports are recorded at stub addresses written into the copied import
slots. Three calls are always substituted: the texture manager
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
         att=0x0b795420, height=0x0b6f5420, light=0x0b9f5430, light2=0x0bc35430, wave=0x0b634ea8, wave2=0x0b674ea8,
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
      0x01a7c748: ('glBlendFunc', 8), 0x01a7c740: ('glDepthMask', 4), 0x01a7c76c: ('glColor3f', 12),
      0x01a7c784: ('glGetFloatv', 8)}
OPENGL_SLOTS = (0x01a7c64c, 0x01a7c790)
# Substituted only by the NATIVE-TERRAIN-002 checks that need them (labelled in the report):
CRT_RAND, PARTICLE, CHAOS_EFFECTS, CAMERA_SINGLETON, SCREEN_WIDTH = 0x01989721, 0x0168fafd, 0x009dc0b1, 0x0098647b, 0x016bc355
FRAME_COUNTER, HERO_POINTER, WATER_MOVE = 0x0b6b53e0, 0x0a39d754, 0x0b6b4ea8
EXTRA_HOOKS = (CRT_RAND, PARTICLE, CHAOS_EFFECTS, CAMERA_SINGLETON, SCREEN_WIDTH)
GENERIC_WORLDS = (0, 1, 2, 3, 4, 8, 142, 0x50, 0x8d)


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


def cvtt(x):
    """cvttss2si: NaN and out-of-range give 0x80000000."""
    if x != x or not -2147483904.0 < x < 2147483648.0:
        return -2147483648
    return int(x)


def crem(a, m):
    """C remainder (sign of the dividend)."""
    r = abs(a) % m
    return -r if a < 0 else r


LAVA = set([0x3f] + list(range(0x52, 0x5b)))
ADDITIVE = set([7, 0x80, 0x81, 0x82])
CHAOS = set(list(range(0x12, 0x18)) + [0x35, 0x61])


def py_scroll(scene, layer, xf, yf):
    """Layer-1 offsets of 0x016cff65 (water, lava and per-world scrolling tiles)."""
    w, time = scene['world'], scene['time']
    t = cvtt(time)
    fwd = lambda m: fdiv(f32(float(crem(t, m))), float(m))
    bwd = lambda m: fdiv(-f32(float(crem(t, m))), float(m))
    cosv = lambda: f32(math.cos(fmul(time, f32(0.0001))))
    cos25 = lambda: fmul(fmul(fadd(cosv(), 1.0), 0.5), 0.5)
    offset, k = [0.0, 0.0], 0.0
    generic = lambda: ([fwd(20000), cos25()], f32(0.0015))
    if layer == 5:
        if w == 0x1e:
            offset, k = [bwd(20000), cos25()], f32(0.0015)
        elif w == 0x5e:
            offset, k = [bwd(20000), fwd(20000)], f32(0.0015)
        elif w == 0x7a:
            offset, k = [fwd(50000), fmul(fadd(cosv(), 1.0), f32(0.1))], f32(0.0015)
        elif w == 0x8d:
            offset, k = [0.0, 0.0], 0.0
        else:
            offset, k = generic()
        if w == 0x22 and scene.get('random'):
            rand = scene['random']
            if rand() % 50 == 0:
                x = fadd(fmul(xf, 100.0), fmul(f32(float(rand() % 100 + 1)), 1.0))
                y = fadd(fmul(yf, 100.0), fmul(f32(float(rand() % 100 + 1)), 1.0))
                scene.setdefault('effects', []).append(('effect', 0x7f90, fbits(x), fbits(y),
                                                        fbits(fadd(scene.get('hero_z', 0.0), 10.0))))
    if w in LAVA:
        if layer == 0xb:
            offset, k = generic()
    elif w in (0x6e, 0x64, 0x65, 0x6f):
        if layer == 6:
            offset, k = generic()
    elif w == 0x70:
        if 0x15 <= layer <= 0x18:
            f, b, c = fwd(30000), bwd(30000), cos25()
            offset = {0x15: [c, f], 0x16: [f, c], 0x17: [b, c], 0x18: [c, b]}[layer]
            k = f32(0.002)
    elif w == 0x7a:
        if layer == 0x10:
            offset, k = generic()
    elif w in (0x8a, 0x8c, 0x8d):
        table = {0x8a: {0x20: 2, 0x21: 3, 0x22: 1}, 0x8c: {0x14: 1, 0x15: 2, 0x16: 3},
                 0x8d: {0x17: 0, 0x1e: 0, 0x18: 1, 0x1f: 1, 0x19: 2, 0x20: 2, 0x1a: 3, 0x21: 3}}[w]
        if layer in table:
            c = cos25()
            offset = [[fwd(20000), c], [c, bwd(20000)], [bwd(20000), c], [c, fwd(20000)]][table[layer]]
            k = f32(0.0015)
    return offset, k


def py_face_alpha_state(w, layer):
    """RenderFace 0x016cf46c blend choice: True = alpha state, None = nothing drawn."""
    if w == 0x27:
        return None if layer == 0x64 else layer == 3
    if 0x62 <= w <= 0x63 or 0x2d <= w <= 0x32:
        return layer == 4
    if w == 0x33:
        return layer == 2
    if 0x45 <= w <= 0x4a:
        return layer == 10
    if w in (0x50, 0x51):
        return layer == 12
    if w in (0x5b, 0x5c):
        return layer == 9
    return layer == 0xe


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
        additive = w == 0x3f or 0x52 <= w <= 0x5a
        blade = fmul(sizes[texture][1], 2.0)
        out.append(('bind', texture))
        if additive:
            out.append(('state', 3, 0))
        u = fadd(fmul(xf, 0.25), scene['grass_offset'][yi & 0xff])
        uv = [u, 0.0, fadd(u, 0.25), 0.0, fadd(u, 0.25), 1.0, u, 1.0]
        c[3] = list(c[0])          # 0x016d127a: corner 3 = corner 0, corner 1 = corner 2
        c[1] = list(c[2])
        c[0][2] = fadd(c[0][2], blade)
        c[1][2] = fadd(c[1][2], blade)
        c[0][0] = fadd(c[0][0], -50.0)
        c[1][0] = fadd(c[1][0], -50.0)
        second = (w in (0x50, 0x51, 0x90, 0x8d, 0x8e) or
                  (w in (0x6e, 0x6f) and scene['layer1'][idx[0]] == 4))
        sway = scene['wave2'] if second else scene['wave']
        c[0][1] = fadd(c[0][1], sway[idx[0]])
        c[1][1] = fadd(c[1][1], sway[idx[1]])
        out.append(('begin', 7))
        for k in range(4):
            out.append(('tex', fbits(uv[2 * k]), fbits(uv[2 * k + 1])))
            out.append(('c3',) + tuple(fbits(v) for v in light[3 * idx[k]:3 * idx[k] + 3]))
            out.append(('v',) + tuple(fbits(v) for v in c[k]))
        out.append(('end',))
        if additive:
            out.append(('state', 1, 0))
        return 0
    i0 = idx[0]
    neighbour = bool(scene['att'][i0] & 0x4000)
    offset, k = [0.0, 0.0], 0.0
    if all(ge(alpha[i], 1.0) for i in idx) and not neighbour:
        layer, layer1_drawn = scene['layer2'][i0], False
    else:
        layer, layer1_drawn = scene['layer1'][i0], True
        offset, k = py_scroll(scene, layer, xf, yf)
    texture = 0x7630 + layer
    if texture not in sizes:
        return 4

    def corners(uv, colour):
        out.append(('begin', 6))
        for q in range(4):
            out.append(('tex', fbits(uv[2 * q]), fbits(uv[2 * q + 1])))
            out.append(colour(idx[q]))
            out.append(('v',) + tuple(fbits(v) for v in c[q]))
        out.append(('end',))
    lit = lambda i: tuple(fbits(fadd(light[3 * i + j], light2[3 * i + j])) for j in range(3))

    uv = py_tile_uv(sizes[texture][0], sizes[texture][1], xf, yf, 0, offset, scene['wave'], k, idx)
    blend = py_face_alpha_state(w, layer)
    status = 0
    if blend is not None:
        out.append(('state', 2, 1) if blend else ('state', 1, 0))
        if w in (0x71, 0x91) and scene['detail'] >= 4 and scene['att'][i0] & 0x2000:
            return 4
        out.append(('bind', texture))
        corners(uv, lambda i: ('c3',) + lit(i))
    if scene['detail'] >= 4 and neighbour:
        around = [index(xi - 1, yi), index(xi + 1, yi), index(xi, yi + 1), index(xi, yi - 1)]
        if any(not 0 <= a < CELLS for a in around):
            status = 3
        else:
            out.append(('bind', 0x7723))
            edge = not all(scene['att'][a] & 0x4000 for a in around)
            out.append(('state', 3, 0))
            a = 0.5 if edge else f32(0.8)
            corners(uv, lambda i: ('c4', fbits(f32(0.8)), fbits(f32(0.8)), fbits(f32(0.8)), fbits(a)))
            out.append(('state', 1, 0))
    if not any(gt(alpha[i], 0.0) for i in idx):
        return status
    layer2 = scene['layer2'][i0]
    if (w in ADDITIVE and layer2 == 5) or (w == 0x85 and layer2 == 4):
        animated = 0x7630 + 200 + scene.get('frame_counter', 0)
        if animated not in sizes:
            return 4
        uv = py_tile_uv(sizes[animated][0], sizes[animated][1], xf, yf, 1, [0.0, 0.0], scene['wave'], 0.0, idx)
        out.append(('state', 3, 0))
        out.append(('bind', animated))
        corners(uv, lambda i: ('c3', fbits(alpha[i]), fbits(alpha[i]), fbits(alpha[i])))
        return status
    if not layer1_drawn:
        return status
    if layer2 != 5:
        offset = [0.0, 0.0]
    if layer2 == 0xff:
        return status
    texture2 = 0x7630 + layer2
    if texture2 not in sizes:
        return 4
    uv = py_tile_uv(sizes[texture2][0], sizes[texture2][1], xf, yf, 0, offset, scene['wave'], 0.0, idx)
    out.append(('state', 2, 1))
    out.append(('bind', texture2))
    corners(uv, lambda i: ('c4',) + lit(i) + (fbits(alpha[i]),))
    return status


def py_add_light(x, y, light, light_range, buffer, variant=None):
    """AddTerrainLight 0x016cacfc; variant 'clamp1' also clamps above at 1, 'noclamp' drops the 0 clamp
    (negative controls)."""
    out = list(buffer)
    rf = f32(float(light_range))
    xf, yf = fdiv(x, 100.0), fdiv(y, 100.0)
    xi, yi = cvtt(xf), cvtt(yf)
    row = f32(float(yi - light_range))
    for yy in range(yi - light_range, yi + light_range + 1):
        column = f32(float(xi - light_range))
        for xx in range(xi - light_range, xi + light_range + 1):
            dx, dy = fsub(xf, column), fsub(yf, row)
            d = fadd(fmul(dx, dx), fmul(dy, dy))
            lf = fdiv(fsub(rf, f32(math.sqrt(d))), rf)
            if gt(lf, 0.0):
                i = index_repeat(xx, yy)
                for k in range(3):
                    v = fadd(fmul(light[k], lf), out[3 * i + k])
                    if variant != 'noclamp' and v == v and 0.0 > v:
                        v = 0.0
                    if variant == 'clamp1' and gt(v, 1.0):
                        v = 1.0
                    out[3 * i + k] = v
            column = fadd(column, 1.0)
        row = fadd(row, 1.0)
    return out


def py_test_frustum_2d(xs, ys, state, x, y, r):
    if 1 <= state <= 4:
        return 1
    j = 3
    for i in range(4):
        d = fsub(fmul(fsub(xs[i], x), fsub(ys[j], y)), fmul(fsub(xs[j], x), fsub(ys[i], y)))
        if r == r and d == d and r >= d:
            return 0
        j = i
    return 1


def py_height_is_rgb(world):
    """0x016c9868 with the handler table of 0x00ea488e."""
    literal = (world in (0x2a, 0x3f, 0x64, 0x65, 0x6e, 0x6f, 0x70, 0x7a) or 0x52 <= world <= 0x5a or
               0x7b <= world <= 0x85)
    return int(literal or 0x86 <= world <= 0x91)


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
RANDOM_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
EFFECT_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                                   ctypes.POINTER(ctypes.c_float))


class Scene(ctypes.Structure):
    _fields_ = [('world_index', ctypes.c_int32), ('layer1', ctypes.c_void_p), ('layer2', ctypes.c_void_p),
                ('alpha', ctypes.c_void_p), ('attributes', ctypes.c_void_p), ('height', ctypes.c_void_p),
                ('light', ctypes.c_void_p), ('light2', ctypes.c_void_p), ('wave', ctypes.c_void_p),
                ('wave2', ctypes.c_void_p), ('grass_offset', ctypes.c_void_p), ('grass_map', ctypes.c_void_p), ('water_height', ctypes.c_float),
                ('time', ctypes.c_float), ('detail', ctypes.c_int32), ('grass_disabled', ctypes.c_uint8),
                ('texture_size', SIZE_CALLBACK), ('texture_context', ctypes.c_void_p),
                ('frame_counter', ctypes.c_int32), ('random', RANDOM_CALLBACK), ('effect', EFFECT_CALLBACK),
                ('effect_context', ctypes.c_void_p), ('hero_z', ctypes.c_float)]


class Frustum(ctypes.Structure):
    _fields_ = [('vertex', ctypes.c_float * 15), ('normal', ctypes.c_float * 15), ('d', ctypes.c_float * 5),
                ('x_min', ctypes.c_int32), ('y_min', ctypes.c_int32), ('x_max', ctypes.c_int32),
                ('y_max', ctypes.c_int32), ('x2d', ctypes.c_float * 4), ('y2d', ctypes.c_float * 4)]


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
        self.setup_002()

    def setup_002(self):
        lib = self.lib
        lib.mu_terrain_height_is_rgb.argtypes = [ctypes.c_int32, VOIDP]
        lib.mu_terrain_world_handler_flag.argtypes = [ctypes.c_int32]
        lib.mu_terrain_add_light.argtypes = [ctypes.c_float, ctypes.c_float, VOIDP, ctypes.c_int32, VOIDP]
        lib.mu_terrain_frame_light.argtypes = [VOIDP, VOIDP] + [ctypes.c_int32] * 4
        lib.mu_terrain_water_move.argtypes = [ctypes.c_int32, ctypes.c_float]
        lib.mu_terrain_water_move.restype = ctypes.c_float
        lib.mu_terrain_frustum_create.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, VOIDP, VOIDP,
                                                  ctypes.POINTER(Frustum)]
        lib.mu_terrain_frustum_2d_params_for.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                                                         ctypes.c_float, ctypes.c_float, VOIDP]
        lib.mu_terrain_frustum_2d.argtypes = [ctypes.c_int32, VOIDP, VOIDP, VOIDP, ctypes.c_int, VOIDP, VOIDP]
        lib.mu_terrain_test_frustum_2d.argtypes = [VOIDP, VOIDP, ctypes.c_int32, ctypes.c_float, ctypes.c_float,
                                                   ctypes.c_float]
        lib.mu_terrain_render.argtypes = [ctypes.POINTER(Scene), ctypes.POINTER(Frustum), ctypes.c_int32, ctypes.c_int,
                                          ctypes.c_int, ctypes.POINTER(Sink), ctypes.POINTER(Stats)]
        lib.mu_terrain_decal.argtypes = [ctypes.POINTER(Scene), ctypes.c_int32] + [ctypes.c_float] * 4 + [
            VOIDP, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.POINTER(Sink)]
        lib.mu_terrain_decal.restype = ctypes.c_long

    def height_is_rgb(self, world):
        unresolved = ctypes.c_int()
        return self.lib.mu_terrain_height_is_rgb(world, ctypes.byref(unresolved)), unresolved.value

    def add_light(self, x, y, light, light_range, buffer):
        grid = floats(buffer)
        self.lib.mu_terrain_add_light(x, y, floats(light), light_range, grid)
        return list(grid)

    def frustum_create(self, aspect, view_far, fov, modelview12, position):
        f = Frustum()
        self.lib.mu_terrain_frustum_create(aspect, view_far, fov, floats(modelview12), floats(position),
                                           ctypes.byref(f))
        return f

    def frustum_2d(self, world, position, angle, params, wide):
        x, y = floats([0.0] * 4), floats([0.0] * 4)
        status = self.lib.mu_terrain_frustum_2d(world, floats(position), floats(angle), floats(params), wide, x, y)
        return status, list(x), list(y)

    def params_2d(self, world, mode, width, scale, distance):
        out = floats([0.0] * 5)
        ok = self.lib.mu_terrain_frustum_2d_params_for(world, mode, width, scale, distance, out)
        return ok, list(out)

    def render(self, scene_built, frustum, scene_state, top_view, alpha_layers):
        out = []
        sink = self.recorder(out)
        status = self.lib.mu_terrain_render(ctypes.byref(scene_built[0]), ctypes.byref(frustum), scene_state,
                                            top_view, alpha_layers, ctypes.byref(sink), ctypes.byref(Stats()))
        return status, out

    def decal(self, scene_built, texture, x, y, sx, sy, light, rotation, alpha, height, follow, flip):
        out = []
        sink = self.recorder(out)
        fans = self.lib.mu_terrain_decal(ctypes.byref(scene_built[0]), texture, x, y, sx, sy, floats(light),
                                         rotation, alpha, height, follow, flip, ctypes.byref(sink))
        return fans, out

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
        effects = []

        def rand(context):
            source = s.get('random')
            return source() if source else 0

        def effect(context, kind, position, light):
            effects.append(('effect', kind, fbits(position[0]), fbits(position[1]), fbits(position[2])))
        random_cb = RANDOM_CALLBACK(rand) if s.get('random') else RANDOM_CALLBACK()
        effect_cb = EFFECT_CALLBACK(effect)
        keep += [random_cb, effect_cb, effects]
        s['effects_out'] = effects
        scene = Scene(s['world'], arr(ctypes.c_uint8, s['layer1']), arr(ctypes.c_uint8, s['layer2']),
                      arr(ctypes.c_float, s['alpha']), arr(ctypes.c_uint16, s['att']),
                      arr(ctypes.c_float, s['height']), arr(ctypes.c_float, s['light']),
                      arr(ctypes.c_float, s['light2']), arr(ctypes.c_float, s['wave']),
                      arr(ctypes.c_float, s['wave2']), arr(ctypes.c_float, s['grass_offset']),
                      arr(ctypes.c_uint8, s['grass_map']), s['water'],
                      s['time'], s['detail'], s['grass_disabled'], callback, None, s.get('frame_counter', 0),
                      random_cb, effect_cb, None, s.get('hero_z', 0.0))
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

def synthetic_scene(seed, world=0, extended=False):
    """extended adds the world-specific tiles (scrolling/lava layers, 0x4000 neighbour cells, the animated
    layer bitmaps 0x76f8.., TileBright 0x7723) used by NATIVE-TERRAIN-002."""
    g = random.Random(seed)
    layer_pool = [0, 1, 2, 3, 4, 5, 6, 7, 8, 0xe, 0xff]
    if extended:
        layer_pool = [0, 1, 2, 3, 4, 5, 5, 6, 7, 8, 9, 10, 0xb, 0xb, 0xc, 0xe, 0x10, 0x14, 0x15, 0x16, 0x17, 0x18,
                      0x19, 0x1a, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x64, 0xff]
    scene = {'world': world, 'water': 1201.0, 'time': g.choice([0.0, 12345.5, 250000.0]), 'detail': g.choice([0, 4]),
             'grass_disabled': 0}
    if extended:
        scene['time'] = g.choice([0.0, 12345.5, 250000.0, 98765.25, 3.5e6, -1234.75])
        scene['frame_counter'] = g.randrange(32)
        scene['hero_z'] = f32(g.uniform(0.0, 500.0))
    scene['layer1'] = bytes(g.choice(layer_pool[:-1]) for _ in range(CELLS))
    scene['layer2'] = bytes(g.choice(layer_pool) for _ in range(CELLS))
    alpha_pool = [0.0, 0.0, 0.0, 1.0, f32(128 / 255.0), f32(1 / 255.0), f32(254 / 255.0)]
    scene['alpha'] = [g.choice(alpha_pool) for _ in range(CELLS)]
    att_pool = [0, 0, 0, 1, 4, 8, 0x40, 0x44, 0x80 & 0, 0x0100 & 0xfaff, 0x1000, 0x2000]
    if extended:
        att_pool += [0x4000, 0x4000, 0x4000, 0x4040, 0x200, 0x6000]
    scene['att'] = [g.choice(att_pool) for _ in range(CELLS)]
    scene['height'] = [f32(g.uniform(-50.0, 400.0)) for _ in range(CELLS)]
    scene['light'] = [f32(g.random()) for _ in range(3 * CELLS)]
    scene['light2'] = [f32(g.uniform(-0.25, 0.25)) if seed & 1 else 0.0 for _ in range(3 * CELLS)]
    scene['wave'] = [f32(g.uniform(-10.0, 10.0)) for _ in range(CELLS)]
    scene['wave2'] = [f32(g.uniform(-15.0, 15.0)) for _ in range(CELLS)]
    scene['grass_offset'] = [f32((g.randrange(32768) % 4) / 4.0) for _ in range(CELLS)]
    scene['grass_map'] = bytes(g.choice((1, 1, 1, 0)) for _ in range(CELLS))
    sizes = {}
    for layer in layer_pool[:-1]:
        sizes[0x7630 + layer] = (float(g.choice((64, 128, 256, 512))), float(g.choice((64, 128, 256))))
    for layer in (0, 1):
        sizes[0x7694 + layer] = (256.0, 64.0)
    if extended:
        for n in range(32):
            sizes[0x76f8 + n] = (float(g.choice((64, 128, 256))), float(g.choice((64, 128, 256))))
        sizes[0x7723] = (128.0, 128.0)
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
    BSS = ((0x01cf0000, 0x01d30000), (0x01ec3000, 0x01ec4000), (0x01ec9000, 0x01eca000), (0x06fce000, 0x06fcf000),
           (0x0a39d000, 0x0a39e000), (0x0b5e0000, 0x0bde0000))
    OBJECTS = 0x00200000   # synthetic hero, camera, world manager and handler objects (0x10000 bytes)

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
        for base, size in ((self.STUBS, 0x10000), (self.BITMAPS, 0x60000), (self.CONFIG, 0x1000), (self.OBJECTS, 0x10000),
                           (self.TEB, 0x1000), (self.GDT, 0x1000), (self.STACK, 0x40000)):
            uc.mem_map(base, size, UC_PROT_ALL)
        # Flat code/data descriptors, then the TEB for fs: (SEH frames).
        gdt = (b'\0' * 8 + descriptor(0, 0xfffff, 0x9a, 0xc) + descriptor(0, 0xfffff, 0x92, 0xc) +
               descriptor(self.TEB, 0xfff, 0x92, 0x4))
        uc.mem_write(self.GDT, gdt)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, self.GDT, len(gdt) - 1, 0))
        uc.reg_write(x86.UC_X86_REG_SS, 2 << 3)   # 32-bit stack segment once a GDT is loaded
        uc.reg_write(x86.UC_X86_REG_FS, 3 << 3)
        uc.mem_write(self.TEB, struct.pack('<I', 0xffffffff))
        # Import stubs: recorded GL calls; every other OpenGL slot traps.
        self.stub_names = {}
        for i, slot in enumerate(range(OPENGL_SLOTS[0], OPENGL_SLOTS[1], 4)):
            stub = self.STUBS + 8 * i
            name, args = GL.get(slot, (None, None))
            uc.mem_write(stub, b'\xc3' if not args else b'\xc2' + struct.pack('<H', args))
            uc.mem_write(slot, struct.pack('<I', stub))
            self.stub_names[stub] = name
        uc.hook_add(UC_HOOK_CODE, self.on_stub, begin=self.STUBS, end=self.STUBS + 0xfff)
        for address in list(STATE_WRAPPERS) + [BIND] + list(LOOKUPS) + [SINGLETON]:
            uc.hook_add(UC_HOOK_CODE, self.on_entry, begin=address, end=address)
        self.extra = {}   # optional substitutions, only while a check installs them (see EXTRA_HOOKS)
        for address in EXTRA_HOOKS:
            uc.hook_add(UC_HOOK_CODE, self.on_extra, begin=address, end=address)
        self.modelview = [0.0] * 16
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
            uc.emu_stop()   # the stop address shares a page with the stubs; chained blocks skip `until`
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
        elif name == 'glColor3f':   # recorded like glColor3fv (same GL state); counted apart in 'gl_color3f'
            self.stream.append(('c3', self.farg(0), self.farg(1), self.farg(2)))
            self.color3f = getattr(self, 'color3f', 0) + 1
        elif name == 'glGetFloatv':
            self.uc.mem_write(self.arg(1), struct.pack('<16f', *self.modelview))
            self.gl_state.append((name, self.arg(0)))
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

    def on_extra(self, uc, address, size, ignored):
        handler = self.extra.get(address)
        if handler:
            handler(self)

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
        self.write('wave2', 'f', s['wave2'])
        self.write('grass_offset', 'f', s['grass_offset'])
        self.uc.mem_write(G['grass_map'], s['grass_map'])
        self.write('water', 'f', [s['water']])
        self.write('time', 'f', [s['time']])
        self.uc.mem_write(G['grass_disabled'], bytes([s['grass_disabled']]))
        self.uc.mem_write(self.CONFIG + 0x2c, struct.pack('<i', s['detail']))
        self.uc.mem_write(G['config'], struct.pack('<I', self.CONFIG))
        self.uc.mem_write(FRAME_COUNTER, struct.pack('<i', s.get('frame_counter', 0)))
        self.uc.mem_write(HERO_POINTER, struct.pack('<I', self.OBJECTS))
        self.uc.mem_write(self.OBJECTS + 0x33ac, struct.pack('<4f', 0.0, 0.0, s.get('hero_z', 0.0), 0.0))
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
    cases = matches = nan_only = 0
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
        mine = authored.face_normal(a, b, c)
        cases += 1
        exact = ok and compare_lists(got, mine)
        matches += int(exact)
        # Out-of-domain inputs (inf/huge) make NaN: x86 generates 0xffc00000,
        # arm64 0x7fc00000. Counted apart; every other bit must agree.
        if ok and not exact and all(fbits(x) == fbits(y) or (x != x and y != y) for x, y in zip(got, mine)):
            nan_only += 1
    report['face_normal'] = {'cases': cases, 'matches': matches, 'generated_nan_sign_only': nan_only}

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

    loader_checks(client, authored, report, g)
    if not args.skip_002:
        terrain2_checks(client, authored, report, g, args.scale_002)

    # Negative control: the "natural" uv corner rule (index 2/3 instead of 1/0) must differ.
    report['negative_controls'] = negative_controls(authored)
    if args.game_root:
        report['installed'] = installed(args, authored, client)
    return report


# --------------------------------------------------------------------------
# Loader loops and the per-frame update, run as bounded regions of the
# client's functions (inputs placed in their frames) or as whole calls.

CRT_FSEEK, CRT_FREAD, CRT_FREE, CRT_FCLOSE, ERROR_BOX = 0x01989dab, 0x01989230, 0x0191bac2, 0x01988c95, 0x016cef3f
WAVE = 0x016ca4fa
ALTERNATE = 0x01ec3254
POISON = b'\xa5'


def install_crt(client):
    """Entry stubs for CRT file I/O and two helpers (modelled, labelled in the report)."""
    from unicorn import UC_HOOK_CODE
    client.file, client.cursor, client.crt_calls, client.crt_allowed = b'', 0, [], set()

    def hook(uc, address, size, ignored):
        if address not in client.crt_allowed:
            client.error = ('unexpected-crt', hex(address))
            uc.emu_stop()
            return
        if address == CRT_FREAD:
            buffer, item, count = client.arg(0), client.arg(1), client.arg(2)
            chunk = client.file[client.cursor:client.cursor + item * count]
            client.cursor += len(chunk)
            uc.mem_write(buffer, chunk)
            client.ret(len(chunk) // item if item else 0, 0)
        elif address == CRT_FSEEK:
            client.cursor = client.arg(1)
            client.ret(0, 0)
        else:
            client.crt_calls.append(hex(address))
            client.ret(0, 0)
    for address in (CRT_FSEEK, CRT_FREAD, CRT_FREE, CRT_FCLOSE, ERROR_BOX):
        client.uc.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)


def region(client, start, end, slots, frame_bytes):
    uc, x86 = client.uc, client.x86
    client.stream, client.gl_state, client.error = [], [], None
    ebp = client.STACK + 0x3e000
    uc.mem_write(ebp - frame_bytes, POISON * frame_bytes)
    for offset, value in slots.items():
        uc.mem_write(ebp + offset, struct.pack('<I', value & 0xffffffff))
    uc.reg_write(x86.UC_X86_REG_EBP, ebp)
    uc.reg_write(x86.UC_X86_REG_ESP, ebp - frame_bytes)
    uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
    uc.reg_write(x86.UC_X86_REG_FPCW, 0x27f)
    uc.reg_write(x86.UC_X86_REG_MXCSR, 0x1f80)
    try:
        uc.emu_start(start, end, timeout=0, count=0)
    except Exception as failure:  # UcError
        client.error = client.error or ('uc', str(failure))
    return (client.error is None and uc.reg_read(x86.UC_X86_REG_EIP) == end and
            uc.reg_read(x86.UC_X86_REG_EBP) == ebp), uc.reg_read(x86.UC_X86_REG_EAX)


WINDOW_AT = 0x0b5f4ea8  # scratch inside the mapped terrain area for file buffers (grass table, not read here)


def loader_checks(client, authored, report, g):
    install_crt(client)
    uc = client.uc
    big = WINDOW_AT

    def bits_of(data):
        return list(struct.unpack(f'<{len(data) // 4}I', data))

    # 8-bit height loop 0x016c850c..0x016c85af ([ebp-8] buffer, [ebp-0x1c] 0x438)
    cases = matches = 0
    for world in (0, 0x37, 142):
        raw = b'BM8\x04' + bytes(g.randrange(256) for _ in range(0x438 + CELLS))
        uc.mem_write(big, raw[4:])
        uc.mem_write(G['height'], POISON * (4 * CELLS))
        client.write('world', 'i', [world])
        ok, _ = region(client, 0x016c850c, 0x016c85af, {-8: big, -0x1c: 0x438}, 0x340)
        status, mine = authored.height_bytes(raw, authored.lib.mu_terrain_height_scale(world))
        cases += 1
        matches += int(ok and status == 0 and compare_lists(client.read('height', 'f', CELLS), mine))
    report['height_bytes'] = {'cases': cases, 'matches': matches}

    # 24-bit height loop 0x016c8843..0x016c8958 ([ebp-0x14] whole file)
    cases = matches = 0
    for _ in range(2):
        raw = b'BM6\x00' + bytes(g.randrange(256) for _ in range(54 + 3 * CELLS))
        uc.mem_write(big, raw)
        uc.mem_write(G['height'], POISON * (4 * CELLS))
        ok, _ = region(client, 0x016c8843, 0x016c8958, {-0x14: big, -0x20: len(raw)}, 0x280)
        status, mine = authored.height_rgb(raw)
        cases += 1
        matches += int(ok and status == 0 and compare_lists(client.read('height', 'f', CELLS), mine))
    report['height_rgb'] = {'cases': cases, 'matches': matches}

    # TerrainLight pixel loop 0x0185b366..0x0185b458 (CRT fseek/fread modelled)
    cases = matches = 0
    for width, height in ((256, 256), (16, 8), (3, 5)):
        header = bytearray(54)
        struct.pack_into('<2sI', header, 0, b'BM', 54 + 3 * width * height)
        struct.pack_into('<III', header, 14, 40, width, height)
        raw = b'BM6\x00' + bytes(header) + bytes(g.randrange(256) for _ in range(3 * width * height))
        client.file, client.cursor = raw, 0
        client.crt_allowed = {CRT_FSEEK, CRT_FREAD}
        target = G['light_map']
        uc.mem_write(target, POISON * (12 * CELLS))
        ok, _ = region(client, 0x0185b366, 0x0185b458, {-4: 0x51e0f11e, 0xc: target}, 0x360)
        status, mine = authored.light(raw)
        got = bytes(uc.mem_read(target, 12 * CELLS))
        n = 12 * width * height
        cases += 1
        matches += int(ok and status == 0 and bits_of(got[:n]) == [fbits(x) for x in mine] and
                       got[n:] == POISON * (12 * CELLS - n))
    report['light_bmp'] = {'cases': cases, 'matches': matches}

    # Attribute tail 0x016c9faf..0x016ca15f after decryption (key at 0x01cf0448 modelled)
    cases = matches = 0
    good = bytes([0, 7, 255, 255]) + b''.join(struct.pack('<H', g.choice((0, 4, 8, 0x40, 0x7f, 0x500, 0x4000,
                                                                          0xff7f))) for _ in range(CELLS))
    bad = bytearray(good)
    bad[4 + 2 * 1234] = 0x80
    plains = [good, bytes([0, 3, 255, 255]) + bytes(g.choice((0, 1, 4, 8, 0x7f)) for _ in range(CELLS)),
              bytes([1]) + good[1:], bytes(bad), good[:3] + b'\xfe' + good[4:], good[:0x10004]]
    for plain in plains:
        encrypted = py_xor3(plain)
        uc.mem_write(G['key'], KEY)
        uc.mem_write(big, encrypted)
        uc.mem_write(G['att'], POISON * (2 * CELLS))
        client.crt_allowed, client.crt_calls = {CRT_FREE, CRT_FCLOSE, ERROR_BOX}, []
        ok, eax = region(client, 0x016c9faf, 0x016ca15f, {-8: big, -0x18: len(plain), -0x14: 0x51e0f11e}, 0x10160)
        status, number, att = authored.parse_attributes(encrypted)
        client_status = 2 if eax == 0xffffffff else 0
        same = (ok and status == client_status and client.read('att', 'H', CELLS) == att and
                (status != 0 or eax == number) and (hex(ERROR_BOX) in client.crt_calls) == (status == 2))
        cases += 1
        matches += int(same)
    report['attributes'] = {'cases': cases, 'matches': matches}

    # Map tail 0x016c9adf..0x016c9b8b
    plain = bytes(g.randrange(256) for _ in range(2 + 3 * CELLS))
    uc.mem_write(big, plain)
    for name, size in (('layer1', CELLS), ('layer2', CELLS), ('alpha', 4 * CELLS)):
        uc.mem_write(G[name], POISON * size)
    ok, _ = region(client, 0x016c9adf, 0x016c9b8b, {-0x14: big}, 0x50)
    number = struct.unpack('<I', uc.mem_read(client.STACK + 0x3e000 - 0x48, 4))[0]
    status, mine_number, l1, l2, alpha = authored.parse_map(plain)
    report['map'] = {'cases': 1, 'matches': int(ok and status == 0 and number == mine_number and
                                              bytes(uc.mem_read(G['layer1'], CELLS)) == l1 and
                                              bytes(uc.mem_read(G['layer2'], CELLS)) == l2 and
                                              compare_lists(client.read('alpha', 'f', CELLS), alpha))}

    # Per-frame update 0x016ca4fa: light copy + wave grids (CRT sin, SSE2 path)
    cases = matches = 0
    details = []
    for world, time, alternate, box in ((0, 123456.7, 0, (0, 0, 248, 248)), (142, 98765.25, 0, (40, 60, 120, 200)),
                                        (8, 7777777.0, 1, (100, 4, 251, 251)), (0x50, 5000.5, 0, (0, 0, 251, 251)),
                                        (0x39, 31.0, 0, (12, 12, 60, 60)), (0x6e, 4.0e6, 1, (0, 200, 251, 251)),
                                        (141, 2.5e6, 0, (8, 8, 248, 248)), (0, 0.0, 0, (0, 0, 251, 251))):
        primary = [f32(g.random()) for _ in range(3 * CELLS)]
        wave0 = [f32(g.uniform(-9, 9)) for _ in range(CELLS)]
        wave20 = [f32(g.uniform(-9, 9)) for _ in range(CELLS)]
        client.write('world', 'i', [world])
        client.write('primary', 'f', primary)
        uc.mem_write(G['light'], POISON * (12 * CELLS))
        client.write('wave', 'f', wave0)
        client.write('wave2', 'f', wave20)
        client.write('time', 'f', [time])
        uc.mem_write(ALTERNATE, struct.pack('<I', alternate))
        for name, value in zip(('xmin', 'ymin', 'xmax', 'ymax'), box):
            client.write(name, 'i', [value])
        ok = client.call(WAVE, [])
        mine_wave, mine_wave2 = floats(wave0), floats(wave20)
        authored.lib.mu_terrain_wave.argtypes = [ctypes.c_int32, ctypes.c_float, ctypes.c_int, ctypes.c_int32,
                                                 ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, VOIDP, VOIDP]
        authored.lib.mu_terrain_wave(world, time, alternate, *box, mine_wave, mine_wave2)
        poison = (ctypes.c_float * (3 * CELLS)).from_buffer_copy(POISON * (12 * CELLS))
        authored.lib.mu_terrain_frame_light(floats(primary), poison, *box)   # authored copy rule
        expected_light = bytes(poison)
        primary_bytes = struct.pack(f'<{3 * CELLS}f', *primary)
        python_light = bytearray(POISON * (12 * CELLS))
        for y in range(box[1], box[3] + 4):
            for x in range(box[0], box[2] + 4):
                i = index_repeat(x, y)
                python_light[12 * i:12 * i + 12] = primary_bytes[12 * i:12 * i + 12]
        assert bytes(python_light) == expected_light
        w_ok = compare_lists(client.read('wave', 'f', CELLS), list(mine_wave))
        w2_ok = compare_lists(client.read('wave2', 'f', CELLS), list(mine_wave2))
        l_ok = bytes(uc.mem_read(G['light'], 12 * CELLS)) == bytes(expected_light)
        cases += 1
        matches += int(ok and w_ok and w2_ok and l_ok)
        details.append({'world': world, 'ok': ok, 'wave': w_ok, 'wave2': w2_ok, 'light_copy': l_ok,
                        'error': client.error})
    report['frame_update'] = {'cases': cases, 'matches': matches, 'details': details}
    report['loader_substitutions'] = ['CRT fseek 0x01989dab / fread 0x01989230 (light loop)',
                                      'free 0x0191bac2, fclose 0x01988c95, error box 0x016cef3f (attribute tail)',
                                      'XOR key bytes at 0x01cf0448 (uncaptured): fc cf ab']


# --------------------------------------------------------------------------
# NATIVE-TERRAIN-002: height handler table, dynamic lights, world tiles,
# frustum, decals.

HEIGHT_SELECTOR, HANDLER_GETTER, WORLD_MANAGER = 0x016c9868, 0x00d5cbe3, 0x01ec91b8
# Handler classes registered by 0x00ea488e: world -> constructor (the function that stores the class vtable
# after the base constructor 0x00d5c99f). Literal 24-bit worlds 0x7a..0x85 never reach the handler.
HANDLER_CTORS = {0x39: 0x00e9ee7a, 0x3a: 0x00e9ee7a, 0x3e: 0x00e42f50, 0x3f: 0x00e93073, 0x40: 0x00dc6bdd,
                 0x45: 0x00dd3866, 0x46: 0x00dd8960, 0x47: 0x00dde612, 0x48: 0x00de54fc, 0x4f: 0x00e6ecaf,
                 0x50: 0x00e1399d, 0x51: 0x00e1399d, 0x52: 0x00e30672, 0x5b: 0x00d6a5f7, 0x5c: 0x00d7a126,
                 0x60: 0x00d7a126, 0x65: 0x00d7a126, 0x6f: 0x00d7a126, 0x5d: 0x00daa127, 0x5e: 0x00e24976,
                 0x5f: 0x00dbd130, 0x64: 0x00e6ef95, 0x6e: 0x00e26010, 0x70: 0x00de57f4, 0x71: 0x00e343cc,
                 0x72: 0x00e203f9, 0x73: 0x00e22373, 0x74: 0x00e3dfec, 0x75: 0x00e3ec82, 0x76: 0x00e3f93a,
                 0x77: 0x00e40651, 0x78: 0x00e4134d, 0x79: 0x00d584f1, 0x7a: 0x00e5430b, 0x7b: 0x00e18da5,
                 0x83: 0x00e43236, 0x84: 0x00e00b07, 0x85: 0x00d807bd, 0x86: 0x00d83d84, 0x87: 0x00e3a2b7,
                 0x88: 0x00d93567, 0x89: 0x00e08c06, 0x8a: 0x00e05835, 0x8b: 0x00d9c03a, 0x8c: 0x00d99f1c,
                 0x8d: 0x00e4be37, 0x8e: 0x00e66fb8, 0x8f: 0x00e0e1ad, 0x90: 0x00e45fea, 0x91: 0x00d75255}
for _w in range(0x7c, 0x80):
    HANDLER_CTORS[_w] = 0x00e18da5
ADD_LIGHT, FRUSTUM, FRUSTUM_3D_STOP, FRUSTUM_2D, TEST_2D, DECAL = (0x016cacfc, 0x016cba24, 0x016cc48f, 0x016d20d9,
                                                                   0x016ccce7, 0x016cdd5f)
CAMERA_POSITION, CAMERA_ANGLE, VIEW_FAR, FOV = 0x0bdc5ab4, 0x0bdc58f0, 0x01cf1630, 0x01cf1634
F_VERTEX, F_NORMAL, F_D, F_X2D, F_Y2D = 0x0bdb5430, 0x0bdb546c, 0x0b6b53e4, 0x0b6b5400, 0x0b6b5410
SCENE_STATE, ZOOM_MODE = 0x01d1df70, 0x0bdb5880
SPECIAL_WORLDS = (0x1e, 0x5e, 0x7a, 0x8d, 0x22, 0x3f, 0x52, 0x56, 0x64, 0x65, 0x6e, 0x6f, 0x70, 0x8a, 0x8c, 7, 0x80,
                  0x82, 0x85, 0x27, 0x62, 0x2d, 0x30, 0x33, 0x45, 0x4a, 0x50, 0x51, 0x5b, 0x5c, 0x71, 0x91, 0x12,
                  0x35, 0, 142)


def ret_with(value, argument_bytes=0):
    return lambda client: client.ret(value & 0xffffffff, argument_bytes)


def mat_rows_to_gl(rows12):
    """3x4 row-major rotation (rows 0..2) -> column-major glGetFloatv layout."""
    gl = [0.0] * 16
    for i in range(3):
        for j in range(4):
            gl[4 * j + i] = rows12[4 * i + j]
    gl[15] = 1.0
    return gl


def random_rotation(g):
    """A modelview-like 3x4: rotation about z then x (camera pitch/yaw) and a translation."""
    yaw, pitch = math.radians(g.uniform(-180, 180)), math.radians(g.uniform(-80, -10))
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    rz = [[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]
    rx = [[1, 0, 0], [0, cp, -sp], [0, sp, cp]]
    m = [[sum(rx[i][k] * rz[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return [f32(m[0][0]), f32(m[0][1]), f32(m[0][2]), f32(g.uniform(-5000, 5000)),
            f32(m[1][0]), f32(m[1][1]), f32(m[1][2]), f32(g.uniform(-5000, 5000)),
            f32(m[2][0]), f32(m[2][1]), f32(m[2][2]), f32(g.uniform(-30000, 0))]


def terrain2_checks(client, authored, report, g, scale=1):
    uc = client.uc
    out = {}

    # (1) 24-bit height choice: build each registered handler by running its constructor, install it as the
    # manager's current handler as OpenWorld's 0x00ea468f would, then run the selector 0x016c9868 itself.
    manager, handlers = client.OBJECTS + 0x9000, {}
    uc.mem_write(WORLD_MANAGER, struct.pack('<I', manager))
    # Two imports some handler members call while constructing (stubbed, labelled):
    # QueryPerformanceFrequency / QueryPerformanceCounter (slots 0x01a7c214 / 0x01a7c210) and RtlAllocateHeap (slot 0x01a7c5c8, bump allocator).
    from unicorn import UC_HOOK_CODE
    qpf_stub, alloc_stub, heap = client.OBJECTS + 0xff00, client.OBJECTS + 0xff10, [client.OBJECTS + 0xc000]
    uc.mem_write(qpf_stub, b'\xc2\x04\x00')
    uc.mem_write(alloc_stub, b'\xc2\x0c\x00')
    uc.mem_write(0x01a7c214, struct.pack('<I', qpf_stub))
    uc.mem_write(0x01a7c210, struct.pack('<I', qpf_stub))   # QueryPerformanceCounter: same shape
    uc.mem_write(0x01a7c5c8, struct.pack('<I', alloc_stub))

    def on_import(uc_, address, size, ignored):
        if address == qpf_stub:
            uc_.mem_write(client.arg(0), struct.pack('<Q', 10000000))
            uc_.reg_write(client.x86.UC_X86_REG_EAX, 1)
        else:
            size_ = (client.arg(2) + 15) & ~15
            uc_.mem_write(heap[0], b'\0' * size_)
            uc_.reg_write(client.x86.UC_X86_REG_EAX, heap[0])
            heap[0] += size_
    uc.hook_add(UC_HOOK_CODE, on_import, begin=qpf_stub, end=alloc_stub)
    # CRT int64 -> double helper 0x0191c350 takes its AVX-512 path unless bit 0x20 of [0x01cf6610] is set
    # (the CPU-feature word is uncaptured BSS); select the SSE2 path.
    uc.mem_write(0x01cf6610, bytes([uc.mem_read(0x01cf6610, 1)[0] | 0x20]))
    built = ok_ctors = 0
    for slot, ctor in enumerate(sorted(set(HANDLER_CTORS.values()))):
        obj = client.OBJECTS + 0xa000 + 0x80 * slot
        uc.mem_write(obj, b'\xa5' * 0x80)
        ok = client.call(ctor, [], ecx=obj)
        built += 1
        ok_ctors += int(ok)
        handlers[ctor] = (obj, ok, bytes(uc.mem_read(obj + 4, 3)), struct.unpack('<I', uc.mem_read(obj, 4))[0],
                          client.error)
    cases = matches = 0
    flags, mismatches = {}, []
    for world in range(0x100):
        ctor = HANDLER_CTORS.get(world)
        obj = handlers[ctor][0] if ctor else 0
        uc.mem_write(manager + 0x10, struct.pack('<I', obj))
        client.write('world', 'i', [world])
        ok = client.call(HEIGHT_SELECTOR, [world])
        got = client.uc.reg_read(client.x86.UC_X86_REG_EAX) & 0xff
        mine, unresolved = authored.height_is_rgb(world)
        cases += 1
        same = ok and got == mine and unresolved == 0
        matches += int(same)
        if got:
            flags.setdefault('rgb', []).append(world)
        if not same:
            mismatches.append([world, ok, got, mine])
    literal_only = sum(1 for w_ in range(0x100) if (w_ in flags.get('rgb', [])) !=
                       bool(py_height_is_rgb(w_) and not 0x86 <= w_ <= 0x91))
    out['height_choice'] = {'cases': cases, 'matches': matches,
                            'python_model_equal': sum(1 for w_ in range(0x100) if (w_ in flags.get('rgb', [])) ==
                                                      bool(py_height_is_rgb(w_))),
                            'negative_control_literal_only_differs': literal_only, 'constructors_run': [built, ok_ctors],
                            'rgb_worlds': flags.get('rgb', []), 'mismatches': mismatches[:8],
                            'handler_flag_bytes': {hex(c): v[2].hex() for c, v in sorted(handlers.items())},
                            'constructor_errors': {hex(c): v[4] for c, v in sorted(handlers.items()) if not v[1]}}

    # (2) AddTerrainLight 0x016cacfc on synthetic buffers.
    cases = matches = 0
    buffer_address = G['light']
    for case in range(160 * scale):
        base = [f32(g.uniform(-0.5, 1.5)) for _ in range(3 * CELLS)] if case % 8 == 0 else None
        if base is None:
            base = list(struct.unpack(f'<{3 * CELLS}f', bytes(uc.mem_read(buffer_address, 12 * CELLS))))
            if case == 1:
                base = [f32(g.random()) for _ in range(3 * CELLS)]
        uc.mem_write(buffer_address, struct.pack(f'<{3 * CELLS}f', *base))
        x = f32(g.choice([g.uniform(-300, 25900), g.uniform(0, 200), 12850.0, -1.0e9, 25555.5]))
        y = f32(g.choice([g.uniform(-300, 25900), g.uniform(25300, 25700), 64.0]))
        light = [f32(g.uniform(-1.0, 2.0)) for _ in range(3)]
        light_range = g.choice([0, 1, 1, 1, 2, 3, 4, 6, -1])
        uc.mem_write(client.CONFIG + 0x400, struct.pack('<3f', *light))
        ok = client.call(ADD_LIGHT, [fbits(x), fbits(y), client.CONFIG + 0x400, light_range, buffer_address])
        got = bytes(uc.mem_read(buffer_address, 12 * CELLS))
        mine = authored.add_light(x, y, light, light_range, base)
        cases += 1
        matches += int(ok and got == struct.pack(f'<{3 * CELLS}f', *mine))
    out['add_light'] = {'cases': cases, 'matches': matches}
    # Negative controls: an upper clamp at 1 or no lower clamp must disagree with the client somewhere.
    differ = {'clamp1': 0, 'noclamp': 0, 'python_model': 0}
    for case in range(40 * scale):
        base = [f32(g.uniform(-0.5, 1.5)) for _ in range(3 * CELLS)]
        x, y = f32(g.uniform(500, 25000)), f32(g.uniform(500, 25000))
        light = [f32(g.uniform(-1.5, 2.5)) for _ in range(3)]
        light_range = g.choice([1, 2, 4])
        uc.mem_write(buffer_address, struct.pack(f'<{3 * CELLS}f', *base))
        uc.mem_write(client.CONFIG + 0x400, struct.pack('<3f', *light))
        client.call(ADD_LIGHT, [fbits(x), fbits(y), client.CONFIG + 0x400, light_range, buffer_address])
        got = bytes(uc.mem_read(buffer_address, 12 * CELLS))
        for variant in (None, 'clamp1', 'noclamp'):
            model = struct.pack(f'<{3 * CELLS}f', *py_add_light(x, y, light, light_range, base, variant))
            if variant is None:
                differ['python_model'] += int(model == got)
            else:
                differ[variant] += int(model != got)
    out['add_light']['negative_controls'] = {'cases': 40, 'clamp1_differs': differ['clamp1'],
                                             'noclamp_differs': differ['noclamp'],
                                             'python_model_equal': differ['python_model']}

    # (3) Tile streams of the world-specific branches (extended synthetic scenes).
    rand_state = [12345]

    def crt_rand():
        rand_state[0] = (rand_state[0] * 214013 + 2531011) & 0xffffffff
        return (rand_state[0] >> 16) & 0x7fff
    streams = {'cases': 0, 'matches': 0, 'unsupported': 0, 'calls': 0, 'effects': 0, 'per_world': {}}
    particles = []
    client.extra = {CRT_RAND: lambda c: c.ret(crt_rand(), 0),
                    PARTICLE: lambda c: (particles.append(('effect', c.arg(0)) + c.read_floats(c.arg(1), 3)),
                                         c.ret(0, 0)),
                    CHAOS_EFFECTS: ret_with(0)}
    # seeds whose first rand() % 50 == 0, so world 0x22's water tiles spawn particles
    particle_seeds = [v for v in range(200000) if ((((v * 214013 + 2531011) & 0xffffffff) >> 16) & 0x7fff) % 50 == 0][:40]
    for seed, world in enumerate(SPECIAL_WORLDS):
        scene = synthetic_scene(500 + seed, world, extended=True)
        if world == 0x22:   # mostly water on layer 1
            scene['layer1'] = bytes(5 if i % 3 else b for i, b in enumerate(scene['layer1']))
        client.load_scene(scene)
        mine_rand = [12345]

        def authored_rand():
            mine_rand[0] = (mine_rand[0] * 214013 + 2531011) & 0xffffffff
            return (mine_rand[0] >> 16) & 0x7fff
        scene['random'] = authored_rand
        built_scene = authored.scene(scene)
        effects = scene['effects_out']
        per = streams['per_world'].setdefault(hex(world), [0, 0, 0])
        for case in range(120 * scale):
            xi, yi = g.randrange(1, 254), g.randrange(1, 254)
            detail = 4 if case % 2 else 0
            client.uc.mem_write(client.CONFIG + 0x2c, struct.pack('<i', detail))
            built_scene[0].detail = detail
            seed_value = particle_seeds[case % len(particle_seeds)] if world == 0x22 else 777 + case
            for pass_ in (0, 2):
                rand_state[0] = mine_rand[0] = seed_value
                del particles[:]
                del effects[:]
                client.write('pass_', 'i', [pass_])
                ok = client.call(TILE, [fbits(float(xi)), fbits(float(yi)), xi, yi, fbits(1.0), 1, 0])
                status, expected = authored.draw_tile(built_scene, pass_, float(xi), float(yi), xi, yi)
                streams['cases'] += 1
                per[0] += 1
                if status == 4:
                    streams['unsupported'] += 1
                    per[2] += 1
                    continue
                client_effects = [tuple(e[:2]) + tuple(e[2:]) for e in particles]
                same = ok and client.stream == expected and client_effects == list(effects)
                streams['matches'] += int(same)
                streams['effects'] += len(effects)
                per[1] += int(same)
                streams['calls'] += len(expected)
                if not same and 'first_mismatch' not in streams:
                    diff = next((i for i, (a, b) in enumerate(zip(client.stream, expected)) if a != b),
                                min(len(client.stream), len(expected)))
                    streams['first_mismatch'] = {'world': world, 'tile': [xi, yi], 'pass': pass_, 'ok': ok,
                                                 'error': client.error, 'at': diff,
                                                 'client': client.stream[max(0, diff - 2):diff + 6],
                                                 'authored': expected[max(0, diff - 2):diff + 6],
                                                 'effects': [client_effects, list(effects)]}
    client.extra = {}
    streams['gl_color3f_calls'] = getattr(client, 'color3f', 0)
    # Python model of the world rules and two negative controls on the same client streams.
    client.extra = {CHAOS_EFFECTS: ret_with(0)}
    neg = {'python_model_equal': 0, 'compared': 0, 'generic_scroll_differs': 0, 'generic_blend_differs': 0}
    for world, wrong in ((0x1e, 0), (0x8d, 0), (0x70, 0), (0x33, 0), (0x5b, 0), (7, 0), (0x3f, 0)):
        scene = synthetic_scene(900 + world, world, extended=True)
        client.load_scene(scene)
        for case in range(60 * scale):
            xi, yi = g.randrange(1, 254), g.randrange(1, 254)
            client.write('pass_', 'i', [0])
            ok = client.call(TILE, [fbits(float(xi)), fbits(float(yi)), xi, yi, fbits(1.0), 1, 0])
            model = []
            if py_draw_tile(scene, 0, float(xi), float(yi), xi, yi, model) == 4:
                continue
            neg['compared'] += 1
            neg['python_model_equal'] += int(ok and model == client.stream)
            other = dict(scene, world=wrong)
            perturbed = []
            py_draw_tile(other, 0, float(xi), float(yi), xi, yi, perturbed)
            key = 'generic_blend_differs' if world in (0x33, 0x5b) else 'generic_scroll_differs'
            neg[key] += int(perturbed != client.stream)
    client.extra = {}
    streams['model_and_negative_controls'] = neg
    out['world_tile_streams'] = streams

    # (4) CreateFrustrum 0x016cba24, 3D part (up to its CreateFrustrum2D call).
    cases = matches = 0
    frustums = []
    for case in range(40 * scale):
        rows = random_rotation(g)
        client.modelview = mat_rows_to_gl(rows)
        aspect = f32(g.choice([1.0, 1728 / 640.0, 1280 / 640.0, g.uniform(0.5, 4.0)]))
        view_far = f32(g.choice([2000.0, 2400.0, 3700.0, g.uniform(500, 8000)]))
        fov = f32(g.choice([30.0, 35.0, 45.0, g.uniform(10, 90)]))
        position = [f32(g.uniform(-2000, 27000)), f32(g.uniform(-2000, 27000)), f32(g.uniform(0, 3000))]
        uc.mem_write(VIEW_FAR, struct.pack('<2f', view_far, fov))
        uc.mem_write(CAMERA_POSITION, struct.pack('<3f', *position))
        ok = client.call(FRUSTUM, [fbits(aspect), client.CONFIG + 0x500, 0], until=FRUSTUM_3D_STOP)
        got_v = struct.unpack('<15I', uc.mem_read(F_VERTEX, 60))
        got_n = struct.unpack('<15I', uc.mem_read(F_NORMAL, 60))
        got_d = struct.unpack('<5I', uc.mem_read(F_D, 20))
        got_box = [client.read(n, 'i', 1)[0] for n in ('xmin', 'ymin', 'xmax', 'ymax')]
        f = authored.frustum_create(aspect, view_far, fov, rows, position)
        same = (ok and got_v == tuple(fbits(v) for v in f.vertex) and got_n == tuple(fbits(v) for v in f.normal) and
                got_d == tuple(fbits(v) for v in f.d) and got_box == [f.x_min, f.y_min, f.x_max, f.y_max])
        cases += 1
        matches += int(same)
        frustums.append(f)
        if not same and 'first_mismatch' not in out.setdefault('frustum_3d', {}):
            out['frustum_3d']['first_mismatch'] = {'ok': ok, 'error': client.error, 'box': [got_box, [
                f.x_min, f.y_min, f.x_max, f.y_max]], 'v': [got_v[:6], [fbits(v) for v in f.vertex][:6]]}
    out.setdefault('frustum_3d', {}).update({'cases': cases, 'matches': matches})

    # (5) CreateFrustrum2D 0x016d20d9 (camera singleton and screen width substituted).
    camera, sub = client.OBJECTS + 0x8000, client.OBJECTS + 0x8100
    cases = matches = 0
    for case in range(60 * scale):
        world = g.choice([0, 2, 0x3f, 0x8b, 0x86, 142, 0x22, 80])
        mode = g.choice([0, 1, 2, 3, 4, 5])
        width = g.choice([640, 800, 1024, 1280, 1728, 1920])
        k1c, k18, k10 = (f32(g.choice([1.0, g.uniform(0.5, 1.5)])) for _ in range(3))
        fov = f32(35.0)
        uc.mem_write(camera, b'\0' * 0x100)
        uc.mem_write(camera + 0xc, struct.pack('<I', sub))
        uc.mem_write(camera + 0x10, struct.pack('<f', k10))
        uc.mem_write(sub, b'\0' * 0x100)
        uc.mem_write(sub + 0x18, struct.pack('<3f', k18, k1c, fov))
        uc.mem_write(FOV, struct.pack('<f', fov))
        client.write('world', 'i', [world])
        uc.mem_write(SCENE_STATE, struct.pack('<i', 5))
        uc.mem_write(ZOOM_MODE, struct.pack('<i', mode))
        uc.mem_write(0x01cf1860, struct.pack('<f', 0.0))
        uc.mem_write(0x0bdc5ef0, struct.pack('<f', 1.0))
        angle = [f32(g.uniform(-90, 0)), 0.0, f32(-45.0)]
        uc.mem_write(CAMERA_ANGLE, struct.pack('<3f', *angle))
        position = [f32(g.uniform(0, 25600)), f32(g.uniform(0, 25600)), f32(g.uniform(0, 1000))]
        uc.mem_write(client.CONFIG + 0x500, struct.pack('<3f', *position))
        wide = g.choice([0, 0, 1])
        client.extra = {CAMERA_SINGLETON: ret_with(camera), SCREEN_WIDTH: ret_with(width)}
        uc.mem_write(F_X2D, b'\0' * 32)
        ok = client.call(FRUSTUM_2D, [client.CONFIG + 0x500, wide])
        client.extra = {}
        got = struct.unpack('<8I', uc.mem_read(F_X2D, 32))
        zoom = fdiv(f32(float(width)), 640.0)
        cam_scale = fmul(fmul(fmul(zoom, k1c), k18), k10)
        distance = fmul(fmul(fmul(2400.0, k1c), k18), k10)
        _, params = authored.params_2d(world, mode, width, cam_scale, distance)
        status, x2d, y2d = authored.frustum_2d(world, position, angle, params, wide)
        cases += 1
        same = ok and status == 0 and got == tuple(fbits(v) for v in x2d + y2d)
        matches += int(same)
        if not same and 'first_mismatch' not in out.setdefault('frustum_2d', {}):
            out['frustum_2d']['first_mismatch'] = {'world': world, 'mode': mode, 'ok': ok, 'error': client.error,
                                                   'client': got, 'authored': [fbits(v) for v in x2d + y2d]}
    out.setdefault('frustum_2d', {}).update({'cases': cases, 'matches': matches})

    # (6) TestFrustrum2D 0x016ccce7 (and its Python model; negative control: the range with the wrong sign).
    cases = matches = model_equal = flipped = 0
    for case in range(3000 * scale):
        if case % 500 == 0:
            xs = [f32(g.uniform(0, 256)) for _ in range(4)]
            ys = [f32(g.uniform(0, 256)) for _ in range(4)]
            uc.mem_write(F_X2D, struct.pack('<4f', *xs) + struct.pack('<4f', *ys))
            state = g.choice([0, 1, 4, 5, 5, 5])
            uc.mem_write(SCENE_STATE, struct.pack('<i', state))
        x, y = f32(g.uniform(-10, 266)), f32(g.uniform(-10, 266))
        r = g.choice([0.0, -80.0, f32(g.uniform(-200, 200))])
        ok = client.call(TEST_2D, [fbits(x), fbits(y), fbits(r)])
        got = client.uc.reg_read(client.x86.UC_X86_REG_EAX) & 0xff
        mine = authored.lib.mu_terrain_test_frustum_2d(floats(xs), floats(ys), state, x, y, r)
        cases += 1
        matches += int(ok and got == mine)
        model_equal += int(got == py_test_frustum_2d(xs, ys, state, x, y, r))
        flipped += int(state == 5 and got != py_test_frustum_2d(xs, ys, 5, x, y, -r))
    out['test_frustum_2d'] = {'cases': cases, 'matches': matches, 'python_model_equal': model_equal,
                              'negative_control_range_sign_differs': flipped}

    # (7) RenderTerrain 0x016cd468 with the frustum tests live (top view off, main scene).
    cases = matches = 0
    for case in range(4 * scale):
        scene = synthetic_scene(700 + case, g.choice([0, 142, 7, 0x3f]), extended=True)
        client.load_scene(scene)
        cx, cy = g.uniform(20, 230), g.uniform(20, 230)
        f = Frustum()
        f.x_min, f.y_min = max(0, int(cx) - 12) & ~3, max(0, int(cy) - 12) & ~3
        f.x_max, f.y_max = min(251, f.x_min + 20), min(251, f.y_min + 20)
        poly = [(cx - 9, cy + 8), (cx + 9, cy + 8), (cx + 3, cy - 6), (cx - 3, cy - 6)]
        for i, (px, py) in enumerate(poly):
            f.x2d[i], f.y2d[i] = f32(px), f32(py)
        for name, value in zip(('xmin', 'ymin', 'xmax', 'ymax'), (f.x_min, f.y_min, f.x_max, f.y_max)):
            client.write(name, 'i', [value])
        uc.mem_write(F_X2D, struct.pack('<4f', *f.x2d) + struct.pack('<4f', *f.y2d))
        uc.mem_write(SCENE_STATE, struct.pack('<i', 5))
        uc.mem_write(G['force'], b'\0')
        uc.mem_write(G['alpha_flag'], b'\1')
        client.extra = {CHAOS_EFFECTS: ret_with(0)}
        ok = client.call(RENDER, [0], until=RENDER_STOP)
        client.extra = {}
        water = struct.unpack('<I', uc.mem_read(WATER_MOVE, 4))[0]
        status, expected = authored.render(authored.scene(scene), f, 5, 0, 1)
        cases += 1
        same = (ok and client.stream == expected and
                water == fbits(authored.lib.mu_terrain_water_move(scene['world'], scene['time'])))
        matches += int(same)
        out.setdefault('render_frustum', {}).setdefault('calls', []).append(len(expected))
        if not same and 'first_mismatch' not in out['render_frustum']:
            diff = next((i for i, (a, b) in enumerate(zip(client.stream, expected)) if a != b),
                        min(len(client.stream), len(expected)))
            out['render_frustum']['first_mismatch'] = {'ok': ok, 'error': client.error, 'at': diff,
                                                       'client': client.stream[diff:diff + 4],
                                                       'authored': expected[diff:diff + 4],
                                                       'lengths': [len(client.stream), len(expected)]}
    out['render_frustum'].update({'cases': cases, 'matches': matches})

    # (8) RenderTerrainAlphaBitmap 0x016cdd5f (decals).
    cases = matches = fans = 0
    for case in range(60 * scale):
        world = g.choice([0, 142, 0x8d])
        scene = synthetic_scene(800 + case % 3, world, extended=True)
        if case % 3 == 0:
            client.load_scene(scene)
            built_scene = authored.scene(scene)
        x, y = f32(g.uniform(-200, 25800)), f32(g.uniform(-200, 25800))
        sx, sy = f32(g.choice([1.0, 2.0, 3.5, g.uniform(0.3, 6)])), f32(g.choice([1.0, 2.0, g.uniform(0.3, 6)]))
        light = [f32(g.random()) for _ in range(3)]
        rotation = f32(g.choice([0.0, 45.0, g.uniform(-360, 360)]))
        alpha = f32(g.choice([1.0, 0.5, g.random()]))
        height = f32(g.choice([0.0, 5.0, g.uniform(-50, 300)]))
        follow, flip = g.choice([0, 1, 1]), g.choice([0, 0, 1])
        uc.mem_write(client.CONFIG + 0x600, struct.pack('<3f', *light))
        texture = g.choice([0x7630, 0x7631, 0x7694])
        ok = client.call(DECAL, [texture, fbits(x), fbits(y), fbits(sx), fbits(sy), client.CONFIG + 0x600,
                                 fbits(rotation), fbits(alpha), fbits(height), follow, flip])
        count, expected = authored.decal(built_scene, texture, x, y, sx, sy, light, rotation, alpha, height,
                                         follow, flip)
        cases += 1
        fans += count
        same = ok and client.stream == expected
        matches += int(same)
        if not same and 'first_mismatch' not in out.setdefault('decal', {}):
            diff = next((i for i, (a, b) in enumerate(zip(client.stream, expected)) if a != b),
                        min(len(client.stream), len(expected)))
            out['decal']['first_mismatch'] = {'ok': ok, 'error': client.error, 'at': diff,
                                              'client': client.stream[diff:diff + 4],
                                              'authored': expected[diff:diff + 4],
                                              'lengths': [len(client.stream), len(expected)]}
    out.setdefault('decal', {}).update({'cases': cases, 'matches': matches, 'fans': fans})
    out['substitutions'] = ['QueryPerformanceFrequency / QueryPerformanceCounter / RtlAllocateHeap imports while running handler constructors',
                            'CRT rand 0x01989721 (MSVC recurrence, fixed seed per case) and CreateParticle '
                            '0x0168fafd (arguments recorded) in the world-0x22 water tiles',
                            'Chaos Castle per-face effects 0x009dc0b1 (returns at once)',
                            'camera singleton 0x0098647b (synthetic camera object) and screen width 0x016bc355 '
                            'in CreateFrustrum2D',
                            'glGetFloatv(GL_MODELVIEW_MATRIX) returns the case matrix',
                            'glColor3f recorded like glColor3fv']
    report.update(out)


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
            if unresolved:  # the runtime world object decides; the viewer goes by the file length
                rgb = len(raw) >= 58 + 3 * CELLS
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
    # Client loops on every installed height, light map, attribute and map file.
    out['client_loops'] = installed_loops(client, authored, data, worlds)
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
        time = 123456.5
        wave, wave2 = floats([0.0] * CELLS), floats([0.0] * CELLS)
        authored.lib.mu_terrain_wave.argtypes = [ctypes.c_int32, ctypes.c_float, ctypes.c_int, ctypes.c_int32,
                                                 ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, VOIDP, VOIDP]
        authored.lib.mu_terrain_wave(world, time, 0, 0, 0, 255, 255, wave, wave2)
        rng = random.Random(number)
        scene = {'world': world, 'layer1': entry['layer1'], 'layer2': entry['layer2'], 'alpha': entry['alpha'],
                 'att': entry['att'], 'height': entry['height'], 'light': primary, 'light2': [0.0] * (3 * CELLS),
                 'wave': list(wave), 'wave2': list(wave2),
                 'grass_offset': [(rng.randrange(32768) % 4) / 4.0 for _ in range(CELLS)],
                 'grass_map': bytes([1]) * CELLS, 'water': 0.0, 'time': time, 'detail': 0, 'grass_disabled': 0,
                 'sizes': tool_sizes(args.game_root, world) or installed_sizes(data / f'World{number}'),
                 'frame_counter': 7, 'hero_z': 150.0}
        client.load_scene(scene)
        built = authored.scene(scene)
        client.extra = {CHAOS_EFFECTS: ret_with(0)}
        g = random.Random(number)
        tiles = matches = unsupported = 0
        if args.installed_tiles <= 0:
            coordinates = [(x, y) for y in range(255) for x in range(255)]
        else:
            coordinates = [(g.randrange(255), g.randrange(255)) for _ in range(args.installed_tiles)]
        for xi, yi in coordinates:
            detail = 4 if (xi + yi) % 2 else 0   # graphics option >= 4 on half the tiles (0x4000 neighbour faces)
            client.uc.mem_write(client.CONFIG + 0x2c, struct.pack('<i', detail))
            built[0].detail = detail
            for pass_ in (0, 2):
                client.write('pass_', 'i', [pass_])
                ok = client.call(TILE, [fbits(float(xi)), fbits(float(yi)), xi, yi, fbits(1.0), 1, 0])
                status, expected = authored.draw_tile(built, pass_, float(xi), float(yi), xi, yi)
                if status == 4:
                    unsupported += 1
                    continue
                tiles += 1
                matches += int(ok and client.stream == expected)
        client.extra = {}
        result['tile_streams'] = {'cases': tiles, 'matches': matches, 'unsupported': unsupported,
                                  'bitmaps': len(scene['sizes'])}
        out['compared'][str(number)] = result
    return out


def installed_loops(client, authored, data, worlds):
    install_crt(client) if not hasattr(client, 'crt_allowed') else None
    uc, big = client.uc, WINDOW_AT
    result = {'height_bytes': [0, 0], 'height_rgb': [0, 0], 'light_bmp': [0, 0], 'attributes': [0, 0],
              'map': [0, 0], 'failures': []}
    for number in worlds:
        folder = data / f'World{number}'
        for path in sorted(folder.iterdir()):
            name, raw = path.name.lower(), None
            if name == 'terrainheight.ozb':
                raw = path.read_bytes()
                if len(raw) >= 58 + 3 * CELLS:
                    key = 'height_rgb'
                    uc.mem_write(big, raw)
                    uc.mem_write(G['height'], POISON * (4 * CELLS))
                    ok, _ = region(client, 0x016c8843, 0x016c8958, {-0x14: big, -0x20: len(raw)}, 0x280)
                    status, mine = authored.height_rgb(raw)
                else:
                    key = 'height_bytes'
                    uc.mem_write(big, raw[4:4 + 0x438 + CELLS])
                    uc.mem_write(G['height'], POISON * (4 * CELLS))
                    client.write('world', 'i', [number - 1])
                    ok, _ = region(client, 0x016c850c, 0x016c85af, {-8: big, -0x1c: 0x438}, 0x340)
                    status, mine = authored.height_bytes(raw, authored.lib.mu_terrain_height_scale(number - 1))
                same = ok and status == 0 and compare_lists(client.read('height', 'f', CELLS), mine)
            elif name.startswith('terrainlight') and name.endswith('.ozb'):
                key, raw = 'light_bmp', path.read_bytes()
                client.file, client.cursor, client.crt_allowed = raw, 0, {CRT_FSEEK, CRT_FREAD}
                uc.mem_write(G['light_map'], POISON * (12 * CELLS))
                ok, _ = region(client, 0x0185b366, 0x0185b458, {-4: 0x51e0f11e, 0xc: G['light_map']}, 0x360)
                status, mine = authored.light(raw)
                same = ok and status == 0 and compare_lists(client.read('light_map', 'f', len(mine)), mine)
            elif name.endswith('.att'):
                key = 'attributes'
                kind, plain = decrypt_file(path.read_bytes(), b'ATT\x01')
                uc.mem_write(G['key'], KEY)
                uc.mem_write(big, plain)
                uc.mem_write(G['att'], POISON * (2 * CELLS))
                client.crt_allowed, client.crt_calls = {CRT_FREE, CRT_FCLOSE, ERROR_BOX}, []
                ok, eax = region(client, 0x016c9faf, 0x016ca15f, {-8: big, -0x18: len(plain), -0x14: 0x51e0f11e},
                                 0x10160)
                status, number_, att = authored.parse_attributes(plain)
                # Wrong sizes (status 1, e.g. the *_Server_64k.att files the client never opens) return -1
                # before any cell is written; corrupt files (status 2) return -1 after writing the cells.
                same = ok and (eax == 0xffffffff) == (status != 0) and (status == 1 or
                                                                        client.read('att', 'H', CELLS) == att)
            elif name.endswith('.map'):
                key = 'map'
                kind, plain = decrypt_file(path.read_bytes(), b'MAP\x01')
                if len(plain) > 0x40000:
                    result['failures'].append([path.name, 'map-too-large-for-window'])
                    continue
                uc.mem_write(big, plain)
                for n, size in (('layer1', CELLS), ('layer2', CELLS), ('alpha', 4 * CELLS)):
                    uc.mem_write(G[n], POISON * size)
                ok, _ = region(client, 0x016c9adf, 0x016c9b8b, {-0x14: big}, 0x50)
                status, number_, l1, l2, alpha = authored.parse_map(plain)
                same = (ok and status == 0 and bytes(uc.mem_read(G['layer1'], CELLS)) == l1 and
                        bytes(uc.mem_read(G['layer2'], CELLS)) == l2 and
                        compare_lists(client.read('alpha', 'f', CELLS), alpha))
            else:
                continue
            result[key][0] += 1
            result[key][1] += int(bool(same))
            if not same:
                result['failures'].append([f'World{number}/{path.name}', key])
    return result


def world_is_rgb(world):
    """0x016c9868 with the handler table (NATIVE-TERRAIN-002): nothing is left to the file length."""
    return bool(py_height_is_rgb(world)), False


def tool_sizes(game_root, world):
    """Bitmap sizes as the native loader resolves them (mu-terrain export trailer), or None."""
    import subprocess
    tool = ROOT / 'native/build/mu-terrain'
    if not tool.exists():
        return None
    out = subprocess.run([str(tool), 'export', str(game_root), '--world', str(world)], capture_output=True).stdout
    trailer = out[out.rfind(b'{"time"'):]
    try:
        bitmaps = json.loads(trailer)['bitmaps']
    except (ValueError, KeyError):
        return None
    return {int(k): (float(v[0]), float(v[1])) for k, v in bitmaps.items()}


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
    parser.add_argument('--skip-002', action='store_true', help='skip the NATIVE-TERRAIN-002 checks')
    parser.add_argument('--scale-002', type=int, default=1, help='multiply the NATIVE-TERRAIN-002 case counts')
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
