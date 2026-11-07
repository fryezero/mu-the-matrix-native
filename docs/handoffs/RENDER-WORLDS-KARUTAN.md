# RENDER-WORLDS-KARUTAN

Two world-slot leftovers:
- Karutan's (worlds 80/81) custom slot `0x00e14596` and after slot `0x00e1543e`, now ported whole as class slots
  (before, RENDER-WORLDS-A had ported only the flag branches and a copy of the after slot);
- world 145's (Aquila) bone placements that RENDER-EFFECTS-019 left open.

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-karutan`, branch
  `claude/render-worlds-karutan`.
  - Branched from `origin/claude/render-worlds-raklion` `6d4f6312` (#337: the shared 121 slot routine and the
    census corrections). #337 was not on main yet when the checks ran, so "before" and `--affected-since` use
    `6d4f6312`: main plus #337.
  - Merged origin/main `0c3c2777` (#337 merged) as `c593c2c0` after the checks. It brought docs and #335/#336's
    session-fixture test lines only: `--list-affected e95ef561` selects 0 validator rows, and no file my checks
    build changed, so nothing was rerun.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.
- Finding: [client-worlds-karutan.md](../research/client-worlds-karutan.md), with the branch table, the diff against
  121's routine, the 145 records, the live comparison and the limits.

## Karutan vs the shared routine (static, then verified)

Karutan's custom slot is its own code, not Test Area 121's or Raklion's: no aligned instruction run, a different
case set and a different world test. So it is ported as its own routine (`world_karutan_visual.c`), not as a row of
`ta_class`. The differences with addresses ([finding](../research/client-worlds-karutan.md) §2):

| Element | Karutan `0x00e14596` | 121 `0x00d58bd8` / Raklion `0x00e949f8` |
|---|---|---|
| World test | `0x00e18ae9` (80, 81), `0x009dad2c` (102), `0x00c7dfcc` → `0x009d3e63` (103..106) at `0x00e145b5..0x00e145ef` | none / `0x00ea233c` (57, 58) |
| After flags | 1, 3, 0x36..0x3a, 0x3e, 0x3f, 0x77 (`0x00e146ce`) and 0x42 | 0x2e, 0x35, 0x4c, 0x59, 0x53, 0x5c |
| Action choice | 0x42 `0x00e146dc`: frame >= 19, `SetAction(rand() % 10 == 0)` | 0x10 `rand() % 2`, 0x11 `rand() % 100` |
| Colour pulse | 0x81 `0x00e14727`: body, grey `0x0185bdc4(−2.5, 0) × 0.3 + 0.7`, mesh 1 with 0x85bb, colour restored, mesh 1 flags 0x44 | none |
| Per-vertex light, particles | none | 6..12, 28 CreateParticle sites |
| Types > 300 | 0x877, 0x87a..0x87d (unreachable) | 0x1a8..0x1ad, base types (unreachable) |

- Shared leaves only: RenderBody `0x00966def`, RenderMesh `0x00966e4a`, SetAction `0x012affa4`, rand `0x01989721`,
  the constant 19 `0x01a82968`.
- 0x81's branch is the same sequence as Kardamahal's 0xaa (`0x00e116b5`), in a separate copy. Its bitmap 0x85bb
  (`Object144\sdsaferzone14B01_R.jpg`, 0x2601/0x2900) is registered by the class's slot 0x24 `0x00e13a5c`.
- The after slot `0x00e1543e` (502 instructions, world test `0x00e18ae9`) draws ten types. It runs in 80/81: the
  after pass `0x016d6949` lists 0x50/0x51. RENDER-WORLDS-A's copy lacked 0x37/0x39's StreamMesh writes
  (`0x00e156eb`, `0x00e1575e`) and stood in for them with a runtime light-skip tweak. Both are replaced.

## What Karutan draws now

- The ten flag types and 0x42 are flagged by the class slot (as before) and drawn by the class after slot.
- 0x42 picks its next action from frame 19 (`rand() % 10 == 0` → 1, else 0) through the shared SetAction. Before,
  only its after flag was set.
- 0x81 draws its body, then mesh 1 pulsed grey with `Object144\sdsaferzone14B01_R.jpg` (now loaded as a slot bitmap
  in 80/81), then mesh 1 additive (flags 0x44). Before, it fell to the generic RenderBody: an unlit dark crystal.
- 0x37/0x39's after mesh carries the StreamMesh byte 0 / 0xff.
- The world test is the client's: the custom slot answers in 80, 81 and 102..106. Only 80/81 have the class.

## World 145 (Aquila): served and refused

- **The three unfollowed map-object records** (types 85, 87: bone 1; type 146: bone 0; models with 2, 2, 1 bones):
  - **served**, as RENDER-EFFECTS-019's general path already places them: the shared-pose bone translation
    `0x012a0030`, plus the position again when the object is alone in its sector (`0x012a0d29`);
  - now compared for exactly these records, alone and in a list (`records_145`).
- **The visual slot's `0x0129fd4f(6)`** (`0x00d77b3e` → `0x00d77c16`, `0x00d77c69`), now **served** with the lone-sector
  placement. An object alone in its sector gets bone 6 × `0x00cf2679(position, 0, scale)` (`0x0129ff2c..0x0129ffd9`).
  `mu_aquila_bone_matrix` reuses RENDER-EFFECTS-018's verified `0x0129fd4f`.
- **Refused, unchanged:**
  - a record, or bone 6, without a pose holding the bone: the client reads `0x06fce398 + 0x30 · bone`, a stale pose;
  - following a bone below −1: `0x0129f671` passes the matrix `0x00a7497a` leaves uninitialised.
  
  None of 145's 93 records falls in either case: all are on posed bones, none follows below −1.
- When the rule applies: an object whose sector holds no other object. 145's placements (`EncTerrain146.obj`) do not
  decode natively and there is no capture, so this is Unicorn-only. The native derives the predicate from its own
  sector lists.

## Shared lines (narrow seams)

- `reconstructed/objects/world_karutan_visual.c`:
  - added: `mu_slots_karutan_custom` / `_after` / `_bitmap` / `_bitmaps`;
  - removed: `mu_karutan_defer`, `mu_karutan_after`;
  - the local `wave` in `mu_karutan_visual` is renamed `w` (it shadowed the slot helper).
- `world_slots2_visual.c`: class 80 for 80/81 in the SLOTS2 chain (custom, after, bitmaps).
- `world_visual_slots.h`: four declarations.
- `world_after.c`: `mu_world_defer` / `mu_world_after_render` drop 0x50/0x51. `mu_world_after_enabled` keeps them
  (the pose's light-skip mesh, unchanged).
- `native/core/mu_objects_runtime.c`:
  - the 0x37/0x39 light-skip tweak in the A after branch is removed;
  - the 145 visual uses `mu_aquila_bone_matrix` with `mu_map_effects_in_sector`;
  - includes `map_effects.h`.
- `reconstructed/objects/map_effects.{c,h}`: `mu_aquila_bone_matrix`.
- Validators:
  - new `scripts/validate_worlds_karutan.py` and its `validators.toml` row;
  - `validate_worlds_121.py`'s `Spec` takes case types, action types and extra stubs (121's and Raklion's defaults
    unchanged, same cases);
  - `validate_render_worlds_a.py`'s Karutan cases (`after_draw`, `flags`) call the class entry points; its
    "Karutan scrolling period" mutant follows the code (`tmod(s,10000,`);
  - `validate_render_effects19.py` gains `records_145` and `aquila_bone6` and three mutants, and builds `aquila.c`
    into its map library. Its row: 6 families, 400 cases, 28 mutants.
- Tests:
  - new `reconstructed/objects/test_worlds_karutan.py` (portable, plus the private comparison);
  - `native/tests/test_render_effects19.py`: an Aquila bone-6 test, and the row counts;
  - 6b: `test_worlds_after2.test_classes` lists 80, 81.
- Docs:
  - the census row in `client-worlds-slots.md`;
  - the Karutan and Aquila entries in `world-handler-coverage.json`;
  - a pointer each in `client-world-fidelity.md`, `client-render-effects-019.md` and `client-worlds-raklion.md`.

## Checks

Under the 2026-11-04 test budget: no lane gate. `nice -n 10`, `make -j4`, `--jobs 2`; load 1m 7–15 with other lanes
active. Code commits: `ae453a69` (the slots, the 145 placement, the validators), `179ea2a8` (mutant tables that compile;
scripts only), `14e7290b` (a host without sector lists counts as in a list: `worlds_slots2_host` had crashed on it).
The later commits are docs only.

| Check | Result | Wall |
|---|---|---|
| `nice -n 10 make -j4` | pass (fresh worktree; later incremental) | 28 s |
| `validate_worlds_karutan --cases 400` (iterating) | 1,200 cases, 0 mismatches | 1.5 s |
| Mutants once, `run_validators.py --private --cache --only validate_worlds_karutan` (at `179ea2a8`) | **validate_worlds_karutan** (new): 3 families × 1,000 = **3,000 cases, 0 mismatches/stops**; **25/25 mutants** caught (lowest 10, "World 102 not tested"). All compile (checked one by one), none equivalent, every anchor exactly once | 144 s |
| Mutants once, `--only validate_render_effects19` (at `179ea2a8`) | 6 families, **400 cases, 0 mismatches** (map_update 80, **records_145 60**, **aquila_bone6 80**, ta_pt 3 × 60); **28/28 mutants** (new: aquila_bone_5 80/80, aquila_unfollowed 21/80, aquila_in_sector_kept 26/80; lowest overall 1, the existing in_sector_next) | 21 s |
| Mutants once, `--only validate_render_worlds_a` (at `ae453a69`; its Karutan cases call the class slots) | 9 families, **9,000 cases, 0 mismatches**; **13/13 mutants** (lowest 9, the moved "Karutan scrolling period"); anchors checked by hand: each matches exactly once | 74 s |
| `validate_render_effects19 --cases 200 --lang-dir <local lang>` (full count, no mutants) | **5,516 cases, 0 mismatches**: map_update 800, records_145 600, aquila_bone6 800, map_records 1,516 (all 758 decoded entries, 145's 93 among them, alone and in a list), ta_pt 3 × 600 | 9.6 s |
| Affected rows, no mutants: `run_validators.py --private --no-mutants --cache --affected-since 6d4f6312 --jobs 2` after `make -j4` (symbol selection: 59 rows, 2 symbol fallbacks: movement, render_effects17; 8 pruned: audio_charsel, audio_combat, fidelity, item_textures, objects, path, session_party, viewport_monsters), at `ae453a69` | **59 pass**, 0 fail/error/skip; **996,661 cases** | 767 s (rows 1,374 s) |
| After `14e7290b` (one runtime line): `--affected-since 179ea2a8` after `make -j4` (12 rows: model_edge, meshdraw, movement, audio_domains, render_effects17, audio_callers, model_light, audio_items, terrain_remaining, render_effects16, worlds_f, terrain), no mutants | **12 pass**, **623,199 cases** | 514 s |
| `run_test_suites.py --affected 6d4f6312` (`MU_RECOVERY_INTEGRATION=0`, `MU_GATE_JOBS=2`) | first run: 1 failure, `test_native_worlds_slots2` (the host segfaulted in `mu_map_effects_in_sector` without sector lists; fixed in `14e7290b`); rerun: **8 suites, 1,495 tests, 1,265 passed, 230 skipped, 0 failures** | 390 s + 322 s |
| Unit modules (`MU_RECOVERY_INTEGRATION=1`): test_worlds_karutan (new; its private test runs the validator at 200 cases), native test_render_effects19 (with its private mutant run) | 14 tests OK | 14 s |
| Unit modules (portable, 6b): test_worlds_121, test_worlds_raklion, test_worlds_after2 (class list), test_worlds_after, test_worlds_slots, test_worlds_slots2, test_worlds_j, native test_render_worlds_a, test_native_worlds_121, test_native_worlds_slots2, test_native_fidelity2; test_worlds_s, test_native_worlds_s | 60 + 7 tests OK (8 skipped: private) | 8 s |
| `scripts/audit_repository.py` | 2,065 staged files, 0 rejected | 17 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; 144/144 | < 1 s |
| Tours, default draw (`live_time` too for Karutan): before = `6d4f6312`'s `mu-world` (main + #337), once | October 22 14, Karutan `live_time` 1, DATA-ACQ-002 32 | 39 + 6 + 81 s |
| Tours after (at `ae453a69`) and again with the final binary (`14e7290b`) | **October 22 14/14 (Karutan included) and DATA-ACQ-002 32/32 byte-identical** (PNG frames, OBJECT and light dumps, frame reports with the output path normalised); Karutan `live_time` 1/1 identical | 27 + 5 + 82 s; final 17 s |
| Two offline Karutan views (not live: tiles 205,17 and 49,169, the October 22 placements) | 0x81 crystal: 2,635 pixels change (region x 1100..1156, y 146..237); the 0x42 view: frame reports only (rand phase); final binary identical to `ae453a69` | 4 + 3 s |

Steward validators: validate_worlds_karutan (mutants: yes, new; done once at `179ea2a8`), validate_render_effects19
(mutants: done once at `179ea2a8`, its checks changed), validate_render_worlds_a (mutants: done once at `ae453a69`,
its Karutan cases changed), and without mutants the 59 rows of `--affected-since 6d4f6312` (ran at `ae453a69`):
validate_charsel_world, validate_login_world, validate_meshdraw, validate_model_light, validate_model_edge, validate_object_render, validate_movement, validate_world_fidelity, validate_terrain_remaining, validate_render_worlds_a, validate_icarus, validate_worlds_b, validate_icarus_c2, validate_worlds_d, validate_worlds_e, validate_worlds_f, validate_worlds_g, validate_audio_callers, validate_worlds_h, validate_worlds_i, validate_map_effects, validate_audio_domains, validate_worlds_j, validate_worlds_k, validate_audio_items, validate_worlds_o, validate_worlds_n, validate_worlds_p, validate_worlds_r, validate_world_tile_folder, validate_worlds_g2, validate_world_light_name, validate_worlds_p2, validate_worlds_r2, validate_worlds_q, validate_worlds_q2, validate_worlds_after, validate_worlds_g3, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_terrain, validate_app_polish1, validate_worlds_s, validate_worlds_s2, validate_worlds_after6, validate_worlds_s3, validate_worlds_slots, validate_worlds_slots2, validate_worlds_121, validate_worlds_raklion, validate_worlds_karutan, validate_render_effects16, validate_worlds_slots3, validate_item_callers, validate_render_effects18, validate_render_effects17, validate_render_effects19. Then the 12 rows whose compiled inputs `14e7290b` changed, again at `14e7290b`:
validate_model_edge, validate_meshdraw, validate_movement, validate_audio_domains, validate_render_effects17,
validate_audio_callers, validate_model_light, validate_audio_items, validate_terrain_remaining,
validate_render_effects16, validate_worlds_f, validate_terrain.

Env:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_SNAPSHOT_DIR=<mu-mac-tools>/native/scratch`;
- `MU_LANG_DIR=<mu-mac-tools>/native/scratch/lang`, `MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`;
- `MU_LIGHT_SNAPSHOT=$MU_SNAPSHOT_DIR/light/live/dumps/login-a.light`, `MU_LIGHT_OBJECTS=$MU_OBJECTS_PLAIN_DIR/EncTerrain95.plain`;
- `MU_PATH_DIRECTIONS=$MU_EVIDENCE_DIR/x86-guest-sec3-25/main-01ced000.bin`;
- `MU_VALIDATOR_CACHE=<mu-mac-tools>/native/cache/validators`;
- optional `--lang-dir` with RENDER-EFFECTS-008's `mapeffects.tsv` for validate_render_effects19's private `map_records`.

## Fidelity (Karutan vs live, October 22 capture)

`fidelity_tour.py`, default draw and `live_time` (identical), `MU_LANG_DIR` = the canonical lang. The one Karutan
view is `80-karutan` (tile 125,123), from the 14-view October 22 tour. The live window PNG of that session is gone,
so the live comparison is the per-field OBJECT scoreboard and the light dumps.

| Field vs live | 80-karutan before → after |
|---|---|
| Objects matched (live 2,143) | 2,143 → 2,143 |
| Static OBJECT field differences (after flag, action, light, hidden/blend mesh, …) | 0 → 0 |
| Frame light near the hero, mean abs | 0.0148 → 0.0148 |
| Native output (PNG frames, OBJECT and light dumps) | byte-identical |

- **No live delta, and why (live).**
  - The six type 0x42 objects lie 7,137..10,428 units from the hero, and the one 0x81 lies 13,304 units away. All
    are beyond the far plane (3,258), so RenderObject never draws them and the custom slot never runs on them.
    In live they sit at action 0, frame 0.
  - The flag types in view were already flagged by the A route, and live agrees.
- **Offline views** at the 0x81 crystal (tile 205,17) and the 0x42 pair (49,169), with the same placements (not
  live):
  - The crystal now glows: the 0x85bb-textured, grey-pulsed mesh 1 plus its additive pass. Before, the generic
    RenderBody drew it dark.
  - The 0x42 view changes only in the frame reports: the action choice draws rand.
- PNGs (local, window-only, before | after): `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-karutan/png/80-k81-before-after.png`
  (half size) and `80-k81-zoom-before-after.png` (the crystal, ×4).

## Census

The slot census counted Karutan's custom `0x00e14596` and after `0x00e1543e` as "V A" in 144/144:
- the custom slot was compared only on its flag branches: 0x42's action choice and 0x81 were missing, and the world
  test was the runtime's;
- the after slot copy lacked the StreamMesh writes.

The row now reads "V KARUTAN" (whole), and the JSON scopes say so. Aquila's visual scope notes the lone-sector
placement. The count stays 144/144. The character and login scene rows (93, 94) still read "V A"; this lane did not
re-check their scope.

## What's left

- Karutan's types 0x877 and 0x87a..0x87d are unreachable (types > 300) and are not ported.
- No live image of the new Karutan branches: the October 22 tile has no 0x42 or 0x81 in view. The live window PNG
  is gone, too. A capture near the 0x42 group (about tile 49,169) or the 0x81 crystal (205,17) would show them.
- World 145 stays Unicorn-only: no decoded placements, no capture (it needs level 1650).
- Still open from 121: the particle visual's stale comment (`reconstructed/particles/visual.c` line 131).

Local files kept: `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-karutan/png/80-k81-before-after.png` and
`80-k81-zoom-before-after.png`. Everything else (tour renders, scratch, the before binary and its worktree, build
dirs) is deleted.
