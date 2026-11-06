# Test budget: what runs when (TEST-SPEED-001 / 002 / 003)

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
| `run_validators.py` | `--no-mutants` | Removes the mutant switches from each row's arguments (`--mutations`, `--mutants`, and with them `--mutant-cases N`/`--mutation-cases N`) and drops the expectations that read mutant results (the row's `mutants_at` paths and every path naming mutants, mutations or negative controls). At replay base 90e11d71, the registry has 115 rows with a removable switch. `--mutations N` with a number (effects, effect_tree, meshdraw) is a count of random input cases, not planted mistakes, and stays; 16 rows have negative controls built into every run and are unchanged. The summary says how many rows ran without mutants; `--index` refuses such a summary (the evidence index records mutant counts). |
| `run_validators.py` | `--affected REF` / `--list-affected REF` | Rows a diff from `merge-base(REF, HEAD)` to the working tree (commits, staged, unstaged, untracked) can affect, with the reason for each. |
| `run_validators.py` | `--cache [DIR]` / `--no-cache` | Reuse original-instruction results (below). Default DIR `~/Documents/MTM/mu-mac-tools/native/cache/validators`. |
| `run_validators.py` | (always) | Wall times in `verify-runs/validator-times.json` (ignored); `--jobs N` starts the longest rows first, unknown rows first of all. |
| `run_test_suites.py` | `--affected REF` / `--list-affected REF` | Work items (suites; `native/tests` per module) a diff can affect, with the reason for each. Lanes only: the steward keeps the full gate. |

### How `--affected` maps a diff (scripts/affected.py)

It may select too much, never knowingly too little:

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
