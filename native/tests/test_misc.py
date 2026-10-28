"""WIP SYS-MISC-001a: verified BossHPUI math, no fabricated packet routes."""
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('validate_misc', ROOT/'scripts/validate_misc.py')
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


class BossMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = vm.library(vm.SRC, Path(cls.tmp.name)/'misc.dylib')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def bar(self, maximum):
        bar = vm.Bar()
        self.lib.mu_misc_boss_init(C.byref(bar))
        self.assertEqual(self.lib.mu_misc_boss_set_maximum(C.byref(bar), maximum), 1)
        return bar

    def test_layer_boundaries_and_palette(self):
        bar = self.bar(1000)
        for hp, expected in [(1000, (10, 0, 1)), (901, (10, 0, 1)), (900, (9, 1, 2)),
                             (700, (7, 3, 1)), (200, (2, 2, 0)), (100, (1, 0, 1)), (0, (0, 0, 1))]:
            self.assertEqual(self.lib.mu_misc_boss_update(C.byref(bar), hp), 1)
            self.assertEqual((bar.remaining, bar.current_colour, bar.next_colour), expected)

    def test_gauge_uses_segment_remainder_and_full_health_exception(self):
        bar = self.bar(1000)
        for hp, expected in [(1000, 100), (999, 99), (900, 0), (150, 50), (1, 1), (0, 0), (-1, 0)]:
            self.assertEqual(self.lib.mu_misc_boss_gauge(C.byref(bar), hp, 1000), expected)
        # Truncating maximum/segments matters for a nonmultiple of 10.
        bar = self.bar(1009)
        self.assertEqual(bar.unit, 100)
        self.assertEqual(self.lib.mu_misc_boss_gauge(C.byref(bar), 1008, 1009), 8)

    def test_invalid_divisors_refuse_without_mutating_state(self):
        bar = vm.Bar()
        self.lib.mu_misc_boss_init(C.byref(bar))
        initial = bytes(bar)
        for maximum in (0, -1, 9):
            self.assertEqual(self.lib.mu_misc_boss_set_maximum(C.byref(bar), maximum), 0)
            self.assertEqual(bytes(bar), initial)
        self.assertEqual(self.lib.mu_misc_boss_update(C.byref(bar), 100), 0)
        self.assertEqual(bytes(bar), initial)
        self.assertEqual(self.lib.mu_misc_boss_gauge(C.byref(bar), 1, 100), -1)

    def test_two_bars_are_independent_and_reset(self):
        left, right = self.bar(1000), self.bar(10000)
        original = bytes(right)
        self.lib.mu_misc_boss_update(C.byref(left), 150)
        self.assertEqual(bytes(right), original)
        self.lib.mu_misc_boss_init(C.byref(left))
        self.assertEqual(tuple(getattr(left, n) for n, _ in vm.Bar._fields_), (0, 10, 10, 0, 1))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned instructions')
class Private(unittest.TestCase):
    def test_original_window_arithmetic_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_misc.py'), '--cases', '40',
                            '--mutants', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        self.assertEqual(result['total'], 200)
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(len(result['mutants_caught']), 6)


if __name__ == '__main__':
    unittest.main()
