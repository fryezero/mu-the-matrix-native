# Client record layout declarations

LAYOUT-001. `scripts/gen_layout.py` merges every `*.def` in this directory. A domain lane adds
its own file rather than editing a shared field list. Identical record declarations may repeat;
all overlapping field declarations fail, including identical ones. Diagnostics name both sources.
Validation completes before output changes. Unknown fields may be added later as disjoint ranges.

```
MU_RECORD(record, known_extent_bytes, evidence)
MU_FIELD(record, offset, byte_size, type, zone, member, evidence)
MU_ADDRESS(record, address) // optional, for a fixed scene global
```

Types are `u8/i8/u16/i16/u32/i32/u64/i64/f32/bytes`. A size larger than the type width is an
array. All scalar storage is little endian; no native struct packing or alignment is assumed.
`bytes` is opaque storage, not decoded client data. `MU_ADDRESS` describes a separate record,
so scattered scene globals do not imply a contiguous structure.

Zones are REPLICATED, MOTION and VIEW. Evidence is VERIFIED, STATIC or LIVE. VERIFIED here means
that [LAYOUT-PROBE-001](../../../docs/research/client-layout-probes.md) executed the field's load.
It does not upgrade the semantic name, array capacity or record allocation size. Currently exactly
seven fields have that label. All record sizes have `extent_kind: known_extent`, and remain STATIC.
In particular CharacterAttribute 0x1b50 is a minimum, not a proven complete allocation. Its skill
array capacities are static; the bounded load probe also tests indexes beyond the byte count's range.

Sources for STATIC rows are the authored offsets in `reconstructed/progress/progress.h`,
`reconstructed/charsel/charsel.h`, `reconstructed/players/remote_players.h`, the ground-item
field mappings formerly in `scripts/validate_items.py`, and the scene addresses formerly in
`live-readers/objread.c`. CharacterMachine contains attributes inline at +8. StatMachine is the
separate 0x1e4 class object with owner/attribute pointers and derived totals.

`make -C native layout` writes ignored outputs under `native/build/gen/`:

- `layout_<record>.h`: bounds-checked, indexed read accessors, field metadata and record tables.
- `layout_types.h`: native/offline projection and restore helpers. Restore writes caller-owned byte
  buffers only. The native code has no mechanism for writing to a client process.
- `layout_all.h`: the record registry and manifest digest.
- `layout.json`: the same fields, widths, zones, evidence, known extents and optional global addresses.
  `sha256` covers canonical JSON without the digest key. Source file/line provenance is included.

Projection packs only bound fields; restore leaves unknown gaps untouched. The lease adapter uses
the field tables but also protects unknown gaps as replicated, including in prefix-sized records.
The journal dumps those same zones and records the layout digest at header bytes 40..71. Old journals
retain their existing reader/build-digest contract; consumers can inspect the layout digest before
interpreting snapshots. There is no automatic old-layout migration.

Consumers currently migrated: hero scalar reads, hero lease/journal zone tables, `objread`'s OBJECT
size/link and scene globals, and `validate_items.py`'s OBJECT/ITEM projection tables. The Python
consumer `scripts/layout_manifest.py` verifies the JSON digest and produces the reader header.
All other per-domain mappings can migrate in their session milestones. Existing reconstructed
routines and their C offsets remain unchanged for independent instruction comparisons.

Tests are `native/tests/test_layout.py` and `test_layout_session.py`. They exercise every bound
field and every array element, short buffers, untouched gaps, negative builds, deterministic
lane merging, evidence labels, JSON consumers and real session journal snapshots.
