#!/usr/bin/env python3
"""Compare the reconstructed scene manager with the client (NATIVE-SHELL-001).

Every case runs one client routine in Unicorn over the pinned restored text
and second image section (scripts/client_ui_machine.py) and the
reconstruction in reconstructed/scene through ctypes, from the same seeded
state, then compares:

* the ordered trace: every call the routine makes into another subsystem
  (each direct callee is a recording stub: callee address, this pointer and
  stack arguments; string arguments by content; stack addresses as one
  token) interleaved with every write into the case's heap objects;
* the scene globals afterwards (SceneFlag and every global the routine reads
  or writes; reads of globals the case did not seed stop the case).

The C side runs against the same Unicorn memory (its host reads and writes
there), and both sides get their callees' return values from the same
per-case script, keyed by the call's position.

Client code run unmodified (pinned below):
  scene dispatcher 0x01859d8a, intro/title scene 0x0185ad63, login-scene
  creation 0x01851804, the scene-3 tick tail 0x01857621..0x018576a7, the
  frame-driver music block 0x0185276c..0x0185280c, start loading 0x0185a75a,
  loading scene 0x01851adc, and the stack probe 0x0191c5a0.
  NATIVE-LOGIN-001: the login render's 3D part 0x01857ed9..0x0185810e (with
  the camera far-plane leaf 0x0098ac45 as client code) and the login tick
  head 0x01857236..0x01857322.
  With reconstructed/ui: CLoadingScene::Create 0x00cdb74c and ::Render
  0x00cdb94f over the client's CSprite routines (GL call streams compared
  with validate_ui's machinery).

Modelled (not client code): every callee of those routines (recording
stubs), the uncaptured globals (seeded per case), the heap objects the
routines touch (UI manager, character record, Hero, GFx state; fake
vtables), the std::string constructor (keeps the char pointer), sprintf
(%d/%s), strcpy and strlen. The network sends inside two routines are
outside the project's scope; their packet-builder calls are collapsed into
one NET_SEND record on the client side.
"""
import argparse
import ctypes
from ctypes import CFUNCTYPE, POINTER, Structure, c_char_p, c_float, c_int32, c_uint8, c_uint16, c_uint32, c_void_p
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402

TEXT_BYTES, TEXT_SHA256 = pins.TEXT.size, pins.TEXT.sha256
DATA_BYTES, DATA_SHA256 = pins.DATA.size, pins.DATA.sha256

STACK_TOKEN = 0x5354414b
NET_SEND = 0x4e455453
VCALL = 0x56434c4c
CHKSTK = (0x0191c5a0, 0x0191c5e0)

# Executed client code: (start, end); digests are pinned in PINNED and checked.
ROUTINES = {
    'dispatch': (0x01859d8a, 0x01859f23),
    'intro': (0x0185ad63, 0x0185b243),
    'login_create': (0x01851804, 0x018519f3),
    'login_tail': (0x01857621, 0x018576a7),
    'frame_music': (0x0185276c, 0x0185280c),
    'start_loading': (0x0185a75a, 0x0185a9bf),
    'loading': (0x01851adc, 0x01851d39),
    # NATIVE-LOGIN-001: the login scene's 3D part
    'login_render': (0x01857ed9, 0x0185810e),
    'login_tick_head': (0x01857236, 0x01857322),
}
# Blocks that stop at one of several addresses (the end above or an early exit).
BLOCK_ENDS = {'login_render': (0x0185810e, 0x018588cd), 'login_tick_head': (0x01857322, 0x01857448)}
# Leaf client routines run as client code inside a block (besides the block itself).
EXTRA_CODE = {'login_render': [(0x0098ac45, 0x0098ac7c), (0x018588cd, 0x018588ce)],
              'login_tick_head': [(0x01857448, 0x01857449)]}
PINNED = {}   # filled from PINNED_JSON below at import

