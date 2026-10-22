#!/usr/bin/env python3
"""Compare reconstructed/raven with the client's Dark Raven (Dark Spirit) routines (NATIVE-HELPERS-002).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py through scripts/validate_helpers.py's
machine: declared regions with a defined-byte mask; an undefined read, an
undeclared access or an unmapped access stops a case). The authored C
(reconstructed/raven, libclient_raven) runs the same steps through ctypes
with Python host callbacks that give the same answers as the client-side
stubs. Compared after every step: the rand() state and call count, the
modelled bytes of the pet objects and of the owners' pet fields, the request
flag and the ordered log of host calls.

Sections:

* sessions   the pet byte 0x00c92bea (create 0x00c92a29, the Dark Raven
             constructor 0x009ecbdf, CreatePetPointer 0x009ec0b0, ObjectInit
             and the CHARACTER constructor 0x0129d272 as client code), the
             per-character move 0x00c930df (MovePet 0x009ecfe9 through the
             vtable, the re-create, the model check 0x00c92e04) and render
             0x00c9314f (RenderPet 0x009ef6d5 through the vtable) for up to
             three owners, with owner changes between steps;
* draw       the render functors 0x00a2eea5 (DarkSpirit) and 0x00a55f03
             (Dark_Soul) of the render registry.

Stubs (engine services): rand() (MSVC LCG), RequestTerrainHeight,
TestFrustrum2D, the model container and getter (synthetic BMD records),
the animation tick 0x012b4dd3, SetAction 0x012affa4, the bone matrix getter
0x0129f12c with TransformPosition 0x012b6ef1 and 0x012b6d2a (synthetic
answers), CreateParticle, CreateSprite, PlayBuffer, the buff lookup
0x01295ade, operator new, the bone-buffer allocation 0x0129f06f, the
SetLive cleanup 0x009b0451, the mount manager 0x009c104e / 0x0106b93a /
0x0106b9f7, the character lookup 0x009a13f4 (no target offline), the
packet builder 0x00d51b91.. (recorded), the deletion 0x00c9321b (recorded,
clears c + 0x31f0), the later raven class 0x009f0258, RenderObject,
RenderMesh 0x00966e4a / RenderBody 0x00966def, the model push/pop, glColor,
RenderBodyShadow, the wave 0x0185bdc4, the random float 0x011ff622 and the
sine wrapper 0x009681bd. CreateAngle, TurnAngle2, AngleMatrix, VectorRotate,
MoveHumming, the composition 0x00cff83e, sqrt and fabs run as client code.
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
import validate_helpers as vh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = ROOT/f'reconstructed/raven/libclient_raven.{SUFFIX}'

f32, bits, from_bits, mix, same, same_log = vh.f32, vh.bits, vh.from_bits, vh.mix, vh.same, vh.same_log

CHAR_BASE, CHAR_STRIDE, CHAR_SIZE, CHAR_OBJ = 0x22000000, 0x4000, 0x3700, 0x3254
PET_SIZE, PET_OBJ = 0x3688, 0x3260
HEAP_BASE, HEAP_SIZE = 0x27000000, 0x80000
MODEL_BASE, MODEL_SLOT = 0x24000000, 0x200
ACTIONS = 0x24100000
MOUNT_REC = 0x24200000
BONE_TOKEN = 0x30000000
WORLD, TICK, HERO, NET = 0x01cf15fc, 0x0bdc5eb0, 0x0a39d754, 0x01d1e028
WALL = 0x0b795420
PARENT = 0x078965ac
WORLD_TIME = 0x06fce370

RAND, TERRAIN, FRUSTUM = 0x01989721, 0x016cc9e2, 0x016ccce7
CONTAINER_GET, MODEL_GET, ANIMATE, SET_ACTION = 0x00966cc4, 0x00eaa8cf, 0x012b4dd3, 0x012affa4
KILL, PARTICLE, SPRITE, RENDER_OBJECT, SOUND, BUFF = 0x009b0451, 0x0168fafd, 0x01692eb7, 0x016d4fe4, 0x00a6ac96, 0x01295ade
BONE_GET, TRANSFORM, TRANSFORM_BASE = 0x0129f12c, 0x012b6ef1, 0x012b6d2a
NEW, BONES_ALLOC = 0x0191ba7b, 0x0129f06f
MANAGER_GET, MOUNT_FIND, MOUNT_STATE = 0x009c104e, 0x0106b93a, 0x0106b9f7
CHARS_GET, FIND_CHAR = 0x0095f6db, 0x009a13f4
PK_CTOR, PK_HEAD, PK_PUT, PK_SEND, PK_DTOR = 0x00d51b91, 0x00d51baf, 0x0095c204, 0x00d51d4f, 0x00d51ba6
DELETE, LATER_CLASS = 0x00c9321b, 0x009f0258
RENDER_MESH, RENDER_BODY, PUSH, POP = 0x00966e4a, 0x00966def, 0x012b7e53, 0x012b7e65
SHADOW, ALPHA_TEST, WAVE, RANDOM_FLOAT, SINE = 0x012bc07a, 0x0184a990, 0x0185bdc4, 0x011ff622, 0x009681bd
SHADOW_WORLD, EVENT_GET, EVENT_BLOCK, DIM_WORLD = 0x009b0418, 0x009a6ef3, 0x009a645f, 0x016a88ae
GL_COLOR3, GL_COLOR4 = 0x01a7c76c, 0x01a7c754
CHAR_CTOR = 0x0129d272

SET_TYPE, CREATE, MOVE, RENDER = 0x00c92bea, 0x00c92a29, 0x00c930df, 0x00c9314f
MOVE_PET, RENDER_PET, CTOR, CREATE_POINTER = 0x009ecfe9, 0x009ef6d5, 0x009ecbdf, 0x009ec0b0
DRAW_RAVEN, DRAW_SOUL = 0x00a2eea5, 0x00a55f03

BODIES = {  # start, exclusive end
    'set_type': (0x00c92bea, 0x00c92e04), 'create': (0x00c92a29, 0x00c92bea),
    'model_fits': (0x00c92e04, 0x00c92e9a), 'horse': (0x00c92e9a, 0x00c92ef3),
    'move': (0x00c930df, 0x00c9314f), 'render': (0x00c9314f, 0x00c9321b), 'delete': (0x00c9321b, 0x00c9326e),
    'create_pointer': (0x009ec0b0, 0x009ec7b7), 'anim': (0x009ec7b7, 0x009ec86f), 'set_ai': (0x009ec878, 0x009ec899),
    'alpha_step': (0x009ecb21, 0x009ecbb7), 'ctor': (0x009ecbdf, 0x009ecf9b), 'move_pet': (0x009ecfe9, 0x009ef6b8),
    'render_pet': (0x009ef6d5, 0x009ef817), 'draw_raven': (0x00a2eea5, 0x00a2f3c0), 'draw_soul': (0x00a55f03, 0x00a5636c),
}

V3 = ctypes.c_float * 3
P = ctypes.c_void_p


class Obj(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('flag_04', ctypes.c_uint8), ('lighting', ctypes.c_uint8),
                ('target', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('alpha_enable', ctypes.c_uint8),
                ('flag_0d', ctypes.c_uint8), ('flag_0e', ctypes.c_uint8), ('ai', ctypes.c_uint8),
                ('action', ctypes.c_uint16), ('prior_action', ctypes.c_uint16), ('flag_40', ctypes.c_uint8),
                ('level', ctypes.c_uint8), ('flag_44', ctypes.c_uint8), ('type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('hidden_mesh', ctypes.c_int32), ('lifetime', ctypes.c_int32),
                ('blend_mesh', ctypes.c_int32), ('time', ctypes.c_uint32), ('scale', ctypes.c_float),
                ('blend_light', ctypes.c_float), ('uv', ctypes.c_float * 2), ('field_b4', ctypes.c_float),
                ('velocity', ctypes.c_float), ('field_c0', ctypes.c_float), ('field_c4', ctypes.c_float),
                ('field_c8', ctypes.c_float), ('frame', ctypes.c_float), ('prior_frame', ctypes.c_float),
                ('alpha_target', ctypes.c_float), ('alpha', ctypes.c_float), ('light', V3), ('direction', V3),
                ('box_min', V3), ('box_max', V3), ('position', V3), ('angle', V3), ('matrix', ctypes.c_float*12)]


class Pet(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('cls', ctypes.c_int32), ('owner', ctypes.c_int32),
                ('target', ctypes.c_int32), ('safe', ctypes.c_uint8), ('counter', ctypes.c_uint8),
                ('byte_29', ctypes.c_uint8), ('tile_byte', ctypes.c_uint8*2), ('target_key', ctypes.c_int16),
                ('level', ctypes.c_uint16), ('tile', ctypes.c_int32*2), ('command', ctypes.c_uint8),
                ('fade_in', ctypes.c_uint8), ('fade_out', ctypes.c_uint8), ('slot', ctypes.c_int32),
                ('info_level', ctypes.c_int32), ('object', Obj)]


class Owner(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('hero', ctypes.c_uint8), ('safe', ctypes.c_uint8),
                ('tile', ctypes.c_int32*2), ('pet_item', ctypes.c_int32), ('pet_level', ctypes.c_uint16),
                ('ride', ctypes.c_uint16), ('action', ctypes.c_uint16),
                ('type', ctypes.c_int32), ('scale', ctypes.c_float), ('frame', ctypes.c_float), ('position', V3),
                ('buff_12', ctypes.c_uint8), ('buff_3d', ctypes.c_uint8), ('buff_b2', ctypes.c_uint8),
                ('buff_118', ctypes.c_uint8), ('has_mount', ctypes.c_uint8), ('mount_offset_z', ctypes.c_float),
                ('mount_state2', ctypes.c_uint8), ('has_info', ctypes.c_uint8), ('info_type', ctypes.c_int16),
                ('info_level', ctypes.c_uint8)]


class Inputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('tick', ctypes.c_uint32)]


HAS_MODEL_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_int32)
KEYS_FN = ctypes.CFUNCTYPE(ctypes.c_int32, P, ctypes.c_int32, ctypes.c_int32)
ANIMATE_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, P, ctypes.c_int32, ctypes.c_float)
SET_ACTION_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32)
BONE_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)
TRANSFORM_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, P, P,
                                ctypes.c_int)
TRANSFORM_BASE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, P, P,
                                     P)
PARTICLE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, P, P, ctypes.c_int32, ctypes.c_float)
SOUND_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.c_int32)
REQUEST_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.c_int32)
TERRAIN_FN = ctypes.CFUNCTYPE(ctypes.c_float, P, ctypes.c_float, ctypes.c_float)
WALL_FN = ctypes.CFUNCTYPE(ctypes.c_uint16, P, ctypes.c_int32, ctypes.c_int32)
ORIGIN_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P)
ANGLE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P)
MATRIX_FN = ctypes.CFUNCTYPE(None, P, P)
FIND_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_int16)
UNSUPPORTED_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.c_int32)


class Host(ctypes.Structure):
    _fields_ = [('context', P), ('has_model', HAS_MODEL_FN), ('action_keys', KEYS_FN), ('animate', ANIMATE_FN),
                ('set_action', SET_ACTION_FN), ('bone', BONE_FN), ('transform', TRANSFORM_FN),
                ('transform_base', TRANSFORM_BASE_FN), ('particle', PARTICLE_FN), ('sound', SOUND_FN),
                ('request', REQUEST_FN), ('terrain_height', TERRAIN_FN), ('terrain_wall', WALL_FN),
                ('model_origin', ORIGIN_FN), ('body_angle', ANGLE_FN), ('parent_matrix', MATRIX_FN),
                ('find', FIND_FN), ('unsupported', UNSUPPORTED_FN)]


FRUSTUM_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_float, ctypes.c_float, ctypes.c_float)
DRAW_OBJECT_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_int32)


class RenderHost(ctypes.Structure):
    _fields_ = [('context', P), ('frustum', FRUSTUM_FN), ('draw_object', DRAW_OBJECT_FN)]


class Raven(ctypes.Structure):
    _fields_ = [('rand_state', ctypes.c_uint32), ('rand_calls', ctypes.c_uint64), ('requested', ctypes.c_uint8),
                ('pets', Pet*16), ('owners', ctypes.POINTER(Owner)), ('owner_count', ctypes.c_int32), ('host', Host)]


class Draw(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int32), ('mesh', ctypes.c_int32), ('flags', ctypes.c_int32),
                ('blend_mesh', ctypes.c_int32), ('hidden', ctypes.c_int32), ('texture', ctypes.c_int32),
                ('bitmap', ctypes.c_int32), ('subtype', ctypes.c_int32), ('alpha', ctypes.c_float),
                ('blend_light', ctypes.c_float), ('uv', ctypes.c_float*2), ('scale', ctypes.c_float), ('color', V3),
                ('vector', V3), ('light', V3)]


class DrawList(ctypes.Structure):
    _fields_ = [('items', Draw*16), ('count', ctypes.c_int32)]


class DrawInputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('time', ctypes.c_float), ('shadow_world', ctypes.c_uint8),
                ('event_block', ctypes.c_uint8), ('dim_world', ctypes.c_uint8), ('color', V3)]


SINE_FN = ctypes.CFUNCTYPE(ctypes.c_float, P, ctypes.c_float)
WAVE_FN = ctypes.CFUNCTYPE(ctypes.c_float, P, ctypes.c_float, ctypes.c_int32)
RFLOAT_FN = ctypes.CFUNCTYPE(ctypes.c_float, P, ctypes.c_float, ctypes.c_float, ctypes.c_int32)


class DrawHost(ctypes.Structure):
    _fields_ = [('context', P), ('sine', SINE_FN), ('wave', WAVE_FN), ('random_float', RFLOAT_FN),
                ('terrain_height', TERRAIN_FN)]


def load_library(path=LIB, extra_cflags=None):
    if extra_cflags is not None or not Path(path).exists():
        cmd = ['make', '-C', str(Path(path).parent), '-B'] if extra_cflags is None else \
            ['make', '-C', str(Path(path).parent), '-B', f'CFLAGS=-std=c11 -O2 -fPIC -ffp-contract=off '
             f'-fno-fast-math {extra_cflags}']
        subprocess.run(cmd, check=True, capture_output=True)
    lib = ctypes.CDLL(str(path))
    PR = ctypes.POINTER(Raven)
    PI = ctypes.POINTER(Inputs)
    lib.mu_rv_init.argtypes = [PR, ctypes.c_uint32, ctypes.POINTER(Owner), ctypes.c_int32, ctypes.POINTER(Host)]
    lib.mu_rv_set_type.argtypes = [PR, PI, ctypes.c_int32, ctypes.c_uint8]
    lib.mu_rv_set_type.restype = ctypes.c_int
    lib.mu_rv_move.argtypes = [PR, PI, ctypes.c_int32]
    lib.mu_rv_render.argtypes = [PR, PI, ctypes.c_int32, ctypes.POINTER(RenderHost)]
    lib.mu_rv_draw_raven.argtypes = [ctypes.POINTER(Obj), ctypes.POINTER(DrawInputs), ctypes.POINTER(DrawHost),
                                     ctypes.POINTER(DrawList)]
    lib.mu_rv_draw_soul.argtypes = [ctypes.POINTER(Obj), ctypes.POINTER(DrawInputs), ctypes.POINTER(DrawHost),
                                    ctypes.POINTER(DrawList)]
    return lib


# --------------------------------------------------------------------------
# Client layout of the modelled fields.

OBJECT_FIELDS = [  # (name, offset, format, count)
    ('live', 0x00, 'B', 1), ('flag_04', 0x04, 'B', 1), ('lighting', 0x05, 'B', 1), ('target', 0x08, 'B', 1),
    ('visible', 0x0b, 'B', 1), ('alpha_enable', 0x0c, 'B', 1), ('flag_0d', 0x0d, 'B', 1), ('flag_0e', 0x0e, 'B', 1),
    ('ai', 0x29, 'B', 1), ('action', 0x2a, 'H', 1), ('prior_action', 0x2c, 'H', 1), ('flag_40', 0x40, 'B', 1),
    ('level', 0x41, 'B', 1), ('flag_44', 0x44, 'B', 1), ('type', 0x5c, 'i', 1), ('subtype', 0x60, 'i', 1),
    ('hidden_mesh', 0x68, 'i', 1), ('lifetime', 0x6c, 'i', 1), ('blend_mesh', 0x74, 'i', 1), ('time', 0x84, 'I', 1),
    ('scale', 0xa0, 'f', 1), ('blend_light', 0xa8, 'f', 1), ('uv', 0xac, 'f', 2), ('field_b4', 0xb4, 'f', 1),
    ('velocity', 0xbc, 'f', 1), ('field_c0', 0xc0, 'f', 1), ('field_c4', 0xc4, 'f', 1), ('field_c8', 0xc8, 'f', 1),
    ('frame', 0xd0, 'f', 1), ('prior_frame', 0xd4, 'f', 1), ('alpha_target', 0xd8, 'f', 1), ('alpha', 0xdc, 'f', 1),
    ('light', 0xec, 'f', 3), ('direction', 0xf8, 'f', 3), ('box_min', 0x128, 'f', 3), ('box_max', 0x134, 'f', 3),
    ('position', 0x158, 'f', 3), ('angle', 0x164, 'f', 3), ('matrix', 0x2e8, 'f', 12)]
PET_FIELDS = [
    ('safe', 0x10, 'B', 1), ('counter', 0x2d, 'B', 1), ('byte_29', 0x35, 'B', 1), ('tile_byte', 0x39, 'B', 2),
    ('target_key', 0x4c, 'h', 1), ('level', 0x150, 'H', 1), ('tile', 0x18c, 'i', 2), ('slot', 0x367c, 'i', 1),
    ('command', 0x3684, 'B', 1), ('fade_in', 0x3685, 'B', 1), ('fade_out', 0x3686, 'B', 1)]


def fields_tuple(fields, raw, base=0):
    out = []
    for name, off, fmt, count in fields:
        out.append((name, struct.unpack('<' + fmt*count, raw[base + off:base + off + struct.calcsize('<' + fmt*count)])))
    return out


def ctypes_tuple(fields, obj):
    out = []
    for name, off, fmt, count in fields:
        v = getattr(obj, name)
        vals = tuple(v) if count > 1 else (v,)
        if fmt == 'f':
            vals = tuple(f32(x) for x in vals)
        out.append((name, vals))
    return out


def char_addr(k):
    return CHAR_BASE + k*CHAR_STRIDE


def owner_of_char(addr):
    k, r = divmod(addr - CHAR_BASE, CHAR_STRIDE)
    return k if r == 0 and 0 <= k < 8 else -1


def owner_of_object(addr):
    k, r = divmod(addr - CHAR_BASE - CHAR_OBJ, CHAR_STRIDE)
    return k if r == 0 and 0 <= k < 8 else -1


# --------------------------------------------------------------------------
# Shared synthetic answers.

def model_slot(case, index):
    types = case['model_types']
    return types.index(index) if index in types else None


def keys_answer(case, model, action):
    return 1 + mix(model ^ case['keys_salt'], action) % 30


def anim_answer(case, step, action, frame_bits, speed_bits):
    return 1 if mix(mix(case['anim_salt'], step), action ^ frame_bits ^ speed_bits) % 5 else 0


def bone_present(case, which, k, bone):
    if which == 0:   # the owner's object
        return 1 if bone < case['owners'][k]['bones'] else 0
    return 1 if bone < case['pet_bones'][k] else 0


def bone_answer(case, model, which, k, bone, vector, translate):
    h = mix(mix(case['bone_salt'] ^ model, which*16 + k), bone*2 + translate)
    base = [float((h >> (8*j)) % 97) - 48.0 for j in range(3)]
    return tuple(f32(f32(vector[j]*0.5) + base[j]) for j in range(3))


def bone_base_answer(case, model, which, k, bone, base, vector):
    a = bone_answer(case, model, which, k, bone, vector, 7)
    return tuple(f32(f32(a[j]*1.25) + base[j]) for j in range(3))


def height_answer(case, x, y):
    return f32(case['height_base'] + float(mix(bits(x) >> 6, bits(y) >> 6) % 300))


def wall_answer(case, x, y):
    return 1 if mix(case['wall_salt'], (y & 0xff)*256 + (x & 0xff)) % 3 == 0 else 0


def frustum_answer(case, x, y, r):
    return 1 if mix(bits(x), bits(y) ^ bits(r) ^ case['frustum_salt']) % 5 else 0


# --------------------------------------------------------------------------
# Client memory and stubs.

class Client:
    def __init__(self, m, case):
        self.m, self.case = m, case
        self.rand_state, self.rand_calls = case['seed'] & 0xffffffff, 0
        self.log = []
        n = len(case['owners'])
        self.chars = [am.undefined_region(f'char{k}', char_addr(k), CHAR_SIZE) for k in range(n)]
        self.heap = am.undefined_region('heap', HEAP_BASE, HEAP_SIZE)
        self.heap_next = HEAP_BASE
        self.models = am.undefined_region('models', MODEL_BASE, MODEL_SLOT*len(case['model_types']))
        for i, t in enumerate(case['model_types']):
            b = MODEL_BASE + i*MODEL_SLOT
            self.models.define(b + 0x22, struct.pack('<h', 60))
            self.models.define(b + 0x30, struct.pack('<I', ACTIONS + i*0x2000))
            self.models.define(b + 0x84, struct.pack('<3f', *case['body_angle']))
        self.actions = am.undefined_region('actions', ACTIONS, 0x2000*len(case['model_types']))
        for i, t in enumerate(case['model_types']):
            for a in range(0x200):
                self.actions.define(ACTIONS + i*0x2000 + a*0x10 + 8, struct.pack('<h', keys_answer(case, t, a)))
        self.mount = am.undefined_region('mount', MOUNT_REC, 0x100)
        self.wall = am.defined_region('wall', WALL, b''.join(struct.pack('<H', wall_answer(case, i & 0xff, i >> 8))
                                                              for i in range(0x10000)), writable=False)
        self.net = am.defined_region('net', NET, struct.pack('<III', 0, 0, case['requested']))
        self.parent = am.defined_region('parent', PARENT, bytes(0x30))
        o0 = case['owners'][0]
        self.info = am.undefined_region('info', 0x24c00000, 0x20)
        self.info.define(0x24c00000, struct.pack('<i', o0['info_type']))
        self.info.define(0x24c00010, bytes([o0['info_level']]))
        self.step = 0
        self.pets = {}   # owner -> address

    def new(self, size):
        addr = (self.heap_next + 15) & ~15
        self.heap_next = addr + size
        if self.heap_next > HEAP_BASE + HEAP_SIZE:
            raise RuntimeError('heap exhausted')
        return addr

    def set_owners(self, owners):
        for k, o in enumerate(owners):
            r = self.chars[k]
            b = r.base
            r.define(b + 0x04, bytes([o['safe']]))
            r.define(b + 0x180, struct.pack('<ii', *o['tile']))
            r.define(b + 0x31f0, struct.pack('<I', self.pets.get(k, 0)))
            r.define(b + 0x31f8, struct.pack('<i', o['pet_item']))
            r.define(b + 0x3204, struct.pack('<H', o['pet_level']))
            r.define(b + 0x322e, struct.pack('<H', o['ride']))
            r.define(b + 0x3e, struct.pack('<h', k))
            ob = b + CHAR_OBJ
            r.define(ob + 0x2a, struct.pack('<H', o['action']))
            r.define(ob + 0x5c, struct.pack('<i', o['type']))
            r.define(ob + 0xa0, struct.pack('<f', o['scale']))
            r.define(ob + 0xd0, struct.pack('<f', o['frame']))
            r.define(ob + 0x158, struct.pack('<3f', *o['position']))

    def read_owner_state(self, k):
        raw = bytes(self.chars[k].data)
        return {'pet': struct.unpack('<I', raw[0x31f0:0x31f4])[0] != 0,
                'item': struct.unpack('<i', raw[0x31f8:0x31fc])[0],
                'level': struct.unpack('<H', raw[0x3204:0x3206])[0]}

    def pet_owner(self, addr):
        for k, a in self.pets.items():
            if a == addr:
                return k
        return -1

    def label(self, addr):
        k = owner_of_object(addr)
        if k >= 0:
            return ('owner', k)
        for k, a in self.pets.items():
            if addr == a + PET_OBJ:
                return ('pet', k)
        return ('?', hex(addr))

    def globals(self, s):
        return [am.defined_region('world', WORLD, struct.pack('<i', s['world']), writable=False),
                am.defined_region('tick', TICK, struct.pack('<I', s['tick']), writable=False),
                am.defined_region('hero', HERO, struct.pack('<I', char_addr(0) if self.case['hero'] else 0x20000000),
                                  writable=False),
                am.defined_region('world-time', WORLD_TIME, struct.pack('<f', s['time']), writable=False),
                am.defined_region('trig-flag', vh.TRIG_FLAG, struct.pack('<I', 1), writable=False),
                am.defined_region('crt-mode', vh.CRT_MATH_MODE, struct.pack('<I', self.case.get('crt_mode', 1)),
                                  writable=False),
                am.defined_region('cookie', vh.COOKIE, struct.pack('<I', 0xbb40e64e), writable=False)]

    def regions(self, s):
        return [*self.globals(s), *self.chars, self.heap, self.models, self.actions, self.mount, self.wall, self.net,
                self.parent, self.info]

    def model_addr(self, index):
        slot = model_slot(self.case, index)
        return 0 if slot is None else MODEL_BASE + slot*MODEL_SLOT

    def model_type(self, addr):
        return self.case['model_types'][(addr - MODEL_BASE)//MODEL_SLOT]

    def stubs(self, s):
        case, log = self.case, self.log
        owners = case['owners']

        def rand(m):
            self.rand_state = (self.rand_state*214013 + 2531011) & 0xffffffff
            self.rand_calls += 1
            return (self.rand_state >> 16) & 0x7fff

        def terrain(m):
            x, y = m.float_argument(0), m.float_argument(1)
            log.append(('height', x, y))
            return m.return_float(height_answer(case, x, y))

        def frustum(m):
            x, y, r = m.float_argument(0), m.float_argument(1), m.float_argument(2)
            log.append(('frustum', x, y, r))
            return frustum_answer(case, x, y, r)

        def container(m):
            return 0x24f00000

        def model_get(m):
            return self.model_addr(m.argument(0)), 4

        def animate(m):
            model = m.ecx()
            action = struct.unpack('<H', bytes(m.uc.mem_read(model + 0xa8, 2)))[0]
            fp = m.argument(0)
            frame = m.read_floats(fp, 1)[0]
            speed = m.float_argument(3)
            o = fp - 0xd0
            ok = (m.argument(1) == o + 0xd4 and m.argument(2) == o + 0x2c and m.argument(4) == o + 0x158 and
                  m.argument(5) == o + 0x164)
            log.append(('animate', self.label(o), self.model_type(model), action, speed, frame, ok))
            return anim_answer(case, self.step, action, bits(frame), bits(speed)), 0x18

        def set_action(m):
            log.append(('set_action', self.label(m.argument(0)), m.argument(1)))
            return 0

        def kill(m):
            return 0

        def particle(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            log.append(('particle', m.argument(0), pos, ang, light, m.argument(4), m.float_argument(5),
                        m.argument(6), m.argument(7)))
            return 0

        def sound(m):
            log.append(('sound', m.argument(0), self.label(m.argument(1))))
            return 0

        def buff(m):
            lst, ident = m.ecx(), m.argument(0)
            k = owner_of_object(lst - 0x358)   # the object's list (+0x358) is the character's c + 0x35ac
            if k >= 0:
                key = {0x12: 'buff_12', 0x3d: 'buff_3d', 0xb2: 'buff_b2', 0x118: 'buff_118'}.get(ident)
                return (owners[k][key] if key else 0), 4
            raise RuntimeError(f'buff list {lst:#x} {ident:#x}')

        def bone_get(m):
            obj, bone = m.ecx(), m.argument(0)
            k = owner_of_object(obj)
            which = 0
            if k < 0:
                k, which = self.pet_owner(obj - PET_OBJ), 1
            log.append(('bone', which, k, bone))
            if not bone_present(case, which, k, bone):
                return 0, 4
            return BONE_TOKEN + which*0x100000 + k*0x10000 + bone*0x30, 4

        def token(t):
            t -= BONE_TOKEN
            return t // 0x100000, (t % 0x100000)//0x10000, (t % 0x10000)//0x30

        def transform(m):
            model, matrix, vec, out, tr = m.ecx(), m.argument(0), m.argument(1), m.argument(2), m.argument(3)
            which, k, bone = token(matrix)
            v = m.read_floats(vec, 3)
            mt = self.model_type(model)
            log.append(('transform', mt, which, k, bone, v, tr))
            m.local_write(out, struct.pack('<3f', *bone_answer(case, mt, which, k, bone, v, tr & 0xff)))
            return 0, 0x10

        def transform_base(m):
            model, out, matrix, base, vec = m.ecx(), m.argument(0), m.argument(1), m.argument(2), m.argument(3)
            which, k, bone = token(matrix)
            v, b = m.read_floats(vec, 3), m.read_floats(base, 3)
            mt = self.model_type(model)
            log.append(('transform_base', mt, which, k, bone, b, v))
            m.local_write(out, struct.pack('<3f', *bone_base_answer(case, mt, which, k, bone, b, v)))
            return 0, 0x10

        def new(m):
            return self.new(m.argument(0))

        def bones_alloc(m):
            obj = m.ecx()
            m.write(obj + 0x318, struct.pack('<I', 0x31000000 + (obj & 0xfffff)))
            return 0, 4

        def manager_get(m):
            return 0x24e00000

        def mount_find(m):
            k = owner_of_char(m.argument(0))
            if k >= 0 and owners[k]['has_mount']:
                m.write(MOUNT_REC + 0x24, struct.pack('<3f', 0.0, 0.0, owners[k]['mount_offset_z']))
                return MOUNT_REC, 4
            return 0, 4

        def mount_state(m):
            k = owner_of_char(m.argument(0))
            assert m.argument(1) == 2 and m.argument(2) & 0xff == 1
            return (owners[k]['mount_state2'] if k >= 0 else 0), 0xc

        def chars_get(m):
            return 0x24d00000

        def find_char(m):
            log.append(('find', m.argument(0) & 0xffff))
            return 0, 4

        def pk_ctor(m):
            return m.ecx()

        def pk_head(m):
            return m.ecx(), 8

        def pk_put(m):
            return m.ecx(), 4

        def pk_send(m):
            log.append(('request',))
            return 0, 8

        def pk_dtor(m):
            return 0

        def delete(m):
            c = m.argument(0)
            k = owner_of_char(c)
            m.write(c + 0x31f0, struct.pack('<I', 0))
            self.pets.pop(k, None)
            return 0

        def later_class(m):
            k = owner_of_char(m.argument(0))
            log.append(('unsupported', k, m.argument(1)))
            return 0, 8

        def render_object(m):
            o = m.argument(0)
            log.append(('object', self.label(o), tuple(m.argument(i) for i in range(1, 6))))
            return 0

        def memset(m):
            dst, value, count = m.argument(0), m.argument(1), m.argument(2)
            m.local_write(dst, bytes([value & 0xff])*count)
            return dst

        def memcpy(m):
            dst, src, count = m.argument(0), m.argument(1), m.argument(2)
            m.local_write(dst, bytes(m.uc.mem_read(src, count)))
            return dst

        def char_info(m):   # 0x0129dabe(c, 0): the hero's pet record
            k = owner_of_char(m.ecx())
            if not owners[k]['has_info']:
                return 0, 4
            return 0x24c00000, 4

        return {RAND: rand, TERRAIN: terrain, FRUSTUM: frustum, CONTAINER_GET: container, MODEL_GET: model_get,
                ANIMATE: animate, SET_ACTION: set_action, KILL: kill, PARTICLE: particle, SOUND: sound, BUFF: buff,
                BONE_GET: bone_get, TRANSFORM: transform, TRANSFORM_BASE: transform_base, NEW: new,
                BONES_ALLOC: bones_alloc, MANAGER_GET: manager_get, MOUNT_FIND: mount_find, MOUNT_STATE: mount_state,
                CHARS_GET: chars_get, FIND_CHAR: find_char, PK_CTOR: pk_ctor, PK_HEAD: pk_head, PK_PUT: pk_put,
                PK_SEND: pk_send, PK_DTOR: pk_dtor, DELETE: delete, LATER_CLASS: later_class,
                RENDER_OBJECT: render_object, 0x0129dabe: char_info, 0x0194cd00: memset, 0x0194c200: memcpy}


class Machine(vh.Machine):
    """validate_helpers' machine; an AND with an immediate 0 (a store of zero by read-modify-write, as the
    vector clear 0x0095e08c does) (or an OR with -1) does not count as a read of undefined bytes."""

    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_READ, UC_PROT_EXEC
        target = struct.unpack('<I', data[GL_COLOR3 - am.DATA_BASE:GL_COLOR3 - am.DATA_BASE + 4])[0]
        self.gl_color3 = target
        page = target & ~0xfff
        if page != self.gl_color4 & ~0xfff:
            self.uc.mem_map(page, am.PAGE, UC_PROT_READ | UC_PROT_EXEC)
            self.uc.mem_write(page, b'\xcc'*am.PAGE)

    def access(self, uc, access, address, size, value, regions):
        if access != self.UC_MEM_WRITE:
            for region in regions:
                if region.base <= address and address + size <= region.end:
                    offset = address - region.base
                    if b'\0' in region.defined[offset:offset + size] and self._and_zero():
                        return
                    break
        return super().access(uc, access, address, size, value, regions)

    def _and_zero(self):
        code = bytes(self.uc.mem_read(self.pc(), 8))
        if code[0] == 0x83 and (code[1] >> 3) & 7 in (1, 4):   # or r/m32, -1 / and r/m32, 0
            mod, rm = code[1] >> 6, code[1] & 7
            n = 2 + (1 if rm == 4 and mod != 3 else 0) + {0: 0, 1: 1, 2: 4}.get(mod, 0)
            if mod == 0 and rm == 5:
                n += 4
            return code[n] == (0 if (code[1] >> 3) & 7 == 4 else 0xff)
        return False


# --------------------------------------------------------------------------
# Native side.

class Native:
    def __init__(self, lib, case, plant=None):
        self.lib, self.case, self.plant = lib, case, plant
        self.log = []
        n = len(case['owners'])
        self.owners = (Owner*max(n, 1))()
        self.r = Raven()
        self.step = 0
        self.host = self._host()
        lib.mu_rv_init(ctypes.byref(self.r), case['seed'] & 0xffffffff, self.owners, n, ctypes.byref(self.host))
        self.r.requested = case['requested']

    def set_owners(self, owners):
        for k, o in enumerate(owners):
            w = self.owners[k]
            w.live = 1
            w.hero = 1 if (k == 0 and self.case['hero']) else 0
            w.safe = o['safe']
            w.tile[0], w.tile[1] = o['tile']
            w.pet_item, w.pet_level, w.ride = o['pet_item'], o['pet_level'], o['ride']
            w.action, w.type, w.scale, w.frame = o['action'], o['type'], o['scale'], o['frame']
            for i in range(3):
                w.position[i] = o['position'][i]
            w.buff_12, w.buff_3d, w.buff_b2, w.buff_118 = o['buff_12'], o['buff_3d'], o['buff_b2'], o['buff_118']
            w.has_mount, w.mount_offset_z, w.mount_state2 = o['has_mount'], o['mount_offset_z'], o['mount_state2']
            w.has_info, w.info_type, w.info_level = o['has_info'], o['info_type'], o['info_level']

    def read_owners(self, owners):
        for k, o in enumerate(owners):
            o['pet_item'], o['pet_level'] = self.owners[k].pet_item, self.owners[k].pet_level

    def label(self, addr):
        base = ctypes.addressof(self.r.pets)
        size = ctypes.sizeof(Pet)
        k, r = divmod(addr - base - Pet.object.offset, size)
        if 0 <= k < 16 and r == 0:
            return ('pet', k)
        return ('?', addr)

    def _host(self):
        case, log, plant = self.case, self.log, self.plant

        def v3(p):
            return tuple(f32(x) for x in ctypes.cast(p, ctypes.POINTER(ctypes.c_float))[:3])

        def has_model(ctx, model):
            return 1 if model_slot(case, model) is not None else 0

        def action_keys(ctx, model, action):
            return keys_answer(case, model, action)

        def animate(ctx, o, model, speed):
            ob = ctypes.cast(o, ctypes.POINTER(Obj)).contents
            log.append(('animate', self.label(o), model, ob.action, f32(speed), f32(ob.frame), True))
            return anim_answer(case, self.step, ob.action, bits(ob.frame), bits(speed))

        def set_action(ctx, o, action):
            log.append(('set_action', self.label(o), action))

        def bone(ctx, which, k, b):
            log.append(('bone', which, k, b))
            return bone_present(case, which, k, b)

        def transform(ctx, model, which, k, b, v, out, tr):
            vv = v3(v)
            log.append(('transform', model, which, k, b, vv, tr))
            o = ctypes.cast(out, ctypes.POINTER(ctypes.c_float))
            ans = bone_answer(case, model, which, k, b, vv, tr)
            for j in range(3):
                o[j] = ans[j]

        def transform_base(ctx, model, which, k, b, base, v, out):
            vv, bb = v3(v), v3(base)
            log.append(('transform_base', model, which, k, b, bb, vv))
            o = ctypes.cast(out, ctypes.POINTER(ctypes.c_float))
            ans = bone_base_answer(case, model, which, k, b, bb, vv)
            for j in range(3):
                o[j] = ans[j]

        def particle(ctx, bitmap, p, a, light, subtype, scale):
            log.append(('particle', bitmap, v3(p), v3(a), v3(light), subtype, f32(scale), 0, 0))

        def sound(ctx, ident, k):
            log.append(('sound', ident, ('pet', k)))

        def request(ctx, k, slot):
            log.append(('request',))

        def terrain(ctx, x, y):
            x, y = f32(x), f32(y)
            log.append(('height', x, y))
            return height_answer(case, x, y)

        def wall(ctx, x, y):
            return wall_answer(case, x, y)

        def origin(ctx, model, p):
            self.model_origin = (model, v3(p))

        def body_angle(ctx, model, out):
            o = ctypes.cast(out, ctypes.POINTER(ctypes.c_float))
            for j in range(3):
                o[j] = case['body_angle'][j]

        def parent(ctx, mtx):
            self.parent = bytes(ctypes.string_at(mtx, 0x30))

        def find(ctx, key):
            log.append(('find', key & 0xffff))
            return 0

        def unsupported(ctx, k, item):
            log.append(('unsupported', k, item))

        self.callbacks = [HAS_MODEL_FN(has_model), KEYS_FN(action_keys), ANIMATE_FN(animate),
                          SET_ACTION_FN(set_action), BONE_FN(bone), TRANSFORM_FN(transform),
                          TRANSFORM_BASE_FN(transform_base), PARTICLE_FN(particle), SOUND_FN(sound),
                          REQUEST_FN(request), TERRAIN_FN(terrain), WALL_FN(wall), ORIGIN_FN(origin),
                          ANGLE_FN(body_angle), MATRIX_FN(parent), FIND_FN(find), UNSUPPORTED_FN(unsupported)]
        return Host(None, *self.callbacks)

    def render_host(self):
        case, log = self.case, self.log

        def frustum(ctx, x, y, r):
            x, y, r = f32(x), f32(y), f32(r)
            log.append(('frustum', x, y, r))
            return frustum_answer(case, x, y, r)

        def draw_object(ctx, o, k, a3):
            log.append(('object', self.label(o), (0, 0, a3 & 0xffffffff, 0xffffffff, 0xffffffff)))

        self.rcallbacks = [FRUSTUM_FN(frustum), DRAW_OBJECT_FN(draw_object)]
        return RenderHost(None, *self.rcallbacks)


# --------------------------------------------------------------------------
# Cases.

PET_VALUES = [1, 1, 2, 2, 3, 3, 0, 10, 13]


def random_owner(rng, k):
    safe = 1 if rng.random() < 0.35 else 0
    tx, ty = rng.randrange(-2, 256), rng.randrange(0, 256)
    return {'safe': safe, 'tile': [tx, ty], 'pet_item': -1, 'pet_level': 0,
            'ride': rng.choice([0, 0, 0, 0x1a04, 0x28f7, 0x1a25, 0x1a02]),
            'action': rng.randrange(0, 0x150), 'type': 0xa91 if rng.random() < 0.9 else 0x3f2,
            'scale': f32(rng.uniform(0.8, 1.3)), 'frame': f32(rng.uniform(0, 12)),
            'position': [f32(tx*100.0 + rng.uniform(0, 100)), f32(ty*100.0 + rng.uniform(0, 100)),
                         f32(rng.uniform(0, 300))],
            'buff_12': 1 if rng.random() < 0.1 else 0, 'buff_3d': 1 if rng.random() < 0.03 else 0,
            'buff_b2': 1 if rng.random() < 0.03 else 0, 'buff_118': 1 if rng.random() < 0.03 else 0,
            'has_mount': 1 if rng.random() < 0.3 else 0, 'mount_offset_z': f32(rng.uniform(0, 80)),
            'mount_state2': 1 if rng.random() < 0.2 else 0, 'has_info': 1 if rng.random() < 0.8 else 0,
            'info_type': rng.choice([-1, 5, 5, 5]), 'info_level': rng.randrange(0, 60),
            'bones': rng.choice([0x40, 0x40, 0x40, 0x23, 0])}


def session_case(rng, index):
    n = rng.randrange(1, 4)
    owners = [random_owner(rng, k) for k in range(n)]
    types = [0xa91, 0x411, 0x748]
    if rng.random() < 0.08:
        types.remove(rng.choice([0x411, 0x748]))
    case = {'seed': rng.getrandbits(32), 'owners': owners, 'height_base': float(rng.randrange(0, 200)),
            'frustum_salt': rng.getrandbits(32), 'bone_salt': rng.getrandbits(16), 'keys_salt': rng.getrandbits(16),
            'anim_salt': rng.getrandbits(32), 'wall_salt': rng.getrandbits(32),
            'world': rng.choice([0, 0, 0, 2, 3, 0x37, 0x12, 10, 0x84]), 'crt_mode': rng.choice([0, 1]),
            'model_types': types, 'hero': rng.choice([0, 1]), 'requested': rng.choice([0, 1, 1]),
            'pet_bones': [rng.choice([0x50, 0x50, 0x50, 0x42, 0x10]) for _ in range(n)],
            'body_angle': [f32(rng.uniform(-30, 30)), f32(rng.uniform(-30, 30)), f32(rng.uniform(0, 360))],
            'tick': rng.getrandbits(16), 'time': f32(rng.uniform(0, 1e6))}
    steps = []
    for k in range(n):
        if rng.random() < 0.85:
            steps.append(('set', k, rng.choice(PET_VALUES)))
    if rng.random() < 0.06:   # a long chase: the owner far away (the lost counter and the reset)
        steps.append(('far', rng.getrandbits(32)))
        steps.extend([('move',)]*rng.randrange(95, 130))
    for _ in range(rng.randrange(10, 60)):
        r = rng.random()
        if r < 0.6:
            steps.append(('move',))
        elif r < 0.75:
            steps.append(('render',))
        elif r < 0.93:
            steps.append(('owners', rng.getrandbits(32)))
        else:
            steps.append(('set', rng.randrange(n), rng.choice(PET_VALUES)))
    case['steps'] = steps
    return case


def jitter_owners(owners, seed):
    rng = random.Random(seed)
    for o in owners:
        if rng.random() < 0.15:
            o['position'][0] = f32(o['position'][0] + rng.uniform(-900, 900))
        for i in range(2):
            o['position'][i] = f32(o['position'][i] + rng.uniform(-60, 60))
        o['position'][2] = f32(o['position'][2] + rng.uniform(-40, 40))
        o['frame'] = f32(rng.uniform(0, 12))
        if rng.random() < 0.3:
            o['action'] = rng.randrange(0, 0x150)
        if rng.random() < 0.12:
            o['safe'] = 1 - o['safe']
        if rng.random() < 0.08:
            o['buff_12'] = 1 - o['buff_12']
        if rng.random() < 0.1:
            o['has_mount'] = 1 - o['has_mount']


def compare_pets(client, native, n):
    for k in range(n):
        addr = client.pets.get(k)
        np = native.r.pets[k]
        if (addr is not None) != bool(np.live):
            return f'pet {k} presence client {addr is not None} native {np.live}'
        if addr is None:
            continue
        raw = bytes(client.heap.data[addr - HEAP_BASE:addr - HEAP_BASE + PET_SIZE])
        c_obj = fields_tuple(OBJECT_FIELDS, raw, PET_OBJ)
        n_obj = ctypes_tuple(OBJECT_FIELDS, np.object)
        for (name, a), (_, b) in zip(c_obj, n_obj):
            if not same(tuple(f32(x) if isinstance(x, float) else x for x in a), b):
                return f'pet {k} object {name}: client {a} native {b}'
        c_pet = fields_tuple(PET_FIELDS, raw)
        n_pet = ctypes_tuple(PET_FIELDS, np)
        for (name, a), (_, b) in zip(c_pet, n_pet):
            if not same(a, b):
                return f'pet {k} {name}: client {a} native {b}'
        owner = struct.unpack('<I', raw[4:8])[0]
        if owner_of_char(owner) != np.owner:
            return f'pet {k} owner'
        if struct.unpack('<I', raw[8:12])[0] != 0 or np.target != -1:
            return f'pet {k} target'
    return None


def run_session(m, lib, case, plant=None):
    client, native = Client(m, case), Native(lib, case, plant)
    owners = case['owners']
    n = len(owners)
    s = {'world': case['world'], 'tick': case['tick'], 'time': case['time']}
    inputs = Inputs(s['world'], s['tick'])
    if plant == 'world':
        inputs.world = 0x37 if s['world'] != 0x37 else 0
    rhost = native.render_host()
    stats = {'steps': 0, 'events': 0, 'moves': 0, 'renders': 0, 'sets': 0, 'pet_steps': 0}
    for index, step in enumerate(case['steps']):
        kind = step[0]
        if kind == 'owners':
            jitter_owners(owners, step[1])
            continue
        if kind == 'far':
            r = random.Random(step[1])
            for o in owners:
                o['position'][0] = f32(o['position'][0] + r.choice([-1, 1])*r.uniform(4000, 9000))
                o['safe'] = 0
            continue
        targets = [step[1]] if kind == 'set' else list(range(n))
        for k in targets:
            if kind != 'set' and k not in client.pets and not native.r.pets[k].live:
                continue
            client.step = native.step = index*8 + k
            client.set_owners(owners)
            native.set_owners(owners)
            client.log.clear()
            native.log.clear()
            stubs = client.stubs(s)
            regions = client.regions(s)
            before = client.heap_next
            if kind == 'set':
                res = m.execute(SET_TYPE, [char_addr(k), step[2]], regions, stubs)
                lib.mu_rv_set_type(ctypes.byref(native.r), ctypes.byref(inputs), k, step[2])
                stats['sets'] += 1
            elif kind == 'move':
                res = m.execute(MOVE, [char_addr(k)], regions, stubs)
                lib.mu_rv_move(ctypes.byref(native.r), ctypes.byref(inputs), k)
                stats['moves'] += 1
            else:
                res = m.execute(RENDER, [char_addr(k)], regions, stubs)
                lib.mu_rv_render(ctypes.byref(native.r), ctypes.byref(inputs), k, ctypes.byref(rhost))
                stats['renders'] += 1
            if not res['ok']:
                return {'ok': False, 'step': index, 'kind': step, 'owner': k,
                        'machine': {kk: v for kk, v in res.items() if kk != 'regions'}, 'log': client.log[-8:]}
            for r in regions:
                if r.name in res['regions']:
                    r.data[:] = res['regions'][r.name]
            # a fresh pet (operator new inside the step)
            ptr = struct.unpack('<I', bytes(client.chars[k].data[0x31f0:0x31f4]))[0]
            if ptr:
                client.pets[k] = ptr
            else:
                client.pets.pop(k, None)
            st = client.read_owner_state(k)
            owners[k]['pet_item'], owners[k]['pet_level'] = st['item'], st['level']
            nw = native.owners[k]
            if (nw.pet_item, nw.pet_level) != (st['item'], st['level']):
                return {'ok': False, 'step': index, 'kind': step, 'why': 'owner pet fields',
                        'client': st, 'native': (nw.pet_item, nw.pet_level)}
            stats['steps'] += 1
            stats['events'] += len(client.log)
            if ptr:
                stats['pet_steps'] += 1
            if not same_log(client.log, native.log):
                return {'ok': False, 'step': index, 'kind': step, 'owner': k, 'why': 'log',
                        'client': client.log[:40], 'native': native.log[:40]}
            if (client.rand_state, client.rand_calls) != (native.r.rand_state, native.r.rand_calls):
                return {'ok': False, 'step': index, 'kind': step, 'why': 'rand'}
            if client.net.data[8] != native.r.requested:
                return {'ok': False, 'step': index, 'kind': step, 'why': 'request flag'}
            why = compare_pets(client, native, n)
            if why:
                return {'ok': False, 'step': index, 'kind': step, 'owner': k, 'why': why, 'log': client.log[:20]}
            if getattr(native, 'parent', None) is not None and bytes(client.parent.data) != native.parent:
                return {'ok': False, 'step': index, 'kind': step, 'why': 'parent matrix'}
    return {'ok': True, 'stats': stats}


def section_sessions(m, lib, args, report):
    rng = random.Random(args.seed)
    total = {'cases': 0, 'steps': 0, 'events': 0, 'moves': 0, 'renders': 0, 'sets': 0, 'pet_steps': 0}
    failures = []
    m.add_probes(PROBES)
    for i in range(args.cases):
        case = session_case(rng, i)
        res = run_session(m, lib, case)
        total['cases'] += 1
        if not res['ok']:
            failures.append({'case': i, **res})
            if len(failures) >= 3:
                break
            continue
        for key, v in res['stats'].items():
            total[key] += v
    total['mismatches'] = len(failures)
    total['probes'] = {PROBES[a]: c for a, c in m.probes.items() if a in PROBES}
    total['probes_hit'] = sum(1 for a in PROBES if m.probes.get(a))
    report['sessions'] = {'total': total, 'failures': failures}
    return not failures


PROBES = {
    0x009ed059: 'move: fade in', 0x009ed132: 'move: fade out near', 0x009ed15b: 'move: fade out far',
    0x009ed1d0: 'move: buff return', 0x009ed236: 'move: request', 0x009ed53f: 'move: safe -> ai 3',
    0x009ed589: 'move: anim end ai 1', 0x009ed597: 'move: anim end ai 0', 0x009ed5a5: 'move: anim end ai 3',
    0x009eda66: 'fly: sparkle', 0x009edb42: 'fly: turn', 0x009edd37: 'fly: horse altitude',
    0x009edd60: 'fly: ride-state altitude', 0x009edda9: 'fly: climb', 0x009ede49: 'fly: sink',
    0x009edef1: 'fly: far direction', 0x009edf21: 'fly: near direction', 0x009ee0fc: 'fly: ai 0',
    0x009ee115: 'fly: ai 1', 0x009ee12e: 'fly: fade-in drop', 0x009ee6d4: 'sit: raven moves',
    0x009eeb3e: 'sit: raven arrives', 0x009eec66: 'sit: soul', 0x009eee55: 'sit: soul near', 0x009eeeb7: 'sit: soul far',
    0x009ef408: 'tail: sound', 0x009ef5df: 'tail: lost count', 0x009ef5f9: 'tail: reset', 0x00c9311c: 'move: re-create',
    0x00c93144: 'move: model swap', 0x009ef77a: 'render: invisible', 0x009ef7e7: 'render: draw',
    0x009ecf0d: 'ctor: no bone raven', 0x009ecec6: 'ctor: no bone soul', 0x009ecdb9: 'ctor: negative tile',
}


# --------------------------------------------------------------------------
# The render functors.

def sx(v):
    return v - 0x100000000 if v >= 0x80000000 else v


class DrawClient:
    def __init__(self, m, case):
        self.m, self.case = m, case
        self.log = []
        self.model = am.undefined_region('model', MODEL_BASE, MODEL_SLOT)
        self.model.define(MODEL_BASE + 0x54, struct.pack('<3f', *case['color']))
        self.obj = am.undefined_region('object', 0x24300000, 0x3d8)
        o = case['object']
        b = 0x24300000
        for name, off, fmt, count in OBJECT_FIELDS:
            v = o[name]
            vals = list(v) if count > 1 else [v]
            self.obj.define(b + off, struct.pack('<' + fmt*count, *vals))
        self.event = am.undefined_region('event', 0x24a00000, 0x100)

    def regions(self):
        c = self.case
        return [am.defined_region('world', WORLD, struct.pack('<i', c['world']), writable=False),
                am.defined_region('world-time', WORLD_TIME, struct.pack('<f', c['time']), writable=False),
                am.defined_region('trig-flag', vh.TRIG_FLAG, struct.pack('<I', 1), writable=False),
                am.defined_region('crt-mode', vh.CRT_MATH_MODE, struct.pack('<I', 1), writable=False),
                am.defined_region('cookie', vh.COOKIE, struct.pack('<I', 0xbb40e64e), writable=False),
                self.model, self.obj, self.event]

    def color(self, m):
        return m.read_floats(MODEL_BASE + 0x54, 3)

    def stubs(self):
        case, log = self.case, self.log

        def mesh(m):   # thiscall (the model), 8 arguments
            assert m.ecx() == MODEL_BASE
            a = [m.argument(i) for i in range(8)]
            log.append(('mesh', a[0], a[1], from_bits(a[2]), sx(a[3]), from_bits(a[4]), from_bits(a[5]),
                        from_bits(a[6]), sx(a[7]), self.color(m)))
            return 0, 0x20

        def body(m):   # thiscall (the model), 8 arguments
            assert m.ecx() == MODEL_BASE
            a = [m.argument(i) for i in range(8)]
            log.append(('body', a[0], from_bits(a[1]), sx(a[2]), from_bits(a[3]), from_bits(a[4]), from_bits(a[5]),
                        sx(a[6]), sx(a[7]), self.color(m)))
            return 0, 0x20

        def push(m):
            log.append(('push', m.float_argument(0)))
            return 0, 4

        def pop(m):
            log.append(('pop',))
            return 0

        def color3(m):
            log.append(('color3', m.float_argument(0), m.float_argument(1), m.float_argument(2)))
            return 0, 0xc

        def color4(m):
            log.append(('color4', *(m.float_argument(i) for i in range(4))))
            return 0, 0x10

        def alpha_test(m):
            log.append(('alpha_test', m.argument(0)))
            return 0

        def shadow(m):
            origin = m.read_floats(MODEL_BASE + 0x78, 3)
            log.append(('shadow', tuple(m.argument(i) for i in range(5)), origin))
            return 0, 0x14

        def terrain(m):
            x, y = m.float_argument(0), m.float_argument(1)
            log.append(('height', x, y))
            return m.return_float(height_answer(case, x, y))

        def sine(m):
            x = m.float_argument(0)
            log.append(('sine', x))
            return m.return_float(f32(math.sin(x)))

        def wave(m):
            a, b = m.float_argument(0), m.argument(1)
            log.append(('wave', a, b))
            return m.return_float(f32(case['wave']))

        def rfloat(m):
            lo, hi, n = m.float_argument(0), m.float_argument(1), m.argument(2)
            log.append(('rfloat', lo, hi, n))
            self.rcount = getattr(self, 'rcount', 0) + 1
            return m.return_float(f32(lo + (hi - lo)*((mix(case['rsalt'], self.rcount) % 1000)/1000.0)))

        def sprite(m):
            pos, light = m.read_floats(m.argument(1), 3), m.read_floats(m.argument(3), 3)
            log.append(('sprite', m.argument(0), pos, m.float_argument(2), light, m.argument(4) == 0x24300000,
                        m.argument(5), m.argument(6), m.argument(7)))
            return 0

        def particle(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            log.append(('particle', m.argument(0), pos, ang, light, m.argument(4), m.float_argument(5),
                        m.argument(6) == 0x24300000, m.argument(7)))
            return 0

        def flag(name):
            def f(m):
                return case[name]
            return f

        def event_get(m):
            return 0x24a00000

        def event_block(m):
            return case['event_block'], 0

        return {RENDER_MESH: mesh, RENDER_BODY: body, PUSH: push, POP: pop, self.m.gl_color3: color3, self.m.gl_color4: color4,
                ALPHA_TEST: alpha_test, SHADOW: shadow, TERRAIN: terrain, SINE: sine, WAVE: wave, RANDOM_FLOAT: rfloat,
                SPRITE: sprite, PARTICLE: particle, SHADOW_WORLD: flag('shadow_world'), EVENT_GET: event_get,
                EVENT_BLOCK: event_block, DIM_WORLD: flag('dim_world')}


def native_draw_log(lib, case, plant=None):
    o = Obj()
    for name, off, fmt, count in OBJECT_FIELDS:
        v = case['object'][name]
        if count > 1:
            arr = getattr(o, name)
            for i, x in enumerate(v):
                arr[i] = x
        else:
            setattr(o, name, v)
    log = []
    state = {'r': 0}

    def sine(ctx, x):
        log.append(('sine', f32(x)))
        return f32(math.sin(f32(x)))

    def wave(ctx, a, b):
        log.append(('wave', f32(a), b))
        return f32(case['wave'])

    def rfloat(ctx, lo, hi, n):
        lo, hi = f32(lo), f32(hi)
        log.append(('rfloat', lo, hi, n))
        state['r'] += 1
        return f32(lo + (hi - lo)*((mix(case['rsalt'], state['r']) % 1000)/1000.0))

    def terrain(ctx, x, y):
        log.append(('height', f32(x), f32(y)))
        return height_answer(case, f32(x), f32(y))

    cbs = [SINE_FN(sine), WAVE_FN(wave), RFLOAT_FN(rfloat), TERRAIN_FN(terrain)]
    host = DrawHost(None, *cbs)
    di = DrawInputs(case['world'], case['time'], case['shadow_world'], case['event_block'], case['dim_world'],
                    V3(*case['color']))
    out = DrawList()
    # the calls the host makes are interleaved with the draws in the client; rebuild the client order
    fn = lib.mu_rv_draw_raven if case['model'] == 0x411 else lib.mu_rv_draw_soul
    fn(ctypes.byref(o), ctypes.byref(di), ctypes.byref(host), ctypes.byref(out))
    return o, log, [out.items[i] for i in range(out.count)]


def expected_client_log(case, o, hlog, draws):
    """The client-shaped call log of the C's draw list (host calls placed where the client makes them)."""
    seq = []
    hl = list(hlog)

    def take(kind):
        for i, e in enumerate(hl):
            if e[0] == kind:
                return hl.pop(i)
        return None

    def v(t):
        return tuple(f32(x) for x in t)

    for d in draws:
        if d.kind == 1:
            seq.append(('color3', *v(d.vector)))
        elif d.kind == 2:
            seq.append(('push', f32(d.alpha)))
        elif d.kind == 3:
            seq.append(('pop',))
        elif d.kind == 4:
            seq.append(('body', d.flags, f32(d.alpha), d.blend_mesh, f32(d.blend_light), f32(d.uv[0]), f32(d.uv[1]),
                        d.hidden, d.texture, v(d.color)))
        elif d.kind == 5:
            if d.texture == 0x7fa5:
                seq.append(take('sine'))
            if case['model'] == 0x748 and d.mesh == 1 and any(x[0] == 'wave' for x in hl) and \
                    sum(1 for x in seq if x[0] == 'mesh' and x[1] == 1) == 1:
                seq.append(take('wave'))
            seq.append(('mesh', d.mesh, d.flags, f32(d.alpha), d.blend_mesh, f32(d.blend_light), f32(d.uv[0]),
                        f32(d.uv[1]), d.texture, v(d.color)))
        elif d.kind == 6:
            seq.append(('sprite', d.bitmap, v(d.vector), f32(d.scale), v(d.light), True, 0, 0, 4))
        elif d.kind == 7:
            for _ in range(4):
                seq.append(take('rfloat'))
            seq.append(('particle', d.bitmap, v(d.vector), v(o.angle), v(d.light), d.subtype, f32(d.scale), True, 0))
        elif d.kind == 8:
            seq.append(('alpha_test', 1))
            seq.append(('color4', 0.0, 0.0, 0.0, f32(d.alpha)))
            seq.append(take('height'))
            seq.append(('shadow', (0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0), v(d.vector)))
    return seq


