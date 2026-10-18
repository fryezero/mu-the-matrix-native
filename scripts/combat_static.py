#!/usr/bin/env python3
"""Static lifter for the Player attack-speed setter (NATIVE-COMBAT-001).

Reads only the pinned restored text (0x00401000) and second image section
(0x01a7c000). Nothing here executes client code; the generated C is compared
with the client's actual instructions by scripts/validate_combat.py.

SetAttackSpeed 0x0138dc60(float attack_speed, float magic_speed), cdecl, is
called by the hero attack-speed adjustment 0x0138d9cf. Its body is a long
straight-line sequence of binary32 SSE expressions over its two arguments and
constants, stored into the PlaySpeed field (+4) of Player action records
obtained through the model container getter 0x00966cc4 and the action getter
0x00d33153(action). It has five counted loops over action ranges and one
two-way branch (attack_speed >= 288 selects the constant 1.148).

The lifter interprets that restricted instruction set: SSE moves and
arithmetic on xmm0/xmm1, stack locals, integer loop counters, the two getter
calls and the stores through the returned action pointer. A comiss + jb pair
runs both paths to their join and merges the differing locals into a select.
Anything else raises Unsupported. The output keeps the client's store order
and its operation order, so the C, built with -ffp-contract=off, rounds like
the client.

  --emit-c PATH   write reconstructed/combat/attack_speed_table.h
  --json PATH     write the lifted stores as JSON
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

SET_ATTACK_SPEED = 0x0138dc60
SET_ATTACK_SPEED_END = 0x0138f92f      # exclusive: the next routine (SetPlayerShock) starts here
MANAGER, ACTION_GETTER = 0x00966cc4, 0x00d33153
MEMORY = re.compile(r'dword ptr \[(?P<base>ebp|eax)(?: (?P<sign>[+-]) (?P<off>0x[0-9a-f]+|\d+))?\]$')
ABSOLUTE = re.compile(r'dword ptr \[(0x[0-9a-f]+)\]$')


class Unsupported(Exception):
    pass


def f32_bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


class Lifter:
    def __init__(self, text, data):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.text, self.data = text, data
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)
        self.stores = []          # (action, expression) in client order
        self.calls = {MANAGER: 0, ACTION_GETTER: 0}

    def read(self, address, size):
        if am.TEXT_BASE <= address and address+size <= am.TEXT_BASE+len(self.text):
            return self.text[address-am.TEXT_BASE:address-am.TEXT_BASE+size]
        if am.DATA_BASE <= address and address+size <= am.DATA_BASE+len(self.data):
            return self.data[address-am.DATA_BASE:address-am.DATA_BASE+size]
        raise Unsupported(f'read outside the image at {address:#x}')

    def instruction(self, address):
        return next(self.md.disasm(self.read(address, 16), address))

    # -- operands ---------------------------------------------------------------
    @staticmethod
    def memory(operand):
        m = MEMORY.match(operand)
        if not m:
            return None
        offset = int(m.group('off'), 0) if m.group('off') else 0
        return m.group('base'), (-offset if m.group('sign') == '-' else offset)

    def load(self, state, operand):
        a = ABSOLUTE.match(operand)
        if a:
            return ('const', struct.unpack('<I', self.read(int(a.group(1), 16), 4))[0])
        mem = self.memory(operand)
        if mem and mem[0] == 'ebp':
            if mem[1] == 8:
                return ('arg', 'attack_speed')
            if mem[1] == 0xc:
                return ('arg', 'magic_speed')
            if mem[1] in state['locals']:
                return state['locals'][mem[1]]
            raise Unsupported(f'read of unset local ebp{mem[1]:+#x}')
        if operand in ('xmm0', 'xmm1'):
            return state[operand]
        raise Unsupported(f'operand {operand}')

    # -- interpreter --------------------------------------------------------------
    def run(self, pc, state, stop=None):
        """Interprets from pc; returns the pc at which it stopped (stop, or the RET)."""
        while True:
            if stop is not None and pc == stop:
                return pc
            if not SET_ATTACK_SPEED <= pc < SET_ATTACK_SPEED_END:
                raise Unsupported(f'pc {pc:#x} outside the routine')
            ins = self.instruction(pc)
            nxt = pc+ins.size
            m, o = ins.mnemonic, ins.op_str
            ops = [x.strip() for x in o.split(',')] if o else []
            if (m, o) in (('push', 'ebp'), ('mov', 'ebp, esp')) or (m == 'sub' and ops[0] == 'esp'):
                pc = nxt
            elif m in ('leave',):
                pc = nxt
            elif m == 'ret':
                return pc
            elif m == 'movss':
                dst, src = ops
                if dst in ('xmm0', 'xmm1'):
                    state[dst] = self.load(state, src)
                else:
                    mem = self.memory(dst)
                    if mem and mem[0] == 'ebp' and mem[1] < 0:
                        state['locals'][mem[1]] = state[src]
                    elif mem and mem[0] == 'eax' and mem[1] == 4 and isinstance(state['eax'], tuple) \
                            and state['eax'][0] == 'action':
                        self.stores.append((state['eax'][1], state[src]))
                    else:
                        raise Unsupported(f'store {o} at {pc:#x}')
                pc = nxt
            elif m in ('mulss', 'addss', 'subss', 'divss'):
                dst, src = ops
                state[dst] = (m[:3], state[dst], self.load(state, src))
                pc = nxt
            elif m == 'push':
                value = int(o, 0) if re.fullmatch(r'0x[0-9a-f]+|\d+', o) else None
                if value is None:
                    mem = self.memory(o)
                    if not (mem and mem[0] == 'ebp' and mem[1] in state['ints']):
                        raise Unsupported(f'push {o} at {pc:#x}')
                    value = state['ints'][mem[1]]
                state['stack'].append(value)
                pc = nxt
            elif m == 'call':
                target = int(o, 16)
                if target == MANAGER:
                    state['eax'] = ('manager',)
                elif target == ACTION_GETTER:
                    if state['ecx'] != ('manager',):
                        raise Unsupported('action getter without the manager')
                    state['eax'] = ('action', state['stack'].pop())
                else:
                    raise Unsupported(f'call {o} at {pc:#x}')
                self.calls[target] += 1
                pc = nxt
            elif m == 'mov' and ops == ['ecx', 'eax']:
                state['ecx'] = state['eax']
                pc = nxt
            elif m == 'mov' and ops[0].startswith('dword ptr [ebp') and re.fullmatch(r'0x[0-9a-f]+|\d+', ops[1]):
                state['ints'][self.memory(ops[0])[1]] = int(ops[1], 0)
                pc = nxt
            elif m == 'mov' and ops[0] == 'eax' and ops[1].startswith('dword ptr [ebp'):
                state['eax'] = state['ints'][self.memory(ops[1])[1]]
                pc = nxt
            elif m == 'inc' and o == 'eax':
                state['eax'] += 1
                pc = nxt
            elif m == 'mov' and ops[0].startswith('dword ptr [ebp') and ops[1] == 'eax':
                state['ints'][self.memory(ops[0])[1]] = state['eax']
                pc = nxt
            elif m == 'cmp' and ops[0].startswith('dword ptr [ebp'):
                state['flags'] = ('int', state['ints'][self.memory(ops[0])[1]], int(ops[1], 0))
                pc = nxt
            elif m == 'jg' and state['flags'][0] == 'int':
                _, a, b = state['flags']
                pc = int(o, 16) if a > b else nxt
            elif m == 'jmp':
                pc = int(o, 16)
            elif m == 'comiss' and ops[0] == 'xmm0':
                state['flags'] = ('float', state['xmm0'], self.load(state, ops[1]))
                pc = nxt
            elif m == 'jb' and state['flags'][0] == 'float':
                # taken when xmm0 < k or unordered; fall through when xmm0 >= k
                _, x, k = state['flags']
                fall = dict(state, locals=dict(state['locals']), ints=dict(state['ints']), stack=list(state['stack']))
                taken = dict(state, locals=dict(state['locals']), ints=dict(state['ints']), stack=list(state['stack']))
                join = self.fall_join(nxt)
                self.run(nxt, fall, stop=join)
                self.run(int(o, 16), taken, stop=join)
                merged = {}
                for key in set(fall['locals']) | set(taken['locals']):
                    a, b = fall['locals'].get(key), taken['locals'].get(key)
                    merged[key] = a if a == b else ('select_ge', x, k, a, b)
                state['locals'] = merged
                state['xmm0'] = ('select_ge', x, k, fall['xmm0'], taken['xmm0'])
                pc = join
            else:
                raise Unsupported(f'{m} {o} at {pc:#x}')

    def fall_join(self, pc):
        """The fall-through path of a two-way branch ends in a forward jmp to the join."""
        for _ in range(64):
            ins = self.instruction(pc)
            if ins.mnemonic == 'jmp':
                return int(ins.op_str, 16)
            pc += ins.size
        raise Unsupported('no join for the float branch')

    def lift(self):
        state = {'xmm0': None, 'xmm1': None, 'eax': None, 'ecx': None, 'locals': {}, 'ints': {}, 'stack': [],
                 'flags': None}
        end = self.run(SET_ATTACK_SPEED, state)
        if state['stack']:
            raise Unsupported('unbalanced pushes')
        return end


def c_expression(expr):
    kind = expr[0]
    if kind == 'arg':
        return 'a' if expr[1] == 'attack_speed' else 'm'
    if kind == 'const':
        value = from_bits(expr[1])
        return f'mu_f32(0x{expr[1]:08x}u) /* {value!r} */'
    if kind in ('mul', 'add', 'sub', 'div'):
        op = {'mul': '*', 'add': '+', 'sub': '-', 'div': '/'}[kind]
        return f'({c_expression(expr[1])} {op} {c_expression(expr[2])})'
    if kind == 'select_ge':
        return (f'({c_expression(expr[1])} >= {c_expression(expr[2])} ? {c_expression(expr[3])} : '
                f'{c_expression(expr[4])})')
    raise ValueError(kind)


def json_expression(expr):
    return [expr[0]] + [json_expression(x) if isinstance(x, tuple) else x for x in expr[1:]]


def emit_c(stores, text_digest):
    lines = ['/* Generated by scripts/combat_static.py from SetAttackSpeed 0x0138dc60 (restored text',
             f' * SHA-256 {text_digest}). Do not edit: regenerate with --emit-c.',
             ' *',
             ' * One statement per store of the client, in the client\'s order; a and m are',
             ' * the routine\'s two binary32 arguments (attack speed, magic speed) and s the',
             ' * PlaySpeed of each Player action (index = action). Build with',
             ' * -ffp-contract=off. */',
             '#ifndef MU_COMBAT_ATTACK_SPEED_TABLE_H',
             '#define MU_COMBAT_ATTACK_SPEED_TABLE_H',
             '',
             f'#define MU_ATTACK_SPEED_STORES {len(stores)}',
             '',
             'static void mu_attack_speed_body(float a, float m, float *s)',
             '{',
             '    (void)m;']
    for action, expr in stores:
        lines.append(f'    s[0x{action:03x}] = {c_expression(expr)};')
    lines += ['}', '', '#endif', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default='evidence/x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', default='evidence/image-data-run10/data-capture-10/client-image-data.bin')
    parser.add_argument('--emit-c')
    parser.add_argument('--json')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    lifter = Lifter(text, data)
    end = lifter.lift()
    body = text[SET_ATTACK_SPEED-am.TEXT_BASE:end+1-am.TEXT_BASE]
    report = {'routine': hex(SET_ATTACK_SPEED), 'ret': hex(end), 'body_sha256': hashlib.sha256(body).hexdigest(),
              'stores': len(lifter.stores), 'distinct_actions': len({a for a, _ in lifter.stores}),
              'calls': {hex(k): v for k, v in lifter.calls.items()}}
    print(json.dumps(report, indent=1))
    if args.emit_c:
        Path(args.emit_c).write_text(emit_c(lifter.stores, am.TEXT_SHA256))
    if args.json:
        Path(args.json).write_text(json.dumps({'report': report, 'stores': [
            [a, json_expression(e)] for a, e in lifter.stores]}, indent=0))


if __name__ == '__main__':
    main()
