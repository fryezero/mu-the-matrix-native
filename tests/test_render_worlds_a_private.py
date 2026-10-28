"""Private RENDER-WORLDS-A instruction comparison, pinned captures only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class RenderWorldsAPrivate(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned captures')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_worlds_a.py'),
                            '--cases','1000','--mutations','--output',str(output)],check=True,capture_output=True)
            result=json.loads(output.read_text())
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['families']),9)
        self.assertEqual(len(result['mutations']),13)
