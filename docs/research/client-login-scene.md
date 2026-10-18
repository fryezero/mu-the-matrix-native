# The login scene's 3D world (NATIVE-LOGIN-001)

NATIVE-SHELL-001 ([scene manager](client-scene-manager.md)) found that the login scene (SceneFlag 3) opens world
`0x5e` (folder World95), but `mu-client` drew the login overlay and the server list over black. This milestone
recovers the 3D part of the scene and draws it natively:

* which world, camera and per-frame work the scene uses;
* the login world's object handler class `CGMLogInScene_Ex` and the after-character pass that draws the ship's
  glow meshes;
* the object placements, read from our own client at the server-select screen;
* `mu-client` and `mu-render ui login|servers --scene` draw the world behind the 2D layer.

Labels:

* **verified**: the client's instructions ran in Unicorn and matched the reconstruction on every compared case;
* **live**: compared with memory read from a running client this project started (read-only, plain game memory);
* **static**: read from decoded instructions, not executed;
* **stand-in**: native code where the client's subsystem is not reconstructed.

Inputs are the pinned restored text (`2bd5f2e9…3724`) and second image section (`c985e2e6…672f`). Every executed
routine is pinned by SHA-256 in `scripts/validate_scene.py` (`PINNED_JSON`) and `scripts/validate_login_world.py`
(`PINNED`). Names are ours.

## 1. World and files (verified, static)

The creation `0x01851804` (verified in NATIVE-SHELL-001) sets world `0x5e` and calls OpenWorld. For this world
OpenWorld loads (static):

* `Data/World95/EncTerrain95.map/.att`, `TerrainHeight.OZB`, the tiles (a small patch: 46,147 of 65,536 cells have no
  ground; the sea is terrain);
* `EncTerrain95.obj`, 47 records in 30-byte version-0 layout (installed bytes do not decode in the captured code,
  [objects](client-objects.md));
* `Object95\HSSailboat04_R.jpg` as bitmap `0x817c` (`0x01828f9d`, only for world `0x5e`);
* `Camera_Angle_Position.bmd` (the camera record);
* no camera-walk script: `Data\%s\CWScript%d.cws` is loaded only for world `0x49` (the old World74 login scene,
  `0x01828a6d`), and MoveMainCamera's tour branch tests world `0x49` too (`0x018549b5`).

