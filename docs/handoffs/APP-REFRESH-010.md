# APP-REFRESH-010

Implementation handoff, 2026-11-08. Branch `codex/app-refresh-010`, worktree `worktrees/app-refresh-010`.
GPT-6.1 Sol. Offline installation and verification, plus four validator-anchor corrections. No production code
changed. The installed app is the detached main build, not the documentation branch.

## What the installed app now has

Native Preview is installed from latest main **`a55200e2`**, #350. Main was still that commit at the final fetch.
It includes everything since APP-REFRESH-009's `a7f7b247`:

- #344 RENDER-ITEMS-CLOAK and #348 CLOAK-002: the 54 wing-cape cases, physics cloth, glow pass and wind.
  This lane visually checks one class-0 wearer; it does not claim a new original-client animation comparison.
- #347 TEST-HYGIENE-001: test/build-order, environment and isolation corrections.
- #349 REGRESS-003: opaque native frame captures through `mu_png_write_opaque`.
- #350 RENDER-ITEMS-002U: wing joints `0x7f7c`/`0x7fd3`, a rendered-frame counter supplied to item draws,
  51 regenerated counter-dependent bodies, and body `0x0f2a`, bringing admitted bodies to 1,364/1,674.
- #346 README-IMAGES-D: documentation and images.

**Visual counter proof did not pass.** The counter changes the reconstructed atlas UVs, but the tested native
atlas passes have blend light 0 and fixed-pose renders remain identical across counter values. The app contains
#350's implementation; visible counter-driven texture animation is not established here. The moving body pose
is not substituted for that proof. See proof (c) and follow-up 1.

**Not included:** a correction to that native blend-light input; armour cloths from CLOAK-003; the six unadmitted
counter types; the remaining 310 bodies and rank-5 gaps. The existing fixture/demo boundaries and missing world
placements remain. No live service, event-state, protection or character-power work belongs to this refresh.

## Installation and rollback

Order: rollback, root build, one full private native/tests run, narrow repairs/reruns, build-time export-input
comparison, detached-main app build, installation, installed-app proofs. The branch was created after the app
build, so `MUNativeCommit` is **a55200e2**.

- Installed app: `~/Applications/Mu The Matrix Native Preview.app`.
- Commands from the repository root, under `nice -n 10`: `make -j4`, `make -C native -j4 world client`, then
  `make -C native/app -j4 MUGFX_LIB="$MU_GFX_LIB"` after sourcing private-env.sh.
- Real Ruffle is bundled from `mu-mac-tools/native/scratch/polish/libmugfx.dylib`, 17,938,288 bytes, the existing
  October 22 build. `native/gfx`, including mugfx and its Ruffle patches, is unchanged in the refresh range.
- Before replacing the app, the process check detected a Preview process. Installation waited; it exited without
  intervention. A second check found no launcher or client. No Preview process was killed.
- The prior app was renamed into lane scratch, then the new bundle copied into the install path with `ditto`.
  The swap had a restore-on-error path. `codesign --verify --deep --strict` and `--check-bundle` passed after copying.
- Native Data manifest check passes. Setup remains done, with 179 GFx movies, 31 text tables, 47 object files and
  a sound table. Owner `settings.json` is byte-identical to `settings.json.before`.

