"""The clock falloff reader accepts only the checked branch form."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_item_falloff as check


class ItemFalloff(unittest.TestCase):
    def test_falloff_rounding_and_positive_zero(self):
        import validate_renderchar as v
        threshold, top = v.f2u(-0.3), v.f2u(0.3)
        for x, expected in ((-1.0, 1.0), (-0.2, 0.5),
                            (1.0, 0.0), (v.u2f(top), 0.0)):
            program = ((gen.C_TIME_F, 0), (gen.C_F_FALLOFF, threshold | top << 32))
            self.assertEqual(gen.clock_value(program, v.u2f(v.f2u(x))), v.f2u(expected))
        lib = base.lib()
        for t in gen.FALLOFF_TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'falloff.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_falloff.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['families']['bodies']['cases'], 292 * 4)
        self.assertEqual(report['families']['records']['cases'], 512 * 4)
        self.assertEqual(report['families']['clocks']['cases'], 24 * 4)
        self.assertEqual(report['families']['ticks']['cases'], sum(check.PERIODS.values()))
        self.assertEqual(report['families']['exits']['cases'], 64 * 4)
        self.assertEqual(report['families']['reader_refusals']['cases'], 5)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
