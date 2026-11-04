# NATIVE-DATA-MANIFEST-001

One current, manifest-bearing Native Data export set, with RENDER-WORLDS-AFTER5's `mapanim.tsv` as a recorded lang
step. This prepares APP-REFRESH-004 (the next reinstall of the Native Preview app).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/native-data-manifest-001`, branch
  `claude/native-data-manifest-001`, from origin/main `5cb6fa6d`, merged with `1e247ae9` (#285 RENDER-WORLDS-AFTER5).
- Offline only. No live game, launcher, network, login or protection work. The owner's installed app, its
  `settings.json` and its Native Data folders were not touched.

## Why

INTEGRATION-GREEN-002 rows 6 and 7 (class (c), missing local input):
- The shared exports `scratch/lang`, `scratch/objects/live/plain` and `scratch/audio/tables` have no Native Data
  manifest. App setup refuses them by design (DATA-ACQ-004). The private app smoke passed only with
  `MU_NATIVE_SCRATCH=scratch/app-refresh-003/export`.
- `scratch/audio/tables/audio-tables.tsv` dates from 2026-10-17. That is before AUDIO-002F resolved music index 44.

AFTER5's `mapanim.tsv` (143 MapObjectAnimationInfo rows, 10 worlds) was read live on 2026-11-04. It existed only as
a loose file under `scratch/render-worlds-after5/lang`, so the installed app could not get it.

## What changed

- **`scripts/build_native_data_export.py`** (new) replays the repository's own exporters over the local snapshots,
  in a fixed recipe. It builds next to the destination, runs `mu-native-data check` on every component, and only
  then renames the set into place. It never rebuilds an existing set in place. The recipe:
  - `lang`: `live_lang_to_plain.py` over `lang/live/lang4.bin`, `skill2/live/lang5.bin` and
    `quest2/live/lang5.bin`; then `live_effect_table_to_plain.py` over `render-effects-008/live/s2-lorencia-fxt.bin`
    (step `effects-v1`); then the mapanim step.
  - `objects/live/plain`: `live_objects_to_plain.py` over 47 world snapshots (`objects/live/dumps`,
    `fidelity2/live`, `data-acq-002/live`). The 31 DATA-ACQ-002 worlds use `--installed Data/World<n>/EncTerrain<n>.obj`.
  - `audio/tables`: `extract_audio_tables.py` over the pinned text/data captures (`pins.TEXT`, `pins.DATA`).
- **The mapanim step:** AFTER5 deleted the langread snapshot after converting it, so the table enters as a
  pre-converted file.
  - Its SHA-256 `d7a2cc72…a57de814` is pinned in the recipe, together with its row count (143) and world count (10).
  - Each row is checked against the 7-column layout that `mu_objects_anim_load` reads.
  - The table is copied into the published lang export. `native_data_manifest.publish_step` then records it: an
    `input` entry (`4/0/mapanim.tsv`), a `file` entry, and the producer
    `lang-export-v1-effects-v1-mapanim-v1-live-read-2026-11-04`. The earlier inputs are kept.
  - A different table is refused. A new live read needs a new table, pin and date in the recipe.
- **`native_data_manifest.py`**: new `producer()` and `publish_step()`. A later step extends a published export's
  producer instead of replacing it.
- **App default scratch** (`PreviewCore.swift` `Paths.defaultScratch`): without `MU_NATIVE_SCRATCH`, the app now
  takes `~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export` when that folder exists. Otherwise it falls
  back to the scratch root, and then to the legacy path, as before. `MU_NATIVE_SCRATCH` and a `scratch` entry in
  `settings.json` still win.
- **App setup needed no code change for mapanim.** For a manifest-bearing export, `copyStep` copies every regular
  file, and the launch plan sets `MU_LANG_DIR=<Native Data>/lang`. Through that variable, `mu_objects_start` reads
  `mapanim.tsv`, and the client's managed-data check verifies the root manifest, which now lists `lang/mapanim.tsv`.
  - Without the file (an older set or Native Data folder), nothing changes.
  - An unrecorded `mapanim.tsv` in an export makes setup refuse the whole export.
- **`test_native_audio` private test:** without `MU_AUDIO_TABLE`, it now uses the canonical set's
  `audio/tables/audio-tables.tsv`.

## The export set

`~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export` (11 MB, decoded game data, local only):

| Component | Files | Manifest | Against APP-REFRESH-003's set |
|---|---|---|---|
| `lang` | 30 + manifest | producer `lang-export-v1-effects-v1-mapanim-v1-live-read-2026-11-04`, 5 inputs | the same 29 files byte for byte, plus `mapanim.tsv` (= AFTER5's file) |
| `objects/live/plain` | 94 (47 worlds) + manifest | `objects-export-v1-…`, 77 inputs | manifest byte-identical |
| `audio/tables` | 1 + manifest | `audio-export-v1`, 2 inputs | manifest byte-identical; 1,515 sites, 1,514 resolved (index 44 resolved) |

Two independent builds of the set are byte-identical.

## Validation

Under the 2026-11-04 test budget there is no lane gate; the steward's batch gate is the full gate. The private
runs use INTEGRATION-GREEN-002's `env.sh` (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT` = the installed game), with
the `MU_NATIVE_SCRATCH` line removed and `MU_AUDIO_TABLE`, `MU_LANG_DIR` and `MU_OBJECTS_PLAIN_DIR` unset.

