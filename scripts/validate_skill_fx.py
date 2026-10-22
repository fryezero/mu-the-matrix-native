#!/usr/bin/env python3
"""Compare reconstructed/combat/skill_fx.c with the client's instructions (NATIVE-COMBAT-002).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case),
with the x87 helpers of scripts/validate_combat.py. The authored C (libcombat)
runs on the same inputs.

Families (client routine -> authored function):

* effect_create  CreateEffect 0x013c0f19 -> mu_sfx_effect_create. The object
                 initialiser 0x0129eb81 is a stub that defines the record as
                 zero; the effect-manager hooks 0x01094ff1 / 0x01095279 answer
                 0; rand(), RequestTerrainHeight, the trigonometric wrappers
                 (host libm) and nested CreateEffect are recording stubs; the
                 live setter, the vector accessors, AngleMatrix 0x00cff32a and
                 VectorRotate 0x00d000ad run as client code.
* effect_move    MoveEffect 0x0142fd09 -> mu_sfx_effect_move. AddTerrainLight,
                 CreateParticle, CreateJoint, CreateEffect, the model getters
                 (a synthetic model with an action table), PlayAnimation, the
                 two hit checks and DeleteEffect (modelled as clearing the live
                 byte) are recording stubs; the generic motion 0x0150df8e runs
                 as client code.
* check_magic    the spell hit check 0x013be199 -> mu_sfx_check_magic (CRT
                 sqrt is a stub returning the host double square root).

Every case compares the record fields the C models (bit for bit; any two NaNs
are equal, as in validate_combat.py), the calls in client order with the
values the client passes, and the number of rand() calls. Negative controls
(the C with one planted mistake, emulated in Python) must disagree on some
cases.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import validate_combat as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

CREATE_EFFECT, MOVE_EFFECT, CHECK_MAGIC, CHECK_ARROW = 0x013c0f19, 0x0142fd09, 0x013be199, 0x013bd374
CREATE_SPRITE, AREA_ATTACK, FLOAT_SQRT, FLOAT_ATAN = 0x01692eb7, 0x013bc25e, 0x00961a07, 0x012b2bca
SERIAL_STEP, QUAKE, WORLD_PREDICATE, WORLD = 0x01d1df18, 0x0bdb588c, 0x009b0418, 0x01cf15fc
HERO_POINTER = 0x0a39d754
ATTRIBUTE = 0x016d34db
CREATE_EFFECT_WRAPPER, CREATE_PARTICLE, CREATE_JOINT = 0x013c0eaa, 0x0168fafd, 0x0153b02c
TERRAIN_LIGHT, TERRAIN_HEIGHT, RAND = 0x016cacfc, 0x016cc9e2, 0x01989721
SINE, COSINE, CRT_SQRT = 0x009681bd, 0x009fa223, 0x019856f0
OBJECT_INIT, MANAGER_A, MANAGER_B = 0x0129eb81, 0x01094ff1, 0x01095279
MODEL_CONTAINER, MODEL_GETTER, PLAY_ANIMATION, DELETE_EFFECT = 0x00966cc4, 0x00eaa8cf, 0x012b4dd3, 0x0142eea4
MODEL_POSE, MODEL_BONE = 0x012b5064, 0x012b678d   # NATIVE-CHARSEL-003: the star dragon poses its model, reads bone 1
BONE_OFFSET = (11.0, -7.0, 23.0)                  # the stub's bone 1 = the effect position + this
POOL = 0x0a4ca430
HERO_DATA_PTR = 0x01d1df18
FRAME_LIGHT = 0x0b9f5430
BODIES = {
    'create_effect': (0x013c0f19, 0x0142b5d8), 'move_effect': (0x0142fd09, 0x0150cc95),
    'helper_claw_draw': (0x01527c4e, 0x01528118), 'helper_rune_draw': (0x0152d6a6, 0x0152d7ca),
    'fenrir_step_draw': (0x0151a5c7, 0x0151a712), 'shock_ring_draw': (0x01514ded, 0x01514f08),
    'effect_advance': (0x0150df8e, 0x0150e1b9), 'check_magic': (0x013be199, 0x013bec7c),
    'heal_joints': (0x0142d83b, 0x0142da3e), 'angle_matrix': (0x00cff32a, 0x00cff4a0),
    'vector_rotate': (0x00d000ad, 0x00d001a0), 'create_particle': (0x015ae7b0, 0x015c3dec),
    'move_particles': (0x01616c80, 0x0168eeb2), 'render_particles': (0x0159123f, 0x015ae373),
    'move_position': (0x012af52d, 0x012af5cb), 'render_sprite': (0x0184c39c, 0x0184ca6b),
}
INPUTS = 0x21000000       # case argument vectors
OBJECTS = 0x22000000      # owner / target objects, 0x400 apart
MODEL = 0x23000000        # synthetic model (getter result) and its action table
HERO_DATA = 0x24000000    # [0x01d1df18] points here (+0x2dec skill serial)
CONTAINER = 0x25000000    # model container (only passed as `this`)
LIGHT_SCRATCH = 0x26000000

f32, bits, from_bits, same = vc.f32, vc.bits, vc.from_bits, vc.same


GL_IMPORTS = {  # IAT slot: (name, stdcall argument count); the slots hold Wine opengl32 addresses
    0x1a7c750: ('glBegin', 1), 0x1a7c760: ('glEnd', 0), 0x1a7c76c: ('glColor3f', 3), 0x1a7c770: ('glColor3fv', 1),
    0x1a7c774: ('glTexCoord2f', 2), 0x1a7c778: ('glVertex3fv', 1), 0x1a7c754: ('glColor4f', 4),
    0x1a7c9a4: ('timeGetTime', 0),   # NATIVE-HELPERS-002: Fenrir's paw marks
}
TIME_GET_TIME_SLOT = 0x1a7c9a4
TRANSFORM_POSITION, KILL_CLEANUP = 0x012b6ef1, 0x009b0451   # NATIVE-HELPERS-002


class FxMachine(vc.Combat):
    """validate_combat's machine plus stubs that continue elsewhere: a handler
    returning ('jump', address) sets EIP without returning (used to leave a
    routine's loop body for its own epilogue), and executable pages at the
    OpenGL import targets so that GL calls can be recording stubs."""

    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_ALL
        targets = sorted({struct.unpack('<I', data[slot-am.DATA_BASE:slot-am.DATA_BASE+4])[0] & ~0xfff
                          for slot in GL_IMPORTS})
        for page in targets:
            self.uc.mem_map(page, am.PAGE, UC_PROT_ALL)
            self.uc.mem_write(page, b'\xc3'*am.PAGE)
        self.gl_target = {slot: struct.unpack('<I', data[slot-am.DATA_BASE:slot-am.DATA_BASE+4])[0]
                          for slot in GL_IMPORTS}

    def stub_entry(self, uc, address, size, ignored):
        handler = self.stubs.get(address)
        if handler is not None and getattr(handler, 'jump_to', None) is not None:
            uc.reg_write(self.x86.UC_X86_REG_EIP, handler.jump_to)
            return
        super().stub_entry(uc, address, size, ignored)


def jump_stub(address):
    def stub(mm):
        return 0
    stub.jump_to = address
    return stub


# --------------------------------------------------------------------------
# Library.

class Effect(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('flag5', ctypes.c_uint8), ('visible', ctypes.c_uint8),
                ('flag_c', ctypes.c_uint8), ('action', ctypes.c_uint16), ('prior_action', ctypes.c_uint16),
                ('client_hit', ctypes.c_uint8), ('skill', ctypes.c_uint16), ('info6', ctypes.c_uint8),
                ('key', ctypes.c_uint16), ('serial', ctypes.c_uint16), ('type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('field_68', ctypes.c_int32), ('lifetime', ctypes.c_int32),
                ('blend_mesh', ctypes.c_int32), ('field_78', ctypes.c_int32), ('field_80', ctypes.c_int32),
                ('scale', ctypes.c_float), ('scale_arg', ctypes.c_float), ('blend_light', ctypes.c_float),
                ('blend_u', ctypes.c_float), ('blend_v', ctypes.c_float), ('velocity', ctypes.c_float),
                ('gravity', ctypes.c_float), ('frame', ctypes.c_float), ('prior_frame', ctypes.c_float),
                ('alpha', ctypes.c_float), ('light', ctypes.c_float*3), ('direction', ctypes.c_float*3),
                ('position', ctypes.c_float*3), ('angle', ctypes.c_float*3), ('start', ctypes.c_float*3),
                ('owner', ctypes.c_int32), ('field_364', ctypes.c_uint16), ('field_58', ctypes.c_int32),
                ('field_2e4', ctypes.c_int32), ('field_6', ctypes.c_uint8), ('field_70', ctypes.c_int32),
                ('heading', ctypes.c_float), ('field_64', ctypes.c_int32), ('time_mark', ctypes.c_uint32)]


class Info(ctypes.Structure):
    _fields_ = [('key', ctypes.c_uint16), ('skill', ctypes.c_uint16), ('word4', ctypes.c_uint16),
                ('word6', ctypes.c_uint16), ('field8', ctypes.c_uint16), ('field18', ctypes.c_int32),
                ('field1c', ctypes.c_int32)]


class Object(ctypes.Structure):   # mu_jt_object (reconstructed/joints)
    _fields_ = [('live', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('weapon', ctypes.c_int16),
                ('position', ctypes.c_float*3), ('light', ctypes.c_float*3),
                ('action', ctypes.c_uint16), ('type', ctypes.c_int32),
                ('eye_188', ctypes.c_float*3), ('eye_194', ctypes.c_float*3)]   # NATIVE-HELPERS-002


class Call(ctypes.Structure):
    _fields_ = [('routine', ctypes.c_int32), ('type', ctypes.c_int32), ('subtype', ctypes.c_int32),
                ('owner', ctypes.c_int32), ('range', ctypes.c_int32), ('scale', ctypes.c_float),
                ('position', ctypes.c_float*3), ('target', ctypes.c_float*3), ('angle', ctypes.c_float*3),
                ('light', ctypes.c_float*3)]


class Particle(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('type', ctypes.c_int32), ('tex_type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('scale', ctypes.c_float), ('position', ctypes.c_float*3),
                ('angle', ctypes.c_float*3), ('light', ctypes.c_float*3), ('lifetime', ctypes.c_int32),
                ('owner', ctypes.c_int32), ('owner_position', ctypes.c_float*3), ('rotation', ctypes.c_float),
                ('frame', ctypes.c_int32), ('moving', ctypes.c_uint8), ('gravity', ctypes.c_float),
                ('velocity', ctypes.c_float*3), ('start', ctypes.c_float*3), ('start_angle', ctypes.c_float*3),
                ('time', ctypes.c_float), ('arg8', ctypes.c_int32)]


class BitmapInfo(ctypes.Structure):
    _fields_ = [('width', ctypes.c_float), ('height', ctypes.c_float), ('components', ctypes.c_int8)]


class Sprite(ctypes.Structure):
    _fields_ = [('bitmap', ctypes.c_int32), ('position', ctypes.c_float*3), ('width', ctypes.c_float),
                ('height', ctypes.c_float), ('light', ctypes.c_float*3), ('rotation', ctypes.c_float),
                ('u', ctypes.c_float), ('v', ctypes.c_float), ('uw', ctypes.c_float), ('vh', ctypes.c_float),
                ('axes', ctypes.c_int32), ('additive', ctypes.c_uint8)]


PARTICLE_FIELDS = [
    ('live', 0x08, 'B', 1), ('type', 0x0c, 'i', 1), ('tex_type', 0x10, 'i', 1), ('subtype', 0x14, 'i', 1),
    ('scale', 0x18, 'f', 1), ('position', 0x20, 'f', 3), ('angle', 0x2c, 'f', 3), ('light', 0x38, 'f', 3),
    ('lifetime', 0x48, 'i', 1), ('owner_position', 0x54, 'f', 3), ('rotation', 0x60, 'f', 1),
    ('frame', 0x64, 'i', 1), ('moving', 0x68, 'B', 1), ('gravity', 0x6c, 'f', 1), ('velocity', 0x70, 'f', 3),
    ('start', 0x88, 'f', 3), ('start_angle', 0x94, 'f', 3), ('time', 0xac, 'f', 1), ('arg8', 0xb0, 'i', 1),
]
PARTICLE = 0x27000000    # the shared record the smart-pointer accessor 0x0169084c returns
PARTICLE_BYTES = 0xc0


def particle_to_bytes(p, names):
    data = bytearray(am.poison(PARTICLE_BYTES, 0x3b))
    mask = bytearray(PARTICLE_BYTES)
    for name, offset, fmt, count in PARTICLE_FIELDS:
        if name not in names:
            continue
        value = getattr(p, name)
        values = list(value) if count > 1 else [value]
        raw = b''.join(struct.pack('<'+fmt, v) for v in values)
        data[offset:offset+len(raw)] = raw
        mask[offset:offset+len(raw)] = b'\1'*len(raw)
    if 'owner' in names:
        struct.pack_into('<I', data, 0x50, object_address(p.owner))
        mask[0x50:0x54] = b'\1'*4
    return bytes(data), bytes(mask)


def compare_particle(p, raw, mask, names):
    for name, offset, fmt, count in PARTICLE_FIELDS:
        if name not in names:
            continue
        size = struct.calcsize('<'+fmt)
        mine = getattr(p, name)
        mine = list(mine) if count > 1 else [mine]
        for k in range(count):
            o = offset+k*size
            if not all(mask[o:o+size]):
                return (name, k, 'client left undefined', mine[k])
            theirs = struct.unpack('<'+fmt, bytes(raw[o:o+size]))[0]
            if fmt == 'f':
                if not same(theirs, mine[k]):
                    return (name, k, theirs, mine[k])
            elif theirs != mine[k]:
                return (name, k, theirs, mine[k])
    return None


class Joint(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('type', ctypes.c_int32), ('tex_type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('render_type', ctypes.c_uint8), ('faces', ctypes.c_uint8),
                ('scale', ctypes.c_float), ('position', ctypes.c_float*3), ('start', ctypes.c_float*3),
                ('angle', ctypes.c_float*3), ('light', ctypes.c_float*3), ('target', ctypes.c_int32),
                ('target_position', ctypes.c_float*3), ('field_64', ctypes.c_uint8), ('num_tails', ctypes.c_int32),
                ('max_tails', ctypes.c_int32), ('tails', ctypes.c_float*(50*12)), ('lifetime', ctypes.c_int32),
                ('reached', ctypes.c_uint8), ('velocity', ctypes.c_float), ('jitter', ctypes.c_float*3),
                ('key', ctypes.c_uint16), ('skill', ctypes.c_uint16), ('serial', ctypes.c_uint8),
                ('field_a24', ctypes.c_uint8), ('field_a25', ctypes.c_uint8), ('tail_update', ctypes.c_uint8),
                ('field_a3c', ctypes.c_uint8), ('field_a44', ctypes.c_uint16), ('time', ctypes.c_float),
                ('brightness', ctypes.c_float), ('field_a54', ctypes.c_float), ('moving', ctypes.c_uint8),
                ('field_a60', ctypes.c_int32), ('phase', ctypes.c_int32)]   # mu_jt_joint (reconstructed/joints)


class JointQuad(ctypes.Structure):
    _fields_ = [('position', ctypes.c_float*12), ('uv', ctypes.c_float*8)]


JOINT_FIELDS = [
    ('live', 0x000, 'B', 1), ('type', 0x004, 'i', 1), ('tex_type', 0x008, 'i', 1), ('subtype', 0x00c, 'i', 1),
    ('render_type', 0x010, 'B', 1), ('faces', 0x011, 'B', 1), ('scale', 0x014, 'f', 1),
    ('position', 0x018, 'f', 3), ('start', 0x024, 'f', 3), ('angle', 0x030, 'f', 3), ('light', 0x048, 'f', 3),
    ('target_position', 0x058, 'f', 3), ('field_64', 0x064, 'B', 1), ('num_tails', 0x068, 'i', 1),
    ('max_tails', 0x06c, 'i', 1), ('tails', 0x070, 'f', 600), ('lifetime', 0xa00, 'i', 1), ('reached', 0xa04, 'B', 1),
    ('velocity', 0xa08, 'f', 1), ('jitter', 0xa0c, 'f', 3), ('key', 0xa18, 'H', 1), ('skill', 0xa1a, 'H', 1),
    ('serial', 0xa1c, 'B', 1), ('field_a24', 0xa24, 'B', 1), ('field_a25', 0xa25, 'B', 1),
    ('tail_update', 0xa26, 'B', 1), ('field_a3c', 0xa3c, 'B', 1), ('field_a44', 0xa44, 'H', 1), ('time', 0xa48, 'f', 1),
    ('brightness', 0xa4c, 'f', 1), ('field_a54', 0xa54, 'f', 1), ('moving', 0xa5c, 'B', 1),
    ('field_a60', 0xa60, 'i', 1), ('phase', 0xa20, 'i', 1),
]
JOINT_POOL, JOINT_BYTES = 0x0a4fa4f0, 0xa64


def joint_values(j, name, count):
    v = getattr(j, name)
    return list(v) if count > 1 else [v]


def joint_to_bytes(j, names, base=None, mask=None):
    data = bytearray(am.poison(JOINT_BYTES, 0x2f)) if base is None else bytearray(base)
    mask = bytearray(JOINT_BYTES) if mask is None else bytearray(mask)
    for name, offset, fmt, count in JOINT_FIELDS:
        if name not in names:
            continue
        raw = b''.join(struct.pack('<'+fmt, v) for v in joint_values(j, name, count))
        data[offset:offset+len(raw)] = raw
        mask[offset:offset+len(raw)] = b'\1'*len(raw)
    if 'target' in names:
        struct.pack_into('<I', data, 0x54, object_address(j.target))
        mask[0x54:0x58] = b'\1'*4
    return bytes(data), bytes(mask)


def joint_from_bytes(raw, j):
    for name, offset, fmt, count in JOINT_FIELDS:
        size = struct.calcsize('<'+fmt)
        values = [struct.unpack('<'+fmt, bytes(raw[offset+k*size:offset+(k+1)*size]))[0] for k in range(count)]
        if count > 1:
            arr = getattr(j, name)
            for k, v in enumerate(values):
                arr[k] = v
        else:
            setattr(j, name, values[0])
    j.target = owner_of(struct.unpack('<I', bytes(raw[0x54:0x58]))[0]) if isinstance(
        owner_of(struct.unpack('<I', bytes(raw[0x54:0x58]))[0]), int) else -9


def compare_joint(j, raw, mask, names):
    for name, offset, fmt, count in JOINT_FIELDS:
        if name not in names:
            continue
        size = struct.calcsize('<'+fmt)
        mine = joint_values(j, name, count)
        for k in range(count):
            o = offset+k*size
            if not all(mask[o:o+size]):
                return (name, k, 'client left undefined', mine[k])
            theirs = struct.unpack('<'+fmt, bytes(raw[o:o+size]))[0]
            if fmt == 'f':
                if not same(theirs, mine[k]):
                    return (name, k, theirs, mine[k])
            elif theirs != mine[k]:
                return (name, k, theirs, mine[k])
    return None


class PlayerState(ctypes.Structure):
    _fields_ = [('class_byte', ctypes.c_uint8), ('state_59', ctypes.c_uint8), ('state_5a', ctypes.c_uint8),
                ('state_72', ctypes.c_uint8), ('predicate', ctypes.c_uint8), ('class_check', ctypes.c_uint8),
                ('transform', ctypes.c_uint16), ('field_3324', ctypes.c_float), ('world_voice', ctypes.c_uint8)]


RAND_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
OBJECT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
CALL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(Call), ctypes.POINTER(Effect))
MODEL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint16,
                            ctypes.POINTER(ctypes.c_int16))


BONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Effect), ctypes.c_int32,
                           ctypes.POINTER(ctypes.c_float))
TIME_FN = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p)
OWNER_BONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                                 ctypes.POINTER(ctypes.c_float))


class Env(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('rand', RAND_FN), ('height', HEIGHT_FN), ('object', OBJECT_FN),
                ('call', CALL_FN), ('model', MODEL_FN), ('serial', ctypes.c_uint8),
                ('report_checks', ctypes.c_uint8), ('hero_object', ctypes.c_int32), ('bone', BONE_FN),
                ('time_ms', TIME_FN), ('owner_bone', OWNER_BONE_FN)]   # NATIVE-HELPERS-002


def load_library(path):
    lib = ctypes.CDLL(str(path))
    P = ctypes.POINTER
    F3 = ctypes.c_float*3
    lib.mu_sfx_effect_create.argtypes = [P(Effect), ctypes.c_int32, ctypes.c_int32, F3, F3, F3, ctypes.c_int32,
                                         ctypes.c_float, P(Info), P(Env)]
    lib.mu_sfx_effect_create.restype = ctypes.c_int
    lib.mu_sfx_effect_move.argtypes = [P(Effect), P(Env)]
    lib.mu_sfx_effect_move.restype = ctypes.c_int
    lib.mu_sfx_check_magic.argtypes = [P(Effect), P(Env)]
    lib.mu_sfx_check_magic.restype = None
    lib.mu_sfx_particle_create.argtypes = [P(Particle), ctypes.c_int32, F3, F3, F3, ctypes.c_int32, ctypes.c_float,
                                           ctypes.c_int32, ctypes.c_int32, P(Env)]
    lib.mu_sfx_particle_create.restype = ctypes.c_int
    lib.mu_sfx_particle_move.argtypes = [P(Particle), ctypes.c_float]
    lib.mu_sfx_particle_move.restype = ctypes.c_int
    lib.mu_sfx_particle_render.argtypes = [P(Particle), P(BitmapInfo), ctypes.c_uint8, P(Sprite)]
    lib.mu_sfx_particle_render.restype = ctypes.c_int
    lib.mu_sfx_sprite_corners.argtypes = [P(ctypes.c_float*12), P(Sprite), P((ctypes.c_float*3)*4),
                                          P((ctypes.c_float*2)*4)]
    lib.mu_sfx_sprite_corners.restype = None
    lib.mu_sfx_joint_create.argtypes = [P(Joint), ctypes.c_int32, F3, F3, F3, ctypes.c_int32, ctypes.c_int32,
                                        ctypes.c_float, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint8,
                                        ctypes.c_uint16, ctypes.c_int32, P(Env)]
    lib.mu_sfx_joint_create.restype = ctypes.c_int
    lib.mu_sfx_joint_move.argtypes = [P(Joint), P(Env), ctypes.c_float, ctypes.c_int, ctypes.c_uint16, ctypes.c_int]
    lib.mu_sfx_joint_move.restype = ctypes.c_int
    lib.mu_sfx_joint_render.argtypes = [P(Joint), ctypes.c_uint8, F3, P(ctypes.c_int32), P(JointQuad), ctypes.c_int]
    lib.mu_sfx_joint_render.restype = ctypes.c_int
    I32P = P(ctypes.c_int32)
    lib.mu_player_shock.argtypes = [P(PlayerState), I32P, ctypes.c_int32, I32P, I32P]
    lib.mu_player_shock.restype = ctypes.c_int32
    lib.mu_player_die.argtypes = [P(PlayerState), I32P, ctypes.c_int32, I32P, I32P]
    lib.mu_player_die.restype = ctypes.c_int32
    lib.mu_player_attack_sound.argtypes = [P(PlayerState), ctypes.c_int32, ctypes.c_int16, ctypes.c_int16,
                                           ctypes.c_int32, I32P, ctypes.c_int32, I32P]
    lib.mu_player_attack_sound.restype = ctypes.c_int32
    lib.mu_player_attack_action.argtypes = [P(vc.AttackInput), P(vc.AttackResult)]
    lib.mu_player_attack_action.restype = None
    return lib


# Record fields: (C name, client offset, struct format, component count).
EFFECT_FIELDS = [
    ('live', 0x00, 'B', 1), ('flag5', 0x05, 'B', 1), ('flag_c', 0x0c, 'B', 1),
    ('action', 0x2a, 'H', 1), ('prior_action', 0x2c, 'H', 1), ('client_hit', 0x3b, 'B', 1), ('skill', 0x3c, 'H', 1),
    ('info6', 0x45, 'B', 1), ('key', 0x54, 'H', 1), ('serial', 0x56, 'H', 1), ('type', 0x5c, 'i', 1),
    ('subtype', 0x60, 'i', 1), ('field_68', 0x68, 'i', 1), ('lifetime', 0x6c, 'i', 1), ('blend_mesh', 0x74, 'i', 1),
    ('field_78', 0x78, 'i', 1), ('field_80', 0x80, 'i', 1), ('scale', 0xa0, 'f', 1), ('scale_arg', 0xa4, 'f', 1),
    ('blend_light', 0xa8, 'f', 1), ('blend_u', 0xac, 'f', 1), ('blend_v', 0xb0, 'f', 1), ('velocity', 0xbc, 'f', 1),
    ('gravity', 0xc8, 'f', 1), ('frame', 0xd0, 'f', 1), ('prior_frame', 0xd4, 'f', 1), ('alpha', 0xdc, 'f', 1),
    ('light', 0xec, 'f', 3), ('direction', 0xf8, 'f', 3), ('position', 0x158, 'f', 3), ('angle', 0x164, 'f', 3),
    ('start', 0x1d0, 'f', 3), ('field_364', 0x364, 'H', 1), ('field_58', 0x58, 'i', 1), ('field_2e4', 0x2e4, 'i', 1),
    ('field_6', 0x06, 'B', 1), ('field_70', 0x70, 'i', 1), ('heading', 0x170, 'f', 1),
    ('field_64', 0x64, 'i', 1), ('time_mark', 0x9c, 'I', 1),   # NATIVE-HELPERS-002
]
# visible (+0x0b) is an input of the hit checks only; owner (+0x34c) is a pointer handled separately.


def object_address(index):
    return 0 if index < 0 else OBJECTS + 0x400*index


def effect_to_bytes(e, defined_names):
    """Client bytes of a record from the C struct; fields in defined_names are defined."""
    data = bytearray(am.poison(0x3d8, 0x47))
    mask = bytearray(0x3d8)
    for name, offset, fmt, count in EFFECT_FIELDS + [('visible', 0x0b, 'B', 1)]:
        if name not in defined_names:
            continue
        value = getattr(e, name)
        values = list(value) if count > 1 else [value]
        raw = b''.join(struct.pack('<'+fmt, v) for v in values)
        data[offset:offset+len(raw)] = raw
        mask[offset:offset+len(raw)] = b'\1'*len(raw)
    if 'owner' in defined_names:
        struct.pack_into('<I', data, 0x34c, object_address(e.owner))
        mask[0x34c:0x350] = b'\1'*4
    return bytes(data), bytes(mask)


def compare_effect(e, raw, mask, names=None):
    """Every modelled field the client defined must equal C (and C must not
    have changed a field the client left undefined: those keep the case input)."""
    for name, offset, fmt, count in EFFECT_FIELDS:
        if names is not None and name not in names:
            continue
        size = struct.calcsize('<'+fmt)
        mine = getattr(e, name)
        mine = list(mine) if count > 1 else [mine]
        for k in range(count):
            o = offset+k*size
            if not all(mask[o:o+size]):
                return (name, k, 'client left undefined', mine[k])
            theirs = struct.unpack('<'+fmt, bytes(raw[o:o+size]))[0]
            if fmt == 'f':
                if not same(theirs, mine[k]):
                    return (name, k, theirs, mine[k])
            elif theirs != mine[k]:
                return (name, k, theirs, mine[k])
    return None


def owner_of(address):
    if address == 0:
        return -1
    if OBJECTS <= address < OBJECTS + 0x400*64 and (address-OBJECTS) % 0x400 == 0:
        return (address-OBJECTS)//0x400
    if POOL <= address < POOL + 0x3d8*200:
        return -2
    return ('pointer', hex(address))


def random_object(rng):
    o = Object()
    o.live = rng.choice([0, 1, 1, 1, 2])
    o.visible = rng.choice([0, 1, 1, 1])
    o.weapon = rng.choice([0, 9, 0x600, 0x603, 0x7ff, 0x800, 0x1000])
    o.type = rng.choice([0x4a8, 0x4a9, 0x4aa, 0x4ab, 0xa91])
    for k in range(3):
        o.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 500.0)
    return o


def object_region(objects, writable=False):
    size = 0x400*max(1, len(objects))
    data = bytearray(am.poison(size, 0x29))
    mask = bytearray(size)
    for i, o in enumerate(objects):
        base = 0x400*i
        data[base] = o.live
        data[base+0x0b] = o.visible
        struct.pack_into('<h', data, base+0x56, o.weapon)
        struct.pack_into('<3f', data, base+0x158, *o.position)
        struct.pack_into('<i', data, base+0x5c, o.type)
        for a, n in ((0, 1), (0x0b, 1), (0x56, 2), (0x158, 12), (0x5c, 4)):
            mask[base+a:base+a+n] = b'\1'*n
    return am.Region('objects', OBJECTS, bytes(data), bytes(mask), writable)


class Case:
    """Shared stubs and C callbacks for one case."""

    def __init__(self, rng, objects, rand_values, height, animation=1, keys=1, has_model=True):
        self.objects = objects
        self.rand_values = list(rand_values)
        self.height_value = height
        self.client_calls, self.c_calls = [], []
        self.client_rand = self.c_rand = 0
        self.animation, self.keys, self.has_model = animation, keys, has_model
        self.c_objects = (Object*max(1, len(objects)))(*objects) if objects else (Object*1)()
        self.c_serial_steps = 0
        self.c_quake = None
        self.attributes = None   # TerrainWall words (the tornado's attribute test)
        self.times = ([rng.choice([1000, 1199, 1200, 1201, 5000, rng.randrange(0, 1 << 32)]) for _ in range(6)]
                      if rng is not None else [1000])
        self.client_time = self.c_time = 0

    # ---- client side
    def stubs(self, m):
        def rand(mm):
            v = self.rand_values[self.client_rand] if self.client_rand < len(self.rand_values) else 0
            self.client_rand += 1
            return v

        def height(mm):
            self.client_calls.append(('height', mm.float_argument(0), mm.float_argument(1)))
            return mm.x87_return(self.height_value)

        def sine(mm):
            x = mm.float_argument(0)
            return mm.x87_return(f32(math.sin(x)) if math.isfinite(x) else float('nan'))

        def cosine(mm):
            x = mm.float_argument(0)
            return mm.x87_return(f32(math.cos(x)) if math.isfinite(x) else float('nan'))

        def sqrt(mm):
            lo, hi = mm.argument(0), mm.argument(1)
            v = struct.unpack('<d', struct.pack('<II', lo, hi))[0]
            return mm.x87_return(math.sqrt(v) if v >= 0 else float('nan'), double=True)

        def terrain_light(mm):
            light = mm.floats(mm.argument(2), 3)
            self.client_calls.append(('light', mm.float_argument(0), mm.float_argument(1), light,
                                      mm.argument(3), mm.argument(4)))
            return 0

        def particle(mm):
            a = [mm.argument(i) for i in range(8)]
            self.client_calls.append(('particle', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      a[4], from_bits(a[5]), owner_of(a[6]), a[7]))
            return 0

        def joint(mm):
            a = [mm.argument(i) for i in range(14)]
            self.client_calls.append(('joint', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      a[4], owner_of(a[5]), from_bits(a[6]), a[7:14]))
            return 0

        def effect(mm):
            a = [mm.argument(i) for i in range(14)]
            sub = a[4] - (1 << 32) if a[4] & 0x80000000 else a[4]
            self.client_calls.append(('effect', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3),
                                      sub, owner_of(a[5]), a[6:14]))
            return 0

        def init(mm):
            o = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
            self.client_calls.append(('init', hex(o)))
            mm.write(o, b'\0'*0x3d8)
            return 0

        def zero8(mm):
            return 0, 8

        def container(mm):
            return CONTAINER, 0

        def getter(mm):
            return (MODEL if self.has_model else 0), 4

        def play(mm):
            a = [mm.argument(i) for i in range(6)]
            self.client_calls.append(('animation', [hex(x) for x in a[:3]], from_bits(a[3]), hex(a[4]), hex(a[5])))
            return self.animation, 0x18

        def check(name):
            def stub(mm):
                self.client_calls.append(('check', name, hex(mm.argument(0))))
                return 0
            return stub

        def delete(mm):
            o = mm.argument(0)
            self.client_calls.append(('delete', hex(o)))
            mm.write(o, b'\0')
            return 0

        def sprite(mm):
            a = [mm.argument(i) for i in range(8)]
            self.client_calls.append(('sprite', a[0], mm.floats(a[1], 3), from_bits(a[2]), mm.floats(a[3], 3),
                                      owner_of(a[4]), from_bits(a[5])))
            return 0

        def area(mm):
            a = [mm.argument(i) for i in range(8)]
            self.client_calls.append(('area', a[0], from_bits(a[1]), mm.floats(a[2], 3), a[3]))
            return 0

        def world_predicate(mm):
            return 0

        def fsqrt(mm):
            return mm.x87_return(f32(math.sqrt(mm.float_argument(0))) if mm.float_argument(0) >= 0 else float('nan'))

        def fatan(mm):
            return mm.x87_return(f32(math.atan(mm.float_argument(0))))

        def sound(mm):
            self.client_calls.append(('sound', mm.argument(0), owner_of(mm.argument(1)), mm.argument(2)))
            return 0

        def pose(mm):
            a = [mm.argument(i) for i in range(8)]
            self.client_calls.append(('pose', hex(a[0]), a[7], a[6]))
            return 0, 0x20

        def bone(mm):
            out, o, index, relative = (mm.argument(i) for i in range(4))
            self.client_calls.append(('bone', owner_of(o), index, relative))
            p = mm.floats(o + 0x158, 3)
            mm.uc.mem_write(out, struct.pack('<3f', *(f32(p[k] + BONE_OFFSET[k]) for k in range(3))))   # the caller's frame
            return 0, 0x10

        def time_get_time(mm):   # NATIVE-HELPERS-002
            v = self.times[self.client_time % len(self.times)]
            self.client_time += 1
            return v

        def transform_position(mm):
            matrix, vin, vout = mm.argument(0), mm.argument(1), mm.argument(2)
            index = (matrix - 0x06fce398) // 0x30
            vec = mm.floats(vin, 3)
            self.client_calls.append(('owner_bone', index, vec, mm.argument(3)))
            mm.write(vout, struct.pack('<3f', *owner_bone_answer(index, vec)))
            return 0, 0x10

        def kill(mm):
            self.client_calls.append(('kill',))
            return 0
        extra = {m.gl_target[TIME_GET_TIME_SLOT]: time_get_time, TRANSFORM_POSITION: transform_position,
                 KILL_CLEANUP: kill}
        return {**extra, MODEL_POSE: pose, MODEL_BONE: bone, PLAY_BUFFER: sound, WORLD_PREDICATE: world_predicate, CREATE_SPRITE: sprite, AREA_ATTACK: area,
                FLOAT_SQRT: fsqrt, FLOAT_ATAN: fatan,
                RAND: rand, TERRAIN_HEIGHT: height, SINE: sine, COSINE: cosine, CRT_SQRT: sqrt,
                TERRAIN_LIGHT: terrain_light, CREATE_PARTICLE: particle, CREATE_JOINT: joint,
                CREATE_EFFECT_WRAPPER: effect, OBJECT_INIT: init, MANAGER_A: zero8, MANAGER_B: zero8,
                MODEL_CONTAINER: container, MODEL_GETTER: getter, PLAY_ANIMATION: play,
                CHECK_ARROW: check('arrow'), CHECK_MAGIC: check('magic'), DELETE_EFFECT: delete}

    # ---- C side
    def env(self, serial=0, report_checks=1, hero_object=-1):
        def rand(ctx):
            v = self.rand_values[self.c_rand] if self.c_rand < len(self.rand_values) else 0
            self.c_rand += 1
            return v

        def height(ctx, x, y):
            self.c_calls.append(('height', x, y))
            return self.height_value

        def obj(ctx, index):
            if 0 <= index < len(self.objects):
                return ctypes.addressof(self.c_objects[index])
            return None

        def call(ctx, cp, ep):
            c = cp.contents
            if c.routine == TERRAIN_LIGHT:
                self.c_calls.append(('light', c.position[0], c.position[1], list(c.light), c.range, FRAME_LIGHT))
            elif c.routine == CREATE_PARTICLE:
                self.c_calls.append(('particle', c.type, list(c.position), list(c.angle), list(c.light), c.subtype,
                                     c.scale, c.owner, 0))
            elif c.routine == CREATE_JOINT:
                self.c_calls.append(('joint', c.type, list(c.position), list(c.target), list(c.angle), c.subtype,
                                     c.owner, c.scale, None))
            elif c.routine == CREATE_EFFECT_WRAPPER:
                self.c_calls.append(('effect', c.type, list(c.position), list(c.angle), list(c.light), c.subtype,
                                     c.owner, None))
            elif c.routine == PLAY_ANIMATION:
                self.c_calls.append(('animation', None, c.scale, None, None))
                return self.animation
            elif c.routine in (CHECK_ARROW, CHECK_MAGIC):
                self.c_calls.append(('check', 'arrow' if c.routine == CHECK_ARROW else 'magic', None))
            elif c.routine == DELETE_EFFECT:
                self.c_calls.append(('delete', None))
            elif c.routine == CREATE_SPRITE:
                self.c_calls.append(('sprite', c.type, list(c.position), c.scale, list(c.light), c.owner,
                                     c.angle[0]))
            elif c.routine == AREA_ATTACK and c.range:
                self.c_calls.append(('area', c.type, c.scale, list(c.position), c.subtype))
            elif c.routine == AREA_ATTACK:
                self.c_calls.append(('area', c.type, c.scale, list(c.position), c.subtype))
            elif c.routine == SERIAL_STEP:
                self.c_serial_steps += 1
            elif c.routine == PLAY_BUFFER:
                self.c_calls.append(('sound', c.type, c.owner, 0))
            elif c.routine == ATTRIBUTE:
                index = ((c.range & 0xff) << 8) + (c.subtype & 0xff)
                return self.attributes[index] if self.attributes else 0
            elif c.routine == QUAKE:
                self.c_quake = c.scale
            elif c.routine == MODEL_POSE:
                self.c_calls.append(('pose', hex(0x06fce398), 0, 0))
            elif c.routine == MODEL_BONE:
                self.c_calls.append(('bone', c.owner, c.range, 0))
            elif c.routine == KILL_CLEANUP:
                self.c_calls.append(('kill',))
            return 0

        def bone(ctx, ep, index, out):
            for k in range(3):
                out[k] = f32(ep.contents.position[k] + BONE_OFFSET[k])

        def model(ctx, t, action, keys):
            keys[0] = self.keys
            return 1 if self.has_model else 0
        def time_ms(ctx):
            v = self.times[self.c_time % len(self.times)]
            self.c_time += 1
            return v

        def owner_bone(ctx, owner, index, vin, vout):
            vec = [vin[0], vin[1], vin[2]]
            self.c_calls.append(('owner_bone', index, vec, 0))
            out = owner_bone_answer(index, vec)
            for k in range(3):
                vout[k] = out[k]
        self._keep = (RAND_FN(rand), HEIGHT_FN(height), OBJECT_FN(obj), CALL_FN(call), MODEL_FN(model), BONE_FN(bone),
                      TIME_FN(time_ms), OWNER_BONE_FN(owner_bone))
        env = Env()
        env.rand, env.height, env.object, env.call, env.model, env.bone, env.time_ms, env.owner_bone = self._keep
        env.serial = serial
        env.report_checks = report_checks
        env.hero_object = hero_object
        return env


def owner_bone_answer(index, vec):
    """The synthetic TransformPosition of both sides (NATIVE-HELPERS-002)."""
    return [f32(f32(vec[k]) + f32(index*10.0 + 100.0*k + 3.0)) for k in range(3)]


def compare_calls(client, mine, skip_tail=True):
    """Calls in order. Tail fields the C does not model (raw pointer arguments,
    constant trailing arguments) are None on the C side and skipped."""
    client = [c for c in client if c[0] != 'init']
    if len(client) != len(mine):
        return ('count', len(client), len(mine), client[:6], mine[:6])
    for a, b in zip(client, mine):
        if a[0] != b[0]:
            return ('kind', a, b)
        for x, y in zip(a[1:], b[1:]):
            if y is None:
                continue
            if not vc._same_call([x], [y]):
                return ('value', a, b)
    return None


# --------------------------------------------------------------------------
# Families.

EFFECT_KINDS = [(0x43b, 0), (0x43b, 2), (0x413, 1), (0x7f2b, 0), (0x7f84, 1), (0x41c, 0), (0x41d, 0), (0x457, 0),
                (0x421, 0), (0x453, 0), (0x454, 0), (0x419, 0), (0x41a, 0), (0x419, 1), (0x41a, 1),
                (0x40e, 0),   # the Tormenta tornado (NATIVE-JOINT-001)
                (0x5ac, 0), (0x5ac, 1), (0x5ad, 0), (0x5ad, 1),   # the character select's star dragon (NATIVE-CHARSEL-003)
                # NATIVE-HELPERS-002: the flying step, Fenrir's lightning and paw marks
                (0x8012, 1), (0x4ac, 0), (0x4ad, 1), (0x4ad, 2), (0x4ad, 3), (0x4ad, 4), (0x4ad, 5), (0x6f3, 0), (0x6f3, 1), (0x6f3, 2), (0x6f6, 0), (0x8438, 0)]
OWNED_KINDS = {0x4ac, 0x4ad}   # the client reads their owner unconditionally
TERRAIN_WALL, PLAY_BUFFER = 0x0b795420, 0x00a6ac96
ARROW_SKILLS = [0, 0, 0, 0x7e7, 0x2d7, 0x7fe, 0x18, 0x34]


def rand_values(rng, n=40):
    return [rng.choice([0, 1, 2, 3, 5, 89, 90, 359, 360, 0x7fff, rng.randrange(0, 0x8000)]) for _ in range(n)]


def random_info(rng, kind):
    info = Info()
    info.key = rng.randrange(0, 0x10000)
    info.skill = rng.choice([0, 0x18, 0x34, 4, 17, 26])
    info.word4 = rng.choice(ARROW_SKILLS + [1, 2, 0x101])
    info.word6 = rng.randrange(0, 0x10000)
    info.field8 = rng.randrange(0, 0x10000)
    info.field18 = rng.randrange(-2**31, 2**31)
    info.field1c = rng.randrange(-2**31, 2**31)
    return info


def info_bytes(info):
    raw = bytearray(0x20)
    struct.pack_into('<HHHHH', raw, 0, info.key, info.skill, info.word4, info.word6, info.field8)
    struct.pack_into('<iiiii', raw, 0x0c, 0, 0, 0, info.field18, info.field1c)
    return bytes(raw)


def family_effect_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = EFFECT_KINDS[n % len(EFFECT_KINDS)]
        objects = [random_object(rng) for _ in range(2)]
        owner = rng.choice([-1, 0, 1]) if kind[0] not in OWNED_KINDS else rng.choice([0, 1])
        pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
        angle = [vc.rfloat(rng, 0.1, 360.0) if k == 2 or rng.random() < 0.3 else 0.0 for k in range(3)]
        light = [vc.rfloat(rng, 0.1, 1.5) for _ in range(3)]
        scale = rng.choice([0.0, -1.0, 1.0, 0.5, 2.0, float('nan'), vc.rfloat(rng, 0.2, 3.0)])
        scale = f32(scale)
        info = random_info(rng, kind)
        serial = rng.randrange(0, 256)
        tornado_hero = None
        if kind[0] == 0x40e:
            tornado_hero = rng.choice([0, 1])   # the tornado reads the hero's position through [0x0a39d754]
            if rng.random() < 0.5:
                for k in range(2):
                    objects[tornado_hero].position[k] = f32(pos[k] + rng.uniform(-900.0, 900.0))
        case = Case(rng, objects, rand_values(rng), vc.rfloat(rng, 0.1, 400.0))
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<9f', *pos, *angle, *light) + info_bytes(info),
                                   writable=False)
        record = am.Region('record', POOL, am.poison(0x3d8, 0x31), bytes(0x3d8))
        record.define(POOL, b'\0')        # slot 0 is free
        hero = am.Region('hero-data', HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
        hero.define(HERO_DATA+0x2dec, bytes([serial]))
        regions = [inputs, record, object_region(objects), hero,
                   am.defined_region('hero-ptr', HERO_DATA_PTR, struct.pack('<I', HERO_DATA), writable=False)]
        hero_obj = rng.choice([-1, 0, 1, owner]) if tornado_hero is None else tornado_hero
        hero_char = (object_address(hero_obj) - 0x3254) & 0xffffffff if hero_obj >= 0 else 0x5000000
        regions += [am.defined_region('hero', HERO_POINTER, struct.pack('<I', hero_char), writable=False)]
        r = m.execute(CREATE_EFFECT, [kind[0], kind[1], INPUTS, INPUTS+12, INPUTS+24, object_address(owner),
                                      bits(scale), INPUTS+36], regions, case.stubs(m), ecx=POOL, cleanup=0x20)
        e = Effect()
        F3 = ctypes.c_float*3
        env = case.env(serial=serial, hero_object=hero_obj)
        supported = lib.mu_sfx_effect_create(ctypes.byref(e), kind[0], kind[1], F3(*pos), F3(*angle), F3(*light),
                                              owner, scale, ctypes.byref(info), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            raw = r['regions']['record']
            mismatch = compare_effect(e, raw, record.defined)
            if mismatch is None:
                theirs = struct.unpack('<I', raw[0x34c:0x350])[0]
                if theirs != object_address(owner):
                    mismatch = ('owner', hex(theirs), owner)
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None:
                after = r['regions']['hero-data'][0x2dec]
                if after != (serial + case.c_serial_steps) & 0xff:
                    mismatch = ('serial', serial, after, case.c_serial_steps)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('effect_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                            'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('effect_create', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r):
            raw = r['regions']['record']
            # negative control: the arrow flies 60 units per step (COMBAT-001's viewer choice)
            if kind[0] == 0x43b:
                d = struct.unpack('<f', raw[0xfc:0x100])[0]
                negatives['create_arrow_speed_60'] += not same(d, -60.0)
            # negative control (NATIVE-HELPERS-002): the shock ring sized over 20
            if kind[0] == 0x8012:
                sc = struct.unpack('<f', raw[0xa0:0xa4])[0]
                negatives['create_shockwave_over_20'] += not same(sc, f32(f32(case.rand_values[0] % 10 + 10.0) / 20.0))
            # negative control: Energy Ball without the +100 lift
            if kind[0] == 0x7f2b:
                z = struct.unpack('<f', raw[0x160:0x164])[0]
                negatives['create_energy_no_lift'] += not same(z, pos[2])


def random_effect(rng, kind):
    e = Effect()
    e.live = 1
    e.type, e.subtype = kind
    e.flag5 = 1
    e.action = rng.choice([0, 0, 1, 0xff, 3])
    e.prior_action = rng.randrange(0, 0x10000)
    e.client_hit = rng.choice([0, 1])
    # arrows of skills 0x7e7 / 0x7fc / 0x7fd (ground test) and 0x2d8 (arc) are not reconstructed
    e.skill = rng.choice([0, 0, 0x18, 0x34, 0x2d7]) if kind[0] == 0x43b else rng.choice([0, 4, 17, 26])
    e.lifetime = rng.choice([30, 29, 6, 5, 4, 1, 0, -1, 60, 20, 2, rng.randrange(-5, 70)])
    e.blend_mesh = rng.choice([-1, 1])
    e.scale = vc.rfloat(rng, 0.1, 2.0)
    e.scale_arg = vc.rfloat(rng, 0.1, 2.0)
    e.field_70 = rng.choice([20, 60, 12, 1, 0, -2])
    e.blend_light = vc.rfloat(rng, 0.2, 1.0)
    e.velocity = vc.rfloat(rng, 0.1, 1.0)
    e.frame = vc.rfloat(rng, 0.1, 10.0)
    e.prior_frame = vc.rfloat(rng, 0.1, 10.0)
    e.alpha = f32(rng.choice([0.0, 0.1, 0.7, 1.0, 1.2])) if kind[0] in (0x6f3, 0x6f6, 0x8438) else 1.0
    e.gravity = f32(rng.choice([17.0, 8.0, 0.0, -3.0, vc.rfloat(rng, 0.2, 30.0)]))
    e.key = rng.randrange(0, 0x10000)
    e.blend_u = vc.rfloat(rng, 0.2, 1.0)
    e.serial = rng.randrange(0, 256)
    for k in range(3):
        e.light[k] = vc.rfloat(rng, 0.1, 1.0)
        e.direction[k] = rng.choice([0.0, -50.0, -60.0, -70.0, vc.rfloat(rng, 0.1, 100.0)])
        e.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        e.angle[k] = vc.rfloat(rng, 0.1, 360.0) if k == 2 or rng.random() < 0.3 else 0.0
        e.start[k] = vc.rfloat(rng, 0.1, 30000.0)
    e.owner = rng.choice([-1, 0, 1]) if kind[0] != 0x454 else rng.choice([0, 1])   # the swirl always has its caster
    if kind[0] in OWNED_KINDS:
        e.owner = rng.choice([0, 1])
    e.field_64 = rng.choice([0, 0, 1, 2, 4, 5, rng.randrange(-2, 8)])   # NATIVE-HELPERS-002
    e.time_mark = rng.choice([1000, 999, 800, 0, rng.randrange(0, 1 << 32)])
    if kind[0] == 0x8012:
        e.lifetime = rng.choice([20, 19, 21, 1, 0, rng.randrange(-2, 41)])
        e.scale = f32(rng.choice([0.0, -0.1, 1.5, vc.rfloat(rng, 0.1, 3.0)]))
    if kind[0] in OWNED_KINDS:
        e.alpha = f32(rng.choice([0.7, 1.0, 0.05, 0.3, 0.0, -0.2, vc.rfloat(rng, 0.0, 1.2)]))
        e.live = rng.choice([1, 1, 2])
    e.heading = f32(rng.choice([0.0, 1.57, 3.13, rng.uniform(0.0, 3.14), vc.rfloat(rng, 0.1, 10.0)]))
    if kind[0] == 0x40e:
        e.lifetime = rng.choice([150, 149, 75, 2, 1, 0, rng.randrange(-2, 151)])
    return e


MOVE_DEFINED = {'live', 'flag5', 'action', 'prior_action', 'client_hit', 'skill', 'type', 'subtype', 'lifetime',
                'blend_mesh', 'scale', 'blend_light', 'velocity', 'frame', 'prior_frame', 'alpha', 'light',
                'direction', 'position', 'angle', 'start', 'owner', 'gravity', 'key', 'blend_u', 'serial',
                'heading', 'field_64', 'time_mark', 'field_70', 'scale_arg'}


def family_effect_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = EFFECT_KINDS[n % len(EFFECT_KINDS)]
        e = random_effect(rng, kind)
        objects = [random_object(rng) for _ in range(2)]
        animation = rng.choice([0, 1, 1])
        keys = rng.choice([1, 7, 10, 30, -3])
        has_model = rng.random() < 0.9
        case = Case(rng, objects, rand_values(rng), vc.rfloat(rng, 0.1, 400.0), animation, keys, has_model)
        raw, mask = effect_to_bytes(e, MOVE_DEFINED)
        record = am.Region('record', POOL, raw, mask)
        model = am.Region('model', MODEL, am.poison(0x2000, 0x55), bytes(0x2000))
        model.define(MODEL+0x30, struct.pack('<I', MODEL+0x1000))
        for a in range(0x100):
            model.define(MODEL+0x1000+16*a+8, struct.pack('<h', keys))
        quake = am.Region('quake', QUAKE, am.poison(4, 0x21), bytes(4))
        regions = [record, object_region(objects), model, quake,
                   am.defined_region('world', WORLD, struct.pack('<i', 0), writable=False)]
        if kind[0] == 0x40e:
            case.attributes = [rng.choice([0, 0, 8, 4, 0xc, 0x100, 0x108]) for _ in range(0x10000)]
            regions.append(am.defined_region('terrain-wall', TERRAIN_WALL, struct.pack('<65536H', *case.attributes),
                                             writable=False))
        before = Effect.from_buffer_copy(e)
        r = m.execute(MOVE_EFFECT, [POOL, 0], regions, case.stubs(m))
        env = case.env()
        supported = lib.mu_sfx_effect_move(ctypes.byref(e), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = compare_effect(e, out, record.defined, MOVE_DEFINED | {'frame'})
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None and case.c_quake is not None:
                q = struct.unpack('<f', r['regions']['quake'])[0]
                if not same(q, case.c_quake):
                    mismatch = ('quake', q, case.c_quake)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('effect_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                          'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('effect_move', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r):
            out = r['regions']['record']
            # negative control: the lifetime check after the decrement for every type
            lt = struct.unpack('<i', out[0x6c:0x70])[0]
            if kind[0] != 0x413 and has_model:
                wrong_live = 0 if before.lifetime - 1 <= 0 else 1
                negatives['move_decrement_first'] += (out[0] != 0) != bool(wrong_live)
            # negative control (NATIVE-HELPERS-002): Fenrir's lightning fading by 0.2 instead of 0.3
            if kind[0] == 0x6f3 and before.field_70 > 0 and has_model:
                negatives['claw_no_shrink'] += not same(e.scale, before.scale)
            if kind[0] == 0x8438 and before.field_70 > 0:
                negatives['rune_no_growth'] += not same(e.scale, before.scale)
            if kind[0] == 0x6f6:
                negatives['tail_wrong_particle'] += any(c[0] == 'particle' and c[1] == 0x8086 and c[5] != 0x13
                                                        for c in case.client_calls)
            if kind == (0x4ac, 0) and before.live and before.field_64 in (0, 1):
                a = struct.unpack('<f', out[0xdc:0xe0])[0]
                step = f32(0.2) if before.field_64 == 0 else f32(-0.2)
                negatives['move_lightning_fade_02'] += not same(a, f32(before.alpha + step))
            # negative control: straight motion without the angle rotation
            if has_model or kind[0] >= 0x7a4:
                px = struct.unpack('<f', out[0x158:0x15c])[0]
                negatives['move_unrotated'] += not same(px, f32(before.position[0] + before.direction[0]))
            del lt


def family_check_magic(m, lib, rng, cases, report, negatives):
    kinds = [(0x413, 1), (0x7f2b, 0), (0x413, 1), (0x7f2b, 0), (0x43b, 0)]
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = random_effect(rng, kind)
        objects = [random_object(rng) for _ in range(2)]
        e.owner = rng.choice([-1, 0, 1, 1])
        if e.owner >= 0 and rng.random() < 0.6:
            t = objects[e.owner]
            for k in range(2):
                e.position[k] = f32(t.position[k] + rng.choice([0.0, 50.0, -70.0, 99.0, 100.0, 101.0, -150.0]))
        case = Case(rng, objects, rand_values(rng), 0.0)
        raw, mask = effect_to_bytes(e, MOVE_DEFINED)
        record = am.Region('record', POOL, raw, mask)
        regions = [record, object_region(objects)]
        stubs = case.stubs(m)
        del stubs[CHECK_MAGIC]
        r = m.execute(CHECK_MAGIC, [POOL], regions, stubs)
        env = case.env(report_checks=0)
        before_lifetime = e.lifetime
        lib.mu_sfx_check_magic(ctypes.byref(e), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['record']
            mismatch = compare_effect(e, out, record.defined, MOVE_DEFINED)
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, case.c_calls)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = vc.ok(r) and mismatch is None
        hit = vc.ok(r) and struct.unpack('<i', r['regions']['record'][0x6c:0x70])[0] == 1 and before_lifetime != 1
        report.add('check_magic', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                          'stopped': r['stopped'], 'error': r['error']})
        report.cover('check_magic', 'hit' if hit else 'miss')
        if vc.ok(r) and e.owner >= 0:
            # negative control: a 3D distance test
            t = objects[e.owner]
            if t.live and t.visible:
                d3 = math.sqrt(sum((f32(e.position[k]) - t.position[k])**2 for k in range(3)))
                negatives['check_magic_3d'] += (d3 <= 100.0) != hit


CREATE_PARTICLE_CORE, MOVE_PARTICLES, RENDER_PARTICLES, RENDER_SPRITE = 0x015ae7b0, 0x01616c80, 0x0159123f, 0x0184c39c
PARTICLE_POOL, BITMAPS = 0x0a3a9adc, 0x0bdc5f00
SHARED_NEW, SHARED_GET, LIST_PUSH, SHARED_FREE = 0x01690a4a, 0x0169084c, 0x01691232, 0x01690754
LIST_NEXT, BITMAP_GET, BLEND_ADD, BLEND_ALPHA = 0x01690894, 0x00c97c2d, 0x0184aa2b, 0x0184a990
TIME_STEP = 0x01cf103c
BITMAP_RECORD = 0x28000000
PARTICLE_KINDS = [(0x7f3c, 0), (0x7f3c, 5), (0x7f2b, 0), (0x7f26, 0), (0x7f26, 1)]


def particle_stubs(case, m, extra=None):
    stubs = case.stubs(m)

    def noop(mm):
        return 0

    def noop4(mm):
        return 0, 4

    def get(mm):
        return PARTICLE, 0
    stubs.update({SHARED_NEW: noop, SHARED_GET: get, LIST_PUSH: noop4, SHARED_FREE: noop})
    stubs.update(extra or {})
    return stubs


def family_particle_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = PARTICLE_KINDS[n % len(PARTICLE_KINDS)]
        pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
        angle = [vc.rfloat(rng, 0.1, 360.0) for _ in range(3)]
        light = [vc.rfloat(rng, 0.1, 1.5) for _ in range(3)]
        scale = f32(rng.choice([1.0, 4.0, 6.0, 0.5, vc.rfloat(rng, 0.2, 8.0)]))
        arg8 = rng.randrange(-2**31, 2**31)
        case = Case(rng, [], rand_values(rng), 0.0)
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<9f', *pos, *angle, *light), writable=False)
        # a fresh allocation: defined bytes of unknown value
        record = am.defined_region('particle', PARTICLE, am.poison(PARTICLE_BYTES, 0x5d))
        regions = [inputs, record]
        r = m.execute(CREATE_PARTICLE_CORE, [kind[0], INPUTS, INPUTS+12, INPUTS+24, kind[1], bits(scale), 0, arg8],
                      regions, particle_stubs(case, m), ecx=PARTICLE_POOL, cleanup=0x20)
        p = Particle()
        F3 = ctypes.c_float*3
        env = case.env()
        supported = lib.mu_sfx_particle_create(ctypes.byref(p), kind[0], F3(*pos), F3(*angle), F3(*light), kind[1],
                                               scale, -1, arg8, ctypes.byref(env))
        names = {f[0] for f in PARTICLE_FIELDS}
        mismatch = None
        if vc.ok(r):
            out = r['regions']['particle']
            mismatch = compare_particle(p, out, record.defined, names)
            if mismatch is None and struct.unpack('<I', out[0x50:0x54])[0] != 0:
                mismatch = ('owner', out[0x50:0x54].hex())
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('particle_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                              'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('particle_create', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r) and kind == (0x7f3c, 0):
            # negative control: the trail ignores the scale argument (subtype 0)
            sc = struct.unpack('<f', r['regions']['particle'][0x18:0x1c])[0]
            negatives['particle_fire_scaled'] += not same(sc, f32(f32(p.scale*scale)))


def random_particle(rng, kind):
    p = Particle()
    p.live = rng.choice([1, 1, 1, 0, 2])
    p.type = p.tex_type = kind[0]
    p.subtype = kind[1]
    p.scale = f32(rng.choice([1.34, 1.0, 0.25, 0.21, 0.19, 2.0, 6.0, vc.rfloat(rng, 0.2, 6.0)]))
    p.lifetime = rng.choice([24, 23, 12, 2, 1, 0, -1, rng.randrange(-3, 30)])
    p.owner = -1
    p.rotation = vc.rfloat(rng, 0.1, 360.0)
    p.frame = rng.randrange(-3, 6)
    p.moving = rng.choice([1, 1, 0])
    p.gravity = f32(rng.choice([0.0, 0.004, 20.0, vc.rfloat(rng, 0.2, 1.0)]))
    p.time = vc.rfloat(rng, 0.1, 100.0)
    p.arg8 = 0
    for k in range(3):
        p.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        p.angle[k] = vc.rfloat(rng, 0.1, 360.0)
        p.light[k] = vc.rfloat(rng, 0.1, 1.5)
        p.velocity[k] = f32(rng.choice([0.0, -3.7, -50.0, vc.rfloat(rng, 0.2, 60.0)]))
        p.start[k] = vc.rfloat(rng, 0.1, 30000.0)
        p.start_angle[k] = vc.rfloat(rng, 0.1, 360.0)
    return p


PARTICLE_MOVE_DEFINED = {'live', 'type', 'tex_type', 'subtype', 'scale', 'position', 'angle', 'light', 'lifetime',
                         'owner', 'rotation', 'frame', 'moving', 'gravity', 'velocity', 'time'}
MOVE_FRAME = 0xc + 0x7038 + 8
RENDER_FRAME = 0xc + 0x1f1c + 8


def mid_frame(size):
    """Saved ESI / EDI where the prologue pushed them (the epilogue pops them)."""
    return (size, {-size+4: 0x3456789a, -size: 0x456789ab})


def family_particle_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = PARTICLE_KINDS[n % len(PARTICLE_KINDS)]
        p = random_particle(rng, kind)
        step = vc.rfloat(rng, 0.1, 2.0)
        case = Case(rng, [], rand_values(rng), 0.0)
        raw, mask = particle_to_bytes(p, PARTICLE_MOVE_DEFINED)
        record = am.Region('particle', PARTICLE, raw, mask)
        regions = [record, am.defined_region('time-step', TIME_STEP, struct.pack('<f', step), writable=False)]
        before = Particle.from_buffer_copy(p)
        head_removes = p.lifetime <= 0 or not p.live
        if head_removes:
            # the loop head erases the record (verified by its two tests in the C; nothing to run)
            moved = lib.mu_sfx_particle_move(ctypes.byref(p), step)
            report.add('particle_move', moved == 0, {'case': n, 'removed_at_head': True})
            report.cover('particle_move', 'removed')
            continue
        stubs = particle_stubs(case, m, {0x0168ee7d: jump_stub(0x0168eea4)})
        size, slots = mid_frame(MOVE_FRAME)
        slots[-0x38] = 7
        r = m.execute(0x01616f7c, [], regions, stubs, ecx=PARTICLE_POOL, frame=(size, slots))
        moved = lib.mu_sfx_particle_move(ctypes.byref(p), step)
        mismatch = None
        if vc.ok(r):
            mismatch = compare_particle(p, r['regions']['particle'], record.defined, PARTICLE_MOVE_DEFINED - {'owner'})
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = moved == 1 and vc.ok(r) and mismatch is None
        report.add('particle_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                            'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('particle_move', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r) and kind[0] == 0x7f3c:
            # negative control: the trail rises by the gravity without the factor 10
            z = struct.unpack('<f', r['regions']['particle'][0x28:0x30][:4])[0]
            g = f32(before.gravity + f32(0.004))
            negatives['particle_rise_no_10'] += not same(z, f32(f32(p.position[2] - f32(g*10.0)) + g))


def family_particle_render(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = PARTICLE_KINDS[n % len(PARTICLE_KINDS)]
        p = random_particle(rng, kind)
        p.live = 1
        mode = rng.choice([0, 0, 1, 2, 3])
        bitmap = BitmapInfo(f32(rng.choice([64.0, 128.0, 256.0, 32.0])), f32(rng.choice([64.0, 128.0, 32.0])),
                            rng.choice([3, 3, 4]))
        if rng.random() < 0.3:
            p.position[2] = f32(rng.choice([300.0, 350.0, 299.9, 350.1, 1e9]))
        case = Case(rng, [], [], 0.0)
        raw, mask = particle_to_bytes(p, PARTICLE_MOVE_DEFINED)
        record = am.Region('particle', PARTICLE, raw, mask)
        bm = am.Region('bitmap', BITMAP_RECORD, am.poison(0x220, 0x44), bytes(0x220))
        bm.define(BITMAP_RECORD+0x204, struct.pack('<ff', bitmap.width, bitmap.height))
        bm.define(BITMAP_RECORD+0x214, struct.pack('<b', bitmap.components))
        regions = [record, bm]
        calls = []

        def bitmap_get(mm):
            calls.append(('bitmap', mm.argument(0)))
            return BITMAP_RECORD, 4

        def blend_add(mm):
            calls.append(('blend', 3))
            return 0

        def blend_alpha(mm):
            calls.append(('blend', 0x990, mm.argument(0)))
            return 0

        def sprite(mm):
            a = [mm.argument(i) for i in range(11)]
            calls.append(('sprite', a[0], mm.floats(a[1], 3), from_bits(a[2]), from_bits(a[3]), mm.floats(a[4], 3),
                          from_bits(a[5]), from_bits(a[6]), from_bits(a[7]), from_bits(a[8]), from_bits(a[9]), a[10]))
            return 0
        stubs = particle_stubs(case, m, {0x015ae351: jump_stub(0x015ae363), 0x01591282: jump_stub(0x015ae363),
                                          BITMAP_GET: bitmap_get,
                                          BLEND_ADD: blend_add, BLEND_ALPHA: blend_alpha, RENDER_SPRITE: sprite})
        size, slots = mid_frame(RENDER_FRAME)
        r = m.execute(0x015912e9, [0x5500 | mode], regions, stubs, ecx=PARTICLE_POOL, frame=(size, slots), cleanup=4)
        sp = Sprite()
        count = lib.mu_sfx_particle_render(ctypes.byref(p), ctypes.byref(bitmap), mode, ctypes.byref(sp))
        mine = []
        if count:
            mine = [('bitmap', p.tex_type), ('blend', 3) if sp.additive else ('blend', 0x990, 0),
                    ('sprite', sp.bitmap, list(sp.position), sp.width, sp.height, list(sp.light), sp.rotation, sp.u,
                     sp.v, sp.uw, sp.vh, sp.axes)]
        mismatch = None
        if vc.ok(r):
            if len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine)):
                mismatch = ('calls', calls, mine)
        equal = vc.ok(r) and mismatch is None
        report.add('particle_render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode,
                                              'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                                              'checks': r['checks']})
        report.cover('particle_render', f'{kind[0]:#x}/{kind[1]}' + ('' if count else ' skipped'))
        if vc.ok(r) and count and kind[0] == 0x7f3c:
            # negative control: the full texture width for the 4-cell fire strip
            w = [c for c in calls if c[0] == 'sprite'][0][3]
            negatives['particle_fire_full_width'] += not same(w, f32(bitmap.width*p.scale))


CREATE_JOINT_CORE, MOVE_JOINT, RENDER_JOINTS = 0x0153b02c, 0x01556c26, 0x01589b56
JOINT_MANAGER_A, JOINT_MANAGER_COUNT, WALL_ATTRIBUTE, WALL_SCENE, HERO_POINTER = 0x01095a0a, 0x01095c69, 0x016d348d, 0x01ec8ee7, 0x0a39d754
BIND_TEXTURE, BLEND_SUB, BLEND_INV, DEPTH_OFF = 0x0184acf6, 0x0184aab7, 0x0184ab46, 0x0184a6da
JOINT_KINDS = [(0x7fd8, 1), (0x7fd3, 0), (0x7fd3, 0)]


def random_joint_args(rng, kind):
    pos = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
    target = [vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 30000.0), vc.rfloat(rng, 0.05, 600.0)]
    angle = [vc.rfloat(rng, 0.1, 360.0) for _ in range(3)]
    scale = f32(rng.choice([5.0, 80.0, 20.0, vc.rfloat(rng, 0.2, 100.0)]))
    return pos, target, angle, scale


def family_joint_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = JOINT_KINDS[n % len(JOINT_KINDS)]
        pos, tpos, angle, scale = random_joint_args(rng, kind)
        objects = [random_object(rng) for _ in range(2)]
        owner = rng.choice([-1, 0, 1])
        key, skill, byte10, word13, arg14 = (rng.randrange(0, 0x10000), rng.choice([0x7f5, 9, 0x123]),
                                              rng.randrange(0, 256), rng.randrange(0, 0x10000),
                                              rng.randrange(-2**31, 2**31))
        serial = rng.randrange(0, 256)
        # the record's previous contents: defined bytes of a former joint (its width is read)
        previous = bytearray(am.poison(JOINT_BYTES, rng.randrange(0, 0x80)))
        previous[0] = 0
        struct.pack_into('<f', previous, 0x14, f32(rng.choice([0.0, 5.0, 80.0, 20.0, vc.rfloat(rng, 0.2, 90.0)])))
        for k in range(600):
            struct.pack_into('<f', previous, 0x70+4*k, f32(rng.uniform(-1000.0, 1000.0)))
        record = am.defined_region('joint', JOINT_POOL, bytes(previous))
        case = Case(rng, objects, rand_values(rng), 0.0)
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<9f', *pos, *tpos, *angle), writable=False)
        hero = am.Region('hero-data', HERO_DATA, am.poison(0x3000, 0x13), bytes(0x3000))
        hero.define(HERO_DATA+0x2dec, bytes([serial]))
        regions = [record, inputs, object_region(objects), hero,
                   am.defined_region('hero-ptr', HERO_DATA_PTR, struct.pack('<I', HERO_DATA), writable=False)]
        stubs = case.stubs(m)
        del stubs[CREATE_JOINT]

        def manager(mm):
            return 0, 12
        stubs[JOINT_MANAGER_A] = manager
        r = m.execute(CREATE_JOINT_CORE, [kind[0], INPUTS, INPUTS+12, INPUTS+24, kind[1], object_address(owner),
                                          bits(scale), key, skill, byte10, 0xffffffff, 0, word13, arg14],
                      regions, stubs)
        j = Joint()
        joint_from_bytes(previous, j)
        F3 = ctypes.c_float*3
        env = case.env(serial=serial)
        supported = lib.mu_sfx_joint_create(ctypes.byref(j), kind[0], F3(*pos), F3(*tpos), F3(*angle), kind[1],
                                            owner, scale, key, skill, byte10, word13, arg14, ctypes.byref(env))
        names = {f[0] for f in JOINT_FIELDS}
        mismatch = None
        if vc.ok(r):
            out = r['regions']['joint']
            mismatch = compare_joint(j, out, record.defined, names)
            if mismatch is None and struct.unpack('<I', out[0x54:0x58])[0] != object_address(owner):
                mismatch = ('target', out[0x54:0x58].hex(), owner)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('joint_create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                           'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('joint_create', f'{kind[0]:#x}/{kind[1]}')
        if vc.ok(r):
            # negative control: the first tail from the new width
            w_old = struct.unpack('<f', bytes(previous[0x14:0x18]))[0]
            negatives['joint_first_tail_new_width'] += not same(w_old, scale)


def random_joint(rng, kind, objects):
    j = Joint()
    raw = bytearray(am.poison(JOINT_BYTES, rng.randrange(0, 0x80)))
    joint_from_bytes(raw, j)
    j.live = 1
    j.type = j.tex_type = kind[0]
    j.subtype = kind[1]
    j.render_type = 1 if kind[0] == 0x7fd8 else 3
    j.faces = 3
    j.scale = f32(rng.choice([5.0, 80.0, 20.0, 80.0, vc.rfloat(rng, 0.2, 100.0)]))
    for k in range(3):
        j.position[k] = vc.rfloat(rng, 0.05, 30000.0) if k < 2 else vc.rfloat(rng, 0.05, 600.0)
        j.start[k] = vc.rfloat(rng, 0.05, 30000.0)
        j.angle[k] = vc.rfloat(rng, 0.1, 360.0)
        j.light[k] = vc.rfloat(rng, 0.1, 5.0)
        j.target_position[k] = vc.rfloat(rng, 0.05, 30000.0)
        j.jitter[k] = vc.rfloat(rng, 0.1, 20.0)
    j.target = rng.choice([-1, 0, 1, 1])
    j.field_64 = rng.choice([0, 1, 2])
    j.max_tails = 2 if kind[0] == 0x7fd8 else 6
    j.num_tails = rng.randrange(0, j.max_tails)
    for k in range(600):
        j.tails[k] = f32(rng.uniform(-3000.0, 3000.0))
    j.lifetime = rng.choice([12, 11, 2, 1, 0, 49, 45, 30, 15, rng.randrange(-2, 50)])
    j.reached = rng.choice([0, 1])
    j.field_a24 = j.field_a25 = 0   # as CreateJoint leaves them for these kinds
    j.velocity = f32(rng.choice([0.0, 4.0, 70.0, vc.rfloat(rng, 0.2, 80.0)]))
    j.skill = rng.choice([0x7f5, 9, 0x123])
    j.tail_update = rng.choice([1, 1, 0])
    j.time = vc.rfloat(rng, 0.1, 50.0)
    j.brightness = f32(rng.choice([1.0, 0.5]))
    j.moving = 1   # CreateJoint sets it and these kinds never clear it (clear, the client would use an uninitialised matrix)
    return j


JOINT_MOVE_DEFINED = {f[0] for f in JOINT_FIELDS} | {'target'}


def family_joint_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = JOINT_KINDS[n % len(JOINT_KINDS)]
        objects = [random_object(rng) for _ in range(2)]
        j = random_joint(rng, kind, objects)
        step = vc.rfloat(rng, 0.1, 2.0)
        wall_scene = rng.choice([0, 1])
        wall = rng.choice([0, 0x100, 0x104, 4])
        hero_obj = rng.choice([-1, 0, 1])
        case = Case(rng, objects, rand_values(rng), vc.rfloat(rng, 0.1, 400.0))
        raw, mask = joint_to_bytes(j, JOINT_MOVE_DEFINED)
        record = am.Region('joint', JOINT_POOL, raw, mask)
        hero_char = (object_address(hero_obj) - 0x3254) & 0xffffffff if hero_obj >= 0 else 0x5000000
        regions = [record, object_region(objects),
                   am.defined_region('time-step', TIME_STEP, struct.pack('<f', step), writable=False),
                   am.defined_region('wall-scene', WALL_SCENE, bytes([wall_scene]), writable=False),
                   am.defined_region('hero', HERO_POINTER, struct.pack('<I', hero_char), writable=False)]
        stubs = case.stubs(m)

        def wall_stub(mm):
            case.client_calls.append(('wall', mm.float_argument(0), mm.float_argument(1)))
            return wall, 0
        stubs[WALL_ATTRIBUTE] = wall_stub
        before = Joint.from_buffer_copy(j)
        r = m.execute(MOVE_JOINT, [JOINT_POOL, 0], regions, stubs)
        env = case.env()
        is_hero = 1 if (hero_obj >= 0 and hero_obj == j.target) else 0
        # the C side reports the wall test as a call when the client makes it
        if j.type == 0x7fd3 and j.scale == 80.0 and wall_scene:
            case.c_calls.append(('wall', None, None))
        supported = lib.mu_sfx_joint_move(ctypes.byref(j), ctypes.byref(env), step, wall_scene, wall, is_hero)
        mismatch = None
        if vc.ok(r):
            out = r['regions']['joint']
            mismatch = compare_joint(j, out, record.defined, JOINT_MOVE_DEFINED - {'target'})
            if mismatch is None:
                mismatch = compare_calls(case.client_calls, sorted_calls(case.c_calls, case.client_calls))
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        equal = supported and vc.ok(r) and mismatch is None
        report.add('joint_move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                         'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('joint_move', f'{kind[0]:#x}/{kind[1]}' + (' wide' if before.scale == 80.0 else ''))
        if vc.ok(r) and before.moving and before.velocity != 0.0:
            # negative control: the head moves along +y
            y = struct.unpack('<f', r['regions']['joint'][0x1c:0x20])[0]
            negatives['joint_forward_plus_y'] += not same(y, f32(before.position[1] + before.velocity))


def sorted_calls(mine, client):
    """The wall test is reported by the C at the point of the first call; move it to the client's place."""
    if not any(c[0] == 'wall' for c in mine):
        return mine
    rest = [c for c in mine if c[0] != 'wall']
    index = next((i for i, c in enumerate(client) if c[0] == 'wall'), None)
    if index is None:
        return rest + [('wall', None, None)]
    return rest[:index] + [('wall', None, None)] + rest[index:]


def family_joint_render(m, lib, rng, cases, report, negatives):
    pool_bytes = 500*JOINT_BYTES
    empty = bytearray(am.poison(pool_bytes, 0x61))
    empty_mask = bytearray(pool_bytes)
    for i in range(500):
        base = i*JOINT_BYTES
        empty[base] = 0
        struct.pack_into('<ii', empty, base+4, 0, 0)
        empty_mask[base:base+0x10] = b'\1'*0x10
    for n in range(cases):
        kind = JOINT_KINDS[n % len(JOINT_KINDS)]
        objects = [random_object(rng) for _ in range(2)]
        j = random_joint(rng, kind, objects)
        j.faces = rng.choice([3, 3, 1, 2, 0])
        mode = rng.choice([0, 0, 1, 2])
        raw, mask = joint_to_bytes(j, JOINT_MOVE_DEFINED)
        pool = bytearray(empty)
        pmask = bytearray(empty_mask)
        pool[0:JOINT_BYTES] = raw
        pmask[0:JOINT_BYTES] = mask
        region = am.Region('joints', JOINT_POOL, bytes(pool), bytes(pmask))
        world_time = am.defined_region('world-time', 0x06fce370, struct.pack('<f', vc.rfloat(rng, 0.1, 1e6)),
                                       writable=False)
        calls = []

        def rec(name, cleanup=0):
            def stub(mm):
                calls.append((name,))
                return 0, cleanup
            return stub

        def bind(mm):
            calls.append(('bind', mm.argument(0)))
            return 0

        def blend_alpha(mm):
            calls.append(('blend', 2, mm.argument(0)))
            return 0

        def count(mm):
            return 0, 0
        stubs = {JOINT_MANAGER_COUNT: count, BIND_TEXTURE: bind, BLEND_ADD: rec('blend1'), BLEND_ALPHA: blend_alpha,
                 BLEND_SUB: rec('blend3'), BLEND_INV: rec('blend4'), DEPTH_OFF: rec('depth_off')}
        for slot, (name, argc) in GL_IMPORTS.items():
            def gl(mm, name=name, argc=argc):
                a = [mm.argument(i) for i in range(argc)]
                if name == 'glVertex3fv':
                    calls.append((name, mm.floats(a[0], 3)))
                elif name == 'glColor3fv':
                    calls.append((name, mm.floats(a[0], 3)))
                elif name in ('glColor3f', 'glColor4f', 'glTexCoord2f'):
                    calls.append((name, [from_bits(x) for x in a]))
                else:
                    calls.append((name, a))
                return 0, 4*argc
            stubs[m.gl_target[slot]] = gl
        r = m.execute(RENDER_JOINTS, [0x5500 | mode], [region, world_time], stubs)
        color = (ctypes.c_float*3)()
        rt = ctypes.c_int32()
        quads = (JointQuad*128)()
        count_q = lib.mu_sfx_joint_render(ctypes.byref(j), mode, color, ctypes.byref(rt), quads, 128)
        mine = []
        if count_q or (j.live and j.num_tails > 0 and j.faces and not (mode == 1 and j.field_64 == 2)
                       and not (mode == 2 and j.field_64 == 1)):
            mine.append({1: ('blend1',), 2: ('blend', 2, 1), 3: ('blend3',), 4: ('blend4',)}.get(rt.value, ('none',)))
            mine.append(('glColor3f', list(color)))
            mine.append(('bind', j.tex_type))
            for q in quads[:count_q]:
                mine.append(('glBegin', [7]))
                for k in range(4):
                    mine.append(('glTexCoord2f', [q.uv[2*k], q.uv[2*k+1]]))
                    mine.append(('glVertex3fv', list(q.position[3*k:3*k+3])))
                mine.append(('glEnd', []))
        mismatch = None
        if vc.ok(r):
            if len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine)):
                diff = next(((i, a, b) for i, (a, b) in enumerate(zip(calls, mine)) if not vc._same_call(a, b)),
                            ('count', len(calls), len(mine)))
                mismatch = ('calls', diff, calls[:4], mine[:4])
        equal = vc.ok(r) and mismatch is None
        report.add('joint_render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode,
                                           'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                                           'checks': r['checks']})
        report.cover('joint_render', f'{kind[0]:#x}/{kind[1]} quads {min(count_q, 9)}')
        if vc.ok(r) and count_q:
            # negative control: the texture runs 0..1 over the drawn tails instead of the full length
            u = [c for c in calls if c[0] == 'glTexCoord2f'][0][1][0]
            negatives['joint_uv_drawn_tails'] += not same(u, f32(1.0))


SET_PLAYER_SHOCK, SET_PLAYER_DIE, SET_PLAYER_ATTACK = 0x0138f92f, 0x01393a61, 0x01392bde
CHAR = 0x24000000
CHAR_OBJ = CHAR + 0x3254


def random_player_state(rng):
    st = PlayerState()
    st.class_byte = rng.choice([0, 1, 2, 3, 4, 13, 0x14, 0x24, rng.randrange(0, 256)])
    st.state_59, st.state_5a, st.state_72 = (rng.random() < 0.15, rng.random() < 0.15, rng.random() < 0.15)
    st.predicate = rng.random() < 0.15
    st.class_check = rng.random() < 0.4
    st.transform = rng.choice([0, 0, 0, 0x1a25, 0x123])
    st.field_3324 = f32(rng.choice([0.0, 0.0, 0.0, -0.0, 1.0, float('nan')]))
    st.world_voice = rng.random() < 0.15
    return st


def player_stubs(st, rands, record, rand_index):
    def state(mm):
        a, b = mm.argument(0), mm.argument(1)
        value = {(1, 0x59): st.state_59, (0, 0x5a): st.state_5a, (1, 0x72): st.state_72}.get((a, b), 0)
        record.append(('state', a, b))
        return 0xbe00 | value, 8

    def rand(mm):
        v = rands[rand_index[0]] if rand_index[0] < len(rands) else 0
        rand_index[0] += 1
        return v

    def recorder(name, value=0, cleanup=0, argc=0):
        def stub(mm):
            record.append((name,) + tuple(mm.argument(i) for i in range(argc)))
            return value, cleanup
        return stub

    def set_action(mm):
        record.append(('set_action', mm.argument(1)))
        return 0

    def sound(mm):
        record.append(('sound', mm.argument(0)))
        return 0
    return {0x0129ddd4: state, 0x01989721: rand, 0x012affa4: set_action, 0x00a6ac96: sound,
            0x013a084d: recorder('tail_13a084d'), 0x0139f3db: lambda mm: 0xaa00 | st.predicate,
            0x00b99205: lambda mm: (1 if st.class_check else 0), 0x0129dcda: lambda mm: 0xab0000 | st.transform,
            0x009dacb8: lambda mm: 0xab00 | st.world_voice}


def player_regions(st, action, world):
    c = am.undefined_region('character', CHAR, 0x3400)
    c.define(CHAR+0x12, bytes([st.class_byte]))
    c.define(CHAR+0x23, bytes([0]))
    c.define(CHAR+0x32b0, struct.pack('<i', 0xa91))
    c.define(CHAR+0x3324, struct.pack('<f', st.field_3324))
    c.define(CHAR+0x38, bytes([7]))
    c.define(CHAR_OBJ+0x2a, struct.pack('<H', action))
    c.define(CHAR_OBJ+0x5c, struct.pack('<i', 0xa91))
    return [c, am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
            am.defined_region('hero', HERO_POINTER, struct.pack('<I', 0x05000000), writable=False)]


def family_player_voice(m, lib, rng, cases, report, negatives):
    """SetPlayerShock / SetPlayerDie (Player branches) and SetPlayerAttack's sound tail."""
    kinds = ['shock', 'die', 'attack']
    item_groups = [-1, -1, 0xae6, 0xaf0, 0x10e6, 0x10e7, 0x12e6, 0x12f3, 0x12f4, 0x12f5, 0x14e6, 0x2000]
    for n in range(cases):
        kind = kinds[n % 3]
        st = random_player_state(rng)
        rands = [rng.choice([0, 1, 2, 3, 4, 5, 0x7fff, rng.randrange(0, 0x8000)]) for _ in range(8)]
        record, rand_index = [], [0]
        world = rng.choice([0, 0, 0, 0x49, 7])
        stubs = player_stubs(st, rands, record, rand_index)
        action_now = rng.choice([0, 0x71, 0x134, 0x8f])
        if kind == 'shock':
            action_now = rng.choice([0, 0x71, 0x134])   # not one of the eleven actions that block the reaction
            stubs[0x009c104e] = lambda mm: 0x0a000000
            stubs[0x0106bdb7] = lambda mm: (0, 4)   # not riding
            r = m.execute(SET_PLAYER_SHOCK, [CHAR, rng.choice([1, 50, 999]), rng.choice([0, 1, 3])],
                          player_regions(st, action_now, world), stubs)
            act = ctypes.c_int32()
            snd = ctypes.c_int32()
            used = lib.mu_player_shock(ctypes.byref(st), (ctypes.c_int32*8)(*rands), 8, ctypes.byref(act),
                                       ctypes.byref(snd))
            mine = [('set_action', act.value)] + ([('sound', snd.value)] if snd.value >= 0 else [])
        elif kind == 'die':
            st.predicate = 0   # the skeleton form's death (0x435 / 0x436 effects) is not reconstructed
            for addr, cleanup in ((0x00a0361c, 4), (0x0095c50b, 4), (0x00a06d72, 0), (0x0095f144, 0),
                                  (0x00c71772, 0), (0x0095eb91, 0), (0x0095f6db, 0), (0x009a176b, 4),
                                  (0x009a19ae, 4), (0x009a1a3c, 0)):
                stubs[addr] = (lambda mm, k=cleanup: (0x0b000000, k))
            stubs[0x009a1a51] = lambda mm: 0   # no party window to update
            r = m.execute(SET_PLAYER_DIE, [CHAR], player_regions(st, action_now, world), stubs)
            act = ctypes.c_int32()
            snds = (ctypes.c_int32*2)()
            used = lib.mu_player_die(ctypes.byref(st), (ctypes.c_int32*8)(*rands), 8, ctypes.byref(act), snds)
            mine = ([('set_action', act.value)] if not st.predicate else []) + \
                [('sound', x) for x in snds if x >= 0]
        else:
            st.predicate = 0   # the skeleton form's attack sounds (the model's sound table) are not reconstructed
            weapon = [rng.choice(item_groups), rng.choice(item_groups)]
            bow = rng.choice([0, 0, 0, 1, 2])
            inp = vc.AttackInput(object_type=0xa91, class_byte=st.class_byte, safe_zone=0, counter=rng.randrange(0, 256),
                                 wing=-1, two_handed=0, bow_kind=bow, dual=0, state_72=0)
            inp.weapon[0], inp.weapon[1] = weapon
            inp.attr_present[0] = inp.attr_present[1] = 0
            inp.rand_values = (ctypes.c_int32*8)(*rands)
            inp.rand_count = 8
            res = vc.AttackResult()
            lib.mu_player_attack_action(ctypes.byref(inp), ctypes.byref(res))
            regions = player_regions(st, action_now, world)
            regions[0].define(CHAR+4, bytes([0]))
            regions[0].define(CHAR+0x28, bytes([inp.counter]))
            regions[0].define(CHAR+0x19ac, struct.pack('<h', weapon[0]))
            regions[0].define(CHAR+0x19ac+0x3fc, struct.pack('<h', weapon[1]))
            regions[0].define(CHAR+0x21a4, struct.pack('<h', -1))
            stubs.update({0x00cd4ea8: lambda mm: 0x5f000001, 0x00cd5d29: lambda mm: 0, 0x0138d9cf: lambda mm: 0,
                          0x01392afd: lambda mm: 0, 0x0139d8f8: lambda mm: bow, 0x0139d9ed: lambda mm: 0xde00,
                          0x00db747f: lambda mm: 0})
            stubs[0x0129ddd4] = lambda mm: (0xbe00, 8)
            r = m.execute(SET_PLAYER_ATTACK, [CHAR], regions, stubs)
            snd = ctypes.c_int32()
            rest = rands[res.rand_used:]
            used_sound = lib.mu_player_attack_sound(ctypes.byref(st), bow, weapon[0], weapon[1], world,
                                                    (ctypes.c_int32*8)(*(rest + [0]*(8-len(rest)))), len(rest),
                                                    ctypes.byref(snd))
            used = res.rand_used + used_sound
            mine = ([('set_action', res.action)] if res.action >= 0 else []) + \
                ([('sound', snd.value)] if snd.value >= 0 else [])
        client = [x for x in record if x[0] in ('set_action', 'sound')]
        equal = vc.ok(r) and client == mine and rand_index[0] == used
        if equal and kind == 'die':
            # the sound block marks itself done: c + 0x3324 = 0.001
            after = struct.unpack('<f', r['regions']['character'][0x3324:0x3328])[0]
            expected = f32(0.001) if st.field_3324 == 0.0 else st.field_3324
            equal = same(after, expected)
        report.add('player_voice', equal, {'case': n, 'kind': kind, 'client': client, 'c': mine,
                                           'rand': [rand_index[0], used], 'stopped': r['stopped'],
                                           'error': r['error'], 'checks': r['checks']})
        report.cover('player_voice', kind + ' ' + ' '.join(hex(x[1]) for x in client))
        if vc.ok(r) and kind == 'shock' and client and not st.state_59 and not st.state_5a and not st.state_72:
            # negative control: the monster's hit action 5 for the hero
            negatives['player_shock_action_5'] += client[0] != ('set_action', 5)


class EffectDecal(ctypes.Structure):
    _fields_ = [('texture', ctypes.c_int32), ('size', ctypes.c_float), ('light', ctypes.c_float*3),
                ('rotation', ctypes.c_float), ('flat', ctypes.c_int32)]


def family_effect_decal(m, lib, rng, cases, report, negatives):
    lib.mu_sfx_effect_decal.argtypes = [ctypes.POINTER(Effect), ctypes.c_int32, ctypes.POINTER(EffectDecal)]
    kinds = [(0x6f3, 0), (0x6f3, 1), (0x6f3, 2), (0x8438, 0)] + [(0x4ad, s) for s in range(1, 6)] + [(0x8012, 1)]
    for n in range(cases):
        kind = kinds[n % len(kinds)]
        e = random_effect(rng, kind)
        world = rng.choice([0, 10, 0x84, 0x18, 0x1d, 0x24, 0x1e])
        raw, mask = effect_to_bytes(e, MOVE_DEFINED)
        regions = [am.Region('record', POOL, raw, mask),
                   am.defined_region('world', WORLD, struct.pack('<i', world), writable=False)]
        calls = []
        def decal(mm):
            a = [mm.argument(i) for i in range(11)]
            calls.append(('decal', a[0], from_bits(a[1]), from_bits(a[2]), from_bits(a[3]), from_bits(a[4]),
                          mm.floats(a[5], 3), from_bits(a[6]), from_bits(a[7]), from_bits(a[8]), a[9], a[10]))
            return 0
        def flat(mm):
            a = [mm.argument(i) for i in range(9)]
            calls.append(('flat', a[0], from_bits(a[1]), from_bits(a[2]), from_bits(a[3]), from_bits(a[4]),
                          mm.floats(a[5], 3), from_bits(a[6]), from_bits(a[7]), from_bits(a[8]), 0, 0))
            return 0
        stubs = {0x016cdd5f: decal, 0x00deec1f: flat, 0x0184aa2b: lambda mm: 0,
                 0x0184a7f3: lambda mm: 0, 0x0184a763: lambda mm: 0, 0x0184a743: lambda mm: 0,
                 0x0095eda9: lambda mm: 0, 0x015324fc: jump_stub(0x01532501),
                 0x01515993: jump_stub(0x0151818b)}
        if kind[0] == 0x8012:
            start, size, cleanup = 0x01514ded, 0x370, 0
            slots = {-size: 0x3456789a, -0x10: POOL}
        else:
            start = {0x6f3: 0x01527c4e, 0x8438: 0x0152d6a6, 0x4ad: 0x0151a5c7}[kind[0]]
            size, cleanup = 0x1c04, 4
            slots = {-size: 0x456789ab, -size+4: 0x3456789a, -0x10: POOL}
        r = m.execute(start, [0] if cleanup else [], regions, stubs, frame=(size, slots), cleanup=cleanup)
        out = EffectDecal()
        supported = lib.mu_sfx_effect_decal(ctypes.byref(e), world, ctypes.byref(out))
        mine = [('flat' if out.flat else 'decal', out.texture, e.position[0], e.position[1], out.size, out.size,
                 list(out.light), out.rotation, 1.0, 0.0 if out.flat else 5.0, 0 if out.flat else 1, 0)]
        equal = supported == 1 and vc.ok(r) and len(calls) == 1 and vc._same_call(calls[0], mine[0])
        report.add('effect_decal', equal, {'case': n, 'kind': kind, 'world': world, 'client': calls, 'c': mine,
                                         'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('effect_decal', f'{kind[0]:#x}/{kind[1]} ' + ('flat' if out.flat else 'terrain'))
        if equal and kind[0] in (0x6f3, 0x8438):
            negatives['decal_no_alpha'] += any(not same(a, b) for a, b in zip(e.light, out.light))
        if equal and kind[0] == 0x8012 and out.flat:
            negatives['decal_flat_as_terrain'] += 1


FAMILIES = [('effect_create', family_effect_create), ('effect_decal', family_effect_decal), ('effect_move', family_effect_move),
            ('check_magic', family_check_magic), ('particle_create', family_particle_create),
            ('particle_move', family_particle_move), ('particle_render', family_particle_render),
            ('joint_create', family_joint_create), ('joint_move', family_joint_move),
            ('joint_render', family_joint_render), ('player_voice', family_player_voice)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
    parser.add_argument('--data', default=str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--only', action='append')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = FxMachine(text, data)
    bodies = {name: {'start': hex(a), 'end': hex(b),
                     'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    report = vc.Report()
    negatives = {k: 0 for k in ['create_arrow_speed_60', 'create_energy_no_lift', 'move_decrement_first',
                                'move_unrotated', 'check_magic_3d', 'particle_fire_scaled', 'particle_rise_no_10',
                                'particle_fire_full_width', 'joint_first_tail_new_width', 'joint_forward_plus_y',
                                'joint_uv_drawn_tails', 'player_shock_action_5',
                                'create_shockwave_over_20', 'move_lightning_fade_02', 'decal_no_alpha', 'decal_flat_as_terrain', 'claw_no_shrink', 'rune_no_growth', 'tail_wrong_particle']}
    timing = {}
    for name, family in FAMILIES:
        if args.only and name not in args.only:
            continue
        rng = random.Random(f'{args.seed}-{name}')
        start = time.time()
        family(m, lib, rng, args.cases, report, negatives)
        timing[name] = round(time.time()-start, 2)
    all_equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result = {'coverage': report.coverage, 'nan_pairs_equal': vc.NAN_COUNT[0], 'text_sha256': am.TEXT_SHA256,
              'data_sha256': am.DATA_SHA256, 'bodies': bodies, 'families': report.families,
              'negative_controls': negatives, 'seconds': timing, 'all_equal': all_equal}
    summary = {k: f"{v['equal']}/{v['cases']}" for k, v in report.families.items()}
    print(json.dumps({'summary': summary, 'negative_controls': negatives, 'coverage': report.coverage,
                      'seconds': timing, 'all_equal': all_equal}, indent=1))
    for k, v in report.families.items():
        if v['first_failures']:
            print(k, json.dumps(v['first_failures'][:3], default=str))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, default=str))
    return 0 if all_equal else 1


if __name__ == '__main__':
    sys.exit(main())
