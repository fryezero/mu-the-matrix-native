#!/usr/bin/env python3
"""Compare the authored BMD bone-track loop with the captured client instructions.

The actual loop 0x012b4225..0x012b4441, client memcpy 0x0194c200, the client
operator new/malloc chain and rotation helper 0x00d00724 with its actual trig
helpers all run in Unicorn over the pinned restored text, the verified second
image section, the captured dispatch flag and the captured memcpy feature word.
No client instruction is stubbed. Two explicit boundaries are modelled:

* HeapAlloc. malloc calls through IAT slot 0x01a7c5c8 into the Wine ntdll
  (not client code). The harness maps an authored two-instruction stub at the
  slot target that returns a deterministic bump-allocated, poison-filled block
  and checks the (heap, flags, size) arguments.
* Two uncaptured globals: the CRT heap handle at 0x0bdcfc10 (a synthetic token
  readable only by the malloc instruction that passes it on) and memcpy's
  second feature word at 0x0bdcb284 (synthetic values 0, 1 and 2 are exercised).

Any other read of uncaptured bytes, of unwritten allocation/bone bytes, or of
undeclared caller-frame slots stops the case.
"""
import argparse
import ctypes
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
FLAG_ADDRESS = 0x0bdd1cc8
FLAG_SHA256 = '67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450'
FEATURE_ADDRESS = 0x01cf6618
FEATURE_SHA256 = 'bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9'
SYNTHETIC_FEATURE = 0x0bdcb284
HEAP_HANDLE = 0x0bdcfc10
HEAP_HANDLE_READER = 0x019a4dcf
HEAP_TOKEN = 0x00520000
IAT_SLOT, IAT_TARGET, IAT_RETURN = 0x01a7c5c8, 0x7bc275e0, 0x019a4ddb
LOOP_START, LOOP_END = 0x012b4225, 0x012b4441
BODIES = {  # start, exclusive end, SHA-256 of captured bytes
    'loop': (LOOP_START, LOOP_END, 'f64d0af94eadadc0a2b603d02d64afe9894a5d43f1a8842baf4f6fdeb95d835c'),
    'memcpy': (0x0194c200, 0x0194c774, 'a54559a3343e0eba7db605526a5e3605108e176e3fbc590a2439578fb4df3936'),
    'operator_new': (0x0191bab9, 0x0191bac2, '8bb78a0e58a9fce635c1116508eb5fc00f0a0b92d2d08abd06f1dc6c97b3de4c'),
    'new_retry': (0x0191ba7b, 0x0191ba9c, '6e821d9b924a3ea12912c009fff2838c20afcff60ec472f3e5702e60528b4a84'),
    'malloc_jump': (0x01983110, 0x0198311b, '8b641bf9120fd530c5eb92f525a94c7d6676eb4346c08f12cde44f35ab45b9d4'),
    'malloc': (0x019a4da0, 0x019a4df1, '8f5fc5d10bcd43802516fcb240b671f03663a02f68e100c1dd4f396d82f4a204'),
    'rotation': (0x00d00724, 0x00d008bf, '1d585a53f706aed8dd37de105b739b739905065deb41350a02fe83d9153e53a2'),
}
MEMCPY, ROTATION, NEW = 0x0194c200, 0x00d00724, 0x0191bab9
CALLS = {0x12b4282: MEMCPY, 0x12b42be: NEW, 0x12b4345: NEW, 0x12b4376: NEW, 0x12b43a8: NEW,
         0x12b43cf: MEMCPY, 0x12b43f0: MEMCPY, 0x12b442e: ROTATION}
MEMCPY_PATHS = {0x194c24e: 'rep-movsb', 0x194c296: 'sse2-palignr', 0x194c427: 'dword-forward',
                0x194c442: 'dword-unaligned-source', 0x194c4b4: 'backward', 0x194c650: 'sse2-coaligned',
                0x194c6cd: 'sse2-unaligned-32-127', 0x194c6fb: 'small-tail'}
# Caller frame (EBP-relative) slots the loop may read before writing in a case.
FRAME_INPUTS = {-0x10: 'stream offset', -0x14: 'model object', -0x18: 'stream base'}
ZEROING_ANDS = {0x12b4225, 0x12b42d6, 0x12b4401}  # AND [slot], 0 reads its old value
FRAME_SCRATCH = {-0x10, -0x20, -0x24, -0x2c, -0x34, -0x38, -0x3c, -0x44, -0x114, -0x118, -0x11c, -0x120}
FRAME_BYTES = 0x470  # reader prologue: three pushes then SUB ESP, 0x464
WINDOW = 0x40000000
STACK, STACK_BYTES = 0x31000000, 0x10000
FRAME_BASE = STACK + 0xc000  # EBP
STUB_PAGE, STUB_RESULT = 0x7bc27000, 0x7bc27f00
FPCW, MXCSR = 0x027f, 0x1f80
MALLOC_LIMIT = 0xffffffe0
FEATURE_VALUES = (0, 1, 2)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def load_pinned(path, size, digest, label):
    payload = Path(path).read_bytes()
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input does not match pinned {label}')
    return payload


def saturating(a, b):
    product = (a & 0xffffffff)*b
    return 0xffffffff if product >> 32 else product


def align(value, boundary=16):
    return (value+boundary-1) & -boundary


