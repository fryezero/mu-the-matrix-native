"""Parallel character poses preserve every model window and attachment output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_viewer import nf


class PoseWorkers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/perf-players-host'], check=True, capture_output=True)

    def test_serial_and_parallel_model_buffers_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / 'authored.bmd'
            model.write_bytes(nf.synthetic_layout(19, meshes=2, bones=7, actions=2, keys=(4, 3)))
            hashes = []
            for reference in ('1', '0', '0'):
                result = subprocess.run([str(NATIVE / 'build/perf-players-host'), str(model)], check=True,
                                        capture_output=True, env=dict(os.environ, MU_PERF_004_BASELINE=reference))
                self.assertGreater(len(result.stdout.splitlines()), 30000)
                hashes.append(hashlib.sha256(result.stdout).hexdigest())
            self.assertEqual(hashes, [hashes[0]] * 3)

    def test_empty_small_and_worker_threshold_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / 'authored.bmd'
            model.write_bytes(nf.synthetic_layout(19, meshes=2, bones=7, actions=2, keys=(4, 3)))
            for count in (0, 1, 7, 8):
                hashes = []
                for reference in ('1', '0'):
                    result = subprocess.run([str(NATIVE / 'build/perf-players-host'), str(model), str(count), '4'],
                                            check=True, capture_output=True,
                                            env=dict(os.environ, MU_PERF_004_BASELINE=reference))
                    hashes.append(hashlib.sha256(result.stdout).hexdigest())
                self.assertEqual(hashes[0], hashes[1], count)


class TopologyProof(unittest.TestCase):
    def test_changed_indices_counts_and_other_owner_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = (NATIVE / 'core/mu_perf_mesh.c').read_text()
            variants = [cache,
                        cache.replace('memcmp(t->triangles, m->triangles, bytes) == 0', '1'),
                        cache.replace('t->vertices == m->vertex_count', '1')]
            for i, source in enumerate(variants):
                src = Path(tmp) / 'cache.c'
                src.write_text(source)
                host = Path(tmp) / 'host'
                subprocess.run(['clang', '-std=c11', '-O2', '-I', str(NATIVE / 'core'),
                                str(HERE / 'perf_topology_host.c'), str(src),
                                str(NATIVE / 'core/mu_meshdraw.c'), '-lm', '-o', str(host)],
                               check=True, capture_output=True)
                result = subprocess.run([str(host)], capture_output=True)
                self.assertEqual(result.returncode == 0, i == 0, (i, result))


@unittest.skipUnless(sys.platform == 'darwin', 'needs macOS offscreen GL')
class PointerSetup(unittest.TestCase):
    def test_growing_storage_and_external_pointer_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = (NATIVE / 'viewer/gl_batch.c').read_text()
            for i, variant in enumerate((source, source.replace('    b->array_base = 0;', ''))):
                src, host = Path(tmp) / 'batch.c', Path(tmp) / 'host'
                src.write_text(variant)
                subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-DGL_SILENCE_DEPRECATION', '-I', str(NATIVE / 'viewer'),
                                str(HERE / 'perf_gl_host.c'), str(src), str(NATIVE / 'viewer/ui_gl.c'),
                                str(NATIVE / 'viewer/gl_headless.c'), str(NATIVE / 'core/mu_ui_raster.c'),
                                '-framework', 'OpenGL', '-lm', '-o', str(host)], check=True, capture_output=True)
                r = subprocess.run([str(host), 'batch', '256', '192'], capture_output=True, text=True,
                                   env=dict(os.environ, MU_PERF_004_BASELINE='0'))
                if r.returncode == 3:
                    self.skipTest('no offscreen GL context')
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(json.loads(r.stdout)['identical'], i == 0)


if __name__ == '__main__':
    unittest.main()
