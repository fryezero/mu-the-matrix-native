# TEST-SPEED-004

PR-ready. The steward owns the merge. No live game, network, login or dispatch work was done. No validator or
test check changed: this is selection tooling, plus one cache read race (below). Details, the full replay table
and limits: [TEST-BUDGET](../testing/TEST-BUDGET.md#test-speed-004-each-rows-exact-inputs).

**What changed.** `--affected` / `--list-affected` now select a validator row only if the diff touches one of
the row's derived inputs. The Python inputs are its imports and `importlib` loads, plus the repository paths
its code builds, classified by use (`make -C` targets, `-I` headers, globs, `sys.path`). The compiled inputs
come per make target from `make -nB`, with headers from fresh `.d` files or `cc -MM`; a Makefile change counts
only when the target's dry run changes. The row's own script and manifest row also count. The selection
tooling, `tests/` and `docs/` select no row. There is no global "unmapped → everything" any more: a row whose
inputs cannot be derived is a reported fallback (currently none; `tests/test_affected_inputs.py` pins the set).
New `--affected-since <tested commit>` on both runners is the steward's question.

**Replay (#292–#308, plus the recorded failures).** `scripts/replay_affected.py` runs the previous and the new
selector on each historical tree. Lane `--affected`: 1,331 → **619** rows, measured serial time 47,927 →
31,586 s. The tooling PRs dropped the most: #297 178 → 22, #299 178 → 16, #305 36 → 1, #307 185 → 38. Steward
`--affected-since` on each PR's own rows: 169 → **99**. #306 gives exactly the 26 rows the steward ran by hand;
#292 gives 0 where the steward ran 40 by fallback. **Zero misses**: #287 worlds_l/m, #282 renderchar/item
textures, #283 particles, #280 audio, #260's objects link failure. Every row the steward ran is selected or
provably unchanged. The new selector adds real inputs the old one missed in 13 cases (rows running
`make -C native build/mu-path|mu-terrain|mu-session`, libcombat's `.inc` files, validate_model_light →
validate_skinning).

**Not done: symbol-level pruning.** The item rows still follow every `libclient_particles` change (~3,600 s
measured), and terrain/model_edge/meshdraw follow every libmunative change. The steward skipped those by
reading which functions are called; the tool stays at the target level because #260's duplicate symbols broke
the link for every consumer. It needs a per-target duplicate/undefined-symbol check first.

**Cache: one cold run per cached row after the merge.** The old cache key hashed `affected.py` itself. The
new closure keys on the harness without the selector, so later selector changes keep the cache warm.
`original_cache` now `fstat`s the file it read: the concurrent-writer test lost one worker's round (600 ≠ 640)
under load once before the fix.

## Commands

Lane (in docs/testing/TEST-BUDGET.md "Commands"; brief item 8 points there):

```sh
nice -n 10 make -j4
tools/python/bin/python scripts/run_validators.py --list-affected origin/main     # = your "Steward validators:"
MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py --affected origin/main
nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2 --report verify-runs/lane-validators
```

Run what it selects and trust it: no `make -n -W` hand-picking, no extra "nearby" rows.

Steward, per PR, after assembling the batch:

```sh
tools/python/bin/python scripts/run_validators.py --only "$PR_ROWS" --list-affected-since "$TESTED"
```

Paste-ready replacement for the brief's item 8 lane/steward lines:

> Lanes: `run_validators.py --list-affected origin/main` is your `Steward validators:` list (with the commit);
> run exactly that with `--affected origin/main` and trust it. Rows "on the conservative fallback" are part of
> it. Steward: per PR, `run_validators.py --only "<its rows>" --list-affected-since <its tested commit>`; run
> the union (often nothing), then the full gate once per batch. Tooling-only PRs: "Steward validators: none".

## Checks

| Check | Result | Wall | Load 1m |
|---|---|---:|---|
| CHECKS_TABLE |

Steward validators: none (tooling). The selection changes which rows run, not what any row checks.
Env for the steward's gate: the usual portable gate (no `MU_*` private env); `MU_RECOVERY_INTEGRATION=1`,
`MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin` only for
validator runs.

Kept until the merge: the worktree `~/Documents/MTM/worktrees/test-speed-004`. Scratch (replay worktrees, logs)
is removed; the replay result is in docs/testing.
