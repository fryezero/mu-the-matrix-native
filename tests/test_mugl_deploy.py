"""Exercise deployment refusal and rerun behavior with synthetic files/runtime."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'mac-play/gl-batching.sh'


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / 'bottle'
        self.game = self.prefix / 'drive_c/game'
        self.state = self.prefix / '.mu-matrix-setup'
        self.scripts = self.root / 'scripts'
        for p in (self.game, self.state, self.scripts / 'mugl/build'):
            p.mkdir(parents=True)
        self.builtin = self.prefix / 'drive_c/windows/system32/opengl32.dll'
        self.builtin.parent.mkdir(parents=True)
        self.builtin.write_bytes(b'MZ' + b'\0' * 62 + b'Wine builtin DLL' + b'\0' * 20)
        self.artifact = self.scripts / 'mugl/build/opengl32.dll'
        self.artifact.write_bytes(b'authored synthetic proxy')
        self.events = self.root / 'events'
        self.wine = self.root / 'wine'
        self.wine.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$EVENTS"\n')
        self.wine.chmod(0o700)

    def run_install(self, mode='1', busy=False):
        env = dict(os.environ, PREFIX=str(self.prefix), STATE=str(self.state),
                   GAME=str(self.game), SCRIPT_DIR=str(self.scripts), BOTTLE='Test',
                   WINE=str(self.wine), EVENTS=str(self.events), MU_GL_BATCHING=mode,
                   BUSY=str(int(busy)))
        return subprocess.run(['bash', '-c', '''set -euo pipefail
            die() { echo "$*" >&2; exit 1; }
            note() { echo "$*"; }
            diagnostic_bottle() { [ "$BUSY" = 0 ] || die 'running game'; }
            source "$1"
            install_gl_batching
        ''', 'deploy', str(HELPER)], env=env, text=True, capture_output=True)

    def test_install_rerun_upgrade_and_opt_out(self):
        original = self.builtin.read_bytes()
        for data in (b'authored synthetic proxy', b'authored synthetic proxy', b'new build'):
            self.artifact.write_bytes(data)
            result = self.run_install()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((self.game / 'opengl32.dll').read_bytes(), data)
            self.assertIn('native,builtin', self.events.read_text())
            self.assertEqual(self.builtin.read_bytes(), original)
        for _ in range(2):
            result = self.run_install('0')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((self.game / 'opengl32.dll').exists())
        self.assertEqual((self.state / 'mugl.mode').read_text(), 'off\n')

    def test_foreign_system_dll_and_symlink_are_refused(self):
        self.builtin.write_bytes(b'foreign DLL')
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertFalse((self.game / 'opengl32.dll').exists())
        self.builtin.unlink()
        self.builtin.symlink_to(self.artifact)
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertFalse(self.events.exists())

    def test_unmanaged_game_dll_is_never_overwritten_or_removed(self):
        dll = self.game / 'opengl32.dll'
        dll.write_bytes(b'unrelated proxy')
        for mode in ('0', '1'):
            self.assertNotEqual(self.run_install(mode).returncode, 0)
            self.assertEqual(dll.read_bytes(), b'unrelated proxy')
        self.assertFalse(self.events.exists())

    def test_active_game_refuses_before_changes(self):
        self.assertNotEqual(self.run_install(busy=True).returncode, 0)
        self.assertFalse((self.game / 'opengl32.dll').exists())
        self.assertFalse(self.events.exists())


if __name__ == '__main__':
    unittest.main()
