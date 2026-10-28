# The character-select scene (NATIVE-CHARSEL-001)

This milestone recovers the client's character-select screen, scene state 5:

* the 3D scene: which world it loads, its camera, where the characters stand, how they animate and how the
  selected one is highlighted;
* its 2D layer: the legacy window `CCharSelMainWin` and the boundary to the GFx (Scaleform) parts;
* how the character list (class, level, name, equipment) becomes the characters on screen. The list is the
  server's data; here it is a synthetic input, and no packet is traced.

The client routines are reconstructed in C (`reconstructed/charsel`, `reconstructed/ui/ui_charsel.c`, the scene
3/5 path of `reconstructed/camera`) and compared with the client's instructions in Unicorn. The native session
`native/core/mu_charsel` and the tools `mu-charsel`, `mu-render charsel` and `mu-charsel-window` render the scene
on macOS arm64 with up to five synthetic characters.

Labels:

* **verified**: the client's instructions ran in Unicorn and matched the reconstruction on every compared case;
* **live**: compared with a window-only capture of the running game;
* **static**: read from decoded instructions, not executed;
* **placeholder**: native code standing in for data the client has and this work does not.

Pinned inputs: restored text capture09 (`2bd5f2e9…3724`) and second section run10 (`c985e2e6…672f`). The
validators pin every executed routine by SHA-256 (`scripts/validate_charsel.py` `PINNED`).

## 1. Scene flow (static)

The frame driver serves scene 5 with the logic tick `0x01856e6c` and the render `0x018576b3`
([camera and input](client-camera-input.md)).

**Creation.** The first tick sets InitCharacterScene `0x0bdc5ca2` and calls CreateCharacterScene `0x01851540`:

* world index `0x5d` (`0x01cf15fc`, `0x01cf1600`), OpenWorld `0x0182876e` → folder **World94**;
* OpenCharacterSceneData `0x0182a553`: the window textures (`Interface\deco.tga` 0x7b10, `b_create.tga`
  0x7b11, `server_menu_b_all.tga` 0x7b12, `b_connect.tga` 0x7b13, `b_delete.tga` 0x7b14, `character_ex.tga`,
  the `server_ex*` frame), `Logo\chasellight.jpg` 0x8022 and the `Logo`/`NewFace` models;
* the creation-preview character `0xa39d780` (CreateCharacter with model 0x136);
* SelectedHero `0x01cf1864` = -1;
* `CUIMng::CreateCharacterScene` `0x011e2f2a` (section 5);
* for each of CharactersClient 0..9 the world handler's SetCharacterPosition (section 3), then a GFx call that
  depends on whether any character exists (`0x00b4b82c` / `0x00b4b927`).

**Tick** (`0x01856e6c`, verified, section 6): the terrain frame update `0x016ca4fa`, MoveCharacters
`0x0137a7ce` (the animation step), effect and UI updates, the GFx manager update, MoveCharacterCamera
`0x01854529`, then the Enter and Esc keys.

**Render** (`0x018576b3`, verified, section 4): MoveMainCamera, BeginOpengl(0, 0, width, 480), CreateFrustrum,
CreateScreenVector, then the scene.

## 2. World and camera (verified)

MoveMainCamera `0x0185498e` has a branch for scenes 5 and 3 (`0x018553f3`, `0x0185555a`). After the in-world
position is computed, the branch replaces CameraAngle (all three components) and CameraPosition with the world
camera record (`0x0098647b()->+0xc`: angle `+0`, position `+0xc`). It skips the pitch and zoom block and jumps
to the common tail at `0x01855a27`: the earthquake shake is still added to the pitch, followed by the lift zone,
the world 5 sway and the distance smoothing. The far plane at zoom level 0 is `2400 · Distance · Z_Distance ·
scale`. The FOV is the record's, because scenes other than 6 always take the world FOV (`0x01851a7f`).

The record of World94 (`Data\World94\Camera_Angle_Position.bmd`, decoded with the existing loader):

| Field | Value |
|---|---|
| Angle X/Y/Z | -84.5, 0, -80 |
| Position | 15215.089, 12186.536, 529.372 |
| FOV | 35 |
| Distance, Z_Distance | 9.1, 0.527996 → far 11,531.4 (×1.4 in the projection) |

The camera looks almost horizontally (5.5° down) toward -x. World95 (world 0x5e), the login scene, has angle
(-84.5, 0, -45).

`reconstructed/camera` takes the record as `scene_angle`/`scene_position`. `validate_camera.py` adds a family for
this path: **1,000/1,000 cases match** in the full run (scenes 3 and 5, the installed records and random ones,
shake and lift inputs; the whole validator: 34,250 comparisons, 0 mismatches). Two new planted mistakes are
detected, among the 13 mutations: the yaw not taken, and the shake skipped.

**The legacy camera table.** MoveCharacterCamera `0x01854529` → `0x01854879` still computes the classic camera
walk from the tables at `0x01cf17c0`/`0x01cf17cc`, which are packed in the file. The runtime data-section capture
`x86-linux-capture-04/main-01ced000.bin` holds them; entry 5 (scene 5) is position (200, -800, 250) and angle
(-87, 0, -10), with CameraFOV 45. These are the "scene-3/5 camera tables" the camera finding left open. They are
written in every logic step, and MoveMainCamera overwrites them in every render pass, before BeginOpengl reads
the camera (static reading). They therefore have no visible effect and are not ported.

## 3. Character slots (verified; marker positions placeholder)

The world handler of world 0x5d is a `CGMCharacterScene_Ex` (RTTI `.?AVCGMCharacterScene_Ex@@`, base
`BaseMap`, vtable `0x01aa7338`, 0x8c bytes). It is found through the world-handler registry and a
`__RTDynamicCast` (`0x0121469f`). It holds five position vectors (`+0x14`) and five angle vectors (`+0x50`), which
its constructor `0x00daa127` zeroes.

**CreateObject** (vtable slot 11, `0x00daa2b2`) runs for every static map object of the world. Objects of types
13 to 17 are the **slot markers 0 to 4**:

* marker k stores the object's position and the angle (0, 0, yaw_k), where yaw is **115, 90, 75, 60 and 35**
  (the classic MU yaws);
* SetCharacterPosition(k) runs;
* the object's `+0x68` is set to -2.

Types 0x26..0x28, 0x36..0x39, 0x45 and 0x50 also get `+0x68` = -2. Types 0x3c and 0x3d get `+0xc0` =
-428.571. Outside world 0x5d the routine returns 0. Vtable slots 12 and 13 animate map objects of other types
and emit their effects. They belong to the static objects, which are out of scope.

**SetCharacterPosition** `0x00da9ff3`(slot) copies **marker 1's** position and angle into the slot's
character. The source index is the constant 1 (`push 0xc; pop eax; shl eax, 0`), so every character stands on
the same marker, facing yaw 90. This fits the screen: the client draws only one character (section 4). Callers:
CreateCharacterScene for slots 0..9, CreateObject, and the character-created handler `0x0122b648`.

**Verified:** `validate_charsel.py` runs CreateObject on sequences of 1 to 6 synthetic map objects (all marker
types, the hidden types, 0x3c/0x3d, other types and other worlds) and SetCharacterPosition with slots including
-1, 400 and 0x7fffffff. In the full run, 1,000 + 1,000 cases match: the scene object, map object and record
bytes, and the return values. While building this, the validator caught a misreading of mine: an extra
"stale argument" for marker 17 came from a disassembly listing filtered by `grep`. The client pushes 4
normally.

**Marker positions.** NATIVE-OBJECTS-001 read the object list of a running client
([client-objects.md](client-objects.md), section 6, live single run). Marker 1 (type 14) is at
**(13629.3008, 12338.5654, 164.4998)**, which is now the native default. Marker 2 (type 15) lies outside the map,
and types 13, 16 and 17 are not in the file. The earlier fit, below, was 12.3 units off in x.

The markers come from `EncTerrain94.obj`, which the captured client code does not decode
([terrain finding](client-terrain.md), section 5). The previous native default for marker 1,
**(13617, 12339, 169.5)**, was a **live fit**. The window-only capture shows the character on a pedestal object
at a known screen position. With the verified camera, the ray through the centre of the pedestal disc meets the
plane z = 169.5, the height the render forces (section 4), at that point. The rendered character overlaps the
live one in body position and size (`renders/charsel/fit/overlay.png`). The other four markers are not needed
by the client's drawing and stay unknown.

## 4. The render (verified)

RenderCharacterScene `0x018576b3` returns 0 before InitCharacterScene, or while the protocol state `0x06fca2c4`
is below 0x33 (the character list has not arrived). Otherwise it does the following:

1. It clears the fog byte `0x0bdc597c`. If the character pick `0x016b47bf(1)` hits and the CInput byte
   `+0x1f` is set (double click), it enters the game through `0x0185a75a(0)`, unless CCharSelMainWin
   `0x009a5029` refuses (any nonzero refuses here).
2. It calls MoveMainCamera, `glColor3f(1,1,1)` and `glClearColor(255.0, 0, 0, 1)`. The red component pushed is
   255.0 (`0x01a7df30`), which GL clamps.
3. It calls BeginOpengl(0, 0, 0x016bc355(), 480), CreateFrustrum(width/640, record position, 0) and
   CreateScreenVector(MouseX, MouseY, &MouseTarget, 1).
4. It sets the light (`OBJECT+0xec`) of CharactersClient 0..9 to 0. If the selected character is live:
   EnableAlphaBlend, light (1,1,1), AddTerrainLight(x, y, (1,1,1), 1, frame light `0x0b9f5430`), and
   DisableAlphaBlend.
5. It sets the z of every character 0..9 to **169.5**, or **194.5** when CHARACTER `+0x322e` is the mount
   0x1a03.
6. It calls RenderTerrain(0) and RenderObjects. **Only character `[0x01cf1154]` is drawn**, by
   RenderCharacter `0x01363260` when it is live and visible, plus `0x00d8bd8f` for Player models.
7. It runs the joint, effect, blur, quest and point passes.
8. **Selection highlight**, when the selected character is live:
   * luminosity `sin(WorldTime·0.0015)·0.3 + 0.5` through the C runtime's sin;
   * EnableAlphaBlend;
   * two ground decals RenderTerrainAlphaBitmap(0x8036 `Skill\gmmzine.jpg`, x, y, size, size, light·lum,
     rotation, 1, 5, 1, 0), with size 1.8 and rotation `+WorldTime·0.01`, then size 1.2 and rotation
     `−WorldTime·0.01`;
   * DisableAlphaBlend;
   * the character light becomes 0.15;
   * CreateParticle(0x8022 `Logo\chasellight.jpg`, position, angles, light, 5, 1.0, 0, 0).
9. If a character is selected, its name goes to `0x0121d4c9()->0x009eaebe`.
10. It draws the 2D layers: the UI helper, GFx, CUIMng (`0x01858c72`), the cursor and the frame end.

**Verified:** `mu_charsel_render` logs every call the client makes, in order. The validator stubs each callee,
records its arguments (vectors by value, character pointers as (index, offset)) and compares the log, the fog
byte, every byte of the records and the return value. Inputs include random selected and shown indices (also
out of range), mounts, liveness, visibility, world time up to 3·10⁷ ms, the pick, the double-click byte and the
screen width. Result: **1,000/1,000 cases match**: 806 drew the scene, 558 drew the highlight, 474 drew a character and 97 entered the game by double click. The C runtime sin ran as client code (the SSE2 path behind the
captured dispatch flag) and agreed with the host libm in every highlight case.

**Inside RenderCharacter (static).** In scene 5 the character's light is 0.4 instead of the terrain light
(`0x01367530`), and the body light `CHARACTER+0x1b8` becomes `0.4 + OBJECT light` (`0x013675c2`). A second
block (`0x01367c0e`, reached for the hero pointer `[0xa39d754]`) uses 0.5. The native session uses 0.4 + light.
RenderCharacter itself belongs to NATIVE-RENDERCHAR-001.

## 5. The 2D layer

`CUIMng::CreateCharacterScene` `0x011e2f2a` (static) creates:

* `CMsgWin` (`+0x8`), centred;
* the server-message window `+0x63a8` (`0x010750e1`) at (10, width·0.0516667 + 10). It shows "You are logged in
  as Free Player" on the live screen and is not reconstructed;
* the option window `+0x458`;
* **CCharSelMainWin** `+0x4bb0` at (0x16, screen height − window height − 0xe), followed by UpdateDisplay and
  ShowWin.

**CCharSelMainWin** (vtable `0x01a7ec20`, 0x518 bytes; verified):

* sprite 0, `deco.tga`, 189×103, placed above the right end;
* sprite 1, an untextured bar, colour (0,0,0), alpha 0x8f, screen width − 0x10a wide and 21 high, beside the
  Menu button;
* four 54×30 buttons: **Create** (frames down 2, over 1, disable 3), **Menu** (no disable frame), **Connect**
  and **Delete**. The window is `bar width + 4·54 + 6` wide.

Its behaviour:

* **Create.** The tip line index is `{0x6ae, 0x6cb, 0x6cc}[rand() % 3]`. The warning flag `+0x510` is set when
  any of characters 0..9 is live with CHARACTER `+0x14 & 0x10`.
* **SetPosition.** Create and Menu go at the left, Connect and Delete at the right edge, the bar at
  (Menu.x + 56, y + 5), and the deco at (right − (189 − 0x16), y − 0x3b).
* **UpdateDisplay.** Create is enabled when a slot is free (10 slots, or the 0x010a5dca count in the other slot
  mode) and the `0x0095f75d()->+4` flag is clear. Connect and Delete are enabled when a character is selected;
  Delete also needs that flag clear. With no live character (and the GFx create interface closed), the GFx
  create-character interface opens.
* **UpdateWhileActive.** Connect enters the game unless `0x009a5029` returns exactly 1. Menu opens the GFx menu
  (`0x00c8c8b1`) and Create the GFx create interface.
* **Delete** (`0x009a553c`). It refuses with a message when CHARACTER `+0x17 != 0xff` (0x676), when the level is
  700 or above on servers without the `0x01072a96` flag (CUIMng message 0x83), when `+0x14 & 0x12` (0x1a1) or
  when `+0x3634 == 1` (0x166e). Otherwise it asks for confirmation with GlobalText 0x6b0 and the name.
* **RenderControls.** The sprites, alpha test, the tip in `ff27d9ff` centred in the bar, and, with the warning
  flag, GlobalText 0x1b4/0x1b5 at (320, 330/348) in black on translucent yellow (`0x011a0998` sets the text
  colour, `0x011a09f3` the background). Then the buttons.

**Verified:** `scripts/validate_charsel_window.py` runs the client's window code on the UI-002 Unicorn machine,
together with CWin, CButton, CSprite and the text facade as client code:

| Item | Result |
|---|---|
| Cases | 120 (8 window sizes) |
| Render calls | 32,210 |
| Update frames | 2,494 (clicks, held presses, edges) |
| Compared state words | 915,990 |
| Events reached | Create, Menu, Connect, message, notice and confirmation |
| Mismatches | 0 |
| Planted mistakes detected | 7 of 7 |

The comparison found two errors in my first reconstruction: the text and background colour setters were swapped,
and Connect is refused only by the value 1.

**GFx boundary (static).** The character list on the right side of the screen (ten entries with class, title,
name and level), the create-character and menu interfaces and the message boxes are GFx movies:

* `0x00b4bed3` is `SelectIndex`. It sets SelectedHero and the shown character `0x01cf1154` to the index and
  calls `SetCharSelArrow`;
* `0x00b4bd6c`(list index, enter) maps the list row through its `+0xa8` table to a slot. A live slot becomes the
  shown and selected character, otherwise both become -1. It then runs UpdateDisplay and, with `enter`, the same
  connect check as the Connect button.

They are not reconstructed. The native session selects a slot the way SelectIndex does.

**Live (window-only capture, 2026-10-17).** Compared over every pixel the native window draws, on a 1722×1048
client area:

| Element | Pixels | Mean absolute error |
|---|---:|---:|
| Menu button | 1,370 | 0.00/255 |
| Connect and Delete buttons | 5,002 | 0.86/255 (the translucent deco edges blend with the 3D scene) |

The Create button differs because the live account has all ten slots in use, so Create shows its disable
frame. The tip line reads "Long game time may be harmful to your health" (GlobalText is not decoded; the native
string is the observed one).

## 6. Selection and the tick (verified)

The tick (`0x01856e6c`) works as follows:

1. It returns while the protocol state is below 0x33.
2. On the first step it creates the scene. It then runs the movers, the GFx update (`0x00ac9613`(scene)) and
   MoveCharacterCamera, and returns while the GFx movie is busy (`0x00aae6f9` = 1).
3. **Enter** (`0x00ec53a7(0x0d)`, unless CInput `+0x31`). It is ignored while the GFx movie or the GFx flags
   `+0x22c->+0x79/+0x78`, the globals `0x01d22d1e`/`0x06fca007` or CUIMng `+0x464` block it, or while SelectedHero
   is outside 0..9. Otherwise it plays sound 25. If the shown character `0x01cf1154` is set, SelectedHero takes
   it. Unless `0x009a5029` returns 1, `0x0185a75a(0)` starts the loading scene.
