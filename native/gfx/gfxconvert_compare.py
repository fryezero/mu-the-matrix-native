"""Private, opt-in DATA-ACQ-003 corpus check. Never writes under the game root.
Runs both converters on every installed movie and NaviMap, comparing SHA-256 of
all files and every embedded DefineBitsLossless2 asset. Reports stay in scratch.
Python/Pillow are test dependencies only, never app dependencies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import gfxswf


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(folder):
    files, assets = {}, {}
    for path in sorted(folder.rglob('*')):
        if not path.is_file():
            continue
        name = str(path.relative_to(folder))
        data = path.read_bytes()
        files[name] = digest(data)
        if path.suffix == '.swf':
            m = gfxswf.parse_movie(data)
            for i, t in enumerate(gfxswf.movie_tags(m)):
                if t.code == 36:
                    assets[f'{name}:{i}'] = digest(t.data)
    return files, assets


def compare(a, b):
    return {'count': len(a), 'equal': sum(a[k] == b.get(k) for k in a),
            'missing': sorted(a.keys() - b.keys()), 'extra': sorted(b.keys() - a.keys()),
            'different': sorted(k for k in a.keys() & b.keys() if a[k] != b[k])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--scratch', type=Path, required=True, help='new directory outside the repository')
    ap.add_argument('--binary', type=Path, default=Path(__file__).resolve().parents[1] / 'build/gfxconvert/gfxconvert')
    ap.add_argument('--native-data', type=Path, help='existing Native Data, read-only comparison')
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    scratch = args.scratch.resolve()
    if scratch.is_relative_to(repo) or scratch.is_relative_to(args.root.resolve()):
        ap.error('scratch must be outside the repository and game root')
    scratch.mkdir(parents=True, exist_ok=False)
    summary = {}
    for mode, options in [('default', []), ('app', ['--bridge', '--transparent', '--var', '_root.isClient=true',
                                                  '--fontconfig', 'English', '--font-subset', 'latin'])]:
        for tool, cmd in [('python', [sys.executable, '-B', str(Path(__file__).with_name('gfxconvert.py'))]),
                          ('c', [str(args.binary.resolve())])]:
            with (scratch / f'{mode}-{tool}.log').open('w') as log:
                subprocess.run(cmd + ['--root', str(args.root), '--out', str(scratch / f'{mode}-{tool}'),
                                      '--report', str(scratch / f'{mode}-{tool}-report.json'), *options],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
        pf, pa = inspect(scratch / f'{mode}-python')
        cf, ca = inspect(scratch / f'{mode}-c')
        summary[mode] = {'files': compare(pf, cf), 'bitmap_assets': compare(pa, ca),
                         'movies': sum(k.endswith('.swf') for k in pf),
                         'navimaps': sum(k.startswith('NaviMap/') for k in pf)}
        (scratch / f'{mode}-sha256.json').write_text(json.dumps({'files': cf, 'bitmap_assets': ca}, indent=2) + '\n')
        if mode == 'app' and args.native_data:
            existing, _ = inspect(args.native_data / 'gfx')
            summary['existing_native_data'] = compare(pf, existing)
    (scratch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return int(any(v[k]['different'] or v[k]['missing'] or v[k]['extra']
                   for mode, v in summary.items() if mode in ('app', 'default')
                   for k in ('files', 'bitmap_assets')))


if __name__ == '__main__':
    raise SystemExit(main())
