"""Authored fixtures for the client-linked rolling BMD decoder."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


class ModelCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        library = HERE / ('libmodelcodec.dylib' if sys.platform == 'darwin' else 'libmodelcodec.so')
        cls.decode = ctypes.CDLL(str(library)).mu_bmd12_decode
        cls.decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        cls.decode.restype = ctypes.c_int32

    def test_query_returns_signed_length_without_accessing_source(self):
        for length in (-2147483648, -1, 0, 1, 2147483647):
            with self.subTest(length=length):
                self.assertEqual(self.decode(None, None, length), length)

    def test_nonpositive_length_preserves_destination_without_source(self):
        for length in (-2147483648, -1, 0):
            buffer = ctypes.create_string_buffer(b'untouched')
            before = buffer.raw
            self.assertEqual(self.decode(buffer, None, length), length)
            self.assertEqual(buffer.raw, before)

    def test_disjoint_feedback_uses_ciphertext(self):
        source = ctypes.create_string_buffer(b'\x00\x01')
        target = ctypes.create_string_buffer(b'xxGUARD')
        self.assertEqual(self.decode(target, source, 2), 2)
        self.assertEqual(target.raw, b'\x73\x35GUARD\x00')
        self.assertEqual(source.raw, b'\x00\x01\x00')

    def test_in_place_feedback_rereads_the_written_source(self):
        buffer = ctypes.create_string_buffer(b'\x00\x01GUARD')
        self.assertEqual(self.decode(buffer, buffer, 2), 2)
        self.assertEqual(buffer.raw, b'\x73\xc2GUARD\x00')

    def test_forward_overlap_reads_modified_upcoming_input(self):
        buffer = ctypes.create_string_buffer(b'\x00\x01xGUARD')
        self.assertEqual(self.decode(ctypes.addressof(buffer)+1, buffer, 2), 2)
        self.assertEqual(buffer.raw, b'\x00\x73\xc3GUARD\x00')

    def test_disjoint_roundtrip_crosses_every_key_index_and_byte_value(self):
        key = bytes.fromhex('d17352f6d29acb273eaf593137b3e7a2')
        plain = bytes(range(256))*2
        cipher = bytearray()
        previous = 0x5e
        # Published inverse encoding, independent of the decoder implementation.
        for index, value in enumerate(plain):
            encoded = ((value+previous) & 255) ^ key[index % 16]
            cipher.append(encoded)
            previous = (encoded+0x3d) & 255
        source = ctypes.create_string_buffer(bytes(cipher))
        target = ctypes.create_string_buffer(len(plain))
        self.assertEqual(self.decode(target, source, len(plain)), len(plain))
        self.assertEqual(target.raw, plain)

    def test_validator_refuses_unpinned_input_without_private_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'not-client-text.bin'
            path.write_bytes(b'authored invalid capture')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_model_codec.py'),
                                     '--text', str(path), '--library', '/nonexistent/library'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)
            self.assertNotIn('No module named', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private client-code and installed v12 comparison is opt-in')
    def test_private_captured_instructions_and_installed_v12_models(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'comparison.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_model_codec.py'),
                            '--text', str(text), '--game-root', os.environ['MU_GAME_ROOT'],
                            '--output', str(output)], check=True, capture_output=True, text=True)
            import json
            report = json.loads(output.read_text())
            self.assertEqual(report['mismatches'], 0)
            self.assertEqual(report['installed_v12']['files'], 180)
            self.assertGreater(report['synthetic_instruction_cases'], 1000)


if __name__ == '__main__':
    unittest.main()
