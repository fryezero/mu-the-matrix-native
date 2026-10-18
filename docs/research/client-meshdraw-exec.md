# Mesh draw executed under Unicorn (CLIENT-MESHDRAW-EXEC-001)

The client's mesh draw `0x012b8d1d` (`ret 0x2c`) and its body `0x012bb35a`
(`ret 0x2c`) now run under Unicorn on the pinned restored text, together with
every client routine they reach. Each OPENGL32 call they make is recorded with
its arguments. The recorded stream is compared, call for call and bit for bit,
with the platform-neutral C port in `native/core/mu_meshdraw.c` that the native
viewer draws with. The comparison also covers the final GL caches, the final
model colour, and the light-colour and normal-texcoord tables each draw wrote
by the time it reached `glBegin`.

| Comparison | Cases | Matching | GL records |
|---|---:|---:|---:|
| Synthetic viewer cases (3 models x 69 option sets) | 207 | 207 | |
| Mutated client-only inputs (skin textures, types, sub-objects, caches, bitmaps with pixels) | 500 | 500 | |
| Synthetic total | | | 111,626 |
| Installed BMDs, 30 per folder (122 folders) | 2,713 | 2,713 | 6,921,466 |
| Pinned CI cases (`pinned_cases`) | 247 | 247 | |
| Texture-name parser `0x01185111`: synthetic / installed names | 4,038 / 9,461 | all | |

Every one of the 64 branch probes in the routine and body was reached. All four
negative controls fail: a changed model colour, time, flag word or vertex bit on
the native side is detected. A port with one constant and one condition changed
fails 11 of 237 cases. Of the sampled installed files, 54 were skipped:
reader-rejected, without meshes, or above the 50-mesh/15,000-entry transform
buffers.

The port's previous open question is closed. The loader writes the mesh
`+0x00` byte as 0 and builds the `+0x1c` record from the texture name; the
name parser itself runs in the comparison.

## Identity

| Input | Bytes | SHA-256 |
|---|---:|---|
| Restored text at `0x00401000` (capture09) | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | 2,557,764 | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Trig dispatch flag `0x0bdd1cc8` (value 1) | 4 | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |
| Math feature word `0x01cf6618` (value `0x2f`) | 4 | `bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9` |

Pinned bodies (the validator refuses to run if any differs):

| Body | Range | SHA-256 |
|---|---|---|
| Mesh draw | `0x012b8d1d..0x012bb35a` | `d19663bdf961b7a6e0adc64ccfb42c935844b40933bb056aa4bc739a3d611660` |
| Body | `0x012bb35a..0x012bb69c` | `8d5686a756fccab0e405b5de3c4b13a51f65ee577ab64e81c5e1b2da5be910ee` |
| GL state wrappers | `0x0184a699..0x0184ad4c` | `e8cb568d580fd0f843e1945e168238eb6fd3537e12dbc2745c82e0eb16f46536` |
| Push/pop matrix | `0x012b7e53..0x012b7e75` | `d947e7048e74d840672941c67c7fab226a9aaf28ba6020419a748fbad582b05c` |
| Vector accessors | `0x00cfc922..0x00cfc956` | `c4d7b5227dd926d12a4052e70553726b62eef04e091aa4581be6dc0bba88d345` |
| Sub-object flag getters | `0x012bd7e9..0x012bd829`, `0x00d99f0d..0x00d99f1c` | `bc211fea…ac7d5f`, `c476f28e…fa9bc` |
| sin / cos / pow wrappers | `0x00968117`, `0x009fa20d`, `0x009f4218` | `ca2de52b…eca579`, `1195ca41…cf3c94c2`, `824c6111…124bf36` |
| Colour scale, vector scale, assign, copy, destructor | `0x00cfcd74`, `0x00cfcb3c`, `0x00cfc8f2`, `0x009fa1cb`, `0x0095eda9` | in `scripts/validate_meshdraw.py` |
| Texture-name parser | `0x01185111..0x01185327` | `4f9d53101640a0cbf20afa026c3d59e62c0121eb9eb3ab4828bf7ae2af40cb1a` |
| CRT strchr, strcmp, strcspn, strlen, strtok, strtok_s, cookie check | `0x0194ce60`, `0x0195a3d0`, `0x0195a460`, `0x0195a4b0`, `0x01983c08`, `0x01986dac`, `0x0191cd7c` | in `scripts/validate_meshdraw.py` |

The CRT sin/cos/pow bodies behind the wrappers (`0x01985700`, `0x0198c4d0`,
`0x0198c480` and their SSE2 kernels) run from the pinned text; they are covered
by the text digest, not pinned separately.

## Method

