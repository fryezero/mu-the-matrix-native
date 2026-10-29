"""RENDER-WORLDS-Q2: the class slot 0x10 (draw-first answer of worlds 134..145) and private instruction comparisons."""
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
import validate_worlds_q2 as q2  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
SQUARE = ((C.c_float * 4)(0, 0, 250, 250), (C.c_float * 4)(0, 250, 250, 0))   # tiles 0..250, clockwise


class WorldsQ2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = q2.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

    def obj(self, typ, x=10000.0, live=1, rng=-30.0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = live
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<f', o, 0xc0, rng)
        struct.pack_into('<2f', o, 0x158, x, 10000.0)
        return o

    def first(self, o, world):
        return self.lib.mu_class_first(o, world, SQUARE[0], SQUARE[1], 6)

    def test_owned_worlds(self):
        self.assertEqual([w for w in range(0, 300) if self.lib.mu_class_first_owned(w)], list(range(134, 146)))

    def test_twisted_karutan_range(self):
        o = self.obj(17)
        self.assertEqual(self.first(o, 142), 1)
        self.assertEqual(struct.unpack_from('<f', o.raw, 0xc0)[0], -800.0)
        o = self.obj(25)   # not listed: no store, no answer
        self.assertEqual(self.first(o, 142), 0)
        self.assertEqual(struct.unpack_from('<f', o.raw, 0xc0)[0], -30.0)
        o = self.obj(17, x=-90000.0)   # far outside the polygon: the range is still written
        self.assertEqual(self.first(o, 142), 0)
        self.assertEqual(struct.unpack_from('<f', o.raw, 0xc0)[0], -800.0)

    def test_other_overrides(self):
        self.assertEqual(self.first(self.obj(1), 134), 1)
        self.assertEqual(self.first(self.obj(2), 134), 0)
        self.assertEqual(self.first(self.obj(0), 145), 1)
        self.assertEqual(self.first(self.obj(0, live=0), 145), 0)   # 0x00d752ad tests the live byte first
        self.assertEqual(self.first(self.obj(0, live=0), 143), 1)
        for world in (137, 139, 140, 133, 146):
            self.assertEqual(self.first(self.obj(0), world), 0)
        o = self.obj(23)
        self.assertEqual(self.first(o, 135), 1)
        self.assertEqual(struct.unpack_from('<f', o.raw, 0xc0)[0], -30.0)

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-q2-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_q2.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual({k: r['cases'] for k, r in result['families'].items()},
                             {'ferea_visual': 1000, 'class_first': 2000, 'render_first': 1000})
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 50)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
