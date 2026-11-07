# APP-REFRESH-008

Implementation handoff, 2026-11-07. Worktree `worktrees/app-refresh-008`, branch `claude/app-refresh-008`. Claude
Opus 5.5 lane. Offline only: no original client, launcher, live read, account, network or protection work. The
owner's Wine play app, its prefix settings and the staged Wine app were not touched. Docs-only PR (brief rule 6c).

## What the installed app now has

The Native Preview was reinstalled from main **`f2370871`** (#334, the latest main at build time). It has everything
since APP-REFRESH-007 (`53cffd00`):

- #328 RENDER-EFFECTS-018: Muun effect records 16/16, Uruk `0x806e`/12;
- #330 RENDER-ITEMS-CALLERS-001: players, player-model actors and ground items pass the item pose, so the item
  pre-draw programs create their sprites in the world;
- #331 RENDER-ITEMS-002S: item bodies 1,345 → 1,359;
- #332 RENDER-EFFECTS-019: the 19 unfollowed map-object records at their bones, the lone-sector rule, Test Area
  121's three particle kinds;
- #333 APP-POLISH-007: every demo character's join vitals as fixture data (Windleaf's orbs no longer read 1100/0
  and 778/0), combat HP follows the hero, the inventory-wing verdict (faithful, unchanged), `--input-script` mouse
  positions in window points;
- #334 HERO-ITEMS-001: the hero's worn items typed from their Item.bmd records (the shipped demo draws the same).

**Not included:** RENDER-ITEMS-002T, RENDER-WORLDS-RAKLION and REGRESS-002 had not merged when the build started
(05:27 CST; `origin/main` was still `f2370871` at 05:36). Nothing that had merged is missing.

**Order of events:** the worktree was added detached at `f2370871`, so the bundle's `MUNativeCommit` is the main SHA.
Rollback first, then the Native Data diff, the build, and the install at 05:28. Every proof below ran on that build.
The branch was then created at the same commit for the docs.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` **f2370871**, real Ruffle.
  - Built with `nice -n 10 make -C native -j4`, `make -C native -j4 world client`, then
    `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`
    (bundles `Contents/Frameworks/libmugfx.dylib`, 17.9 MB).
  - The library is the same 22 Oct build that APP-REFRESH-006 and -007 bundled. `git diff 53cffd00 f2370871 --
    native/gfx` is empty, so it is not stale against this main.
  - No Preview was running (`pgrep -fl 'Native Preview'`: none). The old copy was removed and the new one installed
    with `ditto`. The strict deep signature check (`codesign --verify --deep --strict`) and `--check-bundle` pass
    (mu-client, network guard, GFx library (Ruffle)).
  - `--print-settings`: "GFx movies 179, text tables 31, object files 47, sound table yes; setup done".
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-008/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-007-53cffd00.app.zip` (11.8 MB, 57 entries, SHA-256
    `46a7b8b2…d7717ea4`);
  - `settings.json.before`, which selects `APP-REFRESH-006/Native Data` (unchanged by this lane).
  - To roll back, unzip the app into `~/Applications`. `settings.json` needs no change.
  - The `app-refresh-002/` to `-004/` rollbacks were deleted, as the task asked. `-005/` to `-008/` are kept.

## Native Data: kept (`APP-REFRESH-006/Native Data`)

No export input changed since APP-REFRESH-007.

- `git diff --stat 53cffd00 f2370871` over `scripts/build_native_data_export.py`, `live_lang_to_plain.py`,
  `live_effect_table_to_plain.py`, `live_objects_to_plain.py`, `extract_audio_tables.py`, `native_data_manifest.py`,
  `pins.py`, `native/data`, `native/app/Sources`, `native/app/bundle-dylibs.sh` and `native/app/Makefile`: **empty**.
- The same paths plus `live_lang_filters.py` and `native/gfx/gfxconvert.c` since `20b9d88b` (the exporter commit
  that built the set) are also empty. `native/gfx` did not change at all.
- The only script changes in the range are `scripts/gen_item_bodies.py` and `gen_item_owner_fx.py`. They generate
  compiled-in tables, not Native Data.
