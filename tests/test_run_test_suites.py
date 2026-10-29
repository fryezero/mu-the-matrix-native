"""Portable checks of scripts/run_test_suites.py, the `make test` runner (GATE-PAR-001).

* the suite list has one home: `make test` passes the Makefile's TEST_SUITES to the runner, the runner's own list is
  that variable, no other `unittest discover` line exists, and every directory holding tracked test_*.py files
  is listed (or named below with the reason it is not);
* a deliberately failing suite makes the pool (MU_GATE_JOBS=2) exit non-zero, with its log tail and the summed
  counts, while the other suites still run; MU_GATE_JOBS=1 stops at the first failing suite, in order;
* sharding a suite per module gives the same counts as its one discovery;
* the unittest summary parser and MU_GATE_JOBS validation.
All on synthetic suites in a temporary directory.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_test_suites as rts  # noqa: E402

# Tracked test directories `make test` does not discover, with the reason. A new one fails test_every_test_dir.
NOT_DISCOVERED = {
    # never in `make test` before GATE-PAR-001 (which keeps the same tests); adding it is its owner's change
    'reconstructed/players',
}

PASSING = '''
import unittest
class T(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
    @unittest.skip('synthetic skip')
    def test_c(self): pass
'''
FAILING = '''
import unittest
class T(unittest.TestCase):
    def test_ok(self): pass
    def test_planted(self): self.assertEqual(1, 2, 'planted gate failure')
'''


def run(args, jobs, cwd=ROOT):
    env = dict(os.environ, MU_GATE_JOBS=str(jobs))
    return subprocess.run([sys.executable, str(ROOT / 'scripts/run_test_suites.py'), *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


class SuiteList(unittest.TestCase):
    def test_make_test_passes_the_makefile_list(self):
        text = (ROOT / 'Makefile').read_text()
        recipe = re.search(r'^test: all\n((?:\t[^\n]*\n)+)', text, re.M)
        self.assertIsNotNone(recipe, 'Makefile test: recipe')
        self.assertEqual(recipe.group(1).strip(), '$(PYTHON) scripts/run_test_suites.py $(TEST_SUITES)')
        self.assertNotRegex(text, r'-m unittest|unittest discover -s', 'a discover line outside TEST_SUITES')
        dry = subprocess.run(['make', '-s', '-n', '-o', 'all', '-C', str(ROOT), 'test', 'PYTHON=PY'], capture_output=True,
                             text=True, check=True).stdout.splitlines()
        call = [line for line in dry if 'run_test_suites.py' in line]
        self.assertEqual(len(call), 1, dry[-5:])
        self.assertEqual(call[0].split()[2:], rts.makefile_suites())
        listed = run(['--list'], 1)
        self.assertEqual(listed.stdout.split(), rts.makefile_suites())

    def test_every_test_dir_is_discovered(self):
        files = subprocess.run(['git', 'ls-files', '*test_*.py'], cwd=ROOT, capture_output=True, text=True,
                               check=True).stdout.split()
        dirs = {str(Path(f).parent) for f in files if Path(f).name.startswith('test_')}
        suites = set(rts.makefile_suites())
        self.assertEqual(sorted(dirs - suites - NOT_DISCOVERED), [], 'add the directory to TEST_SUITES')
        self.assertEqual(sorted(NOT_DISCOVERED & suites), [], 'listed now: drop it from NOT_DISCOVERED')
        self.assertEqual(len(rts.makefile_suites()), len(suites), 'a suite listed twice')

    def test_rejects_duplicates_and_missing(self):
        with self.assertRaises(SystemExit):
            rts.check_suites(['tests', 'tests'])
        with self.assertRaises(SystemExit):
            rts.check_suites(['no/such/suite'])


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        for name, body in (('good', PASSING), ('bad', FAILING), ('late', PASSING)):
            d = self.base / name
            d.mkdir()
            (d / f'test_{name}_one.py').write_text(body)
            (d / f'test_{name}_two.py').write_text(PASSING)

    def tearDown(self):
        self.tmp.cleanup()

    def suites(self, *names):
        return [str(self.base / n) for n in names]

    def test_failing_suite_fails_the_pool(self):
        r = run(['--logs', str(self.base / 'logs'), *self.suites('good', 'bad', 'late')], 2)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('planted gate failure', r.stdout)        # the failing log's tail
        self.assertRegex(r.stdout, r'===== \S+/bad failed \(exit 1\)')
        self.assertIn('3 suites, 17 tests, 11 passed, 5 skipped, 1 failures, 0 errors; 1 failed suite(s)', r.stdout)
        self.assertTrue((self.base / 'logs').is_dir() and len(list((self.base / 'logs').glob('*.log'))) == 3)

    def test_passing_pool(self):
        r = run(['--logs', str(self.base / 'logs'), *self.suites('good', 'late')], 3)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('2 suites, 12 tests, 8 passed, 4 skipped, 0 failures, 0 errors; 0 failed suite(s)', r.stdout)

    def test_sequential_stops_at_the_first_failure(self):
        r = run(['--logs', str(self.base / 'logs'), *self.suites('good', 'bad', 'late')], 1)
        self.assertEqual(r.returncode, 1)
        self.assertIn('planted gate failure', r.stdout)
        self.assertNotIn(str(self.base / 'late'), r.stdout)    # never started, as make stopped
        self.assertIn('2 suites, 11 tests, 7 passed, 3 skipped, 1 failures', r.stdout)

    def test_sharded_counts_equal_one_discovery(self):
        bad = str(self.base / 'bad')
        whole = run(['--logs', str(self.base / 'a'), bad], 2)
        with mock.patch.object(rts, 'SHARDED', (bad,)):
            self.assertEqual(len(rts.units(bad)), 2)
        r = subprocess.run([sys.executable, '-c', textwrap.dedent(f'''
            import sys; sys.path.insert(0, {str(ROOT / 'scripts')!r}); sys.argv[0] = 'run_test_suites.py'
            import run_test_suites as r; r.SHARDED = ({bad!r},)
            sys.exit(r.main(['--logs', {str(self.base / 'b')!r}, {bad!r}]))''')],
                           env=dict(os.environ, MU_GATE_JOBS='2'), capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn('2 work items', r.stdout)
        line = lambda out: re.search(r'run_test_suites: 1 suites, .*?errors', out).group(0)
        self.assertEqual(line(r.stdout), line(whole.stdout))
        self.assertIn('planted gate failure', r.stdout)

    def test_counts_and_jobs(self):
        c = rts.counts('Ran 9 tests in 0.1s\n\nFAILED (failures=1, errors=2, skipped=3, expected failures=1)\n')
        self.assertEqual((c['ran'], c['failures'], c['errors'], c['skipped'], rts.passed(c)), (9, 1, 2, 3, 2))
        self.assertEqual(rts.passed(rts.counts('Ran 4 tests in 0.0s\n\nOK (skipped=1)\n')), 3)
        for bad in ('0', '-1', 'x'):
            with mock.patch.dict(os.environ, MU_GATE_JOBS=bad), self.assertRaises(SystemExit):
                rts.jobs_from_env()
        with mock.patch.dict(os.environ, MU_GATE_JOBS=''):
            self.assertEqual(rts.jobs_from_env(), max(1, min(4, (os.cpu_count() or 2) // 2)))


if __name__ == '__main__':
    unittest.main()
