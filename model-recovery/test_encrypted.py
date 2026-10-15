import hashlib
import struct
import unittest
import os
import json
from pathlib import Path
from bmd10 import BmdError, parse_bytes
from bmd_encrypted import decrypt_lea, decrypt_lea_python, parse_model, MAP_KEY
from test_bmd10 import fixture

ROOT = Path(__file__).resolve().parents[1]


class EncryptedModels(unittest.TestCase):
    def test_public_lea256_known_vectors(self):
        vectors = json.loads((Path(__file__).parent/'fixtures/lea256-vectors.json').read_text())['vectors']
        self.assertGreaterEqual(len(vectors), 3)
        for vector in vectors:
            with self.subTest(key=vector['key']):
                cipher,key,plain = (bytes.fromhex(vector[k]) for k in ['ciphertext','key','plaintext'])
                self.assertEqual(decrypt_lea_python(cipher,key),plain)
                self.assertEqual(decrypt_lea(cipher,key),plain)

    def test_v12_roundtrip_with_independent_published_encoding(self):
        body = fixture()[4:]
        encoded = bytearray()
        previous = 0x5e
        for i, value in enumerate(body):
            byte = ((value+previous) & 255) ^ MAP_KEY[i % 16]
            encoded.append(byte)
            previous = (byte+0x3d) & 255
        raw = b'BMD\x0c'+struct.pack('<I',len(encoded))+encoded
        model = parse_model(raw)
        self.assertEqual(model['version'], 12)
        self.assertEqual(len(model['meshes'][0]['vertices']), 3)
        self.assertEqual(model['source_sha256'], hashlib.sha256(raw).hexdigest())

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires MU_GAME_ROOT and private reference evidence')
    def test_published_lea_implementation_matches_real_sample(self):
        original_root = Path(os.environ['MU_GAME_ROOT'])
        raw = (original_root/'Data/Effect/01spa_skill.bmd').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), '90858e15b60e538aa15f51c98fe93f114a169e515d7bec9c313afefe6002f994')
        reference = (ROOT/'evidence/model-v15-sample.bin').read_bytes()[4:]
        self.assertEqual(decrypt_lea(raw[8:]), reference)
        self.assertEqual(decrypt_lea_python(raw[8:]), reference)
        model = parse_model(raw)
        self.assertEqual(model['version'], 15)
        self.assertEqual(len(model['bones']), 9)
        self.assertEqual(len(model['meshes']), 0)
        self.assertEqual(model['cipher_block_trailer_hex'], reference[-4:].hex())

    def test_invalid_cipher_or_envelope_rejected(self):
        for raw in [b'BMD\x0f', b'BMD\x0f'+struct.pack('<I',1)+b'a',
                    b'BMD\x0c'+struct.pack('<I',100), b'BMD\x0e'+b'\0'*100]:
            with self.subTest(raw=raw), self.assertRaises(BmdError):
                parse_model(raw)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires MU_GAME_ROOT')
    def test_full_block_alignment_trailer_in_real_model(self):
        path = Path(os.environ['MU_GAME_ROOT'])/'Data/Effect/Change_Up_Eff.bmd'
        model = parse_model(path.read_bytes())
        self.assertEqual(len(bytes.fromhex(model['cipher_block_trailer_hex'])),16)

    def test_padding_is_opt_in_and_preserved(self):
        raw = fixture()
        pad = b'\xa5'*((-len(raw)+4) % 16)
        with self.assertRaises(BmdError):
            parse_bytes(raw+pad)
        model = parse_bytes(raw+pad, lea_block_padding=True)
        self.assertEqual(model['cipher_block_trailer_hex'],pad.hex())
        with self.assertRaises(BmdError):
            parse_bytes(raw+pad+b'x'*16,lea_block_padding=True)


if __name__ == '__main__':
    unittest.main()
