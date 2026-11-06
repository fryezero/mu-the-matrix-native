# APP-REFRESH-006

Implementation handoff, 2026-11-06. Worktree `worktrees/app-refresh-006`, branch `claude/app-refresh-006`. Claude
Opus 5.5 lane. Offline only: no original client, launcher, live read, account, network or protection work. The
owner's Wine play app, its prefix settings and the staged Wine app were not touched.

## What the installed app now has

The Native Preview was reinstalled from main **`7e6a9292`** (#311 RENDER-WORLDS-SLOTS2, steward batch 51). It has
everything since APP-REFRESH-005 (`7d7d694b`):

- #303 RENDER-WORLDS-S3: Imperial Guardian 69-72, Event square 114, Test Area 121;
- #305, #299 TEST-SPEED-003/002: tooling only;
- #306, #309 RENDER-EFFECTS-014/015: the last bow joints, ground-skill rain 0x70a with 0x70c rings and stones,
  terrain decals, effect-sound sites;
- #307 APP-POLISH-004: window title without the fps suffix, inventory icons from Lang.mpr ItemTRSData;
- #308 RENDER-WORLDS-SLOTS: custom/after/invisible-move slots (Kubera, Swamp of Darkness, Ferea, Vulcanus, 79);
- #310 RENDER-ITEMS-002P: 57 more item bodies;
- #311 RENDER-WORLDS-SLOTS2: the outer RNG draw in every class world, 17 more slots.

**Not included:** RENDER-EFFECTS-016 and RENDER-ITEMS-002Q (no PR at build time, 13:35 CST).

**Order of events:** prep, rollback, the exporter change and the new export set were done while #311 waited for
batch 51. #311 merged at 13:34. The worktree was checked out detached at `7e6a9292` (so the bundle's
`MUNativeCommit` is the main SHA, not this branch's), built, installed at 13:35 and set up; every proof below ran on
that build. The worktree then went back to the branch for the tests.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 7e6a9292, real Ruffle.
  - Built with `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`
    (bundles `Contents/Frameworks/libmugfx.dylib`, 17.9 MB).
  - Installed with `ditto` over the removed old copy, after checking that no Preview was running.
  - Strict deep signature check and `--check-bundle` pass (mu-client, network guard, GFx library (Ruffle)). After the
    test runs the installed copy still has `MUNativeCommit` 7e6a9292 and the 17.9 MB `libmugfx.dylib`.
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-006/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-005-7d7d694b.app.zip` (11.7 MB, 64 files, SHA-256 `c1aa5fce…f508e33`);
  - `settings.json.before`, which selects `APP-REFRESH-004/Native Data`.
  - To roll back: unzip the app into `~/Applications` and copy `settings.json.before` over
    `~/Library/Application Support/MuTheMatrixNative/settings.json`. The APP-REFRESH-004 Native Data folder is kept
    untouched as the data rollback.
  - The `app-refresh-002/` to `-005/` rollbacks are kept.

## Native Data

APP-POLISH-004 (#307) taught `scripts/live_lang_to_plain.py` to write `itemtrs.tsv`, but the canonical export set
(`~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export`) predates it, and the installed Native Data had no
such file, so the app kept the itemtrsdata.bmd stand-in.

- **Exporter change (this PR):** `scripts/build_native_data_export.py` now requires the table after the lang step
  (`require_itemtrs`): `itemtrs.tsv` must exist, be recorded by the lang export's own manifest, parse as code + six
  signed 32-bit words with unique codes (`itemtrs_rows`), and hold the pinned 4,919 codes (`ITEMTRS`). The converter
  skips a table a snapshot lacks without failing; the set build now fails instead. The summary reports
  `itemtrs_rows`. No change to the converter, the manifest engine or app setup: the table comes from
  `live_lang_to_plain` itself, so its manifest records it.
  - lang4 and both lang5 snapshots give the same table (SHA-256 `6937938c…aaef185`, 303,350 bytes, 4,919 rows).
- **New canonical set:** built with `build_native_data_export.py --out …/native-data/export-app-refresh-006`
  (`itemtrs_rows` 4,919, mapanim 143/10, 31 lang files, 47 object worlds, audio 1,515/1,514), then renamed into
  place. The previous set is kept beside it as `export.before-app-refresh-006` (11 MB).
  - Against the previous set: one added file, `lang/itemtrs.tsv`; the lang manifest gains its `file` line
    (`complete 30` → `31`; producer unchanged, `lang-export-v1-effects-v1-mapanim-v1-live-read-2026-11-04`). The
    `objects/live/plain` and `audio/tables` manifests are byte-identical. `mu-native-data check` passes on all three.
- **New Native Data:** `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-006/Native Data` (74 MB), by
  the installed app's `--setup` from the new set: gfx converted 179, lang copied 31, objects copied 94, sound 1,
  manifest written (19 s).
  - `mu-native-data check` passes. Root manifest against APP-REFRESH-004's: `file 6937938c… 303350 lang/itemtrs.tsv`
    added, the lang manifest's own entry changes (`9ac76e53…` 3,321 bytes → `f8e045d6…` 3,410 bytes),
    `complete 390` → `391`. Every gfx, objects and sound entry is identical.
  - `settings.json` now selects that folder (`settings.json.before` in the rollback folder). `--print-settings`:
    "GFx movies 179, text tables 31, object files 47, sound table yes; setup done". `--print-plan`:
    `MU_LANG_DIR=<…/APP-REFRESH-006/Native Data>/lang`, `--world-objects <…>/objects`.

## Journey proofs (installed app, `7e6a9292`)

**Smoke:** `--smoke --backend gl`, isolated logs/settings, `PATH=/nonexistent`, `--no-store`, with and without
`--audio`: ok, world reached, Apple M5, guard `mu-nonet`, 0 connects, 0 inet, 0 lookups, 0 other calls denied.

**Headless:** the installed bundle's mu-client with the app's own launch plan (`--print-plan` over an isolated
support dir holding a copy of the owner's new settings), `--auto --hold 6`, `--no-store`, isolated option settings,
the field session (slot 1 at Lorencia 179,131). The helper runs under `nice` and starts the client directly.

| Proof | Result |
|---|---|
| Selected-skill right-click cast (Budge Dragon) | `skill_casts` 1, 0 refused |
| Kill, drop, Space pickup | `kills` 1, `drops` 1, `space_picks` 1, 1 pickup request, 1 completed |
| Audio (option.ini `[DEFAULT]` `IsMusicPlay=1`, `Volum=9`; `--wav` over the same journey) | 898,228 stereo frames at 44.1 kHz; peak 31,656 = **−0.300 dBFS**; 0 samples above 31,656; 0 at full scale; RMS 4,792 |
| Warps travel M → Noria → M → Devias | `travel: world 0 -> 3` (175,117), `world 3 -> 2` (208,47); `travels` 2, `travel_plates_removed` 4, `plates` 1, `stale_plates` 0 |
| Arrival HUD and a Hound hit (`MU_HUD_TRACE=1`) | HUD = session = **1100/1100** HP, 200/200 MP, 52/52 SD, 25/25 AG for 13 samples; one hit → 1077/1100, then 16 samples steady; Hound killed (`kills` 1, `drops` 1). Travel run: 1100/1100 in all 17 samples |
| **(d) Kubera arrival** (session `join 1 123 237,88`, the DATA-ACQ-002 capture tile; 200 frames) | rc 0, world 123, scene 6 for 143 frames, no crash; crystals, lanterns and mine props drawn (screenshot 4) |

**Windowed:** the installed app itself (`MuNativePreview --seconds 75`, isolated support, log and option dirs,
muted, the field session, `MU_NATIVE_EXTRA_ARGS="--no-store --auto --hold 6 --input-script '…' --out-dir '…'"`),
own window size 1504×936. Travel 0 → 3 → 2: `travel_plates_removed` 4, `plates` 1, `stale_plates` 0. HUD 1100/1100
in all 64 trace samples. 1,611 frames in 75 s (about 21 fps). Guard `mu-nonet`, 0 denials.

**(a) Window title.** All three window-only shots report the window name
"Mu The Matrix Native Preview — OFFLINE PREVIEW (no server connection)" (CGWindowList), with no
"scene 6 world … fps" suffix (APP-REFRESH-005 follow-up 7 closed). Screenshot 1 shows it in the title bar.

**(b) Inventory icons from ItemTRSData.** `mu-render ui inventory` from the same main, the installed game, time
123456, items 6571, 55, 2612 (wing 0x19ab, two weapons), only `MU_LANG_DIR` changed:

| `MU_LANG_DIR` | `render_info` | Triangles | Framebuffer SHA-256 |
|---|---|---|---|
| APP-REFRESH-004 Native Data `lang` (as installed before) | `itemtrsdata` (bmd stand-in) | 1,164 | `52581608…e444012cbf` |
| APP-REFRESH-006 Native Data `lang` (installed now) | `itemtrs` | 1,461 | `50b8d38a…1ab346f4` |

8,175 pixels change in the grid crop. In screenshot 2 (before | after) the wing is smaller and higher (ItemTRSData
scale 0.44, offset y 0.44; was 0.55/0.5), and weapons 55 and 2612, drawn edge-on before (default −90°), stand
upright with their own rotations.

**(c) Ground skills and effect sounds.** `mu-world` from the same main, installed Native Data `lang`, Lorencia
182,128, class 2, a spider at 186,128, `--combat-script "2:skill:<n>:spider"`, 40 frames, 640×400 software (the
RENDER-EFFECTS-015 scene). 0x70c and ring counts are the maximum live in one sampled frame (every 5th):

| Scene | Arrows | Effects | Particles | Max live 0x70c | Max live rings 0x703..0x706 | Decals (tiles) | Sound cues (ids) | Unsupported |
|---|---|---|---|---|---|---|---|---|
| 2044, Bow01 0x12e6 | 14 | 121 | 140 | 11 | 66 | 252 (8,788) | **2** (1373, 1374) | 53 |
| 2044, 0x12f7 | 14 | 148 | 0 | 14 | 66 | 270 (8,926) | **48** (66, 1374) | 46 |
| 2045, Bow01 | 11 | 73 | 88 | 6 | 36 | 150 (5,446) | **2** | 27 |
| 2045, 0x12f7 | 11 | 73 | 0 | 6 | 36 | 98 (3,546) | **47** | 13 |

Every count equals RENDER-EFFECTS-015's "after" (its "before", `eb2a8e76`: 0 sound cues, 0 decals, 0x70a refused).
The remaining unsupported requests are the stones' Fire06 particle (0x7f40/1..3), as recorded there. Screenshot 3
(frame 20) shows the rain, the landing rings and the craters.

**(d) Kubera, closer to live.** `fidelity_tour.py run` for DATA-ACQ-002's `123-kubera` capture with the main
`mu-world`, `objects_dir` = installed Native Data `objects`, `MU_LANG_DIR` = installed Native Data `lang`: tile
237,88, image mean |Δ| **1.591**, share > 24 0.0063, 0 missing, 0 extra, no static field differences near the hero.
For reference, RENDER-WORLDS-SLOTS recorded 4.321 (main `b8645181`, before #308) → 2.037 (#308) with AFTER5's lang;
the lower value here also carries the installed lang's `mapeffects.tsv` and #311's outer draw, so it is not a
like-for-like delta. The previously installed `7d7d694b` predates #308.

**(e) New item bodies (#310).** `mu-render ui inventory`, gallery codes 4116, 135, 2719, 2725, 6599, 138 (types
`0x1afa`, `0x0b6d`, `0x1585`, `0x158b`, `0x24ad`, `0x0b70`):

| `MU_LANG_DIR` | Level 0 | Level 13 |
|---|---|---|
| APP-REFRESH-004 `lang` | 6,025 triangles, `f6ac4417…4839a38` | 34,761 triangles, `d3e4a78d…11ff02` |
| APP-REFRESH-006 `lang` (installed) | 6,495, `9b9799e3…b486b6` | 37,003, `deba5840…125216` |

With the old lang, main reproduces RENDER-ITEMS-002P's "after" byte for byte (its "before": 4,987 triangles,
`f2a99c37…46c2`). With the installed lang the same bodies draw at their ItemTRSData fit. Screenshot 5: level 13,
the armour 0x1afa's lit passes and glow, the weapons' textured blades with glow passes, the pet and the wing.

**Screenshots** (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-006/`, at most
760 px wide, quantized (0.8 MB in all).

| File | Shows |
|---|---|
| `1-title-lorencia-arrival.png` | window-only capture of the installed app: title bar "… OFFLINE PREVIEW (no server connection)", field arrival, HUD 1100/1100 |
| `2-inventory-itemtrs-before-after.png` | inventory grid crop, APP-REFRESH-004 lang (left) and installed lang (right) |
| `3-ground-2044-rings-stones.png` | `mu-world` frame 20 of skill 2044 with Bow01: rain, 0x70c rings, craters |
| `4-kubera-arrival.png` | installed client, headless frame at Kubera 237,88 |
| `5-new-bodies-level13.png` | #310 gallery at level 13 with the installed lang |

## Checks (TEST BUDGET: no lane gate)

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT=~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`,
`MU_SNAPSHOT_DIR=~/Documents/MTM/mu-mac-tools/native/scratch` (test_app_polish4's private lang3 test),
`MU_EVIDENCE_DIR=<main checkout>/evidence`. Heavy steps under `nice -n 10`, `make -j4`.

| Step | Result | Wall time |
|---|---|---|
| Rollback zip + settings copy | 11.7 MB, 64 files | 0.7 s |
| `build_native_data_export.py` (new set) | itemtrs 4,919; every component checks | 23 s |
| Build at `7e6a9292`: `make -C native -j4`, `world`, `make -C native/app -j4 MUGFX_LIB=…` | ok; signed, `--check-bundle` ok | 10 s + 4 s + 9 s |
| Install (`ditto`) + strict signature + `--check-bundle` | ok | < 1 s |
| App `--setup` into the new Native Data + `mu-native-data check` | ok | 19 s + < 1 s |
| Installed smoke, without and with `--audio` | ok, 0 network | 12 s + 12 s |
| Headless journey with `--wav` / Hound+HUD (800 frames) / travel / Kubera | see above | 13 s / 18 s / 14 s / 8 s |
| Windowed travel with three window-only shots | see above | 77 s |
| Kubera fidelity tour | 1.591 | 3 s |
| Inventory renders (trs before/after, gallery 0/13, old-lang control) | see (b), (e) | 4 s |
| Ground scenes, 4 | see (c) | 8 s |
| `python -m unittest native.tests.test_native_data_manifest` (new test: the set requires a recorded `itemtrs.tsv`) | 16/16 | 7 s |
| `native.tests.test_native_lang` (shared `synthetic_snapshot` gains an optional ItemTRSData map; brief 6b) | 15 (2 skipped) | 5 s |
| `native.tests.test_app_polish4` (6b: imports the same helper; private lang3 test included) | 4/4 | 28 s |
| `native.tests.test_native_app` (incl. the private smoke over the installed game) | 19/19 | 58 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, `MU_GATE_JOBS=2`): 6 items | 2 suites, 308 tests, 260 passed, 48 skipped, 0 failures | 68 s |
| `scripts/audit_repository.py` (one new file) | 1,960 staged files, 0 rejected | 17 s |
| Brief-6c doc modules: `tests.test_world_captures_2`, `tests.test_repository_policy` | 13/13 | 0.3 s |

- Steward validators: none. No validator builds or imports `build_native_data_export.py`; the changed test
  helper is not compiled by any row.
- `test_native_app` runs `make -C native preview-app` without `MUGFX_LIB`, which rebuilds only the worktree's
  `native/build/app`. It ran after the install; the installed copy keeps the real Ruffle.
- Load (the steward's batch 51 ran alongside): most steps started at load 8–13. Four short steps started above the
  brief's 14 without waiting: the prep build (14.9, 11 s), a prep ground render (22, 4 s), the setup (15.1, 19 s) and
  the Kubera tour (16.1, 3 s). Memory stayed at 59–65% free.

## Follow-ups

1. **Effect sounds in the client are not counted.** mu-client prints no sound-cue counter, so (c)'s cue counts
   come from `mu-world` scenes. The installed client's journey WAV shows the mix plays (peak −0.300 dBFS). A
   summary counter (`sounds`) in mu-client, as in mu-world's combat summary, would let a refresh count them on the
   installed app.
2. **Ground skills are not reachable from the demo session.** The scenes used `mu-world --combat-script`. The
   demo characters do not have skills 2044/2045 selected, so the installed app cannot show 0x70c without a session
   or skill-book change.
3. **Weapons spill past their cells.** With ItemTRSData, upright weapons (55, 2612; 135 at +13 with its glow quad)
   reach beyond their grid cells (screenshots 2 and 5). APP-POLISH-004 found no clip or bounds fit in the
   original's item pass, so this may match the original; not compared with an original-client capture.
4. **RENDER-EFFECTS-016 and RENDER-ITEMS-002Q** are not installed. The next refresh can keep this Native Data unless
   an export input changes (`build_native_data_export.py`'s recipe, its exporters, `native_data_manifest.py`,
   `pins.py`).
5. **Old export set:** `scratch/native-data/export.before-app-refresh-006` (11 MB) can be deleted once no lane's env
   points at it; nothing in the repository does.
6. Still open from APP-REFRESH-005: Arca War worlds (93/97/102/112) are not installed in the owner's client; the
   new worlds 145/95/110 draw no objects (no object plaintext in the export set); bows 0x12f7/0x12fb unsupported
   kinds; the APP-REFRESH-001 and legacy `Native Data` folders may be removed (the owner's call). APP-REFRESH-004's
   folder is now the data rollback; APP-REFRESH-002's can go once the `app-refresh-004` rollback is retired.

## Cleanup

- Kept: the rollback folder, the five screenshots, the new canonical set (`scratch/native-data/export`) and the old
  one (`export.before-app-refresh-006`, follow-up 5).
- Deleted: `scratch/app-refresh-006` (helpers, sessions, runs, frames, WAV, inventory and ground renders, tour
  output), this worktree's `native/build`, the worktree and the local branch.
  - Helpers, rebuildable from this file and APP-REFRESH-005: `hl.py` (headless run of an app bundle's mu-client
    with the app's plan; `--session`, `--audio`, `--hud`, `OPTION_INI`), `runw.sh` (the GUI app with `--seconds`,
    isolated dirs, muted `option.ini`, window-only shots with a compiled `winshot.swift`), `hj.txt`, `hound.txt`,
    `travel-hl.txt`/`travel.txt` and the spider placement as in APP-REFRESH-005. The audio option file needs the
    `[DEFAULT]` section (a file with another section leaves BGM off and the WAV silent).
