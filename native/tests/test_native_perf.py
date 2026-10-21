"""NATIVE-PERF-001 checks: the rendering optimizations draw what the client draws.

Portable (synthetic data only):
  * native/tools/perf_report.py and imgdiff.py on synthetic logs and images;
  * perf_gl_host (macOS offscreen GL): the same 2D call stream through the
    software raster (core/mu_ui_raster.c) and the GPU replay (viewer/ui_gl.c)
    over the same background, equal up to blending rounding; a terrain- and
    mesh-like immediate-mode stream drawn directly and through the batch
    (viewer/gl_batch.c), pixel-identical with fewer draw calls;
  * mu-client --headless --backend gl over the synthetic game tree of
    test_native_shell: --gpu-overlay against the software overlay within the
    tolerance, MU_NO_GL_BATCH=1 against the batch identical, --perf writes a
    line per frame.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the same comparisons over the
installed client data (Lorencia with the demo placement; the whole mu-client
flow), as in docs/research/native-performance.md.
"""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(NATIVE / 'tools'))
import imgdiff  # noqa: E402
import perf_report  # noqa: E402

CC = os.environ.get('CC') or shutil.which('clang') or shutil.which('cc')
CLIENT = NATIVE / 'build/mu-client'
WORLD = NATIVE / 'build/mu-world'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
# The 2D layer on the GPU against the software raster: blending and filtering round differently (at most 2 per
# channel); quad edges that fall exactly on pixel centres may resolve differently (a few pixels). The scene
# comparisons allow 0.05 % of the pixels above 2 (measured: at most 0.0014 %).
OVERLAY_DELTA, OVERLAY_FRACTION = 2, 0.0005


def png(path, width, height, pixel):
    raw = b''.join(b'\0' + b''.join(bytes(pixel(x, y)) for x in range(width)) for y in range(height))
    chunk = lambda kind, body: struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


