#!/usr/bin/env python3
"""Compare the client-linked v12 rolling decoder to pinned captured x86.

Raw inputs and detailed output remain private. Synthetic cases use no game data.
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
FUNCTION = 0x98c5f2
FUNCTION_BYTES = 194
MANIFEST_SHA256 = pins.V14_MANIFEST.sha256


def synthetic_cases():
    generator = random.Random(FUNCTION)
    patterns = (bytes(range(256))*32, bytes((0x55, 0xaa))*4096,
                bytes(generator.randrange(256) for _ in range(8192)))
    for data in patterns:
        for length in (1, 2, 3, 7, 15, 16, 17, 31, 32, 33, 127, 256, 257, 1024):
            for alignment in range(4):
                source = 2048+alignment
                for displacement in (-1024, -65, -17, -1, 0, 1, 15, 16, 17, 65, 1024, 4096):
                    for direction in (0, 1):
                        yield data, source, source+displacement, length, direction
    for length in (-2147483648, -1, 0, 1, 2147483647):
        for direction in (0, 1):
            yield patterns[0], None, None, length, direction
    for length in (-2147483648, -1, 0):
        for direction in (0, 1):
            yield patterns[0], None, 128, length, direction


def installed_inputs(game_root, manifest):
    raw_manifest = Path(manifest).read_bytes()
    if hashlib.sha256(raw_manifest).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Model manifest does not match the pinned private corpus')
    records = [record for record in json.loads(raw_manifest)['files'] if record.get('version') == 12]
    if len(records) != 180:
        raise ValueError('Expected exactly 180 pinned v12 inputs')
    root = Path(game_root).resolve(strict=True)
    inputs = []
    identities = set()
    for record in records:
        path = (root/record['path']).resolve(strict=True)
        if root not in path.parents:
            raise ValueError('Model source escaped the supplied installation')
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        attributes = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if (attributes(before) != attributes(after) or len(raw) != record['source_bytes'] or
                hashlib.sha256(raw).hexdigest() != record['source_sha256']):
            raise ValueError('Model source identity or digest changed: '+record['path'])
        identity = (before.st_dev, before.st_ino)
        if identity in identities:
            raise ValueError('Duplicate model file identity')
        identities.add(identity)
        if raw[:4] != b'BMD\x0c' or struct.unpack_from('<I', raw, 4)[0] != len(raw)-8:
            raise ValueError('Unexpected pinned v12 envelope')
        inputs.append((record['path'], raw[8:]))
    return inputs


def validate(text, library, game_root=None, manifest=None):
    payload = pins.load(text, TEXT_BYTES, TEXT_SHA256, mismatch=ValueError('Input does not match the pinned restored text'))
    inputs = installed_inputs(game_root, manifest) if game_root is not None else []
    # Import only after identities so portable refusal tests require no emulator.
    import unicorn
    from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ,
                         UC_HOOK_MEM_WRITE, UC_MEM_WRITE, UC_PROT_READ, UC_PROT_WRITE,
                         UC_PROT_EXEC)
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
                                  UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                                  UC_X86_REG_EFLAGS, UC_X86_REG_EIP, UC_X86_REG_ESI,
                                  UC_X86_REG_ESP)

    library = Path(library).resolve(strict=True)
    library_sha256 = hashlib.sha256(library.read_bytes()).hexdigest()
    native = ctypes.CDLL(str(library)).mu_bmd12_decode
    native.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
    native.restype = ctypes.c_int32
    arena, stack, returned_to = 0x700000, 0x600000, 0x500000
    initial_stack = stack+0x800
    code_page = FUNCTION & ~4095
    function = payload[FUNCTION-TEXT_BASE:FUNCTION-TEXT_BASE+FUNCTION_BYTES]
    preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_EBP: 0x23456789,
                 UC_X86_REG_ESI: 0x3456789a, UC_X86_REG_EDI: 0x456789ab}
    failures, unexpected = [], []
    branch_counts = {'query': 0, 'nonquery': 0}
    case_count = 0

    def compare(initial, source, destination, length, direction, label):
        nonlocal case_count
        case_count += 1
        host = (ctypes.c_ubyte*len(initial)).from_buffer_copy(initial)
        pointer = ctypes.addressof(host)
        source_pointer = 1 if source is None else pointer+source
        target_pointer = None if destination is None else pointer+destination
        native_return = native(target_pointer, source_pointer, length)
        machine = Uc(UC_ARCH_X86, UC_MODE_32)
        machine.mem_map(code_page, 4096, UC_PROT_READ | UC_PROT_EXEC)
        machine.mem_write(FUNCTION, function)
        machine.mem_map(arena, len(initial), UC_PROT_READ | UC_PROT_WRITE)
        machine.mem_write(arena, initial)
        machine.mem_map(stack, 4096, UC_PROT_READ | UC_PROT_WRITE)
        machine.mem_map(returned_to, 4096, UC_PROT_READ | UC_PROT_EXEC)
        source_address = 1 if source is None else arena+source
        target_address = 0 if destination is None else arena+destination
        machine.mem_write(initial_stack, struct.pack('<IIII', returned_to, target_address,
                                                     source_address, length & 0xffffffff))
        for register, value in preserved.items():
            machine.reg_write(register, value)
        machine.reg_write(UC_X86_REG_EAX, 0xdeadbeef)
        machine.reg_write(UC_X86_REG_ECX, 0x98765432)
        machine.reg_write(UC_X86_REG_EDX, 0xabcdef01)
        machine.reg_write(UC_X86_REG_ESP, initial_stack)
        machine.reg_write(UC_X86_REG_EFLAGS, 2 | (direction << 10))
        accesses = {'read': 0, 'write': 0}
        access_failures = []
        active = destination is not None and length > 0

        def observe_memory(uc, access, address, size, value, context):
            in_stack = initial_stack-32 <= address and address+size <= initial_stack+16
            if in_stack:
                return
            if (active and access != UC_MEM_WRITE and source_address <= address and
                    address+size <= source_address+length):
                accesses['read'] += 1
            elif (active and access == UC_MEM_WRITE and target_address <= address and
                  address+size <= target_address+length):
                accesses['write'] += 1
            elif len(access_failures) < 8:
                access_failures.append({'access': access, 'address': hex(address), 'bytes': size})

        def query_branch(uc, address, size, context):
            branch_counts['query'] += 1

        def nonquery_branch(uc, address, size, context):
            branch_counts['nonquery'] += 1

        machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe_memory)
        machine.hook_add(UC_HOOK_CODE, query_branch, begin=0x98c5fe, end=0x98c5fe)
        machine.hook_add(UC_HOOK_CODE, nonquery_branch, begin=0x98c606, end=0x98c606)
        machine.emu_start(FUNCTION, returned_to, timeout=30000000,
                          count=max(256, length*64+128) if active else 256)
        checks = {
            'memory': bytes(host) == bytes(machine.mem_read(arena, len(initial))),
            'native_return': native_return == length,
            'x86_return': machine.reg_read(UC_X86_REG_EAX) == length & 0xffffffff,
            'returned_to_caller': machine.reg_read(UC_X86_REG_EIP) == returned_to,
            'stack_cleanup': machine.reg_read(UC_X86_REG_ESP) == initial_stack+4,
            'callee_saved': all(machine.reg_read(reg) == value for reg, value in preserved.items()),
            'direction_flag': (machine.reg_read(UC_X86_REG_EFLAGS) >> 10) & 1 == direction,
            'bounded_accesses': not access_failures,
            'exact_access_counts': accesses == {'read': 2*length, 'write': length} if active
                                   else accesses == {'read': 0, 'write': 0},
        }
        if not all(checks.values()):
            failures.append({'case': case_count, 'label': label, 'source_offset': source,
                             'destination_offset': destination, 'length': length,
                             'direction_flag': direction, 'checks': checks})
        if access_failures:
            unexpected.append({'case': case_count, 'accesses': access_failures})
        return bytes(host[destination:destination+length]) if active else b''

    for case in synthetic_cases():
        compare(*case, label='synthetic')
    synthetic_count = case_count
    corpus = {'files': len(inputs), 'payload_bytes': 0, 'native_python_matches': 0,
              'captured_x86_matches': 0}
    if inputs:
        sys.path.insert(0, str(ROOT/'model-recovery'))
        from bmd_encrypted import decrypt_map
        for path, cipher in inputs:
            length = len(cipher)
            destination = 384+length
            size = (destination+length+128+4095) & ~4095
            initial = bytearray(b'\xa5'*size)
            initial[128:128+length] = cipher
            before_failures = len(failures)
            output = compare(bytes(initial), 128, destination, length, 0, path)
            matches_python = output == decrypt_map(cipher)
            corpus['native_python_matches'] += int(matches_python)
            corpus['captured_x86_matches'] += int(len(failures) == before_failures)
            corpus['payload_bytes'] += length
            if not matches_python:
                failures.append({'case': case_count, 'label': path, 'native_python': False})
    if branch_counts['query'] != 10 or branch_counts['nonquery'] != case_count-10:
        failures.append({'branch_coverage': branch_counts})
    return {'target_sha256': TARGET_SHA256, 'text_sha256': TEXT_SHA256,
            'function_address': hex(FUNCTION), 'function_bytes': FUNCTION_BYTES,
            'function_sha256': hashlib.sha256(function).hexdigest(), 'unicorn': unicorn.__version__,
            'authored_library_sha256': library_sha256,
            'synthetic_instruction_cases': synthetic_count, 'installed_v12': corpus,
            'private_corpus_manifest_sha256': MANIFEST_SHA256 if inputs else None,
            'branch_entries': branch_counts, 'mismatches': len(failures), 'failures': failures,
            'unexpected_accesses': unexpected,
            'scope': 'Finite accessible flat spans, signed lengths, both DF states, disjoint and overlapping buffers; no code/stack aliasing or native Windows/gameplay claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec'/
                        ('libmodelcodec.dylib' if sys.platform == 'darwin' else 'libmodelcodec.so'))
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--manifest', type=Path, default=pins.V14_MANIFEST.default())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.library, args.game_root, args.manifest)
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
