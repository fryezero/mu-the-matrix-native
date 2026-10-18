#!/usr/bin/env python3
"""Compare the login world's object handler (reconstructed/objects/login_world.c) with the client.

NATIVE-LOGIN-001. World 0x5e (Data/World95) is the 3D scene behind the login and server-select
screens; its world handler CGMLogInScene_Ex (vtable 0x01aaa874) overrides five handler slots. The
client routines run in Unicorn over the pinned restored text and second image section through the
strict machine of scripts/actor_machine.py (via validate_object_render.Machine): every byte the
guest reads must have been seeded or written, the image is read-only, and only the listed callees
are recording stubs.

Families:
  create      CreateObject 0x016d8538 for world 0x5e (the default chain's world-group hooks and the
              world-manager dispatch stubbed, as for world 0x8d), then slot 0x2c 0x00e24a4d on the
              result (0x00e24993 as client code; the model action table write compared)
  move        MoveObject 0x017ff238 complete for world 0x5e (the tick with the action PlaySpeed of
              type 5), then slot 0x30 0x00e24acd: the pulse 0x00cfec8d, the C runtime sin
              0x009681bd/0x01985700 and fabs 0x0098a647 run as client code; timeGetTime is a hook
              on its call instruction
  visual      slot 0x34 0x00e24be1 (rand: MSVC recurrence; TransformPosition 0x012b6ef1,
              CreateSprite 0x01692eb7 and CreateParticle 0x0168fafd recorded; the sprite's
              temporary 0x00a0c1d0 as client code, its {1, 1, 1.0} contents checked)
  custom      slot 0x38 0x00e254bb (RenderBody 0x00966def recorded; return value and +0xa)
  after       slot 0x3c 0x00e25639 (RenderMesh 0x00966e4a recorded; model colour writes, alpha)
  after_pass  RenderObjects_AfterCharacter 0x016d6949 for world 0x5e (TestFrustrum2D and the
              predicates 0x017fe909, 0x0095f977, 0x00d8b139, 0x009a645f as client code; the
              world-group predicates before the world test stubbed to 0; the draw 0x016d6791
              recorded)

Usage:
  scripts/validate_login_world.py [--cases N] [--only create,move] [--mutations] [--output report.json]
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
import validate_object_render as vor  # noqa: E402
from validate_object_render import (  # noqa: E402
    OBJ_SIZE, OBJECTS, MODEL, ACTIONS, RECORD, FAKE, SECTORS, X2D, Y2D, TOP_VIEW, COUNTER, TIME, VSTUB_A, VSTUB_B,
    f32, pack_f, put_f, put_i, poison_object, global_regions, run, stopped_reason, new_log, log_events, Tally,
    MsvcRand, Record, fake_object, object_list, sector_bytes, c_world, frustum_polygon, read_vec, World,
    RenderInputs, ANSWER_FN, RAND_FN, SPEED_FN, MoveInputs)

SUFFIX = vor.SUFFIX
WORLD = 0x5e
TIME_GET_TIME_CALL = (0x00cfec9b, 0x00cfeca1)   # call dword ptr [0x01a7c9a4] inside the pulse
BONES_BASE = 0x06fce398
LOGIN_VTABLE = 0x01aaa874   # CGMLogInScene_Ex (RTTI .?AVCGMLogInScene_Ex@@, complete object locator 0x01be35bc)

BODIES = {
    'login_world_check': (0x00e24993, 0x00e249ab),
    'login_create_slot': (0x00e24a4d, 0x00e24acd),
    'login_move_slot': (0x00e24acd, 0x00e24be1),
    'login_visual_slot': (0x00e24be1, 0x00e254bb),
    'login_custom_slot': (0x00e254bb, 0x00e25639),
    'login_after_slot': (0x00e25639, 0x00e25d7a),
    'pulse': (0x00cfec8d, 0x00cfed1e),
    'render_objects_after_character': (0x016d6949, 0x016d6e87),
}
PINNED = {
 'login_world_check': '65e05415dcaad305',
 'login_create_slot': '6b49b2dfc4227ebf',
 'login_move_slot': 'e922bfdf6f503ce4',
 'login_visual_slot': 'd2e85cd094f4c6af',
 'login_custom_slot': 'a670dcfadaa0b280',
 'login_after_slot': '4df0c02c1d9b3bce',
 'pulse': 'd3cd86b0a043069a',
 'render_objects_after_character': '66bf84c6bc92ef40'
}   # first 16 hex digits of each body's SHA-256
LOGIN_TYPES = [1, 2, 3, 5, 7, 8, 0xa, 0xb, 0xc, 0xd, 0x12, 0x13, 0x14, 0x1d, 0x26, 0x36, 0x37, 0x38]


# ---------------------------------------------------------------- ctypes

class Library(vor.Library):
    def __init__(self, path):
        super().__init__(path)
        d = self.dll
        P = ctypes.c_void_p
        d.mu_login_pulse.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint32, P, P]
        d.mu_login_pulse.restype = ctypes.c_float
        d.mu_login_create.argtypes = [P, ctypes.c_int32, ctypes.POINTER(vor.Log)]
        d.mu_login_move.argtypes = [P, ctypes.c_uint32, P, P]
        d.mu_login_move.restype = ctypes.c_int
        d.mu_login_visual.argtypes = [P, ctypes.c_int32, RAND_FN, BONE_FN, P, ctypes.POINTER(vor.Log)]
        d.mu_login_visual.restype = ctypes.c_int
        d.mu_login_custom_render.argtypes = [P, ctypes.c_int32, ctypes.POINTER(vor.Log)]
        d.mu_login_custom_render.restype = ctypes.c_int
        d.mu_login_after_render.argtypes = [P, P, ctypes.c_int32, ctypes.c_uint32, P, P, ctypes.POINTER(vor.Log)]
        d.mu_login_after_render.restype = ctypes.c_int
        d.mu_login_after_pass.argtypes = [ctypes.POINTER(World), ctypes.POINTER(RenderInputs),
                                          ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(vor.Log)]
        d.mu_login_after_pass.restype = ctypes.c_int


BONE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                           ctypes.POINTER(ctypes.c_float))


def bone_out(bone, local):
    """The harness's stand-in TransformPosition: a deterministic binary32 function of bone and local."""
    return (f32(local[0] + bone * 3.25), f32(local[1] - bone * 1.5), f32(local[2] * 2.0 + 100.0 + bone))


