# RENDER-ITEMS-TEX-001

Item bodies that render white natively. [Finding, addresses and survey](../research/client-render-items-tex.md).

Branch `claude/render-items-tex-001` (Claude Opus 5.5), worktree `~/Documents/MTM/worktrees/render-items-tex-001`,
from origin/main `f7a1e33`. Input links `tools/python` and `evidence` come from the main checkout and are never
committed. No live game, network or session code. `reconstructed/renderchar/renderchar.c` is untouched; the body
executor is only called, to probe the override indices.

## What changed

- **Root cause.** Native item meshes took their bitmaps only from the model's folder. The client's item model
  loader `0x00cd558e`, reached on demand from GetModel `0x00eaa8cf`, asks `<record folder>Texture\<name>`, then the
  bitmap-name map. Separately, the body draws' override bitmaps (`0x84d9..` rank-5 blue, `0x8239`, `0x800e`, …)
  were never registered natively. The client registers them at startup with LoadBitmap.
- `reconstructed/objects/item_texture.{h,c}`: `mu_it_open`, one mesh of `0x00cd558e` (specials, TextureType,
  `field_`, name map, message) on OpenTexture's host type.
- `native/core/mu_item_textures.{h,c}`: the rule per type:
  - item record → `mu_it_open`;
  - startup special models and class parts → OpenTexture `Item\` / `Monster\` / `Player\`;
  - else the model folder.
  The override indices are found by probing the body executor and added from the generated `mu_item_bitmaps.inc`
  (89 registrations). Special mesh names keep the client index (`mu_textures.client_index`, passed through by
  mu_scene), so `hide` meshes are skipped as in the client.
- `native/core/mu_texture_names.{h,c}`: `mu_texture_names_item`, the same map without changing its world part.
  Item lookups also consult the 1,401 startup LoadBitmap names (`mu_startup_bitmaps.inc`); the object path is
  unchanged.
- `native/core/mu_textures.{h,c}`: `mu_textures_load_specials` and the `client_index` field. `mu_scene.c`: one
  guarded line.
- Callers: `mu-render ui inventory`, ground items (`mu_items.c`), the in-game inventory gfx (`world_gfx_game.c`)
  and `mu-render character` (after the item type is known). In the two world loaders, the viewer's Data/Player
  fallback now runs only when no client rule applies.
- `native/tests/item_textures_host.c` (survey host) and `native/tests/test_native_item_textures.py`.

## Untextured counts (real renderer, installed data, 48 states per type)

| | Before | After |
|---|---:|---:|
| Survey types with a white pass (of 1,691) | 1,431 | 94 |
| Implemented bodies + skins with a white pass (of 984) | 859 | 82 |
| Meshes without a bitmap | 4,138 | 0 |
| White passes | 268,600 / 535,984 | 8,136 / 525,732 |

What remains:

- **79 types (67 implemented):** their only white meshes have special names (HQskinClass…, skin_Class…, hair_…,
  level_man…). The client binds the wearer's class skin bitmaps `0x7725 + shift` there; native item draws have no
  skin bitmaps.
- **15 types (15 implemented):** a body draw names bitmap index 0, which no LoadBitmap registers. This belongs to
  the body executor (RENDER-ITEMS-002): types 0x0eee, 0x0f00, 0x0f01, 0x0f0e, 0x151a, 0x252b, 0x252c, 0x2537,
  0x2538, 0x280b, 0x280e, 0x2837, 0x2838, 0x2839 and 0x283a.

The rank-5 bodies of RENDER-EFFECTS-005 (`0x1c26`, `0x1c27`, `0x1c2b`, …) have no white pass now.

## Hash changes (intended) and images

Base `f7a1e33` `mu-render` against this branch, `mu-render ui inventory` on installed data:

- **Unchanged.** RENDER-ITEMS-002K's control (codes 0,1,2,3,7,8; 162 triangles) stays `df03a290…4930`. Code 28
  (`0x0b02`, textured before) stays `b079bc2b9568…`.
- **Gallery.** 002K's gallery (28, 2711, 4305, 4398, 7333, 3103; 3,432 triangles) changes `bcae5aac…5c9b` →
  `d537b52f…d25d`. Each item alone:

  | Code | Type | Before → after | Why it was white |
  |---|---|---|---|
  | 2711 | 0x157d | `8e91c0ecabb6` → `9d24c8706aa3` | 5 meshes |
  | 4305 | 0x1bb7 | `a42d989ad204` → `e6c97118085a` | 2 meshes |
  | 4398 | 0x1c14 | `e1a34dd1fe77` → `4fe6115d2f75` | 3 meshes |
  | 7333 | 0x278b | `eea7f80d8922` → `2b9f3a349648` | an override bitmap |
  | 3103 | 0x1705 | `0a73a1c33da7` → `0fabc8752330` | 1 mesh |

- **This lane's gallery.** Codes 29, 32:+9, 4416:+11, 4191, 3608 and 6144 change `2c804d9c…` → `057bf46a…`, and
  triangles 10,535 → 10,495 (the helm's `hide` mesh). Inspected crops: the rank-5 armour at +11 shows its blue
  `0x84d9` overlay instead of white; the `field_` armour, sword, helm and wing are textured. Code 32 at +9 stays
  bright: those are glow passes, and it is textured at +0.
- **61 types draw with a different file.** They use one of 11 files whose `Data/Item/` and `Data/Item/texture/`
  copies differ (eyejam_R, fire_15fmono, sword15_2, necklace, monmark02/03, pentaHR, flame_chrom, Blue_eyebow02,
  ground_wind2, lower_14m). They now draw with the `texture/` copy, as the client does. They were textured before,
  with the model-folder copy.
- Native tests that pin item frames still pass (public and private runs below).

## Checks

- `scripts/validate_item_textures.py --cases 3000 --mutations` (`MU_SECTION3` = capture-04 section 3):
  - item_open: 3,000 cases;
  - registrations: 89;
  - startup_names: 1,402.

  Zero mismatches and zero stops; **16/16 compiled mutants** caught. The registered run (`--cases 1000`) gives
  2,491 cases.
- `reconstructed/objects/test_item_texture.py`: 4 portable tests + 1 private. `native/tests/test_native_item_textures.py`:
  3 synthetic tests + 1 private installed survey.
- Item-render native tests (`test_inventory_skin`, `test_native_hud`, `test_native_items`, `test_native_renderchar`,
  `test_native_character`, `test_native_gfx2/3`): 64 tests pass, public and private (`MU_GAME_ROOT` = the installed
  client).
- Gate on the merged tree (origin/main `e725bb9` merged in `b1625b6`): `MU_GATE_JOBS=4 nice -n 10 bash
  scripts/local-macos-ci.sh` passes: **1,747 tests across 38 suites, 1,518 passed, 229 skipped, zero failures or
  errors**. Fixtures, viewer and live-readers pass, and the publication audit accepts **1,735 staged files, zero
  rejected**.
- Private validators on the merged tree (`run_validators.py --private --jobs 2`, with `MU_SECTION3`):
  - `validate_item_textures`: 2,491 cases, 0 mismatches, 16/16 mutants;
  - `validate_worlds_g2` (its library and name map changed): 2,657 cases, 0 mismatches, 17/17 mutants.

## Limits and next steps

- **Wrap.** The client uploads item-rule textures with GL_CLAMP; the native slots keep GL_REPEAT (the brief allows
  hash changes only for untextured items). It is verified and a one-line change; with it, code 28 would change to
  `4840410d6544…`.
- **TextureType** (166 nude_/cotton_ meshes) and the `field_` flag `+0xa6` are computed but not applied by the mesh
  draw.
- **Skin bitmaps** `0x7725..` for item draws (79 types): character-skin domain.
- **Index-0 overrides** (15 types): RENDER-ITEMS-002.
- **Not converted:** in-world hero, player and monster-attachment items (`mu_character_set_item`,
  `mu_renderchar_attach_load`) keep the model folder, because their loaders do not know the item type. A follow-up
  can pass the type and the item table.
- **Name-map order** between the startup models and the startup LoadBitmap files is not rebuilt. 9 file names have
  two startup paths; the first site is kept.

## Coordination

RENDER-ITEMS-002 part 12 owns the body tables, the generator and the executor; none of them changed here. The probe
calls `mu_rc_item_draws_context`/`mu_rc_item_draws_owner` only, so new bodies are picked up automatically. Shared
files have small edits: `mu_scene.c` (one line), `mu_textures.{c,h}`, `mu_texture_names.{c,h}`, `mu_items.c`,
`world_gfx_game.c`, `mu_render_world.c`, `mu_render_hud.c`, `native/Makefile`, `reconstructed/objects/Makefile` and
`scripts/validators.toml` (appended row). On conflicts keep both sides.

Local files: renders and scratch under `~/Documents/MTM/mu-mac-tools/native/{renders,scratch}/render-items-tex-001`
and the temporary base worktree `worktrees/rit-base` are deleted at the end. No later lane needs them as input.
