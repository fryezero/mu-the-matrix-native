# FOLLOWUPS-001

Branch `codex/followups-001`, from main `a55200e2`. GPT-6.1 Sol. Offline/static only. No original client, live
memory, network/service work, installed Native Preview, Wine app or staged app was changed. Names and equipment
are authored demo/fixture values. [Findings and slot evidence](../research/client-followups-001.md).

## Results

1. Done: charsel captures, software/window frame tools, GFx window captures and both viewer paths save opaque
   PNGs. Raw RGBA report hashes remain raw. Tests exercise both backends and blended model pixels.
2. Left under Next: frame 0 is reproduced, and the supplied libmugfx is proven to ignore MU_GFX_TEST_CLOCK. The
   source already implements that clock via Ruffle patch 0008. Rebuilding the library and proving four identical
   scene starts remains necessary. The regression test explicitly skips the legacy runtime, it does not pass it.
3. Done: `mu-render ui inventory` no longer draws skin sprites over item icons. The old standalone per-icon
   sprite pool contradicted the original draw order; the app's correct world-list routing remains unchanged.
   The CLI retains its documented stand-in frame and grid-only input.
4. Done: original movie constants/clip bindings identify slots 9..14 as amulet, right/left ring, pentagram and
   right/left earring. The opt-in `--gfx-open inventory,equipment-demo` supplies their six level-zero appearance
   records. Item.bmd tags 9/10/10/236/237/238 and installed model files must match. Missing inputs stay empty.
   Private test: all six slots draw, zero missing models; without the opt-in, all six remain empty.

## Evidence

- Capture tests: charsel soft/GL, frame window, model viewer soft/GL with alpha 0.5, terrain viewer soft/GL,
  GFx CPU/GL and REGRESS-003's original soft/GL scene. All saved pixels alpha 255. Model-viewer raw hashes differ
  from flattened PNG hashes, proving the tests exercised blended alpha.
- CLI before/after PNGs are local review inputs in `~/Documents/MTM/mu-mac-tools/native/renders/followups-001/`,
  `inventory-before.png` and `inventory-after.png`. They contain only the tool framebuffer and authored data.
  Lossless PNG recompression was checked against every original RGBA byte. CLI before/after: same current build objects, with only mu_render_hud.c restored from the base for the before
  binary. Authored textured 0x389c fixture, time 500 ms, 1024x768. Before 18 triangles, after 16, one model drawn,
  zero missing in both. The removed two triangles are the skin sprite. The test also proves adding its sprite
  texture or changing the clock cannot change the icon now; ground skin sprites continue to draw.
- Frame-0 probes: original scene four runs / three distinct raw hashes, 18.27 s; minimal HUD scene four runs,
  10.89 s; four identical bridge logs / different PNGs, 11.96 s. AS2 timer probe 18 -> 69 ms without advance.
- Static equipment evidence: local original InventoryFrame MUDefines and InitEquipeSlot bindings, checked against
  Item.bmd +0x256 metadata and the existing instruction-compared inventory pass. No decoded source/data committed.

Source fingerprints, SHA-256:

| Input | SHA-256 |
|---|---|
| Item.bmd | `0aaf7b311d806a1b27afc404e4ccc25d4754bd00b678a546f39f845091c1fc6f` |
| InventoryFrame.ozg | `7fe7f119cb9523f34782b07ac6e52f0b02ccd9da1ad96afc15ae3d431f2d42f1` |
| converted InventoryFrame.swf | `0ed60b49195bb4896cfdab73c04598f960b3841b93fbba9e842b3a5e84d2e4c5` |
| canonical libmugfx.dylib | `30f7484dc2d8e9241cf4f1d3f430ec47193ff2f9777595feb05838e85c4f638e` |

Default-draw byte identity against main `1e2a927a`, one sweep, no draw_all/live_time and no GFx fixture:

| Capture set | Identical PNGs / dumps / reports | Main / branch render wall |
|---|---|---:|
| October 22, 14 views | 28 / 28 / 14 | 27.58 / 26.69 s |
| DATA-ACQ-002, 32 views | 64 / 64 / 32 | 44.67 / 42.30 s |

Total sweep wall 142.27 s. The baseline restored the three world source files changed here from main into a
lane-local binary, linked with the otherwise unchanged world inputs. Report comparison normalized only output
paths and binary names. Each map's bulk outputs were deleted immediately after hashing/comparison.

## Checks

