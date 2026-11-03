# SPRITE-DRAW-001: the shared sprite draw path

Question (from RENDER-WORLDS-Q2 §5): Acheron (91) creates bone sprites and the native counters report them drawn,
yet the frames do not change. Is the shared sprite path (CreateSprite 0x01692508 → RenderSprites 0x0169270e →
RenderSprite 0x0184c39c → `mu_world_particles_draw` → GL/raster backend) losing every sprite's pixels?

**Answer (verified): no.** The shared path draws sprites in the software raster and in GL, in the world runtime
and in `mu-render character`. Acheron's six Spark04 sprites are **outside the view frustum** at the DATA-ACQ-002
tile. The live capture shows none there either. No C behaviour changed, and no hash changed.

## 1. Minimal reproduction (verified, regression test)

`native/tests/sprite_draw_host.c` (`test_native_sprite_draw.py`, portable, synthetic `flare01.OZJ` 32×32) creates
one sprite (`mu_world_particles_sprite`, scale 4, light 1) 400 units ahead of the eye. A client-style view matrix
(x right, z up) and a 60° perspective are used. The sprite is drawn through `mu_world_particles_draw`, both via
`mu_world_particles_draw_raster` and via the headless-GL `mu_gl_backend` (the `--backend gl` path the fidelity tour
uses). Blends 0 (additive), 2 (alpha) and 4 (opaque then alpha) are each drawn separately.

| Sprite position | Raster lit px (blend 0/2/4) | GL lit px (0/2/4) |
|---|---|---|
| on the view axis | 676 / 676 / 676 | 676 / 676 / 676 |
| 0.75 vertical half-angles up | > 400 each | > 400 each |
| 1.5 vertical half-angles up (Acheron's case) | 0 / 0 / 0 | 0 / 0 / 0 |

So on current main the sprite **does** produce pixels. The task's premise (an invisible sprite in front of the
camera) does not reproduce.

Planted mistakes, compiled into the host one at a time (ad hoc; no reconstructed routine changed, so no Unicorn
row): `g_bind` slot always −1, `g_end` corner count 3, sink colour zero, sink alpha zero, and `mu_pt_render_sprite`
skipped in `mu_pt_sprites_render`. All **5/5 are caught**.

## 2. The path, traced (static + measured)

- **Creation.** `mu_world_particles_sprite` → `mu_pt_sprite_create`: live, alpha 1, 1×1 sheet.
- **Pass order.** Draw column: objects 20 (RenderObjectVisual creates the sprites), then particles 100.
  `mu_world_particles_draw` runs decals, then RenderJoints(0), then `mu_pt_sprites_mark_visible`, then RenderSprites
  mode 0 (draw and kill), then the particles.
- **Matrix.** `p->camera[4i+j] = modelview[4j+i]` (0x0184a569). RenderSprite builds eye-space corners with
  `VectorTransform`, and `g_end` maps them back through `to_world` (Rᵀ(v − t)) before the backend's modelview.
- **State.** Blend 0 gives ADD (ONE/ONE, depth mask off); 2 gives ALPHA with alpha test; 4 gives OPAQUE then ALPHA.
  Depth test is on.
- **Texture.** `g_bind` maps the bitmap id to the world particle slot (`bitmap_present` is required). The GL
  backend binds the uploaded texture of that slot.
- **Vertex format.** GL_QUADS becomes two triangles (0 1 2, 0 2 3), with texcoord, colour and vertex per corner.
- **Faithfulness.** The reconstructed CreateSprite/RenderSprites/RenderSprite equal the original under Unicorn
  (`validate_particles` families `sprite` 40, `sprite_create` 4 and `sprite_render` 4 cases, rerun here: pass).

## 3. Acheron (91): why its sprites leave no pixels (measured)

A temporary local trace of every emitted sprite quad was made on the 91 capture (stderr only; removed, never
committed). Per drawn frame, six Spark04 (slot 18, 0x8155) quads reach GL: additive, colour about (0.94, 0.2, 0.2),
48 units wide, about 2,300–2,420 units ahead of the eye. Their eye-space y/−z is 1.45–1.62× the vertical half-angle
tangent (fov 39°, so tan 19.5° = 0.354). Every one of them lies **above the top edge** of the frustum.

- A sprite injected at the hero (+150 z) through the same pool shows at once (bbox 802..920 × 297..414).
- Each Q2 probe on its own leaves the frame unchanged, which is what Q2 saw. Depth-off alone does nothing because
  the quads are outside the frustum. ×20 alone does nothing because the 960-unit quads then reach the top rows, but
  at about 2,350 units behind the ground those rows show, so the depth test hides them.
- The live 91 screenshot shows no bone glints at this tile.
- `drawn_sprites` counts the records handed to the GL stream (registered bitmap), not on-screen quads. That is
  why it reads 6 while the frame stays unchanged.

## 4. Impact over the DATA-ACQ-002 tour (measured)

Method: the 32 captures were rendered at 25 steps, 1722 × 1048, `--backend gl`, twice. Run "on" is main. Run "off"
is the same build with the sprite pass given no GL sink (sprites still created, counted and killed). Sprite pixels
are the changed pixels on → off. "In frustum" counts the last frame's sprite quads with any part inside the view.

| Capture | Sprites/frame | In frustum | Bitmap | Sprite px | Image mean \|Δ\| vs live, off → on |
|---|---:|---:|---|---:|---|
| 134 Ashen Aida | 24 | 12 | Spark03 | 10,128 | 13.135 → 13.053 |
| 63 Vulcanus | 9 | 3 | flare01 | 11,470 | 1.863 → 1.841 |
| 79b Event Square | 12 | 6 | Flare | 72,087 | 3.817 → 3.604 |
| 144 Swamp of Destruction | 42 | 21 | Shiny02 | 1,260 | 12.415 → 12.415 (inside a mask) |
| 91 Acheron | 6 | 0 | Spark04 | 0 | 6.856 → 6.856 |
| 135, 137, 142, 79 | 13, 4, 4, 5 | 0 | | 0 | equal |
| the other 23 | 0 | 0 | | 0 | equal |

Every capture with a sprite quad in the frustum has sprite pixels. Every capture without sprite pixels has no
sprite quad in the frustum.

**Skill/item effect sprites.** flareBlue 0x7fdd (RENDER-EFFECTS-005, rank-5 owner effect) was rendered with
`mu-render character` (installed `player.bmd`, `ArmorMale161_elf.bmd` as armour 0x1c26, lighting 1, world time 0,
320 × 240, raster). It emits one slot-38 quad per frame, and frame 0 changes by **7,710 px** between on and off
(bbox 139..238 × 103..202). The sprite is visible.

**Hash changes:** none. No source in the draw path changed. The lane adds only the test host, its Make rule and
the test.

## 5. Limits and next steps

- `mu_pt_sprites_mark_visible` marks every live sprite visible (static: the native stand-in for 0x01692887). Only
  the alpha ramp (0.2..1) depends on it, not presence. Its own frustum test is not reconstructed.
- RENDER-EFFECTS-005's open "owner binding" (native sprites are owner-free; the client binds them to the OBJECT) is
  a separate placement question. It does not hide pixels.
- "Invisible effect" reports from other lanes should first check the frustum and depth of the emitted quads. The
  trace method in §3 (eye-space corners per quad) answers that in one run.

[Handoff](../handoffs/SPRITE-DRAW-001.md).
