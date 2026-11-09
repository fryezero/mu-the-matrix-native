#!/usr/bin/env python3
"""RENDER-ITEMS-CLOAK / CLOAK-002: the wings' physics capes (every CreateCloth case) against the pinned client.

reconstructed/cloth reproduces the client's cloth (docs/research/client-render-items.md parts 25 and 27). The client routines
run as client code on the restored text and the second section (renderchar_machine, with validate_renderchar's
services); the C runs the same states through ctypes. Families:

* create  CreateCloth 0x01357ccc(c, o, light, arg4) on a fresh CHARACTER for every wing type of its switch (aliases
          included), arg 4 = 1 and wings without a cloth: the cloth count (+0x3f) and every field of every cloth object
          (header, vertices, springs, the sphere list; the glow fields and the +0x48 matrix where set). States: random
          OBJECT angles and scale (+0xa0), wing level (+0x21a6), SceneFlag 0x01d1df70 (5 or 6), sub-type +0x60 (0 or
          0x5bc / 0x5bd with its own model), Player model scale / origin, 60 random bone matrices; some cases without a
          bone array, with too few bones or without the Player model (the client's failure returns).
* step    RenderCharacter's per-frame calls as it makes them: MoveCloth 0x01362f24(c, o) then RenderCloth
          0x01363098(c, o, light, 0) (the creation frame steps once more inside it). Between frames the bones, the
          angles, the model origin and scale, WorldTime 0x06fce370, the logic-step counter 0x0bdc5eb0, the world
          0x01cf15fc (0x37 = the random wind), the wind 0x01ec981c, rand() and the stretch test 0x00aae6f9 change.
          After every frame: every cloth field, the wind vector 0x01ec9820 and the rand() state.
* render  the same frames' GL streams: the state wrapper, BindTexture, glColor4f, glBegin(GL_QUADS), glTexCoord2f /
          glVertex3f per corner and glEnd of virtual slot 8 (0x00fd8bc2) with its glow pass 0x00fd9663, bit for bit.
* wind    the physics manager's step 0x00fdad7b(0.005) on an empty list: the wind walk (rand()) from random winds.
* gate    RenderCharacter 0x01363260 up to its cloth call: the cloth flag [ebp-0x4d], arg 4 [ebp-0x128] and the light
          [ebp-0xc8] at 0x0136ab87 over class bytes, CHARACTER +0x0e / +0x1f / +0x146 / +0x21a4 / +0x32b0, the OBJECT
          type and the world, against mu_cloth_gate.

Services replaced (besides validate_renderchar's): rand() 0x01989721 (the MSVC generator, state shared with the C),
the stretch test 0x00aae6f9 (case value), in the gate family the hero-only test 0x0137ad93 (0), the state wrappers 0x0184a7f3 / 0x0184a990 / 0x0184aa2b and BindTexture
0x0184acf6 (recorded). The trig and sqrt wrappers, AngleMatrix, TransformPosition, the bone accessor, the list and
the allocators run as client code.

--mutations plants mistakes in reconstructed/cloth/cloth.c (compiled separately) and requires each to be caught.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import math
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time as clock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
import renderchar_machine as rmach  # noqa: E402
from renderchar_machine import f2u, u2f  # noqa: E402
import validate_renderchar as vr  # noqa: E402

DIR = ROOT / 'reconstructed/cloth'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
CREATE_CLOTH, MOVE_CLOTH, RENDER_CLOTH, MOVE_WIND = 0x01357ccc, 0x01362f24, 0x01363098, 0x00fdad7b
RENDER_CHARACTER, GATE_AT = 0x01363260, 0x0136ab87
WIND, WIND_VECTOR, TIME, STEPS, WORLD = 0x01ec981c, 0x01ec9820, 0x06fce370, 0x0bdc5eb0, 0x01cf15fc
CLOTH_TYPES = (0x2382, 0x2383, 0x2384, 0x2385, 0x2394, 0x2395)
# CLOAK-002: every other case of the switch 0x01357e5c (first type of each case, then its aliases)
MORE_TYPES = (0x230e, 0x2317, 0x2318, 0x2368, 0x236d, 0x2380, 0x2381, 0x2386, 0x2392, 0x2393, 0x2396, 0x2398,
              0x239e, 0x23a0, 0x23a1, 0x23a5, 0x23a7, 0x23ec, 0x23f1, 0x23f3, 0x23f4, 0x23fc, 0x2488, 0x248a,
              0x248b, 0x2490, 0x24c6, 0x34e6, 0x34e7, 0x34e9, 0x34eb)
ALIAS_TYPES = (0x2498, 0x2492, 0x249a, 0x2387, 0x2397, 0x2399, 0x23fd, 0x2402, 0x2401, 0x2493, 0x249b, 0x24a0,
               0x24a2, 0x24a3, 0x2504, 0x34e8, 0x34ea)
ARG4 = 'arg4'                                     # a case of CreateCloth's arg 4 = 1 (the wing is random)
PLAIN_WINGS = (-1, 0x1000, 0x22ee, 0x0b27, 0x239a, 0x239f, 0x23a2)   # no case (sword, Wing02, unused, table holes)
SCENE = 0x01d1df70
ROTATE_SCRATCH = 0x078965ac                       # RotatePosition 0x012b7019 copies the bone matrix here
SUB_MODEL = vr.PLAYER_MODEL + 0x400
CASE_BONES = vr.BONES                             # the OBJECT +0x318 array (validate_renderchar layout)
LIGHT_VEC = 0x2d000000
MANAGER = 0x2d001000
GL_QUADS = 7
STATE_WRAPPERS = {0x0184a7f3: 1, 0x0184a990: 2, 0x0184aa2b: 3}
RANGES = {'CreateCloth': (0x01357ccc, 0x0135e9eb), 'CreateClothArmour': (0x0135ea29, 0x013626cf),
          'RenderCloth': (0x01363098, 0x01363260), 'MoveCloth': (0x01362f24, 0x01363098),
          'PhysicsVertex': (0x00fd58a8, 0x00fd6c22), 'PhysicsCloth': (0x00fd6c22, 0x00fdbc00)}

# --------------------------------------------------------------------------------------------- ctypes view

class CVertex(ctypes.Structure):
    _fields_ = [('force', ctypes.c_float * 3), ('velocity', ctypes.c_float * 3), ('position', ctypes.c_float * 3),
                ('flags', ctypes.c_uint8), ('count', ctypes.c_int32), ('delta', ctypes.c_float * 3)]


class CSpring(ctypes.Structure):
    _fields_ = [('v0', ctypes.c_int16), ('v1', ctypes.c_int16), ('min_length', ctypes.c_float),
                ('length', ctypes.c_float), ('flags', ctypes.c_uint8)]


class CSphere(ctypes.Structure):
    _fields_ = [('offset', ctypes.c_float * 3), ('bone', ctypes.c_int32), ('center', ctypes.c_float * 3),
                ('radius', ctypes.c_float)]


class CCloth(ctypes.Structure):
    _fields_ = [('owner', ctypes.c_int32), ('bone', ctypes.c_int32), ('texture_front', ctypes.c_int32),
                ('texture_back', ctypes.c_int32), ('type', ctypes.c_uint32), ('origin', ctypes.c_float * 3),
                ('width', ctypes.c_float), ('height', ctypes.c_float), ('columns', ctypes.c_int32),
                ('rows', ctypes.c_int32), ('vertex_count', ctypes.c_int32), ('spring_count', ctypes.c_int32),
                ('custom', ctypes.c_uint8), ('matrix', ctypes.c_float * 12), ('alpha', ctypes.c_float),
                ('alpha_from_object', ctypes.c_uint8),
                ('uv_scale', ctypes.c_float * 2), ('uv_offset', ctypes.c_float * 2), ('wind', ctypes.c_float),
                ('wind_range', ctypes.c_uint8), ('wind_base', ctypes.c_uint8), ('push', ctypes.c_float * 2),
                ('glow_texture', ctypes.c_int32), ('glow', ctypes.c_float * 3), ('mesh', ctypes.c_int32), ('mesh_level', ctypes.c_int32), ('mesh_color', ctypes.c_float * 3),
                ('glow2_texture', ctypes.c_int32), ('glow2', ctypes.c_float * 3),
                ('step', ctypes.c_float * 2),
                ('sphere_count', ctypes.c_int32), ('spheres', CSphere * 8), ('vertices', CVertex * 256),
                ('springs', CSpring * 1024)]


class CHost(ctypes.Structure):
    _fields_ = [('bones', ctypes.POINTER(ctypes.c_float)), ('bone_count', ctypes.c_int32),
                ('has_model', ctypes.c_int32), ('body_scale', ctypes.c_float), ('body_origin', ctypes.c_float * 3),
                ('angles', ctypes.c_float * 3), ('alpha', ctypes.c_float), ('subtype', ctypes.c_int32),
                ('sub_has_model', ctypes.c_int32), ('sub_body_scale', ctypes.c_float),
                ('sub_body_origin', ctypes.c_float * 3)]


class CWingIn(ctypes.Structure):
    _fields_ = [('wing_type', ctypes.c_int16), ('wing_level', ctypes.c_int8), ('arg4', ctypes.c_uint8),
                ('scene', ctypes.c_int32), ('object_scale', ctypes.c_float)]


class CGlobals(ctypes.Structure):
    _fields_ = [('time', ctypes.c_float), ('logic_steps', ctypes.c_int32), ('world', ctypes.c_int32),
                ('wind', ctypes.c_float), ('wind_vector', ctypes.c_float * 3), ('gravity', ctypes.c_float * 3),
                ('rand_seed', ctypes.c_uint32), ('quality', ctypes.c_int32), ('stretch_hold', ctypes.c_uint8)]


class CGateIn(ctypes.Structure):
    _fields_ = [('class_byte', ctypes.c_uint8), ('c_0e', ctypes.c_uint8), ('pk', ctypes.c_uint8),
                ('wing_type', ctypes.c_int16), ('class_index', ctypes.c_int16), ('object_type', ctypes.c_int32),
                ('own_type', ctypes.c_int32), ('world', ctypes.c_int32)]


class CGateOut(ctypes.Structure):
    _fields_ = [('render', ctypes.c_uint8), ('arg4', ctypes.c_uint8), ('light', ctypes.c_float * 3)]


STATE_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
BIND_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
COLOR_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
BEGIN_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32)
TEX_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
VERTEX_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float)
END_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


SPRITE_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                              ctypes.c_float, ctypes.POINTER(ctypes.c_float))


class CSink(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('state', STATE_CB), ('bind', BIND_CB), ('color4', COLOR_CB),
                ('begin', BEGIN_CB), ('texcoord', TEX_CB), ('vertex', VERTEX_CB), ('end', END_CB), ('sprite', SPRITE_CB)]


def bits(value):
    return f2u(value) if isinstance(value, float) else value


def build(source_dir: Path, work: Path, name: str):
    out = work / f'lib{name}.{SUFFIX}'
    result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                             '-ffp-contract=off', '-fno-fast-math', '-shared', str(source_dir / 'cloth.c'),
                             str(ROOT / 'reconstructed/record-math/record_math.c'), '-I', str(source_dir),
                             '-lm', '-o', str(out)], capture_output=True, text=True)
    if result.returncode:
        return None, result.stderr[-2000:]
    lib = ctypes.CDLL(str(out))
    P = ctypes.POINTER
    lib.mu_cloth_create.argtypes = [P(CCloth), P(CHost), ctypes.c_int32, ctypes.c_float, ctypes.c_float,
                                    ctypes.c_float, ctypes.c_int32, ctypes.c_int32, ctypes.c_float, ctypes.c_float,
                                    ctypes.c_int32, ctypes.c_int32, ctypes.c_uint32]
    lib.mu_cloth_wing_create.argtypes = [P(CCloth), P(CWingIn), P(CHost)]
    lib.mu_cloth_move2.argtypes = [P(CCloth), P(CHost), P(CGlobals), ctypes.c_float, ctypes.c_int32]
    lib.mu_cloth_render.argtypes = [P(CCloth), P(CHost), P(CGlobals), P(ctypes.c_float), P(CSink)]
    lib.mu_cloth_wind_step.argtypes = [P(CGlobals)]
    lib.mu_cloth_default_globals.argtypes = [P(CGlobals)]
    lib.mu_cloth_gate.argtypes = [P(CGateIn), P(CGateOut)]
    lib.mu_cloth_draw_allowed.argtypes = [ctypes.c_uint8, ctypes.c_int32, ctypes.c_uint16, ctypes.c_uint16,
                                          ctypes.c_int16]
    return lib, None


# --------------------------------------------------------------------------------------------- client side

GRAVITY = 0x01cf0eb0            # 9.8, 0.0025, 400: initialized section-3 data (pins.EFFECTS_INIT, MU_SECTION3)
SECTION3_INIT = {'bytes': None}


def install(w, state):
    """The cloth family's services on a validate_renderchar World."""
    m, rec = w.m, w.calls
    m.ensure(GRAVITY, 12)
    m.write(GRAVITY, SECTION3_INIT['bytes'][GRAVITY - pins.EFFECTS_INIT.base:GRAVITY - pins.EFFECTS_INIT.base + 12])

    def rand(mm):
        state['seed'] = (state['seed'] * 214013 + 2531011) & 0xffffffff
        return (state['seed'] >> 16) & 0x7fff
    m.stub(0x01989721, rand, 0)
    m.stub(0x00ac3bf7, lambda mm: MANAGER + 0x800, 0)
    m.stub(0x00aae6f9, lambda mm: state['hold'], 0)
    for address, op in STATE_WRAPPERS.items():
        m.stub(address, (lambda o: (lambda mm: rec.append(('state', o)) or 0))(op), 0)
    m.stub(0x0184acf6, lambda mm: rec.append(('bind', mm.arg(0))) or 0, 0)