`scripts/validate_meshdraw.py` maps the text and the second section read-only,
the captured trig flag and feature word, and a stub page at the OPENGL32 slot
targets. A hook on the stub page records each call (`glColor3fv`/`glVertex3fv`
pointer arguments are read at call time), pops the stdcall arguments and returns.
Any unmapped access, write to the image, unexpected import, wrong stack balance,
changed callee-saved register or unrestored SEH chain stops a case.

Inputs come from mesh-draw case files (`native/core/mu_meshdraw_case.h`). The
viewer writes one per model and option set (`mu-render corners --case-out`), and
the validator mutates them. The validator lays each case out as client memory:

* the model object and its mesh records;
* the texture tables and sub-object bytes;
* the transform outputs at the default buffers;
* the colour table `0x089c2120` and the texcoord table `0x072acfd8`, poisoned
  with `0xff` so that any read of an unwritten entry shows;
* the globals: time `0x06fce370`, environment vector `0x0a381de0`, skin base
  `0x0b6b53e0`, and the GL caches.

`mu-render replay` runs the same case through the port.

Modelled, not client code:

* the two bitmap lookups `0x00c97c2d` / `0x00ebbec8`, which are `std::map`
  searches. They return the declared bitmap records. A miss returns a zeroed
  record, as the client's miss path does (it clears and returns the static
  record `0x01ec3030`; static reading `0x00c97ca6..0x00c97cd5`);
* the case memory and the initial GL caches;
* a TEB whose SEH head the routine saves and restores;
* the CRT `_getptd` (`0x019a4ba6`) for strtok's per-thread position;
* in the math sweep only, the CRT fast-math word `0x0bdcfbc8`, set to 0. The x87
  fallbacks read it; no draw case reaches them.

Run (9 min 40 s with the installed corpus on this Mac):

```sh
./tools/python/bin/python scripts/validate_meshdraw.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --flag evidence/trig-state-15/captures/late/math-dispatch-flag.bin \
  --feature evidence/x86-math-capture-09/cpu-features.bin \
  --game-root "$MU_GAME_ROOT" --per-folder 30 --mutations 500 --math-sweep 200000 --output report.json
```

The private test `test_private_client_mesh_draw_execution` runs a smaller
configuration (3 per folder, 300 mutations, 20,000 math samples; about 10 minutes).

## Verified by execution

These are equal between client and port in every case above. The rules are
stated in the port's comments, at the client address of each block.

* **Mode from flags.** The routine never takes a mode argument; it derives one.
  Flag `1` gives the flat path. Otherwise any of `4, 8, 0x200, 0x800, 0x1000,
  0x4000, 0x8000, 0x10000, 0x20000, 0x80000, 0x100000` selects the environment
  group, whose mode is 4, 0x1000, 0x80000 or 0x8000 in that order of precedence.
  Next come the highlight pass (select `<= -2`, or select equal to the texture
  slot), textured (`2`), untextured additive (`0x40`), or no state at all.
* **State.** These are the cached wrappers `0x0184a6da..0x0184acf6`, with their
  exact GL calls and cache updates. The fog wrapper behaviour depends on the fog
  setting byte, which the cases vary.
* **Environment group.** Early returns for the sub-object `[3]` byte, the mesh
  flag `+0x00` and textures `0x7724..0x7909`. Then the normal-indexed texcoord
  table at `0x072acfd8`, written inside the routine (`0x012b9bb3..0x012ba3ef`) for
  every flag variant: `0x200`, `0x800` (environment vector), `0x1000`/`0x4000`
  (cos/sin of time), `0x10000`, `0x20000`, `0x100000`, `0x80000` (raw normal),
  `4`, and the default. The previous viewer placeholder (0.5 + 0.5·normal) was
  wrong. Then the colour pre-scale for alpha < 0.99, and the environment
  bitmaps `0x7fcf`, `0x800b`, `0x800c`, `0x8005`, `0x7f1f`, `0x7f66`.
* **Texture substitutions.** `0x791a` returns. The skin textures `0x7725`,
  `0x77c7`, `0x7818`, `0x7869`, `0x7776` and `0x78ba` are shifted by `+0xa4` and
  use the alternate colour. `0x76f8` adds the skin base. The override argument,
  the `+0xa5`/`+0xa6` flags, and the texture types 1 and 2 with `+0x40` are all
  covered. So are the colour restores after `glEnd`.
* **uv offset.** It is applied when the mesh equals the select argument, or the
  model's `+0x94` mesh (replaced by the mesh itself when the sub-object `[2]`
  byte is set), and either offset is nonzero. NaN counts as nonzero.
* **Per-corner variants.** The planar projection `0x20`, the wave `0x400`, and
  the corner skip `0x200000`.
