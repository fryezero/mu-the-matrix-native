"""Private instruction comparisons for RENDER-WORLDS-D."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WorldsDTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-d-test-') as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_worlds_d.py'), '--cases', '600',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertEqual(sum(f['cases'] for f in r['families'].values()), 2400)
            self.assertTrue(all(f['cases'] == f['equal'] and f['stopped'] == 0 for f in r['families'].values()))
            self.assertEqual(len(r['mutants']), 8)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in r['mutants']))