- The set already has the tables the new code reads: `lang/mapeffects.tsv` (#332's map-object records),
  `lang/muuneffects.tsv` (#328) and `objects/EncTerrain137.plain` (world 136).
- `mu-native-data check` on the folder: "Native Data manifest OK". `settings.json` was not changed.

## Journey proofs (installed app, `f2370871`)

**Smoke:** `--smoke --backend gl`, isolated logs/settings, `PATH=/nonexistent`, with and without `--audio`: ok,
world reached, Apple M5, guard `mu-nonet`, 0 connects, 0 inet, 0 lookups, 0 other calls denied.

**Headless:** the installed bundle's mu-client with the app's own launch plan (`--print-plan` over an isolated
support dir that holds a copy of the owner's settings), `--no-store`, isolated option settings, network guard loaded
(every run: 0 denials). The field session is the bundled one with `join 1 0 179,131 90`.

| Proof | Result |
|---|---|
| Selected-skill right-click cast (Budge Dragon) | `skill 19 at actor 10: ok`; `skill_casts` 1, 0 refused |
| Kill, drop, Space pickup | `kills` 1, `drops` 1, `space_picks` 1, 1 pickup request, 1 completed |
| Audio (option.ini `[DEFAULT]` `IsMusicPlay=1`, `Volum=9`; `--wav` over the same journey) | 898,228 stereo frames at 44.1 kHz; peak 31,656 = **−0.300 dBFS**; 0 samples above 31,656; 0 at full scale; RMS 4,708 |
| Warps travel M → Noria → M → Devias | `travel: world 0 -> 3` (175,117), `world 3 -> 2` (208,47); `travels` 2, `travel_plates_removed` 4, `plates` 1, `stale_plates` 0 |
| Arrival HUD and a Hound hit (`MU_HUD_TRACE=1`, 800 frames) | HUD = session = **1100/1100** HP, 200/200 MP, 52/52 SD, 25/25 AG for 13 samples; one hit → 1077/1100 for 16 samples; Hound killed (`kills` 1, `drops` 1). Travel run: 1100/1100 in all 15 samples |

- The cast journey used a copy of the bundled placement with `wander` removed (four lines changed). With wandering
  monsters, the Budge Dragon was no longer at 007's click point (820,287) at frames 83–191. The run cast skill 19 but
  killed nothing. In the still copy the dragon stands at its spawn, so the clicks went to 690,238.
- The Hound script ends with one `move:` action. mu-client prints the `input_*` counters only when a script action
  went to the world (`f->input_actions`); the run with only `click:X,Y` actions printed none.

**Windowed:** the installed app itself (`MuNativePreview --seconds 45`, isolated support, log and option dirs, muted,
the field session, `MU_HUD_TRACE=1`,
`MU_NATIVE_EXTRA_ARGS="--no-store --auto --hold 6 --input-script '…' --out-dir '…'"`). Travel 0 → 3 → 2:
`travel_plates_removed` 4, `plates` 1, `stale_plates` 0. HUD 1100/1100 in all 36 trace samples. 919 frames in 45.0 s
(about **20.4 fps**) at a **1504×936** drawable. Guard `mu-nonet`, 0 denials. Window name "Mu The Matrix Native
Preview — OFFLINE PREVIEW (no server connection)" (CGWindowList), no fps suffix (screenshot 1).

### Proofs for this refresh

**(a) Windleaf vitals (#333).** The bundled session as installed. Flow: login → character-select row 2 (`click:row:2`,
`dblclick:row:2`) → key 2 → right-click near 182,128.

| Run | HUD (`MU_HUD_TRACE`) | Cast / `{"effects": …}` |
|---|---|---|
| Headless, 1504×936, 220 frames | session = HUD = max = **1119/778/1775/284** (HP/MP/SD/AG) in all 6 samples | `skill 2044 at actor 10: ok`; `"skills":1,"sounds":2,"effects_created":121,"max_live_0x70a":1,"max_live_0x70c":11,"max_live_rings":66,"decals":1524,"decal_quads":56348,"unsupported":0` |
| Windowed installed app (`--seconds 25`, 1504×936), still placement, Bull Fighter at window point 420,490 | the same in all 17 samples | `skill 2044 at actor 8: ok`; the same line, with `decals` 1,504 and `decal_quads` 55,880 (they count drawn frames) |

- The orbs now read **1119/1119** and **778/778**, SD 1775/1775 and AG 284/284 (screenshot 2). APP-REFRESH-007 had
  `max` 0,0,0,0, so the orbs read "1100/0" and "778/0".
- The values come from the progress fixture's DEMO join maxima: `mu_fx_progress_demo_maxima` in
  `native/fixture/progress_demo.h` (the `MAXIMA[16][6]` class table and the start stats), for class 2, level 320 and
  the session's 22/1302/20/15. `native/fixture/hero_join.h` applies them, because Windleaf is not the recorded
  level-1 Dark Knight profile. These are demo-server values. The original client has no maxima formula.
- The cast numbers equal APP-REFRESH-007's and APP-POLISH-005's.

**(b) Windowed Warps travel in window points (#333): the Retina half not run.** The Mac now has one display,
1920×1080 at 1x (`system_profiler`: "UI Looks like 1920 x 1080"). APP-REFRESH-007 had a Retina 3200×2000 drawable.
The windowed run above reports a 1504×936 drawable for a 1504×936-point window, so the script scale is 1.
- The 1x half passes. The same window-point clicks as headless (Warps rows Noria 122,257 and Devias 122,324) open
  Warps and travel 0 → 3 → 2 to Devias 208,47.
- The scale-2 path (a Retina drawable) cannot run without a Retina display. mu-client has no switch that forces it,
  and this lane does not change display settings.
- APP-POLISH-007 verified that path on a Retina window: `click:` and `event:` at 122,257 / 122,324 travel. On a
  Retina display, rerun `travel-w.txt` (below) unchanged.

**(c) Inventory wings 0x2382..0x2385 (#333).** `mu-render ui inventory` from the same main, the installed game, time
123456, `MU_LANG_DIR` = installed Native Data `lang`, codes 6300..6303 and 2096 (wings `0x2382`..`0x2385`, bow
`0x1316`):

| Level | Models drawn / missing | Triangles | Framebuffer SHA-256 |
|---|---|---|---|
| 0 | 5 / 0 | 7,455 | `91b79f79…cca3` |
| 13 | 5 / 0 | 10,775 | `da9fd01e…82c5` |

- Both hashes equal APP-REFRESH-007's and APP-POLISH-007's.
- The wings are **not drawn in full, and that is faithful**. APP-POLISH-007 showed under Unicorn that the client's
  RenderObjDraw `0x0176ce74` draws mesh 1, 2, 1 for `0x2382`/`0x2383` and mesh 0, then mesh 2 three times for
  `0x2384`/`0x2385`. That held in all 320 states, so the long lower mesh is never drawn. #333 therefore changed
  nothing here (screenshot 3).
- This is an offline native render, not compared with an original-client capture.

**(d) World pre-draw item effects (#330).**
- **The shipped Lorencia crowd shows none.** No `item_pre_draw` line at 140,130 in mu-client or in `mu-world`. The
  demo players' kits wear none of the 26 types that have a pre-draw program (#330 found the same for the README
  crowd).
- **With #330's test kits** (Blade: sword `0x0b27`, shield `0x1748` and wing `0x2382`; Archer: bow `0x1316` and wing
  `0x2394`; Maul: mace `0x0f1c`; Seraph: sword `0x0b4c` and wing `0x2384`) passed to the installed mu-client
  (`--players`, hero joining at 128,127), the glows and sparkles draw on the players (screenshot 4).
- mu-client prints no `item_pre_draw` line, because only mu-world and mu-walk call `world_rt_report_summary`. So the
  counts come from `mu-world` built at the same main, with the installed Native Data, GL, 640×400 and 60 frames. The
  ground drops are `0x2384`, `0x0b4c` and `0x1311`:

| Tile | Players drawn (`pre_effects`) / refused / hidden | Ground drawn / refused | `sprites_created` |
|---|---|---|---|
| 128,124 | **138 / 2** / 0 | **36 / 0** | 174 |
| 140,130 | 87 / 1 / 4 | 0 / 0 (out of view) | 87 |
| 140,130, shipped crowd | no line (0 programs ran) | — | — |

- The refusals are wing `0x2384`'s OBJECT-owned particles, as #330 records.
- `native.tests.test_native_world_predraw` (private, `mu-walk` soft 320×240 at 128,124) passes 7/7. It asserts
  #330's 92/2 for players and 18/1 for the ground.
- These scenes are test fixtures, not the shipped demo. The task's "Lorencia demo 0/113 → 110/3" is that test scene.

**(e) Map-object effects at their bones (#332).** World 136 (Burning Kethotum, `Data/World137`, objects
`EncTerrain137.plain` in Native Data). Session `join 1 136 127,17` (the DATA-ACQ-002 capture tile); 200 frames;
frame 199. Installed app against the APP-REFRESH-007 rollback app (`53cffd00`):
- Both: rc 0, world 136, scene 6.
- **15,146 of 1,024,000 pixels change** (mean abs diff 0.39/0.41/0.00 per channel; bbox 266,161..448,479).
- In the crop (screenshot 5, 007 left, installed right), the type-25 record's yellow glow (lighting02-yellow03, bone
  29, not following) moves from the pit at the object origin up to the crystal's top, its bone. That matches
  RENDER-EFFECTS-019's tour (z 184 → 440; |d| against the live window 6.534 → 6.444).
- Test Area 121's three particle kinds (also #332) cannot show: Native Data still has no objects for world 121
  (APP-REFRESH-007 proof e).

**(f) Muun/Uruk (#328): skipped.** No demo scene shows one: the demo session, players and placement have no Muun
and no Uruk object.

**Quest accept offline (007's proof b).** `test_native_quest.LorenciaDemo`'s scripted dialogue, run with `mu-world`
from the same main, the installed Native Data `lang` and `gfx`, the bundled libmugfx and no `MU_QUEST_SCENARIO`.
Result: `"accepted":1,"completed":1,"progress":3,"undecodable":0,"active":[]`. Frame 60 reaches "dialogue request
901: the NPC's quest list (demo server)", and no request 902 appears.

**Screenshots** (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-008/`, each 760 px
wide or less and quantized (0.95 MB in all). Demo names only (Ironclad, Windleaf, Hero, Aeris, #330's test names
Blade/Archer/Maul/Seraph, demo monsters).

| File | Shows |
|---|---|
| `1-window-devias-after-warps-travel.png` | window-only capture of the installed app after Warps travel 0 → 3 → 2: title bar "… OFFLINE PREVIEW (no server connection)", Devias 208,47, HUD 1100/1100 |
| `2-windleaf-orbs-2044-rain.png` | windowed installed app, client framebuffer (`shot:`) at frame 125: orbs 1119/1119 and 778/778, skill 2044's rain, rings and craters |
| `3-inventory-wings-level13.png` | inventory grid at level 13, 2× nearest: wings `0x2382`..`0x2385` (upper meshes, as the client draws) and bow `0x1316` |
| `4-predraw-test-kits-installed-client.png` | installed mu-client headless at 128,127 with #330's test kits: pre-draw glows on Blade's and Seraph's wings |
| `5-world136-bone-glow-before-after.png` | world 136 at 127,17, frame 199: 007 app (left), installed app (right); the glow moves to the crystal's top |

## Checks (TEST BUDGET: no lane gate; docs-only PR, rule 6c)

Heavy steps under `nice -n 10`, `make -j4`. Load was 5.4–10.4 (1 min) through the proofs and memory 56–66% free.
Other lanes' builds pushed it to 35 during the audit; the last module run waited until it was back under 14.

| Step | Result | Wall time |
|---|---|---|
| Rollback zip + settings copy | 11.8 MB, 57 entries | 0.8 s |
| Native Data input diff | empty since 53cffd00 (and since 20b9d88b) | < 1 s |
| Build at `f2370871`: `make -C native -j4`, `world client`, `make -C native/app -j4 MUGFX_LIB=…` | ok; signed, `--check-bundle` ok | 15 s + 9 s + 5 s |
| Install (`ditto`) + strict signature + `--check-bundle` + `mu-native-data check` | ok | < 1 s |
| Installed smoke, without and with `--audio` | ok, 0 network | 12 s + 12 s |
| Headless journey with `--wav` (still placement) / Hound+HUD (800 frames) / travel | see above | 11.2 s / 15.7 s / 10.4 s |
| Windowed travel (`--seconds 45`) | see above | 47 s |
| (a) Windleaf headless / windowed | see above | 10.1 s / 27 s |
| (c) 2 inventory renders | 5/5 models each | 1 s + 1 s |
| (d) installed client test kits / `mu-world` × 3 / `test_native_world_predraw` (private) | see above; 7/7 OK | 10.1 s / 2–4 s each / 9 s |
| (e) world 136 × 2 apps | see above | 12.5 s + 12.5 s |
| Quest, `mu-world` 420 frames | accepted 1 | 5 s |
| `scripts/audit_repository.py` (one new file) | 2,058 staged files, 0 rejected | 19 s |
| Rule 6c doc modules: `tests.test_world_captures_2`, `tests.test_repository_policy` | 13/13 OK | 0.6 s |
| Rule 6c doc modules: `native.tests.test_native_item_textures`, `native.tests.test_native_data_manifest` (from the repo root, brief 8d) | 23 OK, 1 skipped | 7 s |

- Steward validators: none (docs only, rule 6c). No code or tool changed.

## Follow-ups

1. **Retina windowed proof.** Rerun `travel-w.txt` on a Retina display; the 1x half passed here (proof b).
2. **No pre-draw types in the shipped demo.** The app's crowd and hero wear none of the 26 pre-draw types, so the
   installed demo shows none of #330's sprites. A demo kit with one (e.g. wing `0x2382` on a crowd player) would.
   That is a demo-data choice for an APP-POLISH lane. mu-client could also print the `item_pre_draw` line, as
   mu-world does.
3. **Hero items are files** (HERO-ITEMS-001): level, option and ext are 0, so the hero shows no level glow yet.
4. **Test Area 121 has no objects** in Native Data, so #326's slots and #332's 121 kinds only show with
   RENDER-WORLDS-121's demo layout.
5. **Muun/Uruk** (#328) cannot be shown by the demo session.
6. **libmugfx** is still the 22 Oct build (`native/gfx` unchanged since `53cffd00`).
7. Still open from APP-REFRESH-006/007: no `sounds` counter for the DK field journey; ground skill 2045 unreachable
   (no Skill(Kor) record); weapons spill past their cells; Arca War worlds 93/97/102/112 not installed; worlds
   145/95/110 draw no objects. The old export set `scratch/native-data/export.before-app-refresh-006` and the
   APP-REFRESH-001/legacy Native Data folders can go (the owner's call).
8. Journey scripts: the wandering Budge Dragon no longer meets 007's click point, so use the still placement below.
   The Hound script needs one decoded action (e.g. `move:`) for the `input_*` counters to print.

## Cleanup

- Kept: the rollback folder `rollback/app-refresh-008/` and the five screenshots.
- Deleted after the ready line: `scratch/app-refresh-008` (helpers, sessions, runs, frames, WAV, the unzipped rollback
  app, inventory renders) and this worktree's `native/build`. The worktree stays until the steward merges.
- Deleted earlier: `rollback/app-refresh-002/`, `-003/` and `-004/` (11 MB each).
- Helpers, rebuildable from this file and APP-REFRESH-005..007:
  - `hl.py`: a headless run of an app bundle's mu-client with the app's plan (`--app`, `--session`, `--size`,
    `--frames`, `--every`, `--audio`, `--hud`, `--auto`, `--script(-file)`, extra args after `--`), with
    `MU_NATIVE_SETTINGS_DIR` and `MU_NONET_REPORT` in the run folder.
  - `runw.sh`: the GUI app with `--seconds`, isolated dirs, a muted option.ini and `MU_HUD_TRACE`. `SESSION` and
    `EXTRA` override the session and the flow arguments. Window-only shots come from a compiled
    `~/Documents/MTM/mu-mac-tools/winshot.swift`; keep only the titled window, because the matcher also catches the
    app's small helper windows.
  - The field session: the bundled `demo-session.txt` with `join 1 0 179,131 90`.
  - `still-placement.txt`: the bundled placement without `wander`.
  - `hj-still.txt`: `83:move`, `84:rdown`, `86:rup` at 690,238; left clicks there at 131/191/251; Space at
    300/340/380/420.
  - `hound.txt`: as in APP-REFRESH-005, plus `790:move:640,400`.
  - `travel-hl.txt`: as in APP-REFRESH-005.
  - `travel-w.txt`: M at 300, `shot` at 320, click 122,257 at 331, M at 600, click 122,324 at 631, `move` at 700.
  - `wl-w.txt`: the Windleaf flow with a right-click at 420,490 and `shot` at 125/140.
  - `w136.txt`: `join 1 136 127,17`.
  - `predraw-players.txt`: `test_native_world_predraw.PLAYERS`.
