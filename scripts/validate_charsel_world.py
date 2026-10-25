#!/usr/bin/env python3
"""Compare the character-select world's object handler (reconstructed/objects/charsel_world.c) with the client.

NATIVE-CHARSEL-002. World 0x5d (Data/World94) is the 3D scene behind the character list; its world
handler CGMCharacterScene_Ex (vtable 0x01aa7338) overrides the same five handler slots as the login
world's CGMLogInScene_Ex. The client routines run in Unicorn over the pinned restored text and second
image section through the strict machine of scripts/actor_machine.py (via validate_object_render.Machine):
every byte the guest reads must have been seeded or written, the image is read-only, and only the listed
callees are recording stubs.

Families:
  create      CreateObject 0x016d8538 for world 0x5d (the default chain's world-group hooks and the
              world-manager dispatch stubbed, as for worlds 0x8d and 0x5e), then slot 0x2c 0x00daa2b2 on
              the result with the handler object as `this` (its marker vectors compared;
              SetCharacterPosition 0x00da9ff3 recorded)
  move        MoveObject 0x017ff238 complete for world 0x5d, then slot 0x30 0x00daa82b (rand() and
              AddTerrainLight 0x016cacfc recorded; the vector accessor runs as client code)
  visual      slot 0x34 0x00daa9dd (rand: MSVC recurrence; TransformPosition 0x012b6ef1, CreateSprite
              0x01692eb7, CreateParticle 0x0168fafd and the CreateEffect wrapper 0x013c0eaa recorded; the
              C runtime sin wrapper 0x009681bd and the sprite temporary 0x00a0c1d0 as client code)
  custom      slot 0x38 0x00dab4d7 (RenderMesh 0x00966e4a recorded; return value and +0xa)
  after       slot 0x3c 0x00dab5ed (RenderBody 0x00966def and RenderMesh recorded)
  after_pass  RenderObjects_AfterCharacter 0x016d6949 for world 0x5d through mu_login_after_pass (the
              first-draw predicate's default reaches the handler's slot 0x14 through the image's
              CGMCharacterScene_Ex vtable)

Usage:
  scripts/validate_charsel_world.py [--cases N] [--only create,move] [--mutations] [--output report.json]
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
import pins  # noqa: E402
import actor_machine as am  # noqa: E402
import validate_object_render as vor  # noqa: E402
import validate_login_world as vlw  # noqa: E402
from validate_object_render import (  # noqa: E402
    OBJ_SIZE, OBJECTS, MODEL, ACTIONS, RECORD, FAKE, SECTORS, X2D, Y2D, TOP_VIEW, COUNTER, TIME, VSTUB_A, VSTUB_B,
    f32, pack_f, put_f, put_i, poison_object, global_regions, run, stopped_reason, new_log, log_events, Tally,
    MsvcRand, fake_object, object_list, sector_bytes, c_world, frustum_polygon, read_vec, RenderInputs, ANSWER_FN,
    RAND_FN, SPEED_FN, MoveInputs)

SUFFIX = vor.SUFFIX
WORLD = 0x5d
SCENE_OBJECT = 0x41020000          # the CGMCharacterScene_Ex instance (0x8c bytes) in the harness
CHARSEL_VTABLE = 0x01aa7338        # CGMCharacterScene_Ex (RTTI .?AVCGMCharacterScene_Ex@@)
BONES_BASE = 0x06fce398

BODIES = {
    'charsel_world_check': (0x00daa1f5, 0x00daa20d),
    'charsel_create_slot': (0x00daa2b2, 0x00daa82b),
    'charsel_move_slot': (0x00daa82b, 0x00daa9dd),
    'charsel_visual_slot': (0x00daa9dd, 0x00dab4d7),
    'charsel_custom_slot': (0x00dab4d7, 0x00dab5ed),
    'charsel_after_slot': (0x00dab5ed, 0x00dab744),
    'render_objects_after_character': (0x016d6949, 0x016d6e87),
}
PINNED = {
 'charsel_world_check': '1e75039d3b620969',
 'charsel_create_slot': '3db6d3622dd24038',
 'charsel_move_slot': '8b14bd1a079ce9f5',
 'charsel_visual_slot': '0de6d21e874971eb',
 'charsel_custom_slot': '417eb9147293ffee',
 'charsel_after_slot': '177cc0aad89fe1b0',
 'render_objects_after_character': '66bf84c6bc92ef40'
}   # first 16 hex digits of each body's SHA-256
CHARSEL_TYPES = [0xd, 0xe, 0xf, 0x10, 0x11, 4, 7, 8, 0xc, 0x18, 0x19, 0x1a, 0x1f, 0x21, 0x24, 0x26, 0x27, 0x28,
                 0x36, 0x37, 0x38, 0x39, 0x3c, 0x3d, 0x45, 0x47, 0x49, 0x50]


# ---------------------------------------------------------------- ctypes

class Scene(ctypes.Structure):
    _fields_ = [('position', (ctypes.c_float * 3) * 5), ('angle', (ctypes.c_float * 3) * 5)]


class Library(vlw.Library):
    def __init__(self, path):
        super().__init__(path)
        d = self.dll
        P = ctypes.c_void_p
        d.mu_csw_create.argtypes = [P, ctypes.c_int32, ctypes.POINTER(Scene), ctypes.POINTER(vor.Log)]
        d.mu_csw_create.restype = None
        d.mu_csw_move.argtypes = [P, ctypes.c_int32, RAND_FN, P, ctypes.POINTER(vor.Log)]
        d.mu_csw_move.restype = ctypes.c_int
        d.mu_csw_visual.argtypes = [P, ctypes.c_int32, ctypes.c_float, RAND_FN, vlw.BONE_FN, P, P,
                                    ctypes.POINTER(vor.Log)]
        d.mu_csw_visual.restype = ctypes.c_int
        d.mu_csw_custom_render.argtypes = [P, ctypes.c_int32, ctypes.POINTER(vor.Log)]
        d.mu_csw_custom_render.restype = ctypes.c_int
        d.mu_csw_after_render.argtypes = [P, ctypes.c_int32, ctypes.POINTER(vor.Log)]
        d.mu_csw_after_render.restype = ctypes.c_int


def charsel_object(g, typ=None):
    o = bytearray(poison_object(g))
    put_i(o, 0x5c, typ if typ is not None else g.choice(CHARSEL_TYPES + [g.randrange(0, 300)]))
    o[0] = g.choice([1, 1, 1, 0])
    o[0xa] = g.choice([0, 1, 2])
    put_f(o, 0xdc, f32(g.choice([1.0, 1.0, 0.5, g.uniform(0, 1)])))
    put_i(o, 0x68, g.choice([-1, -1, -2, 3]))
    put_i(o, 0x74, g.choice([-1, -1, 1, 4]))
    put_f(o, 0xa8, f32(g.choice([1.0, g.uniform(0, 1.5)])))
    put_f(o, 0xac, f32(g.uniform(-2, 2)), f32(g.uniform(-2, 2)))
    put_f(o, 0xa0, f32(g.choice([1.0, g.uniform(0.2, 15)])))
    put_f(o, 0x158, f32(g.uniform(0, 25600)), f32(g.uniform(0, 25600)), f32(g.uniform(-1000, 1000)))
    put_f(o, 0x164, *(f32(g.uniform(-360, 360)) for _ in range(3)))
    return o


class Rand(MsvcRand):
    """MSVC rand() whose first answers can be forced (the 1/100 and 1/200 branches need a multiple)."""

    def __init__(self, seed, first=()):
        super().__init__(seed)
        self.first = list(first)

    def __call__(self, *ignored):
        if self.first:
            return self.first.pop(0)
        return super().__call__()


def world_time_value(g):
    return f32(g.choice([0.0, 1.0, 3599.9, 3600.0, 100000.0, g.uniform(0, 3e7), g.uniform(0, 1e5),
                         -g.uniform(0, 5000)]))


def scene_bytes(g):
    raw = bytearray(g.getrandbits(8) for _ in range(0x8c))
    struct.pack_into('<I', raw, 0, CHARSEL_VTABLE)
    return raw


# ---------------------------------------------------------------- 1. create

def family_create(machine, lib, g, cases):
    t = Tally('create')
    for n in range(cases):
        rec = vor.random_record(g, 0x8d)
        rec.type = g.choice(CHARSEL_TYPES + [0xd, 0xe, 0xf, 0x10, 0x11, 0x3c, g.randrange(0, 300)])
        poison = poison_object(g)
        calls = []

        def record_call(name, cleanup=0, value=0):
            def stub(m):
                calls.append((name,) + tuple(m.argument(i) for i in range(2)))
                return (value, cleanup)
            return stub
        stubs = {0x0191ba7b: lambda m: OBJECTS, 0x0129e792: lambda m: m.uc.reg_read(m.x86.UC_X86_REG_ECX),
                 0x0129eb81: record_call('init'), 0x01295f18: record_call('buff-list'),
                 0x016d9f51: record_call('register')}
        for address in vlw.CHAIN_CREATE:
            stubs[address] = record_call(hex(address))
        stubs.update({0x0095c652: lambda m: FAKE, 0x00d53c8f: lambda m: FAKE,
                      0x00d53d53: record_call('d53d53', 4), 0x00d53d7d: record_call('d53d7d', 4),
                      0x00db747f: lambda m: FAKE, VSTUB_A: record_call('vslot-2c', 4),
                      0x00ea594b: lambda m: FAKE + 0x100, 0x00ea2ad6: record_call('world-manager-create', 4)})
        x, y = rec.position[0], rec.position[1]

        def sector(v):
            q = v / 1600 if math.isfinite(v) else math.nan
            return int(q) if math.isfinite(q) and -2**31 < q < 2**31 else -2**31
        inside = all(0 <= sector(v) < 16 for v in (x, y))
        regions = global_regions(WORLD, 5, [
            am.defined_region('record', RECORD, bytes(rec)),
            am.defined_region('object', OBJECTS, poison),
            am.defined_region('sectors', SECTORS, bytes(256 * 16)),
            am.defined_region('fake', FAKE, fake_object(), writable=False)])
        result = run(machine, vor.CREATE, [RECORD], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': rec.type}, stop)
            continue
        guest = bytearray(result['regions']['object'])
        scene_before = scene_bytes(g)
        scene_after = bytes(scene_before)
        positions = []
        if inside:
            def set_position(m):
                positions.append((0x00da9ff3, 0, m.argument(0)))
                return (0, 4)
            r2 = run(machine, 0x00daa2b2, [OBJECTS], global_regions(WORLD, 5, [
                am.defined_region('object', OBJECTS, bytes(guest)),
                am.defined_region('scene-object', SCENE_OBJECT, bytes(scene_before))]),
                {0x00da9ff3: set_position}, ecx=SCENE_OBJECT, cleanup=4)
            stop = stopped_reason(r2)
            if stop:
                t.add(False, {'case': n, 'type': rec.type, 'step': 'slot 0x2c'}, stop)
                continue
            guest = bytearray(r2['regions']['object'])
            scene_after = r2['regions']['scene-object']
            if (r2['eax'] & 0xff) != 1:
                t.add(False, {'case': n, 'type': rec.type, 'slot returned': r2['eax']})
                continue
        cobj = ctypes.create_string_buffer(poison, OBJ_SIZE)
        csector = ctypes.c_int32(-1)
        log = new_log(16)
        status = lib.dll.mu_obj_create(ctypes.byref(rec), WORLD, cobj, ctypes.byref(csector), 0, ctypes.byref(log))
        c = bytearray(cobj.raw[:OBJ_SIZE])
        c_positions = [e for e in log_events(log) if e[0] == 0x00da9ff3]
        # the marker vectors through mu_csw_create on the guest's pre-slot object
        cscene = Scene()
        ctypes.memmove(ctypes.byref(cscene), bytes(scene_before[0x14:0x14 + 0x78]), 0x78)
        if inside:
            pre = bytearray(result['regions']['object'])
            log2 = new_log(16)
            lib.dll.mu_csw_create(ctypes.create_string_buffer(bytes(pre), OBJ_SIZE), 0, ctypes.byref(cscene),
                                  ctypes.byref(log2))
        scene_ok = bytes(scene_after[0x14:0x8c]) == bytes(cscene) and scene_after[:0x14] == bytes(scene_before[:0x14])
        if not inside:
            ok = status == 1 and c == bytearray(poison) and guest == bytearray(poison)
            t.count('outside the map')
        else:
            guest[0x350:0x358] = c[0x350:0x358]
            diff = [hex(i) for i in range(OBJ_SIZE) if guest[i] != c[i]]
            ok = status == 0 and not diff and positions == c_positions and scene_ok
            t.count('marker' if 0xd <= rec.type <= 0x11 else f'type {rec.type:#x}' if rec.type in (0x3c, 0x3d)
                    else 'hidden' if rec.type in (0x26, 0x27, 0x28, 0x36, 0x37, 0x38, 0x39, 0x45, 0x50) else 'other')
            if not ok:
                t.add(False, {'case': n, 'type': rec.type, 'diff': diff[:10], 'positions': positions,
                              'c': c_positions, 'scene': scene_ok})
                continue
        t.add(ok, {'case': n, 'type': rec.type})
    return t


# ---------------------------------------------------------------- 2. move

def family_move(machine, lib, g, cases):
    t = Tally('move')
    for n in range(cases):
        o = vor.move_object(g, WORLD, 'generic')
        typ = g.choice([0x18, 0x19, 0x1a, 0x49, 0x49, 0x18, g.randrange(0, 0x60)])
        put_i(o, 0x5c, typ)
        put_f(o, 0xb0, f32(g.uniform(-3, 3)))
        scene = g.choice([5, 5, 3, 6])
        time = f32(g.uniform(0, 3e7))
        seed = g.getrandbits(32)
        rnd = MsvcRand(seed)
        calls = []

        def tick(m):
            calls.append((0x012b4dd3, 0, m.argument(3)))
            return (1, 0x18)

        def light(m):
            a = [m.argument(i) for i in range(5)]
            entry = (0x016cacfc, 0, a[0], a[1]) + read_vec(m, a[2]) + (a[3],)
            calls.append(entry if a[4] == vor.FRAME_LIGHT else ('light grid', a[4]))
            return 0
        stubs = {0x012b4dd3: tick, 0x01989721: lambda m: rnd(), 0x00966cc4: lambda m: FAKE,
                 0x00eaa8cf: lambda m: (MODEL, 4), 0x016cacfc: light}
        for address in vlw.CHAIN_MOVE:
            stubs[address] = (lambda a: lambda m: 0)(address)
        stubs.update({0x00d53c8f: lambda m: FAKE, 0x00d53da7: lambda m: (0, 4), 0x00db747f: lambda m: FAKE,
                      VSTUB_B: lambda m: (0, 4), 0x00ea594b: lambda m: FAKE + 0x100,
                      0x00ea2c2b: lambda m: calls.append(('manager-move',)) or (0, 4)})
        model = bytearray(0x100)
        struct.pack_into('<I', model, 0x30, ACTIONS)
        regions = global_regions(WORLD, scene, [
            am.defined_region('object', OBJECTS, bytes(o)),
            am.defined_region('model', MODEL, bytes(model)),
            am.defined_region('time', TIME, pack_f(time), writable=False),
            am.defined_region('hero-tile', vor.HERO_TILE, struct.pack('<i', 0), writable=False),
            am.defined_region('fake', FAKE, fake_object(), writable=False)])
        result = run(machine, vor.MOVE, [OBJECTS], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        guest = result['regions']['object']
        if ('manager-move',) in calls:
            calls.remove(('manager-move',))
            r2 = run(machine, 0x00daa82b, [OBJECTS], global_regions(WORLD, scene, [
                am.defined_region('object', OBJECTS, guest)]), stubs, ecx=SCENE_OBJECT, cleanup=4)
            stop = stopped_reason(r2)
            if stop:
                t.add(False, {'case': n, 'type': typ, 'step': 'slot 0x30'}, stop)
                continue
            guest = r2['regions']['object']
            t.count('slot ran')
        crand = MsvcRand(seed)
        inputs = MoveInputs(WORLD, scene, 0, time, (ctypes.c_float * 3)(0, 0, 0), 1, 1,
                            SPEED_FN(lambda ctx, ty, ac: math.nan), RAND_FN(lambda ctx: crand()), None, 0)
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        log = new_log()
        status = lib.dll.mu_obj_move(cobj, 0, ctypes.byref(inputs), ctypes.byref(log))
        c_calls = []
        for e in log_events(log):
            if e[0] == 0x012b4dd3:
                c_calls.append(e[:3])
            elif e[0] == 0x016cacfc:
                c_calls.append(e[:8])
            else:
                c_calls.append(e)
        diff = [hex(i) for i in range(OBJ_SIZE) if guest[i] != cobj.raw[i]]
        t.count(f'type {typ:#x}' if typ in (0x18, 0x19, 0x1a, 0x49) else 'other type')
        t.count('terrain lights', sum(1 for c in calls if c[0] == 0x016cacfc))
        t.add(not diff and calls == c_calls and status in (0, 1),
              {'case': n, 'type': typ, 'diff': diff[:8], 'calls': calls, 'c': c_calls, 'status': status})
    return t


# ---------------------------------------------------------------- 3. visual

def family_visual(machine, lib, g, cases):
    t = Tally('visual')
    visual_types = [0x1f, 0x26, 0x27, 0x28, 0x36, 0x37, 0x38, 0x39, 0x45, 0x49, 0x50]
    for n in range(cases):
        o = charsel_object(g, g.choice(visual_types + [0x49, 0x49, 0x1f, g.randrange(0, 0x60)]))
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        world_time = world_time_value(g)
        seed = g.getrandbits(32)
        first = [g.choice([0, 600, 1200, 30000, 7, 100, 300, 1500])] if g.random() < 0.5 else []
        rnd = Rand(seed, first)
        calls = []

        def transform(m):
            a = [m.argument(i) for i in range(4)]
            bone = (a[0] - BONES_BASE) // 0x30 if (a[0] - BONES_BASE) % 0x30 == 0 else ('matrix', a[0])
            local = struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12)))
            ok = m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
            calls.append((0x012b6ef1, 0, bone) + read_vec(m, a[1]) + (a[3],) if ok else ('transform this', a))
            m.uc.mem_write(a[2], struct.pack('<3f', *vlw.bone_out(bone if isinstance(bone, int) else 0, local)))
            return (0, 0x10)

        def sprite(m):
            a = [m.argument(i) for i in range(9)]
            temp = struct.unpack('<IIf', bytes(m.uc.mem_read(a[8], 12)))
            entry = (0x01692eb7, 0, a[0]) + read_vec(m, a[1]) + (a[2],) + read_vec(m, a[3]) + \
                (a[5], 1 if a[4] == OBJECTS else ('owner', a[4]), a[6], a[7])
            calls.append(entry if temp == (1, 1, 1.0) else ('sprite temporary', temp))
            return 0

        def particle(m):
            a = [m.argument(i) for i in range(8)]
            owner = 1 if a[6] == OBJECTS else 0 if a[6] == 0 else ('owner', a[6])
            entry = (0x0168fafd, 0, a[0]) + read_vec(m, a[1]) + read_vec(m, a[2]) + read_vec(m, a[3]) + \
                (a[4], a[5], owner)
            calls.append(entry if a[7] == 0 else ('particle tail', a))
            return 0

        def effect(m):
            a = [m.argument(i) for i in range(14)]
            owner = 1 if a[5] == OBJECTS else ('owner', a[5])
            entry = (0x013c0eaa, 0, a[0]) + read_vec(m, a[1]) + read_vec(m, a[2]) + read_vec(m, a[3]) + \
                (a[4], owner)
            tail = (a[6], a[7], a[8], a[9], a[10], a[11], a[12], a[13])
            calls.append(entry if tail == (0xffffffff, 0, 0, 0, 0, 0xffffffff, 0, 0) else ('effect tail', tail))
            return 0
        stubs = {0x01989721: lambda m: rnd(), 0x012b6ef1: transform, 0x01692eb7: sprite, 0x0168fafd: particle,
                 0x013c0eaa: effect}
        regions = global_regions(WORLD, 5, [am.defined_region('object', OBJECTS, bytes(o), writable=False),
                                           am.defined_region('model', MODEL, bytes(0x100), writable=False),
                                           am.defined_region('time', TIME, pack_f(world_time), writable=False)])
        result = run(machine, 0x00daa9dd, [OBJECTS, MODEL], regions, stubs, ecx=SCENE_OBJECT, cleanup=8)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        crand = Rand(seed, first)

        def cbone(ctx, bone, local, out):
            v = vlw.bone_out(bone, (local[0], local[1], local[2]))
            for k in range(3):
                out[k] = v[k]
        keep = (RAND_FN(lambda ctx: crand()), vlw.BONE_FN(cbone))
        log = new_log()
        handled = lib.dll.mu_csw_visual(ctypes.create_string_buffer(bytes(o), OBJ_SIZE), 0, world_time, keep[0],
                                        keep[1], None, None, ctypes.byref(log))
        c_calls = log_events(log)
        t.count('sprites', sum(1 for c in calls if c[0] == 0x01692eb7))
        t.count('particles', sum(1 for c in calls if c[0] == 0x0168fafd))
        t.count('effects', sum(1 for c in calls if c[0] == 0x013c0eaa))
        t.add(calls == c_calls and (result['eax'] & 0xff) == handled,
              {'case': n, 'type': typ, 'time': world_time, 'calls': calls[:3], 'c': c_calls[:3],
               'eax': result['eax'], 'handled': handled})
    return t


# ---------------------------------------------------------------- 4. custom render

def family_custom(machine, lib, g, cases):
    t = Tally('custom')
    for n in range(cases):
        o = charsel_object(g, g.choice(CHARSEL_TYPES + [0x3c, 0x3c, g.randrange(0, 0x60)]))
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        calls = []

        def mesh(m):
            ok = m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
            calls.append((0x00966e4a, 0) + tuple(m.argument(i) for i in range(8)) if ok else ('mesh this',))
            return (0, 0x20)

        def body(m):
            calls.append(('body',))
            return (0, 0x20)
        regions = global_regions(WORLD, 5, [am.defined_region('object', OBJECTS, bytes(o)),
                                           am.defined_region('model', MODEL, bytes(0x100), writable=False)])
        result = run(machine, 0x00dab4d7, [OBJECTS, MODEL, 0], regions, {0x00966e4a: mesh, 0x00966def: body},
                     ecx=SCENE_OBJECT, cleanup=12)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        log = new_log()
        handled = lib.dll.mu_csw_custom_render(cobj, 0, ctypes.byref(log))
        same = result['regions']['object'] == cobj.raw[:OBJ_SIZE]
        t.count('handled' if handled else 'not handled')
        t.add(same and calls == log_events(log) and (result['eax'] & 0xff) == handled,
              {'case': n, 'type': typ, 'calls': calls, 'c': log_events(log)})
    return t


# ---------------------------------------------------------------- 5. after-character render

def family_after(machine, lib, g, cases):
    t = Tally('after')
    for n in range(cases):
        o = charsel_object(g, g.choice(CHARSEL_TYPES + [0x3c, 0x3c, g.randrange(0, 0x60)]))
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        calls = []

        def draw(address):
            def stub(m):
                ok = m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
                calls.append((address, 0) + tuple(m.argument(i) for i in range(8)) if ok else ('draw this',))
                return (0, 0x20)
            return stub
        regions = global_regions(WORLD, 5, [am.defined_region('object', OBJECTS, bytes(o), writable=False),
                                           am.defined_region('model', MODEL, bytes(0x100), writable=False)])
        result = run(machine, 0x00dab5ed, [OBJECTS, MODEL, 0], regions,
                     {0x00966e4a: draw(0x00966e4a), 0x00966def: draw(0x00966def)}, ecx=SCENE_OBJECT, cleanup=12)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        log = new_log()
        lib.dll.mu_csw_after_render(ctypes.create_string_buffer(bytes(o), OBJ_SIZE), 0, ctypes.byref(log))
        t.count('meshes', sum(1 for c in calls if c[0] == 0x00966e4a))
        t.count('bodies', sum(1 for c in calls if c[0] == 0x00966def))
        t.add(calls == log_events(log), {'case': n, 'type': typ, 'calls': calls, 'c': log_events(log)})
    return t


# ---------------------------------------------------------------- 6. after-character pass

def family_after_pass(machine, lib, g, cases):
    t = Tally('after_pass')
    for n in range(cases):
        scene = g.choice([5, 5, 3, 6])
        top = 1 if g.random() < 0.1 else 0
        count = g.randrange(0, 50)
        x2d, y2d = frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4

        def fields(g, o, k):
            o[0] = g.choice([0, 1, 1, 1, 1])
            o[0xa] = g.choice([0, 1, 1, 2])
            o[0xb] = g.choice([0, 1])
            put_i(o, 0x5c, g.choice(CHARSEL_TYPES + [g.randrange(0, 300)]))
            put_f(o, 0x158, f32((cx + g.uniform(-45, 45)) * 100), f32((cy + g.uniform(-45, 45)) * 100),
                  f32(g.uniform(0, 300)))
            put_f(o, 0xc0, f32(g.choice([-30.0, -428.571442, g.uniform(-600, 50)])))
        objects, heads, nxt = object_list(g, count, fields)
        counter = g.choice([0, 5, 40, 41, 100])
        calls = []
        index = lambda a: (a - OBJECTS) // 0x400

        def draw(m):
            calls.append((0x016d6791, index(m.argument(0))) + tuple(m.argument(i) for i in range(1, 4)))
            return 0
        # the first-draw predicate's default asks the world manager (0x00ea27b4, client code) for the
        # handler's slot 0x14: the manager +0x10 holds an object with the real CGMCharacterScene_Ex vtable
        stubs = {0x016d6791: draw, 0x00db747f: lambda m: FAKE, 0x0095fba9: lambda m: 0, 0x009a6ef3: lambda m: FAKE,
                 0x00ea594b: lambda m: FAKE + 0x100}
        fake = bytearray(fake_object())
        struct.pack_into('<I', fake, 0x110, FAKE + 0x380)
        struct.pack_into('<I', fake, 0x380, CHARSEL_VTABLE)
        for address in vlw.CHAIN_AFTER:
            stubs[address] = (lambda a: lambda m: 0)(address)
        regions = global_regions(WORLD, scene, [
            am.defined_region('sectors', SECTORS, bytes(sector_bytes(heads))),
            am.defined_region('x2d', X2D, pack_f(*x2d), writable=False),
            am.defined_region('y2d', Y2D, pack_f(*y2d), writable=False),
            am.defined_region('top-view', TOP_VIEW, bytes([top]), writable=False),
            am.defined_region('counter', COUNTER, struct.pack('<i', counter)),
            am.defined_region('fake', FAKE, bytes(fake), writable=False)] +
            [am.defined_region(f'object{k}', OBJECTS + 0x400 * k, bytes(o)) for k, o in enumerate(objects)])
        result = run(machine, 0x016d6949, [], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        w, bufs = c_world(objects, heads, nxt)
        xs, ys = (ctypes.c_float * 4)(*x2d), (ctypes.c_float * 4)(*y2d)
        inputs = RenderInputs(WORLD, scene, top, xs, ys, ANSWER_FN(lambda c, k: 0), ANSWER_FN(lambda c, k: 0), None,
                              0.0)
        ccounter = ctypes.c_int32(counter)
        log = new_log()
        status = lib.dll.mu_login_after_pass(ctypes.byref(w), ctypes.byref(inputs), ctypes.byref(ccounter),
                                             ctypes.byref(log))
        c_calls = log_events(log)
        table = result['regions']['sectors']
        blocks_ok = all(table[s * 16 + 0xc] == w.block_visible[s] for s in range(256))
        objs_ok = all(result['regions'][f'object{k}'] == bufs[k].raw[:OBJ_SIZE] for k in range(count))
        counter_ok = struct.unpack('<i', result['regions']['counter'])[0] == ccounter.value
        t.count('drawn', len(calls))
        t.add(status == 0 and calls == c_calls and blocks_ok and objs_ok and counter_ok,
              {'case': n, 'calls': calls[:4], 'c': c_calls[:4], 'blocks': blocks_ok, 'objects': objs_ok,
               'counter': counter_ok})
    return t


# ---------------------------------------------------------------- driver

FAMILIES = {'create': family_create, 'move': family_move, 'visual': family_visual, 'custom': family_custom,
            'after': family_after, 'after_pass': family_after_pass}

MUTATIONS = [
    ('marker 2 yaw 70', 'charsel_world.c', '{115.0f, 90.0f, 75.0f, 60.0f, 35.0f}', '{115.0f, 90.0f, 70.0f, 60.0f, 35.0f}',
     'create'),
    ('type 0x50 not hidden', 'charsel_world.c', 'case 0x39: case 0x45: case 0x50:', 'case 0x39: case 0x45:', 'create'),
    ('scroll 0x19 at 0.02', 'charsel_world.c', 'case 0x19: case 0x1a:\n        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.03f);',
     'case 0x19: case 0x1a:\n        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.02f);', 'move'),
    ('lamp light range 4', 'charsel_world.c', 'arg_v(e, light);\n        arg(e, 3);', 'arg_v(e, light);\n        arg(e, 4);',
     'move'),
    ('lamp sprite rotation not negated', 'charsel_world.c', 'light, -rotation);', 'light, rotation);', 'visual'),
    ('falls spray every 4th', 'charsel_world.c', 'case 0x38:   /* 0x00dab016 */\n        if (R(3) == 0) {',
     'case 0x38:   /* 0x00dab016 */\n        if (R(4) == 0) {', 'visual'),
    ('stardr subtype 1 at 1/100', 'charsel_world.c', 'if (R(200) == 0) {', 'if (R(100) == 0) {', 'visual'),
    ('pedestal mesh 0 in the custom render', 'charsel_world.c', 'mesh(log, index, o, 1, mu_obj_i32(o, MU_OBJF_BLEND_MESH));',
     'mesh(log, index, o, 0, mu_obj_i32(o, MU_OBJF_BLEND_MESH));', 'custom'),
    ('after body without its hidden mesh', 'charsel_world.c',
     'arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_HIDDEN_MESH));\n    arg(e, 0xffffffffu);\n    return 1;',
     'arg(e, 0xffffffffu);\n    arg(e, 0xffffffffu);\n    return 1;', 'after'),
    ('after pass without world 0x5d', 'login_world.c', 'in->world != 0x5d', 'in->world != 0x5e', 'after_pass'),
]


def build_library(directory):
    subprocess.run(['make', '-s', '-C', str(directory / 'objects')], check=True)
    return directory / 'objects' / f'libobjects.{SUFFIX}'


def mutations(machine, args):
    out = []
    for label, file, old, new, family in MUTATIONS:
        scratch = Path(tempfile.mkdtemp(prefix='charselworld-mut-'))
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
            tally = FAMILIES[family](machine, lib, random.Random(args.seed + 31), args.mutation_cases)
            out.append({'mutation': label, 'family': family, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped})
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=pins.TEXT.default_str())
    parser.add_argument('--data', default=pins.DATA.default_str())
    parser.add_argument('--library', default=str(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--seed', type=int, default=0x5d5d)
    parser.add_argument('--only', default=None)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--mutation-cases', type=int, default=300)
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    bodies = {name: {'start': hex(s), 'end_exclusive': hex(e),
                     'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
              for name, (s, e) in BODIES.items()}
    for name, prefix in PINNED.items():
        if prefix and not bodies[name]['sha256'].startswith(prefix):
            raise SystemExit(f'{name}: routine bytes differ from the pinned digest')
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    machine = vor.Machine(text, data)
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
        print(f"{name}: {r['equal']}/{r['cases']} equal, {r['stopped']} stopped, coverage {r['coverage']}", flush=True)
        if r['examples']:
            print('  example:', json.dumps(r['examples'][0], default=str)[:1500])
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
