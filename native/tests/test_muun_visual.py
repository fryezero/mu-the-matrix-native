"""Fixture-only Muun: production models, pose/bone safety and terminal owner leases."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import native_fixtures as nf
from test_native_data import item_file,item_record
from test_native_effect import billboard


def host(root,lang,code=173):
    result=subprocess.run([str(ROOT/'native/build/muun-visual-host'),str(root),str(lang),str(code)],
                          check=True,capture_output=True,text=True)
    return json.loads(result.stdout)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/muun-visual-host'],check=True,capture_output=True)

    def check_controls(self,row):
        self.assertTrue(row['loaded'],row)
        for field in ('matrices','fields','moved','invisible','resumed','foreign','terminal','dead','generation','bone_controls'):
            self.assertEqual(row[field],1,(field,row))


class Fixture(Build):
    def test_model_pose_visibility_and_lifetime(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for d in ('Data/Local','Data/Item','Data/Effect','lang'):(root/d).mkdir(parents=True)
            (root/'Data/Item/FixtureMuun.bmd').write_bytes(nf.synthetic_layout())
            (root/'Data/Local/Item.bmd').write_bytes(item_file([
                item_record(0x2001,b'Data\\Item\\',b'FixtureMuun.bmd',b'Demo companion')]))
            record=bytearray(612)
            struct.pack_into('<ii',record,0,173,0x2001)
            struct.pack_into('<4f',record,0x110,1.25,50,0,20)
            struct.pack_into('<5f',record,0x238,0.25,0.25,0.25,0.25,0.25)
            (root/'Data/Local/MuunRenderInfo.bmd').write_bytes(item_file([record]))
            (root/'Data/Effect/fixture.ein').write_text(json.dumps(billboard()))
            (root/'lang/muuneffects.tsv').write_text(''.join(
                f'173\tData\\\\Effect\\\\fixture.ein\t0\t0\t0\t0\t0\t0\t1\t{bone}\t1\n' for bone in (5,50,3)))
            row=host(root,root/'lang');absent=host(root,root/'lang',174);no_table=host(root,root/'missing')
        self.assertEqual(absent,{'loaded':False,'code':174})
        self.check_controls(row)
        self.assertEqual((row['model'],row['bones'],row['actions']),(0x2ae7,7,3))
        self.assertEqual((row['records'],row['requested'],row['invalid'],row['refused_bones']),(1,3,0,2))
        self.assertEqual(row['updates'],31)
        self.assertTrue(no_table['loaded']);self.assertEqual((no_table['records'],no_table['requested']),(0,0))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1' and os.environ.get('MU_GAME_ROOT'),
                     'requires canonical private-env.sh and installed models/effects')
class Installed(Build):
    def test_existing_codes_on_actual_muun_skeletons(self):
        lang=Path(os.environ['MU_NATIVE_DATA_DIR'])/'lang'
        codes=sorted({int(l.split('\t')[0]) for l in (lang/'muuneffects.tsv').read_text().splitlines() if l and not l.startswith('#')})
        rows=[host(os.environ['MU_GAME_ROOT'],lang,code) for code in codes]
        self.assertEqual(len(rows),15)
        for row in rows:self.check_controls(row);self.assertEqual(row['invalid'],0,row)
        self.assertEqual(sum(r['requested'] for r in rows),16)
        print('Muun installed summary:',json.dumps(rows,sort_keys=True))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1' and os.environ.get('MU_GAME_ROOT'),
                     'requires canonical private-env.sh and native GL world renderer')
class WorldRender(unittest.TestCase):
    def test_attachments_change_pixels_with_original_frustum_units(self):
        from PIL import Image, ImageChops
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/mu-world'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rows=[]
            for name,enabled in [('attached',True),('body',False)]:
                env=dict(os.environ,MU_MUUN_FIXTURE='363')
                if not enabled:
                    env.update(MU_LANG_DIR=str(root/'no-table'),MU_NATIVE_DATA_DIR=str(root/'no-table'))
                result=subprocess.run([str(ROOT/'native/build/mu-world'),'--game-root',os.environ['MU_GAME_ROOT'],
                    '--world','0','--tile','128,124','--headless','--frames','30','--every','29',
                    '--time-series-every','29','--out-dir',str(root/name),'--width','640','--height','400',
                    '--backend','gl','--hero-name','DemoKnight','--no-names','--no-audio','--no-players',
                    '--no-env','--no-items','--no-particles','--no-helpers'],env=env,cwd=ROOT,
                    check=True,capture_output=True,text=True)
                data=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                rows.append([r for r in data if 'muun_fixture' in r][-1])
            self.assertEqual([r['visible'] for r in rows],[1,1],rows)
            self.assertEqual([r['attachments'] for r in rows],[2,0],rows)
            self.assertEqual(rows[0]['updates'],60,rows)
            self.assertGreater(rows[0]['vertices'],0,rows)
            a=Image.open(root/'attached/frame-0029.png').convert('RGB')
            b=Image.open(root/'body/frame-0029.png').convert('RGB')
            self.assertIsNotNone(ImageChops.difference(a,b).getbbox(),rows)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_muun_visual.py'),'--cases','200','--output',str(path)],
                           check=True,capture_output=True)
            report=json.loads(path.read_text())
        self.assertTrue(report['all_equal']);self.assertEqual(report['instruction_cases'],912)


if __name__=='__main__':unittest.main()
