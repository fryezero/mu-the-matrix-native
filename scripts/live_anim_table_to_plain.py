#!/usr/bin/env python3
"""The MapObjectAnimationInfo tables of a langread snapshot as local plaintext (RENDER-WORLDS-AFTER5).

The table object 0x06fbc434 (the Lang table manager 0x06fbaa60 + 0x19d4) is a std::map<int world, loader> filled by
0x0112cb08: for every world 0..0x91 it loads MapObjectAnimationInfo\\MapObjectAnimationInfo<world+1> from
Data\\Lang.mpr into a loader (vtable 0x01aada94, 0x40 bytes) and keeps it when its map is not empty. The loader's
map at +0x38 goes from the key 0x0112bbba(type, action) = 1000 * action + type to the 0x20-byte entry its row
parser 0x0112bc34 builds:

  +0x00 int type      +0x0c int handler (both handler vectors of the action registry 0x01ec7d5c)
  +0x04 int action    +0x10 int param (hero distance of the tick handlers 5 and 7)
  +0x08 float speed   +0x14 std::vector<int> extra (the remaining columns)

At world load 0x00ea289c copies the current world's map into the registry (+0x10). The snapshot needs langread
`graph:0x06fbc434=0x48,4,0`.

mapanim.tsv: one row per entry, worlds ascending, then by key:
  world, type, action, speed, handler, param, extra (comma-separated, '-' when empty)
The speed is printed with repr (exact binary32 round trip). The file is decoded game data: local only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_lang_to_plain import Snapshot, SnapshotError  # noqa: E402

TABLE = 0x06fbc434
LOADER_MAP = 0x38           # loader +0x38 (0x0112bc0f, 0x0112bde5)
ENTRY = 0x20


def key(kind, action):
    return (1000 * action + kind) & 0xffffffff


def entry(snap, node, world):
    raw = snap.read(node + 0x14, ENTRY)
    kind, action = struct.unpack_from('<ii', raw, 0)
    speed = struct.unpack_from('<f', raw, 8)[0]
    handler, param = struct.unpack_from('<ii', raw, 0xc)
    begin, end, _ = struct.unpack_from('<III', raw, 0x14)
    if end < begin or (end - begin) % 4:
        raise SnapshotError(f'world {world}: bad extra vector at {node + 0x28:#x}')
    extra = list(struct.unpack(f'<{(end - begin) // 4}i', snap.read(begin, end - begin))) if end > begin else []
    if key(kind, action) != snap.u32(node + 0x10):
        raise SnapshotError(f'world {world}: node key {snap.u32(node + 0x10)} is not 1000 * {action} + {kind}')
    return {'type': kind, 'action': action, 'speed': speed, 'handler': handler, 'param': param, 'extra': extra}


def read_table(snap):
    """[(world, [entry, ...])] in map order."""
    rows = []
    for world, node in snap.tree(TABLE):
        rows.append((world, [entry(snap, n, world) for _, n in snap.tree(node + 0x14 + LOADER_MAP)]))
    return rows


def table_lines(rows):
    out = ['# RENDER-WORLDS-AFTER5 MapObjectAnimationInfo 0x06fbc434 (0x0112cb08, rows 0x0112bc34); '
           'local decoded game data',
           '#world\ttype\taction\tspeed\thandler\tparam\textra']
    for world, entries in rows:
        for e in entries:
            out.append('\t'.join([str(world), str(e['type']), str(e['action']), repr(float(e['speed'])),
                                  str(e['handler']), str(e['param']), ','.join(map(str, e['extra'])) or '-']))
    return out


def convert(snap, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_table(snap)
    text = '\n'.join(table_lines(rows)) + '\n'
    (out_dir / 'mapanim.tsv').write_text(text, encoding='ascii', newline='\n')
    entries = [e for _, es in rows for e in es]
    return {'worlds': [w for w, _ in rows], 'entries': len(entries),
            'handlers': sorted({e['handler'] for e in entries}),
            'mapanim_sha256': hashlib.sha256(text.encode()).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('snapshot', type=Path, help='langread snapshot with graph:0x06fbc434=0x48,4,0')
    ap.add_argument('out_dir', type=Path, help='local lang directory (MU_LANG_DIR)')
    a = ap.parse_args()
    print(json.dumps(convert(Snapshot.load(a.snapshot), a.out_dir)))


if __name__ == '__main__':
    main()
