#!/usr/bin/env python3
"""Compare the reconstructed character-select scene with the client (NATIVE-CHARSEL-001).

Every case runs the client's own instructions in Unicorn over the pinned
restored text and second image section (scripts/client_ui_machine.py) and the
reconstruction in reconstructed/charsel through ctypes, from the same initial
state, then compares:

* the ordered calls the routine makes into other subsystems (every callee
  that is not run as client code is a recording stub; its arguments are
  compared word for word, pointers into character records as
  (index, offset), vectors passed by pointer by value);
* every byte of the character records, the scene object and the map object
  the routine may touch, the globals it writes and its return value.

Client code run unmodified: CGMCharacterScene_Ex::CreateObject 0x00daa2b2,
SetCharacterPosition 0x00da9ff3, SetCharacterScale 0x01394f6f, CreateHero
0x0137f824, RenderCharacterScene 0x018576b3, the scene-5 logic tick
0x01856e6c, the world check 0x00daa1f5, the character table lookup
0x009a13f4, the vector/record accessors 0x00cfc922/0x00cfc94a, the scene,
class and skin helpers 0x009b0bc1/0x0095f5cc/0x0139d6a2, the record field
getters 0x0095f977/0x0129dcda/0x0129deaa and the C runtime sin 0x01985700
(SSE2 path).  The trig dispatch flag 0x0bdd1cc8 holds the captured value 1.

Undefined reads stop a case: the character records, scene object and every
global are seeded explicitly; anything else the client reads is a failure.
"""
import argparse
import ctypes
from ctypes import POINTER, Structure, c_float, c_int32, c_uint8, c_uint16, c_uint32, c_void_p, CFUNCTYPE
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import client_ui_machine as cm  # noqa: E402
try:
    from unicorn.x86_const import UC_X86_REG_FPCW, UC_X86_REG_MXCSR
except ImportError:  # pragma: no cover
    UC_X86_REG_FPCW = UC_X86_REG_MXCSR = None

TEXT_BYTES, TEXT_SHA256 = 23572480, '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BYTES, DATA_SHA256 = 2557764, 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'

# Executed routine bodies, pinned (start, end, SHA-256 of the restored bytes).
ROUTINES = {
    'create_object': (0x00daa2b2, 0x00daa82b, None),
    'set_character_position': (0x00da9ff3, 0x00daa127, None),
    'world_check': (0x00daa1f5, 0x00daa20d, None),
    'character_scale': (0x01394f6f, 0x013953f3, None),
    'create_hero': (0x0137f824, 0x0137fbac, None),
    'render': (0x018576b3, 0x01857ed9, None),
    'tick': (0x01856e6c, 0x01857236, None),
    'table_lookup': (0x009a13f4, 0x009a1421, None),
    'vector_at': (0x00cfc922, 0x00cfc936, None),
    'vector': (0x00cfc94a, 0x00cfc956, None),
    'live': (0x0095f977, 0x0095f986, None),
    'mount': (0x0129dcda, 0x0129dced, None),
    'name': (0x0129deaa, 0x0129debb, None),
    'scene_get': (0x009b0bc1, 0x009b0bcf, None),
    'class_nibble': (0x0095f5cc, 0x0095f5d7, None),
    'skin_index': (0x0139d6a2, 0x0139d6da, None),
    'class_tier': (0x0139cb8a, 0x0139cbe1, None),
    'crt_sin': (0x01985700, 0x01985743, None),
    'crt_sin_sse2': (0x019a72f8, 0x019a752a, None),
}
PINNED = {
    'create_object': '3db6d3622dd240382a1ae16e1137223a229c459cb1979710f90de5941bc3f733',
    'set_character_position': '84244f1fecbb520bff5a656b9c2fa0d2e4cb9ab8c6fbbb3a4909b63d782c8939',
    'world_check': '1e75039d3b6209698e35d346f820e52dd04296b576fb68594fc4a8116f3b3029',
    'character_scale': 'ec10ca7e6d5b7f26242af5ba096d0e4e06f0995d8f07cfc04778cad3b718c148',
    'create_hero': '5f1f67d3ebf514249a36fc485883ad297b791f96ab7b88893b31d4c036b79b9f',
    'render': '20e0fd56f5f9019e7daca589c236ecb207f0093659117e736ddaa97ca5f9d967',
    'tick': '0ad0e9720d46bc4b09a67af4e6ddd0223f05c7bd4b32bb10d78cb5acab109d88',
    'table_lookup': 'aef4e1e063401a98de255aa54c4d32a92391d38783e7dd7733a352c1651292ac',
    'vector_at': '0518ccd07aae2d4de135e2ab9c0b1c22e7898200e3c42fd1db23a397871043b5',
    'vector': '25992882b0f4cb017f9114855550dd8181349a42644f0517cc755246d09e132a',
    'live': 'c476f28eb4a82f85fe3102246db86847fed98479722b3e89ff836ae68a7fa9bc',
    'mount': '7ecb4a32b00d582fbdf41e34f8895840c775827e80523ffc7c6add7d9f1f181d',
    'name': 'fe03964f580d9ae12bf1f50c5efb55b4bedef9a5143b89f3cce2e5704fa6748e',
    'scene_get': '60e1dbe0e4e756e1dcd216bd8343b4442a04af8747bb16c427db7e71fe4af490',
    'class_nibble': '0ccb64b405499edf6e0778c5493520acecf7b9d1c8421c7ae277ca472664df46',
    'skin_index': '4f90c1b6dac9d02601995bc4755a494200c0021cce59b07c6b603969550f32d1',
    'class_tier': '7d0629010928caeab71f43b9755f5406355c514c6dd86abfd4816fdd51a91eee',
    'crt_sin': 'f102b535fc42e3d5bb4d2711479e5cd687b566bacad8ad279e92ce6ceb5e7a77',
    'crt_sin_sse2': 'e8bdc78a457e4e752fedc47f34b7aceee4bf3a8b8f7e6063b11855296aa3f4da',
}

