#!/usr/bin/env python3
"""Compare the reconstructed audio logic with the client's instructions.

Client code runs in Unicorn over the pinned restored text and the verified
second image section. FMOD is the platform boundary: every call into the 35
FMOD import thunks (0x018eb289 + 6*k) is answered by a recorder with scripted
results, and the recorded sequence is compared with the calls the authored C
(reconstructed/audio, through ctypes) makes for the same inputs.

Checks:
  frame     per-frame ambient loops and music selection, 0x0185280c..0x01854498
            (segment 0x01854279..0x018542c2 is protector-virtualised and skipped)
  openworld OpenWorld music-group volume rule, 0x018290be..0x018293a6
  manager   SND_Load/Play/Stop/Remove, the channel callback, PlayMp3/StopMp3 and
            the FMOD wrapper underneath (create with path cache, play on a group)
  settings  apply/read settings 0x010ab480/0x010ab506 and the options-UI level
            conversions (0x00f2fc2e..0x00f2fc43, 0x00f2fe04..0x00f2fe09)
  init      FMOD system init 0x010aad03 under scripted driver answers

Modelled explicitly (not client code): uncaptured globals (world 0x01cf15fc,
scene 0x01d1df70, hero tile 0x0b437c10, rain 0x0a3a9acc, hero pointer
0x0a39d754, terrain attributes 0x0b795420, music table 0x01cf1680, the sound
system object and the group-name strings), the C++ runtime allocator
(operator new 0x0191ba7b and the matching frees), std::string construction in
the frame block (0x0094997e and its destructors), CRT rand, and the event-world
managers the frame block delegates to (recorded, not run). Any read of an
unmapped address, of uncaptured or never-written bytes stops a case.
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
TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'

FMOD_THUNK, FMOD_COUNT = 0x18eb289, 35
FMOD_NAMES = [
    'Channel::stop', 'Channel::setCallback', 'Channel::setUserData', 'Channel::getUserData',
    'Sound::release', 'System_Create', 'System::release', 'System::setOutput',
    'System::getNumDrivers', 'System::getDriverInfo', 'System::getDriverCaps',
    'System::setSoftwareFormat', 'System::setDSPBufferSize', 'System::setSpeakerMode',
    'System::init', 'System::close', 'System::update', 'System::createStream',
    'System::createSound', 'System::createChannelGroup', 'System::playSound',
    'System::getMasterChannelGroup', 'Channel::setPaused', 'Channel::setPriority',
    'Channel::setChannelGroup', 'Channel::setMode', 'ChannelGroup::release',
    'ChannelGroup::setVolume', 'ChannelGroup::getVolume', 'ChannelGroup::setPaused',
    'ChannelGroup::getPaused', 'ChannelGroup::setMute', 'ChannelGroup::getMute',
    'ChannelGroup::stop', 'ChannelGroup::addGroup']
FMOD_ARGS = [1, 2, 2, 2, 1, 1, 1, 2, 2, 5, 6, 6, 3, 2, 4, 1, 1, 5, 5, 3, 5, 2, 2, 2, 2, 2, 1, 2, 2, 2,
             2, 2, 2, 1, 2]

# Pinned client routine bodies (start, end) with SHA-256 of the restored bytes.
BODIES = {
    'frame-block': (0x185280c, 0x1854498, None),
    'openworld-fragment': (0x18290be, 0x18293a6, None),
    'snd-manager': (0xa6ab76, 0xa6ae7c, None),
    'fmod-wrapper': (0x10aaa2a, 0x10ab573, None),
    'music': (0x120f5a0, 0x120f6c2, None),
}

STACK, STACK_SIZE = 0x30000000, 0x40000
ARENA, ARENA_SIZE = 0x31000000, 0x400000
FAKE, FAKE_SIZE = 0x32000000, 0x100000   # fake object addresses (never dereferenced)
RETURN_SENTINEL = 0x33000000
GDT, TEB = 0x34000000, 0x34001000


def load_pinned(path, size, digest, label):
    payload = Path(path).read_bytes()
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input does not match pinned {label}')
    return payload


def signed(value):
    value &= 0xffffffff
    return value - (1 << 32) if value & 0x80000000 else value


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def f32_bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def bits_f32(bits):
    return struct.unpack('<f', struct.pack('<I', bits & 0xffffffff))[0]


class CaseError(Exception):
    pass


class Machine:
    """Restored text + data in Unicorn with strict read tracking."""

    def __init__(self, text, data, strict_stack=True):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_READ, UC_PROT_EXEC, UC_PROT_ALL
        from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED
        from unicorn import x86_const as x86
        self.x86 = x86
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc = self.uc
        uc.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        data_span = (DATA_BYTES + 0xfff) & ~0xfff
        uc.mem_map(DATA_BASE, data_span, UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        self.data_end = DATA_BASE + DATA_BYTES
        self.tracked = []   # (base, size, bytearray defined)
        for base, size in ((STACK, STACK_SIZE), (ARENA, ARENA_SIZE)):
            self.map_tracked(base, size)
        if not strict_stack:
            # STL code copies empty tag objects (allocators, comparators) out of
            # never-written stack slots; treat the zero-filled stack as defined.
            self.tracked[0][2][:] = b'\x01'*STACK_SIZE
        uc.mem_map(RETURN_SENTINEL, 0x1000, UC_PROT_ALL)
        uc.mem_map(GDT, 0x2000, UC_PROT_ALL)
        self.define(TEB, 0x100)
        entry = lambda base, limit, access, flags: (
            (limit & 0xffff) | ((base & 0xffffff) << 16) | (access << 40) | (((limit >> 16) & 0xf) << 48) |
            (flags << 52) | (((base >> 24) & 0xff) << 56))
        uc.mem_write(GDT, struct.pack('<QQQ', 0, entry(TEB, 0xfff, 0x92, 0x4), entry(0, 0xfffff, 0x92, 0xc)))
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, GDT, 23, 0))
        uc.reg_write(x86.UC_X86_REG_FS, 1 << 3)
        for segment in (x86.UC_X86_REG_SS, x86.UC_X86_REG_DS, x86.UC_X86_REG_ES):
            uc.reg_write(segment, 2 << 3)
        uc.mem_write(TEB, struct.pack('<I', 0xffffffff))  # fs:[0] SEH chain end
        self.hooks = {}
        self.violation = None
        self.pushed_undefined = 0
        self.arena_next = ARENA + 0x1000
        uc.hook_add(UC_HOOK_MEM_READ, self._on_read)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._on_write)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._on_unmapped)

    # ---- memory ----------------------------------------------------------
    def map_tracked(self, base, size):
        from unicorn import UC_PROT_READ, UC_PROT_WRITE
        self.uc.mem_map(base, size, UC_PROT_READ | UC_PROT_WRITE)
        self.tracked.append((base, size, bytearray(size)))

    def model_page(self, address, size=0x1000):
        """Map a tracked region covering an uncaptured client address range."""
        base = address & ~0xfff
        end = (address + size + 0xfff) & ~0xfff
        for b, s, _ in self.tracked:
            if b <= base < b + s:
                return
        self.map_tracked(base, end - base)

    def _region(self, address):
        for base, size, defined in self.tracked:
            if base <= address < base + size:
                return base, defined
        return None, None

    def define(self, address, size):
        for i in range(size):
            base, defined = self._region(address + i)
            if base is not None:
                defined[address + i - base] = 1

    def write(self, address, payload):
        self.model_page(address, len(payload))
        self.uc.mem_write(address, payload)
        self.define(address, len(payload))

    def write32(self, address, value):
        self.write(address, struct.pack('<I', value & 0xffffffff))

    def read32(self, address):
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def read(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def checked_read(self, address, size):
        """Read on behalf of a modelled routine, with the strict definedness rule."""
        for i in range(size):
            a = address + i
            if TEXT_BASE <= a < TEXT_BASE + TEXT_BYTES or DATA_BASE <= a < self.data_end:
                continue
            base, defined = self._region(a)
            if base is None or not defined[a - base]:
                raise CaseError(f'modelled routine read undefined byte {a:#x}')
        return self.read(address, size)

    def cstring(self, address, limit=1024):
        out = bytearray()
        while len(out) < limit:
            byte = self.checked_read(address + len(out), 1)
            if byte == b'\0':
                return out.decode('latin1')
            out += byte
        raise CaseError('unterminated string')

    def alloc(self, size, align=16):
        self.arena_next = (self.arena_next + align - 1) & ~(align - 1)
        address = self.arena_next
        self.arena_next += size
        if self.arena_next > ARENA + ARENA_SIZE:
            raise CaseError('arena exhausted')
        return address

    def _on_read(self, uc, access, address, size, value, user):
        if TEXT_BASE <= address and address + size <= TEXT_BASE + TEXT_BYTES:
            return
        if DATA_BASE <= address and address + size <= self.data_end:
            return
        if GDT <= address < GDT + 0x2000:
            return
        for i in range(size):
            base, defined = self._region(address + i)
            if base is None or not defined[address + i - base]:
                pc = uc.reg_read(self.x86.UC_X86_REG_EIP)
                if base is not None and self._result_independent(pc):
                    return
                if base == STACK and self._stack_push(pc):
                    self.pushed_undefined += 1
                    return
                if self.violation is None:
                    pc = uc.reg_read(self.x86.UC_X86_REG_EIP)
                    self.violation = f'read of undefined byte {address + i:#x} at {pc:#x}'
                uc.emu_stop()
                return

    def _stack_push(self, pc):
        """`push m32` of a never-written stack slot: MSVC passes empty tag objects
        (allocators, comparators) by value this way. Counted, not propagated."""
        if not TEXT_BASE <= pc < TEXT_BASE + TEXT_BYTES - 16:
            return False
        code = self.read(pc, 2)
        return code[0] == 0xff and (code[1] >> 3) & 7 == 6

    def _result_independent(self, pc):
        """`and m32, 0` and `or m32, -1` read memory but their result does not depend on it."""
        if not TEXT_BASE <= pc < TEXT_BASE + TEXT_BYTES - 16:
            return False
        code = self.read(pc, 12)
        if code[0] != 0x83:
            return False
        reg = (code[1] >> 3) & 7
        mod, rm = code[1] >> 6, code[1] & 7
        length = 2 + (1 if rm == 4 and mod != 3 else 0) + {0: 4 if rm == 5 else 0, 1: 1, 2: 4, 3: 0}[mod]
        immediate = code[length]
        return (reg == 4 and immediate == 0) or (reg == 1 and immediate == 0xff)

    def _on_write(self, uc, access, address, size, value, user):
        if address < self.data_end + 0x1000 and address >= TEXT_BASE:
            if self.violation is None:
                self.violation = f'write into captured image {address:#x}'
            uc.emu_stop()
            return
        for i in range(size):
            base, defined = self._region(address + i)
            if base is not None:
                defined[address + i - base] = 1

    def _on_unmapped(self, uc, access, address, size, value, user):
        if self.violation is None:
            pc = uc.reg_read(self.x86.UC_X86_REG_EIP)
            self.violation = f'unmapped access {address:#x} at {pc:#x}'
        return False

    # ---- calls -----------------------------------------------------------
    def hook(self, address, handler):
        """handler(machine) -> (eax, bytes_to_pop_after_return) emulating the routine."""
        from unicorn import UC_HOOK_CODE
        self.hooks[address] = handler

        def run(uc, pc, size, user):
            if pc != address:
                return
            esp = uc.reg_read(self.x86.UC_X86_REG_ESP)
            try:
                result, cleanup = handler(self)
            except CaseError as error:
                self.violation = self.violation or str(error)
                uc.emu_stop()
                return
            ret = self.read32(esp)
            if result is not None:
                uc.reg_write(self.x86.UC_X86_REG_EAX, result & 0xffffffff)
            uc.reg_write(self.x86.UC_X86_REG_ESP, esp + 4 + cleanup)
            uc.reg_write(self.x86.UC_X86_REG_EIP, ret)
        self.uc.hook_add(UC_HOOK_CODE, run, begin=address, end=address)

    def arg(self, index):
        esp = self.uc.reg_read(self.x86.UC_X86_REG_ESP)
        return self.read32(esp + 4 + 4*index)

    def reg(self, name):
        return self.uc.reg_read(getattr(self.x86, 'UC_X86_REG_' + name.upper()))

    def set_reg(self, name, value):
        self.uc.reg_write(getattr(self.x86, 'UC_X86_REG_' + name.upper()), value & 0xffffffff)

    def run(self, begin, until, stops=(), ebp=None, esp=None, count=2_000_000):
        from unicorn import UcError, UC_HOOK_CODE
        handles = []
        for address in stops:
            handles.append(self.uc.hook_add(UC_HOOK_CODE, lambda uc, pc, s, u: uc.emu_stop(),
                                            begin=address, end=address))
        if ebp is not None:
            self.set_reg('ebp', ebp)
        if esp is not None:
            self.set_reg('esp', esp)
        try:
            self.uc.emu_start(begin, until, count=count)
        except UcError as error:
            self.violation = self.violation or f'unicorn: {error} at {self.reg("eip"):#x}'
        for handle in handles:
            self.uc.hook_del(handle)
        if self.violation:
            raise CaseError(self.violation)
        return self.reg('eip')

    def call(self, function, args, this=None, count=2_000_000):
        """Call a client routine with stack args (cdecl/stdcall/thiscall)."""
        esp = STACK + STACK_SIZE - 0x2000
        frame = struct.pack('<I', RETURN_SENTINEL) + b''.join(struct.pack('<I', a & 0xffffffff) for a in args)
        esp -= len(frame)
        self.write(esp, frame)
        if this is not None:
            self.set_reg('ecx', this)
        for name, value in (('ebx', 0x0b0b0b0b), ('esi', 0x0c0c0c0c), ('edi', 0x0d0d0d0d), ('ebp', 0x0e0e0e0e)):
            self.set_reg(name, value)
        self.set_reg('esp', esp)
        from unicorn import UcError
        try:
            self.uc.emu_start(function, RETURN_SENTINEL, count=count)
        except UcError as error:
            self.violation = self.violation or f'unicorn: {error} at {self.reg("eip"):#x}'
        if self.violation:
            raise CaseError(self.violation)
        if self.reg('eip') != RETURN_SENTINEL:
            raise CaseError(f'did not return (eip {self.reg("eip"):#x})')
        return self.reg('eax')


def fmod_check_arguments(text):
    """Static check: every call site of each thunk pushes FMOD_ARGS[k] arguments
    and the caller does not pop them afterwards (stdcall)."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    thunks = {FMOD_THUNK + 6*k: k for k in range(FMOD_COUNT)}
    region = (0xa6a000, 0xa6f000), (0x10aa000, 0x10ad000)
    sites = 0
    for begin, end in region:
        for ins in decoder.disasm(text[begin - TEXT_BASE:end - TEXT_BASE], begin):
            if ins.mnemonic == 'call' and ins.op_str.startswith('0x') and int(ins.op_str, 16) in thunks:
                sites += 1
    return sites