def draw_case(rng, index):
    model = rng.choice([0x411, 0x411, 0x748])
    o = {name: (tuple(f32(rng.uniform(-500, 500)) for _ in range(count)) if fmt == 'f' and count > 1 else
                f32(rng.uniform(0, 1)) if fmt == 'f' else 0)
         for name, off, fmt, count in OBJECT_FIELDS}
    o['type'] = model
    o['level'] = rng.choice([0, 1, 19, 20, 21, 39, 40, 41, 100, 0x81, 0xff])
    o['blend_mesh'] = rng.choice([-1, -1, 0, 2])
    o['hidden_mesh'] = rng.choice([-1, -1, 3])
    o['angle'] = (f32(rng.uniform(0, 360)), f32(rng.uniform(0, 360)), f32(rng.choice([rng.uniform(0, 360), 358.5, 359.0])))
    o['position'] = (f32(rng.uniform(0, 25000)), f32(rng.uniform(0, 25000)), f32(rng.uniform(0, 500)))
    world = rng.choice([0, 0, 2, 10, 0x84, 7])
    return {'model': model, 'object': o, 'world': world, 'time': f32(rng.uniform(0, 1e6)),
            'shadow_world': 1 if rng.random() < 0.1 else 0, 'event_block': 1 if rng.random() < 0.1 else 0,
            'dim_world': 1 if world == 7 else 0, 'color': [f32(rng.uniform(0, 1.5)) for _ in range(3)],
            'wave': f32(rng.uniform(0, 1)), 'rsalt': rng.getrandbits(32), 'height_base': float(rng.randrange(0, 200))}


