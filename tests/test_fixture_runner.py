"""Portable policy tests for VERIFY-SESSION-001, without client data or a native build."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_fixture_scenarios as runner


def evidence():
    return [
        {'jnl': 'frame_in', 'conn': 'game', 'head': 0xc1, 'opcode': 85, 'sub': 148,
         'client_handler': 123, 'apply': 'hero_speed', 'decode': 'ok', 'encrypted': 0},
        {'jnl': 'intent', 'kind': 'master_point', 'status': 'unrecovered'},
        {'expect': 'hero.level = 1', 'pass': True},
        {'fixture': {'last_error': '', 'undecodable_requests': 0, 'refused_connects': 0}},
        {'transport': {'kind': 'fixture', 'links_opened': 1, 'links_refused': 0}},
        {'summary': dict.fromkeys(('frames_in', 'frames_out', 'intents', 'unrecovered_intents',
                                  'snapshots', 'ticks'), 1) | dict.fromkeys(
                                      ('unbound_frames', 'undecodable_frames', 'unsent_frames', 'cues', 'inputs'), 0)}]


class FixtureRunner(unittest.TestCase):
    def test_discovery_needs_no_shared_list_and_requires_each_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'no fixture scenarios'):
                runner.discover(directory, directory)
            (directory / 'hero.ops').touch()
            (directory / 'hero-a.scn').touch()
            self.assertEqual([p.name for p in runner.discover(directory, directory)], ['hero-a.scn'])
            (directory / 'items.ops').touch()
            with self.assertRaisesRegex(ValueError, 'items'):
                runner.discover(directory, directory)
            (directory / 'items-b.scn').touch()
            self.assertEqual(len(runner.discover(directory, directory)), 2)

    def test_inbound_events_use_existing_send_commands(self):
        self.assertEqual(runner.script_lines('3:inbound:c103fe 4:inbound:c2000455'),
                         ['at 3 send game c1 03 fe', 'at 4 send game c2 00 04 55'])

    def test_bad_events_fail_before_running(self):
        for script in ('0:inbound:c103fe', '1:inbound:c303fe', '1:inbound:00', '1:inbound:c104fe',
                       '1:inbound:c103fec103fe', '1:inbound:abc', '1:other:c103fe',
                       '1000001:inbound:c103fe', '1:inbound:c1ff' + '00' * 253):
            with self.subTest(script=script), self.assertRaises(ValueError):
                runner.script_lines(script)

    def test_schedule_includes_server_only_tail_and_script_tail(self):
        _, ticks = runner.prepare('at 100 progress join\n', '')
        self.assertEqual(ticks, 120)
        _, ticks = runner.prepare('at 100 progress join\n', '140:inbound:c103fe')
        self.assertEqual(ticks, 160)

    def test_only_numeric_loopback_endpoints_are_accepted(self):
        for host in ('192.0.2.1', 'example.com', '127.0.0.1:0'):
            endpoint = host if host.endswith(':0') else host + ':55901'
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                runner.prepare('endpoint game ' + endpoint, '')
        runner.prepare('endpoint game 127.0.0.1:55901', '')

    def test_journal_summary_and_per_route_counts(self):
        result = runner.assess(evidence(), 0)
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['unrecovered_by_intent'], {'master_point': 1})
        self.assertEqual(result['routes'][0]['frames'], 1)

    def test_missing_or_false_evidence_fails_closed(self):
        rows = evidence()
        for index in range(len(rows)):
            with self.subTest(index=index):
                self.assertFalse(runner.assess(rows[:index] + rows[index + 1:], 0)['pass'])
        for index, field, value in ((0, 'apply', None), (0, 'decode', 'bad'), (0, 'head', 0xc3),
                                    (0, 'encrypted', 1), (2, 'pass', False)):
            mutant = deepcopy(rows)
            mutant[index][field] = value
            self.assertFalse(runner.assess(mutant, 0)['pass'])
        self.assertFalse(runner.assess(rows, 1)['pass'])

    def test_bad_counters_fail_even_when_scenario_assertions_pass(self):
        for field, value in (('unbound_frames', 1), ('undecodable_frames', 1), ('frames_in', 2),
                             ('unrecovered_intents', 0), ('ticks', -1), ('intents', True)):
            mutant = evidence()
            mutant[-1]['summary'][field] = value
            self.assertFalse(runner.assess(mutant, 0)['pass'], field)
        for index, field, value in ((3, 'last_error', 'failed'), (3, 'undecodable_requests', 1),
                                    (3, 'refused_connects', 1), (4, 'kind', 'sockets'), (4, 'links_refused', 1)):
            mutant = evidence()
            key = 'fixture' if index == 3 else 'transport'
            mutant[index][key][field] = value
            self.assertFalse(runner.assess(mutant, 0)['pass'], field)


if __name__ == '__main__':
    unittest.main()
