# Client JSON effects: particle systems, billboards and the native effect module (NATIVE-FX-001)

This finding maps the client's `Data/Effect/*.ein` effect code, reconstructs it in C (`reconstructed/effects`),
compares the C with the client's own instructions, and adds a native effect module and CLI (`native/core/mu_effect.*`,
`build/mu-effect`). It answers the EFFECT-001 roadmap question (runtime meaning of the effect JSON) for the two
effect types that the installed files use.

"Compared" means the authored C ran against the actual client instructions in Unicorn
(`scripts/validate_effects.py`) and agreed byte for byte on every compared frame. "Static reading" means decoded
instructions only. Names are ours; the client's RTTI names were not captured.

## Identity and method

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Third section capture `main-01ced000.bin` (x86-linux-capture-04, same restored text) | `0571c519b1c4eaf97a143d2dd29bf2a3799e56b2f613cda0d084f4b857c1dc6f` |
| Its initialized part `0x01ced000..0x01cffa00` | `299d83842841fa2cdb619c42fa25d42c228971c9261d526c5743102092729f32` |

The validator runs the client's own path for each case:

1. the client JSON reader (`0x0094997e` source, `0x0093c510` root, `0x0093f708`/`0x0093f7e8` reader and parse);
2. the effect constructor (particle system `0x00a8a436`, billboard via its vtable), base load `0x00a760b2` and the
   type load (`0x00a88fda` / `0x00a6f3e1`);
3. per rendered frame: node update `0x00a75708(dt, 0, 0)` (transform `0x00a76dfe`, then the type update with every
   component, emitter and shape routine it reaches), then the type draw (`0x00a88720` with fill `0x00a8a55c`, or
   `0x00a6ebd1` with fill `0x00a70036`).

Per frame it compares with the C: the live particle records (136 bytes each), the bytes passed to `glBufferSubData`
(the VBO vertex stream), the draw state derived from the recorded GL calls (texture enable, blend enable and
factors, `glMultMatrixf`, cull disable, vertex count) and the number of `rand()` calls.

Boundaries modelled in Python, not client code: `operator new`/`malloc`/`free` (bump allocator), `rand()` (the MSVC
LCG, seeded per case), `sscanf("%lf")` in the JSON number decoder (correctly rounded, like the UCRT), the effect
texture manager `0x00a8fb55` (returns no texture or a fake one), the terrain height `0x016cc9e2` and normal
`0x016ccbb6` (an authored x86 stub for a plane), the GLEW buffer entry points and `opengl32` imports (recorded), locks
(no-ops) and the heap imports. Section-3 bytes beyond the initialized part start zeroed; the report lists every
section-3 address a case read before writing it.

## 1. Data model (compared)

* `.ein` is JSON. `Type` 0 is a particle system (vtable `0x01a81d0c`, 0x158-byte object), `Type` 1 a billboard
  sprite (vtable `0x01a80844`, 0x170-byte object). The 370 installed files are 257 particle systems and 113
  billboards; no other type is installed.
* Missing keys read as JSON null: 0, false, empty arrays (JsonCpp-style `asFloat`/`asInt`/`asUInt`/`asBool`
  `0x0093d773`/`0x0093d1ed`/`0x0093d361`/`0x0093d917`).
* Base keys (`0x00a760b2`): `Name`, `Texture`, `Scale`, `Duration`, `Looping`, `randomduration`, `minduration`,
  `maxduration`, `parentduration`. Particle-system keys: `SpaceIsLocal`, `MaxParticle` (capacity), `Blending`,
  `Billboarding`, `LengthScale`, `SpeedScale`, `Components`. Billboard keys: `Width`, `Height`, `RotationAngle`,
  `Blending`, `Billboarding`, `Brightness`, `Components`.
