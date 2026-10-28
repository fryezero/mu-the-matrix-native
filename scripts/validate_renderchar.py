#!/usr/bin/env python3
"""Compare the reconstructed world render decisions with the client (NATIVE-RENDERCHAR-001).

Sections:

* items: RenderObjDraw 0x0176ce74 is executed on random cases; the mesh-draw
  calls it makes (through the default-buffer wrappers 0x00966def/0x00966e4a,
  recorded with the model fields at each call) must equal
  reconstructed/renderchar mu_rc_item_draws bit for bit. A sweep over every
  item type classifies the types whose stream differs in any of a fixed set of
  configurations as type-specific (--emit-special writes the generated table).

The client routines run as client code; only the services listed in
SERVICES are replaced (docs/research/client-renderchar.md). Needs the pinned
restored text and second section, the captured trig dispatch flag and the
math feature word (as scripts/validate_meshdraw.py).
"""
import argparse
import ctypes
import hashlib
import json
import random
import struct
import sys
import time as clock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import renderchar_machine as rmach  # noqa: E402
from renderchar_machine import f2u, u2f  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'reconstructed' / 'renderchar' / ('librenderchar.dylib' if sys.platform == 'darwin' else 'librenderchar.so')

# Bodies executed (pinned; the validator refuses other text).
ROUTINES = {
    'RenderCharacter': (0x01363260, 0x01378d58),
    'BackCarry': (0x0139db9a, 0x0139f2e8),
    'RenderPartObject': (0x017e63f4, 0x017e79ac),
    'RenderObjDraw': (0x0176ce74, 0x017e6312),
    'RenderPartObjectBody': (0x016e036c, 0x0176cb3b),
    'RenderPartObjectBodyColor': (0x016dec15, 0x016e036c),
    'RenderPartObjectBodyColor2': (0x016dc148, 0x016dec15),
    'PartObjectColor': (0x016db5eb, 0x016dba54),
    'PartObjectColor2': (0x016dba54, 0x016dc148),
    'AncientColor': (0x01806042, 0x01806350),
    'RenderLinkItem': (0x012bd910, 0x013575cb),
}

# Case layout (our choice).
MODEL, OBJ, LIGHT, CONT, BONES, HERO, OPTS = 0x20000000, 0x21000000, 0x21001000, 0x22000000, 0x23000000, 0x24000000, 0x25000000
ITEMREC, NODE, ENCH, CHAR, ACTIONS = 0x26000000, 0x27000000, 0x29000000, 0x2a000000, 0x2b000000
PLAYER_MODEL = MODEL + 0x1000
EXTERNAL_PAGE = 0x10b22000
GL_PAGES = (0x7a8a0000, 0x30000)   # OPENGL32 import targets of the captured data section
GL_SLOTS = {0x1a7c750: ('glBegin', 1), 0x1a7c760: ('glEnd', 0), 0x1a7c774: ('glTexCoord2f', 2),
            0x1a7c76c: ('glColor3f', 3), 0x1a7c770: ('glColor3fv', 1), 0x1a7c754: ('glColor4f', 4),
            0x1a7c778: ('glVertex3fv', 1), 0x1a7c75c: ('glEnable', 1), 0x1a7c758: ('glDisable', 1),
            0x1a7c748: ('glBlendFunc', 2), 0x1a7c740: ('glDepthMask', 1), 0x1a7c77c: ('glBindTexture', 2),
            0x1a7c718: ('glPushMatrix', 0), 0x1a7c72c: ('glPopMatrix', 0), 0x1a7c768: ('glVertex3f', 3)}

# Engine services replaced by recorders, with stdcall/thiscall cleanup bytes.
SERVICES = {
    0x00966cc4: 'model container getter (returns the case container)',
    0x00eaa8cf: 'model lookup (case models only)',
    0x00966ea5: 'transform, default buffers (recorded)',
    0x00966def: 'mesh-draw body, default buffers (recorded with model fields)',
    0x00966e4a: 'mesh draw, default buffers (recorded with model fields)',
    0x012bb35a: 'mesh-draw body (recorded)',
    0x012b8d1d: 'mesh draw (recorded)',
    0x012bc07a: 'body shadow (recorded)',
    0x00cd4ea8: 'item table singleton (returns its static address)',
    0x00cd5d29: 'item table find (case records)',
    0x00cd6017: 'item kind B predicate (+0x251 of the case record)',
    0x00cd5fac: 'item kind A predicate (+0x250)',
    0x00cd5f41: 'item type predicate (+0x252)',
    0x01989721: 'rand (returns 0)',
    0x01692eb7: 'create effect (recorded)', 0x0168fafd: 'create particle (recorded)',
    0x0150e746: 'bone-linked effect (recorded)',
    0x010ffd7a: 'EnchantEffect colour lookup (case colour)',
    0x010ffd25: 'EnchantEffect mesh list lookup (empty)',
    0x010ffddb: 'EnchantEffect colour lookup by mesh (case colour)',
    0x0185baac: 'LoadBitmap (recorded)', 0x018202b4: 'AccessModel (recorded)', 0x0181fbe9: 'OpenTexture (recorded)',
    0x10b223b0: 'external module (outside the restored text, recorded)',
    0x10b22740: 'external module (outside the restored text, recorded)',
    0x00db73f3: 'option singleton constructor (zero object)',
}


def sgn(value):
    return value - (1 << 32) if value & 0x80000000 else value


