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

RENDER-ITEMS-002R adds pre-draw programs (PRE_FX_TYPES): RenderObjDraw's own type case creates bone sprites
0x0150e746 and TransformPosition 0x012b6ef1 positions on the item's own bones (BoneTransform 0x06fce398, by name
through 0x012bd35a), before the body draws. The case starts at the executed basic block after the last type compare
(OBJECT +0x5c or the type argument) that precedes the first effect service, and ends at the jump to the join. The
interpreter then also reads std::string names, the wave 0x0185bdc4, the clock 0x06fce370, the CRT sine 0x009681bd,
the comparison abs 0x0184f8ff, the alpha argument, (float)(rand() % m) values, rand() % 2^n gates, float/int array
elements, the TestFrustrum2D flag [ebp-0xd] and loops over constant counters (decided statically, unrolled).

Only type IDs, addresses, bitmap/subtype numbers, binary32 constants and bone names are exported.
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

# RENDER-ITEMS-002R: bodies whose effects RenderObjDraw creates in its own type case, before the body draws
# (pre-draw programs): bone sprites 0x0150e746 at the item's own posed bones, often by name (0x012bd35a).
# Six swords 0x0b27..0x0b59, three maces 0x0f1c..0x0f2e, four bows 0x1311..0x131d, three shields 0x1748..0x1758
# and ten wings 0x230b..0x2499; their draws fit the generic recipes with the effect requests set aside
# (gen_item_bodies.PRE_EXTENDED/PRE_CARRY). The bows 0x1313, 0x1317 and 0x1319 read but their draws fit no probe
# option over the 292 survey states.
PRE_FX_TYPES = [
    0x0b27, 0x0b2a, 0x0b4b, 0x0b4c, 0x0b57, 0x0b59, 0x0f1c, 0x0f1d, 0x0f2e, 0x1311, 0x1312, 0x1316, 0x131d, 0x1748,
    0x1749, 0x1758, 0x230b, 0x2311, 0x2382, 0x2383, 0x2384, 0x2385, 0x2394, 0x2395, 0x2494, 0x2499,
    # RENDER-ITEMS-002S (part 19): integer clock chains (0x0b4f, 0x0b50, 0x0b53 with a float branch), joint loops
    # (0x22ec, 0x248f), a rotated sprite behind rand() % 15 >= 8 (0x230c, 0x2496), bones at rand() % bone count
    # (0x23ef, 0x2400, 0x2405), names built with _itoa (0x24cf, 0x24d6) and the OBJECT position (0x26f8, 0x26f9).
    0x0b4f, 0x0b50, 0x0b53, 0x22ec, 0x248f, 0x230c, 0x2496, 0x23ef, 0x2400, 0x2405, 0x24cf, 0x24d6, 0x26f8, 0x26f9,
    # RENDER-ITEMS-002T (part 21): two maces with the random spherical vector 0x00d01fc6, rand() % 3 selects,
    # 0x012b678d on item bones and the rendered-frame counter gate (0x0f1f, 0x0f20). 0x0f2a reads too, but its body
    # draws an atlas frame from the rendered-frame counter, which the body probes hold at 0 (not admitted).
    0x0f1f, 0x0f20,
    # RENDER-ITEMS-002U (part 23): 0x0f2a, its atlas frame now a body chain of the counter (gen_item_bodies.FRAME_TYPES).
    0x0f2a,
    # RENDER-ITEMS-002W: exact body scalars and range-aware probes.
    0x1313, 0x1317, 0x1319,
    # RENDER-ITEMS-002V: counter-gated maces, with quantised random body-light scalars.
    0x0f24, 0x0f28, 0x0f29, 0x0f2b, 0x0f2c,
]

# RENDER-ITEMS-002T: owner blocks after the draws in RenderPartObjectBody's case that use the pre-draw idioms
# (post programs, run where the owner programs run): bow 0x130d (TransformPosition 0x012b6ef1 on the OBJECT's own
# bone 4 through 0x0129f12c, a sprite of bitmap 0x8081 + rand() % 3) and 0x2713 (item bones 8, 10, 11, a clock sine
# written to the OBJECT light +0xec and read back as the sprites' light).
POST_FX_TYPES = [0x130d, 0x2713]

DRAWS = (0x00966def, 0x00966e4a)
TRANSFORM, SPRITE, PARTICLE, RANGE, RAND = 0x012b678d, 0x01692eb7, 0x0168fafd, 0x011ff622, 0x01989721
JOINT = 0x0153b02c          # CreateJoint (RENDER-ITEMS-002S)
BONE_SPRITE, NAMED, STRING, STRING_FREE, WAVE = 0x0150e746, 0x012bd35a, 0x0094997e, 0x008e83a0, 0x0185bdc4
ITEM_TRANSFORM, BONE_TRANSFORM = 0x012b6ef1, 0x06fce398
ITOA, STRING_APPEND, STRING_CSTR = 0x0198c1d7, 0x0094b9f7, 0x008e7940
VECTOR_CTOR, VECTOR_DTOR = 0x0191b8be, 0x0191b937
# RENDER-ITEMS-002T: the random spherical vector 0x00d01fc6(out, r max, r min, theta max, theta min, phi max, phi min)
# and the rendered-frame counter [0x0bdc5ebc] (incremented once per rendered frame, client-frame-loop.md).
RANDOM_VECTOR, FRAME_COUNTER = 0x00d01fc6, 0x0bdc5ebc
# The helper's constants (checked against the data capture): the radius floor, the theta cap, degrees to radians
# and the phi cap.
RANDOM_VECTOR_WORDS = {0x01a80990: 0x358637bd, 0x01a7e4e4: 0x43340000, 0x01a7fd6c: 0x3c8efa35, 0x01a7df34: 0x43b40000}
RAND_MAX = 0x7fff
EFFECTS = (TRANSFORM, SPRITE, PARTICLE, RANGE, RAND)
PRE_EFFECTS = EFFECTS + (BONE_SPRITE, NAMED, ITEM_TRANSFORM, JOINT)
BODY_HELPER = 0x016e036c
CLOCK, SINE = 0x06fce370, 0x009681bd
OBJDRAW = (0x0176ce74, 0x017e6312)
SIGN_MASK = 0x01a7df40
DATA_BASE = 0x01a7c000
FRAME_LOW = 0x6000          # frame bytes kept below EBP at the block start
PRE_FRAME_LOW = 0x12800     # RenderObjDraw's frame (0x127d4 bytes)
OBJECT_WORDS = 1 << 24      # interpreter memory keys of OBJECT fields written by a case (RENDER-ITEMS-002S)

# Op codes of item_owner_fx.h (see the header comment written by render()).
OP = dict(const=1, mov=2, mul=3, add=4, sub=5, div=6, neg=7, gate=8, range=9, transform=10, norm=11, angle=12,
          sprite=13, particle=14, wave=15, named=16, bone_sprite=17, visible=18, alpha=19, time=20, sin=21, abs=22, randmod=23, item_transform=24, particle_owner=25,
          # RENDER-ITEMS-002S: integer registers, runtime branches and further services
          ftoi=26, itof=27, imod=28, iquot=29, iadd=30, isub=31, imul=32, irand=33, cond=34, jump=35, bones=36,
          light=37, position=38, joint=39, sprite_rot=40, umod=41,
          # RENDER-ITEMS-002T: the frame counter, OBJECT-bone positions, the random vector, bounded array selects and
          # CreateParticle with a register bitmap and argument 8
          frame=42, object_transform=43, random_vector=44, select=45, particle_reg=46, particle_reg_owner=47,
          bitmap=48, owner_item_transform=49, object_point=50)
OBJECT_BONE = 0x0129f12c    # OBJECT->bone matrix: +0x318 + 0x30 * bone, 0 without one (RENDER-ITEMS-002T)
# Runtime branch conditions (op 34 e): the jcc index; +0x10 = float flags (comiss/ucomiss), else integer flags.
CONDITIONS = ['je', 'jne', 'jl', 'jge', 'jg', 'jle', 'jb', 'jae', 'ja', 'jbe', 'jne_u', 'je_o']
REGISTERS = 4096    # owner_fx.inc run_fx register file (RENDER-ITEMS-002S; part 18 used 1024)
BINARY = {'mulss': 'mul', 'addss': 'add', 'subss': 'sub', 'divss': 'div'}


class Refused(Exception):
    pass


class NeedPhi(Exception):
    """A read of a slot whose value differs between the two paths joining at a branch target: the reading is
    restarted with that (target, slot) joined into a register (RENDER-ITEMS-002S)."""


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

def survey(wa, t, EFFECTS=EFFECTS):
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


def type_compare(md, text, block, size):
    """True when the basic block compares OBJECT +0x5c or the type argument with an immediate."""
    for i in md.disasm(text[block - 0x401000:block - 0x401000 + size], block):
        if i.mnemonic == 'cmp' and re.match(r'^dword ptr \[(eax \+ 0x5c|ebp \+ 0xc)\], 0x[0-9a-f]+$', i.op_str):
            return True
    return False


