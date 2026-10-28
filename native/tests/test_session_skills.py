"""SESSION-SKILL-001: session ownership, plaintext fixture and headless skills."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_session_support import NATIVE,SCENARIOS,run_tool,first,jnl,hexbytes
ROOT=NATIVE.parent
TABLES=SCENARIOS/'skills-tables'

class Skills(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.directory=Path(cls.tmp.name);cls.host=cls.directory/'skills-host'
        subprocess.run(['make','-C',str(NATIVE),'build/mu-session','build/mu-walk'],check=True,capture_output=True)
        libs=['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation'] if sys.platform=='darwin' else []
        subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE/'session'),'-I',str(NATIVE/'build/gen'),
                        str(NATIVE/'tests/skills_host.c'),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),
                        *libs,'-lm','-o',str(cls.host)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_scenario_and_unsent_cast(self):
        p,rows=run_tool('fixture',SCENARIOS/'skills-state.scn','--ticks',15)
        self.assertEqual(p.returncode,0,p.stdout[-3000:]+p.stderr)
        report=first(rows,'summary')
        self.assertEqual((report['frames_in'],report['unbound_frames'],report['undecodable_frames'],report['unsent_frames']),(13,0,0,1))
        cast=next(x for x in jnl(rows,'frame_out') if hexbytes(x['bytes'])[2]==0xd7)
        self.assertEqual((cast['send'],cast['encrypted']),('needs_crypto',1))
        self.assertEqual(hexbytes(cast['bytes']),bytes.fromhex('c1 06 d7 79 78 13'))
        self.assertTrue(all(x['pass'] for x in rows if 'expect' in x))
    def scenario(self,extra=''):
        path=self.directory/'host.scn'
        path.write_text('endpoint game 127.0.0.1:55905\nuse skills\n'+
                        f'at 1 skills data {TABLES}\nat 1 skills file {TABLES}/demo.txt\nat 2 skills login 129 30\n'+extra)
        return path
    def test_detached_answers_and_rebind_preserve_the_book(self):
        path=self.scenario('at 5 skills learn 330\nat 6 skills forget 22\nat 8 send game c1 06 7e 03 17 00\n')
        p=subprocess.run([str(self.host),str(path),str(TABLES)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        row=json.loads(p.stdout)
        self.assertEqual((row['same'],row['count'],row['key'],row['points'],row['unbound']),(1,7,330,23,0))
    def test_lease_catches_a_learned_skill_write(self):
        p=subprocess.run([str(self.host),str(self.scenario()),str(TABLES),'poison'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('lease audit: skills.hero',p.stderr)
    def test_short_list_and_keys_do_not_replace_state(self):
        path=self.scenario('at 4 send game c1 07 a0 20 00 02 00\nat 5 send game c1 05 a0 03 00\n')
        p=subprocess.run([str(self.host),str(path),str(TABLES)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        row=json.loads(p.stdout);self.assertEqual((row['count'],row['first'],row['key']),(6,19,41))
    def test_headless_world_has_skill_state(self):
        from test_native_world import write_open_world
        root=self.directory/'world';write_open_world(root)
        p=subprocess.run([str(NATIVE/'build/mu-walk'),'--game-root',str(root),'--headless','--backend','soft','--out-dir',str(self.directory/'renders'),'--world','0','--tile','120,120',
                          '--frames','4','--no-audio','--no-particles','--no-items',
                          '--no-players'],capture_output=True,text=True,env={**os.environ,'MU_LANG_DIR':str(TABLES)})
        self.assertEqual(p.returncode,0,p.stderr)
        rows=[json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
        self.assertGreater(next(r['session_skills']['learned'] for r in rows if 'session_skills' in r),0)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned instructions')
class Private(unittest.TestCase):
    def test_save_builder_and_mutants(self):
        p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_session_skills.py'),'--cases','40','--mutants'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        row=json.loads(p.stdout);self.assertEqual((row['total'],row['mismatches'],len(row['mutants_caught'])),(80,0,3))
