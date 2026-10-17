#!/usr/bin/env python3
"""Static lifter for the per-type action tables of OpenMonsterModel (NATIVE-ACTOR-001).

Reads only the pinned restored text (0x00401000) and second image section
(0x01a7c000). Nothing here executes client code; the output is checked against
the client's actual instructions by scripts/validate_actors.py.

OpenMonsterModel 0x0180b0f4 ends in two regular switch statements on the
monster type: 0x0180cd7c (byte table 0x0181f588, jump table 0x0181f28c) and
0x01812e53 (byte table 0x0181fa28, jump table 0x0181f744), with a fixed rule
between them. Their case blocks consist only of constant stores into the
model's action records (directly through Actions = model+0x30, through
SetActionSpeed 0x012bd437 / SetActionLoop 0x012bd471, or through the action
pointer returned by GetAction 0x012bcf9d / ActionAt 0x00eaaa44), constant
stores into model fields, and calls to the sound and texture loaders.

The lifter interprets that restricted instruction set concretely for one type
at a time (the type is the only input), from 0x0180cd7c to the epilogue
0x0181f250, with symbolic model/action pointers. Any instruction outside the
set raises Unsupported, so a case that does not fit is reported rather than
guessed. Loader calls are recorded but not part of the generated table.

  --emit-c PATH   write the generated table header (reconstructed/actors/monster_open_table.h)
  --json PATH     write the per-type operations as JSON
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402

LIFT_START, LIFT_STOP = 0x0180cd7c, 0x0181f250
MONSTER_MODEL_BASE = 0x7a5
MONSTER_TYPES = 0x259           # Type + 0x7a5 stays below the first NPC model 0x9fe
OPEN_MONSTER = (0x0180b0f4, 0x0181f25c, '')  # digest filled from the pinned text below
MANAGER, MODEL_AT, ACTION_AT = 0x00966cc4, 0x00eaa8cf, 0x00eaaa44
SET_SPEED, SET_LOOP, GET_ACTION = 0x012bd437, 0x012bd471, 0x012bcf9d
STRING_CTOR, STRING_DTOR, ACCESS_MODEL = 0x0094997e, 0x008e83a0, 0x018202b4
THISCALL = {STRING_CTOR: 1, STRING_DTOR: 0, MODEL_AT: 1, ACTION_AT: 2, SET_SPEED: 2, SET_LOOP: 2, GET_ACTION: 1}
LOADERS = {0x00a6ab76: 'load_wave', 0x0185baac: 'load_bitmap', 0x018329fa: 'action_sounds',
           0x0181fbe9: 'open_texture', ACCESS_MODEL: 'access_model'}
NUMBER = re.compile(r'-?(0x[0-9a-f]+|\d+)')


class Unsupported(Exception):
    pass


class Image:
    def __init__(self, text, data):
        self.text, self.data = text, data
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)

    def read(self, address, size):
        if am.TEXT_BASE <= address and address+size <= am.TEXT_BASE+len(self.text):
            return self.text[address-am.TEXT_BASE:address-am.TEXT_BASE+size]
        if am.DATA_BASE <= address and address+size <= am.DATA_BASE+len(self.data):
            return self.data[address-am.DATA_BASE:address-am.DATA_BASE+size]
        raise Unsupported(f'read outside image {address:#x}')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def cstring(self, address):
        out = bytearray()
        while True:
            byte = self.read(address+len(out), 1)
            if byte == b'\0':
                return out.decode('latin1')
            out += byte

    def instruction(self, address):
        return next(self.md.disasm(self.read(address, 16), address))


class Lifter:
    def __init__(self, image, type_, start=LIFT_START, stop=LIFT_STOP):
        self.image, self.type, self.pc, self.stop = image, type_, start, stop
        self.own = type_+MONSTER_MODEL_BASE
        self.reg = {'eax': None, 'ecx': None, 'edx': None}
        self.xmm0 = None
        self.stack = []
        self.frame = {8: ('int', type_), -0x10: ('model', self.own), -0x20: ('int', self.own)}
        self.flags = None
        self.ops, self.calls = [], []

    def operand(self, text):
        m = re.fullmatch(r'dword ptr \[ebp ([+-]) (0x[0-9a-f]+|\d+)\]', text)
        if m:
            offset = int(m.group(2), 0)*(1 if m.group(1) == '+' else -1)
            if offset not in self.frame:
                raise Unsupported(f'frame read {offset:#x}')
            return self.frame[offset]
        if text in self.reg:
            return self.reg[text]
        if NUMBER.fullmatch(text):
            return ('int', int(text, 0) & 0xffffffff)
        raise Unsupported(text)

    def run(self):
        steps = 0
        while self.pc != self.stop:
            steps += 1
            if steps > 100000:
                raise Unsupported('step limit')
            instruction = self.image.instruction(self.pc)
            self.pc = self.step(instruction, self.pc+instruction.size)
        return self.ops

    def frame_offset(self, text):
        m = re.fullmatch(r'(?:dword|byte) ptr \[ebp ([+-]) (0x[0-9a-f]+)\]', text)
        return int(m.group(2), 16)*(1 if m.group(1) == '+' else -1) if m else None

    def step(self, ins, nxt):
        m, o, R = ins.mnemonic, ins.op_str, self.reg
        where = f'{ins.address:#x} {m} {o}'
        if m == 'nop':
            return nxt
        if m == 'push':
            self.stack.append(self.operand(o))
            return nxt
        if m == 'pop':
            R[o] = self.stack.pop()
            return nxt
        if m == 'add':
            dst, value = o.split(', ')
            if dst == 'esp':
                del self.stack[len(self.stack)-int(value, 0)//4:]
                return nxt
            if dst in R and NUMBER.fullmatch(value):
                R[dst] = ('int', (R[dst][1]+int(value, 0)) & 0xffffffff)
                return nxt
            raise Unsupported(where)
        if m in ('or', 'mov') and o.startswith('dword ptr [ebp - 4], '):
            return nxt  # structured-exception state index
        if m == 'mov':
            dst, src = o.split(', ', 1)
            offset = self.frame_offset(dst)
            if offset is not None and (src in R or NUMBER.fullmatch(src)):
                self.frame[offset] = self.operand(src)
                return nxt
            if dst in R and (src in R or src.startswith('dword ptr [ebp') or NUMBER.fullmatch(src)):
                R[dst] = self.operand(src)
                return nxt
            mm = re.fullmatch(r'(\w+), dword ptr \[(\w+) \+ 0x30\]', o)
            if mm:
                base = R[mm.group(2)]
                if not base or base[0] != 'model':
                    raise Unsupported(where)
                R[mm.group(1)] = ('actions', base[1])
                return nxt
            mm = re.fullmatch(r'byte ptr \[ecx \+ eax\], (\w+)', o)
            if mm:
                self.raw(R['ecx'], R['eax'], 0, 'u8', int(mm.group(1), 0) & 0xff, where)
                return nxt
            mm = re.fullmatch(r'(byte|dword) ptr \[eax \+ (0x[0-9a-f]+)\], (\w+)', o)
            if mm and R['eax'] and R['eax'][0] == 'model':
                size = 'u8' if mm.group(1) == 'byte' else 'u32'
                self.ops.append(('field', R['eax'][1], int(mm.group(2), 16), size,
                                 int(mm.group(3), 0) & (0xff if size == 'u8' else 0xffffffff)))
                return nxt
            raise Unsupported(where)
        if m == 'lea':
            mm = re.fullmatch(r'(\w+), \[ebp - (0x[0-9a-f]+)\]', o)
            if not mm:
                raise Unsupported(where)
            R[mm.group(1)] = ('local', -int(mm.group(2), 16))
            return nxt
        if m == 'shl':
            dst, n = o.split(', ')
            R[dst] = ('int', (R[dst][1] << int(n, 0)) & 0xffffffff)
            return nxt
        if m == 'imul':
            dst, src, n = o.split(', ')
            R[dst] = ('int', (R[src][1]*int(n, 0)) & 0xffffffff)
            return nxt
        if m in ('dec', 'inc'):
            R[o] = ('int', (R[o][1]+(1 if m == 'inc' else -1)) & 0xffffffff)
            return nxt
        if m == 'movss':
            dst, src = o.split(', ')
            if dst == 'xmm0':
                mm = re.fullmatch(r'dword ptr \[(0x[0-9a-f]+)\]', src)
                if not mm:
                    raise Unsupported(where)
                self.xmm0 = ('float', self.image.u32(int(mm.group(1), 16)))
                return nxt
            if dst == 'dword ptr [esp]':
                self.stack[-1] = self.xmm0
                return nxt
            if dst == 'dword ptr [ecx + eax + 4]':
                self.raw(R['ecx'], R['eax'], 4, 'u32', self.xmm0[1], where)
                return nxt
            if dst == 'dword ptr [eax + 4]' and R['eax'] and R['eax'][0] == 'action':
                self.ops.append(('action_speed', R['eax'][1], R['eax'][2], self.xmm0[1]))
                return nxt
            raise Unsupported(where)
        if m == 'cmp':
            a, b = o.split(', ')
            self.flags = (self.operand(a)[1], self.operand(b)[1])
            return nxt
        if m in ('je', 'jne', 'ja', 'jb', 'jae', 'jbe', 'jg', 'jl', 'jge', 'jle'):
            a, b = self.flags
            sa, sb = (a ^ 0x80000000)-0x80000000, (b ^ 0x80000000)-0x80000000
            take = {'je': a == b, 'jne': a != b, 'ja': a > b, 'jb': a < b, 'jae': a >= b, 'jbe': a <= b,
                    'jg': sa > sb, 'jl': sa < sb, 'jge': sa >= sb, 'jle': sa <= sb}[m]
            return int(o, 16) if take else nxt
        if m == 'movzx':
            mm = re.fullmatch(r'eax, byte ptr \[eax \+ (0x[0-9a-f]+)\]', o)
            if not mm:
                raise Unsupported(where)
            R['eax'] = ('int', self.image.read(int(mm.group(1), 16)+R['eax'][1], 1)[0])
            return nxt
        if m == 'jmp':
            mm = re.fullmatch(r'dword ptr \[eax\*4 \+ (0x[0-9a-f]+)\]', o)
            if mm:
                return self.image.u32(int(mm.group(1), 16)+4*R['eax'][1])
            return int(o, 16)
        if m == 'call':
            return self.call(int(o, 16), nxt)
        raise Unsupported(where)

    def raw(self, actions, index, field, size, value, where):
        if not actions or actions[0] != 'actions' or index[0] != 'int' or index[1] % 16:
            raise Unsupported(where)
        self.ops.append(('raw', actions[1], index[1]//16, field, size, value))

    def call(self, target, nxt):
        R = self.reg
        if target == MANAGER:
            R['eax'] = ('manager',)
            return nxt
        if target in THISCALL:
            count = THISCALL[target]
            arguments = list(reversed(self.stack[len(self.stack)-count:])) if count else []  # call order
            del self.stack[len(self.stack)-count:]
            this = R['ecx']
            if target == MODEL_AT:
                R['eax'] = ('model', arguments[0][1])
            elif target == ACTION_AT:
                R['eax'] = ('action', arguments[0][1], arguments[1][1])
            elif target == GET_ACTION:
                R['eax'] = ('action', this[1], arguments[0][1])
            elif target == SET_SPEED:
                self.ops.append(('speed', this[1], arguments[0][1], arguments[1][1]))
            elif target == SET_LOOP:
                self.ops.append(('loop', this[1], arguments[0][1], arguments[1][1] & 0xff))
            return nxt
        if target not in LOADERS:
            raise Unsupported(f'call {target:#x}')
        self.calls.append((LOADERS[target], [a[1] if a and a[0] in ('int', 'float') else None
                                             for a in reversed(self.stack)]))
        R['eax'] = ('ret', target)
        return nxt


def lift_all(image, types=range(MONSTER_TYPES)):
    result = {}
    for type_ in types:
        lifter = Lifter(image, type_)
        lifter.run()
        result[type_] = {'ops': lifter.ops, 'loader_calls': [name for name, _ in lifter.calls]}
    return result


KIND = {'speed': 'MU_MONSTER_OP_SPEED', 'loop': 'MU_MONSTER_OP_LOOP', 'action_speed': 'MU_MONSTER_OP_ACTION_SPEED',
        ('raw', 'u32'): 'MU_MONSTER_OP_RAW32', ('raw', 'u8'): 'MU_MONSTER_OP_RAW8',
        ('field', 'u32'): 'MU_MONSTER_OP_FIELD32', ('field', 'u8'): 'MU_MONSTER_OP_FIELD8'}


def encode(type_, op):
    own = type_+MONSTER_MODEL_BASE
    kind = op[0]
    if kind in ('speed', 'loop', 'action_speed'):
        return (KIND[kind], op[1]-own, op[2], 0, op[3])
    if kind == 'raw':
        _, model, action, field, size, value = op
        return (KIND[('raw', size)], model-own, action, field, value)
    _, model, offset, size, value = op
    return (KIND[('field', size)], model-own, 0, offset, value)


def emit_c(lifted, text_digest):
    blocks, block_index, type_block = [], {}, []
    for type_ in sorted(lifted):
        encoded = tuple(encode(type_, op) for op in lifted[type_]['ops'])
        if encoded not in block_index:
            block_index[encoded] = len(blocks)
            blocks.append(encoded)
        type_block.append(block_index[encoded])
    ops, starts = [], []
    for block in blocks:
        starts.append(len(ops))
        ops.extend(block)
    starts.append(len(ops))
    lines = ['/* Generated by scripts/actor_static.py from the restored client text',
             f' * (SHA-256 {text_digest}).',
             ' * Do not edit. Per-type action operations of OpenMonsterModel 0x0180b0f4 after',
             ' * its default speeds: switch 0x0180cd7c, the loop rule at 0x01812e18 and switch',
             ' * 0x01812e53, in client order. Fields: kind, model index relative to the opened',
             ' * model, action, byte offset, value (binary32 bits for speeds). Validated against',
             ' * the client instructions by scripts/validate_actors.py. */',
             '#ifndef MU_MONSTER_OPEN_TABLE_H', '#define MU_MONSTER_OPEN_TABLE_H', '',
             f'#define MU_MONSTER_TABLE_TYPES {len(type_block)}',
             f'#define MU_MONSTER_TABLE_BLOCKS {len(blocks)}',
             f'#define MU_MONSTER_TABLE_OPS {len(ops)}', '',
             'static const mu_monster_op mu_monster_ops[MU_MONSTER_TABLE_OPS] = {']
    for kind, model, action, offset, value in ops:
        lines.append(f'    {{{kind}, {model}, {action}, {offset:#x}, {value:#010x}u}},')
    lines += ['};', '', 'static const uint16_t mu_monster_block_start[MU_MONSTER_TABLE_BLOCKS + 1] = {']
    for i in range(0, len(starts), 12):
        lines.append('    ' + ', '.join(str(s) for s in starts[i:i+12]) + ',')
    lines += ['};', '', 'static const uint16_t mu_monster_type_block[MU_MONSTER_TABLE_TYPES] = {']
    for i in range(0, len(type_block), 16):
        lines.append('    ' + ', '.join(str(s) for s in type_block[i:i+16]) + ',')
    lines += ['};', '', '#endif', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--emit-c')
    parser.add_argument('--json')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    image = Image(text, data)
    lifted = lift_all(image)
    if args.emit_c:
        Path(args.emit_c).write_text(emit_c(lifted, am.TEXT_SHA256))
    summary = {'types': len(lifted), 'ops': sum(len(v['ops']) for v in lifted.values()),
               'loader_calls': sum(len(v['loader_calls']) for v in lifted.values())}
    if args.json:
        Path(args.json).write_text(json.dumps({'summary': summary, 'types': {str(k): v for k, v in lifted.items()}},
                                              indent=1))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
