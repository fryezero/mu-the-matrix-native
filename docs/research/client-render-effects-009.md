# Named bones, arrows 0x615/0x617, bow 0x12f9's sparks in the session, the bow kinds, the white arrow quads

RENDER-EFFECTS-009 closes four combat-effect leftovers of RENDER-EFFECTS-007:

- the named-bone service;
- the two arrows that need it (0x615, 0x617);
- bow 0x12f9's sparks in the native session, with the joint and particle kinds of that bow;
- the white quads of arrows 0x5b0/0x5b1.

[Handoff](../handoffs/RENDER-EFFECTS-009.md).

## Identity and method

Same pinned target as client-render-effects-004.md and -007.md:

- executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`;
- capture09 text `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` at 0x00401000;
- run10 image data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

"Verified" means authored compiled C compared with the original instructions under Unicorn by
`scripts/validate_render_effects9.py`. The tool reuses three harnesses:

- validate_render_effects7's effect harness;
- validate_joints' families;
- validate_render_effects' particle families.

The bodies were found by per-kind Unicorn block traces (which blocks a kind executes) and then read statically.
"Static" marks readings that were not executed. "Inference" marks native choices that the client does not decide.

| Family | Original bodies | Cases (recorded run, `--cases 20`) | Mismatches |
|---|---|---:|---:|
| CreateEffect 0x615/0x617 × subtypes 0/2/0x63 | shared arrow body, cases `0x013ccdda` / `0x013ccf98` | 120 | 0 |
| MoveEffect 0x615/0x617 | `0x0146a1f9..0x0146aa05` / `0x0146af38..0x0146b64c` with `0x0129f18a`, `0x012bd35a`, `0x0150e746`, the vec3 helpers and `0x00cfd15f` as client code | 120 | 0 |
| Named-bone service (`native/core/mu_named_bones.c`) | `0x012bd35a`, `0x0129f18a`, `0x0129f12c` | 400 | 0 |
| Joint 0x7fd5/3 and 0x7fd6/5: create, move, render | CreateJoint `0x01543446` / `0x0153c393`; MoveJoint `0x0156985b` / `0x01557945..0x01557a6e`; RenderJoints | 400 each | 0 |
| Particle 0x7f5a/0xd: create, move, render | CreateParticle `0x015c5882`; MoveParticles `0x0163533b`; RenderParticles | 400 each | 0 |

- **Totals:** 3,040 original-instruction cases, zero mismatches; 25/25 compiled mutants caught. The gate run
  (`--cases 2`) gives 304 cases and 25/25.
- **Body SHA-256 prefixes (local report):** move_615 `afc7e6dd`, move_617 `79943e31`, bone_find `b06156f9`,
  bone_index `44f47c0f`, owner_bone `b2f844e5`, bone_sprite `09f9dedd`, create_7fd5_3 `7f7ade56`,
  move_7fd5_3 `7e86f219`, create_7f5a_d `fad6b3cc`, move_7f5a_d `23a9a470`.

## The named-bone service (verified)

- **`0x012bd35a(name, fallback)`** is a model method. It returns the index of the first bone record (0x8c bytes
  from `+0x2c`, count `int16 +0x22`) whose name equals the `std::string`, compared with `0x0096c6da`. Otherwise
  it returns `fallback`. A model without records (`+0x2c == 0`) also returns `fallback`.
- **`0x0129f18a(name, own)`** is an object method. It does the same search on the object's model (getter
  `0x00966cc4`/`0x00eaa8cf` of `+0x5c`).
  - It returns NULL without a model, without records, or without a match.
  - Otherwise it returns `BoneTransform 0x06fce398 + 0x30·i`.
  - With `own`, it returns `+0x318 + 0x30·i` when the object's own bone buffer `+0x318` is set.
- **`0x0129f12c(bone)`** returns the owner's bone matrix `+0x318 + 0x30·bone`. It requires a model, `+0x318` set,
  and `0 <= bone < +0x22`; otherwise it returns NULL.

Native: `mu_named_bone_index` / `mu_named_bone_matrix` / `mu_owner_bone_valid` work on bone-name arrays. The skill
environment gains `bone_named(effect, name, fallback)` and `bone_transform(effect, bone, in, translate, out)`,
which is TransformPosition `0x012b6ef1` on that bone.

## Arrows 0x615 lightning_arrow and 0x617 Imperial_arrow (verified)

**Models (static).** The other startup routines' AccessModel calls load them:

| Type | AccessModel call | File |
|---|---|---|
| 0x613 | `0x018273a2` | `Data\Skill\8cha_arrow` |
| 0x614 | `0x0182e8f3` | `Data\item\apocalypse_arrow` |
| 0x615 | `0x0182ebac` | `Data\Skill\lightning_arrow` |
| 0x616 | `0x0182ee41` | `Data\item\TempleGuard_bow_arrow` |
| 0x617 | `0x0182fc7a` | `Data\Skill\Imperial_arrow` |

OpenTexture uses `"Skill\"` for 0x613, 0x615 and 0x617.

