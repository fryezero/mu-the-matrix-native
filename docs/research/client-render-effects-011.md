# The bows' remaining particle kinds and effects, RenderEffects' 0x45e case, effect 0x70c, the functor tick

RENDER-EFFECTS-011 continues RENDER-EFFECTS-010's "Remaining":

- the 33 bows' remaining requests (16 particle kinds, the effects 0x477/3, 0x477/4, 0x60b/0, 0x611/0, 0x45f/0,
  0x45f/1);
- 0x45e's render-time extras (RenderEffects' case 0x01518f49);
- the 0x613..0x617 render-registry functors' animation tick, now per drawn frame;
- the ground skills' effect 0x70c and the clearing site of the owner flag +0x64;
- a live read of the spark bone byte `[[0x0a39d754] + 0x9c4d]`.

[Handoff](../handoffs/RENDER-EFFECTS-011.md).

## Identity and method

Same pinned target as client-render-effects-004/-007/-009/-010 (executable SHA-256 `3cf91f3c…5527a`, capture09
text `2bd5f2e9…3724` at 0x00401000, run10 image data `c985e2e6…a0672f`).

"Verified" means authored compiled C compared with the original instructions under Unicorn by
`scripts/validate_render_effects11.py`. It reuses validate_particles' create/move/render families (the owner
OBJECT's live byte +0x00 defined, a running clock, CreateParticle 0x0168fafd as a recording stub inside a move),
validate_render_effects7's CreateEffect/MoveEffect families (with the spin +0x194 and +0xd8 defined, CRT pow
0x0198c480 as the host's double pow) and a new family that enters RenderEffects 0x015181fa at its case 0x45e. The
bodies were found by per-kind Unicorn block traces (blocks a kind executes that an unknown kind does not) and read
statically. "Static" marks readings that were not executed; "inference" marks native choices the client does not
decide.

| Family | Original bodies | Cases (`--cases 20`) | Mismatches |
|---|---|---:|---:|
| Particle create / move / render, 16 kinds | below | 320 each | 0 |
| CreateEffect, 0x477/3, /4, 0x60b/0, 0x611/0, 0x45f/0, /1, 0x70c/0 | below | 280 | 0 |
| MoveEffect, the same kinds | below | 280 | 0 |
| RenderEffects case 0x45e | `0x01518f49..0x0151930a` | 240 | 0 |

**Totals:** see the handoff (recorded run with 75 compiled mutants, all caught). The registry run (`--cases 2`)
gives 176 cases and 75/75.

## The bows' particle kinds (verified)

All in `reconstructed/particles/bow_kinds2.inc` (hooked into particles.c like bow_kinds.inc).

