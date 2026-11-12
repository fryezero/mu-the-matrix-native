"""ITEMS-UI-001: original integer equipment cursor and its native tooltip adapter."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))
import validate_items_ui as validator
import test_native_gfx2 as gfx


class Cursor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = validator.build(Path(cls.tmp.name), validator.HEADER.read_text(), 'cursor')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_independent_truncation_and_half_open_edges(self):
        rect = (C.c_float * 4)(10.9, 20.9, 30.9, 40.9)
        for x, y, want in ((10,20,1),(39,59,1),(40,20,0),(10,60,0),(9,20,0),(10,19,0)):
            self.assertEqual(self.lib.cursor(rect,x,y),want)

    def test_zero_negative_and_wrapped_extents(self):
        for rect in ((10,20,0,30),(10,20,-1,30),(2147483520,0,256,20)):
            self.assertEqual(self.lib.cursor((C.c_float*4)(*rect),int(rect[0]),int(rect[1])),0)

    def test_window_mouse_normalization(self):
        self.assertEqual(self.lib.mouse(21,1366,640),9)
        self.assertEqual(self.lib.mouse(-3,1366,640),0)
        self.assertEqual(self.lib.mouse(2000,1366,640),640)


class EquipmentLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.host,cls.lib = gfx.build_layer_host(cls.dir)
        cls.movies = cls.dir/'movies'
        cls.movies.mkdir()
        for name in ('main','InventoryFrame','InfoPopup','CharacterInfoFrame','chat'):
            (cls.movies/(name+'.swf')).write_bytes(b'')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self,*ops,scale='1'):
        log = self.dir/'log.txt'
        log.write_text('')
        env = {**os.environ,'MUGFX_STUB_LOG':str(log),'MU_GFX_SCALE':scale}
        result = subprocess.run([str(self.host),str(self.movies),str(self.lib),*map(str,ops)],
                                 env=env,capture_output=True,text=True,check=True)
        return result.stdout,log.read_text()

    def test_equipment_hover_tooltip_and_rollout(self):
        # Synthetic slot in movie-local points. Inventory is at (948,20), giving
        # fractional 640x480 arguments before the independent truncations.
        output,log = self.run_host('key',73,'equipment','invoke',1,'-',
                                   'testCall','["EQUIPrequestSlotInfo",10.9,20.9,30.9,40.9,0]',
                                   'move',959,41,'equipdraws','move',1040,100,'equipdraws')
        rows = [json.loads(s) for s in output.splitlines() if s.startswith('{"equipment"')]
        self.assertEqual([row['select'] for row in rows],[1,0])
        self.assertEqual((rows[0]['word'],rows[0]['excellent'],rows[0]['set']),((9<<3)|0x87,1,2))
        self.assertIn('SetInfoPopup ',log)
        self.assertIn('SetInfoPopupClose ',log)

    def test_retina_hover_and_inventory_close(self):
        output,log = self.run_host('key',73,'equipment','invoke',1,'-',
                                   'testCall','["EQUIPrequestSlotInfo",10.9,20.9,30.9,40.9,0]',
                                   'move',959,41,'equipdraws','key',73,scale='2')
        row = next(json.loads(s) for s in output.splitlines() if s.startswith('{"equipment"'))
        self.assertEqual(row['select'],1)
        self.assertIn('SetInfoPopup ',log)
        self.assertIn('SetInfoPopupClose ',log)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1','private original instruction captures')
class Original(unittest.TestCase):
    def test_instruction_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_items_ui.py'), '--cases','200',
                            '--output',str(path)],check=True,capture_output=True,text=True)
            report = json.loads(path.read_text())
        self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()),report['families'])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and
                     all(os.environ.get(v) for v in ('MU_GAME_ROOT','MU_NATIVE_DATA_DIR','MU_GFX_LIB')),
                     'private Native Data, game root and fixed-clock GFx library')
class NativeHover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='items-ui-scene-')
        subprocess.run(['make','-C',str(ROOT/'native'),'-j4','world'],check=True,capture_output=True)
        cls.exe = Path(cls.tmp.name)/'mu-world'
        shutil.copy2(ROOT/'native/build/mu-world',cls.exe)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_equipment_hover_uses_popup_and_draws_all_accessories(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            data = Path(os.environ['MU_NATIVE_DATA_DIR'])
            log = out/'gfx.log'
            env = {**os.environ,'MU_GFX_LOG':str(log),'MU_GFX_TEST_CLOCK':'1','MU_GFX_SINGLE_BUFFER':'1',
                   'MU_GFX_PUBLIC_DEMO':'1','MU_NATIVE_SETTINGS_DIR':str(out),'MU_LANG_DIR':str(data/'lang')}
            result = subprocess.run([str(self.exe),'--game-root',os.environ['MU_GAME_ROOT'],'--objects-dir',
                                     str(data/'objects'),'--headless','--backend','gl','--no-audio',
                                     '--width','1280','--height','800','--class','1','--tile','140,130',
                                     '--gfx',str(data/'gfx'),'--gfx-open','inventory,equipment-demo',
                                     '--hero-name','Preview','--hero-item','weapon0=Item/CookriShortSword.bmd@0:68:9:1',
                                     '--progress-script','20:click:10050240','--frames','31','--every','1000',
                                     '--out-dir',str(out)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stderr[-2000:])
            self.assertIn('.SetInfoPopup(',log.read_text())
            report = next(json.loads(s)['gfx'] for s in result.stdout.splitlines() if s.startswith('{"gfx":'))
            self.assertEqual(report['item_models_missing'],0)
            self.assertEqual([r['slot'] for r in report['inventory_equipment']],[0,9,10,11,12,13,14])


if __name__ == '__main__':
    unittest.main()
