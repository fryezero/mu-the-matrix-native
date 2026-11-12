# APP-REFRESH-012

Implementation handoff, 2026-11-11. GPT-6.1 Sol. Branch `codex/app-refresh-012`.
Offline Native Preview refresh and documentation. No production code or export input changed.

## Delivery status

PR-ready, docs only. All standard journeys and all seven requested new feature categories pass within the
fixture/env/preference limits below. No production regression found. Full private suite, final rule-6c tests,
validator selection and repository audit pass. Source unchanged from detached main `d4af71dd`.
Checkpoint heads `cc792faa` and `1cdb9b8a` preserved rollback and installed-journey WIP before final delivery.
All final pushes precede the ready-prs entry; the merge steward merges. No source/build input is left to repair.

## What the installed app now has

Installed `MUNativeCommit`: **`d4af71dd`**, full SHA `d4af71dddb4573bf0cb21d8a27908971121013b4`.
Includes all merged code since APP-REFRESH-011's `54a53e1a`:

- ACTORS-001/002: skeleton/equipment recipes and nine later whole-body actor subtypes.
- ITEMS-002X: twenty additional admitted bodies, 1,424/1,674, leaving 250.
- AUDIO-002G and CHARSEL-ITEMS-001: accepted-release button sound 25 and selection equipment levels/glows.
- EFFECTS-025/027: Ferea clouds/28, two bow pairs, exact Hammer14 missing-name state and base-DK Death Stab trails.
- WORLDS-INNER-001: Kanturu inline meshes/effects and Blood Castle candle flares.
- MUUN-VISUAL-001: opt-in fixture body, pose/follow and sixteen verified attachments.

All requested feature-specific installed proofs pass below. No canonical placement or character values changed.

## Installation and rollback

Order: rollback, root build and full private suite, detached-main root/world/client/app builds,
manifest/process checks, guarded bundle swap, installed journeys. Main was still `d4af71dd` when fetched
before installation. No Preview or mu-client was running. No owner process was killed.
Only `~/Applications/Mu The Matrix Native Preview.app` was replaced. The Wine apps/prefix were untouched.

From the repository root:

```sh
nice -n 10 make -j4
nice -n 10 make -C native -j4 world client
nice -n 10 make -C native/app -j4 MUGFX_LIB="$HOME/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib"
```

Raw GFx SHA-256: `eaf39b722e34e6d6f2eae34378bbac67d5004d2b4a9be8de005df3edd26a1645`.
Installed GFx after rpath fixup/signing: `8a20a369a93e211fe6e3431b54bc3d3fd74e3c1c8d1c5ba647c70fbe3d6ed70e`.
Installed mu-client: `dec5a1fe81a138c43ffcef366c4960a724ad9749304aaf0d566ef19c319faedc`.
Same-main rebuilt mu-world: `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.

The old bundle was moved to lane scratch, then the new one copied with ditto, with restore on error.
`codesign --verify --deep --strict` and installed `--check-bundle` pass. Settings stay byte-identical.

Rollback: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-012/`.

| File | Verification |
|---|---|
| `Mu-The-Matrix-Native-Preview-APP-REFRESH-011-54a53e1a.app.zip` | 11,107,185 bytes, 66 entries, `unzip -t` passes; SHA-256 `77c7b9070cc81ab8fe1b54f91f39a0d3226806b0611fb56cb9310f8db4c8b663` |
| `settings.json.before` | original APP-REFRESH-006 selection; unchanged |
| `proofs/` | eight opaque PNGs and one UI-click WAV, 3,754,293 bytes total, PNG width at most 760 |

To restore, first wait until Preview is closed. Move the current app aside, then `ditto -x -k` the archive
into `~/Applications`. Its top-level entry is the app. Restore settings only if they subsequently changed.
Keep all older rollbacks.

## Native Data kept

`~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-006/Native Data` is unchanged.
The `54a53e1a..d4af71dd` export-input diff is empty over scripts/build_native_data_export.py,
live_lang_to_plain.py, live_lang_filters.py, live_effect_table_to_plain.py, live_objects_to_plain.py,
extract_audio_tables.py, native_data_manifest.py, pins.py, native/data, native/gfx and native/app.
The bundled manifest/launch-plan check passes. No export, setup, canonical-data write or selection change.

## Full private native/tests

From the repository root, once at `d4af71dd`:

