#!/usr/bin/env python3
"""Compare reconstructed/helpers with the client's pet and mount routines (NATIVE-HELPERS-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case).
The authored C (reconstructed/helpers, libclient_helpers) runs the same steps
through ctypes with Python host callbacks that give the same answers as the
client-side stubs. Compared after every step: the rand() state and call count,
the modelled bytes of the objects involved, the mount fields and the ordered
log of host calls.

Sections:

* bugs         sessions of CreateBug 0x00c9d8df, MoveBugs 0x00c9e24a,
               RenderBugs 0x00c9e4e3 and DeleteBug 0x00c9ea70 on the 10 bugs at
               0x0bdc3220 with up to four owner characters;
* mount_class  every factory key (kind 0x0106cc24, factory 0x0106cde5 ->
               vtable), and for every class the model load (vtable +0x38), the
               play speeds (+8 then 0x0103dbf4 for actions 0..15) and the rider
               offset (+0x10);
* mount_move   the class moves (vtable +0xc) of Uniria, Dinorant, Dark Horse
               and Fenrir (the base move 0x0103d45a for the others) followed by
               the action map (+0x24, 0x0103d931 / 0x0106c4b6 / +0x28);
* rider        the rider action 0x0106c382 (0x0103dd6b / 0x0103ddde) and the
               lift 0x0103da5c with 0x0103dc68;
* mount_render the render loop's body 0x0103d6d5, shadow 0x0103d281 and
               after-pass 0x0103d830.

Client code includes every routine these reach except the stubs: rand()
(MSVC LCG), RequestTerrainHeight and TestFrustrum2D (synthetic answers),
the model container and getter, the animation tick (recorded), SetAction
(recorded; four actions on helper objects), CreateParticle, CreateEffect,
CreateJoint, CreateSprite, RenderObject and its halves, RenderBodyShadow,
EnableAlphaTest, glColor4f, the buff-list lookup 0x01295ade, the weapon kind
getters 0x0129dd4a / 0x0139d9ed, the item predicates 0x00cd6017 / 0x00b96c35,
the bone lookup 0x0129f18a with TransformPosition 0x012b6ef1 (synthetic
matrices), the bone vector 0x012b6a2b, the SetLive cleanup 0x009b0451, the
mount manager getter and operator new / the std::string helpers of the
methods. Negative controls plant mistakes into the library's answers or inputs
and must be detected.
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
import pins  # noqa: E402
import actor_machine as am  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = ROOT/f'reconstructed/helpers/libclient_helpers.{SUFFIX}'
DEFAULT_TEXT = pins.TEXT.default()
DEFAULT_DATA = pins.DATA.default()

OBJ = 0x3d8
BUGS = 0x0bdc3220
CHAR_BASE, CHAR_STRIDE, CHAR_SIZE, CHAR_OBJ = 0x22000000, 0x4000, 0x3700, 0x3254
WORLD, SCENE, EVENT_OBJ = 0x01cf15fc, 0x01d1df70, 0x01d1dcd0
TRIG_FLAG, CRT_MATH_MODE, COOKIE = 0x0bdd1cc8, 0x0bdcfbc8, 0x01cf65c0
MODEL_BASE, CONTAINER, MANAGER = 0x24000000, 0x24800000, 0x24900000
ARGS = 0x25000000
MOUNT_BASE, MOUNT_STRIDE = 0x26000000, 0x1000          # mount C++ objects (0x58 bytes) and their OBJECTs
HEAP_BASE, HEAP_SIZE = 0x27000000, 0x40000
SCRATCH = 0x7ffb0000
FLD_RET, SCRATCH_FLOAT = SCRATCH, SCRATCH + 0x100

RAND, TERRAIN, FRUSTUM = 0x01989721, 0x016cc9e2, 0x016ccce7
MODEL_CONTAINER, MODEL_GET, ANIMATE, SET_ACTION = 0x00966cc4, 0x00eaa8cf, 0x012b4dd3, 0x012affa4
KILL, PARTICLE, SPRITE, RENDER_OBJECT = 0x009b0451, 0x0168fafd, 0x01692eb7, 0x016d4fe4
DRAW_BODY, DRAW_AFTER, SHADOW, ALPHA_TEST = 0x017ec896, 0x017edf43, 0x012bc07a, 0x0184a990
BUFF = 0x01295ade
EFFECT, JOINT = 0x013c0eaa, 0x0153b02c
BONE_FIND, BONE_TRANSFORM, BONE_VECTOR = 0x0129f18a, 0x012b6ef1, 0x012b6a2b
WEAPON_KIND, WEAPON_54 = 0x0129dd4a, 0x0139d9ed
MANAGER_GET, ITEM_TABLE, ITEM_KIND = 0x009c104e, 0x00cd4ea8, 0x00cd6017
INV_GET, INV_ITEMS, INV_FLAG = 0x00ac3bf7, 0x0095f965, 0x00b96c35
STRING_CTOR, STRING_DTOR, NEW, OBJ_CTOR = 0x0094997e, 0x008e83a0, 0x0191ba7b, 0x0129e792
MAP_INSERT_A, MAP_INSERT_B = 0x0103eb7f, 0x01040039
RIDER_RESET, BONES_ALLOC, POSE = 0x013a763e, 0x0129f06f, 0x012b5064
GL_COLOR4 = 0x1a7c754
SUBTYPE_SENTINEL = 0x5a5a5a   # object +0x60 before the model load (NATIVE-HELPERS-002)

CREATE_BUG, MOVE_BUGS, RENDER_BUGS, DELETE_BUG = 0x00c9d8df, 0x00c9e24a, 0x00c9e4e3, 0x00c9ea70
KIND, FACTORY, DESCRIPTOR = 0x0106cc24, 0x0106cde5, 0x0106cc74
SPEED_LOOKUP, MOVE_BASE, FOLLOW, CATEGORY = 0x0103dbf4, 0x0103d45a, 0x0103d931, 0x0106c4b6
RIDER, LIFT, LIFTS = 0x0106c382, 0x0103da5c, 0x0103dc68
RENDER_BODY, RENDER_SHADOW, RENDER_AFTER = 0x0103d6d5, 0x0103d281, 0x0103d830

BUG_PROBES = {
    0x00c9d8f8: 'create: no-bug world', 0x00c9d90f: 'create: owner not a player', 0x00c9d688: 'create: angel',
    0x00c9d787: 'create: imp', 0x00c9d8c3: 'create: 0x671 scale', 0x00c9d8da: 'create: slot taken',
    0x00c9d9c3: 'move: scene-6 kill', 0x00c9d9fe: 'move: missing model', 0x00c9da9b: 'move: butterfly',
    0x00c9db71: 'move: angel sparkles', 0x00c9de58: 'move: turn', 0x00c9e068: 'move: new direction',
    0x00c9e084: 'move: far speed', 0x00c9e0b4: 'move: near speed', 0x00c9e1b6: 'move: rise', 0x00c9e21c: 'move: sink',
    0x00c9e344: 'render: skipped type', 0x00c9e376: 'render: scene 5 scale', 0x00c9e3c7: 'render: scale 1',
    0x00c9e3fb: 'render: buff blend', 0x00c9e44e: 'render: flare', 0x00c9eac8: 'delete: kill',
}

BODIES = {  # start, exclusive end
    'create_bug': (0x00c9d8df, 0x00c9d95a), 'create_bug_sub': (0x00c9d42a, 0x00c9d8df),
    'move_bug': (0x00c9d95a, 0x00c9e24a), 'move_bugs': (0x00c9e24a, 0x00c9e28a),
    'render_bug': (0x00c9e28a, 0x00c9e4e3), 'render_bugs': (0x00c9e4e3, 0x00c9e523),
    'delete_bug': (0x00c9ea70, 0x00c9ead7), 'bug_types': (0x00ca211e, 0x00ca2154),
    'mount_kind': (0x0106cc24, 0x0106cc74), 'factory': (0x0106cde5, 0x0106d6ca),
    'move_base': (0x0103d45a, 0x0103d6cc), 'speed_lookup': (0x0103dbf4, 0x0103dc68),
    'lifts': (0x0103dc68, 0x0103dd3b), 'lift': (0x0103da5c, 0x0103dbf4),
    'follow': (0x0103d931, 0x0103d9eb), 'category': (0x0106c4b6, 0x0106c5e9),
    'rider': (0x0106c382, 0x0106c4b6), 'rider_unarmed': (0x0103dd6b, 0x0103ddde),
    'rider_armed': (0x0103ddde, 0x0103e1ea), 'render_body': (0x0103d6d5, 0x0103d830),
    'render_after': (0x0103d830, 0x0103d8be), 'render_shadow': (0x0103d281, 0x0103d3c0),
}


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


def same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        if isinstance(a, float) and isinstance(b, float):
            return (math.isnan(a) and math.isnan(b)) or bits(a) == bits(b)
        return False
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def same_log(x, y):
    return len(x) == len(y) and all(same(a, b) for a, b in zip(x, y))


# --------------------------------------------------------------------------
# The library (ctypes).

V3 = ctypes.c_float * 3


class Obj(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('lighting', ctypes.c_uint8), ('visible', ctypes.c_uint8),
                ('alpha_enable', ctypes.c_uint8), ('flag_0d', ctypes.c_uint8), ('flag_0e', ctypes.c_uint8),
                ('flag_41', ctypes.c_uint8),
                ('action', ctypes.c_uint16), ('prior_action', ctypes.c_uint16), ('type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('field_68', ctypes.c_int32), ('lifetime', ctypes.c_int32),
                ('blend_mesh', ctypes.c_int32), ('scale', ctypes.c_float), ('blend_light', ctypes.c_float),
                ('velocity', ctypes.c_float), ('frame', ctypes.c_float), ('prior_frame', ctypes.c_float),
                ('alpha_target', ctypes.c_float), ('alpha', ctypes.c_float), ('alpha_speed', ctypes.c_float),
                ('light', V3), ('direction', V3), ('position', V3), ('angle', V3), ('head_angle', V3),
                ('matrix', ctypes.c_float * 12), ('owner', ctypes.c_int32), ('custom_shadow', ctypes.c_uint8),
                ('shadow_alpha', ctypes.c_float)]


class Owner(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('fade', ctypes.c_uint8), ('kind', ctypes.c_uint8),
                ('action', ctypes.c_uint16), ('type', ctypes.c_int32), ('position', V3), ('angle', V3),
                ('buff_12', ctypes.c_uint8), ('class_byte', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8),
                ('hidden', ctypes.c_uint8), ('ring', ctypes.c_uint8), ('weapon', ctypes.c_int16 * 2),
                ('weapon_kind', ctypes.c_uint8 * 2), ('weapon_54', ctypes.c_uint8)]


class Inputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('scene', ctypes.c_int32), ('event_state', ctypes.c_int32),
                ('has_pet_item', ctypes.c_uint8)]


P = ctypes.c_void_p
TERRAIN_FN = ctypes.CFUNCTYPE(ctypes.c_float, P, ctypes.c_float, ctypes.c_float)
HAS_MODEL_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_int32)
ANIMATE_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_float)
SET_ACTION_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32)
OWNER_ACTION_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.c_int32)
PARTICLE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, P, P, ctypes.c_int32, ctypes.c_float)
EFFECT_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, P, P, ctypes.c_int32, ctypes.c_int32)
JOINT_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, P, P, ctypes.c_float)
BONE_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, P, ctypes.c_int32, ctypes.c_char_p, P, P, ctypes.c_int)
BONE_VECTOR_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_char_p, P, P)
FLAG_FN = ctypes.CFUNCTYPE(ctypes.c_int, P)
KILL_FN = ctypes.CFUNCTYPE(None, P, P)
RESET_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32)


class Host(ctypes.Structure):
    _fields_ = [('context', P), ('terrain_height', TERRAIN_FN), ('has_model', HAS_MODEL_FN),
                ('animate', ANIMATE_FN), ('set_action', SET_ACTION_FN), ('set_owner_action', OWNER_ACTION_FN),
                ('particle', PARTICLE_FN), ('effect', EFFECT_FN), ('joint', JOINT_FN), ('bone_position', BONE_FN),
                ('bone_vector', BONE_VECTOR_FN), ('dark_horse_flag', FLAG_FN), ('kill', KILL_FN),
                ('rider_reset', RESET_FN)]


FRUSTUM_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_float, ctypes.c_float, ctypes.c_float)
DRAW_OBJECT_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                                  ctypes.c_int32)
DRAW_BODY_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)
SPRITE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, ctypes.c_float, P, P)
ALPHA_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32)
COLOR4_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
SHADOW_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)


class RenderHost(ctypes.Structure):
    _fields_ = [('context', P), ('frustum', FRUSTUM_FN), ('draw_object', DRAW_OBJECT_FN),
                ('draw_body', DRAW_BODY_FN), ('draw_after', DRAW_OBJECT_FN), ('sprite', SPRITE_FN),
                ('alpha_test', ALPHA_FN), ('color4', COLOR4_FN), ('shadow', SHADOW_FN)]


class Helpers(ctypes.Structure):
    _fields_ = [('rand_state', ctypes.c_uint32), ('rand_calls', ctypes.c_uint64), ('bugs', Obj * 10),
                ('owners', ctypes.POINTER(Owner)), ('owner_count', ctypes.c_int32), ('host', Host)]


class MountInfo(ctypes.Structure):
    _fields_ = [('cls', ctypes.c_int32), ('vtable', ctypes.c_uint32), ('item', ctypes.c_int32),
                ('model', ctypes.c_int32), ('file', ctypes.c_char_p), ('bone', ctypes.c_char_p),
                ('lift', ctypes.c_float), ('has_lift', ctypes.c_uint8), ('scale_offset', ctypes.c_uint8),
                ('ported', ctypes.c_uint8), ('scale', ctypes.c_float), ('shadow_mode', ctypes.c_uint8),
                ('speed', ctypes.c_float * 16)]


class Mount(ctypes.Structure):
    _fields_ = [('live', ctypes.c_int32), ('key', ctypes.c_int32), ('cls', ctypes.c_int32),
                ('kind', ctypes.c_int32), ('item', ctypes.c_int32), ('state', ctypes.c_int32),
                ('model', ctypes.c_int32), ('owner', ctypes.c_int32), ('object', Obj), ('has_model', ctypes.c_uint8),
                ('offset', V3), ('action', ctypes.c_int32), ('riding', ctypes.c_uint8), ('counter', ctypes.c_int32),
                ('shadow', ctypes.c_uint8), ('flag_48', ctypes.c_uint8), ('shadow_arg', ctypes.c_int32),
                ('fly', ctypes.c_uint8)]


def load_library(path=LIB, extra_cflags=None):
    if extra_cflags is not None or not Path(path).exists():
        cmd = ['make', '-C', str(Path(path).parent), '-B'] if extra_cflags is None else \
            ['make', '-C', str(Path(path).parent), '-B', f'CFLAGS=-std=c11 -O2 -fPIC -ffp-contract=off '
             f'-fno-fast-math {extra_cflags}']
        subprocess.run(cmd, check=True, capture_output=True)
    lib = ctypes.CDLL(str(path))
    PH = ctypes.POINTER(Helpers)
    lib.mu_hp_init.argtypes = [PH, ctypes.c_uint32, ctypes.POINTER(Owner), ctypes.c_int32, ctypes.POINTER(Host)]
    lib.mu_hp_create_bug.argtypes = [PH, ctypes.POINTER(Inputs), ctypes.c_int32, P, ctypes.c_int32, ctypes.c_int32]
    lib.mu_hp_create_bug.restype = ctypes.c_int32
    lib.mu_hp_move_bugs.argtypes = [PH, ctypes.POINTER(Inputs)]
    lib.mu_hp_delete_bug.argtypes = [PH, ctypes.c_int32]
    lib.mu_hp_render_bugs.argtypes = [PH, ctypes.POINTER(Inputs), ctypes.POINTER(RenderHost)]
    lib.mu_hp_mount_class_info.argtypes = [ctypes.c_int32]
    lib.mu_hp_mount_class_info.restype = ctypes.POINTER(MountInfo)
    lib.mu_hp_mount_kind.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int]
    lib.mu_hp_mount_kind.restype = ctypes.c_int32
    lib.mu_hp_mount_class.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
    lib.mu_hp_mount_class.restype = ctypes.c_int32
    lib.mu_hp_mount_model.argtypes = [ctypes.c_int32, ctypes.c_int32]
    lib.mu_hp_mount_model.restype = ctypes.c_int32
    lib.mu_hp_mount_object_subtype.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]   # NATIVE-HELPERS-002
    lib.mu_hp_mount_object_subtype.restype = ctypes.c_int32
    lib.mu_hp_mount_speed.argtypes = [ctypes.c_int32, ctypes.c_int32]
    lib.mu_hp_mount_speed.restype = ctypes.c_float
    PM = ctypes.POINTER(Mount)
    lib.mu_hp_mount_offset.argtypes = [PH, PM]
    lib.mu_hp_mount_move.argtypes = [PH, PM, ctypes.POINTER(Inputs)]
    lib.mu_hp_mount_move.restype = ctypes.c_int
    lib.mu_hp_mount_move_base.argtypes = [PH, PM, ctypes.POINTER(Inputs)]
    lib.mu_hp_mount_move_base.restype = ctypes.c_int
    lib.mu_hp_mount_follow_action.argtypes = [PH, PM]
    lib.mu_hp_action_category.argtypes = [ctypes.c_uint16]
    lib.mu_hp_action_category.restype = ctypes.c_int32
    lib.mu_hp_rider_action.argtypes = [PH, ctypes.c_int32, ctypes.c_int32]
    lib.mu_hp_rider_action.restype = ctypes.c_int32
    lib.mu_hp_mount_place_owner.argtypes = [PH, PM, ctypes.c_int]
    lib.mu_hp_mount_render.argtypes = [PH, PM, ctypes.POINTER(Inputs), ctypes.POINTER(RenderHost)]
    return lib


# --------------------------------------------------------------------------
# Client layout of the modelled fields.

OBJECT_FIELDS = [  # (name, offset, struct format, count)
    ('live', 0x00, 'B', 1), ('lighting', 0x05, 'B', 1), ('visible', 0x0b, 'B', 1), ('alpha_enable', 0x0c, 'B', 1),
    ('flag_0d', 0x0d, 'B', 1), ('flag_0e', 0x0e, 'B', 1), ('flag_41', 0x41, 'B', 1),
    ('action', 0x2a, 'H', 1), ('prior_action', 0x2c, 'H', 1),
    ('type', 0x5c, 'i', 1), ('subtype', 0x60, 'i', 1), ('field_68', 0x68, 'i', 1), ('lifetime', 0x6c, 'i', 1),
    ('blend_mesh', 0x74, 'i', 1), ('scale', 0xa0, 'f', 1), ('blend_light', 0xa8, 'f', 1), ('velocity', 0xbc, 'f', 1),
    ('frame', 0xd0, 'f', 1), ('prior_frame', 0xd4, 'f', 1), ('alpha_target', 0xd8, 'f', 1), ('alpha', 0xdc, 'f', 1),
    ('alpha_speed', 0xe0, 'f', 1), ('light', 0xec, 'f', 3), ('direction', 0xf8, 'f', 3), ('position', 0x158, 'f', 3),
    ('angle', 0x164, 'f', 3), ('head_angle', 0x170, 'f', 3), ('matrix', 0x2e8, 'f', 12),
    ('custom_shadow', 0x3c8, 'B', 1), ('shadow_alpha', 0x3cc, 'f', 1)]
OWNER_PTR = 0x34c

OBJECT_MASK = bytearray(OBJ)
for _n, _o, _f, _c in OBJECT_FIELDS:
    OBJECT_MASK[_o:_o + struct.calcsize('<' + _f*_c)] = b'\1'*struct.calcsize('<' + _f*_c)
OBJECT_MASK[OWNER_PTR:OWNER_PTR + 4] = b'\1\1\1\1'


def char_addr(k):
    return CHAR_BASE + k*CHAR_STRIDE


def owner_obj_addr(k):
    return 0 if k < 0 else char_addr(k) + CHAR_OBJ


def owner_index(addr):
    if addr == 0:
        return -1
    k, r = divmod(addr - CHAR_BASE - CHAR_OBJ, CHAR_STRIDE)
    if r == 0 and 0 <= k < 16:
        return k
    return -2


def object_to_bytes(o, base=None):
    """ctypes Obj -> 0x3d8 client bytes (only modelled fields)."""
    out = bytearray(base if base is not None else bytes(OBJ))
    for name, off, fmt, count in OBJECT_FIELDS:
        v = getattr(o, name)
        vals = list(v) if count > 1 else [v]
        out[off:off + struct.calcsize('<' + fmt*count)] = struct.pack('<' + fmt*count, *vals)
    out[OWNER_PTR:OWNER_PTR + 4] = struct.pack('<I', owner_obj_addr(o.owner))
    return bytes(out)


def bytes_to_object(raw, o):
    for name, off, fmt, count in OBJECT_FIELDS:
        vals = struct.unpack('<' + fmt*count, raw[off:off + struct.calcsize('<' + fmt*count)])
        if count > 1:
            arr = getattr(o, name)
            for i, v in enumerate(vals):
                arr[i] = v
        else:
            setattr(o, name, vals[0])
    o.owner = owner_index(struct.unpack('<I', raw[OWNER_PTR:OWNER_PTR + 4])[0])


def masked(raw):
    return bytes(b if m else 0 for b, m in zip(raw, OBJECT_MASK))


# --------------------------------------------------------------------------
# Machine.

class Machine(am.ActorMachine):
    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_READ, UC_PROT_EXEC, UC_PROT_WRITE
        self.uc.mem_map(SCRATCH, am.PAGE, UC_PROT_READ | UC_PROT_EXEC | UC_PROT_WRITE)
        self.uc.mem_write(FLD_RET, bytes([0xd9, 0x05]) + struct.pack('<I', SCRATCH_FLOAT) + b'\xc3')
        target = struct.unpack('<I', data[GL_COLOR4 - am.DATA_BASE:GL_COLOR4 - am.DATA_BASE + 4])[0]
        self.gl_color4 = target
        self.uc.mem_map(target & ~0xfff, am.PAGE, UC_PROT_READ | UC_PROT_EXEC)
        self.uc.mem_write(target & ~0xfff, b'\xcc'*am.PAGE)
        self.probes = {}

    def add_probes(self, probes):
        for address in probes:
            if address in self.probes:
                continue
            self.probes[address] = 0
            self.uc.hook_add(self.UC_HOOK_CODE, self._probe, begin=address, end=address)
        self.uc.ctl_flush_tb()

    def _probe(self, uc, address, size, ignored):
        self.probes[address] += 1

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
            import traceback
            self.stop(('stub-error', hex(address), repr(failure), traceback.format_exc()[-400:]))
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
        uc.reg_write(x86.UC_X86_REG_ESP, esp + 4 + cleanup)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def float_argument(self, index):
        return from_bits(self.argument(index))

    def read_floats(self, address, count):
        return struct.unpack(f'<{count}f', bytes(self.uc.mem_read(address, 4*count)))

    def return_float(self, value):
        self.uc.mem_write(SCRATCH_FLOAT, struct.pack('<f', value))
        return ('jump', FLD_RET, None)

    def data_word(self, address):
        return bytes(self.uc.mem_read(address, 4))

    def st0_float(self):
        return f32(self.uc.reg_read(self.x86.UC_X86_REG_FP0)) if False else self._st0()

    def _st0(self):
        top = (self.uc.reg_read(self.x86.UC_X86_REG_FPSW) >> 11) & 7
        raw = self.uc.reg_read(self.x86.UC_X86_REG_FP0 + top)
        mant, exp = raw
        sign = (exp >> 15) & 1
        e = exp & 0x7fff
        if e == 0 and mant == 0:
            return -0.0 if sign else 0.0
        value = math.ldexp(mant, e - 16383 - 63)
        return f32(-value if sign else value)

    def ecx(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_ECX)

    def local_write(self, address, payload):
        if am.STACK <= address < am.STACK + am.STACK_BYTES:
            self.uc.mem_write(address, bytes(payload))
        else:
            self.write(address, payload)


def load_inputs(args):
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'image data')
    return text, data


def body_digests(text):
    out = {}
    for name, (lo, hi) in BODIES.items():
        out[name] = hashlib.sha256(text[lo - am.TEXT_BASE:hi - am.TEXT_BASE]).hexdigest()[:16]
    return out


# --------------------------------------------------------------------------
# Shared synthetic answers (client stubs and library callbacks).

def test_height(case, x, y):
    m = mix(bits(x) >> 6, bits(y) >> 6)
    return f32(case['height_base'] + float(m % 300))


def test_frustum(case, x, y, r):
    return 1 if mix(bits(x), bits(y) ^ bits(r) ^ case['frustum_salt']) & 3 else 0


def bone_answer(name, vector, salt):
    """The synthetic TransformPosition result of a named bone and a vector."""
    h = int(hashlib.sha256(name.encode() + struct.pack('<I', salt)).hexdigest()[:8], 16)
    base = [float((h >> (8*k)) % 97) - 48.0 for k in range(3)]
    return tuple(f32(f32(vector[k] * 0.5) + base[k]) for k in range(3))


# --------------------------------------------------------------------------
# Client memory and stubs for a case.

class Client:
    def __init__(self, m, case):
        self.m, self.case = m, case
        self.rand_state, self.rand_calls = case['seed'] & 0xffffffff, 0
        self.log = []
        self.chars = [am.undefined_region(f'char{k}', char_addr(k), CHAR_SIZE) for k in range(len(case['owners']))]
        self.bugs = am.Region('bugs', BUGS, bytes(10*OBJ), bytes(10*OBJ))
        self.models = am.undefined_region('models', MODEL_BASE, 0x2000)
        self.heap = am.undefined_region('heap', HEAP_BASE, HEAP_SIZE)
        self.heap_next = HEAP_BASE
        self.args = am.undefined_region('args', ARGS, 0x100)
        self.extra = []

    def set_owners(self, owners):
        for k, o in enumerate(owners):
            r = self.chars[k]
            base = r.base + CHAR_OBJ
            r.define(base + 0x00, bytes([o['live']]))
            r.define(base + 0x3a, bytes([o['fade']]))
            r.define(base + 0x3b, bytes([o['kind']]))
            r.define(base + 0x2a, struct.pack('<H', o['action']))
            r.define(base + 0x5c, struct.pack('<i', o['type']))
            r.define(base + 0x158, struct.pack('<3f', *o['position']))
            r.define(base + 0x164, struct.pack('<3f', *o['angle']))
            r.define(r.base + 0x12, bytes([o['class_byte']]))
            r.define(r.base + 0x04, bytes([o['safe_zone']]))
            r.define(r.base + 0x31e8, bytes([o['hidden']]))
            r.define(r.base + 0x328d, bytes([o['ring']]))
            r.define(r.base + 0x19ac, struct.pack('<h', o['weapon'][0]))
            r.define(r.base + 0x1da8, struct.pack('<h', o['weapon'][1]))
            r.define(r.base + 0x3e, struct.pack('<h', o.get('key', k)))
            r.define(r.base + 0x32b0, struct.pack('<i', o['type']))

    def read_owner(self, k):
        r = self.chars[k]
        raw = bytes(r.data)
        base = CHAR_OBJ
        return {'position': struct.unpack('<3f', raw[base + 0x158:base + 0x164]),
                'action': struct.unpack('<H', raw[base + 0x2a:base + 0x2c])[0],
                'ring': raw[0x328d]}

    def globals(self, s):
        return [am.defined_region('world', WORLD, struct.pack('<i', s['world']), writable=False),
                am.defined_region('scene', SCENE, struct.pack('<i', s['scene']), writable=False),
                am.defined_region('trig-flag', TRIG_FLAG, struct.pack('<I', 1), writable=False),
                am.defined_region('crt-mode', CRT_MATH_MODE, struct.pack('<I', self.case.get('crt_mode', 1)),
                                  writable=False),
                am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False)]

    def object_label(self, addr):
        if BUGS <= addr < BUGS + 10*OBJ and (addr - BUGS) % OBJ == 0:
            return ('bug', (addr - BUGS)//OBJ)
        if addr == self.case.get('mount_object'):
            return ('mount', 0)
        k = owner_index(addr)
        if k >= 0:
            return ('owner', k)
        return ('?', addr)

    def common_stubs(self, s):
        case, log = self.case, self.log

        def rand(m):
            self.rand_state = (self.rand_state * 214013 + 2531011) & 0xffffffff
            self.rand_calls += 1
            return (self.rand_state >> 16) & 0x7fff

        def terrain(m):
            return m.return_float(test_height(case, m.float_argument(0), m.float_argument(1)))

        def frustum(m):
            x, y, r = m.float_argument(0), m.float_argument(1), m.float_argument(2)
            v = test_frustum(case, x, y, r)
            log.append(('frustum', x, y, r))
            return v

        def container(m):
            return CONTAINER

        def model_get(m):
            index = m.argument(0)
            if index in case.get('missing_models', ()):
                return 0, 4
            return MODEL_BASE + (index % 16)*0x100, 4

        def animate(m):
            model = m.ecx()
            action = struct.unpack('<H', bytes(m.uc.mem_read(model + 0xa8, 2)))[0]
            fp = m.argument(0)
            o = fp - 0xd0
            frame, = m.read_floats(fp, 1)
            log.append(('animate', self.object_label(o), action, m.float_argument(3), frame,
                        m.argument(1) == o + 0xd4 and m.argument(2) == o + 0x2c and m.argument(4) == o + 0x158 and
                        m.argument(5) == o + 0x164))
            return 0, 0x18

        def set_action(m):
            o, action = m.argument(0), m.argument(1)
            log.append(('set_action', self.object_label(o), action))
            return 0

        def kill(m):
            log.append(('kill', self.object_label(m.ecx())))
            return 0

        def particle(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            log.append(('particle', m.argument(0), m.argument(4), pos, ang, light, m.float_argument(5),
                        m.argument(6), m.argument(7)))
            return 0

        def buff(m):
            k = owner_index(m.ecx() - 0x358)
            if k < 0:
                k = (m.ecx() - 0x35ac - CHAR_BASE)//CHAR_STRIDE
            assert m.argument(0) == 0x12
            return case['owners'][k]['buff_12'], 4

        def render_object(m):
            o = m.argument(0)
            scale = from_bits(struct.unpack('<I', bytes(m.uc.mem_read(o + 0xa0, 4)))[0])
            log.append(('object', self.object_label(o), tuple(m.argument(i) for i in range(1, 6)), scale))
            return 0

        def sprite(m):
            pos, light = m.read_floats(m.argument(1), 3), m.read_floats(m.argument(3), 3)
            log.append(('sprite', m.argument(0), pos, m.float_argument(2), light, self.object_label(m.argument(4)),
                        m.float_argument(5), m.argument(6), m.argument(7)))
            return 0

        return {RAND: rand, TERRAIN: terrain, FRUSTUM: frustum, MODEL_CONTAINER: container, MODEL_GET: model_get,
                ANIMATE: animate, SET_ACTION: set_action, KILL: kill, PARTICLE: particle, BUFF: buff,
                RENDER_OBJECT: render_object, SPRITE: sprite}


# --------------------------------------------------------------------------
# Native side for a case.

class Native:
    def __init__(self, lib, case, plant=None):
        self.lib, self.case, self.plant = lib, case, plant
        self.log = []
        n = len(case['owners'])
        self.owners = (Owner * max(n, 1))()
        self.h = Helpers()
        self.host = self._host()
        lib.mu_hp_init(ctypes.byref(self.h), case['seed'] & 0xffffffff, self.owners, n, ctypes.byref(self.host))
        self.mount = None

    def object_label(self, addr):
        base = ctypes.addressof(self.h.bugs)
        if base <= addr < base + 10*ctypes.sizeof(Obj):
            return ('bug', (addr - base)//ctypes.sizeof(Obj))
        if self.mount is not None and addr == ctypes.addressof(self.mount.object):
            return ('mount', 0)
        return ('?', addr)

    def set_owners(self, owners):
        for k, o in enumerate(owners):
            w = self.owners[k]
            w.live, w.fade, w.kind, w.action, w.type = o['live'], o['fade'], o['kind'], o['action'], o['type']
            for i in range(3):
                w.position[i] = o['position'][i]
                w.angle[i] = o['angle'][i]
            w.buff_12 = o['buff_12']
            if self.plant == 'buff' and k == 0:
                w.buff_12 ^= 1
            w.class_byte, w.safe_zone, w.hidden, w.ring = o['class_byte'], o['safe_zone'], o['hidden'], o['ring']
            w.weapon[0], w.weapon[1] = o['weapon']
            w.weapon_kind[0], w.weapon_kind[1] = o['weapon_kind']
            w.weapon_54 = o['weapon_54']

    def read_owner(self, k):
        w = self.owners[k]
        return {'position': tuple(w.position), 'action': w.action, 'ring': w.ring}

    def _host(self):
        case, log = self.case, self.log

        def terrain(ctx, x, y):
            return test_height(case, f32(x), f32(y))

        def has_model(ctx, model):
            return 0 if model in case.get('missing_models', ()) else 1

        def animate(ctx, o, model, speed):
            ob = Obj.from_address(o)
            log.append(('animate', self.object_label(o), ob.action, f32(speed), f32(ob.frame), True))

        def set_action(ctx, o, action):
            log.append(('set_action', self.object_label(o), action))

        def owner_action(ctx, owner, action):
            log.append(('set_action', ('owner', owner), action))

        def v3(p):
            return tuple(f32(x) for x in (ctypes.c_float*3).from_address(p))

        def particle(ctx, bitmap, p, a, l, subtype, scale):
            log.append(('particle', bitmap, subtype, v3(p), v3(a), v3(l), f32(scale), 0, 0))

        def effect(ctx, typ, p, a, l, subtype, owner):
            log.append(('effect', typ, v3(p), v3(a), v3(l), subtype, owner))

        def joint(ctx, typ, p, a, o, scale):
            log.append(('joint', typ, v3(p), v3(a), self.object_label(o), f32(scale)))

        def bone(ctx, o, model, name, v, out, world_space):
            nm = name.decode()
            log.append(('bone', nm, v3(v)))
            res = bone_answer(nm, v3(v), case['bone_salt'])
            arr = (ctypes.c_float*3).from_address(out)
            for i in range(3):
                arr[i] = res[i]
            return 1

        def bone_vector(ctx, o, model, name, v, out):
            nm = name.decode()
            log.append(('bone_vector', nm, v3(v)))
            res = bone_answer(nm + '/v', v3(v), case['bone_salt'])
            arr = (ctypes.c_float*3).from_address(out)
            for i in range(3):
                arr[i] = res[i]

        def flag(ctx):
            return case.get('dark_horse_flag', 0)

        def kill(ctx, o):
            log.append(('kill', self.object_label(o)))

        def reset(ctx, owner):
            log.append(('rider_reset', owner))

        self.callbacks = [TERRAIN_FN(terrain), HAS_MODEL_FN(has_model), ANIMATE_FN(animate),
                          SET_ACTION_FN(set_action), OWNER_ACTION_FN(owner_action), PARTICLE_FN(particle),
                          EFFECT_FN(effect), JOINT_FN(joint), BONE_FN(bone), BONE_VECTOR_FN(bone_vector),
                          FLAG_FN(flag), KILL_FN(kill), RESET_FN(reset)]
        h = Host()
        (h.terrain_height, h.has_model, h.animate, h.set_action, h.set_owner_action, h.particle, h.effect, h.joint,
         h.bone_position, h.bone_vector, h.dark_horse_flag, h.kill, h.rider_reset) = self.callbacks
        return h

    def render_host(self):
        case, log = self.case, self.log

        def frustum(ctx, x, y, r):
            log.append(('frustum', f32(x), f32(y), f32(r)))
            return test_frustum(case, f32(x), f32(y), f32(r))

        def draw_object(ctx, o, a1, a2, a3, a4, a5):
            ob = Obj.from_address(o)
            log.append(('object', self.object_label(o), tuple(x & 0xffffffff for x in (a1, a2, a3, a4, a5)),
                        f32(ob.scale)))

        def draw_body(ctx, o, a1, a2, a3):
            log.append(('draw_body', self.object_label(o), (a1, a2, a3)))
            return case.get('body_drawn', 1)

        def draw_after(ctx, o, a1, a2, a3, a4, a5):
            log.append(('draw_after', self.object_label(o), tuple(x & 0xffffffff for x in (a1, a2, a3, a4, a5))))

        def v3(p):
            return tuple(f32(x) for x in (ctypes.c_float*3).from_address(p))

        def sprite(ctx, bitmap, p, scale, light, owner):
            log.append(('sprite', bitmap, v3(p), f32(scale), v3(light), self.object_label(owner), 0.0, 0, 4))

        def alpha(ctx, arg):
            log.append(('alpha_test', arg))

        def color4(ctx, r, g, b, a):
            log.append(('color4', f32(r), f32(g), f32(b), f32(a)))

        def shadow(ctx, o, model, arg, routine):
            hidden = (0xffffffff, 0xffffffff, 0, 3) if routine == 2 else (0xffffffff,)*4
            log.append(('shadow2' if routine == 1 else 'shadow', MODEL_BASE + (model % 16)*0x100,
                        (*hidden, arg & 0xffffffff)))

        self.render_callbacks = [FRUSTUM_FN(frustum), DRAW_OBJECT_FN(draw_object), DRAW_BODY_FN(draw_body),
                                 DRAW_OBJECT_FN(draw_after), SPRITE_FN(sprite), ALPHA_FN(alpha), COLOR4_FN(color4),
                                 SHADOW_FN(shadow)]
        r = RenderHost()
        (r.frustum, r.draw_object, r.draw_body, r.draw_after, r.sprite, r.alpha_test, r.color4,
         r.shadow) = self.render_callbacks
        return r


# --------------------------------------------------------------------------
# Section: bugs.

def random_owner(rng, k):
    return {'live': rng.choice([1, 1, 1, 1, 0]), 'fade': rng.choice([0, 0, 0, 1, 2, 3]),
            'kind': rng.choice([1, 1, 1, 4, 2]), 'action': rng.choice([0, 1, 0x26, 0x47, 0x67, 0x90, 0x13b, 0x150]),
            'type': rng.choice([0xa91]*5 + [0x7a5, 0x123]),
            'position': [f32(rng.uniform(3000, 20000)), f32(rng.uniform(3000, 20000)), f32(rng.uniform(0, 400))],
            'angle': [0.0, 0.0, f32(rng.uniform(0, 360))], 'buff_12': rng.choice([0, 0, 0, 1]),
            'class_byte': rng.randrange(256), 'safe_zone': rng.choice([0, 0, 1]), 'hidden': rng.choice([0]*8 + [1]),
            'ring': rng.choice([0, 0, 1]), 'weapon': [rng.choice([-1, -1, 0xae6 + rng.randrange(0x1400)]),
                                                     rng.choice([-1, -1, 0xae6 + rng.randrange(0x1400)])],
            'weapon_kind': [rng.choice([0, 0, 0x59, 0x5a, 0x72, 3]), rng.choice([0, 0, 0x59, 0x5a, 0x72, 3])],
            'weapon_54': rng.choice([0, 0, 0, 1]), 'key': k}


def random_bug_bytes(rng, owners):
    """A bug slot as left by earlier play: dead, or a live angel / imp with fuzzed fields."""
    o = Obj()
    o.live = 1 if rng.random() < 0.25 else 0
    o.type = rng.choice([0x24e6, 0x24e7, 0x193, 0x24e6])
    o.owner = rng.randrange(len(owners)) if (o.live or rng.random() < 0.9) else -1
    o.alpha_enable = rng.choice([0, 0, 1])
    o.lighting, o.visible, o.flag_0d, o.flag_0e, o.flag_41 = 1, rng.randrange(2), 0, 0, 0
    o.action = rng.choice([0, 1, 2])
    o.prior_action = rng.choice([0, 1])
    o.subtype, o.field_68, o.lifetime, o.blend_mesh = 0, -1, 30, rng.choice([-1, 1])
    o.scale = f32(rng.choice([0.7, 1.0, 1.2]))
    o.blend_light = f32(rng.uniform(0, 1))
    o.velocity = f32(rng.choice([0.5, 0.3]))
    o.frame, o.prior_frame = f32(rng.uniform(0, 8)), f32(rng.uniform(0, 8))
    o.alpha_target, o.alpha, o.alpha_speed = f32(rng.choice([1.0, 0.0])), f32(rng.uniform(0, 1)), f32(rng.uniform(0, 0.3))
    for i in range(3):
        o.light[i] = 3.0
        o.direction[i] = f32(rng.uniform(-12, 12))
        o.angle[i] = f32(rng.uniform(0, 360)) if i == 2 else 0.0
        o.head_angle[i] = 0.0
    if o.owner >= 0:
        base = owners[o.owner]['position']
        for i in range(3):
            o.position[i] = f32(base[i] + rng.uniform(-400, 400))
    else:
        for i in range(3):
            o.position[i] = f32(rng.uniform(3000, 20000))
    for i in range(12):
        o.matrix[i] = f32(rng.uniform(-1, 1))
    o.custom_shadow, o.shadow_alpha = 0, 0.0
    return object_to_bytes(o)


def bug_case(rng, index):
    n = rng.randrange(1, 5)
    owners = [random_owner(rng, k) for k in range(n)]
    case = {'seed': rng.getrandbits(32), 'owners': owners, 'height_base': float(rng.randrange(0, 200)),
            'frustum_salt': rng.getrandbits(32), 'bone_salt': rng.getrandbits(16),
            'world': rng.choice([0, 0, 0, 2, 3, 0x12, 0x52, 0x35]), 'crt_mode': rng.choice([0, 1]), 'scene': rng.choice([2, 5, 6, 6]),
            'missing_models': [0x24e7] if rng.random() < 0.1 else [],
            'bugs': b''.join(random_bug_bytes(rng, owners) for _ in range(10)) if rng.random() < 0.5 else bytes(10*OBJ)}
    if case['bugs'] == bytes(10*OBJ):   # a fresh array: owner NULL is 0 in memory
        pass
    steps = []
    for _ in range(rng.randrange(8, 40)):
        r = rng.random()
        if r < 0.25:
            steps.append(('create', rng.choice([0x24e6]*5 + [0x24e7, 0x24e7, 0x671, 0x193, 0x24e8]),
                          rng.randrange(n), rng.choice([0, 0, 1])))
        elif r < 0.65:
            steps.append(('move',))
        elif r < 0.85:
            steps.append(('render',))
        elif r < 0.92:
            steps.append(('delete', rng.choice(list(range(n)) + [-1])))
        else:
            steps.append(('owners', rng.getrandbits(32)))
    case['steps'] = steps
    return case


def jitter_owners(owners, seed):
    rng = random.Random(seed)
    for o in owners:
        for i in range(2):
            o['position'][i] = f32(o['position'][i] + rng.uniform(-300, 300))
        o['position'][2] = f32(rng.uniform(0, 400))
        o['angle'][2] = f32(rng.uniform(0, 360))
        if rng.random() < 0.2:
            o['live'] = 1 - o['live']
        if rng.random() < 0.2:
            o['buff_12'] = 1 - o['buff_12']


def run_bug_case(m, lib, case, plant=None):
    client, native = Client(m, case), Native(lib, case, plant)
    owners = case['owners']
    client.bugs = am.Region('bugs', BUGS, case['bugs'], bytes(OBJECT_MASK)*10)
    for i in range(10):
        bytes_to_object(case['bugs'][i*OBJ:(i+1)*OBJ], native.h.bugs[i])
    s = {'world': case['world'], 'scene': case['scene']}
    if plant == 'world':
        s_native = dict(s, world=0x12 if s['world'] != 0x12 else 0)
    else:
        s_native = s
    inputs = Inputs(s_native['world'], s_native['scene'], 0, 0)
    rhost = native.render_host()
    stats = {'steps': 0, 'events': 0, 'creates': 0, 'renders': 0}
    for step in case['steps']:
        client.set_owners(owners)
        native.set_owners(owners)
        client.log.clear()
        native.log.clear()
        stubs = client.common_stubs(s)
        regions = [*client.globals(s), client.bugs, *client.chars, client.models, client.args]
        kind = step[0]
        if kind == 'owners':
            jitter_owners(owners, step[1])
            continue
        if kind == 'create':
            _, typ, k, sub = step
            pos = owners[k]['position']
            client.args.define(ARGS, struct.pack('<3f', *pos))
            res = m.execute(CREATE_BUG, [typ, ARGS, owner_obj_addr(k), sub, 0], regions, stubs)
            pv = V3(*pos)
            lib.mu_hp_create_bug(ctypes.byref(native.h), ctypes.byref(inputs), typ, ctypes.addressof(pv), k, sub)
            stats['creates'] += 1
        elif kind == 'move':
            res = m.execute(MOVE_BUGS, [], regions, stubs)
            lib.mu_hp_move_bugs(ctypes.byref(native.h), ctypes.byref(inputs))
        elif kind == 'render':
            res = m.execute(RENDER_BUGS, [], regions, stubs)
            lib.mu_hp_render_bugs(ctypes.byref(native.h), ctypes.byref(inputs), ctypes.byref(rhost))
            stats['renders'] += 1
        elif kind == 'delete':
            res = m.execute(DELETE_BUG, [owner_obj_addr(step[1])], regions, stubs)
            lib.mu_hp_delete_bug(ctypes.byref(native.h), step[1])
        if not res['ok']:
            return {'ok': False, 'step': step, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
        client.bugs.data[:] = res['regions']['bugs']
        stats['steps'] += 1
        stats['events'] += len(client.log)
        # compare
        if not same_log(client.log, native.log):
            return {'ok': False, 'step': step, 'why': 'log', 'client': client.log[:30], 'native': native.log[:30]}
        if (client.rand_state, client.rand_calls) != (native.h.rand_state, native.h.rand_calls):
            return {'ok': False, 'step': step, 'why': 'rand'}
        for i in range(10):
            raw = bytes(client.bugs.data[i*OBJ:(i+1)*OBJ])
            mine = object_to_bytes(native.h.bugs[i])
            if masked(raw) != masked(mine):
                diff = [hex(j) for j in range(OBJ) if OBJECT_MASK[j] and raw[j] != mine[j]][:12]
                return {'ok': False, 'step': step, 'why': f'bug {i} bytes', 'offsets': diff}
    return {'ok': True, 'stats': stats}


# --------------------------------------------------------------------------
# Mounts: the C++ object in client memory.

MEMSET = 0x0194cd00
VTABLES = {}   # class -> vtable (from the library's table)
MOUNT_ITEMS = [0x1a02, 0x1a03, 0x1a04, 0x1a25, 0x19d7, 0x19e3, 0x19e4, 0x184b, 0x184c, 0x1853, 0x1854, 0x185d,
               0x185e, 0x1833, 0x1834, 0x1835, 0x1836, 0x28f7]
OFFSET_SCALE = 1.5
SHADOW_MODES = {0x0103e1ea: 0, 0x01060321: 1, 0x0106442e: 1, 0x01050d51: 2, 0x01055045: 2, 0x0104ad6b: 3,
                0x0104b983: 3, 0x0104c62b: 3}  # vtable +0x3c
CLASS_ITEMS = {1: 0x1a02, 2: 0x1a03, 3: 0x1a04, 4: 0x1a25, 5: 0x19d7, 6: 0x19e3, 7: 0x19e4, 8: 0x184b, 9: 0x184c,
               10: 0x1853, 11: 0x1854, 12: 0x185d, 13: 0x185e, 14: 0x1833, 15: 0x1834, 16: 0x1835, 17: 0x1836,
               18: 0x28f7}
STRING_TABLE = 0x25000080      # our std::string stand-in objects point at their literal
FENRIR_STRING = 0x01ec9a8c


class MountClient(Client):
    """Client memory with the mount C++ object at MOUNT_BASE and its OBJECT at MOUNT_BASE + 0x100."""

    def __init__(self, m, case):
        super().__init__(m, case)
        self.mount = am.undefined_region('mount', MOUNT_BASE, 0x600)
        self.fenrir_string = am.undefined_region('fenrir-string', FENRIR_STRING, 0x18)
        self.strings = am.undefined_region('strings', ARGS + 0x200, 0x100)
        self.strings.define(ARGS + 0x200, b'sit_pos_0\0')
        self.fenrir_string.define(FENRIR_STRING, struct.pack('<I', ARGS + 0x200))
        self.event = am.undefined_region('event', 0x24a00000, 0x100)
        self.event.define(0x24a00000 + 0x78 + 4, struct.pack('<i', case.get('event_state', 0)))
        self.manager = am.undefined_region('manager', MANAGER, 0x40)
        case['mount_object'] = MOUNT_BASE + 0x100

    def new(self, size):
        addr = (self.heap_next + 15) & ~15
        self.heap_next = addr + size
        if self.heap_next > HEAP_BASE + HEAP_SIZE:
            raise RuntimeError('heap exhausted')
        return addr

    def mount_regions(self, s):
        return [*self.globals(s), *self.chars, self.models, self.args, self.heap, self.mount, self.fenrir_string,
                self.strings, self.event, self.manager]

    def mount_stubs(self, s):
        stubs = self.common_stubs(s)
        case, log = self.case, self.log

        def new(m):
            return self.new(m.argument(0))

        def memset(m):
            dst, value, count = m.argument(0), m.argument(1), m.argument(2)
            m.write(dst, bytes([value & 0xff])*count)
            return dst

        def string_ctor(m):
            this, literal = m.ecx(), m.argument(0)
            m.local_write(this, struct.pack('<I', literal))
            return this, 4

        def string_dtor(m):
            return 0

        def bone_find(m):
            name = m.cstring(m.read32(m.argument(0)))
            self.last_bone = name
            return 0x24f00000, 8

        def bone_transform(m):
            matrix, vec, out = m.argument(0), m.argument(1), m.argument(2)
            v = m.read_floats(vec, 3)
            name = self.last_bone if matrix == 0x24f00000 else '?'
            log.append(('bone', name, v))
            m.local_write(out, struct.pack('<3f', *bone_answer(name, v, case['bone_salt'])))
            return 0, 0x10

        def bone_vector(m):
            out, name_ptr, vec = m.argument(0), m.argument(2), m.argument(3)
            name = m.cstring(m.read32(name_ptr))
            v = m.read_floats(vec, 3)
            log.append(('bone_vector', name, v))
            m.local_write(out, struct.pack('<3f', *bone_answer(name + '/v', v, case['bone_salt'])))
            return out, 0x10

        def bones_alloc(m):
            log.append(('bones', m.argument(0)))
            return 0, 4

        def item_table(m):
            return 0x24b00000

        def item_kind(m):
            item, kind = m.argument(0), m.argument(1)
            return (1 if case.get('item_kind', {}).get(item) == kind else 0), 8

        def effect(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            owner = m.argument(5)
            log.append(('effect', m.argument(0), pos, ang, light, m.argument(4), -1 if owner == 0 else owner))
            return 0

        def joint(m):
            pos, ang = m.read_floats(m.argument(1), 3), m.read_floats(m.argument(3), 3)
            log.append(('joint', m.argument(0), pos, ang, self.object_label(m.argument(5)), m.float_argument(6)))
            return 0

        def event_get(m):
            return 0x24a00000

        def manager_get(m):
            return MANAGER

        def inv_get(m):
            return 0x24c00000

        def inv_items(m):
            return 0x24c00100

        def inv_flag(m):
            return case.get('dark_horse_flag', 0), 4

        def weapon_kind(m):
            k = owner_index(m.ecx() + CHAR_OBJ)
            return case['owners'][k]['weapon_kind'][m.argument(0)] if m.argument(0) in (0, 1) else 0, 4

        def weapon_54(m):
            k = owner_index(m.argument(0) + CHAR_OBJ)
            return case['owners'][k]['weapon_54'] if m.argument(1) == 0 else 0

        def pose(m):
            log.append(('pose', m.argument(1), m.argument(2), m.argument(3)))
            return 0, 0x20

        def rider_reset(m):
            log.append(('rider_reset', owner_index(m.argument(0) + CHAR_OBJ)))
            return 0

        def manager_find(m):   # 0x0106b93a(c): the mount of the character (the case's mount or NULL)
            return (getattr(self, 'mount_addr', 0) if case.get('has_mount') else 0), 4

        def draw_body(m):
            log.append(('draw_body', self.object_label(m.argument(0)), (m.argument(1), m.argument(2), m.argument(3))))
            return case.get('body_drawn', 1)

        def draw_after(m):
            log.append(('draw_after', self.object_label(m.argument(0)), tuple(m.argument(i) for i in range(1, 6))))
            return 0

        def alpha_test(m):
            log.append(('alpha_test', m.argument(0)))
            return 0

        def color4(m):
            log.append(('color4', *(m.float_argument(i) for i in range(4))))
            return 0, 16

        def shadow(m):
            log.append(('shadow', m.ecx(), tuple(m.argument(i) for i in range(5))))
            return 0, 0x14

        def shadow2(m):
            log.append(('shadow2', m.ecx(), tuple(m.argument(i) for i in range(5))))
            return 0, 0x14

        stubs.update({NEW: new, MEMSET: memset, STRING_CTOR: string_ctor, STRING_DTOR: string_dtor,
                      BONE_FIND: bone_find, BONE_TRANSFORM: bone_transform, BONE_VECTOR: bone_vector,
                      BONES_ALLOC: bones_alloc, ITEM_TABLE: item_table, ITEM_KIND: item_kind, EFFECT: effect,
                      JOINT: joint, 0x009a6ef3: event_get, MANAGER_GET: manager_get, INV_GET: inv_get,
                      INV_ITEMS: inv_items, INV_FLAG: inv_flag, WEAPON_KIND: weapon_kind, WEAPON_54: weapon_54,
                      RIDER_RESET: rider_reset, POSE: pose, 0x0106b93a: manager_find, DRAW_BODY: draw_body,
                      DRAW_AFTER: draw_after, ALPHA_TEST: alpha_test, self.m.gl_color4: color4, SHADOW: shadow,
                      0x012bc5ab: shadow2})
        return stubs


def model_answer(case, index):
    """The model getter's BMD for a model index (a model record with +0x22 bone count and +0xf0 our tag)."""
    return MODEL_BASE + (index % 16)*0x100


