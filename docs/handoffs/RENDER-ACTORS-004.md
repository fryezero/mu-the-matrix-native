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