```sh
. ~/Documents/MTM/mu-mac-tools/native/private-env.sh
MU_GATE_JOBS=2 nice -n 10 tools/python/bin/python scripts/run_test_suites.py native/tests
```

The refresh exception to 8d applies: **162 work items, 1,069 tests, 1,054 passed, 15 skipped,
zero failures/errors, 1,468.1 s wall**. No assertion, fixture or production repair was needed.
All fifteen skips require unavailable in-tree mugfx/Ruffle artifacts or tools. Installed Ruffle proofs
are separate. The full suite was not repeated.

## Standard journeys on the installed app

Isolated support/log/options folders, `--no-store`, demo names and the bundled network guard.
Headless runs use the installed launcher's `--print-plan` and its installed mu-client/library.
Every completed app journey has an exit guard report with zero inet, other, connect or lookup denials.

| Journey | Result |
|---|---|
| No-Python GL smoke without/with audio | pass, PATH=/nonexistent, world reached, Apple M5 |
| Field selected-skill cast | pass, one cast, zero skill refusals |
| Kill/drop/Space pickup | pass, one each; one request and completed pickup |
| Field recorded audio, music on, volume 9 | 810,028 stereo frames / 44.1 kHz; peak 31,656, zero above limiter or full scale; RMS 4,679 |
| Hound/HUD, 800 frames | pass, kill/drop 1; 29/29 HUD samples match; HP 1100 -> 1077, maximum 1100 |
| Headless Warps | pass, two travels 0 -> 3 -> 2, four plates removed, final plate 1, stale 0; HUD 15/15 |
| Windowed Warps, 45 s | pass, 692 frames / 45.01 s, drawable 2560x1600, two travels, stale 0; HUD 30/30 |
| Window title/capture | window-only CGWindowID capture, filtered to this launcher's child PID; OFFLINE PREVIEW / no server connection / 25.0 fps diagnostic title |
| Windleaf headless/windowed | pass, HUD 4/4 and 13/13 at 1119/778/1775/284; one 2044 cast, two sound decisions, 121 effects; maxima 1 rain / 11 impacts / 66 rings; unsupported 0 |
| Offline quest, installed movies/library and same-main mu-world | pass, LorenciaDemo 1/1, accept/kill/complete, progress 3, active empty and undecodable 0; guarded |

The field session changes only slot 1's join to 179,131 at angle 90. Still placement removes wander only.
Cast/kill/pickup and travel scripts use APP-REFRESH-011's exact frames/coordinates. Windleaf copies the bundled
slot-2 record/profile into reliable auto-selected slot 1, preserving all five list entries and every value,
joins 182,128, selects 2044 at 100 and casts at 420,490 at 110/111/113. Windowed rain saves at frame 125.
No temporary fixture is installed or committed. Busy-host timings are journey observations, not performance acceptance.

## New proofs

All seven requested feature categories pass. WORLDS-INNER has two proofs. These are offline native controls,
not original-client pixel equivalence. The installed bundle is always the unmodified detached-main build.
The rollback client is APP-REFRESH-011 from the verified archive, SHA-256
`645b63e5247f5e2e261347cb7b4802d44d7d63d66d0908bfbcb8539f33dd737f`, distinct from the installed client hash above.
Controls use matching virtual frames, fixtures and its own matching GFx library. There is no default identity
sweep in this packaging lane. Every accepted app/control run has an exit network-guard report with zero calls
denied. All 32 recorded exit reports, including the actor-refusal control, are zero-attempt.

