# Offline capture and inventory follow-ups

FOLLOWUPS-001, offline/static only. The client provenance is the pinned target in
`docs/evidence-index.json`; inventory instruction evidence remains
[part 24 of client-render-items](client-render-items.md#part-24-the-inventorys-equipment-and-its-icons-effects-inventory-fx).
No live client or installed application was used.

## Capture alpha

The window's framebuffer alpha is not display opacity. Character select, the frame-loop window and software
frame tool, the GFx prototype and the model/terrain viewer now save with `mu_png_write_opaque`. The PNG colour
channels and raw framebuffer report hashes keep their original meaning. Asset, sprite and effect exporters retain
alpha. GFx prototype captures also allocate a buffer in windowed mode and read before swapping; that path previously
passed NULL to the writer. Its standalone Makefile lacked the three mu_perf functions the layer uses, so it now
compiles mu_perf.c.

## Inventory sprites

The standalone `mu-render ui inventory` still had the per-icon particle pool removed from the in-app inventory
by INVENTORY-FX. It drew the 0x389c/0x389d skin sprites immediately over the icon. It now draws the item mesh and
its material/effect passes only. The original CreateSprite list is drawn by a world scene's RenderSprites, not by
the inventory render. A standalone tool has no world in which to keep those off-scene sprites.

The CLI's frame remains its documented stand-in panel. This change does not claim to reproduce the GFx artwork
or add equipment input to that tool. The in-app equipment pass is reused for the accessory fixture below.

## Equipment slots 9 through 14

Static evidence: original InventoryFrame's `Common.Global.MUDefines` defines these constants, and its
`InventoryFrame.onLoad` calls `InitEquipeSlot` for the corresponding named clips. `InitEquipeSlot` reports x, y,
width, height and the slot index via `EQUIPrequestSlotInfo`. The original controller/render loop is already
instruction-compared by validate_inventory_fx (`0x00b958e1`, `0x00b913a2`). The installed Item.bmd's +0x256 slot
metadata uses an alternate index for pentagrams and earrings.

| Movie slot | Original name | Item.bmd slot | Authored fixture code | Model |
|---:|---|---:|---|---|
| 9 | AMULET | 9 | 13:12 = 6668 | necklace01.bmd |
| 10 | RING_RIGHT | 10 | 13:8 = 6664 | ring01.bmd |
| 11 | RING_LEFT | 10 | 13:9 = 6665 | ring02.bmd |
| 12 | PANTAGRAM | 236 | 12:215 = 6359 | penta02.bmd |
| 13 | EARRING_RIGHT | 237 | 12:457 = 6601 | so_neck02.bmd |
| 14 | EARRING_LEFT | 238 | 12:449 = 6593 | so_neck.bmd |

The spelling PANTAGRAM is the movie's own. Left rings share the right-ring Item.bmd slot tag. The movie also
names `CHARACTER_EQUIPMENT_PANTAGRAM_CLIENT_INDEX=236`. These are static observations, not inferred slot names.
The fixture choices and level 0 / option 0 / ext 0 are authored demo values, not recorded owner equipment.

`--gfx-open inventory,equipment-demo` explicitly enables these six records. The host accepts a fixture entry only
when its Item.bmd slot tag matches and its model file exists, otherwise leaves that slot empty. Regular scene
runs retain their existing empty accessory slots. The records go only to the inventory's draw list, never to
session equipment, stats, combat, skills, character mesh parts or persistence.

## Frame-zero instability remains open

The README-IMAGES-D scene reproduced the defect in four runs: three distinct raw frame-0 hashes. A smaller
HUD-only view reproduced it as well, changing 35 or 56 pixels, x 344..842 / y 723..798. Four logged runs had identical
bridge logs but different PNGs, so a different sequence of C-to-movie calls is not needed to trigger it.

Static ActionScript: Frame.Main.setHPMP feeds RodGauges.setValue, which schedules a 0.2-second Tweener width/x
transition; Tweener.updateTime uses getTimer. The canonical private environment's libmugfx is the October 22 build.
A synthetic movie with MU_GFX_TEST_CLOCK=1 returned getTimer 18 then 69 ms across a 50-ms host wait, with no player
advance. Thus this library does not implement the source tree's patch-0008 clock. The same variable cannot freeze
its tweens. That is a verified runtime capability gap; attribution of every differing pixel to it still needs the
rebuilt-library comparison.

The source already contains the opt-in clock and Ruffle patch 0008. Rebuilding that dependency and checking its
runtime integration is larger than these capture/fixture edits, so it is left under Next. `test_followups.FrameZero`
first probes the actual library, explicitly skips the unsupported legacy runtime, and, with a clock-capable
runtime, requires four complete scene starts to produce byte-identical frame-0 PNGs and raw hashes. No deterministic
frame-zero claim is made by this milestone.

Movie/file SHA-256 values and measured checks are in [the handoff](../handoffs/FOLLOWUPS-001.md).
