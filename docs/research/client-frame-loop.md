# Frame loop, frame cap and hot draw/VBO call sites

CLIENT-FRAME-001 maps three things statically:

* the main loop and the code that drives each frame;
* the 24 `GL_TRIANGLE_FAN` and 27 `GL_QUADS` immediate-mode routines;
* the buffer-object (VBO) users.

It also explains where the frame cap lives. This is a reading of decoded instructions
in the pinned restored text and data. No client code was executed. The CrossOver bottle
and its Wine processes were not touched.

**Short answers**

* **Frame cap.** The cap is a compiled-in 40 ms minimum frame time, enforced with
  `Sleep(40 - elapsed)` inside the frame driver `0x01851d39`. That works out to 25 FPS.
  The value is not read from config, data or the server. It is not a busy-wait.
* **Logic rate.** The same function also runs game logic in fixed 40 ms steps through
  an accumulator. Logic stays at 25 Hz whatever the render rate.
* **Why no file patch.** The cap bytes are absent from `main.exe` on disk, because
  Themida packs the code. A file-offset patch therefore does not exist. Changing the
  cap means writing three immediate bytes in process memory after unpacking (located
  below). Nothing was patched.
* **Fans.** The four-vertex fans come from three sources:
  * the terrain tile renderer: one fan per visible tile per layer;
  * terrain-projected decals: one fan per covered tile;
  * the 2D bitmap and rectangle helpers used by the UI.
* **Quads.** The `GL_QUADS` blocks come from billboard sprites/particles, grass and
  assorted effects.
* **VBOs.** Only one game subsystem streams VBOs every frame: the JSON effect system
  (`EffectManager`). It uses two `GL_STREAM_DRAW` buffers: a 144-byte sprite buffer
  that is fully rewritten per sprite, and a 144,000-byte particle buffer that gets a
  prefix of `n*144` bytes per emitter. The prefix writes are the "partial" updates.
  Each update is followed by `glDrawArrays(GL_QUADS, 0, 4n)` with fixed-function
  client arrays.

## Identity

| Input | Bytes | SHA-256 |
|---|---:|---|
| `main.exe` (target identity) | 32,229,376 | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | 2,557,764 | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| `IGC.dll` (installed, read for its PE header only) | 10,185,744 | `dbe122fe94e72286b871e192b6351bafdd28216312c300ba0d97d22a51a9c29b` |
| Debian `libwine_8.0~repack-4_i386.deb` (as in [skinning](client-skinning.md)) | 95,293,888 | `c992aad6a47d81b719514f5d06c5df10267f1e40a6f4f3b4e3f655cbbf308d57` |

The Wine DLLs used to name import slots are pinned in `scripts/client_frame_static.py`:
kernel32, kernelbase, ntdll, winmm, gdi32, user32 and opengl32. Each slot value
minus the DLL's preferred base must be one of that DLL's export RVAs. This pinned set
fully names 5 of the 25 IAT blocks, which hold every API used here:

* gdi32 (20 slots);
* kernel32/ntdll/kernelbase (272);
* opengl32 (81);
* user32 (94);
* winmm (12).

A scratch pass against the rest of the package fully named 12 more blocks (advapi32,
imm32, iphlpapi, netapi32, oleaut32, shell32, uxtheme, version, wininet, ws2_32,
dbghelp, urlmon). glu32 is named in the skinning report. Seven blocks are not Wine
exports: `0x01a7c094`, `0x01a7c7a0`, `0x01a7ca48`, `0x01a7cac4`, `0x01a7cb54`,
`0x01a7cc1c` and `0x01a7cc38`. The DLLs are untrusted third-party data and are only
parsed, never executed.

## 1. Main loop and frame driver

