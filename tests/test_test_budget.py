"""Portable checks of the TEST-SPEED-001 runner flags (docs/testing/TEST-BUDGET.md).

* run_validators.py --no-mutants: every arg form the manifest uses (switches, switches with a case count, the
  numeric --mutations of the input-case validators) against the validator's own argparse, the expectations it
  drops and keeps, an end-to-end run of a synthetic validator with and without mutants (same pass, same cases),
  --recheck and the evidence-index guard;
* run_validators.py --affected/--list-affected: a temporary git repository with a validator, its helper, its
  owning test, its build directory (and what its Makefile reaches), the shared infrastructure and the manifest;
* run_test_suites.py --affected: path → work item mapping on this repository (no build needed) and a synthetic
  sharded suite run with only the selected modules;
* the recorded validator wall times and the longest-first order.
"""
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import affected  # noqa: E402
import run_test_suites as rts  # noqa: E402
import run_validators as rv  # noqa: E402

SWITCH = re.compile(r"""add_argument\(\s*['"](--mutations|--mutants)['"]([^)]*)\)""")


def row(**extra):
    base = {'kind': 'validator', 'test': 't.py::T.test', 'pins': [], 'families': [], 'needs': [], 'build': [],
            'prepare': [], 'args': [], 'expect': {}, 'env': {}, 'timeout': 60, 'report': 'file'}
    base.update(extra)
    return base


class NoMutantsForms(unittest.TestCase):
    def test_switch_and_its_expectations(self):
        r = row(args=['--cases', '60', '--mutations', '--output', '{report}'], cases=120, mutants=3,
                mutants_at='mutants', cases_at='families.*.cases',
                expect={'families.*.mismatches': 0, 'mutants.*': {'truthy': True}, 'all_mutants_caught': True,
                        'ok': True, 'summary.rejected': {'same_as': 'mutations_detected'}})
        out, removed = rv.strip_mutants(r)
        self.assertEqual(removed, ['--mutations'])
        self.assertEqual(out['args'], ['--cases', '60', '--output', '{report}'])
        self.assertEqual(out['expect'], {'families.*.mismatches': 0, 'ok': True})
        self.assertIsNone(out['mutants'])
        self.assertIsNone(out['mutants_at'])
        self.assertEqual((out['cases'], out['cases_at']), (120, 'families.*.cases'))
        self.assertIn('--mutations', r['args'], 'the manifest row itself is not changed')

    def test_switch_with_case_counts(self):
        for args, kept in ((['--cases', '60', '--mutations', '--mutant-cases', '120', '--output', 'x'],
                            ['--cases', '60', '--output', 'x']),
                           (['--mutations', '--mutation-cases=200'], []),
                           (['--mutants', '--output', 'x'], ['--output', 'x'])):
            out, removed = rv.strip_mutants(row(args=args))
            self.assertEqual(out['args'], kept, args)
            self.assertTrue(removed)

    def test_numeric_mutations_are_input_cases_and_stay(self):
        r = row(args=['--limit', '40', '--mutations', '40', '--frames', '30'], expect={'cases': 80})
        out, removed = rv.strip_mutants(r)
        self.assertEqual((out, removed), (r, []))

    def test_built_in_negative_controls_run_unchanged(self):
        r = row(args=['--cases', '60'], mutants=12, mutants_at='negative_controls',
                expect={'negative_controls.*.caught': True})
        self.assertEqual(rv.strip_mutants(r), (r, []))

    def test_nested_mutant_roots(self):
        r = row(args=['--mutations'], mutants_at=['mutations.*', 'bugs.negative.*'],
                expect={'bugs.cases': 5, 'bugs.negative': {'len': 3}, 'bugs.negative.0.caught': True})
        out, _ = rv.strip_mutants(r)
        self.assertEqual(out['expect'], {'bugs.cases': 5})

    def test_every_manifest_row(self):
        """Each stripped switch is a store_true flag of that validator; each kept --mutations N is an int option;
        no stripped row keeps a mutant argument or expectation; case counts are untouched."""
        rows = rv.load_manifest()
        stripped = kept_numeric = 0
        for name, r in rows.items():
            if r['kind'] != 'validator':
                continue
            source = (ROOT / 'scripts' / f'{name}.py').read_text()
            defined = {m.group(1): m.group(2) for m in SWITCH.finditer(source)}
            out, removed = rv.strip_mutants(r)
            for arg in removed:
                if arg in rv.MUTANT_SWITCHES:
                    self.assertIn(arg, defined, f'{name}: {arg} is not an option of the validator')
                    self.assertIn('store_true', defined[arg], f'{name}: {arg} takes a value')
                elif not arg.isdigit():
                    self.assertIn(arg.split('=')[0], source, f'{name}: {arg} is not an option of the validator')
            if removed:
                stripped += 1
                self.assertFalse([a for a in out['args'] if rv.MUTANT_WORDS.search(a)], name)
                self.assertFalse([p for p in out['expect'] if rv.MUTANT_WORDS.search(p)], name)
                self.assertTrue(set(out['expect']) <= set(r['expect']), name)
                self.assertEqual((out.get('cases'), out.get('cases_at')), (r.get('cases'), r.get('cases_at')), name)
            for i, arg in enumerate(r['args']):
                if arg in rv.MUTANT_SWITCHES and i + 1 < len(r['args']) and r['args'][i + 1].isdigit():
                    kept_numeric += 1
                    self.assertRegex(defined.get(arg, ''), r'type\s*=\s*int', f'{name}: {arg} N')
                    self.assertIn(arg, out['args'])
        self.assertGreaterEqual(stripped, 100)   # 110 at TEST-SPEED-001
        self.assertGreaterEqual(kept_numeric, 3)  # effects, effect_tree, meshdraw


