# RENDER-ACTORS-004

## WIP

Branch `codex/render-actors-004`, based on ACTORS-003 ready head `a2398637`.
Offline/static only, no subagents. Deadline 02:30 on 2026-11-12. No ready entry.

Done: binding briefs and actor handoffs read. All 1,024 fixture class selectors,
601 monster and 147 NPC opener selectors audited with the existing original
constructor/opener machines. The first class census is recorded in
`docs/research/actor-construction-census.csv`. Construction coverage is bounded
by world 0, rand 0 and the explicitly declining processors of NATIVE-ACTOR-001.
There are 963 extracted constructors and 61 unresolved original contexts.
Native body plans before this lane: 28 bounded correct, 916 incomplete or
unverified special passes, 80 refused. These are not whole-client fidelity counts.

Five shared NPC composites are being implemented: 230, 248, 250, 253, 255.
OpenNpc requests 22 Female/Man/Girl part files. Constructors select three or
four per actor. Original whole RenderCharacter part plans execute with named
base-body and declining world-service stubs. Native loading and shared posing
are provisional. No canonical placements changed.

Baseline build and explicit world rebuild pass. One-time default sweep passes
for 46 views, 230 file hashes, 61.0 s. Binary SHA-256:
`1be079965a22399f472ca6c7d0f657fa67b62e46b9a47ba6f6c5e7b100d34440`.
Only report output-directory prefixes are normalized. Baseline hashes and
scripts are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-actors-004/`.

Left: native iteration, refusal/file/pose/draw controls, compiled mutants,
complete opener census export, affected checks, reduced private native tests,
one demo render per new class, after identity sweep with rebuilt world binary,
main integration, final docs, PR and ready-prs entry, cleanup.

Next: validate the five NPC composites before expanding any monster action
or lifetime branch. Classes 374/378/617/642 retain ACTORS-003's refusals.
The nine monster secondary-load openers remain leads for action/debris work.

Checkpoint, 21:48 on 2026-11-11: the corrected constructor kind-1 iteration
passes 1,205 checks, zero mismatches, 10.7 s. Native host loads all five classes
in worlds 0 and 3, finds zero missing textures and advancing matching frames.
The initial kind-4 assumption was rejected before admission; the constructor
retains CreateCharacter's proved kind 1. Root build passes, 13.0 s of execution
plus a two-minute resource wait. Focused portable tests pass two, with one
expected private-data skip. Full census export passes 963 constructor/table
comparisons and lists 748 opener selectors, 16 secondary-model openers and 42
secondary model loads. New bounded body plans move 28 to 33, incomplete or
unverified special passes 931 to 926, refused remains 65. Final mutant,
affected, render and identity checks have not run. This is WIP, not PR-ready.

Census policy correction after the first checkpoint: 13 no-opener classes and
eight unregistered NPC model indices also fail the current native loader.
They move from incomplete/unverified to refused. The corrected after totals
are 33 bounded body plans, 905 incomplete/unverified and 86 refused, out of
1,024 fixture selectors. The first checkpoint's 65-refusal figure was incomplete.

The final loader audit also retains the six existing EffectManager overrides
750/751/752/753/758/873, which resolve before the core class table. The core
machine leaves them unresolved, but the native loader already draws their
separately extracted recipes. Final after totals are therefore 33 bounded body
plans, 911 incomplete/unverified and 80 refused. The CSV names these overrides;
this supersedes both earlier provisional refusal counts.

Checkpoint, 22:17: corrected census regeneration is complete. All 963 core
constructor records agree with the native table's model, opened selector,
scale, class byte and nine slots. The 1,024-row class CSV now includes native
EffectManager overrides; totals are 33 / 911 / 80 as above. The 748-row opener
CSV separates extra bitmap and sound loads. Sixteen openers request 42 secondary
models. Census execution took 9.6 s after 14 minutes of resource waits.

Selection after a rebuilt world binary: 24 validators, all three symbol
fallbacks retained; 161 affected suite items. Full runs remain pending.
The native host now checks actual assembly scale and zero draw refusals; the
new validator has ten compiled mutant controls registered, not yet run.

Checkpoint, 22:37: main through UI-WINDOWS-001 `710ac816` is integrated as
`d835c137`. Documentation conflicts retained both lane summaries. Integrated
root build and explicit world rebuild pass, 7.5 s and 6.6 s.

All 24 affected validators pass at `d835c137`: 107,832 row checks, zero failures,
errors or skips, 494.3 s including selection. The new composite row passes 1,427
checks in 8.8 s. Its once-only compiled mutant run passes all ten controls,
49.7 s. Evidence breakdown: 389 original-instruction/loader comparisons,
1,028 authored refusal controls and ten native contexts. Existing actor recipes
pass all 1,669 checks, 102.3 s. Only the new row ran compiled mutants.

Portable affected tests are running. Reduced private tests, five actor renders,
final rebuilt-binary identity, final audit/docs and PR-ready delivery remain.
No production code has changed since `95d9f97c`; the subsequent source additions
are test/census checks and the incoming main UI lane. No ready entry exists.

Checkpoint, 22:57: first portable affected run passed 1,495 tests, 1,246 passed
and 249 expected private-data skips, zero failures/errors. Runner wall 440.1 s;
overall command 650.5 s, including selection and a 120 s resource wait.

Main through `6b75fbda` is integrated as `e7d97c92`, including #373's steward
merge. All status entries and validator rows were retained. Actor behavior and
mutation targets did not change. One new-source comment now uses the verified
exclusive NPC branch end `0x01808e23`, from the pinned jump table.

The merged root build passed in 17.0 s after 480 s of resource waits; explicit
world rebuild passed in 7.0 s after 240 s of waits. After binary SHA-256 is
`b3bcddd6409b8988554051c2e980e02cfd0e737624e2eef235ddb6176452f161`.
The limited validator delta against `d835c137` is queued. Post-merge affected
portable tests, reduced private tests, all proof renders and the final identity
sweep remain pending. No ready entry; this is still WIP.

Checkpoint, 23:19: all 22 selected main-merge delta validators pass at
`aa330645`, 106,052 row checks, zero failures/errors/skips. Overall 769.4 s,
including 360 s of resource waits and selection. `validate_app_polish1/2`
were pruned because their compiled inputs did not change; their earlier passes
at `d835c137` remain current. Composite row 1,427 checks / 11.0 s; existing actor
recipes 1,669 / 112.8 s. No mutants repeated.

Post-merge portable run passes 1,773 tests: 1,481 passed, 292 expected skips,
zero failures/errors. Runner 384.8 s, command 596.8 s including selection and
120 s resource wait. It selected 165 work items, above the private cap. Reduced
private tests are queued; actor renders, identity and final delivery remain.
Class 617's optional file lead was checked against the 740 completed ordinary
openers. None registers `0x5ba`; eight NPC openers remain unresolved. No guessed
filename or body admission was added.
