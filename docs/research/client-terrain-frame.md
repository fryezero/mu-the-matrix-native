# Client terrain, part 2: dynamic lights, world tiles, frustum, decals and the 24-bit height choice (NATIVE-TERRAIN-002)

This finding completes the terrain parts that [client-terrain.md](client-terrain.md) (NATIVE-TERRAIN-001) left
out. It covers the per-frame light sources and their falloff, the world-specific animated tiles (water and lava
UV scrolls, per-world blend states, the additive animated layer, the 0x4000 neighbour face), terrain decals, the
view frustum and visible-tile box of RenderTerrain, and the 24-bit height choice for the worlds the literal list
does not decide. Each part has authored C in `reconstructed/terrain`. `scripts/validate_terrain.py` runs it
against the client's own instructions in Unicorn. The parts are wired into `mu-terrain` and
`mu-viewer --terrain`. Static objects (`EncTerrain*.obj`) remain out of scope.

Labels: **compared** means the authored C was run against the actual instructions in Unicorn and agreed bit for
bit; **static** means a reading of the decoded instructions only. Inputs are the pinned restored text, the second
image section and the dispatch flag of [client-terrain.md](client-terrain.md#identity-and-method). Names are ours.

| Routine | Role |
|---|---|
| `0x016c9868` | 24-bit height selector (literal list, then the world handler) |
| `0x00ea488e`, `0x00ea468f`, `0x00ea2713`, `0x00d5cbe3` | world handler registration, current-handler setter, the virtual call, the inherited slot-1 getter |
| `0x016cacfc` | AddTerrainLight(x, y, light, range, buffer) |
| `0x016ca4fa` | per-frame update (light copy over the visible box, waves) |
| `0x016cff65`, `0x016cf46c`, `0x016cfb31`, `0x016cfb70`, `0x016cfbac` | RenderTerrainFace, RenderFace, alpha layer, additive layer, neighbour face |
| `0x016cba24`, `0x0184a569` | CreateFrustrum, GetOpenGLMatrix (`glGetFloatv(GL_MODELVIEW_MATRIX)`) |
| `0x016d20d9`, `0x016ccce7` | CreateFrustrum2D, TestFrustrum2D |
| `0x016cd468`, `0x016d2e8e`, `0x016d2d81` | RenderTerrain and its 4×4 block walk |
| `0x016cdd5f`, `0x016d197d`, `0x016d2050` | RenderTerrainAlphaBitmap (decal), its tile fan, its tile filter |

## 1. The 24-bit height choice (compared; resolved)

`0x016c9868(w)` returns 1 for the literal worlds (0x2a, 0x3f, 0x52..0x5a, 0x64, 0x65, 0x6e..0x70, 0x7a..0x85).
Otherwise it calls `0x00ea594b`, which returns the world manager `[0x01ec91b8]`. `0x00ea2713` then reads the
current handler `[manager + 0x10]` and returns 0 when it is null, else the handler's vtable slot 1. OpenWorld
`0x0182876e` sets the current handler through `0x00ea468f(world)`, which looks the world up in the map that
`0x00ea488e` fills at start-up. That routine registers one handler object per class with its world list (46
classes; e.g. `0x00e942cd` for 0x39/0x3a, `0x00d7a427` for 0x5c/0x60/0x65/0x6f, one class per world from 0x83 to
0x91).

**Static:** every handler class inherits slot 1 from the base class, `0x00d5cbe3`, which returns byte `+4`. The
base constructor `0x00d5c99f` clears bytes 4..6. Only the constructors of the handlers of worlds 0x86..0x91
(134..145) store `+4 = 1` (e.g. `0x00d83d84` for 0x86). No base method writes `+4` afterwards.

**Compared:** the validator runs all 46 handler constructors in Unicorn. Two import calls are stubbed
(QueryPerformanceFrequency/Counter and RtlAllocateHeap), and the CRT CPU-feature bit that picks the SSE2
int64→double helper is set. Each built object is installed as the manager's current handler, as OpenWorld would,
and the selector `0x016c9868` itself runs for all 256 world indices: **256/256** equal to
`mu_terrain_height_is_rgb`. A negative control (literal list only) differs on 12 worlds.

Result: the 24-bit loader is used for the literal worlds and for 134..145, never by file length. Against the
installed files (`--game-root`), 26 folders are 24-bit by this rule. **World67** (world 66) ships a 196,666-byte
24-bit file, but the client reads it with the 8-bit loader. Both loops agree with the C on every installed
height file (55 + 27).

## 2. Dynamic lights (compared)

The client draws terrain lighting in this order each frame:

1. `0x016ca4fa` copies the primary light `0x0bab5430` into the frame light `0x0b9f5430`. It covers rows
   `y_min..y_max+3` and columns `x_min..x_max+3` of the visible box (repeat indexing), copied bit for bit. The
   rest of the grid keeps last frame's values.
2. Light sources call **AddTerrainLight `0x016cacfc`(x, y, light, range, buffer)** with `buffer = 0x0b9f5430`.
   The call sites are objects, characters, items and effects (204 sites in 46 functions). Range is 1 at 117 of
   them and 4 at 9; the others are 2 or computed. In the character scene the selected character gets `(1, 1, 1)`
   with range 1 at its position (`0x01857a0c`, just before RenderTerrain).
3. RenderTerrain reads the frame light per corner (plus `TerrainLight_2`).

AddTerrainLight: `xf = x / 100`, `yf = y / 100`, `xi = (int)xf`, `yi = (int)yf`. It loops rows `yi-range..yi+range`
(outer) and columns `xi-range..xi+range` with float counters. The falloff is
`lf = (range - sqrt(dx² + dy²)) / range`, where `dx = xf - column` and `dy = yf - row`. The sqrt is taken of the
widened value and rounded to float (`0x00961a07`). Where `lf > 0`, each channel becomes `light·lf + buffer` and is
clamped below at 0. There is no upper clamp; GL clamps vertex colours.

**Compared:** 800 synthetic calls (ranges −1..6, coordinates off the map, negative colours), whole 256×256×3
grid equal; Python model equal on 200/200 extra cases. Negative controls: an upper clamp at 1 differs on 196/200,
dropping the lower clamp on 189/200. The light copy rule is compared through the frame update (8/8 world/time/box
sets).

## 3. World-specific tiles (compared)

RenderTerrainFace `0x016cff65`, layer-1 faces. `t = (int)time` (cvttss2si of `[0x06fce370]`) and
`c = ((cos(time·1e-4) + 1)·0.5)·0.5`. The scroll offset `(u, v)` and the wave factor `k` are:

| Worlds | Tile (layer 1) | u | v | k |
|---|---|---|---|---|
| default | 5 (water) | `(t % 20000)/20000` | `c` | 0.0015 |
| 0x1e | 5 | `-(t % 20000)/20000` | `c` | 0.0015 |
| 0x5e | 5 | `-(t % 20000)/20000` | `(t % 20000)/20000` | 0.0015 |
| 0x7a | 5 | `(t % 50000)/50000` | `(cos+1)·0.1` | 0.0015 |
| 0x8d | 5 | 0 | 0 | 0 |
| 0x3f, 0x52..0x5a | 11 (`Object64\song_lava1`) | default water | | |
| 0x64, 0x65, 0x6e, 0x6f | 6 | default water | | |
| 0x7a | 16 | default water | | |
| 0x70 | 21 / 22 / 23 / 24 | `c` / `(t%30000)/30000` / `-(t%30000)/30000` / `c` | `(t%30000)/30000` / `c` / `c` / `-(t%30000)/30000` | 0.002 |
| 0x8a | 32 / 33 / 34 | `-(t%20000)/20000` / `c` / `c` | `c` / `(t%20000)/20000` / `-(t%20000)/20000` | 0.0015 |
| 0x8c | 20 / 21 / 22 | `c` / `-(t%20000)/20000` / `c` | `-(t%20000)/20000` / `c` / `(t%20000)/20000` | 0.0015 |
| 0x8d | 23,30 / 24,31 / 25,32 / 26,33 | `+u`,`c` / `c`,`-v` / `-u`,`c` / `c`,`+v` (20000 period) | | 0.0015 |

In world 0x22, water tiles also spawn a particle (`rand() % 50 == 0` → CreateParticle `0x7f90` at
`(x·100 + rand()%100 + 1, y·100 + rand()%100 + 1, hero z + 10)`, light (0.3, 0.4, 0.2)). The C takes the CRT
`rand()` and the particle sink as optional callbacks.

RenderFace `0x016cf46c` uses the alpha state for texture 3 in world 0x27 (texture 100 draws nothing there), 4 in
0x2d..0x32/0x62..0x63, 2 in 0x33, 10 in 0x45..0x4a, 12 in 0x50/0x51, 9 in 0x5b/0x5c, and 14 elsewhere; every
other texture is opaque. Worlds 0x71 and 0x91 draw extra overlay faces (texture 0x7722, per-corner blend weights)
for attribute 0x2000 at graphics option ≥ 4. Those are **not reconstructed**; the C reports them as unsupported.

After the face, RenderTerrainFace draws:

* the **neighbour face** `0x016cfbac` at graphics option ≥ 4 on attribute-0x4000 tiles: texture 0x7723
  (`World114\TileBright.jpg`), additive state, colour (0.8, 0.8, 0.8). Alpha is 0.8, or 0.5 when any of the four
  edge neighbours lacks 0x4000. The opaque state is restored afterwards;
* the **additive animated layer** where any alpha > 0 and either the world is 7 or 0x80..0x82 with layer 2 = 5, or
  the world is 0x85 with layer 2 = 4. Texture `0x7630 + 200 + [0x0b6b53e0]`; the counter steps
  `(n + 1) % 32` per 40 ms logic step (`0x01851f61`). Bitmaps `0x76f8 + n` are loaded by `0x018392db` from
  `Object131\wt%02d.jpg` for 0x80..0x82 and from `Object8\wt%02d.jpg` for every other world, GL_LINEAR. The
  layer uses 16-texel UVs (FaceTexture's small flag), no scroll, and `glColor3f(alpha, alpha, alpha)` per corner;
* otherwise the alpha layer of NATIVE-TERRAIN-001.

The Chaos Castle per-face routine `0x009dc0b1` (worlds 0x12..0x17, 0x35, 0x61) only spawns effects. It is not
ported; the validator stubs it, and the terrain stream after it is compared.

**Compared:** 36 worlds with extended synthetic scenes (scrolling tiles, lava, 0x4000 cells, the 32 animated
bitmaps, detail 0 and 4 alternating, times including negative): 43,147 tile×pass streams equal, 53 unsupported
(0x2000 overlay faces), 371 particles equal (position and type). Python model equal on 2,100/2,100; negative
controls (generic world rules) differ on 185 scroll and 44 blend cases. Installed tiles are below.

## 4. Frustum and visible box (compared)

**CreateFrustrum `0x016cba24`(aspect, position, flag).** The main scene passes `aspect = window width / 640`.
`distance = [0x01cf1630]·0.9`. `width = tan(fov·0.5·3.141592/180)·distance·aspect + 100`, with fov from
`[0x01cf1634]`, binary32 constants `0x40490fd8` and `0x3c8efa35` (a literal 3.14159f fails), and the tan of the
widened value rounded. `height = width·3/4`. The corners are `(0,0,0)`, `(∓w, ±h, -d)` in the order
(−,+), (+,+), (+,−), (−,−). Each is rotated by VectorIRotate with the 3×4 modelview from `glGetFloatv`
(`m[i][j] = gl[4j+i]`) and offset by the camera position `0x0bdc5ab4` → vertices `0x0bdb5430`.

The box starts at (25600, 25600, 0, 0) and keeps the minimum/maximum x, y. Each bound becomes
`(int)(v/100)/4·4 ∓ 4`, clamped to 0..251 → `0x0b6b53f8`, `0x0b6b53fc`, `0x01cf15e0`, `0x01cf15e4`. Face normals
`0x0bdb546c` are FaceNormalize of (0,1,2), (0,2,3), (0,3,4), (0,4,1), (3,2,1). The planes `0x0b6b53e4` are
`d = −v·n` with v = vertex 0 for faces 0..3 and vertex 1 for face 4.

**CreateFrustrum2D `0x016d20d9`(position, wide).** The zoom mode `[0x0bdb5880]` selects the distances:

* modes 1..5: `s = width/640 + 0.1`, distance 2700, 3000, 3300, 3400, 3400, widths (1200, 540), (1300, 540),
  (1500, 580), (1600, 660), (1600, 660)·s;
* mode 0 uses the camera object: `s = width/640·k₁·k₂·k₃`, distance `2400·k₁·k₂·k₃`, widths 1190 and 540
  (1900 in 0x3f). World 0x8b's `s = 5` applies only outside scene states 3 and 5.

Offsets are `0.19·d` and `0.47·d` (0.35 in 0x3f). `wide` multiplies the widths by 1.51 and 1.2. The far edge is
lifted by `max(0, cos((71 + CameraAngle[0])°)·10 − 9.2)·d`, using 67° in worlds 0x86/0x8b. The polygon
`(−wf, far), (wf, far), (wn, near), (−wn, near)` is rotated by AngleMatrix(0, 0, 45), offset by the position and
scaled by 0.01 into `0x0b6b5400`/`0x0b6b5410`. Worlds 6 ("webzen" maps) and 0x49 use the camera angle instead
(not reconstructed). Before this, the routine re-applies the camera field of view when it changed, a side effect
outside this function.

**TestFrustrum2D `0x016ccce7`(x, y, range)** returns 1 at once in scene states 1..4 (`[0x01d1df70]`). Otherwise,
for each edge (i, j = i−1), `d = (X[i]−x)(Y[j]−y) − (X[j]−x)(Y[i]−y)`, and the test fails as soon as `range ≥ d`.
RenderTerrain walks 4×4 blocks over the box. A block is walked if TestFrustrum2D(bx+2, by+2, −80) passes and a
tile if TestFrustrum2D(x+0.5, y+0.5, 0) passes; top view `[0x0bdc58b7]` forces both. RenderTerrain also stores a
per-world texture offset in `[0x0b6b4ea8]`, which no routine in the captured text reads.

**Compared:** the 3D part in 200 cases (random modelview, aspect, far, fov, position; vertices, normals, planes
and box), the 2D part in 300 cases (camera singleton and screen width substituted; worlds 0, 2, 0x3f, 0x8b, 0x86,
0x8e, 0x22, 0x50; modes 0..5; `wide` both ways), TestFrustrum2D in 15,000 cases (plus its Python model;
negative control: wrong range sign), and RenderTerrain with live tests through the grass pass (20 boxes, plus
the `[0x0b6b4ea8]` store).

## 5. Decals (compared)

**RenderTerrainAlphaBitmap `0x016cdd5f`**(texture, x, y, size_x, size_y, light, rotation, alpha, height, follow,
flip) has 460 call sites. The most frequent constant textures are `Effect\flare01.jpg` 0x7ef7 (41 sites),
`flareBlue` 0x7fdd, `flareRed` 0x7fe0, `lightmarks` 0x8098, `flare03` 0x7f7a and `empact01` 0x8070. They are
loaded GL_LINEAR + GL_CLAMP (0x2900), so texture coordinates outside 0..1 do not repeat.

The routine first sets `glColor3fv(light)` when alpha == 1 (ucomiss), else `glColor4f(light, alpha)`, binds the
texture and builds AngleMatrix(0, 0, rotation). Let `n = (int)max(size_x, size_y) + 1`. For y, x in −n..n (float
counters) around `((int)(x/100), (int)(y/100))`, a tile is skipped when `0x016d2050` refuses it: index out of
range, attribute 0x200, or in world 0x8d attribute 8 or layer-1 tile 14. For each accepted tile, the corner
texture coordinates `((tu + x + {0,1})/size, (tv + y + {0,1})/size)` are moved by −0.5, rotated, stretched in u by
`size_x/size_y` and moved back. Then `0x016d197d` draws one GL_TRIANGLE_FAN with corners at terrain height +
`height` (follow) or at `height`, v flipped when `flip`. It sets no per-vertex colour, and the caller chooses the
blend state.

**Compared:** 300 calls (sizes 0.3..6, rotations, alpha 1 and < 1, follow/flip, worlds 0, 0x8e, 0x8d, off-map
centres): full GL streams equal, 18,840 fans.

## 6. Installed worlds

`--game-root` with `--installed-worlds 1,143,64,8` compares the full tile stream, both passes, of installed
Lorencia, Twisted Karutan, Vulcanus (world 63, lava) and Atlans (world 7, animated layer) with the new rules. It
uses graphics option 4 on every other tile, frame counter 7, and bitmap sizes as the native loader resolves them.
Every compared tile×pass stream is equal (verification table). Vulcanus has 530 cases on the border strip
(x or y ≥ 252) that use tile 12, whose bitmap `World64` does not ship. RenderTerrain never reaches that strip,
because the box is clamped to 251; the C reports these cases as unsupported.

## 7. Native mode

* `mu_world_frame_box` and `mu_world_add_light` follow the client order: copy over the box, then the sources.
  `mu_world_client_frustum` builds the CreateFrustrum box from a camera and the CreateFrustrum2D polygon around a
  hero position (zoom-mode table). `mu_world_draw_raster_view` draws with the client's tests.
  `mu_world_decal_raster` draws a decal under a chosen wrapper state. The animated-layer frames and TileBright
  are loaded with the world. The software rasterizer gained a clamp wrap for GL_CLAMP bitmaps.
* `mu-terrain render … --light X,Y,R,G,B,RANGE --decal X,Y,SIZE,ROT --detail 4 --frustum HX,HY [--zoom M
  --camera-angle D --view-far U --top-view] [--legacy]`.
* `mu-viewer --terrain`: L toggles lights, F the client frustum, K a decal under the focus point, 4 the graphics
  option; headless runs take `--lights --frustum --decal --detail N`. Headless GL and the software renderer
  agree, for example 0.3 % of pixels differ by more than 8/255 in a 960×600 Lorencia view with lights, frustum and
  decal.

These are viewer choices, not client readings: the frame counter follows the clock (one step per 40 ms); the
light sources and decal are demonstration inputs (the client's sources are objects, characters and effects); the
client-view camera uses yaw −45° and CameraAngle[0] −48.5 (an original-source value, not read from this client)
with `view_far = 3000`; the decal state is additive; TileBright is loaded in every world (the client loads it in
world 113).

Renders (local): `~/Documents/mu-mac-tools/native/renders/terrain2/{lorencia,twisted-karutan,vulcanus-lava,
atlans-water}/` with `before-*.png` (NATIVE-TERRAIN-001 build) and `after-*.png`. Before this milestone,
Vulcanus and Atlans drew no tile at all, because every face reached an unported branch.

## Verification

Final local run: `--scale-002 5` (synthetic) and `--installed-worlds 1,143,64,8 --installed-tiles 0`. The
NATIVE-TERRAIN-001 synthetic checks also pass, now with nothing unsupported (2,700/2,700 tile streams).

| Check | Cases | Bitwise equal |
|---|---:|---:|
| height selector `0x016c9868` with constructed handlers | 256 worlds | 256 |
| AddTerrainLight `0x016cacfc` (whole grid) | 800 | 800 |
| world tile streams, 36 worlds, both passes (679,893 GL calls, 371 particles) | 43,147 (+53 unsupported 0x2000 overlay faces) | 43,147 |
| Python model of the world rules / generic-rule negative controls | 2,100 | 2,100 equal / 185 scroll and 44 blend cases differ |
| AddTerrainLight negative controls (upper clamp / no lower clamp), of 200 | 200 | 196 / 189 differ |
| CreateFrustrum 3D part | 200 | 200 |
| CreateFrustrum2D | 300 | 300 |
| TestFrustrum2D | 15,000 | 15,000 |
| RenderTerrain with live frustum tests | 20 | 20 |
| decals `0x016cdd5f` | 300 | 300 |
| frame light copy (through `0x016ca4fa`) | 8 | 8 |
| installed Lorencia, every tile 0..254², both passes | 130,050 | 130,050 |
| installed Twisted Karutan | 130,050 | 130,050 |
| installed Vulcanus (lava) | 129,520 (+530 border-strip cases without a bitmap) | 129,520 |
| installed Atlans (animated layer) | 130,050 | 130,050 |
| installed height files through both client loops (24-bit by the resolved rule: 26 folders) | 55 + 27 | all |

Substitutions (labelled in the report): CRT `rand()` and CreateParticle in the world-0x22 water, the Chaos
Castle effect routine, the camera singleton and screen width in CreateFrustrum2D, `glGetFloatv`, the three
imports used by handler constructors, and the CRT feature bit. `glColor3f` is recorded like `glColor3fv`.

## Unresolved

* The 0x2000 overlay faces of worlds 0x71/0x91, the Chaos Castle per-face effects, the camera-angle 2D frustum of
  worlds 6 and 0x49, and the camera module's zoom/FOV state (mode selection, `[0x01cf1630]`, CameraAngle).
* Which object/character/effect sources add lights in a given scene (they need objects, which stay blocked, and
  actors).
* Fog and the alpha reference, as before.
