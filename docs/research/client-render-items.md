# Item rendering, RENDER-ITEMS-002

Part 1 covers RenderItem3D's restored special-code chain and native inventory integration.
[Part 2 below](#part-2-bounded-body-and-link-effects-render-items-002b) adds 103 scalar remaps,
11 body types and six bow link effects. [Part 3 below](#part-3-body-clusters-and-offset-links-render-items-002c)
raises body coverage to 262/1,674 and records exact remaining branches.
[Part 4 below](#part-4-armour-weapons-skins-and-spark03-render-items-002d) raises it to 426/1,674, adds
eleven skins and consumes Spark03/11. [Part 5 below](#part-5-remaining-skins-and-ranked-body-clusters-render-items-002e)
raises coverage to 501/1,674 bodies and 17/17 skins, with seven link targets/twelve types consumed.
Part 6 reaches 559 bodies and consumes ground/inventory skin sprites.
Part 7 reaches **635/1,674 bodies**, preserves **17/17 skins**, and consumes **twelve link targets/seventeen types**.
Part 8 reaches **662/1,674 bounded bodies** and **fourteen link targets/nineteen types**.
Its rank-5 no-owner mesh streams draw; the owner effects (19/19 types) are verified by [RENDER-EFFECTS-005](client-render-effects-005.md).
Part 9 reaches **769/1,674 bodies** and **fifteen link targets/twenty types**.
Part 10 reaches **880/1,674 bodies** and **seventeen link targets/twenty-two types**.
Part 11 reaches **967/1,674 bodies** with per-type wave/sine scalar programs; links are unchanged.
[Part 14 below](#part-14-recordquality-probes-exit-model-fields-and-body-random-render-items-002n) reaches **1,213/1,674 bodies**.
[Part 16 below](#part-16-census-of-the-455-remaining-bodies-and-derived-body-programs-render-items-002p) reaches **1,276/1,674 bodies** and groups the rest by blocker.
[Part 17 below](#part-17-owner-effect-programs-of-the-armour-bodies-render-items-002q) reaches **1,319/1,674 bodies** with owner-effect programs.
[Part 18 below](#part-18-pre-draw-effect-programs-on-the-items-own-bones-render-items-002r) reaches **1,345/1,674 bodies** with pre-draw programs on the item's own bones.
[Part 20 below](#part-20-integer-registers-runtime-branches-and-joints-in-pre-draw-programs-render-items-002s) reaches **1,359/1,674 bodies** with integer registers, runtime branches and joints.
[Part 22 below](#part-22-frame-counter-object-bone-positions-random-vectors-and-post-programs-render-items-002t) reaches **1,363/1,674 bodies** with the frame counter, OBJECT-bone positions, random vectors and post programs.
[Part 23 below](#part-23-pre-draw-particles-without-an-owner-and-armour-owner-programs-in-the-world-render-effects-021) serves the pre-draw particles without an owner and runs the armour owner programs in the world.
[Part 24 below](#part-24-the-inventorys-equipment-and-its-icons-effects-inventory-fx) draws the inventory's equipment and its icons' effects.
[Part 25 below](#part-25-the-wings-physics-capes-render-items-cloak) draws the wings' capes as the client's physics cloth.
[Part 26 below](#part-26-the-rendered-frame-counter-in-body-draws-the-wing-joints-and-the-world-callers-render-items-002u) reaches **1,364/1,674 bodies**: the rendered-frame counter is a body input (51 earlier bodies regenerated, `0x0f2a`), the wing joints draw.
Muun/map-object effect placement remains deferred. All parts run offline.

[Part 31 below](#part-31-the-six-remaining-counter-bodies-and-quantised-random-colours-render-items-002v) reaches **1,370/1,674 bodies** with the six remaining counter types and quantised random colours.

## Identity and evidence

The target is `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Inputs are the restored text at `0x00401000`, capture09, and second image section at `0x01a7c000`, run10.
`scripts/pins.py` validates both entire captures. RenderItem3D `0x016c154e..0x016c23d5` has SHA-256
`258dcf544ad62dbd40797d9328b57037e0dff2d28a1e485ffa91e0387773bcb6`.

**Verified** means compiled authored C matches the actual restored instructions in Unicorn.
**Static** means a consumer layout or instruction reading. Snapshot decode and native renders are separate
evidence; neither proves live-client pixels or the omitted effect systems.

## RenderItem3D

The old list called these "27 codes". Its `0x1c2e..0x1c30` range also includes `0x1c2f`, giving 28 codes.
`scripts/gen_item3d.py` interprets the closed, constant-assignment chain `0x016c168a..0x016c222d` and emits
`reconstructed/hud/item3d_overrides.h`, 32 reviewed override rows. The generator accepts only the decoded
instruction subset it models, validates the capture pins, and refuses unknown instructions/calls. It emits
model IDs and scalar transformations, never instruction bytes or game-table records. Regeneration is checked
by the private validator. Time and window selection remain authored C in `item_slots.c`.

Verified behavior includes:

- Level-specific models, offsets, angles and scales for `0x1a0b`, `0x1a0e`, `0x1a13`, `0x1a14`, `0x1c09`,
  `0x1c0b`, `0x1c0c`, `0x1c15`, `0x1c17`, `0x1c18`, `0x1c20..0x1c22`. The level test is signed
  `level_word >> 3`, without a four-bit mask. An explicit scale in a special branch overrides the caller's
  scale override. The quest models `0x1c17/0x1c18` at level 1 pass level word -1 onward.
- Model substitutions for `0x103b/0x1053`, `0x103c/0x1088`, `0x103d`, `0x1049`, `0x1c2e..0x1c30`.
- Unselected `0x1a47..0x1a4b` write angle Y = time times 0.2. Selected items retain their TRS angle at this
  boundary; RenderObjectScreen spins them later.
- Code `0x1c64` forces selection when the special NewUI object's `+0x1c` is nonzero, after `no_select`.
- The existing projection, flip, kind-dependent depth, `code2` kind test and opaque arguments remain intact.

**Unrecovered boundary.** Box of Luck `0x1c0b` at signed levels above 7 reaches `0x016c1afc`, which jumps to
`0x10b3f080`, outside the restored capture. No compare or jump was patched for this work. Those inputs still
return `MU_ITEM3D_SPECIAL`; the restored lower-level paths and default levels 0/4/7 run normally.

## Native integration

The GFx item pass asks RenderItem3D for its drawn model before loading any geometry. It resolves that model
through the existing item-model getter or the previously recovered special-file table. This fixes remaps
even when the ordinary model is absent. RenderObjectScreen's record-kind query uses the drawn model. The
shared resolver also feeds `mu-render ui inventory`; its time-aware inventory pass supplies the frame clock.
The only world-file edit is this item-pass hook in `native/world/world_gfx_game.c`.

The native special NewUI window for `0x1c64` is not implemented, so its activation input stays zero in native
callers; both input states are compared in Unicorn. Remaps whose model files have no recovered mapping,
including the costume model IDs below `0xae6`, remain counted as missing. No ordinary model is substituted
for an unresolved remap. The existing TRS file calibration and plain inventory-tool mesh render remain viewer
choices. Character and ground-item body/effect rendering are unchanged.

## Instruction comparison

`scripts/validate_render_items.py --mutations --output LOCAL.json` runs compiled C against original
RenderItem3D, recording every RenderObjectScreen argument and all three angle words, bit for bit. The
engine/UI/TRS queries are synthetic inputs; RenderObjectScreen is the recorded boundary, not executed in
this family. Each code runs signed levels -1, 0..17 and 31, except the external-jump cases. Eight variants
cover forced select, no_select and flip; random inputs cover hover/UI states, kind flags, scale overrides,
time, excellent/set bits and pass-through arguments.

| Family | Cases | Mismatches |
|---|---:|---:|
| Constant overrides | 3,360 | 0 |
| Unselected spin | 800 | 0 |
| Restored Box of Luck paths | 72 | 0 |
| Special window selection | 160 | 0 |
| Generic and adjacent-code controls | 1,120 | 0 |
| Total | 5,512 | 0 |

Six separately compiled planted C mistakes are caught: model +1 in 1,456 cases, retained level word in 16,
half-speed spin in 575, incorrect no_select precedence in 80, original offset in 136, caller scale in 144.
The older wrapper/general-path comparison also passes 3,000 cases. The new family has a validator-manifest
row and a private owning test. Five portable worked examples cover remaps, signed level tests, scale/reset
order, range endpoints, time/selection and explicit external-jump refusals. A native synthetic regression
draws Beer02 with no ordinary model, then removes that file and checks the missing count.

Local reports are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002/`.

## Existing Lang snapshots

`scripts/probe_item_effect_tables.py` reads snapshots offline and exports Muun records locally. The layouts
below are **static**, not an authored-C effect comparison.

MuunEffectInfo is the multimap at `0x06fbb46c+0x38`. Iterator dereference `0x00aecc71` returns node+0x10;
`0x0114203d` reads name +4, position +0x1c, rotation +0x28, scale +0x34, bone +0x38 and follow byte +0x3c.
All four snapshots contain all 16 records and their strings; the exported rows are identical. Local `lang/muun-*.tsv` exports preserve them.
Native Muun owner creation and effect placement are deferred together to a later part; no unused native
table API was added here.

The map-object effect table is EnchantEffect's `+0x5c` map at `0x06fbb7b0`. `0x0183067e` gets its world
record through `0x010fa28a`; `0x010f4ae9` returns its nested type map at record+0x3c. Each snapshot contains
38 outer world records, but **zero readable nested type maps**. This is more specific than a missing file:
all 38 nested head/node sets are absent. `lang/effect-inputs.json` records the exact missing addresses per
world and snapshot. A future authorized capture needs the graph rooted at `0x06fbb7b0`, its nested maps,
per-type vectors and effect-name string buffers. No live read was attempted in this run.
RENDER-EFFECTS-008 read that graph live (38 worlds, 443 types, 758 entries; filled at startup) and consumes it
natively: [client-render-effects-008.md](client-render-effects-008.md).

| Snapshot | SHA-256 prefix | Muun records | Worlds | Missing nested maps |
|---|---|---:|---:|---:|
| lang/live/lang3.bin | f07b4c022e9c | 16 | 38 | 38 |
| lang/live/lang4.bin | 0461a408fd6b | 16 | 38 | 38 |
| quest2/live/lang5.bin | 2bd041e63312 | 16 | 38 | 38 |
| skill2/live/lang5.bin | 59974e2e44ef | 16 | 38 | 38 |

## Local renders and next step

`~/Documents/MTM/mu-mac-tools/native/renders/render-items-002/` holds the before/after inventory gallery
and the unchanged character control. The inventory gallery has a sword, wings, transformation weapons,
Dark Lord sleeve, beer, a box and a quest item. Baseline: two models drawn, six refused. After: eight drawn,
zero missing/refused, 679 triangles. The gallery's change is intended. The character control has a +13
weapon with excellent/glow passes and Wing01. Both renders have framebuffer SHA-256 `d8a51daf…aeb09` and
32 passes; the wing still uses the existing special-type fallback. These are native renders inspected locally,
not a live-client fidelity claim. A separate local CGL host exercises the actual GFx item hook and
its icon FBO: eight drawn, zero missing, eight icons, result 0. `gfx-items.png` retains its bottom-up
readback order, as passed to the GFx image consumer.

Next: reconstruct a bounded family of RenderObjDraw's 1,674 special types and RenderLinkItem effects,
feed it through the shared character/ground/inventory body renderer, and add original-instruction streams
and mutants. Follow with Muun owner/effect integration using the decoded 16 rows. Map-object effects need
the nested snapshot inputs above; the displaced Box of Luck branch remains outside this part.

## Part 2, bounded body and link effects, RENDER-ITEMS-002B

The complete scalar level-remap chain and a first body/effect family are implemented.
This is a coherent subset of part 2, not completion of the 1,674-type backlog.
The executable identity and evidence labels above still apply. Original client processes were left alone.

### Recovered rules

`scripts/gen_item_glow.py` executes the closed type switch `0x0176d160..0x0176dc26` on all
8,192 item types and all 16 masked input levels. It emits 103 affected model types with 16 scalar
results each in `reconstructed/renderchar/item_glow.h`. The chain's SHA-256 is
`3720a8a2a4d7c411f0f95a4f879dfb4a41f9448922c667281bef6dc57f67f33c`.
It runs after render flag `0x400` clears the input level, before kind-B overrides and the quality cap.
The table contains authored rendering rules derived from instructions, with no captured instruction bytes.

Complete body streams are enabled for **11 of the original 1,674 special item types**, within the existing
unselected, non-shadow, supported-record, no-buff domain:

- `0x12ed`, `0x12f5`: zero stays zero; other levels map to `2*level+1`. Their body branch
  `0x016f5894..0x016f5a26` ignores the caller's hidden mesh and texture override when buffs 6/0x8f are absent.
- `0x22e6..0x22eb`, `0x22f1`, `0x248c`, `0x248d`: suppress ordinary item-level glow.
  `0x22ea/0x248c` set BlendMeshLight to `sin(time*0.001)+1.1`;
  `0x22eb/0x248d` use `(sin(time*0.001)+1)/4`. Excellent/ancient passes still run afterward.

RenderLinkItem's **six bow types**, `0x12ea`, `0x12eb`, `0x12ec`, `0x12f7`, `0x1301`, `0x1303`,
share the switch branch `0x012c70e7..0x012c7415`. Their authored C emits bitmap `0x7f67`:

- `0x12ea/0x12eb/0x1301`: bones 2 and 6, light `l*(1,0.6,0.2)`;
- `0x12ec`: bones 13 through 18, light `l*(0.6,1,0.8)`;
- `0x12f7/0x1303`: bones 13 through 18, then 5 through 8, light `l*(0.5,0.5,0.8)`.

Here `l = (rand()%30+70)*0.005`, with binary32 operations. Scale is 1, rotation and blend are zero.
The executed helper `0x0150e746..0x0150e7c9` applies TransformPosition with translation, then calls
CreateSprite with axes 4 and the default 1-by-1 sheet. These are verified instruction boundaries;
file names such as Bow05 or Wing05 remain viewer inference from the standard filename convention.

### Native integration

The shared item body renderer feeds ground items, remote players, NPC equipment and GFx inventory icons.
The hero's two plain draws now call it too. `mu-render ui inventory` uses the same body pass rather than
one textured draw, with drawn-model record kinds, level and option inputs. Level/glow pixels in that tool
are intentionally changed. Ground-item code and per-world/terrain files are unchanged.

Small character draw hooks emit the six bow effects into the existing particle pool. The native adapter
uses the item's saved bone matrices, its scale and origin, not the shared pose buffer overwritten by later
items. It skips absent bones and counts successful allocations separately from the client's ambiguous
slot-zero/full return. Sprite rendering kills these records in the current frame. The native owner is
`MU_PT_NO_OWNER`, since the original temporary item OBJECT has no durable native pool index. Owner-dependent
behavior beyond these one-frame sprites is not claimed. The native particle pool supplies its existing
MSVC random stream; that stream is not synchronized with the original client's global random consumers.

The hero still has filename-derived types and level-zero inputs, without authoritative equipment instances.
The character tool accepts explicit levels/options and renders the new sprite family. Remote-player and NPC
inputs retain their existing item records. Ground and inventory paths consume body rules only; RenderLinkItem
is a character attachment path, so it does not add these linked sprites to dropped or inventory items.

### Instruction checks and native regressions

`./tools/python/bin/python scripts/validate_item_types.py --mutations --output LOCAL.json`:

| Family | Cases | Mismatches | Boundary |
|---|---:|---:|---|
| Scalar remaps | 131,072 | 0 | 8,192 types times 16 levels, original closed chain vs compiled C |
| Complete body streams | 3,212 | 0 | 11 types, 192 level/state combinations and 100 random cases each |
| Link sprite calls | 792 | 0 | 6 types, 33 random results, hand/back carry and both hands |
| Bone-position helper | 100 | 0 | Original helper including TransformPosition vs compiled shared C math |
| Total | 135,176 | 0 | Scalar counts do not imply complete body coverage for 103 types |

Six separately compiled mistakes are caught: removed remap, 229 cases; wing pulse offset, 584;
weapon hidden-mesh override, 107; wrong link bone, 396; doubled intensity, 792; missing last sprite, 264.
The body stream comparison checks every draw argument and model light/shade/level/flag bit, rejects
unexpected service calls and requires normal ABI return. It varies quality, masked/unmasked level bits,
render flags, record absence, supported kinds, overrides, alpha, time and initial model state.
The link comparison records deep colour/sheet values, not transient pointer addresses.
The bone-helper comparison executes its original instructions without the old recorder stub.

Portable examples cover remap/cap ordering, adjacent type refusal, pulses, excellent tails and bounded output.
The native host checks saved-pose replacement, scale/origin, five missing bones, unknown types and a full
sprite pool. Native character and inventory tests verify the shared pass integration. The new private
validator has a manifest row and owning test. Reports stay in local scratch `render-items-002b/`.

### Renders and remaining work

Local `renders/render-items-002b/` holds inspected before/after inventory and character PNGs.
The character has Bow05 at +13/excellent and Wing05: 32 passes in both versions, one refused body type
before and zero after, with two linked sprites after. The wing's blend pulse and the two bow flares are
visible. The six-item inventory draws all six models in both versions; triangles change from 1,196 to
2,322 because it now draws item body/glow passes. These are native offline renders, not live-client
pixel comparisons. Part 1's renders and their hashes are preserved.

Remaining, precisely:

- **1,663 of 1,674 special body types**, plus the 17 class-part skins. The other 92 types in the
  103-row remap table have only their scalar remap recovered; their body/effect branches remain refused.
- RenderLinkItem's other switch targets. The implemented target is `0x012c70e7`; the next branch starts
  at `0x012c741a`. The no-buff body comparison does not recover weapon buffs 6/0x8f, record-kind special
  branches, selection outlines, shadows or `a13=1`.
- Muun owner/effect integration and the missing nested map-object table graphs from part 1.
- Authoritative hero equipment levels/options, special-window `0x1c64`, unresolved costume model files,
  and Box of Luck signed levels above 7 crossing the external jump. These remain unchanged scope limits.

Final part-2 gate: Local macOS gate on the tree integrated with main `fecdddd`: 1357 tests across 38 discovery runs, 158 explicit private/unavailable-input skips. Offline fixture scenarios, native viewer/readers and publication audit pass, zero rejected files. No hosted workflow dispatched.

## Part 3, body clusters and offset links, RENDER-ITEMS-002C

Part 3 adds **251 body types**, bringing the bounded command-stream implementation to
**262 of 1,674 special item types**. The 17 special class skins remain separate and unimplemented.
The executable and capture pins in Identity and evidence above apply unchanged. No original client or
launcher was started, stopped, read or modified.

### Classification and priority

The offline survey executes all 1,674 item types and 17 class skins in the eleven existing classification
states, covering level, quality, options, flags and time. Its **18,601 state runs identify 798 observed
call shapes**. A shape includes helper entry/return sites and the actual caller addresses of body, mesh,
sprite and particle services. This distinguishes different leaf branches with the same pass count.
It is a finite survey in the existing unselected/no-buff domain, not exhaustive control-flow equivalence.
For 62 types, at least one state stops on unavailable synthetic model/mesh data; their stop PCs are explicit.

- [Every type and its coverage](item-body-types.tsv), 1,691 rows, including all 17 class skins.
- [Ranked branch shapes and original addresses](item-body-shapes.tsv), 798 rows. `size_rank` sorts by shared
  type count. `visibility_rank` prioritizes class skins, wings and low-index weapons/armour, then custom
  equipment, then other item groups. This priority is **inference from model IDs**, not measured wear rates.
  `pet/item` includes other item groups and does not assert every member is a wearable pet.
- `scripts/classify_item_bodies.py` regenerates the local survey and optional reviewed TSV summaries from
  the pinned instructions. Neither TSV contains captured bytes, meshes, textures or item-table records.

| Size rank | Shape | Types | Implemented | Visibility |
|---:|---|---:|---:|---|
| 1 | `5c6ff0c76722cf55` | 61 | 61 | Wings |
| 2 | `d600e31897bd5088` | 59 | 59 | Wings |
| 3 | `ac9ebab05935c051` | 47 | 0 | Custom armour |
| 4 | `6a1cf3ec86050806` | 24 | 9 | Wings, four class skins, other items |
| 5 | `c2dc4acbcd235d05` | 19 | 0 | Custom armour |
| 6 | `ef7283f9b1892031` | 19 | 0 | Custom armour |
| 7 | `6cc0c623a575db41` | 18 | 0 | Other items |
| 8 | `b0c194a89f726bf0` | 15 | 0 | Four class skins, other items |

Across the complete table, 41 shapes are fully implemented and two partly implemented. The two largest
shapes are complete. Shape membership is more precise than the earlier single-state pass-count grouping.

### Parameterized bodies

The 251 additions consist of **120 armour, 122 wing and nine weapon types**. Exact membership is in the TSV
and `mu_rc_body_types` in `reconstructed/renderchar/item_bodies.h`.

- The two large wing families cover `0x234a..0x2367` and `0x241d..0x2476`, 120 types. They force the glow
  level to zero and share base-body, coloured-body and mesh passes, with per-type colour/mesh constants.
  Excellent/ancient tails still execute. Additional wing types `0x24ab/0x24b3` have their own recipes.
- Armour includes helm/armour/pants set indices 39..44, additional equipment branches, and 76 types across
  groups 7/8/9/11 with indices `0x11c..0x12b`, `0x13a`, `0x15d`, `0x193`. Those 76 omit ordinary high-level
  colour passes. Their ancient tail `0x017e5e19..0x017e61bd` uses `sin(time*0.004)*0.5+0.4`, flag `0x240`,
  and three cumulative PartObjectColor2 passes. The glove variants have different leaf branches and remain open.
- Base recipes distinguish render flag `0x40000`, object alpha versus caller alpha, hidden meshes and texture
  overrides. Colour, mesh selection and pass constants are data; one C executor handles the shared recipes.
  A sorted type table supplies the recipes through a binary search.

`scripts/gen_item_bodies.py` probes the reviewed types and emits only constant or input-copy rendering rules.
The probes select a candidate recipe; **independent full-function instruction comparisons provide the verified
finite evidence**. Regeneration fails if a reviewed recipe no longer fits. Seventeen screened candidates failed
comparison and were excluded, including unsupported ancient-colour behavior. Their diagnostic streams remain
local; their types remain refused. The remaining 92 scalar-remap-only types from part 2 are unchanged.

The additions share the previous unselected, non-shadow, no-buff, supported-record boundary. New types require
`a10=a11=-1` and the normal zero OBJECT auxiliary fields, including hidden mesh `+0x68`; explicit mesh overrides return `MU_RC_UNSUPPORTED`. Selected outlines, shadow passes, `a13=1`,
buffs 6/0x8f and the previously refused record kinds remain outside this implementation. Body coverage counts
command streams within that domain, not every possible record configuration or model-file availability.

### Offset links and native integration

Two more RenderLinkItem callers are reconstructed:

- **`0x012c741a`, type `0x14f0`, integrated.** Ten offsets on bone zero, `(i*30-180,-40,0)`. Each emits an
  orange `0x7ef7` sprite at scale 2. A conditional `rand()%3==0` adds a grey `0x7f67` sprite at scale 0.6,
  with a separate random rotation. The initial intensity and conditional random calls preserve original order.
- **`0x012c761d`, type `0x12fb`, caller verified, particle consumer partial.** Bones 7/15 emit two sprites;
  three more use bone zero plus `(20,0,0)` at scales 0.8/1.3/2. An odd random result also requests two
  Spark03 `0x7f26` particles, subtype 11, at bones 4/12. All seven requests match the original call stream.
  The existing particle engine refuses subtype 11: native output has five sprites and two explicitly counted
  unsupported particle requests. That particle's creation/update/render consumer remains to reconstruct.

Together with part 2, three link targets/eight types have verified caller streams. Two targets are fully
integrated; the third has the particle limitation above. Next untouched target: `0x012c7a45`, type `0x0ef4`,
then `0x012c7e68`, type `0x0afc`. No unrelated particle-engine or world-object files changed.

The existing hero, remote-player, NPC, ground-item and GFx inventory hooks consume the shared body renderer.
Character attachments consume the new links through the same saved-pose adapter. Nonzero offsets precede the
bone transform, scale and origin. The character tool now opens its effect pool for the new types too.
Ground/inventory bodies do not acquire character-link effects. Missing bones and full sprite pools are checked;
unknown types consume no random state. Native random synchronization and temporary-owner limitations from
part 2 remain. Particle angle input comes from the native item's posed model, and no live owner fidelity is claimed.

### Checks and local renders

`scripts/validate_item_clusters.py --mutations --output LOCAL.json` compares compiled production C with the
pinned original instructions:

| Family | Cases | Mismatches |
|---|---:|---:|
| Complete bounded body streams, 251 types times 292 states | 73,292 | 0 |
| Two link caller streams, including random-call counts | 800 | 0 |
| Real TransformPosition with nonzero offsets versus shared production C math | 200 | 0 |
| Total | 74,292 | 0 |

Each body type covers 192 level/state combinations and 100 random cases. The comparison checks every draw
argument and light/shade/level/flag word, rejects unexpected services and requires normal ABI return.
The link family records deep colour/sheet values and offset/bone inputs; the transform family separately
executes the real transform instructions. The reuse of the emulator's address space restores data, BSS, case
regions, allocator and CRT state between calls, and is checked against fresh machines before each body sweep.
The comparison does not execute the graphics driver or unsupported particle consumers.

Eight compiled mutants cover mesh indices, object alpha, the flag branch, ancient pass count, staff offsets,
conditional staff calls, bow bones and bow scale. All are detected. Part 2 also reruns with **135,176 cases,
zero mismatches and 6/6 mutants**. Portable examples cover flag/alpha order, suppressed wing levels, hidden
meshes, bounded outputs, explicit refusals and random consumption. Native regressions cover saved poses,
nonzero offsets, missing bones, full pools and the subtype-11 refusal. The new validator has a manifest row
and private owning test.

Local artifacts are under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/render-items-002c/`.
Inspected before/after renders show set-40 helm/armour/pants going from three refused bodies to zero,
13 to 25 passes. The staff control adds 11 linked sprites at the fixed seed; its body remains an explicitly
refused branch. These are native offline renders, not live-client pixel comparisons. Earlier milestone
renders were preserved.

### Remaining work

- **1,412 special item body types and all 17 special class skins.** The TSVs give exact membership, branch
  sites, size/visibility priorities and stopped-state PCs. Next large untouched armour shape has 47 types.
- Spark03 subtype 11's particle consumer, then the remaining link targets starting at `0x012c7a45`.
- New-type mesh overrides and the older outline/shadow/buff/record-kind limits; authoritative hero instances;
  unresolved model mappings, the special NewUI window and displaced Box of Luck branch.
- Muun placement and the missing nested map-object table graph remain deferred exactly as before.

Local macOS gate passed on the tree integrated with main `54ae63f`: **1,378 tests across 38 discovery
runs, 162 explicit private/unavailable-input skips**. Offline fixture scenarios, native viewer/readers and
publication audit pass, 1,237 tracked files audited, zero rejected. No hosted workflow was dispatched.
Self-review against the brief, repository standards and recorded evidence found no blocking issue in this
bounded subset. The subtype-11 consumer gap and all unimplemented types remain explicit above.

## Part 4, armour, weapons, skins and Spark03, RENDER-ITEMS-002D

[Part 4 handoff](../handoffs/RENDER-ITEMS-002D.md) records the scope and remaining branches. The same executable
identity and capture pins apply. The shared body renderer now covers **426/1,674 item types**, up by 164,
and **11/17 class skins**. Additions comprise 137 armour and 27 weapon types. The size-rank-3 armour shape
`ac9ebab05935c051` is complete at 47/47. The TSVs update membership against the unchanged part-3 survey.

The generator emits per-type mesh/body recipes with constants, copied inputs and a shared pulsed-light
input. The pulse follows `0x0185bdc4(-4,0)` and `0x01705471..0x0170567f`, including signed clock truncation,
remainder and binary32 arithmetic, with a 0.2 offset. Only pulse recipes evaluate it. Skin probes use all
sixteen input levels after the closed scalar-remap chain. The separate skin scalar header covers the
fifteen changed rows among seventeen skins. Kind-A predicates now honor the original `0x2c00` item-record
bound; higher skin IDs do not acquire a synthetic item-record kind.

Two next RenderLinkItem targets are implemented and integrated:

- `0x012c7a45`, type `0x0ef4`: five flares on bone zero at two ends of the weapon. Original random order selects
  jitter and scales; the second/fifth sprites rotate 20/90 degrees. Bitmaps are `0x7f67` and `0x7ef7`.
- `0x012c7e68`, type `0x0afc`: two `0x7ef8` sprites at `(5,-22,-10)` and `(-5,-22,-10)`, scale 0.75,
  with light `(p,p-0.5,p-0.5)`, `p = sin(time*0.4)*0.25+0.7`.

The previously partial bow `0x12fb` now consumes both conditional Spark03 subtype-11 requests.
`particles.c` implements creation `0x015de226..0x015de357`, movement `0x01651b78..0x01651ca6` and the existing
render path. Five targets/ten types now have complete native consumers in the established no-owner domain.
Character attachments use saved poses and frame time. Ground/inventory receive the body rules through
their existing hooks. Hero inference now recognizes the five existing ClassNN filename families within
the model-codec bounds. This does not resolve unavailable special-model mappings. Synthetic native checks
cover class filename bounds, missing bones, pool exhaustion, the new links and
successful subtype-11 allocations. Global random synchronization and temporary-owner limitations remain.

The bounded unselected, non-shadow, no-buff, supported-record and no-mesh-override domain from part 3 is
unchanged. Six skins remain refused, including their extra level branches/effects. Independent comparisons
rejected fourteen additional probe-fitting weapon candidates with different ancient-tail light behavior.
They remain refused. Full counts and exact remaining types are in the handoff. Before/after native renders
stay local and show the intended added passes on synthetic geometry; they are not original-client pixels.

`validate_item_expansion.py --mutations` passes **52,172 cases**, zero mismatches, **7/7 mutants** caught:
51,100 full body/skin streams, 800 link caller streams and 272 scalar skin cases. Both generated tables
reproduce from pinned instructions. Ten further private comparisons cover signed clock boundaries.
`validate_item_effects.py --mutations` passes **1,500 cases**, zero mismatches, **3/3 mutants**, comparing
Spark03/11 creation, movement and rendering separately. Total new evidence is **53,682 cases and 10/10
mutants**. Call-stream and record comparisons remain distinct from native render evidence and graphics-driver
behavior. The complete scope, local artifact locations, regressions and merge gate are in the handoff.

## Part 5, remaining skins and ranked body clusters, RENDER-ITEMS-002E

Part 5 extends complete bounded body-command coverage to **501/1,674 item types** and **17/17 class skins**.
The executable identity and capture pins above are unchanged. No original client or launcher was used.
The 75 new item types comprise 38 armour, one wing and 36 types in the survey's `pet/item` category.
That category is a model-group classification, not a claim that every type is a pet.

The exact membership is in the generated C table and the updated type/shape TSVs. Four ranked shapes are
completed: rank 6 `ef7283f9b1892031` at 19/19, rank 7 `6cc0c623a575db41` at 18/18, rank 8
`b0c194a89f726bf0` at 15/15, and rank 10 `64fc725e1c85631d` at 12/12. Rank 8 already had four skins.
The remaining additions share smaller shapes. Visibility ranks remain model-index inference.
The rank-5, 19-type shape still stops in the synthetic oracle. Its body calls model animation/pose code,
which reads the absent action pointer at model `+0x30`, stopping at `0x012b51a7` from caller `0x01747a0a`.
This needs a pose-aware reconstruction; recording a stubbed pose call would not establish native geometry.

The shared recipe executor adds a blend-light input for `0x01740cf0..0x01740d43` and related branches.
It evaluates `0x0185bdc4(-4,0)` with signed clock truncation and remainder, then performs the caller's
binary64 multiply by 0.7 and add of binary32 0.3, rounds to binary32 and clamps above 1.
This differs from the older body-light pulse's binary32 0.2 offset. Generated selectors distinguish them.
All other recipe sources keep their previous meaning. Unknown recipes still fail regeneration.
Independent comparison rejected seven probe-fitting candidates, which remain refused:
`0x230f`, `0x2317`, `0x248e`, `0x2490`, `0x2492`, `0x2504`, `0x270f`. Diagnostics stay local.

### Six remaining class skins

The ordinary skin streams reuse the scalar/glow path; early returns use a second generated rendering table.
Its selector records whether the original branch tests raw masked level or the remapped, capped glow level.
The table is generated by `scripts/gen_skin_bodies.py` from sixty varied calls per reviewed branch.

- `0x3895` tests raw levels 14/15 and emits three fixed-colour passes, even with quality zero.
- `0x3896` tests effective level 13 and emits flags 1/0x44 with fixed alpha/blend values.
- `0x389b` has an effective-level-1 two-colour early return and a different two-pass fallback using texture
  `0x7f20`. These paths retain the initial model shade, level and flag words at each draw.
- `0x389e` has an effective-level-9 two-colour early return; its other levels retain the existing scalar rule.
- `0x389c/0x389d` emit a `0x7f26` sprite at bone-zero offsets `(0,0,15)` and `(0,-5,-15)` respectively.
  The pulse is `sin(time*0.002)*0.35+0.65`. Their colours swap the red/blue multiplier and their scales
  add 2/2.5 after multiplying the pulse by 0.8. TransformPosition runs with translate zero, then the caller
  adds OBJECT position. This preserves bone translation but omits model scale.
  `0x389d` also writes V as the signed truncated remainder of `-time` modulo 4000, times 0.00025.

The skin body/effect comparison executes the entire bounded RenderObjDraw and records deep sprite values,
transform inputs and draw words. It varies every raw level, low level bits, quality, render flags, record
presence/kinds, options, time and initial model state. It checks service arguments and command streams,
not every persistent model/OBJECT byte or graphics-driver output.

### Link callers and native integration

Two further RenderLinkItem targets are reconstructed and consumed, bringing the total to seven targets
covering twelve types in the established no-owner domain:

- `0x012c807d..0x012c856c`, type `0x0afd`, emits seven sprites on bones 4/6/7/8. Random jitter and scale
  precede a time-dependent blue component. The first two sprites rotate with `time*0.0006*360`, 90 degrees
  apart. Their shared position, the third sprite's inherited jitter and the fourth's X offset are preserved.
- `0x012c8d7b..0x012c91f9`, type `0x0afe`, emits five sprites on bone 2. The first two have Z offsets
  +3/-3. One random call sets a later flare's scale; the final sprite uses a separate sine pulse.

Native hero, remote-player and NPC bodies share the new recipes with ground-item and GFx inventory draws.
The three character hooks also supply the two skin sprites, using saved player bones for body parts and
saved item bones for links. The character renderer opens its effect pool for those skins. Missing bones,
full pools and random consumption have native checks. Ground/inventory consume the skin body/UV commands;
these paths still have no skin-sprite pool consumer. Owner-follow behavior and synchronization with the
original global random stream remain outside the native claim. Hero equipment instances remain inferred.
The resumed review caught a missing frame-clock copy in the standalone character renderer's particle pool.
It now supplies the same time as the body commands. A native pixel regression with an authored Spark03 JPEG
fails before the fix and passes after it, checking visible sprite colour/scale at times 0 and 500.

### Evidence and limits

The independent part-5 validator compares compiled production C with pinned original instructions:
21,900 new body cases, 3,072 complete skin body/effect cases, and 800 link caller cases, **25,772 total**.
The separate signed-clock controls cover twenty body-stream cases. Final mutation, regression and release-gate
results are recorded in the [part-5 handoff](../handoffs/RENDER-ITEMS-002E.md).

Inspected offline before/after renders stay under local `renders/render-items-002e/`, with resumed renders in
its `resume/` directory. Synthetic armour goes
from three refused bodies/three fallback passes to zero refusals/24 passes. Three early-return skins go
from three refusals/three passes to zero refusals/seven passes. The other skin scene has four passes and two
allocated sprites. These are untextured authored meshes, not original-client pixels. The sword control
allocates five sprites but has unchanged image pixels without effect textures. Previous renders are preserved.

Remaining: **1,173 item body types**, further link targets, the rank-5 pose-aware branch and rank-9 armour
shape, plus the existing mesh-override, selection/shadow/buff/record-kind and model-mapping limits.
The untouched shared link target `0x012c8571` covers `0x132f/0x14f2`; it includes additional particle behavior.
Skin sprites on ground/inventory draws, authoritative hero instances, the special NewUI/Box of Luck limits,
Muun and nested map-object placement remain explicit follow-ups.

## Part 6, rank-9 armour, further body clusters and sprite chains, RENDER-ITEMS-002F

Part 6 extends bounded body-command coverage to **559/1,674 item types**, adding 27 armour and 31
`pet/item` model-group types. All **17/17 class skins** remain covered. The executable and capture pins
above are unchanged. No original client or launcher was used. Exact membership is in `item_bodies.h`
and the two survey TSVs. Nine more shapes are complete, at size ranks 9, 45, 51, 52, 60, 61, 68, 79 and 85.
The survey now has 122 complete shapes. Its original ranks and observed stopped states are unchanged.

Rank 9, shape `0ce2ff5445249f7d`, covers `0x199f` and `0x19a3..0x19ad`, twelve armour types.
These retain ordinary level and excellent passes but omit the ancient phase even with a present item
record. The generator emits an empty ancient recipe instead of copying the generic tail. Independent
full-function comparisons check every enabled type across 292 states, including record/option/quality
variants. The inherited unselected, non-shadow, no-buff and no-mesh-override boundary remains.

### Generated sprite-chain links

Two RenderLinkItem targets use one parameterized C executor and `item_links.h`, reproducible with
`scripts/gen_item_links.py`. The generator checks reviewed rendering parameters against the instructions;
the independent validator then varies random sequences, clocks and hand/link inputs.

- `0x012cb556`, type `0x0af9`, visits bones 2..8. Each bone emits an orange `0x7ef7` flare at scale 2.
  A conditional `rand()%3==0` precedes it with a grey `0x7f67` sprite at scale 0.6 and a random rotation.
  The initial intensity, per-bone choices and conditional rotations retain the original random order.
- `0x012cb7ab`, type `0x12f9`, visits bones 1..5 with local Z offset 10. Each emits `0x7f67` at scale 1
  and `0x7ef7` at scale 2. One random call sets intensity. The final flare becomes white while the
  preceding sprite keeps its blue multiplier.

Nine link targets covering fourteen types now have complete consumers within the existing no-owner domain.
Character hooks retain their saved-pose adapter, bounds checks and pool-capacity handling. These two
weapon links are not applied to ground or inventory items.

### Ground and inventory skin sprites

The skin-only adapter consumes the existing `0x389c/0x389d` sprite rules in both ground backends, the
software inventory renderer and the actual GFx item/FBO renderer. It uses each model's current saved
bone matrix, the established translate-zero transform followed by OBJECT origin, and the caller's frame
clock. GFx keeps a separate sprite pool and draws each icon's one-frame sprites in that icon's projection.
The GL ground callback now retains a mutable runtime pointer because allocation changes its sprite pool.

Four native regressions cover both ground backends, software inventory and the GFx icon FBO. Each ground
scene tests both original quest-item codes at level 1, with three draws producing three sprites and no
additional random calls. Authored JPEG pixels distinguish missing-texture versus drawn sprites, clocks
0/500, and repeated icon frames 0/0/500/0. The static model fixture isolates this clock from an existing
first-versus-cached animated-pose difference; that broader pose lifecycle is not claimed verified.

### Evidence and remaining work

`scripts/validate_item_ranked.py --mutations` compares compiled production C with the original bounded
instruction streams: **16,936 body cases plus 800 link cases, 17,736 total, zero mismatches**. It also
reproduces both generated tables. All **6/6 compiled mutants** fail: ancient phase, object alpha, chain
bone, scale, random choice and the final white flare. These are finite call-stream comparisons with engine
service boundaries; they do not compare graphics-driver output or establish live owner/random fidelity.

Recovered and rerun before/after offline renders show three new body recipes replacing three refusals:
rank-9 scenes change from 5 to 11 total passes, other ranked bodies from 5 to 28. Textured link and inventory
sprites change visible pixels; the ordinary character control stays byte-identical. Untextured synthetic
armour saturates white, so its pass counts provide evidence beyond its pixels. These are authored models,
not original-client fidelity images. Release checks and cleanup are recorded in the
[part-6 handoff](../handoffs/RENDER-ITEMS-002F.md).

Remaining: **1,115 item body types**. Rank 5 stays refused. Static instructions at
`0x017479b1..0x01747a0a` pass OBJECT action `+0x2c`, frame/prior frame `+0xd0/+0xd4`, angles `+0x164`
and head angles `+0x170` to the real pose builder `0x012b5064`, writing shared bones `0x06fce398`.
The current synthetic body oracle lacks action `model+0x30` and bone-track `model+0x2c` data and stops at
`0x012b51a7`. Completing this branch needs populated synthetic action/bone tracks, full pose/geometry
comparison, and a native pose adapter before enabling its recipes. Merely recording a stubbed pose call
would not verify geometry.

The shared link `0x012c8571`, types `0x132f/0x14f2`, also requests owner-dependent Laser `0x7fd6`
subtype 17, which the joint consumer refuses. The sword target `0x012c91fe` changes shared clock/bone
state at `0x0a3a0e1c/20` and is not a stateless sprite recipe. Further links, authoritative hero instances,
owner-follow/global-random synchronization, model mappings, selection/shadow/buff/record-kind and mesh
overrides, NewUI and Box of Luck remain open. Muun and nested map-object tables remain deferred.


## Part 7, stress gear, clock-driven bodies and pose boundary, RENDER-ITEMS-002G

The executable and complete-capture identities above are unchanged. Part 7 adds **76 item bodies**, one
weapon, 50 armour types and 25 types in the survey's `pet/item` model group. Bounded body coverage is
**635/1,674**, with **17/17 class skins** unchanged. The committed README-STRESS-001 kits had one refused
body, mace `0x0eee`, group 2/index 8. Every body in those eight kits now has an admitted stream. This does
not mean arbitrary gear or all record configurations are implemented.

Twelve more survey shapes are complete, at size ranks **11, 12, 16, 27, 28, 31, 35, 40, 41, 53, 58, 447**.
There are 134 complete shapes. Exact membership remains in the generated C table and the two TSVs.
The original shape IDs, ranks, stopped-state counts and service sites are preserved. Visibility remains
inference from model indices. The classifier's coverage export now includes the part-6 and part-7 lists.

### Parameterized clocks and bodies

The recipe executor adds four scalar sources, evaluated only for types whose generated rows use them:

- `0x016ecaf5`: `(sin(time * 0.0015f) + 1) * 0.5f`.
- `0x016eec41`: `sin(time * 0.002f) * 0.3f + 0.7f`.
- `0x01713552` and related sites: signed truncated time remainder modulo 2000, times `0.0005f`.
- `0x01712fed..0x0171304b`: the existing `0x0185bdc4(-4,0)` wave times `0.65f`, plus `0.2f`,
  clamped above binary32 `0.65f`. These operations round in SSE order.

The mace's `0x016ed6e8` branch writes `sin(time * 0.001f) * 0.6f + 0.4f` to OBJECT blend light.
The `0x18fe/0x1cfe` armour fallback writes the corresponding `0.4f` multiplier and `0.6f` addend.
Those writes survive the later glow phases. The mace also executes a balanced GL matrix push/pop;
`0x012b7e53/0x012b7e65` change no matrix values. The oracle requires exactly that pair, and only for
this type. Native rendering can omit the redundant scope without changing geometry.

Recipes may now contain up to sixteen draws, instead of eight; the native output bound stays 32.
Capacity/sentinel checks and full streams cover admitted recipes. The original selection, shadow, buff,
record-kind and mesh-override limits remain. Five fitting candidates still fail independent ancient-tail
comparison and remain refused: `0x230f/0x248e/0x2490/0x2504/0x270f`.

Independent cases exposed that the old generator's two flag-0x40000 probe clocks both saturated the
clamped pulse. Its apparent constant fit failed at time 791240. Generation now probes clocks below the
clamp too. The regression records the original blend word `1045510311` on that flag branch. The corrected
rules are compared again over every admitted type, rather than accepting probe fit as evidence.

### Three further link targets

`gen_item_pulse_links.py` emits per-sprite scalar rules consumed by one C evaluator. The independent
caller comparison varies clocks, random sequences and all four existing hand/link variants.

- Type `0x0afa`, target `0x012cca07`, sprite sites `0x012ccb7c/0x012ccc40`, visits bones 1 and 2. Its coloured flare uses
  `p = sin(time * 0.002f) * 0.35f + 0.65f`, scale `p*0.9f` and RGB `p*(0.43f,0.14f,0.6f)`.
  Each is followed by a grey flare at scale `sin(time*0.002f)*0.5f+0.4f`.
- Type `0x0eed`, target `0x012cbb43`, emits two bone-1 flares. The first uses the common random
  intensity and scale 2; the second is grey at scale `sin(time*0.002f)+0.5f`.
- Type `0x0eee`, target `0x012cbd11`, emits bone-1 flares at local X -15/+10 with scale
  `sin(time*0.001f)+1`. Two Shiny02 sprites share the second position; their rotations are
  `360 - sin(time*0.01f)*360` and `sin(time*0.01f)*360`, with the caller's pulsed grey colour.

All three retain the common initial random call, including when its intensity is unused. The native
hero, remote-player and NPC attachment hooks consume them using saved item bones, scale and origin.
The standalone character tool's admission query includes them. Bounds, full pools, absent bones and
random counts have native checks. These links remain character attachments; ground/inventory body
rules do not acquire weapon sprites. Owner-follow and global-random synchronization remain unverified.

### Rank-5 pose progress, still refused

`item_pose_machine.py` populates two authored three-key actions and two parented bone tracks, reserves
the seeded heap range from CRT allocations, and executes the real `0x017479b1..0x01747a0a` caller and
`0x012b5064` builder. No pose instruction is stubbed. The actual caller arguments, keep-root/translate
flags, clamped actions and negative/fractional/out-of-range frames are exercised across all nineteen types.
Its output bone matrices match production `mu_pose_build` in **608 cases**. Another **1,216 cases** compare
real TransformPosition on two authored nonzero points per pose with production point math.

This advances beyond the former absent-action stop. It does **not** establish complete rank-5 rendering.
The synthetic model has lighting byte zero and no populated named-mesh registry. Named-mesh selection,
lighting-dependent passes, further clock/random branches, native re-pose/transform ordering and shared-pose
restoration remain to be reconstructed together. All nineteen types stay refused. Point geometry and
pose matrices are separate evidence from mesh dispatch, full skinned geometry and graphics-driver output.

### Native loader, checks and limits

The ground-armour Player-folder fallback now gets glow textures from `Data/Effect`, correcting the
analogous lookup called out by README-STRESS-001. A synthetic item/model/JPEG regression checks all six
loaded glow slots through the real ground loader. The original-directory mutant is caught with 0/6
loaded slots; corrected code has 6/6. This is a native integration fix, not new x86 behavior.

`scripts/validate_item_gear.py --mutations` owns the new instruction families. The release handoff records
final counts, mutation detections, local render inspection, regression runs and the lock-held Mac gate.
Remaining: **1,039 bodies**, full pose-aware rank-5 rendering, further links including owner-dependent
Laser/17 and shared-clock state, authoritative hero equipment, model mappings and the earlier domain,
NewUI/Box of Luck limits. Muun and nested map-object tables remain deferred. No live game or launcher is used.

## Part 8, rank-5 mesh streams and further links, RENDER-ITEMS-002H

Bounded coverage reaches **662/1,674 item bodies**, **17/17 class skins**, and
**fourteen RenderLinkItem targets covering nineteen types**. This adds all nineteen
rank-5 types and eight armour types at size ranks 83 and 88. The original survey's
1,691 identities, ranks and stopped-state observations stay intact. Only membership
and the three shape coverage counts change.

### Rank-5 draw boundary

**Verified:** the complete RenderObjDraw mesh stream for `0x1c24..0x1c34`, `0x1c44`
and `0x1c7a`, with OBJECT owner-bone pointer `+0x318` absent. The comparison runs the
real pose builder at `0x017479b1..0x01747a0a`, with authored action and bone tracks.
Lighting byte `model+0x50`, named Blue mesh hits/misses, clock, level, flags, alpha,
excellent/ancient tails and random consumption vary independently. Each type has
584 cases, 292 per lighting state, **11,096 total, zero mismatches**. Another
**760** supported-record and signed/conversion-clock cases pass. Pose matrices
and transformed authored points retain the separate part-7 comparison.

**Static:** no transform call intervenes between that pose call and the mesh draws
at `0x01747a0a..0x0174a489`. The body draws consume the incoming transformed
vertices; the rebuilt bones serve the later owner effects. The native body adapter
therefore preserves incoming geometry and saved poses. Re-posing and skinning the
body inside this adapter would change geometry that the original branch retains.

The authored C emits two or four base meshes, then the lighting-dependent overlays.
Blue-name lookup follows the first exact texture-name match and preserves a missing
mesh as -1, which the native adapter skips. Other sets select fixed mesh/bitmap
indices. The pulse uses signed integer conversion, remainder by -6283 and binary32
cosine arithmetic. Random blend light is `(rand()%5)/5+0.5`; UV uses
`int(time/80)%4*0.25` and retains the original random call even though its captured
multiplier is zero. The existing runtime particle pool supplies the random stream;
a standalone caller without one uses an explicit zero-valued viewer input.

**Limit:** this completes the mesh branch in the existing no-owner body domain.
It does not complete full rank-5 owner rendering. With readable owner bones 35 and
26, the original continues through `0x84e2`/`0x83de` particles, `0x7fdd` sprites and
additional level-9 overlays. Those paths, their pose-state effects and particle
consumers remain open. No pose-only or no-owner result counts as proof of them.

### Ranked bodies and links

The eight armour types are `0x1b8b`, `0x1b8f`, `0x1bbe`, `0x1bdb`, `0x1f8b`,
`0x1f8f`, `0x1fbe`, `0x1fdb`. The existing generated recipe executor consumes them
through hero, remote player, NPC, ground and both inventory body paths. Independent
full-function checks pass **2,336 cases**, 292 per type, zero mismatches. The five
previously rejected ancient-tail candidates remain refused.

Two further sprite-only callers use the generated scalar-link executor:

- `0x012cd341`, spear `0x10f0`: bones 1..8 emit flare `0x7ef7`, scale 1.3 and
  intensity times `(0.2,0.1,0.8)`.
- `0x012cb9d7`, shield `0x16f5`: bone 1 and local offset `(15,-15,0)` emit
  `0x7f67` at scale 1.5 and `0x7ef7` at intensity+1.5, with intensity times
  `(0.6,0.6,2)`.

Each caller consumes one common random intensity. Full hand/back-carry caller
comparisons pass **800 cases**, zero mismatches. Native saved-pose, missing-bone and
full-pool tests include both links. They remain character attachments; their own
unrelated body recipes are still refused. No effect/particle/joint implementation,
perf, mesh or scene file changed; the new draw paths allocate no per-frame storage.

### Native evidence and remainder

Six offline PNGs compare three authored scenes before/after. A baseline built from
`a38ec75` item sources uses the same surrounding renderer. The ordinary control is
byte-identical, framebuffer SHA-256 `308aad6447474892fd2f7cabf6dff610b9e59fa602a05c04552c5aeff25a62c9`.
The rank-5/ranked armour scene changes from two refusals to zero and 17 to 36 passes,
with 7,490 changed pixels. Its untextured additive geometry saturates white, so the
pixels do not establish material fidelity. The linked spear/shield scene allocates
ten sprites, changes 25,912 pixels with authored textures, and retains two explicit
body refusals. These are native synthetic renders, not original-client images.

Remaining: **1,012 item bodies**, full rank-5 owner effects, further link targets,
Muun/nested map-object inputs and the prior model, owner/random, selection/shadow,
buff/record, mesh-override, hero-instance, NewUI and external Box of Luck limits.
The combined 14,992 comparisons have zero mismatches, all nine compiled mutants
are detected, and both generated tables reproduce. Release checks and cleanup are recorded in the
[part-8 handoff](../handoffs/RENDER-ITEMS-002H.md).

## Part 9, further ranked bodies and shield links, RENDER-ITEMS-002I

Bounded coverage reaches **769/1,674 bodies**, **17/17 skins**, and **fifteen
RenderLinkItem targets/twenty types**. The 107 body additions comprise 43 armour,
five weapons, one wing and 58 survey `pet/item` types. Exact membership remains
in the generated rendering rules and survey TSVs. All 1,691 compiled admissions
agree with membership; original ranks, identities and stopped states stay intact.
Fifty-five more shapes are complete, for 192 total. The largest completed shapes
are seven-type armour ranks 21, 36, 46 and 49. Visibility remains model-index inference.

The armour helper at `0x01747185..0x017471c9` evaluates `0x0185bdc4(-1,0)`,
then rounds the multiply by 0.8 and add of 0.2 in SSE order. It shares the existing
rank-5 pulse, including signed conversion and remainder by -6283. The optional
level-9 overlay at `0x0174b438..0x0174b4e9` uses U/V `time*0.0001`. Its helper
level word and the effective glow level are distinct inputs. The word is absent
on low-quality fallback paths; a record forcing glow level 9 on a raw-level-zero
item does not enable the overlay. Render flag 0x400 clears glow before the record
rules, so testing that flag alone would incorrectly reject some overlays.
The recipe executor retains the existing six phases and adds high-level variants
of its two base phases. Its scalar sources are evaluated only when requested.

The full ranked survey supplied 133 further fitting candidates. Independent
compiled-C/full-function comparisons rejected 54 and admitted 79. Historical
ancient-tail exclusions remain refused. These are bounded command-stream claims,
not proof from fitting probes or graphics-driver pixels.

Shield `0x16fa`, RenderLinkItem target `0x012dbc1e..0x012dc0ee`, emits 0x7ef7
sprites on bones 1..9, each at scale 1.5. Colour is
`(abs(sin(time*0.001))+0.1)*(0.8,0.3,0.8)` with binary32 operations.
The initial random intensity remains consumed even though unused. The shared
saved-pose native adapter handles these sprites; character, ground and inventory
body callers already consume all new body recipes. Weapon links remain attachments.
No new particle/effect/joint consumer or per-frame allocation was added.

The strict validator passes **31,244 body cases, 80 clock boundaries and 400
full link callers, 31,724 total**, zero mismatches. All **9/9 compiled mutants**
are detected, including the raw-level/quality guard, UV, cosine, ancient phase
and shield colour/bone rules. The inherited part-8 comparison adds 14,992 cases
and 9/9 mutants. All 643 earlier recipe rows keep identical rules and metadata;
21,728 C-to-C preservation cases cover all 679 earlier body/skin types separately.
Representative render changes, preserved controls, release gate and cleanup are in the [part-9 handoff](../handoffs/RENDER-ITEMS-002I.md).
The pinned executable and captures above apply unchanged. **905 bodies remain**,
plus full rank-5 owner effects, further links and the earlier domain/model limits.
Rank-5's 0x84e2/0x83de particles and 0x7fdd owner sprites are listed for the effects
lane; no consumer files were edited. Muun/nested map-object placement stays deferred.


## Part 10, atlas armour, six requested seed bodies and shield links, RENDER-ITEMS-002J

Bounded bodies reach **880/1,674**, up 111: 104 armour, one weapon and the six
requested types 0x2322..0x2327. Skins remain **17/17**; consumed links reach
**seventeen targets/twenty-two types**. The original survey now has 228 complete
shapes. Only coverage membership changes; its historical ranks, identities,
service sites and stopped observations are retained.

The survey's six-type wing label is model-index inference. The installed native
Item.bmd getter maps those types to elemental seeds, codes 6204..6209, all using
s30_seed.bmd. Their original body branch 0x016f5f3e..0x016f6253 suppresses ordinary
level glow and emits flags 2/0x44 in six fixed colours. Excellent/ancient tails
remain. OBJECT hidden mesh +0x68 is explicit for these six types. Full-function
cases vary -1/0/2 independently of flags; native item viewers supply -1 to draw
the seed's only mesh. The inherited zero hides that mesh. Other types retain the
previous domain. This is six seed bodies, not six new wearable-wing mappings.

Rank-39/42 armour uses signed atlas frames `(tick%600)/20` and `(tick%455)/35`,
with 6x5 and 4x4 UV grids. Their ancient mesh streams retain preceding body light
separately from model shade. Fourteen types carry that flag. New scalar sources
also cover strict abs(sin(time*0.0008)), the -6 wave with signed remainder -1047,
binary64 0.9 plus binary32 0.1 and upper clamp one, and the unoffset -4 wave.
Strict absolute value preserves negative zero. The generated scalar mask grows
to thirteen bits; evaluation remains lazy and allocation-free.

The initial full-function screen rejected 69 of 166 fitting candidates. Correcting
the atlas ancient-light path admits fourteen of them; **55 remain refused**.
Earlier ancient-tail exclusions remain refused. An independent hidden-mesh sweep
also rejected a constant fit caused by correlated flag/hidden-mesh probes; generation
now varies those inputs independently. Probes alone do not establish coverage.

Two no-owner shield callers use the existing saved-pose sprite adapter:
0x16f7 at 0x012db542..0x012dba1c and 0x16fb at 0x012dc0f3..0x012dc628. Each emits
ten sprites and consumes its unused common random intensity once. Their full
ordered caller streams include hand variants, deep colours and original owner
arguments. Real position helper 0x012b678d is compared separately with production
transform math for absent owner overrides, nonzero bone translations, scale and
object origin. Persistent owner-follow and global random synchronization remain
unverified. Existing native bitmaps/consumers suffice; no effects-lane file changes.

The strict comparison passes **33,622 cases**, zero mismatches: 32,412 full body
streams, 210 clock boundaries, 800 complete shield callers and 200 real position
helper/compiled-transform comparisons. All **12/12 compiled mutants** are caught;
both tables reproduce. All 750 prior recipe rows retain identical rules/metadata,
and 25,152 compiled before/after cases preserve all 786 prior body/skin types.
All 1,691 survey memberships agree with compiled admission.

The [part-10 handoff](../handoffs/RENDER-ITEMS-002J.md) records the strict families,
compiled mutations, native tests, inspected inventory/armour/link pairs, unchanged
control hash, release gate and cleanup. The executable and capture pins at the
top apply unchanged. **794 bodies remain**, plus rank-5 owner effects and the
previous record/buff/selection/shadow/override, hero-instance, model, NewUI and Box
of Luck limits. Muun/nested map-object tables remain deferred.

## Part 11, per-type wave and sine scalar bodies, RENDER-ITEMS-002K

Bounded bodies increase **880 to 967 of 1,674** (41 weapon, 22 armour and 24 survey `pet/item`
types); skins stay **17/17**; links stay **seventeen targets/twenty-two types**. The survey has
**293 complete shapes** (was 228). Exact membership is in `gen_item_bodies.SCALAR_TYPES` and both TSVs.
**707 bodies remain.**

### Why these bodies were refused

A probe screen over the 751 remaining non-stopping types found 377 that draw only generic
helper calls but have a draw word that no shared input or fixed scalar explains (static + verified).
Most of these words are blend light or body light computed by straight-line SSE code right after
one of two calls:

- the wave helper `0x0185bdc4(a, 0)`: signed period `(int)(6283.1855/a)`, truncated tick
  remainder, `cos(rem*0.001*a)` negated below pi, then `(w+1)*0.5`. This generalizes the fixed
  -4/-1/-6 waves of earlier parts;
- the sin wrapper `0x009681bd(time*k)`.

The constants that follow (`mulss/addss/subss/divss` with absolute operands, or the binary64
`fstp qword .. addsd/mulsd .. cvtsd2ss` form) differ per type.

### Implementation

`gen_item_bodies.py` records the return sites of both calls hit by its probes. For each
site it accepts only the exact pinned byte forms (argument loads, `pop ecx`, `fstp` and reload of the
same local, then at most four constant operations) and reads the constants from the pinned data
image. Only the zero phase argument (`xorps`) is accepted. Its term adds a signed zero to the clock and
cannot change the truncated tick. When a type fails the shared inputs, the parsed programs
are added as extra inputs and the type is probed again. Only programs used in the inferred recipe
are kept, renumbered in first-use order.

`item_bodies.h` gains `mu_rc_body_scalars` (89 programs) and `scalar_first/scalar_count` per
type row. Recipe sources 36.. select the type's own program. `renderchar.c` evaluates them in
`body_scalar`, using a generic `client_wave(a, time)` and the existing `client_sin`. All 897
earlier rows keep identical recipes and flags with the new columns zero.

The probe screen admitted 176 candidates: 67 fit the shared inputs, 109 needed programs.
Independent full-function comparisons rejected 89 of them: all 67 shared-input fits (the
earlier refusals stay refused) and 22 program fits whose level, record or random behaviour
differs outside the probes. Field differences were 62 body light, 12 draw words, 11 draw counts,
and 4 bodies that consume the random stream.

### Checks

`scripts/validate_item_scalars.py --mutations` (manifest row `validate_item_scalars`, private test
`ItemScalars.test_original_instructions`): **26,154 cases, zero mismatches**.

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 87 types times 292 states (body random trapped) | 25,404 | 0 |
| Period edges, INT_MIN, negative zero and 2^31 for one type per distinct program (25), two flag sets | 750 | 0 |

All **11/11 separately compiled mutants** are caught: wave period 14,169; wave sign 14,960;
wave scale 7,631; sine argument 11,090; single-precision multiply 24,282; single-precision add 25,510;
binary64 form 322; scalar slot 610; scalar count 26,154; mesh index 24,634; object alpha 15,200.
The body table reproduces from the pinned instructions.

Compiled C-to-C checks of the base `fa63719` library against this one cover all 897 earlier
body/skin types in **28,704 random cases, zero mismatches**. Over all 1,691 survey types, only the 87
new types change admission. All 1,691 survey memberships agree with compiled admission.

### Limits

Remaining program-like refusals are mostly integer UV clocks with per-type constants
(`-(tick % N)/N`, atlas frames with other periods and columns), locals written in other branches,
level-dependent draw counts (72 shapes), immediate `glColor` calls and body-owned effects/particles.
Each needs its own instruction form; they are not claimed. No new link target was added:
Laser/17 and the shared clock/bone-state links stay partial, and no further RenderLinkItem target
was surveyed in this part.


## Part 12, clock-chain and level-split bodies, two link rows, RENDER-ITEMS-002L

Bounded bodies increase **967 to 1,053 of 1,674**, adding **86 types**: 66 through clock chains and
20 through the existing level split. Skins stay **17/17**. Links increase **seventeen
targets/twenty-two types to eighteen/twenty-four**. Exact membership is in
`gen_item_bodies.CHAIN_TYPES`, `LEVEL_TYPES` and both TSVs. The survey has **362 complete shapes**, up from 293. **621 bodies remain.**

### Selection

The part-11 probe screen was rerun over the 664 remaining non-stopping types and each refusal was
classified by its first failure (static + verified):

| First failure | Types |
|---|---:|
| a draw word no input explains (132 of them UV) | 196 |
| body-owned effects/particles in the stream | 157 |
| immediate `glColor3f/3fv/4f` calls (alone or with matrix calls) | 93 |
| fit by probes, refused by the full comparison (part 11) | 89 |
| level-dependent draw count | 72 |
| helper phases do not align with the generic phases | 49 |
| other (matrix/transform services) | 8 |

UV words were the largest group. Disassembly of executed clock reads showed compiler-generated
integer and SSE code, for example `-(tick%2000)*0.0005`, `(int)(time*k_d)%8/2*k`,
`(tick%1200)/80%4*0.25` atlas frames, `(e - tick%(e+1))/e` with `e` a local set earlier, and
`time*k`. Fixed templates do not cover these, so this part slices them.

### Clock chains

Every probe records each executed basic block that contains an instruction reading the clock global
`0x06fce370` (2,155 such instructions in the text). `slice_block` walks the pinned bytes forward from
the block start and tracks GPR, binary32 and binary64 values. It folds:

- clock loads (`movss`, `cvtss2sd`, `cvttss2si`), data-image constants and immediates;
- `mulss/divss/addss/subss` and the `sd` forms, in both operand orders, `cvt*` conversions and the
  `xorps/xorpd` sign mask;
- `cdq; idiv` by a constant, the signed power-of-two remainder `and r,0x8000000m; jns; dec; or; inc`
  (bytes checked exactly) and quotient `cdq; (and edx,m;) add/sub; sar`;
- integer add/sub (both orders), inc/dec/neg, imul and shl by constants.

A local read before any write in the walk takes its value at block entry, as an affine
`entry*mul+add`. That value must also appear as `mov dword [ebp+off], imm` in the text. Any other
instruction clears only what it writes; branches other than the idiom and unconditional `jmp` end
the walk. Each chain whose result is stored as binary32 (local, argument or OBJECT field) becomes a
candidate input, kind 3 in `mu_rc_body_scalars` (up to nine op/constant pairs).
`renderchar.c::clock_program` evaluates it inside the body executor, with cvtt indefinite results,
C99 truncating division and wrapping integer steps. Divisors 0 and -1 are excluded by the generator.
Helper programs keep their part-11 order and chains come after them, so every earlier row is
unchanged.

The screen fitted 106 of 196 field-failure types with chains. The independent 292-state comparison
admitted 66. The other 40 differ outside the probes: body light that depends on quality branches
(most), 1-ulp blend light on the quality-0 path, phase-5 UV, or body random consumption.

### Level split

The 72 count failures add draws above level 9 after the +7 quality cap. Applying the part-9 level
split (phases 6/7) fits 55 of them by probes; 20 pass the full comparison. These are the
`0x1a25..0x2232` armour neighbours of the part-9 clock types. The rest differ in body light or
consume body random, and stay refused.

### Link table additions

All 11,722 item and skin types were run through RenderLinkItem `0x012bd910`. Thirty emit sprites;
the unknown ones were fitted against the existing chain and pulse schemas, and two are plain table rows:

- `0x0f0b` shares target `0x012cbb43` and the rule of `0x0eed` (sprite sites `0x012cbc4d/0x012cbd09`);
- `0x0ef3`, target `0x012cc846..0x012cca02`, is a sprite-chain row: bone 0, one `0x7ef7` flare, RGB
  intensity*(1,0.3,0.1), with the conditional grey `0x7f67` flash.

Both are admitted by the shared table query and the native attachment hook. `0x12fa` multiplies two
scalars and `0xafc` uses a further clock term, so they are not table additions. Laser/17 and the
shared clock/bone-state links stay partial.

### Checks

`scripts/validate_item_chains.py --mutations` (private test `ItemChains.test_original_instructions`,
manifest row) passes **35,346 comparisons, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 86 types times 292 states, body random trapped | 25,112 | 0 |
| Divisor edges, INT_MIN, 2^31, -0.0 for one type per distinct chain (59), flags 2/0x40042 | 2,714 | 0 |
| Level-split boundaries: 20 types, 16 levels, 7 qualities, 3 flag words | 6,720 | 0 |
| Two link callers, 100 random sequences times 4 clock/hand variants | 800 | 0 |

All **17/17 separately compiled mutants** are caught: chain kind 21,980; tick 13,115; indefinite
106; remainder 17,342; quotient 2,969; convert 19,238; multiply 21,281; divide 6,799; negate
4,756; reverse subtract 1,958; integer negate 2,678; slot 15,117; level split 427; mesh index
34,546; object alpha 18,525; link flash 260; link pulse 300. The body, link and pulse tables
reproduce from the pinned instructions.

Compiled C-to-C checks of the base `f4eba8a` library against this one cover all **952 earlier
body/skin types in 30,464 random cases** and 440 link cases, all with zero mismatches. Over all 1,691
survey types, admission changes for exactly the 86 new types. The 948 earlier generated rows keep
identical recipes, flags and programs after re-indexing.

### Limits

**621 bodies** remain. Body-owned effects/particles and immediate `glColor` calls need consumers
outside the draw-record ABI and are not claimed. Neither are quality-branch body light,
non-aligned helper phases or the 89 probe-fitting refusals. Rank-5 owner effects, Muun and
nested map-object tables, and the earlier record, buff, selection, shadow, override, NewUI and Box
of Luck limits are unchanged.


## Part 13, carried model fields and immediate glColor records, RENDER-ITEMS-002M

Bounded bodies increase **1,053 to 1,162 of 1,674**, adding **109 types**: 89 through carried model fields and
20 through immediate `glColor` records. Skins stay **17/17** and links stay **eighteen targets/twenty-four
types**. Exact membership is in `gen_item_bodies.CARRY_TYPES` and `COLOUR_TYPES` and in both TSVs. The survey
has **461 complete shapes**, up from 362; shape identities, ranks and stopped observations are unchanged. **512
bodies remain** (469 non-stopping).

### Selection

The 578 remaining non-stopping types were probed again with glColor calls recorded into the stream (below).
175 fit the probes. Only 20 passed the independent 292-state comparison. All 155 failures had quality 0-2, while
the probes sample quality 9 (static + verified):

| Full-comparison failure (175 probe fits) | Types |
|---|---:|
| body light of a later helper (quality 1 at levels 5-15, quality 2 at levels 0-7) | 97 |
| draw arguments (1-ulp blend light, quality 0) | 21 |
| extra draws at quality 1 (wings) | 25 |
| body random | 12 |

### Carried model fields

The 97 body-light failures have one cause. The client's model object keeps BodyLight, the level word, the
shade and byte `+0xca` after the body's own draws. The helpers that follow start from those values. The ancient
pass `0x840` keeps the light (`ancient_color` is a no-op outside the armour groups), PartObjectColor2 scales it,
and the excellent and colour2 passes overwrite it. At quality 9 the colour helpers overwrite the light first,
which hides the effect from the probes. At quality 1 those helpers are skipped or take the `0x44` branch, and the
ancient pass draws with the body's last light. The recipe executor never wrote its draws back to the model, so
it used the generic light (verified: `0x0b00` level 9, quality 1, ext 1).

Rows now have a `carry` column. For carry types, `emit_parameter_body` copies the model fields of the last
BODY/MESH draw of each applied recipe back to the model. To infer recipes with the inputs this executor sees,
the generator calls the probe entry `mu_rc_item_draws_carry`. This is the generic path, except that after
helper call k it writes back the model fields of the client's last draw in group k. With carry, 156 types fit
and **109 pass** the full comparison. The 20 non-carry passes are among them and stay non-carry. Carry is off
for all earlier rows.

### Immediate glColor records

93 types (part-12 count) call `glColor3f/3fv/4f` between draws, mostly `glColor3fv(model+0x54)`. These calls are
now part of the draw stream. `gen_item_bodies.record_colours` records each call in order, reading the colour at
call time, as a COLOR record: kind 1/2/3 = 3f/3fv/4f, alpha (1 for three components) and RGB. The generator
infers them like any draw word. `MU_RC_ENTRY_COLOR` is the third entry kind of `mu_rc_draw`. The native item
consumer (`native/core/mu_renderchar.c`) passes it to the backend's current colour and GL recorder. The texture
prober skips it. The mesh draw sets its own colour before its vertices on every path except the untextured
additive mode `0x40` with lighting on and no light mesh (`mu_meshdraw.c` 0x012ba812). There, and for later GL
consumers, the current colour is visible. In the part-13 gallery, the COLOR records change zero pixels. 32 of the
109 types emit them.

### Checks

`scripts/validate_item_carry.py --mutations` has a manifest row and the private test
`ItemCarry.test_original_instructions`. It passes **114,388 comparisons, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 109 types times 292 states, body random trapped, glColor recorded | 31,828 | 0 |
| Carry boundaries: 89 types, 16 levels, 7 qualities, 4 option/ext pairs, 2 flag words | 79,744 | 0 |
| Colour types (32) in the 11 survey states with zero, -0.0, NaN, FLT_MAX, denormal and random light words | 2,816 | 0 |

The colour family compares 4,192 COLOR records. All **12/12 separately compiled mutants** are caught: colour
drop 21,736; colour RGB 21,732; colour alpha 21,736; colour kind 5,348; carry off 27,243; carry first-draw
13,870; carry light 27,243; carry channel 27,243; carry shade 81,507; carry flag 66,817; mesh index 106,893;
object alpha 85,530. Four candidate mutants were equivalent in this domain and are not counted. The
entry-kind test is equivalent because an entry-3 record in the MESH branch keeps kind, alpha and RGB. Omitting
the level, shade or flag write-back is equivalent because these bodies leave those fields as the generic path
set them. Writing a wrong shade or flag is caught (the last two counts). The body table reproduces from the
pinned instructions.

Compiled C-to-C checks of the base `9b821b19` library against this one cover all **1,038 earlier types (1,034
bodies and 4 skin types) in 33,216 random cases** and 960 link cases, zero mismatches. Over all 1,691 survey
types, admission changes for exactly the 109 new types.

### The +13 glow "saturated white"

Parts 11 and 12 saw +13 items, including code 28 and code 0, go fully white natively. The glow passes match the
original. At +13 with quality above 3, RenderObjDraw draws the body at light 0.9, then `0x240` and `0x1040`
(additive ONE,ONE, environment UVs, Chrome02 `0x7fcf`, colour 0.9 and 0.81). It then draws `0x48` and `0x44`
(additive, Shiny01 `0x7f66`/Chrome01 `0x7f1f`) in the EnchantEffect colour. Blend modes and texture selection
come from the Unicorn-validated mesh-draw port. The raster clamps vertex colours and blend results to [0,1], as
GL does, and all six special bitmaps load from `Data/Effect`.

The white came from an input. `mu-render ui inventory` takes the enchant colour from `mu_lang`
(NATIVE-LANG-001), and `mu_lang` returns NULL without `MU_LANG_DIR`. `fill_item` then keeps `env.glow_color =
(1,1,1)`, so both enchant passes add white over chrome (verified by render). With the local decoded tables, code 0
takes the table default (1, 0.5, 0) and glows orange. Code 28 takes its row (0.8, 0.8, 1) and glows pale
lavender. White pixels in the crop fall from 241 to 89, where the near-white enchant plus chrome clips as GL
would (offline native renders, not original-client pixel comparisons). The finding is that the glow is faithful
and the earlier white came from a missing table. The inventory tool now prints a one-line stderr warning when
`MU_LANG_DIR` is unset. Its JSON output and hashes are unchanged.

### Limits

**512 bodies** remain. By first failure, the 469 non-stopping ones are:

| First failure | Types |
|---|---:|
| no recipe fits the probes (non-aligned helper phases, unexplained draw words) | 187 |
| body-owned effects/particles in the stream | 169 |
| body random consumption | 56 |
| fit, but extra/missing draws at quality 1-2 (mostly wings `0x23xx/0x24xx`) | 25 |
| fit, but 1-ulp blend light on the quality-0 path (binary32 versus binary64 pulse) | 17 |
| matrix/transform services (`glPushMatrix` pairs, transform) | 13 |
| fit, but body light | 2 |

Body-owned effects still need consumers outside the draw-record ABI. The quality-0 blend precision and the wing
quality-1 draws are quality-dependent recipes, which the probes (quality 9) cannot infer. They are not claimed.
Rank-5 owner effects, Muun and nested map-object tables, and the earlier record, buff, selection, shadow,
override, NewUI and Box of Luck limits are unchanged.

## Part 14, record/quality probes, exit model fields and body random, RENDER-ITEMS-002N

Bounded bodies increase **1,162 to 1,213 of 1,674**, adding **51 types**. Skins stay **17/17** and links stay
**eighteen targets/twenty-four types**. Membership is in `gen_item_bodies.QUALITY_TYPES` (51; 34 of them also in
`EXIT_TYPES`) and in both TSVs. **461 bodies remain.**

### Why part 13's quality-dependent refusals failed (verified)

Part 13 labelled 25 refusals "extra draws at quality 1-2" and 17 "1-ulp blend light on the quality-0 path". The
full comparisons show different causes:

- **Wings.** Every failing case has a record of kind B `0x26` or `0x5b`. That record forces glow level 9
  (`0x0176dc26/0x0176dc50`), so RenderObjDraw runs the `0x44` (and above quality 1, `0x48`) helper. The
  probes use a record-free item at levels 0/7/13. The wing glow rows map those to 0, so the helper phase was
  never sampled and its recipe was empty: missing draws (`0x230f`, state 17).
- **Blend precision.** `0x0f0c` draws its last mesh with `wave(-4,0) * 0.7f + 0.3f` in binary32 and no clamp
  (`0x01712b6e..0x01712b93`). The shared input 20 is the binary64 armour pulse with a clamp. Both agree at
  every probe clock, so the per-type program (part-11 kind 1, already parseable) was never tried.
- **Body light at helper passes.** `0xb10` and similar bodies leave the model at fields that are not their last
  draw's. At the return to `0x017e1f3d`, the model light is (1,1,1) after a last draw at (1, 0.8, 0.2).
  Part 13's carry rule (last draw) does not fit them.

### Supplementary probes

For `QUALITY_TYPES` only, `gen_item_bodies.supplement` adds probes. They cover records `(0,0,0)`,
`(0,0x26,0)` and `(0,0x5b,0)` at qualities 0, 1, 2 and 9 and levels 0/7/13, with six further seeds (further
clocks). The excellent/ancient tails are probed at qualities 1, 2 and 9. Earlier types keep the record-free
quality-9 probes, so their recipes do not change.

### Exit model fields (EXIT entry)

The generator hooks the 65 return sites of RenderObjDraw's calls to the three helpers (`0x016e036c`,
`0x016dc148`, `0x016dec15`) and snapshots body light, level word, shade and `+0xca` there. Each helper's group
gains an EXIT pseudo-record, inferred like any draw word. The probe entry `mu_rc_item_draws_carry` starts
each later helper from those fields. Recipe entry 4 makes `apply_recipe` write words 8..15 to the model. It
is not a draw and never reaches the draw stream. The excellent tail is not one of the three helpers. It has
no snapshot and needs none, because nothing follows it.

One probe-path fix was needed. For a type outside the table, the plain `part_body` fallback did not write
back or advance the probe phase, so every later helper read the wrong snapshot. This affects only the probe
entry (`probe_carry` set). The rendering path is unchanged.

### Body random (kind-4 programs)

At a CRT rand (`0x01989721`) return site the generator accepts exactly `cdq; push n; pop ecx` (or
`mov ecx, n`)`; idiv ecx; cvtsi2ss xmm0, edx`, then up to four binary32 `mulss/addss/subss/divss` data
constants. Programs record the phases whose helper call draws them. A type whose rand site has another form,
draws one site twice in a helper, or draws in some probes of a phase only is refused. In the probes, rand
returns a scripted sequence. The executor draws through `mu_rc_item_context.random`, as rank 5 does, once
per program in client call order, only in the program's phases. Two types are admitted. `0x0b22` uses
`(rand() % 15) / 21.5 + 0.4` as a mesh blend light (`0x016ebefc`). `0x0f0d` uses `(rand() % 20) / 52.5 +
0.4`. Both draw it in the body phases 0/5. Nine more random bodies (`0xb3b, 0xb43, 0xb45, 0x171d..0x171f,
0x1742..0x1744`) fit the old constant-rand probes but no recipe with scripted rand. `0x171d` (verified,
`0x01752cb4`) scales the body-light vector (0.9, 0.4, 0.2) by its value through `0x00cfcd74`, and the recipe
has no product source for that. They stay refused.

### Checks

`scripts/validate_item_quality.py --mutations` has a manifest row and the private test
`ItemQuality.test_original_instructions`. Client and C get the same rand sequence, and the number of rand
results each consumes must also match. It passes **28,080 comparisons, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 51 types times 292 states, rand scripted, glColor recorded | 14,892 | 0 |
| Kind-B 0x26/0x5b records, qualities 0/1/2/9, levels 0-15, two tail pairs | 13,056 | 0 |
| Random types in the 11 survey states with edge sequences (0, 32767, n-1, multiples of n) | 132 | 0 |

The random family compares 132 rand results. All **11/11 separately compiled mutants** are caught, counting rand results consumed as well as draw words: exit off 2,006; exit light 2,006; exit level (+1) 12,624; exit shade 13,878; exit flag 13,447; random modulus 721; random divide 895; random phase mask 934; random value 1,228; mesh index 22,052; object alpha 20,956. Omitting the exit level write is equivalent in this domain, because RenderObjDraw rewrites the level word before any helper reads it. It is documented here and not counted. The body table reproduces from the pinned instructions.

Compiled C-to-C, base `d5ffde0a` library against this one: **1,147 earlier types (1,143 bodies and 4 skin
types) in 36,704 random cases**, each with and without a rand context, zero mismatches. Over all 1,691 survey
types, admission changes for exactly the 51 new types.

### Limits

**461 bodies** remain (418 non-stopping). At the probe stage of the 469 part-13 refusals, 185 call body-owned
effects/particles or matrix/transform services. Most of the rest are no-recipe clusters (draw count/phase
mismatches, unexplained draw words), plus the random bodies above. The record/quality probes and EXIT inference apply only to part-14 types. Earlier rows keep
their part-1..13 probes and still pass their own validators. Rank-5 owner effects, Muun and nested map-object
tables, and the earlier limits are unchanged.

## Part 15, body random scaling a constant body light, RENDER-ITEMS-002O

Bounded bodies increase **1,213 to 1,219 of 1,674**, adding **6 types** (`gen_item_bodies.PRODUCT_TYPES`:
`0x171d..0x171f`, `0x1742..0x1744`; each `0x174x` shares the body code of `0x171x`). Skins stay **17/17** and
links stay **eighteen targets/twenty-four types**. **455 bodies remain**. The survey keeps 798 shapes; the three
shapes of these types are now complete.

### The body (verified)

Part 14 left these bodies refused because the light of one draw is a product. At `0x01752c6c..0x01752d45`
(`0x171d`; `0x01752f50..` for `0x171e`, `0x017531a8..` for `0x171f`) the body saves `model+0x54`, sets it
to a constant vector with `0x00cfcead` (vec3 set: three binary32 stores), draws `rand()` and computes
`(float)(rand() % 15) / 37.5 + 0.5`, scales the vector with `0x00cfcd74` (`*=`: `0x00cfcb3c` multiplies each
component with `mulss`, `0x00cfc8f2` assigns), draws mesh 4 (`0x42`) with it, and restores the saved light.
The constants are (0.9, 0.4, 0.2), (0.8, 0.5, 0.2) and (0.1, 0.4, 0.3).

- **Generator.** `parse_scale` reads the idiom around the rand return site (the three pushed constants, the
  `model+0x54` receiver of both calls) and adds three **kind-5 programs** after the kind-4 program: value =
  binary32 `k * (program a)`, one per light channel. The recipe inference matches the draw's light words to
  them like any other input. Only `PRODUCT_TYPES` get them; every earlier row is generated unchanged.
- **Executor.** `renderchar.c`'s scalar loop evaluates kind 5 from the kind-4 value already in the input
  array (`input[35 + a]`); no extra rand is consumed.
- The other three random bodies (`0xb3b`, `0xb43`, `0xb45`) draw rand at `0x011ff68d`, outside the body
  helpers; they stay refused.

### Checks

`scripts/validate_item_product.py --mutations` has a manifest row and the private test
`ItemProduct.test_original_instructions`. Client and C get the same rand sequence and must consume the same
number of results. It passes **2,874 comparisons, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 6 types times 292 states, rand scripted, glColor recorded | 1,752 | 0 |
| Product types in the 11 survey states, every residue 0..14 of the modulus, 32767 and random sequences | 1,122 | 0 |

All **7/7 separately compiled mutants** are caught: product off, constant, source index, operation and kind
2,874 each; random phase 2,237; mesh index 2,874. The body table reproduces from the pinned instructions.

Compiled C-to-C, main `5cb6fa6d` library against this one: **1,194 earlier body types, 19 rank-5 and 4 skin
types in 77,888 random cases** (32 states each, with and without a rand context), zero mismatches. Over all
1,691 survey types, admission changes for exactly the 6 new types. Portable `test_item_product.py`: 3 tests,
one private skip; it checks admission, refusal outside the domain and the product light of one draw for rand
results 0, 14 and 108.

## Part 16, census of the 455 remaining bodies and derived body programs, RENDER-ITEMS-002P

Bounded bodies increase **1,219 to 1,276 of 1,674**, adding **57 types** (`gen_item_bodies.DERIVED_TYPES`; 13 of
them in `DERIVED_CARRY`). Skins stay **17/17**, links stay **eighteen targets/twenty-four types**. **398 bodies
remain.** The survey keeps 798 shapes; complete shapes go 500 to 543.

### Census (static + verified probes)

All 455 refusals were run under Unicorn: the eleven survey states with the plain item world (services recorded),
then the generator probes with rand scripted and the parsed per-type programs. The first blocker of each type:

| Blocker | Types | Weapon | Armour | Wing | Pet/item | Draws fit with the effect calls set aside |
|---|---:|---:|---:|---:|---:|---:|
| Draw word one binary32 operation from an input (**implemented here**) | 57 | 40 | 10 | 3 | 4 | - |
| Helper-group count (client helper calls differ from the generic path) | 54 | 2 | 0 | 13 | 39 | - |
| Effects: bone sprite `0x0150e746` + CreateParticle `0x0168fafd` | 51 | 22 | 0 | 29 | 0 | 34 |
| Effects: bone sprite `0x0150e746` only | 50 | 30 | 0 | 20 | 0 | 33 |
| No recipe: other unexplained draw words | 50 | 39 | 4 | 3 | 4 | - |
| Effects: CreateParticle + CreateSprite `0x01692eb7` at owner bones (`0x012b678d`) | 42 | 0 | 38 | 4 | 0 | 40 |
| Random helper `0x011ff622` (rand at `0x011ff68d`) | 39 | 39 | 0 | 0 | 0 | - |
| Fault in CRT strlen `0x0195a4e0` (helm/pants/gloves/boots of the rank-5 sets) | 31 | 3 | 28 | 0 | 0 | - |
| No recipe: draw count varies within a phase | 18 | 7 | 0 | 11 | 0 | - |
| Effects: CreateSprite only | 16 | 2 | 5 | 6 | 3 | 16 |
| GL matrix services (`glPushMatrix`/`glPopMatrix`) | 13 | 10 | 0 | 0 | 3 | - |
| Effects: all three services | 9 | 0 | 0 | 9 | 0 | 0 |
| Faults at `0x016ddc73`/`0x016df9a0` (5) and `0x016eef60` (2) | 7 | 5 | 0 | 0 | 2 | - |
| Fit the probes, fail the full comparison at quality 0 (`0x2003`, `0x2007`, `0x2009`, `0x200f`, `0x2010`) | 5 | 0 | 5 | 0 | 0 | - |
| Other rand sites (`0x01707a5e`, `0x016ec26d`, `0x017125a6`, `0x01710a09`) | 4 | 4 | 0 | 0 | 0 | - |
| Effects with a fault | 4 | 0 | 0 | 4 | 0 | 0 |
| Model transform `0x00966ea5` (`0x239e`, `0x23a1`, `0x23a5`) | 3 | 0 | 0 | 3 | 0 | - |
| Effects: CreateParticle only | 2 | 2 | 0 | 0 | 0 | 0 |
| **Total** | **455** | 205 | 90 | 105 | 55 | 123 |

Weapons, armour and wings are the equippable, most-seen groups (400 of 455). The effect services are the largest
group (174 types, 190 with the GL matrix and model transform calls). Their draws alone fit for 123 of them.

### What the effect bodies need (verified on samples, static reading)

- **`0x0150e746(model, bitmap, bone, scale, light, OBJECT, rotation, a7, axes)`** is CreateSprite `0x01692eb7` at
  TransformPosition(BoneTransform `0x06fce398` + 0x30·bone, 0, translate 1): the item's **own** posed bones. The bone
  is often a named lookup (`0x012bd35a(name, -1)`, e.g. `0x0f1f`), so the item world gives -1. Light is frequently a
  random or clock-scaled vector (`0x0b4b`: (0.7, 0.5, 0.3) × a per-frame scalar). The existing owner host
  (`mu_rc_owner_host.transform`) answers OBJECT owner bones, not the item's own bones, so these requests have no
  consumer behind the item executor. RENDER-ITEMS' link-effect consumer (`mu_renderchar_link_effects`) has the item
  bones but is RenderLinkItem's own switch.
- **The armour group `0x1bc3..0x1c78` (38 types)** transforms with `0x012b678d(out, OBJECT, bone, local)`:
  VectorTransform(local, owner bone `0x0129f12c` or BoneTransform) × model scale `+0x74` + OBJECT position `+0x158`.
  That is the owner-host transform. Four code templates cover the 38 types: two sprites per owner bone (26, 27, 36,
  18, 35 ...), then one to four `rand() % 2 == 0` gates (`0x0173e869` → `0x0173e86e`, `0x0174290e`), each followed by
  CreateParticle (`0x810a`, subtype 7) whose scale or position jitter comes from `0x011ff622(lo, hi, step)` and
  vec3 arithmetic (`0x00cfca74` add, `0x00cfcad8` subtract, `0x00cfd0cc` normalize). The particle angle is OBJECT
  `+0x164`; `mu_rc_owner_fx` has no angle field and the native consumer passes zero. Modelling needs a small
  per-type effect program (owner transform, sprite/particle requests, rand gates, step randoms and the vec3 sums)
  inferred from the client's call arguments with authored owner bones. It is not attempted here.
- **The random-helper weapons (39)** draw `0x011ff622` for effects that only appear for some rand results; with
  rand 0 the survey sees no effect call.

### Derived body programs (kind 6; verified)

Of the 125 no-recipe types, many draw a word that is one binary32 operation away from an input the recipes already
know: a light channel times a constant (`0x0b6d`: red and green s × 0.7 and s × 0.4 for its parsed program s), a clock
program plus a constant (`0x0afd`: light (s, s, s + 0.1), the `addss` at `0x016f1d0f`), the generic body light times a
constant (`0x1afa`: (0.85, 0.85, 1.2)), the object alpha times a constant (`0x1be6`), or a negated program (× -1, `0x1554`).

- **Generator.** For `DERIVED_TYPES`, when the parsed programs leave words unexplained, `derive` solves
  `word = f32(input op k)` for one constant over every probe of the phase (inputs: the float generic words, object
  alpha, pulsed light, clock scalars and earlier programs; ops mul/add/sub/div). A candidate is kept only if the
  text holds that `mulss/addss/subss/divss xmm, [abs]` on that constant (`sse_operands`). Each solution becomes a
  **kind-6 program** `(6, input a, ((op, k),))`; the recipe then copies it like any program input. Up to three
  rounds allow a program read by another. Earlier rows are generated unchanged (checked by rendering all 1,200
  earlier rows with the edited generator: only the header comment differs).
- **Executor.** `renderchar.c`'s scalar loop evaluates kind 6 from `input[a]` (an earlier input or program) with
  the binary32 chain (`derived_program`). No rand is drawn.
- **Selection.** 66 of the 125 candidates fit the probes; 57 pass the independent 292-state comparison, 13 of
  them with the part-13 carry rule (their last draw's light reaches the ancient pass at qualities 1-2). Rejected:
  `0x0b36`, `0x1103`, `0x1524` (an extra draw at quality 2 the level split does not predict) and the wings
  `0x239c`, `0x239f`, `0x23a2`, `0x23a3`, `0x23a4`, `0x23a6` (their extra draws start below level 9 at quality 2).
  Words in integer fields (`0x231b`, `0x231c`: flags | 0x40; `0x24e3`) are not derived.

### Checks

`scripts/validate_item_derived.py --mutations` (manifest row, private test `ItemDerived.test_original_instructions`):
**36,252 comparisons, zero mismatches**. Client and C get the same scripted rand sequence and must consume the same
number of results (zero here).

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 57 types times 292 states, rand scripted, glColor recorded | 16,644 | 0 |
| Derived: 11 survey states × 8 clocks (0 to 1,999,999, period edges), records none/0x26/0x5b, random model light and alpha; 118 kind-6 programs | 5,016 | 0 |
| Kind-B 0x26/0x5b records, qualities 0/1/2/9, levels 0-15, with and without the tails | 14,592 | 0 |

All **7/7 separately compiled mutants** are caught: derived off 35,910; source index 35,713; kind 35,789;
multiply 30,778; add→subtract 5,088; one operation short 35,910; carry off 907. The body table reproduces from the
pinned instructions.

Compiled C-to-C, main `6ef9059e` library against this one, every one of the 1,691 survey types, 32 random states,
with and without a rand context: **108,224 cases**; 104,576 identical, and the 3,648 different ones are exactly
the 57 new types (refused before). Portable `test_item_derived.py`: 4 tests, one private skip (admission and
refusal, kind-6 sources, and `0x1afa`'s light as the generic light times (0.85, 0.85, 1.2)).

### Limits

398 bodies remain (table above minus the 57). The effect bodies need a consumer of the item's own bone
transform (bone sprites) or a per-type effect program over the owner host (armour group). The remaining no-recipe
words need two-operation or integer derivations. The quality-0 armour types and the level-split wings need
per-quality probes. Muun, nested map-object tables and the earlier limits are unchanged.

## Part 17, owner-effect programs of the armour bodies, RENDER-ITEMS-002Q

Bounded bodies increase **1,276 to 1,319 of 1,674**, adding **43 types** (`gen_item_owner_fx.OWNER_FX_TYPES`): the
38 worn chest pieces `0x1bc3..0x1c78` that part 16 named, and five helm bodies (`0x19f4`, `0x19fa`, `0x1a00`,
`0x1a1f`, `0x1a78`) with one owner-bone sprite. Skins stay **17/17**, links stay **eighteen targets/twenty-four
types**. **355 bodies remain.** The survey keeps 798 shapes; complete shapes go 543 to 556.

### The effect blocks (verified)

Each body ends its RenderPartObjectBody type case with an effect block after the type's mesh draws. The locals
are vec3/float objects constructed at the scope entry (`0x0173d2d8`, `0x01741212`; `0x0095ea8e` zeroes them).
The blocks use only these services:

- `0x012b678d(model; out, OBJECT, bone, local)`: nothing when the bone is negative or not below the item model's
  bone count (+0x22); otherwise the OBJECT owner bone (`0x0129f12c`: OBJECT +0x318 + 0x30·bone, when the OBJECT
  model has that bone) or BoneTransform `0x06fce398` + 0x30·bone, VectorTransform `0x00d002b2` of the local point,
  times the model scale (+0x74), plus the OBJECT position (+0x158). For worn parts the native part model's
  origin is the OBJECT position and its scale the object scale, so the existing owner transform serves it.
- CreateSprite `0x01692eb7(bitmap, position, scale, light, OBJECT, 0.0, 0, 4, axes)`; the axes object
  `0x00a0c1d0` holds the words 1, 1 and 1.0f.
- CreateParticle `0x0168fafd(bitmap, position, angle, light, subtype, scale, 0, 0)`. The angle is OBJECT +0x164
  (`0x810a`/7 and `0x7f26`/0x26) or a normalized owner-bone difference (`0x810a`/15).
- `rand() % 2` (and/jns/dec/or/inc idiom) and `rand() % 5` (cdq/idiv) gates that skip to the block end.
- `0x011ff622(lo, hi, steps)`: one rand, `(rand() % (b - a + 1) + a) / steps` in binary32 with
  `a = (int)(steps·lo)`, `b = (int)(steps·hi)`, then the two clamps.
- vec3 helpers: set/construct (`0x00cfcead`, `0x0098a0e5`), assign `0x00cfc8f2`, subtract `0x00cfcad8`,
  add `0x00cfca74`, normalize `0x00cfd0cc` (`0x00cfd15f`: length `(float)sqrt((double)((x·x + y·y) + z·z))`,
  zero vector below 1e-6, otherwise each component times 1/length).

Thirteen blocks (eleven for the armour, two for the helms) reduce to seven distinct programs. Four code
templates: (1) sprites `0x7f7a` at four owner bones (two each) and `0x8109` at bone 35, one `% 2` gate, particle
`0x810a`/7 with the OBJECT angle and a `0x011ff622(…, 100)` scale; (2) sprites, a `% 2` gate with particle
`0x7f26`/0x26, a second sprite/particle pair; (3) the same with a further owner transform; (4) the 0x1bde,
0x1bf0..0x1c78 bodies: sprite `0x810a` at bone 26, the normalized direction from bone 19 to bone 26, then a
`% 2` or `% 5` gate, a position jitter from three `0x011ff622(-k, k, 1)` draws and a particle `0x810a`/15 along
that direction; twice (bones 26 and 35).

### Reading the programs (generator; static with concrete frames)

`scripts/gen_item_owner_fx.py` runs each type in four survey states under Unicorn, finds the block (from the
last draw before the first effect service to the first unconditional jump after the last one), and walks it
with an abstract interpreter over the MSVC idioms above. Constants fold exactly in binary32; owner positions,
randoms, the OBJECT angle and normalized vectors become registers. A frame word the block reads before writing
it comes from the frame at the block start, and must be the same in every state. A gated region's writes are
unreadable after the join. Any other instruction, call or operand refuses the type. The output,
`reconstructed/renderchar/item_owner_fx.h`, is a flat op table (const, mov, add, sub, gate, range, transform,
normalize, angle, sprite, particle) with one row per type: first op, count, registers and the highest bone.

Refused by the reader ("no draw before the effect block"): `0x0f1e` and `0x174a` (their owner-bone particle is
created in RenderObjDraw at `0x017d40c4`/`0x017dda31`, before the body helper) and the wings `0x23a8`/`0x23a9`
(owner-bone particles plus item-bone sprites `0x0150e746`, also before the body draws). `0x24c6` faults in the
plain world at `0x01782fec`.

### Executor and native consumers

- `renderchar.c` (`owner_fx.inc`) runs the program after the type's base body draws (phases 0, 5, 6, 7), only
  through `mu_rc_item_draws_owner`. Its random comes from the owner host, in client order. It runs only when
  `mu_rc_item_owner_fx(type)` (highest bone + 1) is at most the host's OBJECT bone count and the new
  `item_bones`. Below that the client reads stale positions or BoneTransform, and the library creates nothing.
- `mu_rc_owner_fx` gains `angle[3]` (zero for the rank-5 block); `mu_rc_owner_host` gains `item_bones` and the
  OBJECT `angle[3]`. The draws are generated by `gen_item_bodies` with the effect requests set aside (all 43
  fit the generic recipes without carry or programs beyond the parsed ones).
- Native (`mu_renderchar.c`): requests go to the existing consumers, `mu_world_particles_create` (now with the
  request's angle) and `mu_world_particles_sprite`. `mu_renderchar_owner` gains `refused`
  (requests no native kind creates, plus programs outside the bone domain) and the OBJECT angle;
  `mu-render character --world-render` prints `owner_refused`.
- Native result (`mu-render character --world-render`, synthetic 50-bone part, armour `0x1bc3`): frame 0
  creates the nine sprites (the `% 2` gate is odd); over three frames 27 sprites are created and the one opened
  gate's CreateParticle `0x810a`/7 is refused (no native particle kind). A 35-bone part is outside the
  program's bone domain: no effects, one refusal (`test_native_renderchar.test_armour_owner_effect_program`).

Effects routed vs refused (static, by request kind in the seven programs): sprites `0x7f7a` (15 sites),
`0x8109` (4) and `0x810a` (5) go to the native sprite pool; the particles `0x810a`/7 (4 sites), `0x810a`/15 (4)
and `0x7f26`/0x26 (2) have no native CreateParticle kind and are counted in `owner_refused` (RENDER-EFFECTS
lanes own those kinds).

### Checks

`scripts/validate_item_ownerfx.py --mutations` (manifest row, private test `ItemOwnerFx.test_original_instructions`):
**14,964 comparisons, zero mismatches** (671 s at `121f24f7`):

| Family | Cases | Mismatches |
|---|---:|---:|
| Body streams, 43 types × 292 states, no owner host (the client's effect requests set aside; the C creates none and draws no rand) | 12,556 | 0 |
| Owner: full RenderObjDraw with OBJECT +0x318 owner bones, bone counts from the program's need to 80, random model scale, OBJECT position and angle, scripted rand; directed states with equal bone-19/26 matrices (zero normalize) and integer matrices. Draw stream, every request bit for bit (6,864 sprites, 1,530 particles) and the rand count (7,041) | 2,064 | 0 |
| Refusal: bone counts one or more below the need, and no OBJECT +0x318: the C creates nothing and draws no rand; the draws still equal the client's | 344 | 0 |

All **14/14 separately compiled mutants** are caught (anchors match once): gate modulus 672, gate target 85, range
low bound 1,054, range span 904, normalize zero path 54, normalize scale 375, transform bone 2,064, add 635,
subtract 612, OBJECT angle 551, sprite scale 2,064, particle subtype 1,205, bone domain 172, phase 474. The two
`0x011ff622` clamps cannot change a result for the programs' constant bounds and have no mutant. Both tables
(`item_bodies.h`, `item_owner_fx.h`) reproduce from the pinned instructions.

Compiled C-to-C, main `ad2968fc` library against this one, all 1,691 survey types × 32 random states, with and
without a rand context: **108,224 cases**; 105,472 identical, and the 2,752 different ones are exactly the 43 new
types (refused before). Portable `test_item_ownerfx.py`: 4 tests, one private skip (admission/refusal, the bone
need, `0x19f4`'s sprite, `0x1bc3`'s gate with the OBJECT angle).

### Limits

- 355 bodies remain. The owner programs run only with an owner host (worn parts): inventory and ground items
  draw the bodies and create no effects (the client would create them at BoneTransform positions there).
- Programs refuse states whose OBJECT model or item model lacks the program's highest bone (the client reads
  BoneTransform `0x06fce398` or leaves the position unchanged).
- Effects created in RenderObjDraw before the body helper are not read: `0x0f1e`, `0x174a`, the wings
  `0x23a8`/`0x23a9`, and 76 of the 80 traced bone-sprite (`0x0150e746`) types. They need a pre-draw hook and,
  for bone sprites, an item-bone host (the item's own BoneTransform and named-bone lookups `0x012bd35a`).

## Part 18, pre-draw effect programs on the item's own bones, RENDER-ITEMS-002R

Bounded bodies increase **1,319 to 1,345 of 1,674**, adding **26 types** (`gen_item_owner_fx.PRE_FX_TYPES`): six
swords (`0x0b27`, `0x0b2a`, `0x0b4b`, `0x0b4c`, `0x0b57`, `0x0b59`), three maces (`0x0f1c`, `0x0f1d`, `0x0f2e`), four
bows (`0x1311`, `0x1312`, `0x1316`, `0x131d`), three shields (`0x1748`, `0x1749`, `0x1758`) and ten wings (`0x230b`,
`0x2311`, `0x2382`..`0x2385`, `0x2394`, `0x2395`, `0x2494`, `0x2499`). Skins stay **17/17**, links stay **eighteen
targets/twenty-four types**. **329 bodies remain.**

### Where the effects are created (verified)

A census of the 355 remaining types (four survey states, every draw and effect service with its return site)
places the effect services of 91 types **before** the first draw: RenderObjDraw `0x0176ce74` creates them in its own
type case (`if (OBJECT +0x5c == A || type == B)`), then jumps to the join that calls the body helper. Only 8
types call effect services after their first draw only, 220 call none (or only rand) in these states, and 36
fault (31 in strlen `0x0195a4e0`). The services in those cases:

- **Bone sprites** `0x0150e746(model, bitmap, bone, scale, light, OBJECT, rotation, a7, axes)`:
  TransformPosition `0x012b6ef1(model; BoneTransform 0x06fce398 + 0x30·bone, (0, 0, 0), out, 1)`, then
  CreateSprite `0x01692eb7(bitmap, out, scale, light, OBJECT, rotation, a7, 4, axes)`. The bone is unchecked.
- **Named bones** `0x012bd35a(std::string name, -1)` on the item model: the first bone record (0x8c bytes at
  `+0x2c`, count `+0x22`) with an equal name, else -1. The names are short literals (`aw001`..`aw007`, `a02`,
  `Point001`..`Point008`, `na1`, `zx0001` ...).
- **Plain** TransformPosition `0x012b6ef1` on `BoneTransform + 0x30·bone` (named or constant, also through
  int arrays) followed by CreateSprite/CreateParticle; some particles pass the OBJECT as owner.
- **Values**: the clock `0x06fce370`, the CRT sine `0x009681bd`, the wave `0x0185bdc4(a, 0)`, the comparison abs
  `0x0184f8ff` (`0 > x ? -x : x`), the alpha argument (`[ebp+0x14]`), `(float)(rand() % m)`, `rand() % 2^n` gates,
  vec3 set/scale (`0x009f413c`, `0x00cfcede`, `0x00cfcd74`), float arrays and loops over constant counters.
- **The flag** `[ebp-0xd]`, written at `0x0176cef2` by TestFrustrum2D `0x016ccce7(OBJECT x·0.01, y·0.01, -20)`
  (1 at once in scene states 1..4): many cases test it first; clear, the case is skipped to the next type test.

BoneTransform at that point holds the item's own pose: its Animation precedes RenderObjDraw (RenderLinkItem passes
the weapon's own OBJECT, `CHAR + 0x19d0`, whose `+0x5c` is the item type).

### Reading the cases (generator; static with concrete frames)

`scripts/gen_item_owner_fx.py` gains a pre-draw mode. A Unicorn run with a basic-block trace of RenderObjDraw finds
the case start: the executed block after the last type compare (`cmp [eax+0x5c], imm` / `cmp [ebp+0xc], imm`)
before the first effect service. The case ends at the jump to the join. The abstract interpreter of part 17 then
reads RenderObjDraw's frame (OBJECT `[ebp+8]`, model `[ebp-0xb0]`, alpha `[ebp+0x14]`) and the idioms above;
integer compares and loop counters are decided statically (both operands constant) and unrolled. New ops 15..25
(wave, named bone, bone sprite, visibility, alpha, time, sine, abs, rand value, item transform, owner particle);
registers widen to 16 bits (unrolled wing loops use up to 356). Bone names go to `mu_rc_fx_names`.

Read: 40 of the 91 pre-draw types. Refused (first reason): loops that create joints (CreateJoint `0x0153b02c`) or
use non-constant counters, integer clock chains (`cvttss2si [0x06fce370]` with `idiv`/branches, `0x0b4f`..`0x0b53`),
owner transforms `0x012b678d` on a named bone (`0x0f1e`, `0x174a`, the wings `0x23a8`/`0x23a9`), light-pointer reads
(`[ebp+0x10]`), compares of runtime values, more than 1,024 registers (`0x23ef`, `0x2400`, `0x2405`, `0x24be`,
`0x24bf`), and services both before and after the draws (`0xf23`..`0xf2b`).

### Draws (generator; verified)

The 40 read types' draws were fitted with the effect requests set aside. 29 fit the default probes, but only 5 of them
pass the independent 292-state comparison. With the part-14 supplementary probes (records 0x26/0x5b, qualities 0-2;
`gen_item_bodies.PRE_EXTENDED`, 21 types) and the part-13 carry rule (`PRE_CARRY`, 17 types), 26 pass all 292
states. The rand sites of the pre-draw block itself belong to the effect program and are left out of the body probes.
The bows `0x1313`, `0x1317` and `0x1319` fit no probe option (27-39 states differ).

### Executor and native consumers

- `owner_fx.inc` becomes one executor (`run_fx`) for both kinds of program. `mu_rc_item_draws_owner` runs the
  type's pre-draw program **before** the body when the host has `item_transform` (and the item is in the drawn
  domain: no select, shadow or `a13`). Its rand comes from the host, in client order, before any body random.
- **Item-bone host** (appended `mu_rc_owner_host` fields): `bone_named` (0x012bd35a on the item model),
  `item_transform` (TransformPosition with the item's own pose and BodyScale/BodyOrigin), `refuse`, `visible`
  (the TestFrustrum2D flag). A bone outside `0..item_bones-1` (missing name -1, short skeleton) is not read: the
  request goes to `refuse`, as does every request computed from such a position (a per-register flag).
- `mu_rc_owner_fx` gains `rotation`, `blend` (0x0150e746's arguments 7/8) and `owner` (CreateParticle owned by the
  OBJECT). `mu_rc_item_pre_fx(type)` reports a program.
- Native (`mu_renderchar.c`): with `env->particles`, sprites go to `mu_world_particles_sprite` (with the rotation
  and blend words) and particles to `mu_world_particles_create`. The item pose comes from the new
  `env->item_bones` (the caller's saved pose, as `mu_renderchar_link_effects` takes it); without it every item-bone
  request is refused, while the program still draws its rand. `mu-render character --world-render` passes the
  weapons' and wing's poses and prints `pre_effects`/`pre_refused`. The flag is 1 (viewer choice: a drawn item is
  in view).

Effects routed vs refused (static request sites over the 26 programs, loops unrolled):

| Request | Sites | Native consumer | Result |
|---|---:|---|---|
| Bone sprite `0x0150e746`: `0x7f7a` 74, `0x7ef7` 50, `0x80ba` 14, `0x8458` 6, `0x7fe0` 4, `0x810a` 2 | 150 | sprite pool | routed (refused when the bone is outside the item skeleton) |
| CreateSprite after TransformPosition: `0x7ef7` 62, `0x7f78` 24 | 86 | sprite pool | routed (same bone rule) |
| CreateParticle `0x7ffd`/27, no owner (bow `0x1316`) | 1 | particle pool | routed; counted as refused when the pool creates no record |
| CreateParticle with the OBJECT as owner: `0x810a`/17, `0x81cf`/0 (`0x2384`, `0x2385`) | 4 | none (owner records take attached-object indices) | refused, counted |

### Checks

`scripts/validate_item_predraw.py --mutations` (manifest row, private test `ItemPreDraw.test_original_instructions`):
**9,256 comparisons, zero mismatches** (901 s):

| Family | Cases | Mismatches |
|---|---:|---:|
| Body streams, 26 types × 292 states, no host (the client's effect requests set aside; the C creates none and draws no rand) | 7,592 | 0 |
| Pre-draw: full RenderObjDraw with the real `0x0150e746`, `0x012bd35a`, `0x012b6ef1`; bone records with the program's names among decoys/duplicates (some or all missing, sometimes no records), authored BoneTransform matrices (junk before and past the count), random scale/origin/angle, scripted rand, the frustum away from the OBJECT in 182 states. Draw stream, every request bit for bit (9,956), refusals by kind/bitmap in order (4,532) and the rand count (520) | 1,664 | 0 |

All **14/14 separately compiled mutants** are caught (anchors match once): wave clock 308, bone name 179, flag test
768, alpha 602, sine 341, abs sign 237, rand modulus 117, transform domain 53, transform bone 395, sprite domain 646,
sprite translate 1,098, position refusal 168, particle owner 84, pre-draw hook 1,580. Not mutated, because no program
can tell: the item transforms' translate word (all 49 translate), the bone sprites' rotation and blend (all 90 pass
0), and arithmetic on refused positions (none is computed). Both tables reproduce from the pinned instructions.
`validate_item_ownerfx --mutations` reruns on the shared executor: 14,964 comparisons, zero mismatches, 14/14 mutants.

Compiled C-to-C, main `18ab0134` library against this one, all 1,691 survey types × 32 random states, with and
without a rand context: **108,224 cases**; 106,560 identical, and the 1,664 different ones are exactly the 26 new
types. Portable `test_item_predraw.py`: 5 tests, one private skip (admission, `0x1311`'s sine light at the named bone
and its refusals, `0xb27`'s flag gate with its rand, no host). Native `test_weapon_pre_draw_program`.

### Limits

- The item world (`validate_renderchar.World`) now records CreateEffect `0x013c0f19` like the other effect
  services: wing `0x23ac`'s level-gated case (`0x017c630e`, through `0x013c0e0a`) reached it in a shifted colour
  sample and faulted unstubbed; recorded, its draws equal the C's. The effect itself is not reproduced.
- 329 bodies remain; 51 pre-draw types are not read (joints, integer clock chains with branches, owner transforms
  on a named item bone, light-pointer reads, register budget, services on both sides of the draws) and 14 read types'
  draws do not fit.
- The programs run only with an item-bone host and particle pools. Native world callers outside `mu-render
  character` do not pass the item pose yet: their requests are refused and counted, the rand stream kept.
- The TestFrustrum2D flag is 1 natively. Bones outside the item skeleton are refused (the client reads the matrix
  before BoneTransform or stale bones). OBJECT-owned particles have no native owner record.

## Part 19, the world callers of the pre-draw programs, RENDER-ITEMS-CALLERS-001

Part 18's programs now run in the native world: the hero, other players, player-model actors and ground items pass
the item's own pose, and RenderObjDraw's flag is computed as the client computes it.
[Handoff](../handoffs/RENDER-ITEMS-CALLERS-001.md).

### What RenderObjDraw reads from its callers (verified, `validate_item_callers`)

- **Callers.** The text calls RenderObjDraw `0x0176ce74` from five sites: RenderLinkItem `0x012bd910` at
  `0x012c6a83` (worn weapons, shields, wings); RenderPartObject `0x017e63f4` at `0x017e7960` and `0x017e7997`
  (ground items and body parts); and two sites at `0x00a497c6`/`0x00a49bc9` (labelled the inventory/UI item path here;
  [part 24](#part-24-the-inventorys-equipment-and-its-icons-effects-inventory-fx) corrects it: they are the render callback of object type `0x67a`, and the inventory goes through RenderPartObject).
- **Pose, then pre-draw, then body.** In RenderLinkItem every path from the origin copy to the call passes the
  item's Animation `0x012b5064` at `0x012c6478`, which writes BoneTransform `0x06fce398` (static control-flow
  check). RenderObjDraw then runs the type's case before the body helper (part 18).
- **The OBJECT position.** RenderLinkItem copies the item model's BodyOrigin (`+0x78`) into the link OBJECT
  (`PART + 0x24`) `+0x158` at `0x012c6302..0x012c637b`. RenderPartObject copies the other way, OBJECT `+0x158` → model
  `+0x78`, at `0x017e64dc..0x017e6543`. Both copies dominate their calls. So the OBJECT position RenderObjDraw
  tests is the model origin in both callers.
- **The flag.** `[ebp-0xd]` = TestFrustrum2D `0x016ccce7(x·0.01f, y·0.01f, -20.0f)` at `0x0176ceea`, constants
  `0x01a7df00` and `0x01a7ee00` in single precision. It is 1 in scene states 1..4, else the polygon
  `0x0b6b5400`/`0x0b6b5410` decides (`mu_terrain_test_frustum_2d`).

Families (seed `0x1c411e5`), all compared bit for bit with `native/world/world_item_pre.h`:

| Family | Cases | Mismatches |
|---|---:|---:|
| link_flag: RenderLinkItem's copy, then RenderObjDraw's entry to the flag store (stack probe, SEH frame, TestFrustrum2D), with random convex polygons of both windings, origins inside/around them, on the -20 margin lines (±0.001..1.5) and NaN/±inf/±0/3e38/denormal coordinates, scene states 6 and 5 | 3,000 | 0 |
| part_flag: the same through RenderPartObject's copy | 3,000 | 0 |
| order: the dominance checks above (pose before the call, the copies before the calls, the one switch jump `0x017e6b16` behind the copy) | 8 | 0 |
| callers: the five call sites | 5 | 0 |

6/6 separately compiled mutants of the header are caught: scale 0.02, y from z, range -21, flag negated, scene
state 3 and polygon arrays swapped. Each anchor matches once.

### Native

- `world_rt_item_pre` (world_rt.c) runs for a type with a pre-draw program when the world has particle pools. It
  passes the pose the caller saved right after the item's pose (`item->bones` for slots 6..8, the ground model's
  bones after `pose_item`) and per-caller counters. It also sets `env->item_out_of_view` from `world_item_pre.h` on
  the model origin, using the frame's polygon and scene state 6; with `--legacy-box`, every item is in view.
- `mu_renderchar_env.item_out_of_view` becomes the host's `visible`. That is the only renderchar change; the
  default (0) keeps `mu-render` as it was.
- The world summary gains `item_pre_draw` (pre_effects, pre_refused, hidden per caller) only when a program ran.

In a Lorencia scene with four demo players and three ground drops of the new types, requests go from 0 created /
113 refused to 110 created / 3 refused. The 3 left are wing `0x2384`'s OBJECT-owned particles. The rand count is
unchanged (133). A player outside the polygon has the flag clear and creates nothing.

### Limits

- The hero's item types come from standard file names, and none of the 26 types uses one. The hero path is wired
  but shows no pre-draw effects until its items carry record types.
- The inventory/UI caller is not wired: it has a per-icon pool only for the `0x389c`/`0x389d` skins.
- Owner binding is not needed for sprites: CreateSprite records live one frame (RenderSprites `0x0169270e` modes
  0/2), and the draw `0x01692931` never reads `+0x34c`. OBJECT-owned particles stay refused, with no native
  owner record or kind.

## Part 20, integer registers, runtime branches and joints in pre-draw programs, RENDER-ITEMS-002S

Bounded bodies increase **1,345 to 1,359 of 1,674** (part 19 changed no body), adding **14 types** to `gen_item_owner_fx.PRE_FX_TYPES`: three
swords with integer clock chains (`0x0b4f`, `0x0b50`, `0x0b53`), nine wings (`0x22ec`, `0x230c`, `0x23ef`, `0x2400`,
`0x2405`, `0x248f`, `0x2496`, `0x24cf`, `0x24d6`) and two pet/item bodies (`0x26f8`, `0x26f9`). Skins stay **17/17**,
links stay **eighteen targets/twenty-four types**. **315 bodies remain.** The survey keeps 798 shapes; complete
shapes go 572 to 581, and both TSVs flip exactly the 14 types.

### Screening first (verified)

The part-18 census reproduces on the 329 remaining types: 53 pre-draw types refuse in the interpreter (51 plus
`0x2489`/`0x24a1`, whose case bounds the reader cannot place), 14 read but their draws fit no recipe, 16 call effect
services only after a draw, 31 fault in strlen `0x0195a4e0` and 2 at `0x0095d4f1` (unstubbed CreateEffect in the plain
world). Before extending the reader, each of these 85 types' draws was fitted under the four probe options (default,
part-14 extended, part-13 carry, both) with a one-type scratch library and the 292-state comparison. Only 19 fit.
The reader was then extended for those; 14 of them now read and are admitted. Their probe options
(`gen_item_bodies.PRE_EXTENDED`/`PRE_CARRY`) are the screen's.

### New idioms (static, with concrete frames)

- **Integer words.** `cvttss2si` (the clock and SSE values; integer indefinite outside the range), `cvtsi2ss`
  into `xmm0`/`xmm1`, `cdq; idiv` (remainder and quotient, emitted when read), `xor r, r`, integer
  `add`/`sub`/`imul`/`shl`/`inc`/`dec`, `rand()` as an integer when no gate or value idiom matches it, and
  `movsx r, word [model + 0x22]` (the item model's bone count). `0x0b4f`..`0x0b53`: `(float)((int)time % n) / n`
  times a constant becomes the bone sprites' rotation (period 4000 ms in `0x0b4f`).
- **Runtime branches.** `cmp`/`test` on integer registers and `comiss`/`ucomiss` on floats followed by a forward
  `jcc` become a `cond` op (x86 flag semantics, unordered sets ZF, PF and CF; `lahf; test ah, 0x44; jp/jnp` is its
  own condition). Both paths are read; an if/else's `jmp` over the else-path becomes a `jump` op. A word that differs
  between the joined paths is unreadable until a read needs it; the reading then restarts with that slot joined into
  one register (moves on both paths, the taken path's after a jump). Gates keep their part-17 behaviour, so the 69
  earlier programs read to the same op rows (the header's `--check` reproduced at every step).
- **Services.** CreateJoint `0x0153b02c(bitmap, position, target position, OBJECT +0x164, subtype, OBJECT, scale, -1,
  0, 0, -1, 0, -1, 0)`; CreateSprite with a rotation (argument 6) and blend word; the light argument `[ebp+0x10]`; the
  OBJECT position (+0x158, through `0x00cfc922`); names built as literal + `_itoa(n)` (`0x0198c1d7`, std::string
  append `0x0094b9f7`, `c_str` `0x008e7940`); MSVC's EH vector constructor/destructor iterators (`0x0191b8be`,
  `0x0191b937`); `xmm1` arithmetic; any two-register array index; writes to OBJECT fields (kept as interpreter memory).
- **Registers.** The file grows to 4,096 (`REGISTERS`, `MU_RC_FX_REGISTERS`); `run_fx` clears only the row's
  `regs`. The 14 programs use at most 309 registers. (Part 18 named five types that refused for exceeding 1,024; with
  integer `rand()` and the bone count read, `0x23ef`/`0x2400`/`0x2405` need 273.)

The 14 programs: 2,827 ops. What they use: joints (40 sites), the OBJECT position (12), `idiv` remainders (8),
integer `rand()` (5), `cvttss2si`/`cvtsi2ss` (3 each), integer conditions (2, `rand() % 15 >= 8` in `0x230c`/`0x2496`),
one float condition with its `jump` (`0x0b53`), the bone count (3) and the rotated sprite (2).

### Executor and native consumers

- `owner_fx.inc` ops 26..41 (ftoi, itof, idiv remainder/quotient, integer add/sub/imul, integer rand, cond, jump, bone
  count, light, position, joint, rotated sprite, unsigned remainder). An `idiv` fault (zero divisor, `INT32_MIN / -1`)
  marks its result refused; a branch on a refused value marks every later request refused.
- Appended ABI: `MU_RC_OWNER_JOINT = 3`, `mu_rc_owner_fx.target[3]` (CreateJoint's target position),
  `mu_rc_owner_host.position[3]` (OBJECT +0x158). `validate_item_ownerfx`/`validate_render_effects5`'s ctypes follow;
  the two positional C initializers (`mu_renderchar.c`, `mu_item_textures.c`) gain the zero position.
- Native (`mu_renderchar.c`): joints go to `mu_world_particles_joint` with no target object (-1: the client's target is
  the item's OBJECT, which has no native object index), so the joint takes the target position argument. The pool
  reconstructs `0x7f7c` only for subtype 0x12 and `0x7fd3` only for subtype 0; these programs create `0x7f7c`/0xe and
  `0x7fd3`/4, so natively the requests are routed and counted as refused (`pre_refused`). The OBJECT position is the
  item model's origin (the native item has no OBJECT of its own).

Effects routed vs refused (static request sites over the 14 programs, loops unrolled):

| Request | Sites | Native consumer | Result |
|---|---:|---|---|
| Bone sprite `0x0150e746`: `0x7ef7` 82, `0x8098` 44, `0x81ec` 32, `0x8180` 6, `0x8078` 5, `0x8149` 1 | 170 | sprite pool | routed (refused outside the item skeleton) |
| CreateSprite: `0x7f78` 24, `0x7fdd` 20, `0x7ef7` 16 (+2 rotated), `0x7f26` 4 | 66 | sprite pool | routed (same bone rule) |
| CreateParticle, no owner: `0x7f66`/5 4, `0x8180`/5 3 | 7 | particle pool | routed; refused when the pool creates none |
| CreateJoint `0x7f7c`/0xe 20, `0x7fd3`/4 20 (wings `0x22ec`, `0x248f`), the OBJECT as target object | 40 | joint pool, no target index | routed; the pool does not reconstruct these kinds, counted as refused |

### Checks

`scripts/validate_item_predraw.py --mutations` (the part-18 row; the 14 types join both families):
**14,240 comparisons, zero mismatches** (758 s):

| Family | Cases | Mismatches |
|---|---:|---:|
| Body streams, 40 types × 292 states, no host | 11,680 | 0 |
| Pre-draw: as part 18, plus CreateJoint recorded with all fourteen arguments and a random OBJECT position. Requests bit for bit (19,241 sprites, 269 particles, 2,196 joints), refusals by kind/bitmap in order (10,725), rand count (1,011), 280 flag-clear states | 2,560 | 0 |

All **25/25 separately compiled mutants** are caught (anchors match once); the eleven new ones: integer rand 76, idiv
remainder 172, cvttss2si (rounding instead of truncation) 53, cvtsi2ss 110, integer condition 6, bone count 30, OBJECT
position 117, joint target 115, joint subtype 115, joint scale 115, sprite rotation 109. Not mutated, because no
program can tell: the float condition and the join `jump` (their only use, `0x0b53`'s triangle wave, computes a value
no request reads: the body draws read it), and the `idiv` fault path (divisors are constants or a bone count >= 1 in
every state). `validate_item_ownerfx --mutations` reruns on the shared executor (below). Both tables reproduce.

Compiled C-to-C, main `53cffd00` library against this one, all 1,691 survey types × 32 random states, with and
without a rand context: **108,224 cases**; 107,328 identical, and the 896 different ones are exactly the 14 new types.
Portable `test_item_predraw.py`: 10 tests, one private skip (rand() % bone count, the joint loop's paired targets, the
integer clock's period and truncation, the `rand() % 15 >= 8` branch, the OBJECT position). Native
`test_wing_joint_and_random_bone_programs`.

### Limits

- 315 bodies remain. Not admitted: `0x0f1f`, `0x0f20`, `0x0f2a` fit the draws but call the random colour helper
  `0x00d01fc6` (about 160 instructions, three `0x011ff622` ranges and sines) and index arrays by `rand() % 3`; the
  frame-counter gate (`[0x0bdc5ebc] % 3`, unsigned) also needs a host field. `0x130d` and `0x2713` fit but create their
  effects after the draws. `0x23a8`/`0x23a9`, `0x0f1e`, `0x174a`, `0x2301`/`0x2302`, `0x23f0`/`0x23f2`, `0x0b51`/`0x0b52`
  read or nearly read but their draws fit no probe option.
- Joints: the target object (the item's OBJECT) has no native index, and the joint pool does not reconstruct
  `0x7f7c`/0xe or `0x7fd3`/4 yet (RENDER-JOINTS lanes). The OBJECT position natively is the model origin.
- OBJECT fields that a case writes (`0x0f1f`'s owner transforms into +0x1f4) are interpreter memory only; no admitted
  program writes one.
- The world callers of part 19 (hero, players, player-model actors, ground items) run these programs too; the OBJECT
  position is the model origin (for ground items, the OBJECT position).

## Part 21, the hero's part slots from its equipment, HERO-ITEMS-001

Part 19 ran the pre-draw programs for the hero as for the players, but the hero's item types were inferred from
standard file names (`mu_renderchar_type_from_path`, `SwordNN.bmd`). The client types the hero from its
equipment. [Handoff](../handoffs/HERO-ITEMS-001.md).

### SetCharacterClass `0x01394870` (verified, `validate_hero_items`)

The hero's equipped ITEM records live in CharacterMachine `[0x01d1df18]` at `+0x1b58 + s · 0x12c` (s: 0 right
hand, 1 left hand, 2..6 helm, armour, pants, gloves, boots, 7 wing, 8 helper). The players' ChangeCharacterExt
`0x0137b68c` decodes 18 viewport bytes into the CHARACTER part slots `c + 0x1c4 + k · 0x3fc` (`+0` type word,
`+2` level, `+3` option, `+4` ext). `0x01394870(c)` fills the same slots from those ITEMs:

- Only for a Player-model character (`c + 0x32b0 == 0xa91`).
- Weapons: slot 6/7 ← s 0/1. Type = code + `0xae6` (only code −1 is empty: −2 gives `0xae4`), level =
  `(level word >> 3) & 15` (arithmetic shift), option = `0x00cd0995(item, 1)`, ext = ITEM `+0x3b`.
- Wing slot 8 ← s 7 and helper slot 10 ← s 8: type and level only. Their option and ext bytes keep their values.
  Slot 9 (muun) is not written.
- Parts: slots 1..5 ← s 2..6. An empty slot takes the class part `0x3700 + 0x50 · (k − 1) + skin` (`0x0139d6a2`),
  which is the part the native character loads (`mu_character_part_type`, all 256 class bytes). A worn part is
  typed like the weapons, with level, option and ext.
- Head (`0x01394f6f`, unless `c + 0xe`): the class head `0x3700 + skin` for 17 helm types (`0x18e6`, `0x18e8`,
  `0x18f0`..`0x18f3`, `0x1925`, `0x1927`, `0x192a`, `0x192c`, `0x193d`..`0x193f`, `0x19a0`, `0x19a1`, `0x1a35`,
  `0x1a5f`) that leave it visible; otherwise −1. The rest of `0x01394f6f` writes scales (`+0x32f4`, `+0x288`).
- `0x00cd0995(item, mode)`: 0 for a code outside `0..0x2c00`. Mode 0: `+0x3b & 0x33`; mode 1: `+0x98 == 1`;
  mode 2: `+0x92 == 1`; other modes 0.
- Not reproduced (stubbed in the comparison): `0x009dadf1` (the weapon override of the worlds `0x009dacb8`
  lists), the hero-only `0x0137ad93` and the stat machine's `0x00a00fb7`. A flag `[ebp-1]` from `0x009dacb8` and
  `c + 0x327e` is computed and never read.

| Family (seed `0x4e20`) | Cases | Mismatches |
|---|---:|---:|
| set_class: random equipment (codes −1, in range, out of range, negative), random level words, random `+0x3b`/`+0x92`/`+0x98` and other ITEM bytes, random class bytes, prior slot bytes, `c + 0xe`, models (10 % not `0xa91`) and worlds; all 11 slots' five bytes | 3,000 | 0 |
| defaults: every class byte, empty equipment | 256 | 0 |
| head: every helm type `0x18d0..0x1a6f`, `c + 0xe` 0 and 1 | 832 | 0 |
| item_flag: `0x00cd0995` directly, modes −1..3 and random, codes around the bounds | 3,000 | 0 |

14/14 mutants caught (level shift and mask, model base, the empty test, the flag bound/mode/`+0x98` test, wing
ext, part stride, the head list and flag, the model gate, the helper slot, swapped hands).

### Native

`world_rt_hero_item_textures` (every hero `set_item` passes through it) keeps each worn file's Item.bmd record
and `world_rt_hero_slots` runs `mu_he_set_character_class` on them. The hero part draws a slot that has a record
with the slot's type, level, option and ext and Item.bmd's kind bytes, as the players do, and the players' glow
colour. A slot without a record (class parts, files outside Item.bmd, no Item.bmd) keeps the file-name inference.
The offline session's records are the front end's files (the demo characters list `item=FILE`, no codes, levels
or options), so the record is the file's first Item.bmd record and level/option/ext are 0.

Record vs file-name guess over Item.bmd: 774 distinct standard-named files. For 424 of them the file's first
record differs from the guess (Item.bmd maps models many-to-one). The 26 pre-draw types all use non-standard
names. The five demo characters' seven items all equal the guess.

| Hero | Before (file name) | After (record) | Seen |
|---|---|---|---|
| Demo characters (Staff02, Sword04, Shield01, Wing02, Bow02, Sword05, Mace01) | same type | same type, kinds from the record | `mu-shell` 85/85 frames identical |
| Combat stand-ins (Sword01, Sword10, Spear01, Bow01, Staff01) | same type | same | 7 scenes identical |
| Combat crossbow `CrossBow01.bmd` | −1 | `0x12ee` Crossbow | identical at level 0 |
| `--hero-item` blade01, CR_shield01, InnocenceCape (test only) | −1 | `0x0b4b`, `0x1748`, `0x2382` | 0 → 30 pre-draw sprites; the cloak's own mesh is no longer drawn, as for a player wearing `0x2382` |

## Part 22, frame counter, OBJECT-bone positions, random vectors and post programs, RENDER-ITEMS-002T

Bounded bodies increase **1,359 to 1,363 of 1,674** (+4): two maces with pre-draw programs (`0x0f1f`, `0x0f20`,
`gen_item_owner_fx.PRE_FX_TYPES`, draws with the part-13 carry rule) and two owner blocks after the draws (bow
`0x130d` and `0x2713`, the new `POST_FX_TYPES`, default draws). Skins stay **17/17**, links stay **eighteen
targets/twenty-four types**. **311 bodies remain.** The survey keeps 798 shapes; complete shapes go 581 to 585, and both TSVs flip exactly the four types.

The third mace, `0x0f2a`, now reads (part of the idioms below come from it) but is not admitted: its body draws an atlas
mesh (`0x8615`) at u = (f % 4)·0.25, v = (f / 4)·0.25 with f = ([0x0bdc5ebc] % 32) / 2 (`0x0176b676`), the rendered-frame
counter, which the body probes always hold at 0, so its fitted recipe is right only at frame 0 (found by the pre-draw
family, which now randomises the counter).

### Screen (verified)

002S named the three maces "draws fit with carry"; a one-type library over the 292 survey states confirms it (0
differing states each, carry only; the part-14 supplementary probes do not fit). The 292 states hold the frame counter
at 0, which hides `0x0f2a`'s atlas (above). `0x130d` and `0x2713` fit the
default probes once their effect requests are set aside (0 differing states).

### New idioms (static, with concrete frames)

- **The random spherical vector `0x00d01fc6`** (out, r max, r min, θ max, θ min, φ max, φ min; not a colour helper):
  r min is clamped at 0; r = r min when r min ≥ r max, else `0x011ff622(r min, r max, 50)`; below the radius floor
  `[0x01a80990]` (1e-6) the vector is zero and the result 0 (`fldz`); θ and φ are clamped (min ≤ max, ≥ 0, θ ≤ 180,
  φ ≤ 360), scaled by `[0x01a7fd6c]` (π/180) and drawn by `0x011ff622(…, 100)`; out = (sin θ·r·cos φ, sin θ·r·sin φ,
  cos θ·r) with the CRT sine `0x009681bd` and cosine `0x009fa223`; the radius is returned on x87. All three maces pass
  constants (r 20..25, θ 0..180, φ 0..360, or 12..15 radius in `0x0f2a`). Op 44 reconstructs the helper; the reader
  checks its four constants in the data capture.
- **`0x012b678d(out, OBJECT, bone, NULL)` on item bones** (op 43): the client leaves `out` unchanged when the bone is
  outside 0..model +0x22 (the C refuses what is computed from it); the matrix is the OBJECT's own bone array (+0x318,
  through `0x0129f12c`, when the OBJECT's model has the bone) or BoneTransform `0x06fce398`; with a NULL local point
  the result is the matrix's translation column times the model scale (+0x74) plus the OBJECT position (+0x158).
  `0x0f1f` writes three such positions into OBJECT +0x1f4..+0x218 and never reads them (interpreter memory only).
- **The rendered-frame counter `[0x0bdc5ebc]`** (op 42), tested unsigned (`xor edx, edx; div`, op 41) against 3 or 5
  before particles (`0x0f1f`, `0x0f20` inside a counted loop, `0x0f2a`).
- **Bounded array selects** (op 45): `rand() % 3` (and loop counters) index frame arrays of named bones or values. The
  reader tracks integer ranges (rand() 0..0x7fff, remainders by a positive constant, scaled and shifted bounds);
  every word the index can reach is copied into consecutive registers and the op picks one at run time.
- **CreateParticle with a computed bitmap and argument 8** (ops 46/47): `0x8315 + rand() % 3` in `0x0f2a`; `0x0f1f`'s
  OBJECT-owned particle passes `rand() % 3` as argument 8. Appended ABI: `mu_rc_owner_fx.extra`.
- **Post programs** (`POST_FX_TYPES`): blocks after the draws in RenderPartObjectBody's case (`0x016e036c`) read with
  the pre-draw idioms in that function's frame (model `[ebp+8]`, OBJECT `[ebp+0xc]`), run where the part-17 owner
  programs run. `0x130d`: `0x0129f12c(OBJECT, 4)` then TransformPosition `0x012b6ef1` on that matrix with the item
  model's scale/origin (op 49), and CreateSprite with bitmap `0x8081 + rand() % 3` (op 48: the next request's bitmap
  from a register). `0x2713`: TransformPosition on item bones 8, 10, 11, a clock sine written into the OBJECT light
  (+0xec, interpreter memory) and read back as the three sprites' light. `mu_rc_item_post_fx()` names them; the owner
  gate checks only the OBJECT's bone count for them (`0x0129f12c` compares with the OBJECT's model, not the item's).

Appended host ABI: `object_transform`, `frame`, `frame_known`, `owner_item_transform`. Natively (`mu_renderchar.c`)
`object_transform` uses the item's own pose (the native item has no OBJECT bone array), the env's new optional
`frame_counter` (NULL by default: callers are unchanged, so requests behind a counter test are refused and counted),
`owner_item_transform` only with an OBJECT owner (worn parts). A particle with a non-zero argument 8 is refused
(`mu_world_particles_create` has none).

### The hidden-mesh domain of wings 0x2382..0x2385 (verified)

APP-POLISH-007 found that with OBJECT +0x68 = 1 or 2 the library drew nothing for wings `0x2382`..`0x2385` while the
client draws them. The library refused any hidden value other than -1, 0 and the type's own (`MU_RC_UNSUPPORTED`).
These wings draw only explicit meshes (RenderMesh `0x00966e4a`), so +0x68 changes nothing in their streams: compared
with the client at +0x68 = 1, 2, 3, 7, 0x7fffffff (60 states each) and in validate_item_predraw's new hidden family,
they are equal; the exemption now includes them (as `0x2322`..`0x2327`).

### Checks

`scripts/validate_item_predraw.py --mutations` (the part-18 row; the four types join, `0x130d`/`0x2713` as post
programs): **16,832 comparisons, zero mismatches** (173 s):

| Family | Cases | Mismatches |
|---|---:|---:|
| Body streams, 44 types × 292 states, no host | 12,848 | 0 |
| Hidden: wings `0x2382`..`0x2385` × 292 states, OBJECT +0x68 = 1, 2, 3, 7 | 1,168 | 0 |
| Pre-draw/post: as part 20, plus a random rendered-frame counter in every state and the OBJECT's own bone array in some (always for `0x130d`, with more than four bones). Requests bit for bit (20,240 sprites, 370 particles, 2,222 joints), refusals by kind/bitmap in order (11,539), rand count (1,488), 308 flag-clear states | 2,816 | 0 |

All **39/39 separately compiled mutants** are caught (anchors once); the fourteen new ones: frame counter 76, object
transform domain 25 and bone 33, random-vector radius steps 25, floor 48, cosine 24 and θ 28, select 1, register
bitmap 23, argument 8 13, bitmap op 64, OBJECT-bone translate 64, post-host arming 128, hidden-mesh wings 292. Not
mutated: the unknown-counter refusal (a C refusal with the client's kind/bitmap passes by design; the portable
`test_frame_counter_gate` covers it), op 49's bone guard (unreachable behind the owner gate), the post gate's
item-bone exemption (equal counts in this world) and the random vector's clamps (constant arguments inside them).
`validate_item_ownerfx --mutations`: 14,964 comparisons, 0 mismatches, 14/14 (129 s). Both tables reproduce.

Compiled C-to-C, main `ae5e6f36` library against this one, all 1,691 survey types × 32 random states (OBJECT hidden
-1/0/1/2) with and without a rand context: **108,224 cases**; 107,898 identical; the 326 different ones are the four
new types and the four wings' hidden-1/2 states.

### Limits

- 311 bodies remain. `0x0f2a` (frame-counter atlas) is not admitted; the body recipes have no frame-counter input and
  the other item validators hold the counter at 0 (only this row's 44 types are checked with a moving counter).
- Natively no frame counter is known by default (`mu_renderchar_env.frame_counter` NULL): requests behind a counter
  test are refused and counted. `0x012b678d` uses the item's own pose and the model origin.
- `0x130d` runs only with an OBJECT owner. The world callers pass the item pose only for pre-draw types, so `0x2713`'s
  post program runs pose-less there (requests refused); the viewer tool opens its pool for post types.
- Joints unchanged (`0x7f7c`/0xe, `0x7fd3`/4 refused, 0/40 drawn).

<a id="part-22-object-owned-item-particles-render-effects-020"></a>

### OBJECT-owned item particles, RENDER-EFFECTS-020

Part 22 continues with the OBJECT-owned particle requests.

The last requests the item programs refused: the CreateParticle calls of the wings `0x2384`/`0x2385` (Cloak of
Brilliance and its [Bound] variant, `SparkleCape.bmd`) that pass the item's OBJECT as owner (part 18's op 25).
[Handoff](../handoffs/RENDER-EFFECTS-020.md).

#### Census (static, and the library over 83 types × states)

Over the 83 program types (43 owner programs of part 17, 40 pre-draw programs of parts 18/20; 3,245 ops), the
OBJECT is passed as an owner by:

| Request | Sites | Native before | Native after |
|---|---:|---|---|
| CreateParticle `0x810a`/0x11 with the OBJECT as owner (`0x2384`, `0x2385`; `rand() % 3` gate under the frustum flag) | 1 op row shared by both types | refused, counted | created, owner = the item OBJECT's slot |
| CreateParticle `0x81cf`/0 with the OBJECT as owner (same types; `rand() % 7` gate) | 1 op row shared | refused, counted | created, same owner |
| CreateSprite / bone sprite with the OBJECT as sprite owner | 275 | routed | unchanged (sprites live one frame; the draw never reads `+0x34c`, part 19) |
| CreateJoint with the OBJECT as target (`0x22ec`, `0x248f`) | 20 | routed, target −1 | unchanged (kinds `0x7f7c`/0xe, `0x7fd3`/4 belong to the joint lane) |

No other op passes the OBJECT to CreateParticle, and types without a program create nothing. Running the
library on all 83 types with random skeleton names, rand streams and the frustum flag (scratch tool, 32 states
per type): `0x2384` makes 3 `0x81cf`/0 and 2 `0x810a`/0x11 requests, `0x2385` 5 and 1 (1,000 states: 129/291 and
131/292). The other particle requests of the programs are not OBJECT-owned and stay refused for want of a kind:
`0x7ffd`/0x1b (bow `0x1316`), `0x7f66`/5 (`0x230c`, `0x2496`) and `0x8180`/5 (`0x23ef`, `0x2400`, `0x2405`).

#### The two kinds (verified, `validate_render_effects20`)

| Kind | CreateParticle `0x015ae7b0` | MoveParticles `0x01616c80` | RenderParticles `0x0159123f` |
|---|---|---|---|
| `0x810a`/0x11 (pin_star03) | `0x015b25a3`: initial LifeTime (+0x4c) 30, LifeTime = it; Scale = `0x011ff622(0.5, 1, 100)` × the argument, kept at +0x1c; alpha 1; rotation `0x011ff622(0, 360, 1)`; position += `0x011ff622(−10, 10, 1)` per axis; velocity = `0x011ff622(−15, 15, 1)` × 0.2 per axis | `0x0161b6ba`: Scale −= initial Scale / initial LifeTime; alpha −= 1 / initial LifeTime (after the common MovePosition along the request's angle) | `0x0159faca`: the record's light × alpha |
| `0x81cf`/0 (Effect\magic_ground12, subtype 1 shares the case) | `0x0160baa3`: LifeTime 20, initial LifeTime = it, initial Scale = the argument, Scale 0, alpha 1 (no rand) | `0x0168418b`: owner word +0x50 NULL → live 0; else Scale += initial Scale / initial LifeTime; below half the initial LifeTime (`cdq; sub; sar`, toward zero) alpha −= 1 / half | `0x015a5eec`: light × alpha |

What the particles read of their OBJECT owner: only `+0x158`, in the common blocks (create `0x015aeb5e..0x015aebd6`,
move `0x01616fee..0x01617071`): the record's `+0x54` becomes the owner's x, y with z = RequestTerrainHeight
`0x016cc9e2`. A Unicorn read hook over the owner OBJECT records exactly bytes `+0x158..+0x163` for both kinds'
create and move (400 cases); the angle `+0x164`, the bones `+0x318`, the scale and the live/visible bytes are never
read. Neither kind reads `+0x54` afterwards, and the position does not follow the owner. Both retire by LifeTime
at MoveParticles' loop head (20 and 30 steps); `0x81cf`/0 also ends at the first step whose owner word is NULL.
The client's owner is a pointer into the character array (RenderLinkItem's link OBJECT `PART + 0x24`) or the
ground-item array, so it is never NULL while a wearer or drop exists.

The angle argument both pass is the OBJECT's `+0x164` (op 12). For worn items, RenderLinkItem `0x012bd910` stores
0.0 into the link OBJECT's `+0x164` at eleven sites before the RenderObjDraw call `0x012c6a83` (the only other
store is type `0x44f`'s z = WorldTime) and reaches `+0x164` only through the accessors `0x00cfc922`/`0x00cfc94a`
(static, `link_angle`). For ground items the OBJECT is the drop itself, whose angle is the drop's.
`0x81cf` is registered at startup (`0x018249a3` in `0x0182049e`: `Effect\magic_ground12.JPG`, GL_LINEAR, GL_CLAMP).

#### Native

- `reconstructed/particles/item_owned_kinds.inc` (new): the two kinds, behind one include and the
  supported/create/move/render hooks of `particles.c`.
- `mu_world_particles` gains 256 item-owner slots (`mu_world_particles_item_owner`, `_refresh`): an owner index is
  `0x40000000 + (generation << 8) + slot`; `fx_object` resolves it to a live, visible object at the slot's
  `+0x158`. The world callers (`world_rt_item_pre`) key the item OBJECT by caller and identity (hero slot,
  player/actor index × 16 + slot, ground pool index) and refresh its position (the model origin, as part 19) every
  draw. A slot unrefreshed for 64 steps (longer than either kind lives) may be reused with generation + 1; the old
  index then resolves to no object. A wearer that leaves keeps its last position, as the client's slot memory does.
- `mu_renderchar.c` routes op 25 to `mu_world_particles_create_owned` with that index; without a key (the offline
  `mu-render character`) or with every slot held the request stays refused and counted.
- `mu_renderchar_env.item_angle` carries the OBJECT's `+0x164` into the pre-draw host: 0 for RenderLinkItem's
  callers, the drop's angle for ground items (`mu_world_item_draw.angle`, `.index`).
- The world particle bitmaps gain `0x81cf` (77 slots).

Scenes (native renders, `mu-walk` soft 320×240 Lorencia 128,124 unless said; refused counts are the requests the
programs could not create):

| Scene | Before (main `f2370871`) | After |
|---|---|---|
| CALLERS-001 crowd, 60 frames, players / ground pre_effects / refused | 92 / 2, 18 / 1 | 93 / 0, 18 / 0 (rand 133 → 141: the created `0x810a`/0x11 draws eight) |
| Same, a frame every 10 | 322 / 5, 108 / 3 | 325 / 0, 113 / 0 |
| Hero `--hero-item wing=Item/SparkleCape.bmd` (`0x2384`), every 10 | 70 / 3 | 74 / 0 |
| GL `mu-world` 640×400 crowd, 41 frames, every 5 | 414 / 9, 144 / 4 | 417 / 5, 146 / 0 (the 5 left are bow `0x1316`'s `0x7ffd`/0x1b, not OBJECT-owned) |

#### Limits

- A slot reused after its hold resolves to no object; the client would read the reused memory. No item-owned
  particle lives long enough to see it.
- `mu-render character` has no item OBJECT registry: its OBJECT-owned requests stay refused.
- The link OBJECT's `+0x164` before RenderLinkItem's first store, and stores outside RenderLinkItem, were not traced;
  all stores found write 0.
- Player-model actors are wired like players, but no installed actor wears `0x2384`/`0x2385`.
- Ground items now pass their angle to every pre-draw program that reads op 12 (`0x1316`, `0x22ec`, `0x230c`,
  `0x23ef`, `0x2400`, `0x2405`, `0x248f`, `0x2496` and the two cloaks); none of them is dropped in the scenes above.

## Part 23, pre-draw particles without an owner and armour owner programs in the world, RENDER-EFFECTS-021

RenderObjDraw's pre-draw programs (part 18/19) still had three particle requests without an owner that no native
pool reconstructed. The armour owner programs (part 17) ran only in `mu-render character`. Both are now served in
the world. Evidence: verified (Unicorn against the pinned text/data), unless said.

### Census of item-program requests (static, every op of the 83 programs)

| Request (op) | Programs | Native consumer before | After |
|---|---|---|---|
| CreateParticle `0x7ffd`/0x1b, no owner (14) | bow `0x1316` | none: refused, counted | `item_predraw_kinds.inc` |
| CreateParticle `0x7f66`/5, no owner (14) | `0x230c`, `0x2496` | none: refused | `item_predraw_kinds.inc` |
| CreateParticle `0x8180`/5, no owner (14) | `0x23ef`, `0x2400`, `0x2405` | none: refused | `item_predraw_kinds.inc` |
| CreateParticle `0x810a`/0x11, `0x81cf`/0, OBJECT owner (25) | `0x2384`, `0x2385` | part 22 | unchanged |
| CreateSprite / bone sprites (13, 17, 40) | 275 sites | sprite pool | unchanged |
| CreateJoint, OBJECT target (39): `0x7f7c`/0xe, `0x7fd3`/4 | `0x22ec`, `0x248f` | joint pool: refused | unchanged (RENDER-ITEMS-002T's joint kinds) |
| Owner programs' `0x7f26`/0x26, `0x810a`/7, `0x810a`/0xf and sprites (10, 13, 14) | 43 armour/helm types | kinds exist (RENDER-EFFECTS-017); programs not run in the world | run in the world with the wearer's OBJECT |
| Since #341 (part 22 of 002T): `0x810a`/0x25 OBJECT-owned with argument 8 (47); `0x855d`/1, `0x84d1`/1 (14) | maces `0x0f1f`, `0x0f20` | none; refused first by the missing frame counter `[0x0bdc5ebc]` | unchanged (next step) |

### The three kinds (CreateParticle `0x015ae7b0`, MoveParticles `0x01616c80`, RenderParticles `0x0159123f`)

| Kind | Create | Move | Render |
|---|---|---|---|
| Clud64 `0x7ffd`/0x1b | `0x015c304a` (the subtype chain from `0x015c07c8`): initial LifeTime (+0x4c) 15, LifeTime 15; rotation `rand() % 360`; light = the argument again; alpha 1; velocity `0x011ff622(-0.5, 0.5, 1)` per axis: one rand each, always 0 | `0x0163274d`: alpha = LifeTime / initial LifeTime (binary32 division); Scale += 0.04 | `0x0159504f`: the sprite with light × alpha (`0x00cfcb3c`) |
| Shiny01 `0x7f66`/5 | the Shiny01 case `0x015e5c73` (LifeTime 18, angle x 45), then `0x015e60e5`: LifeTime `rand() % 10 + 10`; Scale = `(rand() % 10) · 0.02 + scale`; x and y += `rand() % 10 - 5`; gravity = `-(rand() % 10) · 0.3` | the case `0x016584c2` has no head; `0x01658bd3`: rotation += 10; z += gravity; light /= 1.02 per channel; Scale -= 0.01 | Shiny01 is not in the render switch: the default sprite `0x015ae2bf` |
| shiny06 `0x8180`/5 | the case's table `0x016167a0`[5] = `0x015e93ab`, the switch end: the common block only (LifeTime 2) | table `0x0168f700`[5] = `0x0165c194`, the end: nothing | table `0x015ae50f`[5] = `0x0159a5a6`, the end: the common bind and blend state, no sprite |

Index 5 is the only entry of each table that goes straight to the end; the other subtypes of `0x8180` have blocks.
`0x8180`/5 lives two MoveParticles steps and draws nothing. Native skips even its bind, because shiny06 has no
world bitmap slot. In the client the bind and blend state are reset by the next record's render.

### Owner programs in the world

RenderPartObjectBody `0x0173d2d8` runs the effect block of a worn chest/helm with the character OBJECT. The block
transforms through `0x012b678d(out, OBJECT, bone, local)`, a thiscall on the part model. If the bone is negative
or not below the part model's bone count (`+0x22`), `out` is not written. Otherwise the matrix is OBJECT
`+0x318 + 0x30·bone` (`0x0129f12c`, provided the OBJECT's model, found through `+0x5c`, `0x00966cc4` and
`0x00eaa8cf`, has the bone and `+0x318` is set), else BoneTransform `0x06fce398 + 0x30·bone`. The result is
VectorTransform `0x00d002b2` of the local point, × the part model's `+0x74`, + OBJECT `+0x158`. The particles take
OBJECT `+0x164`.

The native characters (players, the hero, player-model actors) hold the same values:
- `player_bones` is the posed Player.bmd skeleton (`mu_character_update`);
- the part model's body scale and origin are the character's scale and position (`mu_character` `slot_params`);
- `params.angles` is the OBJECT angle.

`world_rt_part_owner` builds the `mu_renderchar_owner` from them, for body-part types with an owner program
(`mu_rc_item_owner_fx`), and the three world callers draw those parts with `mu_renderchar_draw_item_owner`. The
existing owner host (RENDER-ITEMS-002Q) runs a program only when its highest bone is below both bone counts; it
refuses where the client would fall back to BoneTransform or skip the write. Counts:
`{"item_owner_fx": true, "hero"|"players"|"actors": {owner_effects, owner_refused}}`, printed only when a part
ran a program.

None of the 43 types is a rank-5 type, so RENDER-EFFECTS-005's rank-5 owner block (bones 35/26 and the level-9
overlay passes) stays as before: it runs in `mu-render character` only.

### Scenes (offline native renders, Lorencia 128,124)

Refused = requests the programs could not create.

| Scene | Before (`ca941c4b`, #339 head) | After |
|---|---|---|
| CALLERS-001 crowd, `mu-walk` soft, 60 frames: players / ground | 93 / 0, 18 / 0 | identical |
| Same, a frame every 10 | 325 / 0, 113 / 0 | identical |
| GL `mu-world` 640×400 crowd, 41 frames, every 5 | players 417 / **5** (bow `0x1316`), ground 146 / 0 | 423 / **0**, 148 / 0 (created 5 → 13, rand 167 → 239) |
| Archer alone (bow `0x1316`), GL, every frame, 61 frames | 854 / **17** | 876 / **0** |
| Five wearers of `0x230c`, `0x2496`, `0x23ef`, `0x2400`, `0x2405`, soft every 10 / GL every 5 | 483 / **10**, 621 / **12** | 487 / **0**, 634 / **0** |
| Shipped Lorencia demo players (after #338), soft every 10 / GL every 5 | 343 / 0 (23 hidden), 441 / 0 (28 hidden) | identical (no such type, no owner-program armour) |
| Five armour wearers (`0x1bc3`, `0x1bc4`, `0x1bde`, `0x1c41`, `0x1c78`), soft every 10 | no program ran, 0 sprites | players 144 owner effects (119 sprites, 25 particles) / **0** refused |
| Same, GL every 5 | no program ran | 190 (153 sprites, 37 particles) / **0** |
| Hero `--hero-item armor=Item/ArmorMale135.bmd` (`0x1bc3`), soft every 10 | no program ran | hero 68 / **0** |

The created counts shift slightly because each new record draws rand() (Clud64 4, Shiny01 5), which moves later
gates.

### Limits

- The native pose is assumed to equal the client's `+0x318`, as RENDER-EFFECTS-005 already assumed for the
  rank-5 bones and the world's link effects for `0x389c`/`0x389d`. This lane verifies the transform and the
  bone-domain rule, not the pose.
- The five helm types run through the same hook, but no scene wears them. Player-model actors are wired, but no
  installed actor wears these armours.
- The rank-5 owner block in the world is left for a later lane (it also adds draw passes).
- The joint kinds `0x7f7c`/0xe and `0x7fd3`/4 stay refused (RENDER-ITEMS-002T).

## Part 24, the inventory's equipment and its icons' effects, INVENTORY-FX

The inventory window draws the hero's equipment and every icon's level, option and ext the way it draws them for
a worn item. The icons' pre-draw programs and skin sprites go to the world's sprite list, never over the icon.
[Handoff](../handoffs/INVENTORY-FX.md).

### The inventory frame's item render (verified, `validate_inventory_fx`)

- **Equipment slots.** The movie reports each slot through `EQUIPrequestSlotInfo(x, y, w, h, slot)`. The handler
  `0x00b97834` needs five arguments, the first a number; it truncates the fifth to the slot (`_ftol` `0x0191c5e0`).
  `0x00b958e1` stores slots 0..14 at controller `+0x110 + s·8` (x, y) and `+0x188 + s·8` (w, h) and ignores others.
- **The render** `0x00b913a2` (the frame's vtable `+0x20` item render) runs the grid's slot pass `0x00ab6130`.
  When that returns 1 and a CharacterMachine `[0x01d1df18]` exists, it walks s = 0..14 over the ITEMs
  `+0x1b58 + s·0x12c` with code `+0x10` ≥ 0 and calls the slot wrapper `0x016c23d5`(item, x, y, w, h, 0,
  frame `+0xcc` == 1 (`0x00abed32`), 0, 0, frame, 0, 0.0f, -1, 0, 1, 0):
  - x = (frame x `0x00aae509` + scale `0x00abedc3` · slot x) · rate x `0x00966d99`, and y the same way;
  - w = rate x · slot w · scale, h = rate y · slot h' · scale;
  - slot h' = slot h · 0.75 (`0x01a800cc`) for the armour slot 3 when the hero's class nibble
    (`[0x0a39d754] + 0x12`, `0x0095f5cc`) is 2, 5, 7, 8, 9, 12 or 14 (`0x00b99205`).
  - The loop sets no colour.
- **What the icon's RenderObjDraw gets.** RenderItem3D → RenderObjectScreen (part of NATIVE-FIDELITY-001) →
  RenderPartObject, which passes RenderObjectScreen's level word, excellent flag and set bits through unchanged
  as RenderObjDraw's arguments 5..7 (`0x017e7932..0x017e7960`, `0x017e796a..0x017e7997`). The item render
  then uses the level `(word >> 3) & 15`, the option and the ext byte, as for a worn item.
- **The flag.** RenderObjDraw's TestFrustrum2D flag is taken at OBJECT `+0x158`, which for an icon is its screen
  position (window pixels, z −100/−130/−140). RenderPartObject copies it to the model origin (part 19).
  - Screen position / 100 is the map's corner tiles (0..25, 0..14). The world polygon almost never reaches them,
    so the flag is clear.
  - Gated programs then skip their case: Cookery Short Sword `0x0b2a`, Floor Hammer `0x0f1c`, Floor Shield
    `0x1748`, the cloaks.
  - Ungated ones still create: Xeno Blade `0x0b4c`, the wings `0x230b`/`0x2311`.
- **Where the sprites go (static).** RenderObjDraw's programs and its `0x389c`/`0x389d` skin case (`0x0176ffe3`,
  CreateSprite at `0x017701f9`) append to the global sprite list. RenderSprites `0x0169270e`, the only routine
  that draws it, has four call sites, all in the scene renders `0x018576b3`, `0x01857ed9` and `0x0185916b`. Only
  the frame driver `0x01851d39` calls those (and `0x010b3963` for the main game). So the icon's sprites are drawn by
  the world's sprite pass with the world camera, at the icon's screen coordinates read as world units. That spot
  lies under the map's corner and out of the hero's view.
- **Not the inventory.** The other two RenderObjDraw call sites, `0x00a497c6`/`0x00a49bc9`, lie in `0x00a49266`.
  `0x00a16273` registers that function at `0x00a13f54` as the render callback of object type `0x67a`. It draws a
  character's parts and weapons (CHARACTER `+0x1c4 + k·0x3fc`) on another object's pose. Parts 19 and 21 had
  called it the inventory/UI path.

| Family | Cases | Mismatches |
|---|---:|---:|
| equip_pass: `0x00b913a2` with its slot pass (no grid pages), frame/scale/rate getters, the class rule and `0x0095f5cc` executed, against `mu_inventory_item_pass`: return value and every wrapper call (16 words, floats bit for bit). Screens 640×480..2560×1440, alignments 0..9, scales, slot rectangles (also zero), codes (−1, 0, random, `0x7fffffff`), all class bytes, frame `+0xcc` −1/0/1/2/`0x101`, no CharacterMachine, invisible frames | 3,000 | 0 |
| equip_info: `0x00b958e1` after 1..5 random calls (slots −3..18, int32 extremes) against `mu_equip_slot_info`: the 60 stored words and which calls stored | 1,000 | 0 |
| part_args: RenderPartObject's two call sequences: arguments 5..7 against `mu_icon_glow_of` (level, option, ext) | 1,000 | 0 |
| inv_flag: RenderPartObject's copy and RenderObjDraw's flag at icon positions against `world_item_pre.h`, world polygons around the map and near its origin, scene states 6/5 | 3,000 | 0 |
| sinks: the call chain, RenderSprites' four sites and their callers, the `0x67a` callback | 17 | 0 |

14/14 mutants of `reconstructed/hud/item_slots.c` are caught: rate swap, multiply order, armour slot, factor,
class set, class nibble, a20, empty test, null CharacterMachine, slot bound, size swap, glow shift, glow mask and
option/ext swap. Each anchor matches once.

### Native

- `reconstructed/hud`: `mu_equip_slot_info`, `mu_inventory_item_pass`, `mu_equip_short_armour` and
  `mu_icon_glow_of`.
- `native/gfx/mu_gfx_layer`:
  - keeps the reported rectangles and the hero's 15 ITEMs (`mu_gfx_layer_set_equipment`: code, level word,
    excellent, set bits, class byte);
  - runs `mu_inventory_item_pass` for the inventory and appends the equipment draws after the grid's.
  - Slots the movie never reported are left out (the client would draw them at the frame origin, size 0).
  - The equipment's cursor test uses the slot rectangle in stage points.
- `native/world/world_rt.c`: SetCharacterClass's ITEMs 0..8 (the session records of APP-POLISH-008, or a file's
  first record at level 0) go to the layer. Slots 9..14 have no offline record.
- `native/world/world_gfx_game.c`:
  - The glow comes from `mu_icon_glow_of(ros)`, so the excellent pass and the set bits now reach grid and
    equipment icons. Kind A `0xc` passes level 0.
  - With a world (`wg_items_set_world`), the pre-draw programs run on the icon's pose with the flag of
    `world_rt_item_pre` (new caller `inventory`, owner key per icon), and the skin sprites are created in the
    world's list.
  - The per-icon skin pool of RENDER-ITEMS-002D (an inference) is gone: no sprite is drawn over an icon.
- The world summary's `item_pre_draw` line gains `inventory` only when an icon ran a program. The GFx summary gains
  `inventory_equipment` only when equipment is drawn.

### Limits

- Character select is unchanged. Its slot levels would come from the character list handler's equipment
  decoding (packet data, not traced), and the native charsel draws plain meshes without the item render.
- RenderObjDraw's level word reaches the native item render as `(word >> 3) & 15`. Its option and luck bits
  (`& 0x87`) are dropped, as for the world's players.
- `mu-render ui inventory` (the software tool) still draws `0x389c`/`0x389d` sprites over its icons.
- Sprites created during the item pass are drawn by the next world draw. The client's order of the GFx pass and
  RenderSprites within one main-game frame was not traced (the GFx manager is reached through a virtual call).
- No original-client capture of an inventory with equipment: the placement is matched up to the wrapper's
  arguments, and the pixels are the native renderer's.

## Part 25, the wings' physics capes, RENDER-ITEMS-CLOAK

HERO-ITEMS-001 found that the RenderObjDraw body of the cloak wings `0x2382`..`0x2385`, `0x2394` and `0x2395` (part 18)
never draws their cape mesh, and APP-POLISH-007 showed the inventory draws only the upper meshes. The world does not
draw that mesh either: **the cape is a physics cloth** that RenderCharacter owns per character. The installed
models agree: `InnocenceCape.bmd`'s mesh 0 (25 vertices, `kundun_innocence2.tga`) and `SparkleCape.bmd`'s mesh 1
(`kundun_sparkle3.tga`) are the meshes RenderObjDraw leaves out, and their textures are the cloth bitmaps below.

### Call path (verified unless marked)

| Step | Address | What it does |
|---|---|---|
| RenderCharacter `0x01363260` cloth flag | `0x01366edf..0x01367530` | `[ebp-0x4d]` = 1 for an OBJECT of type `0xa91` whose class skin (`0x0139cab9`) is 3, 0x33 or 0x43 or whose base class is 0, 4, 6, 7, 8, 9, 0xb, 0xc, 0xd or 0xf, when CHARACTER `+0x0e` is 0 (or 1 with `+0x32b0` = `0xa91`); else for wings `0x23f1`, `0x2401`, `0x24c6`; also for class indices (`+0x146`) `0x37`, `0x169`, `0x3a9`, `0x3ab..0x3ad`; cleared for the glow classes `0x0139bcdc` (`0x211..0x21b`, `0x349..0x34c`, `0x371..0x373`, `0x3c1`, `0x3d5`) and the worlds of `0x009dacb8` (`0x12..0x17`, `0x35`, `0x61`). Light `[ebp-0xc8]` = (1, 1, 1), (1, 0.1, 0.1) when CHARACTER `+0x1f` = 6. The guild-war flags `0x06fca13d`/`0x06fca13f`, the duel manager `0x01d1e028` and the hiding buff `0x009c104e(c, 2, 1)` also write it (not ported) |
| MoveCloth `0x01362f24` | call `0x0136ab80`, every frame | for each cloth of OBJECT `+0x4c` (count `+0x3f`) with an owner: `Move2(0.005, 5)` (`0x00fd821e`); speed 0 under buffs `0x3d`, `0x48`, `0xb2`, `0x118`; a failed step deletes the cloths (`0x0137aafe`) |
| RenderCloth `0x01363098` | call `0x0136aba2`, behind the flag; after the body parts (`0x0136a374`), before the linked items (`0x0136c33f`..) | CreateCloth `0x01357ccc` while OBJECT `+0x4c` is 0, the armour cloths `0x0135ea29` / `0x01362755`, MoveCloth again when one was made, then the draw tests `0x01362e1d` (buff `0x12`, sub-type `0x431`/`0x432`, actions `+0x2a`/`+0x2c` both `0xe4`) and `0x01362e87` (class / sub-type `0x009a0989`, class index `0x271`/`0x272`) and virtual slot 8 (Render) of each cloth with `(light, 0)` |
| CreateCloth `0x01357ccc` | switch on CHARACTER `+0x21a4` (arg 4 = 0) | `0x2382`/`0x2383` (`0x0135b558`): one cloth, bone 19, origin (0, 16, −10), 10×10, 140×130, bitmap `0x83f6`, type `0x1005`, spheres (∓10, −2, 18, r 25) and (∓10, 0, 0, r 28) on bone 17. `0x2384`/`0x2385` (`0x0135b79f`): two cloths, origins (∓3, 20, −5), 160×150, bitmaps `0x83f7` / `0x83f8`, uv scale (0.5, 1), uv offset (0, 0) / (1, 0), push (∓0.1, ∓0.1), two spheres each. `0x2394`/`0x2395` (`0x0135c419`): as `0x2382` with origin (0, 20, −10) and bitmap `0x846b` |
| Bitmaps | `0x018252db`, `0x018252fb`, `0x0182531b`, `0x01827699` | `0x83f6` `Item\texture\kundun_innocence2.tga` (GL_REPEAT), `0x83f7` `kundun_sparkle3.tga`, `0x83f8` `kundun_sparkle3_1.tga` (GL_CLAMP), `0x846b` `BlackCloak_3.tga` (GL_REPEAT), all GL_LINEAR |
| Wind | frame driver `0x01851d39` (`0x01851eee..0x01851f07`) | five calls of the physics manager's step `0x00fdad7b` per logic step: wind `0x01ec981c` += (rand() % 200 − 100) × 0.001, clamped to [−0.2, 1] |

### The cloth (CPhysicsCloth, vtable `0x01ab2780`, 0xe8 bytes; vertices 0x3c bytes, vtable `0x01ab2758`)

- **Create** (slot 2, `0x00fd6e60`): a rows × columns grid; row y is tapered to (0.6 + 0.4y/(rows−1)) of the width for
  type `& 0xc` = 4 and dropped by 10·(2|x/(cols−1) − 0.5|)² for type `& 3` = 1, placed with AngleMatrix(OBJECT angles)
  and the owner bone's translation through TransformPosition `0x012b6ef1`. Springs: vertical (flags 2|4), horizontal
  (3), both diagonals (1; the second only from row 2), rest length = the distance, minimum 0.8 of it. The top row is
  fixed by SetFixed (slot 4, `0x00fd79bb`): the origin plus a 0.6-wide row, swizzled (z, −y, x) and transformed by the
  bone matrix every step.
- **Step** (`0x00fd825f`): the wind (the global, or rand() for types `0x200`/`0x8`/world `0x37`), the wind vector
  `0x01ec9820` = (sin a·w, −w·cos a) with a = (180 + OBJECT angle z)·π/180; forces (slot 7, `0x00fd8463`): per vertex
  w·windvector − 0.01·velocity with w = 0, 3..6 by the grid distance from a point that moves with the logic-step
  counter `0x0bdc5eb0` (5 − d is compared unsigned with 4, so vertices farther than 5 take 6), a rotated sideways push, gravity
  9.8·0.0025·100 (`0x01cf0eb0`, `0x01cf0eb4`); force springs beyond rest + 0.01; the top row; velocity +=
  force·400·t (`0x01cf0eb8`), position += velocity·t. Constraints (`0x00fd88ec`): sphere centres on their bones,
  sphere pushes, the constrain springs (half the error each end), the averaged displacements, and the stretch limits
  (vertical springs below the top row: back into [0.8, 1]·rest; beyond 20× rest the pass stops unless `0x00aae6f9`
  holds). The step's result is always 1 with an owner.
- **Render** (slot 8, `0x00fd8bc2`): EnableAlphaTest(1) for type `0x1000`, `glColor4f(light, OBJECT alpha)`, then
  GL_QUADS of the grid with the front bitmap and again, wound the other way, with the back bitmap; u = x/(cols−1)/uv
  scale − uv offset, v the same clamped to 0.99.

### Port

`reconstructed/cloth` (`mu_cloth_wing_create`, `mu_cloth_move2`, `mu_cloth_render`, `mu_cloth_wind_step`,
`mu_cloth_gate`) and `native/world/world_cloak.c`: per wearer (hero, players by index) the cloths live with the
OBJECT (dropped when the wing or the viewport generation changes and at travel). Every rendered frame
`world_cloak_frame` (after the logic steps) runs the wind walk and MoveCloth for every wearer drawn since its OBJECT
was made; the hero and player parts call `world_cloak_draw` between the body parts and the linked items (first-frame
MoveCloth, the flag, CreateCloth + MoveCloth, Render through the backend: quads as two triangles, the four bitmaps in
the cloak's own texture set). The cloths step every frame whether or not the frame is drawn, so a headless capture
cadence does not change them.

### Checks

`scripts/validate_item_cloak.py` (row `validate_item_cloak`): **2,090 comparisons, 0 mismatches** — create 66
(CreateCloth on the six types ×3 and four wings without a case; failure states without bones, with too few bones or
without the model), step 528 and render 528 (8 frames each of MoveCloth then RenderCloth as RenderCharacter calls
them: every cloth field, the wind vector, rand(); the GL stream bit for bit), wind 200, gate 768 (RenderCharacter
run to `0x0136ab87`). **38/38 compiled mutants caught**, none equivalent, every anchor once. The gravity constants
come from the pinned third section (`effects_init`).

### Limits

- The flag follows the client: a Dark Knight, Elf, Magic Gladiator (tiers 2/3), Summoner or classes 0xa/0xe
  wearing these wings gets no cape (only the upper meshes), as in the original.
- Not ported: the guild-war / duel / hiding-buff writes of the flag, the other CreateCloth cases (other wings, arg 4),
  the armour cloths, the glow and mesh passes, sub-types `0x5bc`/`0x5bd`. Native players have no buffs and sub-type 0.
- The wind starts at 0 when the first cloth wing is drawn and walks with its own MSVC rand() state; the client's
  shares the process rand() and has walked since start-up.
- (inference) The Player model's BodyScale/BodyOrigin at MoveCloth are the OBJECT's scale and position (RenderCharacter
  poses the Player before it); the native host passes the character's position and scale.
- The 0.01 floor of the sphere collision (a vertex within 0.01 of a centre) is in the port but no random state
  reaches it.
- GL_QUADS are drawn as triangles (0, 1, 2), (0, 2, 3).

## Part 26, the rendered-frame counter in body draws, the wing joints and the world callers, RENDER-ITEMS-002U

Bodies **1,363 → 1,364 of 1,674**. The rendered-frame counter `[0x0bdc5ebc]` is now a body input, and a
comparison of the client's streams at different counter values found that **51 admitted bodies** draw texture
coordinates from it: their recipes were right only at counter 0 (every earlier probe and validator held it there).
They are regenerated with counter chains; `0x0f2a` (002T's unadmitted mace) joins with its atlas frame. The joint
kinds of the wing programs are reconstructed ([client-joints.md section 12](client-joints.md#12-the-wing-streaks-0x7f7c0xe-and-0x7fd34-render-items-002u)),
so 40/40 routed CreateJoint calls draw. A native rendered-frame counter feeds the world callers.

### Where the client increments the counter (verified by the existing frame-driver check)

The frame driver `0x01851d39` (client-frame-loop.md): the due 40 ms logic steps, the clear, GetTickCount
(`0x018524f2`), then `++[0x0bdc5ebc]` (`0x01852501..0x01852507`), then the scene render. During any item draw of a
frame the counter therefore holds that frame's number, one more than in the previous frame. Of the 225 references in
the text only `0x01852507` writes it (static scan).

### Which bodies read it (verified, client against client)

Every survey type (1,691) in four states, client RenderObjDraw with the counter at 0 against 7, 13 and 22: 58 types'
streams differ; 51 were admitted bodies. The reads sit in their RenderPartObjectBody cases (`0x0172dd0c` ..
`0x01737116`, 36 sites) and in RenderObjDraw for the maces `0x0f24`..`0x0f2c` (`0x01769c75` .. `0x0176c12a`). All
of them set a mesh's u or v. Six idioms:

- `((counter + 1) % 60)` (`inc; xor edx, edx; push 0x3c; pop ecx; div ecx`), converted as unsigned to binary64
  (`cvtsi2sd` of the word, `shr r, 31`, `addsd [r*8 + 0x01bd3050]` with the table {0, 2^32}), to binary32, times a
  constant (often 1/60), sometimes negated after a vec3 setter call (`0x00cfcead`): swords `0x0b66`..`0x0b73`,
  bows, staffs `0x1560`.., shields `0x1739`..;
- the same with the divisor a binary32 constant truncated (`cvttss2si ecx, [local]`, `0x132b`) and the scale
  `1.0 / that constant` folded;
- `(counter + 1)` unsigned, `/ 1.0`, truncated, `% 16`, then `% 4` and `/ 4` (signed idioms) × 0.25: a 4 × 4 atlas
  (`0x1109`, ten operations);
- `0x0f2a`: f = (counter % 32) / 2 (unsigned, the divisor `2 << 4` from a local), u = (f % 4)·0.25, v = (f / 4)·0.25.

### Generator and library

`gen_item_bodies.py`: kind-3 chains gain `C_FRAME` (the counter into the integer register), `C_U_MOD`/`C_U_DIV`
(`xor edx, edx; div`) and `C_U2D` (the unsigned conversion); `CLOCK_OPS` 9 → 12. Blocks are sliced in counter mode
when their bytes contain the counter's address and the type is in `FRAME_TYPES`; only then do the new idioms apply
(`push k; pop r`, `xor r, r` before `div`, the fix-up table, binary64 temporaries of counter chains, binary32 constant
folding, the vec3 setters `0x00cfcead`/`0x00cfcede` walked over), so every other type's blocks slice as before. Their
probes vary the counter (boundaries and random words per seed); other types keep the zero page, so their samples and
cache keys are unchanged. `renderchar.c`: ops 30..33 in `clock_program`, which now takes the counter;
`mu_rc_item.frame` (appended) carries it; `mu_renderchar.c` fills it from `mu_renderchar_env.frame_counter` (0 when
unknown, the previous behaviour). `validate_renderchar` writes `case['frame']` to the client and the C.

Fitting: with the counter varied, all 51 earlier bodies and `0x0f2a` fit (`0x0f2f` and `0x158a` need nine scalar
programs, so `MU_RC_BODY_SCALARS` is 12; `0x1109`'s chain has ten operations, so `CLOCK_OPS` is 12). The table grows
1,344 → 1,345 rows (`0x0f2a`); at counter 0 every earlier row draws what it drew before (C-to-C below). The other six
counter types (`0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`, `0x0f2c` with effect programs in RenderObjDraw, and
`0x1588`) still fit no probe option.

### Native

- `mu_world_rt.rendered_frames`, incremented once per rendered frame in `mu_world_rt_frame` right after the due logic
  steps and before the frame parts and the draws (the client's position). It counts from the world runtime's start;
  the client's counts from process start, including the login and character-select frames, so the absolute phase
  differs and only the periods (2, 3, 5, 16, 32, 60 frames) are faithful.
- `world_rt_item_pre` sets `env->frame_counter` for every item it is called for (worn weapons, shields and wings of
  the hero, players and player-model actors, ground items), before its pre/post test; its condition now also
  accepts the post-draw types (`|| mu_rc_item_post_fx(type)`), so `0x2713`'s post program gets the item pose in the
  world, and since INVENTORY-FX (#343) also the world's inventory window, whose items go through the same function
  (the client draws them with the live counter too). `mu-render ui inventory` and the texture survey keep it unknown
  (0): their frames are unchanged.
- With the counter present, the requests behind `0x0f1f`'s/`0x0f20`'s counter tests run on the client's frames
  (`counter % 3 == 0`, `% 5 == 0`) instead of all being refused; the particle kinds they create (`0x855d`/1,
  `0x84d1`/1, `0x810a`/0x25 with argument 8) are not in the native pool, so what runs is still refused, now for the
  kind. `mu-render character --frame-counter N` sets the counter for the viewer (N at the first frame, +1 per frame).
- The wing joints (`0x22ec`, `0x248f`): 40/40 routed CreateJoint calls are created and drawn (client-joints.md
  section 12). #339's combined particle refusal rule (an OBJECT-owned particle without an owner key, any request with
  argument 8) does not apply to joints; they keep no target object (-1), which draws the client's quads because
  neither kind reads its target.

### Checks

`scripts/validate_item_predraw.py --mutations` (the part-18 row; new family `frame`): **32,372 comparisons, zero
mismatches** (286 s, both tables reproduce):

| Family | Cases | Mismatches |
|---|---:|---:|
| Body streams, 45 types × 292 states, counter 0 | 13,140 | 0 |
| Hidden: wings `0x2382`..`0x2385` × 292 states | 1,168 | 0 |
| Frame: the 52 counter types × 292 states, each with a counter (16 boundaries 0..0xffffffff, then random; 6,408 distinct values) | 15,184 | 0 |
| Pre-draw/post: 45 programs × 64 states, random counter, the C body reading the same counter (`0x0f2a`'s atlas) | 2,880 | 0 |

**44/44 separately compiled mutants** are caught (anchors once); the five new ones: counter source 14,645, unsigned
remainder 14,259, unsigned quotient 1,010, unsigned conversion 1 (only `0x1109` converts an unreduced counter, and
only counters ≥ 2^31 tell), the item's counter 14,690.

`scripts/validate_joints.py --cases 3000 --mutations`: 9,000 cases, 0 mismatches; 38/38 compiled mutants (16 new on
the wing kinds) and the 9 negative controls (228 s).

Compiled C-to-C, main `138b756e`'s library against this one (main did not change `reconstructed/renderchar` after the
base), all 1,691 survey types × 32 states (OBJECT hidden -1/0/1/2) × with/without a rand context × counter 0 and one
non-zero counter: **216,448 cases**; 215,576 identical. At counter 0 only `0x0f2a` differs (admitted); with a counter
exactly the 52 counter types differ.

The table now writes only the used op/k slots of each scalar row (C zero-fills the rest): with `CLOCK_OPS` 12 the
fully written rows exceeded the audit's 512 KiB limit; compact, `item_bodies.h` is 486,681 bytes (main: 521,715), and
the compiled library is identical over the same 216,448 cases. `validate_item_scalars`/`validate_item_chains` parse
two-digit op counts now; their case counts grow by the counter programs (26,154 → 26,274, 35,346 → 35,406), all
mutants caught. The affected rows ran without mutants on the final code (handoff).

Counter scan (client against client, scratch): 1,691 types × 4 states × counters 7/13/22, then × 12 states × counters
1/0x80000000: 58 counter types in the union, none outside `FRAME_TYPES` plus the six not admitted.

### Limits

- 310 bodies remain. The six counter types not admitted (`0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`, `0x0f2c`, `0x1588`)
  fit no probe option yet; the maces also create effects in RenderObjDraw that are not read.
- The native counter's phase is not the client's (it starts with the world runtime). `mu-render ui inventory`, the
  texture survey and `mu-render character` without `--frame-counter` keep 0, so their counter bodies show frame 0.
- The counter scan covers the survey's unselected/no-buff domain with 16 states per type; a counter read only in
  another branch would not be found.
- `0x0f1f`/`0x0f20`'s counter-gated particles are now refused for their kinds (not in the native pool), not for the
  counter.

### Next groups

1. The six counter types not admitted: read the maces' RenderObjDraw effect programs (`0x0f24`, `0x0f28`, `0x0f29`,
   `0x0f2b`, `0x0f2c`; their counter tests now have an input) and find `0x1588`'s probe option.
2. Part 20's group 3, untouched here: draw fits for programs that already read (`0x23a8`/`0x23a9`, `0x0f1e`,
   `0x174a`, `0x2301`/`0x2302`, `0x23f0`/`0x23f2`, `0x0b51`/`0x0b52`, the bows `0x1313`/`0x1317`/`0x1319`, part 18's
   eleven).
3. The 31 rank-5 parts faulting in strlen `0x0195a4e0` (rank-5 pose world) and the 54 helper-group-count types.
4. Native particle kinds behind the maces' counter tests (`0x855d`/1, `0x84d1`/1, `0x810a`/0x25 with argument 8):
   RENDER-EFFECTS lanes.

## Part 27, every CreateCloth case and the glow pass, CLOAK-002

Part 25 ported six of CreateCloth's cases. This part ports the rest of the routine, the glow pass of Render, the
angle-matrix Create variant, the sub-type tests, and records what the armour cloths and the wind would need. Evidence is
verified (Unicorn against the pinned text and data) unless marked static.

### CreateCloth `0x01357ccc` (verified)

- **Entry.** It returns 0 without a CHARACTER or OBJECT, or when OBJECT `+0x4c` already holds cloths. With **arg 4 ≠ 0**
  (`0x01357d1d`) it makes one cloth whatever the wing (even none): Create(bone 19, (0, 10, 0), 10×10, 75×120,
  front `0x790b` `Player\Robe01.jpg`, back `0x790c` `Robe02.jpg`, type `0x405`), with no spheres. RenderCharacter sets
  arg 4 only in the guild-war and duel branches (part 25), so native characters never reach it.
- **The switch** on CHARACTER `+0x21a4` (`0x01357e5c..0x0135810d`, byte table `0x0135ea14` for `0x2393..0x23a7`) has
  34 case bodies for 54 wing types (20 aliases). Each body writes the count to OBJECT `+0x3f`, allocates the cloths (`0xe8` bytes
  each), calls Create (slot 2) and then the setters: uv scale `0x013bb4a2`, uv offset `0x013bb477`, push `0x013bb44c`,
  SetGlow `0x00fd9f50` (bitmap, pulse speed, minimum, maximum → `+0xa0..+0xac`) and AddCollisionSphere `0x00fd9ded`.
  `reconstructed/cloth` keeps 31 bodies (three of them part 25's) as a table of their immediates (`cloth_defs`). Four have their own code:
  - `0x23ec`/`0x23fd`/`0x2402` (`0x01358112`): three cloths (`0x7916` `deathha.tga`; two 2×5 strips `0x7917`
    `deathjung.tga` of types `0x9000`/`0x11000`). Every value is multiplied by s = OBJECT `+0xa0` / 0.9, or / 1.2
    when SceneFlag `0x01d1df70` (read through `0x009b0bc1`) is 5 (character select).
  - `0x23f1`/`0x2401` (`0x0135897e` → `0x013a0242`): `0x7918` `admangto.tga`, type `0x1405`, one sphere.
  - `0x24c6` (`0x01358a40`): two cloths through the **angle-matrix variant** (slot 1, `0x00fd77dc`) on bone 47 at
    (32, −24, ±32), angles (0, 90, 0), bitmaps `0x830c` / `0x830d` `season_wing_periodc(2).tga`.
- **Level glows.** `0x2396`/`0x2397` call SetGlow when CHARACTER `+0x21a6` (signed byte) is ≥ 9; `0x239e`, `0x23a0`,
  `0x23a1`, `0x23a5` and `0x23a7` when it is ≥ 11. Twelve other cases always glow.
- **Cloth counts.** Three cloths: `0x230e`, `0x2318`, `0x23ec`, `0x2488`, `0x239e`. Two: `0x2384`, `0x2386`, `0x23a5`,
  `0x24c6`. One for every other case. The new types used by the cases are `0x400` (gravity 180), `0x8000`/`0x10000`
  (sideways wind forces) and `0x1` (the dropped top row). The physics core of part 25 already ported them; the step
  family now compares them.
- **Bitmaps.** Every cloth and glow bitmap comes from LoadBitmap `0x0185baac` calls with its filter and wrap. The
  table is in `native/world/world_cloak.c` (59 entries; `Player\` for the robes, else `Item\Texture\`).
- **Types beyond the item range.** `0x34e6`..`0x34eb` are model indices above `0xae6 + 16·512`. No player wing record
  reaches them; they are compared in Unicorn only.

| Case (aliases) | Body | Cloths, bitmaps, type |
|---|---|---|
| `0x230e` (`0x2498`) | `0x01359174` | 3: `0x7914` dl_redwings02 10×10 `0x1405`; two 2×5 `0x7915` `0x1000` |
| `0x2317` (`0x2492`), `0x236d` | `0x01359d7b`, `0x01359b20` | 1: `0x80ed` NCcape `0x1405` |
| `0x2318` (`0x249a`) | `0x01359fd6` | 3: `0x80ef` monke_manto; `0x80ee` monk_manto01 2×5 `0x9000` / `0x11000` |
| `0x2368`, `0x2490` (`0x2504`) | `0x01358cbe`, `0x01358f19` | 1: `0x7912` DarklordRobe `0x1005` |
| `0x2380`, `0x2381` | `0x0135b092`, `0x0135b2d9` | 1: `0x83f3` kundun_purewhite2; `0x2381` glows `0x83f5` |
| `0x2386` (`0x2387`) | `0x0135bb53` | 2 halves: `0x83fa` / `0x83fb` kundun_resplendent_6/5, glows `0x842d` / `0x842e` |
| `0x2392`, `0x2393` | `0x0135bf81`, `0x0135c1c8` | 1: `0x8469` Ironcloak2 |
| `0x2396` (`0x2397`), `0x2398` (`0x2399`) | `0x0135c66f`, `0x0135c913` | 1: Desperatecloak3 / Hatredcloak_3, glows `0x846d` (+9) / `0x846f` |
| `0x239e` | `0x0135cba6` | 3: Fifth_DarkLord_cape_04/05/03, glows `0x8503`/`0x8504`/`0x8502` (+11) |
| `0x23a0`, `0x23a1`, `0x23a7` | `0x0135d220`, `0x0135d515`, `0x0135dce7` | 1: Fifth_Rage_Cape_02, Fifth_Grow_cape_04, Fifth_Illusion_cape_03 (glows +11) |
| `0x23a5` | `0x0135d89f` | 2 halves: Fifth_Kundun_cape_03/04, glows `0x84ef`/`0x84ee` (+11) |
| `0x23f3` (`0x2493`), `0x23fc`, `0x23f4` (`0x249b`) | `0x0135a930`, `0x0135a6d5`, `0x0135ab8b` | 1: Item801_2_wing / Item802_2_wing `0x1405` |
| `0x2488` (`0x24a0`) | `0x013595db` | 3: darklordwing4de + two 2×5 darklordwing4dd, all glowing |
| `0x248a` (`0x24a2`), `0x248b` (`0x24a3`) | `0x0135a43d`, `0x0135ade6` | 1: ragefighterwing4db / growlancerwing4dc, glowing |
| `0x34e6`, `0x34e7` (`0x34e8`), `0x34e9` (`0x34ea`), `0x34eb` | `0x0135e071..0x0135e773` | 1: blessing / hope / sanctuary / light_cape_02 |

### The angle-matrix variant and the sub-types (verified)

- Slot 1 `0x00fd77dc` calls Create (slot 2). On success it writes AngleMatrix(angles) to `+0x48` and sets `+0x44`.
  Create itself fixes the top row once through the normal SetFixed.
- SetFixed (slot 4, `0x00fd79bb`) defers to slot 5 `0x00fd7d2a` when `+0x44` is set. Slot 5 builds each top-row
  point as slot 4 does: x·step − width/2, y 10, the `0x10` offset and the parabola. It then rotates the point by the
  cloth's own matrix and swizzles it (z, −y, x). TransformPosition places it on the bone. The origin, swizzled the
  same way, goes through RotatePosition `0x012b7019` (the bone's rotation times BodyScale) and is added. RotatePosition
  also copies the bone matrix to `0x078965ac`, which the cloth does not read.
- Both SetFixed slots take the model from OBJECT `+0x60` when that sub-type is `0x5bc` or `0x5bd`, else from OBJECT
  `+0x5c`; Create always uses `+0x5c`.
- RenderCloth's draw tests read the same sub-type. `0x01362e1d` hides the cloths for buff `0x12`, for the sub-types
  `0x431`/`0x432`, and when actions `+0x2a` and `+0x2c` are both `0xe4`. `0x01362e87` hides them when `0x009a0989`
  holds (a class of skin 3 under the sub-types `0x3e9`, `0x3ed`, `0x429`, `0x541`, `0x552`, `0x5ba..0x5bf`, `0x5c4`,
  `0x5c5`, `0xa5e`) and for the class indices `0x271`/`0x272`. Native characters keep sub-type 0 and no buffs.

### Render's glow pass (verified)

Render `0x00fd8bc2` order:

1. the state wrapper;
2. `glColor4f(light, alpha)`;
3. (type `0x40000000`: the flare sprites `0x7ef7` through `0x01692eb7`; no wing case uses it);
4. the front face and the back face;
5. the glow pass `0x00fd9663`;
6. the mesh passes `0x00fd9c61`/`0x00fd97de` when `+0xc0` ≠ −1. No wing case sets `+0xc0`; only the armour cloths do.

The glow pass runs when `+0xa0` ≠ −1. It calls EnableAlphaBlend `0x0184aa2b` (additive) and BindTexture(glow). The
brightness is b = 1, or with speed > 0, b = wave·(max − min) + min, where wave = `0x0185bdc4(−speed, 0)` (the cosine
of WorldTime folded into 2000π/speed ms, mapped to [0, 1]; the same wave as `mu_hp_wave`). It calls
`glColor4f(b, b, b, alpha)`, then one GL_QUADS stream wound as the front face through RenderVertex (same uv). So a
glowing cloth draws three quad streams: front, back, glow. `mu_cloth_render` now draws the glow and still refuses
`0x40000000` and a mesh.

### The armour cloths (static; not ported)

- RenderCloth calls CreateClothArmour `0x0135ea29` and, when that makes nothing, `0x01362755` every frame. Both fill
  the second list, OBJECT `+0x48` (count `+0x3e`).
- MoveCloth steps both lists. The armour list renders with white light behind `0x01362edc` (class 4 under the
  sub-types of `0x009a088a` hides it).
- `0x0135ea29` runs only when OBJECT `+0x3b` is 1. CreateCharacter sets that at `0x0137dbd7`, so every character has
  it. It switches on the base class (`0x0095f5cc`: class & 0xf) 0, 3, 4, 8, 9, 0xc and 0xf. It then tests the body-part
  type at CHARACTER `+0x9bc` (`0x3754`, `0x3760`, `0x3774`, `0x3784`, `0x3794`, `0x37a9..0x37e9`, `0x37d3`, `0x37e3`:
  class part skins).
- Its cloths use what this lane does not port:
  - types `0xc0000205`/`0x80002105` (the `0x40000000` flare sprites);
  - the mesh setter `0x00fd7986` (`+0xc0..+0xc8`, its two mesh passes);
  - the second glow `0x00fd9f97` (`+0xb0..`);
  - `0x013bb3fd` and `0x013bb4cd`;
  - the angle-matrix variant on bone 3;
  - a re-create path (`0x01360d33`) that releases (slot 3) and rebuilds the cloths when the body part changes.
- Its bitmaps include `0x7911` `Monster\iui06.jpg`, `0x83ef..0x83f2` `Item1141_Wing1/2`, `Item1146_1/2`, the
  `HQskin`/`SkinClass` cloak skins `0x791d..0x795d` and `0x7ef7` `Effect\flare01.jpg`.
- `0x01362755` is bounded: the class indices (`+0x146`) `0x37` (one cloth `0x790d`, three spheres), `0x169`
  (`0x7ff2`, 6×6 type `0x1008`, the curved grid) and `0x3a9`/`0x3ab..0x3ad` (two halves `0x84e6`/`0x84e7`). Those
  are NPC and monster characters that native renders outside RenderCharacter's path, so a port has no native caller
  yet.

### Wind (static)

- The frame driver `0x01851d39` calls the physics manager's step `0x00fdad7b` five times in every logic step
  (`0x01851ee8..0x01851f07`), after the scene switch. So the walk runs in every scene from the first logic step.
- `rand()` `0x01989721` keeps its state in the per-thread data (`0x019a4ba6` → `+0x18`). `srand` `0x01989742` has 19
  call sites; WinMain's seeds it with `time` (`docs/research/client-ground-items.md`). The wind therefore depends on
  the start-up time and on every `rand()` call of every scene since then. No native stream can reproduce it.
- The native stand-in now walks from the frame driver's logic step 0 (`a->walk.frame.clock.logic_steps`). It no
  longer starts from the first cloth draw: the wind at a frame depends only on the steps since the runtime started, as
  the client's depends on the steps since start-up.
- The rand stream stays native's own (MSVC LCG, seed 1). A first catch-up beyond 2^20 logic steps walks only the last
  2^20.

### Port and checks

- `mu_cloth_wing_create(out, &wing_in, host)` takes the wing type, level, arg 4, scene and OBJECT scale.
  `mu_cloth_host` gains the sub-type model; `mu_cloth_render` takes the globals (WorldTime for the glow);
  `mu_cloth_draw_allowed` takes the class byte and sub-type. The world passes the wing level (hero: its record;
  players: the wing slot's level), scene 6 and sub-type 0. It loads each bitmap the first time a cloth binds it and
  uploads the GL set again when a new one arrives.
- `scripts/validate_item_cloak.py`: **5,694 comparisons, 0 mismatches, 0 stopped**.
  - create 278: every case's first type three times, 17 further aliases, arg 4 = 1 four times, seven wings without a case, twice
    over. Random wing level, scene 5/6, OBJECT scale, and sub-types 0, `0x5bc`, `0x5bd`, `0x5be`, `0x431` and
    `0x3e9`, with or without the sub-type model.
  - step 2,224 and render 2,224 (8 frames each, glow passes included).
  - wind 200, gate 768.
  - Coverage of the full run: 376 cloths, 12 angle-matrix cloths, 89 glows set, 648 glow passes drawn, 48 sub-type
    model cases, 216 frames hidden by the draw test, 6 character-select scalings of `0x23ec`.
- **65/65 compiled mutants caught**, none equivalent, every anchor once. The 27 new ones cover the table, the
  aliases, the level test, the glow pass, the scaling, arg 4, the angle-matrix variant, the sub-type model, the draw
  test, and the `0x8000` and gravity-180 forces.

## Part 28, armour cloths and their render passes, CLOAK-003

The bounded question is which player armour cloths `0x0135ea29` makes, and what prevents the wing-cloth renderer
from drawing them. Inputs are the pinned restored text (`pins.TEXT`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`), second section (`pins.DATA`) and initialized
third section (`pins.EFFECTS_INIT`, gravity). No live inputs. Static disassembly and Unicorn execute the original
class/part switch, constructor, setters, MoveCloth and RenderCloth. Native comparisons use authored bones and
fixture equipment. [Full mapping, parameters, checks and limits](../handoffs/CLOAK-003.md).

### Constructor and equipment

OBJECT `+0x3b` must equal 1. Armour is CHARACTER slot 2 `+0x9bc`; **pants are slot 3 `+0xdb8`**, read by classes
3, 8, 9 and 12. The previous static summary's shorthand that all cases use `+0x9bc` was incomplete.

- Base 0: armour `0x3760`, one bone-17 5x5 grid, origin (0,12.5,2), size 65x70, bitmap `0x7948`, type `0x1406`.
- Base 3: skin 3 always, one bone-19 10x10 robe, (0,12,0), 75x120, `0x7949/0x794a`, type `0x405`. Skin `0x33`
  with pants `0x37d3`, or skin `0x43` with pants `0x37e3`: bone 17, 5x5, (0,12.5,2), 60x70, `0x794b`, `0x1406`.
- Base 4: two bone-20 energy grids, 6x5 / 5x5, origins (0,10,10)/(0,10,8), 30x70, bitmap `0x7911`, types
  `0xc0000205`/`0x80002205`. Wind base/range 10/50 and 8/40. Armour `0x3754`, `0x3774`, `0x3784/0x3794` adds a
  bone-17 5x5, (0,12.5,2), 60x70, bitmap `0x8011`, `0x791d`, `0x791e`, type `0x1406`.
- Base 8: one bone-2 5x5, 50x70, type `0x1402`. Skins `0x08/0x18/0x28` use (0,16,2), bitmaps `0x7956/0x7956/0x7957`;
  skins `0x38/0x48` use (0,14,-6), `0x7958`, and a second sphere. The existing-list path releases this cloth under item
  pants, restoring it only with class pants `0x37a8..0x37e8` at stride `0x10`.
- Base 9: one bone-3 5x10, (-16,-6,2), angles (0,0,-60), 18x80, type `0x21404`. Its pants switch chooses
  `0x791f..0x7933`, with aliases. Item pants set mesh = pants - `0xae6`, pants level and EnchantEffect colour.
  Class pants `0x37a9..0x37e9` do not set a mesh. Darkangel/Blue Eye set glow `0x795a/0x7959`, pulse (3,0,1).
  Temple Guard/Imperial set glow 2 to their cloth bitmap, pulse (3.5,0.1,0.5). Imperial's mesh colour is zero.
- Base 12: pants `0x1de6/0x1de7` make two bone-2 10x10 halves, size 60x85 / 78x85, types `0x21406`, bitmaps
  `0x83ef/0x83f0` or `0x83f1/0x83f2`. Origins (+/-3,10,-4) or (+/-1.5,12,-3); U scale 0.5 and offsets 0/1.
  The first pair has fixed alpha 0.3, with no OBJECT-alpha copy. Left/right spheres use bones 10/3.
- Base 15: armour `0x375f/0x376f/0x377f/0x378f/0x379f`, no wing and class index -1. One bone-18 5x5,
  (0,14.5,23.098), sizes 102.5x80 / 102.5x95 / 101x95, `0x795b/0x795c/0x795d`, type `0x1406`.

All sphere parameters, UV/alpha/wind setters and failure states are compared by `validate_armour_cloak`, including
vertices and springs after stepping. The source gives the exact per-case sphere offsets/radii/bones.

### Render and timing

Render's flare loop `0x00fd8da3` queues one `0x7ef7` sprite per vertex. It loops columns then rows but advances a
flat position index, with scale x*0.2+0.4 and RGB (columns-x)*(sin(WorldTime*0.001)*0.1+0.4)/5. It then draws the
front with that pulsed grey; only the additive-plus-flare combination skips the back. Sprite requests go to the
world's existing RenderSprites path, preserving the deferred draw order.

After the first glow, mesh cloths run `0x00fd9c61`'s second glow at level >=9, then `0x00fd97de`'s cumulative
level passes: +13 Chrome02/UV mode `0x1000`, +11 Chrome02/`0x200`, +9 Shiny01/8, +7 Chrome01/4, needing quality
4/3/2/1. The first two use grey 0.9; the others use the mesh colour. RenderVertexMesh `0x00fd9223` computes UVs
from grid x/width and y/height with time-dependent offsets. It does not use geometry normals.

The existing-list armour constructor returns true for classes 0/3/4/8/9/15 even when it keeps the same cloths.
RenderCloth therefore calls MoveCloth again on those frames, stepping **both** lists a second time. Class 12 has
no existing-list branch. Native reproduces this between saved frames, as well as the creation frame's extra step.
Armour draws with white light after the wing list, behind `0x01362edc`'s class-4 subtype test.

### Native and limits

`mu_cloth_armour_create/update`, the extended cloth sink and `world_cloak.c` serve the existing offline demo's
wearers and hero selections. No item-body source changed. The NPC/monster armour constructor `0x01362755`, buffs,
guild/duel inputs, live motion/pixel equivalence and server equipment transitions remain outside this lane.
The handoff records the final counts, timings, native render differences and steward selection.

CLOAK-003 checks: **4,448 comparisons, 0 mismatches, 0 stopped; 19/19 compiled mutants caught**. The 14 selected
validators pass 56,284 cases; portable tests 1,362 with 0 failures/errors; private cloth modules 20/20 (8d reduced).
The default tours retain all 92 PNGs, 92 dumps and 46 normalized reports byte for byte.

## Part 29, installed Preview proofs and the counter visibility limit, APP-REFRESH-010

Same client identity and pins as above. This is offline native integration evidence, not a new original-client
capture or an extension of the reconstructed instruction domain. [Full handoff](../handoffs/APP-REFRESH-010.md).

The installed Preview is detached main 1e2a927a, including the late #351 armour cloths, with all changes since a7f7b247. Export inputs are unchanged,
so APP-REFRESH-006 Native Data is retained and its manifest verified. One full private native/tests run covered
149 modules / 1,001 tests; two errors exposed ambiguous bow mutant anchors after #350's exact-one assertion.
Four anchors are narrowed to their original branches. The two affected modules pass 7 tests and 38 compiled
mutants; selected effects12/13/14 comparisons pass. No production source or reconstruction case count changed in this refresh PR. The full private run was at a55200e2; after late main, 20 private cloth tests covered the new armour module and the changed wing structs. All installed-app proof sources were repeated on 1e2a927a.

Installed-app evidence, public one-player fixtures and the APP-REFRESH-009 rollback, matching frame 150:

- Class-0 Velvet with wing 0x2382 draws the physics cape, 2,051 changed pixels confined to the cape. Its shape
  changes between frames 120/150. Class/cloth equivalence beyond the merged bounded tests is not claimed.
- Wing 0x22ec adds 4,558 pixels in its blue streaks. Those are the two joint kinds from part 26.
- Mace 0x0f2a +9 draws its new body, 758 changed pixels. Its ordinary pose moves, but counter-driven atlas motion
  is not visually proved. The compiled body stream changes mesh-4 u from 0 to 0.75 for counters 0/7, while the
  native pass has blend mesh 4 and blend light 0. Fixed-pose/time images at different counters are identical.
  Native fill_item initializes that input to 0 and does not supply the caller's blend light. Recover that input
  before reporting visible atlas animation; do not infer a correct replacement constant from these images.
- Raklion at 198,211, frame 60, brings object 1259's spray into view. A particle-only toggle changes 4,624 pixels
  in the spray region below the statue's jaw. At the old 224,211 arrival the projected particle points are off
  the top-left. Later samples do not preserve the useful early view, so persistent visibility remains open.
- Twelve installed native captures, including windowed screenshots, have alpha 255 at every pixel. Comparisons
  ignore the rollback PNG's older, unreliable alpha; the opaque-output claim is checked on raw new PNGs.

Six small opaque window-only PNGs stay in the local app-refresh-010 rollback folder. No client data, rendered
image, helper binary or snapshot is committed. Remaining body/cloth/protection/service boundaries are unchanged.

## Part 30, counter-gated mace particles and rank-5 world owners, RENDER-EFFECTS-022

Evidence is offline. The particle create/move/render comparisons execute the pinned original routines under
Unicorn, and the item-point comparison executes the complete original RenderObjDraw. Text SHA-256:
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; data SHA-256:
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
No original-client pixels, live client, protection modules, server state or memory writes are used.

Part 26 supplied the native frame counter. Three particle kinds of the two admitted maces still had no native
consumer. They now run in the particle pool, with the counter periods unchanged.

| Kind | CreateParticle `0x015ae7b0` | MoveParticles `0x01616c80` | RenderParticles `0x0159123f` |
|---|---|---|---|
| `0x810a/0x25`, mace `0x0f1f` | `0x015b51f0`: NULL owner clears live; otherwise LifeTime = rand % 11 + 20, initial LifeTime = LifeTime, Scale = 0, scale step = scale / trunc(LifeTime/2), alpha = 1, random rotation 0..360, start = position argument | `0x0161d801`: NULL owner clears live; above half of initial LifeTime grow by the scale step, else shrink; alpha -= 1 / initial LifeTime | `0x0159f880`: NULL owner clears live and draws no sprite; position = OBJECT[+0x1f4 + 12*arg8] + start; sprite light = light * alpha |
| `0x855d/1`, twice from mace `0x0f20` | `0x01610e81`: LifeTime = initial LifeTime = 20, Scale = scale, scale step = scale / 20, alpha = 1, moving = 1, random rotation, angle = 0; spherical velocity times a random speed 1.5..3 in 0.01 steps | `0x01689aa8`: alpha -= 1 / initial LifeTime, Scale -= scale step; the common moving block rotates/adds velocity | `0x015aa71c`: light * alpha sprite |
| `0x84d1/1`, mace `0x0f20` | `0x0160c861`: LifeTime = initial LifeTime = 50, Scale = scale, scale step = scale / 50, alpha = 0, random rotation, angle = 0, velocity = (0, 0, random 1.8..2.5 in 0.01 steps) | `0x016855a9`: above half of initial LifeTime alpha += 1 / trunc(initial LifeTime/2), else subtract; Scale -= scale step; moving remains the common block's zero | `0x015a743f`: light * alpha sprite |

The spherical-vector call is `0x00d01fc6(out, 0, 1, 180, 0, 360, 0)`. The minimum radius 1 is at least the
maximum 0, so radius is fixed at 1 and draws no rand. Theta and phi come from quantised ranges after binary32
radian conversion. Every intermediate and random-call order is compared, including the common owner-position
and movement blocks, reused particle bytes and NULL owners.

### Retaining the OBJECT points

The owned spark's argument 8 is an index, not an unused flag. It selects one of three vectors written by the
mace's pre-draw program. Before this lane those writes existed only in the interpreter's register memory,
and `owner_emit` refused a nonzero argument 8. Merely admitting the kind would draw at the wrong position.

`gen_item_owner_fx.py` now emits op 50 at the actual stores to OBJECT `+0x1f4..+0x217`. `owner_fx.inc` emits
`MU_RC_OWNER_POINT` with a word index and value through the existing callback. This adds no host fields or
record fields. The world adapter stores the words in its item-owner slot, separate from the OBJECT `+0x158`
position; state writes count as neither effects nor refusals and draw no rand. The generation-checked slot
retains points between item draws. `mu_world_particles_create_args` passes argument 8 unchanged, and the world
particle draw calls `mu_pt_item_counter_follow` before the ordinary render. Stale/missing owners and indices
outside the actual domain 0..2 end the particle instead of reading unrelated memory.

The general store rule also exports `0x0f2a`'s first point, with no other change to that program. Its particle
kinds remain outside this lane. Only those two programs' op sequences change, plus later table offsets.

The render family runs each kind separately so the owned spark exercises argument 8 indices 0, 1 and 2;
a mixed three-kind cycle would otherwise lock that index to zero. The new validator's points family supplies
the named-bone table explicitly, places the required names at
known indices, varies shared versus OBJECT-owned matrices and includes hidden frames. It compares all nine
retained words, the existing draw/request streams and rand counts. Its production op-50 mutant must change
these words and be caught even when the draw/request streams still agree.

### Bitmap registrations

Verified static startup calls, also checked by the validator:

| ID | LoadBitmap call | File | Filter / wrap |
|---|---|---|---|
| `0x855d` | `0x01825ca1` | `Effect\pin_star03_red.jpg` | LINEAR / CLAMP |
| `0x84d1` | `0x0182e978` | `Item\texture\smoke01_strong_red.jpg` | LINEAR / REPEAT |

The native table grows 77 to 79 slots. Fire06 stays after these additions and rain02/rain03 stay last.
Existing bitmap slots before the insertion are unchanged. `0x810a` already had a texture. The mace's existing
`0x855d` bone sprites also become visible with this slot. The world pool still lacks slots for `0x0f1f`'s
four `0x7f7a` bone sprites and `0x0f20`'s thirteen `0x80ba` bone sprites per draw. They remain counted-only;
this lane does not port those two loader entries.

### Rank-5 owners in the world

Part 23's world hook admitted the 43 armour/helm owner programs only. `world_rt_part_owner` now also admits
`mu_rc_item_rank5`, so players, the hero and player-model actors use the already reconstructed rank-5 block.
It reads the character's posed bones 35/26 through the existing transform adapter, emits four `0x84e2/0`
particles, one `0x7fdd` sprite and one `0x83de/4` particle, and runs its level-9 overlay meshes before the later
glow passes. Source blocks are `0x01747d6d`, `0x0174888d`, `0x01749294`, `0x01749cc5` in RenderPartObjectBody.
The arithmetic and recipes are unchanged; `validate_render_effects5` covers their original-instruction behavior.
Native tests cover rank-5 player and hero callers. The player-model actor caller uses the same hook but has no
installed render fixture here.

### Refusal census, checks and limits

The final counts, wall times, before/after native render measurements, byte-identity sweep and exact steward
rows are recorded in [RENDER-EFFECTS-022](../handoffs/RENDER-EFFECTS-022.md). These are original-instruction
comparisons and offline native before/after renders, not original-client pixel equivalence. The native pose and
counter's absolute phase are unchanged assumptions. The viewer still lacks an item OBJECT registry and refuses
the owned spark. `0x0f2a`'s `0x85bc/5`, `0x83b8/8`, `0x85fc/1` and register-selected particle remain next work.

## Part 31, the six remaining counter bodies and quantised random colours, RENDER-ITEMS-002V

Bodies **1,364 -> 1,370 of 1,674**, adding `0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`, `0x0f2c` and `0x1588`.
The five maces also gain their RenderObjDraw effect programs. There are **304 bodies left**. The later read-program
candidates were screened but none were admitted; the rank-5 strlen group was not attempted.

Evidence is the same pinned restored text and data as part 26: `pins.TEXT` at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, and `pins.DATA` at `0x01a7c000`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. Methods: static instruction reading, finite
recipe probes, full RenderObjDraw comparisons under Unicorn, compiled C comparisons and offline native renders.
No live client or protected component was used. These are bounded instruction comparisons, not original-client pixel
or process-random-phase equivalence.

### Why they did not fit

| Type | Cause and original addresses | Reconstruction |
|---|---|---|
| `0x0f24` | Pre-program `0x017d5675..0x017d62b7`; body range return `0x01769b6a`; scroll reads the frame counter at `0x01769c75` | `0x011ff622(0.25, 1, 100)` supplies a random colour scale. The component writes at `0x01769b73..0x01769c1a` multiply each constant by the range, then by 0.4, with two binary32 roundings. A single folded constant does not preserve them. |
| `0x0f28` | Pre-program `0x017d8bfc..0x017d94dc`; `0x017d8e07..0x017d8e46` computes `3 * (counter % 120)`; body range return `0x0176aa90` | The range is `0x011ff622(0.5, 1, 100)`. The pre-program's unsigned-to-double correction is zero because the converted integer is bounded to 0..357; its final binary32 value is the existing integer-to-float op. The exact conversion sequence and correction-table zero are checked before this reduction is allowed. |
| `0x0f29` | Pre-program `0x017d94f1..0x017d9dcb`; body range return `0x0176b0e0` | Quantised range `(0.25, 1, 100)`, counter chains, carried model fields and supplementary record/quality probes. |
| `0x0f2b` | Pre-program `0x017dab03..0x017db6cf`; body range return `0x0176bae5` | As above, with this type's own colour constants and requests. |
| `0x0f2c` | Pre-program `0x017db6e4..0x017dc347`; counter gate `0x017dbef8..0x017dbefc`, loop `0x017dbf09..0x017dc1e7` | The constant two-iteration loop is inside `counter % 2 == 0`. Its jump to the condition and back edge stay inside the open gate, so they can be unrolled while the gate remains a runtime condition. Runtime backward conditions still refuse, and the interpreter's instruction limit remains. Its body draws need counter/derived/carry recipes but no body random. |
| `0x1588` | Colour setter `0x01736abc`; random-wrapper returns `0x01736b46`, `0x01736c5f`; counter chain at `0x0173691a` | `0x0185caa4` calls `0x011ff622(lo, hi, 1)`, then divides and adds in binary32. The two calls here use `(0, 10, 10, 0.2)`. Colour `(0.5, 0.35, 0.75)` is scaled by the wave and then by the random result. The intermediate component products must round before the second multiplication. Exit-field probes, rather than last-draw carry, preserve the fields read by the ancient pass. The scroll is `-((counter + 1) % 25) * 0.04`. |

Every row reads the same unsigned rendered-frame counter `[0x0bdc5ebc]`, not the logic clock or the item's
animation frame. Its body coordinates and pre-program tests are:

| Type | Body counter use, binary32 scales | Pre-program counter use |
|---|---|---|
| `0x0f24` | `(counter % 100) * 0.01` scroll | Particle blocks when `% 2 == 0` and `% 25 == 0` |
| `0x0f28` | 4 x 4 atlas from `counter % 16`; scrolls `(counter % 25) * 0.04` and `(counter % 100) * 0.01` | Bone-sprite rotation `3 * (counter % 120)`; particle blocks when `% 2 == 0` and `% 8 == 0` |
| `0x0f29` | `(counter % 25) * 0.04` scroll | Particle block when `% 2 == 0` |
| `0x0f2b` | `f = (counter % 12) / 2`, then `(f % 6)` converted to float and **divided by 6**, not multiplied by a rounded reciprocal | No counter test in the pre-program |
| `0x0f2c` | `(counter % 50) * 0.02` scroll | Particle blocks when `% 10 == 0`, `% 2 == 0` with the two-iteration loop, and `% 50 == 0` |
| `0x1588` | `-((counter + 1) % 25) * 0.04`, with uint32 wrap before the remainder | No effect program |

The pre-program survey had another false refusal: it counted range-helper calls after the body helper as effect
services after the draws. `RANGE` and `RAND` are scalar computations there, so they no longer trigger that refusal.
Actual effect services after the body still refuse the pre-program reader.

### Recipes and native execution

- Kind-4 random programs gain an integer offset before float conversion, then lower and upper clamps. The original
  `0x011ff622` truncates `steps * lo/hi` after binary32 multiplication, draws one CRT
  rand, takes the signed remainder in the inclusive integer span, adds the lower integer bound, converts to float,
  divides by steps and clamps to lo then hi. The generator accepts only constant arguments and bounded valid spans.
- The wrapper `0x0185caa4..0x0185caff` first checks its bounds and nonzero divisor. Only its valid constant-argument
  domain is admitted. The wrapper's extra division and addition retain their binary32 rounding.
- Kind-6 programs can retain the two constant multiplications of the mace colour writes. Kind 7 multiplies two
  already-modelled inputs once in binary32. For the staff, the verified setter's component constants seed the
  wave products before a recipe may use the second random multiplication. Kept programs retain and remap all
  dependencies; probes still have to agree at every used draw word.
- `MU_RC_BODY_SCALARS` grows 12 -> 24; the staff uses 22. Clock chains remain capped at 12 ops. Only used op/k slots
  are written in `item_bodies.h`, as in 002U. This is internal table storage, with no exported struct/ctypes change.
- The five mace pre-programs use the existing item host, bones, counter, random-vector and request operations.
  No particle kind, native app, world counter or world caller is changed by this lane.

### Checks

Final counts and wall times are recorded in [RENDER-ITEMS-002V](../handoffs/RENDER-ITEMS-002V.md).
The final pre-draw validator passed **36,196 comparisons, zero mismatches and 48/48 compiled mutants** in
377.4 s. Families: bodies 14,892, hidden 1,168, frame 16,936 and owned programs 3,200. The frame family covers
58 types and 6,971 distinct counter values. The shared random-body validator passed 28,080 comparisons and
11/11 mutants in 226.6 s. Both generated tables reproduce. The full header is 499,004 bytes; recipe rows rise
1,345 -> 1,351. The survey changes exactly six rows in each TSV, complete shapes 586 -> 592 of 798.

The isolated six-type library passed 1,752 body states and 1,752 counter states, plus 320 owned pre-program states,
all with zero mismatches. The counter states included high-bit values and 1,337 distinct counter values. Owned
states compared the complete draw stream, effect requests/refusals and exact rand consumption.

The body-only comparisons for the five pre-program maces use zero rand results: without an item host the native
pre-program is absent, and the original's extra pre-program calls must not shift the body values. Their owned
comparison supplies the same nonzero sequence to both complete programs. The pure-body staff compares nonzero
sequences and exact consumption directly. Moving-counter checks cover all 58 admitted counter types.

### Later groups and limits

- The 24 next read-program candidates were screened with default, carry and exit probes, with and without
  supplementary probes. Twenty-two programs read. `0x2301`/`0x2302` still refuse at the wave operands. Only
  `0x23a8`/`0x23a9` and bows `0x1313`/`0x1317`/`0x1319` fit the initial probes; each fails the independent body-state
  comparison under all three carry options. None is admitted. The first failing states are 3, 6, 4, 3 and 2,
  respectively, in `validate_item_quality.state_cases`. These are rejection results, not passing coverage.
- The other candidates were `0x0f1e`, `0x174a`, `0x23f0`/`0x23f2`, `0x0b51`/`0x0b52`, and part 18's eleven:
  `0x0b29`, `0x0b4d`, `0x1314`, `0x230d`, `0x23ed`, `0x23ee`, `0x23fe`, `0x23ff`, `0x2403`, `0x2404`, `0x2497`.
- The 31 rank-5 strlen parts and the 54 helper-group-count types remain. No new rank-5 pose input was inferred.
- New effect requests are routed through the existing native consumers. A recorded request is not proof that its
  particle kind or texture exists in the native pool. RENDER-EFFECTS-022 owns the parallel `0x810a`/0x25,
  `0x855d`/1 and `0x84d1`/1 particle work; it is not included in this lane's coverage.
- The counter's absolute process phase and the process random phase remain different from the original. The finite
  domain remains unselected items without buffs; unavailable bones and kinds remain explicit refusals.


### Native visibility follow-up for `0x0f2a`

APP-REFRESH-010's proof (c) remains **unverified**, and an independent offline render reproduces its failure.
At fixed action 1, frame 0.5 and world time 123456, `mu-render character --class 1 --world-render` with
`Hammer15.bmd` as weapon0, type `0x0f2a`, level 9 and counters 0/7/8 emits three byte-identical 640x480 PNGs
(SHA-256 `ed849c51a9a47e42e3176feb1e0dce5a2fcf5060065067d386a2f08b687d5efb`). Each draws 9,274 triangles,
13 passes, with `special=0`. The counter reaches the body: its selected mesh 4 UVs are (0,0), (0.75,0), (0,0.25).
But each selected pass retains blend light 0. `fill_item` zeroes that input; `draw_item` forwards it as the
mesh colour scale. UV motion therefore supplies no visible contribution in this fixed-pose native path.

A static read plus original constructor/ObjectInit execution under Unicorn both return normally, with
OBJECT `+0xa8` still zero. ObjectInit `0x0129eb81` explicitly stores zero there at `0x0129ed3c`, after
`xorps xmm0,xmm0` at `0x0129ed39`. This is evidence against assuming that construction supplies a constant 1.
The later caller that supplies visible blend light for this worn item has not been recovered. No guessed
constant is installed. This lane proves counter-driven command changes, **not visible atlas animation**.
The installed preview is untouched. Recover the OBJECT/PART caller's blend-light value and lifetime before
claiming visual completion; then repeat this fixed-pose native test and the app proof.

## Part 32, the remaining mace particle consumers and world bitmap slots, RENDER-EFFECTS-023

Offline/static evidence only. CreateParticle `0x015ae7b0`, MoveParticles `0x01616c80` and RenderParticles
`0x0159123f` run under Unicorn over the pinned text/data, with synthetic records, owners and random sequences.
Text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; data SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Native images are before/after renders, not original-client pixel comparisons.

### Particle pairs

`reconstructed/particles/item_mace_kinds.inc` adds the 19 remaining pairs in the mace programs. The original
common initialization, owner-position refresh, velocity rotation and lifetime decrement remain shared.
The new validator compares defined record bytes, random consumption and ordered sprite/GL calls.

| Item | Pair | Create / move branch | Behavior |
|---|---|---|---|
| `0x0f2a` | `0x8315..0x8317/4` | `0x016065fd` / `0x0168076d` | 16-step fire, shrinking scale, pulse alpha; one shared random displacement on x/y |
| `0x0f2a` | `0x85bc/5` | `0x01612d8e` / `0x0168ac20` | 30-step red line, scale step `(scale - scale*0.3)/30`, pulse alpha |
| `0x0f2a` | `0x83b8/8` | `0x015e407f` / `0x01657e76` | 20..30-step chip; input angle becomes velocity before angle jitter; later velocity drift and fade |
| `0x0f2a` | `0x85fc/1` | `0x01613f98` / `0x0168be7c` | 30-step owned ring, grows from zero, fades below half life, follows the selected OBJECT point |
| `0x0f24` | `0x7ffb/0` | `0x016147ae` / `0x0168c6ab` | 30-step owned shockwave, same growth/fade and direct point following |
| `0x0f28` | `0x807e..0x8080/0x18` | `0x015cfc7a` / `0x01642f6e` | 30-step smoke lines, expanding scale, pulse alpha, random spin and rise |
| `0x0f28` | `0x83b3/0x13` | `0x015d19c4` / `0x0164412a` | 30-step expanding smoke, pulse alpha |
| `0x0f29` | `0x8109/0xe` | `0x015b08fc` / `0x016196d9` | Random 0.5..1 scale, velocity from input angle, angle jitter, velocity drift, spin and late fade |
| `0x0f2b` | `0x8081..0x8083/9` | `0x015d3821` / `0x016459fb` | Four-step glints, random rotation and alpha fade |
| `0x0f2b` | `0x8549/1` | `0x01615d4e` / `0x0168ec04` | Four-step glow, alpha fade |
| `0x0f2c` | `0x82f2/0x1a` | `0x01605f17` / `0x01680103` | 30-step expanding smoke, pulse alpha |
| `0x0f2c` | `0x810b/0xa` | `0x01602036` / `0x0167bf75` | 20-step shrinking glint, input-angle velocity, angle jitter and late fade |
| `0x0f2c` | `0x85fc/2`, arguments 8 = 0/1 | `0x0161400a` / `0x0168be7c` | 50-step owned ring, direct point following |

All 19 render their light times alpha. The pulse uses `LifeTime > initial/2`; the late fades use
`LifeTime < initial/2`. Equality differs between these branches and is sampled explicitly. Products,
subtractions and divisions retain the client's intermediate binary32 rounding and random-call order.

`0x85fc/1,/2` and `0x7ffb/0` read OBJECT `+0x1f4 + 12*arg8` directly at render time
(`0x015ac52a`, `0x015ace36`). They do not add the record's birth vector, unlike EFFECTS-022's `0x810a/0x25`.
Their move clears live on NULL owner; their render leaves position unchanged on NULL owner. Native slot
bounds and generation checks reject stale native references without borrowing another item's points.
The world adapter hosts three points; arbitrary OBJECT memory is outside the domain.

### Bitmap slots and viewer owners

The world bitmap pool grows 79 to 93 slots. `0x7f7a` is `Effect\flare03.jpg`, loader call `0x01823fd4`;
`0x80ba` is `effect\flare01_red.jpg`, call `0x01823914`. Both are LINEAR/CLAMP. The other twelve slots
supply the new particles; only `smokelines01..03` repeat. The validator reads every original call's pushes
and path string; a synthetic native loader fixture supplies distinct greys and checks the actual file mapping,
filter/wrap, and all 19 native draw calls. Fire06 remains after the additions, rain02/rain03 last.

The character viewer assigns a stable registry key per loaded item and refreshes it per draw, through the
same retained point callbacks as the world. It now hosts the owned spark and rings. No blend-light default,
body recipe, item fit, atlas clock, pose or installed app changes here. RENDER-ITEMS-002W owns the blend-light
and body-fit follow-up.

### Refusal census and evidence limits

The admitted tables contain 93 programs and 30 distinct particle pairs; all 30 have native consumers,
with zero unresolved bitmap expressions in the bounded static census. Nineteen are added here. The remaining
world sprite texture gaps are `0x81ec` (three `0x0f2a` sites) and `0x854a` (four `0x0f2b` sites), counted-only.
Hammer14 contains `up01 ` while the program asks for exact `up01`: one sprite refusal per draw remains.
The five-new-mace fixture improves from 2,988 accepted / 322 refused to 3,249 / 61 over 61 draws; all 321
particle requests create, zero unsupported. The full proof has 58,014 component comparisons with zero mismatches;
31/31 compiled mutants are caught. Default captures retain 92/92 PNG and 92/92 dump byte identity.

The native counter and random stream retain their earlier phase differences from the client. Named-bone and
out-of-domain requests remain refused. The point transform proof does not establish native/original pose
identity. Native before/after images establish that these consumers draw in the native paths; they are not
original-client pixel equivalence. Checks, counts, timings, render measurements and remaining work are in
[RENDER-EFFECTS-023](../handoffs/RENDER-EFFECTS-023.md).

## Part 33, NPC and monster cloth callers, CLOAK-004

The remaining constructor `0x01362755..0x01362e1d`, SHA-256
`e80e875813736e2eb79a71ac22017f69de6ebbfd1c0ce4fc38f5ea902640ab60`, fills OBJECT `+0x48`, count `+0x3e`.
Evidence is the same pinned restored text, second section and initialized third section as parts 25/27/28.
No live input. [Mapping, parameters, checks and limits](../handoffs/CLOAK-004.md).

### Selection and parameters

The entry rejects null CHARACTER/OBJECT and an existing CHARACTER `+0x329c` list. It tests CHARACTER `+0x146`:

- `0x37`, Death King: one bone-19 10x10 robe, origin (0,10,0), size 55x140, bitmap `0x790d`, type `0x1001`.
  Spheres: (-10,-10,-10,r35,b17), (10,-10,-10,r35,b17), (0,-10,-40,r50,b19).
- `0x169`, Nightmare: one bone-2 6x6 grid, origin zero, size 180x100, bitmap `0x7ff2`, type `0x1008`, no spheres.
- `0x3a9`, Eunice Monster, and `0x3ab..0x3ad`, Eunice Town/Entrance/Quest: two bone-4 10x10 halves,
  origins (+10,8,2)/(-10,8,2), size 200x120, bitmaps `0x84e6/0x84e7`, type `0x1005`. UV scale (0.5,1),
  U offsets 0/1. Spheres are on bone 3 with x=-10/+10, opposite the origin, y=-5, z=-10/-30, radius 30/35.
- Every other index, including the gap `0x3aa`, gets no cloth. The constructor retains the allocated list/count
  when the individual Create call fails for absent bones or a missing model, as the player constructors do.

The bitmap startup calls resolve to `Player/Robe03.tga`, `Monster/nightmare_cloth.tga`,
`NPC/eunice_cape_L.tga`, `NPC/eunice_cape_R.tga`. All use GL_CLAMP; Robe03/Nightmare use GL_NEAREST,
Eunice GL_LINEAR. The names above are from the local exported Npcname table, not inferred from filenames.

### Models and callers

RenderCloth calls this at `0x01363102` only after player armour creation declines. When it returns true,
MoveCloth runs again that frame. An existing NPC list returns false, so its normal frame cadence is one step,
with two on creation. The list renders after the wing list with white light, through the existing visibility tests.

Death King uses Player model `0xa91` at scale 1.4 in the existing generic class table. Eunice NPCs use `0xa8b`,
`N_eunice.bmd`, scale 0.9. The generic world-0 table had fallback model `0x7a5` for the other two:

- Nightmare's world-39 processor `0x00e879ad`, predicate `0x00e84513`, opens monster type 121 and calls
  CreateCharacter with model `0x81e` at `0x00e87a3c`, then writes scale 1.6.
- Eunice Monster's dedicated virtual create method `0x00d5a9d3`, branch `0x00d5ad35`, opens monster type 437,
  passes model `0x95a` at `0x00d5ad57`, then writes scale 0.9. The pinned vtable pointer at `0x01aa5244` is slot
  `0x48` of `0x01aa51fc`; the existing factory census binds that class only to world 121. That binding is static;
  the bounded instruction run does not execute the virtual manager's lifecycle.

`mu_cloth_npc_model` supplies those bounded selections to native actor loading. Both overrides keep their world conditions, 39 for Nightmare and 121 for Eunice Monster. The player actor loader now admits Death King. The actor
parts draw cloth after body parts/before links for Player models, after the body for other models. The shared
world cloth state has separate actor slots, steps them between saved frames on their own posed bones and clears
those slots before actor-cache replacement, travel and unload. Ordinary town NPCs are not in this constructor.

`validate_npc_cloak` compares the complete constructor, real MoveCloth/RenderCloth frame calls, existing-list
rejection, every cloth field and the ordered GL stream. It also executes the two model-selection entries through
the actual scale stores with engine open/create/name services supplied, stopping before trailing effects.
Final counts, compiled mutants, native scenes and byte-identity results are in the handoff.

## Part 34, mace sprite textures and Ferea fire emitters, RENDER-EFFECTS-024

Offline/static only. Original-instruction comparisons use pinned text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` and data SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Native before/after images are visibility and regression evidence, not original-client pixel equivalence.

### The two sprite texture gaps

Verified static LoadBitmap calls, with their six pushed arguments and original path strings checked by
`validate_render_effects24`:

| Bitmap | Loader call | Original path | Native file | Filter / wrap |
|---|---|---|---|---|
| `0x81ec` | `0x01823365` | `Effect\lightmarks_red.jpg` | `Data/Effect/lightmarks_red.OZJ` | LINEAR / CLAMP |
| `0x854a` | `0x0182ec0d` | `Effect\light_blue.jpg` | `Data/Effect/light_blue.OZJ` | LINEAR / CLAMP |

The world table grows 93 to 95 slots. Slots 0..89 retain their indices; the additions precede Fire06, and
rain02/rain03 remain last. Synthetic files contain distinct greys, so native checks reject swapped files as well
as missing IDs, wrong filtering or wrapping. Both sprites must actually reach the raster draw path. The new slots
serve the three `0x81ec` sites of `0x0f2a` and four `0x854a` sites of `0x0f2b` from part 32.

### Exact Hammer14 bone names

The installed `Data/Item/Hammer14.bmd` has SHA-256
`9c294b8ea5d4db8c7ad35543e102076800d3a042fae6ce81b349cc72eab4220c`. Bone 9 is exactly `up01 `, including the
trailing space; the program asks for `up01`. The lane checks installed authored Hammer14 variants without trimming
or normalizing names. An unrelated model having an `up01` bone would not justify replacing Hammer14. The refusal
remains, with the bounded variant-search result and native counts in the handoff.

### The next measured refusal, Ferea fire

The lane's default 46-view census at main `6736cb57` finds six refused `0x413/10` effect requests and one refused
`0x7f89/28` particle request, all in Ferea. The 61-draw Ferea view has 183 refused fire emitters and 11 refused
clouds/28. The fire emitter is therefore the next consumer selected. The Lorencia demo and eight admitted mace
wearers add no unsupported particle kinds. Counts cover these scenes, not every client program.

CreateEffect sets blend mesh 1 at `0x013d2f08`; subtype 10 follows `0x013d3b33..0x013d3b58`, sets lifetime 1
and leaves the common scale, position, angle and light. MoveEffect `0x0146d6b9..0x0146d7f5` selects one child
with rand % 3, preserving position, angle, light and scale, no owner:

| Choice | Child | Native consumer |
|---|---|---|
| 0 | `0x8084/3` | Added in `world_flames.c` |
| 1 | `0x806e/4` | Existing `world_flames.c` |
| 2 | `0x8085/0` | Existing `world_flames.c` |

The emitter skips the ordinary Fire Ball trail/light block, follows the common movement/animation tail, then
retires when its one-step lifetime decrements to zero. The comparison includes arbitrary modeled records, owner
reads, model-present/absent paths, animation boundaries, ordered child calls and rand consumption. No Fire model
slot is added to the world; this consumer supplies the particle request.

`0x8084/3` create `0x015d45a8..0x015d4748`: lifetime rand % 5 + 27; scale
`((rand % 72 + 52) * 0.01f) * scale`; rotation rand % 360; gravity `(rand % 14 + 44) * 0.1f`; alpha 0;
keep the input light in the three saved-light words and clear current light. Move `0x01646f7f..0x0164723a`
shares the flame's alpha fade and saved-light products, but its positive scale shrinks by `(rand % 3 + 2) * 0.01f`.
It rises by gravity and rotates by 3. Its existing render draws the current light. The comparator caught the
incorrect subtype-0 shrink before the new branch was finalized. All three children are compared for create,
move and render, although only `0x8084/3` needs new logic.

The full focused proof passes 11,006 comparisons with zero mismatches. Compiled mutants, native scene counts,
wall times, default byte identity, remaining refusals and exact steward rows are recorded in
[RENDER-EFFECTS-024](../handoffs/RENDER-EFFECTS-024.md). No blend-light default, item fit, pose, frame counter,
installed Preview or Wine app changes here. Clouds/28 remain a separate consumer to recover.

## Part 35, worn mace light and named part meshes, RENDER-ITEMS-002W

Prerequisite #355 merged before the branch was created. This lane covers the missing worn `0x0f2a` input,
three read-program bows and the 31 strlen parts. [Handoff and verification](../handoffs/RENDER-ITEMS-002W.md).
Particle-request recovery and new particle/sprite consumers are left to RENDER-EFFECTS-023.

### Worn-item caller input and visible atlas

ObjectInit's zero at `0x0129ed3c` is not the final draw input. `RenderLinkItem` reaches the linked OBJECT at
PART+0x24, sets its type and calls `ItemObjectAttribute` at `0x012bdafb`. The callee loads 1.0 from
`0x01a7dd48` at `0x016da0fb`, then writes OBJECT+a8 at `0x016da103`. It also supplies blend mesh -1 and zero UV.
Guarded original execution at times 0, 1, 123456 and -8000 confirms the light and mesh values independently of
poisoned prior fields. The native fill is corrected for this established type only.

The regression first fails with one hash at counters 0/7/8, then passes with three. It holds class, model,
action, pose frame, world time, dimensions and all other inputs fixed. The same demo equipment passes through
a locally built Preview launch plan under its network guard, using isolated settings/session/options. Matching
world frames differ from baseline. This closes APP-REFRESH-010 proof (c) for the native worn path; it does not
refresh the installed app, certify absolute process phase, or substitute pose motion for texture animation.

### Read-program candidates

The three bows `0x1313`, `0x1317`, `0x1319` require per-type scalar recipes with exact SSE order, extended
quality/record probes and range-wrapper random attribution in pre-program blocks. Their original 1-ULP failures
were not relaxed or compared approximately. Both body and owned paths compare exact words and request order.
The two wings `0x23a8`/`0x23a9` still fail fits under default/carry/exit variants and are not enabled.

At `0x017b1d91..0x017b1dad`, `0x2301`/`0x2302` call the wave helper with exact `(0, -4)` operands, rather than
the supported nonzero-frequency/zero-second-argument case. The pinned helper's masked SSE division/CVTT path
produces INT_MIN dividend and divisor, remainder zero and +0. A directed 200-state screen includes signed zeros,
finite boundaries, infinities and NaNs. The reader folds only exact words `0` and `0xc0800000`, with portable
negative-operand tests. Both types now read (312 operations) but still fail draw fitting. No body is admitted for
that reader extension. The other nineteen candidates remain rejected by the existing fit/supplementary probes.

### All 31 strlen parts

A name lookup at `0x012bd4a6` is a model input, not a fixed mesh number. The 28 armour parts are four groups
`0x1a00/0x1e00/0x2000/0x2200`, each with indices `0x26/0x27/0x2c/0x2e/0x2f/0x33/0x44`.
Their Blue/Black/skirt lookups are independent. Weapons `0x0b5c/0x0b62/0x0b68` use their own exact names, including
case-sensitive `.JPG` suffixes. The generator's 21-name catalog is in `validate_renderchar.NAMED_MESH_NAMES`.

New scalar kind 8 copies a lookup's signed mesh index as an integer word. The context appends a callback and
user pointer; old lighting/blue/random fields keep their offsets. Missing context, missing callback or missing
name yields -1. Native lookup searches the drawn model in order and returns the first exact texture name.
The bitmap census supplies present indices to discover all referenced overlays; it does not supply worn indices.
The ordinary classification fixture remains unseeded: its strlen stops and recorded shapes are not rewritten.
Independent comparisons declare the name results and vary positive indices, all missing, each missing and mixed
results, quality, lighting, all levels, alternate records, frame counters and nonzero random sequences.

An early prototype skipped MESH(-1) in the reconstructed stream. The original emits those calls, so that
prototype failed independent comparisons. The final stream keeps them. The native adapter skips a negative
mesh as the original `MeshDraw` does at `0x012b8d46..0x012b8d51` (wrapper call `0x00966e9b`). This prevents a
missing part name from becoming a whole-model draw. Synthetic native models test missing names, independent
part overlays and duplicate names.

`0x0b62` also exposed a clock-reader gap: `0x0172972d` computes `tick % 415 / 83`; the signed remainder-by-one
idiom at `0x01729754..0x01729766` stores U=0, then `0x0172977a..0x0172978a` uses the saved cell times .2 for V.
Allowing the zero-low-bit mask in the existing byte-verified signed remainder reader reaches that V store.
Portable authored instructions exercise both UV chains, including negative clocks; no runtime opcode is added.
`0x0b68` joins the frame-counter set with its `(counter + 1) % 60` scroll. High-level phase probes preserve the
raw level/quality split instead of mixing their different draw counts.

### Remaining work and bounds

The 54 helper-group-count types remain, followed by the other unadmitted types. A two-seed level-zero screen
is exploratory and does not establish full coverage for that group. Named body draws do not establish new
rank-5 pose or owner effects. Existing bone, record, buff, selected-item, process-rand and process-counter bounds
remain. No original client process, protected component, live server/login, packet, character-power or memory-write
work was used. Final counts, table size, exact validator timings and default-draw comparisons are in the handoff.

## Part 36, carried fields, alpha products and no-glow bodies, RENDER-ITEMS-002X

Prerequisite PR #360 merged at `54a53e1a` before this branch was created. This is offline/static work over the
same pinned instructions as part 35: text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
data SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. No client process, protected
component, original installation change or service work is involved. [Handoff and checks](../handoffs/RENDER-ITEMS-002X.md).

### Fourteen later read-program bodies

`gen_item_owner_fx.READ_PROGRAM_TYPES` adds fourteen types. Every pre-program reads with the existing operations.
The exact `(0, -4)` wave-operand fold for `0x2301/0x2302` is part 35's established reader behavior, not a new
approximation here. It still produces the same zero used by the original masked SSE/CVTT route.

| Types | Pre-program start | Body inputs needed |
|---|---|---|
| `0x0b29` | `0x0179ecc0` | Binary32 wave and RenderObjDraw argument alpha multiplied once, scalar kind 7. |
| `0x0b52` | `0x017ab1ab` | Its own wave, clock chain and derived product; default carry. |
| `0x0f1e` | `0x017d405a` | Two wave chains, retained intermediate colour products and carried model fields. |
| `0x174a` | `0x017dd9b3` | Wave times argument alpha, plus carried model fields. |
| `0x2301/0x2302` | `0x017b1c84` | Two wave chains multiplied by OBJECT alpha `+0xdc`, plus carried model fields. |
| `0x23a8/0x23a9` | `0x017cbb53` | Their own binary32 wave chains, extended probes and carried model fields. |
| `0x23ed/0x23fe/0x2403` | `0x01774185` | The sine chain and its binary32 addition, plus carried model fields. |
| `0x23ee/0x23ff/0x2404` | `0x0177448a` | The sine chain and its binary32 addition, plus carried model fields. |

A nested range call must be attributed to its original pre-program caller before it is excluded from the body
random probes. The existing counter/range probe policy now includes these fourteen types. Treating a wrapper's
internal rand return as a body-random site made extended fits fail before the body could be fitted. Body random
sites outside a declared pre-program still remain part of the body fit and its consumption checks.

The old initial fit of `0x23a8` fails independent state 3, and `0x23a9` state 6, by one ULP in mesh blend light.
The accepted recipes use the parsed binary32 wave operations, rather than the shared binary64 blend expression.
The wave pair fails initial states 20/17 with an extra original draw that the incorrectly fitted stream omits.
Extended probes and carrying the model fields left by the previous body draw resolve those failures. No draw,
colour word, alpha source or comparison tolerance is discarded. Argument alpha and OBJECT alpha remain separate
inputs. Scalar kinds, clock-chain caps, scalar storage and public C/ctypes layouts do not change.

The isolated owned comparison runs the same nonzero random stream through each complete original program and
its C reconstruction. It checks every draw word and model field at each recorded draw, ordered requests and
refusals, and exact random consumption. The host-free body family uses zero random results for these pre-program
types, since there is no native pre-program without an item host. Nonzero shared-stream fidelity is established
by the owned comparison, not attributed to the host-free path.

### Six cases bypass the glow helper chain

`0x232c..0x2330` and `0x26f5` use their own body path and then the ordinary option/ancient tail. They do not run
the normal level-glow chain. The existing internal `plain` recipe flag selects that behavior; no new runtime
opcode or public input is introduced. All raw levels are preserved in the input item.

The body's generic-reference probes use level zero and clear only the forcing kind-B value in that reference
copy. This prevents records `0x26/0x5b` from sending the reference down the glow chain. The original instruction
run and the public native comparison retain the unmodified fixture record. The independent `validate_item_groups`
family tests every level at qualities 0/1/2/9 with both forcing records, kind A 0/6 and both tail settings.
Portable tests require that level and those records preserve the declared no-glow body. They do not change
character stats or item records.

### Safe refusal and table size

The largest-group screen exposed stale `_PHASES` data after an unusable probe. A later type with another scalar
width could feed the previous type's rows to `derive()` and raise IndexError. `_fit` now clears that state before
sampling. A portable test seeds an earlier type's phase, forces a failed probe and verifies that no phase remains.
It fails before the fix. The exploratory tail then rejects both types normally. A rejected type is never admitted
because a previous type happened to leave compatible probe data.

The generated C constants omit redundant leading zeroes and spell zero as `0`. Values, array ordering and integer
widths are unchanged. Table reproduction and the C-to-C check cover the regenerated table; final size and body
count are in the handoff. The audit's 512 KiB limit and existing scalar/operation caps still apply.

The survey export had a separate membership list that omitted the named bodies from part 35 and the new
no-glow list. It now consumes `gen.ALL_TYPES`. A portable regression compares its membership with native
`mu_rc_item_special` for all 1,691 surveyed types. Re-exporting the saved raw survey changes only the intended
20 type memberships and nine shape totals; raw classifications, addresses and stopped states remain unchanged.

### Rejected groups and evidence limits

Seven read-program candidates remain rejected: `0x0b4d`, `0x0b51`, `0x1314`, `0x230d`, `0x23f0`, `0x23f2`,
`0x2497`. The helper group adds six types; the other historical 48 remain. The current three-level diagnostic
finds 57 types with some helper-count disagreement, including types whose first blocker is an effect or matrix
call. That diagnostic is not a redefinition or passing census of the historical 54-type group.

Joining consecutive helpers without dropping a draw did not establish a fit for the fifteen tested cases. The
prototype is removed. The no-glow experiment admits six of 23 candidates and rejects the rest. Those other cases
still need model/input-state recovery or different caller flow; a count adjustment alone is insufficient.

The four largest other groups attempted add no body. The four shields `0x1735/0x1737/0x1738/0x1755` refuse fits.
The four armour types `0x2003/0x2007/0x200f/0x2010` reproduce independent overlay-colour failures at states
22/25/27/21. Their differing words are body-light channels; the generic shade/light inputs do not explain them.
The exact source/lifetime of those channels remains open. The two mace cases `0x0eed/0x0f0b` retain matrix work;
`0x0ef4/0x12fb` refuse after the stale-phase fix. These are rejected probes, not coverage.

Requests from the fourteen programs go through the existing item host and native consumers. Missing named bones,
short skeletons, unsupported particle kinds/arguments and missing textures retain explicit refusals. No new
particle kind, pose construction, original-client pixel equivalence or absolute random/counter phase is claimed.
Selected-item, buff and prior record-domain limits remain. Final counts, wall times, affected rows, mutants,
private native checks and the default-draw sweep are in the handoff.

## Part 37, missing-name sprite state, Ferea clouds and the remaining bow pairs, RENDER-EFFECTS-025

Offline/static only. The original-instruction proof uses pinned text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` and data SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, plus the existing flag/feature pins
for complete RenderObjDraw streams. Native renders compare native states; they do not establish original-client
pixels, pose or process-state identity.

### Hammer14's exact-name failure and the unchecked sprite index

The original loader copies all 32 bone-name bytes at `0x012b4276..0x012b4287`, through memcpy at `0x012b4282`.
There is no name trimming in that copy. The installed Hammer14 finding from part 34 remains: bone 9 is `up01 `,
while the program requests `up01`. The exact search at `0x012bd35a` returns its fallback -1 at `0x012bd3b1`.

That is not the end of the original request. The bone sprite helper `0x0150e746` computes
`0x06fce398 + bone * 0x30` at `0x0150e782..0x0150e78b`, with no negative-index test. It calls TransformPosition
`0x012b6ef1` on that matrix, local `(0,0,0)`, translate 1, and then CreateSprite at `0x0150e7bf`.
For -1 the matrix starts at `0x06fce368`, immediately before BoneTransform. This is an observed original
out-of-domain read, not evidence that `up01 ` matches `up01` or that bone zero is the right substitute.

The `up01` call itself has scale zero. At `0x017d9a54..0x017d9a58`, `xorps` and `movss` push zero
for scale before the call at `0x017d9a6e`. Its bone index comes from local `-0x13c4`.
The following `up02` call also uses zero scale. Restoring the missing-name request therefore adds a sprite
allocation and transform, but no visible area. The native before/after PNG identity is expected for this call;
changing its scale to make it visible would change the recovered original behavior.

The preceding storage is process bookkeeping. Static references identify the float clock at `0x06fce370`,
a path-service object pointer at `0x06fce374`, and a tick word at `0x06fce384`. The latter two occupy translation
words when that storage is read as a matrix. Reading a native pointer or the previous native bone allocation
would neither recover those original words nor provide a bounded native operation.

The host therefore supplies this record explicitly, through `item_before_transform`. Only the -1 bone-sprite
case may use it. NULL retains the refusal; other negative indices, oversized bones, missing ordinary poses and
invalid dependent positions keep their bounds. `mu_renderchar_env.item_before_matrix` supplies all twelve words
separately from the pose allocation. The default native record is zero, so that state places the missing-name
sprite at the model origin through the existing TransformPosition arithmetic. A fixture can provide a nonzero
record or NULL. This default is declared native compatibility state, not a recovered original process record.
No bone names, assets or model choices change.

`validate_render_effects25` compares 1,000 complete Hammer14 RenderObjDraw streams with the exact-name failure,
zero and arbitrary nonzero finite pre-bone records, varied scale/origin, posed matrices, item states, counter
values and hidden frames. Requests, body draws and rand consumption must match. Unlike the earlier bounded
refusal check, this comparison requires the fallback sprite's position and arguments, with zero refusals.
The native host separately checks the default record, nonzero translations, NULL refusal and the real native
item draw adapter. Portable tests retain the -2 refusal and the prior short-skeleton bounds.

### Clouds/28

`reconstructed/particles/ferea_clouds.inc` follows CreateParticle `0x015edeaf..0x015ee200` and MoveParticles
`0x0166200c..0x016623c3`. Common initialization, velocity movement, owner-position handling and lifetime
retirement remain shared.

Create sets lifetime and initial lifetime to 300. Two `0x011ff622` calls select x/y displacements from
`[-250,250]` with ten quantization steps, then multiply by input scale. Start copies the displaced position.
Scale is a quantized `[0.5,1.5]` times input scale; rotation is a quantized `[0,360]`; alpha starts at zero.
Input light and angle remain unchanged.

Move computes the alpha pulse as `(cos(((1-life/initial)*360+180)*degrees_to_radians)+1)*0.5`.
It selects speed `[0.3,1.3]` with ten steps. The temporary center adds
`sin(WorldTime * 0.00019999999494757503f) * speed` to current y, then the original vector helper's operations
rotate that center offset by angle z around the current position. Preserve center construction and subtraction:
the intermediate binary32 addition can round the displacement before the rotation. Rotation increases by 0.7.
Render multiplies light by alpha, as the original later cloud branch does. The existing cloud bitmap is reused.

### The next measured groups, two bow pairs

The expanded installed scene covers 96 admitted item programs in twelve eight-wearer batches, sixteen consecutive
draws each. Two newly admitted bow groups add particle pairs absent from part 32's 93-program census.
The remaining unsupported requests in this fixture are five in the batch containing `0x1313`, and seven in the
batch containing `0x1317`/`0x1319`. Static request evaluation has no unresolved bitmap expression and identifies:

| Pair | Programs | Create / move | Behavior |
|---|---|---|---|
| `0x8109/7` | `0x1313`, `0x1317` | `0x015afd35` / `0x01618ab4` | Lifetime 10, saved initial scale, random rotation and quantized input velocity; scale = initial scale * life ratio, one rand-selected velocity component damped by that ratio |
| `0x810a/9` | `0x1319` | `0x015b1605` / `0x0161acd9` | Lifetime 12, saved initial scale, random rotation; scale grows by 0.035 above half life, shrinks by 0.035 otherwise, clamps at zero |

The first velocity range is `[-2.5,2.5]` with one quantization step. The helper truncates the multiplied bounds
before modulo and division; replacing it with an arbitrary continuous range changes the client behavior.
Both particles retain the original common advance and existing bitmap/render paths. Their create/move/render
record words, ordered calls and random consumption are compared against the pinned instructions.

The proved static census is 96 programs / 32 distinct pairs, all with native consumers,
zero unresolved bitmap expressions. The validator freezes those 96 program identities and also reports the full
current inventory. Main's later part 36 adds fourteen programs, making 110 programs / 37 pairs. Five new pairs
remain refused: `0x810a/12`, `0x81cf/1`, `0x810b/8`, `0x8500/2` and `0x8569/0`. Their callers and next steps are
in the handoff. They are outside the 96-program before/after fixture and are not counted as ported here.
The installed scene changes 7,389 accepted / 28 refused requests to 7,416 / zero; unsupported particles 12 to zero.
New particle rand calls alter later gated requests, so the two scenes do not have equal request denominators.
Eight maces separately change 5,610 / 61 to 5,671 / zero over 61 draws at both clocks. Their saved final PNGs are
identical, consistent with the additional sprite's original zero scale.
Closer Ferea creates 257 particles / zero unsupported versus 243 / 14 and changes the final native images.

The focused proof has 10,002 component comparisons, zero mismatches; 24/24 compiled mutants are caught.
Checks, timings, affected rows, rendered differences and limits are recorded in
[RENDER-EFFECTS-025](../handoffs/RENDER-EFFECTS-025.md). The default zero pre-bone record, original process phase,
pose and unsampled requests remain explicit limits. Installed Preview and Wine apps are untouched.

## Part 39, five later item particle consumers, RENDER-EFFECTS-026

Offline/static only. Original instructions use pinned text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` and data SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Native before/after images establish native visibility and regression behavior, not original GPU pixels.
Part 38 belongs to the independent RENDER-ITEMS-002Y lane.

The five pairs left by part 37 now have native create, move and render consumers. The two new bitmap
registrations follow original LoadBitmap `0x0185baac` calls, with LINEAR/CLAMP and flags 1/0:

| Pair | Create branch | Move branch | Render branch | Later callers |
|---|---|---|---|---|
| `0x8500/2` | `0x0160d351` | `0x01685e1b` | `0x015a9b9a` | `0x23a8`, `0x23a9` |
| `0x810b/8` | `0x01601dca` | `0x0167be27` | `0x015a0fce` | `0x23a8`, `0x23a9` |
| `0x810a/12` | `0x015b1a73` | `0x0161b036` | `0x0159faca` | `0x0f1e`, `0x174a` |
| `0x81cf/1` | `0x0160baa3` | `0x01684277` | `0x015a5eec` | `0x2301`, `0x2302` |
| `0x8569/0` | `0x01610b2d` | `0x016896de` | `0x015aa1a0` | `0x23a8`, `0x23a9` |

`0x8500` loads `Skill\wing_hetachi2.jpg` at `0x01827a23`; native file `Data/Skill/wing_hetachi2.OZJ`.
`0x8569` loads `Effect\Damage_ring_2.jpg` at `0x01825e21`; native file `Data/Effect/Damage_ring_2.OZJ`.
The three other bitmaps already have native slots. Two slots are appended before Fire06 and the rain
textures, preserving prior non-tail slot indices. The effect-file count now derives from the full count
minus the two rain slots. The new constructor/mover code is isolated in `item_later_kinds.inc`.

### Record behavior

`0x8500/2` lives rand % 11 + 20 steps. Scale keeps the input; initial scale stores input / lifetime.
Rotation is a quantized [0,360] draw. Record word `+0x84` stores a quantized [-20,20] spin, not a saved
start-angle component. Velocity x/y use [-2,2], z uses [-2,0.8], with 100 quantization steps. Below half
life it subtracts initial scale from scale, and every step subtracts 1 / initial lifetime from alpha.
Rotation adds the saved spin. Velocity then adds quantized x/y [-0.2,0.2], z [-0.2,0.1] jitter.

`0x810b/8` lives 25 steps. Initial scale is input / integer half-life, therefore input / 12 rather than
input / 12.5. It saves random rotation and three quantized [-1.2,1.2] velocities. Below integer half-life
it subtracts the saved initial-scale word from scale; each step subtracts 1 / initial lifetime from alpha.

`0x810a/12` lives 20 steps. Its quantized [0.5,1] scale multiplier is saved as initial scale. It saves
random rotation, displaces each position component by a quantized [-10,10] draw and gives each velocity
component a separate draw from that range times 0.2. Each step subtracts initial scale / initial lifetime
from scale and 1 / initial lifetime from alpha.

`0x81cf/1` shares subtype 0's constructor but has its own compared movement branch. It lives 20 steps,
starts at scale zero, saves input scale and starts alpha at one. A NULL owner clears live. Otherwise
scale grows by saved scale / initial lifetime, and below integer half-life alpha falls by 1 / half-life.
There is no new position-follow operation for this pair.

`0x8569/0` lives 30 steps, starts scale zero and saves input scale. A NULL owner clears live during move.
On subsequent steps, once life is below initial life, alpha falls by 1 / initial life. Scale grows by
saved scale / initial lifetime. Its render branch, after the original height filter, copies the selected
OBJECT `+0x1f4 + 12*arg8` point into position when an owner exists. Unlike `0x810a/0x25`, it adds no saved
start offset. A NULL owner leaves position alone in render. The native owner table supplies points 0..3 for
this pair; older consumers retain their 0..2 bounds. Unknown, stale or out-of-domain native owners retain
a refusal/retirement rather than an out-of-bounds read.

The original caller refreshes all four points every draw. In particular, `0x017cd01f` writes `cr002`
to OBJECT `+0x218`; `0x017cd025..0x017cd0f0` gates four particle requests on counter % 25 == 0.
The older generated program exported only nine point words. The effect consumer now exports the fourth
transform's three words too, for the two frozen wing programs at destination r305 / bone register r16.
The item tables and generator are unchanged. A coupled original comparison observes all twelve words and
the complete request streams, including draws away from the 25-counter gate. The native adapter checks
that point 3 follows changed poses on ungated frames 24 and 26. Legacy validator families keep their
explicit nine-word view; this lane opts into all twelve words and tests index 3 in the render comparator.

All five render the current light times alpha, using the existing sprite renderer and blend selection.
Common initialization, moving-vector rotation, terrain-backed owner-position reads, lifetime decrement,
frame-time accumulation and head retirement remain shared. No authored scale, model or bone name changes.

### Proof and census domain

`validate_render_effects26` compares the original constructors, movers and complete ordered RenderParticles
calls against production C, including owner/null cases, random consumption, half-life boundaries, split-height
passes, blend modes and all four saved OBJECT points. Undefined memory accesses remain machine failures.
The native host separately checks exact bitmap mappings with distinct synthetic greys, allocation, stepping,
positive raster fragments for every pair, changed owner points, stale-owner retirement and full pool retirement.
The 110-program / 37-pair domain is frozen by identity, while later inventory additions remain reported.

The full focused run passes 17,008 checks, including 16,640 cases against original instructions. All 37 compiled
mutants are caught without original-machine stops. The bounded sixteen-draw installed scene reduces pre-draw
refusals 122 to zero; both longer clock fixtures reduce 485 to zero. One exact model path remains unavailable.
Scene results, wall times and remaining fixture limits are recorded in
[RENDER-EFFECTS-026](../handoffs/RENDER-EFFECTS-026.md). The scene census uses installed models and explicit demo
records; it does not establish equipment eligibility or cover every counter phase, context or world producer.
An absent exact authored model path is recorded as unavailable, without name trimming or an asset substitution.
No live client, protection analysis, network state, character-power feature or client-memory write is used.
