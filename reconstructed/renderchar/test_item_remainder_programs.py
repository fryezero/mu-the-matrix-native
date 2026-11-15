"""The five new producers preserve ordered requests and explicit consumer refusals."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_owner_fx as fx
import validate_item_remainder_programs as check


class ItemRemainderPrograms(unittest.TestCase):
    def test_admitted_producers_have_body_and_pre_program(self):
        lib = base.lib()
        self.assertEqual(len(fx.REMAINDER_PROGRAM_TYPES), 5)
        for t in fx.REMAINDER_PROGRAM_TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
            self.assertEqual(lib.mu_rc_item_pre_fx(t), 1, hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'programs.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_remainder_programs.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['families']['bodies']['cases'], 292 * 5)
        self.assertEqual(report['families']['records']['cases'], 512 * 5)
        self.assertEqual(report['families']['clocks']['cases'], 24 * 5)
        self.assertEqual(report['families']['owned']['cases'], 64 * 5)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
