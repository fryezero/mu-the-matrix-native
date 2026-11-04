# APP-REFRESH-004

Implementation handoff, 2026-11-04. Worktree `worktrees/app-refresh-004`, branch `claude/app-refresh-004`, from
origin/main `26b9ef07` (#288 NATIVE-DATA-MANIFEST-001). Claude Opus 5.5 lane. Offline only: no original client,
launcher, live read, account, network or protection work. No source change was needed. The owner's Wine play app and
its prefix settings were not touched.

## What the installed app now has

The Native Preview was reinstalled from main `26b9ef07`. That main has everything since APP-REFRESH-003 (`82849bc`)
except #287:

- #280 PLAY-FIX-001: no old-world name plates after travel, and the −0.3 dBFS output limiter;
- #281 RENDER-WORLDS-AFTER4: draw-first and render-time light;
- #282 RENDER-ITEMS-002N: item bodies 1,213;
- #283 RENDER-EFFECTS-009: named bones, bow 0x12f9's sparks, the white 0x5b0/0x5b1 arrow quads fixed;
- #285 RENDER-WORLDS-AFTER5: object velocities from the mapanim table;
- #286 RENDER-ITEMS-TEX-003: item textures, white types 125 → 36;
- #288 NATIVE-DATA-MANIFEST-001: the canonical manifest-bearing export set with `mapanim.tsv`.

**Not included:**
- **#287 RENDER-EFFECTS-010** (pet particle kinds, the 0x615/0x617 glows, the bow kinds). The steward dropped it
  from batch 27: `test_native_worlds_l` and `test_native_worlds_m` fail on its head `724ad10a`
  (`steward-log.md`, batch 27). It needs a fix and then a later refresh.
- **RENDER-ITEMS-002O** had not merged when this build was made.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 26b9ef07, version 0.1 (1), real Ruffle.
  - Built with `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`.
  - Installed with `ditto` over the removed old copy.
  - The strict deep signature check passes, and so does `--check-bundle` (mu-client, network guard and GFx library
    (Ruffle) all bundled).
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-004/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-003-82849bc.app.zip` (11.7 MB), the app as it was installed;
  - `settings.json.before`, which selects `APP-REFRESH-002/Native Data`.
  - To roll back: unzip the app into `~/Applications`, and copy `settings.json.before` over
    `~/Library/Application Support/MuTheMatrixNative/settings.json`.
  - The `app-refresh-002/` and `app-refresh-003/` rollbacks are kept.
- **Native Data:** `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-004/Native Data` (74 MB).
  - It follows the 6 steps of NATIVE-DATA-MANIFEST-001 "APP-REFRESH-004: installing the new set".
  - The source was the canonical export set `scratch/native-data/export`. `mu-native-data check` passes for `lang`,
    `objects/live/plain` and `audio/tables`.
  - Setup ran into the new, empty support dir (`MU_NATIVE_SUPPORT_DIR=…/APP-REFRESH-004`, 27 s). It converted gfx
    (179 files) and copied lang (30), objects (94) and sound (1), then wrote the manifest.
  - The root manifest check passes. It lists `lang/mapanim.tsv` (SHA-256 `d7a2cc72…a57de814`, 5,477 bytes).
  - With the owner's real settings, `--print-plan` gives `MU_LANG_DIR=<…/APP-REFRESH-004/Native Data>/lang`.
- `settings.json` now holds `nativeData` = the APP-REFRESH-004 folder. The APP-REFRESH-002 folder stays in place as
  the data rollback. So do the APP-REFRESH-001 folder and the legacy `Native Data` folder, which were not touched.
- **Installed smoke**, `--smoke --backend gl` with isolated logs and settings, `--no-store` and `PATH=/nonexistent`.
  It ran with and without `--audio` (18 s and 17 s): ok, world reached, Apple M5, 0 connects, 0 inet and 0 lookups
  denied.

## Journey proofs (installed app)

**Headless:** the bundled mu-client with the app's own launch plan (`--print-plan`, field session: slot 1 at
Lorencia 179,131), `--auto --hold 6`, `--no-store`, isolated settings, the APP-REFRESH-004 Native Data. Results:

| Proof | Result |
|---|---|
| Selected-skill right-click cast (Budge Dragon) | `skill_casts` 1 (skill 19), 0 refused, 2 casts |
| Kill, drop, Space pickup | `kills` 1, `drops` 1, `space_picks` 1, 1 pickup request, 1 pickup completed |
| Warps travel M → Noria → M → Devias | `travel: world 0 -> 3`, then `world 3 -> 2`; `travels` 2 |
| **(a) No previous-world plates after travel** | `travel_plates_removed` 4, `plates` 1, `movie_plates` 1 (the hero), `stale_plates` 0 |
| **(b) Audio at full volume** (option.ini `IsMusicPlay=1`, `Volum=9`; `--wav` over the cast/kill/pickup journey) | 1,251,028 stereo frames at 44.1 kHz; peak 31,656 = **−0.300 dBFS**; 0 samples above the ceiling; 0 at full scale; RMS 4,526 |

The audio numbers compare with APP-REFRESH-003's installed build: peak 32,767, 135 samples at full scale.

**Windowed:** the installed app at its own window size **1504×936** (this Mac's display is 1920×1080; the window
size was not forced), muted settings. Travel 0 → 3 → 2 works the same way. The input report gives
`travel_plates_removed` 4, `movie_plates` 1, `stale_plates` 0. In Devias only the hero's "Ironclad" plate is drawn
(screenshot 3; APP-REFRESH-003's screenshot 4 still showed "Budge Dragon" and "Hound").

**(c) Swamp of Destruction (144): velocities from the mapanim table.**
- Method: `scripts/fidelity_tour.py run`, with `--only` equivalent to the single 144 capture of DATA-ACQ-002's tour
  (`scratch/data-acq-002/live/144-swamp-destruction-*`).
- It used the worktree's `mu-world` (same main `26b9ef07`) and the installed Native Data's `objects`. It ran twice:
  with `MU_LANG_DIR=<Native Data>/lang` (the installed `mapanim.tsv`), and without it.
- Results:

  | | velocity differences against live, map (near hero) | image mean diff |
  |---|---|---|
  | without the table | 1,563 objects (40), 23 types; e.g. type 24 live 0.3 / native 0.16, type 32 live 0.07 / native 0.16 | 12.394 |
  | with the installed table | **0 (0)**; no OBJECT field differs | 11.769 |

- All 8,988 objects are matched in both runs (0 missing, 0 extra). The runs took 3 s each.
- AFTER5 recorded 12.394 → 12.391. The larger image gain here comes from the same table on the later main (#286).

**(d) Bow combat scene.**
- Setup: `mu-world` from the same main, installed data, Lorencia 182,128, class 2, a spider three tiles east, and
  `--combat-script 2:skill:24:spider;3:stop` (Triple Shot), 50 frames.
- Bow 0x12f9 (#283): 1 skill, 4 arrows (type 1140), 4 projectile hits, **15 bow sparks** (`joints_created` 15),
  69 particles, **0 unsupported** (screenshot 4: the green-white sparks and the pink arrow trails).
- Bow 0x1329 (arrow 0x615, #283's named bones): 4 arrows fire (0 fired before #283). Its 160 unsupported particle
  requests remain, and the arrows still draw as dark cards. Those are #287's glow functors and 0x8081..0x8083 kinds,
  which are not on main.

Screenshots (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-004/`. All are
downscaled; 1–3 are window-only captures of the installed app.
- `1-lorencia-arrive-1504x936.png`
- `2-warps-window.png`
- `3-devias-after-travel-no-stale-plates.png`
- `4-bow-0x12f9-sparks.png`
- `5-swamp-144-live-vs-native.png` (live | native with the table)

## Checks (TEST BUDGET: no lane gate)

| Step | Result | Wall time |
|---|---|---|
| Build `nice -n 10 make -C native -j4`; `world`; `make -C native/app -j4 MUGFX_LIB=…` | ok; app signed, `--check-bundle` ok | 20 s + 9 s + 14 s |
| Rollback zip + settings copy | 11.7 MB, 64 files | < 1 s |
| Install (`ditto`) + strict signature + `--check-bundle` | ok | < 1 s |
| `mu-native-data check` × 3 components; setup into the new folder; root check | ok; 179/30/94/1 files | 27 s (setup) |
| Installed smoke, with and without `--audio` | ok, 0 network | 18 s + 17 s |
| Headless journey (cast, kill, pickup, `--wav`) | see above | 14 s |
| Headless travel | see above | 12 s |
| Swamp 144 tours (with and without the table) | 0 vs 1,563 velocity differences | 3 s + 3 s |
| Bow scenes 0x12f9, 0x1329 | see above | 4 s + 4 s |
| Windowed runs (arrival, Warps, travel) | ok | 17 s + 15 s + 47 s |
| `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<installed> python -m unittest native.tests.test_native_app` (incl. the private smoke over the installed game) | 17/17 | 53 s |
| `test_native_data_manifest` (run from `native/tests`) | 15/15 | 6 s |
| `scripts/audit_repository.py` | 1,838 staged files, 0 rejected | 24 s |

- Steward validators: none (docs only).
- `test_native_app` runs `make -C native preview-app` without `MUGFX_LIB`. That rebuilds only the worktree's
  `native/build/app` with the GFx stand-ins. It ran after the install, so the installed app keeps the real Ruffle
  (checked: `Contents/Frameworks/libmugfx.dylib` present, `MUNativeCommit` 26b9ef07).

## Follow-ups

1. **#287 is not installed** (dropped from batch 27). After its fix merges, an APP-REFRESH-005 can reuse this
   folder's Native Data if #287 changes no export input, and only reinstall the app. It brings the 0x615/0x617
   glows (bow 0x1329: 160 unsupported → 0 expected) and the pet particle kinds. RENDER-ITEMS-002O can come in the
   same refresh.
2. **Hero shadow in Noria and Devias** (screenshots of the windowed travel, and screenshot 3): the hero's shadow,
   including the wings, is an opaque, hard-edged black shape on the stone floor. In the Lorencia field the grass
   hides it. Not compared with the live client yet (inference: the client's shadow pass is translucent).
3. **1504×936 window:** the GFx HUD and the Warps window draw at 1:1 instead of scaling with the window. So the
   1280×800 row points (x 122; Noria y 257; Devias y 324) work unchanged at 1504×936. This corrects
   APP-REFRESH-003's note that scripts need `--width 1280 --height 800`. Whether the original scales them at this
   size is not checked.
4. `python -m unittest native.tests.test_native_data_manifest` from the repo root gives 5 `ModuleNotFoundError`s
   (`test_native_lang`, `test_native_shell`). The test imports sibling modules, which works from `native/tests` and
   under `scripts/run_test_suites.py`. A `sys.path` line in the test would make both invocations work.
5. Still open from APP-REFRESH-003: `MU_NATIVE_EXTRA_ARGS` splits on spaces.
6. A later cleanup may remove the APP-REFRESH-001 Native Data folder and the legacy `Native Data` folder. That is the
   owner's call. Keep APP-REFRESH-002 as long as `rollback/app-refresh-004` is kept.

## Cleanup

- Kept: the rollback folder, the five screenshots, and the canonical export set (`scratch/native-data/export`, owned
  by NATIVE-DATA-MANIFEST-001).
- Deleted: `scratch/app-refresh-004` (helpers, runs, tour outputs, frames), `native/build` of this worktree, the
  worktree and the local branch.
  - The helpers are small and easy to rebuild from this file and APP-REFRESH-003's description:
    - `hl.py`: a headless run with an app plan;
    - `runw.sh`: a windowed run at the app's own size, with muted settings;
    - the journey scripts `hj.txt` (cast, kill, Space) and `travel.txt` (M, 122,257, M, 122,324).
