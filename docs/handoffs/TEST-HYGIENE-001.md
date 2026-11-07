# TEST-HYGIENE-001: private native/tests that run clean from a fresh tree, in one process and under `--jobs 2`

Branch `claude/test-hygiene-001` from main `02e4d94d` (#344), merged with `97b282e6` (#346). Worktree
`~/Documents/MTM/worktrees/test-hygiene-001`. Tests and test tooling only: no product code, no validator checks,
no live client, no installed app.

The problems come from APP-REFRESH-009's full private run (its handoff, "Follow-ups" 2–5) and the steward's 8d
runs. Each one below has the cause found and the fix made.

## 1. `test_audio_items` fails in a fresh worktree

- **Cause:** `test_original_ground_audio` runs `scripts/validate_audio_items.py`, which dlopens
  `reconstructed/items/libclient_items.dylib`. The root `make` does not build it. The test passed only when another
  module (e.g. `test_native_fidelity`) had built it first.
- **Reproduced:** fresh worktree after `make -j4`, private-env.sh: `dlopen(... libclient_items.dylib): no such file`.
- **Fix:** the test runs `make -s -C reconstructed/items` before the validator, the same way
  `test_native_fidelity.library()` does. Result: 4/4 OK from the clean tree, 11 s.

## 2. `test_inventory_fx.InventoryScene` fails under `--jobs 2`

- **Seen once** (APP-REFRESH-009, second pass): mu-world exited non-zero with empty stderr. The test printed only
  stderr, so the exit code (a signal shows as a negative code) and stdout were lost.
- **Not reproduced here:** two InventoryScene runs at the same time passed (3/3 each, 29 s). So did a run during 20
  forced relinks of `native/build/mu-world` (`make -W build/world-rt-gl/world_tool.o world`), 3/3 in 13 s.
- **Ruled out:** fixed ports, client lock and session (mu-world runs offline, and the sockets transport takes the
  lock), the `out-dir` (private temp dir), TMPDIR (private per work item), and `option.ini` (not written by this
  flow).
- **Shared state that remained:** the binary `native/build/mu-world`. The runner's make shim serialises builds, but
  not the runs of what they built, so another module's `make` may relink it while this class runs it. The second was
  the user-wide settings folder (`~/Library/Application Support/MuTheMatrixNative`), the default for
  `MU_NATIVE_SETTINGS_DIR`.
- **Fix:**
  - `setUpClass` copies mu-world into the class's own temp dir after `make world` and runs the copy.
  - Each run gets `MU_NATIVE_SETTINGS_DIR` in its own temp dir.
  - A failure now reports `mu-world exit <code>` plus the tails of both stderr and stdout. If it recurs, the cause
    (e.g. a signal) will be visible.
- **Result:** 3/3 alone, and passed in the full `--jobs 2` run below.

## 3. A module removes `MU_LANG_DIR` from `os.environ`

- **Offender:** `test_native_lang.Combat.test_combat_skill_distance_and_log`. It ran
  `os.environ.pop('MU_LANG_DIR')`, then set the variable, then popped it again in `finally`. That deleted the
  caller's value for good.
- **Other `os.environ` writers checked:**
  - `test_transport`: setUp saves the environment, tearDown restores it.
  - `test_app_polish2`: restores `MUGFX_STUB_LOG` in a `finally`.
  - Both are fine. No other module writes `os.environ` without restoring it.
- **Fix:** two `mock.patch.dict(os.environ)` blocks, one without the variable and one with the synthetic table.
- **Proof, one unittest process** (`test_native_lang test_native_map test_native_skill test_render_effects18`,
  private-env.sh):
  - Before the fix: 39 tests, **2 errors** (`KeyError: 'MU_LANG_DIR'` in `test_native_map.PrivateTravel` and
    `test_native_skill.Installed`), 2 skipped, 72 s.
  - After the fix: **39 tests OK**, 2 skipped, 81 s. The two skips were then fixed under item 4.

## 4. Skips that are really missing env

With private-env.sh (it now sets `MU_GFX_LIB` and `MU_LANG_DIR`), 20 tests still skipped at import. Three of those
skips were env or build-order problems, and they now run:

| Test | Was | Now |
|---|---|---|
| `test_native_skill.Installed.test_validator` (validate_skill + validate_skill_server, 60 cases, with mutants) | skipped: it reads the langread snapshot from `SNAP`, which private-env.sh does not set | takes `SNAP`, else `MU_LANG3_SNAPSHOT` (scripts/pins.py LANG3: the file `run_validators.py` passes); OK, ~5 min |
| `test_render_effects18.InstalledMuun` | skipped: private-env.sh's `MU_LANG_DIR` (scratch `lang`, the older langread folder) has no `muuneffects.tsv` | uses `MU_LANG_DIR`'s table, else `MU_NATIVE_DATA_DIR/lang`'s; OK |
| `test_native_objects.test_viewer_headless_objects` (portable) | skipped when `native/build/mu-viewer` was not built yet (the root make does not build it): another build-order dependence | builds `build/mu-viewer`; skips only if that fails (SDL2); OK |

**Skip reasons rewritten to name the variable or build step:**
- `test_native_skill`: Installed and test_validator.
- `test_native_fidelity`: PrivateValidators and test_lang_families.
- `test_native_lang2` and `test_native_npc`: client text capture or `MU_CLIENT_TEXT`.
- `test_native_charsel`: `MU_OBJECTS_PLAIN_DIR`.
- `test_native_gfx2` and `test_native_gfx3`: mugfx build scripts.
- `test_native_stress.MetalTiming`: the dylib path.

About 45 classes still say "requires pinned private instructions" or similar. Each of them is gated only on
`MU_RECOVERY_INTEGRATION=1`, so they run under private-env.sh. They were left alone to keep the diff and the
steward's selection small.

**Still skipping under private-env.sh (17 tests, all named in their reasons):**

| Module.class | Tests | Needs |
|---|---:|---|
| `test_native_gfx.Synthetic` | 1 | an in-tree `native/gfx/mugfx` build (fetch-ruffle.sh, build-mugfx.sh) |
| `test_native_gfx2.LayerWithRuffle`, `.RuffleExtensions` | 1 + 5 | the same |
| `test_native_gfx3.RuffleLoadingAndImages` | 4 | the same |
| `test_native_gfx3.InstalledBaseMovie` | 1 | the same, plus `MU_GAME_ROOT` |
| `test_native_stress.MetalTiming` | 2 | `native/gfx/mugfx/target/release/libmugfx.dylib` (build-mugfx.sh) |
| `test_native_names.GfxRoute`, `.GfxTravel` | 1 + 1 | `MU_NAMES_GFX_MOVIES` (converted name movies) |
| `test_native_quest.LorenciaDemo` | 1 | `MU_QUEST_MOVIES` (converted quest movies) |

The scratch `libmugfx.dylib` in `MU_GFX_LIB` cannot stand in for the in-tree build: those classes also need the
`SHOT` tool from the same Cargo build.

**Suggestion for the orchestrator** (private-env.sh is outside the repository, so not changed here): scratch `lang`
has `live/` (the lang3/lang4 snapshots), `filter*.txt`, `social-options*` and `tools/`. Native Data's `lang` has
nine newer tables (`muuneffects`, `mapeffects`, `mapanim`, `itemtrs`, `guidequest`, `guidestrings`,
`dialoganswers`, `tree4_side`, `tree4_tips`). Neither one is a superset of the other, so `MU_LANG_DIR` should stay
as it is. The tests now fall back where needed.

## 5. Working directory

- **Runner:** `run_test_suites.py` already starts every child with `cwd=ROOT`. But it reads suite arguments from
  the root: run from `native/`, `tests` silently meant the root's `tests` suite. It also reads `--logs` from the
  cwd. `main()` now exits at once with "run it from the repository root (...)" when the cwd is not the root.
  `replay_affected.py` imports the module without calling `main()`, so it is unaffected.
- **Test:** `tests/test_run_test_suites.py::SuiteList.test_refuses_another_working_directory`.
- **Scan of native/tests:**
  - No helper reads a cwd-relative path.
  - Root-relative source lists are prefixed with `ROOT`, or compiled with `cwd=ROOT`.
  - The only scenario with a root-relative path is REGRESS-002's `skills-state.scn`, already pinned.
  - `python -m unittest` from `native/` has no cheap global guard: there is no shared conftest, and adding one would
    touch 229 modules. The rule stays in the brief and in TEST-BUDGET.md.

## Checks

All commands were run from the repository root after `nice -n 10 make -j4` (37 s), at `3b229cef` (branch, merged
with `97b282e6`).

| Check | Result | Wall |
|---|---|---:|
| **Full private native/tests**, private-env.sh, `MU_GATE_JOBS=2`, fresh-tree start (`libclient_items.dylib` and `mu-viewer` deleted first) | **990 tests: 972 passed, 18 skipped, 0 failures, 0 errors** (148 modules). `test_audio_items` 4/4, `InventoryScene` 3/3, `test_native_skill.Installed` 2/2, `InstalledMuun`, `test_viewer_headless_objects` and `test_native_map.PrivateTravel`: all OK | 1,445 s |
| Before (APP-REFRESH-009, full run at `138b756e` without `MU_GFX_LIB`) | 969 tests: 941 passed, 27 skipped, 1 failed (`test_audio_items`, test order) | 1,251 s |
| Item 3 modules in **one** process (`test_native_lang test_native_map test_native_skill test_render_effects18`), private-env.sh | before the fix: 39 tests, 2 errors (`KeyError: 'MU_LANG_DIR'`); after: **39 OK**, 2 skipped (both fixed by item 4, then OK: 4/4 in 332 s) | 72 s / 81 s |
| Portable `run_test_suites.py --affected origin/main`, `MU_RECOVERY_INTEGRATION=0`, jobs 2 | 46 of 185 work items (the changed test modules and the modules that import them; `tests` always): **657 tests, 550 passed, 107 skipped, 0 failures** | 147 s + 61 s selection |
| `audit_repository.py` | 2,098 staged files, 0 rejected | 39 s |
| `run_validators.py --list-affected origin/main` | 0 of 208 rows: **Steward validators: none** | 37 s |

The 18 skips of the full run are the 17 in the table above plus `test_native_gfx2.PatchSeries` ("no pinned Ruffle
checkout (native/gfx/fetch-ruffle.sh)", a runtime skip).

Cost note: `test_native_skill` is now the longest private work item, at 420 s, because its validator pair (60 cases
with mutants) now runs under private-env.sh. It is only selected when its inputs change.

## Cleanup

`native/build`, `reconstructed/*` build outputs, `verify-runs/` and the scratchpad logs were deleted after the
ready line, and the worktree and local branch were removed. No inputs were kept for later lanes.
