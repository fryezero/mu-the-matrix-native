# NEXT-GAPS-001

Docs-only research on `codex/next-gaps-001`, based on main `ff8e0543`. No runtime source changes,
new captures, model extraction, standalone builds, renders, benchmarks or original-client execution.
The required docs-consumer modules compile their synthetic hosts/tools on demand.

## Result and method

[The report](../research/next-gaps.md) ranks ten in-scope lanes and records the remaining evidenced gaps,
file conflicts and parallel groups. It separates merged counts from branch-only WIP and marks excluded
server/network/protection/power work. Every reported inventory count has an owning source location.
The first cut was delivered early to `~/Documents/MTM/mu-mac-tools/native/next-gaps-first-cut.md`.
Its provisional Test Area particle lane was removed after EFFECTS-019 proved it already complete.

Read the full binding brief, resume and external queue, repository instructions, README Progress and
latest relevant handoff limits across items, effects, actors, cloth, worlds, app polish/refresh, inventory,
hero equipment, audio and performance. Cross-checked stale limits against newer handoffs and source.
Text-only counters rechecked world JSON statuses, GFx registration names, actor-table rows and the named
world-gap union. Source ledger and immutable actor/item branch snapshots are in the report.
No subagents were started. Resource pauses followed load above 14.

## Checks

- `scripts/audit_repository.py`: 2,135 staged files, zero rejected, 19.28 s.
- Canonical private-env sourced from the root, then `MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2`,
  `nice -n 10 tools/python/bin/python -m unittest tests.test_world_captures_2 tests.test_repository_policy
  native.tests.test_native_item_textures native.tests.test_native_data_manifest`: 36 tests,
  35 passed, one installed-data skip, no failures/errors, 9.62 s wall. The recorded run reuses the
  hosts/tools compiled by the initial invocation. Its terminal result was not retained, so the modules
  were run again to retain a complete result. No standalone build or validator was run.
- Local links and complete source paths in the research note resolve; `git diff --check` passes.
- Text-only counters: both world-method inventories 144 verified entries, 48 classes/57 registrations;
  32 Player-model table rows; 31 GFx registry entries; 22 named inline-gap worlds.

Final audit also covers these result-recording edits. Docs-only integration uses brief 6c.
Steward validators: none.

## Limits and next

This is a snapshot and a planning estimate, not a new fidelity result. Whole-client refused effects,
complete actor special passes and UI window totals remain unknown. Actor and item WIP results are not
counted as merged. Read current ownership before dispatch; do not duplicate ITEMS-002X, ACTORS-001 or
EFFECTS-025. PERF-005 requires a quiet machine. APP-REFRESH-012 alone may install the Native Preview.
All appearances are fixture/demo-only; no live service, stats, opaque component or owner Wine app work.

After the last push and ready-prs entry, push nothing further. The merge steward owns the combined gate
and merge. The external first-cut file is the only retained local dispatch input; no scratch output
was retained. Test build outputs are removed with this lane's worktree. Remove this lane's worktree and local branch at PR-ready, retaining the remote branch.
