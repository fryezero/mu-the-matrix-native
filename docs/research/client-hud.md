# The in-game interface: GFx movies and the game side (NATIVE-HUD-001)

This finding maps the pinned client's in-game interface and continues
[client-ui-2d.md](client-ui-2d.md) and [client-ui-widgets.md](client-ui-widgets.md). It covers:

* the bottom bar with the HP/MP orbs and the skill bar;
* the inventory;
* the character info window;
* the chat;
* the item tooltip.

**Every one of these is a GFx (Scaleform) movie in this client.** The legacy C/GL window layer is still
linked and still runs, but it does not draw these windows. What remains game code around the movies is
restated as C in `reconstructed/hud` and compared with the client's instructions in Unicorn:

* the item grid behind the item windows;
* the 3D item pass that draws item models over a movie's slots;
* the tooltip text and HTML pipeline.

`mu-render ui inventory|tooltip` renders a native inventory and item tooltips from it.

Labels:

* **verified**: the client's instructions ran in Unicorn and their outputs (calls, argument words, object
  state, strings) equalled the reconstruction;
* **live**: compared with a window-only capture of the running game;
* **static**: read from decoded instructions only;
* **inference**: a conclusion from data or context that is not tied to an executed instruction.

The pinned inputs are those of [client-frame-loop.md](client-frame-loop.md): text capture09 `2bd5f2e9…3724`
at `0x00401000` and the second section run10 `c985e2e6…a0672f`.

## Which interface is GFx and which is legacy (static, live)

| Element | Implementation | Creation | Drawing |
|---|---|---|---|
| Bottom bar, HP/MP/SD/AG orbs, EXP bar, skill and item hotkeys | GFx movie `main` | base movie list `0x00af0e0a` | GFx manager `0x00ac3bf7` → `0x00aae6f9` |
| Top menu, map, player name, chat, option, pet, alarm, buff list | GFx movies `topmenu`, `hudMap`, `hudPlayerName`, `chat`, `winOption`, `PetFrame`, `alarmframe`, `bufflist` | same list | same |
| Inventory | GFx `InventoryFrame`; handler class (0x210 bytes, ctor `0x00b907b9`, vtable `0x01a902ac`) with one 8×8 grid page | registry `0x00ac4a79` (`0x00ab7277(1, 8, 8, 1)`) | movie, then the game's item pass (below) |
| Expanded inventory | GFx `ExtensionBagFrame`, two 8×4 pages (`0x00ab7277(2, 8, 4, 2)`) | registry | same |
| Character info | GFx `CharacterInfoFrame` (ctor `0x00b3d0a3`, vtable `0x01a8af60`) | registry | movie |
| Item tooltip | GFx `InfoPopup` (handler `0x00b8d94b`); the text is built by game code | registry | movie |

The GFx registry `0x00ac4a79` creates **139 windows**. Each one gets a handler object and a movie name,
registered through `0x00ac9cc0`, `0x00ac9d74` or `0x00ac9e28`. They include `ServerSelect`,
`CharacterSelect`, the shops, `trade`, `StorageInven`, the mix windows, `MasterSkillTree`, `SkillTree4th/5th`,
the quest and event windows and `IngameShop`. `Data/Interface/GFx` holds the movies (`*.ozg`) and their images
(`*.ozd`).

**The legacy layer.** `0x00f2951e`, called from the title/loading loader `0x0185ad63`, still creates about 30
legacy NewUI windows. They include the classic main frame (`0x00ecf6ad`/`0x00ecf751`, `in_main-New.tga`) and
the skill list (`0x00f16fd3`/`0x00f1706f`). Their manager draws every visible window each frame
(`0x00f19075`: sort by layer, `IsVisible` = vtable +0x18, `Render` = vtable +0). The classic inventory control's
`Create` `0x00f03c75` and image loader `0x00f0380e` have **no references** of any kind: they are dead code in
this build.

**Live view.** The 2026-10-17 window captures show these screens:

* the bottom bar with orbs and hotkeys;
* the inventory and expanded inventory;
* the character info window;
* three tooltips.

All of them are drawn in the GFx style (vector frames, antialiased GDI-free text, HTML-coloured tooltip lines).
No legacy frame is visible, which fits the static map (inference: the legacy main frame is created but not
shown).

**UI pass order** (main-game render `0x0185916b`, static):