class Heap:
    """Deterministic bump allocator shared by both sides of a comparison."""

    def __init__(self, base, limit):
        self.base, self.limit, self.cursor, self.blocks = base, limit, base, []

    def allocate(self, size):
        address = align(self.cursor+16)
        if address+size > self.limit:
            raise ValueError('Harness heap exhausted')
        self.cursor = address+size
        self.blocks.append((address, size))
        index = len(self.blocks)
        poison = bytes(((index*29+offset*7+0x5a) & 0xff) | 0x80 for offset in range(size))
        return address, poison


# --------------------------------------------------------------------------
# Case construction.


def heap_need(actions, bones, action_field=None):
    """Upper bound of heap bytes the loop can request for disjoint layouts."""
    total = 0
    count = len(actions) if action_field is None else max(action_field, 0)
    for bone in bones:
        if bone.get('dummy', 0):
            continue
        total += align(max(count*12, 1)+16)
        for keys in actions[:count]:
            k = max(keys, 0)
            total += 2*align(max(k*12, 1)+16)+align(max(k*16, 1)+16)
    return total+4096


def bone_stream(bone, actions):
    flag = bone.get('dummy', 0)
    record = bytes([flag])
    if flag:
        return record
    record += bone['name'].ljust(32, b'\0')[:32]+struct.pack('<h', bone['parent'])
    for (positions, rotations), keys in zip(bone['tracks'], actions):
        record += b''.join(p if isinstance(p, bytes) else struct.pack('<3f', *p) for p in positions)
        record += b''.join(struct.pack('<3f', *r) for r in rotations)
    return record


def build_case(label, actions, bones, *, stream=None, start=None, stream_align=0, layout='disjoint',
               bone_field=None, action_field=None, prefix=b'', suffix=b'\x5c'*48, heap_bytes=None):
    """Return a window image, defined-byte mask and the loop arguments."""
    if stream is None:
        stream = prefix+b''.join(bone_stream(bone, actions) for bone in bones)+suffix
        start = len(prefix)
    bone_count = len(bones) if bone_field is None else bone_field
    action_count = len(actions) if action_field is None else action_field
    model = WINDOW
    action_array = WINDOW+0x100
    action_bytes = max(len(actions), 1)*16
    bone_array = align(action_array+action_bytes, 16)
    bone_bytes = max(len(bones), 1)*0x8c
    stream_base = align(bone_array+bone_bytes, 16)+0x40+stream_align
    if layout.startswith('bones-over-stream'):
        delta = int(layout.split(':')[1])
        bone_array = stream_base+delta
    stream_end = stream_base+len(stream)
    if layout == 'actions-in-bone-name':
        action_array = bone_array+4
    heap_base = align(max(stream_end, bone_array+bone_bytes, action_array+action_bytes)+0x100, 0x1000)
    need = heap_need(actions, bones, action_field) if heap_bytes is None else heap_bytes
    size = align(heap_base-WINDOW+need, 0x1000)
    image = bytearray(((index*13+0x31) & 0x7f) | 0x40 for index in range(size))
    defined = bytearray(size)

    def define(address, payload):
        offset = address-WINDOW
        image[offset:offset+len(payload)] = payload
        defined[offset:offset+len(payload)] = b'\1'*len(payload)

    define(model+0x22, struct.pack('<hhh', bone_count, 0, action_count))
    define(model+0x2c, struct.pack('<II', bone_array, action_array))
    for index, keys in enumerate(actions):
        entry = action_array+index*16
        define(entry, b'\0')
        define(entry+8, struct.pack('<hB', keys, 0))
        define(entry+12, b'\0\0\0\0')
    define(stream_base, stream)
    if layout == 'actions-in-bone-name':
        # Keep the declared action fields when the bone array lies over them.
        for index, keys in enumerate(actions):
            define(action_array+index*16+8, struct.pack('<h', keys))
    return {'label': label, 'image': bytes(image), 'defined': bytes(defined), 'model': model,
            'stream': stream_base, 'start': start, 'heap': (heap_base, WINDOW+size),
            'bones': bone_count, 'actions': action_count}


