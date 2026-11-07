# HERO-ITEMS-001

Branched from `origin/claude/render-items-callers-001` (`c2c46da2`, #330); fast-forwarded to main `c5ed13dd` once #330
merged; merged main `ae5e6f36` (batch 69) as `363cc5d1`. Branch/worktree `claude/hero-items-001` (Claude Opus 5.5). No live client, launcher, network or hosted
workflow. No full gate in the lane (2026-11-04 test budget).

Scope: the hero's worn items get their real item types, so item effects (part 18's pre-draw programs, level glows,
link effects) reach the hero as they reach other players.
[Finding](../research/client-render-items.md#part-21-the-heros-part-slots-from-its-equipment-hero-items-001).

## Result

- **Client logic (verified).** The client types the hero from CharacterMachine `[0x01d1df18]`'s equipped ITEMs
  (`+0x1b58 + s · 0x12c`). SetCharacterClass `0x01394870` writes them into the CHARACTER part slots
  `c + 0x1c4 + k · 0x3fc`, the slots the players' ChangeCharacterExt fills from viewport bytes:
  - weapons: type = code + `0xae6`, level `(word >> 3) & 15`, option `0x00cd0995(item, 1)` (`+0x98 == 1`),
    ext `+0x3b`;
  - wing and helper: type and level only;
  - parts: worn parts like weapons; an empty slot takes the class part `0x3700 + 0x50(k − 1) + skin`;
  - head: `0x01394f6f` sets the class head for 17 helm types.

  New `reconstructed/hero-equipment` (`mu_he_set_character_class`, `mu_he_head_type`, `mu_he_item_flag`,
  `mu_he_equipment_of_slot`) reuses the players' slot record and class skin.
- **Native.**
  - `world_rt_hero_item_textures`, which every hero `set_item` passes through, keeps each worn file's Item.bmd
    record. `world_rt_hero_slots` runs the reconstruction on those records.
  - `parts/hero.c` draws a recorded slot with its type, level, option and ext and Item.bmd's kind bytes, as
    `parts/players.c` does, and with the players' glow colour.
  - `mu_renderchar_type_from_path` remains only for slots without a record: class parts, files outside
    Item.bmd, or no Item.bmd.
- **Session records.** The offline demo session lists files (`item=FILE`). A file's record is its first Item.bmd
  record, and level, option and ext are 0, as recorded. Demo data is unchanged.
- **Tool.** `mu-world`/`mu-walk --hero-item SLOT=FILE` passes the front end's equipment, as mu-client passes a
  character's. It is used only for test scenes.

Which hero items changed type, and why:

| Hero | File-name guess | Record type | Visible |
|---|---|---|---|
| Demo characters Nightfall (Staff02), Ironclad (Sword04, Shield01, Wing02), Windleaf (Bow02), Spellblade (Sword05), Crownlord (Mace01) | `0x14e7`, `0xae9`, `0x16e6`, `0x22e7`, `0x12e7`, `0xaea`, `0xee6` | same (+ kind bytes) | no: 85/85 `mu-shell` frames identical |
| Combat stand-ins Sword01/10, Spear01, Bow01, Staff01 | standard | same | no |
| Combat crossbow `CrossBow01.bmd` | −1 (`crossbow` is not a standard prefix) | `0x12ee` Crossbow | no (level 0 draws the same) |
| Test fixture `--hero-item` blade01, CR_shield01, InnocenceCape | −1 | `0x0b4b`, `0x1748`, `0x2382` | yes: 0 → 30 pre-draw sprites, 0 refused |

Item.bmd has 774 distinct standard-named files. For 424 of them, the first record differs from the guess
(models are shared, e.g. `Wing09.bmd` → `0x230b`, guess `0x22ee`). Every one of the 26 pre-draw types uses a
non-standard name.

Hero scene (`mu-walk`, Lorencia 128,124, 60 frames, no players): blade + shield + cloak 30 created / 0 refused,
the same as `sprites_created`, `rand_calls` 120 (unchanged). The shield alone in the left hand gives 4. Sword04 +
Wing02 prints no `item_pre_draw` line. Next to a player wearing `0x2382`, the hero renders the same: 22/22
sprites each.

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_PATH_DIRECTIONS` = the same file (validate_path), `MU_EVIDENCE_DIR=$HOME/Documents/MTM/mu-the-matrix-native/evidence`,
`MU_OBJECTS_PLAIN_DIR=$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain`,
`MU_SNAPSHOT_DIR=$HOME/Documents/MTM/mu-mac-tools/native/scratch`, `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang`,
`MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`, `MU_VALIDATOR_CACHE=$HOME/Documents/MTM/mu-mac-tools/native/cache/validators`.
All heavy steps `nice -n 10`.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` (after the change) | pass | 14.4 s |
| `validate_hero_items --mutations` (new row, `run_validators.py --cache`, at `9346bb0d`) | 7,088 cases, 0 mismatches: set_class 3,000, defaults 256, head 832, item_flag 3,000; 14/14 mutants caught, all compiled, anchors once | 93.6 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, at `9346bb0d`) | 7 suites, 1,299 tests, 0 failures, 195 skips | 306.4 s (+95 s selection) |
| Private modules `test_native_hero_items` (new: 7 portable, 1 Unicorn, 3 scene), `test_native_world_predraw`, `test_native_renderchar`, `test_native_item_textures`, `test_native_players` | 52 tests OK | 142.5 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.7 s |
| `run_validators.py --private --no-mutants --cache --jobs 2` (at `9346bb0d`) | 27 rows pass (below) | 515 s + 28.7 s |
| `scripts/audit_repository.py` | 2,046 files, 0 rejected | 22 s |

