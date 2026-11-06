# RENDER-WORLDS-S3

Imperial Guardian (worlds 69, 70, 71, 72), Event square (114) and Test Area (121) primary create/move/visual
methods. [Addresses, shared code, provenance and limits](../research/client-worlds-s3.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-s3`, branch `claude/render-worlds-s3`, from
  origin/main `83a21893` (#301 RENDER-WORLDS-S); merged `7403244e` (#302 RENDER-WORLDS-S2) as `317156ff` and `7d7d694b` (#295 RENDER-ITEMS-HIDDENMESH, item rendering
  only) as `25ecc012`. Input links
  `tools/python`, `evidence`, `input` from the main checkout, never committed.
- The four Imperial Guardian classes are one source compiled four times (create 69 = 70 = 71, 72 adds type 10; move
  differs by the class static, class 70's missing `break`, class 71's 0.44 and class 72's countdown; visual 69 = 70 =
  71, 72 drops 51 and adds 157/158; class 72's predicate accepts 72..74). Event square's slots are Loren Market's
  behind world 114. One `imperial_guardian.c` with a class argument; `loren_market.c` split into a world-free core
  with per-world wrappers; `test_area.c`; `worlds_s3.h`.
- Coverage **+18 primary methods, +6 classes: 120 → 138/144 and 40 → 46/48** on the base; with S2 merged the
  inventory reads **144/144 and 48/48** (0 static-only, 0 missing).
- `scripts/validate_worlds_s3.py`: 22 families (the two big visuals as bone/frame/emitter families),
  **22,000 cases equal, zero mismatches/stops, 75/75 compiled mutants detected** (3–789 cases each). Registered as
  `validate_worlds_s3`.
- Portable `reconstructed/objects/test_worlds_s3.py` (6 tests + 1 private) and production host
  `native/tests/worlds_s3_host.c` via `test_native_worlds_s3.py`.
- Shared files touched minimally: `object_render.c` (one create and one move block for 114/121, one include),
  `mu_objects_runtime.c` (Imperial Guardian create/move in the class pass, three visual branches, the primary-visual
  list, 121 in the startup-effect worlds, one include), `mu_objects.h` (`imperial_frame`), both Makefiles,
  `validators.toml` (one row), `loren_market.c` (split; every string `validate_worlds_i`'s mutants target kept), and
  five neighbour tests that used 114 or 121 as worlds without methods (`test_worlds_o.py`, `worlds_o_host.c`, and
  S2's `worlds_i_host.c`, `worlds_n_host.c`, `worlds_q_host.c`) now use 73, which has no factory class.
- Refused and counted, not approximated: the 0x7fd5 subtype-5 joints (types 20/51; no native joint kind), Imperial
  Guardian bone types without enough posed bones, the 0x7f42 word4 effects without a word4 hook (existing
  owned-effect consumer). No shared particle/effect/joint hook changed. Types 82/158 read an uninitialized stack
  light: zero (inference).
- No live capture exists; the installed object files of these worlds are encrypted. Headless arrivals in all six
  worlds draw terrain and hero with zero objects. Byte identity against base `83a21893`: October 22 tour and all 32
  DATA-ACQ-002 captures identical. No fidelity claim beyond the instruction comparison.

No original client or launcher was started; no live read. No service, wire, protection-module, item or session
change, and no server/event state: the slots read only object fields, the world, WorldTime, rand and the class
static. Only authored C/Python, synthetic fixtures and reviewed summaries are committed.

## Left

- The custom-render, after-render and invisible-move slots of the six classes (addresses in the finding).
- The default hook chain around the class slots in MoveObject and RenderObjectVisual (addresses in the finding).
- Native kinds for joint 0x7fd5 subtype 5 and the 0x7f42 word4 effect (RENDER-EFFECTS).
- Loren Market's (79) native visual branch draws no outer flicker rand, unlike `0x017f9758` and the other
  primary-visual worlds; unchanged here (captured world) and worth a check.
- Live population, RNG phase and image fidelity of 69..72, 114 and 121 (event instances; no capture).

## Checks

Under the 2026-11-04 test budget: no lane gate. `nice -n 10`, `make -j4`, `--jobs 2`; load 1m 6–18 (three other
lanes and the steward active; heavy steps waited for load ≤ 14 where noted).

| Check | Result | Wall |
|---|---|---|
| `nice -n 10 make -j4` after the main merges | pass | 14.0 s (`317156ff`), 11.6 s (`25ecc012`) |
| `run_test_suites.py --affected origin/main` (lane code, before the merge) | 7 suites, 1,370 tests, 1,161 passed, 209 skipped, 0 failures | 286.5 s |
| Same after the merge (`317156ff`) | 7 suites, 1,376 tests, 1,166 passed, 210 skipped, 0 failures | 247.5 s |
| Edited host modules after the merge (`test_native_worlds_{i,n,q,o,s2,s3}`) | 10 tests OK (2 skipped) | 2.4 s |
| `validate_worlds_s3 --cases 1000 --mutations` (once, via `run_validators.py --cache`, at `4db7a4a6`) | 22 families, 22,000 cases equal, 0 stops; 75/75 mutants detected | 324.3 s |
| Earlier mutant attempts | (1) stopped at mutant 3, which did not compile (unused parameter); replaced, then all 75 compile-checked with `-fsyntax-only` first: 35.5 s. (2) 22,000 equal but 3 mutants undetected (lock bound 11, alpha `>=`, clock phase 2); samples directed, subset rechecked, full run (above) repeated once: 362.9 s | 398.4 s |
| `run_validators.py --private --no-mutants --cache --jobs 2`, 7 rows at `bf40c3ab` | 7 pass | 26.6 s |
| Same, 8 rows at `317156ff` (final code) | 8 pass: worlds_s3 22,000, worlds_i 6,000, worlds_o 9,000, object_render 1,984, charsel_world 1,200, login_world 1,200, audio_callers 5,528, worlds_after4 9,181 cases | 22.9 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.7 s |
| `scripts/audit_repository.py` | 1,920 files, 0 rejected (final, with docs) | 16.7 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; 138/144 and 46/48 before the merge, 144/144 and 48/48 after | < 1 s |
| Byte identity "before" (base `83a21893` binary, once) | Oct 22 tour 27.9 s; DATA-ACQ-002 57.8 s | 85.7 s |
| Byte identity "after" (`317156ff` binary; again at the final `25ecc012`: identical, 80.1 s) | Oct 22 **28/28 PNG, 14/14 OBJECT, 14/14 light**; DATA-ACQ-002 **64/64 frame PNG, 64/64 comparison PNG, 32/32 OBJECT, 32/32 light** identical (also identical at `4db7a4a6`, 81.7 s) | 76.9 s |
| Smoke arrivals 69 (150,30), 70 (30,70), 71 (110,190), 72 (30,70), 114 (30,30), 121 (110,30) | rc 0, 2 frames each, terrain and hero, 0 objects | 0.8–1.1 s each |

Validator rows were chosen per brief 6b, not by the selector (`--list-affected` selects most rows because they build
the shared `reconstructed/objects` or `native` library). These rows cover code paths this diff changes:
- my row;
- `validate_worlds_i` (Loren Market's bodies were split into the shared core);
- the callers of `mu_obj_create`/`mu_obj_move` (object_render, charsel_world, login_world, audio_callers);
- the only objects + native row (worlds_after4);
- `validate_worlds_o`, whose owning test file changed.

Steward validators: validate_worlds_s3, validate_worlds_i, validate_worlds_o, validate_object_render,
validate_charsel_world, validate_login_world, validate_audio_callers, validate_worlds_after4 (ran at `317156ff`; the
last merge `25ecc012` (#295) changed none of their compiled inputs. No mutants needed: validate_worlds_s3's 75/75
ran once at `4db7a4a6` and no merge changed its targets). Env:
`MU_RECOVERY_INTEGRATION=1`, `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_EVIDENCE_DIR=~/Documents/MTM/mu-the-matrix-native/evidence`,
`MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`.

During the lane, reports and renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-s3` and
`renders/render-worlds-s3`, plus a base worktree `worktrees/render-worlds-s3-base` for the "before" tour. All are
deleted. The DATA-ACQ-002, fidelity2 and lang inputs were only read. No new local input needs retention.
