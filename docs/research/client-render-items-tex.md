# Item model textures and the item bitmap registrations (RENDER-ITEMS-TEX-001)

Native item bodies drew white where the client draws textures. The known case was the lit rank-5 body
(RENDER-EFFECTS-005, "Saturation"), whose blue overlays name bitmaps 0x84d9..0x84db. A survey of every item type
showed a much larger cause: natively, item meshes took their bitmaps only from the model's folder. The client never
looks there for an item model. [Checks and limits](../handoffs/RENDER-ITEMS-TEX-001.md). RENDER-ITEMS-TEX-002 applies
the upload parameters, TextureType, the `field_` flag and the wearer's skin bitmaps, and converts the in-world
loaders ([below](#render-items-tex-002-upload-parameters-texturetype-and-the-wearers-skin),
[checks](../handoffs/RENDER-ITEMS-TEX-002.md)). RENDER-ITEMS-TEX-003 registers every startup LoadBitmap call with
0x00c97730's re-registration rule and explains index 0 as object `+0x68`
([below](#render-items-tex-003-every-startup-registration-and-index-0),
[checks](../handoffs/RENDER-ITEMS-TEX-003.md)).

Inputs: the pinned text (capture 09), data (run 10) and section 3 (capture 04, CRT locale state) of
`scripts/pins.py`. Body hashes: `0x00cd558e..0x00cd5c91` sha256 `634484bf…da25`, GetModel `0x00eaa8cf..0x00eaaa3e`
sha256 `3793a9ea…c8b4`.

## How the client loads an item model's textures

**On demand (static).** GetModel `0x00eaa8cf(index)` looks the index up in the model map. On a miss with
`0 <= index <= 0x3af6`, it fetches the ItemModelFile record of `index - 0xae6` (`0x00cd4ea8` → `0x00cd5d29`). Without
a record it stores an empty model object. With a record it calls `0x00cd558e(index, record folder +8, record file
+0x10c)` and stores the result. So an item's model and textures load the first time it is drawn, not at startup.
The native record fields are the same (`mu_item.folder`/`file`).

**Per mesh (verified, `item_open`).** `0x00cd558e` returns 0 when folder or file is `"Empty"`. It opens the BMD
(`0x012b3812(folder, file, 1)`); a failed open shows "ItemModelFile does not exist". It then visits every mesh:

1. IndexTexture = `0x7530`, TextureType = 0, model `+0x40` = 0. The `_splitpath` extension is computed and not used.
2. path = sprintf(`"%sTexture\%s"`, folder, mesh name), into a 256-byte buffer.
3. TextureType, by `_strnicmp` prefix: `nude_` → 1, else `cotton2_` → 3, else `cotton_` → 2.
4. IndexTexture, first match (`_strnicmp` unless noted):
   - `skin_` or `level` → `0x7725`; `hid` → `0x791a`; `hair_` → `0x7776`;
   - `field_` (`strncmp`, case-sensitive): model `+0xa6` = 1 and `LoadImage(path)`. Then `LoadImage` of
     folder + `Texture\` + the name after `field_` with its last four characters replaced by `.tga`. The second
     result is dropped, and the message (if any) names the second path;
   - `HQskin_` → `0x77c7`, `HQskin3` → `0x7869`, `HQskin2` → `0x7818`, `HQskin`/`HQlevel` → `0x77c7`,
     `HQhair_`/`HQhair` → `0x78ba`;
   - anything else: `LoadImage(path, GL_NEAREST, GL_CLAMP)` (`0x00cd5b50`), whatever the extension.
5. If IndexTexture is still `0x7530`, the bitmap-name map is asked (`0x00c97e0c`, key = the mesh name). A hit
   reuses that bitmap (`0x00c97730(index, its file, GL_NEAREST, GL_CLAMP)`). A miss shows "ItemTextureFile does not
   exist : [file - path]" and leaves `0x7530`.

Unlike OpenTexture `0x0181fbe9` (RENDER-WORLDS-G2), there is no model-folder step and no `Data\Item\` or
`Data\Item\Texture\` retry. For the record folder `Data\Item\` the only file the client asks for is
`Data\Item\Texture\<name>`.

**Models opened at startup (static).** The special models `0x3890..0x38a7` are opened by AccessModel/OpenTexture in
startup routine `0x0182cd66`: subfolder `Item\`, except `0x38a2` with `Monster\`. The class parts
`0x3700 + part * 0x50 + n` are opened in `0x0182bb43` with subfolder `Player\`. These follow OpenTexture's order, as
in RENDER-WORLDS-G2.

**Bitmap overrides (verified, `registrations`).** The body executor names fixed client bitmaps by index, for example
the rank-5 blue overlays `0x84d9..0x84db` and `0x8239` (`black_gold_crom05`). They are registered by LoadBitmap
`0x0185baac(path, index, filter, wrap, 1, 0)`. A static scan of all 2,411 LoadBitmap call sites finds the
registration for 89 of the 90 indices the item draws can name. The scan probes all 1,691 survey types over levels
0..15, excellent 0/1, ancient 0/5/8, lit 0/1, four clocks and the rank-5 owner path. Each site holds one immediate
path. 88 sites are in routines the startup loader `0x0182049e` reaches by direct calls: 29 in `0x0182049e` itself
and 59 in `0x0182cd66`, called at `0x018282ce`. One is in the startup opener `0x01832af3`, which has no direct caller
(RENDER-WORLDS-G2). Examples:

| Index | Path | Filter, wrap |
|---|---|---|
| 0x84d9 / 0x84da / 0x84db | `Item\texture\Item1161_Blue_render.jpg` / `Item1162_…` / `Item1163_…` | LINEAR, CLAMP |
| 0x8239 | `Item\Texture\black_gold_crom05.jpg` | LINEAR, REPEAT |
| 0x800e | `Item\Texture\Gra3.jpg` | LINEAR, CLAMP |
| 0x7f20 | `Effect\bab2.jpg` | LINEAR, REPEAT |

The full table is `native/core/mu_item_bitmaps.inc`, with each site, its routine and its startup reach. Index 0
(named by 15 types' draws) has no registration.

**The name map at item-load time (verified, `startup_names`).** Every image LoadImage loads enters the bitmap-name
map under its lowercased file name, and the first load of a name wins (RENDER-WORLDS-G2). When an item first draws,
the map therefore holds the startup LoadBitmap files. There are 1,515 sites in startup routines with an immediate
`.jpg`/`.tga` path, giving 1,401 distinct names. Nine names are also loaded from a second folder; the first site is
kept. Four item meshes are answered only this way: `lightning2.jpg`, `lighting_mega03.JPG` and `hole.jpg`, which
are in `Data\Effect`. The list is `native/core/mu_startup_bitmaps.inc`.

## Unicorn comparison

`scripts/validate_item_textures.py` (registered `validate_item_textures`) has three families with zero mismatches
and zero stops:

| Family | Cases | What runs as client code |
|---|---:|---|
| item_open | 3,000 (default) | All of `0x00cd558e` on synthetic models: 7,299 meshes, 1,388 specials, 782 typed meshes, 238 field models; 6,156 LoadImage, 3,409 name-map, 1,093 reuse and 2,316 message requests. CRT strcmp, strncmp, `_strnicmp` and memset run as client code. sprintf (`%s`/`%d`), `_splitpath`, the std::string members, new, the BMD open and the bitmap services are stubs. |
| registrations | 89 | Each site of the 89 table entries, from its first push: path, index, filter, wrap and both flags equal the table. |
| startup_names | 1,402 | The name count, then each of the 1,401 names' sites, which must load exactly the listed path. |

All 16 compiled mutants are caught:

| Family | Mutation | Cases caught |
|---|---|---:|
| item_open | no `Texture\` | 1,191 |
| item_open | `nude` prefix (no `_`) | 17 of 400 |
| item_open | cotton2_ as cotton_ | 107 |
| item_open | `level_` instead of `level` | 35 |
| item_open | case-sensitive `hid` | 37 |
| item_open | case-insensitive `field_` | 35 |
| item_open | no `+0xa6` | 116 |
| item_open | no second field load | 116 |
| item_open | HQskin_/HQskin3 order | 42 |
| item_open | REPEAT load | 1,166 |
| item_open | REPEAT reuse | 416 |
| item_open | index-0 hit as a miss | 241 |
| item_open | no message | 765 |
| startup_names | a dropped name | 1,163 |
| registrations | a flipped wrap at 0x84d9 | 1 |
| registrations | a flipped wrap at 0x8239 | 1 |

The C step is `mu_it_open` (`reconstructed/objects/item_texture.{h,c}`), with OpenTexture's host type.

## Native use

`native/core/mu_item_textures.{h,c}` picks the rule per type:

- **ItemModelFile record:** `mu_it_open` against the rebuilt name map (`mu_texture_names_item`). Item lookups also
  consult the startup LoadBitmap names, but the object path is unchanged.
- **Startup special models and class parts:** OpenTexture with the subfolder of the startup call.
- **Anything else:** the model folder, as before.

Special mesh names keep the client's IndexTexture (`mu_textures.client_index`). mu_scene passes it to the mesh draw,
whose existing substitutions apply: `hide` meshes return before drawing, and skin indices take the model's skin
shift. The probed override indices are added as extra bitmaps from `mu_item_bitmaps.inc`.

The inventory (`mu-render ui inventory`), ground items (`mu_items.c`), the in-game inventory gfx
(`world_gfx_game.c`) and the character tool (`mu-render character`, once the item type is known) use it.

## Survey with the real renderer (installed data)

`native/tests/item_textures_host.c` loads every survey type as the inventory finds it and draws 48 states through
`mu_renderchar_draw_item` and mu_scene. It counts passes drawn with texturing on and no bitmap.

| Measure | Before (model folder) | After |
|---|---:|---:|
| Types with a white pass, of 1,691 (1,674 bodies + 17 skins) | 1,431 | 94 |
| Of the 984 implemented (967 bodies + 17 skins) | 859 | 82 |
| Meshes without a bitmap (special names excluded) | 4,138 | 0 |
| White passes / passes | 268,600 / 535,984 | 8,136 / 525,732 |
| Unresolved override bitmaps | not loaded | 15 (all index 0) |
| Meshes answered by the name map | — | 24 |

Passes fall by 10,252 because `hide` meshes are no longer drawn. 47 types have no model, as in the client:
42 have no record, 2 are `Empty`, and 3 name files that are not installed (`HelmMale160.bmd.`, `HelmMale162.bmd.`,
`HelmMale150_crusader.bmd`).

The 94 that remain:

- **79 types (67 implemented):** their only white meshes have special names (HQskinClass…, skin_Class…, hair_…,
  level_man…). The client binds the wearer's class skin bitmaps `0x7725 + shift` there. Native item draws have no
  skin bitmaps (character-skin domain).
- **15 types (15 implemented):** a body draw names bitmap index 0, which no LoadBitmap registers. These are body
  executor recipes (RENDER-ITEMS-002).

## Limits

- **Wrap mode, TextureType, `field_` flag, skin bitmaps and the in-world loaders:** applied by RENDER-ITEMS-TEX-002
  (below).
- **The name map's history.** Native rebuilds the startup models (RENDER-WORLDS-G2) and the startup LoadBitmap
  files. It does not rebuild the order between them, nor textures of items loaded earlier in a session.

## RENDER-ITEMS-TEX-002: upload parameters, TextureType and the wearer's skin

Inputs as above. New compared bodies (sha256 in the validator report): RenderCharacter's part-model store
`0x0136a4a9..0x0136a4c3` (`4830f3c5…291f`) and the mesh draw's skin substitution `0x012b8e78..0x012b9471`
(`b4076e4f…25bd`).

### Upload parameters (static; tables verified)

LoadImage `0x00c97689(path, filter, wrap)` first asks its full-path map (`0x00c97d69`). A path that is already loaded
keeps its bitmap and only gains a reference. Any other path gets a new bitmap index (`0x00c98211`), which
`0x00c97730(index, path, filter, wrap)` loads with the call's parameters. The name map keeps the first bitmap of a
file name. The item loader calls LoadImage with GL_NEAREST, GL_CLAMP (`0x00cd5b50`, and both `field_` loads). Its
name-map hit calls `0x00c97730` on the existing bitmap, which only counts a reference (`0x00c977a1..0x00c977e4`), so
the hit keeps the parameters of that bitmap's first load. Native now does the same:

- `mu_texture_names` keeps one entry per loaded file with its filter and wrap. Name lookups still return the first
  file loaded under that name. Before, a load of a new path whose name was taken returned the older file.
- Startup LoadBitmap files enter the map with their own filter and wrap. All 1,401 are immediate arguments: 934
  LINEAR/CLAMP, 251 LINEAR/REPEAT, 212 NEAREST/CLAMP, 4 NEAREST/REPEAT. The table `mu_startup_bitmaps.inc` now holds
  them, and the `startup_names` family checks all three values.
- An item mesh slot takes the parameters of the bitmap it keeps.

In the real-renderer survey, 4,576 of the 4,652 textured item mesh slots (1,623 types) go from GL_REPEAT to GL_CLAMP.
The other 76 keep GL_REPEAT:

- 22 are startup special models (OpenTexture rule);
- 54 have record items whose file a startup model's OpenTexture loaded first, either by the same path or by a
  name-map hit.

Four name-map slots take LINEAR, the filter of their startup LoadBitmap (`lightning2.jpg` ×2, `lighting_mega03.JPG`
and `hole.jpg`).

The full-path rule also changes the file of 72 slots in 72 types. These now draw the `Data/Item/texture/` copy that
the loader's path names, where native had returned an earlier file of the same name:

| File | Slots |
|---|---:|
| `eyejam_R` | 33 |
| `alpha_line2` | 17 |
| `fire_15fmono` | 16 |
| `flame_chrom` | 2 |
| `Swordeff_mono2` | 1 |
| `alpha_line` | 1 |
| `flare01_red` | 1 |
| `Ghost_horse_Armor` | 1 |

### TextureType and the `field_` flag (loader verified; draw already ported)

The mesh draw already ports what the client does with TextureType ([client-meshdraw-exec.md](client-meshdraw-exec.md), "Texture
substitutions"):

- type 1 (`nude_`): returns when `+0xa5` is set or `+0x40 > 0`, otherwise draws with the alternate colour;
- type 2 (`cotton_`): returns when `+0x40 > 0`.

`mu_textures.texture_type` now carries the loader's value into mu_scene. 166 meshes are typed. The item body
executor writes `+0x40` per pass, so typed meshes stop drawing where it is positive: survey passes fall
525,732 → 514,842. `mu_textures.field` carries model `+0xa6`. The draw reads it only together with `+0xa5`
(`texture++`), which native item draws never set, so it changes no pixel today.

### The wearer's skin (verified: `part_skin`, `skin_bitmap`)

A skin mesh keeps its special IndexTexture: `skin_`/`level` → 0x7725, `hair_` → 0x7776, `HQskin…`/`HQlevel` →
0x77c7, 0x7818 or 0x7869, `HQhair` → 0x78ba. The mesh draw binds that index plus `movsx byte [model+0xa4]`
(`0x012b8eae` and five more sites). Then:

- **Who writes `+0xa4`.** RenderCharacter's part loop (`0x0136a374..`, slots 5 down to 0 at character
  `+0x1c4 + k*0x3fc`) fetches each slot's model with GetModel. It stores `0x0139d6a2(character +0x12)` at model
  `+0xa4` (`0x0136a4bd`). That is the class skin index `(class & 0xf) + 16*(tier-1)`, already ported as
  `mu_character_skin_index`. For class 4's helm, the extra model 0x38f6+ copies the byte (`0x0136a5b9`).
- **Before any character draw.** The item loader `memset`s the new model to zero (`0x00cd5619..0x00cd5623`), so a
  model no character has drawn binds the bases themselves.
- **Not model writes.** The other byte stores to `+0xa4` (`0x00c18775`, `0x00c3e245`, …) belong to UI objects.
- **The skin bitmaps.** The startup routine `0x0182a8fe` (reached from `0x0182049e`) registers them with
  LoadBitmap(`Player\…`, GL_NEAREST, GL_CLAMP) in five groups of 16 (one per tier), for example 0x7725
  `skin_barbarian_01`, 0x7736 `level_man01` and 0x77c7 `HQSkinClass101`. 146 indices in 0x7725..0x790a have an
  immediate site. Hair at index 0 (0x7776, 0x78ba) is not registered. They are added to `mu_item_bitmaps.inc`
  (`--skins`), and the `registrations` family checks every site.

Native: `mu_it_part_skin` and `mu_it_skin_bitmap` (`reconstructed/objects/item_texture.c`) are the C steps. The item
loader sets `+0xa4 = 0` and loads the skin bitmaps for that index. `mu_item_textures_wear(class byte)` writes the
wearer's index and loads its bitmaps.

- **Callers that apply a wearer:**
  - `mu-render character` (both paths) uses `--class` for the part slots;
  - in-world players use their class byte, Player-model NPCs their row's class byte, the hero `class_byte`;
  - `mu-render ui inventory` uses an authored `--wearer`;
  - the in-game inventory uses the demo hero's class (authored: as if the hero wore every part).
- **Callers that keep `+0xa4 = 0`:** ground items and inventories without a wearer, as a model no character has
  drawn.

### In-world loaders

Hero parts and equipment, players, Player-model NPCs, the combat weapon, the actor tool's weapons, the +15
attachments, and the helpers' Angel/Imp models and Imp link now reload by the item rule once their type is known.
Where only a path is known (hero equipment, `mu-render character`), the type comes from the first ItemModelFile
record that names the file, or from a class part file name (native choice).

### Unicorn comparison (TEX-002 families)

| Family | Cases | What runs as client code |
|---|---:|---|
| part_skin | 256 | `0x0136a4a9..0x0136a4c3` for every class byte, with `0x0139d6a2`, `0x0095f5cc` and `0x0139cb8a` as client code: model `+0xa4` equals `mu_it_part_skin`. Tiers 1..5 are all reached. |
| skin_bitmap | 3,072 | `0x012b8e78..` to its continue (`0x012b9471`) or return (`0x012bb34b`) exit, for all 256 `+0xa4` bytes × 12 IndexTextures: the six bases, six others and 0x791a, which returns. The bound index equals `mu_it_skin_bitmap`. |
| registrations | 235 | as above, now with the 146 skin indices |
| startup_names | 1,402 | as above, now path, filter and wrap |

New compiled mutants, all caught:

| Family | Mutation | Cases caught |
|---|---|---:|
| part_skin | class & 0xf (no tier) | 240 |
| part_skin | index & 0x3f | 128 |
| skin_bitmap | no HQhair case | 255 |
| skin_bitmap | unsigned shift (movzx) | 768 |
| registrations | a flipped wrap at 0x77c7 | 1 |
| startup_names | a flipped wrap at `lightning2.jpg` | 1 |

### Survey with the real renderer (installed data)

| Measure | TEX-001 (origin/main) | TEX-002, `+0xa4 = 0` | TEX-002, authored wearer |
|---|---:|---:|---:|
| Types with a white pass, of 1,691 | 94 | 28 | 15 |
| Of the 984 implemented | 82 | 27 | 15 |
| White passes / passes | 8,136 / 525,732 | 2,832 / 514,842 | 1,920 / 514,842 |

The authored wearer (survey host `--wearer`) is the first class slot whose `require_class` stage is set, at that
stage; 1,483 types have one. At `+0xa4 = 0`, 13 armour types stay white on their hair meshes (0x7776 and 0x78ba
are not registered at index 0), as in the client for a model nobody has worn. With a wearer, only the 15 index-0
body draws remain (RENDER-ITEMS-002).

## RENDER-ITEMS-TEX-003: every startup registration and index 0

Inputs as above. New compared body (sha256 in the validator report): LoadBitmap's step `0x00c97730..0x00c97916`.

### Why 89 types turned white again (verified)

`mu_item_bitmaps.inc` held only the indices that TEX-001/002's probe of the body executor named at the time (235: 89
override indices and 146 skins). Bodies admitted afterwards (RENDER-ITEMS-002 parts 12–14, #265/#275/#282) name 61
more indices. All 61 have an immediate LoadBitmap call in a startup routine, for example:

- 0x7fe7 `Effect\Lava.jpg` at `0x01822de5` and 0x8186 `effect\volcano_stone_bg.jpg` at `0x01823b14`;
- 0x82e3 `Effect\black_gold_crom02_mono.jpg` at `0x01824525` and 0x8531 `Effect\ef_line01.jpg` at `0x01828164`;
- all four in `0x0182049e`; most others are in `0x0182cd66`.

The client registers them before an item first draws, the same as the first 89. Nothing new loads them. The table was
a subset.

### The registrations (verified, `registrations`)

The table is now every LoadBitmap `0x0185baac` call of the startup routines (those `0x0182049e` reaches by direct
calls, and the opener `0x01832af3`): 1,522 call sites, 1,553 calls, 1,550 indices. 1,515 sites have an immediate
path and index. Seven sites compute them in five runs:

| Run | Routine | Index | Path | i |
|---|---|---|---|---|
| `0x01825019..0x0182506d` | `0x0182049e` | 0x83d7 + i | `Effect\ad00%d.jpg` (i + 1) | 0..5 |
| `0x0182c344..0x0182c4ec` | `0x0182bb43` | 0x7935 + i, 0x793e + i | `Player\InvenArmorMale%d.tga`, `Player\InvenPantsMale%d.tga` (i + 40) | 0..5 |
| (same run) | `0x0182bb43` | 0x7946, 0x7947 | `Item\Texture\succubus_armor.tga`, `succubus_pants2.tga` (sprintf without arguments) | |
| `0x018327d3..0x01832825` | `0x0183220e` | 0x8300 + i | `Item\texture\fire_sq_%05d.jpg` (i) | 0..11 |
| `0x01835dd8..0x01835e26` | `0x01832af3` | 0x8100 + i | `Effect\xsuper000%d.jpg` (i + 1) | 0..5 |

They give 38 calls. Every startup path ends in jpg or tga (1,236 jpg, 57 JPG, 218 tga, 4 TGA), and every call passes
flags (1, 0), so LoadBitmap prefixes `Data\`.

### Re-registration (verified, `reregister`)

LoadBitmap ends in `0x00c97730(index, "Data\" + path, filter, wrap)` on the bitmap table `0x0bdc5f00`:

1. **Same file.** If the index holds a bitmap with a non-zero reference byte `+0x219`, and its file equals the path
   under `_stricmp` `0x0198c794`, the byte is incremented and the call returns 1. Nothing loads, so the first call's
   filter and wrap stay.
2. **Another file.** If the held file differs, the "[Check] … old file / new file" message `0x01a9fd98` is logged and
   `0x00c97916(index, 1)` unloads the old bitmap.
3. **Load.** The extension (`_splitpath` through `0x00c99025`, without the dot) picks the loader under `_stricmp`:
   `jpg` → `0x00c982ea`, `tga` → `0x00c988fc`. Any other extension loads nothing and returns 0.

Three indices have two startup calls:

- 0x7952: the same file twice (a reference);
- 0x7f6c: `shiny05.jpg`, then `Shiny05.jpg` (a reference under `_stricmp`, so the first spelling stays);
- 0x854c: `Effect\Blur_Aura002.jpg` (`0x0182ecad`), then `Item\texture\Blur_Aura002.jpg` (`0x0182f126`). The second
  replaces the first. Both are straight-line code in `0x0182cd66`.

No index has calls in two startup routines, so their relative order does not matter. `mu_it_register` is one call
and `mu_it_registration` replays an index's calls in table order (`reconstructed/objects/item_texture.{h,c}`).
`mu_item_bitmap_registration` uses it.

Outside the startup routines, 822 more immediate sites register 528 other indices (world, UI and event routines).
Four startup indices (0x7f89, 0x8004, 0x8021, 0x8025) are registered again there with another file. The table keeps
the startup state, which is what an item drawn before those routines run sees. No body draw names any of them.

### Index 0 (verified)

No LoadBitmap call registers index 0. LoadImage's new indices start at 0x865d (`0x00c98243`; `0x00c98211`), so they
never reach 0 either. BindTexture `0x0184acf6` looks the index up through `0x00ebbec8` → `0x00c97c2d`. A miss returns
the zeroed static record `0x01ec3030` (`0x00c97cac..`), whose `+0x215` texture name 0 is bound with
`glBindTexture(GL_TEXTURE_2D, 0)`. With texturing on, the client therefore draws index 0 untextured too.

Index 0 is not a constant, though. In all 23 bodies that draw it, the mesh-draw texture argument is object `+0x68`
(HiddenMesh). There are 35 call sites, each `push dword ptr [eax+0x68]` with `eax = [ebp+0xc]` (the object), for
example:

- `0x01702deb` (0x0b1d), `0x016ed79c` (0x0eee) and `0x016e0a3a` (0x230a/0x2495);
- `0x016fb1dd` (0x2537) and `0x0170e146` (0x280b, 0x280e, 0x2837..0x283a).

Under Unicorn (`client_stream`, the eleven classify states), the argument follows object `+0x68`: 0 gives 0, −1 gives
−1 (own texture) and 3 gives 3. For 0x0eee and 0x2537 the body pass's hidden mesh does the same.

The body executor's domain is `+0x68 = 0`: `renderchar.c` refuses any other value except for the seeds
0x2322..0x2327, and its recipes store the word as the constant 0. The client's item objects hold −1.
ItemObjectAttribute `0x016da00b` sets −1 for every type (2 for 0xb05/0xeed/0xf0b/0x1711/0x16f6, 1 for 0x10f0), and
both RenderObjectScreen `0x016c2d82` (inventory, [client-fidelity.md](client-fidelity.md)) and the ground items call
it. None of the 23 types is among its exceptions. In the client's inventory and on the ground, these meshes therefore
draw their own textures. Natively they stay white until the executor admits `+0x68 = −1` (RENDER-ITEMS-002 domain).
This is not a registration.

### Survey (installed data, real renderer, 48 states per type)

| | Main `5cb6fa6d` | TEX-003 |
|---|---:|---:|
| Types with a white pass, of 1,691 | 125 | 36 |
| Of the 1,230 implemented | 124 | 35 |
| White passes / passes | 10,320 / 612,090 | 3,696 / 612,090 |
| Unresolved override bitmaps | 142 (61 indices + index 0) | 23 (index 0 only) |
| With an authored wearer | | 23 (index 0 only) |

The 36 that remain:

- **13 armour types** with `+0xa4 = 0` (the hair meshes, 0x7776/0x78ba not registered, as in TEX-002): 0x191b,
  0x1957, 0x1978, 0x197a, 0x1991, 0x19a6, 0x19aa, 0x19c8, 0x19ca, 0x19f7, 0x19f9, 0x19fa (body not implemented) and
  0x1a05.
- **23 bodies** that pass object `+0x68 = 0` as a mesh texture. TEX-002's 15 are 0x0eee, 0x0f00, 0x0f01, 0x0f0e,
  0x151a, 0x252b, 0x252c, 0x2537, 0x2538, 0x280b, 0x280e and 0x2837..0x283a. Eight came with later bodies: 0x0b1d,
  0x0b1e, 0x0b1f, 0x1305, 0x151b, 0x151c, 0x230a and 0x2495.

The survey limit is re-measured, not restored: registrations cannot bring it under 30, because 23 + 13 = 36 types stay
white in the executor's domain. The private test now requires every white type to be special-only or index-0-only,
with no other unresolved index. It pins the counts (13, 23).

### Unicorn comparison (TEX-003 families)

| Family | Cases | What runs as client code |
|---|---:|---|
| registrations | 1,554 | One count check: every startup site is covered, and call count = table size. Then the 1,553 calls in table order. The 1,515 immediate sites each run from their first push. The five runs execute whole, with sprintf, OpenTexture and LoadBitmap as stubs. Each call's index, path, filter, wrap and flags must equal the table. |
| reregister | 3,314 | `0x00c97730` with `_stricmp`, memset and `0x00c99025` as client code. The std::map members, `_splitpath`, the string members, the unload and the two loaders are stubs. 1,764 synthetic calls (1,000 sequences over held, released and empty slots, with case and extension variants) are compared with `mu_it_register`: requests, return byte and slot. Then all 1,550 table indices are replayed from an empty slot and compared with `mu_it_registration`. |

New compiled mutants, all caught:

| Family | Mutation | Cases caught |
|---|---|---:|
| registrations | a flipped wrap at 0x8531 | 1 |
| registrations | a dropped computed call (`fire_sq_00005`) | 582 |
| registrations | 0x854c's two calls swapped | 2 |
| reregister | case-sensitive path compare | 164 |
| reregister | never a reference (always replace) | 251 |
| reregister | reference byte ignored | 87 |
| reregister | case-sensitive extension | 207 |
| reregister | any extension loads | 277 |
| reregister | first call only (no replay) | 1 |
