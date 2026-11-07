"""APP-POLISH-006: the 80-player crowd's HUD vitals and the demo inventory's durability.

Portable: the README crowd command keeps the world's offline join (the recorded level-1 Dark Knight that
fixture/hero_join.h seeds as current and maximum HP/MP/SD/AG, combat HP 1100) instead of overriding it, and the
capture's checks reject the old HUD (16960/0) while accepting extra glow textures.  Private
(MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR with objects/, gfx/ and lang/, MU_GFX_LIB): both crowd
scenes report the recorded vitals on the HUD, and the world's demo inventory tooltips read full durability.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(NATIVE / 'tools'))
import capture_readme_stress as crowd  # noqa: E402

RECORDED = {'hp': [1100, 1100], 'mp': [200, 200], 'sd': [52, 52], 'ag': [25, 25]}


def recorded_join():
    """fixture/hero_join.h: the class it applies to and its four vitals."""
    text = (NATIVE / 'fixture/hero_join.h').read_text()
    gate = int(re.search(r'seed->class_byte == (\d+) && level == 1', text).group(1))
    vitals = [int(v) for v in re.findall(r'seed->vitals\[\d\] = (\d+);', text)]
    return gate, vitals


def world_defaults():
    """world_rt.c's offline defaults: the hero's class byte and the combat fixture's hero HP, which since
    APP-POLISH-007 is the hero's join HP (the recorded 1100 for this class byte)."""
    text = (NATIVE / 'world/world_rt.c').read_text()
    cls = int(re.search(r'o->class_byte = (0x[0-9a-fA-F]+|\d+);', text).group(1), 0)
    assert re.search(r'o->combat_config\.hero_hp = MU_WORLD_HERO_HP_JOIN;', text)
    hp = recorded_join()[1][0] if cls == recorded_join()[0] else None
    return cls, hp


class CrowdFixture(unittest.TestCase):
    def command(self):
        a = argparse.Namespace(game_root=Path('/g'), objects=Path('/o'), gfx=Path('/m'), lang=Path('/l'))
        return crowd.command(a, 141, (60, 50), Path('/out'), Path('/p.txt'), Path('/a.txt'))

    def test_crowd_keeps_the_recorded_join(self):
        cmd = self.command()
        self.assertNotIn('--class', cmd)
        self.assertNotIn('--hero-hp', cmd)
        self.assertIn('--combat', cmd)
        gate, vitals = recorded_join()
        cls, hp = world_defaults()
        self.assertEqual((cls, gate), (1, 1))
        self.assertEqual(vitals, [1100, 200, 52, 25])
        self.assertEqual(hp, vitals[0])
        self.assertLessEqual(hp, 0xffff)   # A0/30 carries HP in 16 bits

    def test_crowd_keeps_the_world_fov(self):
        """README-IMAGES-C: no native-only FOV override by default; FOV 65 saw past the terrain cull."""
        self.assertNotIn('--perf-fov', self.command())
        a = argparse.Namespace(game_root=Path('/g'), objects=Path('/o'), gfx=Path('/m'), lang=Path('/l'), fov=45.0)
        cmd = crowd.command(a, 0, (182, 128), Path('/out'), Path('/p.txt'), Path('/a.txt'))
        self.assertEqual(cmd[cmd.index('--perf-fov') + 1], '45.0')

    def test_hud_check_rejects_missing_or_exceeded_maxima(self):
        good = 'hud_vitals t=4012 session=1077,200,52,25 hud=1077,200,52,25 max=1100,200,52,25'
        self.assertEqual(crowd.hud_vitals('noise\n' + good)[-1],
                         {'hp': [1077, 1100], 'mp': [200, 200], 'sd': [52, 52], 'ag': [25, 25]})
        for bad in ('hud_vitals t=1012 session=16960,600,51,39 hud=16960,600,51,39 max=0,0,0,0',
                    'hud_vitals t=1012 session=1200,200,52,25 hud=1200,200,52,25 max=1100,200,52,25',
                    'hud_vitals t=1012 session=900,200,52,25 hud=1100,200,52,25 max=1100,200,52,25',
                    ''):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                crowd.hud_vitals(bad)

    def test_glow_check_accepts_extra_and_rejects_missing_textures(self):
        rows = [{'players': {'count': 80, 'addinfo': 80}}, {'gfx': {'renders': 2}},
                {'combat': True, 'skills': 5, 'fx_created': 400, 'joints_created': 16}]
        rows += [{'player': i, 'name': f'P{i}', 'loaded': [0, 1, 1, 1, 1, 1, 1, 0, 1],
                  'textures_missing': [-1, 0, 0, 0, 0, 0, 0, -1, 0],
                  'effect_textures_loaded': [0, 6, 7, 7, 6, 6, 6, 0, 6]} for i in range(80)]
        self.assertEqual(crowd.verify(rows)['players'], 80)
        rows[-1]['effect_textures_loaded'][3] = 5
        with self.assertRaises(ValueError):
            crowd.verify(rows)


