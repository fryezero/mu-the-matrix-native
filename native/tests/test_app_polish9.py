"""Small native windows and a single fixture record for HUD/CharacterInfo."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'native/tests'))
import validate_app_polish9 as validator
from test_native_gfx2 import build_layer_host
import validate_gfx3

SIZES = [(640,480),(800,600),(1024,600),(1024,699),(1024,700),(1024,768),
         (1280,720),(1280,800),(1280,1024),(1366,768),(1440,900),(1600,1000),
         (1680,1050),(1920,1080),(2560,1440)]
NAMES = ['INVENTORY','CHARACTER','SKILL_STAMP','MASTER_TREE','TREE4','TREE5',
         'MOVE_COMMAND','QUEST_PROGRESS','MY_QUEST','QUEST_SUMMARY','JOB_QUEST',
         'COMMAND','MATCHING','GENS','PET_INVENTORY','GREMORY']
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


class Bounds(unittest.TestCase):
    def test_undersize_and_position_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            fit = validator.native_fit(Path(tmp))
            cases = [(-100,-30,900,700,640,406), (1200,900,300,600,1024,650),
                     (50,60,300,600,1920,970), (0,0,300,600,1024,650)]
            self.assertEqual(validator.fit_errors(fit, cases), [])
            self.assertEqual(validator.bar_errors(fit,[(874.95,106,95,640,480),
                                                       (1200,106.5,100,800,600)]),[])

    def test_resize_reaches_unaligned_character_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            validate_gfx3.layer_log(work)
            log = work/'resized.log'
            env = {**os.environ, 'MUGFX_STUB_LOG': str(log)}
            subprocess.run([str(work/'gfx-layer-host'), str(work/'movies'),
                            str(work/('libmugfx_stub.dylib' if sys.platform == 'darwin' else 'libmugfx_stub.so')),
                            'resize', '980', '570'], env=env, capture_output=True, check=True)
            calls = log.read_text()
            for name in ('InventoryFrame','CharacterInfoFrame','MoveCommand'):
                self.assertRegex(calls, name+r' .*\.SetWindowSize \[980,570\]')


@unittest.skipUnless(PRIVATE, 'private original instructions')
class OriginalResize(unittest.TestCase):
    def test_original_instructions(self):
        result = validator.run(SimpleNamespace(text=None, data=None, cases=200, mutants=False))
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['families']['resize']['cases'], 60)


@unittest.skipUnless(PRIVATE and os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GFX_LIB'),
                     'private Native Data and real GFx library')
class LayoutSweep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='mu-polish9-')
        cls.work = Path(cls.tmp.name)
        cls.host, _ = build_layer_host(cls.work)
        text = (ROOT/'native/gfx/mu_gfx_layer.h').read_text()
        enum = text[text.index('enum { MU_GFX_MAIN'):text.index('MU_GFX_MOVIES };')]
        cls.ids = {name.removeprefix('MU_GFX_'): i for i, name in enumerate(re.findall(r'MU_GFX_\w+', enum))}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_window_at_each_size(self):
        for scale, sizes in ((1,SIZES),(2,[SIZES[0],SIZES[-1]])):
            for w,h in sizes:
                with self.subTest(size=(w,h), backing_scale=scale):
                    args = []
                    for name in NAMES:
                        movie = str(self.ids[name])
                        args += ['open',movie,'advance','80','layout','open',movie]
                    env = {**os.environ, 'MU_GFX_SIZE': f'{w}x{h}', 'MU_GFX_SCALE': str(scale),
                           'MU_GFX_TEST_CLOCK': '1'}
                    p = subprocess.run([str(self.host), str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx'),
                                        os.environ['MU_GFX_LIB'], *args, 'maplayout'], env=env, capture_output=True,
                                       text=True, timeout=180)
                    self.assertEqual(p.returncode,0,p.stderr[-2000:]+p.stdout[-2000:])
                    rows = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{"layout_movie"')]
                    opened = [r for r in rows if r['open'] and r['layout_movie'] not in (0,4)]
                    self.assertEqual({r['layout_movie'] for r in opened}, {self.ids[n] for n in NAMES})
                    main = next(r for r in rows if r['layout_movie'] == 0)
                    bottom = main['_y']
                    self.assertGreaterEqual(main['_x'], -0.06)
                    self.assertLessEqual(main['_x']+main['_width'], w+0.06)
                    for r in opened:
                        self.assertTrue(r['_visible'],r)
                        ww = r['width'] if r['width'] is not None else r['_width']
                        hh = r['height'] if r['height'] is not None else r['_height']
                        self.assertGreater(ww,0,r)
                        self.assertGreater(hh,0,r)
                        self.assertGreaterEqual(r['_x'],-0.06,r)
                        self.assertGreaterEqual(r['_y'],-0.06,r)
                        self.assertLessEqual(r['_x']+ww,w+0.15,r)
                        self.assertLessEqual(r['_y']+hh,bottom+0.15,r)
                        # Close registration points must remain inside the viewport.
                        if r['btnClose._x'] is not None:
                            self.assertLessEqual(r['_x']+r['btnClose._x']*r['_xscale']/100,w+0.15,r)
                            self.assertLessEqual(r['_y']+r['btnClose._y']*r['_xscale']/100,bottom+0.15,r)
                    map_row = next(json.loads(l) for l in p.stdout.splitlines() if l.startswith('{"map_layout"'))
                    map_scale = 83 if h < 700 else 100
                    self.assertEqual(map_row['_xscale'],map_scale)
                    mw,mh = (int(w*100/83),int(h*100/83)) if h < 700 else (w,h)
                    self.assertEqual(map_row['_mask._x'],mw//2)
                    self.assertEqual(map_row['_mask._y'],mh//2-30)
                    self.assertEqual((map_row['_mask._width'],map_row['_mask._height']),(800,600))

    def test_open_windows_resize_and_pointer_close(self):
        args = []
        for name in NAMES:
            args += ['open',str(self.ids[name])]
        for w,h in ((640,480),(1024,700),(2560,1440)):
            args += ['resize',str(w),str(h),'advance','80','layout']
        # Smallest native size again; test each close in isolation through real pointer events.
        args += ['resize','640','480']
        for name in reversed(NAMES):
            args += ['open',str(self.ids[name])]
        for name in NAMES:
            args += ['open',str(self.ids[name]),'advance','80','clickclose',str(self.ids[name])]
        env = {**os.environ,'MU_GFX_SIZE':'2560x1440','MU_GFX_TEST_CLOCK':'1'}
        p = subprocess.run([str(self.host),str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx'),
                            os.environ['MU_GFX_LIB'],*args],env=env,capture_output=True,text=True,timeout=180)
        self.assertEqual(p.returncode,0,p.stderr[-2000:])
        rows = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{"layout_movie"')]
        groups = []
        for r in rows:
            if r['layout_movie'] == 0:
                groups.append([])
            groups[-1].append(r)
        self.assertEqual(len(groups),3)
        for group,(w,h) in zip(groups,((640,480),(1024,700),(2560,1440))):
            bottom = group[0]['_y']
            for r in group:
                if r['layout_movie'] not in {self.ids[n] for n in NAMES}:
                    continue
                ww = r['width'] if r['width'] is not None else r['_width']
                hh = r['height'] if r['height'] is not None else r['_height']
                self.assertTrue(r['_visible'],r)
                self.assertGreaterEqual(r['_x'],-0.06,r)
                self.assertGreaterEqual(r['_y'],-0.06,r)
                self.assertLessEqual(r['_x']+ww,w+0.15,r)
                self.assertLessEqual(r['_y']+hh,bottom+0.15,r)
        closes = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{"close_movie"')]
        self.assertEqual(len(closes),len(NAMES))
        self.assertTrue(all(r['close_delivered'] for r in closes),closes)


@unittest.skipUnless(PRIVATE and os.environ.get('MU_GAME_ROOT') and os.environ.get('MU_NATIVE_DATA_DIR'),
                     'private offline client fixture')
class DemoOwnership(unittest.TestCase):
    def test_all_five_demo_characters(self):
        names = ['Nightfall','Ironclad','Windleaf','Spellblade','Crownlord']
        profiles = [(1,0,0,18,18,15,30,0), (1,0,0,28,20,25,10,0),
                    (320,0,318,22,1302,20,15,0), (1,0,0,26,26,26,26,0),
                    (1,0,0,26,20,20,15,25)]
        hp = [600,1100,1119,1100,900]
        for slot,name in enumerate(names):
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix='mu-character9-') as tmp:
                flow = ('8:click:group:0 16:click:server:0 22:text:demo 24:tab 25:text:demo '
                        f'28:enter 42:click:row:{slot} 54:dblclick:row:{slot} 80:key:67')
                env = {**os.environ, 'MU_LANG_DIR': str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'lang'),
                       'MU_HUD_TRACE':'1', 'MU_GFX_TEST_CLOCK':'1', 'MU_GFX_LOG':str(Path(tmp)/'gfx.log')}
                p = subprocess.run([str(ROOT/'native/build/mu-client'), '--game-root',os.environ['MU_GAME_ROOT'],
                    '--session',str(ROOT/'native/client/demo-session.txt'), '--width','1024','--height','768',
                    '--world-objects',str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'objects'),
                    '--gfx',str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx'), '--no-audio','--no-store',
                    '--headless','--backend','gl','--progress','--frames','115','--every','1000',
                    '--out-dir',tmp,'--script',flow],env=env,capture_output=True,text=True,timeout=180)
                self.assertEqual(p.returncode,0,p.stderr[-2000:])
                matches = re.findall(r'character_fixture session=(\S+) view=(\S+) name=(\S+)',p.stderr)
                self.assertTrue(matches,p.stderr[-3000:])
                for session,view,shown in matches:
                    self.assertEqual(view,session)
                    self.assertEqual(shown,name)
                self.assertEqual(tuple(int(n) for n in matches[-1][0].split(',')[:8]),profiles[slot])
                log = (Path(tmp)/'gfx.log').read_text()
                self.assertIn(f'.SetCharacterName ["{name}"]',log)
                self.assertIn(f'{hp[slot]} / {hp[slot]}',log)


if __name__ == '__main__':
    unittest.main()
