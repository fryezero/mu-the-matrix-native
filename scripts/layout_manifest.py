#!/usr/bin/env python3
"""Read generated layout.json for Python validators and read-only reader builds."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'native/build/gen/layout.json'
FORMATS = {'u8': 'B', 'i8': 'b', 'u16': 'H', 'i16': 'h', 'u32': 'I', 'i32': 'i',
           'u64': 'Q', 'i64': 'q', 'f32': 'f', 'bytes': 'B'}
WIDTHS = {'u8': 1, 'i8': 1, 'u16': 2, 'i16': 2, 'u32': 4, 'i32': 4,
          'u64': 8, 'i64': 8, 'f32': 4, 'bytes': 1}


def load(path=None):
    path = Path(path) if path else DEFAULT
    if path == DEFAULT:
        # Generation is cheap and deterministic, and also detects removed/new lane files.
        subprocess.run([sys.executable, str(ROOT / 'scripts/gen_layout.py')], check=True)
    data = json.loads(path.read_text())
    digest = data.pop('sha256')
    actual = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if actual != digest or data['schema_version'] != 1 or data['byte_order'] != 'little':
        raise ValueError('layout.json: digest, schema or byte order mismatch')
    data['sha256'] = digest
    return data


def record(name, data=None):
    for r in (data if data is not None else load())['records']:
        if r['name'] == name:
            return r
    raise ValueError(f'layout.json: missing record {name}')


def fields(name, omit=(), data=None):
    """The existing validators' (member, offset, struct format) projection table."""
    result = []
    for f in record(name, data)['fields']:
        if f['name'] in omit:
            continue
        count = f['size'] // WIDTHS[f['type']]
        result.append((f['name'], f['offset'], (str(count) if count > 1 else '') + FORMATS[f['type']]))
    return result


def reader_header(data):
    obj = record('OBJECT', data)
    next_field = next(f for f in obj['fields'] if f['name'] == 'next')
    out = ['/* Generated from layout.json by scripts/layout_manifest.py. */',
           f'#define MU_READER_OBJECT_SIZE {obj["size"]}u',
           f'#define MU_READER_OBJECT_NEXT {next_field["offset"]}u']
    for r in data['records']:
        if r['address'] is not None:
            out.append(f'#define MU_READER_{r["name"]} {r["address"]}u')
    # Preserve the existing reader's MUGLBLV1 entry order and byte contract.
    names = ['SceneCameraAngle', 'SceneCameraPosition', 'SceneCameraFov', 'SceneCameraFar',
             'SceneFlag', 'SceneTime', 'SceneLoginFade']
    out.append('static const uint32_t mu_reader_scene_globals[][2] = {')
    for name in names:
        r = record(name, data)
        out.append(f'    {{MU_READER_{name}, {r["size"]}u}},')
    out.append('};')
    return '\n'.join(out) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path)
    p.add_argument('--reader-header', type=Path, required=True)
    args = p.parse_args()
    content = reader_header(load(args.manifest))
    path = args.reader_header
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != content:
        path.write_text(content)


if __name__ == '__main__':
    main()
