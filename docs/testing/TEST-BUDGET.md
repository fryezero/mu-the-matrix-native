# Test budget: what runs when (TEST-SPEED-001)

The owner asked for agents' finish phase to run only the checks a change needs. The policy is the brief's
"TEST BUDGET" section (2026-11-04); this page is the tooling that applies it and the measured effect.
[Handoff](../handoffs/TEST-SPEED-001.md).

## Commands

Check `uptime`, `memory_pressure | tail -1`, and `df -h ~` before each heavy command. Wait at load >14
or free memory <25%; follow the brief's swap-growth rule. Run one heavy command at a time.

Set the private environment once, in the lane or steward worktree:

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_EVIDENCE_DIR="$HOME/Documents/MTM/mu-the-matrix-native/evidence"
```

Lane finish. The unit command uses the portable gate environment. Private instruction comparisons run in the
validator command, so unit tests do not silently repeat their own private mutant runs:

```sh
nice -n 10 make -j4
MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py --affected origin/main
nice -n 10 tools/python/bin/python scripts/audit_repository.py
nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2 --report verify-runs/lane-validators
# Set MUTANT_ROWS to the comma-separated rows whose checks or mutant targets you changed.
# Leave empty if none. Run this once, after iteration is finished.
if [ -n "${MUTANT_ROWS:-}" ]; then
  nice -n 10 tools/python/bin/python scripts/run_validators.py --private --cache --only "$MUTANT_ROWS" --jobs 2 --report verify-runs/lane-mutants
fi
```

The audit is required when files were added or renamed. Inspect selection first with `--list-affected origin/main`
on either runner. Review its reasons; list the affected compiled sources and validators in the PR. Brief 6b also
requires checking consumers of changed constants, struct fields and table sizes. A computed dependency can evade
static discovery. Select those consumers explicitly if they are absent. Include any required installed-data test
separately with its private environment; portable unit selection alone does not execute private tests.

Steward per batch. Set `STEWARD_ROWS` to the union of the PRs' listed validators. No mutant reruns unless a PR
explicitly delegates them. The full gate's portable suite environment keeps validators separate:

```sh
MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=4 nice -n 10 bash scripts/local-macos-ci.sh
if [ -n "${STEWARD_ROWS:-}" ]; then
  nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --only "$STEWARD_ROWS" --jobs 2 --report verify-runs/steward-validators
