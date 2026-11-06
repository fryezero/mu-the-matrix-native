# The ground skills' rain 0x70a, its rings, RenderEffects' decals and the effect-sound sites

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; pinned text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` (base `0x00401000`), image data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. This continues
[014](client-render-effects-014.md), whose ground-skill fixture fired the skills but could not land 0x70c natively.
No live client session was needed: every question this lane could check natively was answered statically and
compared under Unicorn.

## Where the cases are (static, from the dispatch tables)

| Routine | Table | 0x700 | 0x701 | 0x702 | 0x707 | 0x70a | 0x70c |
|---|---|---|---|---|---|---|---|
| CreateEffect `0x013c0f19` | `0x0142be91`, base 0x628 | `0x0141a21a` | `0x0141a29c` | `0x0141a319` | `0x01419f40` | `0x01418f78` | `0x0141a4c4` |
| MoveEffect `0x0142fd09` | `0x0150d291`, base 0x601 | `0x014d0586` | `0x014d06fc` | `0x014d0872` | `0x014d0b58` | `0x014d1a18` | `0x014d2131` |
| RenderEffects `0x015181fa` | bytes `0x01532ab2` / jumps `0x01532a26`, base 0x6cd | default `0x015324cf` | default | default | default | `0x0152dc88` | `0x0152e296` |

0x700..0x707 are `Data\Effect\min_elf_skill_ring01..08` (AccessModel `0x018271fa..0x0182736d`, textures
`Effect\`). No AccessModel registers 0x70a; MoveEffect's model getter `0x00eaa8cf` then creates an empty model
(types 0..0x3af6), so 0x70a's lifetime runs like any model effect's (21 steps from life 20).

## Recovered contracts (verified)

Every row is compared with the pinned instructions by `scripts/validate_render_effects15.py`.

| Kind | Contract |
|---|---|
| CreateEffect 0x70a (`0x01418f78..0x0141955d`, any subtype) | +0x38 = 1 (not modelled; no reconstructed routine reads it), +0x70 = life = 20, +0xd8 = 0, scale = the argument, light (1, 1, 1). Then, each with no owner and key 0xffff: 0x700/0 at position + (0, 0, 300), light (0.5, 0.65, 1), scale 2.5; two 0x702/0 at + (0, 0, 250), light (0.65, 0.3, 0.7), scales 1.5 and 2; 0x707/0 at the position with the record's light, scale 0.8. The angle becomes (0, 0, 0). Three 0x701/1 at z + 350, + 450, + 550, light (0.8, 0.8, 1), scale 1.8; z is restored. PlayBuffer(0x55d, NULL, 0) at `0x0141953e`; owner flag +0x64 = 0. The lifts are vector sums (`0x00cfca74`): a −0 in x or y becomes +0. |
| MoveEffect 0x70a (`0x014d1a18..0x014d2131`) | alpha = pow(1 − abs(+0x70 − 2·life)/+0x70, 2); +0xd8 = 10 − life once life ≤ 10. The caster: `0x0137c724`(the sign-extended key), `0x0095f6db`, `0x009a13f4`; none, or its +0x23 (dead) set, leaves the case. Position and angle are saved and restored after the shot. Subtype 1 (skill 0x7fc), life > 9: one aimed shot per step (eleven). Other subtypes (0x7fd): life > 15, z = ground + 200, angle (270, rand_range(−10, 10), 180), one shot straight up (five); 9 < life ≤ 15, one aimed shot (six). Aimed shot: dx, dy = rand_range(−200, 200) (`0x011ff622`); position + (dx, dy), z = ground + 500; target = saved position + 2·(dx, dy) at its own height; `0x012af5cb` aims (heading `0x012aed9e`, pitch 360 − heading of (z, ground distance) to (target z, 0)); CreateArrow `0x0158cf57`(caster, this effect, 0, 0x7e7, 0x7e7, 0x7e7, 0). |
| 0x700, 0x701, 0x702 /0 and /1 | Create: +0x70 = life = 25; subtype 0 scale = the argument; subtype 1 +0xa4 = the argument and scale 1 (0x701: 0). Move, subtype 0: SetLive(o, 0) once alpha ≤ 0 (not NaN; the step continues), scale + 0.03 (0x702: + 0.1), alpha − 0.05, z − 3. Subtype 1: scale + (+0xa4)/(+0x70), alpha = the pulse with 2·life as an integer shift, z − 3. |
| 0x707/0 | Create: +0x70 = life = 20, scale = the argument. Move: yaw + 5, alpha = the pulse. |
| RenderEffects 0x70a (`0x0152dc88`) | EnableAlphaBlend, then RenderTerrainAlphaBitmap `0x016cdd5f`(texture, x, y, size, size, light, rotation, alpha 1, height 5, follow 1, flip 0) with L = (0.7, 0.5, 0.4): empact01 0x8070 size 2 and enemy_ring02 0x7f87 size 3, light L·alpha; for life ≤ 10 (d = +0xd8): Shockwave2 0x8147 size 0.5d + 0.5, light L·(1 − 0.1d); Wave 0x824c size 0.2d + 2, L·(1 − 0.15d); empact01 size 0.15d + 2, L·(1 − 0.2d); then lightmarks 0x8078 size 4, light (0.75, 0.75, 0.8)·alpha; DisableAlphaBlend. |
| RenderEffects 0x70c (`0x0152e296`) | EnableAlphaTest(1); Cratered 0x7fe9 size 2.25, the record's light, rotation = yaw, alpha = light red; DisableAlphaBlend; EnableAlphaBlend; for life > 30: pin_star03 0x810a size 1, (0.7, 0.75, 1)·d, Spark04 0x8155 size 1, d, bostar3_R 0x8179 size 2·scale, (0.7, 0.75, 0.85)·alpha, damage01mono 0x8013 size 3.5·scale, (0.7, 0.6, 0.8)·alpha turned by the yaw; DisableAlphaBlend. |
| RenderEffects 0x45e, subtypes 3..7 (`0x0151919b`) | EnableAlphaBlend; PoundingBall 0x8002 size 2, light (0.3, 0.3, 0.3), rotation WorldTime `0x06fce370`. Arrows never use these subtypes; checked with fixture states only. |
| Effect-sound sites | The reconstructed effect and joint routines play six sounds, each at one PlayBuffer `0x00a6ac96` site: 0x582 `0x013c42ee` (CreateEffect, 0x40e's case `0x013c3eab..0x013c4631`), 0x55d `0x0141953e` (CreateEffect 0x70a), 0x97 `0x01451cce` and 0x96 `0x014520f4` (MoveEffect 0x461 `0x01450a73..0x01452410`; the other 0x96 site `0x0148e286` is not in a reconstructed case), 0x55e `0x014eca9a` (MoveEffect's ground test), 0x42 `0x01579fa1` (MoveJoint 0x7f78/b; 014's comment `0x01579f9b` is the case start). Checked against the call bytes, the pushed sound and the case bounds. |

## Native routes

- `bow_fx.inc`: the kinds above; `mu_sfx_effect_render_ops` returns RenderEffects' wrapper and decal calls in client
  order; `mu_sfx_sound_site` gives each sound's site, and `call_sound` passes it in the call's `arg8`.
- `mu_combat`: `MU_SFX_CALL_CASTER` answers for the hero's key unless the hero is dead (character +0x23).
  `MU_SFX_CALL_CREATE_ARROW` runs CreateArrow for the hero's bow from the effect's moved position, owned by the
  rain's effect OBJECT (refreshed before the call, as the arrow's CreateEffect reads it, and after the rain's move).
  The arrows' landing flag is the rain record's own +0x64 (cleared at its creation): the first landing plays 0x55e.
- Models `min_elf_skill_ring01..08` load at session start (the client loads them at startup), so 0x700..0x707 draw
  through the default RenderObject. Eleven decal bitmaps load with GL_CLAMP (`mu_combat_bitmap.wrap`).
- `mu_combat_decal_quads` lays each decal call over the terrain (`mu_terrain_decal`: one quad per tile, height 5
  above it) in the wrapper's blend. The software path and the app's GL part draw them after the effect models and
  before the joints and particles; the GL part clamps their textures.
- The effect-sound route plays a sound when it has a site, from the existing adapter (0x582) or from
  `mu_sfx_sound_site`, with the existing −0.3 dBFS limiter. 0x55d, 0x55e, 0x42, 0x96 and 0x97 now play.

## Still open

- **Fire06 0x7f40, subtypes 1..3:** the one-in-ten particle of 0x70c's stones (014). CreateParticle's case is not
  reconstructed, so the ground scenes count these requests as unsupported (13 to 53 per scene).
- **The crater's alpha test:** 0x70c's Cratered decal is drawn with (SRC_ALPHA, ONE_MINUS_SRC_ALPHA); the alpha
  test of EnableAlphaTest(1) is not modelled for combat quads.
- **Other combat bitmaps' wrap:** the client loads the joint and particle bitmaps GL_CLAMP too; the native keeps
  them REPEAT (unchanged here, so the bow scenes stay byte-identical).
- **+0x38:** 0x70a stores 1 there; no reconstructed routine reads it.
- **Uruk and Muun:** unchanged from 013/014 (weather `0x01cf15ec` capture; Muun owner fixture).
- **Live look:** not taken; the static contracts fixed what the native scenes show.

The exact counts and wall times are in the [handoff](../handoffs/RENDER-EFFECTS-015.md).