1. NewUI system `0xf2b67f` (BeginBitmap, `0x00f19075`, EndBitmap).
2. A hook into a non-captured module (`0x10b3e920`).
3. The GFx manager `0x00aae6f9`.
4. A last 2D pass `0x016b0b74`.

### The GFx boundary

Scaleform itself is not analysed. The game side talks to the movies through:

* callbacks the movie raises (ExternalInterface; method name + `GFx::Value` arguments of 16 bytes, dispatched
  per handler, for example `0x00abce9f`);
* invokes the game makes on the movie (`0x00aae7e0(handler, method, format, …)`).

| Movie | Callbacks to the game | Game → movie |
|---|---|---|
| `main` | `onSkillTooltip(slot, skill)`, `offSkillTooltip`, `onItemTooltip(slot)`, `offItemTooltip`, `onExpTooltip(text)`, `useItemHotKey(slot)`, `registItemHotKey(slot)`, `onHotKey(keyCode)`, `onOpenSkillWindow`, `onSelectSkill(slot)`, `onLoadSkillSlot`, `onLoad` | `setHPMP` (`maxHp`, `maxMp`, `Shield`, `ShieldMax`, `SkillMana`, `SkillManaMax`), `mcItemHotKey`, `mcSkillHotKey`, `mcExpBar`, `mcRide.setRideInfo`, `mcGiantRide.setRideInfo` |
| item frames (`InventoryFrame`, bags, warehouse, shops, mix) | `requestSlotInfo` (slot origin, cell size, cell gap per page), `requestItemSlotClick`, `requestItemSlotDoubleClick`, `requestItemSlotClickR`, `requestItemSlotOver`, `requestItemSlotOut`, `onCloseBtnClick` | `SetZenText`, `SetRuudText`, `InitText` (`Title`, `Zen`, `Ruud`, `Repair`, `Disassemble`, `Divide`, `Bundle`, `ExtensionBag`, `Artifact`), per-class flags (`SetRageFighter`, `SetMagicGladiator`, `SetGhostKnight`), `SocketOptionEnabled`, `SetOptionEnabled` |
| `CharacterInfoFrame` | `onCloseBtnClick`, `OnHotkeyExpand`, `onClickbtnMasterSkillTree`, `OnClick4thSkillTree`, `OnClick5thSkillTree` | `InitText` (`StatButton`, `PentagramButton`, `DetailInfo`, `ResistRate`, `AttackPVE/PVP`, `DefensePVE/PVP`, `ElementalOption`), `SetElementalText`, `SetCharacterName`, `SetVisible` |
| `InfoPopup` | (none for items) | `SetInfoPopup("%d %d %d %d %s", x, y, w, h, html)`, `SetInfoPopupCompareItem`, `SetInfoPopupEx`, `SetInfoPopupDirection`, `CloseInfoPopup` |

Window placement is game code (verified):

* A movie's position (+0x70, +0x74) lives in a 1024 × 768 design space.
* `0x00aae509`/`0x00aae601` shift that position by the movie's view alignment (Scaleform's nine anchors,
  vtable +0x78 of the movie view). Centre: `x - (1024 - W)/2`. Left: `x`. Right: `x - (1024 - W)`.
  Likewise for `y` with 768.
* The GFx manager keeps `640/W` and `480/H` (+0x2cc/+0x2d0, set by `0x00acb333`).

## The item grid (verified)

Every item page is a 0x4c-byte object (constructor `0x00ad322b`, Init `0x00ad341d`). It holds:

* the columns and rows;
* a pixel extent of 26 pixels per cell;
* an `int` per cell with the covering item's id word (+0x64 of the item object);
* a `std::vector` of item pointers.

Each item stores its top-left cell at +0x69/+0x6a. Its size is the Item.bmd record's width and height
(+0x25a/+0x25b, [client-item-attributes.md](client-item-attributes.md)). Routines:

| Routine | Behaviour |
|---|---|
| `0x00ad4e69` / `0x00ad4ee4` / `0x00ad4ff4` | Fit test of a w × h block at a linear cell index: every cell `index + r*cols + c` must be below `cols*rows` and free. **No column-edge test**: a 2-wide item fits at the last column when the next row's first cell is free. |
| `0x00ad49fb` | First free position, row-major, with that test (so it can return a wrapping position). |
| `0x00ad4994` | First free index with the test **and** `index % cols < cols - (w-1)` (no wrap). |
| `0x00ad4a6d` / `0x00ad4ad9` | Free cells; greedy count of w × h placements up to a limit, remembering taken cells in a 128-entry stack list (larger counts write past it). |
| `0x00ad4cb1`, `0x00ad4f11`, `0x00ad4f51` | Grid rectangle `(x, y, x + cols*26, y + rows*26)`, point and rectangle containment. |
| `0x00ad4d43` / `0x00ad4da5` / `0x00ad5037` | Pixel to cell divides by **20** (the classic 20-pixel cell), so the right part of the 26-pixel extent maps to columns past the grid. |
| `0x00ad37c9` / `0x00ad3775` | Place: bounds check, set the cell, fill the cells (no free test), append, then `0x00c94193(item, type, -1)` and the page refresh `0x00ad86dc`. |
| `0x00ad3a4e` | Remove: erase the first match, clear its cells, refresh (also when absent). |
| `0x00ad403c`, `0x00ad3fd9`, `0x00ad3c57`, `0x00ad47f1` | Find by id, item at a cell (a free cell finds an item with id 0), has code, can move (frees one cell, tests `0x00ad4994`, restores). |

The live inventory grid is 8 × 8 cells at a 26-pixel pitch. Its top-left cell is at window (1416, 540) in a
1722 × 1048 client area (live).

## The 3D item pass (verified)

GFx cannot draw MU's 3D items, so for every open window the per-window pass `0x00abfcca` does the following:

1. It walks the manager's `std::list` of windows with reverse iterators (last added first). It skips three
   special windows only when NewUI windows 0x45, 0x37 or 0x3e are open, and always skips one excluded window.
2. `glPushAttrib(0xfffff)`, the movie's `Display` (vtable +0x1c), `glPopAttrib`.
3. It saves the screen rates and the camera matrix.
4. `glMatrixMode(PROJECTION)`, `glPushMatrix`, `glLoadIdentity`, `glViewport(0, 0, W, H)`,
   **`glOrtho(0, W, 0, H, 20, 2000)`**.
5. `MODELVIEW`, push, identity, then it reads the modelview back (`0x0184a569`, glGetFloatv).
6. Depth test and depth mask on (cached), `glClear(DEPTH)`, `glColor4f(1, 1, 1, frame alpha)`.
7. The window's item render (vtable +0x20).
8. The camera restore `0x0184b705`: identity, `glTranslatef(-camera)`, read back, VectorIRotate `0x00cfff3c`.
9. Pop both matrices and restore the rates and matrix.
10. BeginBitmap, `glColor4f(1, 1, 1, 1)`, the window overlay (vtable +0x24), `glColor4f(0, 0, 0, 1)`, EndBitmap.

For the item windows the item render is the slot pass `0x00ab6130`. For each page and each item with
`code >= 0`:

```
x = (frameX + (col*(cellW+gapX) + originX) * scale) * 640/W        # 640 x 480 units
y = (frameY + (row*(cellH+gapY) + originY) * scale) * 480/H
w = width  * cellW * 640/W * scale                                   # the gap is not included
h = height * cellH * 480/H * scale
glColor4f(1, 1, 1, alpha); 0x016c23d5(item, x, y, w, h, page type, page flag, 0,
                                      type-8 seen (sticky across pages), frame, 0, 0.0f, -1, 0, 1, 0)
```

The slot wrapper `0x016c23d5` does three things:

* When the frame is the GFx manager's active frame, the manager is idle and the cursor is in the slot, it raises
  the status refresh `0x00c94193` and the hover/tooltip request `0x00cda1cf`.
* It calls RenderItem3D.
* It calls the count/durability overlay `0x016bf1fb`.

An element record (item +0x84 in 0..5) selects two extra words; that path is not reconstructed.

**RenderItem3D `0x016c154e`, general path:**

* **Selection.** Select comes from the caller or from hovering (cursor in the slot, manager idle, NewUI window
  0x3e or not `0x00f2b602`).
* **Render info.** The item's render info: offset factors, rotation and scale from the map
  `0x06fbb624+0x38` (default record `0x06fbaa40`). The scale is overridden when the argument is above 0.
* **Model.** `model = code + 0xae6`.
* **Position.** `x += w * fx`. `y += h * fy`, or `(1 - fy) * h` when flipped. `z` is -100, or -140 for kind B
  0x6a and -130 for kind A 0x22.
* **Window pixels.** `0x0184a18f` converts back to window pixels with the origin at the bottom:
  `x / (640/W)`, `(480 - y) / (480/H)`.
