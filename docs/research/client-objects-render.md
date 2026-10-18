# World objects at runtime: creation, move pass, render pass, light and animation (NATIVE-OBJECTS-002)

[client-objects.md](client-objects.md) (NATIVE-OBJECTS-001) covered the `.obj` loader, the record layout and the
model table. This milestone follows what the client does with the objects afterwards:

- CreateObject builds the OBJECT;
- the move pass runs once per logic step (alpha, animation, light sources, fires, sounds);
- the render pass runs once per frame (sector and object culling, body light from the terrain light, the pose,
  RenderBody with the blend mesh).

All of this is authored C in `reconstructed/objects/object_render.{h,c}`. `scripts/validate_object_render.py`
compares it with the client's instructions in Unicorn, and `scripts/live_object_state.py` compares it with object
lists read from a running client. `native/core/mu_objects_runtime.c` runs it in `mu-world`, `mu-walk` and
`mu-terrain render --object-steps N`.

Labels:

- **Compared**: the authored C ran against the actual instructions in Unicorn and agreed bit for bit.
- **Live**: compared with objects read from a running client this project started.
- **Static**: a reading of decoded instructions that was not executed.
- **Stand-in**: native behaviour that is not a client reading.

Inputs are the pinned restored text (`2bd5f2e9…`) and second image section (`c985e2e6…`) of
[client-objects.md](client-objects.md). The names are ours.

| Routine | Role | Bytes (SHA-256, first 16) |
|---|---|---|
| `0x016d8538` CreateObject | sector, generic fields, world type defaults | `7de7ab043a1b8af0` |
| `0x016d82c7` MoveObjects | per logic step: sector walk, MoveObject per object | `82ad21a9be9f2610` |
| `0x017ff238` MoveObject | alpha, animation speed and tick, world object cases | `37f1b5feb59f9988` |
| `0x01616930` CreateFire | fire/smoke particles and their terrain light | `c151f42a8ebbf2d2` |
| `0x012af883` | alpha towards the target | `b94e3e222018f191` |
| `0x016d5020` RenderObjects | per frame: sector and object TestFrustrum2D, draw order | `8443b9fee71f41d9` |
| `0x016d4fe4` RenderObject | `0x017ec896` setup + `0x017edf43` draw | `b871f4435cace570` |
| `0x017ec896` | alpha gate, model fields, body light, Animation, Transform | `2439015f9377ea3f` |
| `0x017edf43` | HiddenMesh, shadow, custom render, RenderBody | `ee695964abc4b115` |
| `0x017ec3d8` | body light | `f470fb563cb68b68` |
| `0x016cb2f7` / `0x016cb08d` | RequestTerrainLight on the primary / frame light | `92efc3ddaccffbf2` / `9223523061702bd3` |
| `0x00e4c6ba` / `0x00e4c95e` / `0x00e4bfff` | Tormenta handler slots 0x2c, 0x30, 0x1c (vtable `0x01aabd10`) | `b0d7ac67a38c3045` / `781bfc06d03f0f16` / — |

## 1. Where the passes run (static)

In the in-world tick `0x0185613e`, the frame-light copy `0x016ca4fa` (`0x0185674c`) runs before MoveObjects
(`0x01856a45`). The object light sources that MoveObject adds with AddTerrainLight therefore land in this step's
frame light, which RenderTerrain and the objects read when they are drawn. The scene-5 and scene-3 ticks call the
same two routines.

The main render `0x0185916b` calls RenderObjects twice (`0x0185982d`, `0x01859853`, around RenderTerrain). The
second pass `0x016d6949`, after the characters, draws objects with `+0xa` set in a list of worlds. It is not
reconstructed (see Limits).

## 2. Object fields (compared and live)

These are the OBJECT fields the routines use. The comments in `object_render.h` list them all.

