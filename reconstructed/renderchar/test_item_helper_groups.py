"""The body caller's late level override and its omitted base draw."""
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_renderchar as v


class ItemHelperGroups(unittest.TestCase):
    def test_positive_levels_use_the_late_seven_chain(self):
        lib = base.lib()
        for t in gen.LATE_GLOW_TYPES:
            case = v.random_case_any(random.Random(t), t)
            case.update(item_level=7 << 3, quality=9, record=None, render_type=2, option1=0, ext=0,
                        a10=0xffffffff, a11=0xffffffff)
            status, expected = v.c_stream(lib, case)
            self.assertEqual(status, 0)
            self.assertEqual(len(expected), 2)
            for level in range(1, 16):
                self.assertEqual(v.c_stream(lib, dict(case, item_level=level << 3)), (status, expected), (hex(t), level))
            self.assertEqual(len(v.c_stream(lib, dict(case, item_level=0))[1]), 1)

    def test_omitted_base_keeps_the_glow_chain(self):
        lib = base.lib()
        case = v.random_case_any(random.Random(0x2368), 0x2368)
        case.update(quality=9, record=None, render_type=2, option1=0, ext=0,
                    a10=0xffffffff, a11=0xffffffff)
        self.assertEqual(v.c_stream(lib, dict(case, item_level=0)), (0, []))
        status, draws = v.c_stream(lib, dict(case, item_level=7 << 3))
        self.assertEqual(status, 0)
        self.assertEqual(len(draws), 1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'helper-groups.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_helper_groups.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['families']['bodies']['cases'], 292*len(gen.HELPER_TYPES))
        self.assertEqual(report['families']['records']['cases'], 512*len(gen.HELPER_TYPES))
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(len(report['mutants']), 4)
        self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
