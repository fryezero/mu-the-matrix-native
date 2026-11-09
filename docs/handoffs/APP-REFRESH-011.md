# APP-REFRESH-011

Implementation handoff, 2026-11-09. Branch `codex/app-refresh-011`, worktree `worktrees/app-refresh-011`.
GPT-6.1 Sol. Offline Native Preview installation, three test-fixture repairs and documentation.
No production code or export input changed in this lane. The app is a detached main build.

## What the installed app now has

Installed `MUNativeCommit`: **`54a53e1a`**, latest main through #360, full SHA
`54a53e1a2d0001f37e4331d390043d5fc0dffe6e`. It includes everything since APP-REFRESH-010's `1e2a927a`:

- #353 FOLLOWUPS-001: opaque tool captures, CLI inventory overlay fix and opt-in accessory slots 9-14.
- #354 RENDER-EFFECTS-022: counter-gated mace particles, retained OBJECT points and rank-5 world callers.
- #355/#360 RENDER-ITEMS-002V/W: 1,364 -> 1,404/1,674 admitted bodies, six remaining counter types, three bows,
  31 named-mesh parts and the recovered blend-light input making `0x0f2a` atlas animation visible.
- #356 GFX-FRAME0-001: the rebuilt pinned GFx bridge that honours `MU_GFX_TEST_CLOCK`.
- #357/#359 RENDER-EFFECTS-023/024: mace bone sprites and textures, nineteen particle pairs, owned rings,
  and Ferea's fire emitter/child particles.
- #358 CLOAK-004: Death King, Nightmare and Eunice NPC/monster cloths and actor lifetime/model handling.

The five new proof categories below pass. Test Area 121 is a limited join-only result, not the cloth proof.
The 270 remaining bodies, exact Hammer14 bone-name refusal and clouds/28 remain. Appearance fixtures do not
change the owner's equipment, gameplay values or canonical placements. No new default demo actor is installed.

## Installation and rollback

Order: rollback; root build and one full private run at main `54a53e1a`; reproduce and repair three test-only
failures; affected tests; fresh main check; detach at the same SHA; build and install; installed-app proofs.
The test edits affect no app build input. No Preview or mu-client was running at either pre-install check.
No owner process was killed. Only Native Preview was replaced; Wine apps and prefix settings were untouched.

- Installed app: `~/Applications/Mu The Matrix Native Preview.app`.
- Build from the repository root: `nice -n 10 make -j4`, `nice -n 10 make -C native -j4 world client`, then
  `nice -n 10 make -C native/app -j4 MUGFX_LIB="$HOME/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib"`.
- Raw GFx artifact SHA-256, checked before bundling:
  **`eaf39b722e34e6d6f2eae34378bbac67d5004d2b4a9be8de005df3edd26a1645`**.
- Installed `Contents/Frameworks/libmugfx.dylib` after rpath fixup and signing:
  `8a20a369a93e211fe6e3431b54bc3d3fd74e3c1c8d1c5ba647c70fbe3d6ed70e`.
- The old bundle was moved into lane scratch, then the new one copied with `ditto`, with restore on error.
  `codesign --verify --deep --strict` and installed `--check-bundle` pass.
- Owner `settings.json` is byte-identical to the pre-install copy. No `--setup` or data-folder switch was needed.

