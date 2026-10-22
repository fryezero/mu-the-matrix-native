"""The Dark Raven in the walk-around world (NATIVE-HELPERS-002) checks.

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic combat world of test_native_combat.py with
synthetic DarkSpirit.bmd / Dark_Soul.bmd models:
  * --helper dark-raven: the pet byte 1 creates the raven (model 0x411) that
    fades in, flies around and above the hero (MovePet's AI 0 / 1) and is
    drawn by RenderPet;
  * --helper dark-raven-40 on a safe tile: the soul model 0x748 that sits
    (AI 3);
  * a demo player with raven=2 gets its own raven;
  * determinism.
The comparison with the client's routines is scripts/validate_raven.py.
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


def write_raven_models(root):
    """Synthetic DarkSpirit.bmd (0x50 bones: MovePet's sparkles pick a bone of rand() % 0x42) and Dark_Soul.bmd."""
    for folder, name, seed, bones in (('Skill', 'DarkSpirit', 41, 0x50), ('Item', 'Dark_Soul', 42, 2)):
        d = Path(root)/'Data'/folder
        d.mkdir(parents=True, exist_ok=True)
        (d/f'{name}.bmd').write_bytes(nf.character_layout(seed, bones=bones, actions=4, keys=(6, 4, 4, 4), meshes=2,
                                                          texture_prefix=f'{name}_'))
        for index in range(2):
            (d/f'{name}_{index}.OZT').write_bytes(nf.ozt(nf.tga(8, 8, seed*10 + index)))


def run(root, *args, size=(64, 64), tile='120,120', check=True):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                                 '--no-env', '--width', str(size[0]), '--height', str(size[1]),
                                 '--every', '1', '--out-dir', tmp, '--tile', tile, *[str(a) for a in args]],
                                capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'ravens': [r for r in rows if isinstance(r.get('raven'), int)],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r['raven'] for r in rows if isinstance(r.get('raven'), dict)), None),
            'logs': [line for line in result.stdout.splitlines() if line.startswith('helpers: ')],
            'stdout': result.stdout, 'returncode': result.returncode}


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_combat_world(Path(cls.tmp.name)/'game')
        write_raven_models(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_raven_flies(self):
        out = run(self.root, '--frames', '80', '--helper', 'dark-raven')
        s = out['summary']
        self.assertEqual((s['sets'], s['creates'], s['moves']), (1, 1, 80))
        frames = [r for r in out['ravens'] if r['raven'] == 0]
        self.assertEqual(len(frames), 80)
        self.assertEqual({r['model'] for r in frames}, {0x411})
        self.assertLess(frames[0]['alpha'], 0.5)                 # fades in from 0.1
        self.assertEqual(frames[-1]['alpha'], 1.0)
        self.assertTrue({r['ai'] for r in frames} <= {0, 1})
        hero_z = out['walk'][-1]['hero'][2]
        self.assertGreater(frames[-1]['position'][2], hero_z + 100.0)   # above the hero
        self.assertGreater(s['drawn'], 0)

    def test_soul_in_safe_zone(self):
        tile = '120,105'   # the synthetic world's safe-zone strip (y 100..110)
        safe = run(self.root, '--frames', '3', '--helper', 'dark-raven-40', tile=tile)['walk'][0]['safe']
        if not safe:
            self.skipTest('the synthetic tile is not a safe zone')
        out = run(self.root, '--frames', '30', '--helper', 'dark-raven-40', tile=tile)
        frames = [r for r in out['ravens'] if r['raven'] == 0]
        self.assertEqual(frames[0]['model'], 0x748)
        self.assertEqual(frames[-1]['ai'], 3)

    def test_player_raven(self):
        players = Path(self.tmp.name)/'players.txt'
        players.write_text('player Corvin class=0x04 at=123,120 dir=3 pk=3 level=300 raven=2 idle=5\n')
        out = run(self.root, '--frames', '60', '--players', players)
        owners = {r['raven'] for r in out['ravens']}
        self.assertEqual(owners, {1})
        self.assertEqual(out['summary']['creates'], 1)

    def test_deterministic(self):
        a = run(self.root, '--frames', '40', '--helper', 'dark-raven-20')
        b = run(self.root, '--frames', '40', '--helper', 'dark-raven-20')
        self.assertEqual(a['ravens'], b['ravens'])


@unittest.skipUnless(PRIVATE, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateTests(unittest.TestCase):
    def test_lorencia_raven(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        out = run(os.environ['MU_GAME_ROOT'], '--frames', '60', '--helper', 'dark-raven', size=(320, 240),
                  tile='175,120')
        logs = '\n'.join(out['logs'])
        self.assertIn('model 0x411: Data/Skill/DarkSpirit.bmd', logs)
        self.assertGreater(out['summary']['sparkles'], 0)
        self.assertGreater(out['summary']['drawn'], 0)
        town = run(os.environ['MU_GAME_ROOT'], '--frames', '20', '--helper', 'dark-raven', size=(320, 240),
                   tile='133,127')
        self.assertIn('model 0x748: Data/Item/Dark_Soul.bmd', '\n'.join(town['logs']))


if __name__ == '__main__':
    unittest.main()
