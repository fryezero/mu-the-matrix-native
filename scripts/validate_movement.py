#!/usr/bin/env python3
"""Compare the reconstructed hero movement (reconstructed/movement) with the client's instructions.

NATIVE-WORLD-001. The client routines run in Unicorn on the pinned restored text
and second image section, through the strict machine of scripts/validate_camera.py:
every byte the guest reads must have been written by the harness or by the guest
(an undefined read stops the case), the image is read-only, imports are stubs.
Only the callees listed in each family's STUBS are replaced; their reason is
recorded in the report. Everything else (AngleMatrix, VectorRotate, the vector
accessors, the CRT sqrt/atan/sin wrappers, CreateAngle, FarAngle, TurnAngle2,
RequestTerrainHeight, SetAction, the buff list walker) runs as client code.

Families:
  angles           CreateAngle 0x012aed9e, FarAngle 0x012af218, TurnAngle2 0x012aefff
  move_path        MovePath 0x012b0846 (path spline, tile update, turn)
  height           RequestTerrainHeight 0x016cc9e2
  speed            CharacterMoveSpeed 0x013957b5 (subsystem predicates stubbed)
  position         MoveCharacterPosition 0x0137b351 (speed stubbed, height executed)
  set_action       SetAction 0x012affa4
  walk_select      SetPlayerWalk 0x0139002a up to 0x01391c19, every class byte (minimal domain)
  stop_select      player stop selector 0x01391e55, every class byte (minimal domain)
  loader_speeds    player loader block 0x018311f7..0x018321e1 (action PlaySpeeds)

Usage:
  python3 scripts/validate_movement.py --text .../client-text.bin --data .../client-image-data.bin \
      [--cases N] [--mutations] [--output report.json]
"""

import argparse
import ctypes
import hashlib
import importlib.util
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

ROOT = Path(__file__).resolve().parents[1]


