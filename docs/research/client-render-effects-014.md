# The last two bow joints, 0x70c's rings and the landing-sound flag

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
This continues [013](client-render-effects-013.md). No live client session was needed: the static
reading answered every question about bow 0x12f7's effect that this lane could check natively.

## Recovered contracts (verified)

Every row below is compared with the pinned instructions under Unicorn by `scripts/validate_render_effects14.py`.

| Kind | Original code | Contract |
|---|---|---|
| joint 0x7f78/b (arrow 0x459, bow 0x12f7) | create `0x015496cb` → `0x0154b471`; move `0x01579b40..0x0157ab78`, `0x0157c24e` | Create: life 30, 15 tails, width 30, light (0.2, 0.2, 1), +0xa20 = 0, jitter x = rand % 3000, target point = argument, no speed. Move: a null owner goes straight to the closing tail; a dead owner clears live and sets life −1. Otherwise c = index·0xd1e3 ± [0x0bdc5eb0] (the sign by the pool ordinal's parity). A direction from sin/cos of (c + 0xd903)·0.072, c·0.09195, (c + 0x2b67)·0.16695. q = life·40/30, blend = (q < 20 ? 4q : q + 60)/(+0xa20 + 30)·30. Sound 0x42 at life 30. Head = target point + direction·min(5·max(q − 10, 0), 150), then per axis (blend·head + (100 − blend)(owner +0x110 + 25 cos((index·0xc81f + k·0xe7f + c/10)·0.01)))·0.01. The joint with skill 1 writes the owner's +0x158 and calls CheckClientArrow `0x013bd374(owner)`. Then Shiny02 0x7f67 (scale (rand % 2 + 8)·0.1) and two flare01 0x7ef7 (·0.18) sprites on the owner, light (0.3, 0.3, 0.5), rotation rand % 360. Subtype b skips the last-ten-steps fade (`0x0157c24e`: subtypes 5, 7 and b). |
| joint 0x7f79/e (arrow 0x45a, bow 0x12fb) | create jump table `0x015539d0`[0xe] = `0x0154ce29`; move `0x0157d379..0x0157d548` | Create: as /f but light (1, 1, 1), 16 tails, speed 70. Move while live with a live owner: a Spark03 0x7f26 sprite (scale 5, the joint's light, no owner, blend 0, axes 4). Then smoke01 0x7f5a 0x22 and 0x23 (scale 1), and Spark03 0x7f26 0xa (scale 4) with light (0.7, 0.3, 0.3). The light is then (1, 1, 0.2). /f's fade and terrain light follow. |
| particle smoke01 0x7f5a/0x22, /0x23 | create `0x015c5390`; move `0x01636d78` / `0x01636c98` | The passed light is replaced by (1, 0.2, 0.2); life 30, rotation rand % 360; 0x23 moves (0, −5, 0) per step. Each step: light / 1.04, scale + 0.06. |
| particle Spark03 0x7f26/0xa | create `0x015de10a` (table `0x016166cc`, index subtype − 1); move `0x01651a45` | Alpha 1, velocity (rand % 8 − 4, 0, rand % 8 − 4), life 20, scale rand % 5 / 10 + 1. Each step: light / 1.08, scale − 0.03, alpha − 0.001, dies at alpha ≤ 0. |
| effects 0x703, 0x704, 0x705/0, /1 (0x70c's rings) | create `0x01419f69`, `0x01419fa0`, `0x0141a016`; move `0x014d09e8`, `0x014d0a48`, `0x014d2253` | Life and +0x70 20, +0xa4 = scale argument, scale 0; 0x704 also yaw +0x168 = rand_range(0, 360). Each step: scale + (+0xa4)/(+0x70), alpha − 1/(+0x70). |
| effects 0x705/3, 0x706 | create `0x0141a131`, `0x0141a168`; move `0x014d2898`, `0x014d0aa8` | Life 20, scale = argument, alpha 0. Each step: alpha = pow(1 − abs(+0x70 − 2·life)/(+0x70), 2); 0x706 also +0xb0 = (life % 4)·0.25. |
| stones 0x419/0x41a subtype 0x13 | create table `0x0142c6d1`[0x13] = `0x013d5665`; move table `0x0150db19`[0x13] = `0x0145bf6a` | Subtype 0's fling and bounce, except that the one-in-ten particle is 0x7f40 (subtype rand % 3 + 1) with light (0.3, 0.3, 0.3). |

The four ring models are `Data\Effect\min_elf_skill_ring04..07` (AccessModel `0x01827299..0x01827354`, textures
`Effect\`). RenderEffects draws 0x703..0x706 and the stones through its default RenderObject. Its byte table
`0x01532ab2` / jump table `0x01532a26` sends them to `0x015324cf`. 0x70a and 0x70c have their own render cases,
`0x0152dc88` and `0x0152e296`, not reconstructed.

## The owner flag +0x64 (verified)

013 left the landing sound's one-play rule "unverified" because only the set at `0x014ecaab` was known. A sweep of
every `[reg + 0x64]` write whose base comes from an effect's owner (+0x34c) finds the rest. Effect 0x40a uses the
same dword as a step counter:

- CreateEffect 0x40a (jump table at `0x013c15e9`, index 0x11; case `0x013ff507`): with a live owner, subtypes 0
  and 1 clear owner +0x64 (`0x013ff56c`, `0x013ff5b8`) and set the owner's alpha +0xdc to 0 or 1; life 70.
  Subtype 2 and a null or dead owner leave it.
- MoveEffect 0x40a (`0x014ecef7` → `0x014f718d`): alpha = life/(+0x70) (inverted for subtype ≠ 0), copied to
  the owner, and owner +0x64 += 1 every step (`0x014f7225..0x014f7232`). A null or dead owner ends the effect.
- 0x40a is created with the character as owner at `0x00e2b2a9` (subtype 1, in `0x00e2b118`) and by two receive
  handlers, `0x01219e9d` in `0x01219a94` and `0x01220b88` in `0x0121e006` (subtype 0). It is the owner fade.

So a ground skill plays 0x55e once per owner until that owner's next 0x40a fade starts. While a fade runs, the
counter is non-zero and the landing stays silent. The validator executes CreateEffect and MoveEffect for 0x40a and
compares the flag with this rule. The native session creates no 0x40a, so keeping one flag per owner for the
session is now the verified behaviour for that session, not an inference.

## Native routes

- `mu_jt_object` gains +0x110 (the arrow's ring point). `effect_object` copies it. The joint reports the
  write-back and arrow check as `MU_JT_CALL_CHECK_ARROW` with the head position. `mu_combat` writes the arrow
  effect's position, runs its existing `check_arrow` and refreshes the arrow's object view at once. Later joints in
  the same MoveJoints pass therefore see the new state, as in the client.
- MoveJoints reads `ambient_clock` = the combat step counter (one per logic step, like `[0x0bdc5eb0]`).
- The combat bitmap table loads `Effect\Flare.jpg` (0x7f78; 24 → 25 slots). Sprite and particle bitmaps
  (Shiny02, flare01, Spark03, smoke01) were already registered; the world particle table is unchanged.
- Sound 0x42 is reported as `MU_JT_CALL_SOUND` and reaches the existing effect-sound route. That route attributes
  no call site, so it is not played. All effect sounds except 0x582 behave the same way.
- The ground skills 0x7fc / 0x7fd (2044 / 2045) are an offline fixture in `mu_combat_cast`. Like the receive
  handler `0x0125f53d..0x0125f5d9`, they create 0x70a (subtype 1 / 0, the hero as owner, its key, scale 1). For
  0x7fc they also call CreateArrows(c, o, 0, 0x7fc, 1, 0). SetAction `0x012b001a(c, skill, 0x107, -1)` and the
  request are not modelled.

## Still open

- **0x70a (the ground skills' rain):** create `0x01418f78` (vector-class code); move `0x014d1a18..0x014d2131`
  (subtype 1: the pulse alpha, +0xd8 = 10 − life below 11). It looks up the caster by key (`0x0137c724`,
  `0x0095f6db`, `0x009a13f4`) and stops for none or +0x23 set. It moves by rand_range offsets (`0x011ff622`,
  bounds `0x01a9a3b4`/`0x01a7dec8`) to ground + 0x01a7e94c, aims through `0x012af5cb`, and fires
  CreateArrow(c, this effect, 0, 0x7e7, 0x7e7, 0x7e7, 0) at three sites (`0x014d1cc6`, `0x014d1f20`,
  `0x014d20cb`). Render case `0x0152dc88`. Only those 0x7e7 arrows reach the ground test, so natively
  0x70c, its rings and its stones appear only once 0x70a exists. 0x7fc's own arrows fly at bow height and hit or
  pass. The fixture counts 0x70a as one unsupported request.
- **0x70c's render** (`0x0152e296`) and native loading of the four ring models: not needed until 0x70a fires.
- **0x45e decal, subtypes 3..7:** after EnableAlphaBlend, RenderTerrainAlphaBitmap `0x016cdd5f`(0x8002
  `Effect\PoundingBall.jpg`, x, y, 2, 2, (0.3, 0.3, 0.3), WorldTime, 1, 5, 1, 0) (`0x0151919b..0x0151927f`). No
  arrow is created with these subtypes, so no scene can show it. A native draw needs the bitmap and the terrain
  decal adapter of `mu_world_helpers.c` in the combat renderer.
- **Uruk:** unchanged from 013. Keyed 0x806e/12 still needs a world-100 population/globals capture including
  weather `0x01cf15ec`, and a native feed for that value.
- **Muun:** unchanged from 013. The `0x0114203d` consumer still needs a Muun owner fixture/capture with OBJECT
  ownership, type, lifetime and posed bone transforms.
- **Live look:** not taken. The static contract fixes 0x12f7's flares (blue sprites around the arrow's moving ring
  point, the arrow carried by the skill-1 joint). A live capture would compare pixels, not behaviour.

The exact counts and wall times are in the [handoff](../handoffs/RENDER-EFFECTS-014.md).
