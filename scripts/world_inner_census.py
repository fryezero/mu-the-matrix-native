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
# The common chain 0x017fcb5c..0x017fccbc in call order: (entry, label). Each hook tests the world itself and
# returns whether it took the object. 0x00d5404b is a thiscall on the instance of 0x00d53c8f; 0x00db7656 is slot
# +0x34 of the singleton 0x01ec9118 (getter 0x00db747f, constructor 0x00db73f3, vtable 0x01aa7a08), a handler
# shaped like the factory's classes but not registered by the factory.
CHAIN = [(0x009db8b1, 'chain 1: 0x009db8b1'), (0x00def747, 'chain 2: Kalima'), (0x00d8e640, 'chain 3: Crywolf'),
         (0x00dfc095, 'chain 4: Land of Trials'), (0x00d622dd, 'chain 5: Aida'), (0x00dac0a2, 'chain 6: 0x00dac0a2'),
         (0x00e75089, 'chain 7: Kanturu'), (0x00e7df87, 'chain 8: Kanturu Remain'), (0x00e84941, 'chain 9: tower'),
         (0x00d5404b, 'chain 10: Barracks / Refuge'), (0x00db7656, 'chain 11: singleton 0x01ec9118 slot +0x34'),
         (0x00e3116a, 'chain 12: Elbeland'), (0x00e5f94b, 'chain 13: Swamp of Calmness')]
CHAIN_STOPS = {e for e, _ in CHAIN} | {0x00d53c8f, 0x00db747f, 0x00ea594b, 0x00ea2dc1}
MANAGER = 0x00ea2dc1
WORLDS = range(0, 161)
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

    def __init__(self, text, entry, world, kind, this=None, stop=()):
        self.t, self.entry, self.world, self.kind, self.stop = text, entry, world, kind, stop
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
                self.bounds.add(-iv.off)   # the type of the table's first entry
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
        if target in SKIP or target in self.stop or not self.t.inside(target):
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
                    self.bounds.add(-s.regs[REG32[a[2]]].off)
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


def analyse(text, entry, world, this=None, stop=()):
    """{type: Run} for the candidate types of routine entry in world, the SENTINEL run, and the candidates."""
    runs = {}
    todo = [SENTINEL, 0, 1]
    bounds, table = set(), False
    while todo:
        kind = todo.pop()
        if kind in runs or kind < 0 or kind > 4096 and kind != SENTINEL:
            continue
        r = Run(text, entry, world, kind, this, stop)
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


def world_groups(text, entry, worlds, this=None, stop=()):
    """Worlds grouped by the code an unlisted type reaches."""
    groups = {}
    for w in worlds:
        r = Run(text, entry, w, SENTINEL, this, stop)
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
    # the shim's other references (vector helpers) resolve against the combat library, loaded globally first
    ctypes.CDLL(str(recon / 'combat' / ('libcombat.' + suffix)), mode=ctypes.RTLD_GLOBAL)
    effects = ctypes.CDLL(str(out))
    effects.census_effect_supported.argtypes = [ctypes.c_int, ctypes.c_int]
    return {'particle': lambda k, s: bool(particles.mu_pt_kind_supported(k, s)),
            'joint': lambda k, s: bool(joints.mu_jt_kind_supported(k, s)),
            'effect': lambda k, s: bool(effects.census_effect_supported(k, s))}, tmp


def type_ranges(kinds):
    """'3,5-7,12' for a sorted list of ints."""
    out, i = [], 0
    while i < len(kinds):
        j = i
        while j + 1 < len(kinds) and kinds[j + 1] == kinds[j] + 1:
            j += 1
        out.append(str(kinds[i]) if i == j else '%d-%d' % (kinds[i], kinds[j]))
        i = j + 1
    return ','.join(out)


def routine_rows(text, label, entry, worlds, stop=(), source=None):
    """Census rows of one routine for the given worlds: one row per (world, case)."""
    rows = []
    for world in worlds:
        runs = analyse(text, entry, world, None, stop)
        for kinds, start, events, truncated in cases(text, entry, runs):
            rows.append({'routine': label, 'entry': '0x%08x' % entry, 'world': world, 'types': kinds,
                         'address': '0x%08x' % start, 'requests': requests(events), 'truncated': bool(truncated),
                         'calls': sorted({'0x%08x' % e[0] for e in events.values()
                                          if e[0] is not None and e[0] not in REQUESTS}), 'source': source})
    return rows


