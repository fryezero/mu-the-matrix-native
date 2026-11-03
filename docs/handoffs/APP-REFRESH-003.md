# APP-REFRESH-003

Implementation handoff, 2026-11-03. Worktree `worktrees/app-refresh-003`, branch `claude/app-refresh-003`, from
origin/main `d5ffde0` (#277 with #275/#276), merged with `d9389d5` (#278 RENDER-WORLDS-AFTER3) before packaging.
macOS 27.2, Apple clang 21, clean build in a fresh worktree. Offline only: no original client, launcher, live read,
account, network or protection work.

## Source changes

- `native/client/main.c`: the windowed loop now prints the `input_state`/`input_items` (and GFx) report at exit,
  as headless runs do, when the run had scripted world input.
- `native/app/Makefile`: `$(CLIENT)` now depends on a phony `client` target that always asks the native submake,
  as the converter rule does. Before, an existing `native/build/mu-client` was bundled stale after a source change
  (`make -C native/app` only). New test `test_app_build_rebuilds_a_stale_client` fails before the change and passes
  after it.
- `native/tests/test_native_app.py` (private smoke): keeps `MU_NATIVE_SCRATCH`. The shared scratch exports have no
  manifests, so with an empty support dir the smoke refused setup ("missing manifest") and printed no JSON.

## Journey proofs

Headless GL drive of the installed bundle's mu-client, with the app's launch plan, `--auto --hold 6`, the
`field` session (slot 1 at Lorencia 179,131) and `--no-store`, isolated settings:

- **Selected-skill right-click cast on the Budge Dragon:** `skill_casts` 1 (skill 19), 0 refused, 2 combat casts.
- **Kill, drop and Space pickup:** 1 kill and 1 drop. Space after the drop lands near the hero gives
  `space_picks` 1, 1 pickup request and 1 completed pickup.
  - The earlier APP-REFRESH-002 failure was the script's fault: further attack clicks after the kill walked the
    hero more than 300 units from the drop (`mu_world_items_space`'s range). It was not a native bug.
- **Move-panel click travel:** M, then a click on the Noria row, then M, then the Devias row. The log shows
  `travel: world 0 -> 3` and then `world 3 -> 2`.
  - Row points at 1280×800: x 122; Noria y 257; Devias y 324.
  - The same travel works in the windowed app (installed build) with the report printed.
- **Audio (`--wav`, BGM on through `option.ini` in the isolated settings dir: IsMusicPlay=1, Volum=9):**
  1,074,628 stereo frames at 44.1 kHz, peak −32,768/32,767, RMS 3,880, 135 samples at full scale.
  - With the default (absent) options the capture is silent, because BGM starts off.

Windowed (installed app, 1280×800 forced; this Mac's display is now 1920×1080, so the app picks a 1504×936
window and the scripts' points would not match without `--width 1280 --height 800`):

- Travel 0 -> 3 -> 2 works, and so do `skill_casts` 1, the chat line, the Help window (Ctrl+H) and the Warps window.
- Windowed kill and pickup counts stay 0: the monsters wander in real time, so fixed click points miss. The
  headless proof is deterministic.
- Kardamahal Underground Temple (world 143, gate 704) loads via a session `join` line, since its Warps row needs
  level 1550.

## Native Data and exports

- No exporter, gfx or app-setup input changed since 52aa5c2, so the installed app keeps
  `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-002/Native Data`.
- Manifest-bearing export set for setup and smoke: `~/Documents/MTM/mu-mac-tools/native/scratch/app-refresh-003/export/`
  (`lang`, `objects/live/plain`, `audio/tables`; 11 MB). `mu-native-data check` passes for all three.
  - `audio/tables` was re-exported with `extract_audio_tables.py --main-exe` and is byte-identical.
  - `lang` and `objects` are copies of the APP-REFRESH-002 components with their manifests.
  - Use `MU_NATIVE_SCRATCH=<export>`.
- The shared `scratch/{lang,objects/live/plain,audio/tables}` were deliberately left without manifests. They hold
  other lanes' extra files (`env.sh`, `live/`, `tools/`), and the client checks any manifest-bearing ancestor of
  `MU_LANG_DIR`. A manifest there would refuse those lanes' runs as soon as their files change.

## Installation

- Installed `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 82849bc, version 0.1 (1), real
  Ruffle. Strict deep signature and `--check-bundle` pass.
- Rollback: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-003/` holds the APP-REFRESH-002 app
  (52aa5c2) as a zip (11.6 MB) and `settings.json.before`. The `app-refresh-002/` rollback (APP-REFRESH-001 app) is kept.
- Installed `--smoke --backend gl` (isolated logs/settings, `--no-store`), with and without `--audio`: ok, world
  reached, 0 connects/inet/lookups.
- Screenshots (local only): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-003/`
  - `1-kardamahal-after3.png`
  - `2-lorencia-cast-fight.png`
  - `3-warps-window.png`
  - `4-devias-after-travel-chat.png`
  - `5-help-window.png`

## Checks

- `nice -n 10 bash scripts/local-macos-ci.sh` at `660a4e4`: 38 suites, 1,805 tests, 1,566 passed, 239 skipped,
  0 failures. Fixtures, viewer and live readers ok; audit 1,801 files, 0 rejected.
- `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<installed> MU_NATIVE_SCRATCH=<export> python -m unittest
  native.tests.test_native_app`: 16/16. Note that it runs `make -C native preview-app` without `MUGFX_LIB`, which
  rebuilds `native/build/app` with the GFx stand-ins. Rebuild with `MUGFX_LIB=` before installing.

## Follow-ups

- The demo placement's Lorencia monsters keep their name labels after travel: "Budge Dragon" and "Hound" float
  without models in Devias (screenshot 4). These are world/session actors, not app packaging.
- At Volum=9 the BGM mix reaches full scale (135 clipped samples in about 24 s). Check the audio module's gain.
- Kardamahal's long map name is drawn too small to read in the top-left map box (screenshot 1).
- `MU_NATIVE_EXTRA_ARGS` still splits on spaces; scripts must use `--input-script FILE`.
- Helpers: `scratch/app-refresh-003/{bin,sess}`. `run.sh` does windowed app runs (forces 1280×800), `hl.py` does
  headless runs with an app plan (`AUDIO=1`, `XARGS`, `EVERY`), `hj.txt`/`j1.txt` are the journey scripts, and
  `sess/` holds the sessions for field, dd3, abyss2 and kard.
