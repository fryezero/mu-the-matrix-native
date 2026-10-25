#!/usr/bin/env python3
"""Compare the authored static-object loader with the client (NATIVE-OBJECTS-001).

Actual client instructions run in Unicorn over the pinned restored text
(capture09), the second image section (run10) and the runtime capture of the
third section (x86-linux-capture-04/main-01ced000.bin, same restored text):

1. The object loader 0x016d9ac5 (called by OpenWorld 0x0182876e at
   0x01828ce1). The loader body, the v12 decoder 0x0098c5f2, the record
   constructor 0x0180778f, memcpy and memset execute as client code. The CRT
   file calls fopen/fseek/ftell/fread/fclose and malloc/free are modelled over
   the file bytes; sprintf is modelled for the error text; import calls
   (MessageBoxA/SendMessageA) are recorded and return. CreateObject 0x016d8538
   is replaced by a recorder that copies the 0x38-byte record it receives.
   Compared with reconstructed/objects through ctypes: the decoded buffer, the
   return value (map number byte or -1), the count global 0x0bdb5888, and every
   record (bytes 2..3, never written by the client, excluded).

   Inputs: synthetic v12-encoded files (versions 0..7, random field bytes,
   counts including 0 and negative), a missing file, and every installed
   Data/World*/EncTerrain*.obj. For the installed files the report states how
   many decode to a header OpenWorld would accept.

2. The object model pass 0x018392db for every world index 0..149. AccessModel
   0x018202b4 and OpenTexture 0x0181fbe9 are recorded; sprintf is modelled;
   leaf callees (no calls, no indirect jumps before their first ret) execute
   as client code, every other callee is skipped and returns a dummy pointer.
   The model files for types 0..299 are compared with
   mu_objects_model_file(world, type). The runtime custom-map table the pass
   consults (0x0095c652(0x5c)) is a skipped callee: its getter returns a
   zero-filled dummy object, so its predicate answers no.

Nothing here reads the protection modules; calls that leave main.exe are
recorded as imports.
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
SECTION3_BASE, SECTION3_BYTES = 0x1ced000, pins.SECTION3.size
SECTION3_SHA256 = pins.SECTION3.sha256
SECTION3_MAPPED = 0x0bdd2000 - SECTION3_BASE  # through the object globals at 0x0bdb5888

LOADER, OPEN_MODELS = 0x016d9ac5, 0x018392db
V12, CTOR, CREATE = 0x0098c5f2, 0x0180778f, 0x016d8538
MEMCPY, MEMSET, SPRINTF = 0x0194c200, 0x0194cd00, 0x009619dd
FOPEN, FREAD, FCLOSE, FSEEK, FTELL = 0x01988f83, 0x01989230, 0x01988c95, 0x01989dab, 0x0198a634
MALLOC, FREE = 0x0191bab9, 0x0191bac2
ACCESS_MODEL, OPEN_TEXTURE = 0x018202b4, 0x0181fbe9
COUNT_GLOBAL, WORLD_GLOBAL = 0x0bdb5888, 0x01cf15fc
AFTER_DECODE = 0x016d9bbc  # first instruction after the second v12 call
OPEN_MODELS_END = 0x0184307c  # after its ret; the jump tables follow

# start, exclusive end, SHA-256 of the captured bytes (checked before use)
BODIES = {
    'object_loader': (0x016d9ac5, 0x016d9d8c, None),
    'v12_decoder': (0x0098c5f2, 0x0098c6b4, None),
    'record_constructor': (0x0180778f, 0x01807828, None),
    'open_world_object_call': (0x01828cbf, 0x01828d79, None),
    'object_model_pass': (0x018392db, 0x0184307c, None),
    'access_model': (0x018202b4, 0x018203f0, None),
}
PINNED_BODY_SHA256 = {  # first 16 hex digits in the finding
    'object_loader': 'babafe52f3db3c15',
}

STACK, STACK_BYTES = 0x0f000000, 0x100000
HEAP, HEAP_BYTES = 0x20000000, 0x08000000
DUMMY = 0x30000000
SENTINEL = 0x7ff00000
GDT = 0x7fe00000
FILE_HANDLE = 0x40000000
PATH_BUFFER = DUMMY + 0x80000
IMPORT_CLEANUP = {0x01a7c830: 16, 0x01a7c83c: 16}  # MessageBoxA, SendMessageA (stdcall)
IMPORT_STUBS = DUMMY + 0xff000  # each recorded import slot points at its own stub address here

V12_KEY = bytes((0xD1, 0x73, 0x52, 0xF6, 0xD2, 0x9A, 0xCB, 0x27, 0x3E, 0xAF, 0x59, 0x31, 0x37, 0xB3, 0xE7, 0xA2))


def v12_encode(plain):
    """Independent inverse of the client's rolling decoder (immediates of 0x0098c5f2)."""
    out, key = bytearray(len(plain)), 0x5e
    for i, p in enumerate(plain):
        c = ((p + key) & 0xff) ^ V12_KEY[i % 16]
        out[i], key = c, (c + 0x3d) & 0xff
    return bytes(out)


