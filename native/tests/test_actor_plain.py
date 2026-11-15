"""Table-driven actor plan admission, conservative exclusions and private comparison."""
import csv
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_actor_plain as v

class Plans(unittest.TestCase):
    def test_plans_and_census(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/actors')], check=True, capture_output=True)
        lib = v.library()
        groups = v.initial_rows()
        self.assertEqual(len(groups), 905)
        self.assertEqual(len({int(r['server_class']) for r in groups}), 905)
        admitted = {int(r['server_class']) for r in groups if r['decision'] == 'checked plain body plan'}
        self.assertEqual(len(admitted), 621)
        with (ROOT/'docs/research/actor-construction-census.csv').open() as f:
            census = {int(r['server_class']): r for r in csv.DictReader(f)}
        for cl in range(-1, 1025):
            plan = v.Plan()
            self.assertEqual(lib.mu_actor_plain_plan(cl, C.byref(plan)), int(cl in admitted))
            if cl in admitted:
                self.assertEqual(plan.server_class, cl)
                self.assertEqual(plan.flags, 2)
                self.assertEqual(plan.translate, 1)
                self.assertEqual(census[cl]['native'], 'correct bounded body plan')
        for cl in (1, 5, 10, 374, 378, 595, 617, 635, 642):
            self.assertNotIn(cl, admitted)
        for r in groups:
            if int(r['server_class']) not in admitted:
                self.assertTrue(r['reason'])

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires private-env.sh')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            run = subprocess.run([sys.executable, str(ROOT/'scripts/validate_actor_plain.py'),
                '--cases', '24', '--output', str(path)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(run.returncode, 0, run.stdout[-4000:]+run.stderr[-3000:])
            value = json.loads(path.read_text())
            self.assertTrue(value['all_equal'])
            self.assertEqual(value['admitted'], 621)
