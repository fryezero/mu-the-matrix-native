#!/usr/bin/env python3
"""Compare reconstructed/combat with the client's instructions (NATIVE-COMBAT-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case).
The authored C (reconstructed/combat, libcombat) runs on the same inputs.

Families (client routine -> authored function):

* damage_color   0x01691738 -> mu_damage_color
* damage_scale   0x01691bbe -> mu_damage_scale (x87 return, read through a
                 trampoline that stores ST0)
* create_point   0x016912ae -> mu_point_create over the 1000-record pool at
                 0x0a3ae150; RequestTerrainHeight 0x016cc9e2 is a stub that
                 returns the case's height in ST0
* move_points    0x016914a0 -> mu_points_move
* render_points  0x0169159e -> mu_points_render; the blend/depth wrappers
                 0x0184a990 / 0x0184a6da and RenderNumber 0x0184cd2f are
                 recording stubs, the vector accessors run as client code
* render_number  0x0184cd2f -> mu_render_number; RenderSpriteUV 0x0184ca6b
                 and the thousands formatter 0x016b8b26 are recording stubs
                 (the formatter writes the authored string), TEXCOORD
                 0x01851263 and the CRT strlen 0x0195a4b0 run as client code
* show_damage    0x00a01a25 -> mu_show_damage, with CreatePoint as client code
* attack_speed   0x0138dc60 -> mu_set_attack_speed; the model container
                 0x00966cc4 and action getter 0x00d33153 are stubs over a
                 0x186-record action array
* player_attack  0x01392bde -> mu_player_attack_action /
                 mu_monster_attack_action; item lookups, the speed adjustment,
                 the attack start, rand(), SetAction, sounds and the event
                 predicates are recording stubs
* in_range       0x016a52a6 -> mu_in_range (CRT sqrt 0x019856f0 stub, double
                 result in ST0)
* shock_allowed  0x0139f3a0 -> mu_monster_shock_allowed
* dead_fade      0x013a5ea1 -> mu_dead_fade (world/scene predicates, removal
                 and list calls are recording stubs)

Negative controls (Python statements with one planted mistake each) must
disagree with the client on some cases.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

DAMAGE_COLOR, DAMAGE_SCALE = 0x01691738, 0x01691bbe
CREATE_POINT, MOVE_POINTS, RENDER_POINTS = 0x016912ae, 0x016914a0, 0x0169159e
RENDER_NUMBER, SPRITE_UV, TEXCOORD, FORMATTER, STRLEN = 0x0184cd2f, 0x0184ca6b, 0x01851263, 0x016b8b26, 0x0195a4b0
SHOW_DAMAGE, TERRAIN_HEIGHT = 0x00a01a25, 0x016cc9e2
BLEND_990, DEPTH_OFF = 0x0184a990, 0x0184a6da
ATTACK_SPEED, MANAGER, ACTION_GETTER = 0x0138dc60, 0x00966cc4, 0x00d33153
PLAYER_ATTACK = 0x01392bde
IN_RANGE, CRT_SQRT = 0x016a52a6, 0x019856f0
SHOCK_ALLOWED = 0x0139f3a0
DEAD_FADE = 0x013a5ea1
HERO_KEY, HERO_PTR, WORLD = 0x06fca288, 0x0a39d754, 0x01cf15fc
POOL = 0x0a3ae150
BODIES = {  # start, exclusive end
    'damage_color': (0x01691738, 0x01691bbe), 'damage_scale': (0x01691bbe, 0x01691c40),
    'create_point': (0x016912ae, 0x0169146f), 'move_points': (0x016914a0, 0x0169159e),
    'render_points': (0x0169159e, 0x016916ca), 'render_number': (0x0184cd2f, 0x0184d875),
    'texcoord': (0x01851263, 0x0185128e), 'strlen': (0x0195a4b0, 0x0195a53b),
    'show_damage': (0x00a01a25, 0x00a021e0), 'attack_speed': (0x0138dc60, 0x0138f92f),
    'player_attack': (0x01392bde, 0x01393a61), 'in_range': (0x016a52a6, 0x016a532a),
    'shock_allowed': (0x0139f3a0, 0x0139f3db), 'dead_fade': (0x013a5ea1, 0x013a659e),
    'class_nibble': (0x0095f5cc, 0x0095f5d7), 'safe_zone': (0x0095fb27, 0x0095fb37),
    'vector_at': (0x00cfc922, 0x00cfc936), 'vector_data': (0x00cfc94a, 0x00cfc956),
}
HELPER = 0x7ffa0000        # trampolines and x87-return helpers (outside every declared region)
HELPER_VALUE = HELPER + 0xf00
HELPER_OUT = 0x2a000000    # trampoline result (a declared region)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


SPECIAL_FLOATS = [0.0, -0.0, 1.0, -1.0, 0.5, 15.0, 14.999999, 15.000001, 50.0, 80.0, 140.0, 300.0, 350.0, 350.00003,
                  299.99997, 10.0, 0.3, 1e-8, -1e-8, 1e30, -1e30, float('inf'), float('-inf'), float('nan'), 288.0,
                  287.99997, 288.00003]


def rfloat(rng, special=0.15, scale=1000.0):
    if rng.random() < special:
        return f32(rng.choice(SPECIAL_FLOATS))
    return f32(rng.uniform(-scale, scale))


NAN_COUNT = [0]


def same(a, b):
    """Binary32 equality; any two NaNs are equal (counted in the report). x86 SSE creates the
    negative indefinite NaN 0xffc00000, AArch64 the default NaN 0x7fc00000, and the hosts
    propagate payloads differently (scripts/validate_effects.py makes the same choice)."""
    if math.isnan(a) and math.isnan(b):
        NAN_COUNT[0] += 1
        return True
    return bits(a) == bits(b)


# --------------------------------------------------------------------------
# Library.

class Point(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('value', ctypes.c_int32), ('extra', ctypes.c_int32),
                ('scale', ctypes.c_float), ('position', ctypes.c_float * 3), ('color', ctypes.c_float * 3),
                ('delay', ctypes.c_int32), ('render_arg', ctypes.c_float), ('move', ctypes.c_uint8),
                ('gravity', ctypes.c_float), ('floor_test', ctypes.c_uint8), ('floor', ctypes.c_float)]


POINT_FIELDS = [  # name, client offset, struct format, kind
    ('live', 0x08, '<B', 'u'), ('value', 0x0c, '<i', 'i'), ('extra', 0x14, '<i', 'i'), ('scale', 0x18, '<f', 'f'),
    ('position0', 0x20, '<f', 'f'), ('position1', 0x24, '<f', 'f'), ('position2', 0x28, '<f', 'f'),
    ('color0', 0x2c, '<f', 'f'), ('color1', 0x30, '<f', 'f'), ('color2', 0x34, '<f', 'f'),
    ('delay', 0x48, '<i', 'i'), ('render_arg', 0x60, '<f', 'f'), ('move', 0x68, '<B', 'u'),
    ('gravity', 0x6c, '<f', 'f'), ('floor_test', 0xa4, '<B', 'u'), ('floor', 0xa8, '<f', 'f')]


def get_field(point, name):
    if name.startswith('position'):
        return point.position[int(name[-1])]
    if name.startswith('color'):
        return point.color[int(name[-1])]
    return getattr(point, name)


def set_field(point, name, value):
    if name.startswith('position'):
        point.position[int(name[-1])] = value
    elif name.startswith('color'):
        point.color[int(name[-1])] = value
    else:
        setattr(point, name, value)


class NumberCall(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('position', ctypes.c_float * 3), ('value', ctypes.c_int32),
                ('color', ctypes.c_float * 3), ('alpha', ctypes.c_float), ('scale', ctypes.c_float),
                ('render_arg', ctypes.c_float)]


class SpriteCall(ctypes.Structure):
    _fields_ = [('bitmap', ctypes.c_int32), ('position', ctypes.c_float * 3), ('width', ctypes.c_float),
                ('height', ctypes.c_float), ('uv', ctypes.c_float * 8), ('light', ctypes.c_float * 12),
                ('alpha', ctypes.c_float), ('skew', ctypes.c_float)]


class DamageInfo(ctypes.Structure):
    _fields_ = [('damage', ctypes.c_int32), ('type', ctypes.c_int32), ('flag8', ctypes.c_uint8),
                ('flag9', ctypes.c_uint8), ('flag_a', ctypes.c_uint8), ('flag_b', ctypes.c_uint8),
                ('flag_c', ctypes.c_uint8), ('flag_d', ctypes.c_uint8)]


class AttackInput(ctypes.Structure):
    _fields_ = [('object_type', ctypes.c_int32), ('class_byte', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8),
                ('counter', ctypes.c_uint8), ('weapon', ctypes.c_int16 * 2), ('wing', ctypes.c_int16),
                ('attr_present', ctypes.c_uint8 * 2), ('two_handed', ctypes.c_uint8), ('bow_kind', ctypes.c_int32),
                ('dual', ctypes.c_uint8), ('state_72', ctypes.c_uint8),
                ('rand_values', ctypes.POINTER(ctypes.c_int32)), ('rand_count', ctypes.c_int32)]


class AttackResult(ctypes.Structure):
    _fields_ = [('action', ctypes.c_int32), ('speed_update', ctypes.c_int32), ('attack_start', ctypes.c_int32),
                ('rand_used', ctypes.c_int32), ('fault', ctypes.c_int32)]


class FadeState(ctypes.Structure):
    _fields_ = [('timer', ctypes.c_float), ('alpha', ctypes.c_float), ('z', ctypes.c_float),
                ('model', ctypes.c_int32), ('world', ctypes.c_int32), ('o6c', ctypes.c_int32),
                ('is_hero', ctypes.c_uint8), ('removed', ctypes.c_uint8)]


HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)


def load_library(path):
    lib = ctypes.CDLL(str(path))
    F, I, U8, P, V = ctypes.c_float, ctypes.c_int32, ctypes.c_uint8, ctypes.POINTER, ctypes.c_void_p
    for name, args, result in [
            ('mu_damage_color', [I, I, I, U8, U8, P(F)], None), ('mu_damage_scale', [I], F),
            ('mu_point_create', [P(Point), P(F), I, P(F), F, U8, U8, F, I, HEIGHT_FN, V], I),
            ('mu_points_move', [P(Point)], None), ('mu_points_render', [P(Point), U8, P(NumberCall), I], I),
            ('mu_render_number', [P(F), I, P(F), F, F, F, P(SpriteCall), I], I),
            ('mu_format_thousands', [I, ctypes.c_char_p, ctypes.c_size_t], I),
            ('mu_show_damage', [P(Point), I, I, P(F), P(F), F, P(DamageInfo), HEIGHT_FN, V], I),
            ('mu_set_attack_speed', [F, F, P(F)], None), ('mu_attack_speed_writes', [I], ctypes.c_int),
            ('mu_player_attack_action', [P(AttackInput), P(AttackResult)], None),
            ('mu_monster_attack_action', [U8, ctypes.c_int], I),
            ('mu_in_range', [I, I, I, I, F], ctypes.c_int), ('mu_monster_shock_allowed', [I, I], ctypes.c_int),
            ('mu_dead_fade', [U8, P(FadeState)], None)]:
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


# --------------------------------------------------------------------------
# Machine helpers.

class Combat(am.ActorMachine):
    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_ALL
        self.uc.mem_map(HELPER, am.PAGE, UC_PROT_ALL)
        # +0x000: fld dword [VALUE]; ret      +0x010: fld qword [VALUE]; ret
        code = b'\xd9\x05' + struct.pack('<I', HELPER_VALUE) + b'\xc3'
        self.uc.mem_write(HELPER, code)
        self.uc.mem_write(HELPER+0x10, b'\xdd\x05' + struct.pack('<I', HELPER_VALUE) + b'\xc3')
        self.x87_hooks = {}

    def trampoline(self, target, argc, double=False, store_int=False):
        """Code at HELPER+0x100: re-pushes the argc arguments, calls target,
        stores ST0 (or EAX) to HELPER_OUT and returns to the sentinel."""
        code = b''
        for _ in range(argc):
            code += b'\xff\x74\x24' + bytes([4*argc])        # push dword [esp+4*argc]
        address = HELPER+0x100
        call_at = address+len(code)
        code += b'\xe8' + struct.pack('<i', target-(call_at+5))
        if argc:
            code += b'\x83\xc4' + bytes([4*argc])            # add esp, 4*argc
        if store_int:
            code += b'\xa3' + struct.pack('<I', HELPER_OUT)  # mov [OUT], eax
        else:
            code += (b'\xdd\x1d' if double else b'\xd9\x1d') + struct.pack('<I', HELPER_OUT)  # fstp
        code += b'\xc3'
        self.uc.mem_write(address, code)
        self.uc.ctl_flush_tb()
        return address

    def x87_return(self, value, double=False):
        """For use inside a stub handler: returns `value` in ST0 by jumping to
        the fld helper with the caller's return address still on the stack."""
        self.uc.mem_write(HELPER_VALUE, struct.pack('<d', value) if double else struct.pack('<f', value))
        return ('x87', HELPER+(0x10 if double else 0))

    def stub_entry(self, uc, address, size, ignored):
        handler = self.stubs.get(address)
        if handler is None:
            return
        x86 = self.x86
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret = self.read32(esp)
        try:
            result = handler(self)
        except Exception as failure:
            self.stop(('stub-error', hex(address), repr(failure)))
            return
        if self.state['stopped'] is not None:
            return
        if isinstance(result, tuple) and result and result[0] == 'x87':
            uc.reg_write(x86.UC_X86_REG_EIP, result[1])
            return
        eax, cleanup = result if isinstance(result, tuple) else (result, 0)
        uc.reg_write(x86.UC_X86_REG_EAX, eax & 0xffffffff)
        uc.reg_write(x86.UC_X86_REG_ESP, esp+4+cleanup)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def caller_stack(self, uc, access, address, size, value, ignored):
        if address >= am.ENTRY_ESP+4 and address+size <= am.ENTRY_ESP+4+self.argument_bytes:
            return   # reads and writes of the routine's own argument slots
        super().caller_stack(uc, access, address, size, value, ignored)

    def float_argument(self, index):
        return from_bits(self.argument(index))

    def floats(self, address, count):
        return list(struct.unpack(f'<{count}f', self.uc.mem_read(address, 4*count)))


