#!/usr/bin/env python3
"""Compare authored record arithmetic with captured instructions and fixed data."""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pins  # noqa: E402

TEXT_BASE = 0x401000
TEXT_BYTES = pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
TARGET_SHA256 = pins.TARGET.sha256
CONTROL_WORD = 0x027f
DATA_REGIONS = {pin.relative.rsplit('/', 1)[1]: (pin.base, pin.size, pin.sha256)
                for pin in (pins.RECORD_BIAS, pins.RECORD_TEMPLATE, pins.FEATURE)}


def load_inputs(capture, data_directory):
    payload = pins.load(capture, TEXT_BYTES, TEXT_SHA256,
                        mismatch=ValueError('Text does not match the pinned restored client'))
    root = Path(data_directory)
    manifest = json.loads((root / 'capture.json').read_text())
    expected = {'format': 'mu-linux-wine-math-capture-v1', 'scope': 'math-data',
                'target_sha256': TARGET_SHA256, 'expected_bytes': 76,
                'restored_text_sha256_before': TEXT_SHA256, 'restored_text_sha256_after': TEXT_SHA256,
                'capture_tool_sha256': pins.MATH_CAPTURE_TOOL_SHA256}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('Math manifest does not match the verified capture profile')
    checks = ('complete_within_scope', 'same_process', 'process_still_running',
              'same_mapping_plan', 'same_image_file', 'target_file_unchanged')
    if not all(manifest.get(key) is True for key in checks):
        raise ValueError('Math capture identity/completeness checks failed')
    records = manifest.get('regions', [])
    if len(records) != len(DATA_REGIONS) or {r.get('file') for r in records} != set(DATA_REGIONS):
        raise ValueError('Math capture has the wrong selected ranges')
    data = {}
    for name, (address, size, digest) in DATA_REGIONS.items():
        record = next(r for r in records if r['file'] == name)
        if (record.get('address') != hex(address) or record.get('bytes') != size or record.get('sha256') != digest):
            raise ValueError('Math region metadata does not match the pinned selection')
        content = (root / name).read_bytes()
        if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('Math region payload identity failed')
        data[name] = content
    identity = struct.pack('<16f', *(1.0 if r == c else 0.0 for r in range(4) for c in range(4)))
    if data['record-bias.bin'] != struct.pack('<d', 0.0) or data['record-template.bin'] != identity:
        raise ValueError('Captured constants do not match the authored public construction')
    return payload, data


def synthetic_records():
    def diagonal(values):
        return [values[r] if r == c else 0.0 for r in range(4) for c in range(4)]
    yield diagonal([1.0]*4)
    yield diagonal([2.0, 4.0, 8.0, 16.0])
    yield [1.0 if c == (1, 2, 0, 3)[r] else 0.0 for r in range(4) for c in range(4)]
    yield [0.0]*16
    yield [0.0]*12 + [2.0, -3.0, 4.0, 0.0]
    yield [1.0]*16
    yield diagonal([2.0**30]*4)
    yield diagonal([2.0**-30]*4)
    yield [1.0, 1.0, 0.0, 0.0, 1.0, 1.0+2.0**-23, 0.0, 0.0,
           0.0, 0.0, 1.0, 0.0, 2.0, -3.0, 4.0, 1.0]
    generator = random.Random(0x4013d0)
    for _ in range(64):
        yield [generator.randint(-1000, 1000)/32.0 for _ in range(16)]
    for _ in range(32):
        words = [(generator.getrandbits(1) << 31) | (generator.randint(124, 130) << 23) |
                 generator.getrandbits(23) for _ in range(16)]
        yield list(struct.unpack('<16f', struct.pack('<16I', *words)))


