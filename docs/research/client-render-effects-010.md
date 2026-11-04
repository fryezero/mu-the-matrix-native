# The pets' particle kinds, arrows 0x615/0x617's kinds and glow, the arc and ground arrow paths, the bows' kinds

RENDER-EFFECTS-010 continues RENDER-EFFECTS-009's "Remaining":

- the six pet particle kinds that RENDER-EFFECTS-007 traced (Clud64, firehik03, Impack01/1, firehik_mono ×3);
- arrows 0x615 / 0x617's particle kinds (0x8081..0x8083/8, 0x85fb/2, 0x8450/4);
- why 0x615 / 0x617 drew as dark meshes: the client draws 0x613..0x617 through render-registry functors;
- RENDER-EFFECTS-007's arrow paths: the arc skill 0x2d8 and the ground test of skills 0x7e7/0x7fc/0x7fd;
- the most requested particle kinds of the other bows.

[Handoff](../handoffs/RENDER-EFFECTS-010.md).

## Identity and method

Same pinned target as client-render-effects-004/-007/-009 (executable SHA-256 `3cf91f3c…5527a`, capture09 text
`2bd5f2e9…3724` at 0x00401000, run10 image data `c985e2e6…a0672f`).

"Verified" means authored compiled C compared with the original instructions under Unicorn by
`scripts/validate_render_effects10.py`, which reuses validate_particles' create/move/render families,
validate_render_effects7/9's effect harness and its own functor family. The bodies were found by per-kind Unicorn
block traces (the blocks a kind executes that a reference kind does not) and read statically. "Static" marks
readings that were not executed; "inference" marks native choices the client does not decide.

| Family | Original bodies | Cases (`--cases 20`) | Mismatches |
|---|---|---:|---:|
| Pet kinds create / move / render (7 kinds with 0x7efa/2) | below | 140 each | 0 |
| Arrow kinds 0x8081..0x8083/8, 0x85fb/2, 0x8450/4 | below | 100 each | 0 |
| Bow kinds 0x7fcd/1, 0x7f73..0x7f75/0, 0x7f5a/0x86, 0x810a/0x24, 0x810a/0xe, 0x7f26/0x1e | below | 160 each | 0 |
| Render-registry functors of 0x613..0x617 | `0x00a4269f`, `0x00a42984`, `0x00a42b8c`, `0x00a42f55`, `0x00a43160` | 100 | 0 |
| CreateEffect, arc skill 0x2d8 (33 arrow types × 0/2) | `0x013cd5b6..0x013cd66f` | 120 | 0 |
| MoveEffect, skills 0x2d8 / 0x7e7 / 0x7fc / 0x7fd (33 arrow types) | `0x014eca00..0x014ecb6e`, Arrow01 `0x01464b8f` | 120 | 0 |

**Totals:** 1,540 original-instruction cases, zero mismatches; 54/54 compiled mutants caught (recorded run 63 s).
The gate's run (`--cases 2`) gives 154 cases and 54/54.

## The pets' particle kinds (verified)

| Kind | Pet | Create | Move | Render |
|---|---|---|---|---|
| Clud64 0x7ffd/0xb | Demon, five bones | `0x015c1930`: three in four drawn with smoke01 (rand % 4), life 30, scale = argument, rotation rand % 360, ±10 jitter, gravity −1.5 | `0x016305fa`: light = life/10, gravity −0.01, z −= gravity, scale −0.03, alpha −0.05 | subtractive (`0x0184aab7`), plain sprite |
| firehik03 0x8085/1 | Demon, bone 0x2c | `0x015d9074`: life rand % 5 + 34, scale (rand % 72 + 72)·0.01·scale, gravity (rand % 24 + 74)·0.1, alpha 0, colour saved at +0x7c, light 0 | `0x0164b824`: below 15 steps alpha −0.2, else +(rand % 2 + 2)/10 up to 1; dies below 0.1; light = colour·alpha; shrinks (rand % 2 + 6)/100 or dies; rises by gravity; spins 3 | plain sprite |
| Impack01 0x7efa/1 | Panda, bone 7 | 0x7efa/2's body (`0x015c336e`), start[0] = 0.1 | `0x016329a3`: scale = sin(life·2°) | **no sprite**: the subtype table `0x015ae4bf` sends 1 and 2 past it |
| firehik_mono 0x8086/4, 0x8087/8, 0x8089/5 | Skeleton (owner = the pet) | one body (`0x015d474d` by table `0x01616648`, `0x015b95cc`, `0x015d980f`): life 8, scale (rand % 42 + 12)·0.01·scale, gravity (rand % 14 + 44)·0.1, colour saved, start = owner +0x158 | `0x0164723f` / `0x016267a6` / `0x0164c42b`: fade below 5 steps (0x8089: 4) by 0.1, grows (rand % 3 + 8)/100 (+(10 − life)·0.02 below 3), pushed 8 along the angle's −y, then − its former and + its owner's new +0x158 (it follows the pet), spins 5 | plain sprite |

A NULL owner faults in the firehik_mono create and move; the native skips the follow then (inference).

## Arrows 0x615 / 0x617's particle kinds (verified)