The object model pass `0x018392db` loads the generic `Data\Object95\Object<t+1>.bmd` for types 0..299 and no extra
models for this world (verified with `validate_objects.py`'s model-pass machine). The visible models:

| Type | File | Content (observed) |
|---:|---|---|
| 1 | `Object02.bmd` (`so_water01`, `sowater01_R.jpg`) | ship wakes |
| 2 | `Object03.bmd` (`so_cloud03.jpg`) | sky plane |
| 5 | `Object06.bmd` (`HS_SB02`, 30 meshes) | the foreground ship with the gold knight statue and crystals |
| 12, 13 | `Object13/14.bmd` | the far ship, the island with the light beam |
| 29 | `Object30.bmd` (`HS_Goose`) | the flying geese |
| 38, 54 | | invisible markers (HiddenMesh −2) that emit mist and spray particles |

## 2. Camera (verified, live)

MoveMainCamera `0x0185498e` takes the world record in scenes 3 and 5 (verified in NATIVE-CHARSEL-001,
`validate_camera.py`). World95's record: angle (−84.5, 0, −45), position (24475.797, 7581.581, 1834.540), FOV 35,
Distance 32.1, Z_Distance 0.324999. So the login camera is **fixed**; nothing in the scene animates it.

The render computes CameraViewFar `[0x01cf1630]` through `0x0098ac45(2400)`: `2400 · Distance · Z_Distance ·
manager[+0x10]` (binary32, in that order; verified as client code inside the render family).

**Live (2026-10-18, objread globals):** CameraAngle `[0x0bdc58f0]` = (−84.5, 0, −45), CameraPosition `[0x0bdc5ab4]`
= (24475.796875, 7581.5810546875, 1834.5399169921875), CameraFOV = 35, CameraViewFar = 25037.923828125, which equals
the reconstruction with manager scale 1.0 bit for bit. The native session reports the same four values.

## 3. Tick and render (verified)

**Tick head** `0x01857236..0x01857322` (`mu_scenemgr_login_tick_head`): the creation on the first step; unless the
credit window (CUIMng+0x4648, byte +0xc) is open: the frame-light copy `0x016ca4fa`, MoveObjects `0x016d82c7`,
`0x00c9e24a`, `0x01537a43` (ecx `0x0a3a0e28`), MoveCharacters `0x0137a7ce`, `0x009c104e(1)->0x0106bcc5` (which pops
the getter's argument word as its own), MoveEffects `0x0150ddb1` (pool `0x0a4ca430`), `0x01589b06`, `0x0159122d`
(ecx `0x0a3a9adc`), `0x009c104e(0)->0x0106bcc5`, `0x00c9eb04`, `0x00b990b0()->0x00eb0d64`,
`0x009c2aea()->0x009b9913`, the GFx update `0x00ac9613(SceneFlag)` and MoveCharacterCamera `0x01854529`. With the
credit window open the client goes on with a GFx branch at `0x01857448` (not reconstructed).

**Render 3D part** `0x01857ed9..0x0185810e` (`mu_scenemgr_login_render_3d`): returns 0 before InitLogIn; clears the
fog byte; MoveMainCamera; `glColor3f(1,1,1)`; `glClearColor(0,0,0,1)`; **BeginOpengl(0, 0, 640, 480)**;
**CreateFrustrum(width/640, record position, 0)**; unless the credit window is open: CameraViewFar,
**RenderTerrain(0)**, RenderCharacters `0x0137a3c2`, `0x00c9e4e3`, **RenderObjects** `0x016d5020`, `0x01589b56(0)`,
RenderEffects `0x015181fa`, `0x01692887`, `0x01538145`, `0x00c9fd8d(0)`, **RenderObjects_AfterCharacter**
`0x016d6949`, `0x00b990b0()->0x00eb0dee`; then the identity push, RenderSprites `0x0169270e(0)` (ecx `0x0a3da070`),
RenderParticles `0x0159123f(0)`, the pop and **BeginBitmap**. The 2D part that follows is NATIVE-UI-001's verified
login overlay (logo fade, copyright and version lines). So the 3D world is drawn first and the overlay, the server
window (CUIMng) and the cursor on top of it, in the same frame.

The names of the unnamed callees (`0x00c9e4e3`/`0x00c9e24a`, `0x00c9fd8d`/`0x00c9eb04`, `0x01589b56`/`0x01589b06`,
`0x01692887`, `0x01538145`) are not established; by their neighbours they are the boid, fish, blur and joint
passes (static guess). The login world creates no joints or effects through the code reconstructed here.

**Verified:** `scripts/validate_scene.py` (recording stubs for every callee, the far-plane leaf as client code, the
CreateFrustrum vector compared by value): 1,000 + 1,000 cases, 0 mismatches (the 3D block ran in 400 and 736 of
them), and both new planted mistakes detected.

## 4. CGMLogInScene_Ex (verified, live)

The world handler of world `0x5e` is `CGMLogInScene_Ex` (RTTI `.?AVCGMLogInScene_Ex@@`, complete object locator
`0x01be35bc`, vtable `0x01aaa874`, base BaseMap). It overrides five slots; each starts with `0x00e24993`
(`[0x01cf15fc] == 0x5e`). `reconstructed/objects/login_world.c`:

| Slot | Routine | Called from | What it does |
|---|---|---|---|
| 0x2c | `0x00e24a4d` | CreateObject (world manager `0x00ea2ad6`) | type 5: action 0 PlaySpeed of model 5 = 0.23 (`0x00eaaa44(type, action)+4`); types 0x26, 0x36: HiddenMesh −2; all others: range −428.571442 |
| 0x30 | `0x00e24acd` | MoveObject (world manager `0x00ea2c2b`) | type 1: blend v −= 0.005 per step; type 0xd: blend light = pulse(0.2, 0.6, 0.001) |
| 0x34 | `0x00e24be1` | RenderObjectVisual `0x017f9758` (wrapper `0x00ea2dc1`) | type 5: six lantern blocks on bones 37 and 98, ten CreateSprite calls (Shiny02 `0x7f67`, flare01 `0x7ef7`; light (1, 0.3, 0) / (0.2, 0.5, 0.8)); type 0x26: on `rand()%6 == 0` CreateParticle(clouds `0x7f89`, sub 0x14, owner); type 0x36: on `rand()%2 == 0` CreateParticle(WATERFALL1 `0x801a`, sub 2) |
| 0x38 | `0x00e254bb` | the custom render `0x017f76ec` (wrapper `0x00ea2f07`) | types 1, 2, 3, 7, 8, 0xa, 0xb, 0xc, 0x12..0x14, 0x1d, 0x37, 0x38: RenderBody(2, …) and +0xa = 0; types 5 and 0xd: the same and **+0xa = 1**; returns handled |
| 0x3c | `0x00e25639` | the after-character draw `0x016d67c7` (wrapper `0x00ea306c`) | type 5: 16 RenderMesh calls: mesh 0x12 with the sail texture `0x817c`, mesh 2 three times (pulse light, `0x817c`, Chrome01 `0x7f1f` with flags 0x46), alpha 0.7 and colour (0.8, 0.7, 0.3) for meshes 0 and 0x18..0x1c (flags 0x42, then 0x44 with Chrome01: the gold statue and the crystals), then alpha 1 and colour 1; type 0xd: mesh 0x16 |

The pulse `0x00cfec8d(lo, hi, speed)` is `(1 − |sin(timeGetTime · speed)|) · (hi − lo) + lo`, with the unsigned
time converted through double, the C runtime sin on the widened product and fabs.

**RenderObjects_AfterCharacter** `0x016d6949` runs in this world (it is in its world list). For each sector it
recomputes the sector visibility (TestFrustrum2D, range −180) and, for live objects with +0xa == 1 in a visible
sector (or top view), sets +0xb from the object test and draws `0x016d6791`: the RenderObject setup and then slot
0x3c. The first-draw predicate `0x017fe909` has no world 0x5e case; its default asks the world manager's handler
slot 0x14, which `CGMLogInScene_Ex` inherits from BaseMap (`0x00d5cbd6`, returns 0). The validator executes that
real dispatch through the image's vtable.

**Verified:** `scripts/validate_login_world.py --cases 2000 --mutations`:

| Family | Cases | Equal | Notes |
|---|---:|---:|---|
| create (CreateObject world 0x5e + slot 0x2c) | 2,000 | 2,000 | object bytes, sector links, the action-table write |
| move (MoveObject world 0x5e + slot 0x30) | 2,000 | 2,000 | slot ran in 1,714; the pulse and the C runtime sin as client code |
| visual (slot 0x34) | 2,000 | 2,000 | 7,430 sprites, 325 particles |
| custom (slot 0x38) | 2,000 | 2,000 | 1,676 handled |
| after (slot 0x3c) | 2,000 | 2,000 | 16,607 RenderMesh calls, colour writes |
| after_pass (`0x016d6949`) | 2,000 | 2,000 | 11,242 draws |

9 of 9 planted mistakes were detected. As for Tormenta in NATIVE-OBJECTS-002, the world-group hooks of the default
chains and the world-manager registry are stubbed; the slots are reached by reading the vtable (static).

**Live:** with the world `0x5e` creation now reconstructed, `scripts/live_object_state.py` finds all 47 objects of
both login snapshots (2026-10-17 and 2026-10-18) equal to `mu_obj_create`, excluding only the values the handler
drives at runtime. Those values match the reconstruction too: between two snapshots 1,032 ms apart (25.8 logic
steps) type 1's blend v moved by 0.130 (26 × 0.005), the ship's frame advanced by 5.98 (26 × 0.23), type 0xd's
blend light was 0.24 (inside 0.2..0.6), and types 5 and 0xd carry +0xa = 1. The body-light copies `+0x1e8` of the
native session equal the live ones for every object (the three NaN records at (0, 0) aside).

## 5. Placements (live)

The owner authorized a read-only live read. It followed `GAME-LOCK.md`: lock held 14:32:30–14:34:36 on
2026-10-18; `mu-to-server.sh` started the play bottle's client to the server-select screen (no account login, no
character); three objread snapshots (14:33:41, :43, :46) and two window-only screenshots; then the client was closed
with taskkill (WM_CLOSE) and the launcher with its own X button (muinput click). `objread` gained an optional third
argument that copies seven scene globals (camera, FOV, far plane, SceneFlag, WorldTime, the overlay fade).

The snapshots hold world 94 (= 0x5e), 47 objects in the sectors and the count global 47, the same 47 records as the
2026-10-17 read, so `EncTerrain95.plain` from NATIVE-OBJECTS-001 is unchanged. Snapshots and screenshots stay local
(`~/Documents/mu-mac-tools/native/scratch/login/live/`, `renders/login/live/`).

## 6. Native

* `native/core/mu_login.{h,c}`: the session (World95, the camera record through `mu_move_main_camera` scene 3,
  BeginOpengl 640×480, the client frustum, the objects runtime), a logic step (frame-light copy over the last
  frustum box + 3 tiles, MoveObjects) and the software draw in the render's order.
* `native/core/mu_objects_runtime.c`: world `0x5e` in the lifecycle (PlaySpeed from the creation log, the move
  clock, the custom render's RenderBody, RenderObjectVisual's sprites and particles, the after-character pass with
  RenderMesh per mesh). It now also passes RenderObject's Transform light arguments (ambient 0.4, scale `+0xe4`,
  minimum `+0xe8`; compared in NATIVE-OBJECTS-002's render family) instead of the default wrapper's 0.4/0.4/0.4; this
  brightens lit objects in every world (the sky plane by 1.5×).
* `native/login/login_gl.c`: the same passes in OpenGL for `mu-client`.
* `mu-client`: the shell runs `mu_scenemgr_login_tick_head` (its MoveObjects call steps the session) and
  `mu_scenemgr_login_render_3d` (its host answers the camera-record manager from the session's record), and the front
  end draws the 3D view under the overlay. `--login-objects DIR` (or `--objects-dir DIR` for all three scenes).
* `mu-render ui login|servers --scene [--objects-dir DIR] [--steps N] [--no-ui]`.

Stand-ins: sprites and particles are additive billboards of the client's bitmaps (CreateSprite `0x01692eb7` and
CreateParticle `0x0168fafd` are not reconstructed; size = bitmap width/2 × scale); the bone positions of the
lanterns use the native pose (body scale and origin applied after the bone matrix; the client poses static objects
with them inside the bones); texture `0x817c` binds the ship's own `HSSailboat04_R.jpg` slot (the client's bitmap is
GL_LINEAR/GL_CLAMP, the model slot GL_NEAREST/GL_REPEAT).

