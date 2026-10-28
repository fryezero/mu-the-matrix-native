#!/usr/bin/env python3
"""RENDER-TIME-001: bounded native full-draw tours and fail-closed temporal comparisons.

Capture emits compact JSON, three PNGs per view and no object/light dumps. Native repeats are
regressions, not evidence of equality to the original client. See docs/research/client-render-time.md.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'scripts/render_time/paths.json'
GROUPS = {'camera': 9, 'objects': 16, 'particles': 10, 'environment': 8,
          'lights': 6, 'sky': 4, 'rng': 5, 'image': 48}
HASHES = ('objects_hash', 'particles_hash', 'environment_hash', 'lights_hash', 'image_hash')
NATIVE_TOLERANCE = 1e-6
# Live thresholds are per-component absolute error after normalizing object/pool sums by count.
LIVE_LIMITS = {
    'camera': [1, 1, 1, .05, 1, 1, 1, .01, .01],
    'objects': [0, .05, .05, .01, .01, .01, .01, 1, 1, 1, .1, .1, .1, .01, .01, .01],
    'particles': [.1, 5, 5, 5, 2, .05, .05, 1, 0, .1],
    'environment': [.1, 5, 5, 5, .05, .05, .1, 2],
    'lights': [1e-6, 1e-6, 1e-6, .05, .05, .05],
    'sky': [1, 1, 1, .1], 'image': [8] * 48,
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_plan(path=PLAN):
    path = Path(path)
    p = json.loads(path.read_text())
    if p['version'] != 1 or not 21 <= p['frames'] <= 10001 or not 1 <= p['sample_every'] <= 10000:
        raise ValueError('invalid time-series plan')
    if p['frames'] // p['sample_every'] > 1000 or p['save_every'] < (p['frames'] - 1) / 2:
        raise ValueError('plan exceeds 1001 samples or three PNGs per view')
    if not p['maps'] or len({e['name'] for e in p['maps']}) != len(p['maps']):
        raise ValueError('empty/duplicate maps')
    for e in p['maps']:
        if Path(e['name']).name != e['name'] or e['name'] in ('.', '..'):
            raise ValueError('unsafe map name')
        if not 0 <= e['world'] <= 255 or len(e['tile']) != 2 or any(not 0 <= x <= 255 for x in e['tile']):
            raise ValueError('invalid world/tile')
        e['script_path'] = path.parent / e['script']
        if not e['script_path'].is_file():
            raise ValueError(f"missing script {e['script']}")
    return p


def schedule(p):
    return sorted(set(range(0, p['frames'], p['sample_every'])) | {p['frames'] - 1})


def validate_series(s):
    if s.get('version') != 1 or s.get('source') not in ('native', 'live') or not s.get('maps'):
        raise ValueError('series needs version, source and maps')
    names = set()
    for e in s['maps']:
        if e['name'] in names:
            raise ValueError('duplicate map')
        names.add(e['name'])
        rows = e['samples']
        if len(rows) < 3 or len(rows) > 1001:
            raise ValueError('need 3..1001 temporal samples per map')
        previous = None
        for r in rows:
            for k in ('frame', 'world_time', 'steps'):
                if type(r[k]) not in (int, float) or not math.isfinite(r[k]):
                    raise ValueError(f'nonfinite {k}')
            if r['world'] != e['world'] or r['frame'] < 0 or r['steps'] < 0:
                raise ValueError('world/frame/steps mismatch')
            if previous and (r['frame'] <= previous['frame'] or r['world_time'] <= previous['world_time'] or
                             r['steps'] <= previous['steps']):
                raise ValueError('nonmonotonic time series')
            previous = r
            for group, count in GROUPS.items():
                values = r[group]
                if len(values) != count or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
                    raise ValueError(f'invalid {group}')
            if s['source'] == 'native':
                for key in HASHES:
                    value = r[key]
                    if len(value) != (64 if key == 'image_hash' else 16) or any(c not in '0123456789abcdef' for c in value):
                        raise ValueError(f'invalid {key}')
        if e.get('expected_frames') != [r['frame'] for r in rows]:
            raise ValueError('missing, extra or reordered samples')
    return s


def coverage(rows):
    camera = [r['camera'] for r in rows]
    start = camera[0]
    return {'walk_distance': round(max(math.dist(start[:3], c[:3]) for c in camera), 6),
            'fov_span': round(max(c[7] for c in camera) - min(c[7] for c in camera), 6),
            'varying_groups': [g for g in GROUPS if any(r[g] != rows[0][g] for r in rows[1:])]}


def capture(plan_path, binary, game_root, objects_dir, out, only=None, backend='gl'):
    p = load_plan(plan_path)
    out = Path(out)
    if out.exists():
        raise ValueError('capture output must be a new directory')
    if shutil.disk_usage(out.parent).free < 5 * 1024**3:
        raise ValueError('less than 5 GiB free; no captures produced')
    entries = [e for e in p['maps'] if only is None or e['name'] in only]
    if not entries or (only and set(only) != {e['name'] for e in entries}):
        raise ValueError('unknown/empty map selection')
    if not Path(game_root).is_dir() or (objects_dir and not Path(objects_dir).is_dir()):
        raise ValueError('missing private input directory')
    out.mkdir()
    result = {'version': 1, 'source': 'native', 'draw_every_frame': True,
              'plan_sha256': digest(plan_path), 'binary_sha256': digest(binary),
              'phase': 'native-fresh-world-seed-1', 'maps': []}
    for e in entries:
        dest = out / e['name']
        dest.mkdir()
        cmd = [str(binary), '--headless', '--backend', backend, '--game-root', str(game_root),
               '--world', str(e['world']), '--tile', ','.join(map(str, e['tile'])),
               '--width', str(p['width']), '--height', str(p['height']), '--no-audio',
               '--no-names', '--no-helpers', '--no-map', '--no-players',
               '--frames', str(p['frames']), '--every', str(p['save_every']), '--out-dir', str(dest),
               '--time-series-every', str(p['sample_every']), '--input-script', str(e['script_path']),
               '--env-seed', '1', '--particle-seed', '1']
        if objects_dir:
            cmd += ['--objects-dir', str(objects_dir)]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (dest / 'native.log').write_text(run.stderr[-16000:])
        if run.returncode:
            raise ValueError(f"{e['name']} render failed ({run.returncode}): {run.stderr[-1000:]}")
        rows = [json.loads(line) for line in run.stdout.splitlines() if line.startswith('{')]
        samples = [r for r in rows if r.get('time_series') == 1]
        entry = {k: e[k] for k in ('name', 'world', 'tile')}
        entry.update(script_sha256=digest(e['script_path']), expected_frames=schedule(p), samples=samples)
        result['maps'].append(entry)
        validate_series(result)
        if entry['expected_frames'] != [r['frame'] for r in samples]:
            raise ValueError('incomplete native capture')
        entry['coverage'] = coverage(samples)
        (dest / 'series.json').write_text(json.dumps(entry, separators=(',', ':')) + '\n')
        print(json.dumps({'map': e['name'], 'samples': len(samples), **entry['coverage']}), flush=True)
    validate_series(result)
    (out / 'series.json').write_text(json.dumps(result, separators=(',', ':')) + '\n')
    return result


def live_error(group, a, b, index):
    if group in ('particles', 'environment') and index in (0, 9 if group == 'particles' else 6):
        return abs(a[index] - b[index]) / max(1, a[index])
    if group in ('objects', 'particles', 'environment') and index > 0:
        if group == 'objects' or index < (9 if group == 'particles' else 6):
            return abs(a[index] / max(1, a[0]) - b[index] / max(1, b[0]))
    if group == 'sky' and index == 3:
        return abs(a[index] - b[index]) / max(1, a[index])
    return abs(a[index] - b[index])


def compare(reference, candidate, mode='native'):
    validate_series(reference)
    validate_series(candidate)
    errors, maps = [], []
    if mode not in ('native', 'live'):
        raise ValueError('unknown comparison mode')
    if candidate['source'] != 'native' or reference['source'] != ('native' if mode == 'native' else 'live'):
        raise ValueError('comparison sources do not match mode')
    for key in ('plan_sha256', 'phase'):
        if not reference.get(key) or reference[key] != candidate.get(key):
            errors.append(f'{key} is missing or unaligned')
    if not candidate.get('draw_every_frame') or (mode == 'native' and not reference.get('draw_every_frame')):
        errors.append('full-draw lifecycle missing')
    if mode == 'live' and (reference.get('mugl_patches') != 'off' or reference.get('phase') != 'aligned'):
        errors.append('live needs mugl patches off and independently established phase alignment')
    left, right = {e['name']: e for e in reference['maps']}, {e['name']: e for e in candidate['maps']}
    if left.keys() != right.keys():
        errors.append('map set differs')
    for name in sorted(left.keys() & right.keys()):
        a, b = left[name], right[name]
        failures = []
        for key in ('world', 'tile', 'script_sha256', 'expected_frames'):
            if key not in a or a[key] != b.get(key):
                failures.append(f'{key} differs or missing')
        cov = coverage(b['samples'])
        if cov['walk_distance'] < 50 or cov['fov_span'] < 1:
            failures.append('path needs >=50 world units of walking and >=1 degree of zoom')
        # WorldTime epochs can differ on live; pair only the recorded relative times, never best-match images.
        epoch_a, epoch_b = a['samples'][0]['world_time'], b['samples'][0]['world_time']
        maxima = {g: 0.0 for g in GROUPS if mode == 'native' or g != 'rng'}
        for x, y in zip(a['samples'], b['samples']):
            if x['frame'] != y['frame'] or abs((x['world_time']-epoch_a)-(y['world_time']-epoch_b)) > (0 if mode == 'native' else 20):
                failures.append(f"frame {y['frame']}: WorldTime/frame alignment")
            if mode == 'native' and (x['world_time'] != y['world_time'] or x['steps'] != y['steps']):
                failures.append(f"frame {y['frame']}: native clock/steps")
            for g in maxima:
                for i, (v, w) in enumerate(zip(x[g], y[g])):
                    error = abs(v-w) if mode == 'native' else live_error(g, x[g], y[g], i)
                    maxima[g] = max(maxima[g], error)
                    if error > (NATIVE_TOLERANCE if mode == 'native' else LIVE_LIMITS[g][i]):
                        failures.append(f"frame {y['frame']}: {g}[{i}]")
            if mode == 'native':
                failures += [f"frame {y['frame']}: {k}" for k in HASHES if x[k] != y[k]]
        maps.append({'name': name, 'world': b['world'], 'samples': len(b['samples']), 'coverage': cov,
                     'max_error': maxima, 'passed': not failures, 'failure_count': len(failures),
                     'failures': failures[:12]})
    return {'version': 1, 'mode': mode, 'passed': not errors and all(m['passed'] for m in maps),
            'errors': errors, 'thresholds': {'native_abs': NATIVE_TOLERANCE, 'native_hashes': 'exact',
                'live_world_time_ms': 20, 'walk_world_units_min': 50, 'fov_degrees_min': 1,
                'live_components': LIVE_LIMITS}, 'maps': maps}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('capture')
    p.add_argument('--plan', type=Path, default=PLAN)
    p.add_argument('--binary', type=Path, default=ROOT / 'native/build/mu-world')
    p.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    p.add_argument('--objects-dir', default=os.environ.get('MU_RENDER_TIME_OBJECTS'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--only', help='comma separated capture names')
    p.add_argument('--backend', choices=['gl', 'soft'], default='gl')
    p = sub.add_parser('compare')
    p.add_argument('reference', type=Path)
    p.add_argument('candidate', type=Path)
    p.add_argument('--mode', choices=['native', 'live'], default='native')
    p.add_argument('--report', type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        if a.command == 'capture':
            if not a.game_root:
                raise ValueError('--game-root or MU_GAME_ROOT required')
            capture(a.plan, a.binary, a.game_root, a.objects_dir, a.out,
                    a.only.split(',') if a.only else None, a.backend)
            return 0
        result = compare(json.loads(a.reference.read_text()), json.loads(a.candidate.read_text()), a.mode)
        a.report.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'passed': result['passed'], 'maps': len(result['maps']), 'errors': result['errors']}))
        return 0 if result['passed'] else 1
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        print(f'render-time: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
