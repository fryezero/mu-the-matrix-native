# The client's legacy window layer: server select and credits (NATIVE-UI-002)

This finding continues [client-ui-2d.md](client-ui-2d.md). It covers the window and
widget layer the pinned client still uses before the game world:

* the widget classes `CSprite` (with frames), `CButton`, `CWin` and `CWinEx`, with their
  hover, press and click states and their mouse hit tests;
* the server-select window `CServerSelWin` (`0x01075554`, created by
  `CreateLoginScene` `0x011e2dc0`): server list layout, button states, load gauges,
  notice box;
* the credits window `CCreditWin`, which the login screen's CREDIT button opens;
* the text wrapper `CutText` `0x01859f23`.

It reconstructs them as C under `reconstructed/ui` (`ui_widget.c`, `ui_server.c`,
`ui_credit.c`). `scripts/validate_ui_widgets.py` runs the client's own routines in
Unicorn and compares every platform call and the objects' state word for word. The
native tool `mu-render ui servers|credits` draws both screens on macOS arm64 with
synthetic data.

Labels:

* **verified**: the client's instructions ran in Unicorn and matched the reconstruction
  word for word (calls and object state);
* **live**: compared with a window capture of the running game;
* **static**: read from decoded instructions only.

Pinned inputs are those of [client-frame-loop.md](client-frame-loop.md) (text capture09
`2bd5f2e9…3724`, second section run10 `c985e2e6…a0672f`).

## Where the screen comes from (static)

The login scene's render `0x01857ed9` draws, between BeginBitmap and EndBitmap:

1. the 2D overlay of UI-001 (logo, copyright, version);
2. a GFx (Scaleform) manager (`0x009fe825` → `0x009fe955`);
3. `0x01858c72`, which calls `CUIMng::Render` `0x011e348b` and then other overlays and the
   cursor. `CUIMng::Render` renders the window list (`CUIMng+0x65a4`) through each
   window's `Render` (vtable slot 6).

`CreateLoginScene` `0x011e2dc0` creates four legacy windows and adds them to that list:
`CMsgWin` (`+0x8`), an option window (`+0x458`, `0xf2f5e0`), `CServerSelWin`
(`+0xab0`) and `CCreditWin` (`+0x4648`). It centres the server window on the `CInput`
screen size and sets scene 2. `CreateCharacterScene` `0x011e2f2a` (scene 4) builds the
character-select windows instead.

**MENU and CREDIT are not legacy windows.** They belong to the GFx movie
`winLoginSceneBottomUI` (handler `0x00c704ea`):

* `onCreditClick` shows the legacy `CCreditWin` through `CUIMng::ShowWin` `0x011e34ec`
  (and sends a request);
* `onMenuClick` opens another GFx interface (`0x00c8c8b1`);
* `onLoad` sets the buttons' visibility from `CCreditWin`'s show flag.

The textures `server_menu_b_all.tga` (`0x7b12`) and `server_credit_b_all.tga` (`0x7b13`)
are still loaded by the login loader `0x0182a34c`, but no login-scene code draws those
indices. Only character select's `CCharSelMainWin` (`0x009a492e`) uses `0x7b12`, after its
own loader has reloaded the index. The GFx button rendering is out of this slice.

