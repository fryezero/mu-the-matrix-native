"""Kind-1 secondary skeleton, explicit selection gates and base-owner lifetime."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import native_fixtures as nf
from test_native_data import item_file,item_record
PRIVATE=os.environ.get('MU_RECOVERY_INTEGRATION')=='1' and os.environ.get('MU_GAME_ROOT')

class Host(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/muun-mount-host'],check=True,capture_output=True)
    def run_host(self,root,lang,code):
        p=subprocess.run([str(ROOT/'native/build/muun-mount-host'),str(root),str(lang),str(code)],
                         check=True,capture_output=True,text=True,cwd=ROOT)
        r=json.loads(p.stdout)
        for key in ('poses','exact','controls','bones','retired'):self.assertEqual(r[key],1,(key,r))
        self.assertEqual(r['refused_bones'],0,r)
        return r

class Fixture(Host):
    def test_two_skeletons_and_terminal_base_lease(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for d in ('Data/Local','Data/Item','Data/Skill','lang'):(root/d).mkdir(parents=True)
            layout=nf.synthetic_layout(actions=5)
            (root/'Data/Item/base.bmd').write_bytes(layout)
            mount=bytearray(layout);mount[4:36]=nf.name32('WolfA.SMD')
            mount=mount.replace(nf.name32('bone1'),nf.name32('Bip01 Spine1'))
            (root/'Data/Skill/wolfpetVehicle.bmd').write_bytes(mount)
            (root/'Data/Local/Item.bmd').write_bytes(item_file([item_record(0x20e7,b'Data\\Item\\',b'base.bmd',b'Demo mount')]))
            r=bytearray(612);struct.pack_into('<ii',r,0,16,0x20e7);r[8]=1;r[9:18]=b'WolfA.SMD'
            struct.pack_into('<4f',r,0x110,.65,50,0,20);struct.pack_into('<5f',r,0x238,*([.25]*5));r[0x258]=1
            (root/'Data/Local/MuunRenderInfo.bmd').write_bytes(item_file([r]))
            row=self.run_host(root,root/'lang',16)
            self.assertEqual((row['model'],row['bone']),(0x5cb,1))

@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and installed Muun models')
class Installed(Host):
    def test_all_eight_kind1_secondary_models(self):
        rows=[self.run_host(os.environ['MU_GAME_ROOT'],Path(os.environ['MU_NATIVE_DATA_DIR'])/'lang',code)
              for code in (16,17,100,101,102,103,104,105)]
        self.assertEqual([r['model'] for r in rows],list(range(0x5cb,0x5d3)))
        self.assertEqual([r['bone'] for r in rows],[4]*8)
        self.assertTrue(all(r['missing']==0 for r in rows),rows)
        print('Kind-1 summary:',json.dumps(rows,sort_keys=True))

@unittest.skipUnless(PRIVATE,'requires pinned instructions and installed kind-1 mesh records')
class BaseMeshes(unittest.TestCase):
    def test_kind1_base_mesh_callers(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import validate_muun_passes as vp
        records=vp.decoded('MuunRenderInfo.bmd');meshes=vp.decoded('MuunMeshInfo.bmd')
        counts={}
        def samples(count,installed):
            for code in (16,17,100,101,102,103,104,105):
                r=next(x for x in records if struct.unpack_from('<i',x)[0]==code)
                self.assertEqual(r[8],1)
                item=struct.unpack_from('<i',r,4)[0]
                rows=[x for x in meshes if struct.unpack_from('<i',x)[0]==item]
                counts[code]=len(rows)
                for clock in (0,3141,123456):yield item+0xae6,r[0x258],rows,clock
        text=vp.pins.load_pinned(vp.pins.TEXT.default_str(),vp.pins.TEXT.size,vp.pins.TEXT.sha256,'text')
        data=vp.pins.load_pinned(vp.pins.DATA.default_str(),vp.pins.DATA.size,vp.pins.DATA.sha256,'data')
        with tempfile.TemporaryDirectory() as td, mock.patch.object(vp,'samples',samples):
            rows=vp.compare(vp.build(td,(ROOT/'reconstructed/muun/passes.c').read_text()),vp.vc.Combat(text,data),0,True)
        self.assertTrue(all(r['mismatches']==0 for r in rows.values()),rows)
        self.assertEqual(rows['mesh']['cases'],24)
        self.assertEqual({code:n for code,n in counts.items() if n},{101:3,103:3,105:3})
        print('Kind-1 base mesh comparison:',json.dumps(rows,sort_keys=True))

@unittest.skipUnless(PRIVATE,'requires pinned private client instructions')
class Original(unittest.TestCase):
    def test_original_secondary_callers(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_secondary.py'),'--output',str(p)],
                           check=True,capture_output=True,cwd=ROOT)
            r=json.loads(p.read_text())
        self.assertTrue(r['all_equal'],r)
        self.assertEqual(r['cases'],873)

@unittest.skipUnless(PRIVATE,'requires canonical private-env.sh and GL world renderer')
class World(unittest.TestCase):
    def test_secondary_body_changes_pixels_in_both_backends(self):
        from PIL import Image,ImageChops
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'world'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for backend in ('gl','soft'):
                images=[]
                for enabled in (False,True):
                    env=dict(os.environ,MU_MUUN_FIXTURE='16');env.pop('MU_MUUN_MOUNT_FIXTURE',None)
                    if enabled:env['MU_MUUN_MOUNT_FIXTURE']='1'
                    out=root/(backend+str(enabled))
                    p=subprocess.run([str(ROOT/'native/build/mu-world'),'--game-root',os.environ['MU_GAME_ROOT'],
                        '--world','0','--tile','128,124','--headless','--frames','8','--every','7',
                        '--time-series-every','7','--out-dir',str(out),'--width','640','--height','400',
                        '--backend',backend,'--hero-name','DemoKnight','--no-names','--no-audio','--no-players',
                        '--no-env','--no-items','--no-particles','--no-helpers'],env=env,cwd=ROOT,
                        check=True,capture_output=True,text=True)
                    rows=[json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
                    mounts=[r for r in rows if 'muun_mount' in r]
                    self.assertEqual(bool(mounts),enabled)
                    if enabled:
                        self.assertEqual((mounts[-1]['visible'],mounts[-1]['attached'],mounts[-1]['missing']),(1,1,0),mounts)
                        self.assertGreater(mounts[-1]['draws'],0)
                    images.append(Image.open(out/'frame-0007.png').convert('RGB'))
                self.assertIsNotNone(ImageChops.difference(*images).getbbox())

if __name__=='__main__':unittest.main()