def synthetic_cases():
    generator = random.Random(0x12b42ae)

    def angle():
        return f32(generator.uniform(-4*math.pi, 4*math.pi))

    def position():
        return f32(generator.uniform(-200, 200))

    def bone(actions, name=None, parent=-1, dummy=0):
        if dummy:
            return {'dummy': dummy}
        name = name or bytes(generator.randrange(32, 127) for _ in range(generator.randrange(1, 32)))
        return {'dummy': 0, 'name': name, 'parent': parent,
                'tracks': [([(position(), position(), position()) for _ in range(k)],
                            [(angle(), angle(), angle()) for _ in range(k)]) for k in actions]}

    cases = []
    cases.append(build_case('zero-bones', [3], []))
    cases.append(build_case('zero-actions', [], [bone([]) for _ in range(3)]))
    cases.append(build_case('zero-keys', [0], [bone([0]), bone([0], parent=0)]))
    cases.append(build_case('zero-and-nonzero-keys', [0, 2, 0], [bone([0, 2, 0]) for _ in range(2)]))
    cases.append(build_case('all-dummy', [2, 1], [bone([], dummy=flag) for flag in (1, 0x80, 0xff)]))
    for flags in ((0, 1, 0), (1, 0, 1, 0), (2, 0, 0x7f, 0)):
        actions = [1, 2]
        bones = [bone(actions, dummy=flag, parent=index-1) for index, flag in enumerate(flags)]
        cases.append(build_case('mixed-dummy', actions, bones))
    for parent in (-1, 0, 5, 0x7fff, -32768, -2):
        cases.append(build_case('raw-parent', [1], [bone([1], parent=parent)]))
    cases.append(build_case('name-full-32', [1], [bone([1], name=bytes(range(65, 97)))]))
    # Key counts across memcpy size thresholds (12*keys vs 32/128 bytes).
    for keys in (1, 2, 3, 5, 10, 11, 16, 64, 300):
        for stream_align in (0, 1, 4, 8, 12):
            cases.append(build_case('key-count', [keys], [bone([keys])], stream_align=stream_align,
                                    prefix=bytes(generator.randrange(256) for _ in range(generator.randrange(0, 20)))))
    cases.append(build_case('many-keys', [2000], [bone([2000])]))
    cases.append(build_case('many-actions', [1, 0, 7, 2, 13, 1, 0, 4, 3, 2, 1],
                            [bone([1, 0, 7, 2, 13, 1, 0, 4, 3, 2, 1]) for _ in range(4)]))
    many = [generator.randrange(0, 9) for _ in range(5)]
    cases.append(build_case('many-bones', many,
                            [bone(many, dummy=0 if generator.random() < .7 else 1) for _ in range(60)]))
    for _ in range(40):
        actions = [generator.randrange(0, 12) for _ in range(generator.randrange(0, 5))]
        bones = [bone(actions, dummy=0 if generator.random() < .8 else generator.randrange(1, 256),
                      parent=generator.randrange(-1, 8)) for _ in range(generator.randrange(0, 8))]
        cases.append(build_case('random', actions, bones, stream_align=generator.randrange(16),
                                prefix=bytes(generator.randrange(256) for _ in range(generator.randrange(0, 40)))))
    edge = [0.0, -0.0, 2.0**-149, -2.0**-126, 1e-20, 0.1, -1.0, math.pi/2, math.pi, -math.pi,
            2*math.pi, 100.0, -1000.0, 65536.0, 180223.0]
    # Positions are copied bitwise: include signaling/quiet NaN, infinities,
    # subnormals and negative zero as raw patterns.
    raw_positions = [struct.pack('<3I', a, b, c) for a, b, c in (
        (0x7f800001, 0xffc00000, 0x7f800000), (0xff800000, 0x00000001, 0x80000000),
        (0x7fbfffff, 0x3f800000, 0xdeadbeef))]
    edge_positions = (raw_positions*len(edge))[:len(edge)]
    edge_bone = {'dummy': 0, 'name': b'edge', 'parent': -1,
                 'tracks': [(edge_positions, [(a, edge[(i*7) % len(edge)], edge[(i*11) % len(edge)])
                                              for i, a in enumerate(edge)])]}
    cases.append(build_case('edge-angles', [len(edge)], [edge_bone]))
    # Signed count fields that the loop treats as empty.
    cases.append(build_case('negative-bone-count', [1], [bone([1])], bone_field=-1))
    cases.append(build_case('bone-field-below-records', [1], [bone([1]), bone([1])], bone_field=1))
    # Overlapping layouts: the loop rereads counts/pointers and writes before
    # later reads, so effects must follow the original order.
    # Bone records written over not-yet-consumed stream bytes change later
    # dummy flags/names/parents. No actions keeps this free of FP domain issues.
    for delta in (0, 0x10, 0x23, 0x60, 0x8c):
        cases.append(build_case('overlap-bones-over-stream', [], [bone([], parent=index) for index in range(6)],
                                layout=f'bones-over-stream:{delta}'))
    for delta in (0, 0x23):
        # Bone writes land in later track data; the copied bytes stay in the SSE2 trig domain here.
        cases.append(build_case('overlap-tracks-over-stream', [2],
                                [{'dummy': 0, 'name': b'o', 'parent': index,
                                  'tracks': [([(1.0, 2.0, 3.0)]*2, [(0.1, 0.2, 0.3)]*2)]} for index in range(3)],
                                layout=f'bones-over-stream:{delta}'))
    cases.append(build_case('overlap-actions-in-bone-name', [1, 2],
                            [bone([1, 2], name=b'ABCD\x00\x00\x00\x00\x01\x00'), bone([1, 2])],
                            layout='actions-in-bone-name'))
    return cases


def characterization_cases():
    """Inputs outside the compared domain; recorded, never counted as matches."""
    generator = random.Random(7)
    track = ([(1.0, 2.0, 3.0)], [(0.25, -0.5, 1.0)])
    cases = [build_case('negative-key-count', [-1], [{'dummy': 0, 'name': b'n', 'parent': -1,
                                                      'tracks': [([], [])]}], heap_bytes=4096),
             build_case('negative-action-count', [1], [{'dummy': 0, 'name': b'n', 'parent': -1, 'tracks': [track]}],
                        action_field=-1, heap_bytes=4096),
             build_case('angle-beyond-sse2-domain', [1], [{'dummy': 0, 'name': b'x', 'parent': -1,
                                                          'tracks': [([(0.0, 0.0, 0.0)], [(1e6, 0.5, 0.5)])]}])]
    failing = build_case('heapalloc-null', [1], [{'dummy': 0, 'name': b'f', 'parent': -1, 'tracks': [track]}])
    failing['fail_allocation'] = 2
    cases.append(failing)
    del generator
    return cases


# --------------------------------------------------------------------------
# Independent Python model (third implementation and negative controls).


