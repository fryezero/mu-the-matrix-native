# RENDER-EFFECTS-027

Death Stab's offline base-DK fixture trail lane. Base `ff8e0543`, branch
`codex/render-effects-027`. No live client or network work. The installed apps
and the other lanes' item/world consumers are untouched.

## WIP

The caller branch at `0x0139959c..0x01399c9d` of the step helper `0x013966ea`,
called from MoveCharacter `0x013a9047`, is reconstructed with explicit model,
bone and world-predicate inputs. Steps 2..8 request three `0x472/2` ribbons;
steps 6..12 request two `0x10e6/1` markers. The markers emit `Flare/12` joints.
The native base-DK demo uses its equipped weapon's authored link bone. Missing
context is counted. The target CHARACTER write at `0x01399c81` is excluded.

- Iteration: 1,200 original-instruction comparisons, zero mismatches, 3.67 s.
  Caller, joint create/move/render, emitter create/move, 200 cases each.
- Baseline build and 46-entry default capture sweep completed before changes.
- Native tool build passes. Portable DK render checks are in progress.
- Left: complete lifecycle comparisons, compiled mutants, affected checks,
  installed-data render and before/after counters, final byte-identity sweep,
  research/status docs, final-main integration, PR and ready line, cleanup.
- Next: inspect the focused native test, finish the lifecycle family, then run
  the full new-validator count and its mutants once. The merge steward owns
  the full gate. Do not append a ready line for this checkpoint.

Local resumable reports and baseline binaries are under
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-027/`.
