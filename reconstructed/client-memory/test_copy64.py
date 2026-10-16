import ctypes
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = Path(__file__).parent / ('libclient_memory.dylib' if sys.platform == 'darwin' else 'libclient_memory.so')


class Copy64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = ctypes.CDLL(str(LIBRARY))
        cls.copy = cls.library.mu_copy64_forward_words
        cls.copy.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cls.copy.restype = ctypes.c_void_p

    def invoke(self, data, source, destination):
        arena = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        pointer = ctypes.addressof(arena)
        result = self.copy(pointer + destination, pointer + source)
        self.assertEqual(result, pointer + destination)
        return bytes(arena)

    def test_disjoint_unaligned_copy_preserves_surrounding_bytes(self):
        data = bytes(range(192))
        expected = bytearray(data)
        expected[97:161] = data[3:67]
        self.assertEqual(self.invoke(data, 3, 97), expected)

    def test_identical_source_and_destination(self):
        data = bytes(range(128))
        self.assertEqual(self.invoke(data, 17, 17), data)

    def test_overlap_toward_lower_addresses(self):
        data = bytes(range(128))
        expected = bytearray(data)
        expected[3:67] = data[7:71]
        self.assertEqual(self.invoke(data, 7, 3), expected)

    def test_overlap_toward_higher_addresses_repeats_the_first_word(self):
        data = bytes(range(128))
        expected = bytearray(data)
        expected[8:72] = data[4:8] * 16
        self.assertEqual(self.invoke(data, 4, 8), expected)

    def test_subword_overlap_reads_each_complete_word_before_writing(self):
        data = bytes(range(128))
        expected = bytearray(data)
        expected[1:65] = bytes((0, 1, 2, 3)) + b''.join(
            bytes((3 + 4*i, 5 + 4*i, 6 + 4*i, 7 + 4*i)) for i in range(15))
        self.assertEqual(self.invoke(data, 0, 1), expected)

    def test_validator_rejects_unpinned_inputs_before_loading_a_library(self):
        spec = importlib.util.spec_from_file_location('validate_client_copy', ROOT / 'scripts/validate_client_copy.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-capture'
            for data in (b'short input', bytes(module.TEXT_BYTES)):
                path.write_bytes(data)
                with self.assertRaisesRegex(ValueError, 'pinned restored client text'):
                    module.validate(path, Path(directory) / 'missing-library')

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private restored-code comparison is opt-in')
    def test_private_captured_instructions_match_reconstruction(self):
        spec = importlib.util.spec_from_file_location('validate_client_copy', ROOT / 'scripts/validate_client_copy.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        capture = Path(os.environ.get('MU_CLIENT_TEXT', ROOT / 'evidence/x86-capture-text-08/client-text.bin'))
        result = module.validate(capture, LIBRARY)
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['cases'], 393)


if __name__ == '__main__':
    unittest.main()
