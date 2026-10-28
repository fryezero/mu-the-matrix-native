"""Party session feed, builder output and retained state without any live client."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_session_support import NATIVE, SCENARIOS, jnl, run_tool

class Party(unittest.TestCase):
    def test_fixture_routes_and_builder_requests(self):
        r, rows = run_tool('fixture', SCENARIOS / 'party-members.scn')
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout[-1200:])
        frames = jnl(rows, 'frame_in')
        self.assertEqual({r['opcode'] for r in frames}, {0x40,0x41,0x42,0x43,0x44})
        self.assertTrue(all(r['result']=='done' for r in frames))
        out = jnl(rows,'frame_out')
        self.assertEqual([r['bytes'] for r in out], ['c1 06 86 01 02 00', 'c1 0f c3 00 48 65 72 6f 00 00 00 00 00 00 00', 'c1 05 3a 02 00'])
        self.assertEqual([r['send'] for r in out], ['needs_crypto','ok','needs_crypto'])

    def test_atomicity_identity_detached_updates_and_independent_cursors(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);scenario=d/'party.scn';exe=d/'host'
            scenario.write_text('endpoint game 127.0.0.1:55907\nuse party hero=Hero peers=Aeris,Kyra\nat 1 party join 0\n'
                'at 2 send game c2 00 05 42 06\n' # invalid count
                'at 3 send game c1 05 44 01 20\n' # truncated update
                'at 4 send game c1 04 43 00\n' # truncated clear
                'at 5 party invite 4660\nat 6 party invite 512\n'
                'at 7 send game c1 11 44 01 ff 3d 48 65 72 6f 00 00 00 00 00 00 00\n'
                'at 8 party result 13\nat 9 party clear\n')
            subprocess.run(['make','-C',str(NATIVE),'build/mu-session'],check=True,capture_output=True)
            subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE/'build/gen'),'-I',str(NATIVE/'session'),
                str(NATIVE/'tests/party_session_host.c'),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),
                *(['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation'] if sys.platform=='darwin' else []),'-lm','-o',str(exe)],check=True,capture_output=True)
            r=subprocess.run([str(exe),str(scenario)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_empty_and_wrong_head_packets_and_decline_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'empty.scn'
            p.write_text('endpoint game 127.0.0.1:55907\njoin world=0 tile=120,120 class=1 level=10 name=Hero slot=0\n'
                'at 1 send game c2 00 05 42 00\n'
                'at 2 send game c1 04 44 00\n'
                'at 3 send game c1 05 42 00 00\n'
                'at 4 send game c2 00 05 43 00\n'
                'at 5 send game c1 05 40 ab cd\n'
                'at 6 client submit party_answer 0\n'
                'expect party.count = 0\nexpect party.key = 43981\nexpect party.pending = 0\n'
                'expect unbound = 0\nexpect undecodable = 0\nexpect unsent = 1\n')
            r,rows=run_tool('fixture',p)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual([x['result'] for x in jnl(rows,'frame_in')],['done','done','ignored','ignored','done'])
            self.assertEqual(jnl(rows,'frame_out')[0]['bytes'],'c1 06 86 00 ab cd')

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned instructions')
class Private(unittest.TestCase):
    def test_original_party_adapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'party.json'
            subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_session_party.py'),'--cases','40','--mutants','--output',str(out)],check=True,capture_output=True)
            r=json.loads(out.read_text())
            self.assertEqual(r['mismatches'],0)
            self.assertEqual((r['total'],len(r['mutants_caught'])),(200,5))
