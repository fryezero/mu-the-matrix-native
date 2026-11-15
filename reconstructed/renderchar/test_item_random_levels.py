"""The optional helper level is the caller's packed word, including its low bits."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_item_random_levels as check
import validate_renderchar as v


class ItemRandomLevels(unittest.TestCase):
    def test_packed_nine_is_distinct_from_decoded_level_one(self):
        lib = base.lib()
        case = v.classify_case(0x1712, v.CLASSIFY[0])
        case.update(quality=2, record=(0, 0x26, 0))
        results = [v.c_stream(lib, dict(case, item_level=packed)) for packed in (8, 9, 15, 16)]
        self.assertTrue(all(status == 0 for status, _ in results))
        self.assertEqual([len(stream) for _, stream in results], [5, 7, 7, 7])
        for t in gen.RANDOM_LEVEL_TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
        for t in (0x0b38, 0x0b39, 0x1710, 0x10fd, 0x1735, 0x1737, 0x1738, 0x1755):
            self.assertEqual(lib.mu_rc_item_special(t), 1, hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'random-levels.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_random_levels.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(gen.RANDOM_LEVEL_TYPES)
        for name, per_type in (('bodies', 292), ('records', 512), ('packed', 1644), ('random', 66),
                               ('clocks', 24), ('exits', 64), ('caller_guards', 3)):
            self.assertEqual(report['families'][name]['cases'], per_type * n, name)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
