# RENDER-WORLDS-P2

Kanturu Underground (137) and Ignis Volcano (138) primary create/move/visual methods.
[Addresses, provenance, fidelity numbers and limits](../research/client-worlds-p2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-p2`, branch `claude/render-worlds-p2`,
  from origin/main `35cab4a`. Input links `tools/python` and `evidence` from the main checkout, never committed.
- New per-world C `reconstructed/objects/kanturu_underground.c`, `ignis_volcano.c`, `worlds_p2.h`; dispatch lines
  in `object_render.c`; runtime lines in `native/core/mu_objects_runtime.c` (all-action PlaySpeed, StreamMesh
  refusal count, deferred Kanturu action step after the tick, world-137 visual with refused joint kinds); build
  lines in both Makefiles.
- Coverage **52 → 58/144 primary methods; 18 → 20/48 classes**; zero static-only, 86 missing. All six methods
  complete (none was large).
- `scripts/validate_worlds_p2.py`: six families, **6,000 cases equal, zero mismatches/stops, 35/35 compiled
  mutants detected**. Registered as `validate_worlds_p2`.
- Portable `reconstructed/objects/test_worlds_p2.py` (4 tests + 1 private) and production host
  `native/tests/worlds_p2_host.c` via `test_native_worlds_p2.py` (both worlds, 200 steps plus visual pass each).
- Saved-population regression at the two DATA-ACQ-002 arrival tiles: range 6,803 and Ignis after-character
  262 differences → 0; near-hero field differences 137: 141 → 42, 138: 39 → 0; primary light exact. Image mean
  |Δ|: 137 5.899 → 5.790, 138 4.139 → 4.139. Ignis near-hero frame light 0.0216 → 0.0239 (new lights, other phase).
- Base vs lane: October 22 fourteen-view tour **28/28 PNG, 14/14 OBJECT, 14/14 light identical**; the other 30
  DATA-ACQ-002 captures **60/60 PNG, 30/30 OBJECT, 30/30 light identical**.
- Refused and counted: Kanturu joints `0x7f7d` 12/14/15 and `0x7f7c` 0x12 (native joint pool lacks the kinds);
  Ignis StreamMesh `+0x94` (no consumer).

No original client or launcher was started; no live read was needed. No service, wire, protection-module,
shared particle/effect/joint hook, item or session change. Only authored C/Python, synthetic fixtures and
reviewed summaries are committed.

Remaining: the four joint kinds and a StreamMesh consumer; the custom/after-render slots of both classes
(Kanturu `0x00e092f4`/`0x00e0ab2a`, Ignis `0x00e05f25`/`0x00e0709e`), likely the source of Kanturu's remaining
20 after-character and 24 hidden-mesh differences; the default hook chain after false returns; the real
frame-time global; 86 other primary methods.

During the lane, reports and renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-p2`
and `renders/render-worlds-p2`, plus a base build worktree `worktrees/render-worlds-p2-base`; all are deleted
after merge with the worktree and branch. The DATA-ACQ-002 inputs were only read. No new local input needs
retention.

## Checks

Pending the locked gate.
