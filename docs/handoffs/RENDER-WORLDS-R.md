# RENDER-WORLDS-R

Scorched Canyon (131), Red Smoke Icarus (132), Temple of Arnil (133) and Gray Aida (134): all twelve primary
methods (create +2c, move +30, visual +34). [Finding, addresses, boundaries and fidelity](../research/client-worlds-r.md).

- Branch `claude/render-worlds-r`, worktree `~/Documents/MTM/worktrees/render-worlds-r`, from origin/main `3d17cac`.
  Input links (`tools/python`, `evidence`) never staged.
- Owned: `reconstructed/objects/{scorched_canyon,red_smoke_icarus,temple_arnil,gray_aida}.c`, `worlds_r.h`,
  `test_worlds_r.py`, `scripts/validate_worlds_r.py`, `native/tests/{worlds_r_host.c,test_native_worlds_r.py}`.
  Minimal shared hooks: one create and one move branch in `object_render.c` (131 create deferred as `MU_WR_CREATE`);
  in `mu_objects_runtime.c` an RNG helper, the deferred-create loop, one visual branch (bone gates, outer flicker
  draw, refusal counting) and the primary-visual world list; Makefile/registry lines; coverage rows of these classes.
- Coverage **+12 primary methods, +4 classes**: 70/144 → 82/144 on `3d17cac`; with RENDER-WORLDS-P2 merged
  **88/144 primary methods, 30/48 classes**, zero static-only, 56 missing.
- Twelve instruction families, 1,000 cases each: **12,000 equal, zero mismatches/stops; 77/77 compiled mutants
  detected (lowest count 4), zero stops**. Boundary types and phase-window clocks were added after one mutant
  (Temple hidden range 0xa0..0xaa) went undetected; three equivalent or non-compiling plants were replaced.
- Tick order: no method reads the frame, action or action table, so only the RNG-using 131 create is deferred
  (static; see the finding).
- Refused and counted (`draw_unsupported`): the 134 visual RenderMesh with StreamMesh (types
  0x41/0x42/0x84/0x85/0x4d/0x4e) and the 134 `0x199` CreateEffect with its scale-derived eighth argument;
  bone cases without enough current bones.
- Fidelity at the DATA-ACQ-002 arrival tiles (before = clean main `3d17cac`): static-field differences
  131 4,374 → 0, 132 1,812 → 0, 133 6,475 → 0, 134 2,926 → 1 (a type-0x29 blend light written by the render pass);
  missing/extra unchanged (0/0, 1/1, 0/0, 0/0). Image mean |Δ|: 131 7.624 → **8.562** (worse: three objects
  beyond the far plane now pass the native frustum; static fields equal live), 132 26.344 → 26.373,
  133 1.028 → 1.028, 134 13.153 → 13.072. Light dumps identical. The 28 other views are byte-identical
  (56/56 PNG, 28/28 OBJECT, 28/28 light).

No original client or launcher was started. No particle/effect consumer, service, wire or protection work.
Only authored source, synthetic fixtures and reviewed summaries are committed.

Remaining: the custom/after/invisible slots of the four classes and the 131..134 after-character second pass;
native consumers for the 134 extra mesh and the `0x199` eighth argument; Scorched Canyon frustum/far-plane parity
for the three far objects (with G2); consumer lifecycles of the listed particles/effect (static audit only);
RNG/animation phase and particle pools in a capture.

Local outputs: `native/scratch/render-worlds-r` (including a temporary base worktree) and `renders/render-worlds-r`,
deleted after merge with the worktree. No new local INPUT needs retention. The DATA-ACQ-002 inputs were only read.
