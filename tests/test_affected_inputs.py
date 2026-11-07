"""Portable checks of the exact-input selection (TEST-SPEED-004, docs/testing/TEST-BUDGET.md).

* Python analysis on small synthetic repositories: a memory-region name is not a path, a constant loop over
  directory names is; an importlib wrapper loading a module by constant name; a function of another module
  receiving ``ROOT / 'reconstructed'`` and running ``make -C directory/'objects'``; ``-I`` and ``glob`` uses of a
  directory; ``sys.path`` imports; a computed import is a reported fallback;
* compiled inputs: a header under ``#if 0`` is not an input (the compiler's -MM), a used one is;
* this repository's registry: a test-only helper and a tooling-only diff select no row, a shared validator
  harness selects exactly the rows importing it, the rows the steward checked by hand in batches 41 and 45
  keep or lose the inputs it found, the old selector's model_light → validate_skinning gap is closed, and the
  set of rows using the conservative fallback is pinned (it may only shrink).
"""
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import affected  # noqa: E402
import run_validators as rv  # noqa: E402

# Rows whose inputs cannot be derived statically (selected for every code change). Shrink it; never grow it
# without a reason in docs/testing/TEST-BUDGET.md.
FALLBACK_ROWS: set[str] = set()


def write(root: Path, files: dict[str, str]) -> Path:
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def deps_of(root: Path, script: str) -> affected.Deps:
    affected.clear_caches(root)
    return affected.python_deps(root / script, root, tooling=False)


class PythonInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_memory_region_name_is_not_a_path_but_a_constant_loop_is(self):
        write(self.root, {
            'reconstructed/objects/objects.c': '', 'reconstructed/joints/joints.c': '',
            'scripts/validate_region.py': "import am\nREGION = am.Region('objects', 0x1000, b'', b'', False)\n"
                                          "KEYS = {'objects': 1, 'joints': 2}\n",
            'scripts/validate_loop.py': "from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n"
                                        "for d in ('joints',):\n    print((ROOT / 'reconstructed' / d).read_text())\n",
        })
        region = deps_of(self.root, 'scripts/validate_region.py')
        self.assertIsNone(region.why('reconstructed/objects/objects.c'))
        self.assertIsNone(region.why('reconstructed/joints/joints.c'))
        loop = deps_of(self.root, 'scripts/validate_loop.py')
        self.assertTrue(loop.why('reconstructed/joints/joints.c'))
        self.assertIsNone(loop.why('reconstructed/objects/objects.c'))

    def test_importlib_wrapper_with_constant_names(self):
        write(self.root, {
            'scripts/helper_a.py': 'import helper_b\n', 'scripts/helper_b.py': '', 'scripts/unused.py': '',
            'scripts/validate_x.py': (
                "import importlib.util, sys\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n"
                "def _load(name):\n    path = ROOT/'scripts'/f'{name}.py'\n"
                "    spec = importlib.util.spec_from_file_location(name, path)\n"
                "    module = importlib.util.module_from_spec(spec)\n    sys.modules[name] = module\n"
                "    spec.loader.exec_module(module)\n    return module\nA = _load('helper_a')\n"),
        })
        deps = deps_of(self.root, 'scripts/validate_x.py')
        self.assertTrue(deps.why('scripts/helper_a.py'))
        self.assertTrue(deps.why('scripts/helper_b.py'))   # followed through the loaded module
        self.assertIsNone(deps.why('scripts/unused.py'))
        self.assertEqual(deps.fallback, {})

    def test_parameter_of_another_modules_function(self):
        write(self.root, {
            'reconstructed/objects/Makefile': 'all: libobjects.so\nlibobjects.so: objects.c\n'
                                              '\tcc -c objects.c -o libobjects.so\n',
            'reconstructed/objects/objects.c': '', 'reconstructed/renderchar/renderchar.c': '',
            'scripts/worlds_lib.py': (
                "import subprocess\ndef build_library(directory):\n"
                "    subprocess.run(['make', '-s', '-C', str(directory / 'objects')], check=True)\n"
                "    return directory / 'objects' / 'libobjects.so'\n"),
            'scripts/validate_w.py': (
                "from pathlib import Path\nimport worlds_lib as v\nROOT = Path(__file__).resolve().parents[1]\n"
                "LIB = v.build_library(ROOT / 'reconstructed')\n"),
        })
        deps = deps_of(self.root, 'scripts/validate_w.py')
        self.assertIn('compiles reconstructed/objects/objects.c', deps.why('reconstructed/objects/objects.c'))
        self.assertIsNone(deps.why('reconstructed/renderchar/renderchar.c'))   # not every reconstructed/ file

    def test_include_directory_glob_and_search_path(self):
        write(self.root, {
            'native/core/a.c': '#include "a.h"\n', 'native/core/a.h': '', 'native/core/b.h': '',
            'native/core/b.c': '', 'reconstructed/quest/quest_1.c': '', 'reconstructed/quest/other.c': '',
            'model-recovery/bmd.py': '', 'model-recovery/unused.py': '',
            'scripts/validate_c.py': (
                "import subprocess, sys\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n"
                "sys.path.insert(0, str(ROOT / 'model-recovery'))\nimport bmd\n"
                "subprocess.run(['cc', '-I', str(ROOT/'native/core'), str(ROOT/'native/core/a.c')])\n"
                "SRC = sorted((ROOT/'reconstructed/quest').glob('quest_*.c'))\n"),
        })
        deps = deps_of(self.root, 'scripts/validate_c.py')
        for path in ('native/core/a.c', 'native/core/a.h', 'reconstructed/quest/quest_1.c', 'model-recovery/bmd.py'):
            self.assertTrue(deps.why(path), path)
        for path in ('native/core/b.h', 'native/core/b.c', 'reconstructed/quest/other.c', 'model-recovery/unused.py'):
            self.assertIsNone(deps.why(path), path)

    def test_computed_import_is_a_reported_fallback(self):
        write(self.root, {'scripts/validate_dyn.py': "import importlib, sys\nM = importlib.import_module(sys.argv[1])\n"})
        deps = deps_of(self.root, 'scripts/validate_dyn.py')
        self.assertTrue(deps.fallback)
        self.assertIn('loads a module from a computed name', next(iter(deps.fallback.values())))
        units = {'validate_dyn': deps, 'validate_other': affected.Deps()}
        why = affected.select(units, ['reconstructed/x/x.c', 'docs/a.md', 'scripts/affected.py'],
                              unmapped_selects_all=False)
        self.assertEqual(list(why), ['validate_dyn'])
        self.assertEqual(len(why['validate_dyn']), 1)    # docs and tooling are not code changes for it
        text = affected.show(why, 2, 'manifest rows', affected.fallback_units(units))
        self.assertIn('1 manifest rows use the conservative fallback', text)


