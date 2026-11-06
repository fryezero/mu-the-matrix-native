#!/usr/bin/env python3
"""RENDER-ITEMS-002Q: owner-effect programs of item bodies, read from the pinned instructions.

The armour bodies 0x1bc3..0x1c78 (and a few helm/weapon bodies) end their type case in RenderPartObjectBody
with a small effect block: owner-bone positions from 0x012b678d, CreateSprite 0x01692eb7 and CreateParticle
0x0168fafd requests, `rand() % 2` gates, quantised randoms 0x011ff622 and vec3 helpers. This script reads each
block as a straight-line program and writes reconstructed/renderchar/item_owner_fx.h, which renderchar.c
interprets after the type's base helper call when an owner host is given (mu_rc_item_draws_owner).

How a block is read (static, with concrete frame values):

* Unicorn runs the type once per survey state (validate_renderchar's plain item world) and records the call
  sites of draws and effect services. The block starts at the return site of the last draw before the first
  effect service and ends at the first unconditional jump after the last effect service.
* An abstract interpreter walks the block instruction by instruction (MSVC /Od idioms only: movss/mulss/addss/
  subss/divss/xorps on xmm0, push/pop/lea/mov of frame words, x87 fstp of 0x011ff622's result, the helper
  calls listed in HELPERS and the `rand() % 2` gate idiom). Values are binary32 constants (folded exactly),
  runtime registers (owner-bone positions, randoms, OBJECT angle) or frame/OBJECT pointers.
* A frame word the block reads before writing comes from the frame at the block start in the Unicorn runs; it
  must be the same in every state (vec3 locals are zero-constructed by 0x0095ea8e at scope entry).
* Any other instruction, helper or operand refuses the type. The block's draws are the body tables' business
  (gen_item_bodies.OWNER_FX_TYPES); a draw inside the block refuses the type too.

Only type IDs, addresses, bitmap/subtype numbers and binary32 constants are exported.
"""
import argparse
import re
import struct
import sys
from pathlib import Path

import pins

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT/'reconstructed/renderchar/item_owner_fx.h'

# 38 worn chest pieces 0x1bc3..0x1c78 (four code templates) and five helm bodies with one owner-bone sprite
# (0x19f4, 0x19fa, 0x1a00, 0x1a1f, 0x1a78). 0x0f1e and 0x174a draw their owner-bone particle in RenderObjDraw
# before the body helper (0x017d40c4, 0x017dda31); the reader refuses them ("no draw before the effect block").
OWNER_FX_TYPES = [
    0x19f4, 0x19fa, 0x1a00, 0x1a1f, 0x1a78,
    0x1bc3, 0x1bc4, 0x1bc5, 0x1bc6, 0x1bc7, 0x1bc8, 0x1bc9, 0x1bca, 0x1bcb, 0x1bcc, 0x1bcd, 0x1bce, 0x1bcf,
    0x1bd0, 0x1bdd, 0x1bde, 0x1bef, 0x1bf0, 0x1bf4, 0x1bf5, 0x1bf6, 0x1bf7, 0x1bf8, 0x1bf9, 0x1bfa, 0x1bfb,
    0x1bfc, 0x1bfd, 0x1bfe, 0x1bff, 0x1c00, 0x1c01, 0x1c1e, 0x1c1f, 0x1c41, 0x1c42, 0x1c77, 0x1c78,
]

DRAWS = (0x00966def, 0x00966e4a)
TRANSFORM, SPRITE, PARTICLE, RANGE, RAND = 0x012b678d, 0x01692eb7, 0x0168fafd, 0x011ff622, 0x01989721
EFFECTS = (TRANSFORM, SPRITE, PARTICLE, RANGE, RAND)
SIGN_MASK = 0x01a7df40
DATA_BASE = 0x01a7c000
FRAME_LOW = 0x6000          # frame bytes kept below EBP at the block start

# Op codes of item_owner_fx.h (see the header comment written by render()).
OP = dict(const=1, mov=2, mul=3, add=4, sub=5, div=6, neg=7, gate=8, range=9, transform=10, norm=11, angle=12,
          sprite=13, particle=14)
BINARY = {'mulss': 'mul', 'addss': 'add', 'subss': 'sub', 'divss': 'div'}