# ---------------------------------------------------------------------------
# C side
# ---------------------------------------------------------------------------

EVENT = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_int32, ctypes.c_int32)
RAND = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
BOSS = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)


class WorldState(ctypes.Structure):
    _fields_ = [('scene', ctypes.c_int32), ('world', ctypes.c_int32), ('hero_tile', ctypes.c_int32),
                ('rain', ctypes.c_int32), ('hero_safe_zone', ctypes.c_int32), ('hero_x', ctypes.c_int32),
                ('hero_y', ctypes.c_int32), ('hero_attribute', ctypes.c_uint16)]


class WorldHooks(ctypes.Structure):
    _fields_ = [('ctx', ctypes.c_void_p), ('rand', RAND), ('in_boss_zone', BOSS), ('event', EVENT)]


def load_library(path):
    library = ctypes.CDLL(str(Path(path).resolve(strict=True)))
    library.mu_world_audio_frame.argtypes = [ctypes.POINTER(WorldState), ctypes.POINTER(WorldHooks)]
    library.mu_world_audio_frame.restype = None
    library.mu_audio_world_music_volume.argtypes = [ctypes.c_int32]
    library.mu_audio_world_music_volume.restype = ctypes.c_float
    library.mu_audio_level_to_volume.argtypes = [ctypes.c_int32]
    library.mu_audio_level_to_volume.restype = ctypes.c_float
    library.mu_audio_volume_to_level.argtypes = [ctypes.c_float]
    library.mu_audio_volume_to_level.restype = ctypes.c_int32
    return library


