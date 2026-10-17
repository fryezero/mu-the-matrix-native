#!/usr/bin/env python3
"""Static map of pose-builder callers and the render path (CLIENT-SKIN-001).

Reads only the pinned restored text and second image section, plus the Wine
8.0~repack-4 i386 opengl32.dll/glu32.dll from Debian libwine to name import
slots. Nothing here executes client code. It reports:

* every raw E8 candidate of the pose builder 0x012b5064, its containing
  function (nearest preceding PUSH EBP; MOV EBP,ESP whose linear decode lands
  exactly on the call with no RET between) and a block-local symbolic reading
  of the eight pushed arguments and ECX, with a coarse classification;
* the same argument reading for the animation tick 0x012b4dd3;
* raw caller counts of the transform, render-mesh and render-body routines and
  their default-buffer wrappers;
* the OPENGL32/GLU32 import-slot names (slot value minus the DLL's preferred or
  observed base must be an export RVA) and raw FF 15 call-site counts;
* the ordered static GL call listing of render-mesh 0x012b8d1d and the GL state
  wrappers it calls.

Symbolic arguments are a reading of straight-line instructions inside one basic
block; they are not data-flow proofs across branches.
"""
import argparse
import bisect
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_hierarchy_common as common  # noqa: E402

POSE, TICK, TRANSFORM, RENDER_MESH, RENDER_BODY = 0x012b5064, 0x012b4dd3, 0x012b5bde, 0x012b8d1d, 0x012bb35a
WRAPPERS = {'transform_default_buffers': 0x00966ea5, 'render_mesh_default_buffers': 0x00966e4a,
            'render_body_default_buffers': 0x00966def}
ELEMENT, VECTOR = 0x00cfc922, 0x00cfc94a
BONE_BUFFER = 0x06fce398
OPENGL32_SHA256 = '6e10ea17cd63f1fec97f37b1c00a902028c82674231cd477d7a857f72cd7b394'
GLU32_SHA256 = 'd75036023e994eaecf6b9cb7ba74ae4a9dfcb7ee84597db1b5f32d1f2e0499b1'
OPENGL32_SLOTS = (0x01a7c64c, 0x01a7c790)  # zero-terminated block; first static import wglDeleteContext
GLU32_SLOTS = (0x01a7c170, 0x01a7c180)     # first static import gluBuild2DMipmaps
GLU32_OBSERVED_BASE = 0x00360000           # evidence/x86-first-game-maps.txt (guest mapping)
STATIC_FIRST_IMPORT = {'opengl32': 'wglDeleteContext', 'glu32': 'gluBuild2DMipmaps'}
GL_MODES = {0: 'GL_POINTS', 1: 'GL_LINES', 2: 'GL_LINE_LOOP', 3: 'GL_LINE_STRIP', 4: 'GL_TRIANGLES',
            5: 'GL_TRIANGLE_STRIP', 6: 'GL_TRIANGLE_FAN', 7: 'GL_QUADS', 8: 'GL_QUAD_STRIP', 9: 'GL_POLYGON'}
STATE_WRAPPERS = {  # investigator labels from the decoded bodies
    0x0184a699: 'push-identity', 0x0184a6ab: 'pop-matrix', 0x0184a6b7: 'enable-depth-test',
    0x0184a6da: 'disable-depth-test', 0x0184a6fd: 'enable-cull-face', 0x0184a720: 'disable-cull-face',
    0x0184a743: 'enable-depth-mask', 0x0184a763: 'disable-depth-mask', 0x0184a783: 'alpha-test-mode',
    0x0184a7f3: 'blend-off', 0x0184a872: 'blend-mode-1', 0x0184a901: 'blend-mode-2', 0x0184a990: 'blend-mode-990',
    0x0184aa2b: 'blend-mode-3', 0x0184aab7: 'blend-mode-ab7', 0x0184ab46: 'blend-mode-b46',
    0x0184abd5: 'blend-mode-bd5', 0x0184ac67: 'blend-mode-c67', 0x0184acf6: 'bind-texture-cached',
    0x012b7e53: 'push-matrix', 0x012b7e65: 'pop-matrix-2'}
