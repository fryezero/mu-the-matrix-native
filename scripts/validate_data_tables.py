#!/usr/bin/env python3
"""Compare the authored data-table decoders with the client (NATIVE-DATA-001).

Two kinds of actual-instruction comparison run in Unicorn over the pinned
restored text and the verified second image section:

1. Codec routines, executed alone with no stubs: the three-byte XOR
   0x00976855 (key read from global 0x01cf0448), its local-key copy
   0x01072ebc, the table checksum 0x00976895 and the package decoder
   0x00f1600f (key global 0x01cf0ea8). Synthetic sizes, alignments, keys and
   key-table contents, plus every installed table image, are compared byte for
   byte (and by return value) with reconstructed/data through ctypes.

2. Table loaders, executed on installed files. The actual loader body runs;
   the CRT calls fopen/fread/fclose/fseek/ftell/feof and operator new/malloc/
   free are modelled over the file bytes, memcpy/memset/c_str and the codec
   routines execute as client code, and every other direct callee (record
   constructors, container inserts, logging) is skipped and returns a dummy
   pointer. Every decoder call (unit length, bytes before and after) and every
   checksum call (length, key, result) is recorded and compared, in order,
   with the unit schedule the authored mu_data_decode produces for the same
   image. Mutations (stored checksum flipped, zero count) must take the
   client's error path (an import call such as MessageBoxA) exactly when the
   authored status reports the error.

Modelled, not client code: the uncaptured .data section (zero-filled), the
key bytes FC CF AB at 0x01cf0448 and 0x01cf0ea8 (the same three bytes the
ServerList decoder 0x01072ebc holds as immediates), the CPU-feature word from
the math capture, the skipped callees, and two loop conditions that depend on
skipped container results (FORCE below). Loader callers are not executed:
they are outside the restored text's reachable code (protected region) and
the loaders are entered directly with a path argument.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
TEXT_BASE, TEXT_BYTES = 0x401000, pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
DATA_BASE, DATA_BYTES = 0x1a7c000, pins.DATA.size
DATA_SHA256 = pins.DATA.sha256
FEATURE_ADDRESS = 0x01cf6618
FEATURE_SHA256 = pins.FEATURE.sha256
SECTION3_BASE, SECTION3_BYTES = 0x1ced000, 0xa0e5000
KEY3 = bytes((0xfc, 0xcf, 0xab))
KEY_GLOBAL, PACKAGE_KEY_GLOBAL = 0x01cf0448, 0x01cf0ea8

XOR3, XOR3_LOCAL, CHECKSUM, XOR3_KEY = 0x00976855, 0x01072ebc, 0x00976895, 0x00f1600f
MEMCPY, MEMSET, CSTR = 0x0194c200, 0x0194cd00, 0x008e7940
FOPEN, FREAD, FCLOSE, FSEEK, FTELL, FEOF = 0x01988f83, 0x01989230, 0x01988c95, 0x01989dab, 0x0198a634, 0x0199430b
NEW, MALLOC, FREE = 0x0191ba7b, 0x0191bab9, 0x0191bac2

# start, exclusive end, SHA-256 of the captured bytes (checked before use)
CODEC_BODIES = {
    'xor3': (0x00976855, 0x00976895, '8d9eb0f5f201e5d8f6075bb4a3caf1e7b478092e607dcf07c0f3e1d424e5ce0d'),
    'checksum': (0x00976895, 0x0097694a, '28a459883c3e577ccd2fad593e5a73ea39c630fdb999b7233bb1d728de78d624'),
    'xor3_local': (0x01072ebc, 0x01072f0d, '5708eddec82b169b718e25e9c68d2fc932b4c7330b049ad7c0deb6f4a57104ea'),
    'xor3_key': (0x00f1600f, 0x00f16067, 'a4e4e90f187316e93ec16365238f6d0ea904dca98ad829a6198684f4bc36916e'),
}

# Loop conditions that read results of skipped container callees.
FORCE = {
    0x00f0ada4: {0x00f0af5f: -0x2c},  # itemtooltip: insert result flag tested after each record
    0x00f0afe2: {0x00f0b1f6: -0x38},  # itemtooltiptext: same pattern
}

STACK, STACK_BYTES = 0x0f000000, 0x100000
HEAP, HEAP_BYTES = 0x20000000, 0x10000000
DUMMY = 0x30000000
SENTINEL = 0x7ff00000
GDT = 0x7fe00000
FILE_HANDLE = 0x40000000


load_pinned = pins.loader(ValueError, 'Input does not match pinned {label}')


class Library:
    def __init__(self, path):
        self.dll = ctypes.CDLL(str(path))
        self.dll.mu_data_xor3.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_char_p]
        self.dll.mu_data_xor3_local.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        self.dll.mu_data_checksum.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32]
        self.dll.mu_data_checksum.restype = ctypes.c_uint32
        self.dll.mu_data_xor3_key.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32]
        self.unit_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32)
        self.dll.mu_data_decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, self.unit_type,
                                            ctypes.c_void_p, ctypes.c_void_p]
        self.dll.mu_data_decode.restype = ctypes.c_int
        self.dll.mu_data_find.argtypes = [ctypes.c_char_p]
        self.dll.mu_data_find.restype = ctypes.c_void_p
        self.dll.mu_data_specs.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
        self.dll.mu_data_specs.restype = ctypes.c_void_p

    def xor3(self, data, size, key=KEY3):
        buffer = ctypes.create_string_buffer(bytes(data), max(len(data), 1))
        self.dll.mu_data_xor3(buffer, size, key)
        return buffer.raw[:len(data)]

    def xor3_local(self, data, size):
        buffer = ctypes.create_string_buffer(bytes(data), max(len(data), 1))
        self.dll.mu_data_xor3_local(buffer, size)
        return buffer.raw[:len(data)]

    def checksum(self, data, key):
        return self.dll.mu_data_checksum(bytes(data), len(data), key)

    def xor3_key(self, data, key, key3=KEY3):
        buffer = ctypes.create_string_buffer(bytes(data), max(len(data), 1))
        self.dll.mu_data_xor3_key(buffer, len(data), key3, key)
        return buffer.raw[:len(data)]

    def specs(self):
        count = ctypes.c_size_t()
        base = self.dll.mu_data_specs(ctypes.byref(count))
        out = []
        for index in range(count.value):
            spec = MuDataSpec.from_address(base+index*ctypes.sizeof(MuDataSpec))
            out.append((base+index*ctypes.sizeof(MuDataSpec), spec))
        return out

    def decode(self, spec_address, image):
        """Run mu_data_decode; return (status, result fields, units, decoded image)."""
        buffer = ctypes.create_string_buffer(bytes(image), max(len(image), 1))
        units = []
        callback = self.unit_type(lambda user, offset, length, codec: units.append((offset, length, codec)))
        result = MuDataResult()
        status = self.dll.mu_data_decode(spec_address, buffer, len(image), callback, None, ctypes.byref(result))
        return status, result, units, buffer.raw[:len(image)]


class MuDataSpec(ctypes.Structure):
    _fields_ = [('file', ctypes.c_char_p), ('path', ctypes.c_char_p), ('loader', ctypes.c_uint32),
                ('kind', ctypes.c_int), ('record_size', ctypes.c_uint32), ('record_count', ctypes.c_uint32),
                ('checksum_key', ctypes.c_uint32), ('codec', ctypes.c_uint32), ('codec_key', ctypes.c_uint32),
                ('flags', ctypes.c_uint32)]


class MuDataResult(ctypes.Structure):
    _fields_ = [('status', ctypes.c_int), ('checksum_stored', ctypes.c_uint32),
                ('checksum_computed', ctypes.c_uint32), ('checksum_offset', ctypes.c_uint32),
                ('checksum_length', ctypes.c_uint32), ('units', ctypes.c_uint32), ('records', ctypes.c_uint32),
                ('records_offset', ctypes.c_size_t), ('consumed', ctypes.c_size_t)]


STATUS = {0: 'ok', 1: 'truncated', 2: 'bad-checksum', 3: 'zero-count', 4: 'bad-header', 5: 'bad-argument'}


class Machine:
    """Pinned client image in Unicorn with flat 32-bit segments and an FS page."""

    def __init__(self, text, data, feature):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_READ, UC_PROT_EXEC, UC_PROT_ALL
        from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_FS, UC_X86_REG_SS
        self.text = text
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, (TEXT_BYTES+0xfff) & ~0xfff, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES+0xfff) & ~0xfff, UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        uc.mem_map(SECTION3_BASE, SECTION3_BYTES, UC_PROT_ALL)
        uc.mem_write(FEATURE_ADDRESS, feature)
        self.set_keys(KEY3, KEY3)
        uc.mem_map(STACK, STACK_BYTES, UC_PROT_ALL)
        uc.mem_map(HEAP, HEAP_BYTES, UC_PROT_ALL)
        uc.mem_map(DUMMY, 0x100000, UC_PROT_ALL)
        uc.mem_map(SENTINEL, 0x1000, UC_PROT_ALL)
        uc.mem_map(GDT, 0x1000, UC_PROT_ALL)
        self.fs = HEAP+HEAP_BYTES-0x1000

        def entry(base, limit, access, flags):
            return struct.pack('<Q', (limit & 0xffff) | (base & 0xffffff) << 16 | access << 40 |
                               ((limit >> 16) & 0xf) << 48 | flags << 52 | (base >> 24) << 56)
        uc.mem_write(GDT+8*3, entry(self.fs, 0xfff, 0xf3, 0x4))
        uc.mem_write(GDT+8*5, entry(0, 0xfffff, 0x93, 0xc))
        uc.reg_write(UC_X86_REG_GDTR, (0, GDT, 0xfff, 0))
        uc.reg_write(UC_X86_REG_FS, (3 << 3) | 3)
        uc.reg_write(UC_X86_REG_SS, 5 << 3)
        self.snapshot = uc.context_save()

    def set_keys(self, key, package_key):
        self.uc.mem_write(KEY_GLOBAL, bytes(key))
        self.uc.mem_write(PACKAGE_KEY_GLOBAL, bytes(package_key))

    def call(self, address, arguments, ecx=0, limit=200_000_000):
        """cdecl/thiscall call with caller-stack arguments; returns eax."""
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EAX, \
            UC_X86_REG_EIP, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI
        uc = self.uc
        esp = STACK+STACK_BYTES-0x2000
        frame = struct.pack('<I', SENTINEL)+b''.join(struct.pack('<I', a & 0xffffffff) for a in arguments)
        uc.mem_write(esp, frame)
        saved = {UC_X86_REG_EBX: 0x11111111, UC_X86_REG_ESI: 0x22222222, UC_X86_REG_EDI: 0x33333333,
                 UC_X86_REG_EBP: 0x44444444}
        for register, value in saved.items():
            uc.reg_write(register, value)
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_ECX, ecx)
        uc.emu_start(address, SENTINEL, count=limit)
        if uc.reg_read(UC_X86_REG_EIP) != SENTINEL:
            raise RuntimeError(f'{address:#x} did not return')
        for register, value in saved.items():
            if uc.reg_read(register) != value:
                raise RuntimeError(f'{address:#x} did not preserve a callee-saved register')
        return uc.reg_read(UC_X86_REG_EAX), uc.reg_read(UC_X86_REG_ESP)-esp


def check_bodies(text):
    out = {}
    for name, (start, end, digest) in CODEC_BODIES.items():
        actual = hashlib.sha256(text[start-TEXT_BASE:end-TEXT_BASE]).hexdigest()
        if actual != digest:
            raise ValueError(f'captured {name} body does not match its pinned digest')
        out[name] = {'start': hex(start), 'end_exclusive': hex(end), 'sha256': actual}
    return out


def codec_cases(machine, library, images):
    """Direct comparisons of the four codec routines."""
    rng = random.Random(0x5eed)
    uc = machine.uc
    buffer = HEAP+0x100000
    counts = {'xor3': 0, 'xor3_local': 0, 'checksum': 0, 'xor3_key': 0}
    failures = []

    def guard_run(address, payload, alignment, arguments, ecx=0, key=KEY3, package_key=KEY3):
        machine.set_keys(key, package_key)
        base = buffer+alignment
        uc.mem_write(buffer-64, b'\xa5'*64)
        uc.mem_write(base, payload)
        uc.mem_write(base+len(payload), b'\x5a'*64)
        eax, cleanup = machine.call(address, [base if a is None else a for a in arguments], ecx=ecx)
        after = bytes(uc.mem_read(base, len(payload)))
        guards = bytes(uc.mem_read(buffer-64, 64)) == b'\xa5'*64 and \
            bytes(uc.mem_read(base+len(payload), 64)) == b'\x5a'*64
        return eax, cleanup, after, guards

    synthetic = []
    for size in list(range(0, 70))+[255, 256, 257, 708, 1000, 4096+3]:
        for alignment in range(4):
            synthetic.append((bytes(rng.randrange(256) for _ in range(size)), alignment))
    keys = [KEY3, b'\x00\x00\x00', b'\x11\x22\x33', b'\xff\x80\x01']
    for payload, alignment in synthetic:
        for key in keys:
            for size in (len(payload), len(payload)-1 if payload else -1, -5):
                eax, cleanup, after, guards = guard_run(XOR3, payload, alignment, [None, size], key=key)
                counts['xor3'] += 1
                if after != library.xor3(payload, size, key) or not guards or cleanup != 4:
                    failures.append(('xor3', len(payload), alignment, size, key.hex()))
        eax, cleanup, after, guards = guard_run(XOR3_LOCAL, payload, alignment, [None, len(payload)], ecx=0x1234)
        counts['xor3_local'] += 1
        if after != library.xor3_local(payload, len(payload)) or not guards or cleanup != 12:
            failures.append(('xor3_local', len(payload), alignment))
        for key in (0, 1, 0xe2f1, 0x12dc, 0xffff, 0x5a18, 0x12345, 0xabcd0000 | 0x7f1d):
            if len(payload) >= 4:
                eax, cleanup, after, guards = guard_run(CHECKSUM, payload, alignment, [None, len(payload), key])
                counts['checksum'] += 1
                if eax != library.checksum(payload, key) or after != payload or not guards or cleanup != 4:
                    failures.append(('checksum', len(payload), alignment, hex(key)))
            for package_key in (KEY3, b'\x10\x20\x30'):
                eax, cleanup, after, guards = guard_run(XOR3_KEY, payload, alignment, [None, len(payload), key],
                                                        package_key=package_key)
                counts['xor3_key'] += 1
                if after != library.xor3_key(payload, key, package_key) or not guards or cleanup != 4:
                    failures.append(('xor3_key', len(payload), alignment, hex(key)))
    installed = 0
    for name, image in images:
        if len(image) < 8 or len(image) > 0x400000:
            continue
        for key in (0xe2f1, 0x5a18, 0xce54):
            eax, _, _, _ = guard_run(CHECKSUM, image, 0, [None, len(image), key])
            installed += 1
            if eax != library.checksum(image, key):
                failures.append(('installed-checksum', name, hex(key)))
        if len(image) <= 0x40000:
            _, _, after, _ = guard_run(XOR3, image, 1, [None, len(image)])
            installed += 1
            if after != library.xor3(image, len(image)):
                failures.append(('installed-xor3', name))
    machine.set_keys(KEY3, KEY3)
    return {'counts': counts, 'installed': installed, 'failures': failures[:20], 'failure_count': len(failures)}


class LoaderTrace:
    """Run one loader with modelled CRT file access; record decoder/checksum calls."""

    def __init__(self, machine, loader, image, string_argument, idle_limit=5000):
        from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED
        import capstone
        self.machine = machine
        self.uc = uc = machine.uc
        uc.context_restore(machine.snapshot)
        machine.set_keys(KEY3, KEY3)
        self.loader, self.image, self.position, self.eof = loader, image, 0, False
        self.events, self.pending, self.heap = [], {}, HEAP
        self.closed, self.post, self.stop, self.idle, self.idle_limit = False, False, None, 0, idle_limit
        self.import_call = None
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        text = machine.text
        body = []
        for instruction in md.disasm(text[loader-TEXT_BASE:loader-TEXT_BASE+0x10000], loader):
            body.append(instruction)
            if instruction.mnemonic == 'ret':
                following = text[instruction.address+instruction.size-TEXT_BASE:][:3]
                if following[:1] == b'\xcc' or following == b'\x55\x8b\xec':
                    break
        self.body_end = body[-1].address+body[-1].size
        targets, returns = set(), {}
        for instruction in body:
            if instruction.mnemonic == 'call':
                try:
                    target = int(instruction.op_str, 16)
                except ValueError:
                    continue
                targets.add(target)
                if target in (XOR3, XOR3_LOCAL, CHECKSUM, XOR3_KEY):
                    returns[instruction.address+instruction.size] = target
        self.allowed = {XOR3, XOR3_LOCAL, CHECKSUM, XOR3_KEY, MEMCPY, MEMSET, CSTR}
        self.hooks = []
        for target in targets | {FOPEN, FREAD, FCLOSE, FSEEK, FTELL, FEOF, NEW, MALLOC, FREE} | self.allowed:
            self.hooks.append(uc.hook_add(UC_HOOK_CODE, self.on_call, begin=target, end=target))
        for address in returns:
            self.hooks.append(uc.hook_add(UC_HOOK_CODE, self.on_return, begin=address, end=address))
        for address, offset in FORCE.get(loader, {}).items():
            self.hooks.append(uc.hook_add(UC_HOOK_CODE, self.on_force, begin=address, end=address,
                                          user_data=offset))
        self.hooks.append(uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.on_unmapped))
        uc.ctl_flush_tb()  # code hooks must apply to blocks translated by earlier runs
        self.cleanups = {}
        self.disassembler = md
        self.string_argument = string_argument

    def close(self):
        for hook in self.hooks:
            self.uc.hook_del(hook)
        self.uc.ctl_flush_tb()

    def allocate(self, size):
        address = self.heap
        self.heap += (size+15) & ~15
        if self.heap > HEAP+HEAP_BYTES-0x2000:
            raise MemoryError('heap model exhausted')
        self.uc.mem_write(address, bytes(size))  # deterministic zero-filled allocations
        return address

    def argument(self, index):
        from unicorn.x86_const import UC_X86_REG_ESP
        esp = self.uc.reg_read(UC_X86_REG_ESP)
        return struct.unpack('<I', self.uc.mem_read(esp+4+4*index, 4))[0]

    def finish(self, eax, cleanup=0):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP
        uc = self.uc
        esp = uc.reg_read(UC_X86_REG_ESP)
        target = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        uc.reg_write(UC_X86_REG_EAX, eax & 0xffffffff)
        uc.reg_write(UC_X86_REG_ESP, esp+4+cleanup)
        uc.reg_write(UC_X86_REG_EIP, target)

    def cleanup_of(self, address):
        if address not in self.cleanups:
            value = 0
            code = self.machine.text[address-TEXT_BASE:address-TEXT_BASE+0x8000]
            for instruction in self.disassembler.disasm(code, address):
                if instruction.mnemonic == 'ret':
                    value = int(instruction.op_str, 16) if instruction.op_str else 0
                    break
            self.cleanups[address] = value
        return self.cleanups[address]

    def on_unmapped(self, uc, access, address, size, value, ignored):
        from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP
        eip = uc.reg_read(UC_X86_REG_EIP)
        if address == eip and not (TEXT_BASE <= address < TEXT_BASE+TEXT_BYTES):
            esp = uc.reg_read(UC_X86_REG_ESP)
            self.import_call = struct.unpack('<I', uc.mem_read(esp, 4))[0]
            self.stop = 'import'
        else:
            self.stop = f'unmapped access {address:#x} at {eip:#x}'
        return False

    def on_force(self, uc, address, size, offset):
        from unicorn.x86_const import UC_X86_REG_EBP
        ebp = uc.reg_read(UC_X86_REG_EBP)
        uc.mem_write((ebp+offset) & 0xffffffff, struct.pack('<I', 1))
        self.events.append(('force', address))

    def on_call(self, uc, address, size, ignored):
        if address == SENTINEL:
            return
        if address == FOPEN:
            self.events.append(('fopen',))
            self.position, self.eof = 0, False
            self.finish(FILE_HANDLE)
        elif address == FREAD:
            pointer, item, count, handle = (self.argument(i) for i in range(4))
            wanted = item*count
            got = self.image[self.position:self.position+wanted]
            whole = len(got)//item if item else 0
            got = got[:whole*item]
            if len(got) < wanted:
                self.eof = True
            if got:
                uc.mem_write(pointer, got)
            self.position += len(got)
            self.events.append(('fread', wanted, len(got)))
            self.idle = 0
            self.finish(whole)
        elif address == FSEEK:
            handle, offset, whence = (self.argument(i) for i in range(3))
            offset = struct.unpack('<i', struct.pack('<I', offset))[0]
            self.position = {0: offset, 1: self.position+offset, 2: len(self.image)+offset}[whence]
            self.eof = False
            self.finish(0)
        elif address == FTELL:
            self.finish(self.position)
        elif address == FEOF:
            self.finish(1 if self.eof else 0)
        elif address == FCLOSE:
            self.events.append(('fclose',))
            self.closed = True
            self.finish(0)
        elif address in (NEW, MALLOC):
            self.finish(self.allocate(self.argument(0)))
        elif address == FREE:
            self.finish(0)
        elif address in (XOR3, XOR3_KEY, CHECKSUM, XOR3_LOCAL):
            from unicorn.x86_const import UC_X86_REG_ESP
            esp = uc.reg_read(UC_X86_REG_ESP)
            back = struct.unpack('<I', uc.mem_read(esp, 4))[0]
            if back in self.pending or not (self.loader <= back < self.body_end):
                return
            pointer, length = self.argument(0), self.argument(1)
            key = self.argument(2) & 0xffff if address in (CHECKSUM, XOR3_KEY) else None
            kind = {XOR3: 'xor3', XOR3_KEY: 'xor3_key', CHECKSUM: 'checksum', XOR3_LOCAL: 'xor3_local'}[address]
            signed = struct.unpack('<i', struct.pack('<I', length))[0]
            span = max(signed, 0) if kind in ('xor3', 'xor3_local') else length
            before = bytes(uc.mem_read(pointer, span)) if span else b''
            self.pending[back] = (kind, pointer, length, span, key, before)
        elif address in self.allowed:
            return
        else:
            self.events.append(('skip', address))
            self.idle += 1
            if self.idle > self.idle_limit:
                self.post = True
                uc.emu_stop()
            self.finish(DUMMY, self.cleanup_of(address))

    def on_return(self, uc, address, size, ignored):
        from unicorn.x86_const import UC_X86_REG_EAX
        if address not in self.pending:
            return
        kind, pointer, length, span, key, before = self.pending.pop(address)
        event = {'kind': kind, 'length': length, 'before': before}
        if kind == 'checksum':
            event.update(key=key, result=uc.reg_read(UC_X86_REG_EAX))
        else:
            event['after'] = bytes(uc.mem_read(pointer, span)) if span else b''
            if key is not None:
                event['key'] = key
        self.events.append(event)
        self.idle = 0

    def run(self, path, limit=4_000_000_000):
        from unicorn import UcError
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EIP
        uc = self.uc
        raw = path.encode('latin1')+b'\0'
        text_address = self.allocate(len(raw))
        uc.mem_write(text_address, raw)
        if self.string_argument:  # MSVC x86 std::string: heap pointer, size, capacity
            argument = self.allocate(24)
            uc.mem_write(argument, struct.pack('<I', text_address)+b'\0'*12+struct.pack('<II', len(raw)-1, 31+len(raw)))
        else:
            argument = text_address
        this = self.allocate(0x40000)
        esp = STACK+STACK_BYTES-0x2000
        uc.mem_write(esp, struct.pack('<II', SENTINEL, argument))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_EBP, 0)
        uc.reg_write(UC_X86_REG_ECX, this)
        try:
            uc.emu_start(self.loader, SENTINEL, count=limit)
        except UcError as error:
            if not self.stop:
                self.stop = f'{error} at {uc.reg_read(UC_X86_REG_EIP):#x}'
        if not self.stop and not self.post and uc.reg_read(UC_X86_REG_EIP) != SENTINEL:
            self.stop = 'instruction limit'
        return self


def uses_string_argument(text, loader):
    """True when the loader passes [ebp+8] to std::string::c_str before fopen."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    previous = None
    for instruction in md.disasm(text[loader-TEXT_BASE:loader-TEXT_BASE+0x300], loader):
        if instruction.mnemonic == 'call' and instruction.op_str == hex(CSTR) and previous == 'ecx, dword ptr [ebp + 8]':
            return True
        if instruction.mnemonic == 'call' and instruction.op_str == hex(FOPEN):
            return False
        previous = instruction.op_str if instruction.mnemonic == 'mov' else previous
    return False


