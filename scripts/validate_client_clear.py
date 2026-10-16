#!/usr/bin/env python3
"""Compare the clear64 wrapper and both captured helper paths to authored C."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import sys

TEXT_BASE = 0x401000
TEXT_BYTES = 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
TARGET_SHA256 = '3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a'
CLEAR_ADDRESS = 0x401020
HELPER_PAGE = 0x194c000
FEATURE_ADDRESS = 0x1cf6618


def validate(capture, library):
    payload = Path(capture).read_bytes()
    if len(payload) != TEXT_BYTES or hashlib.sha256(payload).hexdigest() != TEXT_SHA256:
        raise ValueError('Capture does not match the pinned restored client text')
    import unicorn
    from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE,
                         UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE)
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
                                  UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EFLAGS,
                                  UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP)

    native = ctypes.CDLL(str(Path(library).resolve()))
    clear = native.mu_clear64
    clear.argtypes = [ctypes.c_void_p]
    clear.restype = ctypes.c_void_p
    arena_base, stack_base, return_address = 0x700000, 0x600000, 0x500000
    initial_stack = stack_base + 0x800
    preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_EBP: 0x23456789,
                 UC_X86_REG_ESI: 0x3456789a, UC_X86_REG_EDI: 0x456789ab}
    generator = random.Random(CLEAR_ADDRESS)
    patterns = (bytes((0xff,)) * 512, bytes(range(256)) * 2,
                bytes(generator.randrange(256) for _ in range(512)))
    failures, unexpected, executed = [], [], set()
    count = 0
    for pattern in patterns:
        for offset in range(128, 192):
            for feature in (0, 2):
                for direction_flag in (0, 1):
                    count += 1
                    initial = pattern + bytes((0xa5,)) * (4096 - len(pattern))
                    host = (ctypes.c_ubyte * 4096).from_buffer_copy(initial)
                    pointer = ctypes.addressof(host) + offset
                    returned = clear(pointer)
                    machine = Uc(UC_ARCH_X86, UC_MODE_32)
                    for address in (TEXT_BASE, HELPER_PAGE, FEATURE_ADDRESS & ~4095,
                                    arena_base, stack_base, return_address):
                        machine.mem_map(address, 4096)
                    machine.mem_write(TEXT_BASE, payload[:4096])
                    machine.mem_write(HELPER_PAGE, payload[HELPER_PAGE-TEXT_BASE:HELPER_PAGE-TEXT_BASE+4096])
                    machine.mem_write(FEATURE_ADDRESS, feature.to_bytes(4, 'little'))
                    machine.mem_write(arena_base, initial)
                    machine.mem_write(initial_stack, return_address.to_bytes(4, 'little'))
                    for register, value in preserved.items():
                        machine.reg_write(register, value)
                    machine.reg_write(UC_X86_REG_EAX, 0xdeadbeef)
                    machine.reg_write(UC_X86_REG_ECX, arena_base + offset)
                    machine.reg_write(UC_X86_REG_ESP, initial_stack)
                    machine.reg_write(UC_X86_REG_EFLAGS, 2 | (direction_flag << 10))

                    def observe_code(uc, address, size, context):
                        executed.add(address)

                    def observe_memory(uc, access, address, size, value, context):
                        in_stack = stack_base <= address and address + size <= stack_base + 4096
                        in_destination = arena_base + offset <= address and address + size <= arena_base + offset + 64
                        feature_read = access != UC_MEM_WRITE and FEATURE_ADDRESS <= address and address + size <= FEATURE_ADDRESS + 4
                        if not (in_stack or in_destination or feature_read):
                            unexpected.append({'case': count, 'access': access, 'address': hex(address), 'bytes': size})

                    machine.hook_add(UC_HOOK_CODE, observe_code)
                    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe_memory)
                    machine.emu_start(CLEAR_ADDRESS, return_address, timeout=1000000, count=256)
                    checks = {
                        'memory': bytes(host) == bytes(machine.mem_read(arena_base, 4096)),
                        'native_return': returned == pointer,
                        'x86_return': machine.reg_read(UC_X86_REG_EAX) == arena_base + offset,
                        'returned_to_caller': machine.reg_read(UC_X86_REG_EIP) == return_address,
                        'stack_cleanup': machine.reg_read(UC_X86_REG_ESP) == initial_stack + 4,
                        'callee_saved': all(machine.reg_read(reg) == value for reg, value in preserved.items()),
                        'direction_flag_preserved': (machine.reg_read(UC_X86_REG_EFLAGS) >> 10) & 1 == direction_flag,
                    }
                    if not all(checks.values()):
                        failures.append({'case': count, 'offset': offset, 'feature_word': feature,
                                         'direction_flag': direction_flag, 'checks': checks})
    branches = [hex(address) for address in (0x194cdc7, 0x194ce05) if address in executed]
    if len(branches) != 2 or unexpected:
        failures.append({'branch_or_memory_coverage': False})
    return {'target_sha256': TARGET_SHA256, 'capture_sha256': TEXT_SHA256,
            'function_address': hex(CLEAR_ADDRESS), 'function_bytes': 14,
            'function_sha256': hashlib.sha256(payload[32:46]).hexdigest(),
            'helper_range': ['0x194cd00', '0x194ce59'],
            'helper_sha256': hashlib.sha256(payload[0x194cd00-TEXT_BASE:0x194ce5a-TEXT_BASE]).hexdigest(),
            'unicorn': unicorn.__version__, 'cases': count, 'mismatches': len(failures),
            'failures': failures, 'feature_branch_entries': branches,
            'synthetic_feature_values': [0, 2], 'actual_feature_word_known': False,
            'unexpected_memory_accesses': unexpected,
            'executed_instruction_addresses': [hex(address) for address in sorted(executed)],
            'scope': 'Valid flat memory, 64 cacheline alignments, three patterns, both feature-bit branches and both DF states; no native Windows or real-game invocation claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = validate(args.capture, args.library)
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    return 1 if result['mismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