Rollback folder: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-011/`.

| File | Verification |
|---|---|
| `Mu-The-Matrix-Native-Preview-APP-REFRESH-010-1e2a927a.app.zip` | 11,809,844 bytes, 66 entries, `unzip -t` passes; SHA-256 `820e1d6967e507cdef73b65797702e64d3f96f35000477812856c15e7ab4c667` |
| `settings.json.before` | selects APP-REFRESH-006/Native Data; unchanged |
| `proofs/` | six opaque PNGs, 1,125,427 bytes total, at most 760 pixels wide |

To restore, wait until Preview is closed. Move the current app aside, then `ditto -x -k` the rollback zip into
`~/Applications`. Its top-level entry is the app. Restore `settings.json.before` to
`~/Library/Application Support/MuTheMatrixNative/settings.json` only if settings subsequently changed.
All older rollbacks remain, including app-refresh-007; deleting it was optional.

## Native Data kept

**`~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-006/Native Data`**.

The diff `1e2a927a..54a53e1a` is empty over the export recipe and inputs:
`scripts/build_native_data_export.py`, `live_lang_to_plain.py`, `live_lang_filters.py`,
`live_effect_table_to_plain.py`, `live_objects_to_plain.py`, `extract_audio_tables.py`,
`native_data_manifest.py`, `pins.py`, `native/data` and `native/app`.

Only three `native/gfx` files changed: the window helper Makefile adds mu_perf.c, the Cargo helper locks/caps
build jobs, and mu_gfx_window saves opaque captures. Neither gfxconvert, mugfx source nor the Ruffle patches
changed. Changed item scripts generate compiled tables, not Native Data. The existing canonical set is retained.
The bundled manifest tool passes; setup remains done with 179 GFx movies, 31 text tables, 47 object files and
a sound table. No export, canonical data, legacy data folder or settings selection was modified.

## Full private native/tests and repairs

From the repository root at `54a53e1a`:

```sh
. ~/Documents/MTM/mu-mac-tools/native/private-env.sh
MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py native/tests
```

The APP-REFRESH exception to 8d applies. All **155 work items** ran once: **1,038 tests, 1,019 passed,
16 skipped, three failures, no errors**, **1,354.85 s wall**. All three failures reproduce together in 5.01 s.

1. `test_native_item_cloak.WorldScene.test_wearers_and_cadence`: all cloth count, step and wind assertions
   pass, but the final whole PNG differs. Weapons in this cloth-only fixture have pre/owner programs whose
   random consumption depends on saved draws. Removing the two weapons preserves the cloth scenario and
   restores byte identity at frame 45. No rendering behavior or comparison tolerance was changed.
2. `test_native_world_predraw`: sprite total 170, formerly 110.
3. `test_render_effects21`: sprite total 94, formerly 34; particle count remains 7 and unsupported remains 0.

Both sprite deltas are **CLOAK-003's Dark Lord energy cloth**, not new refused item effects. A plain class-4
player with no items creates exactly 60 sprites, no particles and no item programs. Its 6x5 flare grid draws
on each of the fixtures' two saved frames. The two exact totals now include `2 * 6 * 5`; all pre/owner request,
refusal, random-call and particle assertions remain unchanged. The cloth sink and constructor confirm that path.
Environment-off controls preserve the same totals. Probe wall times total 14.94 s.

The affected non-instruction classes pass **23/23 in 11.89 s**. The three unchanged instruction/mutant tests
already passed in the full run and were not repeated. No production C, shared structure, constant or table size
changed, so 6b/8b add no production consumers. No validator check or mutant target changed.

The 16 skips remain explicit: 15 need in-tree mugfx/Ruffle artifacts or tools, and one needs mu-session built.
The installed library exists and its four-start proof below passes; this does not convert tool-dependent skips
into passes. The full private suite was not repeated. Portable affected selection and rule-6c results are below.

## Standard journeys on the installed app

Isolated support/log/option directories, `--no-store`, demo names and the installed network guard. Headless
runs use the installed launcher's `--print-plan`, its mu-client and its bundled GFx library. Every accepted app
run has an exit guard report with **0 connects, 0 inet, 0 lookups and 0 other denials**.

| Proof | Result |
|---|---|
| No-Python GL smoke, without / with audio | pass; PATH=/nonexistent, world reached, Apple M5, zero network |
| Field selected-skill cast | pass; skill_casts 1, skill_refused 0 |
| Kill/drop/Space pickup | pass; kills 1, drops 1, space_picks 1, one pickup request and completed pickup |
| Field recorded audio, music on / volume 9 | 810,028 stereo frames at 44.1 kHz; peak 31,656 = -0.300 dBFS; zero above limit or full-scale samples; RMS 4,679 |
| Hound/HUD, 800 frames | pass; kill/drop 1; 29/29 HUD samples match session, 1100 -> 1077 HP, maximum remains 1100 |
| Headless Warps, Lorencia -> Noria -> Devias | pass; travels 2, plates removed 4, final plates 1, stale 0; 15/15 HUD samples match |
| Windowed Warps, installed launcher, normal clock | pass; 970 frames / 45.02 s, about 21.55 fps including startup; drawable 2560x1600; two travels, zero stale plates; 37/37 HUD samples match |
| Window title / window-only capture | OFFLINE PREVIEW / no server connection; title 25.0 fps at capture; CGWindowID filtered to this launcher's child PID |
| Windleaf headless / windowed | pass; 6/6 and 17/17 HUD samples match 1119/778/1775/284; one 2044 cast, two sounds, 121 effects, maxima 1 rain / 11 impacts / 66 rings, unsupported 0 |
| Offline quest, installed GFx movies/library and same-main mu-world | LorenciaDemo 1/1 passes, accept/kill/complete; no live account or server |

The field session changes only slot 1's join to 179,131 at angle 90. Still placement removes `wander` from the
bundled monster rows. Cast/pickup uses the same 90/91/93, 131/191/251 and 300/340/380/420 frames as 010.
Travel uses M at 100/300 and clicks 122,257 / 122,324 at 131/331; windowed uses 300/331/600/631.
Windleaf copies the bundled slot-2 record/profile into auto-selected slot 1, preserving all values and all five
list entries, joins at 182,128, selects 2044 at 100 and right-clicks 420,490 at 110/111/113. Its windowed rain
capture is frame 125. No temporary fixture is installed or committed.

The first headless harness attempt launched through system nice, which strips the loader variable on macOS.
Its missing guard report was detected and that run is excluded. The corrected Python harness inherits nice 10
and starts mu-client directly with the plan environment. All accepted headless journeys were rerun guarded.
A headless shot-action attempt was also corrected to capture cadence 150 with final frame 151; shot actions are
window-only. These were harness repairs, not app source changes.

## New proofs

| Requested proof | Verdict and evidence |
|---|---|
| (a) Installed GFx first HUD frame | **PASS.** Four fresh starts with MU_GFX_TEST_CLOCK=1 and MU_GFX_SINGLE_BUFFER=1. First world/HUD frame is 57 in each. Four identical raw frame hashes `4357759187e2cfdeb96a99ad559680759e4c0762eada3b7330edd50c9293b222`; opaque whole-image hashes and HUD crops also match. PNG 1 shows all four HUD crops. |
| (b) Visible 0x0f2a counter animation | **PASS.** Atlas, class 1, Hammer15 +9, Lorencia 138,123, particles/other players/NPC/combat/environment off. A same-source control changes only this body's counter to 0. At matching frames 150/151, installed versus frozen counter differs by 39 RGB pixels each, entirely in the mace, bbox 607,317..645,392 and 610,314..648,391. A second control changes only blend light 1 -> 0: 1,494 / 1,528 changed mace pixels. The full run's fixed-pose body-only regression separately has three distinct hashes at counters 0/7/8. Pose movement is not used as the counter proof. PNG 2. |
| (c) Mace sprites/textures and particles | **PASS.** Installed Atlas's 0x0f2a has its red/white bone glows and particles. The same-frame installed particles-off crop isolates them in PNG 3. Same-main mu-world with the same appearance, 152 frames / three saved draws: hero pre-effects 31, refused 0; 11 particles, 24 sprites, unsupported 0; 24 body passes. The full private EFFECTS-022/023/024 tests cover the original mappings/consumers. Counts are from mu-world, pixels from the installed client. |
| (d) NPC/monster cloth | **PASS, Eunice town fixture.** Session joins Lorencia 128,124 with `actor 939 129 125 5 label EuniceDemo`. Compared at frame 150 with APP-REFRESH-010's client, the Eunice region x700..850, y250..420 changes by 4,355 pixels, showing the new two-half cape. Same placement, model, camera and bundled current GFx inputs. PNG 4. Test Area 121 join reaches scene 6 but shows no NPC, reports missing EncTerrain122.plain and renders black except the hero/HUD; it is not an actor proof. |
| (e) Accessory slots 9-14 | **PASS, opt-in fixture.** Installed `--gfx-open inventory,equipment-demo` reports slots/codes 9/6668, 10/6664, 11/6665, 12/6359, 13/6601, 14/6593. All level/excellent/set bits 0, inventory_open 1, item_models_missing 0. The normal hero equipment remains alongside them. PNG 5; the private regression also confirms all six draw, not merely appear in records. |

All controls are offline native comparisons, not original-client pixel equivalence. Counter and zero-light
controls are scratch-linked clients, not installed replacements. Test clock is scoped to the four-start proof;
it remains unset for normal journeys, windowed runs and ordinary app launches.

### Retained screenshots

Local only: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-011/proofs/`.
Six PNGs, 1,125,427 bytes total, at most 760 pixels wide. Raw installed captures were checked opaque before
cropping/quantizing; final PNGs have no transparency. Only window/framebuffer pixels, short evidence labels
and demo names appear. All six final images were reopened and visually inspected.

