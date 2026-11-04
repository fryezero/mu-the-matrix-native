"""Part 15 bodies: body random scaling a constant body-light vector (kind-5 product programs)."""
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
import validate_item_product as product
import validate_item_quality as quality
import test_item_quality

F32 = lambda x: ctypes.c_float(x).value
# 0x00cfcead constants per body (x, y, z), then (rand % 15) / 37.5 + 0.5 (binary32).
LIGHTS = {0x171d: (0.9, 0.4, 0.2), 0x171e: (0.8, 0.5, 0.2), 0x171f: (0.1, 0.4, 0.3)}


class ItemProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws
    draws_random = test_item_quality.ItemQuality.draws_random

    def setUp(self):
        self.v = quality.v

    def test_admissions_and_existing_domain(self):
        self.assertEqual(gen.PRODUCT_TYPES, [0x171d, 0x171e, 0x171f, 0x1742, 0x1743, 0x1744])
        self.assertFalse(set(gen.PRODUCT_TYPES) & set(gen.QUALITY_TYPES + gen.CARRY_TYPES))
        for t in gen.PRODUCT_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            kinds = [kind for kind, _ in quality.table_programs(t)]
            self.assertEqual(kinds.count(4), 1, hex(t))
            self.assertEqual(kinds.count(5), 3, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))

    def test_light_product(self):
        """One rand per body pass; one draw carries constants times ((rand % 15) / 37.5 + 0.5)."""
        for t, light in LIGHTS.items():
            for twin in (t, t + 0x25):
                for value in (0, 14, 15 * 7 + 3):
                    status, draws, used = self.draws_random(self.item(type=twin, quality=9), [value])
                    self.assertEqual((status, used), (0, 1), hex(twin))
                    scale = F32(F32(F32(value % 15) / F32(37.5)) + F32(0.5))
                    expected = [F32(F32(k) * scale) for k in light]
                    lit = [list(d.body_light) for d in draws if d.entry == 2]
                    self.assertIn(expected, lit, (hex(twin), value))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'product.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_product.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'], 292*len(product.TYPES))
            self.assertEqual(report['families']['products']['cases'], 187*len(product.TYPES))
            self.assertEqual(report['families']['products']['residues'], 15)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), len(product.MUTANTS))
            self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