def authored_events(library, spec_address, spec, image):
    status, result, units, decoded = library.decode(spec_address, image)
    events = []
    has_checksum = bool(spec.flags & 1) and result.checksum_length or (bool(spec.flags & 1) and status != 1)
    if spec.flags & 1 and status in (0, 2):
        events.append({'kind': 'checksum', 'length': result.checksum_length, 'key': spec.checksum_key & 0xffff,
                       'result': result.checksum_computed})
    kind = {0: 'xor3', 1: 'xor3_local', 2: 'xor3_key'}
    for offset, length, codec in units:
        event = {'kind': kind[codec], 'length': length, 'before': bytes(image[offset:offset+length]),
                 'after': decoded[offset:offset+length]}
        if codec == 2:
            event['key'] = spec.codec_key & 0xffff
        events.append(event)
    del has_checksum
    return STATUS[status], result, events


def comparable(event):
    out = dict(event)
    if out['kind'] == 'checksum':
        out.pop('before', None)
    return out


def compare_loader(machine, library, spec_address, spec, image, label, path):
    trace = LoaderTrace(machine, spec.loader, image, uses_string_argument(machine.text, spec.loader)).run(path)
    trace.close()
    client = [comparable(e) for e in trace.events if isinstance(e, dict)]
    status, result, authored = authored_events(library, spec_address, spec, image)
    authored = [comparable(e) for e in authored]
    first_difference = None
    for index, (a, b) in enumerate(zip(client, authored)):
        if a != b:
            first_difference = {'index': index, 'client': {k: (v.hex()[:64] if isinstance(v, bytes) else v)
                                                           for k, v in a.items()},
                                'authored': {k: (v.hex()[:64] if isinstance(v, bytes) else v) for k, v in b.items()}}
            break
    if first_difference is None and len(client) != len(authored):
        first_difference = {'index': min(len(client), len(authored)), 'client_events': len(client),
                            'authored_events': len(authored)}
    error_path = trace.stop == 'import'
    completed = trace.stop is None
    body = machine.text[spec.loader-TEXT_BASE:trace.body_end-TEXT_BASE]
    single = single_unit_control(client, authored)
    return {
        'label': label, 'loader': hex(spec.loader), 'authored_status': status,
        'loader_body': {'end_exclusive': hex(trace.body_end), 'sha256': hashlib.sha256(body).hexdigest()},
        'single_unit_control_differs': single,
        'client_outcome': 'error-path' if error_path else ('completed' if completed else trace.stop),
        'post_processing_cut': trace.post, 'import_return': hex(trace.import_call) if trace.import_call else None,
        'client_events': len(client), 'authored_events': len(authored),
        'decode_units': sum(1 for e in client if e['kind'] != 'checksum'),
        'decoded_bytes': sum(len(e.get('after', b'')) for e in client),
        'forced': sum(1 for e in trace.events if not isinstance(e, dict) and e[0] == 'force'),
        'client_rejected': error_path or (completed and not any(e['kind'] != 'checksum' for e in client)),
        'match': first_difference is None and (
            (status == 'ok' and completed and not error_path) or
            (status != 'ok' and (error_path or (completed and not any(e['kind'] != 'checksum' for e in client))))),
        'first_difference': first_difference,
    }


