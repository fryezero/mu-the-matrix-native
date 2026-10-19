#!/usr/bin/env python3
"""Compare reconstructed/names with the client's hudPlayerName game side (NATIVE-NAMES-001).

The client routines run in Unicorn over the pinned restored text and second
image section (scripts/client_ui_machine.py).  Every routine's result is
compared with reconstructed/names/libnames (ctypes) on the same synthetic
CHARACTER records, handler state and host answers:

* height   the head height 0x00c8526e (ride items, wings, classes, state 2);
* name     the name builder 0x00c84d8a (name kind 0/1/2, GlobalText 4595);
* colors   0x00c84f00 (class colours), 0x00c8502c (PK level), 0x00c85093 (guild);
* gens     0x00c84d08 (gens frame) and 0x00c851f4 (strife gens);
* guild    0x00c8510c over a synthetic guild table 0x0b44a6f4;
* addinfo  addInfo 0x00c82fd1: the GFx object it invokes and the entry it inserts;
* update   the per-frame update 0x00c81d1e (character part) over multi-frame
           sequences: every GFx operation in order and the entries' state;
* sethp, remove, select: 0x00c83afa, 0x00c83a04, 0x00c83c9a;
* bubble   the chat bubble 0x0169d87f with setMessage 0x00c83d2a.

Modelled explicitly (not client code): the GFx value and display-info API,
std::string / std::wstring and the formatter (format(fmt) % a % b, the
results are computed with %s/%d substitution), the std::map nodes and
iterators of the handler's maps, the key -> character lookup, the
projection 0x0184a3ce (verified by NATIVE-FRAME-001; here a recorded
function of its input), the party window, option and singleton flags, the
damage-type table and GlobalText.  Every other executed block must lie in the
allowlisted client functions.  Negative controls plant mistakes into a copy
of the library's inputs and must be detected.
"""
import argparse
from collections import Counter
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402

DEFAULT_TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DEFAULT_DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = ROOT/f'reconstructed/names/libnames.{SUFFIX}'
SECURITY_COOKIE = 0x01cf65c0

# client routines (investigator labels)
HEIGHT, NAME, CLASS_COLOR, PK_COLOR, GUILD_COLOR = 0x00c8526e, 0x00c84d8a, 0x00c84f00, 0x00c8502c, 0x00c85093
GENS_FRAME, STRIFE, GUILD_TEXT, SERVER_TEXT = 0x00c84d08, 0x00c851f4, 0x00c8510c, 0x00c850e1
ADD_INFO, UPDATE, SET_HP, REMOVE, SELECT, MESSAGE, BUBBLE = (0x00c82fd1, 0x00c81d1e, 0x00c83afa, 0x00c83a04,
                                                             0x00c83c9a, 0x00c83d2a, 0x0169d87f)
ENTRY_CTOR = 0x00c8734a
HERO, HERO_ATTR, DUEL_KEY, DUEL_HP, WORLD = 0x0a39d754, 0x01d1df1c, 0x06fca290, 0x06fca28c, 0x01cf15fc
OPTIONS = 0x01d22c7c
GUILDS = 0x0b44a6f4
WINDOW_MANAGER = 0x01d22c60

ALLOWED = (HEIGHT, NAME, CLASS_COLOR, PK_COLOR, GUILD_COLOR, GENS_FRAME, STRIFE, GUILD_TEXT, SERVER_TEXT, ADD_INFO,
           UPDATE, SET_HP, REMOVE, SELECT, MESSAGE, BUBBLE, ENTRY_CTOR,
           0x0129dcda, 0x0095f5cc, 0x00b3ce48, 0x0129deaa, 0x0129de7c, 0x00aa0f0f, 0x00cfc936, 0x00cfc922,
           0x0095f160, 0x0095f602, 0x00da9d49, 0x00c87c7b, 0x0090edb0, 0x00b67eb6, 0x008e7940, 0x008e53e0,
           0x0096167d, 0x00a0020f, 0x00c8526e)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def s32(x):
    return struct.unpack('<i', struct.pack('<I', x & 0xffffffff))[0]


# --------------------------------------------------------------------------- ctypes view of the library

TEXT = 256


class Character(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int16), ('guild', ctypes.c_int16), ('class_byte', ctypes.c_uint8),
                ('guild_relation', ctypes.c_uint8), ('gens', ctypes.c_uint8), ('pk', ctypes.c_uint8),
                ('kind', ctypes.c_uint8), ('live', ctypes.c_uint8), ('gens_rank', ctypes.c_uint8),
                ('monster_class', ctypes.c_int16), ('level', ctypes.c_uint16), ('height', ctypes.c_uint16),
                ('wing', ctypes.c_int16), ('ride', ctypes.c_uint16), ('resist', ctypes.c_uint16 * 4),
                ('max_hp', ctypes.c_uint32), ('hp', ctypes.c_uint32), ('mark', ctypes.c_int32),
                ('elemental', ctypes.c_int32), ('name_kind', ctypes.c_int32), ('position', ctypes.c_float * 3),
                ('server', ctypes.c_char * TEXT), ('duel_name', ctypes.c_char * TEXT), ('name', ctypes.c_char * TEXT)]


class Entry(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int32), ('type', ctypes.c_int32), ('name', ctypes.c_char * TEXT),
                ('x', ctypes.c_float), ('y', ctypes.c_float), ('hp', ctypes.c_int32), ('show', ctypes.c_uint8),
                ('elemental', ctypes.c_int32), ('att', ctypes.c_int32 * 4), ('damage_type', ctypes.c_uint8 * 3),
                ('hp_show', ctypes.c_uint8), ('name_show', ctypes.c_uint8), ('strife', ctypes.c_uint8),
                ('gens', ctypes.c_int32), ('guild', ctypes.c_char * TEXT), ('server', ctypes.c_char * TEXT),
                ('flag_a0', ctypes.c_uint8), ('has_mc', ctypes.c_uint8), ('addinfo_show', ctypes.c_uint8),
                ('mc_visible', ctypes.c_uint8)]


class Window(ctypes.Structure):
    _fields_ = [('item_height', ctypes.c_int32), ('item_offset', ctypes.c_int32), ('height_player', ctypes.c_int32),
                ('height_wing', ctypes.c_int32), ('height_ride_a', ctypes.c_int32), ('height_ride_b', ctypes.c_int32),
                ('height_ride_c', ctypes.c_int32), ('height_ride', ctypes.c_int32), ('height_state', ctypes.c_int32),
                ('height_ride_d', ctypes.c_int32), ('monster_view', ctypes.c_uint8), ('selected', ctypes.c_int32),
                ('item_view', ctypes.c_uint8), ('count', ctypes.c_int32), ('entries', Entry * 400)]


PROJECT = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                           ctypes.POINTER(ctypes.c_float))
STATE2 = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(Character))
DAMAGE = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
GUILD = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_char_p),
                         ctypes.POINTER(ctypes.c_char_p))
PARTY = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int32))
LOOKUP = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)


class Env(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('hero', ctypes.POINTER(Character)), ('hero_level', ctypes.c_int32),
                ('hero_hp', ctypes.c_int32), ('hero_max_hp', ctypes.c_int32), ('duel_key', ctypes.c_int32),
                ('duel_hp', ctypes.c_int32), ('world', ctypes.c_int32), ('name_option', ctypes.c_uint8),
                ('hero_bar_a', ctypes.c_uint8), ('hero_bar_b', ctypes.c_uint8), ('server_flag', ctypes.c_uint8),
                ('gens_option', ctypes.c_uint8), ('hero_gm', ctypes.c_uint8), ('gens_world', ctypes.c_uint8),
                ('gt_level_format', ctypes.c_char_p), ('project', PROJECT), ('state2', STATE2),
                ('damage_type', DAMAGE), ('guild', GUILD), ('party_hp', PARTY)]


class Op(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int32), ('kind', ctypes.c_int32), ('number', ctypes.c_double), ('y', ctypes.c_double),
                ('text', ctypes.c_char * TEXT)]


class Info(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int32), ('type', ctypes.c_int32), ('name', ctypes.c_char * TEXT),
                ('guild', ctypes.c_char * TEXT), ('server', ctypes.c_char * TEXT), ('elemental', ctypes.c_int32),
                ('mark', ctypes.c_int32), ('x', ctypes.c_float), ('y', ctypes.c_float), ('hp', ctypes.c_int32),
                ('is_show', ctypes.c_uint8), ('hp_show', ctypes.c_uint8), ('name_show', ctypes.c_uint8),
                ('strife', ctypes.c_uint8), ('gens_frame', ctypes.c_int32), ('att', ctypes.c_int32 * 4),
                ('damage_type', ctypes.c_uint8 * 3)]


