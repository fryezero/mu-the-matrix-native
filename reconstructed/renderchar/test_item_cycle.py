"""Piecewise colour admission and complete original-instruction comparison."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_item_cycle as cycle
import validate_renderchar as v


class ItemCycle(unittest.TestCase):
    def test_entry_refusals_still_apply(self):
        lib = base.lib()
        case = v.classify_case(0x0b51, v.CLASSIFY[0])
        self.assertEqual(v.c_stream(lib, case)[0], 0)
        for field in ('a10', 'a11'):
            self.assertEqual(v.c_stream(lib, dict(case, **{field: 0}))[0], 2)
        self.assertNotIn(0x1710, gen.ALL_TYPES)
        self.assertNotIn(0x10fd, gen.ALL_TYPES)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'cycle.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_cycle.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual({k: f['cases'] for k, f in report['families'].items()},
                         dict(bodies=292, records=512, clocks=len(cycle.CLOCKS), owned=64,
                              cycle=6000, reader_refusals=4))
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(cycle.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
