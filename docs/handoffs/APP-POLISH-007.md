# APP-POLISH-007: demo characters' vitals, inventory wings, Retina input

Claude Opus 5.5 lane, 2026-11-07. Branch `claude/app-polish-007`, worktree `~/Documents/MTM/worktrees/app-polish-007`,
from main `e68829a6` (#329), merged with `c5ed13dd` (#328, #330). Offline only: no original client, launcher, live
read, account, network or protection work. The installed Native Preview, its settings, the Wine play app and the
staged Wine app were not touched. Fixture data only: no stat editing, damage, combat-rule or power change.
Addresses and evidence labels: [client-app-polish7](../research/client-app-polish7.md).

## 1. Every demo character's orbs: current = maximum

**Cause.** The world seed set maxima only for the recorded level-1 Dark Knight (APP-POLISH-003). The other classes got
their current HP/MP/SD/AG from the fixture server's resource answer (combat's DK HP 1100, the progress fixture's MP,
SD and AG) and maxima 0. So Windleaf's orbs read `1100/0` and `778/0`.

**No client formula.** The original never computes these maxima. Every store into CharacterAttribute `+0x70/+0x74/
+0x7c/+0x84` is in a server answer: the join `0x0124cc64` (block `0x0124d1bf..0x0124d365`), the level up `0x01250b05`,
the stat answer `0x01223f04`, and two more handlers at `0x0125133e`/`0x0126202e`. The third-class setters
`0x00a001fb..0x00a00264` have no caller. The formula table `0x00993099` adds only combat values.

**Fix.**
- `native/session/domains/hero.c`: the seed applies the join answer's own vitals block (`hero_join_vitals`: eight u16
  words, a maximum below 1 becomes 1), verified against `0x0124d1bf..0x0124d365` (below).
- `native/fixture/hero_join.h`: the values. The recorded Dark Knight where the profile matches (class byte 1,
  level 1, 28/20/25/10/0), else the progress fixture's DEMO join maxima for the class, level and stats the fixture
  server is given (`native/fixture/progress_demo.h`, moved out of `behaviors/progress.c`, unchanged; the server's
  A0/30, A0/06 and A0/11 answers already use it).
- `native/world`: `world_rt_hero_join` feeds the seed from the same join data as the fixture lines. The combat HP
  default is `MU_WORLD_HERO_HP_JOIN`, resolved to the hero's join HP maximum; `--hero-hp N` still wins.

| Character (row) | Fixture profile | HP / MP / SD / AG (current = max) | Source | Before (HUD, `max=`) |
|---|---|---|---|---|
| Nightfall (0) | class 0, level 1, start stats | 600 / 600 / 51 / 39 | demo rule | 1100/0, 600/0, 51/0, 39/0 |
| Ironclad (1) | class 1, level 1, 28/20/25/10 | 1100 / 200 / 52 / 25 | recorded live join (FryeZEN2) | unchanged |
| Windleaf (2) | class 2, level 320, 22/1302/20/15 | 1119 / 778 / 1775 / 284 | demo rule | 1100/0, 778/0, 1775/0, 284/0 |
| Spellblade (3) | class 3, level 1, start stats | 1100 / 600 / 65 / 41 | demo rule | 1100/0, 600/0, 65/0, 41/0 |
| Crownlord (4) | class 4, level 1, start stats | 900 / 400 / 66 / 28 | demo rule | 1100/0, 400/0, 66/0, 28/0 |

The demo rule gives the recorded Dark Knight the same 1100/200/52/25. Before values: main `e68829a6` built in a
temporary worktree, headless, the bundled session, character-select row N. After: this branch, the same runs.

## 2. Inventory wings 0x2382..0x2385: faithful, unchanged

RenderObjectScreen `0x016c2d82` → RenderPartObject `0x017e63f4` (`0x016c33d1`) → RenderObjDraw `0x0176ce74`
(`0x017e7960`/`0x017e7997`). Under Unicorn RenderObjDraw draws mesh 1, 2, 1 for `0x2382`/`0x2383`, and mesh 0 then
mesh 2 three times for `0x2384`/`0x2385`. This holds in all 320 states tried (levels 0..15, hidden mesh -1/0/1/2,
render types 0/2/0x102/0x40042), so the other mesh is never drawn. Native recipes give the same lists. The item pass
`glOrtho(0, W, 0, H, 20, 2000)` (`0x00abfe8d`) equals native's projection. Widening native near/far to ±20000 gives
a byte-identical render, so nothing is depth-clipped. The original shows the same upper part. No change.

