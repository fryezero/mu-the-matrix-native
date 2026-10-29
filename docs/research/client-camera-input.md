# Camera, picking, input and frame loop (NATIVE-FRAME-001)

This milestone recovers what a native client needs around the frame loop:

* the scene state machine that the frame driver dispatches;
* the in-world camera, its zoom and the GL matrices;
* mouse picking from the screen into the terrain;
* the keyboard and mouse input path, up to the click-to-move entry.

The camera, picking, input and timing routines are reconstructed in C under
[`reconstructed/camera`](../../reconstructed/camera/README.md). Their outputs are
compared bit for bit with the client's own instructions, executed in Unicorn
(`scripts/validate_camera.py`). A native SDL2 frame-loop skeleton in
[`native/`](../../native/README.md) uses them.

Each statement below is labelled. **Verified** means the C port equals the client's
instructions on every compared case. **Static** means a reading of decoded
instructions that was not executed. **Placeholder** means native code that is not client
behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09), 23,572,480 bytes | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10), 2,557,764 bytes | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Trig dispatch flag `0x0bdd1cc8` (value 1) | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |

The validator pins the bytes of every compared routine by SHA-256 (start, length and
digest are in `ROUTINES` and in its JSON report).

## 1. Scene state machine (static)

The scene dispatcher `0x01859d8a` switches on `[0x01d1df70]`
([frame loop](client-frame-loop.md)). These are the writers of that global, found as
direct `mov [0x01d1df70], imm` stores:

| Store | In | New state | Reading |
|---|---|---|---|
| `0x0185b1f1` | intro `0x0185ad63` | 3 | intro/logo done, go to login |
| `0x01857658` | scene-3 tick `0x01857236` | 5 | login and server accepted, go to character select |
| `0x0185a915` | `0x0185a75a` | 4 | start loading. Callers: character-select tick `0x01856e6c`/render `0x018576b3`, and `0x009a5197`, `0x00b4bd6c`, `0x01285814`, `0x0128590d` (inferred: map changes) |
| `0x01851ce9` | loading `0x01851adc` | 6 | loading done, in world |
| `0x01252ac9` / `0x01252c6d` | `0x0125294e`, called from `0x01287ead` | 5 / 3 | packet-driven return to character select / login (inference) |

The frame driver `0x01851d39` serves states 3, 5 and 6. It calls the per-scene logic
tick inside its 40 ms loop: 3 `0x01857236`, 5 `0x01856e6c`, 6 `0x0185613e`. It calls
the per-scene render once per frame: 3 `0x01857ed9`, 5 `0x018576b3`, 6 `0x0185916b`.
Every logic step first calls the key scan `0x00ec5475` (`0x01851d7c`).
`MoveMainCamera` runs from the renders, not from the logic step:

* in world, first in `0x0185916b` (`0x018591b6`);
* in the login and character-select scenes from `0x01857f14`/`0x018577ac`.

The in-world camera therefore smooths once per rendered frame.

## 2. Frame timing (verified)

`client_frame.c` ports the accumulator and the cap of `0x01851d39`. Two parts are
executed in the client for comparison:

* the frame start, `0x018524e7..0x0185250c`: the previous tick, `GetTickCount`, and
  `++frames`;
* the cap block, `0x0185265a..0x018526a0`: `elapsed = tick - previous`; when elapsed is
  below 40 the client calls `Sleep(40 - elapsed)`, adds the slept time to the tick and
  sets elapsed to 40; then `pending + elapsed` goes to the accumulator.

The comparison stubs GetTickCount and Sleep and records every Sleep argument. The
integer loop `while pending >= 40 { step; pending -= 40 }` was already
instruction-checked statically by `scripts/client_frame_static.py`.

## 3. Camera and projection

**Verified routines:**

