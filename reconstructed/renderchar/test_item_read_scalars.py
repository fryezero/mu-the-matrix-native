"""Authored instruction fixtures for the later body-scalar reader."""
import struct
import unittest
from unittest import mock

import test_renderchar  # sets the scripts import path
import gen_item_bodies as gen
import validate_renderchar as v


class ReadScalars(unittest.TestCase):
    def fixture(self, phase=0.7, clamp=True):
        start, data = 0x401000, bytearray(64)
        def constant(offset, value):
            struct.pack_into('<f', data, offset, value)
            return struct.pack('<I', 0x1a7c000 + offset)
        phase_at, a_at, floor_at = constant(0, phase), constant(4, -4), constant(8, 0.4)
        code = b'\x51\xf3\x0f\x10\x05' + phase_at + gen.MOVSS_ESP
        code += b'\x51\xf3\x0f\x10\x05' + a_at + gen.MOVSS_ESP
        ret = start + len(code) + 5
        code += b'\xe8' + struct.pack('<i', gen.WAVE_HELPER - ret)
        code += b'\x59\x59\xd9\x9d' + struct.pack('<i', -0x100)
        if clamp:
            code += b'\xf3\x0f\x10\x05' + floor_at
            code += b'\x0f\x2f\x85' + struct.pack('<i', -0x100)
            code += b'\x76\x10\xf3\x0f\x10\x05' + floor_at
            code += b'\xf3\x0f\x11\x85' + struct.pack('<i', -0x100)
        return (code + b'\x90' * 64, bytes(data)), ret

    def test_phase_and_clamp_are_separate_from_the_period(self):
        wa, ret = self.fixture()
        program = gen.parse_scalar(wa, gen.WAVE_HELPER, ret)
        self.assertEqual(program, (9, v.f2u(-4), ((5, v.f2u(0.7)), (6, v.f2u(0.4)))))
        self.assertEqual(gen.scalar_value(program, 0), v.f2u(0.4))
        self.assertNotEqual(gen.scalar_value(program, 500), gen.scalar_value(program, 0))

    def test_clamp_requires_the_same_destination_and_branch_end(self):
        wa, ret = self.fixture()
        code = bytearray(wa[0])
        # A neighbouring local is not a clamp of the saved wave result.
        store = code.index(b'\xf3\x0f\x11\x85', ret - 0x401000)
        struct.pack_into('<i', code, store + 4, -0x104)
        program = gen.parse_scalar((bytes(code), wa[1]), gen.WAVE_HELPER, ret)
        self.assertEqual(program[2], ((5, v.f2u(0.7)),))

    def test_wave_phase_must_be_an_absolute_constant(self):
        wa, ret = self.fixture()
        code = bytearray(wa[0])
        code[4:8] = struct.pack('<I', 0x6fce370)
        self.assertIsNone(gen.parse_scalar((bytes(code), wa[1]), gen.WAVE_HELPER, ret))

    def test_integer_local_division_keeps_the_signed_quotient(self):
        with mock.patch.object(gen, '_local_stored', return_value=True):
            ops = ((gen.C_I_ADD, ('i', ('quotient', ('e', -4, 1, 0), 2))),)
            self.assertEqual(gen.resolve_clock(None, ops, {-4: -5}), ((gen.C_I_ADD, 0xfffffffffffffffe),))

    def test_the_two_absolute_helpers_keep_distinct_signed_zero(self):
        conditional = ((gen.C_TIME_F, 0), (gen.C_F_ABS, 0))
        crt = ((gen.C_TIME_F, 0), (gen.C_F_FABS, 0))
        self.assertEqual(gen.clock_value(conditional, -0.0), 0x80000000)
        self.assertEqual(gen.clock_value(crt, -0.0), 0)


if __name__ == '__main__':
    unittest.main()