| Check | Result | Wall time |
|---|---|---|
| Build: `make -C native -j4`, `world`, `preview-app` | ok | 19 s + 5 s + 26 s |
| `build_native_data_export.py` (canonical set) | 47 worlds, 30 lang files, audio 1,515/1,514; every component checks | 26 s (trial run 34 s) |
| `test_native_data_manifest` | 15/15 (new: the mapanim step, its refusals and the earlier provenance it keeps) | 7 s |
| `test_native_audio` (incl. private, default table) | 15/15 | 3 s |
| `test_native_app` (incl. private smoke, default scratch) | 17/17 (new: setup imports a recorded `mapanim.tsv` and refuses an unrecorded one; default-scratch preference) | 64 s |
| The two private tests, verbose | `test_private_installed_audio` ok, `test_smoke_over_the_installed_game` ok | 33 s |
| `tests/test_pins` | 16/16 | 1 s |
| `scripts/audit_repository.py` | 0 rejected | 16 s |

**INTEGRATION-GREEN-002 (c) rows, default env:**
- Row 6, `PreviewAppPrivate.test_smoke_over_the_installed_game`: passes without `MU_NATIVE_SCRATCH`. Setup took
  `scratch/native-data/export`, and the test now also checks that `Native Data/lang/mapanim.tsv` equals the set's file.
- Row 7, `test_private_installed_audio`: passes without `MU_AUDIO_TABLE`. All 76 music rows resolve, index 44
  included.

**App setup over the default scratch** (built app, temporary support dir in lane scratch):
- `--print-settings` gives `scratch: …/scratch/native-data/export`.
- `--setup`: gfx converted 179, lang copied 30, objects copied 94, sound copied 1, manifest written; 28 s.
- The root manifest lists `lang/mapanim.tsv` (`d7a2cc72…`), and `mu-native-data check` passes.
- `--print-plan`: `MU_LANG_DIR=<Native Data>/lang`, `--world-objects <Native Data>/objects`.
- The same app with `MU_NATIVE_SCRATCH` = the shared scratch root refuses:
  `scratch/lang`: missing manifest, exit 1.

**World 144 through Native Data** (one DATA-ACQ-002 tour, default draw):
- `fidelity_tour.py run` with `objects_dir` = `<Native Data>/objects` and `MU_LANG_DIR` = `<Native Data>/lang`,
  both managed. The client checks the root manifest.

| Run | Velocity differences, map (near hero) | Other OBJECT fields | Image |
|---|---|---|---|
| AFTER5 "after" (its PR) | 0 (0) | none | 12.391 |
| **Native Data path (this lane)** | **0 (0)** | **none** (8,988/8,988 matched) | 11.769 |
| control, no `MU_LANG_DIR` | 1,563 (40) | none | 12.394 (= AFTER5 "before") |
| control, `MU_LANG_DIR` = only `mapanim.tsv` | 0 (0) | none | 12.391 (= AFTER5 "after") |