| Requested feature | Installed evidence and limit |
|---|---|
| Character-select levels/excellent | Ironclad with only Cookery Short Sword, frame 110, fixed GFx test clock/single buffer. Level 0 -> +9 changes 1,583 RGB pixels; +9 -> +9 excellent changes 1,809. Both bounds 416,415..511,474, the sword only. Appearance-only temporary records; all five entries retained. PNG 1. |
| Button sound 25 | Three accepted CButton releases: two server-group/server clicks and character-select Create. All three log original handler `0x009867e3`, site `0x0098689e`, id 25, loop 0 and loaded playback result 1. Owner Data/Sound/Option.ini has Effect volume 0, so ordinary captured PCM is correctly silent. An isolated game-root fixture enables only Effect, uses read-only asset symlinks and an APFS clone of the pinned main.exe, and produces 63,900 nonzero signed-16 samples, peak 12,158. Owner audio options hash stays identical. The existing keyboard Esc cue also plays id 25 after these three CButton cues. WAV 2. No FMOD/output parity claim. |
| Death Stab | Installed DK demo selects key 6 / skill 43 at 100, right-clicks at 690,238 on 111/113. Frame 120 visibly adds the long trails and near-caster curls absent in the prior app. One accepted UI cast, zero skill refusals, unsupported 0; the held action's internal combat count is 3 and effects_created 30, not the separate one-cast validator's 189-request count. PNG 3. Base-DK authored weapon/bone context only. |
| Actor subtype | `actor 372 129 125 5 label DemoActor`, hero 128,124, Lorencia. The Elite Skull Soldier whole body is visible at frame 150. Prior app refuses class 372 and returns to selection, so no empty-body same-scene comparison is claimed. PNG 4. Temporary placement only; no default spawn changes. |
| Muun | Same installed client, fixture off/on `MU_MUUN_FIXTURE=363`, Lorencia 128,124, frame 150. Model and dandelion attachment are visible; 3,228 pixels change, bounds 746,267..819,411. PNG 5. Full private host covers all fifteen codes/sixteen attachments; this installed proof shows one code. Fixture-only selection/follow, no inventory/bonus authority. |
| Kanturu 37 inline draw | Ordinary view at 19,218 is supplemented by one unchanged canonical type `0x55` record, position 1658.008,22387.887,230, angle 34, scale 1.96; hero 13,220, frame 150. The added mesh-3 Chrome gem highlights are visibly isolated from the base arch. Whole-frame RGB delta 5,377 includes small HUD timing pixels; retained proof crops the world and labels an x8 difference. PNG 6. Authored one-record layout, not a canonical placement edit. |
| Blood Castle candles | Two-object authored layout, types 0x0b/0x0d at 13000,12800,300 and 12900,12600,300, scale 1; hero 128,128, world 11, frame 90. Seven point flares and the single named-bone flare appear against prior app. Whole-frame delta 9,341; retained world crop excludes HUD timing pixels and labels x8 difference. PNG 7. Raising the fixture objects avoids ground/hero occlusion. The first three-object z50 view isolated well fire only and is not the candle proof. |
| Ferea clouds/28 | One unchanged canonical type-9 emitter at 23201.953,15084.603,388.504, scale 1, in a temporary one-record layout; hero 230,148, frame 240. A dim yellow cloud region is absent from prior app, visible in ordinary pixels and the labeled x8 difference. Whole-frame delta 144,214, bounds 580,0..1135,462; a few item pixels also change with random phase. PNG 8. The ordinary 236,152 view also ran but its coupled emitter changes are not used as an isolated cloud proof. |

The fixed test clock is scoped to selection controls. All standard/windowed journeys use the normal clock.
No temporary fixture is installed or committed. Missing/unavailable event state, general Death Stab classes,
Muun auxiliary behavior and ordinary spawnability retain the owning lanes' limits.

### Retained local proof files

`~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-012/proofs/`, never committed.
Eight opaque indexed PNGs, at most 760 pixels wide, and the 6.424-second stereo PCM UI-click WAV.
Total 3,754,293 bytes. Raw headless sources are opaque before crop/quantization; final PNGs reopen opaque.
All eight final images were reopened and visually inspected together, after inspecting their source frames.
Difference panels explicitly label x8 brightness. They preserve native RGB differences, with no AI imagery.

| File | Contents |
|---|---|
| `1-selection-levels.png` | same-frame level 0 / +9 / +9 excellent |
| `2-button-sound-25.wav` | audible UI fixture, music/environment muted, three CButton clicks and existing Esc cue |
| `3-death-stab.png` | prior/current trails and x8 difference |
| `4-actor-372.png` | admitted whole body; prior refusal stated |
| `5-muun-fixture.png` | off/on model and attachment |
| `6-kanturu.png` | isolated Chrome gem pass and x8 difference |
| `7-blood-castle.png` | raised candle/flare fixture and x8 difference |
| `8-ferea.png` | isolated cloud emitter and x8 difference |
| `9-window-travel-windleaf.png` | actual window/title and windowed rain frame 125 |

