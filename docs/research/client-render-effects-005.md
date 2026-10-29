# Rank-5 item owner effects and Deep Dungeon's DungeonStone

RENDER-EFFECTS-005 completes the rank-5 armour body's owner block, which earlier
parts left open after the lit mesh streams, and consumes the `0x43a` effect that
Deep Dungeon object type 52 requests. [Handoff](../handoffs/RENDER-EFFECTS-005.md),
[coverage inventory](client-skill-visual-coverage.md#render-effects-005-evidence-and-limits).

## Identity and method

The pinned target is the same as in client-render-effects-004.md: executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, capture09 text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` at 0x00401000, run10
image data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

"Verified" below means that authored compiled C was compared with the original
instructions under Unicorn by `scripts/validate_render_effects5.py`.

- **Owner block.** The comparison runs the *complete* RenderObjDraw `0x0176ce74` for every
  rank-5 type through the validate_item_next harness. The real pose call, the real bone lookup
  `0x0129f12c` and the real TransformPosition `0x012b6ef1` are executed. The harness installs
  OBJECT `+0x318` and the model bone count after the pose call (`0x01747a0a`).
- **Recorded services.** rand() is a scripted stream. The named-mesh lookup `0x012bd4a6`,
  CreateParticle `0x0168fafd` and CreateSprite `0x01692eb7` are recording stubs.
- **What must agree.** The whole mesh stream, every emitted effect and the rand() count. Effect
  fields are compared bit for bit, including the zero angle, NULL owner/arg8, the OBJECT owner,
  rotation 0, blend 0, axes 4 and the {1, 1, 1.0} sheet.
- **Particle kinds** use validate_particles' create/move/render families. Fade boundaries are
  directed: lifetime·2 against the initial lifetime 10/20.
- **DungeonStone** uses validate_skill_fx's effect_create/effect_move families.

| Family | Original bodies | Cases (recorded run) | Mismatches |
|---|---|---:|---:|
| Owner block, 19 types | blue `0x01747d6d`, 0x1c2b `0x0174888d`, list B `0x01749294`, list A `0x01749cc5` (inside the full RenderObjDraw) | 3,800 | 0 |
| 0x84e2/0, 0x83de/4 create | `0x0160eb48`, `0x015d1f29` | 2,000 | 0 |
| 0x84e2/0, 0x83de/4 move | `0x01686fa3`, `0x0164455b` | 2,000 | 0 |
| 0x84e2/0, 0x83de/4 render | `0x015a7540`, `0x015a3c58` | 2,000 | 0 |
| DungeonStone 0x43a create | `0x013d6f51..0x013d7139` | 500 | 0 |
| DungeonStone 0x43a move | `0x0146b809..0x0146b940` | 500 | 0 |

The recorded run (`--cases 200 --particle-cases 2000 --stone-cases 500 --mutations`) gives
**10,800** original-instruction comparisons, zero mismatches. The gate run gives 1,190.
Two LoadBitmap calls also match:

- `0x018250a5`: `Effect\smoke_line03.jpg` → 0x83de, LINEAR/CLAMP.
- `0x0182eb98`: `Item\texture\lighting01_10cha.jpg` → 0x84e2, LINEAR/**REPEAT**.

Body SHA-256 prefixes (local report):

| Body | Prefix |
|---|---|
| Owner variants: blue / 0x1c2b / B / A | `ba0ea5e3` / `4c6ca737` / `785e8478` / `9bfdc5a6` |
| Bone lookup | `b2f844e5` |
| Random scale `0x0185caa4` | `8af8c850` |
| 0x84e2 create / move / render | `6a0defb0` / `8111214f` / `4d292937` |
| 0x83de create / move / render | `8b92930f` / `d86fef15` / `30722097` |
| DungeonStone create / move | `ac702cc6` / `dc671e38` |
| CreateEffect wrapper / Deep Dungeon call | `272ba529` / `d9514a42` |

## Recovered behavior

**Selection (verified).** RenderPartObjectBody builds four type lists at
`0x01746fac..0x0174710e`. Each list has its own copy of the body and owner block:

| List | Types |
|---|---|
| Blue | 0x1c26, 0x1c27, 0x1c2c, 0x1c2e, 0x1c2f, 0x1c33, 0x1c44 |
| Single | 0x1c2b |
| B | 0x1c25, 0x1c29, 0x1c31, 0x1c32 |
| A | 0x1c24, 0x1c28, 0x1c2a, 0x1c2d, 0x1c30, 0x1c34, 0x1c7a |

The owner block runs only after the **lit** body (model `+0x50`). It continues only when
`0x0129f12c` returns bones 35 and 26. That requires OBJECT `+0x318` to be set and the bone to be
below the OBJECT model's bone count (`+0x22`). Otherwise the function returns before the
effects and before the level-9 overlays. So no-owner and unlit results stay exactly what
RENDER-ITEMS-002H verified.

**Effects (verified).** Three TransformPosition calls use the item model's scale/origin and the
owner's bones:

- `a = T(bone 35, P1)`;
- `b = T(bone 26, P2)`;
- `c = T(bone 35, P3)`.

Twice, `a` and then `b` receive a jitter. The jitter is drawn in rand() call order z, y, x as
`centre − rand() % m`. After each jitter pass, CreateParticle(0x84e2, b) and then
CreateParticle(0x84e2, a) are emitted. Both use the zero angle, light (0.7, 0.8, 2.0) and
subtype 0. Then come CreateSprite(0x7fdd flareBlue, c, 0.8) and CreateParticle(0x83de, c).

- **Sprite light.** `L = (rand() % 5) / 5 + 0.5` on all three channels. It comes from
  `0x0185caa4(0, 4, 5, 0.5)` over `0x011ff622`. The sprite's owner is the OBJECT.
- **0x83de particle.** Light (0.2, 0.2, 0.4), subtype 4, scale 0.2.

Per-variant constants:

| Variant | P1 | P2 | P3 | jitter m (z, y, x) | 0x84e2 scale |
|---|---|---|---|---|---:|
| Blue | (−25, 0, 20) | (−20, 0, −15) | (10, 0, 10) | 24, 20, 10 | 0.4 |
| 0x1c2b | (−27, 0, 15) | (−27, 0, −15) | (8, 0, 15) | 30, 20, 20 | 0.4 |
| B | (−25, 0, 18) | (−20, 0, −25) | (10, 0, 20) | 20, 10, 20 | 0.5 |
| A | (−30, 0, 15) | (−30, 0, −15) | (10, 0, 20) | 30, 10, 10 | 0.4 |

The jitter centre is m/2 in every variant.

**Level-9 overlays (verified).** These are gated by RenderPartObjectBody's level word, not by the
glow level. RenderObjDraw supplies that word only on the level ≥ 9 glow paths (quality > 1). This
is the same rule the body executor's level split already uses. A record that forces glow 9 on a
raw +8 item therefore draws no overlay.

- **Blue variant, two passes.** First the `Item1161_Blue.jpg` named mesh with texture 0x8239,
  flags 2, alpha 1, the body pulse and UV `time·0.0001`. Then the `Item1161_Black.jpg` mesh with
  no texture, flags 6, alpha 0.26 and the OBJECT blend light.
- **Other variants, one pass.** Mesh 1 with texture 0x8239 and the pulse.

All overlay passes come right after the body meshes and before RenderObjDraw's later glow
passes. Their model-field snapshots are therefore the part-body ones.

**Particles (verified).**

| Kind | Create | Each step |
|---|---|---|
| 0x84e2/0 | lives 10, scale 0, alpha 0, random rotation | Grows by initial scale/10. Alpha rises by 0.2 while 10 < 2·lifetime, then falls by 0.2. |
| 0x83de/4 | lives 20, scale 0, alpha 1 | Grows by initial scale/20 and fades by 0.05. |

Both draw light × alpha.

**DungeonStone 0x43a (verified bodies; static call site).**

- **Loading.** The world model loader's case for worlds 116–120 (jump table `0x0184307f`,
  index 35, `0x0184159b`) loads `Data\Object2\DungeonStone01.bmd`.
- **Call site.** Deep Dungeon type 52 calls the CreateEffect wrapper `0x013c0eaa` with key −1,
  word4 = `(u16)(int)` object scale, field8 −1 and **scale 0.0**. The wrapper passes that scale
  to the core. RENDER-WORLDS-N's validator already asserts these constant arguments.
- **Create.** Lifetime `rand % 16 + 24`. Scale is the raw argument: the common init's 0.9
  default for a non-positive scale is overwritten. Gravity is `−(rand % 4)`. The fling
  `(rand % 64 − 32, −(rand % 32 + 50), rand % 128 + 200)` is rotated by the angle and added to
  the position.
- **Move.** z += gravity, then gravity −1. On terrain contact: z = ground,
  gravity = −gravity·0.4, lifetime −4, direction y −2.
- **Visibility (inference from the static reading).** RenderEffects has no `0x43a` case, so the
  stones Deep Dungeon creates are drawn at scale 0, which is degenerate and invisible. They still
  consume six rand() calls each and occupy effect slots.

## Compiled planted mistakes

Each mutant is compiled separately from production C and run through the same comparator. The
recorded-run detections are below (the cases column is the number of cases run).

| Group | Cases | Mutants and detections |
|---|---:|---|
| Owner block | 3,800 | jitter modulo 959, jitter centre 959, jitter axes 2,603, particle order 2,603, bone 26 → 25: 2,603, bone gate 285, variant-B scale 548, glint 2,093, smoke light 2,603, level gate 452, level word 558, overlay UV 853, Black alpha 319, variant list 137 |
| Particles | 400 | bolt life 400, smoke alpha 400, bolt fade boundary 59, smoke fade 274, alpha light 278 |
| DungeonStone | 100 each | lifetime 100, scale 83, fling 100, fall 98, bounce 51, wear 51 |

**25/25 caught.**

## Native integration

- **Body executor.** `mu_rc_item_draws_owner` sets a thread-local owner host. At its end,
  `rank5_body` calls the separate `rank5_owner.inc` hook. The body executor itself is unchanged,
  and every caller of `mu_rc_item_draws_context` keeps the no-owner domain.
- **Effects.** The hook emits effects in client order, so the native caller creates them at once
  on the shared random stream. Overlay draws use the existing sink.
- **Native caller.** `mu_renderchar_draw_item_owner` supplies the owner's bones (an authored
  owner: the character tool's Player skeleton, since no equipment feed exists).
- **Particle pool.** The two particle bitmaps are registered in the shared pool. They are
  inserted before the relative-to-end slots, so existing slot tests keep their positions.
- **Particle steps.** `mu-render character` now steps particles between frames. Frame 0, whose
  SHA is printed, is unchanged.
- **Deep Dungeon.** The type-52 event is forwarded to the existing scaled-effect hook (key 0xffff,
  scale 0) instead of being counted as unsupported. The DungeonStone model loads only in worlds
  116–120.

## Limits

- **Owners.** No equipment/session feed: native owners are authored (character tool). The
  client's sprite owner (OBJECT) is not bound natively. Native sprites are owner-free, as in the
  earlier link effects.
- **Saturation.** The lit rank-5 body draws saturate white in native frames because textures
  0x84d9..0x84db and 0x8239 are not in the native item texture set. That is the existing
  RENDER-ITEMS limit; this lane did not change it.
- **Group 9 (pants).** The rank-5 path `0x0174a4bc` (raw group 9) is outside `mu_rc_item_rank5`
  and untouched.
- **DungeonStone.** Its invisibility at scale 0 is inferred from the static reading of
  RenderEffects, not from a live capture.
- **Not done in this lane:**
  - **Other bows' arrows** (32 models 0x43c–0x617): they share one create body
    `0x013cb34d..0x013cd66f` with per-type branches, and each has a distinct move. Measured
    against Arrow01, every type differs in create and/or move (see the handoff table).
  - **Bow 0x12f9's sparks.**
  - **Rudolph's 0x3fa and the pet particle kinds.**
