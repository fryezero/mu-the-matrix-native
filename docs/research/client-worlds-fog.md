# RENDER-WORLDS-FOG: world 0x1e's box fog

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Text and
second-image-data captures pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly, then compiled
authored C compared with the original instructions under the strict Unicorn machine (`scripts/validate_worlds_fog.py`),
then native renders of the world before and after. Labels: **verified** = instruction-compared, **static** = read from
the disassembly only, **inference** = reasoning.

Follows [RENDER-EFFECTS-017](client-render-effects-017.md) (fog on combat quads: the wrappers never switch GL_FOG;
the only ungated glEnable(GL_FOG) is `0x00d8cca8`) and [client-environment.md](client-environment.md) §5.

## 1. What the original draws (verified)

It is not a box of geometry: "box" is the region that switches the fixed-function fog on. World 0x1e is
`Data/World31` (map name GlobalText 669; the Castle Siege valley in the usual numbering, **inference**).

RenderMainScene (`0x0185916b..0x01859d89`) runs two tests on the world global `0x01cf15fc` and the hero OBJECT's
Position (Hero `0x0a39d754` + `0x33ac` = CHARACTER + 0x3254 + 0x158, through the accessor `0x00cfc94a`):

| Where | Test | Calls |
|---|---|---|
| `0x018596b4..0x01859797`, after the scene setup `0x0184adc7` and `0x016cba24`, before the perspective setup `0x01849f08` | world ≠ 0x1e | none (jumps to `0x01859797`) |
| | world 0x1e, hero outside the box | `glDisable(GL_FOG)` (`0x0185978b`) |
| | world 0x1e, hero inside | StartFog `0x00d8cca8` with a pointer to three zeroed floats `[ebp-0x74..-0x6c]` |
| `0x01859bfa..0x01859cb3`, after the combat effects `0x0169159e` and the last pass setup `0x0184adc7` | world 0x1e and hero inside | EndFog `0x00d8cd12` = `glDisable(GL_FOG)` |

The box (both tests, `comiss` + `jb`, so a NaN coordinate fails each compare): `x ≥ 16100` (`0x01af7098`),
`19000 ≥ x` (`0x01aae3f0`), `y ≥ 18900` (`0x01af70a0`), `21700 ≥ y` (`0x01af70a4`): tiles x 161..190, y 189..217.
z is not tested.

StartFog `0x00d8cca8`, in order: `glEnable(GL_FOG)`; `glFogfv(GL_FOG_COLOR, colour)`; `glFogf(GL_FOG_MODE, 9729.0f)`
(GL_LINEAR passed as a float, `0x01aa6ac0`); `glFogf(GL_FOG_START, 2000.0f)` (`0x01a802d8`); `glFogf(GL_FOG_END,
2700.0f)` (`0x01aa6aa8`). No density (linear fog does not read it). GL reads four floats of the colour: the fourth is
the caller's stale `[ebp-0x68]`; the fog equation does not change alpha, so it has no effect.

StartFog and EndFog have one caller each (`0x01859783`, `0x01859cad`), and neither address appears as a dword in the
text or the image data (the `sites` family). Between the two calls the render scene draws the terrain, objects,
characters, items, helpers, environment, particles, the EffectManager pass and the combat effects; after EndFog it
draws the screen haze `0x00def268` and the 2D interface. So the fog covers every 3D part of the scene and nothing 2D.
Nothing else switches GL_FOG during the scene: the blend wrappers do so only behind `0x0bdc597c`, which is only ever
stored 0 (RENDER-EFFECTS-017, verified).

Pass and blend: the fog is GL state, so each part keeps its own blend, depth and texture state; the fixed-function
fog changes each fragment's RGB to `f·C + (1 − f)·(0, 0, 0)` with `f = (2700 − c) / 700` clamped to [0, 1], `c` the
fragment's eye distance. Additive (ONE, ONE) effects are darkened the same way, as the client's are.

## 2. What the native did, and does now

Before: no native renderer drew any fog; worse, the GL mesh backend (`native/viewer/gl_backend.c`) called
`glDisable(GL_FOG)` at every mesh draw from the mesh state's fog bit (always 0), so even a scene fog would have been
switched off at the first object.

Now:
- `reconstructed/environment/env_fog.c` (`mu_env_scene_fog_begin`, `mu_env_scene_fog_end`) restates both tests and
  StartFog's parameters.
- `native/world/world_rt.c`: the GL draw issues StartFog's five calls (or the glDisable) before the first part and
  EndFog before the first part ordered at or after the haze (haze 125, item labels 130, names 140); the software draw
  sets the raster's fog the same way.
- `native/viewer/gl_backend.c` (both the immediate and the batched prepare) no longer touches GL_FOG, as the client's
  wrappers do not.
