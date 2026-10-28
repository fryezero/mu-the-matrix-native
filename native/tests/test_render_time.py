"""Portable temporal gates and opt-in installed-data repeatability, RENDER-TIME-001."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent))
import render_time as rt
from test_native_world import write_open_world


def series(source='native'):
    rows = []
    for i in range(3):
        r = {'frame': i * 10, 'steps': i * 10 + 1, 'world': 0, 'world_time': 100000 + i * 400}
        for group, size in rt.GROUPS.items():
            r[group] = [float(i)] * size
        r['camera'] = [i * 100., 0, 0, i * .1, 0, 0, 0, 39 - i, -48.5]
        for key in rt.HASHES:
            r[key] = str(i) * (64 if key == 'image_hash' else 16)
        rows.append(r)
    return {'version': 1, 'source': source, 'plan_sha256': 'fixture', 'phase': 'fixture',
            'draw_every_frame': True, 'maps': [{'name': 'synthetic', 'world': 0, 'tile': [128, 128],
              'script_sha256': 'fixture', 'expected_frames': [0, 10, 20], 'samples': rows}]}


class ComparisonTests(unittest.TestCase):
    def test_identical_repeat_and_counts(self):
        result = rt.compare(series(), series())
        self.assertTrue(result['passed'])
        self.assertEqual(result['maps'][0]['samples'], 3)

    def test_frozen_time_fields_caught_in_each_group(self):
        for group in rt.GROUPS:
            with self.subTest(group=group):
                ref, mutant = series(), series()
                for r in mutant['maps'][0]['samples']:
                    r[group] = ref['maps'][0]['samples'][0][group][:]
                self.assertFalse(rt.compare(ref, mutant)['passed'])

    def test_each_checksum_regression_caught(self):
        for key in rt.HASHES:
            mutant = series()
            mutant['maps'][0]['samples'][1][key] = 'f' * len(mutant['maps'][0]['samples'][1][key])
            self.assertFalse(rt.compare(series(), mutant)['passed'], key)

    def test_missing_nonmonotonic_and_nonfinite_samples_refused(self):
        for mutation in ('missing', 'duplicate', 'nonfinite', 'schema', 'hash'):
            with self.subTest(mutation=mutation):
                s = series(); rows = s['maps'][0]['samples']
                if mutation == 'missing': rows.pop()
                if mutation == 'duplicate': rows[1]['world_time'] = rows[0]['world_time']
                if mutation == 'nonfinite': rows[1]['lights'][0] = float('nan')
                if mutation == 'schema': rows[1]['objects'].pop()
                if mutation == 'hash': rows[1]['image_hash'] = ''
                with self.assertRaises(ValueError): rt.compare(series(), s)

    def test_unaligned_clock_or_script_or_map_cannot_pass(self):
        for key in ('phase', 'plan_sha256', 'draw_every_frame', 'script_sha256', 'world', 'tile'):
            s = series()
            if key in s: s[key] = None
            else: s['maps'][0][key] = None
            try: result = rt.compare(series(), s)
            except ValueError: continue
            self.assertFalse(result['passed'], key)

    def test_absolute_and_relative_clock_regressions_caught(self):
        for shift in (1, 400):
            s = series()
            for r in s['maps'][0]['samples']: r['world_time'] += shift
            self.assertFalse(rt.compare(series(), s)['passed'])

    def test_absolute_live_phase_cannot_be_hidden_by_epoch_subtraction(self):
        ref, native = series('live'), series()
        ref.update(phase='aligned', mugl_patches='off'); native['phase'] = 'aligned'
        for r in native['maps'][0]['samples']: r['world_time'] += 10000
        self.assertFalse(rt.compare(ref, native, 'live')['passed'])

    def test_stationary_path_cannot_pass_identical_repeat(self):
        s = series()
        for r in s['maps'][0]['samples']: r['camera'] = s['maps'][0]['samples'][0]['camera'][:]
        self.assertFalse(rt.compare(s, s)['passed'])

    def test_live_phase_and_mugl_off_are_required(self):
        ref, native = series('live'), series()
        self.assertFalse(rt.compare(ref, native, 'live')['passed'])
        ref['phase'] = native['phase'] = 'aligned'
        ref['mugl_patches'] = 'off'
        self.assertTrue(rt.compare(ref, native, 'live')['passed'])
        ref['mugl_patches'] = 'on'
        self.assertFalse(rt.compare(ref, native, 'live')['passed'])

    def test_live_worldtime_threshold_and_image_threshold(self):
        ref, native = series('live'), series()
        ref.update(phase='aligned', mugl_patches='off'); native['phase'] = 'aligned'
        native['maps'][0]['samples'][1]['world_time'] += 20
        native['maps'][0]['samples'][1]['image'][0] += 8
        self.assertTrue(rt.compare(ref, native, 'live')['passed'])
        native['maps'][0]['samples'][1]['image'][0] += .001
        self.assertFalse(rt.compare(ref, native, 'live')['passed'])
        native = copy.deepcopy(ref); native['source'] = 'native'
        native['maps'][0]['samples'][1]['world_time'] += 21
        self.assertFalse(rt.compare(ref, native, 'live')['passed'])

    def test_plan_covers_all_captured_views(self):
        p = rt.load_plan()
        self.assertEqual(len(p['maps']), 14)
        self.assertEqual(len({e['world'] for e in p['maps']}), 13)
        self.assertEqual(len(rt.schedule(p)), 21)
        for e in p['maps']:
            text = e['script_path'].read_text()
            self.assertIn('41:ldown:', text)
            self.assertIn('160:wheel:-1', text)


class NativeCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'native'), 'build/mu-walk'], check=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_open_world(Path(cls.tmp.name) / 'game')
        cls.script = Path(cls.tmp.name) / 'route.input'
        cls.script.write_text('0:focus:1 10:move:40,32 11:ldown:40,32 14:lup:40,32 20:wheel:1 40:wheel:-1')

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def run_capture(self, every=5, save=False, extra=()):
        cmd = [str(ROOT / 'native/build/mu-walk'), '--game-root', str(self.root), '--headless',
               '--backend', 'soft', '--frames', '61', '--width', '64', '--height', '64', '--no-audio',
               '--no-env', '--no-particles', '--time-series-every', str(every),
               '--input-script', str(self.script)]
        if save: cmd += ['--out-dir', str(Path(self.tmp.name) / 'frames'), '--every', '30']
        run = subprocess.run(cmd + list(extra), capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr[-1500:])
        return [json.loads(l) for l in run.stdout.splitlines() if l.startswith('{"time_series":')]

    def test_repeated_physical_input_is_deterministic(self):
        a, b = self.run_capture(), self.run_capture()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 13)
        self.assertEqual([r['steps'] for r in a], list(range(1, 62, 5)))
        self.assertEqual(a[0]['world_time'], 100000)
        self.assertEqual(a[-1]['world_time'], 102412)
        self.assertEqual(a[0]['camera'][7], 37)
        self.assertEqual(a[7]['camera'][7], 30)
        self.assertEqual(a[-1]['camera'][7], 37)
        self.assertGreaterEqual(rt.coverage(a)['walk_distance'], 50)
        self.assertGreaterEqual(rt.coverage(a)['fov_span'], 1)

    def test_png_and_sample_cadence_do_not_change_simulation(self):
        a, b, c = self.run_capture(), self.run_capture(save=True), self.run_capture(every=10)
        self.assertEqual(a, b)
        self.assertEqual(a[::2], c)
        self.assertEqual(len(list((Path(self.tmp.name) / 'frames').glob('*.png'))), 3)

    def test_explicit_worldtime_epoch(self):
        rows = self.run_capture(extra=('--time-series-start-ms', '250000'))
        self.assertEqual(rows[0]['world_time'], 250000)
        self.assertEqual(rows[-1]['world_time'], 252412)

    def test_invalid_sampling_rejected(self):
        for value in ('0', '-1', '1x', '10001'):
            run = subprocess.run([str(ROOT / 'native/build/mu-walk'), '--game-root', str(self.root),
                '--headless', '--time-series-every', value], capture_output=True)
            self.assertEqual(run.returncode, 2, value)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private installed-data temporal tour is opt-in')
class InstalledDataTests(unittest.TestCase):
    def test_all_captured_maps_repeat_with_installed_data(self):
        # Explicit requests fail on missing data. These are paths, never copied fixtures.
        root = os.environ.get('MU_GAME_ROOT')
        objects = os.environ.get('MU_RENDER_TIME_OBJECTS')
        self.assertTrue(root and Path(root).is_dir(), 'MU_GAME_ROOT required for requested temporal integration')
        self.assertTrue(objects and Path(objects).is_dir(), 'MU_RENDER_TIME_OBJECTS required: captured plain placements')
        binary = ROOT / 'native/build/mu-world'
        subprocess.run(['make', '-s', '-C', str(ROOT / 'native'), 'build/mu-world'], check=True)
        with tempfile.TemporaryDirectory() as tmp:
            a = rt.capture(rt.PLAN, binary, root, objects, Path(tmp) / 'a')
            b = rt.capture(rt.PLAN, binary, root, objects, Path(tmp) / 'b')
            result = rt.compare(a, b)
            self.assertTrue(result['passed'], json.dumps(result))
            self.assertEqual(len(result['maps']), 14)
            self.assertEqual(sum(e['samples'] for e in result['maps']), 294)
            baseline = os.environ.get('MU_RENDER_TIME_BASELINE')
            if baseline:
                prior = rt.compare(json.loads(Path(baseline).read_text()), b)
                self.assertTrue(prior['passed'], json.dumps(prior))
            # Icarus emits particles during drawing. A sample-only draw mutant changes common rows.
            plan = json.loads(rt.PLAN.read_text())
            plan['sample_every'] = 5
            for e in plan['maps']: e['script'] = str(rt.PLAN.parent / e['script'])
            plan_path = Path(tmp) / 'denser.json'
            plan_path.write_text(json.dumps(plan))
            dense = rt.capture(plan_path, binary, root, objects, Path(tmp) / 'dense', ['10-icarus'])
            expected = next(e['samples'] for e in b['maps'] if e['name'] == '10-icarus')
            self.assertEqual(expected, dense['maps'][0]['samples'][::2])
