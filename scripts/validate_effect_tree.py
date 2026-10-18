#!/usr/bin/env python3
"""Compare the reconstructed effect tree and EffectManager layer with the client's own code (NATIVE-FX-002).

The client's actual instructions run in Unicorn over the pinned restored text, the verified second image section
and the initialized part of the third section (the machine of scripts/validate_effects.py). Three case kinds:

  tree     an installed .ein (all 370) or a mutation of one: the client's base load 0x00a760b2 builds the tree
           ("Children"); the owner is set with 0x00a76a30; every frame runs the node update 0x00a75708(dt,
           external, owner) on the root (transform 0x00a76dfe with parent or external matrix, owner action gate,
           type update, bounding box vtable +0x0c, children) and the draw (vtable +0x04) of every node.
  clone    the same, on an instance made by the client's clone 0x00a75934 (type clones 0x00a8986a/0x00a6fb0a)
           with a new transform, owner tint flag, action list and start frame.
  manager  several managed effects (constructed with a manager whose +0xb0 is an octree root built by
           0x00a8e766/0x00a8de79 over the EffectManager's world box): the node updates keep the octree
           (insert 0x00a8df54, remove 0x00a8e4d7); the frustum is built by 0x00a8d821 and the EffectManager render
           0x00a7a30e queries the octree (0x00a8e59f, sphere test 0x00a8d7c8) and draws.

Compared against reconstructed/effects (ctypes) per frame and per node: the node record (world matrix, world
position, world scale, duration, time left, bounding box, playing, drawn, looping), the live particle records, the
glBufferSubData vertex bytes and draw state of each draw, the number of rand() calls and the emitter's rand() % 0
fault; for manager cases also the frustum record (0x90 bytes), the octree node holding every effect (depth and
box), the visible effects in render order and the render pass's GL calls around the effect draws.

Boundaries modelled in Python are those of scripts/validate_effects.py, plus glGetBooleanv/glGetIntegerv (return
the case's GL state before the pass) and glDepthMask (recorded). The EffectManager object itself is a stand-in
block: the routines only read its octree pointer (+0xb0).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_effects as base  # noqa: E402
from validate_effects import CaseError, f32, fbits  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BODIES = {
    'base_load': (0x00a760b2, 0x00a76898),
    'node_update': (0x00a75708, 0x00a75934),
    'clone': (0x00a75934, 0x00a75b17),
    'transform': (0x00a76dfe, 0x00a77164),
    'set_owner': (0x00a76a30, 0x00a76aa9),
    'particle_bbox': (0x00a88970, 0x00a88cfb),
    'billboard_bbox': (0x00a6ed9b, 0x00a6ee80),
    'particle_clone': (0x00a8986a, 0x00a89a4a),
    'billboard_clone': (0x00a6fb0a, 0x00a6fcfd),
    'octree_insert': (0x00a8df54, 0x00a8e4d7),
    'octree_remove': (0x00a8e4d7, 0x00a8e59f),
    'octree_query': (0x00a8e59f, 0x00a8e766),
    'frustum_set': (0x00a8d821, 0x00a8dc7c),
    'frustum_sphere': (0x00a8d7c8, 0x00a8d821),
    'manager_render': (0x00a7a30e, 0x00a7a4e7),
    'texture_upload': (0x00a90987, 0x00a90aef),
}
GL_EXTRA = {0x1a7c73c: 'glGetBooleanv', 0x1a7c738: 'glGetIntegerv', 0x1a7c740: 'glDepthMask',
            0x1a7c780: 'glGenTextures', 0x1a7c74c: 'glTexParameteri', 0x1a7c708: 'glTexEnvi',
            0x1a7c788: 'glTexImage2D', 0x1a7c710: 'glDeleteTextures'}
TEXTURE_UPLOAD, BUILD_MIPMAPS = 0x00a90987, 0x0191b3d1
TEXTURE_OPS = {'glGenTextures': 9, 'glBindTexture': 6, 'glTexParameteri': 10, 'glTexEnvi': 11, 'gluBuild2DMipmaps': 12,
               'glTexImage2D': 13, 'glDeleteTextures': 14}
NEW_TEXTURE, TEXTURE_NAME = 0xffffffff, 7
PS_DRAW, BB_DRAW, RENDER_DRAW_RETURN = 0x00a88720, 0x00a6ebd1, 0x00a7a43d
OP = {'glGetBooleanv': 1, 'glGetIntegerv': 2, 'glDepthMask': 3, 'glEnable': 4, 'glDisable': 5, 'glBindTexture': 6,
      'glBlendFunc': 7}
DRAW_EFFECTS = 8
CRT_SQRT = 0x00961a07
CRT_NAN = 'sqrt of NaN reaches the CRT error path (not modelled)'


class TreeMachine(base.Machine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from unicorn import UC_HOOK_CODE
        for slot, name in GL_EXTRA.items():
            self.stub_name[base.STUB + (slot - 0x1a7c000)] = name
        self.gl_values = {}
        for address in (PS_DRAW, BB_DRAW, RENDER_DRAW_RETURN):
            self.uc.hook_add(UC_HOOK_CODE, self.on_mark, begin=address, end=address)
        self.uc.hook_add(UC_HOOK_CODE, self.on_sqrt, begin=CRT_SQRT, end=CRT_SQRT)
        self.hooks[BUILD_MIPMAPS] = (self.h_mipmaps, 0)   # gluBuild2DMipmaps (statically linked GLU): recorded
        self.uc.hook_add(UC_HOOK_CODE, self.on_replaced, begin=BUILD_MIPMAPS, end=BUILD_MIPMAPS)

    def h_mipmaps(self, args):
        self.gl.append(['gluBuild2DMipmaps', args[2], args[3]])
        return 0

    def on_sqrt(self, uc, address, size, ignored):
        # sqrt of a NaN takes the UCRT error path, whose state the harness does not set up: stop the case there.
        word = self.r32(uc.reg_read(self.x86.UC_X86_REG_ESP) + 4)
        if (word & 0x7f800000) == 0x7f800000 and word & 0x7fffff:
            self.stop_reason = CRT_NAN
            uc.emu_stop()

    def on_mark(self, uc, address, size, ignored):
        if address == RENDER_DRAW_RETURN:
            self.gl.append(['END'])
        else:
            # Each draw sees culling enabled in the client's cached GL state, so a billboard's disable is
            # recorded for every draw (the per-draw convention of validate_effects).
            self.map_page(base.CULL_CACHE)
            uc.mem_write(base.CULL_CACHE, b'\x01')
            self.written3.add(base.CULL_CACHE)
            self.gl.append(['DRAW', uc.reg_read(self.x86.UC_X86_REG_ECX)])

    def on_stub(self, uc, address, size, ignored):
        name = self.stub_name.get(address)
        if name not in GL_EXTRA.values():
            return super().on_stub(uc, address, size, ignored)
        x86 = self.x86
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret = self.r32(esp)
        self.imports[name] = self.imports.get(name, 0) + 1
        if name == 'glDepthMask':
            self.gl.append([name, self.r32(esp + 4) & 0xff])
            pop = 4
        elif name in ('glGenTextures', 'glDeleteTextures'):
            if name == 'glGenTextures':
                uc.mem_write(self.r32(esp + 8), struct.pack('<I', TEXTURE_NAME))
            self.gl.append([name, self.r32(esp + 4)])
            pop = 8
        elif name in ('glTexParameteri', 'glTexEnvi'):
            self.gl.append([name, self.r32(esp + 8), self.r32(esp + 12)])
            pop = 12
        elif name == 'glTexImage2D':
            self.gl.append([name, self.r32(esp + 16), self.r32(esp + 20)])
            pop = 36
        else:
            pname, out = self.r32(esp + 4), self.r32(esp + 8)
            value = self.gl_values.get(pname, 0)
            if name == 'glGetBooleanv':
                uc.mem_write(out, bytes([value & 0xff]))
            else:
                uc.mem_write(out, struct.pack('<I', value & 0xffffffff))
            self.gl.append([name, pname])
            pop = 8
        uc.reg_write(x86.UC_X86_REG_ESP, esp + 4 + pop)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)


def parse_draw(records):
    """Vertex bytes, draw state words and vertex count of one effect draw's GL calls (as validate_effects)."""
    vertices, state, count = b'', [0, 0, 0, 0, 0, 0, 0], 0
    for record in records:
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


