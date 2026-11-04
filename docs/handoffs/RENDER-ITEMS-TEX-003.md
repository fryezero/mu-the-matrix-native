# RENDER-ITEMS-TEX-003

The real regression INTEGRATION-GREEN-002 found (row 5): `test_native_item_textures.test_private_installed_survey`
gave 125 white types on main `5cb6fa6d`, where #266 had measured 28.
[Finding, addresses and survey](../research/client-render-items-tex.md#render-items-tex-003-every-startup-registration-and-index-0).

Branch `claude/render-items-tex-003` (Claude Opus 5.5), worktree `~/Documents/MTM/worktrees/render-items-tex-003`, from
origin/main `5cb6fa6d`. Input links `tools/python`, `evidence` and `input` come from the main checkout and are never
committed. No live game, network or session code. RENDER-ITEMS-002O's glColor logic in
`reconstructed/renderchar/renderchar.c` is untouched; so are the body executor, its tables and the generator.

## Cause

`native/core/mu_item_bitmaps.inc` was generated from the bitmap indices that TEX-001/002's probe of the body executor
named when those lanes ran (`--ids`; 89 override indices plus 146 skins). Bodies admitted later (#265, #275, #282) name
61 more, for example:

- 0x7fe7 `Effect\Lava.jpg` (`0x01822de5`) and 0x8186 `effect\volcano_stone_bg.jpg` (`0x01823b14`);
- 0x82e3 `Effect\black_gold_crom02_mono.jpg` (`0x01824525`) and 0x8531 `Effect\ef_line01.jpg` (`0x01828164`).

All 61 are immediate LoadBitmap `0x0185baac` calls in the startup routines, the same loader and routines as the
first 89. They were never added to the table.

## What changed

- **The table is every startup LoadBitmap call**, not a probe subset. The routines are those the startup loader
  `0x0182049e` reaches by direct calls, plus the opener `0x01832af3`: 1,522 sites, 1,553 calls, 1,550 indices.
  - 1,515 sites are immediate.
  - 7 sites compute index and path in five runs (index arithmetic):
    - 0x83d7 + i `Effect\ad00%d.jpg`;
    - 0x7935 + i and 0x793e + i `Player\InvenArmorMale/InvenPantsMale%d.tga`;
    - 0x7946/0x7947 (the succubus files);
    - 0x8300 + i `Item\texture\fire_sq_%05d.jpg`;
    - 0x8100 + i `Effect\xsuper000%d.jpg`.

    The generator runs them as client code.

  `scripts/validate_item_textures.py --emit-table PATH` regenerates it. `--ids` and `--skins` are gone, so a body
  admitted later cannot fall outside the table again.
- **LoadBitmap's re-registration rule** `0x00c97730` is ported:
  - the same file under `_stricmp` only counts a reference (first filter and wrap stay);
  - another file unloads the old bitmap and loads the new one;
  - only jpg/tga extensions load.

  The C is `mu_it_register` and `mu_it_registration` (`reconstructed/objects/item_texture.{h,c}`).
  `mu_item_bitmap_registration` replays an index's table calls through it. Three indices have two calls: 0x7952 (same
  file), 0x7f6c (`shiny05`/`Shiny05`, a reference) and 0x854c (`Effect\` then `Item\texture\Blur_Aura002.jpg`, a
  replace).
- `native/core/mu_item_textures.{c,h}`: the lookup only. GL_CLAMP per client, the wearer skin, the item rule and the
  override probe are unchanged.
- Tests:
  - `reconstructed/objects/test_item_texture.py`: 2 new portable tests (the table and the rule);
  - `native/tests/test_native_item_textures.py`: 1 new synthetic test (type 0x0aff's body bitmap 0x7fe7 resolves from
    `Data/Effect/Lava`; it fails on main) and the reworked private survey.

## Untextured survey (installed data, real renderer, 48 states per type)

| | Main `5cb6fa6d` | This branch |
|---|---:|---:|
| White types, of 1,691 | 125 | **36** |
| Of the 1,230 implemented | 124 | 35 |
| White passes / passes | 10,320 / 612,090 | 3,696 / 612,090 |
| Unresolved override bitmaps | 142 (61 indices + index 0) | 23 (index 0 only) |
| With the authored wearer (`--wearer`) | | 23 (index 0 only) |

Every remaining white type is a special mesh or index 0:

- **13 armour types, hair meshes at `+0xa4 = 0`.** 0x7776/0x78ba are not registered, which matches a model nobody
  has worn (TEX-002): 0x191b, 0x1957, 0x1978, 0x197a, 0x1991, 0x19a6, 0x19aa, 0x19c8, 0x19ca, 0x19f7, 0x19f9, 0x19fa
  (body not implemented) and 0x1a05. With a wearer they are textured.
- **23 bodies whose mesh texture is object `+0x68`.** TEX-002's 15 are 0x0eee, 0x0f00, 0x0f01, 0x0f0e, 0x151a,
  0x252b, 0x252c, 0x2537, 0x2538, 0x280b, 0x280e and 0x2837..0x283a. The 8 from later bodies are 0x0b1d, 0x0b1e,
  0x0b1f, 0x1305, 0x151b, 0x151c, 0x230a and 0x2495. Verified:
  - At 35 call sites the client pushes object `+0x68` (HiddenMesh) as the mesh draw's texture argument
    (`0x01702deb`, `0x016ed79c`, `0x016e0a3a`, `0x0170e146`, …). Under Unicorn the argument follows `+0x68` (0 → 0,
    −1 → −1, 3 → 3) for all 23 types.
  - The body executor's domain is `+0x68 = 0` (`renderchar.c` refuses other values), so the draw names bitmap 0.
  - Index 0 is never registered: no LoadBitmap site, and LoadImage's indices start at 0x865d. BindTexture's miss
    binds texture name 0 (`0x00c97c2d` → zeroed `0x01ec3030`), so in that domain the client draws it untextured too.
  - The client's item objects hold −1, set by ItemObjectAttribute `0x016da00b`, which RenderObjectScreen
    `0x016c2d82` and the ground items call. None of the 23 types is an exception there. In the real inventory these
    meshes draw their own textures. Natively they stay white until RENDER-ITEMS-002 admits `+0x68 = −1`.

**The limit `< 30` is re-measured, not restored.** Registration alone cannot bring the survey under 30. The 8 new
`+0x68` bodies (15 → 23) are in the executor's domain and are faithful to it. They are white because of the domain,
not because of a missing registration. The private test is now stricter than before:

- every white type is special-only or index-0-only;
- no type has any other unresolved index (this check would have caught the 89);
- the counts are pinned: 13 hair, 23 index 0, 36 in all; with a wearer 23.

A new `+0x68` body will fail the pinned count, and that is meant: re-measure it with its reason.

## Byte identity (types that were textured stay identical)

- **The table.** All 235 previous entries are unchanged (index, path, filter, wrap). For an index with a single call,
  the lookup returns the same entry.
- **Survey, per type.** Main's and this branch's `item-textures-host --list` outputs differ only in the 89 fixed types'
  `white` count and `missing` list. All 4,758 mesh slots (pixel hash, filter, wrap; `MU_ITEM_TEXTURES_MESHES`) are
  byte-identical.
- **`mu-render ui inventory`** (installed data, `MU_LANG_DIR` set, time 123456), base `5cb6fa6d` vs this branch:
  - control 0,1,2,3,7,8: `df03a290…` unchanged;
  - 002K gallery 28,2711,4305,4398,7333,3103: `b49c3023b83…` unchanged;
  - TEX-001 gallery 29,32:9,4416:11,4191,3608,6144: `370f915c501…` unchanged;
  - 002M gallery 26,46,1547,3098,3643,7196: `38a89608625…` → `df7c9eb8639…`, and at +13 `33e5f25476f…` →
    `416cc071a4c…`. Without code 46 (0x0b14, a fixed type: 0x822d `bloodclaw2_render`) it is unchanged at both levels
    (`d751b1f8db3…`, `51766f3d60f…`);
  - 002N gallery 42,60,1062,2691,6185,6571: `b3f28efc2ff…` → `d6df3ce484e…`, and at +13 `b4c5cb328a1…` →
    `63dddce67ec…`. Without code 42 (0x0b10, a fixed type: 0x8231 `BoodAnelsword_render`) it is unchanged at both
    levels (`7f204d39ff0…`, `368df2ba0f5…`).
- **Previously white, now textured** (window-only crops, before | after, kept locally in
  `~/Documents/MTM/mu-mac-tools/native/renders/render-items-tex-003/`, 2–6 KB each):

  | Crop | Code | Type | Bitmap now drawn | Changed pixels |
  |---|---|---|---|---:|
  | `25_0.png` | 25 +0 | 0x0aff | 0x7fe7 `Effect\Lava.jpg` (blade overlay lava instead of white) | 569 |
  | `122_0.png` | 122 +0 | 0x0b60 | 0x8557/0x8136/0x8554 (lightning sword) | 41 |
  | `2645_9.png` | 2645 +9 | 0x153b | 0x82e3 `black_gold_crom02_mono` | 16 |
  | `4927_0.png` | 4927 +0 | 0x1e25 | 0x84df `Item1163_skirt_render` | 350 |
  | `6298_9.png` | 6298 +9 | 0x2380 | 0x83f4/0x83f5 `kundun_purewhite` (wing flames instead of white) | 506 |

  Codes 30 (0x0b04, 0x8186) and 2669 (0x1553, 0x8531) do not change at levels 0/5/9/13. Their override pass needs
  excellent/lit states, which `ui inventory` does not set.

## Checks

- `scripts/validate_item_textures.py --cases 1000 --mutations` (`MU_SECTION3` = capture-04 section 3): six families,
  **10,598 cases, zero mismatches, zero stops**, and **31/31 compiled mutants** caught (9 new). There is no equivalent
  mutant.
  - item_open 1,000;
  - registrations 1,554 (new: every startup call as client code);
  - startup_names 1,402;
  - part_skin 256;
  - skin_bitmap 3,072;
  - reregister 3,314 (new: `0x00c97730` as client code, 1,764 synthetic calls plus 1,550 table replays).

  `scripts/validators.toml` is updated (cases 10,598, mutants 31, family `reregister`).
- Portable: `reconstructed/objects/test_item_texture.py` 7 tests + 1 private; `native/tests/test_native_item_textures.py`
  5 synthetic + 1 private. The new synthetic test fails on main.
- Private `test_native_item_textures` (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`): 6/6 pass.
- `scripts/run_validators.py --private --only validate_item_textures,validate_render_items` (`MU_RECOVERY_INTEGRATION=1`,
  `MU_SECTION3`, `MU_GAME_ROOT`): `validate_item_textures` passes 10,598 cases, zero mismatches, 31/31 mutants
  (613 s, the one run with mutants). `validate_render_items` passes 5,512 cases and 6 mutants (3.8 s).
- `validate_worlds_g2` without mutants: 2,657 cases, zero mismatches (9 s). It shares the texture lookup in
  `libobjects`. The other `reconstructed/objects` rows are not rerun: this diff only appends two functions to
  `item_texture.c` and changes no existing function.
- Not rerun under the 2026-11-04 test budget: `validate_item_carry` (it builds `reconstructed/renderchar`, which this
  diff does not touch) and the full gate (the steward's batch gate runs it). The lane runs the build, the two changed
  unittest modules and the publication audit (PR body).

## Limits and next steps

- **The `+0x68` domain (RENDER-ITEMS-002).** For the 23 types, the executor needs object `+0x68 = −1`
  (ItemObjectAttribute's value) as a copied word (source 35) instead of the constant 0, and its callers must pass −1.
  For 0x0eee and 0x2537, the body pass's hidden mesh also follows `+0x68`. At 0 they hide mesh 0, where the client's
  inventory draws it. That would make them textured, and white_types would fall to 13 (0 with a wearer). This is the
  executor's domain and changes other draws, so it is a follow-up, not a registration.
- **Non-startup registrations.** 822 more immediate LoadBitmap sites in world, UI and event routines register 528
  other indices. Four startup indices (0x7f89, 0x8004, 0x8021, 0x8025) are registered again there with another file.
  The table keeps the startup state. No body draw names any of them; the private test would flag one that does.
- **Inventory states.** `mu-render ui inventory` sets only the level, so the excellent/lit override passes (codes 30,
  2669) are covered by the survey, not by renders.
- **Modelled services** in `reregister`: the std::map members, `_splitpath`, the string members, the unload and the
  two loaders, which leave one reference.
- TEX-002's limits are unchanged: the `field_` second bitmap, the authored wearer, and the name-map history.

## Coordination

The body executor, its tables, the generator and `renderchar.c` are untouched; RENDER-ITEMS-002O owns the glColor
logic. Files changed:

- `reconstructed/objects/item_texture.{h,c}`;
- `native/core/mu_item_textures.{c,h}` and `native/core/mu_item_bitmaps.inc` (generated);
- `scripts/validate_item_textures.py` and `scripts/validators.toml` (this row only);
- the two test files and the docs.

On conflicts keep both sides.

Local files: scratch under `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-tex-003`, the base worktree
`worktrees/rit3-base` and the build directories are deleted at the end. The five crops above (23 KB) stay for the PR.
No later lane needs any of them as input.