class ToolTests(unittest.TestCase):
    def test_perf_report_percentiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'perf.tsv'
            phases = ['events', 'logic', 'terrain', 'sleep']
            lines = ['frame\tscene\ttotal_ms\t' + '\t'.join(p + '_ms' for p in phases)]
            for i in range(100):   # 5 loading frames in scene 5, then 95 world frames of 40 ms (10 ms of work)
                scene = 5 if i < 5 else 6
                lines.append(f'{i}\t{scene}\t40.0\t0.1\t{1.0 + (i % 10) * 0.1:.1f}\t8.0\t30.0')
            log.write_text('\n'.join(lines) + '\n')
            r = perf_report.summarize(str(log), scene=6, skip_first=0)
            self.assertEqual(r['frames'], 95)
            self.assertAlmostEqual(r['fps'], 25.0, places=3)
            self.assertAlmostEqual(r['frame_ms']['p95'], 40.0)
            self.assertAlmostEqual(r['work_ms']['p50'], 10.0)
            self.assertAlmostEqual(r['phases']['terrain']['mean'], 8.0)
            self.assertEqual(r['over_40ms'], 0.0)
            self.assertEqual(perf_report.summarize(str(log), scene=6, skip_first=10)['frames'], 85)
            self.assertAlmostEqual(perf_report.percentile([1, 2, 3, 4], 50), 2.5)

    def test_imgdiff_counts_and_tolerance(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, c, d = (Path(tmp) / n for n in ('a.png', 'b.png', 'c.png', 'd.png'))
            png(a, 8, 4, lambda x, y: (x * 10, y * 10, 50, 255))
            png(b, 8, 4, lambda x, y: (x * 10 + (1 if x == 2 else 0), y * 10 + (9 if (x, y) == (5, 3) else 0), 50,
                                      0 if x == 7 else 255))   # alpha is not compared
            png(c, 8, 4, lambda x, y: (x * 10, y * 10, 50, 255))
            png(d, 4, 4, lambda x, y: (0, 0, 0, 255))
            self.assertTrue(imgdiff.compare(a, c, 0)['identical'])
            r = imgdiff.compare(a, b, 2)
            self.assertEqual((r['differing'], r['max_delta'], r['above_tolerance']), (5, 9, 1))
            self.assertIn('size_mismatch', imgdiff.compare(a, d, 0))
            self.assertEqual(imgdiff.main([str(a), str(b), '--max-delta', '9']), 0)
            self.assertEqual(imgdiff.main([str(a), str(b), '--max-delta', '2']), 1)
            self.assertEqual(imgdiff.main([str(a), str(b), '--max-delta', '2', '--max-fraction', '0.05']), 0)


def build_gl_host(tmp):
    host = Path(tmp) / 'perf-gl-host'
    srcs = [HERE / 'perf_gl_host.c', NATIVE / 'viewer/ui_gl.c', NATIVE / 'viewer/gl_batch.c',
            NATIVE / 'viewer/gl_headless.c', NATIVE / 'core/mu_ui_raster.c']
    subprocess.run([CC, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-DGL_SILENCE_DEPRECATION',
                    *map(str, srcs), '-framework', 'OpenGL', '-lm', '-o', str(host)], check=True)
    return host


@unittest.skipUnless(CC and sys.platform == 'darwin', 'needs a C compiler and macOS offscreen OpenGL')
class GLPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.host = build_gl_host(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self, *args):
        r = subprocess.run([str(self.host), *map(str, args)], capture_output=True, text=True)
        if r.returncode == 3:
            self.skipTest('no offscreen GL context: ' + r.stderr.strip())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_ui_replay_matches_the_software_raster(self):
        r = self.run_host('ui', 320, 200)
        self.assertGreaterEqual(r['primitives'], 8)
        self.assertGreaterEqual(r['uploads'], 3)            # two textures and the re-upload after a draw
        # blending rounds by at most 2; above that only pixels on the blended quad's shared diagonal, which the
        # software raster covers twice (it blends them twice; GL once): 28 of 64,000 measured
        self.assertLessEqual(r['above2'], r['pixels'] // 1000, r)
        self.assertLess(r['differing'], r['pixels'] // 20, r)

    def test_batch_is_pixel_identical_with_fewer_draws(self):
        r = self.run_host('batch', 256, 192)
        self.assertTrue(r['identical'], r)
        self.assertGreater(r['primitives'], 300)
        self.assertLess(r['draws'] * 3, r['primitives'] * 2, r)   # merged draws
        self.assertLess(r['state_applied'] * 2, r['state_calls'], r)   # redundant state dropped


class ClientTests(unittest.TestCase):
    """mu-client headless GL over the synthetic tree of test_native_shell."""

    @classmethod
    def setUpClass(cls):
        try:
            subprocess.run(['make', '-C', str(NATIVE), 'client'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise unittest.SkipTest('SDL2/OpenGL client not buildable here')
        from test_native_shell import write_root, write_session
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_root(Path(cls.tmp.name) / 'root')
        cls.session = write_session(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def render(self, name, *extra, env=None):
        out = Path(self.tmp.name) / name
        out.mkdir()
        r = subprocess.run([str(CLIENT), '--game-root', str(self.root), '--session', str(self.session), '--no-audio',
                            '--headless', '--backend', 'gl', '--auto', '--frames', '120', '--every', '15',
                            '--width', '640', '--height', '480', '--out-dir', str(out), '--quiet', *extra],
                           capture_output=True, text=True, env=dict(os.environ, **(env or {})))
        if r.returncode and 'headless GL' in r.stderr:
            self.skipTest('no offscreen GL context')
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return out

    def test_gpu_overlay_within_tolerance(self):
        cpu = self.render('cpu')
        gpu = self.render('gpu', '--gpu-overlay')
        names = sorted(p.name for p in cpu.glob('*.png'))
        self.assertGreater(len(names), 10)
        self.assertEqual(names, sorted(p.name for p in gpu.glob('*.png')))
        scenes = set()
        for n in names:
            r = imgdiff.compare(cpu / n, gpu / n, OVERLAY_DELTA)
            self.assertLessEqual(r['above_fraction'], OVERLAY_FRACTION, (n, r))
            scenes.add(n.split('-')[2])
        self.assertTrue({'s2', 's3', 's5', 's6'} <= scenes, scenes)   # title, login, character select, world

    def test_batching_is_pixel_identical(self):
        batch = self.render('batch')
        immediate = self.render('immediate', env={'MU_NO_GL_BATCH': '1'})
        for p in sorted(batch.glob('*.png')):
            self.assertTrue(imgdiff.compare(immediate / p.name, p, 0)['identical'], p.name)

    def test_perf_log_has_a_line_per_frame(self):
        log = Path(self.tmp.name) / 'perf.tsv'
        self.render('perf', '--perf', log, '--gpu-overlay')
        header, rows = perf_report.read(str(log))
        self.assertEqual(header[:3], ['frame', 'scene', 'total_ms'])
        for phase in ('logic_ms', 'terrain_ms', 'objects_ms', 'overlay_ms', 'scene_ms'):
            self.assertIn(phase, header)
        self.assertEqual(len(rows), 120)
        self.assertTrue(any(r['terrain_ms'] > 0 for r in rows if r['scene'] == 6))
        self.assertTrue(all(r['sleep_ms'] == 0 for r in rows))   # headless: the virtual clock does not sleep


@unittest.skipUnless(PRIVATE, 'private: needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateSceneTests(unittest.TestCase):
    """The optimized paths over the installed client data (renders stay in a temporary folder)."""

    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'client', 'world'], check=True, capture_output=True)
        cls.root = os.environ['MU_GAME_ROOT']
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def world(self, name, *args, env=None):
        out = Path(self.tmp.name) / name
        out.mkdir()
        r = subprocess.run([str(WORLD), '--game-root', self.root, '--headless', '--backend', 'gl', '--frames', '41',
                            '--every', '20', '--out-dir', str(out), '--quiet', '--no-audio', *map(str, args)],
                           capture_output=True, text=True, env=dict(os.environ, **(env or {})))
        if r.returncode and 'headless GL' in r.stderr:
            self.skipTest('no offscreen GL context')
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return out

    def test_lorencia_batch_identical(self):
        args = ('--width', 800, '--height', 500, '--placement', NATIVE / 'world/lorencia-demo-placement.txt',
                '--combat', '--items')
        batch = self.world('lorencia-batch', *args)
        immediate = self.world('lorencia-immediate', *args, env={'MU_NO_GL_BATCH': '1'})
        pngs = sorted(batch.glob('*.png'))
        self.assertEqual(len(pngs), 3)
        for p in pngs:
            self.assertTrue(imgdiff.compare(immediate / p.name, p, 0)['identical'], p.name)

    def test_client_flow_overlay_and_batch(self):
        def flow(name, *extra, env=None):
            out = Path(self.tmp.name) / name
            out.mkdir()
            r = subprocess.run([str(CLIENT), '--game-root', self.root, '--session',
                                str(NATIVE / 'client/demo-session.txt'), '--no-audio', '--headless', '--backend', 'gl',
                                '--auto', '--frames', '200', '--every', '25', '--width', '640', '--height', '480',
                                '--out-dir', str(out), '--quiet', *extra],
                               capture_output=True, text=True, env=dict(os.environ, **(env or {})))
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            return out
        base = flow('flow-baseline', env={'MU_PERF_BASELINE': '1'})
        new = flow('flow-gpu', '--gpu-overlay')
        for p in sorted(base.glob('*.png')):
            r = imgdiff.compare(p, new / p.name, OVERLAY_DELTA)
            self.assertLessEqual(r['above_fraction'], OVERLAY_FRACTION, (p.name, r))


if __name__ == '__main__':
    unittest.main()