| Offset | Field | Set by |
|---|---|---|
| `+5`, `+6`, `+7` | light enable (→ model `+0x50`), full light (no 0.1 factor), frame light instead of primary | record `+0x2c..+0x2e` |
| `+0xa` | drawn after the characters | Tormenta handler |
| `+0xb` | visible | RenderObjects; MoveObjects clears it in invisible sectors |
| `+0x2a`, `+0x2c` | action, prior action (u16) | 0 |
| `+0x68` | HiddenMesh: −1 none, **−2 = the object is not drawn** (`0x017edf82`, when `[0x0b437bfc]` is 0), k skips mesh k | hidden byte, world cases |
| `+0x74`, `+0xa8`, `+0xac`/`+0xb0` | BlendMesh, BlendMeshLight, blend texture offset u/v | world cases |
| `+0xbc` | animation speed | 0.16, world cases |
| `+0xc0` | TestFrustrum2D range of the render pass | −30, world cases |
| `+0xd0`/`+0xd4` | frame, prior frame | the tick |
| `+0xd8`/`+0xdc`/`+0xe0` | alpha target, alpha, alpha rate | 1, 1, 0.1 (constructor; live value) |
| `+0xec` | light added to the terrain light | record `+0x1c` |
| `+0x1e8` | copy of the body light | body light |

This settles the `+0x68 = −2` question that NATIVE-OBJECTS-001 left open. It is HiddenMesh, and −2 means the object is
not drawn at all. CreateObject sets it for Lorencia's PoseBox01 (type 0x85), and the Tormenta handler sets it for
types 0..9 and 0xb4..0xc8.

## 3. CreateObject and the world handlers (compared, live)

CreateObject computes the sector `(int)(x/1600)·16 + (int)(y/1600)` and returns 0 outside 0..15. It appends the
object to the tail of that sector's list (`+0x350`/`+0x354`). Then it writes the generic fields: alpha 1, target 1,
speed 0.16, `+0xc4` 50, HiddenMesh −1/−2, BlendMesh −1, BlendMeshLight 1, range −30, start position = position, head
angle 0, box (−40,−40,0)..(40,40,80).

**World 0 (Lorencia)** has its own cases in CreateObject:

| Type | Change |
|---|---|
| 0, 1 (Tree01/02) | box ±150 × 500 high, speed `1/scale·0.4` |
| 0x34 Bonfire | BlendMesh 1 |
| 0x3b (59) | speed 0 |
| 0x50 Bridge | range −50 |
| 0x5a StreetLight, 0x96 Candle | BlendMesh 1, speed 0.3 |
| 0x60, 0x61 | speed 0.3 |
| 0x62 Carriage01 | BlendMesh 2 |
| 0x69 Waterspout | BlendMesh 3 |
| 0x75 / 0x76 / 0x77 / 0x7a | BlendMesh 4 / 8 / 2 / 4 |
| 0x85 PoseBox | HiddenMesh −2, box height 160, operable-object table `0x016d9f51` |
| 6, 0x91, 0x92 | operable-object table `0x016d9f51` |

**World 0x8d (Tormenta Island)** has no case of its own. Its handler's slot 0x2c `0x00e4c6ba` (reached through the
world manager `0x00ea594b` → `0x00ea2ad6`) does the following:

| Types | Change |
|---|---|
| 0xb4..0xc8 | HiddenMesh −2 |
| 0x24..0x2a | `+7` (frame light) cleared |
| 0..9 | HiddenMesh −2; 0 and 1 also get range −100 |
| 0x1f, 0x20 | range −1000 and `+0xa` |
| 0xc, 0x1e, 0x22, 0x41, 0x48, 0x4b..0x50, 0x76, 0x79..0x7b | `+0xa` |
| 0x21 | range −175 |
| 0x7d, 0x7f | range −150 |
| 0x27, 0x80 | range −300 (0x27 writes −50 first and falls through) |
| 0xc7 | range −1500 |

Other worlds keep the generic fields, and the C returns `MU_OBJ_UNSUPPORTED`.

**Compared:** 2,000 cases, worlds 0 and 0x8d, random records including off-map and NaN positions. The full object
bytes, the sector links and the registration calls are equal.

