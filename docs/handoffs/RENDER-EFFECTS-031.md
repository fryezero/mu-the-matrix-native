# RENDER-EFFECTS-031

Branch `codex/render-effects-031`, from main `b7dfd2ed`. Offline/static only, no subagents.
The steward owns the full gate and merge. This is a WIP checkpoint, not a ready handoff.

## WIP

Done:

- Preserve an explicitly rebuilt starting-main `mu-world`, SHA-256
  `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- Implement eleven particle consumers (eight requested world pairs, clouds/16,
  Flame01/12 and charge Spark03/2), six joints (Remain/8,9,10, spark/5,
  Swell Life spirit/2 and its flare/2 child) and five effect pairs (ground/4,
  charge/0, Flame01/6 and Muun transition 0x47a/0,1).
- All 5,302 focused checks pass at 80 per pair, including original effect draw dispatch
  and native raster fixtures, 25.124 s script / 34.206 s with reconstruction/world builds.
  Directed clouds/16 boundaries corrected its live-at-10 cutoff and .01 light rise/.2 cap.
  The final 1,371-check sample includes both bitmap loaders, the original model loader,
  frozen census and extended census, all passing in 5.105 s. The installed transition-model
  test also passes, 1.917 s.
- At `d7aaa0d5`, all 66,051 full-sample checks pass. The initial 69-control run detects
  68 controls in 284.976 s, with zero original stops. The life-10 control survives because
  its sample lacks a live in-range record at exactly life 10. Add that deterministic case;
  the 1,371-check / one-control follow-up passes in 6.348 s and detects the remaining control.
  No successful mutant is rerun and production C is unchanged.
- Add original-loader Flame01/water bitmap registrations and DarkLordSkill model routing.
- Capture default and Aida/Remain close-up before scenes and four before skill scenes.
  Initial baseline driver errors repeated the default sweep while fixing manifest paths.
  Final after replay takes 90.570 s including skills. Default captures are 91/92 PNG-identical;
  only Remain frame 24 changes. Aida close-up stays identical; Remain close-up refusals
  fall 64→0. Skill refusals: Swell 38→0, Penetration/416 2→1 each, Blood Storm 1→1.
  The after binary is `151d54f4df743061c705bcc72615ec808e5dfae4e2398fd9e348abcbadaefdfe`.
- Native charge children retain their effect-slot owner in both world and combat adapters.
  Both installed Penetration scenes accept 33 charge particles, zero child refusals, then retire.
- Add per-pair compiled controls and arithmetic/state controls, 69 planned mutants.
  Add original bitmap registration checks and a separate 25-pair world/skill census.
  Existing frozen item census remains 110 programs / 37 pairs.
- Inspect Blood Storm 0x583/0 and child 0x584/0: the constructor is insufficient proof;
  child mover reads an undeclared owner +0x3b field. Both remain refused. Penetration
  child 0x46c/0 and optional target ice remain refused.

Left:

- Complete the other 76 selected private validators, portable work items and 8d reduced.
- Extend the census with explicit denominators, refusal counts and fixture render QA.
- Root build, post-build affected selection, portable/private validators, 8d reduced,
  affected-world fidelity, after identity, audit, latest-main integration and final PR.

Next step: run extra fidelity/Trials fixtures, the other 76 selected validators, 171 portable
work items and 8d reduced for nine focused modules. The private native selection is 160
work items, exceeding the 40-item cost cap. Retain all three validator fallbacks.

The frozen Native Data copy has none of DarkLordSkill.bmd, Flame01.OZJ or water.OZJ.
Full read-only game data supplies all three for these proofs. A later data-refresh lane must
include them; no installed bundle/data copy was changed.

Private working files are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-031/` and
`renders/render-effects-031/`. They contain no new client capture and are disposable at completion.
Pool caps and private RNG/counter sources are unchanged. No installed app, live client or README work.
