#!/usr/bin/env python3
"""Pin LEA decoder bodies, check relocation and compare scalar captured code.

AVX batches require the separate full-x86 guest comparator. This script never
substitutes scalar algorithms for unsupported AVX instructions.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE = 0x401000
TEXT_BYTES = 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
BODIES = {
    0x927060: (4677, 'ccc0ee915849c68077c607526892a398731c53f81635c9ac780c401f6aa26239'),
    0x929370: (4288, '6fa51533865332b415f88ecde322aea8e9778f7dbcfbe116a7112b70d8f747ce'),
    0x92be30: (198, 'a45a3d2a04babe7b627edd1473e63893dbc592eb4f3292387e9528e427b4dc37'),
    0x93bb20: (1798, 'f37b056688cef339f0f1e857fb421d2e04ad3062a3ba3162fc23d80ba02e26a1'),
}
ENTRY = 0x92be30


def check_relocation(payload):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_GRP_CALL, CS_GRP_JUMP
    from capstone.x86 import X86_OP_MEM, X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    report = []
    for address, (count, digest) in BODIES.items():
        body = payload[address-TEXT_BASE:address-TEXT_BASE+count]
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError('Selected decoder body digest mismatch')
        instructions = list(decoder.disasm(body, address))
        if sum(item.size for item in instructions) != count or instructions[-1].mnemonic != 'ret':
            raise ValueError('Incomplete selected instruction stream')
        boundaries = {item.address for item in instructions}
        calls = []
        for instruction in instructions:
            for operand in instruction.operands:
                if operand.type == X86_OP_MEM and (operand.mem.segment or
                        not (operand.mem.base or operand.mem.index)):
                    raise ValueError('Absolute or segmented memory operand prevents relocation')
            if instruction.group(CS_GRP_CALL) or instruction.group(CS_GRP_JUMP):
                operand = instruction.operands[0]
                if operand.type != X86_OP_IMM:
                    raise ValueError('Indirect control transfer prevents bounded relocation')
                if instruction.group(CS_GRP_CALL):
                    if address != ENTRY or operand.imm not in (0x927060, 0x929370, 0x93bb20):
                        raise ValueError('Unexpected helper call')
                    calls.append(hex(operand.imm))
                elif operand.imm not in boundaries:
                    raise ValueError('Branch target outside decoded body boundaries')
        report.append({'address': hex(address), 'bytes': count, 'sha256': digest,
                       'instructions': len(instructions), 'calls': calls,
                       'absolute_or_segmented_memory_operands': 0})
    return report


def check_model_key_link(payload):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_MEM, X86_OP_IMM, X86_REG_EBP
    sys.path.insert(0, str(ROOT/'model-recovery'))
    from bmd_encrypted import FORMAT_KEY
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    instructions = list(decoder.disasm(payload[0x12b3812-TEXT_BASE:0x12b4485-TEXT_BASE], 0x12b3812))
    key = {}
    for item in instructions:
        if 0x12b3a4a <= item.address <= 0x12b3ac6 and item.mnemonic == 'mov':
            destination, value = item.operands
            if (destination.type == X86_OP_MEM and destination.size == 1 and
                    destination.mem.base == X86_REG_EBP and not destination.mem.index and
                    value.type == X86_OP_IMM):
                key[destination.mem.disp] = value.imm
    if sorted(key) != list(range(-0x64, -0x44)) or bytes(key[index] for index in sorted(key)) != FORMAT_KEY:
        raise ValueError('BMD caller key does not match public format constant')
    selected = [(item.mnemonic, item.op_str) for item in instructions if 0x12b3aca <= item.address <= 0x12b3adc]
    if selected != [('push', '0x20'), ('lea', 'eax, [ebp - 0x64]'), ('push', 'eax'),
                    ('lea', 'eax, [ebp - 0x470]'), ('push', 'eax'),
                    ('call', '0x91a6c0'), ('add', 'esp, 0xc')]:
        raise ValueError('BMD key setup argument path changed')
    return {'setup_call_instruction': '0x012b3ad7', 'key_bytes': 32,
            'public_format_constant_matches': True, 'caller_cleanup_bytes': 12,
            'live_model_invocation_observed': False}


def validate(text, library):
    payload = Path(text).read_bytes()
    if len(payload) != TEXT_BYTES or hashlib.sha256(payload).hexdigest() != TEXT_SHA256:
        raise ValueError('Input does not match the pinned restored text')
    relocation = check_relocation(payload)
    caller = check_model_key_link(payload)
    import unicorn
    from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                         UC_MEM_WRITE, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC)
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
                                  UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                                  UC_X86_REG_EFLAGS, UC_X86_REG_EIP, UC_X86_REG_ESI,
                                  UC_X86_REG_ESP)
    library = Path(library).resolve(strict=True)
    handle = ctypes.CDLL(str(library))
    setup, native = handle.mu_client_lea_setup, handle.mu_client_lea_decode
    setup.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
    setup.restype = None
    native.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    native.restype = None
    arena, stack, returned_to = 0x30000000, 0x31000000, 0x32000000
    initial_stack = stack+0x800
    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    machine.mem_map(TEXT_BASE, len(payload), UC_PROT_READ | UC_PROT_EXEC)
    machine.mem_write(TEXT_BASE, payload)
    machine.mem_map(arena, 16384, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(stack, 4096, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(returned_to, 4096, UC_PROT_READ | UC_PROT_EXEC)
    preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_EBP: 0x23456789,
                 UC_X86_REG_ESI: 0x3456789a, UC_X86_REG_EDI: 0x456789ab}
    failures, accesses = [], []
    context = 12288
    source = target = length = rounds = 0
    cases = 0

    def observe(uc, access, address, count, value, ignored):
        if initial_stack-128 <= address and address+count <= initial_stack+20:
            return
        if access == UC_MEM_WRITE:
            valid = arena+target <= address and address+count <= arena+target+length
        else:
            valid = (arena+source <= address and address+count <= arena+source+length or
                     arena+context <= address and address+count <= arena+context+24*rounds or
                     arena+context+768 <= address and address+count <= arena+context+772)
        if not valid and len(accesses) < 8:
            accesses.append((access, hex(address), count))
    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe)
    for pattern in (bytes(32), bytes(range(32))):
        for key_size in (16, 24, 32):
            context_buffer = ctypes.create_string_buffer(b'\xa5'*772, 772)
            setup(context_buffer, ctypes.create_string_buffer(pattern), key_size)
            rounds = key_size//2+16
            for length in (16, 32, 48):
                for alignment in range(4):
                    for displacement in (-65, -17, -1, 0, 1, 15, 16, 2048):
                        source = 2048+alignment
                        target = source+displacement
                        for direction in (0, 1):
                            cases += 1
                            initial = bytearray(bytes(range(256))*64)
                            initial[context:context+772] = context_buffer.raw
                            host = (ctypes.c_ubyte*16384).from_buffer_copy(initial)
                            pointer = ctypes.addressof(host)
                            native(pointer+target, pointer+source, length, pointer+context)
                            machine.mem_write(arena, bytes(initial))
                            machine.mem_write(stack, b'\xa5'*4096)
                            machine.mem_write(initial_stack, struct.pack('<IIIII', returned_to,
                                arena+target, arena+source, length, arena+context))
                            for register, value in preserved.items(): machine.reg_write(register, value)
                            for register in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX):
                                machine.reg_write(register, 0xdeadbeef)
                            machine.reg_write(UC_X86_REG_ESP, initial_stack)
                            machine.reg_write(UC_X86_REG_EFLAGS, 2 | (direction << 10))
                            accesses.clear()
                            machine.emu_start(ENTRY, returned_to, timeout=10000000, count=4000)
                            checks = {
                                'full_arena': bytes(host) == bytes(machine.mem_read(arena, 16384)),
                                'returned': machine.reg_read(UC_X86_REG_EIP) == returned_to,
                                'stack': machine.reg_read(UC_X86_REG_ESP) == initial_stack+4,
                                'saved_registers': all(machine.reg_read(r) == v for r,v in preserved.items()),
                                'direction_flag': (machine.reg_read(UC_X86_REG_EFLAGS) >> 10) & 1 == direction,
                                'bounded_accesses': not accesses,
                            }
                            if not all(checks.values()):
                                failures.append({'case': cases, 'checks': checks, 'accesses': list(accesses)})
    return {'text_sha256': TEXT_SHA256, 'relocation_checks': relocation, 'model_key_link': caller,
            'scalar_instruction_cases': cases, 'unicorn': unicorn.__version__,
            'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
            'mismatches': len(failures), 'failures': failures,
            'avx_helpers_executed': False,
            'scope': 'Actual wrapper and scalar helper only, lengths16/32/48, accessible overlapping data and disjoint setup context; AVX batch comparison is a separate guest run.'}


def compare_corpus(library, game_root, manifest, diagnostics):
    manifest_raw, diagnostics_raw = Path(manifest).read_bytes(), Path(diagnostics).read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != 'fffcbad941e9bad394489382e79ad6d9d2e9f405847975de0eff113babd366ff':
        raise ValueError('Private corpus manifest identity mismatch')
    if hashlib.sha256(diagnostics_raw).hexdigest() != 'ba945b166c52e068a4ed12bbbc67a27f68d697fcf64197aaff627b09e45b909a':
        raise ValueError('Private rejected-model diagnostics identity mismatch')
    records = [record for record in json.loads(manifest_raw)['files'] if record.get('version') == 15]
    rejected = {record['path']: record for record in json.loads(diagnostics_raw)['files']}
    if len(records) != 11583 or len(rejected) != 17:
        raise ValueError('Unexpected pinned v15 corpus counts')
    root = Path(game_root).resolve(strict=True)
    sys.path.insert(0, str(ROOT/'model-recovery'))
    from bmd_encrypted import FORMAT_KEY, decrypt_lea, native_reader
    if native_reader() is None:
        raise ValueError('Build the independent native reader with make -C model-recovery first')
    handle = ctypes.CDLL(str(Path(library).resolve(strict=True)))
    setup, decode = handle.mu_client_lea_setup, handle.mu_client_lea_decode
    setup.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
    setup.restype = None
    decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    decode.restype = None
    context = ctypes.create_string_buffer(772)
    setup(context, ctypes.create_string_buffer(FORMAT_KEY), 32)
    identities, failures = set(), []
    total = matches = 0
    for record in records:
        identity_record = record if 'source_sha256' in record else rejected[record['path']]
        path = (root/record['path']).resolve(strict=True)
        if root not in path.parents:
            raise ValueError('Model path escaped the supplied installation')
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        attrs = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
        if (attrs(before) != attrs(after) or len(raw) != identity_record['source_bytes'] or
                hashlib.sha256(raw).hexdigest() != identity_record['source_sha256']):
            raise ValueError('Pinned model identity changed: '+record['path'])
        identity = before.st_dev, before.st_ino
        if identity in identities:
            raise ValueError('Duplicate model file identity')
        identities.add(identity)
        if (raw[:4] != b'BMD\x0f' or struct.unpack_from('<I', raw, 4)[0] != len(raw)-8 or
                (len(raw)-8) % 16):
            raise ValueError('Unexpected pinned v15 envelope')
        cipher = raw[8:]
        source = ctypes.create_string_buffer(cipher)
        output = ctypes.create_string_buffer(len(cipher))
        decode(output, source, len(cipher), context)
        match = output.raw == decrypt_lea(cipher)
        matches += int(match)
        total += len(cipher)
        if not match: failures.append(record['path'])
    return {'files': len(records), 'payload_bytes': total, 'native_reader_matches': matches,
            'mismatches': len(failures), 'failures': failures,
            'original_instructions_executed_for_corpus': False,
            'structural_rejections_unchanged': 17}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec'/
                        ('libmodelcodec.dylib' if sys.platform == 'darwin' else 'libmodelcodec.so'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--manifest', type=Path, default=ROOT/'model-recovery/verified-v14/manifest.json')
    parser.add_argument('--diagnostics', type=Path, default=ROOT/'evidence/model-edge/diagnostics.json')
    args = parser.parse_args()
    try:
        result = validate(args.text, args.library)
        if args.game_root is not None:
            result['installed_v15'] = compare_corpus(args.library, args.game_root, args.manifest, args.diagnostics)
            result['mismatches'] += result['installed_v15']['mismatches']
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output: output.write(encoded)
    else:
        print(encoded, end='')
    return int(bool(result['mismatches']))


if __name__ == '__main__':
    sys.exit(main())