class ClientScene:
    """Roots built by the client's own constructors and base load, sharing one owner (and manager)."""

    def __init__(self, machine, seed, texture, managed):
        m = self.m = machine
        m.reset()
        m.rand_state = seed & 0xffffffff
        m.texture_mode = texture
        self.roots, self.templates = [], {}
        self.manager = 0
        if managed:
            self.manager = m.alloc(0x100, b'\0')
            node = m.alloc(0x44)
            m.call(0x00a8e766, [], ecx=node)
            box = m.alloc(24)
            m.uc.mem_write(box, struct.pack('<6f', -12750.0, -12750.0, -25500.0, 38250.0, 38250.0, 25500.0))
            m.call(0x00a8de79, [box], ecx=node)
            m.w32(self.manager + 0xb0, node)
        self.owner = m.alloc(0x400, b'\0')
        self.camera = m.alloc(0x90, b'\0')
        self.external = m.alloc(64, b'\0')

    def add(self, text):
        m = self.m
        source = m.alloc(0x40); m.call(0x0094997e, [m.cstr(text)], ecx=source)
        root = m.alloc(0x40); m.call(0x0093c510, [0], ecx=root)
        reader = m.alloc(0x400); m.call(0x0093f708, [], ecx=reader)
        if not m.call(0x0093f7e8, [source, root, 1], ecx=reader) & 0xff:
            raise CaseError('client JSON parse failed')
        kind = json.loads(text).get('Type')
        name = m.alloc(0x40); m.call(0x0094997e, [m.cstr('fx')], ecx=name)
        position, rotation = m.alloc(12, b'\0'), m.alloc(12, b'\0')
        if kind == 0:   # factory 0x00a797a0 / child construction arguments
            o = m.alloc(0x158)
            m.call(0x00a8a436, [self.manager, name, position, rotation, fbits(1.0), 1, 1, fbits(5.0), 0x14, 1, 0,
                                fbits(1.0), fbits(0.0), 0, 0, fbits(0.0), fbits(0.0)], ecx=o)
        elif kind == 1:
            o = m.alloc(0x170)
            color = m.alloc(16); m.uc.mem_write(color, struct.pack('<4f', 1, 1, 1, 1))
            uv0 = m.alloc(8); m.uc.mem_write(uv0, struct.pack('<2f', 0, 0))
            uv1 = m.alloc(8); m.uc.mem_write(uv1, struct.pack('<2f', 1, 1))
            m.call(0x00a6fea9, [self.manager, name, position, rotation, fbits(1.0), 1, fbits(5.0), color, fbits(1.0),
                                fbits(1.0), fbits(0.0), uv0, uv1, 1, 0, fbits(1.0), 0, 0, fbits(0.0), fbits(0.0)],
                   ecx=o)
        else:
            raise CaseError('unsupported type')
        m.call(0x00a760b2, [root], ecx=o)
        self.roots.append(o)
        return len(self.roots) - 1

    def children(self, o):
        head = self.m.r32(o + 0xb4)
        out, n = [], self.m.r32(head)
        while n != head:
            out.append(self.m.r32(n + 8))
            n = self.m.r32(n)
        return out

    def walk(self, o, out):
        out.append(o)
        for c in self.children(o):
            self.walk(c, out)
        return out

    def nodes(self):
        out = []
        for o in self.roots:
            self.walk(o, out)
        return out

    def clone(self, r, position, rotation, scale, tint, actions, start):
        m = self.m
        template = self.roots[r]
        self.templates[r] = template
        p = m.alloc(12); m.uc.mem_write(p, struct.pack('<3f', *position))
        q = m.alloc(12); m.uc.mem_write(q, struct.pack('<3f', *rotation))
        begin = m.alloc(max(4 * len(actions), 4))
        m.uc.mem_write(begin, b''.join(struct.pack('<i', a) for a in actions))
        end = begin + 4 * len(actions)
        if not actions:
            begin = end = 0
        out = m.alloc(8, b'\0')
        m.call(0x00a75934, [out, p, q, fbits(scale), tint & 1, begin, end, end, fbits(start)], ecx=template)
        self.roots[r] = m.r32(out)
        if not self.roots[r]:
            raise CaseError('client clone returned no effect')

    def set_owner(self, flag5, flag6, action, visible, frame, tint, first):
        m, o = self.m, self.owner
        m.uc.mem_write(o + 5, bytes([flag5 & 1, flag6 & 1]))
        m.uc.mem_write(o + 0x2a, struct.pack('<H', action & 0xffff))
        m.uc.mem_write(o + 0x38, bytes([visible & 1]))
        m.uc.mem_write(o + 0xd0, struct.pack('<f', frame))
        m.uc.mem_write(o + 0x1e8, struct.pack('<3f', *tint))
        if first:
            for root in self.roots:
                m.call(0x00a76a30, [o], ecx=root)

    def set_gate(self, node, tint, actions, start):
        m = self.m
        begin = m.alloc(max(4 * len(actions), 4))
        m.uc.mem_write(begin, b''.join(struct.pack('<i', a) for a in actions))
        end = begin + 4 * len(actions)
        m.uc.mem_write(node + 0xc4, struct.pack('<3I', begin, end, end))
        m.uc.mem_write(node + 0xd0, struct.pack('<f', start))
        m.uc.mem_write(node + 0xdc, bytes([tint & 1]))

    def set_transform(self, node, position, rotation, scale):
        m = self.m
        m.uc.mem_write(node + 0x2c, struct.pack('<3f', *position))
        m.uc.mem_write(node + 0x44, struct.pack('<3f', *rotation))
        m.uc.mem_write(node + 0x50, struct.pack('<f', scale))

    def set_camera(self, position, forward, up):
        z = f32(f32(forward[0] * up[1]) - f32(forward[1] * up[0]))
        y = f32(f32(forward[2] * up[0]) - f32(forward[0] * up[2]))
        x = f32(f32(forward[1] * up[2]) - f32(forward[2] * up[1]))
        self.m.uc.mem_write(self.camera, struct.pack('<12f', *position, *forward, x, y, z, *up))

    def set_frustum(self, eye, forward, up, fov, aspect, near, far):
        m = self.m
        vectors = []
        for v in (eye, forward, up):
            a = m.alloc(12); m.uc.mem_write(a, struct.pack('<3f', *v)); vectors.append(a)
        m.call(0x00a8d821, vectors + [fbits(fov), fbits(aspect), fbits(near), fbits(far)], ecx=self.camera)
        return m.rb(self.camera, 0x90)

    def update(self, r, dt, external):
        m = self.m
        pointer = 0
        if external is not None:
            m.uc.mem_write(self.external, struct.pack('<16f', *external))
            pointer = self.external
        m.call(0x00a75708, [fbits(dt), pointer, self.owner], ecx=self.roots[r])

    def draw(self, o):
        m = self.m
        m.gl.clear()
        kind = m.r32(o)
        if kind == 0x01a80844:   # billboard: culling on in the client's cached state, so the disable is recorded
            m.map_page(base.CULL_CACHE)
            m.uc.mem_write(base.CULL_CACHE, b'\x01')
            m.written3.add(base.CULL_CACHE)
        m.call(m.r32(kind + 4), [self.camera], ecx=o)
        return parse_draw([r for r in m.gl if r[0] not in ('DRAW', 'END')])

    def render(self, state):
        """EffectManager render 0x00a7a30e; returns (drawn node pointers, per-draw records, envelope calls)."""
        m = self.m
        m.gl.clear()
        names = {0xbc0: 0, 0xde1: 1, 0xbe2: 2, 0xb72: 3, 0xbe1: 4, 0xbe0: 5}
        m.gl_values = {p: state[i] for p, i in names.items()}
        m.call(0x00a7a30e, [self.camera], ecx=self.manager)
        drawn, segments, envelope, current = [], [], [], None
        for record in m.gl:
            if record[0] == 'DRAW':
                if not drawn:
                    envelope.append(None)   # where the effect draws happen
                drawn.append(record[1])
                current = []
            elif record[0] == 'END':
                segments.append(current)
                current = None
            elif current is not None:
                current.append(record)
            else:
                a = record[1] if len(record) > 1 else 0
                b = record[2] if record[0] in ('glBindTexture', 'glBlendFunc') else 0
                envelope.append((OP[record[0]], a, b))
        envelope = [(DRAW_EFFECTS, len(drawn), 0) if e is None else e for e in envelope]
        return drawn, [parse_draw(s) for s in segments], envelope

    def particles(self, o):
        if self.m.r32(o) != 0x01a81d0c:
            return b''
        n = self.m.r32(o + 0xf4)
        return self.m.rb(self.m.r32(o + 0xf8), n * 0x88) if n else b''

    def state(self, o):
        m = self.m
        floats = m.rb(o + 0x58, 64) + m.rb(o + 0x38, 12) + m.rb(o + 0x54, 4) + m.rb(o + 0xe8, 8) + m.rb(o + 0x98, 24)
        drawn = m.rb(o + (0x114 if m.r32(o) == 0x01a81d0c else 0x144), 1)
        flags = m.rb(o + 0xd4, 1) + drawn + m.rb(o + 0xdf, 1) + b'\0'
        return floats, flags

    def cell(self, o):
        node = self.m.r32(o + 0xb0)
        if not node:
            return -1, b''
        return self.m.r32(node + 0x18), self.m.rb(node, 24)