SUB_REGISTERS = {'ax': 'eax', 'al': 'eax', 'cx': 'ecx', 'cl': 'ecx', 'dx': 'edx', 'dl': 'edx',
                 'si': 'esi', 'di': 'edi'}
JUMPS = re.compile(r'^j')


# --------------------------------------------------------------------------
# PE exports (authored minimal parser for the Wine DLLs).


def pe_exports(payload):
    """Return (preferred image base, {rva: [names]})."""
    pe = struct.unpack_from('<I', payload, 0x3c)[0]
    if payload[pe:pe+4] != b'PE\0\0':
        raise ValueError('not a PE image')
    sections = struct.unpack_from('<H', payload, pe+6)[0]
    optional = struct.unpack_from('<H', payload, pe+20)[0]
    base = struct.unpack_from('<I', payload, pe+24+28)[0]
    export_rva = struct.unpack_from('<I', payload, pe+24+96)[0]
    table = []
    for index in range(sections):
        header = pe+24+optional+40*index
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from('<IIII', payload, header+8)
        table.append((virtual_address, max(virtual_size, raw_size), raw_offset))

    def offset(rva):
        for address, size, raw in table:
            if address <= rva < address+size:
                return rva-address+raw
        raise ValueError(f'RVA {rva:#x} outside sections')
    directory = offset(export_rva)
    functions, names, address_table, name_table, ordinal_table = struct.unpack_from('<IIIII', payload, directory+20)
    rvas = [struct.unpack_from('<I', payload, offset(address_table)+4*i)[0] for i in range(functions)]
    exports = {}
    for i in range(names):
        name_rva = struct.unpack_from('<I', payload, offset(name_table)+4*i)[0]
        ordinal = struct.unpack_from('<H', payload, offset(ordinal_table)+2*i)[0]
        start = offset(name_rva)
        exports.setdefault(rvas[ordinal], []).append(payload[start:payload.index(b'\0', start)].decode())
    return base, exports


def name_slots(data, low, high, payload, base=None):
    preferred, exports = pe_exports(payload)
    base = preferred if base is None else base
    slots = []
    for slot in range(low, high, 4):
        value = struct.unpack('<I', data.read(slot, 4))[0]
        if value == 0:
            break
        names = exports.get((value-base) & 0xffffffff)
        slots.append({'slot': hex(slot), 'value': hex(value), 'name': names[0] if names else None})
    return slots


# --------------------------------------------------------------------------
# Decoding helpers.