**Comparison with the live screenshot** (1722×1048 client area, `renders/login/compare-soft.png`): composition,
ship, island, far ship and wakes coincide. Mean colours: the sea (terrain) within 3% (5.8/40.8/69.6 vs
5.9/40.7/69.1), the sky plane 1.6× darker than live, the ship hull 1.4× brighter, the island beam 0.7×. The body
light inputs are equal (section 4), so the remaining difference is in the vertex lighting or blending of these
meshes (light direction inputs, not traced).

Local renders (not committed), `~/Documents/mu-mac-tools/native/renders/login/`:

* `scene-soft-noui.png`: the 3D part alone, software, after 25 steps;
* `servers-scene-soft.png`: `mu-render ui servers --scene`;
* `client-gl-servers.png`, `client-gl-anim.gif`, `client-gl-anim-strip.png`: `mu-client` headless GL (the ship rocks,
  the geese fly, the beam pulses);
* `compare-soft.png`, `compare-client-gl.png`: live (top) over native (bottom);
* `live/login-client*.png`: the window-only captures;
* `terrain-size-check/`: the side task below.

## 7. Side task: pale terrain at 1280×800

NATIVE-OBJECTS-002 reported pale terrain patches and grey grass in headless renders at 1280×800 that disappear at
1600×1000. On this branch (main `b92488a` plus this work) the effect did not reproduce: `mu-world` Lorencia 147,137
(GL and software, 3 and 12 frames, zoomed), Tormenta 135,10 and 140,30 (GL, 3 and 30 frames) and `mu-terrain
render` give the same images at both sizes apart from scale (`renders/login/terrain-size-check/`). Without the
original command line the cause was not found; it remains open.