| Kind | Bow (arrow) | Create | Move | Render |
|---|---|---|---|---|
| Flare 0x7f78/5 | 0x12fa (0x47f) | `0x015bea78`: lifetime 60 then 40, gravity rand % 100 / 100 x 5 + 1, velocity x rand % 300 − 150, scale rand % 6 x 0.01 + scale, rotation, angle 0, start = position | `0x0162d786`: t = (life + velocity x) x 0.1; x = sin t x 40 + start x, y = start y − cos t x 40, z − gravity, scale − 0.002, start x + 2.5; at life ≤ 20 light / 1.1 | plain sprite, none at lifetime 60 (`0x01598426`) |
| Smoke_line 0x83b3/1 | 0x1320, 0x1323 | `0x015cfe72`: life 20, alpha 1, rotation, initial scale | `0x0164316e`: s = 1 / initial life; scale + s, light − s | plain sprite (its 0x83b3/6 sibling takes light x alpha) |
| Spark04 0x8155/2 | 0x1320, 0x1323 | `0x0160b267`: Spark03/0x1e's body with scale rand % 5 / 10 + 0.2 | `0x01683a73`: Spark03/0x1e's move | light x alpha (`0x015a5aa0`); its create never sets alpha |
| smoke01 0x7f5a/0x18, 0x4e | 0x12fe, 0x130e | `0x015c6bcd`: life 32, scale (rand % 32 + 48) x 0.01 x scale + scale, angle x rand % 360, rotation (int)WorldTime % 360 | 0x18 `0x01636a33`: light l x (0.2, 0.5, 0.35), gravity + 0.1, rise, scale + 0.05; 0x4e `0x0163e3c9`: l x (0.05, 0.25, 0.6), rotation + 0.05, gravity − 0.1, x + sin(WorldTime) x gravity x 0.05, scale + 0.15 | plain sprite |
| smoke01 0x7f5a/0x7a | 0x131e | `0x015cb8ee`: as 0x18 with the colour kept at +0x7c | `0x0163e5d1`: light − colour / initial life, gravity + 0.1, rise, scale + 0.05, alpha = life / initial, z + 5 | plain sprite |
| firehik03 0x8085/0x11 | 0x1302 (0x45d) | `0x015da370`: life 10, initial scale = scale, rotation = rand() | `0x0164dbf6`: light (a x 0.8, a x 0.9, a); a dead or NULL owner (OBJECT +0x00 through `0x0095f977`) ends it (live 0, life 0); else it moves frame time x 300 along `0x0185c113`((0, −1, 0), angle) | plain sprite |
| pin_star02_pupple 0x810c/0 | 0x131e | `0x0160844b`: life 50, velocity rand_range(−1, 1, 10) each, rotation rand_range(0, 360) | `0x01681c64`: at life ≤ 30 a sin/cos/sin jitter and velocity x 0.9; light / 1.005; rotation + rand_range(−10, 10); MovePosition(position, −angle, velocity); scale − initial / initial life; life = (int)(life − 0.1); dies at life ≤ 0 or scale ≤ 0 | plain sprite |
| Snow_Chip02_red 0x83b8/2 | 0x1326 | `0x015e30d4`: life 20, alpha 1, a sideways jump rotate((a, 0, b), angle), rotation, velocity (rr(−3,3), rr(−3,3), rr(−0,6)) evaluated z first | `0x01657383`: scale and alpha = life / initial; rotation ±3 by life % 8 < 4 | plain sprite |
| firehik01 0x8084/0x1e | 0x1326 | `0x015d6c25`: life 10, rotation, alpha 1, velocity rotate((0, −7, 0), angle) | `0x0164a207`: scale − initial / 10, alpha = life / initial, position + velocity | light x alpha (`0x015a4461`) |
| flare_mono 0x8184/1 | 0x12ff | `0x015f960a`: life 40, velocity rand % 4 − 2 each | `0x01672543`: scale + 0.01 above life 20, else − 0.011 | plain sprite |
| lighting_mega01..03 0x8081..0x8083/0 | 0x130c | `0x015d2e4c`: life 5, rotation, gravity 0, alpha 1, the light kept at +0x7c and set to 0 | `0x01644e1d`: alpha − 0.15, dies below 0.1, light = colour x alpha | plain sprite |
| smoke01 0x7f5a/0x6d | 0x1304 (0x45e, render time) | `0x015cad8d`: life 10, rotation | `0x0163c877`: light (0.3, 0.4, 0.5) x life / initial; with an owner and life ≠ 0, CreateParticle(0x7f5a, halfway to the owner's +0x158, angle, (0.3, 0.4, 0.5), 0x6d, rand % 8 x 0.07 + 0.8, NULL) | plain sprite |
| pin_star 0x8108/3 | 0x1304 (render time) | `0x015f696e`: life 10, rotation | `0x0166e3b9`: scale + 0.01, light min(life / initial, 1), position + 2.5 x AngleToVector((0, 0, rotation)) normalised again | plain sprite (`0x0159c043`) |

Bitmaps (static, LoadBitmap 0x0185baac): pin_star02_pupple 0x810c (`0x0182e275`, LINEAR/CLAMP), Snow_Chip02_red
0x83b8 (`0x0183863c`, LINEAR/REPEAT); the others were already in the world table.

## The bows' effects (verified)

`reconstructed/combat/bow_fx.inc`, hooked into skill_fx.c like pet_fx.inc. RenderEffects draws all of them through
its default case (`0x015324cf`, a plain RenderObject; jump tables `0x153254a`/`0x15325ae` and `0x153271e`/`0x15327ee`).

| Effect | Model (AccessModel) | Create | Move |
|---|---|---|---|
| 0x477/3, /4 (0x45b, 0x47f, 0x60d) | Data\Skill\m_Waves (`0x01833c1e`) | `0x013d9444`: life 20, gravity 0.1, blend mesh −2, angle 0, impact = position, z + 50; subtypes 2..4 (`0x013d97f4`): life 15, key −1, scale = (int16)info key x 0.05, gravity 0.01, z − 50, pitch 90, yaw = the angle argument's | `0x014719f8` / `0x01471ac0`: scale + gravity, gravity + 0.005 / 0.002, capped at 1.5 / 2.5, blend light / 1.3 / 1.2, yaw + 45 |
| 0x60b/0 (0x60a) | Data\Effect\Darkangel_effect (`0x018370f6`) | `0x014001e3`: life 10, scale 2, blend mesh 0 | `0x01468a1f`: without its model nothing; scale + 0.6, yaw + 30, blend light / 1.3, below 0.2 it is 0 and SetLive(0) |
| 0x611/0 (0x610) | Data\Effect\ringofpower (`0x0183721f`) | `0x0140fea0`: life 10, +0x70 10, scale = the argument itself, pitch −90 | `0x014c4c8e`: scale + 0.25, alpha = life / 10 |
| 0x45f/0, /1 (0x45c) | Data\Skill\darkwing_hetachi (`0x01833729`) | `0x013e45bc`: position ± 40 per axis, direction = VectorNormalize(old − new), (int)((rand % 10 − 5) x 0.08) (always 0) added, scale ± 30 %, life rand % 20 + 20, alpha rand % 10 x 0.02 + 0.6, gravity 0.1, random angles, spin rand % 10 − 5 | `0x01488ec6` / `0x0148922a`: light and alpha x 0.97 (subtype 1 scale x 0.99), angle + spin |

The info key the arrows pass for 0x477 is 0, so the ring starts at scale 0 and grows by its gravity.

## RenderEffects' case 0x45e (verified)

`0x01518f49` (absolute_gunbow_arrow, bow 0x1304), each drawn frame when the model exists: model colour (1, 1, 1),
the animation tick `0x012b4dd3` at twice the record's speed, RenderObject, then CreateParticle(0x7f5a, position,
angle, (0.3, 0.4, 0.5), 0x6d, s, this effect) and CreateParticle(0x8108, ..., (1, 1, 1), 3, s x 0.1, this effect)
with s = rand % 8 x 0.07 + 0.8. Subtypes 3..7 lay the terrain decal 0x8002 (RenderTerrainAlphaBitmap
`0x016cdd5f`); every other subtype draws the model a second time with the same arguments (subtypes 9 and 0xb only
at lifetime ≤ 0x45). Arrows have subtypes 0, 2 and 0x63, so they draw twice and never lay the decal.
`mu_sfx_arrow_render_extras` (arrow_fx.inc) returns the tick speed, the decal flag and the draw count; natively
`mu_combat_draw_models` ticks, draws twice and creates the two particles owned by the arrow (its effect OBJECT,
`MU_WORLD_FX_COMBAT_BASE`); the decal is only counted.