- `native/core/mu_raster.c` has a minimal GL_LINEAR fog stage (off unless `fog` is set): eye-space z carried per
  vertex through clipping, interpolated perspective-correctly, `c = |z_eye|`, applied after texturing and before the
  alpha test and blending, RGB only. `c = |z_eye|` is the approximation GL allows for the eye distance and what
  drivers use by default (**inference** for the original's driver; macOS GL and the raster agree on the rendered
  frame within 0.009 mean |Δ| per channel, §4).

## 3. Instruction comparison (verified)

`validate_worlds_fog`: `begin` and `end` run the two test fragments as client code from a mid-routine EBP frame with
only the world, the Hero pointer and the hero's Position defined, StartFog/EndFog as client code, and the four GL
imports as logging stubs (arguments as bit patterns). The native side is `env_fog.c` turned into the same GL calls.
Cases: the world ids 0..145 with the hero inside, then world 0x1e in three of four cases with coordinates on each
edge, one ulp either side, anywhere, NaN, ±inf, −0.0 or any bit pattern. `placement` checks, for every draw anchor of
`reconstructed/world-order/parts_order.py` called in the render scene, that the native parts it stands for are fogged
(draw order below world_rt.c's boundary part, both columns) exactly when the call lies between StartFog and EndFog.
`sites` checks the single callers. Counts and mutants are in the [handoff](../handoffs/RENDER-WORLDS-FOG.md).

## 4. Fidelity

None of the 32 DATA-ACQ-002 captures (worlds 6, 38, 40, 56, 63, 79, 91, 112, 113, 116..120, 122, 123, 128..138, 140,
142..144) or the 14 October 22 views (0..4, 7, 8, 10, 33, 37, 51, 57, 80) is in world 0x1e, and no live capture of the
box exists, so there is no live reference for the fogged frame.
- World 0x1e inside the box (tile 176,190, three demo players): GL before/after mean |Δ| 17.6 per channel (the far
  floor goes black from 2000 units, the characters dim, the name plates stay); software 17.6; GL vs software after
  0.009 (before 0.028).
- World 0x1e outside the box (tile 150,200): GL and software frames byte-identical before/after.
- Every other world: byte-identical by construction (the raster's fog is off, GL_FOG was already off at the frame
  start `mu_gl_frame`, and no other code enables it); the DATA-ACQ-002 32/32 and October 22 14/14 sweep confirms it.

## 5. Test Area 121 (static; not ported, slots stay 142/144)

Two corrections to [SLOTS3](client-worlds-slots3.md) §5's outline:
- The "action pick" `0x012affa4` is SetAction (37 instructions): with the object's model (`0x00966cc4` → `0x00eaa8cf`)
  and `action < model+0x26`, and `action ≠ o+0x2a`: `o+0x2c = o+0x2a`, `o+0xd4 = o+0xd0`, `o+0x2a = action`,
  `o+0xd0 = 0`. Native copies exist (`worlds_q_internal.h` `q_set_action`, `worlds_p_internal.h` `wp_set_action`,
  `kanturu_underground.c`). What 121's 0x10/0x11 and Devias 0x67 need is the rand-driven choice of the action around
  it, not a new SetAction.
- The after slot `0x00d5a6cc` (198 instructions) is body/mesh calls only: 0x2e and 0x35 RenderBody `0x00966def`
  (flags 2, `o+0xdc`, `o+0x74`, `o+0xa8..0xb0`, `o+0x68`, −1); 0x4c the same after writing the object light
  `o+0xec[k] = sin(T·s_k)·a + b` through `0x009681bd` (scales `0x01a7ed78`, `0x01a800a0`, `0x01aa528c`; a, b at
  `0x01a7df08`, `0x01a7df14`; T = `0x06fce370`); 0x53, 0x59, 0x5c a mesh call `0x00966e4a`. It is bounded on its own
  (the slot events of `world_slots2_visual.c` cover it), but without the custom slot the census and the frame stay
  partial, so this lane left both.
What the custom slot `0x00d58bd8` still needs, unchanged: a slot event that writes the model's per-vertex light
(`MU_MODEL_LIGHTS`, `0x06fd0918`) for every mesh after the transform and before the body draw (no object slot writes
it today, so the runtime and the mesh draw need the plumbing); the 0x10/0x11 action choice; posed bones and the 28
CreateParticle calls of 0x13..0x15 (refusals counted). 121 has no capture and no warp.

## 6. Limits

- No live reference for the fogged frame (no capture of world 0x1e's box).
- The raster's `c = |z_eye|` and per-fragment evaluation are the usual GL behaviour, not a reading of the original's
  driver (no `push 0xc54` = GL_FOG_HINT in the text, static; the hint stays GL_DONT_CARE).
- Test Area 121's two slots (§5).
