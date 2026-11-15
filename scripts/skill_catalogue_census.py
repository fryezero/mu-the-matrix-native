#!/usr/bin/env python3
"""RENDER-EFFECTS-035: static census of the class-tree skills outside the learned demo set.

For each of the 37 catalogue rows (DK 14, Elf 23) this resolves, from the pinned restored text only:

* the attack-step body (dispatcher 0x013966ea), the area end body (0x013a90c0) and the targeted end
  body (0x013af035) selected for the base skill;
* the visual slice of the magic receive switch (0x01253f73) and of the position-skill receive switch
  (0x0125c9c3), i.e. the case body only: the packet prologue is never read as behaviour;
* the ordered presentation requests of each non-default body (effect, joint, sound, pose, arrows) with
  their constant type, subtype, owner and key words;
* whether the native consumers admit each requested effect or joint kind (libcombat predicates).

Nothing executes client code. The compare-tree and jump-table walker interprets only the switch's own
compare, branch and table instructions; request arguments are read from the pushes in front of each
call. Rows are then grouped by request shape. The per-group original comparison (ordered arguments under
the strict machine) is scripts/validate_render_effects35.py; this census only says what is requested.

  --csv PATH        write the 37-row classification
  --missing PATH    write the missing consumer ids
  --check           compare both with the committed files under docs/research and fail on a difference
"""
import argparse
import csv
import ctypes
import io
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pins  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / 'docs/research/skill-catalogue-classification.csv'
MISSING_PATH = ROOT / 'docs/research/skill-catalogue-missing-consumers.csv'
BASE = 0x401000
DATA_BASE = 0x01a7c000   # the second image section (pins.DATA)

# The catalogue of docs/research/client-render-effects-030.md (stamp-manager filters over the class maps).
CATALOGUE = [
    ('DK', 76, 'Plasma Storm'), ('DK', 232, 'Strike of Destruction'), ('DK', 723, 'Fire Blow'),
    ('DK', 740, "Archangel's will"), ('DK', 813, 'Rush'), ('DK', 1125, 'Poison Storm'),
    ('DK', 1126, 'Frozen Slayer'), ('DK', 1127, 'Bloodying Hit'), ('DK', 1500, "Sword's Fury"),
    ('DK', 1501, 'Sword Blow'), ('DK', 1502, 'Strong Belief'), ('DK', 1503, 'Solid Protection'),
    ('DK', 2040, 'Sword Blow of Saturation'), ('DK', 2043, 'Destruction of Gale'),
    ('Elf', 46, 'Starfall'), ('Elf', 76, 'Plasma Storm'), ('Elf', 77, 'Infinity Arrow'),
    ('Elf', 234, 'Recovery'), ('Elf', 235, 'Multi-Shot'), ('Elf', 425, 'Cure'), ('Elf', 426, 'Party Healing'),
    ('Elf', 427, 'Poison Arrow'), ('Elf', 430, 'Bless'), ('Elf', 432, 'Summon Satyros'),
    ('Elf', 651, 'Shadow Step'), ('Elf', 652, 'Evasion'), ('Elf', 727, 'Focus Shot'),
    ('Elf', 740, "Archangel's will"), ('Elf', 1125, 'Poison Storm'), ('Elf', 1126, 'Frozen Slayer'),
    ('Elf', 1127, 'Bloodying Hit'), ('Elf', 2023, 'Raining Arrow'), ('Elf', 2024, 'Dex Booster'),
    ('Elf', 2025, 'Holy Bolt'), ('Elf', 2026, 'Improve Elemental Attack Power'),
    ('Elf', 2027, 'Improve Elemental Defense'), ('Elf', 2047, 'Holy Bolt of Gale'),
]
# Brand aliases whose base is a catalogue row (same source table). Aliases are not admitted by this census.
ALIASES = {
    ('DK', 232): [807, 809, 1202], ('DK', 723): [1072], ('DK', 1125): [1129, 1133, 1196, 1199],
    ('DK', 1126): [1130, 1134, 1197, 1200], ('DK', 1127): [1131, 1135, 1198, 1201], ('DK', 1500): [801, 802],
    ('DK', 1501): [1203], ('DK', 1502): [810], ('DK', 1503): [803, 804, 805, 806, 1204],
    ('Elf', 77): [441], ('Elf', 235): [411, 431, 1083], ('Elf', 426): [429, 1227], ('Elf', 427): [434],
    ('Elf', 430): [433, 1230], ('Elf', 727): [1085], ('Elf', 1125): [1129, 1133, 1196, 1199],
    ('Elf', 1126): [1130, 1134, 1197, 1200], ('Elf', 1127): [1131, 1135, 1198, 1201], ('Elf', 2023): [1222],
    ('Elf', 2025): [876, 1223], ('Elf', 2026): [1224], ('Elf', 2027): [1225],
}

