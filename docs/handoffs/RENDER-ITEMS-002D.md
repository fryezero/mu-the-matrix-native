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

The next link callers, `0x012c7a45` for axe type `0x0ef4` and `0x012c7e68` for sword type `0x0afc`, preserve
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
Further link callers, mesh overrides, selection/shadows/buffs/record-kind limits, authoritative hero items,
missing model mappings and the earlier Box of Luck/NewUI limits remain open. Muun and nested map-object
placement remain deferred. No live reads, game processes, terrain or per-world object files were used.
