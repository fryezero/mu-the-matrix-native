# APP-REFRESH-012

Implementation handoff, 2026-11-11. GPT-6.1 Sol. Branch `codex/app-refresh-012`.
Offline Native Preview refresh and documentation. No production code or export input changed.

## WIP

Done: rollback verified; one full private suite passes; detached main `d4af71dd` built and installed;
strict signature, bundle, manifest and unchanged-settings checks pass. Installed smoke without/with audio,
field cast/kill/drop/pickup, Hound/HUD, headless/windowed travel and Windleaf headless/windowed pass.
Left: offline quest; seven requested new feature categories; proof inspection; final documentation,
selective checks, PR, steward entry and cleanup.
Next step: when load is at most 14 and memory free at least 25%, run scratch/quest.py, then newproofs.py modes
select, sound, stab, actor, muun, kanturu, bc and ferea. Inspect and explain every result before delivery.
No ready entry exists. Checkpoint every 20-30 minutes. Owner's latest instruction restores the deadline:
stop all work by 02:30 on 2026-11-12; if not PR-ready at 02:15, commit/push WIP before stopping.
The installed bundle is fully replaced and smoke-checked; no swap is in progress.

Scratch/harness: `~/Documents/MTM/mu-mac-tools/native/scratch/app-refresh-012/`.

## What the installed app now has

Installed `MUNativeCommit`: **`d4af71dd`**, full SHA `d4af71dddb4573bf0cb21d8a27908971121013b4`.
Includes all merged code since APP-REFRESH-011's `54a53e1a`:

- ACTORS-001/002: skeleton/equipment recipes and nine later whole-body actor subtypes.
- ITEMS-002X: twenty additional admitted bodies, 1,424/1,674, leaving 250.
- AUDIO-002G and CHARSEL-ITEMS-001: accepted-release button sound 25 and selection equipment levels/glows.
- EFFECTS-025/027: Ferea clouds/28, two bow pairs, exact Hammer14 missing-name state and base-DK Death Stab trails.
- WORLDS-INNER-001: Kanturu inline meshes/effects and Blood Castle candle flares.
- MUUN-VISUAL-001: opt-in fixture body, pose/follow and sixteen verified attachments.

Feature-specific installed proofs are pending below. No canonical placement or character values changed.

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
| `proofs/` | final small PNGs pending |

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
| Windleaf headless/windowed | pass, HUD 4/4 and 13/13 at 1119/778/1775/284; one 2044 cast, two sounds, 121 effects; maxima 1 rain / 11 impacts / 66 rings; unsupported 0 |
| Offline quest | pending |

The field session changes only slot 1's join to 179,131 at angle 90. Still placement removes wander only.
Cast/kill/pickup and travel scripts use APP-REFRESH-011's exact frames/coordinates. Windleaf copies the bundled
slot-2 record/profile into reliable auto-selected slot 1, preserving all five list entries and every value,
joins 182,128, selects 2044 at 100 and casts at 420,490 at 110/111/113. Windowed rain saves at frame 125.
No temporary fixture is installed or committed. Busy-host timings are journey observations, not performance acceptance.

## New proofs

Pending: character-select levels/excellent glows; button sound 25 on server/character select; DK Death Stab;
Kanturu 37 inline draws and Blood Castle candles; fixture Muun; actor subtype; Ferea clouds.
Keep only small window/framebuffer captures, demo names, and explicit fixture/env-switch limits.

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
| Installed smoke | pass | 13.543 |
| Installed smoke-audio | pass | 10.310 |
| Installed field | pass | 21.650 |
| Installed hound | pass | 22.832 |
| Installed travel | pass | 18.421 |
| Installed window-travel | pass | 47.756 |
| Installed wind | pass | 13.597 |
| Installed wind-window | pass | 27.580 |

Steward validators: none. No compiled validator input changed. Final documentation-consumer checks and audit pending.

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
