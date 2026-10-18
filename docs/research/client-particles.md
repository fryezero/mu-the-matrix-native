# Legacy particles, sprites, blob shadows and object visuals (NATIVE-PARTICLE-001)

Several merged milestones stopped at the same missing pieces:

- the world objects' fires and smoke (NATIVE-OBJECTS-002) drew as labelled stand-in billboards;
- the ambient creatures' blob shadows, butterfly and crow glows and the rain splashes (NATIVE-ENV-001) were
  counted, not drawn;
- the skills' sprites and several of their particle kinds (NATIVE-COMBAT-002) were counted, not drawn.

All of them go through the client's older particle and sprite system, its billboard routine, its blob shadow
and two bone helpers. This milestone reconstructs those routines in C (`reconstructed/particles`), compares them
with the client's instructions in Unicorn (`scripts/validate_particles.py`) and runs them in the native world
(`native/core/mu_particles.*`).

Labels:

- **Verified**: the authored C equals the client's instructions on every compared case.
- **Static**: a reading of decoded instructions that was not executed.
- **Viewer choice**: native behaviour that is not a client reading.

## Identity

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

| Routine (names are ours) | Range | SHA-256 (first 16) |
|---|---|---|
| CreateParticle wrapper | `0x0168fafd..0x0168fbae` | `9d5f80528fdfc7d1` |
| CreateParticle core | `0x015ae7b0..0x01615f39` | `08657b970bb9c805` |
| MoveParticles | `0x01616c80..0x0168eeb2` | `fc398a663dc453f9` |
| RenderParticles | `0x0159123f..0x015ae373` | `4033b5e63a8171cb` |
| RenderSprite | `0x0184c39c..0x0184ca6b` | `586804808932d8d3` |
| CreateSprite core | `0x01692508..0x0169270e` | `32855da4ad66f9a3` |
| RenderSprites / per-sprite draw | `0x0169270e..0x01692853` / `0x01692931..0x01692e29` | `81de114f5ff25f20` / `e460a4c608dd35a6` |
| RenderBodyShadow | `0x012bc07a..0x012bc5ab` | `dc60794101639c9c` |
| TransformPosition | `0x012b6ef1..0x012b7019` | `542654674242dba1` |
| bone matrix by name | `0x0129f18a..0x0129f24f` | `b06156f937f9da14` |
| RenderObjectVisual | `0x017f9758..0x017fccce` | `3bc2f7f045cc14ec` |
| Tormenta handler slot 0x34 | `0x00e4ef4b..0x00e4f952` | `58a4fbe6db8df047` |

## 1. Where the client runs them (static)