# Stack argument words of every callee (thiscall callees pop them; cdecl
# callees leave them to the caller). Values are (words, callee pops).
CALLEES = {
    0x00c74245: (0, 0), 0x01185472: (0, 0), 0x00aef92d: (0, 0), 0x00cd4ea8: (0, 0), 0x00cd5d29: (1, 4),
    0x01983b90: (3, 0), 0x0185ad63: (1, 0), 0x01851adc: (1, 0), 0x01851d39: (1, 0), 0x00ac3bf7: (0, 0),
    0x00ac9be9: (1, 4), 0x0120f6d4: (0, 0),
    # packet builder (collapsed into NET_SEND)
    0x00d51b91: (0, 0), 0x00d51baf: (2, 8), 0x00d51c9b: (3, 12), 0x00d51d4f: (2, 8), 0x00d51ba6: (0, 0),
    0x00d51d10: (1, 4),
    # intro
    0x01206785: (1, 4), 0x0185cf00: (0, 0), 0x0185d160: (1, 4), 0x009619dd: (2, 0), 0x0094997e: (1, 4),
    0x0185daa0: (1, 4), 0x0094f183: (0, 0), 0x011e228b: (0, 0), 0x016a5524: (1, 0), 0x012b0e65: (0, 0),
    0x0185baac: (6, 0), 0x0095f75d: (0, 0), 0x011e230d: (0, 0), 0x0184a990: (1, 0), 0x0182049e: (1, 0),
    0x0182a0da: (0, 0), 0x00f2bb92: (0, 0), 0x00f2951e: (0, 0), 0x011e2c8c: (3, 12), 0x011e2bc3: (0, 0),
    0x0185bc1b: (2, 0), 0x00a05a22: (0, 0), 0x01206888: (2, 8), 0x0185d0a0: (0, 0),
    # login creation
    0x0182876e: (1, 0), 0x0182a34c: (0, 0), 0x011e2dc0: (0, 0), 0x0121c055: (2, 0), 0x00f2efe9: (0, 0),
    0x00f2f47f: (0, 0), 0x01983a90: (2, 0), 0x0195a4b0: (1, 0), 0x0185498e: (0, 0), 0x00b95a14: (1, 4),
    0x0120f602: (1, 0), 0x0120f5a0: (1, 0), 0x00b49bf4: (1, 4), 0x00b4b848: (1, 4),
    # login tick tail
    0x01206598: (2, 0), 0x00988c5c: (0, 0), 0x00988d22: (3, 12), 0x01287a66: (0, 0), 0x008e7f90: (0, 0),
    0x00aab55d: (1, 0), 0x0182a4f1: (0, 0), 0x0137c276: (1, 0),
    # start loading
    0x0095f6db: (0, 0), 0x009a13f4: (1, 4), 0x0129deaa: (0, 0), 0x011e3598: (2, 8), 0x00a00031: (1, 4),
    0x00a0033e: (1, 4), 0x0182a85e: (0, 0), 0x00b4c117: (0, 0), 0x009a595b: (0, 0),
    # loading
    0x01989721: (0, 0), 0x0194cd00: (3, 0), 0x0191ba7b: (1, 0), 0x00cdb6ca: (0, 0), 0x00cdb74c: (0, 0),
    0x0184adc7: (4, 0), 0x0184f793: (0, 0), 0x00cdb94f: (0, 0), 0x0184f8d7: (0, 0), 0x0184b6dd: (0, 0),
    # login render (3D part)
    0x016bc355: (0, 0), 0x0098647b: (0, 0), 0x016cba24: (3, 0), 0x016cd468: (1, 0), 0x0137a3c2: (0, 0),
    0x00c9e4e3: (0, 0), 0x016d5020: (0, 0), 0x01589b56: (1, 0), 0x015181fa: (1, 4), 0x01692887: (0, 0),
    0x01538145: (0, 0), 0x00c9fd8d: (1, 0), 0x016d6949: (0, 0), 0x00b990b0: (0, 0), 0x00eb0dee: (0, 0),
    0x0184a699: (0, 0), 0x0169270e: (1, 4), 0x0159123f: (1, 4), 0x0184a6ab: (0, 0),
    # login tick head
    0x01851804: (0, 0), 0x016ca4fa: (0, 0), 0x016d82c7: (0, 0), 0x00c9e24a: (0, 0), 0x01537a43: (0, 0),
    0x0137a7ce: (0, 0), 0x009c104e: (1, 0), 0x0106bcc5: (1, 4), 0x0150ddb1: (0, 0), 0x01589b06: (0, 0),
    0x0159122d: (0, 0), 0x00c9eb04: (0, 0), 0x00eb0d64: (0, 0), 0x009c2aea: (0, 0), 0x009b9913: (0, 0),
    0x00ac9613: (1, 4), 0x01854529: (0, 0),
}
# argument index of a pointer to three floats whose words are compared (as text)
VECTOR_ARG = {0x016cba24: 1}
# sprintf takes a variable list: the format decides (see Client.sprintf).
VARARGS = {0x009619dd}
PACKET = {0x00d51b91, 0x00d51baf, 0x00d51c9b, 0x00d51d4f, 0x00d51ba6, 0x00d51d10}
IMPORTS = {0x01a7c6cc: (4, 16), 0x01a7c6e8: (1, 4), 0x01a7c148: (1, 4), 0x01a7c49c: (0, 0),
           0x01a7c83c: (4, 16), 0x01a7c76c: (3, 12)}
# argument index holding a C string whose content is compared
STRING_ARG = {0x0185baac: 0, 0x009619dd: 1, 0x01206598: 1}
# std::string arguments (resolved through the constructor stub)
STD_STRING_ARG = {0x0120f602: 0, 0x0120f5a0: 0}
# callees whose string argument pointer is replaced by its content only
POINTER_BLIND = {0x0185baac: 0}
VTABLE_ARGS = {0x00: 1, 0x44: 0}
INTERNAL = {0x0094997e, 0x0094f183}   # std::string ctor/dtor around PlayMp3/StopMp3 (not in the trace)

GLOBALS = [
    ('scene', 0x01d1df70, 'i'), ('protocol', 0x06fca2c4, 'i'), ('world', 0x01cf15fc, 'i'),
    ('world_folder', 0x01cf1600, 'i'), ('selected_hero', 0x01cf1864, 'i'), ('loading_world', 0x0b437c14, 'i'),
    ('send_counter', 0x06fc9e4c, 'i'), ('remember_id', 0x01cf0fac, 'i'), ('id_length', 0x0b4371b0, 'i'),
    ('id_field_1118', 0x01cf1118, 'i'), ('id_present', 0x0b436578, 'i'), ('field_1110', 0x01cf1110, 'i'),
    ('frame_tick', 0x0bdc5e64, 'I'), ('login_fade', 0x0bdc5b80, 'f'), ('init_login', 0x0bdc5b86, 'B'),
    ('init_loading', 0x0bdc5b87, 'B'), ('init_character', 0x0bdc5ca2, 'B'), ('init_main', 0x0bdc5ca3, 'B'),
    ('gl_cache_597c', 0x0bdc597c, 'B'), ('loop_flag_2d1e', 0x01d22d1e, 'B'), ('login_flag_5eb8', 0x0bdc5eb8, 'B'),
    ('login_flag_5b7b', 0x0bdc5b7b, 'B'), ('login_flag_656e', 0x0b43656e, 'B'),
    ('login_flag_656f', 0x0b43656f, 'B'), ('login_flag_6570', 0x0b436570, 'B'),
    ('login_flag_1109', 0x01cf1109, 'B'), ('login_flag_71e1', 0x0b4371e1, 'B'),
    ('server_address', 0x01cf1858, 'I'), ('server_port', 0x01cf185c, 'H'),
    ('music_login', 0x01cf1700, 'I'), ('view_far', 0x01cf1630, 'f'),
]
ID_BUFFER = 0x0b436580
HERO_POINTER = 0x01d1df1c


# --------------------------------------------------------------------------
# ctypes view of reconstructed/scene

class Call(Structure):
    _fields_ = [('routine', c_uint32), ('ecx', c_uint32), ('count', c_int32), ('args', c_uint32 * 8),
                ('text', c_char_p)]


