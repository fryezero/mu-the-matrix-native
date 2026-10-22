#!/usr/bin/env python3
"""Run the client's map and travel routines in Unicorn and compare them with reconstructed/map (NATIVE-MAP-001).

The pinned restored text (0x00401000) and second image section run in Unicorn
(scripts/client_ui_machine.py through validate_lang.LangMachine) with a
langread snapshot (NATIVE-LANG-001) mapped at its original addresses: the
GlobalText, Gate and movereq(kor) tables as the running client built them.
libmap (ctypes) is the C restatement.

Families:

* hud_update: the hudMap window's per-frame method 0x00c6af22 (hero marker
  rotation, map offset) over random hero positions, angles, cached values and
  value-defined flags; the SetDisplayInfo structs it commits are compared;
* units: the minimap records of opcode 0xE7 sub 3 / sub 4 (0x00c6b550,
  0x00c6b5c5) on random packets: the addUnit / delUnit invokes and members;
* detected: AddDetectedUnit 0x00c6b6c2 on random detector lists;
* show: the window's OnCall 0x00c6aba6 with "showMap" (the blocked areas
  0x00c6bc46, the notice, setShowMap, the E7 request) and "onLoad" (InitData);
* navimap: LoadWorldMap 0x00c6b116 for worlds 0..255 and both file answers;
* move_build: the move manager's constructor 0x00d3b4cb over random key lists
  of the snapshot's movereq table;
* move_sort: 0x00d3b325 for the three orders on built managers and on random
  synthetic entry vectors (ties, sizes 0..300);
* availability: 0x00bdc0c7(0) over random hero states (level, zen, PK, wings,
  helpers, server and event flags, strife flags);
* rows: the list builder 0x00bdd08d (SetMoveMapList rows) over random states;
* click: 0x00bdc813 (refusal, MU Helper rule, the BF 51 and 8E 02 packets);
* gates: the entrance test 0x016a4608 over the snapshot's Gate table with the
  hero on random entrance tiles (refusals, notices, LoadingWorld, request).

Modelled (not client code): operator new/delete (a bump heap), sprintf
0x009619dd (%s/%d), the GFx manager, windows and values (records), the packet
builder's send (bytes recorded), chat notices, the hero/character/item/helper
predicates the routines ask (random per case, given to both sides), the move
key transform 0x00cda52b (opaque: a random key) and GetTickCount.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402

MAPDIR = ROOT/'reconstructed/map'
HERO_PTR, WORLD, LOADING_WORLD = 0x0a39d754, 0x01cf15fc, 0x0b437c14
CHARATTR_PTR, CHARINFO_PTR, CHAT_PTR = 0x01d1df18, 0x01d1df1c, 0x01d22c6c
MOVE_MGR, MOVE_MGR_GUARD = 0x01d22d44, 0x01d22d48
MOVEREQ, GATE, GLOBALTEXT = 0x06fbb84c, 0x06fbabac, 0x06fbab48
SPRINTF = 0x009619dd
FAKE = 0x0be00000          # fake objects (bss, defined by the cases)


def i32(v):
    return struct.unpack('<i', struct.pack('<I', v & 0xffffffff))[0]


def f2u(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def u2f(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xffffffff))[0]


def d_of(b):
    return struct.unpack('<d', b)[0]


# ---- native library ---------------------------------------------------------------------------------------

class Unit(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('key', ctypes.c_int32), ('state', ctypes.c_int32), ('x', ctypes.c_float),
                ('y', ctypes.c_float), ('text', ctypes.c_char*64)]


class Hud(ctypes.Structure):
    _fields_ = [('shown', ctypes.c_uint8), ('available', ctypes.c_uint8), ('last_x', ctypes.c_float),
                ('last_y', ctypes.c_float), ('last_rotation', ctypes.c_float)]


class HudFrame(ctypes.Structure):
    _fields_ = [('set_rotation', ctypes.c_int), ('rotation', ctypes.c_double), ('set_position', ctypes.c_int),
                ('map_x', ctypes.c_double), ('map_y', ctypes.c_double)]


class ShowResult(ctypes.Structure):
    _fields_ = [('ignored', ctypes.c_int), ('notice', ctypes.c_int), ('set_show', ctypes.c_int), ('shown', ctypes.c_int),
                ('packet', ctypes.c_uint8*4), ('packet_length', ctypes.c_int)]


class MoveRecord(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int32), ('id', ctypes.c_int32), ('name', ctypes.c_char_p),
                ('server_name', ctypes.c_char_p), ('zen', ctypes.c_int32), ('min_level', ctypes.c_int32),
                ('max_level', ctypes.c_int32), ('gate', ctypes.c_int32), ('x44', ctypes.c_int32), ('x48', ctypes.c_int32),
                ('x4c', ctypes.c_int32)]


class MoveEntry(ctypes.Structure):
    _fields_ = [('key', ctypes.c_int32), ('x44', ctypes.c_int32), ('order', ctypes.c_int32), ('x48', ctypes.c_int32),
                ('key2', ctypes.c_int32), ('enabled', ctypes.c_uint8), ('strife', ctypes.c_uint8),
                ('clicked', ctypes.c_uint8), ('pad', ctypes.c_uint8)]


class MoveHero(ctypes.Structure):
    _fields_ = [('level', ctypes.c_int32), ('zen', ctypes.c_int32), ('pk_level', ctypes.c_uint8),
                ('strife_ok', ctypes.c_uint8), ('wings_slot', ctypes.c_uint8), ('helper_type', ctypes.c_int32),
                ('helper_flies', ctypes.c_uint8), ('flying', ctypes.c_int32), ('kalima', ctypes.c_uint8),
                ('server_flag', ctypes.c_uint8), ('event_a', ctypes.c_uint8), ('event_b', ctypes.c_uint8)]


class MoveRow(ctypes.Structure):
    _fields_ = [('order_idx', ctypes.c_int32), ('strife', ctypes.c_char*64), ('map', ctypes.c_char*64),
                ('level', ctypes.c_char*16), ('zen', ctypes.c_char*16), ('checked', ctypes.c_int),
                ('disabled', ctypes.c_int), ('map_idx', ctypes.c_int32)]


class ClickResult(ctypes.Structure):
    _fields_ = [('accepted', ctypes.c_int), ('helper_stop', ctypes.c_int), ('helper_packet', ctypes.c_int),
                ('packet', ctypes.c_uint8*16), ('packet_length', ctypes.c_int)]


class Gate(ctypes.Structure):
    _fields_ = [(n, ctypes.c_int32) for n in ('index', 'flag', 'world', 'x1', 'y1', 'x2', 'y2', 'target', 'dir',
                                              'min_level', 'max_level')]


class GateHero(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('tile_x', ctypes.c_int32), ('tile_y', ctypes.c_int32),
                ('level', ctypes.c_int32), ('loading_world', ctypes.c_int32), ('busy', ctypes.c_uint8),
                ('wings_kind6', ctypes.c_uint8), ('helper_type', ctypes.c_int32), ('helper_flies', ctypes.c_uint8),
                ('hero_3230', ctypes.c_int32), ('throttle', ctypes.c_uint8)]


class GateResult(ctypes.Structure):
    _fields_ = [('gate', ctypes.c_int), ('target', ctypes.c_int), ('refused', ctypes.c_int),
                ('loading_world', ctypes.c_int32), ('packet', ctypes.c_uint8*8), ('packet_length', ctypes.c_int),
                ('helper_stop', ctypes.c_int)]


LOOKUP_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
GATE_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)


class Native:
    def __init__(self, mutation=0, work=None):
        import subprocess
        if mutation:
            lib = Path(work)/f'libmap-m{mutation}.{"dylib" if sys.platform == "darwin" else "so"}'
            subprocess.run(['cc', '-std=c11', '-O2', '-fPIC', '-shared', '-ffp-contract=off', f'-DMU_MAP_MUTATION={mutation}',
                            *[str(MAPDIR/f) for f in ('map_hud.c', 'map_move.c', 'map_gate.c')], '-o', str(lib)], check=True)
        else:
            lib = MAPDIR/('libmap.dylib' if sys.platform == 'darwin' else 'libmap.so')
            subprocess.run(['make', '-s', '-C', str(MAPDIR)], check=True)
        L = self.L = ctypes.CDLL(str(lib))
        L.mu_map_navimap_name.argtypes = [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_map_px_x.restype = L.mu_map_px_y.restype = ctypes.c_float
        L.mu_map_px_x.argtypes = L.mu_map_px_y.argtypes = [ctypes.c_float]
        L.mu_map_hud_update.argtypes = [ctypes.POINTER(Hud), ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_float*2),
                                        ctypes.c_float, ctypes.POINTER(HudFrame)]
        L.mu_map_unit_packet.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int, ctypes.POINTER(Unit)]
        L.mu_map_detected_unit.argtypes = [ctypes.c_int32]*4 + [ctypes.POINTER(Unit)]
        L.mu_map_show.argtypes = [ctypes.POINTER(Hud), ctypes.c_int, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                                  ctypes.POINTER(ShowResult)]
        L.mu_move_build.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int, LOOKUP_FN, ctypes.c_void_p,
                                    ctypes.POINTER(MoveEntry), ctypes.c_int]
        L.mu_move_sort.argtypes = [ctypes.POINTER(MoveEntry), ctypes.c_int, ctypes.c_int32]
        L.mu_move_availability.argtypes = [ctypes.POINTER(MoveEntry), ctypes.c_int, ctypes.POINTER(MoveHero), LOOKUP_FN,
                                           TEXT_FN, ctypes.c_void_p]
        L.mu_move_row_make.argtypes = [ctypes.POINTER(MoveEntry), ctypes.c_int32, ctypes.POINTER(MoveHero), ctypes.c_int,
                                       LOOKUP_FN, TEXT_FN, ctypes.c_void_p, ctypes.POINTER(MoveRow)]
        L.mu_move_click.argtypes = [ctypes.POINTER(MoveEntry), ctypes.c_int, ctypes.c_int32, ctypes.c_int32, ctypes.c_int,
                                    ctypes.c_uint32, ctypes.POINTER(ClickResult)]
        L.mu_gate_check.argtypes = [ctypes.POINTER(Gate), ctypes.c_int, GATE_FN, ctypes.c_void_p,
                                    ctypes.POINTER(GateHero), ctypes.POINTER(GateResult)]


def unit_tuple(u):
    return (u.type, u.key, u.state, u.text.decode('latin1'), f2u(u.x), f2u(u.y))


# ---- the machine: GFx, packets, notices ------------------------------------------------------------------------

class World:
    """Host side of one case: GFx values, invokes, packets, notices."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.values, self.log, self.packets, self.flags = {}, [], {}, {}

    def new_value(self, kind):
        ident = len(self.values) + 1
        self.values[ident] = (kind, [] if kind == 'obj' else {})
        return ident