* Particle-system components by `Type`: 0 emitter (`Delay`, `Frequency`, `MinEmissionCount`, `MaxEmissionCount`,
  `CurveEmissionCount`, `Bursts`, and sub-components 0 shape, 1 start colour, 2 start lifetime, 3 start rotation,
  4 start size, 5 start speed), 1 colour over lifetime, 2 force over lifetime, 3 rotation over lifetime, 4 size over
  lifetime, 5 speed over lifetime, 6 texture-sheet animation, 7 terrain collider. Billboard components: 0 colour,
  1 rotation, 2 size, 3 texture-sheet animation, 4 force.
* Emitter shapes: 0 box `0x00a7dcae`, 1 cone `0x00a7f50b`, 2 hemisphere `0x00a84629`, 3 point `0x00a8503b`,
  4 sphere `0x00a860a7`.
* `Blending`: 0 none; 1 alpha (`GL_SRC_ALPHA`, `GL_ONE_MINUS_SRC_ALPHA`); 2 additive (particles `GL_ONE, GL_ONE`,
  billboards `GL_SRC_COLOR, GL_ONE`); 3 multiply (`GL_DST_COLOR, GL_ZERO`).
* `Billboarding` (particle fill): 0 camera-facing, 1 horizontal (world X/Y), 2 velocity-directional, 3 vertical
  (world Z and camera right); billboards add 4, a plane in the effect's local space.
* Curves (`0x00a74a3f`) are cubic Hermite with unscaled tangents and clamp outside the key range; gradients
  (`0x00a73b41`, `0x00a73ca4`) are piecewise linear.
* Random numbers: MSVC `rand()` `0x01989721`; `0x00a7ebb0` maps `rand() % 1001 / 1000` into a range through the
  lerp `0x00a7eb14`.

## 2. Update and draw rules (compared)

* The client advances effects once per rendered frame by the constant at `0x01cf103c` = 0.1 s (section-3 initialized
  data), not by elapsed time.
* The update needs the previous draw: the type update returns after decrementing the remaining time unless the
  draw flag (particle `+0x114`, billboard `+0x144`) is set, and clears it. The first update after a load therefore
  emits nothing.
* The emitter (`0x00a80752`) emits only when `rand() % Frequency == 0`. **An emitter without `Frequency` divides by
  zero** (`div dword [ecx+0xc]` at `0x00a80790`). On Windows that is an integer-divide exception inside the effect
  update. 45 installed particle systems have no `Frequency`; 39 of them reach the division within 20 frames. The
  C marks the effect `faulted` and stops updating it; the validator accepts the client stop only at `0x00a80790`
  with a zero divisor, on the same frame as the C, with equal `rand()` counts.
* Vertex record: 36 bytes (`glVertexPointer(3, 0)`, `glTexCoordPointer(2, 12)`, `glColorPointer(4, 20)`), four
  vertices per particle or billboard, drawn as `GL_QUADS`. `SpaceIsLocal` particle systems are drawn inside
  `glMultMatrixf(world matrix)`; billboards disable culling through the client's cached wrapper.
* The particle fill can write the owner's tint back into particles; effects without an owner (the compared case)
  never do.

## 3. Verification numbers

Full private run (`--mutations 1500 --frames 60`, library SHA-256 `356cc5d8a2463289…`):

| Measure | Value |
|---|---:|
| Cases (370 installed `.ein` files + 1,500 mutations) | 1,870 |
| Frames compared | 109,774 |
| Particle records compared (136 bytes each) | 595,838 |
| VBO vertices compared (36 bytes each) | 2,507,848 |
| `rand()` calls matched | 450,850 |
| Terrain stub calls | 216,859 |
| Client divide faults matched (same frame, divisor 0, equal `rand()` count) | 44 |
| Mismatches | **0** |
| Distinct effect-code basic blocks executed | 3,636 |

