"""Cache integration safety without private captures; the original machine is synthetic."""
import collections
import ctypes
import math
import os
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


WORKER = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import original_cache as oc
folder, script, tag, go = Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
while not go.exists():
    time.sleep(0.005)
for round in range(int(sys.argv[6])):
    cache = oc.Cache(folder, 'shared', script)
    for i in range(40):
        cache.get('f', (tag, round, i), lambda: (tag, round, i) * 50)
    cache.save()
"""


class MultiKeyCache(unittest.TestCase):
    """TEST-SPEED-003: several harness versions of one name stay warm, the directory has a size cap, a warm cache
    still exposes a changed C side under every key, and concurrent writers keep every entry."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.dir = self.base / 'cache'
        self.script = self.base / 'validate_fake.py'

    def tearDown(self):
        self.tmp.cleanup()

    def version(self, text):
        self.script.write_text(text)
        return oc.Cache(self.dir, 'validate_fake', self.script)

    def files(self, name='validate_fake'):
        return sorted(p.name for p in (self.dir / name).glob('*.pickle.xz'))

    def test_two_alternating_keys_both_stay_warm_and_never_mix(self):
        calls = []
        def run(text, value):
            cache = self.version(text)
            got = [cache.get('f', case, lambda case=case: calls.append(case) or (value, case)) for case in range(5)]
            cache.save()
            return cache, got
        main, got = run('MAIN = 1\n', 'main')
        branch, got_b = run('BRANCH = 1\n', 'branch')
        self.assertNotEqual(main.key, branch.key)
        self.assertEqual(len(calls), 10)
        for _ in range(3):   # main, branch, main, ...: before TEST-SPEED-003 each switch deleted the other key
            again, got2 = run('MAIN = 1\n', 'other')
            self.assertEqual((again.hits, again.misses, got2), (5, 0, got), 'main stays warm, its own values')
            again, got2 = run('BRANCH = 1\n', 'other')
            self.assertEqual((again.hits, again.misses, got2), (5, 0, got_b), 'branch stays warm, its own values')
        self.assertEqual(len(calls), 10, 'no original side rerun after the first run of each version')
        self.assertEqual(self.files(), sorted([main.path.name, branch.path.name]))

    def test_a_file_is_only_used_for_the_key_stored_inside(self):
        first = self.version('A = 1\n')
        first.get('f', 1, lambda: 'a')
        first.save()
        second = self.version('B = 1\n')
        first.path.replace(second.path)   # a file under the wrong name (copied, renamed): a miss, not a stale hit
        self.assertEqual(self.version('B = 1\n').get('f', 1, lambda: 'b'), 'b')
        second.path.write_bytes(b'not xz')   # damaged: a miss
        self.assertEqual(self.version('B = 1\n').get('f', 1, lambda: 'b2'), 'b2')

    def test_planted_c_regression_is_caught_with_a_warm_cache_under_each_key(self):
        good = lambda case: case * 3
        broken = lambda case: case * 3 + (case == 4)   # a planted native-side change
        original_calls = []
        for text in ('MAIN = 1\n', 'BRANCH = 1\n'):
            cache = self.version(text)
            [cache.get('f', c, lambda c=c: original_calls.append(c) or c * 3) for c in range(6)]
            cache.save()
        for text in ('MAIN = 1\n', 'BRANCH = 1\n', 'MAIN = 1\n'):
            warm = self.version(text)
            self.assertEqual([warm.get('f', c, lambda: self.fail('warm')) == good(c) for c in range(6)], [True] * 6)
            warm = self.version(text)
            self.assertEqual([warm.get('f', c, lambda: self.fail('warm')) == broken(c) for c in range(6)],
                             [True, True, True, True, False, True])
            self.assertEqual((warm.hits, warm.misses), (6, 0))
        self.assertEqual(len(original_calls), 12)

    def test_per_name_keys_are_least_recently_used(self):
        with mock.patch.dict(os.environ, {oc.KEEP_ENV: '2'}):
            caches = []
            for text in ('V = 1\n', 'V = 2\n', 'V = 3\n'):
                cache = self.version(text)
                cache.get('f', 0, lambda: text)
                cache.save()
                caches.append(cache)
                os.utime(cache.path, (len(caches), len(caches)))   # distinct, ordered use times
            self.assertEqual(self.files(), sorted(c.path.name for c in caches[1:]), 'the oldest of three is dropped')
            self.assertEqual(self.version('V = 2\n').loaded, 1)   # using V2 makes it the most recent
            os.utime(caches[1].path, (10, 10))
            fourth = self.version('V = 4\n')
            fourth.get('f', 0, lambda: 4)
            fourth.save()
            self.assertEqual(self.files(), sorted([caches[1].path.name, fourth.path.name]), 'V3 was the least used')

    def test_directory_size_cap_drops_least_recently_used_files_but_never_the_new_one(self):
        blob = os.urandom(300_000)   # incompressible: each file is ~300 kB
        written = []
        with mock.patch.dict(os.environ, {oc.MAX_ENV: '1'}):   # 1 MiB cap
            for i, name in enumerate(('a', 'b', 'c', 'd', 'e')):
                script = self.base / f'{name}.py'
                script.write_text('X = 1\n')
                cache = oc.Cache(self.dir, name, script)
                cache.get('f', 0, lambda: blob + bytes([i]))
                cache.save()
                os.utime(cache.path, (100 + i, 100 + i))
                written.append(cache)
                total = sum(p.stat().st_size for p in self.dir.rglob('*.pickle.xz'))
                self.assertLessEqual(total, 1 << 20)
                self.assertTrue(cache.path.is_file(), 'the file just written stays')
            survivors = {p.parent.name for p in self.dir.rglob('*.pickle.xz')}
            self.assertEqual(survivors, {'c', 'd', 'e'}, 'the least recently used names went first')
            huge = oc.Cache(self.dir, 'huge', self.base / 'a.py')
            huge.get('f', 0, lambda: os.urandom(1_200_000))   # larger than the cap on its own
            huge.save()
            self.assertEqual([p.parent.name for p in self.dir.rglob('*.pickle.xz')], ['huge'])

    def test_stale_temporary_files_are_removed_fresh_ones_kept(self):
        cache = self.version('X = 1\n')
        cache.get('f', 0, lambda: 0)
        cache.save()
        stale, fresh = cache.folder / '.tmp-old.xz', cache.folder / '.tmp-new.xz'
        stale.write_bytes(b'x')
        fresh.write_bytes(b'x')
        os.utime(stale, (1, 1))
        oc.prune(self.dir)
        self.assertEqual((stale.exists(), fresh.exists(), cache.path.exists()), (False, True, True))

    def test_concurrent_writers_keep_every_entry_and_never_corrupt(self):
        self.script.write_text('SHARED = 1\n')
        worker = self.base / 'worker.py'
        worker.write_text(WORKER)
        go = self.base / 'go'
        rounds = 8
        procs = [subprocess.Popen([sys.executable, str(worker), str(ROOT / 'scripts'), str(self.dir),
                                   str(self.script), tag, str(go), str(rounds)], stderr=subprocess.PIPE)
                 for tag in ('job1', 'job2')]
        go.write_text('')
        for proc in procs:
            _, err = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0, err.decode()[-2000:])
        cache = oc.Cache(self.dir, 'shared', self.script)
        self.assertEqual(cache.loaded, 2 * rounds * 40, 'both workers\' entries survive')
        for tag in ('job1', 'job2'):
            for r in range(rounds):
                self.assertEqual(cache.get('f', (tag, r, 7), lambda: self.fail('lost')), (tag, r, 7) * 50)
        self.assertEqual(self.files('shared'), [cache.path.name])
        self.assertEqual([p.name for p in (self.dir / 'shared').glob('.tmp-*')], [], 'no temporary file left')


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
