"""SESSION-VIEWPORT-001: records through the real loopback, projection and lease."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

NATIVE=Path(__file__).resolve().parents[1]
ROOT=NATIVE.parent
SCENARIO=NATIVE/'fixture/scenarios/characters-viewport.scn'

class Characters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.host=Path(cls.tmp.name)/'characters-host'
        subprocess.run(['make','-C',str(NATIVE),'build/mu-session'],check=True,capture_output=True)
        subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE/'session'),
                        '-I',str(NATIVE/'build/gen'),str(NATIVE/'tests/characters_host.c'),
                        str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),'-lm',
                        '-o',str(cls.host)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def drive(self,scenario=SCENARIO,*args):
        r=subprocess.run([str(self.host),str(scenario),*args],capture_output=True,text=True)
        return r,[json.loads(x) for x in r.stdout.splitlines() if x.startswith('{')]

    def test_projection_every_mapped_member_and_unknown_gaps(self):
        r,rows=self.drive('projection')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(rows[0]['projection_cases'],100)
        self.assertGreater(rows[0]['fields'],80)

    def test_table_capacity_and_first_free_reuse(self):
        def viewport(key):
            b=bytearray(73)
            b[:5]=bytes([0xc2,0,73,0x12,1])
            b[5:7]=(0x8000|key).to_bytes(2,'big')
            b[5+0x26:5+0x2f]=bytes([255])*9
            b[5+0x30:5+0x32]=bytes([255])*2
            b[5+0x41]=255
            return b.hex(' ')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'capacity.scn'
            lines=['endpoint game 127.0.0.1:55902']
            lines += [f'at {i} send game {viewport(i)}' for i in range(1,402)]
            lines += ['at 402 send game c1 06 14 01 00 06',f'at 403 send game {viewport(1000)}']
            p.write_text('\n'.join(lines)+'\n')
            r,rows=self.drive(p,'capacity')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(rows[0],{'capacity':400,'overflow_ignored':1,'reused_slot':5,'generation':2})

    def test_real_frames_update_one_table_and_helpers(self):
        r,rows=self.drive()
        self.assertEqual(r.returncode,0,r.stderr)
        def record(tick): return next(x for x in rows if x.get('tick')==tick and 'key' in x)
        self.assertEqual(record(1)['key'],0x200)
        self.assertEqual(record(1)['class'],1)
        self.assertEqual(record(1)['helper_slot'],0x24e7)
        self.assertEqual(record(3)['x'],126)  # no world: path failure uses the client's teleport
        self.assertEqual(record(4)['store'],1)
        self.assertEqual(record(5)['dead'],1)
        self.assertEqual(next(x for x in rows if x.get('tick')==6 and 'count' in x)['count'],0)

    def test_replicated_write_during_lease_aborts(self):
        r,_=self.drive(SCENARIO,'bad-lease')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('replicated zone',r.stderr)

    def test_truncated_batch_is_atomic_and_unknown_keys_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'malformed.scn'
            p.write_text('endpoint game 127.0.0.1:55902\n'
                'at 1 send game c2 00 05 12 01\n'
                'at 2 send game c1 08 3d 02 00 7e 78 30\n')
            r,rows=self.drive(p)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue(all(x['count']==0 and x['rev']==0 for x in rows if 'count' in x))

    def test_destroy_reuses_first_free_slot_with_new_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'reuse.scn'
            p.write_text('endpoint game 127.0.0.1:55902\nuse characters x=10 y=10\n'
                'at 1 characters player First class=1 at=10,10\n'
                'at 2 send game c1 06 14 01 02 00\n'
                'at 3 characters player Second class=2 at=11,11\n')
            r,rows=self.drive(p)
        self.assertEqual(r.returncode,0,r.stderr)
        first=next(x for x in rows if x.get('key')==0x200)
        second=next(x for x in rows if x.get('key')==0x201)
        self.assertEqual(first['slot'],second['slot'])
        self.assertGreater(second['generation'],first['generation'])

class PrivateViewport(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('MU_RECOVERY_INTEGRATION')=='1', 'private instruction captures')
    def test_original_0122d413(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'viewport.json'
            subprocess.run([__import__('sys').executable,str(ROOT/'scripts/validate_viewport.py'),
                            '--cases','1000','--mutations','--output',str(report)],check=True,capture_output=True)
            data=json.loads(report.read_text())
        self.assertEqual(data['mismatches'],0)
        self.assertEqual(data['handler_cases'],1000)
        self.assertEqual(data['mutants']['caught'],8)