| Row | Cases | Seconds |
|---|---:|---:|
| `validate_terrain` | 583,500 | 339.1 |
| `validate_audio_combat` / `audio_charsel` / `audio_callers` / `audio_items` / `audio_domains` | 19,548 / 5,968 / 5,528 / 3,000 / 2,544 | 17.6 / 3.7 / 4.5 / 2.7 / 22.6 |
| `validate_meshdraw` | 14,619 | 59.6 |
| `validate_item_textures` (6b) | 10,598 | 125.2 |
| `validate_app_polish4` / `1` / `2` (6b) | 10,485 / 752 / 1,028 | 33.4 / 20.3 / 3.7 |
| `validate_icarus_c2` | 8,400 | 29.8 |
| `validate_movement` | 6,614 | 59.2 |
| `validate_item_callers` | 6,013 | 1.0 |
| `validate_path` | 4,719 | 28.7 |
| `validate_worlds_fog` | 4,044 | 4.4 |
| `validate_terrain_remaining` / `viewport_monsters` / `worlds_f` | 2,147 / 1,963 / 1,818 | 3.4 / 6.6 / 0.4 |
| `validate_renderchar` (6b) | 1,706 | 39.7 |
| `validate_model_light` / `model_edge` | 1,433 / 954 | 4.8 / 116.9 |
| `validate_render_effects17` / `18` / `16` | 618 / 540 / 424 | 6.1 / 0.8 / 3.1 |
| `validate_session_party` | 200 | 0.8 |
| `validate_hud` (6b) | 48 | 98.2 |

`--list-affected origin/main` after `make` selected 22 rows: the 21 above without the 6b additions, plus
`validate_hero_items`. Most come through `libmunative`/`native/Makefile`. `item_callers`, `render_effects18`
and `icarus_c2` copy `reconstructed/`. Six rows were added by hand under 6b/8b: renderchar, item_textures, hud and
app_polish1/2/4. `validate_path` first skipped because `MU_PATH_DIRECTIONS` was not set. It was rerun with that
variable and passed.

## Byte identity, renders, live

- One sweep at the default draw (`fidelity_tour.py render`, no draw_all). Base: main `c5ed13dd` (`mu-world` from
  a temporary worktree).
  - October 22 tour: 28/28 PNG, 14/14 OBJECT, 14/14 light and 14/14 report rows identical (paths normalised).
    Wall before/after 20.5/21.7 s.
  - DATA-ACQ-002: 64/64, 32/32, 32/32, 32/32. Wall 46.1/52.8 s.
  - No frame changed: the tour heroes wear class parts, which have no Item.bmd record and keep their file-name
    type. With nothing changed, no live comparison is needed.
- Demo characters through the front end (`mu-shell --auto --hold 6`, one temporary session per character in
  row 1, their own items and join): 85/85 frames and 5/5 reports identical.
- Combat stand-ins (sword, twohand, spear, bow, crossbow, staff, `--combat-bow 0x12f9`; Windleaf class, Lorencia
  182,128): 21/21 frames and 7/7 reports identical.
