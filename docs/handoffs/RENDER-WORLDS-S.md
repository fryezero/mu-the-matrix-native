# RENDER-WORLDS-S

Aquila's Temple (145) and Debenter (95) primary create/move/visual methods, plus the return-false slots of Boss
Battle (139) and world 115's create/move. [Addresses, ranking, provenance and limits](../research/client-worlds-s.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-s`, branch `claude/render-worlds-s`, from
  origin/main `5a91b98d`; merged `742ef666` (#297 TEST-SPEED-001, #298 APP-POLISH-003) as `dd13e492`. Input links
  `tools/python`, `evidence`, `input` from the main checkout, never committed.
- Base coverage was **109/144 and 37/48**, not R2's 85/144: later lanes had closed most of R2's list. The 12 class
  rows still missing primary methods are ranked in the finding (Warps destination first, then field maps without a
  Warps row, then event/instance maps).
- New per-world C `reconstructed/objects/aquila.c`, `debenter.c`, `worlds_s_stubs.c`, `worlds_s.h`; one create and
  one move block in `object_render.c` (145/139/115); Debenter in the Q dispatch (`worlds_q.c`: `mu_worlds_q_owns`
  includes 95); in `native/core/mu_objects_runtime.c` the Aquila visual branch (bone 6 as `0x0129fd4f`), 145 in the
  primary-visual list, Debenter's bone bound in the Q visual and counted create/move refusals; build lines in both
  Makefiles; the validator row; coverage rows of the four classes.
- Coverage **+11 primary methods, +3 classes: 109 → 120/144 and 37 → 40/48**, zero static-only, 24 missing.
- `scripts/validate_worlds_s.py`: eleven families, **11,000 cases equal, zero mismatches/stops, 61/61 compiled
  mutants detected** (1–1,000 cases each). Registered as `validate_worlds_s`.
- Portable `reconstructed/objects/test_worlds_s.py` (5 tests + 1 private) and production host
  `native/tests/worlds_s_host.c` via `test_native_worlds_s.py`.
- Refused and counted, not approximated: Debenter create key 9 (model pose at creation, joints 0x7fd6 0x3c/0x3d),
  Debenter move 9/11 without an action record, Debenter visual bone types and Aquila bone-6 types without posed
  bones, Debenter's 0x199 word4 effect when no word4 hook is installed. No shared particle/effect/joint hook changed.
- Byte identity at the default draw, base `5a91b98d` vs lane: October 22 tour **28/28 PNG, 14/14 OBJECT, 14/14
  light**; DATA-ACQ-002 **64/64 frame PNG, 64/64 comparison PNG, 32/32 OBJECT, 32/32 light** identical.
- Smoke: headless arrivals at 145, 95 and 139 run without a crash and draw terrain and hero, with zero objects. The
  installed `EncTerrain*.obj` files are encrypted, and no live-read plaintext exists for these worlds. No fidelity
  claim.

Shared files touched minimally: `object_render.c` (two dispatch blocks), `worlds_q.c` (owner list, three dispatch
lines), `mu_objects_runtime.c` (one visual branch, the primary-visual list, two refusal counters, Debenter's bone
bound), both Makefiles, `validators.toml` (one row; the merge conflict with #297's row kept both sides), and four
neighbour assertions that had used 139/145 as "still unsupported" worlds or listed Q's owned worlds
(`test_worlds_o.py` now uses 114, `test_worlds_p2.py`/`test_worlds_r2.py` expect the generic range with status OK,
`test_worlds_q.py` lists 95).

No original client or launcher was started; no live read. No service, wire, protection-module, item or session
change. Only authored C/Python, synthetic fixtures and reviewed summaries are committed.

## Next: RENDER-WORLDS-S2

1. **Nars (110)**: create `0x00e260f0..0x00e26668` (with its table), move `0x00e26668..0x00e26ae7`, visual
   `0x00e26ae7..0x00e28bb2` (8.4 KB; 19 sprites, 16 particles, 11 TransformPosition, 4 effects, AngleMatrix/
   VectorRotate). Same Q-input pattern as Debenter.
2. **Arca War class (92/96/101/111)**: 172/87/430 bytes. It forwards to the base world's class (`this+0x1c`) and has
   its own type-0x59b case gated by `this+0x30` (a server state). Needs Nars first for 111, plus a handler-state input.
3. Then Imperial Guardian 69–72 (four near-identical classes, about 7 KB each), Event square 114, Test Area 121.

## Checks

Under the 2026-11-04 test budget: no lane gate. Code-final commit `96930986`; afterwards only docs changed.
`nice -n 10` throughout; load 1m 5–15 (other lanes active).

| Check | Result | Wall |
|---|---|---|
| `nice -n 10 make -j4` after the main merge | pass | 21.9 s |
| `validate_worlds_s --cases 1000 --mutations` (once, final C) | 11 families, 11,000 cases equal, 0 stops; 61/61 mutants detected | 236.2 s |
| First mutant attempt | stopped at mutant 16 (did not compile: unused parameter); replaced by a value mutant, rerun above | 57.9 s |
| `run_validators.py --private --no-mutants --cache --jobs 2 --only` 11 rows at `96930986` | 11 pass: worlds_s 11,000, object_render 1,984, worlds_q 11,000, worlds_q2 4,000, worlds_after4 9,181, worlds_o 9,000, worlds_p2 6,000, worlds_r2 9,000, charsel_world 1,200, login_world 1,200, audio_callers 5,528 cases | 50.9 s |
| `run_test_suites.py reconstructed/objects` | 147 tests, 120 passed, 27 skipped, 0 failures (first run: 4 neighbour-world failures, fixed) | 1.8 s |
| `test_native_worlds_*` (19 modules) + `test_render_worlds_a` | 30 tests, OK (5 skipped) | 38.5 s |
| `run_test_suites.py tests` | 223 tests, 181 passed, 42 skipped, 0 failures | 16.6 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.6 s |
| `scripts/audit_repository.py` | 1,892 files, 0 rejected (final, with docs) | 16.2 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; 120/144, 40/48 | < 1 s |
| Byte identity "before" (base binary, once) | Oct 22 tour 31.2 s; DATA-ACQ-002 69.0 s | 100.2 s |
| Byte identity "after" (lane binary) | identical (above) | 106.0 s |
| Smoke arrivals 145/95/139 | rc 0, 2 frames each, 0 objects | 0.8 s each |

Validator rows were chosen per brief 6b, not by the selector. `run_validators.py --list-affected origin/main`
selects 69 rows, because every row builds the shared `reconstructed/objects` or `native` library. These 11 rows
cover code paths this diff changes:
- my row;
- the callers of `mu_obj_create`/`mu_obj_move` (object_render, charsel_world, login_world, audio_callers);
- the Q dispatch (worlds_q, worlds_q2);
- the only objects + native row (worlds_after4);
- the rows whose owning test files changed (worlds_o, worlds_p2, worlds_r2).

Steward validators: validate_worlds_s, validate_object_render, validate_worlds_q, validate_worlds_q2,
validate_worlds_after4, validate_worlds_o, validate_worlds_p2, validate_worlds_r2, validate_charsel_world,
validate_login_world, validate_audio_callers (ran at `96930986`; no mutants needed). Env: `MU_RECOVERY_INTEGRATION=1`,
`MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_EVIDENCE_DIR=~/Documents/MTM/mu-the-matrix-native/evidence`,
`MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`.

During the lane, reports and renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-s` and
`renders/render-worlds-s`, plus a base worktree `worktrees/render-worlds-s-base`. All are deleted. The DATA-ACQ-002,
fidelity2 and lang inputs were only read. No new local input needs retention.
