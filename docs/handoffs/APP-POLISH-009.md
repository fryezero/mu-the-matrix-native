# APP-POLISH-009

## WIP checkpoint, 2026-11-11 21:40 Chicago

Done: read the complete lane/common briefs, APP-POLISH-007/008 and owning UI sources.
Built baseline root and `mu-world`; baseline binary SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Original collection resize `0x00ac09b2` calls `0x00aae4ae` for every non-null
handler. Unicorn: 60 cases pass. Native fit: 200 cases pass, no mutants yet.
The initial real-movie 640x480 probe confirmed the original fixed scales overflow.
An initial bounded fit keeps inventory, CharacterInfo, quest, Warps and trees above
the HUD. CharacterInfo now reads the same session records as the HUD; this is
presentation only. No fixture stat formula, combat rule or installed app changed.

Left: merge latest main including UI-WINDOWS-001 #372, finish original/static
layout evidence and compiled mutants, automate all-window/size and demo ownership
checks, inspect proof captures, run affected tests/validators plus reduced private
checks and the default identity sweep, finish research/status/PR documentation.

Next: merge `origin/main`, then include Command, Gens, PetInventory, Gremory and
MatchingSelect in the real-movie layout sweep. This checkpoint is not PR-ready.

Local inputs to resume: `~/Documents/MTM/mu-mac-tools/native/scratch/app-polish-009/`
contains the rebuilt baseline binary, preliminary logs and real-movie geometry.
The worktree is `~/Documents/MTM/worktrees/app-polish-009`.

## WIP checkpoint, 2026-11-11 22:00 Chicago

Merged main `710ac816`, including UI-WINDOWS-001 #372, as `66b4357c`.
The shared sizing conflict retained both creation sizing for presentation windows
and the universal resize dispatch. Root and client/world builds passed.
First focused private run: 5 tests pass in 72.042 s, including the five demo
characters and preliminary geometry for 272 window/size/backing-scale combinations.
The latter did not yet assert actual visibility. The strengthened test adds that
assertion, open-window resizing, original map mask/centering and pointer close
activation. QuestSummary's generic show route now uses its actual open/close
methods. The recording host distinguishes quest/tree close delivery from owning
controller behavior.

The strengthened layout run is waiting in the foreground for load <=14 with free
memory >=25%; no result claimed. Research and the validator manifest row are now
written. Compiled mutants, final affected/private checks, identity sweep, captures
and PR-ready documentation remain. Resume with the pending strengthened-test log
under this lane's scratch, then the selective checks. No ready-prs entry yet.

## WIP checkpoint, 2026-11-11 22:20 Chicago

Final production source is `6c62c838`. Latest fetched main remains `710ac816`.
Final root build: 1.333 s; explicit client/world rebuild: 12.862 s; repository
audit: 2,193 staged files, 0 rejected, 25.590 s. Rebuilt final mu-world SHA-256
`e90d3754d2e90cd6b9d1d6484861f6c53d30c08f5ebb11df2a185415a072a4d8`, distinct
from the baseline above. HUD width/bottom arithmetic is now covered by the
compiled-negative-control definitions as well as panel fitting, ten mutants total.

Strengthened layout run: pointer close delivery for all sixteen panels and
open-window resizing pass. One 1024x699 subprocess refused startup without stderr;
its isolated rerun, at both backing scales with map checks, passed in 5.542 s.
The first strengthened matrix had all other sizes pass. A full final private
run is still required; no completion claim from the initial refusal.

Post-build selection: 11 validators, 133 portable work items, including 129 native
modules. Thus private checks use **8d reduced**. The pending private-selection log,
then affected no-mutant validators, ten changed-target mutants once, affected
portable tests, focused private fixture/UI checks, identity sweep and endpoint
captures are next. No PR or ready-prs line yet. All logs remain in the lane's
scratch directory named above. Runtime code and docs are checkpointed remotely.

## WIP checkpoint, 2026-11-11 22:40 Chicago

All 11 affected validators passed at HEAD `6ea82f67` with no mutants, 122.046 s
including selection. The changed-target run passed all 4,668 cases and caught
10/10 compiled mutants, 6.688 s. Families: 60 original resize-dispatch cases,
4,096 native panel-fit cases and 512 native HUD-fit cases. No failures, errors
or skips. Full per-row reports are in `verify-runs/lane-validators` and
`verify-runs/lane-mutants` in this worktree.

The affected portable run is active, 38 suites / 133 work items / two workers.
The canonical private selection is 164 work items, so **8d reduced** applies.
The queued private command is `native.tests.test_app_polish9`,
`native.tests.test_app_polish5.PrivateGroundSkill`, and `native.tests.test_ui_windows`.
After those: endpoint captures, one rebuilt default identity sweep, final
research/handoff/status lines, audit, PR and ready-prs entry. No ready entry yet.
Production source remains `6c62c838`, with the rebuilt binary hashes recorded above.

## WIP checkpoint, 2026-11-11 23:00 Chicago

Affected portable run passed: 1,405 tests, 1,149 passed, 256 skipped, zero
failures/errors. Runner wall 469.5 s; command including selection 562.633 s.
The reduced private run completed 11 methods in 128.386 s. Layout, resize,
pointer-close, original resize, both skill regressions and all presentation
checks passed. DemoOwnership had five subtest failures: four used an incorrect
GFx log spelling; Windleaf additionally exposed real missing seed metadata.
The fixture had level 320 / 318 points, while its session seed remained 1 / 0.

