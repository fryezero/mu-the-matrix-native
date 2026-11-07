# Test budget: what runs when (TEST-SPEED-001 / 002 / 003 / 004 / 005)

The owner asked for agents' finish phase to run only the checks a change needs. The policy is the brief's
"TEST BUDGET" section (2026-11-04); this page is the tooling that applies it and the measured effect.
[Handoff](../handoffs/TEST-SPEED-001.md).

## Commands

Check `uptime`, `memory_pressure | tail -1`, and `df -h ~` before each heavy command. Wait at load >14
or free memory <25%; follow the brief's swap-growth rule. Run one heavy command at a time.
Run every command from the repository root, as the gate does (fixture scenarios name repository-relative
tables; REGRESS-002).

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

The audit is required when files were added or renamed. Since TEST-SPEED-004 the selection is each row's derived
inputs, and since TEST-SPEED-005 a C change inside a library a row only builds counts only if the row names a
changed exported symbol (below). So **run what `--affected origin/main` selects and trust it**: no hand-picking
with `make -n -W`, no adding "nearby" rows, no dropping rows by reading scripts or by grepping for the changed
functions. Run `--list-affected` **after** `make` (the symbol analysis compiles the build's units to IR, and
native units need the generated `native/build/gen` headers; without them they are a reported fallback).
`Steward validators:` in the PR is exactly the selected list (`--list-affected origin/main` prints it with a
reason per row), with the commit you ran it at. The listing ends with the rows kept by the symbol-level
fallback (a change it cannot attribute to functions: global data, a unit that does not compile, a new
duplicate or unresolved symbol, an unbounded symbol lookup), the rows it dropped because they use no changed
symbol, and the rows on the input-level conservative fallback, if any. Kept rows are part of the list.
Brief 6b (consumers of a changed constant, struct field or table size) is covered for validator rows by the
compiled inputs (the header is an input of every target that includes it); for unit tests keep 6b. Include any
required installed-data test separately with its private environment; portable unit selection alone does not
execute private tests.

Steward per batch. For each PR, the steward's question is which of its tested rows have inputs that changed
between the commit the lane ran them at and the merged tree:

```sh
# per PR: TESTED = the commit its "Steward validators:" line names, after merging the batch's chain locally
tools/python/bin/python scripts/run_validators.py --only "$PR_ROWS" --list-affected-since "$TESTED"
# STEWARD_ROWS = the union of what those print (often nothing: the lane's results stand)
MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=4 nice -n 10 bash scripts/local-macos-ci.sh
if [ -n "${STEWARD_ROWS:-}" ]; then
  nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --only "$STEWARD_ROWS" --jobs 2 --report verify-runs/steward-validators
fi
```

`--affected-since` diffs the tested commit itself (not a merge base) against the working tree, so everything the
chain merge brought in counts. Tooling-only PRs (`scripts/affected.py`, the runners, `original_cache.py`,
`guarded_run.py`, `tests/`, `docs/`) select no validator row: "Steward validators: none (tooling)".

For a docs-only batch, brief 6c replaces the full gate with the audit and `test_world_captures_2`,
`test_repository_policy`, `test_native_item_textures`, `test_native_data_manifest`. The affected selector includes
these through `tests` plus the two native modules. A full uncached, mutant-enabled registry run belongs to an
explicit integration lane, not an ordinary finish.

## Flags

| Command | Flag | What it does |
|---|---|---|
| `run_validators.py` | `--no-mutants` | Removes the mutant switches from each row's arguments (`--mutations`, `--mutants`, and with them `--mutant-cases N`/`--mutation-cases N`) and drops the expectations that read mutant results (the row's `mutants_at` paths and every path naming mutants, mutations or negative controls). At replay base 90e11d71, the registry has 115 rows with a removable switch. `--mutations N` with a number (effects, effect_tree, meshdraw) is a count of random input cases, not planted mistakes, and stays; 16 rows have negative controls built into every run and are unchanged. The summary says how many rows ran without mutants; `--index` refuses such a summary (the evidence index records mutant counts). |
| `run_validators.py` | `--affected REF` / `--list-affected REF` | Rows whose derived inputs a diff from `merge-base(REF, HEAD)` to the working tree (commits, staged, unstaged, untracked) touches, with the reason for each, then the rows on the conservative fallback. |
| `run_validators.py` | `--affected-since REF` / `--list-affected-since REF` | The same from REF itself (the steward: a lane-tested commit) to the working tree. Combine with `--only` to ask about one PR's rows. |
| `run_validators.py` | `--cache [DIR]` / `--no-cache` | Reuse original-instruction results (below). Default DIR `~/Documents/MTM/mu-mac-tools/native/cache/validators`. |
| `run_validators.py` | (always) | Wall times in `verify-runs/validator-times.json` (ignored); `--jobs N` starts the longest rows first, unknown rows first of all. |
| `run_test_suites.py` | `--affected REF` / `--list-affected REF`, `--affected-since REF` | Work items (suites; `native/tests` per module) a diff can affect, with the reason for each. Lanes only: the steward keeps the full gate. |

### How `--affected` maps a diff (scripts/affected.py)

