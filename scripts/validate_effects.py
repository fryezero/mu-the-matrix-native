#!/usr/bin/env python3
"""Compare the reconstructed effect system with the client's own effect code.

The client's actual JSON reader, effect constructors, base and type loaders,
node update 0x00a75708 (transform 0x00a76dfe, particle update 0x00a88443 or
billboard update 0x00a6ea2c with every component, emitter and shape routine
they reach) and draw routines (particle 0x00a88720 with fill 0x00a8a55c,
billboard 0x00a6ebd1 with fill 0x00a70036) run in Unicorn over the pinned
restored text, the verified second image section and the initialized part of
the third section from a restored-state capture. Per rendered frame the
harness compares, against reconstructed/effects (ctypes):

  * the live particle records (136 bytes each, byte exact);
  * the bytes handed to glBufferSubData (the VBO vertex stream, byte exact);
  * the draw state derived from the recorded GL calls (texture enable, blend
    enable and factors, glMultMatrixf, cull disable, vertex count);
  * the number of rand() calls and the emitter's rand() % 0 fault.

Boundaries modelled in Python, not client code: operator new / malloc / free
(bump allocator), rand() (the MSVC LCG, seeded per case), sscanf("%lf") in the
JSON number decoder (Python float, correctly rounded like the UCRT), the
effect texture manager 0x00a8fb55 (returns an empty or a fake texture), the
terrain height 0x016cc9e2 and normal 0x016ccbb6 (an authored x86 stub for a
plane; z = 0 for installed cases, random planes for mutations), the GLEW buffer entry points and opengl32 imports (recorded), SRW
locks and critical sections (no-ops), and the heap imports. Section-3 bytes
outside the initialized part start zeroed; reads of section-3 bytes that the
case never wrote are listed in the report.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE, DATA_BASE = 0x401000, 0x1a7c000
TEXT_BYTES, DATA_BYTES = 23572480, 2557764
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
SEC3_BASE, SEC3_INIT_END = 0x1ced000, 0x1ced000 + 0x12a00
SEC3_SHA256 = '0571c519b1c4eaf97a143d2dd29bf2a3799e56b2f613cda0d084f4b857c1dc6f'   # capture-04 prefix file
SEC3_INIT_SHA256 = None   # filled at first use and reported
BSS_END = 0xbdd2000
TERRAIN_STUBS = 0x51000000
STUB, HEAP, HEAP_BYTES = 0x50000000, 0x40000000, 0x8000000
STACK, STACK_BYTES, TEB, GDT = 0x30000000, 0x100000, 0x32000000, 0x32001000
RETURN = 0x5fff0000
# Restored-text bodies of the main compared routines (start, end, SHA-256).
BODIES = {
    'node_update': (0x00a75708, 0x00a75934),
    'transform': (0x00a76dfe, 0x00a77164),
    'particle_update': (0x00a88443, 0x00a88720),
    'particle_draw': (0x00a88720, 0x00a88970),
    'particle_fill': (0x00a8a55c, 0x00a8b515),
    'particle_loop': (0x00a8a273, 0x00a8a385),
    'emitter_update': (0x00a80752, 0x00a8092e),
    'emission_count': (0x00a8185f, 0x00a81ae2),
    'billboard_update': (0x00a6ea2c, 0x00a6ebd1),
    'billboard_draw': (0x00a6ebd1, 0x00a6ed9b),
    'billboard_fill': (0x00a70036, 0x00a709db),
    'curve_eval': (0x00a74a3f, 0x00a74c73),
}
RAND, SSCANF, NEW, MALLOC, FREE, TEXTURE = 0x01989721, 0x009524ba, 0x0191ba7b, 0x01983110, 0x01983100, 0x00a8fb55
TERRAIN_HEIGHT, TERRAIN_NORMAL = 0x016cc9e2, 0x016ccbb6
EPOCH, PCTYPE, PCTYPE_TABLE = 0x1cf65b4, 0x1d04698, 0x1bba880
CULL_CACHE = 0xbdc597f
USE_SSE2_MATH = 0xbdd1cc8   # UCRT libm dispatch flag read by sqrt/sin/cos (set by CRT startup on SSE2 CPUs)
# Import slots this harness services, named as in CLIENT-FRAME-001 (scripts/client_frame_static.py
# naming against the pinned Wine DLL exports). Any other import stops a case.
IMPORTS = {0x1a7c1ec: 'GetLastError', 0x1a7c28c: 'RtlEnterCriticalSection', 0x1a7c290: 'RtlLeaveCriticalSection',
           0x1a7c2ac: 'SetLastError', 0x1a7c44c: 'RtlAcquireSRWLockExclusive', 0x1a7c450: 'RtlReleaseSRWLockExclusive',
           0x1a7c4c0: 'RtlWakeAllConditionVariable', 0x1a7c5c4: 'HeapFree', 0x1a7c5c8: 'RtlAllocateHeap',
           0x1a7c5e0: 'RtlReAllocateHeap', 0x1a7c5e4: 'RtlSizeHeap', 0x1a7c6f0: 'glVertexPointer',
           0x1a7c6f4: 'glTexCoordPointer', 0x1a7c6f8: 'glNormalPointer', 0x1a7c6fc: 'glEnableClientState',
           0x1a7c700: 'glDisableClientState', 0x1a7c704: 'glColorPointer', 0x1a7c714: 'glMatrixMode',
           0x1a7c718: 'glPushMatrix', 0x1a7c72c: 'glPopMatrix', 0x1a7c730: 'glMultMatrixf', 0x1a7c744: 'glDrawArrays',
           0x1a7c748: 'glBlendFunc', 0x1a7c758: 'glDisable', 0x1a7c75c: 'glEnable', 0x1a7c77c: 'glBindTexture'}
GLEW = {0x1a7cb58: 'glBindBuffer', 0x1a7cb80: 'glBufferSubData', 0x1a7cb84: 'glBufferData'}
GL_ARGS = {'glEnable': 1, 'glDisable': 1, 'glBlendFunc': 2, 'glMatrixMode': 1, 'glPushMatrix': 0, 'glPopMatrix': 0,
           'glMultMatrixf': 1, 'glDrawArrays': 3, 'glBindTexture': 2, 'glVertexPointer': 4, 'glTexCoordPointer': 4,
           'glColorPointer': 4, 'glNormalPointer': 3, 'glEnableClientState': 1, 'glDisableClientState': 1,
           'glBindBuffer': 2, 'glBufferSubData': 4, 'glBufferData': 4}
SYNC = {'RtlAcquireSRWLockExclusive': 4, 'RtlReleaseSRWLockExclusive': 4, 'RtlWakeAllConditionVariable': 4,
        'RtlEnterCriticalSection': 4, 'RtlLeaveCriticalSection': 4, 'EnterCriticalSection': 4,
        'LeaveCriticalSection': 4, 'AcquireSRWLockExclusive': 4, 'ReleaseSRWLockExclusive': 4,
        'WakeAllConditionVariable': 4, 'GetLastError': 0, 'SetLastError': 4}


class CaseError(Exception):
    pass


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def fbits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def load_pinned(path, size, digest, label):
    payload = Path(path).read_bytes()
    if size is not None and len(payload) != size:
        raise ValueError(f'{label}: unexpected size')
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'{label}: SHA-256 mismatch')
    return payload


class Machine:
    """One Unicorn instance over the restored image, reused across cases."""

    def __init__(self, text, data, sec3, sse2_math=1):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL, UC_PROT_READ, UC_PROT_EXEC, UC_PROT_WRITE
        from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_BLOCK
        import unicorn.x86_const as x86
        self.x86 = x86
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, (TEXT_BYTES + 0xfff) & ~0xfff, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES + 0xfff) & ~0xfff, UC_PROT_ALL)
        uc.mem_write(DATA_BASE, data)
        uc.mem_map(SEC3_BASE, (SEC3_INIT_END - SEC3_BASE + 0xfff) & ~0xfff, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_write(SEC3_BASE, sec3)
        uc.mem_map(HEAP, HEAP_BYTES, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(STACK, STACK_BYTES, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(TEB, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(STUB, 0x10000, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(STUB, b'\xc3' * 0x10000)
        uc.mem_map(RETURN, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
        self.bss = set()
        self.data_bytes = data
        self.stub_name, self.hooks = {}, {}
        self.gl, self.imports = [], {}
        self.written3, self.undefined3 = set(), {}
        self.blocks = set()
        self.setup_fs()
        self.w32(EPOCH, 0x80000000)            # magic-static epoch at its link-time value
        # CRT runtime state set by CRT startup: _pctype -> C-locale ctype table (value as in capture-04).
        self.map_page(PCTYPE)
        self.w32(PCTYPE, PCTYPE_TABLE)
        self.written3.update(range(PCTYPE, PCTYPE + 4))
        self.map_page(USE_SSE2_MATH)
        self.w32(USE_SSE2_MATH, sse2_math)
        self.written3.update(range(USE_SSE2_MATH, USE_SSE2_MATH + 4))
        for slot in range(0x1a7c000, 0x1a7cc3c, 4):
            value = struct.unpack_from('<I', data, slot - DATA_BASE)[0]
            if TEXT_BASE <= value < 0x0c000000 or value == 0 or slot in GLEW or 0x1a7cb54 <= slot < 0x1a7cc18:
                continue
            stub = STUB + (slot - 0x1a7c000)
            uc.mem_write(slot, struct.pack('<I', stub))
            self.stub_name[stub] = IMPORTS.get(slot, 'slot_%x' % slot)
        for slot in range(0x1a7cb54, 0x1a7cc18, 4):     # GLEW data imports: slot -> variable -> stub
            var, stub = STUB + 0x8000 + (slot - 0x1a7cb54), STUB + 0x9000 + (slot - 0x1a7cb54)
            uc.mem_write(slot, struct.pack('<I', var))
            uc.mem_write(var, struct.pack('<I', stub))
            self.stub_name[stub] = GLEW.get(slot, 'glew_%x' % slot)
        uc.hook_add(UC_HOOK_CODE, self.on_stub, begin=STUB, end=STUB + 0xffff)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self.on_unmapped)
        uc.hook_add(UC_HOOK_MEM_WRITE, self.on_write3, begin=SEC3_INIT_END, end=BSS_END - 1)
        uc.hook_add(UC_HOOK_MEM_READ, self.on_read3, begin=SEC3_INIT_END, end=BSS_END - 1)
        uc.hook_add(UC_HOOK_BLOCK, self.on_block, begin=0x00a6e900, end=0x00a92800)
        for address, (handler, pop) in {RAND: (self.h_rand, 0), SSCANF: (self.h_sscanf, 0), NEW: (self.h_new, 0),
                                        MALLOC: (self.h_new, 0), FREE: (self.h_free, 0),
                                        TEXTURE: (self.h_texture, 0x14)}.items():
            self.hooks[address] = (handler, pop)
            uc.hook_add(UC_HOOK_CODE, self.on_replaced, begin=address, end=address)
        # Terrain stand-in: authored x86 stubs over a plane z = a + (b*x + c*y), normal (-b, -c, 1).
        uc.mem_map(TERRAIN_STUBS, 0x1000, UC_PROT_ALL)
        self.plane = TERRAIN_STUBS + 0x800
        self.patch_terrain()
        self.heap_mark = HEAP + 0x1000
        self.reset()

    # -- setup helpers
    def setup_fs(self):
        x86, uc = self.x86, self.uc

        def descriptor(base, limit, access, flags):
            return struct.pack('<HHBBBB', limit & 0xffff, base & 0xffff, (base >> 16) & 0xff, access,
                               ((limit >> 16) & 0xf) | (flags << 4), (base >> 24) & 0xff)
        table = (bytes(8) + descriptor(0, 0xfffff, 0x9a, 0xc) + descriptor(0, 0xfffff, 0x92, 0xc) +
                 descriptor(TEB, 0xfff, 0x92, 0x4))
        uc.mem_write(GDT, table)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, GDT, len(table) - 1, 0))
        uc.reg_write(x86.UC_X86_REG_SS, 2 << 3)
        uc.reg_write(x86.UC_X86_REG_DS, 2 << 3)
        uc.reg_write(x86.UC_X86_REG_ES, 2 << 3)
        uc.reg_write(x86.UC_X86_REG_FS, 3 << 3)
        uc.mem_write(TEB, struct.pack('<I', 0xffffffff))
        uc.mem_write(TEB + 0x18, struct.pack('<I', TEB))
        uc.mem_write(TEB + 0x2c, struct.pack('<I', TEB + 0x800))
        uc.mem_write(TEB + 0x800, struct.pack('<I', TEB + 0x900))
        uc.mem_write(TEB + 0x904, struct.pack('<I', 0x80000000))

    def patch_terrain(self):
        p = self.plane
        a, b, c, nb, nc, t = p, p + 4, p + 8, p + 12, p + 16, p + 20
        height = (b'\xf3\x0f\x10\x44\x24\x04' + b'\xf3\x0f\x59\x05' + struct.pack('<I', b) +
                  b'\xf3\x0f\x10\x4c\x24\x08' + b'\xf3\x0f\x59\x0d' + struct.pack('<I', c) +
                  b'\xf3\x0f\x58\xc1' + b'\xf3\x0f\x10\x15' + struct.pack('<I', a) + b'\xf3\x0f\x58\xd0' +
                  b'\xf3\x0f\x11\x15' + struct.pack('<I', t) + b'\xd9\x05' + struct.pack('<I', t) + b'\xc3')
        normal = (b'\x8b\x44\x24\x04' + b'\x8b\x0d' + struct.pack('<I', nb) + b'\x89\x08' +
                  b'\x8b\x0d' + struct.pack('<I', nc) + b'\x89\x48\x04' +
                  b'\xc7\x40\x08' + struct.pack('<I', fbits(1.0)) + b'\xc3')
        self.height_stub, self.normal_stub = TERRAIN_STUBS, TERRAIN_STUBS + 0x100
        self.uc.mem_write(self.height_stub, height)
        self.uc.mem_write(self.normal_stub, normal)
        from unicorn import UC_HOOK_CODE
        self.uc.hook_add(UC_HOOK_CODE, self.on_terrain, begin=TERRAIN_HEIGHT, end=TERRAIN_HEIGHT)
        self.uc.hook_add(UC_HOOK_CODE, self.on_terrain, begin=TERRAIN_NORMAL, end=TERRAIN_NORMAL)
        self.terrain_calls = 0

    def set_plane(self, a, b, c):
        self.uc.mem_write(self.plane, struct.pack('<5f', a, b, c, -f32(b), -f32(c)))

    def on_terrain(self, uc, address, size, ignored):
        self.terrain_calls += 1
        uc.reg_write(self.x86.UC_X86_REG_EIP, self.height_stub if address == TERRAIN_HEIGHT else self.normal_stub)

    def reset(self):
        self.heap_top = self.heap_mark
        self.sizes = {}
        self.rand_state, self.rand_calls = 1, 0
        self.texture_mode = 0
        self.gl.clear()

    # -- memory
    def r32(self, a): return struct.unpack('<I', self.uc.mem_read(a, 4))[0]
    def w32(self, a, v): self.uc.mem_write(a, struct.pack('<I', v & 0xffffffff))
    def rb(self, a, n): return bytes(self.uc.mem_read(a, n))

    def alloc(self, n, fill=b'\xcd'):
        self.heap_top = (self.heap_top + 15) & ~15
        a = self.heap_top
        self.heap_top += max(n, 1)
        if self.heap_top > HEAP + HEAP_BYTES:
            raise CaseError('emulated heap exhausted')
        self.uc.mem_write(a, fill * max(n, 1))
        return a

    def cstr(self, s):
        b = s.encode('latin1') + b'\0'
        a = self.alloc(len(b))
        self.uc.mem_write(a, b)
        return a

    def rcstr(self, a, limit=4096):
        out = bytearray()
        while len(out) < limit:
            c = self.rb(a + len(out), 1)
            if c == b'\0':
                break
            out += c
        return out.decode('latin1')

    def map_page(self, address):
        page = address & ~0xfff
        if page not in self.bss:
            from unicorn import UC_PROT_READ, UC_PROT_WRITE
            self.uc.mem_map(page, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
            self.bss.add(page)

    def on_unmapped(self, uc, access, address, size, value, ignored):
        if SEC3_INIT_END <= address < BSS_END:
            self.map_page(address)
            self.map_page(address + size - 1)
            return True
        return False

    def on_write3(self, uc, access, address, size, value, ignored):
        for k in range(size):
            self.written3.add(address + k)

    def on_read3(self, uc, access, address, size, value, ignored):
        if any(address + k not in self.written3 for k in range(size)):
            self.undefined3[address] = self.undefined3.get(address, 0) + 1

    def on_block(self, uc, address, size, ignored):
        self.blocks.add(address)

    # -- replaced CRT/boundary routines
    def on_replaced(self, uc, address, size, ignored):
        handler, pop = self.hooks[address]
        x86 = self.x86
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret = self.r32(esp)
        result = handler([self.r32(esp + 4 + 4 * i) for i in range(6)])
        if result is not None:
            uc.reg_write(x86.UC_X86_REG_EAX, result & 0xffffffff)
        uc.reg_write(x86.UC_X86_REG_ESP, esp + 4 + pop)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def h_new(self, args): return self.alloc(args[0])
    def h_free(self, args): return 0

    def h_rand(self, args):
        self.rand_state = (self.rand_state * 0x343fd + 0x269ec3) & 0xffffffff
        self.rand_calls += 1
        return (self.rand_state >> 16) & 0x7fff

    def h_sscanf(self, args):
        if self.rcstr(args[1]) != '%lf':
            raise CaseError('unexpected sscanf format')
        m = re.match(r'\s*[-+]?(\d+\.?\d*([eE][-+]?\d+)?|\.\d+([eE][-+]?\d+)?)', self.rcstr(args[0]))
        if not m:
            return 0
        self.uc.mem_write(args[2], struct.pack('<d', float(m.group(0))))
        return 1

    def h_texture(self, args):
        out = args[0]
        texture = 0
        if self.texture_mode:
            texture = self.alloc(0x40, b'\0')
            self.w32(texture + 0x1c, 7)       # GL texture name read by the bind helper 0x00a8f9f1
        self.w32(out, texture)
        self.w32(out + 4, 0)
        return out

    def on_stub(self, uc, address, size, ignored):
        x86 = self.x86
        name = self.stub_name.get(address, '?')
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret = self.r32(esp)
        self.imports[name] = self.imports.get(name, 0) + 1
        if name in GL_ARGS:
            n = GL_ARGS[name]
            args = [self.r32(esp + 4 + 4 * i) for i in range(n)]
            record = [name] + args
            if name == 'glBufferSubData':
                record.append(self.rb(args[3], args[2]) if args[2] else b'')
            if name == 'glMultMatrixf':
                record.append(self.rb(args[0], 64))
            self.gl.append(record)
            pop, value = 4 * n, 0
        elif name in SYNC:
            pop, value = SYNC[name], 0
        elif name in ('RtlAllocateHeap', 'HeapAlloc'):
            n = self.r32(esp + 12)
            value = self.alloc(n, b'\0' if self.r32(esp + 8) & 8 else b'\xcd')
            self.sizes[value] = n
            pop = 12
        elif name in ('RtlFreeHeap', 'HeapFree'):
            pop, value = 12, 1
        elif name in ('RtlSizeHeap', 'HeapSize'):
            pop, value = 12, self.sizes.get(self.r32(esp + 12), 0)
        elif name in ('RtlReAllocateHeap', 'HeapReAlloc'):
            old, n = self.r32(esp + 12), self.r32(esp + 16)
            value = self.alloc(n)
            keep = min(n, self.sizes.get(old, 0))
            if keep:
                uc.mem_write(value, self.rb(old, keep))
            self.sizes[value] = n
            pop = 16
        else:
            self.stop_reason = f'unexpected import {name}'
            uc.emu_stop()
            return
        uc.reg_write(x86.UC_X86_REG_EAX, value)
        uc.reg_write(x86.UC_X86_REG_ESP, esp + 4 + pop)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def call(self, address, args=(), ecx=0, limit=200_000_000):
        from unicorn import UcError
        x86, uc = self.x86, self.uc
        esp = STACK + STACK_BYTES - 0x1000 - 4 * (len(args) + 1)
        uc.mem_write(esp, struct.pack('<I', RETURN) + b''.join(struct.pack('<I', a & 0xffffffff) for a in args))
        uc.reg_write(x86.UC_X86_REG_ESP, esp)
        uc.reg_write(x86.UC_X86_REG_EBP, 0x0badf00d)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        uc.reg_write(x86.UC_X86_REG_MXCSR, 0x1f80)
        uc.reg_write(x86.UC_X86_REG_FPCW, 0x027f)
        self.stop_reason = None
        try:
            uc.emu_start(address, RETURN, count=limit)
        except UcError as error:
            eip = uc.reg_read(x86.UC_X86_REG_EIP)
            raise CaseError(f'{error} at {eip:#x}') from None
        eip = uc.reg_read(x86.UC_X86_REG_EIP)
        if eip != RETURN:
            raise CaseError(f'stopped at {eip:#x}: {self.stop_reason}')
        return uc.reg_read(x86.UC_X86_REG_EAX)


class ClientEffect:
    def __init__(self, machine, text, seed, texture):
        m = self.m = machine
        m.reset()
        m.rand_state = seed & 0xffffffff
        m.texture_mode = texture
        source = m.alloc(0x40); m.call(0x0094997e, [m.cstr(text)], ecx=source)
        root = m.alloc(0x40); m.call(0x0093c510, [0], ecx=root)
        reader = m.alloc(0x400); m.call(0x0093f708, [], ecx=reader)
        if not m.call(0x0093f7e8, [source, root, 1], ecx=reader) & 0xff:
            raise CaseError('client JSON parse failed')
        self.type = json.loads(text).get('Type')
        name = m.alloc(0x40); m.call(0x0094997e, [m.cstr('fx')], ecx=name)
        position = m.alloc(12, b'\0')
        rotation = m.alloc(12, b'\0')
        if self.type == 0:   # factory 0x00a797a0 arguments
            o = m.alloc(0x158)
            m.call(0x00a8a436, [0, name, position, rotation, fbits(1.0), 1, 1, fbits(5.0), 0x14, 1, 0, fbits(1.0),
                                fbits(0.0), 0, 0, fbits(0.0), fbits(0.0)], ecx=o)
        elif self.type == 1:
            o = m.alloc(0x170)
            color = m.alloc(16); m.uc.mem_write(color, struct.pack('<4f', 1, 1, 1, 1))
            uv0 = m.alloc(8); m.uc.mem_write(uv0, struct.pack('<2f', 0, 0))
            uv1 = m.alloc(8); m.uc.mem_write(uv1, struct.pack('<2f', 1, 1))
            m.call(0x00a6fea9, [0, name, position, rotation, fbits(1.0), 1, fbits(5.0), color, fbits(1.0),
                                fbits(1.0), fbits(0.0), uv0, uv1, 1, 0, fbits(1.0), 0, 0, fbits(0.0), fbits(0.0)], ecx=o)
        else:
            raise CaseError('unsupported type')
        self.o = o
        m.call(0x00a760b2, [root], ecx=o)
        owner = m.alloc(0x200, b'\0')
        m.uc.mem_write(owner + 0x38, b'\x01')   # owner visible (the draw reads [effect+0xd8]+0x38)
        m.w32(o + 0xd8, owner)
        self.camera = m.alloc(0x40, b'\0')

    def set_transform(self, position, rotation, scale):
        m = self.m
        m.uc.mem_write(self.o + 0x2c, struct.pack('<3f', *position))
        m.uc.mem_write(self.o + 0x44, struct.pack('<3f', *rotation))
        m.uc.mem_write(self.o + 0x50, struct.pack('<f', scale))

    def set_camera(self, position, forward, up):
        # Client camera record (0x00a8d821): position, forward, right = forward x up, up.
        z = f32(f32(forward[0] * up[1]) - f32(forward[1] * up[0]))
        y = f32(f32(forward[2] * up[0]) - f32(forward[0] * up[2]))
        x = f32(f32(forward[1] * up[2]) - f32(forward[2] * up[1]))
        self.m.uc.mem_write(self.camera, struct.pack('<12f', *position, *forward, x, y, z, *up))

    def update(self, dt):
        self.m.call(0x00a75708, [fbits(dt), 0, 0], ecx=self.o)

    def draw(self):
        m = self.m
        m.gl.clear()
        if self.type == 1:   # cull enabled in the client's cached state, so the disable is recorded
            m.map_page(CULL_CACHE)
            m.uc.mem_write(CULL_CACHE, b'\x01')
            m.written3.add(CULL_CACHE)
        m.call(0x00a88720 if self.type == 0 else 0x00a6ebd1, [self.camera], ecx=self.o)
        vertices, state = b'', [0, 0, 0, 0, 0, 0, 0]
        count = 0
        for record in m.gl:
            name = record[0]
            if name == 'glBufferSubData':
                vertices = record[-1]
            elif name == 'glDrawArrays':
                state[0] = 1
                count = record[3]
            elif name == 'glBlendFunc':
                state[2], state[3] = record[1], record[2]
            elif name in ('glEnable', 'glDisable'):
                on = name == 'glEnable'
                if record[1] == 0xbe2:
                    state[1] = int(on)
                elif record[1] == 0xde1:
                    state[4] = int(on)
                elif record[1] == 0xb44 and not on:
                    state[6] = 1
            elif name == 'glMultMatrixf':
                state[5] = 1
        if not state[1]:
            state[2] = state[3] = 0
        return vertices[:36 * count], state, count

    def particles(self):
        if self.type != 0:
            return b''
        n = self.m.r32(self.o + 0xf4)
        return self.m.rb(self.m.r32(self.o + 0xf8), n * 0x88) if n else b''


class NativeLibrary:
    def __init__(self, path):
        lib = self.lib = ctypes.CDLL(str(path))
        lib.mu_fx_open.restype = ctypes.c_void_p
        lib.mu_fx_open.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
        lib.mu_fx_close.argtypes = [ctypes.c_void_p]
        lib.mu_fx_set_plane.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float]
        lib.mu_fx_set_transform.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float),
                                            ctypes.POINTER(ctypes.c_float), ctypes.c_float]
        lib.mu_fx_frame_update.argtypes = [ctypes.c_void_p, ctypes.c_float]
        lib.mu_fx_frame_draw.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                         ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        lib.mu_fx_frame_draw.restype = ctypes.c_uint32
        lib.mu_fx_particle_records.restype = ctypes.c_void_p
        lib.mu_fx_particle_records.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        for name, restype in (('mu_fx_capacity', ctypes.c_uint32), ('mu_fx_faulted', ctypes.c_int),
                              ('mu_fx_rand_calls', ctypes.c_uint64), ('mu_fx_type', ctypes.c_int)):
            getattr(lib, name).argtypes = [ctypes.c_void_p]
            getattr(lib, name).restype = restype


class NativeEffect:
    def __init__(self, library, text, seed):
        self.lib = library.lib
        error = ctypes.create_string_buffer(256)
        raw = text.encode('latin1')
        self.h = self.lib.mu_fx_open(raw, len(raw), seed & 0xffffffff, error, 256)
        if not self.h:
            raise CaseError('native load failed: ' + error.value.decode())
        self.buffer = ctypes.create_string_buffer(144 * max(self.lib.mu_fx_capacity(self.h), 1) + 144)

    def close(self):
        self.lib.mu_fx_close(self.h)

    def update(self, dt):
        self.lib.mu_fx_frame_update(self.h, dt)

    def draw(self, camera, texture):
        cam = (ctypes.c_float * 9)(*camera)
        state = (ctypes.c_uint32 * 7)()
        n = self.lib.mu_fx_frame_draw(self.h, cam, texture, self.buffer, state)
        return self.buffer.raw[:36 * n], list(state), n

    def particles(self):
        n = ctypes.c_uint32()
        p = self.lib.mu_fx_particle_records(self.h, ctypes.byref(n))
        return ctypes.string_at(p, n.value * 0x88) if n.value else b''


def canonical_nan(raw):
    """Replaces every binary32 NaN by 0x7fc00000. The hosts differ only in the NaN they create: x86 SSE returns
    the "real indefinite" 0xffc00000 for an invalid operation (0/0 in the terrain collider when a particle's speed
    is 0), AArch64 returns the default NaN 0x7fc00000. NaN-ness itself is still compared."""
    if len(raw) % 4:
        return raw, 0
    words = struct.unpack(f'<{len(raw) // 4}I', raw)
    nan = [(w & 0x7f800000) == 0x7f800000 and (w & 0x7fffff) != 0 for w in words]
    if not any(nan):
        return raw, 0
    return struct.pack(f'<{len(words)}I', *(0x7fc00000 if n else w for n, w in zip(nan, words))), sum(nan)


def first_difference(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return -1 if len(a) == len(b) else min(len(a), len(b))


def run_case(machine, library, case):
    """case: dict(text, seed, frames, dt, camera, texture, transform, plane, label)."""
    client = ClientEffect(machine, case['text'], case['seed'], case['texture'])
    native = NativeEffect(library, case['text'], case['seed'])
    result = {'label': case['label'], 'frames': 0, 'vertices': 0, 'particles': 0, 'fault': None, 'mismatch': None}
    try:
        if case.get('transform'):
            position, rotation, scale = case['transform']
            client.set_transform(position, rotation, scale)
            native.lib.mu_fx_set_transform(native.h, (ctypes.c_float * 3)(*position),
                                           (ctypes.c_float * 3)(*rotation), scale)
        # The client's terrain collider always queries the terrain; every case gets a plane (flat z = 0 for the
        # installed cases) so no plane carries over from an earlier case.
        plane = case.get('plane') or (0.0, 0.0, 0.0)
        machine.set_plane(*plane)
        native.lib.mu_fx_set_plane(native.h, *plane)
        camera = case['camera']
        client.set_camera(camera[0:3], camera[3:6], camera[6:9])
        for frame in range(case['frames']):
            client_fault = False
            try:
                client.update(case['dt'])
            except CaseError as error:
                # The integer divide fault of rand() % 0 (emitter 0x00a80790) ends emulation either with
                # UC_ERR_EXCEPTION or with EIP left on the faulting div.
                if 'UC_ERR_EXCEPTION' not in str(error) and '0xa80790' not in str(error):
                    raise
                # Accept it only on that div (div dword [ecx+0xc], the emitter's Frequency) with a zero divisor.
                uc, x86 = machine.uc, machine.x86
                eip, ecx = uc.reg_read(x86.UC_X86_REG_EIP), uc.reg_read(x86.UC_X86_REG_ECX)
                divisor = struct.unpack('<I', uc.mem_read(ecx + 0xc, 4))[0]
                if eip != 0x00a80790 or divisor != 0:
                    raise CaseError(f'unexpected stop {error} (eip {eip:#x}, divisor {divisor})') from None
                client_fault = f'#DE div by zero at {eip:#x}'
            native.update(case['dt'])
            native_fault = bool(native.lib.mu_fx_faulted(native.h))
            if client_fault or native_fault:
                result['fault'] = {'frame': frame, 'client': client_fault or False, 'native': native_fault}
                if not (client_fault and native_fault):
                    result['mismatch'] = 'fault'
                elif machine.rand_calls != native.lib.mu_fx_rand_calls(native.h):
                    result['mismatch'] = 'rand-calls-at-fault'
                break
            cp, np_ = client.particles(), native.particles()
            if cp != np_:
                (cp, nans), (np_, _) = canonical_nan(cp), canonical_nan(np_)
                result['nan_words'] = result.get('nan_words', 0) + nans
            if cp != np_:
                i = first_difference(cp, np_)
                result['mismatch'] = f'particles frame {frame} byte {i} (field {i % 0x88:#x}) counts ' \
                                     f'{len(cp) // 0x88}/{len(np_) // 0x88}'
                break
            cv, cs, cn = client.draw()
            nv, ns, nn = native.draw(camera, case['texture'])
            if cv != nv:
                (cv, nans), (nv, _) = canonical_nan(cv), canonical_nan(nv)
                result['nan_words'] = result.get('nan_words', 0) + nans
            if cv != nv or cn != nn:
                result['mismatch'] = f'vertices frame {frame} byte {first_difference(cv, nv)}'
                break
            if cs != ns:
                result['mismatch'] = f'draw state frame {frame}: client {cs} native {ns}'
                break
            if machine.rand_calls != native.lib.mu_fx_rand_calls(native.h):
                result['mismatch'] = f'rand calls frame {frame}: {machine.rand_calls}/' \
                                     f'{native.lib.mu_fx_rand_calls(native.h)}'
                break
            result['frames'] += 1
            result['vertices'] += nn
            result['particles'] += len(np_) // 0x88
    finally:
        native.close()
    result['rand_calls'] = machine.rand_calls
    return result


# ---- case generation ----

def camera_for(generator):
    position = [generator.uniform(-12, 12), generator.uniform(-12, 12), generator.uniform(-2, 8)]
    target = [generator.uniform(-1, 1), generator.uniform(-1, 1), generator.uniform(0, 2)]
    forward = [t - p for t, p in zip(target, position)]
    length = sum(v * v for v in forward) ** 0.5
    forward = [v / length for v in forward]
    up = [0.0, 0.0, 1.0]
    dot = sum(a * b for a, b in zip(forward, up))
    up = [u - dot * f for u, f in zip(up, forward)]
    length = sum(v * v for v in up) ** 0.5
    up = [v / length for v in up]
    return [f32(v) for v in position + forward + up]


DEFAULT_CAMERA = [3.0, -12.0, 4.0, -0.24, 0.94, -0.24, 0.0, 0.0, 1.0]


def mutate(document, generator):
    """Randomizes parameters of an installed effect description (structure kept)."""
    d = json.loads(json.dumps(document))
    t = d.get('Type')
    if t == 0:
        d['SpaceIsLocal'] = generator.random() < 0.5
        d['Billboarding'] = generator.randrange(4)
        d['Blending'] = generator.randrange(4)
        d['Looping'] = generator.random() < 0.8
        d['LengthScale'] = generator.choice([0.0, 0.5, 1.0, 2.0])
        d['SpeedScale'] = generator.choice([0.0, 0.05, 0.3, 1.0])
        d['MaxParticle'] = generator.choice([1, 3, 8, 20, 60])
        if generator.random() < 0.3:
            d['randomduration'] = True
            d['minduration'], d['maxduration'] = sorted([generator.uniform(0.3, 3), generator.uniform(0.3, 3)])
        components = d.setdefault('Components', [])
        for c in components:
            if c.get('Type') == 0:
                c['Frequency'] = generator.choice([1, 1, 2, 3])
                c['Delay'] = generator.choice([0.0, 0.0, 0.15, 0.5])
                c['MinEmissionCount'] = generator.randrange(0, 4)
                c['MaxEmissionCount'] = c['MinEmissionCount'] + generator.randrange(0, 5)
                if generator.random() < 0.25:
                    c['CurveEmissionCount'] = [{'Time': 0.0, 'Value': generator.uniform(0, 5), 'Tangent': 0.0},
                                               {'Time': 1.0, 'Value': generator.uniform(0, 5), 'Tangent': 1.0}]
                if generator.random() < 0.3:
                    c['Bursts'] = [{'Time': generator.uniform(0, 1), 'Count': generator.randrange(0, 6)}
                                   for _ in range(generator.randrange(1, 4))]
                for s in c.get('Components', []):
                    if s.get('Type') == 0:
                        s['Shape'] = generator.randrange(5)
                        s['Size'] = [generator.uniform(0, 3) for _ in range(3)]
                        s['Radius'] = generator.uniform(0, 2)
                        s['Height'] = generator.uniform(0, 2)
                        s['Tangent'] = generator.uniform(0, 1)
                        s['Cylinder'] = generator.random() < 0.5
                        s['EmitFromShell'] = generator.random() < 0.5
                        s['RandomDirection'] = generator.random() < 0.4
                    elif s.get('Type') == 1 and generator.random() < 0.4:
                        s['ColorGradation'] = [{'Time': 0.0, 'Value': [1, 0.5, 0.2]},
                                               {'Time': 1.0, 'Value': [0.1, 0.2, 1.0]}]
                    elif s.get('Type') in (2, 4, 5) and generator.random() < 0.3:
                        s['Curve'] = [{'Time': 0.0, 'Value': generator.uniform(0.1, 1), 'Tangent': 0.5},
                                      {'Time': 0.6, 'Value': generator.uniform(0.1, 1), 'Tangent': -0.5},
                                      {'Time': 1.0, 'Value': generator.uniform(0.1, 1), 'Tangent': 0.0}]
        present = {c.get('Type') for c in components}
        if 3 not in present and generator.random() < 0.4:
            components.append({'Type': 3, 'Min': -3.0, 'Max': 3.0,
                               'Curve': None if generator.random() < 0.6 else
                               [{'Time': 0, 'Value': 2.0, 'Tangent': 0}, {'Time': 1, 'Value': -1.0, 'Tangent': 0}]})
        if 6 not in present and generator.random() < 0.3:
            h, v = generator.choice([1, 2, 4]), generator.choice([1, 2, 4])
            components.append({'Type': 6, 'HorizentalTiles': h, 'VerticalTiles': v, 'MinTileIndex': 0,
                               'MaxTileIndex': h * v - 1, 'TileIndices': None if generator.random() < 0.5 else
                               [{'Time': 0, 'Value': 0, 'Tangent': h * v}, {'Time': 1, 'Value': h * v, 'Tangent': 0}]})
        if 2 not in present and generator.random() < 0.3:
            components.append({'Type': 2, 'Constant': [generator.uniform(-1, 1) for _ in range(3)],
                               'CurveX': None, 'CurveY': None,
                               'CurveZ': [{'Time': 0, 'Value': 0.5, 'Tangent': 0}, {'Time': 1, 'Value': -2, 'Tangent': 0}]})
        if 7 not in present and generator.random() < 0.3:
            components.append({'Type': 7, 'Bounding': generator.uniform(0.2, 1.0)})
    elif t == 1:
        d['Billboarding'] = generator.randrange(5)
        d['Blending'] = generator.randrange(4)
        d['Looping'] = generator.random() < 0.8
        d['RotationAngle'] = generator.choice([0.0, 0.3, 1.2])
        d['Width'], d['Height'] = generator.uniform(0.2, 5), generator.uniform(0.2, 5)
        if generator.random() < 0.3:
            d['randomduration'] = True
            d['minduration'], d['maxduration'] = sorted([generator.uniform(0.3, 3), generator.uniform(0.3, 3)])
        components = d.setdefault('Components', []) or []
        d['Components'] = components
        present = {c.get('Type') for c in components}
        if 1 not in present and generator.random() < 0.5:
            components.append({'Type': 1, 'Constant': generator.uniform(-3, 3), 'Curve': None})
        if 2 not in present and generator.random() < 0.4:
            components.append({'Type': 2, 'Curve': [{'Time': 0, 'Value': 0.2, 'Tangent': 0},
                                                    {'Time': 1, 'Value': 1.4, 'Tangent': 0}]})
        if 3 not in present and generator.random() < 0.4:
            components.append({'Type': 3, 'HorizentalTiles': 4, 'VerticalTiles': 4,
                               'TileIndices': [{'Time': 0, 'Value': 0, 'Tangent': 15}, {'Time': 1, 'Value': 15, 'Tangent': 15}]})
        if 4 not in present and generator.random() < 0.4:
            components.append({'Type': 4, 'Constant': [generator.uniform(-1, 1) for _ in range(3)],
                               'CurveX': None, 'CurveY': None, 'CurveZ': None})
    return d


def build_cases(game_root, limit, frames, mutations, seed):
    generator = random.Random(seed)
    files = sorted((Path(game_root) / 'Data' / 'Effect').glob('*.ein'))
    if limit:
        files = files[:limit]
    cases = []
    for path in files:
        text = path.read_bytes().decode('latin1')
        cases.append({'label': path.name, 'text': text, 'seed': 1, 'frames': frames, 'dt': 0.1,
                      'camera': DEFAULT_CAMERA, 'texture': 0, 'transform': None, 'plane': None})
    documents = [(p.name, json.loads(p.read_bytes().decode('latin1'))) for p in files]
    for index in range(mutations):
        name, document = documents[index % len(documents)]
        mutated = mutate(document, generator)
        transform = None
        if generator.random() < 0.6:
            transform = ([f32(generator.uniform(-3, 3)) for _ in range(3)],
                         [f32(generator.uniform(-3.2, 3.2)) for _ in range(3)], f32(generator.choice([0.5, 1.0, 1.7, 3.0])))
        plane = None
        if any(c.get('Type') == 7 for c in mutated.get('Components') or []):
            plane = (f32(generator.uniform(-1.5, 0.5)), f32(generator.uniform(-0.3, 0.3)), f32(generator.uniform(-0.3, 0.3)))
        cases.append({'label': f'mutation-{index}-{name}', 'text': json.dumps(mutated, indent=1), 'seed':
                      generator.randrange(1 << 31), 'frames': frames, 'dt': f32(generator.choice([0.04, 0.1, 0.1, 0.25])),
                      'camera': camera_for(generator), 'texture': generator.randrange(2), 'transform': transform,
                      'plane': plane})
    return cases


def validate(args):
    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'image data')
    sec3_file = load_pinned(args.section3, None, SEC3_SHA256, 'section-3 capture')
    sec3 = sec3_file[:SEC3_INIT_END - SEC3_BASE]
    bodies = {name: hashlib.sha256(text[s - TEXT_BASE:e - TEXT_BASE]).hexdigest() for name, (s, e) in BODIES.items()}
    machine = Machine(text, data, sec3, args.sse2_math)
    library = NativeLibrary(args.library)
    cases = build_cases(args.game_root, args.limit, args.frames, args.mutations, args.seed)
    if args.only:
        cases = [c for c in cases if re.search(args.only, c['label'])]
    results = []
    for case in cases:
        try:
            results.append(run_case(machine, library, case))
        except CaseError as error:
            results.append({'label': case['label'], 'error': str(error), 'mismatch': 'error'})
        if args.verbose:
            print(json.dumps({k: v for k, v in results[-1].items() if k != 'text'}), file=sys.stderr)
    mismatches = [r for r in results if r.get('mismatch')]
    effect_blocks = len(machine.blocks)
    summary = {
        'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'section3_capture_sha256': SEC3_SHA256,
        'section3_initialized_sha256': hashlib.sha256(sec3).hexdigest(), 'bodies': bodies,
        'library_sha256': hashlib.sha256(Path(args.library).read_bytes()).hexdigest(),
        'cases': len(results), 'installed_cases': sum(1 for c in cases if not c['label'].startswith('mutation')),
        'mutation_cases': sum(1 for c in cases if c['label'].startswith('mutation')),
        'frames_compared': sum(r.get('frames', 0) for r in results),
        'vertices_compared': sum(r.get('vertices', 0) for r in results),
        'particle_records_compared': sum(r.get('particles', 0) for r in results),
        'faults_matched': sum(1 for r in results if r.get('fault') and not r.get('mismatch')),
        'fault_cases': [[r['label'], r['fault']['frame']] for r in results if r.get('fault') and not r.get('mismatch')],
        'nan_canonicalized_cases': sum(1 for r in results if r.get('nan_words')),
        'nan_canonicalized_words': sum(r.get('nan_words', 0) for r in results),
        'rand_calls': sum(r.get('rand_calls', 0) for r in results),
        'terrain_calls': machine.terrain_calls,
        'mismatches': len(mismatches), 'mismatch_examples': mismatches[:20],
        'mismatch_labels': [r['label'] for r in mismatches],
        'mismatch_kinds': {k: sum(1 for r in mismatches if str(r.get('mismatch')).split(' ')[0] == k)
                           for k in sorted({str(r.get('mismatch')).split(' ')[0] for r in mismatches})},
        'effect_code_blocks_executed': effect_blocks,
        'imports': machine.imports,
        'section3_undefined_reads': {hex(a): n for a, n in sorted(machine.undefined3.items())[:64]},
        'section3_undefined_read_sites': len(machine.undefined3),
        'crt_sse2_math': args.sse2_math,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True, help='x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', type=Path, required=True, help='data-capture-10/client-image-data.bin')
    parser.add_argument('--section3', type=Path, required=True, help='x86-linux-capture-04/main-01ced000.bin')
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT / 'reconstructed/effects' /
                        ('libeffects.dylib' if sys.platform == 'darwin' else 'libeffects.so'))
    parser.add_argument('--limit', type=int, help='first N installed effects only')
    parser.add_argument('--frames', type=int, default=40)
    parser.add_argument('--mutations', type=int, default=400)
    parser.add_argument('--seed', type=int, default=0x0a88443)
    parser.add_argument('--sse2-math', type=int, choices=(0, 1), default=1,
                        help='UCRT libm path flag 0x0bdd1cc8 (1 = SSE2 routines, as on any SSE2 CPU)')
    parser.add_argument('--only', help='regular expression: run only the cases whose label matches')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        summary = validate(args)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
    encoded = json.dumps(summary, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(json.dumps({k: summary[k] for k in ('cases', 'frames_compared', 'vertices_compared',
                                              'particle_records_compared', 'faults_matched', 'mismatches')}))
    return 1 if summary['mismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
