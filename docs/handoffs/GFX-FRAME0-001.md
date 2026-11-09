# GFX-FRAME0-001

Branch `codex/gfx-frame0-001`. GPT-6.1 Sol. Offline/static only. The original client, live memory, services,
installed Native Preview, Wine apps, canonical private environment and canonical GFx library were untouched.

## Cause and result

FOLLOWUPS-001 identified a stale binary. The October 22 libmugfx predates the source's comparison clock and
Ruffle patch 0008. With `MU_GFX_TEST_CLOCK=1`, its AS2 timer returned `[21, 89, 89]` across a host wait and a
40 ms player advance. The rebuilt library returns `[0, 0, 40]`. The source clock needed no change.

`test_followups.FrameZero` now includes the minimal HUD as well as the original Lorencia inventory/tooltip
scene. Both tests ran, neither skipped, with four fresh scene processes per test. Each scene's four raw RGBA
frame-0 hashes and four PNG files are identical. The proof wrapper fails on any skip.

| Scene | Four starts, one raw SHA-256 |
|---|---|
| Minimal HUD, 1280x800, Lorencia 138,123, class 1 | `926e270ba9bf64db7971922a80076fe56e3e90643e15996f5826aecc22d73024` |
| Original README-IMAGES-D scene, inventory and authored equipment | `8962e651dd33e17c2d066d7ee2413f6cb3a75c677194315e3552a374b19f8f83` |

No additional runtime source fix was necessary for those cases. These are native repeatability proofs, not
original-client pixel equivalence. Comparison captures use `MU_GFX_SINGLE_BUFFER=1` and `MU_GFX_TEST_CLOCK=1`.
The normal shared-surface path remains asynchronous; a particular wall-clock screenshot is not a fixed-frame
equivalence claim. Test clocks must remain unset for normal playback and performance measurements.

## Library and build provenance

New local artifact: `~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib`.

SHA-256: `eaf39b722e34e6d6f2eae34378bbac67d5004d2b4a9be8de005df3edd26a1645`.

Canonical legacy library remains `libmugfx.dylib`, SHA-256
`30f7484dc2d8e9241cf4f1d3f430ec47193ff2f9777595feb05838e85c4f638e`.
There is no runtime library digest pin in the repository to update. These local binaries are not committed.

Inputs:

- Ruffle `nightly-2026-10-17`, revision `061b39b0c3ecdd88214ba1750a035a678bf73559`.
- All eight `native/gfx/ruffle-patches/*.patch`, applied in filename order with `git am` and author dates used
  as committer dates. Patched HEAD `7c0c6611`; concatenated patch SHA-256
  `ae38b00491774805eae1731cf7fc2d4bb33e5f1d1476b3b6b2397469501a8bba`.
- `native/gfx/mugfx/Cargo.lock` SHA-256
  `84d12e0019ce492b10a30d28cb36eef7a249a0ccad98b71c930a5fb18cd31a4c`.
- Rust/Cargo 1.99.0, rustc `b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, LLVM 23.1.1,
  target `aarch64-apple-darwin`. Apple clang 21.0.0, SDK 27.2, macOS 27.2 build 26B123.
- Temurin JDK 21.0.12.1+1-LTS from the existing private tools dependency directory.

The lane used an isolated shared clone of the existing pristine pinned Ruffle checkout, then
`apply-ruffle-patches.sh`. It did not modify the shared patched checkout. Cargo used the committed lockfile.
The first build started without a target directory. Recompiling mugfx after touching `src/lib.rs` produced a
byte-identical dylib, checked with `cmp`, in 27.09 s. This is a same-toolchain, same-path repeat compilation;
cross-host or path-independent binary reproducibility was not tested.

From a fresh lane checkout, this is the rebuild recipe. Use the toolchain versions above and run from the repo
root after the brief's load/memory/disk check. `build-mugfx.sh` now enforces `--locked`, cargo `-j 4` and make `-j4`.

```sh
export MU_GFX_DEPS="$HOME/Documents/MTM/mu-mac-tools/native/scratch/gfx-frame0-001/deps"
mkdir -p "$MU_GFX_DEPS"
git clone --shared --quiet \
  "$HOME/Documents/MTM/mu-mac-tools/native/gfx-deps/ruffle-061b39b0c3ec" \
  "$MU_GFX_DEPS/ruffle-061b39b0c3ec"
native/gfx/apply-ruffle-patches.sh
export JAVA_HOME="$HOME/Documents/MTM/mu-mac-tools/native/gfx-deps/jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
nice -n 10 cargo build --locked --release -j 4 --manifest-path native/gfx/mugfx/Cargo.toml
# Equivalent full bridge/window helper, after preparing the dependency link:
# nice -n 10 native/gfx/build-mugfx.sh
cp native/gfx/mugfx/target/release/libmugfx.dylib \
  "$HOME/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib"
shasum -a 256 "$HOME/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib"
```

The first source build took 126.12 s. Cargo dependency retrieval used lockfile revisions; it was not game
network work. All movie loading and scene checks use local files.

## Private checks and captures

All checks ran from the repository root. The private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`, then override `MU_GFX_LIB` with the new artifact.
`MU_GFX_DEPS` points at the isolated dependency directory above. For the optional nameplate and quest checks,
`MU_NAMES_GFX_MOVIES` and `MU_QUEST_MOVIES` point at `$MU_NATIVE_DATA_DIR/gfx`, and `MU_LANG_DIR` at
`$MU_NATIVE_DATA_DIR/lang`. Those variables make the previously unavailable tests run.