## The functor tick (verified tick, native placement)

The 0x613..0x617 render-registry functors tick the animation inside the draw (RENDER-EFFECTS-010). The native now
ticks there too (`mu_combat_draw_models`), once per drawn frame, instead of once per logic step. Headless runs draw
only the saved frames (`--every`), so the arrows' frame advance follows the drawn frames, as in the client.
Measured: of the 33 bow scenes only 0x1323, 0x1329 and 0x132f change (their frame 20; their arrow models animate);
the other 30 bows and all non-bow scenes are byte-identical.

## Effect 0x70c (verified, validator only)

The ground skills' landing mark (RENDER-EFFECTS-010's ground test creates it):

- **Create** `0x0141a4c4`: life 50, +0x70 20, scale 0, +0xd8 0, angle 0, light 1; then CreateEffect 0x704
  ((0.75, 0.75, 1), 0.5), 0x703 ((0.8, 0.4, 1), 0.25), 0x705 ((0.7, 0.7, 1), 0.25), 0x705/1 ((0.2, 0.9, 0.9),
  0.125), 0x705/3 (1, 0.25), 0x706 (1, 0.13), all without owner and key −1, then twice 0x419 + rand % 2 (stones,
  light (1, 0, 0), subtype 0x13, yaw rand_range(0, 360)); its own yaw rand_range(0, 360).
- **Move** `0x014d2131`: scale + 1 / 20, alpha − 1 / 20, +0xd8 = pow(1 − |20 − 2 (life − 30)| / 20, 2) (a pulse
  peaking at life 40), light − 0.04 below life 25.

The native session still fires none of the ground skills, and 0x703..0x706 are not reconstructed, so 0x70c is
reached only by the validator.