CALLFN = CFUNCTYPE(c_uint32, c_void_p, POINTER(Call))
PEEKFN = CFUNCTYPE(c_uint32, c_void_p, c_uint32, c_int32)
POKEFN = CFUNCTYPE(None, c_void_p, c_uint32, c_uint32, c_int32)


class Host(Structure):
    _fields_ = [('user', c_void_p), ('call', CALLFN), ('peek', PEEKFN), ('poke', POKEFN)]


class Globals(Structure):
    _fields_ = [('scene', c_int32), ('protocol', c_int32), ('world', c_int32), ('world_folder', c_int32),
                ('selected_hero', c_int32), ('loading_world', c_int32), ('send_counter', c_int32),
                ('remember_id', c_int32), ('id_length', c_int32), ('id_field_1118', c_int32),
                ('id_present', c_int32), ('field_1110', c_int32), ('frame_tick', c_uint32), ('login_fade', c_float),
                ('init_login', c_uint8), ('init_loading', c_uint8), ('init_character', c_uint8),
                ('init_main', c_uint8), ('gl_cache_597c', c_uint8), ('loop_flag_2d1e', c_uint8),
                ('login_flag_5eb8', c_uint8), ('login_flag_5b7b', c_uint8), ('login_flag_656e', c_uint8),
                ('login_flag_656f', c_uint8), ('login_flag_6570', c_uint8), ('login_flag_1109', c_uint8),
                ('login_flag_71e1', c_uint8), ('server_address', c_uint32), ('server_port', c_uint16),
                ('music_login', c_uint32), ('id_buffer', c_uint32), ('view_far', c_float)]


def library(path=None):
    path = path or ROOT / 'reconstructed/scene' / ('libscene.dylib' if sys.platform == 'darwin' else 'libscene.so')
    lib = ctypes.CDLL(str(path))
    P = c_void_p
    for name, args in {'mu_scenemgr_dispatch': [P, P, c_uint32], 'mu_scenemgr_intro': [P, P, c_uint32],
                       'mu_scenemgr_login_create': [P, P], 'mu_scenemgr_login_tick_tail': [P, P],
                       'mu_scenemgr_frame_music': [P, P], 'mu_scenemgr_start_loading': [P, P, c_int32],
                       'mu_scenemgr_loading': [P, P, c_uint32], 'mu_scenemgr_return_to_character': [P],
                       'mu_scenemgr_login_render_3d': [P, P], 'mu_scenemgr_login_tick_head': [P, P]}.items():
        getattr(lib, name).argtypes = args
        getattr(lib, name).restype = None
    lib.mu_scenemgr_dispatch_target.argtypes = [c_int32]
    lib.mu_scenemgr_dispatch_target.restype = c_int32
    lib.mu_scenemgr_login_render_3d.restype = c_int32
    lib.mu_scenemgr_login_tick_head.restype = c_int32
    return lib


def build_library():
    import subprocess
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/scene')], check=True)


# --------------------------------------------------------------------------
# one case: shared script of return values and memory helpers

def c_string(m, address, limit=512):
    raw = m.read(address, limit)
    return raw.split(b'\0', 1)[0].decode('latin1')


def sprintf(m, words):
    """%d and %s formatting as the client's sprintf; returns (text, used argument words)."""
    fmt = c_string(m, words[1])
    out, i, arg = [], 0, 2
    while i < len(fmt):
        ch = fmt[i]
        if ch == '%' and i + 1 < len(fmt):
            spec = fmt[i + 1]
            if spec == 'd':
                out.append(str(struct.unpack('<i', struct.pack('<I', words[arg]))[0]))
                arg += 1
            elif spec == 's':
                out.append(c_string(m, words[arg]))
                arg += 1
            else:
                out.append('%' + spec)
            i += 2
        else:
            out.append(ch)
            i += 1
    return ''.join(out), arg


class Script:
    """Per-case return values, keyed by (callee, occurrence)."""

    def __init__(self, rng, case):
        self.rng, self.case = rng, case
        self.counts = {}

    def value(self, routine, m, ecx, args):
        k = self.counts.get(routine, 0)
        self.counts[routine] = k + 1
        handles = self.case['handles']
        if routine in handles:
            v = handles[routine]
            return v[k % len(v)] if isinstance(v, list) else v
        if routine == 0x01983a90:   # strcpy(dst, src)
            text = m.read(args[1], 512).split(b'\0', 1)[0]
            m.write(args[0], text + b'\0')
            return args[0]
        if routine == 0x0195a4b0:   # strlen
            return len(m.read(args[0], 512).split(b'\0', 1)[0])
        if routine == 0x00cdb6ca:   # CLoadingScene constructor: vtable, returns this
            m.put32(ecx, self.case['vtable'])
            return ecx
        return self.case['returns'].get((routine, k), (routine * 2654435761 + k) & 0x7fff)


class Tracer:
    def __init__(self):
        self.trace = []

    def call(self, routine, ecx, args, text):
        self.trace.append(('call', routine, ecx, tuple(args), text))

    def write(self, address, size, value):
        self.trace.append(('write', address, size, value & ((1 << (8 * size)) - 1)))


def normalize(m, routine, ecx, args, text_from_client):
    """Stack tokens and string contents, the same way for both sides."""
    args = list(args)
    def stack(v):
        return STACK_TOKEN if cm.STACK_BASE <= v < cm.STACK_BASE + cm.STACK_SIZE else v
    args = [stack(a) for a in args]
    ecx = stack(ecx)
    return routine, ecx, args


# --------------------------------------------------------------------------
# client side

