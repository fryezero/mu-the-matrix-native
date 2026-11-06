# RENDER-WORLDS-S2

Nars (110) and the Arca War class (92, 96, 101, 111) primary create/move/visual methods.
[Addresses, provenance, forwarding and limits](../research/client-worlds-s2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-s2`, branch `claude/render-worlds-s2`,
  from `origin/claude/render-worlds-s` (`ca46f0ab`) while #301 was open; merged origin/main `83a21893` (#301
  RENDER-WORLDS-S) as `5e9226cb`. Input links `tools/python`, `evidence`, `input` from the main checkout, never
  committed.
- New per-world C `reconstructed/objects/nars.c`, `arca.c`, `worlds_s2.h`. Nars runs on the RENDER-WORLDS-Q inputs
  like Debenter. The Arca class forwards to its base world's class through a callback (`mu_arca_forward_fn`): Q
  dispatch for 92/96/111 (`worlds_q.c`), one create and one move block in `object_render.c` for 101 (Uruk), one
  visual branch in `mu_objects_runtime.c` for 101. The base world is client state (`0x00d7b225`: world − 1 for a
  listed world); the class's stage `+0x30` is server state and stays an input (`mu_q_handler.arca_stage`, default
  0 as the constructor).
- Coverage **+6 primary methods, +2 classes: 120 → 126/144 and 40 → 42/48**, zero static-only, 18 missing.
- `scripts/validate_worlds_s2.py`: ten families (Nars create, move and four visual type families; Arca base world,
  create, move, visual), **10,000 cases equal, zero mismatches/stops, 72/72 compiled mutants detected** (1–1,000
  cases each). Registered as `validate_worlds_s2`.
- Portable `reconstructed/objects/test_worlds_s2.py` (4 tests + 1 private) and production host
  `native/tests/worlds_s2_host.c` via `test_native_worlds_s2.py`.
- Refused and counted, not approximated: Nars create type 134 (model pose at creation), Nars visual bone types
  without posed bones, Arca 0x59b without a posed model (always natively: the type is above the 512-type model
  table) and a stage outside 0..5. No shared particle/effect/joint hook changed; effects use the existing word4 and
  scaled CreateEffect consumers.
- Byte identity at the default draw, base `83a21893` vs lane: October 22 tour **28/28 PNG, 14/14 OBJECT, 14/14
  light**; DATA-ACQ-002 **64/64 frame PNG, 32/32 OBJECT, 32/32 light** identical.
- Smoke: headless arrival at 110 runs without a crash and draws terrain and hero, with zero objects (no live-read
  plaintext for Nars). World 111's terrain (`World112`) is not installed. No fidelity claim.

Shared files touched minimally: `worlds_q.c` (ownership, Arca forwarding, Nars dispatch, the bone-bound helper),
`worlds_q.h` (one appended handler field, one declaration), `object_render.c` (one forwarding helper, two blocks
for 101), `mu_objects_runtime.c` (101's visual branch and forwarder, 101 in the primary-visual list, the Q bone
bound now from `mu_worlds_q_visual_bones`), both Makefiles, `validators.toml` (one row), the coverage JSON/MD. Four
neighbour tests that used 111 or 101 as "worlds without methods" or listed Q's owned worlds now use 114 or the
new list: `worlds_n_host.c`, `worlds_q_host.c` (+ its module docstring), `worlds_i_host.c`, `test_worlds_q.py`,
`test_worlds_s.py`.

No original client or launcher was started; no live read. No service, wire, protection-module, item or session
change. Only authored C/Python, synthetic fixtures and reviewed summaries are committed.

## Next

Ranks 5, 6 and 8 of RENDER-WORLDS-S's list, surveyed statically in the finding: Imperial Guardian 69–72 (four
near-identical ~7 KB visuals with CreateJoint on the existing consumer; the move runs its own alpha step and tick;
handler `+0x14` is server state), class 114 (move poses the model and lights at bone points; create registers the
object) and Test Area 121 (three CreateEffect at creation).

## Checks

Under the 2026-11-04 test budget: no lane gate. Code final at `6e7f2958` (after the `83a21893` merge); afterwards
only docs changed. `nice -n 10` throughout; load 1m 6–12 (other lanes active).

| Check | Result | Wall |
|---|---|---|
| `nice -n 10 make -j4` (native, fresh worktree) | pass | 15.0 s (final rerun: no-op) |
| `validate_worlds_s2 --cases 200` while iterating | 2,000 cases equal (after one harness signedness fix) | 1–4 s |
| `validate_worlds_s2 --cases 1000 --mutations` (once, final C) | 10 families, 10,000 cases equal, 0 stops; 72/72 mutants detected | 277 s |
| First mutant attempt | stopped at mutant 3 (duplicate case label, did not compile); replaced, rerun above | 17 s |
| `run_validators.py --private --no-mutants --cache --jobs 2 --only` 10 rows at `6e7f2958` | 10 pass: worlds_s2 10,000, object_render 1,984, worlds_q 11,000, worlds_q2 4,000, worlds_s 11,000, worlds_i 6,000, worlds_after4 9,181, charsel_world 1,200, login_world 1,200, audio_callers 5,528 cases | 43 s |
| `run_test_suites.py --affected origin/main` (`MU_GATE_JOBS=2`) | 7 suites, 1,369 tests, 1,159 passed, 209 skipped, 0 failures, 1 error: `test_joints` needs `reconstructed/combat/libcombat.dylib`, which no selected suite builds in a fresh worktree | 313 s |
| `make -C reconstructed/combat`, then `run_test_suites.py reconstructed/joints` | 15 tests, 14 passed, 1 skipped | 0.1 s |
| `test_native_world*` + `test_render_worlds*` (23 modules; after the 101 sibling fix) | 53 tests OK (7 skipped); first run: `worlds_i_host` used 101 as a world without methods, fixed | 36.5 s |
| `run_test_suites.py reconstructed/objects` | 152 tests, 124 passed, 28 skipped, 0 failures | 3.0 s |
| `test_worlds_s2` + `test_native_worlds_s2` | 6 tests OK (1 private skipped) | 0.3 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.6 s |
| `scripts/audit_repository.py` | 1,911 files, 0 rejected (final, with docs) | 28 s |
| Docs readers (6c): `test_world_captures_2`, `test_repository_policy`, `test_native_item_textures`, `test_native_data_manifest` | 32 tests OK (1 skipped) | 8.4 s |
| `world_handler_coverage.py --write-markdown` | 48 classes, 57 registrations, 288 addresses; 126/144, 42/48 | < 1 s |
| Byte identity "before" (base binary, once) | Oct 22 tour 17 s; DATA-ACQ-002 53 s | 70 s |
| Byte identity "after" (lane binary) | identical (above) | 63 s |
| Smoke arrival 110 / 111 | rc 0, 2 frames, 0 objects / terrain not installed (rc 1, before object code) | 1.7 s / 0.01 s |

Validator rows were chosen per brief 6b, not by the selector: `--list-affected origin/main` selects 69 rows
because every row builds the shared `reconstructed/objects` or `native` library, and `run_test_suites.py
--list-affected` 129 items. These 10 rows cover code paths this diff changes:
- my row;
- the callers of `mu_obj_create`/`mu_obj_move` (object_render, charsel_world, login_world, audio_callers);
- the Q dispatch and handler struct (worlds_q, worlds_q2);
- the rows whose test files changed (worlds_q, worlds_s);
- Uruk Mountain, now also reached through 101 (worlds_i);
- the only objects + native row (worlds_after4).

Steward validators: validate_worlds_s2, validate_object_render, validate_worlds_q, validate_worlds_q2,
validate_worlds_s, validate_worlds_i, validate_worlds_after4, validate_charsel_world, validate_login_world,
validate_audio_callers (ran at `6e7f2958`; no mutants needed). Env: `MU_RECOVERY_INTEGRATION=1`,
`MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_EVIDENCE_DIR=~/Documents/MTM/mu-the-matrix-native/evidence`,
`MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`.

During the lane, reports and renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-s2` and
`renders/render-worlds-s2`, plus a base worktree `worktrees/render-worlds-s2-base`. All are deleted. The
DATA-ACQ-002, fidelity2 and objects inputs were only read. No new local input needs retention.
