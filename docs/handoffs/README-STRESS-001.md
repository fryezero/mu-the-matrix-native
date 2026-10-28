# README-STRESS-001

Implemented on codex/readme-stress-001 in its own worktree, from origin/main
b74de71. No live game, launcher or account state used. No reconstruction files
in the concurrent RENDER-ITEMS-002 part-6 lane were changed.

[Finding, reproduction, privacy review and hashes](../research/readme-stress.md).

## Changes

- Added `26-80-players-lorencia.jpg` and `27-80-players-tormenta-combat.jpg`,
  1600x1000 JPEGs, visually reviewed after encoding and pinned in the audit.
- Fixed the remote armour fallback's glow-directory argument. It formerly
  loaded base textures from Data/Player but looked for chrome/glow textures in
  Data/Item. The correct Data/Effect textures now load; +11 characters remain
  textured in immediate and batched GL. This was not a missing body recipe.
- Added per-slot effect texture diagnostics and made the stress completeness
  check reject absent glow textures. Reconstructed item/renderchar rules stay
  unchanged. The finding flags the analogous ground-item fallback for its lane.
- Added opt-in `MU_GFX_PUBLIC_DEMO=1`, with Preview and authored round resource
  maxima. Normal defaults and server-state setters retain their behavior.
- Added a reproducible offline capture script with varied gear/classes, screen
  rows, eight monsters, normal scenery/skill effects, closed panels and demo HUD.
- README gives the historical #201 crowd80 18.4 / tormenta80 18.9 fps as context.
  These new images are not timed. The 25 fps crowd target remains open.

## Verification

- Player suite: 11 tests, one private skip, zero failures.
- Public HUD/GFx suite with the rebuilt eight-patch Ruffle library: 16 tests,
  two explicit private/dependency skips, zero failures.
- Stress/Metal/clock suite: 16 tests, zero skips or failures.
- Original-directory negative control caught by the real synthetic player-loader
  test: 0/6 effects loaded; corrected loader 6/6, one focused test passes.
- Controlled Lorencia image checks: +11 batched/immediate agree before and after;
  +0 control unchanged across builds. Six PNG digests are in the finding.
- Each final capture admits 80/80 players and name records; all equipped model,
  base and glow textures are complete. Five skill events, 416 effects and 16
  joints reported per 101-frame scene; two GFx frames saved. Both final JPEGs
  reviewed for privacy and visual quality. Images 01-25 retain their hashes.

## Final lock-held gate

Acquired the merge lock at 09:08 CDT on 2026-10-28 after SESSION-SKILL-001 released
it. Integrated origin/main 9a827a4 as merge commit 8ada310, preserving both lanes'
shared-document entries. This includes RENDER-ITEMS-002 part 6 and SESSION-SKILL-001.

`bash scripts/local-macos-ci.sh` passes: 1,507 tests across 38 discovery runs,
173 explicit private/optional skips, zero failures. Eight fixture scenarios pass
all 61 expectations with 67 inbound frames and zero unbound/undecodable frames.
The existing two unrecovered intents and six unsent frames remain reported.
Native viewer and read-only reader build checks pass. Audit: 1,420 files, zero
rejections. No hosted workflow was dispatched. The untracked Python/evidence
symlinks supplied existing inputs; no tracked source was dirty during the gate.

The two final images were then regenerated and privacy-reviewed with the integrated
binary, and their publication pins/digests refreshed. All 80 players, complete base
and glow textures, five skill events, 416 effects and 16 joints still pass in each
scene. This post-gate update changes only media pins and documentation; runtime
sources are identical to the passing gate. The controlled before/after hash probes
in the finding use the earlier b74de71 integration base and isolate this loader fix.

## Cleanup

After merge, release the merge lock, remove all lane renders/scratch, the consumed
`renders/readme-candidates/stress80/` input, local native/Rust outputs, the lane's
private Ruffle dependency worktree, native task worktree and local branch. No new
local input needs retention. The committed capture script and hashes preserve
reproduction and evidence. Fast-forward the main checkout only if clean on main.