def bone_matrices(rng, count, spread=60.0):
    out = []
    for _ in range(count):
        a, b, c = (rng.uniform(-math.pi, math.pi) for _ in range(3))
        ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
        rot = [[cb * cc, sa * sb * cc - ca * sc, ca * sb * cc + sa * sc],
               [cb * sc, sa * sb * sc + ca * cc, ca * sb * sc - sa * cc],
               [-sb, sa * cb, ca * cb]]
        t = [rng.uniform(-spread, spread) for _ in range(3)]
        out.append([u2f(f2u(v)) for v in (rot[0] + [t[0]] + rot[1] + [t[1]] + rot[2] + [t[2]])])
    return out


def perturb(rng, bones, size):
    return [[u2f(f2u(v + rng.uniform(-size, size))) for v in m] for m in bones]


def pack_bones(bones):
    return b''.join(struct.pack('<12f', *m) for m in bones)


def frame_state(rng, frame, base):
    s = dict(base)
    s['angles'] = [u2f(f2u(rng.uniform(-360.0, 360.0))) if rng.random() < 0.5 else 0.0,
                   0.0, u2f(f2u(rng.uniform(0.0, 360.0)))]
    s['time'] = u2f(f2u(base['time0'] + 40.0 * frame + rng.uniform(0.0, 39.0)))
    s['steps'] = (base['steps0'] + frame * rng.choice((1, 1, 2, 7))) & 0xffffffff
    s['world'] = 0x37 if rng.random() < 0.15 else rng.choice((0, 0, 2, 0x12))
    s['wind'] = u2f(f2u(rng.uniform(-0.2, 1.0))) if rng.random() < 0.9 else 0.0
    s['light'] = [u2f(f2u(rng.uniform(0.0, 1.0))) for _ in range(3)]
    s['alpha'] = u2f(f2u(rng.choice((1.0, rng.uniform(0.0, 1.0)))))
    s['origin'] = [u2f(f2u(v + rng.uniform(-30.0, 30.0))) for v in base['origin0']]
    s['scale'] = u2f(f2u(rng.choice((0.9, 1.0, rng.uniform(0.6, 1.4)))))
    s['hold'] = 1 if rng.random() < 0.2 else 0
    s['object_scale'] = u2f(f2u(rng.choice((0.9, 1.0, rng.uniform(0.5, 1.6)))))
    s['sub_scale'] = u2f(f2u(rng.uniform(0.6, 1.4)))
    s['sub_origin'] = [u2f(f2u(v + rng.uniform(-40.0, 40.0))) for v in base['origin0']]
    return s


