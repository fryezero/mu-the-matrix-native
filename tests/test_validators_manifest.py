"""Portable checks of scripts/validators.toml and scripts/run_validators.py (VERIFY-HARNESS-001).

* every scripts/validate_*.py has exactly one manifest row and every row names an existing script;
* every validator row names an owning test that exists, lies in a directory `make test` discovers (so
  `make integration` reaches it) and runs that validator; helper rows name a parent that imports them;
* the runner's expectation language, its input resolution (a missing pin is a skip naming the pin, a
  wrong one a failure) and the evidence-index regeneration, on synthetic data only. Nothing here runs
  client code.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import pins  # noqa: E402
import run_test_suites  # noqa: E402
import run_validators as rv  # noqa: E402

ORPHAN_TEST = 'tests/test_orphan_validators_private.py'


def makefile_test_dirs():
    return set(run_test_suites.makefile_suites())


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = rv.load_manifest()

    def test_one_row_per_validator(self):
        scripts = {p.stem for p in SCRIPTS.glob('validate_*.py')}
        self.assertEqual(sorted(scripts - set(self.rows)), [], 'validators without a manifest row')
        self.assertEqual(sorted(set(self.rows) - scripts), [], 'manifest rows without a validator')

    def test_owning_tests_exist_run_the_validator_and_are_discovered(self):
        dirs = makefile_test_dirs()
        for name, row in self.rows.items():
            if row['kind'] != 'validator':
                continue
            with self.subTest(validator=name):
                file, _, test_id = row['test'].partition('::')
                path = ROOT / file
                self.assertTrue(path.is_file(), f'{name}: owning test {file} does not exist')
                self.assertIn(str(Path(file).parent), dirs, f'{name}: {file} is not in a `make test` directory')
                text = path.read_text()
                if file == ORPHAN_TEST:
                    self.assertIn('OrphanValidators', test_id)
                    continue
                self.assertRegex(text, rf'\b{name}\b', f'{name}: {file} never names the validator')
                klass, _, method = test_id.partition('.')
                self.assertRegex(text, rf'class {klass}\b', f'{name}: no class {klass} in {file}')
                self.assertRegex(text, rf'def {method}\b', f'{name}: no {method} in {file}')

    def test_helpers_are_imported_by_their_family(self):
        for name, row in self.rows.items():
            if row['kind'] != 'helper':
                continue
            with self.subTest(helper=name):
                self.assertIn(row['parent'], self.rows)
                self.assertEqual(self.rows[row['parent']]['kind'], 'validator')
                users = [p.name for p in SCRIPTS.glob('validate_*.py')
                         if p.stem != name and re.search(rf'\b{name}\b', p.read_text())]
                self.assertTrue(users, f'{name}: no validator imports it')

    def test_report_rows_write_their_report(self):
        for name, row in self.rows.items():
            if row['kind'] == 'validator' and row['report'] == 'file':
                self.assertTrue(any('{report}' in arg for arg in row['args']), name)

    def test_orphan_rows_are_run_by_the_orphan_test(self):
        """The rows that no older test runs are exactly the ones the orphan test file runs."""
        orphan = [n for n, r in self.rows.items() if r.get('test', '').startswith(ORPHAN_TEST + '::')]
        self.assertTrue(orphan)
        text = (ROOT / ORPHAN_TEST).read_text()
        self.assertIn('load_manifest', text)
        for name in orphan:
            self.assertEqual(self.rows[name]['test'], f'{ORPHAN_TEST}::OrphanValidators.test_{name[len("validate_"):]}')

    def test_manifest_shape_errors_are_reported(self):
        bad = {'unknown field': '[validate_x]\ntest = "t"\nfrobnicate = 1\n',
               'targets outside build': '[validate_x]\ntest = "t"\nbuild_targets = { native = ["host"] }\n',
               'empty targets': '[validate_x]\ntest = "t"\nbuild = ["native"]\nbuild_targets = { native = [] }\n',
               'unknown pin': '[validate_x]\ntest = "t"\npins = ["nope"]\n',
               'undeclared placeholder': '[validate_x]\ntest = "t"\npins = ["text"]\nargs = ["{data}"]\n',
               'helper without parent': '[validate_x]\nkind = "helper"\n',
               'validator without test': '[validate_x]\nargs = []\n'}
        with tempfile.TemporaryDirectory() as folder:
            for label, text in bad.items():
                with self.subTest(label):
                    path = Path(folder) / 'm.toml'
                    path.write_text(text)
                    with self.assertRaises(rv.ManifestError):
                        rv.load_manifest(path)


class ExpectationTests(unittest.TestCase):
    report = {'families': {'a': {'cases': 3, 'equal': 3}, 'b': {'cases': 5, 'equal': 5}},
              'mutations': [{'mismatches': 4}, {'mismatches': 1}], 'ok': True, 'list': [16, 24],
              'summary': {'loader': 7, 'matches': 7}}

    def judge(self, expect, exit_code=0, stdout=''):
        return rv.evaluate({'expect': expect}, self.report, exit_code, stdout)[0]

    def test_paths_and_fan_out(self):
        self.assertEqual(rv.lookup(self.report, 'families.a.cases'), 3)
        self.assertEqual(rv.lookup(self.report, 'families.*.cases'), [3, 5])
        self.assertEqual(rv.lookup(self.report, 'mutations.1.mismatches'), 1)
        self.assertIsNone(rv.lookup(self.report, 'families.c.cases'))

    def test_operators(self):
        self.assertTrue(self.judge({'ok': True, 'list': [16, 24], 'summary.loader': 7}))
        self.assertTrue(self.judge({'families.*.cases': {'all_min': 3, 'sum': 8}, 'mutations': {'len': 2}}))
        self.assertTrue(self.judge({'mutations.*.mismatches': {'all_min': 1}, 'families': {'len_min': 2}}))
        self.assertTrue(self.judge({'families.*.equal': {'same_as': 'families.*.cases'},
                                    'summary.matches': {'same_as': 'summary.loader'}}))
        self.assertTrue(self.judge({'$stdout': {'contains': 'all cases match'}}, stdout='... all cases match\n'))
        self.assertFalse(self.judge({'families.*.cases': 3}))
        self.assertFalse(self.judge({'mutations.*.mismatches': {'all_min': 2}}))
        self.assertFalse(self.judge({'summary.matches': {'same_as': 'families.a.cases'}}))
        self.assertFalse(self.judge({'absent.path': 0}))
        self.assertFalse(self.judge({}, exit_code=1), 'a nonzero exit fails whatever the report says')
        self.assertFalse(self.judge({'$stdout': {'contains': 'ALL PASS'}}, stdout='FAIL'))

    def test_counts(self):
        row = {'cases_at': 'families.*.cases', 'mutants_at': 'mutations'}
        self.assertEqual(rv.counts(row, self.report), {'cases': 8, 'mutants': 2})


class RunnerInputTests(unittest.TestCase):
    """run_row decides skip/fail from the inputs before it would start anything."""

    def environment(self, folder):
        names = {pins.EVIDENCE_ENV, pins.SNAPSHOT_ENV, 'MU_GAME_ROOT'}
        for pin in pins.PINS.values():
            names.update(pin.env)
        clean = {k: v for k, v in os.environ.items() if k not in names}
        clean[pins.EVIDENCE_ENV] = folder
        return mock.patch.dict(os.environ, clean, clear=True)

    def row(self, **extra):
        return {'kind': 'validator', 'test': 't', 'pins': ['text', 'data'], 'families': [], 'needs': [], 'build': [],
                'prepare': [], 'args': ['--text', '{text}', '--data', '{data}', '--output', '{report}'], 'expect': {},
                'env': {}, 'timeout': 5, 'report': 'file', **extra}

    def test_missing_pin_is_a_skip_naming_it(self):
        with tempfile.TemporaryDirectory() as folder, self.environment(folder):
            entry = rv.run_row('validate_hud', self.row())
        self.assertEqual(entry['status'], 'skip')
        self.assertIn("'text'", entry['reason'])
        self.assertEqual(entry['missing_pins'], ['data', 'text'])

    def test_wrong_input_is_a_failure(self):
        with tempfile.TemporaryDirectory() as folder, self.environment(folder):
            for pin in (pins.TEXT, pins.DATA):
                path = Path(folder) / pin.relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'not the capture')
            entry = rv.run_row('validate_hud', self.row())
        self.assertEqual(entry['status'], 'fail')
        self.assertIn('differs from its pin', entry['reason'])

    def test_missing_game_root_is_a_skip(self):
        with tempfile.TemporaryDirectory() as folder, self.environment(folder):
            entry = rv.run_row('validate_hud', self.row(pins=[], args=['--game-root', '{game_root}'], needs=['game_root']))
        self.assertEqual(entry['status'], 'skip')
        self.assertIn('MU_GAME_ROOT', entry['reason'])

    def test_helper_rows_never_run(self):
        entry = rv.run_row('validate_social2_packets', {'kind': 'helper', 'parent': 'validate_social2', 'families': []})
        self.assertEqual(entry['status'], 'skip')

    def test_private_needs_the_integration_switch(self):
        with mock.patch.dict(os.environ, {'MU_RECOVERY_INTEGRATION': ''}):
            with self.assertRaisesRegex(SystemExit, 'MU_RECOVERY_INTEGRATION'):
                rv.main(['--private', '--only', 'validate_hud'])

    def test_dry_run_lists_without_running(self):
        self.assertEqual(rv.main(['--only', 'validate_hud']), 0)
        self.assertEqual(rv.main(['--list', '--only', 'validate_social2*']), 0)


class ResumeTests(unittest.TestCase):
    def setUp(self):
        contexts = ExitStack()
        self.addCleanup(contexts.close)
        folder = contexts.enter_context(tempfile.TemporaryDirectory())
        self.checkout = Path(folder) / 'checkout'
        self.checkout.mkdir()
        self.report = Path(folder) / 'report'
        self.manifest = self.checkout / 'validators.toml'
        scripts = self.checkout / 'scripts'
        scripts.mkdir()
        self.manifest.write_text(
            '[validate_a]\ntest = "a"\nargs = ["--mutants"]\n'
            '[validate_b]\ntest = "b"\nargs = ["--mutants"]\n')
        for row in ('a', 'b'):
            (scripts / f'validate_{row}.py').write_text('print("synthetic check passed")\n')
        self.git('init', '-q')
        self.git('add', '.')
        self.commit()
        contexts.enter_context(mock.patch.object(rv, 'REPO', self.checkout))
        contexts.enter_context(mock.patch.object(rv, 'record_times'))
        contexts.enter_context(mock.patch.dict(os.environ, {'MU_RECOVERY_INTEGRATION': '1'}))

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.checkout), *args], capture_output=True, check=True)

    def commit(self, *args):
        self.git('-c', 'user.name=Validator test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'Synthetic revision', *args)

    def run_validator(self, *args):
        return rv.main(['--manifest', str(self.manifest), '--private', '--report', str(self.report), *args])

    def assert_resume_rejected(self, reason, *args):
        saved = (self.report / 'summary.json').read_bytes()
        with self.assertRaisesRegex(SystemExit, reason):
            self.run_validator('--resume', *args)
        self.assertEqual((self.report / 'summary.json').read_bytes(), saved)

    def test_resume_rejects_another_commit(self):
        self.assertEqual(self.run_validator('--only', 'a'), 0)
        self.commit('--allow-empty')
        self.assert_resume_rejected('commit changed')

    def test_resume_rejects_a_change_in_mutation_mode(self):
        self.assertEqual(self.run_validator('--only', 'a', '--no-mutants'), 0)
        self.assert_resume_rejected('mutation mode changed')

    def test_resume_rejects_uncommitted_changes(self):
        self.assertEqual(self.run_validator('--only', 'a'), 0)
        (self.checkout / 'scripts' / 'validate_a.py').write_text('raise SystemExit(1)\n')
        self.assert_resume_rejected('uncommitted changes')

    def test_resume_rejects_a_changed_external_manifest(self):
        external = self.report.parent / 'external.toml'
        external.write_bytes(self.manifest.read_bytes())
        self.manifest = external
        self.assertEqual(self.run_validator('--only', 'a'), 0)
        external.write_text(external.read_text().replace('test = "a"', 'test = "changed"'))
        self.assert_resume_rejected('manifest changed')

    def test_resume_reuses_a_pass_and_runs_a_missing_row(self):
        self.report = self.checkout / 'untracked-report'
        self.assertEqual(self.run_validator('--only', 'a'), 0)
        with mock.patch.object(rv, 'run_row', wraps=rv.run_row) as run_row:
            self.assertEqual(self.run_validator('--resume'), 0)
        self.assertEqual([call.args[0] for call in run_row.call_args_list], ['validate_b'])
        summary = json.loads((self.report / 'summary.json').read_text())
        self.assertEqual(summary['totals'], {'pass': 2, 'fail': 0, 'error': 0, 'skip': 0})

    def test_rechecked_verdicts_cannot_be_resumed(self):
        self.assertEqual(self.run_validator('--only', 'a'), 0)
        rv.recheck(rv.load_manifest(self.manifest), self.report)
        self.assert_resume_rejected('no resume context')

    def test_new_run_replaces_stale_summary_before_first_row(self):
        self.assertEqual(self.run_validator('--only', 'a'), 0)
        with mock.patch.object(rv, 'run_row', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_validator()
        summary = json.loads((self.report / 'summary.json').read_text())
        self.assertEqual(summary['rows'], {})


class RecheckTests(unittest.TestCase):
    def test_command_exit_reflects_saved_report_verdicts(self):
        cases = [
            ('complete report', {'cases': 10, 'mutants': 2}, 0, 'pass', 0, None),
            ('fewer cases than expected', {'cases': 9, 'mutants': 2}, 0, 'fail', 1, '#cases'),
            ('missing case count', {'mutants': 2}, 0, 'fail', 1, '#cases'),
            ('missing mutant count', {'cases': 10}, 0, 'fail', 1, '#mutants'),
            ('timed out', {'cases': 10, 'mutants': 2}, None, 'error', 1, None),
        ]
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder)
            manifest = report / 'validators.toml'
            manifest.write_text('[validate_sample]\ntest = "synthetic"\nreport = "file"\n'
                                'cases = 10\ncases_at = "cases"\nmutants = 2\nmutants_at = "mutants"\n')
            summary = report / 'summary.json'
            command = [sys.executable, str(SCRIPTS / 'run_validators.py'), '--manifest', str(manifest),
                       '--recheck', str(report)]
            for name, data, validator_exit, verdict, expected_exit, failed_check in cases:
                with self.subTest(name=name):
                    summary.write_text(json.dumps({'rows': {'validate_sample': {'status': 'pass',
                                                                                 'exit': validator_exit}}}))
                    (report / 'validate_sample.json').write_text(json.dumps(data))
                    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                    row = json.loads(summary.read_text())['rows']['validate_sample']
                    self.assertEqual((row['status'], result.returncode), (verdict, expected_exit),
                                     result.stdout + result.stderr)
                    if failed_check:
                        self.assertFalse(row['expect'][failed_check]['ok'])


class IndexTests(unittest.TestCase):
    def test_index_keeps_findings_and_replaces_only_the_validators(self):
        index = {'updated': '2026-10-17', 'findings': {'loader': {'chunks': 4}},
                 'validation': {'portable_tests_discovered': 254, 'validators': {'old': True}}}
        summary = {'date': '2026-10-25', 'environment': {'commit': 'abc'}, 'totals': {'pass': 1, 'fail': 0, 'error': 0,
                                                                                    'skip': 1},
                   'rows': {'validate_a': {'status': 'pass', 'test': 'x::Y.z', 'cases': 10, 'seconds': 1.0,
                                           'pins': {'text': pins.TEXT.sha256}},
                            'validate_b': {'status': 'skip', 'test': 'x::Y.w', 'reason': 'section3 missing'}}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'index.json'
            path.write_text(json.dumps(index))
            rv.write_index(path, summary)
            out = json.loads(path.read_text())
        self.assertEqual(out['findings'], index['findings'])
        self.assertEqual(out['validation']['portable_tests_discovered'], 254)
        self.assertEqual(out['updated'], '2026-10-25')
        validators = out['validation']['validators']
        self.assertEqual(validators['rows']['validate_a'], {'status': 'pass', 'test': 'x::Y.z', 'cases': 10,
                                                            'pins': ['text']})
        self.assertEqual(validators['rows']['validate_b']['reason'], 'section3 missing')
        self.assertEqual(validators['totals']['skip'], 1)

    def test_index_layout_outside_validation_is_untouched(self):
        text = ('{\n  "updated": "2026-10-17",\n  "findings": {\n    "wine_track": {"keys": ["a", "b"]}\n  },\n'
                '  "validation": {\n    "portable_tests_discovered": 254\n  },\n  "native_macos_client": false\n}\n')
        summary = {'date': '2026-10-25', 'environment': {}, 'rows': {
            'validate_a': {'status': 'skip', 'reason': f'missing {pins.REPO}/x', 'test': 't'},
            'validate_h': {'status': 'skip', 'reason': 'helper module, exercised through validate_a'}}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'index.json'
            path.write_text(text)
            rv.write_index(path, summary)
            out = path.read_text()
        self.assertIn('    "wine_track": {"keys": ["a", "b"]}\n', out)
        self.assertIn('  "native_macos_client": false\n}', out)
        data = json.loads(out)
        self.assertEqual(data['validation']['validators']['rows']['validate_a']['reason'], 'missing <repo>/x')
        self.assertEqual(data['validation']['validators']['helpers']['parent_runs_them'], ['validate_h'])
        self.assertEqual(data['validation']['portable_tests_discovered'], 254)


if __name__ == '__main__':
    unittest.main()
