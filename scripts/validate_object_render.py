#!/usr/bin/env python3
"""Compare the reconstructed world-object routines (reconstructed/objects/object_render.c) with the client.

NATIVE-OBJECTS-002. The client routines run in Unicorn over the pinned restored text (0x00401000) and
the second image section (0x01a7c000) through the strict machine of scripts/actor_machine.py: every byte
the guest reads must have been seeded by the harness or written by the guest, the image is read-only,
and only the callees listed per family are replaced by recording stubs (reasons in the report).

Families:
  light        RequestTerrainLight 0x016cb2f7 (primary light) and 0x016cb08d (frame light)
  body_light   the object body light 0x017ec3d8 (both RequestTerrainLight run as client code; the C
               runtime sin 0x01985700 for type 0x444)
  create       CreateObject 0x016d8538 for worlds 0 and 0x8d (sector, generic fields, Lorencia type
               defaults); the Tormenta handler slot 0x2c 0x00e4c6ba run on the result
  move_pass    MoveObjects 0x016d82c7 (sector walk, visibility, the calls per object)
  move         MoveObject 0x017ff238: generic part for many worlds (run up to the per-world switch at
               0x017ff8ad), world 0 complete (CreateFire 0x01616930, AngleMatrix, VectorRotate and the C
               runtime sin/cos as client code), world 0x8d complete with the Tormenta handler slot 0x30
               0x00e4c95e (sqrt as client code)
  render_pass  RenderObjects 0x016d5020 (sector and object TestFrustrum2D, draw order)
  render       RenderObject 0x016d4fe4 for the static-object call (setup 0x017ec896, draw 0x017edf43)

Stubs (recorded, never executed): the animation tick 0x012b4dd3, BMD::Animation 0x012b5064,
BMD::Transform 0x00966ea5, RenderBody 0x00966def, AddTerrainLight 0x016cacfc, CreateParticle 0x0168fafd,
PlayBuffer 0x00a6ac96, the CRT rand 0x01989721 (MSVC recurrence with a per-case seed, as the C callback),
the model container 0x00966cc4/0x00eaa8cf, the per-world render callees (0x017fcd18, 0x017f76ec,
0x017f9758, 0x017f9375, 0x017f919e, the render registry), the move pass callees and, for world 0x8d, the
world-group hooks of the default chains (their world tests are not executed; the handler slots they
reach are compared separately).

Usage:
  scripts/validate_object_render.py --text .../client-text.bin --data .../client-image-data.bin \
      [--cases N] [--only light,move] [--mutations] [--output report.json]
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import actor_machine as am  # noqa: E402

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
OBJ_SIZE = 0x3d8

# client globals
WORLD, WORLD2, SCENE, TERRAIN_READY = 0x01cf15fc, 0x01cf1600, 0x01d1df70, 0x0b5e3ea4
FRAME_LIGHT, PRIMARY_LIGHT, GRID_BYTES = 0x0b9f5430, 0x0bab5430, 256 * 256 * 12
TIME, HERO_PTR, HERO_TILE, BOUNDS = 0x06fce370, 0x0a39d754, 0x0b437c10, 0x0b437bfc
SECTORS, X2D, Y2D, TOP_VIEW = 0x0bdb61f0, 0x0b6b5400, 0x0b6b5410, 0x0bdc58b7
COUNTER, FRAME_TIME, MOVE_COUNT, EVENT_STEP = 0x06fc9c90, 0x01cf103c, 0x0bdc5890, 0x01cf15f4
TRIG_FLAG, CRT_MATH_MODE = 0x0bdd1cc8, 0x0bdcfbc8
# harness memory
OBJECTS, MODEL, ACTIONS, OUT, RECORD = 0x40000000, 0x41000000, 0x41001000, 0x41002000, 0x41003000
FAKE, BONES, HERO = 0x41004000, 0x41005000, 0x41010000
VSTUB_A, VSTUB_B, VSTUB_C = 0x00401000, 0x00401004, 0x00401008   # never-executed text addresses used as
# targets of fake vtable slots (stubs hook them)


def fake_object():
    fake = bytearray(0x400)
    struct.pack_into('<I', fake, 0, FAKE + 0x200)          # vtable pointer
    struct.pack_into('<I', fake, 0x200 + 0x2c, VSTUB_A)
    struct.pack_into('<I', fake, 0x200 + 0x30, VSTUB_B)
    struct.pack_into('<I', fake, 0x10, VSTUB_C)            # render registry entry
    return bytes(fake)

# routines
LIGHT_PRIMARY, LIGHT_FRAME, BODY_LIGHT = 0x016cb2f7, 0x016cb08d, 0x017ec3d8
CREATE, TORMENTA_CREATE, MOVE_PASS, MOVE, TORMENTA_MOVE = 0x016d8538, 0x00e4c6ba, 0x016d82c7, 0x017ff238, 0x00e4c95e
RENDER_PASS, RENDER = 0x016d5020, 0x016d4fe4
MOVE_SWITCH = 0x017ff8ad
BODIES = {
    'request_terrain_light_frame': (0x016cb08d, 0x016cb2f7),
    'request_terrain_light_primary': (0x016cb2f7, 0x016cb561),
    'body_light': (0x017ec3d8, 0x017ec896),
    'render_object_setup': (0x017ec896, 0x017edd1d),
    'render_object_draw': (0x017edf43, 0x017ee292),
    'render_object': (0x016d4fe4, 0x016d5020),
    'render_objects': (0x016d5020, 0x016d53a4),
    'move_objects': (0x016d82c7, 0x016d8475),
    'move_object': (0x017ff238, 0x01801665),
    'create_object': (0x016d8538, 0x016d9ac5),
    'create_fire': (0x01616930, 0x01616c80),
    'alpha_step': (0x012af883, 0x012af9a9),
    'tormenta_create': (0x00e4c6ba, 0x00e4c93b),
    'tormenta_move': (0x00e4c95e, 0x00e4cbd5),
}

f32, bits, from_bits = am.f32, am.bits, am.from_bits


class Machine(am.ActorMachine):
    """The strict machine, with writes to the routine's own argument slots allowed (cdecl callees
    may reuse them: RequestTerrainLight stores x / 100 back into [ebp+8])."""

    def caller_stack(self, uc, access, address, size, value, ignored):
        if address >= am.ENTRY_ESP + 4 and address + size <= am.ENTRY_ESP + 4 + self.argument_bytes:
            return
        super().caller_stack(uc, access, address, size, value, ignored)


def pack_f(*values):
    return struct.pack('<%df' % len(values), *values)


# ---------------------------------------------------------------- ctypes

class Event(ctypes.Structure):
    _fields_ = [('call', ctypes.c_uint32), ('object', ctypes.c_int32), ('count', ctypes.c_int32),
                ('args', ctypes.c_uint32 * 12)]


class Log(ctypes.Structure):
    _fields_ = [('count', ctypes.c_int32), ('capacity', ctypes.c_int32), ('overflow', ctypes.c_int32),
                ('events', ctypes.POINTER(Event))]


SIN_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float)
RAND_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
ANSWER_FN = ctypes.CFUNCTYPE(ctypes.c_uint8, ctypes.c_void_p, ctypes.c_int32)
SPEED_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)


class LightInputs(ctypes.Structure):
    _fields_ = [('primary', ctypes.c_void_p), ('frame', ctypes.c_void_p), ('scene_state', ctypes.c_int32),
                ('terrain_ready', ctypes.c_uint8), ('time', ctypes.c_float), ('sine', SIN_FN),
                ('context', ctypes.c_void_p)]


class MoveInputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('scene_state', ctypes.c_int32), ('hero_tile', ctypes.c_int32),
                ('time', ctypes.c_float), ('hero', ctypes.c_float * 3), ('has_model', ctypes.c_uint8),
                ('model_has_actions', ctypes.c_uint8), ('speed', SPEED_FN), ('rand_fn', RAND_FN),
                ('context', ctypes.c_void_p)]


class World(ctypes.Structure):
    _fields_ = [('objects', ctypes.POINTER(ctypes.c_void_p)), ('count', ctypes.c_int32),
                ('head', ctypes.c_int32 * 256), ('next', ctypes.POINTER(ctypes.c_int32)),
                ('block_visible', ctypes.c_uint8 * 256)]


class RenderInputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('scene_state', ctypes.c_int32), ('top_view', ctypes.c_uint8),
                ('x2d', ctypes.POINTER(ctypes.c_float)), ('y2d', ctypes.POINTER(ctypes.c_float)),
                ('render_first', ANSWER_FN), ('has_effects', ANSWER_FN), ('context', ctypes.c_void_p),
                ('frame_time', ctypes.c_float)]


class DrawInputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('scene_state', ctypes.c_int32), ('has_model', ctypes.c_uint8),
                ('chaos_hero_flag', ctypes.c_uint8), ('option_flag', ctypes.c_uint8), ('bounds_mode', ctypes.c_int32),
                ('light', LightInputs), ('custom_render', ANSWER_FN), ('registry', ANSWER_FN),
                ('context', ctypes.c_void_p)]


class Record(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int16), ('pad', ctypes.c_uint8 * 2), ('position', ctypes.c_float * 3),
                ('angle', ctypes.c_float * 3), ('vector', ctypes.c_float * 3), ('scale', ctypes.c_float),
                ('flag_2c', ctypes.c_uint8), ('flag_2d', ctypes.c_uint8), ('flag_2e', ctypes.c_uint8),
                ('hidden', ctypes.c_uint8), ('value_30', ctypes.c_float), ('value_34', ctypes.c_float)]


assert ctypes.sizeof(Record) == 0x38


class Library:
    def __init__(self, path):
        d = self.dll = ctypes.CDLL(str(path))
        P = ctypes.c_void_p
        d.mu_obj_terrain_light.argtypes = [P, ctypes.c_int32, ctypes.c_uint8, ctypes.c_float, ctypes.c_float, P]
        d.mu_obj_body_light.argtypes = [P, P, ctypes.POINTER(LightInputs)]
        d.mu_obj_create.argtypes = [ctypes.POINTER(Record), ctypes.c_int32, P, ctypes.POINTER(ctypes.c_int32),
                                    ctypes.c_int32, ctypes.POINTER(Log)]
        d.mu_obj_handler_moves.argtypes = [P, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                                           ctypes.POINTER(ctypes.c_float), ctypes.c_int32]
        d.mu_obj_handler_moves.restype = ctypes.c_uint8
        d.mu_obj_move_pass.argtypes = [ctypes.POINTER(World), ctypes.c_int32, ANSWER_FN, P, ctypes.POINTER(Log)]
        d.mu_obj_move.argtypes = [P, ctypes.c_int32, ctypes.POINTER(MoveInputs), ctypes.POINTER(Log)]
        d.mu_obj_move_generic.argtypes = d.mu_obj_move.argtypes
        d.mu_obj_render_pass.argtypes = [ctypes.POINTER(World), ctypes.POINTER(RenderInputs),
                                         ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(Log)]
        d.mu_obj_visual.argtypes = [P, ctypes.c_int32, ctypes.c_float]
        d.mu_obj_render.argtypes = [P, ctypes.c_int32, P, ctypes.c_uint8, ctypes.POINTER(DrawInputs),
                                    ctypes.POINTER(Log)]


def new_log(capacity=4096):
    storage = (Event * capacity)()
    log = Log(0, capacity, 0, ctypes.cast(storage, ctypes.POINTER(Event)))
    log._storage = storage
    return log


def log_events(log):
    return [(e.call, e.object) + tuple(e.args[:e.count]) for e in log.events[:log.count]]


class MsvcRand:
    def __init__(self, seed):
        self.seed = seed & 0xffffffff

    def __call__(self, *ignored):
        self.seed = (self.seed * 214013 + 2531011) & 0xffffffff
        return (self.seed >> 16) & 0x7fff


# ---------------------------------------------------------------- shared case material

def random_float(g, kind='any'):
    r = g.random()
    if kind == 'any' and r < 0.03:
        return g.choice([math.nan, math.inf, -math.inf, 0.0, -0.0])
    return f32(g.uniform(-2.0, 2.0))


def light_grid(g):
    values = [f32(g.uniform(-0.5, 1.6)) for _ in range(4096)]
    out = bytearray(GRID_BYTES)
    for i in range(256 * 256 * 3):
        struct.pack_into('<f', out, 4 * i, values[(i * 7 + (i >> 5)) & 4095])
    return bytes(out)


def position_pair(g):
    r = g.random()
    if r < 0.08:
        return f32(g.choice([-150.0, -1.0, 25400.0, 25500.5, 25600.0, 1e9, math.nan])), f32(g.uniform(0, 25600))
    if r < 0.15:
        return f32(g.uniform(0, 25600)), f32(g.choice([-0.5, 25499.9, 25500.0, math.inf]))
    return f32(g.uniform(0.0, 25600.0)), f32(g.uniform(0.0, 25600.0))


def global_regions(world, scene=6, extra=()):
    regions = [am.defined_region('world', WORLD, struct.pack('<i', world)),
               am.defined_region('world2', WORLD2, struct.pack('<i', world), writable=False),
               am.defined_region('scene', SCENE, struct.pack('<i', scene), writable=False),
               am.defined_region('trig-flag', TRIG_FLAG, struct.pack('<I', 1), writable=False),
               am.defined_region('crt-math-mode', CRT_MATH_MODE, struct.pack('<I', 0))]
    regions.extend(extra)
    return regions


def poison_object(g):
    return bytes(g.getrandbits(8) for _ in range(OBJ_SIZE))


def put_f(buf, offset, *values):
    struct.pack_into('<%df' % len(values), buf, offset, *values)


def put_i(buf, offset, value):
    struct.pack_into('<i', buf, offset, value)


class Tally:
    def __init__(self, name):
        self.name, self.cases, self.equal, self.stopped, self.mismatches, self.cover = name, 0, 0, 0, [], {}

    def add(self, ok, detail=None, stopped=None):
        self.cases += 1
        if stopped is not None:
            self.stopped += 1
            if len(self.mismatches) < 8:
                self.mismatches.append({'stopped': stopped, **(detail or {})})
        elif ok:
            self.equal += 1
        elif len(self.mismatches) < 8:
            self.mismatches.append(detail or {})

    def count(self, label, n=1):
        self.cover[label] = self.cover.get(label, 0) + n

    def report(self):
        return {'cases': self.cases, 'equal': self.equal, 'stopped': self.stopped,
                'mismatch_count': self.cases - self.equal - self.stopped, 'examples': self.mismatches,
                'coverage': self.cover}


def run(machine, start, arguments, regions, stubs, *, ecx=0, cleanup=0, until=None):
    stubs = dict(stubs)
    if until is not None:
        stubs[until] = lambda m: m.stop(('reached', hex(until)))
    result = machine.execute(start, arguments, regions, stubs, ecx=ecx, cleanup=cleanup)
    if until is not None and result['stopped'] == ('reached', hex(until)):
        result['ok'], result['stopped'] = True, None
    return result


def stopped_reason(result):
    if result['ok']:
        return None
    return {'stopped': result['stopped'], 'error': result['error'],
            'checks': {k: v for k, v in result['checks'].items() if not v}}


def read_vec(m, address):
    return tuple(struct.unpack('<3I', bytes(m.uc.mem_read(address, 12))))


# ---------------------------------------------------------------- 1. light

def family_light(machine, lib, g, cases):
    t = Tally('light')
    grids = [light_grid(g) for _ in range(2)]
    for n in range(cases):
        grid = grids[n % 2]
        frame_flag = n % 2
        scene = g.choice([0, 1, 2, 3, 4, 5, 6, 6, 6, 6])
        ready = g.choice([0, 1, 1, 1, 1])
        x, y = position_pair(g)
        regions = global_regions(0, scene, [
            am.defined_region('frame-light' if frame_flag else 'primary-light', FRAME_LIGHT if frame_flag else
                              PRIMARY_LIGHT, grid, writable=False),
            am.defined_region('terrain-ready', TERRAIN_READY, bytes([ready]), writable=False),
            am.undefined_region('out', OUT, 12)])
        result = run(machine, LIGHT_FRAME if frame_flag else LIGHT_PRIMARY, [bits(x), bits(y), OUT], regions, {})
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        out = (ctypes.c_float * 3)()
        buf = ctypes.create_string_buffer(grid, len(grid))
        lib.dll.mu_obj_terrain_light(ctypes.cast(buf, ctypes.c_void_p), scene, ready, x, y, out)
        expect = struct.pack('<3f', *out)
        got = result['regions']['out']
        t.count('zero' if got == bytes(12) else 'interpolated')
        t.add(got == expect, {'case': n, 'x': x, 'y': y, 'scene': scene, 'got': got.hex(), 'c': expect.hex()})
    return t


# ---------------------------------------------------------------- 2. body light

def body_light_object(g, world_types=None):
    o = bytearray(poison_object(g))
    t = g.choice([g.randrange(0, 300), g.randrange(0, 300), 0x7dc, 0x444, g.randrange(0, 0x1000)])
    put_i(o, 0x5c, t)
    for k in (5, 6, 7):
        o[k] = g.choice([0, 1, 1, 2])
    x, y = position_pair(g)
    put_f(o, 0x158, x, y, f32(g.uniform(-100, 600)))
    put_f(o, 0xec, *(f32(g.uniform(-0.4, 0.6)) for _ in range(3)))
    return o


def family_body_light(machine, lib, g, cases):
    t = Tally('body_light')
    grids = (light_grid(g), light_grid(g))
    sine = SIN_FN(lambda ctx, v: f32(math.sin(v)))
    for n in range(cases):
        o = body_light_object(g)
        model = bytes(g.getrandbits(8) for _ in range(0xd0))
        scene = g.choice([0, 2, 5, 6, 6, 6])
        ready = g.choice([0, 1, 1, 1])
        time = f32(g.uniform(0, 3e7))
        regions = global_regions(0, scene, [
            am.defined_region('frame-light', FRAME_LIGHT, grids[0], writable=False),
            am.defined_region('primary-light', PRIMARY_LIGHT, grids[1], writable=False),
            am.defined_region('terrain-ready', TERRAIN_READY, bytes([ready]), writable=False),
            am.defined_region('time', TIME, pack_f(time), writable=False),
            am.defined_region('object', OBJECTS, bytes(o)),
            am.defined_region('model', MODEL, model)])
        result = run(machine, BODY_LIGHT, [OBJECTS, MODEL], regions, {})
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': struct.unpack_from('<i', o, 0x5c)[0]}, stop)
            continue
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        cmodel = ctypes.create_string_buffer(model, 0xd0)
        gf, gp = ctypes.create_string_buffer(grids[0], GRID_BYTES), ctypes.create_string_buffer(grids[1], GRID_BYTES)
        inputs = LightInputs(ctypes.cast(gp, ctypes.c_void_p), ctypes.cast(gf, ctypes.c_void_p), scene, ready, time,
                             sine, None)
        lib.dll.mu_obj_body_light(cobj, cmodel, ctypes.byref(inputs))
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        t.count('type 0x7dc' if typ == 0x7dc else 'type 0x444' if typ == 0x444 else
                'copy' if (o[5] or o[6]) else 'scaled, no copy')
        same = result['regions']['object'] == cobj.raw[:OBJ_SIZE] and result['regions']['model'] == cmodel.raw[:0xd0]
        t.add(same, {'case': n, 'type': typ, 'flags': list(o[5:8]),
                     'model_got': result['regions']['model'][0x50:0x60].hex(), 'model_c': cmodel.raw[0x50:0x60].hex()})
    return t


# ---------------------------------------------------------------- 3. create

LORENCIA_SPECIAL = [0, 1, 6, 0x34, 0x3b, 0x50, 0x5a, 0x60, 0x61, 0x62, 0x69, 0x75, 0x76, 0x77, 0x7a, 0x85, 0x91,
                    0x92, 0x96]
TORMENTA_SPECIAL = list(range(0, 10)) + [0x0c, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x24, 0x27, 0x2a, 0x2b, 0x41, 0x48,
                                         0x4b, 0x50, 0x51, 0x76, 0x79, 0x7b, 0x7c, 0x7d, 0x7f, 0x80, 0xb3, 0xb4,
                                         0xc0, 0xc7, 0xc8, 0xc9]


def random_record(g, world):
    special = LORENCIA_SPECIAL if world == 0 else TORMENTA_SPECIAL
    r = Record()
    r.type = g.choice(special + [g.randrange(0, 300), g.randrange(-5, 400)])
    if g.random() < 0.06:
        r.position[0], r.position[1] = g.choice([(-1.0, 100.0), (25600.0, 9.0), (100.0, 30000.0), (math.nan, 5.0)])
    else:
        r.position[0], r.position[1] = f32(g.uniform(0, 25599)), f32(g.uniform(0, 25599))
    r.position[2] = f32(g.uniform(-200, 800))
    for k in range(3):
        r.angle[k] = f32(g.uniform(-360, 360))
        r.vector[k] = f32(g.uniform(-0.5, 0.5))
    r.scale = f32(g.choice([1.0, g.uniform(0.3, 3.0)]))
    r.flag_2c, r.flag_2d, r.flag_2e = g.choice([0, 1]), g.choice([0, 1]), g.choice([0, 1])
    r.hidden = g.choice([0, 0, 0, 1])
    r.value_30, r.value_34 = f32(g.choice([0.8, g.uniform(0, 2)])), f32(g.choice([0.2, g.uniform(0, 2)]))
    return r


CREATE_LOG_SKIP = (0x350, 0x358)   # sector links (checked separately)


def family_create(machine, lib, g, cases):
    t = Tally('create')
    for n in range(cases):
        world = g.choice([0, 0x8d])
        rec = random_record(g, world)
        poison = poison_object(g)
        sector_table = bytearray(256 * 16)
        prior = OBJECTS + 0x800 if g.random() < 0.5 else 0   # an existing list head in the object's sector
        calls = []

        def malloc(m):
            calls.append(('malloc', m.argument(0)))
            return OBJECTS

        def ctor(m):
            calls.append(('ctor',))
            return m.uc.reg_read(m.x86.UC_X86_REG_ECX)

        def record_call(name, cleanup=0, value=0):
            def stub(m):
                calls.append((name,) + tuple(m.argument(i) for i in range(2)))
                return (value, cleanup)
            return stub

        stubs = {0x0191ba7b: malloc, 0x0129e792: ctor, 0x0129eb81: record_call('init'),
                 0x01295f18: record_call('buff-list'), 0x016d9f51: record_call('register')}
        if world == 0x8d:
            # world-group hooks of the default chain (not executed) and the world manager dispatch
            for address in (0x009dafa8, 0x00def3ac, 0x00d8e18f, 0x00dfbc3f, 0x00d6200e, 0x00dabeb4, 0x00e74a58,
                            0x00e7dcf4, 0x00e84530, 0x00e30a02, 0x00e5f617):
                stubs[address] = record_call(hex(address))
            stubs[0x0095c652] = lambda m: FAKE                                   # custom-map table
            stubs[0x00d53c8f] = lambda m: FAKE
            stubs[0x00d53d53] = record_call('d53d53', 4)
            stubs[0x00d53d7d] = record_call('d53d7d', 4)
            stubs[0x00db747f] = lambda m: FAKE
            stubs[VSTUB_A] = record_call('vslot-2c', 4)                       # vcall [FAKE vtable + 0x2c]
            stubs[0x00ea594b] = lambda m: FAKE + 0x100
            stubs[0x00ea2ad6] = record_call('world-manager-create', 4)
        x, y = rec.position[0], rec.position[1]
        sx = int(x / 1600) if math.isfinite(x) and -2**31 < x / 1600 < 2**31 else -2**31
        sy = int(y / 1600) if math.isfinite(y) and -2**31 < y / 1600 < 2**31 else -2**31
        inside = 0 <= sx < 16 and 0 <= sy < 16
        sector = (sx << 4) + sy if inside else 0
        if inside and prior:
            struct.pack_into('<II', sector_table, sector * 16 + 4, prior, prior)
        fake = fake_object()
        regions = global_regions(world, 6, [
            am.defined_region('record', RECORD, bytes(rec)),
            am.defined_region('object', OBJECTS, poison),
            am.defined_region('prior', OBJECTS + 0x800, bytes(OBJ_SIZE)),
            am.defined_region('sectors', SECTORS, bytes(sector_table)),
            am.defined_region('fake', FAKE, bytes(fake), writable=False)])
        result = run(machine, CREATE, [RECORD], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': rec.type}, stop)
            continue
        guest = bytearray(result['regions']['object'])
        if inside and world == 0x8d:
            # handler slot 0x2c on the created object (0x00e54061 accepts the world, run as client code)
            r2 = run(machine, TORMENTA_CREATE, [OBJECTS], global_regions(world, 6, [
                am.defined_region('object', OBJECTS, bytes(guest))]), {}, ecx=FAKE + 0x100, cleanup=4)
            stop = stopped_reason(r2)
            if stop:
                t.add(False, {'case': n, 'world': world, 'type': rec.type, 'step': 'tormenta hook'}, stop)
                continue
            guest = bytearray(r2['regions']['object'])
        cobj = ctypes.create_string_buffer(poison, OBJ_SIZE)
        csector = ctypes.c_int32(-1)
        log = new_log(16)
        status = lib.dll.mu_obj_create(ctypes.byref(rec), world, cobj, ctypes.byref(csector), 0, ctypes.byref(log))
        c = bytearray(cobj.raw[:OBJ_SIZE])
        ok = True
        detail = {'case': n, 'world': world, 'type': rec.type, 'status': status}
        if not inside:
            ok = result['eax'] == 0 and status == 1 and c == bytearray(poison) and guest == bytearray(poison)
            t.count('outside the map')
        else:
            links = bytes(guest[CREATE_LOG_SKIP[0]:CREATE_LOG_SKIP[1]])
            guest[CREATE_LOG_SKIP[0]:CREATE_LOG_SKIP[1]] = c[CREATE_LOG_SKIP[0]:CREATE_LOG_SKIP[1]]
            diff = [hex(i) for i in range(OBJ_SIZE) if guest[i] != c[i]]
            table = result['regions']['sectors']
            head, tail = struct.unpack_from('<II', table, sector * 16 + 4)
            prev, nxt = struct.unpack('<II', links)
            link_ok = (head, tail, nxt) == ((prior or OBJECTS), OBJECTS, 0) and prev == (prior if prior else prev)
            registered = [cl for cl in calls if cl[0] == 'register']
            c_registered = [e for e in log_events(log) if e[0] == 0x016d9f51]
            ok = result['eax'] == OBJECTS and status == 0 and not diff and link_ok and csector.value == sector and \
                len(registered) == len(c_registered)
            detail.update({'diff': diff[:12], 'link_ok': link_ok})
            t.count(f'world {world:#x}')
            t.count('type default' if rec.type not in (LORENCIA_SPECIAL if world == 0 else TORMENTA_SPECIAL)
                    else 'type case')
        t.add(ok, detail)
    return t


# ---------------------------------------------------------------- object lists

def object_list(g, count, fields):
    """count objects in random sectors; returns (objects, heads, next) with list order = creation order."""
    objects, sector_of = [], []
    for k in range(count):
        o = bytearray(poison_object(g))
        fields(g, o, k)
        s = g.randrange(256) if g.random() < 0.6 else g.choice([0, 17, 136, 255, 119, 120])
        objects.append(o)
        sector_of.append(s)
    heads, tails, nxt = [-1] * 256, [-1] * 256, [-1] * count
    for k, s in enumerate(sector_of):
        if heads[s] < 0:
            heads[s] = k
        else:
            nxt[tails[s]] = k
        tails[s] = k
    for k, o in enumerate(objects):
        struct.pack_into('<I', o, 0x354, OBJECTS + 0x400 * nxt[k] if nxt[k] >= 0 else 0)
    return objects, heads, nxt


def sector_bytes(heads, visible=None):
    table = bytearray(256 * 16)
    for s in range(256):
        if heads[s] >= 0:
            struct.pack_into('<I', table, s * 16 + 4, OBJECTS + 0x400 * heads[s])
        if visible is not None:
            table[s * 16 + 0xc] = visible[s]
    return table


def c_world(objects, heads, nxt, visible=None):
    bufs = [ctypes.create_string_buffer(bytes(o), OBJ_SIZE) for o in objects]
    ptrs = (ctypes.c_void_p * max(1, len(bufs)))(*[ctypes.cast(b, ctypes.c_void_p) for b in bufs])
    nexts = (ctypes.c_int32 * max(1, len(nxt)))(*nxt)
    w = World()
    w.objects = ptrs
    w.count = len(objects)
    for s in range(256):
        w.head[s] = heads[s]
        w.block_visible[s] = visible[s] if visible else 0
    w.next = nexts
    w._keep = (bufs, ptrs, nexts)
    return w, bufs


def frustum_polygon(g):
    cx, cy = g.uniform(20, 230), g.uniform(20, 230)
    a = g.uniform(0, 2 * math.pi)
    pts = []
    for k, (r, d) in enumerate([(40, 0.3), (40, -0.3), (12, math.pi - 0.6), (12, math.pi + 0.6)]):
        pts.append((f32(cx + r * math.cos(a + d)), f32(cy + r * math.sin(a + d))))
    return [p[0] for p in pts], [p[1] for p in pts]


# ---------------------------------------------------------------- 4. move pass

def family_move_pass(machine, lib, g, cases):
    t = Tally('move_pass')
    for n in range(cases):
        world = g.choice([0, 0x8d, 2, 10])
        count = g.randrange(0, 40)

        def fields(g, o, k):
            o[0] = g.choice([0, 1, 1, 1])
            o[0xb] = g.choice([0, 1])
        objects, heads, nxt = object_list(g, count, fields)
        visible = [g.choice([0, 1]) for _ in range(256)]
        handler = [g.choice([0, 0, 1]) for _ in range(count)]
        calls = []
        address_index = lambda a: (a - OBJECTS) // 0x400

        def rec(call):
            def stub(m):
                calls.append((call, address_index(m.argument(0))))
                return 0
            return stub

        def handler_stub(m):
            return (handler[address_index(m.argument(0))], 4)
        stubs = {0x01802168: lambda m: calls.append((0x01802168, -1)) or 0,
                 0x017ff238: rec(0x017ff238), 0x0180249e: rec(0x0180249e), 0x017ec026: rec(0x017ec026),
                 0x00ea594b: lambda m: FAKE, 0x00ea27e0: handler_stub,
                 0x00cd4ea8: lambda m: FAKE, 0x00cd5d29: lambda m: FAKE, 0x01983b90: lambda m: 0}
        step = g.randrange(-3, 30)
        regions = global_regions(world, 6, [
            am.defined_region('sectors', SECTORS, bytes(sector_bytes(heads, visible))),
            am.defined_region('move-count', MOVE_COUNT, struct.pack('<i', 7)),
            am.defined_region('event-step', EVENT_STEP, struct.pack('<i', step)),
            am.undefined_region('fake', FAKE, 0x400)] +
            [am.defined_region(f'object{k}', OBJECTS + 0x400 * k, bytes(o)) for k, o in enumerate(objects)])
        result = run(machine, MOVE_PASS, [], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        w, bufs = c_world(objects, heads, nxt, visible)
        log = new_log()
        answer = ANSWER_FN(lambda ctx, k: handler[k])
        lib.dll.mu_obj_move_pass(ctypes.byref(w), world, answer, None, ctypes.byref(log))
        c_calls = [(e[0], e[1]) for e in log_events(log)]
        same_objects = all(result['regions'][f'object{k}'] == bufs[k].raw[:OBJ_SIZE] for k in range(count))
        globals_ok = struct.unpack('<i', result['regions']['move-count'])[0] == 0 and \
            struct.unpack('<i', result['regions']['event-step'])[0] == step - 1 and \
            struct.unpack('<i', result['regions']['world'])[0] == world
        t.count('moved objects', sum(1 for c in calls if c[0] == 0x017ff238))
        t.add(calls == c_calls and same_objects and globals_ok,
              {'case': n, 'calls': calls[:6], 'c': c_calls[:6], 'objects': same_objects, 'globals': globals_ok})
    return t


# ---------------------------------------------------------------- 4b. handler slot 0x1c (Tormenta)

def family_handler_moves(machine, lib, g, cases):
    t = Tally('handler_moves')
    for n in range(cases):
        x2d, y2d = frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4
        scene = g.choice([6, 6, 2])
        o = bytearray(poison_object(g))
        put_i(o, 0x5c, g.choice([0x1f, 0x20, 0x1f, 0x20, g.randrange(0, 0xd0)]))
        put_f(o, 0x158, f32((cx + g.uniform(-60, 60)) * 100), f32((cy + g.uniform(-60, 60)) * 100), 0.0)
        put_f(o, 0xc0, f32(g.choice([-1000.0, -30.0, g.uniform(-1500, 100)])))
        regions = global_regions(0x8d, scene, [
            am.defined_region('object', OBJECTS, bytes(o), writable=False),
            am.defined_region('x2d', X2D, pack_f(*x2d), writable=False),
            am.defined_region('y2d', Y2D, pack_f(*y2d), writable=False)])
        result = run(machine, 0x00e4bfff, [OBJECTS], regions, {}, ecx=FAKE, cleanup=4)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        xs, ys = (ctypes.c_float * 4)(*x2d), (ctypes.c_float * 4)(*y2d)
        c = lib.dll.mu_obj_handler_moves(ctypes.create_string_buffer(bytes(o), OBJ_SIZE), 0x8d, xs, ys, scene)
        got = result['eax'] & 0xff
        t.count('moves' if got else 'stays')
        t.add(got == c, {'case': n, 'got': got, 'c': c})
    return t


# ---------------------------------------------------------------- 5. move

TYPES_W0 = [0x32, 0x33, 0x34, 0x37, 0x50, 0x5a, 0x61, 0x75, 0x76, 0x77, 0x7a, 0x7d, 0x7e, 0x82, 0x83, 0x84, 0x96,
            0, 1, 52, 105, 133]
GENERIC_WORLDS = [0, 1, 2, 3, 4, 8, 0x39, 0x3a, 0x50, 0x51, 0x5b, 0x5c, 0x73, 0x87, 0x88, 0x8d, 0x22, 0x3f, 0x8e]
SPEED_TYPES = [8, 0x10, 0x11, 0x44, 0x42, 0x6b, 0x34, 0x39, 0x65, 0x3c, 0x16, 0x29, 0x5c, 0x74, 0x77, 0x81, 0xb5,
               0x51, 0x52, 0x60, 0x62, 0x63, 0x7d, 0x7e, 0x12d, 0x12e]


def move_object(g, world, mode):
    o = bytearray(poison_object(g))
    if world == 0 and mode == 'full':
        typ = g.choice(TYPES_W0 + [g.randrange(0, 160)])
    elif world == 0x8d and mode == 'full':
        typ = g.choice([6, 0xb7, 0xc8, 6, 0xb7, 0xc8, g.randrange(0, 0xd0)])
    else:
        typ = g.choice(SPEED_TYPES + [g.randrange(0, 300)])
    put_i(o, 0x5c, typ)
    o[0xc] = g.choice([0, 0, 1])
    alpha = g.choice([1.0, 1.0, 0.0, 0.005, g.uniform(0, 1.2)])
    put_f(o, 0xd8, f32(g.choice([1.0, 0.0, g.uniform(0, 1)])), f32(alpha), f32(g.choice([0.1, g.uniform(0, 1)])))
    put_f(o, 0xa8, f32(g.choice([1.0, g.uniform(0, 1.5)])))
    struct.pack_into('<HH', o, 0x2a, g.choice([0, 1, 2, 3]), g.choice([0, 1]))
    put_f(o, 0xbc, f32(g.choice([0.16, 0.3, 0.4, g.uniform(0, 1)])))
    put_f(o, 0xa0, f32(g.choice([1.0, g.uniform(0.3, 3)])))
    put_f(o, 0x158, f32(g.uniform(0, 25600)), f32(g.uniform(0, 25600)), f32(g.uniform(-100, 500)))
    put_f(o, 0x164, *(f32(g.uniform(-360, 360)) for _ in range(3)))
    put_f(o, 0xec, *(f32(g.uniform(-0.3, 0.6)) for _ in range(3)))
    return o


def family_move(machine, lib, g, cases):
    t = Tally('move')
    for n in range(cases):
        mode = ['generic', 'full', 'full'][n % 3]
        world = g.choice(GENERIC_WORLDS) if mode == 'generic' else g.choice([0, 0, 0x8d])
        o = move_object(g, world, mode)
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        scene = g.choice([6, 6, 6, 5, 3])
        hero_tile = g.choice([0, 3, 4, 4, 9, 10, 12])
        time = f32(g.choice([g.uniform(0, 3e7), g.uniform(0, 5000), 1000.0, 999.0]))
        has_model = 1 if g.random() < 0.95 else 0
        # only worlds 0x87/0x88 test the action table pointer; elsewhere the client reads it unchecked
        actions = 1 if world not in (0x87, 0x88) or g.random() < 0.8 else 0
        speeds = [f32(g.uniform(0.05, 1.0)) for _ in range(4)]
        hero = (f32(struct.unpack_from('<f', o, 0x158)[0] + g.uniform(-1500, 1500)),
                f32(struct.unpack_from('<f', o, 0x15c)[0] + g.uniform(-1500, 1500)), 0.0)
        seed = g.getrandbits(32)
        rnd = MsvcRand(seed)
        calls = []

        def tick(m):
            args = [m.argument(i) for i in range(6)]
            ok = args[0] == OBJECTS + 0xd0 and args[1] == OBJECTS + 0xd4 and args[2] == OBJECTS + 0x2c and \
                args[4] == OBJECTS + 0x158 and args[5] == OBJECTS + 0x164
            calls.append((0x012b4dd3, 0, args[3]) if ok else ('tick pointers', args))
            return (1, 0x18)

        def add_light(m):
            a = [m.argument(i) for i in range(5)]
            light = read_vec(m, a[2])
            calls.append((0x016cacfc, 0, a[0], a[1]) + light + (a[3],) if a[4] == FRAME_LIGHT else ('light buffer', a))
            return 0

        def particle(m):
            a = [m.argument(i) for i in range(8)]
            entry = (0x0168fafd, 0, a[0]) + read_vec(m, a[1]) + read_vec(m, a[2]) + read_vec(m, a[3]) + (a[4], a[5])
            calls.append(entry if a[6] == 0 and a[7] == 0 else ('particle tail', a))
            return 0

        def sound(m):
            calls.append((0x00a6ac96, 0, m.argument(0), m.argument(1), m.argument(2)))
            return 0

        def model_lookup(m):
            return (MODEL if has_model else 0, 4)
        stubs = {0x012b4dd3: tick, 0x016cacfc: add_light, 0x0168fafd: particle, 0x00a6ac96: sound,
                 0x01989721: lambda m: rnd(), 0x00966cc4: lambda m: FAKE, 0x00eaa8cf: model_lookup}
        if world == 0x8d:
            for address in (0x00def6fb, 0x00d8e38c, 0x00dfbc92, 0x00d6202f, 0x00dabed5, 0x00e74ae0, 0x00e7dd29,
                            0x00e845d0, 0x00e30b86, 0x00e5f629):
                stubs[address] = (lambda a: lambda m: calls.append(('chain', hex(a))) and 0 or 0)(address)
            stubs[0x00d53c8f] = lambda m: FAKE
            stubs[0x00d53da7] = lambda m: (0, 4)
            stubs[0x00db747f] = lambda m: FAKE
            stubs[VSTUB_B] = lambda m: (0, 4)
            stubs[0x00ea594b] = lambda m: FAKE + 0x100
            stubs[0x00ea2c2b] = lambda m: calls.append(('manager-move',)) or (0, 4)
        model = bytearray(0x100)
        struct.pack_into('<I', model, 0x30, ACTIONS if actions else 0)
        action_table = bytearray(16 * 4)
        for k in range(4):
            struct.pack_into('<f', action_table, 16 * k + 4, speeds[k])
        fake = fake_object()
        regions = global_regions(world, scene, [
            am.defined_region('object', OBJECTS, bytes(o)),
            am.defined_region('model', MODEL, bytes(model)),
            am.defined_region('actions', ACTIONS, bytes(action_table), writable=False),
            am.defined_region('time', TIME, pack_f(time), writable=False),
            am.defined_region('hero-tile', HERO_TILE, struct.pack('<i', hero_tile), writable=False),
            am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False),
            am.defined_region('hero', HERO + 0x33ac, pack_f(*hero), writable=False),
            am.defined_region('fake', FAKE, bytes(fake), writable=False)])
        until = MOVE_SWITCH if mode == 'generic' else None
        result = run(machine, MOVE, [OBJECTS], regions, stubs, until=until)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': typ}, stop)
            continue
        guest_obj = result['regions']['object']
        if world == 0x8d and mode == 'full' and ('manager-move',) in calls:
            calls.remove(('manager-move',))
            r2 = run(machine, TORMENTA_MOVE, [OBJECTS], global_regions(world, scene, [
                am.defined_region('object', OBJECTS, guest_obj, writable=False),
                am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False),
                am.defined_region('hero', HERO + 0x33ac, pack_f(*hero), writable=False)]),
                {0x00a6ac96: sound}, ecx=FAKE + 0x100, cleanup=4)
            stop = stopped_reason(r2)
            if stop:
                t.add(False, {'case': n, 'world': world, 'type': typ, 'step': 'tormenta hook'}, stop)
                continue
        calls = [c for c in calls if c[0] != 'chain']
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        crand = MsvcRand(seed)
        rand_fn = RAND_FN(lambda ctx: crand())
        speed_fn = SPEED_FN(lambda ctx, ty, ac: speeds[ac] if 0 <= ac < 4 else math.nan)
        inputs = MoveInputs(world, scene, hero_tile, time, (ctypes.c_float * 3)(*hero), has_model, actions, speed_fn,
                            rand_fn, None)
        log = new_log()
        status = lib.dll.mu_obj_move(cobj, 0, ctypes.byref(inputs), ctypes.byref(log))
        c_calls = log_events(log)
        if mode == 'generic':
            cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
            log = new_log()
            status = lib.dll.mu_obj_move_generic(cobj, 0, ctypes.byref(inputs), ctypes.byref(log))
            c_calls = log_events(log)
        same_obj = guest_obj == cobj.raw[:OBJ_SIZE]
        if status == 2 and mode == 'full':
            t.count('unsupported (C)')
        t.count(f'{mode} world {world:#x}')
        t.count('ticked' if any(c[0] == 0x012b4dd3 for c in calls) else 'no tick')
        t.count('fire/light/sound events', sum(1 for c in calls if c[0] in (0x016cacfc, 0x0168fafd, 0x00a6ac96)))
        diff = [hex(i) for i in range(OBJ_SIZE) if guest_obj[i] != cobj.raw[i]]
        t.add(same_obj and calls == c_calls, {'case': n, 'mode': mode, 'world': world, 'type': typ, 'diff': diff[:8],
                                               'calls': calls[:4], 'c': c_calls[:4]})
    return t


# ---------------------------------------------------------------- 5b. RenderObjectVisual (Lorencia waterspout part)

def family_visual(machine, lib, g, cases):
    t = Tally('visual')
    for n in range(cases):
        o = bytearray(poison_object(g))
        put_i(o, 0x5c, 0x69)
        time = f32(g.choice([g.uniform(0, 3e7), g.uniform(0, 3000), 999.0, 1000.0, 0.0]))
        regions = global_regions(0, 6, [
            am.defined_region('object', OBJECTS, bytes(o)),
            am.defined_region('time', TIME, pack_f(time), writable=False)])
        stubs = {0x00966cc4: lambda m: FAKE, 0x00eaa8cf: lambda m: (MODEL, 4), 0x01989721: lambda m: 7}
        result = run(machine, 0x017f9758, [OBJECTS], regions, stubs, until=0x017f9880)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        lib.dll.mu_obj_visual(cobj, 0, time)
        t.add(result['regions']['object'] == cobj.raw[:OBJ_SIZE], {'case': n, 'time': time})
    return t


# ---------------------------------------------------------------- 6. render pass

def family_render_pass(machine, lib, g, cases):
    t = Tally('render_pass')
    for n in range(cases):
        world = g.choice([0, 0x8d, 10, 0x86, 0x89, 2])
        scene = g.choice([6, 6, 6, 5, 2])
        top = 1 if g.random() < 0.1 else 0
        count = g.randrange(0, 50)
        x2d, y2d = frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4

        def fields(g, o, k):
            o[0] = g.choice([0, 1, 1, 1, 1])
            o[0xb] = g.choice([0, 1])
            put_f(o, 0x158, f32((cx + g.uniform(-45, 45)) * 100), f32((cy + g.uniform(-45, 45)) * 100),
                  f32(g.uniform(0, 300)))
            put_f(o, 0xc0, f32(g.choice([-30.0, -50.0, -300.0, g.uniform(-400, 50)])))
        objects, heads, nxt = object_list(g, count, fields)
        first = [1 if g.random() < 0.1 else 0 for _ in range(count)]
        effects = [1 if g.random() < 0.15 else 0 for _ in range(count)]
        counter = g.choice([0, 5, 40, 41, 100])
        frame_time = f32(g.uniform(0, 60))
        calls = []
        index = lambda a: (a - OBJECTS) // 0x400

        def render_object(m):
            calls.append((0x016d4fe4, index(m.argument(0))) + tuple(m.argument(i) for i in range(1, 6)))
            return 0

        def visual(m):
            calls.append((0x017f9758, index(m.argument(0))))
            return 0

        def effects_update(m):
            calls.append((0x0129f671, index(m.uc.reg_read(m.x86.UC_X86_REG_ECX)), m.argument(0)))
            return (0, 4)
        stubs = {0x016d4fe4: render_object, 0x017f9758: visual, 0x0129f671: effects_update,
                 0x017fcd18: lambda m: first[index(m.argument(0))],
                 0x00d99e3f: lambda m: effects[index(m.uc.reg_read(m.x86.UC_X86_REG_ECX))]}
        regions = global_regions(world, scene, [
            am.defined_region('sectors', SECTORS, bytes(sector_bytes(heads))),
            am.defined_region('x2d', X2D, pack_f(*x2d), writable=False),
            am.defined_region('y2d', Y2D, pack_f(*y2d), writable=False),
            am.defined_region('top-view', TOP_VIEW, bytes([top]), writable=False),
            am.defined_region('counter', COUNTER, struct.pack('<i', counter)),
            am.defined_region('frame-time', FRAME_TIME, pack_f(frame_time), writable=False)] +
            [am.defined_region(f'object{k}', OBJECTS + 0x400 * k, bytes(o)) for k, o in enumerate(objects)])
        result = run(machine, RENDER_PASS, [], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        w, bufs = c_world(objects, heads, nxt)
        xs, ys = (ctypes.c_float * 4)(*x2d), (ctypes.c_float * 4)(*y2d)
        inputs = RenderInputs(world, scene, top, xs, ys, ANSWER_FN(lambda c, k: first[k]),
                              ANSWER_FN(lambda c, k: effects[k]), None, frame_time)
        ccounter = ctypes.c_int32(counter)
        log = new_log()
        lib.dll.mu_obj_render_pass(ctypes.byref(w), ctypes.byref(inputs), ctypes.byref(ccounter), ctypes.byref(log))
        c_calls = log_events(log)
        table = result['regions']['sectors']
        blocks_ok = all(table[s * 16 + 0xc] == w.block_visible[s] for s in range(256))
        objs_ok = all(result['regions'][f'object{k}'] == bufs[k].raw[:OBJ_SIZE] for k in range(count))
        globals_ok = struct.unpack('<i', result['regions']['counter'])[0] == ccounter.value and \
            struct.unpack('<i', result['regions']['world'])[0] == world
        t.count('drawn', sum(1 for c in calls if c[0] == 0x016d4fe4))
        t.count('visible sectors', sum(w.block_visible))
        t.add(calls == c_calls and blocks_ok and objs_ok and globals_ok,
              {'case': n, 'world': world, 'calls': calls[:4], 'c': c_calls[:4], 'blocks': blocks_ok, 'objects': objs_ok,
               'globals': globals_ok})
    return t


# ---------------------------------------------------------------- 7. render

def family_render(machine, lib, g, cases):
    t = Tally('render')
    grids = (light_grid(g), light_grid(g))
    sine = SIN_FN(lambda ctx, v: f32(math.sin(v)))
    for n in range(cases):
        world = g.choice([0, 0x8d, 0, 0x8d, 2, 10, 0x84, 0x14, 0x1a])
        scene = g.choice([6, 6, 5])
        o = body_light_object(g)
        typ = g.choice([g.randrange(0, 300), g.randrange(0, 300), 0x7dc, 0x444, 0x1e, 0])
        put_i(o, 0x5c, typ)
        o[3] = 1 if g.random() < 0.15 else 0
        o[0xd] = g.choice([0, 0, 1])
        o[0xe] = g.getrandbits(8)
        o[0x3b] = g.getrandbits(8)
        put_f(o, 0xdc, f32(g.choice([1.0, 1.0, 0.005, 0.5, 0.16])))
        put_i(o, 0x68, g.choice([-1, -1, -2, 3]))
        put_i(o, 0x74, g.choice([-1, -1, 1, 4]))
        put_i(o, 0x80, g.choice([0, 0, 0, 0x80]))
        put_i(o, 0x34c, 0 if g.random() < 0.95 else HERO)
        put_f(o, 0xd0, f32(g.uniform(0, 20)), f32(g.uniform(0, 20)))
        has_model = 1 if g.random() < 0.95 else 0
        chaos_flag = g.choice([0, 1])
        option = 1 if g.random() < 0.3 else 0
        bounds = 0 if g.random() < 0.85 else 1
        custom = 1 if g.random() < 0.1 else 0
        registry = 1 if g.random() < 0.1 else 0
        time = f32(g.uniform(0, 3e7))
        model = bytes(g.getrandbits(8) for _ in range(0x100))
        calls = []
        idx0 = 0

        def animation(m):
            a = [m.argument(i) for i in range(8)]
            ok = a[4] == OBJECTS + 0x164 and a[5] == OBJECTS + 0x170 and m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
            own = 1 if a[0] == BONES else 0 if a[0] == 0x06fce398 else 'bones?'
            # the last argument is a bool pushed from a dword local whose upper bytes are never written
            calls.append((0x012b5064, idx0, own, a[1], a[2], a[3], a[6], a[7] & 0xff) if ok else ('animation', a))
            return (0, 0x20)

        def transform(m):
            a = [m.argument(i) for i in range(9)]
            ok = a[1] == OBJECTS + 0x128 and a[2] == OBJECTS + 0x134 and a[3] == OBJECTS + 0x31c
            own = 1 if a[0] == BONES else 0 if a[0] == 0x06fce398 else 'bones?'
            calls.append((0x00966ea5, idx0, own, a[4], a[5], a[6], a[7], a[8]) if ok else ('transform', a))
            return (0, 0x24)

        def body(m):
            a = [m.argument(i) for i in range(8)]
            calls.append((0x00966def, idx0) + tuple(a))
            return (0, 0x20)

        def simple(call, cleanup=0, value=0):
            def stub(m):
                calls.append((call, idx0))
                return (value, cleanup)
            return stub

        def registry_found(m):
            return (registry, 4)

        def registry_call(m):
            return (1, 0)

        stubs = {0x00966cc4: lambda m: FAKE, 0x00eaa8cf: lambda m: (MODEL if has_model else 0, 4),
                 0x012b5064: animation, 0x0129f11a: lambda m: BONES, 0x00966ea5: transform,
                 0x017f9375: simple(0x017f9375), 0x017f76ec: lambda m: calls.append((0x017f76ec, idx0)) or custom,
                 0x00a170f2: lambda m: (m.argument(0), 4), 0x00a1711c: lambda m: (m.argument(0), 8),
                 0x01807a11: registry_found, 0x00a16bc0: lambda m: (FAKE + 0x10, 4),
                 VSTUB_C: registry_call,
                 0x00966def: body, 0x017f919e: simple(0x017f919e), 0x012bc07a: simple(0x012bc07a, 0x14),
                 0x0184a990: lambda m: 0, 0x009a6ef3: lambda m: FAKE, 0x009a645f: lambda m: option,
                 0x0103ec05: lambda m: 0, 0x016a88ae: lambda m: 0, 0x017f746f: simple(0x017f746f)}
        fake = fake_object()
        hero = bytearray(0x3300)
        hero[0x325c] = chaos_flag
        regions = global_regions(world, scene, [
            am.defined_region('frame-light', FRAME_LIGHT, grids[0], writable=False),
            am.defined_region('primary-light', PRIMARY_LIGHT, grids[1], writable=False),
            am.defined_region('terrain-ready', TERRAIN_READY, b'\1', writable=False),
            am.defined_region('time', TIME, pack_f(time), writable=False),
            am.defined_region('bounds', BOUNDS, struct.pack('<i', bounds), writable=False),
            am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False),
            am.defined_region('hero', HERO, bytes(hero), writable=False),
            am.undefined_region('bone-scale', 0x01cf104c, 4),
            am.defined_region('object', OBJECTS, bytes(o)),
            am.defined_region('model', MODEL, model),
            am.defined_region('fake', FAKE, bytes(fake), writable=False),
            am.undefined_region('gl-color', 0x41030000, 16)])
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        cmodel = ctypes.create_string_buffer(model, 0x100)
        gf, gp = ctypes.create_string_buffer(grids[0], GRID_BYTES), ctypes.create_string_buffer(grids[1], GRID_BYTES)
        light = LightInputs(ctypes.cast(gp, ctypes.c_void_p), ctypes.cast(gf, ctypes.c_void_p), scene, 1, time,
                            sine, None)
        inputs = DrawInputs(world, scene, has_model, chaos_flag, option, bounds, light,
                            ANSWER_FN(lambda c, k: custom), ANSWER_FN(lambda c, k: registry), None)
        log = new_log()
        status = lib.dll.mu_obj_render(cobj, 0, cmodel, 0, ctypes.byref(inputs), ctypes.byref(log))
        c_calls = log_events(log)
        if status == 2:      # a branch the C does not reconstruct (special types, shadow, owner): not compared
            t.count('unsupported (C), not compared')
            continue
        result = run(machine, RENDER, [OBJECTS, 0, 0, 0, 0xffffffff, 0xffffffff], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': typ}, stop)
            continue
        same = result['regions']['object'] == cobj.raw[:OBJ_SIZE] and \
            result['regions']['model'][:0xd0] == cmodel.raw[:0xd0]
        t.count('drawn' if any(c[0] == 0x00966def for c in calls) else 'not drawn')
        t.count('hidden -2' if struct.unpack_from('<i', o, 0x68)[0] == -2 else 'shown')
        t.add(same and calls == c_calls, {'case': n, 'world': world, 'type': typ, 'status': status,
                                          'calls': calls[:5], 'c': c_calls[:5], 'state': same})
    return t


# ---------------------------------------------------------------- driver

FAMILIES = {'light': family_light, 'body_light': family_body_light, 'create': family_create,
            'move_pass': family_move_pass, 'handler_moves': family_handler_moves, 'move': family_move, 'visual': family_visual, 'render_pass': family_render_pass,
            'render': family_render}

MUTATIONS = [
    ('terrain light without the fy term', 'object_render.c', 'a = a * fy;', 'a = a * fx;', 'light'),
    ('body light scales by 0.1 when +6 is set', 'object_render.c', 'if (!copy || !o[MU_OBJF_LIGHT_FULL])',
     'if (!copy || o[MU_OBJF_LIGHT_FULL])', 'body_light'),
    ('Lorencia tree velocity 0.4 * scale', 'object_render.c', 'float v = 1.0f / mu_obj_f32(o, MU_OBJF_SCALE);',
     'float v = mu_obj_f32(o, MU_OBJF_SCALE);', 'create'),
    ('Tormenta 0x27 keeps range -50', 'object_render.c', 'mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);   /* falls',
     'mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f);   /* falls', 'create'),
    ('move pass skips the visible test', 'object_render.c', 'if (o[MU_OBJF_LIVE] && o[MU_OBJF_VISIBLE]) {',
     'if (o[MU_OBJF_LIVE]) {', 'move_pass'),
    ('street light range 4', 'object_render.c', 'add_light(log, index, o, light, 3);\n        break;\n    }\n    case 0x96',
     'add_light(log, index, o, light, 4);\n        break;\n    }\n    case 0x96', 'move'),
    ('roof fades on HeroTile 3', 'object_render.c', 'in->hero_tile == 4 ? 0.0f : 1.0f', 'in->hero_tile == 3 ? 0.0f : 1.0f',
     'move'),
    ('sector range -180 for Tormenta', 'object_render.c', 'world == 0x8c || world == 0x8d)', 'world == 0x8c)',
     'render_pass'),
    ('hidden -2 drawn', 'object_render.c', 'mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) == -2)\n        return MU_OBJ_SKIPPED;',
     'mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) == -3)\n        return MU_OBJ_SKIPPED;', 'render'),
]


def build_library(directory):
    subprocess.run(['make', '-s', '-C', str(directory / 'objects')], check=True)
    return directory / 'objects' / f'libobjects.{SUFFIX}'


def mutations(machine, args):
    out = []
    for label, file, old, new, family in MUTATIONS:
        scratch = Path(tempfile.mkdtemp(prefix='objrender-mut-'))
        try:
            for name in ('objects', 'terrain', 'record-math', 'model-codec'):
                shutil.copytree(ROOT / 'reconstructed' / name, scratch / name,
                                ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__'))
            path = scratch / 'objects' / file
            source = path.read_text()
            if old not in source:
                out.append({'mutation': label, 'error': 'pattern not found'})
                continue
            path.write_text(source.replace(old, new, 1))
            lib = Library(build_library(scratch))
            tally = FAMILIES[family](machine, lib, random.Random(args.seed + 17), args.mutation_cases)
            out.append({'mutation': label, 'family': family, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped})
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    evidence = ROOT / 'evidence'
    if not evidence.exists():   # a worktree: the main checkout keeps the pinned captures
        evidence = Path.home() / 'Documents/main-exe-study/evidence'
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(evidence / 'x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(
        evidence / 'image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--library', default=str(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--seed', type=int, default=0x0b2e)
    parser.add_argument('--only', default=None)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--mutation-cases', type=int, default=600)
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    bodies = {name: {'start': hex(s), 'end_exclusive': hex(e),
                     'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
              for name, (s, e) in BODIES.items()}
    machine = Machine(text, data)
    lib = Library(Path(args.library))
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'bodies': bodies,
              'library_sha256': hashlib.sha256(Path(args.library).read_bytes()).hexdigest(), 'seed': args.seed,
              'families': {}}
    names = args.only.split(',') if args.only else list(FAMILIES)
    ok = True
    for name in names:
        tally = FAMILIES[name](machine, lib, random.Random(args.seed + zlib.crc32(name.encode()) % 1000), args.cases)
        r = tally.report()
        report['families'][name] = r
        ok = ok and r['mismatch_count'] == 0 and r['stopped'] == 0
        print(f"{name}: {r['equal']}/{r['cases']} equal, {r['stopped']} stopped, coverage {r['coverage']}")
        if r['examples']:
            print('  example:', json.dumps(r['examples'][0], default=str)[:600])
    if args.mutations:
        report['mutations'] = mutations(machine, args)
        for m in report['mutations']:
            print(f"mutation '{m['mutation']}': {m.get('detected')}/{m.get('cases')} detected {m.get('error', '')}")
        ok = ok and all(m.get('detected', 0) > 0 for m in report['mutations'])
    report['ok'] = ok
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    print('ALL PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
