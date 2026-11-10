"""RENDER-ACTORS-001: body recipes and the production Player-model actor loader."""
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
import validate_actor_recipes as v


class Recipes(unittest.TestCase):
    def test_census_matches_class_table(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/actors')], check=True, capture_output=True)
        lib = v.library(v.LIBRARY)
        lib.mu_monster_class_find.argtypes = [C.c_uint32]
        lib.mu_monster_class_find.restype = C.POINTER(v.Row)
        found = set()
        for cl in range(0x400):
            row = lib.mu_monster_class_find(cl)
            if row and row.contents.kind == 3: found.add(cl)
        self.assertEqual(found, set(v.CENSUS))

    def test_census_and_skeleton_whole_bodies(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/actors')], check=True, capture_output=True)
        lib = v.library(v.LIBRARY)
        for cl in v.CENSUS + (-1, 0, 251, 65535):
            with self.subTest(cl=cl):
                row = v.Row()
                self.assertEqual(lib.mu_actor_player_recipe(cl, C.byref(row)), int(cl in v.FIXED))
                if cl in v.WHOLE:
                    self.assertEqual(row.slots[0].type, lib.mu_actor_player_body(cl))
                    self.assertTrue(lib.mu_actor_player_body_file(row.slots[0].type))
                    self.assertEqual(row.slots[0].level, 8 if cl == 236 else 0)
                elif cl in v.FIXED:
                    self.assertGreater(row.slots[1].type, 0xae6)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires private-env.sh')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        for directory in ('reconstructed/actors', 'reconstructed/renderchar'):
            subprocess.run(['make', '-s', '-C', str(ROOT/directory)], check=True, capture_output=True)
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), '-j4', 'world'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_actor_recipes.py'),
                                     '--cases', '24', '--output', str(report)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-4000:]+result.stderr[-2000:])
            value = json.loads(report.read_text())
            self.assertTrue(value['all_equal'])
            self.assertEqual(value['families']['native']['cases'], 32)
