# Rendering the client's GFx interface natively (NATIVE-GFX-001)

The client's in-game interface is Scaleform GFx ([client-hud.md](client-hud.md): 139 GFx windows behind the
registry `0x00ac4a79`). A native client needs a way to play these movies. This research spike answers three
questions:

* What are the movie files?
* Which player can render them on macOS arm64?
* How does the game side connect to the movies?

It also delivers a working prototype.

**Recommendation in short.** Use **Ruffle** (MIT OR Apache-2.0) as an external, pinned library. Put it behind
two layers:

* an offline **GFx → SWF converter** (`native/gfx/gfxconvert.py`);
* a small **C ABI** (`native/gfx/mugfx`) that maps GFx's game boundary (ExternalInterface callbacks, `Invoke`,
  `SetVariable`) onto Ruffle.

Results:

* All 179 installed movies convert, load and run under Ruffle without errors.
* The bottom bar, the inventory and the item tooltip render close to the live client.
* The game-side callbacks NATIVE-HUD-001 mapped arrive unchanged.

The remaining gaps are bounded and listed below: GFx-only ActionScript extensions, six compacted fonts, the
GPU→GL copy and a font library shared between movies.

**Update (NATIVE-GFX-002, [native-gfx2.md](native-gfx2.md)).** The extensions are implemented as a pinned Ruffle
patch series; the compacted fonts convert; keyboard/text input, device fonts, window-sized players and
IOSurface sharing replace the full-window read-back; a GFx layer plays the bar, inventory, tooltips, character
window and chat over mu-world (`--gfx`).

**Update (NATIVE-GFX-003, [native-gfx3.md](native-gfx3.md)).** The HUD runs as the client's base movie with its
icons. Item models are drawn over the inventory. The client's window placement and menu are compared in Unicorn.

Labels used below:

* **observed**: run on this Mac under Ruffle;
* **static**: read from the files without running them;
* **live**: compared with the NATIVE-HUD-001 window captures of the running game;
* **inference**: a conclusion not tied to a run.

Scaleform's own code inside the client is not analysed. The protection modules are out of scope.

## 1. The movie files (static, tool: `native/gfx/gfx_inventory.py`)

`Data/Interface/GFx` contains:

* 1,264 `.ozd` files;
* 179 `.ozg` files;
* 83 `.ozp` files (the NaviMap PNGs, already decoded by asset-recovery);
* 8 `.swf` and 2 `.gfx` font files;
* `fontconfig.txt`;
* `Notice/Eventnotice.png`.

**Container.**

* **`.ozg` movies.** Each one is the ModulusCrypt envelope (the same 34-byte prefix, selector bytes and 1 KiB
  cipher windows as BMD v14, decoded by `model-recovery/libmodulus`) around a GFx movie.
  * Signature `CFX` (zlib, 115 files) or `GFX` (stored, 64 files) instead of `CWS`/`FWS`.
  * SWF version 9 (149), 10 (29) or 8 (1).
  * 13.1 MB on disk, 26.3 MB uncompressed.
* **`.ozd` images.** The same envelope around **DDS** images:
  * 1,260 DXT3, 3 DXT5 and 1 uncompressed RGBA;
  * mostly power-of-two sizes from 8×8 to 1024×1024;
  * 163 MB in total.
* **Font files.** `gfxfontlib.swf`, `fonts/*.swf`, `fonts_all.swf` and `IME.swf` are plain `CWS`. The two
  `fonts/*.gfx` files are plain `CFX`.

The envelope is an asset format already published in this repository, not the protection.

**Exporter.** Every movie carries `ExporterInfo` (tag 1000):

* exporter version word `0x036f` (a GFx 3.x exporter);
* bitmap format 14 (DDS);
* the swf name;
* a table of AS code offsets.

**ActionScript.** All 179 movies are **AS2** (AVM1): `FileAttributes` without the AS3 bit, no `DoABC`. They hold
10,135 `DoAction` and 9,232 `DoInitAction` tags, about 31 MB of AVM1 bytecode in total.

**Tag inventory** (top level and sprites, all movies):