FAKE_VALIDATOR = '''
import argparse, json
p = argparse.ArgumentParser()
p.add_argument('--cases', type=int, default=10)
p.add_argument('--mutations', action='store_true')
p.add_argument('--mutant-cases', type=int, default=5)
p.add_argument('--output', required=True)
a = p.parse_args()
report = {'families': {'a': {'cases': a.cases, 'mismatches': 0}, 'b': {'cases': a.cases, 'mismatches': 0}}}
if a.mutations:
    report['mutants'] = {'off-by-one': a.mutant_cases, 'sign': 1}
    report['all_mutants_caught'] = True
open(a.output, 'w').write(json.dumps(report))
'''


class NoMutantsRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / 'scripts').mkdir()
        (self.repo / 'scripts' / 'validate_fake.py').write_text(FAKE_VALIDATOR)
        self.row = row(args=['--cases', '7', '--mutations', '--mutant-cases', '3', '--output', '{report}'],
                       cases=14, cases_at='families.*.cases', mutants=2, mutants_at='mutants',
                       expect={'families.*.mismatches': 0, 'mutants.*': {'all_min': 1}, 'all_mutants_caught': True})

    def tearDown(self):
        self.tmp.cleanup()

    def run_row(self, r):
        with mock.patch.object(rv, 'REPO', self.repo):
            return rv.run_row('validate_fake', r)

    def test_same_pass_and_cases_with_and_without_mutants(self):
        full = self.run_row(self.row)
        quick = self.run_row(rv.strip_mutants(self.row)[0])
        self.assertEqual((full['status'], full['cases'], full['mutants']), ('pass', 14, 2))
        self.assertEqual((quick['status'], quick['cases']), ('pass', 14))
        self.assertNotIn('mutants', quick)
        self.assertEqual(quick['mutants_skipped'], ['--mutations', '--mutant-cases', '3'])
        self.assertNotIn('--mutations', quick['command'])

    def test_unstripped_expectations_would_fail_without_mutants(self):
        bare = dict(self.row, args=['--cases', '7', '--output', '{report}'])
        self.assertEqual(self.run_row(bare)['status'], 'fail')

    def test_a_real_mismatch_still_fails(self):
        r = rv.strip_mutants(dict(self.row, expect={'families.*.mismatches': 1}))[0]
        self.assertEqual(self.run_row(r)['status'], 'fail')

    def test_summary_recheck_and_index_guard(self):
        report = self.repo / 'report'
        report.mkdir()
        with mock.patch.object(rv, 'REPO', self.repo):
            entry = rv.run_row('validate_fake', rv.strip_mutants(self.row)[0], report)
        summary = {'date': '2026-11-04', 'environment': {}, 'no_mutants': True, 'rows': {'validate_fake': entry}}
        rv.write_summary(report, summary)
        out = io.StringIO()
        with redirect_stdout(out):
            rv.print_totals(summary)
        self.assertIn('mutants skipped (--no-mutants): 1 of 1 rows run', out.getvalue())
        again = rv.recheck({'validate_fake': self.row}, report)   # the full manifest row, rejudged without mutants
        self.assertEqual(again['rows']['validate_fake']['status'], 'pass')
        index = self.repo / 'index.json'
        index.write_text('{"updated": "x", "validation": {}}\n')
        with self.assertRaisesRegex(SystemExit, 'mutant counts'):
            rv.write_index(index, summary)