def login_object(g, typ=None):
    o = bytearray(poison_object(g))
    put_i(o, 0x5c, typ if typ is not None else g.choice(LOGIN_TYPES + [g.randrange(0, 300)]))
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


def now_value(g):
    return g.choice([g.getrandbits(32), g.randrange(0, 1 << 24), 0, 0x80000000 + g.randrange(1 << 20),
                     0xffffffff, 87507920])


def time_hook(machine, now):
    """timeGetTime: EAX = now at the import call of the pulse, then continue after it."""
    uc = machine.uc

    def hook(u, address, size, ignored):
        u.reg_write(machine.x86.UC_X86_REG_EAX, now)
        u.reg_write(machine.x86.UC_X86_REG_EIP, TIME_GET_TIME_CALL[1])
    h = uc.hook_add(machine.UC_HOOK_CODE, hook, begin=TIME_GET_TIME_CALL[0], end=TIME_GET_TIME_CALL[0])
    uc.ctl_flush_tb()
    return h


def host_sin_fn():
    return ctypes.cast(None, ctypes.c_void_p)


# ---------------------------------------------------------------- 1. create

CHAIN_CREATE = (0x009dafa8, 0x00def3ac, 0x00d8e18f, 0x00dfbc3f, 0x00d6200e, 0x00dabeb4, 0x00e74a58, 0x00e7dcf4,
                0x00e84530, 0x00e30a02, 0x00e5f617)


