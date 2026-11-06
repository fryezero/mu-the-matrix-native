#!/usr/bin/env python3
"""Build the canonical Native Data export set from the local snapshots (NATIVE-DATA-MANIFEST-001).

App setup imports only manifest-bearing exports (DATA-ACQ-004). This script replays the repository's own
exporters over the local snapshots in one fixed order and writes one set:

    <out>/lang                 live_lang_to_plain (3 snapshots, incl. itemtrs.tsv), live_effect_table_to_plain,
                               mapanim.tsv
    <out>/objects/live/plain   live_objects_to_plain, 47 worlds (31 with the installed EncTerrain<n>.obj)
    <out>/audio/tables         extract_audio_tables over the pinned text/data captures

Every component carries a native-data.manifest that names its inputs by SHA-256; `mu-native-data check`
verifies the set at the end. The default <out> is the app's default scratch folder
(~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export), so app setup and the private app smoke use
it without MU_NATIVE_SCRATCH.

mapanim.tsv (RENDER-WORLDS-AFTER5's MapObjectAnimationInfo rows) comes from a live read of 2026-11-04 whose
snapshot was not kept, so it enters as a pre-converted table: its SHA-256 is pinned below, its rows are
checked against the format native/core/mu_objects_anim.c reads, and the manifest records it as an input with
the step `mapanim-v1-live-read-2026-11-04`. A new read means a new table, pin and date.

itemtrs.tsv (APP-POLISH-004's ItemTRSData, RenderItem3D's inventory render info) is written by
live_lang_to_plain itself and so recorded by the lang export's own manifest. The converter skips a table that a
snapshot lacks without failing, so the set requires it: the file must be present, recorded in the manifest and
hold the pinned number of codes (every lang snapshot holds the same 4,919), or the build fails. Without it the
app silently keeps the itemtrsdata.bmd stand-in.

All outputs are decoded game data: local only, never committed. The destination must not exist; the set is
built next to it and renamed into place when every check passes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_data_manifest as manifest  # noqa: E402
import pins  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
SCRATCH = Path.home() / 'Documents/MTM/mu-mac-tools/native/scratch'
GAME_ROOT = Path.home() / 'Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix'

# Snapshots relative to the scratch root, in the order the APP-REFRESH-001..003 sets were exported.
LANG = ['lang/live/lang4.bin', 'skill2/live/lang5.bin', 'quest2/live/lang5.bin']
EFFECTS = 'render-effects-008/live/s2-lorencia-fxt.bin'
MAPANIM = {'table': 'render-worlds-after5/lang/mapanim.tsv',
           'sha256': 'd7a2cc72e2854f1edb1738df34ab63dae60676887a3fb5d3fe330015a57de814',
           'step': 'mapanim-v1-live-read-2026-11-04', 'rows': 143, 'worlds': 10}
# ItemTRSData rows every lang snapshot holds (lang3/lang4/lang5: the same 4,919 records; APP-REFRESH-006).
ITEMTRS = {'file': 'itemtrs.tsv', 'rows': 4919}
# (snapshot, installed): installed worlds take the record version of Data/World<n>/EncTerrain<n>.obj.
OBJECTS = [(f'objects/live/dumps/{n}.bin', False) for n in ('login', 'fryezen2', 'charsel', 'nighty')] + \
    [(f'fidelity2/live/{n}-obj.bin', False) for n in (
        '08d-tarkan-C', '57-raklion', '51-elbeland', '80-karutan', '10c-icarus', '07-atlans', '37-kanturu',
        '03-noria', '04-losttower', '33-aida', '02b-devias-town', '01-dungeon')] + \
    [(f'data-acq-002/live/{n}-obj.bin', True) for n in (
        '112-ferea', '113-nixies-lake', '116-deep-dungeon-1', '117-deep-dungeon-2', '118-deep-dungeon-3',
        '119-deep-dungeon-4', '120-deep-dungeon-5', '122-swamp-darkness', '123-kubera', '128-abyss-atlans-1',
        '129-abyss-atlans-2', '130-abyss-atlans-3', '131-scorched-canyon', '132-red-smoke-icarus',
        '133-arenil-temple', '134-ashen-aida', '135-old-kethotum', '136-blaze-kethotum',
        '137-kanturu-underground', '138-ignis-volcano', '140-bloody-tarkan', '142-twisted-karutan',
        '143-kardamahal', '144-swamp-destruction', '38-kanturu-remain', '40-battlegrounds', '56-swamp-calmness',
        '6-arena', '63-vulcanus', '79-loren-market', '91-acheron')]

INT = re.compile(r'-?\d+$')
FLOAT = re.compile(r'-?\d+(\.\d+)?(e-?\d+)?$')


def python(script, *args):
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f'{script} failed:\n{result.stdout[-2000:]}{result.stderr[-2000:]}')
    return result.stdout


def mapanim_rows(text):
    """(rows, worlds) of a mapanim.tsv in the layout mu_objects_anim_load reads; SystemExit when malformed."""
    rows, worlds = 0, set()
    for number, line in enumerate(text.split('\n'), 1):
        if not line or line.startswith('#'):
            continue
        col = line.split('\t')
        ok = len(col) == 7 and all(INT.match(c) for c in col[:3] + col[4:6]) and FLOAT.match(col[3]) and \
            (col[6] == '-' or all(INT.match(c) for c in col[6].split(',')))
        if not ok:
            raise SystemExit(f'mapanim.tsv line {number}: not world, type, action, speed, handler, param, extra')
        rows += 1
        worlds.add(int(col[0]))
    return rows, len(worlds)


def itemtrs_rows(text):
    """Codes in an itemtrs.tsv as mu_lang loads it (code + six signed binary32 words); SystemExit when malformed."""
    codes = set()
    for number, line in enumerate(text.split('\n'), 1):
        if not line or line.startswith('#'):
            continue
        col = line.split('\t')
        if len(col) != 7 or not all(INT.match(c) and -2**31 <= int(c) < 2**31 for c in col):
            raise SystemExit(f'itemtrs.tsv line {number}: not code, x, y, rx, ry, rz, scale (signed 32-bit words)')
        if int(col[0]) in codes:
            raise SystemExit(f'itemtrs.tsv line {number}: code {col[0]} repeated')
        codes.add(int(col[0]))
    return len(codes)


def require_itemtrs(lang, pin=ITEMTRS):
    """The lang export must carry ItemTRSData, recorded by its manifest, with the pinned number of codes."""
    path = Path(lang) / pin['file']
    if not path.is_file():
        raise SystemExit(f'{lang}: no {pin["file"]} (a lang snapshot without ItemTRSData 0x06fbb624?)')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if f'file {digest} {path.stat().st_size} {pin["file"]}\n' not in (Path(lang) / 'native-data.manifest').read_text():
        raise SystemExit(f'{path}: not recorded in the export manifest')
    rows = itemtrs_rows(path.read_text(encoding='ascii'))
    if rows != pin['rows']:
        raise SystemExit(f'{path}: {rows} codes, expected {pin["rows"]}')
    return {'itemtrs_rows': rows}


def add_mapanim(lang, table, main_exe, pin=MAPANIM):
    """Add the pinned mapanim.tsv to a published lang export and record it in the export's manifest."""
    table = Path(table)
    data = table.read_bytes()
    if hashlib.sha256(data).hexdigest() != pin['sha256']:
        raise SystemExit(f'{table}: not the pinned MapObjectAnimationInfo table ({pin["step"]}); '
                         'a new live read needs a new pin and date')
    rows, worlds = mapanim_rows(data.decode('ascii'))
    if (rows, worlds) != (pin['rows'], pin['worlds']):
        raise SystemExit(f'{table}: {rows} rows in {worlds} worlds, expected {pin["rows"]} in {pin["worlds"]}')
    manifest.run('check', lang, main_exe)
    if (Path(lang) / 'mapanim.tsv').exists():
        raise SystemExit(f'{lang}: already holds a mapanim.tsv')
    (Path(lang) / 'mapanim.tsv').write_bytes(data)
    manifest.publish_step(main_exe, lang, pin['step'], [table])
    return {'mapanim_rows': rows, 'mapanim_worlds': worlds}