def out_region():
    return am.Region('out', HELPER_OUT, b'\0'*8, bytes(8))


def read_out(result, double=False):
    raw = result['regions']['out']
    return struct.unpack('<d', raw)[0] if double else struct.unpack('<f', raw[:4])[0]


def ok(result):
    return result['ok']


# --------------------------------------------------------------------------
# Families.

class Report:
    def __init__(self):
        self.families = {}

    def add(self, family, equal, failure=None):
        entry = self.families.setdefault(family, {'cases': 0, 'equal': 0, 'first_failures': []})
        entry['cases'] += 1
        entry['equal'] += bool(equal)
        if not equal and len(entry['first_failures']) < 5:
            entry['first_failures'].append(failure)


def family_damage_color(m, lib, rng, cases, report, negatives):
    hero = 0x1234
    for _ in range(cases):
        t = rng.choice(list(range(-2, 14)) + [rng.randrange(-2**31, 2**31)])
        key = hero if rng.random() < 0.5 else rng.randrange(0, 0x10000)
        fa = rng.choice([0, 1, 1, 2, 0xff])
        fb = rng.choice([0, 0, 1, 2, 0x80])
        color = am.Region('color', 0x21000000, b'\0'*12, bytes(12))
        regions = [color, am.defined_region('hero-key', HERO_KEY, struct.pack('<i', hero), writable=False)]
        r = m.execute(DAMAGE_COLOR, [t, key, 0x21000000, 0xab00 | fa, 0xcd00 | fb], regions, {})
        client = struct.unpack('<3f', r['regions']['color']) if ok(r) else None
        c = (ctypes.c_float*3)()
        lib.mu_damage_color(t, key, hero, fa, fb, c)
        equal = ok(r) and all(same(a, b) for a, b in zip(client, c))
        report.add('damage_color', equal, {'type': t, 'key': key, 'fa': fa, 'fb': fb, 'stopped': r['stopped']})
        if ok(r):
            # negative control: orange for the hero too
            wrong = list(c)
            if t == 0 and fa != 1 and not fb and key == hero:
                wrong = [1.0, f32(0.6), 0.0]
            negatives['damage_color_no_hero_red'] += any(not same(a, b) for a, b in zip(client, wrong))