class ClientCloth:
    """One CHARACTER + OBJECT in a World; reads the cloth objects back."""

    def __init__(self, world_args, case):
        self.w = w = vr.World(*world_args)
        self.m = m = w.m
        self.state = {'seed': case['seed'], 'hold': 0}
        install(w, self.state)
        self.case = case
        if case['has_model']:
            w.add_model(0xa91, vr.PLAYER_MODEL, bones=case['bone_count'], meshes=0, actions=390)
        if case['subtype'] and case['sub_model']:
            w.add_model(case['subtype'], SUB_MODEL, bones=60, meshes=0, actions=1)
        record = vr.character_record(cls=case['class'], action=1)
        struct.pack_into('<h', record, 0x21a4, case['wing'])
        struct.pack_into('<b', record, 0x21a6, case['level'])
        o = 0x3254
        record[o + 0x3b] = 0                                 # no armour cloth (CreateClothArmour 0x0135ea29)
        struct.pack_into('<I', record, o + 0x318, CASE_BONES if case['bones'] else 0)
        struct.pack_into('<i', record, o + 0x60, case['subtype'])
        m.write(vr.CHAR, record)
        m.map(LIGHT_VEC, 0x2000)
        for address in (WIND, WIND_VECTOR, TIME, STEPS, WORLD, SCENE):
            m.ensure(address, 16)
        m.ensure(ROTATE_SCRATCH, 0x40)
        m.w32(SCENE, case['scene'])
        self.o = vr.CHAR + o

    def apply(self, s):
        m, o = self.m, self.o
        m.write(CASE_BONES, pack_bones(s['bones']))
        m.write(o + 0x164, struct.pack('<3f', *s['angles']))
        m.write(o + 0xdc, struct.pack('<f', s['alpha']))
        m.write(o + 0x158, struct.pack('<3f', *s['origin']))
        if self.case['has_model']:
            m.write(vr.PLAYER_MODEL + 0x74, struct.pack('<4f', s['scale'], *s['origin']))
        if self.case['subtype'] and self.case['sub_model']:
            m.write(SUB_MODEL + 0x74, struct.pack('<4f', s['sub_scale'], *s['sub_origin']))
        m.write(o + 0xa0, struct.pack('<f', s['object_scale']))
        m.wf(TIME, s['time'])
        m.w32(STEPS, s['steps'])
        m.w32(WORLD, s['world'])
        m.wf(WIND, s['wind'])
        m.write(LIGHT_VEC, struct.pack('<3f', *s['light']))
        self.state['hold'] = s['hold']

    def frame(self, s, first):
        """MoveCloth then RenderCloth, as RenderCharacter calls them; returns (ok, GL stream)."""
        self.apply(s)
        self.w.calls.clear()
        r1 = self.m.run(MOVE_CLOTH, [vr.CHAR, self.o])
        r2 = self.m.run(RENDER_CLOTH, [vr.CHAR, self.o, LIGHT_VEC, self.case['arg4']])
        stream = []
        for c in self.w.calls:
            if c[0] == 'state':
                stream.append(('state', c[1]))
            elif c[0] == 'bind':
                stream.append(('bind', c[1]))
            elif c[0] == 'gl' and c[1] in ('glColor4f', 'glBegin', 'glTexCoord2f', 'glVertex3f', 'glEnd'):
                stream.append((c[1],) + tuple(c[2]))
        return (r1['ok'] and r2['ok']), stream, (r1, r2)

    def create(self, s):
        self.apply(s)
        return self.m.run(CREATE_CLOTH, [vr.CHAR, self.o, LIGHT_VEC, self.case['arg4']])

    def read(self):
        m, o = self.m, self.o
        count = m.read(o + 0x3f, 1)[0]
        base = m.r32(o + 0x4c)
        cloths = []
        for i in range(count if base else 0):
            cloths.append(read_cloth(m, base + i * 0xe8))
        return count, base != 0, cloths


