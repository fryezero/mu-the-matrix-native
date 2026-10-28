"""The legacy particles, sprites and blob shadows in the walk-around session (NATIVE-PARTICLE-001).

Portable (synthetic data only), through `mu-walk` (headless, software rasterizer) on the synthetic world 0 of
test_native_world.py with a synthetic FireLight01 object (CreateFire every step), synthetic Bird01 (blob
shadows of RenderBoids) and a synthetic Effect/Fire01:
  * CreateParticle from the object move pass fills the particle list, MoveParticles ages it, the sprite pass
    draws the live particles (the bitmap exists) and nothing is unsupported;
  * blob shadows are drawn (the hero's parts and the visible birds);
  * --no-particles keeps the former stand-in path (no particle module, the object runtime's own list);
  * runs are deterministic.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_OBJECTS_PLAIN_DIR with the local EncTerrain1.plain):
the installed Lorencia at the fires of 146,110 creates, moves and draws Fire01 particles with every bitmap
loaded.
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
from test_native_objects import convert, snapshot, write_models  # noqa: E402
from test_native_terrain import ozj_tga  # noqa: E402
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def ozj_jpeg(width, height):
    """A small JPEG under the 24-byte OZJ prefix (PIL when available, else the TGA variant, which the JPEG
    path refuses)."""
    try:
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new('RGB', (width, height), (250, 140, 40)).save(buf, 'JPEG')
        payload = buf.getvalue()
        return payload[:24] + payload
    except ImportError:
        return ozj_tga(width, height, 5)


def run(root, *args, check=True):
    result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                             '--quiet', *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'frame' in r and 'tick' in r],
            'particles': next((r for r in rows if r.get('particles') is True), None),
            'objects': next((r for r in rows if 'objects' in r and 'objects_created' in r), None)}


class ParticleSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_open_world(Path(cls.tmp.name)/'game')
        write_models(cls.root, 1, ['FireLight01.bmd'])
        objects = cls.root/'Data'/'Object1'
        (objects/'Bird01.bmd').write_bytes(nf.synthetic_layout(21, actions=2, keys=(4, 3)))
        effect = cls.root/'Data'/'Effect'
        effect.mkdir(parents=True, exist_ok=True)
        (effect/'Fire01.OZJ').write_bytes(ozj_jpeg(32, 16))
        snap = Path(cls.tmp.name)/'snap.bin'
        snapshot(snap, 0, [(0x32, (12850.0, 12850.0, 60.0), (0.0, 0.0, 0.0), 1.0, -1)])
        cls.plain = Path(cls.tmp.name)/'plain'
        cls.plain.mkdir()
        convert(snap, cls.plain/'EncTerrain1.plain', '--version', 0)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def session(self, *extra):
        return run(self.root, '--frames', 40, '--every', 40, '--out-dir', Path(self.tmp.name)/'out', '--tile',
                   '128,128', '--width', 320, '--height', 200, '--objects-dir', self.plain, *extra)

    def test_fire_particles_are_created_moved_and_drawn(self):
        out = self.session()
        p = out['particles']
        self.assertIsNotNone(p)
        self.assertGreater(p['created'], 0)
        self.assertEqual((p['unsupported'], p['overflow'], p['dropped']), (0, 0, 0))
        self.assertEqual(p['steps'], 40)
        self.assertGreater(p['live'], 0)
        self.assertLessEqual(p['live'], p['created'])
        # Effect/Fire01 loads where the build has JPEG support (the fixture is a JPEG); then every live particle
        # is drawn, otherwise none (the client would read through a missing bitmap record)
        self.assertEqual(p['drawn_particles'], p['live'] if p['bitmaps'][0] else 0)
        self.assertEqual(out['objects']['object_particles'], p['created'] + p['dropped'] + p['unsupported'])
        self.assertGreater(p['visuals'], 0)                   # RenderObjectVisual ran for the drawn object

    def test_shadows(self):
        p = self.session()['particles']
        self.assertGreaterEqual(p['shadows'], 1)              # the hero's parts at least
        self.assertGreater(p['shadow_vertices'], 0)

    def test_no_particles_keeps_the_stand_in(self):
        out = self.session('--no-particles')
        self.assertIsNone(out['particles'])
        self.assertGreater(out['objects']['object_particles'], 0)

    def test_determinism(self):
        a, b = self.session(), self.session()
        self.assertEqual(a['particles'], b['particles'])
        self.assertEqual([f['particles'] for f in a['frames']], [f['particles'] for f in b['frames']])
        self.assertEqual([f['sha256'] for f in a['frames']], [f['sha256'] for f in b['frames']])


@unittest.skipUnless(PRIVATE and os.environ.get('MU_OBJECTS_PLAIN_DIR'),
                     'set MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT and MU_OBJECTS_PLAIN_DIR')
class InstalledLorenciaFires(unittest.TestCase):
    def test_fires(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as out_dir:
            out = run(os.environ['MU_GAME_ROOT'], '--world', 0, '--tile', '146,110', '--frames', 30, '--every', 30,
                      '--out-dir', out_dir, '--width', 320, '--height', 200, '--objects-dir',
                      os.environ['MU_OBJECTS_PLAIN_DIR'])
        p = out['particles']
        # The registered bank includes the later helper, terrain, Icarus and world-warp textures.
        # Keep the complete bank check: a missing installed bitmap must still fail.
        self.assertEqual(p['bitmaps'], [1]*51)
        self.assertGreater(p['created'], 20)
        self.assertEqual(p['unsupported'], 0)
        self.assertGreater(p['drawn_particles'], 0)


if __name__ == '__main__':
    unittest.main()
