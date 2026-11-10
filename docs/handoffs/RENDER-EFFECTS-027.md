# RENDER-EFFECTS-027

Death Stab's offline base-DK fixture trail lane. Base `ff8e0543`, branch
`codex/render-effects-027`. No live client or network work. The installed apps
and the other lanes' item/world consumers are untouched.

## WIP

The caller branch at `0x0139959c..0x01399c9d` of the step helper `0x013966ea`,
called from MoveCharacter `0x013a9047`, is reconstructed with explicit model,
bone and world-predicate inputs. Steps 2..8 request three `0x472/2` ribbons;
steps 6..12 request two `0x10e6/1` markers. The markers emit `Flare/12` joints.
The native base-DK demo uses authored right-hand link bone 33. Missing
context is counted. The target CHARACTER write at `0x01399c81` is excluded.

- Iteration: 1,200 original-instruction comparisons, zero mismatches, 3.67 s.
  Caller, joint create/move/render, emitter create/move, 200 cases each.
- Baseline build and 46-entry default capture sweep completed before changes.
- Full focused comparison: 6,064 cases, zero mismatches, 20/20 compiled mutants, 50.74 s.
- Private changed modules: 18/18 tests, 24.41 s. EFFECTS-016 bitmap consumer repaired for NSkill; its two private tests and 23 mutants pass in 40.15 s.
- Affected portable run completed 157/157 work items, 1,718 tests. One stale EFFECTS-016 bitmap expectation failed and its focused repair passes; 284 portable skips.
- Installed GL DK proof: 189 requests, 14 emitters, 175 joints, zero refusals/hits/kills, one unsent cast; all four saved frames repeat byte-identically, 4.27 s. Baseline has no trail requests.
- Main through `9d6ce467` merged, including ACTORS-001. Build passes, 16.76 s.
- Left: final default identity result, 49 affected private validators, audit, final research/status/handoff and PR/ready line, cleanup.
- Next: finish the sweep and run the selected validators with two workers and no mutants. The merge steward owns the full gate. Do not append a ready line for this checkpoint.

Local resumable reports and baseline binaries are under
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-027/`.
