# RENDER-TERRAIN-002

Implemented the remaining terrain rendering in `codex/render-terrain-002`. The full instruction evidence and
host-input limits are in [the finding](../research/client-terrain-remaining.md).

- Worlds `0x71/0x91` draw the attribute-`0x2000` overlay and original tile with the client's two alpha values.
  The map-load reflection normals/UVs and per-face reflection calculation are reconstructed.
- Chaos Castle creates smoke05 through the existing native particle pool and writes its camera shake into the
  camera's existing earthquake input. The particle alias and bitmap are the only particle-module additions.
- Worlds 6 and `0x49` use the reconstructed camera-angle frustum. The world-6 special hero names use the wider
  frustum; the optional world-`0x49` interpolator pitch delta is explicit, with native default 0.
- The alpha reference 0.25 and disabled scene fog are backed by instruction comparisons. No ordinary-world
  pixel change was needed for them.
- Kalima worlds `0x18..0x1d/0x24` own the signed four-grid water state, update it, sample signed heights and draw
  the two-pass 42x42 mesh. The water textures use the captured filters and wrap modes.

## Checks

- `scripts/validate_terrain_remaining.py --mutations`: 14 families, 2,147 cases, zero mismatches, all 14 compiled
  C mutants detected. The new manifest row runs this validator through the existing private runner.
- `scripts/validate_particles.py --cases 600 --only create --only move --only render`: 600 cases per family,
  1,800 total, zero mismatches, including smoke05; existing negative controls detected.
- Legacy terrain validator, `--scale-002 5`: 43,200 world tile streams equal, zero unsupported overlays,
  682,695 GL calls, 371 particles. The other previous terrain families remain equal. FaceNormalize retains the
  pre-existing 29 generated NaN-sign-only cases, separately labelled from its 371 bitwise-equal cases.
- Existing terrain tests: 19 tests with 2 private-input skips. New terrain tests: 7 synthetic regressions,
  including native Chaos particle creation/drawing and preservation of the unaffected optional water emitter. A 20-frame Chaos run with both software and GL creates and
  draws 13 particles without unsupported requests or overflow.
- Synthetic software renders inspected; GL/software comparisons pass for ordinary terrain, both overlays and
  Kalima. Four ordinary-world pixel hashes, worlds 0/7/63/142, are identical to the pre-change build.
- `bash scripts/local-macos-ci.sh ./tools/python/bin/python` passed after merging current `origin/main`:
  1,328 tests across 38 suites, 156 explicit skips, plus the two fixture scenarios, Mac viewer/readers and
  publication audit. The remaining-terrain validator was rerun on that tree, 2,147/2,147 and 14/14 mutants.

## Local artifacts

- Reports, logs, mutant reports and synthetic roots:
  `~/Documents/MTM/mu-mac-tools/native/scratch/render-terrain-002/`.
- Renders: `~/Documents/MTM/mu-mac-tools/native/renders/render-terrain-002/`.
- Neither path nor the input symlinks is committed. No live game was started, stopped or read.

## Ownership and remaining inputs

Terrain reconstruction, terrain host/renderer, validators/tests and this milestone's shared documentation rows
were changed. The existing smoke02 branches gained the required smoke05 type and bitmap, verified against
original instructions. `native/world/parts/terrain.c` has the minimal terrain integration hooks; no other
`native/world` file and no per-world `reconstructed/objects` file was edited.

The authoritative Chaos stage, world-`0x49` camera interpolation state and cross-system random ordering remain
inputs owned by gameplay/camera systems. The renderer supports those inputs; the offline host uses stage 0,
zero pitch delta and its own seeded random stream. Live fidelity remains a separate acceptance gate.