Harness corrections: quest.py initially lacked the repository root on sys.path; correcting it runs the
existing 1/1 test. The first sound fixture used a main.exe symlink, correctly refused by the manifest hash
policy; an APFS clone satisfies that unchanged check. Resource-guard stops occur before client launch.
No product source, assertion or acceptance threshold was changed for any of these corrections.

## Checks and wall times

One full private suite, no full lane gate. Nice 10, make at most four jobs, test workers two.
Load above 14 caused required pauses. Resource-guard stops before launches are excluded, not app failures.
Memory and disk remained above their limits.

| Check | Result | Wall s |
|---|---|---:|
| Initial root build | pass, timing not captured | |
| Detached root/world-client/real-GFx app builds | pass | 0.42 / 0.21 / 2.06 |
| Full private native/tests | 1,054 passed, 15 skipped, zero failures/errors | 1468.1 |
| Manifest/plan | pass | 2.095 |
| Install/signature/bundle/settings | pass | 0.242 |
| First staged audit | 2,184 files, zero rejected | 21.68 |
| Installed/control smoke | pass | 13.543 |
| Installed/control smoke-audio | pass | 10.310 |
| Installed/control field | pass | 21.650 |
| Installed/control hound | pass | 22.832 |
| Installed/control travel | pass | 18.421 |
| Installed/control window-travel | pass | 47.756 |
| Installed/control wind | pass | 13.597 |
| Installed/control wind-window | pass | 27.580 |
| Installed/control level0 | pass | 4.212 |
| Installed/control level9 | pass | 3.830 |
| Installed/control excellent9 | pass | 4.483 |
| Installed/control sound | delivery passes, owner Effect volume 0 | 5.198 |
| Installed/control stab | pass | 8.515 |
| Installed/control actor | pass | 10.930 |
| Installed/control sound-audible | pass | 5.145 |
| Installed/control muun | pass | 8.855 |
| Installed/control muun-off | pass | 8.013 |
| Installed/control kanturu | pass | 10.578 |
| Installed/control bc | pass | 8.673 |
| Installed/control ferea | pass | 16.990 |
| Installed/control stab-before | pass | 10.809 |
| Installed/control actor-before | expected class refusal, no same-scene frame | 12.285 |
| Installed/control kanturu-before | pass | 12.834 |
| Installed/control bc-before | pass | 8.618 |
| Installed/control ferea-before | pass | 11.622 |
| Installed/control bc-candles | pass | 7.432 |
| Installed/control ferea-cloud | pass | 9.515 |
| Installed/control bc-candles-before | pass | 8.043 |
| Installed/control ferea-cloud-before | pass | 9.537 |
| Installed/control kanturu-inline | pass | 5.799 |
| Installed/control kanturu-inline-before | pass | 5.978 |
| Quest with installed movies/library | 1/1, zero network | 5.479 |
| Second checkpoint audit | 2,184 files, zero rejected | 21.42 |
| Rule-6c documentation consumers, canonical private env | 36/36 passed, zero skips | 67.51 |
| Affected validator selection | 0/222 rows | 22.81 |
| Staged documentation audit | 2,185 files, zero rejected | 16.93 |
| Final metadata-only audit recheck | recorded in PR before push | |

Steward validators: none. The post-build selection is 0/222 manifest rows at the final documentation tree.
No compiled validator input, runtime symbol, struct or table size changed, so 6b/8b add no consumers or mutants.
TEST BUDGET 6c applies: tests.test_world_captures_2, tests.test_repository_policy,
native.tests.test_native_item_textures and native.tests.test_native_data_manifest pass with private-env.sh.
No second full private run, unrelated validator run or full lane gate was needed.

## Follow-ups and limits

No production regression found in completed checks. Unadmitted bodies, actor exclusions, unavailable world
placements, original temporal/pixel equivalence, authoritative event/state and online services remain outside
this refresh. Fixtures do not establish ordinary spawns, account equipment, Muun selection or bonuses.
No protection/anti-cheat work, original-client execution, live reads, network/login/server-state work,
character-power feature, memory writes or owner-password access occurred.

## Cleanup and delivery

Keep the rollback archive, settings copy and final small PNGs. After final pushes and the ready entry,
remove disposable lane scratch/renders, raw frames, WAVs, helpers, retired bundle and worktree builds/reports.
Keep the source worktree/branch until the steward merges, as in APP-REFRESH-011. Shared caches/inputs/GFx artifacts stay.
No push after the ready-prs line. The merge steward owns merging.