class Refused(Exception):
    pass


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def value(b):
    return struct.unpack('<f', struct.pack('<I', b))[0]


def fold(op, a, b=None):
    """binary32 result of one SSE operation on two binary32 words (double rounding is exact here)."""
    x, y = value(a), value(b) if b is not None else None
    if op == 'neg':
        return a ^ 0x80000000
    if op == 'div' and y == 0:
        raise Refused('constant division by zero')
    r = {'mul': lambda: x * y, 'add': lambda: x + y, 'sub': lambda: x - y, 'div': lambda: x / y}[op]()
    return bits(f32(r))


# ---------------------------------------------------------------- dynamic part: block bounds and frames

def survey(wa, t):
    """Run the survey states; return (block start, last effect site, frames at the block start)."""
    import validate_renderchar as v
    from unicorn import UC_HOOK_CODE

    log, frames, start = [], [], [None]

    class World(v.World):
        def install(self):
            super().install()
            m = self.m

            def site(name):
                def hook(uc, address, size, context):
                    log.append((name, m.r32(uc.reg_read(m.x86.UC_X86_REG_ESP))))
                return hook
            # Stubbed services record their return site inside the stub, before it returns.
            for address in DRAWS + EFFECTS:
                name = 'draw' if address in DRAWS else address
                if address in m.stubs:
                    old, cleanup = m.stubs[address]

                    def wrapped(mm, old=old, name=name):
                        log.append((name, mm.r32(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP))))
                        return old(mm)
                    m.stub(address, wrapped, cleanup)
                else:
                    m.uc.hook_add(UC_HOOK_CODE, site(name), begin=address, end=address)

            def snapshot(uc, address, size, context):
                ebp = uc.reg_read(m.x86.UC_X86_REG_EBP)
                frames.append((ebp, m.read(ebp - FRAME_LOW, FRAME_LOW + 0x20)))
            if start[0] is not None:
                m.uc.hook_add(UC_HOOK_CODE, snapshot, begin=start[0], end=start[0])

    first = None
    configs = v.CLASSIFY[:4]
    for config in configs:
        log.clear()
        result, _, _, _ = v.client_stream(wa, v.classify_case(t, config), World)
        if not result['ok']:
            raise Refused(f'client stops at {result["pc"]}')
        names = [n for n, _ in log]
        i = next((k for k, n in enumerate(names) if n in EFFECTS), None)
        if i is None:
            raise Refused('no effect service in the survey state')
        draws = [s for n, s in log[:i] if n == 'draw']
        if not draws:
            raise Refused('no draw before the effect block')
        last = max(s for n, s in log if n in EFFECTS and n != RAND)
        here = (draws[-1], last)
        if first is None:
            first = here
        elif first != here:
            raise Refused('the block bounds differ between states')
    # The same states again with the frame snapshot armed at the block start.
    start[0] = first[0]
    for config in configs:
        v.client_stream(wa, v.classify_case(t, config), World)
    if len(frames) != len(configs):
        raise Refused('block start not reached once in every state')
    return first[0], first[1], frames


# ---------------------------------------------------------------- static part: the abstract interpreter

class Program:
    def __init__(self):
        self.ops = []
        self.regs = 0

    def reg(self, count=1):
        r = self.regs
        self.regs += count
        if self.regs > 255:
            raise Refused('more than 255 registers')
        return r

    def emit(self, op, *args, k=0):
        self.ops.append((OP[op],) + tuple(args) + (0,) * (5 - len(args)) + (k & 0xffffffff,))
        return len(self.ops) - 1

    def scalar(self, word):
        """A register holding a value (constant or register)."""
        if word[0] == 'r':
            return word[1]
        if word[0] == 'c':
            r = self.reg()
            self.emit('const', r, k=word[1])
            return r
        raise Refused(f'not a float value: {word}')

    def vector(self, words):
        """Base of three consecutive registers holding the three words."""
        if all(w[0] == 'r' for w in words) and [w[1] for w in words] == [words[0][1] + k for k in range(3)]:
            return words[0][1]
        base = self.reg(3)
        for k, w in enumerate(words):
            if w[0] == 'c':
                self.emit('const', base + k, k=w[1])
            elif w[0] == 'r':
                self.emit('mov', base + k, w[1])
            else:
                raise Refused(f'not a float value: {w}')
        return base

    def binary(self, op, a, b):
        if a[0] == 'c' and b[0] == 'c':
            return ('c', fold(op, a[1], b[1]))
        r = self.reg()
        self.emit(op, r, self.scalar(a), self.scalar(b))
        return ('r', r)