The initial affected selection was 119 work items, above the 40-item private cap. **8d reduced** covers the two
changed test modules plus the task's real-GFx consumers. No unchanged instruction validator's mutants are repeated.
The private run covers `test_native_gfx`, `test_native_gfx2`, the `test_native_gfx3` classes except
`ClientRoutines`, `test_native_stress.MetalTiming`, `test_native_names.GfxRoute/GfxTravel`,
`test_native_quest.LorenciaDemo`, `test_inventory_fx.InventoryScene`, `test_followups.AccessoryFixture/FrameZero`,
`test_native_capture_alpha.LorenciaTooltipSceneTests`, `test_app_polish5.PrivateGroundSkill`, and
`test_app_polish6.PrivateDemo`. The unchanged `ClientRoutines` instruction comparison is separate from loading
the new library. No C symbol, ABI structure or table size changed; brief 6b/8b add no compiled consumers.

The initial private run found one pre-existing fixture failure. `GfxRoute` expects a dead Hound's nameplate to
be removed, but APP-POLISH-001 moved the presentation Hound to 205,131, outside the bow's range from 182,128.
The unmodified test fails at exactly the same `removeInfo` assertion with the legacy library. Its own placement
now puts a stationary target at 185,128, preserving the presentation fixture. The corrected test passes with
both libraries. This changes only test setup, not combat or GFx behavior.

The capture sweep's GFx cases passed: prototype CPU composite and GL shared-surface PNGs, and the original
inventory/tooltip scene through software and GL backends. Every saved pixel is opaque, and the scene checks
retain the distinct raw-alpha hash. The 80-player Lorencia/Tormenta captures, full-durability tooltip, equipment,
nameplate travel, quest, ground-skill, load order, icons, input, fonts, IOSurface and Metal telemetry checks pass.

Window-only before/after HUD captures are retained as steward review inputs:

- `~/Documents/MTM/mu-mac-tools/native/renders/gfx-frame0-001/before/1-hud.png`
- `~/Documents/MTM/mu-mac-tools/native/renders/gfx-frame0-001/after/1-hud.png`

Both are 1280x800 framebuffer captures from this lane's own SDL window, inspected visually, with alpha 255
throughout. Same current tool and movie inputs; only the library changes. There are 1,310 changed pixels,
bounded by x 532..689, y 723..786 in the animated HUD. The rest is byte-identical. The legacy runtime ignores
the requested comparison clock, so this pair is a visual regression check, not equal-time movie equivalence.
Recipe: `mu-gfx-window --gfx "$MU_NATIVE_DATA_DIR/gfx" --script --bench --frames 25 --size 1280x800 --out-dir DIR`,
with `MU_GFX_TEST_CLOCK=1 MU_GFX_SINGLE_BUFFER=1 MU_GFX_PUBLIC_DEMO=1` and a lane-local settings directory.
Both processes exited themselves; the installed Preview was not used. These short captures are not benchmarks.

| Check | Result | Wall |
|---|---|---:|
| Clean-target locked Cargo release build, cargo -j 4 | pass | 126.12 s |
| Repeat mugfx compilation and binary `cmp` | identical dylib | 27.09 s |
| `nice -n 10 make -j4` | pass | 31.19 s |
| Clock + four-start original/minimal regressions | 2/2 pass, 0 skips; each 4/4 identical raw hashes and PNGs | 36.55 s |
| Private GFx checks, initial | 54 tests, 53 passed, 1 old fixture failure, 0 skips | 113.37 s |
| Unmodified nameplate test with legacy library | same missing removal, confirms baseline defect | 3.70 s |
| Corrected nameplate test, legacy / new | 1/1 each, 0 skips | 3.44 / 3.25 s |
| Window-only before / after | inspected, same layout, opaque | 1.91 / 1.94 s |

The private coverage above is 56 distinct tests after the fixture correction, all exercised with the new library,
zero remaining failures or skips. Only the failed test was repeated after changing its fixture.

To reproduce the core acceptance check after sourcing the private environment and selecting the new library:

```sh
nice -n 10 tools/python/bin/python -m unittest \
  native.tests.test_followups.FrameZero \
  native.tests.test_native_stress.MetalTiming
```

`FrameZero` contains both four-start scene tests. The in-tree mugfx artifact is needed by `MetalTiming`; during
this lane it is the byte-identical build copied to the retained artifact. The final cleanup removes that target
directory, so a later lane must rebuild it to rerun tests that require the in-tree shot executable and library.

## Switching and the next app refresh

The orchestrator should change only the last `MU_GFX_LIB` assignment in
`~/Documents/MTM/mu-mac-tools/native/private-env.sh` from `$S/polish/libmugfx.dylib` to
`$S/polish/libmugfx-frame0.dylib`. Re-source it from the repository root. Do not set `MU_GFX_TEST_CLOCK` globally.
Rollback is the original assignment; both files remain available.

The next APP-REFRESH should verify the new digest above, then bundle it explicitly:

```sh
nice -n 10 make -C native/app -j4 \
  MUGFX_LIB="$HOME/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib"
```

The bundle stores it under `Contents/Frameworks/libmugfx.dylib`. Follow the app refresh's normal dylib fixup,
signing and verification flow; the copied file's hash may change during those steps. Run that lane's full private
native/tests before installing. This lane does not install or replace the app.

## Cleanup and limits

After the ready line, delete the lane's Rust target, dependency copies, scratch, reports and source worktree/local
branch. Keep only `scratch/polish/libmugfx-frame0.dylib` for the next APP-REFRESH and the two small HUD PNGs as
steward review inputs. The images can be deleted after review. No new game input is required by a later lane.
The canonical library digest was rechecked unchanged. The steward owns the merge; no push follows the ready line.

No original-client execution, protection analysis, network/login/server-state work, memory writes, live capture,
installed-app replacement, performance acceptance or general all-movie determinism is claimed. The fixed clock
applies only when requested, and the normal-clock test verifies that real host waiting still advances AS2 time.
