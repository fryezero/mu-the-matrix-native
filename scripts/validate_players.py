#!/usr/bin/env python3
"""Compare reconstructed/players with the client's remote-player routines (NATIVE-PLAYERS-001).

The client routines run in Unicorn over the pinned restored text and second
image section (scripts/client_ui_machine.py); every result is compared with
reconstructed/players/libremoteplayers (ctypes) on the same synthetic
CHARACTER record, equipment bytes, packets and host answers:

* helpers    the class byte 0x0139ca62, the item level 0x01395741, the class
             skin 0x0139d6a2 (with 0x0095f5cc / 0x0139cb8a), the ride state
             0x0129dc91 and the wing switch 0x0137c7df;
* equipment  ChangeCharacterExt 0x0137b68c: every part slot written, the
             bytes c + 0x15 / 0x16 / 0x31dc / 0x322c and the engine calls it
             makes, in order;
* move       the move packet 0x0126568e (opcode 0x3d): the character fields
             and the PathFinding2 / SetPlayerWalk calls;
* step       the remote move step 0x013b852a: the path, walk, stop, action
             and position calls and the fields they leave.

Modelled explicitly (not client code): the key -> character lookup, the
engine services the routines call (effects, the mount manager, the path
finder, MovePath, MoveCharacterPosition, SetPlayerWalk/Stop, SetAction, the
skill table), recorded with their arguments and answered from the case.
Two sites of ChangeCharacterExt (0x0137b8c9 and 0x0137b901) jump into
protection-patched bytes outside the restored text; they are modelled as
"not one of the listed helper codes" and the domain excludes the helper
codes 0xa0..0xe0 (see docs/research/client-remote-players.md).  Every other
executed block must lie in the allowlisted client bodies.  Negative controls
plant mistakes into the library's inputs and must be detected.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
try:
    from unicorn.x86_const import UC_X86_REG_EFLAGS
except ImportError:  # pragma: no cover - the portable tests use the ctypes views only
    UC_X86_REG_EFLAGS = None

DEFAULT_TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DEFAULT_DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = ROOT/f'reconstructed/players/libremoteplayers.{SUFFIX}'
SECURITY_COOKIE = 0x01cf65c0

CLASS_BYTE, ITEM_LEVEL, CLASS_SKIN, CLASS_LOW, CLASS_INDEX = 0x0139ca62, 0x01395741, 0x0139d6a2, 0x0095f5cc, 0x0139cb8a
WING, HELPER_STATE, CHANGE_EQUIP = 0x0137c7df, 0x0129dc91, 0x0137b68c
MOVE_PACKET, MOVE_STEP, WORLD_MODE4 = 0x0126568e, 0x013b852a, 0x00e3068f
HELPER_GET, TRANSFORMED, PET_GET, VEC_AT, VEC_PTR = 0x0129dcda, 0x00b9929c, 0x0129de01, 0x00cfc922, 0x00cfc94a
HERO, HERO_KEY, WORLD = 0x0a39d754, 0x06fca288, 0x01cf15fc
HOLE_A, HOLE_B, HOLE_RETURN = 0x10b3f0b0, 0x10b3f0e0, 0x0137b8ce

# ChangeCharacterExt holds two far jumps into protection-patched bytes: the linear decoder cannot find its end
EXTENTS = {CHANGE_EQUIP: 0x0137c276}


def extent(text, start):
    return EXTENTS.get(start) or cm.function_extent(text, start)


ALLOWED = (CLASS_BYTE, ITEM_LEVEL, CLASS_SKIN, CLASS_LOW, CLASS_INDEX, WING, HELPER_STATE, CHANGE_EQUIP, MOVE_PACKET,
           MOVE_STEP, WORLD_MODE4, HELPER_GET, TRANSFORMED, PET_GET, VEC_AT, VEC_PTR)

# recorded call kinds (remote_players.h)
K = dict(C9EA70=1, HELPER_EFFECT_OFF=2, SET_LIVE=3, HELPER_MODEL=4, EFFECT_24E6=5, EFFECT_24E6_A14=6, MOUNT_RESET=7,
         MOUNT_SET=8, HERO_OPTIONS=9, X9EBF04=10, X9DADF1=11, X1394F6F=12, X1394870=13, PATH=14, SET_WALK=15,
         SET_STOP=16, MOVE_PATH=17, MOVE_POSITION=18, SET_ACTION=19, SEND_MOVE=20, AUTO_NEXT=21, AUTO_REFRESH=22,
         CREATE_ANGLE=23, TERRAIN_HEIGHT=24)
PLANT = None


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


# --------------------------------------------------------------------------- ctypes view of the library

class Slot(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int16), ('level', ctypes.c_uint8), ('option', ctypes.c_uint8), ('ext', ctypes.c_uint8)]


class RPath(ctypes.Structure):
    _fields_ = [('current', ctypes.c_uint8), ('current_float', ctypes.c_uint8), ('count', ctypes.c_uint8),
                ('x', ctypes.c_uint8 * 15), ('y', ctypes.c_uint8 * 15)]


class Character(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int16), ('class_byte', ctypes.c_uint8), ('byte_13', ctypes.c_uint8),
                ('byte_15', ctypes.c_uint8), ('byte_16', ctypes.c_uint8), ('guild_bytes', ctypes.c_uint8 * 5),
                ('pk', ctypes.c_uint8), ('direction', ctypes.c_uint8), ('dead', ctypes.c_uint8),
                ('target', ctypes.c_uint8 * 2), ('byte_2c', ctypes.c_uint8), ('byte_31', ctypes.c_uint8),
                ('movement', ctypes.c_uint8), ('byte_39', ctypes.c_uint8), ('byte_0e', ctypes.c_uint8),
                ('guild', ctypes.c_int16), ('server', ctypes.c_uint16), ('class_word', ctypes.c_int16),
                ('move_speed', ctypes.c_uint16), ('level', ctypes.c_uint16), ('max_hp', ctypes.c_uint32),
                ('hp', ctypes.c_uint32), ('tile', ctypes.c_int32 * 2), ('stunned', ctypes.c_uint8),
                ('ride_state', ctypes.c_uint8), ('helper', ctypes.c_uint16), ('field_3230', ctypes.c_int32),
                ('transformed', ctypes.c_uint8), ('pets', ctypes.c_int32 * 3), ('pet_index', ctypes.c_int32),
                ('byte_31dc', ctypes.c_uint8), ('elemental', ctypes.c_int32), ('byte_327c', ctypes.c_uint8),
                ('field_3330', ctypes.c_float), ('skill', ctypes.c_int32), ('slots', Slot * 11),
                ('path', RPath), ('name', ctypes.c_char * 11),
                ('model', ctypes.c_int32), ('action', ctypes.c_uint16), ('prior_action', ctypes.c_uint16),
                ('kind', ctypes.c_uint8), ('live', ctypes.c_uint8), ('byte_43', ctypes.c_uint8),
                ('position', ctypes.c_float * 3), ('angle', ctypes.c_float * 3)]


class Call(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int32), ('a', ctypes.c_int32), ('b', ctypes.c_int32), ('c', ctypes.c_int32),
                ('d', ctypes.c_int32)]


class Calls(ctypes.Structure):
    _fields_ = [('list', Call * 32), ('count', ctypes.c_int32)]


PATHFN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                          ctypes.POINTER(RPath), ctypes.c_int32)
MOVEFN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(Character))
VOIDFN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Character))
ACTIONFN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Character), ctypes.c_int32)


class Env(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('world', ctypes.c_int32), ('scene_state', ctypes.c_int32),
                ('is_hero', ctypes.c_uint8), ('hero_key_match', ctypes.c_uint8), ('hero_moving', ctypes.c_uint8),
                ('skill_group_7', ctypes.c_uint8), ('path_finding2', PATHFN), ('move_path', MOVEFN),
                ('move_character_position', VOIDFN), ('set_player_walk', VOIDFN), ('set_player_stop', VOIDFN),
                ('set_action', ACTIONFN)]


def load_library(path=LIB):
    import subprocess
    if not Path(path).exists():
        subprocess.run(['make', '-C', str(Path(path).parent)], check=True, capture_output=True)
    lib = ctypes.CDLL(str(path))
    P = ctypes.POINTER
    lib.mu_rp_class_byte.argtypes = [ctypes.c_uint8]
    lib.mu_rp_class_byte.restype = ctypes.c_uint8
    lib.mu_rp_item_level.argtypes = [ctypes.c_uint32]
    lib.mu_rp_item_level.restype = ctypes.c_int32
    lib.mu_rp_class_skin.argtypes = [ctypes.c_uint8]
    lib.mu_rp_class_skin.restype = ctypes.c_uint8
    lib.mu_rp_wing.argtypes = [ctypes.c_char_p, P(Character)]
    lib.mu_rp_helper_state.argtypes = [ctypes.c_char_p, P(Character)]
    lib.mu_rp_change_equipment.argtypes = [P(Character), ctypes.c_char_p, ctypes.c_int32, P(Env), P(Calls)]
    lib.mu_rp_move_packet.argtypes = [ctypes.c_char_p, P(Character), P(Env), P(Calls)]
    lib.mu_rp_move_packet.restype = ctypes.c_int
    lib.mu_rp_move_step.argtypes = [P(Character), P(Env), P(Calls)]
    return lib


# --------------------------------------------------------------------------- synthetic state

def random_equipment(rng):
    e = bytearray(rng.randrange(256) for _ in range(18))
    if rng.random() < 0.5:
        e[0] = 0xff
        e[0xb] |= 0xf0
    if rng.random() < 0.5:
        e[1] = 0xff
        e[0xc] |= 0xf0
    e[0xf] = (e[0xf] & 0x1f) | rng.choice([0, 0, 0, 0x20, 0x40, 0x60, 0x80])   # the patched-site domain
    if rng.random() < 0.4:   # a class part: code 0x1ff
        e[2] |= 0xf0
        e[8] |= 0x80
        e[0xc] |= 0x0f
    return bytes(e)


def planted_equipment(e):
    """The library's copy of the equipment bytes with the planted mistake (negative controls)."""
    e = bytearray(e)
    if PLANT == 'option_bit':
        e[9] ^= 0x80
    if PLANT == 'level_code':
        e[6] ^= 0x04
    if PLANT == 'wing_level':
        e[0x11] ^= 0x01
    return bytes(e)