class NativeLibrary:
    def __init__(self, path):
        lib = self.lib = ctypes.CDLL(str(path))
        P, F, U, V = ctypes.c_void_p, ctypes.c_float, ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)
        U32P = ctypes.POINTER(ctypes.c_uint32)
        I32P = ctypes.POINTER(ctypes.c_int32)
        sig = {
            'mu_fxt_new': (P, [U, ctypes.c_int]),
            'mu_fxt_add': (ctypes.c_int, [P, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]),
            'mu_fxt_close': (None, [P]),
            'mu_fxt_clone': (ctypes.c_int, [P, U, V, V, F, ctypes.c_int, I32P, U, F]),
            'mu_fxt_node_count': (U, [P]),
            'mu_fxt_node_type': (ctypes.c_int, [P, U]),
            'mu_fxt_set_transform': (None, [P, U, V, V, F]),
            'mu_fxt_set_owner': (None, [P, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, F, V]),
            'mu_fxt_set_gate': (ctypes.c_int, [P, U, ctypes.c_int, I32P, U, F]),
            'mu_fxt_update': (ctypes.c_int, [P, U, F, V]),
            'mu_fxt_draw': (U, [P, U, V, ctypes.c_int, P, U32P]),
            'mu_fxt_draw_frustum': (U, [P, U, ctypes.c_int, P, U32P]),
            'mu_fxt_particles': (P, [P, U, U32P]),
            'mu_fxt_node_state': (None, [P, U, V, ctypes.POINTER(ctypes.c_uint8)]),
            'mu_fxt_rand_calls': (ctypes.c_uint64, [P]),
            'mu_fxt_set_frustum': (None, [P, V, V, V, F, F, F, F, V]),
            'mu_fxt_query': (U, [P, U32P, U]),
            'mu_fxt_cell': (ctypes.c_int, [P, U, V]),
            'mu_fxt_render_calls': (U, [U32P, U, U32P]),
        }
        for name, (restype, argtypes) in sig.items():
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = restype, argtypes