def read_cloth(m, p):
    f = lambda off: m.r32(p + off)  # noqa: E731
    head = {
        'owner': int(f(4) != 0), 'bone': f(8), 'texture_front': f(0xc), 'texture_back': f(0x10), 'type': f(0x14),
        'origin': [f(0x18), f(0x1c), f(0x20)], 'width': f(0x24), 'height': f(0x28), 'columns': f(0x2c),
        'rows': f(0x30), 'vertex_count': f(0x34), 'spring_count': f(0x3c), 'custom': m.read(p + 0x44, 1)[0],
        'alpha': f(0x78), 'alpha_from_object': m.read(p + 0x7c, 1)[0], 'uv_scale': [f(0x80), f(0x84)],
        'uv_offset': [f(0x88), f(0x8c)], 'wind': f(0x90), 'wind_range': m.read(p + 0x94, 1)[0],
        'wind_base': m.read(p + 0x95, 1)[0], 'push': [f(0x98), f(0x9c)], 'glow_texture': f(0xa0), 'mesh': f(0xc0),
        'step': [f(0xd4), f(0xd8)], 'glow2_texture': f(0xb0)}
    if head['mesh'] != 0xffffffff:
        head['mesh_level'] = f(0xc4)
        head['mesh_color'] = [f(0xc8), f(0xcc), f(0xd0)]
    if head['glow2_texture'] != 0xffffffff:
        head['glow2'] = [f(0xb4), f(0xb8), f(0xbc)]
    if head['custom']:
        head['matrix'] = list(struct.unpack('<12I', m.read(p + 0x48, 48)))
    if head['glow_texture'] != 0xffffffff:
        head['glow'] = [f(0xa4), f(0xa8), f(0xac)]
    vertices = []
    vbase = f(0x38)
    for i in range(head['vertex_count'] if vbase else 0):
        v = vbase + 0x3c * i
        raw = m.read(v, 0x3c)
        w = struct.unpack('<15I', raw)
        vertices.append({'force': list(w[1:4]), 'velocity': list(w[4:7]), 'position': list(w[7:10]),
                         'flags': raw[0x28], 'count': w[11], 'delta': list(w[12:15])})
    springs = []
    sbase = f(0x40)
    for i in range(head['spring_count'] if sbase else 0):
        raw = m.read(sbase + 16 * i, 16)
        v0, v1, mn, ln = struct.unpack('<hhII', raw[:12])
        springs.append({'v0': v0, 'v1': v1, 'min_length': mn, 'length': ln, 'flags': raw[12]})
    spheres = []
    lst = p + 0xdc
    count = m.r32(lst)
    tail = m.r32(lst + 8)
    node = m.r32(m.r32(lst + 4) + 8) if count else tail
    guard = 0
    while node and node != tail and guard < 64:
        s = m.r32(node)
        w = struct.unpack('<9I', m.read(s, 0x24))
        spheres.append({'offset': list(w[1:4]), 'bone': w[4], 'center': list(w[5:8]), 'radius': w[8]})
        node = m.r32(node + 8)
        guard += 1
    head['sphere_count'] = count
    return {'head': head, 'vertices': vertices, 'springs': springs, 'spheres': spheres}


def c_cloth_view(c):
    head = {
        'owner': int(c.owner != 0), 'bone': c.bone & 0xffffffff, 'texture_front': c.texture_front & 0xffffffff,
        'texture_back': c.texture_back & 0xffffffff, 'type': c.type, 'origin': [f2u(v) for v in c.origin],
        'width': f2u(c.width), 'height': f2u(c.height), 'columns': c.columns & 0xffffffff,
        'rows': c.rows & 0xffffffff, 'vertex_count': c.vertex_count & 0xffffffff,
        'spring_count': c.spring_count & 0xffffffff, 'custom': c.custom, 'alpha': f2u(c.alpha),
        'alpha_from_object': c.alpha_from_object, 'uv_scale': [f2u(v) for v in c.uv_scale],
        'uv_offset': [f2u(v) for v in c.uv_offset], 'wind': f2u(c.wind), 'wind_range': c.wind_range,
        'wind_base': c.wind_base, 'push': [f2u(v) for v in c.push], 'glow_texture': c.glow_texture & 0xffffffff,
        'mesh': c.mesh & 0xffffffff, 'glow2_texture': c.glow2_texture & 0xffffffff, 'step': [f2u(v) for v in c.step], 'sphere_count': c.sphere_count}
    if c.mesh != -1:
        head['mesh_level'] = c.mesh_level & 0xffffffff
        head['mesh_color'] = [f2u(v) for v in c.mesh_color]
    if c.glow2_texture != -1:
        head['glow2'] = [f2u(v) for v in c.glow2]
    if c.custom:
        head['matrix'] = [f2u(v) for v in c.matrix]
    if c.glow_texture != -1:
        head['glow'] = [f2u(v) for v in c.glow]
    vertices = [{'force': [f2u(x) for x in v.force], 'velocity': [f2u(x) for x in v.velocity],
                 'position': [f2u(x) for x in v.position], 'flags': v.flags, 'count': v.count & 0xffffffff,
                 'delta': [f2u(x) for x in v.delta]} for v in c.vertices[:c.vertex_count]]
    springs = [{'v0': s.v0, 'v1': s.v1, 'min_length': f2u(s.min_length), 'length': f2u(s.length),
                'flags': s.flags} for s in c.springs[:c.spring_count]]
    spheres = [{'offset': [f2u(x) for x in s.offset], 'bone': s.bone & 0xffffffff,
                'center': [f2u(x) for x in s.center], 'radius': f2u(s.radius)} for s in c.spheres[:c.sphere_count]]
    return {'head': head, 'vertices': vertices, 'springs': springs, 'spheres': spheres}


def client_fields_only(view):
    """Fields the client leaves uninitialised before Create writes them are not compared: +0x78 / +0x7c / +0x90
    exist from the constructor's memory only after Create / the first step."""
    return view


# --------------------------------------------------------------------------------------------- C side

class CSide:
    def __init__(self, lib, case):
        self.lib = lib
        self.case = case
        self.cloths = (CCloth * 3)()
        self.count = 0
        self.g = CGlobals()
        lib.mu_cloth_default_globals(ctypes.byref(self.g))
        self.g.rand_seed = case['seed']
        self.host = CHost()
        self.bones = (ctypes.c_float * (12 * 200))()
        self.stream = []
        self._sink()

    def _sink(self):
        s = self.stream
        self.cbs = [STATE_CB(lambda c, w: s.append(('state', w))), BIND_CB(lambda c, b: s.append(('bind', b & 0xffffffff))),
                    COLOR_CB(lambda c, r, g, b, a: s.append(('glColor4f', f2u(r), f2u(g), f2u(b), f2u(a)))),
                    BEGIN_CB(lambda c, mode: s.append(('glBegin', mode))),
                    TEX_CB(lambda c, u, v: s.append(('glTexCoord2f', f2u(u), f2u(v)))),
                    VERTEX_CB(lambda c, x, y, z: s.append(('glVertex3f', f2u(x), f2u(y), f2u(z)))),
                    END_CB(lambda c: s.append(('glEnd',))),
                    SPRITE_CB(lambda c, b, p, scale, light: s.append(('sprite', b, *[f2u(p[k]) for k in range(3)],
                                                                    f2u(scale), *[f2u(light[k]) for k in range(3)])))]
        self.sink = CSink(None, *self.cbs)

    def apply(self, st):
        case = self.case
        flat = [v for m in st['bones'] for v in m]
        for i, v in enumerate(flat):
            self.bones[i] = v
        h = self.host
        h.bones = ctypes.cast(self.bones, ctypes.POINTER(ctypes.c_float)) if case['bones'] else None
        h.bone_count = case['bone_count']
        h.has_model = case['has_model']
        h.body_scale = st['scale'] if case['has_model'] else 0.0
        for k in range(3):
            h.body_origin[k] = st['origin'][k] if case['has_model'] else 0.0
            h.angles[k] = st['angles'][k]
        h.alpha = st['alpha']
        h.subtype = case['subtype']
        h.sub_has_model = case['sub_model']
        h.sub_body_scale = st['sub_scale'] if case['sub_model'] else 0.0
        for k in range(3):
            h.sub_body_origin[k] = st['sub_origin'][k] if case['sub_model'] else 0.0
        self.wing_in = CWingIn(case['wing'], case['level'], case['arg4'], case['scene'], st['object_scale'])
        g = self.g
        g.time = st['time']
        g.logic_steps = struct.unpack('<i', struct.pack('<I', st['steps']))[0]
        g.world = st['world']
        g.wind = st['wind']
        g.stretch_hold = st['hold']

    def create(self, st):
        self.apply(st)
        self.count = self.lib.mu_cloth_wing_create(self.cloths, ctypes.byref(self.wing_in), ctypes.byref(self.host))
        return self.count

    def move_cloth(self):
        for i in range(self.count):
            if self.cloths[i].owner and not self.lib.mu_cloth_move2(ctypes.byref(self.cloths[i]),
                                                                     ctypes.byref(self.host), ctypes.byref(self.g),
                                                                     ctypes.c_float(0.005), 5):
                self.count = 0      # DeleteCloth 0x0137aafe
                return

    def frame(self, st, first):
        """RenderCharacter's MoveCloth, then RenderCloth (creation + its MoveCloth on the first frame)."""
        self.apply(st)
        del self.stream[:]
        self.move_cloth()
        created = False
        if self.count == 0:   # RenderCloth calls CreateCloth while the OBJECT has no cloth (+0x4c)
            created = self.create(st) > 0
        if created:
            self.move_cloth()
        light = (ctypes.c_float * 3)(*st['light'])
        if not self.lib.mu_cloth_draw_allowed(self.case['class'], self.case['subtype'], 1, 1, 0):
            return list(self.stream)   # character_record(action=1), class index 0
        for i in range(self.count):
            if self.cloths[i].owner:
                self.lib.mu_cloth_render(ctypes.byref(self.cloths[i]), ctypes.byref(self.host), ctypes.byref(self.g),
                                         light, ctypes.byref(self.sink))
        return list(self.stream)


