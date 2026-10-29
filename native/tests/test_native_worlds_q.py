"""RENDER-WORLDS-Q native checks.

Production host: Acheron, Ferea, Swamp of Darkness and Kubera Mine populations through creation, steps
and the primary visual (sibling world 111 unchanged). Terrain: a synthetic World124 holding only one
elemental light file loads it exactly for its Kubera world (0x00e18e27's names).
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the installed Kubera worlds load their light files.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import test_native_terrain as tt  # noqa: E402

ELEMENTS = {123: 'Fire', 124: 'Water', 125: 'Earth', 126: 'Wind', 127: 'Dark'}


def info(root, world):
    return json.loads(tt.run('info', root, '--world', world).stdout)


class WorldsQ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/mu-terrain', 'build/worlds-q-host'], check=True,
                       capture_output=True)

    def test_production_host(self):
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two actions of two keys, no meshes.
            chunks = [b'BMD\x0a', b'worlds-q'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 2),
                      struct.pack('<hB', 2, 0) * 2, b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1)]
            chunks += [struct.pack('<6f', 0, 2, 3, 4, 2, 3), bytes(24)] * 2
            model = Path(td) / 'q.bmd'
            model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE / 'build/worlds-q-host'), str(model)], check=True)

    def test_kubera_elemental_light(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = tt.write_world(root, 124, seed=5, rgb=True)
            light = (data / 'TerrainLight.OZB').read_bytes()
            (data / 'TerrainLight.OZB').unlink()
            for world, element in ELEMENTS.items():
                path = data / f'TerrainLight_{element}.OZB'
                path.write_bytes(light)
                status = {w: info(root, w)['light_status'] for w in ELEMENTS}
                self.assertEqual(status, {w: 0 if w == world else -1 for w in ELEMENTS})
                path.unlink()
            (data / 'TerrainLight.OZB').write_bytes(light)   # the plain file is not a Kubera light
            self.assertEqual({info(root, w)['light_status'] for w in ELEMENTS}, {-1})

    @unittest.skipUnless(tt.PRIVATE and os.environ.get('MU_GAME_ROOT'), 'installed-data check is opt-in')
    def test_installed_kubera_lights(self):
        root = os.environ['MU_GAME_ROOT']
        for w in ELEMENTS:
            self.assertEqual(info(root, w)['light_status'], 0)


if __name__ == '__main__':
    unittest.main()
