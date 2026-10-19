#!/usr/bin/env python3
"""Compare reconstructed/items with the client's instructions (NATIVE-ITEMS-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case),
with the x87 return helpers of scripts/validate_combat.py. The authored C
(libclient_items) runs on the same inputs.

Families (client routine -> authored function):

* item_angle    ItemAngle 0x01802a66 -> mu_gi_item_angle (the lifted C): Angle,
                Scale and the result byte. The item-script singleton, record
                lookup and kind predicates and the per-index table are stubs
                answering from the case; the vec3 index helper 0x00cfc922 and
                the range helper 0x0095c61f run as client code.
* label_color   the class colour 0x00c84f00 -> mu_gi_label_color.
* object_attr   ItemObjectAttribute 0x016da00b -> mu_gi_object_attribute
                (sin 0x009681bd and rand() are recording stubs; the sub-object
                reset 0x01295f18 is a stub).
* name          the name builder 0x017ea422 -> mu_gi_name_build (the lifted
                C): the colour class (+0x55c), the label text (+0x509) and the
                sequence of sprintf/strcat/strcpy results. sprintf, strcat,
                strcpy, strncpy, memset, GlobalText, the record accessor, the
                kind predicates, the set and text tables, the prefix string and
                the label window are stubs over synthetic strings; 0x00cd0995
                and 0x00cd2175 run as client code.
* create        CreateItem 0x016daa27 -> mu_gi_create: every ITEM and OBJECT
                byte the client writes, the drop sounds, the effects of the
                firecracker boxes and the order of the sub-routine calls
                (reset, SetLive, ItemObjectAttribute, ItemAngle, the name
                builder: recording stubs). The item-code decoder 0x00f09ddc
                runs as client code. The instruction at 0x016dad9b is
                runtime-patched in the capture (a jump into an unanalysed
                module); the validator writes back the compare it overwrote,
                cmp dword ptr [ebp-0x18], 0x1c0d (the low word inferred from
                the same jewel list in the pick-up handler 0x012424bd; the high
                word is the capture's leftover bytes 00 00).
* viewport      ReceiveCreateItemViewport 0x0122c216 -> mu_gi_viewport_parse:
                the CreateItem calls (slot, bytes, x, y, flag), the resets,
                the pool keys and label view bytes.
* move          MoveItems 0x017ea1aa over the 1000-record pool, with the
                sparkle 0x017f7290 as client code (AngleMatrix 0x00cff32a and
                VectorRotate 0x00d000ad as client code; rand(), the terrain
                height, ItemAngle and CreateParticle 0x0168fafd are recording
                stubs) -> mu_gi_move_item.
* render        RenderItems 0x017e9495 over the pool -> mu_gi_render_plan:
                every RenderPartObject 0x017e63f4 call (with the object
                position at the call), the Animation 0x012b5064 arguments, the
                model fields written, the visible byte and the screen
                position (frustum test, model getter, terrain light, sqrt,
                sin, the projection 0x0184a244 and the world predicates are
                stubs; the zen pile runs AngleMatrix/VectorRotate as client
                code over the 100-entry random table).
* select        SelectItem 0x016b4fc0 over the pool -> mu_gi_select (the OBB
                copy 0x00ce3931 and the ray test 0x018500bf are stubs).

Every case compares bit for bit (any two NaNs are equal, as in
validate_combat.py). Negative controls (a planted mistake, emulated on the C
side) must disagree.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import re
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import validate_combat as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
f32, bits, from_bits, same = vc.f32, vc.bits, vc.from_bits, vc.same

ITEM_ANGLE, NAME_BUILDER, OBJECT_ATTR, CREATE_ITEM = 0x01802a66, 0x017ea422, 0x016da00b, 0x016daa27
VIEWPORT, MOVE_ITEMS, RENDER_ITEMS, SELECT_ITEM, LABEL_COLOR = 0x0122c216, 0x017ea1aa, 0x017e9495, 0x016b4fc0, \
    0x00c84f00
SCRIPT, RECORD, KIND_A, KIND_B = 0x00cd4ea8, 0x00cd5d29, 0x00cd5fac, 0x00cd6017
PET_TABLE, PET_LOOKUP = 0x009c2aea, 0x01807c32
RAND, TERRAIN, SINE, SQRT, SOUND = 0x01989721, 0x016cc9e2, 0x009681bd, 0x00961a07, 0x00a6ac96
COSINE = 0x009fa223
WORLD, TIME = 0x01cf15fc, 0x06fce370
POOL, STRIDE = 0x0b4780c8, 0x560
RANDOM_TABLE = 0x06fc9cb8
HERO_POINTER = 0x0a39d754
PATCHED_SITE, PATCHED_BYTES = 0x016dad9b, bytes.fromhex('817de80d1c')   # cmp dword ptr [ebp-0x18], 0x1c0d

BODIES = {
    'item_angle': (0x01802a66, 0x01805f6e), 'name_builder': (0x017ea422, 0x017ebfd2),
    'object_attribute': (0x016da00b, 0x016daa01), 'create_item': (0x016daa27, 0x016db5ae),
    'viewport': (0x0122c216, 0x0122c426), 'move_items': (0x017ea1aa, 0x017ea38b),
    'sparkle': (0x017f7290, 0x017f746f), 'render_items': (0x017e9495, 0x017ea1aa),
    'select_item': (0x016b4fc0, 0x016b5157), 'label_color': (0x00c84f00, 0x00c84fd1),
    'test_frustum': (0x016ccc14, 0x016ccce7), 'set_player_shock': (0x0138f92f, 0x0138fe69),
    'set_player_die': (0x01393a61, 0x013944d9),
    'item_code': (0x00f09ddc, 0x00f09e41),
}

OBJ = 0x22000000            # an OBJECT outside the pool
REC = 0x24000000            # an Item.bmd record
PET = 0x24100000
STRINGS = 0x25000000        # synthetic strings
SCRIPT_OBJ, PET_OBJ = 0x23000000, 0x23001000


# --------------------------------------------------------------------------
# Library.

class Record(ctypes.Structure):
    _fields_ = [('present', ctypes.c_int32), ('kind_a', ctypes.c_uint8), ('kind_b', ctypes.c_uint8),
                ('type', ctypes.c_uint8), ('pc_room', ctypes.c_uint8), ('name', ctypes.c_char_p)]


class ItemData(ctypes.Structure):
    _fields_ = [('code', ctypes.c_int32), ('level', ctypes.c_int32), ('durability', ctypes.c_uint8),
                ('excellent', ctypes.c_uint8), ('ancient', ctypes.c_uint8), ('flag_72', ctypes.c_uint8),
                ('sockets', ctypes.c_uint8*5), ('element', ctypes.c_int32), ('flag_92', ctypes.c_uint8),
                ('flag_98', ctypes.c_uint8)]


F3 = ctypes.c_float*3


class Object(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('field_04', ctypes.c_uint8), ('light_enable', ctypes.c_uint8),
                ('visible', ctypes.c_uint8), ('field_0c', ctypes.c_uint8), ('field_14', ctypes.c_int32),
                ('field_18', ctypes.c_int32), ('field_1c', ctypes.c_int32), ('action', ctypes.c_uint16),
                ('prior_action', ctypes.c_uint16), ('screen_x', ctypes.c_int16), ('screen_y', ctypes.c_int16),
                ('type', ctypes.c_int32), ('sparkle', ctypes.c_int32), ('hidden_mesh', ctypes.c_int32),
                ('blend_mesh', ctypes.c_int32), ('scale', ctypes.c_float), ('blend_light', ctypes.c_float),
                ('blend_u', ctypes.c_float), ('blend_v', ctypes.c_float), ('field_bc', ctypes.c_float),
                ('field_c0', ctypes.c_float), ('gravity', ctypes.c_float), ('frame', ctypes.c_float),
                ('prior_frame', ctypes.c_float), ('alpha', ctypes.c_float), ('light', F3), ('bbox_min', F3),
                ('bbox_max', F3), ('position', F3), ('angle', F3), ('head_angle', F3)]


class Item(ctypes.Structure):
    _fields_ = [('key', ctypes.c_uint16), ('data', ItemData), ('object', Object), ('label_view', ctypes.c_uint8),
                ('name', ctypes.c_char*0x53), ('name_class', ctypes.c_int32)]


RECORD_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)   # const mu_gi_record *
HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
LIGHT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.POINTER(ctypes.c_float))
RAND_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
FLOAT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float)
SOUND_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32)
SOCKET_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ItemData))


class Host(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('record', RECORD_FN), ('terrain_height', HEIGHT_FN),
                ('terrain_light', LIGHT_FN), ('rand', RAND_FN), ('sin', FLOAT_FN), ('sqrt', FLOAT_FN),
                ('play_sound', SOUND_FN), ('socket_like', SOCKET_FN), ('world_time', ctypes.c_float),
                ('world', ctypes.c_int32)]


class PetInfo(ctypes.Structure):
    _fields_ = [('present', ctypes.c_int32), ('scale_bits', ctypes.c_uint32), ('angle_z_bits', ctypes.c_uint32)]


class AngleEnv(ctypes.Structure):
    _fields_ = [('record', Record), ('pet', PetInfo)]


TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)     # const char *
PREFIX_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ItemData))
INT_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_int32)


class NameEnv(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('record', RECORD_FN), ('text', TEXT_FN), ('prefix', PREFIX_FN),
                ('set_tier', INT_FN), ('table_1e', TEXT_FN), ('text_string', TEXT_FN), ('level_key', INT_FN),
                ('level_table_text', TEXT_FN), ('label_window', ctypes.c_int32)]


class NameCall(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int32), ('text', ctypes.c_char*96)]


class NameSink(ctypes.Structure):
    _fields_ = [('calls', NameCall*24), ('count', ctypes.c_int32), ('label_add', ctypes.c_int32),
                ('gl_color', F3)]


RESET_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ItemData))
LIVE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Object), ctypes.c_int32)
OBJ_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Object))
ITEM_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Item))
EFFECT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(Object), ctypes.c_int32)
PENTA_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ItemData),
                            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32))


class CreateHooks(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('reset', RESET_FN), ('set_live', LIVE_FN),
                ('object_attribute', OBJ_FN), ('item_angle', OBJ_FN), ('name_build', ITEM_FN),
                ('create_effect', EFFECT_FN), ('pentagram', PENTA_FN)]


PARTICLE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                               ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_int32,
                               ctypes.c_float)


class MoveHooks(ctypes.Structure):
    _fields_ = [('context', ctypes.c_void_p), ('item_angle', OBJ_FN), ('create_particle', PARTICLE_FN)]


class ViewportEntry(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('drop', ctypes.c_int32), ('x', ctypes.c_float), ('y', ctypes.c_float),
                ('item', ctypes.c_void_p)]


class RenderCall(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('position', F3), ('light', F3), ('alpha', ctypes.c_float),
                ('item_level', ctypes.c_int32), ('option', ctypes.c_int32), ('ext', ctypes.c_int32),
                ('a12', ctypes.c_int32), ('a13', ctypes.c_int32)]


class RenderPlan(ctypes.Structure):
    _fields_ = [('visible', ctypes.c_int32), ('pose_model', ctypes.c_int32), ('pose_skin', ctypes.c_int32),
                ('pose_head_offset', ctypes.c_float), ('render_model', ctypes.c_int32), ('abort', ctypes.c_int32),
                ('calls', RenderCall*80), ('call_count', ctypes.c_int32), ('screen_x', ctypes.c_int16),
                ('screen_y', ctypes.c_int16)]


PROJECT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int32),
                              ctypes.POINTER(ctypes.c_int32))


class RenderEnv(ctypes.Structure):
    _fields_ = [('visible', ctypes.c_int32), ('pose_model_exists', ctypes.c_int32),
                ('render_model_exists', ctypes.c_int32), ('world_float', ctypes.c_int32),
                ('world_39_state', ctypes.c_int32), ('special_height', ctypes.c_float),
                ('random_table', ctypes.POINTER(ctypes.c_int32)), ('project', PROJECT_FN),
                ('context', ctypes.c_void_p), ('kind_option', ctypes.c_int32)]


RAY_FN = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_int32)


def load_library(path):
    lib = ctypes.CDLL(str(path))
    P = ctypes.POINTER
    lib.mu_gi_item_angle.argtypes = [P(Object), P(AngleEnv)]
    lib.mu_gi_item_angle.restype = ctypes.c_int32
    lib.mu_gi_label_color.argtypes = [ctypes.c_int32]
    lib.mu_gi_label_color.restype = ctypes.c_char_p
    lib.mu_gi_object_attribute.argtypes = [P(Object), P(Host)]
    lib.mu_gi_name_build.argtypes = [P(Item), P(NameEnv), P(NameSink)]
    lib.mu_gi_create.argtypes = [P(Item), ctypes.c_char_p, P(ctypes.c_float), ctypes.c_int32, P(Host),
                                 P(CreateHooks)]
    lib.mu_gi_create.restype = ctypes.c_int32
    lib.mu_gi_viewport_parse.argtypes = [ctypes.c_char_p, P(ViewportEntry), ctypes.c_int32]
    lib.mu_gi_viewport_parse.restype = ctypes.c_int32
    lib.mu_gi_move_item.argtypes = [P(Object), P(Host), P(MoveHooks)]
    lib.mu_gi_move_item.restype = ctypes.c_int32
    lib.mu_gi_render_plan.argtypes = [P(Item), ctypes.c_int32, P(Host), P(RenderEnv), P(RenderPlan)]
    lib.mu_gi_select.argtypes = [P(Item), ctypes.c_int32, RAY_FN, ctypes.c_void_p]
    lib.mu_gi_select.restype = ctypes.c_int32
    lib.mu_gi_drop_sound.argtypes = [ctypes.c_int32, ctypes.c_int32]
    lib.mu_gi_drop_sound.restype = ctypes.c_int32
    return lib


# --------------------------------------------------------------------------
# Object and item layouts (client offsets) and comparisons.

OBJ_FIELDS = [('live', 0x00, 'B'), ('field_04', 0x04, 'B'), ('light_enable', 0x05, 'B'), ('visible', 0x0b, 'B'),
              ('field_0c', 0x0c, 'B'), ('field_14', 0x14, 'i'), ('field_18', 0x18, 'i'), ('field_1c', 0x1c, 'i'),
              ('action', 0x2a, 'H'), ('prior_action', 0x2c, 'H'), ('screen_x', 0x50, 'h'), ('screen_y', 0x52, 'h'),
              ('type', 0x5c, 'i'), ('sparkle', 0x60, 'i'), ('hidden_mesh', 0x68, 'i'), ('blend_mesh', 0x74, 'i'),
              ('scale', 0xa0, 'f'), ('blend_light', 0xa8, 'f'), ('blend_u', 0xac, 'f'), ('blend_v', 0xb0, 'f'),
              ('field_bc', 0xbc, 'f'), ('field_c0', 0xc0, 'f'), ('gravity', 0xc8, 'f'), ('frame', 0xd0, 'f'),
              ('prior_frame', 0xd4, 'f'), ('alpha', 0xdc, 'f'), ('light', 0xec, '3f'), ('bbox_min', 0x128, '3f'),
              ('bbox_max', 0x134, '3f'), ('position', 0x158, '3f'), ('angle', 0x164, '3f'),
              ('head_angle', 0x170, '3f')]
ITEM_FIELDS = [('code', 0x10, 'i'), ('level', 0x14, 'i'), ('durability', 0x38, 'B'), ('excellent', 0x3a, 'B'),
               ('ancient', 0x3b, 'B'), ('flag_72', 0x72, 'B'), ('sockets', 0x73, '5B'), ('element', 0x84, 'i'),
               ('flag_92', 0x92, 'B'), ('flag_98', 0x98, 'B')]


def field_size(fmt):
    return struct.calcsize('<' + fmt)


def fill_struct(s, fields, raw, base=0):
    for name, off, fmt in fields:
        values = struct.unpack_from('<' + fmt, raw, base+off)
        target = getattr(s, name)
        if len(values) == 1 and not hasattr(target, '__len__'):
            setattr(s, name, values[0])
        else:
            for k, v in enumerate(values):
                target[k] = v


def struct_values(s, name):
    v = getattr(s, name)
    return list(v) if hasattr(v, '__len__') and not isinstance(v, bytes) else [v]


def compare_fields(s, fields, raw, base=0, label=''):
    for name, off, fmt in fields:
        theirs = struct.unpack_from('<' + fmt, raw, base+off)
        mine = struct_values(s, name)
        for k, (a, b) in enumerate(zip(theirs, mine)):
            if fmt.endswith('f'):
                if not same(a, b):
                    return (label+name, k, a, b)
            elif a != b:
                return (label+name, k, a, b)
    return None


def written_outside(region_before, region_after, covered, base=0, size=None):
    """Offsets whose defined flag changed (client writes) but no compared field covers."""
    out = []
    end = len(region_after) if size is None else base+size
    for i in range(base, end):
        if region_before[i] == 0 and region_after[i] == 1 and (i-base) not in covered:
            out.append(hex(i-base))
            if len(out) > 8:
                break
    return out


def covered_offsets(fields):
    s = set()
    for _, off, fmt in fields:
        s.update(range(off, off+field_size(fmt)))
    return s


class Report:
    def __init__(self):
        self.families = {}
        self.coverage = {}

    def cover(self, family, key):
        entry = self.coverage.setdefault(family, {})
        entry[key] = entry.get(key, 0) + 1

    def add(self, family, equal, failure=None):
        entry = self.families.setdefault(family, {'cases': 0, 'equal': 0, 'first_failures': []})
        entry['cases'] += 1
        entry['equal'] += bool(equal)
        if not equal and len(entry['first_failures']) < 5:
            entry['first_failures'].append(failure)


class Machine(vc.Combat):
    """validate_combat's machine plus a recorder for the defined masks of regions and a
    mapped page at the glColor3f import target (the name builder's zen branch calls it)."""

    def __init__(self, text, data):
        super().__init__(text, data)
        from unicorn import UC_PROT_ALL
        self.data_bytes = data
        self.gl_color = struct.unpack('<I', data[0x01a7c76c-am.DATA_BASE:0x01a7c770-am.DATA_BASE])[0]
        self.uc.mem_map(self.gl_color & ~0xfff, am.PAGE, UC_PROT_ALL)
        self.uc.mem_write(self.gl_color & ~0xfff, b'\xc3'*am.PAGE)

    def execute_regions(self, start, arguments, regions, stubs, **kw):
        before = {r.name: bytes(r.defined) for r in regions}
        r = self.execute(start, arguments, regions, stubs, **kw)
        r['defined_before'] = before
        r['defined_after'] = {reg.name: bytes(reg.defined) for reg in regions}
        return r


def angle_types(header_path):
    text = Path(header_path).read_text()
    values = {int(v, 16) for v in re.findall(r'o->type [<>=!]+ (0x[0-9a-f]+)', text)}
    return sorted(values)


# --------------------------------------------------------------------------
# item_angle

def family_item_angle(m, lib, rng, cases, report, negatives):
    specials = angle_types(ROOT/'reconstructed/items/item_angle_table.h')
    for n in range(cases):
        if rng.random() < 0.75:
            t = rng.choice(specials) + rng.choice([-1, 0, 0, 0, 1])
        else:
            t = rng.randrange(0x900, 0x3a00)
        present = rng.random() < 0.7
        ka = rng.choice([0x1f, 0x17, 0x0c, 2, 0, rng.randrange(0, 256)])
        kb = rng.choice([0x24, 0x25, 0x26, 0x27, 0x5b, 0x2b, 0x10, 0, rng.randrange(0, 256)])
        ty = rng.choice([4, 4, 2, 0, rng.randrange(0, 256)])
        pet = rng.random() < 0.5
        pet_scale, pet_angle = f32(rng.uniform(0.2, 2.0)), f32(rng.uniform(-180, 180))
        obj = am.undefined_region('object', OBJ, 0x400, 0x41)
        obj.define(OBJ+0x5c, struct.pack('<i', t))
        rec = am.undefined_region('record', REC, 0x2c4, 0x43)
        rec.define(REC+0x250, bytes([ka, kb, ty]))
        petr = am.undefined_region('pet', PET, 0x270, 0x45)
        petr.define(PET+0x25c, struct.pack('<ff', pet_scale, pet_angle))
        calls = []
        index = t - 0xae6

        def code_ok(i):
            return 0 <= i <= 0x2c00

        def record(mm):
            calls.append(('record', mm.argument(0)))
            return (REC if present else 0), 4

        def kind(which):
            def stub(mm):
                i, k = mm.argument(0), mm.argument(1)
                i = i - (1 << 32) if i & 0x80000000 else i
                calls.append((which, i, k))
                v = present and code_ok(i) and ((ka if which == 'a' else kb) == (k & 0xff))
                return 0x5a00 | int(v), 8
            return stub

        def pet_lookup(mm):
            calls.append(('pet', mm.argument(0)))
            return (PET if pet else 0), 4
        stubs = {SCRIPT: lambda mm: SCRIPT_OBJ, RECORD: record, KIND_A: kind('a'), KIND_B: kind('b'),
                 PET_TABLE: lambda mm: PET_OBJ, PET_LOOKUP: pet_lookup}
        r = m.execute_regions(ITEM_ANGLE, [OBJ], [obj, rec, petr], stubs)
        raw = r['regions'].get('object', b'')
        o = Object()
        fill_struct(o, OBJ_FIELDS, bytes(am.poison(0x400, 0x41)))
        o.type = t
        env = AngleEnv()
        env.record = Record(1 if present else 0, ka, kb, ty, 0, None)
        env.pet = PetInfo(1 if pet else 0, bits(pet_scale), bits(pet_angle))
        res = lib.mu_gi_item_angle(ctypes.byref(o), ctypes.byref(env))
        mismatch = None
        if vc.ok(r):
            mismatch = compare_fields(o, OBJ_FIELDS, raw)
            if mismatch is None:
                extra = written_outside(r['defined_before']['object'], r['defined_after']['object'],
                                        covered_offsets(OBJ_FIELDS))
                if extra:
                    mismatch = ('unmodelled writes', extra)
        report.add('item_angle', vc.ok(r) and mismatch is None,
                   {'case': n, 'type': hex(t), 'present': present, 'kinds': (ka, kb, ty), 'pet': pet,
                    'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('item_angle', 'record' if any(c[0] in ('a', 'b') for c in calls) else 'type only')
        if vc.ok(r) and mismatch is None:
            # negative control: the record tests ignored (record taken as absent)
            o2 = Object()
            fill_struct(o2, OBJ_FIELDS, bytes(am.poison(0x400, 0x41)))
            o2.type = t
            env2 = AngleEnv()
            env2.pet = env.pet
            lib.mu_gi_item_angle(ctypes.byref(o2), ctypes.byref(env2))
            negatives['angle_no_record'] += compare_fields(o2, OBJ_FIELDS, raw) is not None


# --------------------------------------------------------------------------
# label_color

def family_label_color(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        c = rng.choice(list(range(-3, 30)) + [rng.randrange(-2**31, 2**31)])
        r = m.execute(LABEL_COLOR, [c], [], {}, ecx=0x12345000, cleanup=4)
        client = None
        if vc.ok(r):
            client = ''
            a = r['eax']
            while True:
                b = m.uc.mem_read(a+len(client), 1)
                if b == b'\0':
                    break
                client += b.decode('latin1')
        mine = lib.mu_gi_label_color(c).decode('latin1')
        report.add('label_color', vc.ok(r) and client == mine, {'class': c, 'client': client, 'c': mine,
                                                                 'stopped': r['stopped'], 'error': r['error']})
        report.cover('label_color', mine)
        if vc.ok(r) and 0 <= c <= 0x15:
            negatives['color_shifted'] += lib.mu_gi_label_color(c+1).decode('latin1') != client


# --------------------------------------------------------------------------
# object_attr

class HostCase:
    """rand(), sin, sqrt, terrain height/light and records for both sides of a case."""

    def __init__(self, rng, records=None, height=0.0, light=(0.5, 0.5, 0.5), world=0, world_time=0.0):
        self.rand_values = [rng.randrange(0, 32768) for _ in range(64)]
        self.client_rand = self.c_rand = 0
        self.height = f32(height)
        self.light = [f32(x) for x in light]
        self.world, self.world_time = world, f32(world_time)
        self.records = records or {}
        self.client_calls, self.c_calls = [], []
        self._keep = []
        self._records = {}

    def heights(self, x, y):
        return self.height if not callable(self.height) else self.height(x, y)

    def stubs(self):
        def rand(mm):
            v = self.rand_values[self.client_rand % len(self.rand_values)]
            self.client_rand += 1
            return v

        def height(mm):
            x, y = mm.float_argument(0), mm.float_argument(1)
            self.client_calls.append(('height', x, y))
            return mm.x87_return(self.heights(x, y))

        def sine(mm):
            x = mm.float_argument(0)
            self.client_calls.append(('sin', x))
            return mm.x87_return(f32(math.sin(x)) if math.isfinite(x) else float('nan'))

        def cosine(mm):
            x = mm.float_argument(0)
            return mm.x87_return(f32(math.cos(x)) if math.isfinite(x) else float('nan'))

        def root(mm):
            x = mm.float_argument(0)
            self.client_calls.append(('sqrt', x))
            return mm.x87_return(f32(math.sqrt(x)) if x >= 0 else float('nan'))

        def sound(mm):
            self.client_calls.append(('sound', mm.argument(0)))
            return 0
        return {RAND: rand, TERRAIN: height, SINE: sine, COSINE: cosine, SQRT: root, SOUND: sound}

    def host(self, socket_like=None):
        def rand(ctx):
            v = self.rand_values[self.c_rand % len(self.rand_values)]
            self.c_rand += 1
            return v

        def height(ctx, x, y):
            self.c_calls.append(('height', x, y))
            return self.heights(x, y)

        def light(ctx, x, y, out):
            for k in range(3):
                out[k] = self.light[k]

        def sine(ctx, x):
            self.c_calls.append(('sin', x))
            return f32(math.sin(x)) if math.isfinite(x) else float('nan')

        def root(ctx, x):
            self.c_calls.append(('sqrt', x))
            return f32(math.sqrt(x)) if x >= 0 else float('nan')

        def sound(ctx, i):
            self.c_calls.append(('sound', i))

        def record(ctx, code):
            entry = self.records.get(code)
            if entry is None:
                return None
            if code not in self._records:
                ka, kb, ty, name, pc = entry
                self._names = getattr(self, '_names', [])
                buf = ctypes.create_string_buffer(name.encode('latin1')) if name else None
                self._names.append(buf)
                self._records[code] = Record(1, ka, kb, ty, pc, ctypes.cast(buf, ctypes.c_char_p) if buf else None)
            return ctypes.addressof(self._records[code])

        def sock(ctx, item):
            return 1 if socket_like and socket_like(item.contents.code) else 0
        fns = (RECORD_FN(record), HEIGHT_FN(height), LIGHT_FN(light), RAND_FN(rand), FLOAT_FN(sine),
               FLOAT_FN(root), SOUND_FN(sound), SOCKET_FN(sock))
        self._keep.append(fns)
        return Host(None, *fns, self.world_time, self.world)


def family_object_attr(m, lib, rng, cases, report, negatives):
    types = [0xa99, 0xa9d, 0xaa1, 0xaa2, 0xaeb, 0xaf0, 0xaf3, 0xaf4, 0xb05, 0xb0d, 0xeea, 0xeeb, 0xeec, 0xeed,
             0xf0b, 0x10e6, 0x10ef, 0x10f0, 0x12ec, 0x12f3, 0x12f4, 0x12f6, 0x14e6, 0x14eb, 0x14ec, 0x14ed, 0x14ee,
             0x14ef, 0x14f1, 0x14f3, 0x14f4, 0x150c, 0x1513, 0x1516, 0x16f1, 0x16f2, 0x16f3, 0x16f4, 0x16f6, 0x1701,
             0x1702, 0x170b, 0x1711, 0x18fe, 0x1cfe, 0x22e6, 0x22e9, 0x236a, 0x248e, 0x24e6, 0x26e7, 0x26fb,
             0x28e6, 0x10e5]
    for n in range(cases):
        t = rng.choice(types) if rng.random() < 0.8 else rng.randrange(0x900, 0x3a00)
        wt = rng.choice([0.0, 1234.5, 99999.0, rng.uniform(0, 4e6), -5.0])
        hc = HostCase(rng, world_time=wt)
        obj = am.undefined_region('object', OBJ, 0x400, 0x47)
        obj.define(OBJ+0x5c, struct.pack('<i', t))
        poison = bytes(am.poison(0x400, 0x47))
        obj.define(OBJ+0x68, poison[0x68:0x6c])     # or dword [o+0x68], -1 reads the field
        obj.define(OBJ+0x74, poison[0x74:0x78])
        regions = [obj, am.defined_region('time', TIME, struct.pack('<f', f32(wt)), writable=False)]
        stubs = hc.stubs()
        sub = []
        stubs[0x01295f18] = lambda mm: (sub.append(m.uc.reg_read(m.x86.UC_X86_REG_ECX)) or 0)
        r = m.execute_regions(OBJECT_ATTR, [OBJ], regions, stubs)
        raw = r['regions'].get('object', b'')
        o = Object()
        fill_struct(o, OBJ_FIELDS, bytes(am.poison(0x400, 0x47)))
        o.type = t
        host = hc.host()
        lib.mu_gi_object_attribute(ctypes.byref(o), ctypes.byref(host))
        mismatch = None
        if vc.ok(r):
            mismatch = compare_fields(o, OBJ_FIELDS, raw)
            if mismatch is None and hc.client_rand != hc.c_rand:
                mismatch = ('rand calls', hc.client_rand, hc.c_rand)
            if mismatch is None and sub != [OBJ+0x358]:
                mismatch = ('sub-object reset', sub)
            if mismatch is None:
                extra = written_outside(r['defined_before']['object'], r['defined_after']['object'],
                                        covered_offsets(OBJ_FIELDS))
                if extra:
                    mismatch = ('unmodelled writes', extra)
        report.add('object_attr', vc.ok(r) and mismatch is None,
                   {'case': n, 'type': hex(t), 'time': wt, 'mismatch': mismatch, 'stopped': r['stopped'],
                    'error': r['error'], 'checks': r['checks']})
        report.cover('object_attr', f'blend {o.blend_mesh} hidden {o.hidden_mesh} scale {o.scale:.2f}')
        if vc.ok(r) and mismatch is None:
            negatives['attr_scale_one'] += not same(1.0, o.scale) and same(struct.unpack_from('<f', raw, 0xa0)[0],
                                                                          o.scale)


# --------------------------------------------------------------------------
# name

class TextBank:
    """Synthetic strings in a client region and the same strings for the C side."""

    def __init__(self, base, size=0x10000):
        self.region = am.undefined_region('strings', base, size, 0x49)
        self.base, self.next, self.addresses = base, base, {}

    def add(self, key, text, m=None):
        if key in self.addresses:
            return self.addresses[key]
        raw = text.encode('latin1') + b'\0'
        a = self.next
        self.next += (len(raw) + 15) & ~15
        if m is None:
            self.region.define(a, raw)
        else:
            m.write(a, raw)
        self.addresses[key] = a
        return a


def wr(mm, address, payload):
    """Stub-side write: the stack directly, declared regions through the machine."""
    if am.STACK <= address < am.STACK + am.STACK_BYTES:
        mm.uc.mem_write(address, bytes(payload))
    else:
        mm.write(address, payload)


def rd_str(mm, address):
    return mm.cstring(address, 512)


def c_format(fmt, args):
    out, i, k = '', 0, 0
    while i < len(fmt):
        if fmt[i] == '%' and i+1 < len(fmt) and fmt[i+1] in 'sd':
            v = args[k]
            k += 1
            out += v if fmt[i+1] == 's' else str(v)
            i += 2
        elif fmt[i] == '%' and i+1 < len(fmt) and fmt[i+1] == '%':
            out += '%'
            i += 2
        else:
            out += fmt[i]
            i += 1
    return out, k


def family_name(m, lib, rng, cases, report, negatives):
    text = Path(ROOT/'reconstructed/items/item_name_table.h').read_text()
    types = sorted({int(v, 16) for v in re.findall(r'o_type [<>=!]+ (0x[0-9a-f]+)', text)})
    for n in range(cases):
        slot = rng.randrange(0, 1000)
        base = POOL + STRIDE*slot
        if rng.random() < 0.6:
            t = rng.choice(types) + rng.choice([-1, 0, 0, 0, 1])
        else:
            t = rng.randrange(0xae6, 0x36e6)
        code = rng.choice([t - 0xae6, t - 0xae6, rng.randrange(-5, 0x2c10)])
        level_byte = rng.choice([0, 8, 0x80, 0x84, 0x87, 0x7b, 0xff, rng.randrange(0, 256)])
        level = level_byte if t != 0x26f5 else rng.choice([1, 999, 123456, 0x7fffffff])
        exc = rng.choice([0, 0, 0x40, 0x3f, rng.randrange(0, 128)])
        anc = rng.choice([0, 0, 1, 0x33, rng.randrange(0, 256)])
        sockets = [rng.choice([0xfe, 0xff, 0, rng.randrange(0, 256)]) for _ in range(5)]
        element = rng.choice([0, 1, 2, 3, 4, 5, 6, rng.randrange(-2, 20)])
        f92, f98 = rng.choice([0, 1, 2]), rng.choice([0, 1, 2])
        present = True      # the builder runs only after CreateItem found the record (it reads it unchecked)
        ka = rng.choice([8, 0x19, 0x1a, 0x14, 0x17, 0x18, 6, 2, 0x20, 0x1f, rng.randrange(0, 256)])
        kb = rng.choice([0x28, 0x29, 0x2a, 0x2b, 0x79, rng.randrange(0, 256)])
        ty = rng.choice([1, 2, 4, 6, 8, rng.randrange(0, 256)])
        pc = rng.choice([0, 0, 1])
        script_present = rng.random() < 0.7
        ska = rng.choice([0x1f, 0x1f, rng.randrange(0, 256)])
        prefix = rng.choice(['', '', 'Pfx '])
        tier = rng.choice([0, 1, 2, 3, rng.randrange(-1, 6)])
        level_keys = [rng.randrange(0, 50) for _ in range(16)]
        window = rng.random() < 0.8
        recname = rng.choice(['Sword', 'Zen', 'Jewel of Chaos', 'Box'])
        if code == t - 0xae6:
            script_present, ska = present, ka      # one record answers both lookups
        bank = TextBank(STRINGS)
        rec_region = am.undefined_region('record', REC, 0x2c4, 0x4b)
        rec_region.define(REC+0x210, recname.encode('latin1')+b'\0')
        rec_region.define(REC+0x250, bytes([ka, kb, ty]))
        rec_region.define(REC+0x2b0, bytes([pc]))
        pool = am.undefined_region('pool', base, STRIDE, 0x4d)
        pool.define(base+4+0x10, struct.pack('<i', code))
        pool.define(base+4+0x14, struct.pack('<i', level))
        pool.define(base+4+0x3a, bytes([exc, anc]))
        pool.define(base+4+0x73, bytes(sockets))
        pool.define(base+4+0x84, struct.pack('<i', element))
        pool.define(base+4+0x92, bytes([f92]))
        pool.define(base+4+0x98, bytes([f98]))
        pool.define(base+0x130+0x5c, struct.pack('<i', t))
        pool.define(base+0x55c, bytes(am.poison(STRIDE, 0x4d))[0x55c:0x560])   # and dword [+0x55c], 0 reads it
        pool.define(base+0x509, b'old\0')     # stale text: some branches append to the previous label
        set_region = am.defined_region('set', 0x26000000, b'\0'*0x24 + struct.pack('<i', tier), writable=False)
        keys_region = am.defined_region('level_keys', 0x01cf15bc, struct.pack('<16i', *level_keys), writable=False)
        objects = {}           # ecx -> string (std::string stand-ins)
        log = []

        def code_ok(i):
            return 0 <= i <= 0x2c00

        def item_pred(field):
            def stub(mm):
                k = mm.argument(0) & 0xff
                v = present and code_ok(code) and {'a': ka, 'b': kb, 't': ty}[field] == k
                return 0x5b00 | int(v), 4
            return stub

        def text_stub(prefix_char):
            def stub(mm):
                i = mm.argument(0)
                return bank.add((prefix_char, i), f'{prefix_char}{i:x}', mm), 4
            return stub

        def sprintf(mm):
            dst, fmt = mm.argument(0), mm.argument(1)
            f = mm.cstring(fmt)
            nargs = f.count('%s') + f.count('%d')
            args, k = [], 2
            for ch in re.findall(r'%([sd])', f):
                a = mm.argument(k)
                args.append(mm.cstring(a) if ch == 's' else (a - (1 << 32) if a & 0x80000000 else a))
                k += 1
            out, _ = c_format(f, args)
            if len(out) > 0x50:
                raise RuntimeError(f'long sprintf {f!r} {args!r}')
            wr(mm, dst, out.encode('latin1') + b'\0')
            log.append((1, out))
            return 0

        def strcat(mm):
            dst, src = mm.argument(0), mm.argument(1)
            out = mm.cstring(dst) + mm.cstring(src)
            wr(mm, dst, out.encode('latin1') + b'\0')
            log.append((2, out))
            return dst

        def strcpy(mm):
            dst, src = mm.argument(0), mm.argument(1)
            out = mm.cstring(src)
            wr(mm, dst, out.encode('latin1') + b'\0')
            log.append((3, out))
            return dst

        def strncpy(mm):
            dst, src, cnt = mm.argument(0), mm.argument(1), mm.argument(2)
            s = mm.cstring(src)[:cnt].encode('latin1')
            wr(mm, dst, s + b'\0'*(cnt-len(s)))
            return dst

        def memset(mm):
            dst, v, cnt = mm.argument(0), mm.argument(1), mm.argument(2)
            wr(mm, dst, bytes([v & 0xff])*cnt)
            return dst

        def prefix_string(mm):     # 0x009e051c(this, out, item): the prefix std::string at out
            out = mm.argument(0)
            objects[out] = bank.add(('prefix', 0), prefix, mm)
            return out, 8

        def c_str(mm):
            ecx = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
            if ecx not in objects:
                raise RuntimeError(f'c_str of an unknown string {ecx:#x}')
            return objects[ecx]

        def empty(mm):
            ecx = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
            return int(mm.cstring(objects[ecx]) == '')

        def table_1e(mm):
            key = mm.argument(0)
            entry = 0x27000000 + 0x40*(key & 0xff)
            objects[entry+8] = bank.add(('E', key), f'E{key:x}', mm)
            return entry, 4

        def text_string(mm):
            i = mm.argument(0)
            obj_addr = 0x27100000 + 0x40*(i & 0xff)
            objects[obj_addr] = bank.add(('S', i), f'S{i:x}', mm)
            return obj_addr, 4

        def level_table(mm):
            i = mm.argument(0)
            obj_addr = 0x27200000 + 0x40*(i & 0xff)
            objects[obj_addr] = bank.add(('L', i), f'L{i:x}', mm)
            return obj_addr, 4

        def holder_lock(mm):
            out = mm.argument(0)
            wr(mm, out, struct.pack('<II', 0x28000000 if window else 0, 0))
            return out, 4

        def label_add(mm):
            log.append((7, mm.cstring(mm.argument(0)+0x509)))
            return 0, 4
        gl_target = struct.unpack('<I', m.data_bytes[0x01a7c76c-am.DATA_BASE:0x01a7c770-am.DATA_BASE])[0]

        def gl_color(mm):
            log.append((6, tuple(round(mm.float_argument(i), 6) for i in range(3))))
            return 0, 12
        stubs = {0x00ccc591: lambda mm: (REC if present else 0), 0x0095fc2e: item_pred('a'),
                 0x00987982: item_pred('b'), 0x0095fbeb: item_pred('t'), SCRIPT: lambda mm: SCRIPT_OBJ,
                 KIND_A: lambda mm: (0x5c00 | int(script_present and code_ok(mm.argument(0)) and
                                                   ska == (mm.argument(1) & 0xff)), 8),
                 0x0095f027: text_stub('G'), 0x009619dd: sprintf, 0x01983aa0: strcat, 0x01983a90: strcpy,
                 0x0194c200: strncpy, 0x0194cd00: memset, 0x009953ef: lambda mm: 0x29000000,
                 0x009e051c: prefix_string, 0x008e7940: c_str, 0x008e53e0: empty, 0x008e83a0: lambda mm: 0,
                 0x011447ac: lambda mm: (0x26000000, 4), 0x00961620: table_1e, 0x011753c3: text_string,
                 0x011427c7: level_table, 0x009a19ae: holder_lock,
                 0x009a1a51: lambda mm: int(window), 0x009a1a74: lambda mm: 0x28000000,
                 0x00c83e2a: label_add, 0x009a1a3c: lambda mm: 0, gl_target: gl_color}
        r = m.execute_regions(NAME_BUILDER, [base], [pool, rec_region, set_region, keys_region, bank.region], stubs)
        raw = r['regions'].get('pool', b'')
        # C side
        it = Item()
        fill_struct(it.data, ITEM_FIELDS, bytes(am.poison(STRIDE, 0x4d)), 4)
        fill_struct(it.object, OBJ_FIELDS, bytes(am.poison(STRIDE, 0x4d)), 0x130)
        it.data.code, it.data.level, it.data.excellent, it.data.ancient = code, level, exc, anc
        for k in range(5):
            it.data.sockets[k] = sockets[k]
        it.data.element, it.data.flag_92, it.data.flag_98 = element, f92, f98
        it.object.type = t
        poison_class = struct.unpack_from('<i', bytes(am.poison(STRIDE, 0x4d)), 0x55c)[0]
        it.name_class = poison_class
        it.name = b'old'
        keep = []
        strings = {}

        def cstr(key, value):
            if key not in strings:
                strings[key] = ctypes.create_string_buffer(value.encode('latin1'))
            return ctypes.addressof(strings[key])

        name_buf = ctypes.create_string_buffer(recname.encode('latin1'))
        rec_c = Record(1, ka, kb, ty, pc, ctypes.cast(name_buf, ctypes.c_char_p))

        def record_c(ctx, c):
            return ctypes.addressof(rec_c) if present else None
        fns = [RECORD_FN(record_c), TEXT_FN(lambda ctx, i: cstr(('G', i), f'G{i:x}')),
               PREFIX_FN(lambda ctx, item: cstr(('P',), prefix)), INT_FN(lambda ctx, c: tier),
               TEXT_FN(lambda ctx, k: cstr(('E', k), f'E{k:x}')), TEXT_FN(lambda ctx, i: cstr(('S', i), f'S{i:x}')),
               INT_FN(lambda ctx, lv: level_keys[lv] if 0 <= lv < 16 else 0),
               TEXT_FN(lambda ctx, k: cstr(('L', k), f'L{k:x}'))]
        keep.append(fns)
        env = NameEnv(None, *fns, int(window))
        # the script-kind predicate (0x00cd5fac) uses the record of o->type - 0xae6; give the C a record
        # lookup that answers it like the stub
        rec_s = Record(1, ska, 0, 0, 0, None)

        def record_any(ctx, c):
            if c == code:
                return ctypes.addressof(rec_c) if present else None
            return ctypes.addressof(rec_s) if script_present else None
        if code != t - 0xae6:
            env.record = RECORD_FN(record_any)
            keep.append(env.record)
        sink = NameSink()
        lib.mu_gi_name_build(ctypes.byref(it), ctypes.byref(env), ctypes.byref(sink))
        mine_log = []
        for k in range(sink.count):
            c = sink.calls[k]
            if c.kind == 6:
                mine_log.append((6, tuple(round(x, 6) for x in sink.gl_color)))
            else:
                mine_log.append((c.kind, c.text.decode('latin1')))
        mismatch = None
        if vc.ok(r):
            client_class = struct.unpack_from('<i', raw, 0x55c)[0]
            client_name = raw[0x509:0x509+0x53].split(b'\0')[0].decode('latin1')
            name_defined = True
            mine_name = it.name.decode('latin1')
            if client_class != it.name_class:
                mismatch = ('class', client_class, it.name_class)
            elif name_defined and client_name != mine_name:
                mismatch = ('name', client_name, mine_name)
            elif [x for x in log if x[0] != 7] != [x for x in mine_log if x[0] != 7]:
                mismatch = ('calls', log, mine_log)
            elif any(x[0] == 7 for x in log) != bool(sink.label_add):
                mismatch = ('addItem', log, sink.label_add)
            else:
                extra = written_outside(r['defined_before']['pool'], r['defined_after']['pool'],
                                        set(range(0x509, 0x560)))
                if extra:
                    mismatch = ('unmodelled writes', extra)
        report.add('name', vc.ok(r) and mismatch is None,
                   {'case': n, 'type': hex(t), 'code': hex(code), 'level': level, 'present': present,
                    'kinds': (ka, kb, ty), 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                    'checks': r['checks']})
        report.cover('name', f'class {it.name_class}')
        if vc.ok(r) and mismatch is None:
            # negative control: the level suffix forgotten ("%s" for every plain item)
            negatives['name_no_level'] += ' +' in mine_name and mine_name.split(' +')[0] != mine_name


# --------------------------------------------------------------------------
# create

SPECIAL_CODES = [0x1c0f, 0x1c0d, 0x1c0e, 0x1c10, 0x180f, 0x1c16, 0x1c1f, 0x1c29, 0x1c2a, 0x1c2b, 0x1c2c, 0x1cfe,
                 0x1d00, 0x1d03, 0x1d06, 0x1d07, 0x1d09, 0x1d0c, 0x1d0d, 0x1c0b, 0x1c20, 0x1c21, 0x1c22, 0x1c15,
                 0x1a13, 0x1c17, 0x1c18, 0x1a14, 0x1c09, 0x1a0e, 0x1a0b, 0x1c2e, 0x1c30, 0x0000, 0x0001, 0x0200,
                 0x0400, 0x0c00, 0x0e00, 0x1000, 0x1200, 0x1400, 0x1600, 0x1800, 0x1a00, 0x2000, 0x2400, 0x2c00]


def item_bytes(rng, code):
    b = [rng.randrange(0, 256) for _ in range(15)]
    b[0] = code & 0xff
    b[3] = (b[3] & 0x7f) | (((code >> 8) & 1) << 7)
    b[5] = (((code >> 9) & 0xf) << 4) | (b[5] & 0x0e) | ((code >> 13) & 1)
    return b


def terrain_height(x, y):
    """Deterministic height for both sides (binary32)."""
    if not (math.isfinite(x) and math.isfinite(y)):
        return f32(0.0)
    return f32(100.0 + (int(abs(x)) % 37) + (int(abs(y)) % 11) * 0.5)


def family_create(m, lib, rng, cases, report, negatives):
    item_cov = covered_offsets(ITEM_FIELDS)
    obj_cov = covered_offsets(OBJ_FIELDS)
    covered = {4+o for o in item_cov} | {0x130+o for o in obj_cov}
    for n in range(cases):
        slot = rng.randrange(0, 1000)
        base = POOL + STRIDE*slot
        code = rng.choice(SPECIAL_CODES) if rng.random() < 0.6 else rng.randrange(0, 0x3000)
        b = item_bytes(rng, code)
        if code in (0x1c0b, 0x1c20, 0x1c15, 0x1a13, 0x1c17, 0x1a14, 0x1c09, 0x1a0e, 0x1a0b, 0x1c18):
            b[1] = rng.choice([0, 8, 16, 24, 32, 40, 48, 56, 64, 96, 104, 112, 120, 0x88, 0xff])
        drop = rng.random() < 0.6
        present = rng.random() < 0.9
        ka = rng.choice([8, 0x19, 0x1a, 2, 0, 6, rng.randrange(0, 256)])
        kb = rng.choice([0x2b, 0, rng.randrange(0, 256)])
        ty = rng.choice([2, 2, 1, 0, rng.randrange(0, 256)])
        if ka in (8, 0x19, 0x1a) and (b[6] & 0xf) < 6:
            b[6] = (b[6] & 0xf0) | rng.randrange(6, 16)   # the pentagram lookups are not reproduced
        socket = rng.random() < 0.3
        pos = [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.uniform(-100, 500))]
        code_i = mu_code = (b[0] | ((b[3] & 0x80) << 1) | ((b[5] & 0xf0) << 5) | ((b[5] & 1) << 13))
        pool = am.undefined_region('pool', base, STRIDE, 0x51)
        inputs = am.defined_region('inputs', 0x21000000, bytes(b) + b'\0' + struct.pack('<3f', *pos), writable=False)
        rec = am.undefined_region('record', REC, 0x2c4, 0x53)
        rec.define(REC+0x250, bytes([ka, kb, ty]))
        g = am.defined_region('global', 0x2a100000, b'\0'*0x100, writable=False)
        calls = []

        def code_ok(i):
            return 0 <= i <= 0x2c00

        def item_pred(field):
            def stub(mm):
                k = mm.argument(0) & 0xff
                ecx = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
                c = struct.unpack('<i', bytes(mm.uc.mem_read(ecx+0x10, 4)))[0]
                v = present and code_ok(c) and {'a': ka, 'b': kb, 't': ty}[field] == k
                return 0x5d00 | int(v), 4
            return stub

        def rec_stub(name, cleanup=0, argc=0, value=0):
            def stub(mm):
                calls.append((name,) + tuple(mm.argument(i) for i in range(argc)))
                return value, cleanup
            return stub

        def reset(mm):
            calls.append(('reset', mm.uc.reg_read(mm.x86.UC_X86_REG_ECX) - base))
            return 0

        def live(mm):
            calls.append(('live', mm.uc.reg_read(mm.x86.UC_X86_REG_ECX) - base, mm.argument(0)))
            return 0, 4

        def sound(mm):
            calls.append(('sound', mm.argument(0)))
            return 0

        def height(mm):
            return mm.x87_return(terrain_height(mm.float_argument(0), mm.float_argument(1)))

        def effect(mm):
            p = mm.floats(mm.argument(1), 3)
            calls.append(('effect', mm.argument(0), tuple(bits(x) for x in p), mm.argument(5) - base,
                          mm.argument(6) & 0xffff))
            return 0
        stubs = {0x00ac3bf7: lambda mm: 0x2a100000, 0x0097bbfd: lambda mm: 0x2a100040, 0x00ccc144: reset,
                 0x00ccc591: lambda mm: (REC if present else 0), 0x0095fc2e: item_pred('a'),
                 0x00987982: item_pred('b'), 0x0095fbeb: item_pred('t'),
                 0x00cd1534: lambda mm: int(socket), SOUND: sound, 0x0129f4a5: live,
                 0x016da00b: lambda mm: (calls.append(('attr', mm.argument(0) - base)) or 0),
                 0x01802a66: lambda mm: (calls.append(('angle', mm.argument(0) - base)) or 0),
                 0x017ea422: lambda mm: (calls.append(('name', mm.argument(0) - base)) or 0),
                 TERRAIN: height, 0x013c0eaa: effect}
        r = m.execute_regions(CREATE_ITEM, [base, 0x21000000, 0x21000010, int(drop)], [pool, inputs, rec, g], stubs)
        raw = r['regions'].get('pool', b'')
        # C side
        poison = bytes(am.poison(STRIDE, 0x51))
        it = Item()
        fill_struct(it.data, ITEM_FIELDS, poison, 4)
        fill_struct(it.object, OBJ_FIELDS, poison, 0x130)
        mine = []
        hc = HostCase(rng)
        hc.height = None
        hc.heights = lambda x, y: terrain_height(x, y)
        records = {mu_code: (ka, kb, ty, 'X', 0)} if present else {}
        hc.records = records
        host = hc.host(socket_like=lambda c: socket)
        host.play_sound = SOUND_FN(lambda ctx, i: mine.append(('sound', i)))
        keep = [host.play_sound]
        item_base = ctypes.addressof(it)
        off_obj = Item.object.offset
        off_data = Item.data.offset

        def c_reset(ctx, d):
            mine.append(('reset', 4))

        def c_live(ctx, o, v):
            mine.append(('live', 0x130, v))
            o.contents.live = v

        def c_attr(ctx, o):
            mine.append(('attr', 0x130))

        def c_angle(ctx, o):
            mine.append(('angle', 0x130))

        def c_name(ctx, i):
            mine.append(('name', 0))

        def c_effect(ctx, t, p, o, sub):
            mine.append(('effect', t, tuple(bits(p[k]) for k in range(3)), 0x130, sub))
        hooks = CreateHooks(None, RESET_FN(c_reset), LIVE_FN(c_live), OBJ_FN(c_attr), OBJ_FN(c_angle),
                            ITEM_FN(c_name), EFFECT_FN(c_effect), PENTA_FN(0))
        keep.append(hooks)
        res = lib.mu_gi_create(ctypes.byref(it), bytes(b), (ctypes.c_float*3)(*pos), int(drop), ctypes.byref(host),
                               ctypes.byref(hooks))
        mismatch = None
        if vc.ok(r):
            # SetLive is a stub on the client side: apply its write before comparing
            raw = bytearray(raw)
            if any(c[0] == 'live' for c in calls):
                raw[0x130] = 1
            if calls != mine:
                mismatch = ('calls', calls, mine)
            if mismatch is None:
                mismatch = compare_fields(it.data, ITEM_FIELDS, bytes(raw), 4, 'item.')
            if mismatch is None:
                mismatch = compare_fields(it.object, OBJ_FIELDS, bytes(raw), 0x130, 'object.')
            if mismatch is None:
                extra = written_outside(r['defined_before']['pool'], r['defined_after']['pool'], covered)
                if extra:
                    mismatch = ('unmodelled writes', extra)
        report.add('create', vc.ok(r) and mismatch is None,
                   {'case': n, 'code': hex(code_i), 'bytes': bytes(b).hex(), 'drop': drop, 'present': present,
                    'kinds': (ka, kb, ty), 'socket': socket, 'mismatch': mismatch, 'stopped': r['stopped'],
                    'error': r['error'], 'checks': r['checks']})
        report.cover('create', ('no record' if not present else f'type {it.object.type:#x}' if code_i in
                                SPECIAL_CODES else 'plain') + (' drop' if drop else ''))
        if vc.ok(r) and mismatch is None and drop and present:
            # negative control: every drop plays the plain drop sound 0x1e
            sounds = [c[1] for c in calls if c[0] == 'sound']
            negatives['create_one_sound'] += sounds != [0x1e]


# --------------------------------------------------------------------------
# viewport

def family_viewport(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        count = rng.choice([0, 1, 2, 5, 20, 74, 75, 76, 90, rng.randrange(0, 256)])
        stored = min(count, 75)
        entries = []
        for _ in range(stored):
            key = rng.choice([rng.randrange(0, 1000), rng.randrange(1000, 0x8000), 999, 1000, 0x7fff])
            if rng.random() < 0.5:
                key |= 0x8000
            code = rng.choice([0x1c0f, rng.randrange(0, 0x2c00)])
            entries.append(bytes([key >> 8, key & 0xff, rng.randrange(0, 256), rng.randrange(0, 256)]) +
                           bytes(item_bytes(rng, code)))
        packet = bytes([0xc2, 0, 0, 0x20, count & 0xff]) + b''.join(entries)
        window = rng.random() < 0.7
        view = rng.choice([0, 1])
        pk = am.defined_region('packet', 0x21000000, packet + b'\0'*16, writable=False)
        pool = am.undefined_region('pool', POOL, STRIDE*1000, 0x55)
        win = am.defined_region('window', 0x28000000, b'\0'*0x5c + bytes([view]) + b'\0'*0x23, writable=False)
        g = am.defined_region('global', 0x2a100000, b'\0'*0x100, writable=False)
        calls = []

        def lock(mm):
            out = mm.argument(0)
            wr(mm, out, struct.pack('<II', 0x28000000 if window else 0, 0))
            return out, 4

        def reset(mm):
            calls.append(('reset', (mm.uc.reg_read(mm.x86.UC_X86_REG_ECX) - POOL - 4) // STRIDE))
            return 0

        def create(mm):
            item, src, p, flag = (mm.argument(i) for i in range(4))
            x, y = mm.floats(p, 2)
            calls.append(('create', (item - POOL) // STRIDE, src - 0x21000000, bits(x), bits(y), flag))
            return 0
        stubs = {0x009a19ae: lock, 0x00ccc144: reset, 0x016daa27: create, 0x00ac3bf7: lambda mm: 0x2a100000,
                 0x009617c6: lambda mm: (calls.append(('release',)) or 0)}
        r = m.execute_regions(VIEWPORT, [0x21000000], [pk, pool, win, g], stubs)
        out = (ViewportEntry*80)()
        k = lib.mu_gi_viewport_parse(packet + b'\0'*16, out, 80)
        mine = []
        pbase = ctypes.cast(ctypes.c_char_p(packet), ctypes.c_void_p).value
        buf = ctypes.create_string_buffer(packet + b'\0'*16, len(packet)+16)
        k = lib.mu_gi_viewport_parse(buf, out, 80)
        bufaddr = ctypes.addressof(buf)
        for i in range(k):
            e = out[i]
            mine.append(('reset', e.index))
            mine.append(('create', e.index, e.item - bufaddr, bits(e.x), bits(e.y), e.drop))
        mismatch = None
        if vc.ok(r):
            if calls != mine:
                mismatch = ('calls', calls[:6], mine[:6])
            else:
                raw = r['regions']['pool']
                last = {}
                for i in range(k):
                    last[out[i].index] = i
                for idx in last:
                    key = struct.unpack_from('<H', raw, idx*STRIDE)[0]
                    lv = raw[idx*STRIDE+0x508]
                    if key != idx or lv != (view if window else 1):
                        mismatch = ('pool', idx, key, lv)
                        break
        report.add('viewport', vc.ok(r) and mismatch is None,
                   {'case': n, 'count': count, 'window': window, 'mismatch': mismatch, 'stopped': r['stopped'],
                    'error': r['error'], 'checks': r['checks']})
        report.cover('viewport', f'{min(stored, 10)}+ entries' if stored >= 10 else f'{stored} entries')
        if vc.ok(r) and mismatch is None and count > 75:
            negatives['viewport_no_cap'] += 1


# --------------------------------------------------------------------------
# move

def family_move(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        live_count = rng.choice([1, 3, 8, 20])
        slots = sorted(rng.sample(range(1000), live_count))
        pool = am.undefined_region('pool', POOL, STRIDE*1000, 0x57)
        for i in range(1000):
            pool.define(POOL+STRIDE*i+0x130, b'\0')
        objs = {}
        for i in slots:
            o = POOL + STRIDE*i + 0x130
            t = rng.choice([0xae6, 0xae7, 0x16e5, 0x16e6, 0x18e5, 0x18e6, 0x26f5, rng.randrange(0x900, 0x3a00)])
            p = [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.uniform(50, 400))]
            grav = f32(rng.choice([20.0, 50.0, 2.0, -40.0, 0.0, rng.uniform(-100, 50)]))
            ang = [f32(rng.uniform(-360, 360)) for _ in range(3)]
            spk = rng.choice([1, 47, 48, 95, 96, 0, rng.randrange(0, 1000), -48])
            pool.define(o, b'\1')
            pool.define(o+0x5c, struct.pack('<ii', t, spk))
            pool.define(o+0xc8, struct.pack('<f', grav))
            pool.define(o+0x158, struct.pack('<6f', *p, *ang))
            objs[i] = (t, p, grav, ang, spk)
        hc = HostCase(rng)
        calls = []

        def height(mm):
            x, y = mm.float_argument(0), mm.float_argument(1)
            return mm.x87_return(terrain_height(x, y))

        def angle(mm):
            calls.append(('angle', (mm.argument(0) - POOL - 0x130) // STRIDE))
            return 0

        def particle(mm):
            t, pp, ap, lp, sub = (mm.argument(i) for i in range(5))
            calls.append(('particle', t, tuple(bits(x) for x in mm.floats(pp, 3)),
                          tuple(bits(x) for x in mm.floats(ap, 3)), tuple(bits(x) for x in mm.floats(lp, 3)), sub,
                          bits(mm.float_argument(5))))
            return 0
        stubs = hc.stubs()
        stubs.update({TERRAIN: height, ITEM_ANGLE: angle, 0x0168fafd: particle})
        r = m.execute_regions(MOVE_ITEMS, [], [pool], stubs)
        raw = r['regions'].get('pool', b'')
        # C side
        items = (Item*1000)()
        mine = []
        base_addr = ctypes.addressof(items)
        host = hc.host()
        hc.heights = lambda x, y: terrain_height(x, y)

        def c_angle(ctx, o):
            idx = (ctypes.addressof(o.contents) - base_addr - Item.object.offset) // ctypes.sizeof(Item)
            mine.append(('angle', idx))

        def c_particle(ctx, t, p, a, l, sub, scale):
            mine.append(('particle', t, tuple(bits(p[k]) for k in range(3)), tuple(bits(a[k]) for k in range(3)),
                         tuple(bits(l[k]) for k in range(3)), sub, bits(scale)))
        hooks = MoveHooks(None, OBJ_FN(c_angle), PARTICLE_FN(c_particle))
        mismatch = None
        for i in range(1000):
            if i in objs:
                t, p, grav, ang, spk = objs[i]
                o = items[i].object
                o.live, o.type, o.sparkle, o.gravity = 1, t, spk, grav
                for k in range(3):
                    o.position[k], o.angle[k] = p[k], ang[k]
            lib.mu_gi_move_item(ctypes.byref(items[i].object), ctypes.byref(host), ctypes.byref(hooks))
        if vc.ok(r):
            if calls != mine:
                mismatch = ('calls', calls[:4], mine[:4])
            elif hc.client_rand != hc.c_rand:
                mismatch = ('rand', hc.client_rand, hc.c_rand)
            else:
                fields = [f for f in OBJ_FIELDS if f[0] in ('position', 'angle', 'gravity', 'sparkle', 'type', 'live')]
                for i in objs:
                    mm_ = compare_fields(items[i].object, fields, raw, STRIDE*i+0x130, f'item {i} ')
                    if mm_:
                        mismatch = mm_
                        break
        report.add('move', vc.ok(r) and mismatch is None,
                   {'case': n, 'slots': slots[:5], 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                    'checks': r['checks']})
        report.cover('move', f"landed {sum(1 for c in calls if c[0] == 'angle')}/{live_count}")
        if vc.ok(r) and mismatch is None:
            # negative control: every item gets the weapon height bonus
            negatives['move_all_weapons'] += sum(1 for i in objs if not (0xae6 <= objs[i][0] < 0x16e6))


# --------------------------------------------------------------------------
# render

MODEL_ADDR, CONTAINER = 0x2b000000, 0x2b100000


def project(world):
    """Deterministic stand-in for 0x0184a244 (both sides)."""
    x, y, z = world
    if not all(math.isfinite(v) for v in (x, y, z)):
        return 0, 0
    return int(x / 40.0) % 640, int(y / 40.0 + z / 10.0) % 480


def family_render(m, lib, rng, cases, report, negatives):
    table = [rng.randrange(0, 360) for _ in range(100)]
    for n in range(cases):
        live_count = rng.choice([1, 2, 5])
        slots = sorted(rng.sample(range(1000), live_count))
        world = rng.choice([0, 0, 10, 0x84, 0x27, 7])
        wt = f32(rng.uniform(0, 1e6))
        world_float = rng.random() < 0.15
        w39 = rng.random() < 0.5
        special_h = f32(rng.uniform(0, 500))
        pool = am.undefined_region('pool', POOL, STRIDE*1000, 0x59)
        for i in range(1000):
            pool.define(POOL+STRIDE*i+0x130, b'\0')
        objs = {}
        for i in slots:
            b = POOL + STRIDE*i
            o = b + 0x130
            t = rng.choice([0x26f5, 0x26f5, 0x18e6, 0x1ae6, 0x1ce6, 0x1ee6, 0x20e6, 0x22e5, 0x26f2, 0x2318, 0x23a1,
                            0x34eb, 0xae6, rng.randrange(0x900, 0x3a00)])
            level = rng.choice([0, 8, 16, 0x78]) if t != 0x26f5 else rng.choice([1, 8, 9, 100, 25600, 30000, 999999])
            exc, anc = rng.choice([0, 0, 1, 0x40]), rng.choice([0, 5])
            p = [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 500))]
            ang = [f32(rng.uniform(-360, 360)) for _ in range(3)]
            head = [f32(rng.uniform(-10, 10)) for _ in range(3)]
            fr, pfr = f32(rng.uniform(0, 5)), f32(rng.uniform(0, 5))
            act, pact = rng.randrange(0, 4), rng.randrange(0, 4)
            alpha = f32(rng.choice([1.0, 0.5]))
            light = [f32(rng.choice([0.2, 1.5, 0.3])) for _ in range(3)]
            f18, f1c = rng.randrange(-5, 50), rng.randrange(-5, 50)
            visible = rng.random() < 0.8
            pose_ok, render_ok = rng.random() < 0.95, rng.random() < 0.95
            kind = rng.random() < 0.2
            code = t - 0xae6
            pool.define(b+4+0x10, struct.pack('<ii', code, level))
            pool.define(b+4+0x3a, bytes([exc, anc]))
            pool.define(o, b'\1')
            pool.define(o+0x18, struct.pack('<ii', f18, f1c))
            pool.define(o+0x2a, struct.pack('<HH', act, pact))
            pool.define(o+0x5c, struct.pack('<i', t))
            pool.define(o+0xd0, struct.pack('<ff', fr, pfr))
            pool.define(o+0xdc, struct.pack('<f', alpha))
            pool.define(o+0xec, struct.pack('<3f', *light))
            pool.define(o+0x158, struct.pack('<9f', *p, *ang, *head))
            objs[i] = dict(t=t, level=level, exc=exc, anc=anc, p=p, ang=ang, head=head, fr=fr, pfr=pfr, act=act,
                           pact=pact, alpha=alpha, light=light, f18=f18, f1c=f1c, visible=visible, pose_ok=pose_ok,
                           render_ok=render_ok, kind=kind)
        tl = [f32(rng.uniform(0, 1)) for _ in range(3)]
        hero_class = rng.randrange(0, 256)
        regions = [pool,
                   am.defined_region('table', RANDOM_TABLE, struct.pack('<100i', *table), writable=False),
                   am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
                   am.defined_region('time', TIME, struct.pack('<f', wt), writable=False),
                   am.defined_region('hero_ptr', HERO_POINTER, struct.pack('<I', 0x2c000000), writable=False),
                   am.defined_region('hero', 0x2c000000, b'\0'*0x12 + bytes([hero_class]) + b'\0'*0x2d,
                                     writable=False),
                   am.undefined_region('model', MODEL_ADDR, 0x100, 0x5b)]
        calls = []
        state = {'item': None, 'pose_phase': 0}
        hc = HostCase(rng, light=tl, world=world, world_time=wt)

        def item_of(ptr):
            return (ptr - POOL - 0x130 - 0x158) // STRIDE

        def frustum(mm):
            i = item_of(mm.argument(0))
            state['item'] = i
            state['pose_phase'] = 0
            calls.append(('frustum', i, bits(mm.float_argument(1))))
            return 0x7700 | int(objs[i]['visible'])

        def model_get(mm):
            t = mm.argument(0)
            i = state['item']
            ok = objs[i]['pose_ok'] if state['pose_phase'] == 0 else objs[i]['render_ok']
            state['pose_phase'] += 1
            calls.append(('model', t))
            return (MODEL_ADDR if ok else 0), 4

        def skin(mm):
            calls.append(('skin', mm.argument(0)))
            return 0x31

        def animation(mm):
            a = [mm.argument(i) for i in range(8)]
            calls.append(('anim', a[0], bits(mm.float_argument(1)), bits(mm.float_argument(2)), a[3],
                          a[4] - POOL - STRIDE*state['item'], a[5] - POOL - STRIDE*state['item'], a[6], a[7]))
            return 0, 0x20

        def tlight(mm):
            out = mm.argument(2)
            wr(mm, out, struct.pack('<3f', *tl))
            calls.append(('tlight', bits(mm.float_argument(0)), bits(mm.float_argument(1))))
            return 0

        def part(mm):
            a = [mm.argument(i) for i in range(16)]
            o = a[0]
            pos = mm.floats(o+0x158, 3)
            calls.append(('part', item_of(o+0x158), a[1], a[2], tuple(bits(x) for x in mm.floats(a[3], 3)),
                          a[4], a[5], a[6] & 0xff, a[7], tuple(a[8:16]), tuple(bits(x) for x in pos)))
            # a[6] is a byte local pushed as a dword (its upper bytes are stack contents)
            return 0

        def proj(mm):
            pos = mm.floats(mm.argument(0), 3)
            x, y = project(pos)
            wr(mm, mm.argument(1), struct.pack('<i', x))
            wr(mm, mm.argument(2), struct.pack('<i', y))
            calls.append(('project', tuple(bits(v) for v in pos)))
            return 0

        def kind(mm):
            ecx = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
            i = (ecx - POOL - 4) // STRIDE
            k = mm.argument(0)
            v = objs[i]['kind'] and k == 8
            return 0x5e00 | int(v), 4
        stubs = hc.stubs()
        stubs.update({0x016ccc14: frustum, 0x00966cc4: lambda mm: CONTAINER, 0x00eaa8cf: model_get,
                      0x0095f5cc: skin, 0x012b5064: animation, 0x016cb08d: tlight, 0x017e63f4: part,
                      0x0184a244: proj, 0x0095fc2e: kind, 0x009b0418: lambda mm: int(world_float),
                      0x009a6ef3: lambda mm: 0x2d000000, 0x009a645f: lambda mm: int(w39),
                      0x00deeb4e: lambda mm: mm.x87_return(special_h)})
        r = m.execute_regions(RENDER_ITEMS, [], regions, stubs)
        raw = r['regions'].get('pool', b'')
        # C side
        mine = []
        host = hc.host()
        tbl = (ctypes.c_int32*100)(*table)
        mismatch = None
        aborted = False
        screens = {}
        for i in sorted(objs):
            if aborted:
                break
            d = objs[i]
            it = Item()
            it.data.code, it.data.level, it.data.excellent, it.data.ancient = d['t'] - 0xae6, d['level'], d['exc'], \
                d['anc']
            o = it.object
            o.live, o.type, o.field_18, o.field_1c, o.action, o.prior_action = 1, d['t'], d['f18'], d['f1c'], \
                d['act'], d['pact']
            o.frame, o.prior_frame, o.alpha = d['fr'], d['pfr'], d['alpha']
            for k in range(3):
                o.position[k], o.angle[k], o.head_angle[k], o.light[k] = d['p'][k], d['ang'][k], d['head'][k], \
                    d['light'][k]

            cproj = []

            def c_project(ctx, w, x, y):
                pos = [w[0], w[1], w[2]]
                cproj.append(('project', tuple(bits(v) for v in pos)))
                px, py = project(pos)
                x[0], y[0] = px, py
            env = RenderEnv(int(d['visible']), int(d['pose_ok']), int(d['render_ok']), int(world_float), int(w39),
                            special_h, tbl, PROJECT_FN(c_project), None, int(d['kind']))
            plan = RenderPlan()
            lib.mu_gi_render_plan(ctypes.byref(it), i, ctypes.byref(host), ctypes.byref(env), ctypes.byref(plan))
            mine_i = [('frustum', i, bits(f32(400.0)))]
            if d['visible']:
                mine_i.append(('model', plan.pose_model))
                if plan.pose_model and d['pose_ok']:
                    mine_i.append(('skin', hero_class))
                    mine_i.append(('anim', 0x06fce398, bits(d['fr']), bits(d['pfr']), d['pact'], 0x130+0x164,
                                   0x130+0x170, 0, 0))
                    mine_i.append(('model', plan.render_model))
                    if d['render_ok']:
                        mine_i.append(('tlight', bits(d['p'][0]), bits(d['p'][1])))
                        for c in plan.calls[:plan.call_count]:
                            mine_i.append(('part', i, c.type, 0, tuple(bits(c.light[k]) for k in range(3)),
                                           bits(c.alpha), c.item_level, c.option, c.ext,
                                           (1, 1, 1, 0, 2, c.a12 & 0xffffffff, c.a13 & 0xffffffff, 0),
                                           tuple(bits(c.position[k]) for k in range(3))))
                if plan.abort:
                    aborted = True
            mine.extend(mine_i)
            mine.extend(cproj)      # the projection comes after the item's RenderPartObject calls
            screens[i] = (plan.visible, plan.screen_x, plan.screen_y, plan.call_count > 0)
        client = [c for c in calls if c[0] != 'height' and c[0] != 'sin' and c[0] != 'sqrt']
        if vc.ok(r):
            if client != mine:
                mismatch = ('calls', [c for c, d2 in zip(client, mine) if c != d2][:2],
                            [d2 for c, d2 in zip(client, mine) if c != d2][:2], len(client), len(mine))
            else:
                for i, (vis, sx, sy, drawn) in screens.items():
                    cv = raw[STRIDE*i+0x130+0xb]
                    if cv != vis:
                        mismatch = ('visible', i, cv, vis)
                        break
                    if drawn:
                        cx, cy = struct.unpack_from('<hh', raw, STRIDE*i+0x130+0x50)
                        if (cx, cy) != (sx, sy):
                            mismatch = ('screen', i, (cx, cy), (sx, sy))
                            break
        report.add('render', vc.ok(r) and mismatch is None,
                   {'case': n, 'world': world, 'slots': slots, 'types': [hex(objs[i]['t']) for i in slots],
                    'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('render', 'zen' if any(objs[i]['t'] == 0x26f5 for i in slots) else 'plain')
        if vc.ok(r) and mismatch is None:
            # negative control: one coin per zen pile
            negatives['render_one_coin'] += sum(1 for i in slots if objs[i]['t'] == 0x26f5 and objs[i]['visible']
                                                and objs[i]['pose_ok'] and objs[i]['render_ok'])


# --------------------------------------------------------------------------
# select

SELECT_POISON = bytes(am.poison(STRIDE*1000, 0x5d))


def family_select(m, lib, rng, cases, report, negatives):
    for n in range(cases):
        count = rng.choice([1, 3, 10, 40])
        slots = sorted(rng.sample(range(1000), count))
        pool = am.undefined_region('pool', POOL, STRIDE*1000, 0x5d)
        flags = {}
        for i in range(1000):
            pool.define(POOL+STRIDE*i+0x130, b'\0')
        for i in slots:
            live = rng.random() < 0.85
            vis = rng.random() < 0.8
            hit = rng.random() < 0.2
            o = POOL+STRIDE*i+0x130
            pool.define(o, bytes([int(live)]))
            pool.define(o+0xb, bytes([int(vis)]))
            flags[i] = (live, vis, hit)
        calls, current = [], [None]

        def copy(mm):
            src = mm.argument(0)
            current[0] = (src - POOL - 0x130 - 0x31c) // STRIDE
            return 0, 4

        def ray(mm):
            i = current[0]
            calls.append(('ray', i, mm.argument(0), mm.argument(1)))   # mouse ray origin and target, then the OBB
            return int(flags.get(i, (0, 0, 0))[2])
        r = m.execute_regions(SELECT_ITEM, [], [pool], {0x00ce3931: copy, 0x018500bf: ray})
        raw = r['regions'].get('pool', b'')
        items = (Item*1000)()
        for i, (live, vis, hit) in flags.items():
            items[i].object.live, items[i].object.visible = int(live), int(vis)
            for k in range(3):
                items[i].object.light[k] = struct.unpack_from('<f', SELECT_POISON, STRIDE*i+0x130+0xec+4*k)[0]
            items[i].object.light_enable = SELECT_POISON[STRIDE*i+0x130+5]
        mine = []

        def c_ray(ctx, i):
            mine.append(('ray', i, 0x0bdc5984, 0x0bdc5990))
            return int(flags.get(i, (0, 0, 0))[2])
        cb = RAY_FN(c_ray)
        res = lib.mu_gi_select(items, 1000, cb, None)
        mismatch = None
        if vc.ok(r):
            ce = r['eax'] - (1 << 32) if r['eax'] & 0x80000000 else r['eax']
            if ce != res:
                mismatch = ('result', ce, res)
            elif calls != mine:
                mismatch = ('rays', calls, mine)
            else:
                fields = [f for f in OBJ_FIELDS if f[0] in ('light', 'light_enable')]
                for i in flags:
                    mm_ = compare_fields(items[i].object, fields, raw, STRIDE*i+0x130, f'item {i} ')
                    if mm_:
                        mismatch = mm_
                        break
        report.add('select', vc.ok(r) and mismatch is None,
                   {'case': n, 'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                    'checks': r['checks']})
        report.cover('select', 'hit' if res >= 0 else 'none')
        if vc.ok(r) and mismatch is None and res >= 0:
            negatives['select_last_hit'] += sum(1 for i in flags if flags[i][0] and flags[i][1] and flags[i][2]) > 1


# --------------------------------------------------------------------------
# frustum

def family_frustum(m, lib, rng, cases, report, negatives):
    lib.mu_gi_test_frustum.argtypes = [ctypes.POINTER(ctypes.c_float*15), ctypes.POINTER(ctypes.c_float*5),
                                       ctypes.POINTER(ctypes.c_float*3), ctypes.c_float]
    lib.mu_gi_test_frustum.restype = ctypes.c_int32
    for n in range(cases):
        normals = []
        for _ in range(5):
            v = [rng.uniform(-1, 1) for _ in range(3)]
            length = math.sqrt(sum(x*x for x in v)) or 1.0
            normals += [f32(x/length) for x in v]
        dist = [f32(rng.uniform(-30000, 30000)) for _ in range(5)]
        pos = [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.uniform(-200, 800))]
        rng_range = f32(rng.choice([400.0, 400.0, 0.0, -80.0, rng.uniform(-1000, 1000)]))
        regions = [am.defined_region('normals', 0x0bdb546c, struct.pack('<15f', *normals), writable=False),
                   am.defined_region('distances', 0x0b6b53e4, struct.pack('<5f', *dist), writable=False),
                   am.defined_region('position', OBJ, struct.pack('<3f', *pos), writable=False)]
        r = m.execute(0x016ccc14, [OBJ, bits(rng_range)], regions, {})
        mine = lib.mu_gi_test_frustum((ctypes.c_float*15)(*normals), (ctypes.c_float*5)(*dist),
                                      (ctypes.c_float*3)(*pos), rng_range)
        client = r['eax'] & 0xff if vc.ok(r) else None
        report.add('frustum', vc.ok(r) and client == mine, {'case': n, 'client': client, 'c': mine,
                                                             'stopped': r['stopped'], 'error': r['error']})
        report.cover('frustum', 'visible' if mine else 'culled')
        if vc.ok(r):
            # negative control: the range ignored
            negatives['frustum_no_range'] += lib.mu_gi_test_frustum((ctypes.c_float*15)(*normals),
                                                                   (ctypes.c_float*5)(*dist),
                                                                   (ctypes.c_float*3)(*pos), 0.0) != client


# --------------------------------------------------------------------------
# monster_voice

class MonsterVoice(ctypes.Structure):
    _fields_ = [('object_type', ctypes.c_int32), ('object_kind', ctypes.c_int32), ('field_3324', ctypes.c_float),
                ('has_model', ctypes.c_int32), ('slots', ctypes.c_int16*10), ('world_voice', ctypes.c_uint8)]


def family_monster_voice(m, lib, rng, cases, report, negatives):
    """SetPlayerShock 0x0138f92f / SetPlayerDie 0x01393a61 for monsters (the model's sound slots)."""
    P = ctypes.POINTER
    clib = ctypes.CDLL(str(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))
    clib.mu_monster_shock.argtypes = [P(MonsterVoice), ctypes.c_int32, ctypes.c_int32, P(ctypes.c_int32),
                                      ctypes.c_int32, P(ctypes.c_int32), P(ctypes.c_int32)]
    clib.mu_monster_die.argtypes = [P(MonsterVoice), P(ctypes.c_int32), ctypes.c_int32, P(ctypes.c_int32),
                                    P(ctypes.c_int32)]
    alib = ctypes.CDLL(str(ROOT/f'reconstructed/actors/libactors.{SUFFIX}'))
    alib.mu_monster_sound_slots.argtypes = [ctypes.c_int32, P(ctypes.c_int16)]
    table_types = [t for t in range(0x259) if alib.mu_monster_sound_slots(t, (ctypes.c_int16*10)())]
    special_die = {0x7be, 0x7c3, 0x813, 0x818, 0x81b, 0x81c, 0x864, 0x887, 0x920, 0x2c1b}
    CHARACTER, MODEL = 0x2e000000, 0x2b000000
    for n in range(cases):
        kind = ('shock', 'die')[n % 2]
        mtype = rng.choice(table_types)
        otype = 0x7a5 + mtype if rng.random() < 0.9 else rng.choice([0x7b3, 0x7a5 + rng.randrange(0, 0x259)])
        if kind == 'die' and otype in special_die:
            otype = 0x7a5
        slots = (ctypes.c_int16*10)()
        alib.mu_monster_sound_slots(otype - 0x7a5, slots)
        if rng.random() < 0.2:
            for k in range(10):
                slots[k] = rng.choice([-1, rng.randrange(0, 60)])
        has_model = rng.random() < 0.9
        okind = rng.choice([0, 0, 2, 9, 0x422, 0x425, 0x428, rng.randrange(0, 0x500)])
        f3324 = f32(rng.choice([0.0, 0.0, 0.0, 0.001, -0.0, float('nan')]))
        world_voice = rng.random() < 0.15
        mclass = rng.choice([0, 0x2fb, rng.randrange(0, 0x400)])
        action_now = rng.choice([0, 1, 2, 3, 4, 5, 6, 8, 9])
        rands = [rng.choice([0, 1, 2, 3, 0x7fff, rng.randrange(0, 0x8000)]) for _ in range(6)]
        c = am.undefined_region('character', CHARACTER, 0x3400, 0x61)
        o = CHARACTER + 0x3254
        c.define(CHARACTER+0x23, b'\0')
        c.define(CHARACTER+0x146, struct.pack('<h', mclass))
        c.define(CHARACTER+0x3324, struct.pack('<f', f3324))
        c.define(CHARACTER+0x38, b'\x07')
        c.define(o+0x2a, struct.pack('<H', action_now))
        c.define(o+0x5c, struct.pack('<ii', otype, okind))
        model = am.undefined_region('model', MODEL, 0x100, 0x63)
        model.define(MODEL+0xb6, struct.pack('<10h', *slots))
        record, rand_index = [], [0]

        def rand(mm):
            v = rands[rand_index[0]] if rand_index[0] < len(rands) else 0
            rand_index[0] += 1
            return v

        def set_action(mm):
            record.append(('set_action', mm.argument(1)))
            return 0

        def sound(mm):
            record.append(('sound', mm.argument(0)))
            return 0
        stubs = {RAND: rand, 0x012affa4: set_action, SOUND: sound, 0x013a084d: lambda mm: 0,
                 0x00966cc4: lambda mm: CONTAINER, 0x00eaa8cf: lambda mm: ((MODEL if has_model else 0), 4),
                 0x009dacb8: lambda mm: 0xab00 | int(world_voice)}
        regions = [c, model, am.defined_region('world', WORLD, struct.pack('<i', 0), writable=False),
                   am.defined_region('hero', HERO_POINTER, struct.pack('<I', 0x05000000), writable=False)]
        if kind == 'shock':
            r = m.execute(0x0138f92f, [CHARACTER, rng.choice([1, 50, 999]), rng.choice([0, 1, 3])], regions, stubs)
        else:
            # the tail after the voice block (party and interface updates), as validate_skill_fx's
            # player_voice family stubs it
            for addr, cleanup in ((0x00a0361c, 4), (0x0095c50b, 4), (0x00a06d72, 0), (0x0095f144, 0),
                                  (0x00c71772, 0), (0x0095eb91, 0), (0x0095f6db, 0), (0x009a176b, 4),
                                  (0x009a19ae, 4), (0x009a1a3c, 0)):
                stubs[addr] = (lambda mm, k=cleanup: (0x0b000000, k))
            stubs[0x009a1a51] = lambda mm: 0
            r = m.execute(0x01393a61, [CHARACTER], regions, stubs)
        v = MonsterVoice(otype, okind, f3324, int(has_model), slots, int(world_voice))
        act, snd = ctypes.c_int32(), ctypes.c_int32()
        arr = (ctypes.c_int32*6)(*rands)
        if kind == 'shock':
            used = clib.mu_monster_shock(ctypes.byref(v), mclass, action_now, arr, 6, ctypes.byref(act),
                                         ctypes.byref(snd))
        else:
            used = clib.mu_monster_die(ctypes.byref(v), arr, 6, ctypes.byref(act), ctypes.byref(snd))
        mine = ([('set_action', act.value)] if act.value >= 0 else []) + \
            ([('sound', snd.value)] if snd.value >= 0 else [])
        client = [x for x in record if x[0] in ('set_action', 'sound')]
        equal = vc.ok(r) and client == mine and rand_index[0] == used
        if equal and kind == 'die':
            after = struct.unpack('<f', r['regions']['character'][0x3324:0x3328])[0]
            marked = f3324 == 0.0 and (world_voice or has_model)   # without a model it returns before the store
            equal = same(after, f32(0.001) if marked else f3324)
        report.add('monster_voice', equal, {'case': n, 'kind': kind, 'type': hex(otype), 'okind': okind,
                                            'client': client, 'c': mine, 'rand': [rand_index[0], used],
                                            'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('monster_voice', kind + ' ' + ' '.join(hex(x[1]) for x in client if x[0] == 'sound'))
        if vc.ok(r) and equal and snd.value >= 0xd2 and kind == 'shock':
            # negative control: the hurt sound taken from slot 0 (the idle sound)
            negatives['monster_idle_slot'] += snd.value != 0xd2 + (5 if okind == 9 else 0) + slots[0]


FAMILIES = [('item_angle', family_item_angle), ('label_color', family_label_color),
            ('object_attr', family_object_attr), ('name', family_name), ('create', family_create),
            ('viewport', family_viewport), ('move', family_move), ('render', family_render),
            ('select', family_select), ('frustum', family_frustum), ('monster_voice', family_monster_voice)]
NEGATIVES = ['angle_no_record', 'color_shifted', 'attr_scale_one', 'name_no_level', 'create_one_sound',
             'viewport_no_cap', 'move_all_weapons', 'render_one_coin', 'select_last_hit', 'frustum_no_range', 'monster_idle_slot']


def default_evidence(relative):
    local = ROOT/'evidence'/relative
    if local.exists():
        return str(local)
    return str(Path.home()/'Documents/main-exe-study/evidence'/relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default=default_evidence('x86-text-capture-09/client-text.bin'))
    parser.add_argument('--data', default=default_evidence('image-data-run10/data-capture-10/client-image-data.bin'))
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/items/libclient_items.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=300)
    parser.add_argument('--heavy-cases', type=int, default=None, help='cases of the pool families')
    parser.add_argument('--only', action='append')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lib = load_library(args.library)
    m = Machine(text, data)
    m.data_bytes = data
    m.uc.mem_write(PATCHED_SITE, PATCHED_BYTES)    # the runtime-patched compare (see the docstring)
    bodies = {name: {'start': hex(a), 'end': hex(b),
                     'sha256': hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    report = Report()
    negatives = {k: 0 for k in NEGATIVES}
    timing = {}
    for name, family in FAMILIES:
        if args.only and name not in args.only:
            continue
        rng = random.Random(f'{args.seed}-{name}')
        cases = args.cases if name not in HEAVY else (args.heavy_cases or max(1, args.cases//10))
        start = time.time()
        family(m, lib, rng, cases, report, negatives)
        timing[name] = round(time.time()-start, 2)
    all_equal = all(f['cases'] == f['equal'] for f in report.families.values())
    result = {'coverage': report.coverage, 'nan_pairs_equal': vc.NAN_COUNT[0], 'text_sha256': am.TEXT_SHA256,
              'data_sha256': am.DATA_SHA256, 'bodies': bodies, 'patched_site': {
                  'address': hex(PATCHED_SITE), 'written': PATCHED_BYTES.hex(),
                  'capture': text[PATCHED_SITE-am.TEXT_BASE:PATCHED_SITE-am.TEXT_BASE+7].hex()},
              'families': report.families, 'negative_controls': negatives, 'seconds': timing,
              'all_equal': all_equal}
    summary = {k: f"{v['equal']}/{v['cases']}" for k, v in report.families.items()}
    print(json.dumps({'summary': summary, 'negative_controls': negatives, 'seconds': timing,
                      'all_equal': all_equal}, indent=1))
    for k, v in report.families.items():
        if v['first_failures']:
            print(k, json.dumps(v['first_failures'][:2], default=str)[:4000])
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, default=str))
    return 0 if all_equal else 1


HEAVY = {'move', 'render', 'select', 'viewport'}

if __name__ == '__main__':
    sys.exit(main())
