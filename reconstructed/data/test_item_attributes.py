"""Synthetic checks for the Item.bmd attributes and table layouts (NATIVE-DATA-002).

An independent Python model of the reconstructed client routines (maximum
durability 0x00ccc5b0, warehouse ban 0x016bec14, repair ban 0x016be1d9) and of
the record field offsets is compared with reconstructed/data via ctypes over
random synthetic records. No game data is used. The comparison against the
client's actual instructions is scripts/validate_item_fields.py (run by
tests/test_data_tables_private.py with MU_RECOVERY_INTEGRATION=1).
"""
import ctypes
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent

U8, U16, U32 = ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint32
# (name, offset, ctype, count) in mu_item_attributes order
FIELDS = [('code', 0x000, U32, 1), ('section', 0x004, U16, 1), ('index', 0x006, U16, 1),
          ('kind_a', 0x250, U8, 1), ('kind_b', 0x251, U8, 1), ('type', 0x252, U8, 1), ('two_handed', 0x253, U8, 1),
          ('level', 0x254, U16, 1), ('slot', 0x256, U8, 1), ('skill', 0x258, U16, 1), ('width', 0x25a, U8, 1),
          ('height', 0x25b, U8, 1), ('damage_min', 0x25c, U16, 1), ('damage_max', 0x25e, U16, 1),
          ('defense_rate', 0x260, U8, 1), ('defense', 0x262, U16, 1), ('magic_defense', 0x264, U16, 1),
          ('attack_speed', 0x266, U8, 1), ('walk_speed', 0x267, U8, 1), ('durability', 0x268, U8, 1),
          ('set_defense_tier', 0x26a, U16, 1), ('magic_durability', 0x26c, U8, 1), ('magic_power', 0x270, U32, 1),
          ('combat_power', 0x274, U32, 1), ('attack_success_rate', 0x278, U32, 1),
          ('require_strength', 0x27c, U16, 1), ('require_dexterity', 0x27e, U16, 1),
          ('require_energy', 0x280, U16, 1), ('require_vitality', 0x282, U16, 1), ('require_command', 0x284, U16, 1),
          ('require_level', 0x286, U16, 1), ('value', 0x288, U8, 1), ('zen', 0x28c, U32, 1),
          ('set_attribute', 0x290, U8, 1), ('require_class', 0x291, U8, 16), ('resistance', 0x2a1, U8, 7),
          ('can_drop', 0x2a8, U8, 1), ('can_trade', 0x2a9, U8, 1), ('can_personal_store', 0x2aa, U8, 1),
          ('can_warehouse', 0x2ab, U8, 1), ('can_sell', 0x2ac, U8, 1), ('high_value', 0x2ad, U8, 1),
          ('can_repair', 0x2ae, U8, 1), ('max_stack', 0x2af, U8, 1), ('pc_room', 0x2b0, U8, 1),
          ('evolved_pet', 0x2b1, U8, 1), ('stat_option_melee', 0x2b2, U16, 1), ('stat_option_ranged', 0x2b4, U16, 1),
          ('stat_option_magic', 0x2b6, U16, 1), ('pentagram_grade', 0x2b8, U8, 1), ('field_2b9', 0x2b9, U8, 1),
          ('field_2ba', 0x2ba, U8, 1), ('elemental_attack', 0x2bc, U16, 1),
          ('elemental_defense_bonus', 0x2be, U16, 1), ('elemental_defense', 0x2c0, U16, 1)]


class Attributes(ctypes.Structure):
    _fields_ = [(n, t*c if c > 1 else t) for n, _, t, c in FIELDS]


class State(ctypes.Structure):
    _fields_ = [('code', ctypes.c_int32), ('level', ctypes.c_int32), ('ancient', U8), ('period', U8),
                ('expired', U8), ('excellent', U8)]


class Field(ctypes.Structure):
    _fields_ = [('offset', U16), ('type', U8), ('evidence', U8), ('count', U16), ('stride', U16), ('flags', U8),
                ('name', ctypes.c_char_p)]


class Layout(ctypes.Structure):
    _fields_ = [('file', ctypes.c_char_p), ('record_size', U32), ('fields', ctypes.POINTER(Field)),
                ('field_count', U32)]


WIDTH = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4, 8: 1, 9: 1}
STAFF_KINDS = {0x0c, 0x0d, 0x0e, 0x4e, 0x54, 0x59, 0x5a, 0x72, 0x73}
SPECIAL_255 = {0x1a04, 0x1a05, 0x28f7, 0x28f8, 0x28f9, 0x28fa, 0x2900}


def model_max_durability(r, code, level, excellent, ancient):
    in_range = 0 <= code <= 0x2c00
    kind_b, durability = r[0x251], r[0x268]
    if in_range and kind_b == 0x2b:
        return durability
    d = r[0x26c] if in_range and kind_b in STAFF_KINDS else durability
    level &= 15
    if 1 <= level <= 4:
        d += level
    elif 5 <= level <= 9:
        d += level*2-4
    elif level >= 10:
        d += level*2-4+(level-9)*(level-8)//2
    if code in SPECIAL_255:
        d = 255
    if (in_range and ancient) or (in_range and kind_b == 0x79):
        d += 20
    elif in_range and excellent:
        d += 15
    if in_range and r[0x252] == 4:
        d = 255
    return min(d, 255)