class Client:
    def __init__(self, text, data):
        self.m = cm.Machine(text, data)
        self.vtable_stubs = {}
        self.stub_address = {}
        self.import_stub = {}
        for slot in IMPORTS:
            self.import_stub[slot] = self.m._new_stub()
        self.vtable = None
        self.write_hook = None

    def prepare(self, case, script, tracer, routine_name):
        m = self.m
        m.reset()
        m.allowed = [ROUTINES[routine_name], CHKSTK] + EXTRA_CODE.get(routine_name, [])
        for slot, address in self.import_stub.items():
            m.uc.mem_write(slot, struct.pack('<I', address))
        self.strings = {}   # std::string object -> char pointer
        self.collapsing = False
        self.case, self.script, self.tracer = case, script, tracer

        def make(routine, words, pops):
            def handler(mm):
                if routine in VARARGS:
                    text, used = sprintf(mm, mm.args(8))
                    raw = mm.args(used)
                    mm.uc.mem_write(raw[0], text.encode('latin1') + b'\0')
                    self.record(routine, 0, raw)
                    return self.script.value(routine, mm, 0, raw)
                raw = mm.args(words)
                ecx = mm.uc.reg_read(cm.UC_X86_REG_ECX)
                if routine == 0x0094997e:
                    self.strings[ecx] = raw[0]
                    return ecx
                if routine == 0x0094f183:
                    return 0
                if routine in PACKET:
                    if routine == 0x00d51b91:
                        self.record(NET_SEND, 0, [])
                    self.collapsing = routine != 0x00d51ba6
                    return 0
                if self.collapsing and routine in (0x0129deaa, 0x008e7f90, 0x0195a4b0):
                    return self.script.value(routine, mm, ecx, raw)
                self.record(routine, ecx if routine in THISCALL else 0, raw)
                return self.script.value(routine, mm, ecx, raw)
            return handler

        own = ROUTINES[routine_name]
        for routine, (words, pops) in CALLEES.items():
            if own[0] <= routine < own[1]:
                m.stubs.pop(routine, None)   # the routine under test runs as client code
                continue
            m.stub(routine, make(routine, words, pops), pops)
        for slot, address in self.import_stub.items():
            words, pops = IMPORTS[slot]
            m.stub(address, make(slot, words, pops), pops)
        # fake vtable: entry k records a virtual call at offset 4k
        if self.vtable is None:
            self.vtable_entries = []
            for k in range(32):
                self.vtable_entries.append(m._new_stub())
        for k, address in enumerate(self.vtable_entries):
            offset = 4 * k
            words = VTABLE_ARGS.get(offset, 0)

            def vhandler(mm, offset=offset, words=words):
                raw = mm.args(words)
                self.record(VCALL, mm.uc.reg_read(cm.UC_X86_REG_ECX), [offset] + raw)
                return self.script.value((VCALL << 8) | offset, mm, 0, raw)
            m.stub(address, vhandler, 4 * words)
        # the routine's code may write its own heap objects: recorded
        if self.write_hook is None:
            self.write_hook = m.uc.hook_add(cm.UC_HOOK_MEM_WRITE, self._on_write, begin=cm.HEAP_BASE,
                                            end=cm.HEAP_BASE + cm.HEAP_SIZE - 1)
        self.recording = True

    def _on_write(self, uc, access, address, size, value, user):
        if self.recording:
            self.tracer.write(address, size, value)

    def record(self, routine, ecx, raw):
        m = self.m
        text = None
        args = list(raw)
        if routine in STRING_ARG:
            text = c_string(m, args[STRING_ARG[routine]])
        if routine in VECTOR_ARG:
            text = '%08x %08x %08x' % struct.unpack('<3I', m.read(args[VECTOR_ARG[routine]], 12))
        if routine in STD_STRING_ARG:
            i = STD_STRING_ARG[routine]
            pointer = self.strings.get(args[i])
            if pointer is None:
                raise cm.CaseError(f'{routine:#x}: argument is not a constructed string')
            args[i] = pointer
        if routine in POINTER_BLIND:
            args[POINTER_BLIND[routine]] = 0
        routine, ecx, args = normalize(m, routine, ecx, args, text)
        self.tracer.call(routine, ecx, args, text)


THISCALL = {0x01185472, 0x00aef92d, 0x00cd5d29, 0x00ac9be9, 0x01206785, 0x0185cf00, 0x0185d160, 0x0185daa0,
            0x011e230d, 0x00f2951e, 0x011e2c8c, 0x011e2bc3, 0x00a05a22, 0x01206888, 0x0185d0a0, 0x011e2dc0,
            0x00f2f47f, 0x00b95a14, 0x00b49bf4, 0x00b4b848, 0x00988d22, 0x008e7f90, 0x009a13f4, 0x0129deaa,
            0x011e3598, 0x00a00031, 0x00a0033e, 0x00b4c117, 0x00cdb6ca, 0x00cdb74c, 0x00cdb94f,
            0x015181fa, 0x01692887, 0x01538145, 0x00eb0dee, 0x0169270e, 0x0159123f, 0x01537a43, 0x0106bcc5,
            0x0150ddb1, 0x0159122d, 0x00eb0d64, 0x009b9913, 0x00ac9613}


def seed_globals(m, g):
    for name, address, fmt in GLOBALS:
        m.write(address, struct.pack('<' + fmt, getattr(g, name)))


def read_globals(m):
    out = {}
    for name, address, fmt in GLOBALS:
        out[name] = struct.unpack('<' + fmt, m.read(address, struct.calcsize(fmt)))[0]
    return out


def c_globals(g):
    return {name: getattr(g, name) for name, _, _ in GLOBALS}


def same_globals(a, b):
    for k in a:
        x, y = a[k], b[k]
        if isinstance(x, float) or isinstance(y, float):
            if struct.pack('<f', x) != struct.pack('<f', y):
                return k
        elif x != y:
            return k
    return None


# --------------------------------------------------------------------------
# authored side

