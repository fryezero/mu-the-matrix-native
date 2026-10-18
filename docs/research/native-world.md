# Walking around the world natively (NATIVE-WORLD-001)

This milestone is the first native "walk around the world" build. One window, or a headless run, combines:

- the real terrain of a world (Lorencia by default);
- a hero assembled by the character module and animated;
- the client camera following the hero, with the world's own camera record;
- click-to-move through the client terrain pick and the client's own path finder;
- the client's walk step, walk speed, turn rule and walk/stand action selection;
- the client wheel zoom.

The client routines that compute movement are reconstructed in C (`reconstructed/movement`). They are compared with the client's instructions under Unicorn (`scripts/validate_movement.py`). The native session is `native/core/mu_walk.*`, with the front ends `mu-world` (window) and `mu-walk` (headless software).

Labels used below:

- **Verified** means the C port equals the client's instructions on every compared case.
- **Static** means a reading of decoded instructions that was not executed.
- **Placeholder** means native code that is not client behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

The validator pins every compared routine body by SHA-256. The starts, lengths and digests are in its `ROUTINES` table and in its JSON report.

## 1. The hero's logic step (static, routines verified)

The in-world tick `0x0185613e` calls MoveHero `0x016a9150` at `0x01856d3a`, and later MoveCharacters `0x0137a7ce` at `0x01856eca`. The hero (`[0x0a39d754]`) is skipped by the per-character mover `0x013b852a` and moves only inside MoveHero.

For a plain walk (movement type `c+0x39` = 0, no buff or auto-move state), MoveHero `0x016a9a74..0x016a9cf2` runs these steps while Movement `c+0x38` is set:

1. **SetPlayerWalk `0x0139002a`.** It updates the run counter and sets the walk action and its PlaySpeed.
2. **MovePath `0x012b0846`(c, 1).** When this returns 1 (the hero reached the last cell):
   - `0x016a8904(c, 1)` sends the stop position and clears Movement;
   - SetPlayerStop `0x0138fe69` resets the run counter to 0 and sets the stand action.
3. **MoveCharacterPosition `0x0137b351`.** This runs otherwise. It moves the hero by CharacterMoveSpeed `0x013957b5` along its heading.

The click branch comes after the walk step (`0x016ac4b4..0x016ace4f`):

- **Pick and target.** RenderTerrain(1) picks a tile, and TargetX/Y = `(uint8)(int)(CollisionPosition/100)`.
- **While moving.** The hero re-paths only when its tile `c+0x180/0x184` is within one tile of `(int)(position*0.01)`.
- **New path.** When the target differs from the tile, or the hero stands, PathFinding2 `0x012b0e85`(PositionX, PositionY, TargetX, TargetY, &Path, 0.0, 2) runs. On success, SendMove `0x016b5cd0` sets Movement = 1.
- **One-step delay.** A click therefore starts moving on the next step, and the walk action appears one step after the click.
- **Safe zone.** The safe-zone byte `c+4` is `TerrainWall[tile] & 1`. It is set in the render pass for visible characters (`0x013b23f8` via `0x0129de3a`).

**Path record `c+0x3194`:**

- current cell `+0`, spline sub-step `+1`, cell count `+2`;
- X `+3..+0x11` and Y `+0x12..+0x20` (15 cells).

**Movement (verified):**

| Routine | Rule |
|---|---|
| MovePath `0x012b0846` | Four spline points per cell through the cell centres `((cell+0.5)*100)`, weights (-0.0703125, 0.8671875, 0.2265625, -0.0234375), (-1/16, 9/16, 9/16, -1/16), mirrored, then the next centre. The tile position is written when a sub-step starts. When `(int)sqrt(dx²+dy²) <= 30` the sub-step advances. At the last cell the hero snaps to the point and the routine returns 1. Otherwise it turns toward the point: it snaps when FarAngle >= 45, else TurnAngle2 turns by half the difference |
| CreateAngle `0x012aed9e` | Heading from `atan(dy/dx)` (float wrapper over CRT atan), axis cases below 0.0001 |
| FarAngle `0x012af218`, TurnAngle2 `0x012aefff` | Wrapped difference and the bounded turn |
| MoveCharacterPosition `0x0137b351` | `position += VectorRotate((0, -speed, 0), AngleMatrix(angles))`. z is RequestTerrainHeight. Exception: a Dinorant `0x1a03` outside the safe zone gets +30 (+90 in worlds 8, 10 and 0x84). A 0x7a7-type object bobs. Then timer `o+0xb4` += 0.15 |
| CharacterMoveSpeed `0x013957b5` | Units per 40 ms step. A Player (type 0xa91, kind 1) with no helper, mount, wing or buff walks at **12 while the run counter is below 40, 15 from 40** (= 300 / 375 units = 3 / 3.75 tiles per second). Mounts, pets, wings and buffs give 15/16/17/19/20 or ×0.5/×0.33, as ported. The Chaos Castle group forces 15 |
| RequestTerrainHeight `0x016cc9e2` | Bilinear height, y first, then x. Special height on attribute 0x40 or outside the map. 0 in scene states 1, 2 and 4 |
| SetAction `0x012affa4` | The prior action and frame take the current ones and the frame restarts at 0, when the action is new and in range |