class Text:
    def __init__(self, region):
        self.region = region
        self.engine = common.decoder()
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.lite = Cs(CS_ARCH_X86, CS_MODE_32)
        self.starts = {}
        self.spans = {}
        self.decoded = {}
        self.addresses = {}

    def raw_calls(self, target, opcode=0xe8):
        data, base, sites, cursor = self.region.data, self.region.base, [], -1
        while True:
            cursor = data.find(bytes([opcode]), cursor+1)
            if cursor < 0 or cursor > len(data)-5:
                return sites
            relative = struct.unpack_from('<i', data, cursor+1)[0]
            if (base+cursor+5+relative) & 0xffffffff == target:
                sites.append(base+cursor)

    def raw_bytes(self, pattern):
        data, base, sites, cursor = self.region.data, self.region.base, [], -1
        while True:
            cursor = data.find(pattern, cursor+1)
            if cursor < 0:
                return sites
            sites.append(base+cursor)

    def lands(self, start, target):
        code = self.region.read(start, target+16-start)
        for address, size, mnemonic, _ in self.lite.disasm_lite(code, start):
            if address >= target:
                return address == target
            if mnemonic in ('ret', 'retf'):
                return False
        return False

    def function_start(self, site, limit=0x30000):
        """Nearest PUSH EBP; MOV EBP,ESP that decodes onto site without a RET."""
        if site in self.starts:
            return self.starts[site]
        data, base = self.region.data, self.region.base
        cursor, found = site-base, None
        while cursor > site-base-limit:
            cursor = data.rfind(b'\x55\x8b\xec', 0, cursor)
            if cursor < 0:
                break
            span = self.spans.get(base+cursor)
            # A span holds every instruction start up to the first RET (or up
            # to its decoded end), so membership is the same test as lands().
            if span is not None and (site < span[1] or span[2]):
                accepted = site in span[0]
            else:
                accepted = self.lands(base+cursor, site)
            if accepted:
                found = base+cursor
                break
        self.starts[site] = found
        if found is not None and found not in self.spans:
            addresses, complete, end = set(), False, found
            code = self.region.read(found, min(0x80000, self.region.end-found))
            for address, size, mnemonic, _ in self.lite.disasm_lite(code, found):
                addresses.add(address)
                end = address+size
                if mnemonic in ('ret', 'retf'):
                    complete = True
                    break
            self.spans[found] = (addresses, end, complete)
        return found

    def decode(self, start, end):
        """Detailed linear decode from start through the instruction at or after end (cached)."""
        out = self.decoded.setdefault(start, [])
        if not out or out[-1].address < end:
            cursor = out[-1].address+out[-1].size if out else start
            code = self.region.read(cursor, end+16-cursor)
            for instruction in self.engine.disasm(code, cursor):
                out.append(instruction)
                if instruction.address >= end:
                    break
        index = bisect.bisect_left([i.address for i in out], end) if len(out) < 64 else \
            self._index(start, out, end)
        return out[:index+1]

    def _index(self, start, out, end):
        addresses = self.addresses.get(start)
        if addresses is None or len(addresses) != len(out):
            addresses = self.addresses[start] = [i.address for i in out]
        return min(bisect.bisect_left(addresses, end), len(out)-1)

    def linear(self, start, end):
        instructions, stop = common.decode_range(self.region, start, end, self.engine)
        if stop is not None:
            raise ValueError(f'decode of {start:#x}..{end:#x} stopped at {stop:#x}')
        return instructions


def block_start(instructions):
    targets = {i.operands[0].imm for i in instructions
               if JUMPS.match(i.mnemonic) and i.operands and i.operands[0].type == 2}
    for k in range(len(instructions)-1, -1, -1):
        if instructions[k].address in targets or (k and JUMPS.match(instructions[k-1].mnemonic)):
            return k
    return 0


