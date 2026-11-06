# APP-REFRESH-005

Implementation handoff, 2026-11-06. Worktree `worktrees/app-refresh-005`, branch `claude/app-refresh-005`. Claude
Opus 5.5 lane. Offline only: no original client, launcher, live read, account, network or protection work. No source
change was needed. The owner's Wine play app, its prefix settings and the staged Wine app were not touched.

## What the installed app now has

The Native Preview was reinstalled from main **`7d7d694b`** (#295 RENDER-ITEMS-HIDDENMESH, steward batch 41, on top
of `7403244e` = #302). It has everything since APP-REFRESH-004 (`32b7f34d`):

- #290 RENDER-ITEMS-002O: renderchar validator and six bodies;
- #291 RENDER-WORLDS-AFTER6: tick handlers;
- #292, #296, #300 RENDER-EFFECTS-011/012/013: bow and combat effects (named bones, joints, Shiny01/3);
- #293 APP-POLISH-001: the demo Hound moved off the field arrival, quoted `MU_NATIVE_EXTRA_ARGS`;
- #294 APP-POLISH-002: the HUD vitals follow the session;
- #298 APP-POLISH-003: arrival at full vitals, green HP orb for toxic states;
- #295 RENDER-ITEMS-HIDDENMESH: item white types 36 → 13, 182 types textured or completed;
- #301, #302 RENDER-WORLDS-S/S2: Aquila's Temple, Debenter, Boss Battle, Nars and the Arca War class;
- #297, #299 TEST-SPEED-001/002: tooling only.

**Not included:** RENDER-EFFECTS-014 and RENDER-WORLDS-S3. Neither had a PR when this build was made (11:02 CST).

**Order of events:**
1. Prep and the rollback were done while #295 waited for batch 41. The proof scripts were tried out on a worktree
   build of `7403244e`; that build also gave the "before" item gallery.
2. #295 merged at about 11:01. The worktree was fast-forwarded to `7d7d694b`, rebuilt and installed (11:02).
3. Every proof below was taken on `7d7d694b`. The headless and windowed client proofs use the installed bundle.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 7d7d694b, version 0.1 (1), real Ruffle.
  - Built with `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`,
    which bundles `Contents/Frameworks/libmugfx.dylib` (17.9 MB).
  - Installed with `ditto` over the removed old copy, after checking that no Preview was running.
  - The strict deep signature check passes, and so does `--check-bundle` (mu-client, network guard and GFx library
    (Ruffle) all bundled). After the test runs below, the installed copy still has `MUNativeCommit` 7d7d694b and the
    17.9 MB `libmugfx.dylib`.
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-005/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-004-32b7f34d.app.zip` (11.7 MB, 64 files), the app as it was
    installed before this lane;
  - `settings.json.before`, which selects `APP-REFRESH-004/Native Data` (unchanged by this lane).
  - To roll back: unzip the app into `~/Applications`, and copy `settings.json.before` over
    `~/Library/Application Support/MuTheMatrixNative/settings.json`.
  - The `app-refresh-002/`, `-003/` and `-004/` rollbacks are kept.
- **Native Data: kept** (`~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-004/Native Data`, 74 MB).
  - No export input changed between `32b7f34d` and `7d7d694b`. Unchanged: `scripts/build_native_data_export.py`
    (and so its snapshot lists and the mapanim step), every exporter it runs (`live_lang_to_plain.py`,
    `live_effect_table_to_plain.py`, `live_objects_to_plain.py`, `extract_audio_tables.py`), `native_data_manifest.py`
    and `pins.py`.
  - The app diff (#293) changes only how `MU_NATIVE_EXTRA_ARGS` is split, not setup or the data layout.
  - #295 changes renderchar and the item-texture adapter (`native/core/mu_item_textures.c`, `mu_renderchar.c`,
    `reconstructed/renderchar/*`) and the item body generator. All of these are compiled into the client. Item
    textures are still read from the installed game's `Data/`, so no table is exported.
  - #301 and #302 add object classes for worlds that have no object plaintext in the export set. They need no data
    to load (see proof e).
  - `mu-native-data check` on the folder passes. The manifest still lists `lang/mapanim.tsv` (`d7a2cc72…a57de814`,
    5,477 bytes). With the owner's real settings, `--print-plan` gives `MU_LANG_DIR=<…/APP-REFRESH-004/Native Data>/lang`
    and `--world-objects <…>/objects`.
  - `settings.json` was not changed.
- **Installed smoke**, `--smoke --backend gl` with isolated logs and settings and `PATH=/nonexistent`. It ran with and
  without `--audio`: ok, world reached, Apple M5, guard `mu-nonet`, 0 connects, 0 inet, 0 lookups and 0 other calls
  denied.

## Journey proofs (installed app, `7d7d694b`)

**Headless:** the installed bundle's mu-client with the app's own launch plan (`--print-plan` with an isolated support
dir that holds a copy of the owner's settings), `--auto --hold 6`, `--no-store`, isolated option settings, the
APP-REFRESH-004 Native Data. The session is the field session (the demo session with slot 1 at Lorencia 179,131).
`MU_HUD_TRACE=1` prints session and HUD vitals once per world second.

| Proof | Result |
|---|---|
| Selected-skill right-click cast (Budge Dragon) | `skill_casts` 1, 0 refused |
| Kill, drop, Space pickup | `kills` 1, `drops` 1, `space_picks` 1, 1 pickup request, 1 pickup completed |
| Warps travel M → Noria → M → Devias (1280×800 rows: x 122; Noria y 257; Devias y 324) | `travel: world 0 -> 3`, then `world 3 -> 2`; `travels` 2 |
| No previous-world plates after travel | `travel_plates_removed` 4, `plates` 1, `movie_plates` 1 (the hero), `stale_plates` 0 |
| Audio at full volume (option.ini `IsMusicPlay=1`, `Volum=9`; `--wav` over the cast/kill/pickup journey) | 1,286,308 stereo frames at 44.1 kHz; peak 31,656 = **−0.300 dBFS**; 0 samples above the ceiling; 0 at full scale; RMS 4,513 |
| **(a) Arrival HUD and a Hound hit** (four walk clicks east, then attack clicks on the Hound from frame 352) | HUD = session = **1100/1100** HP, 200/200 MP, 52/52 SD, 25/25 AG for 13 samples; one Hound hit → **1077/1100**, then 16 samples unchanged at 1077 (no self-oscillation); the Hound dies (`kills` 1, `drops` 1). Screenshot 3 shows 1077/1100 on the orb. |
| HUD through travel | 1100/1100 in all 18 samples across Lorencia, Noria and Devias |
| **(b) Demo Hound away from the arrival** | The installed `Resources/world/lorencia-demo-placement.txt` has `actor 1 205 131 6 wander 4 label hound`, 26 tiles east of the arrival at 179,131. In run (a) HP stays 1100 for the first 13 s, while the hero walks east from 179,131 to about 203,134; the first hit comes only after the attack clicks on the Hound. The arrival run behind screenshot 1 shows no Hound near the hero. |
| **(e) New world classes** (session `join 1 <world> <tile>`, 200 frames) | Aquila's Temple 145 (122,65; gate 718), Debenter 95 (19,104) and Nars 110 (128,128): rc 0, scene 6, 143 world frames each, no crash. Arca War 92: the owner's client has no `Data/World93` (nor World97/102/112 for 96/101/111), so the world does not load and the client goes back to character select (12 times in 200 frames, since `--auto` keeps pressing Enter); rc 0, no crash. |

**Windowed:** the installed app itself (`MuNativePreview --seconds 75`, isolated support, log and option dirs,
muted, `MU_NATIVE_SESSION` = the field session, `MU_NATIVE_EXTRA_ARGS="--no-store --auto --hold 6 --input-script '…'"`),
at its own window size **1504×936** (drawable 1504×936 on this display, so the 1x row points apply). Travel 0 → 3 → 2
works the same way: `travel_plates_removed` 4, `plates` 1, `movie_plates` 1, `stale_plates` 0. The HUD shows 1100/1100
in all 67 trace samples. The launcher log records `mu-nonet` with 0 denials. About 25 fps, 1,621 frames in 75 s.

**(c) Formerly white item types.** `mu-render ui inventory` from the same main, the installed game, `MU_LANG_DIR` = the
installed Native Data `lang`, time 123456, items 55, 2612, 6737, 20, 1032 and 6571 (types 0x0b1d, 0x151a, 0x2537,
0x0afa, 0x0eee and 0x2491):

| | Main `7403244e` (before #295) | Installed main `7d7d694b` |
|---|---|---|
| Models drawn / missing | 6 / 0 | 6 / 0 |
| Triangles | 1,868 | 2,376 |
| Framebuffer SHA-256 | `f75474c8…4533f1cc` | `c79f2706…9d06959f` |
| Grid crop (230×230) | | 5,454 pixels changed |

In screenshot 4 (before | after), the white disc of 0x2537, the white blade of 0x0b1d and the white staff section
of 0x151a are textured, and 0x2491's blue feather mesh appears around the gold frame.

**(d) Bow combat scenes.** `mu-world` from the same main, installed data, Lorencia 182,128, class 2, a spider three
tiles east, `--combat-weapon bow --combat-bow <bow> --combat-script "2:skill:24:spider;3:stop"` (Triple Shot), 50 frames.

| Bow | Arrows | Joints | Particles | Unsupported | Hits |
|---|---|---|---|---|---|
| 0x12fc (#300: joint 0x7f79/f, Shiny01/3) | 4 | 4 | 24 | **0** (4 before #300) | 4 |
| 0x130a (#300: joint 0x80e3/5) | 4 | 4 | 0 | **0** (4 before #300) | 4 |
| 0x131e (#300) | 4 | 4 | 32 | **0** (4 before #300) | 4 |
| 0x12f9 (#283) | 4 | 15 (15 bow sparks) | 69 | 0 | 4 |
| 0x1329 (#283, #287) | 4 | 0 | 160 | 0 | 4 |
| 0x12f7 (still open) | 3 | 0 | 0 | 12 | 0 |
| 0x12fb (still open) | 3 | 0 | 0 | 3 | 3 |

The "before #300" counts are RENDER-EFFECTS-013's. Screenshot 5 shows 0x12fc's four green joint trails with the
Shiny01 sparkles at frame 15.

**Screenshots** (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-005/`, all
downscaled to at most 760 px wide and quantized (1.0 MB in all).

| File | Shows |
|---|---|
| `1-lorencia-arrival-1100.png` | window-only capture of the installed app: field arrival, HUD 1100/1100, no Hound near the hero |
| `2-devias-after-travel.png` | window-only capture of the installed app after Warps travel: only the hero's plate |
| `3-hound-hit-hud-1077.png` | installed client, headless frame: Hound hit, HUD 1077/1100 |
| `4-items-before-after-295.png` | inventory grid crop, `7403244e` on the left, `7d7d694b` on the right |
| `5-bow-0x12fc-joints.png` | headless `mu-world` frame: bow 0x12fc joint trails |

## Checks (TEST BUDGET: no lane gate)

| Step | Result | Wall time |
|---|---|---|
| Rollback zip + settings copy | 11.7 MB, 64 files | < 1 s |
| Prep build at `7403244e`: `nice -n 10 make -C native -j4`, then `world` | ok | 30 s |
| Prep app build with real Ruffle | ok | 10 s |
| Build at `7d7d694b` (incremental): native, `world`, `make -C native/app -j4 MUGFX_LIB=…` | ok; app signed, `--check-bundle` ok | 11 s + 5 s + 10 s |
| Install (`ditto`) + strict signature + `--check-bundle` | ok | < 1 s |
| `mu-native-data check` on the kept Native Data | ok | < 1 s |
| Installed smoke, without and with `--audio` | ok, 0 network | 15 s + 15 s |
| Headless Hound / HUD run (800 frames) | see (a) | 20 s |
| Headless journey with `--wav` | see above | 13 s |
| Headless travel | see above | 13 s |
| Headless arrivals 145, 95, 110, 92 | see (e) | 6 s + 5 s + 5 s + 9 s |
| Windowed travel with screenshots | see above | 77 s |
| Inventory gallery, before and after | see (c) | 1 s + 1 s |
| Bow scenes, 7 bows | see (d) | 15 s |
| `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<installed> python -m unittest native.tests.test_native_app` (incl. the private smoke over the installed game) | 18/18 | 66 s |
| `python -m unittest native.tests.test_native_data_manifest` (from the repo root, same env) | 15/15 | 7 s |
| `scripts/audit_repository.py` | 1,915 staged files, 0 rejected | 21 s |
| Brief-6c doc modules: `tests.test_world_captures_2` + `tests.test_repository_policy`; private `test_native_item_textures` (from `native/tests`) | 11/11; 7/7 | 0.4 s; 55 s |

- Steward validators: none (docs only; brief 6c: the audit and the doc-reading modules).
- `test_native_app` runs `make -C native preview-app` without `MUGFX_LIB`. That rebuilds only the worktree's
  `native/build/app` with the GFx stand-ins. It ran after the install, and the installed copy keeps the real Ruffle.
- Load stayed at or below 14 for the heavy steps, with one exception: the first windowed dry run started at load
  15.5; the next steps waited until it was 12.

## Follow-ups

1. **Arca War class worlds are not installed** in the owner's client: `Data/World93`, `World97`, `World102` and
   `World112` are missing, so 92, 96, 101 and 111 cannot load (RENDER-WORLDS-S2 found the same for 111). A join
   to them falls back to character select without a crash. Their object code (#302) is exercised only by tests.
2. **New worlds draw no objects.** 145, 95 and 110 arrive with terrain and hero but zero objects. The installed
   `EncTerrain*.obj` files do not decode with the client's loader, and the export set has no live-read plaintext for
   these worlds. A later live read (DATA-ACQ) would add them to `scratch/native-data/export`; that would need a new
   Native Data folder in the next refresh.
3. **Wing 0x2491 in the inventory** (screenshot 4): with its feather mesh, the icon now reaches past the bottom of
   its grid cells, over the empty slots below. Not compared with the original client (inference: the original
   may scale it the same way).
4. **Bows 0x12f7 and 0x12fb** stay unsupported (12 and 3, as RENDER-EFFECTS-013 recorded). With 0x12f7 none of its
   3 arrows hit the spider in this scene (0 projectile hits); 0x12fb's 3 do.
5. RENDER-EFFECTS-014 and RENDER-WORLDS-S3 are not installed. The next refresh can keep this Native Data unless they
   change an export input.
6. `python -m unittest native.tests.test_native_item_textures` from the repo root fails to import its sibling
   `native_fixtures` module (the same pattern APP-POLISH-001 fixed for `test_native_data_manifest`). It passes from
   `native/tests` and under `scripts/run_test_suites.py`.
7. The window title still shows the diagnostic suffix "scene 6 world 25.0 fps" (`native/client/main.c` title
   format). A player sees it in the title bar.
8. Tooling note: `/usr/bin/nice` drops `DYLD_INSERT_LIBRARIES`, so the network guard would not load. The headless
   helper therefore runs Python under `nice` and starts the client directly (it inherits the priority).
9. From APP-REFRESH-004, still open: a later cleanup may remove the APP-REFRESH-001 and legacy `Native Data`
   folders (the owner's call). APP-REFRESH-002's folder is the data of the `app-refresh-004` rollback, and
   APP-REFRESH-004's folder is the current data.

## Cleanup

- Kept: the rollback folder, the five screenshots, and the canonical export set (`scratch/native-data/export`, owned
  by NATIVE-DATA-MANIFEST-001).
- Deleted: `scratch/app-refresh-005` (helpers, sessions, runs, frames, gallery and bow outputs), this worktree's
  `native/build`, the worktree and the local branch.
  - The helpers are small and easy to rebuild from this file and APP-REFRESH-004:
    - `hl.py`: a headless run of an app bundle's mu-client with the app's plan (`FRAMES`, `EVERY`, `HUD_TRACE`,
      `--session`, `--audio`, `-- <extra args>`), option settings in `<out>/settings`;
    - `runw.sh`: the GUI app with `--seconds`, isolated dirs, a muted option.ini, and window-only shots via
      `~/Documents/MTM/mu-mac-tools/winshot.swift` (owner "mu the matrix native preview");
    - the field session: the bundled `demo-session.txt` with `join 1 0 179,131 90`;
    - `hound.txt`: four clicks at (1200,650) at frames 80/140/200/260 (the hero walks to about 203,134), then attack
      clicks on the Hound at (816,600) from frame 352;
    - `hj.txt`: right-click on the Budge Dragon at (820,287) at frame 83, left clicks there at 131 and 191, Space at
      300/340/380/420;
    - `travel-hl.txt` (headless): M at 100, click 122,257 at 131, M at 300, click 122,324 at 331; the windowed
      `travel.txt` uses frames 300/331/600/631;
    - a spider-only placement (`actor 3 185 128 0 label spider`) for the bow scenes.
