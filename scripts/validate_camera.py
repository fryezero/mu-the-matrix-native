#!/usr/bin/env python3
"""Compare the reconstructed camera, picking, input and frame-timing code
(reconstructed/camera) with the client's own instructions in Unicorn.

The pinned restored text and second image section are executed unchanged.
Global variables of the uncaptured data/BSS sections are synthetic inputs:
the harness defines every byte it provides and stops a case at the first
read of a byte that neither it nor the guest has written. OpenGL, user32
and kernel32 imports are replaced by recorded stubs (they are not client
code). A few client callees outside the validated routines (subsystem
queries of MoveMainCamera) are replaced by synthetic returns; each is
listed in CLIENT_STUBS with its reason. Every result is compared bit for
bit with the C library built from reconstructed/camera.
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

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
FLAG_ADDRESS = 0x0bdd1cc8
FLAG_SHA256 = '67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450'

# Routine bodies pinned by SHA-256 of the restored bytes (start, length, digest).
ROUTINES = {
    'perspective2': (0x01849d76, 0x14e, 'ae02d1afeb2da70a924ff8b2a35dda153c1549d8f5521c71e74e650fd1920ed5'),
    'viewport2': (0x01849ec4, 0x44, 'da6c48cbb3de32a011c47b9e0b6b464ac97234fefeb086d4a5074571d6c41f2d'),
    'create_screen_vector': (0x01849f08, 0x287, 'a916d36d603eb740e7aac5c939b49bc1868601af4d2cb611d9b61ed79c48c981'),
    'projection': (0x0184a244, 0xa4, 'c4b94ebf6f3153e4c3b4d1ec7d3696734f977b6e7fa366b88e1d5be1a4491218'),
    'projection_float_scaled': (0x0184a2e8, 0xe6, 'fc6395bc22b7a508aaa17e2579ac8981978bb5ce19649a658db9827e14802061'),
    'projection_float': (0x0184a3ce, 0x87, '7de05f1f27a15249be57b183d5cf321749a196071678212403a569475d73d9bb'),
    'transform_position': (0x0184a455, 0x114, '9c17e64c2ca3d134c75e5510583dcdf20a883c7f2ad9f276dd06ebec4ac2d20b'),
    'camera_matrix_read': (0x0184a569, 0x5e, '7a0c23ef6ec2f294713e9dfbb38089f3ec2a62ac0a15fcfa5d36239d3f52a4ba'),
    'begin_opengl': (0x0184adc7, 0x4b7, '3f42f777a59ae6d2a872e5b4e54c38e1727600624221dd4c5753e792f453dbfe'),
    'collision_line_face': (0x0184f96c, 0x753, '58338a1d0cac11593209d02db3b5394d59ab0efe31c3f45ee0f2149d588a3009'),
    'inside_test': (0x018506bc, 0x6cc, '9e351baf03214e54a80a656ea6a64e1863715647ea51641ea5e1fde1d4c3c148'),
    'face_normalize': (0x00d01206, 0x2c3, '65ffdcf0493c3e4df861b6a8822c5084b13acbc408f902b2d25c38cfb64c4056'),
    'terrain_tile': (0x016ccda5, 0x6c3, '331b9d1013b9ce7ec588b72dfdccfe827d0d12074d7cbc1e53c8da2f1054d8fd'),
    'key_scan': (0x00ec5475, 0x102, 'd72363ecd2a0cb5ad3164bf6a297fd666a542b2e54f37b4b523330cc9e2398cd'),
    'key_none': (0x00ec5577, 0x35, 'c7e32fb8dc913dab93e4fa3819b7d9bd5b37563e767ed18437b81bd1fae01570'),
    'key_release': (0x00ec55ac, 0x36, 'ae05155334952102b687bda00cb560dbc29d43814c34c15ea8e6263a47fa8688'),
    'key_press': (0x00ec55e2, 0x36, 'f371ed22a02f84af076669bce55cb8df22e4ffda5de5ca734c7815bc300c459c'),
    'key_repeat': (0x00ec5618, 0x36, 'a5ae15dc44c1470dda7400c30e060990fa7cecfd089b4131f6eac980d4d91984'),
    'lerp_steps': (0x0185047d, 0x49, '0bbccdfa913bef1c716591ad509f3570d426e5901154a02d3cc7bf4f121f0d39'),
    'ease': (0x018504c6, 0x150, 'd2f055e3d5aa20677a8c4662dba292af51be7c03d4cf556af491a5b940326c91'),
    'timer_elapsed': (0x018519ff, 0x3d, '43c972ba9d5c90d9838a0c3a0d4651499acc608d646b33c84b271ed04542bb62'),
    'timer_update': (0x00c9b4ac, 0x5c, '2e0dd3d10e2d24fbe76b6481afd6d26c29d6e322401a289b43abe0c7f98c5630'),
    'move_main_camera': (0x0185498e, 0x17b0, '8371198dddd234a637e57af47ac8addd8a81af38d16c5d7de5b0312c89fcf1af'),
    'apply_zoom': (0x0185a9bf, 0x3a4, 'd9b202280a35473a27f4713749d61661b381f77032023e248a993a5df682d304'),
    'wheel_zoom': (0x018588d9, 0x7f, 'da984d70655674d5231d53e72a013cccc548210c0bcf096010b90e03f17101a0'),
    'wndproc': (0x0120fee3, 0x11f4, 'c254c927d726bb1953f52ef645fb683cfe5ab2b5bd4a77585d89a43e2de25ce2'),
    'frame_driver': (0x01851d39, 0x2b40, '0eba991acabc255801dc7a47e9fc0d4fd51312d2fce43d6774e8c2ea6fafd003'),
}

# Import slots used by the routines (names from the Wine export match of
# docs/research/client-frame-loop.md and client-skinning.md; stdcall argument
# counts from the API signatures).
IMPORTS = {
    0x01a7c714: ('glMatrixMode', 1), 0x01a7c718: ('glPushMatrix', 0), 0x01a7c6e4: ('glLoadIdentity', 0),
    0x01a7c6d4: ('glViewport', 4), 0x01a7c174: ('gluPerspective', 8), 0x01a7c654: ('glRotatef', 4),
    0x01a7c698: ('glTranslatef', 3), 0x01a7c758: ('glDisable', 1), 0x01a7c75c: ('glEnable', 1),
    0x01a7c740: ('glDepthMask', 1), 0x01a7c6bc: ('glDepthFunc', 1), 0x01a7c6d0: ('glAlphaFunc', 2),
    0x01a7c670: ('glFogi', 2), 0x01a7c724: ('glFogf', 2), 0x01a7c69c: ('glFogfv', 2),
    0x01a7c784: ('glGetFloatv', 2), 0x01a7c49c: ('GetTickCount', 0), 0x01a7c4a0: ('Sleep', 1),
    0x01a7c7bc: ('GetAsyncKeyState', 1), 0x01a7c7b8: ('GetForegroundWindow', 0), 0x01a7c840: ('GetFocus', 0),
}

STACK, STACK_SIZE = 0x30000000, 0x20000
RETURN = 0x31000000
ARENA, ARENA_SIZE = 0x32000000, 0x40000
STUBS = 0x33000000
CRT_MATH_MODE = 0x0bdcfbc8
SECURITY_COOKIE = 0x01cf65c0
TEB, GDT = 0x34000000, 0x35000000  # fs:[0] exception-list head for the SEH prologues
BSS = ((0x01ced000, 0x00200000), (0x06f00000, 0x00100000), (0x0a300000, 0x01b00000))
INITIAL_ESP = STACK + STACK_SIZE - 0x1000
FPCW, MXCSR = 0x027f, 0x1f80


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(bits):
    return struct.unpack('<f', struct.pack('<I', bits & 0xffffffff))[0]


def same(a, b):
    """Bitwise equality of binary32 values. NaNs compare equal to NaNs: the
    payload/sign of a generated default NaN is a host property (x86 produces
    0xffc00000, arm64 0x7fc00000) and is not reproduced."""
    if math.isnan(a) and math.isnan(b):
        return True
    return fbits(a) == fbits(b)


def load_pinned(path, size, digest, label):
    payload = Path(path).read_bytes()
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input does not match pinned {label}')
    return payload


class Stop(Exception):
    pass


class Guest:
    """Restored client image in Unicorn with strict read tracking."""

    def __init__(self, text, data, flag):
        import unicorn
        from unicorn import x86_const
        self.u = unicorn
        self.x = x86_const
        self.text, self.data = text, data
        uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
        self.uc = uc
        uc.mem_map(TEXT_BASE, (TEXT_BYTES + 0xfff) & ~0xfff, unicorn.UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES + 0xfff) & ~0xfff, unicorn.UC_PROT_ALL)
        uc.mem_write(DATA_BASE, data)
        self.tracked = []
        for base, size in BSS + ((STACK, STACK_SIZE), (ARENA, ARENA_SIZE), (TEB, 0x1000)):
            uc.mem_map(base, size, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
            self.tracked.append((base, size, bytearray(size)))
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
        self.flag = flag
        self.imports = {}
        self.client_stubs = {}
        self.client_values = {}
        self._constant_cache = {}
        self.calls = []
        self.violation = None
        self.handler = {}
        for index, (slot, (name, count)) in enumerate(sorted(IMPORTS.items())):
            address = STUBS + 0x10 * index
            uc.mem_write(address, b'\xc3')
            uc.mem_write(slot, struct.pack('<I', address))
            self.imports[address] = (name, count)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._import, begin=STUBS, end=STUBS + 0x10 * len(IMPORTS))
        for base, size, shadow in self.tracked:
            uc.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE, self._access, begin=base,
                        end=base + size - 1, user_data=shadow)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._readonly_write, begin=TEXT_BASE, end=DATA_BASE + DATA_BYTES)
        uc.hook_add(unicorn.UC_HOOK_MEM_UNMAPPED, self._unmapped)
        for address, (cleanup, reason) in CLIENT_STUBS.items():
            self.stub_client(address, cleanup, lambda args, ecx, a=address: self.client_values.get(a, 0), reason=reason)
        self.reset_memory()

    # ---- memory ----
    def reset_memory(self):
        for base, size, shadow in self.tracked:
            self.uc.mem_write(base, b'\x00' * size)
            shadow[:] = bytes(size)
        self.put(FLAG_ADDRESS, self.flag)
        self.put(TEB, struct.pack('<I', 0xffffffff))
        # CRT math error-mode word read after x87 sqrt/trig (0x019998a5); its live
        # value is not captured. With the default control word both values return
        # the same result, so cases alternate 0 and 1.
        self.crt_mode = getattr(self, 'crt_mode', 1) ^ 1
        self.put(CRT_MATH_MODE, struct.pack('<I', self.crt_mode))
        # /GS security cookie read by the SEH4 prologue of the CRT array
        # constructor iterator; any value works (MSVC default seed used).
        self.put(SECURITY_COOKIE, struct.pack('<I', 0xbb40e64e))

    def _region(self, address):
        for base, size, shadow in self.tracked:
            if base <= address < base + size:
                return base, shadow
        return None, None

    def put(self, address, payload):
        self.uc.mem_write(address, payload)
        base, shadow = self._region(address)
        if shadow is not None:
            shadow[address - base:address - base + len(payload)] = b'\x01' * len(payload)

    def put_f(self, address, *values):
        self.put(address, struct.pack(f'<{len(values)}f', *values))

    def put_i(self, address, *values):
        self.put(address, struct.pack(f'<{len(values)}i', *values))

    def put_u(self, address, *values):
        self.put(address, struct.pack(f'<{len(values)}I', *values))

    def get(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def get_f(self, address, count=1):
        values = struct.unpack(f'<{count}f', self.get(address, 4 * count))
        return values if count > 1 else values[0]

    def get_i(self, address, count=1):
        values = struct.unpack(f'<{count}i', self.get(address, 4 * count))
        return values if count > 1 else values[0]

    def _access(self, uc, access, address, size, value, shadow):
        base = None
        for b, s, sh in self.tracked:
            if sh is shadow:
                base = b
        offset = address - base
        if access == self.u.UC_MEM_WRITE:
            shadow[offset:offset + size] = b'\x01' * size
            return
        if b'\x00' in shadow[offset:offset + size] and self.violation is None:
            if self._constant_store(uc.reg_read(self.x.UC_X86_REG_EIP)):
                return
            self.violation = ('undefined-read', hex(address), size, hex(uc.reg_read(self.x.UC_X86_REG_EIP)))
            uc.emu_stop()

    def _constant_store(self, eip):
        """`and [m], 0` / `or [m], -1` read memory but store a constant (MSVC /Od
        initialises locals and EH states this way); they do not consume the value."""
        if eip not in self._constant_cache:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32
            if not hasattr(self, '_decoder'):
                self._decoder = Cs(CS_ARCH_X86, CS_MODE_32)
            ins = next(self._decoder.disasm(bytes(self.uc.mem_read(eip, 16)), eip), None)
            self._constant_cache[eip] = ins is not None and (
                (ins.mnemonic == 'and' and ins.op_str.endswith(', 0'))
                or (ins.mnemonic == 'or' and ins.op_str.endswith(', 0xffffffff')))
        return self._constant_cache[eip]

    def _readonly_write(self, uc, access, address, size, value, ignored):
        if self.violation is None:
            self.violation = ('image-write', hex(address), size, hex(uc.reg_read(self.x.UC_X86_REG_EIP)))
            uc.emu_stop()

    def _unmapped(self, uc, access, address, size, value, ignored):
        if self.violation is None:
            self.violation = ('unmapped', hex(address), size, hex(uc.reg_read(self.x.UC_X86_REG_EIP)))
        return False

    # ---- stubs ----
    def _args(self, count):
        esp = self.uc.reg_read(self.x.UC_X86_REG_ESP)
        raw = self.get(esp, 4 + 4 * count)
        return esp, struct.unpack(f'<{count + 1}I', raw)

    def _import(self, uc, address, size, ignored):
        if address not in self.imports:
            return
        name, count = self.imports[address]
        esp, words = self._args(count)
        args = words[1:]
        handler = self.handler.get(name)
        result = handler(args) if handler else 0
        self.calls.append((name, args))
        uc.reg_write(self.x.UC_X86_REG_EAX, (result or 0) & 0xffffffff)
        uc.reg_write(self.x.UC_X86_REG_ESP, esp + 4 + 4 * count)
        uc.reg_write(self.x.UC_X86_REG_EIP, words[0])

    def stub_client(self, address, cleanup, result, kind='eax', reason=''):
        """Replace a client callee: result(args_words, ecx) gives eax or a float (x87).
        The snippet code is written once; only its data word changes per call
        (translated blocks are not invalidated by writes made from hooks)."""
        index = len(self.client_stubs)
        snippet = STUBS + 0x8000 + 0x20 * index
        data = snippet + 0x18
        tail = b'\xc3' if cleanup == 0 else b'\xc2' + struct.pack('<H', cleanup)
        load = b'\xa1' if kind == 'eax' else b'\xd9\x05'   # mov eax, [data] / fld dword [data]
        self.uc.mem_write(snippet, load + struct.pack('<I', data) + tail)
        self.client_stubs[address] = (snippet, data, result, kind)
        self.uc.hook_add(self.u.UC_HOOK_CODE, self._client, begin=address, end=address)

    def _client(self, uc, address, size, ignored):
        if address not in self.client_stubs:
            return
        snippet, data, result, kind = self.client_stubs[address]
        esp, words = self._args(4)
        value = result(words[1:], uc.reg_read(self.x.UC_X86_REG_ECX))
        uc.mem_write(data, struct.pack('<I', value & 0xffffffff) if kind == 'eax' else struct.pack('<f', value))
        self.calls.append((hex(address), words[1:]))
        uc.reg_write(self.x.UC_X86_REG_EIP, snippet)

    # ---- execution ----
    def call(self, start, words, ecx=0, until=RETURN, count=200000, xmm_poison=True):
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
        if xmm_poison:
            for index in range(8):
                uc.reg_write(getattr(x, f'UC_X86_REG_XMM{index}'), 0x7ff4dead5eed0000 * (index + 1) & ((1 << 128) - 1))
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

    def st0(self):
        top = (self.uc.reg_read(self.x.UC_X86_REG_FPSW) >> 11) & 7
        mantissa, high = self.uc.reg_read(self.x.UC_X86_REG_FP0 + top)
        sign = -1.0 if high & 0x8000 else 1.0
        exponent = high & 0x7fff
        if exponent == 0x7fff:
            return math.copysign(math.inf, sign) if mantissa == 1 << 63 else math.nan
        if mantissa == 0:
            return math.copysign(0.0, sign)
        return sign * math.ldexp(mantissa, exponent - 16383 - 63)

    def arena(self, payload, offset):
        address = ARENA + offset
        self.put(address, payload)
        return address


# ---------------- C library ----------------

class View(ctypes.Structure):
    _fields_ = [('window_width', ctypes.c_uint32), ('window_height', ctypes.c_uint32),
                ('screen_x', ctypes.c_int32), ('screen_y', ctypes.c_int32),
                ('screen_width', ctypes.c_int32), ('screen_height', ctypes.c_int32),
                ('center_x', ctypes.c_int32), ('center_y', ctypes.c_int32), ('center_y_flip', ctypes.c_int32),
                ('perspective_x', ctypes.c_float), ('perspective_y', ctypes.c_float),
                ('fov', ctypes.c_float), ('view_near', ctypes.c_float), ('view_far', ctypes.c_float),
                ('angle', ctypes.c_float * 3), ('position', ctypes.c_float * 3), ('top_view', ctypes.c_uint8),
                ('camera_matrix', ctypes.c_float * 12), ('mouse_position', ctypes.c_float * 3),
                ('mouse_target', ctypes.c_float * 3), ('gl_viewport', ctypes.c_int32 * 4),
                ('projection', ctypes.c_float * 16), ('modelview', ctypes.c_float * 16)]


class Pick(ctypes.Structure):
    _fields_ = [('nearest', ctypes.c_float), ('collision', ctypes.c_float * 3)]


class Terrain(ctypes.Structure):
    _fields_ = [('height', ctypes.POINTER(ctypes.c_float)), ('wall', ctypes.POINTER(ctypes.c_uint16)),
                ('water_height', ctypes.c_float)]


class Timer(ctypes.Structure):
    _fields_ = [('start', ctypes.c_uint32), ('duration', ctypes.c_uint32), ('done', ctypes.c_uint8)]


class WorldCamera(ctypes.Structure):
    _fields_ = [('scene', ctypes.c_int32), ('world', ctypes.c_int32), ('hero_position', ctypes.c_float * 3),
                ('hero_tile_x', ctypes.c_int32), ('hero_tile_y', ctypes.c_int32), ('hero_byte4', ctypes.c_uint8),
                ('hero_tile_wall', ctypes.c_uint16), ('camera_override', ctypes.c_float * 3),
                ('world_fov', ctypes.c_float), ('far_scale', ctypes.c_float * 3), ('event_world', ctypes.c_uint8),
                ('zoom_object_active', ctypes.c_uint8), ('zoom_object_level', ctypes.c_int16),
                ('far_2300', ctypes.c_uint8), ('zoom_level5_distance', ctypes.c_float),
                ('water_height', ctypes.c_float), ('earthquake', ctypes.c_float), ('world_time', ctypes.c_float),
                ('distance', ctypes.c_float), ('distance_target', ctypes.c_float), ('zoom_level', ctypes.c_int16),
                ('lift', ctypes.c_float), ('fov_from', ctypes.c_float), ('fov_to', ctypes.c_float),
                ('angle_start', ctypes.c_float * 3), ('angle_end', ctypes.c_float * 3),
                ('position_start', ctypes.c_float * 3), ('position_end', ctypes.c_float * 3),
                ('zoom_timer', Timer), ('zoom_index', ctypes.c_int32)]


class KeyInput(ctypes.Structure):
    _fields_ = [('state', ctypes.c_uint8 * 256)]


class KeySample(ctypes.Structure):
    _fields_ = [('active', ctypes.c_uint8), ('down', ctypes.c_uint8 * 256), ('game_foreground', ctypes.c_uint8),
                ('focus_is_foreground', ctypes.c_uint8), ('key_message_down', ctypes.c_uint8)]


class Mouse(ctypes.Structure):
    _fields_ = [('x', ctypes.c_int32), ('y', ctypes.c_int32), ('scale_x', ctypes.c_float), ('scale_y', ctypes.c_float),
                ('left', ctypes.c_uint8), ('left_push', ctypes.c_uint8), ('left_pop', ctypes.c_uint8),
                ('left_double', ctypes.c_uint8), ('right', ctypes.c_uint8), ('right_push', ctypes.c_uint8),
                ('right_pop', ctypes.c_uint8), ('middle', ctypes.c_uint8), ('middle_push', ctypes.c_uint8),
                ('middle_pop', ctypes.c_uint8), ('wheel', ctypes.c_int32), ('last_click_x', ctypes.c_int32),
                ('last_click_y', ctypes.c_int32), ('idle', ctypes.c_int32)]


class Clock(ctypes.Structure):
    _fields_ = [('accumulator', ctypes.c_int32), ('frame_tick', ctypes.c_uint32), ('logic_steps', ctypes.c_uint32),
                ('frames', ctypes.c_uint32), ('pending', ctypes.c_int32), ('previous_tick', ctypes.c_uint32)]


def load_library(directory=None):
    directory = Path(directory) if directory else ROOT / 'reconstructed' / 'camera'
    subprocess.run(['make', '-C', str(directory)], check=True, capture_output=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(directory / f'libclient_camera.{suffix}'))
    P = ctypes.POINTER
    F = ctypes.c_float
    I = ctypes.c_int32
    V = ctypes.c_void_p
    sig = {
        'mu_view_viewport2': ([P(View), I, I, I, I], None),
        'mu_view_perspective2': ([P(View), F, F, F, F], None),
        'mu_view_begin_opengl': ([P(View), I, I, I, I], None),
        'mu_view_camera_matrix_from_gl': ([P(View), V], None),
        'mu_view_create_screen_vector': ([P(View), F, F, V, I], None),
        'mu_view_projection': ([P(View), V, P(I), P(I)], None),
        'mu_view_projection_float': ([P(View), V, P(F), P(F)], None),
        'mu_view_projection_float_scaled': ([P(View), V, P(F), P(F)], None),
        'mu_view_transform_position': ([P(View), V, V, P(I), P(I)], None),
        'mu_face_normalize': ([V, V, V, V], None),
        'mu_inside_test': ([F, F, F, I, V, V, V, V, I, F], ctypes.c_int),
        'mu_collision_line_face': ([P(Pick), V, V, I, V, V, V, V, V, ctypes.c_int], ctypes.c_int),
        'mu_terrain_tile_pick': ([P(Pick), P(View), P(Terrain), F, F, I, I, F, I, P(ctypes.c_uint8), P(F), P(F)],
                                 ctypes.c_int),
        'mu_terrain_pick': ([P(Pick), P(View), P(Terrain), I, I, I, I, P(I), P(I)], ctypes.c_int),
        'mu_tick_timer_elapsed': ([P(Timer), ctypes.c_uint32], ctypes.c_uint32),
        'mu_tick_timer_update': ([P(Timer), ctypes.c_uint32], None),
        'mu_camera_lerp_steps': ([F, F, I, I], F),
        'mu_camera_ease': ([F, F, F, I, ctypes.c_int], F),
        'mu_world_camera_enter': ([P(WorldCamera), P(View)], None),
        'mu_move_main_camera': ([P(WorldCamera), P(View), ctypes.c_uint32], None),
        'mu_world_camera_apply_zoom': ([P(WorldCamera), P(View), I], None),
        'mu_world_camera_wheel': ([P(WorldCamera), P(View), F, I], ctypes.c_int),
        'mu_key_scan': ([P(KeyInput), P(KeySample)], None),
        'mu_key_is': ([P(KeyInput), ctypes.c_uint8, ctypes.c_int, ctypes.c_int], ctypes.c_int),
        'mu_mouse_message': ([P(Mouse), ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32], F),
        'mu_frame_begin': ([P(Clock)], None),
        'mu_frame_logic_step': ([P(Clock)], ctypes.c_int),
        'mu_frame_render_start': ([P(Clock), ctypes.c_uint32], None),
        'mu_frame_finish': ([P(Clock)], I),
    }
    for name, (args, result) in sig.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


def fbuf(*values):
    return (ctypes.c_float * len(values))(*values)


# ---------------- global addresses ----------------
G = {
    'window_width': 0x01cf1624, 'window_height': 0x01cf1628, 'near': 0x01cf162c, 'far': 0x01cf1630,
    'fov': 0x01cf1634, 'fov_from': 0x01cf1638, 'fov_to': 0x01cf163c,
    'screen_x': 0x0bdc58a8, 'screen_y': 0x0bdc58ac, 'screen_w': 0x0bdc58dc, 'screen_h': 0x0bdc58e0,
    'center_x': 0x0bdc58b8, 'center_y': 0x0bdc58bc, 'center_y_flip': 0x0bdc58c0,
    'persp_x': 0x0bdc58cc, 'persp_y': 0x0bdc58d0, 'top_view': 0x0bdc58b7, 'angle': 0x0bdc58f0,
    'position': 0x0bdc5ab4, 'camera_matrix': 0x0bdc5918, 'mouse_position': 0x0bdc5984,
    'mouse_target': 0x0bdc5990, 'nearest': 0x0bdc58c8, 'collision': 0x0bdc58e4,
    'select_flag': 0x0b5e3ea6, 'select_xf': 0x0b7f5420, 'select_yf': 0x0b7f5424,
    'heights': 0x0b6f5420, 'walls': 0x0b795420, 'water_height': 0x01cf15dc,
}


def set_view_globals(guest, view):
    guest.put_u(G['window_width'], view.window_width)
    guest.put_u(G['window_height'], view.window_height)
    guest.put_i(G['screen_x'], view.screen_x, view.screen_y)
    guest.put_i(G['screen_w'], view.screen_width, view.screen_height)
    guest.put_i(G['center_x'], view.center_x, view.center_y, view.center_y_flip)
    guest.put_f(G['persp_x'], view.perspective_x, view.perspective_y)
    guest.put_f(G['near'], view.view_near)
    guest.put_f(G['far'], view.view_far)
    guest.put_f(G['fov'], view.fov)
    guest.put_f(G['angle'], *view.angle)
    guest.put_f(G['position'], *view.position)
    guest.put(G['top_view'], bytes([view.top_view]))
    guest.put_f(G['camera_matrix'], *view.camera_matrix)


def random_float(generator, kind):
    if kind == 'bits':
        while True:
            value = from_bits(generator.getrandbits(32))
            if math.isfinite(value):
                return value
    return f32(generator.uniform(-kind, kind))


class Tally:
    def __init__(self):
        self.results = {}

    def add(self, name, ok, detail=None):
        entry = self.results.setdefault(name, {'cases': 0, 'mismatches': 0, 'first': None})
        entry['cases'] += 1
        if not ok:
            entry['mismatches'] += 1
            if entry['first'] is None:
                entry['first'] = detail


# ---------------- camera / projection cases ----------------

def random_view(generator, lib, full=True):
    view = View()
    sizes = [(640, 480), (800, 600), (1024, 768), (1280, 800), (1728, 1080), (1920, 1200), (1600, 1000)]
    if generator.random() < 0.7:
        view.window_width, view.window_height = generator.choice(sizes)
    else:
        view.window_width = generator.randint(64, 4096)
        view.window_height = generator.randint(64, 4096)
    view.fov = generator.choice([20.0, 30.0, 35.0, 65.0, f32(generator.uniform(1.0, 170.0))])
    view.view_near = generator.choice([20.0, 10.0, f32(generator.uniform(1.0, 100.0))])
    view.view_far = generator.choice([2000.0, 2400.0, 3200.0, f32(generator.uniform(500.0, 6000.0))])
    view.angle[0] = generator.choice([-48.5, f32(generator.uniform(-90, 0))])
    view.angle[1] = generator.choice([0.0, f32(generator.uniform(-10, 10))])
    view.angle[2] = generator.choice([-45.0, f32(generator.uniform(-180, 180))])
    for i in range(3):
        view.position[i] = f32(generator.uniform(0, 25600)) if i < 2 else f32(generator.uniform(0, 2000))
    view.top_view = 1 if generator.random() < 0.1 else 0
    if full:
        lib.mu_view_begin_opengl(ctypes.byref(view), 0, 0, 640, 480)
    return view


def case_perspective(guest, lib, tally, generator, count):
    start = ROUTINES['perspective2'][0]
    for _ in range(count):
        view = random_view(generator, lib, full=False)
        x, y = generator.choice([(0, 0), (generator.randint(0, 300), generator.randint(0, 300))])
        w, h = generator.randint(1, 4000), generator.randint(1, 4000)
        lib.mu_view_viewport2(ctypes.byref(view), x, y, w, h)
        fov = view.fov
        aspect = f32(w / h) if generator.random() < 0.8 else random_float(generator, 10.0)
        near, far = view.view_near, f32(view.view_far * 1.4)
        guest.reset_memory()
        guest.put_u(G['window_width'], view.window_width)
        guest.put_u(G['window_height'], view.window_height)
        guest.put_i(G['screen_x'], x, y)
        guest.put_i(G['screen_w'], w, h)
        guest.call(start, [fbits(fov), fbits(aspect), fbits(near), fbits(far)])
        glu = [c for c in guest.calls if c[0] == 'gluPerspective']
        lib.mu_view_perspective2(ctypes.byref(view), fov, aspect, near, far)
        got = (guest.get_i(G['center_x'], 3), guest.get_f(G['persp_x'], 2))
        want = ((view.center_x, view.center_y, view.center_y_flip), (view.perspective_x, view.perspective_y))
        doubles = struct.unpack('<4d', struct.pack('<8I', *glu[0][1])) if len(glu) == 1 else None
        ok = (got[0] == want[0] and all(same(a, b) for a, b in zip(got[1], want[1])) and doubles is not None
              and doubles == (float(fov), float(aspect), float(near), float(far)))
        tally.add('perspective2 0x01849d76', ok, {'got': got, 'want': want, 'glu': doubles})


def case_viewport(guest, lib, tally, generator, count):
    for _ in range(count):
        view = View()
        view.window_width, view.window_height = generator.randint(1, 5000), generator.randint(1, 5000)
        args = [generator.randint(-100, 3000) for _ in range(4)]
        guest.reset_memory()
        guest.put_u(G['window_height'], view.window_height)
        guest.call(ROUTINES['viewport2'][0], args)
        lib.mu_view_viewport2(ctypes.byref(view), *args)
        gl = [c[1] for c in guest.calls if c[0] == 'glViewport']
        got = (guest.get_i(G['screen_x'], 2), guest.get_i(G['screen_w'], 2),
               tuple(struct.unpack('<4i', struct.pack('<4I', *gl[0]))) if gl else None)
        want = ((view.screen_x, view.screen_y), (view.screen_width, view.screen_height), tuple(view.gl_viewport))
        tally.add('viewport2 0x01849ec4', got == want, {'got': got, 'want': want})


def case_begin_opengl(guest, lib, tally, generator, count):
    """BeginOpengl up to its GetOpenGLMatrix call (0x0184b0c5): GL call
    sequence and arguments, gluPerspective2 globals and the read-back camera matrix."""
    start, stop = ROUTINES['begin_opengl'][0], 0x0184b0c5
    for _ in range(count):
        view = random_view(generator, lib, full=False)
        rect = generator.choice([(0, 0, 640, 480), (0, 0, 640, 432), (generator.randint(0, 100), generator.randint(0, 100),
                                                                       generator.randint(100, 640), generator.randint(100, 480))])
        lib.mu_view_begin_opengl(ctypes.byref(view), *rect)
        guest.reset_memory()
        guest.put_u(G['window_width'], view.window_width)
        guest.put_u(G['window_height'], view.window_height)
        guest.put_f(G['near'], view.view_near)
        guest.put_f(G['far'], view.view_far)
        guest.put_f(G['fov'], view.fov)
        guest.put_f(G['angle'], *view.angle)
        guest.put_f(G['position'], *view.position)
        guest.put(G['top_view'], bytes([view.top_view]))
        guest.put(0x0bdc597c, b'\x00')  # fog enable byte: off
        modelview = bytes(view.modelview)
        guest.handler['glGetFloatv'] = lambda a: guest.put(a[1], modelview) if a[0] == 0xba6 else None
        guest.call(start, list(rect), until=stop)
        del guest.handler['glGetFloatv']
        seq = [(n, a) for n, a in guest.calls]
        rotates = [tuple(from_bits(v) for v in a) for n, a in seq if n == 'glRotatef']
        translate = [tuple(from_bits(v) for v in a) for n, a in seq if n == 'glTranslatef']
        expected_rotates = [(view.angle[1], 0.0, 1.0, 0.0)] + ([] if view.top_view else [(view.angle[0], 1.0, 0.0, 0.0)]) \
            + [(view.angle[2], 0.0, 0.0, 1.0)]
        order = [n for n, a in seq if n in ('glMatrixMode', 'glViewport', 'gluPerspective', 'glRotatef', 'glTranslatef',
                                             'glGetFloatv')]
        expected_order = ['glMatrixMode', 'glViewport', 'gluPerspective', 'glMatrixMode'] + ['glRotatef'] * len(expected_rotates) \
            + ['glTranslatef', 'glGetFloatv']
        matrix = guest.get_f(G['camera_matrix'], 12)
        globals_got = (guest.get_i(G['screen_x'], 2), guest.get_i(G['screen_w'], 2), guest.get_i(G['center_x'], 3),
                       guest.get_f(G['persp_x'], 2))
        globals_want = ((view.screen_x, view.screen_y), (view.screen_width, view.screen_height),
                        (view.center_x, view.center_y, view.center_y_flip), (view.perspective_x, view.perspective_y))
        ok = (order == expected_order
              and len(rotates) == len(expected_rotates)
              and all(same(a, b) for r, e in zip(rotates, expected_rotates) for a, b in zip(r, e))
              and len(translate) == 1 and all(same(a, -b) for a, b in zip(translate[0], view.position))
              and all(same(a, b) for a, b in zip(matrix, view.camera_matrix))
              and globals_got[:3] == globals_want[:3]
              and all(same(a, b) for a, b in zip(globals_got[3], globals_want[3])))
        tally.add('BeginOpengl 0x0184adc7 (to GetOpenGLMatrix)', ok,
                  {'order': order, 'rotates': rotates, 'globals': globals_got, 'want': globals_want})


def case_screen_vector(guest, lib, tally, generator, count):
    start = ROUTINES['create_screen_vector'][0]
    for _ in range(count):
        view = random_view(generator, lib)
        sx = float(generator.randint(0, 640)) if generator.random() < 0.8 else random_float(generator, 2000.0)
        sy = float(generator.randint(0, 480)) if generator.random() < 0.8 else random_float(generator, 2000.0)
        fix = generator.choice([0, 1])
        guest.reset_memory()
        set_view_globals(guest, view)
        out = guest.arena(b'\x00' * 12, 0)
        guest.call(start, [fbits(sx), fbits(sy), out, fix])
        target = fbuf(0, 0, 0)
        lib.mu_view_create_screen_vector(ctypes.byref(view), sx, sy, target, fix)
        got = guest.get_f(out, 3) + guest.get_f(G['mouse_position'], 3)
        want = tuple(target) + tuple(view.mouse_position)
        tally.add('CreateScreenVector 0x01849f08', all(same(a, b) for a, b in zip(got, want)),
                  {'got': got, 'want': want})


def case_projection(guest, lib, tally, generator, count):
    for _ in range(count):
        view = random_view(generator, lib)
        roll = generator.random()
        if roll < 0.7:
            pos = [view.position[0] + f32(generator.uniform(-1500, 1500)), view.position[1] + f32(generator.uniform(-1500, 1500)),
                   f32(generator.uniform(0, 600))]
        elif roll < 0.85:
            pos = [random_float(generator, 1e5) for _ in range(3)]
        elif roll < 0.92:
            pos = [view.position[0], view.position[1], view.position[2]]  # the eye: 0/0 -> NaN
        else:
            pos = [generator.choice([math.nan, math.inf, 3e38]), 0.0, 0.0]
        pos = [f32(p) for p in pos]
        guest.reset_memory()
        set_view_globals(guest, view)
        p = guest.arena(struct.pack('<3f', *pos), 0)
        a, b = guest.arena(b'\x00' * 4, 0x20), guest.arena(b'\x00' * 4, 0x24)
        ix, iy = ctypes.c_int32(), ctypes.c_int32()
        fx, fy = ctypes.c_float(), ctypes.c_float()
        pc = fbuf(*pos)
        # integer projection traps on IDIV overflow exactly as the client would; skip such inputs
        guest.call(ROUTINES['projection'][0], [p, a, b])
        lib.mu_view_projection(ctypes.byref(view), pc, ctypes.byref(ix), ctypes.byref(iy))
        got = (guest.get_i(a), guest.get_i(b))
        tally.add('Projection 0x0184a244', got == (ix.value, iy.value), {'got': got, 'want': (ix.value, iy.value)})
        guest.call(ROUTINES['projection_float'][0], [p, a, b])
        lib.mu_view_projection_float(ctypes.byref(view), pc, ctypes.byref(fx), ctypes.byref(fy))
        got = (guest.get_f(a), guest.get_f(b))
        tally.add('Projection float 0x0184a3ce', same(got[0], fx.value) and same(got[1], fy.value),
                  {'got': got, 'want': (fx.value, fy.value)})
        guest.call(ROUTINES['projection_float_scaled'][0], [p, a, b])
        lib.mu_view_projection_float_scaled(ctypes.byref(view), pc, ctypes.byref(fx), ctypes.byref(fy))
        got = (guest.get_f(a), guest.get_f(b))
        tally.add('Projection float 0.83 0x0184a2e8', same(got[0], fx.value) and same(got[1], fy.value),
                  {'got': got, 'want': (fx.value, fy.value)})
        o = guest.arena(b'\x00' * 12, 0x40)
        guest.call(ROUTINES['transform_position'][0], [p, o, a, b])
        oc = fbuf(0, 0, 0)
        lib.mu_view_transform_position(ctypes.byref(view), pc, oc, ctypes.byref(ix), ctypes.byref(iy))
        got = guest.get_f(o, 3) + (guest.get_i(a), guest.get_i(b))
        want = tuple(oc) + (ix.value, iy.value)
        tally.add('TransformPosition 0x0184a455',
                  all(same(x, y) for x, y in zip(got[:3], want[:3])) and got[3:] == want[3:], {'got': got, 'want': want})


# ---------------- picking ----------------

def random_vec(generator, scale):
    return [f32(generator.uniform(-scale, scale)) for _ in range(3)]


def special_floats():
    return [0.0, -0.0, 1.0, -1.0, 0.5, -0.5, 0.4999999, 100.0, math.inf, -math.inf, math.nan, 1e-30, -1e30]


def case_face_normalize(guest, lib, tally, generator, count):
    start = ROUTINES['face_normalize'][0]
    for number in range(count):
        if number % 10 == 0:
            vs = [[generator.choice(special_floats()) for _ in range(3)] for _ in range(3)]
        elif number % 10 == 1:
            base = random_vec(generator, 1000)
            vs = [base, base[:], [base[0] + 100, base[1], base[2]]]  # degenerate
        else:
            vs = [random_vec(generator, 3000) for _ in range(3)]
        vs = [[f32(v) for v in vec] for vec in vs]
        guest.reset_memory()
        if number % 10 == 0:
            # NaN/infinite lengths: with mode word 0 the CRT sqrt reports the
            # domain error (errno path, CRT state not captured); the returned
            # value is the same, so these cases use mode 1.
            guest.put(CRT_MATH_MODE, struct.pack('<I', 1))
        addresses = [guest.arena(struct.pack('<3f', *v), 0x10 * i) for i, v in enumerate(vs)]
        out = guest.arena(b'\xee' * 12, 0x40)
        guest.call(start, addresses + [out])
        normal = fbuf(0, 0, 0)
        lib.mu_face_normalize(fbuf(*vs[0]), fbuf(*vs[1]), fbuf(*vs[2]), normal)
        got = guest.get_f(out, 3)
        tally.add('FaceNormalize 0x00d01206', all(same(a, b) for a, b in zip(got, normal)),
                  {'in': vs, 'got': got, 'want': tuple(normal)})


def case_inside(guest, lib, tally, generator, count):
    start = ROUTINES['inside_test'][0]
    for number in range(count):
        quad = [random_vec(generator, 200) for _ in range(4)]
        if number % 4 == 0:
            point = [f32(sum(q[i] for q in quad[:3]) / 3) for i in range(3)]
        else:
            point = random_vec(generator, 200)
        if number % 50 == 0:
            point[generator.randint(0, 2)] = generator.choice([math.nan, math.inf])
        n = generator.choice([3, 3, 4, 2, 1])
        axis = generator.choice([1, 2, 4, 1, 2, 4, 3, 8])
        kind = generator.choice([0.7, -0.7, 0.0, -0.0, math.nan, 1.0])
        guest.reset_memory()
        addresses = [guest.arena(struct.pack('<3f', *v), 0x10 * i) for i, v in enumerate(quad)]
        result = guest.call(start, [fbits(point[0]), fbits(point[1]), fbits(point[2]), n] + addresses
                            + [axis, fbits(kind)]) & 0xff
        want = lib.mu_inside_test(point[0], point[1], point[2], n, *[fbuf(*q) for q in quad], axis, kind)
        tally.add('InsideTest 0x018506bc', result == want, {'got': result, 'want': want})


def collision_inputs(generator, number):
    """A ray and a quad: mostly realistic terrain picks, plus edge cases."""
    x0, y0 = f32(generator.uniform(0, 25500)), f32(generator.uniform(0, 25500))
    heights = [f32(generator.uniform(0, 400)) for _ in range(4)]
    quad = [[x0, y0, heights[0]], [x0 + 100, y0, heights[1]], [x0 + 100, y0 + 100, heights[2]], [x0, y0 + 100, heights[3]]]
    quad = [[f32(v) for v in q] for q in quad]
    if number % 3 == 0 or number % 5 == 4:
        target_point = [f32(x0 + generator.uniform(-20, 120)), f32(y0 + generator.uniform(-20, 120)), heights[0]]
        origin = [f32(target_point[0] + generator.uniform(-1500, 1500)), f32(target_point[1] + generator.uniform(-1500, 1500)),
                  f32(generator.uniform(500, 2500))]
        target = [f32(origin[i] + (target_point[i] - origin[i]) * 3) for i in range(3)]
    else:
        origin = random_vec(generator, 30000)
        target = random_vec(generator, 30000)
    if number % 37 == 0:
        target = origin[:]
    if number % 41 == 0:
        target[generator.randint(0, 2)] = origin[generator.randint(0, 2)]
    return origin, target, quad


def case_collision(guest, lib, tally, generator, count):
    start = ROUTINES['collision_line_face'][0]
    hits = 0
    for number in range(count):
        origin, target, quad = collision_inputs(generator, number)
        normal = fbuf(0, 0, 0)
        order = (0, 1, 2, 3) if number % 2 == 0 else (0, 2, 3, 1)
        verts = [quad[i] for i in order]
        lib.mu_face_normalize(fbuf(*verts[0]), fbuf(*verts[1]), fbuf(*verts[2]), normal)
        if number % 29 == 0:
            normal = fbuf(*[generator.choice(special_floats()) for _ in range(3)])
        nearest = generator.choice([9999999.0, 5.0, 1.0, 0.5, f32(generator.uniform(0, 4))])
        n = generator.choice([3, 3, 3, 4])
        store = generator.choice([1, 1, 0])
        if number % 5 == 4:
            # nearest equal to this face's own t: the client accepts t <= nearest
            probe = Pick(9999999.0, (ctypes.c_float * 3)(0, 0, 0))
            if lib.mu_collision_line_face(ctypes.byref(probe), fbuf(*origin), fbuf(*target), n,
                                          *[fbuf(*v) for v in verts], normal, 1):
                nearest = probe.nearest
        guest.reset_memory()
        guest.put_f(G['nearest'], nearest)
        guest.put_f(G['collision'], 7.0, 8.0, 9.0)
        a = guest.arena(struct.pack('<3f', *origin), 0)
        b = guest.arena(struct.pack('<3f', *target), 0x10)
        vs = [guest.arena(struct.pack('<3f', *v), 0x20 + 0x10 * i) for i, v in enumerate(verts)]
        nn = guest.arena(bytes(normal), 0x80)
        result = guest.call(start, [a, b, n] + vs + [nn, store]) & 0xff
        pick = Pick(nearest, (ctypes.c_float * 3)(7.0, 8.0, 9.0))
        want = lib.mu_collision_line_face(ctypes.byref(pick), fbuf(*origin), fbuf(*target), n, *[fbuf(*v) for v in verts],
                                          normal, store)
        hits += want
        got_state = (guest.get_f(G['nearest']),) + guest.get_f(G['collision'], 3)
        want_state = (pick.nearest,) + tuple(pick.collision)
        tally.add('CollisionDetectLineToFace 0x0184f96c',
                  result == want and all(same(x, y) for x, y in zip(got_state, want_state)),
                  {'got': (result, got_state), 'want': (want, want_state)})
    return hits


def case_terrain_tile(guest, lib, tally, generator, count):
    """RenderTerrainTile 0x016ccda5 with Flag = 1 over a synthetic 256x256 terrain."""
    start = ROUTINES['terrain_tile'][0]
    heights = (ctypes.c_float * 65536)()
    walls = (ctypes.c_uint16 * 65536)()
    for i in range(65536):
        heights[i] = f32(generator.uniform(0, 300))
        walls[i] = generator.choice([0, 0, 0, 0x40, 0x08, 0x80])
    terrain = Terrain(heights, walls, 1201.0)
    hb, wb = bytes(heights), bytes(walls)
    hits = 0
    for number in range(count):
        view = random_view(generator, lib)
        lod = generator.choice([1, 1, 1, 2])
        # corners read tile (x+lod, y+lod) without bounds; stay inside the 256x256 arrays
        xi, yi = generator.randint(0, 255 - lod), generator.randint(0, 255 - lod)
        if number % 2 == 0:
            # aim the mouse ray at this tile from the camera
            view.position[0], view.position[1] = f32(xi * 100 + 50 + generator.uniform(-900, 900)), f32(yi * 100 + 50 + generator.uniform(-900, 900))
            view.position[2] = f32(generator.uniform(800, 1600))
            aim = [f32(xi * 100 + generator.uniform(0, 100)), f32(yi * 100 + generator.uniform(0, 100)), heights[yi * 256 + xi]]
            for i in range(3):
                view.mouse_position[i] = view.position[i]
                view.mouse_target[i] = f32(view.position[i] + (aim[i] - view.position[i]) * 2.5)
        else:
            for i in range(3):
                view.mouse_position[i] = f32(generator.uniform(0, 25600))
                view.mouse_target[i] = f32(generator.uniform(0, 25600))
        lodf = float(lod)
        xf, yf = float(xi), float(yi)
        guest.reset_memory()
        guest.put(G['heights'], hb)
        guest.put(G['walls'], wb)
        guest.put_f(G['water_height'], 1201.0)
        guest.put_f(G['mouse_position'], *view.mouse_position)
        guest.put_f(G['mouse_target'], *view.mouse_target)
        guest.put_f(G['nearest'], 9999999.0)
        guest.put_f(G['collision'], 0.0, 0.0, 0.0)
        guest.put(G['select_flag'], b'\x00')
        guest.put_f(G['select_xf'], -1.0, -1.0)
        result = guest.call(start, [fbits(xf), fbits(yf), xi, yi, fbits(lodf), lod, 1]) & 0xff
        pick = Pick(9999999.0, (ctypes.c_float * 3)(0, 0, 0))
        flag, sxf, syf = ctypes.c_uint8(0), ctypes.c_float(-1.0), ctypes.c_float(-1.0)
        want = lib.mu_terrain_tile_pick(ctypes.byref(pick), ctypes.byref(view), ctypes.byref(terrain), xf, yf, xi, yi,
                                        lodf, lod, ctypes.byref(flag), ctypes.byref(sxf), ctypes.byref(syf))
        hits += want
        got = (result, guest.get(G['select_flag'], 1)[0], guest.get_f(G['select_xf'], 2), guest.get_f(G['nearest']),
               guest.get_f(G['collision'], 3))
        exp = (want, flag.value, (sxf.value, syf.value), pick.nearest, tuple(pick.collision))
        ok = got[:2] == exp[:2] and all(same(a, b) for a, b in zip(got[2] + (got[3],) + got[4], exp[2] + (exp[3],) + exp[4]))
        tally.add('RenderTerrainTile pick 0x016ccda5', ok, {'got': got, 'want': exp})
    return hits


# ---------------- input / frame ----------------

def case_key_scan(guest, lib, tally, generator, steps):
    """0x00ec5475 over a random key history, state table compared after every step."""
    table, active_flag, hwnd_global, keydown_flag = 0x01ec91c0, 0x06fc9cb5, 0x06fc9c94, 0x0bdc5982
    keys = KeyInput()
    guest.reset_memory()
    guest.put(table, bytes(256))
    down = [0] * 256
    for step in range(steps):
        sample = KeySample()
        sample.active = 0 if step % 23 == 7 else 1
        for vk in range(256):
            if generator.random() < 0.15:
                down[vk] ^= 1
            sample.down[vk] = down[vk]
        for vk in (0x1b, 0x09, 0x01):
            if generator.random() < 0.4:
                down[vk] ^= 1
                sample.down[vk] = down[vk]
        sample.game_foreground = 0 if step % 17 == 5 else 1
        sample.focus_is_foreground = generator.choice([0, 1])
        sample.key_message_down = generator.choice([0, 1])
        hwnd, focus = 0x1234, 0x1234 if sample.focus_is_foreground else 0x9999
        guest.put(active_flag, bytes([sample.active]))
        guest.put_u(hwnd_global, hwnd)
        guest.put(keydown_flag, bytes([sample.key_message_down]))
        guest.handler['GetAsyncKeyState'] = lambda a, s=sample: 0x8001 if s.down[a[0] & 0xff] else 0
        guest.handler['GetForegroundWindow'] = lambda a, s=sample: hwnd if s.game_foreground else 0x4444
        guest.handler['GetFocus'] = lambda a, f=focus, s=sample: f if s.game_foreground else 0x4444
        guest.call(ROUTINES['key_scan'][0], [], ecx=table)
        lib.mu_key_scan(ctypes.byref(keys), ctypes.byref(sample))
        got = guest.get(table, 256)
        tally.add('key scan 0x00ec5475', got == bytes(keys.state), {'step': step})
        # the four queries through their wrappers, for a few keys
        for vk in generator.sample(range(256), 4) + [0x1b, 0x01]:
            for method, state in (('key_none', 0), ('key_release', 1), ('key_press', 2), ('key_repeat', 3)):
                result = guest.call(ROUTINES[method][0], [vk], ecx=table) & 0xff
                want = lib.mu_key_is(ctypes.byref(keys), sample.active, vk, state)
                tally.add('key queries 0x00ec5577/ac/e2/0x00ec5618', result == want, {'vk': vk, 'state': state})
    for name in ('GetAsyncKeyState', 'GetForegroundWindow', 'GetFocus'):
        guest.handler.pop(name)


def case_mouse_move(guest, lib, tally, generator, count):
    """WM_MOUSEMOVE arithmetic of 0x0120fee3: 0x0121012c..0x0121016b (scale) and
    0x012101ab..0x012101f7 (clamp); the UI calls between them are not executed."""
    for _ in range(count):
        mouse = Mouse()
        mouse.scale_x = generator.choice([1.0, 2.7, 1.25, f32(generator.uniform(0.1, 6))])
        mouse.scale_y = generator.choice([1.0, 2.25, 1.6667, f32(generator.uniform(0.1, 6))])
        lparam = generator.getrandbits(32)
        guest.reset_memory()
        guest.put_f(0x06fbcd94, mouse.scale_x, mouse.scale_y)
        frame = INITIAL_ESP - 0x400
        guest.put(frame + 0x14, struct.pack('<I', lparam))
        guest.uc.reg_write(guest.x.UC_X86_REG_EBP, frame)
        run_range(guest, 0x0121012c, 0x0121016b)
        run_range(guest, 0x012101ab, 0x012101f7)
        lib.mu_mouse_message(ctypes.byref(mouse), 0x200, 0, lparam)
        got = (guest.get_i(0x0bdc5ad8), guest.get_i(0x0bdc5adc))
        tally.add('WM_MOUSEMOVE 0x0121012c', got == (mouse.x, mouse.y), {'lparam': hex(lparam), 'got': got,
                                                                        'want': (mouse.x, mouse.y)})


def run_range(guest, start, stop):
    """Executes an instruction range with the current registers (no call frame)."""
    uc, x = guest.uc, guest.x
    guest.violation = None
    uc.reg_write(x.UC_X86_REG_ESP, INITIAL_ESP - 0x800)
    uc.reg_write(x.UC_X86_REG_FPCW, FPCW)
    uc.reg_write(x.UC_X86_REG_MXCSR, MXCSR)
    try:
        uc.emu_start(start, stop, count=10000)
    except guest.u.UcError as failure:
        raise Stop(f'{hex(start)}: {failure}')
    if guest.violation or uc.reg_read(x.UC_X86_REG_EIP) != stop:
        raise Stop(f'{hex(start)}: {guest.violation}')


def case_mouse_buttons(guest, lib, tally, generator, count):
    """Button and wheel cases of the main message switch of 0x0120fee3 (after
    the hero/UI guards): 0x012104b6.., 0x0121051c.., 0x01210585.., 0x012105eb..,
    0x0121061e.., 0x01210631.., 0x0121066a.., wheel 0x01210780..0x01210797."""
    ranges = {0x201: (0x012104b6, 0x012104dd), 0x202: (0x0121051c, 0x0121054c), 0x204: (0x01210585, 0x012105ac),
              0x205: (0x012105eb, 0x01210612), 0x203: (0x0121061e, 0x0121062c), 0x207: (0x01210631, 0x01210658),
              0x208: (0x0121066a, 0x01210691), 0x20a: (0x01210780, 0x01210797)}
    flags = {'left': 0x0bdc5981, 'left_push': 0x0bdc599c, 'left_pop': 0x0bdc5983, 'left_double': 0x0bdc59a0,
             'right': 0x0bdc599d, 'right_push': 0x0bdc599f, 'right_pop': 0x0bdc599e,
             'middle': 0x0bdc59a1, 'middle_push': 0x0bdc59a3, 'middle_pop': 0x0bdc59a2}
    mouse = Mouse()
    mouse.x, mouse.y = 100, 200
    guest.reset_memory()
    for name, address in flags.items():
        guest.put(address, b'\x00')
    guest.put_i(0x0bdc5ad8, mouse.x, mouse.y)
    guest.put_i(0x06fc9e4c, 5)
    guest.put_i(0x0bdc59a4, 0)
    guest.put_i(0x06fc9e58, 0, 0)
    mouse.idle = 5
    for _ in range(count):
        message = generator.choice(list(ranges))
        wparam = generator.getrandbits(32)
        frame = INITIAL_ESP - 0x400
        guest.put(frame + 0x10, struct.pack('<I', wparam))
        guest.uc.reg_write(guest.x.UC_X86_REG_EBP, frame)
        run_range(guest, *ranges[message])
        lib.mu_mouse_message(ctypes.byref(mouse), message, wparam, 0)
        got = {name: guest.get(address, 1)[0] for name, address in flags.items()}
        want = {name: getattr(mouse, name) for name in flags}
        got['idle'], want['idle'] = guest.get_i(0x06fc9e4c), mouse.idle
        got['click'], want['click'] = guest.get_i(0x06fc9e58, 2), (mouse.last_click_x, mouse.last_click_y)
        got['wheel'], want['wheel'] = guest.get_i(0x0bdc59a4), mouse.wheel
        tally.add('mouse messages 0x0120fee3', got == want, {'message': hex(message), 'got': got, 'want': want})


def case_frame_cap(guest, lib, tally, generator, count):
    """0x018524e7..0x01852507 (frame start) and 0x0185265a..0x018526a0 (cap and
    accumulator), with GetTickCount/Sleep stubbed; the render between is skipped."""
    clock = Clock()
    guest.reset_memory()
    tick = 1000
    sleeps = []
    for number in range(count):
        clock.frame_tick, clock.frames = generator.getrandbits(32) if number == 0 else clock.frame_tick, clock.frames
        pending = generator.choice([0, 13, 39, generator.randint(-50, 400)])
        clock.pending = pending
        guest.put_u(0x0bdc5e64, clock.frame_tick)
        guest.put_u(0x0bdc5ebc, clock.frames)
        tick = (clock.frame_tick + generator.choice([0, 5, 20, 39, 40, 41, 100, generator.randint(0, 2000), 0xfffffff0])) & 0xffffffff
        guest.handler['GetTickCount'] = lambda a, t=tick: t
        guest.handler['Sleep'] = lambda a: sleeps.append(a[0])
        frame = INITIAL_ESP - 0x400
        guest.put(frame - 0x34, struct.pack('<i', pending))
        guest.put(frame - 0x28, struct.pack('<I', 0x77777777))
        guest.uc.reg_write(guest.x.UC_X86_REG_EBP, frame)
        sleeps.clear()
        run_range(guest, 0x018524e7, 0x01852501)
        guest.put(frame - 0x11, b'\x00')
        run_range(guest, 0x01852501, 0x0185250c)
        run_range(guest, 0x0185265a, 0x018526a0)
        accumulator = struct.unpack('<i', guest.get(frame - 0xd0, 4))[0]
        lib.mu_frame_render_start(ctypes.byref(clock), tick)
        sleep = lib.mu_frame_finish(ctypes.byref(clock))
        got = (guest.get(0x0bdc5e64, 4), guest.get_i(0x0bdc5ebc), accumulator, sleeps[:])
        want = (struct.pack('<I', clock.frame_tick), clock.frames, clock.accumulator, [sleep] if sleep >= 0 else [])
        tally.add('frame start and cap 0x018524e7/0x0185265a', got == want, {'got': got, 'want': want})
    guest.handler.pop('GetTickCount')
    guest.handler.pop('Sleep')


# ---------------- camera helpers and MoveMainCamera ----------------

def case_helpers(guest, lib, tally, generator, count):
    for number in range(count):
        a, b = random_float(generator, 100.0), random_float(generator, 100.0)
        i, n = generator.randint(-5, 40), generator.choice([26, 1, 0, -3, 500, generator.randint(-10, 1000)])
        guest.reset_memory()
        guest.call(ROUTINES['lerp_steps'][0], [fbits(a), fbits(b), i, n])
        got = f32(guest.st0())
        want = lib.mu_camera_lerp_steps(a, b, i, n)
        tally.add('lerp 0x0185047d', same(got, want), {'got': got, 'want': want})
        t = generator.choice([f32(generator.uniform(-10, 600)), 0.0, 500.0, 499.99, float(generator.randint(0, 600)),
                              math.nan])
        n = generator.choice([500, 1, generator.randint(1, 2000)])
        forward = generator.choice([0, 1])
        guest.call(ROUTINES['ease'][0], [fbits(a), fbits(b), fbits(t), n, forward])
        got = f32(guest.st0())
        want = lib.mu_camera_ease(a, b, t, n, forward)
        tally.add('ease 0x018504c6', same(got, want), {'in': (a, b, t, n, forward), 'got': got, 'want': want})
        timer = Timer(generator.choice([0, generator.getrandbits(32)]), generator.choice([0, 500, generator.getrandbits(32)]),
                      generator.choice([0, 1, 2]))
        now = generator.getrandbits(32)
        base = 0x0bdc5ed0
        guest.put_u(base, timer.start, timer.duration)
        guest.put(base + 8, bytes([timer.done]))
        guest.handler['GetTickCount'] = lambda args, value=now: value
        got = guest.call(ROUTINES['timer_elapsed'][0], [timer.duration, 1], ecx=base)
        want = lib.mu_tick_timer_elapsed(ctypes.byref(timer), now)
        tally.add('timer elapsed 0x018519ff', got == want, {'got': got, 'want': want})
        guest.call(ROUTINES['timer_update'][0], [], ecx=base)
        lib.mu_tick_timer_update(ctypes.byref(timer), now)
        got = struct.unpack('<IIB', guest.get(base, 9))
        tally.add('timer update 0x00c9b4ac', got == (timer.start, timer.duration, timer.done), {'got': got})
    guest.handler.pop('GetTickCount', None)


HERO, WORLD_INFO, WORLD_INFO2, OBJ988, ZOOM_OBJ, CAM_OBJ, CAM_OBJ2, MISC = (
    ARENA + 0x10000, ARENA + 0x20000, ARENA + 0x20100, ARENA + 0x21000, ARENA + 0x22000, ARENA + 0x23000,
    ARENA + 0x23100, ARENA + 0x24000)

CLIENT_STUBS = {
    # address: (cleanup bytes, reason)
    0x00988c5c: (0, 'scripted-camera object getter; returns an object whose +0x3c is 0 (no scripted camera)'),
    0x0098647b: (0, 'world-information getter; returns the synthetic world record (FOV, far factors)'),
    0x00e94004: (0, 'event-map predicate'),
    0x00e3068f: (0, 'event-map predicate'),
    0x009a6ef3: (0, 'camera-zoom object getter'),
    0x009a645f: (0, 'zoom object predicate (far 2300)'),
    0x0099b3b1: (0, 'zoom object active predicate'),
    0x0099b4c0: (4, 'zoom object level'),
    0x00f2bb92: (0, 'UI/camera manager getter; returns the synthetic object for 0x00ec3394 and 0x00f2aba9'),
    0x00f2aba9: (4, 'UI window-open query (window 0x3e): closed'),
    0x00da9d49: (0, 'world list predicate of the wheel handler: not listed'),
    0x0121d447: (0, 'post-camera manager getter'),
    0x0098564a: (0, 'post-camera update (not part of the camera state)'),
    0x009c104e: (0, 'character-class helper getter'),
    0x0106b9ca: (4, 'hero skill/state id'),
    0x0106b99d: (4, 'hero class value'),
}


def world_scenario(generator):
    c = WorldCamera()
    c.scene = 6
    c.world = generator.choice([0, 0, 1, 2, 3, 4, 7, 0x33, 0x5b, 0x5c, 0x8b, 5, 0x45, 0x48])
    c.hero_tile_x, c.hero_tile_y = generator.randint(0, 255), generator.randint(0, 255)
    c.hero_position[0] = f32(c.hero_tile_x * 100 + generator.uniform(0, 100))
    c.hero_position[1] = f32(c.hero_tile_y * 100 + generator.uniform(0, 100))
    c.hero_position[2] = f32(generator.uniform(0, 500))
    c.hero_byte4 = generator.choice([0, 1, 2])
    c.hero_tile_wall = generator.choice([0, 0, 0x40, 0x80, 0xc0, 0x08])
    if generator.random() < 0.2:
        for i in range(3):
            c.camera_override[i] = f32(generator.uniform(0, 20000))
    c.world_fov = generator.choice([35.0, 30.0, 40.0, 33.5])
    c.far_scale[0] = generator.choice([1.0, 1.2, f32(generator.uniform(0.5, 2))])
    c.far_scale[1] = generator.choice([1.0, f32(generator.uniform(0.5, 2))])
    c.far_scale[2] = generator.choice([1.0, 1.25, f32(generator.uniform(0.5, 2))])
    c.event_world = 1 if generator.random() < 0.1 else 0
    c.zoom_object_active = 1 if generator.random() < 0.15 else 0
    c.zoom_object_level = generator.randint(-1, 6)
    c.far_2300 = 1 if generator.random() < 0.15 else 0
    c.zoom_level5_distance = f32(generator.uniform(800, 2000))
    c.earthquake = generator.choice([0.0, 0.0, f32(generator.uniform(-3, 3))])
    c.world_time = f32(generator.uniform(0, 1e6))
    c.distance = generator.choice([1000.0, f32(generator.uniform(800, 1600))])
    c.distance_target = f32(generator.uniform(800, 1600))
    c.zoom_level = generator.choice([0, 0, 0, 1, 2, 3, 4, 5, 6, -1])
    c.lift = generator.choice([0.0, 0.0, 10.0, 200.0, 205.0, -10.0, 5.0])
    c.fov_from = generator.choice([20.0, 30.0, c.world_fov])
    c.fov_to = generator.choice([20.0, 30.0, c.world_fov])
    for i in range(3):
        c.angle_start[i] = f32(generator.uniform(-60, 0))
        c.angle_end[i] = f32(generator.uniform(-80, -40))
        c.position_start[i] = f32(generator.uniform(0, 2000))
        c.position_end[i] = f32(generator.uniform(0, 2000))
    c.zoom_timer = Timer(generator.choice([0, 1000, generator.getrandbits(32)]), generator.choice([500, 0, 500]),
                         generator.choice([1, 1, 0]))
    c.zoom_index = generator.randint(-1, 3)
    view = View()
    view.fov = generator.choice([c.world_fov, 20.0, 30.0, f32(generator.uniform(15, 40))])
    view.view_far = 2000.0
    view.angle[2] = generator.choice([-45.0, f32(generator.uniform(-180, 180))])
    view.top_view = 1 if generator.random() < 0.05 else 0
    for i in range(3):
        view.position[i] = f32(generator.uniform(0, 20000))
        view.angle[i] = view.angle[i] if i == 2 else f32(generator.uniform(-60, 0))
    return c, view


def install_world(guest, c, view, now, extra=None):
    guest.reset_memory()
    guest.put_i(0x01d1df70, c.scene)
    guest.put_i(0x01cf15fc, c.world)
    guest.put_u(0x0a39d754, HERO)
    guest.put(HERO + 4, bytes([c.hero_byte4]))
    guest.put_i(HERO + 0x180, c.hero_tile_x, c.hero_tile_y)
    guest.put_f(HERO + 0x33ac, *c.hero_position)
    guest.put(0x0b795420 + 2 * (c.hero_tile_y * 256 + c.hero_tile_x), struct.pack('<H', c.hero_tile_wall))
    guest.put_u(WORLD_INFO + 0xc, WORLD_INFO2)
    guest.put_f(WORLD_INFO + 0x10, c.far_scale[2])
    guest.put_f(WORLD_INFO2 + 0x18, c.far_scale[1], c.far_scale[0], c.world_fov)
    guest.put(OBJ988, bytes(0x40))
    guest.put_f(ZOOM_OBJ + 0x68, c.zoom_level5_distance)
    guest.put(ZOOM_OBJ + 0x71, b'\x00')
    guest.put_u(CAM_OBJ + 0x30, CAM_OBJ2)
    guest.put_f(CAM_OBJ2 + 0x15c, *c.camera_override)
    guest.put_f(0x0bdb588c, c.earthquake)
    guest.put_f(0x0bdc5978, c.lift)
    guest.put_f(0x06fce370, c.world_time)
    guest.put_f(0x0bdc5ef0, c.distance)
    guest.put_f(0x01cf1860, c.distance_target)
    guest.put(0x0bdc5b84, struct.pack('<h', c.zoom_level))
    guest.put_f(0x01cf1638, c.fov_from, c.fov_to)
    guest.put_f(0x0bdc58fc, *c.angle_start)
    guest.put_f(0x0bdc5908, *c.angle_end)
    guest.put_f(0x0bdc5ac0, *c.position_start)
    guest.put_f(0x0bdc5acc, *c.position_end)
    guest.put_u(0x0bdc5ed0, c.zoom_timer.start, c.zoom_timer.duration)
    guest.put(0x0bdc5ed8, bytes([c.zoom_timer.done]))
    guest.put_i(0x0bdc5914, c.zoom_index)
    guest.put_f(G['fov'], view.fov)
    guest.put_f(G['far'], view.view_far)
    guest.put_f(G['angle'], *view.angle)
    guest.put_f(G['position'], *view.position)
    guest.put(G['top_view'], bytes([view.top_view]))
    guest.put_f(G['water_height'], c.water_height)
    guest.handler['GetTickCount'] = lambda args: now
    returns = {0x00988c5c: OBJ988, 0x0098647b: WORLD_INFO, 0x00e94004: c.event_world, 0x00e3068f: 0,
               0x009a6ef3: ZOOM_OBJ, 0x009a645f: c.far_2300, 0x0099b3b1: c.zoom_object_active,
               0x0099b4c0: c.zoom_object_level & 0xffff, 0x00f2bb92: CAM_OBJ, 0x00f2aba9: 0, 0x00da9d49: 0,
               0x0121d447: MISC, 0x0098564a: 0, 0x009c104e: MISC}
    returns.update(extra or {})
    for address, value in returns.items():
        guest.client_values[address] = value


def world_state(guest):
    return {'fov': guest.get_f(G['fov']), 'far': guest.get_f(G['far']), 'angle': guest.get_f(G['angle'], 3),
            'position': guest.get_f(G['position'], 3), 'distance': guest.get_f(0x0bdc5ef0),
            'distance_target': guest.get_f(0x01cf1860), 'zoom_level': struct.unpack('<h', guest.get(0x0bdc5b84, 2))[0],
            'lift': guest.get_f(0x0bdc5978), 'timer': struct.unpack('<IIB', guest.get(0x0bdc5ed0, 9)),
            'hero_z': guest.get_f(HERO + 0x33b4), 'water': guest.get_f(G['water_height']),
            'fov_from_to': guest.get_f(0x01cf1638, 2), 'zoom_index': guest.get_i(0x0bdc5914),
            'angle_start': guest.get_f(0x0bdc58fc, 3), 'angle_end': guest.get_f(0x0bdc5908, 3),
            'position_start': guest.get_f(0x0bdc5ac0, 3), 'position_end': guest.get_f(0x0bdc5acc, 3)}


def c_state(c, view):
    return {'fov': view.fov, 'far': view.view_far, 'angle': tuple(view.angle), 'position': tuple(view.position),
            'distance': c.distance, 'distance_target': c.distance_target, 'zoom_level': c.zoom_level, 'lift': c.lift,
            'timer': (c.zoom_timer.start, c.zoom_timer.duration, c.zoom_timer.done), 'hero_z': c.hero_position[2],
            'water': c.water_height, 'fov_from_to': (c.fov_from, c.fov_to), 'zoom_index': c.zoom_index,
            'angle_start': tuple(c.angle_start), 'angle_end': tuple(c.angle_end),
            'position_start': tuple(c.position_start), 'position_end': tuple(c.position_end)}


def states_equal(a, b):
    for key in a:
        x, y = a[key], b[key]
        if isinstance(x, tuple):
            if len(x) != len(y) or not all(same(p, q) if isinstance(p, float) else p == q for p, q in zip(x, y)):
                return False
        elif isinstance(x, float):
            if not same(x, y):
                return False
        elif x != y:
            return False
    return True


def case_move_camera(guest, lib, tally, generator, count):
    for number in range(count):
        c, view = world_scenario(generator)
        now = generator.getrandbits(32)
        install_world(guest, c, view, now)
        guest.call(ROUTINES['move_main_camera'][0], [], count=400000)
        lib.mu_move_main_camera(ctypes.byref(c), ctypes.byref(view), now)
        got, want = world_state(guest), c_state(c, view)
        diff = {k: (got[k], want[k]) for k in got if not states_equal({k: got[k]}, {k: want[k]})}
        tally.add('MoveMainCamera 0x0185498e (in-world path)', not diff, {'diff': diff, 'world': c.world})


def case_zoom(guest, lib, tally, generator, count):
    skills = [0x185d, 0x185e, 0x1833, 0x1834, 0x1835, 0x1836, 0x1000, 0]
    for number in range(count):
        c, view = world_scenario(generator)
        c.world = generator.choice([0, 2, 3, 0x45])
        now = generator.getrandbits(32)
        skill, cls = generator.choice(skills), generator.choice([0, 1, 2, 3])
        min_index = 1 if cls == 2 or skill in skills[:6] else 0
        delta = generator.choice([1.0, -1.0, 3.0, -3.0])
        install_world(guest, c, view, now, {0x0106b9ca: skill, 0x0106b99d: cls})
        applied = lib.mu_world_camera_wheel(ctypes.byref(c), ctypes.byref(view), delta, min_index)
        # with a zoom change the client ends in a sound/log call at 0x0185ace9 (not executed)
        try:
            guest.call(ROUTINES['wheel_zoom'][0], [fbits(delta)], until=0x0185ace9 if applied else RETURN, count=400000)
        except Stop as stop:
            tally.add('wheel zoom 0x018588d9 + 0x0185a9bf', False, {'stop': str(stop), 'applied': applied})
            continue
        got, want = world_state(guest), c_state(c, view)
        diff = {k: (got[k], want[k]) for k in got if not states_equal({k: got[k]}, {k: want[k]})}
        tally.add('wheel zoom 0x018588d9 + 0x0185a9bf', not diff, {'diff': diff, 'applied': applied})


# Plausible reconstruction mistakes; each must be detected (mutation check).
MUTATIONS = [
    ('center_y_flip from the height (MU source form)', 'client_camera.c',
     'v->center_y_flip = (int32_t)(v->window_width -', 'v->center_y_flip = (int32_t)(v->window_height -', 'perspective'),
    ('exact binary32 pi instead of 0x40490fd8', 'client_camera.c', '0x1.921fb0p+1f', '0x1.921fb6p+1f', 'perspective'),
    ('nearest test strict', 'client_camera.c', 'if (!(pick->nearest >= t))', 'if (!(pick->nearest > t))', 'collision'),
    ('inside test strict', 'client_camera.c', 'if (0.0f >= value)', 'if (0.0f > value)', 'inside'),
    ('binary64 face length', 'client_camera.c', '(double)(float)sqrt((double)sum)', 'sqrt((double)sum)', 'face_normalize'),
    ('NaN converts to 0', 'client_camera.c', 'return INT32_MIN;', 'return 0;', 'projection'),
    ('camera height offset 100', 'client_world_camera.c', 'float height = c->distance - 150.0f;\n        v->position[2]',
     'float height = c->distance - 100.0f;\n        v->position[2]', 'move_camera'),
    ('ease end test strict', 'client_world_camera.c', 'if (t >= (float)n)', 'if (t > (float)n)', 'helpers'),
    ('no Tab exception in the key scan', 'client_input.c', '(vk == 0x1b || vk == 0x09)', '(vk == 0x1b)', 'key_scan'),
    ('frame cap at <= 40', 'client_frame.c', 'if (elapsed < MU_FRAME_STEP_MS)', 'if (elapsed <= MU_FRAME_STEP_MS)',
     'frame_cap'),
    ('right button pop set unconditionally', 'client_input.c', 'if (m->right)\n            m->right_pop = 1;',
     'm->right_pop = 1;', 'mouse_buttons'),
]


def run_mutations(guest, families, seed, count):
    import shutil
    import tempfile
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        shutil.copytree(ROOT / 'reconstructed' / 'record-math', scratch / 'record-math',
                        ignore=shutil.ignore_patterns('*.dylib', '*.so'))
        for label, filename, old, new, family in MUTATIONS:
            target = scratch / 'camera'
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(ROOT / 'reconstructed' / 'camera', target, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
            source = (target / filename).read_text()
            if source.count(old) != 1:
                raise ValueError(f'mutation anchor not unique: {label}')
            (target / filename).write_text(source.replace(old, new))
            lib = load_library(target)
            tally = Tally()
            function, family_count = families[family]
            function(guest, lib, tally, random.Random(f'{seed}:{family}'), max(count, family_count // 2))
            bad = sum(r['mismatches'] for r in tally.results.values())
            results.append({'mutation': label, 'family': family, 'mismatches': bad,
                            'cases': sum(r['cases'] for r in tally.results.values())})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    import os
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT',
                                                         str(ROOT / 'evidence/x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get(
        'MU_IMAGE_DATA', str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--flag', default=None, help='captured 4-byte dispatch flag (trig-state capture)')
    parser.add_argument('--cases', type=int, default=400, help='random cases per routine family')
    parser.add_argument('--seed', type=int, default=0x46524d)
    parser.add_argument('--only', default=None, help='comma-separated case names')
    parser.add_argument('--output', default=None, help='write the JSON report here')
    parser.add_argument('--mutations', action='store_true', help='also check that planted mistakes are detected')
    args = parser.parse_args(argv)
    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'second image section')
    if args.flag:
        flag = load_pinned(args.flag, 4, FLAG_SHA256, 'dispatch flag')
    else:
        flag = struct.pack('<I', 1)  # the captured value (CLIENT-TRIG-STATE-001)
    for name, (start, length, digest) in ROUTINES.items():
        if hashlib.sha256(text[start - TEXT_BASE:start - TEXT_BASE + length]).hexdigest() != digest:
            raise ValueError(f'pinned routine {name} changed')
    guest = Guest(text, data, flag)
    lib = load_library()
    tally = Tally()
    n = args.cases
    families = [
        ('viewport', case_viewport, n), ('perspective', case_perspective, n), ('begin_opengl', case_begin_opengl, n),
        ('screen_vector', case_screen_vector, n), ('projection', case_projection, n),
        ('face_normalize', case_face_normalize, n), ('inside', case_inside, 2 * n), ('collision', case_collision, 4 * n),
        ('terrain_tile', case_terrain_tile, 2 * n), ('helpers', case_helpers, n), ('move_camera', case_move_camera, 2 * n),
        ('zoom', case_zoom, n), ('key_scan', case_key_scan, max(20, n // 4)), ('mouse_move', case_mouse_move, n),
        ('mouse_buttons', case_mouse_buttons, n), ('frame_cap', case_frame_cap, n)]
    only = set(args.only.split(',')) if args.only else None
    extra = {}
    for name, function, count in families:
        if only and name not in only:
            continue
        generator = random.Random(f'{args.seed}:{name}')
        result = function(guest, lib, tally, generator, count)
        if result is not None:
            extra[name + '_hits'] = result
    mutation_results = None
    if args.mutations:
        table = {name: (function, count) for name, function, count in families}
        mutation_results = run_mutations(guest, table, args.seed, max(50, n // 4))
        for entry in mutation_results:
            print(f"mutation {entry['mutation']:48s} {entry['mismatches']:5d}/{entry['cases']} detected")
    report = {'mutations': mutation_results, 'routines': {k: {'start': hex(v[0]), 'bytes': v[1], 'sha256': v[2]} for k, v in ROUTINES.items()},
              'client_stubs': {hex(k): v[1] for k, v in CLIENT_STUBS.items()}, 'results': tally.results, 'extra': extra,
              'seed': args.seed, 'cases': n}
    total = sum(r['cases'] for r in tally.results.values())
    bad = sum(r['mismatches'] for r in tally.results.values())
    for name, r in tally.results.items():
        print(f"{name:52s} {r['cases']:7d} cases  {r['mismatches']:5d} mismatches")
        if r['first'] is not None:
            print('    first:', json.dumps(r['first'], default=str)[:600])
    print(f'total {total} comparisons, {bad} mismatches', extra)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    undetected = [m for m in (mutation_results or []) if m['mismatches'] == 0]
    if undetected:
        print('undetected mutations:', [m['mutation'] for m in undetected])
    return 1 if bad or undetected else 0


if __name__ == '__main__':
    sys.exit(main())
