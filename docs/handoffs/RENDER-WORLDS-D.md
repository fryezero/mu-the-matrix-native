# RENDER-WORLDS-D

Implemented six nested warp effect kinds, their lifecycle and render selection, and Noria's code-created
portal placement. [Full evidence, ranked gaps and scoreboard](../research/client-world-fidelity.md#6-render-worlds-d-2026-10-27).

- Four instruction families: 2,400 equal, zero mismatches or stopped cases; 8/8 compiled mutants detected.
- Existing effect create/move: 1,200 equal, zero mismatches.
- Validator manifest runner: 1 pass, no failures/errors/skips, with counts and mutants enforced.
- Synthetic native sessions for worlds 2/3/57/58: 3/5/3/6 effects created, live and drawn, no unsupported kinds;
  repeat runs equal. Placement/deduplication regression includes Noria.
- Fourteen-map-view tour at 25 steps: Noria missing 1 to 0, all other missing/extra counts stay zero;
  primary light exact everywhere; every frame-light score unchanged; thirteen final PNG hashes unchanged.
  Noria's changed hash follows new particle RNG consumption at its arrival camera. No live-image improvement
  is claimed. The retained Dungeon/Icarus/Kanturu image errors stay 2.019/62.030/3.717.
- Native GL portal views inspected for Devias, Noria and Raklion, with 3/5/3 effect models drawn.

Local Mac gate passed on the combined tree through main #185: 1,395 tests across 38 suites, 166 explicit skips,
zero failures; both fixture scenarios pass; viewer/readers build; repository audit accepts 1,255 files and rejects zero.
The B handler regression retains 4,000 equal comparisons and 10/10 compiled mutants. The existing object
regression passes 2,980 comparisons and 19/19 mutants.

Artifacts stay outside the repository:
- `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-d/`: validation, mutant, runner, gate and hash reports,
  manifests and logs.
- `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-d/`: before-main/after tour and portal GL renders.

Remaining: A's flames and after-character work; C2's remaining Icarus work; Elbeland boid mover/model draw is
unblocked by #181 but ranks below the measured placement/effect defects: the captured arrival view has zero
native boids and no live boid-pool snapshot or PNG to score it;
Raklion's inherited active event timer/effects/quake and authoritative timer inputs; Aida's concentrated transient
frame-light outlier; Tarkan/Raklion haze and fresh live-image comparisons in a separate authorized run.
The timer has no captured handler state to score, so the reproducible placement/effect gaps were selected first.

Self-review covered the diff against the brief and repository standards. No independent review is claimed.
No live client or launcher was started, stopped, driven or read; no wire/protection work, proprietary data,
render, capture or local input link is committed. Shared dispatch edits are limited to calls/model registration;
`native/world` has only the two render-frustum assignments.
