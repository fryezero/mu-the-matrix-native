"""Private instruction comparisons for RENDER-WORLDS-E."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]

class WorldsEInstructions(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_e.py'),'--cases','600',
                            '--mutations','--output',str(path)],check=True,capture_output=True)
            r = json.loads(path.read_text())
            self.assertEqual(sum(t['cases'] for t in r['families'].values()),4840)
            self.assertTrue(all(t['cases']==t['equal'] and not t['stopped'] for t in r['families'].values()))
            self.assertEqual(len(r['mutants']),12)
            self.assertTrue(all(m['caught'] for m in r['mutants']))
