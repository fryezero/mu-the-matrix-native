# INTEGRATION-GREEN-001

Verification lane. Branch `codex/integration-green-001`, resumed against main `c769a5d`.
The installed app's Native Data setup identifies the game root. Its `main.exe` matches
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.

## Changes and provenance

- Character-create already runs 300 cases on current main. Confirmed 4,368 cases, zero mismatches,
  all 6/6 mutants detected, including the code-page mutant. No further charsel change.
- Recovered the original capture-04 and model manifest in the older analysis directory. All original
  capture pins, including the full section-3 pin for objects, can be satisfied without a live read.
- Effects and tree validators pin only the exact 76,288 initialized bytes they map. A range-only file
  works; changes inside that range and truncation fail before emulation. The fresh guest range differs
  and still fails. Whole capture versus range-only comparison reports agree in every behavior result.
- Re-pinned the model manifest after two byte-identical strict scans. Direct comparison with the old
  manifest found only three export annotations and 17 improved error strings, with identical paths,
  ordering, source hashes, decoded hashes, statuses and model counts.

Full old/new digests, causes, methods and scanner identity are in
[the finding](../research/private-integration-inputs.md). No private bytes or manifests are committed.

## Focused checks

Five manifest validators pass, zero skipped/failed:

| Validator | Coverage | Result |
|---|---|---|
| charcreate | 4,368 cases, 6 mutants | zero mismatches, 6/6 caught |
| effects | 80 cases, 2,342 frames, 46,196 vertices | zero mismatches |
| effect_tree | 110 cases, 1,967 frames, 66,056 vertices | zero mismatches |
| model_codec | 4,048 synthetic cases, 180 v12 files, 3,176,971 payload bytes | zero mismatches |
| client_lea_decode | 1,152 scalar cases, 11,583 v15 files | zero mismatches |

The v15 corpus is compared with the independent native reader. The corpus comparison does not execute
original AVX instructions. Three existing-snapshot checks pass, without making new captures. Effects
unittest suite: 21 passed, zero skipped. Pin and manifest portable checks: 16 + 17 passed. Two input-boundary
regressions exercise both validators and verify rejection before emulation.

## Before and after

Verified source checkpoint `99d0caf`, merged with main `c769a5d`. Final commits add this summary only.

| Run | Passed | Skipped | Failed/error | Boundary |
|---|---:|---:|---:|---|
| Historical 2026-10-24 | 35/38 directories | See historical handoff | See historical handoff | Before charcreate repair and recovered inputs |
| Fresh baseline, `tests/` only at `8eac05c` | 140 | 0 | 10 | ENOSPC invalidated this baseline; remaining directories stopped |
| Installed export baseline at `8eac05c` | 8 | 0 | 1 | Stale 17-texture expectation |
| Final private-enabled full run, 38/38 directories | 1,455 | 24 | 0 | Three affected directories rerun in full after harness fixes |
| Final available export group | 11 | 0 | 0 | Covers nine skips above; two other test IDs rerun with exports |
| Final unique test coverage | 1,464 | 15 | 0 | 1,479 unique test IDs, no double counting |
| Repeated portable Mac gate | 1,298 | 181 | 0 | 1,479 tests; private comparisons opt out in this separate gate |

The full private run found three harness errors: the audio adapter omitted the new Vulcanus/Santa handlers,
and particle/joint tests called the removed evidence helper. Full reruns passed: native 672 tests with 24 skips,
particles 21/21, joints 11/11. The export group initially exposed the world-specific smoke slot and personal
audio preferences; after explicit test-state fixes the complete 11-test group passed. Checks and mutant
requirements were preserved. The audio adapter separately passed 5,528 original-instruction cases, zero
mismatches, all 18/18 compiled mutants. The generation-order regression passes for three core consumers.

The exact `bash scripts/local-macos-ci.sh` gate passed twice. The final repeat used committed source `99d0caf`:
38 unittest directories, seven fixture scenarios passed, viewer and read-only reader builds passed, audit
1,376 staged files with zero rejected. Fixture metadata reports the four untracked local-input symlinks as
`dirty`; authored source had no uncommitted changes. No hosted workflow was dispatched.