def random_character(rng, key):
    c = {'key': key, 'class_byte': rng.randrange(256), 'byte_16': rng.choice([0, 1, 2, 3, 4, 7, 200]),
         'byte_0e': rng.choice([0, 0, 1]), 'model': rng.choice([0xa91] * 6 + [0x7a5, 0x81e, 0x93f, 0x7ac, 0x7d9]),
         'dead': rng.choice([0, 0, 0, 1, 20]), 'movement': rng.choice([0, 0, 1, 1, 0xff]),
         'byte_31': rng.choice([0, 0, 0, 1]), 'byte_2c': 0, 'direction': rng.randrange(16),
         'tile': [rng.randrange(256), rng.randrange(256)], 'target': [rng.randrange(256), rng.randrange(256)],
         'action': rng.choice([0, 1, 3, 4, 8, 9, 0xb, 0x32, 0x4f]), 'class_word': rng.choice([-1, -1, 0, 0x17f, 0x180, 5]),
         'helper': rng.choice([0xffff, 0xffff, 0x1a02, 0x1a03, 0x184b]), 'ride_state': rng.randrange(5),
         'transformed': rng.choice([0, 0, 0, 1]), 'pets': [rng.choice([-1, 0x24e6, 0x24e7, 5]) for _ in range(3)],
         'pet_index': rng.choice([0, 1, 2, -1, 3]), 'skill': rng.choice([0, 1, 7, 42]),
         'position': [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 500))],
         'angle': [0.0, 0.0, f32(rng.uniform(-360, 360))],
         'slots': [{'type': rng.choice([-1, 0xae6, 0x18e6, 0x3700]), 'level': rng.randrange(16),
                    'option': rng.randrange(2), 'ext': rng.randrange(2)} for _ in range(11)],
         'byte_15': rng.randrange(2), 'byte_31dc': rng.choice([0, 0xf, 0x10]),
         'path': [rng.randrange(256) for _ in range(33)]}
    if rng.random() < 0.3:
        c['target'] = list(c['tile'])
    return c


