# Ambient world life and weather (NATIVE-ENV-001)

The walk-around world of NATIVE-WORLD-001/002 had terrain, the hero, demo actors and their effects, but none of
the client's ambient life: the birds over Lorencia, the bats of the Dungeon, the butterflies of Noria, the fish
shoals of Atlans, the snow of Devias, the rain of Tormenta Island. This milestone finds the routines that make
them, reconstructs them in C (`reconstructed/environment`), compares them with the client's instructions in
Unicorn, and runs them in the native session (`native/core/mu_env.*`).

Labels:

- **Verified**: the authored C equals the client's instructions on every compared case.
- **Static**: a reading of decoded instructions that was not executed.
- **Viewer choice**: native code that is not client behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

`scripts/validate_environment.py` pins the SHA-256 of the 28 routine bodies it executes (`BODIES`).

## 1. Where the client runs them (static)

The in-world tick `0x0185613e` (one 40 ms logic step) calls, in this order:

1. **MoveLeaves `0x01537a43`** with `this = 0x0a3a0e28`, behind a guard (`0x01856a5c..0x01856ceb`):
   - world 0 (Lorencia) unless HeroTile `0x0b437c10` is 4 (the pub floor);
   - world 2 (Devias) when HeroTile is not 3 and below 10 (outdoors);
   - worlds 3 and 7, Devil Square, 0x67..0x6a, Icarus 0xa, Chaos Castle, and a list of event worlds
     (0x1e, 0x1f, 0x21, 0x22, 0x2a, 0x36, 0x39..0x3a, 0x3e, 0x3f, 0x45..0x4a, 0x4f, 0x52..0x5a, 0x5f, 0x60, 0x64,
     0x65, 0x6e, 0x6f, 0x71, 0x72, 0x79, 0x7a, 0x7b..0x7f, 0x80..0x82, 0x83..0x85);
   - otherwise when the world manager's current world object says so (`0x00ea2761`: vtable slot 3, byte +6 of
     the object). Tormenta Island's object sets it.
2. **MoveBoids `0x00c9eb04`**, **MoveFishs `0x00ca05b3`**, then `0x00c9e24a` (the "bugs": ten objects that
   follow an owner at `+0x34c`, i.e. pets and fairies, not ambient life; not ported).

The render scene `0x0185916b` sets the clear colour, clears FogEnable `0x0bdc597c`, draws the terrain, then
**RenderBoids `0x00c9fd8d`(0)**, the characters and objects, **RenderFishs `0x00ca1cf7`**, the bugs,
**RenderLeaves `0x01538145`**, **RenderBoids(1)**, the effects, and in the sprite section opened by BeginSprite
`0x0184a699` (identity modelview) RenderLeaves a second time for Devias outdoors and the guard-list worlds.
RenderLeaves draws planes with `glTranslatef` in world space and billboards whose corners are already in view
space (RenderSprite `0x0184c39c` multiplies by CameraMatrix `0x0bdc5918`), so each world's particles are right in
one of the two passes: planes in the first, Devias billboards in the second.

## 2. Ambient flyers: MoveBoids (verified)

Forty 0x3d8-byte objects at `0x0bdb71f0`. Each step walks them from slot 0 and **returns** at the world's limit:
40 in Atlans (7, 0x80..0x82), 13 in Icarus, 2 in Elbeland (0x33), 2 in Kalima (where a dead slot also needs
`rand() % 10 == 0`), 5 elsewhere.

A dead slot respawns when the world allows it: worlds 0, 1, 3, 4, 0xa and 0x84 always; Atlans when the hero's
tile attribute is 0 or 2; Blood Castle, Kalima and the deep dungeon 0x74..0x78 always; the Atlans abyss on
attribute 0x800. ObjectInit `0x0129eb81`, then live, scale 1, light 0.5, alpha 0 toward 1, turn step 13, and
the model:

| World | Model | Notes |
|---|---|---|
| 0 Lorencia | `0x192` Bird01 | |
| 1 Dungeon, 4 Lost Tower, 0x74..0x78 | `0x194` Bat01 | |
| 3 Noria | `0x193` Butterfly01 | scale 0.3, light 1 |
| Blood Castle 11..17, 52 | `0x1a2` Crow01 | |
| 7, 0x80..0x82 | `0x199`/`0x19a` Fish02/03 | AtlansShoal `0x00ca27b1`, only while the hero is below y 12800; returns 1 in every world |
| 0xa, 0x84 | `0x7c4` (Icarus dragons, `0x00ca2154`) | not ported |
| 0x33 | `0x1a4` | speed from the action table; not ported |

