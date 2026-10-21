#!/usr/bin/env python3
"""Turn a langread snapshot into local plaintext tables (NATIVE-LANG-001).

mac-play/diagnostics/langread copies, read-only, the tables main.exe built
from Data\\Lang.mpr: the script-table manager 0x06fbaa60, the nodes of every
std::map inside it and the buffers those nodes point to.  This script walks
the same trees offline and writes the tables the native port reads
(native/core/mu_lang.c).  The layouts come from the client's consumers; see
docs/research/client-lang-tables.md.  The output is the server's game text:
keep it local, never commit it.

Files written to OUT_DIR:

  globaltext.txt  index<TAB>text                (Text(kor) 0x06fbab48, GlobalText 0x0095f027)
  skills.tsv      skill table                   (Skill(Kor) 0x06fbb138, lookup 0x00961620)
  gates.tsv       gate table                    (Gate 0x06fbabac, lookup 0x0110cbaf)
  moves.tsv       move list                     (movereq(kor) 0x06fbb84c, lookup 0x0113c3f5)
  npcnames.tsv    monster and NPC names         (Npcname(kor) 0x06fbb664, getters 0x011427c7..)
  dialog.tsv      NPC dialog lines              (Dialog(kor) 0x06fbb6d0)
  enchant.tsv     EnchantEffect colours         (0x06fbb754, lookups 0x010ffd7a / 0x010ffddb)
  mapnames.tsv    world -> map name             (map-name function 0x016baaa6, native/core/mu_lang_maps.h)

NATIVE-FIDELITY-001 adds (written when the snapshot holds the table):

  pentagram.tsv   code -> tier                  (PentagramOption 0x06fbae4c, lookup 0x011447ac, record +0x24)
  invenanim.tsv   code -> action, speed         (InvenItemAnimation 0x06fbc830, lookup 0x0111d824, +8 / +0xc)
  legendary.tsv   set type -> 2 x 2 codes       (LegendaryItemSetType 0x06fbcba8, lookup 0x011288c7, +4..+0x10)
  cashsets.tsv    sets (name, second name) and their items (CashItemSetOption 0x06fbcc08, read by 0x009debe4)

NATIVE-LANG-002 adds:

  buffs.tsv       BuffEffect 0x06fbb2a4         (lookup 0x010de66f, by item 0x010de6d3, tooltip 0x01298a54)
  charinfo.tsv    character window rows         (CharacterInfoSetup 0x06fbad18, lookup 0x010e5203, rows 0x00b3dedc)
  skillreq.tsv    skill scroll requirements     (SkillRequire 0x06fbb248, lookup 0x00abf829)

Text fields escape TAB, LF, CR and backslash as \\t \\n \\r \\\\ and bytes
outside printable ASCII as \\xHH, so the files hold the client's bytes
exactly (its strings are ANSI; a few are CP949).
"""
import argparse
import bisect
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]

MANAGER = 0x06fbaa60
TEXT, SKILL, GATE, MOVEREQ = MANAGER + 0xe8, MANAGER + 0x6d8, MANAGER + 0x14c, MANAGER + 0xdec
NPCNAME, DIALOG, ENCHANT = MANAGER + 0xc04, MANAGER + 0xc70, MANAGER + 0xcf4
PENTAGRAM, INVENANIM, LEGENDARY, CASHSET = MANAGER + 0x3ec, MANAGER + 0x1dd0, MANAGER + 0x2148, MANAGER + 0x21a8
BUFF, CHARINFO, SKILLREQ = MANAGER + 0x844, MANAGER + 0x2b8, MANAGER + 0x7e8
MAP_AT = {TEXT: 0x38, SKILL: 0x108, GATE: 0x38, MOVEREQ: 0x38, NPCNAME: 0x38, DIALOG: 0x38, ENCHANT: 0x38}
ENCHANT_DEFAULT = 0x50            # 0x010ffd7a / 0x010ffddb return this+0x50 when nothing matches