class ValidatorTimes(unittest.TestCase):
    def test_record_and_longest_first(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'times.json'
            rv.record_times([{'name': 'a', 'status': 'pass', 'seconds': 5.0},
                             {'name': 'b', 'status': 'fail', 'seconds': 50.0},
                             {'name': 'c', 'status': 'skip', 'seconds': 0.1},
                             {'name': 'd', 'status': 'pass', 'seconds': 9.0, 'mutants_skipped': ['--mutations']}],
                            no_mutants=True, path=path)
            times = json.loads(path.read_text())
        self.assertEqual(times, {'a': 5.0, 'b': 50.0, 'd --no-mutants': 9.0})
        self.assertEqual(rv.longest_first(['a', 'b', 'c', 'd'], True, times), ['c', 'b', 'd', 'a'])
        self.assertEqual(rv.longest_first(['a', 'd'], False, times), ['d', 'a'])


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
                            GIT_COMMITTER_EMAIL='t@t'))


MANIFEST = '''
[validate_alpha]
test = "reconstructed/alpha/test_alpha.py::A.test"
build = ["reconstructed/alpha"]
args = ["--mutations", "--output", "{report}"]

[validate_beta]
test = "tests/test_beta.py::B.test"
args = ["--output", "{report}"]

[validate_gamma]
test = "tests/test_gamma.py::G.test"
build = ["reconstructed/gamma"]
args = []
'''


