#!/usr/bin/env python3
"""Bounded installed-item scene census for EFFECTS-026. Output stays local.

A diagnostic baseline may print REFUSED bitmap/subtype to stderr. Those requests
are counted separately from pre-draw adapter refusals. Normal binaries still
report aggregate unsupported counts. Every draw runs; only first/last PNGs save.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

import validate_render_effects25 as previous

ROOT = Path(__file__).resolve().parents[1]


def programs():
    header = (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text()
    return sorted({int(t, 0) for name in ('mu_rc_fx_types', 'mu_rc_fx_pre_types')
                   for t in re.findall(r'^    \{([^,]+),', header.split(name+'[] = {')[1].split('};')[0], re.M)})


def player(t, n):
    group, index = divmod(t - 0xae6, 512)
    # A weapon slot explicitly carries the authored model, including later wing
    # and accessory models. This is a renderer fixture, not equipment eligibility.
    return (f'player Demo{n} class=0x01 at={126+n%4},{123+n//4} dir=3 pk=3 '
            f'level=400 weapon0={group}:{index}:9\n')


def capture(binary, game, output, later=False, frames=16, clock=0):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    ts = programs()
    if later:
        ts = sorted(set(ts) - previous.CENSUS_PROGRAMS)
    batches = [[t] for t in ts]
    models = json.loads(subprocess.run([str(ROOT/'native/build/mu-data'), 'item-models',
                       str(Path(game)/'Data/Local/Item.bmd'), '--json'],
                       check=True, capture_output=True, text=True).stdout)
    models = {r['model_index']: r for r in models['items']}
    results = []
    start = time.monotonic()
    for n, types in enumerate(batches):
        dest = output/f'batch{n:02}'
        if (dest/'summary.json').exists():
            results.append(json.loads((dest/'summary.json').read_text()))
            continue
        dest.mkdir(exist_ok=True)
        fixture = dest/'players.txt'
        fixture.write_text(''.join(player(t,i) for i,t in enumerate(types)))
        t = types[0]
        record = models[t]
        asset = (record['folder']+record['file']).replace('\\','/')
        group,index = divmod(t-0xae6,512)
        slot = {7:'helm',8:'armor',9:'pants',10:'gloves',11:'boots',12:'wing'}.get(group,'weapon0')
        if not (Path(game)/asset).is_file():
            result = dict(types=[hex(t)], unavailable='authored model path is absent')
            (dest/'summary.json').write_text(json.dumps(result))
            results.append(result)
            print(json.dumps(result),flush=True)
            continue
        command = [str(Path(binary).resolve()), '--game-root', str(game), '--headless', '--backend', 'soft',
                   '--no-audio', '--width','640','--height','480','--every',str(frames-1),
                   '--out-dir',str(dest),'--hero-name','DemoKnight','--tile','128,124',
                   '--frames',str(frames),'--time-series-every',str(frames),'--quiet','--no-players',
                   '--hero-item',f'{slot}={Path(game)/asset}@{group}:{index}:9',
                   '--no-names','--no-helpers','--no-map','--no-items']
        if clock: command += ['--time-series-start-ms',str(clock)]
        run = subprocess.run(command, capture_output=True, text=True)
        if run.returncode: raise RuntimeError(str(run.returncode)+run.stderr[-2500:]+run.stdout[-2500:])
        rows = [json.loads(s) for s in run.stdout.splitlines() if s.startswith('{')]
        (dest/'report.json').write_text(json.dumps(rows,indent=2))
        pre = next((r['hero'] for r in rows if r.get('item_pre_draw')),
                   dict(pre_effects=0, pre_refused=0, hidden=0))
        pt = next(r for r in rows if r.get('particles') is True)
        refused = Counter(re.findall(r'REFUSED ([0-9a-f]+/\d+)',run.stderr))
        results.append(dict(types=[hex(t) for t in types], pre=pre, particles=pt, refused_pairs=dict(refused)))
        (dest/'summary.json').write_text(json.dumps(results[-1]))
        print(json.dumps(results[-1]),flush=True)
    result = dict(binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(), frames=frames,
                  clock=clock, programs=len(ts), batches=results, seconds=time.monotonic()-start)
    (output/'census.json').write_text(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',required=True);p.add_argument('--game-root',required=True)
    p.add_argument('--out',required=True);p.add_argument('--later',action='store_true')
    p.add_argument('--frames',type=int,default=16);p.add_argument('--clock',type=int,default=0)
    a=p.parse_args();capture(a.binary,a.game_root,a.out,a.later,a.frames,a.clock)
