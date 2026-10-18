#!/usr/bin/env python3
"""Run the client's model loader, pose builder, CPU skinning and mesh draw on the
17 v15 BMD records the strict reader rejects (MODEL-EDGE, issue #17).

Everything executes under Unicorn over the pinned restored text, the verified
second image section, the captured trig dispatch flag and the captured memcpy
feature word:

* the plaintext part of model reader 0x012b3812, from the name copy
  0x012b3b50 to its success return 0x012b4477 (header, the mesh loop with the
  texture-name parser 0x01185111 and its sub-object allocation, the action
  loop, the bone-track loop with rotation helper 0x00d00724, the stream free
  and the bone box pass 0x012b2df3/0x012b47fd, then the trailing memset);
* pose builder 0x012b5064 with every helper it reaches;
* model transform 0x012b5bde (CPU skinning);
* mesh draw 0x012b8d1d with the GL state wrappers.

Client memory is laid out at the client's own addresses. The whole third
image section 0x01cec000..0x0bdd9000 is mapped zero-filled, which is what a
loader gives uninitialized data; the captured flag/feature words and declared
caller state are written into it. Every access to that section and to the
heap arena is classified: known client tables (bone buffer, transform outputs,
colour table, bone boxes, ...) or "foreign" memory. Foreign reads and writes
are recorded with their address and instruction instead of stopping, because
recording them is the point of this run.

Modelled boundaries (not client code), all stated in the report:
* HeapAlloc/HeapFree (Wine ntdll behind IAT slots 0x01a7c5c8/0x01a7c5c4): a
  bump allocator handing out poison-filled blocks; reads of never-written
  heap bytes and reads outside every live block are recorded;
* CRT _getptd 0x019a4ba6 (strtok state) returns a zeroed per-thread record;
* the two bitmap map lookups 0x00c97c2d/0x00ebbec8 return the zeroed static
  error record 0x01ec3030 (the client's lookup-miss result);
* OPENGL32 import slots point at a recorder that logs the call and returns;
* caller state the routines read but do not compute: the model object's
  version byte, pose arguments and animation fields, transform arguments and
  globals (bone scale 1.0, override/world/bounds mode/scene 0), the texture
  index table and the GL caches.

Variants make the dependence on unknown state explicit: every pose and
transform runs twice, once with the bone buffer and foreign spans zero and
once with them filled with a finite pattern, and outputs are compared.
The authored C (libmodelreader, libskinning) runs on the same memory images
and must match the client byte for byte.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    path = ROOT/'scripts'/f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tracks = _load('validate_bone_tracks')
TEXT_BASE, TEXT_BYTES, DATA_BASE, DATA_BYTES = tracks.TEXT_BASE, tracks.TEXT_BYTES, tracks.DATA_BASE, tracks.DATA_BYTES

BODIES = {  # start, exclusive end, SHA-256 of the captured bytes (Capstone decodes land on the end)
    'reader': (0x012b3812, 0x012b4485, '544459ba8eb082e25c1c5400cd6e025867ac17f3ec6024ac84f7585ecbfb08a9'),
    'bone_boxes_entry': (0x012b2df3, 0x012b2e81, '3814a8b4ff6adeb576179066e8171a0ad6a6592c96f5ec6eabb7655eab4d87e4'),
    'bone_boxes': (0x012b47fd, 0x012b4dd3, 'a02c98cd87ed5c3a490507c0f438cc2e3d7938480bacd0e9784d5b3e2d03fbb4'),
    'vector_ctor': (0x0098642b, 0x00986457, '9e5a7ef456aff96676a3fce49cd63fe4d6741c16fd949d8e016aa9fe9aee8786'),
    'fill': (0x010a8263, 0x010a8290, 'd9a3e36b0a88c5c689f2902bf5e37d74241a5cfacd049f6dfead7986e1d6a7aa'),
    'sub_init': (0x010a8290, 0x010a82be, '71f427ec7af087d378860461c8632dc2977ab99de6fa894dae0f33fef49b66ed'),
    'name_init': (0x010a82be, 0x010a82d9, '6c8003c471c512e3c49bc142baebe48278396661b5ba4653d62009cec177f632'),
    'sub_copy': (0x011850cc, 0x01185111, 'd4d5cf82f0e7e2d9b8286b2cc37e333ff5dad1534439862672543f8d78a9a3ce'),
    'name_dtor': (0x010a8344, 0x010a8356, 'e1ee77d5fd9b1106f21fee0b5dab226f4d49bee78dfdc88ec7007f9a19c3c906'),
    'free': (0x019a4d50, 0x019a4d8a, 'b0ddf655f6636e53baf006b86cdd42fa300a6b6d893bcebc83f8c1e139abd459'),
    'memset': (0x0194cd00, 0x0194ce60, '75b8edf78e661689f1cb51215ebaf1aad002d087b679f1230d68ef18971567bc'),
    'builder': (0x012b5064, 0x012b58ce, '11a830ee49191265f3d7175caf1f9c11c45327ebd277562d30fd0e0671527d94'),
    'transform': (0x012b5bde, 0x012b678d, 'a546b109d885d267c1269b62cf2cdf694ee0d8faf3440979ffe7fa03f38bd2e9'),
    'mesh_draw': (0x012b8d1d, 0x012bb35a, 'd19663bdf961b7a6e0adc64ccfb42c935844b40933bb056aa4bc739a3d611660'),
    'timing': (0x012aeb2b, 0x012aeca4, '02b0886d0b2b3fb32f6293dbc9caf0874eef065e70b3eff86716019b4056f4db'),
}

# The 17 installed inputs (docs/research/model-edge.md); each file is hash-checked before use.
EDGE_FILES = {
    'Data/Item/dark_05.bmd': 'b1c70013c125951e5e8decc8a2c69094b61f3b9b915542fdccd8e3f46eb85191',
    'Data/Item/medusa.bmd': '1a6d10e8ee2bd0f77a0ff18fe6bed499d3f66c6ae51de115b41dd432217519aa',
    'Data/Item/medusaUp.bmd': 'fc92f031065093e4afdfb578d67f359219d36db4a6dc4f4ee56fd4a89b42224c',
    'Data/Item/rockinghorsepet_evol.bmd': 'c4e907ddcab9e1c9bc480b3999850312ed2259c143cc687b01f261a3d53c9625',
    'Data/Item/scorpio.bmd': 'bffcedd5a86e10aa41c6021a96fb44242f2889603d1c969649415d955f4c631a',
    'Data/Item/scorpioUp.bmd': 'b1783d52f892595772c47923919764a86dd7b5c9d12e7567d15e400eae658c63',
    'Data/Item/selupan.bmd': '4a2a55a0eef116116934e8db06daf5b7893e5e7c4e7e66e516d3fddd8c3ed0ff',
    'Data/Item/selupanUp.bmd': '07b606edf9dbfcf7e4366b6bee53835a3af89c9c4d344e38fbad5d2273dd2002',
    'Data/Monster/Monster151.bmd': 'b3552842a8c66f6af1bd0b54f2da9a5c0a19668a4f94fb3309a48ec013ca0b6e',
    'Data/Monster/Monster211.bmd': '801eb845a6659c31c6479a03b24f5de531630c2b1820ed31537039dba0002e3a',
    'Data/Monster/Monster214.bmd': 'a764e05209e34939cf89ec09b1c78771a07db53f0b7a07ca8c58cad4e607fa63',
    'Data/Monster/Monster215.bmd': '143dd9a4a95cfeb1e5b1fb9e137197c6c8d86582139205b63d3d9500beeb8b2b',
    'Data/Monster/Monster415.bmd': 'e79e4de2397ed173eb22312a2ac7df57011096a666047456d5a4527f144f6f2d',
    'Data/Monster/Monster444.bmd': 'dc8a1dd603876aa986ca570d8c3c9cdccbaa171a0d2f648a60046ffcf0561dc2',
    'Data/Monster/monster223.bmd': '2f57f4adc35432b75ab3aa1858855c12b49991a8b81dc099e05731056066597b',
    'Data/Object134/Object13.bmd': '25b7d2efa9a317cec8f3817c6a59ce5a54b543c0e9d755c22230ac092a727bcc',
    'Data/Skill/CW_Bow_Skill.bmd': 'cf7dad2c6d1e2c8e1fddfa865248b150e1cab3c3ebb7eebbc283ecbfbb313700',
}

READER_START, READER_SUCCESS = 0x012b3b50, 0x012b4477
BUILDER, TRANSFORM, MESH_DRAW = 0x012b5064, 0x012b5bde, 0x012b8d1d
NAME_PARSER, SUB_NEW = 0x01185111, 0x012b40c7
GETPTD, BITMAP_LOOKUPS = 0x019a4ba6, (0x00c97c2d, 0x00ebbec8)
ERROR_BITMAP = 0x01ec3030
HEAPALLOC_SLOT, HEAPFREE_SLOT = 0x01a7c5c8, 0x01a7c5c4
HEAPALLOC_TARGET, HEAPFREE_TARGET = 0x7bc275e0, 0x7b62dad0
HEAP_TOKEN = tracks.HEAP_TOKEN
OPENGL32_SLOTS = (0x01a7c64c, 0x01a7c790)
GL_STUBS = 0x7a800000
GL_SLOTS = {0x1a7c750: ('glBegin', 1), 0x1a7c760: ('glEnd', 0), 0x1a7c774: ('glTexCoord2f', 2),
            0x1a7c76c: ('glColor3f', 3), 0x1a7c770: ('glColor3fv', 1), 0x1a7c754: ('glColor4f', 4),
            0x1a7c778: ('glVertex3fv', 1), 0x1a7c75c: ('glEnable', 1), 0x1a7c758: ('glDisable', 1),
            0x1a7c748: ('glBlendFunc', 2), 0x1a7c740: ('glDepthMask', 1), 0x1a7c77c: ('glBindTexture', 2),
            0x1a7c718: ('glPushMatrix', 0), 0x1a7c72c: ('glPopMatrix', 0)}

SECTION3, SECTION3_END = 0x01ced000, 0x0bdd2000
ARENA, ARENA_BYTES = 0x40000000, 0x04000000
STACK, STACK_BYTES = 0x31000000, 0x40000
TEB, GDT, SENTINEL = 0x32000000, 0x32001000, 0x33000000
PTD = 0x32002000
FRAME_BASE = STACK+0x30000
FPCW, MXCSR = 0x027f, 0x1f80

# Client tables at fixed addresses (docs/research/client-skinning.md, model-hierarchy.md).
BONES, QUATERNIONS, ROOT_MATRIX = 0x06fce398, 0x075a90d8, 0x078965ac
VERTICES, NORMALS, LIGHTS, SECONDARY = 0x078978a0, 0x0812cce0, 0x06fd0918, 0x075a9ee8
COLOURS, TEXCOORD_TABLE = 0x089c2120, 0x072acfd8
VERTEX_STRIDE, LIGHT_STRIDE = 0x2bf20, 0xea60
BOX_COUNTS, BOX_MIN, BOX_MAX = 0x075a9d58, 0x078965e0, 0x07896f40
BONE_SCALE, LIGHT_OVERRIDE, WORLD, BOUNDS_MODE, SCENE = 0x01cf104c, 0x01cf1048, 0x01cf15fc, 0x0b437bfc, 0x01d1df70
TIME = 0x06fce370
KNOWN = [  # name, base, bytes
    ('bones', BONES, 200*0x30), ('quaternions', QUATERNIONS, 0x075a9ee8-QUATERNIONS), ('root', ROOT_MATRIX, 0x30),
    ('box-counts', BOX_COUNTS, 200*2), ('box-min', BOX_MIN, 200*12), ('box-max', BOX_MAX, 200*12),
    ('vertices', VERTICES, 50*VERTEX_STRIDE), ('normals', NORMALS, 50*VERTEX_STRIDE),
    ('lights', LIGHTS, 50*LIGHT_STRIDE), ('secondary', SECONDARY, 50*LIGHT_STRIDE),
    ('colours', COLOURS, 50*VERTEX_STRIDE), ('texcoord-table', TEXCOORD_TABLE, 15001*8),
    ('bone-scale', BONE_SCALE, 4), ('light-override', LIGHT_OVERRIDE, 1), ('world', WORLD, 4),
    ('bounds-mode', BOUNDS_MODE, 4), ('scene', SCENE, 4), ('time', TIME, 4),
    ('trig-flag', tracks.FLAG_ADDRESS, 4), ('memcpy-feature', tracks.FEATURE_ADDRESS, 4),
    ('memcpy-feature-2', tracks.SYNTHETIC_FEATURE, 4), ('heap-handle', tracks.HEAP_HANDLE, 4),
    ('error-bitmap', ERROR_BITMAP, 0x222),
    # GL caches and texture globals read by the mesh draw wrappers.
    ('gl-caches', 0x0bdc58b0, 0xe0), ('bind-cache', 0x01cf1620, 4), ('env-vector', 0x0a381de0, 12),
    ('skin-base', 0x0b6b53e0, 4), ('strchr-sse', 0x0bdcb280, 4), ('security-cookie', 0x01cf65c0, 4),
]
GLOBAL_NAMES = ('bone-scale', 'light-override', 'world', 'bounds-mode', 'scene', 'time', 'trig-flag', 'memcpy-feature',
                'memcpy-feature-2', 'heap-handle', 'error-bitmap', 'gl-caches', 'bind-cache', 'env-vector', 'skin-base',
                'strchr-sse', 'security-cookie', 'texcoord-table')
GLOBAL_SPANS = [k for k in KNOWN if k[0] in GLOBAL_NAMES]
# Read-modify-write instructions whose result ignores the old value (AND with 0,
# OR with -1): their reads of never-written bytes are not data dependences.
CONSTANT_RMW = {0x010a82e3, 0x010a82ea, 0x010a82f1, 0x010a82f8, 0x010a82ff, 0x012b3dde, 0x012b421c, 0x012b2e66,
                0x012b4130}
STATE_TABLES = ('bones', 'quaternions', 'root', 'vertices', 'normals', 'lights', 'secondary', 'colours',
                'texcoord-table')


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def align(value, boundary=16):
    return (value+boundary-1) & -boundary


def load_pinned(path, size, digest, label):
    return tracks.load_pinned(path, size, digest, label)


# --------------------------------------------------------------------------
# Independent Python model of the reader's layout walk (third implementation).


def client_layout(payload):
    """The reader's stream walk: no index, bone, parent or value checks."""
    def s16(o):
        return struct.unpack_from('<h', payload, o)[0]
    o = 32
    nm, nb, na = s16(o), s16(o+2), s16(o+4)
    o += 6
    meshes = []
    for _ in range(max(nm, 0)):
        nv, nn, nt, nf, texture = struct.unpack_from('<5h', payload, o)
        o += 10
        mesh = {'nv': nv, 'nn': nn, 'nt': nt, 'nf': nf, 'texture': texture, 'vertices': o}
        o += 16*nv
        mesh['normals'] = o
        o += 20*nn
        mesh['uvs'] = o
        o += 8*nt
        mesh['polygons'] = o
        o += 64*nf
        mesh['name'] = payload[o:o+32]
        o += 32
        meshes.append(mesh)
    actions = []
    for _ in range(max(na, 0)):
        keys, lock = s16(o), payload[o+2]
        actions.append({'keys': keys, 'lock': lock, 'positions': o+3})
        o += 3+(12*keys if lock else 0)
    bones = []
    for _ in range(max(nb, 0)):
        dummy = payload[o]
        bone = {'offset': o, 'dummy': dummy}
        o += 1
        if not dummy:
            bone['name'] = payload[o:o+32]
            bone['parent'] = s16(o+32)
            o += 34
            bone['tracks'] = []
            for action in actions:
                bone['tracks'].append((o, o+12*action['keys']))
                o += 24*action['keys']
        bones.append(bone)
    return {'meshes': meshes, 'actions': actions, 'bones': bones, 'counts': (nm, nb, na), 'end': o}