def survey_pre(wa, t):
    """Pre-draw blocks: RenderObjDraw's own type case creates the effects before the body helper. Return (case
    start, last effect site, frames at the case start). The case starts at the executed basic block after the last
    type compare that precedes the first effect service."""
    import capstone
    import validate_renderchar as v
    from unicorn import UC_HOOK_BLOCK, UC_HOOK_CODE

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    log, frames, start = [], [], [None]
    services = DRAWS + PRE_EFFECTS + (BODY_HELPER,)

    class World(v.World):
        def install(self):
            super().install()
            m = self.m

            def site(name):
                def hook(uc, address, size, context):
                    log.append((name, m.r32(uc.reg_read(m.x86.UC_X86_REG_ESP))))
                return hook
            for address in services:
                name = 'draw' if address in DRAWS else address
                if address in m.stubs:
                    old, cleanup = m.stubs[address]

                    def wrapped(mm, old=old, name=name):
                        log.append((name, mm.r32(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP))))
                        return old(mm)
                    m.stub(address, wrapped, cleanup)
                else:
                    m.uc.hook_add(UC_HOOK_CODE, site(name), begin=address, end=address)

            def block(uc, address, size, context):
                log.append(('block', address, size))
            m.uc.hook_add(UC_HOOK_BLOCK, block, begin=OBJDRAW[0], end=OBJDRAW[1])

            def snapshot(uc, address, size, context):
                ebp = uc.reg_read(m.x86.UC_X86_REG_EBP)
                frames.append((ebp, m.read(ebp - PRE_FRAME_LOW, PRE_FRAME_LOW + 0x20)))
            if start[0] is not None:
                m.uc.hook_add(UC_HOOK_CODE, snapshot, begin=start[0], end=start[0])

    first = None
    configs = v.CLASSIFY[:4]
    for config in configs:
        log.clear()
        result, _, _, _ = v.client_stream(wa, v.classify_case(t, config), World)
        if not result['ok']:
            raise Refused(f'client stops at {result["pc"]}')
        i = next((k for k, e in enumerate(log) if e[0] in PRE_EFFECTS), None)
        if i is None:
            raise Refused('no effect service in the survey state')
        if any(e[0] in ('draw', BODY_HELPER) for e in log[:i]):
            raise Refused('a draw before the first effect service')
        blocks = [e for e in log[:i] if e[0] == 'block']
        k = max((j for j, e in enumerate(blocks) if type_compare(md, wa[0], e[1], e[2])), default=None)
        if k is None or k + 1 >= len(blocks):
            raise Refused('no type compare before the effects')
        later = [e for e in log[i:] if e[0] in ('draw', BODY_HELPER)]
        j = next((k for k, e in enumerate(log) if e[0] in ('draw', BODY_HELPER)), len(log))
        effects = [e[1] for e in log[:j] if e[0] in PRE_EFFECTS and e[0] != RAND]
        if not later:
            raise Refused('no body draw after the effects')
        # RANGE also computes body-draw scalars after the helper. Those calls are not effect requests.
        if any(e[0] in PRE_EFFECTS and e[0] not in (RAND, RANGE) for e in log[j:]):
            raise Refused('effect services also after the body draws')
        here = (blocks[k + 1][1], max(effects))
        if first is None:
            first = here
        elif first != here:
            raise Refused('the case bounds differ between states')
    start[0] = first[0]
    for config in configs:
        v.client_stream(wa, v.classify_case(t, config), World)
    if len(frames) != len(configs):
        raise Refused('case start not reached once in every state')
    return first[0], first[1], frames


# ---------------------------------------------------------------- static part: the abstract interpreter

class Program:
    def __init__(self):
        self.ops = []
        self.regs = 0
        self.ranges = {}    # RENDER-ITEMS-002T: integer register -> (lo, hi) when bounded (array selects)

    def reg(self, count=1):
        r = self.regs
        self.regs += count
        if self.regs > REGISTERS:
            raise Refused(f'more than {REGISTERS} registers')
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

    # RENDER-ITEMS-002S: integer words (int32 in a register's bits).
    def integer(self, word):
        if word[0] == 'i':
            return word[1]
        if word[0] == 'c':
            r = self.reg()
            self.emit('const', r, k=word[1])
            return r
        raise Refused(f'not an integer value: {word}')

    def ibinary(self, op, a, b):
        if a[0] == 'c' and b[0] == 'c':
            return ('c', ifold(op, a[1], b[1]))
        if op in ('imod', 'iquot', 'umod') and b[0] == 'c' and b[1] == 0:
            raise Refused('constant integer division by zero')
        r = self.reg()
        self.emit(op, r, self.integer(a), self.integer(b))
        self.ranges[r] = self.bound(op, a, b)
        return ('i', r)

    def range_of(self, word):
        if word[0] == 'c':
            return (_signed(word[1]), _signed(word[1]))
        return self.ranges.get(word[1]) if word[0] == 'i' else None

    def bound(self, op, a, b):
        """(lo, hi) of an integer result from its operands' bounds (RENDER-ITEMS-002T), None when unbounded."""
        x, y = self.range_of(a), self.range_of(b)
        if op == 'umod' and y is not None and y[0] == y[1] and y[0] > 0:
            return (0, y[0] - 1)
        if x is None or y is None:
            return None
        if op in ('imod', 'umod') and y[0] == y[1] and y[0] > 0 and x[0] >= 0:
            return (0, min(x[1], y[0] - 1))
        if op == 'iadd':
            lo, hi = x[0] + y[0], x[1] + y[1]
        elif op == 'isub':
            lo, hi = x[0] - y[1], x[1] - y[0]
        elif op == 'imul' and y[0] == y[1] and y[0] >= 0:
            lo, hi = x[0] * y[0], x[1] * y[0]
        else:
            return None
        return (lo, hi) if -2**31 <= lo <= hi < 2**31 else None

    def move(self, r, word):
        """r = word (a constant or a register of either kind)."""
        if word[0] == 'c':
            self.emit('const', r, k=word[1])
        elif word[0] in ('r', 'i'):
            self.emit('mov', r, word[1])
        else:
            raise Refused(f'join of a non-value {word}')

    def patch(self, index, target):
        self.ops[index] = self.ops[index][:-1] + (target,)


MEM = re.compile(r'^dword ptr \[(ebp|esp|eax|ecx|edx|esi|edi)(?: ([+-]) (0x[0-9a-f]+|\d+))?\]$')
INDEX = re.compile(r'^dword ptr \[(eax|ecx|edx|esi|edi) \+ (eax|ecx|edx|esi|edi)\]$')
ABS = re.compile(r'^(?:dword|xmmword) ptr \[(0x[0-9a-f]+)\]$')


def operand(text):
    if text == 'dword ptr [eax + ecx]':
        return ('index',)       # a float array element: ecx = lea of the array, eax = 4 * constant index
    m = INDEX.match(text)
    if m:
        return ('index', m.group(1), m.group(2))   # RENDER-ITEMS-002S: any two registers, either order
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


def _signed(x):
    return x - (1 << 32) if x & 0x80000000 else x


def ifold(op, a, b):
    """x86 result of one 32-bit integer operation on two constant words."""
    x, y = _signed(a), _signed(b)
    if op in ('imod', 'iquot') and (y == 0 or (x == -2**31 and y == -1)):
        raise Refused('constant idiv fault')
    if op == 'umod' and b == 0:
        raise Refused('constant div fault')
    q = abs(x) // abs(y) * (1 if (x < 0) == (y < 0) else -1) if op in ('imod', 'iquot') else 0
    r = {'iadd': lambda: x + y, 'isub': lambda: x - y, 'imul': lambda: x * y, 'iquot': lambda: q,
         'imod': lambda: x - q * y, 'umod': lambda: a % b}[op]()
    return r & 0xffffffff


# Conditional jumps on two constant 32-bit words (cmp a, b), decided statically in pre-draw blocks.
JCC = {'je': lambda a, b: a == b, 'jne': lambda a, b: a != b,
       'jl': lambda a, b: _signed(a) < _signed(b), 'jge': lambda a, b: _signed(a) >= _signed(b),
       'jg': lambda a, b: _signed(a) > _signed(b), 'jle': lambda a, b: _signed(a) <= _signed(b),
       'jb': lambda a, b: a < b, 'jae': lambda a, b: a >= b, 'ja': lambda a, b: a > b, 'jbe': lambda a, b: a <= b}


