"""RENDER-TIME-002 live exporter on synthetic sampler/injector output (no client, no captured bytes)."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_time as rt
import render_time_live as live

MUGL_OFF = live.mugl_provenance('=== hotpatch mask 380460463: funcs 9/9\n=== hotpatch mask 0: funcs 0/9 sites 0 peep 0\n',
                                '0\n', 'full+vbo\n')


def sampler_lines(epoch=250000.0, logic0=9000, torn_at=(), wide_at=()):
    """rtsample output for the Lorencia plan: one post-draw edge and one logic step per 40 ms."""
    out = [{'kind': 'preflight', 'world': 0, 'hero_live': 1, 'hero': [13750., 13050., 170.], 'tile': [137, 130],
            'hero_frame': 0.5, 'hero_action': 0, 'eye': [13750., 12100., 1100.], 'angle': [-48.5, 0., -45.],
            'fov': 35., 'world_time': epoch - 3000, 'logic': logic0 - 75, 'cframe': 50, 'presented': 40,
            'objects': 1200, 'ranges': 3, 'others': [450.5, 1200.]}]
    for k in rt.schedule(rt.load_plan()):
        for attempt in (1, 2) if k in torn_at or k in wide_at else (1,):
            wt, logic = epoch + 40 * k + 40 * (attempt - 1), logic0 + k + (attempt - 1)
            pre = {'presented': 100 + k + attempt - 1, 'logic': logic, 'cframe': 110 + k + attempt - 1,
                   'world_time': wt, 'host_us': 1e6 + 40000 * k}
            post = dict(pre, host_us=pre['host_us'] + 4000)
            if attempt == 1 and k in torn_at:
                post['logic'] += 1
            if attempt == 1 and k in wide_at:
                post['world_time'] += 21
            hero = 13750 + min(k, 60)
            out.append({'kind': 'sample', 'frame': k, 'attempt': attempt, 'world': 0, 'objects_rewalked': 0,
                        'pre': pre, 'post': post,
                        'camera': [hero, 13050, 170, k * .1, hero, 12100, 1100, 35 + (k > 90) * 2 - (k > 160) * 2, -48.5],
                        'objects': [1200.] + [float(k)] * 16 + [300., 0.], 'particles': [3.] + [k * .5] * 8 + [0.],
                        'environment': [5., k, k, k, k, 1., 80., k], 'lights': [.5, .5, .5, .6, .6, .6],
                        'joints': 0, 'particle_list': {'size': 3, 'walked': 3}})
            if k == 0:
                out.append({'kind': 'arm', 'logic': logic0, 'cframe': 110, 'presented': 100, 'world_time': epoch,
                            'host_us': 1e6 + 4100})
    out.append({'kind': 'end', 'edges': 260, 'torn': len(torn_at) + len(wide_at), 'arm_logic': logic0})
    return out


def input_log(late=1.0, size='640 480'):
    events = live.parse_script(rt.load_plan()['maps'][0]['script_path'].read_text())
    return f'client 100 132 {size} foreground 1\n' + ''.join(
        f'event {f} {v} {x} {y} due {f * 40.0:.1f} sent {f * 40.0 + late:.1f}\n' for f, v, x, y in events)


class LiveExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def export(self, lines=None, log=None, mugl=MUGL_OFF):
        samples, inputs = self.tmp / 'samples.jsonl', self.tmp / 'inputs.log'
        samples.write_text(''.join(json.dumps(l) + '\n' for l in (lines or sampler_lines())))
        inputs.write_text(log or input_log())
        return live.export(samples, inputs, rt.PLAN, '00b-lorencia', mugl, self.tmp / 'out')

    def test_export_matches_schema_and_records_phase_evidence(self):
        s = self.export()
        e = s['maps'][0]
        self.assertEqual(len(e['samples']), 21)
        self.assertEqual([r['frame'] for r in e['samples']], rt.schedule(rt.load_plan()))
        self.assertEqual(e['samples'][0]['world_time'], 250000)
        self.assertEqual(s['phase'], 'unaligned')
        self.assertEqual(s['mugl_patches'], 'off')
        ev = s['phase_evidence']
        self.assertEqual(ev['arm']['logic'], 9000)
        self.assertEqual([b['logic'] for b in ev['samples']], rt.schedule(rt.load_plan()))
        self.assertEqual(ev['client_area'], [640, 480])
        self.assertEqual(e['tile'], [137, 130])
        self.assertEqual(e['neighbours_within_300'], 0)
        plan = json.loads((self.tmp / 'out/native-plan.json').read_text())
        self.assertEqual(plan['start_world_time_ms'], 250000)
        self.assertEqual(s['plan_sha256'], rt.digest(self.tmp / 'out/native-plan.json'))
        self.assertEqual(rt.load_plan(self.tmp / 'out/native-plan.json')['maps'][0]['tile'], [137, 130])
        # RENDER-TIME-003: the twin declares that the live UI layer (base.swf) took the wheel
        self.assertIs(plan['maps'][0]['wheel_ui_hit'], True)

    def test_plan_wheel_ui_hit_must_be_boolean(self):
        self.export()
        path = self.tmp / 'out/native-plan.json'
        plan = json.loads(path.read_text())
        plan['maps'][0]['wheel_ui_hit'] = 1
        path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            rt.load_plan(path)

    def test_torn_and_wide_brackets_are_rejected_and_retried(self):
        s = self.export(sampler_lines(torn_at=(10,), wide_at=(100,)))
        rejected = s['phase_evidence']['rejected']
        self.assertEqual([(r['frame'], r['torn']) for r in rejected], [(10, True), (100, False)])
        self.assertEqual(rejected[1]['bracket_ms'], 21)
        self.assertEqual(s['maps'][0]['samples'][1]['steps'] - 9000, 11)   # the retry is one step late, recorded

    def test_missing_world_change_and_arm_mismatch_refused(self):
        for mutation in ('missing', 'world', 'arm', 'all_torn'):
            with self.subTest(mutation=mutation):
                lines = sampler_lines()
                if mutation == 'missing':
                    lines = [l for l in lines if l.get('frame') != 50]
                if mutation == 'world':
                    next(l for l in lines if l.get('frame') == 70)['world'] = 3
                if mutation == 'arm':
                    next(l for l in lines if l['kind'] == 'arm')['logic'] += 1
                if mutation == 'all_torn':
                    for l in lines:
                        if l.get('frame') == 30:
                            l['post']['presented'] += 1
                with self.assertRaises(ValueError):
                    self.export(lines)

    def test_input_log_must_replay_the_plan_script(self):
        log = input_log().splitlines()
        with self.assertRaises(ValueError):
            self.export(log='\n'.join(l for l in log if 'wheel' not in l) + '\n')
        with self.assertRaises(ValueError):
            self.export(log='\n'.join(log[1:]) + '\n')

    def test_mugl_provenance_requires_logged_zero_mask(self):
        self.assertEqual(MUGL_OFF['effective_mask'], 0)
        self.assertEqual(MUGL_OFF['mask_lines'], 2)
        on = live.mugl_provenance('=== hotpatch mask 380460463: funcs 9/9\n', '380460463\n', 'full+vbo')
        self.assertEqual(on['patches'], 'on')
        self.assertEqual(live.mugl_provenance('=== hotpatch mask 0: x\n', '7\n', 'full')['patches'], 'on')
        with self.assertRaises(ValueError):
            live.mugl_provenance('mugl loaded\n', '0\n', 'full')
        s = self.export(mugl=on)
        self.assertEqual(s['mugl_patches'], 'on')

    def test_schedule_parser_accepts_only_live_subset(self):
        events = live.parse_script(rt.load_plan()['maps'][0]['script_path'].read_text())
        self.assertEqual(events[0], (40, 'move', 400, 240))
        self.assertEqual([e for e in events if e[1] == 'wheel'], [(90, 'wheel', 1, 0), (160, 'wheel', -1, 0)])
        self.assertEqual(len(events), 8)
        for bad in ('3:key:13', '0:focus:0', '5:focus:1', '1:move:1', '2:wheel:101', 'x:move:1,2', '4:text:a'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                live.parse_script(bad)
        self.assertEqual(live.parse_script('9:lup:1,2 # c\n9:move:3,4;1:ldown:0,0'),
                         [(1, 'ldown', 0, 0), (9, 'lup', 1, 2), (9, 'move', 3, 4)])

    def test_cli_schedule_and_export(self):
        sched = self.tmp / 'sched.txt'
        script = rt.PLAN.parent / '00b-lorencia.input'
        run = subprocess.run([sys.executable, str(ROOT / 'scripts/render_time_live.py'), 'schedule', str(script), str(sched)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(sched.read_text().splitlines()[1], '41 ldown 400 240')
        (self.tmp / 'samples.jsonl').write_text(''.join(json.dumps(l) + '\n' for l in sampler_lines()))
        (self.tmp / 'inputs.log').write_text(input_log())
        (self.tmp / 'stats.txt').write_text('=== hotpatch mask 0: funcs 0/9 sites 0 peep 0\n')
        (self.tmp / 'mask.txt').write_text('0\n')
        (self.tmp / 'mode.txt').write_text('full+vbo\n')
        args = [sys.executable, str(ROOT / 'scripts/render_time_live.py'), 'export', '--samples', str(self.tmp / 'samples.jsonl'),
                '--inputs', str(self.tmp / 'inputs.log'), '--mugl-stats', str(self.tmp / 'stats.txt'),
                '--mugl-mask', str(self.tmp / 'mask.txt'), '--mugl-mode', str(self.tmp / 'mode.txt'), '--out', str(self.tmp / 'o')]
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['samples'], 21)
        (self.tmp / 'mask.txt').write_text('')
        self.assertEqual(subprocess.run(args[:-2] + ['--out', str(self.tmp / 'p')], capture_output=True).returncode, 0)
        (self.tmp / 'stats.txt').write_text('no mask line\n')
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)


class LiveSelectionAndPairingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def export(self, lines, size='640 480'):
        (self.tmp / 's.jsonl').write_text(''.join(json.dumps(l) + '\n' for l in lines))
        (self.tmp / 'i.log').write_text(input_log(size=size))
        return live.export(self.tmp / 's.jsonl', self.tmp / 'i.log', rt.PLAN, '00b-lorencia', MUGL_OFF, self.tmp / 'out')

    def test_all_edges_selection_skips_worldtime_moves(self):
        lines = sampler_lines()
        out = []
        for l in lines:
            out.append(l)
            if l['kind'] == 'sample' and l['frame'] in (40, 90):
                # extra edges before the next target: one where WorldTime moved during the read, one clean
                for j, wt_move in ((3, 50), (7, 0)):
                    e = copy.deepcopy(l); e['frame'] = -1; e['attempt'] = 0
                    for side in ('pre', 'post'):
                        e[side]['logic'] += j; e[side]['presented'] += j; e[side]['cframe'] += j
                        e[side]['world_time'] += 40 * j
                    e['post']['world_time'] += wt_move
                    out.append(e)
        # make the frame-50 target itself a WorldTime move: the selection must fall through to frame 60's read
        target = next(l for l in out if l.get('frame') == 50)
        target['post']['world_time'] += 49
        s = self.export(out)
        ev = s['phase_evidence']
        self.assertEqual([(r['frame'], r['logic'], r['torn'], r['bracket_ms']) for r in ev['rejected']],
                         [(50, 50, False, 49), (90, 93, False, 50)])
        logic = {b['frame']: b['logic'] for b in ev['samples']}
        # each frame takes the next accepted read: late reads are recorded as late, never relabelled
        self.assertEqual([logic[k] for k in (40, 50, 60, 80, 90, 100)], [40, 60, 70, 90, 97, 100])

    def test_scaled_script_and_dense_native_plan(self):
        s = self.export(sampler_lines(), size='960 600')
        plan = rt.load_plan(self.tmp / 'out/native-plan.json')
        self.assertEqual((plan['width'], plan['height'], plan['sample_every'], plan['frames']), (960, 600, 1, 201))
        self.assertEqual(len(rt.schedule(plan)), 201)
        events = live.parse_script(plan['maps'][0]['script_path'].read_text())
        self.assertEqual(events[:3], [(40, 'move', 600, 300), (41, 'ldown', 600, 300), (44, 'lup', 600, 300)])
        self.assertEqual(events[4], (120, 'move', 390, 300))
        e = s['maps'][0]
        self.assertEqual(e['script_sha256'], rt.digest(plan['maps'][0]['script_path']))
        self.assertEqual(e['base_script_sha256'], rt.digest(rt.PLAN.parent / '00b-lorencia.input'))
        self.assertEqual(s['phase_evidence']['client_area'], [960, 600])
        late = sampler_lines(torn_at=(200,))
        self.assertEqual(rt.load_plan(self.export(late) and self.tmp / 'out/native-plan.json')['frames'], 202)

    def dense_native(self, live_series, frames=205, base=1):
        rows = []
        for i in range(frames):
            r = {'frame': i, 'world': 0, 'world_time': 250000 + 40 * i, 'steps': base + i}
            for g, n in rt.GROUPS.items():
                r[g] = [float(i)] * n
            for key in rt.HASHES:
                r[key] = '0' * (64 if key == 'image_hash' else 16)
            rows.append(r)
        m = live_series['maps'][0]
        return {'version': 1, 'source': 'native', 'draw_every_frame': True, 'plan_sha256': live_series['plan_sha256'],
                'phase': 'native-fresh-world-seed-1', 'maps': [{'name': m['name'], 'world': 0, 'tile': m['tile'],
                'script_sha256': m['script_sha256'], 'expected_frames': list(range(frames)), 'samples': rows}]}

    def test_pair_uses_recorded_logic_ordinals(self):
        s = self.export(sampler_lines(torn_at=(110,)))
        paired = live.pair(s, self.dense_native(s))
        rows = paired['maps'][0]['samples']
        self.assertEqual([r['frame'] for r in rows], rt.schedule(rt.load_plan()))
        self.assertEqual(rows[11]['native_frame'], 111)
        self.assertEqual(rows[11]['camera'][0], 111.0)
        self.assertEqual(rows[12]['native_frame'], 120)
        result = rt.compare(s, paired, 'live')
        self.assertFalse(any('relative steps' in f for f in result['maps'][0]['failures']))
        self.assertIn('phase', ' '.join(result['errors']))
        with self.assertRaises(ValueError):
            live.pair(s, self.dense_native(s, frames=150))
        sparse = self.dense_native(s)
        sparse['maps'][0]['samples'][5]['steps'] += 1
        for r in sparse['maps'][0]['samples'][6:]: r['steps'] += 1
        with self.assertRaises(ValueError):
            live.pair(s, sparse)
        other = self.dense_native(s); other['plan_sha256'] = 'x'
        with self.assertRaises(ValueError):
            live.pair(s, other)


    def test_summary_reports_errors_without_records(self):
        s = self.export(sampler_lines(torn_at=(110,)))
        paired = live.pair(s, self.dense_native(s))
        report = rt.compare(s, paired, 'live')
        out = live.summarize(s, paired, report, self.dense_native(s))
        self.assertEqual(out['late_samples'], [[110, 111]])
        self.assertEqual(out['max_error']['image'], [None] * 48)
        self.assertEqual(out['max_error']['sky'][:3], [None] * 3)
        self.assertNotIn('rng', out['max_error'])
        self.assertEqual(out['compare']['failure_count'], report['maps'][0]['failure_count'])
        self.assertEqual(len(out['diagnostic_camera_error']), 21)
        self.assertNotIn('"samples"', json.dumps(out))   # no per-sample records


class LiveCompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        samples, inputs = self.tmp / 's.jsonl', self.tmp / 'i.log'
        samples.write_text(''.join(json.dumps(l) + '\n' for l in sampler_lines()))
        inputs.write_text(input_log())
        self.live = live.export(samples, inputs, rt.PLAN, '00b-lorencia', MUGL_OFF, self.tmp / 'out')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def native_twin(self):
        n = copy.deepcopy(self.live)
        n.update(source='native', draw_every_frame=True)
        for e in n['maps']:
            e.pop('unavailable')
            for r in e['samples']:
                r['rng'] = [1., 2., 3., 4., 5.]
                r['image'] = [100.] * 48
                r['sky'][:3] = [10., 20., 14.]
                for key in rt.HASHES:
                    r[key] = '0' * (64 if key == 'image_hash' else 16)
        return n

    def test_unaligned_live_phase_cannot_pass(self):
        result = rt.compare(self.live, self.native_twin(), 'live')
        self.assertFalse(result['passed'])
        self.assertIn('phase', ' '.join(result['errors']))
        self.assertEqual(result['maps'][0]['failure_count'], 0)   # values agree; only the phase gate fails

    def test_unavailable_components_are_reported_not_scored(self):
        ref = copy.deepcopy(self.live); ref['phase'] = 'aligned'
        native = self.native_twin(); native['phase'] = 'aligned'
        result = rt.compare(ref, native, 'live')
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['maps'][0]['not_compared'], live.UNAVAILABLE)
        native['maps'][0]['samples'][3]['sky'][3] += 1   # joint count is observed: still scored
        self.assertFalse(rt.compare(ref, native, 'live')['passed'])
        ref['maps'][0]['unavailable'] = {'camera': [99]}
        self.assertFalse(rt.compare(ref, self.native_twin() | {'phase': 'aligned'}, 'live')['passed'])

    def test_unavailable_is_ignored_in_native_mode(self):
        a = self.native_twin(); b = self.native_twin()
        a['maps'][0]['unavailable'] = {'image': list(range(48))}
        b['maps'][0]['samples'][2]['image'][0] += 1
        self.assertFalse(rt.compare(a, b)['passed'])

    def test_camera_and_object_limits_apply_to_live_values(self):
        ref = copy.deepcopy(self.live); ref['phase'] = 'aligned'
        native = self.native_twin(); native['phase'] = 'aligned'
        native['maps'][0]['samples'][5]['camera'][4] += 1.5
        native['maps'][0]['samples'][6]['objects'][1] += 1200 * .06   # mean frame +0.06 > 0.05
        failures = rt.compare(ref, native, 'live')['maps'][0]['failures']
        self.assertEqual(failures, ['frame 50: camera[4]', 'frame 60: objects[1]'])


if __name__ == '__main__':
    unittest.main()
