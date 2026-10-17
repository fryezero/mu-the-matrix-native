#!/usr/bin/env python3
"""Execute the client's mesh draw and body under Unicorn and compare GL streams.

CLIENT-MESHDRAW-EXEC-001. The actual mesh draw 0x012b8d1d (ret 0x2c) and body
0x012bb35a (ret 0x2c) run over the pinned restored text, the verified second
image section, the captured trig dispatch flag and math feature word, with
every client routine they reach: the GL state wrappers 0x0184a6b7..0x0184acf6,
the vector accessors, the sub-object flag getters, the matrix push/pop
wrappers, the colour scale/assign helpers, and the client sin/cos/pow through
the CRT. The OPENGL32 import slots point at a stub page; each call is recorded
with its stdcall arguments (pointer arguments of glColor3fv/glVertex3fv are
read at call time) and returns. Nothing else is stubbed except the two bitmap
map lookups 0x00c97c2d and 0x00ebbec8 (std::map searches in the texture
manager), which return declared bitmap records.

Inputs come from mesh-draw case files (native/core/mu_meshdraw_case.h), written
by `mu-render corners --case-out` for viewer models or by this script for
mutated cases. Each case is laid out as client memory: the model object and its
mesh records, texture tables and sub-object bytes, the transform outputs at the
default wrapper addresses (vertices 0x078978a0, normals 0x0812cce0, light
0x06fd0918, secondary light 0x075a9ee8, all at the 0x2bf20/0xea60 mesh
strides), the colour table 0x089c2120 and texcoord table 0x072acfd8 (poisoned
with 0xff bytes), and the globals time 0x06fce370, env vector 0x0a381de0, skin
base 0x0b6b53e0 and the GL caches. The recorded stream, the final caches, the
final model colour and the tables each mesh draw wrote at its glBegin are
compared byte for byte with `mu-render replay` / `mu-render corners`.

Modelled (not client code): the bitmap lookups above, the case memory itself,
the initial GL caches, and a TEB whose SEH chain head the routine reads/writes.
Any unmapped access, a write to text or the second section, an unexpected
import call or a wrong stack balance stops a case.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tracks = _load('validate_bone_tracks', ROOT/'scripts/validate_bone_tracks.py')
TEXT_BASE, TEXT_BYTES, DATA_BASE, DATA_BYTES = tracks.TEXT_BASE, tracks.TEXT_BYTES, tracks.DATA_BASE, tracks.DATA_BYTES
FLAG_ADDRESS, FEATURE_ADDRESS = tracks.FLAG_ADDRESS, tracks.FEATURE_ADDRESS

MESH_DRAW, BODY = 0x012b8d1d, 0x012bb35a
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes
    'mesh_draw': (0x012b8d1d, 0x012bb35a, 'd19663bdf961b7a6e0adc64ccfb42c935844b40933bb056aa4bc739a3d611660'),
    'body': (0x012bb35a, 0x012bb69c, '8d5686a756fccab0e405b5de3c4b13a51f65ee577ab64e81c5e1b2da5be910ee'),
    'state_wrappers': (0x0184a699, 0x0184ad4c, 'e8cb568d580fd0f843e1945e168238eb6fd3537e12dbc2745c82e0eb16f46536'),
    'push_pop': (0x012b7e53, 0x012b7e75, 'd947e7048e74d840672941c67c7fab226a9aaf28ba6020419a748fbad582b05c'),
    'accessors': (0x00cfc922, 0x00cfc956, 'c4d7b5227dd926d12a4052e70553726b62eef04e091aa4581be6dc0bba88d345'),
    'sub_flags': (0x012bd7e9, 0x012bd829, 'bc211feac9599a8e4badd69e38329ce8b43fb082fb86026e1ef54c0ac4ac7d5f'),
    'sub_flag0': (0x00d99f0d, 0x00d99f1c, 'c476f28eb4a82f85fe3102246db86847fed98479722b3e89ff836ae68a7fa9bc'),
    'cos': (0x009fa20d, 0x009fa223, '1195ca41a1e5500c9a924a2967cf3c94c2dd089253c79792ca2d21f53b04e9c5'),
    'sin': (0x00968117, 0x0096812d, 'ca2de52b85d6fb0c5dce2c931a2e7fcbdf3d89dd52a0efadce786944f6eca579'),
    'pow': (0x009f4218, 0x009f4245, '824c6111cf4a0365bf8d3deac2184c9e86b40f27c3cd079d91f333d6d124bf36'),
    'color_scale': (0x00cfcd74, 0x00cfcdd5, 'e8493fc9542e933e92c0facffcfe41291521508c06808421d1b95af0fc576313'),
    'vector_scale': (0x00cfcb3c, 0x00cfcb98, '9111dd888697ee650a893d39d0eeb5171c5d24ba5bb7983cb9af75db61bcf597'),
    'assign': (0x00cfc8f2, 0x00cfc922, 'd3d8ded5f994a36632d5ea17d482c8cccc8014343fc5e687ccfa68d411d5fa48'),
    'copy': (0x009fa1cb, 0x009fa20d, 'ce0328578bfedb0568d4b95ccdc43f7d3121add8879eb5e7a7e282eda7ce3805'),
    'destructor': (0x0095eda9, 0x0095edb2, '92c6d64d044b483d570bfd94cb01e9b9eef3d4c792e00f39baf084bd82571f9e'),
}
BITMAP_LOOKUP, BITMAP_BIND_LOOKUP = 0x00c97c2d, 0x00ebbec8
OPENGL32_SLOTS = (0x01a7c64c, 0x01a7c790)
# Import slots the mesh draw path may call (names from client_render_static.py / Wine 8.0 opengl32).
GL_SLOTS = {0x1a7c750: ('glBegin', 1), 0x1a7c760: ('glEnd', 0), 0x1a7c774: ('glTexCoord2f', 2),
            0x1a7c76c: ('glColor3f', 3), 0x1a7c770: ('glColor3fv', 1), 0x1a7c754: ('glColor4f', 4),
            0x1a7c778: ('glVertex3fv', 1), 0x1a7c75c: ('glEnable', 1), 0x1a7c758: ('glDisable', 1),
            0x1a7c748: ('glBlendFunc', 2), 0x1a7c740: ('glDepthMask', 1), 0x1a7c77c: ('glBindTexture', 2),
            0x1a7c718: ('glPushMatrix', 0), 0x1a7c72c: ('glPopMatrix', 0)}
OPS = {'glBegin': 1, 'glEnd': 2, 'glTexCoord2f': 3, 'glColor3f': 4, 'glColor3fv': 5, 'glColor4f': 6,
       'glVertex3fv': 7, 'glEnable': 8, 'glDisable': 9, 'glBlendFunc': 10, 'glDepthMask': 11, 'glBindTexture': 12,
       'glPushMatrix': 13, 'glPopMatrix': 14}
TRIG_RETURNS = {0x9681d2: ('sin', math.sin), 0x9fa238: ('cos', math.cos)}
POW_RETURN = 0x9f4239
BRANCHES = {
    0x12b8d61: 'pre-colour', 0x12b8df5: 'no-triangles-return', 0x12b8e81: 'texture-791a-return',
    0x12b8eab: 'skin-substitution', 0x12b8ecf: 'skin-alt-colour', 0x12b9260: 'texture-76f8',
    0x12b9481: 'texture-override', 0x12b94a3: 'texture-increment', 0x12b94fc: 'type-1-alt-colour',
    0x12b95ba: 'type-2-hidden-return', 0x12b9609: 'sub-uv-select', 0x12b9649: 'uv-offset-on',
    0x12b9665: 'light-mesh-colour', 0x12b96bc: 'secondary-light-pass', 0x12b987c: 'light-pass',
    0x12b9983: 'flag-1-path', 0x12b9ada: 'sub-env-return', 0x12b9ae9: 'mesh-flag-env-return',
    0x12b9b00: 'skin-range-env-return', 0x12b9b05: 'environment-group',
    0x12b9c04: 'table-0x200', 0x12b9ca4: 'table-0x800', 0x12b9de9: 'table-0x1000', 0x12b9f74: 'table-0x4000',
    0x12ba0ff: 'table-0x10000', 0x12ba19e: 'table-0x20000', 0x12ba243: 'table-0x100000', 0x12ba2df: 'table-0x80000',
    0x12ba324: 'table-4', 0x12ba38b: 'table-default', 0x12ba437: 'env-colour-alpha', 0x12ba4e4: 'bright-colour-alpha',
    0x12ba5d0: 'bind-7fcf', 0x12ba630: 'bind-800b', 0x12ba64d: 'bind-800c', 0x12ba66a: 'bind-8005',
    0x12ba685: 'bind-7f1f', 0x12ba6a0: 'bind-7f66', 0x12ba6ad: 'bind-env-texture', 0x12ba6d1: 'highlight-pass',
    0x12ba778: 'textured', 0x12ba7c3: 'zero-src-alpha', 0x12ba7cb: 'zero-src-color', 0x12ba7f0: 'alpha-blend',
    0x12ba7fa: 'blend-off', 0x12ba835: 'bright-return', 0x12ba83a: 'bright-untextured', 0x12ba866: 'no-state',
    0x12ba886: 'cull-depth-mask', 0x12ba940: 'corner-mode-2', 0x12ba9bb: 'corner-light-colour',
    0x12baa79: 'corner-mode-4', 0x12bab46: 'corner-mode-80000', 0x12bac1d: 'corner-mode-1000',
    0x12bacf4: 'corner-mode-8000', 0x12baee0: 'vertex-0x20', 0x12bb09f: 'vertex-0x400', 0x12bb1ff: 'vertex-0x200000-skip',
    0x12bb18b: 'vertex-0x200000', 0x12bb256: 'post-type-1-restore', 0x12bb304: 'post-skin-restore',
    0x12bb3cc: 'body-sub', 0x12bb46a: 'body-outline-1', 0x12bb559: 'body-outline-2',
}
LIGHT_PASS, TABLE_LOOP, BEGIN_SITE = 0x12b968c, 0x12b9bb3, 0x12ba891
TEXEL_READ = 0x12bad8a   # movzx eax, byte [eax+ecx]: mode 0x8000 texel of the override bitmap
FAULT_OP = 0x102         # stream record: the routine stopped where it reads outside memory

MODEL, MESHES, ARENA, BITMAPS = 0x20000000, 0x20001000, 0x20010000, 0x30000000
VERTICES, NORMALS, LIGHTS = 0x078978a0, 0x0812cce0, 0x06fd0918
SECONDARY, COLOURS, TEXCOORDS = 0x075a9ee8, 0x089c2120, 0x072acfd8
VERTEX_STRIDE, LIGHT_STRIDE = 0x2bf20, 0xea60
MAX_MESHES, MAX_ENTRIES = 50, 15000   # mesh slots between the transform buffers; 0x2bf20 / 12
TIME, ENV_VECTOR, SKIN_BASE = 0x06fce370, 0x0a381de0, 0x0b6b53e0
CACHE = {'depth_test': 0x0bdc597e, 'cull': 0x0bdc597f, 'depth_mask': 0x0bdc5980, 'alpha_test': 0x0bdc58b5,
         'texture': 0x0bdc597d, 'fog': 0x0bdc597c}
BLEND_CACHE, BIND_CACHE = 0x0bdc58c4, 0x01cf1620
STACK, STACK_BYTES, SENTINEL = 0x34000000, 0x40000, 0x35000000
TEB, GDT = 0x32000000, 0x32001000
STUBS = 0x7a800000
FPCW, MXCSR = 0x027f, 0x1f80


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def load_pinned(path, size, digest, label):
    return tracks.load_pinned(path, size, digest, label)


# --------------------------------------------------------------------------
# Case files (mirror of native/core/mu_meshdraw_case.c).


class Reader:
    def __init__(self, data):
        self.data, self.at = data, 0

    def take(self, n):
        if self.at+n > len(self.data):
            raise ValueError('truncated case')
        out = self.data[self.at:self.at+n]
        self.at += n
        return out

    def u(self, fmt):
        size = struct.calcsize('<'+fmt)
        return struct.unpack('<'+fmt, self.take(size))


def read_case(data):
    r = Reader(data)
    if r.take(4) != b'MUMC' or r.u('I')[0] != 1:
        raise ValueError('not a version-1 mesh-draw case')
    c = {}
    t, e0, e1, e2, skin = r.u('ffffi')
    c['globals'] = {'time': t, 'env': (e0, e1, e2), 'skin_base': skin}
    dt, cull, dm, at, tex, fog, blend, bound = r.u('BBBBBBii')
    c['cache'] = dict(depth_test=dt, cull=cull, depth_mask=dm, alpha_test=at, texture=tex, fog=fog, blend=blend,
                      bound=bound)
    m = {}
    m['mesh_count'], = r.u('h')
    m['hide_typed'], = r.u('i')
    m['alt'] = r.u('fff')
    m['lighting'], = r.u('B')
    m['color'] = r.u('fff')
    m['origin'] = r.u('fff')
    m['light_mesh'], m['skin_shift'], m['a5'], m['a6'], m['alt_on_skin'], m['secondary'] = r.u('bbBBBB')
    slots, = r.u('I')
    m['texture_index'] = list(r.u(f'{slots}i'))
    m['texture_type'] = list(r.u(f'{slots}i'))
    meshes = []
    for _ in range(m['mesh_count']):
        x = {}
        x['flag'], x['slot'], x['vertices'], x['normals'], x['texcoords'], x['triangles'] = r.u('Bhiiii')
        has_sub, = r.u('B')
        sub = r.take(5)
        x['sub'] = bytes(sub) if has_sub else None
        x['uv'] = r.take(8*x['texcoords'])
        x['tri'] = r.take(0x24*x['triangles'])
        x['V'] = r.take(12*x['vertices'])
        x['N'] = r.take(12*x['normals'])
        x['L'] = r.take(4*x['normals'])
        x['S'] = r.take(4*x['normals'])
        meshes.append(x)
    m['meshes'] = meshes
    c['model'] = m
    count, = r.u('I')
    bitmaps = []
    for _ in range(count):
        index, comps, name, w, h, size = r.u('ibIffI')
        bitmaps.append({'index': index, 'components': comps, 'name': name, 'width': w, 'height': h,
                        'pixels': r.take(size)})
    c['bitmaps'] = bitmaps
    count, = r.u('I')
    calls = []
    for _ in range(count):
        kind, target, flags, alpha, select, scale, u, v, texture = r.u('BiIfiffffi'.replace('ffffi', 'fffi'))
        calls.append(dict(kind=kind, target=target, flags=flags, alpha=alpha, select=select, scale=scale, u=u, v=v,
                          texture=texture))
    c['calls'] = calls
    if r.at != len(data):
        raise ValueError('trailing bytes in case')
    return c


def write_case(c):
    out = bytearray(b'MUMC')
    p = lambda fmt, *v: out.extend(struct.pack('<'+fmt, *v))
    p('I', 1)
    g = c['globals']
    p('ffffi', g['time'], *g['env'], g['skin_base'])
    k = c['cache']
    p('BBBBBBii', k['depth_test'], k['cull'], k['depth_mask'], k['alpha_test'], k['texture'], k['fog'], k['blend'],
      k['bound'])
    m = c['model']
    p('h', m['mesh_count'])
    p('i', m['hide_typed'])
    p('fff', *m['alt'])
    p('B', m['lighting'])
    p('fff', *m['color'])
    p('fff', *m['origin'])
    p('bbBBBB', m['light_mesh'], m['skin_shift'], m['a5'], m['a6'], m['alt_on_skin'], m['secondary'])
    p('I', len(m['texture_index']))
    p(f"{len(m['texture_index'])}i", *m['texture_index'])
    p(f"{len(m['texture_type'])}i", *m['texture_type'])
    for x in m['meshes']:
        p('Bhiiii', x['flag'], x['slot'], x['vertices'], x['normals'], x['texcoords'], x['triangles'])
        p('B', 1 if x['sub'] is not None else 0)
        out.extend(x['sub'] if x['sub'] is not None else bytes(5))
        for key in ('uv', 'tri', 'V', 'N', 'L', 'S'):
            out.extend(x[key])
    p('I', len(c['bitmaps']))
    for b in c['bitmaps']:
        p('ibIffI', b['index'], b['components'], b['name'], b['width'], b['height'], len(b['pixels']))
        out.extend(b['pixels'])
    p('I', len(c['calls']))
    for x in c['calls']:
        p('BiIfifffi', x['kind'], x['target'], x['flags'], x['alpha'], x['select'], x['scale'], x['u'], x['v'],
          x['texture'])
    return bytes(out)


def read_stream(data):
    return [struct.unpack_from('<5I', data, at) for at in range(0, len(data), 20)]


def read_tables(data):
    out, at = [], 0
    while at < len(data):
        mesh, lights = struct.unpack_from('<iI', data, at)
        at += 8
        light = data[at:at+12*lights]
        at += 12*lights
        count, = struct.unpack_from('<I', data, at)
        at += 4
        table = data[at:at+8*count]
        at += 8*count
        out.append((mesh, light, table))
    return out


# --------------------------------------------------------------------------
# Emulator.


class Machine:
    def __init__(self, text, data, flag, feature):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_WRITE,
                             UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_PROT_ALL)
        from unicorn import x86_const as x86
        self.x86 = x86
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        RW = UC_PROT_READ | UC_PROT_WRITE
        uc.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        data_size = (DATA_BYTES+0xfff) & ~0xfff
        uc.mem_map(DATA_BASE, data_size, UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        self.pages = {}
        for page in {FLAG_ADDRESS & ~0xfff, FEATURE_ADDRESS & ~0xfff, BIND_CACHE & ~0xfff, CACHE['fog'] & ~0xfff,
                     ENV_VECTOR & ~0xfff, SKIN_BASE & ~0xfff, STRCHR_SSE_FLAG & ~0xfff}:
            uc.mem_map(page, 0x1000, RW)
        uc.mem_write(FLAG_ADDRESS, flag)
        uc.mem_write(FEATURE_ADDRESS, feature)
        # Transform outputs, light/texcoord/colour tables (one mapping each span).
        uc.mem_map(0x06fce000, 0x072cb000-0x06fce000, RW)   # time, lights, texcoord table
        uc.mem_map(0x075a9000, 0x09258000-0x075a9000, RW)   # secondary, vertices, normals, colour table
        uc.mem_map(MODEL, 0x00800000, RW)
        uc.mem_map(BITMAPS, 0x02000000, RW)
        uc.mem_map(STACK, STACK_BYTES, RW)
        uc.mem_map(SENTINEL, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_map(TEB, 0x2000, RW)
        uc.mem_map(STUBS, 0x00100000, UC_PROT_ALL)
        uc.mem_write(STUBS, b'\xcc'*0x00100000)
        self.slot_names = {}
        for slot in range(OPENGL32_SLOTS[0], OPENGL32_SLOTS[1], 4):
            value = struct.unpack('<I', bytes(uc.mem_read(slot, 4)))[0]
            if value == 0:
                break
            if not STUBS <= value < STUBS+0x00100000:
                raise ValueError(f'import slot {slot:#x} outside the stub page')
            self.slot_names[value] = slot
        self.setup_fs()
        uc.hook_add(UC_HOOK_CODE, self.stub, begin=STUBS, end=STUBS+0x000fffff)
        uc.hook_add(UC_HOOK_CODE, self.lookup, begin=BITMAP_LOOKUP, end=BITMAP_LOOKUP)
        uc.hook_add(UC_HOOK_CODE, self.lookup, begin=BITMAP_BIND_LOOKUP, end=BITMAP_BIND_LOOKUP)
        for address in BRANCHES:
            uc.hook_add(UC_HOOK_CODE, self.branch, begin=address, end=address)
        for address in X87_TRANSCENDENTALS:
            uc.hook_add(UC_HOOK_CODE, self.x87, begin=address, end=address)
        self.x87_count = collections.Counter()
        for address in (*TRIG_RETURNS, POW_RETURN):
            uc.hook_add(UC_HOOK_CODE, self.trig, begin=address, end=address)
        uc.hook_add(UC_HOOK_CODE, self.pass_start, begin=LIGHT_PASS, end=LIGHT_PASS)
        uc.hook_add(UC_HOOK_CODE, self.pass_start, begin=TABLE_LOOP, end=TABLE_LOOP)
        uc.hook_add(UC_HOOK_CODE, self.begin_site, begin=BEGIN_SITE, end=BEGIN_SITE)
        uc.hook_add(UC_HOOK_CODE, self.texel, begin=TEXEL_READ, end=TEXEL_READ)
        uc.hook_add(UC_HOOK_CODE, self.entry, begin=MESH_DRAW, end=MESH_DRAW)
        uc.hook_add(UC_HOOK_CODE, self.getptd, begin=GETPTD, end=GETPTD)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self.unmapped)
        uc.hook_add(UC_HOOK_MEM_WRITE, self.forbidden_write, begin=TEXT_BASE, end=DATA_BASE+data_size-1)
        self.coverage = collections.Counter()
        self.trig_stats = {}

    def setup_fs(self):
        uc, x86 = self.uc, self.x86
        # Flat code/data plus one data descriptor for FS at the TEB.
        def descriptor(base, limit, access, flags):
            return struct.pack('<HHBBBB', limit & 0xffff, base & 0xffff, (base >> 16) & 0xff, access,
                               ((limit >> 16) & 0xf) | (flags << 4), (base >> 24) & 0xff)
        # Selectors: 1 flat code, 2 flat data (DS/ES/SS, 32-bit), 3 FS at the TEB.
        table = (bytes(8)+descriptor(0, 0xfffff, 0x9a, 0xc)+descriptor(0, 0xfffff, 0x92, 0xc)
                 + descriptor(TEB, 0xfff, 0x92, 0x4))
        uc.mem_write(GDT, table)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, GDT, len(table)-1, 0x0))
        uc.reg_write(x86.UC_X86_REG_FS, 3 << 3)
        for reg in (x86.UC_X86_REG_SS, x86.UC_X86_REG_DS, x86.UC_X86_REG_ES):
            uc.reg_write(reg, 2 << 3)

    def stop(self, reason):
        if self.state['stopped'] is None:
            self.state['stopped'] = reason
        self.uc.emu_stop()

    def esp(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_ESP)

    def u32(self, address):
        return struct.unpack('<I', bytes(self.uc.mem_read(address, 4)))[0]

    def stub(self, uc, address, size, ignored):
        slot = self.slot_names.get(address)
        if slot not in GL_SLOTS:
            self.stop(('unexpected-import', hex(slot) if slot else hex(address)))
            return
        name, count = GL_SLOTS[slot]
        esp = self.esp()
        ret = self.u32(esp)
        args = [self.u32(esp+4+4*k) for k in range(count)]
        if name in ('glColor3fv', 'glVertex3fv'):
            words = list(struct.unpack('<3I', bytes(uc.mem_read(args[0], 12))))+[0]
        else:
            words = (args+[0, 0, 0, 0])[:4]
            if name == 'glDepthMask':
                words[0] &= 0xff
        self.state['stream'].append((OPS[name], *words))
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp+4+4*count)
        uc.reg_write(self.x86.UC_X86_REG_EIP, ret)

    def lookup(self, uc, address, size, ignored):
        esp = self.esp()
        ret, index = self.u32(esp), struct.unpack('<i', bytes(uc.mem_read(esp+4, 4)))[0]
        record = self.state['bitmaps'].get(index, self.state['error_record'])
        self.state['lookups'] += 1
        uc.reg_write(self.x86.UC_X86_REG_EAX, record)
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp+8)
        uc.reg_write(self.x86.UC_X86_REG_EIP, ret)

    def branch(self, uc, address, size, ignored):
        self.coverage[BRANCHES[address]] += 1

    def trig(self, uc, address, size, ignored):
        # Return of the CRT call inside the client's sin/cos/pow wrapper: the
        # binary64 arguments are still on the stack, the result is in ST0. Each
        # result is compared with the host libm the port uses: after the
        # wrapper's binary32 store (what the routine consumes) and as binary64.
        x86 = self.x86
        if address == POW_RETURN:
            name = 'pow'
            base, exponent_arg = struct.unpack('<dd', bytes(uc.mem_read(self.esp(), 16)))
            host = math.pow(base, exponent_arg)
        else:
            name, function = TRIG_RETURNS[address]
            host = function(struct.unpack('<d', bytes(uc.mem_read(self.esp(), 8)))[0])
        top = (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7
        mantissa, exponent = uc.reg_read(getattr(x86, f'UC_X86_REG_FP{(top) & 7}'))
        if (exponent & 0x7fff) == 0x7fff:
            result = math.nan if mantissa & ((1 << 63)-1) else math.inf
        else:
            result = math.ldexp(mantissa, (exponent & 0x7fff)-16383-63) if mantissa else 0.0
        result = -result if exponent & 0x8000 else result
        entry = self.trig_stats.setdefault(name, {'calls': 0, 'binary32_differences': 0, 'binary64_differences': 0})
        entry['calls'] += 1
        same32 = struct.pack('<f', f32(result)) == struct.pack('<f', f32(host)) or (
            math.isnan(result) and math.isnan(host))
        same64 = struct.pack('<d', result) == struct.pack('<d', host) or (math.isnan(result) and math.isnan(host))
        entry['binary32_differences'] += int(not same32)
        entry['binary64_differences'] += int(not same64)

    def x87(self, uc, address, size, ignored):
        self.x87_count[X87_TRANSCENDENTALS[address]] += 1

    def getptd(self, uc, address, size, ignored):
        # CRT _getptd (per-thread data; strtok keeps its position at +0x1c): modelled.
        esp = self.esp()
        uc.reg_write(self.x86.UC_X86_REG_EAX, PTD_AT)
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp+4)
        uc.reg_write(self.x86.UC_X86_REG_EIP, self.u32(esp))

    def entry(self, uc, address, size, ignored):
        self.state['passes'] = set()   # a pass of an early-returning draw writes no table at glBegin

    def pass_start(self, uc, address, size, ignored):
        self.state['passes'].add(address)

    def begin_site(self, uc, address, size, ignored):
        ebp = uc.reg_read(self.x86.UC_X86_REG_EBP)
        mesh = struct.unpack('<i', bytes(uc.mem_read(ebp+8, 4)))[0]
        meshes = self.state['case']['model']['meshes']
        normals = meshes[mesh]['normals'] if 0 <= mesh < len(meshes) else 0
        light = b''
        if LIGHT_PASS in self.state['passes']:
            light = bytes(uc.mem_read(COLOURS+mesh*VERTEX_STRIDE, 12*normals))
        table = b''
        if TABLE_LOOP in self.state['passes']:
            table = bytes(uc.mem_read(TEXCOORDS, 8*min(normals, 15001)))
        self.state['tables'].append((mesh, light, table))
        self.state['passes'] = set()

    def texel(self, uc, address, size, ignored):
        # The client reads [pixels+at]; outside the allocation (always when the
        # loader freed it: pointer 0) it faults or reads foreign memory.
        x86 = self.x86
        base, at = uc.reg_read(x86.UC_X86_REG_EAX), uc.reg_read(x86.UC_X86_REG_ECX)
        span = self.state['pixels'].get(base)
        if base == 0 or span is None or not 0 <= at < span:
            self.state['fault'] = ('texel', hex(base), at - (1 << 32) if at >= 1 << 31 else at)
            uc.reg_write(x86.UC_X86_REG_EIP, SENTINEL)
            uc.emu_stop()

    def unmapped(self, uc, access, address, size, value, ignored):
        self.stop(('unmapped', hex(address), size, hex(uc.reg_read(self.x86.UC_X86_REG_EIP))))
        return False

    def forbidden_write(self, uc, access, address, size, value, ignored):
        self.stop(('write-to-image', hex(address), hex(uc.reg_read(self.x86.UC_X86_REG_EIP))))

    # ---- case layout ----

    def layout(self, case):
        uc = self.uc
        m = case['model']
        uc.mem_write(MODEL, bytes(0x00800000))
        uc.mem_write(0x06fce000, bytes(0x072cb000-0x06fce000))
        uc.mem_write(0x075a9000, bytes(0x09258000-0x075a9000))
        uc.mem_write(TEXCOORDS, b'\xff'*(8*15001))
        count = m['mesh_count']
        uc.mem_write(COLOURS, b'\xff'*(VERTEX_STRIDE*max(count, 1)))
        cursor = [ARENA]

        def put(payload, align=16):
            at = (cursor[0]+align-1) & -align
            uc.mem_write(at, payload)
            cursor[0] = at+len(payload)
            return at
        index_table = put(struct.pack(f"<{len(m['texture_index'])}i", *m['texture_index']) or b'\0'*4)
        type_table = put(struct.pack(f"<{len(m['texture_type'])}i", *m['texture_type']) or b'\0'*4)
        for i, x in enumerate(m['meshes']):
            record = bytearray(0x20)
            record[0] = x['flag']
            struct.pack_into('<hhhhh', record, 2, x['slot'], x['vertices'], x['normals'], x['texcoords'], x['triangles'])
            struct.pack_into('<I', record, 0x14, put(x['uv']) if x['uv'] else 0)
            struct.pack_into('<I', record, 0x18, put(x['tri']) if x['tri'] else 0)
            struct.pack_into('<I', record, 0x1c, put(x['sub']) if x['sub'] is not None else 0)
            uc.mem_write(MESHES+0x20*i, bytes(record))
            uc.mem_write(VERTICES+i*VERTEX_STRIDE, x['V'])
            uc.mem_write(NORMALS+i*VERTEX_STRIDE, x['N'])
            uc.mem_write(LIGHTS+i*LIGHT_STRIDE, x['L'])
            uc.mem_write(SECONDARY+i*LIGHT_STRIDE, x['S'])
        model = bytearray(0x100)
        struct.pack_into('<h', model, 0x24, count)
        struct.pack_into('<III', model, 0x28, MESHES, 0, 0)
        struct.pack_into('<IIi', model, 0x38, index_table, type_table, m['hide_typed'])
        struct.pack_into('<3f', model, 0x44, *m['alt'])
        model[0x50] = m['lighting']
        struct.pack_into('<3f', model, 0x54, *m['color'])
        struct.pack_into('<3f', model, 0x78, *m['origin'])
        struct.pack_into('<b', model, 0x94, m['light_mesh'])
        struct.pack_into('<bBB', model, 0xa4, m['skin_shift'], m['a5'], m['a6'])
        model[0xca], model[0xcb] = m['alt_on_skin'], m['secondary']
        uc.mem_write(MODEL, bytes(model))
        # Bitmap records (+0x204 width, +0x208 height, +0x214 components, +0x215 name, +0x21a pixels).
        uc.mem_write(BITMAPS, bytes(0x00400000))
        records, at = {}, BITMAPS
        self.pixel_spans = {}
        pixels_at = BITMAPS+0x00400000
        for b in case['bitmaps']:
            record = bytearray(0x222)
            pixels = 0
            if b['pixels']:
                uc.mem_write(pixels_at, b['pixels'])
                pixels = pixels_at
                self.pixel_spans[pixels] = len(b['pixels'])
                pixels_at = (pixels_at+len(b['pixels'])+15) & -16
            struct.pack_into('<ff', record, 0x204, b['width'], b['height'])
            struct.pack_into('<b', record, 0x214, b['components'])
            struct.pack_into('<I', record, 0x215, b['name'])
            struct.pack_into('<I', record, 0x21a, pixels)
            uc.mem_write(at, bytes(record))
            records[b['index']] = at
            at += 0x230
        error_record = at   # stands in for the client's error bitmap (lookup miss)
        uc.mem_write(error_record, bytes(0x222))
        g = case['globals']
        uc.mem_write(TIME, struct.pack('<f', g['time']))
        uc.mem_write(ENV_VECTOR, struct.pack('<3f', *g['env']))
        uc.mem_write(SKIN_BASE, struct.pack('<i', g['skin_base']))
        k = case['cache']
        for name, address in CACHE.items():
            uc.mem_write(address, bytes([k[name]]))
        uc.mem_write(BLEND_CACHE, struct.pack('<i', k['blend']))
        uc.mem_write(BIND_CACHE, struct.pack('<i', k['bound']))
        return records, error_record

    def run_case(self, case, limit=200_000_000):
        from unicorn import UcError
        x86, uc = self.x86, self.uc
        records, error_record = self.layout(case)
        self.state = {'stopped': None, 'stream': [], 'bitmaps': records, 'error_record': error_record,
                      'lookups': 0, 'tables': [], 'passes': set(), 'case': case, 'fault': None,
                      'pixels': self.pixel_spans}
        uc.mem_write(TEB, bytes(0x2000))
        uc.mem_write(TEB, struct.pack('<I', 0xffffffff))
        for call in case['calls']:
            if call['kind'] == 0:
                start = BODY
                args = struct.pack('<IIIIfifffii', call['flags'], VERTICES, NORMALS, LIGHTS, call['alpha'],
                                   call['select'], call['scale'], call['u'], call['v'], call['target'], call['texture'])
            else:
                start = MESH_DRAW
                args = struct.pack('<iIIIIfiffffi'.replace('ffffi', 'fffi'), call['target'], call['flags'], VERTICES,
                                   NORMALS, LIGHTS, call['alpha'], call['select'], call['scale'], call['u'], call['v'],
                                   call['texture'])
            esp = STACK+STACK_BYTES-0x1000
            uc.mem_write(esp, struct.pack('<I', SENTINEL)+args)
            regs = {x86.UC_X86_REG_ESP: esp, x86.UC_X86_REG_ECX: MODEL, x86.UC_X86_REG_EBP: 0x56789abc,
                    x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a, x86.UC_X86_REG_EDI: 0x456789ab,
                    x86.UC_X86_REG_EFLAGS: 0x202}
            for reg, value in regs.items():
                uc.reg_write(reg, value)
            uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
            uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
            try:
                uc.emu_start(start, SENTINEL, count=limit)
            except UcError as error:
                return {'error': self.state['stopped'] or ('emulation', str(error),
                                                           hex(uc.reg_read(x86.UC_X86_REG_EIP)))}
            if self.state['stopped']:
                return {'error': self.state['stopped']}
            if self.state['fault']:
                break
            if uc.reg_read(x86.UC_X86_REG_EIP) != SENTINEL:
                return {'error': ('did-not-return', hex(uc.reg_read(x86.UC_X86_REG_EIP)))}
            if uc.reg_read(x86.UC_X86_REG_ESP) != esp+4+0x2c:
                return {'error': ('stack-balance', hex(uc.reg_read(x86.UC_X86_REG_ESP)-esp))}
            for reg in (x86.UC_X86_REG_EBX, x86.UC_X86_REG_ESI, x86.UC_X86_REG_EDI, x86.UC_X86_REG_EBP):
                if uc.reg_read(reg) != regs[reg]:
                    return {'error': ('callee-saved', reg)}
            if self.u32(TEB) != 0xffffffff:
                return {'error': ('seh-chain-not-restored',)}
        cache = [uc.mem_read(address, 1)[0] for address in CACHE.values()]
        k = dict(zip(CACHE, cache))
        words = [k['depth_test'] | k['cull'] << 8 | k['depth_mask'] << 16 | k['alpha_test'] << 24,
                 k['texture'] | k['fog'] << 8, self.u32(BLEND_CACHE), self.u32(BIND_CACHE)]
        stream = list(self.state['stream'])
        if self.state['fault']:
            stream.append((FAULT_OP, 0, 0, 0, 0))
        stream.append((0x100, *words))
        stream.append((0x101, *struct.unpack('<3I', bytes(uc.mem_read(MODEL+0x54, 12))), 0))
        return {'stream': stream, 'tables': self.state['tables'], 'lookups': self.state['lookups'],
                'fault': self.state['fault']}


# --------------------------------------------------------------------------
# Client math wrappers on sampled arguments (sin 0x00968117, cos 0x009fa20d,
# pow 0x009f4218), compared with the host libm the port uses.

SIN, COS, POW = 0x00968117, 0x009fa20d, 0x009f4218
# The CRT's x87 fallback (taken by the SSE2 trig for large arguments, e.g. at
# 0x019997f5) reads an uncaptured CRT word at 0x0bdcfbc8 (the fast-math flag
# of _set_fastmath, default 0). Only the sweep maps it, as 0: no draw case
# reached it (the page is unmapped there and any access stops a case).
FASTFLAG = 0x0bdcfbc8
# x87 instructions of the CRT fallbacks. Unicorn (QEMU) evaluates fsin/fcos/
# fyl2x through the host libm, so results on those paths are not evidence of
# hardware x87 behaviour; they are counted and reported separately.
X87_TRANSCENDENTALS = {0x019997ed: 'fsin', 0x019996fd: 'fcos', 0x0199a65a: 'fyl2x'}


def st0(machine):
    x86, uc = machine.x86, machine.uc
    top = (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7
    mantissa, exponent = uc.reg_read(getattr(x86, f'UC_X86_REG_FP{top}'))
    if (exponent & 0x7fff) == 0x7fff:
        value = math.nan if mantissa & ((1 << 63)-1) else math.inf
    else:
        value = math.ldexp(mantissa, (exponent & 0x7fff)-16383-63) if mantissa else 0.0
    return -value if exponent & 0x8000 else value


def call_math(machine, address, *floats):
    uc, x86 = machine.uc, machine.x86
    machine.state = {'stopped': None, 'stream': [], 'fault': None}
    esp = STACK+STACK_BYTES-0x1000
    uc.mem_write(esp, struct.pack('<I', SENTINEL)+b''.join(struct.pack('<f', f) for f in floats))
    uc.reg_write(x86.UC_X86_REG_ESP, esp)
    uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
    uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
    from unicorn import UcError
    try:
        uc.emu_start(address, SENTINEL, count=100_000)
    except UcError as error:
        raise RuntimeError(f'math call stopped: {machine.state["stopped"]} {error}') from None
    if machine.state['stopped']:
        raise RuntimeError(f'math call stopped: {machine.state["stopped"]}')
    value = st0(machine)
    uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)  # empty the x87 stack again (cdecl float return)
    return f32(value) if not math.isnan(value) else value


def math_sweep(machine, rng, count):
    from unicorn import UC_PROT_READ
    machine.uc.mem_map(FASTFLAG & ~0xfff, 0x1000, UC_PROT_READ)
    def same(a, b):
        return (math.isnan(a) and math.isnan(b)) or struct.pack('<f', a) == struct.pack('<f', b)
    results = {}
    def check(name, address, args, host):
        entry = results.setdefault(name, {'calls': 0, 'binary32_differences': 0, 'x87_path': 0, 'examples': []})
        before = sum(machine.x87_count.values())
        client = call_math(machine, address, *args)
        entry['calls'] += 1
        x87 = sum(machine.x87_count.values()) != before
        entry['x87_path'] += int(x87)
        if x87:
            return   # emulated through the host libm: no evidence either way
        if not same(client, host):
            entry['binary32_differences'] += 1
            if len(entry['examples']) < 5:
                entry['examples'].append([repr(a) for a in args]+[repr(client), repr(host)])
    for _ in range(count):
        # 0x400 wave: (float)(int)(time + index*0x3a3) * 0.007; 0x8000/0x4000/0x1000: time*0.002, time*0.001.
        base = rng.randrange(-2**31, 2**31)
        x = f32(f32(float(base)) * f32(0.007))
        check('sin_wave', SIN, [x], f32(math.sin(x)))
        check('sin_wave_small', SIN, [f32(f32(float(base % 2000000)) * f32(0.007))],
              f32(math.sin(f32(f32(float(base % 2000000)) * f32(0.007)))))
        t = f32(rng.uniform(-1e7, 1e7))
        y = f32(t*f32(0.002))
        check('sin_time', SIN, [y], f32(math.sin(y)))
        z = f32(t*f32(0.001))
        check('cos_time', COS, [z], f32(math.cos(z)))
        w = struct.unpack('<f', struct.pack('<I', rng.randrange(0, 0x4f000000)))[0]
        check('sin_any', SIN, [w], f32(math.sin(w)))
    for texel in range(256):  # mode 0x8000: pow(texel/256, 2), every input
        f = f32(texel/256.0)
        check('pow_texel', POW, [f, 2.0], f32(math.pow(f, 2.0)))
    return results


# --------------------------------------------------------------------------
# Texture-name sub-object records (BMD loader 0x012b409a..0x012b4130).

NAME_PARSER, GETPTD, STRCHR_SSE_FLAG = 0x01185111, 0x019a4ba6, 0x0bdcb280
NAME_PARSER_BODIES = {  # start, exclusive end, SHA-256 of the captured bytes
    'name_parser': (0x01185111, 0x01185327, '4f9d53101640a0cbf20afa026c3d59e62c0121eb9eb3ab4828bf7ae2af40cb1a'),
    'strchr': (0x0194ce60, 0x0194cf60, '2a954438dc433bab4a41b3728c0bae481942c0733579638d4a08650d92784d4f'),
    'strcmp': (0x0195a3d0, 0x0195a460, 'bf44853397eec092b8f0cd537d7893cb621c3fcd61b558a760d05ae5ac78d9ec'),
    'strcspn': (0x0195a460, 0x0195a4a6, 'c3a436646e0acf44b28d2087806b0dcfc4869473f1b1b8cd1e0c01d07e16cc3c'),
    'strlen': (0x0195a4b0, 0x0195a540, '6d0818e68a7b8591aadfab0422d422a85862617da4d27584ceff92f2f4752143'),
    'strtok': (0x01983c08, 0x01983c26, '5b52a5c0114f3c24596057ace6e59c287e7d5e7cfa168869fa3ce2d5b3131989'),
    'strtok_s': (0x01986dac, 0x01986e55, '488cc16a10c98614751a792c4a363f38fcb9915c4db55b1215465f2822f5a674'),
    'cookie_check': (0x0191cd7c, 0x0191cd8a, 'f35ed70e0702993bbcd466d609f6ce7413c80b567483a99db7b990499f550063'),
}
NAME_AT, OBJECT_AT, PTD_AT = ARENA+0x00700000, ARENA+0x00700100, ARENA+0x00700200


def run_name_parser(machine, name, sse):
    """Client 0x01185111 on a 32-byte name: (result byte, six object bytes)."""
    uc, x86 = machine.uc, machine.x86
    machine.state = {'stopped': None, 'stream': [], 'fault': None}
    uc.mem_write(STRCHR_SSE_FLAG, struct.pack('<I', 1 if sse else 0))
    uc.mem_write(NAME_AT, name.ljust(32, b'\0')[:32]+bytes(32))
    uc.mem_write(OBJECT_AT, bytes(6))
    uc.mem_write(PTD_AT, bytes(0x100))
    esp = STACK+STACK_BYTES-0x1000
    uc.mem_write(esp, struct.pack('<II', SENTINEL, NAME_AT))
    uc.reg_write(x86.UC_X86_REG_ESP, esp)
    uc.reg_write(x86.UC_X86_REG_ECX, OBJECT_AT)
    uc.emu_start(NAME_PARSER, SENTINEL, count=1_000_000)
    if machine.state['stopped'] or uc.reg_read(x86.UC_X86_REG_ESP) != esp+8:
        raise RuntimeError(f'name parser stopped: {machine.state["stopped"]} on {name!r}')
    return uc.reg_read(x86.UC_X86_REG_EAX) & 0xff, bytes(uc.mem_read(OBJECT_AT, 6))


def synthetic_names(rng):
    fixed = [b'', b'_', b'a_', b'_R', b'x_R.jpg', b'x_RHSN.jpg', b'x_RHSNR.jpg', b'x_HX.jpg', b'x_XR.jpg', b'x_r.jpg',
             b'x_.jpg', b'x_R_S.jpg', b'x_R.S.jpg', b'x_S', b'a_b_N.tga', b'_N.ozj', b'skin_N_R.jpg', b'n.jpg',
             b'master10_center.jpg', b'lightning_4sq.jpg', b'fire_sq.jpg', b's195.tga', b'mu_rgb_lights.jpg',
             b'mu_rgb_lights.jpgX', b'Master10_center.jpg', b's195.TGA', b'fire_sq.jpg\0junk', b'q'*32,
             b'q'*31+b'_', b'q'*30+b'_R', b'q'*28+b'_RHS', b'_RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR', b'R_HSN.jpg',
             b'.._S..', b'x_S\x80.jpg', b'x_\xd2.jpg', b'x_DC.jpg', b'x_DT.jpg']
    alphabet = b'RHSN_.xrjDCT0\x00'
    out = list(fixed)
    for _ in range(4000):
        n = rng.randrange(0, 33)
        out.append(bytes(rng.choice(alphabet) for _ in range(n)))
    return out


def installed_names(game_root):
    data = Path(game_root)/'Data'
    data = data if data.is_dir() else Path(game_root)
    names = set()
    for path in sorted(data.rglob('*')):
        if path.suffix.lower() != '.bmd' or not path.is_file():
            continue
        result = subprocess.run([str(native_tool()), 'info', str(path)], capture_output=True, text=True)
        if result.returncode:
            continue
        for mesh in json.loads(result.stdout).get('mesh_list', []):
            names.add(mesh['texture'].encode('latin-1'))
    return sorted(names)


def names_run(machine, names):
    import ctypes
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    library = ctypes.CDLL(str(ROOT/f'native/build/libmumeshdraw.{suffix}'))
    function = library.mu_meshdraw_sub_from_name
    function.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    function.restype = ctypes.c_int
    results = {'names': len(names), 'matches': 0, 'records': 0, 'hidden': 0, 'failures': []}
    for k, name in enumerate(names):
        client, record = run_name_parser(machine, name, sse=k % 2 == 0)
        client_b, record_b = run_name_parser(machine, name, sse=k % 2 == 1)
        sub = ctypes.create_string_buffer(5)
        native = function(name.ljust(32, b'\0')[:32], sub)
        ok = (client == client_b and record == record_b and int(client != 0) == native
              and (not native or record[:5] == sub.raw))
        results['matches'] += int(ok)
        results['records'] += int(bool(client))
        results['hidden'] += int(bool(client) and record[1] != 0)
        if not ok and len(results['failures']) < 20:
            results['failures'].append({'name': name.hex(), 'client': [client, record.hex()],
                                        'native': [native, sub.raw.hex()]})
    return results


# --------------------------------------------------------------------------
# Native side.


def native_tool():
    return ROOT/'native/build/mu-render'


def replay(case_bytes, directory):
    case_path, out, tables = Path(directory)/'case.bin', Path(directory)/'native.ops', Path(directory)/'native.tables'
    case_path.write_bytes(case_bytes)
    result = subprocess.run([str(native_tool()), 'replay', str(case_path), '--out', str(out), '--tables-out',
                             str(tables)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return read_stream(out.read_bytes()), read_tables(tables.read_bytes())


def compare(machine, case_bytes, directory, corners=None):
    """Runs a case on both sides; returns a result dict."""
    case = read_case(case_bytes)
    client = machine.run_case(case)
    if 'error' in client:
        return {'match': False, 'error': client['error']}
    native, tables = replay(case_bytes, directory)
    result = {'records': len(client['stream']), 'stream_match': client['stream'] == native,
              'fault': client['fault'] is not None,
              'tables_match': [(m, l, t) for m, l, t in client['tables']] == tables, 'tables': len(tables)}
    if corners is not None:
        result['corners_match'] = corners == [r for r in client['stream'] if r[0] < 0x100]
    if not result['stream_match']:
        for k, (a, b) in enumerate(zip(client['stream'], native)):
            if a != b:
                result['first_difference'] = {'index': k, 'client': [hex(v) for v in a], 'native': [hex(v) for v in b]}
                break
        else:
            result['first_difference'] = {'length_client': len(client['stream']), 'length_native': len(native)}
    if not result['tables_match']:
        result['table_detail'] = {'client': [(m, len(l), len(t)) for m, l, t in client['tables']][:8],
                                  'native': [(m, len(l), len(t)) for m, l, t in tables][:8]}
    result['digest'] = hashlib.sha256(b''.join(struct.pack('<5I', *r) for r in client['stream'])).hexdigest()
    result['match'] = result['stream_match'] and result['tables_match'] and result.get('corners_match', True)
    return result


def corners_case(model_path, args, directory, label):
    """`mu-render corners --case-out` for a model and options: (case bytes, stream)."""
    out, case = Path(directory)/f'{label}.ops', Path(directory)/f'{label}.case'
    result = subprocess.run([str(native_tool()), 'corners', str(model_path), '--out', str(out), '--case-out', str(case),
                             *[str(a) for a in args]], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return case.read_bytes(), read_stream(out.read_bytes()), json.loads(result.stdout)


# --------------------------------------------------------------------------
# Option matrix and mutations.

# Flag sets that cover every branch of the routine. `mode` is never an
# argument: the routine derives it from the flags.
FLAG_SETS = [0, 1, 0x41, 0x81, 0x2001, 2, 0x42, 0x82, 0x400002, 0x2002, 0x40002, 0x40, 0x2040, 4, 8, 0x200, 0x800,
             0x1000, 0x4000, 0x10000, 0x20000, 0x80000, 0x100000, 0x8000, 0x1042, 0x80040, 0x804, 0x14, 0x84, 0x2004,
             0x20, 0x22, 0x400, 0x402, 0x420, 0x200000, 0x200002, 0x40004, 0x1010, 0x4080, 0x44]


def option_matrix(rng):
    """(label, mu-render options) for synthetic models."""
    out = []
    for flags in FLAG_SETS:
        out.append((f'f{flags:x}', ['--flags', hex(flags)]))
    extras = [
        ['--alpha', '0.5'], ['--alpha', 'nan'], ['--alpha', '0.99'], ['--lighting', '0'],
        ['--lighting', '0', '--alpha', '0.25', '--flags', '0x1000'], ['--select', '1', '--uv-offset', '0.5', '0.125'],
        ['--select', '-2', '--color-scale', '0.75'], ['--select', '-2', '--flags', '0x82'], ['--select', '0'],
        ['--select', '1', '--flags', '0x40'], ['--uv-offset', '0.25', '-0.5', '--flags', '0x1000', '--select', '-1'],
        ['--uv-offset', '0', '5', '--flags', '0x200000'], ['--secondary', '1'], ['--light-skip-mesh', '1'],
        ['--skip-mesh', '2'], ['--texture', '0x9001'], ['--texture', '0x9001', '--flags', '0x8000'],
        ['--time', '123456.75', '--flags', '0x1000'], ['--time', '98765.5', '--flags', '0x4000'],
        ['--time', '4321.25', '--flags', '0x204'], ['--time', '777.5', '--flags', '0x20000'],
        ['--time', '-5000.5', '--flags', '4'], ['--env-vector', '0.3', '-0.4', '0.86', '--flags', '0x800'],
        ['--time', '31337', '--flags', '0x402'], ['--color', '0.5', '0.25', '2', '--flags', '0x40004', '--alpha', '0.5'],
        ['--alpha', '0.3', '--flags', '0x80040'], ['--uv-offset', 'nan', '0', '--select', '0'],
        ['--alpha', '0.5', '--flags', '0x44'],
    ]
    for k, extra in enumerate(extras):
        out.append((f'x{k}', extra))
    return out


def mutate(case, rng, variant):
    """Client-only inputs the viewer never sets: skin textures, types, sub-objects, model bytes."""
    c = json.loads(json.dumps(case, default=lambda b: b.hex()))  # deep copy with bytes as hex
    def unhex(x):
        for key in ('uv', 'tri', 'V', 'N', 'L', 'S'):
            x[key] = bytes.fromhex(x[key])
        x['sub'] = bytes.fromhex(x['sub']) if x['sub'] is not None else None
    for x in c['model']['meshes']:
        unhex(x)
    for b in c['bitmaps']:
        b['pixels'] = bytes.fromhex(b['pixels'])
    m = c['model']
    slots = len(m['texture_index'])
    special = [0x791a, 0x7725, 0x77c7, 0x7818, 0x7869, 0x7776, 0x78ba, 0x76f8, 0x791c, 0x7800, -1, -5]
    m['texture_index'] = [rng.choice(special) if rng.random() < 0.5 else v for v in m['texture_index']]
    m['texture_type'] = [rng.choice([0, 0, 1, 2]) for _ in range(slots)]
    m['hide_typed'] = rng.choice([0, 0, 1])
    m['skin_shift'] = rng.choice([0, 1, -1, 3])
    m['a5'], m['a6'], m['alt_on_skin'] = rng.choice([0, 0, 1]), rng.choice([0, 1]), rng.choice([0, 1])
    m['alt'] = [f32(rng.uniform(0, 2)) for _ in range(3)]
    m['light_mesh'] = rng.choice([-1, 0, 1, 2])
    for x in m['meshes']:
        x['flag'] = rng.choice([0, 0, 0, 1])
        if rng.random() < 0.6:
            x['sub'] = bytes(rng.choice([0, 0, 1]) for _ in range(4))+bytes([rng.choice([0, 1, 1, 2])])
        if rng.random() < 0.05:
            x['triangles'], x['tri'] = 0, b''
    g = c['globals']
    g['skin_base'] = rng.choice([0, 5, 40])
    g['time'] = f32(rng.uniform(-1e5, 1e6))
    g['env'] = [f32(rng.uniform(-1, 1)) for _ in range(3)]
    for b in c['bitmaps']:
        b['components'] = rng.choice([3, 4])
    known = [b['index'] for b in c['bitmaps']]
    extra_indices = [0x7726, 0x77c8, 0x7819, 0x786a, 0x7777, 0x78bb, 0x76fd, 0x7727]
    for index in extra_indices:
        if index not in known:
            c['bitmaps'].append({'index': index, 'components': rng.choice([3, 4]), 'name': 500+index % 97,
                                 'width': 64.0, 'height': 32.0, 'pixels': b''})
    # Bitmaps whose pixels the loaders keep (0x7532, 0x7def, 0x7bd1, 0x851b):
    # width*height*components bytes, read by mode 0x8000.
    for index in (0x7532, 0x7def):
        if index not in known:
            comps, w, h = rng.choice([3, 4]), rng.choice([8, 16, 64]), rng.choice([4, 16, 32])
            c['bitmaps'].append({'index': index, 'components': comps, 'name': 900+index % 89, 'width': float(w),
                                 'height': float(h), 'pixels': bytes(rng.randrange(256) for _ in range(w*h*comps))})
    k = c['cache']
    k.update(depth_test=rng.choice([0, 1]), cull=rng.choice([0, 1]), depth_mask=rng.choice([0, 1]),
             alpha_test=rng.choice([0, 1]), texture=rng.choice([0, 1]), fog=rng.choice([0, 0, 1]),
             blend=rng.choice([0, 1, 2, 3, 4, 8, 5]), bound=rng.choice([-0x7fffffff, 0x9000, 0x7fcf]))
    calls = []
    for _ in range(rng.choice([1, 2, 3])):
        flags = rng.choice(FLAG_SETS) | rng.choice([0, 0, 0x2000, 0x40000, 0x10, 0x400000])
        if flags & 0x8000:
            texture = rng.choice([b['index'] for b in c['bitmaps'] if b['pixels']]*6+[-1, known[0] if known else -1])
        else:
            texture = rng.choice([-1, -1, -1]+known[:2])
        call = dict(kind=rng.choice([0, 0, 1]), target=rng.choice([-1, 0, 1, 2]), flags=flags,
                    alpha=f32(rng.choice([1.0, 0.5, 0.995, 0.25])), select=rng.choice([-1, -2, 0, 1, 2, -3]),
                    scale=f32(rng.uniform(0, 2)), u=f32(rng.choice([0.0, 0.25, -0.5])), v=f32(rng.choice([0.0, 0.5, 3.0])),
                    texture=texture)
        if call['kind'] == 1 and call['target'] < 0:
            call['target'] = rng.choice([0, 1, 5])
        calls.append(call)
    c['calls'] = calls
    return c


# --------------------------------------------------------------------------


def synthetic_run(machine, directory, rng, mutations=200):
    sys.path.insert(0, str(ROOT/'native/tests'))
    import native_fixtures as nf
    results = {'viewer_cases': 0, 'viewer_matches': 0, 'mutated_cases': 0, 'mutated_matches': 0, 'records': 0,
               'fault_cases': 0, 'failures': [], 'digests': {}}
    models = []
    # Model 10's texture names give the loader's sub-object records (uv/highlight
    # select + uv mesh, no environment group, hidden).
    named = {10: ['skin_RS.tga', 'cloth_N.tga', 'metal_H.tga']}
    for seed, version in ((8, 10), (9, 15), (10, 10)):
        sub = Path(directory)/f'model{seed}'
        sub.mkdir(exist_ok=True)
        models.append((seed, nf.write_textured_model(sub, seed, version=version, four_corner=True,
                                                     names=named.get(seed))))
    base = ['--action', '1', '--frame', '1.5', '--origin', '3', '4', '5']
    cases = []
    for seed, path in models:
        for label, args in option_matrix(rng):
            case_bytes, corners, report = corners_case(path, base+args, directory, f's{seed}{label}')
            result = compare(machine, case_bytes, directory, corners)
            results['viewer_cases'] += 1
            results['viewer_matches'] += int(result['match'])
            results['records'] += result.get('records', 0)
            results['fault_cases'] += int(result.get('fault', False))
            results['digests'][f's{seed}{label}'] = result.get('digest')
            if not result['match']:
                results['failures'].append({'case': f's{seed}{label}', **result})
            cases.append(read_case(case_bytes))
    for k in range(mutations):
        mutated = write_case(mutate(rng.choice(cases), rng, k))
        result = compare(machine, mutated, directory)
        results['mutated_cases'] += 1
        results['mutated_matches'] += int(result['match'])
        results['records'] += result.get('records', 0)
        results['fault_cases'] += int(result.get('fault', False))
        if not result['match']:
            results['failures'].append({'case': f'mutation{k}', **result})
            (Path(directory)/f'failed-mutation{k}.case').write_bytes(mutated)
    return results


def installed_run(machine, directory, game_root, per_folder, rng):
    data = Path(game_root)/'Data'
    data = data if data.is_dir() else Path(game_root)
    results = {'cases': 0, 'matches': 0, 'records': 0, 'models': 0, 'failures': [], 'skipped': 0, 'fault_cases': 0,
               'folders': 0}
    folders = collections.defaultdict(list)
    for path in sorted(data.rglob('*')):
        if path.suffix.lower() == '.bmd' and path.is_file():
            folders[path.parent.name].append(path)
    for folder, paths in sorted(folders.items()):
        results['folders'] += 1
        picks = paths if len(paths) <= per_folder else rng.sample(paths, per_folder)
        for path in picks:
            # Mostly the dominant body flags 2, then the whole flag matrix.
            flags = rng.choice([2, 2, 2, 0x42, 0x82, 0x2002, 0x40002] + FLAG_SETS)
            args = ['--flags', hex(flags), '--time', repr(f32(rng.uniform(0, 1e6))),
                    '--alpha', rng.choice(['1', '1', '0.5'])]
            if flags & 0x1000 or rng.random() < 0.2:
                args += ['--uv-offset', '0.25', '0.5', '--select', rng.choice(['-1', '0', '1'])]
            if rng.random() < 0.1:
                args += ['--select', '-2', '--color-scale', '0.75']
            try:
                case_bytes, corners, report = corners_case(path, args, directory, 'installed')
            except RuntimeError:
                results['skipped'] += 1
                continue
            case = read_case(case_bytes)
            meshes = case['model']['meshes']
            if report['meshes'] == 0 or len(meshes) > MAX_MESHES or any(
                    x['vertices'] > MAX_ENTRIES or x['normals'] > MAX_ENTRIES for x in meshes):
                results['skipped'] += 1   # no meshes, or more than the client's transform buffers hold
                continue
            result = compare(machine, case_bytes, directory, corners)
            results['cases'] += 1
            results['models'] += 1
            results['fault_cases'] += int(result.get('fault', False))
            results['matches'] += int(result['match'])
            results['records'] += result.get('records', 0)
            if not result['match']:
                results['failures'].append({'model': str(path.relative_to(data)), **result})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True)
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--per-folder', type=int, default=4)
    parser.add_argument('--mutations', type=int, default=200)
    parser.add_argument('--seed', type=int, default=20261017)
    parser.add_argument('--case', type=Path, help='compare one case file only')
    parser.add_argument('--math-sweep', type=int, default=20000,
                        help='sampled arguments per client math wrapper (0 to skip)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = load_pinned(args.text, TEXT_BYTES, tracks.TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, tracks.DATA_SHA256, 'second image section')
    flag = load_pinned(args.flag, 4, tracks.FLAG_SHA256, 'trig dispatch flag')
    feature = load_pinned(args.feature, 4, tracks.FEATURE_SHA256, 'math feature word')
    for name, (start, end, digest) in {**BODIES, **NAME_PARSER_BODIES}.items():
        if hashlib.sha256(text[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
            raise SystemExit(f'pinned body {name} differs')
    subprocess.run(['make', '-C', str(ROOT/'native')], check=True, capture_output=True)
    machine = Machine(text, data, flag, feature)
    rng = random.Random(args.seed)
    report = {'text_sha256': tracks.TEXT_SHA256, 'data_sha256': tracks.DATA_SHA256,
              'bodies': {k: v[2] for k, v in {**BODIES, **NAME_PARSER_BODIES}.items()}}
    with tempfile.TemporaryDirectory() as directory:
        if args.math_sweep:
            report['math_sweep'] = math_sweep(machine, random.Random(args.seed), args.math_sweep)
            machine.x87_count.clear()
        names = synthetic_names(random.Random(args.seed))
        report['names_synthetic'] = names_run(machine, names)
        if args.game_root:
            report['names_installed'] = names_run(machine, installed_names(args.game_root))
        if args.case:
            report['case'] = compare(machine, args.case.read_bytes(), directory)
        else:
            report['synthetic'] = synthetic_run(machine, directory, rng, args.mutations)
            if args.game_root:
                report['installed'] = installed_run(machine, directory, args.game_root, args.per_folder, rng)
    report['coverage'] = dict(sorted(machine.coverage.items()))
    report['uncovered'] = sorted(set(BRANCHES.values())-set(machine.coverage))
    report['trig'] = machine.trig_stats
    report['x87_transcendentals_in_draw_cases'] = dict(machine.x87_count)
    text_report = json.dumps(report, indent=1)
    if args.output:
        args.output.write_text(text_report)
    print(text_report if len(text_report) < 20000 else json.dumps({k: v for k, v in report.items()
                                                                   if k not in ('synthetic',)}, indent=1)[:20000])
    ok = all(r.get('match', True) for r in [report.get('case', {})])
    if any(v['binary32_differences'] for v in report.get('math_sweep', {}).values()):
        ok = False
    for key in ('synthetic', 'installed', 'names_synthetic', 'names_installed'):
        if key in report and report[key]['failures']:
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
