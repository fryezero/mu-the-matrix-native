# BUILD-DEPS-001 build hygiene, 2026-10-28

## Problem

The native Makefile listed header dependencies by hand (`$(HEADERS)`, `$(WORLD_RT_HDR)`, `$(SESSION_HDR)`,
`$(AUDIO_HEADERS)` and others). Some headers were missing from those lists, so after a merge that changed a shared
struct (for example #247 growing `mu_jt_object` and `mu_sfx_effect`), objects that included it were not rebuilt.
`scripts/local-macos-ci.sh` does not clean, so long-lived worktrees could run the gate or fidelity tools on
stale objects.

Measured against the old lists (`make -p` of the previous `native/Makefile`):

- 826 object/header pairs in 102 native objects were untracked.
- Most were session objects (`build/sdev`, `build/sprod`: `$(SESSION_HDR)` only) and world-runtime objects
  (`build/world-rt`, `build/world-rt-gl`) that include reconstructed/core headers. Examples:
  `remote_players.h` (62 objects), `client_audio.h`/`hero_sound.h` (48), the skill headers (30 each),
  `map.h` (31) and `world_gfx_map.h` (24).
- Five `reconstructed/*` libraries also missed a header: actors (`bone_tracks.h`, `pose_builder.h`,
  `record_math.h`), mix (`item_services.h`), objects (`client_movement.h`), progress (`progress_internal.h`) and
  renderchar (`record_math.h`).
- Recipe-compiled tools and hosts (`mu-render`, `mu-world`, `mu-client`, the `*-host` tests) had no header
  dependencies at all for their own sources.

## Change

- **`native/Makefile`**
  - `DEPFLAGS = -MMD -MP -MT $@` is part of `CFLAGS` and `CXXFLAGS`, which are now recursive (`=`), and is added
    to the two compile lines that do not use `CFLAGS` (`build/recon/%.o`, `build/audio/recon_%.o`).
  - Every compile writes a `.d` next to its `-o` output. Its target is the rule's target: the object for pattern
    rules, or the tool/library for recipes that compile and link.
  - The six rules that compile several sources in one call (`libmuui`, `libmumeshdraw`, `mu-proto`,
    `libmunet`, `mu-data`, `libmuquest`) also run `$(call MULTI_DEPS,<flags>)`, one `-MM` pass into `$@.d`.
    clang keeps only the last source's `-MMD` output for such a call.
  - All `.d` files under `$(BUILD)` are `-include`d after `clean` (the gfx subdirectories are left to
    `gfx/Makefile`).
  - The object pattern rules no longer carry hand-written header lists: `core`, `recon`, `charsel-rt`,
    `world-rt`, `world-rt-gl`, `audio`, `sdev`, `sprod`, `fixture`, `world_fixture.o`, `mu_world_players.o` and
    the two `$(CORE_OBJ)`/`$(WORLD_RT_OBJ)` extra-prerequisite lines. They keep `$(GEN_STAMP)` and
    `$(LAYOUT_STAMP)`, so generated headers still exist before the first compile (`test_native_build_generation`
    passes).
  - **Transition:** an existing object of those rules that has no `.d` yet depends on the phony `deps-missing`,
    so a build directory from before this change rebuilds those objects once.
  - Tool, host and library rules keep their explicit header lists. Those lists only make them rebuild too
    often, never too rarely.
- **`native/gfx/Makefile`**: the window loop and converter objects use `-MMD -MP -MT $@`, and the layer-test
  host gets an `-MM` pass.
- **`native/help/Makefile`**: one `-MM` pass.
- **`reconstructed/deps.mk`** (new) is included at the end of all 36 `reconstructed/*/Makefile`s. Each library
  rule (44, counting model-codec's six and the price/skill mutant rules) runs `$(DEPS)` after its compile: one
  `-MM` pass over the rule's `.c` prerequisites into `<target>.d`. The hand-written HDR lists stay.
- **`model-recovery/Makefile`**, **`live-readers/Makefile`**: single-source builds with `-MMD -MP -MT $@`.
- **`.gitignore`**: `*.d`.

Rules a lane adds to `native/Makefile` are tracked automatically if they compile through `$(CFLAGS)` one source
per call. A new call that compiles several sources at once needs `$(call MULTI_DEPS,<its flags>)`.

## Checks

- **Byte-identical outputs.** Two clean builds of origin/main 99fc34c gave identical hashes for all 647 outputs,
  so the toolchain is deterministic here. A clean build with this change gives the same 647 hashes.
  - Covered: every `native/build` and `live-readers/build` file except the `.d` and `ar` archives (the archives'
    member objects are compared), every `reconstructed/*` and `model-recovery` library, and `recover-block`.
  - Built for the comparison: `make all`, the reconstructed items/players/terrain/mix libraries, the 22 test
    hosts plus mu-session, mu-native-data, libmucrypto, mu-audio-live, `client`, `world`, `make native-viewer`,
    `make live-readers` and `make -C native/gfx converter`.
- **Exact rebuild set.** After touching `reconstructed/joints/joints.h`, the pattern objects `make -n` planned
  to recompile were exactly the 77 objects whose `.d` lists it. A rebuilt tree is `make -q` up to date. A
  `.d` removed from an object makes only that object stale.
- **New test** `native/tests/test_native_build_deps.py` (2 tests, about 1.6 s). It uses `make -q -W <header>`,
  so no real file's mtime changes.
  - It builds two audio objects and `mu-proto` into a temporary `BUILD` that is deleted afterwards.
  - `core/mu_wav.h` makes `mu_wav.o` stale but not `recon_hero_sound.o`, and the reverse for `hero_sound.h`.
  - The first source's header `tools/../core/mu_protocol.h` makes `mu-proto` stale, which shows the `-MM` pass
    covers more than the last source.
  - In-tree, `item_services.h` makes `libmix` stale (it is in no hand list). `bone_tracks.h` makes
    `libbonetracks` stale but not `libmodelcodec`.
  - Run against the old Makefiles, both tests fail.
- **Gate.** `bash scripts/local-macos-ci.sh` after merging origin/main 88a4517 and a clean `native/build`: passed, 1,693 tests (218 explicit skips, 0 failures), 11/11 fixture scenarios, audit 1,662 staged files with 0 rejected. The new worlds-o/p/p2 host rules from main are tracked with no change.

## Limits

- `make -W` matches a header by the exact spelling make knows (for example `../joints/joints.h` versus
  `core/../../reconstructed/joints/joints.h`). Real mtime changes are found under every spelling, so this
  affects only `-W` queries.
- Make does not track flag changes. Changing `CFLAGS` or a `-D` still needs `make clean` (unchanged).
- `live-readers` still rebuilds `objread` on every run, because the phony `layout-json` regenerates
  `build/layout_reader.h`. That predates this change.
- Apple clang lists the SDK's `SDKSettings.json` in every `.d`, so an Xcode/SDK update rebuilds everything.
- `native/app/Makefile` (preview app) is outside the gate's default build and was not changed.