def family_damage_scale(m, lib, rng, cases, report, negatives):
    tramp = m.trampoline(DAMAGE_SCALE, 1)
    for _ in range(cases):
        t = rng.choice(list(range(-2, 14)) + [rng.randrange(-2**31, 2**31)])
        r = m.execute(tramp, [t], [out_region()], {})
        client = read_out(r) if ok(r) else None
        mine = lib.mu_damage_scale(t)
        equal = ok(r) and same(client, mine)
        report.add('damage_scale', equal, {'type': t, 'client': client, 'c': mine, 'stopped': r['stopped']})
        if ok(r):
            negatives['damage_scale_crit_15'] += not same(client, 15.0 if t == 3 else mine)


def pool_region(points, defined_fields):
    """Client bytes of the pool from the C records; fields in defined_fields[i] are defined."""
    data = bytearray(am.poison(MU_BYTES, 0x33))
    mask = bytearray(MU_BYTES)
    for i, fields in enumerate(defined_fields):
        base = i*0xb4
        for name, offset, fmt, kind in POINT_FIELDS:
            if name in fields:
                value = get_field(points[i], name)
                raw = struct.pack(fmt, value)
                data[base+offset:base+offset+len(raw)] = raw
                mask[base+offset:base+offset+len(raw)] = b'\1'*len(raw)
    return am.Region('pool', POOL, bytes(data), bytes(mask))


MU_BYTES = 1000*0xb4
SENTINELS = {'u': 0xa5, 'i': 0x5a5a5a5a, 'f': f32(-7.77e7)}


def compare_pool(points, raw, mask, before_defined):
    """Every field the client defined must equal C; fields the client left
    undefined must still hold the C sentinel (C did not write them)."""
    for i in range(1000):
        base = i*0xb4
        for name, offset, fmt, kind in POINT_FIELDS:
            size = struct.calcsize(fmt)
            defined = all(mask[base+offset:base+offset+size])
            mine = get_field(points[i], name)
            if defined:
                theirs = struct.unpack(fmt, bytes(raw[base+offset:base+offset+size]))[0]
                if kind == 'f':
                    if not same(theirs, mine):
                        return (i, name, theirs, mine)
                elif (theirs & (0xff if kind == 'u' else 0xffffffff)) != (mine & (0xff if kind == 'u' else 0xffffffff)):
                    return (i, name, theirs, mine)
            else:
                sentinel = SENTINELS[kind]
                if (kind == 'f' and not same(mine, sentinel)) or (kind != 'f' and mine != sentinel):
                    return (i, name, 'undefined', mine)
    return None


