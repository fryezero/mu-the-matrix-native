import ctypes
import hashlib
import json
import os
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from bmd10 import BmdError, obj_text
from bmd_encrypted import decrypt_modulus, modulus_reader, parse_model


VECTORS = json.loads((Path(__file__).parent / 'fixtures/modulus-v14-vectors.json').read_text())


def envelope(vector):
    cipher = bytes.fromhex(vector['envelope_hex'])
    return b'BMD\x0e' + struct.pack('<I', len(cipher)) + cipher


class ModulusModels(unittest.TestCase):
    def test_independent_oracle_vectors_cover_all_cipher_pairs_and_windows(self):
        pairs = set()
        for vector in VECTORS['vectors']:
            with self.subTest(name=vector['name']):
                cipher = bytes.fromhex(vector['envelope_hex'])
                if vector['kind'] == 'model':
                    expected = bytes.fromhex(VECTORS['plaintexts'][vector['plaintext_id']]['hex'])
                    pairs.add((cipher[0] & 7, cipher[1] & 7))
                else:
                    expected = bytes((i * 37 + 11) % 256 for i in range(vector['body_bytes']))
                self.assertEqual(hashlib.sha256(expected).hexdigest(), vector['plaintext_sha256'])
                self.assertEqual(decrypt_modulus(cipher), expected)
        self.assertEqual(pairs, {(i, j) for i in range(8) for j in range(8)})
        self.assertEqual(len(VECTORS['vectors']), 91)

    def test_model_vectors_reach_checked_geometry_and_preserve_identity(self):
        for vector in VECTORS['vectors']:
            if vector['kind'] != 'model':
                continue
            with self.subTest(name=vector['name']):
                raw = envelope(vector)
                model = parse_model(raw)
                self.assertEqual(model['version'], 14)
                self.assertEqual(model['source_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(model['decoded_payload_sha256'], vector['plaintext_sha256'])
                self.assertEqual(model['parsed_bytes'], vector['body_bytes'] + 4)
                self.assertEqual(model['modulus']['inner_selector'], raw[8])
                self.assertEqual(model['modulus']['outer_selector'], raw[9])
                self.assertEqual(model['modulus']['inner_algorithm'], raw[8] & 7)
                self.assertIn('v 1 2 3\n', obj_text(model))
                self.assertIn('f 1/1/1 2/2/2 3/3/3\n', obj_text(model))

    def test_incomplete_prefix_and_mismatched_declared_length_rejected(self):
        for length in range(34):
            with self.subTest(prefix_bytes=length), self.assertRaises(BmdError):
                parse_model(b'BMD\x0e' + struct.pack('<I', length) + b'\0' * length)
        raw = envelope(VECTORS['vectors'][0])
        for invalid in (raw[:-1], raw + b'x', raw[:4] + struct.pack('<I', len(raw) - 42) + raw[8:]):
            with self.subTest(size=len(invalid)), self.assertRaises(BmdError):
                parse_model(invalid)

    def test_corrupt_header_counts_do_not_bypass_structural_validation(self):
        raw = bytearray(envelope(VECTORS['vectors'][0]))
        raw[74] ^= 0x80
        with self.assertRaises(BmdError):
            parse_model(raw)

    def test_native_buffer_contract_rejects_invalid_inputs_without_writing(self):
        function = modulus_reader()
        cipher = bytes.fromhex(VECTORS['vectors'][0]['envelope_hex'])
        source = ctypes.create_string_buffer(cipher)
        output = ctypes.create_string_buffer(b'unchanged')
        error = ctypes.create_string_buffer(256)
        for pointer, size, destination, capacity in (
                (None, len(cipher), output, len(output)),
                (source, 33, output, len(output)),
                (source, 128 * 1024 * 1024 + 1, output, len(output)),
                (source, len(cipher), None, 0),
                (source, len(cipher), output, len(output))):
            written = ctypes.c_size_t(999)
            with self.subTest(size=size, capacity=capacity):
                self.assertNotEqual(function(pointer, size, destination, capacity,
                                             ctypes.byref(written), error, len(error)), 0)
                self.assertEqual(written.value, 0)
                self.assertEqual(output.value, b'unchanged')
                self.assertTrue(error.value)

    def test_missing_native_dependency_has_a_build_instruction(self):
        modulus_reader.cache_clear()
        try:
            with patch('bmd_encrypted.ctypes.CDLL', side_effect=OSError('missing')):
                with self.assertRaisesRegex(BmdError, 'make -C model-recovery'):
                    decrypt_modulus(bytes(34))
        finally:
            modulus_reader.cache_clear()

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires MU_GAME_ROOT')
    def test_original_small_overlapping_and_threeway_models_match_oracle(self):
        cases = [
            ('Data/Object113/Object97.bmd',
             'e57c38d4a3a00f26ce0c65958c2e00b926eadaae165b6c6dde8923959dbc7752',
             'db19ef3e1aa0a45f7e2a757ab3b32bf6eaca19fe09eac9442a4c4c7012a78afe'),
            ('Data/Object113/Object07.bmd',
             '55b4d21ce7d3af67f6e039560562b34fc4774a401a0c0fa4448b14a4385f4053',
             '08abfb109b1cdd630f78a2aeadf38af5474a0aa6acb23e695ed878ddf1d5e972'),
            ('Data/Item/flag_class04.bmd',
             'fd90d5a093ee87e576b51b452c048f07b520d586d6882d63630c58720c50391d',
             '777b3e6b7f3ab406678e35f084c51e23f4bfc46144523a6ecc844eb26edbc5a6')]
        for relative, source_digest, decoded_digest in cases:
            with self.subTest(path=relative):
                raw = (Path(os.environ['MU_GAME_ROOT']) / relative).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), source_digest)
                model = parse_model(raw)
                self.assertEqual(model['decoded_payload_sha256'], decoded_digest)
                self.assertNotIn('cipher_block_trailer_hex', model)


if __name__ == '__main__':
    unittest.main()