**Message loop** (inside WinMain, around `0x0120ed88`). The loop calls
`PeekMessageW(..., PM_REMOVE)`. When a message is waiting it translates and
dispatches it. When the queue is empty it calls the scene dispatcher `0x01859d8a(hdc)`
at `0x0120ef38`, which runs when the window-active flag `[0x01cf0fc0] == 1`. A second
call at `0x0120ef54` runs while inactive if the byte `[0x06fc9cb5]` is set. There is
no `WaitMessage` or `MsgWaitForMultipleObjects`, so the loop never blocks. The only
pacing is the Sleep described below.

**Scene dispatcher `0x01859d8a`** switches on the scene-state global `[0x01d1df70]`:

| State | Routine | Reading |
|---:|---|---|
| 2 | `0x0185ad63` (its helper `0x011e2c8c` calls SwapBuffers) | intro/logo scene (inference) |
| 3, 5, 6 | frame driver `0x01851d39` | login/server select, character select and in-game (inference) |
| 4 | `0x01851adc` (SwapBuffers at `0x01851c9a`) | loading screen; sets state 6 when done (`0x01851ce9`) |

The scene names are inferred from the per-scene routines. State 6 reaches the
main-game render `0x0185916b`, which calls the terrain, model, effect and UI passes
listed in section 3. The loading screen chooses one of four images
(`push 4` loop, `0x7b81+i`). Only the frame driver has a frame cap.

**Frame driver `0x01851d39`.** Every instruction below is checked exactly by the
script (36 checks):

```
acc = [0x0bdc5ec0]                          # leftover time from the previous frame
while acc >= 40:                            # 0x01851d6b cmp [ebp-0x34], 0x28
    logic step: per-scene tick (3: 0x01857236, 5: 0x01856e6c, 6: 0x0185613e),
                camera/UI updates, ++[0x0bdc5eb0]    # logic-step counter
    acc -= 40                               # 0x01851f90 sub eax, 0x28
clear colour by world; glClear(COLOR|DEPTH)
prev = [0x0bdc5e64]; [0x0bdc5e64] = GetTickCount()   # 0x018524f2
++[0x0bdc5ebc]                              # rendered-frame counter
drawn = scene render (3: 0x01857ed9, 5: 0x018576b3, 6: object vcall or 0x0185916b)
if drawn: SwapBuffers(hdc)                  # 0x01852653
elapsed = [0x0bdc5e64] - prev               # time between frame starts
if elapsed < 40:                            # 0x01852668 cmp [ebp-0x28], 0x28
    Sleep(40 - elapsed)                     # 0x0185267a
    [0x0bdc5e64] += 40 - elapsed
    elapsed = 40                            # 0x0185268d
[0x0bdc5ec0] = acc + elapsed                # 0x018544aa
```

Because the slept time is added to the saved tick, `elapsed` measures the work time
of the previous frame. Two consequences follow:

* Frames are paced to at least 40 ms. When a frame takes longer, nothing waits; the
  extra time goes into `acc`, and the next frame runs more 40 ms logic steps to catch
  up.
* Logic is fixed-step at 25 Hz and decoupled from rendering. That is reading, not a
  run.

Two instructions in this function leave `main.exe`:

* `0x01851d5e call 0x10b7c7b0` at entry;
* `0x018526e7 jmp 0x10b47590`, right after the cap.

Both targets fall inside `IGC.dll`'s image (preferred base `0x10000000`, SizeOfImage
`0x165c000`). `IGC.dll` is WinLicense-protected and was not captured, so what those
hooks do is unknown. The bytes after the `jmp` do not decode as straight-line code. The
cap instructions themselves sit before the hook and were captured after the hooks
were installed.

**Timing sources** (raw call counts in the text):

