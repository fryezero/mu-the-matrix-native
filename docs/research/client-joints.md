# The joint pool, the world objects' effects and the login scene's particles (NATIVE-JOINT-001)

The client's older effect family has three pools: particles (NATIVE-PARTICLE-001,
[client-particles.md](client-particles.md)), effects and joints (NATIVE-COMBAT-002 ported the skill kinds,
[client-combat.md](client-combat.md) section 8). Three gaps remained after those milestones:

- Tormenta Island's object visuals create joints `0x7f7d` and the effect `0x40e`; both were counted, not drawn;
- the login scene drew its lantern sprites and its mist/spray particles as stand-in billboards;
- many particle, joint and effect kinds of the world objects were not reconstructed.

This milestone reconstructs the joint pool as one module (`reconstructed/joints`, which NATIVE-COMBAT-002's
`skill_fx` now wraps), the kinds the world objects and the login scene create, compares them with the client's
instructions in Unicorn and runs them in the native session.

Labels:

- **Verified**: the authored C equals the client's instructions on every compared case (Unicorn, the strict
  machine of `scripts/actor_machine.py`).
- **Static**: a reading of decoded instructions that was not executed.
- **Viewer choice**: native behaviour that is not a client reading.

## Identity

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

| Routine (names are ours) | Range | SHA-256 (first 16) |
|---|---|---|
| CreateJoint | `0x0153b02c..0x01553644` | `890bce9176519bd6` |
| MoveJoint | `0x01556c26..0x01589800` | `b8fab40aa72e0688` |
| RenderJoints | `0x01589b56..0x0158ba40` | `3ae752ff6197cc9a` |
| tail shift | `0x01553ba6..0x01553d40` | `52435adc58d0480b` |
| MoveHumming | `0x012af2f1..0x012af52d` | `d57cfcde6863dfe2` |
| vector normalise / near-zero test | `0x00cfd15f`, `0x00a72592` | `54a6d52aab926f45` / `e9e9640f2ad19f59` |
| degrees to radians / random sign | `0x00cee2cb`, `0x0185ca80` | `445591c2ef11588e` / `07137bf5799bda85` |

CreateEffect `0x013c0f19`, MoveEffect `0x0142fd09`, CreateParticle `0x015ae7b0`, MoveParticles `0x01616c80`,
RenderParticles `0x0159123f` and RenderObjectVisual `0x017f9758` are pinned by NATIVE-COMBAT-002's and
NATIVE-PARTICLE-001's validators, which this milestone extends.

## 1. The joint pool (verified)

**CreateJoint `0x0153b02c`**(type, position, target position, angle, subtype, target object, width, key, skill,
byte10, arg11, arg12, word13, arg14) takes the first record of 500 (`0xa64` bytes at `0x0a4fa4f0`) that is not
live (after a manager hook `0x01095a0a` that answers 0). The common part sets live, the kinds, render type 1, faces
3, key, skill, velocity 0, position = start, angle, brightness 1, moving 1, light (1, 1, 1), jitter 0, the target
position argument when there is no target object, the target, no tails, and builds the first tail from the
record's **previous** width; then the kind's case and the 50-tail clamp. The record is never cleared: fields a
case leaves keep a former joint's values.

**MoveJoint `0x01556c26`** (MoveJoints `0x01589b06` per logic step, after MoveEffects and before MoveParticles):
the angle matrix and the forward motion along −y when moving, the kind's case, then the closing tail shift when
`+0xa26` is set (with the head's matrix), time += frame time, LifeTime − 1, dead below 0.

**The tail shift `0x01553ba6`**: tail count + 1 capped at max − 1, the tails pushed down by one, tail 0 rebuilt at
the head as four corners pos + R(−w/2, 0, 0), R(w/2, 0, 0), R(0, 0, −w/2), R(0, 0, w/2), w the record's width.

**RenderJoints `0x01589b56`(mode)**: per live record with tails and faces (mode filter on `+0x64`): the render
type's blend wrapper (1 add, 2 alpha test, 3 subtract, 4 inverse add), the record colour light × brightness (none
for `0x7fd5`: the GL colour stays), BindTexture(`+8`), then per tail segment the texture coordinates
(u = (tails − i)/(max − 1); the bolt types `0x7f7c`/`0x7f7d` double it and subtract t = (WorldTime % 1000)/1000;
the `+0xa24`/`+0xa25` modes and subtypes 0xb..0xd have their own rules), the kind's colour and one GL_QUADS quad per
face bit (bit 0 through corners 2/3, bit 1 through corners 0/1).