def prepare_models(client, case):
    for slot in range(16):
        base = MODEL_BASE + slot*0x100
        client.models.define(base + 0x22, struct.pack('<h', 20 + slot))
        client.models.define(base + 0xf0, struct.pack('<i', -1))


def run_factory(m, client, s, kind, item, state):
    """0x0106cc74 + 0x0106cde5 in client memory; returns (object address, vtable) or (0, 0)."""
    stubs = client.mount_stubs(s)
    regions = client.mount_regions(s)
    desc = ARGS + 0x40
    client.args.define(desc, struct.pack('<3i', -1, -1, -1))
    res = m.execute(DESCRIPTOR, [desc, item, state], regions, stubs)
    if not res['ok']:
        return None, res
    client.args.data[:] = res['regions']['args']
    res = m.execute(FACTORY, [desc], regions, stubs, ecx=MANAGER, cleanup=4)
    if not res['ok']:
        return None, res
    for r in regions:
        if r.name in res['regions']:
            r.data[:] = res['regions'][r.name]
    obj = res['eax']
    if obj == 0:
        return (0, 0), res
    vt = struct.unpack('<I', bytes(client.heap.data[obj - HEAP_BASE:obj - HEAP_BASE + 4]))[0]
    return (obj, vt), res


def section_mount_class(m, lib, args, report):
    """Every factory key; for each class the model load, the play speeds and the rider offset."""
    rng = random.Random(args.seed ^ 0xc1a5)
    info = {c: lib.mu_hp_mount_class_info(c) for c in range(1, 22)}
    vt_class = {info[c].contents.vtable: c for c in info if info[c]}
    out = {'factory_cases': 0, 'factory_mismatches': 0, 'classes': {}, 'mismatches': 0}
    first = None
    # factory keys: every mount item with states 0..4, the no-item states, random items
    keys = [(item, st) for item in MOUNT_ITEMS for st in range(5)] + [(-1, st) for st in range(-1, 6)] + \
        [(0xffff, st) for st in range(0, 5)]
    keys += [(rng.randrange(0x3000), rng.randrange(6)) for _ in range(args.cases)]
    emitted = {}
    for item, st in keys:
        case = {'seed': 1, 'owners': [random_owner(rng, 0)], 'bone_salt': 7, 'height_base': 0.0, 'frustum_salt': 0,
                'item_kind': {item: 0x4f} if rng.random() < 0.5 else {}}
        client = MountClient(m, case)
        s = {'world': 0, 'scene': 2}
        stubs = client.mount_stubs(s)
        regions = client.mount_regions(s)
        res = m.execute(KIND, [item, st], regions, stubs)
        if not res['ok']:
            first = first or {'key': (item, st), 'machine': {k: v for k, v in res.items() if k != 'regions'}}
            out['factory_mismatches'] += 1
            continue
        kind_c = struct.unpack('<i', struct.pack('<I', res['eax']))[0]
        kind_n = lib.mu_hp_mount_kind(item, st, 1 if case['item_kind'] else 0)
        got, res2 = run_factory(m, client, s, kind_c, item, st)
        out['factory_cases'] += 1
        if got is None:
            first = first or {'key': (item, st), 'machine': {k: v for k, v in res2.items() if k != 'regions'}}
            out['factory_mismatches'] += 1
            continue
        cls_c = vt_class.get(got[1], 0 if got[1] == 0 else -got[1])
        cls_n = lib.mu_hp_mount_class(kind_n, item, st)
        if kind_c != kind_n or cls_c != cls_n:
            out['factory_mismatches'] += 1
            first = first or {'key': (item, st), 'kind': (kind_c, kind_n), 'class': (cls_c, cls_n)}
    # per class
    for c in range(1, 22):
        states = [0, 1, 2, 3, 4] if c == 4 else ([0, 7, 15] if 5 <= c <= 18 else [0])   # 7, 15: NATIVE-HELPERS-002
        for st in states:
            case = {'seed': 1, 'owners': [random_owner(rng, 0)], 'bone_salt': rng.getrandbits(16), 'height_base': 0.0,
                    'frustum_salt': 0, 'item_kind': {}}
            client = MountClient(m, case)
            prepare_models(client, case)
            s = {'world': 0, 'scene': 2}
            i = info[c].contents
            if c >= 19:
                kind, item, state = 2, c - 18, -1
                fk = (-1, c - 18)
            else:
                kind, item, state = 0, CLASS_ITEMS[c], st
                fk = (item, st)
            got, res = run_factory(m, client, s, kind, *fk)
            entry = {'vtable': hex(got[1]) if got else None}
            if got and got[1]:
                entry['shadow_slot'] = struct.unpack('<I', m.data_word(got[1] + 0x3c))[0]
            ok = got is not None and got[0] != 0
            if ok:
                obj = got[0]
                vt = got[1]
                # move the object into the mount region? keep it on the heap; set +0x1c = OBJECT
                o = MOUNT_BASE + 0x100
                client.mount.define(o, bytes(OBJ))
                client.mount.define(o + 0x318, struct.pack('<I', 0))
                client.heap.define(obj + 0x1c, struct.pack('<I', o))
                client.heap.define(obj + 4, struct.pack('<3i', kind, item if kind != 2 else c - 18, state))
                client.mount.define(o + 0x60, struct.pack('<i', SUBTYPE_SENTINEL))   # NATIVE-HELPERS-002
                regions, stubs = client.mount_regions(s), client.mount_stubs(s)
                slot = lambda k: struct.unpack('<I', m.data_word(vt + 4*k))[0]  # noqa: E731
                client.log.clear()
                r14 = m.execute(slot(14), [], regions, stubs, ecx=obj)
                if not r14['ok']:
                    entry['error'] = {k: v for k, v in r14.items() if k != 'regions'}
                    ok = False
                else:
                    for r in regions:
                        if r.name in r14['regions']:
                            r.data[:] = r14['regions'][r.name]
                    heap = client.heap.data
                    model = struct.unpack('<i', bytes(heap[obj + 0x10 - HEAP_BASE:obj + 0x14 - HEAP_BASE]))[0]
                    raw = bytes(client.mount.data[0x100:0x100 + OBJ])
                    entry['model'] = hex(model)
                    entry['scale'] = struct.unpack('<f', raw[0xa0:0xa4])[0]
                    entry['obj_type'] = hex(struct.unpack('<i', raw[0x5c:0x60])[0])
                    entry['subtype'] = struct.unpack('<i', raw[0x60:0x64])[0]
                    entry['log14'] = client.log[:]
                    # speeds
                    client.log.clear()
                    r2 = m.execute(slot(2), [], regions, stubs, ecx=obj)
                    for r in regions:
                        if r.name in r2['regions']:
                            r.data[:] = r2['regions'][r.name]
                    speeds = []
                    for a in range(16):
                        rs = m.execute(SPEED_LOOKUP, [a], regions, stubs, ecx=obj, cleanup=4)
                        if not all(v for k, v in rs['checks'].items() if k != 'x87_top'):
                            entry['speed_error'] = {k: v for k, v in rs.items() if k != 'regions'}
                            ok = False
                            break
                        speeds.append(m.st0_float())
                    entry['speeds'] = speeds
                    # offset
                    client.log.clear()
                    client.heap.define(obj + 0x20, struct.pack('<I', model_answer(case, model)))
                    client.heap.define(obj + 0x24, struct.pack('<3f', 1.0, 2.0, 3.0))
                    client.mount.define(o + 0xa0, struct.pack('<f', OFFSET_SCALE))   # makes the scale step visible
                    r4 = m.execute(slot(4), [], regions, stubs, ecx=obj)
                    if r4['ok']:
                        for r in regions:
                            if r.name in r4['regions']:
                                r.data[:] = r4['regions'][r.name]
                        entry['offset'] = struct.unpack('<3f', bytes(client.heap.data[obj + 0x24 - HEAP_BASE:
                                                                                      obj + 0x30 - HEAP_BASE]))
                        entry['bones'] = [e[1] for e in client.log if e[0] == 'bone']
                    else:
                        entry['offset_error'] = {k: v for k, v in r4.items() if k != 'regions'}
                        ok = False
            # compare with the library
            if ok:
                mismatch = []
                if lib.mu_hp_mount_model(c, st) != int(entry['model'], 16):
                    mismatch.append('model')
                for a in range(16):
                    if bits(lib.mu_hp_mount_speed(c, a)) != bits(entry['speeds'][a]):
                        mismatch.append(f'speed {a}')
                        break
                mi = info[c].contents
                if entry.get('bones') and (mi.bone or b'').decode() != entry['bones'][0]:
                    mismatch.append('bone')
                if bits(f32(mi.scale)) != bits(f32(entry['scale'])):
                    mismatch.append('scale')
                if lib.mu_hp_mount_object_subtype(c, st, SUBTYPE_SENTINEL) != entry['subtype']:
                    mismatch.append('subtype')   # NATIVE-HELPERS-002
                if entry.get('bones'):
                    base = bone_answer(entry['bones'][0], (0.0, 0.0, 0.0), case['bone_salt'])
                    exp = list(base)
                    if mi.scale_offset:
                        exp = [f32(f32(OFFSET_SCALE) * x) for x in exp]
                    if mi.has_lift:
                        exp[2] = f32(exp[2] + mi.lift)
                    if any(bits(f32(a)) != bits(b) for a, b in zip(exp, entry['offset'])):
                        mismatch.append('offset')
                if mismatch:
                    entry['mismatch'] = mismatch
                    out['mismatches'] += 1
                    first = first or {'class': c, 'state': st, 'mismatch': mismatch}
            else:
                out['mismatches'] += 1
                first = first or {'class': c, 'state': st, 'entry': entry}
            entry['salt'] = case['bone_salt']
            out['classes'][f'{c}/{st}'] = {k: v for k, v in entry.items() if k != 'log14'}
            emitted[(c, st)] = entry
    report['mount_class'] = dict(out, first_failure=first)
    if args.emit_classes:
        emit_classes(info, emitted)
    return first is None


