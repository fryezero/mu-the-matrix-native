"""Low-level caller recipes keep the original caller and body boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import item_caller_groups as callers
import validate_item_caller_groups as check
import validate_renderchar as v


class ItemCallerGroups(unittest.TestCase):
    def test_caller_header_reproduction_and_membership(self):
        rows = {t: 0x3f666666 if scale else 0x3f800000
                for _, _, _, members, scale, _ in callers.GROUPS for t in members}
        self.assertEqual(len(rows), 9)
        self.assertEqual((base.ROOT/'reconstructed/renderchar/item_caller_groups.h').read_text(), callers.render(rows))
        self.assertEqual(set(rows), set(callers.TYPES))

    def test_low_caller_preserves_unwritten_entry_fields(self):
        lib = base.lib()
        for t in callers.TYPES:
            case = v.classify_case(t, v.CLASSIFY[0])
            case.update(item_level=0, quality=9, model_level=37,
                        model_shade=tuple(map(v.f2u, (0.25, 0.5, 0.75))))
            status, stream = v.c_stream(lib, case)
            self.assertEqual(status, 0, hex(t))
            self.assertEqual(stream[0][3:5], (37, case['model_shade']), hex(t))
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
        # Existing independent-state failures remain refused.
        for t in (0x1710, 0x10fd, 0x2003, 0x2007, 0x200f, 0x2010):
            self.assertEqual(lib.mu_rc_item_special(t), 1, hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'callers.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_caller_groups.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['families']['bodies']['cases'], 292 * len(callers.TYPES))
        self.assertEqual(report['families']['records']['cases'], 512 * len(callers.TYPES))
        self.assertEqual(report['families']['clocks']['cases'], 64 * len(callers.TYPES))
        self.assertEqual(report['families']['exits']['cases'], 64 * len(callers.TYPES))
        self.assertEqual(report['families']['reader_refusals']['cases'], 5)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
