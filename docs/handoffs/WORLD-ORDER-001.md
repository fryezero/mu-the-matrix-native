# WORLD-ORDER-001 handoff

Worktree `~/Documents/MTM/worktrees/world-order-001`, branch `codex/world-order-001`, base `2b8c8f5`, including
INPUT-001 PR #190. No sub-agents or live game were used.

## Result

The MoveMainScene / RenderMainScene call-order family is authored C through the scene-manager host shape.
`test_world_parts.py` reads its compiled records and the explicit native adapters, replacing its literal tick
and draw lists. Runtime source and numeric part order columns are unchanged. The finding records the
original-address anchors, all native reorderings/groupings/additions, body pins and limitations:
[client-world-order](../research/client-world-order.md).

Owned implementation is `reconstructed/world-order/`, `scripts/validate_world_order.py`, its manifest row,
`native/tests/test_world_parts.py` and comments in `native/world/parts.def`. Shared documentation edits only
add this milestone's status/continuation and change its plan row.

## Checks

- Private instructions: 1,200 tick and 1,200 draw cases, 78,585 / 63,888 calls compared, zero mismatches or stops.
- All decoded conditional edges covered: 136/136 tick, 158/158 draw. Ten compiled mutants, 400 comparisons
  each, all detected by stream differences and zero stops. The finding lists each count.
- Focused private tests: 14/14 pass. Portable run: 14 tests, one explicit private skip. Missing anchors,
  original-call reorder propagation, all 42 adjacent native order swaps, hooks and dispatch are checked.
- Validator manifest tests: 17/17 pass. The registered family uses 2,400 total cases and ten mutants.
- Full local macOS gate passes at source checkpoint `8555b11`: 1,430 tests across 38 suites, 175 explicit
  skips, zero failures. All six fixture scenarios pass; viewer and read-only readers build. The readers were
  never run against a client. Final registered validator: one pass, zero skips/failures/errors.
- The 23 complete MU_PART rows compare byte-for-byte with origin/main after removing comments; all six
  numeric columns are unchanged. No executable native source is edited. `git diff --check` passes.
- Gate audit: 1,303 files, zero rejected. Final staged documentation audit: 1,304 files, zero rejected.

No fresh original-image comparison is claimed. All existing numeric orders and executable native source
are preserved; existing hash/render regressions are included in the full gate.

## Evidence and remaining boundary

Scratch/reports: `~/Documents/MTM/mu-mac-tools/native/scratch/world-order-001/`.
`private-tests.log` records the focused private run. `final-registered/` holds the manifest-run report,
input/body pins and source digests. `local-macos-ci.log` is the full gate. Early reports are retained as
failed fixture/model/manifest preconditions and described in the finding.

The family compares call identity/order, virtual slots and draw success. Callee bodies, arguments/ECX,
general writes, exception handling and real callee side effects are outside it. The packet interval is one
opaque event. The ordinary stream projects to static native columns; conditional original passes are
validated separately and native differences remain explicit adapters. They are later fidelity work, not
an unimplemented claim of this milestone. No client bytes, decoded data, snapshots or generated artifacts
are committed. The two local input symlinks are never staged. They are untracked directory symlinks, despite their targets
being ignored directories. The fixture report's dirty flag includes these symlinks and documentation edits;
no native executable source changed after the gate's source checkpoint.
