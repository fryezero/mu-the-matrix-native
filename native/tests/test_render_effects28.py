"""Fixture-only buff auras: native pixels, expiry, refusal and original comparisons."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native/tests'))
from test_native_combat import write_combat_world
from test_native_particles import ozj_jpeg

class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/mu-walk'],check=True,capture_output=True)
        cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'mu-walk'
        shutil.copy2(ROOT/'native/build/mu-walk',cls.binary)
        cls.root=Path(write_combat_world(Path(cls.tmp.name)/'game'))
        effect=cls.root/'Data/Effect';effect.mkdir(exist_ok=True)
        for name in ['flareBlue.OZJ','Shiny02.OZJ']:(effect/name).write_bytes(ozj_jpeg(32,32))
        cls.placement=Path(cls.tmp.name)/'actors.txt';cls.placement.write_text('actor 3 122 120 0 label DemoTarget\n')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def cast(self,skill,duration='20',frames=32):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,MU_AURA_FIXTURE_TICKS=duration)
            p=subprocess.run([str(self.binary),'--game-root',str(self.root),'--headless',
                '--backend','soft','--no-audio','--no-items','--no-players','--tile','120,120',
                '--placement',str(self.placement),'--combat','--class','2','--combat-script',
                f'2:skill:{skill}:DemoTarget;3:stop','--frames',str(frames),'--every','1',
                '--width','240','--height','160','--out-dir',tmp],env=env,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr[-2000:])
            rows=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
            images=[hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(tmp).glob('*.png'))]
        return rows,images
    def test_both_buffs_draw_expire_and_repeat_without_power_changes(self):
        for skill in [27,28]:
            with self.subTest(skill=skill):
                before,off=self.cast(skill,'0');rows,on=self.cast(skill)
                aura=next(r for r in rows if r.get('aura_fixture'))
                self.assertGreater(aura['requests'],0);self.assertGreater(aura['created'],0)
                self.assertEqual((aura['refused'],aura['live']),(0,0))
                aframes=[r for r in rows if 'aura_frame' in r]
                self.assertTrue(any(r['live'] for r in aframes))
                self.assertEqual((aframes[-1]['live'],aframes[-1]['sprites']),(0,0))
                if skill==28:self.assertTrue(any(r['sprites']>=6 for r in aframes))
                combat=next(r for r in rows if r.get('combat') is True)
                self.assertEqual((combat['hits'],combat['kills'],combat['requests_sent'],combat['requests_unsent']),(0,0,0,1))
                frames=[r for r in rows if 'combat_frame' in r]
                self.assertTrue(all(r['monsters'][0]['hp']==frames[0]['monsters'][0]['hp'] for r in frames))
                self.assertNotEqual(on,off);self.assertEqual(on[0],off[0]);self.assertEqual(on[-1],off[-1])
                _,repeat=self.cast(skill);self.assertEqual(on,repeat)
    def test_absent_or_invalid_fixture_stays_disabled(self):
        for duration in ['0','-1','10001','bad','3oops']:
            rows,_=self.cast(27,duration,4)
            self.assertFalse(any(r.get('aura_fixture') for r in rows))

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/combat')],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects28.py'),'--cases','60',
                '--output',str(output)],check=True,cwd=ROOT,capture_output=True)
            report=json.loads(output.read_text())
        self.assertTrue(report['all_equal']);self.assertEqual(report['cases'],630)