def single_unit_control(client, authored):
    """Negative control: decode each maximal run of adjacent units as one call.

    Returns True when this plausible alternative (one key phase over the whole
    payload) changes the decoded bytes, i.e. the unit boundaries are observable.
    """
    units = [e for e in authored if e['kind'] in ('xor3', 'xor3_local')]
    if len(units) < 2:
        return None
    whole = b''.join(e['before'] for e in units)
    key = KEY3
    merged = bytes(b ^ key[i % 3] for i, b in enumerate(whole))
    return merged != b''.join(e['after'] for e in client if e['kind'] in ('xor3', 'xor3_local'))


def mutations(spec, image):
    """Yield (label, image) mutations with a known client error decision."""
    kind = spec.kind
    if spec.flags & 1 and kind != 13 and len(image) >= 8:
        # flip one bit of the stored checksum word
        result_offset = None
        if kind in (1, 5, 12):   # counted, count-bytes, two-counts: checksum after records
            result_offset = len(image)-4
        elif kind in (2,):
            result_offset = spec.record_count*spec.record_size
        elif kind in (6, 10):
            result_offset = len(image)-4
        if result_offset is not None and result_offset+4 <= len(image):
            mutated = bytearray(image)
            mutated[result_offset] ^= 0x01
            yield 'checksum-flip', bytes(mutated)
    if spec.flags & 4 and kind == 1 and len(image) >= 4:
        mutated = bytearray(image)
        mutated[0:4] = b'\0\0\0\0'
        yield 'zero-count', bytes(mutated)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, default=pins.TEXT.default())
    parser.add_argument('--data', type=Path, default=pins.DATA.default())
    parser.add_argument('--feature', type=Path, default=pins.FEATURE.default())
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/data' /
                        ('libdatatables.dylib' if sys.platform == 'darwin' else 'libdatatables.so'))
    parser.add_argument('--game-root', type=Path, default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--only', help='comma-separated file names')
    parser.add_argument('--skip-codec', action='store_true')
    parser.add_argument('--skip-mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'second image section')
    feature = load_pinned(args.feature, 4, FEATURE_SHA256, 'CPU feature word')
    if not args.game_root:
        raise SystemExit('--game-root or MU_GAME_ROOT is required for installed tables')
    library = Library(args.library)
    machine = Machine(text, data, feature)
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'feature_sha256': FEATURE_SHA256,
              'bodies': check_bodies(text),
              'authored_library_sha256': hashlib.sha256(args.library.read_bytes()).hexdigest()}
    only = set(args.only.split(',')) if args.only else None
    images = []
    root = Path(args.game_root)
    for spec_address, spec in library.specs():
        name = spec.file.decode()
        folder = root/'Data' if name == 'lang.mpr' else root/'Data/Local'
        matches = [p for p in folder.iterdir() if p.name.lower() == name] if folder.is_dir() else []
        if matches:
            images.append((name, matches[0].read_bytes(), spec_address, spec))
    if not args.skip_codec:
        report['codec'] = codec_cases(machine, library, [(n, i) for n, i, _, _ in images])
        print('codec', json.dumps(report['codec']['counts']), 'installed', report['codec']['installed'],
              'failures', report['codec']['failure_count'], flush=True)
    loaders = []
    for name, image, spec_address, spec in images:
        if only and name not in only:
            continue
        path = spec.path.decode() if spec.path else 'Data\\Local\\'+name
        entry = compare_loader(machine, library, spec_address, spec, image, name, path)
        entry['sha256'] = hashlib.sha256(image).hexdigest()
        entry['bytes'] = len(image)
        loaders.append(entry)
        print(json.dumps({k: v for k, v in entry.items() if k != 'first_difference'}), flush=True)
        if entry['first_difference']:
            print('  first difference', json.dumps(entry['first_difference']), flush=True)
        if not args.skip_mutations:
            for label, mutated in mutations(spec, image):
                result = compare_loader(machine, library, spec_address, spec, mutated, f'{name}:{label}', path)
                loaders.append(result)
                print(json.dumps({k: v for k, v in result.items() if k != 'first_difference'}), flush=True)
    report['loaders'] = loaders
    report['summary'] = {
        'loader_cases': len(loaders), 'matches': sum(1 for e in loaders if e['match']),
        'installed_files': sum(1 for e in loaders if ':' not in e['label']),
        'decode_units': sum(e['decode_units'] for e in loaders if ':' not in e['label']),
        'decoded_bytes': sum(e['decoded_bytes'] for e in loaders if ':' not in e['label']),
        'single_unit_control_detected': sum(1 for e in loaders if ':' not in e['label']
                                            and e['single_unit_control_differs']),
        'single_unit_control_applicable': sum(1 for e in loaders if ':' not in e['label']
                                              and e['single_unit_control_differs'] is not None),
        'mutation_cases': sum(1 for e in loaders if ':' in e['label']),
        'mutations_rejected_by_client': sum(1 for e in loaders if ':' in e['label'] and e['client_rejected']),
    }
    print(json.dumps(report['summary']))
    if args.output:
        args.output.write_text(json.dumps(report, indent=1)+'\n')
    ok = report['summary']['matches'] == report['summary']['loader_cases'] and \
        (args.skip_codec or report['codec']['failure_count'] == 0)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
