#!/usr/bin/env python3
"""Compare the reconstructed click-to-move path finding and path following
(reconstructed/path) with the client's own instructions in Unicorn.

The pinned restored text and second image section are executed unchanged.
The path finder object is built by the client's own constructor and
SetMapDimensions; every search runs PathFinding2 0x012b0e85 (FindPath, the
binary-search-tree queue, BuildPath, the target marking) as client code.
MovePath, the angle helpers and MoveCharacterPosition run as client code too.
Only CRT heap/memset services, a log call and subsystem queries outside the
compared routines are replaced; each is listed in CLIENT_STUBS. Results are
compared bit for bit with the C library built from reconstructed/path.

Synthetic inputs (labelled): the 64-byte neighbour table 0x01cf1640, which
lies in the packed third section, is taken from the unpacked data region of
capture x86-linux-capture-04 (same restored text digest) and pinned by
SHA-256; the finder's touched range starts in its reset state and its path
arrays start zeroed (the client allocates them uninitialised); heap memory
returned to the client is filled with a poison byte.
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
FLAG_ADDRESS = 0x0bdd1cc8
FLAG_SHA256 = '67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450'
DIRECTIONS_ADDRESS = 0x01cf1640
DIRECTIONS_SECTION = 0x01ced000
DIRECTIONS_SHA256 = 'a8cc45492d67c784853284cd426fd5c48a994a55d124bd970c1da1e46616f8b5'

ROUTINES = {
    'path_finding2': (0x012b0e85, 0x1c7, '361a18e5813b76746f898f0b073663ca18207d8ae5d603f8e64ee0ac7599705c'),
    'move_path': (0x012b0846, 0x61f, 'dee0f6b9e70f485a900c7c2b6038e9a7dcfb21a38783b831170495fbffca819c'),
    'set_map': (0x012b0e65, 0x20, '96b33b1953b1ebd00f64ef8c742f01ed0543ca73fb42dd4c05a34eca1e9dd6f3'),
    'tree_insert': (0x012b198d, 0x15a, 'c6c5ed3d060b8775886befac8bd4b11f27a8c831fbc9d62a3f3483aa53a85ed7'),
    'finder_helpers': (0x012b1ae7, 0x15e, 'b9b8d3316ad6a48ab3631c489731445b6d5966a8500fd197d5026a782ad92f6f'),
    'find_path': (0x012b1c45, 0x581, '73c083787c9d97439b78c6a105dfe6dca87e5b819eda16817ad576a0555c83dd'),
    'build_path': (0x012b21c6, 0x207, '1cffd1fbfdeb1f6091590bb7cd51867dfeeb4c5b3ec5657fbf8fbac76666854a'),
    'finder_accessors': (0x012b23cd, 0x1b7, '3ff479c09314193787b123c4f0b4808b46650689ad0ce03b3b3ae3446f64db71'),
    'mark_targets': (0x012b2584, 0x29a, '98ed59736e351bff859e0b37d1ac332408f8a8317c23c0682347df1d0b6d8843'),
    'set_map_dimensions': (0x012b281e, 0xe8, 'c7a705ebb2d8a47a3996814c250c99a7c7805d352d35c61432ef78a6820bb804'),
    'finder_ctor': (0x012b1766, 0x131, '50ff1310dda85d31ceb0cc26cca47c08c47d26208507df0b81039765987dc881'),
    'tree_ops': (0x01212a40, 0x749, 'cbb2742b56dfbbfe79796f76dd283f42b0aaf2401d76c0af3652b5057b7b86f2'),
    'angles': (0x012aed9e, 0x553, 'eafaafa3f5d23ffbb61400f38455700d33cdaecdf2d17577cbdffff48df6e72f'),
    'move_character_position': (0x0137b351, 0x33b, '2c1235b690c6d2f7330a5e44cc7fda6ba6d1d2fd4818860bf76c4605ca77b2e8'),
    'move_characters': (0x0137a7ce, 0x17a, '5a1bc60ef62c416991af83b575b05881c5bc671f2d776e0397e23780f0ef13a9'),
    'atan_wrapper': (0x012b2bca, 0x16, '40175dd440c0e8ec1c4d211cdd9a3f010b7503d020c019bbe63e68c8ac995cc1'),
    'atan_float': (0x012b2d60, 0x1f, '7c0f2f64cd7f4d6188b1c26fc78c9642e3a8ea6f55b9d6cc299df0bdd9c21e10'),
    'sqrt_float': (0x00961a07, 0x1f, 'b76d7bde45ba4e3662747aeb55ea46f130798f820e4e50ea50f14b2fb52c1a1d'),
    'sqrt_wrapper': (0x009b0c87, 0x16, '24f03dde13bb98714ebee52905794e677c52999608ba9302a86ac0401b3652a9'),
    'fabs': (0x0184f8ff, 0x28, '13a551406032c0bea590fd9233cbc74cdd2c67640540461d7cc1a471d2277638'),
    'abs': (0x01983135, 0xf, 'd0bb562db7fb121bef551c43293337f7c6b59dc7ececb15358050a324b67e37d'),
    'tile_index': (0x016d34db, 0x1b, '0d1422308044ba115f6abd792d16efda7d30c1b55b539b7d2394281e0325e9ff'),
    'vec3_at': (0x00cfc922, 0x12, 'c50769ecd71f18b8e82733c7646941784b333ad85cf6f39a4654207733682839'),
}

PATH_FINDING2, MOVE_PATH, FINDER_CTOR, SET_MAP_DIMENSIONS = 0x012b0e85, 0x012b0846, 0x012b1855, 0x012b281e
CREATE_ANGLE, ANGLE_DIFFERENCE, TURN_ANGLE = 0x012aed9e, 0x012af218, 0x012aefff
HEURISTIC, STEP_COST = 0x012b1bcf, 0x012b1b67
MOVE_CHARACTER_POSITION, MOVE_CHARACTERS = 0x0137b351, 0x0137a7ce
CLEAR_LOOP_END = 0x0137a814
FINDER_GLOBAL = 0x06fce374
TERRAIN_WALL = 0x0b795420
OBJECT_FLAGS = 0x0b7b5420
WORLD_GLOBAL = 0x01cf15fc
CRT_MATH_MODE = 0x0bdcfbc8
SKILL_CHARACTER_INDEX = 0x01cf1168
INFINITE = 0x743aa380

STACK, STACK_SIZE = 0x30000000, 0x400000
RETURN = 0x31000000
ARENA, ARENA_SIZE = 0x32000000, 0x4000000
STUBS = 0x37000000
TEB, GDT = 0x38000000, 0x38100000
BSS = ((0x01ced000, 0x00200000), (0x06f00000, 0x00100000), (0x0a300000, 0x01b00000))
INITIAL_ESP = STACK + STACK_SIZE - 0x1000
FPCW, MXCSR = 0x027f, 0x1f80
POISON = 0xcd

# Client callees replaced by recorded stubs: (argument bytes the callee pops, kind, reason).
CLIENT_STUBS = {
    0x01983110: (0, 'eax', 'CRT malloc (operator new 0x0191ba7b): harness arena, poison-filled'),
    0x0191c490: (0, 'eax', 'CRT free (operator delete): no-op'),
    0x0194cd00: (0, 'eax', 'CRT memset: performed by the harness'),
    0x01206598: (0, 'eax', 'log writer (out-of-range target index): recorded'),
    0x00db732d: (0, 'eax', 'PathFinding2 siege-skill predicate 1 (subsystem query)'),
    0x00dabe97: (0, 'eax', 'PathFinding2 siege-skill predicate 2 (subsystem query)'),
    0x0095f6db: (0, 'eax', 'character table lookup (subsystem query)'),
    0x009a13f4: (0, 'eax', 'character object getter (subsystem query)'),
    0x013957b5: (0, 'fld', 'CharacterMoveSpeed (equipment/buff state): synthetic speed'),
    0x016cc9e2: (0, 'fld', 'RequestTerrainHeight: synthetic height'),
    0x0129dcda: (0, 'eax', 'helper item getter (subsystem query)'),
    0x0095fb27: (0, 'eax', 'character predicate (subsystem query)'),
}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def same(a, b):
    if math.isnan(a) and math.isnan(b):
        return True
    return fbits(a) == fbits(b)


def load_pinned(path, size, digest, label, offset=0):
    with open(path, 'rb') as handle:
        handle.seek(offset)
        payload = handle.read(size)
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input does not match pinned {label}: {path}')
    return payload


class Stop(Exception):
    pass


class Guest:
    def __init__(self, text, data, flag, directions):
        import unicorn
        from unicorn import x86_const
        self.u, self.x = unicorn, x86_const
        for name, (start, size, digest) in ROUTINES.items():
            if hashlib.sha256(text[start - TEXT_BASE:start - TEXT_BASE + size]).hexdigest() != digest:
                raise ValueError(f'routine bytes differ from the pinned digest: {name}')
        uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
        self.uc = uc
        uc.mem_map(TEXT_BASE, (TEXT_BYTES + 0xfff) & ~0xfff, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES + 0xfff) & ~0xfff, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
        uc.mem_write(DATA_BASE, data)
        for base, size in BSS + ((STACK, STACK_SIZE), (ARENA, ARENA_SIZE), (TEB, 0x1000)):
            uc.mem_map(base, size, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
        uc.mem_map(RETURN, 0x1000, unicorn.UC_PROT_ALL)
        uc.mem_map(STUBS, 0x10000, unicorn.UC_PROT_ALL)
        uc.mem_map(GDT, 0x1000, unicorn.UC_PROT_READ)
        teb = struct.pack('<HHBBBB', 0xfff, TEB & 0xffff, (TEB >> 16) & 0xff, 0x92, 0x40, (TEB >> 24) & 0xff)
        flat = struct.pack('<HHBBBB', 0xffff, 0, 0, 0x92, 0xcf, 0)
        uc.mem_write(GDT, bytes(8) + teb + flat)
        uc.reg_write(x86_const.UC_X86_REG_GDTR, (0, GDT, 23, 0))
        uc.reg_write(x86_const.UC_X86_REG_FS, 1 << 3)
        for register in (x86_const.UC_X86_REG_SS, x86_const.UC_X86_REG_DS, x86_const.UC_X86_REG_ES):
            uc.reg_write(register, 2 << 3)
        uc.mem_write(TEB, struct.pack('<I', 0xffffffff))
        uc.mem_write(FLAG_ADDRESS, flag)
        uc.mem_write(DIRECTIONS_ADDRESS, directions)
        uc.mem_write(CRT_MATH_MODE, struct.pack('<I', 1))
        uc.hook_add(unicorn.UC_HOOK_MEM_UNMAPPED, self._unmapped)
        self.violation = None
        self.calls = []
        self.values = {}
        self.arena_top = ARENA
        self.stubs = {}
        for index, (address, (cleanup, kind, reason)) in enumerate(sorted(CLIENT_STUBS.items())):
            snippet = STUBS + 0x20 * index
            slot = snippet + 0x18
            load = b'\xa1' if kind == 'eax' else b'\xd9\x05'
            tail = b'\xc3' if cleanup == 0 else b'\xc2' + struct.pack('<H', cleanup)
            uc.mem_write(snippet, load + struct.pack('<I', slot) + tail)
            self.stubs[address] = (snippet, slot, kind)
            uc.hook_add(unicorn.UC_HOOK_CODE, self._stub, begin=address, end=address)
        self.handlers = {
            0x01983110: self._malloc,
            0x0191c490: lambda args, ecx: 0,
            0x0194cd00: self._memset,
            0x01206598: lambda args, ecx: 0,
        }

    def _unmapped(self, uc, access, address, size, value, ignored):
        if self.violation is None:
            self.violation = ('unmapped', hex(address), size, hex(uc.reg_read(self.x.UC_X86_REG_EIP)))
        return False

    def _args(self, count):
        esp = self.uc.reg_read(self.x.UC_X86_REG_ESP)
        return struct.unpack(f'<{count + 1}I', bytes(self.uc.mem_read(esp, 4 + 4 * count)))

    def _stub(self, uc, address, size, ignored):
        if address not in self.stubs:
            return
        snippet, slot, kind = self.stubs[address]
        words = self._args(4)
        handler = self.handlers.get(address)
        ecx = uc.reg_read(self.x.UC_X86_REG_ECX)
        value = handler(words[1:], ecx) if handler else self.values.get(address, 0)
        self.calls.append((address, words[1:]))
        uc.mem_write(slot, struct.pack('<I', value & 0xffffffff) if kind == 'eax' else struct.pack('<f', value))
        uc.reg_write(self.x.UC_X86_REG_EIP, snippet)

    def _malloc(self, args, ecx):
        size = max(args[0], 1)
        address = (self.arena_top + 15) & ~15
        if address + size > ARENA + ARENA_SIZE:
            raise Stop('arena exhausted')
        self.arena_top = address + size
        self.uc.mem_write(address, bytes([POISON]) * size)
        return address

    def _memset(self, args, ecx):
        destination, value, count = args[0], args[1] & 0xff, args[2]
        self.uc.mem_write(destination, bytes([value]) * count)
        return destination

    def reset_arena(self):
        self.arena_top = ARENA

    def alloc(self, size, fill=0):
        address = self._malloc((size,), 0)
        self.put(address, bytes([fill]) * size)
        return address

    def put(self, address, payload):
        self.uc.mem_write(address, bytes(payload))

    def get(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def u32(self, address):
        return struct.unpack('<I', self.get(address, 4))[0]

    def i32(self, address):
        return struct.unpack('<i', self.get(address, 4))[0]

    def f32at(self, address):
        return struct.unpack('<f', self.get(address, 4))[0]

    def call(self, start, words, ecx=0, until=RETURN, count=400_000_000):
        uc, x = self.uc, self.x
        self.violation = None
        self.calls = []
        frame = struct.pack('<I', RETURN) + b''.join(struct.pack('<I', w & 0xffffffff) for w in words)
        esp = INITIAL_ESP - 0x100
        self.put(esp, frame)
        uc.reg_write(x.UC_X86_REG_ESP, esp)
        uc.reg_write(x.UC_X86_REG_EBP, 0x5a5a5a5a)
        uc.reg_write(x.UC_X86_REG_ECX, ecx)
        for reg in (x.UC_X86_REG_EAX, x.UC_X86_REG_EDX, x.UC_X86_REG_EBX, x.UC_X86_REG_ESI, x.UC_X86_REG_EDI):
            uc.reg_write(reg, 0xdeadbeef)
        uc.reg_write(x.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x.UC_X86_REG_FPSW, 0)
        uc.reg_write(x.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, until, count=count)
        except self.u.UcError as failure:
            error = str(failure)
        eip = uc.reg_read(x.UC_X86_REG_EIP)
        if self.violation or error or eip != until:
            raise Stop(f'{hex(start)}: {self.violation or error or "stopped at " + hex(eip)}')
        return uc.reg_read(x.UC_X86_REG_EAX)

    def st0_float(self):
        """x87 st(0) of a float-returning routine, as binary32 (the callers
        store it with fstp dword)."""
        top = (self.uc.reg_read(self.x.UC_X86_REG_FPSW) >> 11) & 7
        mantissa, high = self.uc.reg_read(self.x.UC_X86_REG_FP0 + top)
        sign = -1.0 if high & 0x8000 else 1.0
        exponent = high & 0x7fff
        if exponent == 0x7fff:
            return math.copysign(math.inf, sign) if mantissa == 1 << 63 else math.nan
        if mantissa == 0:
            return math.copysign(0.0, sign)
        return f32(sign * math.ldexp(mantissa, exponent - 16383 - 63))


# ---------------- C library ----------------

class QueueEntry(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('cost', ctypes.c_int32), ('sequence', ctypes.c_uint32)]


class Finder(ctypes.Structure):
    _fields_ = [('width', ctypes.c_int32), ('height', ctypes.c_int32), ('size', ctypes.c_int32),
                ('wall', ctypes.POINTER(ctypes.c_uint16)), ('object_flags', ctypes.POINTER(ctypes.c_uint32)),
                ('count', ctypes.c_int32), ('path_x', ctypes.c_uint8 * 500), ('path_y', ctypes.c_uint8 * 500),
                ('end_x', ctypes.c_int16), ('end_y', ctypes.c_int16), ('mark', ctypes.POINTER(ctypes.c_uint8)),
                ('touched_min', ctypes.c_int32), ('touched_max', ctypes.c_int32),
                ('cost', ctypes.POINTER(ctypes.c_int32)), ('parent_x', ctypes.POINTER(ctypes.c_int32)),
                ('parent_y', ctypes.POINTER(ctypes.c_int32)), ('queue', ctypes.POINTER(QueueEntry)),
                ('queue_count', ctypes.c_int32), ('queue_capacity', ctypes.c_int32),
                ('queue_sequence', ctypes.c_uint32), ('pops', ctypes.c_int32), ('pushes', ctypes.c_int32),
                ('index_errors', ctypes.c_int32)]


class ClientPath(ctypes.Structure):
    _fields_ = [('current', ctypes.c_uint8), ('current_float', ctypes.c_uint8), ('count', ctypes.c_uint8),
                ('x', ctypes.c_uint8 * 15), ('y', ctypes.c_uint8 * 15)]


class Mover(ctypes.Structure):
    _fields_ = [('tile_x', ctypes.c_int32), ('tile_y', ctypes.c_int32), ('position', ctypes.c_float * 3),
                ('angle', ctypes.c_float * 3), ('path', ClientPath)]


def load_library(directory=None):
    directory = Path(directory) if directory else ROOT / 'reconstructed' / 'path'
    subprocess.run(['make', '-C', str(directory)], check=True, capture_output=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(directory / f'libclient_path.{suffix}'))
    P = ctypes.POINTER
    lib.mu_path_finder_init.argtypes = [P(Finder), ctypes.c_int32, ctypes.c_int32, P(ctypes.c_uint16),
                                        P(ctypes.c_uint32)]
    lib.mu_path_finder_free.argtypes = [P(Finder)]
    lib.mu_path_find.argtypes = [P(Finder)] + [ctypes.c_int32] * 4 + [ctypes.c_int, ctypes.c_int32, ctypes.c_int,
                                                                      ctypes.c_float, ctypes.c_int32, ctypes.c_int32]
    lib.mu_path_finding2.argtypes = [P(Finder)] + [ctypes.c_int32] * 4 + [P(ClientPath), ctypes.c_float,
                                                                          ctypes.c_int32, ctypes.c_int]
    lib.mu_path_heuristic.argtypes = [ctypes.c_int32] * 4
    lib.mu_path_step_cost.argtypes = [ctypes.c_int32] * 2
    for name in ('mu_path_create_angle',):
        getattr(lib, name).argtypes = [ctypes.c_float] * 4
        getattr(lib, name).restype = ctypes.c_float
    lib.mu_path_angle_difference.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int]
    lib.mu_path_angle_difference.restype = ctypes.c_float
    lib.mu_path_turn_angle.argtypes = [ctypes.c_float] * 3
    lib.mu_path_turn_angle.restype = ctypes.c_float
    lib.mu_path_move.argtypes = [P(Mover), ctypes.c_int, P(ctypes.c_float)]
    lib.mu_path_step_position.argtypes = [P(ctypes.c_float), P(ctypes.c_float), ctypes.c_float]
    lib.mu_path_clear_characters.argtypes = [P(ctypes.c_uint16), ctypes.c_int32]
    lib.mu_path_stamp_character.argtypes = [P(ctypes.c_uint16), ctypes.c_int32, ctypes.c_int32]
    return lib


class Tally:
    def __init__(self):
        self.results = {}

    def add(self, family, ok, detail=None):
        entry = self.results.setdefault(family, {'cases': 0, 'mismatches': 0, 'first': None})
        entry['cases'] += 1
        if not ok:
            entry['mismatches'] += 1
            if entry['first'] is None:
                entry['first'] = detail


# ---------------- grids ----------------

WALL_VALUES = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x0c, 0x14, 0x21, 0x22, 0x24, 0x100, 0x1000, 0x05]


def grid_noise(rng, density, values=None):
    values = values or WALL_VALUES
    grid = [0] * 65536
    for i in range(65536):
        if rng.random() < density:
            grid[i] = rng.choice(values)
    return grid


def grid_rooms(rng):
    grid = [0] * 65536
    for _ in range(rng.randrange(40, 160)):
        x0, y0 = rng.randrange(0, 250), rng.randrange(0, 250)
        w, h = rng.randrange(1, 30), rng.randrange(1, 30)
        value = rng.choice([0x04, 0x08, 0x10, 0x0c, 0x04])
        hollow = rng.random() < 0.5
        for y in range(y0, min(256, y0 + h)):
            for x in range(x0, min(256, x0 + w)):
                if not hollow or x in (x0, x0 + w - 1) or y in (y0, y0 + h - 1):
                    grid[y * 256 + x] = value
        if hollow and w > 2 and h > 2 and rng.random() < 0.6:   # a door
            grid[y0 * 256 + x0 + w // 2] = 0
    for _ in range(rng.randrange(0, 400)):
        grid[rng.randrange(65536)] |= rng.choice([0x01, 0x02, 0x20])
    return grid


def grid_maze(rng):
    grid = [0x04] * 65536
    cells = 64
    seen = set()
    stack = [(rng.randrange(cells), rng.randrange(cells))]
    while stack:
        cx, cy = stack[-1]
        seen.add((cx, cy))
        grid[(cy * 4 + 1) * 256 + cx * 4 + 1] = 0
        grid[(cy * 4 + 1) * 256 + cx * 4 + 2] = 0
        grid[(cy * 4 + 2) * 256 + cx * 4 + 1] = 0
        grid[(cy * 4 + 2) * 256 + cx * 4 + 2] = 0
        options = [(cx + dx, cy + dy, dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if 0 <= cx + dx < cells and 0 <= cy + dy < cells and (cx + dx, cy + dy) not in seen]
        if not options:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(options)
        for k in range(1, 4):
            for o in (1, 2):
                if dx:
                    grid[(cy * 4 + o) * 256 + cx * 4 + (2 if dx > 0 else 1) + dx * k] = 0
                else:
                    grid[(cy * 4 + (2 if dy > 0 else 1) + dy * k) * 256 + cx * 4 + o] = 0
        stack.append((nx, ny))
    return grid


class World:
    """One TerrainWall/object-flag state, mirrored in the guest and in C."""

    def __init__(self, guest, lib, grid, objects=None):
        self.guest, self.lib = guest, lib
        self.wall = (ctypes.c_uint16 * 65536)(*grid)
        self.objects = (ctypes.c_uint32 * 65536)(*(objects or [0] * 65536))
        guest.put(TERRAIN_WALL, bytes(self.wall))
        guest.put(OBJECT_FLAGS, bytes(self.objects))
        # client finder object: operator new + ctor + SetMapDimensions(256, 256, TerrainWall)
        guest.reset_arena()
        self.object = guest.alloc(0x428, POISON)
        guest.call(FINDER_CTOR, [], ecx=self.object)
        guest.call(SET_MAP_DIMENSIONS, [256, 256, TERRAIN_WALL], ecx=self.object)
        guest.put(self.object + 0x10, bytes(0x3fc - 0x10))   # count + path arrays: zero (harness)
        guest.put(self.object + 0x404, struct.pack('<Ii', INFINITE, -1))   # reset state (harness)
        guest.put(FINDER_GLOBAL, struct.pack('<I', self.object))
        self.c = Finder()
        if lib.mu_path_finder_init(ctypes.byref(self.c), 256, 256, self.wall, self.objects):
            raise MemoryError
        self.out = guest.alloc(0x40)

    def close(self):
        self.lib.mu_path_finder_free(ctypes.byref(self.c))

    def set_wall(self, index, value):
        self.wall[index] = value
        self.guest.put(TERRAIN_WALL + 2 * index, struct.pack('<H', value))

    def search(self, sx, sy, tx, ty, distance, wall_level, siege=False):
        g, o = self.guest, self.object
        filler = bytes([0x5a] * 0x21)
        g.put(self.out, filler)
        g.values[0x00db732d] = 1 if siege else 0
        g.values[0x00dabe97] = 1
        g.values[0x0095f6db] = 0
        character = g.alloc(0x3300)
        g.put(character + 0x32b0, struct.pack('<I', 0xa3b))
        g.values[0x009a13f4] = character
        g.put(SKILL_CHARACTER_INDEX, struct.pack('<I', 7))
        result = g.call(PATH_FINDING2, [sx, sy, tx, ty, self.out, fbits(distance), wall_level]) & 0xff
        guest_state = {
            'result': result,
            'path': g.get(self.out, 0x21),
            'count': g.i32(o + 0x10),
            'path_x': g.get(o + 0x14, 500), 'path_y': g.get(o + 0x208, 500),
            'end': struct.unpack('<hh', g.get(o + 0x3fc, 4)),
            'touched': struct.unpack('<ii', g.get(o + 0x404, 8)),
            'tree': struct.unpack('<II', g.get(o + 0x418 + 4, 8)),
            'wall': g.get(TERRAIN_WALL, 0x20000),
        }
        mark = g.get(g.u32(o + 0x400), 65536)
        cost = struct.unpack('<65536i', g.get(g.u32(o + 0x40c), 0x40000))
        px = struct.unpack('<65536i', g.get(g.u32(o + 0x410), 0x40000))
        py = struct.unpack('<65536i', g.get(g.u32(o + 0x414), 0x40000))
        path = ClientPath()
        ctypes.memmove(ctypes.byref(path), filler, 0x21)
        c = self.c
        want = self.lib.mu_path_finding2(ctypes.byref(c), sx, sy, tx, ty, ctypes.byref(path), distance, wall_level,
                                         1 if siege else 0)
        c_mark = ctypes.string_at(c.mark, 65536)
        c_state = {
            'result': want & 0xff,
            'path': bytes(path),
            'count': c.count,
            'path_x': bytes(c.path_x), 'path_y': bytes(c.path_y),
            'end': (c.end_x, c.end_y),
            'touched': (c.touched_min, c.touched_max),
            'tree': (0, 0),
            'wall': bytes(self.wall),
        }
        diff = {k: 'differs' for k in guest_state if guest_state[k] != c_state[k]}
        if mark != c_mark:
            diff['mark'] = 'differs'
        start = (sy * 256 + sx) if 0 <= sx < 256 and 0 <= sy < 256 else -1
        for i in range(65536):
            m = mark[i]
            if m & 2 and cost[i] != c.cost[i]:
                diff['cost'] = (i, cost[i], c.cost[i])
                break
            if m & 1 and i != start and (px[i] != c.parent_x[i] or py[i] != c.parent_y[i]):
                diff['parent'] = (i, (px[i], py[i]), (c.parent_x[i], c.parent_y[i]))
                break
        stats = {'nodes': path.count if want else 0, 'pops': c.pops, 'closed': sum(1 for m in mark if m & 2)}
        return diff, guest_state, c_state, stats


def walkable(grid, x, y, level=2):
    return 0 <= x < 256 and 0 <= y < 256 and (grid[y * 256 + x] & 0x1e) < level


# distances equal to sqrt(k*k + i*i) for some outer-ring offset (the > test)
EXACT_DISTANCES = [5.0, f32(math.sqrt(5)), f32(math.sqrt(8)), f32(math.sqrt(13)), 3.0, 0.5]


def grid_safezone(rng):
    """Whole map safe zone with dense character tiles: level 2 often fails
    where PathFinding2's level-4 retry passes."""
    density = rng.choice([0.2, 0.35, 0.5])
    grid = [0x01] * 65536
    for i in range(65536):
        r = rng.random()
        if r < density:
            grid[i] = 0x03
        elif r < density + 0.03:
            grid[i] = 0x05
    return grid


