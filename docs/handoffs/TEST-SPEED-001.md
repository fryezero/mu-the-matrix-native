# TEST-SPEED-001

PR-ready, resumed from `96865d8c`, merged stopped main `90e11d71` main `9e93e6c9` (#292), then latest main `2531746f` (#293/#294).
The merge steward owns the merge. No live game or service was used; no validator expectations or C behavior changed.

## Delivered

- `run_validators.py`: no-mutant runs, affected rows, opt-in original-side cache, wall times and longest-first ordering.
- `run_test_suites.py` / `affected.py`: affected work items with reasons; explicit make targets avoid the default
  build; include closures, build-output-independent names, failed-dry-run and unknown-input fallbacks; brief-6c docs consumers.
- Item harness: only pinned original calls cached; C calls, table fitting, reset controls and comparisons stay live.
  Pin hashes including section3, Python/Unicorn versions, harness source closure and case inputs invalidate entries.
  Portable regressions prove changed pins/source invalidate entries and a changed C result still fails on a warm cache.
- [Paste-ready lane/steward commands, full timing tables, replay weights and limits](../testing/TEST-BUDGET.md).

## Results

Retained, byte-identical report pairs: continuation 867.7 → 23.1 s no-mutants warm / 30.1 s mutants warm;
ranked 687.5 → 27.2 s mutants warm; expansion 822.4 → 30.0 s mutants warm. Historical session load 3–23;
per-row loads were not saved. These measurements were not rerun. On the merged tree:

| Item row | Cases | First cached run after merge | Load 1m |
|---|---|---|---|
| `validate_item_continuation` | 25,772 | 618.1 s | 4.8 → 14.6, cold generator |
| `validate_item_carry` | 114,388 | 555.7 s | 4.9–25.2, batch range |
| `validate_item_chains` | 35,346 | 191.0 s | 4.9–25.2, batch range |
| `validate_item_clusters` | 74,292 | 336.8 s | 4.9–25.2, batch range |
| `validate_item_coverage` | 31,724 | 206.6 s | 4.9–25.2, batch range |
| `validate_item_expansion` | 52,172 | 236.0 s | 4.9–25.2, batch range |
| `validate_item_gear` | 25,256 | 140.6 s | 4.9–25.2, batch range |
| `validate_item_next` | 14,992 | 184.8 s | 4.9–25.2, batch range |
| `validate_item_product` | 2,874 | 54.2 s | 4.9–25.2, batch range |
| `validate_item_quality` | 28,080 | 152.9 s | 4.9–25.2, batch range |
| `validate_item_ranked` | 17,736 | 137.9 s | 4.9–25.2, batch range |
| `validate_item_scalars` | 26,154 | 133.3 s | 4.9–25.2, batch range |
| `validate_item_wings_next` | 33,622 | 217.5 s | 4.9–25.2, batch range |

| Small row | With mutants, retained | Without mutants | Cases | Load |
|---|---|---|---|---|
| `validate_item_effects` | 5.6 s | 1.4 s | 1,500 | old session 3–23; new 4.8–4.9 |
| `validate_render_items` | 3.3 s | 1.9 s | 5,512 | old session 3–23; new 4.8–4.9 |


## Affected selection and misses

The fixed twelve-PR replay (#280–#291) gives median weighted suite share **96.6% → 96.8%** and validator rows
**62 → 81.5**. The old WIP's rounded 96% / 57-row record lacked weights and per-PR details; the new replay saves both.
Explicit make/header narrowing removes some false dependencies, but the monolithic native archive, required docs
coverage and unknown-input fallback keep selection broad. No large suite-selection speedup is claimed.
Zero identified misses in the recorded-failure audit, including #287's pre-fix worlds_l/m assertions after
MU_WORLD_PT_BITMAPS grew. Private failures still require private execution; a portable selected test may skip them.

## Checks

| Check | Result | Wall | Load 1m |
|---|---|---|---|
| Initial `make -j4` | pass | 28.59 s | 2.6 → 17.2 |
| Build after #292 | pass | 12.49 s | 8.3–20.0 |
| test_test_budget + test_run_test_suites + test_validators_manifest | 60 tests, pass | 14.66 s | 4.7–5.1 |
| All suites, MU_GATE_JOBS=4 | 38 suites, 1916 tests, 1667 passed, 249 skipped, 0 failures, 0 errors; 0 failed suite(s); 196.9s wall, jobs=4 | 196.92 s process wall | 5.1–17.3 |
| Repository audit | Audited 1873 staged files; 0 rejected. | 13.43 s | 4.1–4.2 |
| Item validators | 13 pass, 482,408 cases, no mutants, zero mismatches | 618.24 s cold row + 1326.40 s two-worker batch | cold 4.8 → 14.6; batch 4.9–25.2 |
| After #293/#294, 98 affected items only | 15 suites, 1288 tests, 1090 passed, 198 skipped, 0 failures, 0 errors; 0 failed suite(s); 174.5s wall, jobs=2 | 201.47 s including selection; build 0.53 s | 3.0–6.5 |

Perf004: 80.5 s inside the full gate, load 5.1–17.3; source inspected, no extra benchmark and no tests removed.
The full macOS CI wrapper was not rerun in this lane. The requested all-suite runner gate passed once; the steward
runs the wrapper for its batch. The initial 35 budget tests also passed in 6.7 s before the final targeted check.

## Steward handoff and cleanup

Steward validators: validate_item_continuation, validate_item_carry, validate_item_chains, validate_item_clusters, validate_item_coverage, validate_item_expansion, validate_item_gear, validate_item_next, validate_item_product, validate_item_quality, validate_item_ranked, validate_item_scalars, validate_item_wings_next. All run with `--no-mutants --cache`; no mutant reruns requested.
These are exactly the thirteen registered consumers of the modified item harness, including the new product row.

Environment: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR="$HOME/Documents/MTM/mu-the-matrix-native/evidence"`.

Retain only the disposable original-side cache at `~/Documents/MTM/mu-mac-tools/native/cache/validators`, **62M**.
Remove lane scratch `native/scratch/test-speed-001`, verify-runs and the worktree/build outputs after the ready line.
Never commit the local input symlink. No push after adding the ready-prs entry.

Left: steward batch gate/merge; more precise ownership for unknown authoring/export tools and a verified way to
narrow shared-library dependencies; cache wiring for other validator families. No other lane work was attempted.

The owner-stopped WIP of 2026-11-04 is superseded by these completed measurements and checks.
