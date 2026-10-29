# Other bows' arrows, bow 0x12f9's sparks, rank-5 pants, bone −1 attach, Rudolph's gold pieces

RENDER-EFFECTS-007 closes the effect leftovers of RENDER-EFFECTS-004/005/006/008: 30 of the 32 other bow arrow
models, bow 0x12f9's sparks, the rank-5 group-9 (pants) owner question, the EffectManager's bone −1 attach and
Rudolph's effect 0x3fa with its Shiny01 twinkle. [Handoff](../handoffs/RENDER-EFFECTS-007.md),
[coverage inventory](client-skill-visual-coverage.md#render-effects-007-evidence-and-limits).

## Identity and method

Same pinned target as client-render-effects-004.md: executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, capture09 text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` at 0x00401000, run10 image data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

"Verified" means authored compiled C compared with the original instructions under Unicorn by
`scripts/validate_render_effects7.py` (validate_skill_fx's harness: rand, terrain height, sin/cos, CreateEffect,
CreateParticle, CreateJoint, CreateSprite, AddTerrainLight, the model getters, pose and bone, the hit checks and the
area request are recording services; AngleMatrix, VectorRotate, 0x011ff622 and the Inferno burst run as client
code). On top of validate_skill_fx's comparison it compares CreateJoint's arguments 7..13 (the colour behind
argument 11 by value), CreateEffect's key and scale, and lets the client write the caller's position and angle
vectors. The block map of the shared bodies came from per-type Unicorn traces (which instructions each type and
subtype executes), not from a static reading alone.

| Family | Original bodies | Cases (recorded run) | Mismatches |
|---|---|---:|---:|
| CreateEffect, 30 arrow types × subtypes 0/2/0x63, Arrow01/0x63, 0x3fa/0 | shared arrow body `0x013cb34d..0x013cd688`; 0x471/0x458 `0x013ca9f2`/`0x013cac12`; 0x459 `0x013cae32`; 0x442 `0x013ce0de`; 0x474 `0x013d8da1`; 0x5b0/0x5b1 `0x013f5f8c`/`0x013f6350`; 0x3fa `0x013de0ff` | 1,840 | 0 |
| MoveEffect, same kinds | `0x01464238..0x0146af38` (cases per type below), 0x474 `0x014712e8`, 0x5b0/0x5b1 `0x014abb41`, 0x459's motion `0x014ed2ef`, 0x3fa `0x01437d53`, bounce `0x0150de66` | 1,840 | 0 |
| Bow 0x12f9's sparks | CreateArrows `0x0158d5bd` with bow 0x12f9, sparks `0x0158dfdc..0x0158e1aa` | 400 | 0 |
| Rank-5 pants owner check | full RenderObjDraw `0x0176ce74`, group-9 path `0x0174a4bc..0x0174ae0e` | 280 | 0 |
| Bone −1 world matrix | `0x0129faee` with `0x00cef49d`, `0x00a8c87e` | 400 | 0 |
| Shiny01 0x7f66/7 create / move / render | `0x015e64d3`, `0x01658fef`, the shared record render | 400 each | 0 |

**5,960** original-instruction comparisons, zero mismatches (`--cases 20 --mutations`); the gate run
(`--cases 2`) gives 596. Body SHA-256 prefixes (local report): arrow create `95e8a420`, 0x471/0x458/0x459/0x442/0x474
creates `262929ea`/`59371160`/`6cf79fa5`/`7071d87b`/`b5a2755e`, 0x5b0/0x5b1 `f887597f`, shared moves `37741350`,
`a51c7d25`, `edea5f20`, `6628c97e`, `c9282a38`, `63145ff6`, `25243b01`, 0x459 motion `5ea0bb1c`, bounce `bbd19e38`,
straight-skill test `5ee890d8`, sparks `98d96376`, 0x3fa create/move `03ffdd7d`/`bc751b4c`, world matrix `c7b30a84`,
rotation `c9f7da9b`.

## Recovered behavior: the arrows (verified)

**Which arrows.** CreateArrow's two bow tables (RENDER-EFFECTS-004) name 32 models besides Arrow01. The model loader
`0x018202b4` (calls `0x018333b8..0x01837389`, static) names their files: ArrowSteel01 (0x43c), ArrowThunder01,
ArrowLaser01, ArrowV01, ArrowSaw01, ArrowNature01 (0x441), ArrowBomb01 (0x442), ArrowWing01 (0x443), ArrowDouble01
(0x458), Arrow_Spark (0x45a), CW_Bow_Skill (0x45b), sketbows_arrows, bloodangel_bow_arrow, absolute_gunbow_arrow
(0x45c..0x45e), KCross (0x471), Carow (0x474), LaceArrow (0x47f), gamble_arrows01 (0x525), devilcrossbow_arrow
(0x5b0), angelic_arrows (0x5b1), Darkangel_Bow_arrow (0x60a), HolyAngelBowArrow, hs_soularcherbow_arrow,
blue_eyebow_stand_arrow, matery_bow6_arrow (0x60d..0x610), arrow_mastery7s (0x612). 0x459 and 0x613..0x617 have no
loader call there; RenderEffects skips 0x459 (its joint rings are its visual).

**The straight skills.** `0x013bce8f` answers true for skills 0x2d7, 0x7e7, 0x7fc, 0x7fd, 0x7fe: those arrows skip
the 130-unit lift, the random roll (angle y = rand % 360) and the per-step turns below.

**Create, shared body `0x013cb34d`.** Blend mesh 1 (Arrow01), −2 (0x441) or 0 (0x43d/0x43e/0x43f/0x443); velocity 1;
lifetime 30; the bow offset (−10, −60, 135) rotated by the angle unless info word4 is a straight skill (or 0x45c/1,
0x43b/6). Then per type:

| Types | Create |
|---|---|
| 0x43c..0x441, 0x45b, 0x47f (default `0x013cd0f2`) | scale 0.8, direction y −70 |
| 0x443 | scale 1.8, direction y −50, gravity −10 |
| 0x45a | scale 1, −70; joint 0x7f79 (sub 0xe, scale 50, arg7 0x28) on the arrow |
| 0x45c / 0x45d / 0x525 | 0.8 / 1.15 (lifetime and +0x70 24) / 0.8, −70, lifetime 30 |
| 0x45e | position += (0, −30, 0) rotated by the caller's angle; scale 0.7, −40, lifetime/+0x70 50; joint 0x80e3/4 scale 100 |
| 0x60a | lifetime 30, scale 1.5, gravity −10, direction (0, −70, 0); joint 0x80e4/1 scale 20 at position + (0, 100, 0) rotated (the caller's position/angle vectors are written) |
| 0x60d..0x614 | +0x70 = lifetime 30, scale 0.2, gravity −10, direction (0, −70, 0), light (0.3, 0.8, 1); 0x60d joint 0x80e3/5 (15, colour (1, 0.7, 0.4)) from 40 ahead; 0x60e joint 0x7f79/0x16 (70, 0x28) after its roll; 0x60f joint 0x828c/2 (140, (0.1, 0.36, 0.55)); 0x610 joint 0x80e3/5 (50, (0.2, 0.55, 1)) |
| 0x616 | impact = position, lifetime 30, scale 1, gravity −10, direction, light (0.3, 0.8, 1) |
| 0x47f / 0x45b (tail) | blend 1, roll, joint 0x7f79/0xc (40, 0x50) / blend 0, scale 1, roll, joint 0x7f79/0xf (50, 0x28) |

Subtype 2 (skills 0x34/0x1a0) adds the 0x46c trail effect and the client's own hit test. The separate bodies:
0x471/0x458 (lifetime 30, blend −2, scale 1, lift 130, direction (0, −70, 0), `+0x188` = position, joint 0x7fd6/5
scale 100, trail on any nonzero subtype); 0x459 (direction (0, −60, 0), impact = position + (−10, −100, 15) rotated,
three/four/eight 0x7f78 ring joints at the impact on the yaw only); 0x442 (offset, blend 0, scale 1, direction y −30,
gravity −10, lifetime 40); 0x474 (subtypes 0/2 only; 0x63 keeps the common initialisation); 0x5b0/0x5b1 (lifetime 30,
scale 1.5, gravity −10, lift, direction (0, −60, 0), two/one coloured joints 0x814c+0x8182 / 0x8185 18 units ahead
along AngleToVector `0x00d015d5`).

**Move.** Each type has its own MoveEffect case after the common luminosity prologue; most end in the arrow hit
check `0x013bd374`:

| Types | Move (each step) |
|---|---|
| 0x43c..0x440, 0x45e, 0x5b0 | hit check only |
| 0x441 / 0x443 | two spinning lightning2 0x7f37 sprites (rotation ±(int)WorldTime × 0.1); four scattered particles 0x7f73+rand%3 / 0x7fcd/1 (+0x7f5a); 0x441 turns +30; terrain light (0.6, 0.8, 0.8)·lum |
| 0x442 | flare01 sprites (1, 0.6, 0.4); four 0x7fcd/1; falls and bounces on the terrain (gravity and forward speed × 0.4, `0x0150de66`); at lifetime 1 the Inferno burst `0x013c07f4` and, for the hero's arrow, the area request (100) |
| 0x458 / 0x471 / 0x474 | turns; `+0x188` follows the arrow (0x471/0x474 one step ahead); 0x471 fades its blend light in over 5 steps; 0x474 three 0x7f5a/0xd and the Inferno burst at lifetime 1 |
| 0x459 | subtype 2: turn +30, terrain light at the impact, trail at lifetime 13; its rings (impact), not the arrow, move along the rotated direction |
| 0x45a / 0x45b / 0x47f / 0x525 | turn +35 / effect 0x477/4 with light (0, 1, 0.1) / turn +60, even steps three 0x7f78/5 and effect 0x477/3 / turn +60, two Spark03 0x7f26/0x1e and 0x7f5a/0x18 |
| 0x45c / 0x45d | model pose; flare01 sprites at bone 0 + direction; on lifetimes 30/28/26/24 0..2 pairs of effect 0x45f; at 30 a 0x7f79/0x12 beam (90, colour (0.4, 0.4, 0.9)) / firehik03 0x8085/0x11 with a lifetime-shaped size |
| 0x5b1 | rand % 3 == 0: 0x8184/1 (scale 0.1, (0.4, 0.95, 1)) |
| 0x60a..0x616 | sprites, particles and effects per type (0x60a three sprites 0x7f7a/0x7f6c/0x8108 and effect 0x60b; 0x60d effect 0x477/4 on rand % 4 == 0; 0x60e 0x8081+k particle and sprites; 0x60f effect 0x38b5/1 every third step, 0x7f5a/0x4e and Spark03/0x1e; 0x610 0x810c, 0x7f5a/0x7a, effect 0x611; 0x612/0x613 0x83b3/0x8155 (+0x810a/0xe); 0x614 three sprites and 0x83b8/0x8084; 0x616 a 0x85cc joint at 30, sprites 0x85c3/0x7f78, five 0x7f5a/0x86 and five 0x810a/0x24) |

0x60a, 0x610, 0x612..0x616 skip their case (and the hit check) when their model is absent. 0x45c and 0x474 with
subtype 0x63 and 0x459 with subtypes 0/0x63 do nothing of their own.

**Render (static, dispatch emulated).** RenderEffects' type switch `0x015183cb` sends 27 of the 30 types to the default
`RenderObject(o, 0, 0, 0, −1, −1)` for model types 0x40f..0x7a3 (`0x015324d2`); 0x471's case is the same call;
0x459 draws nothing; 0x45e (`0x01518f4c`) adds a body light, an animation at twice the speed, particles 0x7f5a/0x6d
and 0x8108 and a ground decal 0x8002 (not reconstructed).

## Bow 0x12f9's sparks (verified)

After CreateArrows' shots (not after its early returns), when the shooter's model exists and its weapon bone
(character `+0x19b1`, read through its own slot index) resolves (`0x0129f12c`):
p = TransformPosition(bone, (0, 10, −130)); fifteen times: angle (rand % 360, 0, 0), on rand % 2 == 0 a joint 0x7fd5/3
(scale 10) at p, then a Spark 0x7f25/0 particle at p.

## Rank-5 pants (group 9) (verified)

`[ebp−0x1e10]` in RenderPartObjectBody is the item group (7 helm, 8 armour, 9 pants). The pants' path `0x0174a4bc`
draws the lit body and named meshes (Item1161_Blue / Item1161_skirt with textures 0x84d9..0x84e0, the level-9
0x8239 passes) and returns through the epilogue or the generic chain: **it has no owner block**. Under the full
RenderObjDraw with readable owner bones (validate_render_effects5's harness), the seven rank-5 pants types run the
group-9 path in every case (list A, the other lists and the level-9 overlays all reached) and emit no particle or
sprite and draw no rand(), while the armour control 0x1c26 emits 48 effects in 12 cases. Nothing is added to
`rank5_owner.inc`; the pants' named-mesh passes belong to the body executor (RENDER-ITEMS-002 part 13).

## Bone −1 attach (verified)

`0x0129faee(out)` with the object in ecx: the 4×4 of `0x00cef49d(a, b, c)` with a = rad(angle z), b = rad(angle y),
c = rad(angle x) (`0x00a8c87e`: binary32 × 0.017453292), binary32 sin/cos:
m0 = cb·ca, m4 = −(cb·sa), m8 = sb; m1 = sc·sb·ca + cc·sa, m5 = −(sc·sb·sa) + cc·ca, m9 = −(sc·cb);
m2 = −(cc·sb·ca) + sc·sa, m6 = cc·sb·sa + sc·ca, m10 = cc·cb; m3 = m7 = m11 = 0, m15 = 1; the 3×3 scaled by `+0xa0`;
m12..m14 = the position. `0x0129f671` uses it as the external matrix of a record following bone −1.

## Rudolph's gold pieces 0x3fa and Shiny01 0x7f66/7 (verified)

The collector's visuals (`0x00eaf993`, state 3) call CreateEffect(0x3fa, 0, no owner, key −1, scale 0). The loader
(`0x00a938d2`) gives it `Data\Monster\sulgold.bmd`: gold pieces. Create: lifetime rand % 10 + 50, scale
(rand % 10 − 5) × 0.02 + 1.6, three random angles, gravity rand % 10 + 10, direction = ((rand % 10 − 5) × 0.1,
(rand % 60 − 40) × 0.1, 0) × 1.3 rotated by the angle, spin axis `+0x64` = rand % 3. Move: that angle +10; position +=
(direction × 1.2, gravity × 1.5); gravity −1.5; on the terrain it bounces (gravity × −0.3, lifetime −2); then
position += direction; the common animation and motion follow.

Shiny01 0x7f66/7 (Rudolph's twinkle above it): scale 0.1 (kept at `+0x88`), lifetime rand % 10 + 20, position ±25
scatter, gravity 1, three random angles, velocity (0.4, 0.4, 0.4) rotated; rotation rand % 20 − 10. Move: scale =
sin(lifetime × 2°).

## Compiled planted mistakes

Each mutant edits production source (arrow_fx.inc, pet_fx.inc, particles.c, mu_effect_scene.c), compiles separately
and runs the same comparator; recorded run (caught / cases): bow offset 14/40, 0x43f blend 40/40, 0x443 scale 40/40,
0x471 lift 19/40, 0x459 rings 40/40, 0x442 lifetime 19/40, 0x60d tint 40/40, 0x47f roll 2/40, 0x45b arg7 40/40,
subtype-2 trail 40/40, spin rate 32/40, 0x441 scatter 40/40, 0x443 light 40/40, 0x47f parity 40/40, 0x442 bounce
18/40, 0x471 fade 22/40, 0x45d glow 10/40, jitter y 22/40, 0x610 glint 33/40, 0x60e spark 40/40, 0x5b1 rate 40/40,
0x45c beam 6/40, spark offset 6/40, spark joint 6/40, gold lifetime 40/40, gold bounce 20/40, twinkle pulse 240/400,
twinkle spread 400/400, world-matrix sign 40/40, axes 35/40, scale 30/40. **31/31 caught.**

## Native integration

- **Arrows.** `reconstructed/combat/arrow_fx.inc` (create, move, the sparks) is included by skill_fx.c through one
  line each in effect_supported, CreateEffect and MoveEffect, plus 0x459's motion in the second switch. Arrow01's
  create moved into the same function unchanged (validate_skill_fx and validate_render_effects4 pass); Arrow01 now
  also accepts subtype 0x63 (CreateArrow's flag 2). `mu_sfx_effect.field_188` and `mu_jt_call.arg7/arg8` are
  appended fields.
- **Session.** `mu-walk --combat-bow 0xITEM` picks a bow item for `--combat-weapon bow`; the bow's arrow model loads
  in one extra combat slot (only the equipped bow's), and the native crossbow (0x12ee) now fires ArrowSteel 0x43c
  instead of counting it unsupported.
- **Bone −1.** `mu_effect_object_world_matrix` (mu_effect_scene) is the external matrix of `.ein` records following
  bone −1 (Ignis Volcano types 175/176 in the effect table); they update instead of counting `unposed`.
- **Rudolph.** `pet_fx.inc`; the gold model loads in the world particle module in every world
  (`MU_WORLD_FX_MODELS` 17 → 18); Shiny01 subtype 7 joins the existing Shiny01 cases in particles.c.

## Limits

- **0x615 and 0x617** stay refused: their MoveEffect cases place sprites at model bones looked up by name
  (`0x0129f18a` "Line003", `0x012bd35a` "red_01"), which no native service answers.
- Arrows of skills 0x7e7/0x7fc/0x7fd add MoveEffect's ground test `0x014eca2e` (not reconstructed, as for Arrow01);
  the arc skill 0x2d8 is refused at creation; 0x442 with a straight skill is refused (the client rotates an unset
  stack vector there). Subtypes other than 0/2/0x63 (0x441/1, 0x43b/3..4, 0x45d/3, 0x525/3, 0x459/1, 3) are not
  arrows' and stay refused.
- 0x45e's render extras (particles and the 0x8002 decal) are not drawn; its model is.
- Natively many of the arrows' joints (0x7fd6, 0x7f79, 0x80e3, 0x80e4, 0x828c, 0x7f78/0xb, 0x814c, 0x8182, 0x8185,
  0x85cc) and particle kinds (0x7fcd/1, 0x7f5a/0, 0xd, 0x18, 0x4e, 0x7a, 0x86, 0x7f73..0x7f75, 0x7f78/5, 0x8184/1,
  0x8081..0x8083, 0x810a, 0x810c, 0x83b3, 0x8155, 0x83b8, 0x8084, 0x8085/0x11) are created as calls but counted
  unsupported by the native joint/particle modules; the arrow models, their sprites and terrain lights draw. The
  white quads of 0x5b0/0x5b1 in native frames are a texture-resolution issue of those models (RENDER-ITEMS).
- The sparks are verified but not called by the native session: it has no weapon-link bone table (`+0x19b1`) or
  world bone transform for the hero.
- Natively Rudolph never reaches state 3 (no ground items are offered to the collector), so 0x3fa is exercised by
  `pet_gold_host`, not by a session. The pets' other particle kinds (Clud64 0x7ffd/0xb, firehik03 0x8085/1,
  Impack01 0x7efa/1, firehik_mono 0x8086/4, 0x8087/8, 0x8089/5) remain; their create bodies are `0x015c1930`,
  `0x015d9074`, `0x015c3348`, `0x015d474d`, `0x015b95cc`, `0x015d980f` (traced, not reconstructed).
- No live comparison with the original client.