fi
```

For a docs-only batch, brief 6c replaces the full gate with the audit and `test_world_captures_2`,
`test_repository_policy`, `test_native_item_textures`, `test_native_data_manifest`. The affected selector includes
these through `tests` plus the two native modules. A full uncached, mutant-enabled registry run belongs to an
explicit integration lane, not an ordinary finish.

## Flags

| Command | Flag | What it does |
|---|---|---|
| `run_validators.py` | `--no-mutants` | Removes the mutant switches from each row's arguments (`--mutations`, `--mutants`, and with them `--mutant-cases N`/`--mutation-cases N`) and drops the expectations that read mutant results (the row's `mutants_at` paths and every path naming mutants, mutations or negative controls). The merged registry has 115 rows with a removable switch. `--mutations N` with a number (effects, effect_tree, meshdraw) is a count of random input cases, not planted mistakes, and stays; 16 rows have negative controls built into every run and are unchanged. The summary says how many rows ran without mutants; `--index` refuses such a summary (the evidence index records mutant counts). |
| `run_validators.py` | `--affected REF` / `--list-affected REF` | Rows a diff from `merge-base(REF, HEAD)` to the working tree (commits, staged, unstaged, untracked) can affect, with the reason for each. |
| `run_validators.py` | `--cache [DIR]` / `--no-cache` | Reuse original-instruction results (below). Default DIR `~/Documents/MTM/mu-mac-tools/native/cache/validators`. |
| `run_validators.py` | (always) | Wall times in `verify-runs/validator-times.json` (ignored); `--jobs N` starts the longest rows first, unknown rows first of all. |
| `run_test_suites.py` | `--affected REF` / `--list-affected REF` | Work items (suites; `native/tests` per module) a diff can affect, with the reason for each. Lanes only: the steward keeps the full gate. |

### How `--affected` maps a diff (scripts/affected.py)

It may select too much, never knowingly too little:

- **A validator row** reads its script and every repository Python file it imports or names (closure, resolved
  next to the file and in `scripts/`); every path its string literals name (a file, or everything under a directory);
  every file whose base name it quotes; its owning test file (and that file's closure); its `build` directories (all
  files except `*.md` and `test_*.py`) and everything their Makefile reaches with `../` (`-I../record-math`,
  `include ../deps.mk`, `RECON := ../reconstructed`); the paths its `args`/`prepare` name; its own manifest row
  (compared with REF's `validators.toml`). `scripts/pins.py`, `scripts/run_validators.py` and
  `scripts/affected.py` select every row.
- **A suite directory** (`reconstructed/*`, `asset-recovery`, `model-recovery`) runs if the diff touches the
  directory, what its Makefile reaches with `../`, or what its test modules import or name.
- A `native/tests` module follows its Python import/path closure and the native make targets it names.
  Explicit target commands no longer inherit the native default goal just because their source mentions `make`.
  A missing/computed target or make wrapper retains the default. Failed dry runs fall back to the whole make
  directory. Header dependencies follow recursive includes and `.d` files; computed includes keep the broad
  include-directory fallback. Target names remain visible before and after build outputs exist.
- `tests` runs for every diff. Docs also select the four brief-6c modules, two inside `tests`. Infrastructure
  selects all suites. Unmapped non-doc inputs select everything, with the reason printed. Validator manifest
  changes are handled row by row; unreferenced unit-test files cannot alter standalone validator execution.
- Local untracked directory symlinks such as `input` are excluded from the diff; tracked symlinks still count.

The native archive links almost all core/reconstructed sources, so selection remains broad for C changes.
The replay below quantifies this limit; do not promise a large suite saving. Imports or paths computed at runtime
can remain invisible, especially when the same changed path is already mapped to a different consumer. This is
an advisory conservative selector, not a complete dependency proof. The steward keeps a full batch gate.

### Original-instruction cache (scripts/original_cache.py)

The pinned client never changes, so the original side of a validator case is a function of the pins, the Python
code that drives Unicorn, and the case input. With `--cache` (or `MU_VALIDATOR_CACHE=<dir>`) that side is stored in
`<dir>/<name>/<key>.pickle.xz`; the key hashes every pin's sha256, the Unicorn and Python versions and the sha256
of every Python file in the closure of the script that runs the original side. Any harness change starts a new key
(the old file is deleted). Pins are still read and verified before using the cache. The key includes the section3 pin as well as text, data, flag and feature pins. Portable tests prove that changing a pin or harness source invalidates warm entries and that a changed C result still fails against a warm cache. Only the original side is cached: the C library is called for every case and compared
with the cached original exactly as with a fresh one, and a C mutant run with a warm cache is still caught.

Wired into the shared item harness, so every validator using it gets the cache:

| Where | Original side cached | Used by |
|---|---|---|
| `gen_item_bodies._original` (cache `gen_item_bodies`) | each Unicorn sample of the body-table regeneration (`client_stream` + the helper tags, exits, random draws and sites its hooks record); the generic C stream and the fit stay live | the 13 validators that check `item_bodies.h` against `gen_item_bodies.generate()` (continuation, ranked, expansion, clusters, chains, next, gear, coverage, scalars, carry, wings_next, quality, product) |
| `validate_item_clusters.body_cases` / `link_cases` | the body stream and the link-effect calls per case | body_cases: item_continuation, ranked, expansion, clusters, chains, next, gear, coverage, scalars, carry, wings_next; link_cases: continuation, expansion, clusters |
| `validate_item_continuation.skin_cases`, `validate_item_ranked.link_cases` | per case | those two |

The pattern for another validator: wrap the call that runs the pinned instructions for one case in
`original_cache.active().get('<family>', <case input>, lambda: <run it>)`, return only plain data (no machine), and
keep every C call outside the lambda. If the original run has side effects other code reads (hooks filling lists),
capture them in the cached value and replay them, as `gen_item_bodies._original` does.

## Timings

| Check | Before | After | How |
|---|---|---|---|
| `validate_item_continuation` (25,772 cases, 9 mutants) | 867.7 s (mutants, no cache) | 719.9 s `--no-mutants` cold cache · **23.1 s** `--no-mutants` warm · 30.1 s mutants warm | reports byte-identical; warm mutant run catches all 9 with the same counts |
| `validate_item_ranked` (17,736 cases, 6 mutants) | 687.5 s | 97.3 s first `--cache` run (generator cache already warm) · **27.2 s** mutants warm · 23.3 s `--no-mutants` warm | byte-identical |
| `validate_item_expansion` (52,172 cases, 7 mutants) | 822.4 s | 228.4 s first `--cache` run · **30.0 s** mutants warm · 23.1 s `--no-mutants` warm | byte-identical |
| Other 9 original rows sharing the generator (clusters, chains, next, gear, coverage, scalars, carry, wings_next, quality) | ~11–15 min each (same 800–960 s generator) | {{OTHER_ITEM}} | first `--cache` run, generator cache warm |
| Validator rows a lane reruns | all nearby rows, with mutants | `--affected`: 0–94 of 170 rows on the last 12 merged PRs (median 62), without mutants | selection only, below |
| `make test` work items a lane runs | 154 items, 321 s serial (orchestrator's measurement) | `--affected`: {{SUITES}} | estimate from recorded per-item times |
| Full gate (`local-macos-ci.sh`) | {{GATE_BEFORE}} | {{GATE_AFTER}} | steward only |


## Selection replay and misses

[Frozen weights and selection lists](test-speed-001-selection.json). Replayed the twelve PRs ending at stopped main `90e11d71`, #280 through #291, with each merge's first-parent diff.
Both selectors used the merged tree and the same frozen main-checkout timing weights: 397.4 s across 154 recorded
items. Two new modules lack weights, so shares exclude their time; selection still includes them. This is a weighted
serial-time estimate, not twelve timed gate runs. The prior WIP recorded rounded 96% and 57 validator rows without
saving its weights or per-PR list. The reproducible baseline here is 96.6% and 62 rows. Manifest replay compares only
the row edits in each historical PR, not later edits. Current registry: 174 rows; current suite work items: 156.

| PR | Suite items before → after | Weighted time before → after | Validator rows before → after |
|---|---|---|---|
| #291 | 130 → 125 | 97.7% → 96.9% | 112 → 112 |
| #290 | 114 → 156 | 95.7% → 100.0% | 39 → 174 |
| #289 | 1 → 3 | 0.6% → 2.6% | 0 → 0 |
| #287 | 121 → 116 | 96.6% → 95.7% | 62 → 62 |
| #288 | 40 → 41 | 35.7% → 36.1% | 51 → 174 |
| #286 | 120 → 115 | 96.5% → 95.6% | 65 → 65 |
| #285 | 123 → 122 | 97.3% → 96.8% | 65 → 174 |
| #284 | 31 → 32 | 38.7% → 39.1% | 16 → 16 |
| #283 | 125 → 124 | 97.4% → 96.9% | 62 → 62 |
| #282 | 114 → 156 | 95.7% → 100.0% | 39 → 174 |
| #281 | 123 → 122 | 97.3% → 96.8% | 65 → 65 |
| #280 | 134 → 133 | 98.6% → 98.2% | 98 → 98 |

Median suite share: **96.6% → 96.8%**. Median validator rows: **62 → 81.5**. Narrower make/header mapping removes
some unnecessary suites, but required docs coverage and the new unknown-input fallback offset that saving.
`classify_item_bodies.py` triggers the all-suite fallback in #282/#290. Unmapped exporter/classifier scripts also
increase validator selection in #285/#288/#290. This is a coverage tradeoff, not a speedup claim. Future work needs
explicit ownership for those tools or a verified link dependency model, rather than dropping shared-library checks.

Known-failure selection audit: zero identified misses. #287's original failing head `724ad10a`, before the host fixes,
changes `mu_particles.h`; both `test_native_worlds_l` and `test_native_worlds_m` retain that dependency through their
hosts. This catches the `MU_WORLD_PT_BITMAPS` growth documented in the steward's PR comment. #282 retains the
renderchar suite containing continuation/gear/scalars' stale assertions and `test_native_item_textures`; #283 retains
`test_native_particles`; #280 retains `test_native_audio`. The renderchar and item-texture private failures recorded
in INTEGRATION-GREEN-002 stay selected, but need private execution to be observed. This audits selection against
recorded failures, not a claim that historical gates were re-executed or that all possible misses have been disproved.
