"""Parallel character poses preserve every model window and attachment output."""
import hashlib
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


if __name__ == '__main__':
    unittest.main()
