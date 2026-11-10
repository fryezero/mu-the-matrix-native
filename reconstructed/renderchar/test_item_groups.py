"""RENDER-ITEMS-002X: a bypassed glow chain must also bypass forced-glow fixture records."""
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import test_renderchar as base
import classify_item_bodies as survey
import gen_item_bodies as gen
import validate_item_groups as groups
import validate_renderchar as v


class ItemGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()

    def test_survey_membership_matches_native_admission(self):
        types = set(survey.special_types())
        actual = {t for t in types if self.lib.mu_rc_item_special(t) == 0}
        self.assertEqual(survey.covered_types() & types, actual)

    def test_failed_probe_clears_derived_phase_state(self):
        previous = list(gen._PHASES)
        try:
            gen._PHASES[:] = [['previous type']]
            with mock.patch.object(gen, 'sample', return_value=None):
                self.assertIsNone(gen._fit(None, None, 0x0ef4, (), None))
            self.assertEqual(gen._PHASES, [])
        finally:
            gen._PHASES[:] = previous

    def test_levels_and_forced_glow_records_keep_the_body(self):
        for t in gen.NO_GLOW_TYPES:
            case = v.random_case_any(random.Random(t), t)
            case.update(item_level=0, quality=9, option1=0, ext=0, record=(0, 0, 0),
                        a10=0xffffffff, a11=0xffffffff)
            status, expected = v.c_stream(self.lib, case)
            self.assertEqual(status, 0, hex(t))
            self.assertTrue(expected, hex(t))
            for level in (0, 3, 7, 9, 13, 15):
                for record in ((0, 0, 0), (0, 0x26, 0), (0, 0x5b, 0)):
                    actual = v.c_stream(self.lib, dict(case, item_level=level << 3, record=record))
                    self.assertEqual(actual, (status, expected), (hex(t), level, record))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'groups.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_groups.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['families']['bodies']['cases'], 292*len(groups.TYPES))
        self.assertEqual(report['families']['records']['cases'], 512*len(groups.TYPES))
        self.assertTrue(all(report['mutants'].values()))