def to_ctypes(c):
    out = Character()
    for k, v in c.items():
        if k == 'slots':
            for i, s in enumerate(v):
                out.slots[i].type, out.slots[i].level, out.slots[i].option, out.slots[i].ext = s['type'], s['level'], s['option'], s['ext']
        elif k == 'path':
            out.path.current, out.path.current_float, out.path.count = v[0], v[1], v[2]
            out.path.x[:] = v[3:18]
            out.path.y[:] = v[18:33]
        elif k in ('tile', 'target', 'pets', 'position', 'angle'):
            getattr(out, k)[:] = v
        else:
            setattr(out, k, v)
    out.live = 1
    out.kind = 1
    return out


def write_character(m, c):
    a = m.alloc(0x3700, define=True)
    m.write(a, b'\0' * 0x3700)
    w = lambda off, fmt, v: m.write(a + off, struct.pack(fmt, v))  # noqa: E731
    w(0x12, '<B', c['class_byte'])
    w(0x15, '<B', c['byte_15'])
    w(0x16, '<B', c['byte_16'])
    w(0x0e, '<B', c['byte_0e'])
    w(0x22, '<B', c['direction'])
    w(0x23, '<B', c['dead'])
    w(0x2c, '<B', c['byte_2c'])
    w(0x2d, '<B', c['target'][0])
    w(0x2e, '<B', c['target'][1])
    w(0x31, '<B', c['byte_31'])
    w(0x38, '<B', c['movement'])
    w(0x3e, '<h', c['key'])
    w(0x26, '<H', c['skill'])
    w(0x146, '<h', c['class_word'])
    w(0x180, '<i', c['tile'][0])
    w(0x184, '<i', c['tile'][1])
    for k, s in enumerate(c['slots']):
        base = 0x1c4 + k * 0x3fc
        w(base, '<h', s['type'])
        w(base + 2, '<B', s['level'])
        w(base + 3, '<B', s['option'])
        w(base + 4, '<B', s['ext'])
    m.write(a + 0x3194, bytes(c['path']))
    w(0x31dc, '<B', c['byte_31dc'])
    w(0x322c, '<B', c['ride_state'])
    w(0x322e, '<H', c['helper'])
    w(0x3234, '<B', c['transformed'])
    for i, p in enumerate(c['pets']):
        w(0x3238 + 4 * i, '<i', p)
    w(0x3244, '<i', c['pet_index'])
    w(0x3254, '<B', 1)               # live
    w(0x3254 + 0x2a, '<H', c['action'])
    w(0x3254 + 0x3b, '<B', 1)
    w(0x3254 + 0x5c, '<i', c['model'])
    for i, v in enumerate(c['position']):
        w(0x3254 + 0x158 + 4 * i, '<f', v)
    for i, v in enumerate(c['angle']):
        w(0x3254 + 0x164 + 4 * i, '<f', v)
    return a