class Authored:
    def __init__(self, lib, client):
        self.lib, self.client = lib, client

    def run(self, routine_name, case, script, tracer, setup):
        m = self.client.m
        self.client.recording = False

        def on_call(user, pointer):
            c = pointer.contents
            args = [c.args[i] for i in range(c.count)]
            text = c.text.decode('latin1') if c.text else None
            routine = c.routine
            record_args = list(args)
            if routine in STRING_ARG and text is None:
                text = c_string(m, args[STRING_ARG[routine]])
            if routine in POINTER_BLIND:
                record_args[POINTER_BLIND[routine]] = 0
            tracer.call(routine, c.ecx, record_args, text)
            if routine == VCALL:
                return script.value((VCALL << 8) | args[0], m, 0, args[1:])
            return script.value(routine, m, c.ecx, args)

        def on_peek(user, address, size):
            raw = m.read(address, size)
            return int.from_bytes(raw, 'little')

        def on_poke(user, address, value, size):
            tracer.write(address, size, value)
            m.write(address, int(value & ((1 << (8 * size)) - 1)).to_bytes(size, 'little'))

        host = Host(None, CALLFN(on_call), PEEKFN(on_peek), POKEFN(on_poke))
        g = setup()
        self._keep = host
        return host, g


# --------------------------------------------------------------------------
# cases

def base_globals(rng):
    g = Globals()
    g.scene = rng.choice([2, 3, 4, 5, 6])
    g.protocol = rng.choice([0, 0x14, 0x33, rng.randint(0, 100)])
    g.world = rng.randint(0, 150)
    g.world_folder = g.world
    g.selected_hero = rng.choice([-1, 0, 1, 4, 9, rng.randint(0, 9)])
    g.loading_world = rng.randint(0, 100)
    g.send_counter = rng.randint(0, 31)
    g.remember_id = rng.choice([0, 1, 5])
    g.id_length = rng.randint(0, 9)
    g.id_field_1118 = rng.randint(0, 9)
    g.id_present = rng.randint(0, 1)
    g.field_1110 = rng.randint(0, 9)
    g.frame_tick = rng.getrandbits(32)
    g.login_fade = cm.f32(rng.uniform(0, 10))
    for name in ('init_login', 'init_loading', 'init_character', 'init_main', 'gl_cache_597c', 'loop_flag_2d1e',
                 'login_flag_5eb8', 'login_flag_5b7b', 'login_flag_656e', 'login_flag_656f', 'login_flag_6570',
                 'login_flag_1109', 'login_flag_71e1'):
        setattr(g, name, rng.randint(0, 1))
    g.server_port = rng.randint(0, 65535)
    g.id_buffer = ID_BUFFER
    return g


def heap_objects(m, rng, case):
    """UI manager, GFx owner and state, character record, Hero, strings."""
    vtable = m.alloc(0x80, define=True)
    for k, address in enumerate(case['client'].vtable_entries):
        m.put32(vtable + 4 * k, address)
    case['vtable'] = vtable
    ui = m.alloc(0x6600, define=True)
    gfx = m.alloc(0x100, define=True)
    m.put32(gfx, vtable)
    owner = m.alloc(0x240, define=True)
    m.put32(owner + 0x22c, gfx)
    owner_a0 = m.alloc(0x40, define=True)
    m.put32(owner + 0xa0, owner_a0)
    state = m.alloc(0x40, define=True)
    music = m.alloc(64, define=True)
    m.write(music, b'data\\music\\login_theme.mp3\0')
    server = m.alloc(32, define=True)
    m.write(server, b'127.0.0.1\0')
    hero = m.alloc(0x400, define=True)
    m.write(hero, bytes(rng.getrandbits(8) for _ in range(0x400)))
    m.put32(HERO_POINTER, hero)
    record = m.alloc(0x200, define=True)
    m.write(record, bytes(rng.getrandbits(8) for _ in range(0x200)))
    name = ''.join(rng.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(rng.randint(1, 10)))
    m.write(record + 0x44, name.encode() + b'\0')
    saved = m.alloc(64, define=True)
    m.write(saved, ''.join(rng.choice('xyz019') for _ in range(rng.randint(0, 10))).encode() + b'\0')
    m.write(ID_BUFFER, bytes(64))
    config = m.alloc(16, define=True)
    m.write(config + 4, bytes([rng.choice([0, 1, 2, 255])]))
    loading_memory = m.alloc(0x2a8, define=True)
    single = m.alloc(0x300, define=True)
    camera_record = m.alloc(0x40, define=True)
    m.write(camera_record, struct.pack('<9f', *(cm.f32(rng.uniform(-90, 90)) for _ in range(3)),
                                       *(cm.f32(rng.uniform(0, 25600)) for _ in range(2)), cm.f32(rng.uniform(0, 2000)),
                                       cm.f32(rng.choice([0.325, rng.uniform(0, 2)])),
                                       cm.f32(rng.choice([32.1, rng.uniform(0, 40)])), 35.0))
    camera = m.alloc(0x20, define=True)
    m.put32(camera + 0xc, camera_record)
    m.write(camera + 0x10, struct.pack('<f', cm.f32(rng.choice([1.0, 1.0, rng.uniform(0.5, 2.0)]))))
    m.write(ui + 0x4654, bytes([rng.choice([0, 0, 0, 1])]))
    case.update(camera=camera, ui=ui, gfx=gfx, owner=owner, state=state, music=music, server=server, hero=hero, record=record,
                saved=saved, config=config, loading_memory=loading_memory, single=single)
    return case