def run_draw(m, lib, case, plant=None):
    client = DrawClient(m, case)
    fn = DRAW_RAVEN if case['model'] == 0x411 else DRAW_SOUL
    res = m.execute(fn, [MODEL_BASE, 0x24300000, 0, 0, 0, 0, 0], client.regions(), client.stubs())
    if not res['ok']:
        return {'ok': False, 'machine': {k: v for k, v in res.items() if k != 'regions'}, 'log': client.log[-6:]}
    o, hlog, draws = native_draw_log(lib, case, plant)
    want = expected_client_log(case, o, hlog, draws)
    if not same_log(client.log, want):
        return {'ok': False, 'why': 'log', 'client': client.log, 'native': want}
    angle = struct.unpack('<3f', res['regions']['object'][0x164:0x170])
    if not same(tuple(f32(x) for x in angle), tuple(f32(x) for x in o.angle)):
        return {'ok': False, 'why': 'angle'}
    if res['eax'] & 0xff != 1:
        return {'ok': False, 'why': 'return'}
    return {'ok': True, 'calls': len(client.log)}


def section_draw(m, lib, args, report):
    rng = random.Random(args.seed + 7)
    total = {'cases': 0, 'calls': 0, 'raven': 0, 'soul': 0}
    failures = []
    for i in range(args.draw_cases):
        case = draw_case(rng, i)
        res = run_draw(m, lib, case)
        total['cases'] += 1
        total['raven' if case['model'] == 0x411 else 'soul'] += 1
        if not res['ok']:
            failures.append({'case': i, **res})
            if len(failures) >= 3:
                break
            continue
        total['calls'] += res['calls']
    total['mismatches'] = len(failures)
    report['draw'] = {'total': total, 'failures': failures}
    return not failures


