"""Part 13 bodies with carried model fields and immediate glColor records."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base
import gen_item_bodies as gen
import validate_item_carry as carry


class ItemCarry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.v = carry.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(gen.CARRY_TYPES), 89)
        self.assertEqual(len(gen.COLOUR_TYPES), 20)
        self.assertFalse(set(gen.CARRY_TYPES) & set(gen.COLOUR_TYPES))
        for t in carry.TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))

    def test_colour_records(self):
        """Colour types emit COLOR records in stream order; three-component calls have alpha 1."""
        types = carry.colour_types()
        self.assertEqual(len(types), 32)
        self.assertTrue(set(gen.COLOUR_TYPES) <= set(types))
        for t in types:
            records = [d for level in (0, 7, 13) for d in self.draws(self.item(type=t, item_level=level << 3))[1]
                       if d.entry == 3]
            self.assertTrue(records, hex(t))
            for d in records:
                self.assertIn(d.flags, (1, 2, 3), hex(t))
                if d.flags != 3:
                    self.assertEqual(d.alpha, 1.0, hex(t))

    def test_carry_writes_back_the_last_draw(self):
        """With only the body pass, the model keeps the fields of the body's last draw."""
        for t in gen.CARRY_TYPES:
            model = self.v.CModel()
            status, draws = self.draws(self.item(type=t), model)
            self.assertEqual(status, 0)
            last = [d for d in draws if d.entry != 3][-1]
            self.assertEqual(list(model.body_light), list(last.body_light), hex(t))
            self.assertEqual(list(model.shade), list(last.shade), hex(t))
            self.assertEqual((model.level_field, model.flag_ca), (last.level_field, last.flag_ca), hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'carry.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_carry.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'], 292*len(carry.TYPES))
            self.assertEqual(report['families']['carry']['cases'], 79744)
            self.assertEqual(report['families']['colours']['cases'], 2816)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), 12)
            self.assertTrue(all(report['mutants'].values()))