def record_size(version):
    return 30 + (2 if version >= 1 else 0) + (1 if version >= 2 else 0) + (12 if version >= 3 else 0) + \
        (1 if version >= 4 else 0) + (8 if version >= 5 else 0)


load_pinned = pins.loader(ValueError, 'Input does not match pinned {label}')


class MuObjectRecord(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int16), ('pad', ctypes.c_uint8 * 2), ('position', ctypes.c_float * 3),
                ('angle', ctypes.c_float * 3), ('vector', ctypes.c_float * 3), ('scale', ctypes.c_float),
                ('flag_2c', ctypes.c_uint8), ('flag_2d', ctypes.c_uint8), ('flag_2e', ctypes.c_uint8),
                ('hidden', ctypes.c_uint8), ('value_30', ctypes.c_float), ('value_34', ctypes.c_float)]


class MuObjectHeader(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint8), ('map', ctypes.c_uint8), ('count', ctypes.c_int16),
                ('record_size', ctypes.c_int32)]


assert ctypes.sizeof(MuObjectRecord) == 0x38


class Library:
    def __init__(self, path):
        self.dll = ctypes.CDLL(str(path))
        self.dll.mu_bmd12_decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        self.dll.mu_bmd12_decode.restype = ctypes.c_int32
        self.dll.mu_objects_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(MuObjectHeader),
                                              ctypes.POINTER(MuObjectRecord), ctypes.c_int32,
                                              ctypes.POINTER(ctypes.c_int32)]
        self.dll.mu_objects_model_file.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        self.dll.mu_objects_folder.argtypes = [ctypes.c_int32]
        self.dll.mu_objects_record_size.argtypes = [ctypes.c_uint8]

    def decode(self, data):
        source = ctypes.create_string_buffer(bytes(data), max(len(data), 1))
        out = ctypes.create_string_buffer(max(len(data), 1))
        self.dll.mu_bmd12_decode(out, source, len(data))
        return out.raw[:len(data)]

    def parse(self, plain, capacity):
        header = MuObjectHeader()
        records = (MuObjectRecord * max(capacity, 1))()
        parsed = ctypes.c_int32()
        status = self.dll.mu_objects_parse(bytes(plain), len(plain), ctypes.byref(header), records, capacity,
                                           ctypes.byref(parsed))
        return status, header, [bytes(records[i]) for i in range(parsed.value)]

    def model_file(self, world, type_):
        out = ctypes.create_string_buffer(300)
        ok = self.dll.mu_objects_model_file(world, type_, out, 300)
        return out.value.decode() if ok else None


