"""Overhead names in the walk-around world (NATIVE-NAMES-001) checks.

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic combat world of test_native_combat.py (a hero
and a synthetic monster of server class 3):
  * addInfo for the hero (player, kind 1) and the monster (kind 2) on the first
    frame, the plates follow their projected head positions every frame;
  * the demo HP packets lower the monster's HP percentage; SetPlayerDie's
    removeInfo takes the plate when the dead counter reaches 15, the demo
    respawn creates it again;
  * chat lines show as bubbles over the hero (10 s, 40 s for '#'), party
    lines ('~') do not;
  * the monster info option hides monster panels; the stand-in drawing
    changes the frame; --no-names turns everything off; runs are deterministic.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): Lorencia with the demo
placement: the four field monsters and the hero get plates, the town NPCs
(kind 4) none.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_combat import write_combat_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PLACEMENT = NATIVE/'world/lorencia-demo-placement.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
HERO, MONSTER = 0x1234, 0x100


def run(root, placement, *args, size=(64, 64), keep=None):
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = keep or tmp
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft',
                                 '--no-audio', '--placement', str(placement), '--width', str(size[0]), '--height',
                                 str(size[1]), '--every', '1', '--out-dir', out_dir, '--tile', '120,120',
                                 *[str(a) for a in args]], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'names': [r for r in rows if 'names_frame' in r],
            'combat': [r for r in rows if 'combat_frame' in r],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r['names'] for r in rows if 'names' in r and isinstance(r['names'], dict)), None)}


def plate(frame, key):
    return next((p for p in frame['plates'] if p[0] == key), None)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_combat_world(Path(cls.tmp.name)/'game')
        cls.placement = Path(cls.tmp.name)/'placement.txt'
        cls.placement.write_text('# demo\nactor 3 123 120 6 label spider\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class NamesTests(Build):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.out = run(cls.root, cls.placement, '--frames', '420', '--combat', '--combat-script', '2:attack:spider',
                      '--combat-seed', '11', '--chat-script', '3:hello;5:~party only;300:#shout')

    def test_plates_are_created_on_the_first_frame(self):
        first = self.out['names'][0]
        self.assertEqual(sorted((p[0], p[1]) for p in first['plates']), [(MONSTER, 2), (HERO, 1)])
        self.assertEqual(self.out['summary']['added'], 3)            # hero, monster, the respawned monster

    def test_plates_follow_the_projection(self):
        hero = [plate(f, HERO) for f in self.out['names']]
        self.assertTrue(all(p and math.isfinite(p[2]) and math.isfinite(p[3]) for p in hero))
        self.assertTrue(all(p[4] == 1 for p in hero))                # PlayerName visible
        # the camera follows the hero, so the monster's plate moves while the hero walks to it
        mon = [plate(f, MONSTER) for f in self.out['names'][:40] if plate(f, MONSTER)]
        self.assertGreater(len({(round(p[2], 2), round(p[3], 2)) for p in mon}), 1)
        self.assertTrue(all(p[3] < h[3] + 400 for p, h in zip(mon, hero)))

    def test_hp_packets_and_death(self):
        names, combat = self.out['names'], self.out['combat']
        hps = [plate(f, MONSTER)[6] for f in names if plate(f, MONSTER)]
        self.assertEqual(set(hps), {0})  # fixture viewport has no HP; damage cannot invent a remote pool
        self.assertEqual(self.out['summary']['hp_updates'], 0)
        self.assertTrue(any(c['points'] > 0 for c in combat))
        dead = [c['monsters'][0]['dead'] for c in combat]
        gone = next(i for i, f in enumerate(names) if plate(f, MONSTER) is None)
        self.assertEqual(dead[gone], 15)                             # SetPlayerDie from the dead counter 15 on
        self.assertIsNotNone(plate(names[gone - 1], MONSTER))
        back = next(i for i, f in enumerate(names) if i > gone and plate(f, MONSTER) is not None)
        self.assertEqual(combat[back]['monsters'][0]['removed'], 0)
        self.assertEqual(plate(names[back], MONSTER)[6], 0)
        self.assertEqual(self.out['summary']['removed'], 1)

    def test_chat_bubbles(self):
        names = self.out['names']
        self.assertEqual(plate(names[2], HERO)[8], '')
        self.assertEqual(plate(names[4], HERO)[8], 'msg')
        self.assertEqual(self.out['summary']['messages'], 2)          # 'hello' and '#shout', not '~party only'
        # 10000 ms for normal chat, from the handler's last update before the line (frame 2): gone before the
        # 40 s shout at frame 300
        tick = {w['frame']: w['tick'] for w in self.out['walk']}
        cleared = next(i for i in range(4, 300) if plate(names[i], HERO)[8] == '')
        self.assertGreaterEqual(tick[cleared] - tick[2], 10000)
        self.assertLess(tick[cleared - 1] - tick[2], 10000)
        self.assertEqual(plate(names[-1], HERO)[8], 'msg')

    def test_deterministic(self):
        again = run(self.root, self.placement, '--frames', '120', '--combat', '--combat-script', '2:attack:spider',
                    '--combat-seed', '11', '--chat-script', '3:hello;5:~party only;300:#shout')
        self.assertEqual(again['names'], self.out['names'][:120])


class OptionTests(Build):
    def test_monster_info_option(self):
        out = run(self.root, self.placement, '--frames', '4', '--monster-info', '0')
        self.assertEqual(plate(out['names'][-1], MONSTER)[5], 0)      # MonsterInfoMC hidden (monster view off)
        self.assertEqual(plate(out['names'][-1], HERO)[5], 1)

    def test_no_names(self):
        out = run(self.root, self.placement, '--frames', '4', '--no-names')
        self.assertEqual(out['names'], [])
        self.assertIsNone(out['summary'])

    def test_stand_in_changes_the_frame(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            run(self.root, self.placement, '--frames', '6', '--chat-script', '1:hello', size=(240, 160), keep=a)
            run(self.root, self.placement, '--frames', '6', '--no-names', size=(240, 160), keep=b)
            self.assertNotEqual((Path(a)/'frame-0005.png').read_bytes(), (Path(b)/'frame-0005.png').read_bytes())


WORLD = NATIVE/'build/mu-world'
GFX_MOVIES = os.environ.get('MU_NAMES_GFX_MOVIES')   # converted movies with base.swf (native/gfx/gfxconvert.py)
GFX_LIB = os.environ.get('MU_GFX_LIB') or str(NATIVE/'gfx/mugfx/target/release/libmugfx.dylib')


@unittest.skipUnless(PRIVATE and GFX_MOVIES and Path(GFX_LIB).exists() and WORLD.exists(),
                     'private: MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NAMES_GFX_MOVIES, libmugfx, mu-world')
class GfxRoute(unittest.TestCase):
    def test_the_movie_gets_the_handler_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp)/'gfx.log'
            env = {**os.environ, 'MU_GFX_LIB': GFX_LIB, 'MU_GFX_LOG': str(log), 'MU_GFX_SINGLE_BUFFER': '1'}
            r = subprocess.run([str(WORLD), '--game-root', os.environ['MU_GAME_ROOT'], '--headless', '--backend', 'gl',
                                '--frames', '160', '--every', '80', '--out-dir', tmp, '--placement', str(PLACEMENT),
                                '--tile', '182,128', '--class', '2', '--combat-weapon', 'bow', '--combat-script',
                                '6:attack:hound', '--chat-script', '60:Hello', '--gfx', GFX_MOVIES, '--quiet'],
                               capture_output=True, text=True, timeout=600, env=env)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            text = log.read_text()
        self.assertIn('hudPlayerName ["onLoad"', text)
        self.assertRegex(text, r'hudPlayerName_\d+\.instance\d+\.addInfo\(\[\{"key":4660,"type":1,"name":"<font color=\'#FFDC00\'')
        self.assertIn('"key":264,"type":2', text)                     # the Bull Fighter
        self.assertIn('playerContainer.ply_4660.setMessage([{"msg":"Nighty: Hello","time":10000}])', text)
        self.assertIn('removeInfo([{"key":265,"type":2}])', text)      # the Hound dies


@unittest.skipUnless(PRIVATE, 'private: MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class Lorencia(unittest.TestCase):
    def test_monsters_get_plates_npcs_none(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        out = run(os.environ['MU_GAME_ROOT'], PLACEMENT, '--frames', '3', '--tile', '182,128')
        last = out['names'][-1]
        types = sorted(p[1] for p in last['plates'])
        self.assertEqual(types, [1, 2, 2, 2, 2])                      # the hero and the four field monsters
        self.assertEqual(out['summary']['skipped'], 8)                 # six town NPCs and the two effect classes


if __name__ == '__main__':
    unittest.main()
