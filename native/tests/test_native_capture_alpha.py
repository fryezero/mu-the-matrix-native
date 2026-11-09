"""Window captures are opaque (REGRESS-003).

The world's blended draws (the terrain's alpha-mapped layer 2, grass, sprites) leave the framebuffer's alpha below
1. The window is opaque and shows only the colour channels, but mu-world/mu-walk wrote that alpha into their frame
PNGs, so viewers that composite over a light background showed flat light-grey polygons over the terrain and grey
grass (README-IMAGES-D finding 1). The frame PNGs now carry alpha 0xff; the colour channels and the frame report's
sha256 (over the raw RGBA readback) are unchanged.

Portable (synthetic data only): the open world of test_native_world.py with a half-transparent layer-2 patch under
the hero, through mu-walk (software rasterizer) and, when a headless GL context is available, mu-world --backend gl.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB): the README-IMAGES-D scene,
Lorencia 138,123 with --npc, the GFx inventory and the Blade +9 tooltip, frame 60, on both backends.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
REPO = NATIVE.parent
sys.path.insert(0, str(HERE))
from test_native_terrain import v12_encrypt  # noqa: E402
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
WORLD = NATIVE/'build/mu-world'
GAME = os.environ.get('MU_GAME_ROOT')
DATA = os.environ.get('MU_NATIVE_DATA_DIR')
GFX = os.environ.get('MU_GFX_LIB')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
SCENE = bool(PRIVATE and GAME and DATA and GFX and Path(GFX).is_file() and Path(DATA, 'gfx').is_dir())


def png_rgba(path):
    """Width, height and RGBA bytes of an 8-bit RGBA PNG (any filter)."""
    data = Path(path).read_bytes()
    pos, idat, width, height = 8, b'', 0, 0
    while pos < len(data):
        n = int.from_bytes(data[pos:pos+4], 'big')
        kind = data[pos+4:pos+8]
        if kind == b'IHDR':
            width, height = int.from_bytes(data[pos+8:pos+12], 'big'), int.from_bytes(data[pos+12:pos+16], 'big')
            assert data[pos+16:pos+18] == bytes([8, 6]), 'expected 8-bit RGBA'
        elif kind == b'IDAT':
            idat += data[pos+8:pos+8+n]
        pos += 12 + n
    raw, stride = zlib.decompress(idat), width*4 + 1
    out, prev = bytearray(), bytearray(width*4)
    for r in range(height):
        f, line = raw[r*stride], bytearray(raw[r*stride+1:(r+1)*stride])
        for i in range(len(line)):
            a, b, c = (line[i-4] if i >= 4 else 0), prev[i], (prev[i-4] if i >= 4 else 0)
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b)//2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += line
        prev = line
    return width, height, bytes(out)


def blended_world(root, alpha_value):
    """The open world with layer 2 = TileGrass02 over a 24x24 patch around 130,60 at the given alpha."""
    write_open_world(root)
    layer1 = bytes(2 if (i & 1) else 0 for i in range(65536))
    layer2 = bytearray([255]) * 65536
    alpha = bytearray(65536)
    for y in range(48, 72):
        for x in range(118, 142):
            layer2[y*256 + x] = 1
            alpha[y*256 + x] = alpha_value
    (Path(root)/'Data'/'World1'/'EncTerrain1.map').write_bytes(v12_encrypt(bytes([0, 1]) + layer1 + bytes(layer2) +
                                                                          bytes(alpha)))
    return root


def frames(stdout):
    rows = [json.loads(line) for line in stdout.splitlines() if line.startswith('{')]
    return [r for r in rows if 'frame' in r and 'png' in r and r.get('png')]


class CaptureAlphaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'all', 'world'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.half = blended_world(cls.base/'half', 128)
        cls.none = blended_world(cls.base/'none', 0)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def capture(self, tool, root, name, *extra):
        out = self.base/name
        r = subprocess.run([str(tool), '--game-root', str(root), '--headless', '--no-audio', '--frames', '1',
                            '--every', '1', '--out-dir', str(out), '--tile', '130,60', '--width', '320',
                            '--height', '200', *extra], capture_output=True, text=True)
        return r, frames(r.stdout)

    def check_opaque(self, tool, *extra, tag):
        r, rows = self.capture(tool, self.half, f'{tag}-half', *extra)
        if r.returncode and tag == 'gl':
            self.skipTest(f'no headless GL context: {r.stderr.strip()[:200]}')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(rows), 1)
        w, h, rgba = png_rgba(rows[0]['png'])
        self.assertEqual((w, h), (320, 200))
        alpha = rgba[3::4]
        self.assertEqual(alpha.count(255), w*h, 'frame PNG alpha below 0xff: blended draws leak into the capture')
        # The layer was blended here (else the test would prove nothing): the report hashes the raw readback, whose
        # alpha is below 1, so it differs from the hash of the opaque PNG pixels ...
        self.assertNotEqual(rows[0]['sha256'], hashlib.sha256(rgba).hexdigest())
        # ... and the colour channels differ from the same view without the layer-2 patch.
        _, plain = self.capture(tool, self.none, f'{tag}-none', *extra)
        _, _, rgba0 = png_rgba(plain[0]['png'])
        self.assertNotEqual(bytes(b for i, b in enumerate(rgba) if i % 4 != 3),
                            bytes(b for i, b in enumerate(rgba0) if i % 4 != 3))
        # Deterministic: a second run writes the same file.
        _, again = self.capture(tool, self.half, f'{tag}-again', *extra)
        self.assertEqual(Path(again[0]['png']).read_bytes(), Path(rows[0]['png']).read_bytes())
        self.assertEqual(again[0]['sha256'], rows[0]['sha256'])

    def test_soft_frames_are_opaque(self):
        self.check_opaque(WALK, '--backend', 'soft', tag='soft')

    @unittest.skipUnless(WORLD.exists(), 'mu-world (SDL2/GL) not built')
    def test_gl_frames_are_opaque(self):
        self.check_opaque(WORLD, '--backend', 'gl', tag='gl')


class OtherWindowCaptures(unittest.TestCase):
    """FOLLOWUPS-001: exercise the other capture front ends, including blended model pixels."""
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'all', 'viewer'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.root = blended_world(cls.base/'world', 128)
        from test_native_charsel import write_world94
        cls.charsel = write_world94(cls.base/'charsel')
        from native_fixtures import write_textured_model
        (cls.base/'model').mkdir()
        cls.model = write_textured_model(cls.base/'model', seed=11)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def opaque(self, path):
        w, h, rgba = png_rgba(path)
        self.assertEqual(rgba[3::4].count(255), w*h, str(path))

    def invoke(self, *args):
        r = subprocess.run(list(map(str, args)), cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return r

    def test_charsel_frames(self):
        for backend, name in [('soft', 'mu-charsel'), ('gl', 'mu-charsel-window')]:
            with self.subTest(backend=backend):
                out = self.base/f'charsel-{backend}'
                self.invoke(NATIVE/'build'/name, '--game-root', self.charsel, '--headless', '--no-ui',
                            '--backend', backend, '--frames', '1', '--every', '1', '--width', '320',
                            '--height', '200', '--out-dir', out)
                pngs = list(out.glob('*.png'))
                self.assertEqual(len(pngs), 1)
                self.opaque(pngs[0])

    def test_frame_window(self):
        out = self.base/'frame-window'
        self.invoke(NATIVE/'build/mu-frame-window', self.model, '--headless', '--frames', '1',
                    '--width', '320', '--height', '200', '--out-dir', out)
        self.opaque(out/'gl-frame-000.png')

    def test_model_viewer(self):
        for backend in ('soft', 'gl'):
            with self.subTest(backend=backend):
                out = self.base/f'viewer-{backend}.png'
                r = self.invoke(NATIVE/'build/mu-viewer', self.model, '--headless', '--backend', backend,
                                '--width', '320', '--height', '200', '--alpha', '0.5', '--out', out)
                self.opaque(out)
                # The report still hashes raw blended pixels. The saved capture changes only alpha.
                report = json.loads(r.stdout.splitlines()[-1])
                self.assertNotEqual(report['sha256'], hashlib.sha256(png_rgba(out)[2]).hexdigest())

    def test_terrain_viewer(self):
        for backend in ('soft', 'gl'):
            with self.subTest(backend=backend):
                out = self.base/f'terrain-viewer-{backend}.png'
                self.invoke(NATIVE/'build/mu-viewer', '--terrain', self.root, '--world', '0', '--headless',
                            '--backend', backend, '--width', '320', '--height', '200', '--target', '13000,6000',
                            '--distance', '1000', '--out', out)
                self.opaque(out)


@unittest.skipUnless(SCENE, 'private: MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB')
class LorenciaTooltipSceneTests(unittest.TestCase):
    """README-IMAGES-D finding 1: the GFx inventory + tooltip scene without a party player, frame 60."""

    def scene(self, backend, out):
        players = Path(out)/'players.txt'
        Path(out).mkdir(parents=True, exist_ok=True)
        players.write_text(''.join(line.replace(' party ', ' ') for line in
                                   (REPO/'native/world/lorencia-demo-players.txt').read_text().splitlines(True)))
        env = {**os.environ, 'MU_GFX_LIB': GFX, 'MU_LANG_DIR': str(Path(DATA, 'lang')), 'MU_GFX_PUBLIC_DEMO': '1',
               'MU_GFX_SINGLE_BUFFER': '1', 'MU_GFX_TEST_CLOCK': '1'}
        r = subprocess.run([
            str(WORLD), '--game-root', GAME, '--objects-dir', str(Path(DATA, 'objects')), '--headless', '--backend',
            backend, '--no-audio', '--width', '1280', '--height', '800', '--class', '1', '--tile', '138,123',
            '--gfx', str(Path(DATA, 'gfx')), '--hero-name', 'Preview', '--placement',
            'native/world/lorencia-demo-placement.txt', '--npc', '--npc-demo', 'native/world/lorencia-demo-npc.txt',
            '--items', '--players', str(players), '--hero-item', 'weapon0=Item/CookriShortSword.bmd@0:68:9:1',
            '--hero-item', 'weapon1=Item/Shield01.bmd@6:0:7', '--hero-item', 'wing=Item/Wing02.bmd@12:1',
            '--gfx-open', 'inventory', '--npc-script', '50:tipinv:0', '--frames', '61', '--every', '60',
            '--out-dir', str(out)], cwd=REPO, env=env, capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return frames(r.stdout)

    def test_gfx_window_captures_are_opaque(self):
        subprocess.run(['make', '-C', str(NATIVE/'gfx'), 'window'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ('--headless', '--headless-gl'):
                out = Path(tmp)/mode[2:]
                out.mkdir()
                env = {**os.environ, 'MU_GFX_LIB': GFX, 'MU_GFX_SINGLE_BUFFER': '1',
                       'MU_NATIVE_SETTINGS_DIR': str(out)}
                r = subprocess.run([str(NATIVE/'build/mu-gfx-window'), '--gfx', str(Path(DATA, 'gfx')),
                                    mode, '--frames', '25', '--size', '640x400', '--out-dir', str(out)],
                                   cwd=REPO, env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr[-2000:])
                pngs = list(out.glob('*.png'))
                self.assertEqual(len(pngs), 1)
                w, h, rgba = png_rgba(pngs[0])
                self.assertEqual(rgba[3::4].count(255), w*h, mode)

    def test_scene_frames_are_opaque(self):
        with tempfile.TemporaryDirectory() as tmp:
            for backend in ('gl', 'soft'):
                rows = self.scene(backend, Path(tmp)/backend)
                last = [r for r in rows if r['frame'] == 60]
                self.assertEqual(len(last), 1, backend)
                w, h, rgba = png_rgba(last[0]['png'])
                self.assertEqual(rgba[3::4].count(255), w*h, backend)
                # The raw readback still has the blended alpha (about 210,000 pixels below 1 before the fix); only
                # the file is opaque.
                self.assertNotEqual(last[0]['sha256'], hashlib.sha256(rgba).hexdigest(), backend)


if __name__ == '__main__':
    unittest.main()
