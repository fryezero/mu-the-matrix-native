# APP-REFRESH-004

Implementation handoff, 2026-11-04. Worktree `worktrees/app-refresh-004`, branch `claude/app-refresh-004`. Claude
Opus 5.5 lane. Offline only: no original client, launcher, live read, account, network or protection work. No source
change was needed. The owner's Wine play app and its prefix settings were not touched.

## What the installed app now has

The Native Preview was reinstalled from main **`32b7f34d`** (#287 RENDER-EFFECTS-010, on top of `26b9ef07` = #288).
It has everything since APP-REFRESH-003 (`82849bc`):

- #280 PLAY-FIX-001: no old-world name plates after travel, and the −0.3 dBFS output limiter;
- #281 RENDER-WORLDS-AFTER4: draw-first and render-time light;
- #282 RENDER-ITEMS-002N: item bodies 1,213;
- #283 RENDER-EFFECTS-009: named bones, bow 0x12f9's sparks, the white 0x5b0/0x5b1 arrow quads fixed;
- #285 RENDER-WORLDS-AFTER5: object velocities from the mapanim table;
- #286 RENDER-ITEMS-TEX-003: item textures, white types 125 → 36;
- #287 RENDER-EFFECTS-010: pet particle kinds, the 0x615/0x617 glows and bow kinds. The steward dropped it from batch
  27, and it merged after its fix (`76b9eee7`);
- #288 NATIVE-DATA-MANIFEST-001: the canonical manifest-bearing export set with `mapanim.tsv`.

**Order of events:**
1. The first install was `26b9ef07` (13:48), built while #287 was out of batch 27. Every proof was taken on it.
2. #287 merged at 13:57. The app was rebuilt from a detached `origin/main` checkout, so `MUNativeCommit` names the
   main commit, and reinstalled (13:58).
3. All proofs were rerun on `32b7f34d`; the numbers below are from that build.
4. #287 changes no exporter, app or setup input (its diff is `native/core`, `reconstructed/{particles,combat}`, tests
   and validators), so the Native Data folder was kept.