def emit_classes(info, emitted):
    names = {5: ('GHOST_HORSE', 'ghost_horse', 0x19d7), 6: ('ICE_DRAGON', 'icedragon', 0x19e3),
             7: ('ICE_DRAGON_RARE', 'icedragon_rare', 0x19e4), 8: ('PIERCE_LION', 'fiercelion', 0x184b),
             9: ('PIERCE_LION_RARE', 'fiercelionR', 0x184c), 10: ('SHINING_TAIL', 'shiningtails', 0x1853),
             11: ('SHINING_TAIL_RARE', 'rare_shiningtails', 0x1854), 12: ('UR', 'Ur', 0x185d),
             13: ('UR_RARE', 'UrUp', 0x185e), 14: ('LEVIATHAN', 'Leviathan', 0x1833),
             15: ('LEVIATHAN_RARE', 'Leviathan_rare', 0x1834), 16: ('TAUROS', 'taurus', 0x1835),
             17: ('TAUROS_RARE', 'taurus_rare', 0x1836), 18: ('DIVINE_HORSE', 'Divine_Horse', 0x28f7),
             19: ('GIANT_1', 'Giant_DarkWizard_01', -1), 20: ('GIANT_2', 'Giant_Elf_01', -1),
             21: ('GIANT_3', 'Giant_GrowLancer_01', -1)}
    print('/* Generated by scripts/validate_helpers.py --sections mount_class --emit-classes: extracted by executing')
    print(' * each class\'s vtable +0x38 (model, scale), +8 with 0x0103dbf4 (speeds) and +0x10 (bone, lift).')
    print(' * The class moves (+0xc) of these classes are not reconstructed (ported 0). Included by helpers.c. */')

    def fl(x):
        x = f32(x)
        t = repr(x)
        for digits in range(0, 10):
            cand = f'{x:.{digits}f}'
            if f32(float(cand)) == x:
                t = cand
                break
        if 'e' not in t and '.' not in t:
            t += '.0'
        return t + 'f'
    for c in range(5, 22):
        e = emitted.get((c, 0))
        if not e or 'speeds' not in e:
            print(f'    /* class {c}: extraction failed */')
            continue
        name, file, item = names[c]
        bone = e['bones'][0] if e.get('bones') else ''
        base = bone_answer(bone, (0.0, 0.0, 0.0), e['salt'])
        scale_offset = bits(f32(e['offset'][0])) != bits(base[0])
        z = f32(f32(OFFSET_SCALE) * base[2]) if scale_offset else base[2]
        lift = f32(e['offset'][2] - z) if bits(f32(e['offset'][2])) != bits(z) else 0.0
        sp = ', '.join(fl(x) for x in e['speeds'])
        print(f'    {{MU_HP_MOUNT_{name}, {e["vtable"]}, {item if item < 0 else hex(item)}, {e["model"]}, "{file}", '
              f'"{bone}", {fl(lift)}, {1 if lift else 0}, {1 if scale_offset else 0}, 0, {fl(e["scale"])}, '
              f'{SHADOW_MODES[e["shadow_slot"]]},')
        print(f'     {{{sp}}}}},')