## Private directory counts

These are unittest methods, including portable methods run with integration enabled, rather than x86 case counts.
The nine export-covered skips remain shown in the native row so the complete-run totals stay inspectable.

| Directory | Passed | Skipped | Failed |
|---|---:|---:|---:|
| `tests` | 152 | 0 | 0 |
| `native/tests` | 648 | 24 | 0 |
| `reconstructed/boot` | 5 | 0 | 0 |
| `asset-recovery` | 12 | 0 | 0 |
| `model-recovery` | 36 | 0 | 0 |
| `reconstructed/client-memory` | 10 | 0 | 0 |
| `reconstructed/record-math` | 23 | 0 | 0 |
| `reconstructed/model-codec` | 58 | 0 | 0 |
| `reconstructed/camera` | 12 | 0 | 0 |
| `reconstructed/actors` | 16 | 0 | 0 |
| `reconstructed/audio` | 33 | 0 | 0 |
| `reconstructed/data` | 13 | 0 | 0 |
| `reconstructed/effects` | 21 | 0 | 0 |
| `reconstructed/path` | 30 | 0 | 0 |
| `reconstructed/ui` | 26 | 0 | 0 |
| `reconstructed/charsel` | 28 | 0 | 0 |
| `reconstructed/movement` | 13 | 0 | 0 |
| `reconstructed/hud` | 19 | 0 | 0 |
| `reconstructed/scene` | 11 | 0 | 0 |
| `reconstructed/combat` | 38 | 0 | 0 |
| `reconstructed/environment` | 11 | 0 | 0 |
| `reconstructed/particles` | 21 | 0 | 0 |
| `reconstructed/items` | 12 | 0 | 0 |
| `reconstructed/joints` | 11 | 0 | 0 |
| `reconstructed/names` | 9 | 0 | 0 |
| `reconstructed/npc` | 12 | 0 | 0 |
| `reconstructed/objects` | 35 | 0 | 0 |
| `reconstructed/mix` | 18 | 0 | 0 |
| `reconstructed/helpers` | 13 | 0 | 0 |
| `reconstructed/raven` | 6 | 0 | 0 |
| `reconstructed/pets` | 7 | 0 | 0 |
| `reconstructed/quest` | 10 | 0 | 0 |
| `reconstructed/price` | 5 | 0 | 0 |
| `reconstructed/skill` | 16 | 0 | 0 |
| `reconstructed/map` | 11 | 0 | 0 |
| `reconstructed/social` | 6 | 0 | 0 |
| `reconstructed/progress` | 14 | 0 | 0 |
| `reconstructed/renderchar` | 34 | 0 | 0 |

## Remaining skips

All nine skips for available lang/object exports were executed successfully in the separate export run.
The remaining 15 tests need the optional compiled mugfx/Ruffle runtime, its pinned checkout, or converted
names/quest movies. No missing core capture, hash mismatch, missed mutant or comparison failure is called a skip.

- `test_native_gfx.Synthetic.test_ruffle_renders_converted_movie_and_bridge_round_trip`: 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)'
- `test_native_gfx2.LayerWithRuffle.test_layer_opens_synthetic_movies`: 'native/gfx/mugfx not built'
- `test_native_gfx2.PatchSeries.test_series_applies_to_the_pinned_checkout`: 'no pinned Ruffle checkout (native/gfx/fetch-ruffle.sh)'
- `test_native_gfx2.RuffleExtensions.test_mouse_extensions`: 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)'
- `test_native_gfx2.RuffleExtensions.test_selection_capabilities_and_no_advance`: 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)'
- `test_native_gfx2.RuffleExtensions.test_text_auto_size_and_vertical_align_layout`: 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)'
- `test_native_gfx2.RuffleExtensions.test_text_field_extensions_and_keyboard`: 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)'
- `test_native_gfx2.RuffleExtensions.test_window_view_and_shared_surface`: 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)'
- `test_native_gfx3.InstalledBaseMovie.test_client_base_movie_runs`: 'needs MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, mugfx'
- `test_native_gfx3.RuffleLoadingAndImages.test_double_buffered_surface`: 'native/gfx/mugfx not built'
- `test_native_gfx3.RuffleLoadingAndImages.test_host_image_shared_with_the_movie`: 'native/gfx/mugfx not built'
- `test_native_gfx3.RuffleLoadingAndImages.test_ime_preedit`: 'native/gfx/mugfx not built'
- `test_native_gfx3.RuffleLoadingAndImages.test_load_order_loadclip_and_load_bitmap_from_lib`: 'native/gfx/mugfx not built'
- `test_native_names.GfxRoute.test_the_movie_gets_the_handler_calls`: 'private: MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NAMES_GFX_MOVIES, libmugfx, mu-world'
- `test_native_quest.LorenciaDemo.test_accept_kill_complete`: 'needs MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_LANG_DIR (with quests.tsv), MU_GFX_LIB and MU_QUEST_MOVIES (converted movies)'

