"""Synthetic accumulation/reset histories through the production terrain C."""
import ctypes as C
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_aida_light_history as history


class AidaLightHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/terrain')], check=True)
        suffix = 'dylib' if sys.platform == 'darwin' else 'so'
        cls.lib = C.CDLL(str(ROOT / 'reconstructed/terrain' / ('libterrain.' + suffix)))
        cls.lib.mu_terrain_add_light.argtypes = [C.c_float, C.c_float, C.c_void_p, C.c_int32, C.c_void_p]
        cls.lib.mu_terrain_frame_light.argtypes = [C.c_void_p, C.c_void_p] + [C.c_int32] * 4

    def analyze(self, updates, reset_left, world=33, frame_present=True):
        primary = (C.c_float * (3 * 256 * 256))(*([0.25] * (3 * 256 * 256)))
        frame = (C.c_float * len(primary)).from_buffer_copy(primary)
        # Authored emitter across a reset edge, unrelated to captured coordinates.
        for n in range(updates):
            if reset_left:
                self.lib.mu_terrain_frame_light(primary, frame, 0, 0, 92, 10)
            flicker = (n % 5) * 0.01
            light = (C.c_float * 3)(0.4 + flicker, 0.6 + flicker, 0.4 + flicker)
            self.lib.mu_terrain_add_light(9560, 675, light, 2, frame)
        obj = bytearray(0x3d8)
        struct.pack_into('<i', obj, 0x5c, 30)
        struct.pack_into('<3f', obj, 0x158, 9560, 675, 0)
        with tempfile.TemporaryDirectory() as td:
            objects, lights = Path(td) / 'objects.bin', Path(td) / 'light.bin'
            objects.write_bytes(b'MUOBJLV1' + struct.pack('<iiiI', world, world, 1, 1)
                                + struct.pack('<II', 0, 0) + obj)
            body = bytes(primary) + (bytes(frame) if frame_present else b'')
            lights.write_bytes(b'MULITLV1' + b'LITE' + struct.pack('<I', len(body)) + body)
            return history.analyze(objects, lights, [96, 7])

    def test_partial_reset_distinguishes_one_and_many_additions(self):
        result = self.analyze(179, True)
        samples = result['sources'][0]['samples']
        self.assertTrue(any(s['tile'][0] <= 95 for s in samples))
        self.assertTrue(any(s['tile'][0] >= 96 for s in samples))
        for sample in samples:
            expected = 1 if sample['tile'][0] <= 95 else 179
            self.assertAlmostEqual(sample['effective_updates'], expected, delta=0.03)
            self.assertAlmostEqual(sample['red_minus_blue'], 0, delta=0.0001)
        self.assertEqual(result['world'], 33)
        self.assertTrue(all(len(digest) == 64 for digest in result['inputs'].values()))

    def test_single_update_is_independent_of_reset_edge(self):
        for sample in self.analyze(1, False)['sources'][0]['samples']:
            self.assertAlmostEqual(sample['effective_updates'], 1, delta=0.0001)

    def test_missing_grid_or_non_aida_world_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'both primary and frame'):
            self.analyze(1, False, frame_present=False)
        with self.assertRaisesRegex(ValueError, 'Aida object'):
            self.analyze(1, False, world=0)