class Machine:
    def __init__(self, text, data, section3):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_READ, UC_PROT_EXEC, UC_PROT_ALL
        from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_FS, UC_X86_REG_SS
        import capstone
        self.text = text
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, (TEXT_BYTES + 0xfff) & ~0xfff, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES + 0xfff) & ~0xfff, UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        uc.mem_map(SECTION3_BASE, SECTION3_MAPPED, UC_PROT_ALL)
        uc.mem_write(SECTION3_BASE, section3)
        uc.mem_map(STACK, STACK_BYTES, UC_PROT_ALL)
        uc.mem_map(HEAP, HEAP_BYTES, UC_PROT_ALL)
        uc.mem_map(DUMMY, 0x100000, UC_PROT_ALL)
        uc.mem_map(SENTINEL, 0x1000, UC_PROT_ALL)
        uc.mem_map(GDT, 0x1000, UC_PROT_ALL)
        self.fs = HEAP + HEAP_BYTES - 0x1000

        def entry(base, limit, access, flags):
            return struct.pack('<Q', (limit & 0xffff) | (base & 0xffffff) << 16 | access << 40 |
                               ((limit >> 16) & 0xf) << 48 | flags << 52 | (base >> 24) << 56)
        uc.mem_write(GDT + 8 * 3, entry(self.fs, 0xfff, 0xf3, 0x4))
        uc.mem_write(GDT + 8 * 5, entry(0, 0xfffff, 0x93, 0xc))
        uc.reg_write(UC_X86_REG_GDTR, (0, GDT, 0xfff, 0))
        uc.reg_write(UC_X86_REG_FS, (3 << 3) | 3)
        uc.reg_write(UC_X86_REG_SS, 5 << 3)
        self.cleanups, self.leaves = {}, {}
        # Imports the loader can reach: point their slots at stub addresses (the
        # slot values are kernel32/user32 addresses of the capture run).
        self.stubs = {}
        for index, slot in enumerate(sorted(IMPORT_CLEANUP)):
            stub = IMPORT_STUBS + 16 * index
            uc.mem_write(stub, b'\xc3')
            uc.mem_write(slot, struct.pack('<I', stub))
            self.stubs[stub] = slot

    # --- helpers -----------------------------------------------------------------
    def cstr(self, address, limit=512):
        raw = bytes(self.uc.mem_read(address, limit))
        return raw.split(b'\0')[0].decode('latin1')

    def argument(self, index):
        from unicorn.x86_const import UC_X86_REG_ESP
        esp = self.uc.reg_read(UC_X86_REG_ESP)
        return struct.unpack('<I', self.uc.mem_read(esp + 4 + 4 * index, 4))[0]

    def finish(self, eax, cleanup=0):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP
        uc = self.uc
        esp = uc.reg_read(UC_X86_REG_ESP)
        target = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        uc.reg_write(UC_X86_REG_EAX, eax & 0xffffffff)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + cleanup)
        uc.reg_write(UC_X86_REG_EIP, target)

    def scan(self, address):
        """(ret cleanup, is_leaf) from a linear walk to the first ret."""
        if address not in self.cleanups:
            cleanup, leaf = 0, True
            code = self.text[address - TEXT_BASE:address - TEXT_BASE + 0x4000]
            for instruction in self.md.disasm(code, address):
                if instruction.mnemonic == 'call' or (instruction.mnemonic == 'jmp' and
                                                      not instruction.op_str.startswith('0x')):
                    leaf = False
                if instruction.mnemonic == 'ret':
                    cleanup = int(instruction.op_str, 16) if instruction.op_str else 0
                    break
            self.cleanups[address], self.leaves[address] = cleanup, leaf
        return self.cleanups[address], self.leaves[address]

    def sprintf(self):
        destination, fmt = self.argument(0), self.cstr(self.argument(1))
        out, index, i = '', 2, 0
        while i < len(fmt):
            if fmt[i] != '%':
                out += fmt[i]
                i += 1
                continue
            j = i + 1
            while fmt[j] in '0123456789-':
                j += 1
            kind, flags = fmt[j], fmt[i + 1:j]
            value = self.argument(index)
            index += 1
            if kind == 's':
                out += self.cstr(value)
            elif kind == 'd':
                out += ('%' + flags + 'd') % struct.unpack('<i', struct.pack('<I', value))[0]
            else:
                raise ValueError(f'unmodelled sprintf conversion %{kind}')
            i = j + 1
        self.uc.mem_write(destination, out.encode('latin1') + b'\0')
        return len(out)

    def reset_section3(self, section3):
        self.uc.mem_write(SECTION3_BASE, section3)

    def run(self, address, arguments, ecx=0, limit=400_000_000):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EAX, \
            UC_X86_REG_EIP, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI
        uc = self.uc
        esp = STACK + STACK_BYTES - 0x4000
        frame = struct.pack('<I', SENTINEL) + b''.join(struct.pack('<I', a & 0xffffffff) for a in arguments)
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
        return uc.reg_read(UC_X86_REG_EAX), uc.reg_read(UC_X86_REG_ESP) - esp