TEST-SPEED-004 replaced the validator side of this mapping; see
[below](#test-speed-004-each-rows-exact-inputs). The text in this subsection is the TEST-SPEED-001/002 design
it started from; the suite side keeps most of it. It may select too much, never knowingly too little:

- **A validator row** reads its script and every repository Python file it imports or names (closure, resolved
  next to the file and in `scripts/`); every path its string literals name (a file, or everything under a directory);
  every file whose base name it quotes; its owning test file; its explicit `build_targets` through forced make dry runs and header dependencies,
  or, without targets, its `build` directories (all
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
of every Python file in the closure of the script that runs the original side. Any harness change starts a new key;
since TEST-SPEED-003 the older keys are kept (four most recently used per name, 250 MB for the whole directory, see
[below](#test-speed-003-multi-key-cache-and-self-built-suite-libraries)), so a lane branch and main stay warm side by side. Pins are still read and verified before using the cache. The key includes the section3 pin as well as text, data, flag and feature pins. Portable tests prove that changing a pin or harness source invalidates warm entries and that a changed C result still fails against a warm cache. Only the original side is cached: the C library is called for every case and compared
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

The first three rows are retained pre-resume measurements. That session recorded load 3–23 overall, but did not
save per-row load samples. Do not read those numbers as a controlled comparison against the merged tree.

| Check | Before | After | How |
|---|---|---|---|
| `validate_item_continuation` (25,772 cases, 9 mutants) | 867.7 s (mutants, no cache) | 719.9 s `--no-mutants` cold cache · **23.1 s** `--no-mutants` warm · 30.1 s mutants warm | reports byte-identical; warm mutant run catches all 9 with the same counts |
| `validate_item_ranked` (17,736 cases, 6 mutants) | 687.5 s | 97.3 s first `--cache` run (generator cache already warm) · **27.2 s** mutants warm · 23.3 s `--no-mutants` warm | byte-identical |
| `validate_item_expansion` (52,172 cases, 7 mutants) | 822.4 s | 228.4 s first `--cache` run · **30.0 s** mutants warm · 23.1 s `--no-mutants` warm | byte-identical |
| Other 9 original rows | Individually uncached runs not measured; each repeats the same historical 800–960 s generator work | 133.3–555.7 s, table below | generator warm; row-specific cases cold where cached |
| Full macOS CI | Historical 116–130 s, load peaks 11.4–19.2, GATE-PAR-001 | policy unchanged; not re-timed here | steward per batch |

### Resume measurements on merged main

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

All thirteen rows passed. Every row after continuation logged **115,980 generator hits, zero misses**. The cold
continuation rebuilt 91,272 generator entries after the main merge changed the harness. Main #292 changed none
of these rows' Python hash closure or renderchar build inputs. No row was repeated to obtain a second warm timing.
The two-worker batch wall was 1326.40 s, including per-row startup and report work, excluding the
resource wait before it. Other lanes were active; these are observations, not isolated performance guarantees.

| Small row | With mutants, retained | Without mutants | Cases | Load |
|---|---|---|---|---|
| `validate_item_effects` | 5.6 s | 1.4 s | 1,500 | old session 3–23; new 4.8–4.9 |
| `validate_render_items` | 3.3 s | 1.9 s | 5,512 | old session 3–23; new 4.8–4.9 |

The small comparison reuses the two completed mutant runs from the saved WIP. Non-mutant case reports are equal
after removing the mutant field. No all-registry mutant run was launched. The retained full continuation/ranked/
expansion report pairs were also rechecked byte-for-byte equal. A 162.2 s warmup attempt was interrupted to finish
a tracked-symlink selector correction before cache population; it is not counted as a passing run or a speed sample.

### Delivery checks

| Check | Result | Wall | Load 1m |
|---|---|---|---|
| Initial `make -j4` | pass | 28.59 s | 2.6 → 17.2 |
| Build after #292 | pass | 12.49 s | 8.3–20.0 |
| test_test_budget + test_run_test_suites + test_validators_manifest | 60 tests, pass | 14.66 s | 4.7–5.1 |
| All suites, MU_GATE_JOBS=4 | 38 suites, 1916 tests, 1667 passed, 249 skipped, 0 failures, 0 errors; 0 failed suite(s); 196.9s wall, jobs=4 | 196.92 s process wall | 5.1–17.3 |
| Repository audit | Audited 1873 staged files; 0 rejected. | 13.43 s | 4.1–4.2 |
| Item validators | 13 pass, 482,408 cases, no mutants, zero mismatches | 618.24 s cold row + 1326.40 s two-worker batch | cold 4.8 → 14.6; batch 4.9–25.2 |
| After #293/#294, 98 affected items only | 15 suites, 1288 tests, 1090 passed, 198 skipped, 0 failures, 0 errors; 0 failed suite(s); 174.5s wall, jobs=2 | 201.47 s including selection; build 0.53 s | 3.0–6.5 |

After #293/#294 landed during publication, their app/world changes selected 98 of 159 items. Only those were rerun under brief 6; both sides of status-doc conflicts were retained. Item harness/cache inputs were unchanged.

The requested full gate here is `scripts/run_test_suites.py` with all suites, after the build, plus a separate audit.
The broader `local-macos-ci.sh` fixture/viewer/live-reader stages remain the steward's batch responsibility.

Perf004 analysis was limited to source inspection and this required gate: its module took 80.5 s at gate load
5.1–17.3. It performs six large serial/parallel buffer comparisons, four small/empty-count comparisons across eight executions, three
topology variants, six GL variants and lease-audit equivalence checks. No checks were removed and no extra perf004
benchmark run was needed. Its source/target dependencies stay selected for relevant native changes.

Cache retained at `~/Documents/MTM/mu-mac-tools/native/cache/validators`: **62M** total at handoff. Scratch,
verify-runs and build outputs are removed after publication; this disposable cache is the retained input for the
steward. Deleting it is safe and makes the next run cold.

## Selection replay and misses

[Frozen weights and selection lists](test-speed-001-selection.json). Replayed the twelve PRs ending at stopped main `90e11d71`, #280 through #291, with each merge's first-parent diff.
Both selectors used the merged tree and the same frozen main-checkout timing weights: 397.4 s across 154 recorded
items. Two new modules lack weights, so shares exclude their time; selection still includes them. This is a weighted
serial-time estimate, not twelve timed gate runs. It excludes selector overhead: the twelve-diff analysis took
44.0 s before and 61.4 s after, reusing in-process dependency discovery, at ending load 6.8 and 5.4 respectively. The prior WIP recorded rounded 96% and 57 validator rows without
saving its weights or per-PR list. The reproducible baseline here is 96.6% and 62 rows. Manifest replay compares only
the row edits in each historical PR, not later edits. Replay registry: 174 rows; replay suite work items: 156. Delivery also integrates #292; it does not change the item harness or its build inputs.

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

## TEST-SPEED-002: measured non-item costs and narrower validator builds

[Implementation and safety](../research/test-speed-002.md), [handoff](../handoffs/TEST-SPEED-002.md),
[selection lists and compiled-input provenance](test-speed-002-selection.json).

Meshdraw's full row falls from **367.99 s to 57.21 s warm**, about **6.4×**. The row still checks 14,619
registered comparisons: 843 synthetic/installed draws, 247 pinned draws and 13,529 names, plus 100,256 sampled
math calls. Zero mismatches; all four built-in negative controls caught. `--mutations 300` is random input
coverage and stays enabled. These rows have no optional compiled-mutant flag, so controls run in both modes.
A separate compiled mutation of production `mu_meshdraw_sub_from_name` produces 44 mismatches among 4,038
synthetic names with 8,076 original-cache hits and zero misses, 1.24 s. The worktree library was never mutated.

All five full meshdraw reports are byte-identical, including coverage, trig observations, counts, and controls:
`2d6410499a2b13b13797071c8709b66eece6c51d7c1f8f98d93eb68c5100e8a1`.
The cache-disabled, cold, warm and warm-control runs use the same integrated tree. The old-harness baseline
precedes integration of #296; its meshdraw, BMD, model-recovery and terrain production sources did not change.
Loads below are start/end 1-minute readings, not peaks. Other lanes ran concurrently; these are observed times.

| Meshdraw full row | Wall | Load 1m |
|---|---:|---|
| Old harness, full, uncached | 367.99 s | 8.11 → 6.02 |
| Batch host, cache disabled | 110.57 s | 8.92 → 8.66 |
| Batch host, cold original cache | 97.50 s | 5.81 → 6.77 |
| Batch host, warm original cache | 57.21 s | 6.69 → 6.53 |
| Warm, controls enabled | 59.49 s | 6.00 → 11.65 |

The cold cache had zero loaded entries, 127,512 misses and 893 repeated-case hits. Warm runs had 128,405 hits
and zero misses. Its compressed disk footprint is **7.7 MiB** (8,054,060 bytes); the shared cache totals **63 MiB**, including the
pre-existing item cache. It is disposable. Deleting it restores cold execution. Native output is never cached;
model parsing, replay and name parsing run on every check. Host math comparisons also run on hits.

The largest meshdraw profile cost was 13,874 subprocess calls, 335 s cumulative, including 313 s collecting
installed texture names. The test-only batch host calls the existing info entry point once per file, 64 files
per process. The original-side cache separately avoids repeated Unicorn calls and preserves their observations.

Terrain's experimental scene-generation change yielded the same full report but no measured improvement:
324.54 s before, load 8.11→6.48, versus 343.68 s after, load 8.92→6.71. It was reverted. No terrain speedup is
claimed. Model-edge's profile spent 199 s in emulation/hooks and 122 s in Python LEA decoding; cumulative times
overlap. The fresh worktree lacked model-recovery's readers. Its prerequisite is now declared for model-edge
and terrain. The following full runs used the readers. Stateful model-edge original execution remains uncached.

| Other full row | Cases | Wall | Load 1m | Result |
|---|---:|---:|---|---|
| `validate_terrain` | 583,500 | 324.54 s | 8.11 → 6.48 | pass |
| `validate_model_edge` | 954 | 106.86 s | 6.48 → 5.51 | pass |
| `validate_audio_domains` | 2,544 | 22.38 s | 6.02 → 5.81 | pass |
| `validate_model_light` | 1,433 | 4.81 s | 5.81 → 5.82 | pass |

### Profiling sample

Two workers, `nice -n 10`, no optional mutants. Meshdraw used per-folder 1, mutations 10, math-sweep 200;
terrain used scale-002 1 and installed world 1; model-edge used sample 20. Those three used cProfile and their
wall times include its overhead and the fresh-worktree builds. Other rows used registry sample counts.
Missing inputs were fixed before the full rows above. The terrain profile ends before installed-world work,
so its 61/97 s synthetic-scene share is not a full-row share. No failed exploratory sample is called a pass.

| Row | Wall | Load 1m | Result |
|---|---:|---|---|
| `validate_meshdraw` | 371.84 s | 10.51 → 9.13 | exit 0; reduced sample below full-registry count |
| `validate_terrain` | 115.01 s | 10.51 → 9.26 | missing v14 reader; full rerun passed below |
| `validate_model_edge` | 353.98 s | 9.26 → 5.41 | pass |
| `validate_audio_callers` | 3.58 s | 9.13 → 8.56 | pass |
| `validate_audio_combat` | 17.73 s | 8.56 → 7.18 | pass |
| `validate_audio_domains` | 0.00 s | 7.18 → 7.18 | missing snapshot location; full rerun passed below |
| `validate_audio_items` | 2.60 s | 7.18 → 6.85 | pass |
| `validate_audio_charsel` | 3.04 s | 6.85 → 6.85 | pass |
| `validate_worlds_after6` | 52.77 s | 6.85 → 5.53 | 7300 cases, 0 mismatches; stale total corrected, saved report passes |
| `validate_worlds_e` | 16.48 s | 5.53 → 5.41 | pass |
| `validate_worlds_after4` | 20.74 s | 5.41 → 6.32 | pass |
| `validate_render_effects` | 0.90 s | 5.41 → 5.38 | pass |
| `validate_render_effects3` | 0.86 s | 5.38 → 5.38 | pass |
| `validate_render_effects4` | 5.41 s | 5.38 → 5.35 | pass |
| `validate_render_effects5` | 4.68 s | 5.35 → 5.48 | pass |
| `validate_render_effects6` | 1.45 s | 5.48 → 5.48 | pass |
| `validate_render_effects7` | 1.63 s | 5.48 → 5.48 | pass |
| `validate_render_effects9` | 1.50 s | 5.48 → 6.32 | pass |
| `validate_render_effects10` | 0.48 s | 6.32 → 6.32 | pass |
| `validate_render_effects11` | 0.35 s | 6.32 → 6.32 | pass |
| `validate_combat` | 0.93 s | 6.32 → 6.32 | pass |
| `validate_skill_fx` | 1.19 s | 6.32 → 6.32 | pass |
| `validate_particles` | 0.89 s | 6.32 → 6.14 | pass |
| `validate_model_light` | 0.01 s | 6.32 → 6.32 | missing snapshot location; full rerun passed below |

`worlds_after6` already included a 1,000-case prime family, but its registry total still said 6,300. The total
now says 7,300. Rejudging the saved full report passes; no comparison, case input or family check changed.

### Selection replay and miss analysis

The replay uses the final 178-row registry and the same source tree for both algorithms, with PR-only new rows
added from that PR's manifest. In #295 this adds `validate_item_hiddenmesh`. Counts include helper rows.
The before rule is TEST-SPEED-001's directory/owning-test closure; the after rule uses declared build targets
and actual validator imports. PR file lists and head SHAs, both selected sets, removed-row reasons, declared
rows and all fifteen native rows' compiled-input provenance are saved in the JSON above. Historical gates
were not rerun. This compares selection rules, not the steward's smaller hand-picked lists.

| PR | Rows before → after | Miss audit |
|---|---:|---|
| #292 | 99 → 93 | 0 identified |
| #293 | 72 → 56 | 0 identified |
| #294 | 72 → 56 | 0 identified |
| #295 | 43 → 35 | 0 identified |
| #296 | 43 → 31 | 0 identified |
| #297 | 178 → 178 | 0 identified |

Removed rows were checked against their script/import inputs and compiled sources/includes. #292's declared
crypto, item-model, NPC-dialogue and protocol rows had no changed production input. The same four plus
worlds_after4 are removed from #296's broader historical list. Their earlier native-directory matches and
owning-test imports were over-selection. #293/#294 retain their app-polish rows; meshdraw, terrain and other
unrelated native consumers no longer inherit the whole native directory. The new hiddenmesh and effects12
rows remain selected. Zero required reruns were identified as missing in this audit. This is a bounded source
and recorded-result audit, not a proof about arbitrary future computed dependencies.

`build_targets` takes precedence over a row's directory-wide `build` dependency. It also limits the runner's
make invocation. Targets are derived from the artifacts consumed by the script; selection expands them with
`make -nB`, recursive includes, `.d` files and included make fragments. Failed dry runs retain directory-wide
fallbacks. Archive consumers remain broad. The owning test file triggers its row, but its unrelated imported
tests do not run inside that validator. Actual validator imports, including `native_fixtures`, still count.
Native Swift app sources and C test hosts are gate-owned unless explicitly referenced by a validator. Unknown
production inputs still select everything. #297 deliberately selects every row because it changes shared tooling.

No suite-selection narrowing was attempted. The native archive and uncertain computed dependencies remain;
the steward still runs the full batch gate. The shared module resolver now also recognizes native test helpers.

### Paste-ready commands

Before a heavy step, check load, free memory and disk as in the brief. Use the lane's own worktree.

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"

# Lane: inspect selection, then run only affected rows, without optional mutants.
tools/python/bin/python scripts/run_validators.py --list-affected origin/main
nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2 --report verify-runs/lane-validators

# Steward for TEST-SPEED-002: its only changed validator harness.
nice -n 10 tools/python/bin/python scripts/run_validators.py --private --no-mutants --cache --only validate_meshdraw --jobs 2 --report verify-runs/test-speed-002

# Tooling-lane exception used here; ordinary lanes still avoid a full gate.
MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=4 nice -n 10 tools/python/bin/python scripts/run_test_suites.py
```

For steward selection, use `--list-affected <last-tested-ref>` and the row's `build_targets` provenance rather
than matching every changed path against the word `native` in `build`. Keep the brief's explicit lane validator
list for shared tooling changes. The selector is conservative and shared infrastructure intentionally selects all.

### Delivery checks

| Check | Result | Wall | Load 1m |
|---|---|---:|---|
| Initial build | pass | 17.28 s | 5.57 → 27.62 |
| Build after main integration | pass | 13.54 s | 4.84 → 13.82 |
| Initial budget tests | 38 pass | 11.72 s | 13.25 → 11.42 |
| Initial cache/runner/manifest tests | 29 pass | 3.01 s | 8.26 → 8.26 |
| Expanded targeted check | 71 pass; one fixture assertion corrected below | 21.21 s | 11.69 → 10.36 |
| Focused assertion recheck | 1 pass | 0.15 s | 8.92 → 8.92 |
| Production name-parser C mutant | 44/4038 mismatches; 8076 hits, zero misses | 1.24 s | 10.87 → 10.87 |
| Full gate, all suites, `MU_GATE_JOBS=4`, at `5eea9e47` | 38 suites, 1,939 tests: 1,687 pass, 252 skip, 0 fail | 190.6 s | 10.50 → 20.23 |
| Repository audit, docs staged | 1,884 staged files, 0 rejected | 15.7 s | 6.52 → 5.88 |

The full gate includes `tests/`: 234 tests in 25.1 s, among them every `test_test_budget`, `test_validator_original_cache` and `test_validators_manifest` case.

## TEST-SPEED-003: multi-key cache and self-built suite libraries

[Handoff](../handoffs/TEST-SPEED-003.md).

**Cache thrash.** Until now `original_cache` kept one key per name and deleted the others on every save. A lane
branch and the steward's main with different harness versions (a changed `gen_item_bodies.py`, say) evicted each
other on every switch, so `validate_item_clusters`/`gear`/`wings_next` ran cold again (+300–650 s each, seen by
RENDER-ITEMS-HIDDENMESH). Now:

- **Per name:** the 4 most recently used keys stay (`MU_VALIDATOR_CACHE_KEYS`). Loading a key marks it used by
  touching its mtime.
- **Whole directory:** capped at 250 MB (`MU_VALIDATOR_CACHE_MAX_MB`). Least recently used files go first; the file
  just written is never removed. Writer temp files older than 6 h are removed.
- **Keys:** unchanged in content (format, validator, Python and Unicorn versions, every pin's sha256, the harness
  code closure, `extra`). A file is returned only for the key stored inside it; a renamed or damaged file is a miss.
- **Concurrent writers:** a save holds a per-name `flock` and merges what another worker saved under the same key
  since this one loaded (two `--jobs` workers both filling `gen_item_bodies`). The file is replaced atomically, so
  a reader sees the old or the new file, never a partial one. The old code lost one worker's entries in 3 of 3
  test runs.
- **Migration:** in place. Same paths and file format, so the existing shared directory stays valid. Worktrees
  still on the old code keep deleting other keys of a name when they save, until they merge main.
- **One-time cost:** `original_cache.py` is in the closure of every cached validator, so this PR is a new key for
  each of them, and each row is cold once after the merge.

Measured on `validate_item_product` (2,874 cases: bodies 1,752, products 1,122; 0 mismatches), `--no-mutants`,
`--jobs 2`, `nice -n 10`, with a scratch cache directory (the shared one was in use) at `dacc64f2`. "Branch" is
main plus one comment line in `scripts/gen_item_bodies.py`, which gives a new generator key.

| Run | Wall | Generator cache | Load 1m start → end |
|---|---:|---|---|
| main, cold | 586.16 s | 24,708 hits, 91,272 misses | 9.61 → 5.15 |
| main, warm | 33.67 s | 115,980 hits, 0 misses | 4.90 → 4.36 |
| branch, cold (the old code deleted main's key here) | 605.45 s | 24,708 hits, 91,272 misses | 4.15 → 9.43 |
| main again | **35.88 s** (old code: cold, ~586 s) | 115,980 hits, 0 misses | → 7.57 |
| branch again | **37.29 s** (old code: cold, ~605 s) | 115,980 hits, 0 misses | → 6.36 |
| main again | **34.39 s** (old code: cold, ~586 s) | 115,980 hits, 0 misses | 6.36 → 5.78 |

All six reports are byte-identical (sha256 `b2bad7fe8465d3b716b1cce4901790b044491cd59ff2a2b07866f5918eb92b3a`).
The three switches took 107.6 s; with the old code they would have been three cold runs, about 1,777 s by the
cold walls above. Those "old code" figures are estimates from the measured cold walls, not new runs: the old save
provably deletes the other key (the replaced unit assertion). The scratch directory held two generator keys:
3.1 MB.

**`test_joints` build dependency.** `reconstructed/joints/test_joints.py` loads `reconstructed/combat/libcombat`
but built only its own directory. It passed only when another suite had built combat first, so in a fresh
worktree `--affected` errored (RENDER-WORLDS-S2). The test now runs `make -C reconstructed/combat` first, as
`test_items` and `test_worlds_o`/`q`/`g2` already do. `test_native_character`'s private test had the same gap
for `reconstructed/model-codec/libcharacter` and gets the same one-line build. No check changed.
`tests/test_test_budget.py::SuitesBuildWhatTheyLink` statically requires every `reconstructed/*` and
`native/tests` test module that loads another directory's library to build that directory too.

Proof: with `libcombat.dylib` removed, `run_test_suites.py reconstructed/joints` failed with 1 error before the
fix, and after it passed (15 tests, 1 skipped, 1.5 s).

### Delivery checks

| Check | Result | Wall | Load 1m |
|---|---|---:|---|
| `test_test_budget` + `test_validator_original_cache` (incl. 8 new tests) | 54 pass | 21.6 s | 9.59 → 11.83 |
| New cache tests against the old `original_cache.py` | 3 fail, 3 error, as intended (concurrency lost entries 3/3) | 0.1 s | — |
| `make -j4` before / after merging main `b8645181` | pass | 24.5 s / 14.9 s | 8.12 → 11.11 / → 17.11 |
| Full suites, `MU_GATE_JOBS=4`, `nice -n 10`, at the merge | 38 suites, 1,973 tests: 1,716 pass, 257 skip, 0 fail | 198.0 s | 12.54 → 26.87 |
| Item row cold / warm (above) | identical reports | 586.16 s / 33.67 s | above |
| Repository audit, docs staged | 1,925 staged files, 0 rejected | 16.7 s | 16.27 → 13.13 |

## TEST-SPEED-004: each row's exact inputs

[Handoff](../handoffs/TEST-SPEED-004.md), [replay spec](test-speed-004-spec.json),
[replay result: every case's lists, first reason per row, removed rows' old reasons, row weights](test-speed-004-selection.json).

`--list-affected` used to select far too much (APP-POLISH-004: all 184 rows for one test-only helper; batch 38:
all 179 because the diff contained the selector; batch 45: 42 flagged, 26 needed), so lanes and the steward
picked rows by hand with `make -n -W`, include checks and script reading. That hand work is now the tool.

**A validator row is affected iff the diff touches one of its derived inputs** (`run_validators.row_deps`):

- **Python**: its script and every repository module it imports. That includes modules found through the
  `sys.path` directories the code adds, modules loaded with `importlib` whose names come from constants or from
  every call site of a local wrapper, and Python scripts it runs. The repository paths the code builds count
  too. Paths are folded from the code: `ROOT / 'reconstructed' / d` with `d` from a constant loop or
  assignment, and function parameters from every call site in the closure, including another module's
  `v.build_library(ROOT / 'reconstructed')`. Each directory is classified by its use:
  `make -C D [targets]` → those targets' compiled inputs; `-I D` → the headers the compiled sources (and C text
  written from Python strings) include; `D.glob('quest_*.c')` → the matches; `sys.path` → imports only;
  `.exists()`/`mkdir` → nothing; anything else → every file under D except `test_*.py`/`*.md`. A bare word is no
  longer a path: the Unicorn region name `'objects'` in validate_joints/skill_fx/render_effects* used to
  select them for every reconstructed/objects change. Quoted file names (`'renderchar.c'`) still match by
  base name.
- **Compiled**: per make target (the row's `build_targets`, its build directories' default goals, and every
  `make -C` its code runs), every file the full dry run `make -nB` compiles or reads. Headers come from the
  target's `.d` file when it is newer than everything it lists, else from the compiler itself: one
  `cc -MM -MG` per flag set, on the dry run's own command line. A header under `#if 0` is not an input. A
  changed Makefile counts for a target only if that target's dry run with the base Makefile differs from the
  current one. A deleted source counts for every target that compiled files in its directory.
- **The row itself**: its script, its manifest row (compared with the base `validators.toml`), `pins.py` for
  a row with pins, the paths its `args`/`prepare` name. The owning unit test is **not** an input. It runs in
  the gate, not in the row.
- **Tooling** (`affected.TOOLING`: `affected.py`, `run_validators.py`, `run_test_suites.py`,
  `original_cache.py`, `guarded_run.py`, `replay_affected.py`) and `tests/`, `docs/` select **no row**. Their tests are
  the always-run `tests` suite (`test_test_budget`, `test_affected_inputs`, `test_validator_original_cache`,
  `test_validators_manifest`, `test_run_test_suites`) plus every test module that imports or names the file
  itself (test_native_app for `guarded_run.py`), not every test that reaches it through a validator.
- **No global fallback.** A path no row's inputs contain selects nothing. A row whose inputs cannot be derived
  (a module loaded from a computed name, a path built from an unknown value at the repository root, a file that
  does not parse) carries the reason. It is selected for every code change and listed at the end of
  `--list-affected` under "use the conservative fallback". **Current fallback rows: none.**
  `tests/test_affected_inputs.py` pins that set; it may only shrink.

`--affected-since REF` diffs REF itself (the lane-tested commit) against the working tree, which is the
steward's question; `--affected REF` diffs `merge-base(REF, HEAD)`, the lane's. Both runners take both.
Suites keep their TEST-SPEED-001 rules plus the Python analysis above, the Makefile dry-run comparison, and:
the tooling no longer selects every suite (only `tests` and the test modules naming it directly), and make
targets are named only by modules that run `make`. A computed path naming more than 8 targets of a make
directory (`NATIVE / 'build' / name`) stands for that whole directory instead of one dry run per target. The
steward keeps the full gate.

### Replay of #292–#308

`scripts/replay_affected.py docs/testing/test-speed-004-spec.json` checks out each tree into a temporary worktree.
It runs the previous selector (main `eb2a8e76`, TEST-SPEED-001/002/003) and this one in fresh processes on the
same tree and the same diff. Lane cases: the PR head against `merge-base(main before the merge, head)`, all
rows. Steward cases: the merged commit against each lane-tested commit named in the PR body or the steward log
(rows tested at a different commit are their own group). They are limited to the PR's `Steward validators:`
rows, because the steward's question is which of those must run again. "Measured s" is the serial sum of the
rows' recorded no-mutant walls (steward log batches 32–46, the tables above). A few rows have no recorded wall
and add nothing, so it is a lower bound.

| PR | Lane `--affected`: rows before → after (measured s) | Steward `--affected-since`: rows before → after | Steward ran | Misses |
|---|---|---|---|---|
| #292 | 95 → **66** (5,184 → 5,180) | 0 → **0** of 40 | 40 | 0 |
| #293 | 59 → **4** (875 → 53) | 1 → **1** of 1 | 1 | 0 |
| #294 | 59 → **4** (855 → 34) | 0 → **0** of 1 | 2 | 0 |
| #296 | 36 → **51** (829 → 914) | 28 → **26** of 31 | 1 | 0 |
| #297 | 178 → **22** (5,205 → 4,278) | 0 → **0** of 13 | 0 | 0 |
| #298 | 67 → **24** (882 → 687) | 3 → **0** of 3 | 3 | 0 |
| #299 | 178 → **16** (5,205 → 736) | 1 → **1** of 1 | 2 | 0 |
| #300 | 60 → **65** (5,166 → 5,162) | 45 → **27** of 45 | 11 | 0 |
| #301 | 68 → **52** (984 → 908); lane ran 11, all selected | 0 → **0** of 11 | 0 | 0 |
| #302 | 69 → **54** (984 → 927); lane ran 10, all selected | 0 → **0** of 10 | 0 | 0 |
| #295 | 36 → **42** (4,916 → 4,935) | 23 → **15** of 27 | 2 | 0 |
| #303 | 70 → **55** (984 → 927); lane ran 8, all selected | 1 → **1** of 8 | 1 | 0 |
| #304 | 0 → **0** (0 → 0) | 0 → **0** of 0 | 0 | 0 |
| #305 | 36 → **1** (4,439 → 19) | 0 → **0** of 0 | 0 | 0 |
| #306 | 62 → **67** (5,166 → 5,162) | 57 → **26** of 61 | 26 | 0 |
| #307 | 185 → **38** (5,238 → 704); lane ran 4, all selected | 4 → **2** of 4 | 1 | 0 |
| #308 | 73 → **58** (1,016 → 960); lane ran 6, all selected | 6 → **0** of 6 | 0 | 0 |
| **Sum** | 1331 → **619** (47,927 → 31,586) | 169 → **99** (11,340 s → 6,862 s) | 90 | 0 |

| Recorded failure | Case | Must select | Rows before → after | Suites before → after | Caught |
|---|---|---|---|---|---|
| #287: steward batch 27: worlds_l_host.c:69 / worlds_m_host.c:75 asserts after MU_WORLD_PT_BITMAPS grew | lane `724ad10a` | test_native_worlds_l.py, test_native_worlds_m.py | 55 → 61 | 156 → 156 | yes |
| #282: INTEGRATION-GREEN-002: renderchar continuation/gear/scalars stale assertions, item-texture survey, validate_renderchar | lane `852261fe` | renderchar, test_native_item_textures.py, validate_renderchar | 169 → 38 | 153 → 153 | yes |
| #283: TEST-SPEED-001 audit: test_native_particles | lane `e4fefcf2` | test_native_particles.py | 54 → 59 | 154 → 154 | yes |
| #280: TEST-SPEED-001 audit: test_native_audio | lane `39561c9f` | test_native_audio.py | 68 → 31 | 152 → 152 | yes |
| #260: steward batch 2: Q swamp_darkness.c and R2 swamp_destruction.c both define mu_swamp_* (link failure of reconstructed/objects) | since `72077f1a` | validate_worlds_q, validate_worlds_r2 | 155 → 72 | — | yes |

**Misses: zero.** Every recorded failure's unit is selected. Every row the steward actually ran is selected,
except where the replay shows its inputs did not change:

- #292: the 40 rows were run because the handoff named no tested rows. `03bec39b → 9e93e6c9` changes only docs
  and `test_native_particles.py`.
- #294: the 2 rows were run "per batch instruction". `7c6bd1ba → 2531746f` changes only docs.
- #298: polish1/polish2/gfx3. The chain merge brought #297's item harness and tooling, which they do not import.
- #296: render_effects12, a new row run as a cheap confirmation; nothing it reads changed after `c76a168f`.
- #299: worlds_after6's registry row was edited by #299 itself; the lane case selects it ("its row changed").

**New selects more in 13 lane cases**, all real compiled inputs the previous selector missed.
validate_path, terrain_remaining, worlds_f, movement and session_party run `make -C native build/mu-path |
mu-terrain | mu-session` from their scripts, and those link libmunative.a, which compiles `mu_combat.c`,
`mu_objects_runtime.c` and `mu_item_textures.c`. validate_items/worlds_k/icarus/joints build libcombat,
which includes `arrow_fx.inc`/`bow_fx.inc`/`bow_joints.inc`. validate_model_light loads validate_skinning
(and through it pose_builder, bone_tracks) with `importlib` and an f-string path; the old closure missed all
three.

**Where it still selects more than the steward did by hand: symbol-level judgment, kept out on purpose.**
#295 (15 vs 2), #296 (26 vs 1), #300 (27 vs 11): the item rows load `libclient_particles` (every particles
source), and libcombat compiles `../joints`. The steward skipped them by reading which functions the
validators call (batch 41: only `mu_pt_transform_position`, in the unchanged `shadow.c`). The tool stays at the
target level, because a change to any linked source can break the link for every consumer whatever it calls.
#260's duplicate `mu_swamp_*` symbols (Q and R2) were exactly that, and symbol pruning would have missed it.
For #306 the tool's 26 rows are the steward's 26.

Symbol-level pruning would save the most in lanes: the 11 item rows (~3,600 s measured) for every particles
change, terrain/model_edge/meshdraw for every libmunative change. It needs a per-target check that no
duplicate or undefined symbol appears, and a sound map from Python attribute names to the exports. That is
the next step, not this one.

### Costs, compatibility and limits

- **Selection time.** The validator selection takes 15–30 s on a cold tree (dry runs, `-MM`, AST analysis)
  against 2–7 s before. Lane suite selection takes 40–110 s, about 40 s more than before, because every
  `native/tests` module's closure now follows real make uses. That is small next to one avoided row.
- **The `tests` suite** (always run) grew: test_test_budget + test_affected_inputs take 31 s in one process,
  against 11.7 s for test_test_budget on main.
- **Cache keys.** `original_cache.code_hash` hashes the closure that `python_deps` returns. The old closure
  contained `affected.py`, so this PR changes every cached row's key either way: **each cached row is cold once
  after the merge.** The new closure no longer contains the selector (tooling is recorded, never followed). It
  does contain the modules the old one missed (model-recovery readers for the item harness), so later selector
  changes no longer cool the cache.
- **`original_cache` read race fixed.** `Cache.__init__` read the file, then stat-ed it. A save by the other
  `--jobs` worker in between made `seen` describe entries it never loaded, and its next save dropped that
  worker's round (`test_concurrent_writers…`: 600 ≠ 640 under load, once in 4 runs here). The reader now
  `fstat`s the file object it read. No key, format or check changed.
- **Static analysis is not a proof.** A path read from a JSON file or an environment variable, or a module named
  by data, is invisible. Such code shows up as a fallback only when the analysis sees the computation, not when
  it sees nothing. Imports no search path resolves fall back to every repository module of that name.
- A name rebound in the same function with an unknown value (icarus_c2's `folder = file.split('/')[0]`) makes
  its paths patterns (`reconstructed/*`). That is conservative, not exact.

## TEST-SPEED-005: symbol-level use of shared libraries

[Handoff](../handoffs/TEST-SPEED-005.md), [replay spec](test-speed-005-spec.json),
[replay result: every case's lists, first reason per row (trimmed), symbol fallback and pruned rows](test-speed-005-selection.json).

The first real uses of TEST-SPEED-004 over-selected through shared libraries. Batch 55: `--list-affected-since
121f24f7` picked all 31 rows of #316 where the steward's make/include/symbol analysis needed 12. Every row that
loads `libclient_particles` was flagged because `particles.c` changed, although #313 only added effect cases and
those rows call only `mu_pt_transform_position` and `mu_pt_rand`. validate_item_hiddenmesh was flagged because an
imported module names libcombat as an argparse default inside its `main()`. RENDER-WORLDS-SLOTS3 (#319): about
70 rows through the shared library; the lane ran 5. The steward and the lanes dropped rows by hand, by reading
which functions the scripts call. That reading is now the tool (`scripts/affected_symbols.py`).

**A C source or header that is an input only because a make target the row builds compiles it** (no other
route names it: not a Python-compiled copy outside mutant code, not a quoted name, directory, glob or `-I` use)
**selects the row only if the row names an exported symbol of that target that the diff changed.**

- **Changed symbols** (`affected_symbols.analyze`, per linked artifact of the target's `make -nB` dry run).
  Every unit the artifact links is compiled to LLVM IR twice with the dry run's own flags
  (`-S -emit-llvm -O0 -g0 -w`): on the working tree, and on the base commit through a clang VFS overlay that
  serves the base content of each changed file. Units whose `-MM` inputs contain no changed file are compiled
  once. Each function and global is a node with a fingerprint: its IR without metadata, attribute groups and
  comments, with anonymous constants (`.str.N`, `__const.f.v`, function-local statics) replaced by their content,
  plus the layout of every struct type it mentions. Edges are the symbols a node references (calls,
  address-taken functions, tables), resolved inside the artifact. An export is changed when a changed node is
  reachable from it: a changed static or inline callee counts for every export that calls it, a changed
  constant table for the functions that read it, a struct layout change for every function touching the
  struct (directly or through callees). `main` and constructors are reachable from every user: an executable
  run by the row is selected when its `main` reaches the change.
- **Global data counts for every user**: a changed, added or removed mutable global (a file-scope or
  function-local static, or an exported variable) selects every row of the target, as a symbol fallback.
- **The link**: a strong definition that appears twice in an artifact where it did not before (steward batch 2's
  duplicate `mu_swamp_*`, #260), or a new reference that neither the artifact nor libSystem defines, selects
  every row. So does a unit that does not compile to IR on either side, a dry run the analysis cannot map
  (prebuilt objects or archives, repository libraries on the link line, `-undefined`/`-flat_namespace`, shell
  globs in a link), and a target without a dry run.
- **Symbols a row uses** (Python closure): every identifier and attribute, every word of a string or bytes
  constant (C text written from Python, `dlsym` names, `argtypes` tables), and every name a string-building
  expression can produce (`'mu_' + name`, f-strings, `%`, `.format`). An unknown part of a built name can only
  be filled with the code's own word pieces (split at `_` and digits, any case): `'mu_' + name` over a dict of
  bodies reaches `mu_acheron_create`, but not `mu_obj_visual_flicker` unless "obj", "visual" and "flicker" all
  occur in the row's code. A `getattr`/`hasattr`/`in_dll` whose name is built right there from parts that
  cannot be bounded (`getattr(lib, a + b)`) makes the row use every export (symbol fallback, reported per row:
  validate_worlds_r2 today). A lookup by a plain variable takes a name the program holds as a string (counted
  where it is written or built) or reads from data (not visible, the same limit as a path read from a file).
- **Mutant-only code** (functions named `*mutant*`/`*mutation*`, `if args.mutations:` blocks): mutant builds
  compile copies of the same sources with a planted change and the row calls the same symbols on them. Their
  path uses are still inputs (reported as `mutant build: ...`), but they do not stop the pruning of a file a
  make target of the row compiles, unless the link structure changed (a new unit, or a unit newly calling into
  another one: hand-written mutant source lists might no longer link), which is a symbol fallback.
- **`main()`-only code of an imported module** (inside a module-level `def main` or
  `if __name__ == '__main__':`) is not an input of a row that never calls that `main`: its path uses, call sites
  and names are left out. A module run as a program (the row's script, a script it runs or loads by path) and a
  module whose `main` some closure module calls or references (`m.main`, `from m import main`) keep it.
  validate_item_hiddenmesh no longer builds libcombat through validate_combat's `--library` default.
- **Globs skip unit tests and docs** like directories do: `reconstructed/particles/*` (a computed path) no
  longer matches `test_particles.py` or `README.md`; a pattern that names them (`tests/test_*.py`) still does.
  A path joined with an unknown name and handed to a library loader (`ctypes.CDLL(str(ROOT / directory /
  target))`) uses the libraries that directory's Makefile builds, not every file in it.

`run_validators.affected_rows(..., symbols=True)` (both runners' `--affected`/`--affected-since` for validator
rows) applies this; `symbols=False` gives the TEST-SPEED-004 input-level answer, which test_test_budget keeps
testing. Suites (`run_test_suites.py --affected`) keep the input-level selection: the native test hosts compile
their own C, and the steward keeps the full gate. The analysis runs only for a row nothing else selects, so a
row already selected through Python or a non-library route costs nothing extra; analyses are cached per target
and per unit in the process (batch 55's 31 rows: 18.9 s, against 16.1 s with TEST-SPEED-004).

### Replay of #295–#320

`scripts/replay_affected.py docs/testing/test-speed-005-spec.json` (82 min, nice 10, load 7–19) runs the
TEST-SPEED-004 selector (main `3ecc205c`) and this one in fresh processes on each historical tree, as
TEST-SPEED-004's replay did; it now also generates `native/build/gen` in each tree (Python generators only) so
native units compile to IR as after a lane's `make`. Lane cases: the PR head against the main it merged into,
all rows. Steward cases: the merged commit against each lane-tested commit (PR bodies, steward log batches
32–58), limited to the PR's `Steward validators:` rows. "Measured s" is the serial sum of the rows' recorded
no-mutant walls (TEST-SPEED-004's weights); rows without one add nothing.

| PR | Lane `--affected`: rows TEST-SPEED-004 → 005 (measured s) | Steward `--affected-since`: rows 004 → 005 | Steward ran | Misses | Symbol fallback rows (005) |
|---|---|---|---|---|---|
| #295 | 42 → **33** (4,935 → 4,551) | 15 → **2** of 27 | 2 | 0 | 1: movement |
| #296 | 51 → **37** (914 → 809) | 26 → **25** of 31 | 1 | 0 (steward ran, not selected: render_effects12) | 13 |
| #297 | 22 → **22** (4,278 → 4,278) | 0 → **0** of 13 | 0 | 0 | 0 |
| #298 | 24 → **24** (687 → 687) | 0 → **0** of 3 | 3 | 0 (steward ran, not selected: app_polish1, app_polish2, gfx3) | 0 |
| #299 | 16 → **16** (736 → 736) | 1 → **1** of 1 | 2 | 0 (steward ran, not selected: worlds_after6) | 0 |
| #300 | 65 → **42** (5,162 → 875) | 27 → **27** of 45 | 11 | 0 | 1: movement |
| #301 | 52 → **52** (908 → 908); lane ran 11, all selected | 0 → **0** of 11 | 0 | 0 | 0 |
| #302 | 54 → **54** (927 → 927); lane ran 10, all selected | 0 → **0** of 10 | 0 | 0 | 0 |
| #303 | 55 → **55** (927 → 927); lane ran 8, all selected | 1 → **1** of 8 | 1 | 0 | 0 |
| #304 | 0 → **0** (0 → 0) | 0 → **0** of 183 | 0 | 0 | 0 |
| #305 | 1 → **0** (19 → 0) | 0 → **0** of 183 | 0 | 0 | 0 |
| #306 | 67 → **43** (5,162 → 875) | 26 → **26** of 61 | 26 | 0 | 1: movement |
| #307 | 38 → **30** (704 → 321); lane ran 4, all selected | 2 → **1** of 4 | 1 | 0 | 1: movement |
| #308 | 58 → **50** (960 → 855); lane ran 6, all selected | 0 → **0** of 6 | 0 | 0 | 2: movement, worlds_g2 |
| #309 | 52 → **30** (897 → 432) | 17 → **1** of 32 | 1 | 0 | 1: movement |
| #310 | 43 → **34** (4,916 → 4,532) | 9 → **7** of 25 | 7 | 0 | 1: movement |
| #311 | 56 → **48** (908 → 803) | 5 → **1** of 6 | 0 | 0 | 27 |
| #312 | 0 → **0** (0 → 0) | — | — | 0 | 0 |
| #313 | 73 → **41** (5,195 → 542) | 19 → **15** of 44 | 18 | validate_audio_charsel, validate_audio_combat, validate_viewport_monsters (steward ran, not selected: audio_charsel, audio_combat, viewport_monsters) | 4: audio_combat, movement, render_worlds_a, worlds_d |
| #314 | 34 → **34** (669 → 669) | 0 → **0** of 2 | 0 | 0 | 0 |
| #315 | 0 → **0** (0 → 0) | — | — | 0 | 0 |
| #316 | 48 → **39** (4,967 → 4,583) | 31 → **12** of 31 | 12 | 0 | 1: movement |
| #317 | 0 → **0** (0 → 0) | — | — | 0 | 0 |
| #318 | 0 → **0** (0 → 0) | — | — | 0 | 0 |
| #319 | 96 → **54** (5,197 → 836); lane ran 5, all selected | 0 → **0** of 5 | 0 | 0 | 2: movement, worlds_r2 |
| #320 | 9 → **9** (85 → 85) | 6 → **6** of 9 | 6 | 0 | 0 |
| **Sum** | 956 → **747** (49,153 → 29,231) | 185 → **125** | 91 | | |

| Recorded failure | Case | Must select | Rows 004 → 005 | Suites 004 → 005 | Caught |
|---|---|---|---|---|---|
| #287 | lane `724ad10a` | test_native_worlds_l.py, test_native_worlds_m.py | 61 → 40 | 156 → 156 | yes |
| #282 | lane `852261fe` | validate_renderchar, renderchar, test_native_item_textures.py | 38 → 34 | 153 → 153 | yes |
| #283 | lane `e4fefcf2` | test_native_particles.py | 59 → 43 | 154 → 154 | yes |
| #280 | lane `39561c9f` | test_native_audio.py | 31 → 31 | 152 → 152 | yes |
| #260 | since `72077f1a` | validate_worlds_q, validate_worlds_r2 | 72 → 69 | — | yes |

**Lane: 956 → 747 rows, measured 49,153 → 29,231 s. Steward: 185 → 125 rows.** The shared-library PRs dropped
the most: #313 73 → 41 (5,195 → 542 s), #300 and #306 65/67 → 42/43 (5,162 → 875 s: the item rows no longer
follow every particles change), #319 96 → 54, #309 52 → 30; steward #309 17 → 1, #316 31 → 12 (exactly the
steward's 12), #295 15 → 2, #311 5 → 1. Every lane-ran row is still selected (#301, #302, #303, #307, #308,
#319).

**Misses against recorded failures and the steward's needed rows: zero**, with one case to read:

- #287 (worlds_l/m host asserts after `MU_WORLD_PT_BITMAPS` grew), #282, #283, #280: the suites are unchanged
  (suites keep the input-level selection) and all four are still caught. #260's duplicate `mu_swamp_*`:
  validate_worlds_q and worlds_r2 are selected through the link check.
- #313: the steward ran 18 rows on make-level grounds (`make -n -W core/mu_objects_runtime.c` rebuilds
  libmunative.a). Three of them (audio_charsel, audio_combat, viewport_monsters) are not selected now. Checked
  at the merged tree `9e1a0ce6`: none of the 6 / 43 / 16 libmunative exports they use (Python names plus the
  hosts they compile; viewport_monsters.c is itself an archive member) reaches a changed function. #313's
  changes are the slot classes, login/charsel object frames and `mu_obj_visual_flicker`. The other 15 are
  selected. These are rows a make-level rule needed and a symbol-level rule does not; they are recorded in the
  spec's `must_rows` and listed here rather than hidden.
- Not selected by either selector, as in TEST-SPEED-004: #296 render_effects12, #298 polish1/2/gfx3, #299
  worlds_after6 (inputs unchanged since the tested commit; see the TEST-SPEED-004 notes).

**Symbol fallback rows** are listed per case in the JSON. Almost all come from one native link line,
`build/mu-shell` (in the native default goal: validate_movement in most cases, 25 rows at #296), which links
`build/shell/*.o` through a shell glob the analysis does not expand; then mutant copies after a new unit
(#311's `world_slots2_visual.c`: 26 rows; #308, #313), global data (#260: librenderchar), one C host that does
not compile without its build flags (#313 mu_image.c) and validate_worlds_r2's unbounded lookup. Expanding
shell globs against the dry run's objects is the next cheap step.

**Suites** change only through the `main()`-only rule and the glob rule: `test_render_time_live.py` no longer
follows `render_time.main`'s `--binary` default (`native/build/mu-world`; the test runs render_time_live,
which never calls render_time.main), and test_native_social / test_native_icarus no longer select on other
`test_*.py` files through computed `native/*` / `reconstructed/*` paths. 17 lane cases lose one suite.

### Limits

- **Built headers.** Native units include generated headers (`native/build/gen`). Run the selection after
  `make`; in an unbuilt tree those units do not compile to IR and their targets are a symbol fallback (the
  replay generates `build/gen` with the Python generators, nothing compiled).
- **Shell globs in link lines** (`build/shell/*.o`) are not expanded: those targets are a symbol fallback.
- **Python imports stay whole-module.** A changed harness module (`scripts/validate_particles.py` in #319)
  selects every row importing it; function-level Python pruning is not part of this.
- **C that loads libraries at run time**: `dlopen`/`dlsym` from repository C reach only external libraries
  today (libmugfx); a repository library loaded that way by another target's code would need its loader's
  strings as roots.
- **Names from data**: a symbol name read from a file or the environment and looked up through a plain
  variable is not visible (as for data paths).
- **Mutant anchors**: a mutant run asserts that its text anchor occurs once. An edit elsewhere in a source can
  duplicate an anchor (RENDER-EFFECTS-017's `mark_abs` ×3). That breaks only mutant runs, which are chosen by
  hand per brief item 2, never by `--affected` (which runs `--no-mutants`).