4. **Esc.** It opens the GFx menu, or closes the GFx window `+0x22c` and clears CUIMng `+0x65b9`.

**Verified:** 1,000/1,000 cases match in the full run (call log, InitCharacterScene, SelectedHero and
`+0x65b9`). Among them, Enter started the loading scene 68 times, was refused by `0x009a5029` 34 times and took
the selection from `0x01cf1154` 74 times; Esc opened the GFx menu 47 times and closed the GFx window 24 times.

## 7. The character list feeds the slots (verified for CreateHero, static for the list)

The list handlers create each character with **CreateHero** `0x0137f824`(slot, class, skin, x, y, angle). It
works as follows:

1. CreateCharacter `0x0137d8a1`(c, 0xa91, 0, 0, angle) (not reconstructed).
2. Light 0.3, key `+0x3e` = slot, position x/y, class `+0x12`, skin `+0x13`, the buff reset `0x01295f18`.
3. In scene 3 (login) a preset equipment set. Otherwise the class body parts `0x3700/0x3750/0x37a0/0x37f0/0x3840
   + skin index` and empty weapons, wing and helper.
4. `0x0128ed7d`, then flag `+0x14` = 0.
5. **SetCharacterScale** `0x01394f6f`: a helmet in a 17-entry list shows the face part (slot 0 = 0x3700 + skin),
   the part scales, and in scene 5 **object scale 1.7**. The world values are 0.9/0.88/0.95/0.92/1.03/0.99/0.8/1.1
   by base class, 1.1 under buffs 0x1a8/0x1a9, and 0.9/0.88 in event worlds.
6. **SetPlayerStop** `0x0138fe69`, the stand action.

The character-created handler `0x0122b648` then sets the level (`+0x144`), the class byte and the name, and
places the character. The handler of the full list presumably does the same and decodes the equipment
(`0x01394870`, see [native-character.md](native-character.md)); that handler was not traced (packet data).

**Verified:** CreateHero 1,000/1,000 and SetCharacterScale 1,000/1,000 cases match in the full run (every record
byte and the call log; all class bytes, helmet types, scenes 3 to 6, event worlds, buffs).

**Idle animation (static plus verified parts).** Every character plays its stand action. In scene 5,
SetPlayerStop's stance branch (`0x01391f89`) follows the scene-6 safe-zone path, which NATIVE-WORLD-001 verified
for unarmed characters: base classes 0..15 → actions 1 1 2 1 1 3 1 5 6 6 1 1 2 1 6 8. The animation tick's
scene-5 rule (the wrap test at keys + 2) is part of the verified tick ([skinning](client-skinning.md)).
Equipped characters take the weapon stand actions of [client-actors.md](client-actors.md) (static).

## 8. Native module

`native/core/mu_charsel` builds a session from the reconstructed code:

* World94 through `mu_terrain`, with the client frustum (scene 5) and the highlight textures;
* the camera through `mu_move_main_camera` with the World94 record;
* the character list: synthetic, or a text file `slot class level name [helm=…|armor=…|weapon0=…|wing=…]`
  with up to five entries. Each entry becomes a client-layout record through `mu_charsel_create_hero` and
  `mu_charsel_set_character_position`. Its models are assembled by `mu_character` (public API: init, set item,
  set state, tick, update) with scale 1.7, marker 1's position and yaw 90, the stand action and the scene-5
  tick;
* per logic step, `mu_charsel_tick_step` (Enter) and one animation step per character;
* per frame, `mu_charsel_render` gives the frame light, the drawn character and the two decals. The decals are
  drawn through the terrain decal port with the additive state;
* the 2D layer: CCharSelMainWin through the 2D software GL over the finished 3D frame (`core/mu_charsel_ui`).

Front ends: `mu-charsel` and `mu-render charsel` (headless, software, with the 2D layer), and `mu-charsel-window`
(`make -C native charsel`: an SDL2/OpenGL window, 1..5 or Left/Right select, Enter is the client's Enter; also
headless GL). Options: `--slot`, `--list`, `--marker X,Y[,Z]`, `--cycle F`, `--enter F`, `--no-ui`.

```sh
native/build/mu-charsel --game-root "$MU_GAME_ROOT" --width 1722 --height 1048 --frames 50 --every 10 \
    --cycle 10 --out-dir /tmp/charsel
make -C native charsel && native/build/mu-charsel-window --game-root "$MU_GAME_ROOT"
```

Local renders, not committed, are under `~/Documents/mu-mac-tools/native/renders/charsel/`:

* `cycle/contact-sheet.png`: the five synthetic characters selected in turn;
* `fit/overlay.png` and `fit/ui-strips.png`: native over live;
* `gl/`: headless OpenGL;
* `live/`: the window-only captures, kept local.

**Not drawn**, and stated in the tool's help and module header (NATIVE-CHARSEL-002, section 9, draws the objects
through the lifecycle and the particle 0x8022):

* the static map objects of World94 (the pedestal, trees and waterfalls), so most of the screen stays black
  where the world has no terrain (63,878 no-ground cells);
* the particle 0x8022;
* the GFx list and interfaces;
* the cursor and the server-message window.

The window front end draws the 3D scene only; the 2D layer is composed in the headless modes. On the very first
frame the deco sprite is drawn without the alpha test, because RenderControls enables it only after the
sprites. The client's state carries over from earlier frames.

## Verification summary

| Comparison | Cases | Result |
|---|---:|---|
| MoveMainCamera scene 3/5 record path (`validate_camera.py`) | 1,000 | 0 mismatches; 34,250 comparisons, 0 mismatches over the whole validator; 13/13 mutations |
| CreateObject sequences, SetCharacterPosition | 1,000 + 1,000 | 0 mismatches |
| SetCharacterScale, CreateHero | 1,000 + 1,000 | 0 mismatches |
| RenderCharacterScene | 1,000 | 0 mismatches |
| Scene-5 tick | 1,000 | 0 mismatches |
| `validate_charsel.py` planted mistakes | 12 | 12 detected |
| CCharSelMainWin (`validate_charsel_window.py`) | 120 | 0 mismatches, 915,990 state words; 7/7 mutations |
| Live: window pixels, marker fit | 1 capture | Menu button exact; character overlap |
| CGMCharacterScene_Ex slots, CreateObject/MoveObject world 0x5d, after pass (`validate_charsel_world.py`, section 9) | 12,000 | 0 mismatches; 10/10 mutations |
| Particle kinds 0x801b/0x801c/0x8017/0x8022 (`validate_particles.py`, all 12 families) | 30,494 | 0 mismatches; 2 new negative controls |
| Live (section 9): object state, scroll advance, native +0xb/+0xa | 4 snapshots | 237/237 equal; 103 steps exact; 237/237 equal |

**Tests.**

* Portable: `reconstructed/charsel/test_charsel.py` (scene routines and window logic, no client bytes),
  `reconstructed/camera/test_client_camera.py` (record path) and `native/tests/test_native_charsel.py` (a
  synthetic World94 tree and Player.bmd: camera, records, selection cycle, Enter, the list file, determinism,
  refusals, headless GL).
* Private (`MU_RECOVERY_INTEGRATION=1`): both validators, and the installed World94.

## 9. The scene's objects at runtime (NATIVE-CHARSEL-002)

NATIVE-CHARSEL-001 drew World94's objects statically. This milestone reconstructs the rest of the scene's world
handler, runs World94's objects through the client's lifecycle (NATIVE-OBJECTS-002) and the particle module
(NATIVE-PARTICLE-001/JOINT-001), and compares the result with the client's instructions and with a live read.

### CGMCharacterScene_Ex (verified)

`CGMCharacterScene_Ex` (vtable `0x01aa7338`) overrides the same five handler slots as the login world's
`CGMLogInScene_Ex`; each first tests `[0x01cf15fc] == 0x5d` (`0x00daa1f5`). `reconstructed/objects/charsel_world.c`:

| Slot | Routine | What it does |
|---|---|---|
| 0x2c | `0x00daa2b2` | +0x64 = 0; types 0x0d..0x11, the slot markers (section 3): marker vectors, SetCharacterPosition, HiddenMesh −2; types 0x26..0x28, 0x36..0x39, 0x45, 0x50 (emitters): HiddenMesh −2; 0x3c, 0x3d: range −428.571 |
| 0x30 | `0x00daa82b` | type 0x18: blend v −0.02 per step, 0x19/0x1a: −0.03 (the waterfalls scroll); type 0x49 (lamps): l = (rand % 4 + 3)·0.1, AddTerrainLight(x, y, (0.2l, 0.6l, l), 3, frame light) |
| 0x34 | `0x00daa9dd` | 0x1f: three Spark04 `0x8155` sprites on bones 6/7/8; 0x26: clouds `0x7f89` 0x14 (rand % 6, owner); 0x27/0x28: effect stardr01 `0x5ac` subtype 0/1 (rand % 100 / % 200); 0x36: WATERFALL1 2 (rand % 2); 0x37: WATERFALL3 `0x801c` 0xe every frame at 2× scale; 0x38: WATERFALL2 `0x801b` 2 (rand % 3); 0x39: effect `0x59a` 3; 0x45: water `0x802a` 1; 0x50: smoke01 0x45 (rand % 8); 0x49: at bone 1 a Shiny02 sprite (light (0.4, sin(WorldTime·0.7)·0.2 + 0.8, 0.4), scale 1.2 + (rand % 30)/90, rotation −((int)WorldTime % 3600)·0.1) and a magic_ground1_3 `0x8145` sprite, and on rand % 3 a fantaB `0x8017` particle 15 above the bone |
| 0x38 | `0x00dab4d7` | types 4, 7, 8, 0xc, 0x18, 0x19, 0x1a, 0x1f, 0x21, 0x24, 0x3d, 0x47: +0xa = 1, nothing drawn; 0x3c (the pedestal): RenderMesh(1, …) and +0xa = 1 |
| 0x3c | `0x00dab5ed` | the same types: RenderBody(2, …, hidden mesh, −1) after the character; 0x3c: RenderMesh(0, 2, alpha, −2, …) |

RenderObjects_AfterCharacter `0x016d6949` lists world 0x5d next to 0x5e, and the first-draw predicate `0x017fe909`
has no case for either: `mu_login_after_pass` serves both.

The JOINT-001 survey (client-joints.md section 5) attributed a "selected character" routine `0x00da9974..` with joint
`0x7f78` and effects `0x7f84`/`0x4bc`/`0x4bd` to the character select. That routine is `0x00da9685`, called from a
monster handler (vtable `0x01aa7264`, monster types 0x398..0x39b, models 0x940..0x945); it is not part of this scene.

Bitmaps (static, LoadBitmap call sites): `0x8155` `Effect\Spark04.jpg`, `0x8145` `Effect\magic_ground1_3.jpg`, `0x801b`
`WATERFALL2`, `0x801c` `WATERFALL3`, `0x802a` `effect\water.jpg`, `0x8017` `Effect\fantaB.jpg`, `0x7b78` `Effect\Impack03.jpg`
(OpenCharacterSceneData, GL_NEAREST). `0x5ac` is `Data\Effect\stardr01.bmd`; `0x59a` (`zu_sealeaf04`) is loaded only by
other worlds' model passes.

**Verified:** `scripts/validate_charsel_world.py --cases 2000 --mutations` (Unicorn, the routines pinned by SHA-256):

| Family | Cases | Equal | Coverage |
|---|---:|---:|---|
| create (CreateObject `0x016d8538` world 0x5d + slot 0x2c, the marker vectors) | 2,000 | 2,000 | 531 markers, 498 hidden emitters |
| move (MoveObject world 0x5d + slot 0x30) | 2,000 | 2,000 | 462 terrain lights |
| visual (slot 0x34; sin wrapper and sprite temporary as client code) | 2,000 | 2,000 | 1,676 sprites, 591 particles, 154 effects |
| custom (slot 0x38) | 2,000 | 2,000 | 987 handled |
| after (slot 0x3c) | 2,000 | 2,000 | 192 meshes, 760 bodies |
| after_pass (`0x016d6949`, world 0x5d) | 2,000 | 2,000 | 6,423 draws |

12,000 cases, 0 mismatches; 10 of 10 planted mistakes detected.

### Particle kinds (verified)

`reconstructed/particles` adds the kinds the scene creates (create, move and render cases of CreateParticle
`0x015ae7b0`, MoveParticles and RenderParticles):

| Kind | Create | Move |
|---|---|---|
| WATERFALL2 `0x801b` 2 | LifeTime 40, rotation r%360, scale (r%6+6)·0.1 + scale, velocity z −(r%3+3), light 0.25 **in scene 5** (SceneFlag through `0x009b0bc1`; 0.4 otherwise), position += (r%20−10, r%20−10, r%40−20) | scale +0.03, velocity x/y (r%20−10)·0.1, z +0.1, light ÷1.1 below LifeTime 10 |
| WATERFALL3 `0x801c` 0xe | no case before the second subtype chain: rotation r%360, LifeTime 30, velocity z r%5+5, scale (r%10+10)·0.05·scale, position jitter | scale +0.05 +0.005, velocity z −0.6 −2.5, light ÷1.1 twice |
| fantaB `0x8017` 0 | LifeTime 24, velocity ((r%10−5)·0.4, 0, (r%10+5)·0.2), start = position | scale −0.02 (≥ 0), velocity x/y ×0.95, z +1, light LifeTime/25 |
| chasellight `0x8022` 5 | LifeTime r%3+20, drawn with Impack03 `0x7b78`, position += (r%50−25, r%50−25 then r%130−65, …), z = the argument's z + r%130, scale (r%10+20)·0.01·1.3, gravity (r%10+20)·0.05·1.3 | light ×1.05 from LifeTime 10, ÷1.16 below; z += gravity |

All four render through the generic path. `scripts/validate_particles.py --cases 3000 --heavy-cases 300`: 30,494
cases over 12 families, 0 mismatches; two new negative controls (WATERFALL2 without the scene rule, the selection
light without its rise) disagree.

### Native

* `native/core/mu_objects_runtime.c` runs world 0x5d like 0x5e: creation, MoveObject's scroll and lamp lights, the
  custom render (the pedestal's mesh 1 in RenderObjects), RenderObjectVisual (sprites, particles and CreateEffect
  through `rt.effect`) and the after-character pass (RenderBody and mesh 0).
* `mu_charsel` (session): `mu_charsel_attach_objects` starts the lifecycle on the front end's objects; each logic step
  copies the frame light over the last frustum box (+3 tiles), runs MoveObjects, MoveCharacters, MoveEffects/
  MoveJoints/MoveParticles; each render creates RenderCharacterScene's selection light CreateParticle(0x8022, …, 5)
  in the particle module (scene 5).
* **CreateFrustrum2D in scene 5.** Zoom mode 0 scales the polygon by the camera object: s = `0x016bc355()`/640 ·
  Distance · Z_Distance · scale (`0x0098ac7c`) and distance 2400 · Distance · Z_Distance · scale (`0x0098ac45`), from
  the scene's camera record (static reading of both helpers; the polygon itself is verified in NATIVE-TERRAIN-002).
  TestFrustrum2D passes everything only in scenes 1..4, so in scene 5 the polygon decides what RenderObjects draws.
  NATIVE-CHARSEL-001 used the in-world values (1, 2400): the polygon was 4.8 times too small and culled the left
  waterfall, the castle and the cliffs. `mu_world_client_frustum_scaled` takes the two values.
