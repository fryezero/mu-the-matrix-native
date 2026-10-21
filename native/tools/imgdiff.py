#!/usr/bin/env python3
"""Pixel comparison of two renders (NATIVE-PERF-001 before/after checks).

    imgdiff.py A.png B.png [--max-delta N] [--max-fraction F] [--json]
    imgdiff.py --dirs DIR_A DIR_B [...]     every PNG present in both directories

Reads the stored-deflate RGBA PNGs the native tools write (mu_png_write; any
8-bit RGBA PNG without interlacing whose rows use filter 0). Compares RGB
only: the framebuffer alpha is never shown. Reports the pixels that differ,
the largest channel difference and the fraction of pixels above --max-delta;
exits 1 when a pair exceeds --max-delta on more than --max-fraction of its
pixels or differs in size.
"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path


def read_png(path):
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'{path}: not a PNG')
    pos, idat, width, height = 8, [], 0, 0
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            width, height, depth, colour = struct.unpack('>IIBB', body[:10])
            if depth != 8 or colour != 6:
                raise ValueError(f'{path}: not RGBA8')
        elif kind == b'IDAT':
            idat.append(body)
        pos += 12 + length
    raw = zlib.decompress(b''.join(idat))
    stride = width * 4 + 1
    rows = []
    for y in range(height):
        if raw[y * stride] != 0:
            raise ValueError(f'{path}: row filter {raw[y * stride]} (only filter 0 is read)')
        rows.append(raw[y * stride + 1:(y + 1) * stride])
    return width, height, rows


def compare(a, b, max_delta):
    wa, ha, ra = read_png(a)
    wb, hb, rb = read_png(b)
    if (wa, ha) != (wb, hb):
        return {'a': str(a), 'b': str(b), 'size_mismatch': [wa, ha, wb, hb]}
    differing = above = worst = 0
    for y in range(ha):
        row_a, row_b = ra[y], rb[y]
        if row_a == row_b:
            continue
        for x in range(0, wa * 4, 4):
            if row_a[x:x + 3] == row_b[x:x + 3]:
                continue
            d = max(abs(row_a[x] - row_b[x]), abs(row_a[x + 1] - row_b[x + 1]), abs(row_a[x + 2] - row_b[x + 2]))
            differing += 1
            if d > worst:
                worst = d
            if d > max_delta:
                above += 1
    n = wa * ha
    return {'a': str(a), 'b': str(b), 'pixels': n, 'differing': differing, 'max_delta': worst,
            'above_tolerance': above, 'above_fraction': above / n if n else 0.0,
            'identical': differing == 0}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--dirs', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--max-delta', type=int, default=0)
    ap.add_argument('--max-fraction', type=float, default=0.0)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    pairs = []
    if a.dirs:
        da, db = Path(a.dirs[0]), Path(a.dirs[1])
        for p in sorted(da.glob('*.png')):
            if (db / p.name).exists():
                pairs.append((p, db / p.name))
    if len(a.paths) == 2:
        pairs.append((Path(a.paths[0]), Path(a.paths[1])))
    if not pairs:
        ap.error('nothing to compare')
    status = 0
    results = []
    for pa, pb in pairs:
        r = compare(pa, pb, a.max_delta)
        r['pass'] = 'size_mismatch' not in r and r['above_fraction'] <= a.max_fraction
        status |= 0 if r['pass'] else 1
        results.append(r)
        if not a.json:
            if 'size_mismatch' in r:
                print(f"{pa.name}: size mismatch {r['size_mismatch']}")
            else:
                print(f"{pa.name}: {'identical' if r['identical'] else 'differs'}, {r['differing']} px differ, "
                      f"max delta {r['max_delta']}, {r['above_tolerance']} px above {a.max_delta} "
                      f"({100 * r['above_fraction']:.4f} %) {'ok' if r['pass'] else 'FAIL'}")
    if a.json:
        print(json.dumps(results, indent=1))
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