All commands ran from the repository root. Code validation at `2fc6c83d` includes main `1e2a927a` (#351).
Final test-hygiene edits were covered by the subsequent 17-test private run. No compiled validator input changed
following that run. No lane full gate and no newly required mutants.

| Check | Result | Wall |
|---|---|---:|
| `nice -n 10 make -j4`, after merging main | pass | 11.26 s |
| Dedicated world/viewer builds, before / after | pass | 11.86 / 11.13 s |
| Initial affected listings, validators / units | 9 rows / 118 items before the new docs/test file | 36.07 / 62.47 s |
| Portable affected suites, MU_RECOVERY_INTEGRATION=0, MU_GATE_JOBS=2 | 119 items, 1,304 tests: 1,088 passed, 216 skipped, 0 failures/errors | 333.48 s including selection; 271.7 s execution |
| Private affected validators, cache, no mutants, jobs 2 | 9/9 pass, table below | 174.31 s including selection |
| Private native/tests, **8d reduced**, canonical private-env.sh | Changed/added modules test_native_capture_alpha, test_inventory_skin, test_followups; 6b existing test_inventory_fx.InventoryScene. 17 tests: 16 passed, 1 explicit legacy-clock skip, 0 failures/errors | 37.64 s |
| Earlier private iteration | 19 tests, 18 passed and the same clock skip; duplicate imported test classes removed before final run | 55.42 s |
| Repository audit | 2,109 staged files, 0 rejected | 24.58 s |
| Four documentation-consumer modules, portable | 36 tests, 35 passed, 1 skipped | 7.63 s |
| CLI baseline build + before/after renders | one model, 0 missing; 18 -> 16 triangles; PNGs inspected | 2.65 s |

The native selection was 114 items, above the 40-item private cap. The final private command deliberately selects
three modules plus the existing inventory scene class; it does not re-run the old inventory validator's mutants.
The 6b search found no other consumers of the new wrapper or its private struct field. The portable run covers the
other selected native modules, including frame/charsel/viewer consumers.

The first private iteration found two test/setup defects: the authored model directory needed creating and the
standalone GFx window did not link mu_perf.c. Both were fixed; that failed attempt took 31.09 s. The first tour
attempt stopped before rendering because of stale pre-relocation manifest paths, 4.12 s; only the lane-local
manifest paths were corrected for the successful sweep.

| Validator | Coverage, all matching | Wall |
|---|---|---:|
| validate_meshdraw | 247 pinned, 207 synthetic, 300 mutated INPUTS, 336 installed; 4/4 negative controls | 51.7 s |
| validate_model_edge | 17 files; 278 poses, 528 transforms, 148 draw calls | 105.3 s |
| validate_movement | 6,614 cases | 48.9 s |
| validate_audio_callers | 5,528 cases | 6.0 s |
| validate_audio_domains | 2,544 cases | 22.3 s |
| validate_audio_items | 3,000 cases | 3.7 s |
| validate_app_polish2 | 1,028 cases | 3.3 s |
| validate_app_polish4 | 10,485 cases | 30.7 s |
| validate_worlds_fog | 4,044 cases | 6.6 s |

Steward validators: validate_meshdraw,validate_model_edge,validate_movement,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_app_polish2,validate_app_polish4,validate_worlds_fog

Run at `2fc6c83d`, canonical private-env.sh, `--private --no-mutants --cache --jobs 2`. None needs mutants. Movement
is the reported symbol fallback. Meshdraw's 300 mutated input cases are input coverage, not compiled C mutants.

Resource note: all heavy jobs used nice 10, make -j4 and at most two validator/test jobs. An early 11.86-second
build and 2.65-second helper run started from combined print/build calls before their high load was inspected.
Subsequent launches used threshold guards; resource waits were observed before the final checks. Memory stayed
above 25% free and disk above 150 GB free.

## Next

Rebuild libmugfx with the source tree's eight Ruffle patches, in an isolated dependency/build directory, without
replacing the owner's installed app or the parallel refresh's files. Point MU_GFX_LIB at that result, confirm
`test_followups.clock_samples()` returns `(0, 0)`, then run `test_followups.FrameZero`. Investigate any remaining
frame-0 differences before claiming determinism. A later app refresh can choose whether to ship the rebuilt library.

No stat formulas or equipment effects were added. General accessory replication, equipment transactions and
character-list packet levels remain outside this offline milestone.

## Cleanup

After the ready line, remove this lane's worktree/builds, local branch, verify-runs and bulk scratch outputs.
Keep only the two losslessly compressed inventory PNGs (11,004 bytes total) as inputs to steward review in
`~/Documents/MTM/mu-mac-tools/native/renders/followups-001/`. They can be deleted after the PR merges. No later
implementation lane needs a private capture or other input from this lane.
