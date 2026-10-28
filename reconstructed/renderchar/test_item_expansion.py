"""Worked examples and private instruction comparison for part 4."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base


class ItemExpansion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_renderchar as v
        cls.v, cls.lib = v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_armour_pulse_and_restored_light(self):
        a = self.draws(self.item(type=0x1950, time=0))[1]
        b = self.draws(self.item(type=0x1950, time=785))[1]
        self.assertEqual([x.entry for x in a], [1, 2])
        self.assertEqual(a[1].flags, 0x42)
        self.assertEqual(a[1].texture, 0x826d)
        self.assertNotEqual(list(a[1].body_light), list(b[1].body_light))
        high = self.draws(self.item(type=0x1950, time=785, item_level=13<<3))[1]
        self.assertEqual(high[0].body_light[:], high[2].body_light[:])

    def test_skin_remaps_and_record_bound(self):
        for t in (0x3890, 0x3891, 0x3899, 0x389f):
            self.assertEqual(len(self.draws(self.item(type=t))[1]), 2)
        for t in (0x3894, 0x3897, 0x3898, 0x38a0):
            self.assertEqual(len(self.draws(self.item(type=t, item_level=13<<3))[1]), 1)
        for t in (0x3700, 0x38a2):
            for kind in (0, 6):
                d = self.draws(self.item(type=t, kind_a=kind, option1=1, ext_option=1))[1]
                self.assertEqual(d[-1].flags, 0x42)
        for t in (0x3895, 0x3896, 0x389b, 0x389c, 0x389d, 0x389e):
            self.assertEqual(self.draws(self.item(type=t))[0], 1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_private_original_instructions(self):
        import gen_item_bodies as gen
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'expansion.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_expansion.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(report['families']['bodies']['cases'], len(gen.ADDITIONAL_TYPES)*292)
            self.assertEqual(report['families']['links']['cases'], 800)
            self.assertEqual(report['families']['skin_remaps']['cases'], 272)
            self.assertEqual(len(report['mutants']), 7)
            self.assertTrue(all(report['mutants'].values()))
