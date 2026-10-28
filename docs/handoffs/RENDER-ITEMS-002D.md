# RENDER-ITEMS-002 part 4

This slice extends the shared body recipes, adds the next two RenderLinkItem callers, and supplies the
Spark03 subtype-11 consumer. It resumes the existing worktree and preserves the earlier milestone evidence.
Only this worktree was used. The original client and launcher were left alone.

The implementation adds 164 item bodies, comprising 137 armour and 27 weapon types, and eleven class skins.
Item body coverage becomes **426/1,674**; skin coverage is **11/17**. The rank-3, 47-type armour cluster
`ac9ebab05935c051` is complete. The type/shape TSVs retain their original 18,601-state survey and update only
coverage membership. Wear frequency remains an inference from model indices.

The armour pulse executes the signed clock remainder, binary32 products and cosine branch of
`0x0185bdc4(-4,0)`, then adds 0.2 at `0x01705495`. Per-type recipes supply mesh/texture constants and choose
pulsed light only where required. Other recipes do not evaluate the pulse. The generator now groups helper
phases after scalar remapping, and probes all sixteen input levels for skins. Full-function comparisons
remain independent of recipe fitting. The skin kind-A test also respects the original item-record index
bound of `0x2c00`, matching the existing kind-B predicate.

The next link callers, `0x012c7a45` for mace-group type `0x0ef4` and `0x012c7e68` for sword type `0x0afc`, preserve
random consumption, per-sprite offsets, colours, scales and rotations. The sword uses frame time. All five
implemented targets, covering ten types, now have native consumers. Spark03/11's create, move and render
records are compared separately, including random consumption. The existing saved-pose adapter feeds the
particle pool, skips absent bones and handles exhausted pools. Hero, remote-player, NPC, ground and GFx
inventory bodies continue through the shared renderer; link effects remain character attachments.
The hero filename inference also recognizes the existing five ClassNN part families, including
HelmClass01 as 0x3700, with the model-codec stride and bounds. This supplies a class part type without
claiming authoritative equipment or resolving missing special-model files.

Local reports: `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002d/`.
Local before/after renders: `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002d/`.
Synthetic armour changes from three refused bodies/three fallback passes to zero refusals/18 passes;
three skin examples change to zero refusals/seven passes. Their added glow is intended. These are native
software renders on authored geometry, not live-client pixel comparisons. Earlier renders are preserved.

Remaining: **1,248 item bodies and six skins** (`0x3895`, `0x3896`, `0x389b`, `0x389c`, `0x389d`, `0x389e`).
The six skins take additional raw-level branches or emit effects, so their complete streams remain refused.
All seventeen skin scalar remaps are checked; that does not count as body coverage for the six. Fourteen
other fitting candidates were excluded after independent comparisons caught their ancient-tail light
behavior: `0x0b1b/0x0b1c`, `0x10fd`, `0x130a`, `0x1504`, `0x153b..0x1543`. Diagnostics remain local.
The next untouched large armour shapes have nineteen types each (`c2dc4acbcd235d05`, `ef7283f9b1892031`).
The next link target is `0x012c807d`, type `0x0afd`, from the original static switch.
Further link callers, mesh overrides, selection/shadows/buffs/record-kind limits, authoritative hero items,
missing model mappings and the earlier Box of Luck/NewUI limits remain open. Muun and nested map-object
placement remain deferred. No live reads, game processes, terrain or per-world object files were used.

## Instruction evidence

Pinned text/data SHA-256 values and the executable identity are unchanged; see the finding's identity section.
`validate_item_expansion.py --mutations` passes **52,172 cases**, zero mismatches: 51,100 complete body/skin
streams (175 types times 292 states), 800 next-link caller streams and 272 scalar cases across all seventeen
skins. All **7/7 compiled mutants** are caught: pulse, mesh index, skin level, skin record bound, mace offset,
mace rotation and sword clock. Generator reproduction for both body recipes and skin scalar rules is checked.
A separate private test passes ten signed-clock boundary cases, including negative time, wrap and conversion
limits. `validate_item_effects.py --mutations` passes **1,500 cases**, 500 each for Spark03/11 create/move/render,
zero mismatches, **3/3 mutants** caught. New instruction evidence totals **53,682 cases and 10/10 mutants**.

Portable examples cover pulsed armour, restoration of light for later passes, skin remaps/refusals, the
record bound, time-varying sword colours and exact mace offsets. Native tests cover class-name inference,
saved transforms, missing bones, exhausted sprites and the formerly unsupported particles. The two new
validators have owning private tests and manifest rows. The native shared adapter, its world call sites and
the no-owner/random limitations were reviewed separately from the emulated command streams.

Part-3 regression passes **74,292 cases**, zero mismatches, **8/8 mutants**. Part-2 regression passes
**135,176 cases**, zero mismatches, **6/6 mutants**. Together with the new families and clock controls,
this run has **263,150 instruction comparisons, zero mismatches and 24/24 compiled mutants caught**.
These counts retain the distinct scalar/body/caller/transform/particle boundaries above.

## Release gate and review

`bash scripts/local-macos-ci.sh` passes on the tree merged with main `3526a0a`: **1,403 tests across
38 discovery runs, 170 explicit private/unavailable-input skips**. The fixture suite, native viewer,
reader builds and publication audit pass; **1,265 files audited, zero rejected**. No hosted CI was run.
Spark03/11 also reruns after the parallel particle changes: 1,500 equal cases, 3/3 mutants.
The initial gate caught a missing header in the ClassNN hook; the include is fixed, the native host and
six renderer tests pass, and the complete gate was rerun on the stable integrated tree.

Self-review against the owner brief, repository standards and task scope found no blocking issue in this
bounded slice. The six refused skins, rejected probe candidates, native type/model limits and all deferred
systems remain explicit above. No other agent worktree or main-checkout file was edited or built in.
