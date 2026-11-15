"""Authored rider poses, style flags and counted request refusals."""
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
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_riding.py'),'--output',str(out)],
                           check=True,capture_output=True,cwd=ROOT)
            r=json.loads(out.read_text())
        self.assertTrue(r['all_equal'],r)
        self.assertEqual(r['cases'],890)

@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and installed native world assets')
class World(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'world'],check=True,capture_output=True,cwd=ROOT)
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.binary=cls.root/'mu-world';shutil.copy2(ROOT/'native/build/mu-world',cls.binary)
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def render(self,tag,code=16,backend='gl',frames=8,no_particles=False,**flags):
        env={k:v for k,v in os.environ.items() if not k.startswith('MU_MUUN_')}
        env.update(MU_MUUN_FIXTURE=str(code),MU_MUUN_MOUNT_FIXTURE='1',MU_SETTINGS_DIR=str(self.root/'settings'))
        env.update(flags)
        out=self.root/tag
        p=subprocess.run([str(self.binary),'--game-root',os.environ['MU_GAME_ROOT'],'--world','0','--tile','128,124',
            '--headless','--frames',str(frames),'--every',str(min(frames-1,24)),'--time-series-every',str(min(frames-1,24)),
            '--out-dir',str(out),'--width','640','--height','400','--backend',backend,'--hero-name','DemoKnight',
            '--no-names','--no-audio','--no-players','--no-env','--no-items','--no-helpers',
            *(['--no-particles'] if no_particles else [])],
            env=env,cwd=ROOT,check=True,capture_output=True,text=True)
        rows=[json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
        def last(name):return [r for r in rows if name in r][-1]
        from PIL import Image
        return Image.open(out/f'frame-{frames-1:04d}.png').convert('RGB'),last,rows
    def test_all_eight_mounted_riders_and_logical_pose_restoration(self):
        from PIL import ImageChops
        for code in (16,17,100,101,102,103,104,105):
            with self.subTest(code=code):
                control,_,_=self.render(f'base{code}',code)
                image,last,_=self.render(f'rider{code}',code,MU_MUUN_RIDER_FIXTURE='1')
                r=last('muun_rider');self.assertEqual((r['draws'],r['restored'],r['refused']),(8,8,0),r)
                s=last('muun_style');self.assertEqual(s['particle_requests'],s['particle_created']+s['particle_refused'],s)
                self.assertGreater(s['particle_requests'],0,s)
                self.assertIsNotNone(ImageChops.difference(control,image).getbbox())
    def test_buff_mesh_and_fade_change_pixels_on_both_backends(self):
        from PIL import ImageChops
        for backend in ('gl','soft'):
            base,_,_=self.render('plain'+backend,backend=backend)
            buff,last,_=self.render('buff'+backend,backend=backend,MU_MUUN_BUFF18_FIXTURE='1')
            self.assertEqual((last('muun_style')['mode'],last('muun_style')['refused_modes']),(10,0))
            fade,last,_=self.render('fade'+backend,backend=backend,MU_MUUN_OWNER_KIND_FIXTURE='2')
            self.assertLess(last('muun_style')['alpha'],1.0)
            self.assertIsNotNone(ImageChops.difference(base,buff).getbbox())
            self.assertIsNotNone(ImageChops.difference(base,fade).getbbox())
    def test_remote_expiry_requests_once_and_accounts_for_consumer_result(self):
        _,last,rows=self.render('remote',frames=90,MU_MUUN_REMOTE_FIXTURE='1',MU_MUUN_RIDER_FIXTURE='1')
        r=last('muun_transition');self.assertEqual((r['muun_transition'],r['pending']),(1,0),r)
        self.assertEqual(r['created']+r['refused'],1,r)
        self.assertEqual({r['muun_rider'] for r in rows if 'muun_rider' in r},{38,71,103,315})
        rider=last('muun_rider');self.assertEqual((rider['draws'],rider['restored'],rider['refused']),(90,90,0),rider)
        # Consumer admission belongs to the effect lane. An explicitly unavailable particle system
        # gives a stable refusal control even after that lane adds the 0x47a consumer.
        _,last,_=self.render('remote-refused',frames=90,no_particles=True,MU_MUUN_REMOTE_FIXTURE='1')
        r=last('muun_transition')
        self.assertEqual((r['muun_transition'],r['created'],r['refused'],r['pending']),(1,0,1,0),r)
    def test_rider_requires_mount_fixture(self):
        env=dict(os.environ,MU_MUUN_FIXTURE='16',MU_MUUN_RIDER_FIXTURE='1');env.pop('MU_MUUN_MOUNT_FIXTURE',None)
        p=subprocess.run([str(self.binary),'--game-root',os.environ['MU_GAME_ROOT'],'--headless','--frames','1',
                          '--no-audio','--out-dir',str(self.root/'invalid')],env=env,cwd=ROOT,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn(b'explicit compatible fixture',p.stderr)

if __name__=='__main__':unittest.main()
