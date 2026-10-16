#!/usr/bin/env python3
"""Re-check every MODEL-HIERARCHY-001 instruction claim against pinned bytes.

Inputs are the restored first section (text) and second image section (data)
named in docs/research/model-hierarchy.md.  Each check decodes a bounded range
from an asserted boundary and compares exact Capstone text at exact addresses.
The report states which checks passed; it never contains original bytes.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_hierarchy_common as common  # noqa: E402

READER = 0x012b3812
READER_END = 0x012b4485
PLAIN_READER = 0x012b2e81
PLAIN_READER_END = 0x012b3812
POSE = 0x012b5064
POSE_END = 0x012b58ce
REST_POSE = 0x012bcffb
REST_POSE_END = 0x012bd35a
INIT = 0x012b2df3
INIT_END = 0x012b2e81
POST_LOAD = 0x012b47fd
POST_LOAD_END = 0x012b4dd3
CONCAT = 0x00cff83e
CONCAT_END = 0x00cfff3c
BONE_BUFFER = 0x06fce398
HEAP_SLOT = 0x01a7c5c8

EXPECTED_CALL_CANDIDATES = {'reader': 3, 'plain_reader': 0, 'pose': 314, 'rest_pose': 1}
EXPECTED_BUFFER_CANDIDATES = 300
EXPECTED_HEAP_SLOT = '0x7bc275e0'

# (start, end, {address: exact text}) -- decoded linearly from `start`.
INSTRUCTION_CLAIMS = {
    'reader_bone_allocation': (0x012b3c73, 0x012b3c9f, {
        0x012b3c79: 'mov ecx, 0x8c',
        0x012b3c7e: 'mul ecx',
        0x012b3c87: 'call 0x191bab9',
        0x012b3c9c: 'mov dword ptr [eax + 0x2c], ecx',
    }),
    'reader_bone_loop': (0x012b4225, 0x012b4441, {
        0x012b4235: 'movsx eax, word ptr [eax + 0x22]',
        0x012b4239: 'cmp dword ptr [ebp - 0x24], eax',
        0x012b4242: 'imul eax, dword ptr [ebp - 0x24], 0x8c',
        0x012b424c: 'add eax, dword ptr [ecx + 0x2c]',
        0x012b425b: 'mov al, byte ptr [eax]',
        0x012b425d: 'mov byte ptr [ecx + 0x22], al',
        0x012b4263: 'inc eax',
        0x012b426a: 'movsx eax, byte ptr [eax + 0x22]',
        0x012b426e: 'test eax, eax',
        0x012b4270: 'jne 0x12b443c',
        0x012b4276: 'push 0x20',
        0x012b4282: 'call 0x194c200',
        0x012b428d: 'add eax, 0x20',
        0x012b429c: 'mov ax, word ptr [eax]',
        0x012b429f: 'mov word ptr [ecx + 0x20], ax',
        0x012b42a6: 'inc eax',
        0x012b42a7: 'inc eax',
        0x012b42ae: 'movsx eax, word ptr [eax + 0x26]',
        0x012b42be: 'call 0x191bab9',
        0x012b42d3: 'mov dword ptr [eax + 0x24], ecx',
        0x012b430c: 'movsx eax, word ptr [ecx + eax + 8]',
        0x012b43cf: 'call 0x194c200',
        0x012b43f0: 'call 0x194c200',
        0x012b442e: 'call 0xd00724',
        0x012b443c: 'jmp 0x12b422b',
    }),
    'reader_epilogue': (0x012b4441, 0x012b4485, {
        0x012b4456: 'push 0',
        0x012b445b: 'call 0x12b2df3',
        0x012b4482: 'ret 0xc',
    }),
    'plain_reader_bone_loop': (0x012b35c7, 0x012b37e3, {
        0x012b35d7: 'movsx eax, word ptr [eax + 0x22]',
        0x012b35e4: 'imul eax, dword ptr [ebp - 0x24], 0x8c',
        0x012b35ee: 'add eax, dword ptr [ecx + 0x2c]',
        0x012b35ff: 'mov byte ptr [ecx + 0x22], al',
        0x012b360c: 'movsx eax, byte ptr [eax + 0x22]',
        0x012b3612: 'jne 0x12b37de',
        0x012b3641: 'mov word ptr [ecx + 0x20], ax',
        0x012b3675: 'mov dword ptr [eax + 0x24], ecx',
        0x012b37de: 'jmp 0x12b35cd',
    }),
    'init_name_rule': (INIT, INIT_END, {
        0x012b2dfc: 'movzx eax, byte ptr [ebp + 8]',
        0x012b2e02: 'je 0x12b2e63',
        0x012b2e3a: 'cmp eax, 0x44',
        0x012b2e4c: 'cmp eax, 0x75',
        0x012b2e54: 'mov byte ptr [eax + 0x22], 1',
        0x012b2e5d: 'mov byte ptr [eax + 0x22], 0',
        0x012b2e7e: 'ret 4',
    }),
    'pose_dummy_skip_and_parent': (POSE, POSE_END, {
        0x012b51f7: 'movsx eax, word ptr [eax + 0x22]',
        0x012b5204: 'imul eax, dword ptr [ebp - 8], 0x8c',
        0x012b5217: 'movsx eax, byte ptr [eax + 0x22]',
        0x012b521b: 'test eax, eax',
        0x012b521d: 'je 0x12b5221',
        0x012b521f: 'jmp 0x12b51ed',
        0x012b522b: 'add eax, dword ptr [ecx + 0x24]',
        0x012b5786: 'movsx eax, word ptr [eax + 0x20]',
        0x012b578a: 'cmp eax, -1',
        0x012b578d: 'jne 0x12b589f',
        0x012b5881: 'imul eax, dword ptr [ebp - 8], 0x30',
        0x012b5885: 'add eax, dword ptr [ebp + 8]',
        0x012b5890: 'push 0x78965ac',
        0x012b5895: 'call 0xcff83e',
        0x012b589f: 'imul eax, dword ptr [ebp - 8], 0x30',
        0x012b58a3: 'add eax, dword ptr [ebp + 8]',
        0x012b58b1: 'movsx eax, word ptr [eax + 0x20]',
        0x012b58b5: 'imul eax, eax, 0x30',
        0x012b58b8: 'add eax, dword ptr [ebp + 8]',
        0x012b58bc: 'call 0xcff83e',
        0x012b58c4: 'jmp 0x12b51ed',
        0x012b58cb: 'ret 0x20',
    }),
    'rest_pose_dummy_skip_and_parent': (REST_POSE, REST_POSE_END, {
        0x012bd022: 'imul eax, dword ptr [ebp - 4], 0x8c',
        0x012bd035: 'movsx eax, byte ptr [eax + 0x22]',
        0x012bd03b: 'je 0x12bd03f',
        0x012bd03d: 'jmp 0x12bd00b',
        0x012bd2a8: 'movsx eax, word ptr [eax + 0x20]',
        0x012bd2ac: 'cmp eax, -1',
        0x012bd2af: 'jne 0x12bd32e',
        0x012bd33d: 'movsx eax, word ptr [eax + 0x20]',
        0x012bd341: 'imul eax, eax, 0x30',
        0x012bd344: 'add eax, dword ptr [ebp + 8]',
        0x012bd348: 'call 0xcff83e',
        0x012bd357: 'ret 0x10',
    }),
    'post_load_bone_flag': (0x012b49b3, 0x012b4a01, {
        0x012b49c3: 'movsx eax, word ptr [eax + 0x22]',
        0x012b49d0: 'imul eax, dword ptr [ebp - 4], 0x8c',
        0x012b49da: 'add eax, dword ptr [ecx + 0x2c]',
        0x012b49e3: 'movsx eax, word ptr [eax*2 + 0x75a9d58]',
        0x012b49f2: 'mov byte ptr [eax + 0x28], 1',
        0x012b49fb: 'mov byte ptr [eax + 0x28], 0',
    }),
    'allocator_chain': (0x0191bab9, 0x0191bac2, {
        0x0191babd: 'jmp 0x191ba7b',
    }),
    'operator_new_loop': (0x0191ba7b, 0x0191ba9c, {
        0x0191ba90: 'call 0x1983110',
        0x0191ba83: 'call 0x199c4c0',
    }),
    'malloc_thunk': (0x01983110, 0x0198311b, {
        0x01983116: 'jmp 0x19a4da0',
    }),
    'malloc_heap_call': (0x019a4da0, 0x019a4df1, {
        0x019a4dcc: 'push esi',
        0x019a4dcd: 'push 0',
        0x019a4dcf: 'push dword ptr [0xbdcfc10]',
        0x019a4dd5: 'call dword ptr [0x1a7c5c8]',
    }),
}

# Whole-body decodes that must land exactly on the end with the stated count.
BODY_CLAIMS = {
    'reader': (READER, READER_END, 989),
    'plain_reader': (PLAIN_READER, PLAIN_READER_END, 815),
    'pose': (POSE, POSE_END, 704),
    'rest_pose': (REST_POSE, REST_POSE_END, 317),
    'concat': (CONCAT, CONCAT_END, 726),
    'post_load': (POST_LOAD, POST_LOAD_END, 485),
}


def capstone_version():
    import capstone
    return capstone.__version__


def check_instructions(region, start, end, expected, engine=None):
    instructions, stop = common.decode_range(region, start, end, engine)
    seen = {i.address: common.text_of(i) for i in instructions}
    mismatches = {}
    for address, text in expected.items():
        if seen.get(address) != text:
            mismatches[hex(address)] = {'expected': text, 'found': seen.get(address)}
    return {'range': [hex(start), hex(end)], 'instructions': len(instructions),
            'stopped_early_at': hex(stop) if stop else None,
            'checked': len(expected), 'mismatches': mismatches,
            'ok': stop is None and not mismatches}


def check_body(region, start, end, count, engine=None):
    instructions, stop = common.decode_range(region, start, end, engine)
    return {'range': [hex(start), hex(end)], 'instructions': len(instructions),
            'expected_instructions': count, 'stopped_early_at': hex(stop) if stop else None,
            'ok': stop is None and len(instructions) == count}


def argument_uses(region, start, end, engine=None):
    """Count `[ebp + 8]`, `[ebp + 0xc]`, `[ebp + 0x10]` operand uses in a body."""
    instructions, _ = common.decode_range(region, start, end, engine)
    counts = {}
    for instruction in instructions:
        for slot in re.findall(r'\[ebp \+ (0x[0-9a-f]+|\d+)\]', instruction.op_str):
            counts[slot] = counts.get(slot, 0) + 1
    return counts


def bone_field_stores(region, start, end, engine=None):
    """Byte/word stores at small displacements; reports which offsets are written."""
    instructions, _ = common.decode_range(region, start, end, engine)
    offsets = {}
    for instruction in instructions:
        if not instruction.mnemonic.startswith('mov'):
            continue
        match = re.match(r'(byte|word) ptr \[\w+ \+ (0x[0-9a-f]+)\],', instruction.op_str)
        if match and not instruction.op_str.startswith(('byte ptr [ebp', 'word ptr [ebp')):
            key = f'{match.group(1)}+{match.group(2)}'
            offsets[key] = offsets.get(key, 0) + 1
    return offsets


def concat_output_stores(region, engine=None):
    """Stores through a pointer formed from the third argument of 0xcff83e."""
    instructions, _ = common.decode_range(region, CONCAT, CONCAT_END, engine)
    stores = 0
    for index, instruction in enumerate(instructions):
        if common.text_of(instruction) == 'add eax, dword ptr [ebp + 0x10]':
            following = instructions[index + 1:index + 6]
            if any(i.mnemonic == 'movss' and i.op_str.startswith('dword ptr [eax')
                   for i in following):
                stores += 1
    return stores


def direct_call_candidates(region, target, engine=None):
    """Unanchored E8 matches, not verified instruction boundaries or callers."""
    engine = engine or common.decoder()
    sites = []
    data = region.data
    for match in re.finditer(rb'\xe8', data):
        offset = match.start()
        if offset + 5 > len(data):
            break
        relative = struct.unpack_from('<i', data, offset + 1)[0]
        if (region.base + offset + 5 + relative) & 0xffffffff != target:
            continue
        decoded = next(engine.disasm(data[offset:offset + 5], region.base + offset), None)
        if decoded is not None and decoded.size == 5:
            sites.append(region.base + offset)
    return sites


def push_buffer_call_candidates(region, immediate, target, window=0x60, max_steps=13, engine=None):
    """Raw PUSH candidates followed by a matching call in a straight-line run.

    Entry alignment and argument provenance are not established. The lookahead
    must not cross another control transfer before its first call.
    """
    from capstone import (CS_GRP_BRANCH_RELATIVE, CS_GRP_CALL, CS_GRP_INT,
                          CS_GRP_IRET, CS_GRP_JUMP, CS_GRP_RET)
    from capstone.x86_const import X86_INS_HLT, X86_INS_UD2
    engine = engine or common.decoder()
    needle = b'\x68' + struct.pack('<I', immediate)
    found = []
    for match in re.finditer(re.escape(needle), region.data):
        va = region.base + match.start()
        length = min(window, region.end - va)
        for step, instruction in enumerate(engine.disasm(region.read(va, length), va)):
            if step == 0 and instruction.size != 5:
                break
            if instruction.group(CS_GRP_CALL):
                if instruction.op_str == hex(target):
                    found.append(va)
                break
            if (any(instruction.group(group) for group in
                    (CS_GRP_BRANCH_RELATIVE, CS_GRP_INT, CS_GRP_IRET, CS_GRP_JUMP, CS_GRP_RET)) or
                    instruction.id in (X86_INS_HLT, X86_INS_UD2)):
                break
            if step >= max_steps:
                break
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True, help='new JSON report path')
    args = parser.parse_args(argv)
    output = Path(args.output)
    if output.exists():
        parser.error('refusing to overwrite an existing report')
    text = common.load_text(args.text)
    data = common.load_data(args.data)
    engine = common.decoder()
    report = {'report_format': 'mu-model-hierarchy-checks-v2',
              'call_search_confidence': 'Raw candidates; instruction boundaries, reachability and argument provenance are unverified.',
              'target_sha256': common.TARGET_SHA256, 'text_sha256': common.TEXT_SHA256,
              'data_sha256': common.DATA_SHA256, 'capstone': capstone_version(),
              'bodies': {}, 'instructions': {}}
    for name, (start, end, count) in BODY_CLAIMS.items():
        report['bodies'][name] = check_body(text, start, end, count, engine)
    for name, (start, end, expected) in INSTRUCTION_CLAIMS.items():
        report['instructions'][name] = check_instructions(text, start, end, expected, engine)
    report['pose_argument_uses'] = argument_uses(text, POSE, POSE_END, engine)
    report['rest_pose_argument_uses'] = argument_uses(text, REST_POSE, REST_POSE_END, engine)
    report['concat_argument_uses'] = argument_uses(text, CONCAT, CONCAT_END, engine)
    report['post_load_bone_field_stores'] = bone_field_stores(text, POST_LOAD, POST_LOAD_END, engine)
    report['concat_output_stores'] = concat_output_stores(text, engine)
    callers = {name: [hex(x) for x in direct_call_candidates(text, target, engine)]
               for name, target in (('reader', READER), ('plain_reader', PLAIN_READER),
                                    ('pose', POSE), ('rest_pose', REST_POSE))}
    report['direct_call_candidates'] = {k: {'count': len(v), 'sites': v if len(v) <= 16 else v[:16]}
                                for k, v in callers.items()}
    pushed = push_buffer_call_candidates(text, BONE_BUFFER, POSE, engine=engine)
    report['pose_push_candidates_for_buffer_0x6fce398'] = len(pushed)
    report['heap_slot_runtime_value'] = hex(struct.unpack('<I', data.read(HEAP_SLOT, 4))[0])
    checks = [v['ok'] for v in report['bodies'].values()]
    checks += [v['ok'] for v in report['instructions'].values()]
    checks.append(report['pose_argument_uses'].get('8') == 3)
    checks.append(report['concat_output_stores'] == 12)
    checks.append(set(report['post_load_bone_field_stores']) == {'byte+0x28'})
    checks.append({k: v['count'] for k, v in report['direct_call_candidates'].items()} == EXPECTED_CALL_CANDIDATES)
    checks.append(report['pose_push_candidates_for_buffer_0x6fce398'] == EXPECTED_BUFFER_CANDIDATES)
    checks.append(report['heap_slot_runtime_value'] == EXPECTED_HEAP_SLOT)
    report['all_ok'] = all(checks)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('all_ok', 'pose_argument_uses', 'concat_output_stores',
                                              'concat_argument_uses', 'pose_push_candidates_for_buffer_0x6fce398',
                                              'heap_slot_runtime_value')}, indent=1))
    print({k: v['count'] for k, v in report['direct_call_candidates'].items()})
    for group in ('bodies', 'instructions'):
        for name, result in report[group].items():
            if not result['ok']:
                print('FAILED', group, name, result)
    return 0 if report['all_ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