def random_points(rng, live_fraction, fields_for_live, force_dead_before=None, define_delay=False):
    points = (Point*1000)()
    defined = []
    for i in range(1000):
        p = points[i]
        for name, offset, fmt, kind in POINT_FIELDS:
            set_field(p, name, SENTINELS[kind])
        live = rng.random() < live_fraction
        if force_dead_before is not None:
            live = i < force_dead_before
        p.live = (rng.choice([1, 2, 0x80, 0xff]) if live else 0)
        fields = {'live'}
        if define_delay:
            p.delay = rng.choice([0, 3, -1, 0x7fffffff])   # CreatePoint's `and [+0x48], 0` reads it
            fields.add('delay')
        if live:
            for name in fields_for_live:
                kind = [f for f in POINT_FIELDS if f[0] == name][0][3]
                if kind == 'f':
                    set_field(p, name, rfloat(rng, 0.2, 400.0))
                elif kind == 'u':
                    set_field(p, name, rng.choice([0, 1, 1, 2, 0xff]))
                else:
                    set_field(p, name, rng.choice([-2, -1, 0, 1, 5, rng.randrange(-2**31, 2**31)]))
                fields.add(name)
        defined.append(fields)
    return points, defined


def height_stub(case_height, record):
    def stub(m):
        x, y = m.float_argument(0), m.float_argument(1)
        record.append(('height', x, y))
        return m.x87_return(case_height)
    return stub


def family_create_point(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        first_free = rng.choice([0, 1, 7, 500, 998, 999, 1000]) if n % 4 == 0 else None
        points, defined = random_points(rng, rng.choice([0.0, 0.3, 0.9]), [], force_dead_before=first_free,
                                        define_delay=True)
        pos = [rfloat(rng) for _ in range(3)]
        color = [rfloat(rng, 0.1, 1.0) for _ in range(3)]
        value = rng.choice([-1, -2, -6, 0, 1, 123, 99999, rng.randrange(-2**31, 2**31)])
        scale, render_arg = rfloat(rng, 0.2, 60.0), rfloat(rng, 0.2, 5.0)
        move, floor_test = rng.choice([0, 1, 0xff]), rng.choice([0, 1, 0x80])
        extra = rng.randrange(-2**31, 2**31)
        h = rfloat(rng, 0.2, 500.0)
        record = []
        args_region = am.defined_region('args', 0x21000000, struct.pack('<3f', *pos) + struct.pack('<3f', *color),
                                        writable=False)
        regions = [pool_region(points, defined), args_region]
        stubs = {TERRAIN_HEIGHT: height_stub(h, record)}
        r = m.execute(CREATE_POINT, [0x21000000, value, 0x2100000c, bits(scale), 0x1100 | move, 0x2200 | floor_test,
                                     bits(render_arg), extra], regions, stubs, ecx=POOL, cleanup=0x20)
        cpos, ccol = (ctypes.c_float*3)(*pos), (ctypes.c_float*3)(*color)
        fn = HEIGHT_FN(lambda ctx, x, y: h)
        index = lib.mu_point_create(points, cpos, value, ccol, scale, move, floor_test, render_arg, extra, fn, None)
        mismatch = None
        if ok(r):
            pool = [x for x in regions if x.name == 'pool'][0]
            mismatch = compare_pool(points, r['regions']['pool'], pool.defined, defined)
        equal = ok(r) and mismatch is None
        report.add('create_point', equal, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'index': index})
        if ok(r) and index >= 0:
            # negative control: floor without the +140
            raw = r['regions']['pool'][index*0xb4+0xa8:index*0xb4+0xac]
            negatives['create_point_floor_without_140'] += not same(struct.unpack('<f', raw)[0], h)


def family_move_points(m, lib, rng, cases, report, negatives):
    live_fields = ['value', 'scale', 'position2', 'delay', 'move', 'gravity']
    for n in range(cases):
        points, defined = random_points(rng, rng.choice([0.01, 0.2, 0.7]), live_fields)
        for i in range(1000):
            if points[i].live and rng.random() < 0.6:
                points[i].delay = rng.choice([0, 0, 1, -5])
        regions = [pool_region(points, defined)]
        r = m.execute(MOVE_POINTS, [], regions, {}, ecx=POOL)
        before = [(points[i].live, points[i].scale, points[i].gravity, points[i].value) for i in range(1000)]
        lib.mu_points_move(points)
        mismatch = compare_pool(points, r['regions']['pool'], regions[0].defined, defined) if ok(r) else None
        equal = ok(r) and mismatch is None
        report.add('move_points', equal, {'case': n, 'mismatch': mismatch, 'stopped': r['stopped']})
        if ok(r):
            raw = r['regions']['pool']
            # negative control: the scale floor also for HIT (-2)
            for i in range(1000):
                live, scale, gravity, value = before[i]
                if live and value == -2 and points[i].delay < 0:
                    s = struct.unpack('<f', raw[i*0xb4+0x18:i*0xb4+0x1c])[0]
                    wrong = max(15.0, f32(scale-5.0)) if not math.isnan(scale) else scale
                    negatives['move_points_hit_shrinks'] += not same(s, f32(wrong))
                    break


def family_render_points(m, lib, rng, cases, report, negatives):
    live_fields = ['value', 'scale', 'position0', 'position1', 'position2', 'color0', 'color1', 'color2',
                   'render_arg', 'gravity', 'floor_test', 'floor']
    for n in range(cases):
        points, defined = random_points(rng, rng.choice([0.0, 0.005, 0.05]), live_fields)
        mode = rng.choice([0, 1, 2, 3, 0xff])
        record = []

        def render_number(mm):
            pos = mm.floats(mm.argument(0), 3)
            col = mm.floats(mm.argument(2), 3)
            record.append(('number', pos, struct.unpack('<i', struct.pack('<I', mm.argument(1)))[0], col, mm.float_argument(3), mm.float_argument(4),
                           mm.float_argument(5)))
            return 0

        def blend(mm):
            record.append(('blend', mm.argument(0)))
            return 0

        def depth(mm):
            record.append(('depth',))
            return 0
        regions = [pool_region(points, defined)]
        r = m.execute(RENDER_POINTS, [0x5500 | mode], regions,
                      {RENDER_NUMBER: render_number, BLEND_990: blend, DEPTH_OFF: depth}, ecx=POOL, cleanup=4)
        calls = (NumberCall*1000)()
        count = lib.mu_points_render(points, mode, calls, 1000)
        mine = [('blend', 1), ('depth',)] + [('number', list(c.position), c.value, list(c.color), c.alpha, c.scale,
                                              c.render_arg) for c in calls[:count]]
        equal = ok(r) and len(mine) == len(record) and all(_same_call(a, b) for a, b in zip(record, mine))
        diff = next(([a, b] for a, b in zip(record, mine) if not _same_call(a, b)), None)
        report.add('render_points', equal, {'case': n, 'mode': mode, 'client': len(record), 'c': len(mine),
                                            'diff': diff, 'stopped': r['stopped']})
        if ok(r):
            negatives['render_points_alpha_gravity'] += any(
                x[0] == 'number' and not same(x[4], x[5]) for x in record[2:3])


