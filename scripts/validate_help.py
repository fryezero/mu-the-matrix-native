#!/usr/bin/env python3
"""SYS-MISC-001b: synthetic HelpWindow reader vs pinned original instructions.

Reuses the data-table machine's explicit CRT file/allocator boundary. The
reader, XOR decoder, checksum, memset and memcpy run as original instructions.
Missing/corrupt input reaches the original error import; native policy clears
the output and returns a status instead of posting a shutdown message.
Truncation is tested portably, since the original ignores short fread results.
No client-derived bytes or decoded fields are serialized in this report.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
import test_help as th
import pins
import validate_data_tables as vd

LOADER = 0x00b8968b


class ReaderTrace(vd.LoaderTrace):
    def __init__(self, machine, image, missing=False):
        self.missing = missing
        self.object = None
        super().__init__(machine, LOADER, image, False)

    def allocate(self, size):
        address = super().allocate(size)
        if size == 0x40000:
            self.object = address
            self.uc.mem_write(address + 0x78, b'\xa5' * th.PAYLOAD)
        return address

    def on_call(self, uc, address, size, ignored):
        if address == vd.FOPEN and self.missing:
            self.events.append(('fopen-missing',))
            self.finish(0)
        else:
            super().on_call(uc, address, size, ignored)


def original(machine, image, missing=False):
    trace = ReaderTrace(machine, image, missing).run('Data\\Local\\helpdata.bmd')
    try:
        skipped = {e[1] for e in trace.events if isinstance(e, tuple) and e[0] == 'skip'}
        if not skipped <= {0x009619dd, 0x01206598}:
            raise RuntimeError(f'Unexpected boundary calls: {skipped}')
        if trace.stop == 'import' and trace.import_call != (0x00b89851 if missing else 0x00b89791):
            raise RuntimeError(f'Unexpected error import return: {trace.import_call}')
        table = bytes(machine.uc.mem_read(trace.object + 0x78, th.PAYLOAD))
        events = [e for e in trace.events if isinstance(e, dict)]
        outcome = 'returned' if trace.stop is None else trace.stop
        if outcome not in ('returned', 'import'):
            raise RuntimeError(f'Unexpected original reader outcome: {outcome}')
        return table, events, outcome
    finally:
        trace.close()


def decode(lib, image):
    out = ctypes.create_string_buffer(b'\xa5' * th.PAYLOAD, th.PAYLOAD)
    status = lib.mu_help_decode(out, image, len(image))
    return status, out.raw


def corpus(cases):
    rng = random.Random(0x001b)
    yield from [('valid-fixture', th.fixture()[1], False)]
    for i in range(cases - 1):
        # Arbitrary record bytes exercise byte copies at every row position,
        # including records the later zero-id sentinel would hide.
        rows = [rng.randbytes(136) for _ in range(512)]
        yield f'valid-{i}', th.encode(rows), False
    valid = th.fixture()[1]
    for offset in (0, 135, 136, th.PAYLOAD - 1, th.PAYLOAD, th.PAYLOAD + 3):
        changed = bytearray(valid)
        changed[offset] ^= 1
        yield f'corrupt-{offset}', bytes(changed), False
    yield 'missing', b'', True


MUTANTS = {
    'checksum-key': ('data_tables.c', '512, 0xc4f7, 0, 0, CHK}', '512, 0xc4f6, 0, 0, CHK}'),
    'row-stride': ('data_tables.c', 'MU_DATA_FIXED, 136, 512, 0xc4f7', 'MU_DATA_FIXED, 135, 512, 0xc4f7'),
    'row-count': ('data_tables.c', 'MU_DATA_FIXED, 136, 512, 0xc4f7', 'MU_DATA_FIXED, 136, 511, 0xc4f7'),
    'xor-phase-key': ('data_codec.c', '{0xfc, 0xcf, 0xab}', '{0xfd, 0xcf, 0xab}'),
    'whole-payload-phase': ('data_tables.c',
                            'return records(d, 0, s->record_count, s->record_size);',
                            'return unit(d, 0, s->record_count * s->record_size) ? MU_DATA_OK : MU_DATA_TRUNCATED;'),
    'last-byte-copy': ('help.c', 'memcpy(out->rows, image, MU_HELP_PAYLOAD_SIZE)',
                       'memcpy(out->rows, image, MU_HELP_PAYLOAD_SIZE - 1)'),
    'stale-on-failure': ('help.c', 'memset(out, 0, sizeof *out);', '/* planted stale output */'),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=24)
    ap.add_argument('--mutants', action='store_true')
    ap.add_argument('--game-root', type=Path, help='optional installed helpdata check, never exports rows')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.cases < 1:
        ap.error('--cases must be positive')
    text = pins.TEXT.read()
    data = pins.DATA.read()
    feature = pins.FEATURE.read()
    machine = vd.Machine(text, data, feature)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'feature_sha256': pins.FEATURE.sha256, 'families': {}, 'mutants': {}}
    entries = list(corpus(args.cases))
    if args.game_root:
        image = (args.game_root/'Data/Local/helpdata.bmd').read_bytes()
        entries.append(('installed', image, False))
        report['installed_input_sha256'] = hashlib.sha256(image).hexdigest()
    references = []
    with tempfile.TemporaryDirectory(prefix='mu-help-validate-') as directory:
        work = Path(directory)
        lib = th.library(th.build_library(work))
        for label, image, missing in entries:
            table, events, outcome = original(machine, image, missing)
            family = label.split('-')[0]
            expected_status = 1 if missing else 0 if family in ('valid', 'installed') else 3
            if missing:
                out = ctypes.create_string_buffer(b'\xa5' * th.PAYLOAD, th.PAYLOAD)
                status = lib.mu_help_read(out, str(work/'absent.bmd').encode())
                actual = out.raw
            else:
                status, actual = decode(lib, image)
            match = status == expected_status and actual == table
            units = sum(e['kind'] == 'xor3' for e in events)
            if expected_status == 0:
                match &= outcome == 'returned' and units == 512
            else:
                match &= outcome == 'import' and units == 0
            row = report['families'].setdefault(family, {'cases': 0, 'mismatches': 0, 'decode_units': 0})
            row['cases'] += 1
            row['mismatches'] += int(not match)
            row['decode_units'] += units
            if not match:
                raise AssertionError(f'{label}: reader mismatch, status={status}, outcome={outcome}, units={units}')
            references.append((label, image, missing, expected_status, table))
        if args.mutants:
            paths = [ROOT/'reconstructed/help/help.c', ROOT/'reconstructed/help/help_controller.c', ROOT/'reconstructed/data/data_tables.c',
                     ROOT/'reconstructed/data/data_codec.c']
            for name, (filename, before, after) in MUTANTS.items():
                folder = work/name
                folder.mkdir()
                sources = []
                for path in paths:
                    source = path.read_text()
                    if path.name == filename:
                        if before not in source:
                            raise AssertionError(f'Mutant source anchor missing: {name}')
                        source = source.replace(before, after)
                    dest = folder/path.name
                    dest.write_text(source)
                    sources.append(dest)
                mutant = th.library(th.build_library(folder, sources))
                caught = None
                for label, image, missing, status, expected in references:
                    if missing:
                        continue
                    if decode(mutant, image) != (status, expected):
                        caught = label
                        break
                if not caught:
                    raise AssertionError(f'Compiled mutant survived: {name}')
                report['mutants'][name] = {'caught': True, 'case': caught}
    report['mismatches'] = sum(x['mismatches'] for x in report['families'].values())
    report['cases'] = sum(x['cases'] for x in report['families'].values())
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
