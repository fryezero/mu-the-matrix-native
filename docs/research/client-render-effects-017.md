# The armour owner effects' particles, fog on combat quads and the raster's clamp

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; pinned text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` (base `0x00401000`), image data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, third section `0x01ced000` (capture 04,
`0571c519…1c6f`). This continues [016](client-render-effects-016.md) and
[RENDER-ITEMS-002Q](client-render-items.md#part-17-owner-effect-programs-of-the-armour-bodies-render-items-002q),
whose armour owner-effect programs (38 chest pieces, 5 helms) asked for three particle kinds the native did not have
and counted each request as refused. No live client session was needed.

## The three particle kinds (verified)

CreateParticle `0x015ae7b0`, MoveParticles `0x01616c80` and RenderParticles `0x0159123f` reach 0x810a through its
compare chain (subtype tests at `0x015b1435`, `0x0161a913`, `0x0159f7ae`) and Spark03 0x7f26 through subtype jump
tables (create `0x016166cc` index subtype − 1, move `0x0168f628` index subtype). Common parts (the record's
initialisation, the motion flag's MovePosition, the LifeTime − 1 tail, the blend by component count) are the
existing reconstruction.

| Kind | Create | Move (per step) | Render |
|---|---|---|---|
| 0x810a/7 (OBJECT angle) | `0x015b143f`: LifeTime `rand % 5 + 50`, Scale = the argument, velocity (`rand % 3 − 1`, `rand % 5`, `rand % 3 − 1`), rotation `0x011ff622(0, 360, 1)` | `0x0161a91d`: at LifeTime ≤ 45 velocity x += sin, y += cos of `rand % 360` degrees; light / 1.005; rotation += `0x011ff622(−10, 10, 1)`; MovePosition `0x012af52d` with the negated angle (`0x00cfca12`); Scale − 0.01; LifeTime = (int)((double)LifeTime − 0.1); dead at LifeTime ≤ 0 or Scale ≤ 0 | plain sprite `0x0159f7e9` (subtype table `0x015ae557`) |
| 0x810a/0xf (normalized bone 19 → 26 direction) | `0x015b227a`: LifeTime 30, kept at +0x4c, +0x1c = Scale, rotation `0x011ff622(0, 360, 1)`; velocity = the request's angle vector (`0x00cfc8f2`), angle = 0 (`0x00cfcede`) | `0x0161b3d8`: Scale ± 0.015 by LifeTime / initial LifeTime > 0.5, floor 0; rotation + 10; velocity x, y += `0x011ff622(−0.5, 0.5, 10)`; velocity z − 0.15 | plain sprite `0x0159f7e9` |
| Spark03 0x7f26/0x26 (OBJECT angle) | `0x015e1113`: LifeTime `rand % 5 + 30`, Scale `rand % 5 / 10 + 0.2`, velocity `rand % 5 − 2` each, gravity 2.5, light = its own copy (`0x009fa1cb`) | `0x01654b63`: velocity x += sin, y += cos of `rand % 360` degrees; velocity × 0.85 (`0x00cfcd74`); light / 1.05 (`0x00cfcddf`); Scale − 0.01; z − gravity; LifeTime − 1, dead at ≤ 0 | plain sprite `0x015a531f` |

`reconstructed/particles/armour_kinds.inc` ports the three; `mu_pt_kind_supported` admits exactly these pairs. Both
bitmaps were already in the world particle table (0x810a pin_star03 from 010, Spark03), so the native owner route
(`owner_emit` → `mu_world_particles_create`) creates them without other changes. `validate_render_effects17`
compares create, move and render with the client under Unicorn; the move cases mix in the boundary records (LifeTime
46/45/1, LifeTime / initial 15/30, Scale 0.01 and 0.015).

## Fog on combat quads: the wrappers never switch it (verified, static)

The blend wrappers (`0x0184a7f3`, `0x0184a990`, `0x0184aa2b`, the other six in `0x0184a7f3..0x0184acf6`) and the
scene setup `0x0184adc7` call glEnable/glDisable(GL_FOG) only behind `movzx eax, byte [0x0bdc597c]; test; je`. That
flag is never set:

- The pinned text names `0x0bdc597c` sixteen times: eleven gated reads and five stores, all `mov byte [0x0bdc597c], 0`
  (`0x01851c24`, `0x018576de`, `0x01857f0d`, `0x018591af` in the render scene before the terrain, `0x0185b124`).
- No instruction pushes or loads the address as a pointer, and neither the image data nor the third section holds
  it, so there is no indirect writer through a stored pointer.

So effect quads are fogged only by fog someone else left on. The only ungated glEnable(GL_FOG) in the text is
`0x00d8cca8` (black, GL_LINEAR, start 2000, end 2700), called once from the render scene (`0x01859783`) when the
world is 0x1e and the hero stands in x 16100..19000, y 18900..21700, and switched off again at `0x01859cad`
([client-environment.md](client-environment.md) §5 named the box). Everything drawn in between, terrain, objects,
characters and effects, is fogged there. The native draws no part of the scene with that fog, so combat quads
without fog match the client everywhere except that box, where the whole native scene lacks it (a world-render gap,
not a wrapper behaviour; no combat-only change would make it right). `mu_sfx_render_state` keeps modelling the
wrappers' fog branch for a flag that is set (016's `render_state` family); no native frame changes. The validator's
`fog_sites` family checks every reference and GL_FOG call site above.

## The raster's linear GL_CLAMP: clamp to edge (fixed)

`native/core/mu_raster.c` clamped GL_CLAMP coordinates to [0, 1] but then took the second bilinear tap modulo the
size, so in the outer half texel (u = s·w − 0.5 < 0, or > w − 1) it blended the opposite edge's texel, a GL_REPEAT
seam. Its header promises clamp to edge, and the combat GL part (`native/world/parts/combat.c`, 016) binds GL_CLAMP
bitmaps as GL_CLAMP_TO_EDGE, where both taps stay inside [0, w − 1] and the outer half texel is the edge texel (the
other GL parts hand GL_CLAMP itself to the driver). The raster
now clamps both tap indices; nearest sampling and GL_REPEAT are unchanged. `raster_sample` compares the raster's
lookup with that rule binary32 for binary32 (random textures 1..256 texels, coordinates inside, outside and on the
half-texel edges).

The client itself loads these bitmaps GL_CLAMP (0x2900), not GL_CLAMP_TO_EDGE. Strict GL 1.x GL_CLAMP blends the
border colour (transparent black by default) into that half texel; many drivers treat it as clamp to edge. Which one
the original's GL stack applies was not measured (inference: no live capture of an edge pixel); the native's raster
and combat GL part now agree on clamp to edge.

What changes on screen: only software-raster frames, at the edges of linear GL_CLAMP sprites and quads drawn larger
than their texture (the cyan seams along the corners of 0x12f9's Spark sprites disappear) and at clamped trails. The
counts are in the [handoff](../handoffs/RENDER-EFFECTS-017.md). The GL paths and therefore the DATA-ACQ-002 tours are
unchanged.

## 0x70a's +0x38

Not needed: no routine reconstructed here reads it.

## Still open

- ~~**World 0x1e's box fog** (`0x00d8cca8`)~~: drawn since RENDER-WORLDS-FOG, both renderers
  ([client-worlds-fog.md](client-worlds-fog.md)).
- **GL_CLAMP vs clamp to edge on the original's driver:** an edge-pixel capture of one clamped sprite would settle
  whether the border colour shows.
- From 016: Uruk's weather capture (0x806e/12) and the Muun owner fixture still need their inputs.
- **Armour owner effects outside the bone domain** (RENDER-ITEMS-002Q): parts whose model lacks the program's
  highest bone still refuse the whole program; 0x1a78's helm has no installed model, so it has no worn scene.

The exact counts and wall times are in the [handoff](../handoffs/RENDER-EFFECTS-017.md).
