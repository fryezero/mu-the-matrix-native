#!/usr/bin/env python3
"""Compare authored copy64 source to the pinned private x86 capture."""
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


def synthetic_cases():
    generator = random.Random(TEXT_BASE)
    patterns = (bytes(range(256)) * 2, bytes((0x55, 0xaa)) * 256,
                bytes(generator.randrange(256) for _ in range(512)))
    for index, data in enumerate(patterns):
        source = 128 + index
        for destination in range(source - 64, source + 65):
            yield data, source, destination
    for index in range(6):
        yield patterns[index % 3], 1 + index, 400 + index


def validate(capture, library):
    payload = Path(capture).read_bytes()
    if len(payload) != TEXT_BYTES or hashlib.sha256(payload).hexdigest() != TEXT_SHA256:
        raise ValueError('Capture does not match the pinned restored client text')
    # Kept optional so source-only tests need no emulator installation or game.
    import unicorn
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
                                  UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                                  UC_X86_REG_EFLAGS, UC_X86_REG_EIP, UC_X86_REG_ESI,
                                  UC_X86_REG_ESP)

    native = ctypes.CDLL(str(Path(library).resolve()))
    copy = native.mu_copy64_forward_words
    copy.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    copy.restype = ctypes.c_void_p
    arena_base, stack_base, return_address = 0x700000, 0x600000, 0x500000
    initial_stack = stack_base + 0x800
    preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_EBP: 0x23456789,
                 UC_X86_REG_ESI: 0x3456789a, UC_X86_REG_EDI: 0x456789ab}
    failures = []
    count = 0
    for count, (data, source, destination) in enumerate(synthetic_cases(), 1):
        initial = data + bytes((0xa5,)) * (4096 - len(data))
        host = (ctypes.c_ubyte * 4096).from_buffer_copy(initial)
        pointer = ctypes.addressof(host)
        returned = copy(pointer + destination, pointer + source)
        machine = Uc(UC_ARCH_X86, UC_MODE_32)
        for address in (TEXT_BASE, arena_base, stack_base, return_address):
            machine.mem_map(address, 4096)
        machine.mem_write(TEXT_BASE, payload[:4096])
        machine.mem_write(arena_base, initial)
        machine.mem_write(initial_stack, return_address.to_bytes(4, 'little') +
                          (arena_base + source).to_bytes(4, 'little'))
        for register, value in preserved.items():
            machine.reg_write(register, value)
        machine.reg_write(UC_X86_REG_EAX, 0xdeadbeef)
        machine.reg_write(UC_X86_REG_EDX, 0xabcdef01)
        machine.reg_write(UC_X86_REG_ECX, arena_base + destination)
        machine.reg_write(UC_X86_REG_ESP, initial_stack)
        machine.reg_write(UC_X86_REG_EFLAGS, 2)  # DF clear, flat memory, valid spans.
        machine.emu_start(TEXT_BASE, return_address, timeout=1000000, count=128)
        checks = {
            'memory': bytes(host) == bytes(machine.mem_read(arena_base, 4096)),
            'native_return': returned == pointer + destination,
            'x86_return': machine.reg_read(UC_X86_REG_EAX) == arena_base + destination,
            'returned_to_caller': machine.reg_read(UC_X86_REG_EIP) == return_address,
            'stack_cleanup': machine.reg_read(UC_X86_REG_ESP) == initial_stack + 8,
            'callee_saved': all(machine.reg_read(reg) == value for reg, value in preserved.items()),
        }
        if not all(checks.values()):
            failures.append({'case': count, 'source_offset': source,
                             'destination_offset': destination, 'checks': checks})
    return {'target_sha256': TARGET_SHA256, 'capture_sha256': TEXT_SHA256,
            'capture_bytes': len(payload), 'function_address': hex(TEXT_BASE),
            'function_bytes': 22, 'function_sha256': hashlib.sha256(payload[:22]).hexdigest(),
            'unicorn': unicorn.__version__, 'cases': count, 'mismatches': len(failures),
            'failures': failures,
            'scope': 'Valid accessible flat-memory spans; DF clear; no faults or concurrent access.',
            'coverage': 'Both overlap directions, offsets -64..64, three alignments/patterns, six disjoint unaligned cases; full arena, pointer return and x86 ABI checks.'}


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