def family_create(machine, lib, g, cases):
    t = Tally('create')
    for n in range(cases):
        rec = vor.random_record(g, 0x8d)
        rec.type = g.choice(LOGIN_TYPES + [5, 5, 0x26, 0x36, g.randrange(0, 300)])
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
        for address in CHAIN_CREATE:
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
        regions = global_regions(WORLD, 3, [
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
        speed_writes = []
        if inside:
            action_table = bytearray(struct.pack('<4f', 9.0, 9.0, 9.0, 9.0))
            slot_calls = []

            def action_lookup(m):   # 0x00eaaa44(type, action): the model's action record
                slot_calls.append((m.argument(0), m.argument(1)))
                return (ACTIONS, 8)
            r2 = run(machine, 0x00e24a4d, [OBJECTS], global_regions(WORLD, 3, [
                am.defined_region('object', OBJECTS, bytes(guest)),
                am.defined_region('actions', ACTIONS, bytes(action_table))]),
                {0x00966cc4: lambda m: FAKE + 0x300, 0x00eaaa44: action_lookup}, ecx=FAKE + 0x100, cleanup=4)
            stop = stopped_reason(r2)
            if stop:
                t.add(False, {'case': n, 'type': rec.type, 'step': 'slot 0x2c'}, stop)
                continue
            guest = bytearray(r2['regions']['object'])
            table = r2['regions']['actions']
            if table != bytes(action_table):
                speed_writes.append((0x00eaaa44, 0) + (slot_calls[0] if slot_calls else (None, None)) +
                                    (struct.unpack_from('<I', table, 4)[0],))
            if (r2['eax'] & 0xff) != 1:
                t.add(False, {'case': n, 'type': rec.type, 'slot returned': r2['eax']})
                continue
        cobj = ctypes.create_string_buffer(poison, OBJ_SIZE)
        csector = ctypes.c_int32(-1)
        log = new_log(16)
        status = lib.dll.mu_obj_create(ctypes.byref(rec), WORLD, cobj, ctypes.byref(csector), 0, ctypes.byref(log))
        c = bytearray(cobj.raw[:OBJ_SIZE])
        c_speed = [e for e in log_events(log) if e[0] == 0x00eaaa44]
        if not inside:
            ok = status == 1 and c == bytearray(poison) and guest == bytearray(poison)
            t.count('outside the map')
        else:
            guest[0x350:0x358] = c[0x350:0x358]
            diff = [hex(i) for i in range(OBJ_SIZE) if guest[i] != c[i]]
            ok = status == 0 and not diff and speed_writes == c_speed
            t.count(f'type {rec.type:#x}' if rec.type in (5, 0x26, 0x36) else 'other type')
            if not ok:
                t.add(False, {'case': n, 'type': rec.type, 'diff': diff[:10], 'speed': speed_writes, 'c': c_speed})
                continue
        t.add(ok, {'case': n, 'type': rec.type})
    return t


# ---------------------------------------------------------------- 2. move

CHAIN_MOVE = (0x00def6fb, 0x00d8e38c, 0x00dfbc92, 0x00d6202f, 0x00dabed5, 0x00e74ae0, 0x00e7dd29, 0x00e845d0,
              0x00e30b86, 0x00e5f629)


def family_move(machine, lib, g, cases):
    t = Tally('move')
    for n in range(cases):
        o = vor.move_object(g, WORLD, 'generic')
        typ = g.choice([1, 1, 0xd, 0xd, 5, 5, g.randrange(0, 60)])
        put_i(o, 0x5c, typ)
        put_f(o, 0xb0, f32(g.uniform(-3, 3)))
        scene = g.choice([3, 3, 5, 6])
        now = now_value(g)
        time = f32(g.uniform(0, 3e7))
        speeds = [f32(g.uniform(0.05, 1.0)) for _ in range(4)]
        seed = g.getrandbits(32)
        rnd = MsvcRand(seed)
        calls = []

        def tick(m):
            calls.append((0x012b4dd3, 0, m.argument(3)))
            return (1, 0x18)
        def action_lookup(m):   # 0x00eaaa44(type, action)
            index = m.argument(1)
            return (ACTIONS + 16 * index if 0 <= index < 4 else 0, 8)
        stubs = {0x012b4dd3: tick, 0x01989721: lambda m: rnd(), 0x00966cc4: lambda m: FAKE,
                 0x00eaa8cf: lambda m: (MODEL, 4), 0x00eaaa44: action_lookup}
        for address in CHAIN_MOVE:
            stubs[address] = (lambda a: lambda m: 0)(address)
        stubs.update({0x00d53c8f: lambda m: FAKE, 0x00d53da7: lambda m: (0, 4), 0x00db747f: lambda m: FAKE,
                      VSTUB_B: lambda m: (0, 4), 0x00ea594b: lambda m: FAKE + 0x100,
                      0x00ea2c2b: lambda m: calls.append(('manager-move',)) or (0, 4)})
        model = bytearray(0x100)
        struct.pack_into('<I', model, 0x30, ACTIONS)
        action_table = bytearray(16 * 4)
        for k in range(4):
            struct.pack_into('<f', action_table, 16 * k + 4, speeds[k])
        regions = global_regions(WORLD, scene, [
            am.defined_region('object', OBJECTS, bytes(o)),
            am.defined_region('model', MODEL, bytes(model)),
            am.defined_region('actions', ACTIONS, bytes(action_table), writable=False),
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
            hook = time_hook(machine, now)
            try:
                r2 = run(machine, 0x00e24acd, [OBJECTS], global_regions(WORLD, scene, [
                    am.defined_region('object', OBJECTS, guest)]), {}, ecx=FAKE + 0x100, cleanup=4)
            finally:
                machine.uc.hook_del(hook)
            stop = stopped_reason(r2)
            if stop:
                t.add(False, {'case': n, 'type': typ, 'step': 'slot 0x30'}, stop)
                continue
            guest = r2['regions']['object']
            t.count('slot ran')
        crand = MsvcRand(seed)
        inputs = MoveInputs(WORLD, scene, 0, time, (ctypes.c_float * 3)(0, 0, 0), 1, 1,
                            SPEED_FN(lambda ctx, ty, ac: speeds[ac] if 0 <= ac < 4 else math.nan),
                            RAND_FN(lambda ctx: crand()), None, now)
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        log = new_log()
        status = lib.dll.mu_obj_move(cobj, 0, ctypes.byref(inputs), ctypes.byref(log))
        c_calls = [e[:3] for e in log_events(log)]
        diff = [hex(i) for i in range(OBJ_SIZE) if guest[i] != cobj.raw[i]]
        t.count(f'type {typ:#x}' if typ in (1, 5, 0xd) else 'other type')
        t.add(not diff and calls == c_calls and status in (0, 1),
              {'case': n, 'type': typ, 'now': now, 'diff': diff[:8], 'calls': calls, 'c': c_calls, 'status': status})
    return t


# ---------------------------------------------------------------- 3. visual

def family_visual(machine, lib, g, cases):
    t = Tally('visual')
    for n in range(cases):
        o = login_object(g, g.choice([5, 5, 5, 0x26, 0x36, 0x26, 0x36, g.randrange(0, 60)]))
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        seed = g.getrandbits(32)
        rnd = MsvcRand(seed)
        calls = []

        def transform(m):
            a = [m.argument(i) for i in range(4)]
            bone = (a[0] - BONES_BASE) // 0x30 if (a[0] - BONES_BASE) % 0x30 == 0 else ('matrix', a[0])
            local = struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12)))
            ok = m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
            calls.append((0x012b6ef1, 0, bone) + read_vec(m, a[1]) + (a[3],) if ok else ('transform this', a))
            m.uc.mem_write(a[2], struct.pack('<3f', *bone_out(bone if isinstance(bone, int) else 0, local)))
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
        stubs = {0x01989721: lambda m: rnd(), 0x012b6ef1: transform, 0x01692eb7: sprite, 0x0168fafd: particle}
        regions = global_regions(WORLD, 3, [am.defined_region('object', OBJECTS, bytes(o), writable=False),
                                           am.defined_region('model', MODEL, bytes(0x100), writable=False)])
        result = run(machine, 0x00e24be1, [OBJECTS, MODEL], regions, stubs, ecx=FAKE, cleanup=8)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        crand = MsvcRand(seed)

        def cbone(ctx, bone, local, out):
            v = bone_out(bone, (local[0], local[1], local[2]))
            for k in range(3):
                out[k] = v[k]
        keep = (RAND_FN(lambda ctx: crand()), BONE_FN(cbone))
        log = new_log()
        handled = lib.dll.mu_login_visual(ctypes.create_string_buffer(bytes(o), OBJ_SIZE), 0, keep[0], keep[1],
                                          None, ctypes.byref(log))
        c_calls = log_events(log)
        t.count('sprites', sum(1 for c in calls if c[0] == 0x01692eb7))
        t.count('particles', sum(1 for c in calls if c[0] == 0x0168fafd))
        t.add(calls == c_calls and (result['eax'] & 0xff) == handled,
              {'case': n, 'type': typ, 'calls': calls[:3], 'c': c_calls[:3], 'eax': result['eax'], 'handled': handled})
    return t


# ---------------------------------------------------------------- 4. custom render

def family_custom(machine, lib, g, cases):
    t = Tally('custom')
    for n in range(cases):
        o = login_object(g)
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        calls = []

        def body(m):
            ok = m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
            calls.append((0x00966def, 0) + tuple(m.argument(i) for i in range(8)) if ok else ('body this',))
            return (0, 0x20)
        regions = global_regions(WORLD, 3, [am.defined_region('object', OBJECTS, bytes(o)),
                                           am.defined_region('model', MODEL, bytes(0x100), writable=False)])
        result = run(machine, 0x00e254bb, [OBJECTS, MODEL, 0], regions, {0x00966def: body}, ecx=FAKE, cleanup=12)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        log = new_log()
        handled = lib.dll.mu_login_custom_render(cobj, 0, ctypes.byref(log))
        same = result['regions']['object'] == cobj.raw[:OBJ_SIZE]
        t.count('handled' if handled else 'not handled')
        t.add(same and calls == log_events(log) and (result['eax'] & 0xff) == handled,
              {'case': n, 'type': typ, 'calls': calls, 'c': log_events(log)})
    return t


# ---------------------------------------------------------------- 5. after-character render

def family_after(machine, lib, g, cases):
    t = Tally('after')
    for n in range(cases):
        o = login_object(g, g.choice([5, 5, 5, 0xd, 0xd, g.randrange(0, 60)]))
        typ = struct.unpack_from('<i', o, 0x5c)[0]
        now = now_value(g)
        model = bytes(g.getrandbits(8) for _ in range(0x100))
        calls = []

        def mesh(m):
            ok = m.uc.reg_read(m.x86.UC_X86_REG_ECX) == MODEL
            calls.append((0x00966e4a, 0) + tuple(m.argument(i) for i in range(8)) if ok else ('mesh this',))
            return (0, 0x20)
        writes = []
        regions = global_regions(WORLD, 3, [am.defined_region('object', OBJECTS, bytes(o)),
                                           am.defined_region('model', MODEL, model)])
        hook = time_hook(machine, now)

        def on_color(u, access, address, size, value, ignored):
            if address == MODEL + 0x5c:   # the third component completes a colour write
                c = struct.unpack('<2I', bytes(u.mem_read(MODEL + 0x54, 8)))
                writes.append((0x54, 0, c[0], c[1], value & 0xffffffff))
        from unicorn import UC_HOOK_MEM_WRITE
        color_hook = machine.uc.hook_add(UC_HOOK_MEM_WRITE, on_color, begin=MODEL + 0x54, end=MODEL + 0x5f)
        try:
            result = run(machine, 0x00e25639, [OBJECTS, MODEL, 0], regions, {0x00966e4a: mesh}, ecx=FAKE,
                         cleanup=12)
        finally:
            machine.uc.hook_del(hook)
            machine.uc.hook_del(color_hook)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'type': typ}, stop)
            continue
        # interleave: colour writes happen between meshes; rebuild the order from the call counts
        cobj = ctypes.create_string_buffer(bytes(o), OBJ_SIZE)
        cmodel = ctypes.create_string_buffer(model, 0x100)
        log = new_log()
        handled = lib.dll.mu_login_after_render(cobj, cmodel, 0, now, None, None, ctypes.byref(log))
        c_events = log_events(log)
        c_calls = [e for e in c_events if e[0] == 0x00966e4a]
        c_colors = [e for e in c_events if e[0] == 0x54]
        same = result['regions']['object'] == cobj.raw[:OBJ_SIZE] and result['regions']['model'] == cmodel.raw[:0x100]
        t.count('meshes', len(calls))
        t.add(same and calls == c_calls and writes == c_colors,
              {'case': n, 'type': typ, 'now': now, 'calls': calls[:3], 'c': c_calls[:3], 'colors': writes,
               'c_colors': c_colors, 'state': same, 'handled': handled})
    return t