def census(text, progress=None):
    """Every routine's rows, plus per routine the worlds it accepts."""
    say = progress or (lambda *_: None)
    rows, routines = [], []
    # RenderObjectVisual's own world cases: the worlds whose unlisted type walks code of their own
    groups = world_groups(text, VISUAL, WORLDS, None, CHAIN_STOPS)
    common = groups[0]
    own = sorted(w for g in groups[1:] for w in g)
    found = routine_rows(text, 'RenderObjectVisual world case', VISUAL, own, CHAIN_STOPS)
    extra = routine_rows(text, 'RenderObjectVisual world case', VISUAL, common[:1], CHAIN_STOPS)
    routines.append({'routine': 'RenderObjectVisual world cases', 'entry': '0x%08x' % VISUAL, 'worlds': own,
                     'cases': len(found), 'note': 'other worlds go straight to the chain' +
                     ('; UNEXPECTED cases in the common group' if extra else '')})
    rows += found
    say('RenderObjectVisual', len(found))
    for entry, label in CHAIN:
        groups = world_groups(text, entry, WORLDS)
        accepted = sorted(w for g in groups[1:] for w in g)
        found = routine_rows(text, label, entry, accepted)
        rejected = routine_rows(text, label, entry, groups[0][:1])
        if rejected:   # the largest group has cases too: the hook takes those worlds as well
            accepted = sorted(accepted + groups[0])
            found += routine_rows(text, label, entry, groups[0][1:]) + rejected
        routines.append({'routine': label, 'entry': '0x%08x' % entry, 'worlds': accepted, 'cases': len(found),
                         'note': ''})
        rows += found
        say(label, len(found))
    coverage = json.loads((ROOT / 'docs/research/world-handler-coverage.json').read_text())
    for c in coverage['classes']:
        visual = c['handlers']['visual']
        entry = int(visual['entry'], 16)
        label = 'class %s (%s) slot +0x34' % (c['class_id'], c['label'])
        found = routine_rows(text, label, entry, c['worlds'], (), visual.get('source'))
        routines.append({'routine': label, 'entry': '0x%08x' % entry, 'worlds': c['worlds'], 'cases': len(found),
                         'note': 'vtable %s' % c['vtable']})
        rows += found
        say(label, len(found))
    return rows, routines


# ---------------------------------------------------------------- the native probe and the status

def world_folder(w):
    """mu_world_folder (native/core/mu_terrain.c): the Object<n> / World<n> folder of a world."""
    if 0x0b <= w <= 0x11 or w == 0x34:
        return 12
    if 0x18 <= w <= 0x1d or w == 0x24:
        return 25
    if 0x12 <= w <= 0x17 or w in (0x35, 0x61):
        return 19
    if w == 0x66:
        return 0x67
    if 0x52 <= w <= 0x5a:
        return 0x53
    if 0x7b <= w <= 0x7f:
        return 0x7c
    return w + 1


PROBE_FRAMES = 40


def native_probe(binary, game_root, world, kind):
    """mu-world's own counters for one authored object of the type at the hero's tile (128, 128), every step drawn:
    the object runtime's refusals and the particle / sprite / joint / effect pools' created and unsupported
    counts. An authored context (position (12650, 12750, 500), idle hero, default clock), not a placement."""
    import shutil
    import subprocess
    import tempfile
    import live_objects_to_plain as plain
    td = Path(tempfile.mkdtemp(prefix='inner-census-probe-'))
    try:
        record = {'type': kind, 'position': (12650.0, 12750.0, 500.0), 'angle': (0.0, 0.0, 0.0), 'scale': 1.0,
                  'flags': (1, 1, 1), 'light': (0.0, 0.0, 0.0), 'state_68': -1, 'value_e4': 0.8, 'value_e8': 0.2}
        folder = world_folder(world)
        (td / ('EncTerrain%d.plain' % folder)).write_bytes(plain.to_plain(folder, [record]))
        (td / 'frames').mkdir()
        run = subprocess.run([binary, '--game-root', game_root, '--world', str(world), '--tile', '128,128',
                              '--headless', '--backend', 'gl', '--frames', str(PROBE_FRAMES), '--every',
                              str(PROBE_FRAMES - 1), '--width', '320', '--height', '200', '--out-dir',
                              str(td / 'frames'), '--no-audio', '--objects-dir', str(td), '--time-series-every',
                              str(PROBE_FRAMES)], capture_output=True, text=True)
        out = {'exit': run.returncode}
        for line in run.stdout.splitlines():
            if not line.startswith('{'):
                continue
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if 'objects' in j and 'object_models' in j:
                out.update({k: j[k] for k in ('object_models', 'object_models_missing', 'objects_drawn',
                                              'objects_create_unsupported', 'objects_draw_unsupported',
                                              'objects_move_unsupported')})
            elif j.get('particles') is True:
                out.update({'particles_created': j['created'], 'particles_unsupported': j['unsupported'],
                            'sprites_created': j['sprites_created']})
            elif j.get('joints') is True:
                out.update({'joints_created': j['created'], 'joints_unsupported': j['unsupported'],
                            'effects_created': j['effects_created'], 'effects_unsupported': j['effects_unsupported']})
        return out
    finally:
        shutil.rmtree(td, ignore_errors=True)


