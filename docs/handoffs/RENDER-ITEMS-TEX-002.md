# RENDER-ITEMS-TEX-002

Follow-ups of RENDER-ITEMS-TEX-001. [Finding, addresses and survey](../research/client-render-items-tex.md#render-items-tex-002-upload-parameters-texturetype-and-the-wearers-skin).

Branch `claude/render-items-tex-002` (Claude Opus 5.5), worktree `~/Documents/MTM/worktrees/render-items-tex-002`, from
origin/main `3021799a`. Input links `tools/python` and `evidence` come from the main checkout and are never committed.
No live game, network or session code. The body executor, its tables and the generator in `renderchar.c`
(RENDER-ITEMS-002 part 12) are untouched.

## What changed

1. **Item upload parameters (GL_CLAMP).** The item loader uploads with GL_NEAREST, GL_CLAMP: LoadImage `0x00c97689`
   called at `0x00cd5b50` and for both `field_` loads. A name-map hit reuses the bitmap as it was first loaded
   (`0x00c97730` only counts a reference). Native now does the same:
   - `mu_texture_names` keeps one entry per loaded file with its filter and wrap. LoadImage keys its loads by full
     path (`0x00c97d69`), and name lookups still return the first file of a name.
   - The startup LoadBitmap names carry their filter and wrap (`mu_startup_bitmaps.inc`, regenerated).
   - `mu_item_textures` gives each slot the parameters of the bitmap it keeps.
2. **The wearer's skin.** RenderCharacter's part loop stores `0x0139d6a2(class byte)` at each part model's `+0xa4`
   (`0x0136a4bd`). The item loader leaves 0 (memset `0x00cd5623`). The mesh draw binds skin IndexTexture + `+0xa4`.
   Native:
   - `mu_it_part_skin` and `mu_it_skin_bitmap` (`reconstructed/objects/item_texture.{h,c}`) are the C steps;
   - the 146 registered skin bitmaps of startup routine `0x0182a8fe` are added to `mu_item_bitmaps.inc` (`--skins`);
   - `mu_item_textures_wear` writes `+0xa4` and loads its bitmaps;
   - `mu_textures.skin_shift` reaches the mesh draw through mu_scene.
3. **TextureType and `field_`.** `mu_textures.texture_type` (166 meshes) and `mu_textures.field` (`+0xa6`) reach the
   mesh draw through mu_scene. Other loaders leave them zero.
4. **In-world loaders.** These now reload by the item rule once their type is known, through
   `mu_item_textures_character`, `mu_item_textures_reload` and `mu_item_textures_type_of_path`:
   - the hero's parts and equipment (`world_rt.c`) and the combat weapon;
   - players (`mu_world_players.c`) and Player-model NPCs (`mu_world_actors.c`);
   - the actor tool's weapons and the +15 attachments (`mu_render_world.c`);
   - the helpers' Angel/Imp models and Imp link (`mu_world_helpers.c`);
   - plain `mu-render character` (`mu_render.c`).

   Part slots wear the character's class byte.
5. **Wearer inputs.**
   - `mu-render ui inventory --wearer CLASS` (authored);
   - the in-game inventory uses the demo hero's class (`wg_items_set_wearer`, authored);
   - `mu-render character` uses `--class`;
   - ground items keep `+0xa4 = 0`.

## Untextured survey (real renderer, installed data, 48 states per type)

| | TEX-001 (origin/main) | TEX-002, `+0xa4 = 0` | TEX-002, authored wearer |
|---|---:|---:|---:|
| Types with a white pass (of 1,691) | 94 | 28 | 15 |
| Implemented bodies + skins with a white pass (of 984) | 82 | 27 | 15 |
| White passes / passes | 8,136 / 525,732 | 2,832 / 514,842 | 1,920 / 514,842 |

- **With a wearer:** the 15 left are the index-0 body draws (RENDER-ITEMS-002).
- **At `+0xa4 = 0`:** 13 armour types also stay white on hair meshes, because 0x7776 and 0x78ba are not registered
  at index 0. This matches a client model nobody has worn.
- **Passes:** they fall by 10,890 because typed meshes stop drawing where the body writes `+0x40 > 0`.

## Hash changes (intended)

Base `3021799a` `mu-render ui inventory` against this branch, installed data:

- **Control unchanged.** Codes 0,1,2,3,7,8 (162 triangles) stay `df03a290…4930`.
- **Code 28** (`0x0b02`): `b079bc2b9568…` → `4840410d6544…`, TEX-001's prediction. Its slots go from REPEAT to CLAMP;
  `gra.jpg` now loads `Data/Item/texture/gra`, which has the same pixels.
- **002K gallery** (28, 2711, 4305, 4398, 7333, 3103; 3,432 triangles): `d537b52f…d25d` → `4717b4d6…a9e8`.
- **TEX-001 gallery** (29, 32:+9, 4416:+11, 4191, 3608, 6144): `057bf46a…5526` → `c879a0d8…d00a`, and triangles
  10,495 → 10,405.
- **Changed items:**

  | Code | Type | Before → after | Why |
  |---|---|---|---|
  | 4305 | 0x1bb7 | `e6c97118085a` → `7bf652efa223` | `eyejam_R` now from `Data/Item/texture/` (full-path rule); CLAMP |
  | 4398 | 0x1c14 | `4fe6115d2f75` → `fa89c3d81af5` | skin mesh binds 0x77c7 `HQSkinClass101` (`+0xa4 = 0`); CLAMP |
  | 3608 | 0x18fe | `a188407b16fd` → `4ae2b46dd2e6` | `level_man033` binds 0x7725 `skin_barbarian_01`; CLAMP |
  | 4416:+11 | 0x1c26 | `44a90a9efe97` → `7a1c4b760a0f`, 8,267 → 8,177 tri | `nude_Item1161` (TextureType 1) not drawn, `+0x40 > 0` |

- **Unchanged items** (CLAMP only, texture coordinates inside the image): 2711, 7333, 3103, 29, 32:+9, 4191, 6144.
- **Per mesh slot** (survey):
  - 4,576 of 4,652 textured slots in 1,623 types go REPEAT → CLAMP;
  - 4 name-map slots go NEAREST → LINEAR;
  - 72 slots draw the `Data/Item/texture/` copy: `eyejam_R` 33, `alpha_line2` 17, `fire_15fmono` 16,
    `flame_chrom` 2, and 4 others.
- **`mu-render character`:**
  - classes 0x00, 0x02 and 0x11 alone are unchanged, because the class parts' skin meshes bind the file of the
    same name;
  - with `--part 1 Data/Item/HelmMale25.bmd`, the helm goes from 4 missing textures (white) to textured. The face
    takes 0x7725 for class 0x00 (`c8735ab6dca7` → `4e59b9ddecef`) and 0x7736 `level_man01` for class 0x11
    (`5091dbcb976f` → `64106c03c92b`).
- **Not item textures, unchanged:** `mu-render render` of `Object1/Beer01` (`5ffbef41…`) and `Monster/Monster01`
  (`50fd644c…`). The world name-map tests (`test_native_worlds_g2`) pass public and private. World object lookups
  still answer with the loaded file.
- **Inspected crops:**
  - 28: the blade's edge strip changes slightly;
  - 3608: the white face is now textured;
  - 4398: the white chest patch now shows the HQ skin;
  - 4416:+11: the nude mesh is gone;
  - the helm on the character: white before, textured with the class face after.

## Checks

- `scripts/validate_item_textures.py --cases 1000 --mutations` (`MU_SECTION3` = capture-04 section 3), five families
  with zero mismatches and zero stops:
  - item_open: 1,000 cases;
  - registrations: 235;
  - startup_names: 1,402;
  - part_skin: 256;
  - skin_bitmap: 3,072.

  That is **5,965 cases**, and **22/22 compiled mutants** are caught (6 new). `scripts/validators.toml` is updated
  (cases 5,965, mutants 22).
- `reconstructed/objects/test_item_texture.py`: 5 portable tests + 1 private.
- `native/tests/test_native_item_textures.py`: 4 synthetic tests (new: GL_CLAMP, TextureType and the wearer skin) + 1
  private installed survey (before/after and `--wearer`).
- Native suites `test_inventory_skin`, `test_native_hud`, `test_native_items`, `test_native_renderchar`,
  `test_native_character`, `test_native_gfx2/3`, `test_native_worlds_g2`, `test_native_helpers`,
  `test_native_players`, `test_native_actor` and `test_native_combat`: 105 tests pass public. The private run
  (`MU_GAME_ROOT` = the installed client) passes except `test_native_combat.InstalledTests.test_lorencia_fight`
  (`models_loaded` 21 ≠ 9). Base `3021799a` fails the same way, so it is not from this lane.
- Gate and private validators on the merged tree: see the PR body.

## Limits and next steps

- **`field_` second bitmap.** With `+0xa5` set, the draw binds IndexTexture + 1, the second file of a `field_` name.
  Native item draws never set `+0xa5`, and native does not upload that second file. It is a limit, not a pixel change
  today.
- **The wearer is authored** for inventories: a CLI option, the demo hero, or the survey's `require_class` choice.
  The client's value is the last character that drew that model. In-world characters use their own class byte, as
  the client does.
- **Path-only loaders.** The hero's equipment and `mu-render character` take the item type from the first record
  that names the model file. Records that share a model file get the first record's type.
- **Name-map history.** The order between startup models and startup LoadBitmap files is not rebuilt, as in TEX-001.
- **Index-0 overrides** (15 types) belong to RENDER-ITEMS-002.

## Coordination

The executor, body tables and generator are untouched. Shared files have small edits:

- core: `mu_scene.{c,h}`, `mu_textures.{c,h}`, `mu_texture_names.{c,h}`, `mu_world_players.c`, `mu_world_actors.c`,
  `mu_world_helpers.c`;
- world: `world_rt.c`, `world_rt_internal.h`, `world/parts/combat.c`, `world_gfx.c` (one line),
  `world_gfx_game.{c,h}`;
- tools: `mu_render.c`, `mu_render_world.c`, `mu_render_hud.c`;
- `reconstructed/objects/Makefile` (links `model-codec/character.c`) and `scripts/validators.toml` (the row's
  counts).

On conflicts keep both sides.

Local files: renders and scratch under `~/Documents/MTM/mu-mac-tools/native/{renders,scratch}/render-items-tex-002` and
the temporary base worktree `worktrees/rit2-base` are deleted at the end. No later lane needs them as input.