# ---------------------------------------------------------------- 6. after-character pass

CHAIN_AFTER = (0x00ea233c, 0x00e94004, 0x00e3068f, 0x00e6eccc, 0x00e18ae9)


def family_after_pass(machine, lib, g, cases):
    t = Tally('after_pass')
    for n in range(cases):
        scene = g.choice([3, 3, 5, 6])
        top = 1 if g.random() < 0.1 else 0
        count = g.randrange(0, 50)
        x2d, y2d = frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4

        def fields(g, o, k):
            o[0] = g.choice([0, 1, 1, 1, 1])
            o[0xa] = g.choice([0, 1, 1, 2])
            o[0xb] = g.choice([0, 1])
            put_i(o, 0x5c, g.choice(LOGIN_TYPES + [g.randrange(0, 300)]))
            put_f(o, 0x158, f32((cx + g.uniform(-45, 45)) * 100), f32((cy + g.uniform(-45, 45)) * 100),
                  f32(g.uniform(0, 300)))
            put_f(o, 0xc0, f32(g.choice([-30.0, -428.571, g.uniform(-600, 50)])))
        objects, heads, nxt = object_list(g, count, fields)
        counter = g.choice([0, 5, 40, 41, 100])
        calls = []
        index = lambda a: (a - OBJECTS) // 0x400

        def draw(m):
            calls.append((0x016d6791, index(m.argument(0))) + tuple(m.argument(i) for i in range(1, 4)))
            return 0
        # the first-draw predicate's default asks the world manager (0x00ea27b4, client code) for the
        # handler's slot 0x14: the manager +0x10 holds an object with the real CGMLogInScene_Ex vtable
        stubs = {0x016d6791: draw, 0x00db747f: lambda m: FAKE, 0x0095fba9: lambda m: 0, 0x009a6ef3: lambda m: FAKE,
                 0x00ea594b: lambda m: FAKE + 0x100}
        fake = bytearray(fake_object())
        struct.pack_into('<I', fake, 0x110, FAKE + 0x380)
        struct.pack_into('<I', fake, 0x380, LOGIN_VTABLE)
        for address in CHAIN_AFTER:
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
    ('type 5 PlaySpeed 0.25', 'login_world.c', 'arg_f(e, 0.23f);', 'arg_f(e, 0.25f);', 'create'),
    ('range -428.571 for every type', 'login_world.c', '} else if (t == 0x26 || t == 0x36) {\n        mu_obj_set_i32',
     '} else if (t == 0x26) {\n        mu_obj_set_i32', 'create'),
    ('scroll +0.005', 'login_world.c', 'MU_OBJF_BLEND_V) - 0.005f', 'MU_OBJF_BLEND_V) + 0.005f', 'move'),
    ('pulse without fabs', 'login_world.c', 's = fabsf(s);', 's = s * 1.0f;', 'move'),
    ('bone 98 lantern offset 2.6', 'login_world.c', '60, 2.8f, 10, 2.0f', '60, 2.6f, 10, 2.0f', 'visual'),
    ('mist particle every 5th', 'login_world.c', 'mist ? 6 : 2', 'mist ? 5 : 2', 'visual'),
    ('type 0xd not after-character', 'login_world.c', 'case 5: case 0xd:\n        body(log, index, o);\n        o[MU_OBJF_AFTER_CHARACTER] = 1;',
     'case 5:\n        body(log, index, o);\n        o[MU_OBJF_AFTER_CHARACTER] = 1;', 'custom'),
    ('lantern alpha 0.8', 'login_world.c', 'mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.7f);',
     'mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.8f);', 'after'),
    ('after pass ignores top view', 'login_world.c', 'if (o[MU_OBJF_VISIBLE] || in->top_view) {',
     'if (o[MU_OBJF_VISIBLE]) {', 'after_pass'),
]


def build_library(directory):
    subprocess.run(['make', '-s', '-C', str(directory / 'objects')], check=True)
    return directory / 'objects' / f'libobjects.{SUFFIX}'


def mutations(machine, args):
    out = []
    for label, file, old, new, family in MUTATIONS:
        scratch = Path(tempfile.mkdtemp(prefix='loginworld-mut-'))
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
            tally = FAMILIES[family](machine, lib, random.Random(args.seed + 29), args.mutation_cases)
            out.append({'mutation': label, 'family': family, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped})
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    evidence = ROOT / 'evidence'
    if not evidence.exists():
        evidence = Path.home() / 'Documents/main-exe-study/evidence'
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(evidence / 'x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(
        evidence / 'image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--library', default=str(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--seed', type=int, default=0x5e5e)
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
            print('  example:', json.dumps(r['examples'][0], default=str)[:900])
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
