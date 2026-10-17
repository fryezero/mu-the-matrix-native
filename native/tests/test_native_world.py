"""Native walk-around session (NATIVE-WORLD-001) checks.

Portable (synthetic data only): a synthetic Data/World1 tree (v12-encrypted
map and attributes, flat open ground with a safe-zone strip), a synthetic v15
Player.bmd with 0x60 actions and v12-encrypted camera records, run through
`mu-walk` (headless, software rasterizer):
  * a scripted click goes through the window-procedure mouse globals, the
    client pick and the path, and the hero walks there at the client's walk
    speed and stops on the clicked tile;
  * walk action 0x32 while moving, stand action 1 after the arrival;
  * the camera record of the world folder is used (else the global one), with
    its FOV and far plane 2000 * Distance * Z_Distance;
  * the wheel zooms to FOV 30 in the client's 500 ms transition;
  * frames are deterministic.
`mu-world --headless` (OpenGL) is checked when SDL2 and an offscreen context
exist. Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): a walk across
Lorencia town with the installed data.
"""
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_terrain import ozj_tga, v12_encrypt  # noqa: E402

WALK = NATIVE / 'build/mu-walk'
WORLD = NATIVE / 'build/mu-world'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def camera_ini(fov, distance, z_distance):
    return (f'[CAMERA ANGLE]\r\nAngle X=-48.500000\r\nAngle Y=0.000000\r\nAngle Z=-45.000000\r\n'
            f'[CAMERA POSITION]\r\nPosition X=0.000000\r\nPosition Y=0.000000\r\nPosition Z=0.000000\r\n'
            f'[CAMERA DISTANCE]\r\nDistance={distance:.6f}\r\nZ_Distance={z_distance:.6f}\r\n'
            f'[CAMERA FOV]\r\nFOV={fov:.6f}\r\n').encode()


def write_open_world(root, *, per_world_camera=True, seed=3):
    """Flat ground at height 1.5*40, open attributes, a safe-zone strip at y 100..110."""
    g = random.Random(seed)
    data = Path(root) / 'Data' / 'World1'
    data.mkdir(parents=True, exist_ok=True)
    layer1 = bytes(g.choice((0, 2)) for _ in range(65536))
    alpha = bytes(65536)
    layer2 = bytes([255]) * 65536
    (data / 'EncTerrain1.map').write_bytes(v12_encrypt(bytes([0, 1]) + layer1 + layer2 + alpha))
    cells = [1 if 100 <= (i >> 8) <= 110 else 0 for i in range(65536)]
    for x in range(60, 200):          # a wall line the path stops at
        cells[150 * 256 + x] = 4
    att = bytes([0, 1, 255, 255]) + b''.join(struct.pack('<H', c) for c in cells)
    att = bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(att))
    (data / 'EncTerrain1.att').write_bytes(v12_encrypt(att))
    (data / 'TerrainHeight.OZB').write_bytes(b'BM8\x04' + bytes(0x438) + bytes([40]) * 65536)
    header = bytearray(54)
    struct.pack_into('<2sI', header, 0, b'BM', 54 + 3 * 65536)
    struct.pack_into('<III', header, 14, 40, 256, 256)
    (data / 'TerrainLight.OZB').write_bytes(b'BM6\0' + bytes(header) + bytes([200]) * (3 * 65536))
    (data / 'EncTerrain1.obj').write_bytes(v12_encrypt(bytes([0, 1, 0, 0])))
    for i, name in enumerate(('TileGrass01', 'TileGrass02', 'TileGround01')):
        (data / f'{name}.OZJ').write_bytes(ozj_tga(32, 32, seed + i))
    (Path(root) / 'Data' / 'G_Camera_Angle_Position.bmd').write_bytes(v12_encrypt(camera_ini(39.0, 9.1, 0.179)))
    if per_world_camera:
        (data / 'Camera_Angle_Position.bmd').write_bytes(v12_encrypt(camera_ini(37.0, 10.1, 0.2)))
    player = Path(root) / 'Data' / 'Player'
    player.mkdir(parents=True, exist_ok=True)
    layout = nf.character_layout(seed, bones=50, actions=0x60, keys=(3, 2), dummies=(9, 21))
    (player / 'Player.bmd').write_bytes(nf.envelope_v15(layout))
    return root


