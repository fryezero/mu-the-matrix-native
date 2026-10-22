"""Synthetic worked examples for the recovered mix and jewel rules."""
import ctypes as C
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from validate_mix import native, Target, Values, source, condition, recipe, put, SUFFIX


class MixRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/mix')], check=True, capture_output=True)
        cls.lib = native(ROOT/f'reconstructed/mix/libmix.{SUFFIX}')

    def test_jewel_level_boundaries_and_mix_window_gate(self):
        t = Target(1, 5, 0, 1, 0, 0, 100, 0)
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c0d, C.byref(t), 0), 1)
        t.level = 6
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c0d, C.byref(t), 0), 0)
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c0e, C.byref(t), 0), 1)
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c0e, C.byref(t), 1), 0)
        t.level = 9
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c0e, C.byref(t), 0), 0)

    def test_life_option_and_period_boundary(self):
        t = Target(1, 15, 3, 3, 0, 0, 1, 0)
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c10, C.byref(t), 1), 1)
        t.option = 4
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c10, C.byref(t), 0), 0)
        t.option = 0
        t.period = 1
        self.assertEqual(self.lib.mu_jewel_allowed(0x1c10, C.byref(t), 0), 0)

    def test_consumption_preserves_unmatched_items_on_failed_recipe(self):
        r = bytes(recipe([condition(10), condition(20)]))
        s = C.create_string_buffer(bytes(source(10) + source(99)))
        self.assertEqual(self.lib.mu_mix_ready(s, 2, r), 0)
        self.assertEqual(struct.unpack_from('<i', s.raw, 0x24)[0], 0)
        self.assertEqual(struct.unpack_from('<i', s.raw, 100+0x24)[0], 1)

    def test_repeated_recipe_and_excess_quantity(self):
        r = recipe([condition(10, 1, 1)])
        s = bytes(source(10, 2))
        self.assertEqual(self.lib.mu_mix_ready(C.create_string_buffer(s), 1, bytes(r)), 0)
        r[0x15b] = 2
        self.assertEqual(self.lib.mu_mix_repeats(s, 1, bytes(r)), 2)
        self.assertEqual(self.lib.mu_mix_ready(C.create_string_buffer(s), 1, bytes(r)), 1)

    def test_required_flags_and_exact_socket_bit(self):
        c = condition(1)
        s = source(1)
        put(s, 0x2c, 0x41)
        put(c, 0x44, 1)
        self.assertEqual(self.lib.mu_mix_matches(bytes(s), bytes(c)), 0)
        put(c, 0x44, 0x41)
        self.assertEqual(self.lib.mu_mix_matches(bytes(s), bytes(c)), 1)
        put(c, 0x44, 0xc1)
        self.assertEqual(self.lib.mu_mix_matches(bytes(s), bytes(c)), 0)

    def test_rate_expression_precedence_and_malformed_input(self):
        r = recipe([])
        tokens = [(0, 10), (1, 0), (0, 5), (3, 0), (0, 3)]
        put(r, 0x44, len(tokens))
        for j, (kind, value) in enumerate(tokens):
            struct.pack_into('<If', r, 0x48+j*8, kind, value)
        out, at = C.c_float(), C.c_int32()
        self.assertEqual(self.lib.mu_mix_formula(bytes(r), C.byref(Values()), C.byref(out), C.byref(at)), 1)
        self.assertEqual((out.value, at.value), (25, 5))
        put(r, 0x44, 33)
        self.assertEqual(self.lib.mu_mix_formula(bytes(r), C.byref(Values()), C.byref(out), C.byref(at)), 0)
        for tokens in ([(5,0),(0,42)],[(0,42),(1,0)],[(0,42),(6,0)],[(0,42),(0,1)],[(7,0),(0,42)]):
            put(r,0x44,len(tokens))
            for j,(kind,value) in enumerate(tokens):struct.pack_into('<If',r,0x48+j*8,kind,value)
            self.assertEqual(self.lib.mu_mix_formula(bytes(r),C.byref(Values()),C.byref(out),C.byref(at)),0)

    def test_truncation_has_defined_x86_overflow_result(self):
        r=recipe([])
        put(r,0x44,4)
        for j,(t,v) in enumerate([(7,0),(5,0),(0,2147483648.),(6,0)]):struct.pack_into('<If',r,0x48+j*8,t,v)
        out,at=C.c_float(),C.c_int32()
        self.assertEqual(self.lib.mu_mix_formula(bytes(r),C.byref(Values()),C.byref(out),C.byref(at)),1)
        self.assertEqual((out.value,at.value),(-2147483648.,4))

    def test_nonfinite_intermediate_is_rejected_before_truncation(self):
        r=recipe([])
        out,at=C.c_float(),C.c_int32()
        for operator in (1,3):
            tokens=[(7,0),(5,0),(0,3e38),(operator,0),(0,3e38),(6,0)]
            put(r,0x44,len(tokens))
            for j,(kind,value) in enumerate(tokens):struct.pack_into('<If',r,0x48+j*8,kind,value)
            self.assertEqual(self.lib.mu_mix_formula(bytes(r),C.byref(Values()),C.byref(out),C.byref(at)),0)

    def test_client_rate_wrap_and_cost_modes(self):
        # The unsigned subtraction wraps and the final clamp produces 100.
        self.assertEqual(self.lib.mu_mix_rate(0, 90, 0, 0, 1, 0, 0, 1), 100)
        self.assertEqual(self.lib.mu_mix_rate(80, 70, 10, 25, 0, 1, 1, 0), 100)
        self.assertEqual(self.lib.mu_mix_cost(ord('A'), 100, 3, 70), 300)
        self.assertEqual(self.lib.mu_mix_cost(ord('B'), 100, 3, 70), 21000)

    def test_unsupported_harmony_summary_is_rejected(self):
        it, record = bytearray(300), bytearray(708)
        put(it, 0x10, 1)
        struct.pack_into('<H', it, 0x6e, 1)
        self.assertEqual(self.lib.mu_mix_source_make(C.create_string_buffer(100), bytes(it), bytes(record), 1), 0)

    def test_kind_37_is_equipment_but_not_compound_equipment(self):
        it,record=bytearray(300),bytearray(708)
        put(it,0x10,1);it[0x3b]=1
        out=C.create_string_buffer(100)
        for kind,compound in ((0x37,0),(0x38,1),(0x2d,1)):
            record[0x250]=kind
            self.assertEqual(self.lib.mu_mix_source_make(out,bytes(it),bytes(record),1),1)
            self.assertEqual((out.raw[0x3c],out.raw[0x44]),(1,compound))

    def test_bad_recipe_count_is_rejected(self):
        r = recipe([])
        put(r, 0x39c, 9)
        self.assertEqual(self.lib.mu_mix_ready(C.create_string_buffer(bytes(source())), 1, bytes(r)), 0)


if __name__ == '__main__':
    unittest.main()