W = World()


def std_string_at(m, address):
    size, cap = struct.unpack('<II', m.read(address + 0x10, 8))
    if size > 0x10000 or cap < size:
        raise cm.CaseError(f'bad std::string at {address:#x}')
    return m.read(address if cap < 16 else m.u32(address), size)


def write_std_string(m, address, payload):
    payload = bytes(payload)
    if len(payload) < 16:
        m.write(address, payload + bytes(16 - len(payload)) + struct.pack('<II', len(payload), 15))
    else:
        buf = m.alloc(len(payload) + 1, define=True)
        m.write(buf, payload + b'\0')
        m.write(address, struct.pack('<I', buf) + bytes(12) + struct.pack('<II', len(payload), len(payload)))


SYNC_SLOTS = {0x1a7c1ec: 0, 0x1a7c28c: 4, 0x1a7c290: 4, 0x1a7c2ac: 4, 0x1a7c44c: 4, 0x1a7c450: 4, 0x1a7c4c0: 4}


def install_common(m):
    vl.heap_stubs(m)
    m.sync_stubs = {}
    for slot, cleanup in SYNC_SLOTS.items():   # locks and last-error (names: scripts/validate_effects.py IMPORTS)
        fn = m._new_stub()
        m.stub(fn, lambda mm: 0, cleanup)
        m.sync_stubs[slot] = fn

    def sprintf(mm):
        words = mm.args(12)
        buf, fmt = words[0], mm.cstr(words[1])
        out, i, k = bytearray(), 0, 2
        while i < len(fmt):
            if fmt[i:i+1] == b'%' and fmt[i+1:i+2] in (b's', b'd'):
                v = words[k]
                k += 1
                out += mm.cstr(v) if fmt[i+1:i+2] == b's' else b'%d' % i32(v)
                i += 2
            else:
                out.append(fmt[i])
                i += 1
        mm.write(buf, bytes(out) + b'\0')
        return len(out)
    m.stub(SPRINTF, sprintf, 0)

    # the window's GFx value calls (thiscall on the window)
    def obj_new(kind):
        def h(mm):
            out, = mm.args(1)
            mm.put32(out, W.new_value(kind))   # the value's first word holds our id
            return out
        return h
    m.stub(0x00c8f5f4, obj_new('obj'), 4)
    m.stub(0x00c8f9cf, obj_new('arr'), 4)
    m.stub(0x00aaf1c5, obj_new('obj'), 4)
    m.stub(0x00aaf205, obj_new('arr'), 4)
    m.stub(0x00aad26b, lambda mm: 0, 0)
    m.stub(0x00aad299, lambda mm: 0, 0)

    def member(kind):
        def h(mm):
            value, name, v = mm.args(3)
            node = W.values[mm.u32(value)]
            if kind == 's':
                payload = ('s', mm.cstr(v).decode('latin1'))
            elif kind == 'i':
                payload = ('i', i32(v))
            elif kind == 'f':
                payload = ('f', v)
            elif kind == 'b':
                payload = ('b', mm.read(v, 1)[0])
            else:   # int through a pointer
                payload = ('i', i32(mm.u32(v)))
            node[1].append((mm.cstr(name).decode(), payload))
            return 0
        return h
    m.stub(0x00ae94c9, member('s'), 12)
    m.stub(0x00ae957f, member('i'), 12)
    m.stub(0x00aeb026, member('f'), 12)
    m.stub(0x00b0809d, member('s'), 12)
    m.stub(0x00b0bc6f, member('b'), 12)
    m.stub(0x00b2ced7, member('p'), 12)

    def set_element(cleanup_args):
        def h(mm):
            if cleanup_args == 3:     # 0x00b48b7e(array, index, value)
                arr, index, value = mm.args(3)
            else:                     # 0x00ab27a6(index, value) on the array value
                arr = mm.uc.reg_read(cm.UC_X86_REG_ECX)
                index, value = mm.args(2)
            W.values[mm.u32(arr)][1][index] = render(mm.u32(value))
            return 0
        return h
    m.stub(0x00b48b7e, set_element(3), 12)
    m.stub(0x00ab27a6, set_element(2), 8)
    m.stub(0x00ab2788, lambda mm: 0, 4)

    def invoke_value(mm):
        method, value = mm.args(2)
        W.log.append(('invoke', mm.cstr(method).decode(), render(mm.u32(value))))
        return 0
    m.stub(0x00c8fac2, invoke_value, 8)
    m.stub(0x00aaf3ef, invoke_value, 8)
    m.stub(0x00c8f9e8, lambda mm: W.log.append(('invoke', mm.cstr(mm.args(1)[0]).decode(), None)) or 0, 4)

    def invoke_bool(mm):
        method, b = mm.args(2)
        W.log.append(('invoke', mm.cstr(method).decode(), b & 0xff))
        return 0
    m.stub(0x00ae48dc, invoke_bool, 8)

    def invoke_fmt(mm):
        words = mm.args(8)
        method, fmt = mm.cstr(words[1]).decode(), mm.cstr(words[2])
        args, k = [], 3
        for token in fmt.split():
            args.append(i32(words[k]) if token == b'%d' else mm.cstr(words[k]).decode('latin1'))
            k += 1
        W.log.append(('invoke', method, tuple(args)))
        return 0
    m.stub(0x00aae7e0, invoke_fmt, 0)

    # packets: the builder's body bytes (as scripts/validate_quest.py)
    def builder_init(mm):
        W.packets[mm.uc.reg_read(cm.UC_X86_REG_ECX)] = bytearray()
        return 0
    m.stub(0x00d52133, builder_init, 0)

    def builder_add(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        p, n, _ = mm.args(3)
        W.packets.setdefault(this, bytearray()).extend(mm.read(p, n))
        return 0
    m.stub(0x00d51c9b, builder_add, 0xc)

    def builder_send(mm):
        this = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        body = bytearray(W.packets.get(this, b''))
        if len(body) >= 2:
            body[1] = len(body)
        W.log.append(('send', bytes(body).hex()))
        return 0
    m.stub(0x00d51d4f, builder_send, 8)

    # chat notices: [0x01d22c6c] -> 0x0095f136 (real: the object) -> 0x0095f547 / 0x0095f4ec(std::string)
    def notice(mm):
        s, = mm.args(1)
        W.log.append(('notice', std_string_at(mm, s).decode('latin1')))
        return 0
    m.stub(0x0095f547, notice, 4)
    m.stub(0x0095f4ec, notice, 4)


def render(ident):
    node = W.values.get(ident)
    if node is None:
        return ('?', ident)
    if node[0] == 'obj':
        return tuple(node[1])
    return tuple(node[1].get(i) for i in range(max(node[1]) + 1 if node[1] else 0))


def prepare(m):
    m.prepare(force=True)
    vl.crt_state(m)
    W.reset()
    m.put32(CHAT_PTR, FAKE + 0x100)          # the chat object (0x0095f136 reads [this])
    m.put32(FAKE + 0x100, FAKE + 0x200)
    m.put32(MOVE_MGR_GUARD, 0)                # the move manager's static is initialised
    m.write(0x0bdd2000, b'\xff' * 0x80)      # the UCRT's cached API pointers: "not available" (its fallbacks run)
    for slot, fn in m.sync_stubs.items():
        m.put32(slot, fn)


# ---- hud families ------------------------------------------------------------------------------------------------

UPDATE, UNIT_3, UNIT_4, DETECTED, ONCALL, LOAD_MAP, INIT_DATA = (0x00c6af22, 0x00c6b550, 0x00c6b5c5, 0x00c6b6c2,
                                                                0x00c6aba6, 0x00c6b116, 0x00c6b89f)


def window(m):
    """A fake hudMap window object: +0x20 hero value, +0x30 map value, the state bytes."""
    w = m.alloc(0x100, define=True)
    m.write(w, bytes(0x100))
    return w


def hud_floats(rng):
    pick = rng.random()
    if pick < 0.1:
        return rng.choice([0.0, -0.0, 25600.0, 12750.0, float('nan'), 1e-30])
    if pick < 0.2:
        return float(rng.randint(0, 255) * 100 + 50)
    return rng.uniform(-1000.0, 26000.0)


def run_hud_update(m, nat, rng, fam, cases):
    hero = FAKE + 0x1000
    commits = []

    def commit(mm):
        di, = mm.args(1)
        target = mm.uc.reg_read(cm.UC_X86_REG_ECX)
        flags = struct.unpack('<H', mm.read(di + 0xe0, 2))[0]
        rec = [target - W.window, flags]
        if flags & 1:
            rec.append(('x', mm.read(di, 8).hex()))
        if flags & 2:
            rec.append(('y', mm.read(di + 8, 8).hex()))
        if flags & 4:
            rec.append(('r', mm.read(di + 0x10, 8).hex()))
        commits.append(tuple(rec))
        return 0
    m.stub(0x00aad3e0, commit, 4)
    for case in range(cases):
        prepare(m)
        commits.clear()
        W.window = w = window(m)
        shown = rng.random() < 0.85
        hero_valid, map_valid = rng.random() < 0.85, rng.random() < 0.85
        m.stub(0x00aad348, (lambda hv, mv: lambda mm: (hv if mm.uc.reg_read(cm.UC_X86_REG_ECX) == W.window + 0x20 else mv))(
            int(hero_valid), int(map_valid)), 0)
        pos = [hud_floats(rng), hud_floats(rng)]
        angle = rng.choice([rng.uniform(-720, 720), 0.0, 45.0, float(rng.randint(0, 7) * 45)])
        last = [hud_floats(rng), hud_floats(rng), rng.uniform(-500, 500)]
        if rng.random() < 0.3:
            last[0], last[1] = pos
        if rng.random() < 0.3:
            last[2] = u2f(f2u(-angle + 225.0)) if not (angle != angle) else last[2]
        m.write(w + 0x4c, bytes([int(shown)]))
        m.write(w + 0x40, struct.pack('<fff', *last))
        m.put32(HERO_PTR, hero)
        m.write(hero + 0x33ac, struct.pack('<fff', pos[0], pos[1], 0.0))
        m.write(hero + 0x33b8, struct.pack('<fff', 0.0, 0.0, angle))
        m.call(UPDATE, [], ecx=w)
        client = (commits[:], m.read(w + 0x40, 12).hex())
        h = Hud(shown=int(shown), available=0, last_x=last[0], last_y=last[1], last_rotation=last[2])
        out = HudFrame()
        nat.L.mu_map_hud_update(ctypes.byref(h), int(hero_valid), int(map_valid),
                                ctypes.byref((ctypes.c_float*2)(*pos)), angle, ctypes.byref(out))
        native = []
        if out.set_rotation:
            native.append((0x20, 4, ('r', struct.pack('<d', out.rotation).hex())))
        if out.set_position:
            native.append((0x30, 3, ('x', struct.pack('<d', out.map_x).hex()), ('y', struct.pack('<d', out.map_y).hex())))
        native = (native, struct.pack('<fff', h.last_x, h.last_y, h.last_rotation).hex())
        fam.check(case, client, native)


def random_unit_packet(rng):
    p = bytearray(rng.randrange(256) for _ in range(rng.choice([11, 12, 20, 30, 40])))
    p[0], p[2], p[3] = 0xc1, 0xe7, 3
    p[7] = rng.choice([0, 0, 0, 1, 1, 2, rng.randrange(256)])
    if rng.random() < 0.8:   # a name of printable bytes, NUL-terminated within the packet
        n = rng.randint(0, len(p) - 11)
        p[10:10 + n] = bytes(rng.randint(0x20, 0x7e) for _ in range(n))
        p[10 + n] = 0
    p[1] = len(p)
    return bytes(p)


def logged_unit(entry):
    kind, method, members = entry
    out = {k: v for k, v in members}
    return (method, out.get('type', ('i', None))[1], out.get('key', ('i', None))[1], out.get('state', ('i', None))[1],
            out.get('text', ('s', None))[1], out.get('x', ('f', None))[1], out.get('y', ('f', None))[1])


def run_units(m, nat, rng, fam, cases):
    for case in range(cases):
        prepare(m)
        w = window(m)
        p = random_unit_packet(rng)
        with_name = rng.random() < 0.5
        buf = m.alloc(len(p) + 16, define=True)
        m.write(buf, p + bytes(16))
        m.call(UNIT_3 if with_name else UNIT_4, [buf], ecx=w)
        client = [logged_unit(e) for e in W.log if e[0] == 'invoke']
        u = Unit()
        r = nat.L.mu_map_unit_packet(p, len(p), int(with_name), ctypes.byref(u))
        if r == 1:
            native = [('addUnit', u.type, u.key, u.state, u.text.decode('latin1'), f2u(u.x), f2u(u.y))]
        elif r == 2:
            native = [('delUnit', u.type, u.key, None, None, None, None)]
        else:
            native = []
        fam.check(p.hex(), client, native)


def run_detected(m, nat, rng, fam, cases):
    for case in range(cases):
        prepare(m)
        w = window(m)
        n = rng.choice([0, 1, 2, 5, rng.randint(0, 40)])
        elems = [(rng.choice([0, 1, 2, rng.randint(-3, 9)]), rng.randint(-10, 300), rng.randint(-10, 300)) for _ in range(n)]
        vec = m.alloc(max(12 * n, 4), define=True)
        for i, e in enumerate(elems):
            m.write(vec + 12 * i, struct.pack('<iii', *e))
        m.call(DETECTED, [vec, vec + 12 * n, vec + 12 * n], ecx=w)
        client = [(e[1], e[2]) for e in W.log if e[0] == 'invoke']
        native = []
        if n:
            arr = []
            for i, (k, x, y) in enumerate(elems):
                u = Unit()
                nat.L.mu_map_detected_unit(i, k, x, y, ctypes.byref(u))
                arr.append((('type', ('i', u.type)), ('key', ('i', u.key)), ('state', ('i', u.state)),
                            ('text', ('s', u.text.decode())), ('x', ('f', f2u(u.x))), ('y', ('f', f2u(u.y)))))
            native = [('AddDetectedUnit', tuple(arr))]
        fam.check(case, client, native)


def run_show(m, nat, rng, fam, cases, snap):
    hero = FAKE + 0x1000
    # the "onLoad" event: InitData
    prepare(m)
    w = window(m)
    name = m.alloc(0x20, define=True)
    write_std_string(m, name, b'onLoad')
    m.stub(0x00aad487, lambda mm: 0, 0)
    m.call(ONCALL, [name, m.alloc(16, define=True)], ecx=w)
    client = W.log[:]
    gt = lambda i: text_of(snap, i)   # noqa: E731
    native = [('invoke', 'InitData', (('MaxPartyCount', ('i', 5)),) + tuple(
        (mname, ('s', gt(t))) for mname, t in zip(
            [n.decode() for n in (ctypes.c_char_p*10).in_dll(nat.L, 'mu_map_init_members')],
            list((ctypes.c_int32*10).in_dll(nat.L, 'mu_map_init_text')))))]
    fam.check('onLoad', client, native)
    for case in range(cases):
        prepare(m)
        w = window(m)
        write_std_string(m, name, b'showMap')
        show = rng.random() < 0.7
        world = rng.choice([0x72, 0x73, 0x4f, 0x4f, 0x72, 0, rng.randint(0, 150)])
        x, y = rng.randint(0, 255), rng.randint(0, 255)
        if rng.random() < 0.5:
            x, y = rng.choice([(rng.randint(0xe8, 0xf9), rng.randint(0xe7, 0xf6)), (rng.randint(0x6d, 0x7f), rng.randint(0xe7, 0xf7)),
                               (0xb6, rng.randint(0xe2, 0xfc)), (rng.randint(0x10, 0x24), rng.randint(0xe2, 0xf6)),
                               (rng.randint(0x34, 0x4b), rng.randint(0xe4, 0xfa)), (rng.randint(0x30, 0x50), rng.randint(0xe0, 0xff))])
        available, shown = rng.random() < 0.7, rng.random() < 0.5
        m.put32(WORLD, world)
        m.put32(HERO_PTR, hero)
        m.put32(hero + 0x180, x)
        m.put32(hero + 0x184, y)
        m.write(w + 0x4c, bytes([int(shown), 0, int(available)]))
        m.stub(0x00aad487, (lambda b: lambda mm: b)(int(show)), 0)
        m.call(ONCALL, [name, m.alloc(16, define=True)], ecx=w)
        client = (W.log[:], m.read(w + 0x4c, 1)[0])
        h = Hud(shown=int(shown), available=int(available))
        out = ShowResult()
        nat.L.mu_map_show(ctypes.byref(h), int(show), world, x, y, ctypes.byref(out))
        native = []
        if out.notice:
            native.append(('notice', text_of(snap, 0x1076)))
        if out.set_show:
            native.append(('invoke', 'setShowMap', out.shown))
            native.append(('send', bytes(out.packet[:out.packet_length]).hex()))
        fam.check((show, world, x, y, available), client, (native, h.shown))


def text_of(snap, index):
    """GlobalText[index] as the client returns it (the snapshot's record, else the client's error text)."""
    cache = TEXT_CACHE.setdefault(id(snap), {})
    if 'map' not in cache:
        cache['map'] = {key: snap.string(node + 0x14 + 8) for key, node in snap.tree(plain.TEXT + 0x38)}
    s = cache['map'].get(index)
    return s.decode('latin1') if s is not None else f'[Text] error index : {index}'


TEXT_CACHE = {}


def run_navimap(m, nat, rng, fam):
    exists = {}

    def attributes(mm):
        path, = mm.args(1)
        name = mm.cstr(path).decode('latin1')
        W.log.append(('file', name))
        return 1 if exists['v'] else 0
    slot = 0x01a7c7a0
    fn = m._new_stub()
    m.stub(fn, attributes, 4)
    for world in list(range(0, 256)) + [-1, 999]:
        for e in (0, 1):
            prepare(m)
            m.put32(slot, fn)
            exists['v'] = e
            w = window(m)
            m.put32(WORLD, world)
            m.call(LOAD_MAP, [], ecx=w)
            client = (W.log[:], m.read(w + 0x4e, 1)[0])
            buf = ctypes.create_string_buffer(64)
            nat.L.mu_map_navimap_name(world, buf, 64)
            name = buf.value.decode()
            native = [('file', './Data/Interface/GFx/Navimap/' + name)]
            if e:
                native.append(('invoke', 'LoadWorldMap', (('fileName', ('s', name)),)))
            fam.check((world, e), client, (native, e))


# ---- move window families -------------------------------------------------------------------------------------

MOVE_CTOR, MOVE_SORT, MOVE_AVAIL, MOVE_ROWS, MOVE_CLICK = 0x00d3b4cb, 0x00d3b325, 0x00bdc0c7, 0x00bdd08d, 0x00bdc813


class Tables:
    """The snapshot's movereq and Gate tables as libmap records, and GlobalText for the callbacks."""

    def __init__(self, snap):
        self.snap = snap
        self.moves = plain.read_moves(snap)
        self.recs, self.keep = {}, []
        for r in self.moves:
            name, server = ctypes.create_string_buffer(r['name']), ctypes.create_string_buffer(r['server_name'])
            self.keep += [name, server]
            self.recs[r['index']] = MoveRecord(r['index'], r['id'], ctypes.addressof(name), ctypes.addressof(server),
                                               r['zen'], r['min_level'], r['max_level'], r['gate'], r['x44'], r['x48'],
                                               r['x4c'])
        self.keys = sorted(self.recs)
        self.by_id = sorted(self.keys, key=lambda k: self.recs[k].id)
        self.lookup = LOOKUP_FN(lambda user, key: ctypes.addressof(self.recs[key]) if key in self.recs else None)
        self.texts = {}

        def text(user, index):
            if index not in self.texts:
                self.texts[index] = ctypes.create_string_buffer(text_of(snap, index).encode('latin1'))
            return ctypes.addressof(self.texts[index])
        self.text_fn = TEXT_FN(text)
        self.gates = []
        for key, node in snap.tree(plain.GATE + 0x38):
            r = node + 0x14
            self.gates.append(Gate(key, *[snap.i32(r + off) for _, off in plain.GATE_COLUMNS]))
        self.gate_by = {g.index: g for g in self.gates}
        self.gate_fn = GATE_FN(lambda user, i: ctypes.addressof(self.gate_by[i]) if i in self.gate_by else None)


TABLES = {}


def tables(snap):
    if id(snap) not in TABLES:
        TABLES[id(snap)] = Tables(snap)
    return TABLES[id(snap)]


def random_keys(rng, t):
    pick = rng.random()
    if pick < 0.3:
        keys = list(t.by_id)              # the table order by record id (the live list's order, data)
    elif pick < 0.5:
        keys = list(t.keys)
    else:
        keys = list(t.keys)
        rng.shuffle(keys)
        keys = keys[:rng.randint(0, len(keys))]
    if rng.random() < 0.15:
        keys.insert(rng.randint(0, len(keys)), rng.choice([0, 35, 36, 999, -1]))   # absent keys: the default record
    return keys


def client_build(m, keys):
    arr = m.alloc(max(4 * len(keys), 4), define=True)
    m.write(arr, struct.pack(f'<{len(keys)}i', *keys))
    m.write(MOVEREQ + 0x40, struct.pack('<III', arr, arr + 4 * len(keys), arr + 4 * len(keys)))
    obj = m.alloc(0x40, define=True)
    m.call(MOVE_CTOR, [], ecx=obj)
    return obj


def client_entries(m, obj):
    begin, end = m.u32(obj + 4), m.u32(obj + 8)
    return [struct.unpack('<iiiiiBBBB', m.read(a, 0x18)) for a in range(begin, end, 0x18)]


def native_entries(arr, n):
    return [(e.key, e.x44, e.order, e.x48, e.key2, e.enabled, e.strife, e.clicked) for e in arr[:n]]


def client_tuple(es):
    return [e[:8] for e in es]


def native_build(nat, t, keys):
    arr = (MoveEntry * (len(keys) + 1))()
    k = (ctypes.c_int32 * max(len(keys), 1))(*keys)
    n = nat.L.mu_move_build(k, len(keys), t.lookup, None, arr, len(keys) + 1)
    return arr, n


def run_move_build(m, nat, rng, fam, cases, snap):
    t = tables(snap)
    for case in range(cases):
        prepare(m)
        keys = random_keys(rng, t)
        obj = client_build(m, keys)
        arr, n = native_build(nat, t, keys)
        fam.check(case, client_tuple(client_entries(m, obj)), native_entries(arr, n))


def run_move_sort(m, nat, rng, fam, cases, snap):
    t = tables(snap)
    for case in range(cases):
        prepare(m)
        order = rng.choice([0, 1, 2, 0, 1, 2, 3, -1])
        if rng.random() < 0.4:
            keys = random_keys(rng, t)
            obj = client_build(m, keys)
            arr, n = native_build(nat, t, keys)
        else:   # synthetic vectors: ties, sizes past the insertion-sort limit and the median of nine
            n = rng.choice([0, 1, 2, 31, 32, 33, 40, 41, 69, 100, 300, rng.randint(0, 300)])
            spread = rng.choice([2, 5, 20, 1000])
            rows = [(rng.randint(-5, 300), rng.randint(0, spread), i if rng.random() < 0.7 else rng.randint(0, spread),
                     rng.randint(0, spread), rng.randint(0, 300), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), 0)
                    for i in range(n)]
            vec = m.alloc(max(0x18 * n, 4), define=True)
            for i, r in enumerate(rows):
                m.write(vec + 0x18 * i, struct.pack('<iiiiiBBBB', *r))
            obj = m.alloc(0x40, define=True)
            m.write(obj + 4, struct.pack('<III', vec, vec + 0x18 * n, vec + 0x18 * n))
            arr = (MoveEntry * max(n, 1))()
            for i, r in enumerate(rows):
                arr[i] = MoveEntry(*r)
        m.call(MOVE_SORT, [order & 0xffffffff], ecx=obj)
        nat.L.mu_move_sort(arr, n, order)
        fam.check((case, order, n), client_tuple(client_entries(m, obj)), native_entries(arr, n))


