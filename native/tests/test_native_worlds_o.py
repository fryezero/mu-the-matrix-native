"""RENDER-WORLDS-O native checks.

Portable: a synthetic Data tree where only World129 (Abyss of Atlans 1) holds tile
bitmaps. Worlds 129 and 130 (folders 130/131) load and draw them through the
original folder rule of 0x01829457; world 131 (folder 132) keeps its own empty
folder. The production object host hides type 39 in the Abyss visual and keeps
other worlds' visuals unchanged.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the installed Abyss worlds load
their tiles from World129.
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


def info(root, world):
    return json.loads(tt.run('info', root, '--world', world).stdout)


def render(root, world):
    return json.loads(tt.run('render', root, '--world', world, '--width', 96, '--height', 64, '--time', 50).stdout)


class AbyssTileFolder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/mu-terrain', 'build/worlds-o-host'], check=True,
                       capture_output=True)

    def test_abyss_2_and_3_take_the_tiles_of_world129(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tt.write_world(root, 129, seed=3, rgb=True)
            for folder in (130, 131, 132):
                data = tt.write_world(root, folder, seed=folder, rgb=True)
                for tile in list(data.glob('Tile*')):
                    tile.unlink()
            reports = {w: info(root, w) for w in (128, 129, 130, 131)}
            for w in (128, 129, 130):
                self.assertEqual((reports[w]['folder'], reports[w]['tile_folder']), (w + 1, 129))
                self.assertGreaterEqual(reports[w]['bitmaps_loaded'], 9)
                self.assertEqual(reports[w]['bitmaps_loaded'], reports[128]['bitmaps_loaded'])
            self.assertEqual((reports[131]['folder'], reports[131]['tile_folder'], reports[131]['bitmaps_loaded']),
                             (132, 132, 0))
            # The synthetic layers also use tile indexes without a file, so status stays "unsupported" (4)
            # as for world 128; every face of 129/130 is textured, none of 131's.
            abyss1 = render(root, 128)
            for w in (129, 130):
                frame = render(root, w)
                self.assertEqual((frame['faces'], frame['missing_texture_binds']), (abyss1['faces'], 0))
                self.assertGreater(frame['faces'], 60000)
            self.assertEqual(render(root, 131)['faces'], 0)

    def test_production_visual_hides_type_39_only_in_abyss(self):
        with tempfile.TemporaryDirectory() as td:
            chunks = [b'BMD\x0a', b'worlds-o'.ljust(32, b'\0'), struct.pack('<HHH', 0, 2, 1), struct.pack('<hB', 2, 0)]
            for bone in range(2):
                chunks += [b'\0' + f'bone{bone}'.encode().ljust(32, b'\0') + struct.pack('<h', -1),
                           struct.pack('<6f', bone, 2, 3, bone + 4, 2, 3), bytes(24)]
            model = Path(td)/'abyss.bmd'
            model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE/'build/worlds-o-host'), str(model)], check=True)

    @unittest.skipUnless(tt.PRIVATE and os.environ.get('MU_GAME_ROOT'), 'installed-data check is opt-in')
    def test_installed_abyss_worlds(self):
        root = os.environ['MU_GAME_ROOT']
        loaded = {w: info(root, w) for w in (128, 129, 130)}
        for w, r in loaded.items():
            self.assertEqual(r['tile_folder'], 129)
            self.assertEqual(r['bitmaps_loaded'], loaded[128]['bitmaps_loaded'])
            self.assertGreater(r['bitmaps_loaded'], 14)