def make_case(client, rng, routine):
    m = client.m
    case = {'client': client, 'returns': {}}
    heap_objects(m, rng, case)
    g = base_globals(rng)
    g.music_login = case['music']
    g.server_address = case['server']
    handles = {
        0x011e228b: case['ui'], 0x00ac3bf7: case['owner'], 0x009a595b: case['state'], 0x0095f75d: case['config'],
        0x00f2f47f: case['saved'], 0x00cd4ea8: case['single'], 0x00cd5d29: case['single'],
        0x00c74245: case['single'], 0x00f2efe9: case['single'], 0x00f2bb92: case['single'],
        0x0095f6db: case['single'], 0x00988c5c: case['single'], 0x0129deaa: case['single'],
        0x01a7c49c: rng.getrandbits(32), 0x01989721: rng.randint(0, 0x7fff),
        0x0098647b: case['camera'], 0x016bc355: rng.choice([640, 800, 1280, 1722, 1920, rng.randint(1, 4000)]),
    }
    if routine == 'start_loading':
        handles[0x009a13f4] = rng.choice([0, case['record'], case['record']])
        m.write(case['record'] + 0x14, bytes([rng.choice([0, 1, 2, 3])]))
    if routine == 'loading':
        handles[0x0191ba7b] = rng.choice([case['loading_memory'], case['loading_memory'], 0])
        m.put32(case['ui'] + 0x6598, rng.choice([0, case['loading_memory']]))
        m.put32(case['loading_memory'], case['vtable'])   # an object left by an earlier call
    case['handles'] = handles
    if routine == 'dispatch':
        g.scene = rng.choice([-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 100, rng.randint(-5, 20)])
        if rng.random() < 0.15:
            g.send_counter = rng.randint(32, 200)
    if routine == 'frame_music':
        g.scene = rng.choice([0, 1, 2, 3, 4, 5, 6, 7])
    return case, g


def snapshot_heap(m, case):
    keys = ('ui', 'gfx', 'owner', 'state', 'hero', 'record', 'config', 'loading_memory', 'single')
    sizes = {'ui': 0x6600, 'gfx': 0x100, 'owner': 0x240, 'state': 0x40, 'hero': 0x400, 'record': 0x200,
             'config': 16, 'loading_memory': 0x2a8, 'single': 0x300}
    blob = b''.join(m.read(case[k], sizes[k]) for k in keys)
    return blob + m.read(ID_BUFFER, 64)


def run_block(m, start, end, frame=0x400):
    """Run client code from start to end inside a synthetic frame (blocks of a larger function)."""
    uc = m.uc
    ebp = cm.STACK_BASE + cm.STACK_SIZE - 0x2000
    esp = ebp - frame
    uc.reg_write(cm.UC_X86_REG_ESP, esp)
    uc.reg_write(cm.UC_X86_REG_EBP, ebp)
    for register in (cm.UC_X86_REG_EAX, cm.UC_X86_REG_ECX, cm.UC_X86_REG_EDX, cm.UC_X86_REG_EBX,
                     cm.UC_X86_REG_ESI, cm.UC_X86_REG_EDI):
        uc.reg_write(register, 0)
    try:
        uc.emu_start(start, end, count=2_000_000)
    except cm.UcError as error:
        m.errors.append(f'{error} at eip {uc.reg_read(cm.UC_X86_REG_EIP):#x}')
    if uc.reg_read(cm.UC_X86_REG_EIP) != end and not m.errors:
        m.errors.append(f'block stopped at {uc.reg_read(cm.UC_X86_REG_EIP):#x}')
    if m.errors:
        raise cm.CaseError('; '.join(m.errors[:4]))


def run_block_ends(m, start, ends, frame=0x400):
    """Run a function from its entry until EIP reaches one of `ends` (the 3D part of a larger routine)."""
    uc = m.uc
    ebp = cm.STACK_BASE + cm.STACK_SIZE - 0x2000
    uc.reg_write(cm.UC_X86_REG_ESP, ebp - frame)
    uc.reg_write(cm.UC_X86_REG_EBP, ebp)
    for register in (cm.UC_X86_REG_EAX, cm.UC_X86_REG_ECX, cm.UC_X86_REG_EDX, cm.UC_X86_REG_EBX,
                     cm.UC_X86_REG_ESI, cm.UC_X86_REG_EDI):
        uc.reg_write(register, 0)
    hooks = [uc.hook_add(cm.UC_HOOK_CODE, lambda u, a, s, d: u.emu_stop(), begin=e, end=e) for e in ends[1:]]
    try:
        uc.emu_start(start, ends[0], count=2_000_000)
    except cm.UcError as error:
        m.errors.append(f'{error} at eip {uc.reg_read(cm.UC_X86_REG_EIP):#x}')
    finally:
        for h in hooks:
            uc.hook_del(h)
    if uc.reg_read(cm.UC_X86_REG_EIP) not in ends and not m.errors:
        m.errors.append(f'block stopped at {uc.reg_read(cm.UC_X86_REG_EIP):#x}')
    if m.errors:
        raise cm.CaseError('; '.join(m.errors[:4]))


def client_run(client, routine, case, g, hdc, start):
    m = client.m
    if routine == 'dispatch':
        m.call(0x01859d8a, [hdc])
    elif routine == 'intro':
        m.call(0x0185ad63, [hdc])
    elif routine == 'login_create':
        m.call(0x01851804)
    elif routine == 'login_tail':
        run_block(m, *ROUTINES['login_tail'])
    elif routine == 'frame_music':
        run_block(m, *ROUTINES['frame_music'], frame=0x200)
    elif routine == 'start_loading':
        m.call(0x0185a75a, [start])
    elif routine == 'loading':
        m.call(0x01851adc, [hdc])
    elif routine in BLOCK_ENDS:
        run_block_ends(m, ROUTINES[routine][0], BLOCK_ENDS[routine])


def authored_run(lib, routine, host, g, hdc, start):
    hp, gp = ctypes.byref(host), ctypes.byref(g)
    {'dispatch': lambda: lib.mu_scenemgr_dispatch(hp, gp, hdc),
     'intro': lambda: lib.mu_scenemgr_intro(hp, gp, hdc),
     'login_create': lambda: lib.mu_scenemgr_login_create(hp, gp),
     'login_tail': lambda: lib.mu_scenemgr_login_tick_tail(hp, gp),
     'frame_music': lambda: lib.mu_scenemgr_frame_music(hp, gp),
     'start_loading': lambda: lib.mu_scenemgr_start_loading(hp, gp, start),
     'loading': lambda: lib.mu_scenemgr_loading(hp, gp, hdc),
     'login_render': lambda: lib.mu_scenemgr_login_render_3d(hp, gp),
     'login_tick_head': lambda: lib.mu_scenemgr_login_tick_head(hp, gp)}[routine]()