def read_fields(m, a):
    r = lambda off, fmt: struct.unpack(fmt, m.read(a + off, struct.calcsize(fmt)))[0]  # noqa: E731
    out = {'byte_15': r(0x15, '<B'), 'byte_16': r(0x16, '<B'), 'direction': r(0x22, '<B'), 'byte_2c': r(0x2c, '<B'),
           'target': [r(0x2d, '<B'), r(0x2e, '<B')], 'movement': r(0x38, '<B'), 'tile': [r(0x180, '<i'), r(0x184, '<i')],
           'byte_31dc': r(0x31dc, '<B'), 'ride_state': r(0x322c, '<B'),
           'path': list(m.read(a + 0x3194, 33)),
           'position': [r(0x3254 + 0x158 + 4 * i, '<I') for i in range(3)],
           'angle': [r(0x3254 + 0x164 + 4 * i, '<I') for i in range(3)], 'slots': []}
    for k in range(11):
        base = 0x1c4 + k * 0x3fc
        out['slots'].append({'type': r(base, '<h'), 'level': r(base + 2, '<B'), 'option': r(base + 3, '<B'),
                             'ext': r(base + 4, '<B')})
    return out


def lib_fields(c):
    bits = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]  # noqa: E731
    return {'byte_15': c.byte_15, 'byte_16': c.byte_16, 'direction': c.direction, 'byte_2c': c.byte_2c,
            'target': list(c.target), 'movement': c.movement, 'tile': list(c.tile), 'byte_31dc': c.byte_31dc,
            'ride_state': c.ride_state,
            'path': [c.path.current, c.path.current_float, c.path.count] + list(c.path.x) + list(c.path.y),
            'position': [bits(v) for v in c.position], 'angle': [bits(v) for v in c.angle],
            'slots': [{'type': s.type, 'level': s.level, 'option': s.option, 'ext': s.ext} for s in c.slots]}


# --------------------------------------------------------------------------- the client machine

