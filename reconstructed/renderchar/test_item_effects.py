"""Item-link consumers and opt-in Spark03/11 instruction comparisons."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base


class ItemEffects(unittest.TestCase):
    def test_next_link_callers(self):
        import validate_item_clusters as v
        lib = base.lib()
        status, calls, consumed = v.c_effects(lib, 0x0ef4, [0]*32, 0)
        self.assertEqual((status, len(calls), consumed), (0, 5, 7))
        self.assertEqual(calls[0][2], (0, v.v.f2u(-101.5), v.v.f2u(-1.5)))
        self.assertEqual(calls[3][2], (0, v.v.f2u(99), v.v.f2u(-1)))
        status, calls, consumed = v.c_effects(lib, 0x0afc, [0]*32, 0)
        self.assertEqual((status, len(calls), consumed), (0, 2, 1))
        self.assertEqual(calls[0][2], (v.v.f2u(5), v.v.f2u(-22), v.v.f2u(-10)))
        self.assertNotEqual(calls, v.c_effects(lib, 0x0afc, [0]*32, 700.25)[1])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_private_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'spark.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_effects.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
            self.assertEqual(sum(f['cases'] for f in report['families'].values()), 1500)
            self.assertTrue(all(f['cases'] == f['equal'] for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), 3)
            self.assertTrue(all(report['mutants'].values()))
