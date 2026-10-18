# The GFx interface in the native client (NATIVE-GFX-002)

NATIVE-GFX-001 ([native-gfx.md](native-gfx.md)) showed that the client's 179 GFx movies convert and run under a
pinned Ruffle. This milestone makes them usable as the native client's interface:

* the GFx ActionScript extensions the movies rely on, as a five-patch series on the pinned Ruffle;
* keyboard and text input, device fonts, and the six packed (`DefineCompactedFont`) fonts;
* rendering without the GPU → CPU → GL copy, players sized to their windows, redraw on change, Retina scale;
* a GFx layer (`native/gfx/mu_gfx_layer.c`) that plays the bottom bar, inventory, item and skill tooltips,
  character window and chat with their game side;
* `mu-world --gfx DIR`: the real HUD and windows over the native 3D world.

**Update (NATIVE-GFX-003, [native-gfx3.md](native-gfx3.md)).** The HUD now runs as the client's base movie
(`base.swf` → `ExternalBase.swf` and its UI loader), which brings the skill icons (`ImageData`), the item hotkey
icons (game image `image0`) and a chat without the leftover rows. `loadBitmapFromLib` works through `loadClip`.
Item models are drawn over the inventory. The window placement and the menu take the client's form, compared in
Unicorn. Two Ruffle patches (0006, 0007) join the series. The stand-alone `main`/`chat` mode below remains for
movie directories without `base.swf`.

Labels:

* **observed**: run on this Mac (Apple M5, macOS 27) under the patched Ruffle;
* **static**: read from the movies' ActionScript (decompiled locally with JPEXS, nothing committed) or counted
  in their bytecode;
* **inference**: a conclusion not tied to a run or an instruction.

Scaleform's code inside the client is not analysed; no client routine is reconstructed here, so there is no
Unicorn comparison. The grid, slot pass and tooltip pipeline the layer uses are the NATIVE-HUD-001 verified
reconstructions.

## 1. GFx ActionScript extensions

Counts are movies (of 179) whose bytecode contains the name (static). "Evidence" names the movie code that
uses it. All are implemented in Ruffle by `native/gfx/ruffle-patches` and checked by
`native/tests/test_native_gfx2.py` (synthetic AS2 movie, observed).

