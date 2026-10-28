"""Worked examples and private instruction comparisons for item part 5."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base


class ItemContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_item_continuation as v
        cls.cont, cls.v, cls.lib = v, v.v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_raw_skin_levels_bypass_quality_and_glow_caps(self):
        for level, light in ((14, [0.2, 0.3, 0.5]), (15, [0.5, 0.3, 0.2])):
            status, draws = self.draws(self.item(type=0x3895, item_level=level << 3, quality=0))
            self.assertEqual((status, len(draws)), (0, 3))
            for actual, expected in zip(draws[0].body_light, light):
                self.assertAlmostEqual(actual, expected, places=6)
            self.assertEqual([d.flags for d in draws], [2, 0x44, 0x48])
        self.assertEqual(len(self.draws(self.item(type=0x3895, item_level=13 << 3, quality=0))[1]), 1)

    def test_effective_skin_override_and_preserved_initial_shade(self):
        status, draws = self.draws(self.item(type=0x3896, item_level=13 << 3, quality=9))
        self.assertEqual((status, [d.flags for d in draws]), (0, [1, 0x44]))
        self.assertEqual(draws[0].blend_mesh, 0)
        self.assertEqual(draws[0].blend_light, 1)
        self.assertEqual(draws[0].alpha, 1)
        capped = self.draws(self.item(type=0x3896, item_level=13 << 3, quality=1))[1]
        self.assertEqual(capped[0].flags, 2)
        self.assertEqual(self.draws(self.item(type=0x389b))[1][1].texture, 0x7f20)
        early = self.draws(self.item(type=0x389b, item_level=2 << 3))[1]
        self.assertEqual(early[-1].texture, -1)

    def test_skin_scroll_and_sprite_colour(self):
        draws = self.draws(self.item(type=0x389d, time=5000.5))[1]
        self.assertEqual(draws[0].v, -0.25)
        a = self.cont.c_skin_effect(self.lib, 0x389c, 0)
        b = self.cont.c_skin_effect(self.lib, 0x389d, 0)
        self.assertEqual(a[0][2], (0, 0, self.v.f2u(15)))
        self.assertEqual(b[0][2], (0, self.v.f2u(-5), self.v.f2u(-15)))
        self.assertEqual(a[0][4][0], b[0][4][2])
        self.assertEqual(a[0][4][2], b[0][4][0])
        self.assertEqual(self.cont.c_skin_effect(self.lib, 0x389b, 0), [])

    def test_sword_stream_and_bounded_output(self):
        values = [0] * 32
        status, effects, consumed = self.cont.clusters.c_effects(self.lib, 0x0afd, values, 0)
        self.assertEqual((status, consumed), (0, 3))
        self.assertEqual([e[1] for e in effects], [4, 4, 4, 4, 6, 7, 8])
        self.assertEqual([e[0] for e in effects], [0x7f67]*2 + [0x7ef7]*5)
        self.assertEqual(effects[1][5], self.v.f2u(90))
        out, count = (self.cont.clusters.Effect * 1)(), C.c_int32()
        @self.cont.clusters.RANDOM
        def random(_): return 0
        self.assertEqual(self.lib.mu_rc_link_effects_time(0x0afd, C.c_float(0), random, None,
                                                        out, 1, C.byref(count)), 3)
        self.assertEqual(count.value, 7)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_private_original_instructions(self):
        import gen_item_bodies as gen
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'continuation.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_continuation.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(report['families']['bodies']['cases'], len(gen.CONTINUATION_TYPES)*292)
            self.assertEqual(report['families']['skins']['cases'], 3072)
            self.assertEqual(report['families']['links']['cases'], 800)
            self.assertEqual(len(report['mutants']), 9)
            self.assertTrue(all(report['mutants'].values()))
