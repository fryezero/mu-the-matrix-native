"""The session's generated lists and the negative build tests (SESSION-CORE-001).

scripts/gen_domains.py joins native/session/ops/*.ops with the route table and generates the domain,
intent and behaviour lists. Portable checks, each on a temporary copy of the session sources:
  * the real tree generates; every intent kind has an MU_SUBMIT route; every hero row is bound to its
    seeded route; the seed is used while native/net/dispatch.def does not exist, and dispatch.def wins
    as soon as it does (the wire-research lane's file);
  * a duplicate ops row fails the build twice over: the generator refuses it, and with the generator's
    checks switched off the generated dispatcher does not compile (duplicate case);
  * an MU_OP naming no route, an MU_OP and an MU_IGNORE on one route, an intent kind without a route,
    two owners of one kind (also an initializer override past the generator), a domain with state but
    no ops file, and two fixture behaviours with one name all fail.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
GEN = ROOT / 'scripts/gen_domains.py'
CC = shutil.which('clang') or shutil.which('cc')
WARN = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-Werror=initializer-overrides']


def make_tree(tmp: Path) -> Path:
    """A copy of what dispatch.c and the generator read, at the same relative places."""
    t = tmp / 'repo'
    shutil.copytree(NATIVE / 'session', t / 'native/session')
    (t / 'native/net').mkdir(parents=True)
    for p in (NATIVE / 'net').glob('*.h'):
        shutil.copy(p, t / 'native/net' / p.name)
    shutil.copy(NATIVE / 'net/dispatch.seed.def', t / 'native/net/dispatch.seed.def')
    (t / 'native/core').mkdir(parents=True)
    shutil.copy(NATIVE / 'core/mu_protocol.h', t / 'native/core/mu_protocol.h')
    if (NATIVE / 'fixture').exists():
        shutil.copytree(NATIVE / 'fixture', t / 'native/fixture')
    else:
        (t / 'native/fixture/behaviors').mkdir(parents=True)
    (t / 'reconstructed/progress').mkdir(parents=True)
    shutil.copy(ROOT / 'reconstructed/progress/progress.h', t / 'reconstructed/progress/progress.h')
    return t


def gen(t: Path, *extra):
    subprocess.run([sys.executable, str(ROOT / 'scripts/gen_layout.py'), '--layout',
                    str(t / 'native/session/layout'), '--out', str(t / 'gen')], check=True)
    return subprocess.run([sys.executable, str(GEN), '--session', str(t / 'native/session'), '--net',
                           str(t / 'native/net'), '--fixture', str(t / 'native/fixture'), '--out', str(t / 'gen'),
                           *extra], capture_output=True, text=True)


def compile_dispatch(t: Path):
    return subprocess.run([CC, *WARN, '-fsyntax-only', '-I', str(t / 'gen'), '-I', str(t / 'native/session'),
                           str(t / 'native/session/dispatch.c')], capture_output=True, text=True)


def append(path: Path, text: str):
    path.write_text(path.read_text() + text)


class Generated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = make_tree(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def summary(self):
        return json.loads((self.t / 'gen/gen_domains.json').read_text())

    def test_real_tree_generates_and_every_kind_is_routed(self):
        r = subprocess.run([sys.executable, str(GEN), '--out', str(self.t / 'gen')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.summary()
        expected_table = 'native/net/dispatch.def' if (NATIVE / 'net/dispatch.def').exists() \
            else 'native/net/dispatch.seed.def'
        self.assertEqual(s['route_table'], expected_table)
        self.assertIn('hero', s['domains'])
        self.assertTrue(s['intents'])
        for k in s['intents']:
            self.assertIsNotNone(k['submit'], k)
        bound = {(r['opcode'], r['sub']): (r['client_handler'], r['apply']) for r in s['routes'] if r['apply']}
        self.assertEqual(bound[(0x16, None)], (0x01234c08, 'hero_kill_exp'))
        self.assertEqual(bound[(0xA0, 0x06)], (0x01250b05, 'hero_levelup'))
        self.assertEqual(bound[(0xA0, 0x11)], (0x01223f04, 'hero_point'))
        self.assertEqual(bound[(0xA0, 0x22)], (0x01285b68, 'hero_master_levelup'))
        self.assertEqual(bound[(0xA0, 0x30)], (0x0127bd9e, 'hero_respawn'))
        self.assertEqual(bound[(0xA0, 0x60)], (0x01285efa, 'hero_master_exp'))
        self.assertEqual(bound[(0x55, 0x57)], (0x0122a5f6, 'hero_stats'))
        self.assertEqual(bound[(0x55, 0x94)], (0x0122a13d, 'hero_speed'))

    def test_copy_generates_and_compiles(self):
        r = gen(self.t)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.summary()['route_table'].endswith('native/net/dispatch.seed.def'))
        if CC:
            c = compile_dispatch(self.t)
            self.assertEqual(c.returncode, 0, c.stderr)

    def test_dispatch_def_wins_over_the_seed(self):
        (self.t / 'native/net/dispatch.def').write_text(
            'MU_FAMILY(0xA0, 3, 4, 0x0128805cu)\nMU_ROUTE(0xA0, 0x06, 0x01250b05u, MU_VERIFIED)\n'
            'MU_ROUTE(0x16, MU_SUB_NONE, 0x01234c08u, MU_VERIFIED)\nMU_ROUTE(0x77, MU_SUB_NONE, 0x01111111u, MU_VERIFIED)\n'
            'MU_FAMILY(0x55, 3, 4, MU_ADDR_UNVERIFIED)\nMU_ROUTE(0x55, 0x57, 0x0122a5f6u, MU_VERIFIED)\n'
            'MU_ROUTE(0x55, 0x94, 0x0122a13du, MU_VERIFIED)\nMU_ROUTE(0xA0, 0x11, 0x01223f04u, MU_VERIFIED)\n'
            'MU_ROUTE(0xA0, 0x22, 0x01285b68u, MU_VERIFIED)\nMU_ROUTE(0xA0, 0x30, 0x0127bd9eu, MU_VERIFIED)\n'
            'MU_ROUTE(0xA0, 0x60, 0x01285efau, MU_VERIFIED)\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.summary()
        self.assertTrue(s['route_table'].endswith('native/net/dispatch.def'), s['route_table'])
        self.assertEqual({r['evidence'] for r in s['routes']}, {'MU_VERIFIED'})
        self.assertIn((0x77, None), {(r['opcode'], r['sub']) for r in s['routes'] if r['apply'] is None})

    def test_duplicate_ops_row_fails_the_build(self):
        append(self.t / 'native/session/ops/hero.ops', 'MU_OP(0xA0, 0x06, hero_levelup)\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('binds a route already bound by ops/hero.ops', r.stderr)
        self.assertFalse((self.t / 'gen/bound_routes.def').exists())   # nothing written
        # past the generator, the duplicate is a duplicate case label: the dispatcher does not compile
        r = gen(self.t, '--no-checks')
        self.assertEqual(r.returncode, 0, r.stderr)
        if not CC:
            self.skipTest('no C compiler for the second half')
        c = compile_dispatch(self.t)
        self.assertNotEqual(c.returncode, 0)
        self.assertIn('duplicate case value', c.stderr)

    def test_op_without_route_fails(self):
        append(self.t / 'native/session/ops/hero.ops', 'MU_OP(0x99, MU_SUB_NONE, hero_levelup)\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('names no route', r.stderr)

    def test_op_and_ignore_on_one_route_fail(self):
        (self.t / 'native/net/ignore.def').write_text('MU_IGNORE(0xA0, 0x06, "a test reason")\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('share route', r.stderr)

    def test_intent_kind_without_route_fails(self):
        append(self.t / 'native/session/domains/hero.intents', 'MU_INTENT_KIND(EXTRA, extra, struct { int32_t a, b; })\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('MU_INTENT_EXTRA has no MU_SUBMIT route', r.stderr)

    def test_two_owners_of_one_kind_fail(self):
        append(self.t / 'native/session/ops/hero.ops', 'MU_SUBMIT(MU_INTENT_ADD_STAT, hero_master_point)\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('MU_INTENT_ADD_STAT is already routed', r.stderr)
        r = gen(self.t, '--no-checks')
        self.assertEqual(r.returncode, 0, r.stderr)
        if not CC:
            self.skipTest('no C compiler for the second half')
        c = compile_dispatch(self.t)
        self.assertNotEqual(c.returncode, 0)
        self.assertIn('initializer', c.stderr)

    def test_domain_state_without_ops_fails(self):
        (self.t / 'native/session/domains/extra_state.h').write_text('typedef struct mu_dom_extra { int x; } mu_dom_extra;\n')
        (self.t / 'native/session/domains/extra.h').write_text('/* public */\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('domains/extra_state.h has no ops/extra.ops', r.stderr)

    def test_duplicate_behaviour_name_fails(self):
        b = self.t / 'native/fixture/behaviors'
        b.mkdir(parents=True, exist_ok=True)
        (b / 'aaa.c').write_text('const mu_fixture_behavior mu_fx_aaa = {.name = "same"};\n')
        (b / 'bbb.c').write_text('const mu_fixture_behavior mu_fx_bbb = {.name = "same"};\n')
        r = gen(self.t)
        self.assertEqual(r.returncode, 1)
        self.assertIn('behaviour name "same" repeats', r.stderr)


if __name__ == '__main__':
    unittest.main()
