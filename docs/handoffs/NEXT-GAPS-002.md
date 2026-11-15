# NEXT-GAPS-002

Docs-only research on `claude/next-gaps-002`, based on main `c5b9d5ca` (PR #400, batch 118).
Claude Fable 5.2, no subagents. No runtime source change, capture, model extraction, standalone
build, render, benchmark, validator or original-client run. The documentation-consumer test modules
compile their synthetic hosts on demand.

## Result

[The report](../research/next-gaps.md) replaces the NEXT-GAPS-001 snapshot of 2026-11-09. It gives:

- the per-area inventory with denominators, main and pushed-branch counts kept apart;
- one table of the 39 consumer ids that lanes report as refused (17 particle pairs, 4 joints, 15
  effects, 2 sprite bindings, 1 blur), with the lane family that requests each;
- assets missing from the frozen Native Data (owner-paused) and assets missing from the game data
  or without a binding (permanent refusals), listed separately;
- fourteen ranked lanes with scope, start files, original addresses, dependencies, method and checks;
- a six-lane parallel plan by file ownership;
- the candidates at diminishing returns, so that they are not started;
- a superseded section for the 001 lanes and counts, and the 001 ledger entries still cited.

The ranked list was copied early to `~/Documents/MTM/mu-mac-tools/native/next-gaps-002-queue.md`
for the orchestrator.

Ranked lanes, in order: RENDER-EFFECTS-034 (consumers for worlds, items and Muun),
RENDER-ACTORS-008 (caller-service groups), RENDER-EFFECTS-035 (skill callers outside the learned
set), HERO-ITEMS-002, RENDER-WORLDS-INNER-006 (after the census), RENDER-ITEMS-002AB,
RENDER-EFFECTS-036 (effect consumers), MOUNT-VISUAL-002, AUDIO-007, UI-WINDOWS-007,
RENDER-ACTORS-009, CHARSEL-ITEMS-002, WORLDS-WATER-001, NATIVE-PERF-005. Names are proposals.

## Method

Read the binding brief, the 2026-11-15 resume and session log, NEXT-GAPS-001's report and handoff,
the status lines, and the latest handoff of every family on main: items, actors, effects, worlds,
UI, audio, Muun, hero equipment, cloth, selection and login scenes, input, terrain, helpers and
performance. Read the handoff drafts on the pushed branches of the lanes running that day at fixed
commits: ACTORS-007 `a1eba04b`, ITEMS-002AA `baec5c08`, EFFECTS-033 `35ae89fe`, WORLDS-PICK-001
`5eaeb445`, UI-WINDOWS-006 `8e0c9713`, MUUN-VISUAL-005 `7fac39fa`, AUDIO-006 `83dc2528`. Branch
counts are labelled as such in the report.

Text-only counters (no original execution):

- C02, `docs/research/ui-window-route-survey.csv`: 134 rows; bound 28 / not bound 106; 13
  provider-complete, 33 provider-missing, 30 state-dependent, 43 no route, 15 previously bound.
- C03, the actor decision and group CSVs at `a1eba04b`: 217 incomplete rows grouped by reason; the
  three lane-2 reasons are 66, 25 and 18 rows.
- The Muun census CSV at `7fac39fa`: 386 rows, 378 kind 0 and 8 kind 1.
- The skill catalogue table in `client-render-effects-030.md`: 14 DK and 23 Elf rows; 27 use the
  default step and both default end bodies, ten have their own step or end body.

Older leads were checked against newer handoffs before use. The pet and Dark Raven particle lists
are marked as unconfirmed, because kind files for them exist in the particle module today; whether
each subtype is supported was not verified.

## Checks

- `scripts/audit_repository.py`: 2,352 staged files, zero rejected, 38 s.
- Canonical private-env sourced from the root, then `MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2`,
  `nice -n 10 tools/python/bin/python -m unittest tests.test_world_captures_2
  tests.test_repository_policy native.tests.test_native_item_textures
  native.tests.test_native_data_manifest`: 36 tests, 35 passed, one expected skip, no failures or
  errors, 43 s wall (42.1 s test time).
- Local links in the report and this handoff resolve; neither file contains a home-directory path;
  `git diff --check` passes.
- No validator, build target, render or benchmark was run.

Docs-only integration uses brief 6c. Steward validators: none.

## Limits

- This is a planning snapshot, not a fidelity result. Counts on pushed branches are the lanes' own
  claims until merged. Three of those lanes had not published a final handoff at the snapshot
  (ACTORS-007, WORLDS-PICK-001, UI-WINDOWS-006); the all-world inner-object census and the
  UI-WINDOWS-006 ledger did not exist yet, so lanes 5 and 10 are scoped by reference to them.
- No single consumer id is requested by two lane families. The shared need is the consumer module;
  the ranking of lane 1 rests on that and on the refusal counts, not on a duplicated id.
- ACTORS-007 does not publish the effect ids behind "additional caller services: effect"; lane 2's
  first deliverable is that list.
- Whether an authored learned-set extension for the catalogue skills (lane 3) should ship in the
  demo is the owner's choice; the lane can prove the callers with test fixtures either way.
- Sizes (S/M/L) and the ranking are estimates. No whole-client refused-effect census exists.
- No visual-equivalence, audio-parity or performance claim is made. No original bytes are published.

## Delivery

After the last push and the ready-prs entry, nothing further is pushed; the merge steward owns the
combined gate and merge. The external queue file is the only local output kept. The worktree and
local branch are removed at PR-ready; the remote branch stays.