In world 0x8d the chain of world-group hooks before the world manager is stubbed. Each stub returns 0, and the
hooks' own world tests are not executed. The handler slot is then run as client code on the result.

**Live:** each object in a live snapshot was rebuilt into its record and passed through `mu_obj_create`. The 35
fields that CreateObject writes were compared, excluding the values the running game drives (see the dynamic list
in the script).

| Snapshot | Objects equal | Result |
|---|---|---|
| Lorencia, 2026-10-17 | 2,833 / 2,833 | |
| Lorencia, 2026-10-18 | 2,833 / 2,833 | |
| Tormenta Island | 8,061 / 8,061 | One exception, the animation speed: 1,957 objects of 45 types carry a per-type speed (0.1..0.5) that neither CreateObject nor the handler writes. The source was not traced (see Limits). |

Every Tormenta object of types 0x24..0x2a has `+7 = 0`, as the handler requires (1,691 objects).

## 4. MoveObjects and MoveObject (compared, live)

**MoveObjects `0x016d82c7`.** It runs with `[0x01cf15fc] = [0x01cf1600]` and clears `[0x0bdc5890]`. It walks sector
i (x) and j (y) in list order:

- In a sector visible in the last render pass, live and visible objects get MoveObject, then `0x0180249e` (world 10
  only), then `0x017ec026` (an event-door routine, gated by globals).
- In an invisible sector, the world handler's slot 0x1c decides whether MoveObject still runs:
  - the base class `0x00d5cbbc` answers no;
  - Tormenta `0x00e4bfff` answers TestFrustrum2D(x·0.01, y·0.01, range) for types 0x1f/0x20.

  Live objects then get `0x017ec026`, and visible is set to 0.

Afterwards the pass decrements `[0x01cf15f4]` and restores the world.

**MoveObject `0x017ff238`** runs these steps in order:

1. **Roof fade.** World 0, types 0x7d/0x7e (HouseWall05/06): target 0 when HeroTile is 4 (the pub floor), else 1.
   World 2, types 0x51/0x52/0x60/0x62/0x63: target 0 when HeroTile is 3 or ≥ 10.
2. **Alpha step `0x012af883`.** With `+0xc`, alpha moves linearly in steps of 0.05 and is clamped to 0..1.
   Otherwise `alpha += (target − alpha)·rate`. Then `BlendMeshLight = min(BlendMeshLight, alpha)`. When
   `0.01 > alpha`, MoveObject returns. Without a model it also returns.
3. **Speed.** `+0xbc`, with world exceptions:
   - world 8 type 8: ×4;
   - 0x39/0x3a types 0x10/0x11/0x44, 0x50/0x51 types 0x42/0x6b, 0x5b/0x5c types 0x10/0x34/0x39/0x65, 0x5e type 5:
     the action's PlaySpeed;
   - 0x73 type 0x3c: 0.16;
   - 0x87/0x88: PlaySpeed for listed types in action 1 (0xb5 in action 2).
4. **Tick.** The animation tick `0x012b4dd3(&frame, &prior frame, &prior action, speed, position, angle)`, which is
   reconstructed as `mu_animation_tick` (NATIVE-VIEW-001).
5. **Login and character-select scenes 3/5.** Types 0x12d/0x12e scroll v by `−(t % 4000)·0.00025`; type 0x12f is not
   ported.
6. **The world's cases.** World 0 has its own switch. Tormenta goes through the world manager to the handler's slot
   0x30 `0x00e4c95e`.

**Lorencia's cases:**