* **Scale.** `scale *= GFx manager → InventoryFrame handler +0x58`.
* **Output.** RenderObjectScreen `0x016c2d82(model, level word, excellent, set bits, &pos, select, …, scale, …)`,
  with the item angle global `0x0b5e3c2c` = the rotation.

27 item codes take special-case branches with other models, offsets and scales
(`0x103b..0x1088`, `0x1a0b..0x1a4b`, `0x1c09..0x1c64`). They are listed in `item_slots.c` and not reconstructed;
one of them (`0x1c0b`) runs through a runtime patch.

RenderObjectScreen (static) does the following:

* It builds the model's animation with the item angle.
* It spins the selected item (`angle.y = time * 0.2`).
* It enlarges the picked-up item by 1.4.
* It gives armour-part models (`0x18e6..0x1ae5`) model height -160, used only when the root action is locked.
* It passes `o->Scale` unchanged to the model's body scale (`0x017e63f4`).

## The tooltip pipeline (verified for the reconstructed parts)

1. **Builder `0x00f0eb44`** (static).
   * It fills the classic text list: TextList (0xff-byte lines), TextListColor, TextBold and a raw-HTML flag.
     In this client the arrays sit at `0x10c76988`, `0x10c7b938`, `0x10c7ba78` and `0x10c7bbb8`, outside the
     image: a runtime module relocated them.
   * It begins with a call into that module (`0x00f0edf1` → `0x10b3efb0`, 72 bytes NOP-padded, no jumps into
     the gap), then a `GlobalText[0x1308]` line.
   * The table-driven part takes the item's itemtooltip record (name colour, show level, name text, 15 lines of
     {text id, colour, style}). For each line it looks up the itemtooltiptext record and calls the formatter
     when the text's `type` is not -1. It stops at the first missing text.
2. **Formatter `0x00f1098a(this, &out, fmt, line, &colour, type, item, item level, -1)`**.
   * It formats into a 0x100-byte buffer with the C library's `sprintf`.
   * Reconstructed: the 14 types that carry most installed lines (1, 2, 4, 5, 6, 7, 9, 11, 13, 101, 201, 202,
     203, 205). With the -1 (plain text) lines they cover 27,328 of the 31,670 line slots of the installed itemtooltip records (86.3%).
   * Values from other systems are inputs:
     * the requirement getters `0x00cd27eb/2832/2879/298d` (server rules and code special cases);
     * the hero (`0x01d1df1c`: level + master level, strength +0x18a, agility +0x18c, energy +0x190);
     * the harmony/socket stat reduction `0x00f13774` and the socket (`0x011df8b9`) and harmony (`0x00cbc335`)
       defense bonuses.
   * Colour rules:
     * type 2 is yellow when a bonus applies, else blue for kind A 3 with an option level;
     * type 5 turns red below the required level and also rewrites TextListColor;
     * the "lacking" types 201..205 turn the line **and the requirement line above it** red;
     * types 202/203 turn yellow when a harmony/socket reduction applies.
3. **InfoPopup `0x00b8d94b(count)`.** For each line:
   * lines starting with 0 are skipped;
   * `"\n"` gives `<BR>`;
   * raw lines are copied;
   * other lines go through `0x00ab4dc0` with bold **0**;
   * a line containing `starGrade*` becomes `" "` + n `icon_star01` and 5-n `icon_star00` images + `" <br>"`,
     n being its last character (stoi).

   The result is converted ANSI → UTF-8 (`0x00a99d93`) and sent as
   `SetInfoPopup(x/(640/W), y/(480/H), w/(640/W), h/(480/H), html)`. The rectangle comes from the popup state
   (+0x9c/+0xa0, +0x7c..+0x88).
4. **HTML line `0x00ab4dc0(out, text, colour, bold)`.**
   * Empty for `""` and `"\n"`.
   * `<` becomes `&lt;`.
   * `<font color='%s'><b>%s</b></font><br>` when bold is 1, else `<font color='%s'>%s</font><br>`.
   * The colours are the classic text-colour enum: 0 `#FFFFFF`, 1 `#7FB2FF`, 2 `#FF3319`, 3 `#FFCC19`,
     4 `#19FF7F`, 5 `#A00000`, 6 `#FF19FF`, 7 `#0000A0`, 8 `#A06600`, 9 `#00FF00`, 10 `#666666`, 11 `#CC7FCC`,
     12 `#B266FF`, 13 `#E56B0A`, 14 `#800080`, 15 `#FFFF00`, 16 `#00B0F0`, 17 `#00B050`, 18 `#CCFF00`,
     19 `#00FFFF`, 20 `#BCBCBC`, 21 `#C1C469`; others give white.