## Inputs and cleanup

No new input needs to survive this lane. After merge, the owner cleanup rule removes the entire
`scratch/integration-green-001/`, any matching render directory, owned temporary files, worktree builds,
worktree and local branch. The PR and these committed summaries retain the verification counts; local logs
are intentionally not retained. Duplicate scan outputs were summarized and removed before completion.

Future private runs use these pre-existing inputs, which this lane does not delete or change:

- The installed game named by Native Data `setup.json`, as `MU_GAME_ROOT`; its target digest is above.
- `~/Documents/MTM/mu-the-matrix-native/evidence/`, as `MU_EVIDENCE_DIR`, for the pins in `scripts/pins.py`.
- `~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`, as `MU_SECTION3`.
  Set `MU_EFFECTS_SECTION3` to this same full capture. Its verified prefix replaces the disposable range-only file.
- `~/Documents/MTM/mu-the-matrix-native/model-recovery/verified-local/manifest.json`, as `MU_V14_MANIFEST`.
- `~/Documents/MTM/main-exe-study/evidence/model-edge/diagnostics.json`, as `MU_EDGE_DIAGNOSTICS`.
- The existing `evidence/x86-guest-sec3-25/main-01ced000.bin`, as `MU_PATH_DIRECTIONS`.
- `~/Documents/MTM/mu-mac-tools/native/scratch/`, as `MU_SNAPSHOT_DIR`, with the existing lang3/lang4,
  quest2/skill2/skill4 snapshots, object plaintexts, character-select dumps and light/login dumps. For the direct
  snapshot tests, set `MU_LANG_SNAPSHOT=.../lang/live/lang3.bin`, `MU_QUEST_SNAPSHOT=.../lang/live/lang4.bin`,
  `MU_LIGHT_SNAPSHOT=.../light/live/dumps/login-a.light`, `MU_LIGHT_OBJECTS=.../objects/live/plain/EncTerrain95.plain`,
  `MU_CHARSEL_DUMP_DIR=.../charsel2/live/dumps`, `MU_LOGIN_DUMP_DIR=.../light/live/dumps`, and
  `MU_OBJECTS_DUMP_DIR=.../objects/live/dumps`, where `...` means `MU_SNAPSHOT_DIR`.

With the repo Python and those inputs, run `MU_RECOVERY_INTEGRATION=1 make test`. Run the export-specific
classes separately with `MU_LANG_DIR=.../lang`, `MU_OBJECTS_PLAIN_DIR=.../objects/live/plain` and
`MU_AUDIO_TABLE=.../audio/tables/audio-tables.tsv`. The verified group comprises PrivateTables, PrivateTravel,
LiveReadPrivateTests, PrivateCharselTests, InstalledTormentaJoints, InstalledLorenciaFires, Installed skill,
InstalledLoginSceneTests and NativeAudioTests.test_private_installed_audio. These variables stay unset for
the portable gate so private exports cannot contaminate synthetic tests.

This establishes offline input/validator compatibility. Gameplay fidelity, live service, new captures,
original AVX execution and native Windows evidence do not advance in this lane.
