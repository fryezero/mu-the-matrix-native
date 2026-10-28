# Inventory item special cases, RENDER-ITEMS-002 part 1

This PR covers RenderItem3D's restored special-code chain and its native inventory integration.
The 1,674 RenderObjDraw type branches, RenderLinkItem's effect switch, their character/ground integrations,
and Muun/map-object effect placement remain for later parts. Nothing here starts or reads a live client.

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
