#!/usr/bin/env python3
"""README-STRESS-001 offline presentation captures, not performance measurements.

Requires locally built mu-world/libmugfx and existing object/movie/language
exports. Writes private PNGs, authored fixtures and exact commands outside the
repository. Review images before copying JPEGs into docs/images and pinning them.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[2]
# class, armour index, weapon group:index, wings, name prefix, upgrade level
KITS = [(0, 10, '5:5', 1, 'W', 3), (1, 9, '0:10', 0, 'K', 7),
        (2, 3, '4:9', 3, 'E', 5), (3, 4, '0:12', 2, 'M', 0),
        (4, 4, '2:8', 4, 'L', 7), (1, 6, '1:8', 0, 'A', 3),
        (0, 0, '5:0', 1, 'S', 0), (2, 3, '4:8', 3, 'F', 3)]


def fixtures(directory, tile):
    x, y = tile
    players = []
    for i in range(80):
        cls, armour, weapon, wing, prefix, level = KITS[i % len(KITS)]
        col, row = i % 10, i // 10
        # Diagonal world rows project into a readable screen rectangle.
        px, py = x + col + row - 8, y + col - row - 1
        parts = ' '.join(f'{slot}={group}:{armour}:{level}' for group, slot in
                         enumerate(('helm', 'armor', 'pants', 'gloves', 'boots'), 7))
        wings = f' wing=12:{wing}:0' if i % 3 else ''
        players.append(f'player {prefix}{i+1:02} class={cls} at={px},{py} dir={i%8} '
                       f'pk=0 level=400 {parts} weapon0={weapon}:{level}{wings}')
    actors = [f'actor {i%4} {x-2+i%4} {y+2+i//4} {i%8} wander 2 label mob{i:02}' for i in range(8)]
    pf, af = directory/'players.txt', directory/'actors.txt'
    pf.write_text('\n'.join(players)+'\n')
    af.write_text('\n'.join(actors)+'\n')
    return pf, af


def verify(rows):
    players = next(r['players'] for r in rows if isinstance(r.get('players'), dict))
    models = [r for r in rows if 'player' in r and 'loaded' in r]
    if players['count'] != 80 or players['addinfo'] != 80 or len(models) != 80:
        raise ValueError('incomplete crowd')
    for r in models:
        for i in (1, 2, 3, 4, 5, 6, 8):
            if i == 8 and not r['loaded'][i]:  # authored wingless characters
                continue
            if not r['loaded'][i] or r['textures_missing'][i] or r['effect_textures_loaded'][i] != 6:
                raise ValueError(f'incomplete base/glow textures: {r["name"]}, slot {i}')
    gfx = next(r['gfx'] for r in rows if isinstance(r.get('gfx'), dict))
    combat = next(r for r in rows if r.get('combat') is True)
    if not gfx['renders'] or not all(combat[k] for k in ('skills', 'fx_created', 'joints_created')):
        raise ValueError('interface or skill effects absent')
    return {'players': 80, 'base_and_glow_textures': 'complete',
            'skills': combat['skills'], 'fx_created': combat['fx_created'],
            'joints_created': combat['joints_created'], 'gfx_renders': gfx['renders']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('game-root', 'objects', 'gfx', 'lang', 'out'):
        ap.add_argument('--'+name, type=Path, required=True)
    a = ap.parse_args()
    a.out = a.out.resolve()
    if a.out == REPO or REPO in a.out.parents:
        ap.error('--out must be outside the repository')
    a.out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MU_LANG_DIR=str(a.lang.resolve()),
               MU_GFX_LIB=str(REPO/'native/gfx/mugfx/target/release/libmugfx.dylib'),
               MU_GFX_SINGLE_BUFFER='1', MU_GFX_TEST_CLOCK='1', MU_GFX_PUBLIC_DEMO='1')
    env.pop('MU_GFX_GPU_LOG', None)
    records = []
    for name, world, tile, selected in [('lorencia', 0, (182, 128), 0), ('tormenta', 141, (60, 50), 100)]:
        directory = a.out/name
        directory.mkdir(exist_ok=False)
        pf, af = fixtures(directory, tile)
        cmd = [str(REPO/'native/build/mu-world'), '--game-root', str(a.game_root.resolve()),
               '--objects-dir', str(a.objects.resolve()), '--world', str(world),
               '--tile', ','.join(map(str, tile)), '--class', '0', '--hero-name', 'Preview',
               '--players', str(pf), '--player-range', '40', '--placement', str(af),
               '--width', '1600', '--height', '1000', '--no-audio', '--headless', '--backend', 'gl',
               '--frames', '101', '--every', '100', '--out-dir', str(directory), '--perf-fov', '65',
               '--gfx', str(a.gfx.resolve()), '--gfx-open', '', '--combat', '--combat-weapon', 'staff',
               '--combat-seed', '1', '--hero-hp', '1000000', '--combat-script',
               '30:skill:9:mob00 50:skill:10:mob01 70:skill:14:mob02 90:skill:24:mob03',
               '--items', '--joint-demo', '0']
        with (directory/'stdout.jsonl').open('w') as out, (directory/'stderr.log').open('w') as err:
            subprocess.run(cmd, cwd=REPO, env=env, stdout=out, stderr=err, check=True)
        stderr = (directory/'stderr.log').read_text()
        if 'continuing without' in stderr or 'drawing none' in stderr:
            raise ValueError('required scenery/interface absent')
        rows = [json.loads(line) for line in (directory/'stdout.jsonl').read_text().splitlines()
                if line.startswith('{')]
        summary = verify(rows)
        png = directory/f'frame-{selected:04}.png'
        records.append(dict(scene=name, frame=selected, command=cmd, summary=summary,
                            environment={k: env[k] for k in ('MU_LANG_DIR', 'MU_GFX_LIB', 'MU_GFX_SINGLE_BUFFER',
                                                            'MU_GFX_TEST_CLOCK', 'MU_GFX_PUBLIC_DEMO')},
                            sha256=hashlib.sha256(png.read_bytes()).hexdigest()))
        print(name, summary, flush=True)
    (a.out/'commands.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
