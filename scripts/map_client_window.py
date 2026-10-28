#!/usr/bin/env python3
"""Map bounded decoded control flow; candidate entries are not recovered symbols."""
import argparse
from collections import deque
import errno
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pins  # noqa: E402

from capstone import (Cs, CS_ARCH_X86, CS_MODE_32, CS_GRP_CALL, CS_GRP_JUMP,
                      CS_GRP_RET, CS_GRP_INT, CS_GRP_IRET, CS_GRP_BRANCH_RELATIVE)
from capstone.x86_const import (X86_OP_IMM, X86_OP_MEM, X86_INS_LEA,
                                X86_INS_JMP, X86_INS_LJMP, X86_INS_HLT, X86_INS_UD2)

MAX_WINDOW = 262144
TEXT_BASE = pins.TEXT.base
TEXT_BYTES = pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
TARGET_SHA256 = pins.TARGET.sha256


def map_window(data, base, seeds, max_functions=1024, max_instructions=4096, discover_padding=True):
    if not 0 < len(data) <= MAX_WINDOW or base < 0 or base + len(data) > 2**32:
        raise ValueError('Select a nonempty bounded x86-32 window')
    if not 1 <= max_functions <= 4096 or not 1 <= max_instructions <= 65536:
        raise ValueError('Function/instruction budgets must be positive and bounded')
    limit = base + len(data)
    seeds = set(seeds)
    if not seeds or any(not base <= entry < limit for entry in seeds):
        raise ValueError('Explicit seeds must lie inside the selected window')
    origins = {entry: {'explicit_seed'} for entry in seeds}
    if discover_padding:
        for offset in range(2, len(data)):
            if ((base + offset) % 16 == 0 and data[offset-2:offset] == b'\xcc\xcc'
                    and data[offset] not in (0, 0xcc)):
                origins.setdefault(base + offset, set()).add('aligned_padding_candidate')
    pending = deque(sorted(origins))
    queued = set(origins)
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    candidates = []
    byte_owners, conflicts = {}, {}

    def transfer(instruction):
        operands = instruction.operands
        if len(operands) != 1:
            return {'site': hex(instruction.address), 'kind': 'unresolved_operand_form', 'target': None}
        if operands[0].type != X86_OP_IMM:
            return {'site': hex(instruction.address), 'kind': 'indirect', 'target': None}
        target = operands[0].imm & 0xffffffff
        return {'site': hex(instruction.address),
                'kind': 'direct_local' if base <= target < limit else 'direct_outside_window',
                'target': hex(target)}

    while pending and len(candidates) < max_functions:
        entry = pending.popleft()
        blocks = deque([entry])
        decoded, occupied = {}, set()
        calls, branches, issues, boundaries, memory_operands = [], [], [], [], []
        budget_reached = False
        while blocks and not budget_reached:
            address = blocks.popleft()
            while True:
                if address in decoded:
                    break
                if address in occupied:
                    issues.append({'kind': 'overlapping_decode_path', 'address': hex(address)})
                    break
                if not base <= address < limit:
                    issues.append({'kind': 'window_exit', 'address': hex(address)})
                    break
                if address != entry and address in origins:
                    boundaries.append({'kind': 'other_candidate_entry', 'address': hex(address)})
                    break
                if len(decoded) >= max_instructions:
                    issues.append({'kind': 'instruction_budget', 'address': hex(address)})
                    budget_reached = True
                    break
                instruction = next(decoder.disasm(data[address-base:address-base+15], address, count=1), None)
                if instruction is None:
                    issues.append({'kind': 'invalid_or_truncated_instruction', 'address': hex(address)})
                    break
                extent = set(range(address, address + instruction.size))
                if extent & occupied:
                    issues.append({'kind': 'overlapping_decode_path', 'address': hex(address)})
                    break
                occupied.update(extent)
                decoded[address] = instruction.size
                for byte in sorted(extent):
                    previous = byte_owners.setdefault(byte, (entry, address))
                    if previous[1] != address:
                        conflicts.setdefault((previous[1], address),
                            {'first_entry': hex(previous[0]), 'first_instruction': hex(previous[1]),
                             'other_entry': hex(entry), 'other_instruction': hex(address)})
                following = address + instruction.size
                for operand in instruction.operands:
                    if operand.type == X86_OP_MEM and operand.mem.base == 0 and operand.mem.index == 0:
                        segment = decoder.reg_name(operand.mem.segment) if operand.mem.segment else None
                        kind = 'absolute_address_expression' if instruction.id == X86_INS_LEA else 'absolute_memory_operand'
                        memory_operands.append({'site': hex(address), 'target': hex(operand.mem.disp & 0xffffffff),
                                                'bytes': operand.size, 'segment': segment,
                                                'kind': 'segmented_offset' if segment else kind})
                if instruction.group(CS_GRP_CALL):
                    edge = transfer(instruction)
                    calls.append(edge)
                    if edge['kind'] == 'direct_local':
                        target = int(edge['target'], 16)
                        origins.setdefault(target, set()).add('decoded_call_target')
                        if target not in queued:
                            pending.append(target)
                            queued.add(target)
                if (instruction.group(CS_GRP_JUMP) or
                        (instruction.group(CS_GRP_BRANCH_RELATIVE) and not instruction.group(CS_GRP_CALL))):
                    edge = transfer(instruction)
                    branches.append(edge)
                    if edge['kind'] == 'direct_local':
                        blocks.append(int(edge['target'], 16))
                    if instruction.id in (X86_INS_JMP, X86_INS_LJMP):
                        break
                if instruction.group(CS_GRP_RET) or instruction.group(CS_GRP_IRET):
                    break
                if instruction.group(CS_GRP_INT) or instruction.id in (X86_INS_HLT, X86_INS_UD2):
                    issues.append({'kind': 'trap_terminator', 'address': hex(address)})
                    break
                address = following
        candidates.append({'entry': hex(entry), 'decoded_instructions': len(decoded),
                           'decoded_bytes': len(occupied), 'calls': calls, 'branches': branches,
                           'issues': issues, 'boundaries': boundaries, 'memory_operands': memory_operands})
    for candidate in candidates:
        candidate['origins'] = sorted(origins[int(candidate['entry'], 16)])
    candidates.sort(key=lambda item: int(item['entry'], 16))
    return {'format': 'mu-client-window-map-v1', 'base': hex(base), 'bytes': len(data),
            'window_sha256': hashlib.sha256(data).hexdigest(),
            'explicit_seeds': [hex(entry) for entry in sorted(seeds)],
            'padding_discovery': discover_padding,
            'budgets': {'functions': max_functions, 'instructions_per_candidate': max_instructions},
            'candidates': candidates, 'unprocessed_entries': [hex(entry) for entry in sorted(pending)],
            'cross_candidate_decode_conflicts': [conflicts[key] for key in sorted(conflicts)],
            'limitations': ['Heuristic candidates and decoded references, not original symbols or validated function boundaries.',
                            'Only the selected window is decoded; outside and indirect targets remain unresolved.',
                            'Calls are followed by possible fallthrough; no-return behavior is not established.',
                            'Candidate boundaries stop traversal and may omit shared tails or miss valid code.',
                            'No runtime execution, type recovery, behavior equivalence or complete client coverage is implied.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--offset', type=lambda value: int(value, 0), default=0)
    parser.add_argument('--length', type=lambda value: int(value, 0), default=65536)
    parser.add_argument('--seed', type=lambda value: int(value, 0), action='append')
    parser.add_argument('--max-functions', type=int, default=1024)
    parser.add_argument('--max-instructions', type=int, default=4096)
    parser.add_argument('--no-padding', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = pins.load(args.capture, TEXT_BYTES, TEXT_SHA256)
    except pins.PinMissing:
        # Keep the native missing-file exception exposed by this CLI before migration.
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(args.capture)) from None
    except pins.PinMismatch:
        parser.error('Capture does not match the pinned restored client text')
    if args.offset < 0 or not 0 < args.length <= MAX_WINDOW or args.offset + args.length > len(payload):
        parser.error('Selected window is outside the pinned capture or exceeds the window bound')
    base = TEXT_BASE + args.offset
    try:
        result = map_window(payload[args.offset:args.offset+args.length], base, args.seed or [base],
                            args.max_functions, args.max_instructions, not args.no_padding)
    except ValueError as error:
        parser.error(str(error))
    import capstone
    result.update(target_sha256=TARGET_SHA256, capture_sha256=TEXT_SHA256, capstone=capstone.__version__)
    with args.output.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({'candidates': len(result['candidates']), 'unprocessed': len(result['unprocessed_entries']),
                      'window_sha256': result['window_sha256']}))


if __name__ == '__main__':
    main()
