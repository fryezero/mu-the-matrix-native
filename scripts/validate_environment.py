#!/usr/bin/env python3
"""Compare the authored environment routines with the client (NATIVE-ENV-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case).
Each case is a world session: the boid, fish and leaf arrays start dead (or
fuzzed), the hero walks, and for every 40 ms logic step the client's

  MoveLeaves 0x01537a43 (this = 0x0a3a0e28), MoveBoids 0x00c9eb04,
  MoveFishs 0x00ca05b3

run in the tick's order, and every few steps the render routines

  RenderBoids 0x00c9fd8d(0), RenderBoids(1), RenderFishs 0x00ca1cf7,
  RenderLeaves 0x01538145

on the same client memory. The authored C (reconstructed/environment,
libclient_env with its deterministic test host) runs the same steps. After
every step the rand() state and call count, the modelled bytes of the 40
boids, 10 fishs, 200 leaves, the leaf trailer (+0x8ca0..+0x8cb0) and the
Tormenta world object, and the ordered log of host calls must be equal.

Client code includes every routine the steps reach, the world predicates,
TileIndex, SetLive 0x0129f4a5, ObjectInit 0x0129eb81, FadeAlpha 0x012af883,
the flock 0x012af9a9 with CreateAngle/TurnAngle, AngleMatrix, VectorRotate,
VectorTransform, the CRT sin/cos/sqrt/atan (trig flag 1), RenderPlane3D
0x0184c121 and RenderSprite 0x0184c39c. Stubs (recording) stand for engine
services: rand() (MSVC LCG), RequestTerrainHeight and TestFrustrum2D
(synthetic answers shared with the C test host), SND_Play, SetAction (four
actions per model), the model getter, the animation tick, CreateParticle,
the effect factory, CreateSprite, TransformPosition, RenderObject,
RenderBodyShadow, the GL state wrappers and bind, the GL imports, FindTexture,
the bitmap record of RenderSprite, the list helpers of ObjectInit and of
SetLive's cleanup, memset, and the event-world leaf handlers (which return 0
outside their worlds). The world manager's leaf calls are redirected to the
Tormenta class methods 0x00e5377c/0x00e538ec in world 0x8d.

Negative controls: library builds with one planted mistake each
(-DMU_ENV_MUTATION=n) must disagree with the client.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

MOVE_LEAVES, MOVE_BOIDS, MOVE_FISHS = 0x01537a43, 0x00c9eb04, 0x00ca05b3
RENDER_BOIDS, RENDER_FISHS, RENDER_LEAVES = 0x00c9fd8d, 0x00ca1cf7, 0x01538145
BOIDS, FISHS, LEAVES = 0x0bdb71f0, 0x0bdc0bb0, 0x0a3a0e28
OBJ, LEAF = 0x3d8, 0xb4
LEAVES_BYTES = 200*LEAF + 0x14
HERO_PTR, HERO = 0x0a39d754, 0x22000000
WORLD, LOGIN, EVENT, TIME, DT = 0x01cf15fc, 0x01ec3254, 0x06fc9eb4, 0x06fce370, 0x01cf103c
ATTRIBUTES, LAYER1 = 0x0b795420, 0x0b735420
CAMERA, CAMERA_MATRIX = 0x0bdc5ab4, 0x0bdc5918
TRIG_FLAG, CRT_MATH_MODE, COOKIE = 0x0bdd1cc8, 0x0bdcfbc8, 0x01cf65c0
TORMENTA, BMD, CONTAINER, BITMAP_RECORD, MANAGER = 0x23000000, 0x24000000, 0x24100000, 0x24200000, 0x24300000
BONES = 0x06fce398
SCRATCH = 0x7ffb0000      # code page: fld dword ptr [SCRATCH+0x100]; ret
FLD_RET = SCRATCH
SCRATCH_FLOAT = SCRATCH + 0x100

RAND, TERRAIN, FRUSTUM, SND_PLAY, SET_ACTION = 0x01989721, 0x016cc9e2, 0x016ccce7, 0x00a6ac96, 0x012affa4
MODEL_CONTAINER, MODEL_GET, ANIMATE = 0x00966cc4, 0x00eaa8cf, 0x012b4dd3
KILL_CLEANUP, INIT, INIT_HELPER_1, INIT_HELPER_2, MEMSET = 0x009b0451, 0x0129eb81, 0x0129f484, 0x009fe607, 0x0194cd00
PARTICLE, EFFECT, SPRITE, BONE, RENDER_OBJECT, SHADOW = 0x0168fafd, 0x0153b02c, 0x01692eb7, 0x012b6ef1, 0x016d4fe4, \
    0x012bc07a
ALPHA_TEST, ALPHA_BLEND, BIND, FIND_TEXTURE, BITMAP_INFO = 0x0184a990, 0x0184aa2b, 0x0184acf6, 0x00c97ce3, 0x00ebbec8
OPEN_MONSTER = 0x0180b0f4
WM_GET, WM_CREATE, WM_MOVE, WM_RENDER = 0x00ea594b, 0x00ea32c9, 0x00ea340c, 0x00ea354f
TORMENTA_CREATE, TORMENTA_MOVE = 0x00e5377c, 0x00e538ec
LEAF_HANDLERS_CDECL = (0x00d8cea8, 0x00e004d3, 0x00d6a5b3, 0x00db36d6)
LEAF_GETTERS = (0x00d53c8f, 0x0153b001, 0x0153af80, 0x0153afab, 0x0153af2a, 0x0153af55, 0x0153afd6)
LEAF_METHODS = (0x00d5537c, 0x00e6e6a8, 0x00e1fdf2, 0x00e45a03, 0x00d837b0, 0x00d998d2, 0x00e74055)
GL_SLOTS = {'glColor4f': (0x1a7c754, 16), 'glColor3f': (0x1a7c76c, 12), 'glPushMatrix': (0x1a7c718, 0),
            'glPopMatrix': (0x1a7c72c, 0), 'glTranslatef': (0x1a7c698, 12), 'glBegin': (0x1a7c750, 4),
            'glEnd': (0x1a7c760, 0), 'glTexCoord2f': (0x1a7c774, 8), 'glVertex3fv': (0x1a7c778, 4),
            'glColor3fv': (0x1a7c770, 4)}

BODIES = {  # start, exclusive end, SHA-256 of the captured bytes
    'move_leaves': (0x01537a43, 0x01538145, '7e21275abc370bdd2d19b0b364b48c3b6e98cdb29a8e6e5f4314e0b2dd16977b'),
    'render_leaves': (0x01538145, 0x01538c67, 'db402036061ba7e9eebc4d1e4f7ada614f65f23a70b8ec1f64899cb9f5c7ff26'),
    'move_boids': (0x00c9eb04, 0x00c9fd8d, '830d6366bebaf56569b534fca82118490d27ec858b8b18ae43cff185e151671e'),
    'render_boids': (0x00c9fd8d, 0x00ca057d, '09a376e738e3a898164224bda1aab8bb43f2fb5e67cce26c9216cfe22c279c45'),
    'move_fishs': (0x00ca05b3, 0x00ca1cf7, 'c9954912dabcd0379ed55a196138af48bbb7ced5f515a6ad7cafed6371fb0fd6'),
    'render_fishs': (0x00ca1cf7, 0x00ca1fb7, '3ba846ca97a1dd16929645c8a0c8d659e8d7f98921b0645e6c9406a4b5775e6c'),
    'create_lorencia': (0x0153959d, 0x015398de, '6b483e1936861ab660a9b4afeb2e92f105919bf509689b877ef28e9bc7329a58'),
    'create_icarus': (0x015398de, 0x01539ace, '64810789787cb396f06b7bba6f17428e8272630a4ace1847939738a260e490f9'),
    'create_devias': (0x0153939c, 0x0153959d, '4daf73986cfb11f37e4bd08382d735cf2da0bf4ee5d6c7d3947db44ff016a82a'),
    'create_noria': (0x01539ace, 0x01539e22, 'b200eadf292d82c2febd6d8ddaf7f72aa872b67c990a109ddf8d0d1424e2637e'),
    'move_lorencia': (0x0153a634, 0x0153ac06, '7db5c1819df9031d4edf1da0375b7d97e8ca9cfc3e48435136ed1d139b55aa2f'),
    'move_default': (0x0153ac06, 0x0153ae88, '1e483f0c5a6710c4f80d6c1226c1d047a4ae7078d5abe60a1fd4b98f74dd785a'),
    'tormenta_create': (0x00e5377c, 0x00e538df, '7b72aaff27b84f37ed594f55dc62d148e996364cb5d7e9b87f4b906b87d64434'),
    'tormenta_move': (0x00e538ec, 0x00e53b8d, 'ea5c9a6815e904f1db285f3cb9ed5af7a0f3a9f0ebe7cbe2ea23138a9fca5087'),
    'tormenta_drop': (0x00e53c14, 0x00e54061, '5980fae6d0dcc3562bdc4cd1b0e5c297fc8e3faa6d37b356122f00660acf59cd'),
    'shoal': (0x00ca27b1, 0x00ca2acd, '286816131638755c327d375f79a688f7949882e9d6a00dff3b81dc07a9ad057e'),
    'bat': (0x00ca2acd, 0x00ca2ba7, 'f1977135250b007ff7acdf69aed03fc4463e622bc779b8b17c789f198eaed452'),
    'butterfly': (0x00ca2ba7, 0x00ca2dcb, '4541eb6c1d450618ce3d7bfbe1306a189fdcf6fbe7c540ba11b08ec2da688627'),
    'bird': (0x00ca2dcb, 0x00ca3189, '339b26272217c98ec61027ffa61a462b57c6acdf4ea9863715ff8c3387a79c2e'),
    'flight': (0x00ca3e2f, 0x00ca4302, '203315d957cabb990e3b22976f852afe581cd315265512583b6cd629153bff26'),
    'flock': (0x012af9a9, 0x012afd99, 'e3df276b038e936765b9dbb25a064ee0fcd7d8ce425369eebdc02cf21e4fb8af'),
    'create_angle': (0x012aeced, 0x012aed9e, '010f6e0113597646c3e38eba34eabd5848b34a734d0093e50d6391ed29319bd3'),
    'turn_angle': (0x012aef0c, 0x012aefff, '3bac17cdda59629c8022798a70ae92517c9089fe30f3f7032c8849bd92f87c12'),
    'fade_alpha': (0x012af883, 0x012af9a9, 'b94e3e222018f1913a91354b3f46f95e29f89efb1cd0f22aa3b86ff44b34b7b4'),
    'object_init': (0x0129eb81, 0x0129f06f, '9a692bd1d8eb0b1e54e8b830c93984659bb36c3a2707006e301ec5706d7a737c'),
    'set_live': (0x0129f4a5, 0x0129f4cb, 'c48b729d8674333ab9777cc99a99a3f5db5c1c3798f7ea60568d1ff978e2273f'),
    'plane': (0x0184c121, 0x0184c39c, '4a5187cdddcc2476f94cc3e3742121af07988d1c0cf9378b7074130aa324866b'),
    'sprite_quad': (0x0184c39c, 0x0184ca6b, '586804808932d8d349c17229244ce36db2f402111c14b9e8732b14c09167f7ac'),
}

PROBES = {  # branch probes (address: label); every one must be reached
    0x00c9f1b0: 'boids: spawn', 0x00c9f292: 'boids: bird', 0x00c9f2b3: 'boids: bat (1, 4)',
    0x00c9f2c8: 'boids: butterfly', 0x00c9f359: 'boids: crow', 0x00c9f410: 'boids: bat (deep dungeon)',
    0x00c9f438: 'boids: shoal creator', 0x00c9f460: 'boids: common setup', 0x00c9fb47: 'boids: Atlans turn',
    0x00c9fbf0: 'boids: subtype kill', 0x00c9fcce: 'boids: aBird1', 0x00c9fcf4: 'boids: aBird2',
    0x00c9fd28: 'boids: aBat', 0x00c9fd6a: 'boids: crow sound', 0x00c9f687: 'boids: model missing',
    0x00ca2f0b: 'bird: land', 0x00ca3056: 'bird: touch down', 0x00ca30c9: 'bird: take off',
    0x00ca317f: 'bird: fly again', 0x00ca2f7b: 'bird: below 200', 0x00ca2fb6: 'bird: above 600',
    0x00ca2bc2: 'butterfly: new heading', 0x00ca2cc4: 'butterfly: low', 0x00ca2d3c: 'butterfly: high',
    0x00ca3eb2: 'flight: Atlans', 0x00ca3f2b: 'flight: index >= 35', 0x00ca3f99: 'flight: phase >= 5',
    0x00ca4037: 'flight: phase wrap', 0x00ca42de: 'flight: random kill', 0x00ca42f4: 'flight: range kill',
    0x012afb6b: 'flock: near', 0x012afbdd: 'flock: far', 0x012afcaa: 'flock: steer',
    0x00ca2815: 'shoal: create', 0x00ca28b2: 'shoal: scale 0.25', 0x00ca2abc: 'shoal: north kill',
    0x00ca0921: 'fishs: spawn', 0x00ca0b4e: 'fishs: Lorencia fish', 0x00ca0ba5: 'fishs: rat',
    0x00ca0bff: 'fishs: effect fish', 0x00ca0d57: 'fishs: world 0x22', 0x00ca0eac: 'fishs: 0x22 safe kill',
    0x00ca0ebc: 'fishs: Atlans', 0x00ca0f8f: 'fishs: Atlans north', 0x00ca10e8: 'fishs: abyss',
    0x00ca12d9: 'fishs: 0x85', 0x00ca13f8: 'fishs: Kalima', 0x00ca1582: 'fishs: 0x19f wave',
    0x00ca160a: 'fishs: action 1', 0x00ca192b: 'fishs: wall turn', 0x00ca1a72: 'fishs: turn',
    0x00ca1af9: 'fishs: subtype down', 0x00ca1b0f: 'fishs: subtype kill', 0x00ca1c3d: 'fishs: range kill',
    0x00ca1c79: 'fishs: rat sound', 0x00ca1c8a: 'fishs: other action', 0x00ca1ccf: 'fishs: timer reset',
    0x01537a8b: 'leaves: Icarus target', 0x01537cce: 'leaves: rain down', 0x01537cf7: 'leaves: rain up',
    0x01537de1: 'leaves: dead leaf', 0x01539775: 'leaves: Lorencia camera rule',
    0x01539cb9: 'leaves: Noria camera rule', 0x015393df: 'leaves: big flake', 0x01539926: 'leaves: Icarus rain',
    0x0153a673: 'leaves: rain move', 0x0153a783: 'leaves: rain ground', 0x0153abf8: 'leaves: drift kill',
    0x0153ac63: 'leaves: ground', 0x0153ad00: 'leaves: faded', 0x0153ad0c: 'leaves: air',
    0x00e537d1: 'Tormenta: rain rises', 0x00e5382d: 'Tormenta: rain falls', 0x00e538b3: 'Tormenta: no rain',
    0x00e538cd: 'Tormenta: drop', 0x00e53ee8: 'Tormenta: drop kept', 0x00e53f3e: 'Tormenta: drop lands',
    0x00e53f82: 'Tormenta: splash', 0x00e53fcc: 'Tormenta: ring', 0x00e53af8: 'Tormenta: ground',
    0x00e53b7f: 'Tormenta: faded',
    0x0153835b: 'render leaves: blend', 0x015383d9: 'render leaves: alpha test',
    0x01538603: 'render leaves: billboard', 0x01538894: 'render leaves: 0x84', 0x01538ab4: 'render leaves: plane',
    0x01538bbb: 'render leaves: rain plane', 0x01538c2f: 'render leaves: leaf plane',
    0x00c9fe93: 'render boids: object', 0x00ca00ca: 'render boids: glow', 0x00ca01dc: 'render boids: crow eyes',
    0x00ca044c: 'render boids: shadow', 0x00ca1ddc: 'render fishs: object', 0x00ca1e92: 'render fishs: shadow',
}

STEP_LEAVES, STEP_BOIDS, STEP_FISHS, STEP_RB0, STEP_RB1, STEP_RF, STEP_RL = 1, 2, 3, 4, 5, 6, 7
STEP_NAMES = {1: 'move_leaves', 2: 'move_boids', 3: 'move_fishs', 4: 'render_boids_0', 5: 'render_boids_1',
              6: 'render_fishs', 7: 'render_leaves'}
BOID_WORLDS = [0, 1, 3, 4, 7, 0x80, 0x81, 0x82, 11, 15, 52, 0x74, 0x77, 24, 36, 2, 0x8d]
FISH_WORLDS = [0, 1, 4, 6, 7, 0x74, 0x80, 0x82, 0x85, 8, 0x21, 0x36, 0x86, 0x22, 24, 2, 3, 0x8d]
LEAF_WORLDS = [0, 2, 3, 7, 0x80, 0x81, 0x8d, 0xa, 0x84]
TARGET_WORLDS = [0, 1, 2, 3, 7, 0x8d]


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def from_bits(b):
    return struct.unpack('<f', struct.pack('<I', b & 0xffffffff))[0]


def mix(a, b):
    m = ((a * 0x9e3779b1) ^ (b * 0x85ebca77)) & 0xffffffff
    m ^= m >> 15
    m = (m * 0x2c1b3c6d) & 0xffffffff
    m ^= m >> 12
    return m


def test_height(case, x, y):
    m = mix(bits(x) >> case['height_shift'], bits(y) >> case['height_shift'])
    return f32(case['height_base'] + float(m % case['height_span']))


# --------------------------------------------------------------------------
# Library.

class Event(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int32), ('a', ctypes.c_int32), ('b', ctypes.c_int32), ('c', ctypes.c_int32),
                ('f', ctypes.c_float * 16)]


class Inputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('hero_position', ctypes.c_float * 3), ('hero_tile', ctypes.c_int32 * 2),
                ('hero_action', ctypes.c_uint16), ('hero_safe_zone', ctypes.c_uint8),
                ('camera_position', ctypes.c_float * 3), ('world_time', ctypes.c_float),
                ('frame_time', ctypes.c_float), ('event_state', ctypes.c_int32), ('login_scene', ctypes.c_int32),
                ('attributes', ctypes.c_void_p), ('layer1', ctypes.c_void_p)]


class Library:
    def __init__(self, path):
        self.lib = lib = ctypes.CDLL(str(path))
        lib.mu_env_test_new.argtypes = [ctypes.c_uint32]
        lib.mu_env_test_new.restype = ctypes.c_void_p
        lib.mu_env_test_free.argtypes = [ctypes.c_void_p]
        for name in ('mu_env_test_env', 'mu_env_test_host_of', 'mu_env_test_inputs'):
            getattr(lib, name).argtypes = [ctypes.c_void_p]
            getattr(lib, name).restype = ctypes.c_void_p
        lib.mu_env_test_run.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        lib.mu_env_test_clear_events.argtypes = [ctypes.c_void_p]
        lib.mu_env_test_store.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.mu_env_test_load.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.mu_env_object_mask.argtypes = [ctypes.c_char_p]
        lib.mu_env_leaf_mask.argtypes = [ctypes.c_char_p]
        lib.mu_env_billboard_quad.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float,
                                              ctypes.c_void_p]
        lib.mu_env_billboard_color.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p]
        lib.mu_env_billboard_color.restype = ctypes.c_int
        m = ctypes.create_string_buffer(OBJ)
        lib.mu_env_object_mask(m)
        self.object_mask = bytes(m.raw)
        m = ctypes.create_string_buffer(LEAF)
        lib.mu_env_leaf_mask(m)
        self.leaf_mask = bytes(m.raw)
        lib.mu_env_test_offset.argtypes = [ctypes.c_int32]
        lib.mu_env_test_offset.restype = ctypes.c_int32
        names = {0: 'rand_state', 1: 'rand_calls', 2: 'rain_target', 3: 'rain_level', 4: 'wind_8ca8',
                 5: 'wind_8cac', 6: 'wind_8cb0', 7: 'tormenta', 8: 'tormenta_max', 9: 'tormenta_rain',
                 20: 'height_base', 21: 'height_span', 22: 'height_shift', 23: 'frustum_mask',
                 24: 'missing_models', 25: 'missing_model', 26: 'missing_bitmaps', 27: 'missing_bitmap',
                 28: 'count', 29: 'events', 30: 'event_size'}
        self.off = {n: lib.mu_env_test_offset(k) for k, n in names.items()}
        assert self.off['event_size'] == ctypes.sizeof(Event)


class NativeSession:
    """libclient_env with its test host, driven like the client."""

    def __init__(self, library, case):
        self.L = library
        lib = library.lib
        self.h = lib.mu_env_test_new(case['seed'] & 0xffffffff)
        self.env = lib.mu_env_test_env(self.h)
        self.host = lib.mu_env_test_host_of(self.h)
        self.inputs = Inputs.from_address(lib.mu_env_test_inputs(self.h))
        self.attributes = ctypes.create_string_buffer(case['attributes'], len(case['attributes']))
        self.layer1 = ctypes.create_string_buffer(case['layer1'], len(case['layer1']))
        self.inputs.attributes = ctypes.cast(self.attributes, ctypes.c_void_p).value
        self.inputs.layer1 = ctypes.cast(self.layer1, ctypes.c_void_p).value
        # test host parameters: env pointer, height_base, height_span, height_shift, frustum_mask, missing...
        host, o = self.host, library.off
        ctypes.c_float.from_address(host + o['height_base']).value = case['height_base']
        ctypes.c_int32.from_address(host + o['height_span']).value = case['height_span']
        ctypes.c_int32.from_address(host + o['height_shift']).value = case['height_shift']
        ctypes.c_int32.from_address(host + o['frustum_mask']).value = 3
        ctypes.c_int32.from_address(host + o['missing_models']).value = len(case['missing_models'])
        for i, model in enumerate(case['missing_models']):
            ctypes.c_int32.from_address(host + o['missing_model'] + 4*i).value = model
        ctypes.c_int32.from_address(host + o['missing_bitmaps']).value = len(case['missing_bitmaps'])
        for i, bitmap in enumerate(case['missing_bitmaps']):
            ctypes.c_int32.from_address(host + o['missing_bitmap'] + 4*i).value = bitmap
        lib.mu_env_test_load(self.h, case['boids'], case['fishs'], case['leaves'])
        self.set_trailer(case['trailer'])
        self.set_tormenta(case['tormenta'])

    def close(self):
        self.L.lib.mu_env_test_free(self.h)

    def set_inputs(self, s):
        i = self.inputs
        i.world = s['world']
        for k in range(3):
            i.hero_position[k] = s['hero'][k]
            i.camera_position[k] = s['camera'][k]
        i.hero_tile[0], i.hero_tile[1] = s['hero_tile']
        i.hero_action = s['hero_action']
        i.hero_safe_zone = s['safe']
        i.world_time = s['time']
        i.frame_time = f32(0.1)
        i.event_state = s['event']
        i.login_scene = 0

    TRAILER = ('rain_target', 'rain_level', 'wind_8ca8', 'wind_8cac', 'wind_8cb0')

    def set_trailer(self, trailer):
        for name, value in zip(self.TRAILER, trailer):
            ctypes.c_int32.from_address(self.env + self.L.off[name]).value = value

    def set_tormenta(self, t):
        o = self.L.off
        ctypes.c_uint8.from_address(self.env + o['tormenta']).value = t[0]
        ctypes.c_float.from_address(self.env + o['tormenta_max']).value = t[1]
        ctypes.c_float.from_address(self.env + o['tormenta_rain']).value = t[2]

    def state(self):
        lib = self.L.lib
        boids = ctypes.create_string_buffer(40*OBJ)
        fishs = ctypes.create_string_buffer(10*OBJ)
        leaves = ctypes.create_string_buffer(200*LEAF)
        lib.mu_env_test_store(self.h, boids, fishs, leaves)
        o = self.L.off
        trailer = tuple(ctypes.c_int32.from_address(self.env + o[n]).value for n in self.TRAILER)
        tormenta = (ctypes.c_uint8.from_address(self.env + o['tormenta']).value,
                    bits(ctypes.c_float.from_address(self.env + o['tormenta_max']).value),
                    bits(ctypes.c_float.from_address(self.env + o['tormenta_rain']).value))
        return {'rand_state': ctypes.c_uint32.from_address(self.env + o['rand_state']).value,
                'rand_calls': ctypes.c_uint64.from_address(self.env + o['rand_calls']).value,
                'boids': boids.raw, 'fishs': fishs.raw, 'leaves': leaves.raw, 'trailer': trailer,
                'tormenta': tormenta}

    def run(self, step):
        lib = self.L.lib
        lib.mu_env_test_clear_events(self.h)
        lib.mu_env_test_run(self.h, step)
        count = ctypes.c_int32.from_address(self.host + self.L.off['count']).value
        events = (Event * 8192).from_address(self.host + self.L.off['events'])
        return [events[i] for i in range(count)]


# --------------------------------------------------------------------------
# Client side.

class EnvMachine(am.ActorMachine):
    """ActorMachine with import stubs, observers and redirecting stubs."""

    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_READ, UC_PROT_EXEC, UC_PROT_WRITE
        self.uc.mem_map(SCRATCH, am.PAGE, UC_PROT_READ | UC_PROT_EXEC | UC_PROT_WRITE)
        self.uc.mem_write(FLD_RET, bytes([0xd9, 0x05]) + struct.pack('<I', SCRATCH_FLOAT) + b'\xc3')
        self.gl_targets = {}
        pages = set()
        for name, (slot, cleanup) in GL_SLOTS.items():
            target = struct.unpack('<I', data[slot-am.DATA_BASE:slot-am.DATA_BASE+4])[0]
            self.gl_targets[target] = (name, cleanup)
            pages.add(target & ~0xfff)
        for page in sorted(pages):
            self.uc.mem_map(page, am.PAGE, UC_PROT_READ | UC_PROT_EXEC)
            self.uc.mem_write(page, b'\xcc'*am.PAGE)
        self.observers = {}
        self.observer_hooks = {}
        self.probe_hits = {a: 0 for a in PROBES}
        for address in PROBES:
            self.uc.hook_add(self.UC_HOOK_CODE, self._probe, begin=address, end=address)

    def _probe(self, uc, address, size, ignored):
        self.probe_hits[address] += 1

    def access(self, uc, access, address, size, value, regions):
        if access == self.UC_MEM_WRITE:
            for region in regions:
                written = getattr(region, 'written', None)
                if written is not None and region.base <= address and address+size <= region.end:
                    off = address-region.base
                    written[off:off+size] = b'\1'*size
                    break
        super().access(uc, access, address, size, value, regions)

    def observe(self, address, handler):
        self.observers[address] = handler
        if address not in self.observer_hooks:
            self.observer_hooks[address] = self.uc.hook_add(self.UC_HOOK_CODE, self._observed, begin=address,
                                                            end=address)
            self.uc.ctl_flush_tb()

    def _observed(self, uc, address, size, ignored):
        handler = self.observers.get(address)
        if handler and address not in self.stubs:
            handler(self)

    def stub_entry(self, uc, address, size, ignored):
        handler = self.stubs.get(address)
        if handler is None:
            return
        x86 = self.x86
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret = self.read32(esp)
        try:
            result = handler(self)
        except Exception as failure:
            self.stop(('stub-error', hex(address), repr(failure)))
            return
        if self.state['stopped'] is not None:
            return
        if isinstance(result, tuple) and result and result[0] == 'jump':
            _, target, ecx = result
            if ecx is not None:
                uc.reg_write(x86.UC_X86_REG_ECX, ecx)
            uc.reg_write(x86.UC_X86_REG_EIP, target)
            return
        eax, cleanup = result if isinstance(result, tuple) else (result, 0)
        uc.reg_write(x86.UC_X86_REG_EAX, eax & 0xffffffff)
        uc.reg_write(x86.UC_X86_REG_ESP, esp+4+cleanup)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def float_argument(self, index):
        return from_bits(self.argument(index))

    def read_floats(self, address, count):
        return struct.unpack(f'<{count}f', bytes(self.uc.mem_read(address, 4*count)))

    def return_float(self, value):
        self.uc.mem_write(SCRATCH_FLOAT, struct.pack('<f', value))
        return ('jump', FLD_RET, None)


def object_index(address):
    if BOIDS <= address < BOIDS + 40*OBJ and (address - BOIDS) % OBJ == 0:
        return (address - BOIDS)//OBJ
    if FISHS <= address < FISHS + 10*OBJ and (address - FISHS) % OBJ == 0:
        return 100 + (address - FISHS)//OBJ
    return -2 if address else -1


def object_base(index):
    return BOIDS + index*OBJ if index < 100 else FISHS + (index - 100)*OBJ


class Client:
    """The client's memory for one case and the stubs that answer it."""

    def __init__(self, machine, library, case):
        self.m, self.L, self.case = machine, library, case
        self.rand_state, self.rand_calls = case['seed'] & 0xffffffff, 0
        self.log = []
        self.in_init = 0
        om, lm = library.object_mask, library.leaf_mask
        self.boids = am.Region('boids', BOIDS, am.poison(40*OBJ, 0x31), bytes(40*OBJ))
        self.fishs = am.Region('fishs', FISHS, am.poison(10*OBJ, 0x32), bytes(10*OBJ))
        self.leaves = am.Region('leaves', LEAVES, am.poison(LEAVES_BYTES, 0x33), bytes(LEAVES_BYTES))
        for i in range(40):
            self._define_masked(self.boids, BOIDS + i*OBJ, case['boids'][i*OBJ:(i+1)*OBJ], om)
        for i in range(10):
            self._define_masked(self.fishs, FISHS + i*OBJ, case['fishs'][i*OBJ:(i+1)*OBJ], om)
        for i in range(200):
            self._define_masked(self.leaves, LEAVES + i*LEAF, case['leaves'][i*LEAF:(i+1)*LEAF], lm)
        self.leaves.define(LEAVES + 0x8ca0, struct.pack('<5i', *case['trailer']))
        self.hero = am.undefined_region('hero', HERO, 0x3400)
        self.tormenta = am.undefined_region('tormenta', TORMENTA, 0x40)
        t = case['tormenta']
        self.tormenta.define(TORMENTA + 6, bytes([t[0]]))
        self.tormenta.define(TORMENTA + 0x14, struct.pack('<ff', t[1], t[2]))
        self.bmd = am.undefined_region('model', BMD, 0x100)
        self.bitmap_record = am.undefined_region('bitmap-record', BITMAP_RECORD, 0x300)
        self.bitmap_record.define(BITMAP_RECORD + 0x214, bytes([case['bitmap_components']]))
        self.camera_matrix = am.defined_region('camera-matrix', CAMERA_MATRIX,
                                               struct.pack('<12f', *case['camera_matrix']), writable=False)
        self.static = [
            am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False),
            am.defined_region('login', LOGIN, struct.pack('<i', 0), writable=False),
            am.defined_region('dt', DT, struct.pack('<f', 0.1), writable=False),
            am.defined_region('attributes', ATTRIBUTES, case['attributes'], writable=False),
            am.defined_region('layer1', LAYER1, case['layer1'], writable=False),
            am.defined_region('trig-flag', TRIG_FLAG, struct.pack('<I', 1), writable=False),
            am.defined_region('crt-mode', CRT_MATH_MODE, struct.pack('<I', case['crt_mode']), writable=False),
            am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
            self.camera_matrix,
        ]

    @staticmethod
    def _define_masked(region, base, payload, mask):
        for k in range(len(mask)):
            if mask[k]:
                region.define(base + k, payload[k:k+1])

    def regions(self, s):
        dynamic = [
            am.defined_region('world', WORLD, struct.pack('<i', s['world']), writable=False),
            am.defined_region('event', EVENT, struct.pack('<i', s['event']), writable=False),
            am.defined_region('time', TIME, struct.pack('<f', s['time']), writable=False),
            am.defined_region('camera', CAMERA, struct.pack('<3f', *s['camera']), writable=False),
        ]
        h = self.hero
        h.define(HERO + 4, bytes([s['safe']]))
        h.define(HERO + 0x180, struct.pack('<ii', *s['hero_tile']))
        h.define(HERO + 0x33ac, struct.pack('<3f', *s['hero']))
        h.define(HERO + 0x3254 + 0x2a, struct.pack('<H', s['hero_action']))
        return [*self.static, *dynamic, self.boids, self.fishs, self.leaves, h, self.tormenta, self.bmd,
                self.bitmap_record]

    # ---- stubs ----
    def stubs(self, s):
        case, log = self.case, self.log

        def rand(m):
            self.rand_state = (self.rand_state * 214013 + 2531011) & 0xffffffff
            self.rand_calls += 1
            return (self.rand_state >> 16) & 0x7fff

        def terrain(m):
            return m.return_float(test_height(case, m.float_argument(0), m.float_argument(1)))

        def frustum(m):
            x, y, r = m.argument(0), m.argument(1), m.argument(2)
            visible = 1 if mix(x, y ^ r) & 3 else 0
            log.append(('frustum', visible, from_bits(x), from_bits(y), from_bits(r)))
            return visible

        def snd(m):
            log.append(('sound', m.argument(0), object_index(m.argument(1)), m.argument(2)))
            return 0

        def set_action(m):
            o, action = m.argument(0), m.argument(1)
            log.append(('set_action', object_index(o), action))
            current = struct.unpack('<H', bytes(m.uc.mem_read(o + 0x2a, 2)))[0]
            if 0 <= action < 4 and action != current:
                frame = bytes(m.uc.mem_read(o + 0xd0, 4))
                m.write(o + 0x2c, struct.pack('<H', current))
                m.write(o + 0xd4, frame)
                m.write(o + 0x2a, struct.pack('<H', action))
                m.write(o + 0xd0, struct.pack('<f', 0.0))
            return 0

        def container(m):
            return CONTAINER

        def model_get(m):
            index = m.argument(0)
            return (0 if index in case['missing_models'] else BMD), 4

        def animate(m):
            frame_ptr = m.argument(0)
            o = frame_ptr - 0xd0
            action = struct.unpack('<H', bytes(m.uc.mem_read(BMD + 0xa8, 2)))[0]
            prior_action = struct.unpack('<H', bytes(m.uc.mem_read(m.argument(2), 2)))[0]
            frame, = m.read_floats(frame_ptr, 1)
            prior_frame, = m.read_floats(m.argument(1), 1)
            checks = (m.argument(1) == o + 0xd4, m.argument(2) == o + 0x2c, m.argument(4) == o + 0x158,
                      m.argument(5) == o + 0x164, m.uc.reg_read(m.x86.UC_X86_REG_ECX) == BMD)
            log.append(('animate', object_index(o), action, prior_action, m.float_argument(3), frame, prior_frame,
                        all(checks)))
            return 0, 0x18

        def kill(m):
            if not self.in_init:
                log.append(('kill', object_index(m.uc.reg_read(m.x86.UC_X86_REG_ECX))))
            return 0

        def noop_this(m):
            return 0

        def memset(m):
            dst, value, count = m.argument(0), m.argument(1), m.argument(2)
            m.write(dst, bytes([value & 0xff])*count)
            return dst

        def particle(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            log.append(('particle', m.argument(0), m.argument(4), *pos, *ang, *light, m.float_argument(5)))
            return 0

        def effect(m):
            log.append(('effect', m.argument(0), object_index(m.argument(5)), m.argument(4), m.float_argument(6)))
            return 0

        def sprite(m):
            pos = m.read_floats(m.argument(1), 3)
            light = m.read_floats(m.argument(3), 3)
            log.append(('sprite', m.argument(0), object_index(m.argument(4)), *pos, m.float_argument(2), *light))
            return 0

        def bone(m):
            matrix, vec, out = m.argument(0), m.argument(1), m.argument(2)
            v = m.read_floats(vec, 3)
            index = (matrix - BONES)//0x30
            log.append(('bone', index, *v))
            o = [f32(f32(v[k]*2.0) + float(k + 1)) for k in range(3)]
            if am.STACK <= out < am.STACK + am.STACK_BYTES:
                m.uc.mem_write(out, struct.pack('<3f', *o))   # the caller's local vector
            else:
                m.write(out, struct.pack('<3f', *o))
            return 0, 0x10

        def render_object(m):
            o = m.argument(0)
            raw = bytes(m.uc.mem_read(o, OBJ))
            pos = struct.unpack('<3f', raw[0x158:0x164])
            ang = struct.unpack('<3f', raw[0x164:0x170])
            light = struct.unpack('<3f', raw[0xec:0xf8])
            scale, alpha, frame = (struct.unpack('<f', raw[a:a+4])[0] for a in (0xbc, 0xdc, 0xd0))
            typ = struct.unpack('<i', raw[0x5c:0x60])[0]
            log.append(('object', object_index(o), m.argument(1), typ, *pos, *ang, *light, scale, alpha, frame,
                        tuple(m.argument(i) for i in range(2, 6))))
            return 0

        def shadow(m):
            origin = m.read_floats(BMD + 0x78, 3)
            log.append(('shadow', *origin, tuple(m.argument(i) for i in range(5))))
            return 0, 0x14

        def alpha_test(m):
            log.append(('alpha_test', m.argument(0)))
            return 0

        def alpha_blend(m):
            log.append(('alpha_blend',))
            return 0

        def bind(m):
            log.append(('bind', m.argument(0)))
            return 0

        def find_texture(m):
            bitmap = m.argument(0)
            return (0 if bitmap in case['missing_bitmaps'] else 0x25000000), 4

        def bitmap_info(m):
            return BITMAP_RECORD, 4

        def open_monster(m):
            log.append(('open_monster', m.argument(0)))
            return 0

        def wm_get(m):
            return MANAGER

        def wm_create(m):
            if s['world'] == 0x8d:
                return ('jump', TORMENTA_CREATE, TORMENTA)
            return 0, 4

        def wm_move(m):
            if s['world'] == 0x8d:
                return ('jump', TORMENTA_MOVE, TORMENTA)
            return 0, 4

        def zero_cdecl(m):
            return 0

        def zero_this4(m):
            return 0, 4

        def getter(m):
            return MANAGER

        stubs = {RAND: rand, TERRAIN: terrain, FRUSTUM: frustum, SND_PLAY: snd, SET_ACTION: set_action,
                 MODEL_CONTAINER: container, MODEL_GET: model_get, ANIMATE: animate, KILL_CLEANUP: kill,
                 INIT_HELPER_1: noop_this, INIT_HELPER_2: noop_this, MEMSET: memset, PARTICLE: particle,
                 EFFECT: effect, SPRITE: sprite, BONE: bone, RENDER_OBJECT: render_object, SHADOW: shadow,
                 ALPHA_TEST: alpha_test, ALPHA_BLEND: alpha_blend, BIND: bind, FIND_TEXTURE: find_texture,
                 BITMAP_INFO: bitmap_info, OPEN_MONSTER: open_monster, WM_GET: wm_get, WM_CREATE: wm_create,
                 WM_MOVE: wm_move, WM_RENDER: zero_this4}
        for a in LEAF_HANDLERS_CDECL:
            stubs[a] = zero_cdecl
        for a in LEAF_GETTERS:
            stubs[a] = getter
        for a in LEAF_METHODS:
            stubs[a] = zero_this4
        for target, (name, cleanup) in self.m.gl_targets.items():
            stubs[target] = self._gl_stub(name, cleanup)
        return stubs

    def _gl_stub(self, name, cleanup):
        log = self.log

        def handler(m):
            if name == 'glVertex3fv' or name == 'glColor3fv':
                log.append((name, *m.read_floats(m.argument(0), 3)))
            else:
                log.append((name, *(m.argument(i) for i in range(cleanup//4))))
            return 0, cleanup
        return handler

    def run(self, step, s):
        m = self.m
        regions = self.regions(s)
        self.log.clear()

        def init_enter(machine):
            # ObjectInit clears fields with read-modify-write (and [m], 0): its
            # record counts as defined while it runs; afterwards only the bytes
            # defined before or written by it stay defined.
            o = machine.uc.reg_read(machine.x86.UC_X86_REG_ECX)
            self.log.append(('init', object_index(o)))
            self.in_init += 1
            region = self.boids if BOIDS <= o < BOIDS + 40*OBJ else self.fishs
            off = o - region.base
            self.init_saved = (region, off, bytes(region.defined[off:off+OBJ]))
            region.written = bytearray(len(region.data))
            region.defined[off:off+OBJ] = b'\1'*OBJ
        m.observe(INIT, init_enter)
        init_end_hooks = []
        start, args, ecx = {STEP_LEAVES: (MOVE_LEAVES, [], LEAVES), STEP_BOIDS: (MOVE_BOIDS, [], 0),
                            STEP_FISHS: (MOVE_FISHS, [], 0), STEP_RB0: (RENDER_BOIDS, [0], 0),
                            STEP_RB1: (RENDER_BOIDS, [1], 0), STEP_RF: (RENDER_FISHS, [], 0),
                            STEP_RL: (RENDER_LEAVES, [], LEAVES)}[step]
        # ObjectInit returns through its final RET at 0x0129f06e; leave the init state there
        def init_leave(machine):
            if self.in_init:
                self.in_init -= 1
                region, off, saved = self.init_saved
                written = region.written[off:off+OBJ]
                region.defined[off:off+OBJ] = bytes(a | b for a, b in zip(saved, written))
                region.written = None
        m.observe(0x0129f06e, init_leave)
        result = m.execute(start, args, regions, self.stubs(s), ecx=ecx, cleanup=0)
        del init_end_hooks
        for r in regions:
            if r.name in result['regions']:
                r.data[:] = result['regions'][r.name]
        return result

    def state(self):
        b, f, l = bytes(self.boids.data), bytes(self.fishs.data), bytes(self.leaves.data)
        t = bytes(self.tormenta.data)
        return {'rand_state': self.rand_state, 'rand_calls': self.rand_calls, 'boids': b, 'fishs': f,
                'leaves': l[:200*LEAF], 'trailer': struct.unpack('<5i', l[0x8ca0:0x8cb4]),
                'tormenta': (t[6], struct.unpack('<I', t[0x14:0x18])[0], struct.unpack('<I', t[0x18:0x1c])[0])}


# --------------------------------------------------------------------------
# Comparison.

def same_float(a, b):
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return bits(a) == bits(b)
    return a == b


def same_tuple(x, y):
    return len(x) == len(y) and all(same_float(a, b) for a, b in zip(x, y))


def native_events(session, events, case, s):
    """The C test host's log in the client log's vocabulary."""
    out = []
    L = session.L.lib
    for e in events:
        k, f = e.kind, list(e.f)
        if k == 1:
            out.append(('sound', e.a, e.b, e.c))
        elif k == 2:
            out.append(('set_action', e.a, e.b))
        elif k == 3:
            out.append(('animate', e.a, e.b, e.c, f[0], f[1], f[2], True))
        elif k == 4:
            out.append(('particle', e.a, e.b, *f[0:9], f[9]))
        elif k == 5:
            out.append(('kill', e.a))
        elif k == 6:
            out.append(('init', e.a))
        elif k == 7:
            out.append(('effect', e.a, e.b, e.c, f[0]))
        elif k == 20:
            out.append(('frustum', e.a, f[0], f[1], f[2]))
        elif k == 21:
            out.append(('object', e.a, e.b, e.c, *f[0:12], (0, 0, 0xffffffff, 0xffffffff)))
        elif k == 22:
            out.append(('sprite', e.a, e.b, *f[0:3], f[3], *f[4:7]))
        elif k == 23:
            out.append(('bone', e.b, *f[0:3]))
        elif k == 24:
            out.append(('alpha_test', e.a))
        elif k == 25:
            out.append(('alpha_blend',))
        elif k == 26:
            out.append(('glColor4f', *(bits(v) for v in f[0:4])))
        elif k == 27:
            out.append(('glColor3f', *(bits(v) for v in f[0:3])))
        elif k == 28:
            out.append(('shadow', *f[0:3], (0xffffffff,)*4 + (0,)))
        elif k == 29:
            out.append(('bind', e.a))
        elif k == 30:
            pos = f[0:3]
            out.append(('glPushMatrix',))
            out.append(('glTranslatef', *(bits(v) for v in pos)))
            if e.a:
                out.append(('glBegin', 7))
                for i, (s_, t_) in enumerate(((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))):
                    out.append(('glTexCoord2f', bits(s_), bits(t_)))
                    out.append(('glVertex3fv', *f[3+3*i:6+3*i]))
                out.append(('glEnd',))
            out.append(('glPopMatrix',))
        elif k == 31:
            # RenderSprite: bind, glBegin, colour, the quad
            pos = (ctypes.c_float * 3)(*f[0:3])
            light = (ctypes.c_float * 3)(*f[5:8])
            cam = (ctypes.c_float * 12)(*case['camera_matrix'])
            quad = (ctypes.c_float * 12)()
            L.mu_env_billboard_quad(cam, pos, f[3], f[4], quad)
            rgba = (ctypes.c_float * 4)()
            n = L.mu_env_billboard_color(e.a, case['bitmap_components'], light, rgba)
            out.append(('bind', e.a))
            out.append(('glBegin', 7))
            if n == 3:
                out.append(('glColor3fv', rgba[0], rgba[1], rgba[2]))
            else:
                out.append(('glColor4f', *(bits(rgba[i]) for i in range(4))))
            for i, (s_, t_) in enumerate(((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))):
                out.append(('glTexCoord2f', bits(s_), bits(t_)))
                out.append(('glVertex3fv', quad[3*i], quad[3*i+1], quad[3*i+2]))
            out.append(('glEnd',))
        else:
            out.append(('unknown', k))
    return out


def normalize_client(log):
    out = []
    for e in log:
        if e[0] == 'frustum':
            out.append(e)
        else:
            out.append(tuple(float(v) if isinstance(v, float) else v for v in e))
    return out


def compare_states(L, a, b):
    diffs = []
    for key in ('rand_state', 'rand_calls', 'trailer', 'tormenta'):
        if a[key] != b[key]:
            diffs.append((key, a[key], b[key]))
    for name, count, size, mask in (('boids', 40, OBJ, L.object_mask), ('fishs', 10, OBJ, L.object_mask),
                                    ('leaves', 200, LEAF, L.leaf_mask)):
        x, y = a[name], b[name]
        for i in range(count):
            for k in range(size):
                if mask[k] and x[i*size+k] != y[i*size+k]:
                    off = k & ~3
                    va = x[i*size+off:i*size+off+4]
                    vb = y[i*size+off:i*size+off+4]
                    if len(va) == 4 and len(vb) == 4:
                        fa, fb = struct.unpack('<f', va)[0], struct.unpack('<f', vb)[0]
                        if math.isnan(fa) and math.isnan(fb):
                            continue
                    diffs.append((name, i, hex(k), x[i*size+k], y[i*size+k]))
                    break
            if len(diffs) > 8:
                return diffs
    return diffs


# --------------------------------------------------------------------------
# Cases.

def make_grid(g, palette, block, size, word):
    out = bytearray(size*size*(2 if word else 1))
    for by in range(0, size, block):
        for bx in range(0, size, block):
            value = g.choice(palette)
            for y in range(by, by + block):
                for x in range(bx, bx + block):
                    if word:
                        struct.pack_into('<H', out, 2*(y*size + x), value)
                    else:
                        out[y*size + x] = value
    return bytes(out)


def random_object(g, L, world, ref):
    o = bytearray(OBJ)
    types = {0: [0x192], 1: [0x194], 3: [0x193], 7: [0x199, 0x19a, 0x19b, 0x19f], 0x80: [0x19b, 0x1a0],
             11: [0x1a2], 52: [0x1a2], 0x74: [0x194, 0x196]}.get(world, [0x192, 0x194, 0x198, 0x196, 0x197])
    o[0] = g.choice([0, 1, 1, 1])
    o[0x0a] = g.choice([0, 0, 1])
    o[0x0c] = g.choice([0, 1])
    o[0x29] = g.choice([0, 0, 1, 2, 3])
    struct.pack_into('<HH', o, 0x2a, g.randrange(4), g.randrange(4))
    struct.pack_into('<iiiii', o, 0x5c, g.choice(types), g.randrange(-1, 3), -1, g.randrange(-5, 128), -1)
    for off in (0xa0, 0xa8, 0xb4, 0xbc, 0xc4, 0xc8, 0xd0, 0xd4, 0xd8, 0xdc, 0xe0):
        struct.pack_into('<f', o, off, g.choice([0.0, 0.1, 0.5, 1.0, g.uniform(-2, 12)]))
    for off, spread in ((0xec, 0), (0xf8, 400), (0x158, 700), (0x164, 0), (0x170, 0), (0x188, 700)):
        for k in range(3):
            base = ref[k] if spread else 0.0
            struct.pack_into('<f', o, off + 4*k, f32(base + g.uniform(-spread or 2, spread or 360)))
    return bytes(o)


def random_leaf(g, ref):
    l = bytearray(LEAF)
    l[8] = g.choice([0, 1, 1])
    struct.pack_into('<i', l, 0xc, g.choice([0x771f, 0x7720, 0x7721, 0x7fe8]))
    struct.pack_into('<f', l, 0x18, g.uniform(0, 10))
    for off, spread in ((0x20, 600), (0x2c, 0), (0x38, 0), (0x70, 0), (0x7c, 0), (0x88, 600)):
        for k in range(3):
            if spread:
                v = ref[k] + g.uniform(-spread, spread)
            elif off == 0x38:
                v = g.uniform(-0.2, 1.0)
            else:
                v = g.uniform(-30, 30)
            struct.pack_into('<f', l, off + 4*k, f32(v))
    struct.pack_into('<ff', l, 0x44, g.uniform(0, 1), g.uniform(0, 1))
    struct.pack_into('<f', l, 0x60, g.uniform(-1, 1))
    return bytes(l)


ALL_WORLDS = sorted(set(BOID_WORLDS + FISH_WORLDS + LEAF_WORLDS))


def make_case(g, index, L, worlds=None, fuzz=None):
    pool = worlds or ALL_WORLDS
    world = pool[index % len(pool)] if g.random() < 0.7 else g.choice(pool)
    hero = [f32(g.uniform(2500, 23000)), f32(g.uniform(2500, 23000)), f32(g.uniform(0, 400))]
    if g.random() < 0.05:
        hero[0] = f32(g.choice([-150.0, 25550.0, 1e9, -1e9]))
    if world == 7 and g.random() < 0.5:
        hero[1] = f32(g.uniform(2500, 12700))
    att_palette = [0, 0, 0, 1, 2, 4, 8, 9, 0x800, 0x1000, 0x801, 0x1002, 3]
    layer_palette = [0, 1, 2, 3, 4, 5, 5, 5, 14]
    fuzz = (g.random() < 0.25) if fuzz is None else fuzz
    boids = b''.join(random_object(g, L, world, hero) if fuzz and g.random() < 0.5 else bytes(OBJ)
                     for _ in range(40))
    fishs = b''.join(random_object(g, L, world, hero) if fuzz and g.random() < 0.5 else bytes(OBJ)
                     for _ in range(10))
    leaves = b''.join(random_leaf(g, hero) if fuzz and g.random() < 0.5 else bytes(LEAF) for _ in range(200))
    if not fuzz:   # dead objects as after the world's entry (ObjectInit leaves +0xe0 = 0.1)
        boids = b''.join(bytes(OBJ)[:0xe0] + struct.pack('<f', 0.1) + bytes(OBJ)[0xe4:] for _ in range(40))
        fishs = b''.join(bytes(OBJ)[:0xe0] + struct.pack('<f', 0.1) + bytes(OBJ)[0xe4:] for _ in range(10))
    trailer = (g.choice([0, 100]), g.randrange(0, 101), g.randrange(-40, 40), g.randrange(-20, 20),
               g.randrange(0, 2000)) if fuzz else (0, 0, 0, 0, 0)
    tormenta = (1, f32(10.0), f32(g.uniform(0, 10)) if fuzz else 0.0)
    case = {'index': index, 'world': world, 'seed': g.getrandbits(32), 'hero': hero,
            'attributes': make_grid(g, att_palette, g.choice([2, 4, 8]), 256, True),
            'layer1': make_grid(g, layer_palette, g.choice([2, 4, 8]), 256, False),
            'height_base': f32(hero[2] + g.uniform(-250, 50)), 'height_span': g.choice([50, 200, 400, 600]),
            'height_shift': g.choice([10, 12, 14]),
            'missing_models': [g.choice([0x192, 0x194, 0x193, 0x198, 0x196])] if g.random() < 0.08 else [],
            'missing_bitmaps': [g.choice([0x771f, 0x7721])] if g.random() < 0.1 else [],
            'bitmap_components': g.choice([3, 4]), 'crt_mode': g.choice([0, 1]),
            'camera_matrix': [f32(g.uniform(-1, 1)) for _ in range(9)] + [f32(g.uniform(-5000, 5000))
                                                                           for _ in range(3)],
            'hero_action': g.choice([1, 0x31, 0x32, 0x40]), 'safe': g.choice([0, 0, 1]),
            'event': g.choice([0, 1, 2]), 'time': f32(g.uniform(0, 3e6)),
            'camera_offset': (f32(g.uniform(-200, 200)), f32(g.uniform(-1500, 500)), f32(g.uniform(300, 1200))),
            'teleport': g.randrange(10, 60) if g.random() < 0.3 else -1,
            'boids': boids, 'fishs': fishs, 'leaves': leaves, 'trailer': trailer, 'tormenta': tormenta,
            'fuzz': fuzz}
    cm = case['camera_matrix']
    case['camera_matrix'] = [cm[0], cm[1], cm[2], cm[9], cm[3], cm[4], cm[5], cm[10], cm[6], cm[7], cm[8], cm[11]]
    return case


def steps_of(world):
    steps = []
    if world in LEAF_WORLDS:
        steps.append(STEP_LEAVES)
    if world in BOID_WORLDS:
        steps.append(STEP_BOIDS)
    if world in FISH_WORLDS:
        steps.append(STEP_FISHS)
    return steps


def run_case(machine, L, case, ticks, render_every, g):
    client = Client(machine, L, case)
    native = NativeSession(L, case)
    s = {'world': case['world'], 'hero': list(case['hero']), 'safe': case['safe'], 'event': case['event'],
         'hero_action': case['hero_action'], 'time': case['time']}
    result = {'index': case['index'], 'world': case['world'], 'fuzz': case['fuzz'], 'steps': 0, 'events': 0,
              'mismatch': None, 'stopped': None, 'rand_calls': 0}
    try:
        for tick in range(ticks):
            s['hero'][0] = f32(s['hero'][0] + g.uniform(-40, 40))
            s['hero'][1] = f32(s['hero'][1] + g.uniform(-40, 40))
            if tick == case['teleport']:   # a warp: every swimmer and flyer is far behind
                s['hero'][0] = f32(s['hero'][0] + g.choice([-2500.0, 2500.0]))
            s['hero_tile'] = (am_cvt(s['hero'][0]/100.0), am_cvt(s['hero'][1]/100.0))
            c = case['camera_offset']
            s['camera'] = [f32(s['hero'][0] + c[0]), f32(s['hero'][1] + c[1]), f32(s['hero'][2] + c[2])]
            s['time'] = f32(s['time'] + 40.0)
            steps = steps_of(case['world'])
            if render_every and tick % render_every == render_every - 1:
                steps += [STEP_RB0, STEP_RB1, STEP_RF, STEP_RL]
            native.set_inputs(s)
            for step in steps:
                r = client.run(step, s)
                if not r['ok']:
                    result['stopped'] = {'step': STEP_NAMES[step], 'tick': tick, 'stopped': str(r['stopped']),
                                         'error': r['error'], 'checks': r['checks']}
                    return result
                ev = native.run(step)
                expected = native_events(native, ev, case, s)
                got = normalize_client(client.log)
                result['steps'] += 1
                result['events'] += len(got)
                if len(expected) != len(got) or not all(same_tuple(a, b) for a, b in zip(expected, got)):
                    first = next((i for i, (a, b) in enumerate(zip(expected, got)) if not same_tuple(a, b)),
                                 min(len(expected), len(got)))
                    result['mismatch'] = {'step': STEP_NAMES[step], 'tick': tick, 'first': first,
                                          'native': [str(x) for x in expected[first:first+3]],
                                          'client': [str(x) for x in got[first:first+3]],
                                          'counts': (len(expected), len(got))}
                    return result
                diffs = compare_states(L, native.state(), client.state())
                if diffs:
                    result['mismatch'] = {'step': STEP_NAMES[step], 'tick': tick, 'state': [str(d) for d in diffs]}
                    return result
        result['rand_calls'] = client.rand_calls
        result['live'] = {'boids': sum(client.boids.data[i*OBJ] for i in range(40)),
                          'fishs': sum(client.fishs.data[i*OBJ] for i in range(10)),
                          'leaves': sum(client.leaves.data[i*LEAF + 8] for i in range(200))}
        return result
    finally:
        native.close()


def am_cvt(v):
    v = f32(v)
    if not (-2147483904.0 < v < 2147483648.0):
        return -2147483648
    return int(v)


def build_library(mutation, out):
    src = ROOT/'reconstructed/environment'
    files = [str(src/n) for n in ('env_core.c', 'env_boids.c', 'env_fish.c', 'env_leaves.c', 'env_world.c',
                                  'env_test_host.c')] + [str(ROOT/'reconstructed/record-math/record_math.c')]
    cmd = ['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared',
           f'-DMU_ENV_MUTATION={mutation}', *files, '-lm', '-o', str(out)]
    subprocess.run(cmd, check=True)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/environment/libclient_env.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=60)
    parser.add_argument('--ticks', type=int, default=40)
    parser.add_argument('--render-every', type=int, default=4)
    parser.add_argument('--worlds', help='comma-separated world list (default: all ported)')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    bodies = {}
    for name, (a, b, digest) in BODIES.items():
        observed = hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()
        if observed != digest:
            raise SystemExit(f'{name}: captured body differs from the pinned digest')
        bodies[name] = {'start': hex(a), 'end_exclusive': hex(b), 'sha256': observed}
    machine = EnvMachine(text, data)
    L = Library(Path(args.library))
    worlds = [int(w, 0) for w in args.worlds.split(',')] if args.worlds else None
    g = random.Random(args.seed)
    started = time.time()
    results = []
    for index in range(args.cases):
        case_worlds = worlds or (TARGET_WORLDS if index % 2 == 0 else None)
        case = make_case(g, index, L, case_worlds)
        results.append(run_case(machine, L, case, args.ticks, args.render_every, random.Random(case['seed'])))
        r = results[-1]
        if r['mismatch'] or r['stopped']:
            print(json.dumps(r, default=str)[:2000])
    equal = [r for r in results if not r['mismatch'] and not r['stopped']]
    probes = {PROBES[a]: n for a, n in machine.probe_hits.items()}
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'bodies': bodies, 'seed': args.seed,
              'probes': probes, 'probes_missed': [k for k, n in probes.items() if not n],
              'library_sha256': hashlib.sha256(Path(args.library).read_bytes()).hexdigest(),
              'cases': len(results), 'equal': len(equal),
              'steps': sum(r['steps'] for r in results), 'events': sum(r['events'] for r in results),
              'rand_calls': sum(r['rand_calls'] for r in results),
              'worlds': sorted({r['world'] for r in results}),
              'mismatches': [r for r in results if r['mismatch']][:20],
              'stopped': [r for r in results if r['stopped']][:20], 'seconds': round(time.time() - started, 1)}
    if args.mutations:
        report['mutations'] = run_mutations(machine, args, worlds)
    report['ok'] = report['equal'] == report['cases'] and not report['probes_missed'] and \
        (not args.mutations or all(m['detected'] for m in report['mutations']))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    print(f"cases {report['equal']}/{report['cases']} equal, {report['steps']} steps, {report['events']} host calls, "
          f"{report['rand_calls']} rand() calls, worlds {[hex(w) for w in report['worlds']]}, "
          f"{report['seconds']} s")
    if args.mutations:
        for m in report['mutations']:
            print(f"mutation {m['id']} ({m['label']}): {'detected' if m['detected'] else 'NOT detected'} "
                  f"in {m['cases_disagreeing']}/{m['cases']}")
    print(f"probes reached {len(probes)-len(report['probes_missed'])}/{len(probes)}"
          + (f", missed: {report['probes_missed']}" if report['probes_missed'] else ''))
    print('ALL PASS' if report['ok'] else 'FAIL')
    return 0 if report['ok'] else 1


MUTATIONS = [
    (1, 'boid limit 6 instead of 5', [0, 1, 3]),
    (2, 'flock radius 500 instead of 400', [0, 7]),
    (3, 'bird landing window 300..400', [0]),
    (4, 'fish turn on layer 4 instead of 5', [0]),
    (5, 'leaf drift without the camera rule', [0, 3]),
    (6, 'snow scale 6 instead of 5', [2]),
    (7, 'Tormenta rain rises 0.2 per call', [0x8d]),
    (8, 'RenderBoids without the +90 turn', [0, 1, 3]),
    (9, 'default leaf move fades 0.04', [2, 7]),
    (10, 'TurnAngle rounds toward the long way', [0, 7]),
]


def run_mutations(machine, args, worlds):
    out = []
    tmp = Path(args.output).parent if args.output else Path('/tmp')
    for mid, label, mworlds in MUTATIONS:
        lib_path = build_library(mid, tmp/f'libclient_env_mut{mid}.{SUFFIX}')
        L = Library(lib_path)
        g = random.Random(args.seed + mid)
        disagree, cases = 0, 6
        for index in range(cases):
            case = make_case(g, index, L, mworlds, fuzz=False)
            r = run_case(machine, L, case, max(args.ticks, 30), args.render_every, random.Random(case['seed']))
            if r['mismatch']:
                disagree += 1
        out.append({'id': mid, 'label': label, 'cases': cases, 'cases_disagreeing': disagree,
                    'detected': disagree > 0})
    return out


if __name__ == '__main__':
    sys.exit(main())
