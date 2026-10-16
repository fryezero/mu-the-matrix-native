import ctypes
import importlib.util
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = Path(__file__).parent / ('librecord_math.dylib' if sys.platform == 'darwin' else 'librecord_math.so')


def identity():
    return [1.0 if row == column else 0.0 for row in range(4) for column in range(4)]


def validator():
    spec = importlib.util.spec_from_file_location('validate_record_math', ROOT / 'scripts/validate_record_math.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = ctypes.CDLL(str(LIBRARY))
        cls.inverse = cls.library.mu_record_inverse
        cls.inverse.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cls.inverse.restype = None
        cls.cofactor = cls.library.mu_record_cofactor
        cls.cofactor.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
        cls.cofactor.restype = ctypes.c_float
        if cls.library.mu_record_math_environment_supported() != 1:
            raise AssertionError('Record math requires binary32/binary64 and round-to-nearest')

    def transform(self, values, inplace=False):
        source = ctypes.create_string_buffer(struct.pack('<16f', *values))
        output = source if inplace else ctypes.create_string_buffer(64)
        self.inverse(output, source)
        return output.raw[:64]

    def test_identity_cofactors_cover_every_removed_row_and_column(self):
        source = ctypes.create_string_buffer(struct.pack('<16f', *identity()))
        for row in range(4):
            for column in range(4):
                self.assertEqual(self.cofactor(source, row, column), 1.0 if row == column else 0.0)

    def test_diagonal_reciprocals(self):
        source, expected = [0.0] * 16, [0.0] * 16
        for index, value in enumerate((2.0, 4.0, 8.0, 16.0)):
            source[index*5], expected[index*5] = value, 1.0/value
        self.assertEqual(list(struct.unpack('<16f', self.transform(source))), expected)

    def test_permutation_inverse_can_be_in_place(self):
        source = [0.0] * 16
        for row, column in enumerate((1, 2, 0, 3)):
            source[row*4+column] = 1.0
        expected = [source[column*4+row] for row in range(4) for column in range(4)]
        self.assertEqual(list(struct.unpack('<16f', self.transform(source, True))), expected)

    def test_zero_scalar_fallback_uses_template_then_negated_translation(self):
        source = [0.0] * 16
        source[12:15] = [2.0, -3.0, 4.0]
        expected = identity()
        expected[12:15] = [-2.0, 3.0, -4.0]
        self.assertEqual(self.transform(source), struct.pack('<16f', *expected))

    def test_in_place_fallback_reads_translation_after_template_write(self):
        source = [0.0] * 16
        source[12:15] = [2.0, -3.0, 4.0]
        expected = identity()
        expected[12:15] = [-0.0, -0.0, -0.0]
        self.assertEqual(self.transform(source, True), struct.pack('<16f', *expected))

    def test_unaligned_disjoint_buffers_preserve_all_guard_bytes(self):
        values = identity()
        data = bytearray(bytes((0xa5,)) * 256)
        data[1:65] = struct.pack('<16f', *values)
        arena = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        pointer = ctypes.addressof(arena)
        self.inverse(pointer+99, pointer+1)
        self.assertEqual(bytes(arena)[:99], data[:99])
        self.assertEqual(bytes(arena)[163:], data[163:])
        self.assertEqual(list(struct.unpack('<16f', bytes(arena)[99:163])), values)

    def test_validator_rejects_wrong_text_and_manifest_without_private_inputs(self):
        module = validator()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'synthetic-text'
            source.write_bytes(b'authored synthetic input')
            with self.assertRaisesRegex(ValueError, 'pinned restored client'):
                module.load_inputs(source, root)
            (root / 'capture.json').write_text('{"complete_within_scope": false}')
            with patch.object(module, 'TEXT_BYTES', source.stat().st_size), patch.object(
                    module, 'TEXT_SHA256', module.hashlib.sha256(source.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'verified capture profile'):
                    module.load_inputs(source, root)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private record-arithmetic comparison is opt-in')
    def test_private_captured_record_arithmetic_matches(self):
        module = validator()
        capture = Path(os.environ.get('MU_CLIENT_TEXT', ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_MATH_DATA', ROOT / 'evidence/x86-math-capture-09'))
        result = module.validate(capture, data, LIBRARY)
        self.assertEqual(result['mismatches'], 0)
        self.assertGreaterEqual(result['inverse_cases'], 500)
        self.assertGreaterEqual(result['cofactor_cases'], 1000)


if __name__ == '__main__':
    unittest.main()