### Kinds

| Kind | Create | Move | Render |
|---|---|---|---|
| `0x7f7d` 0x10, 0x11 (bolts) | draws `0x7f7c` JointThunder01; 50 tails, LifeTime 20, start = position, target = start + R(angle)·(r%100−50, r%100−50, −300w), the target object's light | rebuilt from the start each step: Shiny02 flash, step = normalised (target − start) × 300w/50, width 50w (75w) × (LifeTime+1)/20, 49 steps jittered by (r%2a−a, r%2a, 0) (a = 9w+1) in steps 1..14 and 20..44, pushed sideways by a in 15..19 | additive; per tail colour light × (i+10)/tails × LifeTime × 0.08, u += (t+1) × 0.33 |
| `0x7f7d` 0x12, 0x13 (arcs) | ±100, length 300 (unscaled) | the step plus a polynomial bow 0.005w²(3i²−150i+1250) (0x13: 0.0006w²(i−30)(2i²−105i+750)) in x and y and a jitter ±30 × w/10; width 75 × (LifeTime+1)/20 | as the bolts |
| `0x7f7d` 0x14, 0x15 (rings) | target = start | 48 points around the start at radius 100w (0x15: 1.5 × in y), jittered ±3, each lifted by ±(rand % range + low) where (low, range) follow a pattern travelling with WorldTime; every point is a tail of its own and the first closes the ring; width 60 × (LifeTime+1)/20 | u −= t (wrapped into 0..2), colour light × LifeTime × 0.1 |
| `0x7f7d` 0x16, 0x17 (rings) | phase `+0xa20` = (int)WorldTime % (max/2) | as 0x14/0x15 with the pattern fixed at the phase | as the rings |
| `0x7f7d` 0x18 | length 10w | as the bolts (width 60w, a = 6w+1) but **without** the step toward the target (computed, never added) | as the bolts |
| `0x7f7d` 0x19, 0x1a | length 10w (0x1a: 50w) | as the bolts with width 50w, a = 4w+1, jitter in 1..24 and 30..44, push in 25..29 | as the bolts |
| `0x7fd5` 0 (spark streaks) | width 2, velocity r%20+6, LifeTime r%8+8, 2 tails | the head's forward motion only | additive, no colour |
| `0x7fd8` 1 (Heal), `0x7fd3` 0 (Evil Spirit) | NATIVE-COMBAT-002's port, moved into the module | idem | idem |

A width ≤ 0 makes the `0x7f7d` cases return before the tail clamp: the record keeps its previous tail count and
LifeTime.

Correction to NATIVE-COMBAT-002: Heal's arrival flash is CreateSprite(Shiny02, …, blend 0, **axes 4**); the
validator then compared only the first six arguments. The bolts' flash is CreateSprite(`0x7f67`, start, 1, light,
NULL, rand % 360, 0, 4).

## 2. The world objects' effects (verified)