def python_model(case, rotation, variant='faithful'):
    image = bytearray(case['image'])
    heap = Heap(*case['heap'])
    requests = []

    def u8(a): return image[a-WINDOW]
    def s16(a): return struct.unpack_from('<h', image, a-WINDOW)[0]
    def u32(a): return struct.unpack_from('<I', image, a-WINDOW)[0]
    def put(a, payload): image[a-WINDOW:a-WINDOW+len(payload)] = payload

    def allocate(size):
        requests.append(size)
        if variant == 'elide-empty' and size == 0:
            return 0
        address, poison = heap.allocate(max(size, 1))
        put(address, poison)
        return address

    model, stream, offset = case['model'], case['stream'], case['start']
    index = 0
    while index < s16(model+0x22):
        bone = (u32(model+0x2c)+index*0x8c) & 0xffffffff
        put(bone+0x22, bytes([u8(stream+offset)]))
        offset += 1
        if u8(bone+0x22):
            index += 1
            continue
        put(bone, bytes(image[stream+offset-WINDOW:stream+offset+32-WINDOW]))
        offset += 32
        put(bone+0x20, bytes(image[stream+offset-WINDOW:stream+offset+2-WINDOW]))
        offset += 2
        put(bone+0x24, struct.pack('<I', allocate(saturating(s16(model+0x26), 12))))
        action = 0
        while action < s16(model+0x26):
            entry = u32(bone+0x24)+action*12
            copied = s16(u32(model+0x30)+action*16+8)*12
            keys = s16(u32(model+0x30)+action*16+8)
            sizes = (saturating(saturating(keys, 3), 4),)*2+(saturating(saturating(keys, 4), 4),)
            for field, size in zip((0, 4, 8), sizes):
                put(entry+field, struct.pack('<I', allocate(size)))
            for field in (0, 4):
                target = u32(entry+field)
                put(target, bytes(image[stream+offset-WINDOW:stream+offset+copied-WINDOW]))
                offset += copied
            for key in range(keys):
                source = u32(entry+4)+key*12
                angles = ctypes.create_string_buffer(bytes(image[source-WINDOW:source+12-WINDOW]), 12)
                output = ctypes.create_string_buffer(16)
                rotation(angles, output)
                put(u32(entry+8)+key*16, output.raw)
            action += 1
        index += 1
    return bytes(image), offset, requests


# --------------------------------------------------------------------------
# Emulator.


