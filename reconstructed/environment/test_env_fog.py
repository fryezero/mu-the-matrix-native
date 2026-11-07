"""RENDER-WORLDS-FOG: the render scene's fog tests (env_fog.c) and the software raster's GL_LINEAR fog stage.

Portable (synthetic data only):
  * env_fog.c: world 0x1e inside the box x 16100..19000, y 18900..21700 (ends included, NaN outside) gives StartFog's
    parameters (black, GL_LINEAR, 2000..2700); outside it glDisable; every other world no call; the end test calls
    EndFog exactly when the begin test started the fog;
  * native/core/mu_raster.c: fog off leaves a fragment as it was; fog on blends RGB toward the fog colour by
    f = (end - |z_eye|) / (end - start) clamped to [0, 1] and leaves alpha alone.
Private (MU_RECOVERY_INTEGRATION=1, pinned text/data): scripts/validate_worlds_fog.py with small samples (the
validator row runs the full count and the mutants).
"""
import ctypes as C
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
CC = shutil.which(os.environ.get('CC', 'cc')) or shutil.which('clang')
FLAGS = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-ffp-contract=off', '-fno-fast-math']
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


class Fog(C.Structure):
    _fields_ = [('color', C.c_float * 4), ('mode', C.c_float), ('start', C.c_float), ('end', C.c_float)]


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


RASTER_HOST = r'''
#include "mu_raster.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* argv: fog z r g b a [fog_r fog_g fog_b]; one big triangle in the plane z (eye space), identity view, a
 * perspective projection; prints the centre pixel as "R G B A". */
int main(int argc, char **argv)
{
    if (argc < 7) return 2;
    mu_raster r;
    if (mu_raster_init(&r, 8, 8)) return 1;
    for (int k = 0; k < 16; ++k) r.view[k] = (k % 5 == 0) ? 1.0f : 0.0f;
    const float n = 10.0f, f = 5000.0f;
    memset(r.projection, 0, sizeof r.projection);
    r.projection[0] = 1.0f; r.projection[5] = 1.0f;
    r.projection[10] = (f + n) / (n - f); r.projection[11] = -1.0f; r.projection[14] = 2.0f * f * n / (n - f);
    const uint8_t clear[4] = {0, 0, 0, 255};
    mu_raster_clear(&r, clear);
    r.fog = (uint8_t)atoi(argv[1]);
    r.fog_start = 2000.0f; r.fog_end = 2700.0f;
    for (int k = 0; k < 3; ++k) r.fog_color[k] = argc > 9 ? strtof(argv[7 + k], NULL) : 0.0f;
    mu_meshdraw_state s;
    memset(&s, 0, sizeof s);
    s.depth_test = 1; s.depth_mask = 1;
    mu_raster_set(&r, &s, NULL, 0);
    mu_render_backend b;
    mu_raster_backend(&r, &b);
    const float z = strtof(argv[2], NULL);
    b.sink.color4(b.sink.context, strtof(argv[3], NULL), strtof(argv[4], NULL), strtof(argv[5], NULL),
                  strtof(argv[6], NULL));
    const float v[3][3] = {{-4.0f * -z, -4.0f * -z, z}, {4.0f * -z, -4.0f * -z, z}, {0.0f, 4.0f * -z, z}};
    mu_raster_begin_mode(&r, 4);
    for (int k = 0; k < 3; ++k) b.sink.vertex(b.sink.context, v[k]);
    mu_raster_end_mode(&r);
    const uint8_t *p = r.color + 4 * (4 * 8 + 4);
    printf("%d %d %d %d\n", p[0], p[1], p[2], p[3]);
    mu_raster_free(&r);
    return 0;
}
'''


class EnvFogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='env-fog-test-')
        out = Path(cls.tmp.name)
        lib = out / ('libenv_fog.' + SUFFIX)
        subprocess.run([CC, *FLAGS, '-fPIC', '-shared', str(HERE / 'env_fog.c'), '-o', str(lib)], check=True)
        cls.dll = C.CDLL(str(lib))
        cls.dll.mu_env_scene_fog_begin.argtypes = [C.c_int32, C.POINTER(C.c_float), C.POINTER(Fog)]
        cls.dll.mu_env_scene_fog_end.argtypes = [C.c_int32, C.POINTER(C.c_float)]
        (out / 'host.c').write_text(RASTER_HOST)
        cls.host = out / 'raster-fog-host'
        subprocess.run([CC, *FLAGS, '-I', str(ROOT / 'native/core'), str(out / 'host.c'),
                        str(ROOT / 'native/core/mu_raster.c'), '-lm', '-o', str(cls.host)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def begin(self, world, x, y, z=0.0):
        fog = Fog()
        state = self.dll.mu_env_scene_fog_begin(world, (C.c_float * 3)(x, y, z), C.byref(fog))
        return state, fog

    def end(self, world, x, y, z=0.0):
        return self.dll.mu_env_scene_fog_end(world, (C.c_float * 3)(x, y, z))

    def test_only_world_0x1e(self):
        for world in range(146):
            state, fog = self.begin(world, 17500.0, 20000.0)
            self.assertEqual(state, 2 if world == 0x1e else 0, world)
            self.assertEqual(self.end(world, 17500.0, 20000.0), int(world == 0x1e), world)

    def test_start_fog_parameters(self):
        state, fog = self.begin(0x1e, 16100.0, 21700.0)
        self.assertEqual(state, 2)
        self.assertEqual(list(fog.color)[:3], [0.0, 0.0, 0.0])
        self.assertEqual((fog.mode, fog.start, fog.end), (9729.0, 2000.0, 2700.0))

    def test_box_edges_and_nan(self):
        inf, nan = float('inf'), float('nan')
        inside = [(16100.0, 18900.0), (19000.0, 21700.0), (16100.0, 21700.0), (19000.0, 18900.0), (17000.0, 20000.0)]
        outside = [(16099.998, 20000.0), (19000.002, 20000.0), (17000.0, 18899.998), (17000.0, 21700.002),
                   (nan, 20000.0), (17000.0, nan), (inf, 20000.0), (-inf, 20000.0), (0.0, 0.0)]
        for x, y in inside:
            self.assertEqual(self.begin(0x1e, x, y)[0], 2, (x, y))
            self.assertEqual(self.end(0x1e, x, y), 1, (x, y))
        for x, y in outside:
            self.assertEqual(self.begin(0x1e, x, y)[0], 1, (x, y))
            self.assertEqual(self.end(0x1e, x, y), 0, (x, y))
        self.assertEqual(self.begin(0x1e, 17000.0, 20000.0, nan)[0], 2)   # z is not tested

    def raster(self, fog, z, rgba, colour=None):
        args = [str(self.host), str(fog), repr(z), *map(repr, rgba)] + ([*map(repr, colour)] if colour else [])
        return [int(v) for v in subprocess.run(args, check=True, capture_output=True, text=True).stdout.split()]

    def expected(self, z, rgba, colour=(0.0, 0.0, 0.0)):
        f = min(max(f32((2700.0 - abs(z)) / 700.0), 0.0), 1.0)
        rgb = [int(f32(f32(f * c) + f32((1.0 - f) * k)) * 255.0 + 0.5) for c, k in zip(rgba[:3], colour)]
        return rgb + [int(rgba[3] * 255.0 + 0.5)]

    def test_raster_fog_off_unchanged(self):
        for z in (-500.0, -2350.0, -4000.0):
            self.assertEqual(self.raster(0, z, (0.8, 0.6, 0.4, 0.5)), [204, 153, 102, 128])

    def test_raster_linear_fog(self):
        rgba = (0.8, 0.6, 0.4, 0.5)
        self.assertEqual(self.raster(1, -1500.0, rgba), [204, 153, 102, 128])    # before the start: f = 1
        self.assertEqual(self.raster(1, -3000.0, rgba), [0, 0, 0, 128])          # past the end: the fog colour
        for z in (-2000.0, -2175.0, -2350.0, -2600.0, -2700.0):
            got = self.raster(1, z, rgba)
            want = self.expected(z, rgba)
            self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(got, want)), (z, got, want))
            self.assertEqual(got[3], 128)                                        # alpha unchanged
        got = self.raster(1, -2350.0, rgba, (1.0, 0.5, 0.25))
        want = self.expected(-2350.0, rgba, (1.0, 0.5, 0.25))
        self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(got, want)), (got, want))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-fog-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_fog.py'), '--cases', '300',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))


if __name__ == '__main__':
    unittest.main()