| Type | Effect |
|---|---|
| 0x32 FireLight01 | CreateFire(0, o, 0, 0, 200) |
| 0x33 FireLight02 | CreateFire(0, o, 0, −30, 60) |
| 0x34 Bonfire | CreateFire(0, o, 0, 0, 60); BlendMeshLight `(rand%6+4)·0.1` |
| 0x37 DungeonGate | CreateFire at (−150, −150, 140) and (150, −150, 140) |
| 0x50 Bridge | CreateFire at (90, −200, 30) and (90, 200, 30) |
| 0x5a StreetLight | l = `(rand%2+6)·0.1`; AddTerrainLight(x, y, (l, 0.8l, 0.6l), 3) |
| 0x96 Candle | l = `(rand%4+3)·0.1`; AddTerrainLight(x, y, (l, 0.6l, 0.2l), 3) |
| 0x75, 0x7a | window flicker: BlendMeshLight `(rand%4+4)·0.1` |
| 0x76, 0x77 | v = `(−(int)t % 1000)·0.001` |
| 0x82..0x84 (Light01..03) | CreateFire(type − 0x82, o, 0, 0, 0), then HiddenMesh −2 (invisible light markers) |

**CreateFire `0x01616930`.** The offset is rotated by AngleMatrix(angle), added to the position and jittered by
`rand()%16 − 8` per axis. Then, by type:

- type 0: l = `(rand%6+6)·0.1`, light (l, 0.6l, 0.4l); on `rand%2 == 0`, CreateParticle(Fire01 `0x7f3c`, subtype
  `rand%4`); always AddTerrainLight(range 4);
- types 1 and 2: on `rand%2 == 0`, a smoke particle (smoke01 `0x7f5a`, subtype 0 or 2) with the object's light.

**Tormenta's slot 0x30** only plays ambient sounds when the hero is near:

- type 6 at `1300·scale` → sound 0x581;
- 0xb7 at 450 → 0x584;
- 0xc8 at 800 → 0x583.

The distance uses the C runtime sqrt.

**Compared:**

- MoveObjects: 2,000 cases (14,049 objects moved) with equal call order, visibility bytes and globals.
- Slot 0x1c: 2,000 cases.
- MoveObject: 2,000 cases.
  - The generic part ran for 19 worlds up to the switch at `0x017ff8ad`.
  - World 0 ran complete, with CreateFire, AngleMatrix, VectorRotate and the C runtime sin/cos as client code.
    `rand` is the MSVC recurrence with a per-case seed, matching the C callback.
  - World 0x8d ran complete, with its handler slot as client code.
  - The tick arguments, every AddTerrainLight, CreateParticle and sound call, and the object bytes are equal.

**Live:** two Lorencia snapshots 1.046 s apart show the animation advance of the six visible animated objects:

- types 72, 98 (speed 0.16): +4.16;
- types 90, 96 (speed 0.3): +7.80.

That is 26.0 ticks each, one per 40 ms logic step. BlendMeshLight values seen on 0x7a are {0.4, 0.6, 0.7} and on
0x75 {0.5, 0.7}, inside `(rand%4+4)·0.1`. The live frames show which models animate: in Lorencia only types 72, 90,
96, 98, 105 and 150 have a non-zero frame (the trees and grass have one key). In Tormenta, 15 types animate.

## 5. RenderObjects and RenderObject (compared, live)

**RenderObjects `0x016d5020`** works as follows:

- The counter `0x06fc9c90` resets above 40 and is incremented.
- The bias is −10 in world 10, else 0.
- Sector (i, j) is visible when TestFrustrum2D(i·16+8, j·16+8, r) passes, where r is:
  - −180 by default;
  - −300 in worlds 0x86..0x88, 0x8a, 0x8c and 0x8d;
  - −200 in world 0x89.
- Objects are walked in list order:
  - The per-world predicate `0x017fcd18` answers yes for objects drawn before the test. In world 0 those are types
    0x37 and 0x3c, a static reading; the predicate's default chain was not executed.
  - Such objects get RenderObject(o, 0, 0, 0, −1, −1) and RenderObjectVisual `0x017f9758`. Their attached effects are
    updated when `0x00d99e3f` says so. Then visible = TestFrustrum2D(x·0.01, y·0.01, range + bias), computed when the
    sector is visible (or in top view) and the object is live.
  - Every other object gets the test first and is drawn only when visible.