class AffectedValidators(unittest.TestCase):
    """A small repository: alpha builds reconstructed/alpha (whose Makefile reaches ../shared), beta imports
    helper_beta and names reconstructed/beta/beta.c, gamma builds reconstructed/gamma."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        repo = self.repo = Path(self.tmp.name)
        files = {
            'scripts/validate_alpha.py': 'import pins\n',
            'scripts/validate_beta.py': "import helper_beta\nSOURCE = 'reconstructed/beta/beta.c'\n",
            'scripts/validate_gamma.py': "TABLE = 'gamma_table.h'\n",
            'scripts/helper_beta.py': 'X = 1\n',
            'scripts/pins.py': 'PINS = {}\n',
            'scripts/run_validators.py': '# runner\n',
            'scripts/validators.toml': MANIFEST,
            'reconstructed/alpha/Makefile': 'include ../deps.mk\nCFLAGS += -I../shared\nall:\n',
            'reconstructed/alpha/alpha.c': '',
            'reconstructed/alpha/test_alpha.py': '',
            'reconstructed/alpha/README.md': '',
            'reconstructed/deps.mk': '',
            'reconstructed/shared/shared.h': '',
            'reconstructed/beta/beta.c': '',
            'reconstructed/beta/other.c': '',
            'reconstructed/gamma/Makefile': 'all:\n',
            'reconstructed/gamma/gamma.c': '',
            'reconstructed/other/gamma_table.h': '',
            'tests/test_beta.py': '', 'tests/test_gamma.py': '', 'docs/status.md': '',
        }
        for path, text in files.items():
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(text)
        git(repo, 'init', '-q')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-qm', 'base')
        git(repo, 'tag', 'base')
        self.rows = rv.load_manifest(repo / 'scripts/validators.toml')

    def tearDown(self):
        self.tmp.cleanup()

    def select(self, *changes, commit=True, edit=None):
        git(self.repo, 'reset', '-q', '--hard', 'base')
        git(self.repo, 'clean', '-qfd')
        if edit:
            edit()
        for path in changes:
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(target.read_text() + '\n# changed\n' if target.exists() else 'new\n')
        if commit:
            git(self.repo, 'add', '-A')
            git(self.repo, 'commit', '-qm', 'change')
        return rv.affected_rows(self.rows, 'base', root=self.repo, manifest=self.repo / 'scripts/validators.toml')

    def test_build_dir_and_what_its_makefile_reaches(self):
        self.assertEqual(list(self.select('reconstructed/alpha/alpha.c')), ['validate_alpha'])
        self.assertEqual(list(self.select('reconstructed/shared/shared.h')), ['validate_alpha'])
        self.assertEqual(list(self.select('reconstructed/deps.mk')), ['validate_alpha'])

    def test_docs_and_unit_tests_in_a_build_dir_are_not_compiled(self):
        self.assertEqual(self.select('reconstructed/alpha/README.md', 'docs/status.md'), {})

    def test_owning_test_script_helper_and_named_source(self):
        self.assertEqual(list(self.select('reconstructed/alpha/test_alpha.py')), ['validate_alpha'])
        self.assertEqual(list(self.select('scripts/helper_beta.py')), ['validate_beta'])
        self.assertEqual(list(self.select('reconstructed/beta/beta.c')), ['validate_beta'])
        self.assertEqual(len(self.select('reconstructed/beta/other.c')), 3)  # unmapped code fails open
        self.assertEqual(list(self.select('reconstructed/other/gamma_table.h')), ['validate_gamma'])
        self.assertEqual(list(self.select('tests/test_gamma.py')), ['validate_gamma'])

    def test_uncommitted_and_untracked_changes_count(self):
        self.assertEqual(list(self.select('reconstructed/gamma/gamma.c', commit=False)), ['validate_gamma'])
        self.assertEqual(list(self.select('reconstructed/gamma/new.c', commit=False)), ['validate_gamma'])

    def test_shared_infrastructure_selects_every_row(self):
        for path in ('scripts/pins.py', 'scripts/run_validators.py'):
            with self.subTest(path=path):
                why = self.select(path)
                self.assertEqual(sorted(why), ['validate_alpha', 'validate_beta', 'validate_gamma'])
                self.assertIn('selects everything', why['validate_beta'][0])

    def test_a_changed_manifest_row_selects_only_that_row(self):
        path = self.repo / 'scripts/validators.toml'

        def edit():
            path.write_text(path.read_text().replace('args = []', 'args = ["--cases", "5"]'))
            self.rows = rv.load_manifest(path)
        why = self.select(edit=edit)
        self.assertEqual(list(why), ['validate_gamma'])
        self.assertIn('its row changed', why['validate_gamma'][0])

    def test_test_hosts_and_swift_are_gate_owned_but_references_still_select(self):
        self.assertEqual(self.select('native/tests/unused_host.c'), {})
        self.assertEqual(self.select('native/app/Sources/Unused.swift'), {})
        def edit():
            (self.repo / 'scripts/validate_beta.py').write_text("HOST = 'native/tests/referenced.c'\n")
        self.assertEqual(list(self.select('native/tests/referenced.c', edit=edit)), ['validate_beta'])
        self.assertEqual(len(self.select('native/new_production.c')), 3)

    def test_owning_test_imports_do_not_become_validator_dependencies(self):
        def edit():
            (self.repo / 'tests/test_beta.py').write_text('import helper_gamma\n')
            (self.repo / 'scripts/helper_gamma.py').write_text('VALUE = 1\n')
            (self.repo / 'scripts/validate_gamma.py').write_text('import helper_gamma\n')
        # The real gamma consumer is selected; beta's unused test import is not.
        edit()
        self.assertIsNone(rv.row_deps('validate_beta', self.rows['validate_beta'], self.repo).why('scripts/helper_gamma.py'))
        self.assertTrue(rv.row_deps('validate_gamma', self.rows['validate_gamma'], self.repo).why('scripts/helper_gamma.py'))

    def test_direct_compiler_source_header_closure(self):
        def edit():
            (self.repo / 'reconstructed/beta/beta.c').write_text('#include "adapter.h"\n')
        self.assertEqual(list(self.select('reconstructed/beta/adapter.h', edit=edit)), ['validate_beta'])

    def test_reasons_are_printed(self):
        self.select('scripts/helper_beta.py')
        out = io.StringIO()
        with redirect_stdout(out), mock.patch.object(rv, 'REPO', self.repo):
            code = rv.main(['--manifest', str(self.repo / 'scripts/validators.toml'), '--list-affected', 'base'])
        self.assertEqual(code, 0)
        self.assertIn('affected: 1 of 3 manifest rows selected', out.getvalue())
        self.assertRegex(out.getvalue(), r'validate_beta: scripts/helper_beta.py: imports scripts/helper_beta.py')


class AffectedDeps(unittest.TestCase):
    def test_include_closure_without_a_build(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'inc').mkdir()
            (base / 'a.c').write_text('#include "a.h"\n#include <inc/b.h>\n#include <stdio.h>\n')
            (base / 'a.h').write_text('#include "c.inc"\n')
            (base / 'c.inc').write_text('')
            (base / 'inc' / 'b.h').write_text('')
            (base / 'unused.h').write_text('')
            found = affected._includes((base / 'a.c',), (base,))
        self.assertEqual({p.name for p in found}, {'a.h', 'b.h', 'c.inc'})

    def test_python_closure_names_and_search_dirs(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / 'scripts').mkdir()
            (repo / 'reconstructed' / 'objects').mkdir(parents=True)
            (repo / 'reconstructed' / 'objects' / 'objects.c').write_text('')
            (repo / 'scripts' / 'a.py').write_text(
                "import b\nfrom pathlib import Path\nD = Path('scripts')\nfor d in ['objects']: Path('reconstructed') / d\n")
            (repo / 'scripts' / 'b.py').write_text("import os\nX = 'build/mu-walk'\n")
            deps = affected.python_deps(repo / 'scripts' / 'a.py', repo)
        self.assertIn('scripts/b.py', deps.files)
        self.assertNotIn('scripts', deps.dirs)                      # a search path, not every file in it
        self.assertIn('build/mu-walk', deps.names)                  # a target named before it is built
        self.assertTrue(deps.why('reconstructed/objects/objects.c'))   # ROOT / 'reconstructed' / d
        self.assertIsNone(deps.why('reconstructed/ui/ui.c'))
        self.assertIsNone(deps.why('scripts/c.py'))


NATIVE_SAMPLE = ('test_native_perf004.py', 'test_help_layer.py', 'test_native_worlds_e.py')
_units = rts.units


def sample_units(suite):
    """native/tests limited to a few modules (each full make dry run costs ~0.3 s); the other suites whole."""
    return [u for u in _units(suite) if suite != 'native/tests' or u[1] in NATIVE_SAMPLE]


@mock.patch.object(rts, 'units', sample_units)
class AffectedSuites(unittest.TestCase):
    """The path → work item mapping on this repository's own suites (make -n only; nothing is built)."""

    @classmethod
    def setUpClass(cls):
        cls.suites = rts.makefile_suites()

    def pick(self, *paths):
        return rts.affected_units(self.suites, 'HEAD', changed=list(paths))

    def test_docs_only_runs_the_repository_tests(self):
        self.assertEqual(list(self.pick('docs/status.md')), ['tests'])
        self.assertEqual(self.pick(), {})

    def test_infrastructure_selects_everything(self):
        total = sum(len(rts.units(s)) for s in self.suites)
        for path in ('Makefile', 'scripts/run_test_suites.py', 'scripts/local-macos-ci.sh', 'scripts/affected.py'):
            with self.subTest(path=path):
                self.assertEqual(len(self.pick(path)), total)

    def test_a_test_module_and_its_host(self):
        why = self.pick('native/tests/test_native_perf004.py', 'native/tests/perf_players_host.c')
        self.assertEqual(sorted(why), ['native/tests/test_native_perf004.py', 'tests'])
        self.assertEqual(sorted(self.pick('native/tests/worlds_e_host.c')), ['native/tests/test_native_worlds_e.py', 'tests'])
        self.assertTrue(any('build/perf-players-host' in r for r in why['native/tests/test_native_perf004.py']))

    def test_a_suite_directory_and_what_its_makefile_reaches(self):
        why = self.pick('reconstructed/record-math/record_math.h')
        for suite in ('reconstructed/record-math', 'reconstructed/camera', 'native/tests/test_native_perf004.py',
                      'native/tests/test_native_worlds_e.py'):
            self.assertIn(suite, why)
        self.assertNotIn('reconstructed/boot', why)
        self.assertNotIn('native/tests/test_help_layer.py', why)   # pure Python, builds nothing

    def test_validator_script_selects_its_suite_not_native(self):
        why = self.pick('scripts/validate_hud.py')
        self.assertIn('reconstructed/hud', why)
        self.assertFalse([u for u in why if u.startswith('native/')])