class Machine:
    def __init__(self, text, data, flag, feature, library, record_library):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ,
                             UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED,
                             UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_PROT_ALL, UC_MEM_WRITE)
        from unicorn import x86_const as x86
        self.x86, self.UC_MEM_WRITE = x86, UC_MEM_WRITE
        self.UC_PROT_ALL = UC_PROT_ALL
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, align(DATA_BYTES, 4096), UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        # Partially captured pages: only the named bytes may be read.
        self.partial = {FLAG_ADDRESS & ~0xfff: {FLAG_ADDRESS: flag},
                        FEATURE_ADDRESS & ~0xfff: {FEATURE_ADDRESS: feature},
                        SYNTHETIC_FEATURE & ~0xfff: {SYNTHETIC_FEATURE: b'\0\0\0\0'},
                        HEAP_HANDLE & ~0xfff: {HEAP_HANDLE: struct.pack('<I', HEAP_TOKEN)}}
        for page, contents in self.partial.items():
            uc.mem_map(page, 4096, UC_PROT_READ)
            for address, payload in contents.items():
                uc.mem_write(address, payload)
            uc.hook_add(UC_HOOK_MEM_READ, self.partial_read, begin=page, end=page+4095)
        # Authored HeapAlloc boundary: mov eax, [result]; ret 0xc.
        uc.mem_map(STUB_PAGE, 4096, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(IAT_TARGET, b'\xa1'+struct.pack('<I', STUB_RESULT)+b'\xc2\x0c\x00')
        uc.hook_add(UC_HOOK_CODE, self.heap_alloc, begin=IAT_TARGET, end=IAT_TARGET)
        uc.mem_map(STACK, STACK_BYTES, UC_PROT_READ | UC_PROT_WRITE)
        frame_low = FRAME_BASE-FRAME_BYTES
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.frame_access, begin=frame_low, end=FRAME_BASE+7)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.unmapped)
        uc.hook_add(UC_HOOK_CODE, self.memcpy_entry, begin=MEMCPY, end=MEMCPY)
        uc.hook_add(UC_HOOK_CODE, self.rotation_entry, begin=ROTATION, end=ROTATION)
        for address in MEMCPY_PATHS:
            uc.hook_add(UC_HOOK_CODE, self.memcpy_path, begin=address, end=address)
        self.window_hook = None
        self.mapped_window = 0
        self.preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a,
                          x86.UC_X86_REG_EDI: 0x456789ab}

    # Hooks -------------------------------------------------------------
    def stop(self, reason):
        if self.state['stopped'] is None:
            self.state['stopped'] = reason
        self.uc.emu_stop()

    def pc(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_EIP)

    def partial_read(self, uc, access, address, size, value, ignored):
        page = self.partial[address & ~0xfff]
        for start, payload in page.items():
            if start <= address and address+size <= start+len(payload):
                if start == HEAP_HANDLE and self.pc() != HEAP_HANDLE_READER:
                    break
                if start == SYNTHETIC_FEATURE:
                    self.state['synthetic_feature_reads'] += 1
                return
        self.stop(('uncaptured-read', hex(address), size, hex(self.pc())))

    def frame_access(self, uc, access, address, size, value, ignored):
        if address < FRAME_BASE-FRAME_BYTES or address+size > FRAME_BASE:
            if access == self.UC_MEM_WRITE or address < FRAME_BASE:
                self.stop(('frame-boundary', hex(address), size, hex(self.pc())))
            return
        slot = address-FRAME_BASE
        written = self.state['frame_written']
        if access == self.UC_MEM_WRITE:
            written.update(range(slot, slot+size))
            self.state['frame_slots'].add(slot)
            return
        if all(byte in written for byte in range(slot, slot+size)):
            return
        if slot in FRAME_INPUTS and size == 4:
            self.state['frame_inputs'].add(slot)
            return
        if self.pc() in ZEROING_ANDS:
            return
        self.stop(('undeclared-frame-read', slot, size, hex(self.pc())))

    def window_access(self, uc, access, address, size, value, ignored):
        offset = address-WINDOW
        defined = self.defined
        if access == self.UC_MEM_WRITE:
            defined[offset:offset+size] = b'\1'*size
            return
        if b'\0' not in defined[offset:offset+size]:
            return
        pc = self.pc()
        copy = self.state['copy']
        if copy and BODIES['memcpy'][0] <= pc < BODIES['memcpy'][1]:
            source, length = copy
            if (source & ~15) <= address and address+size <= align(source+length):
                self.state['memcpy_overreads'] += 1
                return
        self.stop(('undefined-read', hex(address), size, hex(pc)))

    def unmapped(self, uc, access, address, size, value, ignored):
        self.stop(('unmapped', hex(address), size, hex(self.pc())))
        return False

    def heap_alloc(self, uc, address, size, ignored):
        esp = uc.reg_read(self.x86.UC_X86_REG_ESP)
        returned, heap, flags, request = struct.unpack('<4I', uc.mem_read(esp, 16))
        if returned != IAT_RETURN or heap != HEAP_TOKEN or flags != 0:
            self.stop(('heapalloc-arguments', hex(returned), hex(heap), flags))
            return
        self.state['heap_sizes'].append(request)
        fail = self.state['fail_allocation']
        if fail is not None and len(self.state['heap_sizes']) == fail:
            uc.mem_write(STUB_RESULT, b'\0\0\0\0')
            return
        block, poison = self.heap.allocate(request)
        uc.mem_write(block, poison)
        uc.mem_write(STUB_RESULT, struct.pack('<I', block))

    def memcpy_entry(self, uc, address, size, ignored):
        esp = uc.reg_read(self.x86.UC_X86_REG_ESP)
        returned, destination, source, length = struct.unpack('<4I', uc.mem_read(esp, 16))
        self.state['copy'] = (source, length)
        self.state['current_paths'] = set()
        self.state['copies'].append((destination, source, length))

    def memcpy_path(self, uc, address, size, ignored):
        # Count each path once per memcpy call (REP instructions re-enter hooks).
        name = MEMCPY_PATHS[address]
        if name not in self.state['current_paths']:
            self.state['current_paths'].add(name)
            self.state['memcpy_paths'][name] = self.state['memcpy_paths'].get(name, 0)+1

    def rotation_entry(self, uc, address, size, ignored):
        self.state['rotations'] += 1

    # Execution -----------------------------------------------------------
    def run(self, case, feature_value):
        uc, x86 = self.uc, self.x86
        image = case['image']
        if self.mapped_window != len(image):
            if self.window_hook is not None:
                uc.hook_del(self.window_hook)
            if self.mapped_window:
                uc.mem_unmap(WINDOW, self.mapped_window)
            uc.mem_map(WINDOW, len(image), self.UC_PROT_ALL & ~4)
            self.window_hook = uc.hook_add(0x400 | 0x800, self.window_access, begin=WINDOW,
                                           end=WINDOW+len(image)-1)
            self.mapped_window = len(image)
        uc.mem_write(WINDOW, image)
        self.defined = bytearray(case['defined'])
        self.heap = Heap(*case['heap'])
        uc.mem_write(SYNTHETIC_FEATURE, struct.pack('<I', feature_value))
        self.state = {'stopped': None, 'frame_written': set(), 'frame_slots': set(), 'frame_inputs': set(),
                      'copy': None, 'copies': [], 'current_paths': set(), 'memcpy_overreads': 0, 'memcpy_paths': {},
                      'heap_sizes': [], 'rotations': 0, 'synthetic_feature_reads': 0,
                      'fail_allocation': case.get('fail_allocation')}
        uc.mem_write(STACK, b'\xa5'*STACK_BYTES)
        uc.mem_write(FRAME_BASE-0x18, struct.pack('<IIi', case['stream'], case['model'], case['start']))
        esp = FRAME_BASE-FRAME_BYTES
        for register, value in self.preserved.items():
            uc.reg_write(register, value)
        for register in (x86.UC_X86_REG_EAX, x86.UC_X86_REG_ECX, x86.UC_X86_REG_EDX):
            uc.reg_write(register, 0xdeadbeef)
        for index in range(8):
            lane = 0x7ff4dead5eed0000+index*0x0101010101
            uc.reg_write(getattr(x86, f'UC_X86_REG_XMM{index}'), lane | (lane << 64))
        uc.reg_write(x86.UC_X86_REG_EBP, FRAME_BASE)
        uc.reg_write(x86.UC_X86_REG_ESP, esp)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_FPSW, 0)
        uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(LOOP_START, LOOP_END, timeout=300000000, count=0)
        except Exception as failure:  # UcError
            error = str(failure)
        state = self.state
        returned = self.pc() == LOOP_END and state['stopped'] is None and error is None
        checks = {'reached_loop_end': returned,
                  'esp': uc.reg_read(x86.UC_X86_REG_ESP) == esp,
                  'ebp': uc.reg_read(x86.UC_X86_REG_EBP) == FRAME_BASE,
                  'callee_saved': all(uc.reg_read(r) == v for r, v in self.preserved.items()),
                  'direction_flag': (uc.reg_read(x86.UC_X86_REG_EFLAGS) >> 10) & 1 == 0,
                  'fpcw': uc.reg_read(x86.UC_X86_REG_FPCW) == FPCW,
                  'mxcsr_control': uc.reg_read(x86.UC_X86_REG_MXCSR) & ~0x3f == MXCSR,
                  'x87_top': (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7 == 0,
                  'frame_writes_declared': all(slot in FRAME_SCRATCH for slot in state['frame_slots'])}
        offset = struct.unpack('<i', uc.mem_read(FRAME_BASE-0x10, 4))[0]
        return {'checks': checks, 'error': error, 'stopped': state['stopped'], 'offset': offset,
                'window': bytes(uc.mem_read(WINDOW, len(image))), 'heap_sizes': state['heap_sizes'],
                'rotations': state['rotations'], 'copies': len(state['copies']),
                'memcpy_paths': state['memcpy_paths'], 'memcpy_overreads': state['memcpy_overreads'],
                'frame_inputs': sorted(state['frame_inputs']),
                'synthetic_feature_reads': state['synthetic_feature_reads']}


class Authored:
    class Image(ctypes.Structure):
        _fields_ = [('bytes', ctypes.c_void_p), ('base', ctypes.c_uint32), ('size', ctypes.c_uint32)]

    ALLOCATE = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32)

    def __init__(self, library):
        handle = ctypes.CDLL(str(library))
        self.read = handle.mu_bone_tracks_read
        self.read.argtypes = [ctypes.POINTER(self.Image), ctypes.c_uint32, ctypes.c_uint32,
                              ctypes.POINTER(ctypes.c_int32), self.ALLOCATE, ctypes.c_void_p]
        self.read.restype = ctypes.c_int
        self.rotation = handle.mu_rotation_quaternion
        self.rotation.argtypes, self.rotation.restype = [ctypes.c_void_p]*2, None
        environment = handle.mu_record_math_environment_supported
        environment.restype = ctypes.c_int
        if environment() != 1:
            raise ValueError('Host requires binary32/binary64 storage and RNE environment')

    def run(self, case):
        buffer = (ctypes.c_ubyte*len(case['image'])).from_buffer_copy(case['image'])
        image = self.Image(ctypes.addressof(buffer), WINDOW, len(case['image']))
        heap = Heap(*case['heap'])
        requests = []
        fail = case.get('fail_allocation')

        def allocate(context, request):
            requests.append(request)
            if request > MALLOC_LIMIT:  # client malloc refuses before HeapAlloc
                return 0
            if fail is not None and len([r for r in requests if r <= MALLOC_LIMIT]) == fail:
                return 0
            block, poison = heap.allocate(max(request, 1))
            ctypes.memmove(ctypes.addressof(buffer)+block-WINDOW, poison, len(poison))
            return block
        callback = self.ALLOCATE(allocate)
        offset = ctypes.c_int32(case['start'])
        status = self.read(ctypes.byref(image), case['model'], case['stream'], ctypes.byref(offset), callback, None)
        return {'status': status, 'window': bytes(buffer), 'offset': offset.value, 'requests': requests}