# --------------------------------------------------------------------------
# Mounts: move, rider, render.

MOUNT_OBJ = MOUNT_BASE + 0x100
OFFSET_SCALE = 1.5


def build_mount(m, client, s, cls, state):
    """Factory + descriptor + OBJECT pointer + speeds (vtable +8) in client memory. Returns (address, vtable)."""
    if cls >= 19:
        kind, item, st = 2, cls - 18, -1
        got, res = run_factory(m, client, s, 2, -1, cls - 18)
    else:
        kind, item, st = 0, CLASS_ITEMS[cls], state
        got, res = run_factory(m, client, s, 0, item, state)
    if not got or not got[0]:
        raise RuntimeError(f'factory failed for class {cls}: {res.get("stopped")}')
    obj, vt = got
    client.heap.define(obj + 4, struct.pack('<3i', kind, item, st))
    client.heap.define(obj + 0x14, struct.pack('<II', char_addr(0), owner_obj_addr(0)))
    client.heap.define(obj + 0x1c, struct.pack('<I', MOUNT_OBJ))
    client.mount_addr = obj
    client.mount.define(MOUNT_OBJ, bytes(OBJ))
    client.mount.define(MOUNT_OBJ + 0x318, struct.pack('<I', 0))
    regions, stubs = client.mount_regions(s), client.mount_stubs(s)
    slot2 = struct.unpack('<I', m.data_word(vt + 8))[0]
    r = m.execute(slot2, [], regions, stubs, ecx=obj)
    if not r['ok']:
        raise RuntimeError(f'speeds failed for class {cls}: {r.get("stopped")}')
    for reg in regions:
        if reg.name in r['regions']:
            reg.data[:] = r['regions'][reg.name]
    return obj, vt


