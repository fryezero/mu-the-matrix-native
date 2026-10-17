#!/usr/bin/env python3
"""Compare the authored model transform and animation tick with the client.

The actual transform 0x012b5bde..0x012b678d (CPU skinning: vertices, normals,
per-normal light and the bounding box) runs in Unicorn over the pinned restored
text, the verified second image section and the captured trig dispatch flag,
with every client function it reaches: vector rotate 0x00d000ad, vector
transform 0x00d002b2, inverse rotate 0x00cfff3c, angle-to-matrix 0x00cff32a
with the actual sin/cos helpers, the world test 0x0095fb7c and the vector
accessors. The actual animation tick 0x012b4dd3..0x012b5064 runs with the
scene-state getter 0x009b0bc1. No client instruction is stubbed and neither
routine reaches an import.

Installed-model comparisons chain three actual client stages: the bone-track
loop (scripts/validate_bone_tracks.py) seeds the bone arrays, the actual pose
builder 0x012b5064 (scripts/validate_pose_builder.py) writes the bone matrices,
and the transform then reads those matrices and the model's real vertex and
normal records, which point at the decoded file bytes exactly as the model
reader's raw copies would hold them.

Modelled explicitly (not client code): the uncaptured globals (bone scale
0x01cf104c, light override 0x01cf1048, world 0x01cf15fc, bounds mode
0x0b437bfc, secondary light table 0x075a9ee8, scene state 0x01d1df70), the
caller's output arrays and box, the mesh record array (counts and pointers as
written by model reader 0x012b3812), and the model fields +0x24, +0x28, +0x50,
+0x74..+0x83, +0x98..+0xa3. Any read of uncaptured or undefined bytes, of an
unmapped address or of caller stack outside the arguments stops a case.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import multiprocessing
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pose = _load('validate_pose_builder')
tracks = pose.tracks
WINDOW = tracks.WINDOW
TEXT_BASE, DATA_BASE = tracks.TEXT_BASE, tracks.DATA_BASE
TRANSFORM_START, TRANSFORM_RETURN = 0x012b5bde, 0x012b678a
TICK_START, TICK_RETURN = 0x012b4dd3, 0x012b5061
BODIES = {  # start, exclusive end, SHA-256 of captured bytes
    'transform': (0x012b5bde, 0x012b678d, 'a546b109d885d267c1269b62cf2cdf694ee0d8faf3440979ffe7fa03f38bd2e9'),
    'tick': (0x012b4dd3, 0x012b5064, '047f50df9bf736daaef507c39d40f76b5673583bb2b831453ed61b39d3ae2d20'),
    'vector_irotate': (0x00cfff3c, 0x00d000ad, '6a3b8bb624c91270b9addd94ea2eb205cb69eb76d51c4c902737ee78fb187102'),
    'vector_rotate': (0x00d000ad, 0x00d0021e, '250728dccd9ba7c60811122d82c62c8c8fc75f6290e408746f4fde439603c457'),
    'vector_transform': (0x00d002b2, 0x00d0045e, '697638c67f6e7da903ef069c8051ad5ecdecc7c044945b4765311712066205ca'),
    'world_test': (0x0095fb7c, 0x0095fb99, '5efade7b9656bcf9c3e241d01671c49cd7bd236b4f33cbf1d000918426609a0c'),
    'scene_state': (0x009b0bc1, 0x009b0bcf, '60e1dbe0e4e756e1dcd216bd8343b4442a04af8747bb16c427db7e71fe4af490'),
}
IROTATE, ROTATE, VTRANSFORM, WORLD_TEST, SCENE_STATE = 0x00cfff3c, 0x00d000ad, 0x00d002b2, 0x0095fb7c, 0x009b0bc1
ELEMENT, VECTOR, AMATRIX = pose.ELEMENT, pose.VECTOR, pose.AMATRIX
TRANSFORM_CALLS = {0x12b5c51: WORLD_TEST, 0x12b5d2a: VECTOR, 0x12b5d30: AMATRIX, 0x12b5d49: IROTATE,
                   0x12b5d9b: IROTATE, 0x12b5e8a: VECTOR, 0x12b5f6d: VTRANSFORM, 0x12b5f8e: VTRANSFORM,
                   0x12b6024: ROTATE, 0x12b629c: VECTOR, 0x12b62bb: ROTATE}
TRANSFORM_ELEMENT_CALLS = 33  # remaining direct calls, all to 0x00cfc922
TICK_CALLS = {0x12b4f9d: SCENE_STATE}
BRANCHES = {
    0x12b5bf1: 'null-bones-return', 0x12b5c10: 'light-override', 0x12b5c62: 'light-world-30',
    0x12b5ce9: 'light-default', 0x12b5dac: 'bounds-init', 0x12b5ec1: 'vertex-prescale',
    0x12b5f77: 'vertex-plain', 0x12b5f9e: 'vertex-body-scale', 0x12b600d: 'vertex-bone-scale',
    0x12b60fa: 'bone-scale-body-scale', 0x12b6195: 'bounds-min-update', 0x12b61ba: 'bounds-max-update',
    0x12b61d8: 'vertex-origin', 0x12b62d2: 'normal-light', 0x12b6349: 'light-minimum-clamp',
    0x12b63d8: 'secondary-floor', 0x12b63e7: 'secondary-computed', 0x12b6486: 'box-from-bounds',
    0x12b6563: 'box-from-arguments',
    0x12b4e12: 'tick-early-return', 0x12b4e42: 'tick-no-keys-return', 0x12b4e73: 'tick-prior-update',
    0x12b4e9a: 'tick-nonpositive-shift', 0x12b4ee7: 'tick-stop-flag', 0x12b4f0f: 'tick-clamp',
    0x12b4f43: 'tick-cycle', 0x12b4f5f: 'tick-lock-limit', 0x12b4fa7: 'tick-scene-5',
    0x12b4fd5: 'tick-world-39-action-7', 0x12b5006: 'tick-wrap',
}
CONSTANTS = {0x1a7e91c: 1.3, 0x1a7e474: 2.0, 0x1a7df14: 0.5, 0x1a7e4ec: -1.0, 0x1a7dd48: 1.0, 0x1a7fb2c: -45.0,
             0x1aa5f18: -1.5, 0x1a80118: -0.5, 0x1a7ebc0: 1.8, 0x1ac8da0: 999999.0, 0x1ac8da4: -999999.0,
             0x1a7dd3c: 0.0, 0x1a7df18: 0.8, 0x1a7df08: 0.2, 0x1a7df00: 0.01}
BONE_SCALE, LIGHT_OVERRIDE, WORLD, BOUNDS_MODE = 0x01cf104c, 0x01cf1048, 0x01cf15fc, 0x0b437bfc
SECONDARY_LIGHT, SCENE = 0x075a9ee8, 0x01d1df70
VERTEX_STRIDE, LIGHT_STRIDE = 0x2bf20, 0xea60
OUT_VERTICES, OUT_NORMALS, OUT_LIGHTS = 0x50000000, 0x58000000, 0x5c000000
STACK, STACK_BYTES = pose.STACK, pose.STACK_BYTES
ENTRY_ESP, SENTINEL = pose.ENTRY_ESP, pose.SENTINEL
FPCW, MXCSR = pose.FPCW, pose.MXCSR
PAGE = 0x1000


def f32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def bits(value):
    return struct.unpack('<I', struct.pack('<f', f32(value)))[0]


def from_bits(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


def align(value, boundary=16):
    return (value+boundary-1) & -boundary


def truncate32(value):
    if not (-2147483648.0 <= value < 2147483648.0):
        return -0x80000000
    return int(value)


def poison(size, salt):
    return bytes(((index*41+salt) & 0x7f) | 0x80 for index in range(size))


class Region:
    """Client bytes at a fixed address with a defined-byte mask."""

    def __init__(self, name, base, data, defined=None, writable=True):
        self.name, self.base, self.data = name, base, bytearray(data)
        self.defined = bytearray(b'\1'*len(data)) if defined is None else bytearray(defined)
        self.writable = writable

    @property
    def end(self):
        return self.base+len(self.data)

    def define(self, address, payload):
        offset = address-self.base
        if offset < 0 or offset+len(payload) > len(self.data):
            raise ValueError(f'{self.name}: {address:#x}+{len(payload)} outside region')
        self.data[offset:offset+len(payload)] = payload
        self.defined[offset:offset+len(payload)] = b'\1'*len(payload)

    def copy(self):
        return Region(self.name, self.base, self.data, self.defined, self.writable)


def global_regions(values):
    """Declared read-only globals; values maps address -> bytes."""
    return [Region(f'global:{address:#x}', address, payload, writable=False) for address, payload in values.items()]


# --------------------------------------------------------------------------
# Emulator.


class SkinMachine:
    def __init__(self, text, data, flag):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                             UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED, UC_PROT_READ, UC_PROT_WRITE,
                             UC_PROT_EXEC, UC_MEM_WRITE)
        from unicorn import x86_const as x86
        self.x86, self.UC_MEM_WRITE = x86, UC_MEM_WRITE
        self.RW = UC_PROT_READ | UC_PROT_WRITE
        self.ACCESS = UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, tracks.TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, align(tracks.DATA_BYTES, PAGE), UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        page = tracks.FLAG_ADDRESS & ~0xfff
        uc.mem_map(page, PAGE, UC_PROT_READ)
        uc.mem_write(tracks.FLAG_ADDRESS, flag)
        uc.hook_add(UC_HOOK_MEM_READ, self.flag_read, begin=page, end=page+PAGE-1)
        uc.mem_map(STACK, STACK_BYTES, self.RW)
        uc.hook_add(self.ACCESS, self.caller_stack, begin=ENTRY_ESP, end=STACK+STACK_BYTES-1)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.unmapped)
        for address in BRANCHES:
            uc.hook_add(UC_HOOK_CODE, self.branch, begin=address, end=address)
        for address in pose.TRIG_RETURNS:
            uc.hook_add(UC_HOOK_CODE, self.trig_result, begin=address, end=address)
        self.UC_HOOK_CODE = UC_HOOK_CODE
        self.dynamic = []  # (base, size, hook)
        self.preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a,
                          x86.UC_X86_REG_EDI: 0x456789ab, x86.UC_X86_REG_EBP: 0x56789abc}

    def stop(self, reason):
        if self.state['stopped'] is None:
            self.state['stopped'] = reason
        self.uc.emu_stop()

    def pc(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_EIP)

    def flag_read(self, uc, access, address, size, value, ignored):
        if not (tracks.FLAG_ADDRESS <= address and address+size <= tracks.FLAG_ADDRESS+4):
            self.stop(('uncaptured-read', hex(address), size, hex(self.pc())))

    def caller_stack(self, uc, access, address, size, value, ignored):
        pc = self.pc()
        if address == ENTRY_ESP and size == 4 and access != self.UC_MEM_WRITE and pc == self.return_instruction:
            return
        if address >= ENTRY_ESP+4 and address+size <= ENTRY_ESP+4+self.argument_bytes and \
                access != self.UC_MEM_WRITE:
            return
        self.stop(('caller-stack', hex(address), size, access == self.UC_MEM_WRITE, hex(pc)))

    def unmapped(self, uc, access, address, size, value, ignored):
        self.stop(('unmapped', hex(address), size, hex(self.pc())))
        return False

    def branch(self, uc, address, size, ignored):
        name = BRANCHES[address]
        self.state['branches'][name] = self.state['branches'].get(name, 0)+1

    def trig_result(self, uc, address, size, ignored):
        name, host = pose.TRIG_RETURNS[address]
        x86 = self.x86
        argument = struct.unpack('<d', uc.mem_read(uc.reg_read(x86.UC_X86_REG_ESP), 8))[0]
        top = (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7
        mantissa, exponent = uc.reg_read(getattr(x86, f'UC_X86_REG_FP{top}'))
        result = math.ldexp(mantissa, (exponent & 0x7fff)-16383-63) if mantissa else 0.0
        result = -result if exponent & 0x8000 else result
        expected = host(argument)
        entry = self.state['trig'].setdefault(name, [0, 0, 0])
        entry[0] += 1
        entry[1] += int(struct.pack('<d', result) != struct.pack('<d', expected))
        entry[2] += int(struct.pack('<f', f32(result)) != struct.pack('<f', f32(expected)))

    def access(self, uc, access, address, size, value, regions):
        for region in regions:
            if region.base <= address and address+size <= region.end:
                offset = address-region.base
                if access == self.UC_MEM_WRITE:
                    if not region.writable:
                        break
                    region.defined[offset:offset+size] = b'\1'*size
                    return
                if b'\0' in region.defined[offset:offset+size]:
                    self.stop(('undefined-read', region.name, hex(address), size, hex(self.pc())))
                return
        self.stop(('undeclared-access', hex(address), size, access == self.UC_MEM_WRITE, hex(self.pc())))

    def map_regions(self, regions):
        uc = self.uc
        for base, size, hook in self.dynamic:
            uc.hook_del(hook)
            uc.mem_unmap(base, size)
        self.dynamic = []
        pages = sorted({page for r in regions if len(r.data)
                        for page in range(r.base & ~0xfff, align(r.end, PAGE), PAGE)})
        spans = []
        for page in pages:
            if spans and spans[-1][1] == page:
                spans[-1][1] = page+PAGE
            else:
                spans.append([page, page+PAGE])
        for low, high in spans:
            inside = [r for r in regions if len(r.data) and r.base < high and r.end > low]
            uc.mem_map(low, high-low, self.RW)
            uc.mem_write(low, b'\xcc'*(high-low))
            hook = uc.hook_add(self.ACCESS, self.access, inside, begin=low, end=high-1)
            self.dynamic.append((low, high-low, hook))
        for r in regions:
            if len(r.data):
                uc.mem_write(r.base, bytes(r.data))

    def execute(self, start, arguments, regions, *, ecx, return_instruction, cleanup):
        uc, x86 = self.uc, self.x86
        regions = [r.copy() for r in regions]
        self.map_regions(regions)
        self.return_instruction = return_instruction
        self.argument_bytes = 4*len(arguments)
        self.state = {'stopped': None, 'branches': {}, 'trig': {}}
        uc.mem_write(STACK, b'\xa5'*STACK_BYTES)
        uc.mem_write(ENTRY_ESP, struct.pack('<I', SENTINEL)+b''.join(struct.pack('<I', a) for a in arguments))
        for register, value in self.preserved.items():
            uc.reg_write(register, value)
        uc.reg_write(x86.UC_X86_REG_EAX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_EDX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        for index in range(8):
            lane = 0x7ff4dead5eed0000+index*0x0101010101
            uc.reg_write(getattr(x86, f'UC_X86_REG_XMM{index}'), lane | (lane << 64))
        uc.reg_write(x86.UC_X86_REG_ESP, ENTRY_ESP)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_FPSW, 0)
        uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, SENTINEL, timeout=900000000, count=0)
        except Exception as failure:  # UcError
            error = str(failure)
        state = self.state
        checks = {'returned': self.pc() == SENTINEL and state['stopped'] is None and error is None,
                  'esp': uc.reg_read(x86.UC_X86_REG_ESP) == ENTRY_ESP+4+cleanup,
                  'callee_saved': all(uc.reg_read(r) == v for r, v in self.preserved.items()),
                  'direction_flag': (uc.reg_read(x86.UC_X86_REG_EFLAGS) >> 10) & 1 == 0,
                  'fpcw': uc.reg_read(x86.UC_X86_REG_FPCW) == FPCW,
                  'mxcsr_control': uc.reg_read(x86.UC_X86_REG_MXCSR) & ~0x3f == MXCSR,
                  'x87_top': (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7 == 0}
        result = {'checks': checks, 'error': error, 'stopped': state['stopped'], 'branches': state['branches'],
                  'trig': state['trig'], 'eax': uc.reg_read(x86.UC_X86_REG_EAX),
                  'regions': {r.name: bytes(uc.mem_read(r.base, len(r.data))) for r in regions if len(r.data)}}
        return result


# --------------------------------------------------------------------------
# Authored C.


class Authored:
    class Image(ctypes.Structure):
        _fields_ = [('bytes', ctypes.c_void_p), ('base', ctypes.c_uint32), ('size', ctypes.c_uint32)]

    class Memory(ctypes.Structure):
        pass

    class TransformArguments(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint32) for name in (
            'bones', 'vertices', 'normals', 'lights', 'bounds_min', 'bounds_max', 'box', 'translate',
            'vertex_scale', 'light_ambient', 'light_scale', 'light_minimum')]

    class TransformGlobals(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint32) for name in (
            'bone_scale', 'light_override', 'world', 'bounds_mode', 'secondary_light')]

    class TickArguments(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint32) for name in (
            'frame', 'prior_frame', 'prior_action', 'speed', 'origin', 'angles')]

    class TickGlobals(ctypes.Structure):
        _fields_ = [('scene_state', ctypes.c_uint32), ('world', ctypes.c_uint32)]

    Memory._fields_ = [('regions', ctypes.POINTER(Image)), ('count', ctypes.c_uint32)]

    def __init__(self, library):
        handle = ctypes.CDLL(str(library))
        self.transform = handle.mu_model_transform
        self.transform.argtypes = [ctypes.POINTER(self.Memory), ctypes.c_uint32,
                                   ctypes.POINTER(self.TransformArguments), ctypes.POINTER(self.TransformGlobals)]
        self.transform.restype = ctypes.c_int
        self.tick = handle.mu_animation_tick
        self.tick.argtypes = [ctypes.POINTER(self.Memory), ctypes.c_uint32, ctypes.POINTER(self.TickArguments),
                              ctypes.POINTER(self.TickGlobals), ctypes.POINTER(ctypes.c_uint8)]
        self.tick.restype = ctypes.c_int
        self.vectors = {name: getattr(handle, f'mu_vector_{name}') for name in ('rotate', 'transform', 'irotate')}
        for function in self.vectors.values():
            function.argtypes, function.restype = [ctypes.c_void_p]*3, None
        self.pose = pose.Authored(library)

    def memory(self, regions):
        buffers = [(r, (ctypes.c_ubyte*len(r.data)).from_buffer_copy(bytes(r.data))) for r in regions if len(r.data)]
        images = (self.Image*len(buffers))(*[self.Image(ctypes.addressof(b), r.base, len(b)) for r, b in buffers])
        return buffers, self.Memory(images, len(buffers))

    def run_transform(self, setup):
        buffers, memory = self.memory(setup['regions'])
        arguments = self.TransformArguments(*setup['arguments'])
        status = self.transform(ctypes.byref(memory), setup['model'], ctypes.byref(arguments),
                                ctypes.byref(self.TransformGlobals(BONE_SCALE, LIGHT_OVERRIDE, WORLD, BOUNDS_MODE,
                                                                   SECONDARY_LIGHT)))
        return {'status': status, 'regions': {r.name: bytes(b) for r, b in buffers}}

    def run_tick(self, setup):
        buffers, memory = self.memory(setup['regions'])
        loop = ctypes.c_uint8(0xee)
        status = self.tick(ctypes.byref(memory), setup['model'], ctypes.byref(self.TickArguments(*setup['arguments'])),
                           ctypes.byref(self.TickGlobals(SCENE, WORLD)), ctypes.byref(loop))
        return {'status': status, 'regions': {r.name: bytes(b) for r, b in buffers}, 'loop': loop.value}


# --------------------------------------------------------------------------
# Independent Python model (third implementation and negative controls).


class PyMemory(pose.PyMemory):
    def __init__(self, regions):
        super().__init__([(r.base, bytearray(r.data)) for r in regions if len(r.data)])

    def named(self, regions):
        lookup = {base: buffer for base, buffer in self.regions}
        return {r.name: bytes(lookup[r.base]) for r in regions if len(r.data)}


def py_dot(a, b):
    value = f32(a[0]*b[0])
    value = f32(value + f32(a[1]*b[1]))
    return f32(value + f32(a[2]*b[2]))


def py_rows(m, v, transpose=False):
    rows = []
    for r in range(3):
        column = [m[r], m[4+r], m[8+r]] if transpose else m[r*4:r*4+3]
        rows.append(py_dot(v, column))
    return rows


def python_transform(setup, variant='faithful'):
    regions = setup['regions']
    m = PyMemory(regions)
    model = setup['model']
    (bones, vertices, normals, lights, bounds_min, bounds_max, box, translate, vertex_scale, ambient, light_scale,
     light_minimum) = setup['arguments']
    translate &= 0xff
    vertex_scale, ambient, light_scale, light_minimum = (from_bits(v) for v in (vertex_scale, ambient, light_scale,
                                                                                light_minimum))
    if bones == 0:
        return m.named(regions)

    def matrix(node):
        return [m.f((bones+node*0x30+4*k) & 0xffffffff) for k in range(12)]
    lighting = m.u8(model+0x50)
    if lighting:
        if m.u8(LIGHT_OVERRIDE):
            vector = [1.3, 0.0, 2.0]
        elif struct.unpack('<i', struct.pack('<I', m.u32(WORLD)))[0] == 30:
            vector = [0.5, -1.0, 1.0]
            m.putf(model+0x98, 0.0)
            m.putf(model+0x9c, 0.0)
            m.putf(model+0xa0, -45.0)
        else:
            vector = [0.0, -1.5, 0.0]
        rotation = pose.py_angle_matrix([m.f(model+0x98+4*k) for k in range(3)])
        light1 = py_rows(rotation, [f32(v) for v in vector], transpose=True)
        light2 = py_rows(rotation, [f32(1.3), f32(-0.5), f32(1.8)], transpose=True)
    mode = m.u32(BOUNDS_MODE)
    low, high = [f32(999999.0)]*3, [f32(-999999.0)]*3
    i = 0
    while i < m.s16(model+0x24):
        mesh = (m.u32(model+0x28)+i*0x20) & 0xffffffff
        j = 0
        while j < m.s16(mesh+4):
            record = (m.u32(mesh+0xc)+j*16) & 0xffffffff
            out = (vertices+i*VERTEX_STRIDE+j*12) & 0xffffffff
            node = m.s16(record)
            position = [m.f(record+4+4*k) for k in range(3)]
            bone = matrix(node)
            scale = m.f(BONE_SCALE)
            if scale == 1.0:
                if vertex_scale != 0.0:
                    position = [f32(vertex_scale*p) for p in position]
                result = py_rows(bone, position, transpose=variant == 'transpose')
                result = [f32(result[k] + bone[k*4+3]) for k in range(3)]
            else:
                result = py_rows(bone, position, transpose=variant == 'transpose')
                result = [f32(f32(result[k]*scale) + bone[k*4+3]) for k in range(3)]
            if translate:
                result = [f32(m.f(model+0x74)*v) for v in result]
            if mode == 2:
                for k in range(3):
                    if low[k] > result[k]:
                        low[k] = result[k]
                    if result[k] > high[k]:
                        high[k] = result[k]
            if translate:
                result = [f32(result[k] + m.f(model+0x78+4*k)) for k in range(3)]
            for k in range(3):
                m.putf(out+4*k, result[k])
            j += 1
        j = 0
        while j < m.s16(mesh+6):
            record = (m.u32(mesh+0x10)+j*20) & 0xffffffff
            out = (normals+i*VERTEX_STRIDE+j*12) & 0xffffffff
            bone = matrix(m.s16(record))
            normal = py_rows(bone, [m.f(record+4+4*k) for k in range(3)])
            if variant == 'normal-translate':
                normal = [f32(normal[k] + bone[k*4+3]) for k in range(3)]
            for k in range(3):
                m.putf(out+4*k, normal[k])
            if m.u8(model+0x50):
                value = f32(f32(py_dot(normal, light1)*light_scale) + ambient)
                if light_minimum > value:
                    value = light_minimum
                m.putf(lights+i*LIGHT_STRIDE+j*4, value)
                value = f32(f32(py_dot(normal, light2)*f32(0.8)) + ambient)
                m.putf(SECONDARY_LIGHT+i*LIGHT_STRIDE+j*4, max(value, f32(0.2)) if value == value else value)
            j += 1
        i += 1
    if mode == 2:
        origin, extent = low, [f32(high[k]-low[k]) for k in range(3)]
    else:
        origin = [m.f(bounds_min+4*k) for k in range(3)]
        for k in range(3):
            m.put32(box+4*k, m.u32(bounds_min+4*k))
        extent = None
    for k in range(3):
        if mode == 2:
            m.putf(box+4*k, origin[k])
    for k in range(3):
        if extent is None:
            value = f32(m.f(bounds_max+4*k) - m.f(bounds_min+4*k))
        else:
            value = extent[k]
        m.putf(box+0xc*(k+1)+4*k, value)
    for k in range(3):
        m.putf(box+4*k, f32(m.f(box+4*k) + m.f(model+0x78+4*k)))
    for axis, k in ((1, 1), (1, 2), (2, 0), (2, 2), (3, 0), (3, 1)):
        m.putf(box+0xc*axis+4*k, 0.0)
    return m.named(regions)


def python_tick(setup, variant='faithful'):
    regions = setup['regions']
    m = PyMemory(regions)
    model = setup['model']
    frame_at, prior_at, action_at, speed = setup['arguments'][:4]
    speed = from_bits(speed)
    if not (frame_at and prior_at and action_at):
        return m.named(regions), 1
    actions = m.s16(model+0x26)
    action = m.u16(model+0xa8)
    if actions > 0 and action >= actions or actions == 0:
        return m.named(regions), 1
    entry = (m.u32(model+0x30)+action*16) & 0xffffffff
    keys = m.s16(entry+8)
    if keys <= 1:
        return m.named(regions), 1
    loop = 1
    old = truncate32(m.f(frame_at))
    m.putf(frame_at, f32(m.f(frame_at)+speed))
    frame = m.f(frame_at)
    if old != truncate32(frame) or variant == 'prior-every-tick':
        m.put16(action_at, action)
        m.putf(prior_at, f32(float(old)))
    if frame <= 0.0:
        m.putf(frame_at, f32(f32(keys-1.0)+frame))
    frame = m.f(frame_at)
    if m.u8(entry):
        if frame >= float(keys):
            m.putf(frame_at, f32(keys-f32(0.01)))
            loop = 0
    else:
        limit = keys-1 if m.u8(entry+0xa) and variant != 'ignore-lock' else keys
        state = struct.unpack('<i', struct.pack('<I', m.u32(SCENE)))[0]
        world = struct.unpack('<i', struct.pack('<I', m.u32(WORLD)))[0]
        if state == 5:
            test = f32(frame+2.0)
        elif world == 0x27 and action == 7:
            test = f32(frame+1.0)
        else:
            test = frame
        if test >= float(limit):
            whole = truncate32(frame)
            remainder = int(math.fmod(whole, limit))
            m.putf(frame_at, f32(float(remainder) + f32(frame-float(whole))))
            loop = 0
    m.put32(model+0xac, m.u32(frame_at))
    m.put16(model+0xb4, truncate32(m.f(model+0xac)) & 0xffff)
    return m.named(regions), loop


# --------------------------------------------------------------------------
# Case construction.


def transform_globals(params):
    return global_regions({
        BONE_SCALE: struct.pack('<f', params.get('bone_scale', 1.0)),
        LIGHT_OVERRIDE: bytes([params.get('override', 0) & 0xff]),
        WORLD: struct.pack('<i', params.get('world', 0)),
        BOUNDS_MODE: struct.pack('<i', params.get('bounds_mode', 0))})


def transform_setup(label, window, model, bones, meshes, params):
    """window: Region holding the model object and bone matrices.

    meshes: [{'vertices': address, 'normals': address, 'nv': int, 'nn': int}]
    with the vertex/normal arrays already defined in the window.
    """
    window = window.copy()
    generator = random.Random(params.get('seed', 0))
    extra = align(len(meshes)*0x20, 16)+0x100
    start = align(window.end, PAGE)
    window.data.extend(poison(start+extra-window.end, 0x3b))
    window.defined.extend(bytes(start+extra-window.end))
    records = start
    for index, mesh in enumerate(meshes):
        record = records+index*0x20
        window.define(record, struct.pack('<BBhhhhh', 0, 0, mesh.get('texture', 0), mesh['nv'], mesh['nn'],
                                          mesh.get('nt', 0), mesh.get('nf', 0)))
        window.define(record+0xc, struct.pack('<II', mesh['vertices'], mesh['normals']))
    count = params.get('mesh_field', len(meshes))
    window.define(model+0x24, struct.pack('<h', count))
    window.define(model+0x28, struct.pack('<I', records))
    window.define(model+0x50, bytes([params.get('lighting', 0)]))
    window.define(model+0x74, struct.pack('<4f', params.get('body_scale', 1.0), *params.get('origin', (0.0,)*3)))
    window.define(model+0x98, struct.pack('<3f', *params.get('light_angles', (0.0, 0.0, 0.0))))
    bounds_min = records+align(len(meshes)*0x20, 16)
    bounds_max = bounds_min+0x10
    box = bounds_min+0x20
    window.define(bounds_min, struct.pack('<3f', *params.get('bounds_min', (-1.0, -2.0, -3.0))))
    window.define(bounds_max, struct.pack('<3f', *params.get('bounds_max', (4.0, 5.0, 6.0))))
    regions = [window]
    for index, mesh in enumerate(meshes[:max(count, 0)]):
        if mesh['nv'] > 0:
            regions.append(Region(f'vertices:{index}', OUT_VERTICES+index*VERTEX_STRIDE,
                                  poison(mesh['nv']*12, index), bytes(mesh['nv']*12)))
        if mesh['nn'] > 0:
            regions.append(Region(f'normals:{index}', OUT_NORMALS+index*VERTEX_STRIDE,
                                  poison(mesh['nn']*12, index+1), bytes(mesh['nn']*12)))
            regions.append(Region(f'lights:{index}', OUT_LIGHTS+index*LIGHT_STRIDE,
                                  poison(mesh['nn']*4, index+2), bytes(mesh['nn']*4)))
            regions.append(Region(f'secondary:{index}', SECONDARY_LIGHT+index*LIGHT_STRIDE,
                                  poison(mesh['nn']*4, index+3), bytes(mesh['nn']*4)))
    regions += transform_globals(params)
    arguments = [bones if not params.get('null_bones') else 0, OUT_VERTICES, OUT_NORMALS, OUT_LIGHTS, bounds_min,
                 bounds_max, box, params.get('translate', 0) & 0xffffffff,
                 bits(params.get('vertex_scale', 0.0)), bits(params.get('ambient', 0.4)),
                 bits(params.get('light_scale', 0.4)), bits(params.get('light_minimum', 0.4))]
    del generator
    vertices = sum(m['nv'] for m in meshes[:max(count, 0)] if m['nv'] > 0)
    normals = sum(m['nn'] for m in meshes[:max(count, 0)] if m['nn'] > 0)
    return {'label': label, 'regions': regions, 'model': model, 'arguments': arguments,
            'vertices': vertices, 'normals': normals}


def random_transform_params(generator, nodes_ok=True):
    lighting = int(generator.random() < 0.6)
    return {'seed': generator.randrange(1 << 30), 'lighting': lighting,
            'override': generator.choice([0, 0, 1]) | (generator.randrange(256) if generator.random() < .1 else 0),
            'world': generator.choice([30, 30, 0, 39, 1]),
            'light_angles': tuple(f32(generator.uniform(-180, 180)) for _ in range(3)),
            'bounds_mode': generator.choice([2, 2, 0, 1]),
            'bone_scale': generator.choice([1.0, 1.0, 1.0, f32(generator.uniform(0.5, 1.5))]),
            'vertex_scale': generator.choice([0.0, 0.0, -0.0, f32(generator.uniform(0.25, 2.0))]),
            'translate': generator.randrange(2) | (generator.randrange(256) << 8),
            'body_scale': f32(generator.uniform(0.5, 2.0)),
            'origin': tuple(f32(generator.uniform(-5000, 5000)) for _ in range(3)),
            'ambient': f32(generator.uniform(0.0, 0.8)), 'light_scale': f32(generator.uniform(0.2, 1.2)),
            'light_minimum': f32(generator.uniform(0.0, 0.6)),
            'bounds_min': tuple(f32(generator.uniform(-100, 0)) for _ in range(3)),
            'bounds_max': tuple(f32(generator.uniform(0, 100)) for _ in range(3))}


def synthetic_window(generator, bones, meshes_spec):
    """Model object, declared bone matrices and raw vertex/normal records."""
    size = 0x200+bones*0x30+sum(nv*16+nn*20+64 for nv, nn in meshes_spec)
    size = align(size+0x100, PAGE)
    window = Region('window', WINDOW, poison(size, 0x5d), bytes(size))
    model = WINDOW
    matrices = WINDOW+0x200
    for index in range(bones):
        window.define(matrices+index*0x30, struct.pack('<12f', *[f32(generator.uniform(-2, 2)) if k % 4 != 3 else
                                                                 f32(generator.uniform(-300, 300))
                                                                 for k in range(12)]))
    cursor = align(matrices+bones*0x30, 16)
    meshes = []
    for nv, nn in meshes_spec:
        vertices = cursor
        for j in range(max(nv, 0)):
            window.define(vertices+j*16, struct.pack('<hh3f', generator.randrange(bones), generator.randrange(-4, 4),
                                                     *[f32(generator.uniform(-150, 150)) for _ in range(3)]))
        cursor = align(vertices+max(nv, 0)*16+1, 16)
        normals = cursor
        for j in range(max(nn, 0)):
            v = [generator.gauss(0, 1) for _ in range(3)]
            n = math.sqrt(sum(x*x for x in v)) or 1.0
            window.define(normals+j*20, struct.pack('<hh3fhh', generator.randrange(bones), 0,
                                                    *[f32(x/n) for x in v], generator.randrange(max(nv, 1)), 0))
        cursor = align(normals+max(nn, 0)*20+1, 16)
        meshes.append({'vertices': vertices, 'normals': normals, 'nv': nv, 'nn': nn})
    return window, model, matrices, meshes


def synthetic_transform_cases():
    generator = random.Random(0x12b5bde)
    cases = []

    def add(label, bones, spec, params):
        window, model, matrices, meshes = synthetic_window(generator, bones, spec)
        cases.append(transform_setup(label, window, model, matrices, meshes, params))
    base = {'lighting': 0, 'bounds_mode': 0}
    add('null-bones', 2, [(3, 3)], dict(base, null_bones=True))
    add('no-meshes', 2, [], dict(base))
    add('empty-meshes', 2, [(0, 0), (0, 4), (4, 0)], dict(base, bounds_mode=2))
    add('negative-counts', 2, [(-1, -1), (3, 2)], dict(base))
    add('negative-mesh-field', 2, [(3, 2)], dict(base, mesh_field=-3))
    add('mesh-field-below-records', 2, [(3, 2), (5, 5)], dict(base, mesh_field=1))
    for bone_scale in (1.0, 0.5, 1.25, f32(1.0000001), -1.0, 0.0):
        for vertex_scale in (0.0, -0.0, 1.5, -2.0):
            for translate in (0, 1, 0x100):
                add('scales', 4, [(6, 5)], dict(base, bone_scale=bone_scale, vertex_scale=vertex_scale,
                                               translate=translate, body_scale=1.75, origin=(10.0, -20.0, 30.0)))
    for mode in (0, 1, 2, -2, 0x102):
        add('bounds-mode', 3, [(8, 2), (5, 1)], dict(base, bounds_mode=mode, translate=1, origin=(1.0, 2.0, 3.0)))
    for override in (0, 1, 0x80):
        for world in (30, 29, 31, 0, -30):
            add('lighting', 3, [(4, 9)], dict(base, lighting=1, override=override, world=world,
                                            light_angles=(30.0, -60.0, 135.0)))
    for minimum, ambient, scale in ((0.4, 0.4, 0.4), (0.0, 0.0, 1.0), (2.0, 0.1, 0.5), (-1.0, -0.5, 3.0),
                                    (0.5, 0.25, -1.0)):
        add('light-arguments', 2, [(2, 12)], dict(base, lighting=1, world=0, light_minimum=minimum, ambient=ambient,
                                                light_scale=scale, light_angles=(0.0, 0.0, 0.0)))
    add('lighting-flag-junk', 2, [(2, 4)], dict(base, lighting=0x80, world=30))
    add('many-meshes', 6, [(generator.randrange(1, 30), generator.randrange(1, 30)) for _ in range(12)],
        dict(base, lighting=1, bounds_mode=2, translate=1))
    add('large-mesh', 8, [(2500, 2200)], dict(base, lighting=1, bounds_mode=2, translate=1))
    for _ in range(120):
        spec = [(generator.randrange(0, 40), generator.randrange(0, 40)) for _ in range(generator.randrange(1, 5))]
        add('random', generator.randrange(1, 12), spec, random_transform_params(generator))
    return cases


def chained_groups():
    """Synthetic models whose bone matrices come from the actual pose builder."""
    generator = random.Random(0x6fce398)
    groups = []
    for index in range(24):
        actions = [generator.randrange(1, 6) for _ in range(generator.randrange(1, 4))]
        count = generator.randrange(1, 14)
        bones = [pose.euler_bone(generator, actions, parent=generator.randrange(-1, b) if b else -1,
                                 dummy=int(b > 0 and generator.random() < 0.15)) for b in range(count)]
        params = pose.random_params(generator, actions, count)
        groups.append((f'chain-{index}', tracks.build_case(f'chain-{index}', actions, bones), params, bones))
    return groups


def tick_setup(label, actions, params):
    """actions: [(stop, keys, lock)]; params: frame, speed, current, globals."""
    size = align(0x200+16*max(len(actions), 1)+0x100, PAGE)
    window = Region('window', WINDOW, poison(size, 0x47), bytes(size))
    model = WINDOW
    array = WINDOW+0x200
    window.define(model+0x26, struct.pack('<h', params.get('action_field', len(actions))))
    window.define(model+0x30, struct.pack('<I', array))
    window.define(model+0xa8, struct.pack('<H', params.get('current', 0) & 0xffff))
    for index, (stop, keys, lock) in enumerate(actions):
        window.define(array+index*16, bytes([stop]))
        window.define(array+index*16+8, struct.pack('<h', keys))
        window.define(array+index*16+0xa, bytes([lock]))
    frame = WINDOW+0x100
    prior_frame = WINDOW+0x110
    prior_action = WINDOW+0x120
    window.define(frame, struct.pack('<f', params.get('frame', 0.0)))
    if params.get('declare_prior'):
        window.define(prior_frame, struct.pack('<f', 123.0))
        window.define(prior_action, struct.pack('<H', 0x5555))
    regions = [window] + global_regions({SCENE: struct.pack('<i', params.get('scene', 0)),
                                         WORLD: struct.pack('<i', params.get('world', 0))})
    pointers = [frame, prior_frame, prior_action]
    for slot in params.get('null', ()):
        pointers[slot] = 0
    arguments = pointers+[bits(params.get('speed', 0.25)), 0xdead0000, 0xdead1000]
    return {'label': label, 'regions': regions, 'model': model, 'arguments': arguments}


def synthetic_tick_cases():
    generator = random.Random(0x12b4dd3)
    cases = []
    one = [(0, 8, 0)]
    for slot in range(3):
        cases.append(tick_setup('null-pointer', one, {'null': (slot,)}))
    cases.append(tick_setup('no-actions', [], {'action_field': 0}))
    cases.append(tick_setup('current-out-of-range', one, {'current': 1}))
    cases.append(tick_setup('current-0xffff', one, {'current': 0xffff}))
    cases.append(tick_setup('negative-action-field', one, {'action_field': -1}))
    for keys in (-1, 0, 1):
        cases.append(tick_setup('few-keys', [(0, keys, 0)], {}))
    for stop in (0, 1, 0x80):
        for lock in (0, 1, 0x40):
            for frame, speed in ((0.0, 0.25), (0.9, 0.2), (6.8, 0.3), (7.0, 0.5), (7.9, 0.2), (6.95, 0.04),
                                 (8.0, 0.0), (11.3, 1.0), (-0.5, 0.25), (0.1, -0.2), (-3.0, -1.0), (0.0, 0.0),
                                 (3.5, 16.75), (2.0, -0.0), (1e-30, -1e-30)):
                cases.append(tick_setup('flags-frames', [(stop, 8, lock)],
                                        {'frame': f32(frame), 'speed': f32(speed), 'declare_prior': frame > 5}))
    for scene in (5, 4, 6):
        for world, current in ((39, 7), (39, 6), (38, 7)):
            for frame in (5.5, 6.5, 6.95, 7.5):
                actions = [(0, 9, 0)]*8
                cases.append(tick_setup('scene-world', actions, {'scene': scene, 'world': world, 'current': current,
                                                                 'frame': frame, 'speed': 0.5}))
    for _ in range(300):
        actions = [(generator.choice([0, 0, 1]), generator.randrange(2, 40), generator.choice([0, 0, 1]))
                   for _ in range(generator.randrange(1, 6))]
        current = generator.randrange(len(actions))
        keys = actions[current][1]
        cases.append(tick_setup('random', actions, {
            'current': current, 'frame': f32(generator.uniform(-2, keys+3)),
            'speed': f32(generator.choice([generator.uniform(0, 1.5), generator.uniform(-1, 0), 0.25])),
            'scene': generator.choice([0, 5]), 'world': generator.choice([0, 39]),
            'declare_prior': generator.random() < 0.5}))
    return cases


# --------------------------------------------------------------------------
# Comparison.


def compare_transform(setup, machine, authored, negative=True):
    x86 = machine.execute(TRANSFORM_START, setup['arguments'], setup['regions'], ecx=setup['model'],
                          return_instruction=TRANSFORM_RETURN, cleanup=0x30)
    native = authored.run_transform(setup)
    python = python_transform(setup)
    checks = dict(x86['checks'], native_status=native['status'] == 0, regions=native['regions'] == x86['regions'],
                  python_model=python == x86['regions'])
    result = {'label': setup['label'], 'checks': checks, 'match': all(checks.values()), 'stopped': x86['stopped'],
              'error': x86['error'], 'branches': x86['branches'], 'trig': x86['trig'],
              'vertices': setup['vertices'], 'normals': setup['normals']}
    if negative:
        result['negatives'] = {v: python_transform(setup, v) != x86['regions']
                               for v in ('transpose', 'normal-translate')}
    if not result['match']:
        result['differing_regions'] = sorted(name for name in x86['regions']
                                             if native['regions'].get(name) != x86['regions'][name])[:8]
    return result


def compare_tick(setup, machine, authored, negative=True):
    x86 = machine.execute(TICK_START, setup['arguments'], setup['regions'], ecx=setup['model'],
                          return_instruction=TICK_RETURN, cleanup=0x18)
    native = authored.run_tick(setup)
    python, loop = python_tick(setup)
    al = x86['eax'] & 0xff
    checks = dict(x86['checks'], native_status=native['status'] == 0, regions=native['regions'] == x86['regions'],
                  loop=native['loop'] == al, python_model=(python, loop) == (x86['regions'], al))
    result = {'label': setup['label'], 'checks': checks, 'match': all(checks.values()), 'stopped': x86['stopped'],
              'error': x86['error'], 'branches': x86['branches']}
    if negative:
        result['negatives'] = {v: python_tick(setup, v) != (x86['regions'], al)
                               for v in ('prior-every-tick', 'ignore-lock')}
    return result


def helper_cases():
    generator = random.Random(0xd002b2)
    cases = []
    for _ in range(300):
        cases.append(([f32(generator.uniform(-500, 500)) for _ in range(3)],
                      [f32(generator.uniform(-3, 3)) for _ in range(12)], generator.random() < 0.2))
    cases.append(([1e-40, -0.0, 3.0], [1.0, 0.0, 0.0, 5.0, 0.0, 1.0, 0.0, -5.0, 0.0, 0.0, 1.0, 0.5], False))
    return cases


def run_helpers(machine, authored):
    results = {}
    returns = {ROTATE: 0xd0021d, VTRANSFORM: 0xd0045d, IROTATE: 0xd000ac}
    for name, start in (('rotate', ROTATE), ('transform', VTRANSFORM), ('irotate', IROTATE)):
        total = matched = 0
        for vector, matrix, alias in helper_cases():
            window = Region('window', WINDOW, poison(PAGE, 0x21), bytes(PAGE))
            source, mat, out = WINDOW+0x100, WINDOW+0x200, WINDOW+0x100 if alias else WINDOW+0x300
            window.define(source, struct.pack('<3f', *vector))
            window.define(mat, struct.pack('<12f', *matrix))
            x86 = machine.execute(start, [source, mat, out], [window], ecx=0xdeadbeef,
                                  return_instruction=returns[start], cleanup=0)
            buffer = (ctypes.c_ubyte*PAGE).from_buffer_copy(bytes(window.data))
            base = ctypes.addressof(buffer)
            authored.vectors[name](base+0x100, base+0x200, base+(out-WINDOW))
            got = bytes(buffer)
            ok = all(x86['checks'].values())
            # Only bytes the call wrote or declared inputs are compared.
            ok = ok and x86['regions']['window'][out-WINDOW:out-WINDOW+12] == got[out-WINDOW:out-WINDOW+12]
            v = vector
            rows = py_rows(matrix, v, transpose=name == 'irotate')
            if name == 'transform':
                rows = [f32(rows[k]+matrix[k*4+3]) for k in range(3)]
            if alias and name != 'irotate':
                # Sequential stores: later rows read the updated input.
                v = list(vector)
                rows = []
                for r in range(3):
                    value = py_dot(v, matrix[r*4:r*4+3])
                    if name == 'transform':
                        value = f32(value + matrix[r*4+3])
                    rows.append(value)
                    v[r] = value
            elif alias:
                v = list(vector)
                rows = []
                for r in range(3):
                    value = py_dot(v, [matrix[r], matrix[4+r], matrix[8+r]])
                    rows.append(value)
                    v[r] = value
            ok = ok and struct.pack('<3f', *rows) == got[out-WINDOW:out-WINDOW+12]
            total += 1
            matched += int(ok)
        results[name] = [total, matched]
    return results


def summarize(results):
    summary = {'cases': len(results), 'matches': sum(bool(r['match']) for r in results), 'by_label': {},
               'branches': {}, 'trig': {}, 'vertices': 0, 'normals': 0}
    for r in results:
        entry = summary['by_label'].setdefault(r['label'] if '/' not in r['label'] else 'installed', [0, 0])
        entry[0] += 1
        entry[1] += int(bool(r['match']))
        for name, count in r.get('branches', {}).items():
            summary['branches'][name] = summary['branches'].get(name, 0)+count
        for name, value in r.get('trig', {}).items():
            entry = summary['trig'].setdefault(name, [0, 0, 0])
            for k in range(3):
                entry[k] += value[k]
        summary['vertices'] += r.get('vertices', 0)
        summary['normals'] += r.get('normals', 0)
    summary['failures'] = [r for r in results if not r['match']][:12]
    return summary


# --------------------------------------------------------------------------
# Chained stages: bone-track loop -> pose builder -> transform.


def chain(label, tcase, params, transform_params, mesh_builder, machines, authored, feature):
    """Run the actual loop and builder, then the transform on their output."""
    machine_tracks, machine_pose, machine = machines
    seeded = pose.seed_case(machine_tracks, authored.pose, tcase, feature)
    if not seeded['ok'] or not seeded['authored_tracks_match']:
        return {'label': label, 'match': False, 'checks': {}, 'seed_failed': str(seeded['stopped'])}
    setup = pose.make_setup(label, tcase, seeded, params)
    built = machine_pose.run(setup)
    native = authored.pose.run(setup)
    builder_ok = all(built['checks'].values()) and built['stopped'] is None and native['status'] == 0 and \
        native['window'] == built['window'] and native['quaternions'] == built['quaternions']
    if not builder_ok:
        return {'label': label, 'match': False, 'checks': {}, 'builder_failed': str(built['stopped'])}
    window = Region('window', WINDOW, built['window'], built_defined(setup, built))
    meshes = mesh_builder(window, tcase)
    # The builder and the transform share the model's scale and origin fields.
    transform_params = dict(transform_params, body_scale=params.get('scale', 1.0),
                            origin=params.get('translation', (0.0, 0.0, 0.0)))
    transform = transform_setup(label, window, tcase['model'], setup['output_span'][0], meshes, transform_params)
    result = compare_transform(transform, machine, authored, negative=False)
    result['builder_branches'] = built['branches']
    return result


def built_defined(setup, built):
    """Defined mask after the builder: declared bytes plus every output slot."""
    defined = bytearray(setup['defined'])
    low, high = setup['output_span']
    defined[low-WINDOW:high-WINDOW] = b'\1'*(high-low)
    return defined


def synthetic_meshes(generator):
    def build(window, tcase):
        image = window.data
        model = tcase['model']
        array = struct.unpack_from('<I', image, model+0x2c-WINDOW)[0]
        usable = [b for b in range(tcase['bones']) if not image[array+b*0x8c+0x22-WINDOW]]
        start = align(window.end, PAGE)
        spec = [(generator.randrange(1, 20), generator.randrange(1, 20)) for _ in range(generator.randrange(1, 4))]
        size = align(sum(nv*16+nn*20+64 for nv, nn in spec), PAGE)
        window.data.extend(poison(start+size-window.end, 0x6b))
        window.defined.extend(bytes(start+size-window.end))
        cursor, meshes = start, []
        for nv, nn in spec:
            vertices = cursor
            for j in range(nv):
                window.define(vertices+j*16, struct.pack('<hh3f', generator.choice(usable), 0,
                                                         *[f32(generator.uniform(-80, 80)) for _ in range(3)]))
            normals = align(vertices+nv*16, 16)
            for j in range(nn):
                window.define(normals+j*20, struct.pack('<hh3fhh', generator.choice(usable), 0,
                                                        *[f32(generator.uniform(-1, 1)) for _ in range(3)], 0, 0))
            cursor = align(normals+nn*20, 16)
            meshes.append({'vertices': vertices, 'normals': normals, 'nv': nv, 'nn': nn})
        return meshes
    return build


def installed_meshes(window, tcase):
    """Mesh records pointing at the decoded file's vertex/normal records."""
    parsed = tcase['parsed']
    meshes = []
    for mesh in parsed['meshes']:
        vertex_offset = mesh['source_offset']+10-4  # offsets are relative to 'BMD\x0a' + payload
        nv, nn = len(mesh['vertices']), len(mesh['normals'])
        meshes.append({'vertices': tcase['stream']+vertex_offset, 'normals': tcase['stream']+vertex_offset+16*nv,
                       'nv': nv, 'nn': nn, 'texture': mesh['texture_index'], 'nt': len(mesh['uvs']),
                       'nf': len(mesh['polygons'])})
    return meshes


