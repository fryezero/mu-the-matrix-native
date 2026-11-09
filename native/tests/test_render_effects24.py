"""RENDER-EFFECTS-024: sprite textures, exact bone names and Ferea's emitter."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_render_effects24 as r24
import validate_particles as pt

PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME = os.environ.get('MU_GAME_ROOT')


class Native(unittest.TestCase):
    def test_native_bitmap_files_filter_wrap_and_emitter(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/libmunative.a',
                        'build/libmusession_world.a'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            report = pt.Report()
            r24.native_checks(r24.build_host(tmp), r24.bitmap_fixture(tmp), report)
        self.assertEqual(report.families['native']['cases'], 4)
        self.assertEqual(report.families['native']['first_failures'], [])
        self.assertEqual(report.families['native']['equal'], 4)


@unittest.skipUnless(PRIVATE, 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        for directory in ('native', 'reconstructed/particles', 'reconstructed/combat'):
            subprocess.run(['make', '-s', '-C', str(ROOT/directory)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects24.py'), '--cases', '20',
                            '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertEqual(report['cases'], 226)


@unittest.skipUnless(PRIVATE and GAME, 'requires private environment and MU_GAME_ROOT')
class Installed(unittest.TestCase):
    def test_hammer14_authored_variants_keep_exact_names(self):
        sys.path.insert(0, str(ROOT/'model-recovery'))
        from bmd_encrypted import parse_model_file
        data = Path(GAME)/'Data'
        paths = sorted(p for p in data.rglob('*') if p.is_file() and p.suffix.lower() == '.bmd' and
                       re.fullmatch(r'hammer14(?:[^0-9].*)?', p.stem.casefold()))
        self.assertTrue(paths, 'no authored Hammer14 variants found')
        for path in paths:
            model = parse_model_file(path, client_layout=True)
            names = [b['name']['text'] for b in model['bones'] if not b['dummy']]
            self.assertIn('up01 ', names, path.name)
            self.assertNotIn('up01', names, path.name)

    def test_ferea_fire_emitter_reaches_native_particles(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/mu-world'],
                       check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp)/'mu-world'
            shutil.copy2(ROOT/'native/build/mu-world', binary)
            args = [str(binary), '--game-root', GAME, '--world', '112', '--tile', '236,152',
                    '--headless', '--backend', 'soft', '--no-audio', '--hero-name', 'DemoKnight',
                    '--width', '320', '--height', '240', '--frames', '21', '--every', '20',
                    '--time-series-every', '21', '--out-dir', tmp]
            snapshot = os.environ.get('MU_SNAPSHOT_DIR')
            self.assertTrue(snapshot, 'requires MU_SNAPSHOT_DIR for DATA-ACQ-002 Ferea placements')
            objects = Path(snapshot)/'data-acq-002/plain'
            self.assertTrue(objects.is_dir(), 'requires MU_SNAPSHOT_DIR/data-acq-002/plain')
            args += ['--objects-dir', str(objects)]
            run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        rows = [json.loads(s) for s in run.stdout.splitlines() if s.startswith('{')]
        effects = next(r for r in rows if r.get('joints') is True)
        self.assertGreater(effects['effects_created'], 0)
        self.assertEqual(effects['effects_unsupported'], 0)
        particles = next(r for r in rows if r.get('particles') is True)
        self.assertGreater(particles['created'], 0)
        # Clouds/28 remain a separate, counted refusal. Do not claim a whole-world zero.
        self.assertGreater(particles['unsupported'], 0)


if __name__ == '__main__':
    unittest.main()
