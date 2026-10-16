"""Synthetic and public-vector checks for the observed LEA context layout."""
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def encrypt_from_context(plaintext, context):
    """Independent consumer checks key order through public encryption vectors."""
    words = struct.unpack('<193I', context)
    def rol(value, bits):
        return ((value << bits) | (value >> (32-bits))) & 0xffffffff
    output = bytearray()
    for offset in range(0, len(plaintext), 16):
        a, b, c, d = struct.unpack_from('<4I', plaintext, offset)
        for index in range(words[192]):
            k = words[6*index:6*index+6]
            a, b, c, d = (rol(((a ^ k[0])+(b ^ k[1])) & 0xffffffff, 9),
                          rol(((b ^ k[2])+(c ^ k[3])) & 0xffffffff, 27),
                          rol(((c ^ k[4])+(d ^ k[5])) & 0xffffffff, 29), a)
        output.extend(struct.pack('<4I', a, b, c, d))
    return bytes(output)


class ClientLeaKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.library = HERE/('libmodelcodec.dylib' if sys.platform == 'darwin' else 'libmodelcodec.so')
        cls.setup = ctypes.CDLL(str(cls.library)).mu_client_lea_setup
        cls.setup.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        cls.setup.restype = None

    def test_null_and_unsupported_sizes_do_not_access_caller_memory(self):
        for size in (-2147483648, -1, 0, 15, 16, 17, 23, 24, 25, 31, 32, 33, 2147483647):
            self.setup(None, 1, size)
            self.setup(1, None, size)
            if size not in (16, 24, 32):
                self.setup(1, 1, size)

    def test_round_count_unused_tail_and_guards_for_all_alignments(self):
        for size, rounds in ((16, 24), (24, 28), (32, 32)):
            for context_alignment in range(4):
                for key_alignment in range(4):
                    context = ctypes.create_string_buffer(b'\xa5'*800, 800)
                    key = ctypes.create_string_buffer(b'\x5a'*key_alignment+bytes(range(size))+b'guard')
                    before = key.raw
                    start = 8+context_alignment
                    self.setup(ctypes.addressof(context)+start,
                               ctypes.addressof(key)+key_alignment, size)
                    self.assertEqual(context.raw[:start], b'\xa5'*start)
                    self.assertEqual(context.raw[start+4*rounds*6:start+768], b'\xa5'*(768-4*rounds*6))
                    self.assertEqual(struct.unpack_from('<I', context.raw, start+768)[0], rounds)
                    self.assertEqual(context.raw[start+772:], b'\xa5'*(800-start-772))
                    self.assertEqual(key.raw, before)

    def test_public_vectors_consume_forward_schedule(self):
        fixture = json.loads((ROOT/'model-recovery/fixtures/lea256-vectors.json').read_text())
        fixture['vectors'].extend([
            {'key': '07AB6305B025D83F79ADDAA63AC8AD00',
             'plaintext': 'F28AE3256AAD23B415E028063B610C60',
             'ciphertext': '64D908FCB7EBFEF90FD670106DE7C7C5'},
            {'key': '1437AF533069BD7525C1560C78BAD2A1E534671C007EF27C',
             'plaintext': '1CB4F4CB6C4BDB5168EA8409727BFD51',
             'ciphertext': '69725C6DF912F8B70EB511E6663C5870'}])
        for vector in fixture['vectors']:
            context = ctypes.create_string_buffer(772)
            key = ctypes.create_string_buffer(bytes.fromhex(vector['key']))
            self.setup(context, key, len(bytes.fromhex(vector['key'])))
            self.assertEqual(encrypt_from_context(bytes.fromhex(vector['plaintext']), context.raw),
                             bytes.fromhex(vector['ciphertext']))

    def test_first_round_for_zero_key_all_supported_sizes(self):
        # Hand-calculated from public delta C3EFE9DB and rotations 1,3,6,11,13,17.
        expanded = (0x87dfd3b7, 0x3efe9dbc, 0xefe9dbc3, 0xfa76f0fb, 0xd3b787df, 0x76f0fbfa)
        for size, expected in ((16, (expanded[0], expanded[1], expanded[2], expanded[1], expanded[3], expanded[1])),
                               (24, expanded), (32, expanded)):
            context = ctypes.create_string_buffer(772)
            self.setup(context, ctypes.create_string_buffer(size), size)
            self.assertEqual(struct.unpack_from('<6I', context.raw), expected)

    def test_validator_refuses_unpinned_text_before_emulator_or_library(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not captured client instructions')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_client_lea_key.py'),
                                     '--text', str(text), '--library', '/nonexistent/library'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)
            self.assertNotIn('No module named', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private captured LEA setup instruction comparison is opt-in')
    def test_private_captured_setup_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'comparison.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_client_lea_key.py'),
                            '--text', str(text), '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertEqual(report['mismatches'], 0)
            self.assertGreater(report['instruction_cases'], 1000)
            self.assertGreater(report['wrong_schedule_mismatches'], 1000)
            self.assertEqual(report['supported_key_bytes'], [16, 24, 32])


if __name__ == '__main__':
    unittest.main()