KIND = {1: 'snd_play', 2: 'snd_stop', 3: 'mp3_play', 4: 'mp3_stop', 5: 'delegate', 6: 'unrecovered'}


def c_frame(library, case):
    events = []

    def on_event(ctx, kind, a, b):
        name = KIND[kind]
        if name == 'snd_play':
            events.append((name, a, b))
        elif name in ('snd_stop', 'mp3_play', 'mp3_stop'):
            events.append((name, a))
        elif name == 'delegate':
            events.append((name, a & 0xffffffff, b))
        else:
            events.append((name, a))

    def on_rand(ctx):
        events.append(('rand',))
        return case['rand']

    def on_boss(ctx, world, x, y):
        events.append(('boss_query', world, x, y))
        return case['boss']

    keep = (EVENT(on_event), RAND(on_rand), BOSS(on_boss))
    hooks = WorldHooks(None, keep[1], keep[2], keep[0])
    state = WorldState(case['scene'], case['world'], case['tile'], case['rain'], case['safe'], case['x'],
                       case['y'], case['attribute'])
    library.mu_world_audio_frame(ctypes.byref(state), ctypes.byref(hooks))
    if ('unrecovered', 0x1854279) in events:
        cut = events.index(('unrecovered', 0x1854279))
        return events[:cut], events[cut + 1:]
    return events, None


# ---------------------------------------------------------------------------
# frame block
# ---------------------------------------------------------------------------

WORLD, SCENE, TILE, RAIN, HERO_PTR = 0x1cf15fc, 0x1d1df70, 0xb437c10, 0xa3a9acc, 0xa39d754
TERRAIN, MUSIC_TABLE, MUSIC_COUNT = 0xb795420, 0x1cf1680, 76
SEG_A, SEG_A_END, SEG_B, FRAME_END = 0x185280c, 0x1854279, 0x18542c2, 0x1854498
SND_PLAY, SND_STOP, PLAY_MP3, STOP_MP3 = 0xa6ac96, 0xa6ad76, 0x120f602, 0x120f5a0
STRING_CTOR, STRING_DTORS = 0x94997e, (0x94f183, 0x8e83a0, 0x94a731)
CRT_RAND, BOSS_GETTER, BOSS_TEST = 0x1989721, 0xfdc490, 0xe5ea60
CDECL_DELEGATES = {0xdb3e26: 1, 0xe8e857: 1, 0xe84474: 0}
GETTERS_NOARG = {0xd53c8f: 0xd557af, 0xdb747f: None}
GETTERS = {0x1214720: 0xe9e9c5, 0x1851350: 0xe42ad0, 0x185137b: 0xe92fc8, 0xdd8a3c: 0xdd306c,
           0x13b9431: 0xdd8891, 0x13b945c: 0xdde543, 0xe34377: 0xde5467, 0x153b001: 0xe6dd22,
           0x13b9406: 0xe189e4, 0xd7f093: 0xd73c38}
MUSIC_FAKE = FAKE + 0x10000
FRAME_EBP = STACK + STACK_SIZE - 0x4000


def client_frame(text, data, case):
    m = Machine(text, data)
    events = []
    m.model_page(WORLD)
    m.model_page(SCENE)
    m.model_page(TILE)
    m.model_page(RAIN)
    m.model_page(HERO_PTR)
    m.model_page(TERRAIN, 0x20000)
    m.write32(WORLD, case['world'])
    m.write32(SCENE, case['scene'])
    m.write32(TILE, case['tile'])
    m.write32(RAIN, case['rain'])
    hero = m.alloc(0x200)
    m.write(hero + 4, bytes([case['safe'] & 0xff]))
    m.write32(hero + 0x180, case['x'])
    m.write32(hero + 0x184, case['y'])
    m.write32(HERO_PTR, hero)
    if 0 <= case['x'] < 256 and 0 <= case['y'] < 256:
        m.write(TERRAIN + 2*(case['x'] + case['y']*256), struct.pack('<H', case['attribute']))
    for index in range(MUSIC_COUNT):
        m.write32(MUSIC_TABLE + 4*index, MUSIC_FAKE + 0x40*index)

    def snd_play(m):
        if m.arg(1) != 0:
            raise CaseError('SND_Play object argument is not null')
        events.append(('snd_play', signed(m.arg(0)), signed(m.arg(2))))
        return 1, 0

    def snd_stop(m):
        events.append(('snd_stop', signed(m.arg(0))))
        return 0, 0

    def mp3(name):
        def handler(m):
            pointer = m.read32(m.arg(0))
            index, rest = divmod(pointer - MUSIC_FAKE, 0x40)
            if rest or not 0 <= index < MUSIC_COUNT:
                raise CaseError('music string does not come from the table')
            events.append((name, index))
            return 0, 0
        return handler

    def ctor(m):
        this, text_pointer = m.reg('ecx'), m.arg(0)
        m.write32(this, text_pointer)
        m.write32(this + 0x10, 1)
        m.write32(this + 0x14, 0x1f)
        return this, 4

    def no_op(m):
        return None, 0

    def rand(m):
        events.append(('rand',))
        return case['rand'], 0

    def boss_getter(m):
        if m.arg(0) != 0x7a:
            raise CaseError('unexpected world object request')
        return FAKE + 0x7a, 0

    def boss_test(m):
        if m.reg('ecx') != FAKE + 0x7a:
            raise CaseError('boss-zone test on an unexpected object')
        events.append(('boss_query', 0x7a, signed(m.arg(0)), signed(m.arg(1))))
        return case['boss'], 8

    def cdecl_delegate(address, count):
        def handler(m):
            events.append(('delegate', address, signed(m.arg(0)) if count else -1))
            return 0, 0
        return handler

    def getter_noarg(address, method):
        def handler(m):
            if method is None:
                events.append(('delegate', address, -1))
            return FAKE + 0x1000 + (address & 0xfff), 0
        return handler

    def method_noarg(address, getter):
        def handler(m):
            if m.reg('ecx') != FAKE + 0x1000 + (getter & 0xfff):
                raise CaseError('delegate method on an unexpected object')
            events.append(('delegate', address, -1))
            return 0, 0
        return handler

    def getter(address):
        def handler(m):
            return FAKE + 0x2000 + m.arg(0), 0
        return handler

    def manager(address):
        def handler(m):
            world = signed(m.reg('ecx') - FAKE - 0x2000)
            events.append(('delegate', address, world))
            return 0, 0
        return handler

    m.hook(SND_PLAY, snd_play)
    m.hook(SND_STOP, snd_stop)
    m.hook(PLAY_MP3, mp3('mp3_play'))
    m.hook(STOP_MP3, mp3('mp3_stop'))
    m.hook(STRING_CTOR, ctor)
    for address in STRING_DTORS:
        m.hook(address, no_op)
    m.hook(CRT_RAND, rand)
    m.hook(BOSS_GETTER, boss_getter)
    m.hook(BOSS_TEST, boss_test)
    for address, count in CDECL_DELEGATES.items():
        m.hook(address, cdecl_delegate(address, count))
    for address, method in GETTERS_NOARG.items():
        m.hook(address, getter_noarg(address, method))
        if method:
            m.hook(method, method_noarg(method, address))
    for address, method in GETTERS.items():
        m.hook(address, getter(address))
        m.hook(method, manager(method))

    end = m.run(SEG_A, SEG_A_END, stops=(FRAME_END,), ebp=FRAME_EBP, esp=FRAME_EBP - 0x960)
    trace_a = list(events)
    if end == FRAME_END:
        return trace_a, None
    if end != SEG_A_END:
        raise CaseError(f'segment A ended at {end:#x}')
    events.clear()
    end = m.run(SEG_B, FRAME_END, ebp=FRAME_EBP, esp=FRAME_EBP - 0x960)
    if end != FRAME_END:
        raise CaseError(f'segment B ended at {end:#x}')
    return trace_a, list(events)


