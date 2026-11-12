"""Additional body admission and private full-stream comparisons."""
import json
import os
import random
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import validate_item_other_bodies as other
import validate_renderchar as v


class ItemOtherBodies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v, cls.lib = v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_admissions_keep_selected_and_shadow_refusals(self):
        for t in other.TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for refusal in ({'select': 1}, {'object_shadow': 1}, {'a10': 0}):
                self.assertEqual(self.draws(self.item(type=t, **refusal))[0], 2, (hex(t), refusal))

    def test_clock_zero_sign(self):
        # Original 0x016fce1b..0x016fce1e adds positive zero after the saved product.
        textures = {0x2568: 0x80de, 0x2569: 0x80df, 0x256a: 0x80e0, 0x256b: 0x80e1}
        for t, texture in textures.items():
            case = v.random_case_any(random.Random(t), t)
            case.update(time=0x80000000, record=None, quality=9, item_level=0,
                        option1=0, ext=0, render_type=2, a10=0xffffffff, a11=0xffffffff)
            status, draws = v.c_stream(self.lib, case)
            self.assertEqual(status, 0)
            colour = [d[2] for d in draws if d[0] == 'MESH' and d[1][0] == 1 and d[1][7] == texture]
            self.assertEqual(colour, [(0, 0, 0)], hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'other-bodies.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_other_bodies.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(other.TYPES)
        self.assertEqual(report['families']['bodies']['cases'], 292*n)
        self.assertEqual(report['families']['records']['cases'], 512*n)
        self.assertEqual(report['families']['clocks']['cases'], 24*n)
        self.assertEqual(report['families']['frame']['cases'], 64*n)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(len(report['mutants']), 3)
        self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
