# The stones' Fire06 particle, the crater's alpha test and the combat bitmaps' filter and wrap

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; pinned text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` (base `0x00401000`), image data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. This continues
[015](client-render-effects-015.md), whose ground-skill scenes landed 0x70c natively but left its stones' particle
unsupported, drew the crater without the alpha test, and kept the other combat bitmaps on GL_REPEAT. No live client
session was needed: each question was answered from the instructions and compared under Unicorn.

## Fire06 0x7f40 is Fire01's case (verified)

0x70c's stones 0x419/0x41a subtype 0x13 create Fire06 0x7f40 with subtype `rand % 3 + 1` one step in ten (014,
`0x0145c2b0`). All three particle routines send 0x7f40 to the case of Fire01 0x7f3c, and none of the three tests
the type inside it:

| Routine | Dispatch for 0x7f37..0x7f5d / 0x7f3c.. | Byte for 0x7f40 | Case |
|---|---|---|---|
| CreateParticle `0x015ae7b0` | `sub 0x7f37`; bytes `0x01615f68`, jumps `0x01615f3c` | 1 (as 0x7f3c) | `0x015ba585`, subtype table `0x01616318` |
| MoveParticles `0x01616c80` | `sub 0x7f3c`; bytes `0x0168eee0`, jumps `0x0168eeb4` | 0 (as 0x7f3c) | `0x016282c9`, subtype table `0x0168f278` |
| RenderParticles `0x0159123f` | `sub 0x7f3c`; bytes `0x015ae397`, jumps `0x015ae373` | 0 (as 0x7f3c) | `0x01597855` (subtype tests only) |

Subtypes 1 (`0x015ba6cb`), 2 and 3 (default `0x015bb3c0`) are Fire01's existing reconstruction: lifetime 24, a
fall of 3.2..4.7 (1) or a sway of −1.6..1.5 (2, 3), a random spin; the move grows the scale by the accumulated
gravity and lifts the sprite (`0x016296f0`); the render draws a quarter of the strip by the frame. The native
admits exactly 0x7f40/1..3 (the only subtypes a reconstructed routine creates). Fire06 is loaded at startup by
LoadBitmap `0x018229e5` (`Effect\Fire06.jpg`, index 0x7f40, GL_LINEAR, GL_CLAMP); the world particle table gains
that slot (`MU_WORLD_PT_BITMAPS` 74 → 75, before the two rain textures).

## EnableAlphaTest(1) under the crater (verified)

RenderEffects' case 0x70c (`0x0152e296`) pushes 1 and calls `0x0184a990` before the Cratered decal. The three
wrappers the decal cases use test a cache byte before each GL call:

| Wrapper | Blend (cache `0x0bdc58c4`) | Cull `0x0bdc597f` | Depth mask `0x0bdc5980` | Alpha test `0x0bdc58b5` | Texture `0x0bdc597d` | Fog (flag `0x0bdc597c`) |
|---|---|---|---|---|---|---|
| EnableAlphaBlend `0x0184aa2b` | 3: GL_BLEND, (ONE, ONE) | off | off | off | on | glDisable when the flag is set |
| EnableAlphaTest `0x0184a990`(a) | 2: GL_BLEND, (SRC_ALPHA, ONE_MINUS_SRC_ALPHA) | off | on when the low byte of a is non-zero, else kept | on | on | glEnable when set |
| DisableAlphaBlend `0x0184a7f3` | 0: glDisable(GL_BLEND) | on | on | off | on | glEnable when set |

An enable runs only when its byte is zero, a disable only when it is non-zero (`movzx`, `test`). The alpha function
is GL_GREATER 0.25 (`0x0184b056`). So the crater's fragments are dropped where texel alpha × vertex alpha ≤ 0.25
(its vertex alpha is the record's light red, which fades below life 25), and the crater writes depth 5 units above
the terrain. The flash decals after it (EnableAlphaBlend) write no depth and test no alpha.

## The combat bitmaps' filter and wrap (verified)

Every bitmap the native combat module binds is loaded by one startup LoadBitmap `0x0185baac` call (push wrap,
filter, index, path; the generated table `native/core/mu_item_bitmaps.inc` lists them). The validator decodes each
site:

| Wrap | Bitmaps (call sites) |
|---|---|
| GL_CLAMP 0x2900 | font_damage `0x01820a39`, FontSC `0x01820bb9`, Hit `0x01820a79`, font_miss `0x01820a59`, resist `0x01820a99`, block `0x01820ab9`, parry `0x01820ad9`, absorb `0x01820af9`, Magic_Ground2 `0x01821599`, Fire01 `0x01820f19`, Spark03 `0x01821639`, JointEnergy01 `0x01822425`, JointSpirit01 `0x018223c5`, Spark01 `0x01822385`, JointLaser01 `0x018223e5`, Flare `0x01822545`, sharke_arrows `0x01821dd9`, devil_arrow `0x01833b47`, arrows_angelic `0x01833ba0`, Swordeff_mono2 `0x01837b6c`, and 015's eleven decal bitmaps |
| GL_REPEAT 0x2901 | Thunder01 `0x01822365`, Flare02 `0x018228e5`, force_Pillar `0x01835b52`, !SwordEff `0x01835b72`, Swordeff_mono3 `0x0182f066` |

All are GL_LINEAR except Cratered.tga (`0x01822c65`, GL_NEAREST). The native loaded all but the decals REPEAT and
all LINEAR; it now takes each row's filter and wrap.

What changes on screen: the software raster's GL_CLAMP clamps texture coordinates to [0, 1]; sprites and joint
quads whose coordinates stay inside that range sample the same texels as before. Among the 40 bow and 10 staff
scenes only the joint trails of arrow 0x459 (bows 0x12f7 and 0x1303, Flare/b on Flare.jpg, 015) reach outside it:
frames 20, 25 and 29 of those two scenes change (up to 3,477 pixels), and they are byte-identical to before when only
Flare's row is set back to REPEAT. Every other bow and staff frame is byte-identical.

## Native routes

- `reconstructed/particles/particles.c`: `MU_PT_BITMAP_FIRE06` shares Fire01's create, move and render cases;
  `mu_pt_kind_supported(0x7f40, 1..3)`.
- `native/core/mu_particles.c`: the Fire06 slot (`Data/Effect/Fire06.OZJ`, LINEAR, CLAMP).
- `reconstructed/combat/bow_fx.inc`: `mu_sfx_render_state`, the three wrappers' caches and GL state.
- `native/core/mu_combat.c`: the decal sink follows the wrappers' state; each decal quad carries its blend factors,
  alpha test and depth mask (`mu_combat_quad.alpha_test`, `.depth_mask`); the software path draws them with the
  raster's GREATER 0.25 test and depth writes, the GL part with glEnable(GL_ALPHA_TEST) and glDepthMask. The bitmap
  table carries each LoadBitmap's filter and wrap (`mu_combat_bitmap.filter`, `.wrap`), used by both paths.

## Still open

- **Fog on combat quads:** the wrappers enable or disable GL_FOG when the fog flag is set; combat quads are drawn
  without fog in both native paths (unchanged; Lorencia's scenes have no fog).
- **The raster's linear GL_CLAMP:** inside [0, 1] the software raster still blends the far edge's texel into the
  outer half texel (its convention for every GL_CLAMP bitmap, terrain decals included); the GL part uses clamp to
  edge. Unchanged here.
- **+0x38 of 0x70a:** stored, read by no reconstructed routine (015).
- **Uruk (not small, input missing):** keyed 0x806e/12 needs a world-100 population/globals capture that includes
  the weather value `0x01cf15ec`, and a native feed for that value (default weather stays 0), as 013 named.
- **Muun (not small, input missing):** the `0x0114203d` consumer needs a Muun owner fixture or capture with the
  OBJECT's ownership, type, lifetime and posed bone transforms (the 16 `muuneffects.tsv` records exist), as 013
  named.
- **Live look:** not taken; the static contracts fixed what the native scenes show.

The exact counts and wall times are in the [handoff](../handoffs/RENDER-EFFECTS-016.md).