| API | Slot | `FF 15` calls | Use |
|---|---|---:|---|
| GetTickCount | `0x01a7c49c` | 279 | frame pacing (`0x018524f2`), many game timers |
| timeGetTime | `0x01a7c9a4` | 131 | interval gate `0x01851a3c`, wall-clock float `[0x06fce370]` = `(float)timeGetTime()` and FPS counter in `0x012aeb2b`, timer fallback |
| QueryPerformanceCounter / Frequency | `0x01a7c210` / `0x01a7c214` | 17 / 9 | timer class `0x0118648a` (ctor), `0x01186606` (elapsed), used for the login/char-select camera timer `[0x06fc9c7c]` |
| Sleep | `0x01a7c4a0` | 20 (+24 register loads) | **only `0x0185267a` is in the frame path**; others are networking/loader threads |
| timeBeginPeriod | `0x01a7c97c` | 1 | only in `0x0118648a`, and only when QueryPerformanceFrequency fails |
| SwapBuffers (gdi32) | `0x01a7c148` | 3 | `0x011e2d5b`, `0x01851c9a`, `0x01852653` |

The client does not raise the timer resolution on the normal path. On native
Windows, `Sleep(40 - elapsed)` therefore rounds up to the default scheduler tick,
while Wine sleeps close to the requested milliseconds. That is an inference about
platform behaviour, not a measurement.

## 2. The frame cap and how the owner could change it

* **Value.** 40 ms gives 25 FPS. It matches the observed 25 FPS menu cap.
* **Where it is stored.** The value is three immediate operands in the code. No
  config, data or server value feeds it:

| Instruction | Bytes | Immediate byte address |
|---|---|---|
| `0x01852668 cmp dword ptr [ebp-0x28], 0x28` | `83 7D D8 28` | `0x0185266B` |
| `0x0185266C jge 0x01852694` | `7D 26` | (branch over the Sleep) |
| `0x0185266E push 0x28` | `6A 28` | `0x0185266F` |
| `0x0185268D mov dword ptr [ebp-0x28], 0x28` | `C7 45 D8 28 00 00 00` | `0x01852690` |

The 44-byte block `0x01852668..0x01852694` has SHA-256
`37978e18…a52e14`. The fixed logic step uses separate immediates: `0x01851D6E`
(`83 7D CC 28`) and `0x01851F92` (`83 E8 28`). **Leave those two unchanged.**

**No file patch is possible.** The first section of `main.exe` is packed (file
entropy 7.98 bits/byte; Themida sections `.themida`/`.boot`). Neither the 44-byte
block nor its first 12 bytes occur anywhere in the 32,229,376-byte file (checked by
`--game-root`). Searches for a config key found none: `config.ini` `[Performance]
Enable` is not referenced by any ASCII or UTF-16 string in the captured sections.
`LauncherOption.if` holds window and resolution settings only. The cap is not
server-sent: the code compares against immediates.

**A minimal runtime patch the owner could apply** (not done here). The owner already
loads an `opengl32.dll` proxy (mugl) into `main.exe`. By its first `wglSwapBuffers`
call the code is unpacked. The proxy could then do three things:

1. Verify that the 44 bytes at `0x01852668` equal the block above. This proves the
   same build and that nothing else has patched it.
2. `VirtualProtect` the page to writable and write the new cap `N` (1..127 ms) to the
   three immediate bytes `0x0185266B`, `0x0185266F` and `0x01852690`. Then restore
   the protection and call `FlushInstructionCache`. For example, N = 16 caps at about
   62 FPS.
3. To remove the cap entirely, write a single byte instead: `0x0185266C` from `7D` to
   `EB`, so the Sleep is always skipped. Elapsed then stays the real frame time.

All three immediates must change together. Otherwise `Sleep(N - elapsed)` and the
accumulator disagree.

Risks and expected effect:

* **Integrity checks.** `IGC.dll` hooks this very function, and Themida/WinLicense
  may checksum code. Neither is known, so test on the owner's own server.
* **Little gain in the world.** The in-world rate (about 17 FPS) is already below the
  cap. Raising the cap only helps scenes whose frame work is under 40 ms, such as
  login, server select and character select.