class World:
    """One client state: models, object, item records, globals."""

    def __init__(self, text, data, flag, feature):
        self.m = m = rmach.RenderMachine(text, data)
        self.calls = m.calls
        m.map(MODEL, 0x10000)
        m.map(OBJ, 0x1000)
        m.map(LIGHT, 0x1000)
        m.map(CONT, 0x1000)
        m.map(BONES, 0x10000)
        m.map(HERO, 0x4000)
        m.map(OPTS, 0x1000)
        m.map(ITEMREC, 0x10000)
        m.map(NODE, 0x1000)
        m.map(ENCH, 0x1000)
        m.map(CHAR, 0x4000)
        m.map(ACTIONS, 0x2000)
        m.map(EXTERNAL_PAGE, 0x1000, b'\xcc' * 0x1000, executable=True)
        m.map(GL_PAGES[0], GL_PAGES[1], b'\xcc' * GL_PAGES[1], executable=True)
        # Declared engine globals.
        m.ensure(0x0bdd1cc8, 4)
        m.write(0x0bdd1cc8, flag)                      # trig dispatch flag (captured)
        m.ensure(0x01cf6618, 4)
        m.write(0x01cf6618, feature)                   # math feature word (captured)
        m.ensure(0x0a39d754, 4)
        m.w32(0x0a39d754, HERO)                        # hero character pointer
        m.ensure(0x01d22c7c, 4)
        m.w32(0x01d22c7c, OPTS)                        # graphics option object
        m.ensure(0x06fce370, 4)                        # world time
        m.ensure(0x01ec8db0, 0x20)                     # item render registry: empty std::map at +8
        for k in range(3):
            m.w32(NODE + 4 * k, NODE)
        m.write(NODE + 0xc, b'\1\1')
        m.w32(0x01ec8db0 + 8, NODE)
        m.w32(0x01ec8db0 + 0xc, 0)
        self.models = {}
        self.records = {}
        self.install()

    def add_model(self, model_type, address, bones=8, meshes=1, actions=1, actions_at=0):
        rec = bytearray(0xd0)
        struct.pack_into('<hhh', rec, 0x22, bones, meshes, actions)
        struct.pack_into('<I', rec, 0x30, actions_at)
        self.m.write(address, rec)
        self.models[model_type] = address

    def add_record(self, index, kind_a, kind_b, kind):
        address = ITEMREC + 0x300 * len(self.records)
        self.m.write(address + 0x250, bytes([kind_a, kind_b, kind]))
        self.records[index] = address

    def install(self):
        m, rec = self.m, self.calls

        def snapshot(model):
            raw = m.read(model, 0xd0)
            return {'body_light': struct.unpack_from('<3I', raw, 0x54), 'level_field': struct.unpack_from('<i', raw, 0x40)[0],
                    'shade': struct.unpack_from('<3I', raw, 0x44), 'flag_ca': raw[0xca]}

        m.stub(0x00966cc4, lambda m: CONT, 0)
        m.stub(0x00eaa8cf, lambda m: self.models.get(m.arg(0), 0), 4)

        def transform(m):
            rec.append(('transform', m.ecx(), [m.arg(i) for i in range(9)]))
            return 0
        m.stub(0x00966ea5, transform, 0x24)

        def body(m):
            rec.append(('BODY', m.ecx(), [m.arg(i) for i in range(8)], snapshot(m.ecx())))
            return 0

        def mesh(m):
            rec.append(('MESH', m.ecx(), [m.arg(i) for i in range(8)], snapshot(m.ecx())))
            return 0
        m.stub(0x00966def, body, 0x20)
        m.stub(0x00966e4a, mesh, 0x20)
        for address, name in ((0x012bb35a, 'raw-body'), (0x012b8d1d, 'raw-mesh')):
            m.stub(address, (lambda n: (lambda m: rec.append((n, m.ecx(), [m.arg(i) for i in range(11)])) or 0))(name), 0x2c)
        m.stub(0x012bc07a, lambda m: rec.append(('shadow', m.ecx(), [m.arg(i) for i in range(5)])) or 0, 0x14)
        m.stub(0x00cd4ea8, lambda m: 0x01ec7a60, 0)
        m.stub(0x00cd5d29, lambda m: self.records.get(m.arg(0), 0), 4)

        def kind(offset):
            def predicate(m):
                address = self.records.get(m.arg(0))
                return int(address is not None and m.arg(0) <= 0x2c00 and m.read(address + offset, 1)[0] == (m.arg(1) & 0xff))
            return predicate
        m.stub(0x00cd6017, kind(0x251), 8)
        m.stub(0x00cd5fac, kind(0x250), 8)
        m.stub(0x00cd5f41, kind(0x252), 8)
        m.stub(0x01989721, lambda m: 0, 0)
        for address in (0x01692eb7, 0x0168fafd, 0x0150e746):
            m.stub(address, (lambda a: (lambda m: rec.append(('effect', a, [m.arg(i) for i in range(4)])) or 0))(address), 0)
        m.stub(0x010ffd7a, lambda m: ENCH, 4)
        m.w32(ENCH + 0x100, 0)
        m.w32(ENCH + 0x104, 0)
        m.stub(0x010ffd25, lambda m: ENCH + 0x100, 4)
        m.stub(0x010ffddb, lambda m: ENCH, 8)
        m.stub(0x0185baac, lambda m: rec.append(('load-bitmap', m.arg(1))) or 1, 0)
        m.stub(0x018202b4, lambda m: rec.append(('access-model', m.arg(0))) or 0, 0)
        m.stub(0x0181fbe9, lambda m: rec.append(('open-texture', m.arg(0))) or 0, 0)
        for address in (0x10b223b0, 0x10b22740):
            m.stub(address, (lambda a: (lambda m: rec.append(('external', a, m.arg(0))) or 0))(address), 0)
        m.stub(0x00db73f3, lambda m: rec.append(('zero-ctor', 0xdb73f3)) or m.ecx(), 0)
        # bitmap lookups (std::map searches, modelled as misses returning a zeroed record)
        m.ensure(0x01ec3030, 0x400)
        m.stub(0x00c97c2d, lambda m: rec.append(('bitmap', m.arg(0))) or 0x01ec3030, 4)
        m.stub(0x00ebbec8, lambda m: rec.append(('bitmap', m.arg(0))) or 0x01ec3030, 4)
        for slot, (name, count) in GL_SLOTS.items():
            target = m.r32(slot)
            m.stub(target, (lambda n, k: (lambda m: rec.append(('gl', n, [m.arg(i) for i in range(k)])) or 0))(name, count), 4 * count)


# ---------------------------------------------------------------- link item
ROOT_MATRIX = 0x078965ac
BACK_KINDS = (0, 0x0b, 0x4b, 0x54, 0x59, 0x5a, 0x72, 0x73, 0x7b)


def character_record(cls=1, action=1, light=(0.8, 0.7, 0.6), position=(100.0, 200.0, 50.0), safe=0):
    c = bytearray(0x3700)
    c[4] = safe                                     # +4 safe-zone flag (0x0095fb27)
    c[0x12] = cls
    struct.pack_into('<h', c, 0x3c, -1)             # no pet/emblem
    struct.pack_into('<3f', c, 0x1b8, *light)
    for slot in range(6):
        struct.pack_into('<h', c, 0x1c4 + slot * 0x3fc, -1)
    for base in (0x19ac, 0x19ac + 0x3fc, 0x21a4, 0x25a0, 0x299c, 0x2d98):
        struct.pack_into('<h', c, base, -1)
    o = 0x3254
    struct.pack_into('<i', c, o + 0x5c, 0xa91)
    struct.pack_into('<f', c, o + 0xa0, 0.9)
    struct.pack_into('<f', c, o + 0xdc, 1.0)
    struct.pack_into('<H', c, o + 0x2a, action)
    c[o + 0xd] = 1
    c[o + 0xe] = 1
    c[o + 0x3b] = 1
    struct.pack_into('<3f', c, o + 0x158, *position)
    struct.pack_into('<I', c, o + 0x318, BONES)
    return c


