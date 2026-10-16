#!/usr/bin/env python3
"""Compare authored rotation conversion with the captured client instructions.

The actual rotation candidate 0x00d00724, its two float wrappers and the
client trigonometric entries 0x01985700/0x0198c4d0 run in Unicorn over the
pinned restored text, the verified second image section and the captured
dispatch flag. Nothing is stubbed. A read of any byte outside those captures,
the synthetic input span or previously written stack bytes stops the case.
"""
import argparse
import ctypes
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
FLAG_ADDRESS = 0x0bdd1cc8
FLAG_SHA256 = '67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450'
FUNCTION, FUNCTION_BYTES = 0xd00724, 411
FUNCTION_SHA256 = '1d585a53f706aed8dd37de105b739b739905065deb41350a02fe83d9153e53a2'
SCALE_ADDRESS = 0x1a7de98
SINE_WRAPPER, COSINE_WRAPPER = 0x9681bd, 0x9fa223
SINE_ENTRY, COSINE_ENTRY = 0x1985700, 0x198c4d0
# Instruction after each wrapper's call: the helper's x87 return is in ST0.
WRAPPER_RETURNS = {0x9681d2: 'sin', 0x9fa238: 'cos'}
PATHS = {0x19a7315: ('sin', 'sse2-main'), 0x19a7466: ('sin', 'sse2-zero'),
         0x19a747c: ('sin', 'sse2-tiny'), 0x19997cf: ('sin', 'x87-fallback'),
         0x19acd75: ('cos', 'sse2-main'), 0x19aceb9: ('cos', 'sse2-tiny-or-zero'),
         0x19996df: ('cos', 'x87-fallback')}
CALLERS = ((0x12b4225, 0x12b4441, (0x12b442e,)), (0x12b35c7, 0x12b37e3, (0x12b37d0,)),
           (0x12b5064, 0x12b58cf, (0x12b53c9, 0x12b53d8)), (0x12bcffb, 0x12bd35b, (0x12bd130,)))