| Extension | Movies | Evidence (static) | Patch: behaviour |
|---|---:|---|---|
| `onPressAux`, `onReleaseAux` `(controllerIdx, keyboardOrMouse, button)`; `onReleaseOutsideAux`, `onDragOverAux`, `onDragOutAux` `(controllerIdx, button)` | 173 / 23 | `Common.Controls.MUItemSlot.onReleaseAux` sends `requestItemSlotClickR` when `buttonIdx == 1`; CLIK `gfx.controls.Button.configUI` maps all five to its press/release/drag handlers (their parameter lists give the argument order) | 0001: right (1) and middle (2) button events call the handlers; a clip with any of them is in button mode; `enabled`/visibility rules as for buttons |
| `MovieClip.hitTestDisable` | 33 | `Frame.Main.onLoad` (HP/MP/SD/AG bars, quest alarm), `UIBase` (`mcBottomHud` when `isClient`), chat `ChatView.SetEditText` (`_bg`/`_textView.hitTestDisable = !editing`) | 0002: the clip and its children are skipped by mouse picking and `hitTest` |
| `MovieClip.topmostLevel` | 75 | CLIK `PopUpManager` (popups, dropdown lists) | 0002: drawn after the whole stage with its ancestors' transforms, picked first |
| `MovieClip.noAdvance` | 24 | `common.CustomMouse`, `Frame.Main.setQuestAlarm` | 0002: the clip's and its children's frames and `onEnterFrame` stop |
| `Selection.disableFocusKeys`, `disableFocusAutoRelease`, `disableFocusRolloverEvent`, `alwaysEnableArrowKeys` | 177 | CLIK `FocusHandler` constructor; `UIBase` | 0003: Tab/arrow keys no longer move focus; clicking outside keeps focus; the other two are stored |
| `Selection.numFocusGroups`, `getFocusBitmask`, `getControllerMaskByFocusGroup`, `get/setControllerFocusGroup`, `findFocus`, `moveFocus`, `captureFocus` | 177 | CLIK `UIComponent` (focus property), `TextInput.changeFocus`, `FocusHandler` | 0003: one controller in one focus group; `findFocus`/`moveFocus` return no candidate (the client turns focus keys off) |
| `System.capabilities.numControllers` | 177 | CLIK `TextInput.changeFocus` and `UIComponent` loop `0 … numControllers-1` | 0003: 1. Without it no CLIK text input takes the focus (found when the chat input stayed dead) |
| `Mouse.getTopMostEntity([x, y][, testAll])` | 177 | CLIK `UIComponent.scrollWheel` walks its `_parent` chain | 0003: topmost object under the point |
| `Mouse.setCursorType`, cursor constants, `getButtonsState`, `getPosition` | 24 | `common.CustomMouse` | 0003: the shape reaches the host (`mugfx_cursor`) |
| `TextField.appendHtml` | 115 | CLIK `TextInput.appendHtml` | 0004: appends to the field's HTML |
| `TextField.textAutoSize` (`shrink`, `fit`), `verticalAlign` (`center`, `bottom`) | 24 / 23 | `util.as`, `RodGauges_SD/AG` (bar numbers), `LRSubMenu`, `TooltipMainButton` | 0004: the text is laid out again at width/scale and drawn scaled; vertical offset inside the field |
| `TextField.shadowColor`, `hitTestDisable` | 24 | `StyleManager` colour styles | 0004: plain properties |
| `_global.gfxExtensions` | 178 | CLIK `FocusHandler` sets it | none needed (a plain assignment; the patched player always has the extensions) |
| `MovieClip.loadBitmapFromLib` | 79 | `Common.Base.MUComponent.GetIconBitmapData` on an icon movie it loaded with `MovieClipLoader` | **not implemented** (the game supplies the icon movies) |

Patch 0005 adds the host side: `Player::set_gfx_view` (a NoScale stage of the window's size whose viewport
shows only one window's area) and `Player::gfx_hit_test` (GFx `Movie::HitTest` with shapes).

**The series.** `native/gfx/ruffle-patches/000{1..5}-mu-*.patch` is a `git format-patch` series on Ruffle
`nightly-2026-10-17` (`061b39b0`), 808 added lines in `core/src` only. `native/gfx/apply-ruffle-patches.sh`
(run by `fetch-ruffle.sh`) leaves the pristine clone untouched, applies the series with `git am` on a separate
worktree `$MU_GFX_DEPS/ruffle-061b39b0c3ec-mu` and links `native/gfx/.deps/ruffle` to it; a stamp of the
patch files rebuilds the worktree when the series changes (`MU_GFX_PRISTINE=1` links the unpatched clone).
Licences: Ruffle is MIT OR Apache-2.0; the patches are this repository's work under its licence; the patch
context lines quote Ruffle under Ruffle's licence ([THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)).

## 2. Input, text and fonts

**mugfx ABI 2** (`native/gfx/mugfx/include/mugfx.h`):

* `mugfx_key(kind, vk, codepoint, mods)` takes the Windows virtual key codes the client and Flash use (`I` =
  73, Enter 13). It maps them to Ruffle's physical/logical keys and also sends the editing keys (Backspace,
  Delete, arrows, Home/End, Enter, Ctrl+A/C/V/X) to a focused text field. `mugfx_text(utf8)` delivers typed or
  IME-committed text. `mugfx_text_focus` reports a focused text field.