The common setup puts the object at the hero ± 512 in x and y, 150..349 above the terrain, with phase
`(rand() % 314) * 0.01`.

Every live object then animates (the model's action = the object's, the tick `0x012b4dd3` at speed 1) and runs
its mover:

- **MoveBat `0x00ca2acd`**: height = terrain + 350 − 150·|sin(phase)|, phase += 0.2.
- **MoveButterfly `0x00ca2ba7`**: one step in 32 a new heading (`rand() % 360`) and climb; the climb drifts by
  ±1.4 and is pushed back between terrain + 50 and terrain + 300.
- **MoveBird `0x00ca2dcb`** (birds and crows): a four-state machine at `+0x29`. Flying (0), it lands when the world
  time modulo 8192 is below 2048 and the hero is 200..400 units away; landing (1) sinks at 20 until under the
  terrain, then takes off (3, scale 1.1, climb 20) and settles back to flying when the scale has shrunk to 1.
  State 2 (on the ground) takes off when the hero walks (action ≥ 0x32) or one step in 256.

Then **MoveBoidFlight `0x00ca3e2f`**: the flock steering `0x012af9a9` (always, one step in four for butterflies)
averages, for the live neighbours within 400 units, a direction away from those closer than 80 and toward the
others, and turns the integer heading toward it by the turn step (CreateAngle `0x012aeced`, TurnAngle
`0x012aef0c`). The object moves forward by 25·scale (Atlans: 8..23 or 16..31 times the scale, faster after phase
5) through AngleMatrix/VectorRotate, despawns one step in 512 and beyond 1,500 units from the hero. In Atlans a
fish on attribute 1 turns around (twice kills it). Within 600 units: aBird1 (`0xc`) and aBird2 (`0xd`) one step
in 512 each, aBat (`0xe`) one in 256, the crow sound (`0x8a`) one in 128 on attribute 1. FadeAlpha `0x012af883`
moves the alpha by 0.05.

**RenderBoids** turns `angle.z` by +90 around the draw (and back, so the float rounding of that pair is part of
the state), tests TestFrustrum2D(x/100, y/100, −20), draws the body (RenderObject `0x016d4fe4`), a glow sprite
`0x7ef7` for butterflies and two eye sprites at bone 1 for crows, then a blob shadow (alpha test,
`glColor4f(0, 0, 0, 0.2)`, RenderBodyShadow `0x012bc07a` at the terrain height) outside Icarus.

## 3. Swimmers and crawlers: MoveFishs (verified)

Ten objects at `0x0bdc0bb0`, only the first three outside the water worlds, 8, 0x22 and 0x85. A dead slot is
moved every step to a random spot within ± 512 of the hero and spawns when that tile allows it:

| World | Tile rule | Model |
|---|---|---|
| 0 Lorencia | layer 1 == 5 (water) | `0x198` Fish01, alpha target 0.2/0.3, scale 0.6/speed |
| 1, 4, 0x74..0x78 | attribute < 8 | `0x196` Rat01 |
| 6 Arena | attribute < 8 | `0x197` Bug01 (action 1) |
| 7 Atlans | attribute 0 or 2 | `0x19b..0x19e` south of y 12800, else `0x19f`/`0x1a0` (pulsing alpha) |
| 0x80..0x82 | attribute 0x800 / 0x1000 | as Atlans |
| 8, 0x21, 0x86; 0x22; Kalima | attribute 0 or 2 | with effects (`0x7fd6`, `0x7ff9`, `0x7f79`) |

Live fish steer like the flock, swim (6..9)·scale forward, follow the terrain outside the water worlds, turn
around on the tiles they may not enter (Lorencia: off layer-1 water; rats: attribute ≥ 8; Atlans: attribute 1 or
≥ 8) and die after two turns or beyond 1,500 units. Rats squeak (`0xf`) one step in 256 within 600 units.
RenderFishs is RenderBoids without sprites.

## 4. Weather particles: MoveLeaves and RenderLeaves (verified)

Two hundred 0xb4-byte particles at `0x0a3a0e28`. The count per world is 80 (200 in Devil Square and world 0x71,
40 in 0x1e, by tile attribute in a few event worlds). The trailer holds a rain target and level (`+0x8ca4`,
read by the audio block as `0x0a3a9acc`; target 100 only in Icarus and Chaos Castle) and two wind values from
sin(time).

A dead particle gets light (1, 1, 1) and is created by the first creator that accepts the world:

| World | Creator | Particle |
|---|---|---|
| 0 Lorencia | `0x0153959d` | leaf01 at hero ±800/−500..+900, 50..349 up, drifting with spin |
| 2 Devias | `0x0153939c` | snow: leaf01 scale 5, one in ten leaf02 scale 10, falling 8..23 at angle −30 |
| 3 Noria, 7, 0x80..0x82 | `0x01539ace` | as Lorencia (Atlans: bubbles) |
| 0xa, 0x84 | `0x015398de` | rain while index < rain level · 2 |
| 0x8d Tormenta Island | world class (vtable `0x01aabd10`) slot 0x64 `0x00e5377c` | rain, see below |

Live particles move with `0x0153a634` in Lorencia and Icarus (drift with spin, gone 447 units from their start;
rain hits the ground with a splash particle), the Tormenta class slot 0x68 `0x00e538ec`, or the default
`0x0153ac06` (random walk, fade by 0.05 per step on the ground).

**Tormenta Island.** The world object holds a rain level (`+0x18`, constructor `0x00e4be37`: maximum 10,
level 0). Each dead-particle creation raises it by 0.3·dt (dt = 0.1) while the hero stands on attribute 0x800,
or lowers it by 0.15·dt elsewhere; a drop is created with probability 1/(11 − level). The drop starts 50..349
units up, falls at angle (−60, 10) at 30..53 units per step, and one in two hits the ground at once with a
`0x771c` or `0x771d` splash particle.

**RenderLeaves** sets alpha test (Lorencia, Noria) or additive blend (Devias, Atlans, Tormenta and the event
worlds), `glColor3f(1, 1, 1)`, and for every live particle whose bitmap exists draws a RenderSprite billboard
(Devias, Raklion, Santa village, 0x79) or a RenderPlane3D quad (`0x0184c121`): 3×3 for leaves, 1×20 for rain.

**The leaf bitmap (static).** `0x01829e21` loads `World<n>\leaf01.tga` into `0x771f`, then `leaf01.jpg` into the
same index (every world but 0x5b/0x5c). CGlobalBitmap::LoadImage `0x00c97730` unloads the old bitmap when the
name differs and only then opens the new file. World1 (Lorencia) and World4 (Noria) have only `leaf01.OZT`, so the
index ends empty and RenderLeaves skips every particle there (FindTexture `0x00c97ce3` returns NULL); the
particles still move and draw `rand()`. Devias (World3) and Atlans (World8) have `leaf01.OZJ`, which is what
the client draws. A live capture would confirm this reading.

## 5. Fog, clear colour, water, lightning

- **Clear colour (static, render scene `0x01859419`)**: Lorencia (10, 20, 14)/256, Devias (0, 0, 10)/256, Icarus
  (3, 25, 44)/256, Illusion Temple (9, 8, 33)/256, world 0x84 (0.149, 0, 0), black elsewhere.
- **Fog (static)**: the render scene clears FogEnable, so BeginOpengl's fog block (`GL_LINEAR`, density
  `0x01cf160c`, colour `0x01cf1610`) never runs in game; the only fog is world 0x1e's black linear fog
  2000..2700 inside one box (`0x00d8cca8`).
- **Water surfaces**: the per-world water/lava scrolls and Atlans' animated caustic layer (bitmaps `0x76f8 + n`,
  the `wt%02d` files of the model pass) are the terrain's, covered by NATIVE-TERRAIN-002.
- **Lightning and day/night**: none in these routines. Thunder and lightning textures belong to skills and event
  monsters.

## 6. Per-world table

| World | Clear | Flyers (limit) | Swimmers (limit) | Weather (count, bitmap, blend) |
|---|---|---|---|---|
| 0 Lorencia | (10, 20, 14) | birds (5) | fish on water (3) | 80 leaves, none drawn (no leaf01.OZJ), alpha test |
| 1 Dungeon | black | bats (5) | rats (3) | none |
| 2 Devias | (0, 0, 10) | none | none | 80 snow billboards, additive |
| 3 Noria | black | butterflies (5) | none | 80 leaves, none drawn, alpha test |
| 7 Atlans | black | fish shoals (40) | fish (10) | 80 bubbles, additive |
| 0x8d Tormenta Island | black | none | none | 80 rain streaks driven by the 0x800 tiles, additive |

`mu_env_world_info_get` restates these branches for any world.

## 7. Verification

