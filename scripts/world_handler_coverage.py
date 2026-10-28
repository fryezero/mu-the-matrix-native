#!/usr/bin/env python3
"""Check the authored 48-class address inventory against the pinned factory and vtables.

No client bytes or strings are exported. Only addresses/world registrations are compared.
The implementation statuses are reviewed annotations, not inferred from address equality.
"""
import argparse
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'docs/research/world-handler-coverage.json'
SLOTS = {'create': 0x2c, 'move': 0x30, 'visual': 0x34,
         'custom_render': 0x38, 'after_render': 0x3c, 'invisible_move': 0x1c}


def inventory(text, data):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_IMM, X86_OP_MEM
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    cs.detail = True

    def instructions(address, size=0x200):
        return list(cs.disasm(text[address - 0x401000:address - 0x401000 + size], address))

    factory = instructions(0xea488e, 0xd9b)
    rows = {}
    for k, ins in enumerate(factory):
        if ins.mnemonic == 'call' and k > 1 and factory[k-1].op_str == 'eax' \
                and factory[k-2].mnemonic == 'lea' and factory[k-2].op_str.startswith('eax, [ebp -'):
            address = ins.operands[0].imm
            if address < 0xea0000:
                rows[factory[k-2].op_str.split(', ', 1)[1]] = {'factory': hex(address), 'worlds': []}
        if ins.mnemonic == 'call' and ins.op_str == '0xea8cf9':
            rows[factory[k-3].op_str.split(', ', 1)[1]]['worlds'].append(factory[k-4].operands[0].imm)
    for row in rows.values():
        body = instructions(int(row['factory'], 16))
        alloc = next(k for k, ins in enumerate(body) if ins.mnemonic == 'call' and ins.op_str == '0x191ba7b')
        constructor = next(ins.operands[0].imm for ins in body[alloc+1:] if ins.mnemonic == 'call')
        tables = []
        for ins in instructions(constructor):
            if ins.mnemonic == 'ret':
                break
            if ins.mnemonic == 'mov' and len(ins.operands) == 2 \
                    and ins.operands[0].type == X86_OP_MEM and ins.operands[0].mem.disp == 0 \
                    and ins.operands[1].type == X86_OP_IMM and 0x1a7c000 < ins.operands[1].imm < 0x1cf0000:
                tables.append(ins.operands[1].imm)
        if len(tables) != 1:
            raise ValueError(f'ambiguous constructor {constructor:#x}: {tables}')
        table = tables[0]
        row.update(constructor=hex(constructor), vtable=hex(table), handlers={
            name: hex(struct.unpack_from('<I', data, table + offset - 0x1a7c000)[0])
            for name, offset in SLOTS.items()})
    return list(rows.values())


