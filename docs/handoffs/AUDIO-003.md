# AUDIO-003: offline object callers and audio census

Branch `codex/audio-003`, base `d4af71dd`. Offline/static only. No original client,
launcher, live service, installed app or staged app is used or changed.

## WIP

Checkpoint in progress, 2026-11-11. Done: reproduced the 1,980 direct-call scan,
classified known owner anchors with an explicit unresolved remainder, identified
16 dropped native object callers, authored their world-specific adapter and
small original/native comparisons. The root baseline build passes. The small
original comparison passes 800 cases with all 16 sites reached. Five native
runtime checks pass, with the opt-in original check skipped in the portable run.

Left: finish the census source review, full corpus and compiled mutants, zone
music smoke, affected build/tests/validators, audit, latest-main integration,
publication and cleanup. Next step: finish the native zone test and register the
new validator. This checkpoint is not PR-ready. No ready-prs entry is written.

## Scope

The adapter forwards already-selected sound events. It does not change object
motion, RNG, gates or visual output. It handles Devias doors, Elbeland's seven
looped emitters, Uruk's type-20 emitter and Kardamahal's six sites. The single
added call in `native/world/parts/objects.c` is at the audio adapter boundary.
No world-object reconstruction or object runtime routine changes.

Ignis's two sound-0x570 sites cannot be distinguished by the existing id-only
callback. Other ambiguous same-id sites, stop requests without a native consumer,
event inputs, remote results, transformed/buff contexts and the opaque frame gap
remain refused. Music's static world/zone selector already has native delivery;
the new test verifies that path without adding a competing selector.
