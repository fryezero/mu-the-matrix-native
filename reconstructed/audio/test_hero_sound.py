"""Checks for the hero footstep routines (NATIVE-WORLD-002, hero_sound.c).

Portable: the authored C against worked examples and the independent Python
statements in scripts/validate_hero_sound.py (PlayWalkSound 0x013b1f61, the
footstep trigger 0x013b8090, the foot reset 0x013a773c, HeroTile 0x016ad7a5).
Private (MU_RECOVERY_INTEGRATION=1): the Unicorn comparison against the
restored client instructions.
"""
import ctypes
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_hero_sound as vh  # noqa: E402  (no Unicorn at import time)

LIBRARY = HERE/('libclient_audio.dylib' if sys.platform == 'darwin' else 'libclient_audio.so')


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


class HeroSoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.lib = vh.load_library(LIBRARY)
        cls.grid = bytearray(0x20000)
        cls.grid_buffer = ctypes.create_string_buffer(bytes(cls.grid), len(cls.grid))

    def sound(self, attributes=None, **fields):
        case = {'world': 0, 'tile': 3, 'action': 0x32, 'safe': 0, 'x': 0, 'y': 0, 'manager': 0}
        case.update(fields)
        grid = attributes if attributes is not None else self.grid_buffer
        return vh.authored_walk_sound(self.lib, case, grid)

    def test_lorencia_grass_and_soil(self):
        self.assertEqual(self.sound(world=0, tile=0), 9)       # pWalk(Grass) on layer-1 tile 0
        self.assertEqual(self.sound(world=0, tile=3), 8)       # stone town tile: pWalk(Soil)
        self.assertEqual(self.sound(world=0, tile=4), 8)       # pub floor

    def test_devias_snow_except_tile_3_and_10_up(self):
        self.assertEqual(self.sound(world=2, tile=0), 10)
        self.assertEqual(self.sound(world=2, tile=9), 10)
        self.assertEqual(self.sound(world=2, tile=3), 8)
        self.assertEqual(self.sound(world=2, tile=10), 8)
        self.assertEqual(self.sound(world=2, tile=-5), 10)     # signed compare

    def test_water_worlds_swim_outside_the_safe_zone(self):
        for world in (7, 0x18, 0x1d, 0x24, 0x80, 0x82):
            self.assertEqual(self.sound(world=world, safe=0), 11, world)
            self.assertEqual(self.sound(world=world, safe=1), 8, world)
        self.assertEqual(self.sound(world=0x1e, safe=0), 8)

    def test_snow_worlds_and_the_swamp_bridge(self):
        for world in (0x39, 0x3a, 0x79, 0x3e):
            self.assertEqual(self.sound(world=world), 10, world)
        grid = bytearray(0x20000)
        struct.pack_into('<H', grid, 2*((7 << 8) + 300 % 256), 0x8000)
        buffer = ctypes.create_string_buffer(bytes(grid), len(grid))
        self.assertEqual(self.sound(buffer, world=0x7a, x=300, y=7), 0x4d1)
        self.assertEqual(self.sound(buffer, world=0x7a, x=7, y=300), 8)

    def test_gates(self):
        for action in range(0x59, 0x60):
            self.assertEqual(self.sound(action=action, tile=0), -1)
        self.assertEqual(self.sound(manager=1, tile=0), -1)
        self.assertEqual(self.sound(action=0x58, tile=0), 9)

    def test_trigger_and_reset_give_two_steps_per_walk_cycle(self):
        foot = (ctypes.c_uint8*2)(0, 0)
        field = ctypes.c_int32(5)
        frame, played = 0.0, []
        for step in range(40):   # walk 0x32 at 0.33 per step over an 8-key cycle
            frame = f32(frame + 0.33)
            wrapped = frame >= 8.0
            if wrapped:
                frame = f32(frame - 8.0)
            self.lib.mu_footstep_reset(0 if wrapped else 1, foot, ctypes.byref(field))
            calls = self.lib.mu_footstep_trigger(0xa91, 1, 0x32, frame, foot)
            played += [step]*calls
        self.assertEqual(field.value, -1)
        self.assertEqual(len(played), 2*int(40*0.33/8) + 2)   # two per cycle, the third cycle started
        self.assertEqual(self.lib.mu_footstep_trigger(0xa91, 0, 0x32, 5.0, foot), 0)   # not the hero
        foot[0] = foot[1] = 0
        self.assertEqual(self.lib.mu_footstep_trigger(0x7a5, 1, 0x32, 5.0, foot), 0)   # not the Player model
        self.assertEqual(self.lib.mu_footstep_trigger(0xa91, 1, 0x01, 5.0, foot), 0)   # standing
        self.assertEqual(self.lib.mu_footstep_trigger(0xa91, 1, 0x6f, 5.0, foot), 0)   # first action past runs
        self.assertEqual(self.lib.mu_footstep_trigger(0xa91, 1, 0x6e, 5.0, foot), 2)
        foot[0] = foot[1] = 0
        self.assertEqual(self.lib.mu_footstep_trigger(0xa91, 1, 0x32, float('nan'), foot), 0)

    def test_hero_tile_truncates_and_clamps(self):
        layer = bytes(range(256))*256
        buffer = ctypes.create_string_buffer(layer, len(layer))
        self.assertEqual(self.lib.mu_hero_tile_index(13350.0, 12750.0), (127 << 8) + 133)
        self.assertEqual(self.lib.mu_hero_tile_index(-50.0, 500.0), (5 << 8) + 0)      # -50 -> 0
        self.assertEqual(self.lib.mu_hero_tile_index(-150.0, 500.0), (5 << 8) - 1)     # -150 -> -1, not floor -2
        self.assertEqual(self.lib.mu_hero_tile_index(500.0, -150.0), 0)                 # negative index
        self.assertEqual(self.lib.mu_hero_tile_index(1e6, 1e6), 0xffff)
        self.assertEqual(self.lib.mu_hero_tile_index(float('nan'), 100.0), 0)           # 0x80000000 / 100
        self.assertEqual(self.lib.mu_hero_tile(buffer, 13350.0, 12750.0), 133)

    def test_python_statements_agree_on_random_cases(self):
        rng = random.Random(7)
        grids = [vh.attribute_grid(rng)]
        buffer = ctypes.create_string_buffer(grids[0], len(grids[0]))
        for case in vh.walk_sound_cases(rng, 400, grids):
            self.assertEqual(vh.authored_walk_sound(self.lib, case, buffer), vh.model_sound(case), case['world'])
        for case in vh.trigger_cases(rng, 400, grids):
            foot = (ctypes.c_uint8*2)(*case['foot'])
            calls = self.lib.mu_footstep_trigger(case['type'], case['is_hero'], case['action'], case['frame'], foot)
            self.assertEqual((list(foot), calls), vh.model_trigger(case))
        for case in vh.tile_cases(rng, 400):
            layer = ctypes.create_string_buffer(case['layer1'], 0x10000)
            self.assertEqual(self.lib.mu_hero_tile(layer, case['px'], case['py']), vh.model_tile(case))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Unicorn comparison against the restored client is opt-in')
    def test_unicorn_comparison(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        if not text.exists() or not data.exists():
            self.skipTest('restored text or image data not present')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_hero_sound.py'), '--text', str(text),
                                 '--data', str(data), '--cases', '600'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ALL PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
