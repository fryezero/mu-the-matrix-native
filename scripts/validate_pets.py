#!/usr/bin/env python3
"""Compare reconstructed/pets with the client's pet process (NATIVE-HELPERS-002, pets).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case).
The authored C (reconstructed/pets, libclient_pets) runs the same steps through
ctypes with Python host callbacks that give the same answers as the client-side
stubs. Compared after every step: the rand() state and call count, the pet
object's fields (+0x04..+0x40), the modelled bytes of its OBJECT, the pending
pick-up global 0x01cf1028 and the ordered log of host calls.

Sections:

* data     the petdata.bmd loader 0x00eb0a7d (file stubs; the checksum
           0x00976895 and BuxConvert 0x00976855 run as client code) on valid,
           corrupted and missing files and, privately, the installed file;
* create   PetObject::Create 0x00eac071 (operator new stubbed; the OBJECT
           constructor 0x0129e792 runs as client code);
* session  Create, then PetObject::Update 0x00eac414 (FadeAlpha, the model tick
           0x00eac84d, the move 0x00eac902 with both move types and the five
           collector states, the zen search 0x00eac65a over 1000 ground items,
           the pick-up request, the sound 0x00eaeacf) and PetObject::Render
           0x00eac4e0 (frustum, RenderObject, the visuals 0x00eaeaf8 of the
           Demon, Spirit of Guardian, Rudolph, Panda, Skeleton and the PC-room
           copies) over many steps with moving owners and advancing clocks.

Client code includes everything these reach except the stubs: rand() (MSVC
LCG), GetTickCount and timeGetTime (scripted clocks), TestFrustrum2D, the model
container and getter, the animation tick, RenderObject, the pose builder,
CreateSprite, CreateParticle, CreateEffect, the buff lookup 0x01295ade, the
pet-slot getter 0x0129de01, the pet list helpers 0x0096a485 / 0x00a8cbcd,
PlayBuffer, the packet builder 0x00d51b91.. (the pick-up request) and the file
and C-runtime helpers of the loader. FadeAlpha, CreateAngle, TurnAngle2,
AngleMatrix, VectorRotate, TransformPosition, the bone origin 0x012b6d2a, the
sin/cos/sqrt/log wrappers and the C runtime they call run as client code. The
loader's BuxCode (0x01cf0448, outside the captured section) is declared with
the bytes fc cf ab. Negative controls plant mistakes into the inputs or the
library and must be detected.
"""
import argparse
import ctypes
import hashlib
import json
import os
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
LIB = ROOT/f'reconstructed/pets/libclient_pets.{SUFFIX}'
f32, bits, from_bits, same, same_log, mix = vh.f32, vh.bits, vh.from_bits, vh.same, vh.same_log, vh.mix

OBJ = 0x3d8
CHAR_BASE, CHAR_STRIDE, CHAR_SIZE, CHAR_OBJ = vh.CHAR_BASE, vh.CHAR_STRIDE, vh.CHAR_SIZE, vh.CHAR_OBJ
PET, PET_OBJ, INFO, PROCESS = 0x28000000, 0x28001000, 0x28002000, 0x28003000
FILE_BUF, CM = 0x28010000, 0x29000000
MODEL_BASE, CONTAINER = vh.MODEL_BASE, vh.CONTAINER
ITEMS, ITEM_STRIDE, ITEM_COUNT = 0x0b4780dc, 0x560, 1000
HERO_PTR, CM_PTR, PENDING, SCENE, WORLD_TIME = 0x0a39d754, 0x01d1df18, 0x01cf1028, 0x01d1df70, 0x06fce370
BONES, BONE_COUNT = 0x06fce398, 0x48
BUX, HWND = 0x01cf0448, 0x06fc9c94
TRIG_FLAG, CRT_MATH_MODE, COOKIE = vh.TRIG_FLAG, vh.CRT_MATH_MODE, vh.COOKIE

RAND, FRUSTUM, MODEL_CONTAINER, MODEL_GET = 0x01989721, 0x016ccce7, 0x00966cc4, 0x00eaa8cf
ANIMATE, KILL, PARTICLE, BUFF, RENDER_OBJECT = 0x012b4dd3, 0x009b0451, 0x0168fafd, 0x01295ade, 0x016d4fe4
SPRITE, EFFECT, POSE, ALT_PET, REMEMBER, CLEAR = 0x01692eb7, 0x013c0eaa, 0x012b5064, 0x0129de01, 0x0096a485, 0x00a8cbcd
SOUND, NEW = 0x00a6ac96, 0x0191ba7b
PKT_CTOR, PKT_HEAD, PKT_BYTE, PKT_SEND, PKT_DTOR = 0x00d51b91, 0x00d51baf, 0x0095c204, 0x00d51d4f, 0x00d51ba6
MEMSET, SPRINTF, FOPEN, MALLOC, FREAD, FCLOSE, MEMCPY, FREE = (0x0194cd00, 0x009619dd, 0x01988f83, 0x0191bab9,
                                                              0x01989230, 0x01988c95, 0x0194c200, 0x0191bac2)
LOGGER = 0x01206598
IAT_TICK, IAT_TIME, IAT_MSGBOX, IAT_SENDMSG = 0x01a7c49c, 0x01a7c9a4, 0x01a7c830, 0x01a7c83c

LOAD, CREATE, UPDATE, RENDER = 0x00eb0a7d, 0x00eac071, 0x00eac414, 0x00eac4e0

BODIES = {
    'load': (0x00eb0a7d, 0x00eb0c52), 'info_map': (0x00eb0c52, 0x00eb0cdb), 'info_find': (0x00eb0cdb, 0x00eb0d30),
    'update_pets': (0x00eb0d64, 0x00eb0dee), 'render_pets': (0x00eb0dee, 0x00eb0e78),
    'create_pet': (0x00eb0e78, 0x00eb1015), 'delete_pet': (0x00eb1015, 0x00eb1203),
    'checksum': (0x00976895, 0x0097694a), 'bux': (0x00976855, 0x00976895), 'create': (0x00eac071, 0x00eac414),
    'update': (0x00eac414, 0x00eac4e0), 'render': (0x00eac4e0, 0x00eac609), 'find_target': (0x00eac65a, 0x00eac81e),
    'interval': (0x00eac81e, 0x00eac84d), 'model_tick': (0x00eac84d, 0x00eac902), 'move': (0x00eac902, 0x00eaeacf),
    'pick_sound': (0x00eaeacf, 0x00eaeaf8), 'visuals': (0x00eaeaf8, 0x00eb0847), 'speed': (0x00eb08c2, 0x00eb091e),
    'elapsed': (0x00eb091e, 0x00eb0933), 'release': (0x00eabf9b, 0x00eac00a),
}

