# INVENTORY-FX

Branched from `origin/claude/render-items-002t` (`53b9f7e7`, #341). Merged main `035c1964` (#338) as `af0ac2a9`
before any change, then main `138b756e` (#339, #340, #341) as the merge after `461a2e4a`. Branch/worktree
`claude/inventory-fx` (Claude Opus 5.5). No live client, launcher, installed app, network or hosted workflow. No
full gate in the lane (2026-11-04 test budget).

Scope: inventory and equipment icons drawn the way the client draws them in its inventory window.
[Finding](../research/client-render-items.md#part-23-the-inventorys-equipment-and-its-icons-effects-inventory-fx).

## Result

| Question | Answer |
|---|---|
| Level glow in the inventory | yes. It was already on for grid items. Now the hero's equipment draws too, e.g. Ironclad's Cookery Short Sword +9 |
| Excellent pass | yes. RenderObjectScreen's excellent flag and set bits now reach the item render (`mu_icon_glow_of`); before, ext was never passed |
| Per-icon pre-draw | yes, as the client runs it. The program runs on the icon's pose with the TestFrustrum2D flag at the icon's screen position; its sprites join the world's list. The client draws none over the icon, so neither does native |
| Character select levels | no. The levels would come from the character-list handler's equipment decoding (packet data, out of scope); the native charsel also draws plain meshes |

### 1. The hero's equipment in the inventory window (new)

The native inventory showed only the 8×8 grid. Its fifteen equipment slots stayed empty because the movie's
`EQUIPrequestSlotInfo` callback was ignored. The client's inventory item render `0x00b913a2` draws the grid
(slot pass `0x00ab6130`), then every equipped ITEM. Those are CharacterMachine `[0x01d1df18] + 0x1b58 + s·0x12c`,
s = 0..14, drawn through the slot wrapper `0x016c23d5` at the rectangles the movie reported (`0x00b958e1`). The
armour slot is 0.75 high for class nibbles 2/5/7/8/9/12/14 (`0x00b99205`).

- `reconstructed/hud`: `mu_equip_slot_info`, `mu_inventory_item_pass`, `mu_equip_short_armour`.
- `mu_gfx_layer` keeps the rectangles and the hero's ITEMs (`mu_gfx_layer_set_equipment`), and appends the
  equipment draws after the grid's.
- `world_rt.c` hands it SetCharacterClass's ITEMs 0..8: APP-POLISH-008's session records, or a file's first
  record at level 0.
- Ironclad (demo session) shows Cookery Short Sword 0:68 +9 excellent, Small Shield +7 and Wings of Heaven.

### 2. Level, option and ext (the excellent pass)

RenderPartObject passes RenderObjectScreen's level word, excellent flag and set bits unchanged as RenderObjDraw's
arguments 5..7 (`0x017e7932..0x017e7960`, `0x017e796a..0x017e7997`).

- `world_gfx_game.c` now takes all three from RenderObjectScreen's outputs (`mu_icon_glow_of`: level
  `(word >> 3) & 15`, option, ext). Before, the level came from the layer's own field, which ignored kind A
  `0xc`'s zero word, and ext was never set.
- Grid items with a level kept their glow. The demo inventory (Blade +9, armour +7/+11/+7, shield +5) is
  pixel-identical before and after (below).

### 3. The icons' pre-draw programs and skin sprites

RENDER-ITEMS-CALLERS-001 and HERO-ITEMS-001 named `0x00a497c6`/`0x00a49bc9` the inventory's RenderObjDraw callers.
They are not: both lie in `0x00a49266`, the render callback `0x00a16273` registers for object type `0x67a` at
`0x00a13f54` (it draws a character's parts on another object). The inventory reaches RenderObjDraw like a ground
item: RenderItem3D → RenderObjectScreen → RenderPartObject.

- The pre-draw case runs on the icon's own pose.
- Its flag is TestFrustrum2D at OBJECT `+0x158`, which for an icon is its screen position. Screen position / 100
  is the map's corner tiles, so the flag is almost always clear.
- Gated programs skip their case (Cookery Short Sword `0x0b2a`, Floor Hammer `0x0f1c`, Floor Shield `0x1748`);
  ungated ones create (Xeno Blade `0x0b4c`, wings `0x230b`/`0x2311`).
- CreateSprite only appends to the global list. RenderSprites `0x0169270e`, its only drawer, is called from the
  three scene renders alone. So the client draws no item sprite over an icon: the world draws them with its
  camera, at the icon's screen coordinates read as world units, under the map corner.

Native:

- `wg_items_set_world` gives the icons the world's particle lists and `world_rt_item_pre` (new caller
  `inventory`, owner key per icon).
- The skin sprites of `0x389c`/`0x389d` go there too. RENDER-ITEMS-002D's per-icon pool, which drew them over the
  icon, is removed (an inference the client contradicts). `test_inventory_skin` now asserts the opposite: the icon
  images are identical with and without the sprite texture, at every clock, with and without a world, and with a
  world the pool receives one sprite per draw.

Scenes (`mu-world` GL 1280×800, Lorencia 140,130, class 1, `--gfx-open inventory`, 30 frames, APP-REFRESH-006
Native Data and libmugfx):

| Scene | `item_pre_draw` inventory: created / refused / flag clear | `sprites_created` (world) | `rand_calls` (world) |
|---|---|---:|---:|
| Ironclad's three records | 0 / 0 / 2 (the sword's gated program skipped) | 8, before and after (the worn sword in the world) | 15,347 = before |
| Grid `mixadd` Xeno Blade +11 and Floor Hammer +9 | 7 / 0 / 2 (Xeno ungated, Hammer gated) | 0 → 7, of which 0 drawn (off view) | 15,347 = before |

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` plus `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang`,
`MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin` for the validators. Scenes and private tests also use
`MU_GFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib` and
`MU_LANG_DIR=$MU_NATIVE_DATA_DIR/lang`. Every heavy step ran under `nice -n 10`, with `make -j4` and `--jobs 2`.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` (+ `make -C native world`) | pass, no warnings | 31.8 s |
| `validate_inventory_fx` with mutants (new row, `run_validators.py --private --cache --only`, at `d06ca841`) | 8,017 cases, 0 mismatches: equip_pass 3,000, equip_info 1,000, part_args 1,000, inv_flag 3,000, sinks 17. **14/14 mutants caught** (75..2,605 detections each), all compiled, every anchor once | 67.9 s |
| `validate_inventory_fx` again, no mutants, at `07be3aae` (its flag-library list made literal for the affected analysis) | 8,017 cases, 0 mismatches | 6 s |
| `run_validators.py --private --no-mutants --cache --only <19 rows> --jobs 2` (at `d06ca841`) | 19 pass (table below) | 150 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, at `d06ca841`) | 8 suites, 1,423 tests: native/tests 909 (0 failures), reconstructed/* 0 failures, `tests` 5 failures in `test_affected_inputs`. My new row's flag-library list could not be derived, so the analysis selected the row for every change; fixed in `07be3aae` | 379.6 s |
| `run_test_suites.py tests` after the fix (at `07be3aae`) | 274 tests, 0 failures, 42 skips | 59.0 s |
| `tests.test_affected_inputs` (at `07be3aae`) | 12 tests OK | 23.6 s |
| Private native/tests (private-env.sh, `MU_GFX_LIB`, Native Data lang): test_inventory_fx (new: 5 portable, 1 Unicorn, 3 scene), test_inventory_skin (GFx test rewritten), test_native_world_predraw, test_native_hero_items, test_app_polish8, test_app_polish6, test_native_gfx2, test_native_gfx3, test_help_layer, test_input_router, test_native_lang, test_native_social (6b: every module naming the layer's item draws, `gfx-open`, `item_pre_draw`, `--hero-item` or the skin host) | 109 tests OK. 12 skipped: they need an in-repo Ruffle build (`native/gfx/mugfx`) | 349.8 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.7 s |
| `scripts/audit_repository.py` | 2,080 files, 0 rejected | 23 s |

| Row | Cases | Seconds |
|---|---:|---:|
| `validate_hud` (symbol fallback) | 48 | 99.6 |
| `validate_movement` (symbol fallback) | 6,614 | 50.0 |
| `validate_app_polish4` | 10,485 | 31.3 |
| `validate_icarus_c2` | 8,400 | 25.5 |
| `validate_audio_domains` / `audio_callers` / `audio_items` | 2,544 / 5,528 / 3,000 | 25.3 / 6.9 / 4.7 |
| `validate_app_polish1` / `2` / `7` | 752 / 1,028 / 5,120 | 20.4 / 3.3 / 1.7 |
| `validate_worlds_fog` | 4,044 | 8.1 |
| `validate_render_effects17` (symbol fallback) / `16` / `18` / `19` | 618 / 424 / 540 / 400 | 7.0 / 3.4 / 1.7 / 0.9 |
| `validate_gfx3` | (pass/fail checks) | 4.7 |
| `validate_render_items` (symbol fallback) | 5,512 | 2.1 |
| `validate_item_callers` (label of the two `0x67a` sites corrected) | 6,013 | 1.5 |
| `validate_map_polish` | 876 | 0.5 |

`--list-affected origin/main` after `make` (at `d06ca841`, again at `07be3aae`: the same rows) selected 20 rows: the
19 above and `validate_inventory_fx`. Four are symbol-level fallbacks (render_items, hud, movement,
render_effects17). Twelve build a changed library but use no changed symbol (audio_charsel, audio_combat,
fidelity, meshdraw, model_edge, model_light, path, session_party, terrain, terrain_remaining, viewport_monsters,
worlds_f). Under 6b/8b no row was added by hand. `validate_fidelity`'s `object_screen` compares
`mu_hud_object_screen`, which is unchanged; the new functions in `item_slots.c` are additions.

## Renders and byte identity

- Window-only crops, before (main `138b756e`) | after, 2× nearest, frame 29, inventory window above the zen row,
  in `~/Documents/MTM/mu-mac-tools/native/renders/inventory-fx/`:
  - `ironclad-cookri-9-excellent-equipment.png`: the empty equipment slots now hold the sword, shield and wings;
  - `grid-xeno-blade-floor-hammer.png`: identical, since pre-draw sprites never show on an icon.
- Control icons:
  - The grid region is byte-identical before/after in both scenes (frames 0 and 29). So is the 3D world.
  - Only the bottom bar's pulsing skill frame differs, and it also differs between two runs of the same base
    binary (GFx animation timing).
- October 22 tour (`fidelity_tour.py render`, default draw, `MU_LANG_DIR` = Native Data lang): 28/28 PNG, 28/28
  OBJECT/light dumps, 14/14 reports and logs identical. Wall before/after 30/23 s.
- DATA-ACQ-002: 64/64, 64/64, 32/32, 32/32 identical. Wall 61/58 s.
- README: 08, 09 and 23 show the inventory. Their hero (`mu-world`, Preview) wears class parts only, so no
  equipment slot fills, and the grid icons are byte-identical. No README image changes; nothing to re-pin.
- These are offline native renders. No original-client capture of an inventory with equipment exists.

## Limits

- Character select draws no levels (see the table above).
- Equipment slots the movie never reported are not drawn; the client would draw them at the frame origin with a
  size of 0. The equipment cursor test uses the slot rectangle, not the client's `0x00ec4bf2`.
- Slots 9..14 (pendant, rings, ...) have no offline record and stay empty. Equipping from the grid is not modelled.
- The level word's option/luck bits (`& 0x87`) do not reach the native item render, as for players.
- `mu-render ui inventory` (software tool) still draws skin sprites over its icons.
- Icon sprites are drawn by the next world draw. The client's order of the GFx pass and RenderSprites in one
  main-game frame was not traced (virtual call).
- Old notes in RENDER-ITEMS-CALLERS-001 and HERO-ITEMS-001 call `0x00a497c6`/`0x00a49bc9` the inventory path.
  The finding (parts 19 and 23) and `validate_item_callers`' label are corrected; the old handoffs are left as
  written.

## Release

Steward validators: validate_inventory_fx (new; ran with mutants at `d06ca841`, again without at `07be3aae`),
validate_render_items, validate_gfx3, validate_hud, validate_map_polish, validate_movement, validate_icarus_c2,
validate_audio_callers, validate_audio_domains, validate_audio_items, validate_app_polish1, validate_app_polish2,
validate_app_polish7, validate_app_polish4, validate_render_effects16, validate_worlds_fog,
validate_render_effects17, validate_item_callers, validate_render_effects18, validate_render_effects19 (ran at
`d06ca841`, after the `138b756e` merge, no mutants). Env: private-env.sh plus `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang`
and `MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`. Mutants: none needed besides validate_inventory_fx;
validate_item_callers changed only a label.

The next APP-REFRESH lane installs this: the demo's inventory then shows Ironclad's equipment.

Cleanup removes `mu-mac-tools/native/scratch/inventory-fx/` (the base worktree, its build, tour renders and run
folders) and this worktree's build directories. The two crops in `renders/inventory-fx/` are kept. The worktree
stays until the steward merges. No new input needs to be kept.
