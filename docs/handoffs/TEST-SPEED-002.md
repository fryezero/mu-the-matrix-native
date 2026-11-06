# TEST-SPEED-002

PR-ready. Full gate at `5eea9e47`: 38 suites, 1,939 tests, 0 failures, 190.6 s. Final checks are recorded in [TEST-BUDGET](../testing/TEST-BUDGET.md#test-speed-002-measured-non-item-costs-and-narrower-validator-builds).
Started from TEST-SPEED-001's `817d5da1` while #297 was open, then integrated main `5a91b98d` through `725c3329`.
The steward owns the merge. No live game, service, login or dispatch work was performed.

Meshdraw full-row wall time is 367.99 s before, 110.57 s with batching and no cache, 97.50 s cold, 57.21 s warm,
and 59.49 s warm with controls. Every report has SHA-256
`2d6410499a2b13b13797071c8709b66eece6c51d7c1f8f98d93eb68c5100e8a1`.
The row retains 14,619 registered comparisons, 100,256 sampled math calls, zero mismatches and four caught
negative controls. A private compiled copy of the production name parser with its R flag broken produces
44 mismatches among 4,038 names, with 8,076 cache hits and zero misses. That mutant check takes 1.24 s.

The new test-only `native/tests/meshdraw_info_batch.c` calls the existing `mu-render info` entry point for each
model. The shared harness edit is limited to `scripts/validate_meshdraw.py`; no item/body/renderchar or combat
implementation was edited. The cache stores original results and observations only. Native parsing, replay,
name parsing and host math comparisons remain live. Pin, source and case invalidation are tested.

Fifteen native rows declare consumed build targets, with make/include/dependency-file provenance. Direct C
adapter headers are included; failed discovery and shared archive consumers remain conservative. The owning
unit test remains a trigger without importing its unrelated fixtures into a standalone validator's dependency
set. Suite-selection narrowing is deferred. The six-PR row replay gives #292 99→93, #293 72→56, #294 72→56,
#295 43→35, #296 43→31, #297 178→178. No required rerun was identified as missing; historical broad lists
contain deliberately removed unrelated rows. [Full lists and proof](../testing/test-speed-002-selection.json).

Terrain's attempted synthetic-scene optimization had byte-identical output but no observed wall-time gain,
so it was reverted. Terrain and model-edge now build their existing model-recovery prerequisite. Model-edge's
stateful original execution remains uncached. The worlds_after6 registry total now counts its existing prime
family, 7,300 rather than 6,300; its saved report rechecks successfully, without rerunning it or changing checks.

Steward validators: validate_meshdraw. Use `--no-mutants --cache --jobs 2`; no compiled mutant rerun requested.
The four built-in controls run regardless of the no-mutants switch.

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"
nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --only validate_meshdraw --jobs 2 --report verify-runs/test-speed-002
```

Retain the disposable cache at `~/Documents/MTM/mu-mac-tools/native/cache/validators`: 63 MiB total,
7.7 MiB for meshdraw. This lane's scratch and builds are removed after the ready line; the worktree stays until the steward merges.
No further push after that line. No new private input needs preservation.

Left: steward batch gate/merge; safe stateful model-edge caching; terrain's installed-world costs; further
proven ownership for broad archive consumers and computed inputs. No suite-time reduction is claimed.
