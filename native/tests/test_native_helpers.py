"""Helpers (pets and mounts) in the walk-around world (NATIVE-HELPERS-001) checks.

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic combat world of test_native_combat.py with
synthetic helper models (Data/Item/helper01.bmd, helper02.bmd,
Data/Skill/Rider01.bmd with a "Bip01 Spine" bone, fenrir_gold.bmd):
  * --helper angel: CreateBug's slot 0 follows the hero, is drawn by RenderBug;
  * --helper uniria: the mount manager's Uniria carries the hero: the rider
    actions 0x26 standing and 0x47 / 0x67 moving (0x0106c382), the mount
    actions 0 / 2 / 3 (0x0103d931), the lift by the rider bone + 20;
  * --helper imp: the link item on the hero;
  * --helper fenrir-gold: the Fenrir class with the gold model of state 4;
  * demo players with pet=angel / ride=0x1a02: ChangeCharacterExt's calls give
    them their angel and their Uniria;
  * --no-helpers and an unknown helper name.
The comparison with the client's routines is scripts/validate_helpers.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_combat import write_combat_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PLAYERS = NATIVE/'world/lorencia-demo-players.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def write_helper_models(root):
    item = Path(root)/'Data'/'Item'
    skill = Path(root)/'Data'/'Skill'
    item.mkdir(parents=True, exist_ok=True)
    skill.mkdir(parents=True, exist_ok=True)
    for name, seed in (('helper01', 31), ('helper02', 32)):
        path = nf.write_textured_model(item, seed)
        path.rename(item/f'{name}.bmd')
    for name, seed, bone in (('Rider01', 33, 'Bip01 Spine'), ('fenrir_gold', 34, 'sit_pos_0')):
        path = nf.write_textured_model(skill, seed)
        raw = path.read_bytes().replace(nf.name32('bone1'), nf.name32(bone))
        (skill/f'{name}.bmd').write_bytes(raw)
        path.unlink()


def run(root, *args, size=(64, 64), tile='120,120', check=True):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                                 '--no-env', '--no-particles', '--width', str(size[0]), '--height', str(size[1]),
                                 '--every', '1', '--out-dir', tmp, '--tile', tile, *[str(a) for a in args]],
                                capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'helpers': [r for r in rows if 'helpers_frame' in r],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r['helpers'] for r in rows if isinstance(r.get('helpers'), dict)), None),
            'logs': [line for line in result.stdout.splitlines() if line.startswith('helpers: ')],
            'returncode': result.returncode, 'stderr': result.stderr}


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_combat_world(Path(cls.tmp.name)/'game')
        write_helper_models(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class HeroHelpers(Build):
    def test_effects_use_world_bones_and_the_real_mount(self):
        subprocess.run(['make', '-C', str(NATIVE), 'build/helper-fx-host'], check=True, capture_output=True)
        out = subprocess.run([str(NATIVE/'build/helper-fx-host'), str(self.root)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(json.loads(out.stdout), dict(spaces=1, offset=1, flash=1, ring=1, owners=1, bounds=1, eye=1))

    def test_angel_follows_the_hero(self):
        out = run(self.root, '--frames', '60', '--helper', 'angel')
        self.assertEqual(out['summary']['bugs_created'], 1)
        last = out['helpers'][-1]
        self.assertEqual(last['bugs'], 1)
        bug = last['bug0']
        self.assertEqual(bug[:2], [0x24e6, 0])                # the angel's model index, owner 0 (the hero)
        hero = out['walk'][-1]['hero']
        self.assertLess(abs(bug[0 + 2] - hero[0]) + abs(bug[1 + 2] - hero[1]), 1200)   # around its owner
        self.assertGreater(bug[4], hero[2])                   # above the ground
        self.assertGreater(sum(f['drawn_bugs'] for f in out['helpers']), 0)
        self.assertGreater(out['summary']['particles'], 0)   # the Spark02 sparkles (0x7f25)

    def test_uniria_carries_the_hero(self):
        out = run(self.root, '--frames', '80', '--helper', 'uniria', '--walk', '124,120')
        s = out['summary']
        self.assertEqual((s['mounts_set'], s['live_mounts']), (1, 1))
        actions = [w['action'] for w in out['walk']]
        self.assertIn(0x26, actions)                          # the rider's stand 0x0103dd6b(c, 0)
        self.assertTrue(set(actions) & {0x47, 0x67})          # walk / run on the mount
        moving = [f for f, w in zip(out['helpers'], out['walk']) if w['moving']]
        self.assertTrue(moving)
        self.assertTrue(all(f['riding'] == 1 for f in out['helpers'][2:]))
        self.assertTrue(any(f['mount0'][2] in (2, 3) for f in moving))   # the mount walks / runs
        last = out['helpers'][-1]['mount0']
        self.assertEqual(last[:2], [1, 0])                    # class Uniria, owner 0
        self.assertNotEqual(last[4:7], [0.0, 0.0, 20.0])      # the lift: the posed rider bone + (0, 0, 20)

    def test_imp_on_the_shoulder(self):
        out = run(self.root, '--frames', '10', '--helper', 'imp')
        self.assertEqual(out['helpers'][-1]['drawn_imps'], 1)
        self.assertEqual(out['summary']['bugs_created'], 0)

    def test_fenrir_gold_model(self):
        out = run(self.root, '--frames', '10', '--helper', 'fenrir-gold')
        self.assertTrue(any('model 0x4ab' in line for line in out['logs']))
        self.assertEqual(out['helpers'][-1]['mount0'][0], 4)
        # NATIVE-HELPERS-002: its registry functor draws the passes (mesh 0 twice, mesh 1), the six flares and
        # the two body lightning effects every frame
        self.assertGreaterEqual(out['helpers'][-1]['passes'], 3)
        self.assertGreaterEqual(out['summary']['sprites'], 6 * 9)
        self.assertGreaterEqual(out['summary']['effects'], 2 * 9)

    def test_no_helpers_and_unknown_name(self):
        out = run(self.root, '--frames', '5', '--helper', 'angel', '--no-helpers')
        self.assertEqual(out['helpers'], [])
        bad = run(self.root, '--frames', '5', '--helper', 'teapot', check=False)
        self.assertNotEqual(bad['returncode'], 0)
        self.assertIn('unknown helper', bad['stderr'])


class PlayerHelpers(Build):
    def test_players_get_their_angel_and_uniria(self):
        players = Path(self.tmp.name)/'players.txt'
        players.write_text('player Aeris class=0x01 at=123,120 dir=3 pk=3 level=180 pet=angel idle=5\n'
                           'player Kyra class=0x02 at=118,122 dir=1 pk=3 level=200 ride=0x1a02 '
                           'route=118,126;118,122 idle=5\n')
        out = run(self.root, '--frames', '120', '--players', players)
        s = out['summary']
        self.assertEqual((s['bugs_created'], s['mounts_set']), (1, 1))
        last = out['helpers'][-1]
        self.assertEqual(last['bug0'][:2], [0x24e6, 1])      # owner 1: the first player
        self.assertEqual(last['mount0'][:2], [1, 2])         # owner 2: Kyra on a Uniria
        rider_actions = {f['mount0'][3] for f in out['helpers'][5:]}
        self.assertTrue(rider_actions <= {0x26, 0x47, 0x67}, rider_actions)


@unittest.skipUnless(PRIVATE, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateTests(unittest.TestCase):
    def test_lorencia_helpers(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        out = run(os.environ['MU_GAME_ROOT'], '--frames', '120', '--players', PLAYERS, '--player-range', '15',
                  '--helper', 'fenrir-blue', size=(320, 240), tile='128,124')
        logs = '\n'.join(out['logs'])
        for line in ('model 0x4aa: Data/Skill/fenrir_blue.bmd', 'model 0x417: Data/Skill/Rider01.bmd',
                     'model 0x24e6: Data/Item/helper01.bmd'):
            self.assertIn(line, logs)
        self.assertGreaterEqual(out['summary']['mounts_set'], 2)    # the hero's Fenrir and Kyra's Uniria
        self.assertEqual(out['summary']['bugs_created'], 1)         # Aeris' angel
        self.assertTrue(any(f['drawn_mounts'] for f in out['helpers']))


if __name__ == '__main__':
    unittest.main()