* **Anything advanced per rendered frame speeds up.** The rendered-frame counter
  `[0x0bdc5ebc]` is incremented once per frame and read at 225 sites, mostly in the
  effect routines `0x016e036c` and `0x0176ce74`. By contrast:
  * the logic-step counter `[0x0bdc5eb0]` (30 readers) stays at 25 Hz;
  * the wall-clock float `[0x06fce370]` used for terrain UV scrolling stays real-time.

  Whether model animation (the tick `0x012b4dd3`, see [skinning](client-skinning.md))
  runs in the logic step or in the render was not traced. Some animation or effect
  speed change at higher caps is therefore likely but unmeasured.

## 3. GL_TRIANGLE_FAN and GL_QUADS routines

All 51 sites are listed with function, return address (`site + 6`, the value a
GL proxy sees at `[esp]` inside glBegin), immediate-mode calls and raw callers in
`static-02.json`. Counts below are the script's.

**Terrain (9 fans + 1 quad).** `0x016cd468` is the terrain render. The main render
calls it once per frame (arg 0), plus an optional picking pass (arg 1) that ray-tests
tiles and draws nothing. It walks the frustum bounding box (`0x016cbe7b`; tiles of 100
units, 4-aligned, clamped to 0..251) in 4×4-tile blocks:

* `0x016d2e8e` handles a block;
* the block test is `0x016ccce7`;
* the per-tile test is inside `0x016d2d81`;
* per tile, `0x016ccda5` builds corners and calls `0x016cff65`.

It does this in an opaque pass (`[0x0b5e3ea0] = 0`) and a second pass with
`[0x0b5e3ea0] = 2`.

Each tile face is `bind(0x7630 + layer)` (cached), then `glBegin(GL_TRIANGLE_FAN)`,
then four corner emitters, then `glEnd`. Each corner emitter (for example
`0x016d36b1`) calls:

* `glTexCoord2f(uv[c])` from `0x0b6b5384`;
* `glColor3fv(light ∘ dynamic light)` from the 256×256×12 arrays `0x0b9f5430` and
  `0x0bc35430`;
* `glVertex3fv(&corner[c])` from `0x0b6b5318`.

The tile index is `y*256 + x` (`0x016d34cd`).

| Function | Fan sites | Reading |
|---|---|---|
| `0x016cf46c` | `0x016cf64a`, `0x016cf6c5`, `0x016cf9b6`, `0x016cfa31`, `0x016cfaad` (main: return `0x016cfab3`) | layer face; per-world special layers and alpha/blend wrappers |
| `0x016cfada` | `0x016cfb0e` | layers `0x64`/`0x65` with alpha or additive blend |
| `0x016cfb31` / `0x016cfb70` | `0x016cfb4d` / `0x016cfb89` | alpha / additive faces with alternate corner sets |
| `0x016cfbac` | `0x016cfce0` | neighbour-dependent face, texture `0x7723` |
| `0x016cff65` | quad `0x016d16b9` | grass: texture `0x7694 + layer1 byte [0x0b735420+tile]`, column offset table `0x0b5f4ea8` |

**Terrain decals (1 fan).** `0x016cdd5f`, with 460 raw callers, projects a texture
onto the terrain. It sets the colour and rotation, binds once, loops over the covered
tiles (visibility `0x016d2050`) and emits one 4-vertex fan per tile through
`0x016d197d` (site `0x016d1f0a`). Its callers were not individually classified;
shadows, auras and magic circles are the likely users (inference).

**2D (11 fans, 2 quads).** These run under the 2D projection helper
`0x0184f793`/`0x0184f8d7`. Each draws 4 corners in a loop: optional glColor4f or
glColor4ub, glTexCoord2f, then glVertex2f.

