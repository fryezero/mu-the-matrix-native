# CHARSEL-ITEMS-001

Selection-only authored appearance records, on branch `codex/charsel-items-001`, from main
`a2ad8814`. Offline/static work only. No subagents, live client, packet/account work, installed
application change or full lane gate.

## Implementation checkpoint

The selection character adapter now uses existing item draw APIs for explicitly authored demo
records. It carries type, level and excellent, with ext only on body parts. File-only items keep
the original selection mesh path. Existing supported item programs use the selection's own
clock, bones and effect pool. The common charsel controller and audio adapters are untouched.
Public/internal charsel header changes and tool report changes are added lines only.

Recovered original callers: selection `0x01857aee`, ordinary body `0x0136a6d7`, ordinary hand
`0x0136c428`, wing `0x0139eefc`, linked RenderObjDraw `0x012c6a83`. The last forces ext zero.
[Research and limits](../research/client-character-select.md#charsel-items-001-authored-equipment-levels-in-selection).

Checks so far: focused portable module, 6 tests, 5 passed and one private skip, 1.35 s.
Original iteration, 1,073 comparisons including 768 mesh-pass cases, zero mismatches, 8.43 s.
Build passes, 6.58 s; GL world/selection targets pass. Final affected checks, renders, mutant run,
latest-main integration, PR and queue entry remain pending at this checkpoint.

The unit selector chose 112 work items, including 109 native modules. Private 8d is reduced to
the new module under the 40-item cap; existing private shell/demo record controls will also run.
The validator selector chose meshdraw, model_edge, movement, audio_callers, audio_domains,
audio_items, app_polish4 and charsel_items. Movement is a retained symbol fallback.

Limits: authored fields only, FILE still picks the mesh, existing unsupported recipes remain
counted fallbacks, and this lane does not add class-specific geometry, +15 attachments or cloth
setup. The shipped demo uses +7/+9 equipment. No original-client visual-equivalence claim.

No PR-ready claim or ready-prs line at this checkpoint. The steward owns integration and merge.

## Verification checkpoint, 2026-11-09

Merged latest main `9d6ce467` as `2a1702906248d91ae4a6db014637176ad400b9cf`. This brought documentation
only; compiled inputs are identical to implementation checkpoint `a59fd288`.

- Affected portable run at `2a170290`: 112 selected work items, 1,140 tests, 951 passed, 189 expected
  skips, zero failures/errors. 308.8 s test wall, 375.3 s including selection analysis.
- Eight affected validators: all pass, zero errors/skips, 181.8 s including selection analysis.
  The new row has 8,817 comparisons and zero mismatches, 7.9 s.
- New row's seven compiled header mutants: all caught, 14.5 s row wall, 14.7 s command.
- Private 8d reduced plus explicit existing world-entry/demo-record controls: 11/11 tests pass,
  23.7 s. Modules/classes: `test_charsel_items`, `test_native_shell.PrivateDemoSessionTests`,
  `test_app_polish8.PrivateRecords`. Every command ran from the repository root after sourcing
  `~/Documents/MTM/mu-mac-tools/native/private-env.sh`.
- Five fixed-clock selection after scenes complete. Each +7 weapon has four passes over two
  saved draws. Ironclad's +9 excellent sword has eight passes, his +7 shield four and level-zero
  wings two. Every demo item has zero special fallbacks and zero refused effects.
- Ironclad's isolated sword controls have two / six / eight passes at level 0 / +9 / +9 excellent,
  with eight supported effects and zero refusals in each scene.

Final PNG comparisons, default world identity sweep, final documentation/audit and PR queue entry
are still pending. No PR-ready line has been written.
