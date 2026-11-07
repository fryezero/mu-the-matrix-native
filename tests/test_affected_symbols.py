"""Portable checks of the symbol-level selection (TEST-SPEED-005, docs/testing/TEST-BUDGET.md).

Each case is a small git repository with a make-built shared library that a row loads with ctypes. The row's
Python names some of the library's exports; the working tree changes the C source after the base commit:

* a change to an export the row does not name selects nothing; one it names selects the row;
* a change to a static callee selects the rows naming any export that reaches it;
* a changed mutable global is global data: every row, as a reported fallback;
* a constant table counts only for the functions that read it; a struct layout change for every function
  touching the struct;
* a new duplicate definition (steward batch 2's ``mu_swamp_*``) or a new unresolved reference is a fallback;
* a name built at run time (``'mu_' + name``) can only be filled with the program's own word pieces;
* mutant copies of the sources do not stop the pruning, unless the link structure changed;
* an argparse default inside an imported module's ``main()`` is not an input unless that main is called.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import affected  # noqa: E402
import affected_symbols  # noqa: E402

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
MAKEFILE = (f'all: libx.{SUFFIX}\nlibx.{SUFFIX}: a.c b.c x.h\n'
            f'\tcc -std=c11 -O2 -fPIC -shared a.c b.c -o libx.{SUFFIX}\n')
A_C = '''#include "x.h"
static int helper(int v) { return v + 1; }
static const int table[3] = {1, 2, 3};
int counter = 0;
int used(int v) { return helper(v); }
int unused(int v) { return v * 2; }
int reads_table(int i) { return table[i]; }
int sums(struct pair *p) { return p->a + p->b; }
int passes(struct pair *p) { return opaque(p); }
'''
B_C = '''#include "x.h"
int opaque(struct pair *p) { (void)p; return 7; }
int other(int v) { return v - 1; }
'''
X_H = 'struct pair { int a; int b; };\nint opaque(struct pair *p);\n'


def row(names: str, extra: str = '') -> str:
    return ('import ctypes, subprocess\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n'
            "subprocess.run(['make', '-s', '-C', str(ROOT / 'lib')], check=True)\n"
            f"lib = ctypes.CDLL(str(ROOT / 'lib' / 'libx.{SUFFIX}'))\n"
            + ''.join(f'lib.{n}(1)\n' for n in names.split()) + extra)


def git(root: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout


class SymbolSelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.write({'lib/Makefile': MAKEFILE, 'lib/a.c': A_C, 'lib/b.c': B_C, 'lib/x.h': X_H,
                    'scripts/validate_used.py': row('used'), 'scripts/validate_unused.py': row('unused'),
                    'scripts/validate_table.py': row('reads_table'), 'scripts/validate_sums.py': row('sums'),
                    'scripts/validate_passes.py': row('passes'), 'scripts/validate_other.py': row('other')})
        git(self.root, 'init', '-q')
        self.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, files: dict[str, str]) -> None:
        for path, text in files.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text)

    def commit(self) -> None:
        git(self.root, 'add', '-A')
        git(self.root, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'base')
        self.base = git(self.root, 'rev-parse', 'HEAD').strip()

    def edit(self, path: str, old: str, new: str) -> None:
        text = (self.root / path).read_text()
        self.assertIn(old, text)
        (self.root / path).write_text(text.replace(old, new, 1))

    def units(self) -> dict[str, affected.Deps]:
        affected.clear_caches(self.root)
        return {p.stem: affected.python_deps(p, self.root, tooling=False)
                for p in sorted((self.root / 'scripts').glob('validate_*.py'))}

    def select(self, pruned: dict | None = None) -> dict[str, list[str]]:
        changed = affected.changed_files(self.base, self.root, since=True)
        return affected.select(self.units(), changed, base=self.base, root=self.root,
                               unmapped_selects_all=False, symbols=True, pruned=pruned)

    def test_unused_symbol_change_selects_only_its_users(self):
        self.edit('lib/a.c', 'return v * 2;', 'return v * 3;')
        pruned = {}
        why = self.select(pruned)
        self.assertEqual(set(why), {'validate_unused'})
        self.assertIn('uses unused changed', why['validate_unused'][0])
        self.assertIn('validate_used', pruned)
        self.assertNotIn('validate_other', why)   # b.c's rows build the same library

    def test_static_callee_change_selects_the_callers_users(self):
        self.edit('lib/a.c', 'return v + 1;', 'return v + 2;')
        why = self.select()
        self.assertEqual(set(why), {'validate_used'})
        self.assertIn('reaches helper', why['validate_used'][0])

    def test_global_data_change_is_a_fallback_for_every_user(self):
        self.edit('lib/a.c', 'int counter = 0;', 'int counter = 5;')
        why = self.select()
        self.assertEqual(set(why), {'validate_used', 'validate_unused', 'validate_table', 'validate_sums',
                                    'validate_passes', 'validate_other'})
        self.assertTrue(all(affected.SYMBOL_FALLBACK in r[0] and 'global data' in r[0] for r in why.values()))
        listing = affected.show(why, len(why), 'manifest rows')
        self.assertIn('6 manifest rows kept by the symbol-level fallback', listing)

    def test_constant_table_counts_only_for_its_readers(self):
        self.edit('lib/a.c', '{1, 2, 3}', '{1, 2, 4}')
        self.assertEqual(set(self.select()), {'validate_table'})

    def test_struct_layout_change_counts_for_functions_touching_it(self):
        self.edit('lib/x.h', 'struct pair { int a; int b; };', 'struct pair { short a; int b; };')
        why = self.select()
        # sums reads the fields; passes only hands the pointer to opaque (b.c), which does not touch it
        self.assertEqual(set(why), {'validate_sums'})

    def test_new_duplicate_definition_is_a_fallback(self):
        self.write({'lib/b.c': B_C + 'int unused(int v) { return v; }\n'})
        why = self.select()
        self.assertIn('validate_used', why)
        self.assertIn('new duplicate definition of unused', why['validate_used'][0])

    def test_new_unresolved_reference_is_a_fallback(self):
        self.edit('lib/a.c', 'return v * 2;', 'extern int nowhere_defined(int);\n  return nowhere_defined(v);')
        why = self.select()
        self.assertIn('validate_used', why)
        self.assertIn('new unresolved reference to nowhere_defined', why['validate_used'][0])

    def test_unit_that_does_not_compile_is_a_fallback(self):
        self.edit('lib/a.c', 'return v * 2;', 'return v * ;')
        why = self.select()
        self.assertIn('validate_used', why)
        self.assertIn('does not compile to IR', why['validate_used'][0])

    def test_built_name_uses_only_the_programs_word_pieces(self):
        self.write({'scripts/validate_built.py': row('', "for n in BODIES:\n    getattr(lib, 'un' + n)(1)\n"
                                                         "BODIES = {'used': 1}\n"),
                    'scripts/validate_param.py': row('', "def call(name):\n    return getattr(lib, 'oth' + name)\n")})
        self.commit()
        self.edit('lib/a.c', 'return v * 2;', 'return v * 3;')   # 'unused'
        why = self.select()
        self.assertIn('validate_built', why)        # 'un' + 'used' (a dict key the loop reads)
        self.assertNotIn('validate_param', why)     # 'oth' + * cannot spell 'unused'
        self.assertTrue(affected.template_matches('mu_*_move', 'mu_swamp_darkness_move',
                                                  frozenset({'swamp', 'darkness'})))
        self.assertFalse(affected.template_matches('mu_*', 'mu_obj_visual_flicker',
                                                   frozenset({'obj', 'visual'})))

    def test_unbounded_lookup_is_a_reported_fallback(self):
        self.write({'scripts/validate_dynamic.py': row('', 'import sys\ngetattr(lib, sys.argv[1] + sys.argv[2])\n')})
        self.commit()
        self.edit('lib/a.c', 'return v * 2;', 'return v * 3;')
        why = self.select()
        self.assertIn('validate_dynamic', why)
        self.assertIn('looks up a symbol name it cannot bound', why['validate_dynamic'][0])

    def test_mutant_copies_do_not_stop_pruning_unless_the_link_changes(self):
        mutant = ("import shutil, tempfile\ndef run_mutants():\n    with tempfile.TemporaryDirectory() as t:\n"
                  "        shutil.copytree(ROOT / 'lib', Path(t) / 'lib')\n"
                  "        subprocess.run(['make', '-s', '-C', str(Path(t) / 'lib')], check=True)\n"
                  "if __name__ == '__main__':\n    import sys\n    if '--mutants' in sys.argv:\n        run_mutants()\n")
        self.write({'scripts/validate_used.py': row('used', mutant)})
        self.commit()
        deps = self.units()['validate_used']
        self.assertTrue(deps.why('lib/a.c'))
        self.assertTrue(deps.mutant_route('lib/a.c'))
        self.edit('lib/a.c', 'return v * 2;', 'return v * 3;')
        self.assertNotIn('validate_used', self.select())
        self.edit('lib/a.c', 'return v * 3;', 'int other(int);\n  return other(v);')   # a.c now calls into b.c
        why = self.select()
        self.assertIn('validate_used', why)
        self.assertIn('mutant builds copy these sources', why['validate_used'][0])

    def test_main_only_default_of_an_imported_module_is_not_an_input(self):
        helper = ("import argparse\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n"
                  "def shared():\n    return 1\n"
                  "def main():\n    p = argparse.ArgumentParser()\n"
                  f"    p.add_argument('--library', default=str(ROOT / 'lib' / 'libx.{SUFFIX}'))\n"
                  "    return p.parse_args()\n"
                  "if __name__ == '__main__':\n    main()\n")
        self.write({'scripts/harness.py': helper,
                    'scripts/validate_imports.py': 'import harness\nharness.shared()\n',
                    'scripts/validate_calls_main.py': 'import harness\nharness.main()\n'})
        units = self.units()
        self.assertIsNone(units['validate_imports'].why('lib/a.c'))
        self.assertTrue(units['validate_calls_main'].why('lib/a.c'))
        self.assertTrue(affected.python_deps(self.root / 'scripts/harness.py', self.root, tooling=False)
                        .why('lib/a.c'))   # run as a program, its main counts


class IRParsing(unittest.TestCase):
    def test_renumbered_anonymous_constants_are_no_change(self):
        base = ('@.str = private unnamed_addr constant [3 x i8] c"ab\\00", align 1\n'
                'define ptr @f() #0 {\n  ret ptr @.str\n}\n')
        head = ('@.str = private unnamed_addr constant [3 x i8] c"zz\\00", align 1\n'
                '@.str.1 = private unnamed_addr constant [3 x i8] c"ab\\00", align 1\n'
                'define ptr @g() #1 {\n  ret ptr @.str\n}\n'
                'define ptr @f() #1 {\n  ret ptr @.str.1, !dbg !7\n}\n')
        before, after = affected_symbols.parse_ir(base, 'a.c'), affected_symbols.parse_ir(head, 'a.c')
        self.assertEqual(before.nodes['f'].fingerprint, after.nodes['f'].fingerprint)
        self.assertNotIn('.str', after.nodes)

    def test_static_local_state_is_global_data(self):
        text = ('@f.count = internal global i32 0, align 4\n'
                'define i32 @f() {\n  %1 = load i32, ptr @f.count\n  ret i32 %1\n}\n')
        unit = affected_symbols.parse_ir(text, 'a.c')
        self.assertTrue(any(n.kind == 'var' for n in unit.nodes.values()))


if __name__ == '__main__':
    unittest.main()