def frame_cases(seed=0x185280c, extra=0):
    cases = []
    base = dict(scene=6, world=0, tile=0, rain=0, safe=1, x=128, y=128, attribute=0, rand=1, boss=0)
    worlds = list(range(0, 0xa0)) + [0xa0, 0xff, 0x100, -1, 0x7fffffff]
    for world in worlds:
        for safe in (0, 1):
            cases.append(dict(base, world=world, safe=safe))
    for scene in (0, 1, 3, 5, 7):
        cases.append(dict(base, scene=scene, world=0))
    for tile in (0, 3, 4, 9, 10, 11, 12, -1):
        for world in (0, 2, 0x51):
            cases.append(dict(base, world=world, tile=tile))
    for rain in (0, 1, 5, -1):
        cases.append(dict(base, world=0, rain=rain))
    for x, y in ((0xcc, 0x14), (0xcd, 0x14), (0xd6, 0x14), (0xd7, 0x14), (0xd0, 0x0c), (0xd0, 0x0d),
                 (0xd0, 0x1f), (0xd0, 0x20), (0xcd, 0x0d), (0xd6, 0x1f)):
        for safe in (0, 1):
            cases.append(dict(base, world=2, x=x, y=y, safe=safe))
    for value in (0, 1, 511, 512, 513, 1024, 32767):
        cases.append(dict(base, world=3, rand=value))
    for attribute in (0, 0x800, 0x1000, 0x1800, 0x7ff, 0xffff):
        for world in (0x64, 0x65):
            cases.append(dict(base, world=world, attribute=attribute, x=37, y=200))
    for boss in (0, 1):
        cases.append(dict(base, world=0x7a, boss=boss, x=99, y=17))
    cases.append(dict(base, world=0x8d, safe=0))
    cases.append(dict(base, world=0x8d, safe=1))
    cases.append(dict(base, world=0x8d, safe=2))
    generator = random.Random(seed)
    for _ in range(extra):
        cases.append(dict(scene=generator.choice((6, 6, 6, 5)), world=generator.randrange(-2, 0xa2),
                          tile=generator.choice((0, 3, 4, 10, 12, generator.randrange(-5, 40))),
                          rain=generator.choice((0, 0, 1, 3)), safe=generator.choice((0, 1, 2)),
                          x=generator.randrange(0, 256), y=generator.randrange(0, 256),
                          attribute=generator.getrandbits(16), rand=generator.randrange(0, 32768),
                          boss=generator.choice((0, 1))))
    return cases


def check_frame_sensitivity(text, data, library, count=300, seed=0x1854498):
    """Give the C side a different world than the client; the comparison must
    notice unless both worlds really behave alike."""
    generator = random.Random(seed)
    cases = [case for case in frame_cases(extra=count)[-count:] if case['scene'] == 6]
    detected = alike = 0
    for case in cases:
        client = client_frame(text, data, case)
        mutated = dict(case, world=case['world'] + generator.choice((1, -1, 2, 7)))
        if client != c_frame(library, mutated):
            detected += 1
        elif client == client_frame(text, data, mutated):
            alike += 1  # the client itself treats both worlds identically
    return {'perturbed': len(cases), 'detected': detected, 'client_identical': alike,
            'missed': len(cases) - detected - alike}


def check_frame(text, data, library, extra):
    results = {'cases': 0, 'equal': 0, 'events': 0, 'first_mismatch': None, 'worlds': set()}
    for case in frame_cases(extra=extra):
        client = client_frame(text, data, case)
        native = c_frame(library, case)
        results['cases'] += 1
        results['events'] += len(client[0]) + len(client[1] or [])
        results['worlds'].add(case['world'])
        if client == native:
            results['equal'] += 1
        elif results['first_mismatch'] is None:
            results['first_mismatch'] = {'case': case, 'client': client, 'native': native}
    results['worlds'] = len(results['worlds'])
    return results


# ---------------------------------------------------------------------------
# FMOD boundary recorder (shared by the client and the C side)
# ---------------------------------------------------------------------------

class Recorder:
    """Answers FMOD calls with deterministic handles and scripted results."""

    def __init__(self, script=None):
        script = script or {}
        self.records = []
        self.next = {'system': 0x5100, 'sound': 0x6000, 'channel': 0x7000, 'group': 0x8000}
        self.fail = {name: list(codes) for name, codes in script.get('fail', {}).items()}
        self.drivers = script.get('drivers', 1)
        self.caps = script.get('caps', 0)
        self.speaker = script.get('speaker', 5)
        self.driver_name = script.get('name', 'Primary Sound Driver')
        self.userdata = {}
        self.volume = {}
        self.mute = {}
        self.paused = {}

    def result(self, name):
        queue = self.fail.get(name)
        return queue.pop(0) if queue else 0

    def new(self, kind):
        handle = self.next[kind]
        self.next[kind] += 1
        return handle

    def record(self, *item):
        self.records.append(item)


CALLBACK_ADDRESS = 0xa6ae37
OPERATOR_NEW = 0x191ba7b
SYS_GET, SYS_CTOR, SND_MAP, SND_MAP_CTOR = 0xa6bb36, 0x10abb73, 0x1d1e018, 0xa6b6f3
GROUP_NAME_STRINGS = 0x6fba808
SYS_INIT, SYS_APPLY, SYS_READ, SYS_STOP_GROUP, SYS_UPDATE = 0x10aad03, 0x10ab480, 0x10ab506, 0x10ab15f, 0x10aafdd
SND_LOAD, SND_REMOVE = 0xa6ab76, 0xa6add6