def random_hero(rng):
    h = MoveHero()
    h.level = rng.choice([1, 10, 50, 150, 400, 800, 1000, 1400, 1700, rng.randint(0, 2000)])
    h.zen = rng.choice([0, 1999, 2000, 50000, 100000, 2500000, 2147483647, rng.randint(0, 3000000)])
    h.pk_level = rng.choice([0, 1, 3, 4, 5, 6])
    h.strife_ok = rng.randint(0, 1)
    h.wings_slot = int(rng.random() < 0.3)
    h.helper_type = rng.choice([-1, 0, 0x1a02, 0x1a03, 0x1a04, 0x28f7, 0x1a25, 0x1a00, rng.randint(0, 0x2c00)])
    h.helper_flies = int(rng.random() < 0.2)
    h.flying = rng.choice([0, 0, 1, -1, 5])
    h.kalima = rng.choice([0, 1, 2])
    h.server_flag = rng.randint(0, 1)
    h.event_a, h.event_b = int(rng.random() < 0.3), int(rng.random() < 0.3)
    return h


def install_hero(m, h):
    hero, ca, w = FAKE + 0x1000, FAKE + 0x8000, None
    m.put32(HERO_PTR, hero)
    m.write(hero + 0x1e, bytes([h.strife_ok, h.pk_level]))
    m.put32(CHARINFO_PTR, FAKE + 0x400)
    m.put32(CHARATTR_PTR, ca)
    m.put32(ca + 0x2d70, h.zen)
    m.stub(0x00a00367, lambda mm: h.level & 0xffffffff, 0)
    m.stub(0x0095fc2e, lambda mm: h.wings_slot, 4)
    m.stub(0x0106c5e9, lambda mm: h.helper_type & 0xffffffff, 0)
    m.stub(0x00cd4ea8, lambda mm: FAKE + 0x500, 0)
    m.stub(0x00cd6017, lambda mm: h.helper_flies, 8)
    m.stub(0x00b9b476, lambda mm: h.flying & 0xffffffff, 0)
    m.stub(0x01072152, lambda mm: FAKE + 0x600, 0)
    m.stub(0x01072a7f, lambda mm: h.server_flag, 0)
    m.stub(0x00fc6706, lambda mm: FAKE + 0x700, 0)
    m.stub(0x00b3b42e, lambda mm: h.event_a, 0)
    m.stub(0x00abec22, lambda mm: FAKE + 0x800, 0)
    m.stub(0x00a9698b, lambda mm: h.event_b, 0)
    return w