Fixed in this checkpoint: append authored points to the development-only seed,
copy level/points from the existing fixture join, and seed the hero's points.
Vitals and formulas are unchanged. The invoke-log assertion is corrected.
An explicit portable metadata round-trip and original alignment assertions are
added. These changes still need rebuilding and verification. The prior validator
and portable results cover the earlier source, not this metadata fix.

Next: run the new metadata unit; rebuild root and client/world; reselect affected
checks with the seed-header 6b closure; rerun affected no-mutant validators and
portable suites; private AppPolish9 and the focused skills/UI checks. Layout
mutants already passed 10/10 and their compiled inputs are unchanged. Then
captures, default identity, final docs/audit/PR/ready line. No ready entry exists.

## WIP checkpoint, 2026-11-11 23:20 Chicago

Merged latest main `fb747e42` as `d2b5fd0c`, retaining every upstream validator
and APP-POLISH-009's row. Manifest parses with 227 entries and no conflict markers.
Upstream includes AUDIO-003, INNER-002 and prior actor/Muun/aura work, so earlier
compiled-input checks need a post-merge selection/rerun. Production metadata fix
is in `2919c022`; current test/merge head includes `dfaaabee` and `d2b5fd0c`.

New portable metadata unit passed in 0.276 s, command 0.371 s. Root rebuild
16.925 s, client/world rebuild 24.487 s. Actual five-character check now agrees
on names, profiles and Windleaf's 320/318; its remaining HP-line assertion failed
because original charinfo.tsv masks rows 26/27/34/35 out for all classes. Verified
that mask and the actual SetName feed. The test now checks original active level,
points and stat rows, conditionally checking HP only if the asset enables it.
No row is invented or enabled. This corrected test still needs a passing rerun.

Endpoint captures inspected, opaque, demo Ironclad only: 640x480 and 2560x1440,
23.759 s. Small SHA-256 `479d107cd7b3c499e732c015b8906395376816386647b4d126b73e658c21112d`,
large `2b4aa4da31eea1fb6a6c3e514eb1caea70e598ad7d624240e99b17a40877e1ae`.
They are in the lane's renders directory and predate this upstream merge; layout
and fixture sources were unchanged by that merge. Final captures can supersede them.

Temporary control worktree `~/Documents/MTM/worktrees/app-polish-009-base` is
owned by this lane, detached at `fb747e42`, and building in the foreground. This
replaces the unused d4af71dd baseline before the ONLY default identity sweep,
so inbound world/audio visuals cannot be mistaken for this lane's changes.
No before sweep has run yet. Finish the control build, rebuild this branch,
run corrected private tests, affected post-merge validators and portable tests,
identity, final docs/audit/PR/ready line. Keep respecting the 02:15/02:30 cutoff.

## WIP checkpoint, 2026-11-11 23:40 Chicago

At `122b088e`, both merged builds passed: root 20.705 s, client/world 21.190 s.
Reduced private checks passed all 12 methods in 100.443 s (command 100.565 s):
five demo profiles and actual CharacterInfo rows, 272 panel/size/backing-scale
combinations, 48 resize-panel checks, sixteen pointer-close deliveries, original
resize instructions and focused skill/presentation regressions. The ownership
test builds and privately copies its binary. No remaining assertion failures.

Own selection is 27 validators; changes since the previous tested `6ea82f67`
select 102, union 106. These include conservative compiled-input fallbacks and
must not be dropped. Before running them, fetched main again: ITEMS-UI-001 #379
is now merged at `626abce1`. Merged as `0f82133e`; only conflict was the shared
manifest append, resolved retaining both rows. All 227 upstream entries are
identical and APP-POLISH-009 makes 228. No inventory icon/cursor edits of ours.
The control worktree fast-forwarded to the same upstream. No identity sweep has
run, so the control baseline can still be rebuilt once before the only sweep.

Next: rebuild control world and branch root/client/world; rerun private UI checks
including the incoming hover module; reselect the validator union (including
validate_items_ui), run it without mutants, run affected portable tests, take
final captures and the single default identity sweep, finish docs/audit/PR/queue
and cleanup. The ten fit mutants already passed once; their inputs are unchanged.
No ready-prs entry yet. Respect the 02:15 WIP / 02:30 stop deadlines.


## WIP checkpoint, 2026-11-11 23:59 Chicago

Final merged source/test head is `7e97044e`, with main `626abce1` (#379).
Control world rebuilt in 6.748 s; branch root 0.799 s; client/world 14.180 s.
Distinct rebuilt mu-world SHA-256 values: control
`0486f35e813b641f2500df6b0107515c33d3fb37d2cc3683005c8b91b08b10ef`, branch
`6f44d4de3913304dfee686528d04c20573942cdbea55f84423df3b33176e58be`.
No before renders have run yet. Corrected tour22's stale local path prefix in
this lane's private manifest copy before rendering; shared inputs are unchanged.

Final reduced private run passed 19/19 methods, no skips/failures/errors,
147.546 s (command 147.640 s), including the incoming equipment-hover module.
Final selectors: own 27 rows, since `6ea82f67` 107 rows, union 107; 30.926 s
and 34.038 s active selection walls. The full union is running without mutants,
two workers, canonical private environment and cache. Current totals:
{'pass': 41, 'fail': 0, 'error': 0, 'skip': 0}. Reports: `verify-runs/lane-validators-final`.
The fit header and its validator/imported original helper are unchanged since
the passing ten-mutant run. The only later edit is research wording.

Left: finish this validator run; affected portable tests; final endpoint captures
and one default identity sweep; final docs/audit/PR/ready line and owned cleanup.
Do not run more unchanged mutants, a full lane gate, an installation or a merge.
No PR or ready entry yet. Resume logs are in the lane's named scratch directory.