def random_mount_state(rng, cls, model):
    o = Obj()
    o.live = rng.choice([1, 1, 1, 0])
    o.lighting, o.visible, o.alpha_enable, o.flag_0d, o.flag_0e = 1, rng.randrange(2), 0, 1, 0
    o.flag_41 = rng.randrange(2)
    o.action, o.prior_action = rng.randrange(12), rng.randrange(12)
    o.type = model
    o.subtype, o.field_68, o.lifetime, o.blend_mesh = 0, -1, 30, -1
    o.scale = f32(rng.choice([1.0, 0.85, 1.2]))
    o.blend_light, o.velocity = 1.0, 0.5
    o.frame = f32(rng.choice([rng.uniform(0, 8), 1.1, 1.05, 4.9, 5.0, 1.25, 1.35, 1.55, 1.7, 1.0, 1.2, 1.8]))
    o.prior_frame = f32(rng.uniform(0, 8))
    o.alpha_target, o.alpha, o.alpha_speed = 1.0, f32(rng.choice([1.0, 0.05, 0.5, 0.0])), 0.0
    for i in range(3):
        o.light[i] = f32(rng.uniform(0, 2))
        o.direction[i] = 0.0
        o.position[i] = f32(rng.uniform(1000, 9000))
        o.angle[i] = f32(rng.uniform(0, 360)) if i == 2 else 0.0
        o.head_angle[i] = 0.0
    o.owner = 0
    o.custom_shadow = rng.choice([0, 0, 1])
    o.shadow_alpha = f32(rng.uniform(0, 1))
    return o


