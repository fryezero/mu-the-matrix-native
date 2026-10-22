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


def export(snapshot_path, artifact_path, directory):
    source = snapshot_path.read_bytes()
    artifact_source = artifact_path.read_bytes()
    result = rows(Snapshot(source), Snapshot(artifact_source))
    counts = {}
    lines = ["# mu-social-options-v1: kind, typed numeric columns, escaped ANSI text"]
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
