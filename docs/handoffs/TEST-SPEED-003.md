# TEST-SPEED-003

PR-ready. The steward owns the merge. No live game, network, login or dispatch work was done. No validator or
test check changed. Numbers, commands and limits are in
[TEST-BUDGET](../testing/TEST-BUDGET.md#test-speed-003-multi-key-cache-and-self-built-suite-libraries).

**Cache thrash fixed.** `scripts/original_cache.py` now keeps the 4 most recently used keys per name (LRU by mtime,
touched on load) and caps the directory at 250 MB. A save merges a concurrent same-key writer's entries under a
per-name `flock` and replaces the file atomically. Keys and file format are unchanged, so the shared directory
`~/Documents/MTM/mu-mac-tools/native/cache/validators` migrates in place; nothing in it was deleted or rewritten
by this lane.

Measured on `validate_item_product` (2,874 cases, 0 mismatches, no mutants), alternating main and a branch-like
generator harness: main cold 586.16 s, warm 33.67 s, branch cold 605.45 s, then main 35.88 s, branch 37.29 s,
main 34.39 s. All warm, with zero misses. With the old code each of those three switches would have been cold
(~586–605 s each, an estimate from the measured cold walls). All six reports are byte-identical.

**`test_joints` fresh-worktree failure fixed.** The test builds `reconstructed/combat` before loading
`libcombat`. The private `test_native_character` path builds `reconstructed/model-codec` before loading
`libcharacter`. A static test (`SuitesBuildWhatTheyLink`) guards the pattern.

Checks:
- full suites: 38 suites, 1,973 tests, 0 failures, 198.0 s;
- budget and cache tests: 54 pass, 21.6 s;
- the audit: 1,925 files, 0 rejected, 16.7 s.

Limits:
- **One cold run per cached row after the merge.** `original_cache.py` is in the code closure of every cached
  validator (the 13 item rows through `gen_item_bodies`, the 3 rows with their own case caches, meshdraw), so
  merging this PR gives each of them a new key.
- **Old code still evicts.** Worktrees still on the old cache code delete other keys of a name when they save,
  until they merge main.
- **Measurement base.** The measurement ran at `dacc64f2`, before merging #295/#303/#304. #295 then changed
  `gen_item_bodies.py` and renderchar, but none of the cache code.

Steward validators: none required for this tooling change; optional warm-up `validate_item_product`
(`--no-mutants --cache --jobs 2`). Env:
`MU_RECOVERY_INTEGRATION=1`,
`MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`.

Kept until the merge: the worktree `~/Documents/MTM/worktrees/test-speed-003`. Scratch is removed.
