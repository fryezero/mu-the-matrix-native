"""Bottle diagnostics must preserve both the idle guard and live-profile isolation."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticGuardTests(unittest.TestCase):
    def query(self, rows, profile=False, bottle='Synthetic'):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            prefix = home / 'Library/Application Support/CrossOver/Bottles' / bottle
            state = prefix / '.mu-matrix-setup'
            state.mkdir(parents=True)
            (state / 'owner').write_text('mu-matrix-crossover-32bit-v2\n')
            runtime = home / 'runtime/bin'
            runtime.mkdir(parents=True)
            wine = runtime / 'wine'
            wine.write_text('#!/bin/bash\nprintf "%s\\n" "$ROWS"\n')
            wine.chmod(0o700)
            env = dict(os.environ, HOME=str(home), CX_ROOT=str(runtime.parent), ROWS=rows)
            return subprocess.run(['bash', '-c', '''set -euo pipefail
                source "$1"
                diagnostic_bottle "$2" "$3"
            ''', 'guard', str(ROOT / 'mac-play/diagnostics/bottle.sh'), bottle,
                'live-profile' if profile else 'idle'], env=env, text=True, capture_output=True)

    def test_active_game_only_allowed_for_explicit_live_profile(self):
        rows = '"main.exe","48","Console","1","0 K"'
        self.assertNotEqual(self.query(rows).returncode, 0)
        self.assertEqual(self.query(rows, profile=True).returncode, 0)

    def test_live_profile_still_refuses_protected_bottle_and_invalid_query(self):
        rows = '"main.exe","48","Console","1","0 K"'
        self.assertNotEqual(self.query(rows, True, 'MuMatrix32').returncode, 0)
        for rows in ('', 'not a process list', rows + '\nquery error'):
            self.assertNotEqual(self.query(rows, True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