* **Mode 0x8000.** Alpha comes from one texel of the override bitmap:
  `1 - pow(texel/256, 2)`, at byte `(u·w + v·h·(w-1))·3` of the pixel buffer.
* **Body.** glPushMatrix, then every mesh except `skip`. Sub-object `[1]` hides
  a mesh, `[0]` passes the mesh as select, and `[4]` = 1/2 adds a black outline
  draw with flags `0x21`/`0x22` and colour reset; then glPopMatrix.
* **NaN alpha** takes glColor4f (comiss/jb). Out-of-range time takes
  `cvttss2si`'s `0x80000000`.

**Math.** The routine consumes the CRT's sin/cos/pow after the wrappers round
them to binary32. The port uses `(float)sin((double)x)`, `(float)cos(…)` and
`(float)pow(…)` from the host libm.

| Arguments | Calls | binary32 differences | Through the x87 fallback (not evidence) |
|---|---:|---:|---:|
| sin, 0x400 wave `(float)(int32)·0.007`, full int32 range | 200,000 | 0 | 198,836 |
| sin, 0x400 wave, `|int| < 2,000,000` | 200,000 | 0 | 0 |
| sin, `time·0.002`, `|time| < 10^7` | 200,000 | 0 | 0 |
| cos, `time·0.001` | 200,000 | 0 | 0 |
| sin, random float bit patterns in `[0, 2^31)` | 200,000 | 0 | 18,555 |
| pow, `(t/256)^2` for every texel t | 256 | 0 | 0 |
| In the draw cases themselves (sin / cos / pow) | 104,998 / 2,827 / 18 | 0 | none |

In binary64, the CRT results differ from macOS libm in the last bit for about
4% of sin and 3% of cos calls (4,257 of 104,998 sin and 97 of 2,827 cos calls
in the draw cases). After binary32 rounding, none differed. The CRT uses its SSE2 kernels for `|x| < 90,112`
and the x87 fallback from there on, a boundary found by bisection and then
checked on 40,000 random arguments on each side. A binary32 difference remains possible when a result
lies within one binary64 ulp of a binary32 rounding boundary: about 2^-29 per
call whose binary64 result differs. For large arguments the SSE2 kernels hand over to
x87 `fsin`/`fcos`/`fyl2x`. Unicorn (QEMU) evaluates those instructions with
the host libm, so equality there says nothing about hardware x87. The draw
cases never reached them. In game, the 0x400 wave argument
`(cvtt(time) + vertex·0x3a3)·0.007` reaches 90,112 once the sum exceeds about
12.9 million. That takes about 3.6 hours of client time at vertex 0, and less
for higher vertex indices. The `0x1000`/`0x4000` arguments reach it after
about 12.5 hours (`time·0.002`) and 25 hours (`time·0.001`).

## Texture-name sub-object records (`+0x1c`)

The BMD loader `0x012b3812` writes each mesh record's fields from the file
(`0x012b3e53..0x012b3ed7`). It writes `+0x00` as 0 (`0x012b3edd`). After
copying the 32-byte texture name to model `+0x34 + mesh·0x20`
(`0x012b406b..0x012b4083`), it constructs a 6-byte object (`0x010a82be`) and
calls the parser `0x01185111` on the name. When the parser returns nonzero, the
loader allocates 5 bytes, copies bytes `[0..4]` (`0x011850cc`) and stores the
pointer at `+0x1c`; otherwise it stores 0 (`0x012b40c5..0x012b4130`). This
wiring is a static reading; the loader as a whole remains unexecuted
(client-model-loader.md).

The parser was executed on every synthetic and installed name, in both CRT
strchr paths (SSE2 and scalar). The port `mu_meshdraw_sub_from_name` matches in
every case:

* `strcmp` with "master10_center.jpg", "lightning_4sq.jpg", "fire_sq.jpg" or
  "s195.tga" gives `{0,1,0,0,0}`: the body skips the mesh.
* Otherwise, from the first `_` (strchr on a local copy followed by `"RHSN\0"`
  on the stack), `strtok(p, ".")` ends the token at the next `.`. Up to four
  characters after the `_` are read. `R` sets `[0]`, `H` sets `[1]`, `S` sets
  `[2]` and `N` sets `[3]`. Any other character ends the scan with no record,
  except for the name "mu_rgb_lights.jpg", which gives `{1,0,0,0,0}`.
* `[4]`, which selects the body's outline passes, is never set from a name. Its
  two cases compare a sign-extended byte with `0x4443`/`0x4454` and cannot
  match. The outline passes therefore need another writer, which was not
  searched for.