def floats(values):
    return (ctypes.c_float * len(values))(*values)


class NativeScene:
    def __init__(self, library, seed, managed):
        self.lib = library.lib
        self.h = self.lib.mu_fxt_new(seed & 0xffffffff, int(managed))
        if not self.h:
            raise CaseError('native scene allocation failed')
        self.buffer = ctypes.create_string_buffer(36 * 4 * 4096)

    def close(self):
        self.lib.mu_fxt_close(self.h)

    def add(self, text):
        error = ctypes.create_string_buffer(256)
        raw = text.encode('latin1')
        r = self.lib.mu_fxt_add(self.h, raw, len(raw), error, 256)
        if r < 0:
            raise CaseError('native load failed: ' + error.value.decode())
        return r

    def draw(self, index, camera, texture):
        state = (ctypes.c_uint32 * 7)()
        if camera is None:
            n = self.lib.mu_fxt_draw_frustum(self.h, index, texture, self.buffer, state)
        else:
            n = self.lib.mu_fxt_draw(self.h, index, floats(camera), texture, self.buffer, state)
        return self.buffer.raw[:36 * n], list(state), n

    def particles(self, index):
        n = ctypes.c_uint32()
        p = self.lib.mu_fxt_particles(self.h, index, ctypes.byref(n))
        return ctypes.string_at(p, n.value * 0x88) if n.value else b''

    def state(self, index):
        out, flags = (ctypes.c_float * 28)(), (ctypes.c_uint8 * 4)()
        self.lib.mu_fxt_node_state(self.h, index, out, flags)
        return bytes(out), bytes(flags)

    def cell(self, index):
        box = (ctypes.c_float * 6)()
        depth = self.lib.mu_fxt_cell(self.h, index, box)
        return depth, bytes(box) if depth >= 0 else b''


def compare_bytes(a, b, result):
    if a != b:
        (a, nans), (b, _) = base.canonical_nan(a), base.canonical_nan(b)
        result['nan_words'] = result.get('nan_words', 0) + nans
    return a == b


def client_update(machine, client, r, dt, external):
    """Node update; returns False or a fault description for the emitter's rand() % 0."""
    try:
        client.update(r, dt, external)
        return False
    except CaseError as error:
        if 'UC_ERR_EXCEPTION' not in str(error) and '0xa80790' not in str(error):
            raise
        uc, x86 = machine.uc, machine.x86
        eip, ecx = uc.reg_read(x86.UC_X86_REG_EIP), uc.reg_read(x86.UC_X86_REG_ECX)
        divisor = struct.unpack('<I', uc.mem_read(ecx + 0xc, 4))[0]
        if eip != 0x00a80790 or divisor != 0:
            raise CaseError(f'unexpected stop {error} (eip {eip:#x}, divisor {divisor})') from None
        return f'#DE div by zero at {eip:#x}'