def load_camera_validator():
    """The strict Unicorn machine of the camera validator, without its stubs."""
    spec = importlib.util.spec_from_file_location('validate_camera_movement', ROOT / 'scripts/validate_camera.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CLIENT_STUBS = {}
    return module


vc = load_camera_validator()
f32, fbits, same = vc.f32, vc.fbits, vc.same

# Routine bodies pinned by SHA-256 of the restored bytes (start, length, digest).
ROUTINES = {
    'create_angle': (0x012aed9e, 0x16e, 'b137f7a4e29666ed59bc3c55dc86aa0b37590db18e7fb72ae242994f0d5dad84'),
    'turn_angle2': (0x012aefff, 0x219, 'fa3840961f3436d9610d0ecd4dc44ffa0f73e526721b0b605e023d25fd926cac'),
    'far_angle': (0x012af218, 0xd9, 'c76fceeda168562e10034d4f05c954f7dc79fb0af0cd5d980677c3f7f4a30bff'),
    'move_path': (0x012b0846, 0x61f, 'dee0f6b9e70f485a900c7c2b6038e9a7dcfb21a38783b831170495fbffca819c'),
    'set_action': (0x012affa4, 0x76, '1505c3f4e0493da318652a309ee428994c61a86629902a9ceeba87acfecbda85'),
    'move_position': (0x0137b351, 0x33b, '2c1235b690c6d2f7330a5e44cc7fda6ba6d1d2fd4818860bf76c4605ca77b2e8'),
    'move_speed': (0x013957b5, 0x7b1, 'e1978e20f0e66b199628d64c4d996d24088cc4be4845117fb99f8f58544f46a4'),
    'request_height': (0x016cc9e2, 0x1d4, '5e23257f18274a1ba3cef6d55cb27e57474682e52fdfdc629ec2476f96f58d72'),
    'set_player_walk': (0x0139002a, 0x1e2b, 'ec4b52ccd891fda86a186abf97e36b37f600073c1cc7ca11a3979f0cdd4ece41'),
    'player_stop_select': (0x01391e55, 0xc88, 'ebb5b79bfe91918e584069d06aef1472630340ac053d7f653deae1bd27098dee'),
    'player_loader_speeds': (0x018311f7, 0xfea, 'd0db6d0290ca9e9b0cc886e88d58dfe60945c57b26c1e410e6a8f185847e0d53'),
}

CHKSTK_PROBE = 0x0191c5c7   # `test [eax], eax` page probe of _chkstk 0x0191c5a0 (value not consumed)
HERO = 0x0a39d754
WORLD = 0x01cf15fc
SCENE = 0x01d1df70
SPECIAL_HEIGHT = 0x01cf15dc
HEIGHT = 0x0b6f5420
WALL = 0x0b795420
ARENA = vc.ARENA
CHAR = ARENA + 0x1000            # CHARACTER record (0x3800 bytes)
OBJ = CHAR + 0x3254              # its OBJECT
CONT = ARENA + 0x8000            # model container / subsystem objects
MODEL = ARENA + 0x9000           # Player BMD record (0xd0 bytes)
ACT = ARENA + 0xa000             # action records, 16 bytes each
ITEM = ARENA + 0xe000
STATS = ARENA + 0x10000


class MovementGuest(vc.Guest):
    def _constant_store(self, eip):
        if eip == CHKSTK_PROBE:
            return True
        return super()._constant_store(eip)


# ---------------- authored library ----------------

class Path_(ctypes.Structure):
    _fields_ = [('current', ctypes.c_uint8), ('current_float', ctypes.c_uint8), ('count', ctypes.c_uint8),
                ('x', ctypes.c_uint8 * 15), ('y', ctypes.c_uint8 * 15)]


class SpeedInput(ctypes.Structure):
    _fields_ = [('move_speed', ctypes.c_uint16), ('object_type', ctypes.c_int32), ('object_kind', ctypes.c_uint8),
                ('special_state', ctypes.c_uint8), ('helper_type', ctypes.c_uint16), ('mount_type', ctypes.c_int32),
                ('helper_option', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8), ('subtype', ctypes.c_int32),
                ('mounted_item', ctypes.c_uint8), ('wing_type', ctypes.c_int16), ('transformed', ctypes.c_uint8),
                ('world_runs', ctypes.c_uint8), ('stunned', ctypes.c_uint8), ('buffs', ctypes.c_uint32),
                ('buff_18b_bonus', ctypes.c_double)]


class PositionInput(ctypes.Structure):
    _fields_ = [('speed', ctypes.c_float), ('world', ctypes.c_int32), ('helper_type', ctypes.c_uint16),
                ('safe_zone', ctypes.c_uint8), ('object_type', ctypes.c_int32),
                ('height', ctypes.POINTER(ctypes.c_float)), ('wall', ctypes.POINTER(ctypes.c_uint16)),
                ('special_height', ctypes.c_float), ('scene_state', ctypes.c_int32)]


BUFF_IDS = [0x18b, 0x38, 0xb8, 0xba, 0xd1, 0xd2, 0xf0, 0x56, 0x112, 0x116, 0x20]


def load_library(directory=None):
    directory = Path(directory) if directory else ROOT / 'reconstructed' / 'movement'
    subprocess.run(['make', '-C', str(directory)], check=True, capture_output=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(directory / f'libclient_movement.{suffix}'))
    F, I, U8, P = ctypes.c_float, ctypes.c_int32, ctypes.c_uint8, ctypes.POINTER
    sig = {
        'mu_create_angle': ([F, F, F, F], F),
        'mu_far_angle': ([F, F, U8], F),
        'mu_turn_angle2': ([F, F, F], F),
        'mu_move_path': ([P(Path_), P(I), P(F), P(F), U8], ctypes.c_int),
        'mu_request_terrain_height': ([P(F), P(ctypes.c_uint16), F, I, F, F], F),
        'mu_character_move_speed': ([P(SpeedInput), P(U8)], F),
        'mu_move_character_position': ([P(PositionInput), P(F), P(F), P(F)], None),
        'mu_set_action': ([P(ctypes.c_uint16), P(ctypes.c_uint16), P(F), P(F), I, I], ctypes.c_int),
        'mu_player_walk_run': ([U8, U8, I, U8], U8),
        'mu_player_walk_action': ([U8, U8, P(F)], I),
        'mu_player_stop_action': ([U8], I),
        'mu_player_stop_speed': ([I], F),
    }
    for name, (args, result) in sig.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


def floats(*values):
    return (ctypes.c_float * len(values))(*values)


class Tally(vc.Tally):
    pass


# ---------------- helpers ----------------

class Stubs:
    """Per-case values for the replaced callees; reasons go into the report."""

    def __init__(self, guest):
        self.guest = guest
        self.values = {}
        self.reasons = {}

    def add(self, address, cleanup, reason, kind='eax', fn=None):
        self.reasons[address] = reason
        if fn is None:
            def fn(args, ecx, a=address):
                return self.values.get(a, 0)
        self.guest.stub_client(address, cleanup, fn, kind=kind)


def bits(value):
    return fbits(value)


def interesting_float(generator, scale=25600.0):
    r = generator.random()
    if r < 0.03:
        return math.nan
    if r < 0.05:
        return generator.choice([math.inf, -math.inf])
    if r < 0.10:
        return generator.choice([0.0, -0.0, 1e-5, -1e-5, 5e-5, -5e-5, 1e-4, -1e-4])
    return f32(generator.uniform(-scale, scale))


def compare_float(tally, name, client, authored, detail):
    tally.add(name, same(f32(client), f32(authored)), dict(detail, client=client, authored=authored))


# ---------------- families ----------------

def case_angles(guest, lib, tally, generator, count):
    for _ in range(count):
        guest.reset_memory() if generator.random() < 0.02 else None
        x1, y1 = f32(generator.uniform(0, 25600)), f32(generator.uniform(0, 25600))
        r = generator.random()
        if r < 0.1:
            x2, y2 = x1, f32(y1 + generator.uniform(-300, 300))
        elif r < 0.2:
            x2, y2 = f32(x1 + generator.uniform(-300, 300)), y1
        elif r < 0.3:   # around the 0.0001 threshold of the axis cases
            x2, y2 = f32(x1 + generator.uniform(-1.5e-3, 1.5e-3)), f32(y1 + generator.uniform(-300, 300))
            if generator.random() < 0.5:
                x1, x2 = 0.0, f32(generator.uniform(-1.5e-3, 1.5e-3))
        elif r < 0.35:
            x1, y1, x2, y2 = (interesting_float(generator) for _ in range(4))
        else:
            x2, y2 = f32(x1 + generator.uniform(-1500, 1500)), f32(y1 + generator.uniform(-1500, 1500))
        guest.call(0x012aed9e, [bits(x1), bits(y1), bits(x2), bits(y2)])
        compare_float(tally, 'create_angle 0x012aed9e', guest.st0(), lib.mu_create_angle(x1, y1, x2, y2),
                      {'args': [x1, y1, x2, y2]})
        a = generator.choice([f32(generator.uniform(-360, 720)), f32(generator.uniform(0, 360)),
                              float(generator.randrange(-8, 16) * 45), interesting_float(generator, 400)])
        t = generator.choice([f32(generator.uniform(-360, 720)), f32(generator.uniform(0, 360)),
                              f32(a + generator.uniform(-200, 200)), float(generator.randrange(-8, 16) * 45)])
        flag = generator.choice([0, 1, 1, 2])
        guest.call(0x012af218, [bits(a), bits(t), flag | (generator.getrandbits(8) << 8 if flag else 0)])
        compare_float(tally, 'far_angle 0x012af218', guest.st0(), lib.mu_far_angle(a, t, flag), {'args': [a, t, flag]})
        d = generator.choice([f32(generator.uniform(0, 45)), f32(generator.uniform(0, 200)), 22.5, 0.0])
        guest.call(0x012aefff, [bits(a), bits(t), bits(d)])
        compare_float(tally, 'turn_angle2 0x012aefff', guest.st0(), lib.mu_turn_angle2(a, t, d), {'args': [a, t, d]})


def random_path(generator):
    count = generator.choice([1, 2, 3, 4, 8, 15, generator.randint(1, 15)])
    x, y = generator.randint(1, 254), generator.randint(1, 254)
    xs, ys = [], []
    for _ in range(15):
        xs.append(x & 0xff)
        ys.append(y & 0xff)
        x += generator.choice([-1, 0, 1])
        y += generator.choice([-1, 0, 1])
    current = generator.choice([0, 0, 1, generator.randint(0, count), count, min(count + 1, 255)])
    current_float = generator.choice([0, 0, 1, 2, 3, generator.randint(0, 6)])
    return count, current, current_float, xs, ys


SPLINE = {0: (-0.0703125, 0.8671875, 0.2265625, -0.0234375), 1: (-0.0625, 0.5625, 0.5625, -0.0625),
          2: (-0.0234375, 0.2265625, 0.8671875, -0.0703125)}


def spline_point(n, current, current_float, xs, ys):
    """Independent statement of MovePath's spline point (binary32, source order)."""
    px, py = [], []
    for i in range(4):
        cell = min(max(current + i - 1, 0), n - 1)
        px.append(f32(f32(xs[cell] + 0.5) * 100.0))
        py.append(f32(f32(ys[cell] + 0.5) * 100.0))
    if current_float == 3:
        return px[2], py[2]
    if current_float not in SPLINE:
        return 0.0, 0.0
    w = SPLINE[current_float]

    def mix(v):
        t = f32(f32(v[0] * w[0]) + f32(v[1] * w[1]))
        t = f32(t + f32(v[2] * w[2]))
        return f32(t + f32(v[3] * w[3]))
    return mix(px), mix(py)


def case_move_path(guest, lib, tally, generator, count):
    for _ in range(count):
        guest.reset_memory()
        n, current, current_float, xs, ys = random_path(generator)
        aligned = generator.random() < 0.25
        if aligned:   # a straight column of cells: the spline x is exact, so FarAngle can be exactly 45
            xs = [xs[0]] * 15
        cell = min(max(current, 0), n - 1)
        cx, cy = (xs[cell] + 0.5) * 100, (ys[cell] + 0.5) * 100
        spread = generator.choice([5, 25, 40, 120, 400])
        position = [f32(cx + generator.uniform(-spread, spread)), f32(cy + generator.uniform(-spread, spread)),
                    f32(generator.uniform(0, 400))]
        if aligned:
            position[0] = f32(cx)
        if generator.random() < 0.15 and current < n:   # exactly at the (int) 30 arrival radius
            tx, ty = spline_point(n, current, current_float, xs, ys)
            position[0], position[1] = f32(tx + generator.choice([30.0, 30.5, 31.0, -30.0, 29.75])), ty
        angles = [f32(generator.uniform(-90, 0)), 0.0, f32(generator.choice([generator.uniform(-360, 720),
                                                                              generator.randrange(0, 8) * 45.0]))]
        tile = [generator.randint(0, 255), generator.randint(0, 255)]
        turn = generator.choice([0, 1, 1, 1, 2])
        record = bytes([current, current_float, n]) + bytes(xs) + bytes(ys)
        guest.put(CHAR + 0x3194, record)
        guest.put(CHAR + 0x180, struct.pack('<ii', *tile))
        guest.put(OBJ + 0x158, struct.pack('<3f', *position))
        guest.put(OBJ + 0x164, struct.pack('<3f', *angles))
        result = guest.call(0x012b0846, [CHAR, turn]) & 0xff
        path = Path_(current, current_float, n, (ctypes.c_uint8 * 15)(*xs), (ctypes.c_uint8 * 15)(*ys))
        ctile = (ctypes.c_int32 * 2)(*tile)
        cpos, cang = floats(*position), floats(*angles)
        mine = lib.mu_move_path(ctypes.byref(path), ctile, cpos, cang, turn)
        client_path = guest.get(CHAR + 0x3194, 33)
        ok = (result == mine and client_path == bytes(path)[:33]
              and list(struct.unpack('<ii', guest.get(CHAR + 0x180, 8))) == list(ctile)
              and all(same(a, b) for a, b in zip(struct.unpack('<3f', guest.get(OBJ + 0x158, 12)), cpos))
              and all(same(a, b) for a, b in zip(struct.unpack('<3f', guest.get(OBJ + 0x164, 12)), cang)))
        tally.add('move_path 0x012b0846', ok, {'record': record.hex(), 'pos': position, 'angles': angles,
                                               'turn': turn, 'client': result, 'authored': mine})


def random_grid(generator):
    style = generator.random()
    heights = []
    for i in range(65536):
        if style < 0.5:
            heights.append(float((i * 2654435761 >> 20) % 256) * 1.5)
        else:
            heights.append(f32(generator.uniform(-500, 1500)) if (i & 7) == 0 else float(i % 97) * 3.0)
    walls = [generator.choice([0, 0, 0, 1, 4, 0x40, 0x41, 0x80]) if generator.random() < 0.2 else 0 for _ in range(65536)]
    return heights, walls


def put_grid(guest, heights, walls, special):
    guest.put(HEIGHT, struct.pack('<65536f', *heights))
    guest.put(WALL, struct.pack('<65536H', *walls))
    guest.put(SPECIAL_HEIGHT, struct.pack('<f', special))


def case_height(guest, lib, tally, generator, count, stubs):
    grids = max(2, count // 200)
    per = max(1, count // grids)
    for _ in range(grids):
        guest.reset_memory()
        heights, walls = random_grid(generator)
        special = f32(generator.choice([0.0, 1201.0, generator.uniform(-100, 500)]))
        put_grid(guest, heights, walls, special)
        h = (ctypes.c_float * 65536)(*heights)
        w = (ctypes.c_uint16 * 65536)(*walls)
        for _ in range(per):
            scene = generator.choice([6, 6, 6, 6, 1, 2, 3, 4, 5])
            stubs.values[0x009b0bc1] = scene
            r = generator.random()
            if r < 0.08:
                x, y = interesting_float(generator, 30000), interesting_float(generator, 30000)
            elif r < 0.15:
                x, y = float(generator.randint(0, 25700)), float(generator.randint(0, 25700))
            else:
                x, y = f32(generator.uniform(0, 25599.9)), f32(generator.uniform(0, 25599.9))
            guest.call(0x016cc9e2, [bits(x), bits(y)])
            compare_float(tally, 'request_height 0x016cc9e2', guest.st0(),
                          lib.mu_request_terrain_height(h, w, special, scene, x, y), {'xy': [x, y], 'scene': scene})


def case_speed(guest, lib, tally, generator, count, stubs):
    for _ in range(count):
        guest.reset_memory()
        s = SpeedInput()
        s.move_speed = generator.choice([0, 10, 12, 15, generator.randint(0, 65535)])
        s.object_type = generator.choice([0xa91, 0xa91, 0xa91, 0x7a7, generator.randint(0, 0x4000)])
        s.object_kind = generator.choice([1, 1, 1, 0, 2, 8])
        s.special_state = 1 if generator.random() < 0.05 else 0
        helpers = [0xffff, 0xffff, 0xffff, 0x1833, 0x1836, 0x1853, 0x185e, 0x184b, 0x184c, 0x19d7, 0x19e3, 0x19e4,
                   0x1a02, 0x1a03, 0x1a04, 0x28f7, 0x1a25, 0x1a00, generator.randint(0, 0xffff)]
        s.helper_type = generator.choice(helpers)
        s.mount_type = generator.choice([0xffff, 0xffff, 0x1a25, 0x1a04, 0x1a03, 0x184b, 0x12345, -1])
        s.helper_option = generator.choice([0, 0, 1, 7])
        s.safe_zone = generator.choice([0, 0, 1, 2])
        s.subtype = generator.choice([0, 0, 0x431, 0x432, 7])
        s.mounted_item = 1 if generator.random() < 0.1 else 0
        s.wing_type = generator.choice([-1, -1, -1, 0x22eb, 0x230a, 0x248d, 0x2495, 0x1800, 0x2400])
        s.transformed = 1 if generator.random() < 0.05 else 0
        world_result = generator.choice([0, 0, 0, 1, 2])
        s.world_runs = 1 if world_result == 1 else 0
        s.stunned = 1 if generator.random() < 0.05 else 0
        s.buffs = 0
        for k in range(len(BUFF_IDS)):
            if generator.random() < 0.08:
                s.buffs |= 1 << k
        bonus = f32(generator.choice([0.0, 1.5, 3.0, generator.uniform(-5, 5)]))
        s.buff_18b_bonus = bonus
        run = generator.choice([0, 5, 9, 10, 19, 20, 39, 40, 41, 255])
        world = generator.choice([0, 3, 0x84])
        ch = bytearray(0x3800)
        ch[4] = s.safe_zone
        ch[0x24] = run
        struct.pack_into('<H', ch, 0x14c, s.move_speed)
        ch[0x190] = s.stunned
        struct.pack_into('<h', ch, 0x21a4, s.wing_type)
        ch[0x299f] = s.helper_option
        struct.pack_into('<i', ch, 0x32b0, s.object_type)
        struct.pack_into('<i', ch, 0x32b4, s.subtype)
        ch[0x3254 + 0x3b] = s.object_kind
        guest.put(CHAR, bytes(ch))
        guest.put(WORLD, struct.pack('<i', world))
        high = generator.getrandbits(16) << 16
        stubs.values.update({0x009fa30a: CONT, 0x009fbb31: s.special_state | (high & 0xffffff00),
                             0x0129dcda: s.helper_type | high, 0x0106c5e9: s.mount_type & 0xffffffff,
                             0x0139fcbf: s.mounted_item | (high & 0xffffff00), 0x00b9929c: s.transformed | (high & 0xffffff00),
                             0x009dacb8: world_result | (high & 0xffffff00), 0x00966c42: CONT + 0x40, 0x0117b5eb: bonus})
        stubs.buffs = s.buffs
        saved = guest.client_stubs.pop(0x013957b5, None)   # the routine under test runs as client code
        try:
            guest.call(0x013957b5, [CHAR])
        finally:
            if saved is not None:
                guest.client_stubs[0x013957b5] = saved
        client = guest.st0()
        client_run = guest.get(CHAR + 0x24, 1)[0]
        crun = ctypes.c_uint8(run)
        mine = lib.mu_character_move_speed(ctypes.byref(s), ctypes.byref(crun))
        ok = same(f32(client), f32(mine)) and client_run == crun.value
        tally.add('move_speed 0x013957b5', ok, {'input': {k: getattr(s, k) for k, _ in SpeedInput._fields_},
                                                'run': run, 'client': [client, client_run], 'authored': [mine, crun.value]})


def case_position(guest, lib, tally, generator, count, stubs):
    grids = max(2, count // 150)
    per = max(1, count // grids)
    for _ in range(grids):
        heights, walls = random_grid(generator)
        special = f32(generator.choice([0.0, 1201.0]))
        h = (ctypes.c_float * 65536)(*heights)
        w = (ctypes.c_uint16 * 65536)(*walls)
        for k in range(per):
            guest.reset_memory()
            put_grid(guest, heights, walls, special)
            p = PositionInput()
            p.speed = f32(generator.choice([12.0, 15.0, 8.0, 17.0, generator.uniform(0, 40)]))
            p.world = generator.choice([0, 0, -1, 8, 10, 0x84, 3])
            p.helper_type = generator.choice([0xffff, 0x1a03, 0x1a03, 0x1a25])
            p.safe_zone = generator.choice([0, 1, 2])
            p.object_type = generator.choice([0xa91, 0xa91, 0x7a7])
            p.height, p.wall, p.special_height = h, w, special
            p.scene_state = generator.choice([6, 6, 6, 2])
            position = [f32(generator.uniform(100, 25500)), f32(generator.uniform(100, 25500)), f32(generator.uniform(0, 500))]
            angles = [f32(generator.choice([0.0, generator.uniform(-90, 90)])), 0.0,
                      f32(generator.choice([generator.uniform(-360, 720), generator.randrange(0, 8) * 45.0]))]
            timer = f32(generator.uniform(0, 50))
            ch = bytearray(0x3800)
            ch[4] = p.safe_zone
            struct.pack_into('<i', ch, 0x32b0, p.object_type)
            struct.pack_into('<f', ch, 0x3254 + 0xb4, timer)
            struct.pack_into('<3f', ch, 0x3254 + 0x158, *position)
            struct.pack_into('<3f', ch, 0x3254 + 0x164, *angles)
            guest.put(CHAR, bytes(ch))
            guest.put(WORLD, struct.pack('<i', p.world))
            stubs.values.update({0x013957b5: p.speed, 0x0129dcda: p.helper_type | (generator.getrandbits(16) << 16),
                                 0x009b0bc1: p.scene_state})
            guest.call(0x0137b351, [CHAR])
            cpos, cang, ctimer = floats(*position), floats(*angles), ctypes.c_float(timer)
            lib.mu_move_character_position(ctypes.byref(p), cpos, cang, ctypes.byref(ctimer))
            client_pos = struct.unpack('<3f', guest.get(OBJ + 0x158, 12))
            client_timer = struct.unpack('<f', guest.get(OBJ + 0xb4, 4))[0]
            ok = all(same(a, b) for a, b in zip(client_pos, cpos)) and same(client_timer, ctimer.value)
            tally.add('move_position 0x0137b351', ok, {'pos': position, 'angles': angles, 'speed': p.speed,
                                                       'world': p.world, 'client': list(client_pos),
                                                       'authored': list(cpos)})


def case_set_action(guest, lib, tally, generator, count, stubs):
    for _ in range(count):
        guest.reset_memory()
        n = generator.choice([0, 1, 10, 0x186, 0x186, -3])
        null_model = generator.random() < 0.05
        model = bytearray(0xd0)
        struct.pack_into('<h', model, 0x26, n)
        guest.put(MODEL, bytes(model))
        guest.put(CONT, bytes(0x40))
        stubs.values.update({0x00966cc4: CONT, 0x00eaa8cf: 0 if null_model else MODEL})
        action, prior = generator.randint(0, 0x190), generator.randint(0, 0x190)
        frame, prior_frame = f32(generator.uniform(0, 20)), f32(generator.uniform(0, 20))
        new = generator.choice([action, generator.randint(0, 0x190), 0x186, 0x185, -1 & 0xffffffff, 0x7fffffff])
        ob = bytearray(0x400)
        struct.pack_into('<i', ob, 0x5c, 0xa91)
        struct.pack_into('<HH', ob, 0x2a, action, prior)
        struct.pack_into('<ff', ob, 0xd0, frame, prior_frame)
        guest.put(OBJ, bytes(ob))
        guest.call(0x012affa4, [OBJ, new])
        a, b = ctypes.c_uint16(action), ctypes.c_uint16(prior)
        fa, fb = ctypes.c_float(frame), ctypes.c_float(prior_frame)
        if not null_model:
            lib.mu_set_action(ctypes.byref(a), ctypes.byref(b), ctypes.byref(fa), ctypes.byref(fb), n,
                              struct.unpack('<i', struct.pack('<I', new & 0xffffffff))[0])
        ca, cb = struct.unpack('<HH', guest.get(OBJ + 0x2a, 4))
        cfa, cfb = struct.unpack('<ff', guest.get(OBJ + 0xd0, 8))
        ok = ca == a.value and cb == b.value and same(cfa, fa.value) and same(cfb, fb.value)
        tally.add('set_action 0x012affa4', ok, {'n': n, 'new': new, 'client': [ca, cb, cfa, cfb],
                                                'authored': [a.value, b.value, fa.value, fb.value]})


def player_record(class_byte, safe, run, action=0x7fff):
    """Unarmed, unequipped Player character: every byte zero except the listed fields."""
    ch = bytearray(0x3800)
    ch[4] = safe
    ch[0x12] = class_byte
    ch[0x24] = run
    for k in range(6):
        struct.pack_into('<h', ch, 0x1c4 + k * 0x3fc, -1)
    struct.pack_into('<h', ch, 0x19ac, -1)
    struct.pack_into('<h', ch, 0x19ac + 0x3fc, -1)
    struct.pack_into('<h', ch, 0x21a4, -1)
    struct.pack_into('<h', ch, 0x299c, -1)
    struct.pack_into('<i', ch, 0x32b0, 0xa91)
    struct.pack_into('<H', ch, 0x3254 + 0x2a, action)
    return bytes(ch)


LOADER_TABLE = {}


def loader_action_table(guest, stubs):
    """Player action records as the loader block 0x018311f7..0x018321e1 leaves them (executed once)."""
    if 'table' not in LOADER_TABLE:
        guest.reset_memory()
        model = bytearray(0xd0)
        struct.pack_into('<h', model, 0x26, 0x186)
        struct.pack_into('<I', model, 0x30, ACT)
        guest.put(MODEL, bytes(model))
        guest.put(ACT, bytes(0x186 * 16))
        guest.put(CONT, bytes(0x40))
        stubs.values.update({0x00966cc4: CONT, 0x0142fc46: MODEL})
        run_range(guest, 0x018311f7, 0x018321e1)
        LOADER_TABLE['table'] = guest.get(ACT, 0x186 * 16)
    return LOADER_TABLE['table']


def player_world(guest, world, table):
    model = bytearray(0xd0)
    struct.pack_into('<h', model, 0x26, 0x186)
    struct.pack_into('<I', model, 0x30, ACT)
    guest.put(MODEL, bytes(model))
    guest.put(ACT, table)
    guest.put(CONT, bytes(0x100))
    guest.put(ITEM, bytes(0x400))
    guest.put(STATS, bytes(0x3000))
    guest.put(0x01d1df18, struct.pack('<I', STATS))     # skill/stat table pointer (all zero)
    guest.put(0x01d1e028, bytes(8))                     # flight-state object (+4 = 0)
    guest.put(SCENE, struct.pack('<i', 6))
    guest.put(WORLD, struct.pack('<i', world))
    guest.put(HERO, struct.pack('<I', CHAR))


# The minimal domain of the walk/stand selection: model and item records as
# above, no mount or ride state, no mounted item, no buff (stubs.buffs = 0),
# world predicate 0x009dacb8 false, scene state 6.
MINIMAL_DOMAIN = {0x00966cc4: CONT, 0x00eaa8cf: MODEL, 0x00cd4ea8: CONT + 0x40, 0x00cd5d29: ITEM,
                  0x009c104e: CONT + 0x80, 0x0106bdb7: 0, 0x0106bd76: 0, 0x0139fcbf: 0, 0x009dacb8: 0,
                  0x009b0bc1: 6, 0x0129dcda: 0xffff}


def case_walk_select(guest, lib, tally, generator, count, stubs):
    table = loader_action_table(guest, stubs)
    stubs.values.update(MINIMAL_DOMAIN)
    stubs.buffs = 0
    runs = [0, 1, 38, 39, 40, 41, 255]
    combos = [(c, s, r, w) for c in range(256) for s in (0, 1, 2) for r in runs for w in (0,)]
    if count < len(combos):
        combos = [combos[i] for i in sorted(generator.sample(range(len(combos)), count))]
    for class_byte, safe, run, world in combos:
        guest.reset_memory()
        player_world(guest, world, table)
        guest.put(CHAR, player_record(class_byte, safe, run))
        guest.call(0x0139002a, [CHAR], until=0x01391c19, count=3000000)
        action = struct.unpack('<H', guest.get(OBJ + 0x2a, 2))[0]
        new_run = guest.get(CHAR + 0x24, 1)[0]
        speed = struct.unpack('<f', guest.get(ACT + 16 * action + 4, 4))[0]
        mine_run = lib.mu_player_walk_run(class_byte, safe, world, run)
        mspeed = ctypes.c_float()
        mine = lib.mu_player_walk_action(class_byte, mine_run, ctypes.byref(mspeed))
        ok = action == mine and new_run == mine_run and same(speed, mspeed.value)
        tally.add('walk_select 0x0139002a', ok, {'class': class_byte, 'safe': safe, 'run': run, 'world': world,
                                                 'client': [action, new_run, speed],
                                                 'authored': [mine, mine_run, mspeed.value]})


def case_stop_select(guest, lib, tally, generator, count, stubs):
    table = loader_action_table(guest, stubs)
    stubs.values.update(MINIMAL_DOMAIN)
    stubs.buffs = 0
    for class_byte in range(256):
        for safe in (0, 1):
            guest.reset_memory()
            player_world(guest, 0, table)
            guest.put(CHAR, player_record(class_byte, safe, 10, action=0x32))
            guest.call(0x01391e55, [CHAR], count=3000000)
            action = struct.unpack('<H', guest.get(OBJ + 0x2a, 2))[0]
            mine = lib.mu_player_stop_action(class_byte)
            tally.add('stop_select 0x01391e55', action == mine, {'class': class_byte, 'safe': safe,
                                                                 'client': action, 'authored': mine})


def case_loader_speeds(guest, lib, tally, generator, count, stubs):
    raw = loader_action_table(guest, stubs)
    table = {}
    for i in range(0x186):
        record = raw[16 * i:16 * i + 16]
        table[i] = (record[0], struct.unpack_from('<f', record, 4)[0])
    for action in (1, 2, 3, 5, 6, 8):
        tally.add('loader_speeds 0x018311f7', same(table[action][1], lib.mu_player_stop_speed(action)),
                  {'action': action, 'client': table[action][1], 'authored': lib.mu_player_stop_speed(action)})
    return {hex(i): [loop, speed] for i, (loop, speed) in table.items() if loop or speed}


def run_range(guest, start, until, frame_size=0x400, count=5000000):
    """Runs a straight block inside a function body with a fresh EBP frame (locals undefined)."""
    uc, x = guest.uc, guest.x
    guest.violation = None
    guest.calls = []
    ebp = vc.INITIAL_ESP - 0x200
    uc.reg_write(x.UC_X86_REG_ESP, ebp - frame_size)
    uc.reg_write(x.UC_X86_REG_EBP, ebp)
    for reg in (x.UC_X86_REG_EAX, x.UC_X86_REG_ECX, x.UC_X86_REG_EDX, x.UC_X86_REG_EBX, x.UC_X86_REG_ESI,
                x.UC_X86_REG_EDI):
        uc.reg_write(reg, 0xdeadbeef)
    uc.reg_write(x.UC_X86_REG_EFLAGS, 2)
    uc.reg_write(x.UC_X86_REG_FPCW, vc.FPCW)
    uc.reg_write(x.UC_X86_REG_MXCSR, vc.MXCSR)
    error = None
    try:
        uc.emu_start(start, until, count=count)
    except guest.u.UcError as failure:
        error = str(failure)
    if guest.violation or error or uc.reg_read(x.UC_X86_REG_EIP) != until:
        raise vc.Stop(f'{hex(start)}: {guest.violation or error or "stopped"}')


STUB_TABLE = [
    # address, cleanup, kind, reason
    (0x009b0bc1, 0, 'eax', 'scene-state getter on 0x01d1df70 (RequestTerrainHeight): synthetic scene'),
    (0x009fa30a, 0, 'eax', 'singleton getter (CharacterMoveSpeed special state)'),
    (0x009fbb31, 4, 'eax', 'special-state predicate (speed 8)'),
    (0x0129dcda, 0, 'eax', 'helper item type of the character (pets/mounts): synthetic, garbage upper bits'),
    (0x0106c5e9, 0, 'eax', 'second mount type query'),
    (0x0139fcbf, 0, 'eax', 'mounted-item predicate'),
    (0x00b9929c, 0, 'eax', 'transformation predicate (speed 20)'),
    (0x009dacb8, 0, 'eax', 'world predicate forcing run speed'),
    (0x00966c42, 0, 'eax', 'skill/option table lookup (buff 0x18b bonus argument)'),
    (0x0117b5eb, 0, 'float', 'buff 0x18b speed bonus value'),
    (0x013957b5, 0, 'float', 'CharacterMoveSpeed, compared separately; MoveCharacterPosition gets the speed'),
    (0x00966cc4, 0, 'eax', 'model container getter'),
    (0x00eaa8cf, 4, 'eax', 'model lookup by type: the synthetic Player BMD record'),
    (0x00d33153, 4, 'eax', 'Player action record accessor: synthetic action array'),
    (0x00cd4ea8, 0, 'eax', 'item attribute table getter'),
    (0x00cd5d29, 4, 'eax', 'item attribute record (all zero, unarmed)'),
    (0x009c104e, 0, 'eax', 'character extra-state manager getter'),
    (0x0106bdb7, 4, 'eax', 'mount/ride predicate: not riding'),
    (0x0106bd76, 4, 'eax', 'mount/ride predicate: not riding'),
    (0x0142fc46, 0, 'eax', 'Player BMD getter in the loader block'),
]


def install_stubs(guest):
    stubs = Stubs(guest)
    stubs.buffs = 0

    def buff(args, ecx):
        identifier = args[0] & 0xffffffff
        return 1 if identifier in BUFF_IDS and stubs.buffs & (1 << BUFF_IDS.index(identifier)) else 0

    for address, cleanup, kind, reason in STUB_TABLE:
        stubs.add(address, cleanup, reason, kind=kind)
    stubs.add(0x01295ade, 4, 'buff predicate on the character buff list: synthetic set', fn=buff)
    stubs.add(0x00d33153, 4, 'Player action record accessor: synthetic action array',
              fn=lambda args, ecx: ACT + 16 * (args[0] & 0xffff))
    return stubs


MUTATIONS = [
    ('near-zero threshold 0.001', 'if (0.0001f > client_fabs(nx))', 'if (0.001f > client_fabs(nx))', 'angles'),
    ('far angle abs for any flag', 'if (abs_flag == 1 && 0.0f > d)', 'if (abs_flag && 0.0f > d)', 'angles'),
    ('turn target wrap at 0', 'if (0.0f > target)\n        target = target + 360.0f;\n    if (180.0f > a) {', 'if (0.0f >= target)\n        target = target + 360.0f;\n    if (180.0f > a) {', 'angles'),
    ('arrival radius < 30', 'if (cvtt(distance) <= 30) {', 'if (cvtt(distance) < 30) {', 'move_path'),
    ('spline weights swapped', 'tx = tx + px[2] * 0.2265625f;', 'tx = tx + px[2] * 0.8671875f;', 'move_path'),
    ('snap at > 45', 'if (far >= 45.0f)', 'if (far > 45.0f)', 'move_path'),
    ('height x before y', 'left = left * yd;', 'left = left * xd;', 'height'),
    ('walk speed 10', 'speed = *run < 40 ? 12.0f : 15.0f;', 'speed = *run < 40 ? 10.0f : 15.0f;', 'speed'),
    ('dinorant +50', 'position[2] = ground + 30.0f;', 'position[2] = ground + 50.0f;', 'position'),
    ('velocity +y', 'float velocity[3] = {0.0f, -in->speed, 0.0f}', 'float velocity[3] = {0.0f, in->speed, 0.0f}',
     'position'),
    ('set action at count', 'if (new_action >= action_count)', 'if (new_action > action_count)', 'set_action'),
    ('class 7 male walk', '{0, 0, 1, 0, 0, 1, 0, 1, 1, 1', '{0, 0, 1, 0, 0, 1, 0, 0, 1, 1', 'walk_select'),
]


def run_mutations(guest, families, stubs, seed, count):
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        shutil.copytree(ROOT / 'reconstructed' / 'record-math', scratch / 'record-math',
                        ignore=shutil.ignore_patterns('*.dylib', '*.so'))
        for index, (label, old, new, family) in enumerate(MUTATIONS):
            target = scratch / f'movement{index}'
            shutil.copytree(ROOT / 'reconstructed' / 'movement', target, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
            (target / 'Makefile').write_text((target / 'Makefile').read_text().replace('../record-math', '../record-math'))
            source = (target / 'client_movement.c').read_text()
            if source.count(old) != 1:
                raise ValueError(f'mutation anchor not unique: {label}')
            (target / 'client_movement.c').write_text(source.replace(old, new))
            lib = load_library(target)
            tally = Tally()
            function, family_count = families[family]
            function(guest, lib, tally, random.Random(f'{seed}:{family}'), max(count, family_count // 2), stubs)
            bad = sum(r['mismatches'] for r in tally.results.values())
            results.append({'mutation': label, 'family': family, 'mismatches': bad,
                            'cases': sum(r['cases'] for r in tally.results.values())})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT',
                                                         str(ROOT / 'evidence/x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get(
        'MU_IMAGE_DATA', str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--cases', type=int, default=400, help='random cases per family')
    parser.add_argument('--seed', type=int, default=0x574c44)
    parser.add_argument('--only', default=None, help='comma-separated family names')
    parser.add_argument('--output', default=None, help='write the JSON report here')
    parser.add_argument('--mutations', action='store_true', help='also check that planted mistakes are detected')
    args = parser.parse_args(argv)
    text = vc.load_pinned(args.text, vc.TEXT_BYTES, vc.TEXT_SHA256, 'restored text')
    data = vc.load_pinned(args.data, vc.DATA_BYTES, vc.DATA_SHA256, 'second image section')
    digests = {}
    for name, (start, length, digest) in ROUTINES.items():
        actual = hashlib.sha256(text[start - vc.TEXT_BASE:start - vc.TEXT_BASE + length]).hexdigest()
        digests[name] = actual
        if digest is not None and actual != digest:
            raise ValueError(f'pinned routine {name} changed')
    guest = MovementGuest(text, data, struct.pack('<I', 1))
    stubs = install_stubs(guest)
    lib = load_library()
    tally = Tally()
    n = args.cases

    def plain(function):
        return lambda g, l, t, r, c, s=None: function(g, l, t, r, c)

    families = [
        ('angles', plain(case_angles), n), ('move_path', plain(case_move_path), 2 * n), ('height', case_height, 2 * n),
        ('speed', case_speed, 2 * n), ('position', case_position, n), ('set_action', case_set_action, n),
        ('walk_select', case_walk_select, 256 * 3 * 7), ('stop_select', case_stop_select, 512),
        ('loader_speeds', case_loader_speeds, 4)]
    only = set(args.only.split(',')) if args.only else None
    extra = {}
    for name, function, count in families:
        if only and name not in only:
            continue
        stubs.values.clear()      # no stub value carries over between families
        stubs.buffs = 0
        result = function(guest, lib, tally, random.Random(f'{args.seed}:{name}'), count, stubs)
        if result is not None:
            extra[name] = result
    mutation_results = None
    if args.mutations:
        table = {name: (function, count) for name, function, count in families}
        mutation_results = run_mutations(guest, table, stubs, args.seed, max(600, n // 4))
        for entry in mutation_results:
            print(f"mutation {entry['mutation']:32s} {entry['mismatches']:5d}/{entry['cases']} detected")
    report = {'routines': {k: {'start': hex(v[0]), 'bytes': v[1], 'sha256': digests[k]} for k, v in ROUTINES.items()},
              'client_stubs': {hex(k): v for k, v in sorted(stubs.reasons.items())}, 'results': tally.results,
              'extra': extra, 'mutations': mutation_results, 'seed': args.seed, 'cases': n}
    total = sum(r['cases'] for r in tally.results.values())
    bad = sum(r['mismatches'] for r in tally.results.values())
    for name, r in tally.results.items():
        print(f"{name:40s} {r['cases']:7d} cases  {r['mismatches']:5d} mismatches")
        if r['first'] is not None:
            print('    first:', json.dumps(r['first'], default=str)[:700])
    print(f'total {total} comparisons, {bad} mismatches')
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    undetected = [m for m in (mutation_results or []) if m['mismatches'] == 0]
    if undetected:
        print('undetected mutations:', [m['mutation'] for m in undetected])
    return 1 if bad or undetected else 0


if __name__ == '__main__':
    sys.exit(main())