def pick_search(rng, grid):
    for _ in range(200):
        sx, sy = rng.randrange(1, 255), rng.randrange(1, 255)
        if walkable(grid, sx, sy) or rng.random() < 0.05:
            break
    span = rng.choice([2, 4, 8, 15, 25, 40])
    tx = min(255, max(0, sx + rng.randint(-span, span)))
    ty = min(255, max(0, sy + rng.randint(-span, span)))
    if rng.random() < 0.03:
        sx = 0 if rng.random() < 0.5 else sx
        sy = 0 if sx else sy
    if rng.random() < 0.03:
        tx, ty = sx, sy
    distance = rng.choice([0.0] * 6 + [1.0, 1.0, 1.5, 2.0, 2.9, 4.0] + EXACT_DISTANCES)
    level = rng.choice([2] * 6 + [4, 4, 1, 8, 0x20, 3])
    siege = rng.random() < 0.08
    return sx, sy, tx, ty, distance, level, siege


def run_search_family(guest, lib, tally, rng, count, family='PathFinding2 synthetic', grids=None, stats=None):
    makers = grids or [lambda r: grid_noise(r, 0.0), lambda r: grid_noise(r, 0.1), lambda r: grid_noise(r, 0.25),
                       lambda r: grid_noise(r, 0.4), grid_rooms, grid_maze, grid_safezone]
    done = 0
    while done < count:
        maker = makers[done % len(makers)] if isinstance(makers, list) else makers
        grid = maker(rng)
        objects = None
        if rng.random() < 0.3:
            objects = [1 if rng.random() < 0.03 else 0 for _ in range(65536)]
        world = World(guest, lib, grid, objects)
        try:
            for _ in range(min(12, count - done)):
                sx, sy, tx, ty, distance, level, siege = pick_search(rng, grid)
                if rng.random() < 0.3:   # a character tile appears or leaves between searches
                    index = rng.randrange(65536)
                    world.set_wall(index, world.wall[index] ^ 0x02)
                try:
                    diff, got, want, st = world.search(sx, sy, tx, ty, distance, level, siege)
                except Stop as stop:
                    tally.add(family, False, {'stop': str(stop), 'case': (sx, sy, tx, ty, distance, level, siege)})
                    done += 1
                    continue
                if stats is not None:
                    stats.append(st)
                tally.add(family, not diff, {'diff': diff, 'case': (sx, sy, tx, ty, distance, level, siege),
                                             'got': got['result'], 'want': want['result']})
                done += 1
        finally:
            world.close()