SKILL_COLUMNS = (
    # name, record offset, C type (i: int32, b: uint8)
    ('level', 0x20, 'i'), ('damage', 0x24, 'i'), ('mana', 0x28, 'i'), ('ag', 0x2c, 'i'),
    ('distance', 0x34, 'i'), ('delay', 0x38, 'i'), ('req_3c', 0x3c, 'i'), ('req_40', 0x40, 'i'),
    ('req_44', 0x44, 'i'), ('req_48', 0x48, 'i'), ('req_4c', 0x4c, 'i'), ('mastery', 0x50, 'i'),
    ('use_type', 0x58, 'i'), ('brand', 0x5c, 'i'), ('master_bonus', 0x7c, 'b'), ('icon', 0x8c, 'i'),
    ('type', 0x90, 'i'), ('skip', 0x00, 'b'))
GATE_COLUMNS = (('flag', 0x08), ('world', 0x0c), ('x1', 0x10), ('y1', 0x14), ('x2', 0x18), ('y2', 0x1c),
                ('target', 0x20), ('dir', 0x24), ('min_level', 0x28), ('max_level', 0x2c))
MOVE_COLUMNS = (('id', 0x00), ('zen', 0x34), ('min_level', 0x38), ('max_level', 0x3c), ('gate', 0x40),
                ('x44', 0x44), ('x48', 0x48), ('x4c', 0x4c))
NPC_COLUMNS = (('x1c', 0x1c, 'i'), ('x20', 0x20, 'i'), ('x24', 0x24, 'b'))


class SnapshotError(ValueError):
    pass


class Snapshot:
    """Sparse copy of client memory: blocks of (address, bytes)."""

    def __init__(self, data):
        if data[:8] != b'MULANGV1' or len(data) < 12:
            raise SnapshotError('not a langread snapshot (MULANGV1)')
        count = struct.unpack_from('<I', data, 8)[0]
        offset, self.blocks = 12, {}
        for _ in range(count):
            if offset + 8 > len(data):
                raise SnapshotError('truncated block header')
            address, size = struct.unpack_from('<II', data, offset)
            offset += 8
            if offset + size > len(data):
                raise SnapshotError('truncated block')
            if size > len(self.blocks.get(address, b'')):
                self.blocks[address] = data[offset:offset + size]
            offset += size
        self.starts = sorted(self.blocks)

    @classmethod
    def load(cls, path):
        return cls(Path(path).read_bytes())

    def read(self, address, size):
        i = bisect.bisect_right(self.starts, address) - 1
        while i >= 0:
            start = self.starts[i]
            block = self.blocks[start]
            if address + size <= start + len(block):
                return block[address - start:address - start + size]
            if address - start > 0x100000:
                break
            i -= 1
        raise SnapshotError(f'{size} bytes at {address:#x} not in the snapshot')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def i32(self, address):
        return struct.unpack('<i', self.read(address, 4))[0]

    def string(self, address):
        """MSVC std::string at address: buffer +0 (inline below 16), size +0x10, capacity +0x14."""
        size, capacity = struct.unpack('<II', self.read(address + 0x10, 8))
        if size > capacity:
            raise SnapshotError(f'bad std::string at {address:#x}')
        if capacity < 16:
            return self.read(address, size)
        return self.read(self.u32(address), size)

    def tree(self, container):
        """(key, node) of an MSVC std::map<int, T> whose head pointer is at container (size at +4),
        in key order.  Node: _Left +0, _Parent +4, _Right +8, _Isnil +0xd, key +0x10."""
        head, size = self.u32(container), self.u32(container + 4)
        if self.read(head + 0xd, 1) != b'\x01':
            raise SnapshotError(f'no map head at {container:#x}')
        out, stack, seen = [], [], set()
        root = self.u32(head + 4)
        if root != head:
            stack.append(root)
        while stack:
            node = stack.pop()
            if node in seen or len(seen) > size:
                raise SnapshotError(f'map {container:#x} is not a tree')
            seen.add(node)
            left, _, right = struct.unpack('<III', self.read(node, 12))
            if self.read(node + 0xd, 1) != b'\x00':
                raise SnapshotError(f'nil node inside map {container:#x}')
            out.append((self.i32(node + 0x10), node))
            if left != head:
                stack.append(left)
            if right != head:
                stack.append(right)
        if len(out) != size:
            raise SnapshotError(f'map {container:#x}: {len(out)} nodes for size {size}')
        out.sort()
        return out


def escape(raw):
    out = []
    for byte in raw:
        ch = chr(byte)
        if ch == '\\':
            out.append('\\\\')
        elif ch == '\t':
            out.append('\\t')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif 0x20 <= byte < 0x7f:
            out.append(ch)
        else:
            out.append(f'\\x{byte:02x}')
    return ''.join(out)


