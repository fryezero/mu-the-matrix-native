#!/usr/bin/env python3
"""The map-object effect table of a langread snapshot as local plaintext (RENDER-EFFECTS-008).

EnchantEffect's +0x5c map at 0x06fbb7b0 (read by 0x0183067e only): std::map<int world, record>; the record's
+0x3c is a std::map<int type, std::vector<entry>> (0x010f4ae9), keyed by the object's int32 at +0x5c. Entry,
0x54 bytes (0x01849998):

  +0x04 std::string  .ein path          +0x34 float  scale
  +0x1c float[3]     position           +0x38 int    bone
  +0x28 float[3]     rotation           +0x3c byte   follow bone
  +0x3d byte         owner tint         +0x44 float  start frame
  +0x48 std::vector<int> actions

0x0183067e hands them to the factory 0x00a797a0 (template transform off) and attaches the effect with
0x0129f9c6(effect, bone, follow, 0, 0.0). The snapshot needs langread `graph:0x06fbb7b0=8,6,0`.

mapeffects.tsv: one row per entry, in map and vector order:
  world, type, index, path, x, y, z, rx, ry, rz, scale, bone, follow, tint, start (binary32 bits, hex), actions
Floats are printed with repr (exact binary32 round trip). The file is decoded game data: local only.

muuneffects.tsv (when the snapshot holds MuunEffectInfo, the multimap 0x06fbb46c+0x38 read by 0x0114203d):
  code, path, x, y, z, rx, ry, rz, scale, bone, follow
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_lang_to_plain import Snapshot, SnapshotError, escape  # noqa: E402

TABLE = 0x06fbb7b0
WORLD_TYPES = 0x3c          # record +0x3c (0x010f4ae9)
ENTRY = 0x54                # 0x01849998 / 0x01849a75
MUUN = 0x06fbb46c + 0x38


def f32(raw, offset):
    return struct.unpack_from('<f', raw, offset)[0]


def entry(snap, address):
    raw = snap.read(address, ENTRY)
    begin, end, _ = struct.unpack_from('<III', raw, 0x48)
    if end < begin or (end - begin) % 4:
        raise SnapshotError(f'bad action vector at {address + 0x48:#x}')
    actions = struct.unpack(f'<{(end - begin) // 4}i', snap.read(begin, end - begin)) if end > begin else ()
    return {'path': snap.string(address + 4),
            'position': [f32(raw, 0x1c + 4 * k) for k in range(3)],
            'rotation': [f32(raw, 0x28 + 4 * k) for k in range(3)],
            'scale': f32(raw, 0x34), 'bone': struct.unpack_from('<i', raw, 0x38)[0],
            'follow': raw[0x3c], 'tint': raw[0x3d], 'start': struct.unpack_from('<I', raw, 0x44)[0],
            'actions': list(actions)}


def read_table(snap):
    """[(world, type, [entry, ...])] in map order."""
    rows = []
    for world, node in snap.tree(TABLE):
        for kind, inner in snap.tree(node + 0x14 + WORLD_TYPES):
            begin, end, _ = struct.unpack('<III', snap.read(inner + 0x14, 12))
            if end < begin or (end - begin) % ENTRY:
                raise SnapshotError(f'world {world} type {kind}: vector of {end - begin} bytes')
            rows.append((world, kind, [entry(snap, a) for a in range(begin, end, ENTRY)]))
    return rows


def read_muun(snap):
    """MuunEffectInfo rows (code, name +4, position +0x1c, rotation +0x28, scale +0x34, bone +0x38, follow +0x3c
    of the value at node+0x10, 0x00aecc71), or None when the snapshot lacks it."""
    try:
        nodes = snap.tree(MUUN)
    except SnapshotError:
        return None
    rows = []
    for code, node in nodes:
        raw = snap.read(node + 0x10, 0x40)
        rows.append({'code': code, 'path': snap.string(node + 0x14),
                     'position': [f32(raw, 0x1c + 4 * k) for k in range(3)],
                     'rotation': [f32(raw, 0x28 + 4 * k) for k in range(3)],
                     'scale': f32(raw, 0x34), 'bone': struct.unpack_from('<i', raw, 0x38)[0], 'follow': raw[0x3c]})
    return rows


def number(value):
    return repr(float(value))


def table_lines(rows):
    out = ['# RENDER-EFFECTS-008 map-object effect table 0x06fbb7b0 (0x0183067e); local decoded game data',
           '#world\ttype\tindex\tpath\tx\ty\tz\trx\try\trz\tscale\tbone\tfollow\ttint\tstart\tactions']
    for world, kind, entries in rows:
        for k, e in enumerate(entries):
            out.append('\t'.join([str(world), str(kind), str(k), escape(e['path']),
                                  *map(number, e['position'] + e['rotation'] + [e['scale']]),
                                  str(e['bone']), str(e['follow']), str(e['tint']), f"{e['start']:08x}",
                                  ','.join(map(str, e['actions'])) or '-']))
    return out


def muun_lines(rows):
    out = ['# RENDER-EFFECTS-008 MuunEffectInfo 0x06fbb46c+0x38 (0x0114203d); local decoded game data',
           '#code\tpath\tx\ty\tz\trx\try\trz\tscale\tbone\tfollow']
    for r in rows:
        out.append('\t'.join([str(r['code']), escape(r['path']),
                              *map(number, r['position'] + r['rotation'] + [r['scale']]),
                              str(r['bone']), str(r['follow'])]))
    return out


def convert(snap, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_table(snap)
    text = '\n'.join(table_lines(rows)) + '\n'
    (out_dir/'mapeffects.tsv').write_text(text, encoding='ascii', newline='\n')
    summary = {'worlds': len({w for w, _, _ in rows}), 'types': len(rows),
               'entries': sum(len(e) for _, _, e in rows),
               'mapeffects_sha256': hashlib.sha256(text.encode()).hexdigest()}
    muun = read_muun(snap)
    if muun is not None:
        text = '\n'.join(muun_lines(muun)) + '\n'
        (out_dir/'muuneffects.tsv').write_text(text, encoding='ascii', newline='\n')
        summary.update(muun_records=len(muun), muuneffects_sha256=hashlib.sha256(text.encode()).hexdigest())
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('snapshot', type=Path, help='langread snapshot with graph:0x06fbb7b0=8,6,0')
    ap.add_argument('out_dir', type=Path, help='local lang directory (MU_LANG_DIR)')
    a = ap.parse_args()
    print(json.dumps(convert(Snapshot.load(a.snapshot), a.out_dir)))


if __name__ == '__main__':
    main()
