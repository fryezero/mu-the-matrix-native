#!/usr/bin/env python3
"""Merge domain layout declarations into portable C field tables and layout.json.

MU_RECORD(record, known_extent, evidence) may repeat identically across lanes.
MU_FIELD(record, offset, size, type, zone, member, evidence) must never overlap,
even if declarations are identical. Types are little-endian scalars or arrays
(size is a multiple of type width); bytes is opaque storage. MU_ADDRESS(record,
address) binds a fixed-size record to a scene global. Unknown holes are omitted
from projection tables and remain replicated in the lease audit. All validation
finishes before any output is written. No private inputs are needed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TYPES = {'u8': (1, 'uint8_t'), 'i8': (1, 'int8_t'), 'u16': (2, 'uint16_t'),
         'i16': (2, 'int16_t'), 'u32': (4, 'uint32_t'), 'i32': (4, 'int32_t'),
         'u64': (8, 'uint64_t'), 'i64': (8, 'int64_t'), 'f32': (4, 'float'), 'bytes': (1, 'uint8_t')}
EVIDENCE = {'VERIFIED', 'STATIC', 'LIVE'}
ZONES = {'REPLICATED', 'MOTION', 'VIEW'}
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def load(directory):
    records, fields, addresses = {}, [], {}
    paths = sorted(Path(directory).glob('*.def'))
    if not paths:
        raise ValueError(f'{directory}: no layout declarations')
    for path in paths:
        text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m[0].count('\n'), path.read_text(), flags=re.S)
        for line, raw in enumerate(text.splitlines(), 1):
            raw = raw.split('//', 1)[0].strip()
            if not raw:
                continue
            where = f'{path.name}:{line}'
            m = re.fullmatch(r'(MU_RECORD|MU_FIELD|MU_ADDRESS)\(([^()]*)\)', raw)
            if not m:
                raise ValueError(f'{where}: malformed declaration')
            kind, args = m[1], [a.strip() for a in m[2].split(',')]
            if len(args) != {'MU_RECORD': 3, 'MU_FIELD': 7, 'MU_ADDRESS': 2}[kind]:
                raise ValueError(f'{where}: wrong argument count')
            name = args[0]
            if not IDENT.fullmatch(name):
                raise ValueError(f'{where}: invalid record name')
            if kind == 'MU_RECORD':
                size, ev = int(args[1], 0), args[2]
                if not 0 < size <= 0x100000 or ev not in EVIDENCE:
                    raise ValueError(f'{where}: invalid record extent/evidence')
                r = dict(name=name, size=size, evidence=ev, extent_kind="known_extent")
                if name in records and records[name] != r:
                    raise ValueError(f'{where}: conflicting record {name}')
                records[name] = r
            elif kind == 'MU_ADDRESS':
                address = int(args[1], 0)
                if not 0 < address <= 0xffffffff or name in addresses:
                    raise ValueError(f'{where}: invalid/duplicate address for {name}')
                addresses[name] = address
            else:
                off, size = int(args[1], 0), int(args[2], 0)
                typ, zone, member, ev = args[3:]
                if typ not in TYPES or zone not in ZONES or ev not in EVIDENCE or not IDENT.fullmatch(member):
                    raise ValueError(f'{where}: invalid type/zone/member/evidence')
                if off < 0 or size <= 0 or size % TYPES[typ][0]:
                    raise ValueError(f'{where}: invalid field range or type width')
                fields.append((name, dict(name=member, offset=off, size=size, type=typ, zone=zone,
                                          evidence=ev, source=where)))
    for name, f in fields:
        if name not in records or f['offset'] + f['size'] > records[name]['size']:
            raise ValueError(f"{f['source']}: {name}.{f['name']} outside declared record")
    if set(addresses) - set(records):
        raise ValueError('address without record')
    result = []
    for name, r in sorted(records.items()):
        fs = sorted((f for rec, f in fields if rec == name), key=lambda f: f['offset'])
        if not fs:
            raise ValueError(f'{name}: no fields')
        end, packed, members = 0, 0, set()
        previous = None
        for f in fs:
            if f['offset'] < end:
                raise ValueError(f"overlap in {name}: {previous['source']} ({previous['name']}) and "
                                 f"{f['source']} ({f['name']})")
            if f['name'] in members:
                raise ValueError(f"duplicate member {name}.{f['name']}")
            members.add(f['name'])
            f['projection_offset'] = packed
            packed += f['size']
            end = f['offset'] + f['size']
            previous = f
        result.append(dict(**r, address=addresses.get(name), fields=fs, projection_size=packed))
    # Generated C identifiers must also be unique on case-insensitive filesystems.
    if len({r['name'].lower() for r in result}) != len(result):
        raise ValueError('case-colliding record names')
    return dict(schema_version=1, byte_order='little', records=result)


COMMON = '''/* Generated by scripts/gen_layout.py. Do not edit. */
#ifndef MU_LAYOUT_TYPES_H
#define MU_LAYOUT_TYPES_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef enum { MU_LAYOUT_REPLICATED, MU_LAYOUT_MOTION, MU_LAYOUT_VIEW } mu_layout_zone;
typedef struct {
    const char *name, *type, *evidence;
    uint32_t offset, size, projection_offset;
    mu_layout_zone zone;
} mu_layout_field;
typedef struct {
    const char *name, *evidence;
    uint32_t size, projection_size, address;
    const mu_layout_field *fields;
    size_t field_count;
} mu_layout_record;
/* Projection is for native/offline byte buffers only. Unknown bytes are untouched on restore. */
static inline int mu_layout_project(const mu_layout_record *r, const uint8_t *raw, size_t n,
                                   uint8_t *packed, size_t cap) {
    if (!r || !raw || !packed || n < r->size || cap < r->projection_size) return 0;
    for (size_t i = 0; i < r->field_count; ++i) {
        const mu_layout_field *f = &r->fields[i];
        memcpy(packed + f->projection_offset, raw + f->offset, f->size);
    }
    return 1;
}
static inline int mu_layout_restore(const mu_layout_record *r, uint8_t *raw, size_t n,
                                   const uint8_t *packed, size_t cap) {
    if (!r || !raw || !packed || n < r->size || cap < r->projection_size) return 0;
    for (size_t i = 0; i < r->field_count; ++i) {
        const mu_layout_field *f = &r->fields[i];
        memcpy(raw + f->offset, packed + f->projection_offset, f->size);
    }
    return 1;
}
static inline uint64_t mu_layout_le(const uint8_t *p, size_t width) {
    uint64_t v = 0;
    for (size_t i = 0; i < width; ++i) v |= (uint64_t)p[i] << (8 * i);
    return v;
}
#endif
'''


def outputs(data):
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
    sha = hashlib.sha256(canonical).hexdigest()
    data = dict(data, sha256=sha)
    out = {'layout.json': json.dumps(data, indent=2) + '\n', 'layout_types.h': COMMON}
    all_h = ['/* Generated by scripts/gen_layout.py. */', '#ifndef MU_LAYOUT_ALL_H', '#define MU_LAYOUT_ALL_H',
             f'#define MU_LAYOUT_SHA256 "{sha}"']
    for r in data['records']:
        name = r['name']
        h = ['/* Generated by scripts/gen_layout.py. */', f'#ifndef MU_LAYOUT_{name.upper()}_H',
             f'#define MU_LAYOUT_{name.upper()}_H', '#include "layout_types.h"',
             f'#define MU_LAYOUT_{name}_SIZE {r["size"]}u',
             f'static const mu_layout_field MU_{name}_FIELDS[] = {{']
        for f in r['fields']:
            h.append('    {"%s", "%s", "%s", %du, %du, %du, MU_LAYOUT_%s},' %
                     (f['name'], f['type'], f['evidence'], f['offset'], f['size'],
                      f['projection_offset'], f['zone']))
        h.extend(['};', 'static const mu_layout_record MU_%s_LAYOUT = {"%s", "%s", %du, %du, %du, '
                  'MU_%s_FIELDS, sizeof MU_%s_FIELDS / sizeof MU_%s_FIELDS[0]};' %
                  (name, name, r['evidence'], r['size'], r['projection_size'], r['address'] or 0,
                   name, name, name)])
        for f in r['fields']:
            width, ctype = TYPES[f['type']]
            count = f['size'] // width
            fname = f'mu_layout_{name}_{f["name"]}'
            h.append(f'#define MU_LAYOUT_{name}_{f["name"]}_OFFSET {f["offset"]}u')
            h.append(f'static inline {ctype} {fname}(const uint8_t *p, size_t n, size_t index) {{')
            h.append(f'    if (!p || index >= {count}u || n < {f["offset"] + f["size"]}u) return 0;')
            h.append(f'    uint64_t v = mu_layout_le(p + {f["offset"]}u + index * {width}u, {width}u);')
            if f['type'] == 'f32':
                h.append('    uint32_t bits = (uint32_t)v; float result; memcpy(&result, &bits, 4); return result;')
            elif f['type'].startswith('i'):
                # Avoid implementation-defined unsigned-to-signed conversion.
                h.append(f'    {ctype} result; uint{width * 8}_t bits = (uint{width * 8}_t)v; '
                         f'memcpy(&result, &bits, {width}); return result;')
            else:
                h.append(f'    return ({ctype})v;')
            h.append('}')
        h.append('#endif')
        out[f'layout_{name}.h'] = '\n'.join(h) + '\n'
        all_h.append(f'#include "layout_{name}.h"')
    all_h.append('static const mu_layout_record *const MU_LAYOUT_RECORDS[] = {')
    all_h.extend(f'    &MU_{r["name"]}_LAYOUT,' for r in data['records'])
    all_h.extend(['};', '#define MU_LAYOUT_RECORD_COUNT (sizeof MU_LAYOUT_RECORDS / sizeof MU_LAYOUT_RECORDS[0])',
                  '#endif'])
    out['layout_all.h'] = '\n'.join(all_h) + '\n'
    return out


def generate(directory, out):
    generated = outputs(load(directory))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in generated.items():
        p = out / name
        if not p.exists() or p.read_text() != content:
            tmp = p.with_suffix(p.suffix + '.tmp')
            tmp.write_text(content)
            tmp.replace(p)
    for p in out.glob('layout_*.h'):
        if p.name not in generated:
            p.unlink()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layout', type=Path, default=ROOT / 'native/session/layout')
    p.add_argument('--out', type=Path, default=ROOT / 'native/build/gen')
    args = p.parse_args()
    try:
        generate(args.layout, args.out)
    except ValueError as e:
        print(f'gen_layout: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
