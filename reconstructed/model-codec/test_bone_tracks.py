"""Checks for the authored BMD bone-track loop (client 0x012b4225..0x012b4441)."""
import ctypes
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def load_validator():
    spec = importlib.util.spec_from_file_location('validate_bone_tracks', ROOT/'scripts/validate_bone_tracks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BoneTrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.v = load_validator()
        cls.authored = cls.v.Authored(HERE/f'libbonetracks.{SUFFIX}')

    def run_case(self, case):
        return self.authored.run(case)

    def test_layout_strides_and_allocation_order(self):
        v = self.v
        positions = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
        rotations = [(0.0, 0.0, 0.0), (0.5, -0.25, 1.0)]
        bones = [{'dummy': 1},
                 {'dummy': 0, 'name': b'Bip01', 'parent': -1, 'tracks': [(positions, rotations), ([], [])]}]
        case = v.build_case('layout', [2, 0], bones, prefix=b'\x11\x22\x33')
        result = self.run_case(case)
        self.assertEqual(result['status'], 0)
        # One request of actions*12, then per action positions, rotations, quaternions.
        self.assertEqual(result['requests'], [24, 24, 24, 32, 0, 0, 0])
        window = result['window']
        at = lambda address: address-v.WINDOW
        array = struct.unpack_from('<I', window, at(case['model']+0x2c))[0]
        dummy, bone = array, array+0x8c
        # Dummy record: only +0x22 is written.
        self.assertEqual(window[at(dummy+0x22)], 1)
        for offset in list(range(0, 0x22))+list(range(0x23, 0x8c)):
            self.assertEqual(window[at(dummy+offset)], case['image'][at(dummy+offset)])
        self.assertEqual(window[at(bone):at(bone+32)], b'Bip01'.ljust(32, b'\0'))
        self.assertEqual(struct.unpack_from('<h', window, at(bone+0x20))[0], -1)
        self.assertEqual(window[at(bone+0x22)], 0)
        # Byte +0x23 and +0x28..+0x8b are not touched.
        self.assertEqual(window[at(bone+0x23)], case['image'][at(bone+0x23)])
        self.assertEqual(window[at(bone+0x28):at(bone+0x8c)], case['image'][at(bone+0x28):at(bone+0x8c)])
        tracks = struct.unpack_from('<I', window, at(bone+0x24))[0]
        p, r, q = struct.unpack_from('<3I', window, at(tracks))
        self.assertEqual(window[at(p):at(p+24)], b''.join(struct.pack('<3f', *x) for x in positions))
        self.assertEqual(window[at(r):at(r+24)], b''.join(struct.pack('<3f', *x) for x in rotations))
        self.assertEqual(struct.unpack_from('<4f', window, at(q)), (0.0, 0.0, 0.0, 1.0))
        expected = ctypes.create_string_buffer(16)
        self.authored.rotation(ctypes.create_string_buffer(struct.pack('<3f', *rotations[1])), expected)
        self.assertEqual(window[at(q+16):at(q+32)], expected.raw)
        # Second action has zero keys: three blocks requested, nothing copied.
        self.assertEqual(len(set(struct.unpack_from('<3I', window, at(tracks+12)))), 3)
        self.assertEqual(result['offset'], 3+1+1+32+2+48)

    def test_zero_actions_still_request_track_array(self):
        v = self.v
        case = v.build_case('zero-actions', [], [{'dummy': 0, 'name': b'a', 'parent': 0, 'tracks': []}]*2)
        result = self.run_case(case)
        self.assertEqual((result['status'], result['requests']), (0, [0, 0]))
        self.assertEqual(result['offset'], 2*35)

    def test_signed_counts(self):
        v = self.v
        bone = {'dummy': 0, 'name': b'n', 'parent': 1, 'tracks': [([], [])]}
        untouched = v.build_case('negative-bones', [1], [bone], bone_field=-3)
        result = self.run_case(untouched)
        self.assertEqual((result['status'], result['requests'], result['offset']), (0, [], 0))
        self.assertEqual(result['window'], untouched['image'])
        negative = v.build_case('negative-keys', [-1], [bone], heap_bytes=4096)
        result = self.run_case(negative)
        # Saturating unsigned multiplies request 0xffffffff; client malloc refuses it.
        self.assertEqual((result['status'], result['requests']), (1, [12, 0xffffffff]))

    def test_allocation_failure_and_image_bounds(self):
        v = self.v
        track = ([(1.0, 1.0, 1.0)], [(0.1, 0.2, 0.3)])
        case = v.build_case('fail', [1], [{'dummy': 0, 'name': b'f', 'parent': -1, 'tracks': [track]}])
        case['fail_allocation'] = 2
        result = self.run_case(case)
        self.assertEqual(result['status'], 1)
        tracks = struct.unpack_from('<I', result['window'], case['model']+0x2c-v.WINDOW)[0]+0x24
        entry = struct.unpack_from('<I', result['window'], tracks-v.WINDOW)[0]
        # The failed pointer is not stored: the entry keeps the allocator's poison bytes.
        poison = v.Heap(*case['heap']).allocate(12)[1]
        self.assertEqual(result['window'][entry-v.WINDOW:entry-v.WINDOW+4], poison[:4])
        outside = v.build_case('outside', [1], [{'dummy': 0, 'name': b'o', 'parent': -1, 'tracks': [track]}])
        image = bytearray(outside['image'])
        struct.pack_into('<I', image, outside['model']+0x2c-v.WINDOW, 0x10)
        outside['image'] = bytes(image)
        self.assertEqual(self.run_case(outside)['status'], 2)

    def test_python_model_agrees_and_negative_control_fails(self):
        v = self.v
        cases = v.synthetic_cases()
        differences = 0
        for case in cases:
            native = self.run_case(case)
            model = v.python_model(case, self.authored.rotation)
            self.assertEqual(native['status'], 0, case['label'])
            self.assertEqual((native['window'], native['offset']), model[:2], case['label'])
            wrong = v.python_model(case, self.authored.rotation, variant='elide-empty')
            differences += int(wrong[:2] != model[:2])
        self.assertGreater(differences, 5)

    def test_quaternion_convention(self):
        v = self.v
        angles = [(0.3, -0.7, 1.1), (2.0, 0.5, -3.0)]
        case = v.build_case('q', [2], [{'dummy': 0, 'name': b'q', 'parent': -1,
                                        'tracks': [([(0, 0, 0)]*2, angles)]}])
        window = self.run_case(case)['window']
        array = struct.unpack_from('<I', window, case['model']+0x2c-v.WINDOW)[0]
        tracks = struct.unpack_from('<I', window, array+0x24-v.WINDOW)[0]
        q = struct.unpack_from('<I', window, tracks+8-v.WINDOW)[0]
        for index, triple in enumerate(angles):
            actual = struct.unpack_from('<4f', window, q+16*index-v.WINDOW)
            for a, b in zip(actual, v.hamilton_reference([v.f32(x) for x in triple])):
                self.assertAlmostEqual(a, b, delta=1e-6)

    def test_validator_refuses_unpinned_text_without_optional_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not captured code')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_bone_tracks.py'),
                                     '--text', str(text), '--data', str(text), '--flag', str(text),
                                     '--feature', str(text)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private bone-track instruction comparison is opt-in')
    def test_private_original_bone_track_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', ROOT/'evidence/x86-math-capture-09'))/'cpu-features.bin'
        game_root = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(game_root, 'Requested integration needs MU_GAME_ROOT for installed v12/v14 models')
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_bone_tracks.py'), '--text', str(text),
                            '--data', str(data), '--flag', str(flag), '--feature', str(feature),
                            '--game-root', game_root, '--versions', '12,14', '--workers', '4',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        synthetic = result['synthetic']
        self.assertEqual(synthetic['matches'], synthetic['cases'])
        self.assertGreater(synthetic['cases'], 300)
        self.assertGreater(result['negative_control_elide_empty_differences'], 0)
        self.assertEqual(set(synthetic['memcpy_paths']), {'rep-movsb', 'sse2-palignr', 'dword-forward',
                                                          'dword-unaligned-source', 'backward', 'sse2-coaligned',
                                                          'sse2-unaligned-32-127', 'small-tail'})
        stops = {item['label']: item for item in result['characterization']}
        self.assertFalse(stops['heapalloc-null']['emulator_reached_end'])
        self.assertFalse(stops['angle-beyond-sse2-domain']['emulator_reached_end'])
        installed = result['installed']
        self.assertEqual(installed['per_version']['12'], {'files': 180, 'reader_rejected': 0, 'compared': 180,
                                                          'matches': 180, 'keys': 3802})
        self.assertEqual(installed['per_version']['14'], {'files': 216, 'reader_rejected': 0, 'compared': 216,
                                                          'matches': 216, 'keys': 15562})
        self.assertLess(installed['worst_quaternion_error'], 1e-6)


if __name__ == '__main__':
    unittest.main()