class CapturedReference:
    def __init__(self, payload, data):
        import unicorn
        import unicorn.x86_const as registers
        self.unicorn, self.registers = unicorn, registers
        self.payload, self.data = payload, data
        self.branch_counts = {'zero_fallback': 0, 'reciprocal': 0}
        self.eax_offsets = {'zero_fallback': set(), 'reciprocal': set()}
        self.unexpected = []

    def execute(self, initial, source, destination=None, row=0, column=0):
        u, r = self.unicorn, self.registers
        machine = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        arena, stack, bridge = 0x700000, 0x600000, 0x500000
        inverse = destination is not None
        function = 0x4013d0 if inverse else 0x401240
        for page in (TEXT_BASE, arena, stack, bridge, 0x1a7d000, 0x1cf3000):
            machine.mem_map(page, 4096)
        machine.mem_write(TEXT_BASE, self.payload[:4096])
        machine.mem_write(arena, initial)
        for name in ('record-bias.bin', 'record-template.bin'):
            machine.mem_write(DATA_REGIONS[name][0], self.data[name])
        machine.mem_write(bridge+0x200, struct.pack('<H', CONTROL_WORD))
        prologue = b'\xdb\xe3\xd9\x2d' + struct.pack('<I', bridge+0x200)
        prologue += b'\xe9' + struct.pack('<i', function - (bridge+0x100+13))
        machine.mem_write(bridge+0x100, prologue)  # Authored FNINIT / FLDCW / JMP harness.
        if inverse:
            arguments = (bridge, arena+destination, arena+source)
            stop = bridge
        else:
            arguments = (bridge, arena+source, row, column)
            machine.mem_write(bridge, b'\xd9\x1d' + struct.pack('<I', bridge+0x300))
            stop = bridge+6  # Authored FSTP rounds the already-float helper return.
        initial_stack = stack+0x800
        machine.mem_write(initial_stack, struct.pack('<'+'I'*len(arguments), *arguments))
        preserved = {r.UC_X86_REG_EBX: 0x12345678, r.UC_X86_REG_EBP: 0x23456789,
                     r.UC_X86_REG_ESI: 0x3456789a, r.UC_X86_REG_EDI: 0x456789ab}
        for register, value in preserved.items():
            machine.reg_write(register, value)
        machine.reg_write(r.UC_X86_REG_ECX, 0x81234567)  # Observed helper overwrites this unused context.
        machine.reg_write(r.UC_X86_REG_ESP, initial_stack)
        machine.reg_write(r.UC_X86_REG_EFLAGS, 2)
        observed_branches, helper_entries, unexpected = set(), [0], []

        def observe_code(uc, address, size, context):
            if address == 0x401240:
                helper_entries[0] += 1
            if address in (0x40145d, 0x40148f):
                observed_branches.add(address)
            allowed = (0x401240 <= address < 0x4013c4 or 0x4013d0 <= address < 0x4014de or
                       bridge+0x100 <= address < bridge+0x10d or not inverse and bridge <= address < bridge+6)
            if not allowed:
                unexpected.append({'kind': 'code', 'address': hex(address)})

        def observe_memory(uc, access, address, size, value, context):
            end = address+size
            valid = stack <= address and end <= stack+4096
            if access == u.UC_MEM_WRITE:
                valid |= inverse and arena+destination <= address and end <= arena+destination+64
                valid |= not inverse and bridge+0x300 <= address and end <= bridge+0x304
            else:
                valid |= arena+source <= address and end <= arena+source+64
                valid |= bridge+0x200 <= address and end <= bridge+0x202
                valid |= any(DATA_REGIONS[name][0] <= address and end <= DATA_REGIONS[name][0]+len(self.data[name])
                             for name in ('record-bias.bin', 'record-template.bin'))
            if not valid:
                unexpected.append({'kind': 'memory', 'address': hex(address), 'bytes': size, 'access': access})

        machine.hook_add(u.UC_HOOK_CODE, observe_code)
        machine.hook_add(u.UC_HOOK_MEM_READ | u.UC_HOOK_MEM_WRITE, observe_memory)
        machine.emu_start(bridge+0x100, stop, timeout=1000000, count=5000)
        checks = {'returned': machine.reg_read(r.UC_X86_REG_EIP) == stop,
                  'stack': machine.reg_read(r.UC_X86_REG_ESP) == initial_stack + 4*len(arguments),
                  'saved_registers': all(machine.reg_read(reg) == value for reg, value in preserved.items()),
                  'control_word': machine.reg_read(r.UC_X86_REG_FPCW) == CONTROL_WORD,
                  'helper_entries': helper_entries[0] == (16 if inverse else 1),
                  'bounded_access': not unexpected}
        if inverse:
            branch = 'zero_fallback' if observed_branches == {0x40145d} else 'reciprocal'
            checks['branch_observed'] = len(observed_branches) == 1
            self.branch_counts[branch] += 1
            self.eax_offsets[branch].add(machine.reg_read(r.UC_X86_REG_EAX) - (arena+destination))
        self.unexpected.extend(unexpected[:10])
        result = None if inverse else bytes(machine.mem_read(bridge+0x300, 4))
        return bytes(machine.mem_read(arena, 4096)), result, checks


