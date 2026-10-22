#!/usr/bin/env python3
"""Probe the available 4th/5th skill inputs without inventing runtime manager state.

Runs the original getters on every captured class and reports missing reads.
ParticleSkill +0x38/+0x40 hold vectors of 0x24-byte records: getters select
the first by (word+8 * 512 + word+12), word+16, or word+24 respectively.
This is an input/lookup probe, not validation of either complete skill tree.
Only addresses, counts and failures are written; no table payload is exported.
"""
import argparse
import json
import os
from pathlib import Path

import client_ui_machine as cm
import live_lang_to_plain as plain
import validate_lang as vl


def probe(text, data, snapshot):
    m = vl.LangMachine(text, data, snapshot)
    report = {'fourth': {}, 'fifth': {}, 'manager': {}}
    for name, obj, function, nargs in (('nodes', 0x06fbb8ec, 0x010b4406, 3),
                                      ('tooltips', 0x06fbb930, 0x010ba100, 1),
                                      ('side_options', 0x06fbbaec, 0x010b6ec4, 1)):
        nodes = snapshot.tree(obj + 0x3c)
        row = {'top_level_entries': len(nodes), 'returned': 0, 'blocked': 0, 'first_blocker': None}
        for key, _ in nodes:
            m.prepare(force=True)
            try:
                m.call(function, [key] + [0] * (nargs - 1), ecx=obj)
                row['returned'] += 1
            except cm.CaseError as error:
                row['blocked'] += 1
                row['first_blocker'] = row['first_blocker'] or str(error)
        report['fourth'][name] = row

    obj = 0x06fbc8bc
    checks = mismatches = wrong_stride = 0
    for offset, functions in ((0x38, ((0x010bce97, 'item'), (0x010bcf3a, 'skill'))),
                              (0x40, ((0x010bd07a, 'option'),))):
        nodes = snapshot.tree(obj + offset)
        count = 0
        for key, node in nodes:
            begin, end = snapshot.u32(node + 0x14), snapshot.u32(node + 0x18)
            assert (end - begin) % 0x24 == 0
            snapshot.read(begin, end - begin)
            records = list(range(begin, end, 0x24))
            count += len(records)
            for address in records:
                for function, kind in functions:
                    field = lambda record, at: snapshot.i32(record + at)
                    lookup = lambda record: (field(record, 8) * 512 + field(record, 12) if kind == 'item'
                                              else field(record, 16 if kind == 'skill' else 24))
                    value = lookup(address)
                    expected = next(record for record in records if lookup(record) == value)
                    m.prepare(force=True)
                    actual = m.call(function, [key, value], ecx=obj)
                    checks += 1
                    mismatches += actual != expected
                    wrong_stride += actual != begin + records.index(expected) * 0x20
        report['fifth'][hex(offset)] = {'groups': len(nodes), 'records': count, 'stride': 0x24}
    report['fifth'].update(lookup_checks=checks, mismatches=mismatches,
                           wrong_stride_detected=wrong_stride)
    # Do not define a fabricated singleton, TLS state or card inventory to make this return a manager.
    m.prepare(force=True)
    try:
        report['manager']['returned'] = hex(m.call(0x00abeb00))
    except cm.CaseError as error:
        report['manager']['blocker'] = str(error)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    p.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    p.add_argument('--snapshot', required=True)
    p.add_argument('--output')
    a = p.parse_args()
    for path, digest in ((a.text, vl.TEXT_SHA256), (a.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    report = probe(Path(a.text).read_bytes(), Path(a.data).read_bytes(), plain.Snapshot.load(a.snapshot))
    report.update(text_sha256=vl.TEXT_SHA256, data_sha256=vl.DATA_SHA256)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return int(report['fifth']['mismatches'] != 0)


if __name__ == '__main__':
    raise SystemExit(main())
