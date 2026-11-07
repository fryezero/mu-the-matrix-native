# RENDER-ITEMS-CALLERS-001

Branched from main `6eaf3f2b` (#325); merged main `53cffd00` (#326, #327) before any check ran. Branch/worktree
`claude/render-items-callers-001` (Claude Opus 5.5). No live client, launcher, network or hosted workflow. No full
gate in the lane (2026-11-04 test budget).

Scope: make the item pre-draw effects of RENDER-ITEMS-002R (#325) show in the game world. Before this lane only
`mu-render character --world-render` passed the item pose; every world caller ran the programs with refusals.
[Finding](../research/client-render-items.md#part-19-the-world-callers-of-the-pre-draw-programs-render-items-callers-001).

## Result

| Caller (client) | Native | Pose passed | Flag |
|---|---|---|---|
| RenderLinkItem `0x012bd910` → RenderObjDraw at `0x012c6a83` (worn weapons, shields, wings) | `parts/hero.c`, `parts/players.c`, `parts/actors.c` (player-model actors), slots 6..8 | the item's saved pose `item->bones` | TestFrustrum2D at the model's BodyOrigin |
| RenderPartObject `0x017e63f4` → RenderObjDraw at `0x017e7960`/`0x017e7997` (ground items) | `parts/items.c`, software and GL | `mu_model_bone_matrices` after `pose_item` | at the model origin (= OBJECT position) |
| `0x00a497c6`/`0x00a49bc9` (inventory/UI 3D items) | `world_gfx_game.c` | not wired (limit) | — |

- `world_rt_item_pre` (world_rt.c) sets `env->item_bones`, `env->pre_counts` (per caller) and the flag, only for a
  type with a pre-draw program and a particle pool. Other draws are unchanged.
- `world_item_pre.h` holds the flag: `!TestFrustrum2D(x2d, y2d, 6, origin.x·0.01f, origin.y·0.01f, -20.0f)` with
  the frame's CreateFrustrum2D polygon. With `--legacy-box`, every item counts as in view, as in the other world parts.
- `mu_renderchar_env.item_out_of_view` (new, default 0) feeds `host.visible`; that is the only change in
  `mu_renderchar.c`/`.h` (two lines and a field).
- Report: one `{"item_pre_draw": true, "hero"|"players"|"actors"|"ground": {pre_effects, pre_refused, hidden}}`
  summary line, printed only when a program ran, so every other report is unchanged.

Scene (`mu-walk`, Lorencia 128,124, 60 frames, four demo players wearing sword `0x0b27`, shield `0x1748`, wings
`0x2382`/`0x2394`/`0x2384`, bow `0x1316`, mace `0x0f1c` and sword `0x0b4c`; ground drops `0x2384`, `0x0b4c`, `0x1311`):

| | players pre_effects / pre_refused | ground | sprites created | rand calls |
|---|---|---|---:|---:|
| before (main's behaviour, counted) | 0 / 94 | 0 / 19 | 0 | 133 |
| after | **92 / 2** | **18 / 1** | 110 | 133 |

The refusals left are wing `0x2384`'s OBJECT-owned particles (`0x810a`/17, `0x81cf`/0). A player outside the polygon
(138,114) has the flag clear: 0 requests, `hidden` 4. The GL `mu-world` run of the same scene at 140,130 gives
players 92/1 and ground 18/0 (other particles share the stream).

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_EVIDENCE_DIR=$HOME/Documents/MTM/mu-the-matrix-native/evidence`,
`MU_OBJECTS_PLAIN_DIR=$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain`,
`MU_SNAPSHOT_DIR=$HOME/Documents/MTM/mu-mac-tools/native/scratch`, `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang`,
`MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`, `MU_VALIDATOR_CACHE=$HOME/Documents/MTM/mu-mac-tools/native/cache/validators`.
All heavy steps `nice -n 10`.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` | pass | 31.5 s |
| `validate_item_callers --mutations` (new row, via `run_validators.py --cache`, at `ca90c5e3`) | 6,013 cases, 0 mismatches: link_flag 3,000, part_flag 3,000, order 8, callers 5; 6/6 mutants caught (scale 1,780, axis 1,826, range 732, negate 6,000, scene 4,036, swap 1,826 detections), all compiled, anchors once | 3.6 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, at `e5205817`) | 7 suites, 1,299 tests, 0 failures, 196 skips | 272.5 s (+74 s selection) |
| Private modules `test_native_world_predraw`, `test_native_renderchar`, `test_native_item_textures` (6b: default env), `test_native_players`, `test_native_items` | 46 tests OK | 116.8 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.7 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` (at `e5205817`) | 12 rows pass (table below) | 238.7 s |
| `scripts/audit_repository.py` | 2,027 files, 0 rejected | 16.6 s |

| Row (selected by `--list-affected origin/main`) | Cases | Seconds |
|---|---:|---:|
| `validate_meshdraw` (symbol fallback) | 14,619 | 56.5 |
| `validate_model_edge` (symbol fallback) | 954 | 117.9 |
| `validate_movement` (symbol fallback) | 6,614 | 51.0 |
| `validate_render_effects17` (symbol fallback) | 618 | 7.0 |
| `validate_audio_callers` / `audio_domains` / `audio_items` | 5,528 / 2,544 / 3,000 | 6.6 / 35.0 / 9.9 |
| `validate_app_polish1` / `2` / `4` | 752 / 1,028 / 10,485 | 23.5 / 4.3 / 32.1 |
| `validate_render_effects16` | 424 | 3.2 |
| `validate_worlds_fog` | 4,044 | 5.1 |

Not selected (the symbol-level selector found no changed symbol in use): audio_charsel, audio_combat, model_light,
path, session_party, terrain, terrain_remaining, viewport_monsters, worlds_f. `validate_item_predraw` and
`validate_renderchar` are not selected either: `reconstructed/renderchar` is unchanged, and `mu-render character`
keeps `item_out_of_view` 0 (the flag was 1 before).

## Byte identity and renders

- One sweep at the default draw (`fidelity_tour.py render`, no draw_all), base = main `53cffd00` (`mu-world` from a
  temporary worktree). October 22 tour: 28/28 PNG, 14/14 OBJECT, 14/14 light identical; 14/14 report rows are
  identical once the output paths are normalised. DATA-ACQ-002: 64/64 PNG, 32/32 OBJECT, 32/32 light, 32/32 reports.
  No frame changed: the tours show only the hero, whose inferred item types include none of the 26. Wall before/after:
  October 22 17.5/18.0 s, DATA-ACQ-002 43.7/43.6 s.
- README crowd images 26/27 (`capture_readme_stress.py`, both scenes): 4/4 PNGs byte-identical, the same SHA-256
  (`31df49bf…`, `718ffc07…`), no `item_pre_draw` line. The crowd's kits wear none of the 26 types. Nothing to re-pin.
  Wall 23.7 / 23.3 s.
- Window-only crops (before | after, 2× nearest, GL `mu-world` 640×400, Lorencia 140,130, frame 30), in
  `~/Documents/MTM/mu-mac-tools/native/renders/render-items-callers-001/`: `players-blade-archer.png` (wing `0x2382`'s
  glows, the bow's sparkle), `players-seraph-wing-0x2384.png`, `ground-and-maul.png` (60-85 KB). These are offline
  native renders, not pixel comparisons with the original client.

## Limits

- **Hero**: wired like the players, but its item types are inferred from standard file names
  (`mu_renderchar_type_from_path`, `SwordNN.bmd`). The 26 pre-draw types use other names (Item.bmd records), so the
  hero shows no pre-draw effects until its items are session-backed (type from the record).
- **Inventory/UI** (`0x00a497c6`/`0x00a49bc9`, `world_gfx_game.c`): not wired. Its sprite pool exists only for the
  `0x389c`/`0x389d` skins and draws per icon. Routing there needs a per-icon pool.
- **Owner binding** (scope 3): not needed for sprites. CreateSprite records live one frame: RenderSprites
  `0x0169270e` kills every drawn sprite in modes 0/2, and the per-sprite draw `0x01692931` never reads the owner word
  `+0x34c` (both verified in `reconstructed/particles`). The programs run every draw at the current bone positions,
  so the sprites follow the item. OBJECT-owned particles (`0x2384`/`0x2385`) stay refused: the native owner
  records take attached-object indices, and those kinds/subtypes have no native consumer.
- Characters outside the polygon are still drawn natively (other lanes' visibility rules). Their items then count
  as `hidden`.
- Bones outside the item skeleton stay refused, as in 002R.

## Release

Steward validators: validate_item_callers (new; ran with mutants at `ca90c5e3`), validate_meshdraw,
validate_model_edge, validate_movement, validate_render_effects17, validate_audio_callers, validate_audio_domains,
validate_audio_items, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_render_effects16,
validate_worlds_fog (ran at `e5205817`, no mutants). That is exactly the 13 rows of `--list-affected origin/main`;
meshdraw, model_edge, movement and render_effects17 are its symbol-level fallback rows. `ca90c5e3` changed only
validate_item_callers' `build` entry. Env as under Checks.

Cleanup removes `mu-mac-tools/native/scratch/render-items-callers-001/`, the base worktree and the build directories.
The crops in `renders/render-items-callers-001/` are the only kept artifacts. The worktree stays until the steward
merges. No new input needs to be kept.