# Switch heads: (first instruction after the base skill is stored, frame slot of the switch value).
SWITCHES = {
    'step': (0x01396742, -0x14), 'area': (0x013a90c0, -0x14), 'target': (0x013af035, -0x20),
    'magic': (0x01253f73, -0x1c), 'position': (0x0125c9c3, -0x18),
}
DEFAULTS = {'step': 0x0139b454, 'area': 0x013aea7a, 'target': 0x013b1911, 'magic': 0x0125c47c,
            'position': 0x01260e10}
# Where a case body ends: the shared join or default of its switch (the body itself is not followed past it).
EXITS = {
    'step': {0x0139b5c5, 0x0139b454}, 'area': {0x013aea7a, 0x013b1def}, 'target': {0x013b1911, 0x013b1def},
    'magic': {0x0125c47c}, 'position': {0x01260e1d, 0x01260e10, 0x0126152a},
}
# The position join 0x01260e1d has one more skill test: base 235 continues at 0x01260e65 up to 0x0126152a.
POSITION_TAIL = {235: 0x01260e65}

EFFECT, JOINT, PARTICLE, SOUND = 0x013c0eaa, 0x0153b02c, 0x0168fafd, 0x00a6ac96
SKILL_ACTION, SET_MAGIC, SET_ATTACK = 0x012b001a, 0x013944d9, 0x01392bde
BOW_POSE, PEN_POSE, MOUNT_POSE, ARROWS, RAND = 0x013946ee, 0x013947d8, 0x0106c453, 0x0158d5bd, 0x01989721
REQUESTS = {EFFECT: ('effect', 14), JOINT: ('joint', 14), PARTICLE: ('particle', 8), SOUND: ('sound', 3),
            SKILL_ACTION: ('action', 4), SET_MAGIC: ('magic-pose', 2), SET_ATTACK: ('attack-pose', 1),
            BOW_POSE: ('bow-pose', 1), PEN_POSE: ('penetration-pose', 1), MOUNT_POSE: ('mount-pose', 2),
            ARROWS: ('arrows', 6)}
VECTOR_DATA, VECTOR_AT = 0x00cfc94a, 0x00cfc922
# Service families a slice calls besides its requests (what an authored fixture has to answer).
SERVICES = {
    0x00966cc4: 'model', 0x00eaa8cf: 'model', 0x012b678d: 'bone', 0x0129f12c: 'bone', 0x012b6ef1: 'bone',
    0x009c104e: 'mount', 0x0106bdb7: 'mount', 0x0106b93a: 'mount', 0x0129dcda: 'mount', 0x00c0755a: 'mount',
    0x009c2aea: 'mount', 0x009ba6e5: 'mount', 0x01950635: 'mount', 0x00ac3bf7: 'mount',
    0x0095f6db: 'target', 0x009a13f4: 'target', 0x0137c724: 'target', 0x0095f977: 'target',
    0x016cc9e2: 'terrain', 0x01295ade: 'presence', 0x016a782e: 'learned-index', RAND: 'rand',
    0x009fd745: 'key',
}
QUIET = {VECTOR_DATA, VECTOR_AT, 0x00cfccae, 0x00cff32a, 0x00d000ad, 0x00cfcead, 0x00cfcd74, 0x00cfd583,
         0x0095ea8e, 0x0095eda9}   # vector accessors, copies, arithmetic and destructors
# Frame slots that hold the acting OBJECT / its CHARACTER in each body family.
OWNERS = {
    'magic': {'dword ptr [ebp - 0x10]': 'source', 'dword ptr [ebp - 0x14]': 'target'},
    'position': {'dword ptr [ebp - 0x10]': 'source', 'dword ptr [ebp - 0x20]': 'source'},
    'step': {'dword ptr [ebp + 0xc]': 'source'},
    'area': {'dword ptr [ebp + 0xc]': 'source', 'dword ptr [ebp - 0x10]': 'target'},
    'target': {'dword ptr [ebp + 0xc]': 'source', 'dword ptr [ebp - 0x10]': 'target'},
}
HEX = re.compile(r'^-?(0x[0-9a-f]+|\d+)$')
LOCAL = re.compile(r'^dword ptr \[ebp ([+-]) (0x[0-9a-f]+|\d+)\]$')