## Tests

* Portable: `reconstructed/objects/test_login_world.py` (worked examples of every slot, the pulse and the
  after pass), `reconstructed/scene/test_scene.py` (render 3D order, far plane, credit window, tick head),
  `native/tests/test_native_login.py` (a synthetic World95 tree with models and a plaintext: camera record, far
  plane, creation hooks, after-character objects, lantern sprites, determinism; `mu-shell` draws the world behind
  the server list).
* Private: `tests/test_login_world_private.py` (the Unicorn validator; the live snapshots with
  `MU_LOGIN_DUMP_DIR`), `native/tests/test_native_login.py` `InstalledLoginSceneTests` (`MU_GAME_ROOT`,
  `MU_OBJECTS_PLAIN_DIR`: camera and far plane equal to the live read, 47 objects, 2 after-character objects,
  10 sprites), `validate_scene.py --only login_render login_tick_head`.

## NATIVE-JOINT-001

The stand-ins are gone: the lantern sprites go through CreateSprite/RenderSprites and the mist (clouds `0x7f89`
subtype 0x14, owner = the marker) and spray (WATERFALL1 `0x801a` subtype 2) through CreateParticle/MoveParticles/
RenderParticles of the reconstructed particle module (verified kinds, [client-joints.md](client-joints.md)); the
tick head moves the particles, the render ends the 3D part with RenderSprites(0) and RenderParticles(0). The report's
`sprites` is the CreateSprite count of the last RenderObjects pass, `particles` the live particles.

## Limits and next steps

* The sprite and particle systems were stand-ins until NATIVE-JOINT-001 (above).
* The sky and ship brightness differ from the live capture (section 6).
* The credit-window branch of the tick and the GFx parts of the scene (MENU, CREDIT, the account dialog).
* The unnamed passes of section 3 (boids, fishes, blurs, joints) are not ported; the geese are static objects of
  this world.
* The pale-terrain report could not be reproduced (section 7).