* `fscommand(cmd, arg)` reaches the host as `fscommand [cmd, arg]`. The chat sends `TextInput focusIn/focusOut`
  (the client's IME signal, static); the layer tracks the edit state from it.
* `mugfx_mouse` adds the wheel and mouse-leave; right/middle buttons reach the Aux handlers.
* `mugfx_hit_test`, `mugfx_cursor`.

**Device fonts.** mugfx gives Ruffle a UI backend whose `load_device_font` maps the device font names of the
movies to macOS fonts: Times New Roman (26 movies), Arial, Tahoma, Verdana; Agency FB → Arial Narrow; MS
PGothic, NanumGothic, Arial Unicode MS and unknown names → Arial Unicode; Slate Mobile (glyph-less in 13
movies) → Arial. `mugfx_register_font(name, path, style)` overrides the map. These are host choices; the
client resolves device fonts through Windows.

**Packed fonts** (static). The six `DefineCompactedFont` tags (ExtensionBagFrame, GensRanking, GuildInfoFrame,
PrivateStoreFrame, RebuyList, SnsWindow) are one 8,388-byte font: character id, the name **"Slate Mobile"** as
a NUL-terminated string, then packed glyph data. 47 other movies carry a regular DefineFont3 "Slate Mobile"
with 95 glyphs. `gfxconvert.py` now replaces each compacted font with the glyph-richest same-named
DefineFont2/3 of the GFx directory, under the compacted font's id, so its text fields (for example ids 223/224
in GuildInfoFrame) keep their font. Without such a font it uses the fontconfig `$NormalFont`. The packed glyph
format is not decoded; whether its glyphs equal the DefineFont3's is an inference from the shared name.

## 3. Rendering

* **Window-sized players.** The layer reads each visible movie's root bounds (`_level0.getBounds()`), pads them
  by 4 points, rounds to 32 points and calls `mugfx_set_view`: the movie keeps the full window as its stage, the
  render target covers only its window. Bottom bar 960×160, inventory 352×672, chat 640×160 instead of
  1280×800 each.
* **IOSurface sharing (macOS).** `mugfx_open_shared` backs the wgpu render target with an IOSurface (Metal
  texture `newTextureWithDescriptor:iosurface:plane:` wrapped through wgpu-hal). The GL compositor binds the
  same surface with `CGLTexImageIOSurface2D` (`GL_TEXTURE_RECTANGLE`, BGRA, premultiplied alpha). The layer
  submits every changed movie, then waits once for the GPU (`mugfx_gpu_wait`) before drawing.
* **Redraw on change.** Only movies Ruffle marks dirty are rendered. The movies themselves invalidate often
  (tweens, CLIK timers): with the inventory open, about half the frames re-render it.
* **Retina.** `mugfx_set_view` takes a backing scale: the movies lay out in points and render at full
  resolution. mu-world passes its drawable/window ratio.

Cost per frame (observed, `mu-gfx-window --bench --open`, 600 frames, no vsync, bar + inventory + chat at
1280×800):

| Path | Frame | CPU / frame | Notes |
|---|---:|---:|---|
| NATIVE-GFX-001 style: full-window players, read-back + `glTexSubImage2D` (`--readback --full-stage`) | 5.85 ms | 4.26 ms | |
| window-sized players, read-back (`--readback`) | 3.56 ms | 2.97 ms | |
| window-sized players, IOSurface (default) | 2.98 ms | 2.66 ms | one GPU wait of about 1.2 ms per rendered frame |

With vsync (120 Hz) the CPU per frame is about 2–3.6 ms shared against 5.2 ms for the old path (noisy). The
remaining wait is the GPU executing Ruffle's frame; double-buffered surfaces would hide it at one frame of
latency (not done).

## 4. The GFx layer and its game side

