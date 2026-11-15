"""Pre-draw producers behind RenderObjDraw's decoded item level."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_owner_fx as fx
import validate_item_gated_programs as check


class ItemGatedPrograms(unittest.TestCase):
    def test_gated_producers_have_body_and_level_program(self):
        lib = base.lib()
        self.assertEqual(fx.GATED_PROGRAM_TYPES, [0x0b2b, 0x0b2c, 0x0b2d, 0x0b2e, 0x0b32])
        self.assertEqual(fx.OP['level'], 51)
        for t in fx.GATED_PROGRAM_TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
            self.assertEqual(lib.mu_rc_item_pre_fx(t), 1, hex(t))
        for t in (0x0b2f, 0x0b30, 0x0b31, 0x1318):
            self.assertEqual(lib.mu_rc_item_special(t), 1, hex(t))
            self.assertEqual(lib.mu_rc_item_pre_fx(t), 0, hex(t))
        # Every gated program reads the level once, compares it with nine and leaves below it.
        header = (base.HERE/'item_owner_fx.h').read_text()
        self.assertEqual(len(re.findall(r'\n    \{51, \d+, 0, 0, 0, 0, 0x00000000u\},\n    \{1, \d+, 0, 0, 0, 0, 0x00000009u\},'
                                        r'\n    \{34, \d+, \d+, 0, 0, 2, 0x[0-9a-f]{8}u\},', header)), 5)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'gated.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_gated_programs.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(fx.GATED_PROGRAM_TYPES)
        for name, per_type in (('bodies', 292), ('records', 512), ('clocks', 24), ('owned', 64),
                               ('levels', 3 * len(check.LEVEL_WORDS)), ('exits', 64)):
            self.assertEqual(report['families'][name]['cases'], per_type * n, name)
        self.assertEqual(report['families']['reader_refusals']['cases'], 4)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual({report['families']['levels']['coverage'][hex(t)] for t in fx.GATED_PROGRAM_TYPES}, {9})
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