| File | Contents |
|---|---|
| `1-gfx-frame-zero.png` | four first-HUD-frame crops, same test clock |
| `2-0f2a-counter-animation.png` | installed vs frozen-counter controls at frames 150/151, 8x RGB differences |
| `3-mace-effects.png` | installed Atlas and particles/sprites on/off crops |
| `4-eunice-cloth.png` | prior app, installed Eunice cape, 4x difference |
| `5-accessories-9-14.png` | installed inventory, enlarged equipment slots and exact fixture codes |
| `6-window-travel-windleaf.png` | real window with OFFLINE PREVIEW/fps title, plus windowed 2044 rain |

## Checks and wall times

No full lane gate. Builds use nice 10 and at most -j4; test workers 2. A two-minute resource pause followed
load >14; subsequent checks were below load 14 and above 25% memory free. Disk stayed over 150 GB free.
Two brief command overlaps occurred when a still-running session was mistaken for completion: the initial
build tail with suite startup and a 0.45-second make with the repair-test tail. No second full run was started.

| Step | Result | Wall |
|---|---|---:|
| Rollback zip / archive check | 66 entries, valid | 0.66 s / <1 s |
| Initial root build | pass | 33.33 s |
| Full private native/tests, root, jobs 2 | 1,038 tests; three fixture failures, 16 skips | 1,354.85 s |
| Three exact reproductions / diagnostic controls / repaired classes | 3 fail / causes isolated / 23 pass | 5.01 / 14.94 / 11.89 s |
| Detached final root / world-client / app build | pass | 0.45 / 0.24 / 2.33 s |
| Native Data manifest / install + signature + bundle | pass / pass | 0.43 / 0.33 s |
| Installed smoke without / with audio | pass, zero network | 11.10 / 11.17 s |
| Guarded field+audio / Hound / travel | pass | 10.66 / 13.53 / 11.89 s |
| Four installed frame-zero starts | four identical | 6.56 + 6.53 + 6.60 + 6.60 s |
| Zero-light / frozen-counter control builds | pass | 3.11 / 3.15 s |
| Atlas installed / zero-light / frozen-counter final captures | pass | 6.44 / 6.59 / 6.83 s |
| Mace installed / same-main world report | pass | 7.01 / 1.68 s |
| Eunice installed / old-client control / Test Area 121 join | pass / pass / no visible NPC | 6.70 / 7.46 / 5.30 s |
| Installed accessories with telemetry | six accessories, no missing model | 8.36 s |
| Window capture helper build | pass | 0.49 s |
| Windowed travel / Windleaf headless / windowed | pass | 46.54 / 8.35 / 26.40 s |
| Quest with installed GFx library/movies | 1/1 | 4.45 s |
| Validator affected selection | 0/214 rows | 20.77 s |
| Portable affected suites, 12 selected work items | 369 tests: 304 passed, 65 expected skips, 0 failures/errors | 117.46 s including selection; 65.4 s execution |
| Rule-6c four documentation consumers, private env | 36/36 passed, 0 skips | 55.54 s |
| Checkpoint audit / final staged audit | 2,133 files, 0 rejected each | 17.43 s checkpoint; final wall in PR |