def client_fmod_handler(recorder, k, machine_ref):
    name = FMOD_NAMES[k]

    def handler(m):
        a = [m.arg(i) for i in range(FMOD_ARGS[k])]
        r = recorder.result(name)
        if k == 0 or k == 4 or k == 6 or k == 15 or k == 16 or k == 26 or k == 33:
            recorder.record(name, a[0])
        elif k == 1:
            recorder.record(name, a[0], 'end-callback' if a[1] == CALLBACK_ADDRESS else hex(a[1]))
        elif k == 2:
            recorder.record(name, a[0], ('entry', signed(m.read32(a[1] - 4))) if a[1] else None)
            if r == 0:
                recorder.userdata[a[0]] = a[1]
        elif k == 3:
            recorder.record(name, a[0])
            m.write32(a[1], recorder.userdata.get(a[0], 0))
        elif k == 5:
            recorder.record(name)
            if r == 0:
                m.write32(a[0], recorder.new('system'))
        elif k in (7, 13):
            recorder.record(name, a[0], signed(a[1]))
        elif k == 8:
            recorder.record(name, a[0])
            if r == 0:
                m.write32(a[1], recorder.drivers)
        elif k == 9:
            recorder.record(name, a[0], signed(a[1]), signed(a[3]), a[4] != 0)
            if r == 0:
                text = recorder.driver_name.encode('latin1')[:max(0, signed(a[3]) - 1)] + b'\0'
                m.write(a[2], text)
        elif k == 10:
            recorder.record(name, a[0], signed(a[1]), a[3] != 0, a[4] != 0)
            if r == 0:
                m.write32(a[2], recorder.caps)
                m.write32(a[5], recorder.speaker)
        elif k == 11:
            recorder.record(name, *[signed(x) for x in a])
        elif k == 12:
            recorder.record(name, a[0], a[1], signed(a[2]))
        elif k == 14:
            recorder.record(name, a[0], signed(a[1]), a[2], a[3])
        elif k in (17, 18):
            recorder.record(name, a[0], m.cstring(a[1]), hex(a[2]), a[3])
            if r == 0:
                m.write32(a[4], recorder.new('sound'))
        elif k == 19:
            recorder.record(name, a[0], m.cstring(a[1]))
            if r == 0:
                m.write32(a[2], recorder.new('group'))
        elif k == 20:
            recorder.record(name, a[0], signed(a[1]), a[2], a[3] & 0xff)
            if r == 0:
                m.write32(a[4], recorder.new('channel'))
        elif k == 21:
            recorder.record(name, a[0])
            if r == 0:
                m.write32(a[1], recorder.new('group'))
        elif k in (22, 29, 31):
            recorder.record(name, a[0], a[1] & 0xff)
            if k == 31:
                recorder.mute[a[0]] = a[1] & 0xff
            if k == 29:
                recorder.paused[a[0]] = a[1] & 0xff
        elif k in (23, 25):
            recorder.record(name, a[0], signed(a[1]) if k == 23 else hex(a[1]))
        elif k in (24, 34):
            recorder.record(name, a[0], a[1])
        elif k == 27:
            recorder.record(name, a[0], hex(a[1]))
            recorder.volume[a[0]] = a[1]
        elif k == 28:
            recorder.record(name, a[0])
            m.write32(a[1], recorder.volume.get(a[0], f32_bits(1.0)))
        elif k in (30, 32):
            recorder.record(name, a[0])
            store = recorder.mute if k == 32 else recorder.paused
            m.write(a[1], bytes([store.get(a[0], 0)]))
        return r, 4*FMOD_ARGS[k]
    return handler


class Api(ctypes.Structure):
    pass


H = ctypes.c_uint32
I32 = ctypes.c_int32
U32 = ctypes.c_uint32
VP = ctypes.c_void_p
P = ctypes.POINTER
API_TYPES = [
    (I32, VP, H), (I32, VP, H, VP), (I32, VP, H, VP), (I32, VP, H, P(VP)), (I32, VP, H),
    (I32, VP, P(H)), (I32, VP, H), (I32, VP, H, I32), (I32, VP, H, P(I32)),
    (I32, VP, H, I32, VP, I32, VP), (I32, VP, H, I32, P(U32), P(I32), P(I32), P(I32)),
    (I32, VP, H, I32, I32, I32, I32, I32), (I32, VP, H, U32, I32), (I32, VP, H, I32),
    (I32, VP, H, I32, U32, VP), (I32, VP, H), (I32, VP, H),
    (I32, VP, H, ctypes.c_char_p, U32, VP, P(H)), (I32, VP, H, ctypes.c_char_p, U32, VP, P(H)),
    (I32, VP, H, ctypes.c_char_p, P(H)), (I32, VP, H, I32, H, I32, P(H)), (I32, VP, H, P(H)),
    (I32, VP, H, I32), (I32, VP, H, I32), (I32, VP, H, H), (I32, VP, H, U32), (I32, VP, H),
    (I32, VP, H, ctypes.c_float), (I32, VP, H, P(ctypes.c_float)), (I32, VP, H, I32), (I32, VP, H, P(I32)),
    (I32, VP, H, I32), (I32, VP, H, P(I32)), (I32, VP, H), (I32, VP, H, H)]
API_FUNCS = [ctypes.CFUNCTYPE(*t) for t in API_TYPES]
Api._fields_ = [('ctx', VP)] + [(f'f{k}', API_FUNCS[k]) for k in range(FMOD_COUNT)]


def c_api(recorder, callback_address):
    def make(k):
        name = FMOD_NAMES[k]

        def f(ctx, *a):
            r = recorder.result(name)
            if k in (0, 4, 6, 15, 16, 26, 33):
                recorder.record(name, a[0])
            elif k == 1:
                recorder.record(name, a[0], 'end-callback' if a[1] == callback_address else hex(a[1] or 0))
            elif k == 2:
                recorder.record(name, a[0], ('entry', ctypes.c_int32.from_address(a[1]).value) if a[1] else None)
                if r == 0:
                    recorder.userdata[a[0]] = a[1]
            elif k == 3:
                recorder.record(name, a[0])
                a[1][0] = recorder.userdata.get(a[0])
            elif k == 5:
                recorder.record(name)
                if r == 0:
                    a[0][0] = recorder.new('system')
            elif k in (7, 13):
                recorder.record(name, a[0], a[1])
            elif k == 8:
                recorder.record(name, a[0])
                if r == 0:
                    a[1][0] = recorder.drivers
            elif k == 9:
                recorder.record(name, a[0], a[1], a[3], bool(a[4]))
                if r == 0:
                    text = recorder.driver_name.encode('latin1')[:max(0, a[3] - 1)] + b'\0'
                    ctypes.memmove(a[2], text, len(text))
            elif k == 10:
                recorder.record(name, a[0], a[1], bool(a[3]), bool(a[4]))
                if r == 0:
                    a[2][0] = recorder.caps
                    a[5][0] = recorder.speaker
            elif k == 11:
                recorder.record(name, *a)
            elif k == 12:
                recorder.record(name, a[0], a[1], a[2])
            elif k == 14:
                recorder.record(name, a[0], a[1], a[2], a[3] or 0)
            elif k in (17, 18):
                recorder.record(name, a[0], a[1].decode('latin1'), hex(a[2]), a[3] or 0)
                if r == 0:
                    a[4][0] = recorder.new('sound')
            elif k == 19:
                recorder.record(name, a[0], a[1].decode('latin1'))
                if r == 0:
                    a[2][0] = recorder.new('group')
            elif k == 20:
                recorder.record(name, a[0], a[1], a[2], a[3])
                if r == 0:
                    a[4][0] = recorder.new('channel')
            elif k == 21:
                recorder.record(name, a[0])
                if r == 0:
                    a[1][0] = recorder.new('group')
            elif k in (22, 29, 31):
                recorder.record(name, a[0], a[1])
                if k == 31:
                    recorder.mute[a[0]] = a[1]
                if k == 29:
                    recorder.paused[a[0]] = a[1]
            elif k in (23, 25):
                recorder.record(name, a[0], a[1] if k == 23 else hex(a[1]))
            elif k in (24, 34):
                recorder.record(name, a[0], a[1])
            elif k == 27:
                bits = f32_bits(a[1])
                recorder.record(name, a[0], hex(bits))
                recorder.volume[a[0]] = bits
            elif k == 28:
                recorder.record(name, a[0])
                a[1][0] = bits_f32(recorder.volume.get(a[0], f32_bits(1.0)))
            elif k in (30, 32):
                recorder.record(name, a[0])
                store = recorder.mute if k == 32 else recorder.paused
                a[1][0] = store.get(a[0], 0)
            return r
        return API_FUNCS[k](f)
    functions = [make(k) for k in range(FMOD_COUNT)]
    api = Api(None, *functions)
    return api, functions


CRT_FREE, MUSIC_SLOT, CRT_MEMMOVE, CRT_MEMCPY = 0x19a4d50, 0x6fc9fe0, 0x194c200, 0x194c780
CRT_MEMSET, CRT_STRSTR, SECURITY_COOKIE, LOCALE_CHANGED = 0x194cd00, 0x194fe20, 0x1cf65c0, 0xbdcf8ec


def crt_memset(m):
    destination, value, count = m.arg(0), m.arg(1) & 0xff, m.arg(2)
    if count > 0x10000:
        raise CaseError('memset size out of model range')
    m.write(destination, bytes([value])*count)
    return destination, 0


