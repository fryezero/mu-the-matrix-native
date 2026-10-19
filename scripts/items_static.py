#!/usr/bin/env python3
"""Static lifters for two ground-item routines (NATIVE-ITEMS-001).

Reads only the pinned restored text (0x00401000) and second image section
(0x01a7c000). Nothing here executes client code; the generated C is compared
with the client's actual instructions by scripts/validate_items.py (families
item_angle and item_name).

1. ItemAngle 0x01802a66(OBJECT *o), cdecl: the resting pose of a dropped item.
   MoveItems 0x017ea1aa calls it when the item lands and CreateItem
   0x016daa27 once at creation. A long chain of type tests writes the object's
   Angle (+0x164, through the vec3 index helper 0x00cfc922) and Scale (+0xa0),
   with a few tests of the Item.bmd record (item-script singleton 0x00cd4ea8:
   record 0x00cd5d29, kind-A / kind-B predicates 0x00cd5fac / 0x00cd6017), a
   range helper 0x0095c61f and one per-index table lookup (singleton
   0x009c2aea, lookup 0x01807c32: +0x25c scale, +0x260 angle z).

2. The name builder 0x017ea422(ITEM_t *item), cdecl, called at the end of
   CreateItem: the label colour class (item +0x55c, mapped to an HTML colour by
   0x00c84f00) and the label text (item +0x509, through sprintf 0x009619dd,
   strcat 0x01983aa0, strcpy 0x01983a90 and GlobalText 0x0095f027), then the
   hudPlayerName addItem call 0x00c83e2a.

The lifters translate a routine basic block by basic block over the closed
instruction subset the debug-style code uses (loads of the argument and of
locals, compares of fields and locals, conditional and plain jumps, stores of
constants, the named calls). Registers do not live across blocks (every block
reloads them); anything outside the subset raises Unsupported. Every client
block becomes a label, so the C takes exactly the client's path. One span of
the name builder (std::string temporaries of the plain-item path) is replaced
by a hand-written statement list, labelled in the output.

  --emit-angle PATH   write reconstructed/items/item_angle_table.h
  --emit-name PATH    write reconstructed/items/item_name_table.h
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

ITEM_ANGLE = 0x01802a66
NAME_BUILDER = 0x017ea422
VEC_INDEX = 0x00cfc922
SCRIPT, RECORD, KIND_A, KIND_B = 0x00cd4ea8, 0x00cd5d29, 0x00cd5fac, 0x00cd6017
PET_TABLE, PET_LOOKUP = 0x009c2aea, 0x01807c32
IN_RANGE = 0x0095c61f
GLOBAL_TEXT, TEXT_TABLE = 0x0095f027, 0x06fbab48
SPRINTF, STRCAT, STRCPY = 0x009619dd, 0x01983aa0, 0x01983a90
ITEM_ATTR, IS_KIND_A, IS_TYPE, IS_KIND_B = 0x00ccc591, 0x0095fc2e, 0x0095fbeb, 0x00987982
ITEM_OPTION, KIND_A2_TYPE2 = 0x00cd0995, 0x00cd2175
SET_TABLE, SET_LOOKUP = 0x06fbae4c, 0x011447ac
TABLE_1E, TABLE_1E_GET = 0x06fbb138, 0x00961620
TEXT_67 = 0x011753c3
LEVEL_TABLE, LEVEL_TABLE_GET, LEVEL_KEYS = 0x06fbb664, 0x011427c7, 0x01cf15bc
CSTR = 0x008e7940
GL_COLOR3F_IAT = 0x01a7c76c
LABEL_HOLDER, HOLDER_LOCK, HOLDER_VALID, HOLDER_GET, HOLDER_RELEASE = 0x01d22c60, 0x009a19ae, 0x009a1a51, 0x009a1a74, \
    0x009a1a3c
LABEL_ADD = 0x00c83e2a
OBJ_TYPE, OBJ_ANGLE, OBJ_SCALE = 0x5c, 0x164, 0xa0
JCC = {'je': '==', 'jne': '!=', 'jl': '<', 'jle': '<=', 'jg': '>', 'jge': '>='}


class Unsupported(Exception):
    pass


def f32(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def c_string(text):
    out = ''
    for ch in text:
        if ch in '\\"':
            out += '\\' + ch
        elif 32 <= ord(ch) < 127:
            out += ch
        else:
            out += f'\\x{ord(ch):02x}'
    return f'"{out}"'


class Image:
    def __init__(self, text, data):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.text, self.data = text, data
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)

    def read(self, address, size):
        if am.TEXT_BASE <= address and address+size <= am.TEXT_BASE+len(self.text):
            return self.text[address-am.TEXT_BASE:address-am.TEXT_BASE+size]
        if am.DATA_BASE <= address and address+size <= am.DATA_BASE+len(self.data):
            return self.data[address-am.DATA_BASE:address-am.DATA_BASE+size]
        raise Unsupported(f'read outside the image at {address:#x}')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def cstring(self, address):
        out = bytearray()
        while True:
            b = self.read(address+len(out), 1)
            if b == b'\0':
                return out.decode('latin1')
            out += b

    def routine(self, start):
        """Linear decode to the RET at or after every forward jump."""
        out, far = [], start
        for ins in self.md.disasm(self.read(start, 0x8000), start):
            out.append(ins)
            if ins.mnemonic.startswith('j') and ins.op_str.startswith('0x'):
                far = max(far, int(ins.op_str, 16))
            if ins.mnemonic == 'ret' and ins.address >= far:
                return out
        raise Unsupported('no end of routine')


MEM = re.compile(r'(?P<size>byte|word|dword) ptr \[(?P<base>e[a-d]x|ebp)(?: (?P<sign>[+-]) (?P<off>0x[0-9a-f]+|\d+))?\]$')
SCALED = re.compile(r'dword ptr \[eax\*4 \+ (0x[0-9a-f]+)\]$')
ABS = re.compile(r'dword ptr \[(0x[0-9a-f]+)\]$')
NUM = re.compile(r'-?(0x[0-9a-f]+|\d+)$')


def mem(operand):
    m = MEM.match(operand)
    if not m:
        return None
    off = int(m.group('off'), 0) if m.group('off') else 0
    return m.group('size'), m.group('base'), -off if m.group('sign') == '-' else off


def num(operand):
    if not NUM.match(operand):
        return None
    value = int(operand, 0)
    return value - (1 << 32) if value >= 0x80000000 else value


def hexi(value):
    return f'0x{value:x}' if value >= 0 else str(value)


class Lifter:
    """Block-by-block translation. Values are tuples whose first element is a kind; ('int', expr) and
    ('bool', expr) carry a C expression. Subclasses supply load/call/store semantics."""

    routine_start = None
    manual = {}          # block start -> (end, [C lines], {label targets the lines jump to})

    def __init__(self, image):
        self.image = image
        self.ins = image.routine(self.routine_start)
        self.end = self.ins[-1].address
        targets = {self.routine_start}
        for i in self.ins:
            if i.mnemonic.startswith('j'):
                if not i.op_str.startswith('0x'):
                    raise Unsupported(f'indirect jump at {i.address:#x}')
                targets.add(int(i.op_str, 16))
        for start, (end, _, _) in self.manual.items():
            targets = {t for t in targets if not start < t < end} | {start, end}
        self.targets = targets
        self.stats = {'blocks': 0}

    def count(self, key, n=1):
        self.stats[key] = self.stats.get(key, 0) + n

    def block_code(self, start, stop):
        st = {'eax': None, 'ecx': None, 'edx': None, 'xmm0': None, 'stack': [], 'flags': None}
        out = []
        for ins in self.ins:
            if ins.address < start:
                continue
            if ins.address >= stop:
                break
            m, o, a = ins.mnemonic, ins.op_str, ins.address
            ops = [x.strip() for x in o.split(',')] if o else []
            if self.prologue(m, o, ops):
                continue
            if m == 'ret':
                out.append(self.ret_statement())
                return out, True
            if m in JCC:
                if st['flags'] is None:
                    raise Unsupported(f'{m} without flags at {a:#x}')
                lhs, rhs = st['flags']
                out.append(f'    if ({lhs} {JCC[m]} {rhs}) goto L_{int(o, 16):08x};')
                continue
            if m == 'jmp':
                out.append(f'    goto L_{int(o, 16):08x};')
                return out, True
            if m == 'nop':
                continue
            if m == 'push':
                v = num(o)
                if v is not None:
                    st['stack'].append(('int', hexi(v)))
                elif o in ('eax', 'ecx'):
                    st['stack'].append(st[o])
                else:
                    st['stack'].append(self.load(st, o, a))
                continue
            if m == 'pop':
                st['stack'].pop()
                continue
            if m == 'add' and ops[0] == 'esp':
                for _ in range(num(ops[1])//4):
                    st['stack'].pop()
                continue
            if m == 'call':
                if o.startswith('dword ptr'):
                    target = int(ABS.match(o).group(1), 16)
                else:
                    target = int(o, 16)
                self.call(st, target, out, a)
                continue
            if m == 'test' and ops == ['eax', 'eax']:
                st['flags'] = (st['eax'][1], '0')
                continue
            if m == 'cmp':
                lhs = st['eax'] if ops[0] == 'eax' else self.load(st, ops[0], a)
                rhs = num(ops[1])
                if rhs is None:
                    raise Unsupported(f'cmp {o} at {a:#x}')
                st['flags'] = (self.compare_operand(lhs, a), hexi(rhs))
                continue
            if not self.instruction(st, m, o, ops, out, a):
                raise Unsupported(f'{m} {o} at {a:#x}')
        return out, False

    def prologue(self, m, o, ops):
        return (m == 'push' and o == 'ebp') or (m == 'mov' and o == 'ebp, esp') or \
            (m == 'sub' and ops and ops[0] == 'esp') or m == 'leave'

    def compare_operand(self, value, address):
        if value[0] in ('int', 'bool'):
            return value[1]
        raise Unsupported(f'compare of {value} at {address:#x}')

    def lift(self):
        starts = sorted(t for t in self.targets if self.routine_start <= t <= self.end)
        blocks = []
        i = 0
        while i < len(starts):
            s = starts[i]
            if s in self.manual:
                end, lines, _ = self.manual[s]
                blocks.append((s, ['    /* hand-written span (see the header comment) */'] + lines))
                self.count('manual_spans')
                i = starts.index(end)
                continue
            stop = starts[i+1] if i+1 < len(starts) else self.end+1
            code, terminated = self.block_code(s, stop)
            if not terminated and i+1 < len(starts):
                code.append(f'    goto L_{stop:08x};')
            blocks.append((s, code))
            i += 1
        self.stats['blocks'] = len(blocks)
        return blocks


class AngleLifter(Lifter):
    routine_start = ITEM_ANGLE
    LOCALS = {-1: 'result', -8: 'rec', -0xc: 'pet', -0x10: 'type_copy'}

    def ret_statement(self):
        return '    return result;'

    def load(self, st, operand, address):
        m = mem(operand)
        if m and m[1] == 'ebp':
            if m[2] == 8:
                return ('obj',)
            name = self.LOCALS.get(m[2])
            if name in ('rec', 'pet'):
                return (name,)
            if name == 'type_copy':
                return ('int', 'type_copy')
            if name == 'result' and m[0] == 'byte':
                return ('int', 'result')
            raise Unsupported(f'read of local {operand}')
        if m and m[1] in ('eax', 'ecx'):
            base = st[m[1]]
            if base == ('obj',) and m[0] == 'dword' and m[2] == OBJ_TYPE:
                return ('int', 'o->type')
            if base == ('rec',) and m[0] == 'byte' and m[2] in (0x250, 0x251, 0x252):
                self.count('record_tests')
                return ('int', {0x250: 'env->record.kind_a', 0x251: 'env->record.kind_b',
                                0x252: 'env->record.type'}[m[2]])
            if base == ('pet',) and m[0] == 'dword' and m[2] in (0x25c, 0x260):
                return ('bits', {0x25c: 'env->pet.scale_bits', 0x260: 'env->pet.angle_z_bits'}[m[2]])
        raise Unsupported(f'load {operand} at {address:#x}')

    def compare_operand(self, value, address):
        if value == ('rec',):
            return 'env->record.present'
        if value == ('pet',):
            return 'pet_present'
        if value == ('int', 'o->type'):
            self.count('type_tests')
        return super().compare_operand(value, address)

    def store_float(self, target, value, out):
        if value[0] == 'f32':
            bits = value[1]
            rhs = '0.0f' if bits is None else f'mu_gi_f32(0x{bits:08x}u) /* {f32(bits)!r} */'
        elif value[0] == 'bits':
            rhs = f'mu_gi_f32({value[1]})'
        else:
            raise Unsupported(f'float store of {value}')
        out.append(f'    {target} = {rhs};')

    def call(self, st, target, out, a):
        index_ok = ('int', '(o->type - 0xae6)')
        if target == VEC_INDEX:
            if not st['ecx'] or st['ecx'][0] != 'vec':
                raise Unsupported(f'index helper without a vector at {a:#x}')
            st['eax'] = ('elem', st['ecx'][1] + 4*int(st['stack'].pop()[1], 0))
        elif target in (SCRIPT, PET_TABLE):
            st['eax'] = ('script',) if target == SCRIPT else ('pet_table',)
        elif target == RECORD:
            if st['ecx'] != ('script',) or st['stack'].pop() != index_ok:
                raise Unsupported(f'record lookup at {a:#x}')
            st['eax'] = ('rec',)
        elif target in (KIND_A, KIND_B):
            if st['ecx'] != ('script',):
                raise Unsupported('predicate without the script singleton')
            index, kind = st['stack'].pop(), st['stack'].pop()
            if index != index_ok or kind[0] != 'int':
                raise Unsupported(f'predicate arguments {index} {kind}')
            fn = 'mu_gi_kind_a' if target == KIND_A else 'mu_gi_kind_b'
            self.count('kind_a_calls' if target == KIND_A else 'kind_b_calls')
            st['eax'] = ('bool', f'{fn}(&env->record, o->type - 0xae6, {kind[1]})')
        elif target == PET_LOOKUP:
            if st['ecx'] != ('pet_table',) or st['stack'].pop() != index_ok:
                raise Unsupported(f'pet lookup at {a:#x}')
            self.count('pet_lookups')
            st['eax'] = ('pet',)
        elif target == IN_RANGE:
            value, low, high = st['stack'][-1], st['stack'][-2], st['stack'][-3]
            self.count('range_calls')
            st['eax'] = ('bool', f'mu_gi_in_range({value[1]}, {low[1]}, {high[1]})')
        else:
            raise Unsupported(f'call {target:#x} at {a:#x}')

    def instruction(self, st, m, o, ops, out, a):
        if m == 'mov' and ops[0] in ('eax', 'ecx'):
            st[ops[0]] = st['eax'] if ops[1] == 'eax' else self.load(st, ops[1], a)
            return True
        if m == 'add' and ops[0] == 'ecx' and st['ecx'] == ('obj',) and num(ops[1]) == OBJ_ANGLE:
            st['ecx'] = ('vec', OBJ_ANGLE)
            return True
        if m == 'sub' and ops[0] == 'eax' and st['eax'][0] == 'int':
            st['eax'] = ('int', f"({st['eax'][1]} - 0x{num(ops[1]):x})")
            return True
        if m == 'mov' and ops[0].startswith('dword ptr [ebp') and ops[1] == 'eax':
            name = self.LOCALS.get(mem(ops[0])[2])
            if name == 'rec' and st['eax'] == ('rec',):
                return True
            if name == 'pet' and st['eax'] == ('pet',):
                out.append('    pet_present = env->pet.present;')
                return True
            if name == 'type_copy' and st['eax'] == ('int', 'o->type'):
                out.append('    type_copy = o->type;')
                return True
            return False
        if m == 'mov' and ops[0] == 'byte ptr [ebp - 1]' and num(ops[1]) is not None:
            out.append(f'    result = {num(ops[1])};')
            return True
        if m == 'movzx' and ops == ['eax', 'al']:
            return st['eax'][0] == 'bool'
        if m == 'movzx' and ops[0] == 'eax':
            st['eax'] = self.load(st, ops[1], a)
            return True
        if m == 'movss' and ops[0] == 'xmm0':
            st['xmm0'] = ('f32', self.image.u32(int(ABS.match(ops[1]).group(1), 16)))
            return True
        if m == 'xorps' and ops == ['xmm0', 'xmm0']:
            st['xmm0'] = ('f32', None)
            return True
        if (m == 'movss' and ops[1] == 'xmm0') or (m == 'mov' and ops[0].startswith('dword ptr [e') and
                                                  ops[1] == 'ecx' and st['ecx'] and st['ecx'][0] == 'bits'):
            value = st['xmm0'] if m == 'movss' else st['ecx']
            d = mem(ops[0])
            base = st[d[1]]
            if base and base[0] == 'elem' and d[2] == 0:
                self.count('angle_stores')
                self.store_float(f"o->angle[{(base[1]-OBJ_ANGLE)//4}]", value, out)
                return True
            if base == ('obj',) and d[2] == OBJ_SCALE:
                self.count('scale_stores')
                self.store_float('o->scale', value, out)
                return True
        return False


# The plain-item span of the name builder: memset(buf, 0, 0x40); the prefix string
# (0x009953ef/0x009e051c, a std::string) is copied with strncpy(buf, prefix, 0x40);
# then strcpy(buf, record name) when the prefix is empty (0x008e53e0), else
# strcat(buf, record name); the temporary is destroyed at 0x017ebd29.
NAME_GENERAL_SPAN = (0x017ebb77, 0x017ebc04, [
    '    mu_gi_name_memset(s, buf, 0, 0x40);',
    '    prefix = mu_gi_name_prefix(env, it);',
    '    mu_gi_name_strncpy(s, buf, prefix, 0x40);',
    '    if (prefix[0] == 0) mu_gi_name_strcpy(s, buf, mu_gi_record_name(env, it));',
    '    else mu_gi_name_strcat(s, buf, mu_gi_record_name(env, it));',
    '    goto L_017ebc04;'], {0x017ebc04})


class NameLifter(Lifter):
    routine_start = NAME_BUILDER
    manual = {NAME_GENERAL_SPAN[0]: NAME_GENERAL_SPAN[1:]}
    # ebp locals: -0x10 object, -0x14 item, -0x18 level, -0x2c set record, -0x54 table-1e entry,
    # -0x5c label-window shared pointer, -0x74 std::string temporary, -0xb4 char buf[0x40]
    INT_LOCALS = {-0x18: 'level', -0x1c: 'sw_1c', -0x20: 'element', -0x24: 'i24', -0x28: 'i28',
                  -0x30: 'sw_30', -0x34: 'n34', -0x38: 'n38', -0x3c: 'sw_3c', -0x40: 'sw_40',
                  -0x44: 'sw_44', -0x48: 'sw_48', -0x4c: 'sw_4c', -0x50: 'sw_50'}

    def ret_statement(self):
        return '    return;'

    def prologue(self, m, o, ops):
        if super().prologue(m, o, ops):
            return True
        # SEH frame and the destructor-state slot [ebp-4]
        return (m == 'push' and o in ('-1',)) or (m == 'push' and o.startswith('0x1a32')) or \
            (m == 'mov' and 'fs:[0]' in o) or (m == 'push' and o == 'eax' and False) or \
            (m in ('or', 'and', 'mov') and ops and ops[0] == 'dword ptr [ebp - 4]') or \
            (m == 'mov' and o == 'ecx, dword ptr [ebp - 0xc]')

    def load(self, st, operand, address):
        if operand == 'dword ptr fs:[0]':
            return ('seh',)
        sc = SCALED.match(operand)
        if sc and int(sc.group(1), 16) == LEVEL_KEYS and st['eax'] and st['eax'][0] == 'int':
            return ('int', f"mu_gi_level_key(env, {st['eax'][1]})")   # int table 0x01cf15bc[level]
        m = mem(operand)
        if m and m[1] == 'ebp':
            off = m[2]
            if off == 8:
                return ('rec',)
            if off == -0x10:
                return ('obj',)
            if off == -0x14:
                return ('item',)
            if off == -0x2c:
                return ('set',)
            if off == -0x54:
                return ('t1e',)
            if off in self.INT_LOCALS:
                return ('int', self.INT_LOCALS[off])
            raise Unsupported(f'read of local {operand} at {address:#x}')
        if m and m[1] in ('eax', 'ecx'):
            base, off = st[m[1]], m[2]
            if base == ('obj',) and off == OBJ_TYPE:
                return ('int', 'o_type')
            if base == ('item',) and m[0] == 'dword' and off in (0x10, 0x14, 0x84):
                return ('int', {0x10: 'it->data.code', 0x14: 'it->data.level', 0x84: 'it->data.element'}[off])
            if base == ('item',) and m[0] == 'byte' and off == 0x3a:
                return ('int', 'it->data.excellent')
            if base == ('set',) and off == 0x24:
                return ('int', 'set_tier')
            if base == ('attr',) and m[0] == 'byte' and off == 0x2b0:
                return ('int', 'mu_gi_record_pc_room(env, it)')
            if base and base[0] == 'item_plus' and m[0] == 'byte' and off == 0x73:
                return ('int', f'it->data.sockets[{base[1]}]')
        raise Unsupported(f'load {operand} at {address:#x}')

    def instruction(self, st, m, o, ops, out, a):
        if m == 'mov' and ops[0] in ('eax', 'ecx') and ops[1] == 'dword ptr fs:[0]':
            return True
        if m == 'mov' and ops[0] in ('eax', 'ecx', 'edx'):
            src = ops[1]
            if src in ('eax', 'ecx'):
                st[ops[0]] = st[src]
            elif num(src) is not None:
                st[ops[0]] = ('const', num(src))
            else:
                st[ops[0]] = self.load(st, src, a)
            return True
        if m == 'add' and ops[0] in ('eax', 'ecx'):
            v, base = num(ops[1]), st[ops[0]]
            if v is not None:
                if base == ('rec',) and v == 4:
                    st[ops[0]] = ('item',)
                elif base == ('rec',) and v == 0x130:
                    st[ops[0]] = ('obj',)
                elif base == ('rec',) and v == 0x509:
                    st[ops[0]] = ('name',)
                elif base == ('attr',) and v == 0x210:
                    st[ops[0]] = ('str', 'mu_gi_record_name(env, it)')
                elif base == ('t1e',) and v == 8:
                    st[ops[0]] = ('t1e_string',)
                elif base and base[0] == 'int':
                    st[ops[0]] = ('int', f'({base[1]} + 0x{v:x})')
                else:
                    return False
                return True
            mm = mem(ops[1])
            if base == ('item',) and mm and mm[1] == 'ebp' and mm[2] in (-0x24, -0x28):
                st[ops[0]] = ('item_plus', self.INT_LOCALS[mm[2]])
                return True
            return False
        if m == 'sub' and ops[0] == 'eax' and st['eax'][0] == 'int':
            st['eax'] = ('int', f"({st['eax'][1]} - 0x{num(ops[1]):x})")
            return True
        if m == 'sar' and ops[0] == 'eax':
            st['eax'] = ('int', f"({st['eax'][1]} >> {num(ops[1])})")
            st['flags'] = (st['eax'][1], '0')
            return True
        if m == 'and' and ops[0] == 'eax' and num(ops[1]) is not None:
            st['eax'] = ('int', f"({st['eax'][1]} & 0x{num(ops[1]):x})")
            st['flags'] = (st['eax'][1], '0')
            return True
        if m == 'inc' and o == 'eax':
            st['eax'] = ('int', f"({st['eax'][1]} + 1)")
            return True
        if m == 'lea' and ops[0] in ('eax', 'ecx'):
            off = mem(ops[1].replace('[', 'dword ptr [', 1))[2]
            st[ops[0]] = {-0xb4: ('buf',), -0x74: ('tmpstr',), -0x5c: ('holder',)}.get(off)
            if st[ops[0]] is None:
                return False
            return True
        if m == 'mov' and ops[0].startswith('dword ptr [ebp') and ops[1] == 'eax':
            off = mem(ops[0])[2]
            if off in self.INT_LOCALS and st['eax'][0] == 'int':
                out.append(f"    {self.INT_LOCALS[off]} = {st['eax'][1]};")
                return True
            if off in (-0x10, -0x14) and st['eax'] in (('obj',), ('item',)):
                return True
            if off == -0x2c and st['eax'] == ('set',):
                return True
            if off == -0x54 and st['eax'] == ('t1e',):
                return True
            return False
        if m == 'and' and ops[0].startswith('dword ptr [ebp') and ops[1] == '0':
            off = mem(ops[0])[2]
            if off in self.INT_LOCALS:
                out.append(f'    {self.INT_LOCALS[off]} = 0;')
                return True
            return False
        if m in ('mov', 'and') and ops[0] == 'dword ptr [eax + 0x55c]' and st['eax'] == ('rec',):
            value = 0 if m == 'and' else num(ops[1])
            out.append(f'    it->name_class = {value};')
            self.count('class_stores')
            return True
        if m == 'movzx' and ops == ['eax', 'al']:
            return st['eax'][0] == 'bool'
        if m == 'movzx' and ops[0] == 'eax':
            st['eax'] = self.load(st, ops[1], a)
            return True
        if m == 'movss' and ops[0] == 'xmm0':
            st['xmm0'] = ('f32', self.image.u32(int(ABS.match(ops[1]).group(1), 16)))
            return True
        if m == 'movss' and ops == ['dword ptr [esp]', 'xmm0']:
            st['stack'][-1] = st['xmm0']      # push ecx; movss [esp], xmm0: a float argument
            return True
        return False

    def call(self, st, target, out, a):
        stack = st['stack']
        item_args = {IS_KIND_A: 'mu_gi_item_kind_a', IS_TYPE: 'mu_gi_item_type', IS_KIND_B: 'mu_gi_item_kind_b',
                     ITEM_OPTION: 'mu_gi_item_option'}
        if target in item_args:
            if st['ecx'] != ('item',):
                raise Unsupported(f'item predicate on {st["ecx"]} at {a:#x}')
            k = stack.pop()
            st['eax'] = ('bool', f'{item_args[target]}(env, it, {k[1]})')
            self.count('item_predicates')
        elif target == KIND_A2_TYPE2:
            st['eax'] = ('bool', 'mu_gi_item_type2_kind2(env, it)')
            self.count('item_predicates')
        elif target == ITEM_ATTR:
            if st['ecx'] != ('item',):
                raise Unsupported(f'attribute accessor on {st["ecx"]} at {a:#x}')
            st['eax'] = ('attr',)
        elif target == SCRIPT:
            st['eax'] = ('script',)
        elif target == KIND_A:
            index, kind = stack.pop(), stack.pop()
            st['eax'] = ('bool', f'mu_gi_script_kind_a(env, {index[1]}, {kind[1]})')
            self.count('item_predicates')
        elif target == GLOBAL_TEXT:
            if st['ecx'] != ('const', TEXT_TABLE):
                raise Unsupported(f'GlobalText on {st["ecx"]} at {a:#x}')
            st['eax'] = ('str', f'mu_gi_text(env, {stack.pop()[1]})')
            self.count('global_text')
        elif target == SET_LOOKUP:
            if st['ecx'] != ('const', SET_TABLE):
                raise Unsupported('set lookup on another table')
            code = stack.pop()
            out.append(f'    set_tier = mu_gi_set_tier(env, {code[1]});')
            st['eax'] = ('set',)
        elif target == TABLE_1E_GET:
            if st['ecx'] != ('const', TABLE_1E):
                raise Unsupported('table 0x06fbb138 expected')
            arg = stack.pop()
            out.append(f'    t1e = mu_gi_table_1e(env, {arg[1]});')
            st['eax'] = ('t1e',)
        elif target == TEXT_67:
            if st['ecx'] != ('const', TEXT_TABLE):
                raise Unsupported('0x011753c3 on another table')
            st['eax'] = ('strobj', f'mu_gi_text_string(env, {stack.pop()[1]})')
        elif target == LEVEL_TABLE_GET:
            if st['ecx'] != ('const', LEVEL_TABLE):
                raise Unsupported('table 0x06fbb664 expected')
            st['eax'] = ('strobj', f'mu_gi_level_table_text(env, {stack.pop()[1]})')
        elif target == CSTR:
            src = st['ecx']
            if src == ('t1e_string',):
                st['eax'] = ('str', 't1e')
            elif src and src[0] == 'strobj':
                st['eax'] = ('str', src[1])
            else:
                raise Unsupported(f'c_str of {src} at {a:#x}')
        elif target == SPRINTF:
            args = list(reversed(stack))
            if args[0] != ('name',):
                raise Unsupported(f'sprintf destination {args[0]} at {a:#x}')
            fmt = args[1]
            if fmt[0] == 'int':      # a literal format in the image
                fmt_expr = c_string(self.image.cstring(int(fmt[1], 0)))
            elif fmt[0] == 'str':
                fmt_expr = fmt[1]
            else:
                raise Unsupported(f'sprintf format {fmt} at {a:#x}')
            rest = []
            for v in args[2:]:
                if v == ('name',):
                    rest.append('MU_GI_ARG_S(it->name)')
                elif v == ('buf',):
                    rest.append('MU_GI_ARG_S(buf)')
                elif v[0] == 'str':
                    rest.append(f'MU_GI_ARG_S({v[1]})')
                elif v[0] == 'int':
                    rest.append(f'MU_GI_ARG_D({v[1]})')
                else:
                    raise Unsupported(f'sprintf argument {v} at {a:#x}')
            out.append(f'    mu_gi_name_sprintf(s, it->name, {fmt_expr}, {len(rest)}' +
                       ''.join(', ' + r for r in rest) + ');')
            self.count('sprintf_calls')
        elif target in (STRCAT, STRCPY):
            dst, src = stack[-1], stack[-2]
            dst_expr = {('name',): 'it->name', ('buf',): 'buf'}.get(dst)
            if src[0] == 'int':
                src_expr = c_string(self.image.cstring(int(src[1], 0)))
            elif src[0] == 'str':
                src_expr = src[1]
            else:
                raise Unsupported(f'strcat source {src} at {a:#x}')
            if dst_expr is None:
                raise Unsupported(f'strcat destination {dst} at {a:#x}')
            fn = 'mu_gi_name_strcat' if target == STRCAT else 'mu_gi_name_strcpy'
            out.append(f'    {fn}(s, {dst_expr}, {src_expr});')
            self.count('strcat_calls')
        elif target == GL_COLOR3F_IAT:
            r, g, b = stack[-1], stack[-2], stack[-3]
            for _ in range(3):
                stack.pop()
            vals = ', '.join(f'mu_gi_f32(0x{v[1]:08x}u)' for v in (r, g, b))
            out.append(f'    mu_gi_name_gl_color(s, {vals});')
        elif target == HOLDER_LOCK:
            if st['ecx'] != ('const', LABEL_HOLDER):
                raise Unsupported('label holder expected')
            stack.pop()
            st['eax'] = ('holder',)
        elif target == HOLDER_VALID:
            st['eax'] = ('bool', 'mu_gi_label_window(env)')
        elif target == HOLDER_GET:
            st['eax'] = ('window',)
        elif target == LABEL_ADD:
            if st['ecx'] != ('window',) or stack.pop() != ('rec',):
                raise Unsupported('addItem arguments')
            out.append('    mu_gi_name_label_add(s, it);')
        elif target == HOLDER_RELEASE:
            pass
        elif target == 0x008e83a0 and st['ecx'] == ('tmpstr',):
            pass                       # std::string destructor of the plain-item span's temporary
        else:
            raise Unsupported(f'call {target:#x} at {a:#x}')


def emit(name, guard, signature, prelude, blocks, stats, digest, body_digest, routine, comment):
    lines = [f'/* Generated by scripts/items_static.py from {routine} (restored text',
             f' * SHA-256 {digest}; routine body SHA-256 {body_digest}).',
             ' * Do not edit: regenerate with the lifter.',
             ' *']
    lines += [f' * {c}' if c else ' *' for c in comment]
    lines += [' */', f'#ifndef {guard}', f'#define {guard}', '', f'/* {json.dumps(stats)} */', '',
              signature, '{']
    lines += prelude
    used = set(re.findall(r'goto (L_[0-9a-f]{8});', '\n'.join('\n'.join(c) for _, c in blocks)))
    for start, code in blocks:
        label = f'L_{start:08x}'
        lines.append(f'{label}:' if label in used else f'/* {label} */')
        if label in used:
            lines.append('    ;')
        lines.extend(code)
    lines += ['}', '', '#endif', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', default='evidence/x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', default='evidence/image-data-run10/data-capture-10/client-image-data.bin')
    parser.add_argument('--emit-angle')
    parser.add_argument('--emit-name')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second section')
    image = Image(text, data)
    report = {}
    for key, cls in (('item_angle', AngleLifter), ('item_name', NameLifter)):
        lifter = cls(image)
        blocks = lifter.lift()
        body = text[lifter.routine_start-am.TEXT_BASE:lifter.end+1-am.TEXT_BASE]
        body_digest = hashlib.sha256(body).hexdigest()
        report[key] = {'routine': hex(lifter.routine_start), 'ret': hex(lifter.end), 'body_sha256': body_digest,
                       **lifter.stats}
        if key == 'item_angle' and args.emit_angle:
            Path(args.emit_angle).write_text(emit(
                'angle', 'MU_GI_ITEM_ANGLE_TABLE_H',
                'static int32_t mu_gi_item_angle_body(mu_gi_object *o, const mu_gi_angle_env *env)',
                ['    int32_t result = 0, type_copy = 0, pet_present = 0;', '    (void)type_copy;',
                 '    (void)pet_present;'], blocks, lifter.stats, am.TEXT_SHA256, body_digest,
                'ItemAngle 0x01802a66',
                ['One label per client basic block, in address order; the statements are the',
                 "block's stores (Angle +0x164 through the index helper, Scale +0xa0) and its",
                 'branch. Record and per-index table reads come from env (ground_items.h).']))
        if key == 'item_name' and args.emit_name:
            Path(args.emit_name).write_text(emit(
                'name', 'MU_GI_ITEM_NAME_TABLE_H',
                'static void mu_gi_name_body(mu_gi_item *it, const mu_gi_name_env *env, mu_gi_name_sink *s)',
                ['    const mu_gi_object *o = &it->object;', '    const int32_t o_type = o->type;',
                 '    int32_t level = 0, element = 0, i24 = 0, i28 = 0, n34 = 0, n38 = 0, set_tier = 0;',
                 '    int32_t sw_1c = 0, sw_30 = 0, sw_3c = 0, sw_40 = 0, sw_44 = 0, sw_48 = 0, sw_4c = 0, sw_50 = 0;',
                 '    const char *prefix = "", *t1e = "";', '    char buf[0x40];',
                 '    (void)o; (void)sw_1c; (void)sw_30; (void)sw_3c; (void)sw_40; (void)sw_44; (void)sw_48;',
                 '    (void)sw_4c; (void)sw_50; (void)set_tier; (void)t1e; (void)i24; (void)i28;',
                 '    memset(buf, 0, sizeof buf);'], blocks, lifter.stats, am.TEXT_SHA256, body_digest,
                'the item name builder 0x017ea422',
                ['One label per client basic block. it->name_class is item +0x55c (the label',
                 'colour class), it->name item +0x509. The span 0x017ebb77..0x017ebc04 (the',
                 'plain-item prefix and record name through std::string temporaries) is a',
                 'hand-written statement list; everything else is lifted.']))
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