def store_mount(client, obj, mt):
    """The library's Mount -> client memory (the C++ object at obj, its OBJECT at MOUNT_OBJ)."""
    h = client.heap
    h.define(obj + 0x10, struct.pack('<i', mt.model))
    h.define(obj + 0x14, struct.pack('<I', char_addr(mt.owner)))
    h.define(obj + 0x18, struct.pack('<I', owner_obj_addr(mt.owner)))
    h.define(obj + 0x20, struct.pack('<I', MODEL_BASE + (mt.model % 16)*0x100 if mt.has_model else 0))
    h.define(obj + 0x24, struct.pack('<3f', *mt.offset))
    h.define(obj + 0x30, struct.pack('<i', mt.action))
    h.define(obj + 0x34, bytes([mt.riding]))
    h.define(obj + 0x38, struct.pack('<i', mt.counter))
    h.define(obj + 0x3c, bytes([mt.shadow]))
    h.define(obj + 0x48, bytes([mt.flag_48]))
    h.define(obj + 0x4c, struct.pack('<i', mt.shadow_arg))
    h.define(obj + 0x50, bytes([mt.fly]))
    raw = object_to_bytes(mt.object, bytes(client.mount.data[0x100:0x100 + OBJ]))
    client.mount.define(MOUNT_OBJ, raw)
    client.mount.define(MOUNT_OBJ + 0x318, struct.pack('<I', 0))


