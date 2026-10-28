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

The full lock-held Mac gate and integration base are recorded after completion.
No hosted workflow is used.

## Cleanup

After merge, release the merge lock, remove all lane renders/scratch, the consumed
`renders/readme-candidates/stress80/` input, local native/Rust outputs, the lane's
private Ruffle dependency worktree, native task worktree and local branch. No new
local input needs retention. The committed capture script and hashes preserve
reproduction and evidence. Fast-forward the main checkout only if clean on main.