def manager_case(m, nat, rng, t):
    """A built (and maybe sorted) manager in both worlds, with random strife flags; returns (obj, arr, n)."""
    keys = random_keys(rng, t)
    obj = client_build(m, keys)
    arr, n = native_build(nat, t, keys)
    if rng.random() < 0.5:
        order = rng.randint(0, 2)
        m.call(MOVE_SORT, [order], ecx=obj)
        nat.L.mu_move_sort(arr, n, order)
    begin = m.u32(obj + 4)
    for i in range(n):
        if rng.random() < 0.3:
            m.write(begin + 0x18 * i + 0x15, b'\x01')
            arr[i].strife = 1
        if rng.random() < 0.5:
            en, cl = rng.randint(0, 1), rng.randint(0, 1)
            m.write(begin + 0x18 * i + 0x14, bytes([en]))
            m.write(begin + 0x18 * i + 0x16, bytes([cl]))
            arr[i].enabled, arr[i].clicked = en, cl
    m.put32(MOVE_MGR, obj)
    return obj, arr, n


def run_availability(m, nat, rng, fam, cases, snap):
    t = tables(snap)
    for case in range(cases):
        prepare(m)
        h = random_hero(rng)
        install_hero(m, h)
        obj, arr, n = manager_case(m, nat, rng, t)
        w = window(m)
        m.write(w + 0x7c, bytes([h.kalima]))
        m.call(MOVE_AVAIL, [0], ecx=w)
        nat.L.mu_move_availability(arr, n, ctypes.byref(h), t.lookup, t.text_fn, None)
        fam.check(case, client_tuple(client_entries(m, obj)), native_entries(arr, n))