**RenderObject `0x016d4fe4` (static-object call).** The setup `0x017ec896` does this:

1. In the Chaos Castle worlds alpha drops by 0.15 when the hero flag is set.
2. If `0.01 > alpha`, it stops.
3. It writes the model fields: height 0, `+0x51`, the body light, scale, action, origin, `+0xcb`.
4. It calls Animation(bones, frame, prior frame, prior action, angle, head angle, 0, !translate). The bone buffer is
   the object's own when `+0xd` is set, else `0x06fce398`.
5. It sets bone scale 1 and calls Transform(bones, box min, box max, OBB, translate, 0, 0.4, `+0xe4`, `+0xe8`).

The draw `0x017edf43` then:

1. returns for HiddenMesh −2;
2. draws flags 0x82 when `+0x80 == 0x80`;
3. applies the buff tint;
4. runs the shadow block when `+3` is set (not reconstructed);
5. calls the per-world custom render `0x017f76ec` and the render registry `0x01d1e010`;
6. otherwise calls **RenderBody(2, alpha, BlendMesh, BlendMeshLight, u, v, HiddenMesh, −1)**, which maps directly
   to the body port `0x012bb35a` (select, colour scale, uv offsets, skip mesh);
7. calls the after-render visuals `0x017f919e`.

**Body light `0x017ec3d8`.** Two types are special:

- type 0x7dc: (0.6, 0.6, 0.6);
- type 0x444: `sin(t·0.003)·0.5 + 0.5`.

Otherwise:

```
model +0x50 = object +5
light = RequestTerrainLight(+7 ? frame light 0x0b9f5430 : primary light 0x0bab5430, x, y)
light *= 0.1 unless +6
colour (model +0x54) = light + object light (+0xec);  copied to +0x1e8 when +5 or +6
```

**RequestTerrainLight** returns (0, 0, 0) in three cases: scene state 1, 2 or 4; terrain not ready
(`[0x0b5e3ea4]`); or `(int)(x/100)`, `(int)(y/100)` outside 0..254. Otherwise it interpolates bilinearly,
in this exact binary32 order:

```
a = (L[y+1][x] − L[y][x])·fy + L[y][x]
b = (L[y+1][x+1] − L[y][x+1])·fy + L[y][x+1]
out = (b − a)·fx + a
```

**RenderObjectVisual, Lorencia Waterspout (0x69).** BlendMeshLight 1 and v = `(−(int)t % 1000)·0.001`, compared up to
its first effect call. The smoke and flare sprites it creates at named bones are not reconstructed.

**Compared:**

| Routine | Cases |
|---|---|
| RequestTerrainLight | 2,000 |
| body light | 2,000 (all flag and type paths) |
| RenderObjects | 2,000 (11,733 draws, 99,756 sector tests) |
| RenderObject | 1,839 |
| visual | 2,000 |

The 1,839 RenderObject cases leave out 161 that reached a branch the C reports as unsupported (special types,
shadow, owner): those are not compared. Call logs (Animation, Transform, RenderBody arguments), model fields and
object bytes are equal.

**Live:** the body-light copy `+0x1e8` of the objects drawn in the snapshot frame (`+0xb`), for the plain flags
(`+6`, `+7`), was set against RequestTerrainLight on the native primary light (`mu-terrain export`, NATIVE-TERRAIN-001)
plus the object light.

| Snapshot | Bit-identical | Brighter |
|---|---|---|
| Lorencia, day 1 | 89 / 169 | 80 |
| Lorencia, day 2 | 81 / 155 | 74 |
| Tormenta | 70 / 75 | 5 |

None is darker. That is what the frame light predicts: where no source reached the tile, the frame light equals the
primary light, and AddTerrainLight only adds. It also checks the native primary light against the client's at
runtime.

## 6. Verification summary

Final local run: `scripts/validate_object_render.py --cases 2000 --mutations` (about 30 s). Report:
`~/Documents/mu-mac-tools/native/scratch/objects3/reports/object-render-final.json`.

