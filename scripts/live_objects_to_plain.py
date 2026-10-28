#!/usr/bin/env python3
"""Turn a live object-list snapshot into an EncTerrain plaintext (NATIVE-OBJECTS-001, live read).

Input: the file written by the macOS read-only snapshot tool (live-readers/objread.c):

    "MUOBJLV1", i32 world [0x01cf15fc], i32 world [0x01cf1600], i32 count [0x0bdb5888], u32 n,
    n x (u32 address, u32 sector, 0x3d8 object bytes)

The objects are the ones CreateObject 0x016d8538 built and linked into the 256 sector lists at 0x0bdb61f0.
CreateObject copies the loader's record into fixed object fields (docs/research/client-objects.md, static reading):

    type +0x5c (i32), position +0x158, start position +0x110, angle +0x164, light +0xec, scale +0xa0,
    flags +5/+6/+7, +0x68 = -2 for a nonzero hidden flag (else -1), values +0xe4/+0xe8.

A sidecar <out>.hidden lists the types whose objects carry +0x68 = -2 at runtime (world handlers set it per
type, e.g. Lorencia's PoseBox01; the native drawer skips them).

Output: a plaintext in the loader's layout (u8 version, u8 map number, i16 count, records) that
`--objects PLAIN_FILE` loads. --installed picks the version the installed file's length implies for the count;
default 5.
Records take the current position (+0x158) unless --start-position is given; the summary counts objects whose
two positions differ. The record order is sector order, not file order. Objects whose type is outside
0..299 (made by code, not by the file) are dropped unless --keep-all. The output is decoded game data: keep it
local, never commit it.
"""
import native_data_manifest as manifest
import argparse
import json
from pathlib import Path
import struct
import sys

OBJECT_BYTES = 0x3d8


def read_snapshot(path):
    data = Path(path).read_bytes()
    if data[:8] != b'MUOBJLV1':
        raise ValueError('not an object-list snapshot')
    world, world2, count, n = struct.unpack_from('<iiiI', data, 8)
    objects, offset = [], 24
    for _ in range(n):
        address, sector = struct.unpack_from('<II', data, offset)
        objects.append((address, sector, data[offset + 8:offset + 8 + OBJECT_BYTES]))
        offset += 8 + OBJECT_BYTES
    return world, world2, count, objects


def fields(obj, current=True):
    f = lambda o, n=1: struct.unpack_from('<%df' % n, obj, o)
    return {
        'type': struct.unpack_from('<i', obj, 0x5c)[0],
        'position': f(0x158 if current else 0x110, 3),
        'current_position': f(0x158, 3),
        'start_position': f(0x110, 3),
        'angle': f(0x164, 3),
        'light': f(0xec, 3),
        'scale': f(0xa0)[0],
        'flags': tuple(obj[5:8]),
        'state_68': struct.unpack_from('<i', obj, 0x68)[0],
        'value_e4': f(0xe4)[0],
        'value_e8': f(0xe8)[0],
    }


RECORD_SIZES = {0: 30, 1: 32, 2: 33, 3: 45, 4: 46, 5: 54}


def installed_version(path, count):
    """The record version whose size makes 4 + count * size equal the installed file's length."""
    size = Path(path).stat().st_size
    fits = [v for v, r in RECORD_SIZES.items() if count >= 0 and 4 + count * r == size]
    if not fits:
        raise ValueError(f'{path}: no record version fits {count} objects in {size} bytes')
    return fits[0]


def to_plain(map_number, records, version=5):
    """Plaintext in the loader's layout; fields the version does not carry are left out."""
    out = bytearray([version, map_number & 0xff]) + struct.pack('<h', len(records))
    for r in records:
        out += struct.pack('<h3f3ff', r['type'], *r['position'], *r['angle'], r['scale'])
        if version >= 1:
            out += bytes(r['flags'][:2])
        if version >= 2:
            out += bytes(r['flags'][2:3])
        if version >= 3:
            out += struct.pack('<3f', *r['light'])
        if version >= 4:   # +0x68 also changes at runtime; only meaningful for version >= 4 files
            out += bytes([1 if r['state_68'] == -2 else 0])
        if version >= 5:
            out += struct.pack('<ff', r['value_e4'], r['value_e8'])
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--out', type=Path, help='plaintext output (local only)')
    parser.add_argument('--map', type=int, help='map number byte (default: the terrain folder of the world)')
    parser.add_argument('--start-position', action='store_true', help='use +0x110 instead of +0x158')
    parser.add_argument('--keep-all', action='store_true')
    parser.add_argument('--json', type=Path, help='per-object field dump (local only)')
    parser.add_argument('--version', type=int, choices=range(6), help='record version to write (default 5)')
    parser.add_argument('--installed', type=Path,
                        help='installed EncTerrain<n>.obj: write the version its length implies for the count')
    manifest.arguments(parser)
    args = parser.parse_args()
    if args.out:
        manifest.prepare(args)
        manifest.prepare_output(args, args.out.parent)
    world, world2, count, objects = read_snapshot(args.snapshot)
    records = [fields(o, not args.start_position) for _, _, o in objects]
    kept = [r for r in records if args.keep_all or 0 <= r['type'] < 300]
    moved = sum(1 for r in records if r['current_position'] != r['start_position'])
    summary = {'world': world, 'world2': world2, 'count_global': count, 'objects_in_sectors': len(objects),
               'kept': len(kept), 'moved_since_creation': moved,
               'types': len({r['type'] for r in kept}), 'hidden': sum(r['state_68'] == -2 for r in kept)}
    print(json.dumps(summary))
    if args.json:
        args.json.write_text(json.dumps([dict(r, address=hex(a), sector=s) for (a, s, _), r in
                                         zip(objects, records)], indent=0))
    if args.out:
        folder = args.map if args.map is not None else world + 1
        version = args.version if args.version is not None else \
            installed_version(args.installed, count) if args.installed else 5
        args.out.write_bytes(to_plain(folder, kept, version))
        hidden = sorted({r['type'] for r in kept if r['state_68'] == -2})
        args.out.with_suffix('.hidden').write_text(''.join(f'{t}\n' for t in hidden))
        manifest.publish(args, args.out.parent, f'objects-export-v1-map-{folder}-version-{version}-start-{int(args.start_position)}-keep-{int(args.keep_all)}', [args.snapshot] + ([args.installed] if args.installed else []))
        print(json.dumps({'out': str(args.out), 'version': version, 'records': len(kept)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