def run_rows(m, nat, rng, fam, cases, snap):
    t = tables(snap)
    for case in range(cases):
        prepare(m)
        h = random_hero(rng)
        install_hero(m, h)
        obj, arr, n = manager_case(m, nat, rng, t)
        begin = m.u32(obj + 4)
        for i in range(n):   # random availability (the pass is a family of its own)
            v = rng.randint(0, 1)
            m.write(begin + 0x18 * i + 0x14, bytes([v]))
            arr[i].enabled = v
        w = window(m)
        favs = []
        for k in range(5):
            if rng.random() < 0.5:
                favs.append((0xffff, 0xffff))
            else:
                favs.append((rng.choice([0, 1, 0xffff]), rng.choice(t.keys + [0xffff, 7])))
        m.write(w + 0x8c, b''.join(struct.pack('<HH', *f) for f in favs))
        order = rng.randint(0, 2)
        m.call(MOVE_ROWS, [order], ecx=w)
        client = W.log[:]
        nat.L.mu_move_sort(arr, n, order)
        fv = (MoveFavourites * 1)() if False else None   # noqa: F841
        rows = []
        for i in range(n):
            row = MoveRow()
            checked = int(any(f[1] == (arr[i].key2 & 0xffff) for f in favs))
            nat.L.mu_move_row_make(ctypes.byref(arr[i]), i, ctypes.byref(h), checked, t.lookup, t.text_fn, None,
                                   ctypes.byref(row))
            rows.append((('orderIdx', ('s', str(row.order_idx))), ('strStrife', ('s', row.strife.decode('latin1'))),
                         ('strMap', ('s', row.map.decode('latin1'))), ('strLv', ('s', row.level.decode())),
                         ('strZen', ('s', row.zen.decode())), ('btnChecked', ('b', row.checked)),
                         ('bDisabled', ('i', row.disabled)), ('mapIdx', ('i', row.map_idx))))
        native = [('invoke', 'SetMoveMapList', tuple(rows)), ('invoke', 'ClearFavorMap', ())]
        native += [('invoke', 'AddMoveMapDataByMapIndex', (f[1],)) for f in favs if f[0] != 0xffff]
        fam.check(case, client, native)