def stream_bits(stream):
    out = []
    for item in stream:
        name = item[0]
        if name == 'state':
            out.append(('state', item[1]))
        elif name == 'bind':
            out.append(('bind', item[1] & 0xffffffff))
        else:
            out.append(tuple([name] + [v & 0xffffffff for v in item[1:]]))
    return out


# --------------------------------------------------------------------------------------------- families

def new_family():
    return {'cases': 0, 'mismatches': 0, 'stopped': 0, 'examples': []}


class Caught(Exception):
    """A mutant run stops at its first mismatch."""


STOP = {'early': False}


def note(fam, ok, example):
    fam['cases'] += 1
    if not ok:
        fam['mismatches'] += 1
        if len(fam['examples']) < 3:
            fam['examples'].append(example)
        if STOP['early']:
            raise Caught()


def first_difference(a, b, path=''):
    if type(a) is not type(b):
        return path or '/'
    if isinstance(a, dict):
        for k in a:
            if k not in b:
                return f'{path}/{k}'
            d = first_difference(a[k], b[k], f'{path}/{k}')
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f'{path}#len {len(a)} != {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f'{path}[{i}]')
            if d:
                return d
        return None
    return None if a == b else f'{path}: {a} != {b}'


def random_case(rng, wing, index):
    kind = rng.random()
    arg4 = 0
    if wing == ARG4:
        arg4, wing = 1, rng.choice((-1, 0x2382, 0x24c6, 0x22ee))
    case = {'wing': wing, 'class': rng.choice((0, 4, 0x20, 1, 0x12, 6, 3, 0x23)), 'seed': rng.randrange(1 << 32),
            'bones': 1, 'bone_count': 60, 'has_model': 1, 'arg4': arg4,
            'level': rng.choice((0, 7, 8, 9, 10, 11, 13, 15, -3)), 'scene': rng.choice((5, 6, 6)),
            'subtype': rng.choice((0, 0, 0, 0, 0x5bc, 0x5bd, 0x5be, 0x431, 0x3e9)), 'sub_model': 1}
    if case['subtype'] and rng.random() < 0.2:
        case['sub_model'] = 0
    if kind < 0.06:
        case['bones'] = 0
    elif kind < 0.10:
        case['bone_count'] = rng.choice((10, 18, 19))
    elif kind < 0.13:
        case['has_model'] = 0
    rngb = random.Random(case['seed'] ^ index)
    case['bones0'] = bone_matrices(rngb, 60, spread=rng.choice((20.0, 60.0, 150.0)))
    case['time0'] = rng.uniform(0.0, 5e6)
    case['steps0'] = rng.choice((0, rng.randrange(1, 1 << 20), rng.randrange(1 << 31, 1 << 32)))
    case['origin0'] = [rng.uniform(-5000.0, 30000.0) for _ in range(3)]
    return case


COVERAGE = {}


def cover(key, n=1):
    COVERAGE[key] = COVERAGE.get(key, 0) + n


def run_cases(world_args, lib, cases, frames, seed, families):
    rng = random.Random(seed)
    types = list(CLOTH_TYPES) * 3 + list(MORE_TYPES) * 3 + list(ALIAS_TYPES) + [ARG4] * 4 + list(PLAIN_WINGS)
    for index in range(cases):
        wing = types[index % len(types)]
        case = random_case(rng, wing, index)
        client = ClientCloth(world_args, case)
        cside = CSide(lib, case)
        fr = random.Random(case['seed'])
        bones = case['bones0']
        base = {'bones': bones, 'time0': case['time0'], 'steps0': case['steps0'], 'origin0': case['origin0']}
        # create: CreateCloth directly on a twin CHARACTER (the state of frame 0)
        st0 = frame_state(fr, 0, base)
        st0['bones'] = bones
        twin = ClientCloth(world_args, case)
        r = twin.create(st0)
        tcount, tptr, tcloths = twin.read()
        tside = CSide(lib, case)
        n = tside.create(st0)
        cv = [c_cloth_view(tside.cloths[i]) for i in range(n)]
        cover('cloths', n)
        cover('custom', sum(1 for c in cv if c['head']['custom']))
        cover('glow_set', sum(1 for c in cv if 'glow' in c['head']))
        cover('arg4', case['arg4'])
        cover('scene5_23ec', int(case['scene'] == 5 and case['wing'] in (0x23ec, 0x23fd, 0x2402)))
        cover('sub_model', int(case['subtype'] in (0x5bc, 0x5bd) and n > 0))
        ok = r['ok'] and tcount == n and (tptr == (n > 0)) and not first_difference(tcloths, cv)
        if not r['ok']:
            families['create']['stopped'] += 1
        note(families['create'], ok, {'case': case['wing'], 'run': r if not r['ok'] else None, 'count': [tcount, n],
                                      'diff': first_difference(tcloths, cv)})
        # step + render: the frames
        for frame in range(frames):
            st = frame_state(fr, frame, base)
            if frame:
                bones = perturb(fr, bones, fr.choice((0.5, 3.0, 20.0)))
            st['bones'] = bones
            okc, stream, runs = client.frame(st, frame == 0)
            cstream = cside.frame(st, frame == 0)
            count, ptr, cloths = client.read()
            cview = [c_cloth_view(cside.cloths[i]) for i in range(cside.count)]
            wind_vec = list(struct.unpack('<3I', client.m.read(WIND_VECTOR, 12)))
            cwind = [f2u(v) for v in cside.g.wind_vector]
            # the client's vector keeps its earlier z; ours starts at 0 like the captured section
            same = okc and count == cside.count and not first_difference(cloths, cview) and wind_vec[:2] == cwind[:2] \
                and client.state['seed'] == cside.g.rand_seed
            if not okc:
                families['step']['stopped'] += 1
            note(families['step'], same, {'wing': case['wing'], 'frame': frame, 'runs': None if okc else runs,
                                          'count': [count, cside.count], 'diff': first_difference(cloths, cview),
                                          'wind': [wind_vec, cwind], 'seed': [client.state['seed'], cside.g.rand_seed]})
            a, b = stream_bits(stream), stream_bits(cstream)
            cover('glow_pass', sum(1 for x in a if x == ('state', 3)))
            cover('hidden_draw', int(cside.count > 0 and not a))
            cover('drawn_frames', int(bool(a)))
            if not okc:
                families['render']['stopped'] += 1
            note(families['render'], okc and a == b,
                 {'wing': case['wing'], 'frame': frame, 'len': [len(a), len(b)],
                  'first': next(([i, a[i], b[i]] for i in range(min(len(a), len(b))) if a[i] != b[i]), None)})


