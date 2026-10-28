# Generated client record layout

LAYOUT-001, 2026-10-27. The source is `native/session/layout/*.def`; the schema and commands are
in [its README](../../native/session/layout/README.md). No live client was attached or written.

The 15 records have 118 bound fields. They cover CHARACTER, CharacterAttribute,
CharacterMachine, the separate StatMachine, OBJECT, ITEM, and nine separate address-bound scene
globals. These are curated bindings for current consumers, not a claim that all client records
or every unknown byte have been recovered. All extents remain STATIC known extents. Only the
seven [probed fields](client-layout-probes.md) are labeled VERIFIED; their semantic and capacity
limits remain as documented in that finding.

`gen_layout.py` generates the indexed C accessors, per-record field tables, registry/digest and
`native/build/gen/layout.json`. The session's lease audit and snapshot dump use the same tables.
Unknown gaps remain protected during leases. CharacterAttribute storage now covers the known
0x1b50 extent, while verified progress routines continue to use their original 0x200 prefix.
CharacterMachine contains attributes inline at +8; it is distinct from the 0x1e4 stat machine.

The portable projection comparison compiles the generated C and tests every field and array
element against Python's independent JSON offsets and struct decoding. It also checks packed
bytes, restored fields, untouched unknown gaps, and rejection of short buffers and bad indexes.
Real negative builds reject duplicate and overlapping declarations before emitting any output.

`live-readers/objread.c` builds its OBJECT size/next pointer and scene constants through
`layout_manifest.py` from JSON. Its snapshot format and scene entry order are preserved; no
reader was attached to a process for this milestone. `scripts/validate_items.py` replaces both
pasted OBJECT/ITEM field lists with JSON tables. Its instruction comparison is rerun against the
same captures, unchanged reconstruction, cases and controls used for LAYOUT-PROBE-001.

The journal header now stores the canonical layout digest. Generated zone boundaries change the
snapshot segmentation but preserve byte coverage, including unknown gaps. The record header and
snapshot payload format stay the same; no automatic migration of old layout digests is claimed.

Actual checks and remaining limits are in [the handoff](../handoffs/LAYOUT-001.md).
