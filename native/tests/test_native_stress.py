"""NATIVE-PERF-002: workload integrity, budget failures and exact ordered rendering."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path[:0] = [str(HERE), str(NATIVE / 'tools'), str(NATIVE.parent / 'scripts')]
import bench_stress as bench
import imgdiff
from test_native_combat import write_combat_world


class BenchmarkContract(unittest.TestCase):
    def test_quality_overrides_are_rejected_even_when_empty(self):
        args = ['--game-root', '/unused', '--data', '/unused', '--gfx-lib', '/unused',
                '--out', '/unused']
        for key in ('MU_GFX_NO_ITEM_MODELS', 'MU_GFX_NO_ICON_MODELS', 'MU_GFX_NO_SKILLS',
                    'MU_GFX_PLAIN_ITEMS'):
            for value in ('', '1'):
                with self.subTest(key=key, value=value), \
                        mock.patch.dict(os.environ, {key: value}, clear=True), \
                        mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('quality guard bypassed')), \
                        contextlib.redirect_stderr(io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as caught:
                        bench.main(args)
                    self.assertEqual(caught.exception.code, 2)
                    self.assertIn(f'{key} would omit part of the stress workload', err.getvalue())

    def test_generated_crowd_has_eighty_distinct_equipped_players(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, a = bench.fixtures(Path(tmp), (182, 128), 80)
            players, actors = p.read_text().splitlines(), a.read_text().splitlines()
            self.assertEqual(len(players), 80)
            self.assertEqual(len({line.split()[1] for line in players}), 80)
            self.assertEqual(len({line.split(' at=')[1].split()[0] for line in players}), 80)
            for line in players:
                for part in ('helm=', 'armor=', 'pants=', 'gloves=', 'boots=', 'weapon0=', 'wing='):
                    self.assertIn(part, line)
            self.assertEqual(len(actors), 32)

    def test_budget_rejects_slow_or_short_measurements(self):
        r = {'frames': 200, 'fps': 25.0, 'work_ms': {'p95': 30, 'p99': 35}, 'frame_ms': {'p95': 40, 'p99': 41}}
        self.assertEqual(bench.check(r, headless=False), [])
        for key, value in [('fps', 24.5), ('frames', 99)]:
            self.assertTrue(bench.check(dict(r, **{key: value}), headless=False))
        self.assertTrue(bench.check(dict(r, work_ms={'p95': 39, 'p99': 45}), headless=True))
        self.assertTrue(bench.check(dict(r, fps=24.9), headless=True))
        self.assertEqual(bench.check(dict(r, fps=90), headless=True), [])

    def test_nonfinite_or_missing_metrics_cannot_pass(self):
        r = {'frames': 200, 'fps': 25.0, 'work_ms': {'p95': 30, 'p99': 35},
             'frame_ms': {'p95': 40, 'p99': 41}}
        for value in (float('nan'), float('inf'), -1, None):
            self.assertTrue(bench.check(dict(r, fps=value), headless=True))
            self.assertTrue(bench.check(dict(r, work_ms={'p95': value, 'p99': 35}), headless=False))
        self.assertTrue(bench.check(dict(r, frame_ms={}), headless=False))

    def test_pacing_tails_fail_even_at_25_fps(self):
        result = {'frames': 200, 'fps': 25, 'work_ms': {'p95': 30, 'p99': 35},
                  'frame_ms': {'p95': 44, 'p99': 46}}
        self.assertIn('frame pacing p95 > 41 ms or p99 > 42 ms', bench.check(result, headless=False))

    def test_metal_missing_unsupported_invalid_and_cached_frames(self):
        import perf_report
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'metal.jsonl'
            rows = [{'supported': True}, {'frame': 1, 'gpu_ms': 2}, {'frame': 1, 'gpu_ms': 3},
                    {'frame': 1, 'event': 'end', 'submissions': 2},
                    {'frame': 2, 'event': 'end', 'submissions': 0},
                    {'frame': 3, 'event': 'end', 'submissions': 1},
                    {'frame': 4, 'map_error': True}, {'frame': 4, 'event': 'end', 'submissions': 1},
                    {'frame': 0, 'gpu_ms': 999}, {'frame': 5, 'gpu_ms': -1},
                    {'frame': 5, 'event': 'end', 'submissions': 1}]
            log.write_text('\n'.join(map(json.dumps, rows)))
            r = perf_report.metal_summary(log, {1, 2, 3, 4, 5, 6})
            self.assertEqual((r['samples'], r['missing_frames'], r['mean']), (2, 4, 2.5))
            rows[0]['supported'] = False
            log.write_text('\n'.join(map(json.dumps, rows)))
            self.assertIsNone(perf_report.metal_summary(log, {1, 2})['mean'])

    def test_regression_ceiling_is_separate_from_the_25_hz_target(self):
        limits = {'min_fps': 18, 'work_p95_ms': 68, 'work_p99_ms': 80, 'cpu_mean_ms': 55}
        result = {'frames': 200, 'fps': 21, 'work_ms': {'p95': 56, 'p99': 63},
                  'phases': {'cpu': {'mean': 45}}, 'frame_ms': {'p95': 57, 'p99': 65}}
        self.assertEqual(bench.regression(result, limits), [])
        self.assertTrue(bench.check(result, headless=False))
        self.assertTrue(bench.regression(dict(result, fps=15), limits))
        self.assertTrue(bench.regression(dict(result, phases={'cpu': {'mean': 60}}), limits))
        self.assertTrue(bench.regression(dict(result, work_ms={'p95': 90, 'p99': 100}), limits))

    def test_workload_rejects_missing_players_or_effects(self):
        rows = [{'players': {'count': 80, 'viewport_packets': 80, 'addinfo': 80}}, {'actors': 32},
                {'gfx': {'renders': 100, 'inventory_open': 1, 'item_models_missing': 0, 'item_models': 10, 'base_mode': 1}},
                {'map': True, 'map_shown': 1}, {'combat': True, 'skills': 4, 'area_requests': 4,
                                             'particles_created': 12, 'fx_created': 20, 'joints_created': 12},
                {'particles': True, 'created': 100, 'dropped': 0, 'overflow': 0}]
        rows += [{'player': i, 'loaded': [0, 1, 1, 1, 1, 1, 1, 0, 1],
                  'textures_missing': [-1, 0, 0, 0, 0, 0, 0, -1, 0]} for i in range(80)]
        self.assertEqual(bench.workload(rows, 80)['players']['count'], 80)
        for index in range(len(rows)):
            with self.assertRaises(ValueError):
                bench.workload(rows[:index] + rows[index + 1:], 80)
        rows[0]['players']['viewport_packets'] = 8
        with self.assertRaises(ValueError):
            bench.workload(rows, 80)


class DirectCornerStream(unittest.TestCase):
    def test_stream_and_tables_match_and_detect_two_mutants(self):
        import validate_meshdraw as vm
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-render'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            cc = shutil.which('clang') or shutil.which('cc')
            if not cc:
                self.skipTest('needs a C compiler')
            hosts = []
            for mutant in range(3):
                host = directory / f'host-{mutant}'
                subprocess.run([cc, '-std=c11', '-O2', '-ffp-contract=off', '-fno-fast-math',
                                '-Wall', '-Wextra', '-Werror', f'-DPERF_MUTANT={mutant}',
                                str(HERE / 'perf_corner_host.c'), str(NATIVE / 'core/mu_meshdraw.c'),
                                str(NATIVE / 'core/mu_meshdraw_case.c'), '-lm', '-o', str(host)],
                               check=True, capture_output=True)
                hosts.append(host)
            killed = set()
            cases = vm.pinned_cases(directory)
            self.assertEqual(len(cases), 247)
            for label, case, _ in cases:
                path = directory / 'case.bin'
                path.write_bytes(case)
                literal = subprocess.check_output([str(hosts[0]), '0', str(path)])
                self.assertEqual(literal, subprocess.check_output([str(hosts[0]), '1', str(path)]), label)
                for mutant in (1, 2):
                    if subprocess.check_output([str(hosts[mutant]), '1', str(path)]) != literal:
                        killed.add(mutant)
            self.assertEqual(killed, {1, 2})


@unittest.skipUnless(sys.platform == 'darwin', 'offscreen GL needs macOS')
class OrderedRendering(unittest.TestCase):
    def test_absent_players_preserves_the_hero_batch(self):
        subprocess.run(['make', '-C', str(NATIVE), 'world'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'game'
            root.mkdir()
            write_combat_world(root)
            outputs = []
            for mode in ('1', '0'):
                out = Path(tmp) / mode
                r = subprocess.run([str(NATIVE / 'build/mu-world'), '--game-root', str(root),
                                    '--headless', '--backend', 'gl', '--frames', '3', '--every', '1',
                                    '--out-dir', str(out), '--width', '160', '--height', '120',
                                    '--tile', '120,120', '--no-audio'],
                                   env=dict(os.environ, MU_PERF_002_BASELINE=mode),
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr[-2000:])
                outputs.append(out)
            for p in outputs[0].glob('*.png'):
                self.assertTrue(imgdiff.compare(p, outputs[1] / p.name, 0)['identical'], p.name)

    def test_scaled_demo_preserves_pixels_and_state(self):
        subprocess.run(['make', '-C', str(NATIVE), 'world'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'game'
            root.mkdir()
            write_combat_world(root)
            players = Path(tmp) / 'players.txt'
            players.write_text('\n'.join(f'player P{i:02} class=1 at={117+i%8},{118+i//8} '
                                         'route=121,122;120,120 idle=5 die=8 respawn=12' for i in range(80)))
            captures = []
            states = []
            for mode in ('1', '0'):
                out = Path(tmp) / mode
                result = subprocess.run([str(NATIVE / 'build/mu-world'), '--game-root', str(root),
                                         '--headless', '--backend', 'gl', '--frames', '32', '--every', '10',
                                         '--out-dir', str(out), '--width', '160', '--height', '120',
                                         '--tile', '120,120', '--players', str(players), '--player-range', '40',
                                         '--no-audio', '--perf-fov', '65'],
                                        env=dict(os.environ, MU_PERF_002_BASELINE=mode),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                rows = [json.loads(l) for l in result.stdout.splitlines() if l.startswith('{')]
                summary = next(r['players'] for r in rows if isinstance(r.get('players'), dict))
                self.assertEqual(summary['count'], 80)
                self.assertGreaterEqual(summary['viewport_packets'], 80)
                self.assertEqual(summary['addinfo'], 80)
                states.append([r for r in rows if 'players_frame' in r or 'players' in r])
                captures.append(out)
            self.assertEqual(states[0], states[1])
            files = sorted(captures[0].glob('*.png'))
            self.assertEqual(len(files), 5)
            for p in files:
                self.assertTrue(imgdiff.compare(p, captures[1] / p.name, 0)['identical'], p.name)


if __name__ == '__main__':
    unittest.main()