OP_NAMES = {1: 'info_visible', 2: 'mc_visible', 3: 'name_show', 4: 'set_hp', 5: 'hp_show', 6: 'hp_visible',
            7: 'elemental', 8: 'gens', 9: 'guild', 10: 'server', 11: 'strife', 12: 'position', 13: 'top',
            14: 'message', 15: 'remove'}


def load_library(path=LIB):
    if not Path(path).exists():
        subprocess.run(['make', '-C', str(Path(path).parent)], check=True, capture_output=True)
    lib = ctypes.CDLL(str(path))
    P = ctypes.POINTER
    lib.mu_hn_window_init.argtypes = [P(Window)]
    lib.mu_hn_head_height.argtypes = [P(Window), P(Character), P(Env)]
    lib.mu_hn_head_height.restype = ctypes.c_int32
    lib.mu_hn_name_text.argtypes = [P(Character), P(Env), ctypes.c_char_p, ctypes.c_size_t]
    for name in ('mu_hn_class_color', 'mu_hn_pk_color'):
        getattr(lib, name).argtypes = [ctypes.c_int32]
        getattr(lib, name).restype = ctypes.c_char_p
    lib.mu_hn_guild_color.argtypes = [P(Character), P(Env)]
    lib.mu_hn_guild_color.restype = ctypes.c_char_p
    lib.mu_hn_guild_text.argtypes = [P(Character), P(Env), ctypes.c_char_p, ctypes.c_size_t]
    lib.mu_hn_gens_frame.argtypes = [P(Character), P(Env)]
    lib.mu_hn_gens_frame.restype = ctypes.c_int32
    lib.mu_hn_strife_gens.argtypes = [P(Character), P(Env)]
    lib.mu_hn_add_info.argtypes = [P(Window), P(Character), P(Env), P(Info)]
    lib.mu_hn_update.argtypes = [P(Window), LOOKUP, P(Env), P(Op), ctypes.c_int32]
    lib.mu_hn_update.restype = ctypes.c_int32
    lib.mu_hn_set_hp.argtypes = [P(Window), ctypes.c_int32, ctypes.c_uint32, ctypes.c_uint32, P(Op)]
    lib.mu_hn_set_hp.restype = ctypes.c_int32
    lib.mu_hn_remove.argtypes = [P(Window), P(Character), P(Op)]
    lib.mu_hn_remove.restype = ctypes.c_int32
    lib.mu_hn_select.argtypes = [P(Window), ctypes.c_int32, P(Op)]
    lib.mu_hn_select.restype = ctypes.c_int32
    lib.mu_hn_set_mc.argtypes = [P(Window), ctypes.c_int32, ctypes.c_int]
    lib.mu_hn_chat_bubble.argtypes = [P(Window), P(P(Character)), ctypes.c_int32, ctypes.c_char_p, ctypes.c_char_p,
                                      ctypes.c_int32, P(Op)]
    lib.mu_hn_chat_bubble.restype = ctypes.c_int32
    lib.mu_hn_info_json.argtypes = [P(Info), ctypes.c_char_p, ctypes.c_size_t]
    lib.mu_hn_info_json.restype = ctypes.c_size_t
    return lib


# --------------------------------------------------------------------------- a synthetic world (shared by both sides)

RIDES = [0xffff] * 6 + [0x1a02, 0x1a03, 0x1a04, 0x1a25, 0x19d7, 0x19e3, 0x19e4, 0x184b, 0x184c, 0x1853, 0x1854,
                        0x185d, 0x185e, 0x28f7, 0x1833, 0x1834, 0x1835, 0x1836, 0x1234, 0x0]
CLASSES = [-1] * 6 + [0x271, 0x272, 0x396, 0x2a9, 0x2b2, 0, 1, 14, 300, 0x1ff]
SERVERS = ['', '', 'Matrix-1', 'GS7', 'x' * 20]
NAMES = ['Nighty', 'Bull Fighter', 'Hound', 'a', 'LongerThan15Chars', 'Elf Lala', 'Budge Dragon', 'Q']