class Census:
    def __init__(self, text, data=None):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.text, self.data, self.md = text, data, Cs(CS_ARCH_X86, CS_MODE_32)
        self.cache = {}

    def insn(self, pc):
        if pc not in self.cache:
            self.cache[pc] = next(self.md.disasm(self.text[pc - BASE:pc - BASE + 16], pc))
        return self.cache[pc]

    @staticmethod
    def local(operand):
        m = LOCAL.match(operand)
        if not m:
            return None
        value = int(m.group(2), 0)
        return -value if m.group(1) == '-' else value

    def select(self, name, skill):
        """Walk the switch's own compare tree / jump tables for one value; return the case body."""
        pc, slot = SWITCHES[name]
        slots, eax, flags = {slot: skill}, None, None
        for _ in range(400):
            i = self.insn(pc)
            m, ops, nxt = i.mnemonic, [x.strip() for x in i.op_str.split(',')], pc + i.size
            if m == 'mov' and ops[0] == 'eax' and self.local(ops[1]) in slots:
                eax = slots[self.local(ops[1])]
            elif m == 'mov' and self.local(ops[0]) is not None and ops[1] == 'eax' and eax is not None:
                slots[self.local(ops[0])] = eax
            elif m == 'dec' and i.op_str == 'eax' and eax is not None:
                eax = (eax - 1) & 0xffffffff
            elif m == 'sub' and ops[0] == 'eax' and eax is not None and HEX.match(ops[1]):
                eax = (eax - int(ops[1], 0)) & 0xffffffff
            elif m == 'cmp' and self.local(ops[0]) in slots and HEX.match(ops[1]):
                flags = (slots[self.local(ops[0])], int(ops[1], 0) & 0xffffffff)
            elif m in ('ja', 'jae', 'jb', 'jbe', 'je', 'jne', 'jg', 'jge', 'jl', 'jle') and flags is not None:
                a, b = flags
                sa, sb = (a - (1 << 32) if a >> 31 else a), (b - (1 << 32) if b >> 31 else b)
                if {'ja': a > b, 'jae': a >= b, 'jb': a < b, 'jbe': a <= b, 'je': a == b, 'jne': a != b,
                        'jg': sa > sb, 'jge': sa >= sb, 'jl': sa < sb, 'jle': sa <= sb}[m]:
                    nxt = int(i.op_str, 16)
            elif m == 'jmp' and HEX.match(i.op_str):
                nxt = int(i.op_str, 16)
            elif m == 'movzx' and eax is not None and re.match(r'^eax, byte ptr \[eax \+ 0x[0-9a-f]+\]$', i.op_str):
                eax = self.text[int(i.op_str.split('+ ')[1][:-1], 16) + eax - BASE]
            elif m == 'jmp' and eax is not None and re.match(r'^dword ptr \[eax\*4 \+ 0x[0-9a-f]+\]$', i.op_str):
                table = int(i.op_str.split('+ ')[1][:-1], 16)
                nxt = struct.unpack_from('<I', self.text, table + eax * 4 - BASE)[0]
            else:
                return pc
            pc = nxt
        raise RuntimeError(f'{name}: switch walk for {skill} did not end')

    def body(self, start, exits, limit=4000):
        """Instructions reachable from a case body without crossing its switch's joins."""
        seen, work = {}, [start]
        while work:
            pc = work.pop()
            while pc not in seen and pc not in exits:
                i = self.insn(pc)
                seen[pc] = i
                if len(seen) > limit:
                    raise RuntimeError(f'body {start:#x} exceeds {limit} instructions')
                if i.mnemonic in ('ret', 'int3'):
                    break
                if i.mnemonic == 'jmp':
                    if not HEX.match(i.op_str):
                        break
                    pc = int(i.op_str, 16)
                    continue
                if i.mnemonic.startswith('j') and HEX.match(i.op_str):
                    work.append(int(i.op_str, 16))
                pc += i.size
        return seen

    def float_at(self, address):
        if self.data is not None and DATA_BASE <= address < DATA_BASE + len(self.data):
            return struct.unpack_from('<f', self.data, address - DATA_BASE)[0]
        if BASE <= address < BASE + len(self.text):
            return struct.unpack_from('<f', self.text, address - BASE)[0]
        return None

    def arguments(self, seen, order, k, count):
        """The last `count` pushes in front of call order[k], innermost first (argument 0 first)."""
        args, skip, j = [], 0, k - 1
        while j >= 0 and len(args) < count and order[j] + seen[order[j]].size == order[j + 1]:
            i = seen[order[j]]
            if i.mnemonic == 'push':
                if skip:
                    skip -= 1
                else:
                    args.append(i.op_str)
            elif i.mnemonic == 'movss' and i.op_str == 'dword ptr [esp], xmm0':
                # push ecx; <load xmm0>; movss [esp], xmm0: a float argument
                load = seen[order[j - 1]]
                value = '?'
                if load.mnemonic == 'xorps':
                    value = 0.0
                elif load.mnemonic == 'movss' and re.match(r'^xmm0, dword ptr \[0x[0-9a-f]+\]$', load.op_str):
                    value = self.float_at(int(load.op_str.split('[')[1][:-1], 16))
                args.append(f'f:{value}')
                j -= 2            # the load and the push ecx it fills
            elif i.mnemonic == 'call':
                target = int(i.op_str, 16) if HEX.match(i.op_str) else None
                if target == VECTOR_AT:
                    skip += 1     # operator[](index): one callee-cleaned push
                elif target != VECTOR_DATA:
                    after = seen[order[j + 1]]
                    if after.mnemonic == 'pop':
                        skip += 1
                    elif after.mnemonic == 'add' and after.op_str.startswith('esp, '):
                        skip += int(after.op_str.split(', ')[1], 0) // 4
                    elif target not in QUIET:
                        break
            j -= 1
        return args

    def requests(self, family, start):
        seen = self.body(start, EXITS[family])
        order = sorted(seen)
        out, services, time_writes = [], set(), []
        for k, address in enumerate(order):
            i = seen[address]
            if i.mnemonic == 'mov' and re.match(r'^byte ptr \[eax \+ 0x21\], (0x[0-9a-f]+|\d+)$', i.op_str):
                time_writes.append(int(i.op_str.split(', ')[1], 0))
            if i.mnemonic != 'call' or not HEX.match(i.op_str):
                continue
            target = int(i.op_str, 16)
            if target in REQUESTS:
                kind, count = REQUESTS[target]
                out.append(self.describe(family, kind, address, self.arguments(seen, order, k, count)))
            elif target in SERVICES:
                services.add(SERVICES[target])
            elif target not in QUIET:
                services.add(f'{target:#010x}')
        return dict(start=start, end=order[-1] + seen[order[-1]].size, instructions=len(order), requests=out,
                    services=sorted(services), attack_time=sorted(set(time_writes)))

    @staticmethod
    def word(text):
        if HEX.match(text):
            value = int(text, 0)
            return '-1' if value == -1 or value == 0xffffffff else f'{value:#x}'
        return 'var'

    def describe(self, family, kind, address, a):
        owner = lambda text: OWNERS[family].get(text, 'none' if text == '0' else 'var')
        a = a + ['?'] * 14
        if kind == 'effect':
            return dict(kind=kind, site=address, type=self.word(a[0]), subtype=self.word(a[4]), owner=owner(a[5]),
                        key=self.word(a[6]), skill=self.word(a[7]),
                        scale=a[10][2:] if a[10].startswith('f:') else 'var')
        if kind == 'joint':
            return dict(kind=kind, site=address, type=self.word(a[0]), subtype=self.word(a[4]), owner=owner(a[5]),
                        scale=a[6][2:] if a[6].startswith('f:') else 'var', key=self.word(a[7]),
                        skill=self.word(a[8]))
        if kind == 'particle':
            return dict(kind=kind, site=address, type=self.word(a[0]), subtype=self.word(a[4]))
        if kind == 'sound':
            return dict(kind=kind, site=address, type=self.word(a[0]), owner=owner(a[1]))
        if kind == 'action':
            return dict(kind=kind, site=address, action=self.word(a[2]), alternative=self.word(a[3]))
        if kind == 'arrows':
            return dict(kind=kind, site=address, index=self.word(a[3]), flag=self.word(a[4]), skill=self.word(a[5]))
        return dict(kind=kind, site=address)


