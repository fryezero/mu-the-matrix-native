#!/usr/bin/env python3
"""Compare reconstructed/particles with the client's instructions (NATIVE-PARTICLE-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case),
with the x87 return helpers of scripts/validate_combat.py. The authored C
(libclient_particles) runs on the same inputs.

Families (client routine -> authored function):

* create        CreateParticle core 0x015ae7b0 -> mu_pt_create_record, every
                supported kind, with and without an owner. The shared-pointer
                helpers (make 0x01690a4a, get 0x0169084c, push_back 0x01691232,
                release 0x01690754) are stubs over one record; rand(),
                RequestTerrainHeight and the sin/cos wrappers (host libm) are
                recording stubs; AngleMatrix, VectorRotate and the vector
                helpers run as client code.
* wrapper       CreateParticle 0x0168fafd -> mu_pt_wrapper_keeps (world 0x8b
                drop rule, the filter 0x010954d4 as client code; the core is a
                recording stub).
* move          MoveParticles' record body 0x01616f7c..0x0168ee7d (entered
                mid-routine with its frame) -> mu_pt_move_record.
* wind          MoveParticles' wind block 0x01616c80..0x01616ec9 ->
                mu_pt_wind_step.
* render        RenderParticles' record body 0x015912e9..0x015ae351 ->
                mu_pt_render_record (blend wrappers, bitmap getter and
                RenderSprite are recording stubs).
* sprite        RenderSprite 0x0184c39c -> mu_pt_render_sprite: the GL stream
                (BindTexture and the bitmap getter are stubs; VectorTransform,
                AngleMatrix, VectorRotate and the texcoord setter run as client
                code; GL imports are recording stubs).
* sprite_create CreateSprite core 0x01692508 over the 1000 records ->
                mu_pt_sprite_create (SetLive as client code).
* sprite_render RenderSprites 0x0169270e(mode) with the per-sprite draw
                0x01692931 as client code -> mu_pt_sprites_render (blend
                wrappers, bitmap getter, RenderSprite and the kill cleanup
                0x009b0451 are recording stubs).
* shadow        RenderBodyShadow 0x012bc07a -> mu_pt_render_body_shadow on a
                synthetic posed model (state wrappers and RequestTerrainHeight
                are recording stubs; glPushMatrix/glPopMatrix wrappers and the
                world predicates run as client code).
* bone          TransformPosition 0x012b6ef1 -> mu_pt_transform_position.
* bone_lookup   the bone-matrix lookup 0x0129f18a by name -> mu_pt_find_bone
                (the client's std::string constructor 0x0094997e builds the
                name, its compare runs as client code; the model getter is a
                stub).
* visual        RenderObjectVisual 0x017f9758 in world 0 and the Tormenta
                handler slot 0x34 0x00e4ef4b -> mu_pt_object_visual (model
                getter, bone lookup, TransformPosition, CreateParticle,
                CreateSprite, CreateJoint, CreateEffect are recording stubs;
                the std::string helpers and the sheet constructor run as client
                code).

Every case compares the record fields the C models (bit for bit; any two NaNs
are equal, as in validate_combat.py), the calls in client order with the values
the client passes, and the number of rand() calls. Negative controls (a
planted mistake, emulated in Python on the C result) must disagree.
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
import pins  # noqa: E402
import actor_machine as am  # noqa: E402
import validate_combat as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

f32, bits, from_bits, same = vc.f32, vc.bits, vc.from_bits, vc.same

CREATE_WRAPPER, CREATE_CORE, MOVE_PARTICLES, RENDER_PARTICLES = 0x0168fafd, 0x015ae7b0, 0x01616c80, 0x0159123f
RENDER_SPRITE, CREATE_SPRITE_CORE, RENDER_SPRITES, SHADOW = 0x0184c39c, 0x01692508, 0x0169270e, 0x012bc07a
TRANSFORM_POSITION, BONE_MATRIX, VISUAL, TORMENTA_VISUAL = 0x012b6ef1, 0x0129f18a, 0x017f9758, 0x00e4ef4b
SHARED_NEW, SHARED_GET, LIST_PUSH, SHARED_FREE, LIST_NEXT = 0x01690a4a, 0x0169084c, 0x01691232, 0x01690754, 0x01690894
RAND, TERRAIN, SINE, COSINE = 0x01989721, 0x016cc9e2, 0x009681bd, 0x009fa223
BITMAP_GET, BIND = 0x00c97c2d, 0x0184acf6
STATE_ADD, STATE_ALPHA, STATE_SUB, STATE_INV, STATE_FOG = 0x0184aa2b, 0x0184a990, 0x0184aab7, 0x0184ab46, 0x0184a7f3
STATE_6B7, STATE_6DA, STATE_UNTEX, STATE_DEPTH_OFF, STATE_DEPTH_ON = 0x0184a6b7, 0x0184a6da, 0x0184a783, 0x0184a763, \
    0x0184a743
KILL_CLEANUP = 0x009b0451
MODEL_CONTAINER, MODEL_GET = 0x00966cc4, 0x00eaa8cf
CREATE_PARTICLE, CREATE_SPRITE, CREATE_JOINT, CREATE_EFFECT = 0x0168fafd, 0x01692eb7, 0x0153b02c, 0x013c0eaa
WORLD, TIME, DT, DIVISOR = 0x01cf15fc, 0x06fce370, 0x01cf103c, 0x0a39d768
SCENE_FLAG = 0x01d1df70   # SceneFlag (read through 0x009b0bc1 by WATERFALL2, NATIVE-CHARSEL-002)
CAMERA_MATRIX = 0x0bdc5918
POOL, SPRITES, BITMAPS = 0x0a3a9adc, 0x0a3da070, 0x0bdc5f00
VERTICES = 0x078978a0
GL_SLOTS = {'glBegin': (0x1a7c750, 4), 'glEnd': (0x1a7c760, 0), 'glColor3fv': (0x1a7c770, 4),
            'glColor4f': (0x1a7c754, 16), 'glTexCoord2f': (0x1a7c774, 8), 'glVertex3fv': (0x1a7c778, 4),
            'glPushMatrix': (0x1a7c718, 0), 'glPopMatrix': (0x1a7c72c, 0)}

BODIES = {
    'create_particle_wrapper': (0x0168fafd, 0x0168fbae), 'create_particle_core': (0x015ae7b0, 0x01615f39),
    'move_particles': (0x01616c80, 0x0168eeb2), 'render_particles': (0x0159123f, 0x015ae373),
    'render_sprite': (0x0184c39c, 0x0184ca6b), 'create_sprite': (0x01692508, 0x0169270e),
    'render_sprites': (0x0169270e, 0x01692853), 'sprite_draw': (0x01692931, 0x01692e29),
    'body_shadow': (0x012bc07a, 0x012bc5ab), 'transform_position': (0x012b6ef1, 0x012b7019),
    'bone_matrix': (0x0129f18a, 0x0129f24f), 'object_visual': (0x017f9758, 0x017fccce),
    'tormenta_visual': (0x00e4ef4b, 0x00e4f952),
}

INPUTS = 0x21000000
OBJECTS = 0x22000000      # owner objects, 0x400 apart
PARTICLE = 0x27000000
PARTICLE_BYTES = 0xc0
BITMAP_RECORD = 0x28000000
MODEL = 0x29000000
MESHES = 0x29100000
TRIANGLES = 0x29200000
BONE_OBJECT = 0x29300000
MATRIX = 0x29400000

KINDS = [(0x7ef7, 1)] + [(0x7f3c, s) for s in (0, 1, 2, 3, 4, 5, 6, 17)] + [(0x7f5a, 0), (0x7f5a, 2), (0x7f5a, 3), (0x7f25, 0), (0x771c, 0), (0x771d, 0),
                                                            (0x7f2b, 0), (0x7f26, 0), (0x7f26, 1),
                                                            (0x7f89, 0x14), (0x801a, 2),   # NATIVE-JOINT-001: login mist/spray
                                                            (0x7f66, 0), (0x7f66, 1),      # Noria's Shiny01
                                                            # NATIVE-CHARSEL-002: the character-select scene
                                                            (0x801b, 2), (0x801c, 0xe), (0x8017, 0), (0x8022, 5),
                                                            # NATIVE-HELPERS-002: the helpers' kinds
                                                            (0x7f25, 1), (0x7f5b, 0), (0x7f5e, 0), (0x7fcd, 0), (0x7f26, 0xf), (0x831d, 6), (0x83b3, 6),
                                                            (0x8086, 0x13), (0x8086, 0x18), (0x7f26, 0x2a), (0x7f5a, 0x7f), (0x7f5a, 0x75)]
BITMAP_RECORD_GET = 0x00ebbec8   # the bitmap record by index (this = 0x0bdc5f00), smoke02's height (NATIVE-HELPERS-002)
STATE_BLEND = 0x0184abd5         # (SRC_ALPHA, ONE_MINUS_SRC_ALPHA), smoke02's render (NATIVE-HELPERS-002)


def object_address(index):
    return 0 if index < 0 else OBJECTS + 0x400*index


# --------------------------------------------------------------------------
# Library.

F3 = ctypes.c_float*3
RAND_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
OWNER_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float))
BITMAP_HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_int32)


class Particle(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('type', ctypes.c_int32), ('tex_type', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('scale', ctypes.c_float), ('position', F3), ('angle', F3),
                ('light', F3), ('alpha', ctypes.c_float), ('lifetime', ctypes.c_int32), ('owner', ctypes.c_int32),
                ('owner_position', F3), ('rotation', ctypes.c_float), ('frame', ctypes.c_int32),
                ('moving', ctypes.c_uint8), ('gravity', ctypes.c_float), ('velocity', F3), ('field_7c', ctypes.c_float),
                ('start', F3), ('start_angle', F3), ('time', ctypes.c_float), ('arg8', ctypes.c_int32), ('initial_lifetime', ctypes.c_int32),
                ('initial_scale', ctypes.c_float), ('field_80', ctypes.c_float), ('field_84', ctypes.c_float)]


class Host(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('rand', RAND_FN), ('terrain_height', HEIGHT_FN),
                ('owner_position', OWNER_FN), ('world', ctypes.c_int32), ('world_time', ctypes.c_float),
                ('frame_time', ctypes.c_float), ('drop_divisor', ctypes.c_int32), ('scene_state', ctypes.c_int32),
                ('bitmap_height', BITMAP_HEIGHT_FN)]


class Bitmap(ctypes.Structure):
    _fields_ = [('width', ctypes.c_float), ('height', ctypes.c_float), ('components', ctypes.c_int8)]


class SpriteCall(ctypes.Structure):
    _fields_ = [('bitmap', ctypes.c_int32), ('position', F3), ('width', ctypes.c_float), ('height', ctypes.c_float),
                ('light', F3), ('rotation', ctypes.c_float), ('u', ctypes.c_float), ('v', ctypes.c_float),
                ('uw', ctypes.c_float), ('vh', ctypes.c_float), ('axes', ctypes.c_int32)]


class RenderCall(ctypes.Structure):
    _fields_ = [('state_count', ctypes.c_int32), ('state', ctypes.c_int32*4), ('state_arg', ctypes.c_int32*4),
                ('sprites', ctypes.c_int32), ('sprite', SpriteCall)]


STATE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
INT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
VOID_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
VEC_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
COLOR4_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
TEX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)


class GL(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('state', STATE_FN), ('bind', INT_FN), ('begin', INT_FN),
                ('end', VOID_FN), ('color3', VEC_FN), ('color4', COLOR4_FN), ('texcoord', TEX_FN),
                ('vertex', VEC_FN), ('push_matrix', VOID_FN), ('pop_matrix', VOID_FN)]


class Sprite(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('type', ctypes.c_int32),
                ('blend', ctypes.c_int32), ('axes', ctypes.c_int32), ('sheet', ctypes.c_float*2),
                ('sheet_time', ctypes.c_int32), ('scale', ctypes.c_float), ('alpha', ctypes.c_float),
                ('light', F3), ('start', F3), ('position', F3), ('rotation', ctypes.c_float),
                ('owner', ctypes.c_int32)]


class Sprites(ctypes.Structure):
    _fields_ = [('records', Sprite*1000), ('created', ctypes.c_uint64), ('full', ctypes.c_uint64)]


class Sheet(ctypes.Structure):
    _fields_ = [('across', ctypes.c_int32), ('down', ctypes.c_int32), ('ms', ctypes.c_float)]


class ShadowMesh(ctypes.Structure):
    _fields_ = [('triangle_count', ctypes.c_int16), ('texture', ctypes.c_int16),
                ('triangles', ctypes.POINTER(ctypes.c_uint8)), ('vertices', ctypes.POINTER(ctypes.c_float)),
                ('vertex_count', ctypes.c_int32)]


class VisualObject(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('type', ctypes.c_int32), ('position', F3), ('angle', F3),
                ('light', F3), ('scale', ctypes.c_float), ('blend_light', ctypes.c_float),
                ('blend_v', ctypes.c_float)]


P = ctypes.POINTER
FP = P(ctypes.c_float)
HAS_MODEL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, P(VisualObject))
BONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, P(VisualObject), ctypes.c_char_p, FP, FP)
VPARTICLE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, FP, FP, FP, ctypes.c_int32, ctypes.c_float,
                                ctypes.c_int32)
VSPRITE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, FP, ctypes.c_float, FP, ctypes.c_int32,
                              ctypes.c_float, ctypes.c_int32, ctypes.c_int32)
VJOINT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, FP, FP, ctypes.c_int32, ctypes.c_int32,
                             ctypes.c_float)
VEFFECT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, FP, FP, FP, ctypes.c_int32, ctypes.c_int32)


BONE_INDEX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, P(VisualObject), ctypes.c_int32, FP, FP)


class VisualHost(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('rand', RAND_FN), ('has_model', HAS_MODEL_FN), ('bone_position', BONE_FN),
                ('particle', VPARTICLE_FN), ('sprite', VSPRITE_FN), ('joint', VJOINT_FN), ('effect', VEFFECT_FN),
                ('world', ctypes.c_int32), ('world_time', ctypes.c_float), ('bone_index_position', BONE_INDEX_FN)]


BITMAP_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, P(Bitmap))
KILL_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)


def load_library(path):
    lib = ctypes.CDLL(str(path))
    I, U8, V = ctypes.c_int32, ctypes.c_uint8, ctypes.c_void_p
    for name, args, result in [
            ('mu_pt_kind_supported', [I, I], ctypes.c_int),
            ('mu_pt_wrapper_keeps', [P(Host), I, I], ctypes.c_int),
            ('mu_pt_create_record', [P(Particle), P(Host), I, FP, FP, FP, I, ctypes.c_float, I, I], ctypes.c_int),
            ('mu_pt_move_record', [P(Particle), P(Host)], ctypes.c_int),
            ('mu_pt_render_record', [P(Particle), P(Bitmap), U8, P(RenderCall)], ctypes.c_int),
            ('mu_pt_render_sprite', [FP, P(SpriteCall), I, P(GL)], None),
            ('mu_pt_sprite_create', [P(Sprites), I, FP, ctypes.c_float, FP, I, ctypes.c_float, I, I, P(Sheet)], I),
            ('mu_pt_sprites_mark_visible', [P(Sprites)], None),
            ('mu_pt_sprites_render', [P(Sprites), U8, ctypes.c_float, FP, BITMAP_FN, V, P(GL), KILL_FN, V], I),
            ('mu_pt_render_body_shadow', [P(ShadowMesh), I, FP, I, I, I, I, I, P(Host), P(GL)], I),
            ('mu_pt_transform_position', [FP, FP, FP, ctypes.c_int, ctypes.c_float, FP], None),
            ('mu_pt_object_visual', [P(VisualObject), P(VisualHost)], ctypes.c_int),
            ('mu_pt_find_bone', [P(ctypes.c_char_p), I, ctypes.c_char_p], I),
            ('mu_pt_particle_store', [P(Particle), ctypes.c_char_p], None),
            ('mu_pt_particle_load', [P(Particle), ctypes.c_char_p], None),
            ('mu_pt_particle_mask', [ctypes.c_char_p], None),
            ('mu_pt_sprite_store', [P(Sprite), ctypes.c_char_p], None),
            ('mu_pt_sprite_load', [P(Sprite), ctypes.c_char_p], None),
            ('mu_pt_sprite_mask', [ctypes.c_char_p], None)]:
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


def particle_bytes(lib, p):
    raw = ctypes.create_string_buffer(0xb4)
    lib.mu_pt_particle_store(ctypes.byref(p), raw)
    mask = ctypes.create_string_buffer(0xb4)
    lib.mu_pt_particle_mask(mask)
    return bytes(raw.raw), bytes(mask.raw)


def sprite_bytes(lib, s):
    raw = ctypes.create_string_buffer(0x3d8)
    lib.mu_pt_sprite_store(ctypes.byref(s), raw)
    mask = ctypes.create_string_buffer(0x3d8)
    lib.mu_pt_sprite_mask(mask)
    return bytes(raw.raw), bytes(mask.raw)


def compare_masked(mine, theirs, defined, mask, floats_at=()):
    """First difference on the modelled bytes (4-byte words compared as binary32 where both are
    floats in the model; any two NaNs equal)."""
    for off in range(0, len(mask), 1):
        if not mask[off]:
            continue
        if not defined[off]:
            return ('client left undefined', hex(off))
    off = 0
    while off < len(mask):
        if mask[off] and off+4 <= len(mask) and all(mask[off:off+4]):
            a, b = mine[off:off+4], theirs[off:off+4]
            if a != b:
                fa, fb = struct.unpack('<f', a)[0], struct.unpack('<f', b)[0]
                if not (off in floats_at and same(fa, fb)):
                    return (hex(off), b.hex(), a.hex(), fb, fa)
            off += 4
            continue
        if mask[off] and mine[off] != theirs[off]:
            return (hex(off), theirs[off], mine[off])
        off += 1
    return None


PARTICLE_FLOATS = {0x1c, 0x80, 0x84, 0x18, 0x20, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38, 0x3c, 0x40, 0x44, 0x54, 0x58, 0x5c, 0x60, 0x6c,
                   0x70, 0x74, 0x78, 0x7c, 0x88, 0x8c, 0x90, 0x94, 0x98, 0x9c, 0xac}
SPRITE_FLOATS = {0x90, 0x94, 0xa0, 0xd0, 0xec, 0xf0, 0xf4, 0x110, 0x114, 0x118, 0x158, 0x15c, 0x160, 0x16c}


# --------------------------------------------------------------------------
# Machine.

class PtMachine(vc.Combat):
    """validate_combat's machine with recording stubs at the OpenGL import
    targets and stubs that continue elsewhere (handler.jump_to)."""

    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_ALL
        self.gl_targets = {}
        pages = set()
        for name, (slot, cleanup) in GL_SLOTS.items():
            target = struct.unpack('<I', data[slot-am.DATA_BASE:slot-am.DATA_BASE+4])[0]
            self.gl_targets[target] = (name, cleanup)
            pages.add(target & ~0xfff)
        for page in sorted(pages):
            self.uc.mem_map(page, am.PAGE, UC_PROT_ALL)
            self.uc.mem_write(page, b'\xc3'*am.PAGE)

    def stub_entry(self, uc, address, size, ignored):
        handler = self.stubs.get(address)
        if handler is not None and getattr(handler, 'jump_to', None) is not None:
            uc.reg_write(self.x86.UC_X86_REG_EIP, handler.jump_to)
            return
        super().stub_entry(uc, address, size, ignored)

    def gl_stubs(self, log):
        stubs = {}
        for target, (name, cleanup) in self.gl_targets.items():
            def handler(mm, name=name, cleanup=cleanup):
                if name in ('glVertex3fv', 'glColor3fv'):
                    log.append((name, mm.floats(mm.argument(0), 3)))
                elif name in ('glColor4f', 'glTexCoord2f'):
                    log.append((name, [mm.float_argument(i) for i in range(cleanup//4)]))
                else:
                    log.append((name, [mm.argument(i) for i in range(cleanup//4)]))
                return 0, cleanup
            stubs[target] = handler
        return stubs


def jump_stub(address):
    def stub(mm):
        return 0
    stub.jump_to = address
    return stub


def mid_frame(size, slots=None):
    out = {-size+4: 0x3456789a, -size: 0x456789ab}
    out.update(slots or {})
    return (size, out)


def globals_region(world=0, world_time=0.0, dt=0.1, divisor=1, scene=6):
    return [am.defined_region('scene', SCENE_FLAG, struct.pack('<i', scene), writable=False),
            am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
            am.defined_region('time', TIME, struct.pack('<f', world_time), writable=False),
            am.defined_region('dt', DT, struct.pack('<f', dt), writable=False),
            am.defined_region('divisor', DIVISOR, struct.pack('<i', divisor), writable=False)]


class Case:
    """rand(), RequestTerrainHeight, sin/cos and the owner objects of one case,
    for both sides."""

    def __init__(self, rng, rand_values=None, height=0.0, owners=()):
        self.rand_values = list(rand_values if rand_values is not None else
                                [rng.randrange(0, 32768) for _ in range(64)])
        self.height = f32(height)
        self.bitmap_h = f32(rng.choice([64.0, 32.0, 128.0, 256.0]))
        self.owners = list(owners)
        self.client_rand = self.c_rand = 0
        self.client_calls, self.c_calls = [], []
        self._keep = []

    def stubs(self, m):
        def rand(mm):
            v = self.rand_values[self.client_rand % len(self.rand_values)]
            self.client_rand += 1
            return v

        def height(mm):
            self.client_calls.append(('height', mm.float_argument(0), mm.float_argument(1)))
            return mm.x87_return(self.height)

        def sine(mm):
            x = mm.float_argument(0)
            return mm.x87_return(f32(math.sin(x)) if math.isfinite(x) else float('nan'))

        def cosine(mm):
            x = mm.float_argument(0)
            return mm.x87_return(f32(math.cos(x)) if math.isfinite(x) else float('nan'))
        def sqrt(mm):
            x = mm.float_argument(0)
            return mm.x87_return(f32(math.sqrt(x)) if x >= 0 else float('nan'))
        return {RAND: rand, TERRAIN: height, SINE: sine, COSINE: cosine, 0x00961a07: sqrt}

    def owner_regions(self):
        out = []
        for i, pos in enumerate(self.owners):
            raw = bytearray(am.poison(0x400, 0x31))
            mask = bytearray(0x400)
            struct.pack_into('<3f', raw, 0x158, *pos)
            mask[0x158:0x164] = b'\1'*12
            out.append(am.Region(f'owner{i}', object_address(i), bytes(raw), bytes(mask), writable=False))
        return out

    def host(self, world=0, world_time=0.0, dt=0.1, divisor=1, scene=6):
        def rand(ctx):
            v = self.rand_values[self.c_rand % len(self.rand_values)]
            self.c_rand += 1
            return v

        def height(ctx, x, y):
            self.c_calls.append(('height', x, y))
            return self.height

        def owner(ctx, index, out):
            pos = self.owners[index]
            for k in range(3):
                out[k] = pos[k]
        def bitmap_height(ctx, index):
            self.c_calls.append(('bitmap', index))
            return self.bitmap_h
        fns = (RAND_FN(rand), HEIGHT_FN(height), OWNER_FN(owner), BITMAP_HEIGHT_FN(bitmap_height))
        self._keep.append(fns)
        return Host(None, fns[0], fns[1], fns[2], world, f32(world_time), f32(dt), divisor, scene, fns[3])

    def bitmap_region(self):
        # NATIVE-HELPERS-002: the record the getter 0x00ebbec8 returns (only the height +0x208 defined)
        region = am.Region('bitmap', BITMAP_RECORD, am.poison(0x220, 0x45), bytes(0x220), writable=False)
        region.define(BITMAP_RECORD+0x208, struct.pack('<f', self.bitmap_h))
        return region

    def bitmap_stub(self):
        def get(mm):
            self.client_calls.append(('bitmap', mm.argument(0)))
            return BITMAP_RECORD, 4
        return get


class Report:
    def __init__(self):
        self.families = {}
        self.coverage = {}

    def cover(self, family, key):
        entry = self.coverage.setdefault(family, {})
        entry[key] = entry.get(key, 0) + 1

    def add(self, family, equal, failure=None):
        entry = self.families.setdefault(family, {'cases': 0, 'equal': 0, 'first_failures': []})
        entry['cases'] += 1
        entry['equal'] += bool(equal)
        if not equal and len(entry['first_failures']) < 5:
            entry['first_failures'].append(failure)


def rf(rng, lo, hi, special=0.1):
    if rng.random() < special:
        return f32(rng.choice([0.0, -0.0, 1.0, lo, hi, 0.5]))
    return f32(rng.uniform(lo, hi))


def shared_stubs(case, m, extra=None):
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


# --------------------------------------------------------------------------
# Families.

def family_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        pos = [rf(rng, 0.0, 25600.0), rf(rng, 0.0, 25600.0), rf(rng, -100.0, 800.0)]
        angle = [rf(rng, -360.0, 360.0) for _ in range(3)]
        light = [rf(rng, 0.0, 1.5) for _ in range(3)]
        scale = f32(rng.choice([1.0, 1.0, 0.5, 2.0, 4.0, rf(rng, 0.1, 8.0)]))
        arg8 = rng.randrange(-2**31, 2**31)
        owner = rng.choice([-1, -1, 0])
        world = rng.choice([0, 2, 0x22, 0x8d, 0x8b, 0x5d])
        world_time = f32(rng.choice([0.0, 39.0, 123456.0, rng.uniform(0, 3.0e6)]))
        scene = rng.choice([6, 5, 5, 3])
        case = Case(rng, height=rng.uniform(-50, 400), owners=[[rf(rng, 0, 25600), rf(rng, 0, 25600), 150.0]])
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<9f', *pos, *angle, *light), writable=False)
        record = am.defined_region('particle', PARTICLE, am.poison(PARTICLE_BYTES, 0x5d))
        regions = [inputs, record] + globals_region(world, world_time, scene=scene) + case.owner_regions()
        r = m.execute(CREATE_CORE, [kind[0], INPUTS, INPUTS+12, INPUTS+24, kind[1], bits(scale),
                                    object_address(owner), arg8 & 0xffffffff], regions, shared_stubs(case, m),
                      ecx=POOL, cleanup=0x20)
        p = Particle()
        # the record keeps a former particle's bytes where CreateParticle writes nothing (+0x44, +0x7c)
        lib.mu_pt_particle_load(ctypes.byref(p), am.poison(PARTICLE_BYTES, 0x5d))
        host = case.host(world, world_time, scene=scene)
        supported = lib.mu_pt_create_record(ctypes.byref(p), ctypes.byref(host), kind[0], F3(*pos), F3(*angle),
                                            F3(*light), kind[1], scale, owner, arg8)
        mismatch = None
        if vc.ok(r):
            out = r['regions']['particle']
            mine, mask = particle_bytes(lib, p)
            mismatch = compare_masked(mine, out, record.defined, mask, PARTICLE_FLOATS)
            if mismatch is None and struct.unpack('<I', out[0x50:0x54])[0] != object_address(owner):
                mismatch = ('owner', out[0x50:0x54].hex())
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None and not all(vc._same_call(a, b) for a, b in zip(case.client_calls, case.c_calls)) \
                    or len(case.client_calls) != len(case.c_calls):
                mismatch = mismatch or ('calls', case.client_calls, case.c_calls)
        equal = supported == 1 and vc.ok(r) and mismatch is None
        report.add('create', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                     'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('create', f'{kind[0]:#x}/{kind[1]}' + (' owner' if owner >= 0 else ''))
        if vc.ok(r) and kind in ((0x831d, 6), (0x83b3, 6), (0x7f26, 0x2a), (0x7f5a, 0x7f)):
            negatives['tail_initial_life_20'] += struct.unpack_from('<i', r['regions']['particle'], 0x4c)[0] != 20
        if vc.ok(r) and kind == (0x801b, 2):
            # negative control (NATIVE-CHARSEL-002): WATERFALL2's light without the scene-5 rule
            l = struct.unpack('<f', r['regions']['particle'][0x38:0x3c])[0]
            negatives['create_waterfall2_no_scene'] += not same(l, f32(0.4))
        if vc.ok(r) and kind == (0x7f25, 1):
            # negative control (NATIVE-HELPERS-002): the angel's sparkle living like Spark02 subtype 0
            life = struct.unpack('<i', r['regions']['particle'][0x48:0x4c])[0]
            negatives['create_spark2_1_as_0'] += life != case.rand_values[1] % 16 + 24
        if vc.ok(r) and kind == (0x7f3c, 1):
            # negative control: Fire01 subtype 1 sized like subtype 0
            sc = struct.unpack('<f', r['regions']['particle'][0x18:0x1c])[0]
            negatives['create_fire1_large'] += not same(sc, f32(f32((case.rand_values[1] % 64) + 128) * f32(0.01)))


def family_wrapper(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        world = rng.choice([0x8b, 0x8b, 0, 0x8d, 2])
        divisor = rng.choice([0, 1, 2, 3, 5, -4, 10])
        kind = rng.choice(KINDS + [(0x7ef7, 0), (0x7f27, 0), (0x8086, 1)])
        case = Case(rng)
        created = []

        def core(mm):
            created.append(mm.argument(0))
            return 0, 0x20
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<9f', *([1.0]*9)), writable=False)
        regions = [inputs] + globals_region(world, 0.0, 0.1, divisor)
        stubs = case.stubs(m)
        stubs[CREATE_CORE] = core
        r = m.execute(CREATE_WRAPPER, [kind[0], INPUTS, INPUTS+12, INPUTS+24, kind[1], bits(1.0), 0, 0], regions,
                      stubs)
        host = case.host(world, 0.0, 0.1, divisor)
        keeps = lib.mu_pt_wrapper_keeps(ctypes.byref(host), kind[0], kind[1])
        mismatch = None
        if vc.ok(r):
            if bool(created) != bool(keeps):
                mismatch = ('keep', bool(created), keeps)
            elif case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        report.add('wrapper', vc.ok(r) and mismatch is None, {'case': n, 'world': world, 'kind': kind,
                                                               'mismatch': mismatch, 'stopped': r['stopped'],
                                                               'error': r['error'], 'checks': r['checks']})
        report.cover('wrapper', f'world {world:#x} ' + ('kept' if keeps else 'dropped'))
        if vc.ok(r) and world == 0x8b:
            # negative control: the drop applied to every kind
            d = divisor if divisor > 0 else 1
            negatives['wrapper_no_exempt'] += (case.rand_values[0] % d == 0) != bool(created)


def random_particle(rng, kind):
    p = Particle()
    p.live = rng.choice([1, 1, 1, 1, 0, 2])
    p.type = p.tex_type = kind[0]
    p.subtype = kind[1]
    p.scale = rf(rng, 0.05, 6.0)
    p.lifetime = rng.choice([24, 23, 16, 12, 2, 1, 0, -1, rng.randrange(-3, 60)])
    p.owner = rng.choice([-1, -1, -1, 0])
    p.rotation = rf(rng, -360.0, 720.0)
    p.frame = rng.randrange(-3, 6)
    p.moving = rng.choice([1, 1, 0])
    p.gravity = f32(rng.choice([0.0, 0.004, 20.0, 6.5, rf(rng, -10.0, 10.0)]))
    p.time = rf(rng, 0.0, 100.0)
    p.arg8 = rng.randrange(-10, 10)
    p.alpha = f32(rng.choice([0.1, 1.0, 0.95, 0.12, 0.09, rf(rng, -0.5, 1.5)]))
    p.field_7c = rf(rng, 0.0, 0.1)
    p.field_80, p.field_84 = rf(rng, 0.0, 1.0), rf(rng, 0.0, 1.0)
    p.initial_lifetime = rng.choice([30, 40, 100, 1, 2, 0, -1, -3])
    p.initial_scale = rf(rng, 0.1, 2.0)
    if kind == (0x7f89, 0x14):
        p.lifetime = rng.choice([300, 151, 150, 149, 2, 1, 0, -1, rng.randrange(-3, 301)])
    if kind in ((0x801b, 2), (0x8022, 5)):   # NATIVE-CHARSEL-002: the fades at LifeTime 10
        p.lifetime = rng.choice([40, 22, 11, 10, 9, 2, 1, rng.randrange(1, 41)])
    if kind == (0x8017, 0):
        p.scale = f32(rng.choice([0.01, 0.02, 0.019, 0.021, rf(rng, 0.0, 2.0)]))
    for k in range(3):
        p.position[k] = rf(rng, 0.0, 25600.0) if k < 2 else rf(rng, -100.0, 800.0)
        p.angle[k] = rf(rng, -360.0, 360.0)
        p.light[k] = rf(rng, 0.0, 1.5)
        p.velocity[k] = f32(rng.choice([0.0, -3.7, -50.0, rf(rng, -60.0, 60.0)]))
        p.start[k] = rf(rng, 0.0, 25600.0)
        p.start_angle[k] = rf(rng, -360.0, 360.0)
        p.owner_position[k] = rf(rng, 0.0, 25600.0)
    return p


def particle_region(lib, p):
    raw, mask = particle_bytes(lib, p)
    data = bytearray(am.poison(PARTICLE_BYTES, 0x3b))
    defined = bytearray(PARTICLE_BYTES)
    for i in range(0xb4):
        if mask[i]:
            data[i] = raw[i]
            defined[i] = 1
    struct.pack_into('<I', data, 0x50, object_address(p.owner))
    defined[0x50:0x54] = b'\1'*4
    return am.Region('particle', PARTICLE, bytes(data), bytes(defined))


MOVE_FRAME = 0xc + 0x7038 + 8
RENDER_FRAME = 0xc + 0x1f1c + 8


def family_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        p = random_particle(rng, kind)
        world = rng.choice([0, 0x22, 0x8d, 2])
        dt = f32(rng.choice([0.1, 0.1, rf(rng, 0.0, 2.0)]))
        case = Case(rng, height=rng.uniform(-50, 400), owners=[[rf(rng, 0, 25600), rf(rng, 0, 25600), 150.0]])
        record = particle_region(lib, p)
        regions = [record, case.bitmap_region()] + globals_region(world, 0.0, dt) + case.owner_regions()
        host = case.host(world, 0.0, dt)
        before = Particle.from_buffer_copy(p)
        if p.lifetime <= 0 or not p.live:
            moved = lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))
            report.add('move', moved == 0, {'case': n, 'removed_at_head': True})
            report.cover('move', 'erased at the head')
            continue
        stubs = shared_stubs(case, m, {0x0168ee7d: jump_stub(0x0168eea4), BITMAP_RECORD_GET: case.bitmap_stub()})
        r = m.execute(0x01616f7c, [], regions, stubs, ecx=POOL, frame=mid_frame(MOVE_FRAME, {-0x38: 7}))
        moved = lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))
        mismatch = None
        if vc.ok(r):
            mine, mask = particle_bytes(lib, p)
            mismatch = compare_masked(mine, r['regions']['particle'], record.defined, mask, PARTICLE_FLOATS)
            if mismatch is None and case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            if mismatch is None and (len(case.client_calls) != len(case.c_calls) or
                                     not all(vc._same_call(a, b) for a, b in zip(case.client_calls, case.c_calls))):
                mismatch = ('calls', case.client_calls, case.c_calls)
        equal = moved == 1 and vc.ok(r) and mismatch is None
        report.add('move', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mismatch': mismatch,
                                   'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('move', f'{kind[0]:#x}/{kind[1]}' + (' owner' if p.owner >= 0 else ''))
        if vc.ok(r) and kind == (0x8022, 5):
            # negative control (NATIVE-CHARSEL-002): the selection light without its rise
            z = struct.unpack('<f', r['regions']['particle'][0x28:0x2c])[0]
            negatives['move_chasellight_no_rise'] += not same(z, f32(p.position[2] - p.gravity))
        if vc.ok(r) and kind == (0x7f5a, 0x75) and before.lifetime > 0 and before.live:
            negatives['breath_no_direction'] += any(not same(p.position[k], before.position[k]) for k in range(3))
        if vc.ok(r) and kind == (0x8086, 0x13) and before.lifetime > 0 and before.live:
            negatives['tail_fire_no_saved_colour'] += not same(p.light[0], before.light[0])
        if vc.ok(r) and kind == (0x7f5b, 0):
            # negative control (NATIVE-HELPERS-002): smoke02 seated without half its height
            z = struct.unpack('<f', r['regions']['particle'][0x28:0x2c])[0]
            negatives['move_smoke2_no_half_height'] += not same(z, case.height)
        if vc.ok(r) and kind == (0x7f5a, 0):
            # negative control: smoke light over 16 steps instead of 8
            l = struct.unpack('<f', r['regions']['particle'][0x38:0x3c])[0]
            negatives['move_smoke_light_16'] += not same(l, f32(f32(before.lifetime)/f32(16.0)))


def family_wind(m, lib, rng, cases, report, negatives):
    class System(ctypes.Structure):
        _fields_ = [('records', ctypes.c_void_p), ('count', ctypes.c_int32), ('capacity', ctypes.c_int32),
                    ('wind', ctypes.c_float*2), ('wind_sum', ctypes.c_float*2), ('created', ctypes.c_uint64),
                    ('dropped', ctypes.c_uint64), ('unsupported', ctypes.c_uint64), ('overflow', ctypes.c_uint64)]
    lib.mu_pt_wind_step.argtypes = [P(System), P(Host)]
    lib.mu_pt_wind_step.restype = None
    for n in range(cases):
        wind = [f32(rng.choice([0.0, 0.6, -0.6, 0.59999, rf(rng, -0.7, 0.7)])) for _ in range(2)]
        wsum = [f32(rng.choice([0.0, 1.7, -1.7, 1.69, rf(rng, -1.8, 1.8)])) for _ in range(2)]
        case = Case(rng)
        raw = bytearray(am.poison(0x20, 0x11))
        mask = bytearray(0x20)
        struct.pack_into('<2f', raw, 8, *wind)
        struct.pack_into('<2f', raw, 0x14, *wsum)
        mask[8:0x10] = b'\1'*8
        mask[0x14:0x1c] = b'\1'*8
        pool = am.Region('pool', POOL, bytes(raw), bytes(mask))
        stubs = case.stubs(m)
        stubs[0x01616ec9] = jump_stub(0x0168eea4)
        r = m.execute(MOVE_PARTICLES, [], [pool], stubs, ecx=POOL)
        s = System()
        s.wind[0], s.wind[1] = wind
        s.wind_sum[0], s.wind_sum[1] = wsum
        host = case.host()
        lib.mu_pt_wind_step(ctypes.byref(s), ctypes.byref(host))
        mismatch = None
        if vc.ok(r):
            out = r['regions']['pool']
            theirs = struct.unpack('<2f', out[8:0x10]) + struct.unpack('<2f', out[0x14:0x1c])
            mine = (s.wind[0], s.wind[1], s.wind_sum[0], s.wind_sum[1])
            if not all(same(a, b) for a, b in zip(theirs, mine)):
                mismatch = ('wind', theirs, mine)
            elif case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
        report.add('wind', vc.ok(r) and mismatch is None, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'],
                                                            'error': r['error'], 'checks': r['checks']})
        report.cover('wind', 'step')
        if vc.ok(r):
            # negative control: no clamp on the walk
            w = f32(f32(f32(case.rand_values[0] % 2001 - 1000) * f32(0.0006)) + wind[0])
            negatives['wind_unclamped'] += not same(struct.unpack('<f', r['regions']['pool'][8:12])[0], w)


def family_render(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        p = random_particle(rng, kind)
        p.live = 1
        p.owner = -1
        mode = rng.choice([0, 0, 1, 2, 3])
        bm = Bitmap(f32(rng.choice([64.0, 128.0, 256.0, 32.0])), f32(rng.choice([64.0, 128.0, 32.0])),
                    rng.choice([3, 3, 4]))
        if rng.random() < 0.3:
            p.position[2] = f32(rng.choice([300.0, 350.0, 299.99997, 350.00003, 1e9]))
        case = Case(rng)
        record = particle_region(lib, p)
        bmr = am.Region('bitmap', BITMAP_RECORD, am.poison(0x220, 0x44), bytes(0x220), writable=False)
        bmr.define(BITMAP_RECORD+0x204, struct.pack('<ff', bm.width, bm.height))
        bmr.define(BITMAP_RECORD+0x214, struct.pack('<b', bm.components))
        calls = []

        def bitmap_get(mm):
            calls.append(('bitmap', mm.argument(0)))
            return BITMAP_RECORD, 4

        def wrapper(address, args):
            def stub(mm):
                calls.append(('state', address, mm.argument(0) if args else 0))
                return 0
            return stub

        def sprite(mm):
            a = [mm.argument(i) for i in range(11)]
            calls.append(('sprite', a[0], mm.floats(a[1], 3), from_bits(a[2]), from_bits(a[3]), mm.floats(a[4], 3),
                          from_bits(a[5]), from_bits(a[6]), from_bits(a[7]), from_bits(a[8]), from_bits(a[9]), a[10]))
            return 0
        stubs = shared_stubs(case, m, {0x015ae351: jump_stub(0x015ae363), 0x01591282: jump_stub(0x015ae363),
                                         BITMAP_GET: bitmap_get, RENDER_SPRITE: sprite,
                                         STATE_ADD: wrapper(STATE_ADD, 0), STATE_ALPHA: wrapper(STATE_ALPHA, 1),
                                         STATE_SUB: wrapper(STATE_SUB, 0), STATE_6B7: wrapper(STATE_6B7, 0),
                                         STATE_6DA: wrapper(STATE_6DA, 0), STATE_BLEND: wrapper(STATE_BLEND, 0)})
        regions = [record, bmr]
        if kind == (0x7f89,18):
            regions.append(am.defined_region('time', TIME, struct.pack('<f',12345.0)))
        r = m.execute(0x015912e9, [0x5500 | mode], regions, stubs, ecx=POOL, frame=mid_frame(RENDER_FRAME),
                      cleanup=4)
        rc = RenderCall()
        if kind == (0x7f89,18):
            lib.mu_pt_elbeland_render.argtypes = [ctypes.POINTER(Particle),ctypes.c_float]
            lib.mu_pt_elbeland_render(ctypes.byref(p),12345.0)
        drawn = lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), mode, ctypes.byref(rc))
        mine = []
        if drawn == 1:
            mine.append(('bitmap', p.tex_type))
            for k in range(rc.state_count):
                if rc.state[k] == STATE_SUB:
                    continue
                mine.append(('state', rc.state[k], rc.state_arg[k]))
            for k in range(rc.state_count):
                if rc.state[k] == STATE_SUB:
                    mine.append(('state', rc.state[k], rc.state_arg[k]))
            sp = rc.sprite
            mine.append(('sprite', sp.bitmap, list(sp.position), sp.width, sp.height, list(sp.light), sp.rotation,
                         sp.u, sp.v, sp.uw, sp.vh, sp.axes))
        mismatch = None
        if vc.ok(r) and (len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine))):
            mismatch = ('calls', calls, mine)
        equal = drawn != 2 and vc.ok(r) and mismatch is None
        report.add('render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode, 'mismatch': mismatch,
                                     'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('render', f'{kind[0]:#x}/{kind[1]}' + ('' if drawn == 1 else ' skipped'))
        if vc.ok(r) and drawn == 1 and kind in ((0x831d, 6), (0x83b3, 6), (0x7f26, 0x2a), (0x7f5a, 0x7f)):
            negatives['tail_glint_no_alpha'] += not same(p.light[0], f32(p.light[0] * p.alpha))
        if vc.ok(r) and drawn == 1 and kind == (0x7fcd, 0):
            # negative control (NATIVE-HELPERS-002): drop01 drawn with the whole sheet
            u = [c for c in calls if c[0] == 'sprite'][0][9]
            negatives['render_drop_whole_sheet'] += not same(u, f32(1.0))
        if vc.ok(r) and drawn == 1 and kind[0] == 0x7f3c:
            # negative control: the full texture width for the four-cell strip
            w = [c for c in calls if c[0] == 'sprite'][0][3]
            negatives['render_fire_full_width'] += not same(w, f32(bm.width*p.scale))


class GLLog:
    """The C side's GL stream in the client's terms."""

    def __init__(self):
        self.log = []

        def state(ctx, wrapper, arg):
            self.log.append(('state', wrapper, arg))

        def bind(ctx, b):
            self.log.append(('bind', b))

        def begin(ctx, mode):
            self.log.append(('glBegin', [mode]))

        def end(ctx):
            self.log.append(('glEnd', []))

        def color3(ctx, v):
            self.log.append(('glColor3fv', [v[0], v[1], v[2]]))

        def color4(ctx, r, g, b, a):
            self.log.append(('glColor4f', [r, g, b, a]))

        def tex(ctx, u, v):
            self.log.append(('glTexCoord2f', [u, v]))

        def vertex(ctx, v):
            self.log.append(('glVertex3fv', [v[0], v[1], v[2]]))

        def push(ctx):
            self.log.append(('glPushMatrix', []))

        def pop(ctx):
            self.log.append(('glPopMatrix', []))
        self.fns = (STATE_FN(state), INT_FN(bind), INT_FN(begin), VOID_FN(end), VEC_FN(color3), COLOR4_FN(color4),
                    TEX_FN(tex), VEC_FN(vertex), VOID_FN(push), VOID_FN(pop))
        self.gl = GL(None, *self.fns)


def random_camera(rng):
    a = [rf(rng, -180.0, 180.0, 0.0) for _ in range(3)]
    cx, sx = math.cos(math.radians(a[0])), math.sin(math.radians(a[0]))
    cz, sz = math.cos(math.radians(a[2])), math.sin(math.radians(a[2]))
    rows = [[cz, -sz, 0.0], [sx*sz, sx*cz, -cx], [cx*sz, cx*cz, sx]]
    t = [rf(rng, -20000.0, 20000.0, 0.0) for _ in range(3)]
    return [f32(v) for v in rows[0] + [t[0]] + rows[1] + [t[1]] + rows[2] + [t[2]]]


def family_sprite(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        camera = random_camera(rng)
        bitmap = rng.choice([0x7f3c, 0x7f5a, 0x771c, 0x7ef7, 0x7f49, 0x7df3])
        comps = rng.choice([3, 4])
        pos = [rf(rng, 0.0, 25600.0), rf(rng, 0.0, 25600.0), rf(rng, -100.0, 800.0)]
        light = [rf(rng, 0.0, 1.5) for _ in range(3)]
        w, h = rf(rng, 0.0, 300.0), rf(rng, 0.0, 300.0)
        rot = f32(rng.choice([0.0, 0.0, -0.0, 30.0, rf(rng, -720.0, 720.0)]))
        u, v, uw, vh = [f32(rng.choice([0.0, 0.25, 0.5, 1.0, rf(rng, 0, 1)])) for _ in range(4)]
        axes = rng.choice([4, 4, 1, 2, 3, 7, 0, 5])
        case = Case(rng)
        log = []
        regions = [am.defined_region('inputs', INPUTS, struct.pack('<6f', *pos, *light), writable=False),
                   am.defined_region('camera', CAMERA_MATRIX, struct.pack('<12f', *camera), writable=False)]
        bmr = am.Region('bitmap', BITMAP_RECORD, am.poison(0x220, 0x44), bytes(0x220), writable=False)
        bmr.define(BITMAP_RECORD+0x214, struct.pack('<b', comps))
        regions.append(bmr)

        def bind(mm):
            log.append(('bind', mm.argument(0)))
            return 0

        def bitmap_get(mm):
            return BITMAP_RECORD, 4
        stubs = case.stubs(m)
        stubs.update(m.gl_stubs(log))
        stubs.update({BIND: bind, BITMAP_GET: bitmap_get})
        r = m.execute(RENDER_SPRITE, [bitmap, INPUTS, bits(w), bits(h), INPUTS+12, bits(rot), bits(u), bits(v),
                                      bits(uw), bits(vh), axes], regions, stubs)
        gl = GLLog()
        call = SpriteCall(bitmap, F3(*pos), w, h, F3(*light), rot, u, v, uw, vh, axes)
        lib.mu_pt_render_sprite((ctypes.c_float*12)(*camera), ctypes.byref(call), comps, ctypes.byref(gl.gl))
        mismatch = None
        if vc.ok(r) and (len(log) != len(gl.log) or not all(vc._same_call(a, b) for a, b in zip(log, gl.log))):
            mismatch = ('gl', log, gl.log)
        report.add('sprite', vc.ok(r) and mismatch is None, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'],
                                                              'error': r['error'], 'checks': r['checks']})
        report.cover('sprite', ('rotated' if rot != 0.0 else 'upright') + f' {comps}')
        if vc.ok(r) and rot == 0.0:
            # negative control: texcoords not flipped in v
            t = [c for c in log if c[0] == 'glTexCoord2f'][0][1]
            negatives['sprite_v_unflipped'] += not (same(t[0], u) and same(t[1], v))


SPRITE_BYTES = 0x3d8


def random_sprite(rng, live):
    s = Sprite()
    s.live = live
    s.visible = rng.choice([0, 1])
    s.type = rng.choice([0x7ef7, 0x7f3c, 0x7f5a, 0x7fea])
    s.blend = rng.choice([0, 0, 1, 2, 3, 4, 5])
    s.axes = rng.choice([4, 4, 1, 7])
    across, down = rng.choice([(1, 1), (1, 1), (4, 4), (2, 1), (1, 2), (3, 3)])   # 0 across divides by zero
    s.sheet[0], s.sheet[1] = float(across), float(down)
    s.sheet_time = rng.choice([1, 40, 100])
    s.scale = rf(rng, 0.0, 6.0)
    s.alpha = f32(rng.choice([1.0, 0.95, 0.2, 0.25, rf(rng, 0.0, 1.2)]))
    s.rotation = f32(rng.choice([0.0, 30.0, rf(rng, -360, 360)]))
    s.owner = -1
    for k in range(3):
        s.light[k] = rf(rng, 0.0, 1.5)
        s.position[k] = rf(rng, 0.0, 25600.0) if k < 2 else f32(rng.choice([rf(rng, -100.0, 800.0), 300.0, 350.0]))
        s.start[k] = s.position[k]
    return s


def sprites_region(lib, records, defined_records):
    data = bytearray(am.poison(SPRITE_BYTES*1000, 0x27))
    defined = bytearray(SPRITE_BYTES*1000)
    for i, s in enumerate(records):
        base = i*SPRITE_BYTES
        if i in defined_records:
            raw, mask = sprite_bytes(lib, s)
            for k in range(SPRITE_BYTES):
                if mask[k]:
                    data[base+k] = raw[k]
                    defined[base+k] = 1
            struct.pack_into('<I', data, base+0x34c, 0)
            defined[base+0x34c:base+0x350] = b'\1'*4
        else:
            data[base] = s.live
            defined[base] = 1
            struct.pack_into('<f', data, base+0x160, s.position[2])
            defined[base+0x160:base+0x164] = b'\1'*4
    return am.Region('sprites', SPRITES, bytes(data), bytes(defined))


def family_sprite_create(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        free = rng.choice([0, 0, 1, 5, 37, 999, None])
        records = []
        for i in range(1000):
            live = 0 if (free is not None and i == free) else (1 if free is None or i < free else rng.choice([0, 1]))
            s = Sprite()
            s.live = live
            records.append(s)
        region = sprites_region(lib, records, set())
        # dead records: every field may be read or written
        for i in range(1000):
            if not records[i].live:
                base = i*SPRITE_BYTES
                region.defined[base:base+SPRITE_BYTES] = b'\1'*SPRITE_BYTES
        bitmap = rng.choice([0x7ef7, 0x7f3c, 0x7fea])
        pos = [rf(rng, 0.0, 25600.0), rf(rng, 0.0, 25600.0), rf(rng, -100.0, 800.0)]
        light = [rf(rng, 0.0, 1.5) for _ in range(3)]
        scale, rot = rf(rng, 0.0, 8.0), rf(rng, -360.0, 360.0)
        blend, axes = rng.choice([0, 1, 2, 3, 4]), rng.choice([4, 1, 7])
        sheet = (rng.choice([1, 1, 4]), rng.choice([1, 1, 2]), f32(rng.choice([1.0, 40.0, 99.9, -3.5])))
        owner = rng.choice([-1, 0])
        case = Case(rng)
        inputs = am.defined_region('inputs', INPUTS, struct.pack('<6f', *pos, *light) +
                                   struct.pack('<iif', *sheet), writable=False)
        stubs = case.stubs(m)
        kills = []

        def cleanup(mm):
            kills.append(mm.uc.reg_read(mm.x86.UC_X86_REG_ECX))
            return 0
        stubs[KILL_CLEANUP] = cleanup
        r = m.execute(CREATE_SPRITE_CORE, [bitmap, INPUTS, bits(scale), INPUTS+12, object_address(owner), bits(rot),
                                           blend, axes, INPUTS+24], [region, inputs] + case.owner_regions(), stubs,
                      ecx=SPRITES, cleanup=0x24)
        sp = Sprites()
        for i in range(1000):
            sp.records[i].live = records[i].live
        index = lib.mu_pt_sprite_create(ctypes.byref(sp), bitmap, F3(*pos), scale, F3(*light), owner, rot, blend, axes,
                                        ctypes.byref(Sheet(*sheet)))
        mismatch = None
        if vc.ok(r):
            if (r['eax'] & 0xffffffff) != index:
                mismatch = ('index', r['eax'], index)
            elif free is not None or any(not s.live for s in records):
                out = r['regions']['sprites'][index*SPRITE_BYTES:(index+1)*SPRITE_BYTES]
                mine, mask = sprite_bytes(lib, sp.records[index])
                mask = bytearray(mask)
                mask[0x0b] = 0      # visible: CreateSprite does not write it
                mask[0x0d0:0x0d4] = mask[0x0d0:0x0d4]
                rmask = bytearray(mask)
                for k in (0x164, 0x168):   # angle x/y untouched
                    rmask[k:k+4] = b'\0'*4
                defined = region.defined[index*SPRITE_BYTES:(index+1)*SPRITE_BYTES]
                mismatch = compare_masked(mine, out, defined, rmask, SPRITE_FLOATS)
                if mismatch is None and struct.unpack('<I', out[0x34c:0x350])[0] != object_address(owner):
                    mismatch = ('owner', out[0x34c:0x350].hex())
            if mismatch is None and kills:
                mismatch = ('cleanup', kills)
        report.add('sprite_create', vc.ok(r) and mismatch is None, {'case': n, 'free': free, 'mismatch': mismatch,
                                                                     'stopped': r['stopped'], 'error': r['error'],
                                                                     'checks': r['checks']})
        report.cover('sprite_create', 'full' if free is None else ('slot 0' if index == 0 else 'slot'))
        if vc.ok(r) and free is not None:
            # negative control: the sheet's ms rounded instead of truncated
            t = struct.unpack('<i', r['regions']['sprites'][index*SPRITE_BYTES+0x98:index*SPRITE_BYTES+0x9c])[0]
            negatives['sprite_sheet_rounded'] += t != int(round(sheet[2])) if math.isfinite(sheet[2]) else 0


def family_sprite_render(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        mode = rng.choice([0, 0, 1, 2])
        world_time = f32(rng.choice([0.0, 39.0, rng.uniform(0, 3.0e6)]))
        camera = random_camera(rng)
        live_set = set(rng.sample(range(1000), rng.choice([0, 1, 3, 8])))
        records = [random_sprite(rng, 1 if i in live_set else 0) for i in range(1000)]
        region = sprites_region(lib, records, live_set)
        bm = Bitmap(f32(rng.choice([64.0, 128.0, 32.0])), f32(rng.choice([64.0, 32.0])), rng.choice([3, 4]))
        bmr = am.Region('bitmap', BITMAP_RECORD, am.poison(0x220, 0x44), bytes(0x220), writable=False)
        bmr.define(BITMAP_RECORD+0x204, struct.pack('<ff', bm.width, bm.height))
        bmr.define(BITMAP_RECORD+0x214, struct.pack('<b', bm.components))
        regions = [region, bmr, am.defined_region('camera', CAMERA_MATRIX, struct.pack('<12f', *camera),
                                                   writable=False)] + globals_region(0, world_time)
        case = Case(rng)
        log = []

        def wrapper(address, args):
            def stub(mm):
                log.append(('state', address, mm.argument(0) if args else 0))
                return 0
            return stub

        def bitmap_get(mm):
            return BITMAP_RECORD, 4

        def sprite(mm):
            a = [mm.argument(i) for i in range(11)]
            log.append(('sprite', a[0], mm.floats(a[1], 3), from_bits(a[2]), from_bits(a[3]), mm.floats(a[4], 3),
                        from_bits(a[5]), from_bits(a[6]), from_bits(a[7]), from_bits(a[8]), from_bits(a[9]), a[10]))
            return 0

        def cleanup(mm):
            log.append(('kill', (mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)-SPRITES)//SPRITE_BYTES))
            return 0
        stubs = case.stubs(m)
        stubs.update({STATE_ADD: wrapper(STATE_ADD, 0), STATE_ALPHA: wrapper(STATE_ALPHA, 1),
                      STATE_SUB: wrapper(STATE_SUB, 0), STATE_INV: wrapper(STATE_INV, 0),
                      STATE_FOG: wrapper(STATE_FOG, 0), BITMAP_GET: bitmap_get, RENDER_SPRITE: sprite,
                      KILL_CLEANUP: cleanup})
        r = m.execute(RENDER_SPRITES, [0x7700 | mode], regions, stubs, ecx=SPRITES, cleanup=4)
        sp = Sprites()
        for i in range(1000):
            sp.records[i] = records[i]
        clog = []

        def kill(ctx, index):
            clog.append(('kill', index))
        calls = []

        class Recorder(GLLog):
            pass
        gl = GLLog()

        def bitmap_fn(ctx, b, out):
            out[0].width, out[0].height, out[0].components = bm.width, bm.height, bm.components
            return 1
        bfn, kfn = BITMAP_FN(bitmap_fn), KILL_FN(kill)
        # the C draws through RenderSprite; capture its arguments instead of the GL stream
        drawn_calls = []
        orig = lib.mu_pt_sprites_render
        count = orig(ctypes.byref(sp), mode, world_time, (ctypes.c_float*12)(*camera), bfn, None,
                     ctypes.byref(gl.gl), kfn, None)
        # rebuild the C order: state wrappers and kills from the logs, sprites from the GL stream
        mine = []
        glog = gl.log
        k = 0
        killed = iter(clog)
        # replay: walk the C GL log, converting each bind..glEnd to a sprite record
        i = 0
        events = []
        while i < len(glog):
            e = glog[i]
            if e[0] == 'state':
                events.append(e)
                i += 1
            elif e[0] == 'bind':
                j = i
                while glog[j][0] != 'glEnd':
                    j += 1
                events.append(('sprite-gl', glog[i:j+1]))
                i = j+1
            else:
                i += 1
        # client side: convert its RenderSprite argument records to GL with the C RenderSprite
        theirs = []
        for e in log:
            if e[0] == 'sprite':
                call = SpriteCall(e[1], F3(*e[2]), e[3], e[4], F3(*e[5]), e[6], e[7], e[8], e[9], e[10], e[11])
                g = GLLog()
                lib.mu_pt_render_sprite((ctypes.c_float*12)(*camera), ctypes.byref(call), bm.components,
                                        ctypes.byref(g.gl))
                theirs.append(('sprite-gl', g.log))
            elif e[0] == 'state':
                theirs.append(e)
        mismatch = None
        if vc.ok(r):
            if len(theirs) != len(events) or not all(vc._same_call(a, b) for a, b in zip(theirs, events)):
                bad = next((k for k, (a, b) in enumerate(zip(theirs, events)) if not vc._same_call(a, b)),
                           min(len(theirs), len(events)))
                mismatch = ('calls', len(theirs), len(events), bad, theirs[bad:bad+1], events[bad:bad+1])
            elif [e for e in log if e[0] == 'kill'] != clog:
                mismatch = ('kills', [e for e in log if e[0] == 'kill'][:6], clog[:6])
            else:
                for i in live_set:
                    out = r['regions']['sprites'][i*SPRITE_BYTES:(i+1)*SPRITE_BYTES]
                    mine_b, mask = sprite_bytes(lib, sp.records[i])
                    sub = bytearray(SPRITE_BYTES)
                    sub[0] = 1
                    sub[0xd0:0xd4] = b'\1'*4
                    mismatch = compare_masked(mine_b, out, region.defined[i*SPRITE_BYTES:(i+1)*SPRITE_BYTES], sub,
                                              SPRITE_FLOATS)
                    if mismatch:
                        mismatch = ('record', i, mismatch)
                        break
        report.add('sprite_render', vc.ok(r) and mismatch is None, {'case': n, 'mode': mode, 'mismatch': mismatch,
                                                                     'stopped': r['stopped'], 'error': r['error'],
                                                                     'checks': r['checks']})
        report.cover('sprite_render', f'mode {mode} ' + ('drawn' if count else 'none'))
        if vc.ok(r) and count:
            # negative control: the size without the alpha factor
            first = [e for e in log if e[0] == 'sprite'][0]
            negatives['sprite_render_no_alpha'] += any(
                same(first[3], f32(bm.width*records[i].scale)) for i in live_set) is False


def shadow_model(rng):
    meshes = []
    for i in range(rng.choice([1, 2, 3])):
        nv = rng.randrange(3, 12)
        verts = [[rf(rng, -200.0, 200.0, 0.0) + 12800.0, rf(rng, -200.0, 200.0, 0.0) + 12800.0,
                  rf(rng, -20.0, 300.0, 0.05)] for _ in range(nv)]
        tris = []
        for _ in range(rng.randrange(0, 6)):
            corners = rng.choice([3, 3, 4])
            tris.append((corners, [rng.randrange(nv) for _ in range(4)]))
        meshes.append({'texture': rng.choice([0, 1, 2, 3]), 'verts': verts, 'tris': tris})
    return meshes


def family_shadow(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        meshes = shadow_model(rng)
        origin = [f32(12800.0 + rf(rng, -50, 50, 0.0)), f32(12800.0 + rf(rng, -50, 50, 0.0)), rf(rng, 0.0, 200.0)]
        hide_texture = rng.choice([-1, -1, 0, 1, 2])
        hide_mesh = rng.choice([-1, -1, 0, 1])
        first = rng.choice([-1, -1, 0, 1])
        end = rng.choice([-1, -1, len(meshes), 1, 2])
        if end != -1 and end > len(meshes):
            end = len(meshes)
        z_offset = rng.choice([0, 0, 5, -3])
        world = rng.choice([0, 0, 0x1e, 0x91, 2])
        case = Case(rng, height=rng.uniform(0, 300))
        model = bytearray(am.poison(0x100, 0x61))
        mmask = bytearray(0x100)
        struct.pack_into('<h', model, 0x24, len(meshes))
        struct.pack_into('<I', model, 0x28, MESHES)
        struct.pack_into('<3f', model, 0x78, *origin)
        for a, b in ((0x24, 2), (0x28, 4), (0x78, 12)):
            mmask[a:a+b] = b'\1'*b
        regions = [am.Region('model', MODEL, bytes(model), bytes(mmask), writable=False)]
        mesh_raw = bytearray(am.poison(0x20*len(meshes), 0x62))
        mesh_mask = bytearray(0x20*len(meshes))
        tri_raw = bytearray()
        c_meshes = (ShadowMesh*len(meshes))()
        keep = []
        for i, mesh in enumerate(meshes):
            base = 0x20*i
            struct.pack_into('<h', mesh_raw, base+2, mesh['texture'])
            struct.pack_into('<h', mesh_raw, base+0xa, len(mesh['tris']))
            struct.pack_into('<I', mesh_raw, base+0x18, TRIANGLES+len(tri_raw))
            for a, b in ((2, 2), (0xa, 2), (0x18, 4)):
                mesh_mask[base+a:base+a+b] = b'\1'*b
            tbytes = bytearray()
            for corners, idx in mesh['tris']:
                t = bytearray(am.poison(0x24, 0x63))
                t[0] = corners
                struct.pack_into('<4h', t, 2, *idx)
                tbytes += t
            c_tri = (ctypes.c_uint8*max(1, len(tbytes)))(*tbytes) if tbytes else (ctypes.c_uint8*1)()
            flat = [v for vert in mesh['verts'] for v in vert]
            c_v = (ctypes.c_float*len(flat))(*flat)
            keep += [c_tri, c_v]
            c_meshes[i] = ShadowMesh(len(mesh['tris']), mesh['texture'], ctypes.cast(c_tri, P(ctypes.c_uint8)),
                                     ctypes.cast(c_v, FP), len(mesh['verts']))
            tri_raw += tbytes
            vregion = am.defined_region(f'verts{i}', VERTICES + i*0x2bf20,
                                        struct.pack(f'<{len(flat)}f', *flat), writable=False)
            regions.append(vregion)
        regions.append(am.Region('meshes', MESHES, bytes(mesh_raw), bytes(mesh_mask), writable=False))
        if tri_raw:
            tmask = bytearray(len(tri_raw))
            for t in range(len(tri_raw)//0x24):
                tmask[t*0x24] = 1
                tmask[t*0x24+2:t*0x24+10] = b'\1'*8
            regions.append(am.Region('triangles', TRIANGLES, bytes(tri_raw), bytes(tmask), writable=False))
        regions += globals_region(world)
        log = []

        def wrapper(address, args):
            def stub(mm):
                log.append(('state', address, mm.argument(0) if args else 0))
                return 0
            return stub
        stubs = case.stubs(m)
        stubs.update(m.gl_stubs(log))
        stubs.update({STATE_UNTEX: wrapper(STATE_UNTEX, 1), STATE_DEPTH_OFF: wrapper(STATE_DEPTH_OFF, 0),
                      STATE_DEPTH_ON: wrapper(STATE_DEPTH_ON, 0)})
        r = m.execute(SHADOW, [hide_texture & 0xffffffff, hide_mesh & 0xffffffff, first & 0xffffffff,
                               end & 0xffffffff, z_offset & 0xffffffff], regions, stubs, ecx=MODEL, cleanup=0x14)
        host = case.host(world)
        gl = GLLog()
        lib.mu_pt_render_body_shadow(c_meshes, len(meshes), F3(*origin), hide_texture, hide_mesh, first, end, z_offset,
                                     ctypes.byref(host), ctypes.byref(gl.gl))
        theirs = [e for e in log]
        mismatch = None
        if vc.ok(r):
            if len(theirs) != len(gl.log) or not all(vc._same_call(a, b) for a, b in zip(theirs, gl.log)):
                mismatch = ('gl', theirs[:12], gl.log[:12])
            elif len(case.client_calls) != len(case.c_calls) or \
                    not all(vc._same_call(a, b) for a, b in zip(case.client_calls, case.c_calls)):
                mismatch = ('heights', case.client_calls[:4], case.c_calls[:4])
        report.add('shadow', vc.ok(r) and mismatch is None, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'],
                                                              'error': r['error'], 'checks': r['checks']})
        report.cover('shadow', f'world {world:#x}' + (' vertices' if any(e[0] == 'glVertex3fv' for e in log) else ''))
        if vc.ok(r):
            vs = [e for e in log if e[0] == 'glVertex3fv']
            if vs and world not in (0x91,):
                # negative control: the shadow at the origin's height instead of the terrain's
                negatives['shadow_origin_height'] += not same(vs[0][1][2], f32(origin[2] + 5.0))


def family_bone(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        matrix = [rf(rng, -2.0, 2.0) for _ in range(12)]
        for k in (3, 7, 11):
            matrix[k] = rf(rng, -20000.0, 20000.0)
        vec = [rf(rng, -300.0, 300.0) for _ in range(3)]
        translate = rng.choice([0, 1, 1, 2])
        scale = rf(rng, 0.0, 3.0)
        origin = [rf(rng, 0.0, 25600.0) for _ in range(3)]
        model = bytearray(am.poison(0x100, 0x51))
        mmask = bytearray(0x100)
        struct.pack_into('<f', model, 0x74, scale)
        struct.pack_into('<3f', model, 0x78, *origin)
        mmask[0x74:0x84] = b'\1'*16
        null = rng.random() < 0.05
        regions = [am.Region('model', MODEL, bytes(model), bytes(mmask), writable=False),
                   am.defined_region('matrix', MATRIX, struct.pack('<12f', *matrix), writable=False),
                   am.defined_region('in', INPUTS, struct.pack('<3f', *vec), writable=False),
                   am.defined_region('out', INPUTS+0x100, struct.pack('<3f', 7.0, 8.0, 9.0))]
        r = m.execute(TRANSFORM_POSITION, [0 if null else MATRIX, INPUTS, INPUTS+0x100, translate], regions, {},
                      ecx=MODEL, cleanup=0x10)
        out = F3(7.0, 8.0, 9.0)
        lib.mu_pt_transform_position(None if null else (ctypes.c_float*12)(*matrix), F3(*vec), out, translate,
                                     scale, F3(*origin))
        mismatch = None
        if vc.ok(r):
            theirs = struct.unpack('<3f', r['regions']['out'])
            if not all(same(a, b) for a, b in zip(theirs, out)):
                mismatch = ('out', theirs, list(out))
        report.add('bone', vc.ok(r) and mismatch is None, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'],
                                                            'error': r['error'], 'checks': r['checks']})
        report.cover('bone', 'null' if null else f'translate {bool(translate)}')
        if vc.ok(r) and translate and not null:
            t = struct.unpack('<3f', r['regions']['out'])
            negatives['bone_no_scale'] += not same(t[0], f32(f32(f32(f32(vec[0]*matrix[0]) + f32(vec[1]*matrix[1])) +
                                                            f32(vec[2]*matrix[2])) + matrix[3]) + origin[0])


BONE_TRANSFORM, CRT_MALLOC, CRT_FREE, HEAP = 0x06fce398, 0x019a4da0, 0x019a4d50, 0x2a800000


def family_visual(m, lib, rng, cases, report, negatives):
    lorencia_types = [0x38, 0x69, 0x69, 0x38, 0x32, 0x5a, 0x00, 0x96]
    tormenta_types = [2, 3, 4, 5, 9, 9, 0xbf, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0, 6, 0x1f]
    # NATIVE-JOINT-001: Dungeon, Devias, Noria
    other_types = {1: [0x3d, 0x3d, 0x3c, 0], 2: [0x64, 0x64, 0x63, 1], 3: [9, 0x23, 1, 0x11, 0x27, 0x27, 0x27, 2, 0x10]}
    worlds = [0, 0x8d, 0, 0x8d, 1, 2, 3, 3]
    for n in range(cases):
        world = worlds[n % len(worlds)]
        tormenta = world == 0x8d
        typ = rng.choice(tormenta_types if tormenta else lorencia_types if world == 0 else other_types[world])
        has_model = rng.random() > 0.05
        pos = [rf(rng, 0.0, 25600.0), rf(rng, 0.0, 25600.0), rf(rng, -100.0, 400.0)]
        angle = [rf(rng, -360.0, 360.0) for _ in range(3)]
        light = [rf(rng, 0.0, 1.5) for _ in range(3)]
        scale = rf(rng, 0.1, 3.0)
        world_time = f32(rng.choice([0.0, 39.0, rng.uniform(0, 3.0e6)]))
        rands = [rng.choice([0, 1, 50, 500, 501, 32, 8, rng.randrange(32768)]) for _ in range(48)]
        case = Case(rng, rand_values=rands)
        obj = bytearray(am.poison(0x400, 0x71))
        omask = bytearray(0x400)
        struct.pack_into('<i', obj, 0x5c, typ)
        struct.pack_into('<3f', obj, 0x158, *pos)
        struct.pack_into('<3f', obj, 0x164, *angle)
        struct.pack_into('<3f', obj, 0xec, *light)
        struct.pack_into('<f', obj, 0xa0, scale)
        for a, b in ((0x5c, 4), (0x158, 12), (0x164, 12), (0xec, 12), (0xa0, 4)):
            omask[a:a+b] = b'\1'*b
        objr = am.Region('object', OBJECTS, bytes(obj), bytes(omask))
        heap = am.Region('heap', HEAP, am.poison(0x10000, 0x33), bytes(0x10000))
        regions = [objr, heap] + globals_region(world, world_time)
        log = []
        brk = [HEAP]

        def malloc(mm):   # the C runtime heap (Noria 0x27's std::vector of bone names)
            size = (mm.argument(0) + 15) & ~15
            at = brk[0]
            brk[0] += max(size, 16)
            return at

        def free(mm):
            return 0

        def getter(mm):
            return (MODEL if has_model else 0), 4

        def container(mm):
            return 0x29500000, 0

        def bone_matrix(mm):
            name = read_msvc_string(mm, mm.argument(0))
            log.append(('bone', name, mm.argument(1)))
            return MATRIX, 8

        def transform(mm):
            a = [mm.argument(i) for i in range(4)]
            v = mm.floats(a[1], 3)
            out = [f32(v[0]*2.0 + 1.0), f32(v[1]*2.0 - 3.0), f32(v[2] + 10.0)]
            log.append(('transform', a[0], a[3]))
            mm.uc.mem_write(a[2], struct.pack('<3f', *out))   # a local of the caller
            return 0, 0x10

        def particle(mm):
            a = [mm.argument(i) for i in range(8)]
            log.append(('particle', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3), a[4],
                        from_bits(a[5]), a[6], a[7]))
            return 0

        def sprite(mm):
            a = [mm.argument(i) for i in range(9)]
            sheet = struct.unpack('<iif', mm.uc.mem_read(a[8], 12))
            log.append(('sprite', a[0], mm.floats(a[1], 3), from_bits(a[2]), mm.floats(a[3], 3), a[4],
                        from_bits(a[5]), a[6], a[7], list(sheet)))
            return 0

        def joint(mm):
            a = [mm.argument(i) for i in range(14)]
            log.append(('joint', a[0], mm.floats(a[1], 3), mm.floats(a[2], 3), mm.floats(a[3], 3), a[4], a[5],
                        from_bits(a[6]), a[7:14]))
            return 0

        def effect(mm):
            a = [mm.argument(i) for i in range(14)]
            log.append(('effect', a[0], hex(a[1]), hex(a[2]), hex(a[3]), a[4], a[5], a[6:14]))
            return 0
        stubs = case.stubs(m)
        stubs.update({MODEL_CONTAINER: container, MODEL_GET: getter, BONE_MATRIX: bone_matrix,
                      TRANSFORM_POSITION: transform, CREATE_PARTICLE: particle, CREATE_SPRITE: sprite,
                      CREATE_JOINT: joint, CREATE_EFFECT: effect, CRT_MALLOC: malloc, CRT_FREE: free})
        if world == 1:
            # Dungeon's case ends in the default branch (event-world hooks, world manager): static reading,
            # they answer no for world 1; the case jumps to the epilogue there
            stubs[0x017fcb5c] = jump_stub(0x017fccc1)
        if tormenta:
            if not has_model:
                continue   # the slot is reached after the model check of RenderObjectVisual
            # RenderObjectVisual's random draw happens before the world manager reaches the slot
            case.client_rand = 1
            r = m.execute(TORMENTA_VISUAL, [OBJECTS, MODEL], regions, stubs, ecx=0x29600000, cleanup=8)
        else:
            r = m.execute(VISUAL, [OBJECTS], regions, stubs)
        vo = VisualObject(0, typ, F3(*pos), F3(*angle), F3(*light), scale, f32(0.0), f32(0.0))
        clog = []

        def c_rand(ctx):
            v = case.rand_values[case.c_rand % len(case.rand_values)]
            case.c_rand += 1
            return v

        def c_has(ctx, o):
            return 1 if has_model else 0

        def c_bone(ctx, o, name, vin, vout):
            clog.append(('bone', name.decode(), 0))
            clog.append(('transform', MATRIX, 0))
            vout[0] = f32(vin[0]*2.0 + 1.0)
            vout[1] = f32(vin[1]*2.0 - 3.0)
            vout[2] = f32(vin[2] + 10.0)

        def c_particle(ctx, t, p, a, l, sub, sc, owner):
            clog.append(('particle', t, [p[0], p[1], p[2]], [a[0], a[1], a[2]], [l[0], l[1], l[2]], sub, sc,
                         object_address(owner), 0))

        def c_sprite(ctx, b, p, sc, l, owner, rot, blend, axes):
            clog.append(('sprite', b, [p[0], p[1], p[2]], sc, [l[0], l[1], l[2]], object_address(owner), rot, blend,
                         axes, [1, 1, 1.0]))

        def c_joint(ctx, b, p, a, sub, owner, sc):
            clog.append(('joint', b, [p[0], p[1], p[2]], [p[0], p[1], p[2]], [a[0], a[1], a[2]], sub,
                         object_address(owner), sc, [0xffffffff, 0, 0, 0xffffffff, 0, 0xffffffff, 0]))

        def c_bone_index(ctx, o, bone, vin, vout):
            clog.append(('transform', BONE_TRANSFORM + 0x30*bone, 0))
            vout[0] = f32(vin[0]*2.0 + 1.0)
            vout[1] = f32(vin[1]*2.0 - 3.0)
            vout[2] = f32(vin[2] + 10.0)

        def c_effect(ctx, t, p, a, l, sub, owner):
            clog.append(('effect', t, hex(OBJECTS+0x158), hex(OBJECTS+0x164), hex(OBJECTS+0xec), sub,
                         object_address(owner), [0xffffffff, 0, int(scale) & 0xffff, 0, 0, 0xffffffff, 0, 0]))
        fns = (RAND_FN(c_rand), HAS_MODEL_FN(c_has), BONE_FN(c_bone), VPARTICLE_FN(c_particle), VSPRITE_FN(c_sprite),
               VJOINT_FN(c_joint), VEFFECT_FN(c_effect))
        vh = VisualHost(None, *fns, world, world_time, BONE_INDEX_FN(c_bone_index))
        lib.mu_pt_object_visual(ctypes.byref(vo), ctypes.byref(vh))
        mismatch = None
        uninitialised = 0
        if vc.ok(r):
            theirs = [e for e in log]
            if typ == 0x38 and not tormenta:
                # the client transforms an uninitialised local: compare the sprite positions as the
                # C's stub output for (0,0,0) only when the client's input was the stack fill pattern
                fill = from_bits(0xa5a5a5a5)
                expect = [f32(fill*2.0 + 1.0), f32(fill*2.0 - 3.0), f32(fill + 10.0)]
                fixed = []
                for e in theirs:
                    if e[0] == 'sprite' and all(same(a, b) for a, b in zip(e[2], expect)):
                        uninitialised += 1
                        e = (e[0], e[1], [1.0, -3.0, 10.0]) + tuple(e[3:])
                    fixed.append(e)
                theirs = fixed
            if len(theirs) != len(clog) or not all(vc._same_call(a, b) for a, b in zip(theirs, clog)):
                mismatch = ('calls', theirs, clog)
            elif case.client_rand != case.c_rand:
                mismatch = ('rand calls', case.client_rand, case.c_rand)
            else:
                out = r['regions']['object']
                written = {'light': struct.unpack('<3f', out[0xec:0xf8])}
                if not all(same(a, b) for a, b in zip(written['light'], vo.light)):
                    mismatch = ('light', written['light'], list(vo.light))
                if typ == 0x69 and not tormenta and has_model and mismatch is None:
                    bl, bv = struct.unpack('<f', out[0xa8:0xac])[0], struct.unpack('<f', out[0xb0:0xb4])[0]
                    if not (same(bl, vo.blend_light) and same(bv, vo.blend_v)):
                        mismatch = ('blend', bl, bv, vo.blend_light, vo.blend_v)
        report.add('visual', vc.ok(r) and mismatch is None, {'case': n, 'world': world, 'type': typ,
                                                              'mismatch': mismatch, 'stopped': r['stopped'],
                                                              'error': r['error'], 'checks': r['checks']})
        kinds = sorted({e[0] for e in log if e[0] in ('particle', 'sprite', 'joint', 'effect')})
        report.cover('visual', f'{world:#x}/{typ:#x} ' + ('+'.join(kinds) or 'none'))
        negatives['visual_uninitialised_input_seen'] += uninitialised
        if vc.ok(r) and typ == 0x69 and not tormenta:
            ps = [e for e in log if e[0] == 'particle']
            if ps:
                # negative control: the second puff at Box04's drop (-20) instead of -80
                negatives['visual_second_drop'] += not same(ps[1][2][1], f32(f32(-20.0*2.0) - 3.0))


STRING_CTOR = 0x0094997e
BONE_NAMES = ['Bip01', 'Box01', 'Box03', 'Box04', 'Box10', 'Bip01 Head', 'Box04x', 'Box0', 'box04', 'Light01',
              'A very long bone name over sixteen']


def family_bone_lookup(m, lib, rng, cases, report, negatives):
    """The bone-matrix lookup 0x0129f18a(name, own) by name: the client's std::string constructor builds
    the name, its compare runs as client code over the model's bone records (0x8c bytes, name first)."""
    STRING = 0x2a100000
    BONES = 0x2a200000
    TEXT = 0x2a300000
    for n in range(cases):
        count = rng.randrange(0, 7)
        names = [rng.choice(BONE_NAMES) for _ in range(count)]
        wanted = rng.choice(BONE_NAMES[:6] + names if names else BONE_NAMES[:6])
        own = rng.choice([0, 1])
        own_buffer = rng.choice([0, 0x2a400000])
        has_model = rng.random() > 0.05
        has_bones = rng.random() > 0.05
        # the name string, built by the client's constructor
        text = am.defined_region('text', TEXT, wanted.encode().ljust(48, b'\0'), writable=False)   # strlen reads words
        r0 = m.execute(STRING_CTOR, [TEXT], [text, am.undefined_region('string', STRING, 0x20)], {}, ecx=STRING,
                       cleanup=4)
        if not vc.ok(r0) or len(wanted) >= 16:
            report.cover('bone_lookup', 'long name (heap string, not run)' if len(wanted) >= 16 else 'ctor failed')
            continue
        string = am.defined_region('string', STRING, r0['regions']['string'], writable=False)
        model = bytearray(am.poison(0x40, 0x13))
        mmask = bytearray(0x40)
        struct.pack_into('<h', model, 0x22, count)
        struct.pack_into('<I', model, 0x2c, BONES if has_bones else 0)
        mmask[0x22:0x24] = b'\1'*2
        mmask[0x2c:0x30] = b'\1'*4
        bones = bytearray(am.poison(max(1, count)*0x8c, 0x14))
        bmask = bytearray(max(1, count)*0x8c)
        for i, name in enumerate(names):
            raw = name.encode()[:31] + b'\0'
            bones[i*0x8c:i*0x8c+len(raw)] = raw
            bmask[i*0x8c:i*0x8c+32] = b'\1'*32
            bones[i*0x8c+len(raw):i*0x8c+32] = bytes(32-len(raw))
        obj = bytearray(am.poison(0x400, 0x15))
        omask = bytearray(0x400)
        struct.pack_into('<i', obj, 0x5c, 7)
        struct.pack_into('<I', obj, 0x318, own_buffer)
        omask[0x5c:0x60] = b'\1'*4
        omask[0x318:0x31c] = b'\1'*4
        regions = [string, am.Region('model', MODEL, bytes(model), bytes(mmask), writable=False),
                   am.Region('bones', BONES, bytes(bones), bytes(bmask), writable=False),
                   am.Region('object', BONE_OBJECT, bytes(obj), bytes(omask), writable=False)]

        def container(mm):
            return 0x29500000, 0

        def getter(mm):
            return (MODEL if has_model else 0), 4
        r = m.execute(BONE_MATRIX, [STRING, own], regions, {MODEL_CONTAINER: container, MODEL_GET: getter},
                      ecx=BONE_OBJECT, cleanup=8)
        arr = (ctypes.c_char_p*max(1, count))(*[x.encode()[:31] for x in names]) if count else None
        index = lib.mu_pt_find_bone(arr, count, wanted.encode()) if has_model and has_bones else -1
        if index < 0:
            expect = 0
        elif own and own_buffer:
            expect = own_buffer + 0x30*index
        else:
            expect = 0x06fce398 + 0x30*index
        mismatch = None
        if vc.ok(r) and (r['eax'] & 0xffffffff) != expect:
            mismatch = ('matrix', hex(r['eax']), hex(expect))
        report.add('bone_lookup', vc.ok(r) and mismatch is None, {'case': n, 'names': names, 'wanted': wanted,
                                                                   'mismatch': mismatch, 'stopped': r['stopped'],
                                                                   'error': r['error'], 'checks': r['checks']})
        report.cover('bone_lookup', 'found' if index >= 0 else 'not found')
        if vc.ok(r) and has_model and has_bones:
            # negative control: a case-insensitive prefix test
            loose = next((i for i, x in enumerate(names) if x.lower().startswith(wanted.lower()) or
                          wanted.lower().startswith(x.lower())), -1)
            negatives['bone_lookup_loose'] += loose != index


