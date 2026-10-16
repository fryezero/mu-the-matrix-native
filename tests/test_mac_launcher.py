"""Exercise the real launch/reset guard with an isolated fake CrossOver runtime."""
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'mac-play/start-launcher.sh'

class LauncherResetTests(unittest.TestCase):
    def run_launcher(self, tasks, query_status=0, display_status=0, server_status=0,
                     fast_mode="auto", installed=False, stale=False, fast_status=0, modified=False):
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
            cache = root / 'fast cache'
            tools = root / 'tools'
            tools.mkdir()
            commit = 'ab1a6a032e488c0d6eade54ce70a02d653277810'
            for name, body in {
                'sw_vers': '#!/bin/bash\necho TEST_OS\n',
                'cksum': '#!/bin/bash\necho TEST_RUNTIME\n'
                         'if [ -f "$MU_FAST_X87_HOME/source/build/libtimewalker.dylib" ]; then\n'
                         '  "$REAL_CKSUM" "$MU_FAST_X87_HOME/source/build/libtimewalker.dylib"\nfi\n',
                'git': f'#!/bin/bash\ncase "$*" in *rev-parse*) echo {commit};; esac\n',
            }.items():
                tool = tools / name
                tool.write_text(body)
                tool.chmod(0o700)
            if installed:
                for name in ('scripts/run-crossover.sh', 'build/libtimewalker.dylib',
                             'build/x87-loader-wrapper', 'build/x87/bin/runtime_loader',
                             'build/x87/bin/libRuntimeRosettax87'):
                    path = cache / 'source' / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('#!/bin/bash\nprintf "fast|%s|%s\\n" "$TIMEWALKER_CROSSOVER_ROOT" "$*" >> "$EVENTS"\n'
                                    'if [[ "$*" = *MuTheMatrix.exe* ]]; then exit "$FAST_STATUS"; fi\n'
                                    'exec "$CX_ROOT/bin/wine" "$@"\n')
                    path.chmod(0o700)
                (cache / 'validated').write_text('STALE\n' if stale else 'TEST_OS\nTEST_RUNTIME\n')
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
                       DISPLAY_STATUS=str(display_status), SERVER_STATUS=str(server_status),
                       MU_FAST_X87=fast_mode, MU_FAST_X87_HOME=str(cache),
                       FAST_STATUS=str(fast_status), REAL_CKSUM=shutil.which('cksum'), PATH=str(tools) + os.pathsep + os.environ['PATH'])
            if installed and not stale:
                identity = subprocess.check_output(
                    ['bash', '-c', 'source "$1"; fast_x87_identity', 'identity', str(SCRIPT.parent / 'fast-x87.sh')], env=env)
                (cache / 'validated').write_bytes(identity)
            if modified:
                (cache / 'source/build/libtimewalker.dylib').write_text('changed build output')
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


    def test_validated_fast_path_keeps_plain_display_check_then_launches(self):
        result, events, _ = self.run_launcher('"services.exe","24","Console","1","0 K"', installed=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = events.splitlines()
        self.assertIn('tasklist', lines[0])
        self.assertIn('server|', lines[1])
        self.assertIn('server|', lines[2])
        self.assertNotIn('fast|', lines[3])
        self.assertIn('MonitorCheck.exe', lines[3])
        self.assertIn('fast|', lines[-1])
        self.assertIn('MuTheMatrix.exe', lines[-1])

    def test_stale_install_falls_back_to_plain(self):
        result, events, _ = self.run_launcher('"services.exe","24","Console","1","0 K"', installed=True, stale=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('fast|', events)
        self.assertIn('stale', result.stdout)

    def test_modified_build_output_falls_back(self):
        result, events, _ = self.run_launcher('"services.exe","24","Console","1","0 K"', installed=True, modified=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('fast|', events)

    def test_explicit_plain_bypasses_installed_fast_path(self):
        result, events, _ = self.run_launcher('"services.exe","24","Console","1","0 K"', installed=True, fast_mode='0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('fast|', events)

    def test_required_missing_install_refuses_before_reset(self):
        result, events, _ = self.run_launcher('"services.exe","24","Console","1","0 K"', fast_mode='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(events, '')

    def test_fast_failure_does_not_retry_launcher(self):
        result, events, _ = self.run_launcher('"services.exe","24","Console","1","0 K"', installed=True, fast_status=7)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(events.count('MuTheMatrix.exe'), 1)

    def test_running_game_blocks_installed_fast_path(self):
        result, events, _ = self.run_launcher('"main.exe","24","Console","1","0 K"', installed=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('server|', events)
        self.assertNotIn('fast|', events)

if __name__ == '__main__':
    unittest.main()
