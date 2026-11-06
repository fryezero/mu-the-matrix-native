"""Cache integration safety without private captures; the original machine is synthetic."""
import collections
import ctypes
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import original_cache as oc
import validate_meshdraw as mesh


class MeshCache(unittest.TestCase):
    def test_warm_entries_replay_observations_but_host_comparisons_stay_live(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / 'oracle.py'
            script.write_text('version = 1\n')
            cache = oc.Cache(Path(folder), 'mesh', script)
            machine = object.__new__(mesh.Machine)
            machine.coverage = collections.Counter(existing=3)
            machine.x87_count = collections.Counter()
            machine.trig_stats = {}
            calls = []
            def original():
                calls.append(1)
                machine.coverage['body'] += 2
                machine.x87_count['fsin'] += 1
                machine.record_trig('sin', (0.0,), 0.0)
                return {'stream': [(1, 2, 3, 4, 5)]}
            with mock.patch.object(oc, 'named', return_value=cache):
                first = mesh.cached_original(machine, 'draw', {'x': b'case'}, original)
                cache.save()
            warm = oc.Cache(Path(folder), 'mesh', script)
            with mock.patch.object(oc, 'named', return_value=warm), mock.patch.object(math, 'sin', return_value=1.0):
                self.assertEqual(mesh.cached_original(machine, 'draw', {'x': b'case'}, original), first)
            self.assertEqual(calls, [1])
            self.assertEqual(machine.coverage, {'existing': 3, 'body': 4})
            self.assertEqual(machine.x87_count, {'fsin': 2})
            self.assertEqual(machine.trig_stats['sin'],
                             dict(calls=2, binary32_differences=1, binary64_differences=1))
            self.assertEqual((warm.hits, warm.misses), (1, 0))
            with mock.patch.object(oc, 'named', return_value=warm):
                mesh.cached_original(machine, 'draw', {'x': b'changed'}, original)
            self.assertEqual(len(calls), 2)

    def test_compare_runs_compiled_native_with_a_warm_original(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            script = folder / 'oracle.py'
            script.write_text('version = 1\n')
            source = folder / 'native.c'
            source.write_text('int native_word(void) { return 2 + MUTANT; }\n')
            libraries = []
            for mutant in (0, 1):
                lib = folder / f'native{mutant}.so'
                subprocess.run(['cc', '-shared', '-fPIC', f'-DMUTANT={mutant}', str(source), '-o', str(lib)],
                               check=True, capture_output=True)
                libraries.append(ctypes.CDLL(str(lib)))
            cache = oc.Cache(folder, 'mesh', script)
            machine = object.__new__(mesh.Machine)
            machine.coverage = collections.Counter()
            machine.x87_count = collections.Counter()
            machine.trig_stats = {}
            original = mock.Mock(return_value=dict(stream=[(1, 2, 3, 4, 5)], tables=[], fault=None))
            machine._run_case = original
            with mock.patch.object(mesh, 'read_case', return_value={'input': 1}), \
                    mock.patch.object(oc, 'named', return_value=cache), \
                    mock.patch.object(mesh, 'replay', side_effect=lambda *_: ([(1, libraries[0].native_word(), 3, 4, 5)], [])):
                self.assertTrue(mesh.compare(machine, b'case', folder)['match'])
            cache.save()
            warm = oc.Cache(folder, 'mesh', script)
            with mock.patch.object(mesh, 'read_case', return_value={'input': 1}), \
                    mock.patch.object(oc, 'named', return_value=warm), \
                    mock.patch.object(mesh, 'replay', side_effect=lambda *_: ([(1, libraries[1].native_word(), 3, 4, 5)], [])):
                self.assertFalse(mesh.compare(machine, b'case', folder)['match'])
            self.assertEqual(original.call_count, 1)
            self.assertEqual((warm.hits, warm.misses), (1, 0))

    def test_failed_original_does_not_poison_instrumentation_or_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / 'oracle.py'
            script.write_text('version = 1\n')
            cache = oc.Cache(Path(folder), 'mesh', script)
            machine = object.__new__(mesh.Machine)
            machine.coverage = collections.Counter(body=3)
            machine.x87_count = collections.Counter()
            with mock.patch.object(oc, 'named', return_value=cache):
                with self.assertRaises(RuntimeError):
                    mesh.cached_original(machine, 'draw', 1, mock.Mock(side_effect=RuntimeError('failed')))
            self.assertEqual(machine.coverage, {'body': 3})
            self.assertIsNone(machine.cache_trig)
            self.assertEqual(cache.data, {})


class TerrainInputs(unittest.TestCase):
    def test_decal_template_changes_only_world_and_owns_no_global_rng(self):
        import random
        import validate_terrain as terrain
        with mock.patch.object(terrain, 'CELLS', 8):
            state = random.getstate()
            template = terrain.synthetic_scene(800, extended=True)
            for world in (0, 142, 141):
                self.assertEqual(dict(template, world=world), terrain.synthetic_scene(800, world, extended=True))
            self.assertEqual(random.getstate(), state)


class InfoBatch(unittest.TestCase):
    def test_batch_matches_each_original_entry_point_including_failures(self):
        subprocess.run(['make', '-j4', '-s', '-C', str(ROOT / 'native'), 'build/meshdraw-info-batch'],
                       check=True, capture_output=True)
        sys.path.insert(0, str(ROOT / 'native/tests'))
        import native_fixtures as nf
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            good = nf.write_textured_model(folder, 8, version=10, four_corner=True)
            bad = folder / 'bad.bmd'
            bad.write_bytes(b'invalid')
            paths = [good, bad, folder / 'absent.bmd', good]
            expected = []
            for path in paths:
                result = subprocess.run([str(ROOT / 'native/build/mu-render'), 'info', str(path)],
                                        capture_output=True, text=True)
                expected.append(result.stdout.strip() if result.returncode == 0 else '{}')
            batch = subprocess.run([str(ROOT / 'native/build/meshdraw-info-batch'), *map(str, paths)],
                                   capture_output=True, text=True, check=True)
            self.assertEqual(batch.stdout.splitlines(), expected)


if __name__ == '__main__':
    unittest.main()