# --------------------------------------------------------------------------
# Installed models through the existing readers.


def hamilton_reference(angles):
    a0, a1, a2 = (float(value) for value in angles)
    factors = [(math.sin(a0/2), 0.0, 0.0, math.cos(a0/2)), (0.0, math.sin(a1/2), 0.0, math.cos(a1/2)),
               (0.0, 0.0, math.sin(a2/2), math.cos(a2/2))]

    def product(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
                aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
    return product(product(factors[2], factors[1]), factors[0])


def installed_case(path, relative, raw):
    sys.path.insert(0, str(ROOT/'model-recovery'))
    import bmd_encrypted
    version = raw[3]
    model = bmd_encrypted.parse_model(raw)
    body = raw[8:]
    plain = {12: bmd_encrypted.decrypt_map, 14: bmd_encrypted.decrypt_modulus,
             15: bmd_encrypted.decrypt_lea}[version](body)
    if hashlib.sha256(plain).hexdigest() != model['decoded_payload_sha256']:
        raise ValueError(f'{relative}: decoded payload differs from reader')
    actions = [action['keys'] for action in model['actions']]
    bones = model['bones']
    start = (bones[0]['source_offset'] if bones else model['parsed_bytes'])-4
    case = build_case(relative, actions, [{'dummy': int(bone['dummy'])} for bone in bones],
                      stream=plain, start=start, suffix=b'',
                      heap_bytes=heap_need(actions, [{'dummy': int(b['dummy'])} for b in bones]))
    case['parsed'] = model
    case['version'] = version
    return case


def check_against_reader(case, window):
    """Independent reader cross-check of the loop's output records."""
    model = case['parsed']
    view = memoryview(window)
    bone_array = struct.unpack_from('<I', window, case['model']+0x2c-WINDOW)[0]
    worst = 0.0
    for index, bone in enumerate(model['bones']):
        record = bone_array+index*0x8c-WINDOW
        if view[record+0x22] != int(bone['dummy']):
            return False, worst, f'bone {index} dummy'
        if bone['dummy']:
            continue
        if struct.unpack_from('<h', window, record+0x20)[0] != bone['parent']:
            return False, worst, f'bone {index} parent'
        tracks = struct.unpack_from('<I', window, record+0x24)[0]-WINDOW
        for action, track in enumerate(bone['tracks']):
            positions, rotations, quaternions = struct.unpack_from('<3I', window, tracks+action*12)
            keys = len(track['positions'])
            expected_p = b''.join(struct.pack('<3f', *p) for p in track['positions'])
            expected_r = b''.join(struct.pack('<3f', *r) for r in track['rotations'])
            if bytes(view[positions-WINDOW:positions-WINDOW+keys*12]) != expected_p:
                return False, worst, f'bone {index} action {action} positions'
            if bytes(view[rotations-WINDOW:rotations-WINDOW+keys*12]) != expected_r:
                return False, worst, f'bone {index} action {action} rotations'
            for key, angles in enumerate(track['rotations']):
                q = struct.unpack_from('<4f', window, quaternions-WINDOW+key*16)
                reference = hamilton_reference(angles)
                sign = 1.0 if sum(a*b for a, b in zip(q, reference)) >= 0 else -1.0
                worst = max(worst, max(abs(a-sign*b) for a, b in zip(q, reference)))
    return True, worst, None


# --------------------------------------------------------------------------
# Comparison driver.

_WORKER = {}


def compare(case, machine, authored, feature_value, negative=True):
    x86 = machine.run(case, feature_value)
    native = authored.run(case)
    python = python_model(case, authored.rotation)
    heap_expected = [max(r, 1) for r in native['requests'] if r <= MALLOC_LIMIT]
    checks = dict(x86['checks'], native_status=native['status'] == 0,
                  window=native['window'] == x86['window'], offset=native['offset'] == x86['offset'],
                  heap_sizes=heap_expected == x86['heap_sizes'],
                  python_model=python[0] == x86['window'] and python[1] == x86['offset'],
                  frame_inputs=set(x86['frame_inputs']) <= set(FRAME_INPUTS))
    result = {'label': case['label'], 'feature': feature_value, 'checks': checks,
              'match': all(checks.values()), 'stopped': x86['stopped'], 'error': x86['error'],
              'allocations': len(x86['heap_sizes']), 'rotations': x86['rotations'], 'copies': x86['copies'],
              'memcpy_paths': x86['memcpy_paths'], 'memcpy_overreads': x86['memcpy_overreads'],
              'frame_inputs': x86['frame_inputs'], 'final_offset': x86['offset']}
    if negative:
        wrong = python_model(case, authored.rotation, variant='elide-empty')
        result['negative_elide_empty_differs'] = wrong[0] != x86['window'] or wrong[1] != x86['offset']
    if 'parsed' in case:
        consistent, worst, problem = check_against_reader(case, x86['window'])
        expected_end = case['parsed']['parsed_bytes']-4
        result['reader'] = {'consistent': consistent, 'problem': problem,
                            'end_offset': x86['offset'] == expected_end, 'worst_quaternion_error': worst}
        result['match'] = result['match'] and consistent and x86['offset'] == expected_end
    if not result['match']:
        diffs = [i for i, (a, b) in enumerate(zip(native['window'], x86['window'])) if a != b]
        result['first_window_difference'] = hex(WINDOW+diffs[0]) if diffs else None
        result['window_difference_count'] = len(diffs)
    return result


def worker_init(paths):
    text = Path(paths['text']).read_bytes()
    data = Path(paths['data']).read_bytes()
    flag = Path(paths['flag']).read_bytes()
    feature = Path(paths['feature']).read_bytes()
    _WORKER['machine'] = Machine(text, data, flag, feature, paths['library'], None)
    _WORKER['authored'] = Authored(paths['library'])


def worker_model(job):
    index, path, relative = job
    raw = Path(path).read_bytes()
    try:
        case = installed_case(path, relative, raw)
    except Exception as error:  # reader rejection or decode error
        return {'label': relative, 'version': raw[3], 'reader_error': str(error)}
    result = compare(case, _WORKER['machine'], _WORKER['authored'], FEATURE_VALUES[index % len(FEATURE_VALUES)],
                     negative=False)
    result['version'] = case['version']
    result['sha256'] = hashlib.sha256(raw).hexdigest()
    result['keys'] = sum(case['parsed']['actions'][a]['keys'] for a in range(len(case['parsed']['actions']))
                         for b in case['parsed']['bones'] if not b['dummy'])
    return result


def installed_jobs(root, versions):
    seen, jobs = set(), []
    for path in sorted(Path(root).rglob('*')):
        if path.suffix.lower() != '.bmd' or not path.is_file():
            continue
        with path.open('rb') as handle:
            header = handle.read(4)
        if header[:3] != b'BMD' or header[3] not in versions:
            continue
        identity = (path.stat().st_dev, path.stat().st_ino)
        if identity in seen:
            continue
        seen.add(identity)
        jobs.append((len(jobs), str(path), str(path.relative_to(root))))
    return jobs


def summarize(results):
    summary = {'cases': len(results), 'matches': sum(r['match'] for r in results),
               'by_label': {}, 'memcpy_paths': {}, 'allocations': 0, 'rotations': 0, 'copies': 0,
               'memcpy_overreads': 0}
    for r in results:
        entry = summary['by_label'].setdefault(r['label'] if '/' not in r['label'] else 'installed', [0, 0])
        entry[0] += 1
        entry[1] += int(r['match'])
        for name, count in r['memcpy_paths'].items():
            summary['memcpy_paths'][name] = summary['memcpy_paths'].get(name, 0)+count
        for key in ('allocations', 'rotations', 'copies', 'memcpy_overreads'):
            summary[key] += r[key]
    summary['failures'] = [r for r in results if not r['match']][:12]
    return summary


def validate(text, data, flag, feature, library, game_root=None, versions=(12, 14), workers=1):
    payload = load_pinned(text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data_payload = load_pinned(data, DATA_BYTES, DATA_SHA256, 'second image section')
    flag_payload = load_pinned(flag, 4, FLAG_SHA256, 'dispatch flag')
    feature_payload = load_pinned(feature, 4, FEATURE_SHA256, 'memcpy feature word')
    for name, (start, end, digest) in BODIES.items():
        if hashlib.sha256(payload[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
            raise ValueError(f'Pinned {name} body mismatch')
    if struct.unpack_from('<I', data_payload, IAT_SLOT-DATA_BASE)[0] != IAT_TARGET:
        raise ValueError('HeapAlloc IAT slot value changed')
    import unicorn
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    decoded = list(decoder.disasm(payload[LOOP_START-TEXT_BASE:LOOP_END-TEXT_BASE], LOOP_START))
    if sum(item.size for item in decoded) != LOOP_END-LOOP_START:
        raise ValueError('Loop decode does not land on its end')
    calls = {item.address: item.operands[0].imm for item in decoded
             if item.mnemonic == 'call' and item.operands[0].type == X86_OP_IMM}
    if calls != CALLS or any(item.mnemonic == 'call' and item.address not in CALLS for item in decoded):
        raise ValueError('Loop call targets changed')
    library = Path(library).resolve(strict=True)
    machine = Machine(payload, data_payload, flag_payload, feature_payload, library, None)
    authored = Authored(library)

    synthetic = []
    for case in synthetic_cases():
        for feature_value in FEATURE_VALUES:
            synthetic.append(compare(case, machine, authored, feature_value))
    characterization = []
    for case in characterization_cases():
        x86 = machine.run(case, 1)
        native = authored.run(case)
        characterization.append({'label': case['label'], 'emulator_reached_end': x86['checks']['reached_loop_end'],
                                 'emulator_stopped': x86['stopped'], 'emulator_heap_sizes': x86['heap_sizes'],
                                 'authored_status': native['status'], 'authored_requests': native['requests'],
                                 'windows_equal': native['window'] == x86['window']})
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'flag_sha256': FLAG_SHA256,
              'feature_word_sha256': FEATURE_SHA256, 'feature_word_value': feature_payload.hex(),
              'bodies': {name: {'start': hex(s), 'end_exclusive': hex(e), 'sha256': d}
                         for name, (s, e, d) in BODIES.items()},
              'loop_calls': {hex(a): hex(t) for a, t in CALLS.items()},
              'unicorn': unicorn.__version__,
              'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'fpcw': hex(FPCW), 'mxcsr': hex(MXCSR), 'synthetic_feature_values': FEATURE_VALUES,
              'heap_token': hex(HEAP_TOKEN),
              'synthetic': summarize(synthetic),
              'negative_control_elide_empty_differences': sum(r.get('negative_elide_empty_differs', False)
                                                             for r in synthetic),
              'characterization': characterization}
    if game_root:
        jobs = installed_jobs(game_root, versions)
        paths = {'text': str(text), 'data': str(data), 'flag': str(flag), 'feature': str(feature),
                 'library': str(library)}
        if workers > 1:
            with multiprocessing.get_context('spawn').Pool(workers, worker_init, (paths,)) as pool:
                results = pool.map(worker_model, jobs, chunksize=4)
        else:
            worker_init(paths)
            results = [worker_model(job) for job in jobs]
        compared = [r for r in results if 'reader_error' not in r]
        per_version = {}
        for r in results:
            entry = per_version.setdefault(str(r['version']), {'files': 0, 'reader_rejected': 0, 'compared': 0,
                                                              'matches': 0, 'keys': 0})
            entry['files'] += 1
            if 'reader_error' in r:
                entry['reader_rejected'] += 1
                continue
            entry['compared'] += 1
            entry['matches'] += int(r['match'])
            entry['keys'] += r['keys']
        report['installed'] = dict(summarize(compared), per_version=per_version,
                                   reader_rejected=[{'label': r['label'], 'error': r['reader_error']}
                                                    for r in results if 'reader_error' in r],
                                   worst_quaternion_error=max((r['reader']['worst_quaternion_error']
                                                               for r in compared), default=0.0),
                                   corpus_sha256=hashlib.sha256('\n'.join(
                                       f"{r['label']}\t{r.get('sha256', '')}" for r in results).encode()).hexdigest())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True, help='math-capture cpu-features.bin')
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec' /
                        ('libbonetracks.dylib' if sys.platform == 'darwin' else 'libbonetracks.so'))
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--versions', default='12,14')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.data, args.flag, args.feature, args.library, args.game_root,
                          tuple(int(v) for v in args.versions.split(',')), args.workers)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    synthetic = result['synthetic']
    failed = synthetic['matches'] != synthetic['cases'] or not result['negative_control_elide_empty_differences']
    if 'installed' in result:
        failed = failed or result['installed']['matches'] != result['installed']['cases']
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