**The Tormenta field tornado `0x40e`** (`Object142\hs_fieldtornado.bmd`, loaded by the Tormenta handler
`0x00e4c4de`). The handler's slot 0x34 calls the wrapper `0x013c0eaa`(0x40e, position, angle, light, 0, the object,
−1, 0, (u16)scale, 0, 0.0, −1, 0, 0) on `rand % 500 == 1` for its type 9 markers; the wrapper builds the info block
(key −1, word4 = the object's scale, field 8 −1) and calls CreateEffect with scale 0.

- **CreateEffect `0x013c3eab`**: `+5` and `+6` cleared (the object's light flags), light = 1 + light, LifeTime 150
  (also at `+0x70`), `+0xc` = 1, alpha, scale, blend light 1, speed 0.3, heading `+0x170` = (rand % 314)/100, no
  hidden or blend mesh, angle 0, drift direction ((rand%20−10)·scale, (rand%20−10)·scale, 0), the position moved by
  (rand%512 − 256) in x and y and put on the terrain, frame 1; PlayBuffer(`0x582`, o, 0) when the hero
  (`[0x0a39d754] + 0x33ac`) is within 800 in x/y.
- **MoveEffect `0x01435ef3`** (after the common prologue): a new heading on `rand % 500 == 0`, position +=
  (2 sin h, 2 cos h), angle z 0, LifeTime × 0.9 on tiles whose TerrainWall word has bit 8 (`TERRAIN_INDEX`
  `0x016d34db`), blend light = (LifeTime + 1)/150, the model's PlayAnimation; then the lifetime (no generic motion).
- **RenderEffects → RenderObject** has no case for `0x40e` (static): the model draws with flags 2, alpha 1 and the
  effect's light. The native draw passes `+5` (cleared) as the model's lighting flag (static reading).

`skill_fx` reports the new calls as MU_SFX_CALL_SOUND (`0x00a6ac96`) and MU_SFX_CALL_ATTRIBUTE (`0x016d34db`, the
caller answers the attribute word).

## 3. Particle kinds (verified)

| Kind | Create | Move | Render |
|---|---|---|---|
| clouds `0x7f89` 0x14 (login mist, owner = the object) | LifeTime 300, gravity rand%1000, alpha `+0x44` 0.1, position += (r%500−250, r%500−250, r%20−20), start y = (r%100)/100, start z = the new z, scale (r%20+180) × 0.01 × scale, `+0x7c` = (r%10)/100, velocity 0 | above LifeTime 150: alpha + 0.04 (double) below 1, z + 1; then alpha − 0.025 above 0.1, z − 0.5; dead at LifeTime 0 | light × alpha |
| WATERFALL1 `0x801a` 2 (login spray) | LifeTime 30, rotation r%360, velocity z −(r%5+7), light 0.2, scale 1.6 + scale | scale − 0.005, light ÷ 1.2 below LifeTime 5, × 1.1 above 20, velocity z + 0.1 | generic |
| Shiny01 `0x7f66` 0, 1 (Noria) | LifeTime 18, angle x 45 | scale = sin(LifeTime × 10 × 0.0174533); subtype 1: × 0.75, rotation − 12 | generic |

CreateParticle writes neither `+0x44` nor `+0x7c` in its common part: like the other untouched fields they keep a
former particle's bytes (the validator now starts the C record from the same bytes).

## 4. Object visuals (verified)

RenderObjectVisual `0x017f9758` for Dungeon, Devias and Noria (every sprite blend 0, axes 4, the object as owner,
light from l = (rand%30+70)/100; bone points transform the zero vector unless said):

- **Dungeon 0x3d** (`0x017fc8e0`): lightning2 `0x7f37` pairs with rotation ±((int)(WorldTime × 0.1) % 360), light
  (0.4l, 0.8l, l), at bones 15 (scale 0.3), 19 (0.3) and 21 (1.5) by index (`BoneTransform + 0x30·bone`). The case
  ends in the default branch (event-world hooks, world manager), static for world 1.
- **Devias 0x64** (`0x017f9bdc`): a lightning2 pair (scale 2.5, light (l, l, l)) at Cylinder01 + (0, 0, 150).
  Type 0x67 picks its next action at the end of the current one (`0x012affa4`), not ported.
- **Noria** (`0x017f9dd1`): flares `0x7ef7` (rotation 0, light (0.4l, 0.7l, l)): type 9 Box01 1.5, 0x23 Box04
  1.5, 1 light03/02/01 0.5, 0x11 Box03/08/11/14 1. Type 0x27: a lightning2 pair at light01 (light (0.4l, 0.8l,
  l)); white flares at light06, light04, light03, light05, light02 (a `std::vector<std::string>` the client builds
  each call), each with two Shiny01 particles (subtypes 0, 1) on `rand % 32 == 0`; at light07, on `rand % 8 ==
  0`, eight spark joints `0x7fd5` (angle (r%60+60, 140, r%30), width 10) each with a Spark02 particle.

## 5. Survey: what each world's objects and ambient code create

Static scan of the creators (CreateParticle `0x0168fafd`, CreateSprite `0x01692eb7`, CreateJoint `0x0153b02c`,
CreateEffect `0x013c0eaa`, CreateFire `0x01616930`) in RenderObjectVisual's world cases, MoveObject `0x017ff238`'s
world cases, the world handlers' slots (vtables found from the BaseMap slots and their world predicates) and the
ambient routines; status after this milestone. "Not visible" means the native session does not run that code
path for want of placements: decoded object lists exist only for Lorencia, Tormenta Island, World94 and World95.

| World | Source | Kinds created | Status |
|---|---|---|---|
| Lorencia 0 | RenderObjectVisual | smoke01 `0x7f5a` 0 (Waterspout), flare01 sprites (MerchantAnimal) | ported (PARTICLE-001) |
| | MoveObject `0x017ff8e8` | CreateFire: Fire01 `0x7f3c`, smoke01 0/2 | ported (OBJECTS-002, PARTICLE-001) |
| | ambient | butterfly/crow flare sprites, rain02 splash `0x771c` | ported (ENV-001, PARTICLE-001) |
| Dungeon 1 | RenderObjectVisual 0x3d | lightning2 `0x7f37` sprites ×6 | ported, verified; not visible |
| | MoveObject `0x017ffe04` | effect `0x1a5` 0, CreateFire | not ported; not visible |
| Devias 2 | RenderObjectVisual 0x64 | lightning2 sprites ×2 | ported, verified; not visible |
| | MoveObject `0x017fffda` | fantaF `0x8016` 0, smoke01 `0x7f5a` 0x15, CreateFire | not ported; not visible |
| Noria 3 | RenderObjectVisual 1, 9, 0x11, 0x23, 0x27 | flare01 ×10, lightning2 ×2, Shiny01 `0x7f66` 0/1, joint `0x7fd5` 0, Spark02 `0x7f25` 0 | ported, verified; not visible |
| | MoveObject `0x018006e2` | Spark03 `0x7f26` 9 | not ported; not visible |
| Atlans 7 | RenderObjectVisual | default branch (no world-7 handler class found) | nothing |
| | MoveObject `0x018009f2` | drop01 `0x7fcd` 0 | not ported; not visible |
| Tormenta 0x8d | handler slot 0x34 `0x00e4ef4b` | joints `0x7f7d` 0x10..0x1a, effect `0x40e` | ported, verified, drawn |
| | handler slots 0x30, 0x64/0x68 | none / rain02, rain03 | ported (ENV-001, PARTICLE-001) |
| World94 0x5d (character select) | handler slot 0x34 `0x00daa9dd` | sprites `0x8155`×3, Shiny02, `0x8145`; particles clouds 0x14, WATERFALL1 2, `0x801b` 2, `0x801c` 0xe, `0x802a` 1, `0x8017` 0, smoke01 0x45; effects `0x5ac` 0/1, `0x59a` 3 | NATIVE-CHARSEL-002: the handler and the sprites, clouds, WATERFALL1/2/3 and fantaB kinds ported, verified, drawn through the lifecycle; `0x802a` 1, smoke01 0x45 (types not placed) and the effects not ported |
| | `0x00da9974..` | joint `0x7f78` 2, effects `0x7f84` 0xd, `0x4bc` 1, `0x4bd` 3 | correction (NATIVE-CHARSEL-002): this is `0x00da9685` of a monster handler (vtable `0x01aa7264`, monsters 0x398..0x39b), not the character select |
| World95 0x5e (login) | handler slot 0x34 `0x00e24be1` | Shiny02/flare01 sprites ×10, clouds `0x7f89` 0x14, WATERFALL1 `0x801a` 2 | ported, verified, drawn |
| ambient (other worlds) | RenderBoids `0x00c9fd8d` | lightning2, Fire01, flare01, clouds 0x12 for boid types `0x472`, `0x7c6`, `0x1a3`, `0x1a4` (Icarus, Elbeland) | not in these worlds |
| | MoveFishs `0x00ca05b3` | joints `0x7fd6` 4 (worlds 8, 0x21, 0x86), `0x7ff9` 0 (0x22), `0x7f79` 8 (Kalima) | not in these worlds |
| | MoveBoids `0x00c9eb04` | effect `0x413` 3 | not in these worlds |

Combat (NATIVE-COMBAT-002) kinds that were counted and not drawn: the Twisting Slash swirl's `0x7fd5` joints are now
drawn (the shared module); its smoke/spark particles and the stones' Fire01 1..3 came with NATIVE-PARTICLE-001;
Inferno's burst `0x013c07f4` remains.

## 6. Verification

`scripts/validate_joints.py --cases 3000` (new), `scripts/validate_skill_fx.py --cases 3000` and
`scripts/validate_particles.py --cases 3000 --heavy-cases 300` (extended), final local run (reports local in
`native/scratch/joints/reports/`):

| Validator | Family | Cases | Equal | Coverage of the new kinds |
|---|---|---:|---:|---|
| joints | joint_create (`0x0153b02c`, 14 kinds, early returns) | 3,000 | 3,000 | every `0x7f7d` subtype with and without width |
| joints | joint_move (`0x01556c26`) | 3,000 | 3,000 | 14 kinds, ~214 each |
| joints | joint_render (`0x01589b56`, modes 0..2, face bits) | 3,000 | 3,000 | 0..9+ quads |
| skill_fx | 10 families (effect_create/move cover `0x40e`) | 30,000 | 30,000 | `0x40e`: 187 create, 187 move |
| particles | 12 families (create/move/render cover clouds, WATERFALL1, Shiny01; visual covers worlds 1..3) | 30,494 | 30,494 | 1,500 visual cases in worlds 1..3 |

69,494 cases, 0 mismatches. The joint validator runs every routine above as client code with stubs only for
rand(), the C runtime sin/cos/sqrt (host libm), RequestTerrainHeight, CreateSprite/CreateEffect, the terrain light,
the area request, the wall attribute and the GL imports; the Noria 0x27 visual runs the client's `std::vector` and
`std::string` code over a stubbed C runtime malloc/free (`0x019a4da0`/`0x019a4d50`).

Negative controls (a planted mistake applied to the C result) disagree:

| Planted mistake | Disagreements |
|---|---:|
| ring phase modulo the full tail count | 123 |
| no closing tail shift | 2,358 |
| start flash in white | 1,435 |
| ring and bolt tail factors swapped | 1,262 |

plus the 12 + 12 controls of the two extended validators (all non-zero).

## 7. Native

- `native/core/mu_joints.*`: the joint helpers both owners use (CreateJoint's slot search, MoveJoints,
  RenderJoints as quads with the colour in effect, the render type's GL state). `mu_combat` keeps its 500 records
  and now creates, moves and draws them through these helpers (so the swirl's spark streaks draw, with Spark01).
- `native/core/mu_particles.*` (the world module) also keeps the world objects' joints (500) and effects (200):
  RenderObjectVisual's CreateJoint/CreateEffect (Tormenta's lightning and tornado), MoveEffects, MoveJoints and
  MoveParticles in that order each step, the effect models (`mu_world_particles_draw_models`), RenderJoints(0)
  before the sprite section; the joint, Spark01, clouds, WATERFALL1, lightning2 and Shiny01 bitmaps; owners for
  CreateParticle (the object's position); the Dungeon/Devias/Noria visuals.
- `mu-world`: the effect models and joints in the GL and software draws, the hero position for the tornado's
  sound distance, a `{"joints": true, ...}` summary line, frame reports `"joints": [live, quads, effects]`, and
  `--joint-demo SUB` (viewer test: a lightning joint above the hero every 20 steps).
- The login scene (`mu_login`, `login/login_gl.c`): the lantern sprites (`rt.sprite` hook) and the mist and spray
  particles (`rt.particle` with the owner) go to the particle module; MoveParticles runs in the tick head and
  RenderSprites(0)/RenderParticles(0) end the 3D part; the stand-in billboards are gone from the draw.

Viewer choices: the world objects and the skills keep separate joint pools (the client has one); the effect models
play their first action; the tornado's PlayBuffer is counted; the colour at the start of RenderJoints is white; a
joint of a kind that is not reconstructed is released at creation.

## 8. Local renders

`~/Documents/mu-mac-tools/native/renders/joints/` (not committed; `render.sh`, `sheets.py`): 1600×1000 headless GL
sequences, before = main (#114 build), after = this branch, with contact sheets and GIFs:

- `tormenta-135-10`: the hero's tile; the bolts of the crystals at the left edge;
- `tormenta-82-19-tornado`: crystal lightning and the field tornado;
- `tormenta-50-46-crystals`, `tormenta-90-10-crystals`: the crystals' arcs and rings;
- `login-before-after.png`: `mu-render ui login --scene` at 25/100/200 steps (1722×1048): the spray at the bow and
  the mist around the island now come from the client's kinds (compare `renders/login/live/login-client.png`).

## 9. Tests

- `reconstructed/joints/test_joints.py`: worked examples (targets and light, the early return, the ring phase, the
  spark streak, a bolt's rebuild and flash, a ring's tails, RenderJoints' colour and scroll, 0x7fd5 without colour,
  skill_fx giving the same records); private: a 60-case Unicorn run.
- `reconstructed/combat/test_skill_fx.py`: the tornado's creation, sound and drift.
- `reconstructed/particles/test_particles.py`: the login mist and spray, Shiny01, the Dungeon/Devias/Noria visuals.
- `native/tests/test_native_joints.py`: every `0x7f7d` subtype through `--joint-demo` on the synthetic world, the
  flashes, `--no-particles`, determinism; private: Tormenta at 82,19 (lightning, tornado, bitmaps).
- `native/tests/test_native_login.py`, `test_native_particles.py`, `test_native_combat.py` (updated counts).

## 10. Not ported

- MoveObject's particle kinds of Dungeon, Devias, Noria and Atlans (`0x1a5`, `0x8016`, `0x7f5a` 0x15, `0x7f26` 9,
  `0x7fcd`), the character-select scene's kinds, other joint kinds (`0x7f78`, `0x7f79`, `0x7fd6`, `0x7ff9`, …), the
  `0x7f78`/`0x7fdd` second move, `0x7fd6` 0x36's tail shift.
- RenderObject's draw of effect models (static), the tornado's sound playback.
- The world objects of Dungeon, Devias, Noria and Atlans are not placed natively (no decoded object lists), so their
  ported visuals are not seen yet.

## Reproduce

```sh
make -C reconstructed/joints && make -C reconstructed/combat && make -C reconstructed/particles && make -C native all world
scripts/validate_joints.py --cases 3000 --output /tmp/joints.json
scripts/validate_skill_fx.py --cases 3000 --output /tmp/skillfx.json
scripts/validate_particles.py --cases 3000 --heavy-cases 300 --output /tmp/particles.json
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 141 --tile 82,19 --objects-dir LOCAL_PLAIN_DIR
native/build/mu-render ui login --root "$MU_GAME_ROOT" --scene --objects-dir LOCAL_PLAIN_DIR --steps 100 --out /tmp/l.png
```