_WORKER = {}


def installed_transform_params(digest):
    generator = random.Random(int(digest[16:32], 16))
    return random_transform_params(generator)


def installed_tick_cases(case, digest):
    generator = random.Random(int(digest[32:48], 16))
    actions = case['parsed']['actions']
    if not actions:
        return []
    specs = [(generator.choice([0, 0, 1]), a['keys'], int(bool(a['lock_positions']))) for a in actions]
    cases = []
    animated = [a for a, action in enumerate(actions) if action['keys'] > 1] or list(range(len(actions)))
    for _ in range(3):
        current = generator.choice(animated)
        keys = actions[current]['keys']
        cases.append(tick_setup('tick', specs, {'current': current, 'frame': f32(generator.uniform(0, max(keys, 1))),
                                                'speed': f32(generator.choice([0.25, 0.4, 0.16, 1.0, 0.33])),
                                                'scene': generator.choice([0, 0, 5]),
                                                'world': generator.choice([0, 39])}))
    return cases


def worker_init(paths):
    text = Path(paths['text']).read_bytes()
    data = Path(paths['data']).read_bytes()
    flag = Path(paths['flag']).read_bytes()
    feature = Path(paths['feature']).read_bytes()
    _WORKER['machines'] = (tracks.Machine(text, data, flag, feature, paths['library'], None),
                           pose.PoseMachine(text, data, flag), SkinMachine(text, data, flag))
    _WORKER['authored'] = Authored(paths['library'])