class LoaderRun:
    """0x016d9ac5 on one file image (None = missing file)."""

    def __init__(self, machine, image):
        from unicorn import UC_HOOK_CODE
        self.m, self.uc, self.image = machine, machine.uc, image
        self.position, self.heap, self.records, self.imports = 0, HEAP, [], []
        self.decoded, self.events = None, []
        hooks = []
        for target in (FOPEN, FREAD, FCLOSE, FSEEK, FTELL, MALLOC, FREE, CREATE, SPRINTF):
            hooks.append(self.uc.hook_add(UC_HOOK_CODE, self.on_call, begin=target, end=target))
        hooks.append(self.uc.hook_add(UC_HOOK_CODE, self.on_decoded, begin=AFTER_DECODE, end=AFTER_DECODE))
        for stub in machine.stubs:
            hooks.append(self.uc.hook_add(UC_HOOK_CODE, self.on_import, begin=stub, end=stub))
        self.hooks = hooks
        self.uc.ctl_flush_tb()

    def close(self):
        for hook in self.hooks:
            self.uc.hook_del(hook)
        self.uc.ctl_flush_tb()

    def allocate(self, size):
        address = self.heap
        self.heap += (size + 0x10f) & ~15   # 0x100 guard gap
        if self.heap > HEAP + HEAP_BYTES - 0x2000:
            raise MemoryError('heap model exhausted')
        return address

    def on_import(self, uc, address, size, ignored):
        slot = self.m.stubs[address]
        self.imports.append(hex(slot))
        self.m.finish(1, IMPORT_CLEANUP[slot])

    def on_decoded(self, uc, address, size, ignored):
        from unicorn.x86_const import UC_X86_REG_EBP
        ebp = uc.reg_read(UC_X86_REG_EBP)
        buffer = struct.unpack('<I', uc.mem_read(ebp - 0xc, 4))[0]
        length = struct.unpack('<I', uc.mem_read(ebp - 0x18, 4))[0]
        self.decoded = bytes(uc.mem_read(buffer, length))

    def on_call(self, uc, address, size, ignored):
        m = self.m
        if address == FOPEN:
            self.events.append(('fopen', m.cstr(m.argument(0)), m.cstr(m.argument(1))))
            self.position = 0
            m.finish(FILE_HANDLE if self.image is not None else 0)
        elif address == FSEEK:
            handle, offset, origin = m.argument(0), struct.unpack('<i', struct.pack('<I', m.argument(1)))[0], \
                m.argument(2)
            base = {0: 0, 1: self.position, 2: len(self.image)}[origin]
            self.position = base + offset
            m.finish(0)
        elif address == FTELL:
            m.finish(self.position)
        elif address == FREAD:
            pointer, item, count = m.argument(0), m.argument(1), m.argument(2)
            got = self.image[self.position:self.position + item * count]
            whole = len(got) // item if item else 0
            got = got[:whole * item]
            if got:
                uc.mem_write(pointer, got)
            self.position += len(got)
            self.events.append(('fread', item * count, len(got)))
            m.finish(whole)
        elif address == FCLOSE:
            self.events.append(('fclose',))
            m.finish(0)
        elif address == MALLOC:
            m.finish(self.allocate(m.argument(0)))
        elif address == FREE:
            m.finish(0)
        elif address == SPRINTF:
            m.finish(m.sprintf())
        elif address == CREATE:
            self.records.append(bytes(uc.mem_read(m.argument(0), 0x38)))
            m.finish(1)

    def run(self):
        self.uc.mem_write(PATH_BUFFER, b'Data\\World1\\EncTerrain1.obj\0')
        self.uc.mem_write(COUNT_GLOBAL, struct.pack('<I', 0xdeadbeef))
        eax, cleanup = self.m.run(LOADER, [PATH_BUFFER])
        count = struct.unpack('<i', self.uc.mem_read(COUNT_GLOBAL, 4))[0]
        return struct.unpack('<i', struct.pack('<I', eax))[0], cleanup, count


def mask(record):
    return record[:2] + b'\0\0' + record[4:]


def compare_loader(machine, library, image, expect_records=True):
    run = LoaderRun(machine, image)
    try:
        result, cleanup, count = run.run()
    finally:
        run.close()
    problems = []
    if cleanup != 4:   # cdecl: only the return address is popped
        problems.append('stack')
    if image is None:
        if result != -1 or run.records or len(run.imports) != 2:
            problems.append('missing-file path')
        return {'result': result, 'imports': run.imports, 'problems': problems}
    authored = library.decode(image)
    if run.decoded != authored:
        problems.append('decode')
    if expect_records:
        if [mask(r) for r in run.records] != python_records(authored):
            problems.append('python-model')
        result_mistakes = [m for m in MISTAKES if [mask(r) for r in run.records] != python_records(authored, m)]
    else:
        result_mistakes = []
    status, header, records = library.parse(authored, 40000)
    if result != header.map:
        problems.append('return')
    if count != header.count:
        problems.append('count-global')
    if expect_records:
        if status != 0:
            problems.append(f'authored-status-{status}')
        if [mask(r) for r in run.records] != [mask(r) for r in records]:
            problems.append('records')
    else:
        # The client walks max(count, 0) records even past the buffer; compare the in-bounds ones.
        if len(run.records) != max(header.count, 0):
            problems.append('record-calls')
        n = len(records)
        if [mask(r) for r in run.records[:n]] != [mask(r) for r in records]:
            problems.append('records-in-bounds')
    return {'result': result, 'count': count, 'status': status, 'version': header.version,
            'records': len(run.records), 'problems': problems, 'mistakes_detected': result_mistakes}