class Client:
    def __init__(self, text, data):
        self.text = text
        self.m = cm.Machine(text, data)
        for start in ALLOWED:
            self.m.allow((start, extent(text, start)))
        self.cleanup_cache = {}
        # the protection-patched sites of ChangeCharacterExt: mapped so the hooks can run, never executed as code
        self.m.uc.mem_map(0x10b3f000, 0x1000, cm.UC_PROT_ALL)
        self.m.uc.mem_write(HOLE_A, b'\xc3')
        self.m.uc.mem_write(HOLE_B, b'\xc3')
        self.m.stub(HOLE_A, self.hole_a, 0)
        self.m.stub(HOLE_B, self.hole_b, 0)
        self.records = []
        self.install()

    # callee-popped bytes, read from each routine's return (scratch disassembly); 0x009ebf04 begins with a jump into a
    # protector stub, so the linear decoder cannot find its return
    CLEANUP = {0x00b990b0: 0, 0x00eb1015: 8, 0x00eb0e78: 0x18, 0x009c104e: 0, 0x0106ba49: 4, 0x0106b85d: 0xc,
               0x0095f6db: 0, 0x009a13f4: 4, 0x009ebf04: 0, 0x009dadf1: 0, 0x01394f6f: 0, 0x01394870: 0,
               0x00c9ea70: 0, 0x0129f4a5: 4, 0x009b0bc1: 0, 0x00c9d8df: 0, 0x00c9d42a: 0, 0x00b9b476: 0,
               0x0137c724: 0, 0x0095f659: 0, 0x0129cc44: 0, 0x0129c51d: 0x10, 0x016b5cd0: 0, 0x0139002a: 0,
               0x012b0e85: 0, 0x00961620: 4, 0x012affa4: 0, 0x012b0846: 0, 0x0138fe69: 0, 0x0137b351: 0,
               0x016cc9e2: 0, 0x012aed9e: 0}

    def cleanup(self, address):
        if address in self.CLEANUP:
            return self.CLEANUP[address]
        if address not in self.cleanup_cache:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32
            end = cm.function_extent(self.text, address)
            o = address - cm.TEXT_BASE
            rets = {int(ops, 16) if ops else 0
                    for _, _, mn, ops in Cs(CS_ARCH_X86, CS_MODE_32).disasm_lite(self.text[o:end - cm.TEXT_BASE], address)
                    if mn in ('ret', 'retn')}
            if len(rets) != 1:
                raise RuntimeError(f'{address:#x}: returns {sorted(rets)}; add an explicit cleanup')
            self.cleanup_cache[address] = rets.pop()
        return self.cleanup_cache[address]

    def stub(self, address, handler):
        self.m.stub(address, handler, self.cleanup(address))

    def ecx(self):
        return self.m.uc.reg_read(cm.UC_X86_REG_ECX)

    def hole_a(self, m):
        """0x0137b8c9: the stolen compare; modelled as 'no match' (ZF clear) and the return to 0x0137b8ce."""
        uc = m.uc
        uc.reg_write(UC_X86_REG_EFLAGS, uc.reg_read(UC_X86_REG_EFLAGS) & ~0x40)
        uc.reg_write(cm.UC_X86_REG_EIP, HOLE_RETURN)
        return cm.REDIRECT

    def hole_b(self, m):
        return m.fail('the helper switch default (0x0137b901) was reached: outside the validated domain')

    def rec(self, *entry):
        self.records.append(entry)

    def install(self):
        s, m = self.stub, self.m
        # ChangeCharacterExt services
        s(0x00c9ea70, lambda m: self.rec('c9ea70'))
        s(0x00b990b0, lambda m: (self.rec('b990b0', *m.args(2)), 0x7f00f000)[1])
        s(0x00eb1015, lambda m: self.rec('eb1015'))
        s(0x00eb0e78, lambda m: self.rec('eb0e78'))
        s(0x0129f4a5, lambda m: self.rec('set_live', self.ecx(), m.args(1)[0]))
        s(0x009b0bc1, lambda m: self.scene_state)
        s(0x00c9d8df, lambda m: self.rec('effect_24e6', *m.args(5)))
        s(0x00c9d42a, lambda m: self.rec('effect_24e6_a14', *m.args(6)))
        s(0x009c104e, lambda m: (self.rec('mount_mgr', m.args(1)[0]), 0x7f00f100)[1])
        s(0x0106ba49, lambda m: self.rec('mount_reset'))
        s(0x0106b85d, lambda m: self.rec('mount_set', *m.args(3)))
        s(0x00b9b476, lambda m: 0x1234)
        s(0x009ebf04, lambda m: self.rec('9ebf04'))
        s(0x009dadf1, lambda m: self.rec('9dadf1'))
        s(0x01394f6f, lambda m: self.rec('1394f6f'))
        s(0x01394870, lambda m: self.rec('1394870'))
        # the move packet and the step
        s(0x0137c724, lambda m: self.lookup_index(m.args(1)[0]))
        s(0x0095f6db, lambda m: m.args(1)[0])
        s(0x009a13f4, lambda m: self.lookup_character(self.ecx()))
        s(0x0095f659, lambda m: self.hero_state)
        s(0x0129cc44, lambda m: (self.rec('auto_next'), 0)[1])
        s(0x0129c51d, lambda m: self.rec('auto_refresh'))
        s(0x016b5cd0, lambda m: (self.rec('send_move'), 0)[1])
        s(0x012aed9e, lambda m: m.fail('CreateAngle (model 0x7d9) is outside the validated domain'))
        s(0x0139002a, lambda m: self.rec('set_walk'))
        s(0x012b0e85, self.path_finding2)
        s(0x00961620, lambda m: self.skill_record)
        s(0x012affa4, lambda m: self.rec('set_action', m.args(2)[1]))
        s(0x012b0846, lambda m: (self.rec('move_path', m.args(2)[1]), self.arrived)[1])
        s(0x0138fe69, lambda m: self.rec('set_stop'))
        s(0x0137b351, lambda m: self.rec('move_position'))
        s(0x016cc9e2, lambda m: m.fail('RequestTerrainHeight (dead model 0x7a7) is outside the validated domain'))

    def path_finding2(self, m):
        sx, sy, tx, ty, path, _zero, mode = m.args(7)
        self.rec('path', sx, sy, tx, ty, mode)
        found = self.path_answers.pop(0) if self.path_answers else 0
        if found:
            m.write(path, self.path_bytes)
        return found

    def lookup_index(self, key):
        return self.key_index.get(key, 400)

    def lookup_character(self, index):
        return self.index_char.get(index, 0)

    def reset(self, world=0, scene_state=6, hero_key=0x7777, hero_moving=0, skill_group=0):
        m = self.m
        m.reset()
        self.records = []
        m.put32(SECURITY_COOKIE, 0xbb40e64e)
        m.put32(HERO, 0)
        m.put32(HERO_KEY, hero_key)
        m.put32(WORLD, world)
        self.scene_state = scene_state
        self.hero_state = m.alloc(0x20, define=True)
        m.write(self.hero_state, b'\0' * 0x20)
        m.write(self.hero_state + 8, bytes([hero_moving]))
        self.skill_record = m.alloc(0x100, define=True)
        m.write(self.skill_record, b'\0' * 0x100)
        m.put32(self.skill_record + 0x90, skill_group)
        self.key_index, self.index_char = {}, {}
        self.path_answers, self.path_bytes, self.arrived = [], b'', 0


# --------------------------------------------------------------------------- the library side

