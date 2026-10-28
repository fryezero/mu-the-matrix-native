"""Worked examples and private instruction gate for RENDER-ITEMS-002b."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base


class ItemTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_renderchar as v
        cls.v, cls.lib = v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_wings_suppress_levels_and_keep_tail(self):
        for t in [*range(0x22e6, 0x22ec), 0x22f1, 0x248c, 0x248d]:
            status, draws = self.draws(self.item(type=t, item_level=15 << 3))
            self.assertEqual(status, 0)
            self.assertEqual([d.flags for d in draws], [2])
            self.assertEqual(list(draws[0].body_light), list(self.item().light))
            self.assertEqual([d.flags for d in self.draws(self.item(type=t, option1=1))[1]], [2, 0x42])
        self.assertEqual(self.draws(self.item(type=0x22ec))[0], 1)  # adjacent effect-heavy wing stays refused

    def test_weapon_remap_before_caps_and_mesh_override(self):
        for t in (0x12ed, 0x12f5):
            status, d = self.draws(self.item(type=t, item_level=4 << 3, a10=2, a11=99))
            self.assertEqual(status, 0)
            self.assertEqual([x.flags for x in d], [2, 0x44, 0x48])  # 4 -> 9
            self.assertEqual(d[0].hidden, -1)
            self.assertEqual([x.flags for x in self.draws(self.item(type=t, item_level=4 << 3, quality=0))[1]], [2])
            self.assertEqual([x.flags for x in self.draws(self.item(type=t, item_level=4 << 3, render_type=0x402))[1]], [0x402])

    def test_wing_blend_pulses(self):
        f = base.f32
        pulse = base.fsin(f(1234 * f(0.001)))
        for t, expected in ((0x22ea, f(pulse + f(1.1))), (0x248c, f(pulse + f(1.1))),
                            (0x22eb, f(f(pulse + 1) / 4)), (0x248d, f(f(pulse + 1) / 4))):
            self.assertEqual(self.draws(self.item(type=t, time=1234, option1=1))[1][-1].blend_light, expected)

    def test_link_family_and_capacity(self):
        import validate_item_types as v
        for t, n in ((0x12ea, 2), (0x12eb, 2), (0x1301, 2), (0x12ec, 6), (0x12f7, 10), (0x1303, 10)):
            status, out = v.c_link(self.lib, t, 29)
            self.assertEqual((status, len(out)), (0, n))
            self.assertEqual(out[0][1], 13 if n > 2 else 2)
            self.assertTrue(all(x[0] == 0x7f67 and x[-1] == 4 for x in out))
        n = C.c_int32()
        out = (v.Sprite * 2)()
        out[1].bone = 777
        self.assertEqual(self.lib.mu_rc_link_sprites(0x12ec, 0, out, 1, C.byref(n)), 3)
        self.assertEqual((n.value, out[1].bone), (6, 777))
        self.assertEqual(self.lib.mu_rc_link_sprites(0x12ed, 0, out, 1, C.byref(n)), 1)
        self.assertEqual(n.value, 0)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_private_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'types.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_types.py'), '--mutations',
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertEqual(sum(f['mismatches'] for f in report['families'].values()), 0)
            self.assertEqual(sum(f['cases'] for f in report['families'].values()), 135176)
            self.assertEqual(len(report['mutants']), 6)
            self.assertTrue(all(report['mutants'].values()))