Mutations randomize every root key, emitter counts, delays, bursts, shapes and sizes, add colour/curve/force/
rotation/texture-sheet/collider components, apply random transforms (position, rotation, scale), cameras, frame
steps (0.04/0.1/0.25 s), seeds, texture presence and terrain planes. Installed cases use seed 1, step 0.1, a fixed
camera and flat ground at z = 0. The 44 matched faults are all installed files without `Frequency` (38 fault on the
first emitting frame; the rest after their `Delay`). The 45th (`Delay` 7.0 s) does not reach the division within 60 frames.

Two points about the comparison:

* **NaN encoding.** Eight cases produce NaN particles: the collider divides force by speed, and some installed
  effects have speed 0, so it computes 0/0. x86 SSE returns the "real indefinite" `0xffc00000`; AArch64 returns the
  default NaN `0x7fc00000`. The validator maps every NaN word to `0x7fc00000` before comparing (25,118 words in
  those eight cases) and reports the count. Which words are NaN is still compared exactly.
* **Earlier runs.** The first full run after the takeover (1,870 cases) found 50 real mismatches besides the
  matched faults. In 41, an expired billboard reported texture-enabled draw state although the client returns before
  any GL call; this is now fixed in `mu_fx_draw`. In 9, the harness gave the client a terrain plane while the C
  skipped the collider; every case now sets the same plane on both sides. After both fixes the run above reports 0.

Synthetic portable checks (CI): `reconstructed/effects/test_effects.py` (MSVC `rand` sequence, curve endpoints,
emission up to capacity, per-seed determinism, blend states of both types, the missing-`Frequency` fault frame,
JSON rejection) and `native/tests/test_native_effect.py` (deterministic renders, vertex dump layout, billboard sheet,
fault, scan). Private (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, pinned captures under `evidence/` or
`MU_EVIDENCE`): an 80-case instruction comparison and an installed-file scan.

## 4. Native module (static readings where noted)

`native/core/mu_effect.*` loads an `.ein`, resolves its `Texture` path case-insensitively under the installation
root, runs the reconstructed update and fill, and rasterizes the quads with the native software rasterizer.
The terrain collider sees flat ground at z = 0 (no world is loaded). `build/mu-effect` offers `render`, `sheet` (contact sheet of every K-th frame), `dump` (per-frame vertex streams)
and `scan` (every installed `.ein`; 370 files, 0 load failures). Renders stay local
(`~/Documents/mu-mac-tools/native/renders/effects/`).

Render state applied by the native draw that is a **static reading** of the EffectManager render `0x00a7a30e` and
the effect texture loader `0x00a90987`, not compared: depth test on, depth writes off, alpha test off,
`GL_MODULATE`, `GL_LINEAR`, `GL_REPEAT`, no mipmaps. Culling for particle systems is left off: the particle draw does
not set it, and the state left by earlier passes was not recovered. The shared software rasterizer gained
`GL_DST_COLOR` (`0x306`) as a blend factor for the multiply mode.

## 5. Limits and next steps

* The native module draws with flat ground at z = 0 for the collider, not the loaded world's terrain.
* Not reconstructed: the EffectManager (creation by name, lists, parenting, `parentduration`, owner tints, frustum
  culling via the planes of `0x00a8d821`), any effect types other than 0 and 1, and the callers that attach effects
  to characters, skills and world objects.
* The terrain collider was compared against a plane stub, not the client terrain.
* `sqrt`, `sin` and `cos` use host libm in the C and the client's CRT (SSE2 path, flag `0x0bdd1cc8` = 1) in the
  validator; they agreed on every compared case, but that is not a proof for all inputs.
* Next: map the EffectManager and its callers, then attach effects to native characters and terrain objects.
* Update (NATIVE-FX-002, [client-effect-manager.md](client-effect-manager.md)): trees, parentduration, owners,
  instancing, the octree, culling and the render pass are now compared. Two statements above are corrected there:
  the owner tint replaces the colour only while filling (it is restored), and the EffectManager render does not set
  the depth test (it turns depth writes and alpha test off and restores them). Factory instances never reach the
  `rand() % 0` fault: the emitter constructor replaces `Frequency` 0 by 1.