def model_store_ban(r, code, level, period):
    if period:
        return 1
    if (code == 0x1a14 and level != 0) or (code == 0x1c0b and level == 13):
        return 1
    if code == 0x1c15 and level == 3:
        return 0
    return int(r[0x2ab] == 0)


def model_repair_ban(r, code, period, expired):
    if 0 <= code <= 0x2c00 and r[0x251] == 0x2b:
        return 1
    if period and expired:
        return 1
    return int(r[0x2ae] == 0)


class ItemAttributeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        lib = cls.lib = ctypes.CDLL(str(HERE/('libdatatables.dylib' if sys.platform == 'darwin' else 'libdatatables.so')))
        lib.mu_item_attributes_read.argtypes = [ctypes.c_char_p, ctypes.POINTER(Attributes)]
        for name in ('mu_item_max_durability', 'mu_item_store_ban', 'mu_item_repair_ban'):
            getattr(lib, name).argtypes = [ctypes.POINTER(Attributes), ctypes.POINTER(State)]
            getattr(lib, name).restype = ctypes.c_int
        lib.mu_record_layouts.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
        lib.mu_record_layouts.restype = ctypes.POINTER(Layout)
        lib.mu_record_layout_find.argtypes = [ctypes.c_char_p]
        lib.mu_record_layout_find.restype = ctypes.POINTER(Layout)

    def records(self, count=400, seed=0x2c4):
        rng = random.Random(seed)
        for i in range(count):
            record = bytearray(rng.randrange(256) for _ in range(708))
            if i % 5 == 1:
                record[0x251] = rng.choice(sorted(STAFF_KINDS | {0x2b, 0x79}))
            if i % 7 == 2:
                record[0x252] = 4
            code = rng.choice([rng.randrange(0x2c00), *SPECIAL_255, 0x1a14, 0x1c0b, 0x1c15, 0x2c00, 0x2c01, -3])
            struct.pack_into('<i', record, 0, code)
            yield code, bytes(record)

    def attributes(self, record):
        out = Attributes()
        self.lib.mu_item_attributes_read(record, ctypes.byref(out))
        return out

    def test_attribute_offsets(self):
        for _, record in self.records(60):
            a = self.attributes(record)
            for name, offset, ctype, count in FIELDS:
                width = ctypes.sizeof(ctype)
                values = [int.from_bytes(record[offset+i*width:offset+(i+1)*width], 'little') for i in range(count)]
                got = list(getattr(a, name)) if count > 1 else [getattr(a, name)]
                self.assertEqual(got, values, name)

    def test_derived_routines_match_model(self):
        checks = 0
        for code, record in self.records():
            a = self.attributes(record)
            for level in range(16):
                for excellent, ancient in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    state = State(code, level, 1 if ancient else 0, 0, 0, excellent)
                    got = self.lib.mu_item_max_durability(ctypes.byref(a), ctypes.byref(state)) & 0xff
                    self.assertEqual(got, model_max_durability(record, code, level, excellent, ancient))
                    checks += 1
            for level in (0, 3, 13):
                for period, expired in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    state = State(code, level, 0, period, expired, 0)
                    self.assertEqual(self.lib.mu_item_store_ban(ctypes.byref(a), ctypes.byref(state)),
                                     model_store_ban(record, code, level, period))
                    self.assertEqual(self.lib.mu_item_repair_ban(ctypes.byref(a), ctypes.byref(state)),
                                     model_repair_ban(record, code, period, expired))
        self.assertGreater(checks, 20000)

    def test_ancient_bits_and_excellent_flag(self):
        record = bytearray(708)
        record[0x268] = 10
        a = self.attributes(bytes(record))
        for bits, want in ((0x01, 30), (0x10, 30), (0x33, 30), (0x04, 10), (0xcc, 10)):
            state = State(5, 0, bits, 0, 0, 0)
            self.assertEqual(self.lib.mu_item_max_durability(ctypes.byref(a), ctypes.byref(state)), want, hex(bits))
        state = State(5, 0, 0, 0, 0, 2)  # 0x00cd0995(1) tests the flag for == 1
        self.assertEqual(self.lib.mu_item_max_durability(ctypes.byref(a), ctypes.byref(state)), 10)

    def test_layout_catalog(self):
        count = ctypes.c_size_t()
        layouts = self.lib.mu_record_layouts(ctypes.byref(count))
        self.assertGreaterEqual(count.value, 20)
        files = set()
        for i in range(count.value):
            layout = layouts[i]
            files.add(layout.file.decode())
            previous = -1
            names = set()
            for k in range(layout.field_count):
                f = layout.fields[k]
                width = WIDTH[f.type]
                span = f.count if f.type in (8, 9) else (f.stride or width)*(f.count-1)+width
                self.assertGreaterEqual(f.offset, previous, (layout.file, f.name))
                self.assertLessEqual(f.offset+span, layout.record_size, (layout.file, f.name))
                self.assertIn(f.evidence, (1, 2, 3))
                self.assertNotIn(f.name, names)
                names.add(f.name)
                if not f.stride:
                    previous = f.offset+span
                else:
                    previous = f.offset
        self.assertIn('item.bmd', files)
        item = self.lib.mu_record_layout_find(b'ITEM.BMD')
        self.assertEqual(item.contents.record_size, 708)
        self.assertFalse(self.lib.mu_record_layout_find(b'absent.bmd'))


if __name__ == '__main__':
    unittest.main()