def wind_family(world_args, lib, cases, seed, fam):
    rng = random.Random(seed ^ 0x77)
    w = vr.World(*world_args)
    m = w.m
    state = {'seed': 1, 'hold': 0}
    install(w, state)
    m.map(MANAGER, 0x1000)
    m.ensure(WIND, 16)
    for _ in range(cases):
        wind = rng.choice((u2f(f2u(rng.uniform(-0.3, 1.1))), -0.2, 1.0, 0.0))
        state['seed'] = rng.randrange(1 << 32)
        m.wf(WIND, wind)
        m.write(MANAGER, b'\0' * 0x200)
        m.write(MANAGER + 4, struct.pack('<III', 0, MANAGER + 0x100, MANAGER + 0x110))   # list: count, head, tail
        m.write(MANAGER + 0x100 + 8, struct.pack('<I', MANAGER + 0x110))                  # head.next = tail
        m.write(MANAGER + 0x110 + 4, struct.pack('<I', MANAGER + 0x100))                  # tail.prev = head
        g = CGlobals()
        lib.mu_cloth_default_globals(ctypes.byref(g))
        g.wind = wind
        g.rand_seed = state['seed']
        steps = rng.randrange(1, 6)
        ok = True
        for _ in range(steps):
            r = m.run(MOVE_WIND, [f2u(0.005)], ecx=MANAGER)
            # thiscall with one argument: the callee pops 4 bytes (ret 4)
            ok = ok and r['checks']['returned'] and r['checks']['callee_saved']
            lib.mu_cloth_wind_step(ctypes.byref(g))
        same = ok and m.r32(WIND) == f2u(g.wind) and state['seed'] == g.rand_seed
        note(fam, same, {'wind': wind, 'client': m.r32(WIND), 'c': f2u(g.wind)})