When the server list arrives, the client's handler `0x0127ec2f` calls `ShowWin(server
window)` and `UpdateDisplay` unless the credits are showing, then `0x0107610c` (not
reconstructed here). The list's contents are the server's data. In this work they are an
input with the fields the window reads, and nothing about the network is reconstructed.

## Widget classes

| Class | Size, vtable | Routines (all verified) |
|---|---|---|
| `CSprite` | `0xa8`, `0x01ab9ba8` | full Create `0x010ad847` (frame table), Create from `SImgInfo` `0x010adc87`, SetAction `0x010ae3a1`, SetNowFrame `0x010ae3eb`, Update `0x010ae557`, PtInSprite `0x010ae2a5`, getters `0x00986ed4..0x00986f8a` |
| `CButton` | `0xe0`, `0x01a7e46c` | Create `0x009865f4`, Update `0x009867e3`, Render `0x00986bbd`, SetText `0x00986d95`, Show `0x00986d49`, CursorInObject `0x00986d72` |
| `CWin` | `0x3c`, `0x01ac7468` | Create `0x0120ccfd`, Release `0x0120ce41`, SetPosition `0x0120ceb4`, SetSize `0x0120ceee`, CursorInWin `0x0120cf39`, Show `0x0120d090`, Update `0x0120d0ce`, Render `0x0120d26d`, RenderButtons `0x0120d2fd` |
| `CWinEx` | `0x4c`, `0x01ac74a4` | Create `0x0120d3df`, SetLine `0x0120d861`, SetPosition `0x0120d73c`, CursorInWin `0x0120da21`, Show `0x0120db2c`, Render `0x0120db7e`, resizing `0x0120dbc7` |

Window vtable order: 0 destructor, 1 Release, 2 SetPosition, 3 CursorInWin, 4 Show,
5 SetActive, 6 Render, 7 (returns 0), 8 ReleaseControls, 9 CursorInControls,
10 UpdateWhileShow, 11 CheckAdditionalState, 12 UpdateWhileActive, 13 RenderControls.

### Sprites with frames

`Create` takes a frame table of texel positions. Each frame's top-left texture
coordinate is `(x + 0.5) / texture size`. A non-null table forces `tile` off and selects
frame 0. `SetNowFrame` moves the four texture coordinates to the frame's corner and keeps
the quad's texture extent; it ignores frames outside `[start, end]`. `SetAction` sets the
range, interval and repeat flag only for sprites with more than one frame. `Update` steps
once the accumulated time reaches the interval: with repeat on it wraps to the start,
otherwise it stops at the end.

**Hit test.** `PtInSprite` builds a rectangle from corners 0 and 2, scaled by the sprite's
scale and turned to top-left window pixels. It then applies `PtInRect`: the left and top
edges are inside, the right and bottom edges are outside, and a hidden sprite never hits.

### Buttons

A button is a sprite plus `enable`, `active` (hit testing on), `click` and `check`, an
eight-entry image map and optional text. `Create(w, h, tex, frames, down, over, disable,
checkUp, checkDown, checkOver, checkDisable)` stacks the frames vertically (`y = h·i`).
Missing down/over frames fall back to 0, and missing check-down/over frames fall back to
check-up.

`CButton::Update` (skipped when the time step is negative or the button hidden) keeps one
static held button `0x01d1dc2c`:

| Situation | State used | Text offset |
|---|---|---|
| disabled | disable / check-disable | 0.5 |
| cursor over, nothing held | over / check-over | 0.5 |
| cursor over, this button held | down / check-down | 1.5 |
| otherwise | up / check-up | 0.5 |

* Left button down over the button makes it the held button.
* Left button up over the held button sets `click` for this frame, plays sound 25 and, for
  buttons with check frames, toggles `check`. Any release clears the held button.
* The text colour is taken from the same state index.
* `Render` draws nothing for a disabled button without a disable frame. Its text uses the
  fixed font (`0x06fc9cb0`): `GetTextExtentPoint32A`, then `RenderText` centred (sort 3)
  in the button's width, at `y = (y + (h − cy)/2)/rate + offset`.

### Windows

`CWin::Update` runs every frame for a shown window:

1. A button release resets the window state.
2. In the normal state every registered button updates.
3. `UpdateWhileShow` runs.
4. Then, only if the window is active:
   * a left press in the 26-pixel title strip (`CursorInWin(2)`) starts a drag, which
     moves the window by the cursor's motion unless it is docked;
   * `CheckAdditionalState` runs, then `UpdateWhileActive`.

`CursorInWin` area 0 is the whole rectangle, area 2 the title strip, and area 3 any
button or the window's own controls. The server and credit windows refuse area 2, so they
cannot be dragged.

`CWinEx` is a frame of five sprites:

* a tiled background inset by 3 pixels;
* top and bottom edges;
* tiled left and right sides, whose height is `lines × side texture height`.

`SetLine` clamps the line count to `[min, max]`. On a left press, `CheckAdditionalState`
lets the bottom 5 pixels or the top 4 pixels resize the frame by whole lines.

## The server-select window (verified)

`Create` `0x01075554`:

* `CWin::Create(0, 0, −2)` (no background);
* 25 group buttons, 108×26 from `cha_bt.tga` (4 frames: down 2, over 1, check 3);
* 20 server buttons, 193×26 from `server_b2_all.tga` (3 frames), each with a 160×4 load
  gauge from `server_b2_loding.jpg`;
* two column decorations and two selection arrows from `server_deco_all.tga`
  (`SImgInfo` frames at x 0, 0x44 and 0x88);
* a `CWinEx` notice box (`server_ex03/01/02`, 1 to 10 lines, set to 10);
* window size 465 × (notice height + 556).

`SetPosition` `0x0107592f` places, with `g` the group button height, `d` the notice box
height and `(x, y)` the window position:

| Element | Position |
|---|---|
| top group buttons 0–4 | centred, stacked upwards from `y + H − g − 5 − d` |
| left column 5–14 | `x`, from `y + H − (11g + d + 10)` down |
| right column 15–24 | `x + 108 + 193 + 0x38`, same rows |
| notice box | centred under the window, bottom-aligned |
| decorations | at buttons 5 and 15 (+0x6c) with datums (8, 0x13) and (0x3c, 0x13) |

`UpdateDisplay` `0x01075bc2` walks the server list in the manager's order:

* groups with position 2 take the first free top button (at most 5), position 0 the left
  column (10), and position 1 the right column (10);
* each placed group's button index is written back into the group (`+0x10`);
* group names use the colour set `ffe2e2e2/ffe2e2e2/ffffffff/0`, or
  `ff79ffff/ff79ffff/ffc1eeff/0` for type 2. The client copies eight entries because group
  buttons have check frames, and it keeps each set twice;
* the column decorations show when their column has groups.

The selected group (`+0x3ae4`, found again by its button index) then fills its servers:

* names in one of four colour sets by the server's type, including orange `ff00b4ff`;
* gauges set to `percent / 100`;
* the group description wrapped into the notice box's two 83-byte rows;
* the arrow beside the selected button. Selections 0–10 use arrow 0 at the button's right
  edge and 11–24 use arrow 1 at its left edge. Left-column buttons 11–14 therefore get the
  arrow on the other side from buttons 5–10;
* server buttons stacked beside the left column, moved up when they are taller than the
  column.

Without a selected group, the server notice (`+0x134`) fills the box.

`RenderControls` `0x01076c1e` draws, in order:

1. the notice box;
2. the decorations, only when there are at least three groups;
3. the arrows and the two notice rows (fixed font, white);
4. the buttons in registration order;
5. if a group is selected, the gauges and three `GlobalText` lines (`0x235–0x237`) at
   (90, 104/119/134) in 640×480 units;
6. extra lines (`0x10f3/0x10f4` for group ids 0x11 and 0x27, `0x1225/0x1226` for type-2
   groups).

`UpdateWhileActive` `0x01076a24`:

* A clicked group button moves the check mark to itself, becomes the selection and sends
  a request. The list reply runs `UpdateDisplay` again.
* A clicked server button whose load is below `0x80` hides the window and starts
  connecting. The network side is outside this work, so the reconstruction emits events
  instead.

**A runtime patch in the capture.** At `0x01076018` the restored capture holds a jump to
`0x10b492f0`, outside the image. A protection or customisation module patched it at run
time. The bytes left behind show the instruction pair it replaced
(`mov eax, [server]; movzx eax, byte [eax+0x14]`), so the colour row is the server's type
byte. The validator executes that original pair at the site. The live game draws server
names in red, blue, green and yellow, which none of the client's four colour sets contain.
The patch therefore very likely replaces the colours (an inference). The module itself was
not analysed.

## The credits window (verified)

`CCreditWin` is a `CWin` (`0x568` bytes):

* a full-screen background made opaque black;
* two 400×400 illustrations (`im1_1.jpg` … `im8_2.jpg`, loaded on demand as textures
  `0x7fa7/0x7fa8`, LINEAR, CLAMP);
* `deco.tga` (always hidden) and the `cr_mu_lo.tga` logo;
* three black 800×42 bars over the text rows;
* its own bold, non-antialiased font. `CreateFontA` height is 10, or 14/18/24 at window
  widths 800/1024/1280, and the face is `GlobalText[0]`.

Opening it (`Show(1)`) loads illustration pair 0 and reads the first credit block. While
the window is active, `UpdateWhileActive` `0x009d95e4` animates it:

* Illustrations fade in over 2000 ms, hold for 22 s and fade out. The next pair (modulo 8)
  is then loaded. Alpha arithmetic is 16-bit, as the client does it.
* Each bar fades out over 300 ms to reveal its row. After 2.3 s the name bar fades back in,
  and the subtitle and title bars too when the next record does not continue their block.
  When the name bar is opaque again, the next block is read.
* A block is one title (type 1) or subtitle (type 2) record followed by up to four names
  (type 3).
* An end record (type 0) plays sound 25, hides the window, sends a request and switches
  the music (`0x0120f5a0`/`0x0120f602`).

`RenderControls` `0x009d9632` works as follows:

* It turns the alpha test off with a raw `glDisable`.
* It draws the illustrations, decoration and logo.
* It draws the title in `ffe2e2e2` and the subtitle in that colour at y 20 and 46.
* It draws the names in `ffc1eeff` at y 72. There are 1–4 columns, with box width
  `W/rate`, `W/4`, `W/3` or `W/4`.
* It draws the bars, then raises the alpha test again.

A row that was never assigned in the current run shows record 0. This client behaviour is
kept.

The credit records come from the client's credit file, loaded into the table at
`0x06fbac20`. That file is not decoded, so the records are an input. An out-of-range
index returns the table's fallback record, and the reconstruction treats it as an end
record (static assumption).

## CutText (verified)

`0x01859f23(src, dst, lines, width)` copies `src` into rows of `width` bytes:

* A row breaks when the next character would reach `width`.
* It breaks after the last space, provided that space is fewer than `min(width/2, 10)`
  bytes back.
* It returns the number of rows.

The client measures characters with `_mbclen`. Under a single-byte code page that is one
byte, which the reconstruction assumes.

## Validation

`scripts/validate_ui_widgets.py` uses the UI-001 machine (`scripts/client_ui_machine.py`)
with the following setup:

* an allowlist computed as the static call closure of the routines above;
* the three window vtables;
* the text facade, CUIRenderTextOriginal and the C runtime's array-constructor iterator.

These are modelled explicitly:

* `CInput`;
* the server list behind the manager's accessors (`0x01072152`, `0x01072838..0x01072928`,
  `0x0107134f..0x010713f8`);
* the credit table (`0x010ea60c`) and `GlobalText`;
* operator new/delete and the string helpers;
* `PtInRect`/`SetRect`/`IsBadReadPtr`;
* GDI metrics (UI-001's synthetic font);
* the texture lookups;
* markers for sounds, the request, hide, connect, music and `LoadBitmap` calls.

Windows live in zero-initialised storage like the static `CUIMng`. A read of any
undefined global or heap byte stops a case.

The full run (seed 1, `--cases 120`) covered:

| Area | Cases | Covered |
|---|---:|---|
| CutText | 400 | widths 1–0x53, 1–5 rows, words and space runs |
| CSprite frames | 120 | 813 Create/SetAction/SetNowFrame/Update/Show/SetPosition steps, 190 PtInSprite tests (74 hits) |
| CWinEx | 60 | Create, SetLine, SetPosition, Show, Render (3,480 calls); 494 CWin::Update frames with drags and resizes (36 move, 42 + 55 resize frames, 284 line changes) |
| CServerSelWin | 120 | ctor, Create and SetPosition at 8 window sizes, UpdateDisplay over random lists (0–30 groups, all positions, overflow, 0–20 servers, loads 0–200, invalid selections), Render (26,774 calls), 1,523 input frames (74 clicks, 49 group selections, 7 connects), 6,819,157 compared state words |
| CCreditWin | 40 | Create at 8 window sizes, Show, 3,180 update frames (54 illustration changes, 705 credit records read, 87 end records), Render (22,320 calls), 1,007,334 compared state words |

Every case compares all platform calls and, after every step, the complete object state.
The state includes:

* every sprite's corners, texture coordinates and frames;
* button states, image maps, texts and colours;
* window rectangles and drag state;
* list counters, the selected group, the notice rows and the held button.

Negative controls showed that the comparison catches single-constant mutations of the
reconstruction:

* a 2400 ms instead of 2300 ms name hold;
* a one-unit text-colour change;
* a wrong name-column width.

A 1-ulp change of the logo placement factor was not caught. The truncated result rarely
changes.

During development the comparison found one reconstruction error: the group colour table
needs eight entries. It also found one modelling error: windows must live in zeroed static
storage, because an empty list leaves the notice rows untouched.

Portable checks: `reconstructed/ui/test_ui_widgets.py` holds:

* independent Python statements of CutText, the layout, UpdateDisplay, the click flow and
  the credit fades;
* a private check that runs the validator.

`native/tests/test_native_ui.py` renders both screens on a synthetic root and checks
layout, check, hover and pressed frames, the click events and the credit blocks. Its
private checks use the installed textures.

## Native module and tool

`mu-render ui servers` composes the server-select screen:

1. Create and centre the window (CreateLoginScene).
2. Open it as the list handler does (ShowWin + UpdateDisplay).
3. Click a group the way a player does, through `CWin::Update`. The click handler and the
   list reply run as in the client.
4. Draw the UI-001 overlay, then the window.

The default server list is synthetic. `--list FILE` reads another list and `--frames`
drives hover, press and click. The client events (group request, hide, connect) and
sounds are printed.

`mu-render ui credits` opens the credits window and advances `--time` in 40 ms frames,
with synthetic or `--credits FILE` records. A font set switches CoreText fonts on the
reconstruction's `SelectObject` calls and adds window fonts on `CreateFontA`.

Renders stay local (`~/Documents/mu-mac-tools/native/renders/ui2/`).

### Live comparison

Two window-only sessions under `GAME-LOCK.md` were used, both with bottle MuMatrix32 and
a 1722×1048 client area at Retina 2×, reduced 2:1. The captures stay local.

* The UI-001 session's capture of the server-select screen.
* A session of this work on 2026-10-17, about 1.5 minutes long, with the game closed
  afterwards. It went only as far as server select: the cursor was moved onto the second
  server button and CREDIT was clicked.

The native renders used a local list file copied from the screen (one group, seven
servers). The comparison used every pixel that the native UI draws opaquely, found by
rendering over black and over white and rendering again without text:

| Region | Opaque pixels | Mean absolute error |
|---|---:|---:|
| selected (checked) group button (UI-001 capture / this session) | 672 / 777 | 0.00/255 |
| server buttons without gauge rows | 6,706 | 0.00/255 |
| hovered server button (`over` frame), cursor area excluded | 868 | 0.00/255 |
| notice box frame | 4,357 | 0.00/255 |
| selection arrow | 251 | 0.00/255 |
| credits: illustration pair 0, about 3 s after CREDIT (alpha 255) | 1,192,292 | 0.03/255 (max 1) |
| credits: `cr_mu_lo` logo | 41,540 | 0.03/255 (max 1) |

* Layout, frames, check and hover states, decorations, notice text placement and the
  credits layout coincide.
* The credits images differ by at most one level, from linear-filter rounding in the
  software rasteriser.
* Gauge rows differ only because the live loads are unknown.
* Server-name colours differ because of the runtime patch above.
* Glyph shapes differ like UI-001's (CoreText instead of GDI).
* Translucent pixels blend with the 3D world, which is not rendered, and were not
  compared.
* The live credits screen also shows an EXIT button. It is a GFx element like
  MENU/CREDIT, and the native render does not draw it.

## Limits and open points

* **GFx.** The MENU/CREDIT buttons and the MENU interface are GFx movies. Their rendering
  is not reconstructed.
* **3D world and cursor.** The ship scene behind the window and the cursor (`0x01858958`)
  are not drawn.
* **The window manager.** `CUIMng::Update`'s focus, activation and docking logic
  (`0x011e3143`, `0x011e3823`) are not reconstructed. The native tool activates the
  server window as `SetTop` would and applies `HideWin` events itself.
* **After the list arrives.** `0x0107610c` runs after `UpdateDisplay` and is not covered.
* **Server-name colours** in the live game come from the runtime-patched path (see
  above).
* **Credit data.** The credit file and `GlobalText` (`Data\Lang.mpr`) are not decoded.
  Defaults are synthetic records, and the three server-screen lines were read off the live
  screen.
* **Synthetic limits.** At most 20 servers per group. The client would write past its 20
  buttons, and the reconstruction clamps.
* **Character select.** `CreateCharacterScene`'s windows (`CCharSelMainWin` `0x009a492e`
  and the others) are the next 2D slice.