**Not included:** RENDER-ITEMS-002O (renderchar glColor). It had no PR when this build was made.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 32b7f34d, version 0.1 (1), real Ruffle.
  - Built with `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`,
    which bundles `Contents/Frameworks/libmugfx.dylib` (17.9 MB).
  - Installed with `ditto` over the removed old copy, after checking that no Preview was running.
  - The strict deep signature check passes, and so does `--check-bundle` (mu-client, network guard and GFx library
    (Ruffle) all bundled).
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-004/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-003-82849bc.app.zip` (11.7 MB, 64 files), the app as it was installed
    before this lane;
  - `settings.json.before`, which selects `APP-REFRESH-002/Native Data`.
  - To roll back: unzip the app into `~/Applications`, and copy `settings.json.before` over
    `~/Library/Application Support/MuTheMatrixNative/settings.json`.
  - The `app-refresh-002/` and `app-refresh-003/` rollbacks are kept.
- **Native Data:** `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-004/Native Data` (74 MB).
  - It follows the 6 steps of NATIVE-DATA-MANIFEST-001 "APP-REFRESH-004: installing the new set".
  - The source was the canonical export set `scratch/native-data/export`. `mu-native-data check` passes for `lang`,
    `objects/live/plain` and `audio/tables`.
  - Setup ran into the new, empty support dir (`MU_NATIVE_SUPPORT_DIR=…/APP-REFRESH-004`). It converted gfx
    (179 files) and copied lang (30), objects (94) and sound (1), then wrote the manifest.
  - The root manifest check passes. It lists `lang/mapanim.tsv` (SHA-256 `d7a2cc72…a57de814`, 5,477 bytes).
  - With the owner's real settings, `--print-plan` gives `MU_LANG_DIR=<…/APP-REFRESH-004/Native Data>/lang` and
    `--world-objects <…>/objects`.
- `settings.json` now holds `nativeData` = the APP-REFRESH-004 folder. The APP-REFRESH-002 folder stays in place as
  the data rollback. So do the APP-REFRESH-001 folder and the legacy `Native Data` folder, which were not touched.
- **Installed smoke**, `--smoke --backend gl` with isolated logs and settings, `--no-store` and `PATH=/nonexistent`.
  It ran with and without `--audio`: ok, world reached, Apple M5, guard `mu-nonet`, 0 connects, 0 inet, 0 lookups
  and 0 other calls denied.

## Journey proofs (installed app, `32b7f34d`)

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
(screenshot 2; APP-REFRESH-003's screenshot 4 still showed "Budge Dragon" and "Hound").

**(c) Swamp of Destruction (144): velocities from the mapanim table.**
- Method: `scripts/fidelity_tour.py run` over the single 144 capture of DATA-ACQ-002's tour
  (`scratch/data-acq-002/live/144-swamp-destruction-*`).
- It used the worktree's `mu-world` (same main) and the installed Native Data's `objects`. It ran twice: with
  `MU_LANG_DIR=<Native Data>/lang` (the installed `mapanim.tsv`), and without it.
- Results:

  | | velocity differences against live, map (near hero) | image mean diff |
  |---|---|---|
  | without the table | 1,563 objects (40), 23 types; e.g. type 24 live 0.3 / native 0.16, type 32 live 0.07 / native 0.16 | 12.394 |
  | with the installed table | **0 (0)**; no OBJECT field differs | 11.769 |

- All 8,988 objects are matched in both runs (0 missing, 0 extra).
- The same numbers came out on `26b9ef07`.
- AFTER5 recorded 12.394 → 12.391 for the image. The larger gain here comes from the same table on the later main.

**(d) Bow combat scenes.**
- Setup: `mu-world` from the same main, installed data, Lorencia 182,128, class 2, a spider three tiles east, and
  `--combat-script 2:skill:24:spider;3:stop` (Triple Shot), 50 frames.

| Bow | Arrows | Result |
|---|---|---|
| 0x1329 (arrow 0x615; #283 bones, #287 glows) | 4 | 160 particles, 32 sprites, **0 unsupported** (160 on `26b9ef07`, without #287). Glowing blue arrows (screenshot 3). |
| 0x132f (arrow 0x617, #287) | 4 | 32 particles, 144 sprites, 0 unsupported |
| 0x12f9 (#283) | 4 (type 1140) | **15 bow sparks** (`joints_created` 15), 69 particles, 0 unsupported (screenshot 4) |

All three bows score 4 projectile hits.

**Screenshots** (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-004/`, all
downscaled.

| File | Shows |
|---|---|
| `1-lorencia-arrive-1504x936.png` | window-only capture of the installed app |
| `2-devias-after-travel-no-stale-plates.png` | window-only capture of the installed app |
| `3-bow-0x1329-glows.png` | headless frame |
| `4-bow-0x12f9-sparks.png` | headless frame |
| `5-swamp-144-live-vs-native.png` | live, then native with the table |

## Checks (TEST BUDGET: no lane gate)