| Family | Cases | Equal |
|---|---:|---:|
| light (RequestTerrainLight, both grids) | 2,000 | 2,000 |
| body_light | 2,000 | 2,000 |
| create (worlds 0, 0x8d, Tormenta slot 0x2c) | 2,000 | 2,000 |
| move_pass | 2,000 | 2,000 |
| handler_moves (Tormenta slot 0x1c) | 2,000 | 2,000 |
| move (19 worlds generic, 0 and 0x8d complete) | 2,000 | 2,000 |
| visual (Waterspout part) | 2,000 | 2,000 |
| render_pass | 2,000 | 2,000 |
| render (static-object call) | 1,839 (+161 not compared) | 1,839 |

Nine planted mistakes, each detected on a 600-case rerun:

| Planted mistake | Detected |
|---|---:|
| interpolation axis | 301 |
| 0.1 factor | 198 |
| tree speed | 14 |
| Tormenta 0x27 fall-through | 4 |
| move pass visibility | 528 |
| street-light range | 11 |
| roof HeroTile | 6 |
| Tormenta sector range | 46 |
| HiddenMesh −2 | 89 |

Live comparisons, run with `scripts/live_object_state.py` (sections 3 to 5):

- creation: 13,727 / 13,727 objects;
- body-light copy: 240 bit-identical, the rest brighter only;
- frame advance: 26 ticks per 1.046 s.

## 7. Native module

`native/core/mu_objects_runtime.c` provides five entry points:

- `mu_objects_start` creates every OBJECT with `mu_obj_create` and links the sectors.
- `mu_objects_step` runs MoveObjects. For each named object it runs MoveObject and carries out the logged calls:
  - the tick goes through the object's model (`mu_model_tick`);
  - AddTerrainLight calls are kept for `mu_objects_apply_lights`, which applies them after each frame-light copy;
  - CreateParticle calls go to the stand-in particles.
- `mu_objects_visibility` runs RenderObjects with the CreateFrustrum2D polygon.
- `mu_objects_prepare` runs RenderObject. It sets body light, lighting flag, pose at the object's frame and the
  RenderBody arguments, then calls RenderObjectVisual.
- `mu_objects_render_raster` is the software path.

`mu-world`/`mu-walk` call them in the client's order:

- MoveObjects in the step hook, after the hero and the characters;
- object lights after `mu_world_frame_box`;
- the render pass and the draws after RenderTerrain;
- the particles after the characters.

`mu-terrain render --objects FILE --object-steps N` runs N steps before drawing. Live sidecars next to the plaintext
are used where the creation case is not reconstructed:

- `EncTerrain<n>.hidden` types, for worlds other than 0 and 0x8d;
- `EncTerrain<n>.velocity`, the Tormenta speeds, written by `scripts/live_object_state.py --velocity-out`.

Stand-ins and viewer choices:

- **Particles.** The legacy particle system (CreateParticle `0x0168fafd`, MoveParticle/RenderParticle) is not
  reconstructed. Fire and smoke events draw as billboards of the client's bitmaps (`Effect/Fire01.jpg`,
  `Effect/smoke01.jpg`):
  - fire: additive, 24 steps, rising 2.5 units per step, shrinking;
  - smoke: alpha-blended, 32 steps, growing.
- **Frame-light copy.** `mu-world` copies the frame light each rendered frame (NATIVE-TERRAIN-002), so the last
  step's lights are re-applied after each copy. In the client the copy and the sources share the logic step; the
  resulting light per frame is the same.
- **CRT rand.** One MSVC seed (1) shared by the object routines. In the client `rand()` is shared with everything
  else.
- **Unported branches.** RenderObjectVisual, the after-render visuals, the custom render and the registry are not
  ported. The draw uses the generic RenderBody unless the C reports a custom render. Attached effects (`+0x3d0`)
  are taken as empty, and PlaySpeeds as 0; worlds 0 and 0x8d never ask for them.
