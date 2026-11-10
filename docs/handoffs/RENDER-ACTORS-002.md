# RENDER-ACTORS-002

## WIP

Base `a2ad8814`, branch `codex/render-actors-002`. Offline/static only; no subagents.
Nine candidate kind-1, class-byte-0 whole-body recipes are implemented for classes
372, 373, 503, 548, 616, 646, 706, 806 and 807. All are level zero with empty equipment.
Their subtype files come from the pinned startup AccessModel calls. The actor loader
reuses OpenTexture's existing name-map and Item/Texture retry for missing body textures.

Done: binding brief and predecessor handoff read, baseline build and one-time default
scene hashes saved, portable census/recipe checks pass. The corrected private iteration
passes 565 checks in 56.0 s, including 32 native loads with zero missing body textures,
216 kind controls and six native refusals. Its small body-hook sample is 105 cases.
The first iteration's signed loader-number, event fixture and Item/Texture failures
are fixed. Final counts and mutants have not run.

Left: final original comparisons and changed mutants, actual native loads and refusal
controls, demos, affected checks, final identity sweep, self-review and PR-ready delivery.
No ready entry has been written.

Next: inspect the private iteration report, then finish the bounded nine-row set.
Six other rows stay refused: 374 and 642 need companion construction/lifetime;
378 needs its appearance/effect branch; 625/626 need action-dependent hooks; 617's
startup model file is unresolved. Do not admit these as plain bodies.

Local reports and baseline hashes are in
`~/Documents/MTM/mu-mac-tools/native/scratch/render-actors-002/`.
No installed app or data was changed. Temporary outputs are removed at PR-ready.