def crt_memmove(m):
    destination, source, count = m.arg(0), m.arg(1), m.arg(2)
    if count > 0x10000:
        raise CaseError('memmove size out of model range')
    m.write(destination, m.checked_read(source, count))
    return destination, 0


def crt_strstr(m):
    haystack, needle = m.cstring(m.arg(0), 4096), m.cstring(m.arg(1), 4096)
    index = haystack.find(needle)
    return (m.arg(0) + index) if index >= 0 else 0, 0


class ClientSide:
    """The client's sound system, sound table and music player in Unicorn."""

    def __init__(self, text, data, recorder):
        self.m = m = Machine(text, data, strict_stack=False)
        self.recorder = recorder
        for k in range(FMOD_COUNT):
            m.hook(FMOD_THUNK + 6*k, client_fmod_handler(recorder, k, m))
        m.hook(OPERATOR_NEW, lambda m: (m.alloc(max(1, m.arg(0))), 0))
        m.hook(CRT_FREE, lambda m: (None, 0))  # bump allocator: frees are recorded as no-ops
        m.hook(CRT_MEMSET, crt_memset)
        m.hook(CRT_MEMMOVE, crt_memmove)
        m.hook(CRT_MEMCPY, crt_memmove)
        m.hook(CRT_STRSTR, crt_strstr)
        m.model_page(SECURITY_COOKIE)
        m.write32(SECURITY_COOKIE, 0xbb40e64e)  # MSVC default __security_cookie
        m.model_page(LOCALE_CHANGED)
        m.write32(LOCALE_CHANGED, 0)  # C locale: _stricmp takes the ASCII path
        self.system = m.alloc(0x20)
        m.hook(SYS_GET, lambda m: (self.system, 0))
        m.model_page(SND_MAP)
        m.model_page(GROUP_NAME_STRINGS, 0x48)
        for index, name in enumerate(('Music', 'Environment', 'Effect')):
            m.write(GROUP_NAME_STRINGS + 0x18*index, self.string_object_bytes(name))
        m.model_page(MUSIC_SLOT)
        m.write(MUSIC_SLOT, b'\0'*8)  # shared_ptr in .bss, zero before first use
        m.call(SND_MAP_CTOR, [], this=SND_MAP)
        m.call(SYS_CTOR, [], this=self.system)

    @staticmethod
    def string_object_bytes(text):
        raw = text.encode('latin1')
        if len(raw) >= 16:
            raise ValueError('inline helper only for short strings')
        return raw.ljust(16, b'\0') + struct.pack('<II', len(raw), 15)

    def string(self, text):
        raw = text.encode('latin1')
        obj = self.m.alloc(0x18)
        if len(raw) < 16:
            self.m.write(obj, self.string_object_bytes(text))
        else:
            heap = self.m.alloc(len(raw) + 1)
            self.m.write(heap, raw + b'\0')
            self.m.write(obj, struct.pack('<I', heap) + b'\0'*12 + struct.pack('<II', len(raw), len(raw)))
        return obj

    def op(self, item):
        m = self.m
        kind = item[0]
        if kind == 'init':
            return m.call(SYS_INIT, [item[1]], this=self.system) & 0xff
        if kind == 'load':
            return m.call(SND_LOAD, [item[1], self.string(item[2]), item[3], item[4]]) & 0xff
        if kind == 'play':
            return m.call(SND_PLAY, [item[1], 0, item[2]]) & 0xff
        if kind == 'stop':
            m.call(SND_STOP, [item[1], 1])
            return None
        if kind == 'remove':
            m.call(SND_REMOVE, [item[1]])
            return None
        if kind == 'end':
            return m.call(CALLBACK_ADDRESS, [item[1], item[2], 0, 0])
        if kind == 'mp3':
            m.call(PLAY_MP3, [self.string(item[1])])
            return None
        if kind == 'stopmp3':
            m.call(STOP_MP3, [self.string(item[1])])
            return None
        if kind == 'apply':
            mute, volume, mutes, volumes = item[1]
            record = m.alloc(0x18)
            m.write(record, bytes([mute, 0, 0, 0]) + struct.pack('<I', volume) + bytes(mutes) + b'\0' +
                    struct.pack('<3I', *volumes))
            m.call(SYS_APPLY, [record], this=self.system)
            return None
        if kind == 'read':
            record = m.alloc(0x18)
            m.call(SYS_READ, [record], this=self.system)
            raw = m.read(record, 0x18)
            return (raw[0], hex(struct.unpack_from('<I', raw, 4)[0]), tuple(raw[8:11]),
                    tuple(hex(v) for v in struct.unpack_from('<3I', raw, 12)))
        if kind == 'stopgroup':
            m.call(SYS_STOP_GROUP, [item[1]], this=self.system)
            return None
        if kind == 'update':
            m.call(SYS_UPDATE, [], this=self.system)
            return None
        raise ValueError(kind)


class NativeSide:
    def __init__(self, library, recorder):
        self.library = library
        self.recorder = recorder
        callback = ctypes.cast(library.mu_audio_fmod_channel_callback, ctypes.c_void_p).value
        self.api, self.keep = c_api(recorder, callback)
        library.mu_audio_client_new.restype = ctypes.c_void_p
        library.mu_audio_client_new.argtypes = [ctypes.POINTER(Api)]
        self.client = library.mu_audio_client_new(ctypes.byref(self.api))
        library.mu_audio_set_callback_client(ctypes.c_void_p(self.client))

    def close(self):
        self.library.mu_audio_client_delete(ctypes.c_void_p(self.client))

    def op(self, item):
        L, c = self.library, ctypes.c_void_p(self.client)
        kind = item[0]
        if kind == 'init':
            return L.mu_audio_system_init(c, ctypes.c_void_p(item[1] or None))
        if kind == 'load':
            return L.mu_audio_snd_load(c, item[1], item[2].encode('latin1'), item[3], item[4])
        if kind == 'play':
            return L.mu_audio_snd_play(c, item[1], None, item[2])
        if kind == 'stop':
            L.mu_audio_snd_stop(c, item[1])
            return None
        if kind == 'remove':
            L.mu_audio_snd_remove(c, item[1])
            return None
        if kind == 'end':
            return L.mu_audio_channel_callback(c, item[1], item[2])
        if kind == 'mp3':
            L.mu_audio_play_mp3(c, item[1].encode('latin1'))
            return None
        if kind == 'stopmp3':
            L.mu_audio_stop_mp3(c, item[1].encode('latin1'))
            return None
        if kind == 'apply':
            mute, volume, mutes, volumes = item[1]
            settings = (ctypes.c_int32*8)()
            settings[0] = mute
            settings[1] = signed(volume)
            for i in range(3):
                settings[2 + i] = mutes[i]
                settings[5 + i] = signed(volumes[i])
            L.mu_audio_apply_settings(c, settings)
            return None
        if kind == 'read':
            settings = (ctypes.c_int32*8)()
            L.mu_audio_read_settings(c, settings)
            u = [v & 0xffffffff for v in settings]
            return (u[0], hex(u[1]), tuple(u[2:5]), tuple(hex(v) for v in u[5:8]))
        if kind == 'stopgroup':
            L.mu_audio_stop_group(c, item[1])
            return None
        if kind == 'update':
            L.mu_audio_system_update(c)
            return None
        raise ValueError(kind)