- **Sounds.** Tormenta's sound events are counted, not played.

Renders, local only, under `~/Documents/mu-mac-tools/native/renders/objects3/`, 1600×1000 headless GL unless marked.
"before" is the NATIVE-OBJECTS-001 build: action 0, frame 0, primary light at the tile, all objects in the box.

- `lorencia-147-137-{before,after}-gl.png`, `lorencia-147-137-after-soft.png`: street lamps light the planters and
  pavement, their blend meshes glow, and the lighting is the bilinear terrain light.
- `lorencia-146-110-fires-{before,after}-gl.png`: the FireLight01/02 fires burn (stand-in particles) and light the
  walls through AddTerrainLight.
- `lorencia-fires-anim.gif` and `-strip.png`: flicker and flames over 60 frames.
- `tormenta-135-10-{before,after}-gl.png`, `tormenta-140-30-after-gl.png`, `tormenta-140-30-anim.gif`/`-strip.png`:
  Tormenta objects lit by the handler's flags (`+5 = 0` gives flat, unshaded light), animated plants, the −2 types
  not drawn.

Headless renders at the default 1280×800 show pale terrain patches and grey grass in Lorencia and Tormenta with this
build and with the NATIVE-OBJECTS-001 build alike. At 1600×1000 they do not appear. It is a terrain-path issue that
depends on the window size, outside this milestone; the renders above use 1600×1000.

## Live read (2026-10-18)

The owner authorized the read, and it followed `GAME-LOCK.md`. The lock was held from 13:47:50 to about 13:51. One
session in the play bottle ran:

- `mu-autologin.sh` from 13:48 to 13:49:34;
- two read-only snapshots with `objread` at 13:50:09 and 13:50:10;
- the client and launcher were closed at 13:50:39.

No character was moved and nothing was written to the client. The autologin entered with the currently selected
character, who stands in Lorencia, so the snapshots are of Lorencia (2,833 objects, as on 2026-10-17). Tormenta Island
was not re-read: that would have needed selecting Nighty in the character list. The Tormenta checks above use the
2026-10-17 snapshot, taken with Nighty at 135,10 (8,061 objects, unchanged). The snapshots stay local in
`~/Documents/mu-mac-tools/native/scratch/objects3/live/`.

## Tests

- `reconstructed/objects/test_object_render.py` (portable): worked examples of every routine on authored grids,
  records and objects.
- `native/tests/test_native_objects.py` `test_object_lifecycle_in_the_walk_session` (portable):
  - a synthetic Lorencia with a street light, a candle and a far street light;
  - creation, culling (2 of 3 in the draw list), one AddTerrainLight per moved object, a tick per move;
  - `mu-terrain render --object-steps`.
- `tests/test_object_render_private.py`:
  - the Unicorn validator (`MU_RECOVERY_INTEGRATION=1`, pinned captures, Unicorn);
  - the live creation comparison (`MU_OBJECTS_DUMP_DIR` with the local snapshots).

## Limits and next steps

- **Other worlds' cases.** These are not ported:
  - CreateObject and MoveObject cases of worlds other than 0 and 0x8d, and the world-group hooks of the default
    chains (stubbed in the comparison);
  - RenderObjectVisual `0x017f9758`, beyond the Waterspout scroll: Lorencia's bone-placed smoke and flares, and the
    other worlds;
  - the after-render visuals, the per-world custom render `0x017f76ec` and the render registry;
  - the shadow block of RenderObject;
  - RenderObjects_AfterCharacter `0x016d6949` for `+0xa` objects. The static reading does not show the first pass
    skipping them, so the native draws them once, in the first pass.
- **Tormenta speeds.** Its per-type animation speeds are set outside CreateObject and the handler; the source was not
  traced. The native uses the live per-type values.
- **Particles.** The legacy particle system (fire, smoke, sprites) is the next reconstruction needed for exact effects.
- **Tormenta re-read.** A read with Nighty would need the character selected in the list (not done; no movement
  involved).