def markdown(document):
    rows = document['classes']
    lines = ['# World-handler class coverage', '',
             'RENDER-WORLDS-G/H/I/J. Static address inventory from factory `0x00ea488e`, its allocation constructors and',
             'the pinned second-section vtables. Class IDs use the first registered world; labels are descriptive,',
             'not recovered symbol names. The default BaseMap registration for world 146 is outside the 48 concrete classes.', '',
             '`V` = compiled native C has an instruction-compared family, within the scope recorded in JSON.',
             '`S` = authored static-only C. `M` = native method missing, even when its address is known.',
             'A V does not mean every state, subtype, nested effect or visual host is complete.',
             'Counts below concern the three primary class methods only; inherited no-ops remain M until compared.', '',
             '| Class | Worlds, decimal | Vtable | Create +2c | Move +30 | Visual +34 |',
             '|---|---|---|---|---|---|']
    counts = dict(verified_family=0, static_only=0, missing=0)
    classes = 0
    for row in rows:
        cells = []
        active = False
        for name in ('create', 'move', 'visual'):
            handler = row['handlers'][name]
            status = handler['status']
            counts[status] += 1
            active |= status == 'verified_family'
            cells.append(f"`{handler['entry']}` {'V' if status == 'verified_family' else 'S' if status == 'static_only' else 'M'}")
        classes += active
        lines.append('| ' + ' | '.join([row['label'], ', '.join(map(str, row['worlds'])), '`'+row['vtable']+'`'] + cells) + ' |')
    lines += ['', f"{classes}/48 classes have at least one verified primary method. Of 144 primary methods: "
              f"{counts['verified_family']} verified families, {counts['static_only']} static-only C, {counts['missing']} missing.", '',
              'The companion [JSON](world-handler-coverage.json) records factory, constructor and related entry points',
              'for all 48 classes: invisible-sector move +1c, custom render +38 and after render +3c, with separate statuses.', '',
              '## Built-in worlds and hooks', '',
              'These are not extra factory classes and do not count toward 48 or 144. Their verified scope is in',
              '[world fidelity](client-world-fidelity.md), the object-render finding and the named lane handoffs.', '',
              '| Worlds | Create | Move | Visual and related |',
              '|---|---|---|---|',
              '| 0 Lorencia | 016d8538, verified | 017ff238, verified | 017f9758, bounded verified particle cases |',
              '| 1 Dungeon | 016d8e3a switch, verified | 017ff238 switch, verified | 017fc8e0, bounded verified |',
              '| 2 Devias | 016d8538 switch, verified | 017fffda, B verified | 017f9bdc bounded verified; placements D/B |',
              '| 3 Noria | 016d8538 switch, verified | 017ff238 switch, verified | 017f9dd1 bounded verified; placement D |',
              '| 4 Lost Tower | generic only | 017ff238 switch, verified | K verifies 017f6ca7 push helper and 017fa92b sprite producers |',
              '| 7 Atlans | 016d8538 switch, verified | 017ff238 switch, verified | K verifies default switch landing 017fcb5c; no dedicated Atlans visual case |',
              '| 8 Tarkan | 016d8538 switch, verified | 01800bf8, B verified | F haze; K verifies 017fb2a4 lamp/plume producers; EFFECTS-003 consumers |',
              '| 10 Icarus | generic only | 0180249e bounded verified | C/C2 sky/cover/ribbons/dragons; K verifies type-10 Bone01 flare producer; EFFECTS-003 consumer |',
              '| 33, 54 Aida | generic only | 00d6202f bounded verified | E source/reset-history attribution; capture history missing |',
              '| 37, 40 Kanturu | 00e74a58 bounded verified | 00e74ae0 bounded verified | A bounded flames/after-character verified |',
              '| 51 Elbeland | 00e30a02 bounded verified | 00e30b86, B verified | E boid movement/clouds verified; captured speeds missing |', '',
              '## Reproduce and limits', '',
              '`tools/python/bin/python scripts/world_handler_coverage.py` checks all factory registrations, constructors,',
              'vtables and 288 slot addresses against the pinned text/data. `--write-markdown` regenerates this view.',
              'No bytes, decoded tables, captures or assets are exported. Implementation annotations require source review.',
              'The fourteen-view tour has worlds 0/1/2/3/4/7/8/10/33/37/51/57/80. Other factory classes need',
              'DATA-ACQ-002 object/clock/pool captures for visual checks. Synthetic instruction cases do not supply those images.', '']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write-markdown', action='store_true')
    args = ap.parse_args()
    document = json.loads(TABLE.read_text())
    import pins
    actual = inventory(pins.TEXT.read(), pins.DATA.read())
    assert len(actual) == len(document['classes']) == 48
    for found, row in zip(actual, document['classes']):
        for key in ('worlds', 'factory', 'constructor', 'vtable'):
            assert found[key] == row[key], (row['class_id'], key)
        for name, address in found['handlers'].items():
            assert address == row['handlers'][name]['entry'], (row['class_id'], name)
    rendered = markdown(document)
    output = TABLE.with_suffix('.md')
    if args.write_markdown:
        output.write_text(rendered)
    else:
        assert output.read_text() == rendered, 'stale markdown'
    print('48 classes, 57 world registrations, 288 slot addresses checked')
    print(next(line for line in rendered.splitlines() if '/48 classes have' in line))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