PROBES = {
    0x00eacb4e: 'fly: teleport', 0x00eaccd1: 'fly: turn', 0x00eacef7: 'fly: speed',
    0x00ead006: 'collector: helper flags', 0x00ead036: 'collector: found -> 1', 0x00ead042: 'collector: not hero',
    0x00ead0ff: 'collector: unicorn height', 0x00ead164: 'collector: skeleton height',
    0x00ead350: 'collector: far teleport', 0x00ead509: 'state 0: follow', 0x00ead5ba: 'state 0: circle',
    0x00ead7ac: 'state 0: turn', 0x00eada1b: 'state 1: no target', 0x00eadbb3: 'state 1: turn',
    0x00eade87: 'state 1 -> 2', 0x00eadf00: 'state 2 -> 3', 0x00eae085: 'state 2: pick',
    0x00eae08e: 'state 2: send', 0x00eae593: 'state 3 -> 0', 0x00eae5bc: 'state 4: follow',
    0x00eac7a5: 'search: found', 0x00eac498: 'update: owner gone',
    0x00eaeb70: 'visuals: demon', 0x00eaefe9: 'visuals: spirit', 0x00eaf670: 'visuals: rudolph',
    0x00eaf9b7: 'visuals: rudolph effect', 0x00eafc67: 'visuals: panda', 0x00eb06a0: 'visuals: skeleton particle',
}

PET_ITEMS = [0x1a40, 0x1a41, 0x1a43, 0x1a50, 0x1a6a, 0x1a7b, 0x1bd5, 0x1bd6, 0x1a44]


# --------------------------------------------------------------------------
# The library (ctypes).

Obj = vh.Obj
V3 = ctypes.c_float * 3
P = ctypes.c_void_p


class Info(ctypes.Structure):
    _fields_ = [('seq', ctypes.c_int32), ('item', ctypes.c_int32), ('byte_08', ctypes.c_uint8),
                ('byte_09', ctypes.c_uint8), ('slot', ctypes.c_uint8), ('move', ctypes.c_uint8),
                ('range', ctypes.c_float), ('follow', ctypes.c_uint8), ('pad_11', ctypes.c_uint8 * 3),
                ('scale', ctypes.c_float), ('blend_mesh', ctypes.c_int32), ('speed', ctypes.c_float * 5)]


class Owner(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('kind', ctypes.c_uint8), ('action', ctypes.c_uint16),
                ('key', ctypes.c_int16), ('position', V3), ('angle', V3), ('scale', ctypes.c_float),
                ('buff_12', ctypes.c_uint8), ('alt_pet', ctypes.c_int32)]


class Ground(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('type', ctypes.c_int32), ('position', V3)]


class Inputs(ctypes.Structure):
    _fields_ = [('scene', ctypes.c_int32), ('hero', ctypes.c_int32), ('helper_type', ctypes.c_int32),
                ('helper_92', ctypes.c_uint8), ('helper_93', ctypes.c_uint8), ('world_time', ctypes.c_float),
                ('items', ctypes.POINTER(Ground)), ('before_items', ctypes.c_int32)]


TIME_FN = ctypes.CFUNCTYPE(ctypes.c_uint32, P)
HAS_MODEL_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_int32)
ANIMATE_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_float)
KILL_FN = ctypes.CFUNCTYPE(None, P, P)
INT_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32)


class Host(ctypes.Structure):
    _fields_ = [('context', P), ('tick', TIME_FN), ('time', TIME_FN), ('has_model', HAS_MODEL_FN),
                ('animate', ANIMATE_FN), ('kill', KILL_FN), ('pickup', INT_FN), ('sound', INT_FN)]


class Pet(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int32), ('owner', ctypes.c_int32), ('object', Obj), ('item', ctypes.c_int32),
                ('created', ctypes.c_uint32), ('target_item', ctypes.c_int32), ('target', V3),
                ('has_target', ctypes.c_int32), ('pick_tick', ctypes.c_uint32), ('wait_tick', ctypes.c_uint32),
                ('state', ctypes.c_int32), ('angle1', ctypes.c_float), ('angle2', ctypes.c_float),
                ('info', ctypes.POINTER(Info))]


class Pets(ctypes.Structure):
    _fields_ = [('rand_state', ctypes.c_uint32), ('rand_calls', ctypes.c_uint64), ('pending_pickup', ctypes.c_int32),
                ('table', Info * 32), ('list', Pet * 32), ('count', ctypes.c_int32),
                ('owners', ctypes.POINTER(Owner)), ('owner_count', ctypes.c_int32), ('host', Host)]


FRUSTUM_FN = ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.c_float, ctypes.c_float, ctypes.c_float)
DRAW_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)
POSE_FN = ctypes.CFUNCTYPE(None, P, P, ctypes.c_int32, ctypes.c_int)
MATRIX_FN = ctypes.CFUNCTYPE(P, P, ctypes.c_int32, ctypes.c_int32)
SPRITE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, ctypes.c_float, P, P)
PARTICLE_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, P, P, ctypes.c_int32, ctypes.c_float, P, ctypes.c_int32)
EFFECT_FN = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, P, P, P, P)


class RenderHost(ctypes.Structure):
    _fields_ = [('context', P), ('frustum', FRUSTUM_FN), ('draw_object', DRAW_FN), ('pose', POSE_FN),
                ('bone_matrix', MATRIX_FN), ('sprite', SPRITE_FN), ('particle', PARTICLE_FN), ('effect', EFFECT_FN),
                ('remember', INT_FN)]


def load_library(path=LIB):
    if not Path(path).exists():
        subprocess.run(['make', '-C', str(Path(path).parent)], check=True, capture_output=True)
    lib = ctypes.CDLL(str(path))
    PP, PE = ctypes.POINTER(Pets), ctypes.POINTER(Pet)
    lib.mu_pets_init.argtypes = [PP, ctypes.c_uint32, ctypes.POINTER(Owner), ctypes.c_int32, ctypes.POINTER(Host)]
    lib.mu_pet_checksum.argtypes = [P, ctypes.c_uint32, ctypes.c_uint16]
    lib.mu_pet_checksum.restype = ctypes.c_uint32
    lib.mu_pet_data_load.argtypes = [P, ctypes.c_size_t, P]
    lib.mu_pet_data_load.restype = ctypes.c_int
    lib.mu_pet_create_object.argtypes = [PP, PE, ctypes.c_int32, ctypes.c_int32, P, ctypes.c_int32, ctypes.c_int32]
    lib.mu_pet_create_object.restype = ctypes.c_int
    lib.mu_pet_update.argtypes = [PP, PE, ctypes.POINTER(Inputs)]
    lib.mu_pet_update.restype = ctypes.c_int
    lib.mu_pet_render.argtypes = [PP, PE, ctypes.POINTER(Inputs), ctypes.POINTER(RenderHost)]
    lib.mu_pet_render.restype = ctypes.c_int
    lib.mu_pet_visuals.argtypes = [PP, PE, ctypes.POINTER(Inputs), ctypes.POINTER(RenderHost), ctypes.c_uint32]
    lib.mu_pet_visuals.restype = ctypes.c_int
    lib.mu_hp_object_init.argtypes = [P]
    return lib


# --------------------------------------------------------------------------
# Machine.

class Machine(vh.Machine):
    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_READ, UC_PROT_EXEC
        self.iat = {}
        for slot in (IAT_TICK, IAT_TIME, IAT_MSGBOX, IAT_SENDMSG):
            target = struct.unpack('<I', data[slot - am.DATA_BASE:slot - am.DATA_BASE + 4])[0]
            self.iat[slot] = target
            page = target & ~0xfff
            try:
                self.uc.mem_map(page, am.PAGE, UC_PROT_READ | UC_PROT_EXEC)
                self.uc.mem_write(page, b'\xcc'*am.PAGE)
            except Exception:
                pass


