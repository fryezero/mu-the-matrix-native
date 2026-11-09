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
   The CLI retains its documented stand-in frame and grid-only input, rather than claim GFx artwork equivalence.
4. Done: original movie constants/clip bindings identify slots 9..14 as amulet, right/left ring, pentagram and
   right/left earring. The opt-in `--gfx-open inventory,equipment-demo` supplies their six level-zero appearance
   records. Item.bmd tags 9/10/10/236/237/238 and installed model files must match. Missing inputs stay empty.
   Private test: all six slots draw, zero missing models; without the opt-in, all six remain empty.

## Evidence

- Capture tests: charsel soft/GL, frame window, model viewer soft/GL with alpha 0.5, terrain viewer soft/GL,
  GFx CPU/GL and REGRESS-003's original soft/GL scene. All saved pixels alpha 255. Model-viewer raw hashes differ
  from flattened PNG hashes, proving the tests exercised blended alpha rather than only an opaque clear.
- CLI before/after: same current build objects, with only mu_render_hud.c restored from the base for the before
  binary. Authored textured 0x389c fixture, time 500 ms, 1024x768. Before 18 triangles, after 16, one model drawn,
  zero missing in both. The removed two triangles are the skin sprite. The test also proves adding its sprite
  texture or changing the clock cannot change the icon now; ground skin sprites continue to draw.
- Frame-0 probes: original scene four runs / three distinct raw hashes, 18.27 s; minimal HUD scene four runs,
  10.89 s; four identical bridge logs / different PNGs, 11.96 s. AS2 timer probe 18 -> 69 ms without advance.
- Static equipment evidence: local original InventoryFrame MUDefines and InitEquipeSlot bindings, checked against
  Item.bmd +0x256 metadata and the existing instruction-compared inventory pass. No decoded source/data committed.

## Checks

Pending final affected checks and wall times.

## Next

Rebuild libmugfx with the source tree's eight Ruffle patches, in an isolated dependency/build directory, without
replacing the owner's installed app or the parallel refresh's files. Point MU_GFX_LIB at that result, confirm
`test_followups.clock_samples()` returns `(0, 0)`, then run `test_followups.FrameZero`. Investigate any remaining
frame-0 differences before claiming determinism. A later app refresh can choose whether to ship the rebuilt library.

No stat formulas or equipment effects were added. General accessory replication, equipment transactions and
character-list packet levels remain outside this offline milestone.

## Cleanup

Pending final PR-ready cleanup.