def compare_mount(client, obj, mt):
    h = bytes(client.heap.data)
    b = lambda a, n: h[obj + a - HEAP_BASE:obj + a - HEAP_BASE + n]  # noqa: E731
    diffs = []
    got = {'offset': struct.unpack('<3f', b(0x24, 12)), 'action': struct.unpack('<i', b(0x30, 4))[0],
           'riding': b(0x34, 1)[0], 'counter': struct.unpack('<i', b(0x38, 4))[0], 'fly': b(0x50, 1)[0]}
    mine = {'offset': tuple(f32(x) for x in mt.offset), 'action': mt.action, 'riding': mt.riding,
            'counter': mt.counter, 'fly': mt.fly}
    for k in got:
        if not same(tuple(got[k]) if isinstance(got[k], tuple) else got[k],
                    tuple(mine[k]) if isinstance(mine[k], tuple) else mine[k]):
            diffs.append((k, got[k], mine[k]))
    raw = bytes(client.mount.data[0x100:0x100 + OBJ])
    if masked(raw) != masked(object_to_bytes(mt.object)):
        diffs.append(('object', [hex(j) for j in range(OBJ) if OBJECT_MASK[j] and raw[j] !=
                                 object_to_bytes(mt.object)[j]][:10]))
    return diffs


def mount_case(rng, cls):
    owner = random_owner(rng, 0)
    owner['action'] = rng.choice([0, 1, 0x26, 0x30, 0x47, 0x4e, 0x55, 0x67, 0x70, 0x90, 0x120, 0x135, 0x13b, 0x143,
                                  0x150, 0x190, rng.randrange(0x200)])
    return {'seed': rng.getrandbits(32), 'owners': [owner], 'bone_salt': rng.getrandbits(16),
            'height_base': 0.0, 'frustum_salt': rng.getrandbits(32), 'item_kind': {},
            'world': rng.choice([0, 0, 2, 2, 8, 10, 0x84, 0x27, 7, 0x18, 0x24, 0x80]),
            'scene': 2, 'event_state': rng.choice([0, 3, 4, 6]), 'crt_mode': rng.choice([0, 1]),
            'dark_horse_flag': 0, 'cls': cls, 'state': rng.choice([0, 1, 2, 4]) if cls == 4 else 0,
            'has_mount': 1, 'body_drawn': rng.choice([1, 1, 1, 0])}


def make_native_mount(lib, native, case, rng):
    cls = case['cls']
    mt = Mount()
    mt.live, mt.key, mt.cls = 1, 0, cls
    mt.kind, mt.item, mt.state = (2, cls - 18, -1) if cls >= 19 else (0, CLASS_ITEMS[cls], case['state'])
    mt.model = lib.mu_hp_mount_model(cls, case['state'])
    mt.owner = 0
    mt.object = random_mount_state(rng, cls, mt.model)
    mt.has_model = 1
    for i in range(3):
        mt.offset[i] = f32(rng.uniform(-50, 50))
    mt.action = rng.randrange(8)
    mt.riding, mt.counter = rng.randrange(2), rng.choice([0, 1, 5, 99, 100, 101])
    mt.shadow, mt.flag_48, mt.shadow_arg, mt.fly = rng.choice([1, 1, 0]), 0, rng.choice([0, 5]), rng.randrange(2)
    native.mount = mt
    return mt


