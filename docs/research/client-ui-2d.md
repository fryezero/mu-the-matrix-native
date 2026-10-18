# The client's 2D interface layer (NATIVE-UI-001)

This finding covers the 2D layer of the pinned client:

* how interface textures are loaded;
* the 2D projection;
* the bitmap, colour and sprite quads;
* the GDI text path.

It reconstructs these routines as C (`reconstructed/ui`) and checks them against the
client's own instructions in Unicorn. A native module (`native/core/mu_ui_*`) runs them
on macOS arm64, and `mu-render ui` renders two real screens headlessly:

* the title/loading screen, complete;
* the login scene's 2D overlay (logo and text).

Labels used below:

* **verified**: the client's instructions ran in Unicorn and their output matched the
  reconstruction word for word.
* **live**: compared with a window capture of the running game.
* **static**: read from decoded instructions only.

Pinned inputs are the same as in [client-frame-loop.md](client-frame-loop.md):

* `main.exe` SHA-256 `3cf91f3c…5527a`;
* restored text capture09 `2bd5f2e9…3724` at `0x00401000`;
* second section run10 `c985e2e6…a0672f` at `0x01a7c000`.

The third PE section (`0x01ced000`, the globals) is packed on disk and was not
captured. The validator models every global it needs and treats any other read from
that section as an error.

## Routines