- **Tick** `0x0185613e`: MoveObjects (CreateFire's particles) … MoveLeaves, MoveBoids, MoveFishs … then
  MoveEffects `0x0150ddb1`, MoveJoints `0x01589b06` and **MoveParticles** (`0x01856dcd` through the thunk
  `0x0159122d`). A particle created in a step is moved in the same step.
- **Render scene** `0x0185916b`: RenderObjects (RenderObjectVisual creates particles and sprites per frame),
  RenderBoids/RenderFishs (sprites, shadows), the characters (their parts' shadows), RenderLeaves, effects and
  joints, then `0x01692887` (every live sprite visible) and BeginSprite `0x0184a699` (glPushMatrix,
  glLoadIdentity). In that sprite section: RenderLeaves' billboards, **RenderSprites(0)**, **RenderParticles(0)**.
  A second branch draws the split passes (modes 1/2: below z 350, above z 300).

## 2. The particle list (verified)

`CreateParticle 0x0168fafd(type, position, angle, light, subtype, scale, owner, arg8)`:

- **Wrapper.** Only world 0x8b drops particles: `rand() % max([0x0a39d768], 1)`, forced to 0 for the 17 kinds
  of the filter `0x010954d4` (Fire01, smoke01, Spark03 …). The particle is created when the remainder is 0.
  Other worlds call no `rand()`.
- **Core `0x015ae7b0`.** It allocates a 0xb4-byte record from a pool (`0x0a63f040`, freed records reused) and
  pushes a shared pointer to the end of a `std::list` (list object `0x0a3a9adc`). The list is unbounded.
  - Common part: live, type = drawn bitmap, subtype, position = start, angle = start angle, light, scale,
    gravity 0, LifeTime 2, frame 0, owner, rotation 0, moving 1, time 0, argument 8, velocity 0.
  - With an owner, the owner position is the owner's `+0x158` with z = RequestTerrainHeight; else 0.
  - Then the kind's case (a switch over several hundred bitmaps). Fields a case does not write keep the
    common values.

Record fields: `+0x08` live, `+0x0c` type, `+0x10` drawn bitmap, `+0x14` subtype, `+0x18` scale,
`+0x20` position, `+0x2c` angle, `+0x38` light, `+0x48` LifeTime, `+0x50` owner, `+0x54` owner position,
`+0x60` rotation, `+0x64` frame, `+0x68` moving, `+0x6c` gravity, `+0x70` velocity, `+0x88` start,
`+0x94` start angle, `+0xac` time, `+0xb0` argument 8.

**MoveParticles `0x01616c80`.** First a wind block: `wind[i] += (rand() % 2001 − 1000) · 0.0006` within
±0.6, then `wind_sum[i] += wind[i]` within ±1.7 (list object `+0x08`, `+0x14`; two `rand()` calls per step).
Then each record in list order:

1. erased when LifeTime ≤ 0 or not live;
2. with the moving flag, MovePosition `0x012af52d`: position += VectorRotate(velocity, AngleMatrix(angle));
3. with an owner, the owner position is refreshed;
4. the kind's case;
5. LifeTime − 1, time += frame time `[0x01cf103c]`.

**RenderParticles `0x0159123f`(mode).** For each live record: the mode filter. Then size = bitmap
`+0x204/+0x208` × scale, EnableAlphaBlend `0x0184aa2b` for 3-component bitmaps, else EnableAlphaTest(0)
`0x0184a990`. Then the kind's extra state and one RenderSprite.

The reconstructed kinds (all verified for create, move and render):

| Kind | Create | Move | Render |
|---|---|---|---|
| Fire01 `0x7f3c` 0 | life 24, velocity y −(r%16+32)·0.1, scale (r%64+128)·0.01, rotation r%360 | gravity +0.004, scale −0.04, frame (23−life)/6, z += gravity·10 | quarter-width cell `frame%4`, rotation = angle x |
| Fire01 1 | as 0, scale (r%4+10)·0.01 | gravity +0.004, scale += gravity, velocity ·0.98 | as 0 |
| Fire01 2, 3, 4, 6 | life 24, velocity y −(r%32−16)·0.1, rotation; scale = argument | 2..4 as 1; 6 as 5 | as 0 |
| Fire01 5, 17 | life 24 (17: 10), scale (r%64+128)·scale·0.01 | as 0, rotation +5 | rotation = record rotation |
| smoke01 `0x7f5a` 0 | life 16, scale (r%32+48)·0.01, angle x r%360, rotation = world time % 360 | light = life/8, gravity +0.2, z += gravity, scale +0.05 | generic |
| smoke01 2 | life 50, scale (r%64+64)·0.01, rotation, gravity (r%32+60)·0.1 | light = life/50, gravity −0.1, x −= gravity·0.2, z += gravity, scale −0.01 | + EnableAlphaBlendMinus `0x0184aab7` |
| smoke01 3 | life 10, scale (r%32+80)·0.01, angle x r%90−45, angle z r%360, velocity y −(r%8+40) | light (0.8, 0.8, 1)·life/8, velocity ·0.4, scale +0.1 | generic |
| rain02/rain03 `0x771c/0x771d` 0 | life 20, scale (r%6+8)·0.1, position += r%10−5 per axis | scale +0.03, light −0.05 (world 0x22: light (1, 1, 0.7), no fade) | generic |
| Spark02 `0x7f25` 0 | scale (r%4+4)·0.1, life r%16+24, angle z, gravity r%16+6, velocity R·(0, (r%20+20)·0.1, 0) | light life/16, fall, bounce on the terrain (gravity ·−0.6, life −4), velocity once more | generic |
| Thunder01 `0x7f2b` 0 | scale (r%8+6)·scale·0.1, rotation, gravity 20 | rotation += gravity | generic |
| Spark03 `0x7f26` 0, 1 | 1: random angle, velocity R·(0, −50, 0) | scale −0.5 (1: −2), dies below 0.2 | generic |

"Generic" is RenderSprite(bitmap, position, size, light, rotation, 0, 0, 1, 1, axes 4). Thunder01 and Spark03
restate NATIVE-COMBAT-002's port of the same kinds; their validator and this one agree.

## 3. RenderSprite `0x0184c39c` (verified)

1. BindTexture(bitmap).
2. The centre in view space: VectorTransform(position, CameraMatrix `0x0bdc5918`). Half width and height.
3. The corners:
   - rotation 0: (x−w, y−h), (x+w, y−h), (x+w, y+h), (x−w, y+h) at the eye z;
   - otherwise (±w, ±h, 0) turned by AngleMatrix of the rotation on the axes selected by the last argument
     (bit 0 x, bit 1 y, bit 2 z), plus the centre.
4. glBegin(GL_QUADS) and the colour:
   - glColor3fv(light) for 3-component bitmaps;
   - glColor4f(light, 1) for 0x7f49/0x7df3;
   - else glColor4f(light, light.r).
5. Texcoords (u, v+vh), (u+uw, v+vh), (u+uw, v), (u, v), glEnd.

The quad is in view space under BeginSprite's identity modelview.

## 4. Sprites (verified)

**CreateSprite `0x01692eb7` → `0x01692508`.** The arguments are bitmap, position, scale, light, owner,
rotation, blend, axes and a sheet `{across, down, ms}` (`0x00a0c1d0` builds {1, 1, 1.0}). The wrapper's two
option checks are taken as passing. The first of 1000 OBJECT records at `0x0a3da070` that is not live gets:

- SetLive(1);
- bitmap `+0x5c`, blend `+0x60`, owner `+0x34c`, alpha `+0xd0` = 1, scale `+0xa0`, angle z = rotation;
- axes `+0x8c`, position `+0x158` = start `+0x110`, light `+0xec`;
- sheet `+0x90/+0x94` (as floats), `+0x98` (truncated).

When all are live it returns 0, which cannot be told from slot 0.

**RenderSprites `0x0169270e`(mode).** Mode 1 skips sprites above z 350. Mode 2 kills those at or below z 300.
Each live sprite gets its blend wrapper:

| `+0x60` | Wrapper |
|---|---|
| 0 | EnableAlphaBlend |
| 1 | EnableAlphaBlendMinus |
| 2 | EnableAlphaTest(1) |
| 3 | `0x0184ab46` (ONE_MINUS_SRC_COLOR, ONE) |
| 4 | DisableAlphaBlend `0x0184a7f3` + EnableAlphaTest(1) |
| bitmap 0x7fea | EnableAlphaTest(1) |

Then the per-sprite draw `0x01692931`:

- alpha +0.1 up to 1 when visible, −0.1 down to 0.2 otherwise;
- size = bitmap size × alpha × scale;
- RenderSprite with the sheet cell of the world time `(t % (cells·ms)) / ms`;
- bitmap 0x7fea: a fixed 64×64 cell of a 3×3 sheet chosen by the blend value.

Modes 0 and 2 then kill the sprite, so sprites live for one frame. A sheet with 0 cells across divides by
zero in the client.

## 5. RenderBodyShadow `0x012bc07a` (verified)

`RenderBodyShadow(hide texture, hide mesh, first, end, z offset)` on the posed model:

1. 0x0184a783(0) (depth mask on, alpha test off, texture off), then depth mask off, glPushMatrix.
2. For each mesh in first (−1: 0) up to end (−1: the count), except the hidden mesh, empty meshes and meshes
   with the hidden texture: glBegin(GL_TRIANGLES) and every corner of every triangle. A quad's fourth corner is
   sent inside GL_TRIANGLES too, as the client does. Each vertex `v = VertexTransform − BodyOrigin` becomes:
   - x += (x + 2000) · z / (z − 4000) (2500 in world 0x1e);
   - z = 5;
   - v += origin;
   - z = RequestTerrainHeight(x, y) + 2 + offset (world 0x91: z = 10 + origin z + offset, no terrain);

   then glEnd.
3. glPopMatrix, depth mask on.

The colour is the caller's:

- RenderBoids/RenderFishs: EnableAlphaTest(1), glColor4f(0, 0, 0, 0.2), BodyOrigin = the terrain under the
  creature.
- The item render `0x0176ce74`, the character parts' shadow block (**static**): DisableAlphaBlend +
  glColor3f(0, 0, 0), so opaque black. In Atlans (7, 0x80..0x82) it uses EnableAlphaTest(1) and alpha 0.2.
  There is none in 0x18..0x1d, 0x24, 0xa, 0x84, and the z offset is 5 in world 0x8f.

## 6. Bone helpers (verified)

- **`0x0129f18a(name, own)`** finds the first bone of the object's model whose name (the 0x8c-byte bone
  record starts with it) equals the `std::string`. It returns `BoneTransform 0x06fce398 + 0x30·i`, or with
  `own` the object's own buffer `+0x318` when set. NULL when there is no model, no bones or no match.
- **TransformPosition `0x012b6ef1`(matrix, in, out, translate).** out = VectorTransform(in, matrix); with
  translate, out = out · BodyScale `+0x74` + BodyOrigin `+0x78`. A NULL matrix leaves out alone.

## 7. Object visuals (verified)

**RenderObjectVisual `0x017f9758`.** It runs after RenderObject for every object of the render pass, hidden
ones included. Without a model it returns. Otherwise one `rand()` for every object
(`l = (rand % 30 + 70) · 0.01`), then the world's cases.

Lorencia (world 0):

- **Waterspout01 (0x69).** BlendMeshLight 1 and the v scroll. On `rand % 2 == 0`, two smoke01 particles
  (subtype 0, scale 1, the object's angle and light, no owner) at bone Box04 + (r%32−16, −20, r%32−16) and
  Box03 + (r%32−16, −80, r%32−16), through TransformPosition(…, 0).
- **MerchantAnimal01 (0x38).** Two flare01 sprites (scale 5l, light (0.6l, 0.3l, 0.1l), additive, axes 4,
  the object as owner) at bones Box04 and Box10. **The client transforms a local it never writes**
  (`[ebp−0x2c]`): the sprite position is a function of stack residue. In Unicorn the input was the stack fill
  pattern in all 712 such calls. The C passes (0, 0, 0), the bone's origin.

Tormenta Island (0x8d) runs the event-world hooks (they answer no there), then the world manager to the
handler's slot 0x34:

- types 2..5 and 0xbf..0xc5: on `rand % 50 == 0` the object's light becomes (0.59, 0.59, 1) and
  CreateJoint(0x7f7d, position, position, angle, subtype, the object, scale, …) with subtypes 0x1a, 0x10,
  0x11, 0x18, 0x19, 0x12..0x17;
- type 9: on `rand % 500 == 1` CreateEffect(0x40e, …).

These objects are HiddenMesh −2 markers. The joints and the effect belong to the joint and effect pools; NATIVE-JOINT-001
reconstructs and draws them ([client-joints.md](client-joints.md)), together with the Dungeon, Devias and Noria
visuals and the clouds, WATERFALL1 and Shiny01 kinds.

## 8. Verification

`scripts/validate_particles.py` runs the client routines over the pinned captures in the strict machine of
`scripts/actor_machine.py`: declared regions with defined-byte masks; an undefined read stops a case. The
entry points are:

- the record bodies of MoveParticles and RenderParticles entered with their frames (as NATIVE-COMBAT-002 did);
- CreateParticle, CreateSprite, RenderSprite, RenderSprites, RenderBodyShadow, TransformPosition, the bone
  lookup and both visuals from their entries.

Stubs record the engine services: rand(), RequestTerrainHeight, the host-libm sin/cos wrappers, the shared
pointer helpers, the GL imports and state wrappers, the bitmap getter, CreateJoint/CreateEffect and the model
getter. AngleMatrix, VectorRotate, VectorTransform, the uv setter, SetLive, the world predicates, the
`std::string` constructor and compare run as client code.

Final local run (`--cases 3000 --heavy-cases 300`, 51 s; report local in
`native/scratch/particles/reports/particles-final.json`):

| Family | Cases | Equal |
|---|---:|---:|
| create (17 kinds, with/without owner) | 3,000 | 3,000 |
| wrapper (world 0x8b rule) | 3,000 | 3,000 |
| move (1,974 run in Unicorn, 1,026 erased at the head) | 3,000 | 3,000 |
| wind | 3,000 | 3,000 |
| render (modes 0..3, 3/4 components) | 3,000 | 3,000 |
| sprite (RenderSprite GL stream, upright/rotated) | 3,000 | 3,000 |
| sprite_create (1000 records, full list) | 300 | 300 |
| sprite_render (modes 0..2, sheets, 0x7fea) | 300 | 300 |
| shadow (worlds 0, 2, 0x1e, 0x91; quads) | 3,000 | 3,000 |
| bone (TransformPosition) | 3,000 | 3,000 |
| bone_lookup (client `std::string`) | 2,929 (+71 long names not run) | 2,929 |
| visual (Lorencia 0x38/0x69, Tormenta slot 0x34) | 2,923 | 2,923 |

Negative controls (a planted mistake applied to the C result) disagree on every family:

| Planted mistake | Disagreements |
|---|---:|
| Fire01 1 sized like 0 | 177 |
| drop without the exemption | 334 |
| smoke light over 16 | 118 |
| unclamped wind | 1,115 |
| full-width fire cell | 1,102 |
| unflipped v | 1,386 |
| rounded sheet time | 142 |
| sprite size without alpha | 184 |
| shadow at the origin height | 1,497 |
| TransformPosition without scale | 2,126 |
| loose bone-name test | 504 |
| Waterspout's second drop −20 | 240 |

## 9. Native module

`native/core/mu_particles.*` runs the module in `mu-world`, `mu-walk` and mu-client:

- `mu_world_particles_attach` hooks it into the object runtime (CreateParticle of the move pass,
  RenderObjectVisual after RenderObject) and the ambient creatures (CreateParticle, CreateSprite, crow eyes
  at bone 1 through TransformPosition, RenderBodyShadow).
- `on_step` calls MoveParticles after the other movers.
- The draws call the sprite section (RenderSprites(0), then RenderParticles(0)) after the environment.
- The hero's and the monsters' part shadows (the item render's shadow block) go before each part.
- NATIVE-COMBAT-002's sprites and its particle kinds that skill_fx does not port (Fire01 1..3 of the impact
  stones, the Twisting Slash swirl's smoke01 3 and Spark02 0) go to the module as well.

The view-space quads go back to world space with the camera matrix and through the session's render backend
(GL or the software rasterizer), as two triangles.

Viewer choices:

- the module's own MSVC rand() (seed `--particle-seed`, default 1);
- a 4096-particle cap;
- RenderObjectVisual runs per rendered frame (the client's frame cap gives one per step);
- bone positions use the native pose (bones without the origin, TransformPosition with translate), which equals
  the client's pose with the origin folded into the bones up to rounding;
- the hero's shadow conditions beyond the world rules (shadow flag `+3`, `+0x44`, buff 0x12, an option
  singleton) are taken as allowing it.

`--no-particles` restores the former stand-in path. The JSON reports a `particles` summary line and per-frame
`particles: [live, drawn particles, drawn sprites, shadows]`.

```sh
make -C reconstructed/particles && make -C native all viewer
./tools/python/bin/python scripts/validate_particles.py --cases 3000 --heavy-cases 300 --output /tmp/pt.json
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 0 --tile 146,110 --objects-dir LOCAL_PLAIN_DIR
```

## 10. Tests

- `reconstructed/particles/test_particles.py` (portable): worked examples of every routine (kinds, common
  initialisation, owner position, Fire01/smoke01/rain/Spark cases, the wrapper rule, the fire strip, the
  upright quad, one-frame sprites with the alpha ramp, the shadow projection and world 0x91, TransformPosition,
  the bone test, the Waterspout/MerchantAnimal/Tormenta visuals, the layout). Private: a 40-case Unicorn run.
- `native/tests/test_native_particles.py` (portable): a synthetic world 0 with a FireLight01 object, Bird01
  and a synthetic Fire01. It checks creation, moves, draws, shadows, `--no-particles` and determinism.
  Private (`MU_OBJECTS_PLAIN_DIR`): the installed Lorencia fires at 146,110.

## 11. Local renders

In `~/Documents/mu-mac-tools/native/renders/particles/` (not committed): 1600×1000 headless GL sequences,
`<name>-before` (`--no-particles`: the stand-ins) and `<name>-after`, the last 48 frames each, with GIFs and a
contact sheet:

- `lorencia-146-110-fires`: the FireLight fires;
- `lorencia-waterspout-141-128`: the fountain's smoke at Box04/Box03, bird shadows;
- `lorencia-147-137`;
- `tormenta-135-10`: no particle there; the handler's joints are counted;
- `tormenta-118-150-rain`: splash particles on a 0x800 tile after 400 steps;
- `devias-snow-shadows`: the hero's shadow on the snow;
- `noria-butterflies`: glow sprites and shadows;
- `dungeon-bats`: bat shadows.

## 12. Not ported

NATIVE-JOINT-001 ([client-joints.md](client-joints.md)) has since ported the Tormenta joints and effect, the login
scene's sprites and its clouds/WATERFALL1 kinds, Shiny01 and the Dungeon/Devias/Noria visuals; the list below is
this milestone's.

- The other particle kinds (several hundred bitmaps and subtypes of the three switches), owner-following
  details beyond the owner position, and the 0x7ef7/6 and 0x7f54/5 extra state wrappers.
- The joints and the effect the Tormenta handler creates (kinds of the joint/effect pools that
  NATIVE-COMBAT-002 does not reconstruct).
- RenderObject's own shadow block for objects with `+3` (none in Lorencia and Tormenta Island reach it in the
  native build).
- The login scene's lanterns and mist (NATIVE-LOGIN-001 keeps its stand-ins). Shiny02/flare01 sprites would go
  through this module; the clouds/WATERFALL1 particle kinds are not reconstructed.
- The split passes (modes 1 and 2) are reconstructed but the native draws mode 0 only, as the in-world branch
  does.
