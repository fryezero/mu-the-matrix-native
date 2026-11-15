"""Authored remote buff visibility and the fifth proved seat interval."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
PRIVATE=os.environ.get('MU_RECOVERY_INTEGRATION')=='1' and os.environ.get('MU_GAME_ROOT')
@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and pinned instructions')
class Original(unittest.TestCase):
    def test_instruction_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_visibility.py'),'--output',str(out)],check=True,capture_output=True,cwd=ROOT)
            r=json.loads(out.read_text())
        self.assertTrue(r['all_equal'],r);self.assertEqual(r['cases'],417)
@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and native world assets')
class World(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'world'],check=True,capture_output=True,cwd=ROOT)
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.binary=cls.root/'mu-world';shutil.copy2(ROOT/'native/build/mu-world',cls.binary)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def render(self,*args,**kwargs):
        from native.tests import test_muun_riding as riding
        return riding.World.render(self,*args,**kwargs)
    def test_remote_raw_groups_and_predicate_on_both_backends(self):
        from PIL import ImageChops
        for backend in ('gl','soft'):
            shown,last,_=self.render('shown'+backend,backend=backend,MU_MUUN_BUFF18_FIXTURE='1',MU_MUUN_REMOTE_BUFF_FIXTURE='9,6,1')
            self.assertEqual(last('muun_mount')['draws'],8)
            self.assertEqual(last('muun_buff_hidden')['hidden_draws'],0)
            hidden,last,_=self.render('hidden'+backend,backend=backend,MU_MUUN_BUFF18_FIXTURE='1',MU_MUUN_REMOTE_BUFF_FIXTURE='9,0,1')
            self.assertEqual(last('muun_mount')['draws'],0)
            self.assertEqual(last('muun_buff_hidden')['hidden_draws'],8)
            self.assertEqual(last('muun_style')['refused_modes'],0)
            no_gate,last,_=self.render('no-gate'+backend,backend=backend,MU_MUUN_BUFF18_FIXTURE='1',MU_MUUN_REMOTE_BUFF_FIXTURE='9,0,0')
            self.assertEqual(last('muun_mount')['draws'],8)
            self.assertIsNone(ImageChops.difference(shown,no_gate).getbbox())
            self.assertIsNotNone(ImageChops.difference(shown,hidden).getbbox())
    def test_authored_fifth_seat_interval_has_a_real_pose_and_restores_hero(self):
        from PIL import ImageChops
        for backend in ('gl','soft'):
            normal,_,_=self.render('normal'+backend,backend=backend,MU_MUUN_RIDER_FIXTURE='1')
            posed,last,_=self.render('pose280'+backend,backend=backend,MU_MUUN_RIDER_FIXTURE='1',MU_MUUN_RIDER_ACTION_FIXTURE='280')
            r=last('muun_rider')
            self.assertEqual((r['muun_rider'],r['draws'],r['restored'],r['refused']),(280,8,8,0),r)
            self.assertEqual(last('muun_mount')['refused_actions'],0)
            self.assertEqual(last('muun_mount')['refused_bones'],0)
            self.assertIsNotNone(ImageChops.difference(normal,posed).getbbox())
    def test_raw_flags_need_their_explicit_fixture_context(self):
        for flags in ({'MU_MUUN_REMOTE_BUFF_FIXTURE':'9,0,1'},
                      {'MU_MUUN_REMOTE_BUFF_FIXTURE':'256,0,1','MU_MUUN_BUFF18_FIXTURE':'1'},
                      {'MU_MUUN_RIDER_ACTION_FIXTURE':'280'},
                      {'MU_MUUN_RIDER_FIXTURE':'1','MU_MUUN_RIDER_ACTION_FIXTURE':'0'}):
            env={k:v for k,v in os.environ.items() if not k.startswith('MU_MUUN_')}
            env.update(MU_MUUN_FIXTURE='16',MU_MUUN_MOUNT_FIXTURE='1',MU_SETTINGS_DIR=str(self.root/'settings'),**flags)
            p=subprocess.run([str(self.binary),'--game-root',os.environ['MU_GAME_ROOT'],'--headless','--frames','1',
                '--no-audio','--out-dir',str(self.root/'invalid')],env=env,cwd=ROOT,capture_output=True)
            self.assertNotEqual(p.returncode,0)
if __name__=='__main__':unittest.main()