| Address | Routine | Status |
|---|---|---|
| `0x0185baac` | `LoadBitmap(path, index, filter, wrap, check, fullpath)`: prefixes `Data\` and calls `CGlobalBitmap::LoadImage` `0x00c97730` on the table `0x0bdc5f00` | static |
| `0x00c97730` | `LoadImage`: if the index is already used, prints a Korean "same index used twice" warning. Dispatches on the extension: `jpg` goes to OpenJpeg, `tga` to OpenTga, anything else returns false | static |
| `0x00c982ea` | OpenJpeg: opens `<stem>.OZJ`, `fseek` 24, IJG libjpeg | verified |
| `0x00c988fc` | OpenTga: reads `<stem>.OZT` whole | verified |
| `0x0184a6b7..0x0184aa2b` | GL state wrappers with cache bytes `0x0bdc58b5`/`597c..5980` and blend mode `0x0bdc58c4` | verified |
| `0x0184acf6` | BindTexture with the cache `0x01cf1620`. Negative indices bind texture name `-index` | verified |
| `0x0184f793` / `0x0184f8d7` | BeginBitmap / EndBitmap | verified |
| `0x01850636` / `0x01850679` | ConvertX/Y: `(float)W * x / 640`, `(float)H * y / 480` | verified |
| `0x0184dcb1` | RenderBitmap(tex, x, y, w, h, u, v, uw, vh, scale, startScale, alpha) | verified |
| `0x0184d9bb` / `0x0184dc62` | RenderColor(x, y, w, h, alpha, mode) / EndRenderColor | verified |
| `0x0184e01a` (via `0x00ec52a9`) | RenderColorBitmap(…, colour): per-vertex `glColor4ub` | verified |
| `0x010ad7b2`, `0x010ad847`, `0x010add3c`, `0x010adfe4`, `0x010ae63d`, `0x00986f8a` | CSprite: ctor, Create, SetPosition, SetSize, Render, Show | verified |
| `0x00aac91b..0x00aacfd6` | CGaugeBar: ctor, Create, SetPosition, SetValue, Show, Render | verified |
| `0x011e230d` / `0x011e2c8c` | CreateTitleSceneUI / RenderTitleSceneUI | verified |
| `0x0119fcf6` | CUIRenderTextOriginal::Create: screen-size 24-bit top-down DIB section | static |
| `0x0119ff3e`, `0x011a0431`, `0x011a054e` | RenderText, WriteText, UploadText | verified |
| `0x0182a0da` | CreateFonts | verified |
| `0x01857ed9` | login-scene render (state 3), 2D part `0x01858108..0x018588ac` | verified (2D part) |

### Texture loading

**OpenTga (verified).**

* The OZT bytes are the 4-byte wrapper followed by a TGA. The client reads fixed
  offsets: width int16 at 16, height int16 at 18, bits per pixel at 20, pixels from 22.
* It ignores the id length, colour map, image type and origin bit.
* It requires 32 bits per pixel and width and height of at most 1024 (signed compare).
* The texture size is the smallest power of two that is at least the image size, with
  a 1024 cap and 1 for sizes of 1 or less.
* Rows are flipped (`dst row = h-1-y`) and BGRA becomes RGBA in an uninitialised
  `new[]` buffer.
* The upload is `glTexImage2D(…, 4, W, H, 0, GL_RGBA, …)`, then `glTexEnvf(MODULATE)`,
  then MIN/MAG filter and WRAP S/T from the arguments.
* The buffer is freed except for indices `0x7532` (font), `0x7def` and `0x7bd1`.
* The client reads past the end of short files. The reconstruction refuses them
  instead, and leaves the padding zeroed.

**OpenJpeg (verified).**

* The client's IJG libjpeg is linked statically: `jpeg_CreateDecompress` version 62,
  struct size 0x1b0, 123 messages. It runs unmodified in Unicorn. Only these are
  stubbed: `setjmp`, `malloc`/`free`, `getenv("JPEGMEM")`, the stdio file calls, and
  the client's `error_exit` (which longjmps, so OpenJpeg returns false).
  `output_message` is also stubbed; it only runs for warnings.
* Images larger than 1024 return **true without creating a bitmap**.
* The buffer is `texW*texH*3`. Each scanline is copied to `(scanline-1)*texW*3` with
  length `output_width*output_components`, and the copy stops once the total would
  exceed the buffer.
* Greyscale JPEGs (1 component) and CMYK JPEGs (4 components) are therefore copied
  with RGB strides. The reconstruction keeps this behaviour, but clamps the CMYK case
  that would overflow.
* The upload is `glTexImage2D(…, 3, …, GL_RGB, …)` with no TexEnv call. The buffer is
  kept only for index `0x851b` (and the TGA indices above).

### The 2D projection (verified)

BeginBitmap does the following, in order:

1. `glMatrixMode(PROJECTION)`, `glPushMatrix`, `glLoadIdentity`.
2. `glViewport(0, 0, W, H)`.
3. `gluPerspective(fov, W/H, near, far)` (globals `0x01cf1634/162c/1630`).
4. `glLoadIdentity`, then `gluOrtho2D(0, W, 0, H)`. The perspective call has no effect.
5. `glMatrixMode(MODELVIEW)`, `glPushMatrix`, `glLoadIdentity`, DisableDepthTest.

So 2D coordinates are window pixels with the origin at the bottom left. Every quad
helper converts from the client's top-left convention with `y = H - y`.

### Quads (verified)

**RenderBitmap.** The corners are `(x,y)`, `(x,y-h)`, `(x+w,y-h)`, `(x+w,y)`, drawn as
a `GL_TRIANGLE_FAN`. The texture coordinates are `(u,v)`, `(u,v+vh)`, `(u+uw,v+vh)`,
`(u+uw,v)`.

* `startScale` converts x and y from 640x480 units; `scale` converts w and h.
* When `alpha > 0`, every vertex is wrapped in `glColor4f(1,1,1,alpha)` …
  `glColor4f(1,1,1,1)`.

**RenderColor.** Always converts all four values and disables texturing.
`mode` 0 draws white with the given alpha; mode 1 draws black.

**CSprite.**

* Create:
  * corners are `(0,H')`, `(0,H'-h)`, `(w,H'-h)`, `(w,H')`, with `H' = WindowHeight / scaleY`;
  * texture coordinates are inset by half a texel (`0.5/texW`, `(w-0.5)/texW`);
  * the colour is RGBA 255 and the sprite starts hidden.
