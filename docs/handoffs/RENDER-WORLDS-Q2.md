# RENDER-WORLDS-Q2

The world leftovers of Q, R, R2 and AFTER2: Ferea's visual, the draw-first class slot 0x10 (Twisted Karutan's
range −800 writer), the Kanturu Underground blend light, the Ferea/Swamp handler writers and Acheron's sprites.
[Finding, addresses, checks, fidelity and limits](../research/client-worlds-q2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-q2`, branch `claude/render-worlds-q2`, from
  origin/main `9b821b19` with `claude/render-worlds-after2` merged (`f9e8ed71`), then origin/main `79a6b470`
  (#269 G3, #270 AFTER2; clean). Input links `tools/python` and `evidence` from the main checkout, never committed.
- **1. Ferea visual `0x00de6405` (verified, complete):** bounded (23 types). `reconstructed/objects/ferea.c`,
  named bones through the new `mu_q_inputs.bone_index`; world 112 is now a primary-visual world in the runtime.
- **2. Kanturu Underground type 0xa (verified, no C change):** the move slot is right; live WorldTime 2,189,675 gives
  0.1 exactly. The difference was the tour clock: new opt-in `"live_time"` in `scripts/fidelity_tour.py`.
- **3. Twisted Karutan range −800 (verified):** class slot 0x10 `0x00e67005`, reached from the draw-first predicate
  `0x017fcd18` through `0x00ea2788`. All twelve slot-0x10 overrides (worlds 134..145) are in
  `reconstructed/objects/world_first_visual.c` and feed the native `render_first`.
- **4. Ferea door states / Swamp variant (static):** both are written only by server messages (`0x0128b204` →
  `0x00dee27b`; class message `0x00e5ea8f` → `0x00e5eef9`); offline the constructor values are correct. Not ported.
- **5. Acheron sprites (measured):** not occluded and not too small (depth-off, ×20 and draw-all probes leave the
  frames identical); the quads reach the shared sprite pass but no pixels. Next: the RENDER-EFFECTS sprite draw path.
- **6.** Not done: custom/after slots of 133, 144, 141, 143, 145.
- Shared lines: `mu_objects_runtime.c` (render_first for 134..145 with the frustum in its context, `visual_bone_index`,
  112 in the primary-visual list), `worlds_q.h` (`bone_index` field, Ferea declarations), `worlds_q.c` (one dispatch
  line), `world_visual.h` (two declarations), `fidelity_tour.py` (`live_time`), `validate_worlds_q.py` (the
  trailing `Inputs` field), one validator row, coverage inventory (Ferea visual verified: 109/144).

## Checks

- `validate_worlds_q2`: 3 families, **4,000 cases equal, 0 mismatches/stops, 50/50 compiled mutants**. Registered.
- Portable `reconstructed/objects/test_worlds_q2.py` (3 + 1 private), new Ferea cases in `test_worlds_q.py`, production
  host `native/tests/worlds_q_host.c` (Ferea primary visual).
- Fidelity (32 DATA-ACQ-002 captures, base `f9e8ed71` vs lane): 25 byte-identical; Ferea 2.348 → 2.250; Twisted
  Karutan range 3,868 → 0 (image 7.145 → 7.145); Swamp of Destruction 12.415 → 12.395; 135/136/138/143 more first-pass
  draws, images equal. Live clock: Kanturu Underground 6.362 → 5.043 with blend light equal to live.

## PR-ready gate

On the merge of origin/main `79a6b470`, after `make -C native clean`: `nice -n 10 bash scripts/local-macos-ci.sh`
passes: **38 suites, 1,780 tests, 1,545 passed, 235 skipped, 0 failures/errors; fixtures, native viewer, live readers;
audit 1,768 files, 0 rejected**. Private (`run_validators.py --private --jobs 2`, `MU_RECOVERY_INTEGRATION=1`,
`MU_GAME_ROOT` = the installed client): **7 pass, 0 fail** (`validate_worlds_q2`, `validate_worlds_q`,
`validate_worlds_after2`, `validate_worlds_after`, `validate_worlds_r2`, `validate_object_render`,
`validate_world_light_name`). Only docs changed after the gate.

No original client or launcher was started; the DATA-ACQ-002 inputs were only read. Renders were summarised and
deleted; the scratch folder and the base worktree `worktrees/render-worlds-q2-base` are removed at handoff. No new
local input needs retention.