**Create.** These are 0x616's case of the shared body: impact = position, lifetime and `+0x70` 30, scale 1,
gravity −10, direction (0, −70, 0). The light is (0.3, 0.8, 1) for 0x615 and (1, 1, 1) for 0x617.

**Move 0x615 (`0x0146a1f9`).**

1. Without a model the case returns, with no hit check.
2. `0x0129f18a(o, "Line003", 0)` looks up the bone. When it finds it:
   - b = TransformPosition(matrix, (0, 0, 0), b, **translate 0**);
   - sprite 0x810a at b, scale 1, light (0.2, 0.3, 1)·g;
   - sprite 0x81cf at b, scale 0.1, light (0.4, 0.45, 1)·g. Here g = `0x0185caa4(0, 15, 70, 0.5)`, drawn once for
     each sprite;
   - step = VectorRotate(−direction / 10, AngleMatrix(angle));
   - for i < 10: particle 0x8081 + rand % 3, subtype 8, scale 0.35, light (0.25, 0.75, 1), no owner, at
     b + step·i + three `0x011ff622(−5, 5, 1)` jitters.
3. The arrow hit check runs.

**Move 0x617 (`0x0146af38`).**

1. Without a model the case returns.
2. Nine `0x0150e746(model, bitmap, 0x012bd35a(name, −1), scale, light, o, 0, 0, ones)` calls. Each is CreateSprite
   at TransformPosition(BoneTransform + 0x30·bone, (0, 0, 0), **translate 1**):
   - with light (1, 1, 1): red_01/0x7fe0 0.2, red_02/0x7fe0 0.4, red_01/0x80ba 0.15, red_02/0x80ba 0.35;
   - with light (0.6, 0.2, 1): t1..t5 on 0x7f7a with 0.1, 0.2, 0.3, 0.4, 0.3.
3. d = normalize(impact − position). The normalize is `0x00cfd15f`: v·(1/|v|), or zero within 1e-6 (`0x00a72592`).
4. Particle 0x85fb/2 (0.1, (0.5, 0.2, 1)) and particle 0x8450/4 (0.1, (1, 1, 1)) at the position, with d as their
   angle.
5. The hit check runs.

A missing name gives index −1. The client then reads the matrix 0x30 bytes before BoneTransform; the native reads a
zero matrix (out = BodyOrigin).

**Render (static).** RenderEffects' switch sends 0x613..0x617 (and 0x5b0, 0x60a, 0x612) to the default
`RenderObject(o, 0, 0, 0, −1, −1)` at `0x015324cf`. The table is `0x153271e`/`0x15327ee` from type 0x4ee.

**BoneTransform (inference).** Both moves read the global BoneTransform, which no call in either case poses. It
holds the bones of the client's last Animation, normally the last model drawn in the previous frame. The native
answers with the arrow's own model, posed at its frame, angle and scale with model-space bones (Animation without
translate).

- 0x617's sprites (translate 1) sit on the arrow's bones.
- 0x615's (translate 0) are model-space points near the world origin, as the client's are unless its last
  Animation translated. They are outside the view at the scene tiles.

## Bow 0x12f9's sparks in the session

`mu_sfx_bow_sparks` (verified in RENDER-EFFECTS-007) now runs after the shots of the hero's CreateArrows.