| Routine | Address | What the port reproduces |
|---|---|---|
| glViewport2 | `0x01849ec4` | Screen rectangle globals; `glViewport(x, WindowHeight-(y+h), w, h)` |
| gluPerspective2 | `0x01849d76` | `gluPerspective` doubles; centres; per-pixel factors (below) |
| BeginOpengl | `0x0184adc7` | Up to its GetOpenGLMatrix call `0x0184b0c5`: unsigned 640x480 scaling; the exact GL call order and arguments; camera matrix read-back |
| GetOpenGLMatrix | `0x0184a569` | `m[r][c] = modelview[r + 4c]`, 3 rows |
| CreateScreenVector | `0x01849f08` | Mouse ray (below) |
| Projection | `0x0184a244` / `0x0184a3ce` / `0x0184a2e8` / `0x0184a455` | Integer 640x480; float pixels; float divided by 0.83 below 700 px height; TransformPosition |

**The globals.** WindowWidth `0x01cf1624` and WindowHeight `0x01cf1628` are unsigned.
The camera globals are:

* CameraFOV `0x01cf1634`, near `0x01cf162c`, far `0x01cf1630`;
* CameraAngle `0x0bdc58f0` (degrees), CameraPosition `0x0bdc5ab4`;
* the top-view byte `0x0bdc58b7`;
* CameraMatrix `0x0bdc5918`, row-major 3x4;
* MousePosition `0x0bdc5984` and MouseTarget `0x0bdc5990`;
* MouseX/MouseY `0x0bdc5ad8`/`0x0bdc5adc`, in 640x480 units.

**gluPerspective2** computes:

* `center_x = screen_w/2 + screen_x` and `center_y = screen_h/2 + screen_y`, both with
  C division;
* `center_y_flip = WindowWidth - center_y`. The client reads `0x01cf1624` here, the
  width, where the classic MU source uses the height. Only TransformPosition uses this
  value. The port keeps the client's choice.
* `t = tan(fov*0.5f*π'/180)`, where `π'` is the stored binary32 `0x40490fd8`
  (3.1415920), three ulps below binary32 π. The tangent goes through the wrapper
  `0x00a0cf72` (float → CRT double tan → float);
* `perspective_x = t/(screen_w/2)*aspect` and
  `perspective_y = t/(screen_h/2)*(WindowHeight/screen_h)`.

**BeginOpengl(x, y, w, h)** scales its 640x480 arguments with unsigned 32-bit
arithmetic. It then issues these calls:

* `glMatrixMode(PROJECTION)`, `glPushMatrix`, `glLoadIdentity`;
* viewport2;
* `gluPerspective2(fov, (float)w/(float)h, near, far*1.4f)`;
* `glMatrixMode(MODELVIEW)`, `glPushMatrix`, `glLoadIdentity`;
* `glRotatef(A1,0,1,0)`;
* `glRotatef(A0,1,0,0)` unless top view;
* `glRotatef(A2,0,0,1)`;
* `glTranslatef(-P)`;
* render state;
* `GetOpenGLMatrix(CameraMatrix)`.

The rest builds a frustum object at `0x0bdc5ae8` through `0x00a8d821`, from the
position, `-row2`, `row1`, `fov*0.0174533`, aspect, near and `far*1.4`. That part is
static and not ported.

**The GL matrices are not client code.** The client lets the driver compute the
rotations and the projection, then reads the modelview back. `client_camera.c` builds
them with the reference formulas, labelled as such: Mesa `_math_matrix_rotate`
axis-aligned branches, Mesa matmul order, and the Wine glu32/SGI `gluPerspective` with
`glMultMatrixd`. The native renderer loads these matrices directly.

Against this Mac's driver (Apple M5 legacy GL, `mu-frame-window --gl-check`, 2,000
camera states):

* the projection is within 2 ulp;
* the modelview differs by at most 0.0049 world units, in translations of order 1e4.

A probe found that Apple's glRotatef uses `sinf(angle*(float)(π/180))`: 20,000 of
20,000 single rotations matched. Apple's composition is neither binary32 nor binary64
Mesa order. It was not matched and is not needed by the port. The client's CameraMatrix
inherits whichever driver runs it.