def unescape(text):
    out, i = bytearray(), 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == 'x' and i + 3 < len(text):
                out.append(int(text[i + 2:i + 4], 16))
                i += 4
                continue
            out.append({'t': 9, 'n': 10, 'r': 13, '\\': 92}.get(nxt, ord(nxt)))
            i += 2
            continue
        out.append(ord(ch))
        i += 1
    return bytes(out)


def record(node):
    return node + 0x14            # pair<const int, T>: key at +0x10, T at +0x14


def read_text(snap):
    return [(key, snap.string(record(node) + 8)) for key, node in snap.tree(TEXT + MAP_AT[TEXT])]


def read_skills(snap):
    rows = []
    for key, node in snap.tree(SKILL + MAP_AT[SKILL]):
        r = record(node)
        row = {'index': key, 'record_index': snap.i32(r + 4), 'name': snap.string(r + 8)}
        for name, offset, kind in SKILL_COLUMNS:
            row[name] = snap.i32(r + offset) if kind == 'i' else snap.read(r + offset, 1)[0]
        rows.append(row)
    return rows


def read_gates(snap):
    rows = []
    for key, node in snap.tree(GATE + MAP_AT[GATE]):
        r = record(node)
        rows.append({'index': key, **{name: snap.i32(r + off) for name, off in GATE_COLUMNS}})
    return rows


def read_moves(snap):
    rows = []
    for key, node in snap.tree(MOVEREQ + MAP_AT[MOVEREQ]):
        r = record(node)
        row = {'index': key, 'name': snap.string(r + 4), 'server_name': snap.string(r + 0x1c)}
        row.update({name: snap.i32(r + off) for name, off in MOVE_COLUMNS})
        rows.append(row)
    return rows


def read_npcs(snap):
    rows = []
    for key, node in snap.tree(NPCNAME + MAP_AT[NPCNAME]):
        r = record(node)
        row = {'index': key, 'name': snap.string(r + 4)}
        for name, off, kind in NPC_COLUMNS:
            row[name] = snap.i32(r + off) if kind == 'i' else snap.read(r + off, 1)[0]
        rows.append(row)
    return rows


def read_dialog(snap):
    return [(key, snap.string(record(node) + 4)) for key, node in snap.tree(DIALOG + MAP_AT[DIALOG])]


def read_enchant(snap):
    """code -> [(mesh, r_bits, g_bits, b_bits)], and the default colour bits."""
    rows = []
    for key, node in snap.tree(ENCHANT + MAP_AT[ENCHANT]):
        begin, end, _ = struct.unpack('<III', snap.read(record(node), 12))
        if (end - begin) % 16:
            raise SnapshotError(f'EnchantEffect {key}: vector of {end - begin} bytes')
        entries = []
        if end > begin:
            data = snap.read(begin, end - begin)
            entries = [struct.unpack_from('<iIII', data, i) for i in range(0, len(data), 16)]
        rows.append((key, entries))
    default = struct.unpack('<III', snap.read(ENCHANT + ENCHANT_DEFAULT, 12))
    return rows, default


def read_pentagram(snap):
    """PentagramOption: the lookup 0x011447ac finds the code in the map at +0x3c and returns the record (node +0x14),
    or the default record +0x4c; the name builder reads the tier at record +0x24."""
    rows = [(key, snap.i32(record(node) + 0x24)) for key, node in snap.tree(PENTAGRAM + 0x3c)]
    return rows, snap.i32(PENTAGRAM + 0x4c + 0x24)


def read_invenanim(snap):
    """InvenItemAnimation: 0x0111d824 finds the code in the map at +0x38 and returns the record (node +0x14) or
    NULL; RenderObjectScreen reads the action word +8 and the speed +0xc. Record +0/+4 hold group and index."""
    out = []
    for key, node in snap.tree(INVENANIM + 0x38):
        r = record(node)
        out.append((key, snap.i32(r), snap.i32(r + 4), struct.unpack('<H', snap.read(r + 8, 2))[0], snap.u32(r + 0xc)))
    return out