def cited_sources():
    """Lower-cased text of the reconstructed and native sources: a routine whose entry they never cite has no
    native producer."""
    chunks = []
    for pattern in ('reconstructed/*/*.c', 'reconstructed/*/*.h', 'reconstructed/*/*.inc', 'native/core/*.c',
                    'native/core/*.h'):
        for path in sorted(ROOT.glob(pattern)):
            chunks.append(path.read_text(errors='replace').lower())
    return '\n'.join(chunks)


def cited(sources, entry):
    return any(form in sources for form in ('0x%08x' % entry, '0x%x' % entry, '%08x' % entry))


def started(probe):
    return probe.get('exit') == 0 and 'object_models' in probe


def judge(row, probe, is_cited, oracle):
    """(status, missing, evidence) of one (world, type) pair of a census row."""
    if not started(probe):
        return 'refused', 'not probed: the world has no terrain in the installed data and no other world shares ' \
            'the case', 'none'
    if probe['object_models_missing'] or not probe['object_models']:
        return 'refused', 'no model file for the type in the world\'s object folder (dead in the installed data)', \
            'none'
    missing = []
    for item in row['requests']:
        name, _, rest = item.partition(':')
        if name not in oracle or '?' in rest:
            continue
        kind, _, sub = rest.partition('/')
        if not oracle[name](int(kind, 16), int(sub)):
            missing.append('%s %s/%s' % (name, kind, sub))
    activity = sum(probe.get(k, 0) for k in ('particles_created', 'particles_unsupported', 'sprites_created',
                                             'joints_created', 'joints_unsupported', 'effects_created',
                                             'effects_unsupported'))
    refusals = probe['objects_draw_unsupported']
    evidence = 'observed' if activity or refusals else ('source' if is_cited else 'none')
    if refusals >= PROBE_FRAMES - 1 and not (probe.get('particles_created') or probe.get('sprites_created') or
                                             probe.get('joints_created') or probe.get('effects_created')):
        return 'refused', 'the object runtime counts every draw unsupported' + \
            ('' if is_cited else ' (no native producer)'), evidence
    if evidence == 'none':
        return 'refused', 'no native producer: the routine is not ported and the runtime does not count it', evidence
    counters = ['%d %s' % (probe[key], label) for key, label in (
        ('objects_draw_unsupported', 'draws refused'), ('particles_unsupported', 'particle requests refused'),
        ('joints_unsupported', 'joint requests refused'), ('effects_unsupported', 'effect requests refused'))
        if probe.get(key)]
    missing = sorted(set(missing))
    if missing or counters:
        text = '; '.join((['no consumer: ' + ', '.join(missing)] if missing else []) +
                         (['probe (%d draws): ' % PROBE_FRAMES + ', '.join(counters)] if counters else []))
        return 'partial', text, evidence
    return 'drawn', '', evidence


def with_status(rows, binary, game_root, progress=None):
    """Census rows split by the status of their types: [{..., types, status, missing, evidence, notes}]."""
    oracle, scratch = oracles()
    sources = cited_sources()
    probes, out = {}, []
    try:
        for n, row in enumerate(rows):   # one probe per (case, object folder, type)
            for kind in row['types']:
                key = (row['entry'], row['address'], world_folder(row['world']), row['world'], kind)
                shared = (row['entry'], row['address'], world_folder(row['world']), kind)
                if shared not in probes or not started(probes[shared][1]):
                    probes[shared] = (row['world'], native_probe(binary, game_root, row['world'], kind))
                probes[key] = probes[shared]
            if progress and n % 25 == 0:
                progress(n, len(rows), len(probes))
        siblings = {}   # a world without terrain borrows the probe of a world that runs the same case
        for (entry, address, _, world, kind), (_, probe) in [(k, v) for k, v in probes.items() if len(k) == 5]:
            if started(probe):
                siblings.setdefault((entry, address, kind), (world, probe))
        for row in rows:
            is_cited = cited(sources, int(row['entry'], 16))
            groups = {}
            for kind in row['types']:
                world, probe = probes[(row['entry'], row['address'], world_folder(row['world']), row['world'], kind)]
                notes = []
                if not started(probe) and (row['entry'], row['address'], kind) in siblings:
                    world, probe = siblings[(row['entry'], row['address'], kind)]
                if started(probe) and world != row['world']:
                    notes.append('probed in world %d (same case; %s)' % (
                        world, 'same object folder' if world_folder(world) == world_folder(row['world']) else
                        'this world has no terrain in the installed data'))
                verdict = judge(row, probe, is_cited, oracle)
                if probe.get('objects_create_unsupported'):
                    notes.append('create unsupported')
                if probe.get('objects_move_unsupported'):
                    notes.append('move unsupported')
                groups.setdefault(verdict + ('; '.join(notes),), []).append(kind)
            for (status, missing, evidence, notes), kinds in groups.items():
                extra = [notes] if notes else []
                if row['truncated']:
                    extra.append('request list may be incomplete (walk cut at the step limit)')
                if any('?' in item for item in row['requests']):
                    extra.append('variable request id (? = chosen at run time)')
                out.append(dict(row, types=kinds, status=status, missing=missing, evidence=evidence,
                                notes='; '.join(extra)))
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)
    return out