For RENDER-ITEMS-002S (not changed here): with OBJECT hidden mesh 1 or 2 the native recipes refuse these four types
(no draws) while the client draws (160 of the 320 states). Inventory and ground items use -1/0.

## 3. Retina input

- Real mouse events were already right: SDL points × drawable/window (`main.c`, `input_sdl.h`), GFx divides back
  (`mu_gfx_layer_mouse`).
- The input script was not: its positions were drawable pixels, so Retina needed doubled numbers. Now they are
  **window points** in windowed mu-client and mu-world (`mu_world_rt_action_scaled`, `click:X,Y`/`dblclick:X,Y`
  scaled the same way). Headless and 1x: scale 1, unchanged. [client-input](../research/client-input.md) documents it.
- mu-client gains windowed `event:VERB:X,Y` (move, ldown, lup, rdown, rup): it queues an SDL mouse event at window
  points, which the event loop handles like a system event. The windowed proof uses it to show that a real click
  hits, without the desktop pointer.
- UI scale: GFx stage = drawable / scale, so the HUD and Warps window keep the original's 1600×1000 layout, drawn at
  2×. The windowed Warps frame downscaled by 2 vs a headless 1600×1000 frame: mean abs diff 2.63/2.30/1.87 per
  channel (a 1.1× control: 15.98/14.10/11.17). The native-only offline label is drawn in drawable pixels (half size
  on Retina).

## Proofs (builds from this worktree; final ones at `82ce8a2a`)

| Proof | Result | Wall time |
|---|---|---|
| Windleaf headless (row 2, key 2, `MU_HUD_TRACE`), 201 / 800 frames | HUD = session = 1119/778/1775/284, `max=` the same, all samples (5 / 29); skill 2044 `ok`, `skill_casts` 1 | 8.9 s / 20.5 s |
| Rows 0..4 headless, main vs branch, 220 frames | table above | ~9 s each |
| DK Hound journey (`mu-world`, Lorencia 203,131, `40:attack:hound`) | 1100/1100, 200/200, 52/52, 25/25 → one hit 1077/1100; identical on main | 4.3 s |
| Elf in `mu-world --class 2`, same journey | main 1100/0 → hit 1077/0; branch 800/800 → hit 777/800 | 4 s each |
| DK windowed (1600×1000 pt, 3200×2000 px), 42 s | HUD 1100/1100, 200/200, 52/52, 25/25 in all 33 samples | 44 s |
| Windowed Warps, script `click:` at window points 122,257 / 122,324 | branch: `travel: world 0 -> 3`, `world 3 -> 2`; main: Warps opens, no travel | 44 s × 2 |
| Windowed Warps, `event:` SDL mouse events at the same window points | `world 0 -> 3`, `world 3 -> 2` | 44 s |
| `mu-render ui inventory`, main vs branch: wings level 0 and 13 + bow, controls 6571/55/2612, synthetic 12 | 8/8 byte-identical (`91b79f79…`, `da9fd01e…`, `50b8d38a…`, `2bb04c70…`) | 1.3–1.6 s each |