def python_records(plain, mistake=None):
    """Independent Python statement of the loader walk, with optional planted mistakes
    (negative controls the client comparison must reject)."""
    version, count = plain[0], struct.unpack_from('<h', plain, 2)[0]
    if mistake == 'version-gt':
        version = max(version - 1, 0)
    offset, out = 4, []
    for _ in range(max(count, 0)):
        rec = bytearray(0x38)
        struct.pack_into('<f', rec, 0x28, 1.0)
        rec[0x2c:0x30] = bytes((0, 0, 0, 0)) if mistake == 'flags-default-0' else bytes((1, 1, 1, 0))
        struct.pack_into('<ff', rec, 0x30, 0.8, 0.2)
        if offset + record_size(version) > len(plain):
            break
        p = plain[offset:offset + record_size(version)]
        rec[0:2] = p[0:2]
        rec[4:16] = p[2:14]
        rec[0x10:0x1c] = p[14:26]
        rec[0x28:0x2c] = p[26:30]
        q = 30
        if version >= 1:
            rec[0x2c:0x2e] = p[q:q + 2]
            q += 2
        if version >= 2:
            rec[0x2e] = p[q]
            q += 1
        if version >= 3:
            if mistake == 'vector-after-hidden' and version >= 4:
                rec[0x2f] = p[q]
                rec[0x1c:0x28] = p[q + 1:q + 13]
            else:
                rec[0x1c:0x28] = p[q:q + 12]
            q += 12
        if version >= 4:
            if mistake != 'vector-after-hidden':
                rec[0x2f] = p[q]
            q += 1
        if version >= 5:
            if mistake == 'swap-30-34':
                rec[0x30:0x34], rec[0x34:0x38] = p[q + 4:q + 8], p[q:q + 4]
            else:
                rec[0x30:0x38] = p[q:q + 8]
            q += 8
        offset += record_size(version)
        out.append(bytes(rec))
    return out


MISTAKES = ('version-gt', 'flags-default-0', 'vector-after-hidden', 'swap-30-34')


def synthetic_images(rng, total):
    images = []
    for index in range(total):
        version = index % 8
        count = rng.choice([0, 1, 2, 3, 5, 17, rng.randrange(0, 60)])
        body = bytearray([version, rng.randrange(256)]) + struct.pack('<h', count)
        for _ in range(count):
            record = bytearray(rng.randrange(256) for _ in range(record_size(version)))
            if rng.random() < 0.7:   # plausible floats in some records
                struct.pack_into('<h3f3ff', record, 0, rng.randrange(-5, 300), rng.uniform(0, 25600),
                                 rng.uniform(0, 25600), rng.uniform(-200, 600), 0.0, 0.0, rng.uniform(0, 360),
                                 rng.uniform(0.5, 2.0))
            body += record
        images.append(bytes(body))
    # Negative counts: the loop runs zero times.
    images.append(bytes([3, 7]) + struct.pack('<h', -1) + bytes(45))
    images.append(bytes([0, 7]) + struct.pack('<h', -32768))
    return images


