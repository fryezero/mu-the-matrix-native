#!/usr/bin/env python3
"""Compare authored LEA key setup with pinned captured client instructions.

No game bytes are included. Supply the restored private text locally.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
TEXT_BASE = 0x401000
TEXT_BYTES = pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
TARGET_SHA256 = pins.TARGET.sha256
FUNCTION = 0x92a430
FUNCTION_BYTES = 6446
FUNCTION_SHA256 = '027959c97d01690e622312ae0c16e269a7b95cb30d3af160486349219a28b0da'
CONTEXT_BYTES = 772


def synthetic_cases():
    generator = random.Random(FUNCTION)
    keys = [bytes(32), b'\xff'*32, b'\x55\xaa'*16, bytes(range(32)), bytes(reversed(range(32)))]
    keys.extend(bytes(generator.randrange(256) for _ in range(32)) for _ in range(8))
    for key in keys:
        for size in (16, 24, 32):
            for context_alignment in range(4):
                for key_alignment in range(4):
                    for direction in (0, 1):
                        yield key, size, 512+context_alignment, 4096+key_alignment, direction
    for size in (-2147483648, -1, 0, 15, 16, 17, 23, 24, 25, 31, 32, 33, 2147483647):
        for direction in (0, 1):
            # None is NULL; -1 maps to intentionally unmapped pointer 1.
            yield b'', size, None, -1, direction
            yield b'', size, -1, None, direction
            if size not in (16, 24, 32):
                yield b'', size, -1, -1, direction


def validate(text, library):
    payload = pins.load(text, TEXT_BYTES, TEXT_SHA256, mismatch=ValueError('Input does not match the pinned restored text'))
    function = payload[FUNCTION-TEXT_BASE:FUNCTION-TEXT_BASE+FUNCTION_BYTES]
    if hashlib.sha256(function).hexdigest() != FUNCTION_SHA256:
        raise ValueError('Pinned setup body mismatch')
    import unicorn
    from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ,
                         UC_HOOK_MEM_WRITE, UC_MEM_WRITE, UC_PROT_READ, UC_PROT_WRITE,
                         UC_PROT_EXEC)
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
                                  UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                                  UC_X86_REG_EFLAGS, UC_X86_REG_EIP, UC_X86_REG_ESI,
                                  UC_X86_REG_ESP)
    library = Path(library).resolve(strict=True)
    native = ctypes.CDLL(str(library)).mu_client_lea_setup
    native.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
    native.restype = None
    arena, stack, returned_to = 0x30000000, 0x31000000, 0x32000000
    initial_stack = stack+0x800
    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    code_page = FUNCTION & ~4095
    machine.mem_map(code_page, 8192, UC_PROT_READ | UC_PROT_EXEC)
    machine.mem_write(FUNCTION, function)
    machine.mem_map(arena, 8192, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(stack, 4096, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(returned_to, 4096, UC_PROT_READ | UC_PROT_EXEC)
    preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_EBP: 0x23456789,
                 UC_X86_REG_ESI: 0x3456789a, UC_X86_REG_EDI: 0x456789ab}
    failures = []
    context_address = key_address = size = 0
    active = False
    reads, writes, access_failures, execution_failures = [], [], [], []
    branch_counts = {16: 0, 24: 0, 32: 0}
    wrong_count = case_count = 0
    case_counts = {'16': 0, '24': 0, '32': 0, 'noop': 0}

    def memory_hook(uc, access, address, count, value, ignored):
        if initial_stack-8 <= address and address+count <= initial_stack+16:
            return
        if (active and access != UC_MEM_WRITE and key_address <= address and
                address+count <= key_address+size):
            reads.append((address-key_address, count))
        elif (active and access == UC_MEM_WRITE and context_address <= address and
              address+count <= context_address+CONTEXT_BYTES):
            writes.append((address-context_address, count))
        elif len(access_failures) < 8:
            access_failures.append((access, hex(address), count))

    def code_hook(uc, address, count, ignored):
        if not FUNCTION <= address < FUNCTION+FUNCTION_BYTES:
            if len(execution_failures) < 8:
                execution_failures.append(hex(address))
        if address in (0x92b75e, 0x92ae8c, 0x92a468):
            branch_counts[{0x92b75e: 16, 0x92ae8c: 24, 0x92a468: 32}[address]] += 1

    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, memory_hook)
    machine.hook_add(UC_HOOK_CODE, code_hook)

    def pointer(base, offset):
        return 0 if offset is None else 1 if offset == -1 else base+offset

    for key, size, context_offset, key_offset, direction in synthetic_cases():
        case_count += 1
        active = context_offset is not None and context_offset >= 0 and key_offset is not None and key_offset >= 0
        case_counts[str(size) if active else 'noop'] += 1
        initial = bytearray(bytes(range(256))*32)
        if active:
            initial[key_offset:key_offset+size] = key[:size]
        host = (ctypes.c_ubyte*8192).from_buffer_copy(initial)
        native(pointer(ctypes.addressof(host), context_offset),
               pointer(ctypes.addressof(host), key_offset), size)
        machine.mem_write(arena, bytes(initial))
        machine.mem_write(stack, b'\xa5'*4096)
        context_address, key_address = pointer(arena, context_offset), pointer(arena, key_offset)
        machine.mem_write(initial_stack, struct.pack('<IIII', returned_to, context_address,
                                                     key_address, size & 0xffffffff))
        for register, value in preserved.items():
            machine.reg_write(register, value)
        for register in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX):
            machine.reg_write(register, 0xdeadbeef)
        machine.reg_write(UC_X86_REG_ESP, initial_stack)
        machine.reg_write(UC_X86_REG_EFLAGS, 2 | (direction << 10))
        reads.clear()
        writes.clear()
        access_failures.clear()
        execution_failures.clear()
        machine.emu_start(FUNCTION, returned_to, timeout=10000000, count=3000)
        actual = bytes(machine.mem_read(arena, 8192))
        rounds = size//2+16 if active else 0
        expected_reads = [(offset, 4) for offset in range(0, size, 4)] if active else []
        expected_writes = [(offset, 4) for offset in range(0, 24*rounds, 4)] + [(768, 4)] if active else []
        # Every key word is read once; context stores can be reordered in a
        # compact implementation because the declared spans are disjoint.
        checks = {
            'full_arena': bytes(host) == actual,
            'returned_to_caller': machine.reg_read(UC_X86_REG_EIP) == returned_to,
            'stack_cleanup': machine.reg_read(UC_X86_REG_ESP) == initial_stack+4,
            'callee_saved': all(machine.reg_read(reg) == value for reg, value in preserved.items()),
            'direction_flag': (machine.reg_read(UC_X86_REG_EFLAGS) >> 10) & 1 == direction,
            'bounded_accesses': not access_failures,
            'exact_word_reads': sorted(reads) == expected_reads,
            'exact_word_writes': sorted(writes) == expected_writes,
            'bounded_execution': not execution_failures,
        }
        if active:
            end = context_offset+24*rounds
            checks['unused_context_tail'] = actual[end:context_offset+768] == initial[end:context_offset+768]
            checks['round_count'] = struct.unpack_from('<I', actual, context_offset+768)[0] == rounds
            # Negative control: the same keys in reversed round order are a
            # plausible decrypt-context convention, but not this setup ABI.
            wrong = bytearray(bytes(host))
            blocks = [wrong[start:start+24] for start in range(context_offset, end, 24)]
            wrong[context_offset:end] = b''.join(reversed(blocks))
            wrong_count += int(wrong != actual)
        if not all(checks.values()):
            failures.append({'case': case_count, 'key_bytes': size, 'context_offset': context_offset,
                             'key_offset': key_offset, 'direction_flag': direction, 'checks': checks,
                             'unexpected_accesses': list(access_failures),
                             'unexpected_execution': list(execution_failures)})
    if any(branch_counts[key] != case_counts[str(key)] for key in (16, 24, 32)):
        failures.append({'branch_coverage': branch_counts, 'cases': case_counts})
    return {'target_sha256': TARGET_SHA256, 'text_sha256': TEXT_SHA256,
            'function_address': hex(FUNCTION), 'function_bytes': FUNCTION_BYTES,
            'function_sha256': FUNCTION_SHA256, 'unicorn': unicorn.__version__,
            'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
            'instruction_cases': case_count, 'case_counts': case_counts,
            'supported_key_bytes': [16, 24, 32], 'branch_entries': branch_counts,
            'wrong_schedule_mismatches': wrong_count, 'mismatches': len(failures), 'failures': failures,
            'scope': 'Synthetic disjoint accessible key/context spans, all word alignments, both DF states, null and unsupported no-ops. No key/context alias or whole-decoder/gameplay equivalence.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec'/
                        ('libmodelcodec.dylib' if sys.platform == 'darwin' else 'libmodelcodec.so'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.library)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    return int(bool(result['mismatches']))


if __name__ == '__main__':
    sys.exit(main())
