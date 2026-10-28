"""SESSION-GLOBALS-001: real lifecycle parity, including different inputs on re-entry."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_native_combat import write_combat_world
from test_native_helpers import write_helper_models

NATIVE = Path(__file__).resolve().parents[1]
ROOT = NATIVE.parent


class SessionGlobals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/session-repeat-host',
                        'build/world-repeat-host', 'build/globals-owner-host'], check=True, capture_output=True)

    def compare(self, host, pairs, base):
        sequential = base / 'sequential'
        sequential.mkdir()
        env = dict(os.environ)
        for key in ('MU_LANG_DIR', 'MU_GAME_ROOT', 'MU_SKILL_DEMO', 'MU_AUDIO_CUE_LOG', 'MU_QUEST_SCENARIO'):
            env.pop(key, None)
        def invoke(out, runs):
            subprocess.run([str(NATIVE / 'build' / host), str(out),
                            *[str(v) for pair in runs for v in pair]], cwd=ROOT, env=env,
                           check=True, capture_output=True, timeout=120)
        invoke(sequential, pairs)
        for i, pair in enumerate(pairs):
            fresh = base / f'fresh-{i}'
            fresh.mkdir()
            invoke(fresh, [pair])
            for file in fresh.iterdir():
                self.assertEqual((sequential / f'{i}{file.suffix}').read_bytes(), file.read_bytes(),
                                 f'{host}: run {i}, {pair}, {file.suffix}')
        return sequential

    def test_all_fixtures_twice_match_fresh_process_journals_and_state(self):
        scenarios = sorted((NATIVE / 'fixture/scenarios').glob('*.scn'))
        self.assertGreaterEqual(len(scenarios), 8)
        with tempfile.TemporaryDirectory() as tmp:
            pairs = [(s, seed) for seed in (17, 29) for s in scenarios]
            self.compare('session-repeat-host', pairs, Path(tmp))

    def test_world_reentry_with_different_language_and_skills_matches_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = write_combat_world(base / 'game')
            write_helper_models(game)
            pairs = []
            for i in range(2):
                lang = base / f'lang-{i}'
                lang.mkdir()
                (lang / 'globaltext.txt').write_text(f'0\tHelvetica\n484\tvisit-{i}\n')
                (lang / 'demo.txt').write_text(f'list 1 {'19' if i == 0 else '41 22'}\n')
                pairs.append((game, lang))
            out = self.compare('world-repeat-host', pairs, base)
            self.assertIn(b'"learned":2', (out / '1.txt').read_bytes().replace(b' ', b''))
            self.assertIn(b'"drawn_imps":1', (out / '1.txt').read_bytes().replace(b' ', b''))

    def test_overlapping_owners_survive_other_owner_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = write_combat_world(base / 'game')
            write_helper_models(game)
            args = []
            for i in range(2):
                lang = base / f'lang-{i}'
                lang.mkdir()
                (lang / 'globaltext.txt').write_text(f'484\tvisit-{i}\n')
                args.append(lang)
            demos = [base / 'one.txt', base / 'two.txt']
            demos[0].write_text('list 1 19\n')
            demos[1].write_text('list 1 41\n')
            r = subprocess.run([str(NATIVE / 'build/globals-owner-host'), str(game),
                                *map(str, args + demos)], cwd=ROOT, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stdout.decode() + r.stderr.decode())
            self.assertIn(b'independent world', r.stdout)