def edge_census(payload, layout):
    """Every value outside the strict reader's supported semantics."""
    out = []
    nb = len(layout['bones'])
    bones = layout['bones']

    def s16(o):
        return struct.unpack_from('<h', payload, o)[0]
    for mi, mesh in enumerate(layout['meshes']):
        for j in range(mesh['nv']):
            node = s16(mesh['vertices']+16*j)
            if not 0 <= node < nb or bones[node]['dummy']:
                out.append(('vertex-bone', mi, j, node))
        for j in range(mesh['nn']):
            node = s16(mesh['normals']+20*j)
            if not 0 <= node < nb or bones[node]['dummy']:
                out.append(('normal-bone', mi, j, node))
        for j in range(mesh['nf']):
            o = mesh['polygons']+64*j
            corners = payload[o]
            for kind, field, upper in (('vertex', 2, mesh['nv']), ('normal', 10, mesh['nn']), ('uv', 18, mesh['nt'])):
                for k in range(min(corners, 4)):
                    index = s16(o+field+2*k)
                    if not 0 <= index < upper:
                        out.append((f'{kind}-index', mi, j, k, index))
    for bi, bone in enumerate(bones):
        if bone['dummy']:
            continue
        parent = bone['parent']
        if 0 <= parent < nb and bones[parent]['dummy']:
            out.append(('dummy-parent', bi, parent))
        for ai, (po, ro) in enumerate(bone['tracks']):
            for q in range(3*layout['actions'][ai]['keys']):
                for kind, base in (('position', po), ('rotation', ro)):
                    if not math.isfinite(struct.unpack_from('<f', payload, base+4*q)[0]):
                        out.append((f'nonfinite-{kind}', bi, ai, q//3, q % 3,
                                    payload[base+4*q:base+4*q+4][::-1].hex()))
    return out


def affected_bones(layout):
    """Non-dummy bones whose parent chain reaches a dummy record."""
    bones, out = layout['bones'], set()
    for i in range(len(bones)):
        current, seen = i, set()
        while current != -1 and 0 <= current < len(bones) and current not in seen:
            seen.add(current)
            if bones[current]['dummy']:
                if current != i:
                    out.add(i)
                break
            current = bones[current]['parent']
    return sorted(out)


# --------------------------------------------------------------------------
# Emulator.


