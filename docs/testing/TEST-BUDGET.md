# Test budget: what runs when (TEST-SPEED-001)

The owner asked for agents' finish phase to run only the checks a change needs. The policy is the brief's
"TEST BUDGET" section (2026-11-04); this page is the tooling that applies it and the measured effect.
[Handoff](../handoffs/TEST-SPEED-001.md).

## Commands

**A lane, at its finish** (one heavy job at a time, `nice -n 10`; `REF` = `origin/main`):

```sh
nice -n 10 make -j4
nice -n 10 tools/python/bin/python scripts/run_test_suites.py --affected origin/main
tools/python/bin/python scripts/audit_repository.py          # only if files were added or renamed
MU_RECOVERY_INTEGRATION=1 <env> nice -n 10 tools/python/bin/python scripts/run_validators.py \
    --private --no-mutants --cache --affected origin/main --jobs 2 --report <scratch>/validators
# mutants once, only for the validators the lane created or whose checks/targets it changed:
MU_RECOVERY_INTEGRATION=1 <env> nice -n 10 tools/python/bin/python scripts/run_validators.py \
    --private --cache --only <those rows> --report <scratch>/mutants
```

Look first with `--list-affected origin/main` (both runners): it prints every selected item with the changed path
and the reason. `Steward validators:` in the PR body = the rows `--affected` selected (mark the ones that need
mutants, normally none).

**The steward, per batch**: the full gate, unchanged, plus the listed rows:

```sh
nice -n 10 bash scripts/local-macos-ci.sh
MU_RECOVERY_INTEGRATION=1 <env> nice -n 10 tools/python/bin/python scripts/run_validators.py \
    --private --no-mutants --cache --only <union of the PRs' Steward validators> --jobs 2
```

Run the registry with mutants and without `--cache` only for a full integration lane (INTEGRATION-GREEN-*).

## Flags

| Command | Flag | What it does |
|---|---|---|
| `run_validators.py` | `--no-mutants` | Removes the mutant switches from each row's arguments (`--mutations`, `--mutants`, and with them `--mutant-cases N`/`--mutation-cases N`) and drops the expectations that read mutant results (the row's `mutants_at` paths and every path naming mutants, mutations or negative controls). 110 rows have a switch. `--mutations N` with a number (effects, effect_tree, meshdraw) is a count of random input cases, not planted mistakes, and stays; 16 rows have negative controls built into every run and are unchanged. The summary says how many rows ran without mutants; `--index` refuses such a summary (the evidence index records mutant counts). |
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
- **A `native/tests` module** runs if the diff touches the module, what it imports or names, or any source or header
  of the native make targets it names (`build/mu-walk`, `'perf-players-host'`, `viewer`, …) and, if it runs make at
  all, of the default goal. A target's sources are every repository file its full dry run (`make -C native -nB
  <target>`) names, every file reached through `#include` from them (no build needed), every header in its `-I`
  directories, and the `.d` files' headers when built. A `native/tests` helper or host no module reaches selects every
  module.
- The `tests` suite (repository policy, manifests; ~2 s) runs on every non-empty diff. The top-level `Makefile`,
  `scripts/run_test_suites.py`, `scripts/local-macos-ci.sh` and `scripts/affected.py` select everything.

What this means in practice: `libmunative` links all of `native/core` and almost all of `reconstructed/`, so a
change to a reconstructed or core C file still selects ~110 of the 118 `native/tests` modules. The selection pays
off for Python-only changes (validators, generators, tools), docs, app/viewer-only changes, test hosts and single
test modules. Known limits: imports or paths built at run time from computed names are seen only when their
pieces are quoted; a validator that reads a file through an environment variable depends on it invisibly (those are
local inputs, never in a diff).

### Original-instruction cache (scripts/original_cache.py)

The pinned client never changes, so the original side of a validator case is a function of the pins, the Python
code that drives Unicorn, and the case input. With `--cache` (or `MU_VALIDATOR_CACHE=<dir>`) that side is stored in
`<dir>/<name>/<key>.pickle.xz`; the key hashes every pin's sha256, the Unicorn and Python versions and the sha256
of every Python file in the closure of the script that runs the original side. Any harness change starts a new key
(the old file is deleted). Only the original side is cached: the C library is called for every case and compared
with the cached original exactly as with a fresh one, and a C mutant run with a warm cache is still caught.

Wired into the shared item harness, so every validator using it gets the cache:

| Where | Original side cached | Used by |
|---|---|---|
| `gen_item_bodies._original` (cache `gen_item_bodies`) | each Unicorn sample of the body-table regeneration (`client_stream` + the helper tags, exits, random draws and sites its hooks record); the generic C stream and the fit stay live | the 12 validators that check `item_bodies.h` against `gen_item_bodies.generate()` (continuation, ranked, expansion, clusters, chains, next, gear, coverage, scalars, carry, wings_next, quality) |
| `validate_item_clusters.body_cases` / `link_cases` | the body stream and the link-effect calls per case | body_cases: item_continuation, ranked, expansion, clusters, chains, next, gear, coverage, scalars, carry, wings_next; link_cases: continuation, expansion, clusters |
| `validate_item_continuation.skin_cases`, `validate_item_ranked.link_cases` | per case | those two |

The pattern for another validator: wrap the call that runs the pinned instructions for one case in
`original_cache.active().get('<family>', <case input>, lambda: <run it>)`, return only plain data (no machine), and
keep every C call outside the lambda. If the original run has side effects other code reads (hooks filling lists),
capture them in the cached value and replay them, as `gen_item_bodies._original` does.

## Timings

{{TIMINGS}}
