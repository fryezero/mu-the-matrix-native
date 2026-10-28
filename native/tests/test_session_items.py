"""Ground routes and explicit fixture policy, with no guessed pickup-answer route."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_session_support import NATIVE, SCENARIOS, first, jnl, run_tool
ROOT=NATIVE.parent

class Items(unittest.TestCase):
    def test_detach_rebind_lease_and_slot_999(self):
        with tempfile.TemporaryDirectory() as tmp:
            host=Path(tmp)/'host'
            subprocess.run(['make','-C',str(NATIVE),'build/mu-session'],check=True,capture_output=True)
            subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE/'build/gen'),'-I',str(NATIVE/'session'),
                            str(NATIVE/'tests/items_session_host.c'),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),
                            *(['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation'] if sys.platform=='darwin' else []),'-lm','-o',str(host)],check=True,capture_output=True)
            p=Path(tmp)/'view.scn'
            p.write_text('endpoint game 127.0.0.1:55906\nat 1 send game c2 00 18 20 01 03 e7 78 78 01 00 ff 00 00 00 00 ff ff ff ff ff ff ff ff\nat 3 send game c2 00 07 21 01 03 e7\n')
            r=subprocess.run([str(host),str(p)],capture_output=True,text=True)
            for field in ('live','type','data'):
                bad=subprocess.run([str(host),str(p),field],capture_output=True,text=True)
                self.assertNotEqual(bad.returncode,0,field)
                self.assertIn('replicated zone',bad.stderr)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_walk_drop_pickup_removal_and_despawn(self):
        r,rows=run_tool('fixture',SCENARIOS/'items-ground.scn')
        self.assertEqual(r.returncode,0,r.stderr+r.stdout[-1500:])
        frames=jnl(rows,'frame_in')
        self.assertEqual([x['opcode'] for x in frames],[0x20,0x21,0x20,0x21])
        self.assertEqual([x['apply'] for x in frames],['items_viewport','items_delete']*2)
        self.assertEqual([x['result'] for x in frames],['done']*4)
        out=jnl(rows,'frame_out')
        self.assertEqual(len(out),2)
        self.assertEqual(out[0]['bytes'],'c1 06 a2 79 78 10')
        self.assertEqual((out[1]['send'],out[1]['encrypted']),('needs_crypto',1))
        self.assertEqual(out[1]['bytes'],'c1 05 00 00 00')

    def scenario(self,body,expect):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'items.scn'
            p.write_text('endpoint game 127.0.0.1:55906\njoin world=0 tile=120,120 class=1 level=10 name=Items slot=0\n'+body+'\nexpect unbound = 0\nexpect undecodable = 0\n'+expect)
            r,rows=run_tool('fixture',p)
        self.assertEqual(r.returncode,0,r.stderr+r.stdout[-1500:])
        return rows

    def test_short_packets_atomic_invalid_key_clamps_to_zero(self):
        rows=self.scenario('at 1 send game c2 00 18 20 01 ff ff 78 78 01 00 ff 00 00 00 00 ff ff ff ff ff ff ff ff\n'
                           'at 2 send game c2 00 06 21 02 00\n'
                           'at 3 send game c2 00 05 20 01\n'
                           'at 4 send game c2 00 07 21 01 ff ff\n',
                           'expect items.creates = 1\nexpect items.deletes = 1\nexpect items.live = 0\n')
        self.assertEqual([x['result'] for x in jnl(rows,'frame_in')],['done','ignored','ignored','done'])

    def test_only_one_pending_pickup_and_missing_slot_refused(self):
        rows=self.scenario('at 1 send game c2 00 18 20 01 00 00 78 78 01 00 ff 00 00 00 00 ff ff ff ff ff ff ff ff\n'
                           'at 2 client submit item_pickup 999\nat 3 client submit item_pickup 0\n'
                           'at 4 client submit item_pickup 0\n',
                           'expect unsent = 1\nexpect items.pending = 0\nexpect items.live = 1\n')
        self.assertEqual([x['status'] for x in jnl(rows,'intent')],['refused','not_now','refused'])

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned instructions')
class Private(unittest.TestCase):
    def test_recorded_delete_builder_and_answer_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'items.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_session_items.py'),'--cases','40','--mutants','--output',str(p)],check=True,capture_output=True)
            r=json.loads(p.read_text())
        self.assertEqual((r['total'],r['mismatches'],len(r['mutants_caught'])),(160,0,4))