* SetPosition / SetSize honour the sizing datums: bit 1 anchors the right edge, bit 0
  the bottom edge. Tiled sprites also move their texture coordinates.
* Render emits `glColor4ub(r,g,b,a)` once and multiplies the vertices by scaleX/scaleY.

**CGaugeBar.** It is a tiled sprite. SetValue sets the width to
`(right-left)*now/total`, with `total >= 1` and `now <= total`, using unsigned 32-bit
arithmetic.

### Title/loading scene (verified, live)

`0x0185ad63` loads the 14 textures `0x7b81..0x7b8e`, all `GL_LINEAR`/`GL_CLAMP` except
`lo_lo.jpg` (`GL_REPEAT`). A flag from `0x0095f75d` selects `MuBattle_loading01..06`
instead of `lo_back_s5_im01..06`.

CreateTitleSceneUI lays out 13 sprites and the gauge:

| Sprite | Content | Placement |
|---|---|---|
| 0, 1 | top letterbox | 400x69 each, scale W/800, H/600 |
| 5, 6 | bottom letterbox | 400x100 at y 500 |
| 7..12 | background | 512/512/256-wide tiles in 1280-wide virtual space; the height comes from the window aspect |
| 2 | MU_TITLE | never drawn |
| 3 | `lo_121518` | hidden |
| 4 | webzen logo | 53x46 at (16, 8), unscaled |
| gauge | `lo_lo` | 4x15, rect (0,0,0x290,0xf), at (0x48, 0x21c) |

RenderTitleSceneUI draws, in this order:

1. camera setup `0x0184adc7` and `glClear(COLOR|DEPTH)`;
2. BeginBitmap;
3. sprites 0..12 except 2;
4. gauge SetValue/Render;
5. a timer reset when `now == 0`, and a hook `0x00aac477` while the timer is under 3 s;
6. EndBitmap, `0x0184b6dd`, SwapBuffers.

The validator runs both client functions end to end, with markers for the out-of-scope
calls.

### Text (verified for the client side, boundary for GDI)

**CreateFonts** sets `FontHeight` (`0x0b437bf4`) from the window width:

| Window width | FontHeight |
|---|---:|
| < 800 | 12 |
| < 1024 | 13 |
| < 1280 | 14 |
| < 1680 | 15 |
| otherwise | 16 |

It then calls `CreateFontA` four times. Every call uses `NONANTIALIASED_QUALITY`, the
charset byte from `0x01cf0c20`, and face `GlobalText[0]` except where noted:

| Font | Height | Weight | Face |
|---|---|---|---|
| normal (`0x06fc9ca4`) | FontHeight-1 | 400 | `GlobalText[0]` |
| bold | FontHeight-1 | 700 | `GlobalText[0]` |
| big | 2*(FontHeight-1) | 700 | `GlobalText[0]` |
| fixed | 12 | 400 | `GlobalText[18]` |

**RenderText(x, y, text, boxW, boxH, sort, outSize)** works as follows:

* It measures the text with `GetTextExtentPointA`. An empty string is measured as "0".
* It scales positions and the box by the screen rates (`0x06fbcd94/98`).
* It aligns by `sort`:
  * 1: clip on the right;
  * 2: clip on the left;
  * 3: centre;
  * 4: right;
  * 7: right of x;
  * 8: centred on x.
* The clip offset is a pixel count added to a byte offset. This is a client quirk, and
  it is kept.
* It optionally fills the background with RenderColor.
* Unless the text starts with `\n`, it draws `SetBkColor(0)`, `SetTextColor(0xffffff)`
  and `TextOutA(dc, 0, 0, text)` into the DIB.
* It then copies the result in 256-pixel chunks. The chunk count is
  `width/256 + 1`; the last chunk is `width % 256` pixels wide.

**WriteText** converts DIB pixels into the RGBA font texture (`0x7532`, loaded from
`Interface\FontInput.tga`):

