#!/usr/bin/env python3
"""Full-quality PERF-004 frame equality, without writing bulk frame images.

Uses the stress workloads, fixed AS2 time and synchronous presentation. Timing
runs must use bench_stress instead. Reports hashes and rejects missing frames.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import bench_stress as bench


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game-root', type=Path, required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--gfx-lib', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--binary', type=Path, default=bench.NATIVE / 'build/mu-world')
    ap.add_argument('--frames', type=int, default=151)
    ap.add_argument('--scenario', choices=bench.SCENARIOS, action='append')
    a = ap.parse_args()
    if a.frames < 81:
        ap.error('use at least 81 frames to exercise map and combat')
    for key in ('MU_GFX_NO_ITEM_MODELS', 'MU_GFX_NO_ICON_MODELS', 'MU_GFX_NO_SKILLS', 'MU_GFX_PLAIN_ITEMS'):
        if key in os.environ:
            ap.error(f'{key} would omit part of the comparison workload')
    a.out = a.out.resolve()
    if bench.NATIVE.parent == a.out or bench.NATIVE.parent in a.out.parents:
        ap.error('--out must be outside the repository')
    a.headless, a.renders, a.seconds = True, False, 0
    a.out.mkdir(parents=True, exist_ok=False)
    report = {'pose_tasks_requested': 4, 'binary_sha256': hashlib.sha256(a.binary.read_bytes()).hexdigest(),
              'gfx_sha256': hashlib.sha256(a.gfx_lib.read_bytes()).hexdigest(), 'scenarios': {}}
    env = dict(os.environ, MU_LANG_DIR=str(a.data / 'lang'), MU_GFX_LIB=str(a.gfx_lib),
               MU_GFX_TEST_CLOCK='1', MU_GFX_SINGLE_BUFFER='1', MU_PERF_HASH_ONLY='1',
               MU_PERF_004_VBO_BASELINE='0', MU_PERF_004_POSE_TASKS='4', MU_PERF_BASELINE='0', MU_PERF_002_BASELINE='0', MU_PERF_003_BASELINE='0', MU_NO_GL_BATCH='0')
    for name in a.scenario or bench.SCENARIOS:
        results = []
        for mode in ('1', '0'):
            d = a.out / f'{name}-{mode}'
            d.mkdir()
            cmd = bench.command(a, name, d) + ['--out-dir', str(d / 'hashes'), '--every', '1']
            env['MU_PERF_004_BASELINE'] = mode
            (d / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
            with (d / 'stdout.jsonl').open('w') as out, (d / 'stderr.log').open('w') as err:
                subprocess.run(cmd, env=env, stdout=out, stderr=err, check=True)
            rows = [json.loads(s) for s in (d / 'stdout.jsonl').read_text().splitlines() if s.startswith('{')]
            frames = [r for r in rows if 'frame' in r and 'sha256' in r]
            if [r['frame'] for r in frames] != list(range(a.frames)):
                raise ValueError(f'{name}: missing, duplicate or out-of-order frames')
            hashes = [r['sha256'] for r in frames]
            if len(hashes) != a.frames or any(len(h) != 64 for h in hashes):
                raise ValueError(f'{name}: missing full-frame hashes')
            bench.workload(rows, bench.SCENARIOS[name][2])
            uploads = next((r for r in rows if 'vbo_uploads' in r), None)
            if uploads is None or uploads.get('vbo_failures') != 0 or bool(uploads['vbo_uploads']) != (mode == '0'):
                raise ValueError(f'{name}: streaming path not complete')
            if list((d / 'hashes').glob('*.png')):
                raise ValueError('hash-only comparison wrote bulk images')
            results.append(hashes)
        differing = [i for i, (x, y) in enumerate(zip(*results)) if x != y]
        report['scenarios'][name] = {'frames': a.frames, 'differing': differing,
                                    'hashes': results[0], 'optimized_hashes': results[1]}
        (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f'{name}: {a.frames - len(differing)}/{a.frames} identical', flush=True)
        if differing:
            raise ValueError(f'{name}: differing frames {differing}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
