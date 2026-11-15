# UI-WINDOWS-004

## WIP

Started from PR #391 head c3b29c40, then merged current main 4babc900 at
d14d3a67. Worktree/branch: ui-windows-004 / codex/ui-windows-004.

Done: read all binding briefs and prior handoffs. Added a reproducible pinned
static lifecycle census. Initial report has 137 registrations, 103 direct
toggle calls and 1,042 lifecycle candidates, 415 with manager receivers.
Unresolved receivers remain candidates rather than proved UI routes.
Added nine empty NPC movie controllers and ten manager-slot routes, an
exclusive callback firewall and a private/synthetic production host.
The graphical NPC host opts into close/open before the existing 25/28 sound
tail. No packet parsing, network or service implementation changed.

Checked: explicit world/client build passes in 13.33 s. Focused private UI
regressions and the new census tests pass 17 tests with two optional mutant
classes skipped in 22.11 s. Thirteen original NPC route/sound decisions pass,
and both real-movie and synthetic callback firewalls pass. Census complete:
118 entry-unresolved rows classify 9 provider-complete, 17 provider-missing,
30 state-dependent, 62 no route found. The inherited PlayGuide binding is
withdrawn after proving its slot is +0x1f0, whereas Ctrl+T/menu 22 select
EventMapEntranceUI +0x2ac. Survey 16 bound / 118 unresolved becomes 24 / 110.
The scan also lists 176 legacy manager calls, 47 proved immediate IDs,
and all 23 main-menu constants. Unknown receivers and IDs stay unresolved.

Left: compiled mutants, native journeys/captures, one default identity sweep,
affected build/tests/validators, audit, final integration and publication.
The source is WIP until those checks complete. After twenty minutes of
resource waits, use the brief's two-job fallback, one heavy job at a time.

Next step: native frame journeys for all nine layouts, inspect the captures,
then run the changed-controller mutants once.

The explicitly rebuilt pre-edit world at d14d3a67 has SHA-256
75ca1d88bb09c47a9e41358cceaa49bedf9a014039237563e4c0c3cd2435cf09.
A private copy is retained under the lane scratch directory for the single
baseline render. No main checkout build or installed app work was done.

No PR-ready claim or ready-prs entry. Checkpoint history records unfinished
work. Stop by 02:30 on 2026-11-15; push WIP by 02:15 if still unfinished.