class Interpreter:
    def __init__(self, wa, frames, start, last, pre=False, need=(), post=False):
        import capstone
        self.post = post        # RENDER-ITEMS-002T: RenderPartObjectBody's frame with the pre-draw idioms
        self.owner_bones = []
        self.need = set(need)   # (branch target, slot) pairs joined into registers (RENDER-ITEMS-002S)
        self.pre, self.low = pre, PRE_FRAME_LOW if pre and not post else FRAME_LOW
        self.names = []
        self.text, self.data = wa[0], wa[1]
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.frames, self.start, self.last = frames, start, last
        self.mem, self.stack, self.reg = {}, [], {}
        self.xmm0 = self.st0 = None
        self.p = Program()
        self.pending = []       # (target address, op index of the gate, saved state)
        self.skips = []         # pre-draw: (target, op index) of visibility tests that leave the case
        self.bones = []

    # memory -------------------------------------------------------------
    def frame_word(self, off):
        words = set()
        for ebp, raw in self.frames:
            i = self.low + off
            if not 0 <= i <= len(raw) - 4:
                raise Refused(f'frame word {off:#x} outside the snapshot')
            words.add(struct.unpack_from('<I', raw, i)[0])
        if len(words) != 1:
            raise Refused(f'frame word ebp{off:+#x} differs between states')
        return ('c', words.pop())

    def load(self, ptr, k=0):
        if ptr[0] == 'select':
            return self.select(ptr[1], ptr[2])
        if ptr[0] == 'frame':
            off = ptr[1] + 4 * k
            w = self.mem.get(off)
            if w is None:
                w = self.frame_word(off)
            return self.use(w)
        if ptr[0] == 'objptr' and OBJECT_WORDS + ptr[1] + 4 * k in self.mem:
            return self.use(self.mem[OBJECT_WORDS + ptr[1] + 4 * k])
        if ptr[0] == 'objptr' and ptr[1] == 0x164:
            return ('angle', k)
        if self.pre and ptr[0] in ('objptr', 'lightptr'):
            # RENDER-ITEMS-002S: OBJECT position (+0x158) and light argument components, read where used.
            lo = 0x158 if ptr[0] == 'objptr' else 0
            i = ptr[1] + 4 * k - lo
            if i % 4 or not 0 <= i < 12:
                raise Refused(f'load through {ptr}')
            base = self.p.reg(3)
            self.p.emit('position' if ptr[0] == 'objptr' else 'light', base)
            return ('r', base + i // 4)
        raise Refused(f'load through {ptr}')

    def select(self, base, index):
        """RENDER-ITEMS-002T: frame word base + index (bytes, a bounded integer register): every word the index can
        reach is copied into consecutive registers and the select op picks one at run time."""
        bound = self.p.range_of(index)
        if bound is None or bound[0] < 0 or bound[1] - bound[0] > 0x100 or bound[0] % 4:
            raise Refused(f'array select index {index} {bound}')
        words = [self.load(('frame', base + off)) for off in range(0, bound[1] + 4 - bound[1] % 4, 4)]
        kinds = {w[0] for w in words} - {'c'}
        if not kinds <= {'r'} and not kinds <= {'i'}:
            raise Refused(f'array select of {words}')
        kind = kinds.pop() if kinds else 'r'
        table = self.p.reg(len(words))
        for k, w in enumerate(words):
            self.p.move(table + k, w)
        r = self.p.reg()
        self.p.emit('select', r, index[1], table, len(words))
        if kind == 'i':
            values = [self.p.range_of(w) for w in words]
            if all(values):
                self.p.ranges[r] = (min(x[0] for x in values), max(x[1] for x in values))
        return (kind, r)

    def use(self, w):
        """A word being read: a value that differs between joined paths restarts the reading with a join."""
        if w is not None and w[0] == 'phi':
            if len(w) == 3 and (w[1], w[2]) not in self.need:
                raise NeedPhi((w[1], w[2]))
            raise Refused('read of a word after a gated write')
        return w

    def store(self, ptr, k, w):
        if self.pre and ptr[0] == 'objptr' and not 0x158 <= ptr[1] + 4 * k < 0x170:
            offset = ptr[1] + 4 * k
            if 0x1f4 <= offset < 0x218 and offset % 4 == 0:
                # RENDER-EFFECTS-022: RenderParticles reads these nine words after the item draw.
                self.p.emit('object_point', self.p.scalar(w), (offset - 0x1f4) // 4)
            self.mem[OBJECT_WORDS + offset] = w    # RENDER-ITEMS-002S: OBJECT fields the case writes
            return
        if ptr[0] != 'frame':
            raise Refused(f'store through {ptr}')
        self.mem[ptr[1] + 4 * k] = w

    def vec(self, ptr):
        if ptr[0] == 'objptr' and ptr[1] == 0x164:
            base = self.p.reg(3)
            self.p.emit('angle', base)
            return [('r', base + k) for k in range(3)]
        if self.pre and ptr in (('objptr', 0x158), ('lightptr', 0)):
            base = self.p.reg(3)
            self.p.emit('position' if ptr[0] == 'objptr' else 'light', base)
            return [('r', base + k) for k in range(3)]
        return [self.load(ptr, k) for k in range(3)]

    def absolute(self, address):
        i = address - DATA_BASE
        if not 0 <= i <= len(self.data) - 4:
            raise Refused(f'constant {address:#x} outside the data capture')
        return ('c', struct.unpack_from('<I', self.data, i)[0])

    def cstring(self, address):
        i = address - DATA_BASE
        if not 0 <= i < len(self.data):
            raise Refused(f'string {address:#x} outside the data capture')
        end = self.data.index(b'\0', i)
        raw = self.data[i:end]
        if not 0 < len(raw) < 32 or not all(0x20 <= c < 0x7f for c in raw):
            raise Refused(f'bone name {raw!r}')
        return raw.decode()

    def element(self, regs=('eax', 'ecx')):
        index, base = self.reg.get(regs[0]), self.reg.get(regs[1])
        if base and base[0] != 'frame' and index and index[0] == 'frame':
            index, base = base, index
        if self.pre and index and index[0] == 'i' and base and base[0] == 'frame':
            return ('select', base[1], index)      # RENDER-ITEMS-002T: an array element at a bounded runtime index
        if not self.pre or not index or index[0] != 'c' or not base or base[0] != 'frame' or index[1] % 4 or \
                index[1] > 0xfc:
            raise Refused(f'array element {index} {base}')
        return ('frame', base[1] + index[1])

    def read(self, opnd):
        kind = opnd[0]
        if kind == 'index':
            return self.load(self.element(opnd[1:] or ('eax', 'ecx')))
        if kind == 'abs' and self.pre and opnd[1] == FRAME_COUNTER:
            r = self.p.reg()       # RENDER-ITEMS-002T: the rendered-frame counter (unsigned)
            self.p.emit('frame', r)
            return ('i', r)
        if kind == 'abs' and self.pre and opnd[1] == CLOCK:
            r = self.p.reg()
            self.p.emit('time', r)
            return ('r', r)
        if kind == 'abs':
            return self.absolute(opnd[1])
        if kind == 'imm':
            return ('c', opnd[1])
        if kind == 'mem':
            base, off = opnd[1], opnd[2]
            if base == 'ebp' and self.pre and not self.post:
                # RenderObjDraw(OBJECT, type, light, alpha, ...); the item model is the local at ebp-0xb0.
                if off == 8:
                    return ('object',)
                if off == -0xb0:
                    return ('model',)
                if off == 0x14:
                    r = self.p.reg()
                    self.p.emit('alpha', r)
                    return ('r', r)
                if off == 0x10:
                    return ('lightptr', 0)      # RENDER-ITEMS-002S: the light argument (float[3])
                if off < 0:
                    return self.load(('frame', off))
            elif base == 'ebp':
                if off == 8:
                    return ('model',)
                if off == 0xc:
                    return ('object',)
                if off < 0:
                    return self.load(('frame', off))
            if base == 'esp':
                if off % 4 or off // 4 >= len(self.stack):
                    raise Refused('stack read outside the pushed arguments')
                return self.use(self.stack[-1 - off // 4])
            if base in ('eax', 'ecx', 'edx', 'esi', 'edi') and self.pre and \
                    (self.reg.get(base) or ('',))[0] in ('frame', 'objptr', 'lightptr'):
                ptr = self.reg[base]
                return self.load((ptr[0], ptr[1] + off))
            raise Refused(f'read {opnd}')
        if kind == 'reg':
            w = self.reg.get(opnd[1])
            if w is None:
                raise Refused(f'read of unset {opnd[1]}')
            if w[0] == 'lazy':      # idiv/div results, emitted when read
                w = self.reg[opnd[1]] = self.p.ibinary(w[1], w[2], w[3])
            return self.use(w)
        raise Refused(f'read {opnd}')

    def write(self, opnd, w):
        if opnd[0] == 'index':
            self.store(self.element(opnd[1:] or ('eax', 'ecx')), 0, w)
        elif opnd[0] == 'mem' and opnd[1] in ('eax', 'ecx') and self.pre and \
                (self.reg.get(opnd[1]) or ('',))[0] == 'frame':
            self.store(('frame', self.reg[opnd[1]][1] + opnd[2]), 0, w)
        elif opnd[0] == 'mem' and opnd[1] in ('eax', 'ecx') and self.pre and \
                (self.reg.get(opnd[1]) or ('',))[0] == 'objptr':
            self.store(('objptr', self.reg[opnd[1]][1] + opnd[2]), 0, w)    # RENDER-ITEMS-002T: OBJECT fields
        elif opnd[0] == 'mem' and opnd[1] == 'ebp' and opnd[2] < 0:
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
        return self.use(self.stack[-1 - k])

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
        elif target == TRANSFORM and self.pre:        # RENDER-ITEMS-002T: model->0x012b678d(out, OBJECT, bone, NULL)
            out, owner, bone, local = (self.arg(k) for k in range(4))
            if ecx != ('model',) or owner != ('object',) or local != ('c', 0) or bone[0] not in ('c', 'i') or \
                    out[0] not in ('frame', 'objptr'):
                raise Refused(f'object transform operands {ecx} {owner} {bone} {local}')
            if bone[0] == 'c':
                if _signed(bone[1]) >= 0x100:
                    raise Refused(f'object transform bone {bone}')
                if bone[1] < 0x100:
                    self.bones.append(bone[1])
            base = p.reg(3)
            p.emit('object_transform', base, p.integer(bone))
            for k in range(3):
                self.store(out, k, ('r', base + k))
            self.pop(4)
            self.reg['eax'] = ('junk',)
        elif target == RANDOM_VECTOR and self.pre:    # cdecl (out, six floats), the radius on x87
            for address, word in RANDOM_VECTOR_WORDS.items():
                if self.absolute(address) != ('c', word):
                    raise Refused(f'random vector constant {address:#x}')
            out = self.arg(0)
            if out[0] != 'frame':
                raise Refused(f'random vector output {out}')
            args = p.reg(6)
            for k in range(6):
                p.move(args + k, self.arg(k + 1))
            base = p.reg(4)
            p.emit('random_vector', base, args)
            for k in range(3):
                self.store(out, k, ('r', base + k))
            self.st0 = ('r', base + 3)
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
        elif target == SPRITE and self.pre and (self.arg(5) != ('c', 0) or self.arg(6) != ('c', 0)):
            # RENDER-ITEMS-002S: CreateSprite with a rotation (argument 6) and blend word (argument 7).
            a = [self.arg(k) for k in range(9)]
            axes = self.vec(a[8])
            if a[4] != ('object',) or a[6][0] != 'c' or a[6][1] > 0xff or a[7] != ('c', 4) or a[0][0] != 'c' or \
                    tuple(axes) != (('c', 1), ('c', 1), self.absolute(0x01a7dd48)):
                raise Refused(f'sprite arguments {a}')
            pos = p.vector(self.vec(a[1]))
            light = p.vector(self.vec(a[3]))
            p.emit('sprite_rot', pos, p.scalar(a[2]), light, p.scalar(a[5]), a[6][1], k=a[0][1])
            self.reg['eax'] = ('junk',)
        elif target == JOINT and self.pre:            # cdecl, 14 arguments
            a = [self.arg(k) for k in range(14)]
            fixed = tuple(a[7:])
            if a[0][0] != 'c' or a[0][1] > 0xffff or a[4][0] != 'c' or a[4][1] > 0xff or a[5] != ('object',) or \
                    fixed != (('c', 0xffffffff), ('c', 0), ('c', 0), ('c', 0xffffffff), ('c', 0), ('c', 0xffffffff), ('c', 0)):
                raise Refused(f'joint arguments {a}')
            pos = p.vector(self.vec(a[1]))
            aim = p.vector(self.vec(a[2]))
            angle = p.vector(self.vec(a[3]))
            p.emit('joint', pos, aim, angle, p.scalar(a[6]), a[4][1], k=a[0][1])
            self.reg['eax'] = ('junk',)
        elif target == SPRITE:                         # cdecl, 9 arguments
            a = [self.arg(k) for k in range(9)]
            axes = self.vec(a[8])
            fixed = (a[4], a[5], a[6], a[7], tuple(axes))
            if fixed != (('object',), ('c', 0), ('c', 0), ('c', 4),
                         (('c', 1), ('c', 1), self.absolute(0x01a7dd48))) or a[0][0] not in ('c', 'i') or \
                    a[0][0] == 'i' and not self.pre:
                raise Refused(f'sprite arguments {a[0]} {fixed}')
            pos = p.vector(self.vec(a[1]))
            light = p.vector(self.vec(a[3]))
            if a[0][0] == 'i':
                p.emit('bitmap', a[0][1])      # RENDER-ITEMS-002T: the next request's bitmap from a register
            p.emit('sprite', pos, p.scalar(a[2]), light, k=a[0][1] if a[0][0] == 'c' else 0)
            self.reg['eax'] = ('junk',)
        elif target == PARTICLE and self.pre and (self.arg(7) != ('c', 0) or self.arg(0)[0] == 'i'):
            # RENDER-ITEMS-002T: a bitmap computed at run time (rand() % 3 + base) or a register argument 8.
            a = [self.arg(k) for k in range(8)]
            owner = a[6] == ('object',)
            if a[0][0] not in ('c', 'i') or a[4][0] != 'c' or a[4][1] > 0xff or (a[6] != ('c', 0) and not owner) or \
                    a[7][0] not in ('c', 'i'):
                raise Refused(f'particle arguments {a}')
            pos = p.vector(self.vec(a[1]))
            angle = p.vector(self.vec(a[2]))
            light = p.vector(self.vec(a[3]))
            pair = p.reg(2)
            p.move(pair, a[0])
            p.move(pair + 1, a[7])
            p.emit('particle_reg_owner' if owner else 'particle_reg', pos, angle, light, p.scalar(a[5]), a[4][1], k=pair)
            self.reg['eax'] = ('junk',)
        elif target == PARTICLE:                       # cdecl, 8 arguments
            a = [self.arg(k) for k in range(8)]
            owner = self.pre and a[6] == ('object',)
            if a[0][0] != 'c' or a[4][0] != 'c' or a[4][1] > 0xff or (a[6] != ('c', 0) and not owner) or \
                    a[7] != ('c', 0):
                raise Refused(f'particle arguments {a}')
            pos = p.vector(self.vec(a[1]))
            angle = p.vector(self.vec(a[2]))
            light = p.vector(self.vec(a[3]))
            p.emit('particle_owner' if owner else 'particle', pos, angle, light, p.scalar(a[5]), a[4][1], k=a[0][1])
            self.reg['eax'] = ('junk',)
        elif target == STRING and self.pre:          # std::string(const char *) on a frame object, ret 4
            name = self.arg(0)
            if ecx is None or ecx[0] != 'frame' or name[0] not in ('c', 'text'):
                raise Refused(f'string operands {ecx} {name}')
            self.store(ecx, 0, ('string', self.cstring(name[1]) if name[0] == 'c' else name[1]))
            self.pop(1)
            self.reg['eax'] = ecx
        elif target == STRING_FREE and self.pre:     # ~std::string
            self.reg['eax'] = ('junk',)
        # RENDER-ITEMS-002S: names built as literal + _itoa(n), and MSVC's EH vector iterators.
        elif target == ITOA and self.pre:            # cdecl _itoa(value, buffer, radix)
            n, buf, radix = self.arg(0), self.arg(1), self.arg(2)
            if n[0] != 'c' or buf[0] != 'frame' or radix != ('c', 10):
                raise Refused(f'itoa operands {n} {buf} {radix}')
            self.store(buf, 0, ('text', str(_signed(n[1]))))
            self.reg['eax'] = buf
        elif target == STRING_APPEND and self.pre:   # std::string::append(const char *), ret 4
            text = self.arg(0)
            text = self.load(text) if text[0] == 'frame' else text
            old = self.load(ecx) if ecx and ecx[0] == 'frame' else None
            if not old or old[0] != 'string' or text[0] != 'text':
                raise Refused(f'string append operands {old} {text}')
            self.store(ecx, 0, ('string', old[1] + text[1]))
            self.pop(1)
            self.reg['eax'] = ecx
        elif target == STRING_CSTR and self.pre:     # std::string::c_str()
            w = self.load(ecx) if ecx and ecx[0] == 'frame' else None
            if not w or w[0] != 'string':
                raise Refused(f'c_str of {w}')
            self.reg['eax'] = ('text', w[1])
        elif target == VECTOR_CTOR and self.pre:     # eh vector constructor iterator(p, size, n, ctor, dtor), ret 0x14
            ptr, size, n, ctor = (self.arg(k) for k in range(4))
            if ptr[0] != 'frame' or size != ('c', 0xc) or n[0] != 'c' or ctor != ('c', 0x0095ea8e) or n[1] > 0x100:
                raise Refused(f'vector constructor {ptr} {size} {n} {ctor}')
            for k in range(3 * n[1]):
                self.store(ptr, k, ('c', 0))
            self.pop(5)
        elif target == VECTOR_DTOR and self.pre:     # eh vector destructor iterator(p, size, n, dtor), ret 0x10
            self.pop(4)
        elif target == NAMED and self.pre:           # model->0x012bd35a(name, fallback), ret 8
            name, fallback = self.load(self.arg(0)), self.arg(1)
            if ecx != ('model',) or name[0] != 'string' or fallback != ('c', 0xffffffff):
                raise Refused(f'named bone operands {ecx} {name} {fallback}')
            if name[1] not in self.names:
                self.names.append(name[1])
            r = p.reg()
            p.emit('named', r, k=self.names.index(name[1]))
            self.pop(2)
            self.reg['eax'] = ('i', r)
        elif target == WAVE and self.pre:            # cdecl 0x0185bdc4(a, b), result on x87
            a, b = self.arg(0), self.arg(1)
            # 0x2301/0x2302 call (0, -4). Masked SSE division and CVTT produce
            # INT_MIN for both dividend and divisor, a zero remainder and exact +0.
            if a == ('c', 0) and b == ('c', 0xc0800000):
                self.st0 = ('c', 0)
                self.reg['eax'] = ('junk',)
                return
            if a[0] != 'c' or b != ('c', 0) or value(a[1]) == 0:
                raise Refused(f'wave operands {a} {b}')
            r = p.reg()
            p.emit('wave', r, k=a[1])
            self.st0 = ('r', r)
            self.reg['eax'] = ('junk',)
        elif target in (0x009f413c, 0x00cfcede) and self.pre:   # vec3(s) / set(s): all three s, ret 4
            for k in range(3):
                self.store(ecx, k, self.arg(0))
            self.pop(1)
            self.reg['eax'] = ecx
        elif target == 0x00cfc922 and self.pre:      # &this[i], ret 4
            i, base = self.arg(0), ecx
            if i[0] != 'c' or i[1] > 2 or not base or base[0] not in ('frame', 'objptr', 'lightptr'):
                raise Refused(f'element operands {base} {i}')
            self.pop(1)
            self.reg['eax'] = (base[0], base[1] + 4 * i[1])
        elif target in (0x0095ea8e, 0x00cfcf7b) and self.pre:   # vec3() / zero(): all three 0
            for k in range(3):
                self.store(ecx, k, ('c', 0))
            self.reg['eax'] = ecx
        elif target == SINE and self.pre:            # cdecl 0x009681bd(x): (float)sin((double)x) on x87
            x = self.arg(0)
            r = p.reg()
            p.emit('sin', r, p.scalar(x))
            self.st0 = ('r', r)
            self.reg['eax'] = ('junk',)
        elif target == 0x0184f8ff and self.pre:       # cdecl abs by comparison: 0 > x ? -x : x, on x87
            r = p.reg()
            p.emit('abs', r, p.scalar(self.arg(0)))
            self.st0 = ('r', r)
            self.reg['eax'] = ('junk',)
        elif target == 0x00cfcd74:                     # this *= s (0x00cfcb3c, then assign), ret 4
            s = self.arg(0)
            a = self.vec(ecx)
            result = [p.binary('mul', a[k], s) for k in range(3)]
            for k in range(3):
                self.store(ecx, k, result[k])
            self.pop(1)
            self.reg['eax'] = ecx
        elif target == OBJECT_BONE and self.post:     # RENDER-ITEMS-002T: OBJECT->0x0129f12c(bone), ret 4
            bone = self.arg(0)
            if ecx != ('object',) or bone[0] != 'c' or bone[1] >= 0x100:
                raise Refused(f'object bone operands {ecx} {bone}')
            self.pop(1)
            self.reg['eax'] = ('ownerptr', bone[1])
        elif target == ITEM_TRANSFORM and self.post and (self.arg(0) or ('',))[0] == 'ownerptr':
            # TransformPosition 0x012b6ef1 on the OBJECT's own bone matrix (item model scale and origin)
            matrix, local, out, translate = (self.arg(k) for k in range(4))
            if ecx != ('model',) or translate not in (('c', 0), ('c', 1)) or out[0] != 'frame':
                raise Refused(f'owner item transform operands {ecx} {matrix} {translate}')
            self.owner_bones.append(matrix[1])
            src = p.vector(self.vec(local))
            base = p.reg(3)
            p.emit('owner_item_transform', base, 0, src, 0, translate[1], k=matrix[1])
            for k in range(3):
                self.store(out, k, ('r', base + k))
            self.pop(4)
            self.reg['eax'] = ('junk',)
        elif target == ITEM_TRANSFORM and self.pre:  # model->TransformPosition(BoneTransform + 0x30 bone, local, out, t), ret 0x10
            matrix, local, out, translate = (self.arg(k) for k in range(4))
            if ecx != ('model',) or matrix[0] != 'boneptr' or translate not in (('c', 0), ('c', 1)) or \
                    out[0] != 'frame':
                raise Refused(f'item transform operands {ecx} {matrix} {translate}')
            bone = matrix[1]
            if bone[0] == 'c':
                self.bones.append(bone[1])
                b = p.reg()
                p.emit('const', b, k=bone[1])
            else:
                b = bone[1]
            src = p.vector(self.vec(local))
            base = p.reg(3)
            p.emit('item_transform', base, b, src, k=translate[1])
            for k in range(3):
                self.store(out, k, ('r', base + k))
            self.pop(4)
            self.reg['eax'] = ('junk',)
        elif target == BONE_SPRITE and self.pre:     # cdecl, 9 arguments
            a = [self.arg(k) for k in range(9)]
            axes = self.vec(a[8])
            if a[0] != ('model',) or a[1][0] != 'c' or a[5] != ('object',) or a[7][0] != 'c' or a[7][1] > 0xff or \
                    tuple(axes) != (('c', 1), ('c', 1), self.absolute(0x01a7dd48)):
                raise Refused(f'bone sprite arguments {a}')
            if a[2][0] == 'i':
                bone = a[2][1]
            elif a[2][0] == 'c' and a[2][1] < 0x100:
                bone = p.reg()
                p.emit('const', bone, k=a[2][1])
                self.bones.append(a[2][1])
            else:
                raise Refused(f'bone sprite bone {a[2]}')
            light = p.vector(self.vec(a[4]))
            p.emit('bone_sprite', bone, p.scalar(a[3]), light, p.scalar(a[6]), a[7][1], k=a[1][1])
            self.reg['eax'] = ('junk',)
        elif target in DRAWS:
            raise Refused('draw inside the effect block')
        else:
            raise Refused(f'call {target:#x}')

    # control ------------------------------------------------------------
    GATE = [('and', None), ('jns', None), ('dec', 'eax'), ('or', None),
            ('inc', 'eax'), ('test', 'eax, eax'), ('jne', None)]

    RAND_VALUE = [('cdq', ''), ('push', None), ('pop', 'ecx'), ('idiv', 'ecx'), ('cvtsi2ss', 'xmm0, edx')]

    GATE_IDIV = [('cdq', ''), ('push', None), ('pop', 'ecx'), ('idiv', 'ecx'), ('test', 'edx, edx'), ('jne', None)]

    def integer_op(self, mn, ops):
        """imul/add/sub/shl/inc/dec of a general register holding an integer word; False when not one."""
        parts = [x.strip() for x in ops.split(',')]
        dst = parts[0]
        if dst not in ('eax', 'ecx', 'edx', 'esi', 'edi'):
            return False
        cur = self.reg.get(dst)
        if mn in ('inc', 'dec'):
            if not cur or cur[0] not in ('c', 'i'):
                return False
            self.reg[dst] = self.p.ibinary('iadd', self.read(('reg', dst)), ('c', 1 if mn == 'inc' else 0xffffffff))
            return True
        if mn == 'imul' and len(parts) == 3:
            src = self.read(operand(parts[1]))
            k = int(parts[2], 0) & 0xffffffff
            if src[0] == 'i' and k == 0x30:
                self.reg[dst] = ('scaled', src)        # a bone's matrix offset
            elif src[0] in ('c', 'i'):
                self.reg[dst] = self.p.ibinary('imul', src, ('c', k))
            else:
                return False
            return True
        if mn == 'add' and cur == ('object',) and parts[1] in ('eax', 'ecx', 'edx') and \
                (self.reg.get(parts[1]) or ('',))[0] == 'c':
            self.reg[dst] = ('objptr', self.reg[parts[1]][1])
            return True
        if mn == 'add' and cur in (('object',),) and re.match(r'^(0x[0-9a-f]+|\d+)$', parts[1]):
            self.reg[dst] = ('objptr', int(parts[1], 0))
            return True
        src = self.read(operand(parts[1]))
        if mn == 'add' and cur and cur[0] == 'c' and src[0] in ('objptr', 'lightptr', 'frame'):
            self.reg[dst] = (src[0], src[1] + cur[1])    # constant index plus a pointer
            return True
        if mn == 'add' and cur and cur[0] in ('objptr', 'lightptr') and src[0] == 'c':
            self.reg[dst] = (cur[0], cur[1] + src[1])
            return True
        if not cur or cur[0] not in ('c', 'i') and not (cur[0] == 'lazy'):
            return False
        a = self.read(('reg', dst))
        if mn == 'shl':
            if src[0] != 'c' or src[1] > 31:
                return False
            self.reg[dst] = self.p.ibinary('imul', a, ('c', 1 << src[1]))
        elif src[0] in ('c', 'i'):
            self.reg[dst] = self.p.ibinary('iadd' if mn == 'add' else 'isub' if mn == 'sub' else 'imul', a, src)
        else:
            return False
        return True

    def merge(self, address):
        while self.pending and self.pending[-1][0] == address:
            _, index, (mem, stack) = self.pending.pop()
            if len(stack) != len(self.stack):
                raise Refused('stack depth differs at a gate target')
            slots = [('mem', off) for off in sorted(set(mem) | set(self.mem)) if mem.get(off) != self.mem.get(off)]
            slots += [('stack', k) for k, w in enumerate(stack) if w != self.stack[k]]
            joined = {}
            # RENDER-ITEMS-002S: a slot read after the join becomes one register written on both paths:
            # fall-through path, jump over the taken path's moves, taken path (the branch op continues there).
            need = [slot for slot in slots if (address, slot) in self.need]
            if need:
                def word(m, st, slot):
                    if slot[0] == 'stack':
                        return st[slot[1]]
                    return m[slot[1]] if slot[1] in m else self.frame_word(slot[1])
                for slot in need:
                    a, b = word(self.mem, self.stack, slot), word(mem, stack, slot)
                    kinds = {a[0], b[0]} - {'c'}
                    if len(kinds) > 1 or not {a[0], b[0]} <= {'c', 'r', 'i'}:
                        raise Refused(f'join of {a} and {b}')
                    joined[slot] = (kinds.pop() if kinds else 'r', self.p.reg())
                    self.p.move(joined[slot][1], a)
                jump = self.p.emit('jump')
                self.p.patch(index, len(self.p.ops))
                for slot in need:
                    self.p.move(joined[slot][1], word(mem, stack, slot))
                self.p.patch(jump, len(self.p.ops))
            else:
                self.p.patch(index, len(self.p.ops))
            for slot in slots:
                w = joined.get(slot, ('phi', address, slot))
                if slot[0] == 'mem':
                    self.mem[slot[1]] = w
                else:
                    self.stack[slot[1]] = w
            self.reg = {}
            self.xmm0 = self.st0 = None
        if any(target < address for target, _, _ in self.pending):
            raise Refused('gate target skipped')

    def run(self):
        address = self.start
        end = None
        insns = {}
        for i in self.md.disasm(self.text[self.start - 0x401000:self.last - 0x401000 + 0x400], self.start):
            insns[i.address] = i
        steps = 0
        self.flags = None
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
                for idiom in (self.GATE, self.GATE_IDIV) + ((self.RAND_VALUE,) if self.pre else ()):
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
                if seq is None and self.pre:
                    # RENDER-ITEMS-002S: rand() as an integer value (then cdq/idiv, compares, indices ...).
                    r = self.p.reg()
                    self.p.emit('irand', r)
                    self.p.ranges[r] = (0, RAND_MAX)
                    self.reg = {k: w for k, w in self.reg.items() if k not in ('eax', 'ecx', 'edx')}
                    self.reg['eax'] = ('i', r)
                    address = nxt
                    continue
                if seq is None:
                    raise Refused(f'rand outside the gate idiom at {address:#x}')
                if idiom is self.RAND_VALUE:
                    # (float)(rand() % m) into xmm0 (0x0179f04a): a value, not a gate.
                    modulus = int(seq[1].op_str, 0)
                    if not 1 < modulus < 0x10000:
                        raise Refused('rand value modulus')
                    r = self.p.reg()
                    self.p.emit('randmod', r, k=modulus)
                    self.xmm0 = ('r', r)
                    self.reg.pop('eax', None)
                    self.reg.pop('ecx', None)
                    address = a
                    continue
                if idiom is self.GATE:
                    # rand() % 2^n: and eax, 0x80000000 | (2^n - 1); jns; dec; or eax, ~(2^n - 1); inc
                    mask = re.match(r'^eax, 0x8000(00[0-9a-f]{2}|0[0-9a-f]{3})$', seq[0].op_str)
                    low = int(seq[0].op_str[5:], 16) & 0x7fffffff if mask else 0
                    if not mask or low & (low + 1) or not low or seq[3].op_str != f'eax, {0xffffffff ^ low:#x}' or \
                            int(seq[1].op_str, 16) != seq[5].address or (low != 1 and not self.pre):
                        raise Refused('gate idiom')
                    modulus = low + 1
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
            if self.pre:
                steps += 1
                if steps > 100000:
                    raise Refused('more than 100000 interpreted instructions')
            if self.pre and mn == 'jmp' and self.start <= int(ops, 16) <= self.last and \
                    all(int(ops, 16) < target for target, _, _ in self.pending):
                address = int(ops, 16)   # a loop's back edge or its jump to the condition (constant counters)
                continue
            if self.pre and mn in CONDITIONS and self.flags is not None and self.flags[0] == 'rt':
                # RENDER-ITEMS-002S: a forward branch on a runtime value becomes a cond op; both paths are read
                # and joined at the target (merge).
                _, kind, a, b = self.flags
                self.flags = None
                target = int(ops, 16)
                if target <= address or (kind and mn in ('jl', 'jge', 'jg', 'jle')):
                    raise Refused(f'runtime branch {mn} at {address:#x}')
                ra, rb = (self.p.scalar(a), self.p.scalar(b)) if kind else (self.p.integer(a), self.p.integer(b))
                index = self.p.emit('cond', ra, rb, 0, 0, kind | CONDITIONS.index(mn))
                self.pending.append((target, index, (dict(self.mem), list(self.stack))))
                self.pending.sort(key=lambda x: -x[0])
                address = nxt
                continue
            if self.pre and mn == 'jmp' and self.pending and self.pending[-1][0] == nxt and int(ops, 16) > nxt:
                # if/else: the then-path jumps over the else-path, which starts at the branch target.
                _, index, (mem, stack) = self.pending.pop()
                if self.pending and self.pending[-1][0] == nxt:
                    raise Refused(f'two branches to the else-path at {nxt:#x}')
                jump = self.p.emit('jump')
                self.pending.append((int(ops, 16), jump, (dict(self.mem), list(self.stack))))
                self.pending.sort(key=lambda x: -x[0])
                self.p.patch(index, len(self.p.ops))
                self.mem, self.stack, self.reg = dict(mem), list(stack), {}
                self.xmm0 = self.st0 = None
                address = nxt
                continue
            if self.pre and mn == 'jmp' and self.pending and all(t == int(ops, 16) for t, _, _ in self.pending) and \
                    address >= self.last:
                for _, index, _ in self.pending:     # paths that leave the case at the join: the program end
                    self.p.patch(index, len(self.p.ops))
                self.pending = []
                end = address
                break
            if self.pre and mn in JCC and self.flags is not None:
                a, b = self.flags
                taken = JCC[mn](a, b)
                self.flags = None
                address = int(ops, 16) if taken else nxt
                continue
            if mn == 'jmp':
                if self.pending or address < self.last:
                    raise Refused(f'jump inside the block at {address:#x}')
                end = address
                break
            if mn == 'nop':
                pass
            elif self.pre and mn in ('cmp', 'test'):
                a, b = (self.read(operand(x.strip())) for x in ops.split(',', 1))
                if mn == 'test':
                    nj = insns.get(nxt)
                    if a != b or not nj or nj.mnemonic not in ('je', 'jne'):
                        raise Refused(f'test {ops} at {address:#x}')
                    b = ('c', 0)
                if a[0] == 'c' and b[0] == 'c':
                    self.flags = (a[1], b[1])
                elif {a[0], b[0]} <= {'c', 'i'}:
                    self.flags = ('rt', 0, a, b)
                else:
                    raise Refused(f'cmp of {a} and {b} at {address:#x}')
            elif self.pre and mn in ('comiss', 'ucomiss'):
                dst, src = (operand(x.strip()) for x in ops.split(',', 1))
                if dst != ('reg', 'xmm0') or self.xmm0 is None:
                    raise Refused(f'{mn} {ops}')
                a, b = self.xmm0, self.read(src)
                i1 = insns.get(nxt)
                i2 = insns.get(nxt + i1.size) if i1 else None
                i3 = insns.get(i2.address + i2.size) if i2 else None
                if i1 and i1.mnemonic == 'lahf':
                    # lahf; test ah, 0x44; jp: taken unless ordered equal (jnp: ordered equal).
                    if not i2 or (i2.mnemonic, i2.op_str) != ('test', 'ah, 0x44') or not i3 or \
                            i3.mnemonic not in ('jp', 'jnp') or int(i3.op_str, 16) <= i3.address:
                        raise Refused(f'float compare idiom at {address:#x}')
                    cc = 'jne_u' if i3.mnemonic == 'jp' else 'je_o'
                    index = self.p.emit('cond', self.p.scalar(a), self.p.scalar(b), 0, 0, 0x10 | CONDITIONS.index(cc))
                    self.pending.append((int(i3.op_str, 16), index, (dict(self.mem), list(self.stack))))
                    self.pending.sort(key=lambda x: -x[0])
                    self.reg.pop('eax', None)
                    address = i3.address + i3.size
                    continue
                self.flags = ('rt', 0x10, a, b)
            elif self.pre and mn == 'xor' and len(set(x.strip() for x in ops.split(','))) == 1 and \
                    ops.split(',')[0] in ('eax', 'ecx', 'edx', 'esi', 'edi'):
                self.reg[ops.split(',')[0]] = ('c', 0)
            elif self.pre and mn == 'cdq':
                self.reg['edx'] = ('cdq',)
            elif self.pre and mn in ('idiv', 'div'):
                dividend, divisor = self.read(('reg', 'eax')), self.read(operand(ops))
                if mn == 'idiv' and self.reg.get('edx') != ('cdq',) or mn == 'div' and self.reg.get('edx') != ('c', 0):
                    raise Refused(f'{mn} without its extension at {address:#x}')
                if mn == 'idiv':
                    self.reg['eax'] = ('lazy', 'iquot', dividend, divisor)
                    self.reg['edx'] = ('lazy', 'imod', dividend, divisor)
                else:
                    self.reg['eax'] = ('junk',)
                    self.reg['edx'] = ('lazy', 'umod', dividend, divisor)
            elif self.pre and mn == 'cvttss2si':
                dst, src = (x.strip() for x in ops.split(',', 1))
                x = self.xmm0 if src == 'xmm0' else self.read(operand(src))
                if x is None or x[0] not in ('c', 'r'):
                    raise Refused(f'cvttss2si of {x}')
                if x[0] == 'c':
                    f = value(x[1])
                    self.reg[dst] = ('c', int(f) & 0xffffffff if -2**31 <= f < 2**31 else 0x80000000)
                else:
                    r = self.p.reg()
                    self.p.emit('ftoi', r, x[1])
                    self.reg[dst] = ('i', r)
            elif self.pre and mn == 'cvtsi2sd':
                # Unsigned conversion of a bounded counter remainder. All int32 values are exact in binary64;
                # a nonnegative range makes the 2^32 correction zero, then cvtsd2ss equals cvtsi2ss.
                dst, src = (x.strip() for x in ops.split(',', 1))
                x = self.read(operand(src))
                bound = self.p.range_of(x)
                seq, at = [], nxt
                for _ in range(5):
                    ii = insns.get(at)
                    if ii is None:
                        break
                    seq.append((ii.mnemonic, ii.op_str))
                    at += ii.size
                if dst != 'xmm0' or bound is None or not 0 <= bound[0] <= bound[1] < 2**31 or len(seq) != 5 or \
                        seq[:3] != [('mov', 'eax, ' + src), ('shr', 'eax, 0x1f'),
                                    ('addsd', 'xmm0, qword ptr [eax*8 + 0x1bd3050]')] or \
                        seq[3][0] != 'movsd' or not seq[3][1].endswith(', xmm0') or \
                        seq[4] != ('cvtsd2ss', 'xmm0, ' + seq[3][1].split(',')[0]):
                    raise Refused(f'unbounded unsigned double conversion at {address:#x}')
                if struct.unpack_from('<d', self.data, 0x01bd3050 - DATA_BASE)[0] != 0.0:
                    raise Refused('unsigned conversion correction is not zero')
                if x[0] == 'c':
                    self.xmm0 = ('c', bits(f32(float(_signed(x[1])))))
                else:
                    r = self.p.reg()
                    self.p.emit('itof', r, x[1])
                    self.xmm0 = ('r', r)
                # Leave the first instruction following cvtsd2ss to the normal reader.
                address = nxt
                for _ in range(5):
                    address += insns[address].size
                self.reg['eax'] = ('c', 0)   # the nonnegative source shifted right by 31
                continue
            elif self.pre and mn == 'cvtsi2ss':
                dst, src = (x.strip() for x in ops.split(',', 1))
                x = self.read(operand(src))
                if x[0] == 'c':
                    w = ('c', bits(f32(float(_signed(x[1])))))
                elif x[0] == 'i':
                    r = self.p.reg()
                    self.p.emit('itof', r, x[1])
                    w = ('r', r)
                else:
                    raise Refused(f'cvtsi2ss of {x}')
                if dst == 'xmm0':
                    self.xmm0 = w
                else:
                    self.reg[dst] = w
            elif self.pre and mn == 'movsx' and re.match(r'^(eax|ecx|edx), word ptr \[(eax|ecx|edx) \+ 0x22\]$', ops) and \
                    self.reg.get(ops[ops.index('[') + 1:ops.index('[') + 4]) == ('model',):
                r = self.p.reg()
                self.p.emit('bones', r)
                self.reg[ops[:3]] = ('i', r)
            elif self.pre and mn == 'and' and re.match(r'^dword ptr \[ebp - (0x[0-9a-f]+|\d+)\], 0$', ops):
                self.write(operand(ops.split(',')[0]), ('c', 0))    # a loop counter's start
            elif self.pre and mn in ('inc', 'dec') and ops == 'eax' and (self.reg.get('eax') or ('',))[0] == 'c':
                self.reg['eax'] = ('c', (self.reg['eax'][1] + (1 if mn == 'inc' else -1)) & 0xffffffff)
            elif mn == 'mov' and ops.startswith('byte ptr [ebp - 4], '):
                pass            # the EH state byte
            elif self.pre and mn == 'mov' and re.match(r'^(word|byte) ptr \[ebp - 0x[0-9a-f]+\], (ax|al)$', ops) and \
                    self.reg.get('eax') == ('c', 0):
                pass            # zeroes an _itoa buffer (its text is the call's result)
            elif self.pre and mn == 'movzx' and ops == 'eax, byte ptr [ebp - 0xd]':
                # TestFrustrum2D 0x016ccce7(OBJECT x * 0.01, y * 0.01, -20) at 0x0176ceea: not visible skips the
                # case (to the next type test, after the block; checked at the end).
                t1, t2 = insns.get(nxt), None
                t2 = insns.get(nxt + t1.size) if t1 else None
                if not t1 or (t1.mnemonic, t1.op_str) != ('test', 'eax, eax') or not t2 or t2.mnemonic != 'je':
                    raise Refused(f'visibility test at {address:#x}')
                self.skips.append((int(t2.op_str, 16), self.p.emit('visible')))
                address = t2.address + t2.size
                continue
            elif self.pre and mn == 'imul' and ops == 'eax, dword ptr [eax + ecx], 0x30':
                index = self.read(('index',))           # an int array element (constant bone) times 0x30
                if index[0] == 'c':
                    self.reg['eax'] = ('c', (index[1] * 0x30) & 0xffffffff)
                elif index[0] == 'i':
                    self.reg['eax'] = ('scaled', index)
                else:
                    raise Refused(f'bone array element {index}')
            elif self.pre and mn == 'imul' and ops == 'eax, eax, 0x30' and self.reg.get('eax', ('',))[0] == 'i':
                self.reg['eax'] = ('scaled', self.reg['eax'])          # a named bone's matrix offset
            elif self.pre and mn == 'add' and ops == f'eax, {BONE_TRANSFORM:#x}':
                index = self.reg.get('eax', ('',))
                if index[0] == 'scaled':
                    self.reg['eax'] = ('boneptr', index[1])
                elif index[0] == 'c' and index[1] % 0x30 == 0 and index[1] < 0x30 * 0x100:
                    self.reg['eax'] = ('boneptr', ('c', index[1] // 0x30))
                else:
                    raise Refused(f'BoneTransform index {index}')
            elif self.pre and mn == 'imul' and re.match(r'^eax, eax, (0x[0-9a-f]+|\d+)$', ops) and self.reg.get('eax', ('',))[0] == 'c':
                self.reg['eax'] = ('c', (self.reg['eax'][1] * int(ops.split(', ')[2], 0)) & 0xffffffff)
            elif self.pre and mn == 'shl' and re.match(r'^eax, \d+$', ops) and self.reg.get('eax', ('',))[0] == 'c':
                self.reg['eax'] = ('c', (self.reg['eax'][1] << int(ops[5:])) & 0xffffffff)

            elif self.pre and mn in ('imul', 'add', 'sub', 'shl', 'inc', 'dec') and self.integer_op(mn, ops):
                pass        # RENDER-ITEMS-002S: integer arithmetic on registers
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
                elif self.pre and dst == ('reg', 'xmm1'):
                    self.reg['xmm1'] = self.read(src)
                elif self.pre and src == ('reg', 'xmm1'):
                    self.write(dst, self.read(src))
                elif self.pre and dst == ('reg', 'xmm0') or src == ('reg', 'xmm0'):
                    pass
                else:
                    raise Refused(f'movss {ops}')
            elif self.pre and mn in BINARY and ops.startswith('xmm1, '):
                src = operand(ops[6:])
                self.reg['xmm1'] = self.p.binary(BINARY[mn], self.read(('reg', 'xmm1')),
                                                 self.xmm0 if src == ('reg', 'xmm0') else self.read(src))
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
                if dst not in ('eax', 'ecx', 'edx') + (('esi', 'edi') if self.pre else ()) or not m:
                    raise Refused(f'lea {ops}')
                self.reg[dst] = ('frame', -int(m.group(1), 16))
            elif mn == 'mov':
                dst, src = (operand(x.strip()) for x in ops.split(',', 1))
                if dst[0] == 'mem' and dst[1] == 'ebp' and dst[2] == -4:
                    pass
                elif src[0] == 'mem' and src[1] in ('eax', 'ecx') and not self.pre:
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


def extract_pre(wa, t):
    start, last, frames = survey_pre(wa, t)
    need = set()
    while True:
        it = Interpreter(wa, frames, start, last, pre=True, need=need)
        try:
            end = it.run()
            break
        except NeedPhi as e:
            if len(need) >= 256:
                raise Refused('more than 256 joined slots')
            need.add(e.args[0])
    for target, index in it.skips:
        if target <= end:
            raise Refused(f'visibility test target {target:#x} inside the case')
        it.p.ops[index] = it.p.ops[index][:-1] + (len(it.p.ops),)
    effects = sum(op[0] in (OP['sprite'], OP['particle'], OP['bone_sprite'], OP['particle_owner'], OP['joint'],
                            OP['sprite_rot'], OP['particle_reg'], OP['particle_reg_owner']) for op in it.p.ops)
    if not effects:
        raise Refused('no effect request')
    return {'start': start, 'end': end, 'ops': it.p.ops, 'regs': it.p.regs, 'bones': it.bones, 'names': it.names}


def extract_post(wa, t):
    """RENDER-ITEMS-002T: an owner block after the draws read with the pre-draw idioms (RenderPartObjectBody's frame)."""
    start, last, frames = survey(wa, t, EFFECTS + (ITEM_TRANSFORM, BONE_SPRITE, NAMED))
    need = set()
    while True:
        it = Interpreter(wa, frames, start, last, pre=True, need=need, post=True)
        try:
            end = it.run()
            break
        except NeedPhi as e:
            if len(need) >= 256:
                raise Refused('more than 256 joined slots')
            need.add(e.args[0])
    if it.skips or any(op[0] == OP['named'] for op in it.p.ops):
        raise Refused('visibility test or named bone in an owner block')
    effects = sum(op[0] in (OP['sprite'], OP['particle'], OP['particle_reg'], OP['sprite_rot'], OP['bone_sprite'])
                  for op in it.p.ops)
    if not effects:
        raise Refused('no effect request')
    return {'start': start, 'end': end, 'ops': it.p.ops, 'regs': it.p.regs, 'bones': it.owner_bones,
            'item_bones': it.bones, 'post': True}


def extract(types=OWNER_FX_TYPES + POST_FX_TYPES):
    wa = tuple(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    out, refused = {}, {}
    for t in types:
        try:
            out[t] = extract_post(wa, t) if t in POST_FX_TYPES else extract_type(wa, t)
        except Refused as e:
            refused[t] = str(e)
    return out, refused


def render(programs, pre=None):
    """The header: owner-effect programs (after the body draws) and pre-draw programs (RENDER-ITEMS-002R)."""
    pre = pre or {}
    blocks, rows, pre_rows, ops, names = [], [], [], [], []
    lines = ['/* Generated by scripts/gen_item_owner_fx.py (RENDER-ITEMS-002Q, 002R). Effect programs of item bodies,',
             ' * read from the pinned instructions; see client-render-items.md parts 17, 18, 20 and 21. One op =',
             ' * {op, a, b, c, d, e, k}. Registers are binary32 words (named bones: int32); a vec3 is three registers.',
             ' *  1 const  r[a] = bits k            2 mov  r[a] = r[b]',
             ' *  3..6     r[a] = r[b] mul/add/sub/div r[c] (binary32)      7 neg  r[a] = -r[b] (sign flip)',
             ' *  8 gate   rand() % a != 0: continue at op k (program-relative)',
             ' *  9 range  r[a] = 0x011ff622(r[b], r[c], k steps), one rand',
             ' * 10 transform  r[a..a+2] = 0x012b678d(owner bone k, local r[b..b+2])',
             ' * 11 norm   r[a..a+2] = 0x00cfd15f(r[b..b+2])   12 angle  r[a..a+2] = OBJECT +0x164',
             ' * 13 sprite CreateSprite 0x01692eb7(bitmap k, pos r[a], scale r[b], light r[c], OBJECT, 0, 0, 4, axes)',
             ' * 14 particle CreateParticle 0x0168fafd(bitmap k, pos r[a], angle r[b], light r[c], subtype e, scale r[d], 0, 0)',
             ' * Pre-draw programs (RenderObjDraw\'s own type case, before the body draws; item bones = BoneTransform):',
             ' * 15 wave   r[a] = 0x0185bdc4(bits k, 0) of the item time       16 named  r[a] = 0x012bd35a(name k, -1)',
             ' * 17 bone sprite 0x0150e746(bitmap k, bone r[a], scale r[b], light r[c], OBJECT, rotation r[d], e, 4, axes)',
             ' * 18 visible  TestFrustrum2D flag 0 (0x0176ceea): continue at op k (the case is skipped)',
             ' * 19 alpha  r[a] = RenderObjDraw alpha (arg 4)   20 time  r[a] = 0x06fce370   21 sin  r[a] = 0x009681bd(r[b])',
             ' * 22 abs    r[a] = 0 > r[b] ? -r[b] : r[b] (0x0184f8ff)   23 randmod  r[a] = (float)(rand() % k)',
             ' * 24 item transform  r[a..a+2] = TransformPosition 0x012b6ef1(item bone r[b], local r[c..c+2], translate k)',
             ' * 25 particle  as 14 with the OBJECT as owner (argument 7)',
             ' * RENDER-ITEMS-002S (part 19): integer registers hold int32 bits.',
             ' * 26 ftoi  r[a] = cvttss2si r[b]   27 itof  r[a] = cvtsi2ss r[b]   28/29  r[a] = r[b] idiv r[c] remainder/quotient',
             ' * 30..32   r[a] = r[b] add/sub/imul r[c] (int32)   33 irand  r[a] = rand()   36 bones  r[a] = item bone count',
             ' * 34 cond   jcc e & 15 (je jne jl jge jg jle jb jae ja jbe, 10 = lahf/jp, 11 = lahf/jnp) on r[a], r[b]',
             ' *           (e & 0x10: comiss flags, else cmp): continue at op k     35 jump  continue at op k',
             ' * 37 light  r[a..a+2] = RenderObjDraw light (arg 3)   38 position  r[a..a+2] = OBJECT +0x158',
             ' * 39 joint  CreateJoint 0x0153b02c(bitmap k, pos r[a], target r[b], angle r[c], subtype e, OBJECT, scale r[d],',
             ' *           -1, 0, 0, -1, 0, -1, 0)   40 sprite  as 13 with rotation r[d] and blend e   41 umod  r[a] = r[b] div r[c]',
             ' * RENDER-EFFECTS-022: 50 object point  OBJECT[0x1f4 + 4*b] = r[a], emitted as MU_RC_OWNER_POINT.',
             ' * RENDER-ITEMS-002T (part 21): 42 frame  r[a] = [0x0bdc5ebc]   43 object transform  r[a..a+2] = 0x012b678d(item bone',
             ' *           r[b], NULL)   44 random vector  r[a..a+2] = 0x00d01fc6(r[b..b+5]), r[a+3] its result',
             ' * 45 select r[a] = r[c + r[b] / 4] (r[b] a byte offset below 4d)   46/47 particle  as 14/25 with bitmap r[k], argument 8',
             ' *           r[k+1]   48 bitmap  the next request\'s bitmap is r[a]   49 owner item transform  r[a..a+2] =',
             ' *           0x012b6ef1(OBJECT bone k matrix (0x0129f12c), local r[c..c+2], translate e)',
             ' */',
             'typedef struct { uint8_t op; uint16_t a, b, c, d; uint8_t e; uint32_t k; } mu_rc_fx_op;',
             'static const mu_rc_fx_op mu_rc_fx_ops[] = {']

    def block(prog):
        key = tuple(prog['ops'])
        if key not in blocks:
            blocks.append(key)
            ops.extend(prog['ops'])
            lines.append(f'    /* block {prog["start"]:#010x}..{prog["end"]:#010x} */')
            for op in prog['ops']:
                lines.append('    {%d, %d, %d, %d, %d, %d, 0x%08xu},' % op)
        index = blocks.index(key)
        return sum(len(b) for b in blocks[:index])
    for t, prog in sorted(programs.items()):
        rows.append((t, block(prog), len(prog['ops']), prog['regs'], max(prog['bones'], default=-1)))
    for t, prog in sorted(pre.items()):
        # Name indices become global (mu_rc_fx_names).
        local = prog['names']
        for name in local:
            if name not in names:
                names.append(name)
        prog = dict(prog, ops=[op if op[0] != OP['named'] else op[:-1] + (names.index(local[op[-1]]),)
                               for op in prog['ops']])
        pre_rows.append((t, block(prog), len(prog['ops']), prog['regs']))
    lines += ['};',
              'static const struct { int32_t type; uint16_t first, count; uint16_t regs; int16_t max_bone; } mu_rc_fx_types[] = {']
    for row in rows:
        lines.append('    {0x%04x, %d, %d, %d, %d},' % row)
    lines += ['};',
              '/* Pre-draw programs (RENDER-ITEMS-002R). */',
              'static const struct { int32_t type; uint16_t first, count; uint16_t regs; } mu_rc_fx_pre_types[] = {']
    for row in pre_rows:
        lines.append('    {0x%04x, %d, %d, %d},' % row)
    if not pre_rows:
        lines.append('    {-1, 0, 0, 0},')
    lines += ['};', '/* Owner-table programs that read item bones or OBJECT fields (RENDER-ITEMS-002T post programs). */',
              'static const int32_t mu_rc_fx_post_types[] = {']
    lines += ['    0x%04x,' % t for t, prog in sorted(programs.items()) if prog.get('post')] or ['    -1,']
    lines += ['};', 'static const char *const mu_rc_fx_names[] = {']
    lines += ['    "%s",' % name for name in names] or ['    "",']
    lines += ['};', '']
    return '\n'.join(lines)


def extract_pre_all(types=None):
    wa = tuple(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    out, refused = {}, {}
    for t in PRE_FX_TYPES if types is None else types:
        try:
            out[t] = extract_pre(wa, t)
        except Refused as e:
            refused[t] = str(e)
    return out, refused


def generate():
    """The header from the pinned instructions; SystemExit when a listed type no longer reads."""
    programs, refused = extract()
    pre, pre_refused = extract_pre_all()
    if refused or pre_refused:
        raise SystemExit(f'effect program no longer reads from the pinned instructions: {refused} {pre_refused}')
    return render(programs, pre)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HEADER)
    p.add_argument('--check', action='store_true')
    p.add_argument('--types', help='comma-separated hex types (report only)')
    a = p.parse_args()
    types = [int(x, 16) for x in a.types.split(',')] if a.types else OWNER_FX_TYPES + POST_FX_TYPES
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
    result = generate()
    if a.check:
        if a.output.read_text() != result:
            raise SystemExit('owner-effect table differs from the pinned instructions')
    else:
        a.output.write_text(result)


if __name__ == '__main__':
    main()