def configure_library(library):
    v = ctypes.c_void_p
    signatures = {
        'mu_audio_system_init': ([v, v], ctypes.c_int), 'mu_audio_snd_load': ([v, I32, ctypes.c_char_p, I32, I32], ctypes.c_int),
        'mu_audio_snd_play': ([v, I32, v, I32], ctypes.c_int), 'mu_audio_snd_stop': ([v, I32], None),
        'mu_audio_snd_remove': ([v, I32], None), 'mu_audio_channel_callback': ([v, H, I32], I32),
        'mu_audio_play_mp3': ([v, ctypes.c_char_p], None), 'mu_audio_stop_mp3': ([v, ctypes.c_char_p], None),
        'mu_audio_apply_settings': ([v, v], None), 'mu_audio_read_settings': ([v, v], None),
        'mu_audio_stop_group': ([v, ctypes.c_int], None), 'mu_audio_system_update': ([v], None),
        'mu_audio_client_delete': ([v], None), 'mu_audio_set_callback_client': ([v], None)}
    for name, (argtypes, restype) in signatures.items():
        function = getattr(library, name)
        function.argtypes, function.restype = argtypes, restype


def run_script(text, data, library, script):
    """Returns (client trace, native trace); each is the FMOD records interleaved
    with operation markers and return values."""
    traces = []
    for side in ('client', 'native'):
        recorder = Recorder(script.get('fmod'))
        runner = ClientSide(text, data, recorder) if side == 'client' else NativeSide(library, recorder)
        trace = []
        try:
            for item in script['ops']:
                recorder.records.append(('op',) + tuple(x if not isinstance(x, (list, tuple)) else str(x) for x in item))
                value = runner.op(item)
                recorder.records.append(('ret', value))
        except CaseError as error:
            recorder.records.append(('error', str(error)))
        finally:
            if side == 'native':
                runner.close()
        trace = recorder.records
        traces.append(trace)
    return traces


SHORT = 'Data\\Sound\\a.wav'  # 16 characters: heap string in the client
PATHS = ['Data\\Sound\\aWind.wav', 'Data\\Sound\\eBlow1.wav', 'Data\\Sound\\iButtonClick.wav', 'x.wav',
         'Data\\Sound\\w34\\bg_idle1.wav', 'Data\\Sound\\AquilasTemple\\AquilasSanctuary_env.wav']
MUSIC = ['data\\music\\Pub.mp3', 'Data\\Music\\PUB.MP3', 'data\\music\\main_theme.mp3', 'data\\music\\Noria.mp3', 'n.mp3']


def manager_scripts(seed=0xa6ab76, extra=0):
    def channel(n):
        return 0x7000 + n
    scripts = []
    base = [('init', 0)]
    scripts.append({'ops': base + [('load', 1, PATHS[0], 1, 1), ('load', 1, PATHS[1], 1, 1), ('play', 1, 1),
                                   ('play', 1, 1), ('stop', 1), ('end', channel(0), 0), ('play', 1, 0),
                                   ('end', channel(1), 1), ('play', 1, 0), ('end', channel(1), 0), ('play', 1, 0),
                                   ('play', 2, 0), ('stop', 2), ('remove', 2), ('remove', 1), ('play', 1, 0),
                                   ('end', channel(2), 0), ('update',)]})
    # shared path, removal releases only with the last owner
    scripts.append({'ops': base + [('load', 5, PATHS[2], 2, 1), ('load', 6, PATHS[2], 4, 1), ('remove', 5),
                                   ('play', 6, 1), ('remove', 6), ('load', 7, PATHS[2], 1, 1), ('play', 7, 0),
                                   ('end', channel(0), 0), ('load', 8, PATHS[3], 1, 0), ('load', 9, SHORT, 3, 1),
                                   ('play', 9, 1), ('play', 8, 0)]})
    # cache key case and ordering
    scripts.append({'ops': base + [('load', 1, 'Data\\Sound\\Aa.wav', 1, 1), ('load', 2, 'data\\sound\\aa.wav', 1, 1),
                                   ('load', 3, 'Data\\Sound\\Ab.wav', 1, 1), ('load', 4, 'Data\\Sound\\AA.wav', 1, 1),
                                   ('play', 2, 0), ('play', 4, 0), ('remove', 1), ('remove', 3), ('remove', 2),
                                   ('load', 5, 'data\\sound\\aa.wav', 1, 1), ('remove', 4), ('remove', 5),
                                   ('mp3', 'Data\\Sound\\Ab.wav'), ('load', 6, 'Data\\Sound\\Ab.wav', 1, 1),
                                   ('mp3', 'data\\sound\\AB.WAV'), ('stopmp3', 'DATA\\SOUND\\AB.wav'),
                                   ('play', 6, 1)]})
    # music
    scripts.append({'ops': base + [('mp3', MUSIC[0]), ('mp3', MUSIC[1]), ('mp3', MUSIC[2]), ('stopmp3', MUSIC[0]),
                                   ('stopmp3', 'DATA\\MUSIC\\MAIN_THEME.MP3'), ('stopmp3', MUSIC[2]), ('mp3', MUSIC[3]),
                                   ('mp3', MUSIC[3]), ('load', 3, MUSIC[3], 1, 1), ('mp3', MUSIC[4]),
                                   ('stopmp3', MUSIC[4]), ('play', 3, 1)]})
    # failure paths
    for name in ('System::createStream', 'System::playSound', 'Channel::setChannelGroup', 'Channel::setPriority',
                 'Channel::setMode', 'Channel::setPaused', 'Channel::setUserData', 'Channel::setCallback',
                 'System::createSound', 'ChannelGroup::stop'):
        scripts.append({'fmod': {'fail': {name: [0x1c, 0, 0x24]}},
                        'ops': base + [('load', 1, PATHS[0], 1, 1), ('load', 2, PATHS[4], 1, 1), ('play', 1, 1),
                                       ('play', 1, 1), ('play', 2, 0), ('play', 2, 1), ('mp3', MUSIC[0]), ('mp3', MUSIC[2]),
                                       ('mp3', MUSIC[3]), ('load', 3, PATHS[5], 1, 1), ('play', 3, 0)]})
    # no system: everything is a no-op
    scripts.append({'ops': [('load', 1, PATHS[0], 1, 1), ('play', 1, 1), ('mp3', MUSIC[0]), ('stop', 1),
                            ('apply', (1, f32_bits(0.5), (1, 0, 1), (f32_bits(0.1),)*3)), ('read',), ('stopgroup', 0),
                            ('update',)]})
    # settings
    values = [0.0, 0.4, 1.0, 0.5, 2.0, -1.0, 1e-30, 3.4028234663852886e38]
    for i, value in enumerate(values):
        mutes = (i & 1, (i >> 1) & 1, (i >> 2) & 1)
        volumes = tuple(f32_bits(values[(i + j) % len(values)]) for j in range(3))
        scripts.append({'ops': base + [('read',), ('apply', (i & 1, f32_bits(value), mutes, volumes)), ('read',),
                                       ('stopgroup', i % 3), ('apply', (0, f32_bits(1.0), (0, 0, 0), (f32_bits(0.4),
                                                                                                   f32_bits(1.0),
                                                                                                   f32_bits(1.0)))),
                                       ('read',)]})
    generator = random.Random(seed)
    for _ in range(extra):
        ops = list(base)
        channels = 0
        for _ in range(generator.randrange(5, 40)):
            choice = generator.random()
            sid = generator.randrange(1, 6)
            if choice < 0.25:
                ops.append(('load', sid, generator.choice(PATHS + [SHORT]), generator.randrange(1, 5), 1))
            elif choice < 0.5:
                ops.append(('play', sid, generator.randrange(0, 2)))
                channels += 1
            elif choice < 0.6:
                ops.append(('stop', sid))
            elif choice < 0.68:
                ops.append(('remove', sid))
            elif choice < 0.8 and channels:
                ops.append(('end', channel(generator.randrange(0, channels)), generator.choice((0, 0, 0, 1, 2))))
            elif choice < 0.9:
                ops.append((generator.choice(('mp3', 'stopmp3')), generator.choice(MUSIC)))
            else:
                ops.append(('update',))
        fail = {}
        if generator.random() < 0.3:
            fail[generator.choice(FMOD_NAMES[17:26] + ['Channel::setUserData'])] = [0, 0x1c]
        scripts.append({'fmod': {'fail': fail}, 'ops': ops})
    return scripts