def text_of(request):
    k = request['kind']
    if k == 'effect':
        extra = ''.join(f' {name}={request[name]}' for name, quiet in (('key', '-1'), ('skill', '0x0'), ('scale', '0.0'))
                        if request[name] != quiet)
        return f"effect {request['type']}/{request['subtype']} owner={request['owner']}{extra}"
    if k == 'joint':
        return (f"joint {request['type']}/{request['subtype']} owner={request['owner']} scale={request['scale']}"
                f" key={request['key']} skill={request['skill']}")
    if k == 'particle':
        return f"particle {request['type']}/{request['subtype']}"
    if k == 'sound':
        return f"sound {request['type']} owner={request['owner']} site={request['site']:#010x}"
    if k == 'action':
        return f"action {request['action']}/{request['alternative']}"
    if k == 'arrows':
        return f"arrows index={request['index']} flag={request['flag']} skill={request['skill']}"
    return k


def shape_of(request):
    """Request shape with the row's own ids removed: what a table-driven caller has to support."""
    k = request['kind']
    if k == 'effect':
        return f"effect(owner={request['owner']},key={'-1' if request['key'] == '-1' else 'word'})"
    if k == 'joint':
        return f"joint(owner={request['owner']})"
    return k


class Consumers:
    """The native admission predicates (libcombat). None means 'not built': availability unknown."""

    def __init__(self, path=None):
        suffix = 'dylib' if sys.platform == 'darwin' else 'so'
        path = Path(path) if path else ROOT / f'reconstructed/combat/libcombat.{suffix}'
        self.lib = ctypes.CDLL(str(path)) if path.exists() else None
        if self.lib:
            for name in ('mu_sfx_effect_kind_supported', 'mu_jt_kind_supported'):
                getattr(self.lib, name).argtypes = [ctypes.c_int32, ctypes.c_int32]

    def missing(self, request):
        """The consumer id this request needs and the native side lacks, or None."""
        if request['kind'] not in ('effect', 'joint') or self.lib is None:
            return None
        if request['type'] == 'var' or request['subtype'] == 'var':
            return (request['kind'], request['type'], request['subtype'])
        test = self.lib.mu_sfx_effect_kind_supported if request['kind'] == 'effect' else self.lib.mu_jt_kind_supported
        if test(int(request['type'], 0), int(request['subtype'], 0)):
            return None
        return (request['kind'], request['type'], request['subtype'])


