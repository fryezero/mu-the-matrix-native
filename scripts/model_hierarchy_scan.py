#!/usr/bin/env python3
"""Locate x86-32 instructions that use the 0x8c bone-record stride.

A byte match is kept only when Capstone decodes an instruction starting at
the match whose immediate operand equals the stride.  The enclosing function
start is a candidate: the nearest preceding `push ebp; mov ebp, esp` from
which linear decoding lands exactly on the match.  Neither result is a
recovered symbol; both are reported as candidates with their checks.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_hierarchy_common as common  # noqa: E402

STRIDE = 0x8c
PROLOGUE = b'\x55\x8b\xec'
MAX_BACKTRACK = 0x2000
FIELD_RE = re.compile(r'(byte|word|dword) ptr \[(\w+) \+ (0x[0-9a-f]+)\]')


def stride_sites(region, stride=STRIDE, engine=None):
    engine = engine or common.decoder()
    imm = stride.to_bytes(4, 'little')
    patterns = [
        # imul r32, r/m32, imm32: opcode 69 then ModRM (+SIB/disp) then imm32
        re.compile(rb'\x69' + rb'.{1,6}?' + re.escape(imm), re.S),
        # mov r32, imm32 (b8+r) and add/sub r/m32, imm32 (81 /0, /5) or eax form (05, 2d)
        re.compile(rb'[\xb8-\xbf\x05\x2d]' + re.escape(imm), re.S),
        re.compile(rb'\x81.' + re.escape(imm), re.S),
    ]
    seen = {}
    for pattern in patterns:
        for match in pattern.finditer(region.data):
            va = region.base + match.start()
            if va in seen:
                continue
            decoded = next(engine.disasm(region.read(va, min(16, region.end - va)), va), None)
            if decoded is None or decoded.size != match.end() - match.start():
                continue
            imms = [op.imm & 0xffffffff for op in decoded.operands if op.type == 2]
            if stride in imms:
                seen[va] = common.text_of(decoded)
    return dict(sorted(seen.items()))


def function_candidate(region, site, engine=None, max_backtrack=MAX_BACKTRACK):
    """Nearest prologue whose linear decode reaches `site` on a boundary."""
    engine = engine or common.decoder()
    low = max(region.base, site - max_backtrack)
    window = region.read(low, site - low)
    position = window.rfind(PROLOGUE)
    while position >= 0:
        start = low + position
        try:
            _, stop = common.decode_range(region, start, site, engine)
        except ValueError:
            stop = -1
        if stop is None:
            return start
        position = window.rfind(PROLOGUE, 0, position)
    return None


def field_accesses(instructions):
    fields = []
    for instruction in instructions:
        text = common.text_of(instruction)
        for width, register, displacement in FIELD_RE.findall(text):
            fields.append({'site': hex(instruction.address), 'width': width,
                           'base': register, 'offset': displacement, 'text': text})
    return fields


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', required=True, help='pinned restored first section')
    parser.add_argument('--output', required=True, help='new JSON report path')
    args = parser.parse_args(argv)
    output = Path(args.output)
    if output.exists():
        parser.error('refusing to overwrite an existing report')
    region = common.load_text(args.text)
    engine = common.decoder()
    sites = stride_sites(region, engine=engine)
    report = {'text_sha256': common.TEXT_SHA256, 'target_sha256': common.TARGET_SHA256,
              'stride': hex(STRIDE), 'method': 'byte pattern + Capstone decode at match',
              'sites': []}
    for va, text in sites.items():
        start = function_candidate(region, va, engine)
        report['sites'].append({'site': hex(va), 'text': text,
                                'function_candidate': hex(start) if start else None})
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(sites)} stride sites; report {output}')


if __name__ == '__main__':
    main()