- **0x8081..0x8083/8** (0x615's sparks; one body: create `0x015d377c` by table `0x01616620`, move `0x01645975`,
  render `0x0159feab`): life and initial life 5, scale = argument (kept at +0x1c), rotation rand % 360, alpha 1;
  alpha = life / initial, scale −0.018; the sprite's light × alpha.
- **0x85fb/2 and 0x8450/4** (0x617's trails, create `0x01613d5d` / `0x0160fc08`): life 20, the angle argument
  becomes the velocity × `0x011ff622(7, 10, 10)` and the angle is cleared; alpha = life / 20, scale + initial
  scale·0.4 (0x85fb) or ·0.2 (0x8450); light × alpha, 0x8450 subtractive (`0x015a86ac`).
- Bitmaps (static, LoadBitmap): lighting_mega01..03 (`0x01821acf..`, LINEAR/REPEAT), aura_0316_mono (`0x018267da`),
  Wind_smoke (`0x01838af0`).

## Why 0x613..0x617 drew dark: the render registry (verified)

RenderObject's draw `0x017edf43` hands an object type to its render-registry functor before RenderBody
(client-helper-visuals.md). Start-up registers these arrows (`0x00a16273(type, functor)` at
`0x00a13aeb..0x00a13b2f`, static):

| Type | Functor | Passes (RenderMeshDefault `0x00966e4a`: mesh, flags, select; model colour) |
|---|---|---|
| 0x613 8cha_arrow | `0x00a4269f` | 0..3 flags 2, select = mesh (highlight), colours (0.4, 1, 0.7) / (0.4, 0.5, 1) |
| 0x614 apocalypse_arrow | `0x00a42984` | 0 (select 0), 1 (select −1), 2 (select 2, colour (1, 0.15, 0.2)); tick speed 0.003 |
| 0x615 lightning_arrow | `0x00a42b8c` | mesh 1 plain, mesh 1 chrome-additive 0x44 (0.5, 0.4, 1), mesh 0 additive 0x42 with BlendMesh, mesh 2 elec_light additive on `Item\texture\elec_light.jpg` 0x8551 (a 6-cell strip, cell = (int)WorldTime % 150 / 25), mesh 3 additive (0.25, 0.45, 1) |
| 0x616 TempleGuard_bow_arrow | `0x00a42f55` | meshes 0, 2, 1 additive 0x42, mesh 1 in (0.3, 0.7, 1) |
| 0x617 Imperial_arrow | `0x00a43160` | mesh 2 plain with BlendMesh, mesh 2 chrome (flags 6, (0.6, 0.6, 0.8)), meshes 5, 4, 0, 1, 3 additive 0x42 in their own colours |

Each functor first ticks the animation (`0x012b4dd3`, speed +0xbc; SetAction(o, 0) `0x012affa4` when it answers 0),
saves the model colour +0x54, sets it before each pass, restores it, and returns 1 (no RenderBody). The glow meshes
(elec_light, gsw_line, force_Pillar, alpha_light2) carry no `_R` texture script, so RenderBody with BlendMesh −1
drew them opaque: dark cards. Natively `mu_combat_draw_models` draws the passes (`mu_sfx_arrow_render_passes`) mesh
by mesh; the tick runs once per logic step (the client ticks per drawn frame; inference).

## The arc skill 0x2d8 (verified)

- **Create** (`0x013cd5b6`, the end of the shared arrow body, every arrow type): life 40, direction y
  −(rand % 80 + 45), angle x −(rand % 60 + 32), gravity (rand % 80 + 1)·0.1 + 26. RENDER-EFFECTS-007 refused it.
- **Arrow01's move** (`0x01464b8f`, subtypes 3/4 or skill 0x2d8): pitch + gravity up to 50; unless the tile's
  TerrainWall word has bit 8 (TERRAIN_INDEX `0x016d34db`), a ground below z lifts it to ground + 10 and stops it;
  Fire01/5 particle; **no hit check**. The other 32 arrow types move as before with this skill.

## The ground skills 0x7e7 / 0x7fc / 0x7fd (verified)

MoveEffect's tail `0x014eca00` (any record of these skills, i.e. their arrows): with h = RequestTerrainHeight at the
position,

- h + 20 > z: when the owner OBJECT's +0x64 is 0 it plays 0x55e and sets it to 1; CreateEffect(0x70c) at
  (x, y, h) with the record's angle and the prologue light (key 0xffff, no owner); SetLive(o, 0);
- z > h + 600: SetLive(o, 0).

A NULL owner faults. The client's clearing site of +0x64 was not found (only this set, `0x014ecaab`); the native keeps
one flag per owner for the session (inference). The native session fires none of these skills (0 skills cast with
`--combat-script 2:skill:728|2023|2044`), so these paths are reached only by the validator; effect 0x70c is not
reconstructed.

## The other bows' kinds (verified)

| Kind | Arrow | Create | Move | Render |
|---|---|---|---|---|
| drop01 0x7fcd/1 | ArrowWing 0x443, ArrowBomb 0x442 | subtype 0's body | `0x0162284b`: next cell, jitter (rand % 30 − 15)·scale, rise (rand % 20 + 10)·0.3·scale, +0.002 | the drop sheet |
| flower1..3 0x7f73..0x7f75/0 | ArrowNature 0x441 | `0x015b5a9d`: life rand % 10 + 15, scale (rand % 8 + 4)·0.03, velocity ((rand % 32 − 16), (rand % 32 − 16), (rand % 32 − 32))·0.1 | `0x0161dd24`: while frame 0, velocity jitter ±1.6 and fly; below the ground it rests (frame 1); spins rand % 16 | plain sprite |
| smoke01 0x7f5a/0x86 | 0x616 | life 20, rotation | alpha = life/20, +0.04 | light × alpha |
| pin_star03 0x810a/0x24 | 0x616 | `0x015b4d61`: life 20, spin rate ±2 at +0x84, angle z −180, not moving, velocity = 10·AngleToVector(angle) (`0x00d015d5`, VectorNormalize `0x00cff0d3` divides) + 3 jitters | spins, flies, alpha and size by life | light × alpha |
| pin_star03 0x810a/0xe | 0x613 | life 25, scale `0x011ff622(0.5, 1, 100)`·scale | fades over the last half, shrinks, −10° a step, velocity jitter | light × alpha |
| Spark03 0x7f26/0x1e | gamble_arrows01 0x525 | life rand % 5 + 50, scale rand % 10/10 + 0.2, velocity rand % 5 − 2, gravity 0.5 | at 45 steps and below a sin/cos wander; light /1.05; −0.01; a second life step | plain sprite |

Bitmaps: pin_star03 (`0x0182d4b5`, LINEAR/CLAMP), `Skill\flower1..3.tga` (`0x01834adb..`, NEAREST/CLAMP).

## Measurements

Installed data, Lorencia 182,128 (Triple Shot at the spider, 30 frames) and 133,127 (pets, 40 frames); base = main
`5cb6fa6d`, built once.

| Scene | Unsupported requests | Notes |
|---|---|---|
| 33 bows (one per arrow type) | **1,561 → 553** | arrows 119 = 119 |
| bow 0x1329 (0x615) | 280 → 0 | glowing blue arrows instead of dark cards |
| bow 0x132f (0x617) | 56 → 0 | additive purple glows instead of black cards |
| bow 0x132c (0x616) | 284 → 4 | 0x85cc/0 joint remains |
| bows 0x12ec / 0x12f3 / 0x12f4 | 84 → 0 each | leaves, drops |
| bows 0x12fe / 0x130e / 0x1323 | 84 → 28, 72 → 44, 94 → 38 | |
| pet demon | 18 → 0 | 18 particles created; its subtractive clouds draw |
| pet panda / PC panda | 1 → 0 | Impack01 sets its blend state only |
| skeleton pet on a dying demo player | 4 → 0 | the flames follow the pet |
| 10 other combat scenes, other bows' and pets' scenes | unchanged | byte-identical PNGs (37 scenes) |

**DATA-ACQ-002 tours** (32 captures, default draw, base against the branch): 128/128 PNGs, 64/64 OBJECT/light dumps,
33 JSON and 32 logs byte-identical; the 32 frame reports differ only in the particle summary's `bitmaps` list
(62 → 72 slots, intended).

## Compiled planted mistakes

54 mutants on pet_kinds.inc, arrow_kinds.inc, bow_kinds.inc, world_owned_fx.inc, particles.c, arrow_fx.inc and
skill_fx.c; each is compiled separately and caught (recorded run, caught/40: from 2 for thresholds the random records
rarely reach, e.g. flame_fade at life 14, to 40). None is equivalent: each changes a value or branch the cases reach.

## Limits

- **The spark bone** stays RENDER-EFFECTS-009's stand-in; no live read was taken.
- **0x45e's render extras** (static, `0x01518f4c`): a tick at twice the speed, particles 0x7f5a/0x6d and 0x8108/3
  every drawn frame, and the 0x8002 decal only for subtypes 3..7 (never an arrow's). Not reconstructed.
- **0x442 with a straight skill** stays refused: the client rotates an unset stack vector there.
- **The ground skills' effect 0x70c** and the owner flag's clearing site; no native route fires 0x2d8/0x7e7/0x7fc/0x7fd.
- **The functor tick** runs per logic step natively (per drawn frame in the client).
- **Remaining bow kinds** (553 requests): 0x477/3, 4, 0x7f78/5, 0x83b3/1, 0x8155/2, 0x7f5a/0x18, 0x4e, 0x7a,
  0x8085/0x11, 0x60b, 0x810c, 0x83b8/2, 0x8084/0x1e, 0x45f/0, 1, 0x611, 0x38b5/1, 0x8184/1, 0x8081..0x8083/0 and the
  joints 0x7f78/0xb, 0x7f79/0xc..0x16, 0x80e3/4, 5, 0x80e4/1, 0x828c/2, 0x814c, 0x8182, 0x8185/0xa, 0x85cc/0.
- The skeleton's flames are drawn (2 in its scene) but too small to show in the sampled frames.
- No live comparison.