def run_case(machine, library, case):
    managed = case['kind'] == 'manager'
    client = ClientScene(machine, case['seed'], case['texture'], managed)
    native = NativeScene(library, case['seed'], managed)
    result = {'label': case['label'], 'kind': case['kind'], 'frames': 0, 'nodes': 0, 'node_states': 0,
              'vertices': 0, 'particles': 0, 'draws': 0, 'fault': None, 'mismatch': None}
    try:
        for text in case['texts']:
            client.add(text)
            native.add(text)
        for r, clone in enumerate(case.get('clones') or []):
            if clone is None:
                continue
            position, rotation, scale, tint, actions, start = clone
            client.clone(r, position, rotation, scale, tint, actions, start)
            acts = (ctypes.c_int32 * max(len(actions), 1))(*actions)
            if not native.lib.mu_fxt_clone(native.h, r, floats(position), floats(rotation), scale, tint, acts,
                                           len(actions), start):
                raise CaseError('native clone failed')
        nodes = client.nodes()
        count = native.lib.mu_fxt_node_count(native.h)
        if count != len(nodes):
            result['mismatch'] = f'node count {len(nodes)}/{count}'
            return result
        result['nodes'] = count
        index_of = {o: i for i, o in enumerate(nodes)}
        for k, o in enumerate(nodes):
            if (machine.r32(o) == 0x01a81d0c) != (native.lib.mu_fxt_node_type(native.h, k) == 0):
                result['mismatch'] = f'node {k} type'
                return result
        cloned = set()
        for r, clone in enumerate(case.get('clones') or []):
            if clone is not None:
                cloned.update(client.walk(client.roots[r], []))
        for k, o in enumerate(nodes):   # instance state straight after the clone: matrix, scale, times, playing
            if o not in cloned:
                continue
            cs, ns = client.state(o), native.state(k)
            if cs[0][:64] != ns[0][:64] or cs[0][76:88] != ns[0][76:88] or cs[1][0] != ns[1][0]:
                i = base.first_difference(cs[0], ns[0])
                result['mismatch'] = f'clone state node {k} float {i // 4} ' \
                                     f'{struct.unpack("<28f", cs[0])[i // 4] if i >= 0 else ""}/' \
                                     f'{struct.unpack("<28f", ns[0])[i // 4] if i >= 0 else ""} flags {cs[1].hex()}/{ns[1].hex()}'
                return result
            result['clone_states'] = result.get('clone_states', 0) + 1
        for k, transform in (case.get('transforms') or {}).items():
            position, rotation, scale = transform
            client.set_transform(nodes[k], position, rotation, scale)
            native.lib.mu_fxt_set_transform(native.h, k, floats(position), floats(rotation), scale)
        owner = case['owner'][0]
        client.set_owner(*owner, first=True)
        native.lib.mu_fxt_set_owner(native.h, owner[0], owner[1], owner[2], owner[3], owner[4], floats(owner[5]))
        for k, (tint, actions, start) in (case.get('gates') or {}).items():
            client.set_gate(nodes[k], tint, actions, start)
            acts = (ctypes.c_int32 * max(len(actions), 1))(*actions)
            native.lib.mu_fxt_set_gate(native.h, k, tint, acts, len(actions), start)
        machine.set_plane(0.0, 0.0, 0.0)
        camera = case['camera']
        frustum = case.get('frustum')
        if frustum:
            record = client.set_frustum(*frustum)
            native_record = (ctypes.c_float * 36)()
            native.lib.mu_fxt_set_frustum(native.h, floats(frustum[0]), floats(frustum[1]), floats(frustum[2]),
                                          frustum[3], frustum[4], frustum[5], frustum[6], native_record)
            if record != bytes(native_record):
                result['mismatch'] = f'frustum record byte {base.first_difference(record, bytes(native_record))}'
                return result
            result['frustum_records'] = 1
        else:
            client.set_camera(camera[0:3], camera[3:6], camera[6:9])
        for frame in range(case['frames']):
            if frame:
                owner = case['owner'][frame % len(case['owner'])]
                client.set_owner(*owner, first=False)
                native.lib.mu_fxt_set_owner(native.h, owner[0], owner[1], owner[2], owner[3], owner[4],
                                            floats(owner[5]))
            fault = None
            for r in range(len(case['texts'])):
                external = (case.get('externals') or [None] * len(case['texts']))[r]
                client_fault = client_update(machine, client, r, case['dt'], external)
                ext = floats(external) if external is not None else None
                native_ok = native.lib.mu_fxt_update(native.h, r, case['dt'], ext)
                if client_fault or not native_ok:
                    fault = {'frame': frame, 'root': r, 'client': client_fault or False, 'native': not native_ok}
                    break
            if fault:
                result['fault'] = fault
                if not (fault['client'] and fault['native']):
                    result['mismatch'] = 'fault'
                elif machine.rand_calls != native.lib.mu_fxt_rand_calls(native.h):
                    result['mismatch'] = 'rand-calls-at-fault'
                break
            for k, o in enumerate(nodes):
                cp, np_ = client.particles(o), native.particles(k)
                if not compare_bytes(cp, np_, result):
                    i = base.first_difference(cp, np_)
                    result['mismatch'] = f'particles frame {frame} node {k} byte {i} (field {i % 0x88:#x}) ' \
                                         f'counts {len(cp) // 0x88}/{len(np_) // 0x88}'
                    return result
                cs, ns = client.state(o), native.state(k)
                if not compare_bytes(cs[0], ns[0], result) or cs[1][0] != ns[1][0] or cs[1][2] != ns[1][2]:
                    i = base.first_difference(cs[0], ns[0])
                    result['mismatch'] = f'node state frame {frame} node {k} float {i // 4} flags ' \
                                         f'{cs[1].hex()}/{ns[1].hex()}'
                    return result
                result['node_states'] += 1
                result['particles'] += len(np_) // 0x88
                if managed:
                    cc, nc = client.cell(o), native.cell(k)
                    if cc != nc:
                        result['mismatch'] = f'octree cell frame {frame} node {k}: depth {cc[0]}/{nc[0]}'
                        return result
                    result['cells'] = result.get('cells', 0) + 1
            if managed:
                state = case['gl_state']
                drawn, segments, envelope = client.render(state)
                capacity = 4096
                indices = (ctypes.c_uint32 * capacity)()
                n = native.lib.mu_fxt_query(native.h, indices, capacity)
                native_order = list(indices[:n])
                client_order = [index_of.get(o, -1) for o in drawn]
                if client_order != native_order:
                    result['mismatch'] = f'visible order frame {frame}: {client_order[:12]} / {native_order[:12]}'
                    return result
                calls = (ctypes.c_uint32 * 72)()
                m = native.lib.mu_fxt_render_calls((ctypes.c_uint32 * 6)(*state), n, calls)
                native_envelope = [tuple(calls[3 * i:3 * i + 3]) for i in range(m)]
                if envelope != native_envelope:
                    result['mismatch'] = f'render calls frame {frame}: {envelope} / {native_envelope}'
                    return result
                result['render_passes'] = result.get('render_passes', 0) + 1
                result['visible'] = result.get('visible', 0) + n
                for k, (cv, cs, cn) in zip(native_order, segments):
                    nv, ns, nn = native.draw(k, None, case['texture'])
                    if not compare_bytes(cv, nv, result) or cn != nn or cs != ns:
                        result['mismatch'] = f'render draw frame {frame} node {k}'
                        return result
                    result['draws'] += 1
                    result['vertices'] += nn
                drawn_set = set(native_order)
                for k, o in enumerate(nodes):   # effects outside the view are not drawn this frame
                    if k not in drawn_set:
                        continue
            else:
                for k, o in enumerate(nodes):
                    cv, cs, cn = client.draw(o)
                    nv, ns, nn = native.draw(k, camera, case['texture'])
                    if not compare_bytes(cv, nv, result) or cn != nn:
                        result['mismatch'] = f'vertices frame {frame} node {k} byte {base.first_difference(cv, nv)}'
                        return result
                    if cs != ns:
                        result['mismatch'] = f'draw state frame {frame} node {k}: client {cs} native {ns}'
                        return result
                    result['draws'] += 1
                    result['vertices'] += nn
            for k, o in enumerate(nodes):   # the drawn flags after the draws
                if client.state(o)[1][1] != native.state(k)[1][1]:
                    result['mismatch'] = f'drawn flag frame {frame} node {k}'
                    return result
            if machine.rand_calls != native.lib.mu_fxt_rand_calls(native.h):
                result['mismatch'] = f'rand calls frame {frame}: {machine.rand_calls}/' \
                                     f'{native.lib.mu_fxt_rand_calls(native.h)}'
                return result
            result['frames'] += 1
    finally:
        native.close()
        result['rand_calls'] = machine.rand_calls
    return result