class TightenedSelection(unittest.TestCase):
    def test_explicit_target_does_not_inherit_default(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'native').mkdir()
            (root / 'native/Makefile').write_text('all: full\nfull:\n\t@true\nhost:\n\t@true\n')
            path = root / 'test.py'
            dep = affected.Deps(files={'test.py': 'test'})
            path.write_text("run(['make', '-s', '-C', str(NATIVE), 'host'])")
            self.assertFalse(rts.needs_default_goal(dep, 'native', root))
            for code in ("run(['make', '-C', str(NATIVE)])", "run(['make', '-C', str(NATIVE), target])"):
                path.write_text(code)
                self.assertTrue(rts.needs_default_goal(dep, 'native', root))

    def test_new_rows_and_renderchar_fix_are_reached(self):
        rows = rv.load_manifest()
        for name in ('validate_worlds_after5', 'validate_worlds_after6', 'validate_render_effects10',
                     'validate_item_product', 'validate_renderchar'):
            dep = rv.row_deps(name, rows[name])
            self.assertTrue(dep.why('scripts/' + name + '.py'))
            source = ('reconstructed/renderchar/renderchar.c' if name in
                      ('validate_item_product', 'validate_renderchar') else
                      'reconstructed/objects/action_registry.c' if 'worlds_after' in name else
                      'reconstructed/combat/skill_fx.c')
            self.assertTrue(dep.why(source), (name, source))

    def test_shared_bitmap_header_still_selects_both_failed_hosts(self):
        for name in ('test_native_worlds_l.py', 'test_native_worlds_m.py'):
            dep = rts.unit_deps(('native/tests', name))
            self.assertTrue(dep.why('native/core/mu_particles.h'), name)

    def test_build_output_existence_does_not_change_target_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'build').mkdir()
            (root / 'build/host').write_text('binary')
            (root / 'test.py').write_text("TOOL = 'build/host'")
            self.assertIn('build/host', affected.python_deps(root / 'test.py', root).names)


