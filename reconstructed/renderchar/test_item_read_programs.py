"""Later read-program admissions and private instruction comparison."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import validate_item_read_programs as programs
import validate_renderchar as v


class ItemReadPrograms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v, cls.lib = v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_admissions_preserve_the_existing_refusals(self):
        for t in programs.TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            self.assertEqual(self.draws(self.item(type=t, select=1))[0], 2, hex(t))
            self.assertEqual(self.draws(self.item(type=t, object_shadow=1))[0], 2, hex(t))
        self.assertEqual(self.lib.mu_rc_item_special(0x0b51), 1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'read-programs.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_read_programs.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(programs.TYPES)
        self.assertEqual(report['families']['bodies']['cases'], 292*n)
        self.assertEqual(report['families']['records']['cases'], 512*n)
        self.assertEqual(report['families']['clocks']['cases'], len(programs.CLOCKS)*n)
        self.assertEqual(report['families']['owned']['cases'], 64*n)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(len(report['mutants']), 6)
        self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
