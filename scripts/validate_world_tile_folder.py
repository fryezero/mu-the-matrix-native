#!/usr/bin/env python3
"""World tile-bitmap folder (RENDER-WORLDS-O) against pinned instructions.

OpenWorld 0x0182876e passes the map folder (0x018308d6(world), Data\\World<w+1>
outside the event groups) to the tile-bitmap loader 0x01829457, which replaces it
by 0x81 when 0x016a8325(folder - 1) holds. The loader and the predicate execute
as original instructions with the world global set; the bitmap loader 0x0185baac
records its path and the C library sprintf 0x009619dd is a Python stub over the
client's own format strings. The singleton getter 0x00db747f and its
flag 0x0095fba9 (AlphaTileGround03 or TileGround03) are stubs sampling both
answers. 0x018308d6 depends on runtime singletons and is not
executed; folder numbers 0..299 are passed for each sampled world global. Every
recorded path must lie in World<n>, n = mu_terrain_tile_folder(folder), apart
from the literal Object64 lava tile.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import subprocess
import actor_machine as am
import validate_object_render as v
import pins
ROOT = Path(__file__).resolve().parents[1]
TILES, PREDICATE, LOAD, SPRINTF = 0x01829457, 0x016a8325, 0x0185baac, 0x009619dd
BODIES = {'tiles': (0x01829457, 0x01829e21), 'predicate': (0x016a8325, 0x016a8342)}
# World globals that select alternative names inside the loader, plus the Abyss worlds and neighbours.
WORLDS = [0, 0x25, 0x27, 0x33, 0x3f, 0x49, 0x4a, 0x50, 0x51, 0x52, 0x5b, 0x5c, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x8d, 0x91]


def read_string(m, address, limit=260):
    raw = bytes(m.uc.mem_read(address, limit))
    return raw.split(b'\0', 1)[0].decode('latin-1')


def sprintf(m):
    fmt, args, k = read_string(m, m.argument(1)), [], 2
    for spec in re.findall(r'%0?\d*[sd]', fmt):
        value = m.argument(k)
        args.append(read_string(m, value) if spec.endswith('s') else value - (1 << 32) if value & 0x80000000 else value)
        k += 1
    out = (fmt % tuple(args)).encode('latin-1') + b'\0'
    m.uc.mem_write(m.argument(0), out)
    return len(out) - 1


def tiles_of(machine, world, folder):
    paths = []

    def load(m):
        paths.append((m.argument(1), read_string(m, m.argument(0))))
        return 0
    r = v.run(machine, TILES, [folder], v.global_regions(world), {LOAD: load, SPRINTF: sprintf, 0xdb747f: lambda m: v.FAKE,
                                                       0x95fba9: lambda m: folder & 1}, cleanup=0)
    return (paths if r['ok'] else None), v.stopped_reason(r)


def check(paths, expected):
    """All paths in World<expected>, or the literal Object64 lava file; returns the directories seen."""
    dirs = set()
    for _, path in paths:
        m = re.match(r'World(\d+)\\', path)
        if m:
            dirs.add(int(m.group(1)))
        elif path != 'Object64\\song_lava1.jpg':
            dirs.add(path)
    return dirs == {expected}, sorted(dirs, key=str)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/terrain')], check=True)
    lib = C.CDLL(str(ROOT / f'reconstructed/terrain/libterrain.{v.SUFFIX}'))
    lib.mu_terrain_tile_folder.argtypes = [C.c_int32]
    lib.mu_terrain_tile_folder.restype = C.c_int32
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()},
              'families': {}}
    tally = v.Tally('folders')
    remapped, old_rule_mismatches = {}, 0
    for world in WORLDS:
        for folder in range(0, 300):
            paths, stop = tiles_of(machine, world, folder)
            if paths is None:
                tally.add(False, {'world': world, 'folder': folder}, stop)
                continue
            expected = lib.mu_terrain_tile_folder(folder)
            ok, dirs = check(paths, expected)
            old_rule_mismatches += not check(paths, folder)[0]   # the pre-O native rule: its own folder
            tally.count('bitmaps', len(paths))
            if expected != folder:
                remapped[folder] = expected
            tally.add(ok, {'world': world, 'folder': folder, 'c': expected, 'dirs': dirs[:4]})
    report['families']['folders'] = tally.report()
    report['remapped_folders'] = remapped
    report['old_rule_mismatches'] = old_rule_mismatches
    for name, r in report['families'].items():
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    print('remapped folders', remapped, 'old-rule mismatches', report['old_rule_mismatches'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(any(r['equal'] != r['cases'] for r in report['families'].values()) or
               remapped != {130: 129, 131: 129} or not report['old_rule_mismatches'])


if __name__ == '__main__':
    raise SystemExit(main())
