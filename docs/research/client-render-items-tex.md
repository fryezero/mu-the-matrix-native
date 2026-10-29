# Item model textures and the item bitmap registrations (RENDER-ITEMS-TEX-001)

Native item bodies drew white where the client draws textures. The known case was the lit rank-5 body
(RENDER-EFFECTS-005, "Saturation"), whose blue overlays name bitmaps 0x84d9..0x84db. A survey of every item type
showed a much larger cause: natively, item meshes took their bitmaps only from the model's folder. The client never
looks there for an item model. [Checks and limits](../handoffs/RENDER-ITEMS-TEX-001.md). RENDER-ITEMS-TEX-002 applies
the upload parameters, TextureType, the `field_` flag and the wearer's skin bitmaps, and converts the in-world
loaders ([below](#render-items-tex-002-upload-parameters-texturetype-and-the-wearers-skin),
[checks](../handoffs/RENDER-ITEMS-TEX-002.md)).

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