def _flat(x):
    out = []
    for v in x:
        if isinstance(v, (list, tuple)):
            out += _flat(v)
        else:
            out.append(v)
    return out


def _same_call(a, b):
    fa, fb = _flat(a), _flat(b)
    if len(fa) != len(fb):
        return False
    for x, y in zip(fa, fb):
        if isinstance(x, float) or isinstance(y, float):
            if not same(float(x), float(y)):
                return False
        elif x != y:
            return False
    return True


def family_render_number(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        value = rng.choice([-12, -11, -10, -7, -6, -3, -2, -1, 0, 1, 9, 10, 99, 999, 1000, 1001, 12345, 999999,
                            1000000, 2147483647, rng.randrange(0, 2**31), rng.randrange(1, 5000)])
        pos = [rfloat(rng, 0.1, 500.0) for _ in range(3)]
        color = [rfloat(rng, 0.1, 1.0) for _ in range(3)]
        alpha, scale, arg6 = rfloat(rng, 0.2, 4.0), rfloat(rng, 0.2, 60.0), rfloat(rng, 0.3, 5.0)
        record = []
        text = ctypes.create_string_buffer(64)
        lib.mu_format_thousands(value, text, 64)

        def formatter(mm):
            record.append(('format', mm.uc.mem_read(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP)+4, 8).hex()))
            mm.uc.mem_write(mm.argument(2), text.value + b'\0')
            return 0

        def sprite(mm):
            record.append(('sprite', mm.argument(0), mm.floats(mm.argument(1), 3), mm.float_argument(2),
                           mm.float_argument(3), mm.floats(mm.argument(4), 8), mm.floats(mm.argument(5), 12),
                           mm.float_argument(6), mm.float_argument(7)))
            return 0
        args = am.defined_region('args', 0x21000000, struct.pack('<3f', *pos) + struct.pack('<3f', *color),
                                 writable=False)
        r = m.execute(RENDER_NUMBER, [0x21000000, value, 0x2100000c, bits(alpha), bits(scale), bits(arg6)], [args],
                      {SPRITE_UV: sprite, FORMATTER: formatter})
        sprites = (SpriteCall*64)()
        count = lib.mu_render_number((ctypes.c_float*3)(*pos), value, (ctypes.c_float*3)(*color), alpha, scale, arg6,
                                     sprites, 64)
        client = [x for x in record if x[0] == 'sprite']
        mine = [('sprite', s.bitmap, list(s.position), s.width, s.height, list(s.uv), list(s.light), s.alpha, s.skew)
                for s in sprites[:count]]
        formats = [x for x in record if x[0] == 'format']
        format_ok = (not formats and -11 <= value <= -1) or \
            (len(formats) == 1 and formats[0][1] == struct.pack('<d', float(value)).hex())
        equal = ok(r) and format_ok and len(client) == len(mine) and all(_same_call(a, b) for a, b in zip(client, mine))
        report.add('render_number', equal, {'case': n, 'value': value, 'client': len(client), 'c': len(mine),
                                            'format_ok': format_ok, 'stopped': r['stopped']})
        if ok(r) and len(client) > 1:
            negatives['render_number_no_diagonal'] += not same(client[1][2][1], client[0][2][1])


def family_show_damage(m, lib, rng, cases, report, negatives):
    hero = 0x4242
    for n in range(cases):
        points, defined = random_points(rng, rng.choice([0.0, 0.2, 0.95, 0.999]), [], define_delay=True)
        info = DamageInfo(damage=rng.choice([0, 0, 1, 77, 4321, rng.randrange(-2**31, 2**31)]),
                          type=rng.choice(list(range(0, 14)) + [rng.randrange(-5, 40)]),
                          flag8=rng.random() < 0.25, flag9=rng.random() < 0.25, flag_a=rng.random() < 0.25,
                          flag_b=rng.random() < 0.3, flag_c=rng.random() < 0.3, flag_d=rng.random() < 0.3)
        key = hero if rng.random() < 0.4 else rng.randrange(0, 0x8000)
        pos = [rfloat(rng, 0.1, 500.0) for _ in range(3)]
        color = [rfloat(rng, 0.1, 1.0) for _ in range(3)]
        scale = rfloat(rng, 0.2, 60.0)
        h = rfloat(rng, 0.2, 300.0)
        record = []
        info_raw = struct.pack('<ii6B', info.damage, info.type, info.flag8, info.flag9, info.flag_a, info.flag_b,
                               info.flag_c, info.flag_d)
        info_mask = b'\1'*14
        args = am.Region('args', 0x21000000, struct.pack('<3f', *pos) + struct.pack('<3f', *color) + info_raw,
                         b'\1'*24 + info_mask)
        regions = [pool_region(points, defined), args,
                   am.defined_region('hero-key', HERO_KEY, struct.pack('<i', hero), writable=False)]
        r = m.execute(SHOW_DAMAGE, [key, 0x21000000, 0x2100000c, bits(scale), 0x21000018], regions,
                      {TERRAIN_HEIGHT: height_stub(h, record)}, ecx=0x31313131, cleanup=0x14)
        ccol = (ctypes.c_float*3)(*color)
        fn = HEIGHT_FN(lambda ctx, x, y: h)
        made = lib.mu_show_damage(points, key, hero, (ctypes.c_float*3)(*pos), ccol, scale, ctypes.byref(info), fn,
                                  None)
        mismatch = compare_pool(points, r['regions']['pool'], regions[0].defined, defined) if ok(r) else None
        color_after = struct.unpack('<3f', r['regions']['args'][12:24]) if ok(r) else None
        color_equal = ok(r) and all(same(a, b) for a, b in zip(color_after, ccol))
        equal = ok(r) and mismatch is None and color_equal
        report.add('show_damage', equal, {'case': n, 'mismatch': mismatch, 'color_equal': color_equal, 'made': made,
                                          'stopped': r['stopped']})
        if ok(r) and info.damage and info.flag8:
            negatives['show_damage_flag8_single'] += made != 1


