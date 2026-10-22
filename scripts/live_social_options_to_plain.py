#!/usr/bin/env python3
"""Export item option tables from authorized private Lang snapshots.

Authored schemas from client-social.md. Output contains private game text;
keep it outside git. Requires complete records, including ArtifactOption's
0x84-byte tail (older captures can be more complete than newer ones).
"""
import argparse
import hashlib
import json
from pathlib import Path

from live_lang_to_plain import Snapshot, escape

GUARDIAN = 0x06FBBF24
ADVANCED = 0x06FBBFCC
ARTIFACT = 0x06FBC47C


def rows(snapshot, artifact_snapshot):
    """Return typed rows: kind, numeric columns, escaped source bytes."""
    out = []
    for offset, kind in ((0x38, "guardian_name"), (0x48, "guardian_bonus_name")):
        for key, node in snapshot.tree(GUARDIAN + offset):
            r = node + 0x14
            snapshot.read(r, 0x1C)
            out.append((kind, [key], snapshot.string(r + 4)))
    for offset, kind, size in (
        (0x40, "guardian_value", 0x14),
        (0x50, "guardian_bonus", 0x20),
    ):
        for key, node in snapshot.tree(GUARDIAN + offset):
            r = node + 0x14
            snapshot.read(r, size)
            out.append(
                (kind, [key] + [snapshot.i32(r + x) for x in range(0, size, 4)], b"")
            )
    for key, node in snapshot.tree(ADVANCED + 0x38):
        r = node + 0x14
        snapshot.read(r, 0x34)
        out.append(
            (
                "advanced",
                [key, snapshot.i32(r + 4)]
                + [snapshot.i32(r + x) for x in range(0x20, 0x34, 4)],
                snapshot.string(r + 8),
            )
        )
    for key, node in artifact_snapshot.tree(ARTIFACT + 0x38):
        r = node + 0x14
        artifact_snapshot.read(r, 0x20)
        out.append(
            (
                "artifact_name",
                [key, artifact_snapshot.i32(r + 0x1C)],
                artifact_snapshot.string(r + 4),
            )
        )
    for key, node in artifact_snapshot.tree(ARTIFACT + 0x40):
        r = node + 0x14
        artifact_snapshot.read(r, 0x84)  # Reject a captured leading prefix.
        out.append(
            (
                "artifact",
                [key, artifact_snapshot.i32(r + 4)]
                + [artifact_snapshot.i32(r + x) for x in range(0x20, 0x84, 4)],
                artifact_snapshot.string(r + 8),
            )
        )
    return out