def body_digests(text):
    return {name: hashlib.sha256(text[lo - am.TEXT_BASE:hi - am.TEXT_BASE]).hexdigest()[:16]
            for name, (lo, hi) in BODIES.items()}


def char_addr(k):
    return CHAR_BASE + k*CHAR_STRIDE


def owner_obj_addr(k):
    return 0 if k < 0 else char_addr(k) + CHAR_OBJ


def owner_index(addr):
    return vh.owner_index(addr)


def bone_matrix_values(case, bone):
    """Synthetic BoneTransform rows (3x4) for a bone."""
    out = []
    for i in range(12):
        m = mix(bone * 31 + i, case['bone_salt'])
        if i in (3, 7, 11):
            out.append(f32(float(m % 4001) - 2000.0 + (case['origin'][i // 4] if case.get('world_bones') else 0)))
        else:
            out.append(f32((float(m % 2001) - 1000.0) / 1000.0))
    return out


def test_frustum(case, x, y, r):
    return 1 if mix(bits(x), bits(y) ^ bits(r) ^ case['frustum_salt']) % 5 else 0


def info_bytes(info):
    return bytes(info)


# --------------------------------------------------------------------------
# Client memory and stubs for a case.

class Client:
    def __init__(self, m, case):
        self.m, self.case = m, case
        self.rand_state, self.rand_calls = case['seed'] & 0xffffffff, 0
        self.log = []
        n = len(case['owners'])
        self.chars = [am.undefined_region(f'char{k}', char_addr(k), CHAR_SIZE) for k in range(n)]
        self.pet = am.undefined_region('pet', PET, 0x50)
        self.obj = am.undefined_region('obj', PET_OBJ, OBJ)
        self.info = am.undefined_region('info', INFO, 0x30)
        self.models = am.undefined_region('models', MODEL_BASE, 0x1000)
        self.args = am.undefined_region('args', vh.ARGS, 0x100)
        self.cm = am.undefined_region('cm', CM, 0x1b58 + 16*0x12c)
        self.items = am.undefined_region('items', ITEMS - ITEM_STRIDE, (ITEM_COUNT + 1)*ITEM_STRIDE)
        self.items.define(ITEMS - ITEM_STRIDE, struct.pack('<i', case['before_items']))
        self.bones = am.defined_region('bones', BONES, b''.join(struct.pack('<12f', *bone_matrix_values(case, b))
                                                               for b in range(BONE_COUNT)), writable=False)
        self.pending = am.defined_region('pending', PENDING, struct.pack('<i', -1))
        self.tick_n = self.time_n = 0
        self.packet = []
        self.object_given = False
        self.heap = am.defined_region('heap', vh.HEAP_BASE, am.poison(0x10000, 0x33))
        self.heap_next = vh.HEAP_BASE

    def set_owners(self, owners):
        for k, o in enumerate(owners):
            r = self.chars[k]
            base = r.base + CHAR_OBJ
            r.define(base + 0x00, bytes([o['live']]))
            r.define(base + 0x3b, bytes([o['kind']]))
            r.define(base + 0x2a, struct.pack('<H', o['action']))
            r.define(base + 0x158, struct.pack('<3f', *o['position']))
            r.define(base + 0x164, struct.pack('<3f', *o['angle']))
            r.define(base + 0xa0, struct.pack('<f', o['scale']))
            r.define(r.base + 0x3e, struct.pack('<h', o['key']))

    def set_items(self, items):
        for i, it in enumerate(items):
            base = ITEMS + i*ITEM_STRIDE
            if it is None:   # an empty slot: dead, type 0
                self.items.define(base + 0x11c, b'\0')
                self.items.define(base, struct.pack('<i', 0))
                continue
            self.items.define(base + 0x11c, bytes([it['live']]))
            self.items.define(base + 0x127, bytes([it['visible']]))
            self.items.define(base, struct.pack('<i', it['type']))
            self.items.define(base + 0x274, struct.pack('<3f', *it['position']))

    def set_cm(self, slot, helper_type, b92, b93):
        base = CM + 0x1b58 + slot*0x12c
        self.cm.define(base + 0x10, struct.pack('<i', helper_type))
        self.cm.define(base + 0x92, bytes([b92, b93]))

    def globals(self, s):
        hero = s['hero']
        return [am.defined_region('scene', SCENE, struct.pack('<i', s['scene']), writable=False),
                am.defined_region('hero', HERO_PTR, struct.pack('<I', char_addr(hero) if hero >= 0 else 0x2f000000),
                                  writable=False),
                am.defined_region('cm-ptr', CM_PTR, struct.pack('<I', CM), writable=False),
                am.defined_region('world-time', WORLD_TIME, struct.pack('<f', s['world_time']), writable=False),
                am.defined_region('trig-flag', TRIG_FLAG, struct.pack('<I', 1), writable=False),
                am.defined_region('crt-mode', CRT_MATH_MODE, struct.pack('<I', self.case.get('crt_mode', 1)),
                                  writable=False),
                am.defined_region('cookie', COOKIE, struct.pack('<I', 0xbb40e64e), writable=False)]

    def regions(self, s):
        return [*self.globals(s), *self.chars, self.pet, self.obj, self.info, self.models, self.args, self.cm,
                self.items, self.bones, self.pending, self.heap]

    def label(self, addr):
        if addr == PET_OBJ:
            return 'pet'
        if addr == 0:
            return None
        k = owner_index(addr)
        return ('owner', k) if k >= 0 else ('?', addr)

    def stubs(self, s):
        case, log, m = self.case, self.log, self.m

        def rand(m):
            self.rand_state = (self.rand_state * 214013 + 2531011) & 0xffffffff
            self.rand_calls += 1
            return (self.rand_state >> 16) & 0x7fff

        def tick(m):
            v = (s['clock'] + 3*self.tick_n) & 0xffffffff
            self.tick_n += 1
            return v

        def now(m):
            v = (s['clock'] + 5*self.time_n + 1) & 0xffffffff
            self.time_n += 1
            return v

        def frustum(m):
            x, y, r = m.float_argument(0), m.float_argument(1), m.float_argument(2)
            log.append(('frustum', x, y, r))
            return test_frustum(case, x, y, r)

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
            log.append(('animate', self.label(o), action, m.float_argument(3), frame,
                        m.argument(1) == o + 0xd4 and m.argument(2) == o + 0x2c and m.argument(4) == o + 0x158 and
                        m.argument(5) == o + 0x164))
            return 0, 0x18

        def kill(m):
            log.append(('kill', self.label(m.ecx())))
            return 0

        def buff(m):
            k = owner_index(m.ecx() - 0x358)
            assert m.argument(0) == 0x12 and k >= 0
            return case['owners'][k]['buff_12'], 4

        def alt_pet(m):
            k = (m.ecx() - CHAR_BASE)//CHAR_STRIDE
            return case['owners'][k]['alt_pet'] & 0xffffffff

        def render_object(m):
            log.append(('object', self.label(m.argument(0)), tuple(m.argument(i) for i in range(1, 6))))
            return 0

        def pose(m):
            model = m.ecx()
            a = [m.argument(i) for i in range(8)]
            ang = m.read_floats(a[4], 3)
            head = m.read_floats(a[5], 3)
            if a[7]:
                extra = m.read_floats(model + 0x78, 3)
            else:
                extra = m.read_floats(model + 0x74, 1)
            log.append(('pose', a[0] == BONES, from_bits(a[1]), from_bits(a[2]), a[3], ang, head, a[6], a[7], extra))
            return 0, 0x20

        def sprite(m):
            pos, light = m.read_floats(m.argument(1), 3), m.read_floats(m.argument(3), 3)
            sheet = m.argument(8)
            sv = (m.read32(sheet), m.read32(sheet + 4), m.read_floats(sheet + 8, 1)[0])
            log.append(('sprite', m.argument(0), pos, m.float_argument(2), light, self.label(m.argument(4)),
                        m.argument(5), m.argument(6), m.argument(7), sv))
            return 0

        def particle(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            log.append(('particle', m.argument(0), pos, ang, light, m.argument(4), m.float_argument(5),
                        self.label(m.argument(6)), m.argument(7)))
            return 0

        def effect(m):
            pos, ang, light = (m.read_floats(m.argument(i), 3) for i in (1, 2, 3))
            rest = tuple(m.argument(i) for i in range(4, 14))
            log.append(('effect', m.argument(0), pos, ang, light, rest))
            return 0

        def remember(m):
            assert m.ecx() == PET + 0x44
            log.append(('remember', m.read32(m.argument(0))))
            return 0, 4

        def clear(m):
            assert m.ecx() == PET + 0x44
            log.append(('remember', 0xffffffff))
            return 0

        def sound(m):
            log.append(('sound', m.argument(0), m.argument(1), m.argument(2)))
            return 0

        def pkt_ctor(m):
            self.packet = []
            return m.ecx()

        def pkt_head(m):
            self.packet.append(('head', m.argument(0) & 0xff, m.argument(1) & 0xff))
            return m.ecx(), 8

        def pkt_byte(m):
            self.packet.append(m.argument(0) & 0xff)
            return m.ecx(), 4

        def pkt_send(m):
            log.append(('pickup', tuple(self.packet)))
            return 0, 8

        def pkt_dtor(m):
            return 0

        def new(m):
            size = m.argument(0)
            if size == OBJ and not self.object_given:
                self.object_given = True
                return PET_OBJ
            addr = (self.heap_next + 15) & ~15
            self.heap_next = addr + size
            assert self.heap_next <= vh.HEAP_BASE + 0x10000
            return addr

        def memset(m):
            dst, value, count = m.argument(0), m.argument(1), m.argument(2)
            m.write(dst, bytes([value & 0xff])*count)
            return dst

        stubs = {MEMSET: memset, RAND: rand, m.iat[IAT_TICK]: tick, m.iat[IAT_TIME]: now, FRUSTUM: frustum,
                 MODEL_CONTAINER: container, MODEL_GET: model_get, ANIMATE: animate, KILL: kill, BUFF: buff,
                 ALT_PET: alt_pet, RENDER_OBJECT: render_object, POSE: pose, SPRITE: sprite, PARTICLE: particle,
                 EFFECT: effect, REMEMBER: remember, CLEAR: clear, SOUND: sound, PKT_CTOR: pkt_ctor,
                 PKT_HEAD: pkt_head, PKT_BYTE: pkt_byte, PKT_SEND: pkt_send, PKT_DTOR: pkt_dtor, NEW: new}
        return stubs

    # the pet object's fields
    def write_pet(self, pet):
        r = self.pet
        r.define(PET + 0x00, struct.pack('<I', 0x1aadaec))
        r.define(PET + 0x04, struct.pack('<I', char_addr(pet['owner']) if pet['owner'] >= 0 else 0))
        r.define(PET + 0x08, struct.pack('<I', PET_OBJ if pet['has_object'] else 0))
        r.define(PET + 0x0c, struct.pack('<i', pet['item']))
        r.define(PET + 0x10, struct.pack('<I', pet['created']))
        r.define(PET + 0x14, struct.pack('<i', pet['target_item']))
        r.define(PET + 0x18, struct.pack('<3f', *pet['target']))
        r.define(PET + 0x24, struct.pack('<i', pet['has_target']))
        r.define(PET + 0x28, struct.pack('<II', pet['pick_tick'], pet['wait_tick']))
        r.define(PET + 0x34, struct.pack('<i', pet['state']))
        r.define(PET + 0x38, struct.pack('<2f', pet['angle1'], pet['angle2']))
        r.define(PET + 0x40, struct.pack('<I', INFO))

    def read_pet(self, raw):
        def i32(o):
            return struct.unpack('<i', raw[o:o+4])[0]

        def u32(o):
            return struct.unpack('<I', raw[o:o+4])[0]
        owner = u32(4)
        return {'owner': (owner - CHAR_BASE)//CHAR_STRIDE if owner else -1, 'item': i32(0xc), 'created': u32(0x10),
                'target_item': i32(0x14), 'target': struct.unpack('<3f', raw[0x18:0x24]), 'has_target': i32(0x24),
                'pick_tick': u32(0x28), 'wait_tick': u32(0x2c), 'state': i32(0x34),
                'angle1': struct.unpack('<f', raw[0x38:0x3c])[0], 'angle2': struct.unpack('<f', raw[0x3c:0x40])[0]}


# --------------------------------------------------------------------------
# Native side.

class Native:
    def __init__(self, lib, case, plant=None):
        self.lib, self.case, self.plant = lib, case, plant
        self.log = []
        n = len(case['owners'])
        self.owners = (Owner * n)()
        self.p = Pets()
        self.host = self._host()
        lib.mu_pets_init(ctypes.byref(self.p), case['seed'] & 0xffffffff, self.owners, n, ctypes.byref(self.host))
        self.pet = Pet()
        self.ground = (Ground * ITEM_COUNT)()
        self.matrices = {}
        self.s = None
        self.tick_n = self.time_n = 0

    def label(self, addr):
        if addr == ctypes.addressof(self.pet.object):
            return 'pet'
        return None if not addr else ('?', addr)

    def set_owners(self, owners):
        for k, o in enumerate(owners):
            w = self.owners[k]
            w.live, w.kind, w.action, w.key = o['live'], o['kind'], o['action'], o['key']
            for i in range(3):
                w.position[i] = o['position'][i]
                w.angle[i] = o['angle'][i]
            w.scale = o['scale']
            w.buff_12 = o['buff_12']
            w.alt_pet = o['alt_pet']

    def set_items(self, items):
        for i, it in enumerate(items):
            g = self.ground[i]
            if it is None:
                g.live, g.type = 0, 0
                continue
            g.live, g.visible, g.type = it['live'], it['visible'], it['type']
            for k in range(3):
                g.position[k] = it['position'][k]
            if self.plant == 'zen' and it['type'] == 0x1c0f:
                g.type = 0x1c0e

    def _host(self):
        case, log = self.case, self.log

        def tick(ctx):
            v = (self.s['clock'] + 3*self.tick_n) & 0xffffffff
            self.tick_n += 1
            return v

        def now(ctx):
            v = (self.s['clock'] + 5*self.time_n + 1) & 0xffffffff
            self.time_n += 1
            return v

        def has_model(ctx, model):
            return 0 if model in case.get('missing_models', ()) else 1

        def animate(ctx, o, model, speed):
            ob = Obj.from_address(o)
            log.append(('animate', self.label(o), ob.action, f32(speed), f32(ob.frame), True))

        def kill(ctx, o):
            log.append(('kill', self.label(o)))

        def pickup(ctx, item):
            log.append(('pickup', (('head', 0xc1, 0), (item >> 8) & 0xff, item & 0xff)))

        def sound(ctx, s):
            log.append(('sound', s, 0, 0))

        self.callbacks = [TIME_FN(tick), TIME_FN(now), HAS_MODEL_FN(has_model), ANIMATE_FN(animate), KILL_FN(kill),
                          INT_FN(pickup), INT_FN(sound)]
        h = Host()
        h.tick, h.time, h.has_model, h.animate, h.kill, h.pickup, h.sound = self.callbacks
        return h

    def render_host(self):
        case, log = self.case, self.log

        def v3(p):
            return tuple(f32(x) for x in (ctypes.c_float*3).from_address(p))

        def frustum(ctx, x, y, r):
            log.append(('frustum', f32(x), f32(y), f32(r)))
            return test_frustum(case, f32(x), f32(y), f32(r))

        def draw(ctx, o, a1, a2, a3, a4, a5):
            log.append(('object', self.label(o), tuple(x & 0xffffffff for x in (a1, a2, a3, a4, a5))))

        def pose(ctx, o, model, translate):
            ob = Obj.from_address(o)
            extra = tuple(f32(x) for x in ob.position) if translate else (f32(ob.scale),)
            log.append(('pose', True, f32(ob.frame), f32(ob.prior_frame), ob.prior_action, tuple(ob.angle),
                        tuple(ob.head_angle), 0, translate, extra))

        def matrix(ctx, model, bone):
            if bone not in self.matrices:
                self.matrices[bone] = (ctypes.c_float*12)(*bone_matrix_values(case, bone))
            return ctypes.addressof(self.matrices[bone])

        def sprite(ctx, bitmap, p, scale, light, o):
            log.append(('sprite', bitmap, v3(p), f32(scale), v3(light), self.label(o), 0, 0, 4, (1, 1, 1.0)))

        def particle(ctx, bitmap, p, a, l, subtype, scale, owner, arg8):
            log.append(('particle', bitmap, v3(p), v3(a), v3(l), subtype, f32(scale), self.label(owner or 0), arg8))

        def effect(ctx, typ, p, a, l, args):
            rest = tuple(x & 0xffffffff for x in (ctypes.c_int32*10).from_address(args))
            log.append(('effect', typ, v3(p), v3(a), v3(l), rest))

        def remember(ctx, kind):
            log.append(('remember', kind & 0xffffffff))

        self.render_callbacks = [FRUSTUM_FN(frustum), DRAW_FN(draw), POSE_FN(pose), MATRIX_FN(matrix),
                                 SPRITE_FN(sprite), PARTICLE_FN(particle), EFFECT_FN(effect), INT_FN(remember)]
        r = RenderHost()
        (r.frustum, r.draw_object, r.pose, r.bone_matrix, r.sprite, r.particle, r.effect,
         r.remember) = self.render_callbacks
        return r

    def read_pet(self):
        q = self.pet
        return {'owner': q.owner, 'item': q.item, 'created': q.created, 'target_item': q.target_item,
                'target': tuple(q.target), 'has_target': q.has_target, 'pick_tick': q.pick_tick,
                'wait_tick': q.wait_tick, 'state': q.state, 'angle1': q.angle1, 'angle2': q.angle2}


# --------------------------------------------------------------------------
# Cases.

def random_owner(rng, k):
    return {'live': rng.choice([1, 1, 1, 1, 1, 0]), 'kind': rng.choice([1, 1, 1, 1, 2]),
            'action': rng.choice([0, 1, 0x20, 0x31, 0x32, 0x90, 0x133, 0x13b, 0x141, 0x142, 0x148, 0x160, 0x185,
                                  0x186]),
            'key': rng.randrange(-2, 2000), 'position': [f32(rng.uniform(3000, 20000)), f32(rng.uniform(3000, 20000)),
                                                       f32(rng.uniform(0, 400))],
            'angle': [0.0, 0.0, f32(rng.uniform(0, 360))], 'scale': f32(rng.choice([1.0, 1.0, 1.2, 0.9])),
            'buff_12': rng.choice([0, 0, 0, 1]), 'alt_pet': rng.choice([-1, -1, -1, -1, 0, 3])}


def random_info(rng, item):
    info = Info()
    info.seq = rng.randrange(32)
    info.item = item - 0x1a00
    info.byte_08, info.byte_09 = rng.choice([0xff, 0]), rng.choice([0xff, 0])
    info.slot = rng.choice([8, 8, 8, rng.randrange(16)])
    info.move = rng.choice([0, 1, 1, 1, 0, 2])
    info.range = f32(rng.choice([50.0, 10.0, 12.0, 80.0, 120.0, rng.uniform(1, 200)]))
    info.follow = rng.choice([0, 1, 1, 2])
    info.scale = f32(rng.choice([0.2, 0.3, 0.5, 0.6, 0.7, 0.8]))
    info.blend_mesh = rng.choice([-1, -1, 0, 1])
    for i in range(5):
        info.speed[i] = f32(rng.choice([0.5, 0.8, 0.25, rng.uniform(0, 1)]))
    return info


def random_items(rng, owners, hero):
    items = [None]*ITEM_COUNT
    centre = owners[hero]['position'] if hero >= 0 else owners[0]['position']
    for _ in range(rng.randrange(0, 12)):
        i = rng.randrange(ITEM_COUNT)
        items[i] = {'live': rng.choice([1, 1, 1, 0]), 'visible': rng.choice([1, 1, 0]),
                    'type': rng.choice([0x1c0f, 0x1c0f, 0x1c0f, 0x1c0e, 0x1a00]),
                    'position': [f32(centre[0] + rng.uniform(-450, 450)), f32(centre[1] + rng.uniform(-450, 450)),
                                 f32(centre[2] + rng.uniform(-20, 20))]}
    return items


def session_case(rng):
    n = rng.randrange(1, 4)
    owners = [random_owner(rng, k) for k in range(n)]
    owner = rng.randrange(n)
    hero = owner if rng.random() < 0.75 else rng.choice([-1] + list(range(n)))
    item = rng.choice(PET_ITEMS)
    model = 0x24e6 + (item - 0x1a00) if rng.random() < 0.9 else rng.choice([0x2561, 0x2526])
    info = random_info(rng, item)
    case = {'seed': rng.getrandbits(32), 'owners': owners, 'owner': owner, 'hero': hero, 'item': item,
            'model': model, 'subtype': rng.choice([0, 0, 1]), 'info': bytes(info), 'bone_salt': rng.getrandbits(16),
            'frustum_salt': rng.getrandbits(32), 'crt_mode': rng.choice([0, 1]),
            'scene': rng.choice([6, 6, 6, 5, 2]), 'missing_models': [model] if rng.random() < 0.05 else [],
            'items': random_items(rng, owners, hero if hero >= 0 else owner),
            'cm': (info.slot, rng.choice([0x1a40, 0x1a40, 0x1a40, -1]), rng.choice([0, 0, 0, 1]),
                   rng.choice([0, 1, 1])),
            'clock': rng.randrange(0, 1 << 32), 'before_items': rng.choice([0, 0x1c0f, -1]), 'world_time': f32(rng.uniform(0, 1e6)),
            'start': rng.choice(['fresh', 'fresh', 'object', 'live'])}
    steps = []
    for _ in range(rng.randrange(10, 60)):
        r = rng.random()
        if r < 0.5:
            steps.append(('update', rng.choice([40, 40, 40, 41, 1000, 3100, 100100, 0])))
        elif r < 0.8:
            steps.append(('render', rng.choice([0, 1, 40])))
        elif r < 0.95:
            steps.append(('owners', rng.getrandbits(32)))
        else:
            steps.append(('items', rng.getrandbits(32)))
    case['steps'] = steps
    return case


def jitter_owners(owners, seed, big):
    rng = random.Random(seed)
    for o in owners:
        spread = 1200 if big else 120
        for i in range(2):
            o['position'][i] = f32(o['position'][i] + rng.uniform(-spread, spread))
        o['position'][2] = f32(rng.uniform(0, 400))
        o['angle'][2] = f32(rng.uniform(0, 360))
        if rng.random() < 0.05:
            o['live'] = 1 - o['live']
        if rng.random() < 0.1:
            o['buff_12'] = 1 - o['buff_12']
        if rng.random() < 0.2:
            o['action'] = rng.choice([0, 1, 0x20, 0x31, 0x32, 0x90, 0x133, 0x141, 0x148, 0x185, 0x186])


def object_start(rng_seed, case):
    """The OBJECT a pet's +8 already points at (a former pet's), as bytes."""
    rng = random.Random(rng_seed)
    o = Obj()
    o.live = 1 if case['start'] == 'live' else 0
    o.type = case['model']
    o.owner = case['owner']
    o.alpha_enable = 0
    o.action, o.prior_action = rng.choice([0, 1]), rng.choice([0, 1])
    o.scale = f32(0.5)
    o.velocity = f32(0.5)
    o.frame, o.prior_frame = f32(rng.uniform(0, 8)), f32(rng.uniform(0, 8))
    o.alpha_target, o.alpha, o.alpha_speed = 1.0, f32(rng.uniform(0, 1)), f32(0.1)
    for i in range(3):
        o.light[i] = 3.0
        o.direction[i] = f32(rng.uniform(-12, 12))
        o.angle[i] = f32(rng.uniform(0, 360)) if i == 2 else 0.0
        o.position[i] = f32(rng.uniform(3000, 20000))
    for i in range(12):
        o.matrix[i] = f32(rng.uniform(-1, 1))
    o.shadow_alpha = 1.0
    return vh.object_to_bytes(o)


def run_session(m, lib, case, plant=None):
    client, native = Client(m, case), Native(lib, case, plant)
    owners = [dict(o, position=list(o['position']), angle=list(o['angle'])) for o in case['owners']]
    items = case['items']
    info = Info.from_buffer_copy(case['info'])
    if plant == 'range':
        info.range = f32(info.range * 1.5 + 1.0)
    native.p.table[0] = info
    client.info.define(INFO, case['info'])
    client.set_cm(*case['cm'])
    native_in = Inputs()
    native.pet.info = ctypes.pointer(native.p.table[0])
    # the pet before Create: a fresh PetObject (0x00eabf2b) or one whose OBJECT exists
    pet0 = {'owner': case['owner'] if case['start'] == 'live' else -1, 'has_object': case['start'] != 'fresh', 'item': -1, 'created': 0, 'target_item': 0,
            'target': (0.0, 0.0, 0.0), 'has_target': 0, 'pick_tick': 0, 'wait_tick': 0, 'state': 0, 'angle1': 0.0,
            'angle2': 0.0}
    if case['start'] != 'fresh':   # a PetObject whose fields hold an earlier pet's state (Create keeps them)
        rs = random.Random(case['seed'] ^ 0x7e7)
        pet0.update({'target_item': rs.choice([-1, 0, rs.randrange(ITEM_COUNT)]),
                     'target': tuple(f32(rs.uniform(3000, 20000)) for _ in range(3)), 'has_target': rs.choice([0, 1]),
                     'pick_tick': rs.getrandbits(32), 'wait_tick': rs.getrandbits(32), 'state': rs.randrange(6),
                     'angle1': f32(rs.uniform(0, 6)), 'angle2': f32(rs.uniform(0, 6))})
    client.write_pet(pet0)
    q = native.pet
    q.target_item, q.has_target, q.pick_tick, q.wait_tick, q.state = (pet0['target_item'], pet0['has_target'],
                                                                      pet0['pick_tick'], pet0['wait_tick'],
                                                                      pet0['state'])
    q.angle1, q.angle2 = pet0['angle1'], pet0['angle2']
    for i in range(3):
        q.target[i] = pet0['target'][i]
    if pet0['has_object']:
        raw = object_start(case['seed'], case)
        client.obj = am.Region('obj', PET_OBJ, raw, bytes(vh.OBJECT_MASK))
        vh.bytes_to_object(raw, native.pet.object)
    else:   # operator new's memory: garbage the constructor overwrites (and-with-0 reads count as reads)
        client.obj = am.defined_region('obj', PET_OBJ, am.poison(OBJ, case['seed'] & 0xff))
        lib.mu_hp_object_init(ctypes.addressof(native.pet.object))
    native.pet.owner, native.pet.item = pet0['owner'], -1
    stats = {'steps': 0, 'updates': 0, 'renders': 0, 'calls': 0}
    rhost = native.render_host()
    clock = case['clock']
    plan = [('create', 0)] + case['steps']
    for step in plan:
        kind = step[0]
        if kind == 'owners':
            jitter_owners(owners, step[1], step[1] & 7 == 0)
            continue
        if kind == 'items':
            rng = random.Random(step[1])
            items = list(items)
            for _ in range(4):
                i = rng.randrange(ITEM_COUNT)
                items[i] = {'live': 1, 'visible': rng.choice([1, 1, 0]), 'type': rng.choice([0x1c0f, 0x1c0f, 0x1a00]),
                            'position': [f32(owners[case['owner']]['position'][0] + rng.uniform(-350, 350)),
                                         f32(owners[case['owner']]['position'][1] + rng.uniform(-350, 350)), 0.0]}
            continue
        clock = (clock + (step[1] if kind != 'create' else 0)) & 0xffffffff
        s = {'scene': case['scene'], 'hero': case['hero'], 'world_time': f32(case['world_time'] + clock % 100000),
             'clock': clock}
        if plant == 'scene':
            s_native = dict(s, scene=6 if s['scene'] != 6 else 5)
        else:
            s_native = s
        client.case = dict(case, owners=owners)
        native.case = dict(case, owners=owners)
        client.set_owners(owners)
        native.set_owners(owners)
        client.set_items(items)
        native.set_items(items)
        client.log.clear()
        native.log.clear()
        client.tick_n = client.time_n = native.tick_n = native.time_n = 0
        native.s = s_native
        native_in.scene, native_in.hero = s_native['scene'], s_native['hero']
        native_in.helper_type = case['cm'][1]
        native_in.helper_92, native_in.helper_93 = case['cm'][2], case['cm'][3]
        native_in.world_time = s_native['world_time']
        native_in.items = ctypes.cast(native.ground, ctypes.POINTER(Ground))
        native_in.before_items = case['before_items']
        stubs = client.stubs(s)
        regions = client.regions(s)
        if kind == 'create':
            pos = owners[case['owner']]['position']
            client.args.define(vh.ARGS, struct.pack('<3f', *pos))
            res = m.execute(CREATE, [case['item'], case['model'], vh.ARGS, char_addr(case['owner']),
                                     case['subtype'], 0], regions, stubs, ecx=PET, cleanup=0x18)
            pv = V3(*pos)
            if not pet0['has_object']:   # the OBJECT constructor's SetLive(0) (ObjectInit) runs its cleanup
                native.log.append(('kill', 'pet'))
            r_native = lib.mu_pet_create_object(ctypes.byref(native.p), ctypes.byref(native.pet), case['item'],
                                                case['model'], ctypes.addressof(pv), case['owner'], case['subtype'])
        elif kind == 'update':
            res = m.execute(UPDATE, [], regions, stubs, ecx=PET)
            r_native = lib.mu_pet_update(ctypes.byref(native.p), ctypes.byref(native.pet), ctypes.byref(native_in))
            stats['updates'] += 1
        else:
            res = m.execute(RENDER, [], regions, stubs, ecx=PET)
            r_native = lib.mu_pet_render(ctypes.byref(native.p), ctypes.byref(native.pet), ctypes.byref(native_in),
                                         ctypes.byref(rhost))
            stats['renders'] += 1
        stats['steps'] += 1
        stats['calls'] += len(client.log)
        if not res['ok']:
            return {'ok': False, 'step': step, 'machine': {k: v for k, v in res.items() if k != 'regions'},
                    'log': client.log[-6:]}
        client.pet.data[:] = res['regions']['pet']
        client.obj.data[:] = res['regions']['obj']
        client.pending.data[:] = res['regions']['pending']
        # compare
        cpet, npet = client.read_pet(bytes(client.pet.data)), native.read_pet()
        if case['start'] == 'live' and kind == 'create':
            pass
        diffs = []
        if (res['eax'] & 0xff) != (r_native & 0xff):
            diffs.append(('result', res['eax'], r_native))
        if client.rand_state != native.p.rand_state or client.rand_calls != native.p.rand_calls:
            diffs.append(('rand', client.rand_calls, native.p.rand_calls))
        for k in cpet:
            if not same(cpet[k] if not isinstance(cpet[k], tuple) else tuple(f32(x) for x in cpet[k]),
                        npet[k] if not isinstance(npet[k], tuple) else tuple(f32(x) for x in npet[k])) and \
                    not (k in ('angle1', 'angle2') and bits(cpet[k]) == bits(npet[k])):
                diffs.append(('pet', k, cpet[k], npet[k]))
        craw = vh.masked(bytes(client.obj.data))
        nraw = vh.masked(vh.object_to_bytes(native.pet.object))
        if craw != nraw:
            first = next(i for i in range(OBJ) if craw[i] != nraw[i])
            diffs.append(('object', hex(first), craw[first:first + 12].hex(), nraw[first:first + 12].hex()))
        pending = struct.unpack('<i', bytes(client.pending.data))[0]
        if pending != native.p.pending_pickup:
            diffs.append(('pending', pending, native.p.pending_pickup))
        if not same_log(client.log, native.log):
            at = next((i for i, (a, b) in enumerate(zip(client.log, native.log)) if not same(a, b)),
                      min(len(client.log), len(native.log)))
            diffs.append(('log', at, len(client.log), len(native.log), client.log[at:at + 2], native.log[at:at + 2]))
        if diffs:
            return {'ok': False, 'step': step, 'diffs': diffs[:4], 'case': {k: case[k] for k in
                                                                           ('item', 'model', 'hero', 'owner')}}
    return {'ok': True, 'stats': stats}


# --------------------------------------------------------------------------
# Sections.

def section_session(m, lib, args, report):
    rng = random.Random(args.seed ^ 0x5e55)
    m.add_probes(PROBES)
    totals = {'cases': 0, 'mismatches': 0, 'steps': 0, 'updates': 0, 'renders': 0, 'calls': 0}
    first = None
    for i in range(args.cases):
        case = session_case(rng)
        r = run_session(m, lib, case)
        totals['cases'] += 1
        if r['ok']:
            for k in ('steps', 'updates', 'renders', 'calls'):
                totals[k] += r['stats'][k]
        else:
            totals['mismatches'] += 1
            first = first or r
    probes = {label: m.probes[a] for a, label in PROBES.items()}
    report['session'] = dict(totals, first_failure=first, probes=probes)
    unreached = [k for k, v in probes.items() if v == 0]
    if unreached:
        print('session: unreached probes', unreached)
    if args.negative:
        detected = {}
        for plant in ('range', 'scene', 'zen'):
            rng2 = random.Random(args.seed ^ sum(map(ord, plant)))
            hit = False
            for i in range(args.negative):
                if not run_session(m, lib, session_case(rng2), plant)['ok']:
                    hit = True
                    break
            detected[plant] = hit
        report['session']['negative'] = detected
    return totals['mismatches'] == 0


def checksum_py(lib, data):
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    return lib.mu_pet_checksum(buf, len(data), 0x3bb2)


def bux(data):
    code = (0xfc, 0xcf, 0xab)
    return bytes(b ^ code[i % 3] for i, b in enumerate(data))


def data_cases(rng, lib, private):
    out = []
    if private is not None:
        out.append(('installed', private))
    for i in range(args_data_cases(rng)):
        plain = bytearray(0x600)
        for r in range(rng.randrange(0, 33)):
            rec = struct.pack('<ii4Bf4Bfi5f', r, rng.randrange(1, 512), 0xff, 0, 8, rng.randrange(3),
                              f32(rng.uniform(0, 100)), rng.randrange(2), 0, 0, 0, f32(rng.uniform(0, 1)),
                              rng.choice([-1, 0]), *[f32(rng.uniform(0, 1)) for _ in range(5)])
            plain[r*0x30:(r+1)*0x30] = rec
        enc = bux(bytes(plain[:0x30]))  # not used: each record is converted separately
        enc = b''.join(bux(bytes(plain[r*0x30:(r+1)*0x30])) for r in range(32))
        total = checksum_py(lib, enc)
        kind = rng.choice(['valid', 'valid', 'valid', 'corrupt', 'corrupt-sum'])
        body = bytearray(enc)
        stored = total
        if kind == 'corrupt':
            body[rng.randrange(0x600)] ^= 1 << rng.randrange(8)
        elif kind == 'corrupt-sum':
            stored ^= 1 << rng.randrange(32)
        out.append((kind, bytes(body) + struct.pack('<I', stored)))
    out.append(('missing', None))
    return out


def args_data_cases(rng):
    return 60


def section_data(m, lib, args, report):
    rng = random.Random(args.seed ^ 0xda7a)
    root = os.environ.get('MU_GAME_ROOT')
    private = None
    if root and (Path(root)/'Data/Local/petdata.bmd').exists():
        private = (Path(root)/'Data/Local/petdata.bmd').read_bytes()
    totals = {'cases': 0, 'mismatches': 0, 'kinds': {}}
    first = None
    installed = None
    for kind, blob in data_cases(rng, lib, private):
        log = []
        state = {'buf': None}
        proc = am.undefined_region('process', PROCESS, 0x614)
        heap = am.undefined_region('file', FILE_BUF, 0x1000)
        regions = [proc, heap, am.defined_region('bux', BUX, bytes([0xfc, 0xcf, 0xab]), writable=False),
                   am.defined_region('hwnd', HWND, struct.pack('<I', 0x1234), writable=False)]

        def memset(mm):
            dst, value, count = mm.argument(0), mm.argument(1), mm.argument(2)
            mm.write(dst, bytes([value & 0xff])*count)
            return dst

        def sprintf(mm):
            dst, fmt = mm.argument(0), mm.cstring(mm.argument(1))
            text = fmt.replace('%s', mm.cstring(mm.argument(2))) if '%s' in fmt else fmt
            mm.local_write(dst, text.encode('latin1') + b'\0')
            return len(text)

        def fopen(mm):
            log.append(('fopen', mm.cstring(mm.argument(0)), mm.cstring(mm.argument(1))))
            return 0 if blob is None else 0x77

        def malloc(mm):
            return FILE_BUF

        def fread(mm):
            dst, size, count = mm.argument(0), mm.argument(1), mm.argument(2)
            if state['buf'] is None:
                state['buf'] = 0
            chunk = blob[state['buf']:state['buf'] + size*count]
            state['buf'] += len(chunk)
            mm.local_write(dst, chunk)
            return len(chunk)//size

        def fclose(mm):
            return 0

        def memcpy(mm):
            dst, src, n = mm.argument(0), mm.argument(1), mm.argument(2)
            mm.local_write(dst, bytes(mm.uc.mem_read(src, n)))
            return dst

        def free(mm):
            return 0

        def logger(mm):
            log.append(('message', mm.cstring(mm.argument(1))))
            return 0

        def msgbox(mm):
            return 1, 0x10

        def sendmsg(mm):
            log.append(('close',))
            return 0, 0x10

        stubs = {MEMSET: memset, SPRINTF: sprintf, FOPEN: fopen, MALLOC: malloc, FREAD: fread, FCLOSE: fclose,
                 MEMCPY: memcpy, FREE: free, LOGGER: logger, m.iat[IAT_MSGBOX]: msgbox, m.iat[IAT_SENDMSG]: sendmsg}
        res = m.execute(LOAD, [], regions, stubs, ecx=PROCESS)
        totals['cases'] += 1
        totals['kinds'][kind] = totals['kinds'].get(kind, 0) + 1
        table = (Info * 32)()
        if blob is None:
            r = lib.mu_pet_data_load(None, 0, ctypes.byref(table))
        else:
            buf = ctypes.create_string_buffer(blob, len(blob))
            r = lib.mu_pet_data_load(buf, len(blob), ctypes.byref(table))
        expect = {0: [], 1: [('message', 'Data\\Local\\petdata.bmd - File not exist.'), ('close',)],
                  2: [('message', 'Data\\Local\\petdata.bmd - File corrupted.'), ('close',)]}[r]
        client_table = res['regions']['process'][4:4 + 0x600] if res['ok'] else None
        ok = res['ok'] and client_table == bytes(table) and [x for x in log if x[0] != 'fopen'] == expect and \
            log[0] == ('fopen', 'Data\\Local\\petdata.bmd', 'rb')
        if kind == 'installed' and ok:
            installed = [(t.seq, t.item, t.slot, t.move, f32(t.range), t.follow, f32(t.scale), t.blend_mesh,
                          tuple(f32(x) for x in t.speed)) for t in table if t.item]
        if not ok:
            totals['mismatches'] += 1
            first = first or {'kind': kind, 'machine': {k: v for k, v in res.items() if k != 'regions'},
                              'log': log, 'native_result': r}
    report['data'] = dict(totals, first_failure=first, installed_records=len(installed or []))
    if installed is not None:
        report['data']['installed'] = installed
    return totals['mismatches'] == 0


MUTATIONS = {1: ('session', 'fly speed factor'), 2: ('session', 'collector second angle period'),
             3: ('session', 'Spirit of Guardian light phases swapped'), 4: ('data', 'checksum shift'),
             5: ('session', 'zen search radius'), 6: ('session', 'skeleton bone 0x3d')}


def run_mutations(m, args):
    import shutil
    import tempfile
    caught = {}
    src = ROOT/'reconstructed'
    for n, (section, label) in MUTATIONS.items():
        tmp = Path(tempfile.mkdtemp(prefix='mu-pet-mut-'))
        out = tmp/f'libclient_pets.{SUFFIX}'
        cmd = ['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', f'-DMU_PET_MUTATION={n}',
               '-shared', str(src/'pets/pets.c'), str(src/'helpers/helpers.c'),
               str(src/'movement/client_movement.c'), str(src/'record-math/record_math.c'), '-lm', '-o', str(out)]
        subprocess.run(cmd, check=True, capture_output=True)
        lib = load_library(out)
        sub = argparse.Namespace(**vars(args))
        sub.cases, sub.negative = min(args.cases, 150), 0
        good = globals()['section_' + section](m, lib, sub, {})
        caught[f'{n} {label}'] = not good
        shutil.rmtree(tmp, ignore_errors=True)
    return caught


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', default=str(vh.DEFAULT_TEXT))
    ap.add_argument('--data', default=str(vh.DEFAULT_DATA))
    ap.add_argument('--seed', type=int, default=20261022)
    ap.add_argument('--cases', type=int, default=300)
    ap.add_argument('--negative', type=int, default=0)
    ap.add_argument('--sections', default='data,session')
    ap.add_argument('--report', default=None)
    ap.add_argument('--mutations', action='store_true')
    args = ap.parse_args(argv)
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'image data')
    lib = load_library()
    m = Machine(text, data)
    report = {'bodies': body_digests(text), 'seed': args.seed}
    ok = True
    t0 = time.time()
    for name in [s for s in args.sections.split(',') if s]:
        s0 = time.time()
        good = globals()['section_' + name](m, lib, args, report)
        ok = ok and good
        print(f'{name}: {"ok" if good else "MISMATCH"} ({time.time() - s0:.1f} s)', flush=True)
    if args.mutations:
        caught = run_mutations(m, args)
        report['mutations'] = caught
        ok = ok and all(caught.values())
        print('mutations:', caught, flush=True)
    report['seconds'] = round(time.time() - t0, 1)
    out = json.dumps(report, indent=1, default=str)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(out)
    print(out[:5000])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