def texture_uploads(machine, library):
    """The effect texture upload 0x00a90987 for every filter/wrap/mipmap combination and the refused inputs."""
    m, lib, compared = machine, library.lib, 0
    lib.mu_fxt_texture_calls.restype = ctypes.c_uint32
    lib.mu_fxt_texture_calls.argtypes = [ctypes.c_int, ctypes.c_int32, ctypes.c_int32, ctypes.c_uint32,
                                         ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int,
                                         ctypes.POINTER(ctypes.c_uint32)]
    cases = [(1, w, h, f, flt, wrap, mip) for (w, h) in ((64, 32), (256, 256)) for f in (0x1907, 0x1908)
             for flt in (0x2601, 0x2600) for wrap in (0x2901, 0x812f) for mip in (0, 1)]
    cases += [(0, 64, 64, 0x1908, 0x2601, 0x2901, 0), (1, 0, 64, 0x1908, 0x2601, 0x2901, 0),
              (1, 64, 0, 0x1908, 0x2601, 0x2901, 1)]
    for has_pixels, w, h, f, flt, wrap, mip in cases:
        m.reset()
        pixels = m.alloc(16) if has_pixels else 0
        m.call(TEXTURE_UPLOAD, [pixels, w, h, f, flt, wrap, mip])
        client = []
        for record in m.gl:
            op = TEXTURE_OPS[record[0]]
            a = record[1] if len(record) > 1 else 0
            b = record[2] if len(record) > 2 else 0
            if record[0] == 'glBindTexture':
                b = NEW_TEXTURE if b == TEXTURE_NAME else b
            if record[0] in ('glGenTextures',):
                b = 0
            client.append((op, a, b))
        out = (ctypes.c_uint32 * 36)()
        n = lib.mu_fxt_texture_calls(has_pixels, w, h, f, flt, wrap, mip, out)
        native = [tuple(out[3 * i:3 * i + 3]) for i in range(n)]
        if client != native:
            return compared, f'texture upload {has_pixels, w, h, f, flt, wrap, mip}: {client} / {native}'
        compared += 1
    return compared, None


# ---- case generation ----

def nodes_of(document):
    out = [document]
    for child in document.get('Children') or []:
        if child.get('Type') in (0, 1):
            out.extend(nodes_of(child))
    return out


def mutate_tree(document, generator):
    """FX-001 parameter mutation on every node, plus child transforms, parentduration and looping."""
    d = base.mutate(document, generator)
    children = []
    for child in document.get('Children') or []:
        c = mutate_tree(child, generator)
        if generator.random() < 0.7:
            c['Position'] = [generator.uniform(-2, 2) for _ in range(3)]
            c['Rotation'] = [generator.uniform(-3.2, 3.2) if generator.random() < 0.5 else 0.0 for _ in range(3)]
            c['Scale'] = generator.choice([0.3, 1.0, 1.0, 2.5, 10.0])
        c['parentduration'] = generator.random() < 0.4
        if generator.random() < 0.3:
            c['Duration'] = generator.choice([0.3, 1.0, 2.0])
        children.append(c)
    if children:
        d['Children'] = children
    return d


