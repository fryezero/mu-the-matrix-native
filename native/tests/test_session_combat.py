"""SESSION-COMBAT-001: authoritative frames, plain requests, refusal and event loss."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_session_support import NATIVE, SCENARIOS, first, hexbytes, jnl, run_tool
ROOT=NATIVE.parent


class Combat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.host=Path(cls.tmp.name)/'combat-host'
        subprocess.run(['make','-C',str(NATIVE),'build/mu-session'],check=True,capture_output=True)
        subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE/'session'),'-I',str(NATIVE/'build/gen'),
                        str(NATIVE/'tests/combat_host.c'),str(NATIVE/'build/libmusession.a'),
                        str(NATIVE/'build/libmunative.a'),*(['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation'] if sys.platform=='darwin' else []),'-lm','-o',str(cls.host)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def drive(self,body):
        p=Path(self.tmp.name)/'case.scn'
        p.write_text('endpoint game 127.0.0.1:55904\nuse monsters\nat 1 monsters actor 3 121 120 1\n'+body)
        r=subprocess.run([str(self.host),str(p)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        return [json.loads(x) for x in r.stdout.splitlines()]

    def test_fight_frames_and_plaintext_attack_encrypted_cast_unsent(self):
        r,rows=run_tool('fixture',SCENARIOS/'combat-fight.scn')
        self.assertEqual(r.returncode,0,r.stdout[-3000:]+r.stderr)
        frames=jnl(rows,'frame_in')
        self.assertEqual([x['opcode'] for x in frames],[0x13,0xc5,0xf3,0x17,0x16,0x20,0xa4])
        self.assertEqual([x['result'] for x in frames],['done']*4+['ignored','done','done'])
        out=jnl(rows,'frame_out')
        self.assertEqual(hexbytes(out[0]['bytes']),bytes.fromhex('c1 07 43 04 00 78 01'))
        cast=next(x for x in out if hexbytes(x['bytes'])[2]==0xd7)
        self.assertEqual((cast['send'],cast['encrypted']),('needs_crypto',1))
        self.assertEqual(hexbytes(cast['bytes']),bytes.fromhex('c1 06 d7 79 78 11'))
        self.assertEqual(first(rows,'status')['unsent'],2)

    def test_damage_never_implies_death_and_malformed_frames_are_atomic(self):
        damage='c1 18 f3 84 00 00 00 00 ff ff 00 00 00 80 00 00 00 00 00 00 00 00 00 00'
        rows=self.drive(f'at 2 send game {damage}\nat 3 send game c1 05 17 04 00\n'
                        'at 4 send game c1 09 c5 04 00 01 77 ff ff\n')
        self.assertEqual(rows[0]['dead'],0)
        self.assertEqual((rows[-1]['damage'],rows[-1]['die'],rows[-1]['action']),(1,0,0))
        rows=self.drive('at 2 send game c1 09 17 04 00 00 28 00 00\n')
        self.assertEqual((rows[0]['dead'],rows[0]['movement']),(1,0))

    def test_both_action_cases_face_known_target_or_use_packet_direction(self):
        for action in (0x78,0x79):
            for target,angle in (('ff ff',90.0),('00 01',270.0)):
                rows=self.drive(f'at 2 send game c1 09 c5 04 00 03 {action:02x} {target}\n')
                self.assertEqual((rows[0]['movement'],rows[0]['angle'],rows[0]['x'],rows[0]['y']),
                                 (0,angle,12150.0,12050.0))
                self.assertEqual(rows[-1]['action'],1)

    def test_late_event_reader_reports_loss_and_keeps_sequence_order(self):
        body=''.join(f'at {i+2} send game c1 09 c5 04 00 01 78 ff ff\n' for i in range(140))
        row=self.drive(body)[-1]
        self.assertEqual((row['events'],row['lost'],row['cursor'],row['first_seq']),(128,12,140,12))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned instructions')
class Private(unittest.TestCase):
    def test_original_bodies_builders_and_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_session_combat.py'),'--cases','40',
                            '--mutants','--output',str(report)],check=True,capture_output=True)
            r=json.loads(report.read_text())
        self.assertEqual(r['total'],240)
        self.assertEqual(r['mismatches'],0)
        self.assertEqual(len(r['mutants_caught']),6)