**The owner flag +0x64.** The only writer found is the set at `0x014ecaab`. CreateCharacter `0x0137d8a1` and its
direct OBJECT initialisers (`0x0129f4a5`, `0x0129dc61`, `0x0129f484`, `0x0129de3a`, `0x01295f18`, `0x0129dcda`,
`0x00aa0fdd`) write no +0x64; a byte-pattern sweep of the effect code (0x01300000..0x01600000) finds only effect-record
writes. The world-object loaders clear an OBJECT's +0x64 at creation (client-character-select.md, client-worlds-q.md),
so the flag most likely resets only when the owner's OBJECT is created again (inference). The native keeps one flag
per owner for the session.

## The spark bone (live read)

2026-11-04 14:18, the free-runtime client, Nighty on MTM-1 in Lorencia (world 0 read back): the hero pointer
`[0x0a39d754]` = 0x19c7aae4 and the byte at +0x9c4d = **0** (the 32 bytes around it are 0; a second read 13 s later
gave the same). RENDER-EFFECTS-009's `MU_COMBAT_SPARK_BONE` 0 is therefore the live value for this state. The byte
belongs to another CharactersClient slot, so a crowded scene could hold data there (limit).

## Measurements

Installed data, Lorencia 182,128, Triple Shot at a spider placed at 186,128, 30 frames, every fifth drawn; base =
this branch before the change (RENDER-EFFECTS-010's code, equal to main `26b9ef07` for these files).

| Scene | Unsupported requests | Notes |
|---|---|---|
| 33 bows (one per arrow type), arrows 119 = 119 | **598 → 77** | the rest: 14 joint kinds (66) and effect 0x38b5/1 (11) |
| 0x12fa / 0x12fc / 0x12fd | 71 → 3, 35 → 4, 30 → 4 | flares, rings, feathers |
| 0x12fe / 0x12ff / 0x1302 | 31 → 0, 19 → 4, 31 → 0 | smoke, flare_mono, firehik03 |
| 0x1305 / 0x130a / 0x130c / 0x130e | 35 → 4, 15 → 4, 35 → 4, 46 → 15 | burst, ring, lighting_mega, smoke |
| 0x131e / 0x1320 / 0x1323 / 0x1326 | 83 → 4, 32 → 0, 42 → 0, 62 → 0 | |
| 0x1304 (0x45e) | 4 → 4 | 0 → 20 particles at render time (its 0x80e3/4 joint remains) |
| 0x1323 / 0x1329 / 0x132f | unchanged | frame 20 differs: the functor tick per drawn frame |

(RENDER-EFFECTS-010 counted 553 with its own scene; the kinds listed are the same.)

## Compiled planted mistakes

75 mutants on bow_kinds2.inc, particles.c, bow_fx.inc and arrow_fx.inc; each is compiled separately and caught.
Two first candidates were equivalent and replaced: a normalise threshold that needs an exactly zero scatter, and the
0x6d trail's `life ≠ 0` test (a record at life 0 never reaches the move: the loop head erases it).

## Limits

- **The bows' joints** (66 requests): 0x7f78/0xb, 0x80e3/4, 5, 0x80e4/1, 0x7f79/0xc, 0xe, 0xf, 0x12, 0x16,
  0x814c/0xa, 0x8182/0xa, 0x8185/0xa, 0x828c/2, 0x85cc/0. Their CreateJoint/MoveJoints bodies are traced
  (handoff) but not reconstructed; the combat bitmap table (16/16) has no room for their bitmaps yet.
- **0x38b5/1** (0x60f, 11 requests): CreateEffect runs the shared arrow body for it (multishot02, a model above
  0x7a4 that the native draw skips); not reconstructed.
- **Spark04/2's alpha** is never written by its create; the client's record is value-initialised (0 natively), so
  it draws black under additive blending (inference from the missing write).
- **0x70c's children** 0x703..0x706 and the stones' subtype 0x13 are not reconstructed; no native route fires the
  ground skills.
- **Uruk's keyed effect 0x806e/12** stays refused: it fires only with the weather input, which is off by default
  and has no capture (RENDER-WORLDS-M). **The Muun table** has no native Muun owners.
- **The decal 0x8002** of 0x45e subtypes 3..7 is counted, not drawn (no arrow has those subtypes).
- **The model colour** RenderEffects sets for 0x45e ((1, 1, 1) at +0x54) is not applied natively (the native colour is
  the record's light).