def walk(root, *args, tool=WALK, check=True):
    result = subprocess.run([str(tool), '--game-root', str(root), '--headless', *[str(a) for a in args]],
                            capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'{tool.name} failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    frames = [r for r in rows if 'frame' in r]
    summary = next(r for r in rows if r.get('summary'))
    logs = [r['log'] for r in rows if 'log' in r]
    return frames, summary, logs, result


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_open_world(Path(cls.tmp.name) / 'game')
        cls.fallback = write_open_world(Path(cls.tmp.name) / 'game2', per_world_camera=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class WalkTests(Build):
    def test_click_walks_to_the_tile_at_the_client_speed(self):
        frames, summary, logs, _ = walk(self.root, '--backend', 'soft', '--tile', '120,120', '--walk', '124,123',
                                        '--frames', '90', '--every', '1', '--width', '320', '--height', '200',
                                        '--out-dir', Path(self.tmp.name) / 'a')
        self.assertEqual((summary['moves'], summary['arrivals']), (1, 1), logs)
        self.assertIn('click-to-move: tile 124,123 (5 cells)', logs)
        self.assertIn('arrived: tile 124,123', logs)
        last = frames[-1]
        self.assertEqual(last['tile'], [124, 123])
        self.assertEqual(last['hero'][:2], [12450.0, 12350.0])
        self.assertEqual(last['moving'], 0)
        self.assertEqual(last['hero'][2], 60.0)           # RequestTerrainHeight of the flat 1.5 * 40 ground
        self.assertAlmostEqual(summary['units_per_step'], 12.0, places=3)   # CharacterMoveSpeed 12, run < 40
        moving = [f for f in frames if f['moving']]
        self.assertTrue(moving)
        # the click starts the move after MoveHero's walk branch: the walk action follows one step later
        self.assertEqual(moving[0]['action'], 1)
        self.assertEqual({f['action'] for f in moving[1:]}, {0x32})
        self.assertEqual(last['action'], 1)
        self.assertEqual({f['safe'] for f in frames}, {0})
        self.assertEqual({f['run'] for f in moving}, {0})  # class 1 outside the safe zone: no run growth

    def test_class_3_starts_running_after_40_steps(self):
        frames, summary, logs, _ = walk(self.root, '--backend', 'soft', '--class', '3', '--tile', '120,40',
                                        '--walk', '120,54', '--frames', '120', '--every', '1', '--width', '160',
                                        '--height', '100', '--out-dir', Path(self.tmp.name) / 'b')
        moving = [f for f in frames if f['moving']][1:]
        actions = [f['action'] for f in moving]
        self.assertIn(0x32, actions)
        self.assertIn(0x4f, actions)                      # run action once the counter reaches 40
        self.assertEqual(actions.index(0x4f), [f['run'] for f in moving].index(40))

    def test_safe_zone_resets_the_run_counter(self):
        frames, _, _, _ = walk(self.root, '--backend', 'soft', '--class', '3', '--tile', '120,103', '--walk',
                               '126,103', '--frames', '60', '--every', '1', '--width', '160', '--height', '100',
                               '--out-dir', Path(self.tmp.name) / 'c')
        self.assertEqual({f['safe'] for f in frames}, {1})
        self.assertEqual({f['run'] for f in frames}, {0})

    def test_path_stops_before_a_wall(self):
        frames, summary, logs, _ = walk(self.root, '--backend', 'soft', '--tile', '120,145', '--walk', '120,155',
                                        '--frames', '60', '--every', '1', '--width', '160', '--height', '100',
                                        '--out-dir', Path(self.tmp.name) / 'd')
        self.assertEqual(frames[-1]['tile'], [120, 149], logs)   # attribute 4 >= wall mode 2 blocks

    def test_camera_records(self):
        frames, summary, _, _ = walk(self.root, '--backend', 'soft', '--frames', '3', '--every', '1', '--width',
                                     '160', '--height', '100', '--out-dir', Path(self.tmp.name) / 'e')
        self.assertEqual((summary['camera_key'], summary['world_fov']), (1, 37.0))
        self.assertAlmostEqual(frames[-1]['far'], f32(f32(2000 * f32(10.1)) * f32(0.2)), places=2)
        self.assertAlmostEqual(frames[-1]['fov'], 37.0, places=4)
        frames, summary, _, _ = walk(self.fallback, '--backend', 'soft', '--frames', '3', '--every', '1',
                                     '--width', '160', '--height', '100', '--out-dir', Path(self.tmp.name) / 'f')
        self.assertEqual((summary['camera_key'], summary['world_fov']), (0, 39.0))
        self.assertAlmostEqual(frames[-1]['far'], f32(f32(2000 * f32(9.1)) * f32(0.179)), places=2)

    def test_wheel_zoom(self):
        frames, _, _, _ = walk(self.fallback, '--backend', 'soft', '--wheel', '3:1', '--frames', '30', '--every',
                               '1', '--width', '160', '--height', '100', '--out-dir', Path(self.tmp.name) / 'g')
        self.assertAlmostEqual(frames[2]['fov'], 39.0, places=4)
        self.assertAlmostEqual(frames[-1]['fov'], 30.0, places=4)
        self.assertLess(frames[-1]['pitch'], -48.5)

    def test_frames_are_deterministic(self):
        args = ('--backend', 'soft', '--tile', '120,120', '--walk', '124,121', '--frames', '40', '--every', '13',
                '--width', '200', '--height', '120')
        a, _, _, _ = walk(self.root, *args, '--out-dir', Path(self.tmp.name) / 'h1')
        b, _, _, _ = walk(self.root, *args, '--out-dir', Path(self.tmp.name) / 'h2')
        self.assertEqual([r['sha256'] for r in a], [r['sha256'] for r in b])
        self.assertTrue(all(r['sha256'] for r in a))

    def test_bad_inputs_are_refused(self):
        result = subprocess.run([str(WALK), '--game-root', str(Path(self.tmp.name) / 'missing'), '--headless'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        result = subprocess.run([str(WALK), '--game-root', str(self.root), '--headless', '--tile', '300,1'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        result = subprocess.run([str(WALK), '--game-root', str(self.root), '--headless', '--backend', 'gl'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


class WindowToolTests(Build):
    def test_gl_headless(self):
        build = subprocess.run(['make', '-C', str(NATIVE), 'world'], capture_output=True, text=True)
        if build.returncode:
            self.skipTest('mu-world needs SDL2 and OpenGL: ' + build.stderr.strip()[-200:])
        frames, summary, logs, result = walk(self.root, '--backend', 'gl', '--tile', '120,120', '--walk', '124,121',
                                             '--frames', '50', '--every', '25', '--width', '320', '--height', '200',
                                             '--out-dir', Path(self.tmp.name) / 'gl', tool=WORLD, check=False)
        if result.returncode and 'headless GL' in result.stderr:
            self.skipTest('no offscreen GL context: ' + result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary['arrivals'], 1)
        self.assertEqual(frames[-1]['tile'], [124, 121])


@unittest.skipUnless(PRIVATE, 'private: needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateLorenciaTests(unittest.TestCase):
    def test_walk_across_lorencia_town(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        root = os.environ['MU_GAME_ROOT']
        with tempfile.TemporaryDirectory() as folder:
            frames, summary, logs, _ = walk(root, '--backend', 'soft', '--tile', '133,127', '--walk',
                                            '138,128 143,134 140,140', '--frames', '260', '--every', '65',
                                            '--width', '320', '--height', '200', '--out-dir', folder)
        self.assertEqual((summary['folder'], summary['camera_key']), (1, 0))   # Lorencia uses the global record
        self.assertEqual(summary['world_fov'], 39.0)
        self.assertAlmostEqual(summary['distance'], 9.1, places=5)
        self.assertAlmostEqual(summary['z_distance'], 0.179, places=5)
        self.assertGreaterEqual(summary['arrivals'], 3, logs)
        self.assertEqual({f['safe'] for f in frames}, {1})              # Lorencia town is a safe zone
        self.assertAlmostEqual(summary['units_per_step'], 12.0, places=3)


if __name__ == '__main__':
    unittest.main()