GAME = os.environ.get('MU_GAME_ROOT')
DATA = os.environ.get('MU_NATIVE_DATA_DIR')
GFX = os.environ.get('MU_GFX_LIB')
PRIVATE = (os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and GAME and DATA and GFX and Path(GFX).is_file() and
           all(Path(DATA, d).is_dir() for d in ('objects', 'gfx', 'lang')))


@unittest.skipUnless(PRIVATE, 'private: MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB')
class PrivateDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'world'], check=True, capture_output=True)

    def test_crowd_scenes_show_the_recorded_vitals(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run([sys.executable, str(NATIVE / 'tools/capture_readme_stress.py'), '--game-root', GAME,
                                '--objects', str(Path(DATA, 'objects')), '--gfx', str(Path(DATA, 'gfx')),
                                '--lang', str(Path(DATA, 'lang')), '--out', str(Path(tmp, 'out'))],
                               capture_output=True, text=True, env={**os.environ, 'MU_GFX_LIB': GFX}, timeout=600)
            if p.returncode and 'headless GL' in p.stderr:
                self.skipTest('no offscreen GL context')
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            records = json.loads(Path(tmp, 'out/commands.json').read_text())
        self.assertEqual([r['scene'] for r in records], ['lorencia', 'tormenta'])
        for r in records:
            self.assertEqual(r['summary']['hud_vitals'], RECORDED, r['scene'])
            self.assertEqual(r['summary']['players'], 80)

    def test_demo_inventory_tooltips_read_full_durability(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp, 'gfx.log')
            env = {**os.environ, 'MU_GFX_LIB': GFX, 'MU_LANG_DIR': str(Path(DATA, 'lang')),
                   'MU_GFX_SINGLE_BUFFER': '1', 'MU_GFX_LOG': str(log)}
            p = subprocess.run([str(NATIVE / 'build/mu-world'), '--game-root', GAME,
                                '--objects-dir', str(Path(DATA, 'objects')), '--headless', '--backend', 'gl',
                                '--no-audio', '--gfx', str(Path(DATA, 'gfx')), '--gfx-open', 'inventory',
                                '--npc-script', '10:tipinv:0 20:tipinv:2', '--frames', '30', '--every', '1000',
                                '--out-dir', tmp], capture_output=True, text=True, env=env, timeout=300)
            if p.returncode and 'headless GL' in p.stderr:
                self.skipTest('no offscreen GL context')
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            pairs = [tuple(map(int, m)) for m in re.findall(r'Durability: \[(\d+)/(\d+)\]', log.read_text())]
        self.assertEqual(len(pairs), 2, pairs)   # Blade +9 (cell 0) and the +7 helm (cell 2)
        for current, maximum in pairs:
            self.assertGreater(maximum, 1)
            self.assertEqual(current, maximum)


if __name__ == '__main__':
    unittest.main()
