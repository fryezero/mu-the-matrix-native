# Native Data and client updates

The app accepts Native Data only for its supported client build. The current
`main.exe` SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The installed executable, the root manifest and every component manifest must
agree. A matching executable alone does not make an old data folder usable.

Setup writes `native-data.manifest` after conversion and verified export copies
finish. Each manifest records its version, client hash, producer version/options,
source input sizes and SHA-256 hashes, and the exact output inventory with sizes
and hashes. A final count marks completion. The root inventory includes component
manifests, which retain snapshot and converter-input provenance. Incremental
object exports retain earlier input records. Manifests and exports stay local.

The app checks before creating a launch plan or starting the native client.
The native client, world, character-select, viewer, renderer, terrain, language,
audio and GFx window command-line tools also check managed data before use.
They recognize a manifest, a legacy `setup.json`, or a `Native Data` folder in the
path's ancestors. Raw authored fixtures and explicit research inputs remain
available through the existing low-level file APIs. For any custom folder whose
management metadata was removed, explicitly check it with `mu-native-data check`
before using a tool. App setup always requires a manifest on imported exports,
regardless of the folder name.

Missing manifests, unsupported builds, truncated manifests, missing/extra/changed
files and symlinks produce this message and stop the launch:

> Native Data cannot be used: [reason]. Re-acquire Native Data for this client build in a new folder, then run Setup again.

Deleting files from a completed component is an error. Entire optional components
may be absent at acquisition time: the offline preview then retains its existing
stand-ins. An incomplete conversion or copy does not produce a completed set.
A recorded empty optional set does not claim acquisition of every world.

## Regenerate for the supported build

1. Keep the old Native Data and capture folders as backups. Do not edit their
   manifests or copy files from another client build into them. `--force` first
   verifies the existing set; it cannot bless an unversioned or damaged set.
2. Select the matching installed game folder in the app settings. Choose a new,
   empty Native Data folder. The default is
   `~/Library/Application Support/MuTheMatrixNative/Native Data`.
3. Use the existing local captures from that client build, or acquire a fresh
   set through the guided capture design in DATA-ACQ-002/CAPTURE-KIT-001. Guided
   capture is the chosen user path, including event worlds. Its packaging and
   second-user reproduction are still pending; this milestone adds no capture
   automation. Acquisition and native play must be serialized with the shared
   game lock. No live capture is required merely to regenerate converted movies.
4. Export the snapshots into new component directories under a new scratch root.
   Development commands below use already acquired files. Supply the supported
   executable with `--main-exe`; it is hashed before any output is changed.
   Keep diagnostic JSON outside the component directories where possible.

   ```sh
   make -C native build/mu-native-data
   tools/python/bin/python scripts/live_lang_to_plain.py "$LANG_SNAPSHOT" \
     --out "$SCRATCH/lang" --main-exe "$GAME_ROOT/main.exe"
   mkdir -p "$SCRATCH/objects/live/plain" "$SCRATCH/audio/tables"
   tools/python/bin/python scripts/live_objects_to_plain.py "$OBJECT_SNAPSHOT" \
     --out "$SCRATCH/objects/live/plain/EncTerrain1.plain" \
     --main-exe "$GAME_ROOT/main.exe"
   tools/python/bin/python scripts/extract_audio_tables.py \
     --text "$TEXT_CAPTURE" --data "$IMAGE_DATA_CAPTURE" \
     --out "$SCRATCH/audio-report.json" \
     --tsv "$SCRATCH/audio/tables/audio-tables.tsv" --main-exe "$GAME_ROOT/main.exe"
   # Optional additional language tables, using the documented matching snapshots:
   tools/python/bin/python scripts/live_social_options_to_plain.py "$SOCIAL_SNAPSHOT" \
     --out-dir "$SCRATCH/lang" --main-exe "$GAME_ROOT/main.exe"
   ```

   For object exports, repeat the existing snapshot-to-world mapping for each
   captured world; the example's world 1 filename is not a generic mapping.
   The snapshot and installed-file options retain their prior meanings.
   Exports accept an empty or already verified destination, preserving earlier
   source hashes when adding worlds/tables. `--raw-output` is an explicit
   research/fixture seam; setup refuses to import those unversioned files.
5. Set the app's scratch folder to that new scratch root, then run Setup in the
   settings window. Setup converts installed GFx, fonts and NaviMaps using its
   bundled C converter and copies verified optional exports. The packaged app
   needs no Python. Command-line equivalent, with an explicit empty destination:

   ```sh
   MU_NATIVE_GAME_ROOT="$GAME_ROOT" MU_NATIVE_SCRATCH="$SCRATCH" \
     MU_NATIVE_SUPPORT_DIR="$NEW_SUPPORT" \
     "$APP/Contents/MacOS/MuNativePreview" --setup
   "$APP/Contents/MacOS/mu-native-data" check \
     "$NEW_SUPPORT/Native Data" "$GAME_ROOT/main.exe"
   ```

   A failed forced regeneration leaves the old movie files intact, but refuses
   the incomplete set. Choose a new empty folder and retry after fixing the input.

## A genuinely new client build

An unknown executable is refused even during setup. A user must obtain a native
app release supporting that build, then repeat acquisition in new folders. Do not
change the manifest's client hash to bypass the refusal.

For maintainers, re-pinning requires a new evidence record and validation of the
changed client routines, layouts, exports and conversion results. Update the pin
in `native/data/manifest.cpp`, the app build default in `native/app/Makefile`,
`scripts/pins.py` and the evidence index together, then rerun the relevant
instruction comparisons, manifest tests, first-run tests and local macOS gate.
The test suite checks that the app and portable helper pins match the evidence
index. `CLIENT_SHA256` is a compile-time fixture-test override, never a launcher
environment bypass. Existing sets cannot be migrated by changing hashes.

The jump-table diff tool for a new build is explicitly remaining DATA-ACQ-004
work. It depends on the paused NET-DISPATCH-001 work. This manifest slice does
not resolve dispatch differences, implement the guided capture kit, or prove a
new build's compatibility.

A manifest detects accidental drift; it is not a signature or an independent
attestation of an old snapshot's originating process. Exporters record the
supplied supported executable and exact snapshot hashes. Sources must come from
that same build. Source files need not remain installed to verify an acquired
set; output hashes and nested provenance manifests are verified on consumption.
