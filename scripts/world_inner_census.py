#!/usr/bin/env python3
"""RENDER-WORLDS-PICK-001: the all-world inner-object census (docs/research/client-worlds-pick.md, section 5).

For every routine RenderObjectVisual 0x017f9758 can reach for a map object - its own world cases, the thirteen
hooks of the common chain 0x017fcb5c..0x017fccbc and the visual slot +0x34 of the 48 factory classes - this lists
the object types the routine treats differently from an unlisted type, the address where their code starts, and
the particle / sprite / joint / effect / mesh / sound requests that code makes.

Method (static, on the pinned text): an abstract interpreter runs each routine with a concrete world and a
concrete object type. Values derived from them stay concrete; everything else (the model, rand, the clock, floats,
globals) is unknown, and a branch on an unknown value explores both sides. The instructions reached with type t
that an unlisted type does not reach are t's case. The candidate types come from the routine itself: every
constant a type-derived value is compared with (plus its neighbours), and every index of a jump table the type
selects, until no new constant appears; types between two neighbouring constants behave alike. Calls into the
world-handler code region and into small leaf functions (world tests, getters) are followed; engine calls are
recorded with their stack arguments (immediates only) and not followed.

Native status per row comes from three oracles, none of them a hand list:
  producer   the reconstructed routine's source names the type (a `case`/comparison constant in the function the
             coverage table or this script's table assigns to the routine);
  consumers  mu_pt_kind_supported (particles), mu_jt_kind_supported (joints) and skill_fx.c's effect_supported
             (effects), called in the built libraries for each (kind, subtype) the case requests;
  refusals   the rows the object runtime counts as refused (worlds 46 / 98; rows a lane's finding lists).
Rows are "drawn" (producer present, every requested consumer present), "partial" (what is missing is listed) or
"refused" (reason listed). A row whose requests have a variable kind or subtype says so.

No bytes, tables or decoded data are written: addresses, type numbers and request ids only.

  world_inner_census.py --csv docs/research/world-inner-census.csv --json <scratch>/census.json
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
from pathlib import Path

import capstone
from capstone import x86 as X

import pins

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x00401000
WORLD_GLOBALS = (0x01cf15fc, 0x01cf1600)
STACK_TOP = 0x7f000000
ENTRY_ESP = STACK_TOP - 0x4000
RETURN = 0x7fff0000          # the top-level return address
HANDLER_CODE = (0x00d50000, 0x00eb0000)   # the world handlers' code (classes and chain hooks)
SENTINEL = 100000            # an object type no routine names
MAX_STEPS = 300000
VISUAL = 0x017f9758
CHAIN = [0x009db8b1, 0x00def747, 0x00d8e640, 0x00dfc095, 0x00d622dd, 0x00dac0a2, 0x00e75089, 0x00e7df87,
         0x00e84941, 0x00d5404b, 0x00e3116a, 0x00e5f94b]
MANAGER = 0x00ea2dc1
SINGLETON_GETTER = 0x00db747f
REQUESTS = {
    0x0168fafd: ('particle', 0, 4), 0x015ae7b0: ('particle', 0, 4),
    0x01692eb7: ('sprite', 0, None),
    0x0153b02c: ('joint', 0, 4), 0x01543446: ('joint', 0, 4),
    0x013c0eaa: ('effect', 0, 4), 0x013c0f19: ('effect', 0, 4),
    0x00966e4a: ('mesh', 0, None), 0x00966def: ('body', None, None),
    0x00a6ac96: ('sound', 0, None), 0x016cacfc: ('light', None, None),
    0x016cdd5f: ('terrain-bitmap', 0, None), 0x012b6ef1: ('bone', None, None),
}
# engine routines never followed (frequent, large, or irrelevant to the type)
SKIP = set(REQUESTS) | {0x00966cc4, 0x00eaa8cf, 0x01989721, 0x00cfc922, 0x00cfc94a, 0x012b5064, 0x00966ea5}

OBJ = ('object',)


class Typed:
    """A concrete value derived from the object type by adding constants: value = type + offset."""
    __slots__ = ('v', 'off')

    def __init__(self, v, off):
        self.v, self.off = v & 0xffffffff, off


def conc(x):
    """The concrete 32-bit value of x, or None."""
    if isinstance(x, int):
        return x
    if isinstance(x, Typed):
        return x.v
    return None


def signed(x):
    return x - 0x100000000 if x & 0x80000000 else x


REG32 = {X.X86_REG_EAX: 'eax', X.X86_REG_ECX: 'ecx', X.X86_REG_EDX: 'edx', X.X86_REG_EBX: 'ebx',
         X.X86_REG_ESI: 'esi', X.X86_REG_EDI: 'edi', X.X86_REG_ESP: 'esp', X.X86_REG_EBP: 'ebp'}
SUB = {X.X86_REG_AX: ('eax', 0, 2), X.X86_REG_CX: ('ecx', 0, 2), X.X86_REG_DX: ('edx', 0, 2),
       X.X86_REG_BX: ('ebx', 0, 2), X.X86_REG_SI: ('esi', 0, 2), X.X86_REG_DI: ('edi', 0, 2),
       X.X86_REG_AL: ('eax', 0, 1), X.X86_REG_CL: ('ecx', 0, 1), X.X86_REG_DL: ('edx', 0, 1),
       X.X86_REG_BL: ('ebx', 0, 1), X.X86_REG_AH: ('eax', 1, 1), X.X86_REG_CH: ('ecx', 1, 1),
       X.X86_REG_DH: ('edx', 1, 1), X.X86_REG_BH: ('ebx', 1, 1)}
ORDER = ('eax', 'ecx', 'edx', 'ebx', 'esi', 'edi', 'esp', 'ebp')
JCC = {'je': 'e', 'jz': 'e', 'jne': 'ne', 'jnz': 'ne', 'jg': 'g', 'jnle': 'g', 'jge': 'ge', 'jnl': 'ge',
       'jl': 'l', 'jnge': 'l', 'jle': 'le', 'jng': 'le', 'ja': 'a', 'jnbe': 'a', 'jae': 'ae', 'jnb': 'ae',
       'jnc': 'ae', 'jb': 'b', 'jc': 'b', 'jnae': 'b', 'jbe': 'be', 'jna': 'be', 'js': 's', 'jns': 'ns'}
SETCC = {'sete': 'e', 'setz': 'e', 'setne': 'ne', 'setnz': 'ne', 'setg': 'g', 'setge': 'ge', 'setl': 'l',
         'setle': 'le', 'seta': 'a', 'setae': 'ae', 'setb': 'b', 'setbe': 'be'}


class Text:
    def __init__(self, text):
        self.text = text
        self.end = BASE + len(text)
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.md.detail = True
        self.cache = {}
        self.lengths = {}
        self.simples = {}

    def inside(self, a):
        return BASE <= a < self.end

    def insn(self, a):
        i = self.cache.get(a)
        if i is None:
            i = next(self.md.disasm(self.text[a - BASE:a - BASE + 16], a), None)
            if i is None:
                raise ValueError('undecodable %08x' % a)
            ops = []
            for o in i.operands:
                if o.type == X.X86_OP_REG:
                    ops.append(('r', o.reg, o.size))
                elif o.type == X.X86_OP_IMM:
                    ops.append(('i', o.imm & 0xffffffff, o.size))
                else:
                    ops.append(('m', (o.mem.segment, o.mem.base, o.mem.index, o.mem.scale, o.mem.disp), o.size))
            written = [REG32[r] if r in REG32 else SUB[r][0] for r in i.regs_access()[1] if r in REG32 or r in SUB]
            i = (i.mnemonic, tuple(ops), i.size, tuple(written), i.op_str)
            self.cache[a] = i
        return i

    def u32(self, a):
        return struct.unpack_from('<I', self.text, a - BASE)[0]

    def length(self, a):
        """Bytes from a to its first ret (a linear scan; enough to tell a small leaf from a body)."""
        n = self.lengths.get(a)
        if n is None:
            at, n = a, 0x10000
            try:
                while at - a < 0x4000:
                    m = self.insn(at)
                    at += m[2]
                    if m[0] in ('ret', 'retn'):
                        n = at - a
                        break
            except (ValueError, struct.error):
                pass
            self.lengths[a] = n
        return n

    def simple(self, a, depth=0):
        """A small straight leaf: at most 0x90 bytes to its ret, no backward jump, and only calls to such leaves
        (world tests, getters). String and container helpers loop, so they fail this."""
        known = self.simples.get(a)
        if known is not None:
            return known
        ok, at = self.length(a) <= 0x90, a
        try:
            while ok and at - a < 0x90:
                mnem, ops, size, _, _ = self.insn(at)
                if mnem in ('ret', 'retn'):
                    break
                if mnem == 'call':
                    ok = bool(ops) and ops[0][0] == 'i' and depth < 2 and self.inside(ops[0][1]) and \
                        self.simple(ops[0][1], depth + 1)
                elif mnem.startswith('j'):
                    ok = bool(ops) and ops[0][0] == 'i' and a <= ops[0][1] < a + 0x90 and ops[0][1] > at
                elif mnem.startswith(('rep', 'loop')):
                    ok = False
                at += size
        except (ValueError, struct.error):
            ok = False
        self.simples[a] = ok
        return ok

    def ret_bytes(self, a):
        at = a
        try:
            while at - a < 0x8000:
                m = self.insn(at)
                if m[0] in ('ret', 'retn'):
                    return m[1][0][1] if m[1] else 0
                at += m[2]
        except (ValueError, struct.error):
            pass
        return 0


class State:
    __slots__ = ('pc', 'regs', 'mem', 'flags', 'stack')

    def __init__(self, pc, regs, mem, flags, stack):
        self.pc, self.regs, self.mem, self.flags, self.stack = pc, regs, mem, flags, stack

    def copy(self, pc):
        return State(pc, dict(self.regs), dict(self.mem), self.flags, self.stack)

    def key(self):
        def k(v):
            return ('t', v.v, v.off) if isinstance(v, Typed) else v
        regs = tuple(k(self.regs[r]) for r in ORDER)
        ebp = self.regs['ebp']
        frame = ()
        if isinstance(ebp, int):   # the current frame's locals that hold a known value
            frame = tuple(sorted((a, k(v[1])) for a, v in self.mem.items()
                                 if ebp - 0x900 <= a < ebp + 0x40 and v[1] is not None))
        f = self.flags
        if f is not None:
            f = tuple(k(x) for x in f)
        return (self.pc, self.stack, regs, frame, f)


class Run:
    """One exploration of a routine with a concrete world and type."""

    def __init__(self, text, entry, world, kind, this=None):
        self.t, self.entry, self.world, self.kind = text, entry, world, kind
        self.reached = set()
        self.events = {}        # call site -> (target, args)
        self.bounds = set()     # type values a type-derived value was compared with
        self.table = False      # a jump or index table selected by the type
        self.lossy = False      # a type-derived value went through a non-affine operation
        self.truncated = False
        self.why = None
        self.this = this

    def cut(self, reason, s):
        self.truncated = True
        self.why = self.why or (reason, hex(s.pc), [hex(x) for x in s.stack])

    # ---- values
    def get_reg(self, s, reg, size):
        if reg in REG32:
            return s.regs[REG32[reg]]
        if reg in SUB:
            name, shift, n = SUB[reg]
            v = s.regs[name]
            if isinstance(v, tuple) and v and v[0] == 'low8' and shift == 0 and n == 1:
                return v[1]
            c = conc(v)
            if c is None:
                return None
            return (c >> (8 * shift)) & ((1 << (8 * n)) - 1)
        return None

    def set_reg(self, s, reg, value):
        if reg in REG32:
            s.regs[REG32[reg]] = value
        elif reg in SUB:
            name, shift, n = SUB[reg]
            old, new = conc(s.regs[name]), conc(value)
            if new is None:
                s.regs[name] = None
            elif old is not None:
                mask = ((1 << (8 * n)) - 1) << (8 * shift)
                s.regs[name] = (old & ~mask & 0xffffffff) | ((new << (8 * shift)) & mask)
            elif shift == 0 and n == 1:
                s.regs[name] = ('low8', new & 0xff)
            else:
                s.regs[name] = None

    def address(self, s, m):
        segment, base, index, scale, disp = m
        if segment == X.X86_REG_FS or segment == X.X86_REG_GS:
            return None
        b = 0
        if base:
            b = s.regs.get(REG32.get(base))
            if b is OBJ:
                return ('obj', disp) if not index else None
            b = conc(b)
            if b is None:
                return None
        i = 0
        if index:
            iv = s.regs.get(REG32.get(index))
            if isinstance(iv, Typed) and not base and self.t.inside(disp & 0xffffffff):
                self.table = True
            i = conc(iv)
            if i is None:
                return None
        return (b + i * scale + disp) & 0xffffffff

    def load(self, s, a, size):
        if a is None:
            return None
        if isinstance(a, tuple):
            return Typed(self.kind, 0) if a[1] == 0x5c and size == 4 else None
        if a in WORLD_GLOBALS and size == 4:
            return self.world & 0xffffffff
        if self.t.inside(a) and a + size <= self.t.end:
            return int.from_bytes(self.t.text[a - BASE:a - BASE + size], 'little')
        if STACK_TOP - 0x100000 <= a < STACK_TOP:
            v = s.mem.get(a)
            if v is None:
                return None
            n, value = v
            if n == size:
                return value
            c = conc(value)
            if c is not None and size < n:
                return c & ((1 << (8 * size)) - 1)
        return None

    def store(self, s, a, size, value):
        if isinstance(a, int) and STACK_TOP - 0x100000 <= a < STACK_TOP:
            s.mem[a] = (size, value)
            for k in range(1, 4):   # an overlapping older slot is no longer known
                s.mem.pop(a - k, None)
                if k < size:
                    s.mem.pop(a + k, None)

    def value(self, s, op):
        kind, x, size = op
        if kind == 'i':
            return x & ((1 << (8 * size)) - 1) if size < 4 else x
        if kind == 'r':
            return self.get_reg(s, x, size)
        return self.load(s, self.address(s, x), size)

    def assign(self, s, op, value):
        kind, x, size = op
        if kind == 'r':
            if size == 4 or x in SUB:
                self.set_reg(s, x, value)
        elif kind == 'm':
            self.store(s, self.address(s, x), size, value)

    # ---- arithmetic
    def binary(self, name, a, b, size):
        ca, cb = conc(a), conc(b)
        mask = (1 << (8 * size)) - 1
        if name == 'xor' and a is b and a is not None:
            return 0
        if name == 'and' and (ca == 0 or cb == 0):
            return 0
        if name == 'or' and (ca == mask or cb == mask):
            return mask
        if ca is None or cb is None:
            return None
        if name in ('add', 'sub') and size == 4 and isinstance(a, Typed) != isinstance(b, Typed):
            if name == 'add':
                t, c = (a, cb) if isinstance(a, Typed) else (b, ca)
                return Typed(t.v + c, t.off + signed(c))
            if isinstance(a, Typed):
                return Typed(a.v - cb, a.off - signed(cb))
        if isinstance(a, Typed) or isinstance(b, Typed):
            self.lossy = True
        r = {'add': ca + cb, 'sub': ca - cb, 'and': ca & cb, 'or': ca | cb, 'xor': ca ^ cb,
             'shl': ca << (cb & 31), 'shr': (ca & mask) >> (cb & 31), 'imul': signed(ca) * signed(cb),
             'sar': (signed(ca) if size == 4 else ca) >> (cb & 31)}[name]
        return r & mask

    def compare(self, a, b):
        for x, y in ((a, b), (b, a)):
            if isinstance(x, Typed) and isinstance(y, int):
                self.bounds.add(signed(y) - x.off)
            elif isinstance(x, Typed) and isinstance(y, Typed):
                self.lossy = True

    def condition(self, s, cc):
        f = s.flags
        if f is None:
            return None
        if f[0] == 'cmp':
            a, b = conc(f[1]), conc(f[2])
            if a is None or b is None:
                return None
            sa, sb = signed(a), signed(b)
            return {'e': a == b, 'ne': a != b, 'g': sa > sb, 'ge': sa >= sb, 'l': sa < sb, 'le': sa <= sb,
                    'a': a > b, 'ae': a >= b, 'b': a < b, 'be': a <= b, 's': ((a - b) >> 31) & 1 == 1,
                    'ns': ((a - b) >> 31) & 1 == 0}[cc]
        r = conc(f[1])
        if r is None:
            return None
        sr = signed(r)
        return {'e': r == 0, 'ne': r != 0, 'g': sr > 0, 'ge': sr >= 0, 'l': sr < 0, 'le': sr <= 0, 'a': r != 0,
                'ae': True, 'b': False, 'be': r == 0, 's': sr < 0, 'ns': sr >= 0}[cc]

    def follow(self, target):
        if target in SKIP or not self.t.inside(target):
            return False
        return HANDLER_CODE[0] <= target < HANDLER_CODE[1] or self.t.simple(target)

    # ---- the walk
    def explore(self):
        regs = {r: None for r in ORDER}
        regs['esp'], regs['ecx'] = ENTRY_ESP, self.this
        mem = {ENTRY_ESP: (4, RETURN), ENTRY_ESP + 4: (4, OBJ)}
        work = [State(self.entry, regs, mem, None, ())]
        seen = set()
        steps = 0
        while work:
            s = work.pop()
            while True:
                key = s.key()
                if key in seen:
                    break
                seen.add(key)
                steps += 1
                if steps > MAX_STEPS:
                    self.cut(1, s)
                    return
                nxt = self.step(s, work)
                if nxt is None:
                    break
                s.pc = nxt

    def step(self, s, work):
        pc = s.pc
        try:
            mnem, ops, size, written, _ = self.t.insn(pc)
        except (ValueError, struct.error):
            self.cut(2, s)
            return None
        self.reached.add(pc)
        after = pc + size
        esp = s.regs['esp']
        if not isinstance(esp, int):
            self.cut(3, s)
            return None
        if mnem == 'mov':
            self.assign(s, ops[0], self.value(s, ops[1]))
        elif mnem in ('movzx', 'movsx', 'movsxd'):
            v = conc(self.value(s, ops[1]))
            if isinstance(self.value(s, ops[1]), Typed):
                self.lossy = True
            if v is not None and mnem != 'movzx':
                bits = 8 * ops[1][2]
                if v & (1 << (bits - 1)):
                    v |= (0xffffffff >> bits) << bits
            if ops[1][0] == 'm' and ops[1][2] == 1 and v is None:
                a = ops[1][1]
                if not a[1] and a[2] and isinstance(s.regs.get(REG32.get(a[2])), Typed):
                    self.table = True
            self.assign(s, ops[0], v)
        elif mnem == 'lea':
            a = self.address(s, ops[1][1])
            self.assign(s, ops[0], a if isinstance(a, int) else None)
        elif mnem == 'push':
            v = self.value(s, ops[0])
            s.regs['esp'] = esp - 4
            self.store(s, esp - 4, 4, v)
        elif mnem == 'pop':
            v = self.load(s, esp, 4)
            s.regs['esp'] = esp + 4
            self.assign(s, ops[0], v)
        elif mnem in ('add', 'sub', 'and', 'or', 'xor', 'shl', 'shr', 'sar') and len(ops) == 2:
            a, b = self.value(s, ops[0]), self.value(s, ops[1])
            if mnem == 'xor' and ops[0] == ops[1]:
                r = 0
            else:
                r = self.binary(mnem, a, b, ops[0][2])
            self.assign(s, ops[0], r)
            s.flags = ('res', r) if r is not None else None
        elif mnem == 'imul' and len(ops) == 3:
            r = self.binary('imul', self.value(s, ops[1]), self.value(s, ops[2]), 4)
            self.assign(s, ops[0], r)
            s.flags = None
        elif mnem in ('inc', 'dec'):
            r = self.binary('add' if mnem == 'inc' else 'sub', self.value(s, ops[0]), 1, ops[0][2])
            self.assign(s, ops[0], r)
            s.flags = ('res', r) if r is not None else None
        elif mnem == 'neg':
            v = conc(self.value(s, ops[0]))
            r = (-v) & 0xffffffff if v is not None else None
            self.assign(s, ops[0], r)
            s.flags = ('res', r) if r is not None else None
        elif mnem == 'cmp':
            a, b = self.value(s, ops[0]), self.value(s, ops[1])
            self.compare(a, b)
            if ops[0][2] == 4 and ops[1][0] == 'i':
                b = b & 0xffffffff if b is not None else None
            s.flags = ('cmp', a, b)
        elif mnem == 'test':
            a, b = conc(self.value(s, ops[0])), conc(self.value(s, ops[1]))
            s.flags = ('res', a & b) if a is not None and b is not None else None
        elif mnem in JCC:
            target = ops[0][1]
            taken = self.condition(s, JCC[mnem])
            if taken is None:
                work.append(s.copy(target))
                return after
            return target if taken else after
        elif mnem in SETCC:
            c = self.condition(s, SETCC[mnem])
            self.assign(s, ops[0], None if c is None else int(c))
        elif mnem == 'jmp':
            if ops[0][0] == 'i':
                return ops[0][1]
            target = conc(self.value(s, ops[0]))
            if target is not None and self.t.inside(target):
                return target
            if ops[0][0] == 'm':   # a table selected by an unknown value: every entry
                _, base, index, scale, disp = ops[0][1]
                table = disp & 0xffffffff
                if index and scale == 4 and not base and self.t.inside(table):
                    for k in range(1024):
                        entry = self.t.u32(table + 4 * k)
                        if not (pc - 0x40000 <= entry <= pc + 0x40000):
                            break
                        work.append(s.copy(entry))
                    return None
            self.cut(4, s)
            return None
        elif mnem == 'call':
            target = ops[0][1] if ops[0][0] == 'i' else conc(self.value(s, ops[0]))
            args = tuple(conc(self.load(s, esp + 4 * k, 4)) for k in range(8))
            objs = tuple(k for k in range(8) if self.load(s, esp + 4 * k, 4) is OBJ)
            self.events[pc] = (target, args, objs)
            if target is not None and self.follow(target) and len(s.stack) < 6:
                s.regs['esp'] = esp - 4
                self.store(s, esp - 4, 4, after)
                s.stack = s.stack + (after,)
                return target
            if target is not None:
                s.regs['esp'] = esp + self.t.ret_bytes(target)
            for r in ('eax', 'ecx', 'edx'):
                s.regs[r] = None
            s.flags = None
        elif mnem in ('ret', 'retn'):
            n = ops[0][1] if ops else 0
            back = self.load(s, esp, 4)
            s.regs['esp'] = esp + 4 + n
            if not s.stack:
                return None
            if back != s.stack[-1]:
                self.cut(5, s)
                return None
            s.stack = s.stack[:-1]
            return back
        elif mnem == 'leave':
            ebp = s.regs['ebp']
            if not isinstance(ebp, int):
                self.cut(6, s)
                return None
            s.regs['ebp'] = self.load(s, ebp, 4)
            s.regs['esp'] = ebp + 4
        elif mnem in ('nop', 'fnop', 'int3'):
            if mnem == 'int3':
                return None
        else:   # floats, divisions, string moves: whatever they write becomes unknown
            for r in written:
                if r != 'esp':
                    s.regs[r] = None
            for op in ops[:1]:
                if op[0] == 'm':
                    a = self.address(s, op[1])
                    if isinstance(a, int):
                        self.store(s, a, op[2], None)
            s.flags = None
        return after


def analyse(text, entry, world, this=None):
    """{type: Run} for the candidate types of routine entry in world, the SENTINEL run, and the candidates."""
    runs = {}
    todo = [SENTINEL, 0, 1]
    bounds, table = set(), False
    while todo:
        kind = todo.pop()
        if kind in runs or kind < 0 or kind > 4096 and kind != SENTINEL:
            continue
        r = Run(text, entry, world, kind, this)
        r.explore()
        runs[kind] = r
        new = r.bounds - bounds
        bounds |= r.bounds
        table = table or r.table or r.lossy
        for b in new:
            todo += [b - 1, b, b + 1]
        if table and bounds:
            lo, hi = max(0, min(bounds) - 1), min(4096, max(bounds) + 1)
            todo += [k for k in range(lo, hi + 1) if k not in runs]
        if r.lossy:
            todo += [k for k in range(0, 512) if k not in runs]
    return runs


FLOATS = ('movss', 'movsd', 'movaps', 'movups', 'movd', 'movq', 'cvt', 'mulss', 'mulsd', 'addss', 'addsd', 'subss',
          'subsd', 'divss', 'divsd', 'comiss', 'ucomiss', 'comisd', 'xorps', 'andps', 'sqrt', 'maxss', 'minss')


def effectful(text, a):
    """An instruction that does something beyond choosing a path: a call, a float operation, or a write that
    is not to the frame (an OBJECT or model field, a global)."""
    mnem, ops, _, _, _ = text.insn(a)
    if mnem == 'call' or mnem.startswith(FLOATS) or (mnem.startswith('f') and mnem not in ('fnop',)):
        return True
    if mnem in ('mov', 'and', 'or', 'add', 'sub', 'inc', 'dec', 'xor') and ops and ops[0][0] == 'm':
        base = ops[0][1][1]
        return base not in (X.X86_REG_EBP, X.X86_REG_ESP)
    return False


def cases(text, entry, runs):
    """[(types, start address, call events, truncated)] for the types whose code does something an unlisted type's
    does not. A type that only walks more of the switch (a table entry that lands on the default) is not a case."""
    base = runs[SENTINEL]
    kinds = sorted(k for k in runs if k != SENTINEL)
    top = max(kinds) if kinds else 0
    plumbing = set()
    by_signature = {}
    last = None
    for kind in range(0, top + 1):
        if kind in runs:
            last = kind
        r = runs[last]   # a type between two candidates behaves like the candidate below it
        extra = r.reached - base.reached
        effects = frozenset(a for a in extra if effectful(text, a))
        if not effects:
            plumbing |= extra
            continue
        by_signature.setdefault(effects, []).append((kind, last))
    out = []
    for effects, members in by_signature.items():
        r = runs[members[0][1]]
        extra = r.reached - base.reached
        body = [a for a in extra - plumbing if entry <= a < entry + 0x20000] or sorted(extra - plumbing) or \
            sorted(effects)
        events = {site: e for site, e in r.events.items() if site in extra}
        out.append(([k for k, _ in members], min(body), events, r.truncated))
    return sorted(out, key=lambda c: c[0][0])


def requests(events):
    """Compact request list of a case: kind:id/subtype in call-site order ('?' for a variable value)."""
    out = []
    for site in sorted(events):
        target, args, _ = events[site]
        if target not in REQUESTS:
            continue
        name, first, second = REQUESTS[target]
        if first is None:
            item = name
        else:
            a = args[first]
            item = '%s:%s' % (name, '0x%x' % a if a is not None else '?')
            if second is not None:
                b = args[second]
                item += '/%s' % (b if b is not None and b < 0x80000000 else ('?' if b is None else b - 0x100000000))
        out.append(item)
    return out


def world_groups(text, entry, worlds, this=None):
    """Worlds grouped by the code an unlisted type reaches."""
    groups = {}
    for w in worlds:
        r = Run(text, entry, w, SENTINEL, this)
        r.explore()
        groups.setdefault(frozenset(r.reached), []).append(w)
    return sorted(groups.values(), key=lambda g: -len(g))


# ---------------------------------------------------------------- native oracles

def oracles():
    """Callables (kind, subtype) -> bool for particles, joints and effects, from the built libraries."""
    import ctypes
    import subprocess
    import tempfile
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    recon = ROOT / 'reconstructed'
    for d in ('particles', 'joints', 'combat'):
        subprocess.run(['make', '-s', '-C', str(recon / d)], check=True)
    particles = ctypes.CDLL(str(recon / 'particles' / ('libclient_particles.' + suffix)))
    joints = ctypes.CDLL(str(recon / 'joints' / ('libclient_joints.' + suffix)))
    for lib, name in ((particles, 'mu_pt_kind_supported'), (joints, 'mu_jt_kind_supported')):
        getattr(lib, name).argtypes = [ctypes.c_int32, ctypes.c_int32]
        getattr(lib, name).restype = ctypes.c_int
    # skill_fx.c's static effect_supported, through a one-function shim compiled next to the library's sources
    tmp = tempfile.mkdtemp(prefix='inner-census-')
    shim = Path(tmp) / 'effect_shim.c'
    shim.write_text('#include "%s"\nint census_effect_supported(int t, int s) { return effect_supported(t, s); }\n'
                    % (recon / 'combat' / 'skill_fx.c'))
    out = Path(tmp) / ('effect_shim.' + suffix)
    subprocess.run(['clang', '-std=c11', '-O1', '-fPIC', '-w', '-shared', '-I', str(recon / 'combat'), str(shim),
                    '-Wl,-undefined,dynamic_lookup', '-o', str(out)], check=True)
    effects = ctypes.CDLL(str(out))
    effects.census_effect_supported.argtypes = [ctypes.c_int, ctypes.c_int]
    return {'particle': lambda k, s: bool(particles.mu_pt_kind_supported(k, s)),
            'joint': lambda k, s: bool(joints.mu_jt_kind_supported(k, s)),
            'effect': lambda k, s: bool(effects.census_effect_supported(k, s))}, tmp


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--probe', help='entry[,world]: print the cases of one routine')
    a = p.parse_args(argv)
    text = Text(pins.TEXT.read())
    if a.probe:
        parts = a.probe.split(',')
        entry, world = int(parts[0], 16), int(parts[1]) if len(parts) > 1 else 0
        runs = analyse(text, entry, world)
        print('candidates', len(runs), 'sentinel reach', len(runs[SENTINEL].reached),
              'truncated', runs[SENTINEL].truncated)
        for kinds, start, events, truncated in cases(text, entry, runs):
            print(kinds, hex(start), requests(events), 'TRUNCATED' if truncated else '')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
