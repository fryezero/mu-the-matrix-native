"""RENDER-EFFECTS-008: live_effect_table_to_plain.py on synthetic langread snapshots."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import live_effect_table_to_plain as plain  # noqa: E402
from live_lang_to_plain import Snapshot, SnapshotError  # noqa: E402


class Memory:
    """Blocks of a synthetic MULANGV1 snapshot, allocated upward from a heap base."""

    def __init__(self):
        self.blocks, self.top = {}, 0x20000000

    def put(self, address, payload):
        self.blocks[address] = bytes(payload)

    def alloc(self, payload):
        address = self.top
        self.top = (self.top + len(payload) + 0xf) & ~0xf
        self.put(address, payload)
        return address

    def string(self, text):
        if len(text) < 16:
            return text.ljust(16, b'\0') + struct.pack('<II', len(text), 15)
        buffer = self.alloc(text + b'\0')
        return struct.pack('<I', buffer) + bytes(12) + struct.pack('<II', len(text), len(text) | 0xf)

    def tree(self, items):
        """MSVC std::map of (key, value bytes): returns the head address."""
        head = self.top
        self.top += 0x20
        keys = [k for k, _ in items]
        nodes = {k: self.top + 0x100 * n for n, k in enumerate(keys)}
        self.top += 0x100 * len(keys)

        def link(lo, hi, parent):
            if lo >= hi:
                return head
            mid = (lo + hi) // 2
            node = nodes[keys[mid]]
            left, right = link(lo, mid, node), link(mid + 1, hi, node)
            self.put(node, struct.pack('<IIIBBxxi', left, parent, right, 1, 0, keys[mid]) + dict(items)[keys[mid]])
            return node
        root = link(0, len(keys), head)
        self.put(head, struct.pack('<IIIBBxx', nodes[keys[0]] if keys else head, root,
                                   nodes[keys[-1]] if keys else head, 1, 1))
        return head

    def snapshot(self):
        out = [b'MULANGV1', struct.pack('<I', len(self.blocks))]
        for address, payload in self.blocks.items():
            out += [struct.pack('<II', address, len(payload)), payload]
        return b''.join(out)


def entry(mem, path, scale, bone, follow, actions=(), tint=0, start=0):
    raw = bytearray(0x54)
    raw[4:0x1c] = mem.string(path)
    struct.pack_into('<7fi', raw, 0x1c, 1.0, -2.0, 70.0, 1.5, 0.0, -0.25, scale, bone)
    raw[0x3c], raw[0x3d] = follow, tint
    struct.pack_into('<I', raw, 0x44, start)
    if actions:
        buffer = mem.alloc(struct.pack(f'<{len(actions)}i', *actions))
        struct.pack_into('<III', raw, 0x48, buffer, buffer + 4 * len(actions), buffer + 4 * len(actions))
    return bytes(raw)


def build(muun=True):
    mem = Memory()
    worlds = []
    for world, types in ((116, {62: [(b'Data\\Effect\\fire01-green01.ein', 50.0, 0, 1)],
                                67: [(b'Data\\Effect\\fire01-red01.ein', 60.0, 0, 1),
                                     (b'Data\\Effect\\smoke13-black01.ein ', 40.0, 3, 0, (0, 2), 1, 0x00220000)]}),
                         (63, {69: [(b'Data\\Effect\\twister19-yellow01.ein', 350.0, 44, 1)], 70: []})):
        inner = []
        for kind, rows in sorted(types.items()):
            data = b''.join(entry(mem, *r) for r in rows)
            begin = mem.alloc(data) if data else 0
            inner.append((kind, struct.pack('<III', begin, begin + len(data), begin + len(data))))
        record = bytearray(0x44)
        struct.pack_into('<II', record, 0x3c, mem.tree(inner), len(inner))
        worlds.append((world, bytes(record)))
    worlds.sort()
    mem.put(plain.TABLE, struct.pack('<II', mem.tree(worlds), len(worlds)))
    if muun:
        value = bytearray(0x40)
        value[4:0x1c] = mem.string(b'Data\\Effect\\leaf_particle_F.ein')
        struct.pack_into('<7fi', value, 0x1c, -55.0, 11.0, 0.0, 1.5, 0.75, 0.0, 9.0, 5)
        value[0x3c] = 1
        mem.put(plain.MUUN, struct.pack('<II', mem.tree([(173, bytes(value[4:]))]), 1))
    return mem


class EffectTablePlain(unittest.TestCase):
    def test_rows_in_map_and_vector_order(self):
        with tempfile.TemporaryDirectory() as td:
            summary = plain.convert(Snapshot(build().snapshot()), td)
            lines = (Path(td) / 'mapeffects.tsv').read_text().splitlines()
            muun = (Path(td) / 'muuneffects.tsv').read_text().splitlines()
        self.assertEqual((summary['worlds'], summary['types'], summary['entries'], summary['muun_records']),
                         (2, 4, 4, 1))
        rows = [line.split('\t') for line in lines if not line.startswith('#')]
        self.assertEqual([r[:4] for r in rows], [
            ['63', '69', '0', 'Data\\\\Effect\\\\twister19-yellow01.ein'],
            ['116', '62', '0', 'Data\\\\Effect\\\\fire01-green01.ein'],
            ['116', '67', '0', 'Data\\\\Effect\\\\fire01-red01.ein'],
            ['116', '67', '1', 'Data\\\\Effect\\\\smoke13-black01.ein ']])   # a heap string, kept byte for byte
        self.assertEqual(rows[3][4:], ['1.0', '-2.0', '70.0', '1.5', '0.0', '-0.25', '40.0', '3', '0', '1',
                                       '00220000', '0,2'])
        self.assertEqual(rows[0][11:], ['44', '1', '0', '00000000', '-'])
        self.assertEqual(muun[2].split('\t'), ['173', 'Data\\\\Effect\\\\leaf_particle_F.ein', '-55.0', '11.0',
                                                '0.0', '1.5', '0.75', '0.0', '9.0', '5', '1'])

    def test_missing_vector_or_muun(self):
        mem = build(muun=False)
        with tempfile.TemporaryDirectory() as td:
            self.assertNotIn('muun_records', plain.convert(Snapshot(mem.snapshot()), td))
        # a vector buffer the snapshot lacks (the first session's graph scan) is an error, not a short table
        victim = max(a for a in mem.blocks if a != plain.TABLE and a != plain.MUUN and len(mem.blocks[a]) == 0x54 * 2)
        del mem.blocks[victim]
        with self.assertRaises(SnapshotError):
            plain.read_table(Snapshot(mem.snapshot()))


if __name__ == '__main__':
    unittest.main()
