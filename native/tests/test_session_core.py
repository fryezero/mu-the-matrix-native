"""The session core (SESSION-CORE-001), through mu-session and the in-process fixture (FIXTURE-001).

Portable, synthetic scenarios written here (no game data):
  * the product library carries no seed and no fixture symbol; the dev library has both;
  * every intent kind has a submit route, every hero route an apply function (mu-session routes);
  * the world-change barrier: a respawn to another map is applied, then nothing more applies (pumping
    while waiting applies nothing) until the matching world attaches; attaching another world does not
    release it, attaching the same world again is a no-op, and a respawn in the same world moves the
    hero through the port instead of raising the barrier;
  * cue loss: a reader that falls more than 1024 cues behind loses the oldest and is told how many;
  * the lease audit (MU_SESSION_AUDIT) aborts on a write outside the motion zone during a lease, names
    the field, and journals it first; motion-zone writes pass;
  * plaintext 0x16 yields the client's own C1 4D 02 00 16 report, built by the verified builder and
    marked for the encrypted send (Send(1, 0)), unsent until the C3 wrap exists.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_session_support import NATIVE, SCENARIOS, TOOL, first, hexbytes, jnl, run_tool, unxor, write_scenario  # noqa: E402

PRODUCT = NATIVE / 'build/libmusession_product.a'
DEV = NATIVE / 'build/libmusession.a'
HEAD = 'endpoint game 127.0.0.1:55901\nuse progress class=0x01 level=1 latency=0\n' \
       'join world=0 tile=10,10 angle=0 class=0x01 level=1 name=Core slot=0\n'


def symbols(lib):
    nm = shutil.which('nm')
    out = subprocess.run([nm, '-g', str(lib)], capture_output=True, text=True).stdout
    return {line.split()[-1].lstrip('_') for line in out.splitlines() if len(line.split()) >= 2}


@unittest.skipUnless(TOOL.exists(), 'mu-session not built (make -C native)')
class SessionCore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def scenario(self, body):
        return write_scenario(self.dir / 'case.scn', HEAD + body)

    @unittest.skipUnless(shutil.which('nm'), 'nm not available')
    def test_product_library_has_no_seed_or_fixture(self):
        prod, dev = symbols(PRODUCT), symbols(DEV)
        self.assertIn('mu_session_open', prod)
        self.assertIn('mu_session_pump', prod)
        self.assertNotIn('mu_session_open_seeded', prod)
        self.assertNotIn('mu_dom_hero_seed', prod)
        self.assertFalse([s for s in prod if s.startswith('mu_fixture') or s.startswith('mu_fx_')])
        self.assertIn('mu_session_open_seeded', dev)
        self.assertIn('mu_fixture_open', dev)

    def test_every_intent_kind_is_routed(self):
        r, rows = run_tool('routes')
        self.assertEqual(r.returncode, 0, r.stderr)
        intents = [row['intent'] for row in rows if 'intent' in row]
        self.assertEqual({i['name'] for i in intents}, {'add_stat', 'master_point'})
        for i in intents:
            self.assertIsNotNone(i['submit'], i)
        routes = [row['route'] for row in rows if 'route' in row]
        bound = {(x['opcode'], x['sub']): x['apply'] for x in routes if x['apply']}
        self.assertEqual(sum(name.startswith('hero_') for name in bound.values()), 8)

    def test_world_change_barrier_and_attach_idempotency(self):
        scn = self.scenario('at 3 progress respawn map=2 x=20 y=30 dir=3 money=7\n'
                            'at 4 progress levelup\nat 5 progress levelup\n'
                            'at 8 client attach 5\n'          # another world: still waiting
                            'at 12 client attach 2\n'         # the world the barrier waits for: both level ups apply
                            'at 12 client attach 2\n'         # the same world again: no-op
                            'at 14 client attach 2\n'
                            'at 20 progress respawn map=2 x=1 y=2 dir=1 money=9\n'   # same world: no barrier
                            'expect waiting = -1\nexpect hero.level = 3\nexpect place.world = 2\n'
                            'expect stub.placements = 1\nexpect money = 9\n')
        r, rows = run_tool('fixture', scn, '--ticks', 30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        frames = jnl(rows, 'frame_in')
        respawns = [f for f in frames if f['opcode'] == 0xA0 and f['sub'] == 0x30]
        self.assertEqual([(f['tick'], f['result']) for f in respawns], [(3, 'world_change'), (20, 'done')])
        levelups = [f for f in frames if f['opcode'] == 0xA0 and f['sub'] == 0x06]
        self.assertEqual([f['tick'] for f in levelups], [12, 12])   # held from ticks 4 and 5
        self.assertFalse([f for f in frames if 3 < f['tick'] < 12])  # pumping while waiting applied nothing
        events = [e['text'] for e in jnl(rows, 'event')]
        self.assertEqual(events.count('barrier: waiting for world 2'), 1)
        self.assertEqual(events.count('barrier: released'), 1)
        self.assertIn('attach world 5', events)
        self.assertEqual(events.count('attach world 2'), 1)          # the repeats were no-ops

    def test_cue_loss_is_reported(self):
        body = ''.join('at %d progress levelup\n' % t for t in range(2, 62)) + 'at 70 client cues\n'
        r, rows = run_tool('fixture', self.scenario(body), '--ticks', 72)
        self.assertEqual(r.returncode, 0, r.stderr)
        cues = first(rows, 'cues')
        total = first(rows, 'summary')['cues']
        self.assertGreater(total, 1024)
        self.assertEqual(cues['lost_main'], 0)                      # the per-tick reader keeps up
        self.assertEqual(cues['late_read'], 1024)                   # the ring's size
        self.assertEqual(cues['late_lost'], total - 1024)
        self.assertEqual(cues['level_up'], 60)

    def test_lease_audit_catches_a_replicated_write(self):
        journal = self.dir / 'audit.mujnl'
        r, rows = run_tool('fixture', self.scenario('at 2 progress join\nat 5 client lease write 0x12 9\n'),
                           '--ticks', 8, '--journal', journal)
        self.assertLess(r.returncode, 0)                             # abort()
        self.assertIn('lease audit: hero.record+0x012 (class_byte) changed during the lease', r.stderr)
        d, drows = run_tool('journal', journal)
        self.assertEqual(d.returncode, 0, d.stderr)
        self.assertTrue([e for e in jnl(drows, 'event') if e['text'].startswith('lease audit: hero.record+0x012')])
        # just past the motion zone is replicated again
        r, _ = run_tool('fixture', self.scenario('at 5 client lease write 0x188 1\n'), '--ticks', 8)
        self.assertLess(r.returncode, 0)
        self.assertIn('hero.record+0x188', r.stderr)
        # the motion zone itself (the tile, +0x180..+0x187) may be written under the lease
        r, _ = run_tool('fixture', self.scenario('at 5 client lease write 0x180 7\nat 6 client lease write 0x187 1\n'),
                        '--ticks', 8)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_plaintext_kill_exp_yields_the_report(self):
        r, rows = run_tool('fixture', SCENARIOS / 'hero-progress.scn')
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr)
        records = [x for x in rows if x.get('jnl') in ('frame_in', 'frame_out')]
        kills = [i for i, x in enumerate(records) if x['jnl'] == 'frame_in' and x['opcode'] == 0x16]
        self.assertEqual(len(kills), 2)
        for i in kills:
            f, out = records[i], records[i + 1]
            self.assertEqual((f['encrypted'], f['result'], f['apply']), (0, 'ignored', 'hero_kill_exp'))
            self.assertEqual(out['jnl'], 'frame_out')
            self.assertEqual(out['encrypted'], 1)                    # Send(1, 0): the client's C3 path
            self.assertEqual(out['send'], 'needs_crypto')            # no wrap before NET-DECODE-001
            wire = hexbytes(out['bytes'])
            self.assertEqual(unxor(wire, 2), bytes([0xc1, 0x06, 0x4d, 0x02, 0x00, 0x16]))
        status = first(rows, 'status')
        self.assertEqual(status['unsent'], 2)
        self.assertEqual(status['protocol_state'], 0x33)
        # the refused frames changed no hero state: the experience only ever moved through A0 06
        self.assertEqual(first(rows, 'hero')['exp'], 0)


if __name__ == '__main__':
    unittest.main()
