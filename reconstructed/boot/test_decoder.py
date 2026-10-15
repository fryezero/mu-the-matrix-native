"""Tests API failure behavior and compares real decoded blocks to pinned evidence."""
import ctypes
import hashlib
import json
import pathlib
import os
import platform
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class DecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        darwin = platform.system() == 'Darwin'
        library = pathlib.Path(cls.temp.name) / ('decoder.dylib' if darwin else 'decoder.so')
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        *(['-dynamiclib'] if darwin else ['-shared', '-fPIC']), str(HERE / 'decoder.c'),
                        '-o', str(library)], check=True)
        cls.lib = ctypes.CDLL(str(library))
        cls.decode = cls.lib.mu_decode_block
        cls.decode.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                               ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
                               ctypes.POINTER(ctypes.c_size_t)]
        cls.decode.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_decode(self, data, capacity):
        source = ctypes.create_string_buffer(data)
        target = ctypes.create_string_buffer(max(capacity, 1))
        consumed, written = ctypes.c_size_t(), ctypes.c_size_t()
        code = self.decode(source, len(data), target, capacity,
                           ctypes.byref(consumed), ctypes.byref(written))
        return code, consumed.value, written.value, target.raw[:written.value]

    def test_literal_and_terminator(self):
        self.assertEqual(self.run_decode(b'A\xc0\0', 1), (0, 3, 1, b'A'))

    def test_overlapping_backward_copy(self):
        self.assertEqual(self.run_decode(b'A\xd8\x02\0', 3), (0, 4, 3, b'AAA'))

    def test_rejects_truncated_or_invalid_reference(self):
        for data in [b'', b'A', b'A\xc0', b'A\xc0\x04']:
            with self.subTest(data=data):
                self.assertEqual(self.run_decode(data, 10)[0], -1)

    def test_rejects_output_overflow(self):
        self.assertEqual(self.run_decode(b'A\xc0\0', 0)[0], -1)
        self.assertEqual(self.run_decode(b'A\xd8\x02\0', 2)[0], -1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires private executable and local evidence')
    def test_four_original_blocks_match_independent_reference(self):
        report = json.loads((ROOT / 'evidence/loader-recovery/recovery.json').read_text())
        source = (ROOT / 'input/main.exe').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), report['input_sha256_before'])
        self.assertEqual(len(report['chunks']), 4)
        for block in report['chunks']:
            start, end = block['compressed_file_start'], block['compressed_file_end_exclusive']
            code, consumed, written, output = self.run_decode(source[start:end], block['decoded_bytes'])
            with self.subTest(block=block['index']):
                self.assertEqual(code, 0)
                self.assertEqual(consumed, end - start)
                self.assertEqual(written, block['decoded_bytes'])
                self.assertEqual(hashlib.sha256(output).hexdigest(), block['sha256'])


if __name__ == '__main__':
    unittest.main()
