# LAYOUT-PROBE-001 handoff

Owned worktree `~/Documents/MTM/worktrees/layout-001`, branch `codex/layout-probe-001`.

The [finding](../research/client-layout-probes.md) records the addresses, method and evidence limits.
OBJECT +0 and +8 are separate flags. CHARACTER +0x144 and +0x14e have separate reads and uses;
+0x14e's interpretation stays static. CharacterAttribute's 0x200 progress prefix does not cover
the skill ids or timers. Known extent is at least 0x1b50; full allocation size remains unproved.

Checks actually run, with the reconstructed sources and affected validators unchanged:

| Check | Cases | Mismatches | Controls caught |
|---|---:|---:|---:|
| New bounded load probes, 7 families | 7,452 | 0 | 7/7 competing hypotheses |
| charsel, 6 families | 360 | 0 | 12/12 |
| combat, 12 families, 500 cases / 60 heavy | 4,240 | 0 | 12/12 |
| players, 4 groups including 768 byte helpers | 4,768 | 0 | 7/7 |
| progress, 13 families | 10,503 | 0 | 16/16 |
| scene, 9 families + loading UI | 225 + 10 | 0 | loading-screen control detected |
| ground items, 11 families, 500 cases / 60 heavy | 3,740 | 0 | 10/11 |
| skill delay start/ready/tick, unchanged `--families delay` | 177 | 0 | 1/1 |
| probe unit/private tests | 2 | 0 | |

Ground items' existing `frustum_no_range` control remains zero at both 60/6 and 500/60;
this is a control coverage limitation, not a successful sensitivity claim. Combat at 60/4
missed the hero-color control; 500/60 catches all 12. Initial items/scene runs lacked their
shared UI library in this fresh worktree. After the local build they both pass unchanged.

Local macOS gate: recorded in the PR after completion. Logs and reports are private under
`~/Documents/MTM/mu-mac-tools/native/scratch/layout-001/`.

Next: LAYOUT-001 on a fresh branch from the main containing this PR. Generate accessors,
field/zone tables and JSON; preserve the neutral names and static extent labels above.
No live game, network, protection or running-client write was used. No client bytes are committed.