# Authored grouping. The census asserts that every row of a uniform group has the same request shape.
GROUPS = {
    'A caster-frame': 'receive slice requests one caster-owned effect at the caster frame, with constant words',
    'B bone-frame buff': 'receive slice poses, then one effect at the caster bone 17 (mount service declared)',
    'C triple storm': 'receive slice: one target-owned effect and two unowned ground effects',
    'D heal family': 'receive slice: 0x8021 caster effect, pose 0xd9/0x106, sound, one target effect',
    'E existing end body': 'default pose slice 0x0125594d and an already recovered or small end body',
    'F arrows': 'bow pose and an arrow or volley caller',
    'G own step or end body': 'own attack-step or area-end body (hand trace)',
    'H mount context': 'mount pose helper 0x0106c453 (out of scope with Fire Breath)',
    'I no receive case': 'no case in either receive switch, default step and both default ends',
}
ROW_GROUP = {
    740: 'A caster-frame', 77: 'A caster-frame', 652: 'A caster-frame', 651: 'A caster-frame',
    2023: 'A caster-frame', 2025: 'A caster-frame', 727: 'A caster-frame',
    1500: 'B bone-frame buff', 1502: 'B bone-frame buff', 1503: 'B bone-frame buff',
    1125: 'C triple storm', 1126: 'C triple storm', 1127: 'C triple storm',
    425: 'D heal family', 430: 'D heal family', 2024: 'D heal family', 234: 'D heal family',
    432: 'E existing end body', 2026: 'E existing end body', 2027: 'E existing end body',
    46: 'F arrows', 235: 'F arrows', 427: 'F arrows', 2047: 'F arrows',
    232: 'G own step or end body', 2043: 'G own step or end body', 2040: 'G own step or end body',
    1501: 'G own step or end body', 723: 'G own step or end body',
    76: 'H mount context', 813: 'I no receive case', 426: 'I no receive case',
}