def run_click(m, nat, rng, fam, cases, snap):
    t = tables(snap)
    mgr, holder = FAKE + 0x3000, FAKE + 0x3400
    wins = {name: FAKE + 0x3800 + 0x40 * i for i, name in enumerate(('a', 'b', 'c', 'self'))}
    vt = FAKE + 0x3f00

    def close(mm):
        W.log.append(('close', {v: k for k, v in wins.items()}.get(mm.uc.reg_read(cm.UC_X86_REG_ECX), '?')))
        return 0
    close_fn = m._new_stub()
    m.stub(close_fn, close, 0)
    for case in range(cases):
        prepare(m)
        h = random_hero(rng)
        install_hero(m, h)
        obj, arr, n = manager_case(m, nat, rng, t)
        w = wins['self']
        for a in wins.values():
            m.write(a, bytes(0x40))
            m.put32(a, vt)
        m.write(vt, bytes(0x48))
        m.put32(vt + 0x44, close_fn)
        visible = {wins[k]: rng.randint(0, 1) for k in 'abc'}
        world = rng.choice([0x1e, 0x22, 0x4f, 0, 2, 64, rng.randint(0, 150)])
        m.put32(WORLD, world)
        running = rng.randint(0, 1)
        key_in, key_out = rng.getrandbits(32), rng.getrandbits(32)
        m.write(holder, bytes(0x100))
        m.put32(holder + 0x84, key_in)
        m.stub(0x00ac3bf7, lambda mm: mgr, 0)
        for fn, target in ((0x0095fb15, FAKE + 0x3100), (0x009e819e, FAKE + 0x3200), (0x00b3b37d, wins['a']),
                           (0x0095f623, wins['b']), (0x00abed69, wins['c']), (0x00b2d745, holder)):
            m.stub(fn, (lambda v: lambda mm: v)(target), 0)
        m.stub(0x00c082c3, lambda mm: 0, 0)
        m.stub(0x00b8d8b5, lambda mm: 0, 0)
        m.stub(0x00aae6f9, lambda mm: visible.get(mm.uc.reg_read(cm.UC_X86_REG_ECX), 0), 0)
        m.stub(0x0182ff32, lambda mm: W.log.append(('helper_stop',)) or 0, 0)
        m.stub(0x0095f659, lambda mm: FAKE + 0x3300, 0)
        m.stub(0x0095fc71, (lambda r: lambda mm: r)(running), 0)
        m.stub(0x00cda52b, (lambda k: lambda mm: W.log.append(('key', mm.args(1)[0])) or k)(key_out), 4)
        m.stub(0x00b3bc1e, lambda mm: W.log.append(('b3bc1e', mm.args(1)[0])) or 0, 4)
        m.stub(0x0095c5da, lambda mm: mm.put32(mm.args(1)[0], FAKE + 0x3a00) or mm.args(1)[0], 4)
        m.stub(0x0095f17c, lambda mm: FAKE + 0x3b00, 0)
        m.stub(0x00bde9f3, lambda mm: FAKE + 0x3c00, 0)
        m.stub(0x00c6922a, lambda mm: W.log.append(('c6922a', mm.u32(mm.args(1)[0]))) or 0, 4)
        m.stub(0x0095ebd0, lambda mm: 0, 0)
        m.stub(0x00bdba22, lambda mm: W.log.append(('bdba22',)) or 0, 0)
        index = rng.choice([rng.randint(0, max(n - 1, 0)), -1, n, rng.randint(0, max(n - 1, 0))])
        special = [i for i in range(n) if arr[i].key2 in (0x18, 0x2c, 0x30)]
        if special and rng.random() < 0.4:   # the MU Helper rule's target keys, enabled
            index = rng.choice(special)
            m.write(m.u32(obj + 4) + 0x18 * index + 0x14, b'\x01')
            arr[index].enabled = 1
        result = m.call(MOVE_CLICK, [index & 0xffffffff], ecx=w) & 0xff
        client = (result, W.log[:], client_tuple(client_entries(m, obj)))
        r = ClickResult()
        nat.L.mu_move_click(arr, n, index, world, running, key_out, ctypes.byref(r))
        log = []
        if r.accepted:
            if r.helper_stop:
                log.append(('helper_stop',))
                if r.helper_packet:
                    log.append(('send', 'c105bf5101'))
            log += [('close', k) for k in 'abc' if visible[wins[k]]]
            log.append(('key', key_in))
            log.append(('send', bytes(r.packet[:r.packet_length]).hex()))
            log.append(('b3bc1e', arr[index].key2 & 0xffff))
            log.append(('c6922a', arr[index].key2))
            log += [('bdba22',), ('close', 'self')]
        native = (r.accepted, log, native_entries(arr, n))
        fam.check((case, index, world), client, native)


