"""Worked examples and the private instruction comparison for RENDER-ITEMS-002."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_hud as vh


class RenderItemsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/hud')], check=True)
        suffix = 'dylib' if sys.platform == 'darwin' else 'so'
        cls.lib = vh.slot_lib(ctypes.CDLL(str(ROOT/f'reconstructed/hud/libmu_hud.{suffix}')))

    def draw(self, code, level=0, **fields):
        inp, out = vh.Item3dIn(), vh.Item3dOut()
        inp.code, inp.level_word = code, level * 8
        inp.w, inp.h = 20, 40
        inp.trs = vh.ItemTRS(0.37, 0.81, (ctypes.c_float*3)(27, -19, 48), 0.0043)
        inp.frame_scale = inp.rate_x = inp.rate_y = 1
        for name, value in fields.items():
            setattr(inp, name, value)
        return self.lib.mu_item3d(ctypes.byref(inp), ctypes.byref(out)), out

    def test_remap_keeps_raw_level_test(self):
        for level, model in ((0, 0x14f0), (1, 0xaf9), (2, 0x12f8), (16, 0x24f9), (-1, 0x24f9)):
            status, out = self.draw(0x1a13, level)
            self.assertEqual((status, out.model, out.level_word), (1, model, level * 8))
        self.assertEqual(self.draw(0x1a0e, 1)[1].model, 0x38a0)
        self.assertEqual(self.draw(0x1a0e, 17)[1].model, 0x24f4)

    def test_level_word_reset_and_scale_override_order(self):
        status, out = self.draw(0x1c17, 1, scale_override=22)
        self.assertEqual((status, out.model, out.level_word), (1, 0x389c, -1))
        self.assertEqual(out.scale, vh.cm.f32(0.264))
        self.assertEqual(self.draw(0x1c18, 1)[1].level_word, -1)
        self.assertEqual(self.draw(0x1c18, 2)[1].level_word, 16)

    def test_range_includes_middle_code(self):
        for code in (0x1c2e, 0x1c2f, 0x1c30):
            self.assertEqual(self.draw(code, 9)[1].model, 0x2714)
        self.assertEqual(self.draw(0x1c31)[1].model, 0x2717)

    def test_time_and_selection(self):
        for code in range(0x1a47, 0x1a4c):
            self.assertEqual(self.draw(code, time=120)[1].angle[1], 24)
            self.assertEqual(self.draw(code, time=120, select=1)[1].angle[1], -19)
        out = self.draw(0x1c64, no_select=1, special_window_active=1)[1]
        self.assertEqual(out.select, 1)
        self.assertEqual(self.draw(0x1c64, no_select=1)[1].select, 0)

    def test_external_jump_refusal(self):
        for level in (8, 13, 15, 16, 100):
            self.assertEqual(self.draw(0x1c0b, level)[0], 2)
        for level in (-1, 0, 1, 2, 3, 4, 5, 6, 7):
            self.assertEqual(self.draw(0x1c0b, level)[0], 1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned restored text')
    def test_private_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_items.py'), '--mutations',
                            '--output', str(Path(tmp)/'report.json')], check=True)


if __name__ == '__main__':
    unittest.main()