**The bone (static and inference).** The bone is `Weapon[Weapon[0].LinkBone].LinkBone`: the byte at
`+0x19b1 + 0x3fc·(byte +0x19b1)`, from `0x0158e076..0x0158e092`.

- For the Player, Weapon[0].LinkBone is 33.
- That byte lies past the hero's record, at CharactersClient + 0x3670·(i + 2) + 0x2f6d: another slot's data.
  No instruction in the text addresses `+0x2f6d`.
- The native has no such record and reads it as 0 (`MU_COMBAT_SPARK_BONE`, inference: a cleared slot).
- `0x0129f12c` then checks the hero's bone count.

**The position.** TransformPosition(bone, (0, 10, −130), translate 1) on the posed hero. The native uses the
weapon attach path: `mu_model_rotation_position` on the Player model plus the hero's position.

**The kinds.**

- The sparks' Spark02 0x7f25/0 particle was already consumed.
- Joint 0x7fd5/3 (**verified**): create is the subtype-0 body. Move adds velocity +0.1, light[0] /= 1.1, and sets
  light[1] and light[2] to light[0]. Render draws no record colour (as subtype 0).
- Joint 0x7fd6/5 (**verified**) is the trail of arrows 0x458/0x471/0x474.
  - Create: velocity 0, lifetime 999,999,999, 10 tails, scale, position = the target's `+0x188`.
  - Move: when the target is not live, the joint dies. Otherwise its position = target `+0x188` (the arrow's
    `field_188`).
  - The native maps an arrow's "this effect" joint owner to an effect object (`MU_COMBAT_EFFECT_OBJECT`: live,
    type, position, angle, light, `+0x188`), refreshed after MoveEffects as MoveJoints reads it. Other effects keep
    no object.
- Particle 0x7f5a/0xd (**verified**) is Carow's smoke.
  - Create: lifetime 20, scale (rand % 64 + 64)·0.01 (the argument scale is replaced), rotation rand % 360,
    gravity (rand % 32 + 60)·0.1.
  - Move: l = lifetime / 20, light (l, 0.5l, 0.1l), scale += 0.09.
  - Render: the generic smoke sprite.

## The white quads of 0x5b0/0x5b1 (static)

The models name `devil_arrow.jpg` (0x5b0) and `arrows_angelic.jpg` (0x5b1), which `Data\Skill\` lacks. The
startup opener `0x01832af3` calls OpenTexture with `"Skill\"` for both (recorded table
`reconstructed/objects/texture_preload.inc`). OpenTexture then tries its later steps, as RENDER-WORLDS-G2 found:

1. the bitmap-name map;
2. `Data\Item\`;
3. `Data\Item\Texture\`.

What each texture resolves to:

- **0x5b1.** `arrows_angelic.jpg` is found in `Data\Item\Texture\` (`mu_texture_names_find`).
- **0x5b0.** `devil_arrow.jpg` comes from the name map. `LoadBitmap("Effect\devil_arrow.jpg", 0x8182)` at
  `0x01833b47` (right after AccessModel(0x5b0), before the opener's OpenTexture calls) puts the name in the map.
  `mu_texture_names` does not rebuild that LoadBitmap, so the combat loader adds that one entry
  (`startup_bitmap_name`).

The native only looked in the model's folder, so these meshes drew untextured, which is white.

## Measurements

**Combat scenes.** Triple Shot at the spider, Lorencia 182,128, 30 frames, installed data. The 33 bow items of
CreateArrow's tables, base `f858e134` against the branch:

| Bow | Arrows | Unsupported requests | Consumed now |
|---|---|---|---|
| 0x12f9 (Carow) | 4 → 4 | 130 → **0** | 15 sparks, 141 particles, 15 joints |
| 0x12f8 (KCross) | 4 → 4 | 4 → **0** | 4 trails |
| 0x12f6 (ArrowDouble) | 3 → 3 | 3 → **0** | 3 trails |
| 0x1329 (0x615) | **0 → 4** | 4 → 310 | the arrows; their 0x8081..0x8083/8 particles are new requests |
| 0x132f (0x617) | **0 → 4** | 4 → 62 | the arrows and 279 sprites; 0x85fb/2 and 0x8450/4 are new requests |
| 0x1300 / 0x12ff (0x5b0/0x5b1) | 4 → 4 | 8 / 19 (unchanged) | textures found (1 mesh each) |
| the other 26 | unchanged | unchanged | |

Totals over the 33 bows: arrows 111 → 119. Unsupported requests 1,572 → 1,799. Without the two new arrows, the
other 31 bows go from 1,564 to 1,427.

**Identity.** Ten non-bow combat scenes (sword 41/42, staff 1/2/3/9/17, crossbow and bow 24, spear) have 11/11
identical PNGs each.

**DATA-ACQ-002 tours.** All 32 captures were rendered, base against the branch, with the same environment:

- normal mode: 64/64 PNGs, 32/32 OBJECT, 32/32 light and 32/32 frame reports byte-identical (the reports differ
  only in their own output path);
- `draw_all`: 192/192 files identical.

The kinds added here are not requested at those tiles.

**Frames.** Before/after strips of bow 0x12f9, 0x5b0, 0x615 and 0x617 are local (`renders/render-effects-009/keep`).

- 0x12f9: the sparks' orange flash at the hero's hand, the green 0x7fd6/5 trails and the orange smoke behind the
  Carow heads.
- 0x5b0: dark textured arrows where white quads were.
- 0x615/0x617: the arrow models draw where nothing drew before.

## Compiled planted mistakes

Each mutant edits production source (`arrow_fx.inc`, `mu_named_bones.c`, `particles.c`, `joints.c`) and is
compiled separately. Recorded run, caught/cases:

| Mutant | Caught | Mutant | Caught |
|---|---|---|---|
| line_name | 25/40 | svc_fallback | 12/80 |
| line_translate | 25/40 | svc_first | 20/80 |
| lightning_tint | 25/40 | svc_count | 8/80 |
| lightning_steps | 25/40 | svc_own | 19/80 |
| lightning_jitter | 25/40 | trail_life | 400/400 |
| lightning_spark | 25/40 | trail_rise | 400/400 |
| imperial_order | 28/40 | trail_fade | 241/400 |
| imperial_scale | 32/40 | trail_grow | 241/400 |
| imperial_tint | 32/40 | spark_speed | 200/400 |
| imperial_axis | 31/40 | spark_fade | 198/400 |
| imperial_sub | 32/40 | spark_kind | 200/400 |
| | | trail_lifetime | 200/400 |
| | | trail_tails | 200/400 |
| | | trail_follow | 122/400 |

**25/25 caught.** None is equivalent: each changes a value or a branch that the cases reach.

## Limits

- **The spark bone** is the native stand-in 0 for a byte of another CharactersClient slot. A live read of
  `[[0x0a39d754] + 0x9c4d]` with the hero in Lorencia would give the client's value. No live read was taken: the
  game lock was free, but the data-acq-002 readers' build is gone and the rest of the lane did not need a live
  read.
- **BoneTransform** of 0x615/0x617 is the arrow's own pose (inference, above).
- **0x615 / 0x617 draw as dark meshes natively.** Their glow meshes (elec_light, gsw_line, force_Pillar,
  alpha_light2) are drawn with BlendMesh −1 through the default RenderObject, as the client's dispatch does. Whether
  the client blends them is a mesh-draw question (RENDER-ITEMS / meshdraw), not checked live.
- **Particle kinds these arrows request that stay unsupported:**
  - 0x615's 0x8081..0x8083/8 and 0x617's 0x85fb/2, 0x8450/4;
  - the other bows' kinds listed in the handoff.
- **Joint 0x7fd6/5's no-model branch** (the target's model missing) is not exercised. The arrow always has its
  model when it moves.
- **Arrow paths left out** (unchanged from 007): the ground test of skills 0x7e7/0x7fc/0x7fd, the arc skill 0x2d8,
  0x442 with a straight skill, and 0x45e's render-time particles and decal.
- **The six pet particle kinds** were not started (Clud64, firehik03, Impack01/1, firehik_mono ×3).
- No live comparison.
