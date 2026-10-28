# README-REFRESH-004

Documentation-only task in worktree `worktrees/readme-refresh-004`, branch `claude/readme-refresh-004`, from
origin/main `fa63719` (PR #241).

## Changes

- Refreshed What works today and Progress for every PR merged after README-REFRESH-003 (#213): #215, #216,
  #217, #219, #221, #224, #225, #227, #228, #229, #230, #232, #233, #235, #237, #238, #239, #240 and #241. The
  other numbers in #214–#241 are issues, not merged PRs.
- World: 33/144 primary methods across 11/48 classes; Loren Market/Uruk, completed Raklion/Karutan, built-in
  Lost Tower/Tarkan/Icarus visuals, recorded particle consumers; Icarus full-draw error 26.897 → 23.154.
- Items: 880/1,674 bodies, 17/17 skins, 17 link targets / 22 types; 794 bodies remain.
- Skill visuals: 18/23 primary (56/77 weighted). Sound: 76 migrated sites.
- Session: ground items, minimap markers and party added to the table, plus the globals ownership note;
  11/11 fixture scenarios, 86 inbound frames, two unrecovered intents, nine unsent requests.
- HelpWindow (Ctrl+H native binding), RENDER-TIME-001's native half (live half open), the Native Preview refresh,
  and a note that NATIVE-PERF-003's crowd80 18.4 / tormenta80 18.9 fps have not been re-timed since.
- What is still missing: updated remaining counts; online/login/live play, owner-led network lanes, live
  comparisons, the 25 fps crowd target and second-user installation stay open.
- Claim sources: [readme-refresh.md](../research/readme-refresh.md#readme-refresh-004-claim-sources).

## Images

None added or edited. All README media and audit pins are unchanged. All local README link and image targets
resolve.

## Checks

Under the merge queue and lock, origin/main was still `fa63719`, so no integration merge was needed.
`bash scripts/local-macos-ci.sh` (task-scoped TMPDIR) passed: **1,630 tests across 38 discovery suites,
208 explicit private/optional skips, zero failures/errors**. All **11/11 fixture scenarios** pass **86
expectations** with **86 inbound frames**, zero unbound/undecodable; the existing two unrecovered intents and
nine unsent requests are reported. Native viewer and read-only reader builds pass (readers built only).
Publication audit: **1,586 staged files, zero rejected**. Only this handoff's check summary changed after the
gate; the staged audit is repeated before merge. This lane claims no new private run, instruction comparison,
timing or live acceptance. Self-review against the brief and source PRs; no independent review claimed.

## Cleanup and remaining work

After merge: release the merge lock, delete this task's scratch, remove the worktree and local branch,
fast-forward the main checkout only if clean on main. No local input is retained. Remaining work is unchanged
from the source handoffs; no live game, launcher, installed data, credential or signing state was touched.