def object_folder(snapshot):
    """The terrain folder the exporter writes by default: the snapshot's world + 1."""
    with open(snapshot, 'rb') as f:
        head = f.read(12)
    if head[:8] != b'MUOBJLV1':
        raise SystemExit(f'{snapshot}: not an object-list snapshot')
    return int.from_bytes(head[8:12], 'little', signed=True) + 1


def build(out, scratch, game_root, text, data):
    main_exe = game_root / 'main.exe'
    manifest.run('pin', main_exe)
    lang, objects, audio = out / 'lang', out / 'objects/live/plain', out / 'audio/tables'
    summary = {}
    for snapshot in LANG:
        python('live_lang_to_plain.py', scratch / snapshot, '--out', lang, '--main-exe', main_exe)
    manifest.run('check', lang, main_exe)
    summary.update(require_itemtrs(lang))
    python('live_effect_table_to_plain.py', scratch / EFFECTS, lang)
    manifest.publish_step(main_exe, lang, 'effects-v1', [scratch / EFFECTS])
    summary.update(add_mapanim(lang, scratch / MAPANIM['table'], main_exe))
    objects.mkdir(parents=True)
    for snapshot, installed in OBJECTS:
        folder = object_folder(scratch / snapshot)
        extra = ['--installed', game_root / f'Data/World{folder}/EncTerrain{folder}.obj'] if installed else []
        python('live_objects_to_plain.py', scratch / snapshot, '--out', objects / f'EncTerrain{folder}.plain',
               '--main-exe', main_exe, *extra)
    audio.mkdir(parents=True)
    report = json.loads(python('extract_audio_tables.py', '--text', text, '--data', data,
                               '--out', out.parent / (out.name + '-audio-report.json'),
                               '--tsv', audio / 'audio-tables.tsv', '--main-exe', main_exe).strip().splitlines()[-1])
    (out.parent / (out.name + '-audio-report.json')).unlink()
    for component in (lang, objects, audio):
        manifest.run('check', component, main_exe)
    summary.update(lang_files=len([p for p in lang.iterdir() if p.name != 'native-data.manifest']),
                   object_worlds=len(list(objects.glob('*.plain'))), audio=report)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', type=Path, default=SCRATCH / 'native-data/export', help='new export root (must not exist)')
    ap.add_argument('--scratch', type=Path, default=SCRATCH, help='scratch root holding the snapshots')
    ap.add_argument('--game-root', type=Path, default=GAME_ROOT, help='installed game (main.exe, Data/World*)')
    ap.add_argument('--text', type=Path, help='restored text capture (default: the pinned evidence path)')
    ap.add_argument('--data', type=Path, help='image data capture (default: the pinned evidence path)')
    a = ap.parse_args(argv)
    out = a.out.resolve()
    if out.exists():
        raise SystemExit(f'{out} exists: choose a new folder (sets are never rebuilt in place)')
    building = out.parent / f'{out.name}.building-{os.getpid()}'
    try:
        summary = build(building, a.scratch, a.game_root, a.text or pins.TEXT.path(), a.data or pins.DATA.path())
        building.rename(out)
    finally:
        if building.exists():
            shutil.rmtree(building)
    print(json.dumps(dict(summary, out=str(out))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
