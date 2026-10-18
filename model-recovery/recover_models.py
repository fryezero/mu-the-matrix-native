#!/usr/bin/env python3
"""Validate BMD assets and export selected real meshes without modifying inputs.

--client-layout parses the way the client's model reader does (docs/research/
model-edge.md): values outside the strict semantics are kept and listed per
file under client_semantics instead of rejecting the file.
"""
import argparse
import json
import math
from pathlib import Path
from bmd10 import BmdError, obj_text, summarize
from bmd_encrypted import parse_model_file


def finite_json(value):
    """JSON-safe copy: non-finite floats become strings (their bits are in client_semantics)."""
    if isinstance(value, float) and not math.isfinite(value):
        return 'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--asset', action='append', default=[])
    parser.add_argument('--validate-all', action='store_true')
    parser.add_argument('--client-layout', action='store_true',
                        help="accept values the client's reader accepts; list them instead of rejecting")
    args = parser.parse_args()
    root, output = args.root.resolve(strict=True), args.output.resolve()
    if output.exists() or output == root or root in output.parents:
        parser.error('Output must be a new directory outside the installation')
    selected = set()
    for relative in args.asset:
        path = (root/relative).resolve(strict=True)
        if root not in path.parents:
            parser.error('Selected asset is outside the installation')
        selected.add(path)
    identity = lambda p: (p.stat().st_dev,p.stat().st_ino)
    selected_ids = {identity(p) for p in selected}
    paths = {identity(p): p for p in selected}
    if args.validate_all:
        paths.update((identity(p),p.resolve()) for p in root.rglob('*')
                     if p.is_file() and p.suffix.lower() == '.bmd'
                     and root in p.resolve().parents)
    if not paths:
        parser.error('Select assets or --validate-all')
    output.mkdir(parents=True)
    records = []
    totals = {'total': len(paths), 'parsed': 0, 'rejected': 0,
              'unsupported': 0, 'json_exports': 0, 'obj_exports': 0}
    versions = {}
    for index, path in enumerate(sorted(paths.values())):
        record = {'path': str(path.relative_to(root))}
        try:
            with path.open('rb') as source:
                header = source.read(4)
            version = header[3] if len(header) == 4 and header[:3] == b'BMD' else None
            record['version'] = version
            if version not in (10,12,14,15):
                record.update(status='unsupported', error='Unsupported model envelope or table format')
            else:
                model = parse_model_file(path, client_layout=args.client_layout)
                record.update(summarize(model), status='parsed')
                if model.get('client_semantics'):
                    issues = model['client_semantics']
                    record['client_semantics'] = {'count': len(issues), 'strict': sum(x['strict'] for x in issues),
                                                  'kinds': sorted({x['kind'] for x in issues})}
                if 'modulus' in model:
                    record['modulus'] = model['modulus']
                    record['decoded_payload_sha256'] = model['decoded_payload_sha256']
                if model.get('cipher_block_trailer_hex'):
                    record['cipher_block_trailer_hex'] = model['cipher_block_trailer_hex']
                if identity(path) in selected_ids:
                    destination = output/path.relative_to(root)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.with_suffix('.json').write_text(json.dumps(finite_json(model),indent=2,allow_nan=False)+'\n')
                    record['json'] = str(destination.with_suffix('.json').relative_to(output))
                    totals['json_exports'] += 1
                    try:
                        destination.with_suffix('.obj').write_text(obj_text(model))
                        record['obj'] = str(destination.with_suffix('.obj').relative_to(output))
                        totals['obj_exports'] += 1
                    except BmdError as error:
                        record['pose_error'] = str(error)
        except (BmdError, OSError) as error:
            record.update(status='rejected', error=str(error))
        status = record['status']
        totals[status] += 1
        version = str(record.get('version'))
        counts = versions.setdefault(version, {'parsed': 0, 'rejected': 0, 'unsupported': 0})
        counts[status] += 1
        records.append(record)
        if (index+1) % 250 == 0:
            print(json.dumps({'processed': index+1, **totals}), flush=True)
    manifest = {'summary': totals, 'versions': versions, 'files': records,
                'limitations': ['Structural file decoding, not verified original engine rendering.',
                                'ECB alignment trailers are preserved without inferring padding semantics.',
                                'Other/table envelopes remain unsupported; recognized models can still be rejected.']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'summary':totals,'versions':versions}),flush=True)
    return 0 if not totals['rejected'] and not totals['unsupported'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