- The Native Data image differs from AFTER5's because its lang also carries `mapeffects.tsv`. RENDER-EFFECTS-008's
  table effects then draw too, as in the installed app.
- Each tour took about 3 s. The renders were deleted after reading.

Steward validators: none. No reconstructed routine or validator-built source changed.

## APP-REFRESH-004: installing the new set

The installed app (82849bc) predates this change, so its default scratch is still the scratch root. Pass the set
explicitly:

1. Build the app from main with this PR and the real Ruffle (`MUGFX_LIB=` as in APP-REFRESH-003), and install it
   with the rollback steps of APP-REFRESH-003.
2. Check the set before using it:
   `"$APP/Contents/MacOS/mu-native-data" check "$E/<component>" "$GAME_ROOT/main.exe"` for `lang`,
   `objects/live/plain` and `audio/tables`, with `E=~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export`.
   - If the set is missing or stale, rebuild it into a NEW folder:
     `tools/python/bin/python scripts/build_native_data_export.py --out <new>`, after `make -C native build/mu-native-data`.
3. Run setup into a NEW, empty Native Data folder, as in DATA-ACQ-004:
   `MU_NATIVE_GAME_ROOT="$GAME_ROOT" MU_NATIVE_SCRATCH="$E" MU_NATIVE_SUPPORT_DIR="$NEW_SUPPORT" "$APP/Contents/MacOS/MuNativePreview" --setup`.
   - With the new app, `MU_NATIVE_SCRATCH` can be left out: the default is `$E`.
   - Expect: gfx converted (179), lang copied (30), objects copied (94), sound copied (1), manifest written.
4. Verify:
   - `mu-native-data check "$NEW_SUPPORT/Native Data" "$GAME_ROOT/main.exe"` passes;
   - `grep lang/mapanim.tsv "$NEW_SUPPORT/Native Data/native-data.manifest"` finds the entry;
   - `--print-plan` shows `MU_LANG_DIR=<Native Data>/lang`.
5. Point `settings.json`'s `nativeData` at the new folder (keep a `settings.json.before`). Today it holds only
   `nativeData` = the APP-REFRESH-002 folder, which stays in place as the rollback. It has no `scratch` key, so
   the new app's default scratch applies.
6. Smoke the installed app (`--smoke --backend gl`, with isolated logs and `--no-store`). In Swamp of Destruction
   (world 144), the objects' velocities should now follow AFTER5's table.

## Old folders a later cleanup can remove

Not deleted here, because other lanes may still read them. Once no lane's env points at them:
- `scratch/app-refresh-003/export` (11 MB): superseded by this set. INTEGRATION-GREEN-002's `env.sh` still sets it
  as `MU_NATIVE_SCRATCH`; drop that line first.
- `scratch/audio/tables` (`audio-tables.tsv`/`.json`, 2026-10-17): stale; superseded by `export/audio/tables`.
- `scratch/render-worlds-after5/lang/mapanim.tsv`: now inside the set. Keep it as long as the recipe pins it as the
  mapanim input; a rebuild needs it.
- Keep: `scratch/lang` and `scratch/objects/live/plain`. Their snapshots (`lang/live`, `objects/live/dumps`) are
  recipe inputs, and the export-group tests still use their extra files (`social-options.tsv`, `filter*.txt`,
  `EncTerrain142.velocity`, `env.sh`, `tools/`).

## Limits

- The mapanim provenance is a pinned hash of a converted table, not of the live snapshot, which AFTER5 deleted.
  The manifest proves integrity from this point on, not the read itself (see DATA-ACQ-004's limits).
- The export-group tests (`MU_LANG_DIR`, `MU_OBJECTS_PLAIN_DIR`) still point at the shared folders. The set holds
  no `social-options.tsv`: APP-REFRESH-001..003 never exported it, and setup imports only what a manifest records.
- The app's GFx fallback copies (`<scratch>/npc/movies`, `gfx3/movies`) are only looked up under the scratch folder.
  With the new default, that is the export folder, which has no movies. This fallback is used only when the game
  folder has no `Data/Interface/GFx`. Such movies were refused anyway unless they carried a manifest.
