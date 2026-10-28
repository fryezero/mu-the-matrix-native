#!/usr/bin/env python3
"""Offline NATIVE-PERF-002 stress matrix. Requires local game/Native Data inputs.

Run from any directory; output is private and must live outside the repository.
Window mode measures the actual 25 Hz cap; headless measures uncapped throughput.
Use --baseline after optimization to retain the old draw path on the same binary.
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys

import perf_report

NATIVE = Path(__file__).resolve().parents[1]
SCENARIOS = {
    'crowd40': (0, (182, 128), 40, 1280, 800, 'inventory,character'),
    'crowd80': (0, (182, 128), 80, 1280, 800, 'inventory,character,master,tree4'),
    'tormenta80': (141, (50, 46), 80, 1280, 800, 'inventory,character,master,tree4'),
    'retina80': (141, (50, 46), 80, 3456, 2160, 'inventory,character,master,tree4'),
}


def fixtures(directory, tile, players):
    """Authored demos: every player has five +11 armour pieces, weapon and wings.

    Positions are distinct and within the demo viewport. Moving monsters fight
    the hero, and repeated area skills plus lightning exercise particles/joints.
    """
    x, y = tile
    player_lines = []
    for i in range(players):
        px, py = x - 5 + i % 10, y - 4 + i // 10
        player_lines.append(
            f'player Perf{i:03} class=0x01 at={px},{py} dir={i % 8} pk=3 level=400 '
            'helm=7:9:11 armor=8:9:11 pants=9:9:11 gloves=10:9:11 boots=11:9:11 '
            'weapon0=0:10:11:1 wing=12:0:11')
    actors = []
    for i in range(32):
        px, py = x - 4 + i % 8, y - 2 + i // 8
        actors.append(f'actor {i % 4} {px} {py} {i % 8} wander 2 label mob{i:02}')
    player_path, actor_path = directory / 'players.txt', directory / 'actors.txt'
    player_path.write_text('\n'.join(player_lines) + '\n')
    actor_path.write_text('\n'.join(actors) + '\n')
    return player_path, actor_path


def command(args, name, directory):
    world, tile, players, width, height, windows = SCENARIOS[name]
    pf, af = fixtures(directory, tile, players)
    casts = ' '.join(f'{f}:skill:{(9, 10, 14, 24, 26)[i % 5]}:mob{(i % 32):02}'
                     for i, f in enumerate(range(30, min(args.frames if args.headless else int(args.seconds * 25),
                                                         30 + 32 * 20), 20)))
    cmd = [str(args.binary), '--game-root', str(args.game_root), '--objects-dir', str(args.data / 'objects'),
           '--world', str(world), '--tile', ','.join(map(str, tile)), '--class', '0',
           '--players', str(pf), '--player-range', '40', '--placement', str(af),
           '--width', str(width), '--height', str(height), '--combat', '--combat-weapon', 'staff',
           '--combat-seed', '1', '--hero-hp', '1000000', '--combat-script', casts,
           '--items', '--joint-demo', '0', '--perf-fov', '65',
           '--gfx', str(args.data / 'gfx'), '--gfx-open', windows,
           '--travel-script', '60:tab', '--no-audio', '--perf', str(directory / 'frames.tsv')]
    if args.headless:
        cmd += ['--headless', '--backend', 'gl', '--frames', str(args.frames)]
    else:
        cmd += ['--seconds', str(args.seconds)]
    if args.renders:
        cmd += ['--out-dir', str(directory / 'renders'), '--every', '60']
    return cmd


def check(result, *, headless):
    """Apple M5 envelope. Never call uncapped throughput measured capped fps."""
    failures = []
    metrics = [result.get('fps'), result.get('frames')]
    metrics += [result.get(group, {}).get(key) for group in ('work_ms', 'frame_ms') for key in ('p95', 'p99')]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in metrics):
        return ['missing, negative or nonfinite timing metric']
    if result['frames'] < 100:
        failures.append('fewer than 100 measured frames')
    if not headless and not 24.8 <= result['fps'] <= 25.2:
        failures.append('capped fps outside 24.8..25.2')
    if result['work_ms']['p95'] > 38 or result['work_ms']['p99'] > 40:
        failures.append('work p95 > 38 ms or p99 > 40 ms')
    if not headless and (result['frame_ms']['p95'] > 41 or result['frame_ms']['p99'] > 42):
        failures.append('frame pacing p95 > 41 ms or p99 > 42 ms')
    if headless and result['fps'] < 25:
        failures.append('uncapped throughput below 25 fps')
    return failures


def measurement_complete(result, *, headless, frames, seconds):
    if headless:
        return result['frames'] == frames
    elapsed = result['frames'] * result['frame_ms']['mean'] / 1000.0
    return math.isfinite(elapsed) and elapsed >= seconds * 0.95


def regression(result, limits):
    failures = []
    metrics = [result.get('fps'), result.get('frames'),
               result.get('phases', {}).get('cpu', {}).get('mean')]
    metrics += [result.get('work_ms', {}).get(key) for key in ('p95', 'p99')]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in metrics):
        return ['missing, negative or nonfinite timing metric']
    if result['frames'] < 100:
        failures.append('fewer than 100 measured frames')
    if result['fps'] < limits['min_fps']:
        failures.append('fps below measured M5 regression floor')
    for percentile in ('p95', 'p99'):
        if result['work_ms'][percentile] > limits[f'work_{percentile}_ms']:
            failures.append(f'work {percentile} exceeds M5 regression ceiling')
    if result['phases'].get('cpu', {}).get('mean', float('inf')) > limits['cpu_mean_ms']:
        failures.append('thread CPU exceeds M5 regression ceiling')
    return failures


def workload(rows, expected):
    """Refuse a fast run that silently omitted any requested workload."""
    players = next((r['players'] for r in rows if isinstance(r.get('players'), dict)), {})
    models = [r for r in rows if 'player' in r and 'loaded' in r]
    required = (1, 2, 3, 4, 5, 6, 8)
    if len(models) != expected or any(
            len(r.get('loaded', [])) != 9 or len(r.get('textures_missing', [])) != 9 or
            any(not r['loaded'][i] or r['textures_missing'][i] != 0 for i in required) for r in models):
        raise ValueError('player equipment model or texture missing')
    actors = next((r for r in rows if r.get('actors') == 32), {})
    combat = next((r for r in rows if r.get('combat') is True), {})
    particles = next((r for r in rows if r.get('particles') is True), {})
    gfx = next((r['gfx'] for r in rows if isinstance(r.get('gfx'), dict)), {})
    map_state = next((r for r in rows if r.get('map') is True), {})
    if players.get('count') != expected or players.get('viewport_packets', 0) < expected or players.get('addinfo', 0) < expected:
        raise ValueError('crowd truncated or outside the viewport')
    if not actors or not all(combat.get(k, 0) > 0 for k in
                             ('skills', 'area_requests', 'fx_created', 'joints_created')):
        raise ValueError('monsters/combat/effects missing')
    if particles.get('created', 0) <= 0 or particles.get('dropped', 0) or particles.get('overflow', 0):
        raise ValueError('particle workload missing or overflowing')
    if (not gfx.get('renders') or not gfx.get('inventory_open') or not gfx.get('item_models')
            or not gfx.get('base_mode') or gfx.get('item_models_missing', 0)):
        raise ValueError('GFx or inventory item models missing')
    if not map_state.get('map_shown'):
        raise ValueError('map window missing')
    return {'players': players, 'actors': actors, 'combat': combat, 'gfx': gfx, 'map': map_state, 'particles': particles, 'player_models': len(models)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game-root', type=Path, required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--gfx-lib', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--binary', type=Path, default=NATIVE / 'build/mu-world')
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--frames', type=int, default=300)
    ap.add_argument('--seconds', type=float, default=60)
    ap.add_argument('--renders', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--perf-003-baseline', action='store_true', help='disable only PERF-003 optimizations')
    ap.add_argument('--gpu-timing', action='store_true', help='require the full Metal timing extension')
    ap.add_argument('--check', action='store_true', help='require the 25 Hz target')
    ap.add_argument('--check-regression', action='store_true', help='check the measured M5 envelope')
    ap.add_argument('--scenario', choices=SCENARIOS, action='append')
    a = ap.parse_args(argv)
    if 'MU_GFX_TEST_CLOCK' in os.environ:
        ap.error('MU_GFX_TEST_CLOCK is only for deterministic render comparisons')
    if a.gpu_timing and a.headless:
        ap.error('--gpu-timing requires the window shared-surface path')
    if a.frames <= 50 or a.seconds <= 0:
        ap.error('use more than 50 frames and a positive duration')
    for key in ('MU_GFX_NO_ITEM_MODELS', 'MU_GFX_NO_ICON_MODELS', 'MU_GFX_NO_SKILLS',
                'MU_GFX_PLAIN_ITEMS'):
        # The renderer uses getenv presence, including an empty value.
        if key in os.environ:
            ap.error(f'{key} would omit part of the stress workload')
    a.out = a.out.resolve()
    if NATIVE.parent == a.out or NATIVE.parent in a.out.parents:
        ap.error('--out must be outside the source repository')
    env = dict(os.environ, MU_LANG_DIR=str(a.data / 'lang'), MU_GFX_LIB=str(a.gfx_lib))
    env.update(MU_PERF_BASELINE='0', MU_NO_GL_BATCH='0')
    env['MU_PERF_002_BASELINE'] = '1' if a.baseline else '0'
    env['MU_PERF_003_BASELINE'] = '1' if a.perf_003_baseline else '0'
    if a.gpu_timing:
        lib = ctypes.CDLL(str(a.gfx_lib))
        for symbol in ('mugfx_perf_frame', 'mugfx_perf_end'):
            if not hasattr(lib, symbol):
                ap.error(f'--gpu-timing requires {symbol}; rebuild libmugfx')
    report = {'machine': platform.platform(), 'mode': 'headless-uncapped' if a.headless else 'window-capped',
              'load_start': os.getloadavg(),
              'binary_sha256': hashlib.sha256(a.binary.read_bytes()).hexdigest(),
              'gfx_sha256': hashlib.sha256(a.gfx_lib.read_bytes()).hexdigest(),
              'perf_003_baseline': a.perf_003_baseline, 'gpu_timing': a.gpu_timing,
              'gfx_double_buffer': 'MU_GFX_SINGLE_BUFFER' not in env,
              'region_reference': env.get('MU_PERF_REGION_REFERENCE') == '1', 'scenarios': {}}
    failed = False
    limits = json.loads((NATIVE / 'tools/stress_m5_limits.json').read_text())['scenarios']
    for name in a.scenario or SCENARIOS:
        directory = a.out / name
        directory.mkdir(parents=True, exist_ok=False)
        metal = directory / 'metal.jsonl' if a.gpu_timing else None
        env.pop('MU_GFX_GPU_LOG', None)
        if metal:
            env['MU_GFX_GPU_LOG'] = str(metal)
        cmd = command(a, name, directory)
        (directory / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
        with (directory / 'stdout.jsonl').open('w') as out, (directory / 'stderr.log').open('w') as err:
            process = subprocess.Popen(cmd, stdout=out, stderr=err, env=env)
            (directory / 'pid').write_text(str(process.pid) + '\n')
            code = process.wait()
        stderr = (directory / 'stderr.log').read_text()
        if code or 'continuing without' in stderr or 'libmugfx' in stderr or 'too many' in stderr:
            raise RuntimeError(f'{name}: incomplete workload, exit {code}; inspect {directory}')
        all_frames = perf_report.summarize(str(directory / 'frames.tsv'), scene=6)
        if not measurement_complete(all_frames, headless=a.headless, frames=a.frames, seconds=a.seconds):
            raise RuntimeError(f'{name}: benchmark stopped before the requested measurement completed')
        result = perf_report.summarize(str(directory / 'frames.tsv'), scene=6, skip_first=50, metal_log=metal)
        if metal and (not result['metal']['supported'] or result['metal']['missing_frames']):
            raise RuntimeError(f'{name}: incomplete Metal timing: {result["metal"]}')
        rows = [json.loads(line) for line in (directory / 'stdout.jsonl').read_text().splitlines()
                if line.startswith('{')]
        result['workload'] = workload(rows, SCENARIOS[name][2])
        if metal and result['workload']['gfx'].get('shared') != 1:
            raise RuntimeError(f'{name}: Metal timing requires shared-surface rendering')
        result['failures'] = check(result, headless=a.headless)
        report['scenarios'][name] = result
        result['regression_failures'] = regression(result, limits[name])
        failed |= bool(a.check and result['failures']) or bool(a.check_regression and result['regression_failures'])
        (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f"{name}: {result['fps']:.2f} fps, work p95 {result['work_ms']['p95']:.2f} ms; "
              f"{result['failures'] or 'PASS'}", flush=True)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
