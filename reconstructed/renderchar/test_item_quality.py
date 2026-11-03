"""Part 14 bodies: supplementary record/quality probes, exit model fields and body random."""
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
import validate_item_quality as quality


class ItemQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.v = quality.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def draws_random(self, it, values):
        """Draws with a context whose random source returns values in order; also the count consumed."""
        v, used = self.v, []

        def draw(_):
            used.append(values[len(used) % len(values)])
            return used[-1]
        context = v.CContext(0, -1, v.RANDOM_FN(draw), None)
        model, out, count = v.CModel(), (v.CDraw * 32)(), ctypes.c_int32()
        status = self.lib.mu_rc_item_draws_context(ctypes.byref(it), ctypes.byref(model), out, 32, ctypes.byref(count),
                                                   ctypes.byref(context))
        return status, list(out[:count.value]), len(used)

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(gen.QUALITY_TYPES), 51)
        self.assertEqual(len(gen.EXIT_TYPES), 34)
        self.assertTrue(set(gen.EXIT_TYPES) <= set(gen.QUALITY_TYPES))
        self.assertFalse(set(gen.QUALITY_TYPES) & set(gen.CARRY_TYPES))
        for t in gen.QUALITY_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))

    def test_record_glow_reaches_helper_phase(self):
        """Kind B 0x5b forces glow level 9: wings take the 0x44 helper at quality 1, 0x44 and 0x48 above."""
        for t in [t for t in gen.QUALITY_TYPES if t >= 0x2300]:
            flags = lambda q: [d.flags & ~0x100 for d in self.draws(self.item(type=t, quality=q, has_record=1,
                                                                             kind_b=0x5b))[1] if d.entry == 1]
            self.assertIn(0x44, flags(1), hex(t))
            self.assertNotIn(0x48, flags(1), hex(t))
            self.assertTrue({0x44, 0x48} <= set(flags(2)), hex(t))

    def test_exit_fields_are_not_the_last_draw(self):
        """0xb10 leaves the model light at (1,1,1) after a last draw at (1, 0.8, 0.2); EXIT draws nothing."""
        model = self.v.CModel()
        status, draws = self.draws(self.item(type=0x0b10), model)
        self.assertEqual(status, 0)
        self.assertTrue(all(d.entry in (1, 2, 3) for d in draws))
        self.assertEqual(list(model.body_light), [1.0, 1.0, 1.0])
        self.assertNotEqual(list(draws[-1].body_light), list(model.body_light))

    def test_body_random(self):
        """One rand result per body pass, (rand % n) / k + c into a draw word; none in helper passes."""
        types = quality.random_types()
        self.assertEqual(types, [0x0b22, 0x0f0d])
        for t in types:
            for flags in (2, 0x40042):
                it = lambda level=0: self.item(type=t, render_type=flags, item_level=level << 3, quality=9)
                status, low, used = self.draws_random(it(), [0])
                self.assertEqual((status, used), (0, 1), hex(t))
                _, high, used = self.draws_random(it(), [14])
                self.assertEqual(used, 1, hex(t))
                self.assertNotEqual([d.blend_light for d in low], [d.blend_light for d in high], hex(t))
                # +13: the body pass draws once; the four helper passes draw nothing.
                self.assertEqual(self.draws_random(it(13), [3])[2], 1, hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'quality.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_quality.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'], 292*len(quality.TYPES))
            self.assertEqual(report['families']['records']['cases'], 256*len(quality.TYPES))
            self.assertEqual(report['families']['random']['cases'], 66*len(quality.random_types()))
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), len(quality.MUTANTS))
            self.assertTrue(all(report['mutants'].values()))