# --------------------------------------------------------------------------

MUTATIONS = {1: 'sessions', 2: 'sessions', 3: 'sessions', 4: 'draw'}
NEGATIVE = ['world']


def run_mutations(m, args):
    caught = {}
    for n, section in MUTATIONS.items():
        lib = load_library(LIB.with_name(f'libclient_raven_m{n}.{SUFFIX}'), f'-DMU_RV_MUTATION={n}') \
            if False else None
        subprocess.run(['make', '-C', str(LIB.parent), '-B', f'CFLAGS=-std=c11 -O2 -fPIC -ffp-contract=off '
                        f'-fno-fast-math -DMU_RV_MUTATION={n}'], check=True, capture_output=True)
        tmp = LIB.with_name(f'libclient_raven_m{n}.{SUFFIX}')
        tmp.write_bytes(LIB.read_bytes())
        lib = load_library(tmp)
        rep = {}
        sub = argparse.Namespace(**vars(args))
        sub.cases, sub.draw_cases = min(args.cases, 60), min(args.draw_cases, 200)
        good = globals()['section_' + section](m, lib, sub, rep)
        caught[f'MU_RV_MUTATION={n}'] = not good
        tmp.unlink()
    subprocess.run(['make', '-C', str(LIB.parent), '-B'], check=True, capture_output=True)
    return caught


