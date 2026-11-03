"""SPRITE-DRAW-001: the shared sprite pass draws a sprite's pixels.

Portable: a synthetic flare01.OZJ, one CreateSprite 400 units ahead of the eye through
mu_world_particles_draw (software raster and headless GL) for the additive, alpha and
opaque-then-alpha blends; the same sprite above the view (Acheron's DATA-ACQ-002 case) draws none.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_particles import ozj_jpeg


class SpriteDraw(unittest.TestCase):
    def test_one_sprite_draws_pixels_and_none_outside_the_view(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/sprite-draw-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            effect = Path(tmp)/'Data/Effect'
            effect.mkdir(parents=True)
            (effect/'flare01.OZJ').write_bytes(ozj_jpeg(32, 32))
            p = subprocess.run([str(NATIVE/'build/sprite-draw-host'), tmp], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('the same sprite above the view none: OK', p.stdout)
        self.assertIn('ahead: raster ', p.stdout)


if __name__ == '__main__':
    unittest.main()
