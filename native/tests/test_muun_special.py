"""Special Muun mesh rows: admit individually, retain bone-effect refusals."""
import ctypes as C
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
PRIVATE=os.environ.get('MU_RECOVERY_INTEGRATION')=='1' and os.environ.get('MU_GAME_ROOT')

class Portable(unittest.TestCase):
    def test_persistent_light_and_signed_atlas_boundaries(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import validate_muun_special as vs
        with tempfile.TemporaryDirectory() as td:
            lib=vs.build(td,(ROOT/'reconstructed/muun/special.c').read_text())
            row=bytearray(300);struct.pack_into('<f',row,0x114,.9)
            c8=C.c_float(.5);p=vs.vp.Pass();p.mesh=2;uv=(C.c_float*2)()
            lib.mu_mv_special_pass(0x2b7a,2,bytes(row),.2,0,1,1,C.byref(c8),C.byref(p),uv)
            self.assertEqual(c8.value,0)
            for expected in (.35,.7,.9):
                lib.mu_mv_special_pass(0x2b7a,0,bytes(row),1,0,1,1,C.byref(c8),C.byref(p),uv)
                self.assertEqual(c8.value,C.c_float(expected).value)
            for mesh,clock,expected in ((5,260,(0,0)),(6,260,(.25,.75)),(6,300,(0,0)),(5,-20,(-.25,0))):
                p=vs.vp.Pass();p.mesh=mesh
                lib.mu_mv_special_pass(0x2b8e,0,bytes(row),1,clock,1,1,C.byref(c8),C.byref(p),uv)
                self.assertEqual(tuple(uv),expected)
                self.assertEqual((p.flags,p.blend,p.texture),(0x42,mesh,-1))
            self.assertEqual([lib.mu_mv_special_admit(m,k) for m,k in ((0x2b8d,1),(0x2b8e,2),(0x2b90,4),(0x2b8e,5))],[0,0,0,1])

@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and pinned instructions/models')
class Original(unittest.TestCase):
    def test_instruction_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_special.py'),'--installed','--output',str(out)],
                           check=True,capture_output=True,cwd=ROOT)
            r=json.loads(out.read_text())
        self.assertTrue(r['all_equal'],r);self.assertEqual(r['cases'],452)
        self.assertGreater(r['families']['installed']['cases'],0)
        self.assertGreater(r['families']['ordered']['cases'],0)
        self.assertGreater(r['families']['refusal']['cases'],0)

@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and installed native world assets')
class Installed(unittest.TestCase):
    def test_all_five_row_counts_and_pixels_on_both_backends(self):
        from PIL import Image,ImageChops
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'world','build/muun-visual-host'],check=True,capture_output=True,cwd=ROOT)
        game=Path(os.environ['MU_GAME_ROOT']);lang=Path(os.environ['MU_NATIVE_DATA_DIR'])/'lang'
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);binary=root/'mu-world';shutil.copy2(ROOT/'native/build/mu-world',binary)
            overlay=root/'plain';(overlay/'Data/Local').mkdir(parents=True)
            for child in (game/'Data').iterdir():
                if child.name.lower()!='local':(overlay/'Data'/child.name).symlink_to(child)
            for child in (game/'Data/Local').iterdir():
                if child.name.lower()!='muunmeshinfo.bmd':(overlay/'Data/Local'/child.name).symlink_to(child)
            for code,kept,refused in ((356,3,0),(357,3,1),(375,7,1),(376,8,2),(377,4,1)):
                with self.subTest(code=code):
                    p=subprocess.run([str(ROOT/'native/build/muun-visual-host'),str(game),str(lang),str(code)],
                        check=True,capture_output=True,text=True,cwd=ROOT)
                    r=json.loads(p.stdout)
                    self.assertEqual((r['mesh_passes'],r['refused_meshes']),(kept,refused),r)
                    self.assertTrue(r['loaded'],r)
                    if code==357:
                        # The installed model has meshes 0..2; the table's mesh-3 row remains refused.
                        self.assertEqual(r['meshes'],3,r)
                    for backend in ('gl','soft'):
                        images=[]
                        for enabled,game_root in ((False,overlay),(True,game)):
                            env={k:v for k,v in os.environ.items() if not k.startswith('MU_MUUN_')}
                            env.update(MU_MUUN_FIXTURE=str(code),MU_SETTINGS_DIR=str(root/'settings'))
                            out=root/f'{code}-{backend}-{enabled}'
                            p=subprocess.run([str(binary),'--game-root',str(game_root),'--world','0','--tile','128,124',
                                '--headless','--frames','8','--every','7','--time-series-every','7','--out-dir',str(out),
                                '--width','640','--height','400','--backend',backend,'--hero-name','DemoKnight','--no-names',
                                '--no-audio','--no-players','--no-env','--no-items','--no-particles','--no-helpers'],
                                env=env,check=True,capture_output=True,text=True,cwd=ROOT)
                            rows=[json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
                            r=[r for r in rows if 'muun_fixture' in r][-1]
                            self.assertEqual((r['mesh_passes'],r['refused_meshes']),(kept,refused) if enabled else (0,0),r)
                            self.assertEqual(r['textures_missing'],0,r)
                            images.append(Image.open(out/'frame-0007.png').convert('RGB'))
                        self.assertIsNotNone(ImageChops.difference(*images).getbbox())

if __name__=='__main__':unittest.main()