class CompiledInputs(unittest.TestCase):
    def test_header_under_if_0_is_not_an_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root = write(Path(folder), {
                'lib/Makefile': 'all: lib.o\nlib.o: lib.c\n\tcc -DUSE_B=1 -c lib.c -o lib.o\n',
                'lib/lib.c': '#include "used.h"\n#if 0\n#include "dead.h"\n#endif\n'
                             '#if USE_B\n#include "b.h"\n#endif\n',
                'lib/used.h': '', 'lib/dead.h': '', 'lib/b.h': '',
            })
            affected.clear_caches(root)
            deps = affected.target_deps('lib', None, root)
            self.assertTrue(deps.why('lib/used.h'))
            self.assertTrue(deps.why('lib/b.h'))          # -D from the dry-run command is honoured
            self.assertIsNone(deps.why('lib/dead.h'))
            self.assertEqual(len(affected._includes((root / 'lib/lib.c',), (root / 'lib',))), 3)  # textual: all


class RegistryInputs(unittest.TestCase):
    """This repository's registry (dry runs and -MM only; nothing is built)."""

    @classmethod
    def setUpClass(cls):
        cls.rows = rv.load_manifest()

    def deps(self, name):
        return rv.row_deps(name, self.rows[name])

    def select(self, *paths):
        units = {name: self.deps(name) for name in self.rows} if not hasattr(self, '_units') else self._units
        type(self)._units = units
        return rv.affected_rows(self.rows, 'HEAD', changed=list(paths), units=units)

    def test_test_only_helper_and_tooling_select_no_row(self):
        for path in ('scripts/guarded_run.py', 'scripts/run_validators.py', 'scripts/run_test_suites.py',
                     'scripts/affected.py', 'scripts/affected_symbols.py', 'scripts/original_cache.py',
                     'tests/test_test_budget.py', 'tests/test_affected_symbols.py',
                     'tests/test_affected_inputs.py', 'docs/testing/TEST-BUDGET.md'):
            with self.subTest(path=path):
                self.assertEqual(self.select(path), {})

    def test_shared_harness_selects_exactly_its_importers(self):
        why = self.select('scripts/gen_item_bodies.py')
        importers = {name for name in self.rows if self.deps(name).why('scripts/gen_item_bodies.py')}
        self.assertEqual(set(why), importers)
        self.assertIn('validate_item_ranked', why)
        self.assertNotIn('validate_worlds_s', why)
        self.assertNotIn('validate_render_effects', why)

    def test_steward_hand_checks(self):
        # batch 45: the 'objects' Unicorn region name in joints/render_effects; render_effects9-14's only
        # native/core input is mu_named_bones.c
        for name in ('validate_joints', 'validate_render_effects', 'validate_worlds_l', 'validate_worlds_m'):
            self.assertIsNone(self.deps(name).why('reconstructed/objects/object_render.c'), name)
        dep = self.deps('validate_render_effects9')
        self.assertTrue(dep.why('native/core/mu_named_bones.c'))
        self.assertIsNone(dep.why('native/core/mu_objects_runtime.c'))
        # batch 45: mu_objects_runtime.c is compiled into libmunative.a, which the audio rows link
        self.assertTrue(self.deps('validate_audio_callers').why('native/core/mu_objects_runtime.c'))
        # the worlds validators build reconstructed/objects through another module's build_library()
        dep = self.deps('validate_worlds_j')
        self.assertTrue(dep.why('reconstructed/objects/objects.c'))
        self.assertIsNone(dep.why('reconstructed/renderchar/renderchar.c'))

    def test_dynamic_module_load_is_followed(self):
        # validate_model_light loads validate_skinning with importlib; the TEST-SPEED-002 selector missed it
        dep = self.deps('validate_model_light')
        self.assertTrue(dep.why('scripts/validate_skinning.py'))
        self.assertTrue(dep.why('scripts/validate_pose_builder.py'))

    def test_fallback_rows_are_pinned(self):
        units = {name: self.deps(name) for name in self.rows}
        fallback = affected.fallback_units(units)
        self.assertEqual(set(fallback), FALLBACK_ROWS,
                         'rows whose inputs cannot be derived changed; see docs/testing/TEST-BUDGET.md')

    def test_list_affected_prints_the_fallback_section(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = rv.main(['--list-affected-since', 'HEAD'])
        self.assertEqual(code, 0)
        self.assertRegex(out.getvalue(), r'affected: \d+ of \d+ manifest rows selected')


if __name__ == '__main__':
    unittest.main()