def worker_model(job):
    index, path, relative = job
    raw = Path(path).read_bytes()
    try:
        case = tracks.installed_case(path, relative, raw)
    except Exception as error:  # reader rejection or decode error
        return {'label': relative, 'version': raw[3], 'reader_error': str(error)}
    digest = hashlib.sha256(raw).hexdigest()
    summary = {'label': relative, 'version': case['version'], 'sha256': digest,
               'meshes': len(case['parsed']['meshes']), 'results': [], 'ticks': []}
    samples = pose.installed_params(case, digest, index)
    if samples:
        kind, params = samples[1 % len(samples)]
        result = chain(relative, case, params, installed_transform_params(digest), installed_meshes,
                       _WORKER['machines'], _WORKER['authored'],
                       tracks.FEATURE_VALUES[index % len(tracks.FEATURE_VALUES)])
        result['kind'] = kind
        summary['results'].append({k: result[k] for k in ('match', 'branches', 'trig', 'vertices', 'normals',
                                                         'stopped', 'kind', 'seed_failed', 'builder_failed')
                                   if k in result} | ({} if result['match'] else {'checks': result['checks']}))
    else:
        summary['skipped'] = 'only zero-key actions'
    for tick in installed_tick_cases(case, digest):
        result = compare_tick(tick, _WORKER['machines'][2], _WORKER['authored'], negative=False)
        summary['ticks'].append({k: result[k] for k in ('match', 'branches', 'stopped')})
    return summary


