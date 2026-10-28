# Tarkan and Raklion screen haze, RENDER-WORLDS-F

The native renderer omitted two additive screen quads in each world. This is a client-side cause of the
brightness gap in [world fidelity gap 2](client-world-fidelity.md#4-gaps-ranked-by-visibility), independent of
the separate Wine renderer contribution observed on 2026-10-22. The correction changes no terrain light,
vertex-color scale, texture combiner or fixed-function fog setting. No original client or launcher was used.

## Evidence and reconstruction

**Verified** means production C compared with the pinned original instructions under Unicorn. **Static** means
instruction reading. The text and second-section identities are verified through `scripts/pins.py`, the same
whole-input pins as [the terrain finding](client-terrain.md#identity-and-method). The table gives half-open
original ranges and SHA-256 prefixes; the local validator report retains full region digests.

| Family | Original range | Region SHA-256 prefix | Cases |
|---|---|---|---:|
| Tarkan screen pass | `0x016b247c..0x016b2627` | `d19d8ea9078ac717` | 600 |
| Raklion screen pass | `0x00e9eae8..0x00e9ec6a` | `f0b5ef2c9300c7bf` | 600 |
| Screen quad | `0x0184f4ba..0x0184f793` | `588810608368efb9` | 600 |
| Tarkan texture-load prefix | `0x01839ac1..0x01839b01` | `31db16816bdead59` | 1 |
| Raklion texture-load prefix | `0x0183f494..0x0183f4d4` | `140907dcb4a6eb60` | 2 |
| Native world dispatch | silent siblings, world 58 equals 57 | authored host boundary | 15 |

All **1,818 comparisons match, zero mismatches or stopped cases; 7/7 compiled C mutants are caught**. Mutants
change the first sand scroll, signed Raklion V scroll, quarter-height UV skew, additive-state selection,
Raklion color, Tarkan texture name and world gate. The validator freezes the production source before building
both baseline and mutants. Clock cases include zero, period boundaries, negative values, int32 limits, NaN
and infinity. Quad cases vary position, dimensions, UVs and viewport size independently. The world gate is
an authored scope check, not an original sibling-world reconstruction.

`reconstructed/terrain/world_haze.c` emits the pass through the existing terrain sink. The whole relevant
Tarkan branch and complete Raklion routine execute as original instructions. The Tarkan comparison stops at
`0x016b2eb6`, before dispatching sibling world handlers and unrelated hero/UI overlays. The Raklion receiver
is unused in this method. Original width/height converters and Vector2 execute; only GL imports, texture
lookup and loader services use recording stubs. Existing terrain state wrappers execute as original code
and are compared at their established abstract state-call boundary. Native pixel tests separately check
ONE/ONE behavior. No texture decoding or GPU rasterization is claimed as Unicorn evidence.

Let `p = float(CVTTSS2SI(WorldTime) % 100000)`. The C remainder retains its sign.

| World | Ordered bitmap | RGB color | UV origin | UV extent |
|---|---|---|---|---|
| 8 | `0x7f21`, `Object9/sand01.jpg` | 0.3, 0.3, 0.25 | `p*0.0002`, 0 | 0.3, 0.3 |
| 8 | `0x7f22`, `Object9/sand02.jpg` | same | `p*0.001`, 0 | 3, 2 |
| 57/58 | `0x7f22`, `Object9/sand02.jpg` | 0.4, 0.4, 0.45 | `p*0.0006`, `-p*0.0006` | 3, 2 |
| 57/58 | `0x7f21`, `Effect/Map_Smoke1.jpg` | same | `p*0.0001`, 0 | 0.3, 0.3 |

All use GL_LINEAR, GL_REPEAT, GL_MODULATE and additive ONE/ONE blending, with depth writes and alpha test off.
Tarkan first calls the alpha wrapper with argument 1 and white alpha 0.5, then switches to additive and
`glColor3f`; that last call restores alpha 1. Using 0.5 as the haze's final alpha would be incorrect.

The quad covers logical 640 by 480 scaled to the full window. Its GL_TRIANGLE_FAN vertices go top-left,
bottom-left, bottom-right, top-right. Its left-edge V coordinates are `v+dv*0.25` and `v+dv-dv*0.25`, while
the right edge uses `v+dv` and `v`. A conventional rectangular UV mapping changes the client behavior.

## The earlier hypotheses

**Static.** RenderMainScene calls the 2D setup `0x0184f793` at `0x01859cb8`, then the interface-weather entry
`0x016b229b` at `0x01859cd0` when the top-view flag is clear. That entry calls the Tarkan branch. Its common
continuation calls world-manager `0x00ea31ad`, which invokes handler slot `+0x40`; Raklion's vtable
`0x01aad9d0` points that slot at `0x00e9eae8`. Its object mover and event timer are separate and unchanged.
The full-window orthographic state explains why the two draws appear after the 3D geometry in the saved trace.

The saved Tarkan trace's two `0x0184f707` fans occur immediately after ONE/ONE state and two texture binds.
This address is the return address of glBegin inside the verified quad, not a new unknown rendering routine.
The previously described 'same state calls' did not rule out this post pass: the trace recorded call families
and texture object names, but not the quad's color, UV or bitmap identity.

The 75 `0x0184c2bc` quads belong to the existing RenderLeaves path. It uses SRC_ALPHA/ONE_MINUS_SRC_ALPHA,
white color, a 16 by 16 leaf bitmap and individual translated planes. It is spatially sparse, unlike the screen
passes. Native RenderLeaves is already reconstructed in `reconstructed/environment/env_leaves.c`. The
25-frame native Tarkan tour has not yet populated that pool, so this task does not claim the leaf phase matches
the old live frame. Existing weather comparisons are reported separately in the handoff.

There is no literal `Fog.OZJ` reference in the pinned second-section string scan. This is not proof that no
formatted or external path can ever load it. The verified relevant texture-loader prefixes name sand01,
sand02 and Map_Smoke1 directly, and the missing passes need none of the World9/World58 Fog files. A global
proof about every possible Fog loader is unnecessary and is not claimed. Previously verified terrain streams,
primary/frame light equality, zero light-offset grid and disabled scene fog remain consistent with this result.

## Native integration and measured boundary

`native/core/mu_world_haze.*` loads the client-selected bitmaps with the existing JPEG upload rule and renders
the verified stream through the software rasterizer. `native/world/parts/haze.c` supplies the GL sink and owns
texture setup/teardown. One row in `parts.def` places the pass after 3D effects and before labels. The native
host establishes full-window orthographic state, saves/restores GL state and matrices, and leaves other worlds
silent. Missing bitmaps skip their draw rather than becoming an untextured white quad. `--no-env` suppresses
the pass with the other weather. No world-handler, Raklion timer, input or session state was changed.

Fourteen tour views were rendered before/after, 1722 by 1048, 25 frames, with identical assets, object snapshots,
clocks and the original HUD/hero masks. All twelve unaffected PNG hashes are identical. All fourteen object
and light dump pairs are identical. The two changed native frames have these masked differences:

| Native-only measurement | Tarkan | Raklion |
|---|---:|---:|
| Scored pixels | 1,178,576 | 1,178,576 |
| Pixels changed by haze | 1,176,401 | 1,178,575 |
| Mean RGB increase | 13.469, 13.472, 11.244 | 11.254, 11.250, 12.650 |
| Mean absolute native change | 12.728 | 11.718 |
| Channels that darken | 0 | 0 |

This additive contribution has a larger relative effect over darker ground and reduces relative contrast.
It can explain the original light-grid/image discrepancy. It is screen-space and scrolls with WorldTime;
the older impression that the entire unexplained pattern followed the ground is not an invariant of this pass.
No brightness multiplier was fitted to that impression.

**Original-image scores are unavailable before and after.** Tarkan and Raklion's original PNGs were deleted
on 2026-10-23; none survive in README sources. Both current tour reports return null image errors. Historical
first-tour errors 22.5 / 22.7 and the separate Tarkan Wine A/B 18.8 to 13.2 remain historical measurements,
not current baselines. Subtracting the native-only changes above from those errors would be invalid. Native
headless time also differs from the captured WorldTime, so even a recovered still needs the exact haze phase.
The finding identifies and implements a missing client pass; it does not establish that all residual Wine/native
image error has disappeared or assign the remainder to Wine.

Reproduce the local comparison with `scripts/world_haze_fidelity.py BEFORE_MANIFEST AFTER_MANIFEST --output FILE`.
The native before/after hashes and explicit null errors are retained locally. A later separately authorized
capture must retain both original PNGs plus simultaneous WorldTime and renderer mode, then replay that clock
for a real score. No live capture was attempted in this task.