def run_case(client, lib, routine, seed, mutate=None):
    """Returns (client trace, authored trace, client globals, authored globals, heap equal)."""
    rng = random.Random(seed)
    hdc = rng.getrandbits(31) | 0x10000001   # outside the stack range (stack addresses become a token)
    start = rng.choice([0, 1, 1])
    # client
    tracer_c = Tracer()
    rng_case = random.Random(seed * 7 + 1)
    client.prepare(None, None, tracer_c, routine)
    case, g = make_case(client, rng_case, routine)
    script_c = Script(rng_case, case)
    client.case, client.script = case, script_c
    seed_globals(client.m, g)
    g_before = Globals.from_buffer_copy(g)
    client_run(client, routine, case, g, hdc, start)
    client.recording = False
    globals_c = read_globals(client.m)
    heap_c = snapshot_heap(client.m, case)
    # authored, from the same state
    tracer_a = Tracer()
    rng_case = random.Random(seed * 7 + 1)
    client.prepare(None, None, tracer_a, routine)
    client.recording = False
    case2, g2 = make_case(client, rng_case, routine)
    script_a = Script(rng_case, case2)
    seed_globals(client.m, g2)
    if mutate:
        mutate(g2)
    authored = Authored(lib, client)
    host, _ = authored.run(routine, case2, script_a, tracer_a, lambda: g2)
    authored_run(lib, routine, host, g2, hdc, start)
    globals_a = c_globals(g2)
    heap_a = snapshot_heap(client.m, case2)
    return tracer_c.trace, tracer_a.trace, globals_c, globals_a, heap_c == heap_a, g_before


