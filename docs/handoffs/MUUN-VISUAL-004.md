# MUUN-VISUAL-004

WIP on `codex/muun-visual-004`, based on main `b7dfd2ed`. Offline/static only.
The merge steward owns integration. No installed app or effect consumer edits.

## What draws

The opt-in kind-1 fixture can now place an authored rider on the eight existing secondary skeletons.
`MU_MUUN_FIXTURE=<kind-1 id>`, `MU_MUUN_MOUNT_FIXTURE=1` and `MU_MUUN_RIDER_FIXTURE=1` enable it.
The rider uses the existing unarmed action consumer with authored stand/walk/run/attack categories,
then the secondary action map. Rendering temporarily borrows the hero's renderer and restores its
parameters and animation state. No logical position, equipment, stats or authoritative feed is changed.

`MU_MUUN_OWNER_KIND_FIXTURE=2` supplies the fade input. `MU_MUUN_BUFF18_FIXTURE=1` selects the original
local-owner mode-10 mesh pass. Both require the mount fixture. Secondary model-specific requests use
existing particle entry points; missing consumers are counted. `MU_MUUN_REMOTE_FIXTURE=1` supplies an
authored 3-second remote expiry and one 0x47a request. Consumer refusal remains explicit.

Appearances 356/357/375/376/377 now admit 3/3/7/8/4 mesh rows respectively through the same appearance
fixture flag. Two render-time light rows and two atlas rows are instruction-compared. The three bone-effect
branches, four actual rows, remain refused. Appearance 357 additionally refuses its unavailable mesh 3.

## Checks so far

- Root build passes. Focused secondary module: 5/5 pass after adding its missing data-decoder build dependency.
- New original comparison: 890 cases, zero mismatches. All 22 compiled mutants caught, 9.61 s.
- The GL rider proof is visible. New private module 5/5 passes, 33.75 s, including all eight riders,
  exact renderer restoration, GL/software buff/fade pixels and one remote expiry/refusal.
- Eight actual skeletons pass the extended native host. All 32 secondary requests per host are refused by
  existing particle consumers, with no effect-consumer change in this lane.
- One authored remote expiry emits one request, refused by the current 0x47a consumer boundary.
- Before identity baseline exists for 46 required views plus five exploratory views. Binary SHA-256
  `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.

Affected private validators: 40/40 pass at `8e992004`, 813.48 s including selection, no skipped rows.
The optional unchanged mutant switches were disabled. New rider mutants passed once separately.

## Limits and next

Affected portable tests, 8d reduced,
default after identity, audit, latest-main integration and PR-ready docs remain pending.
The five special models now draw 25/30 rows. Four bone-effect rows and appearance 357 mesh 3 remain refused.
The installed 357 skeleton has only meshes 0..2. Code 363 still cannot supply actions 3/4.
The fixture authors its initial ride pose and clock. Full original creation/render ordering is not compared.
No production selection, inventory, power, packets, authoritative targets, process-clock or live-scene parity.

The first portable batch passes: 1,543 tests, 1,269 passed, 274 skips, zero failures/errors, 460.08 s.
It predates the final special-row integration. The special-row root build passes in 11.70 s; its private
module passes 3/3 in 16.03 s, with 450 original cases and GL/software controls for all five models.
The new special-row mutant set and affected refresh remain pending.

## WIP

Done: recovered rider gate/placement, secondary request producer, owner-kind-2 subtraction, buff mode and
remote expiry. Native integration builds; focused prior secondary tests pass. New tests and mutant row added.
Left: special-row mutants, final affected refresh, reduced private Muun modules, identity/proof checks,
research/status text and PR delivery.
Next: run the new special-row mutants once, then refresh the affected validators/tests and finish delivery.

Scratch and proof renders are under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-004`.
No new future-lane input has been created. No ready queue entry exists yet.