**Walk/stand selection** (verified in the minimal domain). The domain is an unarmed character with no item, wing, helper, mount, buff or flight state, in world 0, scene 6. SetPlayerWalk (up to its tail `0x01391c19`) and the player stop selector `0x01391e55` were executed for all 256 class bytes:

- **Run counter.** In a safe zone (world not 0x84) it resets to 0. Otherwise, below 40, it grows by 1 per step for base classes 3, 4, 6 and 7. Equipment, stats and buffs add other growth conditions, which are not ported.
- **Walk action.**
  - 0x4f (base class 11: 0x63) once the counter reaches 40. There is no safe-zone test here; the zone acts only through the counter reset.
  - Otherwise 0x32, or 0x33 for base classes 2, 5, 7, 8, 9, 12 and 14.
  - SetPlayerWalk rewrites the walk PlaySpeeds each step: 0.33 walk and 0.34 run; base class 6 uses 0.32 and 0.28.
- **Stand action** per base class 0..15: 1 1 2 1 1 3 1 5 6 6 1 1 2 1 6 8. Their PlaySpeeds come from the player loader block `0x018311f7..0x018321e1`, executed: 0.28, and 0.24 for action 3.

These tables are isolated in `mu_player_walk_*` and `mu_player_stop_*` so that the NATIVE-ACTOR-001 action tables can replace them.

## 2. The path finder (verified)

PathFinding2 `0x012b0e85` calls the path object (`[0x06fce374]`, 256×256 over TerrainWall) through FindPath `0x012b1c45`(sx, sy, tx, ty, error check 1, wall mode, flag, distance, 500, mask 0x1e). The search works as follows:

- **Pop.** It pops the open cell of lowest priority. The open list is a binary tree keyed by priority with equal keys to the right, and the leftmost node is popped, which gives first-in first-out order among equal priorities.
- **Cost and parent.** The popped cell's cost is the minimum, over its closed neighbours, of the neighbour's cost plus 5 (straight) or 7 (diagonal). That neighbour becomes its parent.
- **Close.** The cell is closed, and if it is the target the path is built.
- **Open neighbours.** Every neighbour whose `(attribute & 0x1e) < wall mode` is opened. Its priority is `((|a-b|*5 + min(a,b)*7 + 1)*3)/4` plus the popped cell's cost.
- **Object cells.** Cells in the object grid `0x0b7b5420` open only as the target.
- **Fallback.** When FindPath fails, the wall mode becomes 4 if the start is a safe-zone cell, or if the target is a safe cell without a character. A second search without the error check then goes to the cell closest to the target by the heuristic.
- **Result.** The first 15 cells of the path are copied.

Only the single-target branch (distance 0, the plain click) is ported. The target-area branch `0x012b2584` (distance > 0, attacks and talks) is not.

The neighbour order is the direction table at `0x01cf1640`. It lies in the executable's packed data section (encrypted in the file), but the runtime capture of that section has it:

- **Source.** `evidence/x86-linux-capture-04/main-01ced000.bin`, SHA-256 `0571c519…57c1dc6f`. This is compatibility-environment evidence: a Linux Wine run whose text region equals capture09.
- **Value.** The table is (-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1), in row-major order.
- **Use.** The port takes the order as a parameter. The validator checks that the capture holds this table, uses it in half of the path cases and varies the order in the rest. The native session uses the client table.
- **Different table.** SendMove's packet direction table `0x01cf0fc8` is a separate table with a clockwise order.