MEM = re.compile(r'^dword ptr \[(ebp|esp|eax|ecx)(?: ([+-]) (0x[0-9a-f]+|\d+))?\]$')
ABS = re.compile(r'^(?:dword|xmmword) ptr \[(0x[0-9a-f]+)\]$')


def operand(text):
    m = MEM.match(text)
    if m:
        off = int(m.group(3), 0) if m.group(3) else 0
        return ('mem', m.group(1), -off if m.group(2) == '-' else off)
    m = ABS.match(text)
    if m:
        return ('abs', int(m.group(1), 16))
    if re.match(r'^(0x[0-9a-f]+|\d+|-\d+|-0x[0-9a-f]+)$', text):
        return ('imm', int(text, 0) & 0xffffffff)
    return ('reg', text)


class Interpreter:
    def __init__(self, wa, frames, start, last):
        import capstone
        self.text, self.data = wa[0], wa[1]
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.frames, self.start, self.last = frames, start, last
        self.mem, self.stack, self.reg = {}, [], {}
        self.xmm0 = self.st0 = None
        self.p = Program()
        self.pending = []       # (target address, op index of the gate, saved state)
        self.bones = []

    # memory -------------------------------------------------------------
    def frame_word(self, off):
        words = set()
        for ebp, raw in self.frames:
            i = FRAME_LOW + off
            if not 0 <= i <= len(raw) - 4:
                raise Refused(f'frame word {off:#x} outside the snapshot')
            words.add(struct.unpack_from('<I', raw, i)[0])
        if len(words) != 1:
            raise Refused(f'frame word ebp{off:+#x} differs between states')
        return ('c', words.pop())

    def load(self, ptr, k=0):
        if ptr[0] == 'frame':
            off = ptr[1] + 4 * k
            w = self.mem.get(off)
            if w is None:
                w = self.frame_word(off)
            if w[0] == 'phi':
                raise Refused(f'read of ebp{off:+#x} after a gated write')
            return w
        if ptr[0] == 'objptr' and ptr[1] == 0x164:
            return ('angle', k)
        raise Refused(f'load through {ptr}')

    def store(self, ptr, k, w):
        if ptr[0] != 'frame':
            raise Refused(f'store through {ptr}')
        self.mem[ptr[1] + 4 * k] = w

    def vec(self, ptr):
        if ptr[0] == 'objptr' and ptr[1] == 0x164:
            base = self.p.reg(3)
            self.p.emit('angle', base)
            return [('r', base + k) for k in range(3)]
        return [self.load(ptr, k) for k in range(3)]

    def absolute(self, address):
        i = address - DATA_BASE
        if not 0 <= i <= len(self.data) - 4:
            raise Refused(f'constant {address:#x} outside the data capture')
        return ('c', struct.unpack_from('<I', self.data, i)[0])

    def read(self, opnd):
        kind = opnd[0]
        if kind == 'abs':
            return self.absolute(opnd[1])
        if kind == 'imm':
            return ('c', opnd[1])
        if kind == 'mem':
            base, off = opnd[1], opnd[2]
            if base == 'ebp':
                if off == 8:
                    return ('model',)
                if off == 0xc:
                    return ('object',)
                if off < 0:
                    return self.load(('frame', off))
            if base == 'esp':
                if off % 4 or off // 4 >= len(self.stack):
                    raise Refused('stack read outside the pushed arguments')
                return self.stack[-1 - off // 4]
            raise Refused(f'read {opnd}')
        if kind == 'reg':
            w = self.reg.get(opnd[1])
            if w is None:
                raise Refused(f'read of unset {opnd[1]}')
            return w
        raise Refused(f'read {opnd}')

    def write(self, opnd, w):
        if opnd[0] == 'mem' and opnd[1] == 'ebp' and opnd[2] < 0:
            if opnd[2] == -4:
                return          # the EH state word
            self.mem[opnd[2]] = w
        elif opnd[0] == 'mem' and opnd[1] == 'esp':
            off = opnd[2]
            if off % 4 or off // 4 >= len(self.stack):
                raise Refused('stack write outside the pushed arguments')
            self.stack[-1 - off // 4] = w
        elif opnd[0] == 'reg':
            self.reg[opnd[1]] = w
        else:
            raise Refused(f'write {opnd}')

    def arg(self, k):
        if k >= len(self.stack):
            raise Refused('missing call argument')
        return self.stack[-1 - k]

    def pop(self, n):
        if n > len(self.stack):
            raise Refused('stack underflow')
        del self.stack[len(self.stack) - n:]

    # calls --------------------------------------------------------------
    def call(self, target):
        p, ecx = self.p, self.reg.get('ecx')
        if target == 0x00cfc94a:                       # data(): returns this
            self.reg['eax'] = ecx
        elif target == 0x0095eda9:                     # vec3 destructor
            self.reg['eax'] = ('junk',)
        elif target in (0x0098a0e5, 0x00cfcead):       # vec3(x, y, z) / set(x, y, z), ret 0xc
            for k in range(3):
                self.store(ecx, k, self.arg(k))
            self.pop(3)
            self.reg['eax'] = ecx
        elif target == 0x00a0c1d0:                     # axes: words 1, 1 and 1.0f
            for k, w in enumerate((1, 1, self.absolute(0x01a7dd48)[1])):
                self.store(ecx, k, ('c', w))
            self.reg['eax'] = ecx
        elif target == 0x00cfc8f2:                     # operator=(src), ret 4
            src = self.vec(self.arg(0))
            for k in range(3):
                self.store(ecx, k, src[k])
            self.pop(1)
            self.reg['eax'] = ecx
        elif target in (0x00cfcad8, 0x00cfca74):       # out = this -/+ other, ret 8
            out, other = self.arg(0), self.arg(1)
            a, b = self.vec(ecx), self.vec(other)
            op = 'sub' if target == 0x00cfcad8 else 'add'
            result = [p.binary(op, a[k], b[k]) for k in range(3)]
            for k in range(3):
                self.store(out, k, result[k])
            self.pop(2)
            self.reg['eax'] = out
        elif target == 0x00cfcb3c:                     # out = this * s, ret 8
            out, s = self.arg(0), self.arg(1)
            a = self.vec(ecx)
            result = [p.binary('mul', a[k], s) for k in range(3)]
            for k in range(3):
                self.store(out, k, result[k])
            self.pop(2)
            self.reg['eax'] = out
        elif target == 0x00cfd0cc:                     # normalize in place (0x00cfd15f(this, this))
            src = p.vector(self.vec(ecx))
            base = p.reg(3)
            p.emit('norm', base, src)
            for k in range(3):
                self.store(ecx, k, ('r', base + k))
            self.reg['eax'] = ('junk',)
        elif target == TRANSFORM:                      # model->(out, OBJECT, bone, local), ret 0x10
            out, owner, bone, local = (self.arg(k) for k in range(4))
            if ecx != ('model',) or owner != ('object',) or bone[0] != 'c' or bone[1] >= 0x100:
                raise Refused(f'owner transform operands {ecx} {owner} {bone}')
            src = p.vector(self.vec(local))
            base = p.reg(3)
            p.emit('transform', base, src, k=bone[1])
            self.bones.append(bone[1])
            for k in range(3):
                self.store(out, k, ('r', base + k))
            self.pop(4)
            self.reg['eax'] = ('junk',)
        elif target == RANGE:                          # cdecl (lo, hi, steps), result on x87
            lo, hi, steps = (self.arg(k) for k in range(3))
            if steps[0] != 'c' or not 0 < steps[1] < 0x10000:
                raise Refused(f'range steps {steps}')
            if lo[0] != 'c' or hi[0] != 'c':
                raise Refused('range bounds are not constants')
            span = [int(f32(f32(float(steps[1])) * value(w[1]))) for w in (lo, hi)]
            if not 0 < span[1] - span[0] + 1 < 0x10000:
                raise Refused(f'range span {span}')   # the C relies on a positive divisor
            r = p.reg()
            p.emit('range', r, p.scalar(lo), p.scalar(hi), k=steps[1])
            self.st0 = ('r', r)
            self.reg['eax'] = ('junk',)
        elif target == SPRITE:                         # cdecl, 9 arguments
            a = [self.arg(k) for k in range(9)]
            axes = self.vec(a[8])
            fixed = (a[4], a[5], a[6], a[7], tuple(axes))
            if fixed != (('object',), ('c', 0), ('c', 0), ('c', 4),
                         (('c', 1), ('c', 1), self.absolute(0x01a7dd48))) or a[0][0] != 'c':
                raise Refused(f'sprite arguments {a[0]} {fixed}')
            pos = p.vector(self.vec(a[1]))
            light = p.vector(self.vec(a[3]))
            p.emit('sprite', pos, p.scalar(a[2]), light, k=a[0][1])
            self.reg['eax'] = ('junk',)
        elif target == PARTICLE:                       # cdecl, 8 arguments
            a = [self.arg(k) for k in range(8)]
            if a[0][0] != 'c' or a[4][0] != 'c' or a[4][1] > 0xff or a[6] != ('c', 0) or a[7] != ('c', 0):
                raise Refused(f'particle arguments {a}')
            pos = p.vector(self.vec(a[1]))
            angle = p.vector(self.vec(a[2]))
            light = p.vector(self.vec(a[3]))
            p.emit('particle', pos, angle, light, p.scalar(a[5]), a[4][1], k=a[0][1])
            self.reg['eax'] = ('junk',)
        elif target in DRAWS:
            raise Refused('draw inside the effect block')
        else:
            raise Refused(f'call {target:#x}')

    # control ------------------------------------------------------------
    GATE = [('and', 'eax, 0x80000001'), ('jns', None), ('dec', 'eax'), ('or', 'eax, 0xfffffffe'),
            ('inc', 'eax'), ('test', 'eax, eax'), ('jne', None)]

    GATE_IDIV = [('cdq', ''), ('push', None), ('pop', 'ecx'), ('idiv', 'ecx'), ('test', 'edx, edx'), ('jne', None)]

    def merge(self, address):
        while self.pending and self.pending[-1][0] == address:
            _, index, (mem, stack) = self.pending.pop()
            if len(stack) != len(self.stack):
                raise Refused('stack depth differs at a gate target')
            for off in set(mem) | set(self.mem):
                if mem.get(off) != self.mem.get(off):
                    self.mem[off] = ('phi',)
            for k, w in enumerate(stack):
                if w != self.stack[k]:
                    self.stack[k] = ('phi',)
            self.reg = {}
            self.xmm0 = self.st0 = None
            self.p.ops[index] = self.p.ops[index][:-1] + (len(self.p.ops),)
        if any(target < address for target, _, _ in self.pending):
            raise Refused('gate target skipped')

    def run(self):
        address = self.start
        end = None
        insns = {}
        for i in self.md.disasm(self.text[self.start - 0x401000:self.last - 0x401000 + 0x400], self.start):
            insns[i.address] = i
        while True:
            self.merge(address)
            i = insns.get(address)
            if i is None:
                raise Refused(f'no instruction at {address:#x}')
            mn, ops = i.mnemonic, i.op_str
            nxt = address + i.size
            if mn == 'call' and int(ops, 16) == RAND:
                # rand() % m != 0 skips to the target: m = 2 as and/jns/dec/or/inc (0x0173e869 .. 0x0173e87c),
                # other m as cdq/push m/pop ecx/idiv ecx (0x01742f5c).
                modulus, seq = None, None
                for idiom in (self.GATE, self.GATE_IDIV):
                    seq, a = [], nxt
                    for want in idiom:
                        j = insns.get(a)
                        if j is None or j.mnemonic != want[0] or (want[1] is not None and j.op_str != want[1]):
                            seq = None
                            break
                        seq.append(j)
                        a += j.size
                    if seq is not None:
                        break
                if seq is None:
                    raise Refused(f'rand outside the gate idiom at {address:#x}')
                if idiom is self.GATE:
                    if int(seq[1].op_str, 16) != seq[5].address:
                        raise Refused('gate idiom jump')
                    modulus = 2
                else:
                    modulus = int(seq[1].op_str, 0)
                    if not 1 < modulus < 0x100:
                        raise Refused('gate modulus')
                target = int(seq[-1].op_str, 16)
                if target <= a:
                    raise Refused('backward gate')
                index = self.p.emit('gate', modulus)
                self.pending.append((target, index, (dict(self.mem), list(self.stack))))
                self.pending.sort(key=lambda x: -x[0])
                address = a
                continue
            if mn == 'jmp' and not self.p.ops and not self.pending and not self.stack and int(ops, 16) > address:
                address = int(ops, 16)   # the draws ended in an if/else; the block starts at the join
                continue
            if mn == 'jmp':
                if self.pending or address < self.last:
                    raise Refused(f'jump inside the block at {address:#x}')
                end = address
                break
            if mn == 'nop':
                pass
            elif mn == 'push':
                o = operand(ops)
                self.stack.append(('junk',) if o == ('reg', 'ecx') and self.reg.get('ecx') is None else self.read(o))
            elif mn == 'pop':
                self.reg[ops] = self.stack.pop()
            elif mn == 'movss':
                dst, src = (operand(x.strip()) for x in ops.split(',', 1))
                if dst == ('reg', 'xmm0'):
                    self.xmm0 = self.read(src)
                elif src == ('reg', 'xmm0'):
                    if self.xmm0 is None:
                        raise Refused('store of an unset xmm0')
                    self.write(dst, self.xmm0)
                else:
                    raise Refused(f'movss {ops}')
            elif mn in BINARY:
                dst, src = (operand(x.strip()) for x in ops.split(',', 1))
                if dst != ('reg', 'xmm0') or self.xmm0 is None:
                    raise Refused(f'{mn} {ops}')
                self.xmm0 = self.p.binary(BINARY[mn], self.xmm0, self.read(src))
            elif mn == 'xorps':
                dst, src = (operand(x.strip()) for x in ops.split(',', 1))
                if dst == src == ('reg', 'xmm0'):
                    self.xmm0 = ('c', 0)
                elif dst == ('reg', 'xmm0') and src == ('abs', SIGN_MASK) and self.xmm0 is not None:
                    if self.xmm0[0] == 'c':
                        self.xmm0 = ('c', self.xmm0[1] ^ 0x80000000)
                    else:
                        r = self.p.reg()
                        self.p.emit('neg', r, self.p.scalar(self.xmm0))
                        self.xmm0 = ('r', r)
                else:
                    raise Refused(f'xorps {ops}')
            elif mn == 'lea':
                dst, src = (x.strip() for x in ops.split(',', 1))
                m = re.match(r'^\[ebp - (0x[0-9a-f]+)\]$', src)
                if dst not in ('eax', 'ecx', 'edx') or not m:
                    raise Refused(f'lea {ops}')
                self.reg[dst] = ('frame', -int(m.group(1), 16))
            elif mn == 'mov':
                dst, src = (operand(x.strip()) for x in ops.split(',', 1))
                if dst[0] == 'mem' and dst[1] == 'ebp' and dst[2] == -4:
                    pass
                elif src[0] == 'mem' and src[1] in ('eax', 'ecx'):
                    raise Refused(f'mov {ops}')
                else:
                    self.write(dst, self.read(src))
            elif mn == 'add' and ops.startswith('esp, '):
                n = int(ops[5:], 0)
                if n % 4:
                    raise Refused('odd stack adjustment')
                self.pop(n // 4)
            elif mn == 'add' and ops.startswith('ecx, '):
                base, n = self.reg.get('ecx'), int(ops[5:], 0)
                if base == ('object',):
                    self.reg['ecx'] = ('objptr', n)
                elif base and base[0] == 'frame':
                    self.reg['ecx'] = ('frame', base[1] + n)
                else:
                    raise Refused(f'add ecx of {base}')
            elif mn == 'fstp':
                if self.st0 is None:
                    raise Refused('fstp without an x87 value')
                self.write(operand(ops), self.st0)
                self.st0 = None
            elif mn == 'or' and ops == 'dword ptr [ebp - 4], 0xffffffff':
                pass
            elif mn == 'call':
                self.call(int(ops, 16))
                if int(ops, 16) in (SPRITE, PARTICLE, RANGE):
                    pass
            else:
                raise Refused(f'{mn} {ops} at {address:#x}')
            address = nxt
        return end


def extract_type(wa, t):
    start, last, frames = survey(wa, t)
    it = Interpreter(wa, frames, start, last)
    end = it.run()
    effects = sum(op[0] in (OP['sprite'], OP['particle']) for op in it.p.ops)
    if not effects:
        raise Refused('no effect request')
    return {'start': start, 'end': end, 'ops': it.p.ops, 'regs': it.p.regs, 'bones': it.bones}


def extract(types=OWNER_FX_TYPES):
    wa = tuple(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    out, refused = {}, {}
    for t in types:
        try:
            out[t] = extract_type(wa, t)
        except Refused as e:
            refused[t] = str(e)
    return out, refused


def render(programs):
    blocks, rows, ops = [], [], []
    lines = ['/* Generated by scripts/gen_item_owner_fx.py (RENDER-ITEMS-002Q). Owner-effect programs of item bodies,',
             ' * read from the pinned instructions; see client-render-items.md part 17. One op = {op, a, b, c, d, e, k}.',
             ' * Registers are binary32; a vec3 is three consecutive registers.',
             ' *  1 const  r[a] = bits k            2 mov  r[a] = r[b]',
             ' *  3..6     r[a] = r[b] mul/add/sub/div r[c] (binary32)      7 neg  r[a] = -r[b] (sign flip)',
             ' *  8 gate   rand() % a != 0: continue at op k (program-relative)',
             ' *  9 range  r[a] = 0x011ff622(r[b], r[c], k steps), one rand',
             ' * 10 transform  r[a..a+2] = 0x012b678d(owner bone k, local r[b..b+2])',
             ' * 11 norm   r[a..a+2] = 0x00cfd15f(r[b..b+2])   12 angle  r[a..a+2] = OBJECT +0x164',
             ' * 13 sprite CreateSprite 0x01692eb7(bitmap k, pos r[a], scale r[b], light r[c], OBJECT, 0, 0, 4, axes)',
             ' * 14 particle CreateParticle 0x0168fafd(bitmap k, pos r[a], angle r[b], light r[c], subtype e, scale r[d], 0, 0)',
             ' */',
             'typedef struct { uint8_t op, a, b, c, d, e; uint32_t k; } mu_rc_fx_op;',
             'static const mu_rc_fx_op mu_rc_fx_ops[] = {']
    for t, prog in sorted(programs.items()):
        key = tuple(prog['ops'])
        if key not in blocks:
            blocks.append(key)
            first = len(ops)
            ops.extend(prog['ops'])
            lines.append(f'    /* block {prog["start"]:#010x}..{prog["end"]:#010x} */')
            for op in prog['ops']:
                lines.append('    {%d, %d, %d, %d, %d, %d, 0x%08xu},' % op)
        index = blocks.index(key)
        first = sum(len(b) for b in blocks[:index])
        rows.append((t, first, len(prog['ops']), prog['regs'], max(prog['bones'], default=-1)))
    lines += ['};',
              'static const struct { int32_t type; uint16_t first, count; uint8_t regs, max_bone; } mu_rc_fx_types[] = {']
    for row in rows:
        lines.append('    {0x%04x, %d, %d, %d, %d},' % row)
    lines += ['};', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HEADER)
    p.add_argument('--check', action='store_true')
    p.add_argument('--types', help='comma-separated hex types (report only)')
    a = p.parse_args()
    types = [int(x, 16) for x in a.types.split(',')] if a.types else OWNER_FX_TYPES
    programs, refused = extract(types)
    for t, why in sorted(refused.items()):
        print(f'refused {t:#06x}: {why}', file=sys.stderr)
    if a.types:
        for t, prog in sorted(programs.items()):
            print(f'{t:#06x} block {prog["start"]:#x}..{prog["end"]:#x} ops {len(prog["ops"])} regs {prog["regs"]} '
                  f'bones {prog["bones"]}')
        return
    if refused:
        raise SystemExit('owner-effect program no longer reads from the pinned instructions')
    result = render(programs)
    if a.check:
        if a.output.read_text() != result:
            raise SystemExit('owner-effect table differs from the pinned instructions')
    else:
        a.output.write_text(result)


if __name__ == '__main__':
    main()