def family_attack_speed(m, lib, rng, cases, report, negatives):
    actions = 0x7a000000
    for n in range(cases):
        a = rng.choice([0.0, 287.0, 288.0, 289.0, 287.99997, 288.00003, float('nan'), 65535.0, -1.0, 1e9]) \
            if n % 3 == 0 else f32(rng.choice([rng.uniform(0, 600), float(rng.randrange(0, 2000))]))
        mg = rng.choice([0.0, 100.0, float('nan'), 65535.0]) if n % 3 == 1 else \
            f32(rng.choice([rng.uniform(0, 600), float(rng.randrange(0, 2000))]))
        a, mg = f32(a), f32(mg)
        region = am.Region('actions', actions, am.poison(0x186*0x10, 0x44), bytes(0x186*0x10))
        record = []

        def manager(mm):
            record.append('m')
            return 0x5e5e0000

        def getter(mm):
            this = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
            action = mm.argument(0)
            if this != 0x5e5e0000 or not 0 <= action < 0x186:
                mm.stop(('getter', hex(this), action))
                return 0
            return actions + action*0x10, 4
        r = m.execute(ATTACK_SPEED, [bits(a), bits(mg)], [region], {MANAGER: manager, ACTION_GETTER: getter})
        speeds = (ctypes.c_float*0x186)(*([f32(-7.77e7)]*0x186))
        lib.mu_set_attack_speed(a, mg, speeds)
        mismatch = None
        if ok(r):
            raw, mask = r['regions']['actions'], region.defined
            for i in range(0x186):
                written = all(mask[i*0x10+4:i*0x10+8])
                others = any(mask[i*0x10:i*0x10+4]) or any(mask[i*0x10+8:i*0x10+0x10])
                if others:
                    mismatch = (i, 'other bytes written')
                    break
                if written:
                    theirs = struct.unpack('<f', raw[i*0x10+4:i*0x10+8])[0]
                    if not same(theirs, speeds[i]):
                        mismatch = (i, theirs, speeds[i])
                        break
                elif not same(speeds[i], f32(-7.77e7)):
                    mismatch = (i, 'C wrote an action the client did not')
                    break
        equal = ok(r) and mismatch is None
        report.add('attack_speed', equal, {'case': n, 'a': a, 'm': mg, 'mismatch': mismatch, 'stopped': r['stopped']})
        if ok(r) and not math.isnan(a) and a >= 288.0:
            theirs = struct.unpack('<f', r['regions']['actions'][0x6f*0x10+4:0x6f*0x10+8])[0]
            negatives['attack_speed_no_cap'] += not same(theirs, f32(f32(0.6) + f32(a*f32(0.004))))


MONSTER_PREDICATES = [0x00df242b, 0x00d90793, 0x00e00479, 0x00d6a4aa, 0x00db3660, 0x00e77e2f, 0x00e8087b, 0x00e8d6a6,
                      0x00e33c6e, 0x00e6680b]
MONSTER_CHAINS = [(0x00d53c8f, 0x00d55bb6), (0x00ea594b, 0x00ea3f2a), (0x00a9c2fa, 0x00a9c61e)]
CHAR = 0x24000000
OBJ = CHAR + 0x3254