def read_msvc_string(mm, address):
    """MSVC std::string as the client's helper 0x0094997e builds it (short buffer or pointer)."""
    raw = bytes(mm.uc.mem_read(address, 0x20))
    for off in (0, 4):
        size_at = off + 16
        size = struct.unpack('<I', raw[size_at:size_at+4])[0]
        cap = struct.unpack('<I', raw[size_at+4:size_at+8])[0]
        if size < 64 and cap >= size:
            if cap < 16:
                return raw[off:off+size].decode('latin1')
            ptr = struct.unpack('<I', raw[off:off+4])[0]
            return bytes(mm.uc.mem_read(ptr, size)).decode('latin1')
    return raw.hex()


FAMILIES = [('create', family_create), ('wrapper', family_wrapper), ('move', family_move), ('wind', family_wind),
            ('render', family_render), ('sprite', family_sprite), ('sprite_create', family_sprite_create),
            ('sprite_render', family_sprite_render), ('shadow', family_shadow), ('bone', family_bone),
            ('bone_lookup', family_bone_lookup),
            ('visual', family_visual)]
HEAVY = {'sprite_create', 'sprite_render'}
NEGATIVES = ['create_fire1_large', 'wrapper_no_exempt', 'move_smoke_light_16', 'wind_unclamped',
             'render_fire_full_width', 'sprite_v_unflipped', 'sprite_sheet_rounded', 'sprite_render_no_alpha',
             'shadow_origin_height', 'bone_no_scale', 'bone_lookup_loose', 'visual_second_drop', 'visual_uninitialised_input_seen',
             'create_waterfall2_no_scene', 'move_chasellight_no_rise',
             'create_spark2_1_as_0', 'move_smoke2_no_half_height', 'render_drop_whole_sheet',
             'tail_initial_life_20', 'tail_glint_no_alpha', 'tail_fire_no_saved_colour', 'breath_no_direction']   # NATIVE-HELPERS-002


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=pins.TEXT.default_str())
    parser.add_argument('--data', default=pins.DATA.default_str())
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/particles/libclient_particles.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--heavy-cases', type=int, default=None, help='cases of the 1000-record families')
    parser.add_argument('--only', action='append')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = PtMachine(text, data)
    bodies = {name: {'start': hex(a), 'end': hex(b),
                     'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    report = Report()
    negatives = {k: 0 for k in NEGATIVES}
    timing = {}
    for name, family in FAMILIES:
        if args.only and name not in args.only:
            continue
        rng = random.Random(f'{args.seed}-{name}')
        cases = args.cases if name not in HEAVY else (args.heavy_cases or max(1, args.cases//5))
        start = time.time()
        family(m, lib, rng, cases, report, negatives)
        timing[name] = round(time.time()-start, 2)
    all_equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result = {'coverage': report.coverage, 'nan_pairs_equal': vc.NAN_COUNT[0], 'text_sha256': am.TEXT_SHA256,
              'data_sha256': am.DATA_SHA256, 'bodies': bodies, 'families': report.families,
              'negative_controls': negatives, 'seconds': timing, 'all_equal': all_equal}
    summary = {k: f"{v['equal']}/{v['cases']}" for k, v in report.families.items()}
    print(json.dumps({'summary': summary, 'negative_controls': negatives, 'seconds': timing,
                      'all_equal': all_equal}, indent=1))
    for k, v in report.families.items():
        if v['first_failures']:
            print(k, json.dumps(v['first_failures'][:2], default=str)[:3000])
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, default=str))
    return 0 if all_equal else 1


if __name__ == '__main__':
    sys.exit(main())
