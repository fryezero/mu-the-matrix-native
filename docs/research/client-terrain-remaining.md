# Remaining terrain rendering, RENDER-TERRAIN-002

The remaining terrain routines run in `reconstructed/terrain/terrain.c` and feed the native terrain renderer.
The comparisons use the same pinned restored text, second image section and trig flag as
[client-terrain.md](client-terrain.md#identity-and-method). `scripts/pins.py` verifies their complete digests before
execution. No client was launched or read live. Reports and renders are local, outside the repository.

**Verified** means compiled authored C compared with the original instructions in Unicorn. **Static** means an
instruction reading. Host conventions and remaining integration inputs are listed separately below.

## Overlay faces

RenderFace `0x016cf46c` draws two fans in worlds `0x71` and `0x91` when detail is at least 4 and the first corner
has attribute `0x2000`. The first fan binds `0x7722`, `World114/cubemap_up.jpg`, and uses alpha 0.4. The second
uses the original tile UVs under the alpha wrapper with alpha `1 - 0.4`. Both retain frame light plus the second
light map. This is independent of the `0x4000` neighbour face and the later layer-2 pass.

World `0x71` uses the map-load reflection grid. `0x016c936a` interpolates normalized edge vectors, normalizing
after every interpolation. `0x016c95f9` computes sphere-map UVs from a fixed camera position. World `0x91`
recomputes the four sphere-map coordinates against the current camera and terrain normals per face.
`0x016c977c` reflects the direction about the normal, normalizes it, and maps it to two texture coordinates.
The caller passes tile coordinates directly to RequestTerrainHeight, without multiplying them by 100. The C
preserves that quirk. The original also emits GL normals; terrain uses vertex colors with fixed-function lighting
disabled, so the native sinks and comparison omit those normal-state calls.

The initializer, reflection helper and both complete tile streams are verified. The native loader resolves the
overlay bitmap and builds world `0x71`'s grid. The active camera and terrain normals feed world `0x91`.

## Chaos Castle

`0x009dc0b1` runs before the ordinary face in worlds `0x12..0x17`, `0x35` and `0x61`. After a one-in-eight random
gate, arena state 0, 3 or 6 selects four inclusive boundary strips. The routine creates smoke `0x7f5e` at
`(tile_x*100 + rand()%30 - 15, tile_y*100 + rand()%30 - 15, hero_z)`, with white light, zero angle and scale 1.5.
A subsequent one-in-five gate writes camera shake `(rand()%3 - 3)*0.1`. Random call counts, particle calls and
shake writes are verified, including rejected worlds, stages, gates and strip boundaries.

The native terrain callbacks route that particle into the existing particle pool. The smoke05 bitmap is loaded;
its create, move and render cases share the already reconstructed smoke02 branches. Adding `0x7f5e/0` to all
three original-instruction families passed 600 cases each, including their existing negative controls. Changes
to particle files are limited to this required terrain effect. Per-world object files are untouched.

## Camera frustum, fog and alpha

CreateFrustrum2D `0x016d20d9` uses the full negated camera angles in world `0x49`, with the camera interpolator's
pitch delta added to X. In world 6 it uses negated camera yaw only when the hero name contains `webzen` or
`webzen2`; otherwise it retains the ordinary 45-degree rotation. The special-name view uses distance 8500,
near offset `distance*0.05`, back offset `distance*0.47` and widths 3000/540 times screen width divided by 640.
Both name outcomes, widths, zoom modes, rotations and pitch deltas are verified. The name lookup and camera
singleton are explicit host inputs; their C++ object storage is outside this family.

The GL setup region `0x0184b043..0x0184b0bb` sets `GL_GREATER` with alpha reference 0.25. An enabled fog flag
selects GL_LINEAR mode, density and the four-component fog color; a cleared flag disables fog. Both outcomes
are verified. Static inspection of the scene entry points shows that they clear the flag. Native scene rendering
uses the cleared flag and the recovered 0.25 reference. The earlier 0.25 value was already correct, so this
adds evidence and explicit configuration without changing ordinary-world pixels. No enabled-fog gameplay is
claimed.

## Kalima signed grids

Worlds `0x18..0x1d` and `0x24` replace ordinary terrain rendering with a dynamic water mesh. The record contains
four 256x256 signed 32-bit grids, the active-buffer index, light direction, 1764 vertices and normals, and an
index buffer. The verified offsets include active `+0x100004` and index count `+0x114ad4`.

- `0x009f953b` clears the grids and sets light direction to `(1,-1,1)`.
- `0x009f9952` injects a bounded disturbance, including negative-coordinate random placement and signed shifts.
- `0x009f85fc` updates the active grid from its other buffer with wrapping integer sums and arithmetic shifts.
- `0x009f8318` writes the two sinusoidal grids around the hero, preserving float operation order and truncation.
- `0x009f9b67` samples the signed grid at twice the ordinary tile resolution. Its final divisor is 4.
- `0x009f86d6` builds the 42x42 mesh around the hero, alternating triangle diagonals, accumulating face normals
  in client order and normalizing their averages. Its height divisor is 2, unlike the height query.
- `0x009f9644` draws 3362 triangles twice, with the alpha water texture and additive normal-based light pass.
  Texture IDs `0x7630/0x7631` resolve to `Object25/water1.tga` and `water2.jpg` with the captured filters.

Every routine has a separate verified family. The native world owns the signed record, advances it with the
terrain frame, uses the signed height query for ground sampling and draws the mesh through both software and
GL sinks. The existing triangle batching accepts the new triangle primitive. Native world changes are confined
to the terrain part's camera/hero feed, special-name frustum call, event-particle callback and alternate-pass hook.

## Verification

`validate_terrain_remaining.py --mutations` compares 2,147 cases across 14 families with **0 mismatches**.
The two whole-grid reflection cases compare 196,608 normal floats and 131,072 UV floats. Each mesh case
compares all vertices, normals, indices and the count. The six draw cases compare the complete color, UV,
vertex, texture and wrapper streams for both passes. All **14 compiled C mutants** are detected in their named
family, independently of the additional output-perturbation controls. Mutants change reflection scale, overlay
opacity, reflection normals/camera, camera rotation, alpha reference, the Chaos random gate, grid clearing,
ripple/stencil shifts, wave phase, height divisor, triangle diagonal and additive light.

The particle create/move/render comparisons add **1,800 cases, 0 mismatches**. Portable synthetic terrain tests
pass 19 existing tests and 6 new regressions, with the two existing private-world tests skipped. The new
regressions check signed layout and negative arithmetic, signed heights and bounds, both overlay worlds,
Kalima's dynamic render, the two camera-frustum worlds and the Chaos smoke callback into the real native particle pool.
A 20-frame synthetic Chaos run on both software and GL creates and draws 13 particles with zero unsupported
requests or overflows.

Synthetic software renders were inspected. At 240x150, GL versus software pixels differing by more than 8/255
are 452/36000 for world 0, 0/36000 for Kalima, 520/36000 for world `0x71` and 760/36000 for world `0x91`.
Differences are rasterization and texture-filter edges, within the existing comparison threshold.

Ordinary-world software hashes remain byte-identical to the pre-change build at 200x120, target 12850/12850,
distance 2500, time 1234, seed 7:

| World | SHA-256 of RGBA pixels |
|---|---|
| 0 | `8a1831b283316bc2cde28b9e310cb4e5daddce63ceff852fa36103fb9f3e86e4` |
| 7 | `91e7d61d592d177c48b52a8bab98693cb21d15ab5e0cb841b93cd0863e330cf1` |
| 63 | `4d4d7f4159f08aaa7db921a15ae39f0e54042f8382322349b6aede01adfa3bdd` |
| 142 | `141262c13f5cd755597749f90a263d7e440307f57d9fb8b7f58b6c7a3c507259` |

Intended changes are the two `0x2000` overlays at detail 4+, Chaos Castle boundary smoke, camera-angle culling
in the specified worlds and Kalima's signed water mesh. The alpha-reference evidence changes no pixels.
The legacy terrain validator at `--scale-002 5` now compares all 43,200 world tile streams with zero
mismatches and zero unsupported overlays, 682,695 GL calls and 371 particles. Its other previous families
remain equal. The original face-normal family's 29 generated NaN-sign-only pairs retain their earlier label;
371/400 ordinary bitwise normal results match, without a numeric mismatch.

Local artifacts are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-terrain-002/` and
`~/Documents/MTM/mu-mac-tools/native/renders/render-terrain-002/`. They are not committed.

## Host boundaries and limits

- The native renderer uses its own seeded MSVC random stream, particle capacity and frame clock. Comparisons
  inject the same random values into C and Unicorn and verify consumption. Global cross-system random ordering
  is not established by this task.
- Chaos arena stage is an explicit renderer input, default 0 in the offline host. The shake write feeds the existing native camera's earthquake input on the next frame. The stage's
  authoritative event feed and the camera interpolator's evolving pitch delta belong to their gameplay/camera owners. The default
  native frustum pitch delta is 0; the reconstructed entry accepts the actual delta explicitly.
- Native host bounds refuse unsafe signed-grid coordinates and radii. The original trusts its callers. Comparisons
  cover the original's valid domain; signed intermediate arithmetic wraps as x86 does.
- Synthetic render agreement and instruction comparisons do not replace a live fidelity tour. No live game,
  installed data publication, networking, protection modules or per-world object reconstruction was used.

## Instruction provenance

The table gives half-open text ranges and SHA-256 prefixes. The complete text pin is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; text base is `0x00401000`.

| Routine or bounded region | Range | SHA-256 prefix |
|---|---|---|
| reflection normals | `0x016c936a..0x016c95f9` | `6cb7a2f713d60660` |
| reflection grid | `0x016c95f9..0x016c977c` | `022f66b05a364410` |
| reflection UV | `0x016c977c..0x016c9868` | `562418efd01b8c1d` |
| overlay face | `0x016cf46c..0x016cfada` | `7cf63f00b1ce5362` |
| Chaos face | `0x009dc0b1..0x009dc2f0` | `c74ccfffb51d3b6a` |
| camera frustum | `0x016d20d9..0x016d2d81` | `de946a01a793f7ac` |
| fog and alpha region | `0x0184b043..0x0184b0bb` | `1da8601076e6d13f` |
| signed init | `0x009f953b..0x009f95a7` | `ac24f48e091284d9` |
| signed ripple | `0x009f9952..0x009f9b67` | `9996efef36a9c7e2` |
| signed step | `0x009f85fc..0x009f86d6` | `6854c04b4f39aace` |
| signed wave | `0x009f8318..0x009f85fc` | `0f02259520934033` |
| signed height | `0x009f9b67..0x009f9c88` | `6459b618c680fc08` |
| signed mesh | `0x009f86d6..0x009f8fd4` | `daaf4b6fd994fdd3` |
| signed draw | `0x009f9644..0x009f9952` | `dd185342e2fe844d` |