def family_player_attack(m, lib, rng, cases, report, negatives):
    item_groups = [-1, -1, 0xae6, 0xaf0, 0xafb, 0xb05, 0xafd, 0xaff, 0x10e5, 0x10e6, 0x10e7, 0x10e8, 0x12e5, 0x12e6,
                   0x12f3, 0x14e5, 0x14e6, 0x16e5, 0x16e6, 0x2000]
    for n in range(cases):
        monster = rng.random() < 0.25
        obj_type = (rng.choice([0x7a5, 0x7a6, 0x7c5, 0x2c1b, 0x28, 0x800]) if monster else 0xa91)
        weapon = [rng.choice(item_groups) if rng.random() < 0.8 else rng.randrange(-1, 0x3000) for _ in range(2)]
        inp = AttackInput(object_type=obj_type, class_byte=rng.randrange(0, 256), safe_zone=rng.choice([0, 0, 1]),
                          counter=rng.randrange(0, 256), wing=rng.choice([-1, -1, 0, 5]),
                          two_handed=rng.choice([0, 0, 1, 2]), bow_kind=rng.choice([0, 0, 0, 1, 2, 3]),
                          dual=rng.choice([0, 0, 1]), state_72=rng.choice([0, 0, 1]))
        inp.weapon[0], inp.weapon[1] = weapon
        inp.attr_present[0], inp.attr_present[1] = rng.choice([0, 1, 1]), rng.choice([0, 1])
        rands = [rng.choice([0, 1, 2, 9, 10, 0x7fff, rng.randrange(0, 0x8000)]) for _ in range(8)]
        inp.rand_values = (ctypes.c_int32*8)(*rands)
        inp.rand_count = 8
        blocks = rng.random() < 0.2 if monster else False
        world = rng.choice([0, 0, 0x49, 7])
        record = []
        rand_index = [0]
        attr_records = {0: 0x26000000, 1: 0x26001000}

        c = am.undefined_region('character', CHAR, 0x3400)
        c.define(CHAR+4, bytes([inp.safe_zone]))
        c.define(CHAR+0x12, bytes([inp.class_byte]))
        c.define(CHAR+0x28, bytes([inp.counter]))
        c.define(CHAR+0x19ac, struct.pack('<h', weapon[0]))
        c.define(CHAR+0x19ac+0x3fc, struct.pack('<h', weapon[1]))
        c.define(CHAR+0x21a4, struct.pack('<h', inp.wing))
        c.define(CHAR+0x3324, struct.pack('<f', 1.0))     # non-zero: the tail skips the effect/sound block
        c.define(OBJ+0x5c, struct.pack('<i', obj_type))
        attr0 = am.Region('attr0', 0x26000000, am.poison(0x300, 0x21), bytes(0x300))
        attr0.define(0x26000000+0x253, bytes([inp.two_handed]))
        attr1 = am.Region('attr1', 0x26001000, am.poison(0x300, 0x22), bytes(0x300))
        regions = [c, attr0, attr1, am.defined_region('world', WORLD, struct.pack('<i', world), writable=False)]
        lookups = []

        def item_holder(mm):
            lookups.append(mm.argument(0))
            return 0x5f000000 + len(lookups)

        def item_attr(mm):
            k = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX) - 0x5f000001
            # first lookup: weapon 0 (top of the routine); a second lookup of weapon 1 happens in the dual branch
            expected = (weapon[0] if k == 0 else weapon[1]) - 0xae6
            if k > 1 or lookups[k] != expected & 0xffffffff:
                mm.stop(('item lookup', k, lookups))
                return 0
            slot = 0 if k == 0 else 1
            return attr_records[slot] if inp.attr_present[slot] else 0

        def rand(mm):
            v = rands[rand_index[0]] if rand_index[0] < len(rands) else 0
            rand_index[0] += 1
            return v

        def recorder(name, value=0, cleanup=0, argc=0):
            def stub(mm):
                record.append((name,) + tuple(mm.argument(i) for i in range(argc)))
                return value, cleanup
            return stub

        def set_action(mm):
            record.append(('set_action', mm.argument(0), mm.argument(1)))
            return 0

        def state(mm):
            a, b = mm.argument(0), mm.argument(1)
            return (0xbe00 | (inp.state_72 if (a, b) == (1, 0x72) else 0)), 8   # push 0x72; push 1 -> f(1, 0x72)
        stubs = {0x00cd4ea8: item_holder, 0x00cd5d29: item_attr, 0x0138d9cf: recorder('speed_update', argc=1),
                 0x01392afd: recorder('attack_start', argc=3), 0x012affa4: set_action, 0x01989721: rand,
                 0x0139d8f8: lambda mm: inp.bow_kind, 0x0139d9ed: lambda mm: 0xde00 | inp.dual,
                 0x0129ddd4: state, 0x013a084d: recorder('tail_13a084d'), 0x0139f3db: lambda mm: 0xaa00,
                 0x00a6ac96: recorder('sound', argc=3), 0x00db747f: lambda mm: 0x27000000}
        for p in MONSTER_PREDICATES:
            stubs[p] = (lambda mm, b=blocks: 0xcc00 | (1 if b else 0))
        for first, second in MONSTER_CHAINS:
            stubs[first] = (lambda mm: 0x27100000)
            stubs[second] = (lambda mm, b=blocks: 0xcc00 | (1 if b else 0))
        stubs[0x27200000] = (lambda mm, b=blocks: (0xcc00 | (1 if b else 0), 8))
        vtable = am.defined_region('vtable', 0x27000000, struct.pack('<I', 0x27000010) + b'\0'*12 +
                                   b'\0'*0x5c + struct.pack('<I', 0x27200000), writable=False)
        regions.append(vtable)
        from unicorn import UC_PROT_ALL
        try:
            m.uc.mem_map(0x27200000, am.PAGE, UC_PROT_ALL)
        except Exception:
            pass
        r = m.execute(PLAYER_ATTACK, [CHAR], regions, stubs)
        res = AttackResult()
        if monster:
            action = lib.mu_monster_attack_action(inp.counter, 1 if blocks else 0) \
                if obj_type not in (0x7c5, 0x2c1b, 0x28) else None
        else:
            lib.mu_player_attack_action(ctypes.byref(inp), ctypes.byref(res))
            action = res.action
        client_actions = [x[2] for x in record if x[0] == 'set_action']
        equal = ok(r)
        if equal:
            if monster and obj_type in (0x7c5, 0x2c1b, 0x28):
                expected = {0x2c1b: [3], 0x28: [1]}.get(obj_type)
                if obj_type == 0x7c5:
                    r0 = rands[0] % 8
                    expected = [3 + rands[1] % 2] if r0 > 2 else ([8] if r0 > 0 else [9])
                equal = client_actions == expected
            else:
                equal = client_actions == ([] if action == -1 else [action])
                if not monster:
                    equal = equal and res.speed_update == sum(1 for x in record if x[0] == 'speed_update') and \
                        res.attack_start == sum(1 for x in record if x[0] == 'attack_start')
            # the counter: +1 by the common tail, +1 more by the monster default branch
            counter_after = r['regions']['character'][0x28]
            bump = 2 if (monster and obj_type not in (0x7c5, 0x2c1b, 0x28) and not blocks) else 1
            equal = equal and counter_after == (inp.counter + bump) & 0xff
        report.add('player_attack', equal, {'case': n, 'type': hex(obj_type), 'weapon': [hex(w & 0xffff) for w in weapon],
                                            'client': client_actions, 'c': action, 'lookups': lookups,
                                            'attr': list(inp.attr_present), 'record': record[:6],
                                            'stopped': r['stopped']})
        if ok(r) and not monster and client_actions:
            # negative control: two-handed swords as one-handed
            if 0xae6 <= weapon[0] < 0x10e6 and inp.two_handed and inp.attr_present[0] and (inp.class_byte & 15) != 9:
                wrong = 0x71 + inp.counter % 2
                negatives['player_attack_two_handed_ignored'] += client_actions[0] != wrong


def family_in_range(m, lib, rng, cases, report, negatives):
    tramp = m.trampoline(IN_RANGE, 4, store_int=True)
    for n in range(cases):
        tx, ty = rng.randrange(0, 256), rng.randrange(0, 256)
        x, y = tx + rng.randrange(-9, 10), ty + rng.randrange(-9, 10)
        if n % 10 == 0:
            x, y = rng.randrange(-2**31, 2**31), rng.randrange(-2**31, 2**31)
        rang = rng.choice([1.0, 2.0, 6.0, 7.0, 8.0, 1.4142135, 1.4142137, float('nan'), 0.0, -1.0, rfloat(rng, 0.1, 10)])
        rang = f32(rang)
        c = am.undefined_region('character', CHAR, 0x200)
        c.define(CHAR+0x180, struct.pack('<ii', tx, ty))

        def sqrt(mm):
            v = struct.unpack('<d', mm.uc.mem_read(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP)+4, 8))[0]
            return mm.x87_return(math.sqrt(v) if v >= 0 else float('nan'), double=True)
        r = m.execute(tramp, [CHAR, x, y, bits(rang)], [c, out_region()], {CRT_SQRT: sqrt})
        client = r['regions']['out'][0] if ok(r) else None
        mine = lib.mu_in_range(tx, ty, x, y, rang)
        equal = ok(r) and client == mine
        report.add('in_range', equal, {'case': n, 'tile': [tx, ty], 'target': [x, y], 'range': rang, 'client': client,
                                       'c': mine, 'stopped': r['stopped']})
        if ok(r):
            negatives['in_range_chebyshev'] += client != int(max(abs(tx-x), abs(ty-y)) <= rang)


def family_shock_allowed(m, lib, rng, cases, report, negatives):
    tramp = m.trampoline(SHOCK_ALLOWED, 2, store_int=True)
    for n in range(cases):
        cls = rng.choice([0x2fb, 0x2fb, 0, 1, 2, 3, rng.randrange(-5, 1000)])
        action = rng.choice(list(range(-2, 12)) + [rng.randrange(-2**31, 2**31)])
        r = m.execute(tramp, [cls, action], [out_region()], {})
        client = r['regions']['out'][0] if ok(r) else None
        mine = lib.mu_monster_shock_allowed(cls, action)
        equal = ok(r) and client == mine
        report.add('shock_allowed', equal, {'class': cls, 'action': action, 'client': client, 'c': mine,
                                            'stopped': r['stopped']})
        if ok(r):
            negatives['shock_always'] += client != 1


