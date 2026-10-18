"""Native character-select scene (NATIVE-CHARSEL-001) checks.

Portable (synthetic data only): a synthetic Data/World94 tree (v12-encrypted
map, attributes and its own camera record), a synthetic v15 Player.bmd, run
through `mu-charsel` / `mu-render charsel` (headless, software rasterizer):
  * the world-94 camera record drives the camera (scene-5 record path);
  * every list entry becomes a record with the client's CreateHero values
    (class body parts 0x3700.. + skin index, scale 1.7) and stands on marker 1
    with the marker's yaw 90;
  * only the selected character is drawn, with the two highlight decals and
    the particle; --cycle walks the GFx-style selection through the list;
  * Enter in the scene tick asks for the loading scene (reported);
  * frames are deterministic; malformed lists are refused.
`mu-charsel-window --headless` (OpenGL) is checked when SDL2 and an offscreen
context exist. Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the
installed World94 and class parts.
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
import native_fixtures as nf  # noqa: E402
from test_native_terrain import ozj_tga, v12_encrypt  # noqa: E402

CHARSEL = NATIVE / 'build/mu-charsel'
RENDER = NATIVE / 'build/mu-render'
WINDOW = NATIVE / 'build/mu-charsel-window'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def camera_ini(angle, position, fov, distance, z_distance):
    return (f'[CAMERA ANGLE]\r\nAngle X={angle[0]:.6f}\r\nAngle Y={angle[1]:.6f}\r\nAngle Z={angle[2]:.6f}\r\n'
            f'[CAMERA POSITION]\r\nPosition X={position[0]:.6f}\r\nPosition Y={position[1]:.6f}\r\n'
            f'Position Z={position[2]:.6f}\r\n'
            f'[CAMERA DISTANCE]\r\nDistance={distance:.6f}\r\nZ_Distance={z_distance:.6f}\r\n'
            f'[CAMERA FOV]\r\nFOV={fov:.6f}\r\n').encode()


CAMERA = ((-84.5, 0.0, -80.0), (12400.0, 12300.0, 529.0), 35.0, 9.1, 0.528)
MARKER = (11500.0, 12450.0)


def write_world94(root, seed=5):
    data = Path(root) / 'Data' / 'World94'
    data.mkdir(parents=True, exist_ok=True)
    layer1 = bytes((i * 7) % 3 for i in range(65536))
    (data / 'EncTerrain94.map').write_bytes(v12_encrypt(bytes([0, 94]) + layer1 + bytes([255]) * 65536 +
                                                        bytes(65536)))
    att = bytes([0, 94, 255, 255]) + bytes(2 * 65536)
    att = bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(att))
    (data / 'EncTerrain94.att').write_bytes(v12_encrypt(att))
    (data / 'TerrainHeight.OZB').write_bytes(b'BM8\x04' + bytes(0x438) + bytes([113]) * 65536)  # 1.5*113 = 169.5
    header = bytearray(54)
    struct.pack_into('<2sI', header, 0, b'BM', 54 + 3 * 65536)
    struct.pack_into('<III', header, 14, 40, 256, 256)
    (data / 'TerrainLight.OZB').write_bytes(b'BM6\0' + bytes(header) + bytes([180]) * (3 * 65536))
    (data / 'EncTerrain94.obj').write_bytes(v12_encrypt(bytes([0, 94, 0, 0])))
    for i, name in enumerate(('TileGrass01', 'TileGrass02', 'TileGround01')):
        (data / f'{name}.OZJ').write_bytes(ozj_tga(32, 32, seed + i))
    (data / 'Camera_Angle_Position.bmd').write_bytes(v12_encrypt(camera_ini(*CAMERA)))
    (Path(root) / 'Data' / 'G_Camera_Angle_Position.bmd').write_bytes(
        v12_encrypt(camera_ini((-48.5, 0, -45), (0, 0, 0), 39.0, 9.1, 0.179)))
    skill = Path(root) / 'Data' / 'Skill'
    skill.mkdir(parents=True, exist_ok=True)
    (skill / 'gmmzine.OZJ').write_bytes(ozj_tga(16, 16, seed + 9))
    player = Path(root) / 'Data' / 'Player'
    player.mkdir(parents=True, exist_ok=True)
    layout = nf.character_layout(seed, bones=50, actions=0x60, keys=(3, 2), dummies=(9, 21))
    (player / 'Player.bmd').write_bytes(nf.envelope_v15(layout))
    return root


def run(root, *args, tool=CHARSEL, check=True, prefix=()):
    result = subprocess.run([str(tool), *prefix, '--game-root', str(root), '--headless', *[str(a) for a in args]],
                            capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'{tool.name} failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    frames = [r for r in rows if 'frame' in r]
    summary = next((r for r in rows if r.get('summary')), None)
    entries = [r for r in rows if 'entry' in r]
    return frames, summary, entries, result


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_world94(Path(cls.tmp.name) / 'game')
        cls.marker = f'{MARKER[0]},{MARKER[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def out(self, name):
        return Path(self.tmp.name) / name


class CharselTests(Build):
    def test_camera_record_and_records(self):
        frames, summary, entries, _ = run(self.root, '--marker', self.marker, '--frames', '3', '--every', '1',
                                          '--width', '320', '--height', '200', '--out-dir', self.out('a'))
        self.assertEqual((summary['folder'], summary['camera_key']), (94, 94))
        self.assertEqual(summary['camera_angle'], [-84.5, 0.0, -80.0])
        last = frames[-1]
        self.assertEqual(last['angle'], [-84.5, 0.0, -80.0])
        self.assertEqual(last['eye'], [12400.0, 12300.0, 529.0])
        self.assertAlmostEqual(last['fov'], 35.0, places=4)
        self.assertAlmostEqual(last['far'], f32(f32(2400 * f32(9.1)) * f32(0.528)), places=1)
        self.assertEqual(len(entries), 5)
        for e in entries:
            skin = e['class'] & 0xf
            self.assertEqual(e['parts'], [-1, 0x3700 + skin, 0x3750 + skin, 0x37a0 + skin, 0x37f0 + skin,
                                          0x3840 + skin])
            self.assertAlmostEqual(e['scale'], 1.7, places=5)
        self.assertEqual([e['stand_action'] for e in entries], [1, 1, 2, 1, 1])   # SetPlayerStop per base class
        self.assertEqual(last['position'], [MARKER[0], MARKER[1], 169.5])
        self.assertEqual((last['selected'], last['shown'], last['drawn_entry']), (0, 0, 0))
        self.assertEqual((last['decals'], last['particles']), (2, 1))

    def test_selection_cycle_and_enter(self):
        frames, summary, _, _ = run(self.root, '--marker', self.marker, '--frames', '25', '--every', '1',
                                    '--cycle', '5', '--enter', '22', '--width', '160', '--height', '100',
                                    '--out-dir', self.out('b'))
        drawn = [f['drawn_entry'] for f in frames]
        self.assertEqual(drawn[:5], [0] * 5)
        self.assertEqual(drawn[5:10], [1] * 5)
        self.assertEqual(drawn[20:], [4] * 5)
        self.assertGreaterEqual(summary['enter_requests'], 1)
        self.assertEqual(frames[-1]['selected'], 4)
        # every list entry stands on marker 1
        self.assertEqual({tuple(f['position']) for f in frames}, {(MARKER[0], MARKER[1], 169.5)})

    def test_list_file_and_mu_render_alias(self):
        listing = self.out('list.txt')
        listing.write_text('# slot class level name\n3 0x21 400 Nighty\n7 0x02 12 Elfie\n')
        frames, summary, entries, _ = run(self.root, '--marker', self.marker, '--list', listing, '--slot', '7',
                                          '--frames', '2', '--every', '1', '--width', '160', '--height', '100',
                                          '--out-dir', self.out('c'), tool=RENDER, prefix=('charsel',))
        self.assertEqual([(e['slot'], e['class'], e['level'], e['name']) for e in entries],
                         [(3, 0x21, 400, 'Nighty'), (7, 2, 12, 'Elfie')])
        self.assertEqual(entries[0]['parts'][1], 0x3700 + 0x01 + 32)   # class 0x21: tier 3 skin
        self.assertEqual((frames[-1]['selected'], frames[-1]['drawn_entry']), (7, 1))

    def test_frames_are_deterministic(self):
        args = ('--marker', self.marker, '--frames', '12', '--every', '5', '--width', '200', '--height', '120')
        a, _, _, _ = run(self.root, *args, '--out-dir', self.out('d1'))
        b, _, _, _ = run(self.root, *args, '--out-dir', self.out('d2'))
        self.assertEqual([r['sha256'] for r in a], [r['sha256'] for r in b])
        self.assertTrue(all(r['sha256'] for r in a))

    def test_bad_inputs_are_refused(self):
        for text in ('10 1 1 X\n', '0 1 1\n', '0 1 1 A\n0 2 2 B\n', '0 1 1 A spear=x.bmd\n'):
            listing = self.out('bad.txt')
            listing.write_text(text)
            _, _, _, result = run(self.root, '--list', listing, '--frames', '1', check=False)
            self.assertNotEqual(result.returncode, 0, text)
        _, _, _, result = run(self.root, '--slot', '9', '--frames', '1', check=False)
        self.assertNotEqual(result.returncode, 0)
        _, _, _, result = run(self.root, '--backend', 'gl', '--frames', '1', check=False)
        self.assertEqual(result.returncode, 2)


class WindowToolTests(Build):
    def test_gl_headless(self):
        build = subprocess.run(['make', '-C', str(NATIVE), 'charsel'], capture_output=True, text=True)
        if build.returncode:
            self.skipTest('mu-charsel-window needs SDL2 and OpenGL: ' + build.stderr.strip()[-200:])
        frames, summary, _, result = run(self.root, '--marker', self.marker, '--backend', 'gl', '--frames', '3',
                                         '--every', '1', '--width', '160', '--height', '100', '--out-dir',
                                         self.out('gl'), tool=WINDOW, check=False)
        if result.returncode:
            self.skipTest('no offscreen OpenGL context: ' + result.stderr.strip()[-200:])
        self.assertEqual(frames[-1]['drawn_entry'], 0)
        self.assertNotEqual(summary['renderer'], 'software')


@unittest.skipUnless(PRIVATE, 'set MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT for the installed client')
class PrivateCharselTests(unittest.TestCase):
    def test_installed_scene(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            frames, summary, entries, _ = run(os.environ['MU_GAME_ROOT'], '--frames', '6', '--every', '5',
                                              '--width', '320', '--height', '200', '--out-dir', tmp)
            self.assertEqual((summary['folder'], summary['camera_key']), (94, 94))
            self.assertEqual(summary['camera_angle'], [-84.5, 0.0, -80.0])
            self.assertAlmostEqual(summary['fov'], 35.0, places=3)
            self.assertEqual(len(entries), 5)
            self.assertEqual(frames[-1]['decals'], 2)


if __name__ == '__main__':
    unittest.main()