Installed names: 9,461 distinct, 820 with a record, 6 of them hidden.

## Static readings (not executed)

* **Scene setup** `0x0184adc7`:
  * `glDisable(GL_ALPHA_TEST)`, then glEnable for `GL_TEXTURE_2D`,
    `GL_DEPTH_TEST` and `GL_CULL_FACE`, then `glDepthMask(1)`, with the matching
    caches (`0x0184afe1..0x0184b031`). The port's `mu_gl_cache_scene_defaults`
    follows this.
  * `glDepthFunc(GL_LEQUAL)` at `0x0184b03d` and
    `glAlphaFunc(GL_GREATER, 0.25)` at `0x0184b056`.
  * Fog depends on the byte `0x0bdc597c`. When it is set: glEnable(GL_FOG),
    `glFogi(GL_FOG_MODE, GL_LINEAR)`, glFogf(GL_FOG_DENSITY) from bss
    `0x01cf160c`, and glFogfv(GL_FOG_COLOR) from `0x01cf1610`. When it is clear:
    glDisable(GL_FOG). (The WIP commit message said GL_EXP; the immediate is
    `0x2601`, GL_LINEAR.)
  * All five absolute writes to `0x0bdc597c` store 0 (`0x01851c24`,
    `0x018576de`, `0x01857f0d`, `0x018591af`, `0x0185b124`). Indirect writes
    were not excluded.
* **Texture upload.** OpenTexture `0x0181fbe9`, the name resolver `0x0181fead`,
  and the loaders `0x00c982ea` (JPEG) and `0x00c988fc` (TGA). The rules are in
  `native/core/mu_textures.h`:
  * `t` names use the TGA rule: 32-bit pixels read raw from offset 22 of the
    `.ozt`, RLE and the origin bit ignored, rows flipped;
  * `j` names use the JPEG rule;
  * both use a power-of-two buffer and level 0 with no mipmaps;
  * filters are GL_NEAREST with GL_REPEAT for 1,045 of the 1,058 OpenTexture
    calls, and TGA is always GL_NEAREST.
* **Pixel buffers.** The loaders free the `+0x21a` pixel buffer after the upload
  (`0x00c98841..0x00c98892`, `0x00c98f0f..`). Bitmaps `0x7532`, `0x7def` and
  `0x7bd1` keep theirs, and so does `0x851b`, JPEG only. Mode 0x8000 on any
  other bitmap therefore reads through a null pointer.
* **Body flags.** 797 of the 1,256 body-wrapper calls pass flags 2.

## Port conventions (authored, not client behaviour)

* A mesh whose indices fall outside the supplied counts, or that has more than
  15,000 normals, is refused before any call (`MU_MESHDRAW_REFUSED`). The client
  bounds nothing.
* `MU_MESHDRAW_FAULT`: at a mode 0x8000 texel outside the pixel buffer, the port
  stops where the client would read outside memory. Everything up to that
  corner has been emitted, with no glEnd, and the body and case runner stop. The
  validator detects the same read at `0x012bad8a` and compares the stream up to
  it. 17 synthetic and 71 installed cases end this way. The viewer keeps no
  pixel buffers (the client frees them), so mode 0x8000 always faults there.
* The bitmap lookup is a callback. Explicit host pointers replace client
  addresses.
* Each viewer draw starts from the scene-setup caches with the model colour
  from the parameters; the client keeps both across calls.

## Native viewer use

The scene driver (`native/core/mu_scene.c`) builds the client inputs for a BMD:

* mesh `+0x00` = 0;
* `+0x1c` from the texture name;
* texture types 0, filled with 0 by the loader at `0x012b3e2e`;
* bitmap records with GL names, component counts, and no pixels.

It forwards the literal call stream. The GL backend re-applies the effective
state before each glBegin; the software rasterizer receives the same state. The
GL backend uses the client's per-texture filter and wrap (`--linear` overrides
the filter), GL_LEQUAL, alpha GREATER 0.25, GL_MODULATE, and fog off.

## Unresolved

* Live callers. For characters and items these are now traced by execution in
  [client-renderchar.md](client-renderchar.md) (NATIVE-RENDERCHAR-001). For other callers the actual flags, alpha, select and texture arguments, the model
  fields (`+0x44`, `+0x94`, `+0xa4..+0xa6`, `+0xca`, `+0xcb`), the texture types
  and the skin base in game are unknown. The validator covers their domains,
  not their live values.
* Other writers of mesh `+0x00`, `+0x1c` (in particular `[4]`) and the texture
  type table after load.
* Hardware x87 trig for huge arguments, the uninitialized power-of-two padding
  (zero here), the GL driver itself, and native Windows behaviour.
