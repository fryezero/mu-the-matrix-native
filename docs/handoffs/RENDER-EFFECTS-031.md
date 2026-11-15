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
- All 2,440 focused original-instruction create/move/render checks pass (40 per pair,
  11.002 s script / 13.502 s including reconstruction builds). No mutants run yet.
- Add original-loader Flame01/water bitmap registrations and DarkLordSkill model routing.
- Capture default and Aida/Remain close-up before scenes and four before skill scenes.
  Initial baseline driver errors repeated the default sweep while fixing manifest paths;
  the completed baseline is retained. No after result yet.
- Inspect Blood Storm 0x583/0 and child 0x584/0: the constructor is insufficient proof;
  child mover reads an undeclared owner +0x3b field. Both remain refused. Penetration
  child 0x46c/0 and optional target ice remain refused.

Left:

- Complete directed boundaries, native pool/raster tests, original render dispatch
  for effect pairs and compiled mutants.
- Extend the census with explicit denominators, refusal counts and fixture render QA.
- Root build, post-build affected selection, portable/private validators, 8d reduced,
  affected-world fidelity, after identity, audit, latest-main integration and final PR.

Next step: finish native raster coverage and original render dispatch, then run the final checks.

Private working files are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-031/` and
`renders/render-effects-031/`. They contain no new client capture and are disposable at completion.
Pool caps and private RNG/counter sources are unchanged. No installed app, live client or README work.
