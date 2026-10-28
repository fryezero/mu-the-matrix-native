# RENDER-WORLDS-F

Recovered and implemented Tarkan/Raklion's missing additive screen haze. [Full finding](../research/client-world-haze.md).
Worktree `~/Documents/MTM/worktrees/render-worlds-f`, branch `codex/render-worlds-f`. No live client, launcher,
service, protected module, main-checkout build or other agent's worktree was used.

## Scope

- `reconstructed/terrain/world_haze.*`: exact screen weather calls and quad geometry for worlds 8/57/58.
- `native/core/mu_world_haze.*`: existing client texture-upload rules and software raster adapter.
- `native/world/parts/haze.c`: new isolated screen part, GL setup/draw/teardown. Existing world source is touched
  only by one new `parts.def` row; makefile and order test include it. Raklion timer/object methods and input
  files are untouched. Both renderers run it after 3D effects and before labels; `--no-env` suppresses it.
- New registered validator, synthetic pixel and runtime regressions, explicit availability/hash measurement tool,
  finding and shared documentation lines. No fitted light multiplier, fog flag or combiner change.

## Checks

- `validate_worlds_f.py --cases 600 --mutations`: **1,818 comparisons, zero mismatches/stops, 7/7 compiled
  mutants caught**. Tarkan/Raklion/quad 600 each; loader prefixes 3; native scope guard 15. Registered private
  runner passes with the same counts. GL imports and resource services are recording boundaries; the actual
  instructions execute the world branches, quad, coordinate scaling and state wrappers.
- Portable new tests pass: flat-texture additive pixels, sibling silence, missing-texture silence, and runtime
  draws on both GL/software backends in worlds 8/57/58. The existing eight world-part order checks pass.
- Fourteen saved-snapshot tour views rendered at the existing 25-frame endpoint. **Twelve unaffected PNG hashes
  identical; fourteen object and light dump pairs identical.** Original Tarkan/Raklion images do not survive,
  so both before and after original-image errors are null. The script preserves this rather than inventing scores.
- Full local Mac gate and broad weather regression: results recorded below before merge.

## Image evidence

| Measurement | Tarkan | Raklion |
|---|---:|---:|
| Current original-image error before | unavailable | unavailable |
| Current original-image error after | unavailable | unavailable |
| Native masked mean absolute change | 12.728 | 11.718 |
| Native pixels changed out of 1,178,576 | 1,176,401 | 1,178,575 |
| Channels darkened | 0 | 0 |

The historical first-tour 22.5 / 22.7 errors are not current before scores. The historical separate Tarkan
Wine-renderer A/B 18.8 to 13.2 remains valid evidence of a Wine-track contribution; it does not measure this
correction. The client pass adds color over the screen even with equal terrain light and disabled fog.
Exact captured clock/phase and the residual image error remain unmeasured. No claim that all error comes
from Wine, or that the image gap is completely closed.

## Reproduce and continue

```sh
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private \
  --only validate_worlds_f --report "$F_SCRATCH/registered"
tools/python/bin/python scripts/fidelity_tour.py run "$F_SCRATCH/before.json"
tools/python/bin/python scripts/fidelity_tour.py run "$F_SCRATCH/after.json"
tools/python/bin/python scripts/world_haze_fidelity.py "$F_SCRATCH/before.json" "$F_SCRATCH/after.json" \
  --output "$F_SCRATCH/fidelity.json"
bash scripts/local-macos-ci.sh
```

`F_SCRATCH=~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-f`; native renders are in the corresponding
`native/renders/render-worlds-f/{before,after}` directories. Use a binary built before/after the correction for
the two tour commands. The manifests retain the original HUD/hero masks and saved snapshot paths. All reports,
full digests, scratch assembly and renders remain local. No client bytes or decoded assets are committed.

Next: a separately authorized capture of original Tarkan/Raklion PNGs plus simultaneous WorldTime and renderer
mode, then a native replay at that clock. The main brightness cause is now a verified implementation rather
than an unexplained terrain-light hypothesis. Fog.OZJ's possible other loaders remain unproven and are not
needed by these verified passes. RenderLeaves phase, Wine-side batching/JPEG differences and sibling lanes
remain separate.
