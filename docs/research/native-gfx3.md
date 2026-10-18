# The client's HUD movie, icons, item models and placement (NATIVE-GFX-003)

NATIVE-GFX-002 ([native-gfx2.md](native-gfx2.md)) put the client's GFx windows over the native world with a
pinned Ruffle. It played `main` and `chat` as stand-alone movies and left out the icons, the item models, the
client's window placement and labels. This milestone closes most of that:

* **The HUD runs as the client runs it.** One base movie (`base.swf` → `ExternalBase.swf`) loads the bar, the
  chat and the other HUD movies through its own UI loader. The layer answers its channels as the client's
  handlers do.
* **Icons.** The skill slots show the client's skill sheets from `ImageData`. The item hotkeys show the game
  image `image0`, into which the host renders the item models. `loadBitmapFromLib` works for the 79 movies that
  use it.
* **Item models** are drawn over the inventory cells, as the client's per-window item pass does:
  RenderItem3D's placement and the world item render's glow levels.
* **Client placement and labels.** The window registry's alignment and the window creator's scale rule come
  from the client. The menu takes the client's form, with GlobalText placeholders. Both are compared with the
  client's instructions in Unicorn.
* **Smaller items.**
  * The chat's leftover rows are gone.
  * IME composition text shows in the chat input.
  * The interface appears in mu-client's world scene.
  * Double-buffered shared surfaces remove the GPU wait.

Labels:

* **verified**: the client's instructions ran in Unicorn (`scripts/validate_gfx3.py`). Their output equals the
  layer's.
* **static**: read from decoded instructions or from the movies' ActionScript (decompiled locally with JPEXS;
  nothing committed).
* **observed**: run on this Mac (Apple M5, macOS 27) under the patched Ruffle.
* **inference**, **layer choice**: as in the earlier notes.

Scaleform's own code inside the client is not analysed. The pinned inputs are those of
[client-hud.md](client-hud.md): text capture09 `2bd5f2e9…3724` and the second image section run10
`c985e2e6…a0672f`.

## 1. The HUD is one base movie

**What the client does** (static):

1. The GFx manager creates `base.swf` as its base movie (string at `0x01a85fe4`, set-up near `0x00aef02e`) and
   sets `_root.isClient`.
2. `base.swf`'s frame 1 defines `onLoad`. It loads `ExternalBase.swf` into `_root.base` with a
   `MovieClipLoader` and reports `base onLoad`.
3. `ExternalBase.swf`'s frame 1 defines `onLoad`, which calls `UI.onFileLoad()` and `DataMan.onFileLoad()`.
   They are `core.KeyMovieClip`s. Each reports its channel with its path: `UIFrame onLoad _level0.base.UI` and
   `ASData onLoad _level0.base.DataMan`.
4. The client's `UIFrame` handler (`0x00c8ed86`) answers `onLoad` with **LoadFrameFiles** (`0x00c8f05d`,
   **verified**):

   ```
   {mcData: [ImageData], mcTopLevel: [Tooltip, Popups], mcBottomFrame: [main],
    mcBottom: [ItemDurability, Chat, AlarmFrame, topmenu, bufflist],
    mcBottomHud: [hudPlayerName, hudMap, hudNotice]}
   ```

   It ignores `onFileLoad`.
5. ExternalBase's `core.MovieLoader` loads every name as `<name>.swf`. When a movie has loaded, its
   `onLoadComplete` calls `onFileLoad` on the loaded movie's clips. Those report their own channels:

   | Channel | Path |
   |---|---|
   | `main` | `…mcBottomFrame.main_1.mc` |
   | `chat` | `…mcBottom.Chat_2.instance96` |
   | `topmenu`, `alarmframe`, `bufflist`, `hudMap`, … | their own paths |

   After the last movie, `UIFrame onFileLoad` follows.
6. The game sends `changeScene` on scene changes. Scene 6 is `GameScene.Main` (`0x00c8eeec`).

The HUD movies then share one player:

* `_global` is shared, so `gSystem.Image`, `gSystem.DataMan` and `gSystem.isMainScene` are set.
* `_root` is `base.swf`, so `_root.getBitmap(n)` is the base movie's `loadBitmap("image" + n)`.