def evaluate(instructions):
    """Symbolic reading of a straight-line run ending at a call.

    Returns (pushed values in push order, registers, notes). Registers start
    as '?reg'; memory operands become '[expression]'. Calls to the vector
    accessors are folded (0x00cfc94a returns ECX, 0x00cfc922 returns
    ECX+4*index); other calls are noted and their results stay opaque.
    """
    from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
    state, stack, notes = {}, [], []

    def register(instruction, operand):
        name = instruction.reg_name(operand.reg)
        return SUB_REGISTERS.get(name, name)

    def address(instruction, operand):
        memory, parts = operand.mem, []
        if memory.base:
            name = instruction.reg_name(memory.base)
            parts.append(name if name in ('ebp', 'esp') else state.get(name, '?'+name))
        if memory.index:
            name = instruction.reg_name(memory.index)
            parts.append(f"{state.get(name, '?'+name)}*{memory.scale}")
        if memory.disp or not parts:
            parts.append(hex(memory.disp & 0xffffffff) if memory.disp >= 0 or not parts else '-'+hex(-memory.disp))
        return '+'.join(parts).replace('+-', '-')

    def value(instruction, operand):
        if operand.type == X86_OP_IMM:
            return hex(operand.imm & 0xffffffff)
        if operand.type == X86_OP_REG:
            name = register(instruction, operand)
            return state.get(name, '?'+name)
        return '['+address(instruction, operand)+']'

    for instruction in instructions[:-1]:
        mnemonic, operands = instruction.mnemonic, instruction.operands
        destination = register(instruction, operands[0]) if operands and operands[0].type == X86_OP_REG else None
        if mnemonic == 'push':
            stack.append(value(instruction, operands[0]))
        elif mnemonic == 'pop':
            popped = stack.pop() if stack else '?'
            if destination:
                state[destination] = popped
        elif mnemonic in ('mov', 'movss', 'movd') and len(operands) == 2:
            if operands[0].type == X86_OP_MEM:
                target = address(instruction, operands[0])
                if target == 'esp' and stack:
                    stack[-1] = value(instruction, operands[1])
            else:
                state[destination] = value(instruction, operands[1])
        elif mnemonic in ('movzx', 'movsx'):
            state[destination] = ('u' if mnemonic == 'movzx' else 's')+str(operands[1].size*8) + \
                value(instruction, operands[1])
        elif mnemonic == 'lea':
            state[destination] = '&['+address(instruction, operands[1])+']'
        elif mnemonic == 'add' and destination == 'esp':
            del stack[len(stack)-operands[1].imm//4:]
        elif mnemonic == 'add' and destination and operands[1].type == X86_OP_IMM:
            state[destination] = f"({state.get(destination, '?'+destination)})+{hex(operands[1].imm)}"
        elif mnemonic == 'xorps' and operands[0].reg == operands[1].reg:
            state[destination] = '0.0'
        elif mnemonic == 'xor' and destination and operands[1].type == X86_OP_REG and \
                operands[0].reg == operands[1].reg:
            state[destination] = '0x0'
        elif mnemonic == 'cvttss2si':
            state[destination] = 'int('+value(instruction, operands[1])+')'
        elif mnemonic == 'cvtsi2ss':
            state[destination] = 'float('+value(instruction, operands[1])+')'
        elif mnemonic in ('dec', 'inc') and destination:
            state[destination] = f"({state.get(destination)}){'-1' if mnemonic == 'dec' else '+1'}"
        elif mnemonic in ('subss', 'addss', 'mulss', 'divss') and destination:
            state[destination] = f'({state.get(destination)} {mnemonic[:3]} {value(instruction, operands[1])})'
        elif mnemonic == 'call':
            target = operands[0].imm if operands[0].type == X86_OP_IMM else None
            if target == VECTOR:
                state['eax'] = state.get('ecx', '?ecx')
            elif target == ELEMENT:
                index = stack.pop() if stack else '?'
                state['eax'] = f"{state.get('ecx')}+4*{index}"
            else:
                notes.append('call '+(hex(target) if target else instruction.op_str))
                state['eax'] = 'ret('+(hex(target) if target else instruction.op_str)+')'
            state.pop('ecx', None)
            state.pop('edx', None)
        elif JUMPS.match(mnemonic):
            notes.append('branch@'+hex(instruction.address))
        elif destination:
            state[destination] = '?'+mnemonic
    return stack, state, notes


def call_arguments(text, site, count):
    start = text.function_start(site)
    if start is None:
        return {'site': hex(site), 'function': None}
    instructions = text.decode(start, site)
    if not instructions or instructions[-1].address != site:
        return {'site': hex(site), 'function': hex(start), 'decode': 'no-sync'}
    first = block_start(instructions)
    stack, state, notes = evaluate(instructions[first:])
    widened = len(stack) < count
    if widened:
        stack, state, notes = evaluate(instructions[max(0, len(instructions)-120):])
    return {'site': hex(site), 'function': hex(start), 'block': hex(instructions[first].address),
            'arguments': stack[-count:][::-1], 'ecx': state.get('ecx'), 'notes': notes, 'widened': widened}


def normalize(expression):
    expression = re.sub(r'\[ebp-0x[0-9a-f]+\]', 'LOCAL', expression or 'None')
    return re.sub(r'\[ebp\+0x[0-9a-f]+\]', 'ARG', expression)


def base_of(expression, field):
    for pattern in (r'^\[(.*)\+%s\]$', r'^u16\[(.*)\+%s\]$', r'^\((.*)\)\+%s$'):
        match = re.match(pattern % re.escape(field), expression)
        if match:
            return match.group(1)
    return None


def classify_pose_call(arguments):
    output, frame, prior, action, angles, head, keep, translate = arguments
    frame_base, prior_base = base_of(frame, '0xd0'), base_of(prior, '0xd4')
    action_base, angle_base, head_base = base_of(action, '0x2c'), base_of(angles, '0x164'), base_of(head, '0x170')
    objects = {b for b in (frame_base, prior_base, action_base, angle_base, head_base) if b}
    if frame_base and prior_base and action_base and angle_base and head_base and len(objects) == 1:
        state = 'object-fields'
    elif prior_base and action_base and angle_base and len({prior_base, action_base, angle_base}) == 1:
        state = 'object-prior-computed-frame'
    elif frame == '0.0' and prior == '0.0' and action == '0x0':
        state = 'bind-pose'
    elif re.match(r'^float\(\(int\(.*\)\)-1\)$', prior):
        state = 'prior-is-frame-minus-one'
    else:
        state = 'other'
    return {'output': 'bone-buffer' if output == hex(BONE_BUFFER) else 'other', 'state': state,
            'head': 'object+0x170' if head_base else ('angles' if head == angles else 'other'),
            'keep_root': keep, 'translate': translate}


def computed_frame_source(text, record):
    """Last store to the frame local before the call, as normalized text."""
    match = re.match(r'^\[ebp-(0x[0-9a-f]+)\]$', record['arguments'][1])
    if not match:
        return 'not-a-local'
    site, start = int(record['site'], 16), int(record['function'], 16)
    instructions = text.decode(start, site)
    target = f'dword ptr [ebp - {match.group(1)}],'
    for k in range(len(instructions)-2, -1, -1):
        if instructions[k].op_str.startswith(target):
            run = instructions[max(0, k-2):k+1]
            return normalize('; '.join(f'{i.mnemonic} {i.op_str}' for i in run)
                             .replace('dword ptr ', '').replace('ebp - ', 'ebp-').replace('ebp + ', 'ebp+'))
    return 'no-store-before-call'


def gl_listing(text, start, end, slots):
    """Ordered GL import and state-wrapper calls with immediate pushes."""
    events, pushes = [], []
    for instruction in text.linear(start, end):
        if instruction.mnemonic == 'push':
            pushes.append(instruction.op_str)
        if instruction.mnemonic != 'call':
            continue
        operand = instruction.operands[0]
        name = None
        if instruction.op_str.startswith('dword ptr [0x'):
            name = slots.get(int(instruction.op_str[11:-1], 16))
        elif operand.type == 2:
            name = STATE_WRAPPERS.get(operand.imm)
        if name:
            immediates = [p for p in reversed(pushes[-4:])]
            events.append({'address': hex(instruction.address), 'call': name, 'recent_pushes': immediates})
        pushes = []
    return events


def analyze(text_path, data_path, opengl32_path, glu32_path):
    text = Text(common.load_text(text_path))
    data = common.load_data(data_path)
    opengl = Path(opengl32_path).read_bytes()
    glu = Path(glu32_path).read_bytes()
    if hashlib.sha256(opengl).hexdigest() != OPENGL32_SHA256 or hashlib.sha256(glu).hexdigest() != GLU32_SHA256:
        raise ValueError('Wine DLL does not match the pinned Debian 8.0~repack-4 i386 build')
    report = {'text_sha256': common.TEXT_SHA256, 'data_sha256': common.DATA_SHA256,
              'opengl32_sha256': OPENGL32_SHA256, 'glu32_sha256': GLU32_SHA256}

    pose_records = [call_arguments(text, site, 8) for site in text.raw_calls(POSE)]
    for record in pose_records:
        if record.get('arguments'):
            record['class'] = classify_pose_call(record['arguments'])
    report['pose_callers'] = summarize_calls(pose_records, 8)
    report['pose_callers']['classes'] = {
        key: dict(collections.Counter(r['class'][key] for r in pose_records if 'class' in r).most_common())
        for key in ('output', 'state', 'head', 'keep_root', 'translate')}
    report['pose_callers']['computed_frame_sources'] = dict(collections.Counter(
        computed_frame_source(text, r) for r in pose_records
        if r.get('class', {}).get('state') == 'object-prior-computed-frame').most_common(8))
    report['pose_callers']['sites'] = pose_records

    tick_records = [call_arguments(text, site, 6) for site in text.raw_calls(TICK)]
    report['tick_callers'] = summarize_calls(tick_records, 6)
    report['tick_callers']['sites'] = tick_records

    consumers = {}
    for name, target in [('transform', TRANSFORM), ('render_mesh', RENDER_MESH), ('render_body', RENDER_BODY)] + \
            list(WRAPPERS.items()):
        sites = text.raw_calls(target)
        functions = collections.Counter(text.function_start(s) for s in sites)
        consumers[name] = {'target': hex(target), 'raw_calls': len(sites), 'functions': len(functions),
                           'top_functions': [[hex(f) if f else None, n] for f, n in functions.most_common(5)]}
    report['consumers'] = consumers

    opengl_slots = name_slots(data, *OPENGL32_SLOTS, opengl)
    glu_slots = name_slots(data, *GLU32_SLOTS, glu, base=GLU32_OBSERVED_BASE)
    report['imports'] = {'opengl32': opengl_slots, 'glu32': glu_slots,
                         'opengl32_named': sum(bool(s['name']) for s in opengl_slots),
                         'glu32_named': sum(bool(s['name']) for s in glu_slots),
                         'first_slot_is_static_import': {
                             'opengl32': opengl_slots[0]['name'] == STATIC_FIRST_IMPORT['opengl32'],
                             'glu32': glu_slots[0]['name'] == STATIC_FIRST_IMPORT['glu32']}}
    slots = {int(s['slot'], 16): s['name'] for s in opengl_slots+glu_slots if s['name']}
    report['import_call_sites'] = dict(sorted(
        ((name, len(text.raw_bytes(b'\xff\x15'+struct.pack('<I', slot)))) for slot, name in slots.items()),
        key=lambda item: -item[1]))
    begin_slot = next(slot for slot, name in slots.items() if name == 'glBegin')
    begins = []
    for site in text.raw_bytes(b'\xff\x15'+struct.pack('<I', begin_slot)):
        start = text.function_start(site)
        run = text.decode(start, site) if start is not None else []
        pushed = None
        if run and run[-1].address == site:
            for instruction in reversed(run[:-1]):  # the argument push must follow any earlier call
                if instruction.mnemonic == 'call' or JUMPS.match(instruction.mnemonic):
                    break
                if instruction.mnemonic == 'push':
                    pushed = instruction.op_str
                    break
        mode = GL_MODES.get(int(pushed, 16)) if pushed and re.match(r'^(0x)?[0-9a-f]+$', pushed) else None
        begins.append({'site': hex(site), 'function': hex(start) if start is not None else None,
                       'mode': mode or f'not-immediate:{pushed}'})
    report['glbegin_sites'] = {'count': len(begins), 'modes': dict(collections.Counter(
        b['mode'] if not b['mode'].startswith('not-immediate') else 'not-immediate' for b in begins)),
        'sites': begins}
    report['render_mesh_gl'] = gl_listing(text, RENDER_MESH, RENDER_BODY, slots)
    report['state_wrappers'] = {hex(start): {'label': label, 'gl': gl_listing(text, start, end, slots)}
                                for (start, label), end in zip(sorted(STATE_WRAPPERS.items()),
                                                               [s for s, _ in sorted(STATE_WRAPPERS.items())][1:] +
                                                               [0x0184ad4c])
                                if start >= 0x0184a699}
    return report


def summarize_calls(records, count):
    positions = []
    for k in range(count):
        positions.append(dict(collections.Counter(normalize(r['arguments'][k]) for r in records
                                                  if r.get('arguments')).most_common(10)))
    return {'raw_candidates': len(records),
            'synced': sum(bool(r.get('arguments')) for r in records),
            'functions': len({r.get('function') for r in records}),
            'widened': sum(bool(r.get('widened')) for r in records),
            'argument_patterns': positions,
            'ecx': dict(collections.Counter(normalize(r.get('ecx')) for r in records).most_common(6))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--opengl32', type=Path, required=True, help='Debian libwine 8.0~repack-4 i386 opengl32.dll')
    parser.add_argument('--glu32', type=Path, required=True, help='Debian libwine 8.0~repack-4 i386 glu32.dll')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.text, args.data, args.opengl32, args.glu32)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(report, indent=1)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