def gate_family(world_args, lib, cases, seed, fam):
    from unicorn import UC_HOOK_CODE
    rng = random.Random(seed ^ 0x6a7e)
    indices = (0, 0, 0, 0x37, 0x169, 0x3ab, 0x3ad, 0x3a9, 0x211, 0x215, 0x216, 0x21b, 0x349, 0x3d5, 0x271, 0x100)
    worlds = (0, 0, 0, 2, 0x12, 0x17, 0x35, 0x61, 0x37, 0x18)
    wings = (-1, 0x2382, 0x2384, 0x2394, 0x23f1, 0x2401, 0x24c6, 0x22ee)
    for k in range(cases):
        cls = k % 256 if k < 256 else rng.randrange(256)
        case = {'class': cls, 'c_0e': rng.choice((0, 0, 1, 2)), 'pk': rng.choice((0, 3, 6, 6)),
                'wing': rng.choice(wings), 'index': rng.choice(indices), 'world': rng.choice(worlds),
                'type': rng.choice((0xa91, 0xa91, 0xa91, 0xa92, 0x7dc))}
        case['own'] = case['type']   # CHARACTER +0x32b0 is the passed OBJECT's +0x5c (o = c + 0x3254)
        w = vr.World(*world_args)
        m = w.m
        w.add_model(0xa91, vr.PLAYER_MODEL, bones=60, meshes=0, actions=390, actions_at=vr.ACTIONS)
        w.add_model(0xa92, vr.PLAYER_MODEL + 0x100, bones=60, meshes=0, actions=390, actions_at=vr.ACTIONS)
        for i in range(0x186):
            m.write(vr.ACTIONS + 16 * i, struct.pack('<BxxxI', 0, f2u(0.25)))
        record = vr.character_record(cls=cls, action=1)
        record[0xe] = case['c_0e']
        record[0x1f] = case['pk']
        struct.pack_into('<h', record, 0x146, case['index'])
        struct.pack_into('<h', record, 0x21a4, case['wing'])
        m.write(vr.CHAR, record)
        m.write(vr.BONES, b''.join(struct.pack('<12f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0) for _ in range(200)))
        m.ensure(WORLD, 4)
        m.w32(WORLD, case['world'])
        for address, cleanup in vr.CHAR_SKIPS.items():
            m.stub(address, (lambda a: (lambda mm: 0))(address), cleanup)
        m.stub(0x00d33153, lambda mm: vr.ACTIONS + 16 * mm.arg(0), 4)
        m.stub(0x012b5064, lambda mm: 0, 0x20)
        m.stub(0x012b4dd3, lambda mm: 0, 0x18)
        m.stub(0x017e63f4, lambda mm: 0, 0)
        m.stub(0x012bd910, lambda mm: 0, 0)
        m.stub(0x0137ad93, lambda mm: 0, 0)   # hero-only test ([ebp-0xb5], not read by the cloth block)
        o = vr.CHAR + 0x3254
        seen = []

        def at_block(uc, address, size, user):
            # the block reads the passed OBJECT's type (0x01366ebc / 0x01366ffa) and CHARACTER +0x32b0
            m.write(o + 0x5c, struct.pack('<i', case['type']))
        m.uc.hook_add(UC_HOOK_CODE, at_block, begin=0x01366eb2, end=0x01366eb2)

        def at_gate(uc, address, size, user):
            if not seen:
                ebp = uc.reg_read(m.x86.UC_X86_REG_EBP)
                seen.append((m.read(ebp - 0x4d, 1)[0], m.read(ebp - 0x128, 1)[0],
                             struct.unpack('<3I', m.read(ebp - 0xc8, 12))))
        m.uc.hook_add(UC_HOOK_CODE, at_gate, begin=GATE_AT, end=GATE_AT)

        r = m.run(RENDER_CHARACTER, [vr.CHAR, o, 0])
        gi = CGateIn(case['class'], case['c_0e'], case['pk'], case['wing'], case['index'], case['type'],
                     case['own'], case['world'])
        go = CGateOut()
        lib.mu_cloth_gate(ctypes.byref(gi), ctypes.byref(go))
        want = (go.render, go.arg4, tuple(f2u(v) for v in go.light))
        if not seen:
            fam['stopped'] += 1
        note(fam, bool(seen) and seen[0] == want, {'case': case, 'client': seen[0] if seen else r, 'c': want})


MUTANTS = {
    'weight_unsigned': ('(uint32_t)n < 4u ? n : 4', 'n < 4 ? n : 4'),
    'weight_plus': ('k4 == 0 ? 0 : k4 + 2', 'k4 == 0 ? 0 : k4 + 1'),
    'damping': ('v->velocity[k] * 0.01f', 'v->velocity[k] * 0.02f'),
    'gravity_pick': ("(type & 0xc00) == 0x400 ? 180.0f : 100.0f", "(type & 0xc00) == 0x400 ? 180.0f : 101.0f"),
    'calm_clamp': ('0.0f > wind ? 0.0f : wind', 'wind'),
    'move_order': ('v->position[k] = v->velocity[k] * time + v->position[k];',
                   'v->position[k] = a * time + v->position[k];'),
    'constrain_half': ('f = f * 0.5f;\n        f = f / d;\n        diff[k] = f * diff[k];\n    }\n    for (int k = 0; k < 3; ++k)\n        a->delta',
                       'f = f * 0.25f;\n        f = f / d;\n        diff[k] = f * diff[k];\n    }\n    for (int k = 0; k < 3; ++k)\n        a->delta'),
    'apply_fixed_count': ('        v->delta[0] = 0.0f;\n        return;\n    }\n    if (v->count <= 0)',
                          '        v->delta[0] = 0.0f;\n        v->count = 0;\n        return;\n    }\n    if (v->count <= 0)'),
    'stretch_factor': ('d > s->length * 20.0f', 'd > s->length * 10.0f'),
    'stretch_min': ('} else if (s->min_length > d) {', '} else if (0) {'),
    'sphere_push': ('float f = s->radius - length;', 'float f = s->radius - length * 1.01f;'),
    'sphere_swizzle': ('{s->offset[2], -s->offset[1], s->offset[0]}', '{s->offset[0], -s->offset[1], s->offset[2]}'),
    'fixed_swizzle': ('p[1] = -q[1];', 'p[1] = q[1];'),
    'fixed_taper': ('set_fixed_custom(c, h, matrix);\n        return;\n    }\n    int curve = 0;\n    for (int32_t x = 0; x < c->columns; ++x) {\n        float width = c->width;\n        float step = c->step[0];\n        switch (c->type & 0xc) {\n        case 4:\n            width = width * 0.6f;',
                    'set_fixed_custom(c, h, matrix);\n        return;\n    }\n    int curve = 0;\n    for (int32_t x = 0; x < c->columns; ++x) {\n        float width = c->width;\n        float step = c->step[0];\n        switch (c->type & 0xc) {\n        case 4:\n            width = width * 0.7f;'),
    'create_taper': ('t = t + 0.6f;', 't = t + 0.5f;'),
    'create_y': ('p[1] = 20.0f;', 'p[1] = 10.0f;'),
    'parabola': ('float drop = 10.0f * f;\n                drop = drop * f;\n                p[1] = p[1] - drop;\n                break;',
                 'float drop = 12.0f * f;\n                drop = drop * f;\n                p[1] = p[1] - drop;\n                break;'),
    'spring_diag_row': ('if (yy > 1) {', 'if (yy > 0) {'),
    'spring_min': ('set_spring(c, n++, i, i + 1, d * 0.8f, d, 3);', 'set_spring(c, n++, i, i + 1, d * 0.75f, d, 3);'),
    'spring_flags': ('vertical |= 4;', 'vertical |= 0;'),
    'force_slack': ('if (!(d > s->length + 0.01f))', 'if (!(d > s->length + 0.02f))'),
    'phase_step': ('g->logic_steps / 10;', 'g->logic_steps / 12;'),
    'phase_wrap': ('(int32_t)((uint32_t)q * 101u)', '(int32_t)((uint32_t)q * 100u)'),
    'wind_angle': ('float a = 180.0f + h->angles[2];', 'float a = h->angles[2];'),
    'wind_y': ('const float nw = -c->wind;', 'const float nw = c->wind;'),
    'world_wind': ('g->world == 0x37', 'g->world == 0x38'),
    'uv_clamp': ('t > 0.99f ? 0.99f : t', 't > 0.999f ? 0.999f : t'),
    'back_winding': ('render_vertex(c, sink, x, y + 1);\n                render_vertex(c, sink, x + 1, y + 1);\n                render_vertex(c, sink, x + 1, y);',
                     'render_vertex(c, sink, x + 1, y);\n                render_vertex(c, sink, x + 1, y + 1);\n                render_vertex(c, sink, x, y + 1);'),
    'object_alpha': ('if (c->alpha_from_object && c->owner)', 'if (0)'),
    'wing_texture': ('{0x2382, 0, 19, 0.0f, 16.0f,', '{0x2382, 0, 19, 0.0f, 20.0f,'),
    'sparkle_offset': ('{0.5f, 1.0f}, {1.0f, 0.0f}, 0.1f, -1,', '{0.5f, 1.0f}, {0.5f, 0.0f}, 0.1f, -1,'),
    'black_spheres': ('0x846b, 0x846b, 0x1005,\n     {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4,\n     {{-10.0f, -2.0f, 18.0f, 25.0f, 17}',
                      '0x846b, 0x846b, 0x1005,\n     {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4,\n     {{-10.0f, -2.0f, 18.0f, 26.0f, 17}'),
    # CLOAK-002
    'table_origin': ('{0x2368, 0, 19, 0.0f, 8.0f,', '{0x2368, 0, 19, 0.0f, 8.5f,'),
    'table_sphere': ('{{0.0f, 73.0f, -5.0f, 50.0f, 19}', '{{0.0f, 73.0f, -5.0f, 51.0f, 19}'),
    'table_glow_min': ('0x794e, 3.0f, 0.4f, 1.0f', '0x794e, 3.0f, 0.5f, 1.0f'),
    'alias': ('case 0x2318: case 0x249a: return 0x2318;', 'case 0x2318: return 0x2318;'),
    'glow_level': ('in->wing_level >= d->glow_level', 'in->wing_level > d->glow_level'),
    'glow_state': ('sink->state(sink->context, MU_CLOTH_STATE_BLEND_ONE);\n    sink->bind(sink->context, c->glow_texture);',
                   'sink->state(sink->context, MU_CLOTH_STATE_ALPHA_TEST);\n    sink->bind(sink->context, c->glow_texture);'),
    'glow_formula': ('bright = w * range + c->glow[1];', 'bright = w * range;'),
    'glow_period': ('glow_wave(-c->glow[0], g->time)', 'glow_wave(c->glow[0], g->time)'),
    'glow_cos': ('3.1415927f > x ? -crt_cos(x) : crt_cos(x)', '3.1415927f > x ? crt_cos(x) : -crt_cos(x)'),
    'glow_speed': ('if (c->glow[0] > 0.0f) {', 'if (c->glow[0] > 5.0f) {'),
    'scene': ('if (in->scene == 5)', 'if (in->scene == 6)'),
    'scale_09': ('s = in->object_scale / 0.9f;', 's = in->object_scale / 0.8f;'),
    'scaled_negate': ('mu_cloth_create(&out[2], h, 19, -(s * 15.0f),', 'mu_cloth_create(&out[2], h, 19, (s * 15.0f),'),
    'arg4_back': ('75.0f, 120.0f, 0x790b, 0x790c, 0x405);', '75.0f, 120.0f, 0x790b, 0x790b, 0x405);'),
    'admangto_sphere': ('mu_cloth_add_sphere(&out[0], 0.0f, -10.0f, -40.0f, 37.0f, 17);\n        break;',
                        'mu_cloth_add_sphere(&out[0], 0.0f, -10.0f, -40.0f, 36.0f, 17);\n        break;'),
    'season_bitmap': ('i ? 0x830d : 0x830c;', 'i ? 0x830c : 0x830c;'),
    'season_angles': ('{0.0f, 90.0f, 0.0f};', '{0.0f, 80.0f, 0.0f};'),
    'custom_flag': ('c->custom = 1;', 'c->custom = 0;'),
    'custom_rotate': ('mu_vector_rotate(q, c->matrix, p);', 'mu_vector_rotate(q, matrix, p);'),
    'custom_origin_scale': ('r[k] = scale * rr[k];', 'r[k] = rr[k];'),
    'custom_origin_swizzle': ('o[1] = -oo[1];', 'o[1] = oo[1];'),
    'custom_taper': ('static void set_fixed_custom(mu_cloth *c, const mu_cloth_host *h, const float *matrix)\n{\n    int curve = 0;\n    for (int32_t x = 0; x < c->columns; ++x) {\n        float width = c->width;\n        float step = c->step[0];\n        switch (c->type & 0xc) {\n        case 4:\n            width = width * 0.6f;',
                     'static void set_fixed_custom(mu_cloth *c, const mu_cloth_host *h, const float *matrix)\n{\n    int curve = 0;\n    for (int32_t x = 0; x < c->columns; ++x) {\n        float width = c->width;\n        float step = c->step[0];\n        switch (c->type & 0xc) {\n        case 4:\n            width = width * 0.7f;'),
    'sub_model': ('if (h->subtype == 0x5bc || h->subtype == 0x5bd) {', 'if (h->subtype == 0x5bc) {'),
    'draw_subtype': ('if (subtype == 0x431 || subtype == 0x432)', 'if (subtype == 0x432)'),
    'draw_skin3': ('if (skin_index(class_byte) != 3)', 'if (skin_index(class_byte) != 4)'),
    'force_8000': ('t = t * 0.8f;\n        v->force[0] = -t + v->force[0];', 't = t * 0.7f;\n        v->force[0] = -t + v->force[0];'),
    'gravity_180': ('(type & 0xc00) == 0x400 ? 180.0f : 100.0f', '(type & 0xc00) == 0x400 ? 170.0f : 100.0f'),
    'wind_clamp': ('(-0.2f > g->wind ? -0.2f : g->wind) : 1.0f', '(-0.3f > g->wind ? -0.3f : g->wind) : 1.0f'),
    'gate_class': ('base == 0xd ||', 'base == 0xe ||'),
    'gate_c0e': ('if (in->c_0e == 0 || (in->c_0e == 1 && in->own_type == 0xa91))', 'if (in->c_0e == 0 || in->c_0e == 2)'),
    'gate_world': ("in->world == 0x35 || in->world == 0x61", "in->world == 0x35"),
    'gate_pk': ('out->light[1] = 0.1f;', 'out->light[1] = 0.2f;'),
    'gate_glow': ('if (index >= 0x211 && index <= 0x21b)', 'if (index >= 0x211 && index <= 0x215)'),
}


def families(world_args, lib, args, only=None):
    """only: 'cloth' (create, step, render), 'wind' or 'gate' (a mutant runs the family that compares its code)."""
    fam = {k: new_family() for k in ('create', 'step', 'render', 'wind', 'gate')}
    if only in (None, 'cloth'):
        run_cases(world_args, lib, args.cases, args.frames, args.seed, fam)
    if only in (None, 'wind'):
        wind_family(world_args, lib, args.wind_cases, args.seed, fam['wind'])
    if only in (None, 'gate'):
        gate_family(world_args, lib, args.gate_cases, args.seed, fam['gate'])
    return fam


def mutations(world_args, args, work):
    source = (DIR / 'cloth.c').read_text()
    results = {}
    small = argparse.Namespace(cases=args.cases, frames=args.frames, seed=args.seed, wind_cases=args.wind_cases,
                               gate_cases=args.gate_cases)   # the full sets; each run stops at its first mismatch
    for name, (old, new) in MUTANTS.items():
        count = source.count(old)
        if count != 1:
            raise SystemExit(f'mutant {name}: anchor matches {count} times, expected exactly once')
        mdir = work / f'm_{name}'
        mdir.mkdir()
        (mdir / 'cloth.c').write_text(source.replace(old, new))
        shutil.copy(DIR / 'cloth.h', mdir / 'cloth.h')
        (work / 'record-math').mkdir(exist_ok=True)
        shutil.copy(ROOT / 'reconstructed/record-math/record_math.h', work / 'record-math/record_math.h')
        lib, error = build(mdir, work, f'm_{name}')
        if lib is None:
            raise SystemExit(f'mutant {name} does not compile: {error}')
        STOP['early'] = True
        try:
            only = 'gate' if name.startswith('gate_') else 'wind' if name.startswith('wind_clamp') else 'cloth'
            fam = families(world_args, lib, small, only)
            results[name] = sum(f['mismatches'] for f in fam.values())
        except Caught:
            results[name] = 1
        finally:
            STOP['early'] = False
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=278, help='characters (create cases); each runs --frames frames')
    parser.add_argument('--frames', type=int, default=8)
    parser.add_argument('--wind-cases', type=int, default=200)
    parser.add_argument('--gate-cases', type=int, default=768)
    parser.add_argument('--seed', type=int, default=0x2382)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--text')
    parser.add_argument('--data')
    parser.add_argument('--flag', help='captured trig dispatch flag 0x0bdd1cc8')
    parser.add_argument('--feature', help='captured math feature word 0x01cf6618')
    parser.add_argument('--section3', help='initialized section-3 bytes (the gravity constants at 0x01cf0eb0)')
    args = parser.parse_args(argv)
    text = pins.TEXT.read(args.text, exit=True)
    data = pins.DATA.read(args.data, exit=True)
    flag = pins.FLAG.read(args.flag, exit=True)
    feature = pins.FEATURE.read(args.feature, exit=True)
    world_args = (text, data, flag, feature)
    SECTION3_INIT['bytes'] = pins.EFFECTS_INIT.read(args.section3, exit=True)
    import hashlib
    work = Path(tempfile.mkdtemp(prefix='item-cloak-'))
    started = clock.time()
    try:
        lib, error = build(DIR, work, 'cloth')
        if lib is None:
            raise SystemExit(error)
        report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                  'section3_init_sha256': pins.EFFECTS_INIT.sha256,
                  'gravity': list(struct.unpack('<3f', SECTION3_INIT['bytes'][GRAVITY - pins.EFFECTS_INIT.base:][:12])),
                  'routines': {k: [hex(a), hex(b), hashlib.sha256(text[a - rmach.TEXT_BASE:b - rmach.TEXT_BASE]).hexdigest()]
                               for k, (a, b) in RANGES.items()},
                  'families': families(world_args, lib, args), 'coverage': dict(COVERAGE)}
        if args.mutations:
            report['mutants'] = mutations(world_args, args, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    report['seconds'] = round(clock.time() - started, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + '\n')
    bad = sum(f['mismatches'] for f in report['families'].values())
    stopped = sum(f['stopped'] for f in report['families'].values())
    missed = [k for k, v in report.get('mutants', {}).items() if not v]
    summary = {k: {'cases': v['cases'], 'mismatches': v['mismatches'], 'stopped': v['stopped']}
               for k, v in report['families'].items()}
    print(json.dumps({'families': summary, 'coverage': report['coverage'], 'mutants': report.get('mutants'),
                      'seconds': report['seconds']}))
    return 1 if bad or stopped or missed else 0


if __name__ == '__main__':
    sys.exit(main())
