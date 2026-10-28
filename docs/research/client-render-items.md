# Item rendering, RENDER-ITEMS-002

Part 1 covers RenderItem3D's restored special-code chain and native inventory integration.
[Part 2 below](#part-2-bounded-body-and-link-effects-render-items-002b) adds 103 scalar remaps,
11 body types and six bow link effects. [Part 3 below](#part-3-body-clusters-and-offset-links-render-items-002c)
raises body coverage to 262/1,674 and records exact remaining branches.
[Part 4 below](#part-4-armour-weapons-skins-and-spark03-render-items-002d) raises it to 426/1,674, adds
eleven skins and consumes Spark03/11. Muun/map-object effect placement remains deferred. All parts run offline.

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