class LibSide:
    """Env callbacks answering from the same scripted host as the client stubs."""

    def __init__(self, lib, client):
        self.lib, self.client = lib, client
        self.records = []
        self.keep = []

    def env(self, world, scene_state, is_hero=0, hero_key_match=0, hero_moving=0, skill_group_7=0):
        env = Env()
        client = self

        def path(_, sx, sy, tx, ty, path_ptr, mode):
            client.records.append(('path', sx, sy, tx, ty, mode))
            found = client.path_answers.pop(0) if client.path_answers else 0
            if found:
                ctypes.memmove(path_ptr, client.path_bytes, 33)
            return found

        def move_path(_, c):
            client.records.append(('move_path', 1))
            return client.arrived

        def walk(_, c):
            client.records.append(('set_walk',))

        def stop(_, c):
            client.records.append(('set_stop',))

        def position(_, c):
            client.records.append(('move_position',))

        def action(_, c, a):
            client.records.append(('set_action', a))
        cbs = [PATHFN(path), MOVEFN(move_path), VOIDFN(position), VOIDFN(walk), VOIDFN(stop), ACTIONFN(action)]
        self.keep.extend(cbs)
        (env.path_finding2, env.move_path, env.move_character_position, env.set_player_walk, env.set_player_stop,
         env.set_action) = cbs
        env.world, env.scene_state, env.is_hero, env.hero_key_match = world, scene_state, is_hero, hero_key_match
        env.hero_moving, env.skill_group_7 = hero_moving, skill_group_7
        return env


def translate(calls, env_bits):
    """The library's call list in the client's recorded form."""
    out = []
    for i in range(calls.count):
        k = calls.list[i]
        name = {v: n for n, v in K.items()}[k.kind]
        if name == 'C9EA70':
            out.append(('c9ea70',))
        elif name == 'HELPER_EFFECT_OFF':
            out.append(('b990b0', env_bits['c'], k.a & 0xffffffff))
            out.append(('eb1015',))
        elif name == 'SET_LIVE':
            out.append(('set_live', k.a & 0xffffffff, 0))
        elif name == 'HELPER_MODEL':
            out.append(('b990b0', k.a & 0xffffffff, k.b & 0xffffffff))
            out.append(('eb0e78',))
        elif name == 'EFFECT_24E6':
            out.append(('effect_24e6', k.a & 0xffffffff, env_bits['pos'], env_bits['o'], 0, 0))
        elif name == 'EFFECT_24E6_A14':
            out.append(('effect_24e6_a14', k.a & 0xffffffff, env_bits['pos'], env_bits['o'], k.b & 0xffffffff, 0, 0))
        elif name == 'MOUNT_RESET':
            out.append(('mount_mgr', env_bits['c']))
            out.append(('mount_reset',))
        elif name == 'MOUNT_SET':
            arg = 0x1234 if k.b == -2 else k.b
            out.append(('mount_mgr', k.a & 0xffffffff))
            out.append(('mount_set', k.a & 0xffffffff, arg & 0xffffffff, env_bits['c']))
        elif name == 'X9EBF04':
            out.append(('9ebf04',))
        elif name == 'X9DADF1':
            out.append(('9dadf1',))
        elif name == 'X1394F6F':
            out.append(('1394f6f',))
        elif name == 'X1394870':
            out.append(('1394870',))
        elif name == 'PATH':
            out.append(('path', k.a & 0xff, (k.a >> 8) & 0xff, k.b & 0xff, (k.b >> 8) & 0xff, k.c))
        elif name == 'SET_WALK':
            out.append(('set_walk',))
        elif name == 'SET_STOP':
            out.append(('set_stop',))
        elif name == 'MOVE_PATH':
            out.append(('move_path', 1))
        elif name == 'MOVE_POSITION':
            out.append(('move_position',))
        elif name == 'SET_ACTION':
            out.append(('set_action', k.a))
        elif name == 'SEND_MOVE':
            out.append(('send_move',))
        else:
            out.append((name.lower(),))
    return out


# --------------------------------------------------------------------------- sections

def validate_helpers(client, lib, rng, cases):
    m = client.m
    checked = 0
    for v in range(256):
        client.reset()
        got = m.call(CLASS_BYTE, [v]) & 0xff
        want = lib.mu_rp_class_byte(v ^ (8 if PLANT == 'class_byte' else 0))
        assert got == want, f'class byte {v}: client {got} library {want}'
        client.reset()
        got = m.call(ITEM_LEVEL, [v]) & 0xffffffff
        want = lib.mu_rp_item_level(v) & 0xffffffff
        assert got == want, f'item level {v}: client {got} library {want}'
        client.reset()
        got = m.call(CLASS_SKIN, [v]) & 0xff
        want = lib.mu_rp_class_skin(v)
        assert got == want, f'class skin {v}: client {got} library {want}'
        checked += 3
    wings = 0
    for i in range(cases):
        c = random_character(rng, 1)
        e = bytearray(random_equipment(rng))
        if i < 0x67 * 2:   # every switch index, with and without the level nibble
            idx = i % 0x67
            e[4] = (e[4] & ~0xc) | ((idx >> 4) & 3) << 2
            e[8] = (e[8] & ~7) | ((idx >> 3) & 7)
            e[0xf] = (e[0xf] & ~0x1c) | ((idx & 7) << 2)
            e[0x11] = rng.randrange(256) if i >= 0x67 else 0
        e = bytes(e)
        client.reset()
        a = write_character(m, c)
        ep = m.alloc(32, define=True)
        m.write(ep, e + b'\0' * 14)
        m.call(WING, [ep, a])
        m.call(HELPER_STATE, [ep], ecx=a)
        got = read_fields(m, a)
        lc = to_ctypes(c)
        lib.mu_rp_wing(planted_equipment(e), ctypes.byref(lc))
        lib.mu_rp_helper_state(planted_equipment(e), ctypes.byref(lc))
        want = lib_fields(lc)
        for key in ('slots', 'ride_state'):
            assert got[key] == want[key], f'wing/helper case {i} {key}: client {got[key]} library {want[key]}'
        wings += 1
    return {'byte_helpers': checked, 'wing_and_ride_state': wings}


