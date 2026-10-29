# RENDER-WORLDS-R2

Twisted Karutan (142), Kardamahal (143) and Swamp of Destruction (144) primary create/move/visual methods.
[Addresses, provenance, fidelity numbers and limits](../research/client-worlds-r2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-r2`, branch `claude/render-worlds-r2`,
  from origin/main `88a4517`, fast-forwarded to `5fa43cd` (BUILD-DEPS-001) before any edit. Input links
  `tools/python` and `evidence` from the main checkout, never committed.
- New per-world C `reconstructed/objects/twisted_karutan.c`, `kardamahal.c`, `swamp_destruction.c`, `worlds_r2.h`;
  one create and one move block in `object_render.c`; in `native/core/mu_objects_runtime.c` the post-tick
  Kardamahal named-bone light, one visual branch (flicker rand, bone gate, effect/joint refusals) and the
  primary-visual world list; build lines in both Makefiles; the validator registry entry; coverage rows of these
  three classes.
- Coverage **+9 primary methods, +3 classes**: 76 → 85/144 and 26 → 29/48, zero static-only, 59 missing. All nine
  methods complete (the largest, the Swamp visual, is a 34-entry jump table of seventeen joint cases).
- `scripts/validate_worlds_r2.py`: nine families, **9,000 cases equal, zero mismatches/stops, 56/56 compiled
  mutants detected** (3–786 cases each). Registered as `validate_worlds_r2`.
- Portable `reconstructed/objects/test_worlds_r2.py` (4 tests + 1 private) and production host
  `native/tests/worlds_r2_host.c` via `test_native_worlds_r2.py` (three worlds, 200 steps plus visual pass each).
- Saved-population regression at the three DATA-ACQ-002 arrival tiles: 8,476 static field differences → 0
  (all after-character of 142/143/144, all range of 143/144); near-hero frame light 142 0.0058 → 0.0000, 143
  0.0012 → 0.0001, 144 0.0316 → 0.0088; image mean |Δ| 142 13.480 → 13.480, 143 10.912 → 10.911, 144
  12.755 → 12.376; primary light exact; zero missing/extra.
- Base vs lane: October 22 fourteen-view tour **28/28 PNG, 14/14 OBJECT, 14/14 light identical**; the other 29
  DATA-ACQ-002 captures **58/58 PNG, 29/29 OBJECT, 29/29 light identical**.
- Refused and counted: the three CreateEffect requests with info word4 (0x199 from 142 type 196 and 144 type 185,
  0x195 from 143 type 161); Kardamahal 115 without a posed model; Twisted Karutan 72 without twelve posed bones.

No original client or launcher was started; no live read was needed. No service, wire, protection-module,
shared particle/effect/joint hook, item or session change. Only authored C/Python, synthetic fixtures and
reviewed summaries are committed.

Found on main (not changed here, other lanes' files): since BUILD-DEPS-001 the `reconstructed/objects` Makefile
includes `../deps.mk`, but the mutant copies of `validate_worlds_{g,h,n,o,p,p2}.py` copy only the source
directories, so their `--mutations` runs stop at `make: No rule to make target '../deps.mk'` (verified for P2:
`run_validators.py --private --only validate_worlds_p2` failed). `validate_worlds_r2.py` copies `deps.mk`;
RENDER-WORLDS-G2 (`eb4b53a`) made the include optional and P2 passes again on the merged tree.

Remaining: the CreateEffect kinds 0x195/0x199 with word4; the 142 range −800 writer and the 142–144 velocity
differences (not in these slots); the custom/after/invisible-move slots of the three classes; the default hook
chain around the class slots; the client's BodyOrigin phase for Kardamahal 115; 59 other primary methods.

During the lane, reports and renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-r2`
and `renders/render-worlds-r2`, plus a base build worktree `worktrees/render-worlds-r2-base`; all are deleted
after merge with the worktree and branch. The DATA-ACQ-002 inputs were only read. No new local input needs
retention.

## Checks

Merge process of the 20:50 brief update (merge steward; no lock). Latest main `eb4b53a` (RENDER-WORLDS-G2) merged
as `b641395`; conflicts in both Makefiles (G2's `texture_lookup.c` plus this lane's sources) and the plan rows keep
both sides. `native/build` rebuilt from clean (G2 changed `mu_objects.h`). On the merged tree, at `nice -n 10`:

- `bash scripts/local-macos-ci.sh` passes: **1,704 tests across 38 discovery runs, 220 explicit skips, zero
  failures/errors; 11/11 fixture scenarios; native viewer and reader builds; publication audit 1,683 files, zero
  rejected**. No hosted workflow dispatched. (Preflight before the merge: 1,699 tests, 219 skips, 1,672 files.)
- `MU_RECOVERY_INTEGRATION=1 run_validators.py --private --jobs 2 --only validate_worlds_r2,validate_object_render,
  validate_worlds_p2`: **3/3 pass** (R2: 9,000 cases, 56/56 mutants).
- `world_handler_coverage.py`: 48 classes, 57 registrations, 288 addresses; 85/144, 29/48.
- Fidelity tours (before `5fa43cd`, after this lane before the G2 merge) as in the finding.

Steward validators: validate_worlds_r2 (MU_RECOVERY_INTEGRATION=1).
