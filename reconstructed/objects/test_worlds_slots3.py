"""RENDER-WORLDS-SLOTS3: RenderObjectVisual's outer draw (0x017f9797) in the worlds without a class and Tormenta 141:
the flicker rule, and the private instruction comparison of the labelled rand() sequence."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


class WorldsSlots3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        suffix = 'dylib' if sys.platform == 'darwin' else 'so'
        cls.dll = C.CDLL(str(ROOT / 'reconstructed/objects' / ('libobjects.' + suffix)))
        cls.dll.mu_obj_visual_flicker.argtypes = [C.c_int32, C.c_int]

    def test_flicker_in_worlds_without_a_class(self):
        # Lorencia, Dungeon, Devias, Noria, Icarus, the Kanturu flame worlds, Arena, Tormenta 141: the runtime draws
        for world in (0, 1, 2, 3, 6, 10, 37, 38, 40, 51, 56, 73, 141):
            self.assertEqual(self.dll.mu_obj_visual_flicker(world, 1), 1, world)
            self.assertEqual(self.dll.mu_obj_visual_flicker(world, 0), 0, world)
        # Lost Tower, Atlans and Tarkan: mu_builtin_visual's first draw is the outer one
        for world in (4, 7, 8):
            self.assertEqual(self.dll.mu_obj_visual_flicker(world, 1), 0, world)

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-slots3-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_slots3.py'), '--cases', '200',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))


if __name__ == '__main__':
    unittest.main()
