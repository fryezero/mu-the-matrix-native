#!/usr/bin/env python3
"""Inspect existing langread snapshots, offline, for the two effect tables.

MuunEffectInfo is the multimap at 0x06fbb46c+0x38. Iterator dereference
0x00aecc71 returns node+0x10; 0x0114203d consumes name +4, position +0x1c,
rotation +0x28, scale +0x34, bone +0x38, follow +0x3c. The map-object effects
are EnchantEffect+0x5c (0x06fbb7b0), not a separate script table. Its world
records contain a nested type map at +0x3c (0x0183067e / 0x010f4ae9).
Decoded TSVs belong in local scratch, never in the repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from live_lang_to_plain import Snapshot, SnapshotError, escape


def inspect(path, output):
    raw = path.read_bytes()
    snap = Snapshot(raw)
    muun = []
    for key, node in snap.tree(0x06fbb46c + 0x38):
        name = escape(snap.string(node + 0x14))
        fields = struct.unpack('<7fiB', snap.read(node + 0x2c, 33))
        muun.append((key, name, *fields))
    worlds = snap.tree(0x06fbb7b0)
    nested, missing = 0, []
    for world, node in worlds:
        try:
            nested += len(snap.tree(node + 0x50))
        except SnapshotError as exc:
            missing.append({'world': world, 'missing': str(exc)})
    output.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(raw).hexdigest()[:12]
    (output/f'muun-{name}.tsv').write_text(
        '# code\tname\tx\ty\tz\trx\try\trz\tscale\tbone\tfollow\n' +
        '\n'.join('\t'.join(map(str, row)) for row in muun) + '\n')
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'muun_records': len(muun),
            'map_object_worlds': len(worlds), 'nested_type_rows_readable': nested,
            'nested_type_maps_missing': missing,
            'evidence': 'static consumer layouts and offline snapshot decode; no runtime effect comparison'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, action='append', required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    results = [inspect(path, args.out_dir) for path in args.snapshot]
    (args.out_dir/'effect-inputs.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps([{k: v for k, v in r.items() if k != 'nested_type_maps_missing'} |
                      {'missing_nested_maps': len(r['nested_type_maps_missing'])} for r in results]))


if __name__ == '__main__':
    main()
