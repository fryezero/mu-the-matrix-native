# RENDER-WORLDS-H

Implemented the complete primary create/move/visual group for Duel Arena and world 82.
[Finding, exact addresses, domains and DATA-ACQ-002 needs](../research/client-worlds-h.md).

- Owned new worktree `~/Documents/MTM/worktrees/render-worlds-h`, branch `codex/render-worlds-h`,
  from origin/main `6fcbfb4`. Scope claim: issue #203. Per-world C with minimal shared object dispatch.
- Six instruction families, 1,000 cases each: **6,000 comparisons, zero mismatches/stops, 19/19 compiled mutants
  detected**. All OBJECT bytes, AL, ordered expanded calls and final RNG state compared. Recording engine
  boundaries and the type-48 zero-divisor host guard are explicit in the finding.
- Registered G/H regression: **12,000 cases, zero mismatches/stops, 32/32 compiled mutants**; two pass,
  zero failures/errors/skips. Inventory: 48 classes, 57 world registrations, 288 addresses checked.
- Coverage: **9/48 classes, 25/144 verified primary families, zero static-only and 119 missing**.
- Production native host: eleven emitter types, 200 draws each, with exact callbacks, owners and effect scale;
  every type also checks absent/unloaded models and RNG stability. Public dispatch, bounded logs and invalid
  scatter-scale safety regressions pass. Three separately linked native omission/scale controls are caught. G's generic-sibling test now uses unimplemented world 65 instead of 64.
- Saved October 22 fourteen-view regression: **28/28 PNG hashes, 14/14 object dump hashes and 14/14 light dump
  hashes identical** against the pre-change baseline. Original stale manifest paths were repaired only in local
  task manifests. Worlds 64/82 have no live object/image capture, so no image-fidelity improvement is claimed.

## Final locked integration

Acquired the merge lock at 09:20 CDT. Latest origin/main `48bfe7c`, including skill-session #204 and
README #205, is merged as `76d8e87`. Shared conflicts keep both status entries, both validator rows,
the H host target and the generated-header core dependencies. No sibling implementation was dropped.

`bash scripts/local-macos-ci.sh` passes: **1,511 tests across 38 discovery runs, 187 explicit private/optional
skips, zero failures/errors; 8/8 fixture scenarios; native viewer and read-only reader builds; publication
audit 1,429 files, zero rejected**. No hosted workflow was dispatched, and readers were built only.
The final registered G/H rerun passes the same 12,000 cases and 32 compiled mutants without errors/skips.
The integrated native binary again retains all 28 PNG and 28 object/light dump hashes against baseline
`6fcbfb4`. No image change from the imported skill/README work appears in these unpopulated tour views.
Only evidence/status documentation changed after this gate.

During execution, reports are in `scratch/render-worlds-h` and images in `renders/render-worlds-h`, under
`~/Documents/MTM/mu-mac-tools/native/`. Both entire task folders and worktree builds are removed after merge;
these committed counts and limits are the retained evidence.

No live client/launcher was started, stopped, driven or read. No service, wire, protection-module,
main-checkout build or sibling-worktree work. No original bytes, assets, snapshots, renders or input links staged.
Self-review covers standards, original behavior, native consumers and evidence boundaries; no independent review.

Remaining: DATA-ACQ-002 for world 64 and 82 objects/models/light/clock/RNG/pools/camera/PNG, the other 119 primary
methods and separately inventoried custom/after/invisible slots. The finding lists the unsupported downstream particle/effect requests; their lifecycles and full nested-pool image replay remain open.
After merge, remove this task's scratch/renders/builds, worktree and local branch. No newly created local INPUT
needs to survive. Counts and limitations remain in this handoff, the finding and PR.