def read_legendary(snap):
    """LegendaryItemSetType: 0x011288c7 finds the set type in the map at +0x38 (record = node +0x14) or returns the
    default record +0x48; 0x011289d6 compares the code with the four ints at record +4."""
    rows = [(key, [snap.i32(record(node) + 4 + 4 * k) for k in range(4)]) for key, node in snap.tree(LEGENDARY + 0x38)]
    return rows, [snap.i32(LEGENDARY + 0x48 + 4 + 4 * k) for k in range(4)]


def read_cashsets(snap):
    """CashItemSetOption, as 0x009debe4 reads it: the set vector +0x64 (0xcc-byte records: std::string name +4,
    second name +0x1c) and the item vector +0x50 (0x14-byte records: group +0, index +4, set +8)."""
    sets, items = [], []
    begin, end, _ = struct.unpack('<III', snap.read(CASHSET + 0x64, 12))
    if not begin:
        raise SnapshotError('no CashItemSetOption vectors')
    for r in range(begin, end, 0xcc):
        sets.append((snap.string(r + 4), snap.string(r + 0x1c)))
    begin, end, _ = struct.unpack('<III', snap.read(CASHSET + 0x50, 12))
    for r in range(begin, end, 0x14):
        items.append((snap.i32(r), snap.i32(r + 4), snap.i32(r + 8)))
    return sets, items


def read_buffs(snap):
    """BuffEffect, as the client reads it: 0x010de66f finds the buff in the map at +0x38 (record = node +0x14) or
    returns the default record +0x40 (also for buff >= 0x1cb); 0x010de6d3 scans for (item group +8, index +0xc);
    the bufflist's addBuff 0x00c5f296 reads +4 (BuffDetailType for groups 0xf7/0xf6) and +0x28 (1 debuff, 2 cash
    buff); the tooltip lines 0x01298a54 read the name +0x10, the description vector<std::string> +0x34 and +0x40
    (1 or 2: the first line is a format for the hero's buff value)."""
    def one(key, r):
        begin, end, _ = struct.unpack('<III', snap.read(r + 0x34, 12))
        if end < begin or (end - begin) % 0x18:
            raise SnapshotError(f'BuffEffect {key}: bad description vector')
        lines = [snap.string(a) for a in range(begin, end, 0x18)]
        return {'index': key, 'record_index': snap.i32(r), 'group': snap.i32(r + 4),
                'item_group': snap.i32(r + 8), 'item_index': snap.i32(r + 0xc), 'name': snap.string(r + 0x10),
                'type': snap.i32(r + 0x28), 'x2c': snap.i32(r + 0x2c), 'x30': snap.i32(r + 0x30),
                'value_kind': snap.i32(r + 0x40), 'lines': lines}
    rows = [one(key, record(node)) for key, node in snap.tree(BUFF + 0x38)]
    return rows, one('default', BUFF + 0x40)


def read_charinfo(snap):
    """CharacterInfoSetup, as the row builder 0x00b3dedc reads it (map +0x38, record = node +0x14; lookup 0x010e5203
    returns the default +0x44 on a miss): +0 id, +4 label colour, +8 label, +0x20 value group, +0x24 vector<int> of
    16 class flags (index 0x0095f5cc(class)), +0x30 SetName type, +0x34 sort, +0x38 value colour, +0x3c/+0x54
    prefix/suffix strings, +0xa0 button."""
    def one(key, r):
        begin, end, _ = struct.unpack('<III', snap.read(r + 0x24, 12))
        if end < begin or (end - begin) % 4 or end - begin > 0x100:
            raise SnapshotError(f'CharacterInfoSetup {key}: bad class vector')
        classes = list(struct.unpack(f'<{(end - begin) // 4}i', snap.read(begin, end - begin))) if end > begin else []
        return {'id': key, 'record_id': snap.i32(r), 'color': snap.i32(r + 4), 'label': snap.string(r + 8),
                'group': snap.i32(r + 0x20), 'classes': classes, 'type': snap.i32(r + 0x30),
                'sort': snap.i32(r + 0x34), 'value_color': snap.i32(r + 0x38), 'prefix': snap.string(r + 0x3c),
                'suffix': snap.string(r + 0x54), 'button': snap.i32(r + 0xa0)}
    rows = [one(key, record(node)) for key, node in snap.tree(CHARINFO + 0x38)]
    return rows, one('default', CHARINFO + 0x44)