* `charsel/parts.def` orders `mu_charsel_rt`'s draw passes: terrain, RenderObjects, the shown character with each part's shadow
  (the item render's shadow block, `mu_world_particles_character_shadow`, static), the effect models,
  RenderObjects_AfterCharacter, the highlight decals, then RenderJoints/RenderSprites/RenderParticles. Headless frames
  that are not saved still run RenderObjects (`mu_charsel_frame_objects`). `--objects-out FILE` writes each object's
  type, position, +0xb, +0xa and blend v. `mu-client` gets all of this through `mu_charsel_rt` (CHARSEL-RT-001).

Viewer choices: the module's own rand(); the joints are drawn after the decals instead of before the
after-character pass (the scene creates none); effect kinds that are not reconstructed (stardr01 `0x5ac`, `0x59a`)
are released at creation.

### Live read (2026-10-18)

The owner authorized a read-only live read. It followed `GAME-LOCK.md`: lock held 20:11:01–20:13:27; the play
bottle's client went to the server select (`mu-to-server.sh`), logged into the account and **stopped at the character
select** (no Enter, no character entered the world); four objread snapshots with the scene globals (20:12:18, :20,
:22, :23) and one window-only screenshot; then the client was closed with taskkill (WM_CLOSE) and the launcher
closed on a WM_CLOSE (its own X button was not needed). Snapshots and the screenshot stay local
(`~/Documents/mu-mac-tools/native/scratch/charsel2/live/`, `renders/charsel2/live/`).

* Globals: SceneFlag 5, world 93 (0x5d), CameraAngle (−84.5, 0, −80), CameraPosition (15215.0889, 12186.5361,
  529.3717), FOV 35, CameraViewFar 11531.4326 — the native session reports the same values.
* `scripts/live_object_state.py` (World94 rules added): **237/237 objects** equal `mu_obj_create` in both snapshots
  apart from the handler-driven fields. Between the first and last snapshot WorldTime advanced 4,120 ms = 103 logic
  steps, and every waterfall MoveObjects moved (visible in both) scrolled by exactly 103 × 0.02 / 0.03; the one culled
  waterfall did not move.
* The native session (`mu-charsel --objects-out`) sets +0xb (RenderObjects' visibility) and +0xa (the custom render)
  on the same objects as the live client: **237/237 equal, 221 visible, 38 after-character**.

**Screenshot** (1722×1048 client area, `renders/charsel2/compare-live-before-after.png`, `compare-live-gl.png`): the
native frame has the live composition (both waterfalls with their spray, the castle, the cliffs, the pedestal glow, the
lamps' glows). Mean absolute difference against the live capture, left waterfall region: 48.7 (before) → 16.2
(after); pedestal region 11.9 → 5.6; the whole 3D area 29.3 → 21.7 (the live character is a different, winged
character and the GFx list covers the right edge).

Local renders (not committed), `~/Documents/mu-mac-tools/native/renders/charsel2/` (`render.sh`, `sheets.py`):
`before/`, `after/` (software), `after-gl/` (headless GL), `after-cycle/contact-sheet.png`, `after-anim/anim.gif`.

### Tests

* Portable: `reconstructed/objects/test_charsel_world.py` (every slot, the marker vectors, the after pass for 0x5d),
  `reconstructed/particles/test_particles.py` (the four kinds), `native/tests/test_native_charsel.py` `LifecycleTests`
  (a synthetic EncTerrain94.plain and Object94 models: markers hidden, after-character flags, the scroll, the lamp's
  sprites and light, particles, determinism).
* Private: `tests/test_charsel_world_private.py` (the Unicorn validator; the live snapshots with
  `MU_CHARSEL_DUMP_DIR`), `native/tests/test_native_charsel.py` with `MU_OBJECTS_PLAIN_DIR` (237 created, 221 visible,
  38 after-character, part shadows).


## 10. Picking, the GFx list, the star dragon and the markers (NATIVE-CHARSEL-003)

Labels as above; **verified** = Unicorn comparison of the client's instructions, **static** = decoded instructions read,
**observed** = run on this Mac under the patched Ruffle.

### Picking in the 3D scene (verified through NATIVE-NPC-001; scene-5 use static)

RenderCharacterScene's first call is SelectCharacter `0x016b47bf(1)` (section 4). It is the client's general picker
(NATIVE-NPC-001 reconstructs it, `reconstructed/npc` `mu_npc_pick`, and compares it with the instructions):

* a first pass gives every live, visible, non-transparent character of the kind mask LightEnable (`+5`) and a light
  indexed by CHARACTER `+0x144` (the level: 0..4 only), or −0.4 when `+0x1f ≥ 6`; the render resets the lights of
  0..9 right after, so this has no visible effect in scene 5;
* the second pass tests the mouse segment (CreateScreenVector, `0x0bdc5984` → `0x0bdc5990`) against each candidate's
  box at OBJECT `+0x31c` with the separating-axis test `0x018500bf` (six axes, `0x01850d88`) and keeps the one nearest to
  CameraPosition (squared distance, strict less). Scene 5 is the one scene that does not skip the hero; **world 0x5d
  grows each tested box by 100 in z, in place** (`0x016b4d2c`);
* the box comes from RenderPartObject's Transform `0x017e68a6`: BoundingBoxMin + body origin, axes diag(Max − Min).
  CreateCharacter gives the Player (model 0xa91) the box (−60, −60, 0)..(40, 40, 120) (`0x0137dfe3`, `0x0137e2d4`),
  unscaled: the 1.7-scaled character is about 200 tall, the box 120 + 100.

What the result does in scene 5: **only the double click.** When the pick hits and CInput `+0x1f` is set, the render
enters the game with the *current* SelectedHero (`0x0185a75a(0)`, unless CCharSelMainWin `0x009a5029` refuses). A
single click on the 3D character selects nothing, and there is no hover highlight in 3D: selection, hover and the
arrows are the GFx list's (below). Only the shown character is drawn, so only its box is refreshed; the others keep the
box of the last frame they were drawn in and grow by 100 per frame (an inference from the reading: after switching, a
double click high above the pedestal can still hit a stale box).

Keyboard: the scene tick handles Enter (sound 25, entry) and Esc only (section 6). The list movie swallows the arrow
keys (`MUComponent.handleInput` returns true for 37..40 without passing them on), so the client has **no keyboard
navigation** of the list. The native 1..5 and Left/Right keys are native shortcuts (they go through the list's row
click and an extra SelectIndex so the movie shows them).

`mu_charsel_pick` (native) runs `mu_npc_pick` over the session's records (its writes go back into them): the records
carry CreateCharacter's box fields, the drawn character's box is written after its update (Transform, static), the pick
runs before RenderCharacterScene's logic, and a WM_LBUTTONDBLCLK (the shell turns a
second press within 500 ms and 4 pixels into one, as Windows does for a CS_DBLCLKS class) is the `+0x1f` stand-in.

### The GFx character list (verified)

The list, its arrows and the create-character panel are the movie `CharacterSelect` (`Data\Interface\GFx\
CharacterSelect.ozg`, AS2 class `CharacterSelect`, decompiled locally with JPEXS, nothing committed). Its game side is
the window object at GFx manager `+0x22c` and a callback handler (vtable `0x01a8b520`, `+0x10` = the window).
`reconstructed/charsel/charsel_gfx.c`:

| Routine | What it does |
|---|---|
| `0x00b4915b` | On the movie's UIInit: `SetInputBoxLength(10)`, `InitText({StrOK GT 0xe4, StrCancel 0xe5, StrName 0x101c, ChangeName 0x2a4, BaseCharSlot 0x1464, LockCharSlot 0x1465, MoveCharText, ViewableSelectedWinNum 10})`, `InitStat` (GT 0xa6, 0xa7, 0xa9, 0xa8, 0x76c), `SetInputBoxLength(10)`, `InitClassInfo` (`0x00b4aef1`: 16 classes, button, class type, name, Str/Dex/Vit/Ene/Cha, explanation), `SetClassInfo(1)`, `SetnumViewableSelctedWin(10)` |
| `0x00b4b927` | `SetSelectText` with ten rows from the row → slot map `+0xa8`: a live character gives `{type 0, index, textJob (class name 0x0139cc2e), textState (guild status +0x17: 0xff → GT 0x1e8, 0 → 0x532, 0x20 → 0x516, 0x40 → 0x515, 0x80 → 0x514), textName, textLevel}` (name and level through the HTML helper `0x00ab4dc0` in #FFCC19), an empty row `{type 1, textCreat GT 0x1464}`, or `{type 2, GT 0x1465}` past the account's slot count. A name colour is computed from CHARACTER `+0x14` and a "webzen" test and never used |
| `0x00b4b848` | show(flag): with a live character, focus, SelectIndex(row `+0xa0`), then `SetSelectVisible(flag)`, `SetCharSelArrow` |
| `0x00b4bed3` | `SelectIndex(n)`; SelectedHero and the shown character take **n** (the row, used as the slot); CCharSelMainWin UpdateDisplay; `SetCharSelArrow` |
| `0x00b4bd6c` | A row clicked (double click: enter): Dark Lord cleanup `0x010b03cb` for the previous selection; a live row selects its slot, an empty one clears the selection and opens the create-character panel; UpdateDisplay; with enter the CCharSelMainWin check and `0x0185a75a(0)`; `SetCharSelArrow` |
| `0x00b4bfc2` | The arrows (`onCharSelArrow`): **reorder** the characters (swap the row with its neighbour, rebuild the map from the characters' key `+0x3e`), SelectIndex, select, rebuild the list |
| `0x00b4c1df` | The movie's callbacks: OnCharSelectedClick / DClick → `0x00b4bd6c`, onCharSelArrow, the create panel's SetSelectedClass, SetCreateBoardInfo, OnEnterCharacterName, OnClickCreateCancel, UpdateInput, OnClickCreateCharacter; ignored while the GFx movie is busy and the window's `+0x79` is set |

`scripts/validate_charsel_gfx.py` runs these instructions in Unicorn with the GFx value API stubbed (objects, arrays,
member setters, Invoke; GlobalText "GT<n>", class names "CLASS<n>") and compares the invoke and call lines, the window
fields and the selection globals with the C (pinned by SHA-256 in `validate_charsel_gfx.pins.json`):

| Family | Cases | Mismatches |
|---|---:|---:|
| list `0x00b4b927` | 300 | 0 |
| show `0x00b4b848` / `0x00b4b82c` | 300 | 0 |
| select `0x00b4bd6c` | 300 | 0 |
| index `0x00b4bed3` | 300 | 0 |
| arrow `0x00b4bfc2` | 300 | 0 |
| dispatch `0x00b4c1df` | 300 | 0 |
| init `0x00b4915b` + `0x00b4aef1` | 300 | 0 |

2,100 cases, 0 mismatches, 5/5 planted mistakes detected (guild text, swapped globals, arrow direction, double click,
locked rows). The two HTML helpers `0x00ab4dc0` (22-colour table, `&lt;`, `<font color='%s'>%s</font><br>`, bold
variant) and `0x0096fe90` (`#rrggbb` from an RGBA word) and the class-name switch `0x0139cc2e` (code = skin index,
68 GlobalText numbers; codes 9 and 10 use another accessor) are **static** readings; the validator implements the HTML
helpers independently.

**When the client calls them** (static): the login scene's creation (`0x018519b5`, `0x018519d3`) closes the create
panel and runs show(0); CreateCharacterScene ends with `0x00b4b82c` (fill and show) when a character exists, else
`0x00b4b927`. show(0) at the login scene matters: the movie's own `onLoadUI` loads 12 test rows and shows its scroll
bar; SetSelectVisible(false) hides it, and the real ten rows never show it again — which is what the live screen shows.

**Native** (`native/charsel/charsel_list_gfx.c`, observed): mu-client and mu-shell `--gfx DIR` play CharacterSelect.swf
as one full-window libmugfx player (own loader; the HUD layer `mu_gfx_layer.c` is untouched) composited over the frame.
UIInit runs the window's initialisation, the login scene's show(0) and the list step; clicks go to the movie first
(hit test), the callbacks run the reconstruction over the session's records (SelectedHero and the shown character are
the session's), an entry from the list is the session's enter request. An empty row, OnClickCreateCharacter and
OnEnterCharacterName are **OFFLINE DEMO** no-ops (counted, reported in the offline label; the client would open the
create panel and send a packet). GlobalText comes from NATIVE-LANG-001's tables (`MU_LANG_DIR`), else "GT<n>".
Compared by eye with the live capture of NATIVE-CHARSEL-002 at 1722×1048: same placement, row size, fonts, colours,
selection and arrows, no scroll bar (`renders/charsel3/list-live-vs-native.png`).

### The star dragon `0x5ac` / `0x5ad` (create verified, move verified, render static)

Objects 0x27 and 0x28 of World94 create effect 0x5ac (`Data\Effect\stardr01.bmd`) subtype 0 / 1 (handler slot 0x34,
`rand % 100` / `% 200` per drawn frame, section 9). CreateEffect's case `0x013f41b4`: angle (0, 310, 90), position y +=
`rand % 600 − 300`, blend mesh 0, speed 1; subtype 0: LifeTime 70, direction x −25, scale 1; subtype 1: LifeTime 130,
x −15, scale 0.7; then it poses its model (`0x012b5064`), reads bone 1 (`0x012b678d`: BodyScale · bone translation +
position) and creates **0x5ad** (`stardr02.bmd`) there with light 0.5, the same subtype and itself as owner. 0x5ad
(`0x013f4457`): blend mesh 0, speed 1, LifeTime 70/130, direction x −25/−15, scale 0.5/0.3. MoveEffect has no case for
either (jump tables `0x0150d161`/`0x014ece4f` → the defaults): the animation, the rotated motion and the LifeTime.
RenderEffects (static): 0x5ac is a plain RenderObject (`0x0151e966`); 0x5ad (`0x0151e980`) poses, plays its animation
again in the render pass and, while 20 < LifeTime < 25, creates a Spark04 `0x8155` sprite (0.7, light (0.8, 0.8, 1)),
takes light 0.6 and scale 0.8/0.6, else scale 0.5/0.3. On screen these are shooting stars crossing the sky towards
the lower left (`renders/charsel3/dragon-strip.png`).

`scripts/validate_skill_fx.py` now includes the four kinds (create and move families, 20 cases each at 400 cases;
the full validator at 300 cases stays all-equal). Native: `mu_particles` loads both models for world 0x5d, answers the
bone with the native pose and runs the glint's render pass.

### Markers 0 and 2..4 (verified and static)

CreateObject stores all five marker vectors (verified, section 3), but nothing reads them except
SetCharacterPosition, whose index is the constant 1 (verified). The handler is reached through `__RTDynamicCast` only at
two sites (`0x0122b7fe`, the character-created handler, and `0x018517ae`, CreateCharacterScene), both calling
SetCharacterPosition; its other slots (0x2c..0x3c, verified) do not touch the vectors; marker objects themselves are
hidden (`+0x68 = −2`). EncTerrain94 holds only marker 1 (type 14) and marker 2 (type 15, at (−136.21, 17173.0,
−1044.95), outside the map). **Role: none in this client** — the five yaws (115, 90, 75, 60, 35) are the classic
five-pedestal layout; this client shows one character on marker 1.

### Live comparison

No new live run was needed: the list was compared with the NATIVE-CHARSEL-002 capture. The game lock was not taken.

### Tests

* Portable: `reconstructed/charsel/test_charsel_gfx.py` (worked examples of every routine), `native/tests/test_native_shell.py`
  `CharacterListTests` (the list through the stand-in libmugfx, which now plays CharacterSelect: UIInit, rows, row
  clicks and double clicks; the auto flow enters with slot 1 from the list; an empty row is an offline create request; a
  double click beside the character does not enter), `test_native_charsel.py` `test_star_dragon_emitters`.
* Private: the Unicorn validators (`validate_charsel_gfx.py`, `validate_skill_fx.py`).

Local renders (`~/Documents/mu-mac-tools/native/renders/charsel3/`): `shell-lang/` (mu-shell, GlobalText, World94
objects, 1722×1048), `client-gl/` (mu-client headless GL, whole flow), `dragon/` and `dragon-strip.png`,
`list-live-vs-native.png`.

## 11. Creating and deleting characters, the system menu (NATIVE-CHARCREATE-001)

Labels as above: **verified** = the client's instructions ran in Unicorn and matched the reconstruction, **static** = decoded
instructions read, **observed** = run on this Mac (mu-shell, headless GL) with the converted client movies under the patched
Ruffle. OFFLINE DEMO marks what the server decides and the native client answers locally.

### The create panel is part of CharacterSelect (verified)

The create panel is the movie's `mcCharacterCreate` (sixteen class buttons, the stats, the description, the name box, OK and
Cancel). Its game side is the CharacterSelect window (GFx manager `+0x22c`), `reconstructed/charsel/charcreate.c`:

| Routine | What it does |
|---|---|
| `0x00b49bf4`(flag) | `+0x78` = flag; open: focus; closed: `SetClassInfo(1)`; `SetCreateVisible(flag)`; the list's show(!flag) (`0x00b4b848`) |
| `0x00b4b684` | the rename mode's class restriction: the body (SetClassDisable for all but the character's class, ExplainChangeName) sits behind an unconditional `jmp` — **dead code** in this client |
| `0x00b4a442`(class) | preview `+0x12` = class; CreateCharacter(`0x0a39d780`, **model 0x135 + class**, 0, 0, 0.0); object `+0x3b`, `+0x03` = 0; the pose `0x00b4a4a1`; SetAction(object, 1) |
| `0x00b4a4a1` | per class (jump table `0x00b4aeb1`): the window's camera offset `+0xb4`, the object's angle `+0x164` (class 6 keeps CreateCharacter's) and scale `+0xa0`; table below |
| `0x00b4a349`(x, y, w, h) | the preview rectangle `+0x88..+0x94` = window origin + movie point × window scale (truncated); the origin getters `0x00aae509`/`0x00aae601` (alignment modes 0..8) run as client code |
| `0x00b49eca`(name, class) | in this order: `+0x7c ≥ +0x80` (daily count) → GT 0x1832; size < 4 → GT 0x186; `0x00b4b29d` (the name tables) → GT 0x6b3; `0x00cdb9af` (characters) → GT 0x187 — each a message box id 0x64; rename mode (`+0x9c == 1`) → the rename request `0x009a4708`(old, new); else protocol state 0x34 and the create request `0x009a466c` with the name (10 bytes) and **(preview class << 4) + skin** (the movie's class argument is not read) |
| `0x00b4b29d` | FilterName(kor) `0x06fbacd0` (`0x0110cb45`: any word found in the name) or Filter(kor) `0x06fbac88` (`0x0110c9f2`: the name without spaces `0x0110c960`, each word by `0x0185c95d`, which steps by `_mbclen`) |
| `0x00cdb9af` | single-byte characters: only `0-9 A-Z a-z`; double-byte (CP949 lead bytes): lead 0x81..0xc8, trail A-Z/a-z/0x81..0xfe, not the symbol rows (lead 0xa1..0xaf with trail ≥ 0xa1), not lead 0xc6 trail 0x53..0xa0, not lead 0xc7/0xc8 trail ≤ 0xa0 |
| `0x00b4b31a` | UpdateInput: at 10 bytes or more the text is cut to 10 (`resize(10)`) and sent back with SetCharacterName |
| `0x00b49d0d`(created, limit) | `+0x7c`/`+0x80`; UpdateCreateCount(GT 0x1831 "Daily Character Creation Limit: %d left" with limit − created) |
| `0x00b4b2d6`, `0x00b4bf25`, `0x00b4c806`, `0x00b49c82`, `0x00b49ca0` | reset (SetInputExplainVisible(1), SetCharacterName(""), SetClassInfo(1)); the list row (0..10, else 0); `+0x98`; the pending delete `+0x98`/`+0x79` |
| `0x00b49cd7` → `0x00b4a14c` | the window's render hook: while the panel is open, the preview: the animation step `0x013960d2` (at its end SetAction(0)), light (1, 1, 1), CameraFOV 10, the camera walk `0x01854879`(object position, (5, −500, 46) − offset, angle (−90, 0, 0)), **BeginOpengl2 `0x0184b27e`(rect)** (viewport in window pixels, gluPerspective2(FOV, w/h, near, far × 1.4), the camera rotations), RenderObject(object, 1, 0, 0, −1, −1), the viewport back |

The class table of InitClassInfo (NATIVE-CHARSEL-003) gives each button a ClassType; the movie calls `SetSelectedClass(ClassType)`.
`OpenCharacterSceneData` (`0x0182a74d`, static) loads `Data\Logo\NewFace01..16.bmd` as models 0x135..0x144 (textures from `Logo\`)
and sets the PlaySpeed of actions 0 and 1 to 0.3 (0.25 for model 0x13a action 0); the animation step's per-model factors for
0x135..0x144 are NATIVE-ACTORS' verified ones. The busts carry the class's look; no items are shown.

The pose table (`--emit-poses`, executed): camera offset / angle / scale

| Class | Offset | Angle | Scale | Class | Offset | Angle | Scale |
|---|---|---|---|---|---|---|---|
| 0 DW | 0, 0, 0 | 0, 0, −40 | 4.9 | 8 RW | 10.8, 0, 2.8 | 8, 0, −2 | 8 |
| 1 DK | 0, 0, 0 | 0, 0, −12 | 5 | 9 Slayer | 10.8, 0, −1 | 1, 0, −2 | 8 |
| 2 Elf | 4.8, 0, 0 | 8, 0, 5 | 8 | 10 Gun Crusher | 10.8, 0, −1 | 1, 0, −2 | 5.2 |
| 3 MG | 0, 0, 4.8 | 8, 0, −13 | 5 | 11 Light Wizard | 14.8, 0, 5 | 1, 0, −2 | 7.6 |
| 4 DL | 0, 0, 0 | 8, 0, −18 | 5.1 | 12 Mage | 10.8, 0, 4 | 1, 0, −2 | 0.078 |
| 5 Summoner | 4.8, 0, 0 | 2, 0, 2 | 8 | 13 Illusion Knight | 10.8, 0, 0 | 1, 0, −2 | 8.6 |
| 6 RF | 2, 0, −7.5 | (kept) | 5.1 | 14 Alchemist | 14.8, 0, 0 | 1, 0, −2 | 7.6 |
| 7 GL | 4.8, 0, −2 | 8, 0, −2 | 8 | 15 Crusader | 12.8, 0, −23 | 1, 0, −2 | 0.19 |

Which classes are offered: all sixteen buttons are enabled (`CanNotBeCreated` false in InitClassInfo, NATIVE-CHARSEL-003);
account requirements are the server's (its answer 0 / 2 / 5, below). The daily count comes with the server's character list
(not traced).

### The server's answers (verified)

* **Created** `0x0122b648`: result 1 → the slot's character released (`0x0137c457`), CreateHero(slot, `0x0139ca62`(class code),
  preview skin, 0, 0, 0) — x/y/angle are 0 for slots 0..4 and uninitialised locals otherwise —, level `+0x144`, class `+0x12`,
  the name (10 bytes), SetCharacterPosition, protocol state 0x35, the panel reset and closed, UpdateDisplay, the list row = the
  slot, **InitCharacterScene = 0** (CreateCharacterScene runs again on the next tick) and UpdateCreateCount(packet +0x2c, +0x2b).
  Result 0 → the panel stays, GT 0x6b4 ("Incorrect name was entered or same character name exists."); 2 → closed, GT 0x18c; 5 →
  GT 0x179b.
* **`0x0139ca62`**: class byte = bit 3 → 0x10, bits 4..7 → 0..3, bit 2 → 0x20, bit 1 → 0x40, bit 0 → 0x80 (all 256 codes).
* **Deleted** `0x012326c4`: result 1 → the `+0x98` character released, the selected one's effects cleared, SelectedHero −1,
  GT 0x6b2 (message 0x77: OK reopens the panel when characters 0..4 are all gone), InitCharacterScene = 0, row 0; 0 → GT 0x676,
  3 → GT 0x1b7, other → GT 0x191 ("The password you have entered is incorrect."); then `+0x98` = −1, `+0x79` = 0.

### The delete flow and the message boxes (verified; the Caution window static)

CCharSelMainWin's Delete (NATIVE-CHARSEL-001, verified there) asks with GT 0x6b0 "Would you like to delete %s character?" as
message 0x65 and marks the slot (`0x00b49c82`). The window's message results `0x00b49967`: 0x65 OK → 0x66 (GT 0xea7 + "\n" +
GT 0xea8, "You cannot restore a deleted character!"); 0x66 OK → 0x67, the password box (`0x00b3974a`, 20 characters, GT 0x6b1);
0x67 OK → the delete request `0x00b4a0da` (state 0x38, the selected character's name and the password); any Cancel closes the
box (`0x00b399db`); 0x64 (a create error) OK reopens the panel.

The boxes are the **Caution** movie (GFx manager `+0x90`). Static reading of its queue (`0x00b38f50`) and display
(`0x00b390a9`): SetUIType(type, title, text, text type), SetDisableOkBtn(0), InitCaution(OK GT 0xe4, Cancel GT 0xe5), and for
the input types SetInputBoxLength and SetInputFocus; the wrappers set the type: `0x00b39648` 0 (two buttons), `0x00b3967c` 1
(OK), `0x00b39714` 3 (input), `0x00b3974a` 4 (password). The movie's OnClickBtnOK / OnClickBtnCancel reach the owner's result
handler through `0x00b39912`; its onClickCautionInputCancel (any release outside the password field) only moves the IME focus
(`0x00b3aadd`), it is not a cancel.

### Class names (verified)

`0x0139cc2e`(class, flag) switches on the skin index (`(tier − 1) · 16 + class & 0xf`). Executed for all 256 class bytes and both
flags: codes **9/25/41/57 → GlobalText 5526..5529** (Slayer, Royal Slayer, Master Slayer, Slaughterer) and **10/26/42/58 →
5786..5789** (Gun Crusher, Gun Breaker, Master Gun Breaker, Heist Gun Crusher) through the `std::string` accessor `0x011753c3`;
codes with no case (19, 20, 22, 23) give the default GT 2305; with flag 0, codes 11 and 12 give 0x1750/0x1751 instead of
5914/5923. The native list now uses this table. The class models of 9 and 10 are the ordinary part files (`HelmClass10/11`
…, `mu_character_part_file`) and NewFace10/11 for the preview.

### The system menu (verified, the window loader static)

Esc in the scene tick (verified, section 6) and the Menu button call `0x00c8c8b1`: open (`openWindow` on the KeyWindow) and
`0x00c8ce3d(0)` (scene 5: CCharSelMainWin's Show(0) and the list's show(0)), or the reverse. The window is
**winSystemMenu** (`window.winSystemMenu`, a KeyWindow of the base movie's window framework). Its events `0x00c8c6be`:
onLoad → InitText {tfTitle GT 0xd7a, btnExit 0x17d, btnServerSelect 0x17e, btnCharSelect 0x17f, btnOption 0x181, btnClose
0x3ea}, SceneChange(SceneFlag), closeWindow; onClose → closeWindow and the scene's windows back; onExit → (after `0x00c8cbe2`,
which saves the macros) the list order to the server (`0x00b4c117`/`0x00b4c6ce`), the countdown box GT 0x17c with 5 and the
logout request `0x009a5ab2(0)`; onServerSelectClick → `0x009a5ab2(2)`; onCharSelectClick → `(1)`; onOptionClick → the option
window (`0x01d22c7c`) opens.

### Verification

`scripts/validate_charcreate.py --cases 300 --mutations` (Unicorn, the routines pinned by SHA-256 in
`validate_charcreate.pins.json`; GlobalText "GT<n>", the CRT string routines, the formatter, the string stream, the packet
objects and the code page modelled):

| Family | Client entry | Cases | Mismatches |
|---|---|---:|---:|
| show / restrict / klass / board | `0x00b49bf4` / `0x00b4b684` / `0x00b4a442` / `0x00b4a349` | 4 × 300 | 0 |
| name (105 create requests, 13 renames, 167 refusals; SBCS and CP949) | `0x00b49eca` | 300 | 0 |
| input / count | `0x00b4b31a` / `0x00b49d0d` | 2 × 300 | 0 |
| created / message / deleted | `0x0122b648` / `0x00b49967` / `0x012326c4` | 3 × 300 | 0 |
| render (202 previews drawn) | `0x00b49cd7` | 300 | 0 |
| menu (toggle, scene windows, all events) | `0x00c8c8b1` / `0x00c8ce3d` / `0x00c8c6be` | 300 | 0 |
| classname / serverclass | `0x0139cc2e` / `0x0139ca62` | 512 / 256 | 0 |

4,368 cases, 0 mismatches; 6 of 6 planted mistakes detected (the code page, the two name tables swapped, the camera offset,
the server's class code, the window scale, the menu's scene). The comparison found two mistakes of mine: the rename request's
argument order, and class 6's pose (it leaves the angle).

### Native (observed)

`native/charsel/charsel_create_gfx.c`, owned by the GFx list (mu-client/mu-shell `--gfx DIR`; convert `CharacterSelect`,
`Caution` and `winSystemMenu` with `gfxconvert.py --bridge`):

* the panel's callbacks run the reconstruction; the window's slot `+0x10` (`0x00b496d4`, static) asks the movie for
  SetCreateBoardInfo after UIInit;
* the preview: the class's NewFace model with the pose's angle and scale, the intro action 1 then action 0, drawn by the software
  rasteriser into the panel's rectangle over the frame (GL blends against the framebuffer) under BeginOpengl2's matrices
  (`reconstructed/camera`); in both the software and the GL front end;
* the name tables: `scripts/live_lang_filters.py SNAPSHOT DIR` writes `filter.txt` (10 words) and `filtername.txt` (45 words)
  from the Lang snapshot of NATIVE-LANG-001; the native client assumes a single-byte ANSI code page (the English setup), so only
  ASCII letters and digits pass;
* the Caution boxes and winSystemMenu are two more libmugfx players (the menu window attached as the window loader does,
  `onFileLoad` once its first frame ran; the timeline's own instance hidden);
* **OFFLINE DEMO** (`client/offline-session.*`): the create request is answered from the local character list — the first free
  slot of 0..9, level 1, class byte = `0x0139ca62`(class << 4), result 0 for a name already used (case-insensitive), 2 with no
  free slot, a daily count of 5 —, the delete request deletes without checking the password (which is never stored or
  logged), the menu's Select Server returns to the server list at once and Exit quits after the countdown box. The list is
  kept in a store file (`--store FILE`; the window defaults to
  `~/Library/Application Support/MuTheMatrixNative/offline-characters.txt`, headless runs keep it in memory, `--no-store`);
  after an answer the scene is created again (InitCharacterScene = 0) while the GFx windows stay;
* the session takes all ten slots (`MU_CHARSEL_MAX_ENTRIES` 10), CCharSelMainWin's Connect enters, Create and Delete start the
  flows; the scene tick reads the panel's `+0x78`/`+0x79` (Enter is ignored while the panel or a box is open);
* scripted input: `click:create|delete|menu|connect`, `click:class:N`, `click:createname`, `click:createok|createcancel`,
  `click:msgok|msgcancel|msginput`, `click:menu:exit|server|option|character|close`, with `text:` for typing.

Local renders (`~/Documents/mu-mac-tools/native/renders/charcreate/`, not committed): `class-previews.png` (the sixteen busts in
their panel), `try4/` (a Slayer created and listed), `try5/` (delete flow: confirmation, warning, password, success; the menu),
`client-gl/` (mu-client headless GL at 1722×1048, an Illusion Knight created).

### Tests

* Portable: `reconstructed/charsel/test_charcreate.py` (name rules and filters in both code pages, the request, the pose, the
  board and render, the created answer, the delete flow, class names, the menu), `native/tests/test_native_shell.py`
  `CharacterCreateTests` (the stand-in libmugfx now plays the panel, Caution and winSystemMenu: create through the panel with a
  synthetic NewFace10, name refusals with synthetic tables, the delete flow (the password reaches no file), cancel/Esc, the
  menu's Select Server and Exit, the store across runs and an empty store).
* Private (`MU_RECOVERY_INTEGRATION=1`): `validate_charcreate.py` through `test_charcreate.py`.

## Open points

* The effect `0x59a`; the particle kinds `0x802a` 1 and smoke01 0x45 (their emitter types 0x45 and 0x50 are not placed
  in World94); RenderEffects' 0x5ad case and RenderPartObject's box are static readings.
* The objects' animation PlaySpeeds (no World94 handler sets any); `0x009a5029`'s checks.
* The Caution window's queue and display code and its button handler `0x00b39912` (static readings); the Option window; the
  create panel against a live capture (bust placement); the server's character-list handler (the daily counts).
* RenderCharacter's scene-5 light branches, and which of them the hero pointer selects.
* The server-message window `+0x63a8`.
* The list handler's equipment decoding (packet data, deliberately not traced).
* GlobalText (`Data\Lang.mpr`) for the tip and warning strings.


## Character-select runtime extraction, CHARSEL-RT-001 (2026-10-27)

Verified host refactor from `a9128ef`. `native/charsel/charsel_rt.c` dispatches the existing passes through
`parts.def`: scene assets, terrain, objects, character, effects, after-character objects, decals, billboards,
and the optional standalone 2D layer. `mu_charsel_rt_options` replaces the embed config; `charsel_tool.c` owns
CLI parsing, scripts and reports. No reconstructed routine or client-code pin changed. The existing session
still owns the scene tick, characters and particles; session-account migration remains open.

The private character-create check now uses `--cases 300 --mutations`, as does its validator manifest row.
This gives 4,368 instruction comparisons with zero mismatches and detects 6/6 planted mistakes, including the
CP949 mutant that 60 cases missed. The two private charsel tests that referenced the removed `EVIDENCE`
attribute now let the validator resolve and check its pins, so requested integration reports missing inputs
as errors. The manifest run, including mutants, took 58.7 seconds on this Mac.

The comparison scope, exact counts, local artifact paths and limits are in
[the lane handoff](../handoffs/CHARSEL-RT-001.md). No live client was used.


## AUDIO-002 part 5: native tick sound delivery

The three sound-25 branches of scene tick `0x01856e6c` now reach the shell's existing audio host through
`mu_charsel_set_sound`. Verified source sites are Enter `0x01857064`, Esc menu `0x01857163` and Esc
panel close `0x018571e6`; object NULL, loop 0. Enter's sound precedes the later refusal check.
The original tick gates run unchanged, including busy, panel/menu, input, selection and protocol gates.
The native callback is immediate and borrowed; detach discards sounds and close clears it. The shell
supplies the configured sound table, while standalone tools need an explicit callback. Its no-GFx
Esc-to-server shortcut remains unchanged and bypasses these branches.

New complete-tick instruction comparison: 5,760 Enter + 64 Escape + 144 common = **5,968 cases,
zero mismatches/stops, 11/11 compiled mutants caught**. The unchanged existing charsel validator passes
another 6,000 cases and 12/12 mutants. Six native tests cover sound delivery, mute/disable, detach,
close and shell wiring; pre-change standalone hashes and audio-on/off shell renders agree.
[Full evidence and limits](../handoffs/AUDIO-002E.md). No original client or live service was used.
