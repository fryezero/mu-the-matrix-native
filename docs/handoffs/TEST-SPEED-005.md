# TEST-SPEED-005

PR-ready. The steward owns the merge. No live game, network, login or dispatch work was done. No validator or
test check changed: this is selection tooling only. Details, the full replay table and limits:
[TEST-BUDGET](../testing/TEST-BUDGET.md#test-speed-005-symbol-level-use-of-shared-libraries).

**What changed.** `--affected` / `--affected-since` (validator rows) now prune at symbol level. A C source or
header that is an input only because a make target the row builds compiles it selects the row only if the
row's Python names an exported symbol of that target that the diff changed. `scripts/affected_symbols.py`
compiles the target's units to LLVM IR on the working tree and on the base commit (clang VFS overlay, same
flags). It fingerprints every function and global (anonymous constants by content, struct layouts included)
and follows calls and references inside each linked artifact. It falls back to "select" for changed global
data, a unit that does not compile, a new duplicate or unresolved symbol (#260), or a link it cannot map, and
reports those rows per row. Python side: identifiers, string words, and names built at run time (filled only
with the code's own word pieces). Also: `main()`-only code of an imported module is not an input unless that
main is called (validate_item_hiddenmesh), mutant-only path uses do not stop the pruning (unless the link
structure changed), and globs skip unit tests and docs like directories do.

**Replay (#295–#320 plus the five recorded failures, 53 cases, 82 min).** `scripts/replay_affected.py
docs/testing/test-speed-005-spec.json` runs the TEST-SPEED-004 selector (main `3ecc205c`) and this one on each
historical tree. Lane `--affected`: **956 → 747 rows**, measured serial time **49,153 → 29,231 s**. Steward
`--affected-since` on each PR's rows: **185 → 125**. Batch 55's #316: 31 → **12**, exactly the steward's 12.
#319 lane: 96 → 54 (24 of the 54 import the changed Python harness `validate_particles.py`, which stays a
whole-module input; 7 run native executables whose `main` reaches the change). #313 73 → 41, #300/#306 → 42/43
(the item rows no longer follow particles), steward #309 17 → 1, #311 5 → 1, #295 15 → 2. Every row a lane ran
is still selected.

**Misses: zero against the recorded failures** (#287 worlds_l/m host asserts, #282, #283, #280 suites
unchanged and caught; #260's duplicate `mu_swamp_*` caught by the link check). **One case to read:** #313's
steward ran 18 rows on make-level grounds; audio_charsel, audio_combat and viewport_monsters are not selected
now. At the merged tree none of the 6 / 43 / 16 libmunative exports they use reaches a changed function (the
slot classes, login/charsel frames, `mu_obj_visual_flicker`). They stay in the spec's `must_rows` and in the
table. The steward can rerun them once to confirm if it wants (~40 s together).

**Fallback rows (symbol level)** are listed per case. Most come from one native link line with a shell glob
(`build/mu-shell` links `build/shell/*.o`: validate_movement, and 25 rows at #296). The rest: mutant copies after
a new unit (#311: 26 rows), global data (#260), one C host without its flags (#313 mu_image.c) and
validate_worlds_r2's unbounded lookup. Expanding shell globs in link lines is the next cheap step.

**Costs.** Selection time: batch 55's 31 rows 18.9 s (16.1 s with TEST-SPEED-004) on a built tree; up to ~2× on a
lane diff that touches several libraries nothing else selects (each unit compiled once per side, -O0). Cache
keys are unchanged: every validator's Python closure is identical (checked for all rows), so nothing is cold
after the merge. Suites keep the input-level selection; 17 lane cases lose one suite through the `main()`-only
and glob rules (`test_render_time_live.py`, which never runs render_time.main's mu-world).

## Commands

Lane (docs/testing/TEST-BUDGET.md "Commands"; brief item 8 points there). Unchanged, except: run the selection
**after** `make`, and the listing's "kept by the symbol-level fallback" rows are part of the list.

```sh
nice -n 10 make -j4
tools/python/bin/python scripts/run_validators.py --list-affected origin/main     # = your "Steward validators:"
MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py --affected origin/main
nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2 --report verify-runs/lane-validators
```

Steward, per PR, after assembling and building the batch:

```sh
tools/python/bin/python scripts/run_validators.py --only "$PR_ROWS" --list-affected-since "$TESTED"
```

Paste-ready replacement for the brief's item 8 lane/steward lines:

> Lanes: after `make`, `run_validators.py --list-affected origin/main` is your `Steward validators:` list (with
> the commit). Run exactly that with `--affected origin/main` and trust it: no `make -n -W`, no grepping for
> changed functions. Rows "kept by the symbol-level fallback" are part of it. Steward: per PR, after the batch
> build, `run_validators.py --only "<its rows>" --list-affected-since <its tested commit>`; run the union (often
> nothing), then the full gate once per batch. Tooling-only PRs: "Steward validators: none".

## Checks

| Check | Result | Wall | Load 1m |
|---|---|---:|---|
| Full gate: `run_test_suites.py`, all suites, `MU_GATE_JOBS=4`, `nice -n 10`, no MAKEFLAGS (after `make -j4`, 30.7 s) | 38 suites, 2,059 tests: 1,789 pass, 270 skip, 0 fail | 226.1 s | 4.7 → 25.3 |
| test_affected_symbols + test_affected_inputs + test_test_budget (final code) | 73 tests OK | 48.9 s | 8.1 |
| Repository audit, staged | 1,998 files, 0 rejected | 25.9 s | ~8 |
| Replay #295–#320 + 5 failure cases (53 cases), `replay_affected.py` | 0 misses against recorded failures; #313's 3 make-level rows explained above | 82 min | 4–19 |
| Batch 55 (#316) `--list-affected-since 121f24f7` on this tree, built | 12 of 31 (the steward's 12) | 18.9 s (33.1 s at load ~12) | 4–12 |

Steward validators: none (tooling). The selection changes which rows run, not what any row checks.
Env for the steward's gate: the usual portable gate (no `MU_*` private env); `MU_RECOVERY_INTEGRATION=1`,
`MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin` only for
validator runs.

Kept until the merge: the worktree `~/Documents/MTM/worktrees/test-speed-005`. Scratch (replay worktrees, logs)
is removed; the replay result is in docs/testing.
