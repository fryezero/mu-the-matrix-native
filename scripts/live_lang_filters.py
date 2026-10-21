#!/usr/bin/env python3
"""Write the character-name filter tables from a langread snapshot (NATIVE-CHARCREATE-001).

The create panel's OnEnterCharacterName 0x00b49eca refuses a name through 0x00b4b29d, which tests two Lang.mpr
tables (docs/research/client-character-select.md section 11):

  filtername.txt   FilterName(kor) 0x06fbacd0 (manager +0x270): words found anywhere in the name (0x0110cb45)
  filter.txt       Filter(kor)     0x06fbac88 (manager +0x228): words found in the name without spaces (0x0110c9f2)

Each table object holds a std::vector<std::string> at +0x38 (begin, end; 0x18-byte strings, the size 0x0096a4d8
and index 0x00b3b292 helpers).  One word per line, escaped as live_lang_to_plain.py escapes (the client's bytes,
\\xHH outside printable ASCII).  The output is the server team's data: keep it local (next to the other
plaintexts in MU_LANG_DIR), never commit it.

  live_lang_filters.py SNAPSHOT OUT_DIR
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_lang_to_plain as L  # noqa: E402

TABLES = (('filter.txt', 0x06fbac88), ('filtername.txt', 0x06fbacd0))


def read_vector(snap, table):
    begin, end = snap.u32(table + 0x38), snap.u32(table + 0x3c)
    if end < begin or (end - begin) % 0x18 or end - begin > 0x18 * 100000:
        raise L.SnapshotError(f'bad vector at {table + 0x38:#x}')
    return [snap.string(begin + 0x18 * k) for k in range((end - begin) // 0x18)]


def convert(snap, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, table in TABLES:
        words = read_vector(snap, table)
        (out_dir / name).write_text(''.join(L.escape(w) + '\n' for w in words), encoding='ascii')
        counts[name] = len(words)
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('snapshot', type=Path)
    ap.add_argument('out_dir', type=Path)
    a = ap.parse_args(argv)
    counts = convert(L.Snapshot.load(a.snapshot), a.out_dir)
    for name, n in counts.items():
        print(f'{name}: {n} words')
    return 0


if __name__ == '__main__':
    sys.exit(main())
