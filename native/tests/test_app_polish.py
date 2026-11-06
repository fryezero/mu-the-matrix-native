"""Bounded shadow policy, Warps size and approachable offline demo checks."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_app_polish1 as v


class AppPolishTests(unittest.TestCase):
    def test_production_shadow_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = v.native_shadow(Path(tmp))
            for world in (0, 2, 3):
                self.assertEqual(probe(world), [1, 0, 0, 0, 0, 0, 1])
            self.assertAlmostEqual(probe(7)[-1], .2)
            self.assertEqual(probe(10)[0], 0)
            self.assertEqual(probe(143)[2], 5)

    def test_warps_native_window_sizes(self):
        import validate_gfx3 as gfx
        with tempfile.TemporaryDirectory() as tmp:
            for w,h in ((1280,800),(1504,936),(1024,699)):
                expected = ([['SetScale',83]] if h<700 else []) + [['SetAlign',10],['SetWindowSize',w,h]]
                self.assertEqual(v.layer_window(gfx.layer_log(Path(tmp),(w,h))),expected)

    def test_demo_hound_starts_outside_arrival_neighborhood(self):
        lines=(ROOT/'native/world/lorencia-demo-placement.txt').read_text().splitlines()
        hound=next(line.split() for line in lines if line.startswith('actor 1 '))
        x,y,radius=int(hound[2]),int(hound[3]),int(hound[hound.index('wander')+1])
        self.assertGreater(abs(x-179)-radius, 15)
        self.assertEqual(y,131)


class ClientComparison(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original instructions')
    def test_unicorn(self):
        from types import SimpleNamespace
        report=v.run(SimpleNamespace(text=None,data=None,section3=None,cases=20,mutants=False))
        self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()))
