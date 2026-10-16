"""Public vectors and synthetic batch/alias checks for client-linked ECB."""
import ctypes
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


class ClientLeaDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        lib = ctypes.CDLL(str(HERE/('libmodelcodec.dylib' if sys.platform == 'darwin' else 'libmodelcodec.so')))
        cls.setup = lib.mu_client_lea_setup
        cls.setup.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        cls.setup.restype = None
        cls.decode = lib.mu_client_lea_decode
        cls.decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
        cls.decode.restype = None

    def context(self, key=bytes(range(32))):
        context = ctypes.create_string_buffer(772)
        self.setup(context, ctypes.create_string_buffer(key), len(key))
        return context

    def test_public_vectors_decrypt_through_context(self):
        vectors = json.loads((ROOT/'model-recovery/fixtures/lea256-vectors.json').read_text())['vectors']
        vectors += [
            {'key': '07AB6305B025D83F79ADDAA63AC8AD00', 'plaintext': 'F28AE3256AAD23B415E028063B610C60',
             'ciphertext': '64D908FCB7EBFEF90FD670106DE7C7C5'},
            {'key': '1437AF533069BD7525C1560C78BAD2A1E534671C007EF27C',
             'plaintext': '1CB4F4CB6C4BDB5168EA8409727BFD51', 'ciphertext': '69725C6DF912F8B70EB511E6663C5870'}]
        for vector in vectors:
            cipher = bytes.fromhex(vector['ciphertext'])
            source = ctypes.create_string_buffer(cipher)
            output = ctypes.create_string_buffer(len(cipher))
            self.decode(output, source, len(cipher), self.context(bytes.fromhex(vector['key'])))
            self.assertEqual(output.raw, bytes.fromhex(vector['plaintext']))

    def test_noop_gates_do_not_read_context_or_caller_spans(self):
        for length in (0, 1, 15, 16, 17, 0xffffffff):
            self.decode(1, 1, length, None)
            self.decode(None, 1, length, 1)
            self.decode(1, None, length, 1)
            if length == 0 or length % 16:
                self.decode(1, 1, length, 1)

    def test_batch_snapshots_and_forward_overlap(self):
        context = self.context()
        original = bytes(range(256))*4
        for length in (16, 32, 48, 64, 80, 112, 128, 144, 192, 208, 240, 256, 272):
            for displacement in (-129, -65, -17, -1, 0, 1, 15, 16, 63, 64, 127, 128):
                expected = bytearray(original)
                source, target = 256, 256+displacement
                offset = 0
                while offset < length:
                    remaining = length-offset
                    batch = 128 if remaining >= 128 else 64 if remaining >= 64 else 16
                    # Independent model: a disjoint decode snapshots one batch,
                    # then writes it before reading the following batch.
                    saved = ctypes.create_string_buffer(bytes(expected[source+offset:source+offset+batch]))
                    decoded = ctypes.create_string_buffer(batch)
                    self.decode(decoded, saved, batch, context)
                    expected[target+offset:target+offset+batch] = decoded.raw
                    offset += batch
                arena = ctypes.create_string_buffer(original, len(original))
                self.decode(ctypes.addressof(arena)+target, ctypes.addressof(arena)+source, length, context)
                self.assertEqual(arena.raw, bytes(expected), (length, displacement))

    def test_disjoint_batch_boundaries_equal_single_block_reference(self):
        for key_size in (16, 24, 32):
            context = self.context(bytes(range(key_size)))
            for length in (16, 48, 64, 80, 112, 128, 144, 192, 240, 256, 272):
                source = ctypes.create_string_buffer(bytes(range(256))*2)
                output = ctypes.create_string_buffer(length)
                self.decode(output, source, length, context)
                reference = bytearray()
                for offset in range(0, length, 16):
                    block = ctypes.create_string_buffer(16)
                    self.decode(block, ctypes.addressof(source)+offset, 16, context)
                    reference.extend(block.raw)
                self.assertEqual(output.raw, bytes(reference))

    def test_validator_refuses_unpinned_text_before_optional_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not the restored client')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_client_lea_decode.py'),
                                     '--text', str(text), '--library', '/nonexistent/library'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)
            self.assertNotIn('No module named', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private scalar decoder instruction comparison is opt-in; AVX requires guest')
    def test_private_scalar_instructions_and_relocation_checks(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'comparison.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_client_lea_decode.py'),
                            '--text', str(text), '--game-root', os.environ['MU_GAME_ROOT'],
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertEqual(report['mismatches'], 0)
            self.assertEqual(report['scalar_instruction_cases'], 1152)
            self.assertEqual(len(report['relocation_checks']), 4)
            self.assertFalse(report['avx_helpers_executed'])
            self.assertEqual(report['installed_v15']['native_reader_matches'], 11583)
            self.assertFalse(report['installed_v15']['original_instructions_executed_for_corpus'])


if __name__ == '__main__':
    unittest.main()
