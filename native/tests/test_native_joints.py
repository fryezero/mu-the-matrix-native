"""The joint pool and the world objects' effects in the walk-around session (NATIVE-JOINT-001).

Portable (synthetic data only), through `mu-walk` (headless, software rasterizer) on the synthetic world 0 of
test_native_world.py with a synthetic Effect/JointThunder01 and Effect/Shiny02 and `--joint-demo SUB` (a viewer
test: a Tormenta lightning joint 0x7f7d of subtype SUB above the hero every 20 steps through the world objects'
joint pool):
  * every subtype 0x10..0x1a is created (none unsupported), moves for its 21 steps and draws quads;
  * the bolts and arcs create their Shiny02 start flash through CreateSprite;
  * --no-particles drops the module (no joint report);
  * runs are deterministic.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_OBJECTS_PLAIN_DIR with the local EncTerrain142.plain): the
installed Tormenta Island at 82,19 creates the handler's lightning joints and the field tornado, draws them and
has every joint bitmap.
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
from test_native_particles import ozj_jpeg  # noqa: E402
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
WORLD = NATIVE/'build/mu-world'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def run(binary, root, *args):
    result = subprocess.run([str(binary), '--game-root', str(root), '--headless', '--no-audio', '--quiet',
                             *[str(a) for a in args]], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'{binary.name} failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'joints': next((r for r in rows if r.get('joints') is True), None),
            'particles': next((r for r in rows if r.get('particles') is True), None),
            'frames': [r for r in rows if 'frame' in r and 'tick' in r]}


class JointSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_open_world(Path(cls.tmp.name)/'game')
        effect = cls.root/'Data'/'Effect'
        effect.mkdir(parents=True, exist_ok=True)
        (effect/'JointThunder01.OZJ').write_bytes(ozj_jpeg(64, 16))
        (effect/'Shiny02.OZJ').write_bytes(ozj_jpeg(32, 32))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def session(self, subtype, *extra, frames=45):
        return run(WALK, self.root, '--backend', 'soft', '--frames', frames, '--every', frames, '--out-dir',
                   Path(self.tmp.name)/'out', '--tile', '128,128', '--width', 320, '--height', 200, '--joint-demo',
                   subtype, *extra)

    def test_every_tormenta_subtype_lives_moves_and_draws(self):
        for subtype in range(0x10, 0x1b):
            with self.subTest(subtype=hex(subtype)):
                j = self.session(subtype)['joints']
                self.assertIsNotNone(j)
                self.assertEqual((j['created'], j['unsupported'], j['full']), (3, 0, 0))   # steps 1, 21, 41
                self.assertEqual(j['live'], 1)       # LifeTime 20: the first two ended after 21 moves
                self.assertGreater(j['quads'], 0)    # two faces per tail segment, the bitmap present

    def test_bolts_create_their_start_flash(self):
        p = self.session(0x1a)['particles']
        self.assertGreater(p['sprites_created'], 0)   # Shiny02 at the start of every rebuilt bolt
        p = self.session(0x14)['particles']
        self.assertEqual(p['sprites_created'], 0)     # the rings create none

    def test_no_particles_has_no_joint_pool(self):
        self.assertIsNone(self.session(0x1a, '--no-particles')['joints'])

    def test_determinism(self):
        a = self.session(0x19, '--every', 15)
        b = self.session(0x19, '--every', 15)
        self.assertEqual(a['joints'], b['joints'])
        self.assertEqual([f['sha256'] for f in a['frames']], [f['sha256'] for f in b['frames']])


@unittest.skipUnless(PRIVATE and os.environ.get('MU_OBJECTS_PLAIN_DIR'),
                     'set MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT and MU_OBJECTS_PLAIN_DIR')
class InstalledTormentaJoints(unittest.TestCase):
    def test_lightning_and_tornado(self):
        subprocess.run(['make', '-C', str(NATIVE), 'all'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as out_dir:
            out = run(WALK, os.environ['MU_GAME_ROOT'], '--backend', 'soft', '--world', 141, '--tile', '82,19',
                      '--frames', 400, '--every', 1, '--out-dir', out_dir, '--width', 320, '--height', 200,
                      '--objects-dir', os.environ['MU_OBJECTS_PLAIN_DIR'])
        j, p = out['joints'], out['particles']
        self.assertEqual(p['bitmaps'][7:11], [1, 1, 1, 1])   # JointThunder01, Spark01, JointSpirit01, JointEnergy01
        self.assertGreater(j['created'], 10)
        self.assertEqual((j['unsupported'], j['full']), (0, 0))
        self.assertGreater(j['max_live'], 3)
        self.assertGreaterEqual(j['effects_created'], 1)      # the field tornado (type 9, rand % 500 == 1)
        self.assertEqual(j['effects_unsupported'], 0)
        self.assertGreater(p['sprites_created'], 0)           # the bolts' Shiny02 flashes


if __name__ == '__main__':
    unittest.main()