def validate(text, data, flag, feature, library, game_root=None, versions=(12, 14), workers=1, limit=None):
    payload = tracks.load_pinned(text, tracks.TEXT_BYTES, tracks.TEXT_SHA256, 'restored text')
    data_payload = tracks.load_pinned(data, tracks.DATA_BYTES, tracks.DATA_SHA256, 'second image section')
    flag_payload = tracks.load_pinned(flag, 4, tracks.FLAG_SHA256, 'dispatch flag')
    feature_payload = tracks.load_pinned(feature, 4, tracks.FEATURE_SHA256, 'memcpy feature word')
    for table in (BODIES, pose.BODIES, tracks.BODIES):
        for name, (start, end, digest) in table.items():
            if hashlib.sha256(payload[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
                raise ValueError(f'Pinned {name} body mismatch')
    for address, value in CONSTANTS.items():
        if data_payload[address-DATA_BASE:address-DATA_BASE+4] != struct.pack('<f', value):
            raise ValueError(f'Constant at {address:#x} changed')
    import unicorn
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    for name, expected, others, ret in (('transform', TRANSFORM_CALLS, TRANSFORM_ELEMENT_CALLS, '0x30'),
                                        ('tick', TICK_CALLS, 0, '0x18')):
        start, end, _ = BODIES[name]
        decoded = list(decoder.disasm(payload[start-TEXT_BASE:end-TEXT_BASE], start))
        if sum(item.size for item in decoded) != end-start or decoded[-1].mnemonic != 'ret' or \
                decoded[-1].op_str != ret:
            raise ValueError(f'{name} decode does not land on its ret {ret}')
        calls = {item.address: item.operands[0].imm for item in decoded if item.mnemonic == 'call'}
        if any(item.mnemonic == 'call' and item.operands[0].type != X86_OP_IMM for item in decoded):
            raise ValueError(f'{name} has an indirect call')
        listed = {a: t for a, t in calls.items() if a in expected}
        rest = [t for a, t in calls.items() if a not in expected]
        if listed != expected or len(rest) != others or any(t != ELEMENT for t in rest):
            raise ValueError(f'{name} call targets changed')
    library = Path(library).resolve(strict=True)
    machine = SkinMachine(payload, data_payload, flag_payload)
    machines = (tracks.Machine(payload, data_payload, flag_payload, feature_payload, library, None),
                pose.PoseMachine(payload, data_payload, flag_payload), machine)
    authored = Authored(library)
    report = {'text_sha256': tracks.TEXT_SHA256, 'data_sha256': tracks.DATA_SHA256,
              'flag_sha256': tracks.FLAG_SHA256, 'unicorn': unicorn.__version__,
              'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'bodies': {name: {'start': hex(s), 'end_exclusive': hex(e), 'sha256': d}
                         for name, (s, e, d) in BODIES.items()},
              'transform_calls': {hex(a): hex(t) for a, t in TRANSFORM_CALLS.items()},
              'helpers': run_helpers(machine, authored)}
    transforms = [compare_transform(setup, machine, authored) for setup in synthetic_transform_cases()]
    generator = random.Random(0x75a90d8)
    chained = []
    for number, (label, tcase, params, _) in enumerate(chained_groups()):
        chained.append(chain(label, tcase, params, random_transform_params(generator), synthetic_meshes(generator),
                             machines, authored, tracks.FEATURE_VALUES[number % 3]))
    ticks = [compare_tick(setup, machine, authored) for setup in synthetic_tick_cases()]
    report['synthetic_transform'] = summarize(transforms)
    report['chained_transform'] = summarize(chained)
    report['synthetic_tick'] = summarize(ticks)
    report['negative_controls'] = {
        variant: sum(r.get('negatives', {}).get(variant, False) for r in source)
        for variant, source in (('transpose', transforms), ('normal-translate', transforms),
                                ('prior-every-tick', ticks), ('ignore-lock', ticks))}
    if game_root:
        jobs = tracks.installed_jobs(game_root, versions)
        if limit:
            jobs = jobs[:limit]
        paths = {'text': str(text), 'data': str(data), 'flag': str(flag), 'feature': str(feature),
                 'library': str(library)}
        if workers > 1:
            with multiprocessing.get_context('spawn').Pool(workers, worker_init, (paths,)) as pool:
                models = pool.map(worker_model, jobs, chunksize=4)
        else:
            worker_init(paths)
            models = [worker_model(job) for job in jobs]
        for m in models:
            for r in m.get('results', []):
                r['label'] = m['label']
            for r in m.get('ticks', []):
                r['label'] = m['label']
        per_version = {}
        for m in models:
            entry = per_version.setdefault(str(m['version']), {'files': 0, 'reader_rejected': 0, 'compared': 0,
                                                              'matches': 0, 'zero_key_only': 0, 'vertices': 0,
                                                              'normals': 0, 'ticks': 0, 'tick_matches': 0})
            entry['files'] += 1
            if 'reader_error' in m:
                entry['reader_rejected'] += 1
                continue
            entry['zero_key_only'] += int(bool(m.get('skipped')))
            for r in m['results']:
                entry['compared'] += 1
                entry['matches'] += int(bool(r['match']))
                entry['vertices'] += r.get('vertices', 0)
                entry['normals'] += r.get('normals', 0)
            entry['ticks'] += len(m['ticks'])
            entry['tick_matches'] += sum(bool(r['match']) for r in m['ticks'])
        transforms_installed = [r for m in models for r in m.get('results', [])]
        ticks_installed = [r for m in models for r in m.get('ticks', [])]
        report['installed'] = {
            'transform': summarize(transforms_installed), 'tick': summarize(ticks_installed),
            'per_version': per_version, 'reader_rejected': [m['label'] for m in models if 'reader_error' in m],
            'max_meshes': max((m.get('meshes', 0) for m in models), default=0),
            'models_over_50_meshes': sum(m.get('meshes', 0) > 50 for m in models),
            'corpus_sha256': hashlib.sha256('\n'.join(f"{m['label']}\t{m.get('sha256', '')}"
                                                      for m in models).encode()).hexdigest()}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True, help='math-capture cpu-features.bin')
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec' /
                        ('libskinning.dylib' if sys.platform == 'darwin' else 'libskinning.so'))
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--versions', default='12,14')
    parser.add_argument('--limit', type=int, help='first N installed models only')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.data, args.flag, args.feature, args.library, args.game_root,
                          tuple(int(v) for v in args.versions.split(',')), args.workers, args.limit)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    failed = not all(result['negative_controls'].values())
    failed = failed or any(total != matched for total, matched in result['helpers'].values())
    for key in ('synthetic_transform', 'chained_transform', 'synthetic_tick'):
        failed = failed or result[key]['matches'] != result[key]['cases']
    if 'installed' in result:
        for key in ('transform', 'tick'):
            failed = failed or result['installed'][key]['matches'] != result['installed'][key]['cases']
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