## 3. Camera data of a world

The OpenWorld path is static; the loader was decoded.

**Loading.**

- OpenWorld `0x0182876e` asks the camera-info singleton `0x0098647b` (object `[0x01d1dc24]`) to load `Data\World*\Camera_Angle_Position.bmd` (scan `0x0098acbd`, keyed by folder number) and `Data\G_Camera_Angle_Position.bmd` (key 0).
- The singleton selects the record of the world's folder, else key 0 (`0x0098b55e`).
- It sets CameraFOV from it (`0x0098c5d6`).

**File format** (loader `0x0098af0c`):

- The file is `"MAP\x01"` plus a Modulus envelope `0x016ced37` (else the v12 cipher `0x0098c5f2`), the same scheme as `EncTerrain*.map`.
- The plaintext is written to `CAP_%d.ini` and read with GetPrivateProfileStringA.
- Keys:
  - `[CAMERA ANGLE]` Angle X/Y/Z;
  - `[CAMERA POSITION]` Position X/Y/Z (30-character buffer);
  - `[CAMERA DISTANCE]` Distance and Z_Distance;
  - `[CAMERA FOV]` FOV (11-character buffers, empty default, atof).
- Record layout: angle +0, position +0xc, Z_Distance +0x18, Distance +0x1c, FOV +0x20.

**Lorencia** (World1) has no file of its own, so it uses the global record: **FOV 39**, Distance 9.1, Z_Distance 0.179. MoveMainCamera's level-0 far plane is `2000 * Distance * Z_Distance * scale` (`0x0098ac45`) = **3257.8**, and the projection uses ×1.4. The scale `+0x10` is 1. Only the FOV-65 camera mode raises it, through `lerp(1, 2.2, …)` in `0x016d20d9`. The wheel zoom table is {20, 30, world FOV}. Six installed worlds carry their own record (World94, 95, 111, 133, 134 and 144); for example World95 has FOV 35 and Distance 32.1.

**Near plane.** CameraViewNear `0x01cf162c` has no writer in the code. It is a static initializer in the packed `.data` section. The same runtime capture holds:

- near **20.0**;
- far 2000 and FOV 55, the initial values that OpenWorld/MoveMainCamera overwrite;
- WindowWidth/Height 1024×768, the configuration of that run.

The native session uses near 20.

## 4. Native session

`native/core/mu_walk.c`, per logic step (client accumulator, 40 ms):

1. Key scan.
2. MoveHero: the hero's walk step, then the click start.
3. The Player animation step, with the current action's PlaySpeed.

Per frame:

1. Safe-zone byte from the hero's tile.
2. MoveMainCamera, with the hero tile `c+0x180/0x184` and the world camera record.
3. BeginOpengl and the mouse ray.

Other details:

- Terrain heights, attributes and picking come from `mu_terrain`.
- The hero is assembled by `mu_character`: Player.bmd plus the class parts.
- `mu-world --walk` scripts clicks. Each tile centre is projected with the client projection `0x0184a244`, then a mouse move, left down and left up are sent. These pass through the window procedure's mouse globals, the pick, the path finder and SendMove like a real click.

Viewer choices, not client readings:

- the box of terrain drawn around the hero (34 tiles);
- the red click marker (the client draws a cursor effect);
- sky colour;
- no static objects (the `.obj` files do not decode, see the terrain finding);
- the class's parts only, without weapons.

**Run it.**

```sh
make -C native && make -C native world
G="$MU_GAME_ROOT"
native/build/mu-world --game-root "$G"                                  # Lorencia town square, class 0x01
native/build/mu-world --game-root "$G" --headless --backend gl --frames 900 --every 3 --out-dir DIR \
    --walk "137,131 141,135 143,140" --wheel "290:1 470:-1"
native/build/mu-walk  --game-root "$G" --headless --backend soft ...    # software rasterizer, no SDL2/GL
```

## Verification

`scripts/validate_movement.py` uses the strict machine of `validate_camera.py`:

- an undefined read stops a case;
- the image is read-only;
- imports are stubs.

On top of that it adds a tracked 4 MiB heap for the path object and its nodes, with operator new as a bump allocator, and two documented exceptions:

- `_chkstk` page probes;
- byte locals pushed as dwords whose callee reads only the byte.

Each replaced callee, and the reason it is replaced, is listed in the report.

**Synthetic inputs.** Two values are supplied by the harness:

- **Domain records.** The subsystem predicates of CharacterMoveSpeed and the minimal-domain records for the walk/stand selection are supplied by the harness.
- **CRT memset feature word.** Word `0x0bdcb284` is set to 2, as in validate_bone_tracks.

**Final local run** (`--cases 1000 --mutations --game-root`, 17,890 comparisons, 0 mismatches, 15 minutes on one core; the data-section check passed in a separate 100-case path run):

| Family | Cases |
|---|---:|
| CreateAngle, FarAngle, TurnAngle2 | 1,000 each |
| MovePath | 2,000 |
| RequestTerrainHeight | 2,000 |
| CharacterMoveSpeed | 2,000 |
| MoveCharacterPosition (executed AngleMatrix, VectorRotate, height, sin) | 996 |
| SetAction | 1,000 |
| SetPlayerWalk, all 256 class bytes × safe 0/1/2 × 7 run values | 5,376 |
| Stop selector, 256 class bytes × safe 0/1 | 512 |
| Loader stand PlaySpeeds | 6 |
| PathFinding2 and FindPath. Synthetic maps plus the installed attribute maps of worlds 0, 2, 3 and 142; the client neighbour order and two others; error check, iteration limit and mask varied in the direct calls | 1,000 (691 PathFinding2, 309 direct FindPath) |

**Mutation check.** Sixteen planted mistakes are all detected, for example:

- an arrival radius `< 30`;
- swapped spline weights;
- a snap at `> 45`;
- walk speed 10;
- velocity +y;
- heuristic weight 6;
- a parent taken on equal cost;
- last-in first-out among equal priorities;
- a wall test without the mask.

**Portable tests** (`make test`):

- `reconstructed/movement/test_client_movement.py`: analytic checks plus an independent Python statement of FindPath on 40 random maps.
- `native/tests/test_native_world.py`, which runs `mu-walk` on a synthetic world, Player and camera records:
  - arrival on the clicked tile at exactly 12 units per step;
  - walk 0x32 then stand 1;
  - run 0x4f after 40 steps for class 3, and the safe-zone reset;
  - the wall stop;
  - the camera record choice and far plane;
  - the wheel zoom to FOV 30;
  - determinism and refused inputs;
  - GL headless.
- **Private tests** (`MU_RECOVERY_INTEGRATION=1`): the instruction comparison, and a walk across Lorencia town that checks FOV 39 and the global record, three arrivals, the safe zone, and 12.0000 units per position step.

## Local renders

These are in `~/Documents/mu-mac-tools/native/renders/world/` and are not committed:

- `lorencia-gl/`: 300 frames, OpenGL headless 1280×800, every 3rd frame of a 900-frame walk (36 s game time).
  - Class 0x01, starting on tile 133,127 in Lorencia town.
  - 18 scripted clicks, 18 arrivals, 713 position steps at 12.0000 units.
  - Wheel zoom 39 → 30 at frame 290 and back at frame 470.
  - Per-frame state in `lorencia-gl.jsonl`.
- `lorencia-soft/`: the same run with the software rasterizer, 960×600, every 10th frame.
- `lorencia-gl-contact.png`: 16 frames of the walk.
- `window-check.png`: window-only screenshot of `mu-world` walking in Lorencia. The window ran at 24.98 FPS (cap 25) over 16 s, with 400 logic steps and 8 arrivals.

## Unresolved

- **Packed data.** The direction table and near plane come from a compatibility-environment capture of the packed `.data` section, not from a native Windows run. They are static data with no code writers.
- **Not ported (static only).** The path finder's target-area branch; SetPlayerWalk and SetPlayerStop outside the minimal domain (weapons, mounts, flight, buffs); MoveHero's attack, talk, pick-up and auto-move branches; the move and stop packets.
- **Live check.** No live in-game comparison of the walk speed or the path was made.
- **Parallel work.** Another worktree (`native-path`) works on the path finder in parallel with its own validator. The two ports should be reconciled when both merge.
- **Static objects.** Static objects, their collision-object cells `0x0b7b5420`, and the character bit `2` that MoveCharacters sets on occupied tiles are absent in the native session.