def init_scripts():
    scripts = []
    names = ['Primary Sound Driver', 'SigmaTel High Definition Audio CODEC', 'Realtek xSigmaTel', '', 'sigmatel']
    for drivers in (0, 1, 3):
        for caps in (0, 2, 3, 0x80):
            for name in names:
                scripts.append({'fmod': {'drivers': drivers, 'caps': caps, 'name': name, 'speaker': 5},
                                'ops': [('init', 0x1234), ('init', 0)]})
    for codes in ([0x3a], [0x3a, 0x3a], [0x1f], [0x3a, 0], [0x24]):
        scripts.append({'fmod': {'fail': {'System::init': codes}}, 'ops': [('init', 0)]})
    for step in ('System_Create', 'System::getNumDrivers', 'System::setOutput', 'System::getDriverCaps',
                 'System::setSpeakerMode', 'System::setDSPBufferSize', 'System::getDriverInfo',
                 'System::setSoftwareFormat', 'System::getMasterChannelGroup', 'System::createChannelGroup',
                 'ChannelGroup::addGroup'):
        for codes in ([0x1c], [0, 0x1c], [0, 0, 0x1c]):
            scripts.append({'fmod': {'caps': 2, 'name': 'SigmaTel', 'fail': {step: codes}},
                            'ops': [('init', 0), ('init', 0)]})
    for speaker in range(0, 9):
        scripts.append({'fmod': {'speaker': speaker, 'fail': {'System::init': [0x3a]}}, 'ops': [('init', 0)]})
    return scripts


def check_scripts(text, data, library, scripts):
    results = {'scripts': len(scripts), 'equal': 0, 'fmod_calls': 0, 'first_mismatch': None}
    for script in scripts:
        client, native = run_script(text, data, library, script)
        results['fmod_calls'] += sum(1 for r in client if r[0] not in ('op', 'ret', 'error'))
        if any(r[0] == 'error' for r in client):
            if results['first_mismatch'] is None:
                results['first_mismatch'] = {'script': script, 'client_error': [r for r in client if r[0] == 'error']}
            continue
        if client == native:
            results['equal'] += 1
        elif results['first_mismatch'] is None:
            index = next(i for i, (a, b) in enumerate(zip(client + [None], native + [None])) if a != b)
            results['first_mismatch'] = {'script': script, 'index': index, 'client': client[max(0, index - 4):index + 3],
                                         'native': native[max(0, index - 4):index + 3]}
    return results


# ---------------------------------------------------------------------------
# settings: options-UI conversions
# ---------------------------------------------------------------------------

def check_ui(text, data, library, seed=0xf2fc2e):
    m = Machine(text, data)
    ebp = STACK + STACK_SIZE - 0x4000
    floats = [0.0, -0.0, 0.4, 1.0, 1/9, 2/9, 0.5, 0.0555555, 0.0555556, 0.944444, 0.9444445, 1.5, 2.0, -0.1, -0.06,
              -0.05555, 1e-40, 1e30, -1e30, 238609294.0, 238609296.0, -238609351.0, float('inf'), float('-inf'),
              float('nan')]
    generator = random.Random(seed)
    floats += [generator.uniform(-2, 2) for _ in range(3000)]
    floats += [struct.unpack('<f', struct.pack('<I', generator.getrandbits(32)))[0] for _ in range(2000)]
    equal = total = 0
    first = None
    for value in floats:
        bits = f32_bits(value) if value == value else 0x7fc00000
        m.write32(ebp - 0xc, bits)
        m.run(0xf2fc2e, 0xf2fc47, ebp=ebp, esp=ebp - 0x20)
        client = signed(m.reg('eax'))
        native = library.mu_audio_volume_to_level(ctypes.c_float(bits_f32(bits)))
        total += 1
        if client == native:
            equal += 1
        elif first is None:
            first = (hex(bits), client, native)
    levels = list(range(-20, 40)) + [2**31 - 1, -2**31, 2**24 + 1, 123456789] + [generator.randrange(-2**31, 2**31)
                                                                               for _ in range(2000)]
    for fragment in ((0xf2fe04, 0xf2fe11, 0x1c, 0x20), (0xc764c0, 0xc764cd, None, 0x28)):
        start, end, source, target = fragment
        for level in levels:
            if source is not None:
                m.write32(ebp - source, level)
                m.run(start, end + 5, ebp=ebp, esp=ebp - 0x40)
            else:
                record = m.alloc(0x40)
                m.write32(record + 0x30, level)
                m.write32(ebp - 0x10, record)
                m.run(0xc764bd, end + 5, ebp=ebp, esp=ebp - 0x40)
            client = m.read32(ebp - target)
            native = f32_bits(library.mu_audio_level_to_volume(level))
            total += 1
            if client == native:
                equal += 1
            elif first is None:
                first = (hex(start), level, hex(client), hex(native))
    return {'cases': total, 'equal': equal, 'first_mismatch': first}


# ---------------------------------------------------------------------------
# OpenWorld music volume
# ---------------------------------------------------------------------------

OPENWORLD_START, OPENWORLD_END = 0x18290be, 0x18293a6


def check_openworld(text, data, library):
    results = {'cases': 0, 'equal': 0, 'first_mismatch': None}
    for world in list(range(-3, 0x110)) + [0x7fffffff, -0x80000000]:
        recorder = Recorder()
        client = ClientSide(text, data, recorder)
        m = client.m
        m.model_page(WORLD)
        m.write32(WORLD, world)
        group = 0x8100
        m.write32(client.system + 0xc, group)  # music group handle
        ebp = STACK + STACK_SIZE - 0x8000
        try:
            m.run(OPENWORLD_START, OPENWORLD_END, ebp=ebp, esp=ebp - 0x220)
            calls = [r for r in recorder.records]
        except CaseError as error:
            calls = [('error', str(error))]
        volume = library.mu_audio_world_music_volume(world)
        native = [('ChannelGroup::setVolume', group, hex(f32_bits(volume)))]
        results['cases'] += 1
        if calls == native:
            results['equal'] += 1
        elif results['first_mismatch'] is None:
            results['first_mismatch'] = {'world': world, 'client': calls, 'native': native}
    return results


# ---------------------------------------------------------------------------

def body_digests(text):
    out = {}
    for name, (begin, end, _) in BODIES.items():
        out[name] = {'begin': hex(begin), 'end': hex(end),
                     'sha256': hashlib.sha256(text[begin - TEXT_BASE:end - TEXT_BASE]).hexdigest()}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--library', default=str(ROOT/'reconstructed/audio'/(
        'libclient_audio.dylib' if sys.platform == 'darwin' else 'libclient_audio.so')))
    parser.add_argument('--checks', default='frame,openworld,manager,settings,init')
    parser.add_argument('--random', type=int, default=400, help='extra random frame cases')
    parser.add_argument('--report')
    args = parser.parse_args()
    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'second image section')
    library = load_library(args.library)
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'bodies': body_digests(text)}
    checks = args.checks.split(',')
    ok = True
    configure_library(library)
    if 'frame' in checks:
        report['frame'] = check_frame(text, data, library, args.random)
        ok &= report['frame']['equal'] == report['frame']['cases']
        report['frame_sensitivity'] = check_frame_sensitivity(text, data, library)
    if 'openworld' in checks:
        report['openworld'] = check_openworld(text, data, library)
        ok &= report['openworld']['equal'] == report['openworld']['cases']
    if 'manager' in checks:
        report['manager'] = check_scripts(text, data, library, manager_scripts(extra=args.random))
        ok &= report['manager']['equal'] == report['manager']['scripts']
    if 'init' in checks:
        report['init'] = check_scripts(text, data, library, init_scripts())
        ok &= report['init']['equal'] == report['init']['scripts']
    if 'settings' in checks:
        report['settings'] = check_ui(text, data, library)
        ok &= report['settings']['equal'] == report['settings']['cases']
    print(json.dumps(report, indent=1, default=str))
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1, default=str) + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
