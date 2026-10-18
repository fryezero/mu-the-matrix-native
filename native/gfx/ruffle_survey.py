#!/usr/bin/env python3
"""Run every converted GFx movie through Ruffle (mugfx-shot) and summarise
what works and what Ruffle reports as missing (NATIVE-GFX-001).

    ruffle_survey.py SWF_DIR OUT_DIR [--shot PATH] [--frames N] [--size WxH] [--sheet]

Per movie: load/advance/render time, rendered pixels, ExternalInterface calls
made on its own (no game side attached), Ruffle warnings (including
"Encountered stub" for unimplemented Flash APIs), panics and timeouts.
Writes OUT_DIR/survey.json and, with --sheet, contact sheets.  All outputs
are client-derived renders: keep them local.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SHOT = HERE/'mugfx/target/release/mugfx-shot'


def run_one(shot: Path, swf: Path, png: Path, frames: int, size: str, timeout: float) -> dict:
    env = dict(os.environ, MUGFX_LOG='warn', MUGFX_TRACE='1')
    t = time.time()
    try:
        p = subprocess.run([str(shot), str(swf), str(png), '--frames', str(frames), '--size', size],
                           capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'seconds': timeout}
    out, err = p.stdout.decode(errors='replace'), p.stderr.decode(errors='replace')
    rec: dict = {'status': 'ok' if p.returncode == 0 else f'exit {p.returncode}', 'seconds': round(time.time() - t, 2)}
    for line in out.splitlines():
        if line.startswith('{'):
            try:
                rec.update(json.loads(line))
            except ValueError:
                pass
    calls = collections.Counter(line.split(' ', 2)[1] for line in out.splitlines() if line.startswith('call '))
    rec['calls'] = dict(calls)
    stubs, warns, traces = collections.Counter(), collections.Counter(), 0
    for line in err.splitlines():
        if '[trace]' in line:
            traces += 1
            continue
        m = re.search(r'Encountered stub: (.*)$', line)
        if m:
            stubs[m.group(1).strip()] += 1
        elif ' WARN ' in line or line.startswith('WARN') or 'ERROR' in line or '[avm-warning]' in line:
            msg = re.sub(r'^.*?(WARN|ERROR)\s+', '', line).strip()
            warns[re.sub(r'\d+', 'N', msg)[:160]] += 1
        elif 'panicked' in line:
            warns['panic: ' + line[:160]] += 1
    rec['stubs'] = dict(stubs)
    rec['warnings'] = dict(warns.most_common(20))
    rec['traces'] = traces
    return rec


def contact_sheets(results: dict, out: Path, cols: int = 8, per: int = 48):
    from PIL import Image, ImageDraw
    items = [(n, out/f'{n}.png') for n in sorted(results) if (out/f'{n}.png').exists()]
    w, h = 240, 180
    for s in range(0, len(items), per):
        chunk = items[s:s + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * w, rows * (h + 14)), (40, 40, 40))
        draw = ImageDraw.Draw(sheet)
        for i, (name, path) in enumerate(chunk):
            im = Image.open(path).convert('RGBA')
            bg = Image.new('RGBA', im.size, (110, 110, 110, 255))
            bg.alpha_composite(im)
            bg = bg.convert('RGB')
            bg.thumbnail((w, h))
            x, y = (i % cols) * w, (i // cols) * (h + 14)
            sheet.paste(bg, (x, y))
            draw.text((x + 2, y + h), name[:34], fill=(255, 255, 0))
        sheet.save(out/f'sheet{s // per}.png')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('swf_dir', type=Path)
    ap.add_argument('out_dir', type=Path)
    ap.add_argument('--shot', type=Path, default=DEFAULT_SHOT)
    ap.add_argument('--frames', type=int, default=10)
    ap.add_argument('--size', default='1024x768')
    ap.add_argument('--timeout', type=float, default=60)
    ap.add_argument('--sheet', action='store_true')
    args = ap.parse_args(argv)
    if not args.shot.exists():
        ap.error(f'{args.shot} missing: run native/gfx/build-mugfx.sh')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for swf in sorted(args.swf_dir.glob('*.swf')):
        rec = run_one(args.shot, swf, args.out_dir/f'{swf.stem}.png', args.frames, args.size, args.timeout)
        results[swf.stem] = rec
        print(f'{swf.stem}: {rec["status"]} {rec.get("load_ms", 0):.0f} ms load, '
              f'{rec.get("drawn_pixels", 0)} px, {len(rec.get("calls", {}))} call names, '
              f'{sum(rec.get("stubs", {}).values())} stub hits, {sum(rec.get("warnings", {}).values())} warnings',
              flush=True)
    stubs, warns = collections.Counter(), collections.Counter()
    for rec in results.values():
        for k in rec.get('stubs', {}):
            stubs[k] += 1
        for k in rec.get('warnings', {}):
            warns[k] += 1
    summary = {
        'movies': len(results),
        'status': dict(collections.Counter(r['status'] for r in results.values())),
        'blank': sorted(n for n, r in results.items() if r.get('drawn_pixels', 0) == 0),
        'stubs_by_movies': dict(stubs.most_common()),
        'warnings_by_movies': dict(warns.most_common(40)),
        'load_ms_median': sorted(r.get('load_ms', 0) for r in results.values())[len(results) // 2] if results else 0,
    }
    (args.out_dir/'survey.json').write_text(json.dumps({'summary': summary, 'movies': results}, indent=1,
                                                        ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if args.sheet:
        contact_sheets(results, args.out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