- README:
  - 26/27 crowd: the `capture_readme_stress.py` fixture through `mu-world` gives 3/3 frames and the report
    identical.
  - 01, 12 and 22 show the hero in class parts on mounts; 10 and 28 use the bow stand-ins checked above.
  - No README image changes and nothing needs re-pinning.
- Window-only crops (before | after, 2× nearest, `mu-shell` soft 640×400, Lorencia 140,130, frame 139; test-only
  sessions, not the shipped demo), in `~/Documents/MTM/mu-mac-tools/native/renders/hero-items-001/`:
  - `hero-fxblade.png` (blade01 + InnocenceCape: the cloak's glows);
  - `hero-fxshield.png` (Hammer01 + CR_shield01 + Black Cloak: the shield's sparks);
  - `hero-fxgun.png` (Gunman_masterw01 + SparkleCape).

  99–112 KB each. These are offline native renders. There is no live capture of a hero wearing these items.

## Limits

- **Session records are files.** The demo format has no item codes, levels or options. The record is the file's
  first Item.bmd record: `CookriShortSword.bmd` gives `0x0b27` (the [Bound] variant), not `0x0b2a`. Level,
  option and ext are 0, so the hero shows no level glow or excellent pass yet; the path carries them once a session
  record does. A session format with codes (or the hero's inventory packet) is the follow-up.
- **Cloak meshes.** For the cloak types (`0x2382`..`0x2385`, `0x2394`, `0x2395`), the record's RenderObjDraw body
  (part 18, validated) does not draw the cloak mesh that the file-name fallback drew. A player wearing `0x2382`
  renders the same way. Where the client draws the cape is not traced; it is follow-up work for the item library.
- **Not reproduced** from `0x01394870`: `0x009dadf1` (the weapon override of the worlds `0x009dacb8` lists),
  `0x0137ad93` (hero only), `0x00a00fb7` (stat machine), and the rest of `0x01394f6f` (scales). The head slot is
  computed, but the native character does not draw slot 0.
- **Inventory/UI path** (`0x00a497c6`/`0x00a49bc9`, `world_gfx_game.c`): not wired.
  - The per-icon pool is small: `draw_skin` already opens one and draws each icon's one-frame sprites.
  - A faithful flag needs the world frame's CreateFrustrum2D polygon in the GFx item layer, tested at the icon's
    OBJECT `+0x158` (`ros.position`). That is untested.
  - None of the demo inventory's nine items has a pre-draw program, so wiring it now would show nothing.
- OBJECT-owned particles (`0x2384`/`0x2385`) stay refused, as for players.

## Release

Steward validators: validate_hero_items (new; ran with mutants at `9346bb0d`), validate_meshdraw,
validate_model_edge, validate_model_light, validate_movement, validate_path, validate_terrain,
validate_viewport_monsters, validate_terrain_remaining, validate_icarus_c2, validate_worlds_f,
validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items,
validate_session_party, validate_audio_charsel, validate_render_effects16, validate_worlds_fog,
validate_render_effects17, validate_item_callers, validate_render_effects18, validate_renderchar,
validate_item_textures, validate_hud, validate_app_polish1, validate_app_polish2, validate_app_polish4 (ran at
`9346bb0d`, no mutants), validate_render_effects19 and validate_app_polish7 (from the merge). Env as under Checks,
including `MU_PATH_DIRECTIONS`.

After merging main `ae5e6f36` (#331 RENDER-ITEMS-002S, #332 RENDER-EFFECTS-019, #333 APP-POLISH-007) as
`363cc5d1`, research parts 20 (002S) and 21 (this lane) were both kept, and the code auto-merged.
- `--list-affected origin/main` then selected the same 22 rows plus `validate_render_effects19`, whose mutant
  build copies `reconstructed/`.
- All 30 rows (the 28 above, render_effects19, and app_polish7, #333's row for the same front-end hero) reran at
  `363cc5d1` without mutants: 30 pass with the same case counts as above (render_effects19 260, app_polish7
  5,120), 516 s. `hero_items`' inputs changed only by a header comment, so its mutants were not repeated.
- `test_native_hero_items` (portable + scene), `test_native_world_predraw`, `test_native_renderchar`,
  `test_native_item_textures`, `test_native_players` and `test_app_polish7`: 58 tests OK, 98.5 s. The hero scene
  numbers are unchanged after 002S.

Cleanup removes `mu-mac-tools/native/scratch/hero-items-001/`, the base worktree, the build directories and every
render except the three crops. The worktree stays until the steward merges. No new input needs to be kept.