def elemental_rows(s, old):
    """Exact family keys and complete numeric vectors; private source bytes."""
    import struct

    out = []

    def ints(p, n):
        return list(struct.unpack("<" + "i" * n, s.read(p, 4 * n)))

    def vector(snapshot, p, stride):
        a, b, c = struct.unpack("<III", snapshot.read(p, 12))
        if a > b or b > c or (b - a) % stride:
            raise ValueError("invalid captured vector")
        return range(a, b, stride)

    def add(kind, values, text=b""):
        out.append((kind, values, text))

    for key, node in old.tree(0x6FBAA60 + 0x38):
        r = node + 20
        old.read(r, 0xE0)
        add(
            "earring_primary",
            [old.i32(r + 0xDC), old.i32(r), old.i32(r + 0xD4)],
            old.string(r + 4),
        )
    for key, node in old.tree(0x6FBAA60 + 0x40):
        r = node + 20
        old.read(r, 0x80)
        add(
            "earring_pair",
            [old.i32(r), old.i32(r + 4)]
            + [old.i32(r + x) for x in range(0x20, 0x38, 4)],
            old.string(r + 8),
        )
    for tag, node in s.tree(0x6FBAA60 + 0x50):
        for pos, r in enumerate(vector(s, node + 20, 12)):
            add("earring_value", [tag, pos] + ints(r, 3))
    for key, node in s.tree(0x6FBAAC0 + 0x38):
        r = node + 20
        s.read(r, 0x20)
        add("earring_name", [key, s.i32(r + 0x1C)], s.string(r + 4))
    for key, node in s.tree(0x6FBAE4C + 0x3C):
        r = node + 20
        s.read(r, 0x34)
        ids = [s.i32(p) for p in vector(s, r + 0x28, 4)]
        if len(ids) != 7:
            raise ValueError("unexpected pentagram option vector")
        add("pentagram", [s.i32(r + 8), s.i32(r + 0x24)] + ids, s.string(r + 0xC))
    for key, node in s.tree(0x6FBAE4C + 0x44):
        r = node + 20
        req = []
        for p in vector(s, r + 0x1C, 12):
            values = [s.i32(q) for q in vector(s, p, 4)]
            if len(values) != 3:
                raise ValueError("incomplete prerequisite triple")
            req.extend(values)
        if len(req) != 15:
            raise ValueError("incomplete prerequisite vector")
        add("pentagram_option", [key] + req, s.string(r + 4))
    for r in vector(s, 0x6FBAEFC + 0x3C, 0x50):
        s.read(r, 0x50)
        display = [s.i32(p) for p in vector(s, r + 0x1C, 4)]
        stats = [s.i32(p) for p in vector(s, r + 0x28, 4)]
        if len(display) != 11 or len(stats) != 11:
            raise ValueError("incomplete elemental level vector")
        add(
            "jewel",
            [
                s.i32(r + 4),
                s.i32(r + 0x10),
                s.i32(r + 0x14),
                s.i32(r),
                s.i32(r + 0x18),
                s.i32(r + 0x4C),
            ]
            + display
            + stats,
            s.string(r + 0x34),
        )
    for pos, r in enumerate(vector(s, 0x6FBC00C + 0x38, 0x4C)):
        ids = [s.i32(p) for p in vector(s, r + 0x34, 4)]
        values = [s.i32(p) for p in vector(s, r + 0x40, 4)]
        if len(ids) != 6 or len(values) != 6:
            raise ValueError("incomplete elemental set")
        add("ertel_set", [pos, s.i32(r)] + ids + values, s.string(r + 4))
    for pos, r in enumerate(vector(s, 0x6FBC09C + 0x38, 0x1C)):
        add("ertel_text", [pos, s.i32(r)], s.string(r + 4))
    return out


def export(snapshot_path, artifact_path, directory):
    source = snapshot_path.read_bytes()
    artifact_source = artifact_path.read_bytes()
    result = rows(Snapshot(source), Snapshot(artifact_source))
    result += elemental_rows(Snapshot(source), Snapshot(artifact_source))
    counts = {}
    lines = ["# mu-social-options-v1: kind, typed numeric columns, escaped ANSI text"]
    # Explicit availability includes loaded-empty tables, unlike row presence.
    families = "guardian_name guardian_value guardian_bonus_name guardian_bonus advanced artifact_name artifact earring_primary earring_pair earring_value earring_name pentagram pentagram_option jewel ertel_set ertel_text".split()
    lines += ["# available " + kind for kind in families]
    for kind, values, text in result:
        counts[kind] = counts.get(kind, 0) + 1
        lines.append("\t".join([kind] + [str(v) for v in values] + [escape(text)]))
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "social-options.tsv").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    metadata = {
        "schema": 1,
        "snapshot_sha256": hashlib.sha256(source).hexdigest(),
        "artifact_snapshot_sha256": hashlib.sha256(artifact_source).hexdigest(),
        "rows": counts,
    }
    (directory / "social-options-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("snapshot", type=Path)
    p.add_argument("--artifact-snapshot", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    a = p.parse_args()
    print(
        json.dumps(
            export(a.snapshot, a.artifact_snapshot or a.snapshot, a.out_dir),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