def family_dead_fade(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        dead = rng.choice([0, 1, 2, 15, 40, 255])
        model = rng.choice([0x7a5, 0x7a6, 0x7c5, 0x7e5, 0x940, 0x819, 0x7b0])
        world = rng.choice([0, 7, 7, 3])
        timer = rng.choice([0.0, 0.98, 0.99, 1.0, 1.5, 1.98, 1.99, 1.995, 2.5, float('nan'), rfloat(rng, 0.1, 3.0)])
        alpha = rng.choice([1.0, 0.5, 0.0, rfloat(rng, 0.1, 1.0)])
        z = rfloat(rng, 0.1, 500.0)
        o6c = rng.choice([0, 99, 100, 101])
        hero = rng.random() < 0.2
        pred = rng.random() < 0.3      # world predicate 0x009dacb8 (skips the list removal)
        st = FadeState(timer=f32(timer), alpha=f32(alpha), z=z, model=model, world=world, o6c=o6c, is_hero=hero)
        c = am.undefined_region('character', CHAR, 0x3400)
        c.define(CHAR+0x23, bytes([dead]))
        c.define(CHAR+0x1a8, struct.pack('<f', st.timer))
        c.define(CHAR+0x2a, b'\x00')
        c.define(OBJ+0x5c, struct.pack('<i', model))
        c.define(OBJ+0x6c, struct.pack('<i', o6c))
        c.define(OBJ+0xdc, struct.pack('<f', st.alpha))
        c.define(OBJ+0x158, struct.pack('<3f', 0.0, 0.0, z))
        c.define(OBJ+0x8, b'\x01')
        regions = [c, am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
                   am.defined_region('hero-ptr', HERO_PTR, struct.pack('<I', CHAR if hero else 0x25000000),
                                     writable=False)]
        record = []

        def rec(name, value=0, cleanup=0, argc=0):
            def stub(mm):
                record.append((name,) + tuple(mm.argument(i) for i in range(argc)))
                return value, cleanup
            return stub
        stubs = {0x0137d58f: rec('137d58f'), 0x0129f4a5: rec('effects_off', cleanup=4),
                 0x009dacb8: lambda mm: 0x9900 | (1 if pred else 0), 0x009dacec: lambda mm: 0x9900,
                 0x0095f6db: lambda mm: 0x28000000, 0x009a176b: rec('list_remove', cleanup=4),
                 0x0098294d: rec('free_slot', argc=1), 0x0137aafe: rec('after_fade', argc=3),
                 0x013a5690: rec('13a5690'), 0x00ac3bf7: lambda mm: 0x28100000,
                 0x0095f998: lambda mm: 0x28200000, 0x00bb1c32: lambda mm: (0, 4),
                 0x009b0bc1: lambda mm: 1, 0x01989721: lambda mm: 7, 0x013c07f4: rec('particle')}
        r = m.execute(DEAD_FADE, [CHAR, OBJ, 0x29000000], regions, stubs)
        lib.mu_dead_fade(dead, ctypes.byref(st))
        equal = ok(r)
        if equal:
            raw = r['regions']['character']
            t = struct.unpack('<f', raw[0x1a8:0x1ac])[0]
            a = struct.unpack('<f', raw[0x3254+0xdc:0x3254+0xe0])[0]
            zz = struct.unpack('<f', raw[0x3254+0x160:0x3254+0x164])[0]
            live = raw[0x3254+8]
            removed = live == 0
            equal = same(t, st.timer) and same(a, st.alpha) and same(zz, st.z) and removed == bool(st.removed)
            equal = equal and (sum(1 for x in record if x[0] == 'list_remove') == (1 if st.removed and not pred else 0))
        report.add('dead_fade', equal, {'case': n, 'dead': dead, 'model': hex(model), 'timer': timer,
                                        'stopped': r['stopped']})
        if ok(r) and dead and not math.isnan(timer):
            t = struct.unpack('<f', r['regions']['character'][0x1a8:0x1ac])[0]
            negatives['dead_fade_step_005'] += not same(t, f32(f32(timer) + f32(0.05)))


FAMILIES = [('damage_color', family_damage_color), ('damage_scale', family_damage_scale),
            ('create_point', family_create_point), ('move_points', family_move_points),
            ('render_points', family_render_points), ('render_number', family_render_number),
            ('show_damage', family_show_damage), ('attack_speed', family_attack_speed),
            ('player_attack', family_player_attack), ('in_range', family_in_range),
            ('shock_allowed', family_shock_allowed), ('dead_fade', family_dead_fade)]
HEAVY = {'create_point', 'move_points', 'render_points', 'show_damage'}   # 180 KB pool per case


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
    parser.add_argument('--data', default=str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--heavy-cases', type=int, default=None, help='cases of the pool families (default cases/3)')
    parser.add_argument('--only', action='append')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = Combat(text, data)
    bodies = {name: {'start': hex(a), 'end': hex(b),
                     'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    report = Report()
    negatives = {k: 0 for k in ['damage_color_no_hero_red', 'damage_scale_crit_15', 'create_point_floor_without_140',
                                'move_points_hit_shrinks', 'render_points_alpha_gravity', 'render_number_no_diagonal',
                                'show_damage_flag8_single', 'attack_speed_no_cap', 'player_attack_two_handed_ignored',
                                'in_range_chebyshev', 'shock_always', 'dead_fade_step_005']}
    timing = {}
    for name, family in FAMILIES:
        if args.only and name not in args.only:
            continue
        rng = random.Random(f'{args.seed}-{name}')
        cases = args.cases if name not in HEAVY else (args.heavy_cases or max(1, args.cases//3))
        start = time.time()
        family(m, lib, rng, cases, report, negatives)
        timing[name] = round(time.time()-start, 2)
    result = {'nan_pairs_equal': NAN_COUNT[0], 'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'bodies': bodies,
              'families': report.families, 'negative_controls': negatives, 'seconds': timing}
    all_equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result['all_equal'] = all_equal
    summary = {k: f"{v['equal']}/{v['cases']}" for k, v in report.families.items()}
    print(json.dumps({'summary': summary, 'negative_controls': negatives, 'seconds': timing, 'all_equal': all_equal},
                     indent=1))
    for k, v in report.families.items():
        if v['first_failures']:
            print(k, json.dumps(v['first_failures'][:3], default=str))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, default=str))
    return 0 if all_equal else 1


if __name__ == '__main__':
    sys.exit(main())