Screenshots (local, not committed), `~/Documents/MTM/mu-mac-tools/native/renders/app-polish-007/`, ≤ 760 px, demo names
only: `1-windleaf-orbs-before-after.png` (headless frame 200, main above, branch below), `2-warps-retina-window-points.png`
(the client's own framebuffer capture, Warps open), `3-devias-after-travel.png`, `4-inventory-wings-level13.png`.

## Checks (TEST BUDGET: no lane gate)

Heavy steps under `nice -n 10`, `make -j4`, `--jobs 2`; waited whenever the 1-minute load was above 14.

| Check | Result | Wall time |
|---|---|---|
| `make -j4` + `make -C native -j4 client world` at `82ce8a2a` | ok | 21.7 s |
| `validate_app_polish7` with mutants (once, final) | join 4,096 + seed 1,024 = 5,120 cases, 0 mismatches; 10/10 mutants caught, 0 equivalent | 4.1 s |
| Affected rows `--no-mutants --cache` at `82ce8a2a` (symbol-level selection after make, 21 rows) | 21 pass (below) | 519 s + 42 s |
| Private `test_app_polish2/5/6/7` | 20 tests OK (Windleaf cast, crowd HUD, original join block) | 56 s |
| 6b modules, portable (32 modules: app_polish2/4/5/6/7, input_router, session_*, fixture_hero/scenarios, layout_session, native_progress/combat/app/shell/hud/world2/ui/audio/perf004, world_parts, render_time_003, audio_*) | 246 tests; 3 failures that also fail on main `e68829a6` in this checkout (below), 1 error fixed (`test_app_polish5` read `START` from the moved table) | 150 s |
| `scripts/audit_repository.py` | 2,044 staged files, 0 rejected | 16.9 s |

Affected rows (cases, seconds): app_polish2 1,028 (3.2), app_polish4 10,485 (36.8), app_polish7 5,120 (1.5),
audio_callers 5,528 (5.3), audio_charsel 5,968 (3.4), audio_combat 19,548 (20.7), audio_domains 2,544 (22.5),
audio_items 3,000 (3.1), meshdraw 14,619 (70.8), model_edge 954 (132.0), model_light 1,433 (5.8), movement 6,614
(60.2), path 4,719 (42.2, `MU_PATH_DIRECTIONS`), render_effects16 424 (3.3), render_effects17 618 (7.0),
session_party 200 (0.7), terrain 583,500 (360.1), terrain_remaining 2,147 (3.9), viewport_monsters 1,963 (10.2),
worlds_f 1,818 (0.5), worlds_fog 4,044 (5.6). Thirteen of them are selected only because `gen_domains.py` reads
`native/session` and `native/fixture`; its output is byte-identical between main and this branch.

Pre-existing failures (identical on main `e68829a6` built in a temporary worktree here):
`test_session_skills.test_scenario_and_unsent_cast`, `test_session_combat.test_fight_frames_…`,
`test_fixture_scenarios.test_every_discovered_scenario_runs_in_make_test` (skills-state, combat-fight,
quest-progress, quest-routes: undecodable/unsent counts). Probably this checkout's environment (the same nine
expectations fail on main); not investigated further.

- Steward validators: validate_app_polish7 (mutants run once, 10/10), validate_app_polish2, validate_app_polish4,
  validate_worlds_fog, validate_movement, validate_path, validate_audio_callers, validate_audio_domains,
  validate_audio_items, validate_audio_combat, validate_audio_charsel, validate_session_party, validate_meshdraw,
  validate_model_edge, validate_model_light, validate_terrain, validate_terrain_remaining, validate_viewport_monsters,
  validate_worlds_f, validate_render_effects16, validate_render_effects17 (ran at `82ce8a2a`, no mutants except
  app_polish7). Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, `MU_SECTION3=…/x86-linux-capture-04/main-01ced000.bin`,
  `MU_EVIDENCE_DIR=<main checkout>/evidence`, `MU_VALIDATOR_CACHE`, `MU_SNAPSHOT_DIR=~/Documents/MTM/mu-mac-tools/native/scratch`
  (app_polish4), `MU_PATH_DIRECTIONS=~/Documents/MTM/main-exe-study/evidence/path-table-live-01/live-a-01ced000.bin`.

## Limits

- Values for everyone but the level-1 Dark Knight are demo-server values; the client has no rule and there is no
  recording. The list levels (350, 400, 320, 280, 250) stay display data; only Windleaf has join stats.
- The real NSEvent → SDL conversion is SDL's; the windowed check starts at the SDL event.
- The wing verdict reaches RenderObjDraw's mesh calls; no original-client inventory capture.

## For the next APP-REFRESH

Reinstall from a main with this PR. Check: Windleaf's orbs 1119/1119 and 778/778, SD 1775/1775, AG 284/284; Ironclad
1100/1100 and a Hound hit → 1077; Warps travel by clicking 122,257 / 122,324 window points (the 1x numbers) in a
Retina window. No Native Data change.

## Cleanup

After the ready line: `scratch/app-polish-007` (helpers, runs, session copy, validator reports), this worktree's
`native/build`, and the temporary `worktrees/app-polish-007-base` are deleted. The four screenshots are kept for
review. The worktree stays until the steward merges.