Rollback folder: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-010/`:

| File | Verification |
|---|---|
| `Mu-The-Matrix-Native-Preview-APP-REFRESH-009-a7f7b247.app.zip` | 11,788,703 bytes, 66 entries; SHA-256 `3dc834612794049e125c012bbf4c3a2e6c8711687006ee41ae800a72a505ccd4` |
| `settings.json.before` | selects APP-REFRESH-006/Native Data |
| `proofs/` | six opaque window-only proof PNGs, 727,412 bytes total |

To restore, first wait until Preview is closed. Move the current Preview bundle aside and use
`ditto -x -k` on the rollback zip with `~/Applications` as the destination. Its top-level entry is the app bundle.
Restore `settings.json.before` to `~/Library/Application Support/MuTheMatrixNative/settings.json` if the selection
has subsequently changed. This lane did not change it. Older rollbacks, including app-refresh-006, are retained.

## Native Data kept

Folder: **`~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-006/Native Data`**.

The build-time diff `a7f7b247..a55200e2` is empty over:

- `scripts/build_native_data_export.py`, `live_lang_to_plain.py`, `live_lang_filters.py`,
  `live_effect_table_to_plain.py`, `live_objects_to_plain.py`, `extract_audio_tables.py`,
  `native_data_manifest.py` and `pins.py`;
- `native/data`, `native/gfx` and `native/app`, including the GFx converter, app setup recipe and bundling.

The changed scripts in the range are compiled-table generators, validators, the audit and the test runner.
None is an export input. The exporter recipe imports the same manifest/pins and calls unchanged exporters.
The existing canonical set is therefore kept, verified by the installed manifest tool. No `--setup`, new export,
new data folder or canonical-data write was needed. The demo files are app resources and ship with this build.

## Full private native/tests and the two errors

From the repository root, at `a55200e2`:

```sh
. ~/Documents/MTM/mu-mac-tools/native/private-env.sh
MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py native/tests
```

The APP-REFRESH exception to brief 8d was applied: the full 149 work items ran once, rather than an 8d reduced
selection. Result: **1,001 tests, 981 passed, 18 skipped, 0 failures, 2 errors**, 1,212.66 s wall.

Both errors were `ClientComparison` in test_render_effects12/13. Direct reproduction reached the new
exact-one-anchor assertion in `validate_joints.run_mutants`, added by #350, `c950da3f`. It exposed four older
ambiguous strings in `bow_joints.inc`: `field_a25 = 2`, `faces = 2`, `lifetime = 30`, and `subtype == 4`.
The original comparisons reached equality before mutant construction failed. This was neither a missing input
nor a rendering mismatch.

The fix lengthens those four anchors with adjacent statements to select their original first/intended branches.
The planted changes, case counts, expected mutant counts and production C are unchanged. All 27 bow anchors
in the two lists match exactly once. Existing regression modules failed before and now pass: **7/7 tests** in
38.61 s, including **22/22 + 16/16 compiled mutants**. The full private suite was not repeated.

The 18 skips are explicit: 15 need an in-tree mugfx/Ruffle build and its tools, two need MU_NAMES_GFX_MOVIES,
and one needs MU_QUEST_MOVIES. The quest proof below supplies the installed movies and closes that one separately.
The canonical private environment stays unchanged.

## Standard journeys on the installed app

Each app run uses isolated support, logs and option directories, `--no-store`, public demo names and the bundled
network guard. Headless runs use the installed launcher's `--print-plan` and its installed mu-client. Every guard
exit report has 0 connects, 0 inet, 0 lookups and 0 other calls denied.

| Proof | Result |
|---|---|
| No-Python smoke, GL, without and with audio | pass; PATH=/nonexistent, Apple M5, world reached, zero network |
| Field selected-skill cast | pass; skill_casts 1, skill_refused 0 |
| Kill, drop, Space pickup | pass; kills 1, drops 1, space_picks 1, one pickup request and one completed pickup |
| Recorded audio, same field journey, music on / volume 9 | 827,668 stereo frames at 44.1 kHz; peak 31,656 = -0.300 dBFS; 0 samples above 31,656 or at full scale; RMS 4,735 |
| Headless Warps, Lorencia -> Noria -> Devias | pass; travels 2, plates removed 4, plates 1, stale plates 0; 16/16 HUD samples match at 1100/1100 |
| Hound/HUD, 800 frames | pass; kill/drop 1; HUD equals session in all 29 samples, 1100 -> 1077 HP, maximum stays 1100 |
| Windowed Warps, installed launcher, 45 seconds | pass on Retina: 899 frames / 45.02 s, about 20.0 fps, drawable 3200x2000; same clicks travel 0 -> 3 -> 2; 35/35 HUD samples match; zero stale plates and network attempts |
| Window title and capture | OFFLINE PREVIEW / no server connection; diagnostic title suffix 25.0 fps at capture; window-only screencapture by CGWindowID |
| Windleaf headless | pass; 1119/778/1775/284 current = HUD = maxima; skill 2044, one cast, 121 effects, max 1 rain / 11 impacts / 66 rings, 0 unsupported |
| Windleaf windowed | pass on Retina 3008x1872; 15/15 HUD samples match; same 121 effects, one cast, two sounds, 0 unsupported; rain captured at frame 125 |
| Offline quest accept/kill/complete | pass; existing LorenciaDemo test, 1/1, installed movies/lang and same-main mu-world; accepted 1, completed 1, progress 3, active empty, undecodable 0, no request 902 |

The field session is a copy of the bundled session with `join 1 0 179,131 90`. The still placement removes only
`wander` from the bundled monster rows. The cast/kill script moves and right-clicks at 690,238 at 90/91/93, clicks
there at 131/191/251, then Space at 300/340/380/420. Travel uses M at 100/300 and rows 122,257 / 122,324 at 131/331;
windowed uses 300/331/600/631 and a final move at 700.

The old fixed-frame row-2 Windleaf flow did not enter the world on this run. A private fixture copies the bundled
Windleaf record into the known-working auto-selected slot 1, retains all five list entries, and supplies exactly
the bundled Windleaf join/profile data at 182,128. It changes no character values. Auto enters that slot, key 2
at frame 100 selects 2044, and a right-click at 420,490 at 110 targets the still Bull Fighter. The older 845,100
point missed. Neither fixture is installed or committed.

## New proofs

All rollback comparisons use the APP-REFRESH-009 zip's mu-client, its own launch plan and matching virtual frames.
RGB comparisons ignore the rollback PNG's unreliable alpha. New PNG alpha is checked before cropping/quantizing.
These are native offline comparisons, not original-client pixel equivalence.

| Requested proof | Verdict and evidence |
|---|---|
| (a) Class-0 physics cape, moving vs rollback | **PASS.** Velvet, class 0, wing 12:156 = 0x2382, at 126,126, dir 7; hero at 128,124. New vs rollback frame 150 changes only the cape, 2,051 pixels, bbox 632,152..700,214. The new cape region changes in 3,348 pixels between frames 120 and 150; screenshot 1 shows the two shapes and rollback. |
| (b) Wing 0x22ec / new joint body | **PASS.** Streak, class 0, wing 12:6 at the same tile/direction. Frame 150 adds blue streaks: 4,558 pixels vs rollback, bbox 598,92..727,212. Screenshot 2. |
| (c) Visible frame-counter body animation | **FAIL / not established.** Atlas wears 2:68 +9 = 0x0f2a. The new body draws, 758 pixels vs rollback at frame 150, and its pose moves across frames. That does not prove counter-driven atlas motion. Fixed-pose/time renders at counters 0/7/8, also swords 0x0b66 and lance 0x1109, are pixel-identical. The compiled command stream changes 0x0f2a mesh 4 u from 0 to 0.75 at counters 0/7, but native fill_item leaves blend light 0; that pass selects blend mesh 4 with blend light 0. This is the rendering input to investigate, not a reason to claim a visual pass. Screenshot 3 is labeled unverified. |
| (d) Raklion statue spray in view | **PASS, early-frame view.** Join world 57 at 198,211, angle 90, default zoom, frame 60. Object 1259, type 0x14, remains at 19613.52,21512.94,107.64. A same-frame installed-app run with only --no-particles isolates blue spray below its jaw: 4,624 changed pixels in x500..595, y310..390. Screenshot 4 shows particles off/on/difference. The offline helper sees 0x801c/8, 0x801c/9 and 0x801e/7 at projected points around 446..565, 238..326; the same-main world report creates 12 object particles. The old arrival 224,211 projects these points off the top-left. Later frame 210 does not retain the useful statue/spray view; persistent visibility remains a follow-up. |
| (e) Opaque screenshots | **PASS.** Ten installed headless world captures plus two windowed rain captures, 12 total, have alpha min=max=255. Final proof PNGs are opaque indexed PNGs without transparency; no alpha patches are composited away to obtain this result. |

The cape, wing and mace players are private one-player demo files. None replaces the shipped crowd.
The Raklion diagnosis also used a scratch copy of EncTerrain58.plain with only object 1259 removed, then a
particle-only toggle to separate spray from statue geometry. The canonical folder was never modified.

### Retained screenshots

`~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-010/proofs/`, local only, never committed.
All are at most 760 pixels wide, six files / 727,412 bytes total. Crops and comparison panels contain only native
window/framebuffer pixels with short evidence labels. Demo names only.

| File | Contents |
|---|---|
| `1-cape-motion.png` | rollback frame 150, installed frames 120 and 150 |
| `2-wing-22ec-streaks.png` | rollback, installed, 4x RGB difference |
| `3-0f2a-counter-unverified.png` | new body and moving pose; explicitly not a visual counter proof |
| `4-raklion-spray.png` | frame 60 at 198,211, particles off/on/4x difference |
| `5-retina-window-travel.png` | installed app after windowed Warps travel, OFFLINE PREVIEW and fps title |
| `6-windleaf-2044.png` | windowed frame 125, rain and 1119/778 HUD |

## Checks and wall times

No full lane gate. One heavy job at a time, nice 10, make at most -j4, test/validator workers 2.
Resource checks deferred steps when load exceeded 14; memory stayed above the 25% threshold. The app build and
checks ran from the repository root. Data check took 0.41 s; installation plus strict signature/bundle check 0.319 s.

| Step | Result | Wall |
|---|---|---:|
| Rollback zip / extraction check | 66 entries, hash above | 0.61 s / 0.06 s |
| Root build / incremental world-client / detached real-Ruffle app | pass | 30.06 / 0.23 / 2.02 s |
| Full private native/tests, a55200e2, 149 modules | 1,001 tests; 981 pass, 18 skip, two anchor errors | 1,212.66 s |
| Direct error reproductions, effects12 / effects13 | exact ambiguous-anchor assertion | 3.66 / 3.88 s |
| Fixed private modules, effects12 + effects13 | 7/7, 22/22 + 16/16 mutants | 38.61 s |
| Native Data export-input diff / manifest check / settings cmp | unchanged / valid / identical | <1 / 0.41 / <1 s |
| Installed smoke, no Python, without/with audio | pass, zero network | 17.15 / 17.94 s |
| Field+audio / Hound/HUD / headless travel | pass | 10.69 / 12.56 / 13.16 s |
| Windowed travel | pass, Retina | 47.15 s including launcher cleanup |
| Cape final camera, installed / rollback | pass | 9.26 / 7.28 s |
| Wing joint, installed / rollback | pass | 8.40 / 7.42 s |
| New mace body, installed / rollback | visible body, counter proof unverified | 7.72 / 7.56 s |
| Counter fixed-pose probes, eight angle/counter images plus three body pairs | identical, unverified | about 5 s total |
| Raklion camera probes, including the old arrival and zoom attempt | useful early view found at 198,211; other attempts not claimed | 6.48 + 7.29 + 9.42 + 11.32 + 9.62 s |
| Raklion record-removal control / particles-off control | isolated statue / isolated spray | 6.94 / 6.69 s |
| Same-main Raklion world report / projected-particle helper | 12 object particles; projected into window at new tile | 1.89 s / about 2 s |
| Windleaf final headless / windowed | one cast, 121 effects each | 9.47 / 26.74 s |
| Quest LorenciaDemo, explicit installed movies | 1/1 | 4.33 s |
| Final affected selection | exactly effects12/13/14 | 20.44 s |
| Three selected private validators, no mutants, cached | 3/3: 64 + 180 + 660 instruction cases, 0 mismatches | 1.53 s, row walls 0.4 / 0.6 / 1.0 s |
| Portable affected selection | 7 work items; includes native_social2 conservative fallback | 63.29 s |
| Portable affected execution, including selection | 310 tests: 265 passed, 45 intentional skips, 0 failures/errors | 125.57 s total, 54.0 s test execution |
| Four rule-6c modules with canonical private env | 36/36 passed | 64.72 s |
| Staged repository audit | 2,104 files, 0 rejected; final snapshot rechecked before push | 19.88 s initial pass; final wall in PR |

Steward validators: validate_render_effects12, validate_render_effects13, validate_render_effects14, tested at
`6e046dacbdde0ed289d0b5882397bd1f9301dedf`, with private-env.sh. No row needs mutants from the steward.
The two changed lists ran all their compiled mutants once after the fix. Effects14 imports effects12; its
unchanged comparisons ran without mutants. No C, header, table size, exporter or app source changed, so 6b/8b add
no other consumers. The new documentation does not change those validator inputs. The portable selector also kept test_native_social2 on its conservative computed-path fallback; it ran rather than being dropped. The 45 portable skips are distinct from the full private run's 18 unavailable-input/tool skips.

## Follow-ups

1. Recover/wire the native item blend-light input before claiming visible #350 atlas animation. Reproducer:
   same-main mu-render character, Hammer15.bmd as weapon0, type 0x0f2a, level 9, fixed pose/time, counters 0 and 7.
   The draw stream changes u but the final PNG does not. Native fill_item zero-initializes blend light and does
   not supply a caller value. Do not replace it with an assumed constant without the original caller evidence.
2. Raklion: explain why the useful early statue/spray view is absent in the later samples. The frame-60 picture
   and particle-only control are verified; persistent/event-state equivalence is not. No server-state work here.
3. The fixed-frame character-select row-2 flow missed on this run. The private Windleaf slot-1 fixture gives the
   cast/HUD proof, but does not certify the old row-2 script. Update its scene/readiness handling separately.
4. Existing limits: armour cloths, guild-war/duel/buff inputs, native wind stream vs process rand, no live cape
   animation equivalence, 310 item bodies, six other counter types, rank-5 owner paths, Muun/Uruk demo coverage,
   missing Test Area 121 and worlds 145/95/110 placements, unavailable Arca War worlds, inventory icon sprite
   follow-up and retained legacy data/export folders. The October 22 Ruffle build remains source-compatible.
5. The Retina travel follow-up from 008/009 is closed by the 3200x2000 windowed run above. The other 17 skipped
   optional tool/movie tests were not converted into passes by this lane.

## Cleanup and delivery

Keep the rollback zip, settings copy and six small PNGs in rollback/app-refresh-010. All older rollbacks stay.
After writing the ready-prs line, remove lane scratch and renders, all worktree build outputs, private test reports,
raw frames, WAVs, helpers and unzipped/retired app copies. No new private input is needed by a later lane; the
canonical inputs and recipes above reproduce the findings. Keep the source worktree until the steward merges.
No pushes after the ready line. The MERGE-STEWARD owns merging.
