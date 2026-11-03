"""RENDER-WORLDS-AFTER4: the whole draw-first predicate 0x017fcd18 (portable synthetic checks) and the private
instruction comparison (validate_worlds_after4)."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_object_render as v  # noqa: E402
import validate_worlds_after4 as wa4  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME_ROOT = os.environ.get('MU_GAME_ROOT')


class WorldsAfter4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = wa4.build(ROOT / 'reconstructed')
        cls.dll = cls.lib.dll

    def obj(self, typ, x=5000.0, y=5000.0, live=1, rng=-300.0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = live
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<f', o, 0xc0, rng)
        struct.pack_into('<2f', o, 0x158, x, y)
        return o

    def first(self, o, world, eye=(5000.0, 5000.0, 0.0), tower=0, scene=6):
        # a square around tiles 40..60 (position / 100)
        xs, ys = (C.c_float * 4)(40, 60, 60, 40), (C.c_float * 4)(40, 40, 60, 60)
        es = (C.c_float * 3)(*eye)
        return self.dll.mu_draw_first(o, world, C.byref(wa4.DrawFirstInputs(xs, ys, scene, es, tower)))

    def test_lists_without_frustum(self):
        far = dict(x=90000.0, y=90000.0)
        self.assertEqual(self.first(self.obj(0x37, **far), 0), 1)
        self.assertEqual(self.first(self.obj(0x62, **far), 0x4a), 1)
        self.assertEqual(self.first(self.obj(0x23, **far), 0x21), 1)
        self.assertEqual(self.first(self.obj(0x24, **far), 0x21), 0)

    def test_live_byte(self):
        self.assertEqual(self.first(self.obj(6, live=1), 0x33), 1)
        self.assertEqual(self.first(self.obj(6, live=2), 0x33), 0)   # 0x33 and 0x70 want exactly 1
        self.assertEqual(self.first(self.obj(0x10, live=2), 0x38), 1)
        self.assertEqual(self.first(self.obj(0x10, live=0), 0x38), 0)

    def test_chain(self):
        self.assertEqual(self.first(self.obj(0x4bc, x=1e6), 0x27, tower=0), 1)
        self.assertEqual(self.first(self.obj(0x4bc, x=1e6), 0x27, tower=4), 0)
        self.assertEqual(self.first(self.obj(7, rng=-400.0), 0x76), 1)   # 0x74..0x78: any type, range <= -400
        self.assertEqual(self.first(self.obj(7, rng=-399.0), 0x76), 0)
        self.assertEqual(self.first(self.obj(0x9e), 0x7d), 1)
        self.assertEqual(self.first(self.obj(0x47, live=0), 0x81), 0)

    def test_class_tail_and_range(self):
        o = self.obj(0x6b)
        self.assertEqual(self.first(o, 142), 1)
        self.assertEqual(struct.unpack_from('<f', o, 0xc0)[0], -800.0)   # Twisted Karutan's slot 0x10

    def test_world_49_fade(self):
        o = self.obj(0x7a)
        struct.pack_into('<2f', o, 0xa8, 0.5, 0.0)
        struct.pack_into('<f', o, 0xd8, 0.98)
        self.assertEqual(self.first(o, 0x49, eye=(5000.0 + 3000.0, 5000.0, 0.0)), 1)   # near list: 4000 > d
        self.assertAlmostEqual(struct.unpack_from('<f', o, 0xa8)[0], 0.53, places=6)
        self.assertAlmostEqual(struct.unpack_from('<f', o, 0xd8)[0], 1.01, places=6)   # below 1: step, no clamp
        self.first(o, 0x49, eye=(5000.0 + 3000.0, 5000.0, 0.0))
        self.assertEqual(struct.unpack_from('<f', o, 0xd8)[0], 1.0)   # at or above 1: set to 1
        o = self.obj(5)
        struct.pack_into('<f', o, 0xa8, 0.7)
        struct.pack_into('<2f', o, 0xd8, 0.4, 0.4)
        self.assertEqual(self.first(o, 0x49, eye=(5000.0 + 2500.0, 5000.0, 0.0)), 0)   # d > 2000: cleared
        self.assertEqual(struct.unpack_from('<4f', o, 0xa8)[0], 0.0)
        self.assertEqual(struct.unpack_from('<2f', o, 0xd8), (0.0, 0.0))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-after4-orig-') as td:
            report = Path(td) / 'report.json'
            args = [sys.executable, str(ROOT / 'scripts/validate_worlds_after4.py'), '--cases', '9000',
                    '--mutations', '--output', str(report)] + (['--game-root', GAME_ROOT] if GAME_ROOT else [])
            subprocess.run(args, check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(result['families']['draw_first']['cases'], 9000)
            if GAME_ROOT:
                self.assertEqual(result['families']['action_keys']['cases'], 181)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 40)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