| Tags | Count |
|---|---:|
| ShowFrame / PlaceObject2 / PlaceObject3 / RemoveObject2 | 105,126 / 28,954 / 1,580 / 3,688 |
| DefineSprite / ExportAssets / FrameLabel | 11,233 / 16,939 / 9,448 |
| DefineShape 1–4 / DefineScalingGrid | 5,237 + 727 + 204 + 44 / 1,358 |
| DefineEditText (138 HTML, 0 device-font fields) / CSMTextSettings / DefineText | 4,905 / 4,895 / 8 |
| DefineFont3 / ImportAssets2 (fonts) / DefineButton2 / Metadata | 112 / 178 / 3 / 30 |
| **GFx** DefineExternalImage2 (1009) / DefineSubImage (1008) / ExporterInfo (1000) / DefineCompactedFont (1005) | 1,584 / 7,750 / 179 / 6 |

There are no morph shapes, sounds, video, bitmaps embedded in the SWF, or AS3.

**Images.**

* `DefineExternalImage2` names a `.dds` file, which is stored as the `.ozd` of the same stem.
* An id with high word 9 (159 of them) is a **texture atlas**. `DefineSubImage` cuts 7,750 rectangles out of it
  as bitmap characters (its `image` field is the atlas id's low word).
* The other 1,425 are plain bitmaps (`*-nopack` export names), stretched to a power of two in the DDS.
* `MonsterInfo` references nine `.dds` files that are not installed (wind, water, fire, …). Inference: the
  game supplies them at run time.

**Fonts.**

* 170 movies import `$NormalFont` and 8 import `$DevFont` from `gfxfontlib.swf`.
* `gfxfontlib.swf` holds small placeholder fonts: Arial Unicode MS with 191 glyphs and NanumGothic Bold with
  205 glyphs.
* GFx resolves the imports through `fontconfig.txt`. For the English configuration, `$NormalFont` and
  `$DevFont` map to **Arial Unicode MS** in `fonts/fonts_all.swf` (36,685 glyphs, 9.7 MB). That file also holds
  MS PGothic (14,545 glyphs) and NanumGothic Bold (17,333 glyphs).
* Movie-local fonts:
  * "Slate Mobile" with 95 glyphs (47 movies);
  * glyph-less name-only fonts used as device fonts ("Times New Roman" in 26 movies, "Agency FB", "MS
    PGothic", …);
  * six `DefineCompactedFont` (GFx's packed font format) in ExtensionBagFrame, GensRanking, GuildInfoFrame,
    PrivateStoreFrame, RebuyList and SnsWindow.

**CLIK and game classes.**

* The movies use 34 Scaleform **CLIK** AS2 classes: `gfx.controls.Button`, ScrollingList, TileList, DropdownMenu,
  ItemSlot, DragManager, FocusHandler, Tween, …
* They define 422 game classes of their own, in two frameworks:
  * `Common.Base.MUComponent` / `MUSlotComponent` (the item windows);
  * `core.KeyMovieClip` with `EventCall(cmd, param)` → `ExternalInterface.call(keyName, cmd, param)`. Used by
    `main` and other newer windows.

**The game boundary** (static, AVM1 scan):

* 537 distinct `ExternalInterface.call` names (literal, constant or `prefix + "literal"`). Examples:
  * `requestWindowPos` (606 sites), `UIInit`/`AppearComplete`/`LeaveComplete`/`RollOver`/`RollOut`/
    `CloseWindow`/`TweenTimeSet` (151 each);
  * `onClick{name}` (219);
  * `requestSlotInfo`, `EQUIPrequestSlotInfo`;
  * the `request*Slot*` family.
* 74 `EventCall` commands.
* `fscommand("TextInput")` (13) and `fscommand("GFxApplyLanguage")` (1).
* No `addCallback`. The game reaches into the movies with GFx `Invoke` on display-object paths.

The NATIVE-HUD-001 names all occur:

* `setHPMP`, `onHotKey` and the skill/item hotkey and tooltip callbacks in `main`;
* `SetZenText`/`SetRuudText`/`SetRageFighter`/… in `InventoryFrame`;
* `OnClick4thSkillTree`/`OnClick5thSkillTree`/`onClickbtnMasterSkillTree`/`OnHotkeyExpand` in
  `CharacterInfoFrame`;
* `SetInfoPopup*` in `InfoPopup`.

Three names were not found as strings: `mcItemHotKey`, `mcSkillHotKey` and `mcExpBar` (clip names the game
resolves, inference), plus `CloseInfoPopup`.

**GFx-only AS2 extensions** (static: the name occurs in the movie's constant pools):

| Extension | Movies |
|---|---:|
| Selection `disableFocusKeys`, `disableFocusAutoRelease`, `disableFocusRolloverEvent`, `alwaysEnableArrowKeys`, `findFocus`, `getFocusBitmask`; `getTopMostEntity`; `_global.gfxExtensions` (CLIK's focus handling) | 177–178 |
| `onReleaseAux` | 173 |
| `appendHtml` | 115 |
| `loadBitmapFromLib` | 79 |
| `topmostLevel` | 75 |
| `hitTestDisable` | 33 |
| `noAdvance`, `setCursorType`, `textAutoSize`, `shadowColor` | 24 |
| `verticalAlign`, `onPressAux`, `onDragOverAux`, `onDragOutAux`, `onReleaseOutsideAux` | 23 |

`onReleaseAux` is the right-click release; `MUItemSlot` sends `requestItemSlotClickR` from it.

```sh
MU_GAME_ROOT=... tools/.venv/bin/python native/gfx/gfx_inventory.py [--json local.json] [--movie NAME] [--verbose]
```

The tool prints these tables. Its JSON report holds names from client files and stays local.

## 2. Options compared

| | Ruffle (+ converter + mugfx) | Lightspark | GameSWF descendants / Gnash / Shumway / Swfdec | Native re-implementation |
|---|---|---|---|---|
| Licence | MIT OR Apache-2.0. The 317-crate dependency graph is MIT/Apache/Zlib/ISC/BSD/Unicode/Unlicense (counted with `cargo metadata`). The default font is Noto Sans (OFL-1.1). | LGPL-3.0 | gameswf: public domain (the ancestor of Scaleform itself); Gnash: GPL-3; Swfdec: LGPL; Shumway: Apache-2 | Ours (MIT) |
| State (2026-10) | Active: daily nightlies, release tags; AS1/2/3. Evaluated hands-on (below). | Active (0.10.0 released 2026-10-18); "all AS versions" per its README. Build documented for Linux distros only (ffmpeg, librtmp, fontconfig); macOS is not a documented target. Not built here. | Unmaintained for 10–15 years; SWF ≤ 8 subsets (gameswf); no macOS arm64 builds | — |
| GFx specifics | None natively. The converter handles container, DDS, atlases, fonts and fontconfig. The extensions need shims (below). | None natively; same converter needed | gameswf shares GFx's roots but predates GFx 3 | Everything authored |
| Embedding | A Rust library with a renderer trait. wgpu (Metal) offscreen target works; C ABI written here. | C++ application/plugin; embedding API not designed for it | — | Native from the start |
| Fidelity seen | Inventory, bottom bar, tooltip close to live (section 3) | not measured | not measured | Depends on porting 179 movies' layouts and 31 MB of AS2 logic by hand |
| Effort to production | Medium: extension shims, zero-copy textures, input/IME, per-window wiring | High: macOS port first, then the same work | Very high (revive dead code) | Very high: 139 windows, 422 game classes, 34 CLIK classes |

Lightspark and the dead players were assessed from their repositories and documentation only. Ruffle already
renders every movie (below), so building Lightspark's Linux-first stack on macOS would not change the
recommendation.

## 3. Ruffle results (observed)

**Build.** `native/gfx/fetch-ruffle.sh` clones Ruffle tag `nightly-2026-10-17` (commit
`061b39b0c3ecdd88214ba1750a035a678bf73559`) into `$MU_GFX_DEPS` and links `native/gfx/.deps/ruffle`. No Ruffle
source is in the repository.

* Ruffle's build compiles its AS3 player globals with Java. The script downloads a Temurin JDK 21 into the deps
  directory when no `java` works; nothing is installed system-wide.
* Toolchain: Rust 1.99 (rustup, user account).
* `build-mugfx.sh` builds the crate (about 45 s on the M5) and the prototype window.

**Unconverted movies fail.**

* A header-patched `CFX→CWS` movie loads, but renders an empty white stage: no shapes appear because every
  bitmap is an external DDS or an atlas cut.
* GFx tags 1000–1009 are unknown to Ruffle and skipped.

**Converted movies** (`gfxconvert.py`):

* 179 of 179 convert in about 7 s.
* Atlas cuts and plain images become premultiplied `DefineBitsLossless2`, resampled to the declared size.
* The font import is inlined and renamed to `$NormalFont`, as GFx's font map resolves it.

**Survey** (`ruffle_survey.py`, 179 movies, 1024×768, 10 frames each):

* Run: 179/179 load, run and render with no panic or timeout, in 14 s in total. Median load is 36 ms.
* **149 draw content.** The other 30 are empty until the game feeds them: popups, tooltips, `base`, `hudMap`,
  `hudPlayerName`, …
* Ruffle's own reports:
  * an unimplemented `MovieClip.scale9Grid` setter (AVM1 stub) in 112 movies. The `DefineScalingGrid` tags
    themselves render;
  * one "AVM1 stack underflow" per movie in shared CLIK init code. It is present without the bridge too, and
    nothing visibly breaks;
  * "unknown device font" for the glyph-less fonts (Times New Roman 33, Slate Mobile 13, …). Ruffle falls back
    to its Noto Sans;
  * the nine missing `MonsterInfo` images;
  * one unregistered `sbTileList` symbol.
* Contact sheets: `~/Documents/mu-mac-tools/native/renders/gfx/survey/sheet0..3.png`.

**Fidelity against the live captures** (live: `renders/hud/live/`):

* **Inventory.** It matches the live window: frame, equipment slots, 8×8 grid, buttons and zen/ruud fields.
  * The movie reports `requestSlotInfo(24.75, 370, 26, 26, page 0)`. Slot 1 is 26 px right of slot 0, so the
    pitch is 26 px with no gap. This equals the 26-pixel pitch measured on the live capture (NATIVE-HUD-001).
  * Right alignment comes from the movie's own `SetAlign(4)` + `SetWindowSize`.
* **Bottom bar.** It matches the live bar, including the masked orb fill.
* **Tooltip.** The text NATIVE-HUD-001's reconstructed HTML pipeline produces for item 0 +9 (`mu-render ui
  tooltip --html-out`), passed to `InfoPopup.SetInfoPopup`, renders as the live tooltips do: centred lines in a
  dark box.
* **Fonts.** With `--fontconfig English`, the glyphs are Arial Unicode MS, as in the live captures. The default
  `gfxfontlib.swf` placeholder gives NanumGothic Bold instead.
  * `--font-subset latin` (U+0020–024F, 2000–22FF, 2460–27BF, FF00–FFEF) shrinks the movie from 7.4 MB to
    125 KB.
  * The rendered tooltip is pixel-identical to the full-font render.

**What does not work yet.**

* **GFx AS2 extensions.** Ruffle implements none of them. Visible effects:
  * no right-click item actions (`onReleaseAux`);
  * HUD overlays marked `hitTestDisable` still take the mouse;
  * CLIK focus extensions are inert;
  * `textAutoSize`/`verticalAlign` text layout falls back to Flash behaviour.
  * Remedy: AS2 polyfills added by the converter (where the Flash API suffices), or a small patch set on a Ruffle
    fork. Ruffle's licence allows both.
* **`DefineCompactedFont`** in 6 movies: the text of those windows uses Ruffle's fallback font.
* **Device fonts.** Ruffle needs system fonts registered through its font backend; mugfx does not do this yet.
* **IME/keyboard.** `IME.swf` and `fscommand("TextInput")` are not wired. Keyboard events are not forwarded by
  the prototype.
* **GPU memory.** Decoded RGBA bitmaps take 4× the size of the DXT3 originals.

**The game boundary through Ruffle** (observed, with a host bridge):

* **Movie → game.** `ExternalInterface.call` reaches the C callback with JSON arguments. The C callback's JSON
  reply is returned to ActionScript.
* **Game → movie.** The converter adds one `DoAction` (`--bridge`) that registers `__mu_invoke(path, method,
  args)`, `__mu_set` and `__mu_get` with `ExternalInterface.addCallback`. `mugfx_invoke`/`mugfx_set_variable`/
  `mugfx_get_variable` call them; this is GFx `Invoke`/`SetVariable`/`GetVariable` on AS2 paths.
* **Calls from inside callbacks.** They are queued and run after the current advance. This lets a handler
  answer `CloseWindow` with `SetVisible(false)`.
* **Not covered.** Ruffle's `ExternalValue` cannot carry display objects. The movie → game argument lists seen
  so far carry numbers, strings and plain objects only.

**Cost per frame on this Mac** (Apple M5, macOS 27, Metal through wgpu; `mu-gfx-window`, 1280×800). Both
movies render at full window size:

| Run | Frame | CPU / frame | Per movie (bar / inventory) |
|---|---:|---:|---|
| `--bench --open`: both movies rendered and copied every frame, no vsync (3 runs) | 6.03–6.08 ms (≈165 fps) | 4.9 ms | advance 0.16 / 0.50 ms, Ruffle render submit 0.33 / 0.60 ms, GPU completion + readback 1.09 / 1.50 ms, `glTexSubImage2D` 0.48 / 0.47 ms |
| vsync (120 Hz panel), render only when the movie changed | 10.4 ms (vsync) | 3.7 ms | 76 / 186 renders in 600 frames |

GPU load (`ioreg` "Device Utilization %", sampled each second):

* about 17–20 % for the window without movie renders (`--baseline`);
* about 23–27 % with the bar rendering on change.

**The cost is dominated by the GPU → CPU → GL copy** of two 4 MB frames. Integration steps that remove most of
it (inference):

* size each window's player to its frame rather than the screen (the inventory is about 330×640);
* render only on change (already done);
* share the wgpu texture with GL (IOSurface on macOS) or draw the native world through wgpu/Metal.

## 4. The prototype (`native/gfx/mu_gfx_window.c`)

`mu-gfx-window` opens a native **SDL2 + OpenGL 2.1** window, or runs headless into PNGs. It plays `main` and
`InventoryFrame` through mugfx and wires the game side as the client does (static boundary from
client-hud.md):

* **Bottom bar.**
  * The host plays the UI loader: `onFileLoad`. The movie answers `main("onLoad", "_level0.mc")`, which gives
    the host its path.
  * The host sends `InitMenuInfo` with English labels.
  * Every 40 ms logic step it sends `setHPMP({hp, maxHp, mp, maxMp, Shield, ShieldMax, SkillMana, SkillManaMax,
    isToxic})` with demo values. The orbs, SD and AG bars and their numbers follow.
  * The bar's `onHotKey` (keyCode I/V) or the I key toggles the inventory.
* **Inventory callbacks.**
  * `UIInit` gives the instance (`_level0.g_mcInventory`).
  * `requestWindowPos` and `requestSlotInfo` give the frame position and the page geometry.
  * `requestItemSlotClick` picks up or drops an item through the **reconstructed grid** (`inv_grid.c`: free
    test `0x00ad4ee4`, place `0x00ad37c9`, remove `0x00ad3a4e`, cell lookup `0x00ad3fd9`).
  * `CloseWindow` → `SetVisible(false)`; the window is then no longer displayed.
* **Inventory invokes.** The host sends `InitText`, `SetSlotStateAll` (cell backgrounds for occupied cells),
  `SetAlign`/`SetWindowSize` and `SetVisible`.
* **Items.** They are placed by the **reconstructed slot pass** `mu_slot_pass` (`0x00ab6130`). It takes the
  geometry the movie reported and the 640×480 rates; the result is converted back to pixels as
  `0x0184a18f` does. Coloured boxes stand in for the RenderItem3D models; that is a prototype choice.
* **Hidden windows.** They are neither rendered nor given mouse input. This is a prototype stand-in for the GFx
  manager's visibility test.

**Scripted headless run.** Its renders (local) are in `~/Documents/mu-mac-tools/native/renders/gfx/proto/`:

* `1-hud.png`;
* `2-inventory-open.png`;
* `3-item-held.png`: a 2×2 item picked up with a real movie click on cell 9;
* `4-item-moved.png`: the item dropped on cell 41;
* `5-closed.png`: the movie's own close button clicked → `CloseWindow` → hidden;
* `tooltip-infopopup*.png`: the reconstructed tooltip HTML in the client's InfoPopup.

The run log `~/Documents/mu-mac-tools/native/scratch/gfx/proto-final.log` records every callback and invoke
with its JSON.

Prototype choices that are not client facts:

* the `_level0.mc` / `onFileLoad` loader step;
* the cell gap read from the slot clips;
* the slot state values 1/2;
* the right alignment;
* the item boxes.

```sh
native/gfx/fetch-ruffle.sh && native/gfx/build-mugfx.sh
tools/.venv/bin/python native/gfx/gfxconvert.py --out LOCAL --bridge --transparent --var _root.isClient=true \
    --fontconfig English --font-subset latin --movie main --movie InventoryFrame --movie InfoPopup
native/build/mu-gfx-window --gfx LOCAL [--size 1280x800] [--script] [--headless --out-dir DIR] [--bench --open]
native/gfx/mugfx/target/release/mugfx-shot LOCAL/InfoPopup.swf tip.png --invoke _level0.g_mcInfoPopup SetInfoPopup '[...]'
tools/.venv/bin/python native/gfx/ruffle_survey.py ALL_SWF_DIR OUT --sheet
```

## Verification

`native/tests/test_native_gfx.py` runs 12 tests: 10 portable, 2 private.

* **Envelope.** It decodes the 24 non-model ModulusCrypt oracle vectors of model-recovery through the GFx
  reader.
* **DDS.** DXT1 (both colour modes), DXT3, DXT5 (interpolated alpha, two blocks) and RGBA are checked against
  hand-built blocks. Truncation is rejected.
* **Synthetic GFx movie.** A movie authored in the test has: a CFX header, ExporterInfo, an atlas and a plain
  DefineExternalImage2, DefineSubImage, an ImportAssets2 font, and AS2 with ExternalInterface, EventCall,
  fscommand, a CLIK class and a MUDefines constant. Against it the tests check:
  * the scanner and the inventory report;
  * the converted SWF: no GFx tags, cropped and resampled premultiplied bitmaps, the inlined renamed font, the
    bridge before the first frame (re-read by the scanner);
  * the fontconfig mapping and the Latin subset (codes, advances, kerning kept);
  * a missing image being reported.
* **Ruffle** (when mugfx is built). The converted synthetic movie renders: atlas cut and resampled plain bitmap
  at the expected pixels, transparent stage. The bridge round trip `ping(41)` → `ExternalInterface.call("pong",
  42)` works.
* **Private** (`MU_RECOVERY_INTEGRATION=1`): 179 movies parse (all AS2, one exporter version) and every `.ozd`
  decodes. `main` and `InventoryFrame` convert with no missing image. Run on 2026-10-18: 12/12 pass.

The portable CI has no Rust, so its Ruffle test is skipped. No client routine is reconstructed in this
milestone, so there is no Unicorn comparison. The grid and slot pass the prototype uses are the
NATIVE-HUD-001 verified reconstructions.

## Recommendation for the owner

Take the Ruffle route for the GFx windows, in this order:

1. **Keep Ruffle external and pinned.** Fork it only if extension patches cannot be done as AS2 polyfills.
   Convert the movies at install time from the user's own client files. Converted movies and fonts are client
   data and must not ship with the code.
2. **Add the extension shims that matter for play first**: `onReleaseAux`/right-click, `hitTestDisable`, the CLIK
   focus extensions, `textAutoSize`. Then decode `DefineCompactedFont` for the 6 movies, register device fonts
   and wire keyboard/IME.
3. **Make the integration zero-copy.** Size the players per window and share the textures with the native
   renderer, or move the native renderer to wgpu/Metal. Use one shared font library instead of a font per
   movie.
4. **Wire windows one by one** with the NATIVE-HUD-001 handlers as the game side. The next ones are
   CharacterInfoFrame, the tooltip with item hover, chat and the extension bags.

A native re-implementation only makes sense for a few windows that must look different. It cannot reproduce
179 movies of layout, animation and AS2 logic at reasonable cost.
