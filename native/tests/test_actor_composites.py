"""RENDER-ACTORS-004: bounded composite NPC recipes and production loading."""
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
import validate_actor_composites as v


class Recipes(unittest.TestCase):
    def test_five_recipes_and_refusals(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/actors')], check=True, capture_output=True)
        lib = v.library()
        for cl in range(1024):
            self.assertEqual(lib.mu_actor_npc_recipe(cl, None), int(cl in v.CLASSES))
        self.assertIsNone(lib.mu_actor_npc_part_file(0xa13))
        self.assertEqual(lib.mu_actor_npc_part_file(0xa1a), b'Data/Npc/ManUpper02.bmd')

    def test_census_covers_fixture_selectors(self):
        with (ROOT/'docs/research/actor-construction-census.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([int(r['server_class']) for r in rows], list(range(1024)))
        by_class = {int(r['server_class']): r for r in rows}
        for cl in (374, 378, 617, 642):
            self.assertEqual(by_class[cl]['native'], 'refused')
        for cl in v.CLASSES:
            self.assertIn('sub-model/extra-load', by_class[cl]['construction'])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires private-env.sh')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            run = subprocess.run([sys.executable, str(ROOT/'scripts/validate_actor_composites.py'),
                '--cases', '20', '--output', str(report)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(run.returncode, 0, run.stdout[-5000:] + run.stderr[-3000:])
            value = json.loads(report.read_text())
            self.assertTrue(value['all_equal'])
            self.assertEqual(value['families']['native']['cases'], 10)