* `0x0184dcb1` (textured): 243 raw callers in 76 functions;
* `0x0184d9bb` (untextured colour): 170 / 60;
* `0x0184f4ba`: 31;
* `0x0184e34d` (rotated): 29;
* `0x010ae63d`: 29, two sites;
* `0x0184e01a`: 6;
* `0x0184e72b`, `0x0184eb8a`, `0x0184f036`, `0x0107ba6b`: no direct callers.

The two 2D quads are `0x009fef9f` and `0x0158c495`.

**3D effects and misc (3 fans, 21 quads).**

* `0x0184c39c`: billboard sprite quad, 445 raw callers, 433 of them in `0x0159123f`
  (the sprite/particle pass called twice by the main render);
* `0x0184c121`: 13 callers;
* `0x0184ca6b`: 13 callers;
* the effect quad/fan routines in `0x01589b56..0x015909cc` and `0x01534b4c`/`0x0153518b`:
  segment strips at one fan per segment, and unrolled 20- and 24-vertex shapes;
* bone-attached quads `0x01537498`;
* an object's virtual draw `0x00fd8bc2` with 7 quad helpers;
* a six-face box `0x0184b807`;
* flat quads `0x009888bf` and `0x0107c555`;
* the fan `0x009f8fd4`.

**Plausible per-frame share (inference, not measured).**

* **Terrain.** Each visible tile issues one opaque face plus faces for extra layers
  in the second pass, and a grass quad where grass applies. A few thousand visible
  tiles times one to three faces gives several thousand to roughly 15 thousand fans.
* **Decals.** Each decal adds (covered tiles) fans. A busy PvP spot with many
  characters could add thousands.
* **2D UI.** One fan per element, typically hundreds.
* **Quads.** Most come from sprites and particles (`0x0159123f`) and grass.

The profile's roughly 20k four-vertex fans is consistent with terrain plus decals
dominating, but this split is not established. A cheap way to establish it is to have
the proxy count glBegin calls keyed by `[esp]` and map the return addresses through the
table in `static-02.json`.

The large `GL_TRIANGLES` blocks (about 1,800 per frame) are one per skinned mesh from
`0x012b8d1d` ([skinning](client-skinning.md)).

## 4. Buffer objects

**How the client reaches the VBO functions.** `main.exe` contains no
`glBufferSubData` name string. Buffer calls go through a block of 49 data-import
slots, `0x01a7cb54..0x01a7cc14`. Each slot holds the address of a function-pointer
variable, and the code calls it as `mov eax,[slot]; call [eax]`. The pointed-to
variables lie at `0x62ae4d10..0x62ae6af1`. That is consistent with a GLEW-style
`glew32.dll` (its customary base is `0x62aa0000`), but the DLL is not in the client
folder and was not identified.

Names are inferred from the pushed arguments:

| Slot | Name | Argument evidence |
|---|---|---|
| `0x01a7cb58` | glBindBuffer | `(0x8892, id)`; 22 uses |
| `0x01a7cb80` | glBufferSubData | `(0x8892, 0, size, data)`; 2 uses |
| `0x01a7cb84` | glBufferData | `(target, size, data, usage)`; 7 uses |
| `0x01a7cbcc` / `0x01a7cb88` | glGenBuffers / glDeleteBuffers | `(1, &id)` |
| `0x01a7cc14` / `0x01a7cc04` | glMapBuffer / glUnmapBuffer | `(0x8892, GL_WRITE_ONLY)` / `(0x8892)`; wrappers `0x00a926a5` / `0x00a926d0` have no direct callers |
| `0x01a7cb68` | glVertexAttribPointer | `(index, size, GL_FLOAT, 0, stride, offset)` |
| `0x01a7cb6c` | glActiveTexture | `(0x84c0..0x84c3)` in `0x00fed5db`, `0x00ffdcba`, `0x00ffdd30` only |
| `0x01a7cc00` | glUseProgram | `(program)` and `(0)` |

The game also requests ARB names itself: `0x00a79534` checks
`GL_ARB_vertex_buffer_object` and nine entry points, and `0x00adc163`/`0x00c8fb9d`
request the framebuffer names.