Steward validators: none. Selection at `a5edc515` plus final documentation edits selects 0/214 rows.
This is a test-fixture/documentation PR. No compiled validator input changed; no mutants are requested.
The 23 affected non-instruction tests and the full run's existing instruction tests cover the test repairs.

## Follow-ups and limits

- The 270 unadmitted bodies and prior pose/owner/buff/record domains remain. No character-power feature changed.
- Hammer14's exact `up01 ` versus `up01` refusal remains; no guessed bone normalization. Ferea clouds/28 remains.
- Eunice is an authored temporary placement. No eligible CLOAK-004 actor was added to the shipped demo.
  Ordinary town NPCs do not select these cloths. The Test Area 121 installed session is not an actor proof.
- The six accessory records are appearance-only and opt-in; ordinary app launch does not equip them.
- Missing placements/data, Arca War worlds, native wind/process-rand differences, protected/opaque components,
  live-service boundaries and strict performance acceptance remain. Short window timings are not a performance
  equivalence claim. No Ferea screenshot is claimed by this refresh; its emitter is included and privately tested.
- Fifteen in-tree GFx/Ruffle tool checks and the mu-session-dependent check remain skipped, as recorded above.
- No original client/launcher execution, live reads, account work, game networking, protection analysis or memory
  writes. No owner password was read, printed or stored. Wine play/staged apps and prefixes stayed untouched.

## Cleanup and delivery

Keep only rollback/app-refresh-011's zip, settings copy and six PNGs from this lane. Keep older rollbacks.
After the ready line, remove lane scratch, raw frames, WAVs, temporary fixture/control clients, retired app,
helpers, private reports and all worktree build outputs. Shared inputs, original-side validator caches and both
GFx artifacts stay. Keep the source worktree and branch until the steward merges. No push after ready-prs.txt.