class ModelRun:
    """0x018392db for one world: recorded AccessModel/OpenTexture/CreateObject calls."""

    def __init__(self, machine):
        from unicorn import UC_HOOK_CODE
        self.m, self.uc = machine, machine.uc
        targets = set()
        code = machine.text[OPEN_MODELS - TEXT_BASE:OPEN_MODELS_END - TEXT_BASE]
        for instruction in machine.md.disasm(code, OPEN_MODELS):
            if instruction.mnemonic == 'call' and instruction.op_str.startswith('0x'):
                targets.add(int(instruction.op_str, 16))
        self.executed = {MEMSET, MEMCPY, 0x0191c5a0}  # memset, memcpy, the stack probe
        self.hooks = [self.uc.hook_add(UC_HOOK_CODE, self.on_call, begin=t, end=t)
                      for t in targets | {ACCESS_MODEL, OPEN_TEXTURE, CREATE, SPRINTF} if t not in self.executed]
        self.uc.ctl_flush_tb()
        self.log, self.skipped, self.leaf_runs = [], {}, {}

    def close(self):
        for hook in self.hooks:
            self.uc.hook_del(hook)
        self.uc.ctl_flush_tb()

    def on_call(self, uc, address, size, ignored):
        from unicorn.x86_const import UC_X86_REG_ESP
        m = self.m
        back = struct.unpack('<I', uc.mem_read(uc.reg_read(UC_X86_REG_ESP), 4))[0]
        if not (OPEN_MODELS <= back < OPEN_MODELS_END):
            return  # reached from an executed callee, not from the pass itself
        if address == SPRINTF:
            m.finish(m.sprintf())
        elif address == ACCESS_MODEL:
            number = struct.unpack('<i', struct.pack('<I', m.argument(3)))[0]
            self.log.append(('model', m.argument(0), m.cstr(m.argument(1)), m.cstr(m.argument(2)), number))
            m.finish(0)
        elif address == OPEN_TEXTURE:
            self.log.append(('texture', m.argument(0), m.cstr(m.argument(1)), m.argument(2), m.argument(3)))
            m.finish(0)
        elif address == CREATE:
            self.log.append(('create', bytes(uc.mem_read(m.argument(0), 0x38)).hex()))
            m.finish(1)
        else:
            cleanup, leaf = m.scan(address)
            if leaf:
                self.leaf_runs[hex(address)] = self.leaf_runs.get(hex(address), 0) + 1
                return  # execute the client's leaf routine
            self.skipped[hex(address)] = self.skipped.get(hex(address), 0) + 1
            m.finish(DUMMY, cleanup)

    def run(self, world):
        self.log = []
        self.uc.mem_write(WORLD_GLOBAL, struct.pack('<i', world))
        self.uc.mem_write(DUMMY, bytes(0x10000))
        self.m.run(OPEN_MODELS, [])
        return self.log


def model_path(entry):
    _, index, folder, name, number = entry
    if number == -1:
        file = f'{name}.bmd'
    elif number < 10:
        file = f'{name}0{number}.bmd'
    else:
        file = f'{name}{number}.bmd'
    return (folder + file).replace('\\', '/')


def compare_models(machine, library, worlds):
    run = ModelRun(machine)
    out, failures, totals = {}, [], {'types_compared': 0, 'models_recorded': 0}
    try:
        for world in worlds:
            log = run.run(world)
            models = [e for e in log if e[0] == 'model']
            totals['models_recorded'] += len(models)
            client = {}
            for entry in models:
                if entry[1] < 300:
                    client[entry[1]] = model_path(entry)
            folders = sorted({e[2] for e in models if e[3] == 'Object'})
            for type_ in range(300):
                authored = library.model_file(world, type_)
                totals['types_compared'] += 1
                if authored != client.get(type_):
                    failures.append((world, type_, client.get(type_), authored))
            out[str(world)] = {'models': len(models), 'types_below_300': len(client),
                               'object_folders': folders,
                               'extra_models_300_plus': len([e for e in models if e[1] >= 300]),
                               'textures': len([e for e in log if e[0] == 'texture']),
                               'creates': len([e for e in log if e[0] == 'create'])}
    finally:
        run.close()
    return {'worlds': out, 'totals': totals, 'failures': failures[:20], 'failure_count': len(failures),
            'skipped_callees': run.skipped, 'executed_leaf_callees': run.leaf_runs}


