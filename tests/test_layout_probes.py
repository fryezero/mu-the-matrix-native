"""Bounded field probes, private execution only with pinned text present."""
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import probe_layout
import pins


class LayoutProbes(unittest.TestCase):
    def test_conflicting_fields_are_separate_probes(self):
        rows = {r[0]: r for r in probe_layout.PROBES}
        self.assertEqual(rows['object_live'][4:6], (0, 1))
        self.assertEqual(rows['object_fade_flag'][4:6], (8, 1))
        self.assertEqual(rows['character_scene_level'][4:6], (0x144, 2))
        self.assertEqual(rows['character_label_level'][4:6], (0x14e, 2))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client text')
    def test_original_loads_and_competing_hypotheses(self):
        result = probe_layout.run(pins.TEXT.read(), mutations=True)
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['cases'], 7452)
        self.assertEqual(result['mutations_caught'], 7)
