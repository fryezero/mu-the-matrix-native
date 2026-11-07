# APP-REFRESH-009

Implementation handoff, 2026-11-07. Worktree `worktrees/app-refresh-009`, branch `claude/app-refresh-009`. Claude
Opus 5.5 lane. Offline only: no original client, launcher, live read, account, network or protection work. The
owner's Wine play app, its prefix settings and the staged Wine app were not touched. Docs-only PR (brief rule 6c).

## What the installed app now has

The Native Preview was reinstalled from main **`a7f7b247`** (#343, the latest main at build time). It has everything
since APP-REFRESH-008 (`f2370871`):

- #335 REGRESS-002: tests and tooling only (scenario tools run from the repository root);
- #337 RENDER-WORLDS-RAKLION: Raklion 57/58's custom and after slots, whole, through Test Area 121's routine; the
  0x14 statue's WATERFALL particles;
- #338 APP-POLISH-008: session equipment records (`SLOT=FILE@GROUP:INDEX[:LEVEL[:OPTION[:EXT]]]`); new Lorencia
  crowd outfits with pre-draw item effects; Ironclad's Cookery Short Sword 0:68 +9 excellent with its level glow;
- #339 RENDER-EFFECTS-020: the cloak wings' (`0x2384`/`0x2385`) OBJECT-owned particles are created;
- #340 RENDER-WORLDS-KARUTAN: Karutan 80/81's slots, the 0x81 crystal's grey pulse, world 145's bone placements;
- #341 RENDER-ITEMS-002T: item bodies 1,359 → 1,363; wings `0x2382`..`0x2385` draw at OBJECT +0x68 = 1/2;
- #342 RENDER-EFFECTS-021: particle kinds `0x7ffd`/0x1b, `0x7f66`/5, `0x8180`/5; armour owner programs in the world;
- #343 INVENTORY-FX: the hero's equipment in the inventory window, the icons' level/option/ext (excellent pass).

**Not included:** RENDER-ITEMS-002U and RENDER-ITEMS-CLOAK. Neither had a PR or a ready line when the build started
(09:06 CST; open PRs: none; `ready-prs.txt` ended with #343). RENDER-ITEMS-CLOAK (#344) was opened at 09:13 and
merged at 09:30 (main `02e4d94d`), about 25 minutes after the build, while the docs were being written. That is
outside the ~20-minute window, so it was not rebuilt. No shipped demo character wears a cloak type (APP-POLISH-008
left `0x2382`/`0x2394` out), so it changes no shipped demo scene. The next refresh picks it up. #342 merged at about 08:53 and #343 (steward batch 77)
at about 09:05, while this lane waited on its private run, so both are in the build. Nothing that had merged is
missing.

**Order of events:** rollback first (08:29), then the full private native/tests run on `138b756e`, the build-time
Native Data diff, the build, and the install at 09:06. The worktree was detached at `a7f7b247`, so the bundle's
`MUNativeCommit` is the main SHA. Every proof below ran on that build. The branch was created at the same commit for
the docs.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` **a7f7b247**, real Ruffle.
  - Built with `nice -n 10 make -j4` (repository root), `make -C native -j4 world client`, then
    `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`
    (bundles `Contents/Frameworks/libmugfx.dylib`, 17.9 MB).
  - The library is the same 22 Oct build that APP-REFRESH-006 to -008 bundled. In `f2370871..a7f7b247`, `native/gfx`
    changed only in `mu_gfx_layer.c/.h` (#343). Those are compiled into mu-client and mu-world (`native/Makefile`
    `GFX_SRC`), not into the Ruffle library. `native/gfx/mugfx` and the Ruffle patches did not change, so the
    library is not stale against this main.
  - No Preview was running (`pgrep -fl 'Native Preview'`: none). The old copy was removed and the new one installed
    with `ditto`. The strict deep signature check (`codesign --verify --deep --strict`) and `--check-bundle` pass
    (mu-client, network guard, GFx library (Ruffle)).
  - `--print-settings`: "GFx movies 179, text tables 31, object files 47, sound table yes; setup done".
- **Demo files are app resources, not Native Data.** #338's `demo-characters.txt` (session) and
  `lorencia-demo-players.txt` (world) are copied into `Contents/Resources/session` and `Contents/Resources/world` by
  `native/app/Makefile`. The installed copies are byte-identical (`cmp`) to `a7f7b247`'s files. The demo run below
  shows them in use.
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-009/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-008-f2370871.app.zip` (11.8 MB, 66 entries, SHA-256
    `7be241a4…34070a66`);
  - `settings.json.before`, which selects `APP-REFRESH-006/Native Data` (unchanged by this lane).
  - To roll back, unzip the app into `~/Applications`. `settings.json` needs no change.
  - The `app-refresh-005/` rollback was deleted, as the task asked. `-006/` to `-009/` are kept.

## Native Data: kept (`APP-REFRESH-006/Native Data`)

No export input changed since APP-REFRESH-008.

- `git diff --stat f2370871 a7f7b247` over `scripts/build_native_data_export.py`, `live_lang_to_plain.py`,
  `live_effect_table_to_plain.py`, `live_objects_to_plain.py`, `extract_audio_tables.py`, `native_data_manifest.py`,
  `pins.py`, `live_lang_filters.py`, `native/data`, `native/app/Sources`, `native/app/bundle-dylibs.sh` and
  `native/app/Makefile`: **empty**.
- `native/gfx`: only `mu_gfx_layer.c/.h` (client code, above). `gfxconvert.c` is unchanged since `20b9d88b` (the
  exporter commit that built the set), as are the other paths above.
- The script changes in the range are generators of compiled-in tables (`gen_item_bodies.py`, `gen_item_owner_fx.py`,
  `classify_item_bodies.py`), `run_fixture_scenarios.py` (#335) and validators.
- The set already has what the new code reads: `objects/EncTerrain58.plain` (Raklion 57), `EncTerrain81.plain`
  (Karutan 80) and `EncTerrain145.plain`. World 145's placements (`EncTerrain146`) do not decode, as #340 records.
- `mu-native-data check` on the folder: "Native Data manifest OK". `settings.json` was not changed (`cmp` with
  `settings.json.before`).

## Private native/tests (brief 8d, from the repository root, private-env.sh)

| Run | Selection | Result | Wall |
|---|---|---|---:|
| Full, at `138b756e` (main before #342/#343), `MU_GATE_JOBS=2` | 145 modules | **969 tests: 941 passed, 27 skipped, 1 failed** | 1,251 s |
| Rerun of the failed module and the 12 modules with skips, one process each, plus `MU_GFX_LIB` (bundled libmugfx) and `MU_LANG_DIR` (Native Data `lang`) | 13 modules | **136 tests OK, 20 skipped** | 352 s |
| `--affected-since 138b756e` at `a7f7b247` (build SHA), `MU_GFX_LIB` set | **all 147 modules** (#342/#343 touch `scripts/validators.toml`, which selects everything) | **983 tests: 962 passed, 20 skipped, 1 failed** | 1,154 s (+41 s selection) |
| The failed test alone, at `a7f7b247` | `test_inventory_fx.InventoryScene.test_ironclad_equipment` | **1 test OK** | 10 s |

- **The full run's failure, `test_audio_items.test_original_ground_audio`, is a test-order effect in a fresh
  worktree.** Its validator dlopens `reconstructed/items/libclient_items.dylib`, which the root `make` does not build.
  Another module built it at 08:36, after this module had run. Rerun: 4/4 OK. It also passed in the second pass.
- **The second pass's failure is a concurrency flake.** `InventoryScene` (new in #343) starts `make -C native world`
  in `setUpClass` and then runs mu-world. Under `jobs=2` the run exited non-zero with empty stderr. Alone: OK.
- The 27 skips of the full run were missing variables: `MU_GFX_LIB` is not in private-env.sh. With it (and
  `MU_LANG_DIR`), 14 of those tests ran and passed. The 20 that still skip need an in-tree `native/gfx/mugfx` build or
  the pinned Ruffle checkout (13), the Metal GFx library (2), `MU_NAMES_GFX_MOVIES` / `MU_QUEST_MOVIES` (3), a pinned
  langread snapshot (1) or `mugfx` (1).
- Run in one unittest process, 3 modules error with `KeyError: 'MU_LANG_DIR'` (`test_native_map.PrivateTravel`,
  `test_native_skill.Installed`, `test_render_effects18.InstalledMuun`). Another module in the same process removes
  the variable. In their own processes (as the runner does), all three pass.

## Journey proofs (installed app, `a7f7b247`)

**Smoke:** `--smoke --backend gl`, isolated logs and support dirs, `PATH=/nonexistent`, with and without `--audio`:
ok, world reached, Apple M5, guard `mu-nonet`, 0 connects, 0 inet, 0 lookups, 0 other calls denied.

**Headless:** the installed bundle's mu-client with the app's own launch plan (`--print-plan` over an isolated
support dir that holds a copy of the owner's settings), `--no-store`, isolated option settings, network guard loaded
(every run: 0 denials), 1280×800. The field session is the bundled one with `join 1 0 179,131 90`.

| Proof | Result |
|---|---|
| Selected-skill right-click cast (Budge Dragon, still placement) | `skill 19 at actor 10: ok`; `skill_casts` 1, 0 refused |
| Kill, drop, Space pickup | `kills` 1, `drops` 1, `space_picks` 1, 1 pickup request, 1 completed |
| Audio (option.ini `[DEFAULT]` `IsMusicPlay=1`, `Volum=9`; `--wav` over the same journey) | 862,948 stereo frames at 44.1 kHz; peak 31,656 = **−0.300 dBFS**; 0 samples above 31,656; 0 at full scale; RMS 4,697 |
| Warps travel M → Noria → M → Devias | `travel: world 0 -> 3` (175,117), `world 3 -> 2` (208,47); `travels` 2, `travel_plates_removed` 4, `plates` 1, `stale_plates` 0; HUD 1100/1100 in all 14 samples |
| Arrival HUD and a Hound hit (`MU_HUD_TRACE=1`, 800 frames) | HUD = session = **1100/1100** HP, 200/200 MP, 52/52 SD, 25/25 AG for 13 samples; one hit → 1077/1100 for 16 samples; HUD ≠ session in 0 samples; Hound killed (`kills` 1, `drops` 1) |

- The cast script moved from frame 83 to 90 (`90:move`, `91:rdown`, `93:rup` at 690,238). In this build the world
  scene starts at frame 84, so 008's `83:move` arrived in character select and the right-click did not target. The
  clicks and Space frames are unchanged.

**Windowed:** the installed app itself (`MuNativePreview --seconds 45`, isolated support, log and option dirs, muted,
the field session, `MU_HUD_TRACE=1`, `MU_NATIVE_EXTRA_ARGS="--no-store --auto --hold 6 --input-script '…' --out-dir
'…'"`). Travel 0 → 3 → 2: `travel_plates_removed` 4, `plates` 1, `stale_plates` 0. HUD = session = 1100/1100 in all
35 trace samples. 860 frames in 45 s (about **19.1 fps**) at a **1504×936** drawable. Guard `mu-nonet`, 0 denials.
Window name "Mu The Matrix Native Preview — OFFLINE PREVIEW (no server connection)" (CGWindowList).

**Windleaf 1119/778 and the 2044 rain** (008 proof a, the same flow: character-select row 2, key 2, a right-click):

| Run | HUD (`MU_HUD_TRACE`) | Cast / `{"effects": …}` |
|---|---|---|
| Headless, 1504×936, 220 frames | session = HUD = max = **1119/778/1775/284** in all 6 samples | `skill 2044 at actor 10: ok`; `"skills":1,"sounds":2,"effects_created":121,"max_live_0x70a":1,"max_live_0x70c":11,"max_live_rings":66,"decals":1524,"decal_quads":56348,"unsupported":0` |
| Windowed installed app (`--seconds 25`), still placement, right-click at window point 420,490 | the same in all 15 samples | `skill 2044 at actor 8: ok`; the same line, with `decals` 1,504 and `decal_quads` 55,880 |

Both lines equal APP-REFRESH-008's (screenshot 3).

**Quest accept offline:** `test_native_quest.LorenciaDemo`'s scripted dialogue with `mu-world` from the same main,
the installed Native Data `lang` and `gfx`, the bundled libmugfx and no `MU_QUEST_SCENARIO`:
`"accepted":1,"completed":1,"progress":3,"undecodable":0,"active":[]`, no request 902. The test itself: 1/1 OK.

### Proofs for this refresh

**(a) Shipped Lorencia demo (#338).** `mu-world` from `a7f7b247` with the app's demo files and arguments (installed
`Resources` placement, NPC demo, players; `--combat --progress --items`; installed Native Data objects and `lang`;
GL 640×400, 60 frames; class 1, angle 90; Ironclad's three records as `--hero-item`). mu-client prints no
`item_pre_draw` line, so the counts come from mu-world, as in APP-POLISH-008.

| Tile | Players drawn / refused / hidden | Hero drawn / refused | `sprites_created` |
|---|---|---|---|
| 140,130 (Ironclad's join tile) | **98 / 0** / 2 | **8 / 0** | 127 (`rand_calls` 936) |
| 128,124 | **51 / 0** / 2 | **8 / 0** | 76 |

- `hero_records`: slot 6 type `0x0b2a` (2858) level 9, option 1, **8 passes**; slot 7 `0x16e6` level 7, 4 passes;
  slot 8 `0x22e7` level 0, 2 passes. All of this equals APP-POLISH-008's table. APP-REFRESH-008's shipped crowd had
  no `item_pre_draw` line.
- In the installed app (windowed, bundled session, `--auto`, 16 s), Ironclad's +9 sword glows and Redhand's Xeno
  Blade and Wings of Eternal draw their effects (screenshot 1).

**(b) Raklion (#337): partly shown.** A headless session join in world 57 works (`join 1 57 224,211 90`, rc 0,
scene 6). The 0x14 statue nearest that tile is object 1259 at (19614, 21513), tile 196,215, the one RENDER-WORLDS-RAKLION's
tour saw.
- `mu-world` at `a7f7b247`, world 57, 224,211, GL 1280×800, 60 frames: **`object_particles` 12**, 5 particles drawn.
  The other particle types (0x13, 0x15) are all 30 or more tiles away. So these are the statue's WATERFALL
  particles (inference from the positions).
- Installed app against the rollback app (`f2370871`), frame 199 at 224,211: 3,732 of 1,024,000 pixels change.
  3,076 of them are in the statue column region (x 400..800, y 0..200), where a mesh behind the unicorn statue now
  draws darker (inference: #337's per-vertex and object light for types 6..12). The rest is Ironclad's new sword.
- **The spray itself is not distinguishable in the client's default camera** at 224,211. RENDER-WORLDS-RAKLION's
  tour saw it far up the screen (x 915..1137, y 0..167). Tiles nearer the statue (196,210, 203,216, 200,219) did not
  bring it into a clear view, so no PNG is kept for (b).

**(c) Karutan (#340).** Session `join 1 80 205,17 90` next to the 0x81 crystal (object 1792 at (20679, 1818)),
headless 1280×800, frame 199. Installed app against the rollback app: 1,582 pixels change, **1,533 of them in the
crystal** (x 800..880, y 100..200). The crystal goes from 008's unlit dark body to #340's grey pulse with
`Object144\sdsaferzone14B01_R.jpg` and its additive mesh (screenshot 4).

**(d) Cloak sparks (#339), test fixture.** `test_native_world_predraw.PLAYERS`: Seraph wears wing 12:158 =
`0x2384`; the three drops include `0x2384`.
- `mu-world` at `a7f7b247`, GL 640×400, 60 frames, at 128,124: players **94 drawn / 0 refused**, ground **19 / 0**
  APP-REFRESH-008 reported 138 / **2** and 36 / 0 for its run of this scene; its two refusals were `0x2384`'s
  OBJECT-owned particles. The hero with `--hero-item wing=Item/SparkleCape.bmd`: **21 / 0**.
- Installed mu-client with these players (`--players`, hero joining at 128,127): blue `0x810a`/`0x81cf` sparks around
  Seraph's cloak that the rollback app does not draw (screenshot 5, before | after | 4× difference).

**(e) Armour owner programs (#342), test fixture.** `test_render_effects21.ARMOUR` (armour types `0x1bc3`, `0x1bc4`,
`0x1bde`, `0x1c41`, `0x1c78` on five players):
- `mu-world` at `a7f7b247`, GL 640×400, 60 frames, at 128,124: `item_owner_fx` players **44 owner effects, 0
  refused**. Before #342 no owner program ran in the world.
- Installed mu-client with these players: the owner sprites and particles on ArmA and ArmD that the rollback app does
  not draw (screenshot 6).

**(f) INVENTORY-FX (#343).** The installed app (windowed, bundled session, `--auto`, key I at frame 150): the
inventory window opens (`inventory_open` 1). Its equipment slots show Ironclad's Cookery Short Sword, Small Shield and
Wings of Heaven (screenshot 2). The client reports `"inventory_equipment": [{"slot": 0, "code": 68, "level": 9,
"excellent": 1}, {"slot": 1, "code": 3072, "level": 7, "excellent": 0}, {"slot": 7, "code": 6145, "level": 0,
"excellent": 0}]`.
- RENDER-ITEMS-002U and RENDER-ITEMS-CLOAK were not merged: no proof.
- #341 (RENDER-ITEMS-002T): no shipped or fixture scene here wears the four new bodies or a hidden wing. Its native
  tests (`test_native_renderchar`, `test_native_item_textures`, `test_native_world_predraw`) passed in both private
  runs.

**Screenshots** (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-009/`, each 760 px
wide or less and quantized (0.86 MB in all). Demo names only (Ironclad, Redhand, Windleaf, Hero, Aeris, the test names
Seraph and ArmA..ArmE, demo monsters).

| File | Shows |
|---|---|
| `1-window-lorencia-demo-ironclad-sword9-redhand.png` | window-only capture of the installed app, shipped demo at 140,130: Ironclad's +9 sword glow, Redhand's blade and wings |
| `2-window-inventory-ironclad-equipment.png` | window-only capture: the inventory with Ironclad's sword, shield and wings in their slots |
| `3-windleaf-orbs-2044-rain.png` | windowed installed app, client framebuffer (`shot:`) at frame 125: orbs 1119/1119 and 778/778, the 2044 rain |
| `4-karutan-0x81-crystal-before-after-diff.png` | world 80 at 205,17, frame 199: 008 app, installed app, 4× difference |
| `5-cloak-0x2384-sparks-before-after-diff.png` | the predraw fixture at 128,127: Seraph, 008 app, installed app, 4× difference (2× nearest) |
| `6-armour-owner-fx-before-after-diff.png` | the armour fixture at 128,127: ArmA and ArmD, 008 app, installed app, 4× difference |

## Checks (TEST BUDGET: no lane gate; docs-only PR, rule 6c)

Heavy steps under `nice -n 10`, `make -j4`, `--jobs 2`. Load (1 min) was 10–31 during the first private run (other
lanes' validators), 5–10 through the build and proofs. Memory 58–70% free. Disk 61 GB free.

| Step | Result | Wall time |
|---|---|---|
| Rollback zip + settings copy | 11.8 MB, 66 entries | 0.8 s |
| Build at `138b756e` (for the private run) | ok | 34 s |
| Private native/tests, full, at `138b756e` | 969 tests, 941 passed, 27 skipped, 1 failed (test order, above) | 1,251 s |
| Reruns: 13 modules in their own processes, `MU_GFX_LIB` + `MU_LANG_DIR` | 136 OK, 20 skipped | 352 s |
| Native Data input diff `f2370871..a7f7b247` | empty (`native/gfx`: client-only `mu_gfx_layer.*`) | < 1 s |
| Build at `a7f7b247`: root `make -j4`, `make -C native -j4 world client`, `make -C native/app -j4 MUGFX_LIB=…` | ok; signed, `--check-bundle` ok | 11 s + 9 s + 2 s |
| Install (`ditto`) + strict signature + `--check-bundle` + `mu-native-data check` | ok | < 1 s |
| Private native/tests `--affected-since 138b756e` at `a7f7b247` (147 modules selected) | 983 tests, 962 passed, 20 skipped, 1 failed (concurrency flake; alone OK) | 1,154 s + 10 s |
| Installed smoke, without and with `--audio` | ok, 0 network | 13 s + 15 s |
| Headless journey with `--wav` / Hound+HUD (800 frames) / travel | see above | 14.3 s / 19.3 s / 15.8 s |
| Windowed travel (`--seconds 45`) | see above | 47 s |
| Windleaf headless / windowed | see above | 12.1 s / 27 s |
| (a) `mu-world` × 2 / windowed demo (`--seconds 24`) | see above | 4 s + 3 s / 27 s |
| (b) Raklion: installed + rollback app × 4 tiles, `mu-world` | see above | 7–9 s each |
| (c) Karutan: installed + rollback app | see above | 7.6 s + 9.3 s |
| (d)/(e) `mu-world` × 3; installed + rollback client × 2 | see above | 3–4 s each; 10–13 s each |
| (f) windowed inventory (`--seconds 24`) | see above | 27 s |
| Quest, `test_native_quest.LorenciaDemo` + a direct `mu-world` run | accepted 1; 1/1 OK | 4 s + 5 s |
| `scripts/audit_repository.py` (one new file) | 2,085 staged files, 0 rejected | 16 s |
| Rule 6c doc modules: `tests.test_world_captures_2`, `tests.test_repository_policy` | 13/13 OK | 0.6 s |
| Rule 6c doc modules: `native.tests.test_native_item_textures`, `native.tests.test_native_data_manifest` (from the repo root, private-env.sh) | 23/23 OK | 56 s |

- Steward validators: none (docs only, rule 6c). No code or tool changed.

## Follow-ups

1. **Raklion's spray in view.** The client's default camera at 224,211 does not frame the 0x14 statue at 196,215
   clearly. A tile and angle that do (or a zoomed-out `--wheel`) would give (b) a picture.
2. **private-env.sh lacks `MU_GFX_LIB`** (and `MU_LANG_DIR`). The canonical env skips 14 private tests that pass
   when they are set. Suggest adding `MU_GFX_LIB=$HOME/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`
   and `MU_LANG_DIR=$MU_NATIVE_DATA_DIR/lang` (orchestrator's file, not changed here).
3. **`test_audio_items` needs `reconstructed/items/libclient_items.dylib`**, which the root `make` does not build. In a
   fresh worktree it fails until another module builds it. A `make -C reconstructed/items` in its setUp (or the root
   `all`) would fix it.
4. **`test_inventory_fx.InventoryScene` flaked once under `jobs=2`** (non-zero exit, empty stderr; alone OK).
5. **Env leak across modules in one process:** some module removes `MU_LANG_DIR` from `os.environ`; three modules
   then error with `KeyError` when run in the same unittest process. The runner's one-process-per-module hides it.
6. **The cast journey's frames:** the world now starts at frame 84; scripts should move at 90 or later (above).
7. **Retina windowed proof** (008 follow-up 1): still a 1x display here.
8. **Not in this build:** RENDER-ITEMS-002U (no PR) and RENDER-ITEMS-CLOAK (#344, merged 25 minutes after the build).
9. Still open from APP-REFRESH-006..008: the libmugfx 22 Oct build (not stale), Test Area 121 has no objects in Native
   Data, Muun/Uruk not in the demo, Arca War worlds not installed, worlds 145/95/110 draw no objects, the old export
   set and the APP-REFRESH-001/legacy Native Data folders (the owner's call).

## Cleanup

- Kept: the rollback folder `rollback/app-refresh-009/` and the six screenshots.
- Deleted after the ready line: `scratch/app-refresh-009` (helpers, sessions, fixture files, runs, frames, WAV, the
  unzipped rollback app) and this worktree's `native/build` and `verify-runs`. The worktree stays until the steward
  merges.
- Deleted earlier: `rollback/app-refresh-005/` (11.8 MB).
- Helpers, rebuildable from this file and APP-REFRESH-005..008:
  - `hl.py`: a headless run of an app bundle's mu-client with the app's plan (`--app`, `--session`, `--size`,
    `--frames`, `--every`, `--audio`, `--hud`, `--auto`, `--script-file`, `--option-ini`, `--placement`,
    `--players`, extra args after `--`), with `MU_NATIVE_SETTINGS_DIR` and `MU_NONET_REPORT` in the run folder.
  - `runw.sh`: the GUI app with `--seconds`, isolated dirs, a muted option.ini and `MU_HUD_TRACE`; `SESSION` and
    `EXTRA` override the session and the flow arguments; a window-only shot at a given second from a compiled
    `~/Documents/MTM/mu-mac-tools/winshot.swift` (keep only the titled window).
  - Sessions: the bundled `demo-session.txt` with `join 1 0 179,131 90` (field), `join 1 57 224,211 90`,
    `join 1 80 205,17 90`, `join 1 0 128,127 90` (fixtures). Comparison runs with the rollback app need its own
    bundled `demo-characters.txt` (it refuses #338's records).
  - `still-placement.txt`: the bundled placement without `wander`.
  - `hj-still.txt`: `90:move`, `91:rdown`, `93:rup` at 690,238; left clicks there at 131/191/251; Space (`key:32`)
    at 300/340/380/420.
  - `hound.txt`: clicks at 1200,650 at 80/140/200/260, attack clicks at 816,600 from 352 every 60 frames to 652,
    `790:move:640,400`.
  - `travel-hl.txt`: M (`key:77`) at 100, click 122,257 at 131, M at 300, click 122,324 at 331.
    `travel-w.txt`: the same at 300/331/600/631, `move` at 700.
  - `wl-hl.txt`: `test_app_polish5.FLOW` (right-click 845,100); `wl-w.txt`: the same at 420,490 with `shot` at 125/140.
  - `inv-w.txt`: `150:key:73`.
  - `predraw-players.txt` / `armour-players.txt`: `test_native_world_predraw.PLAYERS` / `test_render_effects21.ARMOUR`.
