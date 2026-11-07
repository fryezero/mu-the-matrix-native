"""RENDER-EFFECTS-018: the Muun effect table through the production host (loader, slot refresh 0x009af6f6 /
0x009af699 / 0x0114203d, the OBJECT update 0x0129f671) and Uruk's keyed effect 0x806e/12 with its flame particles
through the native routes; the pinned instruction comparisons run separately (scripts/validate_render_effects18.py)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
ROOT = NATIVE.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_effect import billboard, particle_system  # noqa: E402

# Synthetic rows (code, path, x, y, z, rx, ry, rz, scale, bone, follow): code 363 twice (multimap order), 183 placed
# without following its bone, 400's template is absent.
TABLE = '''# synthetic
#code\tpath\tx\ty\tz\trx\try\trz\tscale\tbone\tfollow
173\tData\\\\Effect\\\\fxa.ein\t-55.0\t11.0\t0.0\t1.5\t0.9\t0.0\t9.0\t5\t1
183\tData\\\\Effect\\\\fxb.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t10.0\t5\t0
363\tData\\\\Effect\\\\fxa.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t30.0\t26\t1
363\tData\\\\Effect\\\\fxb.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t10.0\t50\t1
400\tData\\\\Effect\\\\missing.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t9.0\t3\t1
'''


def run_host(root, lang, *codes):
    subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/muun-effects-host'], check=True, capture_output=True)
    out = subprocess.run([str(NATIVE/'build/muun-effects-host'), str(root), str(lang), *map(str, codes)],
                         check=True, capture_output=True, text=True).stdout
    return [json.loads(line) for line in out.splitlines()]


class MuunHost(unittest.TestCase):
    def test_synthetic_table_slot_and_update(self):
        with tempfile.TemporaryDirectory() as td:
            root, lang = Path(td)/'root', Path(td)/'lang'
            (root/'Data/Effect').mkdir(parents=True)
            lang.mkdir()
            (root/'Data/Effect/fxa.ein').write_text(json.dumps(particle_system(Scale=2.0)))
            (root/'Data/Effect/fxb.ein').write_text(json.dumps(billboard()))
            (lang/'muuneffects.tsv').write_text(TABLE)
            rows = run_host(root, lang)
            absent = run_host(root, Path(td)/'nothing')
        self.assertEqual(absent, [{'table': False}])
        self.assertEqual(rows[0], {'table': True, 'entries': 5, 'codes': 4})
        by_code = {r['code']: r for r in rows[1:-1]}
        self.assertEqual(sorted(by_code), [173, 183, 363, 400])
        # one entry per code, 363's two in file order with their own bones; template scale = the requested scale
        self.assertEqual(by_code[173]['bones'], [[5, 1, 9.0]])
        self.assertEqual(by_code[183]['bones'], [[5, 0, 10.0]])
        self.assertEqual(by_code[363]['bones'], [[26, 1, 30.0], [50, 1, 10.0]])
        # the absent template: requested, refused by the factory, nothing attached (the gate itself passed)
        self.assertEqual((by_code[400]['attached'], by_code[400]['requested'], by_code[400]['invalid'],
                          by_code[400]['records']), (1, 1, 1, 0))
        for code in (173, 183, 363):
            self.assertTrue(by_code[code]['matrices'])
            self.assertEqual(by_code[code]['updates'], 30 * len(by_code[code]['bones']))
        # following bone 5 places the effect at the bone's frame (3*5, -2*5, 45) x 1.2 around the OBJECT, the
        # unfollowed record at the bone's translation added to the position without the scale (0x012a0030)
        self.assertEqual(by_code[173]['at'], [12818.0, 12988.0, 234.0])
        self.assertEqual(by_code[183]['at'], [12815.0, 12990.0, 225.0])
        summary = rows[-1]
        self.assertEqual((summary['requested'], summary['invalid'], summary['attached'], summary['placed']),
                         (5, 1, 4, 4))
        # a foreign owner key, an inactive slot and no render-info record refuse; a refresh clears first
        self.assertEqual(summary['gate'], [0, 0, 0, 1, 1])
        self.assertEqual(summary['refresh'], [1, 1])
        self.assertEqual(summary['cleared'], 5)
        # timed 0.25 with dt 0.1: alive after two updates, expired in the third
        self.assertEqual((summary['expired'], summary['left'], summary['scaled']), (1, 0, 2))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT') and
                     os.environ.get('MU_LANG_DIR') and
                     (Path(os.environ.get('MU_LANG_DIR', '/nonexistent'))/'muuneffects.tsv').is_file(),
                     'requires the installed game and the local muuneffects.tsv')
class InstalledMuun(unittest.TestCase):
    def test_sixteen_records_load_attach_and_follow_their_bones(self):
        rows = run_host(os.environ['MU_GAME_ROOT'], os.environ['MU_LANG_DIR'])
        self.assertEqual(rows[0], {'table': True, 'entries': 16, 'codes': 15})
        summary = rows[-1]
        self.assertEqual((summary['requested'], summary['invalid'], summary['attached'], summary['placed']),
                         (16, 0, 16, 15))
        self.assertTrue(all(r['matrices'] for r in rows[1:-1]))
        self.assertEqual(sorted({b[0] for r in rows[1:-1] for b in r['bones']}), [3, 5, 26, 50])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            env = dict(os.environ)
            env.pop('MU_LANG_DIR', None)   # the registry's case count: the synthetic families only
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects18.py'),
                            '--cases', '20', '--mutations', '--output', str(out)], check=True, capture_output=True,
                           env=env)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'], CASES)
        self.assertEqual(len(report['mutants']), MUTANTS)


CASES, MUTANTS = 540, 35   # the registry row (scripts/validators.toml)


if __name__ == '__main__':
    unittest.main()
