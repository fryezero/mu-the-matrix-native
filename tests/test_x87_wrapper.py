"""Compile the authored wrapper and observe both exec paths with fake loaders."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'mac-play/x87-main-only-wrapper.c'


class X87WrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc')
        if not compiler:
            raise RuntimeError('A C compiler is required for the loader wrapper tests')
        cls.tmp = tempfile.TemporaryDirectory(prefix='mu wrapper ')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        # Its own path must never count as a match.
        cls.wrapper = cls.root / 'main.exe wrapper'
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(SOURCE), '-o', str(cls.wrapper)], check=True)
        cls.runtime = cls.root / 'runtime loader'
        cls.real = cls.root / 'real loader'
        for path, label in ((cls.runtime, 'runtime'), (cls.real, 'real')):
            path.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                            f'print(json.dumps([{label!r}, sys.argv, '
                            'os.getenv("TIMEWALKER_X87_ONLY")]))\n'
                            'sys.exit(int(os.getenv("FAKE_EXIT", "0")))\n')
            path.chmod(0o700)

    def run_wrapper(self, args, only='main.exe', **overrides):
        env = dict(os.environ, TIMEWALKER_X87_RUNTIME_LOADER=str(self.runtime),
                   TIMEWALKER_X87_REAL_LOADER=str(self.real), FAKE_EXIT='0')
        env.pop('TIMEWALKER_X87_ONLY', None)
        if only is not None:
            env['TIMEWALKER_X87_ONLY'] = only
        env.update(overrides)
        return subprocess.run([str(self.wrapper), *args], env=env,
                              text=True, capture_output=True)

    def assert_route(self, args, only, fast):
        result = self.run_wrapper(args, only)
        self.assertEqual(result.returncode, 0, result.stderr)
        route, argv, inherited_filter = json.loads(result.stdout)
        self.assertEqual(route, 'runtime' if fast else 'real')
        self.assertEqual(argv, ([str(self.runtime), str(self.real)] if fast else
                               [str(self.real)]) + args)
        self.assertEqual(inherited_filter, only)

    def test_case_insensitive_substring_in_any_argument(self):
        for args, only in [([r'C:\Game Folder\MAIN.EXE', '', 'a "quote"'], 'main.exe'),
                           (['--flag', 'prefix-MaIn.ExE-suffix', 'last'], 'main.exe'),
                           (['fp_x87.exe'], 'fp_x87')]:
            with self.subTest(args=args):
                self.assert_route(args, only, True)

    def test_launcher_and_nonmatches_bypass_runtime_preserving_arguments(self):
        for args in ([r'C:\Game Folder\MuTheMatrix.exe', '--flag', '', '$literal'],
                     ['main.ex', 'main', 'exe'], [], ['']):
            with self.subTest(args=args):
                self.assert_route(args, 'main.exe', False)

    def test_empty_and_unset_filter_apply_to_everything(self):
        for only in ('', None):
            for args in ([], ['MuTheMatrix.exe']):
                with self.subTest(only=only, args=args):
                    self.assert_route(args, only, True)

    def test_exit_status_is_forwarded_on_both_paths(self):
        for arg in ('main.exe', 'MuTheMatrix.exe'):
            self.assertEqual(self.run_wrapper([arg], FAKE_EXIT='23').returncode, 23)

    def test_missing_environment_or_unavailable_loader_fails_closed(self):
        for key in ('TIMEWALKER_X87_RUNTIME_LOADER', 'TIMEWALKER_X87_REAL_LOADER'):
            for value in ('', str(self.root / 'missing')):
                for arg in ('main.exe', 'MuTheMatrix.exe'):
                    with self.subTest(key=key, value=value, arg=arg):
                        result = self.run_wrapper([arg], **{key: value})
                        self.assertEqual(result.returncode, 127)
                        self.assertEqual(result.stdout, '')
                        self.assertIn('mu-x87:', result.stderr)

    def test_exec_failure_returns_127_on_both_paths(self):
        # A searchable directory passes access(X_OK), but cannot be executed.
        for arg, key in [('main.exe', 'TIMEWALKER_X87_RUNTIME_LOADER'),
                         ('MuTheMatrix.exe', 'TIMEWALKER_X87_REAL_LOADER')]:
            result = self.run_wrapper([arg], **{key: str(self.root)})
            self.assertEqual(result.returncode, 127)
            self.assertIn('could not launch', result.stderr)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