# ---- gates ---------------------------------------------------------------------------------------------------

GATE_CHECK, TICKS_SLOT = 0x016a4608, 0x01a7c49c


def c_format(fmt, *args):
    """The validator's sprintf model on Python strings (%s, %d)."""
    out, i, k = '', 0, 0
    while i < len(fmt):
        if fmt[i] == '%' and fmt[i + 1:i + 2] in ('s', 'd'):
            out += str(args[k])
            k += 1
            i += 2
        else:
            out += fmt[i]
            i += 1
    return out


def run_gates(m, nat, rng, fam, cases, snap):
    t = tables(snap)
    entrances = [g for g in t.gates if g.flag == 1]
    hero, ca, g6, mgr, win, vt = FAKE + 0x1000, FAKE + 0x8000, FAKE + 0x4300, FAKE + 0x4400, FAKE + 0x4500, FAKE + 0x4600
    now = {'v': 0}
    tick_fn = m._new_stub()
    m.stub(tick_fn, lambda mm: now['v'], 0)
    close_fn = m._new_stub()
    m.stub(close_fn, lambda mm: W.log.append(('close',)) or 0, 0)

    def packet(mm):
        W.log.append(('gate', mm.read(mm.uc.reg_read(cm.UC_X86_REG_ECX), 8).hex()))
        return 0
    gates_c = (Gate * len(t.gates))(*t.gates)
    for case in range(cases):
        prepare(m)
        m.put32(TICKS_SLOT, tick_fn)
        g = rng.choice(entrances)
        world = g.world if rng.random() < 0.9 else rng.choice([0x62, 0x2d, 0x30, rng.randint(0, 150)])
        if rng.random() < 0.85:
            x, y = rng.randint(g.x1, max(g.x1, g.x2)), rng.randint(g.y1, max(g.y1, g.y2))
        else:
            x, y = rng.randint(g.x1 - 2, g.x2 + 2), rng.randint(g.y1 - 2, g.y2 + 2)
        h = GateHero()
        h.world, h.tile_x, h.tile_y = world, x, y
        h.level = rng.choice([g.min_level - 1, g.min_level, g.min_level + 5, 1, 400, 2000, rng.randint(0, 1500)])
        h.loading_world = rng.choice([0] * 12 + [1, 30, 50, 9999999])
        busy = [int(rng.random() < 0.05) for _ in range(4)]
        h.busy = int(any(busy))
        h.wings_kind6 = 0
        item_type = rng.choice([-1, 0, 0x1800, 0x2c00, 0x2c01, rng.randint(0, 0x3000)])
        kind = rng.choice([6, 6, 0, 5, 7])
        h.helper_type = rng.choice([-1, 0, 0x1a02, 0x1a03, 0x1a04, 0x1a25, rng.randint(0, 0x2c00)])
        fa, fb = int(rng.random() < 0.15), int(rng.random() < 0.15)
        h.helper_flies = int(fa or fb)
        h.hero_3230 = rng.choice([0, 0, 1, -1])
        h.wings_kind6 = int(0 <= item_type <= 0x2c00 and kind == 6)
        flag01c, g6flag = int(rng.random() < 0.1), int(rng.random() < 0.15)
        last, now['v'] = rng.randint(0, 100000), rng.randint(0, 100000)
        h.throttle = int(flag01c or g6flag or ((now['v'] - last) & 0xffffffff) < 3000)
        visible = rng.randint(0, 1)
        # client state
        m.put32(WORLD, world)
        m.put32(LOADING_WORLD, h.loading_world)
        m.put32(HERO_PTR, hero)
        m.write(hero, bytes(0x40))
        m.write(hero + 0x2c, bytes([busy[0]]))
        m.put32(hero + 0x31c8, busy[1])
        m.put32(hero + 0x180, x)
        m.put32(hero + 0x184, y)
        m.put32(hero + 0x3230, h.hero_3230)
        m.write(FAKE + 0x20000, bytes(0x500))
        m.write(FAKE + 0x20000 + 0x469, bytes([busy[2]]))
        m.put32(FAKE + 0x20000 + 0x4d0, 0xffffffff if busy[2] else 0)
        m.stub(0x0095f659, lambda mm: FAKE + 0x20000, 0)
        m.stub(0x00db747f, lambda mm: 0, 0)
        m.stub(0x009fa30a, lambda mm: FAKE + 0x4100, 0)
        m.stub(0x009fbb31, (lambda b: lambda mm: b)(busy[3]), 4)
        m.stub(0x00a00367, (lambda v: lambda mm: v & 0xffffffff)(h.level), 0)
        m.put32(CHARINFO_PTR, FAKE + 0x400)
        m.put32(CHARATTR_PTR, ca)
        m.put32(ca + 0x1b58 + 7 * 0x12c + 0x10, item_type)
        m.write(FAKE + 0x4200 + 0x250, bytes([kind]))
        m.stub(0x00ccc591, lambda mm: FAKE + 0x4200, 0)
        m.stub(0x0106c5e9, (lambda v: lambda mm: v & 0xffffffff)(h.helper_type), 0)
        m.stub(0x00c92e9a, (lambda v: lambda mm: v)(fa), 0)
        m.stub(0x00cd4ea8, lambda mm: FAKE + 0x500, 0)
        m.stub(0x00cd6017, (lambda v: lambda mm: v)(fb), 8)
        m.write(0x06fca01c, bytes([flag01c]))
        m.write(g6, bytes(0x10))
        m.write(g6 + 6, bytes([g6flag]))
        m.put32(g6 + 8, last)
        m.stub(0x0095f75d, lambda mm: g6, 0)
        m.stub(0x00ac3bf7, lambda mm: mgr, 0)
        m.put32(mgr + 0x180, win)
        m.put32(win, vt)
        m.put32(vt + 0x44, close_fn)
        m.stub(0x00aae6f9, (lambda v: lambda mm: v)(visible), 0)
        m.stub(0x00b67ff9, packet, 0)
        m.stub(0x0182ff32, lambda mm: W.log.append(('helper_stop',)) or 0, 0)
        m.stub(0x0183055c, lambda mm: W.log.append(('macro', mm.cstr(mm.args(1)[0]).decode())) or 0, 0)
        m.stub(0x01697ac9, lambda mm: 0, 0)
        m.stub(0x016b617f, lambda mm: W.log.append(('quest_gate',)) or 0, 0)
        m.stub(0x00acbb85, lambda mm: mm.put32(mm.args(1)[0], 0) or mm.args(1)[0], 4)
        for a in range(0x01cf114c, 0x01cf1160, 4):
            m.put32(a, 0)
        m.put32(0x0b449ad0, 7)
        m.call(GATE_CHECK, [])
        client = (W.log[:], i32(m.u32(LOADING_WORLD)))
        r = GateResult()
        nat.L.mu_gate_check(gates_c, len(t.gates), t.gate_fn, None, ctypes.byref(h), ctypes.byref(r))
        log = []
        if r.packet_length:
            if visible:
                log.append(('close',))
            log.append(('gate', bytes(r.packet[:8]).hex()))
            if r.helper_stop:
                log += [('helper_stop',), ('macro', 'Data\\Macro.txt')]
        if r.refused == 1:
            log.append(('notice', c_format(text_of(snap, 350), t.gate_by[r.gate].min_level)))
        elif r.refused == 2:
            log.append(('notice', text_of(snap, 263)))
        elif r.refused == 3:
            log.append(('quest_gate',))
        fam.check((case, g.index, world, x, y, busy, h.level, h.throttle, h.loading_world), client, (log, r.loading_world))


