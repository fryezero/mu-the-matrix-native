"""Ambient life and weather in the walk-around session (NATIVE-ENV-001).

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic world 0 of test_native_world.py plus synthetic
Bird01/Fish01 models and a leaf01 .tga:
  * MoveBoids keeps at most five birds alive in world 0 and they are drawn;
  * MoveLeaves (the tick's guard is open on layer-1 tiles 0/2) keeps 80
    particles; the world has no leaf01.OZJ, so its leaf bitmap is empty and
    no particle is drawn (the client's .jpg-over-.tga rule) unless the viewer
    option --env-tga-leaves loads the .tga;
  * no fish without layer-1 water tiles;
  * the clear colour of world 0 is (10, 20, 14);
  * runs are deterministic, the seed changes the rand() stream, --no-env
    removes the module.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): logic-only runs of the
installed Lorencia, Dungeon, Devias, Noria, Atlans and Tormenta Island.
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
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def leaf_ozt(size=8):
    header = bytearray(4) + bytearray(18)
    header[4 + 2] = 2
    struct.pack_into('<hh', header, 16, size, size)
    header[20], header[21] = 32, 8
    return bytes(header) + bytes([40, 160, 200, 255])*(size*size)


def run(root, *args, check=True):
    result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                             *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'frame' in r and 'tick' in r],
            'env': next((r for r in rows if r.get('env') is True), None), 'result': result}


def png_pixel(path, x, y):
    data = Path(path).read_bytes()
    import zlib
    pos, idat, width, height = 8, b'', 0, 0
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos+4])[0]
        kind = data[pos+4:pos+8]
        if kind == b'IHDR':
            width, height = struct.unpack('>II', data[pos+8:pos+16])
        elif kind == b'IDAT':
            idat += data[pos+8:pos+8+n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = width*4 + 1
    rows, prev = [], bytearray(width*4)
    for r in range(height):
        f, line = raw[r*stride], bytearray(raw[r*stride+1:(r+1)*stride])
        for i in range(len(line)):
            a = line[i-4] if i >= 4 else 0
            b = prev[i]
            c = prev[i-4] if i >= 4 else 0
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
        rows.append(line)
        prev = line
    return tuple(rows[y][4*x:4*x+4])


class EnvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_open_world(Path(cls.tmp.name)/'game')
        objects = cls.root/'Data'/'Object1'
        objects.mkdir(parents=True, exist_ok=True)
        (objects/'Bird01.bmd').write_bytes(nf.synthetic_layout(21, actions=2, keys=(4, 3)))
        (objects/'Fish01.bmd').write_bytes(nf.synthetic_layout(22, actions=2, keys=(4, 3)))
        (cls.root/'Data'/'World1'/'leaf01.OZT').write_bytes(leaf_ozt())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_birds_and_leaves(self):
        out = run(self.root, '--frames', 120, '--every', 0, '--tile', '130,60')
        env = out['env']
        self.assertIsNotNone(env)
        self.assertEqual(env['world'], 0)
        self.assertEqual(env['max_boids'], 5)       # MoveBoids stops at slot 5 in world 0
        self.assertEqual(env['max_fishs'], 0)       # no layer-1 water tile
        self.assertEqual(env['max_leaves'], 80)
        self.assertEqual(env['leaf_steps'], 120)    # the guard is open off tile 4
        self.assertEqual(env['leaf_bitmap'], 0)     # no leaf01.OZJ: the bitmap is empty
        for f in out['frames']:
            boids, fishs, leaves, objects, drawn = f['env']
            self.assertLessEqual(boids, 5)
            self.assertEqual(fishs, 0)
            self.assertEqual(drawn, 0)

    def test_tga_viewer_option_draws_the_particles(self):
        out = run(self.root, '--frames', 60, '--every', 59, '--out-dir', Path(self.tmp.name)/'tga', '--tile', '130,60',
                  '--env-tga-leaves')
        self.assertEqual(out['env']['leaf_bitmap'], 1)
        self.assertGreater(out['frames'][-1]['env'][4], 0)

    def test_clear_colour(self):
        out = run(self.root, '--frames', 1, '--every', 1, '--out-dir', Path(self.tmp.name)/'clear', '--tile', '130,60',
                  '--width', 320, '--height', 200, '--angle', 0)
        png = out['frames'][-1]['png']
        self.assertEqual(png_pixel(png, 0, 0)[:3], (10, 20, 14))
        bare = run(self.root, '--frames', 1, '--every', 1, '--out-dir', Path(self.tmp.name)/'bare', '--tile', '130,60',
                   '--width', 320, '--height', 200, '--angle', 0, '--no-env')
        self.assertIsNone(bare['env'])
        self.assertEqual(png_pixel(bare['frames'][-1]['png'], 0, 0)[:3], (0, 0, 0))

    def test_determinism_and_seed(self):
        a = run(self.root, '--frames', 80, '--every', 0, '--tile', '130,60')
        b = run(self.root, '--frames', 80, '--every', 0, '--tile', '130,60')
        c = run(self.root, '--frames', 80, '--every', 0, '--tile', '130,60', '--env-seed', 99)
        self.assertEqual(a['env'], b['env'])
        self.assertEqual([f['env'] for f in a['frames']], [f['env'] for f in b['frames']])
        self.assertNotEqual((a['env'], [f['env'] for f in a['frames']]), (c['env'], [f['env'] for f in c['frames']]))


@unittest.skipUnless(PRIVATE, 'set MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateWorlds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def world(self, world, tile, frames=200):
        return run(os.environ['MU_GAME_ROOT'], '--world', world, '--tile', tile, '--frames', frames, '--every', 0)['env']

    def test_target_worlds(self):
        lorencia = self.world(0, '111,127', 300)
        self.assertEqual((lorencia['max_boids'], lorencia['max_fishs'], lorencia['max_leaves']), (5, 3, 80))
        self.assertEqual(lorencia['leaf_bitmap'], 0)   # World1 has no leaf01.OZJ
        dungeon = self.world(1, '108,247')
        self.assertEqual((dungeon['max_boids'], dungeon['max_fishs'], dungeon['leaf_steps']), (5, 3, 0))
        devias = self.world(2, '210,36')
        self.assertEqual((devias['max_boids'], devias['max_leaves'], devias['leaf_bitmap']), (0, 80, 1))
        noria = self.world(3, '180,111')
        self.assertEqual((noria['max_boids'], noria['max_leaves'], noria['leaf_bitmap']), (5, 80, 0))
        atlans = self.world(7, '21,29')
        self.assertEqual((atlans['max_boids'], atlans['max_fishs'], atlans['max_leaves'], atlans['leaf_bitmap']),
                         (40, 10, 80, 1))
        tormenta = self.world(141, '118,150', 400)
        self.assertEqual(tormenta['tormenta_rain'], 10.0)
        self.assertGreater(tormenta['particles'], 0)


if __name__ == '__main__':
    unittest.main()