class EdgeMachine:
    def __init__(self, text, data, flag, feature):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                             UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED, UC_PROT_READ, UC_PROT_WRITE,
                             UC_PROT_EXEC, UC_PROT_ALL, UC_MEM_WRITE)
        from unicorn import x86_const as x86
        self.x86, self.UC_MEM_WRITE = x86, UC_MEM_WRITE
        RW = UC_PROT_READ | UC_PROT_WRITE
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, align(DATA_BYTES, 0x1000), UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        self.flag, self.feature = flag, feature
        uc.mem_map(SECTION3, SECTION3_END-SECTION3, RW)
        uc.mem_map(ARENA, ARENA_BYTES, RW)
        uc.mem_map(STACK, STACK_BYTES, RW)
        uc.mem_map(TEB, 0x4000, RW)
        uc.mem_map(SENTINEL, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
        for page in (HEAPALLOC_TARGET & ~0xfff, HEAPFREE_TARGET & ~0xfff):
            uc.mem_map(page, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
            uc.mem_write(page, b'\xcc'*0x1000)
        uc.mem_write(HEAPALLOC_TARGET, b'\xc2\x0c\x00')   # ret 0xc; EAX set by the hook
        uc.mem_write(HEAPFREE_TARGET, b'\xc2\x0c\x00')
        uc.mem_map(GL_STUBS, 0x00100000, UC_PROT_ALL)
        uc.mem_write(GL_STUBS, b'\xcc'*0x00100000)
        self.gl_names = {}
        for slot in range(OPENGL32_SLOTS[0], OPENGL32_SLOTS[1], 4):
            value = struct.unpack('<I', bytes(uc.mem_read(slot, 4)))[0]
            if GL_STUBS <= value < GL_STUBS+0x00100000:
                self.gl_names[value] = slot
        self.setup_segments()
        uc.hook_add(UC_HOOK_CODE, self.heap_alloc, begin=HEAPALLOC_TARGET, end=HEAPALLOC_TARGET)
        uc.hook_add(UC_HOOK_CODE, self.heap_free, begin=HEAPFREE_TARGET, end=HEAPFREE_TARGET)
        uc.hook_add(UC_HOOK_CODE, self.gl_call, begin=GL_STUBS, end=GL_STUBS+0x000fffff)
        uc.hook_add(UC_HOOK_CODE, self.getptd, begin=GETPTD, end=GETPTD)
        for address in BITMAP_LOOKUPS:
            uc.hook_add(UC_HOOK_CODE, self.lookup, begin=address, end=address)
        uc.hook_add(UC_HOOK_CODE, self.name_parser_return, begin=0x012b40c0, end=0x012b40c0)
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.section3_access, begin=SECTION3, end=SECTION3_END-1)
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.arena_access, begin=ARENA, end=ARENA+ARENA_BYTES-1)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.unmapped)
        self.known = sorted(KNOWN, key=lambda k: k[1])
        self.known_bases = [k[1] for k in self.known]
        self.dirty = set()
        self.reset()

    def setup_segments(self):
        uc, x86 = self.uc, self.x86

        def descriptor(base, limit, access, flags):
            return struct.pack('<HHBBBB', limit & 0xffff, base & 0xffff, (base >> 16) & 0xff, access,
                               ((limit >> 16) & 0xf) | (flags << 4), (base >> 24) & 0xff)
        table = (bytes(8)+descriptor(0, 0xfffff, 0x9a, 0xc)+descriptor(0, 0xfffff, 0x92, 0xc)
                 + descriptor(TEB, 0xfff, 0x92, 0x4))
        uc.mem_write(GDT, table)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, GDT, len(table)-1, 0x0))
        uc.reg_write(x86.UC_X86_REG_FS, 3 << 3)
        for reg in (x86.UC_X86_REG_SS, x86.UC_X86_REG_DS, x86.UC_X86_REG_ES):
            uc.reg_write(reg, 2 << 3)

    # ---- state -------------------------------------------------------------
    def reset(self):
        """Zero every written page of the third section; empty heap."""
        uc = self.uc
        for page in self.dirty:
            uc.mem_write(page, bytes(0x1000))
        self.dirty = set()
        self.put(tracks.FLAG_ADDRESS, self.flag)
        self.put(tracks.FEATURE_ADDRESS, self.feature)
        self.put(tracks.HEAP_HANDLE, struct.pack('<I', HEAP_TOKEN))
        self.put(BONE_SCALE, struct.pack('<f', 1.0))
        self.blocks = {}          # base -> size (live)
        self.freed = {}
        self.cursor = ARENA+0x1000
        self.defined = bytearray(ARENA_BYTES)
        self.allocations = []
        self.names = []
        self.state = None

    def put(self, address, payload):
        self.uc.mem_write(address, bytes(payload))
        if SECTION3 <= address < SECTION3_END:
            for page in range(address & ~0xfff, align(address+len(payload), 0x1000), 0x1000):
                self.dirty.add(page)

    def read(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def allocate(self, size, defined=False):
        address = align(self.cursor+16)
        if address+max(size, 1) > ARENA+ARENA_BYTES:
            raise ValueError('harness heap exhausted')
        self.cursor = address+max(size, 1)
        index = len(self.allocations)+1
        poison = bytes(((index*29+offset*7+0x5a) & 0xff) | 0x80 for offset in range(min(max(size, 1), 4096)))
        payload = (poison*(max(size, 1)//len(poison)+1))[:max(size, 1)]
        self.uc.mem_write(address, payload)
        self.blocks[address] = max(size, 1)
        if defined:
            self.defined[address-ARENA:address-ARENA+size] = b'\1'*size
        return address

    def define(self, address, payload):
        """Declare caller-supplied bytes (heap or third section)."""
        self.put(address, payload)
        if ARENA <= address < ARENA+ARENA_BYTES:
            self.defined[address-ARENA:address-ARENA+len(payload)] = b'\1'*len(payload)

    # ---- hooks -------------------------------------------------------------
    def pc(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_EIP)

    def esp(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_ESP)

    def stop(self, reason):
        if self.state['stopped'] is None:
            self.state['stopped'] = reason
        self.uc.emu_stop()

    def unmapped(self, uc, access, address, size, value, ignored):
        self.stop(('unmapped', hex(address), size, hex(self.pc())))
        return False

    def heap_alloc(self, uc, address, size, ignored):
        returned, heap, flags, request = struct.unpack('<4I', self.read(self.esp(), 16))
        if heap != HEAP_TOKEN or flags != 0:
            self.stop(('heapalloc-arguments', hex(returned), hex(heap), flags))
            return
        block = self.allocate(request)
        self.allocations.append((request, block, hex(self.state['caller'])))
        uc.reg_write(self.x86.UC_X86_REG_EAX, block)

    def heap_free(self, uc, address, size, ignored):
        returned, heap, flags, block = struct.unpack('<4I', self.read(self.esp(), 16))
        if block in self.blocks:
            self.freed[block] = self.blocks.pop(block)
        else:
            self.stop(('free-of-unknown-block', hex(block)))
        self.state['frees'].append(block)
        uc.reg_write(self.x86.UC_X86_REG_EAX, 1)

    def getptd(self, uc, address, size, ignored):
        esp = self.esp()
        uc.reg_write(self.x86.UC_X86_REG_EAX, PTD)
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp+4)
        uc.reg_write(self.x86.UC_X86_REG_EIP, self.u32(esp))

    def lookup(self, uc, address, size, ignored):
        esp = self.esp()
        self.state['lookups'] += 1
        uc.reg_write(self.x86.UC_X86_REG_EAX, ERROR_BITMAP)
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp+8)
        uc.reg_write(self.x86.UC_X86_REG_EIP, self.u32(esp))

    def name_parser_return(self, uc, address, size, ignored):
        self.names.append(uc.reg_read(self.x86.UC_X86_REG_EAX) & 0xff)

    def gl_call(self, uc, address, size, ignored):
        slot = self.gl_names.get(address)
        if slot not in GL_SLOTS:
            self.stop(('unexpected-import', hex(slot) if slot else hex(address)))
            return
        name, count = GL_SLOTS[slot]
        esp = self.esp()
        args = list(struct.unpack('<%dI' % count, self.read(esp+4, 4*count))) if count else []
        if name in ('glColor3fv', 'glVertex3fv'):
            pointer = args[0]
            args = [pointer]+list(struct.unpack('<3I', self.read(pointer, 12)))
            state = self.state
            inside = self.find(state['expected'], state['expected_bases'], pointer, 12)[0]
            if inside is None and SECTION3 <= pointer < SECTION3_END:
                key = ('gl', pointer, name)
                if key not in state['foreign_seen']:
                    state['foreign_seen'].add(key)
                    state['foreign'].append({'write': False, 'address': hex(pointer), 'size': 12,
                                             'pc': f'{name} argument', 'value': self.read(pointer, 12).hex(),
                                             'inside': self.annotate(pointer)})
        self.state['gl'].append((name, *args))
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp+4+4*count)
        uc.reg_write(self.x86.UC_X86_REG_EIP, self.u32(esp))

    @staticmethod
    def find(spans, bases, address, size):
        import bisect
        index = bisect.bisect_right(bases, address)-1
        if index >= 0:
            name, base, length = spans[index]
            if address+size <= base+length:
                return name, base
        return None, None

    def annotate(self, address):
        """Name of the known client table holding a foreign address, with entry index."""
        name, base = self.find(self.known, self.known_bases, address, 1)
        if name is None:
            return None
        offset = address-base
        if name in ('vertices', 'normals', 'colours'):
            return f'{name} mesh {offset//VERTEX_STRIDE} entry {(offset % VERTEX_STRIDE)/12:g}'
        if name in ('lights', 'secondary'):
            return f'{name} mesh {offset//LIGHT_STRIDE} entry {(offset % LIGHT_STRIDE)/4:g}'
        if name == 'bones':
            return f'bones slot {offset/0x30:g}'
        return f'{name}+{offset:#x}'

    def section3_access(self, uc, access, address, size, value, ignored):
        state = self.state
        write = access == self.UC_MEM_WRITE
        if write:
            self.dirty.add(address & ~0xfff)
        name, base = self.find(state['expected'], state['expected_bases'], address, size)
        if name is None:
            key = (write, address, size, self.pc())
            if key not in state['foreign_seen']:
                state['foreign_seen'].add(key)
                state['foreign'].append({'write': write, 'address': hex(address), 'size': size, 'pc': hex(self.pc()),
                                         'value': self.read(address, size).hex() if not write else
                                         (value & ((1 << (8*size))-1)).to_bytes(size, 'little').hex(),
                                         'inside': self.annotate(address)})
            return
        written = state['written']
        if write:
            written.update(range(address, address+size))
            return
        if name in STATE_TABLES and not all(a in written for a in range(address, address+size)):
            state['prior_reads'].setdefault(name, set()).add(address-base)

    def arena_access(self, uc, access, address, size, value, ignored):
        offset = address-ARENA
        if access == self.UC_MEM_WRITE:
            self.defined[offset:offset+size] = b'\1'*size
            return
        spans = self.state['arena_expected']
        if spans is not None and self.find(spans, self.state['arena_bases'], address, size)[0] is None:
            key = ('heap', address, size, self.pc())
            if key not in self.state['foreign_seen']:
                self.state['foreign_seen'].add(key)
                self.state['foreign'].append({'write': False, 'address': hex(address), 'size': size,
                                              'pc': hex(self.pc()), 'value': self.read(address, size).hex(),
                                              'inside': 'heap outside the routine\'s records'})
        if b'\0' not in self.defined[offset:offset+size]:
            return
        pc = self.pc()
        if 0x0194c200 <= pc < 0x0194c774:   # memcpy reads whole aligned 16-byte units around its source
            source, length = self.state['copy']
            if (source & ~15) <= address and address+size <= align(source+length):
                self.state['memcpy_overreads'] += 1
                return
        inside = any(b <= address < b+s for b, s in self.blocks.items())
        key = (inside, pc)
        record = self.state['undefined_reads'].setdefault(key, [0, hex(address), set()])
        record[0] += 1
        if len(record[2]) < 64:
            record[2].add((address, size))

    def memcpy_entry(self, uc, address, size, ignored):
        _, destination, source, length = struct.unpack('<4I', self.read(self.esp(), 16))
        self.state['copy'] = (source, length)

    # ---- execution ---------------------------------------------------------
    def begin(self, caller, expected=(), arena=None):
        """expected: (name, base, bytes) spans of the third section this stage legitimately uses;
        arena: optional heap spans it may read (others are recorded as foreign heap reads)."""
        spans = sorted(list(expected)+GLOBAL_SPANS, key=lambda k: k[1])
        arena_spans = sorted(arena, key=lambda k: k[1]) if arena is not None else None
        self.state = {'stopped': None, 'foreign': [], 'foreign_seen': set(), 'written': set(), 'prior_reads': {},
                      'undefined_reads': {}, 'memcpy_overreads': 0, 'copy': (0, 0), 'frees': [], 'gl': [],
                      'lookups': 0, 'caller': caller, 'expected': spans, 'expected_bases': [k[1] for k in spans],
                      'arena_expected': arena_spans,
                      'arena_bases': [k[1] for k in arena_spans] if arena_spans is not None else None}
        if not hasattr(self, 'memcpy_hook'):
            from unicorn import UC_HOOK_CODE
            self.memcpy_hook = self.uc.hook_add(UC_HOOK_CODE, self.memcpy_entry, begin=0x0194c200, end=0x0194c200)

    def registers(self, esp, ebp, ecx=0xdeadbeef):
        uc, x86 = self.uc, self.x86
        self.preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a,
                          x86.UC_X86_REG_EDI: 0x456789ab}
        for register, value in self.preserved.items():
            uc.reg_write(register, value)
        uc.reg_write(x86.UC_X86_REG_EAX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_EDX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        for index in range(8):
            lane = 0x7ff4dead5eed0000+index*0x0101010101
            uc.reg_write(getattr(x86, f'UC_X86_REG_XMM{index}'), lane | (lane << 64))
        uc.reg_write(x86.UC_X86_REG_EBP, ebp)
        uc.reg_write(x86.UC_X86_REG_ESP, esp)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_FPSW, 0)
        uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)

    def go(self, start, end, limit=2_000_000_000):
        error = None
        try:
            self.uc.emu_start(start, end, timeout=0, count=limit)
        except Exception as failure:  # UcError
            error = str(failure)
        return error

    def common_checks(self, end):
        x86, uc = self.x86, self.uc
        return {'reached_end': self.pc() == end and self.state['stopped'] is None,
                'callee_saved': all(uc.reg_read(r) == v for r, v in self.preserved.items()),
                'direction_flag': (uc.reg_read(x86.UC_X86_REG_EFLAGS) >> 10) & 1 == 0,
                'fpcw': uc.reg_read(x86.UC_X86_REG_FPCW) == FPCW,
                'mxcsr_control': uc.reg_read(x86.UC_X86_REG_MXCSR) & ~0x3f == MXCSR,
                'x87_top': (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7 == 0}

    def summary(self):
        state = self.state
        return {'stopped': state['stopped'], 'foreign': state['foreign'],
                'prior_reads': {k: sorted(v) for k, v in state['prior_reads'].items()},
                'undefined_reads': [{'inside_block': k[0], 'pc': hex(k[1]), 'count': v[0], 'first': v[1],
                                     'spans': sorted(v[2])}
                                    for k, v in state['undefined_reads'].items() if k[1] not in CONSTANT_RMW],
                'memcpy_overreads': state['memcpy_overreads']}

    # ---- stages ------------------------------------------------------------
    def run_reader(self, payload, version=15, authored=None):
        """Reader 0x012b3b50..0x012b4477 on a decoded payload; returns the model object.

        With authored, the authored C runs on a snapshot of the same input and must
        leave the heap arena and the third-section state window byte-identical."""
        bones = max(client_layout(payload)['counts'][1], 0)
        self.begin(READER_START, [('box-counts', BOX_COUNTS, 2*bones), ('box-min', BOX_MIN, 12*bones),
                                  ('box-max', BOX_MAX, 12*bones)])
        model = self.allocate(0xd0)
        self.define(model+0x20, bytes([version]))
        stream = self.allocate(len(payload))
        self.define(stream, payload)
        ebp = FRAME_BASE
        self.put(ebp-0x470, b'\xa5'*0x470)
        self.put(ebp-0x18, struct.pack('<IIi', stream, model, 0))   # [ebp-0x18] stream, -0x14 model, -0x10 offset
        self.put(ebp-0xc, struct.pack('<III', 0xffffffff, 0x01a1ce74, 0xffffffff))
        self.put(TEB, struct.pack('<I', ebp-0xc))
        self.put(PTD, bytes(0x100))
        self.registers(ebp-0x470, ebp)
        snapshot = Snapshot(self) if authored else None
        error = self.go(READER_START, READER_SUCCESS)
        checks = self.common_checks(READER_SUCCESS)
        checks['al_one'] = self.uc.reg_read(self.x86.UC_X86_REG_EAX) & 0xff == 1
        checks['esp'] = self.esp() == ebp-0x470
        checks['stream_freed'] = self.state['frees'] == [stream]
        result = dict(self.summary(), checks=checks, error=error, model=model, stream=stream,
                      offset=struct.unpack('<i', self.read(ebp-0x10, 4))[0],
                      allocations=[(size, hex(block)) for size, block, _ in self.allocations],
                      names=list(self.names))
        result['match'] = all(checks.values()) and error is None
        if authored:
            flags = []
            for mesh in mesh_records(self, model):
                flags.append(self.read(mesh['sub'], 5) if mesh['sub'] else bytes(5))
            native = authored.run_reader(snapshot, model, stream, self.names, flags)
            diffs = snapshot.same_as(self)
            result['authored'] = {'status': native['status'], 'offset': native['offset'] == result['offset'],
                                  'released': native['released'] == [stream], 'differences': diffs,
                                  'name_calls': native['name_calls'] == len(self.names)}
            result['authored']['match'] = (native['status'] == 0 and not diffs and result['authored']['offset'] and
                                           result['authored']['released'] and result['authored']['name_calls'])
            result['match'] = result['match'] and result['authored']['match']
        return result

    def call(self, start, arguments, ecx, cleanup):
        esp = STACK+0x20000
        self.put(esp, struct.pack('<I', SENTINEL)+b''.join(struct.pack('<I', a & 0xffffffff) for a in arguments))
        self.registers(esp, 0x56789abc, ecx)
        self.preserved[self.x86.UC_X86_REG_EBP] = 0x56789abc
        self.put(TEB, struct.pack('<I', 0xffffffff))
        error = self.go(start, SENTINEL)
        checks = self.common_checks(SENTINEL)
        checks['esp'] = self.esp() == esp+4+cleanup
        checks['seh'] = self.u32(TEB) == 0xffffffff
        return dict(self.summary(), checks=checks, error=error, match=all(checks.values()) and error is None,
                    gl=list(self.state['gl']), lookups=self.state['lookups'])


# --------------------------------------------------------------------------
# Caller state for the later stages.

def set_model_fields(machine, model, *, action=0, scale=1.0, origin=(0.0, 0.0, 0.0), lighting=1,
                     colour=(1.0, 1.0, 1.0)):
    machine.define(model+0x50, bytes([lighting]))
    machine.define(model+0x54, struct.pack('<3f', *colour))
    machine.define(model+0x74, struct.pack('<4f', scale, *origin))
    machine.define(model+0x90, struct.pack('<f', 0.0))
    machine.define(model+0x98, struct.pack('<3f', 0.0, 0.0, 0.0))
    machine.define(model+0xa8, struct.pack('<H', action))
    machine.define(model+0xa4, bytes(3))      # skin shift / flags read by the mesh draw
    machine.define(model+0x44, struct.pack('<3f', 1.0, 1.0, 1.0))
    machine.define(model+0xca, bytes(2))


def stale_pattern(seed, size):
    generator = random.Random(seed)
    return b''.join(struct.pack('<f', f32(generator.uniform(-3, 3))) for _ in range(size//4))


def compare_authored(machine, snapshot, function, *arguments):
    status = function(snapshot, *arguments)
    diffs = snapshot.same_as(machine)
    return {'status': status, 'differences': diffs, 'match': status == 0 and not diffs}


def run_pose(machine, model, frame, prior_frame, prior_action, state, authored=None):
    """Pose builder on the shared bone buffer 0x06fce398."""
    args_block = machine.allocate(0x40, defined=True)
    machine.define(args_block, struct.pack('<5f', 0.0, 0.0, 0.0, 0.0, 0.0))
    if state == 'stale':
        machine.put(BONES, stale_pattern(1, 200*0x30))
        machine.put(QUATERNIONS, stale_pattern(2, 0x075a9ee8-QUATERNIONS))
    else:
        machine.put(BONES, bytes(200*0x30))
        machine.put(QUATERNIONS, bytes(0x075a9ee8-QUATERNIONS))
    machine.put(ROOT_MATRIX, bytes(0x30))
    bones = struct.unpack('<h', machine.read(model+0x22, 2))[0]
    machine.begin(BUILDER, [('bones', BONES, 0x30*bones), ('quaternions', QUATERNIONS, 16*bones),
                            ('root', ROOT_MATRIX, 0x30)])
    arguments = [BONES, bits(frame), bits(prior_frame), prior_action, args_block, args_block+0xc, 0, 0]
    snapshot = Snapshot(machine) if authored else None
    result = machine.call(BUILDER, arguments, model, 0x20)
    result['bones'] = machine.read(BONES, 200*0x30)
    if authored:
        # The builder writes the clamped prior action back into its own argument slot;
        # that stack slot is outside both compared images.
        result['authored'] = compare_authored(machine, snapshot, authored.run_pose, model, arguments)
        result['match'] = result['match'] and result['authored']['match']
    return result


def run_transform(machine, model, foreign_state, foreign_spans, authored=None):
    """CPU skinning 0x012b5bde with the default buffers; foreign spans zero or patterned."""
    block = machine.allocate(0x60, defined=True)
    machine.define(block, struct.pack('<3f', -1.0, -2.0, -3.0))
    machine.define(block+0x10, struct.pack('<3f', 4.0, 5.0, 6.0))
    for index, (base, size) in enumerate(foreign_spans):
        machine.put(base, stale_pattern(100+index, size) if foreign_state == 'pattern' else bytes(size))
    bones = struct.unpack('<h', machine.read(model+0x22, 2))[0]
    expected = [('bones', BONES, 0x30*bones)]
    for i, mesh in enumerate(mesh_records(machine, model)):
        expected += [('vertices', VERTICES+i*VERTEX_STRIDE, 12*mesh['nv']),
                     ('normals', NORMALS+i*VERTEX_STRIDE, 12*mesh['nn']),
                     ('lights', LIGHTS+i*LIGHT_STRIDE, 4*mesh['nn']),
                     ('secondary', SECONDARY+i*LIGHT_STRIDE, 4*mesh['nn'])]
    machine.begin(TRANSFORM, expected)
    arguments = [BONES, VERTICES, NORMALS, LIGHTS, block, block+0x10, block+0x20, 1, bits(0.0), bits(0.4),
                 bits(0.4), bits(0.4)]
    snapshot = Snapshot(machine) if authored else None
    result = machine.call(TRANSFORM, arguments, model, 0x30)
    if authored:
        result['authored'] = compare_authored(machine, snapshot, authored.run_transform, model, arguments)
        result['match'] = result['match'] and result['authored']['match']
    return result


def run_mesh_draw(machine, model, mesh, flags=0, select=-1):
    record = mesh_records(machine, model)[mesh]
    expected = [('vertices', VERTICES+mesh*VERTEX_STRIDE, 12*record['nv']),
                ('normals', NORMALS+mesh*VERTEX_STRIDE, 12*record['nn']),
                ('lights', LIGHTS+mesh*LIGHT_STRIDE, 4*record['nn']),
                ('secondary', SECONDARY+mesh*LIGHT_STRIDE, 4*record['nn']),
                ('colours', COLOURS+mesh*VERTEX_STRIDE, 12*record['nn'])]
    count = len(mesh_records(machine, model))
    arena = [('model', model, 0xd0), ('meshes', machine.u32(model+0x28), 0x20*max(count, 1)),
             ('names', machine.u32(model+0x34), 0x20*max(count, 1)), ('textures', machine.u32(model+0x38), 4*max(count, 1)),
             ('types', machine.u32(model+0x3c), 4*max(count, 1)), ('uvs', record['uvs'], 8*record['nt']),
             ('triangles', record['triangles'], 0x24*record['nf'])]
    if record['sub']:
        arena.append(('sub', record['sub'], 5))
    machine.begin(MESH_DRAW, expected, [a for a in arena if a[2] > 0])
    arguments = [mesh, flags, VERTICES, NORMALS, LIGHTS, bits(1.0), select & 0xffffffff, bits(1.0), bits(0.0),
                 bits(0.0), 0xffffffff]
    return machine.call(MESH_DRAW, arguments, model, 0x2c)


def mesh_records(machine, model):
    count = struct.unpack('<h', machine.read(model+0x24, 2))[0]
    array = machine.u32(model+0x28)
    out = []
    for i in range(max(count, 0)):
        record = machine.read(array+0x20*i, 0x20)
        nv, nn, nt, nf = struct.unpack_from('<4h', record, 4)
        out.append({'nv': nv, 'nn': nn, 'nt': nt, 'nf': nf, 'vertices': struct.unpack_from('<I', record, 0xc)[0],
                    'normals': struct.unpack_from('<I', record, 0x10)[0],
                    'uvs': struct.unpack_from('<I', record, 0x14)[0],
                    'triangles': struct.unpack_from('<I', record, 0x18)[0],
                    'sub': struct.unpack_from('<I', record, 0x1c)[0]})
    return out


def outputs(machine, meshes):
    """Transform outputs the draw consumes: vertices, normals, lights, secondary lights."""
    data = {}
    for i, mesh in enumerate(meshes):
        data[i] = (machine.read(VERTICES+i*VERTEX_STRIDE, 12*mesh['nv']),
                   machine.read(NORMALS+i*VERTEX_STRIDE, 12*mesh['nn']),
                   machine.read(LIGHTS+i*LIGHT_STRIDE, 4*mesh['nn']),
                   machine.read(SECONDARY+i*LIGHT_STRIDE, 4*mesh['nn']))
    return data


def differing_entries(a, b, stride):
    return [i for i in range(len(a)//stride) if a[i*stride:(i+1)*stride] != b[i*stride:(i+1)*stride]]


# --------------------------------------------------------------------------
# Authored C on the same memory images.

STATE_WINDOW = (0x06f00000, 0x089c2120+50*VERTEX_STRIDE)   # bone buffer .. colour table, incl. foreign spans


class Image(ctypes.Structure):
    _fields_ = [('bytes', ctypes.c_void_p), ('base', ctypes.c_uint32), ('size', ctypes.c_uint32)]


class Memory(ctypes.Structure):
    _fields_ = [('regions', ctypes.POINTER(Image)), ('count', ctypes.c_uint32)]


ALLOCATE = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32)
RELEASE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32)
NAME_FLAGS = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8))


class Hooks(ctypes.Structure):
    _fields_ = [('allocate', ALLOCATE), ('release', RELEASE), ('name_flags', NAME_FLAGS), ('context', ctypes.c_void_p)]


GLOBAL_PAGES = (0x01cf1000, 0x01d1d000, 0x0b437000)   # bone scale/override/world, scene state, bounds mode


class Snapshot:
    """Copies of the heap arena (up to its cursor), the third-section state window and the global pages."""

    def __init__(self, machine, margin=0x100000):
        self.arena_size = min(align(machine.cursor-ARENA+margin, 0x1000), ARENA_BYTES)
        low, high = STATE_WINDOW
        self.spans = [(ARENA, self.arena_size), (low, high-low)]+[(page, 0x1000) for page in GLOBAL_PAGES]
        self.buffers = [(ctypes.c_ubyte*size).from_buffer_copy(machine.read(base, size)) for base, size in self.spans]
        self.arena = self.buffers[0]
        self.cursor = machine.cursor
        self.allocations = len(machine.allocations)

    def memory(self):
        images = (Image*len(self.spans))(*[Image(ctypes.addressof(b), base, size)
                                           for (base, size), b in zip(self.spans, self.buffers)])
        self.images = images
        return Memory(images, len(self.spans))

    def same_as(self, machine):
        """First differing address per span after the client ran on the same input."""
        diffs = {}
        for (base, size), buffer in zip(self.spans, self.buffers):
            observed = machine.read(base, size)
            mine = bytes(buffer)
            if mine != observed:
                first = next(i for i in range(size) if mine[i] != observed[i])
                diffs[hex(base)] = hex(base+first)
        return diffs


class Authored:
    def __init__(self, library):
        handle = ctypes.CDLL(str(library))
        self.read = handle.mu_model_read_layout
        self.read.argtypes = [ctypes.POINTER(Memory), ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_int32),
                              ctypes.POINTER(Hooks), ctypes.c_void_p]
        self.read.restype = ctypes.c_int
        self.pose = handle.mu_pose_build
        self.pose.argtypes = [ctypes.POINTER(Memory), ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
        self.pose.restype = ctypes.c_int
        self.transform = handle.mu_model_transform
        self.transform.argtypes = [ctypes.POINTER(Memory), ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
        self.transform.restype = ctypes.c_int
        environment = handle.mu_record_math_environment_supported
        environment.restype = ctypes.c_int
        if environment() != 1:
            raise ValueError('Host requires binary32/binary64 storage and RNE environment')

    def run_reader(self, snapshot, model, stream, names, flags):
        """names/flags: the parser results the client produced, in mesh order."""
        cursor = [snapshot.cursor]
        index = [snapshot.allocations]
        released = []

        def allocate(context, request):
            if request > 0xffffffe0:
                return 0
            address = align(cursor[0]+16)
            size = max(request, 1)
            cursor[0] = address+size
            index[0] += 1
            poison = bytes(((index[0]*29+offset*7+0x5a) & 0xff) | 0x80 for offset in range(min(size, 4096)))
            payload = (poison*(size//len(poison)+1))[:size]
            ctypes.memmove(ctypes.addressof(snapshot.arena)+address-ARENA, payload, size)
            return address
        calls = [0]

        def name_flags(context, name, out):
            k = calls[0]
            calls[0] += 1
            for b in range(5):
                out[b] = flags[k][b] if k < len(flags) else 0
            return names[k] if k < len(names) else 0
        hooks = Hooks(ALLOCATE(allocate), RELEASE(lambda c, b: released.append(b)), NAME_FLAGS(name_flags), None)
        offset = ctypes.c_int32(0)
        globals_ = (ctypes.c_uint32*3)(BOX_COUNTS, BOX_MIN, BOX_MAX)
        status = self.read(ctypes.byref(snapshot.memory()), model, stream, ctypes.byref(offset), ctypes.byref(hooks),
                           ctypes.addressof(globals_))
        return {'status': status, 'offset': offset.value, 'released': released, 'name_calls': calls[0]}

    def run_pose(self, snapshot, model, arguments):
        args = (ctypes.c_uint32*8)(*[a & 0xffffffff for a in arguments])
        globals_ = (ctypes.c_uint32*2)(QUATERNIONS, ROOT_MATRIX)
        return self.pose(ctypes.byref(snapshot.memory()), model, ctypes.addressof(args), ctypes.addressof(globals_))

    def run_transform(self, snapshot, model, arguments):
        args = (ctypes.c_uint32*12)(*[a & 0xffffffff for a in arguments])
        globals_ = (ctypes.c_uint32*5)(BONE_SCALE, LIGHT_OVERRIDE, WORLD, BOUNDS_MODE, SECONDARY)
        return self.transform(ctypes.byref(snapshot.memory()), model, ctypes.addressof(args), ctypes.addressof(globals_))


# --------------------------------------------------------------------------
# Per-file analysis.


def define_texture_indices(machine, model, value=0):
    """Model +0x38: per-mesh texture index table, allocated but left unwritten by the
    reader; the texture loader fills it later. Declared caller state here."""
    count = struct.unpack('<h', machine.read(model+0x24, 2))[0]
    table = machine.u32(model+0x38)
    machine.define(table, struct.pack('<%di' % max(count, 1), *([value]*max(count, 1))))


def check_layout(machine, model, payload, layout):
    """Independent check of the reader's records against the Python layout walk."""
    problems = []
    nm, nb, na = layout['counts']
    counts = struct.unpack('<hhh', machine.read(model+0x22, 6))
    if counts != (nb, nm, na):
        problems.append(('counts', counts))
    stream_raw = lambda o, n: payload[o:o+n]   # noqa: E731
    for i, (mesh, record) in enumerate(zip(layout['meshes'], mesh_records(machine, model))):
        if (record['nv'], record['nn'], record['nt'], record['nf']) != (mesh['nv'], mesh['nn'], mesh['nt'], mesh['nf']):
            problems.append(('mesh-counts', i))
        if machine.read(record['vertices'], 16*mesh['nv']) != stream_raw(mesh['vertices'], 16*mesh['nv']):
            problems.append(('vertices', i))
        if machine.read(record['normals'], 20*mesh['nn']) != stream_raw(mesh['normals'], 20*mesh['nn']):
            problems.append(('normals', i))
        if machine.read(record['uvs'], 8*mesh['nt']) != stream_raw(mesh['uvs'], 8*mesh['nt']):
            problems.append(('uvs', i))
        triangles = machine.read(record['triangles'], 0x24*mesh['nf'])
        expected = b''.join(stream_raw(mesh['polygons']+64*j, 0x24) for j in range(mesh['nf']))
        if triangles != expected:
            problems.append(('triangles', i))
    bones = machine.u32(model+0x2c)
    for i, bone in enumerate(layout['bones']):
        record = machine.read(bones+i*0x8c, 0x8c)
        if record[0x22] != bone['dummy']:
            problems.append(('dummy', i))
        if not bone['dummy'] and (record[:32] != bone['name'] or struct.unpack_from('<h', record, 0x20)[0] != bone['parent']):
            problems.append(('bone', i))
    actions = machine.u32(model+0x30)
    for i, action in enumerate(layout['actions']):
        record = machine.read(actions+16*i, 16)
        if struct.unpack_from('<h', record, 8)[0] != action['keys'] or record[0xa] != action['lock']:
            problems.append(('action', i))
    return problems


def pose_samples(layout, census):
    """(label, action, frame, prior frame, prior action) samples per file."""
    keys = [a['keys'] for a in layout['actions']]
    samples = []
    for action, k in enumerate(keys[:3]):
        if k <= 0:
            continue
        samples += [('first-key', action, 0.0, 0.0, action),
                    ('blend', action, f32(k*0.5+0.25), float(int(k*0.5)), action),
                    ('last-key', action, float(k-1), float(k-1), action)]
    for kind, bone, action, key, *_ in [c for c in census if c[0].startswith('nonfinite')]:
        k = keys[action]
        samples += [(f'nonfinite-key-{key}', action, float(key), float(key), action),
                    (f'into-key-{key}', action, f32(key+0.5) if key+1 < k else f32(key+0.25), float(key), action),
                    (f'from-key-{key}', action, f32(max(key-1, 0)+0.5), float(max(key-1, 0)), action),
                    (f'wrap-after-key-{key}', action, 0.25, float(key), action)]
    return samples


def foreign_bone_spans(census):
    indices = sorted({c[3] for c in census if c[0] in ('vertex-bone', 'normal-bone')})
    return [(BONES+(index*0x30), 0x30) for index in indices], indices


def nonfinite_slots(bones, count):
    out = []
    for slot in range(count):
        values = struct.unpack_from('<12f', bones, slot*0x30)
        if not all(math.isfinite(v) for v in values):
            out.append(slot)
    return out


def corner_calls(gl):
    """Corner subsequence of a client GL stream: (op, bits...) between glBegin and glEnd."""
    out, inside = [], False
    for call in gl:
        if call[0] == 'glBegin':
            inside = True
        elif call[0] == 'glEnd':
            inside = False
        elif inside:
            if call[0] == 'glTexCoord2f':
                out.append(('t', call[1], call[2]))
            elif call[0] == 'glColor3fv':
                out.append(('c3', call[2], call[3], call[4]))
            elif call[0] == 'glColor4f':
                out.append(('c4',)+tuple(call[1:5]))
            elif call[0] == 'glVertex3fv':
                out.append(('v', call[2], call[3], call[4]))
    return out


def native_corners(tool, path, scratch):
    """mu-render corners stream as one corner list per glBegin/glEnd block, in the same (op, bits...) form.

    The tool writes the literal GL stream of the mesh-draw port (op, four words per call); the
    blocks follow the body's mesh order, one per mesh that reaches glBegin."""
    import subprocess
    output = Path(scratch)/'corners.bin'
    run = subprocess.run([str(tool), 'corners', str(path), '--out', str(output)], capture_output=True, text=True)
    if run.returncode:
        return None, run.stderr.strip()
    data = output.read_bytes()
    names = {3: ('t', 2), 5: ('c3', 3), 6: ('c4', 4), 7: ('v', 3)}  # glTexCoord2f, glColor3fv, glColor4f, glVertex3fv
    blocks, inside = [], False
    for offset in range(0, len(data), 20):
        op, a, b, c, d = struct.unpack_from('<5I', data, offset)
        if op == 1:
            blocks.append([])
            inside = True
        elif op == 2:
            inside = False
        elif inside and op in names:
            name, width = names[op]
            blocks[-1].append((name,)+(a, b, c, d)[:width])
    return blocks, json.loads(run.stdout)


def analyse(machine, authored, relative, raw, native=None, scratch=None):
    payload = tracks_payload(raw)
    layout = client_layout(payload)
    client_layout_cache[relative] = layout
    census = edge_census(payload, layout)
    report = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest(), 'counts': layout['counts'],
              'census': [list(c) for c in census], 'affected_bones': affected_bones(layout)}
    machine.reset()
    reader = machine.run_reader(payload, raw[3], authored)
    report['reader'] = {k: reader[k] for k in ('match', 'checks', 'error', 'stopped', 'foreign', 'undefined_reads',
                                                'names') if k in reader}
    report['reader']['authored'] = reader.get('authored')
    report['reader']['offset_is_layout_end'] = reader['offset'] == layout['end']
    report['reader']['trailing_bytes_ignored'] = len(payload)-reader['offset']
    report['reader']['allocations'] = len(reader['allocations'])
    report['reader']['layout_problems'] = check_layout(machine, reader['model'], payload, layout)
    model = reader['model']
    set_model_fields(machine, model)
    define_texture_indices(machine, model)
    nb = max(layout['counts'][1], 0)
    meshes = mesh_records(machine, model)
    spans, indices = foreign_bone_spans(census)
    report['foreign_bone_indices'] = indices
    report['foreign_bone_addresses'] = [hex(base) for base, _ in spans]
    poses = []
    for label, action, frame, prior, prior_action in pose_samples(layout, census):
        machine.define(model+0xa8, struct.pack('<H', action))
        entry = {'label': label, 'action': action, 'frame': frame, 'prior_frame': prior}
        results = {}
        for state in ('zero', 'stale'):
            result = run_pose(machine, model, frame, prior, prior_action, state, authored)
            results[state] = result
            entry[f'{state}_match'] = result['match']
            entry[f'{state}_prior_slot_reads'] = sorted({o//0x30 for o in result['prior_reads'].get('bones', [])})
            entry[f'{state}_nonfinite_slots'] = nonfinite_slots(result['bones'], nb)
            entry[f'{state}_foreign'] = result['foreign']
            if not result['match']:
                entry[f'{state}_detail'] = {k: result.get(k) for k in ('checks', 'error', 'stopped', 'authored')}
            if meshes:
                transforms = {}
                for foreign in ('zero', 'pattern'):
                    run_pose(machine, model, frame, prior, prior_action, state)   # same pose before each variant
                    t = run_transform(machine, model, foreign, spans, authored)
                    transforms[foreign] = (t, outputs(machine, meshes))
                    entry[f'{state}_transform_{foreign}_match'] = t['match']
                    if not t['match']:
                        entry[f'{state}_transform_{foreign}_detail'] = {k: t.get(k) for k in (
                            'checks', 'error', 'stopped', 'authored', 'undefined_reads')}
                    entry[f'{state}_transform_foreign_reads'] = sorted({f['address'] for f in t['foreign']
                                                                        if not f['write']})
                    entry[f'{state}_transform_foreign_writes'] = sorted({f['address'] for f in t['foreign'] if f['write']})
                results[state, 'outputs'] = transforms['zero'][1]
                diff, values = {}, {}
                for i in range(len(meshes)):
                    a, b = transforms['zero'][1][i], transforms['pattern'][1][i]
                    d = {name: differing_entries(x, y, size) for name, x, y, size in
                         zip(('vertices', 'normals', 'lights', 'secondary'), a, b, (12, 12, 4, 4))}
                    d = {k: v for k, v in d.items() if v}
                    if d:
                        diff[i] = d
                        values[i] = {name: {n: [x[n*size:(n+1)*size].hex(), y[n*size:(n+1)*size].hex()]
                                            for n in d[name]}
                                     for name, x, y, size in zip(('vertices', 'normals', 'lights', 'secondary'), a, b,
                                                                 (12, 12, 4, 4)) if name in d}
                entry[f'{state}_foreign_dependent_outputs'] = diff
                entry[f'{state}_foreign_dependent_values'] = values
        entry['state_dependent_slots'] = differing_entries(results['zero']['bones'][:0x30*nb],
                                                           results['stale']['bones'][:0x30*nb], 0x30)
        if meshes:
            diff = {}
            for i in range(len(meshes)):
                a, b = results['zero', 'outputs'][i], results['stale', 'outputs'][i]
                d = {name: differing_entries(x, y, size) for name, x, y, size in
                     zip(('vertices', 'normals', 'lights', 'secondary'), a, b, (12, 12, 4, 4))}
                d = {k: v for k, v in d.items() if v}
                if d:
                    diff[i] = d
            entry['state_dependent_outputs'] = diff
        poses.append(entry)
    report['poses'] = poses
    # Mesh draws after a zero-state pose of the first sample and zero foreign memory.
    draws = []
    if meshes and poses:
        first = pose_samples(layout, census)[0]
        heap_reset = []
        client_corners, client_begun = {}, set()
        machine.define(model+0xa8, struct.pack('<H', first[1]))
        for lighting in (1, 0):
            machine.define(model+0x50, bytes([lighting]))
            run_pose(machine, model, first[2], first[3], first[4], 'zero')
            run_transform(machine, model, 'zero', spans)
            for i in range(len(meshes)):
                streams = {}
                record = {'mesh': i, 'lighting': lighting}
                for variant in ('zero', 'stale'):
                    if variant == 'stale':
                        machine.put(COLOURS+i*VERTEX_STRIDE, stale_pattern(7, VERTEX_STRIDE))
                        machine.put(TEXCOORD_TABLE, stale_pattern(8, 15001*8))
                        for f in streams['zero'][1]['foreign']:
                            if not f['write']:
                                machine.put(int(f['address'], 16), stale_pattern(9, f['size']))
                                if ARENA <= int(f['address'], 16) < ARENA+ARENA_BYTES:
                                    heap_reset.append((int(f['address'], 16), f['size']))
                        for u in streams['zero'][1]['undefined_reads']:
                            for address, size in u['spans']:
                                machine.define(address, stale_pattern(10, size))
                    else:
                        machine.put(COLOURS+i*VERTEX_STRIDE, bytes(VERTEX_STRIDE))
                        machine.put(TEXCOORD_TABLE, bytes(15001*8))
                        for address, size in heap_reset:    # undo earlier stale heap bytes
                            machine.uc.mem_write(address, bytes(size))
                    d = run_mesh_draw(machine, model, i)
                    streams[variant] = (d['gl'], d)
                    record[f'{variant}_match'] = d['match']
                    if not d['match']:
                        record[f'{variant}_detail'] = {k: d.get(k) for k in ('checks', 'error', 'stopped')}
                zero, stale = streams['zero'], streams['stale']
                if lighting == 1:
                    client_corners[i] = corner_calls(zero[0])
                    if any(c[0] == 'glBegin' for c in zero[0]):
                        client_begun.add(i)
                record['gl_calls'] = len(zero[0])
                record['triangles_begun'] = sum(1 for c in zero[0] if c[0] == 'glBegin')
                record['vertex_calls'] = sum(1 for c in zero[0] if c[0] == 'glVertex3fv')
                record['foreign'] = [{k: f[k] for k in ('address', 'size', 'pc', 'value', 'inside')}
                                     for f in zero[1]['foreign'] if not f['write']]
                record['undefined_reads'] = zero[1]['undefined_reads']
                record['state_dependent_calls'] = [
                    {'index': n, 'zero': list(a), 'stale': list(b)} for n, (a, b) in enumerate(zip(zero[0], stale[0]))
                    if a != b][:12]
                record['state_dependent_call_count'] = sum(1 for a, b in zip(zero[0], stale[0]) if a != b)
                record['stream_lengths_equal'] = len(zero[0]) == len(stale[0])
                draws.append(record)
        machine.define(model+0x50, bytes([1]))
        if native is not None and first[1:] == (0, 0.0, 0.0, 0):
            # mu-render corners runs the mesh draws through the body 0x012bb35a, which skips a mesh
            # whose +0x1c sub-object has byte 1 set and passes select = mesh when byte 0 is set
            # (texture names with "_R"). Give the client the same arguments for those meshes,
            # from the same zero state (lighting on, first pose, zero tables).
            records = mesh_records(machine, model)
            subs = {i: machine.read(r['sub'], 5) for i, r in enumerate(records) if r['sub']}
            if any(sub[1] or sub[0] for sub in subs.values()):
                run_pose(machine, model, first[2], first[3], first[4], 'zero')
                run_transform(machine, model, 'zero', spans)
                machine.put(TEXCOORD_TABLE, bytes(15001*8))
                for address, size in heap_reset:
                    machine.uc.mem_write(address, bytes(size))
                for i, sub in subs.items():
                    if sub[1]:
                        client_begun.discard(i)
                        client_corners.pop(i, None)
                    elif sub[0]:
                        machine.put(COLOURS+i*VERTEX_STRIDE, bytes(VERTEX_STRIDE))
                        d = run_mesh_draw(machine, model, i, select=i)
                        client_corners[i] = corner_calls(d['gl'])
                        if any(c[0] == 'glBegin' for c in d['gl']):
                            client_begun.add(i)
                        else:
                            client_begun.discard(i)
                report['body_select_meshes'] = sorted(i for i, sub in subs.items() if sub[0] and not sub[1])
            # The viewer's default state (action 0, frame 0) with the client's zero state.
            observed, info = native_corners(native, Path(native_root)/relative, scratch)
            if observed is None:
                report['native'] = {'match': False, 'error': info}
            else:
                # The client draws are run per mesh; meshes without glBegin have no block.
                drawn = sorted(client_begun)
                observed = dict(zip(drawn, observed)) if len(observed) == len(drawn) else \
                    {('block', n): v for n, v in enumerate(observed)}
                mismatched = [i for i in drawn if client_corners[i] != observed.get(i, [])]
                report['native'] = {'match': not mismatched and set(observed) <= set(drawn),
                                    'meshes': len(client_corners), 'corner_records': sum(len(v) for v in client_corners.values()),
                                    'mismatched_meshes': mismatched, 'tool': info}
                if mismatched:
                    i = mismatched[0]
                    a, b = client_corners[i], observed.get(i, [])
                    first_diff = next((n for n, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
                    report['native']['first_difference'] = {'mesh': i, 'index': first_diff,
                                                            'client': a[first_diff:first_diff+3],
                                                            'native': b[first_diff:first_diff+3]}
    report['draws'] = draws
    return report


native_root = None


def tracks_payload(raw):
    """Decoded v15 payload via the repository's LEA reader (client-linked, PR #32)."""
    sys.path.insert(0, str(ROOT/'model-recovery'))
    import bmd_encrypted
    if raw[:3] != b'BMD' or raw[3] != 15:
        raise ValueError('MODEL-EDGE inputs are BMD v15 files')
    length = struct.unpack_from('<I', raw, 4)[0]
    if length != len(raw)-8 or length % 16:
        raise ValueError('v15 envelope length mismatch')
    return bmd_encrypted.decrypt_lea(raw[8:])


# --------------------------------------------------------------------------
# Reader comparisons beyond the 17 files: synthetic payloads and an installed sample.


def synthetic_payload(generator, label):
    """A decoded-layout payload with raw values the strict reader rejects."""
    def f():
        choice = generator.random()
        if choice < 0.03:
            return struct.pack('<I', generator.choice([0x7fc00000, 0xffff0000, 0x7f800000, 0xff800000, 0x00000001]))
        return struct.pack('<f', f32(generator.uniform(-100, 100)))
    nm, nb, na = generator.randrange(0, 4), generator.randrange(0, 9), generator.randrange(0, 4)
    if label == 'negative-model-counts':
        nm, nb, na = -generator.randrange(1, 5), -1, -2
    out = bytearray(bytes(generator.randrange(32, 127) for _ in range(31))+b'\0')
    out += struct.pack('<hhh', nm, nb, na)
    weird = [-1, -8888, -32768, 32767, nb, nb+7, 199, 200]
    for _ in range(max(nm, 0)):
        nv, nn, nt, nf = (generator.randrange(0, 12) for _ in range(4))
        out += struct.pack('<5h', nv, nn, nt, nf, generator.randrange(-2, 30))
        for _ in range(nv):
            bone = generator.randrange(max(nb, 1)) if generator.random() < 0.85 else generator.choice(weird)
            out += struct.pack('<hh', bone, generator.randrange(-5, 5))+f()+f()+f()
        for _ in range(nn):
            bone = generator.randrange(max(nb, 1)) if generator.random() < 0.85 else generator.choice(weird)
            out += struct.pack('<hh', bone, 0)+f()+f()+f()+struct.pack('<hh', generator.randrange(-3, nv+3), 0)
        for _ in range(nt):
            out += f()+f()
        for _ in range(nf):
            block = bytearray(generator.randrange(256) for _ in range(64))
            block[0] = generator.choice([3, 3, 4, 0, 2, 7, 0x83])
            out += bytes(block)
        names = [b'skin.jpg', b'body_R.jpg', b'hair_H.tga', b'eye_SN.ozj', b'x_RHSN.jpg', b'fire_sq.jpg', b'a_RX.jpg',
                 b'mu_rgb_lights.jpg', b'chrome01.jpg', b'a b c']
        out += generator.choice(names).ljust(32, b'\0')
    keys = []
    for _ in range(max(na, 0)):
        k = generator.randrange(0, 5)
        lock = generator.choice([0, 0, 1, 2, 0x80])
        keys.append(k)
        out += struct.pack('<hB', k, lock)
        if lock:
            out += b''.join(f()+f()+f() for _ in range(k))
    for index in range(max(nb, 0)):
        flag = generator.choice([0, 0, 0, 1, 0x80, 0xff])
        out += bytes([flag])
        if not flag:
            parent = generator.randrange(-1, index) if index and generator.random() < 0.8 else generator.choice(
                [-1, -2, nb, index+1, 0x7fff])
            out += bytes(generator.randrange(32, 127) for _ in range(8)).ljust(32, b'\0')+struct.pack('<h', parent)
            for k in keys:
                out += b''.join(f()+f()+f() for _ in range(k))
                out += b''.join(struct.pack('<3f', *(f32(generator.uniform(-3, 3)) for _ in range(3))) for _ in range(k))
    out += bytes(generator.randrange(256) for _ in range(generator.randrange(0, 40)))   # ignored trailer
    return bytes(out)


def reader_comparison(machine, authored, payload, version, label):
    machine.reset()
    result = machine.run_reader(payload, version, authored)
    layout = client_layout(payload)
    problems = check_layout(machine, result['model'], payload, layout) if result['match'] else ['not reached']
    return {'label': label, 'match': result['match'] and not problems and result['offset'] == layout['end'],
            'foreign': len(result['foreign']), 'names': result['names'], 'problems': problems[:4],
            'authored': result.get('authored'), 'checks': result['checks'], 'stopped': result['stopped']}


def synthetic_readers(machine, authored, count=300):
    generator = random.Random(0x12b3812)
    results = []
    for index in range(count):
        label = 'negative-model-counts' if index % 50 == 7 else 'mutated'
        results.append(reader_comparison(machine, authored, synthetic_payload(generator, label), 15, label))
    return results


def installed_readers(machine, authored, game_root, every):
    sys.path.insert(0, str(ROOT/'model-recovery'))
    import bmd_encrypted
    results, index = [], 0
    for path in sorted(Path(game_root).rglob('*')):
        if path.suffix.lower() != '.bmd' or not path.is_file():
            continue
        with path.open('rb') as handle:
            header = handle.read(4)
        if header[:3] != b'BMD' or header[3] not in (12, 14, 15):
            continue
        index += 1
        if index % every:
            continue
        raw = path.read_bytes()
        try:
            bmd_encrypted.parse_model(raw)   # the strict reader accepts it
        except Exception:
            continue
        body = raw[8:]
        payload = {12: bmd_encrypted.decrypt_map, 14: bmd_encrypted.decrypt_modulus,
                   15: bmd_encrypted.decrypt_lea}[raw[3]](body)
        results.append(reader_comparison(machine, authored, payload, raw[3], str(path.relative_to(game_root))))
    return results


# --------------------------------------------------------------------------
# Driver.


def check_pins(text):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    for name, (start, end, digest) in BODIES.items():
        if hashlib.sha256(text[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
            raise ValueError(f'Pinned {name} body mismatch')
    for address in sorted(CONSTANT_RMW):
        instruction = next(decoder.disasm(text[address-TEXT_BASE:address-TEXT_BASE+16], address))
        operand = instruction.op_str.rsplit(',', 1)[-1].strip()
        if not ((instruction.mnemonic == 'and' and operand == '0') or
                (instruction.mnemonic == 'or' and operand == '0xffffffff')):
            raise ValueError(f'{address:#x} is not a constant read-modify-write')
    if text[SUB_NEW-TEXT_BASE:SUB_NEW-TEXT_BASE+2] != b'\x6a\x05':
        raise ValueError('sub-object allocation site changed')


def summarize(reports):
    summary = {'files': len(reports), 'reader_matches': 0, 'authored_reader_matches': 0, 'pose_calls': 0,
               'pose_matches': 0, 'transform_calls': 0, 'transform_matches': 0, 'draw_calls': 0, 'draw_matches': 0,
               'geometry_state_dependent_files': [], 'per_file': {}}
    for r in reports:
        reader = r['reader']
        summary['reader_matches'] += int(reader['match'] and not reader['layout_problems'] and
                                         reader['offset_is_layout_end'])
        summary['authored_reader_matches'] += int(bool(reader['authored'] and reader['authored']['match']))
        state_slots, prior_slots, nonfinite, state_outputs, foreign_outputs = set(), set(), set(), {}, {}
        for p in r['poses']:
            for state in ('zero', 'stale'):
                summary['pose_calls'] += 1
                summary['pose_matches'] += int(p[f'{state}_match'])
                prior_slots.update(p[f'{state}_prior_slot_reads'])
                nonfinite.update(p[f'{state}_nonfinite_slots'])
                for foreign in ('zero', 'pattern'):
                    key = f'{state}_transform_{foreign}_match'
                    if key in p:
                        summary['transform_calls'] += 1
                        summary['transform_matches'] += int(p[key])
                for mesh, d in p.get(f'{state}_foreign_dependent_outputs', {}).items():
                    for name, entries in d.items():
                        foreign_outputs.setdefault(f'{mesh}:{name}', set()).update(entries)
            state_slots.update(p['state_dependent_slots'])
            for mesh, d in p.get('state_dependent_outputs', {}).items():
                for name, entries in d.items():
                    state_outputs.setdefault(f'{mesh}:{name}', set()).update(entries)
        for d in r['draws']:
            summary['draw_calls'] += 2
            summary['draw_matches'] += int(d['zero_match'])+int(d['stale_match'])
        if state_outputs:
            summary['geometry_state_dependent_files'].append(r['path'])
        summary['per_file'][r['path']] = {
            'counts': r['counts'], 'census_kinds': sorted({c[0] for c in r['census']}),
            'affected_bones': r['affected_bones'], 'pose_state_dependent_slots': sorted(state_slots),
            'pose_prior_slot_reads': sorted(prior_slots), 'nonfinite_slots': sorted(nonfinite),
            'transform_state_dependent_outputs': {k: sorted(v) for k, v in state_outputs.items()},
            'transform_foreign_dependent_outputs': {k: sorted(v) for k, v in foreign_outputs.items()},
            'reader_foreign': r['reader']['foreign'],
            'draw_foreign': sorted({(f['address'], f['inside']) for d in r['draws'] for f in d['foreign']}),
            'draw_outside_block_reads': sorted({(u['pc'], u['first']) for d in r['draws'] for u in d['undefined_reads']
                                                if not u['inside_block']}),
            'draw_state_dependent_calls': sum(d['state_dependent_call_count'] for d in r['draws']),
            'vertex_calls': sum(d['vertex_calls'] for d in r['draws'] if d['lighting'] == 1)}
    return summary


def expectations(summary, reports):
    """Exit status: every execution matched, and the observed dependences on unknown
    state are exactly those the census predicts from the client's unchecked indices."""
    failures = []
    if summary['reader_matches'] != summary['files'] or summary['authored_reader_matches'] != summary['files']:
        failures.append('reader')
    for key in ('pose', 'transform', 'draw'):
        if summary[f'{key}_matches'] != summary[f'{key}_calls']:
            failures.append(key)
    for r in reports:
        f = summary['per_file'][r['path']]
        census = [tuple(c) for c in r['census']]
        dummies = [i for i, bone in enumerate(client_layout_cache[r['path']]['bones']) if bone['dummy']]
        expected_slots = sorted(set(dummies) | set(r['affected_bones'])) if r['affected_bones'] else []
        if f['pose_state_dependent_slots'] != expected_slots and r['affected_bones']:
            failures.append(f"{r['path']}: state-dependent slots {f['pose_state_dependent_slots']}")
        parents = sorted({c[2] for c in census if c[0] == 'dummy-parent'})
        if f['pose_prior_slot_reads'] != parents:
            failures.append(f"{r['path']}: prior slot reads {f['pose_prior_slot_reads']} != {parents}")
        if f['transform_state_dependent_outputs']:
            failures.append(f"{r['path']}: geometry depends on prior bone slots")
        predicted = {}
        for c in census:
            if c[0] in ('vertex-bone', 'normal-bone'):
                predicted.setdefault(f"{c[1]}:{'vertices' if c[0] == 'vertex-bone' else 'normals'}", []).append(c[2])
        observed = {k: v for k, v in f['transform_foreign_dependent_outputs'].items()
                    if k.split(':')[1] in ('vertices', 'normals')}
        if any(not set(v) <= set(predicted.get(k, [])) for k, v in observed.items()):
            failures.append(f"{r['path']}: foreign-dependent outputs {observed} beyond {predicted}")
        nonfinite_bones = sorted({c[1] for c in census if c[0].startswith('nonfinite')})
        if f['nonfinite_slots'] != nonfinite_bones:
            failures.append(f"{r['path']}: non-finite slots {f['nonfinite_slots']}")
        corner_reads = [c for c in census if c[0] in ('normal-index', 'uv-index')]
        foreign_draw = [x for x in f['draw_foreign']]
        if bool(corner_reads) != bool(foreign_draw) or (corner_reads and len(foreign_draw) != len(corner_reads)+1):
            # +1: a texcoord is two scalar reads (u at +0, v at +4).
            failures.append(f"{r['path']}: draw foreign reads {foreign_draw}")
    return failures


client_layout_cache = {}


def validate(text_path, data_path, flag_path, feature_path, library, game_root, native=None, sample=0):
    text = load_pinned(text_path, TEXT_BYTES, tracks.TEXT_SHA256, 'restored text')
    data = load_pinned(data_path, DATA_BYTES, tracks.DATA_SHA256, 'second image section')
    flag = load_pinned(flag_path, 4, tracks.FLAG_SHA256, 'dispatch flag')
    feature = load_pinned(feature_path, 4, tracks.FEATURE_SHA256, 'memcpy feature word')
    check_pins(text)
    if struct.unpack_from('<I', data, HEAPALLOC_SLOT-DATA_BASE)[0] != HEAPALLOC_TARGET or \
            struct.unpack_from('<I', data, HEAPFREE_SLOT-DATA_BASE)[0] != HEAPFREE_TARGET:
        raise ValueError('heap import slot values changed')
    import unicorn
    machine = EdgeMachine(text, data, flag, feature)
    library = Path(library).resolve(strict=True)
    authored = Authored(library)
    reports = []
    global native_root
    native_root = game_root
    import tempfile
    scratch = tempfile.mkdtemp(prefix='model-edge-')
    for relative, digest in EDGE_FILES.items():
        raw = (Path(game_root)/relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f'{relative}: installed file differs from the pinned identity')
        reports.append(analyse(machine, authored, relative, raw, native, scratch))
    summary = summarize(reports)
    failures = expectations(summary, reports)
    synthetic = synthetic_readers(machine, authored)
    summary['synthetic_readers'] = {'cases': len(synthetic), 'matches': sum(r['match'] for r in synthetic),
                                    'with_foreign_access': sum(1 for r in synthetic if r['foreign']),
                                    'sub_objects': sum(sum(1 for n in r['names'] if n) for r in synthetic)}
    failures += [f"synthetic reader {r['label']}: {r}" for r in synthetic if not r['match']][:5]
    if sample:
        installed = installed_readers(machine, authored, game_root, sample)
        summary['installed_readers'] = {'every': sample, 'cases': len(installed),
                                        'matches': sum(r['match'] for r in installed),
                                        'sub_objects': sum(sum(1 for n in r['names'] if n) for r in installed)}
        failures += [f"installed reader {r['label']}: {r}" for r in installed if not r['match']][:5]
    if native is not None:
        compared = [r for r in reports if 'native' in r]
        summary['native_corner_streams'] = {'files': len(compared), 'matches': sum(r['native']['match'] for r in compared),
                                            'corner_records': sum(r['native'].get('corner_records', 0) for r in compared)}
        failures += [f"{r['path']}: native corner stream {r['native']}" for r in compared if not r['native']['match']]
    return {'text_sha256': tracks.TEXT_SHA256, 'data_sha256': tracks.DATA_SHA256,
            'bodies': {name: {'start': hex(s), 'end_exclusive': hex(e), 'sha256': d} for name, (s, e, d) in BODIES.items()},
            'unicorn': unicorn.__version__, 'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
            'summary': summary, 'failures': failures, 'files': reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True, help='math-capture cpu-features.bin')
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec' /
                        ('libmodelreader.dylib' if sys.platform == 'darwin' else 'libmodelreader.so'))
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--native', type=Path, help='native/build/mu-render: compare its corner streams')
    parser.add_argument('--sample', type=int, default=0,
                        help='also compare the reader on every Nth installed v12/v14/v15 model the strict reader accepts')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.data, args.flag, args.feature, args.library, args.game_root, args.native,
                          args.sample)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    print(json.dumps({k: v for k, v in result['summary'].items() if k != 'per_file'}, indent=1))
    print('failures:', result['failures'])
    return int(bool(result['failures']))


if __name__ == '__main__':
    sys.exit(main())
