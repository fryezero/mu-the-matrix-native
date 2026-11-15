# RENDER-WORLDS-PICK-001

Branch `claude/render-worlds-pick-001`, from main `c5b9d5ca` (#400, batch 118; #399 INNER-005 merged). Claude
Fable 5.2 lane, no subagents. Worktree `~/Documents/MTM/worktrees/render-worlds-pick-001`. Merge belongs to the
steward.

## WIP (checkpoint 1)

**Done**
- Step 1 code: `reconstructed/objects/object_pick.{c,h}` (the box write of `0x012b5bde` as RenderObject's setup
  calls it, the mode-2 vertex bounds, the exported segment test), runtime binding in
  `native/core/mu_objects_runtime.c` (box written where the setup reaches its Transform call, also in the
  after-character prepare), mouse segment through `rt.mouse_start` / `rt.mouse_end`
  (`native/world/parts/objects.c`, `mu_objects_anim.c`).
- `scripts/validate_worlds_pick.py` (families box / segment / pick), registry row `validate_worlds_pick`,
  `reconstructed/objects/test_worlds_pick.py`, `native/tests/pick_host.c` + `test_native_worlds_pick.py`.
  Small-sample runs: 400 cases per family equal, 0 stops; portable tests and the host pass.
- Base numbers taken once: base `mu-world` SHA-256
  `0b67fc1e9ec614d2c318fb51d31f1205c7f8d5fd4921aa34834b969a23519c8a` (main `c5b9d5ca`), 46-view default sweep
  ledger in `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-pick-001/before-ledger.json`.

**Left**
- Mutants once (23), full case counts; research doc `docs/research/client-worlds-pick.md`.
- Step 2: the all-world inner-object census (CSV + summary).
- Step 3 if time remains; then checks, after sweep, status lines, PR.

**Next step**
- Write the census extractor in `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-pick-001/`.
