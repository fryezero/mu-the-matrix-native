"""0x47a original consumer comparison and authored transition pixel proof."""
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
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_transition.py'),'--output',str(out)],check=True,capture_output=True,cwd=ROOT)
            r=json.loads(out.read_text())
        self.assertTrue(r['all_equal'],r);self.assertEqual(r['cases'],400)
@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and native world assets')
class World(unittest.TestCase):
    def test_transition_creates_draws_and_expires_on_both_backends(self):
        from PIL import Image,ImageChops
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'world'],check=True,capture_output=True,cwd=ROOT)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);binary=root/'mu-world';shutil.copy2(ROOT/'native/build/mu-world',binary)
            for backend in ('gl','soft'):
                images=[]; ends=[]
                for remote,frames in ((False,90),(True,81),(True,90)):
                    env={k:v for k,v in os.environ.items() if not k.startswith('MU_MUUN_')}
                    env.update(MU_MUUN_FIXTURE='16',MU_MUUN_MOUNT_FIXTURE='1',MU_SETTINGS_DIR=str(root/'settings'))
                    if remote:env['MU_MUUN_REMOTE_FIXTURE']='1'
                    out=root/f'{backend}-{remote}-{frames}'
                    p=subprocess.run([str(binary),'--game-root',os.environ['MU_GAME_ROOT'],'--world','0','--tile','128,124',
                        '--headless','--frames',str(frames),'--every','3','--time-series-every','1','--out-dir',str(out),'--width','640','--height','400',
                        '--backend',backend,'--hero-name','DemoKnight','--no-names','--no-audio','--no-players',
                        '--no-env','--no-items','--no-helpers'],env=env,check=True,capture_output=True,text=True,cwd=ROOT)
                    rows=[json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')]
                    r=next((r for r in reversed(rows) if 'muun_transition' in r),{'created':0,'refused':0,'pending':0})
                    self.assertEqual((r['created'],r['refused'],r['pending']),(int(remote),0,0),r)
                    effect_rows=[r for r in rows if 'effect_models' in r]
                    # The detailed effect report is emitted at shutdown, so inspect one run while
                    # the transition is live and another after expiry.
                    if remote and frames==81:
                        self.assertEqual(effect_rows[-1]['effect_models'],1)
                        self.assertEqual(effect_rows[-1]['effects_live'],1)
                    if frames==90:
                        self.assertEqual(effect_rows[-1]['effects_live'],0)
                        images.append(Image.open(out/'frame-0078.png').convert('RGB'))
                        ends.append(Image.open(out/'frame-0089.png').convert('RGB'))
                self.assertIsNotNone(ImageChops.difference(*images).getbbox())
                self.assertIsNone(ImageChops.difference(*ends).getbbox())
if __name__=='__main__':unittest.main()
