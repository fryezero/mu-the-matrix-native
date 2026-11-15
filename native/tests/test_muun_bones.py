"""Verified bone rows, frozen-data census and native request/pixel controls."""
import csv
import io
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
class Census(unittest.TestCase):
    def test_all_initial_appearance_rows_have_explicit_limits(self):
        with (ROOT/'docs/research/muun-appearance-census.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),386);self.assertEqual(len({r['appearance'] for r in rows}),386)
        self.assertTrue(all(r['draws_before_005'] and r['missing_before_005'] for r in rows))
        self.assertEqual(sum(r['slot']=='1' for r in rows),8)
        self.assertEqual(sum(r['draws_before_005']=='refused' for r in rows),7)
@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and pinned instructions/models')
class Original(unittest.TestCase):
    def test_instruction_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_bones.py'),'--installed','--output',str(out)],check=True,capture_output=True,cwd=ROOT)
            r=json.loads(out.read_text())
        self.assertTrue(r['all_equal'],r);self.assertEqual(r['cases'],221)
        self.assertEqual(r['families']['installed']['cases'],12)
        self.assertEqual(r['families']['ordered']['cases'],9)
@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and native world assets')
class World(unittest.TestCase):
    def test_frozen_census_and_retained_missing_assets(self):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/muun-census-host'],check=True,capture_output=True,cwd=ROOT)
        p=subprocess.run([str(ROOT/'native/build/muun-census-host'),os.environ['MU_GAME_ROOT'],
            str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'lang')],check=True,capture_output=True,text=True,cwd=ROOT)
        rows=list(csv.DictReader(io.StringIO(p.stdout)))
        self.assertEqual(len(rows),386);self.assertEqual(sum(r['loaded']=='1' for r in rows),379)
        self.assertEqual(sum(int(r['extra_refused']) for r in rows),9)
        self.assertEqual(sum(int(r['extra_draws']) for r in rows),551)
        self.assertEqual(sum(int(r['attachments']) for r in rows),16)
        absent={r['appearance'] for r in rows if r['loaded']=='0'}
        self.assertEqual(absent,{'58','59','60','61','62','63','193'})
        self.assertEqual(next(r['actions'] for r in rows if r['appearance']=='363'),'3')

    def test_bone_rows_account_for_every_consumer_result_on_both_backends(self):
        from PIL import Image,ImageChops
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'world'],check=True,capture_output=True,cwd=ROOT)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);binary=root/'mu-world';shutil.copy2(ROOT/'native/build/mu-world',binary)
            for code,ops in ((375,3),(376,16),(377,None)):
                for backend in ('gl','soft'):
                    images=[]
                    for particles in (False,True):
                        env={k:v for k,v in os.environ.items() if not k.startswith('MU_MUUN_')}
                        env.update(MU_MUUN_FIXTURE=str(code),MU_SETTINGS_DIR=str(root/'settings'))
                        out=root/f'{code}-{backend}-{particles}'
                        p=subprocess.run([str(binary),'--game-root',os.environ['MU_GAME_ROOT'],'--world','0','--tile','128,124',
                            '--headless','--frames','8','--every','7','--time-series-every','7','--out-dir',str(out),'--width','640','--height','400',
                            '--backend',backend,'--hero-name','DemoKnight','--no-names','--no-audio','--no-players',
                            '--no-env','--no-items','--no-helpers',*(['--no-particles'] if not particles else [])],
                            env=env,check=True,capture_output=True,text=True,cwd=ROOT)
                        rows=[json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')]
                        r=[r for r in rows if 'muun_bone_requests' in r][-1]
                        self.assertEqual(r['muun_bone_requests'],r['created']+r['refused'],r)
                        self.assertEqual(r['invalid_points'],0,r)
                        if ops:self.assertEqual(r['muun_bone_requests'],8*ops,r)
                        else:self.assertGreaterEqual(r['muun_bone_requests'],24,r)
                        if not particles:self.assertEqual(r['created'],0,r)
                        elif code in (376,377):self.assertGreater(r['created'],0,r)
                        images.append(Image.open(out/'frame-0007.png').convert('RGB'))
                    if code in (376,377):self.assertIsNotNone(ImageChops.difference(*images).getbbox())
if __name__=='__main__':unittest.main()