def installed_objects(game_root):
    data = Path(game_root) / 'Data'
    out = []
    for folder in sorted(data.glob('World*')):
        for path in sorted(folder.glob('EncTerrain*.obj')):
            try:
                number = int(path.stem[len('EncTerrain'):])
            except ValueError:
                continue
            out.append((folder.name, number, path))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, default=pins.TEXT.default())
    parser.add_argument('--data', type=Path, default=pins.DATA.default())
    parser.add_argument('--section3', type=Path, default=pins.SECTION3.default())
    parser.add_argument('--library', type=Path,
                        default=ROOT / 'reconstructed/objects' /
                        ('libobjects.dylib' if sys.platform == 'darwin' else 'libobjects.so'))
    parser.add_argument('--game-root', type=Path, default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--synthetic', type=int, default=400)
    parser.add_argument('--worlds', default='0-199')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text (capture09)')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'second image section (run10)')
    section3 = load_pinned(args.section3, SECTION3_BYTES, SECTION3_SHA256, 'third section (x86-linux-capture-04)')
    bodies = {}
    for name, (start, end, _) in BODIES.items():
        digest = hashlib.sha256(text[start - TEXT_BASE:end - TEXT_BASE]).hexdigest()
        if name in PINNED_BODY_SHA256 and not digest.startswith(PINNED_BODY_SHA256[name]):
            raise ValueError(f'{name} body does not match the digest in the terrain finding')
        bodies[name] = {'start': hex(start), 'end_exclusive': hex(end), 'bytes': end - start, 'sha256': digest}

    library = Library(args.library)
    machine = Machine(text, data, section3)
    report = {'inputs': {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'section3_sha256': SECTION3_SHA256},
              'bodies': bodies}

    # 1. Loader, synthetic files.
    rng = random.Random(0x0b1ec7)
    failures, cases, records, detected = [], 0, 0, set()
    for image in synthetic_images(rng, args.synthetic):
        result = compare_loader(machine, library, v12_encode(image))
        cases += 1
        records += result['records']
        detected.update(result['mistakes_detected'])
        if result['problems']:
            failures.append((cases, result))
    missing = compare_loader(machine, library, None)
    cases += 1
    if missing['problems']:
        failures.append(('missing', missing))
    report['loader_synthetic'] = {'cases': cases, 'records_compared': records, 'missing_file': missing,
                                  'negative_controls': {m: m in detected for m in MISTAKES},
                                  'failures': failures[:10], 'failure_count': len(failures)}
    print(f'loader, synthetic: {cases - len(failures)}/{cases} cases match ({records} records); '
          f'planted mistakes detected {len(detected)}/{len(MISTAKES)}')
    if len(detected) != len(MISTAKES):
        failures.append(('negative-controls', sorted(set(MISTAKES) - detected)))
        report['loader_synthetic']['failure_count'] = len(failures)

    # 2. Loader, installed files.
    if args.game_root:
        installed = []
        accepted = 0
        for folder, number, path in installed_objects(args.game_root):
            image = path.read_bytes()
            result = compare_loader(machine, library, image, expect_records=False)
            plain = library.decode(image)
            version, map_number, count = plain[0], plain[1], struct.unpack_from('<h', plain, 2)[0]
            fits = count >= 0 and 4 + count * record_size(version) == len(image)
            would_accept = result['result'] == number   # OpenWorld's only check
            accepted += would_accept
            installed.append({'folder': folder, 'number': number, 'bytes': len(image),
                              'sha256': hashlib.sha256(image).hexdigest()[:16], 'client_return': result['result'],
                              'client_count': result['count'], 'header_fits_length': fits,
                              'openworld_accepts': would_accept, 'problems': result['problems']})
        bad = [e for e in installed if e['problems']]
        report['loader_installed'] = {'files': len(installed), 'matching_authored': len(installed) - len(bad),
                                      'openworld_would_accept': accepted,
                                      'header_fits_length': sum(e['header_fits_length'] for e in installed),
                                      'files_detail': installed}
        print(f'loader, installed: {len(installed) - len(bad)}/{len(installed)} files match the authored decode; '
              f'OpenWorld would accept {accepted}, header fits the length for '
              f'{report["loader_installed"]["header_fits_length"]}')

    # 3. Model table.
    low, high = (int(x) for x in args.worlds.split('-'))
    machine.reset_section3(section3)
    models = compare_models(machine, library, range(low, high + 1))
    report['model_table'] = models
    worlds = high - low + 1
    print(f'model table: {models["totals"]["types_compared"] - models["failure_count"]}/'
          f'{models["totals"]["types_compared"]} (world, type) pairs match over {worlds} worlds; '
          f'{models["totals"]["models_recorded"]} AccessModel calls recorded')

    if args.output:
        args.output.write_text(json.dumps(report, indent=1, default=str))
    ok = not report['loader_synthetic']['failure_count'] and not models['failure_count'] and \
        all(not e['problems'] for e in report.get('loader_installed', {}).get('files_detail', []))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