### Runtime-patched sites

The restored text is a memory capture, so it contains patches a runtime module applied. None of these modules
are analysed:

| Site | Jump target | Handling |
|---|---|---|
| `0x00b8dcc2` (SetInfoPopup arguments) | `0x10b2d160` | The leftover bytes `75 B8` are the tail of `FF 75 B8`. The original was `push eax; push [ebp-0x44]; push [ebp-0x48]` (7 bytes), and the validator executes it, as UI-002 did. |
| `0x00f0edf1` (builder header) | `0x10b3efb0` | Opaque; the builder is not executed. |
| `0x016c1afc` (RenderItem3D case `0x1c0b`) | `0x10b3f080` | Outside the reconstructed general path. |
| `0x016c2ed6` (RenderObjectScreen model selection) | `0x10b22780` | Not reconstructed. |

## Validation

`scripts/validate_hud.py` (on `scripts/client_ui_machine.py`) runs the client routines with an allowlist built
from their static call closure:

* Throw helpers fail the case.
* Functions whose linear extent scan is broken by a patched jump get explicit extents.
* Modelled explicitly: `operator new`/`new[]`/`delete`, `free`, `memset`, `memmove`, `memcpy`, `strlen`,
  `strcmp`, the C++ `ostringstream` (constructor, `<<` on its base at +0x10, `str`), the Boost.Format-style
  formatter (constructor, `%`, `str`), `stoi`, the ANSI→UTF-8 conversion, the client `sprintf` (a C printf
  subset), the GFx manager, frame and NewUI accessors, and the named system inputs.
* The relocated text arrays are mapped at `0x10c70000`.
* `MSVC std::string` objects are read and written with the 16-byte inline buffer, size at +0x10 and capacity at
  +0x14. Strings of 4 KB or more get the big-block alignment header the client's deallocation checks.

Full runs (2026-10-17):

| Section | Cases | Compared |
|---|---:|---|
| grid | 200 (seed 7) | 22,166 steps: return values, every scalar field at the client offsets, the cell array, the item vector and every item's cell after each step, plus 3,695 status/refresh events; 1,725 places, 660 removes, 6,240 fit tests, 4,316 searches, 5,476 pixel tests, 1,079 greedy counts, 109 wrapping placements |
| slots | 300 (seed 3) | 1,454 wrapper calls and their colour calls, all 16 argument words; 523 pages, all ten alignment values |
| pass | 600 (seed 11) | 38,640 GL calls and markers word for word, the camera matrix, eye, rates and state caches after the pass; 1,505 windows, 943 drawn |
| item3d | 3,000 (seed 5) | events, the RenderObjectScreen arguments (incl. position, scale, the item angle global) and the overlay arguments; 2,840 draws, 622 hovers, 1,007 selected, 606 flipped |
| html | 400 (seed 13) | 3,200 single HTML lines and 400 whole tooltips (4,595 lines, 889 star grades, 381 raw lines): the SetInfoPopup words and the UTF-8 HTML |
| format | 3,000 (seed 17) | output string, colour and TextListColor for the 14 types with the installed itemtooltiptext formats (read from `MU_GAME_ROOT`, never written out) |

**Negative controls.** Each of these single-rule mutations of the reconstruction is caught:

* the free-index edge test `<` → `<=`;
* the gap included in the item width;
* z -140 → -130;
* the ortho far plane 2000 → 2048;
* two tooltip colours swapped;
* the lacking rule writing its own line instead of the previous one.

During development the comparisons found these errors:

* the excellent flag needs the item-code range check of `0x00cd0995`;
* the window list is walked back to front;
* a second list entry for the same window shares one alpha (harness);
* the stream base sits at +0x10 (harness).

Portable checks:

* `reconstructed/hud/test_hud.py` holds independent Python statements of the grid, anchoring, slot geometry,
  RenderItem3D, HTML and formatter rules (13 tests). Its private test runs the validator.
* `native/tests/test_native_hud.py` renders a synthetic game root authored in the test (Item.bmd, itemtrsdata,
  itemtooltip, itemtooltiptext, a textured BMD).

## Native module and tool

* `native/core/mu_hud.*` places items with the grid (`0x00ad49fb`), runs the slot pass, the wrapper and
  RenderItem3D, and gives each item's model, position, rotation and scale.
