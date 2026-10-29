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
Its rank-5 no-owner mesh streams draw; full owner effects remain open.
Part 9 reaches **769/1,674 bodies** and **fifteen link targets/twenty types**.
Part 10 reaches **880/1,674 bodies** and **seventeen link targets/twenty-two types**.
Part 11 reaches **967/1,674 bodies** with per-type wave/sine scalar programs; links are unchanged.
Muun/map-object effect placement remains deferred. All parts run offline.

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

