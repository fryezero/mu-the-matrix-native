"""Exercise the real launch/reset guard with an isolated fake CrossOver runtime."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'mac-play/start-launcher.sh'

class LauncherResetTests(unittest.TestCase):
    def run_launcher(self, tasks, query_status=0, display_status=0, server_status=0):
        with tempfile.TemporaryDirectory(prefix='mu launcher ') as tmp:
            root = Path(tmp)
            runtime = root / 'CrossOver runtime'
            (runtime / 'bin').mkdir(parents=True)
            prefix = root / 'TestBottle'
            (prefix / '.mu-matrix-setup').mkdir(parents=True)
            game = prefix / 'drive_c' / 'MuTheMatrix-TestBottle'
            game.mkdir(parents=True)
            (game / 'MuTheMatrix.exe').touch()
            (prefix / 'drive_c/MuMatrixTools').mkdir()
            (prefix / 'drive_c/MuMatrixTools/MonitorCheck.exe').touch()
            events = root / 'events'
            wine = runtime / 'bin/wine'
            wine.write_text('''#!/bin/bash
printf '%s|%s\\n' "$WINEPREFIX" "$*" >> "$EVENTS"
case "$*" in
 *MonitorCheck.exe*) exit "$DISPLAY_STATUS" ;;
 *tasklist*) printf '%s\\n' "$MOCK_TASKS"; exit "$QUERY_STATUS" ;;
esac
''')
            server = runtime / 'bin/wineserver'
            server.write_text('#!/bin/bash\nprintf "server|%s|%s\\n" "$WINEPREFIX" "$*" >> "$EVENTS"\nexit "$SERVER_STATUS"\n')
            wine.chmod(0o700)
            server.chmod(0o700)
            env = dict(os.environ, CX_ROOT=str(runtime), CX_BOTTLE='TestBottle',
                       WINEPREFIX=str(prefix), MU_GAME_DIR=str(game), EVENTS=str(events),
                       MOCK_TASKS=tasks, QUERY_STATUS=str(query_status),
                       DISPLAY_STATUS=str(display_status), SERVER_STATUS=str(server_status))
            result = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True)
            return result, events.read_text() if events.exists() else '', str(prefix)

    def test_idle_bottle_resets_then_launches(self):
        result, events, prefix = self.run_launcher('"services.exe","24","Console","1","100 K"')
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = events.splitlines()
        self.assertIn('tasklist', lines[0])
        self.assertEqual(lines[1], f'server|{prefix}|-k')
        self.assertEqual(lines[2], f'server|{prefix}|-w')
        self.assertIn('MonitorCheck.exe', lines[3])
        self.assertIn('MuTheMatrix.exe', lines[4])

    def test_running_game_is_never_killed_or_relaunched(self):
        result, events, _ = self.run_launcher('"MAIN.EXE","100","Console","1","100 K"')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already running', result.stderr)
        self.assertNotIn('server|', events)
        self.assertNotIn('MuTheMatrix.exe', events)

    def test_existing_launcher_is_never_killed(self):
        result, events, _ = self.run_launcher('"MuTheMatrix.exe","100","Console","1","100 K"')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already running', result.stderr)
        self.assertNotIn('server|', events)

    def test_failed_query_refuses_reset(self):
        result, events, _ = self.run_launcher('', query_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('server|', events)

    def test_failed_display_check_prevents_launcher(self):
        result, events, _ = self.run_launcher('"tasklist.exe","24","Console","1","0 K"', display_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('MonitorCheck.exe', events)
        self.assertNotIn('MuTheMatrix.exe', events)

    def test_failed_server_reset_prevents_launcher(self):
        result, events, _ = self.run_launcher('"tasklist.exe","24","Console","1","0 K"', server_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('MonitorCheck.exe', events)
        self.assertNotIn('MuTheMatrix.exe', events)

    def test_unrecognised_output_refuses_reset(self):
        for tasks in ('', 'unrecognised tasklist output',
                      '"tasklist.exe","24","Console","1","0 K"\nquery failed'):
            with self.subTest(tasks=tasks):
                result, events, _ = self.run_launcher(tasks)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('server|', events)

if __name__ == '__main__':
    unittest.main()
