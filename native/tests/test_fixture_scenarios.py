"""The discovered full-stack fixture suites and verification skill, synthetic and loopback only."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_fixture_scenarios as runner

V = ROOT / '.claude/skills/verify-mu-native/scripts'
PROGRESS = runner.SCENARIOS / 'hero-progress.scn'
SPEED = 'c10c55941500000015000000'


@unittest.skipUnless(runner.TOOL.exists(), 'mu-session not built (make -C native)')
class FixtureScenarios(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def drive(self, report='suite', *args):
        process = subprocess.run([sys.executable, str(ROOT / 'scripts/run_fixture_scenarios.py'),
                                  '--report', str(self.directory / report), *map(str, args)],
                                 capture_output=True, text=True, timeout=120)
        return process, runner.read_rows(process.stdout)

    def test_every_discovered_scenario_runs_in_make_test(self):
        process, rows = self.drive()
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        summary = rows[-1]
        self.assertEqual(summary['scenarios'], len(runner.discover(runner.SCENARIOS, runner.OPS)))
        self.assertEqual(summary['failed'], 0)
        applies = set()
        for result in summary['results']:
            self.assertEqual(result['journal']['unbound_frames'], 0)
            applies.update(r['apply'] for r in result['routes'])
            folder = self.directory / 'suite' / Path(result['scenario']).stem
            self.assertEqual((folder / 'session.mujnl').read_bytes()[:8], b'MUJNL\x00\x01\x00')
        self.assertTrue({'hero_stats', 'hero_speed', 'hero_levelup', 'hero_point', 'hero_respawn',
                         'hero_kill_exp', 'hero_master_exp', 'hero_master_levelup'} <= applies)

    def test_skill_fixture_script_journal_summary_and_cleanup(self):
        run = self.directory / 'verify-runs' / 'skill'
        run.mkdir(parents=True)
        process = subprocess.run([str(V / 'run-tool.sh'), str(run), 'inbound', '--fixture', str(PROGRESS),
                                  '--script', '60:inbound:' + SPEED], capture_output=True, text=True, timeout=120)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        summary = runner.read_rows(process.stdout)[-1]
        self.assertEqual(summary['journal']['frames_in'], 14)
        self.assertEqual(summary['results'][0]['unrecovered_by_intent'], {'master_point': 1})
        self.assertTrue(any(r.get('jnl') == 'frame_in' and r['tick'] == 60 and r['bytes'].replace(' ', '') == SPEED
                            for r in runner.read_rows(process.stdout)))
        for args, expected in ((['journal.frames_in'], '14'), (['--frames'], 'hero_speed'),
                               (['--last'], 'hero_speed')):
            process = subprocess.run([sys.executable, str(V / 'summary.py'), str(run / 'proof/inbound.stdout'),
                                      *args], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn(expected, process.stdout)
        self.assertEqual((run / 'proof/inbound.exit').read_text().strip(), '0')
        self.assertEqual((run / 'pids').read_text(), '')
        subprocess.run([str(V / 'cleanup.sh'), str(run)], check=True, capture_output=True)
        self.assertTrue((run / 'proof/inbound/hero-progress/session.mujnl').exists())
        self.assertFalse((run / 'tmp').exists())

    def test_unbound_route_fails_even_without_an_expect_for_it(self):
        scenario = self.directory / 'hero-unbound.scn'
        scenario.write_text(PROGRESS.read_text().replace('expect unbound = 0', '# removed on purpose'))
        process, rows = self.drive('unbound', '--fixture', scenario, '--script', '60:inbound:c103fe')
        self.assertEqual(process.returncode, 1, process.stderr)
        result = rows[-1]['results'][0]
        self.assertEqual(result['journal']['unbound_frames'], 1)
        self.assertIn('unbound inbound route', result['errors'])

    def test_failed_expectation_is_not_hidden_by_zero_unbound(self):
        scenario = self.directory / 'hero-wrong.scn'
        scenario.write_text(PROGRESS.read_text().replace('hero.level = 4', 'hero.level = 99'))
        process, rows = self.drive('wrong', '--fixture', scenario)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(rows[-1]['journal']['unbound_frames'], 0)
        self.assertIn('missing or failed scenario expectations', rows[-1]['results'][0]['errors'])

    def test_empty_journey_is_not_a_pass(self):
        scenario = self.directory / 'hero-empty.scn'
        scenario.write_text('endpoint game 127.0.0.1:55901\njoin world=0 tile=1,1 class=1\nexpect unbound = 0\n')
        process, rows = self.drive('empty', '--fixture', scenario)
        self.assertEqual(process.returncode, 1)
        self.assertIn('no inbound frames or journal frame count differs', rows[-1]['results'][0]['errors'])

    def test_bad_event_and_non_loopback_scenario_never_start_tool(self):
        scenario = self.directory / 'hero-network.scn'
        scenario.write_text(PROGRESS.read_text().replace('127.0.0.1', '192.0.2.1'))
        for name, args in (('endpoint', ['--fixture', scenario]),
                           ('crypto', ['--fixture', PROGRESS, '--script', '60:inbound:c303fe'])):
            process, rows = self.drive(name, *args)
            self.assertEqual(process.returncode, 1)
            self.assertFalse((self.directory / name / Path(args[1]).stem / 'command.json').exists())
            self.assertEqual(rows[-1]['failed'], 1)

    def test_output_directory_cannot_reuse_stale_evidence(self):
        self.drive()
        process, _ = self.drive()
        self.assertEqual(process.returncode, 2)
        self.assertIn('File exists', process.stderr)

    def test_timeout_fails_and_retains_attempt_evidence(self):
        process, rows = self.drive('timeout', '--fixture', PROGRESS, '--timeout', '0.000001')
        self.assertEqual(process.returncode, 1)
        self.assertEqual(rows[-1]['failed'], 1)
        folder = self.directory / 'timeout/hero-progress'
        self.assertEqual((folder / 'exit.txt').read_text(), 'timeout\n')
        self.assertTrue((folder / 'stdout.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
