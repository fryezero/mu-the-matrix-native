# TEST-SPEED-001

Tooling for the TEST BUDGET rules (brief, 2026-11-04): lanes run only what their diff can affect, without mutants
unless they changed the mutant targets, and validators reuse the pinned original's results. Branch
`claude/test-speed-001` from main `5cb6fa6d`. What to run and how the mapping works:
[docs/testing/TEST-BUDGET.md](../testing/TEST-BUDGET.md).

## What changed

- `scripts/run_validators.py`: `--no-mutants`, `--affected REF`, `--list-affected REF`, `--cache [DIR]`,
  `--no-cache`; per-row wall times in `verify-runs/validator-times.json` and longest-first under `--jobs`;
  `--recheck` of a `--no-mutants` report judges it without mutants; `--index` refuses a `--no-mutants` summary.
- `scripts/run_test_suites.py`: `--affected REF`, `--list-affected REF` (lanes; the steward keeps the full gate).
- `scripts/affected.py` (new): the diff → validator row / work item mapping both runners use.
- `scripts/original_cache.py` (new): the opt-in original-instruction cache, wired into the shared item harness
  (`gen_item_bodies._original`, `validate_item_clusters.body_cases`/`link_cases`, `validate_item_continuation.skin_cases`,
  `validate_item_ranked.link_cases`). `validate_item_clusters.link_cases`' original side moved into
  `client_link()` unchanged.
- `tests/test_test_budget.py` (new, portable, in the `tests` suite).

## Where the validator time went (measured)

`validate_item_continuation` under cProfile (no mutants, 1,091 s profiled): 966 s (89%) in
`gen_item_bodies.generate()`, the "body table drifted" check that refits the whole body table from the pinned
original (1,194 fits, 111,372 Unicorn samples) on every run; 106 s in the body cases' own Unicorn runs; the C side, skins,
links and Python overhead are the rest. Unicorn `emu_start` is 992 s of the total, Python hook callbacks inside it
~240 s. Mutants add 148 s to continuation (867.7 − 719.9). The same `generate()` call sits in 12 validators
(continuation, ranked, expansion, clusters, chains, next, gear, coverage, scalars, carry, wings_next, quality),
which is why each of them takes 11–15 minutes. The generator also calls the C library's generic path, so the
whole `generate()` result cannot be cached; only its Unicorn sample is (with what the sample's hooks record), and
the fit against the C stream runs every time.

## Timings (this Mac, `nice -n 10`, other lanes running; load 3–23)

| Check | Before | After | How |
|---|---|---|---|
| `validate_item_continuation` (25,772 cases, 9 mutants) | 867.7 s (mutants, no cache) | 719.9 s `--no-mutants` cold cache · **23.1 s** `--no-mutants` warm · 30.1 s mutants warm | reports byte-identical; warm mutant run catches all 9 with the same counts |
| `validate_item_ranked` (17,736 cases, 6 mutants) | 687.5 s | 97.3 s first `--cache` run (generator cache already warm) · **27.2 s** mutants warm · 23.3 s `--no-mutants` warm | byte-identical |
| `validate_item_expansion` (52,172 cases, 7 mutants) | 822.4 s | 228.4 s first `--cache` run · **30.0 s** mutants warm · 23.1 s `--no-mutants` warm | byte-identical |
| Other 9 rows sharing the generator (clusters, chains, next, gear, coverage, scalars, carry, wings_next, quality) | ~11–15 min each (same 800–960 s generator) | {{OTHER_ITEM}} | first `--cache` run, generator cache warm |
| Validator rows a lane reruns | all nearby rows, with mutants | `--affected`: 0–94 of 170 rows on the last 12 merged PRs (median 62), without mutants | selection only, below |
| `make test` work items a lane runs | 154 items, 321 s serial (orchestrator's measurement) | `--affected`: {{SUITES}} | estimate from recorded per-item times |
| Full gate (`local-macos-ci.sh`) | {{GATE_BEFORE}} | {{GATE_AFTER}} | steward only |


## Checks

{{CHECKS}}

## Limits

- `--affected` is conservative and the native library is one big link: a reconstructed or `native/core` C change
  still selects ~110 of the 118 `native/tests` modules and 40–95 validator rows (measured on the last 12 merged
  PRs below). The selection helps most for Python, docs, app/viewer, test-host and single-module changes.
- Imports or paths a script builds at run time from unquoted pieces are invisible to the mapping; inputs read
  through environment variables are local and never in a diff.
- The cache is wired into the item family only (the 12 slowest rows found). Other validators run uncached until
  their original-side call is wrapped (pattern in TEST-BUDGET.md). The cache lives outside the repository
  (`~/Documents/MTM/mu-mac-tools/native/cache/validators`, ~10 MB for the item family) and is not shared between
  machines.
- The steward's gate is unchanged (full gate per batch).

Steward validators: validate_item_continuation, validate_item_ranked, validate_item_expansion (their scripts or
harness changed; no expectations changed; mutants not required: the runs above already passed them).
Env: as in [INTEGRATION-GREEN-002](INTEGRATION-GREEN-002.md#environment).

## Local files

`~/Documents/MTM/mu-mac-tools/native/cache/validators/` (the warm cache, kept: it is the point of the change;
delete freely, it rebuilds). Scratch `native/scratch/test-speed-001/` deleted at the end.

## WIP (stopped by owner, 2026-11-04 ~14:55)

Done: `run_validators.py --no-mutants`, `--affected/--list-affected`, `--cache/--no-cache`, validator wall times +
longest-first; `run_test_suites.py --affected/--list-affected`; `scripts/affected.py`, `scripts/original_cache.py`
(item harness wired); `tests/test_test_budget.py` (30 tests pass). Measured (byte-identical reports in every case):
continuation 867.7 s → 719.9 s no-mutants cold → 23.1 s no-mutants warm / 30.1 s mutants warm; ranked 687.5 s →
97.3 s first cached → 27.2 s warm; expansion 822.4 s → 228.4 s → 30.0 s warm. `--affected` on the last 12 PRs:
suites 1–98% of serial time (median 96%), validators 0–103 rows (median 57).
Next: finish the handful-of-rows mutants vs --no-mutants comparison (was running, killed), the other 9 item rows with
--cache, perf004 gate analysis (needs native build), fill {{...}} placeholders in TEST-BUDGET.md and this file,
status/plan lines, merge main, full gate, PR, ready-prs line.
