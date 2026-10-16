#!/usr/bin/env python3
"""Compare sequential pose composition under controlled binary32 RNE state."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE = 0x401000
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
FUNCTION = 0xcff83e
FUNCTION_BYTES = 1790
FUNCTION_SHA256 = 'c358cd6e89029b912c7297f31c049c8383a5aa85bf6400ee77c6e033c01bcb7c'


def validate(text, library):
    payload = Path(text).read_bytes()
    if len(payload) != 23572480 or hashlib.sha256(payload).hexdigest() != TEXT_SHA256:
        raise ValueError('Input does not match pinned restored text')
    function = payload[FUNCTION-TEXT_BASE:FUNCTION-TEXT_BASE+FUNCTION_BYTES]
    if hashlib.sha256(function).hexdigest() != FUNCTION_SHA256:
        raise ValueError('Pinned pose helper body mismatch')
    import unicorn
    from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                         UC_MEM_WRITE, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC)
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP,
                                  UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                                  UC_X86_REG_EFLAGS, UC_X86_REG_EIP, UC_X86_REG_ESI,
                                  UC_X86_REG_ESP, UC_X86_REG_MXCSR, UC_X86_REG_XMM0, UC_X86_REG_XMM1)
    library = Path(library).resolve(strict=True)
    handle = ctypes.CDLL(str(library))
    environment = handle.mu_record_math_environment_supported
    environment.restype = ctypes.c_int
    if environment() != 1:
        raise ValueError('Host requires binary32/binary64 storage and RNE environment')
    native = handle.mu_pose_concat
    native.argtypes, native.restype = [ctypes.c_void_p]*3, None
    arena, stack, returned_to = 0x30000000, 0x31000000, 0x32000000
    initial_stack = stack+0x800
    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    machine.mem_map(FUNCTION & ~4095, 8192, UC_PROT_READ | UC_PROT_EXEC)
    machine.mem_write(FUNCTION, function)
    machine.mem_map(arena, 8192, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(stack, 4096, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(returned_to, 4096, UC_PROT_READ | UC_PROT_EXEC)
    preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_EBP: 0x23456789,
                 UC_X86_REG_ESI: 0x3456789a, UC_X86_REG_EDI: 0x456789ab}
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_MEM, X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    instructions = list(decoder.disasm(function, FUNCTION))
    source_calls = []
    for start, end, expected in ((0x12b5064, 0x12b58cf, (0x12b5895, 0x12b58bc)),
                                  (0x12bcffb, 0x12bd35b, (0x12bd348,))):
        caller = list(decoder.disasm(payload[start-TEXT_BASE:end-TEXT_BASE], start))
        selected = [item for item in caller if item.address in expected]
        if (len(selected) != len(expected) or any(item.mnemonic != 'call' or
                item.operands[0].type != X86_OP_IMM or item.operands[0].imm != FUNCTION for item in selected)):
            raise ValueError('Selected hierarchy call link changed')
        source_calls.extend(hex(item.address) for item in selected)
    registers = {'eax': UC_X86_REG_EAX, 'ecx': UC_X86_REG_ECX,
                 'edx': UC_X86_REG_EDX, 'esi': UC_X86_REG_ESI,
                 'xmm0': UC_X86_REG_XMM0, 'xmm1': UC_X86_REG_XMM1}
    arithmetic = {item.address: item for item in instructions if item.mnemonic in ('mulss', 'addss')}
    after_arithmetic = {item.address+item.size: registers[item.reg_name(item.operands[0].reg)]
                        for item in arithmetic.values()}
    product_nonzero = {}
    bad_intermediate = False

    def observe_arithmetic(uc, address, count, ignored):
        nonlocal bad_intermediate
        if address in after_arithmetic:
            bits = uc.reg_read(after_arithmetic[address]) & 0xffffffff
            exponent, fraction = bits & 0x7f800000, bits & 0x7fffff
            if exponent == 0x7f800000 or (exponent == 0 and fraction):
                bad_intermediate = True
            if bits & 0x7fffffff == 0 and product_nonzero.get(address, False):
                bad_intermediate = True
        instruction = arithmetic.get(address)
        if instruction is not None and instruction.mnemonic == 'mulss':
            left = uc.reg_read(registers[instruction.reg_name(instruction.operands[0].reg)]) & 0xffffffff
            operand = instruction.operands[1]
            if operand.type != X86_OP_MEM:
                raise ValueError('Unexpected original product operand')
            memory = operand.mem
            location = memory.disp
            if memory.base: location += uc.reg_read(registers[instruction.reg_name(memory.base)])
            if memory.index: location += memory.scale*uc.reg_read(registers[instruction.reg_name(memory.index)])
            right = struct.unpack('<I', bytes(uc.mem_read(location, 4)))[0]
            product_nonzero[address+instruction.size] = bool(left & 0x7fffffff and right & 0x7fffffff)
    machine.hook_add(UC_HOOK_CODE, observe_arithmetic)
    a = b = output = 0
    reads = 0
    writes, accesses = [], []

    def observe(uc, access, address, count, value, ignored):
        nonlocal reads
        if initial_stack-12 <= address and address+count <= initial_stack+16:
            return
        if access == UC_MEM_WRITE:
            valid = arena+output <= address and address+count <= arena+output+48
            if valid: writes.append((address-arena-output, count))
        else:
            valid = (arena+a <= address and address+count <= arena+a+48 or
                     arena+b <= address and address+count <= arena+b+48)
            if valid: reads += 1
        if not valid and len(accesses) < 8:
            accesses.append((access, hex(address), count))
    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe)
    generator = random.Random(FUNCTION)
    patterns = [[0.0]*12, [1.0]*12, [-1.0]*12,
                [float(index-6)/4 for index in range(12)],
                [2**24,1,-2**24,0, 1,0,0,1, 0,1,0,0]]
    patterns.extend([generator.choice((-2.,-1.,-.5,.25,.5,1.,2.)) for _ in range(12)] for _ in range(8))
    cases = attempted = outside_domain = negative = 0
    failures = []
    for values in patterns:
        repeated = struct.pack('<12f', *values)*171
        for alignment in range(4):
            initial = b'\xa5'*alignment+repeated[:8192-alignment]
            for gap in (0, 4, 16, 48, 128):
                a, b = 2048+alignment, 2048+alignment+gap
                for displacement in (-128, -48, -16, -4, 0, 4, 16, 48, 128, 256):
                    output = a+displacement
                    for direction in (0, 1):
                        attempted += 1
                        host = (ctypes.c_ubyte*8192).from_buffer_copy(initial)
                        pointer = ctypes.addressof(host)
                        native(pointer+a, pointer+b, pointer+output)
                        machine.mem_write(arena, initial)
                        machine.mem_write(stack, b'\xa5'*4096)
                        machine.mem_write(initial_stack, struct.pack('<IIII', returned_to, arena+a, arena+b, arena+output))
                        for register, value in preserved.items(): machine.reg_write(register, value)
                        for register in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX):
                            machine.reg_write(register, 0xdeadbeef)
                        machine.reg_write(UC_X86_REG_ESP, initial_stack)
                        machine.reg_write(UC_X86_REG_EFLAGS, 2 | (direction << 10))
                        machine.reg_write(UC_X86_REG_MXCSR, 0x1f80)
                        bad_intermediate = False
                        product_nonzero.clear()
                        reads = 0
                        writes.clear()
                        accesses.clear()
                        machine.emu_start(FUNCTION, returned_to, timeout=10000000, count=800)
                        mxcsr = machine.reg_read(UC_X86_REG_MXCSR)
                        # Invalid, denormal-input, divide, overflow or underflow
                        # status puts this case outside the supported FP domain.
                        if bad_intermediate or mxcsr & 0x1f:
                            outside_domain += 1
                            continue
                        cases += 1
                        actual = bytes(machine.mem_read(arena, 8192))
                        checks = {'full_arena': bytes(host) == actual,
                                  'returned': machine.reg_read(UC_X86_REG_EIP) == returned_to,
                                  'stack': machine.reg_read(UC_X86_REG_ESP) == initial_stack+4,
                                  'callee_saved': all(machine.reg_read(r) == v for r,v in preserved.items()),
                                  'direction_flag': (machine.reg_read(UC_X86_REG_EFLAGS) >> 10) & 1 == direction,
                                  'mxcsr_control': mxcsr & ~0x3f == 0x1f80,
                                  'bounded_accesses': not accesses,
                                  'data_reads': reads == 75,
                                  'field_stores': writes == [(offset,4) for offset in range(0,48,4)]}
                        if not all(checks.values()):
                            failures.append({'attempt': attempted, 'checks': checks, 'accesses': list(accesses),
                                             'alignment': alignment, 'gap': gap, 'displacement': displacement,
                                             'native_bits': bytes(host)[output:output+48].hex(),
                                             'x86_bits': actual[output:output+48].hex()})
                        saved_a = ctypes.create_string_buffer(initial[a:a+48])
                        saved_b = ctypes.create_string_buffer(initial[b:b+48])
                        wrong_output = ctypes.create_string_buffer(48)
                        native(saved_a, saved_b, wrong_output)
                        wrong = initial[:output]+wrong_output.raw+initial[output+48:]
                        negative += int(wrong != actual)
    return {'text_sha256': TEXT_SHA256, 'function': hex(FUNCTION), 'function_bytes': FUNCTION_BYTES,
            'function_sha256': FUNCTION_SHA256, 'hierarchy_call_instructions': source_calls, 'unicorn': unicorn.__version__,
            'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
            'attempted_cases': attempted, 'instruction_cases': cases, 'outside_fp_domain': outside_domain,
            'mxcsr_initial': '0x1f80', 'intermediate_values_checked': True,
            'mxcsr_status_alone_is_domain_oracle': False, 'mismatches': len(failures), 'failures': failures,
            'snapshot_negative_control_differences': negative,
            'scope': 'Controlled RNE masked binary32 state, finite normal/zero inputs and intermediates, no underflow/overflow; word-relative overlaps and unaligned spans; no actual live pose-state/native Windows claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/record-math'/
                        ('librecord_math.dylib' if sys.platform == 'darwin' else 'librecord_math.so'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.library)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output: output.write(encoded)
    else: print(encoded, end='')
    return int(bool(result['mismatches']))


if __name__ == '__main__':
    sys.exit(main())