**CreateScreenVector(sx, sy, out, fix)** computes:

* `sx' = (float)WindowWidth*sx/640` and `sy' = (float)WindowHeight*sy/480`;
* `p1 = ((sx'-cx)*F*px, -(sy'-cy)*F*py, -F)`, where F is the far plane when `fix`, else
  2000;
* `MousePosition = IRotate(-CameraMatrix[.][3])` (the eye);
* `out = MousePosition + IRotate(p1)`, through `VectorIRotate 0x00cfff3c` from
  record-math.

The in-world render calls it with `fix = 1` on MouseX/MouseY (`0x018597ba`), after
BeginOpengl.

## 4. In-world camera (verified, ordinary path)

`MoveMainCamera 0x0185498e` runs once per rendered frame. The port covers scene 6 in an
ordinary world:

* not top view (the top-view branch is ported too);
* no scripted camera object (`0x00988c5c()->+0x3c` = 0);
* not world 6 or 0x49;
* not the scene-3/5 camera tables.

The comparison runs the whole function in the client. Only the subsystem queries in
`CLIENT_STUBS` return synthetic values.

| Item | Value (client) |
|---|---|
| Yaw | `A[2] = -45`, set when the world is entered (`0x01856385`), never by input |
| Pitch | `A[0] = -48.5` (+ the zoom pitch drop) + `[0x0bdb588c]` (earthquake shake, 69 writers in effects) |
| Roll | `A[1] = 0` (world 5 adds `sin(t*0.0008)*2.5`; pitch `sin(t*0.0005)*2`) |
| Eye | `hero + IRotate((0,-CameraDistance,0), AngleMatrix(0,0,yaw))`, z = `hero.z + distance - 150` (water tiles flag 0x40: z from 1201). The eye sits at +x/-y of the hero |
| Lift | Tiles with flag 0x80 raise `[0x0bdc5978]` by 10 per frame up to 210 and add `IRotate((0,lift,0), yaw -45)` |
| Distance | CameraDistance `0x0bdc5ef0` follows target `0x01cf1860` as `d += (t - d)/3` **after** the eye is placed. Target by zoom level `0x0bdc5b84`: 1000/1100/1200/1300/1400/object +0x68. Outside the zoom-object mode the level is 0, so distance 1000 |
| Far | Level 0: `2000 * info.f1c * info.f18 * info.f10` (2400 in scenes 3/5, 2300 in one object mode); levels 1-5: 2500/2600/2950/3200/3200; world 0x33: 3220; event worlds: 3700; worlds 0x5b/0x5c for hero byte 1: 3000; projection far = `far*1.4` |
| Near | `[0x01cf162c]`, set outside these routines |
| FOV | The world FOV comes from world data (`0x0098647b()->+0xc->+0x20`). Scenes other than 6 and worlds 6, 0x45..0x4a always use it (`0x01851a7f`) |

**Zoom (verified).**