def random_character(rng, key, kind=None, names=NAMES):
    c = {
        'key': key, 'guild': rng.choice([-1, -1, 0, 1, 2, 3]), 'class_byte': rng.randrange(256),
        'guild_relation': rng.choice([0, 0, 1, 2, 4, 8, 9]), 'gens': rng.choice([0, 0, 1, 2]),
        'pk': rng.choice([0, 1, 2, 3, 3, 3, 4, 5, 6, 7]), 'kind': kind if kind is not None else rng.choice([1, 2, 2, 0, 3]),
        'live': rng.choice([1, 1, 1, 0]), 'gens_rank': rng.choice([0, 1, 5, 14, 15, 200]),
        'monster_class': rng.choice(CLASSES), 'level': rng.choice([1, 50, 150, 400, 650, 65535]),
        'height': rng.choice([0, 0, 120, 180, 250, 1000]), 'wing': rng.choice([-1, -1, 3]),
        'ride': rng.choice(RIDES), 'resist': [rng.randrange(0, 3) for _ in range(4)],
        'max_hp': rng.choice([0, 1, 100, 5000, 0xffffffff, 0x80000001]), 'hp': 0, 'mark': rng.randrange(-1, 30),
        'elemental': rng.choice([0, 0, 1, 2, 3, 4, 5]), 'name_kind': rng.choice([0, 0, 1, 2, 3]),
        'position': [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.choice([0.0, rng.uniform(-50, 600)]))],
        'server': rng.choice(SERVERS), 'duel_name': rng.choice(['', 'Nighty', 'Other']), 'name': rng.choice(names),
    }
    c['hp'] = rng.choice([0, c['max_hp'], c['max_hp'] // 2, rng.randrange(0, 0xffffffff), 77])
    return c


def to_ctypes(c):
    out = Character()
    for k, v in c.items():
        if k in ('server', 'duel_name', 'name'):
            setattr(out, k, v.encode('latin1'))
        elif k == 'resist':
            out.resist[:] = v
        elif k == 'position':
            out.position[:] = v
        else:
            setattr(out, k, v)
    return out


def projection(p):
    """The recorded projection both sides use (a fixed function of the position)."""
    x = f32(f32(p[0] * f32(0.03125)) - f32(p[2] * f32(0.0625)) + f32(13.37))
    y = f32(f32(p[1] * f32(-0.02)) + f32(p[2] * f32(0.75)) + f32(480.5))
    return x, y


# --------------------------------------------------------------------------- emulator models

class Strings:
    """MSVC std::string (0x18 bytes: buffer/pointer, size +0x10, capacity +0x14) in emulated memory."""

    def __init__(self, m):
        self.m = m

    def write(self, address, s, define=True):
        b = s.encode('latin1') if isinstance(s, str) else bytes(s)
        if len(b) < 16:
            self.m.write(address, b + b'\0' * (16 - len(b)), define)
            cap = 15
        else:
            buf = self.m.alloc(len(b) + 1, define=True)
            self.m.write(buf, b + b'\0')
            self.m.write(address, struct.pack('<I', buf) + b'\0' * 12, define)
            cap = len(b)
        self.m.write(address + 0x10, struct.pack('<II', len(b), cap), define)

    def read(self, address):
        size, cap = struct.unpack('<II', self.m.read(address + 0x10, 8))
        ptr = struct.unpack('<I', self.m.read(address, 4))[0] if cap >= 16 else address
        return self.m.read(ptr, size).decode('latin1')

    def cstr(self, address, limit=1024):
        out = bytearray()
        while len(out) < limit:
            b = self.m.read(address + len(out), 1)[0]
            if not b:
                break
            out.append(b)
        return out.decode('latin1')


def write_character(m, strings, c, a=None):
    if a is None:
        a = m.alloc(0x3700, define=True)
    m.write(a, b'\0' * 0x3700)
    w = lambda off, fmt, v: m.write(a + off, struct.pack(fmt, v))  # noqa: E731
    w(0x12, '<B', c['class_byte'])
    w(0x19, '<B', c['guild_relation'])
    w(0x1e, '<B', c['gens'])
    w(0x1f, '<B', c['pk'])
    w(0x3c, '<h', c['guild'])
    w(0x3e, '<h', c['key'])
    m.write(a + 0x44, c['server'].encode('latin1') + b'\0')
    w(0x146, '<h', c['monster_class'])
    w(0x14e, '<H', c['level'])
    w(0x150, '<I', c['max_hp'])
    w(0x154, '<I', c['hp'])
    w(0x158, '<H', c['height'])
    w(0x15c, '<i', c['mark'])
    w(0x21a4, '<h', c['wing'])
    w(0x322e, '<H', c['ride'])
    w(0x3254, '<B', c['live'])
    w(0x3268, '<i', c['elemental'])
    for i, r in enumerate(c['resist']):
        w(0x3274 + 2 * i, '<H', r)
    w(0x328f, '<B', c['kind'])
    for i, v in enumerate(c['position']):
        w(0x33ac + 4 * i, '<f', v)
    w(0x362c, '<B', c['gens_rank'])
    w(0x363c, '<i', c['name_kind'])
    strings.write(a + 0x3640, c['duel_name'])
    strings.write(a + 0x3658, c['name'])
    return a


class Host:
    """Host answers shared by the client stubs and the library callbacks."""

    def __init__(self, rng, characters, hero=None):
        self.rng = rng
        self.characters = characters          # key -> dict
        self.hero = hero                      # dict or None
        self.hero_level = rng.choice([1, 100, 400, 1000])
        self.hero_hp = rng.choice([0, 1, 500, 117918])
        self.hero_max_hp = rng.choice([1, 1000, 117918, 0])
        self.duel_key = rng.choice([-1, 0, 1, 2, 3])
        self.duel_hp = rng.randrange(100)
        self.world = rng.choice([0, 0, 0x8b, 51, 7])
        self.name_option = rng.choice([0, 1, 1])
        self.hero_bar_a = rng.choice([0, 0, 1])
        self.hero_bar_b = rng.choice([0, 0, 1])
        self.server_flag = rng.choice([0, 1])
        self.gens_option = rng.choice([0, 0, 1])
        self.hero_gm = rng.choice([0, 0, 0, 1])
        self.gens_world = rng.choice([0, 1])
        self.state2 = {k: rng.choice([0, 0, 0, 1]) for k in characters}
        self.damage = {}
        self.guilds = {i: (rng.choice(['', 'Lions', 'MatrixGuild']), rng.choice(['', 'Union'])) for i in range(4)}
        self.party = {}
        for k, c in characters.items():
            if rng.random() < 0.3:
                self.party[c['name']] = rng.randrange(0, 101)
        self.gt = '%s[%d]'
        self.projected = []

    def damage_type(self, cls, i):
        key = (cls, i)
        if key not in self.damage:
            self.damage[key] = self.rng.choice([0, 0, 1, 7])
        return self.damage[key]


def make_env(host, keep):
    """A ctypes Env over the host; keep holds references the callbacks need."""
    env = Env()

    def project(_, pos, x, y):
        p = (pos[0], pos[1], pos[2])
        host.projected.append(('lib', p))
        x[0], y[0] = projection(p)

    def state2(_, c):
        return host.state2.get(c.contents.key, 0)

    def damage(_, cls, i):
        return host.damage_type(cls, i)

    names = []

    def guild(_, index, name, second):
        g = host.guilds.get(index, ('', ''))
        a, b = ctypes.c_char_p(g[0].encode()), ctypes.c_char_p(g[1].encode())
        names.extend([a, b])
        name[0], second[0] = a.value, b.value

    def party(_, name, hp):
        n = name.decode('latin1')
        if n in host.party:
            hp[0] = host.party[n]
            return 1
        return 0
    cbs = [PROJECT(project), STATE2(state2), DAMAGE(damage), GUILD(guild), PARTY(party)]
    keep.extend(cbs + [names])
    env.project, env.state2, env.damage_type, env.guild, env.party_hp = cbs
    if host.hero is not None:
        hero = to_ctypes(host.hero)
        keep.append(hero)
        env.hero = ctypes.pointer(hero)
    env.hero_level, env.hero_hp, env.hero_max_hp = host.hero_level, host.hero_hp, host.hero_max_hp
    env.duel_key, env.duel_hp, env.world = host.duel_key, host.duel_hp, host.world
    env.name_option, env.hero_bar_a, env.hero_bar_b = host.name_option, host.hero_bar_a, host.hero_bar_b
    env.server_flag, env.gens_option, env.hero_gm, env.gens_world = (host.server_flag, host.gens_option, host.hero_gm,
                                                                      host.gens_world)
    gt = ctypes.c_char_p(host.gt.encode())
    keep.append(gt)
    env.gt_level_format = gt
    return env


class Client:
    """One Unicorn machine with the models of the boundary installed."""

    def __init__(self, text, data):
        self.text = text
        self.m = cm.Machine(text, data)
        self.s = Strings(self.m)
        self.cleanup_cache = {}
        for start in ALLOWED:
            self.m.allow((start, cm.function_extent(text, start)))

    # Callees whose bodies hold several returns (inline exception funclets end with a plain ret):
    # the immediate of the function's own epilogue, read from the decoded body.
    CLEANUP = {0x016bec9f: 0,          # begins with a jump into a protector stub; cdecl (the caller pops)
               0x00aaf829: 8, 0x00a08738: 8, 0x00c85f97: 8, 0x009d6d27: 4, 0x008e83a0: 0, 0x008e62b0: 4}

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

    def reset(self, host):
        m = self.m
        m.reset()
        m.put32(SECURITY_COOKIE, 0xbb40e64e)
        self.host = host
        self.values = {}          # GFx Value address -> python value / ('path', ...)
        self.display = {}         # DisplayInfo address -> dict
        self.wide = {}            # std::wstring address -> text
        self.formats = {}         # formatter object -> [fmt, args]
        self.records = []
        self.char_addr = {}
        self.addr_char = {}
        for k, c in host.characters.items():
            a = write_character(m, self.s, c)
            self.char_addr[k] = a
            self.addr_char[a] = k
        self.hero_addr = 0
        if host.hero is not None:
            hk = host.hero['key']
            self.hero_addr = self.char_addr.get(hk) or write_character(m, self.s, host.hero)
        m.put32(HERO, self.hero_addr)
        attr = m.alloc(0x100, define=True)
        m.put32(attr + 0x68, host.hero_hp)
        m.put32(attr + 0x40, host.hero_max_hp)
        m.put32(HERO_ATTR, attr)
        m.put32(DUEL_KEY, host.duel_key)
        m.put32(DUEL_HP, host.duel_hp)
        m.put32(WORLD, host.world)
        opts = m.alloc(0x40, define=True)
        m.write(opts, b'\0' * 0x40)
        m.write(opts + 0x23, bytes([host.name_option]))
        m.put32(OPTIONS, opts)          # 0x0095f160 reads the pointer, 0x0095f602 adds 0x20, the byte is +3
        for i in range(4):
            name, second = host.guilds[i]
            rec = GUILDS + 0x58 * i
            m.write(rec, second.encode() + b'\0' * (9 - len(second)))
            m.write(rec + 9, name.encode() + b'\0' * (0x4f - len(name)))
        self._install()

    # ---- models -----------------------------------------------------------------------------------------------
    def _install(self):
        m, s, host = self.m, self.s, self.host
        args = m.args

        # height helpers
        manager = m.alloc(16, define=True)
        self.stub(0x009c104e, lambda _: manager)

        def state2(_):
            c, kind, flag = args(3)
            assert self.ecx() == manager and kind == 2 and flag == 1, (kind, flag)
            return host.state2.get(self.addr_char.get(c, -9999), 0)
        self.stub(0x0106b9f7, state2)

        # GlobalText and the formatter
        gt = m.alloc(64, define=True)
        m.write(gt, host.gt.encode() + b'\0')

        def global_text(_):
            assert args(1)[0] == 0x11f3 and self.ecx() == 0x06fbab48
            return gt
        self.stub(0x011753c3, global_text)

        def fmt_from_cstr(_):          # 0x009d5d27 format(const char *)
            self.formats[self.ecx()] = [s.cstr(args(1)[0]), []]
            return self.ecx()
        self.stub(0x009d5d27, fmt_from_cstr)

        def fmt_from_string(_):        # 0x009d59cc format(const std::string &)
            self.formats[self.ecx()] = [s.read(args(1)[0]), []]
            return self.ecx()
        self.stub(0x009d59cc, fmt_from_string)

        def feed(kind):
            def handler(_):
                this = self.ecx()
                if kind in ('str1', 'int1', 'short1'):
                    value = args(1)[0]
                    target = this
                else:
                    tmp, value = args(2)
                    target = this
                v = {'str1': lambda: s.read(value), 'int1': lambda: s32(m.u32(value)),
                     'short1': lambda: struct.unpack('<H', m.read(value, 2))[0],   # movzx: operator<<(unsigned short) 0x00b3cc1f
                     'cstrp': lambda: s.cstr(m.u32(value)), 'string': lambda: s.read(value),
                     'chars': lambda: s.cstr(value)}[kind]()
                self.formats[target][1].append(v)
                return this
            return handler
        self.stub(0x0096c702, feed('str1'))
        self.stub(0x009d419a, feed('int1'))
        self.stub(0x00b3c940, feed('short1'))
        self.stub(0x00aaf829, feed('cstrp'))
        self.stub(0x00a08738, feed('string'))
        self.stub(0x00c85f97, feed('chars'))

        def fmt_text(obj):
            fmt, values = self.formats[obj]
            out, i, k = '', 0, 0
            while i < len(fmt):
                if fmt[i] == '%' and i + 1 < len(fmt) and fmt[i + 1] in 'sd':
                    out += str(values[k])
                    k += 1
                    i += 2
                else:
                    out += fmt[i]
                    i += 1
            assert k == len(values), (fmt, values)
            return out

        def fmt_str(_):                # 0x0097258c / 0x009d6d27 str(out)
            out = args(1)[0]
            s.write(out, fmt_text(self.ecx()))
            return out
        self.stub(0x0097258c, fmt_str)
        self.stub(0x009d6d27, fmt_str)
        for dtor in (0x0096f4ae, 0x009d5f0d):
            self.stub(dtor, lambda _: 0)

        # std::string
        self.stub(0x008e6d00, lambda _: (s.write(self.ecx(), ''), self.ecx())[1])
        self.stub(0x0094997e, lambda _: (s.write(self.ecx(), s.cstr(args(1)[0])), self.ecx())[1])
        self.stub(0x0094af7d, lambda _: (s.write(self.ecx(), s.read(args(1)[0])), self.ecx())[1])
        self.stub(0x008e80e0, lambda _: (s.write(self.ecx(), s.read(args(1)[0])), self.ecx())[1])
        self.stub(0x008e7410, lambda _: (s.write(self.ecx(), s.read(args(1)[0])), self.ecx())[1])
        self.stub(0x008e62b0, lambda _: (s.write(self.ecx(), s.read(args(1)[0])), self.ecx())[1])
        self.stub(0x0094b9f7, lambda _: (s.write(self.ecx(), s.read(self.ecx()) + s.cstr(args(1)[0])), self.ecx())[1])
        for dtor in (0x008e83a0, 0x0094f183):
            self.stub(dtor, lambda _: 0)

        def concat_cstr(_):            # 0x00975e18 (out, const string &, const char *)
            out, a, b = args(3)
            s.write(out, s.read(a) + s.cstr(b))
            return out
        self.stub(0x00975e18, concat_cstr)
        self.stub(0x00944959, concat_cstr)   # (out, string &&, const char *)
        self.stub(0x0097035e, lambda _: 1 if s.read(self.ecx()) == s.cstr(args(1)[0]) else 0)   # string == char *

        # std::wstring (text kept in Python)
        self.stub(0x00ae34d3, lambda _: (self.wide.__setitem__(self.ecx(), ''), self.ecx())[1])

        def wide_literal(_):
            p = args(1)[0]
            assert m.read(p, 2) == b'\0\0', 'only the empty wide literal is expected'
            self.wide[self.ecx()] = ''
            return self.ecx()
        self.stub(0x00ab038f, wide_literal)

        def utf8_to_wide(_):           # 0x0120b0ec (out, const std::string &)
            out, src = args(2)
            self.wide[out] = s.read(src)
            return out
        self.stub(0x0120b0ec, utf8_to_wide)
        self.stub(0x00ae4076, lambda _: (self.wide.__setitem__(self.ecx(), self.wide[args(1)[0]]), self.ecx())[1])
        self.stub(0x00ab10db, lambda _: self.ecx())          # c_str: the object stands for its buffer
        self.stub(0x00ab01fc, lambda _: 0)

        # GFx values and display info
        def value_ctor(_):
            self.values[self.ecx()] = None
            return self.ecx()
        self.stub(0x00aad26b, value_ctor)
        self.stub(0x00aad299, lambda _: 0)
        self.stub(0x00c8f5f4, lambda _: self.values.__setitem__(args(1)[0], {}))
        self.stub(0x00c8f9cf, lambda _: self.values.__setitem__(args(1)[0], []))

        def set_member(kind):
            def handler(_):
                obj, name, value = args(3)
                v = {'int': lambda: s32(value), 'str': lambda: s.cstr(value), 'bool': lambda: bool(value & 0xff),
                     'float': lambda: struct.unpack('<f', struct.pack('<I', value))[0],
                     'value': lambda: self.values[value]}[kind]()
                self.values[obj][s.cstr(name)] = v
            return handler
        self.stub(0x00ae957f, set_member('int'))
        self.stub(0x00ae94c9, set_member('str'))
        self.stub(0x00aecd73, set_member('bool'))
        self.stub(0x00aeb026, set_member('float'))
        self.stub(0x00ae497d, set_member('value'))

        def set_element(_):            # 0x00c67e19 (array, index, value)
            array, index, value = args(3)
            arr = self.values[array]
            while len(arr) <= index:
                arr.append(None)
            arr[index] = self.values[value]
        self.stub(0x00c67e19, set_element)

        def window_invoke(_):          # 0x00c8fac2 (method, value)
            method, value = args(2)
            self.records.append(('invoke', s.cstr(method), json.loads(json.dumps(self.values.get(value)))))
        self.stub(0x00c8fac2, window_invoke)

        # display objects: Value -> ('mc', key) / ('member', parent, name)
        def get_member(_):             # 0x00ae949c (name, out)
            name, out = args(2)
            self.values[out] = ('member', self.values[self.ecx()], s.cstr(name))
        self.stub(0x00ae949c, get_member)
        self.stub(0x00aad348, lambda _: 1 if self.defined(self.values.get(self.ecx())) else 0)
        self.stub(0x00aad23a, lambda _: (self.display.__setitem__(self.ecx(), {}), self.ecx())[1])
        self.stub(0x00aad43a, lambda _: self.display[self.ecx()].__setitem__('visible', args(1)[0] & 0xff))

        def set_position(_):
            x, y = struct.unpack('<dd', struct.pack('<IIII', *args(4)))
            self.display[self.ecx()]['x'], self.display[self.ecx()]['y'] = x, y
        self.stub(0x00c87caa, set_position)

        def set_display(_):            # Value::SetDisplayInfo(di)
            target = self.values[self.ecx()]
            di = {k: v for k, v in self.display[args(1)[0]].items() if not k.startswith('_')}
            self.records.append(('display', self.path(target), di))
            if target[0] == 'mc' and 'visible' in di:
                self.mc_visible[target[1]] = di['visible']
        self.stub(0x00aad3e0, set_display)

        def get_display(_):            # 0x00c87a9e mc.GetDisplayInfo(out)
            target = self.values[self.ecx()]
            self.display[args(1)[0]] = {'_visible': self.mc_visible.get(target[1], 1)}
        self.stub(0x00c87a9e, get_display)
        self.stub(0x00c87bd9, lambda _: self.display[self.ecx()]['_visible'])
        self.stub(0x00ab0ae3, lambda _: (self.values.__setitem__(self.ecx(), bool(args(1)[0] & 0xff)), self.ecx())[1])

        def value_double(_):
            self.values[self.ecx()] = struct.unpack('<d', struct.pack('<II', *args(2)))[0]
            return self.ecx()
        self.stub(0x00ab0bfe, value_double)
        self.stub(0x00ab0cd0, lambda _: (self.values.__setitem__(self.ecx(), self.wide[args(1)[0]]), self.ecx())[1])

        def invoke(_):                 # 0x00c87c06 Value::Invoke(method, result, args, count)
            method, result, argv, count = args(4)
            assert result == 0
            values = [self.values[argv + 0x10 * i] for i in range(count)]
            self.records.append(('call', self.path(self.values[self.ecx()]), s.cstr(method),
                                 json.loads(json.dumps(values))))
        self.stub(0x00c87c06, invoke)

        def invoke0(_):                # 0x00c87be9 Value::Invoke(method, result) (setTopMovie)
            method, result = args(2)
            self.records.append(('call', self.path(self.values[self.ecx()]), s.cstr(method), []))
        self.stub(0x00c87be9, invoke0)

        # characters and singletons
        chars_mgr = m.alloc(16, define=True)
        self.stub(0x0137c724, lambda _: s32(args(1)[0]) & 0xffffffff)   # key -> index (identity)
        self.stub(0x0095f6db, lambda _: chars_mgr)

        def get_character(_):          # 0x009a13f4 (index)
            assert self.ecx() == chars_mgr
            index = s32(args(1)[0])
            if index in self.char_list_index:
                return self.char_list_index[index]
            return 0 if index in self.missing else self.char_addr.get(index, 0)
        self.stub(0x009a13f4, get_character)
        self.missing = set()
        self.char_list_index = {}
        self.stub(0x00a00367, lambda _: host.hero_level)
        flag_a, flag_b, flag_s, flag_g = (m.alloc(0x100, define=True) for _ in range(4))
        m.write(flag_a + 0x8c, bytes([host.hero_bar_a]))
        m.write(flag_b + 4, bytes([host.hero_bar_b]))
        self.stub(0x009a595b, lambda _: flag_a)
        self.stub(0x00c89acf, lambda _: m.read(self.ecx() + 0x8c, 1)[0])
        self.stub(0x0095f7df, lambda _: flag_b)
        self.stub(0x00b4d664, lambda _: m.read(self.ecx() + 4, 1)[0])
        self.stub(0x0095f75d, lambda _: flag_s)
        self.stub(0x0095fb99, lambda _: host.server_flag)
        self.stub(0x0095c652, lambda _: (lambda a: (a == [0x5c, 5] or self.fail_case(f'0x0095c652 {a}'), flag_g)[1])(args(2)))
        self.stub(0x00d7b3ce, lambda _: host.gens_option)
        self.stub(0x016a83da, lambda _: host.hero_gm)
        self.stub(0x016bec9f, lambda _: host.gens_world if s32(args(1)[0]) == host.world else self.fail_case('world'))
        self.stub(0x0114282c, lambda _: host.damage_type(s32(args(2)[0]), s32(args(2)[1])))

        def project(_):                # 0x0184a3ce (position, &x, &y)
            p, px, py = args(3)
            pos = struct.unpack('<fff', m.read(p, 12))
            host.projected.append(('client', pos))
            x, y = projection(pos)
            m.write(px, struct.pack('<f', x))
            m.write(py, struct.pack('<f', y))
        self.stub(0x0184a3ce, project)

        # party window lookup (0x0095c595 window handle, 0x0095f16e get, 0x00c7955f find by name)
        party_window = m.alloc(16, define=True)
        self.stub(0x0095c595, lambda _: (m.put32(args(1)[0], party_window), args(1)[0])[1])
        self.stub(0x0095f16e, lambda _: m.u32(self.ecx()))
        self.stub(0x0095ebbb, lambda _: 0)

        def party_find(_):             # (out, name)
            out, name = args(2)
            assert self.ecx() == party_window
            n = s.read(name)              # the character's name std::string (+0x3658)
            if n in host.party:
                member = m.alloc(0x20, define=True)
                m.put32(member + 0x18, host.party[n])
                m.put32(out, member)
            else:
                m.put32(out, 0)
            return out
        self.stub(0x00c7955f, party_find)
        self.stub(0x0095f077, lambda _: 1 if m.u32(self.ecx()) else 0)
        self.stub(0x0095f128, lambda _: m.u32(self.ecx()))
        self.stub(0x0095eb67, lambda _: 0)

        # the handler's maps (models over Python lists; nodes live in emulated memory)
        self.stub(0x00c86d0b, self._make_pair)
        self.stub(0x00c86c93, self._insert)
        self.stub(0x00c876cf, lambda _: 0)
        self.stub(0x00afbd93, lambda _: 0)
        self.stub(0x00c899e7, self._erase)
        for address, handler in ((0x00c89a79, self._info_find), (0x00c89955, self._info_end),
                                 (0x00c877cc, self._iter_ne), (0x00c87722, self._iter_eq),
                                 (0x00c87871, self._info_deref), (0x00c897fc, self._mc_begin),
                                 (0x00c8997f, self._mc_end), (0x00c877fb, self._iter_ne),
                                 (0x00c8791b, self._iter_next), (0x00c87889, self._mc_deref),
                                 (0x00c89aa4, self._mc_find), (0x00c8774b, self._iter_eq)):
            self.stub(address, handler)

    def fail_case(self, message):
        raise AssertionError(message)

    def defined(self, v):
        return v is not None and not (isinstance(v, tuple) and v[0] == 'member' and v[2] in self.undefined_members)

    def path(self, v):
        if v[0] == 'mc':
            return f'mc{v[1]}'
        return self.path(v[1]) + '.' + v[2]

    # ---- map models ---------------------------------------------------------------------------------------------
    # info map (handler +0x4c): self.info[key] = node address (pair<int, entry> at node: key +0, entry +4)
    # clip map (handler +0x54): self.mc_keys sorted; pair at self.mc_pair[key] (key +0, Value +8)
    # iterators are 4-byte cells holding a node address (0 = end) or ('mc', index)

    def setup_maps(self, window, entries, mc_keys):
        m = self.m
        self.window = window
        self.info = {}
        for e in entries:
            node = m.alloc(0x100, define=True)
            m.write(node, b'\0' * 0x100)
            self.write_entry(node + 4, e)
            m.put32(node, e['key'] & 0xffffffff)
            self.info[e['key']] = node
        self.mc_keys = sorted(mc_keys)
        self.mc_pair = {}
        self.mc_visible = {}
        for k in self.mc_keys:
            pair = m.alloc(0x20, define=True)
            m.write(pair, b'\0' * 0x20)
            m.put32(pair, k & 0xffffffff)
            self.values[pair + 8] = ('mc', k)
            self.mc_pair[k] = pair
        self.undefined_members = set()
        self.inserted = []

    def write_entry(self, a, e):
        m, s = self.m, self.s
        m.write(a, b'\0' * 0xa4)
        m.write(a, struct.pack('<ii', e['key'], e['type']))
        s.write(a + 8, '')
        s.write(a + 0x20, e['name'])
        m.write(a + 0x38, struct.pack('<ffi', e['x'], e['y'], e['hp']))
        m.write(a + 0x44, bytes([e['show']]))
        m.write(a + 0x48, struct.pack('<i', e['elemental']))
        m.write(a + 0x4c, struct.pack('<4i', *e['att']))
        m.write(a + 0x5c, bytes(e['damage_type']) + bytes([e['hp_show'], e['name_show'], e['strife']]))
        m.write(a + 0x64, struct.pack('<iii', e['gens'], 0, 0))
        s.write(a + 0x70, e['guild'])
        s.write(a + 0x88, e['server'])
        m.write(a + 0xa0, bytes([e['flag_a0']]))

    def read_entry(self, a):
        m, s = self.m, self.s
        key, typ = struct.unpack('<ii', m.read(a, 8))
        x, y, hp = struct.unpack('<ffi', m.read(a + 0x38, 12))
        b = m.read(a + 0x5c, 6)
        return {'key': key, 'type': typ, 'name': s.read(a + 0x20), 'x': x, 'y': y, 'hp': hp,
                'show': m.read(a + 0x44, 1)[0], 'elemental': s32(m.u32(a + 0x48)),
                'att': list(struct.unpack('<4i', m.read(a + 0x4c, 16))), 'damage_type': list(b[:3]),
                'hp_show': b[3], 'name_show': b[4], 'strife': b[5], 'gens': s32(m.u32(a + 0x64)),
                'guild': s.read(a + 0x70), 'server': s.read(a + 0x88), 'flag_a0': m.read(a + 0xa0, 1)[0]}

    def _make_pair(self, _):           # 0x00c86d0b (out, &key, &entry) -> out
        out, key, entry = self.m.args(3)
        self.pending = (out, s32(self.m.u32(key)), entry)
        return out

    def _insert(self, _):              # 0x00c86c93 this = map +0x4c (result, pair)
        result, pair = self.m.args(2)
        out, key, entry = self.pending
        assert self.ecx() == self.window + 0x4c and pair == out
        self.inserted.append(self.read_entry(entry))
        return result

    def _erase(self, _):               # 0x00c899e7 this = map +0x4c (result, iterator value)
        result, node = self.m.args(2)
        assert self.ecx() == self.window + 0x4c
        key = s32(self.m.u32(node))
        del self.info[key]
        self.records.append(('erase', key))
        return result

    def _info_find(self, _):           # (out, &key)
        out, key = self.m.args(2)
        assert self.ecx() == self.window + 0x4c
        self.m.put32(out, self.info.get(s32(self.m.u32(key)), 0))
        return out

    def _info_end(self, _):
        out = self.m.args(1)[0]
        self.m.put32(out, 0)
        return out

    def _iter_ne(self, _):
        return 1 if self.m.u32(self.ecx()) != self.m.u32(self.m.args(1)[0]) else 0

    def _iter_eq(self, _):
        return 1 if self.m.u32(self.ecx()) == self.m.u32(self.m.args(1)[0]) else 0

    def _info_deref(self, _):
        return self.m.u32(self.ecx())

    def _mc_begin(self, _):
        out = self.m.args(1)[0]
        assert self.ecx() == self.window + 0x54
        self.m.put32(out, self.mc_pair[self.mc_keys[0]] if self.mc_keys else 0)
        return out

    def _mc_end(self, _):
        out = self.m.args(1)[0]
        self.m.put32(out, 0)
        return out

    def _iter_next(self, _):           # post-increment (out, 0)
        out, _zero = self.m.args(2)
        cur = self.m.u32(self.ecx())
        self.m.put32(out, cur)
        key = s32(self.m.u32(cur))
        i = self.mc_keys.index(key)
        self.m.put32(self.ecx(), self.mc_pair[self.mc_keys[i + 1]] if i + 1 < len(self.mc_keys) else 0)
        return out

    def _mc_deref(self, _):
        return self.m.u32(self.ecx())

    def _mc_find(self, _):             # (out, &key)
        out, key = self.m.args(2)
        assert self.ecx() == self.window + 0x54
        self.m.put32(out, self.mc_pair.get(s32(self.m.u32(key)), 0))
        return out

    def window_object(self, host_window):
        m = self.m
        w = m.alloc(0x100, define=True)
        m.write(w, b'\0' * 0x100)
        hw = host_window
        m.write(w + 0x1c, struct.pack('<10i', hw.item_height, hw.item_offset, hw.height_player, hw.height_wing,
                                      hw.height_ride_a, hw.height_ride_b, hw.height_ride_c, hw.height_ride,
                                      hw.height_state, hw.height_ride_d))
        m.write(w + 0x44, bytes([hw.monster_view]))
        m.put32(w + 0x48, hw.selected)
        m.write(w + 0x5c, bytes([hw.item_view]))
        return w

    def call(self, address, args=(), ecx=None):
        return self.m.call(address, args, ecx)


# --------------------------------------------------------------------------- sections: helpers

def random_window(rng, lib, defaults=False):
    w = Window()
    lib.mu_hn_window_init(ctypes.byref(w))
    if not defaults:
        for f in ('height_player', 'height_wing', 'height_ride_a', 'height_ride_b', 'height_ride_c', 'height_ride',
                  'height_state', 'height_ride_d'):
            setattr(w, f, rng.randrange(-50, 1000))
        w.monster_view = rng.choice([0, 1, 1])
    return w


def world_case(rng, n=6, kinds=None):
    chars = {}
    for i in range(n):
        key = rng.randrange(0, 2000) if rng.random() < 0.3 else i
        while key in chars:
            key += 1
        chars[key] = random_character(rng, key, kinds[i] if kinds else None)
    hero_key = rng.choice(list(chars)) if rng.random() < 0.8 else None
    hero = chars[hero_key] if hero_key is not None else random_character(rng, 9999, 1)
    if rng.random() < 0.5 and hero_key is not None:
        for c in chars.values():
            if c is not hero and rng.random() < 0.5:
                c['guild'] = hero['guild']
                c['gens'] = hero['gens']
    host = Host(rng, chars, hero)
    return host


PLANT = None      # a planted mistake on the library's side (negative controls)
PLANTS = {
    'pk_shift': lambda c, env: setattr(c, 'pk', (c.pk + 1) & 0xff),
    'name_kind': lambda c, env: setattr(c, 'name_kind', 0 if c.name_kind == 1 else c.name_kind),
    'height_plus': lambda c, env: setattr(c, 'height', (c.height + 1) & 0xffff),
    'base_class': lambda c, env: setattr(c, 'class_byte', c.class_byte ^ 1),
    'ride_swap': lambda c, env: setattr(c, 'ride', 0x1a03 if c.ride == 0x1a02 else (0x1a02 if c.ride == 0x1a03 else c.ride)),
    'resist_order': lambda c, env: c.resist.__setitem__(slice(0, 4), list(c.resist)[::-1]),
    'option_flip': lambda c, env: setattr(env, 'name_option', env.name_option ^ 1),
    'hero_hp': lambda c, env: setattr(env, 'hero_hp', env.hero_hp + 1),
    'world_8b': lambda c, env: setattr(env, 'world', 0 if env.world == 0x8b else 0x8b),
    'gens_option': lambda c, env: setattr(env, 'gens_option', env.gens_option ^ 1),
    'server_flag': lambda c, env: setattr(env, 'server_flag', env.server_flag ^ 1),
    'level_600': lambda c, env: setattr(c, 'level', (c.level + 600) & 0xffff if c.name_kind == 2 else c.level),
}

ENV_PLANTS = {'option_flip', 'hero_hp', 'world_8b', 'gens_option', 'server_flag'}


def lib_side(host, keep):
    env = make_env(host, keep)
    cts = {k: to_ctypes(c) for k, c in host.characters.items()}
    keep.append(cts)
    if host.hero is not None and host.hero['key'] in cts:
        env.hero = ctypes.pointer(cts[host.hero['key']])   # the same record: pointer identity as in the client
    if PLANT in ENV_PLANTS:
        PLANTS[PLANT](None, env)
    elif PLANT:
        for c in cts.values():
            PLANTS[PLANT](c, env)
    return env, cts


def validate_helpers(client, lib, rng, cases):
    counts = {'height': 0, 'name': 0, 'class_color': 0, 'pk_color': 0, 'guild_color': 0, 'gens': 0, 'strife': 0,
              'guild': 0}
    for case in range(cases):
        host = world_case(rng)
        client.reset(host)
        keep = []
        env, cts = lib_side(host, keep)
        w = random_window(rng, lib)
        wa = client.window_object(w)
        out = client.m.alloc(0x18, define=True)
        for k, c in host.characters.items():
            a = client.char_addr[k]
            got = s32(client.call(HEIGHT, (a,), wa))
            want = lib.mu_hn_head_height(ctypes.byref(w), ctypes.byref(cts[k]), ctypes.byref(env))
            assert got == want, ('height', c, got, want)
            counts['height'] += 1
            client.call(NAME, (out, a), wa)
            got = client.s.read(out)
            buf = ctypes.create_string_buffer(512)
            lib.mu_hn_name_text(ctypes.byref(cts[k]), ctypes.byref(env), buf, 512)
            assert got == buf.value.decode('latin1'), ('name', c, got, buf.value)
            counts['name'] += 1
            got = client.s.cstr(client.call(GUILD_COLOR, (a,), wa))
            want = lib.mu_hn_guild_color(ctypes.byref(cts[k]), ctypes.byref(env)).decode()
            assert got == want, ('guild colour', got, want)
            counts['guild_color'] += 1
            got = s32(client.call(GENS_FRAME, (a,), wa))
            want = lib.mu_hn_gens_frame(ctypes.byref(cts[k]), ctypes.byref(env))
            assert got == want, ('gens frame', c, got, want)
            counts['gens'] += 1
            got = client.call(STRIFE, (a,), wa) & 0xff
            want = lib.mu_hn_strife_gens(ctypes.byref(cts[k]), ctypes.byref(env))
            assert got == want, ('strife', c, got, want)
            counts['strife'] += 1
            client.call(GUILD_TEXT, (out, a), wa)
            got = client.s.read(out)
            lib.mu_hn_guild_text(ctypes.byref(cts[k]), ctypes.byref(env), buf, 512)
            assert got == buf.value.decode('latin1'), ('guild text', c, got, buf.value)
            counts['guild'] += 1
        if case == 0:
            for i in list(range(-3, 30)) + [0x7fffffff, -0x80000000]:
                got = client.s.cstr(client.call(CLASS_COLOR, (i & 0xffffffff,), wa))
                assert got == lib.mu_hn_class_color(i).decode(), ('class colour', i)
                got = client.s.cstr(client.call(PK_COLOR, (i & 0xffffffff,), wa))
                assert got == lib.mu_hn_pk_color(i).decode(), ('pk colour', i)
                counts['class_color'] += 1
                counts['pk_color'] += 1
    return counts



# --------------------------------------------------------------------------- sections: the routines

SECTIONS = {}
ENTRY_FIELDS = ('key', 'type', 'name', 'x', 'y', 'hp', 'show', 'elemental', 'att', 'damage_type', 'hp_show',
                'name_show', 'strife', 'gens', 'guild', 'server', 'flag_a0')


def random_entry(rng, key, typ=None):
    return {'key': key, 'type': typ if typ is not None else rng.choice([1, 2, 2, 0]),
            'name': rng.choice(['', 'old', 'x' * 30]),
            'x': f32(rng.choice([0.0, 100.0, rng.uniform(-100, 1500)])),
            'y': f32(rng.choice([0.0, 100.0, rng.uniform(-100, 1500)])), 'hp': rng.choice([0, 50, 100, -5]),
            'show': rng.choice([0, 1]), 'elemental': rng.choice([0, 1, 2]), 'att': [rng.randrange(3) for _ in range(4)],
            'damage_type': [rng.randrange(2) for _ in range(3)], 'hp_show': rng.choice([0, 1]),
            'name_show': rng.choice([0, 1]), 'strife': rng.choice([0, 1]), 'gens': rng.choice([0, 29, 3]),
            'guild': rng.choice(['', 'Lions', 'Lions - Union']), 'server': rng.choice(['', 'GS7', 'Matrix-1']),
            'flag_a0': rng.choice([0, 0, 1])}


def entry_to_ctypes(e, out):
    for k in ENTRY_FIELDS:
        v = e[k]
        if k in ('name', 'guild', 'server'):
            setattr(out, k, v.encode('latin1'))
        elif k in ('att', 'damage_type'):
            getattr(out, k)[:] = v
        else:
            setattr(out, k, v)


def entry_from_ctypes(e):
    d = {}
    for k in ENTRY_FIELDS:
        v = getattr(e, k)
        if isinstance(v, bytes):
            v = v.decode('latin1')
        elif k in ('att', 'damage_type'):
            v = list(v)
        d[k] = v
    return d


def lib_entries(w):
    return {w.entries[i].key: entry_from_ctypes(w.entries[i]) for i in range(w.count)}


def set_lib_entries(w, entries, mc_keys, mc_visible=None):
    w.count = 0
    for e in sorted(entries, key=lambda e: e['key']):
        entry_to_ctypes(e, w.entries[w.count])
        w.entries[w.count].has_mc = 1 if e['key'] in mc_keys else 0
        w.entries[w.count].mc_visible = (mc_visible or {}).get(e['key'], 1)
        w.count += 1


def same_float(a, b):
    return (a != a and b != b) or f32(a) == f32(b)


def compare_entry(got, want, what):
    for k in ENTRY_FIELDS:
        a, b = got[k], want[k]
        if k in ('x', 'y'):
            assert same_float(a, b), (what, k, a, b, got, want)
        else:
            assert a == b, (what, k, a, b, got, want)


def validate_addinfo(client, lib, rng, cases):
    added = skipped = 0
    for _ in range(cases):
        host = world_case(rng)
        client.reset(host)
        keep = []
        env, cts = lib_side(host, keep)
        w = random_window(rng, lib)
        wa = client.window_object(w)
        keys = list(host.characters)
        existing = [random_entry(rng, k) for k in keys if rng.random() < 0.2]
        client.setup_maps(wa, existing, [])
        set_lib_entries(w, existing, set())
        for k in keys:
            client.records = []
            client.inserted = []
            host.projected = []
            client.call(ADD_INFO, (client.char_addr[k],), wa)
            info = Info()
            r = lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(cts[k]), ctypes.byref(env), ctypes.byref(info))
            invokes = [x for x in client.records if x[0] == 'invoke']
            assert (len(invokes) == 1) == bool(r), ('addInfo taken', host.characters[k], invokes, r)
            assert len(client.inserted) == r, ('inserted', client.inserted, r)
            client_proj = [p for side, p in host.projected if side == 'client']
            lib_proj = [p for side, p in host.projected if side == 'lib']
            assert client_proj == lib_proj, ('projection input', client_proj, lib_proj)
            if not r:
                skipped += 1
                continue
            added += 1
            buf = ctypes.create_string_buffer(8192)
            lib.mu_hn_info_json(ctypes.byref(info), buf, 8192)
            want = json.loads(buf.value.decode('latin1'))
            got = invokes[0][2]
            assert invokes[0][1] == 'addInfo'
            assert list(got) == list(want), ('member order', list(got), list(want))
            for name in want:
                if name in ('x', 'y'):
                    assert same_float(got[name], want[name]), (name, got, want)
                else:
                    assert got[name] == want[name], (name, got[name], want[name], host.characters[k])
            compare_entry(client.inserted[0], lib_entries(w)[k], 'inserted entry')
            client.info[k] = 0     # present for later characters with the same key (none: keys are unique)
    return {'added': added, 'skipped': skipped}


SECTIONS['addinfo'] = validate_addinfo



def client_ops(records):
    """The client's recorded GFx operations as (key, kind, value) in order."""
    ops = []
    for r in records:
        if r[0] == 'display':
            path, di = r[1], r[2]
            key = int(path.split('.')[0][2:])
            if path.endswith('._info._hp'):
                ops.append((key, 'hp_visible', di['visible']))
            elif path.endswith('._info'):
                ops.append((key, 'info_visible', di['visible']))
            elif 'x' in di:
                assert di.get('visible') == 1, di
                ops.append((key, 'position', (f32(di['x']), f32(di['y']))))
            else:
                assert di == {'visible': 1}, di
                ops.append((key, 'mc_visible', 1))
        elif r[0] == 'call':
            path, method, args = r[1], r[2], r[3]
            key = int(path.split('.')[0][2:])
            kind = {'setPlayerNameShow': 'name_show', 'setHp': 'set_hp', 'setHpShow': 'hp_show',
                    'setElemental': 'elemental', 'setGensFrame': 'gens', 'setGuildName': 'guild',
                    'setServerName': 'server', 'setStrifeGens': 'strife', 'setTopMovie': 'top',
                    'setMessage': 'message'}[method]
            value = args[0] if args else 0
            if isinstance(value, bool):
                value = int(value)
            if kind == 'message':
                value = (value['msg'], value['time'])
            ops.append((key, kind, value))
        elif r[0] == 'invoke' and r[1] == 'removeInfo':
            ops.append((r[2]['key'], 'remove', r[2]['type']))
    return ops


def lib_ops(ops, n):
    out = []
    for i in range(n):
        o = ops[i]
        kind = OP_NAMES[o.kind]
        if kind == 'position':
            value = (f32(o.number), f32(o.y))
        elif kind in ('guild', 'server'):
            value = o.text.decode('latin1')
        elif kind == 'message':
            value = (o.text.decode('latin1'), int(o.number))
        else:
            value = o.number
            if value == int(value):
                value = int(value)
        out.append((o.key, kind, value))
    return out


def same_ops(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x[0] != y[0] or x[1] != y[1]:
            return False
        if x[1] == 'position':
            if not all(same_float(p, q) for p, q in zip(x[2], y[2])):
                return False
        elif x[2] != y[2] and not (isinstance(x[2], float) and isinstance(y[2], (int, float)) and same_float(x[2], y[2])):
            return False
    return True


def mutate(rng, host):
    for c in host.characters.values():
        if rng.random() < 0.5:
            c['position'] = [f32(c['position'][0] + rng.uniform(-30, 30)), f32(c['position'][1] + rng.uniform(-30, 30)),
                             c['position'][2]]
        if rng.random() < 0.15:
            c['elemental'] = rng.choice([0, 1, 2, 3])
        if rng.random() < 0.1:
            c['guild'] = rng.choice([-1, 0, 1, 2, 3])
        if rng.random() < 0.1:
            c['server'] = rng.choice(SERVERS)
        if rng.random() < 0.1:
            c['ride'] = rng.choice(RIDES)
        if rng.random() < 0.1:
            c['gens'] = rng.choice([0, 1, 2])
    for name in list(host.party):
        if rng.random() < 0.3:
            host.party[name] = rng.randrange(101)
    if rng.random() < 0.2:
        host.name_option ^= 1
    if rng.random() < 0.2:
        host.hero_hp = rng.randrange(0, 120000)


def validate_update(client, lib, rng, cases, frames=4):
    total_ops = Counter()
    for _ in range(cases):
        host = world_case(rng, n=rng.randrange(1, 8))
        client.reset(host)
        w = random_window(rng, lib)
        w.item_view = 0          # the item loop (NATIVE-ITEMS-001) is not part of this comparison
        w.selected = rng.choice([-1] + list(host.characters))
        wa = client.window_object(w)
        keys = list(host.characters)
        entries = []
        for k in keys:
            if rng.random() < 0.85:
                e = random_entry(rng, k, host.characters[k]['kind'] if rng.random() < 0.9 else None)
                entries.append(e)
        mc_keys = {e['key'] for e in entries if rng.random() < 0.9} | ({rng.randrange(3000, 3100)} if rng.random() < 0.2 else set())
        mc_visible = {k: rng.choice([0, 1, 1]) for k in mc_keys}
        client.setup_maps(wa, entries, mc_keys)
        client.mc_visible = dict(mc_visible)
        client.missing = {k for k in keys if rng.random() < 0.1}
        set_lib_entries(w, entries, mc_keys, mc_visible)
        for frame in range(frames):
            if frame:
                mutate(rng, host)
                for k, c in host.characters.items():
                    write_character(client.m, client.s, c, client.char_addr[k])
                client.m.put32(HERO_ATTR + 0, client.m.u32(HERO_ATTR))
                attr = client.m.u32(HERO_ATTR)
                client.m.put32(attr + 0x68, host.hero_hp)
                client.m.write(client.m.u32(OPTIONS) + 0x23, bytes([host.name_option]))
            keep = []
            env, cts = lib_side(host, keep)
            missing = set(client.missing)

            def lookup(_, key, cts=cts, missing=missing):
                if key in missing or key not in cts:
                    return None
                return ctypes.addressof(cts[key])
            cb = LOOKUP(lookup)
            client.records = []
            host.projected = []
            client.call(UPDATE, (), wa)
            ops = (Op * 4096)()
            n = lib.mu_hn_update(ctypes.byref(w), cb, ctypes.byref(env), ops, 4096)
            got, want = client_ops(client.records), lib_ops(ops, n)
            assert same_ops(got, want), ('operations', frame, got, want)
            client_proj = [p for side, p in host.projected if side == 'client']
            lib_proj = [p for side, p in host.projected if side == 'lib']
            assert client_proj == lib_proj, ('projection input', client_proj, lib_proj)
            le = lib_entries(w)
            for k, node in client.info.items():
                compare_entry(client.read_entry(node + 4), le[k], f'entry after frame {frame}')
            for o in got:
                total_ops[o[1]] += 1
    return {'cases': cases, 'frames': cases * frames, 'operations': dict(sorted(total_ops.items()))}


SECTIONS['update'] = validate_update



def small_world(client, lib, rng):
    host = world_case(rng, n=rng.randrange(1, 7))
    client.reset(host)
    w = random_window(rng, lib)
    wa = client.window_object(w)
    keys = list(host.characters)
    entries = [random_entry(rng, k, host.characters[k]['kind']) for k in keys if rng.random() < 0.8]
    mc_keys = {e['key'] for e in entries if rng.random() < 0.85}
    client.setup_maps(wa, entries, mc_keys)
    set_lib_entries(w, entries, mc_keys)
    keep = []
    env, cts = lib_side(host, keep)
    return host, w, wa, env, cts, keep


def validate_small(client, lib, rng, cases):
    counts = Counter()
    for _ in range(cases):
        host, w, wa, env, cts, keep = small_world(client, lib, rng)
        keys = list(host.characters) + [rng.randrange(5000, 5010)]
        for step in range(8):
            what = rng.choice(['sethp', 'remove', 'select', 'select', 'view'])
            client.records = []
            op = (Op * 4)()
            if what == 'sethp':
                key = rng.choice(keys)
                hp = rng.choice([0, 1, 50, 99, 0xffffffff, rng.randrange(1 << 32)])
                mx = rng.choice([0, 1, 100, 0xffffffff, rng.randrange(1 << 32)])
                client.call(SET_HP, (key & 0xffffffff, hp, mx), wa)
                n = lib.mu_hn_set_hp(ctypes.byref(w), key, hp, mx, op)
            elif what == 'remove':
                key = rng.choice(list(host.characters))
                client.call(REMOVE, (client.char_addr[key],), wa)
                n = lib.mu_hn_remove(ctypes.byref(w), ctypes.byref(cts[key]), op)
                if n:
                    client.mc_keys = [k for k in client.mc_keys if k != key]   # the movie's delMC event
                    client.mc_pair.pop(key, None)
            elif what == 'select':
                key = rng.choice(keys + [-1, -1])
                client.call(SELECT, (key & 0xffffffff,), wa)
                n = lib.mu_hn_select(ctypes.byref(w), key, op)
                assert s32(client.m.u32(wa + 0x48)) == w.selected, ('selected', key)
            else:
                v = rng.choice([0, 1])
                client.m.write(wa + 0x44, bytes([v]))
                w.monster_view = v
                counts['view'] += 1
                continue
            got, want = client_ops(client.records), lib_ops(op, n)
            assert same_ops(got, want), (what, got, want)
            le = lib_entries(w)
            assert sorted(client.info) == sorted(le), ('entries', sorted(client.info), sorted(le))
            for k, node in client.info.items():
                compare_entry(client.read_entry(node + 4), le[k], what)
            counts[what] += 1
            counts[what + '_ops'] += n
    return dict(sorted(counts.items()))


def validate_bubble(client, lib, rng, cases):
    counts = Counter()
    for _ in range(cases):
        host, w, wa, env, cts, keep = small_world(client, lib, rng)
        order = list(host.characters)
        rng.shuffle(order)
        # the character list 0x0095f6db/0x009a13f4: index i -> character, 400 entries (the rest: dead records)
        dead = write_character(client.m, client.s, dict(random_character(rng, 7777), live=0))
        client.char_list_index = {i: (client.char_addr[k] if i < len(order) else dead) for i, k in
                                  enumerate(order + [None] * (400 - len(order)))}
        window_object = client.m.alloc(16, define=True)

        def window(_):                 # 0x009a19ae: the hudPlayerName handler pointer
            out = client.m.args(1)[0]
            client.m.put32(out, wa)
            client.m.put32(out + 4, 0)
            return out
        client.stub(0x009a19ae, window)
        client.stub(0x009617c6, lambda _: 0)
        arr = (ctypes.POINTER(Character) * len(order))(*[ctypes.pointer(cts[k]) for k in order])
        for _step in range(4):
            name = rng.choice([host.characters[k]['name'] for k in order] + ['Nobody'])
            text = rng.choice(['hello', 'Buy +9 sword', 'x' * 40, ''])
            flag = rng.choice([0, 1, 2])
            n_ = client.s
            na, ta = client.m.alloc(64, define=True), client.m.alloc(128, define=True)
            client.m.write(na, name.encode() + b'\0')
            client.m.write(ta, text.encode() + b'\0')
            client.records = []
            client.call(BUBBLE, (na, ta, flag))
            op = (Op * 2)()
            n = lib.mu_hn_chat_bubble(ctypes.byref(w), arr, len(order), name.encode(), text.encode(), flag, op)
            got, want = client_ops(client.records), lib_ops(op, n)
            assert same_ops(got, want), ('bubble', name, text, flag, got, want)
            counts['messages'] += n
            counts['calls'] += 1
        del window_object, n_
    return dict(counts)


SECTIONS['small'] = validate_small
SECTIONS['bubble'] = validate_bubble


# --------------------------------------------------------------------------- main



def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', default=str(DEFAULT_TEXT))
    parser.add_argument('--data', default=str(DEFAULT_DATA))
    parser.add_argument('--library', default=str(LIB))
    parser.add_argument('--cases', type=int, default=200)
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--only', default='', help='comma-separated sections')
    parser.add_argument('--output', default='')
    parser.add_argument('--negative', type=int, default=0, help='cases per planted mistake (0: skip the controls)')
    args = parser.parse_args()
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    if hashlib.sha256(text).hexdigest() != TEXT_SHA256 or hashlib.sha256(data).hexdigest() != DATA_SHA256:
        raise SystemExit('the pinned restored text and image data are required')
    lib = load_library(args.library)
    client = Client(text, data)
    sections = dict(helpers=validate_helpers, **SECTIONS)
    only = [s for s in args.only.split(',') if s]
    result = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'seed': args.seed, 'cases': args.cases,
              'bodies': {f'{a:#010x}': hashlib.sha256(text[a - cm.TEXT_BASE:cm.function_extent(text, a) - cm.TEXT_BASE]).hexdigest()[:16]
                         for a in (HEIGHT, NAME, ADD_INFO, UPDATE, SET_HP, REMOVE, SELECT, MESSAGE, BUBBLE)},
              'sections': {}}
    ok = True
    for name, fn in sections.items():
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
            for name in ('helpers', 'addinfo', 'update', 'small', 'bubble'):
                try:
                    sections[name](client, lib, random.Random(f'{args.seed}:{plant}:{name}'), args.negative)
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