* rows of 256 RGBA pixels, at most 0x8000 bytes;
* a pixel whose **blue byte is 0xff** becomes the text colour; every other pixel
  becomes transparent black.

**UploadText** clips to the window, re-uploads the whole font texture with
`glTexImage2D`, and draws it with RenderBitmap. Its texture coordinates are
`(n + 0.01)/texSize`.

GDI itself (`GetTextExtentPointA`, `TextOutA`, `CreateFontA`, the DIB section) is the
platform boundary. On macOS, `mu_ui_font` replaces it with CoreText:

* the cell height equals the `CreateFontA` height;
* advances are rounded to whole pixels;
* rendering is non-antialiased with a 50% threshold, white on black.

### Login-scene overlay (verified for the 2D part, live)

After the 3D login world, `0x01857ed9` does the following:

* It adds 0.02 per frame to a fade value `0x0bdc5b80`, capped at 10.
* It sets EnableAlphaBlend, then `glColor4f(fade-0.3)`, EnableAlphaTest(1),
  `glColor4f(fade)`.
* It draws `Logo\MU-logo_g.tga` (`0x7b1f`, colour `0x4cffffff`) and
  `Logo\MU-logo.tga` (`0x7b1e`), sized from the logo's image size:
  * centred horizontally;
  * at y = H·0.05, measured in 640x480 units, so the screen offset grows with H²/480;
  * with texture coordinates `(n-0.5)/texSize`.
* It draws three GDI lines with the normal font, white, without a background:
  * `GlobalText[454]`, right-aligned at x = 300;
  * `GlobalText[455]` from x = 300;
  * `sprintf(GlobalText[456], version)` at the right edge, x = `0x016bc355() - cx·480/H - 10`;
  * all at y = `479 - cy·640/W`.
* The version is five bytes at `0x01cf100c`, each minus `i+1`. The separator branch
  tests `i % 1` and never fires.
* It then calls the UI manager (`0x009fe825`/`0x009fe955`) and the cursor `0x01858c72`.
  These are not part of this slice.

## Validation

`scripts/validate_ui.py` runs each client routine in `scripts/client_ui_machine.py`:

* Unicorn over the pinned captures;
* a flat GDT with FS pointing at a TEB;
* import slots redirected to recording stubs;
* an explicit table of client-function stubs, each with its own stack cleanup;
* an execution allowlist;
* a read of any undefined global or heap byte stops the case.

It compares the recorded OpenGL/GLU/GDI calls with the reconstruction's calls word for
word. Texture uploads are compared by SHA-256.

The full run (`MU_GAME_ROOT` set, seed 1) took 6.9 min on one core on 2026-10-17:

| Area | Cases |
|---|---:|
| RenderBitmap + RenderColor + EndRenderColor | 48 |
| state wrappers, projection and bind cache from all 64 cache-flag combinations × 3 blend modes, including final flag state | 192 |
| CSprite create/position/size/show/render | 160 |
| title scene (8 window sizes × 5 progress values) | 40 |
| RenderText/WriteText/UploadText (8 window sizes, 8 sorts, clipping, backgrounds, multi-chunk strings), including DIB, font buffer and output size | 140 |
| CreateFonts width bands | 11 |
| login overlay (fade, logo sizes, screen widths, string shapes) | 48 |
| OpenTga | 966 |
| OpenJpeg | 272 |

**OpenTga** covers all 487 installed OZT files in `Data\Interface` and `Data\Logo`,
synthetic images, and 472 header mutations. The mutations are image type, origin bit,
id length, 24 bpp, width 1025, and a smaller header size.

**OpenJpeg** covers 246 installed OZJ files, out of 352: all 234 files of 40 KB or
less, plus 12 large ones (`--jpeg-large`). It also includes 26 truncated mutations.

* For every untruncated file, the client's IJG 6b output equals libjpeg-turbo
  (Homebrew 3.x, library defaults) **byte for byte**.
