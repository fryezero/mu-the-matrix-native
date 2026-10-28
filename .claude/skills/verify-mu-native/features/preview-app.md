# Native Preview app refresh

Verify the newly built offline app in its own HOME before an owner-authorized
installation. Existing data must pass the build-keyed manifest check.

## Sub-features

- app-build: current mu-client, bundled C converter/helper, real Ruffle, strict signature.
- app-first-run: temporary HOME without Python; setup, repeat and refusal before client start.
- app-window: all available panels, walking, attack/cast, sound cues and click travel.
- app-install: only after the gate and smoke pass; record data regeneration and source revision.

## How to get to it (user POV)

Double-click the preview, enter the offline demo and select a character. Click
the ground to walk, a monster to attack, right-click to cast. Use the keys in
[input.md](input.md) for panels. M opens Move; clicking a destination travels.
Hold Option at launch for settings and a new Native Data destination.

## Driving it with run-tool.sh

Preconditions: explicit owner authorization to refresh/install the app, an isolated
worktree and a real compatible local libmugfx. Read
[Native Data](../../../../docs/native-data.md) before importing exports. Never
stamp legacy exports. Re-export existing snapshots with the documented writers.

- Build the normal binaries and run doctor. Build the app with
  `make -C native preview-app MUGFX_LIB="$MU_INPUT_GFX_LIB"`.
  `codesign --verify --strict --deep "$APP"` and
  `"$APP/Contents/MacOS/MuNativePreview" --check-bundle` must pass.
- First run: create `$TEMP_HOME`; run `env -i HOME="$TEMP_HOME"
  CFFIXED_USER_HOME="$TEMP_HOME" PATH=/nonexistent MU_NATIVE_GAME_ROOT="$GAME_ROOT"
  MU_NATIVE_SCRATCH="$VERIFIED_EXPORTS" "$APP/Contents/MacOS/MuNativePreview" --setup`.
  Check the resulting root with the bundled `mu-native-data check DIR MAIN_EXE`.
  Repeat setup must say `manifest: kept`. Corrupt only the temporary root
  manifest's build field and require setup/plan/smoke refusal before a child log
  appears; restore the exact original manifest afterward.
- Gameplay: run [input.md](input.md) through run-tool. Enable `--items` for pickup;
  after the selected cast, left-click the actor to exercise plaintext attack and
  kill/drop. A successful cast does not prove encrypted skill damage.
- App window: use the same temporary HOME, `MU_NATIVE_SETTINGS_DIR="$RUN/tmp/settings"`,
  and `MU_NATIVE_EXTRA_ARGS="--no-store --input-script $INPUT --out-dir $SHOTS"`.
  Start the built launcher with `--seconds 45`. Capture `shot:NAME` for each panel,
  read the child log and inspect every PNG. The launcher extras split on spaces,
  so INPUT/SHOTS must have no spaces. Test Ctrl+A/J with `down:17 key:A up:17`
  or `down:17 key:J up:17`; Home/End/F1 are numeric keys 36/35/112.
- Travel: at 1280x800, the current Move list has Noria at 130,258, Devias at
  130,325 and Lorencia at 130,240. Open M before each click, allow the world to
  load, capture it, and require `travel: world` logs 0→3→2→0. Coordinates depend
  on sorting, movies and screen size; inspect the Move screenshot first.
- Sound: enable `MU_AUDIO_CUE_LOG="$RUN/proof/audio.jsonl"`, require successful
  `play` rows and record unresolved rows separately. Inspect the guard exit
  report for zero IP/connect/lookup attempts. Cue logs do not prove human hearing.
  The launcher's `--smoke` adds `--no-audio` unless `--audio` is also passed.
  For PCM proof add `--wav PATH` through launcher extras; enable BGM or effects
  through Options in the run's settings if the installed preferences are muted.

## Gotchas

- The generic skill ban on driving Preview prevents touching an owner's existing
  process. This recipe covers only a new built-app process you start for an
  explicitly requested refresh. Stop only that owned PID.
- The app may show an error alert after a child failure. The launcher still
  running is not proof of a working client; inspect the child log/exit.
- Session seeds omit resources. The world fixtures must supply their baseline
  hero replies, and combat respawn must retain MP/SD/AG. Require a real successful
  selected cast, not just an opened skill bar.
- Fourth/fifth/master trees can open with absent data. Record the visible gap;
  do not count the missing data as verified or use it to conceal a new regression.
- Owner data may be legacy and correctly refused. Follow the new-folder setup
  procedure, preserve the legacy folder as rollback input, and record the new
  destination. Do not silently delete or relabel the old data.
- Installation and owner-data changes are exceptions authorized by the refresh
  request, not by this recipe. Other native drives retain the read-only rules.
