"""HelpWindow reader fixtures are authored, never installed/decoded game data."""
import ctypes
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = 512 * 136


def encode(rows):
    payload = b''.join(bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(row))
                       for row in rows)
    value, key = 0xc4f7 << 9, 0xc4f7
    for offset in range(0, len(payload), 4):
        word = struct.unpack_from('<I', payload, offset)[0]
        value = value ^ word if ((offset // 4) + key) % 2 == 0 else (value + word) & 0xffffffff
        if offset % 16 == 0:
            value ^= ((key + value) & 0xffffffff) >> ((offset // 4) % 8 + 1)
    return payload + struct.pack('<I', value)


def fixture():
    rows = [bytearray(136) for _ in range(512)]
    for i in range(511):
        struct.pack_into('<iBB', rows[i], 0, (i % 3) + 1, i % 14, i % 4)
        rows[i][6:14] = b'Test key'
        rows[i][70:80] = b'Test label'
    # Inactive row 511 still contains bytes which the reader must copy.
    rows[-1][-1] = 0xa5
    return b''.join(rows), encode(rows)


def build_library(directory, sources=None):
    output = Path(directory) / ('libhelp.dylib' if sys.platform == 'darwin' else 'libhelp.so')
    sources = sources or [ROOT/'reconstructed/help/help.c', ROOT/'reconstructed/data/data_tables.c',
                          ROOT/'reconstructed/data/data_codec.c']
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Wconversion', '-fPIC', '-shared', '-I', str(ROOT/'reconstructed/help'),
                    '-I', str(ROOT/'reconstructed/data'), *map(str, sources), '-o', str(output)],
                   check=True, capture_output=True)
    return output


def library(path):
    lib = ctypes.CDLL(str(path))
    lib.mu_help_decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
    lib.mu_help_decode.restype = ctypes.c_int
    lib.mu_help_read.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.mu_help_read.restype = ctypes.c_int
    return lib


class HelpReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='mu-help-')
        cls.lib = library(build_library(cls.work.name))
        cls.decoded, cls.encoded = fixture()

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def read(self, image):
        out = ctypes.create_string_buffer(b'\xa5' * PAYLOAD, PAYLOAD)
        path = Path(self.work.name)/'helpdata.bmd'
        if image is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(image)
        status = self.lib.mu_help_read(out, os.fsencode(path))
        return status, out.raw

    def test_valid_and_trailing(self):
        for suffix in (b'', b'ignored tail'):
            self.assertEqual(self.read(self.encoded + suffix), (0, self.decoded))

    def test_truncated(self):
        for length in (0, 1, 135, PAYLOAD - 1, PAYLOAD, PAYLOAD + 1, PAYLOAD + 3):
            with self.subTest(length=length):
                self.assertEqual(self.read(self.encoded[:length]), (2, bytes(PAYLOAD)))

    def test_corrupted(self):
        for offset in (0, 135, 136, PAYLOAD - 1, PAYLOAD, PAYLOAD + 3):
            image = bytearray(self.encoded)
            image[offset] ^= 1
            with self.subTest(offset=offset):
                self.assertEqual(self.read(image), (3, bytes(PAYLOAD)))

    def test_missing_clears_previous_rows(self):
        self.assertEqual(self.read(self.encoded)[0], 0)
        self.assertEqual(self.read(None), (1, bytes(PAYLOAD)))

    def test_bad_arguments(self):
        out = ctypes.create_string_buffer(b'\xa5' * PAYLOAD, PAYLOAD)
        self.assertEqual(self.lib.mu_help_decode(out, None, 0), 6)
        self.assertEqual(out.raw, bytes(PAYLOAD))
        self.assertEqual(self.lib.mu_help_read(None, None), 6)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction inputs opt-in')
    def test_original_instructions(self):
        output = Path(self.work.name)/'report.json'
        subprocess.run([sys.executable, str(ROOT/'scripts/validate_help.py'), '--cases', '4',
                        '--mutants', '--output', str(output)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