def diff_traces(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f'entry {i}: client {fmt_entry(x)} != authored {fmt_entry(y)}'
    if len(a) != len(b):
        extra = a[len(b):] if len(a) > len(b) else b[len(a):]
        return f'length client {len(a)} authored {len(b)}; first extra {fmt_entry(extra[0])}'
    return None


def fmt_entry(e):
    if e[0] == 'call':
        return f"call {e[1]:#010x} ecx={e[2]:#x} args={[hex(v) for v in e[3]]} text={e[4]!r}"
    return f'write {e[1]:#x}/{e[2]} = {e[3]:#x}'


def routine_digests(text):
    out = {}
    for name, (start, end) in list(ROUTINES.items()) + [('chkstk', CHKSTK)]:
        out[name] = {'start': f'{start:#010x}', 'end': f'{end:#010x}',
                     'sha256': hashlib.sha256(text[start - cm.TEXT_BASE:end - cm.TEXT_BASE]).hexdigest()}
    return out


# --------------------------------------------------------------------------
# CLoadingScene (reconstructed/ui) through validate_ui's machinery

def validate_loading_ui(text, data, cases, report):
    import validate_ui as vu
    lib = vu.library()
    lib.mu_ui_loading_create.argtypes = [c_void_p, c_void_p, c_int32, c_int32]
    lib.mu_ui_loading_create.restype = None
    lib.mu_ui_loading_render.argtypes = [c_void_p, c_void_p]
    lib.mu_ui_loading_render.restype = None
    client = vu.Client(text, data)
    client.machine.allow((0x00cdb6ca, 0x00cdb6fd), (0x00cdb74c, 0x00cdb91c), (0x00cdb94f, 0x00cdb982))
    count = 0
    windows = list(vu.WINDOWS) + [(800, 600), (1280, 1024), (2560, 1440), (1366, 768), (640, 480)]
    gl_calls = 0
    for case in range(cases + 1):
        window = windows[case % len(windows)]
        screen = window
        planted = case == cases   # last case: the C side gets the height off by one (must be detected)

        def cfn(m):
            dummy = m.alloc(0x100, define=True)

            def vector_constructor(mm):
                array, size, count_, ctor, dtor = mm.args(5)
                if ctor != 0x010ad7b2 or size != 0xa8:
                    return mm.fail(f'unexpected vector constructor {ctor:#x} size {size:#x}')
                for i in range(count_):
                    element = array + i * size
                    mm.put32(element, 0x01ab9ba8)
                    mm.put32(element + 0x78, 0)
                    mm.put32(element + 0xc, 0)
                return 0
            client.stub(0x0191b8be, vector_constructor, 0x14)
            client.stub(0x00cc3564, lambda mm: dummy)
            client.stub(0x009828b5, lambda mm: screen[0])
            client.stub(0x009828a6, lambda mm: screen[1])
            client.stub(0x009a4405, lambda mm: mm.uc.reg_read(cm.UC_X86_REG_ECX))   # CInput copy (pass through)
            client.stub(0x00cc3552, lambda mm: 0)
            obj = m.alloc(0x2a8, define=True)
            m.call(0x00cdb6ca, ecx=obj)
            m.call(0x00cdb74c, ecx=obj)
            m.calls.append(('--render--', ()))
            m.call(0x00cdb94f, ecx=obj)
        buf = ctypes.create_string_buffer(8192)

        def afn(a):
            lib.mu_ui_loading_create(a.sp, buf, screen[0], screen[1] + (1 if planted else 0))
            a.calls.append(('--render--', ()))
            lib.mu_ui_loading_render(a.sp, buf)
        got, want, _ = vu.run_pair(client, lib, window, vu.base_bitmaps(), cfn, afn)
        problem = vu.diff(got, want)
        if planted:
            if not problem:
                raise AssertionError('CLoadingScene: planted height error not detected')
            report['loading_screen_planted_detected'] = True
            break
        if problem:
            raise AssertionError(f'CLoadingScene {window}: {problem}')
        gl_calls += len(got)
        count += 1
    report['loading_screen_gl_calls'] = gl_calls
    report['loading_screen_cases'] = count


# --------------------------------------------------------------------------

def mutations():
    """Planted mistakes in the C side's inputs that the comparison must detect."""
    return [
        ('loading', 'init flag ignored', lambda g: setattr(g, 'init_loading', 1 - g.init_loading)),
        ('frame_music', 'scene off by one', lambda g: setattr(g, 'scene', g.scene + 1)),
        ('login_tail', 'protocol forced 0x14', lambda g: setattr(g, 'protocol', 0x14 if g.protocol != 0x14 else 0)),
        ('start_loading', 'selected hero changed', lambda g: setattr(g, 'selected_hero', g.selected_hero + 1)),
        ('dispatch', 'scene 3 <-> 5', lambda g: setattr(g, 'scene', {3: 4, 5: 2, 4: 3, 2: 5}.get(g.scene, 3))),
        ('login_create', 'remember flag flipped', lambda g: setattr(g, 'remember_id', 0 if g.remember_id else 1)),
        ('intro', 'scene already 3', lambda g: setattr(g, 'scene', 3 if g.scene != 3 else 2)),
        ('login_render', 'login not created', lambda g: setattr(g, 'init_login', 1 - g.init_login)),
        ('login_tick_head', 'scene passed to the GFx update', lambda g: setattr(g, 'scene', g.scene + 1)),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', default=pins.TEXT.default_str())
    parser.add_argument('--data', default=pins.DATA.default_str())
    parser.add_argument('--cases', type=int, default=200, help='cases per routine')
    parser.add_argument('--loading-ui-cases', type=int, default=40)
    parser.add_argument('--only', nargs='*', choices=sorted(ROUTINES) + ['loading_ui'])
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    text = pins.TEXT.read(args.text, mismatch=SystemExit('restored text does not match the pinned capture'))
    data = pins.DATA.read(args.data, mismatch=SystemExit('image data does not match the pinned capture'))
    digests = routine_digests(text)
    for name, pinned in PINNED.items():
        if digests[name]['sha256'] != pinned:
            raise SystemExit(f'{name}: routine bytes differ from the pinned digest')
    build_library()
    lib = library()
    client = Client(text, data)
    client.vtable_entries = [client.m._new_stub() for _ in range(32)]
    client.vtable = True
    report = {'routines': digests, 'cases': {}, 'started': time.strftime('%Y-%m-%dT%H:%M:%S')}
    only = set(args.only or list(ROUTINES) + ['loading_ui'])
    stats = {}
    for routine in ROUTINES:
        if routine not in only:
            continue
        n = calls = writes = sends = 0
        outcomes = {}
        for case in range(args.cases):
            seed = args.seed * 1000003 + case * 31 + sum(map(ord, routine))
            trace_c, trace_a, glob_c, glob_a, heap_ok, g0 = run_case(client, lib, routine, seed)
            problem = diff_traces(trace_c, trace_a)
            if problem:
                raise SystemExit(f'{routine} case {case} (seed {seed}): {problem}')
            key = same_globals(glob_c, glob_a)
            if key:
                raise SystemExit(f'{routine} case {case}: global {key} client {glob_c[key]} authored {glob_a[key]}')
            if not heap_ok:
                raise SystemExit(f'{routine} case {case}: heap objects differ')
            n += 1
            calls += sum(1 for e in trace_c if e[0] == 'call')
            writes += sum(1 for e in trace_c if e[0] == 'write')
            sends += sum(1 for e in trace_c if e[0] == 'call' and e[1] == NET_SEND)
            if any(e[0] == 'call' and e[1] in (0x016cd468, 0x016d82c7) for e in trace_c):
                outcomes['3D part ran'] = outcomes.get('3D part ran', 0) + 1
            outcome = f'{g0.scene}->{glob_c["scene"]}'
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        stats[routine] = {'cases': n, 'calls': calls, 'object_writes': writes, 'net_sends': sends,
                          'scene_transitions': outcomes}
        print(f'{routine}: {n} cases, {calls} calls, {writes} object writes, transitions {outcomes}', flush=True)
    report['cases'] = stats
    if 'loading_ui' in only:
        validate_loading_ui(text, data, args.loading_ui_cases, report)
        print(f"loading_ui: {report['loading_screen_cases']} cases", flush=True)
    if args.mutations:
        detected = []
        for routine, label, mutate in mutations():
            if routine not in only:
                continue
            found = False
            for case in range(60):
                seed = args.seed * 7919 + case
                trace_c, trace_a, glob_c, glob_a, heap_ok, _ = run_case(client, lib, routine, seed, mutate)
                if diff_traces(trace_c, trace_a) or same_globals(glob_c, glob_a) or not heap_ok:
                    found = True
                    break
            detected.append({'routine': routine, 'mutation': label, 'detected': found})
            print(f'mutation {routine} / {label}: {"detected" if found else "MISSED"}', flush=True)
        report['mutations'] = detected
        if not all(d['detected'] for d in detected):
            raise SystemExit('a planted mistake was not detected')
    report['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'routines'}, indent=1))


PINNED_JSON = """{
 "dispatch": "03bb564739db41b0451bee4e76d5eaeadd9ee249d19dc55cf9a38ba54d73728e",
 "intro": "ae70d856e537c5088528cdd475786249695707e663dbb449d4e0b0df10892359",
 "login_create": "5d242b6d58e57d03e30ecb0161d50be7de08a448f7c877a9f167132dee75969d",
 "login_tail": "b56d1f6edee7d6d58239abaac561d0a90922e9d00ef4c950ec0fc80524fdafa1",
 "frame_music": "ae7f48f571a5dd1eb8d3eafeeefacdbe75d0f08cc05fed1eee5d5558bd184747",
 "start_loading": "5cd7792c564f12b840179b4e539765314972cc811eeab60d13d9fe92717f7b67",
 "loading": "f8e88b133046f9a6c86c80bbaafe622b355c6a0af2e71e79537cef5bb5d14744",
 "login_render": "2c6317943d1e9eeafb2d45f9bdf48a0d05c7ba208359eea79b0382b75cde0658",
 "login_tick_head": "2239f0d5d5cbab893b134a6fd0b9882babb3cafbe06a7cb74045f23b8e3c47dc",
 "chkstk": "0f8ce31cd9b1ce0c271e496c2447217aee128105e3fb255669f8cb2607ef4519"
}"""
PINNED.update(json.loads(PINNED_JSON))

if __name__ == '__main__':
    main()
