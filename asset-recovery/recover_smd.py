#!/usr/bin/env python3
"""Validate/export the observed 24-byte-wrapped version-1 SMD text subset.

Preserves payload bytes. Does not interpret materials or verify a game loader.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def validate_payload(payload):
    lines = [line.strip() for line in payload.decode('ascii').splitlines() if line.strip()]
    if not lines or lines.pop(0) != 'version 1':
        raise ValueError('Expected version 1')
    sections = {}
    while lines:
        name = lines.pop(0)
        if name not in ('nodes', 'skeleton', 'triangles') or name in sections:
            raise ValueError('Unknown or duplicate section')
        if 'end' not in lines:
            raise ValueError('Unterminated section')
        stop = lines.index('end')
        sections[name] = lines[:stop]
        del lines[:stop+1]
    if set(sections) != {'nodes', 'skeleton', 'triangles'}:
        raise ValueError('Missing required section')
    nodes = {}
    for row in sections['nodes']:
        match = re.fullmatch(r'(\d+)\s+"([^"\r\n]+)"\s+(-?\d+)', row)
        if not match or int(match[1]) in nodes:
            raise ValueError('Invalid or duplicate node')
        nodes[int(match[1])] = {'name': match[2], 'parent': int(match[3])}
    if not nodes:
        raise ValueError('No nodes')
    for node in nodes:
        seen = set()
        parent = node
        while parent != -1:
            if parent not in nodes or parent in seen:
                raise ValueError('Missing or cyclic node parent')
            seen.add(parent)
            parent = nodes[parent]['parent']

    def numeric_row(row, fields):
        bits = row.split()
        if len(bits) != fields or not re.fullmatch(r'\d+', bits[0]) or int(bits[0]) not in nodes:
            raise ValueError('Unexpected row fields or unknown node')
        if not all(math.isfinite(float(value)) for value in bits[1:]):
            raise ValueError('Non-finite numeric value')

    frames = []
    current = None
    for row in sections['skeleton']:
        if row.startswith('time '):
            if not re.fullmatch(r'time \d+', row):
                raise ValueError('Invalid frame time')
            current = int(row[5:])
            if frames and current <= frames[-1]:
                raise ValueError('Frame times not increasing')
            frames.append(current)
        else:
            if current is None:
                raise ValueError('Transform before frame')
            numeric_row(row, 7)
    if not frames:
        raise ValueError('No skeleton frames')
    rows = sections['triangles']
    if not rows or len(rows) % 4:
        raise ValueError('Incomplete triangle')
    materials = set()
    for offset in range(0, len(rows), 4):
        materials.add(rows[offset])
        for row in rows[offset+1:offset+4]:
            numeric_row(row, 9)
    return {'nodes': nodes, 'frames': frames, 'triangles': len(rows)//4, 'materials': sorted(materials)}


def unwrap_smd(raw):
    if len(raw) < 48 or len(raw) > 16*1024*1024 or raw[:24] != raw[24:48]:
        raise ValueError('Not an observed 24-byte repeated-prefix wrapper within size limit')
    payload = raw[24:]
    return payload, validate_payload(payload)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--asset', required=True)
    p.add_argument('--output', type=Path, required=True, help='New .smd file outside installation')
    a = p.parse_args()
    root = a.root.resolve(strict=True)
    source = (root/a.asset).resolve(strict=True)
    dest = a.output.resolve()
    if root not in source.parents or root == dest or root in dest.parents or dest.suffix.lower() != '.smd':
        p.error('Input must be inside installation; output .smd must be outside it')
    if dest.exists() or dest.with_suffix('.json').exists():
        p.error('Output or metadata already exists')
    if source.stat().st_size > 16*1024*1024:
        p.error('Input exceeds bounded 16 MiB parser limit')
    raw = source.read_bytes()
    payload, facts = unwrap_smd(raw)
    facts.update(source=str(source), source_sha256=hashlib.sha256(raw).hexdigest(),
                 payload_sha256=hashlib.sha256(payload).hexdigest(), source_bytes=len(raw), payload_bytes=len(payload))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as f:
        f.write(payload)
    with dest.with_suffix('.json').open('x') as f:
        json.dump(facts, f, indent=2)
        f.write('\n')
    print(json.dumps(facts))

if __name__ == '__main__':
    main()