def validate_equipment(client, lib, rng, cases):
    m = client.m
    side = LibSide(lib, client)
    counts = {'cases': 0, 'player_model': 0, 'a14': 0, 'calls': 0}
    for i in range(cases):
        c = random_character(rng, 1)
        if rng.random() < 0.85:
            c['model'] = 0xa91
        e = random_equipment(rng)
        scene = rng.choice([6, 6, 6, 5, 2])
        a14 = rng.choice([0, 0, 0x40000000])
        client.reset(scene_state=scene)
        a = write_character(m, c)
        ep = m.alloc(32, define=True)
        m.write(ep, e + b'\0' * 14)
        m.call(CHANGE_EQUIP, [400, ep, a, a14])
        got = read_fields(m, a)
        got_calls = list(client.records)
        lc = to_ctypes(c)
        calls = Calls()
        env = side.env(0, scene)
        lib.mu_rp_change_equipment(ctypes.byref(lc), planted_equipment(e), a14, ctypes.byref(env), ctypes.byref(calls))
        want = lib_fields(lc)
        bits = {'c': a, 'o': a + 0x3254, 'pos': a + 0x3254 + 0x158}
        want_calls = translate(calls, bits)
        for key in ('slots', 'byte_15', 'byte_16', 'byte_31dc', 'ride_state'):
            assert got[key] == want[key], f'equipment case {i} {key}: client {got[key]} library {want[key]}'
        assert got_calls == want_calls, f'equipment case {i} calls: client {got_calls} library {want_calls}'
        counts['cases'] += 1
        counts['player_model'] += c['model'] == 0xa91
        counts['a14'] += a14 != 0
        counts['calls'] += len(got_calls)
    return counts


def random_path_answers(rng):
    return [rng.choice([0, 1]), rng.choice([0, 1])]


def random_path_bytes(rng):
    n = rng.randrange(2, 16)
    cells = [rng.randrange(256) for _ in range(30)]
    return bytes([0, 0, n] + cells)


def validate_move(client, lib, rng, cases):
    m = client.m
    side = LibSide(lib, client)
    counts = {'cases': 0, 'hero': 0, 'paths': 0, 'teleports': 0, 'ignored': 0}
    for i in range(cases):
        c = random_character(rng, rng.randrange(1, 0x7fff))
        if c['model'] == 0x7d9:
            c['model'] = 0xa91
        world = rng.choice([0, 0, 1, 0x52, 0x5a, 0x5b])
        hero_match = rng.random() < 0.15
        hero_moving = rng.choice([0, 1])
        found = rng.random() < 0.9
        packet = bytes([0xc1, 8, 0x3d, c['key'] >> 8, c['key'] & 0xff, rng.randrange(256), rng.randrange(256),
                        rng.randrange(256)])
        lib_packet, lib_world = packet, world
        if PLANT == 'move_target':
            lib_packet = packet[:5] + bytes([(packet[5] + 1) & 0xff]) + packet[6:]
        if PLANT == 'move_mode':
            lib_world = 0x52 if world == 0 else 0
        client.reset(world=world, hero_key=c['key'] if hero_match else 0x7777, hero_moving=hero_moving)
        a = write_character(m, c)
        if found:
            client.key_index[c['key']] = 5
            client.index_char[5] = a
        answers, pbytes = random_path_answers(rng), random_path_bytes(rng)
        client.path_answers, client.path_bytes = list(answers), pbytes
        pp = m.alloc(16, define=True)
        m.write(pp, packet + b'\0' * 8)
        m.call(MOVE_PACKET, [pp])
        got = read_fields(m, a)
        got_calls = list(client.records)
        lc = to_ctypes(c)
        calls = Calls()
        side.path_answers, side.path_bytes = list(answers), pbytes
        env = side.env(lib_world, 6, hero_key_match=int(hero_match), hero_moving=hero_moving)
        side.records = []
        lib.mu_rp_move_packet(lib_packet, ctypes.byref(lc) if found else None, ctypes.byref(env), ctypes.byref(calls))
        want = lib_fields(lc)
        want_calls = translate(calls, {})
        for key in ('direction', 'target', 'tile', 'movement', 'byte_2c', 'path', 'position', 'angle'):
            assert got[key] == want[key], f'move case {i} {key}: client {got[key]} library {want[key]}'
        assert got_calls == want_calls, f'move case {i} calls: client {got_calls} library {want_calls}'
        counts['cases'] += 1
        counts['hero'] += hero_match
        counts['paths'] += sum(1 for r in got_calls if r[0] == 'path')
        counts['teleports'] += got['tile'] != c['tile'] and not got['movement'] and found and not c['dead']
        counts['ignored'] += not found or c['dead'] != 0
    return counts