class AffectedRun(unittest.TestCase):
    def test_only_the_selected_modules_run(self):
        with tempfile.TemporaryDirectory() as folder:
            suite = Path(folder) / 'suite'
            suite.mkdir()
            for name in ('one', 'two', 'three'):
                (suite / f'test_{name}.py').write_text(textwrap.dedent('''
                    import unittest
                    class T(unittest.TestCase):
                        def test_a(self): pass
                    '''))
            only = {f'{suite}/test_two.py'}
            (Path(folder) / 'logs').mkdir()
            out = io.StringIO()
            with mock.patch.object(rts, 'SHARDED', (str(suite),)), mock.patch.object(rts, 'record_times'), \
                    redirect_stdout(out):
                code = rts.run_parallel([str(suite)], 2, Path(folder) / 'logs', only)
            self.assertEqual(code, 0, out.getvalue())
            self.assertIn('1 work items', out.getvalue())
            self.assertIn('1 suites, 1 tests, 1 passed', out.getvalue())
            logs = [p.name for p in (Path(folder) / 'logs').iterdir()]
            self.assertEqual(len(logs), 1)
            self.assertTrue(logs[0].endswith('test_two.py.log'), logs)


class ValidatorTargets(unittest.TestCase):
    def test_target_sources_headers_make_fragments_and_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'native').mkdir()
            (root / 'flags.mk').write_text('CFLAGS = -O2\n')
            (root / 'native/Makefile').write_text(
                'include ../flags.mk\nall: wanted other\nwanted: a.c a.h\n\tcc $(CFLAGS) -c a.c -o a.o\n'
                'other: b.c\n\tcc -c b.c -o b.o\n')
            (root / 'native/a.c').write_text('#include "a.h"\n')
            (root / 'native/a.h').write_text('#include "nested.h"\n')
            (root / 'native/nested.h').write_text('')
            (root / 'native/b.c').write_text('')
            row = dict(build=['native'], build_targets={'native': ['wanted']}, args=[], prepare=[])
            dep = rv.row_deps('validate_example', row, root)
            for path in ('native/a.c', 'native/a.h', 'native/nested.h', 'native/Makefile', 'flags.mk'):
                self.assertTrue(dep.why(path), path)
            self.assertIsNone(dep.why('native/b.c'))
            row['build_targets']['native'] = ['missing']
            self.assertTrue(rv.row_deps('validate_example', row, root).why('native/b.c'))

    def test_build_cache_distinguishes_targets(self):
        with mock.patch.object(rv.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout='', stderr='')) as run, \
                mock.patch.object(rv, '_built', {}):
            rv.build('native', ('one',))
            rv.build('native', ('two',))
            rv.build('native', ('one',))
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args.args[0][-1], 'two')
            self.assertIn('-j4', run.call_args.args[0])

    def test_validator_imports_native_fixture_source_without_owning_test(self):
        deps = rv.row_deps('validate_meshdraw', rv.load_manifest()['validate_meshdraw'])
        self.assertTrue(deps.why('native/tests/native_fixtures.py'))

    def test_native_rows_have_target_provenance(self):
        rows = rv.load_manifest()
        for name, row in rows.items():
            if 'native' in row['build']:
                self.assertTrue(rv.build_targets(row, 'native'), name)
        for name, source in [('validate_crypto', 'native/net/crypto.cpp'),
                             ('validate_protocol', 'native/core/mu_protocol.c'),
                             ('validate_item_models', 'native/tools/mu_data.c'),
                             ('validate_worlds_after4', 'native/core/mu_bmd.h')]:
            dep = rv.row_deps(name, rows[name])
            self.assertTrue(dep.why(source), (name, source))
            self.assertIsNone(dep.why('native/app/Launcher.swift'), name)