`scripts/validate_environment.py` runs world sessions: the arrays start dead (or fuzzed in a quarter of the
cases), the hero walks (sometimes warping 2,500 units), and every logic step runs the client's MoveLeaves,
MoveBoids and MoveFishs in the tick's order on one client memory; every fourth step adds both RenderBoids passes,
RenderFishs and RenderLeaves. The C runs the same steps. After every step the rand() state and count, the
modelled bytes of all objects and particles, the leaf trailer, the Tormenta object and the ordered log of every
host call (sounds, SetAction, animation ticks, ObjectInit, kills, particles, effects, frustum tests, RenderObject
snapshots, sprites, bone positions, shadow origins, GL state and colour calls, binds, and the GL vertex streams of
RenderPlane3D and RenderSprite) must be equal.

Client code runs everything the steps reach (see the script's docstring); stubs answer the engine services with
the test host's synthetic answers. The world manager's leaf calls are redirected to the Tormenta class methods in
world 0x8d. Unmodelled object bytes stay undefined, so a read of a field the C does not model stops a case.

Private run (seed 20261018, 400 cases of 60 steps, 25 worlds including all six target worlds; 622 s; reports
local in `native/scratch/env/reports/`):

| Measure | Result |
|---|---|
| cases equal | 400 / 400 |
| steps compared (tick and render routines) | 80,400 |
| host calls compared in order | 5,056,654 |
| rand() calls | 3,778,740 |
| branch probes reached (spawn per world, every mover state, kills, sounds, Tormenta drop/splash, render branches) | 94 / 94 (the rarest, the crow sound, 3 times) |
| negative controls (library builds with one planted mistake, 12 cases each) | 10 / 10 detected |

The controls: boid limit 6, flock radius 500, bird landing window 300..400, fish turn on layer 4, leaf drift without
the camera rule, snow scale 6, Tormenta rain rising 0.2, RenderBoids without the +90 turn, leaf fade 0.04 and a
reversed TurnAngle. Each disagreed with the client in 6 to 12 of its 12 cases.

## 8. Native session

`native/core/mu_env.*` runs the module in `mu-world`/`mu-walk`/mu-client: `on_step` calls `mu_world_env_step`
(guard, MoveLeaves, MoveBoids, MoveFishs) after the actors, `draw_gl`/`draw_soft` call `mu_world_env_draw` after the
actors, and the clear colour replaces the black sky. The host gives the routines RequestTerrainHeight over the
world, SetAction and the animation tick on the model (`mu_move_set_action`, `mu_model_tick`), and SND_Play through
the audio engine; the rain level feeds the audio block's `0x0a3a9acc`. TestFrustrum2D uses the session's 2D
frustum.

Viewer choices: rand() starts from 1 (`--env-seed`); the body is drawn with the default render flags and the
object's light as colour; shadows, glow sprites and splash particles are counted, not drawn; billboards are drawn
in the world pass; `--env-tga-leaves` loads the `.tga` the client unloads. The world's models count as loaded for
the logic (the client's getter returns them; all target-world files are installed).

## 9. Tests

- **Portable** (`make test`): `reconstructed/environment/test_environment.py` (rand, the per-world table, asset
  names, spawn and weather worked examples, Python statements of the default leaf mover, the bat mover and
  FadeAlpha) and `native/tests/test_native_env.py` (`mu-walk` on a synthetic world 0 with synthetic Bird01/Fish01
  and a leaf .tga: five birds, 80 invisible leaves, the viewer option, the clear colour, determinism, seed,
  `--no-env`).
- **Private** (`MU_RECOVERY_INTEGRATION=1`): an 8-case Unicorn comparison; logic runs of the installed Lorencia,
  Dungeon, Devias, Noria, Atlans and Tormenta Island.

## 10. Local renders

In `~/Documents/mu-mac-tools/native/renders/env/` (not committed): headless GL frame sequences (1280×800, every
10th frame) `lorencia/` (town walk), `lorencia-water/` (fish), `dungeon/`, `devias/`, `noria/`, `atlans/`,
`tormenta/`, per-frame state in the `.jsonl` next to each, `atlans-soft/` (software rasterizer),
`lorencia-tga-leaves-viewer-option/`, and `contact-worlds.png`.

## 11. Not ported

- Icarus dragons (`0x00ca2154`), the Elbeland flyer `0x1a4` and the movers `0x00ca3189`, `0x00ca33c3`,
  `0x00ca3ce1`, `0x00df150a`; the Devil Square and Chaos Castle rain creators and movers; the event-world leaf
  handlers (they return 0 outside their worlds); RenderLeaves' 0x71 branch.
- The login-scene branch of MoveBoids (`0x01ec3254` ≠ 0).
- RenderObject's body pass (static). RenderBodyShadow, CreateSprite and CreateParticle are reconstructed and
  drawn by NATIVE-PARTICLE-001 ([client-particles.md](client-particles.md)).
- The pets/fairies of `0x00c9e24a`.
