"""Analytic checks for the client-linked 3x4 pose composition."""
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class PoseConcatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        library = ctypes.CDLL(str(HERE/('librecord_math.dylib' if sys.platform == 'darwin' else 'librecord_math.so')))
        cls.concat = library.mu_pose_concat
        cls.concat.argtypes = [ctypes.c_void_p]*3
        cls.concat.restype = None
        cls.environment = library.mu_record_math_environment_supported
        cls.environment.restype = ctypes.c_int

    def invoke(self, parent, local):
        a = ctypes.create_string_buffer(struct.pack('<12f', *parent))
        b = ctypes.create_string_buffer(struct.pack('<12f', *local))
        output = ctypes.create_string_buffer(48)
        self.concat(a, b, output)
        return struct.unpack('<12f', output.raw)

    def test_identity_and_noncommuting_translation(self):
        self.assertEqual(self.environment(), 1)
        identity = [1,0,0,0, 0,1,0,0, 0,0,1,0]
        local = [2,0,0,7, 0,3,0,11, 0,0,4,13]
        self.assertEqual(self.invoke(identity, local), tuple(local))
        parent = [1,0,0,2, 0,1,0,3, 0,0,1,5]
        self.assertEqual(self.invoke(parent, local), (2,0,0,9, 0,3,0,14, 0,0,4,18))
        self.assertEqual(self.invoke(local, parent), (2,0,0,11, 0,3,0,20, 0,0,4,33))

    def test_binary32_rounding_occurs_before_following_add(self):
        parent = [2**24,1,-2**24,0]+[0]*8
        local = [1,0,0,0, 1,0,0,0, 1,0,0,0]
        self.assertEqual(self.invoke(parent, local)[0], 0)
        parent[:4] = [1+2**-23,-1,0,0]
        local[:4] = [1-2**-23,0,0,0]
        self.assertEqual(self.invoke(parent, local)[0], 0)

    def test_in_place_parent_uses_each_prior_output_store(self):
        parent = ctypes.create_string_buffer(struct.pack('<12f', *range(1,13)))
        local = ctypes.create_string_buffer(struct.pack('<12f', *([1]*12)))
        self.concat(parent, local, parent)
        self.assertEqual(struct.unpack('<12f', parent.raw[:48]),
                         (6,11,20,41, 18,31,56,113, 30,51,92,185))

    def test_validator_refuses_unpinned_text_without_optional_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not captured code')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_pose_concat.py'),
                                     '--text', str(text), '--library', '/nonexistent/library'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private pose instruction comparison is opt-in')
    def test_private_original_pose_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_pose_concat.py'),
                            '--text', str(text), '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(result['mismatches'], 0)
            self.assertGreater(result['instruction_cases'], 1000)
            self.assertGreater(result['snapshot_negative_control_differences'], 0)


if __name__ == '__main__':
    unittest.main()