ARENA, STACK, RETURNED_TO, FLAG_PAGE = 0x30000000, 0x31000000, 0x32000000, 0x0bdd1000
INITIAL_STACK = STACK + 0x1800
SSE2_LIMIT = 180224.0  # |angle| below this keeps the halved double under hi16 0x40f6.
FPCW, MXCSR = 0x027f, 0x1f80


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits32(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits32(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def ordered64(value):
    bits = struct.unpack('<q', struct.pack('<d', value))[0]
    return bits if bits >= 0 else -(bits & 0x7fffffffffffffff)


def extended_to_double(register):
    mantissa, high = register
    sign = -1 if high & 0x8000 else 1
    if high & 0x7fff == 0x7fff:
        return math.copysign(math.inf, sign) if mantissa == 1 << 63 else math.nan
    if mantissa == 0:
        return math.copysign(0.0, sign)
    exact = sign*Fraction(mantissa)*Fraction(2)**((high & 0x7fff)-16383-63)
    value = float(exact)
    if Fraction(value) != exact:
        raise ValueError('x87 trig result is not exactly binary64')
    return value


def load_pinned(path, size, digest, label):
    payload = Path(path).read_bytes()
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input does not match pinned {label}')
    return payload


def midpoint_angles(path):
    """Angles from scan_trig_midpoints output: twice each candidate, both signs."""
    cases = []
    for line in Path(path).read_text().splitlines():
        name, argument, distance = line.split()
        if name not in ('sin', 'cos') or int(distance) < 0:
            raise ValueError('Malformed midpoint candidate line')
        half = from_bits32(int(argument, 16))
        if not (0 < half < SSE2_LIMIT/2):
            raise ValueError('Midpoint candidate outside the SSE2 domain')
        for sign in (1.0, -1.0):
            for position in range(3):
                triple = [0.0, 0.0, 0.0]
                triple[position] = sign*2.0*half
                cases.append(('midpoint-candidate', tuple(triple)))
    return cases


def angle_domain():
    """Deterministic synthetic angle triples and their categories."""
    tau = 2*math.pi
    edge = [0.0, -0.0, from_bits32(1), -from_bits32(1), from_bits32(2), from_bits32(3),
            2.0**-126, -2.0**-126, 1e-20, -1e-8, 2.0**-12, 0.1, -0.5, 1.0, -1.0,
            math.pi/4, math.pi/2, -math.pi/2, math.pi, -math.pi, 3*math.pi/2, tau, -tau,
            4*math.pi, 10.0, -100.0, 1000.0, 12345.678, 65536.0, -131072.0,
            SSE2_LIMIT-2.0**-6, -(SSE2_LIMIT-2.0**-6)]
    edge = [f32(value) for value in edge]
    cases = []
    core = [edge[index] for index in (0, 1, 2, 4, 8, 11, 13, 14, 16, 18, 21, 25, 28, 30)]
    for a in core:
        for b in core:
            for c in core:
                cases.append(('edge-product', (a, b, c)))
    generator = random.Random(FUNCTION)
    others = (lambda: f32(generator.uniform(-math.pi, math.pi)))
    for value in edge:
        for position in range(3):
            triple = [others(), others(), others()]
            triple[position] = value
            cases.append(('edge-axis', tuple(triple)))
    for _ in range(1500):
        cases.append(('uniform-pi', tuple(f32(generator.uniform(-math.pi, math.pi)) for _ in range(3))))
    for _ in range(1000):
        cases.append(('uniform-4pi', tuple(f32(generator.uniform(-4*math.pi, 4*math.pi)) for _ in range(3))))
    for _ in range(1500):
        cases.append(('log-magnitude', tuple(f32(generator.choice((-1, 1))*2.0**generator.uniform(-40, 17.4))
                                            for _ in range(3))))
    for _ in range(500):
        triple = []
        while len(triple) < 3:
            value = from_bits32(generator.getrandbits(32))
            if math.isfinite(value) and abs(value) < SSE2_LIMIT:
                triple.append(value)
        cases.append(('random-bits', tuple(triple)))
    beyond = [SSE2_LIMIT, -SSE2_LIMIT, 1e6, -1e10, 3.4028234663852886e38, math.inf, -math.inf, math.nan]
    for value in beyond:
        for position in range(3):
            triple = [0.25, -0.75, 1.5]
            triple[position] = value
            cases.append(('beyond-sse2', tuple(f32(item) for item in triple)))
    return cases


def validate(text, data, flag, library, midpoints=None):
    payload = load_pinned(text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data_payload = load_pinned(data, DATA_BYTES, DATA_SHA256, 'second image section')
    flag_payload = load_pinned(flag, 4, FLAG_SHA256, 'dispatch flag')
    if struct.unpack('<I', flag_payload)[0] != 1:
        raise ValueError('Captured dispatch flag is not 1')
    body = payload[FUNCTION-TEXT_BASE:FUNCTION-TEXT_BASE+FUNCTION_BYTES]
    if hashlib.sha256(body).hexdigest() != FUNCTION_SHA256:
        raise ValueError('Pinned rotation body mismatch')
    if struct.unpack_from('<d', data_payload, SCALE_ADDRESS-DATA_BASE)[0] != 0.5:
        raise ValueError('Captured scale is not 0.5')
    import unicorn
    from unicorn import (Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ,
                         UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED, UC_MEM_WRITE,
                         UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC)
    from unicorn import x86_const as x86
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    caller_links = []
    for start, end, expected in CALLERS:
        decoded = list(decoder.disasm(payload[start-TEXT_BASE:end-TEXT_BASE], start))
        selected = [item for item in decoded if item.address in expected]
        if (len(selected) != len(expected) or any(item.mnemonic != 'call' or item.operands[0].type != X86_OP_IMM
                                                  or item.operands[0].imm != FUNCTION for item in selected)):
            raise ValueError('Selected rotation call link changed')
        caller_links.extend(hex(item.address) for item in selected)

    library = Path(library).resolve(strict=True)
    handle = ctypes.CDLL(str(library))
    environment = handle.mu_record_math_environment_supported
    environment.restype = ctypes.c_int
    if environment() != 1:
        raise ValueError('Host requires binary32/binary64 storage and RNE environment')
    native = handle.mu_rotation_quaternion
    native.argtypes, native.restype = [ctypes.c_void_p]*2, None
    trig_type = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)
    injected = handle.mu_rotation_quaternion_using
    injected.argtypes, injected.restype = [ctypes.c_void_p, ctypes.c_void_p, trig_type, trig_type], None

    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    machine.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
    machine.mem_write(TEXT_BASE, payload)
    machine.mem_map(DATA_BASE, (DATA_BYTES+4095) & ~4095, UC_PROT_READ)
    machine.mem_write(DATA_BASE, data_payload)
    machine.mem_map(FLAG_PAGE, 4096, UC_PROT_READ)
    machine.mem_write(FLAG_ADDRESS, flag_payload)
    machine.mem_map(ARENA, 8192, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(STACK, 8192, UC_PROT_READ | UC_PROT_WRITE)
    machine.mem_map(RETURNED_TO, 4096, UC_PROT_READ | UC_PROT_EXEC)
    preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_EBP: 0x23456789,
                 x86.UC_X86_REG_ESI: 0x3456789a, x86.UC_X86_REG_EDI: 0x456789ab}
    xmm = [getattr(x86, f'UC_X86_REG_XMM{index}') for index in range(8)]

    state = {}

    def reset(source, destination):
        state.update(source=source, destination=destination, stopped=None, stores=[],
                     written=set(), data_reads=set(), flag_reads=0, input_reads=0,
                     trig=[], paths=[])
        state['written'].update(range(INITIAL_STACK, INITIAL_STACK+12))

    def observe(uc, access, address, size, value, ignored):
        end = address+size
        if access == UC_MEM_WRITE:
            if STACK <= address and end <= INITIAL_STACK:
                state['written'].update(range(address, end))
            elif ARENA+state['destination'] <= address and end <= ARENA+state['destination']+16:
                state['stores'].append((address-ARENA-state['destination'], size))
            elif state['stopped'] is None:
                state['stopped'] = ('write', hex(address), size)
                uc.emu_stop()
            return
        if STACK <= address and end <= INITIAL_STACK+12:
            if all(byte in state['written'] for byte in range(address, end)):
                return
        elif ARENA+state['source'] <= address and end <= ARENA+state['source']+12:
            state['input_reads'] += 1
            return
        elif DATA_BASE <= address and end <= DATA_BASE+DATA_BYTES:
            state['data_reads'].add((address, size))
            return
        elif FLAG_ADDRESS <= address and end <= FLAG_ADDRESS+4:
            state['flag_reads'] += 1
            return
        elif TEXT_BASE <= address and end <= TEXT_BASE+TEXT_BYTES:
            return
        if state['stopped'] is None:
            state['stopped'] = ('uncaptured-read', hex(address), size)
        uc.emu_stop()

    def unmapped(uc, access, address, size, value, ignored):
        if state['stopped'] is None:
            state['stopped'] = ('unmapped', hex(address), size)
        return False

    def trig_return(uc, address, size, ignored):
        top = (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7
        state['trig'].append((WRAPPER_RETURNS[address], uc.reg_read(x86.UC_X86_REG_FP0+top)))

    def path(uc, address, size, ignored):
        state['paths'].append(PATHS[address])

    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe)
    machine.hook_add(UC_HOOK_MEM_UNMAPPED, unmapped)
    for address in WRAPPER_RETURNS:
        machine.hook_add(UC_HOOK_CODE, trig_return, begin=address, end=address)
    for address in PATHS:
        machine.hook_add(UC_HOOK_CODE, path, begin=address, end=address)

    def run(arena, source, destination, poison=0x7ff4dead5eed0000, fpcw=FPCW, mxcsr=MXCSR):
        reset(source, destination)
        machine.mem_write(ARENA, arena)
        machine.mem_write(STACK, b'\xa5'*8192)
        machine.mem_write(INITIAL_STACK, struct.pack('<III', RETURNED_TO, ARENA+source, ARENA+destination))
        for register, value in preserved.items():
            machine.reg_write(register, value)
        for register in (x86.UC_X86_REG_EAX, x86.UC_X86_REG_ECX, x86.UC_X86_REG_EDX):
            machine.reg_write(register, 0xdeadbeef)
        for index, register in enumerate(xmm):
            lane = (poison+index*0x0101010101) & 0xffffffffffffffff
            machine.reg_write(register, lane | (lane << 64))
        machine.reg_write(x86.UC_X86_REG_ESP, INITIAL_STACK)
        machine.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        machine.reg_write(x86.UC_X86_REG_FPCW, fpcw)
        machine.reg_write(x86.UC_X86_REG_FPSW, 0)
        machine.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        machine.reg_write(x86.UC_X86_REG_MXCSR, mxcsr)
        error = None
        try:
            machine.emu_start(FUNCTION, RETURNED_TO, timeout=10000000, count=4000)
        except UcError as failure:
            error = str(failure)
        returned = machine.reg_read(x86.UC_X86_REG_EIP) == RETURNED_TO and state['stopped'] is None and error is None
        final_mxcsr = machine.reg_read(x86.UC_X86_REG_MXCSR)
        checks = {'returned': returned,
                  'stack': machine.reg_read(x86.UC_X86_REG_ESP) == INITIAL_STACK+4,
                  'callee_saved': all(machine.reg_read(r) == v for r, v in preserved.items()),
                  'direction_flag': (machine.reg_read(x86.UC_X86_REG_EFLAGS) >> 10) & 1 == 0,
                  'mxcsr_control': final_mxcsr & ~0x3f == mxcsr,
                  'fpcw': machine.reg_read(x86.UC_X86_REG_FPCW) == fpcw,
                  'x87_top': (machine.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7 == 0,
                  'input_reads': state['input_reads'] == 3,
                  'flag_reads': state['flag_reads'] == 6,
                  'ordered_stores': state['stores'] == [(0, 4), (4, 4), (8, 4), (12, 4)]}
        return {'checks': checks, 'error': error, 'stopped': state['stopped'],
                'arena': bytes(machine.mem_read(ARENA, 8192)),
                'trig': list(state['trig']), 'paths': list(state['paths']),
                'mxcsr_status': final_mxcsr & 0x3f}

    def host_arena(arena, source, destination, function=None, angles_override=None):
        host = (ctypes.c_ubyte*8192).from_buffer_copy(arena)
        pointer = ctypes.addressof(host)
        if angles_override is not None:
            reordered = ctypes.create_string_buffer(angles_override)
            native(reordered, pointer+destination)
        elif function is None:
            native(pointer+source, pointer+destination)
        else:
            function(pointer+source, pointer+destination)
        return bytes(host)

    cases = angle_domain()+(midpoint_angles(midpoints) if midpoints else [])
    background = bytes((index*37+11) & 0xff for index in range(8192))
    source, destination = 0x800, 0x1000
    compared = stopped = mismatches = composition_mismatches = 0
    axis_order_differences = double_intermediate_differences = 0
    failures, stops, outside = [], [], []
    category_counts, path_counts, stop_reasons = {}, {}, {}
    trig_calls = trig_equal_double = trig_equal_float = midpoint_calls = midpoint_float_equal = 0
    ulp_histogram = {}
    worst = {'sin': None, 'cos': None}
    data_reads = set()
    status_flags = {}
    for number, (category, angles) in enumerate(cases):
        arena = bytearray(background)
        arena[source:source+12] = struct.pack('<3f', *angles)
        arena = bytes(arena)
        result = run(arena, source, destination)
        data_reads.update(state['data_reads'])
        if category == 'beyond-sse2':
            # Outside the supported domain: characterize only, never counted as a match.
            expected = host_arena(arena, source, destination)
            outside.append({'angles': [f'{bits32(a):08x}' for a in angles],
                            'returned': result['checks']['returned'], 'stopped': result['stopped'],
                            'paths': sorted({'/'.join(item) for item in result['paths']}),
                            'x86': result['arena'][destination:destination+16].hex()
                            if result['checks']['returned'] else None,
                            'native': expected[destination:destination+16].hex()})
            continue
        if not result['checks']['returned']:
            stopped += 1
            reason = result['stopped'][0] if result['stopped'] else 'error'
            key = f"{category}:{reason}:{result['stopped'][1] if result['stopped'] else result['error']}"
            stop_reasons[key] = stop_reasons.get(key, 0)+1
            if len(stops) < 12:
                stops.append({'case': number, 'category': category,
                              'angles': [f'{bits32(a):08x}' for a in angles],
                              'stopped': result['stopped'], 'error': result['error'],
                              'paths': ['/'.join(item) for item in result['paths']]})
            continue
        compared += 1
        category_counts[category] = category_counts.get(category, 0)+1
        for item in result['paths']:
            label = '/'.join(item)
            path_counts[label] = path_counts.get(label, 0)+1
        status_flags[hex(result['mxcsr_status'])] = status_flags.get(hex(result['mxcsr_status']), 0)+1
        # Exact client trig doubles, keyed per call for the composition check.
        halves = [f32(a*0.5) for a in (angles[2], angles[1], angles[0])]
        expected_order = [(name, half) for half in halves for name in ('sin', 'cos')]
        client = {}
        for (name, half), (observed_name, register) in zip(expected_order, result['trig']):
            if category == 'midpoint-candidate' and half != 0:
                midpoint_calls += 1
            if observed_name != name:
                raise ValueError('Unexpected trig call order')
            value = extended_to_double(register)
            client[(name, bits32(half))] = value
            host = math.sin(half) if name == 'sin' else math.cos(half)
            trig_calls += 1
            trig_equal_double += int(struct.pack('<d', host) == struct.pack('<d', value))
            float_equal = struct.pack('<f', host) == struct.pack('<f', value)
            trig_equal_float += int(float_equal)
            if category == 'midpoint-candidate' and half != 0:
                midpoint_float_equal += int(float_equal)
            difference = abs(ordered64(host)-ordered64(value))
            key = f'{name}:{min(difference, 3)}'
            ulp_histogram[key] = ulp_histogram.get(key, 0)+1
            if difference and (worst[name] is None or difference > worst[name]['ulp']):
                worst[name] = {'ulp': difference, 'argument': half.hex(), 'client': value.hex(), 'host': host.hex()}
        if len(result['trig']) != 6:
            raise ValueError('Expected six trig calls')
        expected = host_arena(arena, source, destination)
        checks = dict(result['checks'], full_arena=expected == result['arena'])

        def lookup(name):
            return lambda argument: client[(name, bits32(argument))]
        sine, cosine = trig_type(lookup('sin')), trig_type(lookup('cos'))
        composed = host_arena(arena, source, destination,
                              function=lambda a, b: injected(a, b, sine, cosine))
        composition_ok = composed == result['arena']
        composition_mismatches += int(not composition_ok)
        if not all(checks.values()):
            mismatches += 1
            if len(failures) < 12:
                failures.append({'case': number, 'category': category, 'checks': checks,
                                 'angles': [f'{bits32(a):08x}' for a in angles],
                                 'native': expected[destination:destination+16].hex(),
                                 'x86': result['arena'][destination:destination+16].hex(),
                                 'composition_with_client_trig_matches': composition_ok})
        wrong = host_arena(arena, source, destination, angles_override=struct.pack('<3f', *reversed(angles)))
        axis_order_differences += int(wrong != result['arena'])
        sv = {i: f32(client[('sin', bits32(f32(angles[i]*0.5)))]) for i in range(3)}
        cv = {i: f32(client[('cos', bits32(f32(angles[i]*0.5)))]) for i in range(3)}
        unrounded = (sv[0]*cv[1]*cv[2]-cv[0]*sv[1]*sv[2], cv[0]*sv[1]*cv[2]+sv[0]*cv[1]*sv[2],
                     cv[0]*cv[1]*sv[2]-sv[0]*sv[1]*cv[2], cv[0]*cv[1]*cv[2]+sv[0]*sv[1]*sv[2])
        double_intermediate_differences += int(struct.pack('<4f', *unrounded) !=
                                               result['arena'][destination:destination+16])

    # Alias, alignment, register-poison and FP control-word sweeps on a subset.
    generator = random.Random(FUNCTION+1)
    alias_cases = alias_mismatches = 0
    for _ in range(64):
        angles = tuple(f32(generator.uniform(-4*math.pi, 4*math.pi)) for _ in range(3))
        for alignment in range(4):
            for displacement in (-16, -12, -8, -4, -1, 0, 1, 4, 8, 12, 16):
                base = 0x800+alignment
                target = base+displacement
                arena = bytearray(background)
                arena[base:base+12] = struct.pack('<3f', *angles)
                arena = bytes(arena)
                result = run(arena, base, target)
                ok = (result['checks']['returned'] and all(result['checks'].values())
                      and host_arena(arena, base, target) == result['arena'])
                alias_cases += 1
                alias_mismatches += int(not ok)
    state_cases = state_mismatches = 0
    control_variants = {'pc64': (0x037f, MXCSR), 'pc24': (0x007f, MXCSR),
                        'poison-zero': (FPCW, MXCSR), 'mxcsr-status-preset': (FPCW, MXCSR | 0x3f)}
    for _ in range(64):
        angles = tuple(f32(generator.uniform(-100, 100)) for _ in range(3))
        arena = bytearray(background)
        arena[source:source+12] = struct.pack('<3f', *angles)
        arena = bytes(arena)
        expected = host_arena(arena, source, destination)
        for label, (fpcw, mxcsr) in control_variants.items():
            poison = 0 if label == 'poison-zero' else 0x7ff4dead5eed0000
            result = run(arena, source, destination, poison=poison, fpcw=fpcw, mxcsr=mxcsr)
            checks = dict(result['checks'])
            checks['mxcsr_control'] = True if label == 'mxcsr-status-preset' else checks['mxcsr_control']
            state_cases += 1
            state_mismatches += int(not (all(checks.values()) and result['arena'] == expected))
    dispatch_probes = {}
    for label, (fpcw, mxcsr) in {'mxcsr-round-toward-zero': (FPCW, 0x7f80),
                                 'x87-invalid-unmasked': (0x027e, MXCSR)}.items():
        arena = bytearray(background)
        arena[source:source+12] = struct.pack('<3f', 0.25, -0.75, 1.5)
        result = run(bytes(arena), source, destination, fpcw=fpcw, mxcsr=mxcsr)
        dispatch_probes[label] = {'returned': result['checks']['returned'], 'stopped': result['stopped'],
                                  'paths': ['/'.join(item) for item in result['paths']]}

    spans = sorted(data_reads)
    return {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'flag_sha256': FLAG_SHA256,
            'flag_value': 1, 'function': hex(FUNCTION), 'function_bytes': FUNCTION_BYTES,
            'function_sha256': FUNCTION_SHA256, 'selected_call_instructions': caller_links,
            'unicorn': unicorn.__version__,
            'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
            'fpcw_initial': hex(FPCW), 'mxcsr_initial': hex(MXCSR),
            'attempted_cases': len(cases), 'instruction_cases': compared, 'category_counts': category_counts,
            'stopped_cases': stopped, 'outside_domain_cases': outside, 'stop_reasons': stop_reasons, 'stop_examples': stops,
            'mismatches': mismatches, 'failures': failures,
            'composition_with_client_trig_mismatches': composition_mismatches,
            'trig_path_counts': path_counts, 'mxcsr_status_after': status_flags,
            'trig_calls': trig_calls, 'trig_host_double_equal': trig_equal_double,
            'trig_host_float_equal': trig_equal_float, 'trig_ulp_histogram_capped_at_3': ulp_histogram,
            'trig_worst_double_ulp': worst,
            'midpoint_input_sha256': hashlib.sha256(Path(midpoints).read_bytes()).hexdigest() if midpoints else None,
            'midpoint_nonzero_trig_calls': midpoint_calls, 'midpoint_trig_float_equal': midpoint_float_equal,
            'data_reads': {'count': len(spans), 'first': hex(spans[0][0]) if spans else None,
                           'last_end': hex(max(a+s for a, s in spans)) if spans else None},
            'alias_alignment_cases': alias_cases, 'alias_alignment_mismatches': alias_mismatches,
            'state_variant_cases': state_cases, 'state_variant_mismatches': state_mismatches,
            'dispatch_probes': dispatch_probes,
            'axis_order_negative_control_differences': axis_order_differences,
            'double_intermediate_negative_control_differences': double_intermediate_differences,
            'scope': ('Controlled synthetic angles, flag 1, x87 0x027f and MXCSR 0x1f80 unless noted; '
                      'full captured text/second-section/flag; any other read stops a case. Host libm '
                      'substitutes client trig in mu_rotation_quaternion; no live animation input, '
                      'native Windows FP state or exceptional-value equivalence claim.')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/record-math' /
                        ('librecord_math.dylib' if sys.platform == 'darwin' else 'librecord_math.so'))
    parser.add_argument('--midpoints', type=Path, help='Optional scan_trig_midpoints output')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.text, args.data, args.flag, args.library, args.midpoints)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    failed = (result['mismatches'] or result['composition_with_client_trig_mismatches'] or
              result['alias_alignment_mismatches'] or result['state_variant_mismatches'] or
              not result['axis_order_negative_control_differences'])
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