def read_skillreq(snap):
    """SkillRequire: the lookup 0x00abf829(group, index) walks the map at +0x54 (record = node +0x14) for the
    record whose +8/+0xc equal the item; +4 is the skill (data: the scroll's skill), +0x10..+0x18 unnamed."""
    rows = []
    for key, node in snap.tree(SKILLREQ + 0x54):
        r = record(node)
        rows.append((key, *(snap.i32(r + o) for o in (0, 4, 8, 0xc, 0x10, 0x14, 0x18))))
    return rows


def map_name_table(path=ROOT/'native/core/mu_lang_maps.h'):
    """world -> GlobalText index template from the generated header."""
    out = []
    for m in re.finditer(r'\{\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\}', path.read_text()):
        out.append(tuple(int(x) for x in m.groups()))
    return out


def f32(bits):
    return f'{struct.unpack("<f", struct.pack("<I", bits))[0]:.9g}'


def convert(snap, out_dir, header=''):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    note = ('# NATIVE-LANG-001 plaintext from a live read of main.exe (scripts/live_lang_to_plain.py).\n'
            '# The server\'s game text: local only, never commit.\n' + header)
    counts = {}
    text = read_text(snap)
    with open(out_dir/'globaltext.txt', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '# index<TAB>text (GlobalText 0x0095f027)\n')
        for key, raw in text:
            f.write(f'{key}\t{escape(raw)}\n')
    counts['globaltext'] = len(text)

    skills = read_skills(snap)
    cols = ['index', 'name'] + [c[0] for c in SKILL_COLUMNS]
    with open(out_dir/'skills.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#' + '\t'.join(cols) + '\n')
        for row in skills:
            f.write('\t'.join(escape(row[c]) if c == 'name' else str(row[c]) for c in cols) + '\n')
    counts['skills'] = len(skills)

    gates = read_gates(snap)
    cols = ['index'] + [c[0] for c in GATE_COLUMNS]
    with open(out_dir/'gates.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#' + '\t'.join(cols) + '\n')
        for row in gates:
            f.write('\t'.join(str(row[c]) for c in cols) + '\n')
    counts['gates'] = len(gates)

    moves = read_moves(snap)
    cols = ['index', 'name', 'server_name'] + [c[0] for c in MOVE_COLUMNS]
    with open(out_dir/'moves.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#' + '\t'.join(cols) + '\n')
        for row in moves:
            f.write('\t'.join(escape(row[c]) if c in ('name', 'server_name') else str(row[c]) for c in cols) + '\n')
    counts['moves'] = len(moves)

    npcs = read_npcs(snap)
    cols = ['index', 'name'] + [c[0] for c in NPC_COLUMNS]
    with open(out_dir/'npcnames.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#' + '\t'.join(cols) + '\n')
        for row in npcs:
            f.write('\t'.join(escape(row[c]) if c == 'name' else str(row[c]) for c in cols) + '\n')
    counts['npcnames'] = len(npcs)

    dialog = read_dialog(snap)
    with open(out_dir/'dialog.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#index\ttext\n')
        for key, raw in dialog:
            f.write(f'{key}\t{escape(raw)}\n')
    counts['dialog'] = len(dialog)

    enchant, default = read_enchant(snap)
    with open(out_dir/'enchant.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#code\tmesh\tr\tg\tb  (code = item type*512+index; mesh -1 = every mesh; '
                'rows in the client\'s vector order; "default" = the table colour +0x50)\n')
        f.write('default\t-1\t' + '\t'.join(f32(b) for b in default) + '\n')
        for key, entries in enchant:
            for mesh, r, g, b in entries:
                f.write(f'{key}\t{mesh}\t{f32(r)}\t{f32(g)}\t{f32(b)}\n')
            if not entries:
                f.write(f'{key}\tempty\t0\t0\t0\n')
    counts['enchant_codes'] = len(enchant)
    counts['enchant_entries'] = sum(len(e) for _, e in enchant)

    try:
        rows, default = read_pentagram(snap)
        with open(out_dir/'pentagram.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#code\ttier  (PentagramOption record +0x24; "default" = the default record\'s)\n')
            f.write(f'default\t{default}\n')
            for key, tier in rows:
                f.write(f'{key}\t{tier}\n')
        counts['pentagram'] = len(rows)
    except SnapshotError:
        pass
    try:
        rows = read_invenanim(snap)
        with open(out_dir/'invenanim.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#code\tgroup\tindex\taction\tspeed  (InvenItemAnimation; speed as binary32 bits)\n')
            for key, group, index, action, speed in rows:
                f.write(f'{key}\t{group}\t{index}\t{action}\t{speed}\n')
        counts['invenanim'] = len(rows)
    except SnapshotError:
        pass
    try:
        rows, default = read_legendary(snap)
        with open(out_dir/'legendary.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#type\tcode00\tcode01\tcode10\tcode11  (LegendaryItemSetType record +4..+0x10)\n')
            f.write('default\t' + '\t'.join(str(c) for c in default) + '\n')
            for key, codes in rows:
                f.write(f'{key}\t' + '\t'.join(str(c) for c in codes) + '\n')
        counts['legendary'] = len(rows)
    except SnapshotError:
        pass
    try:
        sets, items = read_cashsets(snap)
        with open(out_dir/'cashsets.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#set<TAB>i<TAB>name<TAB>second name | item<TAB>group<TAB>index<TAB>set  (CashItemSetOption)\n')
            for i, (name, name2) in enumerate(sets):
                f.write(f'set\t{i}\t{escape(name)}\t{escape(name2)}\n')
            for group, index, set_ in items:
                f.write(f'item\t{group}\t{index}\t{set_}\n')
        counts['cashsets'] = len(sets)
        counts['cashset_items'] = len(items)
    except SnapshotError:
        pass

    try:
        rows, default = read_buffs(snap)
        with open(out_dir/'buffs.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#index\tgroup\titem_group\titem_index\ttype\tx2c\tx30\tvalue_kind\tname\tline...  '
                    '(BuffEffect; type 1 debuff, 2 cash buff; the description lines follow the name; '
                    '"default" = the default record +0x40)\n')
            for b in [default] + rows:
                f.write('\t'.join(str(b[c]) for c in ('index', 'group', 'item_group', 'item_index', 'type', 'x2c', 'x30',
                                                     'value_kind')) + '\t' + escape(b['name']) +
                        ''.join('\t' + escape(line) for line in b['lines']) + '\n')
        counts['buffs'] = len(rows)
    except SnapshotError:
        pass
    try:
        rows, default = read_charinfo(snap)
        with open(out_dir/'charinfo.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#id\tcolor\tgroup\ttype\tsort\tvalue_color\tbutton\tclasses\tlabel\tprefix\tsuffix  '
                    '(CharacterInfoSetup; classes: one digit per class index; "default" = the default record +0x44)\n')
            for c in [default] + rows:
                f.write('\t'.join(str(c[k]) for k in ('id', 'color', 'group', 'type', 'sort', 'value_color', 'button')) +
                        '\t' + (''.join('1' if v else '0' for v in c['classes']) or '-') + '\t' +
                        '\t'.join(escape(c[k]) for k in ('label', 'prefix', 'suffix')) + '\n')
        counts['charinfo'] = len(rows)
    except SnapshotError:
        pass
    try:
        rows = read_skillreq(snap)
        with open(out_dir/'skillreq.tsv', 'w', encoding='ascii', newline='\n') as f:
            f.write(note + '#key\tx00\tskill\titem_group\titem_index\tx10\tx14\tx18  (SkillRequire, lookup 0x00abf829)\n')
            for row in rows:
                f.write('\t'.join(str(v) for v in row) + '\n')
        counts['skillreq'] = len(rows)
    except SnapshotError:
        pass

    names = dict(text)
    maps = map_name_table()
    with open(out_dir/'mapnames.tsv', 'w', encoding='ascii', newline='\n') as f:
        f.write(note + '#world\tglobaltext\tname  (from the map-name function 0x016baaa6; -1: no GlobalText)\n')
        for world, gt, _ in maps:
            f.write(f'{world}\t{gt}\t{escape(names.get(gt, b""))}\n')
    counts['mapnames'] = len(maps)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('snapshot', help='langread output (MULANGV1)')
    parser.add_argument('--out', required=True, help='output directory (local; never commit)')
    args = parser.parse_args(argv)
    try:
        counts = convert(Snapshot.load(args.snapshot), args.out)
    except SnapshotError as error:
        print(f'live_lang_to_plain: {error}', file=sys.stderr)
        return 1
    print(' '.join(f'{k}={v}' for k, v in counts.items()), '->', args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