**Two GFx behaviours Ruffle lacked** are patch 0006 (observed in synthetic tests and on the client's movies):

* a movie root's frame-1 `onLoad` runs after the frame. This applies to a level and to a movie loaded into a
  clip;
* `MovieClipLoader.onLoadComplete` is broadcast with `onLoadInit`, after the loaded movie's first frame. This
  fits GFx loading local files synchronously; the client's `onLoadComplete` needs the loaded clips.

**Movie loading.** mugfx now has a navigator (`native/gfx/mugfx/src/navigator.rs`). It loads `loadClip` names
from the root movie's directory:

* `\` counts as a separator;
* the file name alone is tried next;
* names also match case-insensitively. The movies name files `datas\ImageData`, `frame\main` or `Icons.swf`,
  and the client installs them flat.

`mugfx_resolve` reports the file a name maps to.

**The layer (base mode).** When the movie directory holds `base.swf`, `mu_gfx_layer.c` opens it as the HUD
player. Without it, the NATIVE-GFX-002 stand-alone players remain (`standalone`).

* **Channel answers:**
  * `UIFrame onLoad` → `LoadFrameFiles`, with the client's list limited to the converted movies. A missing movie
    would keep the loader waiting.
  * `UIFrame onFileLoad` → `changeScene(6)`.
  * `ASData onLoad` → the skill table.
  * `main onLoad` → menu, gauges, hotkeys.
  * `chat onLoad` → `InitData`.
* The chat plays inside the base player. The layer's chat movie aliases it.
* Opening runs the loader to completion: 12 movies in about 300 ms (observed).

Renders (local, `~/Documents/mu-mac-tools/native/renders/gfx3/`):

* the whole client HUD: bar, top menu with the location, alarm frame, chat, ride buttons;
* the windows over it.

## 2. Icons

### Skill icons (`ImageData`, ASData)

`SkillHotKey.UpdateSkillInfo` looks the slot's skill up in `gSystem.DataMan.skill`. `ImageData`'s `ImageLoader`
then cuts the icon out of one of its sheets. The sheet is picked by `SkillUseType`:

| SkillUseType | Sheet |
|---|---|
| 0, 1 | `Icon_Skill` |
| 3, 4 | master |
| 7..9 | 4th |
| 14 | 5th |

The cell is `Magic_Icon` in a 25 × 18 grid (static).

The client fills the table with `skill.setSkillAll([...])`. The SkillInfo builder `0x00c5ebaa` reads a record
of the in-memory skill table `0x06fbb138` (lookup `0x00961620`):

| Member | Record offset |
|---|---|
| `Index` | +4 |
| `Magic_Icon` | +0x8c |
| `Name` | +8, std::string |
| `Delay` | +0x38 |
| `SkillUseType` | +0x58 |
| `MasteryType` | +0x50 |

Records whose first byte is set are skipped. This mapping is **verified**.

That table is built from `Skill(kor).txt` in the encrypted `Data/Lang.mpr` ([client-data-tables.md](client-data-tables.md)),
which is out of reach. The installed `Data/Local/skill.bmd` decodes with the classic per-record XOR
`FC CF AB`. Its layout:

* 120-byte records, 750 of them, plus a 4-byte checksum;
* the name at +0 in CP949;
* `MasteryType` at +54, `SkillUseType` at +55, `Magic_Icon` at +74.

The restored code never loads it (NATIVE-DATA-002), so using it is an **inference**. The icon numbers it gives
(`Magic_Icon` = index for the first skills) produce the expected icons: Poison, Meteorite, Lightning, Fire Ball,
Flame (observed).

`world_gfx_game.c` reads it (`wg_skills_load`, 514 skills) and passes it to `mu_gfx_layer_set_skills`. Names stay
the placeholders "Skill N": the file's names are Korean, and the build's English names are in Lang.mpr. Without
a game root the layer uses icon = index.

### Item hotkey icons (`image0`)

`Frame.mainAssets.ItemHotKey.DrawIcon` draws `gSystem.Image.DrawRootImg(icon, 0, renderX, renderY, renderW,
renderH)`. The image is `_root.getBitmap(0)` → `loadBitmap("image0")`, a 64 × 64 placeholder external image
of `base.swf`. It is drawn as a bitmap fill with the matrix `scale(1, -1)`, so the movie reads the image
bottom-up: a GL texture. The client:

* renders the hotkey items into it (`0x00c55607`: the item, the render rectangle, 512.0 and 2.0 to
  `0x00aef562`);
* registers `image0` when the bar loads (`0x00c71f4b`, after `InitMenuInfo`);
* sends `setItemHotKeyAll` with `renderX/Y/W/H` per slot.

The render rectangles (`0x00c552b1`, static): x from 0 in steps of 32 (`0x01a9c2cc`), y += 32 when x passes the
image width; each icon 20 × 20 (double `20.0` at `0x01a83c80`). The routine sits in a larger hotkey rebuild with
STL map iteration and was not executed.

**Host images.** Patch 0007 adds `Player::set_gfx_image`. `BitmapData.loadBitmap(name)` returns a host image
by that name before it looks at the library, and the image's pixels are shared. A movie that already drew the
bitmap sees updated pixels (observed: red, then green, without re-attaching). `mugfx_set_image` exposes it.

The layer:

* lays the hotkeys out as above;
* asks the host to render the items into a 512 × 512 RGBA image with rows bottom-up (`icons` callback); without
  one it draws coloured stand-ins;
* sets `image0` **before** sending `setItemHotKeyAll`, because `DrawIcon` fetches the bitmap while
  `setItemHotKeyAll` runs.

In mu-world the host renders the item models into an offscreen framebuffer with the inventory's RenderItem3D
path, treating the image as a 640 × 480 screen, and reads it back (`wg_items_icons`). The demo healing potion
appears in slot Q (observed).

### `loadBitmapFromLib`

The 79 movies call `MUComponent.GetIconBitmapData(name)` → `mcIcon.loadBitmapFromLib(name)`:

* `mcIcon` is the clip into which `SetIconFile("Icons.swf")` loaded the icon library with a `MovieClipLoader`;
* `loadBitmapFromLib` is a function that `Icons.swf`'s frame 1 defines: `return BitmapData.loadBitmap(name)`;
* it resolves `icon_N` in the icon movie's own library (AVM1 closures keep their defining clip).

With the navigator it works unchanged. It needs no patch (observed):

* `PartyFrame`'s buff slots show `icon_1`, `icon_5`, `icon_9` and `icon_20`. Render:
  `renders/gfx3/icons/partyframe-buffs.png`;
* a synthetic test movie checks the same path.

`Icons.swf` must be converted next to the window movies.

## 3. Item models over the inventory

GFx cannot draw MU's items. For every open window, the client's per-window item pass `0x00abfcca` draws them
after the movie (verified in NATIVE-HUD-001). The layer now calls the host's `items` callback right after the
inventory movie, with each item's slot-pass output:

* the 640 × 480 slot call of `mu_slot_pass` (`0x00ab6130`);
* the cell rectangle;
* the window scale;
* whether the cursor is over the item.

The held item comes at the end with `held`.

`world_gfx_game.c` (mu-world, mu-client):

1. **Placement.** The slot wrapper `0x016c23d5` and RenderItem3D's general path `0x016c154e` (reconstructed
   NATIVE-HUD-001 code) give model, position, rotation and scale. Render info comes from `itemtrsdata.bmd` with
   NATIVE-HUD-001's authored scale factor 200.
2. **Model state.** RenderObjectScreen's static readings apply: the hovered item spins (`angle.y = time·0.2`)
   and the held item is enlarged 1.4×.
3. **Glow.** The model draws with the world item render passes `mu_renderchar_draw_item` (NATIVE-RENDERCHAR-001)
   by level. +5 gets the bluish body light (0.30, 0.42, 0.60); +7 and up get the shine passes. The draws go
   through the GL mesh-draw port.
4. **Pass state.** As `0x00abfcca`: `glOrtho(0, W, 0, H, 20, 2000)` over the stage, depth cleared per window.

Inferences and layer choices:

* **Light terms.** RenderPartObject `0x017e63f4` is not reconstructed. The item model's lighting flag is
  cleared and the light terms are 0.4/0.8/0.2, as in the world item render (inference).
* **Armour textures.** The armour-part item models (`Data/Item/HelmMale02.bmd`, …) have their textures in
  `Data/Player`. The loader falls back there when `Data/Item` lacks them (installed files).
* **Armour height.** Armour parts (groups 7..11) are posed at skeleton height. The client places them through
  a per-item action table (`0x06fbc830`, not reconstructed), so the stand-in centres the transformed model on
  its cells vertically (layer choice). NATIVE-HUD-001's renders showed the same gap.

Without a game root, or in `mu-gfx-window`, the coloured boxes remain. Renders: `renders/gfx3/world/`
(mu-world) and `renders/gfx3/client/` (mu-client).

## 4. Client placement and labels

**Window registry** (`0x00ac4a79`, static: each registration pushes alignment, flag, name; 139 windows parsed):

| Window | Alignment |
|---|---|
| InventoryFrame | 11 (`MUDefines.Align_Right`) |
| CharacterInfoFrame | 9 (`Align_None`) |
| InfoPopup | 9 (`Align_None`) |

NATIVE-GFX-002 used 4 (RightCenter) for the inventory.

**Window creator** `0x00ac9edc` (verified, 80 cases over random window sizes, both alignments):

* When the window height (`0x01cf1628`) is below 700, it sends `SetScale(83)` for most windows. The exceptions:
  `SetScale(90)` for MasterSkillTree; `SetScale(77)` for SimpleUI and SimpleUISubWin; none for Caution, the
  info popups, PlayGuide and IngameShop. SwitchMode gets `SetScale(H/768·100)`.
* `SetScale` also stores scale/100 in the handler at +0x58, which RenderItem3D multiplies in.
* Unless the alignment is 9, it sends `SetAlign(alignment)` and `SetWindowSize(window width, window height)`
  (`0x00aae4ae` also sets the movie's viewport).
* The movie's `MUComponent.SetWindowSize` then places itself. For `Align_Right`: x = width − window width,
  y scaled by the height ratio.

The layer sends the same invokes for the same sizes. The item pass, tooltips and cell centres use the window
scale.

**InitMenuInfo** (`0x00c71fc2` with helpers `0x00c72580`/`0x00c725e6`, verified):

* `keyCode` is a menu id, not a key code. `key` and `label` are GlobalText strings, with one literal `CTRL+T`.
* The structure:

  | Group | keyCode | key | label | subMenu |
  |---|---:|---|---|---|
  | IngameShop | 0 | GT 0xd5c | GT 0xd5d | — |
  | CharacterInfo | 1 | GT 0xd5e | GT 0xd5f | — |
  | Inventory | −1 | — | GT 0xd61 | ids 13, 14, 15 |
  | Quest | −1 | — | GT 0xd63 | ids 2, 22 (`CTRL+T`) |
  | Community | −1 | — | GT 0xd64 | ids 9..12 |
  | System | −1 | — | GT 0xd65 | ids 4, 5, 7, 8 |

* The menu dispatcher `0x00c714bd` (static): id 1 toggles CharacterInfoFrame (`0x00c733cf`). Ids 13/14/15 toggle
  PetInventoryFrame / **InventoryFrame** (`0x00c73a2f`) / GremoryCase.

The Unicorn comparison corrected the first static reading, which had attached the submenus to the wrong groups.

Because the ids are not key codes, `Frame.Main.onKeyUp` (it matches `Key.getCode()` against them) does not
produce the window hotkeys. In the client they come from the game's own key scan, which is not reconstructed.
The layer maps I/V, C and Esc itself (layer choice) and no longer calls `onKeyUp`. Menu clicks map id 1 and
id 14.

**Labels from Lang.mpr.** The GlobalText strings are in `Data/Lang.mpr`, whose entries are encrypted with a
password behind the protection boundary ([client-data-tables.md](client-data-tables.md)). Placeholders:

* menu entries with a known role get English stand-ins: In-game shop, Character, Inventory, Pet inventory,
  Gremory case, the group names;
* the others read "GlobalText <n>" (`MU_GFX_GT_IDS=1` shows the numbers everywhere);
* the inventory/character `InitText` labels, the chat's `InitData` names and the top menu's map name ("World N")
  stay English stand-ins;
* skill names are "Skill N".

Strings that come from game data the repository reads:

* item names and tooltips (Item.bmd, itemtooltip/itemtooltiptext);
* the client's literal `CTRL+T`;
* the window and channel names.

**Other HUD state.**

* The top menu gets `setMapName`/`setPosition` from the host (mu-world: hero cell).
* The alarm frame's ranking, PC-room and play-time boxes start hidden. Offline there are no such events
  (layer choice). Their default contents had shown dev text.

## 5. Chat and IME

**The leftover rows.** NATIVE-GFX-002's chat showed "ChatTypeHtml" and "longchat :" rows. They are the last
lines of `ChatView.testChatType`, which `configUI` runs when `gSystem.isClient` is false. Inside the client's
base movie the chat no longer runs it (observed: only the real lines in `renders/gfx3/*/8-chat-sent.png`). The
stand-alone mode keeps the NATIVE-GFX-002 behaviour.

**IME.** mugfx passes compositions to Ruffle's IME preedit (`mugfx_ime`, `ImeEvent::Preedit/Commit`):

* the SDL front end sends `SDL_TEXTEDITING` to `mu_gfx_layer_compose`;
* the composing text shows in the chat input with its caret;
* the committed text replaces it.

The client's own IME movie (`IME.swf`, candidate list) is not played (layer choice).

## 6. mu-client's world scene

`mu-client --gfx DIR [--gfx-open …]`:

* opens the layer when the world scene's embed is created, after its GL set-up, and closes it with the embed;
* composites the interface after the world in the GL path;
* routes window events to it first.

Only the world-scene path of `client/main.c` changed. A headless `--auto` run shows the HUD and inventory models
on both world visits (`renders/gfx3/client/`).

## 7. Double-buffered surfaces and cost

`mugfx_set_double_buffer` gives a shared movie two IOSurfaces. A frame renders into the back one. The host keeps
sampling the last completed one: completion is tracked with `on_submitted_work_done`, and the shown surface's
seed changes when it flips. The layer then skips the GPU wait, and frames show at most one frame later. It is on
by default in mu-world/mu-client (`MU_GFX_SINGLE_BUFFER=1` turns it off) and `--double` in `mu-gfx-window`.

Cost per frame (`mu-gfx-window --headless-gl --bench --open`, 600 frames, 1280 × 800, bar + inventory +
character; three runs each):

| Mode | Frame | GPU wait |
|---|---:|---:|
| stand-alone players (NATIVE-GFX-002 movies) | 1.28–1.65 ms | 0.87–1.24 ms |
| base movie | 2.34–2.54 ms | 1.38–1.47 ms |
| base movie, double-buffered | 1.96–2.02 ms | 0 |

The base movie holds the whole HUD (top menu to bar). It therefore renders at window size, and more of its
movies animate (240 against 121 renders of the bar).

## Verification

**Unicorn** (`scripts/validate_gfx3.py --cases 40 --mutations`, 2026-10-18). The client routines run with the
GFx value API stubbed (object/array creation, member setters, array pushes, Invoke; object values as
references). Their output is compared with the layer's invokes from the stand-in library log:

| Section | Compared | Result |
|---|---|---|
| loadlist | `0x00c8f05d` | equal: 5 slots, 12 movies |
| menu | `0x00c71fc2` + helpers | equal: 6 groups, 19 entries, 32 GlobalText numbers |
| skill | `0x00c5ebaa` over 40 synthetic records | the 6 members and their offsets |
| window | `0x00ac9edc` + `0x00aaebca`/`0x00aae4ae` for 40 window sizes (the 699/700 boundary included) × alignments 11 and 9 | 80 cases, equal invokes |

Five planted mistakes are caught:

* a list without hudNotice;
* the submenus swapped;
* `Magic_Icon` read from +0x90;
* inventory alignment 4;
* a scale threshold of 768.

**Tests.** `native/tests/test_native_gfx3.py` has 12 tests. Run on 2026-10-18 with mugfx built,
`MU_RECOVERY_INTEGRATION=1` and Unicorn: 12/12 pass. The NATIVE-GFX-001/002 suites (26 tests) also pass.

* **Portable (CI):**
  * the patch series;
  * the base-movie flow on the stand-in library (ABI 3: base movie, `set_image`, `resolve`, `ime`);
  * placement and scale at 1280 × 800 and 1024 × 600;
  * menu ids;
  * IME;
  * item draws;
  * the skill.bmd decoder on a synthetic file.
* **With mugfx (skipped in CI):** synthetic movies for:
  * root `onLoad`, child `onLoad`, `onLoadComplete` after the first frame;
  * `loadClip` with `datas\icons.swf` and case-insensitive names;
  * `loadBitmapFromLib` (width 4);
  * host images: `getPixel32`, then updated pixels on an attached bitmap;
  * IME preedit/commit;
  * double buffering: the seed alternates, the output stays correct.
* **Private:**
  * the client's 17 HUD/window movies convert and the layer runs the base movie on the real library: channels,
    the full list, `changeScene`, `image0`, inventory, item draws;
  * the Unicorn validator with its planted mistakes.

Renders (local) in `~/Documents/mu-mac-tools/native/renders/gfx3/`:

* `cpu/`, `gl/`, `gl2x/` and `gl-double/`: the scripted `mu-gfx-window` run;
* `world/`: mu-world with the inventory and character window, item models and hotkey icon;
* `client/`: mu-client's world scene;
* `icons/`: PartyFrame buffs through `loadBitmapFromLib`, and the bar's skill sheet and `image0` test.

## Gaps and next steps

* **Not reconstructed:**
  * the item hotkey rebuild around `0x00c552b1` (static only);
  * RenderPartObject's light and the armour-part height rule;
  * the client's key scan for window hotkeys;
  * the `IME.swf` candidate movie.
* **Blocked:** the GlobalText strings, skill names and map names (encrypted Lang.mpr).
* **Remaining windows.** The expanded inventory, shops, warehouse, PartyFrame, bufflist data, Tooltip/Popups
  content, `hudMap`/`hudPlayerName` and `ItemDurability` are loaded but get no game data.
* **Cost.** The base movie renders at window size. Cropping its view to the visible HUD parts, or splitting
  it, would save GPU time. A shared font library is still open.
