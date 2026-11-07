# REGRESS-002: the three "pre-existing" session/fixture failures APP-POLISH-007 saw

Branch `claude/regress-002`, worktree `~/Documents/MTM/worktrees/regress-002`. It started from main `c5ed13dd`
and was re-checked on `ae5e6f36` (#333) and `f2370871` (#334). Offline only. No original client, no installed app,
no network.

## Summary

APP-POLISH-007 (#333) reported three failures that "also fail on main `e68829a6` in this checkout":
`test_session_skills.test_scenario_and_unsent_cast`, `test_session_combat.test_fight_frames_and_plaintext_attack_encrypted_cast_unsent`
and `test_fixture_scenarios.test_every_discovered_scenario_runs_in_make_test`, all "undecodable/unsent counts"
in skills-state, combat-fight, quest-progress and quest-routes.

They are **not** a code regression and **not** private-environment drift. They are a **working-directory
dependence**. Four fixture scenarios name their data tables relative to the repository root
(`native/fixture/scenarios/skills-tables`, `.../quest-tables`). `mu-session fixture` resolves those paths
against its cwd, and the test helpers started it in the caller's cwd. The gate always runs tests with
`cwd=ROOT`, so it passes. A lane that runs the modules from `native/` (`cd native && python -m unittest
tests.test_…`) gets exactly the reported failures. A fourth module the lane did not list,
`test_session_quest.test_quest_journals_have_no_host_pointer_differences`, fails the same way.

Fix: the two harness entry points that start `mu-session` for scenarios now pass `cwd=ROOT`
(`native/tests/test_session_support.run_tool`, `scripts/run_fixture_scenarios.run_scenario`). A new test runs the
four scenarios through the runner from `native/`. No product code changed.

## 1. Reproduction

All runs used `make -j4` first. The three modes are: repository root without private env (as the gate),
repository root with the lane env (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, `MU_SECTION3`, `MU_EVIDENCE_DIR`,
`MU_NATIVE_DATA_DIR` = APP-REFRESH-006 Native Data), and cwd `native/` without private env.

| Main | root, portable | root, private | cwd `native/` |
|---|---|---|---|
| `c5ed13dd` | 3 modules OK (skills 8/1 skip, combat 5/1 skip, fixture 8) | OK (no skips) | **3 fail** + `test_session_quest` fails |
| `ae5e6f36` (#333) | OK | OK | same 4 fail |
| `f2370871` (#334) | OK | OK | same 4 fail (scenario probe) |
| branch, fix applied, on `f2370871` | OK | OK | **OK** |

Ruled out on `c5ed13dd` (all pass from the root): `MU_LANG_DIR` set to the Native Data `lang`, to
`mu-mac-tools/native/scratch/lang` (with `skills.tsv`), and the 38 modules the lane listed run in one unittest
process (278 tests, 30 skipped, 0 failures, 190 s; no test calls `os.chdir`). `mu-session fixture` uses the
in-process transport, so loopback port collisions with other lanes are not a factor either.

Failing expectations with cwd `native/` (`mu-session fixture <scenario>`; the counts are the same on all three
mains):

| Scenario | Failing expectations | Why |
|---|---|---|
| `skills-state` | `skills.count = 7` (15), `skills.selected = 330` (0), `skills.key.1 = 330` (0), `unsent = 1` (0) | `client skill-data` / `skills data` / `skills file` do not find `native/fixture/scenarios/skills-tables`: the fixture falls back to its default book, and the client has no table for the cast request |
| `combat-fight` | `undecodable = 0` (1), `quest.kills.3 = 1` (0) | `client quest-data` finds no quest tables, so the quest kill frame is undecodable |
| `quest-progress` | `undecodable = 0` (3), `unsent = 1` (0), 4 × `quest.*` "unknown key" | same, the quest domain is unbound |
| `quest-routes` | `undecodable = 0` (10), `frames_in = 17` (10) | same |

`quest-data` already tries the scenario's own folder first (`native/tools/mu_session.c`). That cannot help:
the path is written repository-relative, and `run_fixture_scenarios.py` copies each scenario into its report
folder before running it.

## 2. Bisect

`git bisect run` in a throwaway worktree, range `707b82ca` (good, the base of #171 before any of these scenarios)
to `c5ed13dd`. The probe built only `make -C native build/mu-session` and ran the scenario with the runner's tick
rule (last `at` + 20) from the root and from `native/`. It exits 0 when the scenario is absent or both runs pass,
1 when the root passes and `native/` fails, and 125 when the root fails or the build fails.

| Scenario (test) | First bad commit | Merged by | Wall |
|---|---|---|---|
| `skills-state` (`test_session_skills`) | `aef79e57` "session: checkpoint skill domain, plaintext fixture and headless ownership" (adds the scenario and the test) | #204 SESSION-SKILL-001 | 25 s |
| `combat-fight` (`test_session_combat`) | `e72517ba` "SESSION-COMBAT-001 combat domain, fixture behaviour, fight scenario" (adds the scenario; the test came in `5d790b80`, same PR) | #197 | 25 s |
| `quest-progress` (`test_session_quest`, `test_fixture_scenarios`) | `2a916b52` "Move quest state and window actions into the session" | #179 | 29 s |
| `quest-routes` (`test_fixture_scenarios`) | `2a916b52` | #179 | 25 s |

At each first-bad commit the root run passes and the `native/` run fails. Every scenario has been
cwd-dependent since the commit that wrote it, so no later change regressed it. `test_fixture_scenarios` and
the runner were added in `6b0169db` (#171), before these scenarios existed.

## 3. Cause and fix

**Cause:** a test-harness assumption, not the client code or a test's stale expectation. The scenario language
treats data paths as repository-relative, but nothing pinned the tool's cwd. The gate's runner (`scripts/run_test_suites.py`) starts every unittest
process with `cwd=ROOT`, so the assumption always held there. It did not hold for a lane running modules from
`native/`.

**Fix (tests and tooling only, no product code):**
- `native/tests/test_session_support.py`: `run_tool` runs `build/mu-session` with `cwd=` the repository root
  (48 callers across 13 modules; this is the cwd the gate already used, so their behaviour in the gate is unchanged).
- `scripts/run_fixture_scenarios.py`: `run_scenario` runs the tool with `cwd=ROOT`. This also covers the
  verify skill's `run-tool.sh` and the gate's fixtures stage, which already ran from the root.
- `native/tests/test_fixture_scenarios.py`: `test_repository_relative_scenarios_pass_from_any_cwd` runs the four
  scenarios through the runner with `cwd=native/`. Without the runner change it fails
  (`skills-state` exit 1); with it, it passes.
- `docs/testing/TEST-BUDGET.md`: one line saying lane commands run from the repository root, as the gate does.

The scenarios themselves keep their repository-relative paths. Scenario-relative paths would break the runner,
which copies each scenario into its report folder.

## 4. The gate gap and the recommendation

**Did the gate run these modules?** Yes. `scripts/local-macos-ci.sh` runs every `native/tests` module (one work
item per module, `MU_GATE_JOBS=4`) and the fixtures stage (`run_fixture_scenarios.py` over every discovered
scenario), all with `cwd=ROOT` and `MU_RECOVERY_INTEGRATION=0`. The three failing tests are portable tests, not
private ones, so the gate ran them and they were green there. It cannot see a cwd dependence, because it never
runs from anywhere else. With this fix, the session and fixture scenario harness no longer depends on cwd.
Other modules may still assume the root (not swept: a full `native/` cwd sweep costs about a gate). The
TEST-BUDGET line makes the root the documented place to run lane commands.

**The structural gap is the private classes.** The gate's `MU_RECOVERY_INTEGRATION=0` skips every private class:
191 test modules in `native/tests`, `tests` and `reconstructed` carry such a skip. In this branch's affected
selection alone, 50 of 361 tests skipped, for example "private client comparisons need MU_RECOVERY_INTEGRATION=1" (22),
"private pinned instructions" (5) and "private pinned client captures and installation" (4). The steward's
`run_validators.py --private` step covers the registered validator rows, not these unittest classes. A
regression in a private class (for example `test_session_combat.PrivateCombat`, `test_session_skills`'s private
class, the `MU_NATIVE_DATA_DIR` app tests) reaches main unseen unless the lane happened to run it.

Recommended smallest change (steward only, no runner change needed: suite arguments and `--affected-since`
already combine). After the portable gate, run the batch's affected **native/tests** modules once with the
private env:

```sh
# BASE = the main commit the batch was merged onto
MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=… MU_SECTION3=… MU_EVIDENCE_DIR=… MU_NATIVE_DATA_DIR=… \
  MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py native/tests --affected-since "$BASE"
```

Measured on this branch: the 15 affected `native/tests` modules in private mode took about 2.5 min wall at
`jobs=2` (87 tests, 0 failures, 0 skips). Leave `tests/` out of the private step. In private mode its
`test_orphan_validators_private` replays private validators: it was still running after more than 9 minutes and was
stopped, and those comparisons belong to `run_validators.py --private`, which the steward already runs. Lanes
should keep naming the private modules they ran in the PR (brief 6b).

## Checks

| Check | Result | Wall |
|---|---|---|
| `nice -n 10 make -j4` at `c5ed13dd` / `ae5e6f36` / `f2370871` | ok | 35 s / 12.5 s / 10.3 s |
| 4 modules × 3 modes (root portable, root private, cwd `native/`) at `f2370871` with the fix | 12/12 OK (25 tests per mode; portable skips are the existing "private pinned instructions" classes) | ~6 s / ~17 s / ~6 s |
| Same, unfixed, at `c5ed13dd` and `ae5e6f36` | root OK in both modes; cwd `native/` 4 fail | ~30 s each |
| 38 lane-listed modules in one process, `c5ed13dd` | 278 tests, 0 failures | 190 s |
| 4 × `git bisect run` | first bad = the scenario's own commit (table above) | 25–29 s each |
| `run_test_suites.py --affected origin/main`, portable, `MU_GATE_JOBS=2`, at `f2370871` + this diff | 18 work items (`tests` + 17 `native/tests` modules, incl. the docs modules): 384 tests, 0 failures, 51 skipped | 152 s |
| `scripts/audit_repository.py` | 2,058 staged files, 0 rejected | 17.5 s |
| Same selection, private env, `native/tests` part | 15 modules, 87 tests OK | ~2.5 min |
| `tests/test_fixture_runner.py`, private | 8 OK | <1 s |
| `run_validators.py --list-affected origin/main` (after make) | 0 of 201 rows at `ae5e6f36`, 0 of 202 at `f2370871` | 23 s |

Steward validators: none (tooling and tests only; `--list-affected origin/main` selects 0 of 202 rows at
`f2370871` + this diff).

## Left

- A one-time sweep of all `native/tests` from a non-root cwd, to find any other root-assuming module. It costs
  about a gate, so it is not done here; the documented root makes it optional.
- The steward step above is a recommendation for the orchestrator; `local-macos-ci.sh` is unchanged.
