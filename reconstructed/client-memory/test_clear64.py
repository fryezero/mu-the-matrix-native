import ctypes
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = Path(__file__).parent / ('libclient_memory.dylib' if sys.platform == 'darwin' else 'libclient_memory.so')


def validator():
    spec = importlib.util.spec_from_file_location('validate_client_clear', ROOT / 'scripts/validate_client_clear.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Clear64Tests(unittest.TestCase):
    def test_all_cacheline_alignments_preserve_surrounding_bytes_and_return(self):
        library = ctypes.CDLL(str(LIBRARY))
        clear = library.mu_clear64
        clear.argtypes = [ctypes.c_void_p]
        clear.restype = ctypes.c_void_p
        data = bytes(range(256)) * 2
        for offset in range(128, 192):
            with self.subTest(offset=offset):
                arena = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
                pointer = ctypes.addressof(arena) + offset
                self.assertEqual(clear(pointer), pointer)
                self.assertEqual(bytes(arena), data[:offset] + bytes(64) + data[offset+64:])

    def test_validator_rejects_unpinned_input(self):
        module = validator()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-capture'
            path.write_bytes(bytes(module.TEXT_BYTES))
            with self.assertRaisesRegex(ValueError, 'pinned restored client text'):
                module.validate(path, Path(directory) / 'missing-library')

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private restored-code comparison is opt-in')
    def test_private_scalar_and_sse_paths_match_captured_instructions(self):
        path = Path(os.environ.get('MU_CLIENT_TEXT', ROOT / 'evidence/x86-capture-text-08/client-text.bin'))
        result = validator().validate(path, LIBRARY)
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['cases'], 768)
        self.assertEqual(result['feature_branch_entries'], ['0x194cdc7', '0x194ce05'])
        self.assertEqual(result['unexpected_memory_accesses'], [])


if __name__ == '__main__':
    unittest.main()