| Step | Result | Wall time |
|---|---|---|
| Build at `26b9ef07`: `nice -n 10 make -C native -j4`; `world`; `make -C native/app -j4 MUGFX_LIB=…` | ok | 20 s + 9 s + 14 s |
| Rebuild at `32b7f34d` (incremental, same three steps) | ok; app signed, `--check-bundle` ok | 10 s + 4 s + 8 s (+ 3 s for the detached-main restamp) |
| Rollback zip + settings copy | 11.7 MB, 64 files | < 1 s |
| Install (`ditto`) + strict signature + `--check-bundle`, each time | ok | < 1 s |
| `mu-native-data check` × 3 components; setup into the new folder; root check | ok; 179/30/94/1 files | 27 s (setup) |
| Installed smoke, with and without `--audio` | ok, 0 network | 11 s + 11 s (18 s + 17 s on `26b9ef07`) |
| Headless journey (cast, kill, pickup, `--wav`) | see above | 14 s |
| Headless travel | see above | 13 s |
| Swamp 144 tours (with and without the table) | 0 vs 1,563 velocity differences | 3 s + 3 s |
| Bow scenes 0x12f9, 0x1329, 0x132f | see above | 2 s + 2 s + 3 s |
| Windowed runs: arrival, then Warps and travel on `26b9ef07`; arrival and travel on `32b7f34d` | ok | 17 s + 15 s + 47 s; 34 s |
| `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<installed> python -m unittest native.tests.test_native_app` (incl. the private smoke over the installed game) | 17/17 at `26b9ef07`, 17/17 again at `32b7f34d` | 53 s, 53 s |
| `test_native_data_manifest` (run from `native/tests`, at `26b9ef07`) | 15/15. Not rerun: #287 touches none of its files. | 6 s |
| `scripts/audit_repository.py` | 1,838 staged files, 0 rejected | 24 s |

- Steward validators: none (docs only).
- `test_native_app` runs `make -C native preview-app` without `MUGFX_LIB`. That rebuilds only the worktree's
  `native/build/app` with the GFx stand-ins. It ran after the install, so the installed app keeps the real Ruffle
  (checked afterwards: `MUNativeCommit` 32b7f34d, `libmugfx.dylib` 17.9 MB).
- The first `test_native_app` run started at load 20.6, above the brief's limit of 14. Later heavy steps waited for
  a load of 14 or less.

## Follow-ups

1. **Hero shadow in Noria and Devias** (screenshot 2): the hero's shadow, including the wings, is an opaque,
   hard-edged black shape on the stone and snow floors. In the Lorencia field the grass hides it. Not compared with
   the live client yet (inference: the client's shadow pass is translucent).
2. **RENDER-ITEMS-002O** (renderchar glColor) is not installed. The next refresh can reuse this Native Data if 002O
   changes no export input, and only reinstall the app.
3. **1504×936 window:** the GFx HUD and the Warps window draw at 1:1 instead of scaling with the window. So the
   1280×800 row points (x 122; Noria y 257; Devias y 324) work unchanged at 1504×936. This corrects
   APP-REFRESH-003's note that scripts need `--width 1280 --height 800`. Whether the original scales them at this
   size is not checked.
4. **Demo monster pressure:** in the windowed Lorencia field arrival, the demo Hound takes the hero from 1,707 to 614
   HP within about 6 s. It is the offline demo placement, not client data, but a player who just opens the app sees
   it.
5. `python -m unittest native.tests.test_native_data_manifest` from the repo root gives 5 `ModuleNotFoundError`s
   (`test_native_lang`, `test_native_shell`). The test imports sibling modules, which works from `native/tests` and
   under `scripts/run_test_suites.py`. A `sys.path` line in the test would make both invocations work.
6. Still open from APP-REFRESH-003: `MU_NATIVE_EXTRA_ARGS` splits on spaces.
7. A later cleanup may remove the APP-REFRESH-001 Native Data folder and the legacy `Native Data` folder. That is the
   owner's call. Keep APP-REFRESH-002 as long as `rollback/app-refresh-004` is kept.

## Cleanup

- Kept: the rollback folder, the five screenshots, and the canonical export set (`scratch/native-data/export`, owned
  by NATIVE-DATA-MANIFEST-001).
- Deleted: `scratch/app-refresh-004` (helpers, runs, tour outputs, frames), `native/build` of this worktree, the
  worktree and the local branch.
  - The helpers are small and easy to rebuild from this file and APP-REFRESH-003's description:
    - `hl.py`: a headless run with an app plan;
    - `runw.sh`: a windowed run at the app's own size, with muted settings;
    - the journey scripts `hj.txt` (cast, kill, Space) and `travel.txt` (M, 122,257, M, 122,324);
    - a spider-only placement (`actor 3 185 128 0 label spider`) for the bow scenes.