* **The wheel.** The window procedure passes `(short)HIWORD(wParam)/40.0f` to
  `0x018588d9`. That handler acts only when the zoom is settled (`[0x0bdc5ed8]` = 1),
  window 0x3e is closed, and the world is outside a list (`0x00da9d49`, world 0x8b only). Wheel up lowers
  the index `0x0bdc5914`, down raises it. The message reaches that case only after the UI layer
  `0x00aefb79` declines it (base.swf hit test, GFx dispatch, chat `InMouseViewBox`, GFx input flag); the whole
  route is reconstructed in `client_wheel.c` (RENDER-TIME-003, [client-render-time.md](client-render-time.md#zoom-refusal-and-visible-objects-render-time-003-2026-10-28)).
* **Levels.** `0x0185a9bf` clamps the index to `[min, 2]` over the FOV table
  {20, 30, world FOV}. min is 1 for hero class value 2 or skill ids 0x185d, 0x185e and
  0x1833..0x1836, else 0. The table holds two more entries, 50 and 65, that the count 3
  never reaches.
* **The transition.** Duration 500 ms of GetTickCount (timer `0x0bdc5ed0`: start,
  duration, done). The pitch target is `-48.5 - lerp(0, 30.8, (int)(worldFOV-FOV), 26)`.
  The height target is `(dist - 150 + hero.z) - lerp(0, 580, …, 26)`. The ease is
  `0x018504c6`, constant deceleration.
* **Result.** For a world FOV of 35, zooming in gives FOV 30 at pitch -54.42 and 111.5 units
  lower, or FOV 20 at pitch -66.27 and 335 units lower. That is the client's zoom limit.

## 5. Picking (verified)

Click-to-move (static, below) calls `RenderTerrain(1)` at `0x016cd468`. That resets the
nearest-hit value `0x0bdc58c8` to 9999999 (`0x0184f957`) and walks the visible tiles.
For each tile it calls `RenderTerrainTile 0x016ccda5` with Flag = 1:

* **Corners.** The four corners are `(xf*100 [+100], yf*100 [+100], height[(x[+lod], y[+lod])])`.
  The tile index is `y*256 + x`, with no wrap and no bounds. Height `0x0b6f5420`
  (float), wall flags `0x0b795420` (uint16). The +100 ignores lod. A corner on a water
  tile (flag 0x40) uses `[0x01cf15dc]`.
* **Faces.** `FaceNormalize 0x00d01206(v0,v1,v2)` is a binary32 cross product, divided
  in binary64 by `(double)(float)sqrt(len²)`. Then
  `CollisionDetectLineToFace 0x0184f96c(MousePosition, MouseTarget, 3, v0,v1,v2,v3, N, 1)`.
  On a miss it retries with `(v0,v2,v3)` and the vertex order v0,v2,v3,v1.
* **Collision.** `t = -(N·O - N·a)/N·(T-O)` must satisfy `0 <= t <= nearest`. The point
  `X = (T-O)*t + O` must lie within the segment's range on the two axes other than the
  one with the smallest |dir|. Then `InsideTest 0x018506bc` runs on the plane of the
  first normal component with |n| >= 0.5, testing x, then y, then z. When the component
  is positive the edge sign test flips (axis << 3). On success it stores `nearest = t`
  and CollisionPosition `0x0bdc58e4 = X`.
* **Selection.** A hit sets SelectFlag `0x0b5e3ea6` and SelectXF/YF `0x0b7f5420/4`.

**The target (static).** `0x016a5063` re-tests the selected tile, then sets:

* TargetX/Y `0x0b449ac0/4` = `(int)(CollisionPosition/100)`;
* `0x0b449ac8/c` = `(int)CollisionPosition`.

`mu_terrain_pick` iterates a tile rectangle with the same per-tile code. The client's
4x4-block frustum walk `0x016d2e8e` was not ported. It only changes which tile wins an
exact tie in t.

The ray is the one built in the previous render pass. A click is handled in the next
logic step with the ray of the last frame, so the cursor position at the last render
counts.

## 6. Input

**Window procedure (static).**

* **Registration.** `RegisterClassExW` (`0x012115ad`) registers `0x10b7d5f0`, inside
  IGC.dll. That wrapper is opaque and was not analysed.
* **The game procedure** is `0x0120fee3`. It first offers messages to the UI
  (`0x00ac9995`, `0x00c622fa`) and then handles them itself.

**Mouse globals (verified, message cases executed as instruction ranges):**

| Message | Effect |
|---|---|
| WM_MOUSEMOVE | `MouseX = cvtt((short)LOWORD(lParam) / [0x06fbcd94])`, `MouseY` likewise with `[0x06fbcd98]` (window/640, window/480); clamped to 0..640 and 0..480 after the UI calls |
| WM_LBUTTONDOWN | idle `0x06fc9e4c` = 0, LPop `0x0bdc5983` = 0, LPush `0x0bdc599c` = 1 if not held, LButton `0x0bdc5981` = 1, SetCapture |
| WM_LBUTTONUP | LPush = 0, LPop = 1 (always), LButton = 0, last click = MouseX/Y (`0x06fc9e58/5c`), ReleaseCapture |
| WM_RBUTTONDOWN/UP | `0x0bdc599d` held, `0x0bdc599f` push, `0x0bdc599e` pop (pop only if it was held) |
| WM_MBUTTONDOWN/UP | `0x0bdc59a1` held, `0x0bdc59a3` push, `0x0bdc59a2` pop |
| WM_LBUTTONDBLCLK | `0x0bdc59a0` = 1 |
| WM_MOUSEWHEEL | Camera zoom with delta/40 when the UI does not take it; MouseWheel `0x0bdc59a4` = `(short)HIWORD(wParam)/120` |
| WM_KEYDOWN/UP | `0x0bdc5982` = 1/0 |

The left and right button cases first return when the hero byte `+0x190` > 0 or the UI
holds the mouse (`0x00abed56`). The ranges compared start after those guards.

**Keyboard (verified).** The keyboard is polled: `CNewKeyInput` at `0x01ec91c0` holds
256 states and is scanned once per logic step by `0x00ec5475` with
`GetAsyncKeyState(vk) & 0x8000`, provided `GetForegroundWindow()` is the game window
`0x06fc9c94` and the active byte `0x06fc9cb5` is set.

* **Transitions.** NONE/RELEASE → PRESS → REPEAT; up: REPEAT/PRESS → RELEASE → NONE.
* **Esc and Tab** do not change while no WM_KEYDOWN is pending and the focus is the
  foreground window.
* **Queries.** `0x00ec5577/ac/e2/0x00ec5618` (wrappers `0x00ec537f`, `0x00ec5393`,
  `0x00ec53a7`, `0x00ec53bb`) test for state 0/1/2/3 and are false while inactive.
* **Mouse buttons are polled too.** `CInput 0x00cc36cc` reads VK 1, 2 and 4 through
  the same table. The double click compares the QPC timer with GetDoubleClickTime.

**Key bindings (static, call sites of the four queries; 195 functions).**

* **In-world dispatcher** `0x00efbfd0`. Most letter keys open UI panels through
  `0x00c714bd(id)`: Y 0x0d, I 0x0e, C 0x10/1, Q 0x10, W 0x11, E 0x12, R 0x13, Z 0x14,
  X 0x15/0, T 2, M 4, O 5, J 6, P 7, F 9, G 0x0a, B 0x0b, N 0x0c, K 0x0f. Others are V,
  S, A, H, U, D, Tab, Home, End, `[`, `]`, and Alt/Ctrl/Shift modifiers.
* **Other keys.**
  * Digits 1..0: `0x00be808b` (skill hotkeys, inference).
  * Esc closes windows: about 100 UI functions.
  * Enter: chat.
  * Arrows: list widgets `0x011b6426..`.
  * Space: `0x00efd9ab`.
  * F1: `0x00f0736c`, `0x00f24f38`.
* Panel names are not recovered. The S6 conventions (I inventory, C character, …)
  are inference only.

**Click-to-move entry (static).**

* `MoveHero 0x016a9150` is called from the in-world tick at `0x01856d3a`.
* With the left button pushed and Shift not held (`0x016ac4b4`), it runs
  `RenderTerrain(1)` and the tile test.
* A hit, with hero flag `+0x3254`, sets TargetX/Y from CollisionPosition/100
  (`0x016ac544..`) and continues into movement.
* Alt (`0x0107e99a`) goes through `0x016a5063`, which prefers a character under the
  cursor (`0x01cf1154`).
* Path finding and the move packet were not traced here; path finding and following are now in
  [client-path.md](client-path.md) (the move packet stays untraced).

## Verification

`scripts/validate_camera.py` builds `reconstructed/camera`. It maps:

* the restored text and the second section (both unchanged), plus the flag;
* zeroed BSS ranges with a definedness shadow;
* a TEB and a GDT for the SEH prologues' `fs:[0]`.

A case stops at the first read of a byte that neither the harness nor the guest wrote.
`and [m],0` and `or [m],-1`, which MSVC uses to initialise locals, count as stores.
Imports are recorded stubs. Each of the 16 client callees replaced in MoveMainCamera and
zoom runs is listed with its reason.

Two synthetic inputs remain:

* the CRT math mode word `0x0bdcfbc8`, alternated between 0 and 1. With the default
  control word both values return the same result. NaN-length cases use 1, because
  mode 0 enters the CRT's errno path.
* the /GS cookie `0x01cf65c0`, any value.

NaN results count as equal regardless of payload, since x86 and arm64 generate
different default NaNs.

**Result at `--cases 1000`** (seeded, 64 s on one core): **33,250 comparisons, 0
mismatches** in 23 families:

| Family | Cases |
|---|---|
| viewport2, perspective2, BeginOpengl, CreateScreenVector, each projection helper | 1,000 each |
| FaceNormalize | 1,000 |
| InsideTest | 2,000 |
| CollisionDetectLineToFace | 4,000 (330 hits) |
| RenderTerrainTile pick | 2,000 (551 hits) |
| lerp, ease, timer elapsed, timer update | 1,000 each |
| MoveMainCamera | 2,000 |
| Wheel zoom | 1,000 |
| Key scan steps, key queries | 250, 6,000 |
| WM_MOUSEMOVE, mouse messages, frame start and cap | 1,000 each |

Host libm `sin`/`cos`/`tan` agreed with the client's CRT trig in every MoveMainCamera,
zoom and perspective case. The trig substitution is still a property of these domains,
not a proof.

**Mutation check (`--mutations`).** Eleven plausible mistakes were each detected:

* the MU-source `center_y_flip` from the height;
* exact binary32 π;
* `t < nearest`;
* a strict InsideTest;
* a binary64 face length;
* NaN converted to 0;
* a height offset of 100;
* a strict ease end;
* no Tab exception;
* a cap at `<= 40`;
* an unconditional right pop.

**Tests.**

* **Portable** (`make test`): `reconstructed/camera/test_client_camera.py` (10 analytic
  checks) and `native/tests/test_native_frame.py`.
* **Private** (`MU_RECOVERY_INTEGRATION=1`): the instruction comparison at 60 cases plus
  mutations, and a frame-loop run with an installed model.

## Native skeleton

`native/core/mu_frame.c` (with `mu-frame` headless and `mu-frame-window` SDL2) runs:

* **logic** in 40 ms steps from the client accumulator; the key scan first;
* **the left click** (pushed or held, Shift up): picking with the last ray, target
  tile;
* **the hero walk** (placeholder: straight line, 15 units per step);
* **render**: frame tick, MoveMainCamera, BeginOpengl(0,0,640,480), CreateScreenVector;
* **draw**: flat placeholder terrain, model, target marker;
* **cap**: Sleep(40 - elapsed).

Window messages are translated from SDL (mouse in drawable pixels, wheel ×120), keys
through USB HID usage → VK. The world FOV 35 and near 20 are the classic MU source
defaults; they are placeholders until the world data is decoded.

**Local runs.**

* The window ran at 24.3 FPS over 3 s (cap 25) with 74 logic steps.
* Headless renders are under `~/Documents/mu-mac-tools/native/renders/frame/`:
  * `box/` and `monster02/`: software raster, 800x600, scripted clicks and wheel zoom
    35→30→20→30→35;
  * `gl/`: CGL, 1024x768, Monster02.

## Unresolved

* The scene-3/5 camera tables, world 6 and 0x49, the scripted camera object, top-view
  input and the frustum object `0x00a8d821`.
* The world FOV and near-plane sources (world data), and WindowWidth/scale setup.
* The tile walk order of `0x016d2e8e`, and character picking (`0x01cf1154`, OBB tests).
* MoveHero beyond target selection (path finding, move packet, walk speed), and the
  hotkey panel names.
* The IGC.dll window-procedure wrapper (out of scope).