* Both reject the same 13 inputs: 12 with message 51 and 1 with message 8.
* For the truncated mutations, the call sequences always agree. The pixels agree in 23
  of 26. In the other 3 (`Cface02`, `magic_09_2` and `warrior02`, each cut to two
  thirds), the two libraries fill the missing data differently after the inserted EOI.
  Native output is therefore client-exact for intact files only.

During development the comparison caught two modelling errors on the harness side: a
missing image size in the ctypes bitmap view, and a missing `%%` escape in the sprintf
stub. No deliberate negative controls are committed; any single-word difference fails
a case.

`reconstructed/ui/test_ui.py` holds 16 portable checks against independent Python
statements, plus 1 private check that runs the validator on a sample.
`native/tests/test_native_ui.py` holds 6 portable checks, covering:

* the raster fill rule, culling, filtering and alpha test;
* synthetic-root title and login renders;
* hashes.

It also has 1 private check of the installed title and login renders.

### Live comparison (window-only capture, 2026-10-17)

One reference session was run under `GAME-LOCK.md`: bottle MuMatrix32, about 1 min,
the game closed afterwards. The captures are local only. The game ran with a
1722x1048 client area at Retina 2x. Native renders at 1722x1048 compared with the
capture reduced 2:1 as follows:

**Title screen (frames 033–037).**

* Mean absolute error is **0.59–0.63/255 per channel** outside the progress band.
* With progress 56/100 the band itself fits at 0.82/255.
* Layout, letterboxes, background tiles, logo and webzen mark coincide.

**Login overlay.**

* The logo pixels match with a mean absolute difference of 3.4/765.
* Text baselines are within 1 px. The right-hand line starts at the same pixel
  (x 1625).
* With CoreText Tahoma the left line is 533 px wide, against 530 px live. Arial
  (603 px) and Arial Unicode MS (489 px) do not fit, so `GlobalText[0]` is very
  likely "Tahoma". That is an inference from glyph metrics.
* Strings read off the screen:
  * `Mu The Matrix, Private Server Since 2005 / `;
  * `  COPYRIGHT WEBZEN, INC. ALL RIGHTS RESERVED.`;
  * `Ver %s` with version `10000`.

  These are now the defaults of `mu-render ui login`.

## Native module and tool

| Path | Role |
|---|---|
| `native/core/mu_ui_raster.*` | Deterministic software GL subset; the framebuffer has row 0 at the bottom |
| `native/core/mu_ui_assets.*` | Path resolution, the reconstructed decoders, libjpeg; the lookup behind the client's `Bitmaps.GetTexture` |
| `native/core/mu_ui_font.*` | GDI boundary: CoreText, or the `@box` placeholder |
| `native/tools/mu_render_ui.c` | `mu-render ui title|login|text` |

## Limits and open points

* **The 3D login world.** The ship scene behind the login and server-select screens is
  not rendered (terrain/models/effects milestones).
* **UI-manager windows.** The server-select window, the widget classes and the credits
  window are covered by [client-ui-widgets.md](client-ui-widgets.md) (NATIVE-UI-002).
  The MENU/CREDIT buttons are a GFx (Scaleform) movie. `CLoginWin::Create` `0x00cdc29d`
  has no callers and appears unused.
* **GDI shapes.** GDI's exact hinting and glyph shapes are not reproduced. CoreText
  metrics differ by about 0.5% in width.
* **Encrypted inputs.** `GlobalText` (`Data\Lang.mpr`, encrypted) is not decoded. The
  version bytes sit in the packed third section.
* **GL_CLAMP.** The raster implements it as clamp-to-edge. The client's half-texel
  insets keep sprite sampling away from the border.
* **Mipmapped textures.** Mipmapped filters (not used by the interface) sample the
  base level.
* **Unexecuted wrappers.** Blend modes 1, 4–8 (`0x0184a872`, `0x0184a901`,
  `0x0184aab7..0x0184ac67`) are static readings, not executed.
