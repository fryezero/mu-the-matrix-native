# LAYOUT-001 handoff

Owned worktree `~/Documents/MTM/worktrees/layout-001`, branch `codex/layout-001`, based on
LAYOUT-PROBE-001's merge `15962e94cb4c2d8bcf85ade0d7bba0867b50d214`.

## Changes

- `native/session/layout/{viewport,hero,objects,items,scene}.def`: 15 records and 118 bound fields.
  Only the seven probed fields are VERIFIED. Every record extent is STATIC/known_extent.
- `scripts/gen_layout.py`: validated cross-domain merge, bounds/type/name/zone/evidence checks,
  overlap refusal, deterministic per-record headers, indexed read accessors, field registry,
  projection helpers and `native/build/gen/layout.json` with a canonical digest. Generated outputs
  are ignored build artifacts. All validation precedes writes.
- `scripts/layout_manifest.py`: JSON digest check, Python field formats and the reader-header compiler.
- Native Makefile: `layout` and a generation stamp required by session dev/product objects and tool.
- Hero: generated scalar accessors; attribute storage covers known 0x1b50 extent; the generated
  tables replace its handwritten audit/dump zones. Unknown gaps remain replicated; prefix-owned
  records are clipped to their actual allocation. Audit overflow aborts instead of silently skipping.
- Journal: layout digest at header bytes 40..71, same snapshot record format with manifest-defined
  field boundaries and protected unknown gaps.
- `live-readers/objread.c`: JSON-derived OBJECT size/link and scene global constants. `validate_items.py`:
  JSON-derived OBJECT/ITEM projection lists. All reconstructed routines remain unchanged.
- Existing session build-test copies now generate layout headers; the lease test expects the manifest's
  exact `class_byte` name. New tests cover the generator, compiled projection/accessors and real journal.

## Checks

- Five generator/projection/consumer tests pass: 3 real overlap build failures, 6 invalid-declaration
  failures, deterministic/disjoint domain merge, previous-output preservation on failure, every field
  and every array element through compiled C, short buffers, bad indexes, untouched unknown bytes,
  JSON-driven reader constants, existing validator tables, and JSON digest rejection.
- The changed item validator: 3,740 original-instruction cases, zero mismatches, 10/11 existing controls
  detected, identical to the probe milestone. The frustum control's zero remains a documented limit.
- Local macOS gate and journal integration: final counts are recorded below after the updated-main gate.

Private reports/logs: `~/Documents/MTM/mu-mac-tools/native/scratch/layout-001/`.

## Limits and next work

The manifest covers the bound fields, not every unknown client byte. Other domains can add disjoint
fields and migrate their consumers in their own session milestones. The label-level interpretation,
array capacity and full allocation extents retain the probe finding's static boundaries. Old journals
are not migrated automatically by layout digest. No client process was read or written, and no live
game, network or protection work was performed. Renders and reconstructed gameplay behavior were not
changed; only snapshot segmentation, the layout digest and known attribute storage coverage change.