def installed_grid(tool, root, world):
    out = subprocess.run([str(tool), 'att', root, '--world', str(world), '--out', '-'], capture_output=True)
    if out.returncode != 0 or len(out.stdout) != 0x20000:
        return None
    return list(struct.unpack('<65536H', out.stdout))


def run_installed_family(guest, lib, tally, rng, count, root, tool, worlds, stats=None):
    per = max(1, count // max(1, len(worlds)))
    loaded, seen = [], set()
    for world_index in worlds:
        grid = installed_grid(tool, root, world_index)
        if grid is None:
            continue
        digest = hashlib.sha256(struct.pack('<65536H', *grid)).hexdigest()
        if digest in seen:   # event worlds sharing a folder
            continue
        seen.add(digest)
        free = [i for i in range(65536) if (grid[i] & 0x1e) < 2 and 0 < i % 256 and i >= 256]
        if not free:
            continue
        loaded.append(world_index)
        world = World(guest, lib, grid)
        try:
            for _ in range(per):
                s = rng.choice(free)
                sx, sy = s % 256, s // 256
                span = rng.choice([3, 8, 15, 25, 40])
                if rng.random() < 0.7:
                    near = [rng.choice(free) for _ in range(40)]
                    near = [i for i in near if abs(i % 256 - sx) <= span and abs(i // 256 - sy) <= span] or [s]
                    t = rng.choice(near)
                    tx, ty = t % 256, t // 256
                else:   # anywhere nearby, walls included (unreachable targets)
                    tx = min(255, max(0, sx + rng.randint(-span, span)))
                    ty = min(255, max(0, sy + rng.randint(-span, span)))
                distance = rng.choice([0.0, 0.0, 0.0, 1.0])
                try:
                    diff, got, want, st = world.search(sx, sy, tx, ty, distance, 2)
                except Stop as stop:
                    tally.add(f'PathFinding2 installed', False, {'stop': str(stop), 'world': world_index})
                    continue
                if stats is not None:
                    stats.append(st)
                tally.add('PathFinding2 installed', not diff,
                          {'diff': diff, 'world': world_index, 'case': (sx, sy, tx, ty, distance)})
                path = got['path']
                if got['result'] and rng.random() < 0.35:
                    n = path[2]
                    xs, ys = list(path[3:3 + n]), list(path[0x12:0x12 + n])
                    walker = guest.alloc(CHAR_SIZE)
                    ok, detail, steps = compare_walk(guest, lib, walker, xs, ys, random_angle(rng),
                                                     rng.choice(SPEEDS))
                    tally.add('walk on installed paths', ok, detail)
        finally:
            world.close()
    tally.results.setdefault('PathFinding2 installed', {'cases': 0, 'mismatches': 0, 'first': None})['worlds'] = loaded


# ---------------- following ----------------

CHAR_SIZE = 0x3600
OBJ = 0x3254


def random_path(rng, count=None):
    count = count or rng.randint(1, 15)
    x, y = rng.randrange(20, 236), rng.randrange(20, 236)
    xs, ys = [x], [y]
    for _ in range(count - 1):
        dx, dy = rng.choice([(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)])
        x, y = x + dx, y + dy
        xs.append(x)
        ys.append(y)
    return xs, ys


def write_mover(guest, address, m):
    guest.put(address + 0x180, struct.pack('<ii', m.tile_x, m.tile_y))
    guest.put(address + 0x3194, bytes(m.path))
    guest.put(address + OBJ + 0x158, struct.pack('<3f', *m.position))
    guest.put(address + OBJ + 0x164, struct.pack('<3f', *m.angle))


def read_mover(guest, address):
    return {'tile': struct.unpack('<ii', guest.get(address + 0x180, 8)),
            'path': guest.get(address + 0x3194, 0x21),
            'position': struct.unpack('<3f', guest.get(address + OBJ + 0x158, 12)),
            'angle': struct.unpack('<3f', guest.get(address + OBJ + 0x164, 12))}


def c_mover_state(m):
    return {'tile': (m.tile_x, m.tile_y), 'path': bytes(m.path), 'position': tuple(m.position),
            'angle': tuple(m.angle)}


def states_equal(a, b):
    for key in a:
        x, y = a[key], b[key]
        if isinstance(x, tuple) and x and isinstance(x[0], float):
            if not all(same(p, q) for p, q in zip(x, y)):
                return False
        elif x != y:
            return False
    return True


def random_angle(rng):
    r = rng.random()
    if r < 0.1:
        return rng.choice([0.0, 45.0, 90.0, 180.0, 270.0, 360.0, -0.0, -45.0, -180.0, 359.99997, 180.00002, 179.99998])
    if r < 0.2:
        return f32(rng.uniform(-360.0, 720.0))
    return f32(rng.uniform(0.0, 360.0))


def run_move_family(guest, lib, tally, rng, count):
    guest.reset_arena()
    address = guest.alloc(CHAR_SIZE)
    for _ in range(count):
        xs, ys = random_path(rng)
        m = Mover()
        m.path.count = len(xs)
        for i, (x, y) in enumerate(zip(xs, ys)):
            m.path.x[i], m.path.y[i] = x, y
        if rng.random() < 0.05:
            m.path.count = rng.choice([0, len(xs) + rng.randint(0, 3)])
        m.path.current = rng.randrange(0, max(1, m.path.count + (1 if rng.random() < 0.1 else 0)))
        m.path.current_float = rng.choice([0, 0, 1, 2, 3, 4 if rng.random() < 0.05 else 0])
        m.tile_x, m.tile_y = rng.randrange(256), rng.randrange(256)
        i = min(m.path.current, max(0, len(xs) - 1))
        cx, cy = (xs[i] + 0.5) * 100, (ys[i] + 0.5) * 100
        spread = rng.choice([5.0, 25.0, 31.0, 60.0, 150.0])
        m.position[0] = f32(cx + rng.uniform(-spread, spread))
        m.position[1] = f32(cy + rng.uniform(-spread, spread))
        m.position[2] = f32(rng.uniform(0, 500))
        m.angle[0], m.angle[1], m.angle[2] = 0.0, 0.0, random_angle(rng)
        turn = rng.choice([0, 1, 1, 1])
        if rng.random() < 0.25:   # straight path along x or y, position on the line: exact axis angles
            along_x = rng.random() < 0.5
            n = rng.randint(2, 15)
            x0, y0 = rng.randrange(20, 220), rng.randrange(20, 220)
            step = rng.choice([1, -1])
            m.path.count = n
            for i in range(n):
                m.path.x[i] = x0 + (i * step if along_x else 0)
                m.path.y[i] = y0 + (0 if along_x else i * step)
            m.path.current = rng.randrange(0, n)
            m.path.current_float = rng.choice([0, 1, 2, 3])
            i = m.path.current
            if along_x:
                m.position[0] = f32((m.path.x[i] + 0.5) * 100 + rng.uniform(-80, 80))
                m.position[1] = f32((y0 + 0.5) * 100)
            else:
                m.position[0] = f32((x0 + 0.5) * 100)
                m.position[1] = f32((m.path.y[i] + 0.5) * 100 + rng.uniform(-80, 80))
            m.angle[2] = rng.choice([0.0, 45.0, 135.0, 225.0, 315.0, 90.0, 270.0, 180.0, 44.99999, 45.00001])
            turn = 1
        write_mover(guest, address, m)
        try:
            result = guest.call(MOVE_PATH, [address, turn]) & 0xff
        except Stop as stop:
            tally.add('MovePath', False, {'stop': str(stop)})
            continue
        got = read_mover(guest, address)
        want_result = lib.mu_path_move(ctypes.byref(m), turn, None)
        want = c_mover_state(m)
        ok = result == (want_result & 0xff) and states_equal(got, want)
        tally.add('MovePath', ok, {'got': got, 'want': want, 'result': (result, want_result)})


def compare_walk(guest, lib, address, xs, ys, angle, speed):
    """MovePath (turning) then MoveCharacterPosition per 40 ms step from the
    first node to the arrival, compared after every step."""
    m = Mover()
    m.path.count = len(xs)
    for i, (x, y) in enumerate(zip(xs, ys)):
        m.path.x[i], m.path.y[i] = x, y
    m.tile_x, m.tile_y = xs[0], ys[0]
    m.position[0], m.position[1] = f32((xs[0] + 0.5) * 100), f32((ys[0] + 0.5) * 100)
    m.position[2] = 0.0
    m.angle[2] = angle
    guest.values[0x013957b5] = speed
    guest.values[0x016cc9e2] = 0.0
    guest.put(WORLD_GLOBAL, struct.pack('<i', -1))
    guest.put(address + OBJ + 0x5c, struct.pack('<I', 0xa91))
    write_mover(guest, address, m)
    for step in range(400):
        try:
            result = guest.call(MOVE_PATH, [address, 1]) & 0xff
            if not result:
                guest.call(MOVE_CHARACTER_POSITION, [address])
        except Stop as stop:
            return False, {'stop': str(stop), 'step': step}, step
        want_result = lib.mu_path_move(ctypes.byref(m), 1, None)
        if not want_result:
            lib.mu_path_step_position(m.position, m.angle, speed)
            m.position[2] = 0.0
        got, want = read_mover(guest, address), c_mover_state(m)
        if result != (want_result & 0xff) or not states_equal(got, want):
            return False, {'step': step, 'got': got, 'want': want, 'speed': speed}, step + 1
        if result:
            return True, None, step + 1
    return True, {'note': 'no arrival in 400 steps'}, 400


SPEEDS = [12.0, 15.0, 8.0, 16.0, 17.0, 19.0, 20.0, 7.5, 4.95]


def run_walk_family(guest, lib, tally, rng, count):
    guest.reset_arena()
    address = guest.alloc(CHAR_SIZE)
    for _ in range(count):
        xs, ys = random_path(rng, rng.randint(2, 15))
        ok, detail, steps = compare_walk(guest, lib, address, xs, ys, random_angle(rng), rng.choice(SPEEDS))
        tally.add('walk (MovePath + MoveCharacterPosition)', ok, detail)


def run_angle_family(guest, lib, tally, rng, count):
    specials = [0.0, -0.0, 0.00005, -0.00005, 0.0001, -0.0001, 0.00011, math.inf, -math.inf, math.nan, 1e30, -1e30]
    for _ in range(count):
        if rng.random() < 0.15:
            x1, y1 = rng.choice(specials), rng.choice(specials)
            x2, y2 = rng.choice(specials), rng.choice(specials)
        else:
            x1, y1 = f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600))
            x2, y2 = f32(x1 + rng.uniform(-300, 300)), f32(y1 + rng.uniform(-300, 300))
            if rng.random() < 0.15:
                x2 = x1
            if rng.random() < 0.15:
                y2 = y1
        guest.call(CREATE_ANGLE, [fbits(x1), fbits(y1), fbits(x2), fbits(y2)])
        got = guest.st0_float()
        want = lib.mu_path_create_angle(x1, y1, x2, y2)
        tally.add('CreateAngle 0x012aed9e', same(got, want), {'in': (x1, y1, x2, y2), 'got': got, 'want': want})
        a, b = random_angle(rng), random_angle(rng)
        if rng.random() < 0.05:
            a = rng.choice([math.nan, math.inf, -math.inf])
        flag = rng.choice([0, 1, 1, 2])
        guest.call(ANGLE_DIFFERENCE, [fbits(a), fbits(b), flag])
        got = guest.st0_float()
        want = lib.mu_path_angle_difference(a, b, flag)
        tally.add('angle difference 0x012af218', same(got, want), {'in': (a, b, flag), 'got': got, 'want': want})
        step = f32(rng.choice([rng.uniform(0, 22.5), rng.uniform(0, 200), 0.0, 22.5, 90.0]))
        if rng.random() < 0.3:   # boundary equalities of the TurnAngle branches
            a = f32(rng.choice([rng.uniform(0, 180), rng.uniform(180, 360), 0.0, 90.0, 180.0, 270.0]))
            step = f32(rng.choice([a, f32(360.0 - a), rng.uniform(0, 45), f32(a - 180.0) if a >= 180 else a]))
            b = rng.choice([f32(a + step), f32(a + 180.0), f32(a - step), f32(a - 180.0), f32(f32(a + step) - 360.0),
                            f32(f32(a - step) + 360.0), f32(f32(a + step) - 360.0), rng.uniform(0, 360)])
            b = f32(b)
        guest.call(TURN_ANGLE, [fbits(a), fbits(b), fbits(step)])
        got = guest.st0_float()
        want = lib.mu_path_turn_angle(a, b, step)
        tally.add('TurnAngle 0x012aefff', same(got, want), {'in': (a, b, step), 'got': got, 'want': want})
        tx, ty, x, y = (rng.randint(-300, 600) for _ in range(4))
        got = guest.call(HEURISTIC, [tx, ty, x, y], ecx=ARENA)
        tally.add('heuristic 0x012b1bcf', got == (lib.mu_path_heuristic(tx, ty, x, y) & 0xffffffff), (tx, ty, x, y))
        dx, dy = rng.randint(-1, 1), rng.randint(-1, 1)
        got = guest.call(STEP_COST, [dx, dy], ecx=ARENA)
        tally.add('step cost 0x012b1b67', got == lib.mu_path_step_cost(dx, dy), (dx, dy))


def run_occupancy_family(guest, lib, tally, rng, count):
    for _ in range(count):
        grid = grid_noise(rng, rng.choice([0.05, 0.3, 0.9]),
                          [0x02, 0x03, 0x06, 0x22, 0x01, 0x04, 0xffff, 0xfffe, 0x8002])
        guest.put(TERRAIN_WALL, struct.pack('<65536H', *grid))
        try:
            guest.call(MOVE_CHARACTERS, [], until=CLEAR_LOOP_END)
        except Stop as stop:
            tally.add('occupancy clear 0x0137a7ce', False, {'stop': str(stop)})
            continue
        got = guest.get(TERRAIN_WALL, 0x20000)
        wall = (ctypes.c_uint16 * 65536)(*grid)
        lib.mu_path_clear_characters(wall, 65536)
        tally.add('occupancy clear 0x0137a7ce', got == bytes(wall), None)


# Plausible reconstruction mistakes; each must be detected (mutation check).
MUTATIONS = [
    ('queue ties popped last-in first-out', 'client_path.c',
     '(a->cost == b->cost && a->sequence < b->sequence)', '(a->cost == b->cost && a->sequence > b->sequence)',
     'search'),
    ('diagonal step cost 5', 'client_path.c', 'return dx != 0 && dy != 0 ? 7 : 5;', 'return dx != 0 && dy != 0 ? 5 : 5;', 'search'),
    ('heuristic without +1', 'client_path.c', '(abs(dx - dy) * 5 + m * 7 + 1) * 3 / 4',
     '(abs(dx - dy) * 5 + m * 7) * 3 / 4', 'search'),
    ('classic A* priority g(parent)+step+h', 'client_path.c',
     'mu_path_heuristic(tx, ty, nx, ny) + f->cost[current]',
     'mu_path_heuristic(tx, ty, nx, ny) + f->cost[current] + mu_path_step_cost(mu_path_directions[d][0], '
     'mu_path_directions[d][1])', 'search'),
    ('passability mask 0x1c (character tiles walkable)', 'client_path.h', '#define MU_PATH_WALL_MASK 0x1e',
     '#define MU_PATH_WALL_MASK 0x1c', 'search'),
    ('no safe-zone retry level 4', 'client_path.c', '            wall = 4;', '            wall = wall_level;',
     'search'),
    ('path capacity 16', 'client_path.h', '#define MU_PATH_CLIENT_NODES 15', '#define MU_PATH_CLIENT_NODES 14',
     'search'),
    ('distance marking with >=', 'client_path.c', 'if (!(distance > s))', 'if (!(distance >= s))', 'search'),
    ('object block ignored', 'client_path.c', 'if (f->object_flags && (f->object_flags[n] & 1u)',
     'if (0 && f->object_flags && (f->object_flags[n] & 1u)', 'search'),
    ('arrival radius < 30', 'client_path.c', 'if (whole <= 30)', 'if (whole < 30)', 'move'),
    ('spline t = 0.5 weights everywhere', 'client_path.c', '{-0.0703125f, 0.8671875f, 0.2265625f, -0.0234375f},',
     '{-0.0625f, 0.5625f, 0.5625f, -0.0625f},', 'move'),
    ('turn snaps above 45 only', 'client_path.c', 'if (difference >= 45.0f)', 'if (difference > 45.0f)', 'move'),
    ('exact binary32 pi in CreateAngle', 'client_path.c', 'a = a / 3.14159274f;', 'a = a * 0.318309886f;',
     'angles'),
    ('TurnAngle wraps with >', 'client_path.c', 'if (lo >= 0.0f && (b >= a + 180.0f || lo > b))',
     'if (lo > 0.0f && (b >= a + 180.0f || lo > b))', 'angles'),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    evidence = ROOT / 'evidence'
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(evidence / 'x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get(
        'MU_IMAGE_DATA', str(evidence / 'image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--flag', default=os.environ.get(
        'MU_TRIG_FLAG', str(evidence / 'trig-state-15/captures/late/math-dispatch-flag.bin')))
    parser.add_argument('--directions', default=os.environ.get(
        'MU_PATH_DIRECTIONS', str(evidence / 'x86-linux-capture-04/main-01ced000.bin')),
        help='unpacked third-section capture holding the neighbour table 0x01cf1640')
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--tool', default=str(ROOT / 'native/build/mu-path'))
    parser.add_argument('--worlds', default='0,1,2,3,4,7,8,9,10,32,33,37,38,40,41,56,62,79,90,141,142')
    parser.add_argument('--cases', type=int, default=200, help='cases per family')
    parser.add_argument('--seed', type=int, default=0x50415448)
    parser.add_argument('--only', default=None, help='comma list: search,installed,move,walk,angles,occupancy')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', default=None)
    args = parser.parse_args(argv)

    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'second section')
    flag = load_pinned(args.flag, 4, FLAG_SHA256, 'dispatch flag')
    directions = load_pinned(args.directions, 64, DIRECTIONS_SHA256, 'neighbour table',
                             offset=DIRECTIONS_ADDRESS - DIRECTIONS_SECTION)
    guest = Guest(text, data, flag, directions)
    lib = load_library()
    only = set(args.only.split(',')) if args.only else None
    n = args.cases
    tally = Tally()
    stats = []
    families = {
        'search': lambda lib_, t, r, c: run_search_family(guest, lib_, t, r, c, stats=stats),
        'move': lambda lib_, t, r, c: run_move_family(guest, lib_, t, r, c),
        'walk': lambda lib_, t, r, c: run_walk_family(guest, lib_, t, r, max(1, c // 4)),
        'angles': lambda lib_, t, r, c: run_angle_family(guest, lib_, t, r, c),
        'occupancy': lambda lib_, t, r, c: run_occupancy_family(guest, lib_, t, r, max(1, c // 20)),
    }
    if args.game_root and Path(args.tool).exists():
        worlds = list(range(0, 160)) if args.worlds == 'all' else [int(w) for w in args.worlds.split(',')]
        families['installed'] = lambda lib_, t, r, c: run_installed_family(guest, lib_, t, r, c, args.game_root,
                                                                           args.tool, worlds, stats=stats)
    for name, function in families.items():
        if only and name not in only:
            continue
        function(lib, tally, random.Random(f'{args.seed}:{name}'), n)
    total = sum(r['cases'] for r in tally.results.values())
    bad = sum(r['mismatches'] for r in tally.results.values())
    for family, r in tally.results.items():
        print(f"{family:44s} {r['cases']:6d} cases {r['mismatches']:5d} mismatches")
        if r['first']:
            print('    first:', json.dumps(r['first'], default=str)[:800])
    found = [s for s in stats if s['nodes']]
    summary = {'searches': len(stats), 'found': len(found),
               'max_pops': max((s['pops'] for s in stats), default=0),
               'max_closed': max((s['closed'] for s in stats), default=0),
               'mean_nodes': (sum(s['nodes'] for s in found) / len(found)) if found else 0}
    print(f'total {total} comparisons, {bad} mismatches; searches {json.dumps(summary)}')

    mutation_results = None
    if args.mutations:
        import shutil
        import tempfile
        mutation_results = []
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            shutil.copytree(ROOT / 'reconstructed' / 'record-math', scratch / 'record-math',
                            ignore=shutil.ignore_patterns('*.dylib', '*.so'))
            for label, filename, old, new, family in MUTATIONS:
                target = scratch / 'path'
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(ROOT / 'reconstructed' / 'path', target, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
                source = (target / filename).read_text()
                if source.count(old) != 1:
                    raise ValueError(f'mutation anchor not unique: {label}')
                (target / filename).write_text(source.replace(old, new))
                mutated = load_library(target)
                t = Tally()
                name = {'search': 'search', 'move': 'walk', 'angles': 'angles'}[family]
                count = max(40, n // 2)
                if family == 'move':
                    families['move'](mutated, t, random.Random(f'{args.seed}:mut:{label}'), count)
                families[name](mutated, t, random.Random(f'{args.seed}:mut:{label}'), count)
                misses = sum(r['mismatches'] for r in t.results.values())
                cases = sum(r['cases'] for r in t.results.values())
                mutation_results.append({'mutation': label, 'mismatches': misses, 'cases': cases})
                print(f'mutation {label:52s} {misses:5d}/{cases} detected')
    report = {'total': total, 'mismatches': bad, 'families': tally.results, 'searches': summary,
              'mutations': mutation_results,
              'stubs': {hex(k): v[2] for k, v in CLIENT_STUBS.items()},
              'routines': {k: {'start': hex(v[0]), 'bytes': v[1], 'sha256': v[2]} for k, v in ROUTINES.items()}}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    undetected = [m['mutation'] for m in (mutation_results or []) if m['mismatches'] == 0]
    if undetected:
        print('undetected mutations:', undetected)
    return 1 if bad or undetected else 0


if __name__ == '__main__':
    sys.exit(main())