MANAGER = 0x7e0f0000           # CharactersClient manager (0x0095f6db result); +8 = table
FAKE_BASE, FAKE_SIZE = 0x7e000000, 0x00100000
RECORD, OBJECT = 0x3670, 0x3254
WORLD_INFO = 0x7e0e0000        # 0x0098647b result; +0xc -> record
CAMERA_RECORD = 0x7e0e0100
TRIG_FLAG, CRT_MATH_MODE = 0x0bdd1cc8, 0x0bdcfbc8


def fake(n):
    return FAKE_BASE + (n << 12)


ID = dict(UI_HELPER=fake(1), QUEST_MGR=fake(2), QUEST=fake(3), NAME_MGR=fake(4), INPUT=fake(5), UIMNG=fake(6),
          UI_9C2AEA=fake(7), GFX=fake(8), GFX_MOVIE=fake(9), GFX_22C=fake(10), MENU=fake(11), MENU_HANDLE=fake(12))
STACK_REF = 0x5ac00000
GL_TAGS = {'glColor3f': 0x01a7c76c, 'glClearColor': 0x01a7c6cc}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def fb(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


# --------------------------------------------------------------------------
# ctypes view of reconstructed/charsel

CHARFN = CFUNCTYPE(c_void_p, c_void_p, c_int32)


class Event(Structure):
    _fields_ = [('call', c_uint32), ('count', c_int32), ('args', c_uint32 * 16)]


class Log(Structure):
    _fields_ = [('count', c_int32), ('overflow', c_int32), ('events', Event * 96)]


class Scene(Structure):
    _fields_ = [('position', (c_float * 3) * 5), ('angle', (c_float * 3) * 5)]


class MapObject(Structure):
    _fields_ = [('type', c_int32), ('position', c_float * 3), ('field_64', c_int32), ('field_68', c_int32),
                ('field_c0', c_float)]


class ScaleInputs(Structure):
    _fields_ = [('scene', c_int32), ('world', c_int32), ('event_world', c_uint8), ('buff_1a8', c_uint8),
                ('buff_1a9', c_uint8)]


class Frame(Structure):
    _fields_ = [('initialised', c_uint8), ('protocol', c_int32), ('selected', c_int32), ('shown', c_int32),
                ('world_time', c_float), ('mouse_x', c_int32), ('mouse_y', c_int32), ('record_position', c_float * 3),
                ('pick', c_int32), ('input_byte_1f', c_uint8), ('enter_refused', c_uint8), ('screen_width', c_int32),
                ('quest_object', c_uint32)]


class Tick(Structure):
    _fields_ = [('scene', c_int32), ('initialised', c_uint8), ('protocol', c_int32), ('selected', c_int32),
                ('shown', c_int32), ('gfx_busy', c_uint8), ('gfx_busy_enter', c_uint8), ('gfx_busy_escape', c_uint8),
                ('input_byte_31', c_uint8), ('key_enter', c_uint8), ('key_escape', c_uint8), ('gfx_flag_78', c_uint8),
                ('gfx_flag_79', c_uint8), ('global_1d22d1e', c_uint8), ('global_6fca007', c_uint8),
                ('ui_byte_464', c_uint8), ('gfx_menu_flag', c_uint8), ('enter_refused', c_uint8),
                ('ui_byte_65b9', c_uint8)]


def load_library(directory=None):
    import subprocess
    directory = Path(directory or ROOT / 'reconstructed' / 'charsel')
    subprocess.run(['make', '-s', '-C', str(directory)], check=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(directory / f'libcharsel.{suffix}'))
    lib.mu_charsel_set_character_position.argtypes = [POINTER(Scene), c_int32, CHARFN, c_void_p]
    lib.mu_charsel_create_object.argtypes = [POINTER(Scene), c_int32, POINTER(MapObject), CHARFN, c_void_p]
    lib.mu_charsel_character_scale.argtypes = [c_void_p, c_uint32, POINTER(ScaleInputs), POINTER(Log)]
    lib.mu_charsel_create_hero.argtypes = [c_int32, c_uint8, c_uint8, c_float, c_float, c_float, POINTER(ScaleInputs),
                                           CHARFN, c_void_p, POINTER(Log)]
    lib.mu_charsel_create_hero.restype = c_void_p
    lib.mu_charsel_render.argtypes = [POINTER(Frame), CHARFN, c_void_p, POINTER(c_uint8), POINTER(Log)]
    lib.mu_charsel_tick_step.argtypes = [POINTER(Tick), POINTER(Log)]
    return lib


class Records:
    """Host copies of character records (indices given), for the C side."""

    def __init__(self, images):
        self.buffers = {i: ctypes.create_string_buffer(bytes(b), RECORD) for i, b in images.items()}
        self.fn = CHARFN(self._get)
        self.requested = []

    def _get(self, context, index):
        self.requested.append(index)
        buffer = self.buffers.get(index)
        if buffer is None:
            # a record the case did not seed: the client would read undefined memory
            raise_later.append(index)
            buffer = self.buffers[index] = ctypes.create_string_buffer(RECORD)
        return ctypes.addressof(buffer)

    def address_index(self, address):
        for index, buffer in self.buffers.items():
            base = ctypes.addressof(buffer)
            if base <= address < base + RECORD:
                return index, address - base
        return None

    def image(self, index):
        return bytes(self.buffers[index].raw)


raise_later = []


def c_events(log):
    out = []
    for i in range(log.count):
        e = log.events[i]
        out.append((e.call, tuple(e.args[k] for k in range(e.count))))
    return out


# --------------------------------------------------------------------------
# client side


class Case:
    def __init__(self, machine, table_base):
        self.m = machine
        self.table = table_base
        self.merged = []

    def ref(self, value):
        """Translate a pointer argument into the reconstruction's encoding."""
        if self.table <= value < self.table + 400 * RECORD:
            index, offset = divmod(value - self.table, RECORD)
            return 0x40000000 + (index << 16) + offset
        return value

    def vec(self, pointer):
        return [self.m.u32(pointer + 4 * i) for i in range(3)]


class Harness:
    def __init__(self, text, data):
        m = self.m = cm.Machine(text, data)
        m.uc.mem_map(FAKE_BASE, FAKE_SIZE, cm.UC_PROT_ALL)
        for name, (start, end, _) in ROUTINES.items():
            m.allow((start, end))
        self.case = None
        self._stubs()

    # stubs ---------------------------------------------------------------
    def _record(self, address, count, convert=None, ret=0, cleanup=0, this=False):
        def handler(m, address=address):
            words = m.args(count)
            if this:
                words = [m.uc.reg_read(cm.UC_X86_REG_ECX)] + words
            if convert:
                words = convert(self.case, words)
            else:
                words = [self.case.ref(w) for w in words]
            self.case.merged.append((address, tuple(w & 0xffffffff for w in words)))
            value = ret(self.case, words) if callable(ret) else ret
            return value
        self.m.stub(address, handler, cleanup)

    def _stubs(self):
        r = self._record
        # getters (no arguments)
        r(0x0095f6db, 0, ret=MANAGER)
        # 0x0095f6db is not logged by the reconstruction: its records are dropped
        r(0x0098647b, 0, ret=WORLD_INFO)
        r(0x00cc3564, 0, ret=ID['INPUT'])
        r(0x011e228b, 0, ret=ID['UIMNG'])
        r(0x009c104e, 0, ret=ID['UI_HELPER'])
        r(0x00b990b0, 0, ret=ID['QUEST_MGR'])
        r(0x0121d4c9, 0, ret=ID['NAME_MGR'])
        r(0x009c2aea, 0, ret=ID['UI_9C2AEA'])
        r(0x00ac3bf7, 0, ret=ID['GFX'])
        # render callees
        r(0x016b47bf, 1, ret=lambda c, w: c.pick)
        r(0x009a5029, 1, this=True, cleanup=4, ret=lambda c, w: c.enter_refused)
        r(0x0185a75a, 1)
        r(0x0185498e, 0)
        r(0x016bc355, 0, ret=lambda c, w: c.screen_width)
        r(0x0184adc7, 4)
        r(0x016cba24, 3, convert=lambda c, w: [w[0]] + c.vec(w[1]) + [w[2]])
        r(0x01849f08, 4)
        r(0x0184aa2b, 0)
        r(0x0184a7f3, 0)
        r(0x016cacfc, 5, convert=lambda c, w: [w[0], w[1]] + c.vec(w[2]) + [w[3], w[4]])
        r(0x016cd468, 1)
        r(0x016d5020, 0)
        r(0x01363260, 3)
        r(0x00d8bd8f, 2)
        r(0x00c9e4e3, 0)
        r(0x01534b4c, 0)
        r(0x01589b56, 1)
        r(0x015181fa, 1, this=True, cleanup=4)
        r(0x00eb1309, 1, this=True, cleanup=4, ret=lambda c, w: ID['QUEST'] if c.quest_object else 0)
        r(0x00eac4e0, 0, this=True)
        r(0x00c9fd8d, 1)
        r(0x016d6949, 0)
        r(0x01692887, 0, this=True)
        r(0x016cdd5f, 11, convert=lambda c, w: w[:5] + c.vec(w[5]) + w[6:])
        r(0x0168fafd, 8, convert=lambda c, w: [w[0]] + c.vec(w[1]) + c.vec(w[2]) + c.vec(w[3]) + w[4:])
        r(0x009eaebe, 1, this=True, cleanup=4)
        r(0x0184a699, 0)
        r(0x0106bcc5, 1, this=True, cleanup=4)
        r(0x0169270e, 1, this=True, cleanup=4)
        r(0x0159123f, 1, this=True, cleanup=4)
        r(0x0169159e, 1, this=True, cleanup=4)
        r(0x0184a6ab, 0)
        r(0x0184f793, 0)
        r(0x01858c72, 0)
        r(0x0184f8d7, 0)
        r(0x0184b6dd, 0)
        # tick callees
        r(0x01851540, 0)
        r(0x016ca4fa, 0)
        r(0x016d82c7, 0)
        r(0x00c9e24a, 0)
        r(0x0137a7ce, 0)
        r(0x0137a716, 1)
        r(0x0150ddb1, 0, this=True)
        r(0x01589b06, 0)
        r(0x0159122d, 0, this=True)
        r(0x00c9eb04, 0)
        r(0x00eb0d64, 0, this=True)
        r(0x009b9913, 0, this=True)
        r(0x00ac9613, 1, this=True, cleanup=4)
        r(0x01854529, 0)
        r(0x00aae6f9, 0, this=True, ret=lambda c, w: c.next_busy())
        r(0x00ec53a7, 1, ret=lambda c, w: c.key(w[0]))
        r(0x00a6ac96, 3)

        def menu(c, w):
            out = w[1]
            c.m.put32(out, ID['MENU_HANDLE'])
            c.m.put32(out + 4, 0)
            return out
        r(0x009a5792, 1, this=True, cleanup=4,
          convert=lambda c, w: [w[0], STACK_REF if cm.STACK_BASE <= w[1] < cm.STACK_BASE + cm.STACK_SIZE else w[1]],
          ret=lambda c, w: menu(c, [w[0], c.m.args(1)[0]]))
        r(0x00c8c8b1, 0, this=True)
        r(0x00b49bf4, 1, this=True, cleanup=4)
        # create-hero callees
        r(0x0137d8a1, 5)
        r(0x01295f18, 0, this=True)
        r(0x0129dc78, 1, this=True, cleanup=4)
        r(0x0128ed7d, 2)
        r(0x0138fe69, 1)
        r(0x009dacb8, 1, ret=lambda c, w: c.event_world)
        r(0x01295ade, 1, this=True, cleanup=4, ret=lambda c, w: c.buff.get(w[1], 0))

    # case setup ----------------------------------------------------------
    def begin(self, records):
        m = self.m
        m.reset()
        m.uc.mem_write(FAKE_BASE, b'\0' * FAKE_SIZE)
        table = m.alloc(400 * RECORD, align=0x1000)
        case = self.case = Case(m, table)
        case.merged = []
        for name, tag in GL_TAGS.items():
            m.handlers[name] = (lambda tag: lambda machine, words: case.merged.append(
                (tag, tuple(w & 0xffffffff for w in words))) and 0)(tag)
        case.pick, case.enter_refused, case.screen_width, case.quest_object = 0, 0, 640, 0
        case.event_world, case.buff = 0, {}
        case.busy = []
        case.keys = {}
        case.next_busy = lambda: case.busy.pop(0) if case.busy else 0
        case.key = lambda vk: case.keys.get(vk, 0)
        m.uc.mem_write(MANAGER + 8, struct.pack('<I', table))
        for index, image in records.items():
            m.write(table + index * RECORD, image)
        m.write(TRIG_FLAG, struct.pack('<I', 1))
        m.uc.reg_write(UC_X86_REG_FPCW, 0x027f)
        m.uc.reg_write(UC_X86_REG_MXCSR, 0x1f80)
        return case

    def record_image(self, index):
        return self.m.read(self.case.table + index * RECORD, RECORD)

    def client_events(self):
        return [e for e in self.case.merged if e[0] != 0x0095f6db]


# --------------------------------------------------------------------------
# tallies


class Tally:
    def __init__(self):
        self.results = {}
        self.coverage = {}

    def cover(self, key, value=1):
        self.coverage[key] = self.coverage.get(key, 0) + value

    def add(self, family, ok, detail=None):
        r = self.results.setdefault(family, {'cases': 0, 'mismatches': 0, 'first': None})
        r['cases'] += 1
        if not ok:
            r['mismatches'] += 1
            if r['first'] is None:
                r['first'] = detail


def diff_bytes(a, b, limit=8):
    out = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            out.append((hex(i), x, y))
            if len(out) >= limit:
                break
    return out


def random_record(g, index, live=None):
    image = bytearray(RECORD)
    # seed the fields these routines may read with random content, the rest zero
    for offset in range(0, RECORD, 4):
        if g.random() < 0.02:
            image[offset:offset + 4] = struct.pack('<I', g.getrandbits(32))
    o = OBJECT
    image[o] = (1 if g.random() < 0.8 else 0) if live is None else live
    image[o + 0x0b] = 1 if g.random() < 0.85 else 0
    image[o + 0x5c:o + 0x60] = struct.pack('<i', g.choice([0xa91, 0xa91, 0xa91, 0x136, 0]))
    for k in range(3):
        image[o + 0x158 + 4 * k:o + 0x15c + 4 * k] = struct.pack('<f', f32(g.uniform(-30000, 30000)))
        image[o + 0x164 + 4 * k:o + 0x168 + 4 * k] = struct.pack('<f', f32(g.uniform(-360, 360)))
        image[o + 0xec + 4 * k:o + 0xf0 + 4 * k] = struct.pack('<f', f32(g.uniform(0, 1)))
    image[0x322e:0x3230] = struct.pack('<H', g.choice([0, 0, 0x1a03, 0x1a04, 0xffff]))
    return bytes(image)


# --------------------------------------------------------------------------
# families


def family_create_object(h, lib, tally, g, count):
    for number in range(count):
        indices = [0, 1, 2, 3, 4, 17]
        records = {i: random_record(g, i) for i in indices}
        case = h.begin(records)
        m = h.m
        world = 0x5d if g.random() < 0.85 else g.choice([0x5c, 0x5e, 0, 93 + 256])
        m.write(0x01cf15fc, struct.pack('<i', world))
        scene_addr = m.alloc(0x8c, align=16)
        scene = Scene()
        image = bytearray(0x8c)
        for k in range(5):
            for i in range(3):
                p, a = f32(g.uniform(-20000, 20000)), f32(g.uniform(-360, 360))
                scene.position[k][i], scene.angle[k][i] = p, a
                image[0x14 + 12 * k + 4 * i:0x18 + 12 * k + 4 * i] = struct.pack('<f', p)
                image[0x50 + 12 * k + 4 * i:0x54 + 12 * k + 4 * i] = struct.pack('<f', a)
        m.write(scene_addr, image)
        host = Records(records)
        steps = g.randint(1, 6)
        ok, detail = True, None
        for step in range(steps):
            obj = m.alloc(0x400, align=16)
            mo = MapObject()
            mo.type = g.choice(list(range(0x0d, 0x12)) * 3 + [0x26, 0x27, 0x28, 0x36, 0x37, 0x38, 0x39, 0x45, 0x50,
                                                             0x3c, 0x3d, 0x0c, 0x12, 0x18, 0x49, 0, -1, 0x1000])
            for i in range(3):
                mo.position[i] = f32(g.uniform(-30000, 30000))
            mo.field_64, mo.field_68 = g.getrandbits(31), g.getrandbits(31)
            mo.field_c0 = f32(g.uniform(-1000, 1000))
            oimg = bytearray(0x400)
            oimg[0x5c:0x60] = struct.pack('<i', mo.type)
            oimg[0x64:0x68] = struct.pack('<i', mo.field_64)
            oimg[0x68:0x6c] = struct.pack('<i', mo.field_68)
            oimg[0xc0:0xc4] = struct.pack('<f', mo.field_c0)
            for i in range(3):
                oimg[0x158 + 4 * i:0x15c + 4 * i] = struct.pack('<f', mo.position[i])
            m.write(obj, oimg)
            try:
                got = m.call(ROUTINES['create_object'][0], [obj], ecx=scene_addr) & 0xff
            except cm.CaseError as error:
                ok, detail = False, {'stop': str(error), 'type': mo.type}
                break
            want = lib.mu_charsel_create_object(ctypes.byref(scene), world, ctypes.byref(mo), host.fn, None)
            cimg = m.read(obj, 0x400)
            want_obj = (mo.type, mo.field_64, mo.field_68, fb(mo.field_c0))
            got_obj = (struct.unpack_from('<i', cimg, 0x5c)[0], struct.unpack_from('<i', cimg, 0x64)[0],
                       struct.unpack_from('<i', cimg, 0x68)[0], struct.unpack_from('<I', cimg, 0xc0)[0])
            simg = m.read(scene_addr, 0x8c)
            want_scene = b''.join(struct.pack('<f', scene.position[k][i]) for k in range(5) for i in range(3)) + \
                b''.join(struct.pack('<f', scene.angle[k][i]) for k in range(5) for i in range(3))
            if got != want or got_obj != want_obj or simg[0x14:0x8c] != want_scene:
                ok, detail = False, {'type': mo.type, 'ret': (got, want), 'obj': (got_obj, want_obj)}
                break
            for index in indices:
                if h.record_image(index) != host.image(index):
                    ok, detail = False, {'type': mo.type, 'record': index,
                                         'diff': diff_bytes(h.record_image(index), host.image(index))}
                    break
            if not ok:
                break
        tally.cover('create_object: steps', steps)
        tally.add('CreateObject 0x00daa2b2 + SetCharacterPosition 0x00da9ff3 (map-object sequences)', ok, detail)


def family_set_position(h, lib, tally, g, count):
    for number in range(count):
        slot = g.choice([0, 1, 2, 3, 4, 9, 17, 399, 400, -1, -2, 0x7fffffff, g.randint(5, 398)])
        indices = sorted({0, 1, 2, 3, 4} | ({slot} if 0 <= slot < 400 else set()))
        records = {i: random_record(g, i) for i in indices}
        h.begin(records)
        m = h.m
        scene_addr = m.alloc(0x8c, align=16)
        scene = Scene()
        image = bytearray(0x8c)
        for k in range(5):
            for i in range(3):
                p, a = f32(g.uniform(-20000, 20000)), f32(g.uniform(-360, 360))
                scene.position[k][i], scene.angle[k][i] = p, a
                image[0x14 + 12 * k + 4 * i:0x18 + 12 * k + 4 * i] = struct.pack('<f', p)
                image[0x50 + 12 * k + 4 * i:0x54 + 12 * k + 4 * i] = struct.pack('<f', a)
        m.write(scene_addr, image)
        host = Records(records)
        try:
            got = m.call(ROUTINES['set_character_position'][0], [slot], ecx=scene_addr) & 0xff
        except cm.CaseError as error:
            tally.add('SetCharacterPosition 0x00da9ff3', False, {'stop': str(error), 'slot': slot})
            continue
        want = lib.mu_charsel_set_character_position(ctypes.byref(scene), slot, host.fn, None)
        ok = got == want and all(h.record_image(i) == host.image(i) for i in indices)
        tally.add('SetCharacterPosition 0x00da9ff3', ok, {'slot': slot, 'ret': (got, want)})


HELMS = [0x18e6, 0x18e8, 0x18f0, 0x18f1, 0x18f2, 0x18f3, 0x1925, 0x1927, 0x192a, 0x192c, 0x193d, 0x193e, 0x193f,
         0x19a0, 0x19a1, 0x1a35, 0x1a5f]


def family_scale(h, lib, tally, g, count):
    for number in range(count):
        index = g.choice([0, 1, 5, 9, g.randint(0, 399)])
        image = bytearray(random_record(g, index))
        image[0x0e] = 1 if g.random() < 0.08 else 0
        image[0x12] = number & 0xff if number < 256 else g.getrandbits(8)
        helm = g.choice(HELMS + [0xffff, 0x3700 + g.randint(0, 80), g.getrandbits(16), 0x18e7, 0x1a60])
        image[0x1c4 + 0x3fc:0x1c6 + 0x3fc] = struct.pack('<H', helm)
        records = {index: bytes(image)}
        case = h.begin(records)
        m = h.m
        scene = g.choice([5, 5, 6, 3, 4])
        world = g.choice([0x5d, 0, 0x12, 0x35])
        m.write(0x01d1df70, struct.pack('<i', scene))
        m.write(0x01cf15fc, struct.pack('<i', world))
        case.event_world = 1 if g.random() < 0.15 else 0
        b1, b2 = (1 if g.random() < 0.1 else 0), (1 if g.random() < 0.1 else 0)
        case.buff = {0x1a8: b1, 0x1a9: b2}
        host = Records(records)
        inputs = ScaleInputs(scene, world, case.event_world, b1, b2)
        log = Log()
        try:
            m.call(ROUTINES['character_scale'][0], [case.table + index * RECORD])
        except cm.CaseError as error:
            tally.add('SetCharacterScale 0x01394f6f', False, {'stop': str(error)})
            continue
        lib.mu_charsel_character_scale(host.fn(None, index), 0x40000000 + (index << 16), ctypes.byref(inputs),
                                       ctypes.byref(log))
        got_ev, want_ev = h.client_events(), c_events(log)
        ok = got_ev == want_ev and h.record_image(index) == host.image(index)
        tally.add('SetCharacterScale 0x01394f6f', ok,
                  {'class': image[0x12], 'scene': scene, 'events': (got_ev, want_ev),
                   'diff': diff_bytes(h.record_image(index), host.image(index))})


def family_create_hero(h, lib, tally, g, count):
    for number in range(count):
        slot = g.choice([0, 1, 2, 3, 4, 7, 9, g.randint(10, 399), 400, -1])
        indices = [slot] if 0 <= slot < 400 else []
        records = {i: random_record(g, i) for i in indices}
        case = h.begin(records)
        m = h.m
        scene = g.choice([5, 5, 5, 3, 6])
        world = g.choice([0x5d, 0x5e])
        m.write(0x01d1df70, struct.pack('<i', scene))
        m.write(0x01cf15fc, struct.pack('<i', world))
        case.event_world = 1 if g.random() < 0.1 else 0
        b1, b2 = (1 if g.random() < 0.1 else 0), (1 if g.random() < 0.1 else 0)
        case.buff = {0x1a8: b1, 0x1a9: b2}
        cls, skin = g.getrandbits(8), g.getrandbits(8)
        x, y, angle = f32(g.uniform(0, 26000)), f32(g.uniform(0, 26000)), f32(g.uniform(-360, 360))
        host = Records(records)
        inputs = ScaleInputs(scene, world, case.event_world, b1, b2)
        log = Log()
        try:
            got = m.call(ROUTINES['create_hero'][0], [slot, cls, skin, fb(x), fb(y), fb(angle)])
        except cm.CaseError as error:
            tally.add('CreateHero 0x0137f824', False, {'stop': str(error)})
            continue
        want = lib.mu_charsel_create_hero(slot, cls, skin, x, y, angle, ctypes.byref(inputs), host.fn, None,
                                          ctypes.byref(log))
        got_ref = case.ref(got) if got else 0
        want_ref = 0
        if want:
            found = host.address_index(want)
            want_ref = 0x40000000 + (found[0] << 16) + found[1] if found else -1
        got_ev, want_ev = h.client_events(), c_events(log)
        ok = got_ref == want_ref and got_ev == want_ev and all(h.record_image(i) == host.image(i) for i in indices)
        tally.add('CreateHero 0x0137f824', ok, {'slot': slot, 'scene': scene, 'ret': (got_ref, want_ref),
                                                'events': (got_ev, want_ev)})


def frame_scenario(g):
    f = Frame()
    f.initialised = 1 if g.random() < 0.95 else 0
    f.protocol = g.choice([0x33, 0x34, 0x35, 0x35, 0x32, 0x40])
    f.selected = g.choice([-1, 0, 1, 2, 3, 4, 5, 9, 10, 17, 399, 400])
    f.shown = g.choice([-1, f.selected, 0, 1, 4, 9, 12])
    f.world_time = g.choice([0.0, f32(g.uniform(0, 1e5)), f32(g.uniform(0, 5e6)), f32(g.uniform(0, 3e7))])
    f.mouse_x, f.mouse_y = g.randint(0, 640), g.randint(0, 480)
    for i in range(3):
        f.record_position[i] = f32(g.uniform(0, 26000))
    f.pick = g.choice([-1, -1, 0, 3, -5])
    f.input_byte_1f = 1 if g.random() < 0.4 else 0
    f.enter_refused = 1 if g.random() < 0.3 else 0
    f.screen_width = g.choice([640, 800, 1024, 1280, 1728, 1920, 853])
    f.quest_object = 1 if g.random() < 0.3 else 0
    return f


def family_render(h, lib, tally, g, count):
    for number in range(count):
        f = frame_scenario(g)
        indices = set(range(10))
        for v in (f.selected, f.shown):
            if 0 <= v < 400:
                indices.add(v)
        records = {i: random_record(g, i) for i in sorted(indices)}
        case = h.begin(records)
        m = h.m
        case.pick, case.enter_refused, case.screen_width = f.pick, f.enter_refused, f.screen_width
        case.quest_object = f.quest_object
        m.write(0x0bdc5ca2, bytes([f.initialised]))
        m.write(0x06fca2c4, struct.pack('<i', f.protocol))
        m.write(0x01cf1864, struct.pack('<i', f.selected))
        m.write(0x01cf1154, struct.pack('<i', f.shown))
        m.write(0x06fce370, struct.pack('<f', f.world_time))
        m.write(0x0bdc5ad8, struct.pack('<ii', f.mouse_x, f.mouse_y))
        m.write(CRT_MATH_MODE, struct.pack('<I', g.choice([0, 1])))
        m.write(0x0bdc597c, b'\x07')
        m.uc.mem_write(WORLD_INFO + 0xc, struct.pack('<I', CAMERA_RECORD))
        m.uc.mem_write(CAMERA_RECORD + 0xc, struct.pack('<3f', *f.record_position))
        m.uc.mem_write(ID['INPUT'] + 0x1f, bytes([f.input_byte_1f]))
        host = Records(records)
        fog = c_uint8(7)
        log = Log()
        try:
            got = m.call(ROUTINES['render'][0], []) & 0xff
        except cm.CaseError as error:
            tally.add('RenderCharacterScene 0x018576b3', False, {'stop': str(error)})
            continue
        want = lib.mu_charsel_render(ctypes.byref(f), host.fn, None, ctypes.byref(fog), ctypes.byref(log))
        got_ev = merge_gl(h)
        want_ev = c_events(log)
        got_fog = m.read(0x0bdc597c, 1)[0]
        ok = (got == want and got_ev == want_ev and got_fog == fog.value and not log.overflow and
              all(h.record_image(i) == host.image(i) for i in records))
        detail = {'ret': (got, want), 'fog': (got_fog, fog.value), 'selected': f.selected, 'shown': f.shown}
        if got_ev != want_ev:
            first = next((i for i, (a, b) in enumerate(zip(got_ev, want_ev)) if a != b), min(len(got_ev), len(want_ev)))
            detail['first_event'] = (first, got_ev[first:first + 2], want_ev[first:first + 2])
        calls = [e[0] for e in got_ev]
        tally.cover('render: drawn', int(got == 1))
        tally.cover('render: highlight decals', calls.count(0x016cdd5f) // 2)
        tally.cover('render: selected terrain light', calls.count(0x016cacfc))
        tally.cover('render: RenderCharacter', calls.count(0x01363260))
        tally.cover('render: click enters game', calls.count(0x0185a75a))
        tally.add('RenderCharacterScene 0x018576b3', ok, detail)


def merge_gl(h):
    """Client calls in order: client stubs and the two GL imports (recorded by
    the machine) interleaved by their order of occurrence."""
    return [e for e in h.case.merged if e[0] != 0x0095f6db]


def family_tick(h, lib, tally, g, count):
    for number in range(count):
        t = Tick()
        t.scene = 5
        t.initialised = 1 if g.random() < 0.8 else 0
        t.protocol = g.choice([0x33, 0x35, 0x32, 0x40])
        t.selected = g.choice([-1, 0, 1, 4, 9, 10, -2])
        t.shown = g.choice([-1, 0, 2, 9, 11])
        t.gfx_busy = 1 if g.random() < 0.1 else g.choice([0, 0, 2])
        t.gfx_busy_enter = 1 if g.random() < 0.1 else 0
        t.gfx_busy_escape = 1 if g.random() < 0.15 else 0
        t.input_byte_31 = 1 if g.random() < 0.1 else 0
        t.key_enter = 1 if g.random() < 0.5 else 0
        t.key_escape = 1 if g.random() < 0.5 else 0
        t.gfx_flag_78 = 1 if g.random() < 0.15 else 0
        t.gfx_flag_79 = 1 if g.random() < 0.1 else 0
        t.global_1d22d1e = 1 if g.random() < 0.1 else 0
        t.global_6fca007 = 1 if g.random() < 0.1 else 0
        t.ui_byte_464 = 1 if g.random() < 0.1 else 0
        t.gfx_menu_flag = 1 if g.random() < 0.15 else 0
        t.enter_refused = g.choice([0, 0, 1, 2])
        t.ui_byte_65b9 = 1
        t_selected_before = t.selected
        case = h.begin({})
        m = h.m
        m.write(0x01d1df70, struct.pack('<i', t.scene))
        m.write(0x0bdc5ca2, bytes([t.initialised]))
        m.write(0x06fca2c4, struct.pack('<i', t.protocol))
        m.write(0x01cf1864, struct.pack('<i', t.selected))
        m.write(0x01cf1154, struct.pack('<i', t.shown))
        m.write(0x01d22d1e, bytes([t.global_1d22d1e]))
        m.write(0x06fca007, bytes([t.global_6fca007]))
        m.write(0x01d22c7c, struct.pack('<I', ID['MENU']))
        m.uc.mem_write(ID['MENU'] + 0x1c, bytes([t.gfx_menu_flag]))
        m.uc.mem_write(ID['GFX'] + 0x90, struct.pack('<I', ID['GFX_MOVIE']))
        m.uc.mem_write(ID['GFX'] + 0x22c, struct.pack('<I', ID['GFX_22C']))
        m.uc.mem_write(ID['GFX_22C'] + 0x78, bytes([t.gfx_flag_78, t.gfx_flag_79]))
        m.uc.mem_write(ID['INPUT'] + 0x31, bytes([t.input_byte_31]))
        m.uc.mem_write(ID['UIMNG'] + 0x464, bytes([t.ui_byte_464]))
        m.uc.mem_write(ID['UIMNG'] + 0x65b9, bytes([t.ui_byte_65b9]))
        case.busy = [t.gfx_busy, t.gfx_busy_enter if t.key_enter and not t.input_byte_31 else t.gfx_busy_escape]
        case.keys = {0x0d: t.key_enter, 0x1b: t.key_escape}
        case.enter_refused = t.enter_refused
        log = Log()
        try:
            m.call(ROUTINES['tick'][0], [])
        except cm.CaseError as error:
            tally.add('scene-5 logic tick 0x01856e6c', False, {'stop': str(error)})
            continue
        lib.mu_charsel_tick_step(ctypes.byref(t), ctypes.byref(log))
        got_ev, want_ev = merge_gl(h), c_events(log)
        got_state = (m.read(0x0bdc5ca2, 1)[0], struct.unpack('<i', m.read(0x01cf1864, 4))[0],
                     bytes(m.uc.mem_read(ID['UIMNG'] + 0x65b9, 1))[0])
        want_state = (t.initialised, t.selected, t.ui_byte_65b9)
        ok = got_ev == want_ev and got_state == want_state
        detail = {'state': (got_state, want_state)}
        if got_ev != want_ev:
            first = next((i for i, (a, b) in enumerate(zip(got_ev, want_ev)) if a != b), min(len(got_ev), len(want_ev)))
            detail['first_event'] = (first, got_ev[first:first + 2], want_ev[first:first + 2])
        calls = [e[0] for e in got_ev]
        tally.cover('tick: scene created', calls.count(0x01851540))
        tally.cover('tick: Enter starts loading', calls.count(0x0185a75a))
        tally.cover('tick: Enter refused by 0x009a5029', int(0x009a5029 in calls and 0x0185a75a not in calls))
        tally.cover('tick: Esc opens the GFx menu', calls.count(0x00c8c8b1))
        tally.cover('tick: Esc closes the GFx window', calls.count(0x00b49bf4))
        tally.cover('tick: selection taken from 0x01cf1154', int(got_state[1] != t_selected_before))
        tally.add('scene-5 logic tick 0x01856e6c', ok, detail)


# Plausible reconstruction mistakes; each must be detected.
MUTATIONS = [
    ('every slot uses its own marker', 'scene->position[1][i]', 'scene->position[slot < 5 && slot >= 0 ? slot : 1][i]',
     'set_position'),
    ('marker 4 yaw 30', '60.0f, 35.0f}', '60.0f, 30.0f}', 'create_object'),
    ('types 0x3c/0x3d hidden', 'case 0x3c: case 0x3d:\n        object->field_c0', 'case 0x3c: case 0x3d:\n        object->field_68 = -2;\n        object->field_c0',
     'create_object'),
    ('scene-5 scale 1.8', '1.7f);   /* 0x01a9a5a4 */', '1.8f);   /* 0x01a9a5a4 */', 'scale'),
    ('class 11 part scale on slot 2', 'nibble == 11 && k == 1', 'nibble == 11 && k == 2', 'scale'),
    ('hero light 0.4', 'MU_OBJ_LIGHT + 4 * i, 0.3f', 'MU_OBJ_LIGHT + 4 * i, 0.4f', 'create_hero'),
    ('mount height 190.5', 'mount == 0x1a03 ? 194.5f', 'mount == 0x1a03 ? 190.5f', 'render'),
    ('highlight pulse 0.25', 'float value = s * 0.3f;', 'float value = s * 0.25f;', 'render'),
    ('decal rotation not mirrored', 'float t = pass == 0 ? f->world_time : -f->world_time;', 'float t = f->world_time;',
     'render'),
    ('shown character needs no visible flag', ' && shown[MU_CHARSEL_OBJECT + MU_OBJ_VISIBLE]', '', 'render'),
    ('Enter keeps the old selection', 'if (t->shown >= 0)\n            t->selected = t->shown;', '', 'tick'),
    ('Enter accepts slot 10', 't->selected >= MU_CHARSEL_LIST', 't->selected > MU_CHARSEL_LIST', 'tick'),
]


def run_mutations(h, seed, count):
    import shutil
    import tempfile
    results = []
    table = {name: function for name, function, weight in FAMILIES}
    with tempfile.TemporaryDirectory() as scratch:
        for label, old, new, family in MUTATIONS:
            target = Path(scratch) / 'charsel'
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(ROOT / 'reconstructed' / 'charsel', target, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
            source = (target / 'charsel.c').read_text()
            if source.count(old) != 1:
                raise ValueError(f'mutation anchor not unique: {label}')
            (target / 'charsel.c').write_text(source.replace(old, new))
            lib = load_library(target)
            tally = Tally()
            table[family](h, lib, tally, random.Random(f'{seed}:{family}'), count)
            bad = sum(r['mismatches'] for r in tally.results.values())
            results.append({'mutation': label, 'family': family, 'mismatches': bad,
                            'cases': sum(r['cases'] for r in tally.results.values())})
    return results


FAMILIES = [
    ('set_position', family_set_position, 1.0),
    ('create_object', family_create_object, 1.0),
    ('scale', family_scale, 1.0),
    ('create_hero', family_create_hero, 1.0),
    ('render', family_render, 1.0),
    ('tick', family_tick, 1.0),
]


def main(argv=None):
    import os
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT',
                                                         str(ROOT / 'evidence/x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get(
        'MU_IMAGE_DATA', str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--cases', type=int, default=200)
    parser.add_argument('--seed', type=int, default=0x43534c)
    parser.add_argument('--only', default=None)
    parser.add_argument('--output', default=None)
    parser.add_argument('--print-pins', action='store_true')
    parser.add_argument('--mutations', action='store_true', help='also check that planted mistakes are detected')
    args = parser.parse_args(argv)
    text = Path(args.text).read_bytes()
    data = Path(args.data).read_bytes()
    if len(text) != TEXT_BYTES or hashlib.sha256(text).hexdigest() != TEXT_SHA256:
        raise SystemExit('restored text does not match the pinned capture')
    if len(data) != DATA_BYTES or hashlib.sha256(data).hexdigest() != DATA_SHA256:
        raise SystemExit('second section does not match the pinned capture')
    pins = {}
    for name, (start, end, _) in ROUTINES.items():
        pins[name] = hashlib.sha256(text[start - cm.TEXT_BASE:end - cm.TEXT_BASE]).hexdigest()
        if name in PINNED and PINNED[name] != pins[name]:
            raise SystemExit(f'pinned routine {name} changed')
    if args.print_pins:
        print(json.dumps(pins, indent=1))
    h = Harness(text, data)
    lib = load_library()
    tally = Tally()
    only = set(args.only.split(',')) if args.only else None
    started = time.time()
    for name, function, weight in FAMILIES:
        if only and name not in only:
            continue
        function(h, lib, tally, random.Random(f'{args.seed}:{name}'), max(1, int(args.cases * weight)))
    mutation_results = None
    if args.mutations:
        mutation_results = run_mutations(h, args.seed, max(40, args.cases // 4))
        for entry in mutation_results:
            print(f"mutation {entry['mutation']:44s} {entry['mismatches']:5d}/{entry['cases']} detected")
    total = sum(r['cases'] for r in tally.results.values())
    bad = sum(r['mismatches'] for r in tally.results.values())
    for name, r in tally.results.items():
        print(f"{name:80s} {r['cases']:6d} cases {r['mismatches']:5d} mismatches")
        if r['first'] is not None:
            print('    first:', json.dumps(r['first'], default=str)[:900])
    print(f'total {total} cases, {bad} mismatches, {time.time() - started:.1f} s')
    print('coverage:', json.dumps(tally.coverage))
    if args.output:
        report = {'routines': {k: {'start': hex(v[0]), 'end': hex(v[1]), 'sha256': pins[k]} for k, v in ROUTINES.items()},
                  'results': tally.results, 'coverage': tally.coverage, 'mutations': mutation_results,
                  'seed': args.seed, 'cases': args.cases}
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    undetected = [m['mutation'] for m in (mutation_results or []) if m['mismatches'] == 0]
    if undetected:
        print('undetected mutations:', undetected)
    return 1 if bad or undetected else 0


if __name__ == '__main__':
    sys.exit(main())