def run_mount_case(m, lib, case, rng, mode, plant=None):
    client, native = MountClient(m, case), Native(lib, case, plant)
    prepare_models(client, case)
    s = {'world': case['world'], 'scene': case['scene']}
    obj, vt = build_mount(m, client, s, case['cls'], case['state'])
    mt = make_native_mount(lib, native, case, rng)
    if plant == 'speed':
        mt.object.action = (mt.object.action + 1) % 12
    store_mount(client, obj, mt)
    if plant == 'speed':
        mt.object.action = (mt.object.action - 1) % 12
    owners = case['owners']
    inputs = Inputs(s['world'] if plant != 'world' else (2 if s['world'] != 2 else 0), s['scene'],
                    case['event_state'], 0)
    rhost = native.render_host()
    stats = {'steps': 0, 'events': 0}
    slot = lambda k: struct.unpack('<I', m.data_word(vt + 4*k))[0]  # noqa: E731
    for step in range(case['steps']):
        client.set_owners(owners)
        native.set_owners(owners)
        client.log.clear()
        native.log.clear()
        regions, stubs = client.mount_regions(s), client.mount_stubs(s)
        info = lib.mu_hp_mount_class_info(case['cls']).contents
        if mode == 'move':
            res = m.execute(slot(3) if info.ported else MOVE_BASE, [], regions, stubs, ecx=obj)
            if not res['ok']:
                return {'ok': False, 'step': step, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
            for r in regions:
                if r.name in res['regions']:
                    r.data[:] = res['regions'][r.name]
            moved = res['eax'] & 0xff
            if info.ported:
                mine = lib.mu_hp_mount_move(ctypes.byref(native.h), ctypes.byref(mt), ctypes.byref(inputs))
            else:
                mine = lib.mu_hp_mount_move_base(ctypes.byref(native.h), ctypes.byref(mt), ctypes.byref(inputs))
            if bool(moved) != bool(mine):
                return {'ok': False, 'step': step, 'why': 'return', 'client': moved, 'native': mine}
            if moved:
                res = m.execute(slot(9), [], regions, stubs, ecx=obj)
                if not res['ok']:
                    return {'ok': False, 'step': step, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
                for r in regions:
                    if r.name in res['regions']:
                        r.data[:] = res['regions'][r.name]
                lib.mu_hp_mount_follow_action(ctypes.byref(native.h), ctypes.byref(mt))
        elif mode == 'render':
            res = m.execute(RENDER_BODY, [], regions, stubs, ecx=obj)
            if not res['ok']:
                return {'ok': False, 'step': step, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
            for r in regions:
                if r.name in res['regions']:
                    r.data[:] = res['regions'][r.name]
            if res['eax'] & 0xff:
                for start in (RENDER_SHADOW, RENDER_AFTER):
                    res = m.execute(start, [], regions, stubs, ecx=obj)
                    if not res['ok']:
                        return {'ok': False, 'step': step, 'start': hex(start),
                                'machine': {k: v for k, v in res.items() if k != 'regions'}}
                    for r in regions:
                        if r.name in res['regions']:
                            r.data[:] = res['regions'][r.name]
            lib.mu_hp_mount_render(ctypes.byref(native.h), ctypes.byref(mt), ctypes.byref(inputs), ctypes.byref(rhost))
        elif mode == 'lift':
            lift = rng.randrange(2)
            res = m.execute(LIFT, [lift], regions, stubs, ecx=obj, cleanup=4)
            if not res['ok']:
                return {'ok': False, 'step': step, 'machine': {k: v for k, v in res.items() if k != 'regions'}}
            for r in regions:
                if r.name in res['regions']:
                    r.data[:] = res['regions'][r.name]
            lib.mu_hp_mount_place_owner(ctypes.byref(native.h), ctypes.byref(mt), lift)
        stats['steps'] += 1
        stats['events'] += len(client.log)
        clog = [e for e in client.log if e[0] != 'pose']
        if not same_log(clog, native.log):
            return {'ok': False, 'step': step, 'why': 'log', 'client': clog[:20], 'native': native.log[:20]}
        if (client.rand_state, client.rand_calls) != (native.h.rand_state, native.h.rand_calls):
            return {'ok': False, 'step': step, 'why': 'rand'}
        d = compare_mount(client, obj, mt)
        if d:
            return {'ok': False, 'step': step, 'why': 'fields', 'diffs': d}
        co, no = client.read_owner(0), native.read_owner(0)
        if not same(tuple(co['position']), tuple(no['position'])) or co['ring'] != no['ring']:
            return {'ok': False, 'step': step, 'why': 'owner', 'client': co, 'native': no}
        # next step: the owner moves and acts
        jitter_owners(owners, rng.getrandbits(32))
        owners[0]['action'] = rng.choice([0, 0x26, 0x47, 0x67, 0x90, 0x13b, 0x143, rng.randrange(0x200)])
        owners[0]['fade'] = rng.choice([0, 0, 0, 1, 2])
        owners[0]['hidden'] = rng.choice([0]*6 + [1])
        owners[0]['ring'] = rng.choice([0, 0, 1])
        case['body_drawn'] = rng.choice([1, 1, 1, 0])
        if mt.cls >= 19 or not info.ported:
            pass
    return {'ok': True, 'stats': stats}


MOVE_PROBES = {
    0x01064cc2: 'uniria dust', 0x01040302: 'dinorant dust', 0x010401e6: 'dinorant fly actions',
    0x01043a8f: 'fenrir flying step', 0x01043d90: 'fenrir ground', 0x0103f5e0: 'dark horse run',
    0x0103f457: 'dark horse dust', 0x0103fc59: 'dark horse ring', 0x0103d5bf: 'fade clamp',
}


def section_mount_move(m, lib, args, report):
    rng = random.Random(args.seed ^ 0x3017)
    m.add_probes(MOVE_PROBES)
    totals = {'cases': 0, 'mismatches': 0, 'steps': 0, 'events': 0, 'by_class': {}}
    first = None
    classes = [1, 2, 3, 4]*4 + list(range(5, 19))
    for i in range(args.cases):
        cls = classes[i % len(classes)]
        case = mount_case(rng, cls)
        case['steps'] = rng.randrange(4, 16)
        r = run_mount_case(m, lib, case, rng, 'move')
        totals['cases'] += 1
        totals['by_class'][cls] = totals['by_class'].get(cls, 0) + 1
        if r['ok']:
            totals['steps'] += r['stats']['steps']
            totals['events'] += r['stats']['events']
        else:
            totals['mismatches'] += 1
            if first is None:
                first = dict(r, cls=cls, world=case['world'])
    probes = {label: m.probes[a] for a, label in MOVE_PROBES.items()}
    report['mount_move'] = dict(totals, first_failure=first, probes=probes)
    if args.negative:
        det = {}
        for plant in ('buff', 'world', 'speed'):
            hit = False
            rng2 = random.Random(args.seed ^ len(plant))
            for i in range(args.negative):
                case = mount_case(rng2, [1, 2, 3, 4][i % 4])
                case['steps'] = 8
                if plant == 'buff':
                    case['owners'][0]['buff_12'] = 0
                if not run_mount_case(m, lib, case, rng2, 'move', plant)['ok']:
                    hit = True
                    break
            det[plant] = hit
        report['mount_move']['negative'] = det
    return first is None and all(probes.values())


def section_mount_render(m, lib, args, report):
    rng = random.Random(args.seed ^ 0x4e4d)
    totals = {'cases': 0, 'mismatches': 0, 'steps': 0, 'events': 0, 'lift_cases': 0}
    first = None
    for i in range(args.cases):
        cls = [1, 2, 3, 4, 5, 8, 16, 14, 18][i % 9]
        case = mount_case(rng, cls)
        case['steps'] = rng.randrange(3, 10)
        mode = 'render' if i % 3 else 'lift'
        r = run_mount_case(m, lib, case, rng, mode)
        totals['cases'] += 1
        totals['lift_cases'] += mode == 'lift'
        if r['ok']:
            totals['steps'] += r['stats']['steps']
            totals['events'] += r['stats']['events']
        else:
            totals['mismatches'] += 1
            first = first or dict(r, cls=cls, mode=mode, world=case['world'])
    report['mount_render'] = dict(totals, first_failure=first)
    return first is None


def section_rider(m, lib, args, report):
    """0x0106c382(c, how) with and without a mount, and the action category 0x0106c4b6."""
    rng = random.Random(args.seed ^ 0x51de)
    totals = {'cases': 0, 'mismatches': 0, 'category': 0}
    first = None
    for i in range(args.cases*4):
        case = mount_case(rng, rng.choice([1, 2, 3, 4]))
        case['has_mount'] = rng.randrange(2)
        o = case['owners'][0]
        o['weapon'] = [rng.choice([-1, 0xae6 + rng.randrange(0x1400)]), rng.choice([-1, 0xae6 + rng.randrange(0x1400)])]
        o['class_byte'] = rng.choice([rng.randrange(256), 9, 0x19, 0x29])
        how = rng.choice([0, 1, 2, 6, 3, 5, -1])
        client, native = MountClient(m, case), Native(lib, case)
        prepare_models(client, case)
        s = {'world': case['world'], 'scene': case['scene']}
        if case['has_mount']:
            obj, vt = build_mount(m, client, s, case['cls'], case['state'])
        client.set_owners(case['owners'])
        native.set_owners(case['owners'])
        regions, stubs = client.mount_regions(s), client.mount_stubs(s)
        res = m.execute(RIDER, [char_addr(0), how & 0xffffffff], regions, stubs)
        totals['cases'] += 1
        if not res['ok']:
            totals['mismatches'] += 1
            first = first or {'machine': {k: v for k, v in res.items() if k != 'regions'}}
            continue
        lib.mu_hp_rider_action(ctypes.byref(native.h), 0, how)
        if not same_log(client.log, native.log):
            totals['mismatches'] += 1
            first = first or {'how': how, 'client': client.log, 'native': native.log, 'owner': o}
    # the category over every action word
    stubs = {}
    for a in range(0, 0x200):
        cdata = am.defined_region('obj', 0x25000000, struct.pack('<H', a)*0x20)
        res = m.execute(CATEGORY, [0x25000000 - 0x2a + 0x2a], [cdata], stubs)
        if res['ok'] and res['eax'] != lib.mu_hp_action_category(a):
            totals['mismatches'] += 1
            first = first or {'category': a, 'client': res['eax'], 'native': lib.mu_hp_action_category(a)}
        totals['category'] += 1
    report['rider'] = dict(totals, first_failure=first)
    return first is None


# --------------------------------------------------------------------------
# Driver.

def section_bugs(m, lib, args, report):
    rng = random.Random(args.seed ^ 0xb065)
    m.add_probes(BUG_PROBES)
    totals = {'cases': 0, 'mismatches': 0, 'steps': 0, 'events': 0, 'creates': 0, 'renders': 0}
    first = None
    for i in range(args.bug_cases):
        case = bug_case(rng, i)
        r = run_bug_case(m, lib, case)
        totals['cases'] += 1
        if r['ok']:
            for k in ('steps', 'events', 'creates', 'renders'):
                totals[k] += r['stats'][k]
        else:
            totals['mismatches'] += 1
            if first is None:
                first = r
    probes = {label: m.probes[a] for a, label in BUG_PROBES.items()}
    report['bugs'] = dict(totals, first_failure=first, probes=probes)
    if any(v == 0 for v in probes.values()):
        print('bugs: unreached probes', [k for k, v in probes.items() if v == 0])
        first = first or {'unreached': [k for k, v in probes.items() if v == 0]}
    if args.negative:
        detected = {}
        for plant in ('buff', 'world'):
            hit = 0
            rng2 = random.Random(args.seed ^ hash(plant) & 0xffff)
            for i in range(args.negative):
                case = bug_case(rng2, i)
                if not run_bug_case(m, lib, case, plant)['ok']:
                    hit = 1
                    break
            detected[plant] = bool(hit)
        report['bugs']['negative'] = detected
    return totals['mismatches'] == 0 and first is None


MUTATIONS = {1: ('mount_class', 'Fenrir model of state 1'), 2: ('bugs', 'angel spawn height'),
             3: ('rider', 'armed walk action'), 4: ('rider', 'action category boundary'),
             5: ('mount_move', 'base move fade step'), 6: ('mount_render', 'render counter wrap')}


def run_mutations(m, args):
    import shutil
    import tempfile
    caught = {}
    src = ROOT/'reconstructed/helpers'
    for n, (section, label) in MUTATIONS.items():
        tmp = Path(tempfile.mkdtemp(prefix='mu-hp-mut-'))
        out = tmp/f'libclient_helpers.{SUFFIX}'
        cmd = ['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', f'-DMU_HP_MUTATION={n}',
               '-shared', str(src/'helpers.c'), str(ROOT/'reconstructed/movement/client_movement.c'),
               str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(out)]
        subprocess.run(cmd, check=True, capture_output=True)
        lib = load_library(out)
        sub = argparse.Namespace(**vars(args))
        sub.cases, sub.bug_cases, sub.negative, sub.emit_classes = min(args.cases, 120), min(args.bug_cases, 120), 0, False
        rep = {}
        good = globals()['section_' + section](m, lib, sub, rep)
        caught[f'{n} {label}'] = not good
        shutil.rmtree(tmp, ignore_errors=True)
    return caught


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', default=str(DEFAULT_TEXT))
    ap.add_argument('--data', default=str(DEFAULT_DATA))
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--bug-cases', type=int, default=300)
    ap.add_argument('--cases', type=int, default=500)
    ap.add_argument('--negative', type=int, default=0)
    ap.add_argument('--sections', default='bugs,mount_class,mount_move,rider,mount_render')
    ap.add_argument('--report', default=None)
    ap.add_argument('--mutations', action='store_true', help='rebuild with each planted mistake; all must be caught')
    ap.add_argument('--emit-classes', action='store_true', help='print mount_classes.h extracted by execution')
    args = ap.parse_args(argv)
    text, data = load_inputs(args)
    lib = load_library()
    m = Machine(text, data)
    report = {'bodies': body_digests(text), 'seed': args.seed}
    sections = [s for s in args.sections.split(',') if s]
    ok = True
    t0 = time.time()
    for name in sections:
        fn = globals().get('section_' + name)
        if fn is None:
            raise SystemExit(f'unknown section {name}')
        s0 = time.time()
        good = fn(m, lib, args, report)
        ok = ok and good
        print(f'{name}: {"ok" if good else "MISMATCH"} ({time.time() - s0:.1f} s)', flush=True)
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
    print(text_out[:6000])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
