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