class SuitesBuildWhatTheyLink(unittest.TestCase):
    """TEST-SPEED-003: a test module that loads another reconstructed directory's library runs that directory's make
    itself. Otherwise it passes only after another suite happened to build it, and `--affected` in a fresh worktree
    fails (test_joints needed reconstructed/combat/libcombat)."""

    def test_every_foreign_library_is_built_by_its_loader(self):
        root = Path(__file__).resolve().parents[1]
        missing = []
        for module in sorted([*root.glob('reconstructed/*/test_*.py'), *root.glob('native/tests/test_*.py')]):
            text = module.read_text()
            own = module.parent.name if module.parent.parent.name == 'reconstructed' else None
            for directory in sorted(set(re.findall(r"reconstructed/([\w.-]+)/lib\w+", text)) - {own}):
                built = (re.search(rf"reconstructed/{re.escape(directory)}['\"]", text)
                         or ("'reconstructed'/" in text and f"'{directory}'" in text))
                if not built:
                    missing.append(f'{module.relative_to(root)}: reconstructed/{directory}')
        self.assertEqual(missing, [], 'load a library only after `make -C reconstructed/<dir>`')


class OriginalCache(unittest.TestCase):
    """scripts/original_cache.py: off by default, keyed by the code that drives the original side, and the C side
    (here a plain function standing for the compiled library) is compared fresh on every run."""

    def setUp(self):
        import original_cache
        self.oc = original_cache
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.script = self.base / 'validate_fake.py'
        self.script.write_text('ORIGINAL = 1\n')

    def tearDown(self):
        self.tmp.cleanup()

    def cache(self):
        return self.oc.Cache(self.base / 'cache', 'validate_fake', self.script)

    def compare(self, cache, c_side, original_calls):
        def original(case):
            original_calls.append(case)
            return (case['x'] * 2, [('draw', case['x'])])
        return [cache.get('family', case, lambda: original(case)) == c_side(case) for case in
                ({'x': 1, 'y': (2, None)}, {'x': 3, 'y': (4, 0.5)})]

    def test_disabled_without_the_environment(self):
        with mock.patch.dict(os.environ, {self.oc.ENV: ''}):
            self.oc._caches.clear()
            self.assertFalse(self.oc.named('gen_fake', self.script).enabled)
        self.assertEqual(self.oc.Disabled().get('f', {}, lambda: 7), 7)

    def test_hits_after_save_and_c_changes_are_still_seen(self):
        good = lambda case: (case['x'] * 2, [('draw', case['x'])])
        calls = []
        first = self.cache()
        self.assertEqual(self.compare(first, good, calls), [True, True])
        first.save()
        self.assertEqual((first.misses, len(calls)), (2, 2))
        warm = self.cache()
        self.assertEqual(self.compare(warm, good, calls), [True, True])
        self.assertEqual((warm.hits, warm.misses, len(calls)), (2, 0, 2), 'the original side was not rerun')
        broken = lambda case: (case['x'] * 2 + (case['x'] == 3), [('draw', case['x'])])   # a planted C change
        self.assertEqual(self.compare(self.cache(), broken, calls), [True, False])

    def test_code_changes_start_a_fresh_cache(self):
        first = self.cache()
        first.get('family', {'x': 1}, lambda: 1)
        first.save()
        self.script.write_text('ORIGINAL = 2\n')
        second = self.cache()
        self.assertNotEqual(first.key, second.key)
        self.assertEqual(second.get('family', {'x': 1}, lambda: 2), 2)
        second.save()
        self.assertEqual(sorted(p.name for p in (self.base / 'cache' / 'validate_fake').glob('*.pickle.xz')),
                         sorted([first.path.name, second.path.name]), 'the older key is kept (TEST-SPEED-003)')
        self.assertEqual(self.cache().get('family', {'x': 1}, lambda: 3), 2, 'the new key never reads the old file')

    def test_pin_changes_invalidate_warm_entries(self):
        import dataclasses
        import pins
        first = self.cache()
        first.get('family', 1, lambda: 'old original')
        first.save()
        name = next(n for n in pins.PINS if 'section3' in n)
        replacement = dataclasses.replace(pins.PINS[name], sha256='0' * 64)
        with mock.patch.dict(pins.PINS, {name: replacement}):
            fresh = self.cache()
            self.assertNotEqual(fresh.key, first.key)
            self.assertEqual(fresh.get('family', 1, lambda: 'new original'), 'new original')
            self.assertEqual(fresh.hits, 0)

    def test_canonical_case_keys(self):
        self.assertEqual(self.oc.canonical({'b': 1, 'a': (1.5, None)}), self.oc.canonical({'a': (1.5, None), 'b': 1}))
        self.assertNotEqual(self.oc.canonical([1, 2]), self.oc.canonical((1, 2)))
        self.assertNotEqual(self.oc.canonical(0.1), self.oc.canonical(0.1000000001))
        with self.assertRaises(TypeError):
            self.oc.canonical(object())


if __name__ == '__main__':
    unittest.main()
