# App shadow and window follow-ups

APP-POLISH-001 checks the two visual inferences from APP-REFRESH-004 against original instructions. The result
supports retaining opaque ordinary character shadows and the existing Warps size rule. This is bounded code
agreement, not proof of identical whole frames or every HUD element.

## Identity and method

- Target `main.exe`: `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
- Text at 0x00401000: `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
- Data at 0x01a7c000: `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
- Section 3: `0571c519b1c4eaf97a143d2dd29bf2a3799e56b2f613cda0d084f4b857c1dc6f`.

The validator checks all three capture pins. It seeds synthetic world and graphics-cache globals rather than
reusing runtime state from section 3. Unicorn enforces allowed code ranges and defined global/heap reads.
The native policy and state functions are extracted verbatim into a temporary C translation unit. The production
GFx layer runs through the existing native host with a recording movie API. No client bytes are committed.

## Character shadow

Verified caller slice `0x0176cfab..0x0176d15b`, ordinary visible, unbuffed character parts:

- Underwater predicate `0x016a88ae`, including `0x016a8325`: worlds 7 and 128..130 select
  `EnableAlphaTest(1)` at `0x0184a990` and black with alpha 0.2.
- Other worlds take `0x0176d008`, call `DisableAlphaBlend` at `0x0184a7f3`, then `glColor3f(0,0,0)` at
  `0x0176d028`. OpenGL supplies alpha 1. This includes Lorencia, Devias and Noria, and applies to ordinary wing
  parts through the same native character-shadow function.
- `0x009b0418` excludes worlds 24..29 and 36. Worlds 10 and 132 are excluded too. The predicate at
  `0x00e136f3` selects z offset 5 in world 143; other admitted worlds use zero.
- `RenderBodyShadow` at `0x012bc07a` keeps the caller's color/blend, removes texturing and alpha testing with
  `0x0184a783(0)`, disables depth writes with `0x0184a763`, projects posed mesh vertices and restores depth
  writes with `0x0184a743`. It does not replace the current depth-test function. No stencil operation appears
  in the compared pass. The native backend explicitly depth-tests these triangles.
- Projection is `x += (x + 2000) * z / (z - 4000)` relative to BodyOrigin, with 2500 in world 30;
  height is terrain + 2 + offset. World 145 uses origin z + 10 + offset instead. The existing particle oracle
  compares emitted vertices, state calls, terrain queries and mesh filtering with synthetic posed meshes.

The earlier "translucent" suggestion was an inference from appearance. The caller shows that adding a soft,
translucent shadow in Noria/Devias would change the original's ordinary body-shadow policy.

Excluded from the new policy comparison: object visibility/shadow flags, event suppression, buff 0x12,
model-specific hide-mesh overrides at `0x0176d0c7..0x0176d10a`, culling/overlap across the whole scene and
special helper passes. The projection comparison does exercise independent synthetic mesh hiding.

## Warps and HUD

Verified Warps window creator `0x00ac9edc` through SetScale `0x00aaebca` and SetWindowSize `0x00aae4ae`,
alignment 10, compared with native `MoveCommand` invokes:

- Height below 700 sends SetScale(83). At 700 and above it sends no scale adjustment.
- At 1280x800 and 1504x936 the calls are SetAlign(10), SetWindowSize(actual width, actual height).
- `0x00aae4c6..0x00aae4e5` forwards seven words to the viewport helper `0x00ab0d72`:
  `[width, height, 0, 0, width, height, 0]`. The viewport is the actual window, not a fixed 800x600 canvas.

Thus this caller resizes the viewport and gives the movie the window dimensions without proportional movie
magnification. The real-movie journeys confirm unchanged Warps row points. Native Retina backing scale is a
separate points-to-pixels conversion.

This does not verify the complete base HUD initialization, Scaleform SDK scale mode, or every ActionScript
layout function. That portion of priority 2 remains open. No visual scaling adjustment is made on partial evidence.

Counts, wall times, mutants and app checks are in [the handoff](../handoffs/APP-POLISH-001.md).
