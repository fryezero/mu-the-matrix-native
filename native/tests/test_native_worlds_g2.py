"""OpenTexture's name map / Item retries over a synthetic game root, and the Vulcanus far plane (RENDER-WORLDS-G2)."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE / 'tests'))
import native_fixtures as fx  # noqa: E402


def model(path, names, seed):
    layout = fx.synthetic_layout(seed, texture_names=names)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(layout)


def texture(path, seed):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fx.ozt(fx.tga(8, 8, seed)))


class WorldsG2Host(unittest.TestCase):
    def test_name_map_item_retries_and_far_plane(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-g2-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / 'Data'
            # a startup model (0x01832af3 opens Skeleton01 with "Skill\\") and Deep Dungeon's preloaded wall model
            model(data / 'Skill/Skeleton01.bmd', ['probe.tga', 'skin_a.tga', 'cloth.tga'], 3)
            texture(data / 'Skill/probe.OZT', 1)
            model(data / 'Object2/DungeonStone01.bmd', ['wallx.tga', 'a.tga', 'b.tga'], 4)
            texture(data / 'Object2/wallx.OZT', 2)
            texture(data / 'Object117/direct.OZT', 3)
            texture(data / 'Item/itemonly.OZT', 4)
            texture(data / 'Item/Texture/deep.OZT', 5)
            run = subprocess.run([str(NATIVE / 'build/worlds-g2-host'), td], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)


if __name__ == '__main__':
    unittest.main()
