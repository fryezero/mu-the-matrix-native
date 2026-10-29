# RENDER-WORLDS-P

Old Kethotum (135), Burning Kethotum (136) and Bloody Tarkan (140): all nine primary methods (create +2c,
move +30, visual +34). [Finding, addresses, boundaries and fidelity](../research/client-worlds-p.md).

- Branch `claude/render-worlds-p`, worktree `~/Documents/MTM/worktrees/render-worlds-p`, from origin/main
  `f5a3199`, merged with `3735625` (RENDER-WORLDS-N, RENDER-EFFECTS-004). Input links never staged.
- Owned: `reconstructed/objects/{old_kethotum,burning_kethotum,bloody_tarkan}.c`, `worlds_p{,_internal}.h`,
  `test_worlds_p.py`, `scripts/validate_worlds_p.py`, `native/core/mu_objects_worlds_p.{c,h}`,
  `native/tests/{worlds_p_host.c,test_native_worlds_p.py}`. Minimal shared hooks: one create and one move dispatch
  in `object_render.c`; in `mu_objects_runtime.c` the deferred create/move, the PlaySpeed lookup, the clamped-light
  event and apply, one visual branch and the primary-visual/pose world lists; in `mu_objects.h` a 16-action speed
  table per type and the `MU_OBJECT_LIGHT_CLAMPED` range flag; Makefile/registry lines; coverage rows of these classes.
- Coverage **52 → 61/144 primary methods, 18 → 21/48 classes**, zero static-only, 83 missing.
- Ten instruction families (nine methods plus the clamped AddTerrainLight `0x016caeae`), 1,000 cases each:
  **10,000 equal, zero mismatches/stops; 51/51 compiled mutants detected, zero stops** (several by only one case:
  directed boundary samples). One planted change was equivalent (double 1.35 vs float 1.35f) and was replaced.
- The 136 type-0xb5 `.ein` effects (C++ effect manager) are compared as requests at the manager boundary; the
  native host has no `.ein` system and counts each refusal. 135/136 create and move are deferred to the objects host
  so the move runs after the tick with the model action table (original order); see the finding.
- Native host: create speeds/rest counts, rest→swing and gate open/close cycles with sounds after real ticks,
  `.ein` refusal, brazier/clamped lights, five 200-preparation visual runs, model-gate RNG stability, missing-bone
  refusal and sibling-world dispatch. Portable: deferral, one generic tick, log-capacity independence.
- Fidelity at the DATA-ACQ-002 arrival tiles (before = clean main `3735625`): static-field differences
  135 399 → 0, 136 303 → 0, 140 30 → 2 (type-67 velocity, not these methods); missing/extra 0/0; image mean |Δ|
  unchanged (2.388, 8.661, 5.225); light dumps identical (no emitter in moved sectors).

No original client or launcher was started. No particle/effect consumer (RENDER-EFFECTS-004 owns those hooks),
service, wire or protection work. Only authored source, synthetic fixtures and reviewed summaries are committed.

Remaining: the custom/after/invisible slots of these classes; a native `.ein` effect system for 136 type 0xb5;
model PlaySpeeds before create (loader); RNG/animation phase and particle pools in a capture; consumer lifecycles
of `0x7efa/2`, `0x7f26/14`, effect `0x59a/3` and the 136 brazier kinds (static audit only); a capture with an
emitter in view to score the 136/140 lights; the two Bloody Tarkan type-67 velocities (outside these methods).

Local outputs: `native/scratch/render-worlds-p` and `renders/render-worlds-p`, deleted after merge with the worktree.
No new local INPUT needs retention. The DATA-ACQ-002 inputs were only read.