def validate(capture, data_directory, library):
    payload, data = load_inputs(capture, data_directory)
    native = ctypes.CDLL(str(Path(library).resolve()))
    if native.mu_record_math_environment_supported() != 1:
        raise ValueError('Host FP environment is outside the supported RNE binary32/binary64 subset')
    inverse = native.mu_record_inverse
    inverse.argtypes, inverse.restype = [ctypes.c_void_p, ctypes.c_void_p], None
    cofactor = native.mu_record_cofactor
    cofactor.argtypes, cofactor.restype = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint], ctypes.c_float
    reference = CapturedReference(payload, data)
    failures, mismatches, cofactor_count, inverse_count = [], 0, 0, 0
    for index, values in enumerate(synthetic_records()):
        source = 512 + index % 4
        initial = bytearray(bytes((0xa5,))*4096)
        initial[source:source+64] = struct.pack('<16f', *values)
        initial = bytes(initial)
        for row in range(4):
            for column in range(4):
                cofactor_count += 1
                host = (ctypes.c_ubyte*4096).from_buffer_copy(initial)
                result = cofactor(ctypes.addressof(host)+source, row, column)
                arena, expected, checks = reference.execute(initial, source, row=row, column=column)
                valid = (struct.pack('<f', result) == expected and bytes(host) == arena == initial and
                         all(checks.values()) and math.isfinite(result))
                if not valid:
                    mismatches += 1
                    if len(failures) < 20:
                        failures.append({'kind': 'cofactor', 'record': index, 'row': row, 'column': column, 'checks': checks})
        for displacement in (-64, -17, -4, -1, 0, 1, 4, 17, 64, 128):
            inverse_count += 1
            destination = source+displacement
            host = (ctypes.c_ubyte*4096).from_buffer_copy(initial)
            pointer = ctypes.addressof(host)
            inverse(pointer+destination, pointer+source)
            arena, _, checks = reference.execute(initial, source, destination)
            finite = all(math.isfinite(value) for value in struct.unpack('<16f', arena[destination:destination+64]))
            if bytes(host) != arena or not all(checks.values()) or not finite:
                mismatches += 1
                if len(failures) < 20:
                    failures.append({'kind': 'inverse', 'record': index, 'displacement': displacement, 'checks': checks, 'finite_reference': finite})
    return {'target_sha256': TARGET_SHA256, 'capture_sha256': TEXT_SHA256,
            'math_data_sha256': {name: item[2] for name, item in DATA_REGIONS.items()},
            'reference': 'Captured wrapper/helper and captured fixed data; no arithmetic stubs.',
            'unicorn': reference.unicorn.__version__, 'x87_control_word': hex(CONTROL_WORD),
            'cofactor_cases': cofactor_count, 'inverse_cases': inverse_count,
            'mismatches': mismatches, 'first_failures': failures,
            'branches': reference.branch_counts,
            'observed_eax_offsets': {name: sorted(values) for name, values in reference.eax_offsets.items()},
            'unexpected_accesses': reference.unexpected[:20],
            'limitations': ['Controlled PC53/RNE masked x87 state, DF clear and host default RNE; actual original FP state unknown.',
                            'Synthetic finite moderate records and selected scale/degenerate/alias cases; NaN, infinity, unmasked traps and FP flags unverified.',
                            'Logical void inverse API; branch-dependent original EAX scratch values are observations, not a recovered return contract.',
                            'Captured-instruction evidence, not native Windows or actual game invocation.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--math-data', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = validate(args.capture, args.math_data, args.library)
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    return 1 if result['mismatches'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