def census(text, data=None, consumers=None):
    c = Census(text, data)
    consumers = consumers or Consumers()
    rows = []
    for cls, skill, name in CATALOGUE:
        row = dict(cls=cls, skill=skill, name=name, aliases=ALIASES.get((cls, skill), []), bodies={})
        for family in SWITCHES:
            start = c.select(family, skill)
            default = start == DEFAULTS[family]
            if family == 'position' and default and skill in POSITION_TAIL:
                start, default = POSITION_TAIL[skill], False
            row['bodies'][family] = dict(start=start, default=default) if default else dict(
                default=False, **c.requests(family, start))
        requests = [r for family in ('magic', 'position', 'step', 'area', 'target')
                    for r in row['bodies'][family].get('requests', [])]
        missing = sorted({m for m in map(consumers.missing, requests) if m})
        row.update(group=ROW_GROUP[skill], missing=missing,
                   default_step_and_ends=all(row['bodies'][f]['default'] for f in ('step', 'area', 'target')))
        rows.append(row)
    return rows


def write_csv(rows):
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    w.writerow(['class', 'skill', 'name', 'aliases', 'group', 'step_body', 'area_end', 'target_end',
                'magic_receive', 'position_receive', 'receive_requests', 'step_end_requests', 'services',
                'missing_consumers'])
    for r in rows:
        b = r['bodies']
        cell = lambda f: ('default ' if b[f]['default'] else '') + f"{b[f]['start']:#010x}"
        listing = lambda families: '; '.join(f"{f}: " + ', '.join(map(text_of, b[f]['requests'])) + (
            f" [AttackTime={'/'.join(map(str, b[f]['attack_time']))}]" if b[f]['attack_time'] else '')
            for f in families if not b[f]['default'] and (b[f]['requests'] or b[f]['attack_time']))
        services = sorted({s for f in b for s in b[f].get('services', [])})
        w.writerow([r['cls'], r['skill'], r['name'], ' '.join(map(str, r['aliases'])), r['group'], cell('step'),
                    cell('area'), cell('target'), cell('magic'), cell('position'), listing(('magic', 'position')),
                    listing(('step', 'area', 'target')), ' '.join(services),
                    ' '.join(f'{k}:{t}/{s}' for k, t, s in r['missing'])])
    return out.getvalue()


def write_missing(rows):
    users = {}
    for r in rows:
        for m in r['missing']:
            users.setdefault(m, []).append(f"{r['cls']} {r['skill']}")
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    w.writerow(['kind', 'type', 'subtype', 'rows', 'requesting_rows'])
    for (kind, t, s), who in sorted(users.items()):
        w.writerow([kind, t, s, len(who), '; '.join(who)])
    return out.getvalue()


def summary(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r['group'], []).append(f"{r['cls']} {r['skill']}")
    shapes = {}
    for r in rows:
        key = tuple(shape_of(q) for f in ('magic', 'position') for q in r['bodies'][f].get('requests', []))
        shapes.setdefault(r['group'], set()).add(key)
    return dict(rows=len(rows), dk=sum(r['cls'] == 'DK' for r in rows), elf=sum(r['cls'] == 'Elf' for r in rows),
                default_step_and_ends=sum(r['default_step_and_ends'] for r in rows),
                groups={g: dict(rows=len(v), members=v, receive_shapes=len(shapes[g])) for g, v in sorted(groups.items())},
                missing_consumers=len({m for r in rows for m in r['missing']}),
                rows_without_missing=sum(not r['missing'] for r in rows))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--text')
    p.add_argument('--data')
    p.add_argument('--csv', type=Path)
    p.add_argument('--missing', type=Path)
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    rows = census(pins.TEXT.read(a.text), pins.DATA.read(a.data))
    table, missing = write_csv(rows), write_missing(rows)
    if a.csv:
        a.csv.write_text(table)
    if a.missing:
        a.missing.write_text(missing)
    report = summary(rows)
    if a.check:
        report['csv_equal'] = CSV_PATH.read_text() == table
        report['missing_equal'] = MISSING_PATH.read_text() == missing
    print(json.dumps(report, indent=2))
    return int(a.check and not (report['csv_equal'] and report['missing_equal']))


if __name__ == '__main__':
    raise SystemExit(main())