def link_world(world_args, item_type, kind_b=0, bones=None):
    w = World(*world_args)
    m = w.m
    w.add_model(item_type, MODEL, bones=4, meshes=1, actions=1)
    w.add_model(0xa91, PLAYER_MODEL, bones=60, meshes=0, actions=390)
    if kind_b:
        w.add_record(item_type - 0xae6, 0, kind_b, 0)
    m.write(CHAR, character_record())
    if bones is None:
        bones = b''.join(struct.pack('<12f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0) for _ in range(200))
    m.write(BONES, bones)
    m.ensure(ROOT_MATRIX, 0x30)
    rec = w.calls

    def rotpos(m):
        vec = m.arg(1)
        rec.append(('rotpos', m.ecx(), m.arg(0), [m.r32(vec + 4 * k) for k in range(3)]))
        for k in range(3):
            m.wf(m.arg(2) + 4 * k, (1.0, 2.0, 3.0)[k])
        return 0
    m.stub(0x012b7019, rotpos, 0xc)

    def pose(m):
        model = m.ecx()
        rec.append(('pose', model, [m.arg(i) for i in range(8)], [m.r32(ROOT_MATRIX + 4 * k) for k in range(12)],
                    [m.r32(model + 0x78 + 4 * k) for k in range(3)], [m.r32(m.arg(4) + 4 * k) for k in range(3)]))
        return 0
    m.stub(0x012b5064, pose, 0x20)
    m.stub(0x012b4dd3, lambda m: rec.append(('tick', m.ecx(), m.arg(0), m.arg(3))) or 0, 0x18)
    m.stub(0x0176ce74, lambda m: rec.append(('objdraw', [m.arg(i) for i in range(13)])) or 0, 0)
    return w


def run_link(world_args, item_type, kind_b=0, right=1, link=1, xyz=(0.0, 0.0, 15.0), link_bone=47, bones=None,
             level=0, option=0):
    w = link_world(world_args, item_type, kind_b, bones)
    part = CHAR + 0x19ac
    w.m.write(part, struct.pack('<hBBBB', item_type, level, option, 0, link_bone))
    result = w.m.run(0x012bd910, [f2u(xyz[0]), f2u(xyz[1]), f2u(xyz[2]), CHAR, part, item_type, level, option, link, 1, 0,
                                  right])
    return result, w


TEST_BONE = (0.36, -0.48, 0.8, 11.0, 0.8, 0.6, 0.0, -7.0, -0.48, 0.64, 0.6, 3.0)


def extract_back(world_args, types, lib):
    """Local back-carry matrix per (type, kind B, right hand), and how the client
    applies it: 0 = concat under the owner bone (0x00cff83e), 1 = absolute (the
    owner bone is not used). Extracted with an identity owner bone, classified
    with a second, general owner bone."""
    identity = b''.join(struct.pack('<12f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0) for _ in range(200))
    tested = struct.pack('<12f', *TEST_BONE) * 200     # every bone: absolute entries are bone-independent
    bone_bits = (ctypes.c_uint32 * 12)(*[f2u(x) for x in TEST_BONE])
    table = {}
    for item_type in types:
        for kind_b in BACK_KINDS:
            for right in (0, 1):
                roots = []
                for bones in (identity, tested):
                    result, w = run_link(world_args, item_type, kind_b, right, bones=bones)
                    poses = [c for c in w.calls if c[0] == 'pose']
                    rot = any(c[0] == 'rotpos' for c in w.calls)
                    roots.append(tuple(poses[0][3]) if result['ok'] and len(poses) == 1 and not rot else None)
                if roots[0] is None or roots[1] is None:
                    table[(item_type, kind_b, right)] = None
                    continue
                local = (ctypes.c_uint32 * 12)(*roots[0])
                composed = (ctypes.c_uint32 * 12)()
                lib.mu_pose_concat(bone_bits, local, composed)
                if roots[1] == tuple(composed):
                    table[(item_type, kind_b, right)] = (0,) + roots[0]
                elif roots[1] == roots[0]:
                    table[(item_type, kind_b, right)] = (1,) + roots[0]
                else:
                    table[(item_type, kind_b, right)] = None
    return table


# ---------------------------------------------------------------- C side
F3 = ctypes.c_float * 3


class CDraw(ctypes.Structure):
    _fields_ = [('entry', ctypes.c_int32), ('mesh', ctypes.c_int32), ('flags', ctypes.c_uint32), ('alpha', ctypes.c_float),
                ('blend_mesh', ctypes.c_int32), ('blend_light', ctypes.c_float), ('u', ctypes.c_float), ('v', ctypes.c_float),
                ('hidden', ctypes.c_int32), ('texture', ctypes.c_int32), ('body_light', F3), ('level_field', ctypes.c_int32),
                ('shade', F3), ('flag_ca', ctypes.c_uint8)]


class CModel(ctypes.Structure):
    _fields_ = [('body_light', F3), ('level_field', ctypes.c_int32), ('shade', F3), ('flag_ca', ctypes.c_uint8),
                ('hide_skin', ctypes.c_uint8)]


class CItem(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('item_level', ctypes.c_int32), ('option1', ctypes.c_int32),
                ('ext_option', ctypes.c_int32), ('select', ctypes.c_int32), ('render_type', ctypes.c_uint32),
                ('a10', ctypes.c_int32), ('a11', ctypes.c_int32), ('a12', ctypes.c_int32), ('a13', ctypes.c_int32),
                ('alpha', ctypes.c_float), ('light', F3), ('object_alpha', ctypes.c_float), ('blend_mesh', ctypes.c_int32),
                ('blend_light', ctypes.c_float), ('u', ctypes.c_float), ('v', ctypes.c_float), ('buff_39', ctypes.c_uint8),
                ('buff_12', ctypes.c_uint8), ('buff_41', ctypes.c_uint8), ('object_shadow', ctypes.c_uint8),
                ('time', ctypes.c_float), ('quality', ctypes.c_int32), ('has_record', ctypes.c_int32),
                ('kind_a', ctypes.c_uint8), ('kind_b', ctypes.c_uint8), ('item_kind', ctypes.c_uint8), ('enchant', F3)]


def emit_back_table(path, table):
    matrices = sorted({v for v in table.values() if v is not None})
    ids = {m: i for i, m in enumerate(matrices)}
    lines = ['/* Generated by scripts/validate_renderchar.py --emit-back: the local back-carry matrix',
             ' * RenderLinkItem 0x012bd910 uses in link mode, extracted by executing it per',
             ' * (type, kind B, right hand) with an identity and a general owner bone (EXTRACTED).',
             ' * Column 0: 0 = composed under the owner bone (0x00cff83e), 1 = absolute. */',
             f'static const uint32_t mu_rc_back_matrices[{len(matrices)}][13] = {{']
    for m in matrices:
        lines.append('    {' + ', '.join(f'0x{x:08x}' for x in m) + '},')
    lines.append('};')
    lines.append('/* {first type, last type, kind B, right hand, matrix} ; -1 = another path */')
    rows = []
    for (t, k, r), v in sorted(table.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        mid = ids[v] if v is not None else -1
        if rows and rows[-1][2] == k and rows[-1][3] == r and rows[-1][4] == mid and rows[-1][1] == t - 1:
            rows[-1][1] = t
        else:
            rows.append([t, t, k, r, mid])
    lines.append(f'static const int32_t mu_rc_back_rows[{len(rows)}][5] = {{')
    for row in rows:
        lines.append('    {0x%04x, 0x%04x, 0x%02x, %d, %d},' % tuple(row))
    lines.append('};')
    path.write_text('\n'.join(lines) + '\n')
    return len(matrices), len(rows)


def back_section(world_args, lib, args):
    if args.back_types == 'weapons':
        types = list(range(0xae6, 0xae6 + 7 * 512)) + list(range(0xa99, 0xaa2))   # + the +15 attachments
    else:
        types = [0xae6 + g * 512 + i for g in range(7) for i in range(0, 512, 37)]
    table = extract_back(world_args, types, lib)
    summary = {'types': len(types), 'entries': len(table), 'plain': sum(v is not None for v in table.values()),
               'absolute': sum(1 for v in table.values() if v is not None and v[0] == 1)}
    if args.emit_back:
        summary['matrices'], summary['rows'] = emit_back_table(args.emit_back, table)
    rng = random.Random(args.seed + 1)
    keys = [k for k, v in table.items() if v is not None]
    matches, failures = 0, []
    out = (ctypes.c_uint32 * 12)()
    for index in range(args.back_checks):
        key = rng.choice(keys)
        bone = [rng.uniform(-1, 1) for _ in range(9)]
        bone = bone[0:3] + [rng.uniform(-50, 50)] + bone[3:6] + [rng.uniform(-50, 50)] + bone[6:9] + [rng.uniform(-50, 50)]
        bones = struct.pack('<12f', *bone) * 200
        result, w = run_link(world_args, key[0], key[1], key[2], bones=bones)
        poses = [c for c in w.calls if c[0] == 'pose']
        client = tuple(poses[0][3]) if result['ok'] and len(poses) == 1 else None
        bone_bits = (ctypes.c_uint32 * 12)(*[f2u(x) for x in bone])
        status = lib.mu_rc_back_root(bone_bits, key[0], key[1], key[2], out)
        mine = tuple(out) if status == 1 else None
        if client is not None and client == mine:
            matches += 1
        elif len(failures) < 5:
            failures.append({'key': [hex(key[0]), hex(key[1]), key[2]], 'client': client, 'c': mine})
    summary.update({'checks': args.back_checks, 'matches': matches, 'failures': failures,
                    'ok': matches == args.back_checks})
    return summary


def kind_section(world_args, lib, args):
    """Every value of the record fields kind A/kind B/type on sampled generic types: the
    values that change the executed stream must be exactly those the library refuses or
    models (kind A 6, kind B 0x26/0x5b)."""
    rng = random.Random(args.seed + 2)
    generic = [t for t in range(0xae6, 0xae6 + 16 * 512) if not lib.mu_rc_item_special(t)]
    types = []
    for group in range(16):
        members = [t for t in generic if (t - 0xae6) // 512 == group]
        types += rng.sample(members, min(args.kind_types, len(members)))
    configs = [CLASSIFY[1], CLASSIFY[7], CLASSIFY[5]]
    mismatched, refused = {0: [], 1: [], 2: []}, {0: [], 1: [], 2: []}
    for field in (0, 1, 2):
        for value in range(256):
            for item_type in types:
                verdict = None
                for config in configs:
                    case = classify_case(item_type, config)
                    record = [0, 0, 0]
                    record[field] = value
                    case['record'] = tuple(record)
                    status, cstream = c_stream(lib, case)
                    if status == 2:
                        verdict = 'refused'
                        break
                    result, stream, _, _ = client_stream(world_args, case)
                    if not result['ok'] or stream != cstream:
                        verdict = 'mismatch'
                        break
                if verdict == 'refused':
                    refused[field].append(value)
                    break
                if verdict == 'mismatch':
                    mismatched[field].append(value)
                    break
    names = ('kind_a', 'kind_b', 'type')
    return {'types': len(types), 'refused': {names[f]: [hex(v) for v in refused[f]] for f in refused},
            'mismatched': {names[f]: [hex(v) for v in mismatched[f]] for f in mismatched},
            'ok': not any(mismatched.values())}


# ---------------------------------------------------------------- character
# Recorded and skipped: name/effect managers, the character effect emitters 0x01362f24/0x01363098
# (direct GL sprites, not mesh draws), sound 0x00a6ac96, and the helper/pet pass 0x01378d9c.
CHAR_SKIPS = {0x00ea3692: 4, 0x00ea3cae: 0xc, 0x00a0b4ba: 0, 0x0129f671: 4, 0x01362f24: 0, 0x01363098: 0,
              0x00a6ac96: 0, 0x01378d9c: 0}


class CSlot(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('level', ctypes.c_int8), ('option', ctypes.c_uint8), ('ext', ctypes.c_uint8),
                ('has_record', ctypes.c_int32), ('kind_b', ctypes.c_uint8), ('action', ctypes.c_uint8),
                ('frame', ctypes.c_float), ('prior_frame', ctypes.c_float), ('speed', ctypes.c_float)]


class CCharacter(ctypes.Structure):
    _fields_ = [('class_byte', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8), ('action', ctypes.c_uint16),
                ('frame', ctypes.c_float), ('alpha', ctypes.c_float), ('translate', ctypes.c_int32),
                ('select', ctypes.c_int32), ('parts', CSlot * 6), ('weapons', CSlot * 2), ('wing', CSlot),
                ('player_speed', ctypes.c_float * 0x186)]


class CCall(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int32), ('slot', ctypes.c_int32), ('type', ctypes.c_int32),
                ('item_level', ctypes.c_int32), ('option', ctypes.c_int32), ('ext', ctypes.c_int32),
                ('render_type', ctypes.c_int32), ('translate', ctypes.c_int32), ('select', ctypes.c_int32),
                ('xyz', ctypes.c_float * 3), ('link', ctypes.c_int32), ('right_hand', ctypes.c_int32),
                ('link_bone', ctypes.c_int32), ('part_action', ctypes.c_int32), ('part_speed', ctypes.c_float),
                ('part_frame', ctypes.c_float), ('part_prior_frame', ctypes.c_float)]


SLOT_BASES = [0x1c4 + k * 0x3fc for k in range(6)] + [0x19ac, 0x19ac + 0x3fc, 0x21a4]


def character_client(world_args, ch):
    w = World(*world_args)
    m = w.m
    w.add_model(0xa91, PLAYER_MODEL, bones=60, meshes=0, actions=390, actions_at=ACTIONS)
    w.add_model(0xa92, PLAYER_MODEL + 0x100, bones=60, meshes=0, actions=390, actions_at=ACTIONS)
    for k in range(0x186):
        m.write(ACTIONS + 16 * k, struct.pack('<BxxxI', 0, ch['speeds'][k]))
    record = character_record(cls=ch['class'], action=ch['action'], safe=ch['safe'])
    struct.pack_into('<I', record, 0x3254 + 0xd0, ch['frame'])
    struct.pack_into('<I', record, 0x3254 + 0xdc, ch['alpha'])
    model_at = MODEL + 0x200
    for index, slot in enumerate(ch['slots']):
        if slot is None:
            continue
        base = SLOT_BASES[index]
        bone = 33 if index == 6 else 42 if index == 7 else 47 if index == 8 else 0
        struct.pack_into('<hbBBB', record, base, slot['type'], slot['level'], slot['option'], slot['ext'], bone)
        struct.pack_into('<III', record, base + 0xc, slot['frame'], slot['prior'], slot['speed'])
        record[base + 6] = slot['action']
        if slot['type'] not in w.models:
            w.add_model(slot['type'], model_at, bones=4, meshes=1, actions=1)
            model_at += 0x100
        if slot['kind'] is not None and slot['type'] - 0xae6 not in w.records:
            w.add_record(slot['type'] - 0xae6, 0, slot['kind'], 0)
    m.write(CHAR, record)
    m.write(BONES, b''.join(struct.pack('<12f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0) for _ in range(200)))
    rec = w.calls
    o = CHAR + 0x3254
    m.stub(0x00d33153, lambda m: ACTIONS + 16 * m.arg(0), 4)
    m.stub(0x012b5064, lambda m: rec.append(('pose', m.ecx())) or 0, 0x20)
    m.stub(0x012b4dd3, lambda m: rec.append(('tick', m.ecx())) or 0, 0x18)
    for address, cleanup in CHAR_SKIPS.items():
        m.stub(address, (lambda a: (lambda m: rec.append(('skip', a)) or 0))(address), cleanup)

    def rpo(m):
        a = [m.arg(i) for i in range(16)]
        rec.append(('RPO', a, m.read(o + 4, 1)[0]))
        return 0
    m.stub(0x017e63f4, rpo, 0)

    def link(m):
        a = [m.arg(i) for i in range(12)]
        part = a[4]
        rec.append(('LINK', a, m.read(part + 5, 2), m.r32(part + 0x14), m.r32(part + 0xc), m.r32(part + 0x10), m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP))))
        return 0
    m.stub(0x012bd910, link, 0)
    result = m.run(0x01363260, [CHAR, o, ch['select']])
    calls = []
    for c in rec:
        if c[0] == 'RPO':
            a = c[1]
            if c[2] == 1:
                calls.append(('SHADOW', a[1], a[10]))
            else:
                slot = (a[2] - CHAR - 0x1c4) // 0x3fc if a[2] else -1
                calls.append(('PART', slot, a[1], a[5], a[6], a[7], a[10], a[11], a[12]))
        elif c[0] == 'LINK':
            a = c[1]
            base = a[4] - CHAR
            index = SLOT_BASES.index(base) if base in SLOT_BASES else -9
            slot = index if index < 6 else index - 6 if index < 8 else 8
            calls.append(('LINK', slot, a[5], sgn(a[6]) if a[6] & 0x80000000 else a[6], a[7], tuple(a[0:3]), a[8],
                          a[9], a[10], a[11] & 0xff, c[2][0], c[2][1], c[3], c[4], c[5]))
    return result, calls, w


def character_c(lib, ch):
    cc = CCharacter(class_byte=ch['class'], safe_zone=ch['safe'], action=ch['action'], frame=u2f(ch['frame']),
                    alpha=u2f(ch['alpha']), translate=1, select=ch['select'])
    for k in range(0x186):
        cc.player_speed[k] = u2f(ch['speeds'][k])
    targets = [cc.parts[i] for i in range(6)] + [cc.weapons[0], cc.weapons[1], cc.wing]
    for target, slot in zip(targets, ch['slots']):
        if slot is None:
            target.type = -1
            continue
        target.type, target.level, target.option, target.ext = slot['type'], slot['level'], slot['option'], slot['ext']
        target.has_record = int(slot['kind'] is not None)
        target.kind_b = slot['kind'] or 0
        target.action = slot['action']
        target.frame, target.prior_frame, target.speed = u2f(slot['frame']), u2f(slot['prior']), u2f(slot['speed'])
    out = (CCall * 32)()
    count = ctypes.c_int32()
    status = lib.mu_rc_character_plan(ctypes.byref(cc), out, 32, ctypes.byref(count))
    calls = []
    for c in out[:min(count.value, 32)]:
        if c.kind == 1:
            calls.append(('SHADOW', c.type, c.translate))
        elif c.kind == 2:
            calls.append(('PART', c.slot, c.type, c.item_level & 0xffffffff, c.option, c.ext, c.translate, c.select,
                          c.render_type))
        else:
            calls.append(('LINK', c.slot, c.type, c.item_level, c.option, tuple(f2u(x) for x in c.xyz), c.link,
                          c.translate, 0, c.right_hand, c.link_bone, c.part_action, f2u(c.part_speed),
                          f2u(c.part_frame), f2u(c.part_prior_frame)))
    return status, calls


def random_character(rng, generic):
    def part_type(group):
        members = generic[group]
        return rng.choice(members) if members else -1
    def slot(item_type):
        return {'type': item_type, 'level': rng.randrange(-2, 16), 'option': rng.choice([0, 0, 1, rng.randrange(256)]),
                'ext': rng.choice([0, 0, rng.randrange(64)]), 'action': rng.randrange(4),
                'frame': f2u(rng.uniform(0, 5)), 'prior': f2u(rng.uniform(0, 5)), 'speed': f2u(rng.uniform(0, 1)),
                'kind': rng.choice([None, 0, 0, 0x59, 0x5a, 0x72, 0x54, 0x7b, 0x4b, 8, 9, 10, 0x0e])}
    slots = [None] * 9
    for index in range(1, 6):
        if rng.random() < 0.7:
            slots[index] = slot(part_type(6 + index))
    specials = [0x12fd, 0x1302, 0x12ff, 0x1305, 0x1100, 0x151e, 0xf30, 0xee8, 0xeeb, 0x14ec, 0xb09, 0xb55, 0xf05, 0x1315,
                0x150a, 0xf06, 0x12ed, 0x24eb, 0xb0f]
    for index in (6, 7):
        if rng.random() < 0.8:
            item_type = rng.choice(specials) if rng.random() < 0.25 else part_type(rng.randrange(7))
            slots[index] = slot(item_type)
    if rng.random() < 0.5:
        slots[8] = slot(0x22e6 + rng.randrange(7) if rng.random() < 0.8 else rng.choice([0x239a, 0x2301, 0x2386, 0x23ee]))
        slots[8]['kind'] = None
    return {'class': rng.choice([0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 14, 15, 0x11, 0x21, 0x22, 0x31]),
            'safe': rng.choice([0, 1]), 'select': 0,
            'action': rng.choice([1, 2, 3, 4, 15, 0x7e, 0x71, 0x72, 0x8f, 9, 0x1f, 0x5a, 0x150, rng.randrange(0x186)]),
            'frame': f2u(rng.uniform(0, 50)), 'alpha': f2u(rng.choice([1.0, 0.75, 0.5, 0.4, rng.uniform(0, 1)])),
            'speeds': [f2u(rng.uniform(0.05, 0.6)) for _ in range(0x186)], 'slots': slots}


def character_section(world_args, lib, args):
    rng = random.Random(args.seed + 3)
    generic = {g: [t for t in range(0xae6 + g * 512, 0xae6 + (g + 1) * 512) if not lib.mu_rc_item_special(t)]
               for g in range(16)}
    matches, refused, failures = 0, 0, []
    for index in range(args.characters):
        ch = random_character(rng, generic)
        status, mine = character_c(lib, ch)
        if status == 2:
            refused += 1
            continue
        result, client, w = character_client(world_args, ch)
        if result['ok'] and status == 0 and client == mine:
            matches += 1
        elif len(failures) < 10:
            failures.append({'character': {k: v for k, v in ch.items() if k != 'speeds'}, 'result': result,
                             'client': client, 'c': mine, 'backtrace': None if result['ok'] else w.m.backtrace()})
    compared = args.characters - refused
    return {'characters': args.characters, 'refused': refused, 'compared': compared, 'matches': matches,
            'failures': failures, 'ok': matches == compared}


# ---------------------------------------------------------------- character light (NATIVE-FIDELITY-001)
HERO_ATTR = 0x2c000000     # Hero character attribute block [0x01d1df1c] (case layout)
LIGHT_BLOCK_START, LIGHT_BLOCK_END = 0x01367530, 0x01367d85


class CLightIn(ctypes.Structure):
    _fields_ = [('scene_state', ctypes.c_int32), ('terrain_light', ctypes.c_float * 3),
                ('object_light', ctypes.c_float * 3), ('model_type', ctypes.c_int32), ('class_index', ctypes.c_int32),
                ('is_hero', ctypes.c_int32), ('ability', ctypes.c_uint8)]


def light_client(world_args, case):
    """RenderCharacter on one character; returns character +0x1b8 at the end of the light block
    0x01367530..0x01367d85 (a code hook at 0x01367d85), or None when the run does not reach it."""
    from unicorn import UC_HOOK_CODE
    w = World(*world_args)
    m = w.m
    w.add_model(0xa91, PLAYER_MODEL, bones=60, meshes=0, actions=390, actions_at=ACTIONS)
    w.add_model(0xa92, PLAYER_MODEL + 0x100, bones=60, meshes=0, actions=390, actions_at=ACTIONS)
    for k in range(0x186):
        m.write(ACTIONS + 16 * k, struct.pack('<BxxxI', 0, f2u(0.25)))
    record = character_record(cls=1, action=1)
    o = 0x3254
    struct.pack_into('<3I', record, o + 0xec, *case['object_light'])
    struct.pack_into('<h', record, 0x146, case['class_index'])
    m.write(CHAR, record)
    m.write(BONES, b''.join(struct.pack('<12f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0) for _ in range(200)))
    m.ensure(0x01d1df70, 4)
    m.w32(0x01d1df70, case['scene_state'])
    m.map(HERO_ATTR, 0x1000)
    m.write(HERO_ATTR + 0x1a6, bytes([case['ability']]))
    m.ensure(0x01d1df1c, 4)
    m.w32(0x01d1df1c, HERO_ATTR)
    m.w32(0x0a39d754, CHAR if case['is_hero'] else HERO)
    calls = []

    def terrain_light(mm):
        calls.append(('terrain_light', mm.arg(0), mm.arg(1)))
        for k in range(3):
            mm.w32(mm.arg(2) + 4 * k, case['terrain_light'][k])
        return 0
    m.stub(0x016cb08d, terrain_light, 0)
    for address, cleanup in CHAR_SKIPS.items():
        m.stub(address, (lambda a: (lambda mm: 0))(address), cleanup)
    m.stub(0x00d33153, lambda mm: ACTIONS + 16 * mm.arg(0), 4)
    m.stub(0x012b5064, lambda mm: 0, 0x20)
    m.stub(0x012b4dd3, lambda mm: 0, 0x18)
    m.stub(0x017e63f4, lambda mm: 0, 0)
    m.stub(0x012bd910, lambda mm: 0, 0)
    seen = []

    def at_start(uc, address, size, user):
        # the block reads the object type at 0x0136768a only; a Player body runs up to the block and the
        # case type is written at its entry (types such as 0x7dc take other paths before it)
        m.write(CHAR + o + 0x5c, struct.pack('<i', case['model_type']))
    m.uc.hook_add(UC_HOOK_CODE, at_start, begin=LIGHT_BLOCK_START, end=LIGHT_BLOCK_START)

    def at_end(uc, address, size, user):
        if not seen:
            seen.append(tuple(struct.unpack('<3I', m.read(CHAR + 0x1b8, 12))))
    m.uc.hook_add(UC_HOOK_CODE, at_end, begin=LIGHT_BLOCK_END, end=LIGHT_BLOCK_END)
    result = m.run(0x01363260, [CHAR, CHAR + o, 0])
    return (seen[0] if seen else None), calls, result


def light_c(lib, case):
    c = CLightIn(scene_state=case['scene_state'], model_type=case['model_type'], class_index=case['class_index'],
                 is_hero=case['is_hero'], ability=case['ability'])
    for k in range(3):
        c.terrain_light[k] = u2f(case['terrain_light'][k])
        c.object_light[k] = u2f(case['object_light'][k])
    out = (ctypes.c_float * 3)()
    status = lib.mu_rc_character_light(ctypes.byref(c), out)
    return status, tuple(f2u(v) for v in out)


def random_light_case(rng):
    def fb(lo, hi):
        return f2u(rng.uniform(lo, hi))
    glow = [0x211, 0x215, 0x216, 0x21b, 0x349, 0x34c, 0x371, 0x373, 0x3c1, 0x3d5]
    return {'scene_state': rng.choice([6, 6, 6, 5, 5, 2, 4, rng.randrange(-1, 12)]),
            'terrain_light': [fb(0, 1.5) for _ in range(3)],
            'object_light': [rng.choice([f2u(0.2), f2u(0.0), fb(-0.5, 1.5)]) for _ in range(3)],
            'model_type': rng.choice([0xa91] * 8 + [0x7dc]),
            'class_index': rng.choice([0, 1, 2, 3, 7, rng.randrange(0x200), rng.randrange(0x1000)] + glow[:1]
                                      if rng.random() < 0.9 else glow),
            'is_hero': rng.choice([0, 1, 1]),
            'ability': rng.choice([0, 0, 1, 2, 4, 8, rng.randrange(256)])}


def light_section(world_args, lib, args):
    lib.mu_rc_character_light.argtypes = [ctypes.POINTER(CLightIn), ctypes.POINTER(ctypes.c_float)]
    lib.mu_rc_character_light.restype = ctypes.c_int
    rng = random.Random(args.seed + 11)
    cases = [random_light_case(rng) for _ in range(args.light_cases)]
    # every scene/hero/ability-bit/type path at least once
    for scene in (5, 6):
        for hero in (0, 1):
            for bit in range(5):
                for model_type in (0xa91, 0x7dc):
                    cases.append({'scene_state': scene, 'terrain_light': [f2u(0.3), f2u(0.6), f2u(0.9)],
                                  'object_light': [f2u(0.2)] * 3, 'model_type': model_type, 'class_index': 1,
                                  'is_hero': hero, 'ability': (1 << bit) if bit < 4 else 0xf})
    matches, unsupported, failures, tally = 0, 0, [], {'hero': 0, 'scene5': 0, 'type_7dc': 0, 'ability_bits': 0,
                                                         'glow_branch': 0, 'terrain_light_calls': 0}
    for case in cases:
        status, mine = light_c(lib, case)
        client, calls, result = light_client(world_args, case)
        tally['terrain_light_calls'] += sum(1 for c in calls if c[0] == 'terrain_light')
        if status == 2:
            unsupported += 1
            tally['glow_branch'] += 1
            continue
        tally['hero'] += case['is_hero']
        tally['scene5'] += case['scene_state'] == 5
        tally['type_7dc'] += case['model_type'] == 0x7dc
        tally['ability_bits'] += bool(case['is_hero'] and case['ability'] & 0xf)
        if client is not None and client == mine:
            matches += 1
        elif len(failures) < 10:
            failures.append({'case': case, 'client': client, 'c': mine, 'result': result})
    # negative control: the hero without the ability tints
    control = 0
    for case in cases:
        if case['is_hero'] and case['scene_state'] != 5 and case['ability'] & 0xf and \
                lib.mu_rc_light_glow_class(case['class_index']) == 0:
            status, mine = light_c(lib, dict(case, ability=0))
            client, _, _ = light_client(world_args, case)
            control += client != mine
    compared = len(cases) - unsupported
    return {'cases': len(cases), 'compared': compared, 'matches': matches, 'unsupported_glow': unsupported,
            'coverage': tally, 'negative_control_detected': control, 'failures': failures,
            'ok': matches == compared and control > 0}


# ---------------------------------------------------------------- weapon link bones
def extract_link_bones(world_args, types):
    """Weapon link bones (+0x19b1, +0x1dad) the character create 0x0137d8a1 sets per model
    type: its switch 0x0137eefc..0x0137f5f4 executed with the frame built (EXTRACTED)."""
    table = {}
    for model_type in types:
        w = World(*world_args)
        w.m.write(CHAR, character_record())
        w.m.write(CHAR + 0x19b1, b'\xee')
        w.m.write(CHAR + 0x19b1 + 0x3fc, b'\xee')
        result = w.m.run_inside(0x0137eefc, 0x0137f5f4, 0x40, {8: CHAR, 0xc: model_type, -4: CHAR + 0x3254})
        if not result['ok']:
            table[model_type] = None
            continue
        table[model_type] = (w.m.read(CHAR + 0x19b1, 1)[0], w.m.read(CHAR + 0x19b1 + 0x3fc, 1)[0])
    return table


def emit_link_bones(path, table):
    lines = ['/* Generated by scripts/validate_renderchar.py --emit-link-bones: the weapon link bones',
             ' * (character +0x19b1, +0x1dad) the character create 0x0137d8a1 assigns per model type,',
             ' * from its switch 0x0137eefc..0x0137f5f4 executed under Unicorn (EXTRACTED). 0xee = not',
             ' * written; types that stop are absent. */',
             'static const struct { uint16_t type; uint8_t right, left; } mu_rc_link_bones[] = {']
    for t, v in sorted(table.items()):
        if v is not None:
            lines.append('    {0x%04x, 0x%02x, 0x%02x},' % (t, v[0], v[1]))
    lines.append('};')
    path.write_text('\n'.join(lines) + '\n')


def bits_list(values):
    return tuple(f2u(v) for v in values)


def c_stream(lib, case, generic=False):
    item = CItem(type=case['type'], item_level=case['item_level'], option1=case['option1'], ext_option=case['ext'],
                 select=0, render_type=case['render_type'], a10=case['a10'], a11=case['a11'], a12=case['a12'], a13=0,
                 alpha=u2f(case['alpha']), light=F3(*[u2f(x) for x in case['light']]),
                 object_alpha=u2f(case['object_alpha']), blend_mesh=case['blend_mesh'],
                 blend_light=u2f(case['blend_light']), u=u2f(case['u']), v=u2f(case['v']),
                 time=u2f(case['time']), quality=case['quality'], has_record=int(case['record'] is not None),
                 kind_a=(case['record'] or (0, 0, 0))[0], kind_b=(case['record'] or (0, 0, 0))[1],
                 item_kind=(case['record'] or (0, 0, 0))[2], enchant=F3(*[u2f(x) for x in case['enchant']]))
    model = CModel(body_light=F3(*[u2f(x) for x in case['model_light']]), level_field=case['model_level'],
                   shade=F3(*[u2f(x) for x in case['model_shade']]), flag_ca=case['model_ca'])
    out = (CDraw * 32)()
    count = ctypes.c_int32()
    entry = lib.mu_rc_item_draws_generic if generic else lib.mu_rc_item_draws
    status = entry(ctypes.byref(item), ctypes.byref(model), out, 32, ctypes.byref(count))
    stream = []
    for d in out[:min(count.value, 32)]:
        if d.entry == 1:
            args = [d.flags, f2u(d.alpha), d.blend_mesh & 0xffffffff, f2u(d.blend_light), f2u(d.u), f2u(d.v),
                    d.hidden & 0xffffffff, d.texture & 0xffffffff]
        else:
            args = [d.mesh & 0xffffffff, d.flags, f2u(d.alpha), d.blend_mesh & 0xffffffff, f2u(d.blend_light), f2u(d.u),
                    f2u(d.v), d.texture & 0xffffffff]
        stream.append(('BODY' if d.entry == 1 else 'MESH', args, bits_list(d.body_light), d.level_field,
                       bits_list(d.shade), d.flag_ca))
    return status, stream


def client_stream(world_args, case, world_factory=None):
    w = (world_factory or World)(*world_args)
    m = w.m
    w.add_model(case['type'], MODEL)
    if case['record'] is not None:
        w.add_record(case['type'] - 0xae6, *case['record'])
    m.w32(OPTS + 0x2c, case['quality'])
    m.w32(0x06fce370, case['time'])
    for k in range(3):
        m.w32(LIGHT + 4 * k, case['light'][k])
        m.w32(ENCH + 4 * k, case['enchant'][k])
        m.w32(MODEL + 0x54 + 4 * k, case['model_light'][k])
        m.w32(MODEL + 0x44 + 4 * k, case['model_shade'][k])
    m.w32(MODEL + 0x40, case['model_level'])
    m.write(MODEL + 0xca, bytes([case['model_ca']]))
    m.w32(OBJ + 0xdc, case['object_alpha'])
    m.w32(OBJ + 0x74, case['blend_mesh'])
    m.w32(OBJ + 0xa8, case['blend_light'])
    m.w32(OBJ + 0xac, case['u'])
    m.w32(OBJ + 0xb0, case['v'])
    struct_obj = struct.pack('<i', case['type'])
    m.write(OBJ + 0x5c, struct_obj)
    args = [OBJ, case['type'], LIGHT, case['alpha'], case['item_level'], case['option1'], case['ext'], 0,
            case['render_type'], case['a10'], case['a11'], case['a12'], 0]
    result = m.run(0x0176ce74, args)
    stream = []
    for call in w.calls:
        if call[0] in ('BODY', 'MESH'):
            s = call[3]
            stream.append((call[0], call[2], tuple(s['body_light']), s['level_field'], tuple(s['shade']), s['flag_ca']))
    others = [c for c in w.calls if c[0] not in ('BODY', 'MESH')]
    return result, stream, others, m


def random_case(rng, item_type):
    case = random_case_any(rng, item_type)
    if 0xa99 <= item_type <= 0xaa1:
        case.update(item_level=0, option1=0, ext=0)
    return case


def random_case_any(rng, item_type):
    def fbits(lo, hi):
        return f2u(rng.uniform(lo, hi))
    record = None if rng.random() < 0.1 else (rng.choice([0, 0, 0, 6, rng.randrange(256)]),
                                              rng.choice([0, 0, 0, 0x26, 0x5b, rng.randrange(256)]),
                                              rng.choice([0, 0, 0, 4, rng.randrange(256)]))
    a10 = -1 if rng.random() < 0.8 else rng.randrange(-2, 6)
    a11 = -1 if rng.random() < 0.8 else rng.randrange(-2, 0x9000)
    return {'type': item_type, 'item_level': rng.choice([rng.randrange(16) << 3, rng.randrange(-0x80, 0x100)]),
            'option1': rng.choice([0, 1, 1, rng.randrange(256)]), 'ext': rng.choice([0, 0, rng.randrange(0x40)]),
            'render_type': rng.choice([2, 2, 0, 0x40042, 0x102, 0x402, rng.randrange(0x10000)]),
            'a10': a10 & 0xffffffff, 'a11': a11 & 0xffffffff, 'a12': 3,
            'alpha': fbits(0.02, 1.0), 'light': [fbits(0, 1.5) for _ in range(3)], 'object_alpha': fbits(0, 1),
            'blend_mesh': rng.choice([-1, 0, rng.randrange(8)]) & 0xffffffff, 'blend_light': fbits(0, 1),
            'u': fbits(-1, 1), 'v': fbits(-1, 1), 'time': fbits(0, 2e6), 'quality': rng.choice([0, 1, 2, 3, 4, 5, 5, 9]),
            'record': record, 'enchant': [fbits(0, 1) for _ in range(3)],
            'model_light': [fbits(0, 1) for _ in range(3)], 'model_shade': [fbits(0, 1) for _ in range(3)],
            'model_level': rng.randrange(-1, 16), 'model_ca': rng.randrange(2)}


CLASSIFY = [dict(item_level=lv << 3, option1=opt, ext=ext, quality=q, time=f2u(t), render_type=rt)
            for lv, opt, ext, q, t, rt in ((0, 0, 0, 5, 0.0, 2), (0, 1, 0, 5, 700.0, 2), (3, 0, 0, 5, 300.0, 2),
                                           (5, 0, 0, 5, 900.0, 2), (7, 0, 0, 5, 0.0, 2), (9, 0, 1, 5, 400.0, 2),
                                           (11, 0, 0, 5, 0.0, 2), (13, 1, 0, 5, 1300.0, 2), (15, 0, 2, 5, 2000.0, 0x102),
                                           (12, 0, 0, 2, 0.0, 0), (6, 1, 0x10, 5, 5000.0, 0x40042))]


def classify_case(item_type, config):
    case = {'type': item_type, 'item_level': config['item_level'], 'option1': config['option1'], 'ext': config['ext'],
            'render_type': config['render_type'], 'a10': 0xffffffff, 'a11': 0xffffffff, 'a12': 3,
            'alpha': f2u(0.9), 'light': [f2u(0.8), f2u(0.7), f2u(0.6)], 'object_alpha': f2u(1.0),
            'blend_mesh': 0xffffffff, 'blend_light': f2u(0.0), 'u': 0, 'v': 0, 'time': config['time'],
            'quality': config['quality'], 'record': (0, 0, 0), 'enchant': [f2u(0.25), f2u(0.5), f2u(0.75)],
            'model_light': [0, 0, 0], 'model_shade': [0, 0, 0], 'model_level': 0, 'model_ca': 0}
    return case


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True, help='captured trig dispatch flag 0x0bdd1cc8')
    parser.add_argument('--feature', type=Path, required=True, help='captured math feature word 0x01cf6618')
    parser.add_argument('--cases', type=int, default=2000)
    parser.add_argument('--classify', choices=('none', 'sample', 'all', 'parts'), default='sample')
    parser.add_argument('--merge-special', type=Path, help='keep the special ranges of this header (with --classify parts)')
    parser.add_argument('--emit-special', type=Path)
    parser.add_argument('--seed', type=int, default=20261017)
    parser.add_argument('--sections', default='items,back')
    parser.add_argument('--kind-types', type=int, default=2, help='types per item group in the kind sweep')
    parser.add_argument('--characters', type=int, default=300)
    parser.add_argument('--light-cases', type=int, default=400)
    parser.add_argument('--emit-link-bones', type=Path)
    parser.add_argument('--back-types', choices=('sample', 'weapons'), default='sample')
    parser.add_argument('--emit-back', type=Path, help='write the extracted back-carry matrix table')
    parser.add_argument('--back-checks', type=int, default=300)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = rmach.load_pinned(args.text, rmach.TEXT_BYTES, rmach.TEXT_SHA256, 'text')
    data = rmach.load_pinned(args.data, rmach.DATA_BYTES, rmach.DATA_SHA256, 'data')
    flag, feature = args.flag.read_bytes()[:4], args.feature.read_bytes()[:4]
    lib = ctypes.CDLL(str(LIBRARY))
    lib.mu_rc_item_special.restype = ctypes.c_int
    world_args = (text, data, flag, feature)
    report = {'text_sha256': rmach.TEXT_SHA256, 'data_sha256': rmach.DATA_SHA256,
              'routines': {name: [hex(a), hex(b), hashlib.sha256(text[a - rmach.TEXT_BASE:b - rmach.TEXT_BASE]).hexdigest()]
                           for name, (a, b) in ROUTINES.items()},
              'services': {hex(k): v for k, v in SERVICES.items()}}
    started = clock.time()
    sections = set(args.sections.split(','))
    if 'back' in sections:
        report['back'] = back_section(world_args, lib, args)
    if 'kinds' in sections:
        report['kinds'] = kind_section(world_args, lib, args)
    if 'linkbones' in sections:
        table = extract_link_bones(world_args, list(range(0x7a5, 0xa92)))
        report['linkbones'] = {'types': len(table), 'extracted': sum(v is not None for v in table.values()),
                               'written': sum(1 for v in table.values() if v and v != (0xee, 0xee)), 'ok': True}
        if args.emit_link_bones:
            emit_link_bones(args.emit_link_bones, table)
    if 'character' in sections:
        report['character'] = character_section(world_args, lib, args)
    if 'light' in sections:
        report['light'] = light_section(world_args, lib, args)
    if 'items' not in sections:
        report['seconds'] = round(clock.time() - started, 1)
        if args.output:
            args.output.write_text(json.dumps(report, indent=1, default=str))
        print(json.dumps({k: v for k, v in report.items() if k in ('back', 'kinds', 'character', 'linkbones', 'light')}, default=str)[:4000])
        return 0 if all(report[k]['ok'] for k in ('back', 'kinds', 'character', 'linkbones', 'light') if k in report) else 1
    # --- classification
    special = set()
    if args.classify != 'none':
        types = [0xae6 + g * 512 + i for g in range(16) for i in range(512)] + list(range(0x3700, 0x3900))
        if args.classify == 'sample':
            types = [t for t in types if (t - 0xae6) % 512 < 40]
        elif args.classify == 'parts':
            types = list(range(0x3700, 0x3900))
        for item_type in types:
            for config in CLASSIFY:
                case = classify_case(item_type, config)
                result, stream, _, _ = client_stream(world_args, case)
                status, cstream = c_stream(lib, case, generic=True)
                if not result['ok'] or stream != cstream:
                    special.add(item_type)
                    break
        report['classification'] = {'types': len(types), 'special': len(special)}
        if args.emit_special:
            if args.merge_special:
                import re as _re
                for a, b in _re.findall(r'\{0x([0-9a-f]+), 0x([0-9a-f]+)\}', args.merge_special.read_text()):
                    if not 0x3700 <= int(a, 16) < 0x3900:
                        special.update(range(int(a, 16), int(b, 16) + 1))
            ranges = []
            for t in sorted(special):
                if ranges and ranges[-1][1] == t - 1:
                    ranges[-1][1] = t
                else:
                    ranges.append([t, t])
            lines = ['/* Generated by scripts/validate_renderchar.py --emit-special: item types whose',
                     ' * executed RenderObjDraw stream differs from the generic reconstruction in at',
                     ' * least one classification configuration (type-specific client branches). */',
                     'static const int32_t mu_rc_special_ranges[][2] = {']
            lines += [f'    {{0x{a:04x}, 0x{b:04x}}},' for a, b in ranges] or ['    {-1, -1},']
            lines += ['};', '', 'static int mu_rc_special_type(int32_t type)', '{',
                      '    /* classified: items 0xae6..0x2ae5 and the class part skins 0x3700..0x38ff */',
                      '    if (!((type >= 0xae6 && type < 0xae6 + 16 * 512) || (type >= 0x3700 && type < 0x3900)))',
                      '        return 1;   /* outside the classified ranges */',
                      '    for (size_t i = 0; i < sizeof mu_rc_special_ranges / sizeof mu_rc_special_ranges[0]; ++i)',
                      '        if (type >= mu_rc_special_ranges[i][0] && type <= mu_rc_special_ranges[i][1])',
                      '            return 1;', '    return 0;', '}', '']
            args.emit_special.write_text('\n'.join(lines))
    # --- random cases on generic types
    rng = random.Random(args.seed)
    generic = [t for t in range(0xae6, 0xae6 + 16 * 512) if not lib.mu_rc_item_special(t) and t not in special]
    generic += list(range(0xa99, 0xaa2)) * 20          # +15 attachment models (level/option/ext 0)
    matches, failures, excluded = 0, [], 0
    controls = {'cases': [], 'level-8': 0, 'time+1000ms': 0, 'quality-1': 0, 'excellent-flipped': 0}
    for index in range(args.cases):
        case = random_case(rng, rng.choice(generic))
        status, cstream = c_stream(lib, case)
        if status == 2:                      # outside the reconstructed domain (record type 4)
            excluded += 1
            continue
        result, stream, others, m = client_stream(world_args, case)
        if result['ok'] and status == 0 and stream == cstream:
            matches += 1
            if len(controls['cases']) < 300:
                # negative controls: the C with one input changed must differ from the client
                controls['cases'].append(1)
                for name, change in (('level-8', {'item_level': case['item_level'] - 8}),
                                     ('time+1000ms', {'time': f2u(u2f(case['time']) + 1000.0)}),
                                     ('quality-1', {'quality': case['quality'] - 1}),
                                     ('excellent-flipped', {'option1': 1 - case['option1'] if case['option1'] in (0, 1) else 1})):
                    mutated = dict(case, **change)
                    if c_stream(lib, mutated)[1] != stream:
                        controls[name] += 1
        elif len(failures) < 20:
            failures.append({'case': {k: (hex(v) if isinstance(v, int) else v) for k, v in case.items()},
                             'result': result, 'status': status, 'client': stream, 'c': cstream,
                             'backtrace': m.backtrace() if not result['ok'] else None})
    report['items'] = {'cases': args.cases, 'excluded': excluded, 'compared': args.cases - excluded, 'matches': matches,
                       'failures': failures, 'generic_types': len(generic),
                       'negative_controls': {k: (len(v) if k == 'cases' else v) for k, v in controls.items()}}
    report['seconds'] = round(clock.time() - started, 1)
    text_out = json.dumps(report, indent=1, default=str)
    if args.output:
        args.output.write_text(text_out)
    print(json.dumps({'classification': report.get('classification'), 'items': {k: v for k, v in report['items'].items() if k != 'failures'},
                      'seconds': report['seconds']}))
    if failures:
        print(json.dumps(failures[:2], indent=1, default=str)[:6000])
    return 0 if matches == args.cases - excluded else 1


if __name__ == '__main__':
    sys.exit(main())
