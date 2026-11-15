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
Special mutants: 16/17 caught in 6.77 s. The fade-speed mutant was initially hidden by clamping.
Two deterministic unsaturated cases were added; its focused retry compiles and catches it.
All 17 distinct special mutants are now caught, with the other sixteen not repeated. Full baseline now 452 cases.
Affected refresh remains pending.

## WIP

Done: recovered rider gate/placement, secondary request producer, owner-kind-2 subtraction, buff mode and
remote expiry. Native integration builds; focused prior secondary tests pass. New tests and mutant row added.
Left: final affected refresh, reduced private Muun modules, identity/proof checks,
research/status text and PR delivery.
Next: refresh the affected validators/tests for the special-row source, then finish private/proof/identity and delivery.

Scratch and proof renders are under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-004`.
No new future-lane input has been created. No ready queue entry exists yet.

## Final source verification checkpoint

At source/checker commit `76f42724`, the 36 rows selected since `8e992004` pass in 628.46 s,
zero failures/errors/skips. Five earlier rows have unchanged inputs and retain their passing results:
helpers, mount visuals, pets, raven and world fog. The steward union is 41 rows.

The final affected portable refresh since `59822bfc` passes 1,478 tests: 1,208 passed, 270 explicit
skips, zero failures/errors, 434.60 s including selection, 163 work items. The first batch covers the
unchanged work items. Main remains `b7dfd2ed` at the 22:40 check.

Only the combined reduced private Muun run, final native proof/default identity, delivery docs/audit and
PR/cleanup remain. No further production C change has been made since the verified special-row source.

## Main integration checkpoint

Main AUDIO-004 at `2b0b2716` is integrated; the registry conflict keeps both new Muun rows and the incoming
audio row. The merged root build passes in 21.20 s. The final pre-merge private Muun run passes 19/19 in
60.40 s; the 35 inspected GL proof images pass in 24.12 s. Pre-merge default identity passes all 230 required
files plus 46 stderr logs with different before/after binary hashes.

Done: all Muun source, tests, original comparisons, mutants, final pre-merge proof/identity and status lines.
Left: resource-guarded affected checks for incoming compiled audio inputs, merged proof/identity and final audit.
Next: list the affected rows and modules after the merged build, run only that refresh, then replace WIP with
the complete handoff, push, open PR, append ready queue and clean up.

## Merged validator checkpoint

The exact current-main diff selects 42 steward rows (46.36 s selection), including incoming AUDIO-004.
The 28 rows with changed compiled inputs since `76f42724` pass at `fed9a7a4`: 567.78 s execution plus
105.58 s selector preview, zero failures/errors/skips. The latest results for all 42 rows total 745,557
reported cases; fourteen rows retain their unchanged earlier inputs and passing results.

Done: merged root build and complete merged affected validator refresh.
Left: merged portable/private Muun checks, after-only native proof/identity and final audit/delivery.
Next: wait for resource load to fall, inspect and run the affected portable selection, then finish.

## Second main integration checkpoint

The AUDIO-004 merged portable run passes 1,769 tests (1,446 passed, 323 skips), zero failures/errors,
443.64 s; its preview selection costs 56.97 s. Reduced private Muun tests pass 19/19, zero skips, in
76.02 s. The 35 refreshed proof PNGs and contact sheet are byte-identical to the inspected first set
(17.36 s rendering). Explicit world rebuild check passes in 0.34 s. Binary SHA-256
`25024c17935ce37245cbf895bf84444e321deec2c361a0b120e38cd3cbe389a4` differs from the baseline.
After tours (20.30 + 55.93 s) and 0.22 s comparison pass 92 PNGs, 92 dumps, 46 normalized reports
and 46 stderr logs, all unchanged.

A final fetch found new main `4babc900`, including RENDER-ACTORS-005 and RENDER-WORLDS-INNER-004.
Both are now merged without conflict. No Muun source changes were authored for this integration.
Done: every AUDIO-004 merged source check and identity/proof control passed.
Left: build/select and refresh only checks whose compiled inputs the new main changes; final proof/identity,
audit and delivery. Next: build the integrated tree, inspect the exact affected selections, run the refresh.

## Actor/world validator checkpoint

At `88420149`, all 32 rows selected for the incoming actor/world compiled changes pass, zero failures,
errors or skips: 621.77 s runner plus 134.32 s preview selection. The exact current-main diff selects
43 steward rows (39.58 s preview), adding actor monsters. Eleven unchanged earlier rows retain passing
results. No Muun C/checker source changed.

The remote fixture test now checks one accounted created/refused result and adds a forced `--no-particles`
refusal control, rather than requiring another lane's 0x47a consumer to remain absent. Current observed
consumer results remain zero created/one refused. The new control still needs its final private run.
Done: integrated build and all actor/world affected validator refreshes.
Left: focused riding row for the test edit, portable/private checks, final proof/identity, audit and PR.
Next: resource guard, focused row, then the selected portable refresh.