def run_negative(m, lib, args):
    rng = random.Random(args.seed + 99)
    out = {}
    for name in NEGATIVE:
        detected = 0
        for i in range(args.negative):
            case = session_case(rng, i)
            if case['world'] in (0x37,):
                continue
            res = run_session(m, lib, case, plant=name)
            detected += 0 if res['ok'] else 1
        out[name] = detected
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', default=str(vh.DEFAULT_TEXT))
    ap.add_argument('--data', default=str(vh.DEFAULT_DATA))
    ap.add_argument('--seed', type=int, default=20261022)
    ap.add_argument('--cases', type=int, default=200)
    ap.add_argument('--draw-cases', type=int, default=500)
    ap.add_argument('--negative', type=int, default=0)
    ap.add_argument('--sections', default='sessions,draw')
    ap.add_argument('--report', default=None)
    ap.add_argument('--mutations', action='store_true')
    args = ap.parse_args(argv)
    text, data = vh.load_inputs(args)
    lib = load_library()
    m = Machine(text, data)
    report = {'bodies': {name: hashlib.sha256(text[lo - am.TEXT_BASE:hi - am.TEXT_BASE]).hexdigest()[:16]
                         for name, (lo, hi) in BODIES.items()}, 'seed': args.seed}
    ok = True
    t0 = time.time()
    for name in [s for s in args.sections.split(',') if s]:
        s0 = time.time()
        good = globals()['section_' + name](m, lib, args, report)
        ok = ok and good
        print(f'{name}: {"ok" if good else "MISMATCH"} ({time.time() - s0:.1f} s)', flush=True)
    if args.negative:
        neg = run_negative(m, lib, args)
        report['negative'] = neg
        print('negative:', neg, flush=True)
    if args.mutations:
        caught = run_mutations(m, args)
        report['mutations'] = caught
        ok = ok and all(caught.values())
        print('mutations:', caught, flush=True)
    report['seconds'] = round(time.time() - t0, 1)
    text_out = json.dumps(report, indent=1, default=str)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(text_out)
    print(text_out[:3000])
    for sec in ('sessions', 'draw'):
        for f in report.get(sec, {}).get('failures', [])[:1]:
            print('FAIL', sec, {k: v for k, v in f.items() if k not in ('client', 'native')})
            if f.get('why') == 'log':
                c, n = f['client'], f['native']
                for i in range(max(len(c), len(n))):
                    a = c[i] if i < len(c) else None
                    b = n[i] if i < len(n) else None
                    print(('   ' if json.dumps(a) == json.dumps(b) else '>> ') + f'{a}\n   {b}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
