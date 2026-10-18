"""Native login scene (NATIVE-LOGIN-001) checks.

Portable (synthetic data only): a synthetic Data/World95 tree (v12-encrypted map, attributes and its own camera
record), synthetic Object95 models and a decoded-layout EncTerrain95.plain, through `mu-render ui login --scene`
and `mu-shell` (headless, software rasterizer):
  * the World95 camera record drives the camera (scene-3 record path) and CameraViewFar is
    2400 * Distance * Z_Distance in binary32;
  * CreateObject runs the login world's handler: the ship (type 5) and type 0xd become after-character objects,
    the hidden types 0x26/0x36 are not drawn; the ship's RenderObjectVisual creates its ten lantern sprites;
  * the object animation advances with the logic steps; frames are deterministic;
  * without objects the terrain alone is drawn; mu-shell draws the world behind the server list.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT and MU_OBJECTS_PLAIN_DIR with the local EncTerrain95.plain): the
installed World95 with the live placements (camera and far plane equal to the live read).
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
from test_native_charsel import camera_ini  # noqa: E402
from test_native_objects import obj_plain, write_models  # noqa: E402

RENDER = NATIVE / 'build/mu-render'
SHELL = NATIVE / 'build/mu-shell'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
PLAIN = os.environ.get('MU_OBJECTS_PLAIN_DIR')

CAMERA = ((-84.5, 0.0, -45.0), (14000.0, 11000.0, 600.0), 35.0, 32.1, 0.325)
# type, x, y, z, angle, scale: in front of the camera (it looks along +x -y rotated by -45 degrees: toward -x, +y)
RECORDS = [(5, 12000.0, 12600.0, 200.0, 30.0, 8.0), (1, 11500.0, 13000.0, 190.0, 0.0, 8.0),
           (13, 11000.0, 13400.0, 150.0, 0.0, 8.0), (0x26, 11800.0, 12900.0, 169.0, 0.0, 1.0),
           (2, 10500.0, 14200.0, 200.0, 0.0, 12.0)]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def write_world95(root, seed=7):
    data = Path(root) / 'Data' / 'World95'
    data.mkdir(parents=True, exist_ok=True)
    layer1 = bytes((i * 5) % 3 for i in range(65536))
    (data / 'EncTerrain95.map').write_bytes(v12_encrypt(bytes([0, 95]) + layer1 + bytes([255]) * 65536 +
                                                        bytes(65536)))
    att = bytes([0, 95, 255, 255]) + bytes(2 * 65536)
    att = bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(att))
    (data / 'EncTerrain95.att').write_bytes(v12_encrypt(att))
    (data / 'TerrainHeight.OZB').write_bytes(b'BM8\x04' + bytes(0x438) + bytes([100]) * 65536)
    header = bytearray(54)
    struct.pack_into('<2sI', header, 0, b'BM', 54 + 3 * 65536)
    struct.pack_into('<III', header, 14, 40, 256, 256)
    (data / 'TerrainLight.OZB').write_bytes(b'BM6\0' + bytes(header) + bytes([200]) * (3 * 65536))
    (data / 'EncTerrain95.obj').write_bytes(v12_encrypt(bytes([0, 95, 0, 0])))
    for i, name in enumerate(('TileGrass01', 'TileGrass02', 'TileGround01')):
        (data / f'{name}.OZJ').write_bytes(ozj_tga(32, 32, seed + i))
    (data / 'Camera_Angle_Position.bmd').write_bytes(v12_encrypt(camera_ini(*CAMERA)))
    (Path(root) / 'Data' / 'G_Camera_Angle_Position.bmd').write_bytes(
        v12_encrypt(camera_ini((-48.5, 0, -45), (0, 0, 0), 39.0, 9.1, 0.179)))
    write_models(root, 95, ['Object02.bmd', 'Object03.bmd', 'Object06.bmd', 'Object14.bmd', 'Object39.bmd'])
    plain = Path(root) / 'plain'
    plain.mkdir(exist_ok=True)
    (plain / 'EncTerrain95.plain').write_bytes(obj_plain(95, RECORDS))
    return plain


def login(root, *args, objects=None):
    command = [str(RENDER), 'ui', 'login', '--root', str(root), '--scene', '--no-ui', '--size', '320x200']
    if objects:
        command += ['--objects-dir', str(objects)]
    result = subprocess.run(command + [str(a) for a in args], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-render ui login failed: {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    scene = next(r for r in rows if 'camera_angle' in r)
    frame = next(r for r in rows if r.get('screen') == 'login')
    return scene, frame


class LoginSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'root'
        cls.plain = write_world95(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_camera_record_and_far_plane(self):
        scene, _ = login(self.root, '--out', Path(self.tmp.name) / 'terrain.png', objects=Path(self.tmp.name) / 'none')
        self.assertEqual(scene['world'], 0x5e)
        self.assertEqual(scene['camera_angle'], [-84.5, 0, -45])
        self.assertEqual(scene['camera_position'], [14000.0, 11000.0, 600.0])
        self.assertEqual(scene['fov'], 35)
        far = f32(f32(f32(2400.0) * f32(32.1)) * f32(0.325))   # 0x0098ac45, the manager's scale 1.0
        self.assertAlmostEqual(scene['view_far'], far, places=2)
        self.assertEqual(scene['objects'], 0)                  # no plaintext: terrain only

    def test_login_world_objects(self):
        out = Path(self.tmp.name) / 'objects.png'
        scene, frame = login(self.root, '--out', out, objects=self.plain)
        self.assertEqual((scene['objects'], scene['objects_created']), (5, 5))
        self.assertEqual(scene['after_character'], 2)          # the ship and type 0xd (custom render +0xa = 1)
        self.assertEqual(scene['sprites'], 10)                  # the ship's lantern sprites (slot 0x34)
        self.assertEqual(scene['draw_list'], 5)
        self.assertEqual(scene['objects_drawn'], 4)             # type 0x26 is HiddenMesh -2
        self.assertGreater(scene['after_meshes'], 0)
        again, frame2 = login(self.root, '--out', out, objects=self.plain)
        self.assertEqual(frame['framebuffer_sha256'], frame2['framebuffer_sha256'])
        _, frame3 = login(self.root, '--out', out, '--steps', 3, objects=self.plain)
        self.assertNotEqual(frame['framebuffer_sha256'], frame3['framebuffer_sha256'])   # time moves the scene

    def test_shell_draws_the_world_behind_the_server_list(self):
        sys.path.insert(0, str(HERE))
        from test_native_shell import write_root, write_session
        shell_root = Path(self.tmp.name) / 'shell'
        write_root(shell_root)
        write_world95(shell_root)
        session = write_session(Path(self.tmp.name))
        out = Path(self.tmp.name) / 'shell-out'
        out.mkdir(exist_ok=True)
        for objects in (None, shell_root / 'plain'):
            args = [str(SHELL), '--game-root', str(shell_root), '--no-audio', '--session', str(session),
                    '--headless', '--frames', '4', '--every', '100', '--width', '320', '--height', '240',
                    '--out-dir', str(out)]
            if objects:
                args += ['--login-objects', str(objects)]
            result = subprocess.run(args, capture_output=True, text=True, check=True)
            summary = next(json.loads(l) for l in result.stdout.splitlines() if '"summary"' in l)
            self.assertEqual(summary['scene'], 3)
            self.assertEqual(summary['world'], 0x5e)
        from PIL import Image  # noqa: PLC0415 (the shell test environment has Pillow)
        png = sorted(out.glob('frame-*-s3-frame.png'))[-1]
        pixels = Image.open(png).convert('RGB').getdata()
        lit = sum(1 for p in pixels if max(p) > 24)
        self.assertGreater(lit, len(pixels) // 3)   # not the black frame of NATIVE-SHELL-001


@unittest.skipUnless(PRIVATE and PLAIN and Path(PLAIN or '/nonexistent', 'EncTerrain95.plain').exists(),
                     'installed client and the local decoded EncTerrain95.plain')
class InstalledLoginSceneTests(unittest.TestCase):
    def test_installed_world95_with_the_live_placements(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            scene, _ = login(os.environ['MU_GAME_ROOT'], '--out', Path(tmp) / 'l.png', objects=PLAIN)
        # the live read of 2026-10-18 (objread globals): CameraAngle, CameraPosition, CameraFOV, the far plane
        self.assertEqual(scene['camera_angle'], [-84.5, 0, -45])
        self.assertEqual(scene['camera_position'], [24475.797, 7581.581, 1834.540])
        self.assertEqual(scene['fov'], 35)
        self.assertEqual(scene['view_far'], 25037.924)
        self.assertEqual((scene['objects'], scene['objects_created']), (47, 47))
        self.assertEqual(scene['after_character'], 2)
        self.assertEqual(scene['sprites'], 10)


if __name__ == '__main__':
    unittest.main()