**Stream VBOs: the JSON effect system.** The nearby code reads the effect JSON keys
(Type, Looping, Duration, Billboarding, TexCoord, Blending, MaxParticle,
SpaceIsLocal, Bursts, `EffectManager`). The helper class `0x00a92497` creates the
buffer:

| Buffer object | Creator | Size | Usage | Stride / flags | Draw method |
|---|---|---:|---|---|---|
| `0x01d1e2c8` | `0x00a6fe5d` | 144 (4 vertices) | GL_STREAM_DRAW | 36 / `0xb` (vertex, texcoord, colour) | sprite `0x00a6ebd1` (vtable `0x01a80844` slot 1) |
| `0x01d1e6f8` | `0x00a8a3ea` | 144,000 (1,000 quads) | GL_STREAM_DRAW | 36 / `0xb` | emitter `0x00a88720` (vtable `0x01a81d0c` slot 1) |

Per draw, both methods:

1. set the state (texture enable, three blend choices);
2. bind the buffer and enable the vertex, texcoord and colour client arrays with
   `glVertexPointer(3,…,0)`, `glTexCoordPointer(2,…,12)` and
   `glColorPointer(4,…,20)` (`0x00a92542`);
3. update the buffer:
   * **sprite:** `glBufferSubData(GL_ARRAY_BUFFER, 0, 144, verts)`, a whole-buffer
     update; or
   * **emitter:** allocate `n*4` vertices on the heap, fill them, and
     `glBufferSubData(GL_ARRAY_BUFFER, 0, n*144, verts)`, a prefix update;
4. `glDrawArrays(GL_QUADS, 0, 4)` or `(…, 0, 4n)`;
5. unbind and disable the arrays (`0x00a92631`).

The emitter also wraps the draw in `glMatrixMode(GL_MODELVIEW)`, glPushMatrix,
glMultMatrixf and glPopMatrix when its local-space byte `+0xf0` is set.

About 550 `glBufferSubData` per second at about 17 FPS is roughly 32 effect draws per
frame. The partial updates are the emitter's prefixes.

**Other VBO users** (rarely or not shown in the profile):

* **Static meshes.** `0x01006867` uploads `GL_STATIC_DRAW` vertex and index buffers
  (keys `Vertices`, `Indices`, `Subsets`). Five GLSL paths draw them with
  `glDrawElements`: `0x00ccae46`, `0x00fe849a`, `0x00fe9519`, `0x00fecdb4` and
  `0x00ff8e59`.
* **Dynamic GLSL paths.** `0x00fea83b`, `0x00fef3bd`, `0x00ff24c5` and `0x00ff5953`
  respecify the whole buffer with `glBufferData(…, n*36 or n*44, data,
  GL_DYNAMIC_DRAW)` before each `glDrawArrays`.
* **A third-party renderer** at `0x0060e000..0x00613000` loads its own ARB table into
  object fields `+0x2164..+0x21e4`, including `glBufferDataARB`, ARB programs,
  YUV→RGB fragment programs and Flash-style colour-transform programs. It also has its
  own glViewport/glOrtho method `0x00612340`. Which product it is was not established.

## 5. Implications for an OpenGL batching layer

* **Terrain is the main batching target.** Its fans are uniform: 4 vertices, each
  with texcoord, colour and position, and one cached texture bind per tile face.
  Consecutive tiles that share a texture and state merge into one draw. That is what
  mugl does now.
* **Terrain could be reordered.** Within the opaque pass, tiles do not overlap, so
  sorting the faces by texture before submission would not change the image. Within
  the second pass the same holds per pass, but the pass order must be kept. Both are
  inferences from the depth layout, not tests.
