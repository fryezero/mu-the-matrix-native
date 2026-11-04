"""RENDER-WORLDS-AFTER5: live_anim_table_to_plain.py on synthetic langread snapshots."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_anim_table_to_plain as plain  # noqa: E402
from live_lang_to_plain import Snapshot, SnapshotError  # noqa: E402
from test_effect_table_plain import Memory  # noqa: E402


def entry(mem, kind, action, speed, handler, param, extra=()):
    raw = bytearray(0x20)
    struct.pack_into('<iifii', raw, 0, kind, action, speed, handler, param)
    if extra:
        buffer = mem.alloc(struct.pack(f'<{len(extra)}i', *extra))
        struct.pack_into('<III', raw, 0x14, buffer, buffer + 4 * len(extra), buffer + 4 * len(extra))
    return bytes(raw)


def build(bad_key=False):
    mem = Memory()
    worlds = []
    for world, rows in ((144, [(13, 0, 0.21, 2, 300, (6, 11, 1)), (13, 1, 0.27, 2, 300, (1, 2, 0)),
                               (32, 0, 0.07, 0, 300, ())]),
                        (142, [(107, 0, 4.0, 0, 0, ())])):
        items = sorted(((1000 * a + k + (1 if bad_key else 0), entry(mem, k, a, s, h, p, x))
                        for k, a, s, h, p, x in rows))
        head = mem.tree(items)
        loader = struct.pack('<I', 0x01aada94) + bytes(0x34) + struct.pack('<II', head, len(items))
        worlds.append((world, loader))
    head = mem.tree(sorted(worlds))
    mem.put(plain.TABLE, struct.pack('<II', head, len(worlds)) + bytes(0x40))
    return Snapshot(mem.snapshot())


class AnimTablePlain(unittest.TestCase):
    def test_rows(self):
        with tempfile.TemporaryDirectory() as td:
            summary = plain.convert(build(), td)
            lines = (Path(td) / 'mapanim.tsv').read_text().splitlines()
        self.assertEqual(summary['worlds'], [142, 144])
        self.assertEqual(summary['entries'], 4)
        self.assertEqual(summary['handlers'], [0, 2])
        rows = [line.split('\t') for line in lines if not line.startswith('#')]
        self.assertEqual(rows[0], ['142', '107', '0', '4.0', '0', '0', '-'])
        self.assertEqual(rows[1][:3], ['144', '13', '0'])                   # key order: action 0 first
        self.assertEqual(struct.pack('<f', float(rows[1][3])), struct.pack('<f', 0.21))   # binary32 round trip
        self.assertEqual(rows[1][4:], ['2', '300', '6,11,1'])
        self.assertEqual([r[1:3] for r in rows[1:]], [['13', '0'], ['32', '0'], ['13', '1']])

    def test_key_mismatch(self):
        with self.assertRaises(SnapshotError):
            plain.read_table(build(bad_key=True))


if __name__ == '__main__':
    unittest.main()
