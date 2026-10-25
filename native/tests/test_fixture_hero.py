"""The fixture server and the hero domain's vertical slice (FIXTURE-001 with SESSION-CORE-001).

Portable, synthetic, loopback only:
  * the fixture's real C1 frames reach the hero domain through transport -> dechunker -> dispatch ->
    mu_prg_recv_*: every frame of native/fixture/scenarios/hero-progress.scn is routed to the apply
    function bound to its client handler, with no unbound and no undecodable frame, and every
    expectation of the scenario holds;
  * A0 06 and A0 11 update the hero: the level-up's level, points and maxima (the demo server's values)
    and the stat answer's point and maximum, through the verified handlers;
  * the stat request goes out through the verified builder (XorData on the two data bytes, Send(0, 0)),
    the fixture undoes the XorData and answers;
  * two seeds give two journals, each reproducible byte for byte;
  * over TCP: `mu-session serve` on 127.0.0.1 and `mu-session connect`, i.e. the product sockets
    transport with its client lock (in a temporary directory), carry the same frames;
  * mu-session refuses a non-loopback --to before creating any transport.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_session_support import SCENARIOS, TOOL, first, hexbytes, jnl, run_tool, unxor, write_scenario  # noqa: E402

HEAD = 'endpoint game 127.0.0.1:55901\nuse progress class=0x01 level=1 latency=1\n' \
       'join world=0 tile=133,127 angle=0 class=0x01 level=1 name=Hero slot=0\n'


def routes():
    _, rows = run_tool('routes')
    return {(r['route']['opcode'], r['route']['sub']): r['route'] for r in rows if 'route' in r}


@unittest.skipUnless(TOOL.exists(), 'mu-session not built (make -C native)')
class FixtureHero(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixture_frames_reach_the_hero_domain(self):
        r, rows = run_tool('fixture', SCENARIOS / 'hero-progress.scn')
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr)
        expects = [x for x in rows if 'expect' in x]
        self.assertEqual(len(expects), 13)
        self.assertTrue(all(x['pass'] for x in expects), expects)
        table = routes()
        frames = jnl(rows, 'frame_in')
        self.assertEqual(len(frames), 13)
        seen = set()
        for f in frames:
            self.assertEqual((f['conn'], f['head'], f['decode']), ('game', 0xC1, 'ok'))
            route = table[(f['opcode'], f['sub'])]
            self.assertEqual(f['client_handler'], route['client_handler'])
            self.assertEqual(f['apply'], route['apply'])
            seen.add((f['opcode'], f['sub']))
        self.assertEqual(seen, {(0x55, 0x57), (0x55, 0x94), (0x16, None), (0xA0, 0x06), (0xA0, 0x11), (0xA0, 0x30)})
        summary = first(rows, 'summary')
        self.assertEqual((summary['unbound_frames'], summary['undecodable_frames']), (0, 0))
        hero = first(rows, 'hero')
        self.assertEqual(hero['stats'], [29, 21, 25, 10, 0])
        self.assertEqual(hero['speed_text'], '21 / 400')
        self.assertEqual(hero['derived'], 1)                          # the stat machine recalculated (0x00a00fb7)
        fixture = first(rows, 'fixture')
        self.assertEqual((fixture['requests'], fixture['undecodable_requests'], fixture['last_error']), (2, 0, ''))

    def test_level_up_and_stat_answer_update_the_hero(self):
        scn = write_scenario(self.dir / 'a.scn', HEAD + 'at 2 progress levelup\nat 6 client submit add_stat 2\n')
        r, rows = run_tool('fixture', scn, '--ticks', 6)
        self.assertEqual(r.returncode, 0, r.stderr)
        hero = first(rows, 'hero')
        # A0 06 (the demo server's level 2 values for a Dark Knight: HP 1100 + 20/10, MP 200, SD 83*6/10 + 6, AG 25)
        self.assertEqual((hero['level'], hero['points'], hero['next_exp']), (2, 5, 340))
        self.assertEqual((hero['hp'], hero['mp'], hero['sd'], hero['ag']), ([1102, 1102], [200, 200], [0, 55], [0, 25]))
        r, rows = run_tool('fixture', scn, '--ticks', 12)
        self.assertEqual(r.returncode, 0, r.stderr)
        hero = first(rows, 'hero')
        # A0 11 accepted for vitality: points - 1, HP max from +6 (1100 + 2 + 1 * 30 / 10); 0x55 0x57 the stat
        self.assertEqual((hero['points'], hero['hp'][1], hero['stats'][2]), (4, 1105, 26))
        outs = jnl(rows, 'frame_out')
        self.assertEqual(len(outs), 1)
        self.assertEqual((outs[0]['send'], outs[0]['encrypted']), ('ok', 0))   # Send(0, 0): as built
        self.assertEqual(unxor(hexbytes(outs[0]['bytes']), 2), bytes([0xc1, 0x05, 0x01, 0x00, 0x02]))

    def test_two_seeds_two_reproducible_journals(self):
        scn = write_scenario(self.dir / 's.scn', HEAD + ''.join('at %d progress kill random %d\n' % (t, t)
                                                                 for t in range(2, 30, 3)))
        def journal(seed, name):
            path = self.dir / name
            r, _ = run_tool('fixture', scn, '--seed', seed, '--ticks', 40, '--journal', path, '--quiet')
            self.assertEqual(r.returncode, 0, r.stderr)
            return path.read_bytes()
        a1, a2, b = journal(7, 'a1.mujnl'), journal(7, 'a2.mujnl'), journal(8, 'b.mujnl')
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, b)
        self.assertEqual(a1[:8], b'MUJNL\x00\x01\x00')

    def test_tcp_round_trip_over_the_sockets_transport(self):
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        scn = write_scenario(self.dir / 't.scn', 'endpoint game 127.0.0.1:%d\nuse progress latency=1\n'
                             'join world=0 tile=1,1 class=0x01 level=1 name=Tcp\n'
                             'at 2 progress join\nat 4 progress levelup\nexpect hero.level = 2\n'
                             'expect unbound = 0\n' % port)
        env = dict(os.environ)
        env.pop('MU_AGENT', None)
        env['MU_CLIENT_LOCK_PATH'] = str(self.dir / 'client.lock')
        env['MU_CLIENT_PROCESS_NAMES'] = 'mu-test-%s.exe' % uuid.uuid4().hex[:12]
        server = subprocess.Popen([str(TOOL), 'serve', str(scn), '--port', str(port), '--seconds', '20'],
                                  stdout=subprocess.PIPE, text=True)
        try:
            self.assertIn('fixture_listening', server.stdout.readline())
            r, rows = run_tool('connect', scn, '--to', '127.0.0.1:%d' % port, '--ticks', 40, env=env)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr)
            transport = first(rows, 'transport')
            self.assertEqual((transport['kind'], transport['links_opened'], transport['links_refused']),
                             ('sockets', 1, 0))
            self.assertGreater(transport['bytes_in'], 0)
            self.assertEqual(first(rows, 'hero')['level'], 2)
            self.assertEqual({(f['opcode'], f['sub']) for f in jnl(rows, 'frame_in')},
                             {(0x55, 0x57), (0x55, 0x94), (0xA0, 0x06)})
            out, _ = server.communicate(timeout=20)
            self.assertEqual(server.returncode, 0, out)
        finally:
            if server.poll() is None:
                server.kill()
                server.wait()
            server.stdout.close()

    def test_connect_refuses_a_non_loopback_endpoint(self):
        scn = write_scenario(self.dir / 'n.scn', HEAD)
        r, rows = run_tool('connect', scn, '--to', '192.0.2.1:44405', '--ticks', 2)
        self.assertEqual(r.returncode, 2)
        self.assertIn('loopback', r.stderr)
        self.assertFalse([x for x in rows if 'transport' in x])


if __name__ == '__main__':
    unittest.main()