def random_matrix(generator):
    if generator.random() < 0.2:
        return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
    import math
    a, b, c = (generator.uniform(-3.2, 3.2) for _ in range(3))
    s = generator.choice([0.5, 1.0, 1.0, 1.6])
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    rz = [[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]]
    ry = [[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]
    rx = [[1, 0, 0], [0, cc, -sc], [0, sc, cc]]
    mul = lambda p, q: [[sum(p[i][k] * q[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    r = mul(mul(rz, ry), rx)
    t = [generator.uniform(-5, 5) for _ in range(3)]
    m = [0.0] * 16
    for col in range(3):
        for row in range(3):
            m[4 * col + row] = r[row][col] * s
    m[12:15] = t
    m[15] = 1.0
    return [f32(v) for v in m]


def owner_track(generator, frames, varied):
    tint = [f32(generator.uniform(0, 1.5)) for _ in range(3)]
    flags = (int(generator.random() < 0.8), int(generator.random() < 0.8)) if varied else (0, 0)
    track, action, frame = [], generator.randrange(4), 0.0
    for _ in range(frames):
        if varied and generator.random() < 0.15:
            action = generator.randrange(4)
            frame = 0.0
        frame = f32(frame + 0.5)
        visible = 0 if varied and generator.random() < 0.08 else 1
        track.append((flags[0], flags[1], action, visible, frame if varied else 0.0, tint))
    return track


def gates_for(generator, count):
    gates = {}
    for k in range(count):
        if generator.random() < 0.5:
            actions = generator.sample(range(4), generator.randrange(0, 3))
            gates[k] = (int(generator.random() < 0.5), actions, f32(generator.choice([0.0, 1.0, 2.5, -1.5, -4.0])))
    return gates


def build_cases(game_root, frames, mutations, clones, scenes, seed, limit):
    generator = random.Random(seed)
    files = sorted((Path(game_root) / 'Data' / 'Effect').glob('*.ein'))
    if limit:
        files = files[:limit]
    documents = [(p.name, json.loads(p.read_bytes().decode('latin1'))) for p in files]
    with_children = [(n, d) for n, d in documents if d.get('Children')] or documents
    cases = []
    for path in files:
        text = path.read_bytes().decode('latin1')
        cases.append({'kind': 'tree', 'label': path.name, 'texts': [text], 'seed': 1, 'frames': frames, 'dt': 0.1,
                      'camera': base.DEFAULT_CAMERA, 'texture': 0,
                      'owner': [(0, 0, 0, 1, 0.0, (1.0, 1.0, 1.0))]})
    for index in range(mutations):
        name, document = (with_children if index % 3 else documents)[generator.randrange(
            len(with_children) if index % 3 else len(documents))]
        mutated = mutate_tree(document, generator)
        count = len(nodes_of(mutated))
        transforms = {}
        if generator.random() < 0.6:
            transforms[0] = ([f32(generator.uniform(-3, 3)) for _ in range(3)],
                             [f32(generator.uniform(-3.2, 3.2)) for _ in range(3)],
                             f32(generator.choice([0.5, 1.0, 1.7, 3.0])))
        cases.append({'kind': 'tree', 'label': f'mutation-{index}-{name}', 'texts': [json.dumps(mutated, indent=1)],
                      'seed': generator.randrange(1 << 31), 'frames': frames,
                      'dt': f32(generator.choice([0.04, 0.1, 0.1, 0.25])), 'camera': base.camera_for(generator),
                      'texture': generator.randrange(2), 'transforms': transforms,
                      'externals': [random_matrix(generator) if generator.random() < 0.5 else None],
                      'owner': owner_track(generator, frames, True), 'gates': gates_for(generator, count)})
    for index in range(clones):
        name, document = with_children[generator.randrange(len(with_children))] if index % 2 else \
            documents[generator.randrange(len(documents))]
        if index % 4 == 3:
            document = mutate_tree(document, generator)
        clone = ([f32(generator.uniform(-4, 4)) for _ in range(3)],
                 [f32(generator.uniform(-3.2, 3.2)) if generator.random() < 0.5 else 0.0 for _ in range(3)],
                 f32(generator.choice([0.5, 1.0, 2.0, 9.0])), generator.randrange(2),
                 generator.sample(range(4), generator.randrange(0, 3)),
                 f32(generator.choice([0.0, 1.0, 2.5, -1.5])))
        cases.append({'kind': 'clone', 'label': f'clone-{index}-{name}', 'texts': [json.dumps(document, indent=1)],
                      'clones': [clone], 'seed': generator.randrange(1 << 31), 'frames': frames,
                      'dt': f32(generator.choice([0.04, 0.1, 0.25])), 'camera': base.camera_for(generator),
                      'texture': generator.randrange(2),
                      'externals': [random_matrix(generator) if generator.random() < 0.4 else None],
                      'owner': owner_track(generator, frames, True)})
    for index in range(scenes):
        count = generator.randrange(2, 7)
        picks = [documents[generator.randrange(len(documents))] for _ in range(count)]
        texts = [json.dumps(mutate_tree(d, generator) if generator.random() < 0.3 else d, indent=1) for _, d in picks]
        centre = [12750.0 + generator.uniform(-6000, 6000), 12750.0 + generator.uniform(-6000, 6000),
                  generator.uniform(-100, 300)]
        externals, clone_list, transforms = [], [], {}
        for r in range(count):
            spread = generator.choice([30.0, 300.0, 1500.0, 30000.0])
            position = [f32(centre[0] + generator.uniform(-spread, spread)),
                        f32(centre[1] + generator.uniform(-spread, spread)),
                        f32(centre[2] + generator.uniform(-spread / 10, spread / 10))]
            scale = f32(generator.choice([1.0, 10.0, 40.0, 100.0]))
            if generator.random() < 0.5:   # factory path: an instance of the loaded template
                clone_list.append((position, [0.0, 0.0, f32(generator.uniform(-3, 3))], scale, 0, [], 0.0))
                externals.append(None)
            else:                           # owner path: world matrix of the owner (scale and translation)
                clone_list.append(None)
                m = [scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, scale, 0, position[0], position[1], position[2], 1.0]
                externals.append([f32(v) for v in m])
        eye = [f32(centre[0] + generator.uniform(-1500, 1500)), f32(centre[1] + generator.uniform(-1500, 1500)),
               f32(centre[2] + generator.uniform(400, 1500))]
        target = [centre[0] + generator.uniform(-300, 300), centre[1] + generator.uniform(-300, 300), centre[2]]
        forward = [t - e for t, e in zip(target, eye)]
        length = sum(v * v for v in forward) ** 0.5
        forward = [f32(v / length) for v in forward]
        up = [0.0, 0.0, 1.0]
        dot = sum(a * b for a, b in zip(forward, up))
        up = [u - dot * f for u, f in zip(up, forward)]
        length = sum(v * v for v in up) ** 0.5
        up = [f32(v / length) for v in up]
        frustum = (eye, forward, up, f32(generator.uniform(0.4, 1.4)), f32(generator.choice([4 / 3, 16 / 9, 1.0])),
                   f32(generator.choice([10.0, 20.0, 50.0])), f32(generator.choice([2000.0, 3000.0, 6000.0])))
        gl_state = [generator.randrange(2), generator.randrange(2), generator.randrange(2), generator.randrange(2),
                    generator.choice([0x302, 1, 0x306, 0x300]), generator.choice([0x303, 1, 0])]
        cases.append({'kind': 'manager', 'label': f'scene-{index}', 'texts': texts, 'clones': clone_list,
                      'seed': generator.randrange(1 << 31), 'frames': max(frames // 2, 4), 'dt': 0.1,
                      'camera': None, 'frustum': frustum, 'texture': generator.randrange(2),
                      'externals': externals, 'transforms': transforms, 'gl_state': gl_state,
                      'owner': owner_track(generator, frames, False)})
    return cases


def validate(args):
    text = base.load_pinned(args.text, base.TEXT_BYTES, base.TEXT_SHA256, 'restored text')
    data = base.load_pinned(args.data, base.DATA_BYTES, base.DATA_SHA256, 'image data')
    sec3 = base.load_pinned(args.section3, None, base.SEC3_SHA256, 'section-3 capture')[:base.SEC3_INIT_END -
                                                                                      base.SEC3_BASE]
    bodies = {name: hashlib.sha256(text[s - base.TEXT_BASE:e - base.TEXT_BASE]).hexdigest()
              for name, (s, e) in BODIES.items()}
    machine = TreeMachine(text, data, sec3)
    library = NativeLibrary(args.library)
    cases = build_cases(args.game_root, args.frames, args.mutations, args.clones, args.scenes, args.seed, args.limit)
    if args.only:
        cases = [c for c in cases if re.search(args.only, c['label'])]
    texture_compared, texture_mismatch = texture_uploads(machine, library)
    results = []
    if texture_mismatch:
        results.append({'label': 'texture-upload', 'kind': 'texture', 'mismatch': texture_mismatch})
    for case in cases:
        try:
            results.append(run_case(machine, library, case))
        except CaseError as error:
            if CRT_NAN in str(error):
                results.append({'label': case['label'], 'kind': case['kind'], 'skipped': CRT_NAN})
            else:
                results.append({'label': case['label'], 'kind': case['kind'], 'error': str(error),
                                'mismatch': 'error'})
        if args.verbose:
            print(json.dumps(results[-1]), file=sys.stderr)
    mismatches = [r for r in results if r.get('mismatch')]
    total = lambda key: sum(r.get(key, 0) or 0 for r in results)
    return {
        'text_sha256': base.TEXT_SHA256, 'data_sha256': base.DATA_SHA256,
        'section3_initialized_sha256': hashlib.sha256(sec3).hexdigest(), 'bodies': bodies,
        'library_sha256': hashlib.sha256(Path(args.library).read_bytes()).hexdigest(),
        'cases': len(results), 'cases_by_kind': {k: sum(1 for c in cases if c['kind'] == k)
                                                 for k in ('tree', 'clone', 'manager')},
        'installed_tree_cases': sum(1 for c in cases if c['kind'] == 'tree' and not c['label'].startswith('mutation')),
        'nodes': total('nodes'), 'frames_compared': total('frames'), 'node_states_compared': total('node_states'),
        'draws_compared': total('draws'), 'vertices_compared': total('vertices'),
        'particle_records_compared': total('particles'), 'octree_cells_compared': total('cells'),
        'render_passes_compared': total('render_passes'), 'visible_effects_compared': total('visible'),
        'frustum_records_compared': total('frustum_records'), 'texture_uploads_compared': texture_compared,
        'faults_matched': sum(1 for r in results if r.get('fault') and not r.get('mismatch')),
        'skipped_crt_nan': [r['label'] for r in results if r.get('skipped')],
        'nan_canonicalized_words': total('nan_words'), 'rand_calls': total('rand_calls'),
        'mismatches': len(mismatches), 'mismatch_examples': mismatches[:20],
        'mismatch_kinds': {k: sum(1 for r in mismatches if str(r.get('mismatch')).split(' ')[0] == k)
                           for k in sorted({str(r.get('mismatch')).split(' ')[0] for r in mismatches})},
        'effect_code_blocks_executed': len(machine.blocks), 'imports': machine.imports,
        'section3_undefined_read_sites': len(machine.undefined3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True, help='x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', type=Path, required=True, help='data-capture-10/client-image-data.bin')
    parser.add_argument('--section3', type=Path, required=True, help='x86-linux-capture-04/main-01ced000.bin')
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT / 'reconstructed/effects' /
                        ('libeffects.dylib' if sys.platform == 'darwin' else 'libeffects.so'))
    parser.add_argument('--limit', type=int, help='first N installed effects only')
    parser.add_argument('--frames', type=int, default=30)
    parser.add_argument('--mutations', type=int, default=300)
    parser.add_argument('--clones', type=int, default=200)
    parser.add_argument('--scenes', type=int, default=150)
    parser.add_argument('--seed', type=int, default=0x0a75708)
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
    print(json.dumps({k: summary[k] for k in ('cases', 'nodes', 'frames_compared', 'node_states_compared',
                                              'draws_compared', 'octree_cells_compared', 'render_passes_compared',
                                              'faults_matched', 'mismatches')}))
    return 1 if summary['mismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