# ---- main --------------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', required=True, help='langread snapshot (local)')
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--families', default=','.join(FAMILIES))
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes are caught')
    parser.add_argument('--output')
    args = parser.parse_args()
    for path, digest in ((args.text, vl.TEXT_SHA256), (args.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    snap = plain.Snapshot.load(args.snapshot)
    rng = random.Random(args.seed)
    m = vl.LangMachine(text, data, snap)
    install_common(m)
    nat = Native()
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256, 'seed': args.seed, 'families': {}}
    for name in args.families.split(','):
        fam = vl.Family(name)
        FAMILIES[name](m, nat, rng, fam, args.cases, snap)
        report['families'][name] = fam.summary()
        print(name, json.dumps(fam.summary()))
    report['mismatches'] = sum(f['mismatches'] for f in report['families'].values())
    report['cases'] = sum(f['cases'] for f in report['families'].values())
    if args.mutations:
        report['mutations'] = {}
        with tempfile.TemporaryDirectory() as work:
            for k, (name, family) in enumerate(MUTATIONS, 1):
                fam = vl.Family(family)
                FAMILIES[family](m, Native(k, work), random.Random(args.seed), fam, 60, snap)
                report['mutations'][name] = {'family': family, 'detected': fam.mismatches > 0,
                                             'mismatches': fam.mismatches, 'cases': fam.cases}
                print('mutation', name, json.dumps(report['mutations'][name]))
        if not all(v['detected'] for v in report['mutations'].values()):
            report['mismatches'] += 1
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1))
    print('total', report['cases'], 'cases', report['mismatches'], 'mismatches')
    return 1 if report['mismatches'] else 0


MUTATIONS = [('rotation_224', 'hud_update'), ('unit_key_type', 'units'), ('detected_type', 'detected'),
             ('hide_packet', 'show'), ('build_x44_x48', 'move_build'), ('stable_sort', 'move_sort'),
             ('pk_threshold', 'availability'), ('strife_text', 'rows'), ('special_key', 'click'),
             ('gate_x2_strict', 'gates')]

FAMILIES = {
    'hud_update': lambda m, nat, rng, fam, n, snap: run_hud_update(m, nat, rng, fam, n),
    'units': lambda m, nat, rng, fam, n, snap: run_units(m, nat, rng, fam, n),
    'detected': lambda m, nat, rng, fam, n, snap: run_detected(m, nat, rng, fam, n),
    'show': lambda m, nat, rng, fam, n, snap: run_show(m, nat, rng, fam, n, snap),
    'move_build': lambda m, nat, rng, fam, n, snap: run_move_build(m, nat, rng, fam, n, snap),
    'move_sort': lambda m, nat, rng, fam, n, snap: run_move_sort(m, nat, rng, fam, n, snap),
    'availability': lambda m, nat, rng, fam, n, snap: run_availability(m, nat, rng, fam, n, snap),
    'rows': lambda m, nat, rng, fam, n, snap: run_rows(m, nat, rng, fam, n, snap),
    'click': lambda m, nat, rng, fam, n, snap: run_click(m, nat, rng, fam, n, snap),
    'gates': lambda m, nat, rng, fam, n, snap: run_gates(m, nat, rng, fam, n, snap),
}


if __name__ == '__main__':
    sys.exit(main())