* `mu-render ui inventory` draws:
  * a plain stand-in panel and cell grid at the measured movie geometry (the GFx frame is not reconstructed);
  * the item models with the native model pipeline under `glOrtho(0, W, 0, H, 20, 2000)`;
  * with `--hover N`, the item's tooltip. Its lines come from itemtooltip/itemtooltiptext through the
    reconstructed formatter cases. The UI-001 text path draws them (GDI boundary: CoreText) in the HTML colours;
    `--html-out` writes the InfoPopup HTML.
* `mu-render ui tooltip --item CODE[:LEVEL]` draws one tooltip.
* Without a game root everything is synthetic.

Choices that are not client facts:

* **Render info.** It comes from `Data/Local/itemtrsdata.bmd` (counted 32-byte records, each its own XOR
  unit). The client's loader is not in the restored text. The record is a u32 code and 7 floats. The mapping
  (offsets = floats 1–2, rotation = floats 4–6, scale = float 7, the constant 2000 dropped) is an inference from
  the editor's save routine `0x0112052f` (6 floats per code) and the value ranges.
* **Scale.** The file scales are 0.001–0.004. RenderItem3D's own special cases and the default record use
  0.2–0.6 in the same pixel-orthographic pass, so the loader evidently rescales. The tool multiplies by an
  authored factor (`--item-scale`, default 200), which gives the expected cell-filling sizes.
* **Armour-part models** (helms etc.) are drawn at their skeleton height. The client's lock/height rule
  depends on a per-item action table (`0x06fbc830` via `0x0111d824`) that is not reconstructed.
* **Missing tooltip parts.** The builder's header (runtime-patched), the GlobalText lines, price,
  set/socket/excellent/harmony blocks, full name-colour rules and level-adjusted requirements (`0x00ccf659`)
  are not reproduced.

Renders stay local in `~/Documents/mu-mac-tools/native/renders/hud/`. Live captures are in `…/hud/live/`.

### Live comparison

One session under `GAME-LOCK.md` on 2026-10-17 (21:00–21:06) used bottle MuMatrix32 with a 1722 × 1048 client
area. The character was at the Twisted Karutan spawn. The client was closed afterwards. A note on that client:
another agent's mistaken autologin had restarted it at 21:01 under this agent's lock, with the same character
and position; the captures were taken afterwards and are unaffected. The session captured:

* the world;
* the inventory with the expanded inventory;
* three tooltips;
* the character info window.

Findings:

* **Grid geometry.** It was measured on the capture and is what the native tool uses (by construction, not a
  match): 26-pixel cell pitch with a 1-pixel dark separation, 8 × 8, top-left at (1416, 540), the frame aligned
  to the right edge. The expanded inventory shows two 8 × 4 pages, as the registry creates them.
* **Tooltips.** They show what the pipeline produces:
  * centred lines;
  * the item name first;
  * a blank line (`<BR>`);
  * then lines in white, blue (`#7FB2FF`), yellow, purple and red (`#FF3319`).

  Pixel comparison is not meaningful because the movie renders the HTML.
* **One tooltip against the native one.** The third tooltip is item 6676 (a ring). Its itemtooltip record has
  no table lines, so the native tooltip shows only the name. Everything the live tooltip adds comes from the
  builder's other blocks, which are not reconstructed:
  * `Durability: [30/30]`;
  * the repair line;
  * three blue option lines.
* **3D items.** They sit in their cells with cell-coloured backgrounds drawn by the movie (green when usable,
  red when not; the status refresh `0x00c94193` informs the movie).

## Limits and next steps

* **GFx.** Movies, their layout and their HTML rendering are not reconstructed. A native front end needs either
  a Scaleform-compatible player or authored native windows fed by the boundary above.
* **Not reconstructed:**
  * the tooltip builder `0x00f0eb44` as a whole and the remaining formatter types (0 damage, 103/105/107 time
    and option lines, …), plus the requirement routine `0x00ccf659`;
  * RenderObjectScreen `0x016c2d82` and RenderPartObject `0x017e63f4` (glow levels, excellent/ancient effects);
  * RenderItem3D's 27 special codes;
  * the element record of the wrapper;
  * the overlay `0x016bf1fb` (stack counts and durability bars).
* **The item render-info loader** (and so the true scale conversion) is outside the restored text. A capture of
  the routine that fills `0x06fbb624` would settle it.
* **The legacy NewUI windows** that `0x00f2951e` creates (main frame, skill list, about 30 others) are a further
  legacy-GL slice. The live game does not show them.
