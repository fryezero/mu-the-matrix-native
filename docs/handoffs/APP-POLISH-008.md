# APP-POLISH-008

Branched from main `f2370871` (#334); merged main `8623fced` (#335 REGRESS-002, #336 APP-REFRESH-008) as `69ab8d76`
and `0c3c2777` (#337 RENDER-WORLDS-RAKLION) as `1cac5083`. Branch/worktree `claude/app-polish-008` (Claude Opus 5.5).
No live client, launcher, installed app, network or hosted workflow. No full gate in the lane (2026-11-04 test
budget). [Finding](../research/client-app-polish8.md).

Scope: make the item work of #330 (RENDER-ITEMS-CALLERS-001) and #334 (HERO-ITEMS-001) visible in the shipped offline
demo. APP-REFRESH-008 proof (d) found the shipped Lorencia crowd wears none of the 26 pre-draw types, and the demo
session lists item files only, so the hero's records were each file's first Item.bmd match at level, option and ext 0.

## Result

### 1. Session equipment records (backward compatible)

The character list (`demo-characters.txt`, `mu-charsel --list` format; also the character store) takes an optional
record after an item file:

```
SLOT=FILE[@GROUP:INDEX[:LEVEL[:OPTION[:EXT]]]]
1 0x01 400 Ironclad weapon0=Item/CookriShortSword.bmd@0:68:9:1 weapon1=Item/Shield01.bmd@6:0:7 wing=Item/Wing02.bmd@12:1
```

- The fields are what the hero's equipment ITEM holds (CharacterMachine `[0x01d1df18] + 0x1b58 + s·0x12c`,
  HERO-ITEMS-001): code `+0x10` = group·512 + index, level 0..15 (level word `+0x14` = level << 3, read back as
  `(word >> 3) & 15`), option 0/1 (`+0x98`, which `0x00cd0995(item, 1)` tests == 1: the excellent pass), ext `+0x3b`.
  Group 0..15, index 0..511, level 0..15, option 0..1, ext 0..255; anything else is refused with the line number.
- A file-only item loads exactly as before (record unset: the file's first Item.bmd record, level/option/ext 0).
- Reader: `mu_charsel_parse_item` (native/core/mu_charsel.c), used by `mu_charsel_list_parse` and by
  `mu-world`/`mu-walk --hero-item SLOT=FILE@...`. The store (`mu_offline_session_save`) writes the records back.
- Feed: `mu_world_rt_options.item_records` (mu-client passes the chosen entry's records). In `world_rt.c` a record
  applies only while the slot holds the front end's own file (not a class part or the combat stand-in). It types
  the slot (`hero_item_type`: code + 0xae6, also for the skill checks' weapon codes) and fills the ITEM through
  `mu_he_item_of_record` (reconstructed/hero-equipment). The existing `mu_he_set_character_class` then writes type,
  level, option and ext into the part slots that `parts/hero.c` draws.
- Report: `{"hero_records": true, "slots": [{item, type, level, option, ext, passes}]}`, printed by mu-world/mu-walk
  only when a record is in use. Every other report is unchanged.

### 2. Demo outfits (fixture data only, appearance only)

| Character | Item (code, type) | Level | Pre-draw program |
|---|---|---|---|
| Ironclad (demo hero, DK) | Cookery Short Sword 0:68 = `0x0b2a` (was Katana file `Sword04.bmd`), excellent | +9 | yes, 8 sprites / 0 refused |
| Ironclad | Small Shield 6:0 `0x16e6` / Wings of Heaven 12:1 `0x22e7` (same files) | +7 / 0 | no |
| Nightfall, Windleaf, Spellblade, Crownlord | their files' own records 5:1, 4:1, 0:4, 2:0 (same files) | +7 | no |
| Aeris (crowd) | Floor Shield 6:98 `0x1748` (was 6:6) | +7 | yes |
| Redhand (crowd) | Xeno Blade 0:102 `0x0b4c` (was 0:10), excellent; Wings of Eternal 12:37 `0x230b` (new) | +11 / 0 | yes, both |
| Sunwing (crowd) | Wings of Dimension 12:43 `0x2311` (was 12:1) | 0 | yes |
| Corvin (crowd) | Floor Hammer 2:54 `0x0f1c` (was 2:8) | +9 | yes |

- Every new type is served in full: 0 refused in every scene below. The bow `0x1316` (CALLERS' test kit) was tried
  on Kyra and dropped: 1 refused at 128,124. Wings `0x2384`/`0x2385` (OBJECT-owned particles, RENDER-EFFECTS-020) and
  the cloaks `0x2382`/`0x2394` (no cloak mesh drawn, HERO-ITEMS-001 limit) were left out.
- Ironclad's sword: the file's first record is the [Bound] variant 0:65 `0x0b27`; the record names 0:68 `0x0b2a`.
  Its kind byte is 0x51, not the Katana's 1. Every demo Dark Knight skill (18..23, 41..44, 48, 49, 344) has weapon
  rule 0, 1 or 2 (`skills_ext.tsv` column `+0xb4`), and rule 2 lists 0x51 (`skill_canuse.c`). So the skill bar
  behaves the same. The other characters keep their weapon codes, so their skill checks are unchanged.
- Unchanged: classes, levels, names, stats, join vitals (`hero_join.h`, `progress_demo.h`), combat numbers (the
  fixture's damage does not read the weapon), skills, joins, the character-select scene (it draws files, not levels).

### 3. Proofs (mu-world, GL 640×400, 60 frames, installed game, APP-REFRESH-006 Native Data objects; the app's
demo files: placement, NPC demo, `--combat --progress --items`, demo players; hero = Ironclad, class 1, angle 90)

| Scene | Before (main `f2370871`) | After |
|---|---|---|
| 140,130 (Ironclad's join tile) | no `item_pre_draw` line (no program ran); `sprites_created` 29 | players **98 drawn / 0 refused** (2 hidden), hero **8 / 0**; `sprites_created` 127, `rand_calls` 936 = before |
| 128,124 | no line; `sprites_created` 17 | players **51 / 0** (2 hidden), hero **8 / 0**; `sprites_created` 76 |

Hero level glow: the same scene's `hero_records` line reads slot 6 type `0x0b2a` (2858), level 9, option 1,
**8 passes**; slot 7 `0x16e6` level 7, 4 passes; slot 8 `0x22e7` level 0, 2 passes. The same sword with a record at
level 0 draws 2 passes; at +9 without the option, 6 (two drawn frames: 1 → 3 → 4 passes a frame).
With the file-only line the sword is `0x0b27` with no record passes, as on main.

`mu-walk` soft 320×240 at 128,124 (`test_native_world_predraw`): demo players file 0 → **98 / 0**.

Window-only crops (before | after, 2× nearest, frame 60), local in
`~/Documents/MTM/mu-mac-tools/native/renders/app-polish-008/`, demo names only:
- `hero-ironclad-cookri-sword-9-excellent.png` (140,124: Katana → Cookery Short Sword with its glow);
- `redhand-xeno-blade-wings-of-eternal.png` (140,124: Redhand on the gold Fenrir, the new wings' glow);
- `sunwing-wings-of-dimension.png` (135,132).

These are offline native renders, not compared with an original-client capture.

### 4. README

No README image changes. 26/27 come from `capture_readme_stress.py`, which builds its own 80-player fixture and passes
no demo files or hero items. 01 is a custom crowd. 03 shows Nightfall in character select, which draws item files
without levels, and her staff file is unchanged. 10/28 use the bow stand-ins; 12/22 show class parts.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_SECTION3,
MU_EVIDENCE_DIR, MU_PATH_DIRECTIONS, MU_SNAPSHOT_DIR, MU_OBJECTS_PLAIN_DIR, MU_NATIVE_DATA_DIR, MU_VALIDATOR_CACHE, …)
plus `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang`, `MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`; for the private module run
also `MU_GFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib` and
`MU_LANG_DIR=$MU_NATIVE_DATA_DIR/lang`. All heavy steps `nice -n 10`, `make -j4`, `--jobs 2`.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` (+ `make -C native world client`) | pass, no warnings | 13.9 s + 11.6 s |
| `validate_hero_items` with mutants (`run_validators.py --private --cache --only`, at `fdcc3390`) | 10,088 cases, 0 mismatches: set_class 3,000, defaults 256, head 832, item_flag 3,000, **record 3,000 (new)**; **18/18 mutants caught** (4 new: record_level, record_option, record_ext, record_code, 750 detections each), all compiled, every anchor once | 175.6 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, at `fdcc3390`) | 7 suites, 1,330 tests, 0 failures, 201 skips | 335.8 s (+67 s selection) |
| Private modules (private-env.sh): test_app_polish8 (new), hero_items (Library, HeroScene), world_predraw (FlagHeader, WorldPreDraw), players, helpers, raven, app_polish5, app_polish7, charsel, shell, audio_charsel, quest.Session, native_app | 129 tests OK, 0 skipped | 236.5 s |
| Same scene modules after the `1cac5083` merge (app_polish8, hero_items, world_predraw, players) | 37 tests OK | 30.6 s |
| `scripts/run_fixture_scenarios.py` (repo root) | 11/11 scenarios pass | < 1 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` (at `69ab8d76`) | 15 rows selected, 14 pass, `validate_hero_items` failed only its manifest case count (new family); fixed in `fdcc3390` and rerun above | 263.7 s |
| The 14 other rows again after the `1cac5083` merge (`--list-affected-since fdcc3390` selected all 14) | 14 pass (table) | 202.2 s |
| `scripts/audit_repository.py` | 2,061 files, 0 rejected | 37.5 s |

| Row | Cases | s at `69ab8d76` | s at `1cac5083` |
|---|---:|---:|---:|
| `validate_meshdraw` | 14,619 | 58.8 | 69.8 |
| `validate_model_edge` | 954 | 130.5 | 145.0 |
| `validate_movement` (symbol fallback) | 6,614 | 63.7 | 62.3 |
| `validate_app_polish4` | 10,485 | 43.5 | 39.6 |
| `validate_icarus_c2` | 8,400 | 24.6 | 22.7 |
| `validate_item_callers` | 6,013 | 1.4 | 1.3 |
| `validate_audio_callers` / `audio_domains` / `audio_items` | 5,528 / 2,544 / 3,000 | 6.8 / 28.6 / 4.6 | 6.1 / 29.1 / 5.6 |
| `validate_worlds_fog` | 4,044 | 9.4 | 7.3 |
| `validate_render_effects17` (symbol fallback) / `16` / `18` / `19` | 618 / 424 / 540 / 260 | 8.4 / 5.5 / 1.2 / 0.5 | 8.1 / 3.8 / 1.6 / 0.8 |
| `validate_hero_items` (with mutants, at `fdcc3390`) | 10,088 | 175.6 | (inputs unchanged by the merge) |

`--list-affected origin/main` after `make`: these 15 rows; 9 rows build a changed library but use no changed symbol
(audio_charsel, audio_combat, model_light, path, session_party, terrain, terrain_remaining, viewport_monsters,
worlds_f). 6b by hand: every module that names the demo files, `mu_charsel_*`, `mu_world_rt_options`, hero-equipment
or the world runtime's internals is in the private run above. `validate_app_polish7` only names the demo files in a
comment, and its own class/level table is unchanged.

### Byte identity (one sweep at the default draw, `fidelity_tour.py render`, base = `f2370871` from a temporary worktree)

- October 22 tour: 28/28 PNG, 28/28 OBJECT + light dumps, 14/14 reports identical (paths normalised). Wall
  before/after 26.7/29.4 s.
- DATA-ACQ-002: 64/64 PNG, 64/64 dumps, 32/32 reports identical. Wall 56.5/75.0 s.
- No frame changed: the tours run `mu-world` with `--no-audio` only (no players file, no session, no hero items),
  so no demo outfit is in view and no record is used.

## Limits

- The character-select scene still draws the item files without levels (its loader `load_entry` has no glow path).
  The records reach the world hero only.
- A record's FILE is still the mesh that is loaded. The client loads the model of the code's record. The bundled
  records name their own files (checked against Item.bmd by `test_app_polish8`), but a mismatched hand-written line
  would draw one item's mesh with another's type.
- No inventory/UI path for the hero's items (HERO-ITEMS-001 limit). The demo inventory's nine items are unchanged.
- The cloak types still draw no cloak mesh; OBJECT-owned particles (`0x2384`/`0x2385`) stay refused. Neither is worn
  by the demo characters.
- mu-client prints no `item_pre_draw` / `hero_records` line (only mu-world/mu-walk call the report). The counts above
  come from `mu-world` with the app's demo files and arguments.

## Release

Steward validators: validate_hero_items (ran with mutants at `fdcc3390`; its inputs are unchanged since),
validate_meshdraw, validate_model_edge, validate_movement, validate_app_polish4, validate_icarus_c2,
validate_item_callers, validate_audio_callers, validate_audio_domains, validate_audio_items, validate_worlds_fog,
validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19 (ran at
`69ab8d76`, and again at `1cac5083` after the #337 merge, no mutants). Env: private-env.sh plus
`MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang` and `MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`.

The next APP-REFRESH lane installs this: the shipped session then shows Ironclad's sword glow and the crowd's
pre-draw effects. Cleanup removes `mu-mac-tools/native/scratch/app-polish-008/` (renders, the base worktree and its
build) and the lane's build directory. The three crops are kept. The worktree stays until the steward merges. No new
input needs to be kept.