`mu_gfx_layer.c` loads libmugfx with `dlopen` (no Rust at build time; a missing library or movie fails
cleanly) and opens `main`, `InventoryFrame`, `InfoPopup`, `CharacterInfoFrame` and `chat`. The boundary it
plays (static readings of each movie's ActionScript):

| Movie | Movie → game | Game → movie |
|---|---|---|
| `main` (Frame.Main at `_level0.mc`) | `main onLoad/onResize/onHotKey/onSelectSkill/onSkillTooltip/offSkillTooltip/useItemHotKey/onLoadSkillSlot` | `onFileLoad` (UI loader step), `InitMenuInfo`, `setHPMP`, `mcExpBar.setExpData`, `mcSkillHotKey.SetSkillSlot/setSelectSkill/onUseSkillDelay`, `mcItemHotKey.setItemHotKeyAll`, `onKeyUp` |
| `InventoryFrame` | `UIInit`, `requestWindowPos`, `requestSlotInfo`, `requestItemSlotClick/ClickR/Over/Out`, `CloseWindow` | `InitText`, `SetZenText`, `SetRuudText`, `SetAlign(4)`, `SetWindowSize`, `SetSlotStateAll`, `SetVisible` |
| `InfoPopup` | `UIInit` | `SetInfoPopup(x, y, w, h, html)`, `SetInfoPopupMainSmall(x, y, w, h, hotkey, name)`, `SetInfoPopupClose` |
| `CharacterInfoFrame` | `UIInit`, `onClickButton(index)` (the "+" stat buttons), `CloseWindow` | `InitText`, `ClearItems`, `SetCharacterName`, `SetName(position, index, sort, text, v1, v2, button)`, `UpdateScorllList`, `SetPointText`, `SetVisible` |
| `chat` (symbol library; `Chat` attached as `_level0.mc`) | `chat onLoad/onEnterText/onFocuseText`, `fscommand TextInput` | `InitData`, `OpenEditText`, `CloseEditText`, `onPushText({pos: 0, str})`, `AddChatInfo({type, name, msg})`, `ClearAllChatHistory` |

The clip names `mcSkillHotKey`, `mcItemHotKey` and `mcExpBar`, which NATIVE-HUD-001 found as strings in the
client's invokes, are children of `_level0.mc` (static, instance names in main.swf).

Behaviour (observed in `mu-gfx-window` and mu-world; layer choices marked):

* **Input routing.** Mouse moves go to every visible movie. A press goes to the topmost visible movie whose GFx
  hit test covers the point (windows by z-order, then chat, then the bar), and the release to the same movie.
  When no movie is hit, the event is the world's: a click through the bar's `hitTestDisable` gauges or the
  non-editing chat reaches the 3D view.
* **Keys.** Keys go to the bar, whose own handlers produce `onHotKey` (`Main.onKeyUp`) and `onSelectSkill`
  (`SkillHotKeyPage` Key listener). `Main.onKeyUp` is a clip key handler. In the client it fires because the
  bar has keyboard focus (inference); the layer calls it after a key-up the bar saw. The keys the interface uses
  (window hotkeys, digits, Esc with a window open, everything while the chat edits) are not passed to the walk
  session.
* **Inventory.** It runs on the reconstructed grid: pick/drop, right click (logged; the demo potion heals,
  layer choice), hover tooltip, close button. Items are coloured stand-ins placed by the reconstructed slot
  pass (no RenderItem3D models, layer choice). A held item released over the world is put back, because
  dropping is a server action.
* **Tooltips.** The host's tooltip callback builds the InfoPopup HTML. mu-world uses `core/mu_hud_tip.c`: the
  NATIVE-HUD-001 itemtooltip/itemtooltiptext pipeline, moved out of `tools/mu_render_hud.c` unchanged. Without
  a game root, a minimal tooltip goes through the reconstructed HTML assembly. Skill slots show
  `SetInfoPopupMainSmall`.
* **Character window.** It is filled from the hero values (demo, or fed by the host with
  `mu_gfx_layer_set_hero`). The labels are English stand-ins for GlobalText; "+" spends a point.
* **Chat.** Enter opens the input (`OpenEditText`, CLIK focus with `numControllers`). Typed text goes to the
  movie's field. Enter submits through the movie's own `onPushText` path, which reports `onEnterText`. The
  layer echoes the line with `AddChatInfo` (local echo, layer choice). Esc cancels. The chat's own
  `onKeyDown` is gated on the main UI scene (`gSystem.isMainScene` → `UIBase`, which a standalone chat movie
  lacks), so the layer drives Enter itself.
* **Hero values.** The 40 ms logic step feeds `setHPMP` and `setExpData` only when values change.

**mu-world.** `mu-world --gfx DIR [--gfx-open inventory,character]` (`native/world/world_gfx.c`) opens the
layer after the 3D pass, in the window and headless GL. It feeds SDL input to the layer first and uses the
game root for Item.bmd sizes/names and the tooltip tables. mu-world's functions are unchanged, and mu-client
links the layer because `world_embed.c` compiles `world/main.c`. Headless run: 60 frames with the HUD,
inventory and character window, 12 renders, 35 callbacks, 169 invokes.

## Verification

`native/tests/test_native_gfx2.py` has 14 tests. Run on 2026-10-18 with mugfx built and
`MU_RECOVERY_INTEGRATION=1`: 14/14 pass, and the 12 NATIVE-GFX-001 tests also pass.

* **Portable (CI).**
  * The patch series is well formed. It applies to the pinned checkout when one is present.
  * Compacted-font conversion with a donor and without one.
  * The layer compiled without GL against `tests/gfx_stub_mugfx.c`, a stand-in libmugfx that answers like the
    movies. The test covers:
    * paths from UIInit/onLoad;
    * the first-fit placement 0, 1, 3;
    * the `I` hotkey opening the inventory;
    * window-sized view 928,0 352×672;
    * the helm tooltip HTML;
    * pick/drop to cell 41, right click;
    * chat send and echo;
    * character rows;
    * a world click not taken, the close button, Esc;
    * the same at Retina scale 2;
    * a missing library failing cleanly.
* **With mugfx (skipped in CI).**
  * The synthetic AS2 movie checks:
    * `hitTestDisable` (the click reaches `bottom`, not `top`);
    * `onReleaseAux(0, 0, 1)` and `onDragOutAux(0, 1)`;
    * `topmostLevel` drawn and picked above a higher-depth clip;
    * the GFx hit test;
    * `getTopMostEntity` → `_level0.pop`, `setCursorType` → cursor 2;
    * `numControllers`/`numFocusGroups`/`Mouse.HAND`/`getControllerMaskByFocusGroup`;
    * `noAdvance` stopping `onEnterFrame`;
    * `appendHtml`, the `textAutoSize`/`verticalAlign` properties and their layout (centred ink starts below
      30 px, shrunk ink is shorter);
    * text input and Backspace into a focused field;
    * `disableFocusKeys` keeping focus on Tab;
    * a window view, at scale 1 and 2, with view-relative input;
    * IOSurface output equal to read-back (≤ 2 per channel).
  * The layer also opens synthetic movies on the real library.
* **Private.** The six compacted-font movies convert with no unconverted tag.

Renders are local in `~/Documents/mu-mac-tools/native/renders/gfx2/`:

* `cpu/`, `gl/` and `gl-readback/`: the scripted `mu-gfx-window` run (HUD, inventory, tooltip, held item, moved
  item, character window, chat typing and sent, skill select, closed windows) through the CPU, IOSurface and
  read-back paths;
* `gl2x/`: the same at Retina scale;
* `world/`: mu-world with the interface;
* `compacted/`.

The movies converted for these runs are in `~/Documents/mu-mac-tools/native/scratch/gfx2/movies`.

## Gaps and next steps

* **Not implemented:**
  * `loadBitmapFromLib` (79 movies);
  * Aux events on Buttons/TextFields (only MovieClips);
  * directional `findFocus`;
  * IME composition text (SDL `TEXTEDITING`): committed text works.
* **Missing data movies.** The skill and item hotkey icons come from the client's data/image movies
  (`gSystem.DataMan`, `gSystem.Image`), which are not loaded, so the slots show counts and cooldowns without
  icons.
* **Chat placeholders.** The chat list shows two authored placeholder rows ("ChatTypeHtml", "longchat :") in
  its empty renderers. The cause is not settled (CLIK list behaviour under Ruffle against GFx).
* **Window placement and labels.** Window positions are the movies' defaults plus `SetAlign(4)` for the
  inventory. The client's design-space placement and GlobalText labels are not wired.
* **Not yet done:**
  * item models (RenderItem3D) over the inventory;
  * the remaining windows (expanded inventory, shops, warehouse);
  * mu-client's world scene;
  * double-buffered surfaces to hide the GPU wait;
  * a shared font library instead of a font per movie.