COLUMNS = ('routine', 'entry', 'world', 'types', 'type_count', 'address', 'requests', 'status', 'missing', 'evidence',
           'notes')


def write_csv(path, rows):
    with open(path, 'w', newline='') as handle:
        w = csv.writer(handle, lineterminator='\n')
        w.writerow(COLUMNS)
        for r in sorted(rows, key=lambda r: (int(r['entry'], 16), r['world'], r['types'][0])):
            w.writerow([r['routine'], r['entry'], r['world'], type_ranges(r['types']), len(r['types']), r['address'],
                        ' '.join(r['requests']), r['status'], r['missing'], r['evidence'], r['notes']])


def summary(rows, routines):
    def tally(items):
        out = {'drawn': 0, 'partial': 0, 'refused': 0}
        for r in items:
            out[r['status']] += len(r['types'])
        return out
    total = tally(rows)
    dead = sum(len(r['types']) for r in rows if r['status'] == 'refused' and r['missing'].startswith('no model'))
    per = {}
    for r in rows:
        per.setdefault((r['routine'], r['entry']), []).append(r)
    return {'pairs': sum(total.values()), 'rows': len(rows), 'status': total, 'refused_dead_no_model': dead,
            'routines': [{'routine': name, 'entry': entry, 'worlds': type_ranges(sorted({r['world'] for r in items})),
                          **tally(items)} for (name, entry), items in per.items()],
            'routines_without_cases': [r['routine'] for r in routines if not r['cases']]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--probe', help='entry[,world]: print the cases of one routine')
    p.add_argument('--json', help='write the raw census (rows and routines) here, or reuse it with --reuse')
    p.add_argument('--reuse', action='store_true', help='read --json instead of walking the text again')
    p.add_argument('--csv', help='write the census with the native status here')
    p.add_argument('--summary', help='write the totals (JSON) here')
    p.add_argument('--binary', default=str(ROOT / 'native/build/mu-world'))
    p.add_argument('--game-root', default=None, help='default: MU_GAME_ROOT')
    a = p.parse_args(argv)
    text = Text(pins.TEXT.read())
    if a.probe:
        parts = a.probe.split(',')
        entry, world = int(parts[0], 16), int(parts[1]) if len(parts) > 1 else 0
        runs = analyse(text, entry, world)
        print('candidates', len(runs), 'sentinel reach', len(runs[SENTINEL].reached),
              'truncated', runs[SENTINEL].truncated, runs[SENTINEL].why)
        for kinds, start, events, truncated in cases(text, entry, runs):
            print(type_ranges(kinds), hex(start), requests(events), 'TRUNCATED' if truncated else '')
        return 0
    if a.reuse and a.json:
        raw = json.loads(Path(a.json).read_text())
        if raw['text_sha256'] != pins.TEXT.sha256:
            raise SystemExit('the raw census was made from another text')
        rows, routines = raw['rows'], raw['routines']
    else:
        rows, routines = census(text, lambda label, n: print('%-60s %d' % (label, n), file=sys.stderr, flush=True))
        if a.json:
            Path(a.json).write_text(json.dumps({'text_sha256': pins.TEXT.sha256, 'rows': rows,
                                                'routines': routines}, indent=1))
    print(json.dumps({'rows': len(rows), 'routines': len(routines),
                      'truncated': sum(1 for r in rows if r['truncated'])}))
    if a.csv:
        import os
        root = a.game_root or os.environ.get('MU_GAME_ROOT')
        if not root:
            raise SystemExit('--game-root or MU_GAME_ROOT needed for the native probe')
        judged = with_status(rows, a.binary, root, lambda n, total, probes: print(
            'status %d/%d rows, %d probes' % (n, total, probes), file=sys.stderr, flush=True))
        write_csv(a.csv, judged)
        totals = summary(judged, routines)
        if a.summary:
            Path(a.summary).write_text(json.dumps(totals, indent=1))
        print(json.dumps({k: totals[k] for k in ('pairs', 'rows', 'status', 'refused_dead_no_model')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