* **The terrain geometry is static.** A 256×256 grid with fixed tile corners could be
  kept as an indexed VBO, with only the per-vertex colours (light times dynamic light)
  and the animated UVs (water layers scroll with wall-clock time) streamed per frame.
  Doing so needs a client-side change or a proxy that recognises the fans from these
  return addresses.
* **Decal and 2D fans also merge.** Decal fans share one bind per decal. UI fans
  change texture often, but they are already 4-vertex quads.
* **Effect VBO draws** are `GL_QUADS` with client arrays from a VBO. A proxy can
  treat them in two ways:
  * copy the 144 or `n*144` bytes, which it already has through BufferSubData, into
    its own batch, so that consecutive same-state effect draws merge;
  * keep them as VBO draws but orphan the buffer on every offset-0 update. The draw
    after each update reads only the prefix just written, so orphaning the 144,000-byte
    buffer on prefix updates is safe. The current mugl orphans only full-size updates
    (`off == 0 && size == buffer size`), which covers the sprite buffer but not
    emitter prefixes.
* **Inherent state changes:**
  * per-mesh texture, blend and cull from the mesh draw flags;
  * terrain texture changes between tiles;
  * effect blend modes;
  * the 2D projection switch.

  The client's state wrappers (`0x0184a6b7..0x0184acf6`) already deduplicate
  depth, cull, blend and texture.
* **Elidable state changes:** glPushMatrix/glPopMatrix pairs with no matrix call
  between them, such as the model body `0x012bb35a`.
* **Unattributed calls.** Main's captured code does not explain about 600
  glViewport+glOrtho and 1,900 glActiveTexture calls per frame:
  * main has 8 glViewport sites, 5 glOrtho sites and 17 calls of its 2D helper;
  * glActiveTexture is reached only from the three shader paths above.

  The candidates are `IGC.dll` (packed, hooks the frame driver and the UI phase at
  `0x01859cf1 call 0x10b3e920`) and the third-party renderer. Attribute them by
  return address before optimising.

## Failed or rejected hypotheses

* **Alphabetical IAT order.** The data-import slots are not alphabetical: the
  `0x8d40` framebuffer bind precedes glBindBuffer. Names were therefore assigned only
  from arguments, and 39 of the 49 slots stay unnamed.
* **glBufferSubData requested by name.** The name occurs in neither captured section,
  and the VBO calls go through the data-import block.
* **A config-driven cap.** The `config.ini` `[Performance]` key is never referenced.
* **A cap in IGC.dll.** The cap's immediates sit in `main.exe`'s own captured code.
  `IGC.dll`'s hooks might still change timing; that is unverified.

## Unresolved

* Runtime counts per routine. All shares in section 3 are inference.
* `IGC.dll` hook behaviour and integrity checks. The provider of the data-import
  block. The third-party renderer's identity.
* Whether the model animation tick runs per logic step or per rendered frame.
* The callers of the terrain decal, the effect class names (RTTI type descriptors lie
  in the uncaptured third section), and scene names.

## Reproduce

```sh
./tools/python/bin/python scripts/client_frame_static.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --wine-dlls /extracted/libwine/usr/lib/i386-linux-gnu/wine/i386-windows \
  --game-root "$MU_GAME_ROOT" --output /new/local/frame.json
```

The report takes about 30 s on one core. The local report is
`evidence/client-frame/static-02.json` (SHA-256 `9627bb4f…0abe`), ignored, in the
frameloop worktree. The extracted DLLs and the scratch scripts are under the same
directory.

`tests/test_client_frame_static.py` has eight portable checks:

* multi-DLL slot naming and refusal of unpinned DLLs;
* slot call, thunk and load search;
* exact cap-immediate and instruction-text reading;
* glBegin mode, return address and vertex calls;
* non-immediate glBegin modes;
* pointer-slot arguments;
* buffer creation parameters.

A ninth, private check (`MU_RECOVERY_INTEGRATION=1`, optional `MU_GAME_ROOT`) pins the
counts and values above.