def validate_step(client, lib, rng, cases):
    m = client.m
    side = LibSide(lib, client)
    counts = {'cases': 0, 'moving': 0, 'arrived': 0, 'paths': 0, 'keep_action': 0}
    for i in range(cases):
        c = random_character(rng, 1)
        if c['dead'] and c['model'] == 0x7a7:
            c['model'] = 0xa91
        world = rng.choice([0, 0, 1, 0x52, 0x5a])
        skill7 = rng.random() < 0.2
        arrived = rng.choice([0, 1])
        client.reset(world=world, skill_group=7 if skill7 else 3)
        a = write_character(m, c)
        answers, pbytes = random_path_answers(rng), random_path_bytes(rng)
        client.path_answers, client.path_bytes, client.arrived = list(answers), pbytes, arrived
        m.call(MOVE_STEP, [a, a + 0x3254])
        got = read_fields(m, a)
        got_calls = list(client.records)
        lc = to_ctypes(c)
        if PLANT == 'step_direction':
            lc.direction = (lc.direction + 1) & 0xff
        calls = Calls()
        side.path_answers, side.path_bytes, side.arrived = list(answers), pbytes, arrived
        env = side.env(world, 6, skill_group_7=int(skill7))
        lib.mu_rp_move_step(ctypes.byref(lc), ctypes.byref(env), ctypes.byref(calls))
        want = lib_fields(lc)
        want_calls = translate(calls, {})
        for key in ('target', 'tile', 'movement', 'path', 'position', 'angle'):
            assert got[key] == want[key], f'step case {i} {key}: client {got[key]} library {want[key]}'
        assert got_calls == want_calls, f'step case {i} calls: client {got_calls} library {want_calls}'
        counts['cases'] += 1
        counts['moving'] += any(r[0] == 'move_path' for r in got_calls)
        counts['arrived'] += any(r[0] == 'set_stop' for r in got_calls)
        counts['paths'] += sum(1 for r in got_calls if r[0] == 'path')
        counts['keep_action'] += any(r[0] == 'set_action' for r in got_calls)
    return counts


SECTIONS = {'helpers': validate_helpers, 'equipment': validate_equipment, 'move': validate_move, 'step': validate_step}
PLANTS = ['class_byte', 'option_bit', 'level_code', 'wing_level', 'move_target', 'move_mode', 'step_direction']


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', default=str(DEFAULT_TEXT))
    parser.add_argument('--data', default=str(DEFAULT_DATA))
    parser.add_argument('--library', default=str(LIB))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--seed', type=int, default=20261021)
    parser.add_argument('--only', default='')
    parser.add_argument('--output', default='')
    parser.add_argument('--negative', type=int, default=0, help='cases per planted mistake (0: skip the controls)')
    args = parser.parse_args()
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    if hashlib.sha256(text).hexdigest() != TEXT_SHA256 or hashlib.sha256(data).hexdigest() != DATA_SHA256:
        raise SystemExit('the pinned restored text and image data are required')
    lib = load_library(args.library)
    client = Client(text, data)
    only = [s for s in args.only.split(',') if s]
    result = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'seed': args.seed, 'cases': args.cases,
              'bodies': {f'{a:#010x}': hashlib.sha256(text[a - cm.TEXT_BASE:extent(text, a) - cm.TEXT_BASE]).hexdigest()[:16]
                         for a in (CLASS_BYTE, ITEM_LEVEL, CLASS_SKIN, WING, HELPER_STATE, CHANGE_EQUIP, MOVE_PACKET, MOVE_STEP)},
              'sections': {}}
    ok = True
    for name, fn in SECTIONS.items():
        if only and name not in only:
            continue
        rng = random.Random(f'{args.seed}:{name}')
        try:
            result['sections'][name] = {'result': fn(client, lib, rng, args.cases), 'mismatches': 0}
        except (AssertionError, cm.CaseError) as error:
            ok = False
            result['sections'][name] = {'error': str(error)[:2000], 'mismatches': 1}
        print(name, json.dumps(result['sections'][name])[:600], flush=True)
    if args.negative:
        global PLANT
        caught = {}
        for plant in PLANTS:
            PLANT = plant
            found = None
            for name, fn in SECTIONS.items():
                try:
                    fn(client, lib, random.Random(f'{args.seed}:{plant}:{name}'), args.negative)
                except (AssertionError, cm.CaseError) as error:
                    found = f'{name}: {str(error)[:120]}'
                    break
            caught[plant] = found
            print('negative', plant, 'caught' if found else 'NOT CAUGHT', (found or '')[:100], flush=True)
            ok = ok and found is not None
        PLANT = None
        result['negative_controls'] = {'planted': len(caught), 'caught': sum(1 for v in caught.values() if v),
                                       'sections': caught}
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
