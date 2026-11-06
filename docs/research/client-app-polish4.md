# Window name and inventory item render info (APP-POLISH-004)

APP-POLISH-004 follows up three APP-REFRESH-005 notes: the diagnostic window title, wing 0x2491 overflowing its
inventory cells, and two tooling problems. Labels: **verified** = the original instructions ran under Unicorn and
agreed with compiled native code; **static** = an instruction reading that was not executed; **inference** = a
conclusion from values.

Inputs: the pinned restored text at `0x00401000` (capture09) and second image section at `0x01a7c000` (run10)
(`scripts/pins.py`), the pinned langread snapshot `lang3.bin` (SHA-256 `f07b4c02…62a3`; `lang4.bin` holds the
same 4,919 ItemTRSData records), and the installed `Data/Local/itemtrsdata.bmd` for the comparison with the old
native source. Import slots are named with the pinned Wine DLLs of `scripts/client_frame_static.py`.

## 1. Window name

- **Verified.** The window routine `0x012114c5` builds a `std::wstring` from `L"MU"` (`0x01ac7a88`, constructor
  `0x00aafcc2` at `0x012114e0`). When the battle-core query `0x0095fb99` is true it appends `L"_BATTLE_CORE"`
  (`0x01ac7a90`, `0x00ae45f9` at `0x0121150c`). After `RegisterClassExW` (`0x012115ad`) it passes the same
  string as class name and window name to `CreateWindowExW` (slot `0x01a7c8b0`): `0x01211646` full screen,
  `0x01211686` windowed. Unicorn runs the routine up to that call with the query false and true: `MU`/`MU` and
  `MU_BATTLE_CORE`/`MU_BATTLE_CORE`.
- **Static.** The only `SetWindowTextW` (slot `0x01a7c8b8`) call, `0x010aef4b` in `0x010aee60`, rebuilds the
  same name (`0x01ab9efc`, `0x01ab9f04`) and appends `L" onStreaming"` (`0x01ab9f20`) when the streaming toggle
  is on. No code writes a scene or frame rate into the title.
- **Native.** `mu-client`'s title is `--title` (the preview app passes its product name and the offline note,
  "Mu The Matrix Native Preview — OFFLINE PREVIEW (no server connection)", the Info.plist display name plus the
  documented disclosure), else `MU_WINDOW_TITLE` = `"MU"`. The `  scene N name  F fps` suffix (NATIVE-PERF-001)
  is now a diagnostic behind `--title-stats` or `MU_TITLE_STATS=1`. Battle-core and streaming modes do not exist
  natively.

## 2. How the original fits an item model into its inventory cells

- **Render info (verified).** RenderItem3D `0x016c154e` calls `0x011204db(code)` on ItemTRSData `0x06fbb624`
  (`0x016c1613..0x016c161b`). That find walks the `std::map` at `+0x38` and returns node `+0x14`, or the default
  record `0x06fbaa40` on a miss (`0x01120519`). The record is copied at `0x016c1624`. RenderItem3D reads
  `+0`/`+4` (slot offset factors, `0x016c162d..0x016c163c`), `+8..+0x10` (rotation through `0x00cfc8f2` into the
  item angle `0x0b5e3c2c`) and `+0x14` (scale, unless the caller's override is above zero, `0x016c165a..0x016c1671`).
  The default record comes from the static initializer `0x008dcce0`: rotation `(-90, 0, 0)` (`0x0098a0e5`,
  `0x01a7e954` = -90), offsets 0.5/0.5 (`0x01a7df14`) and scale 0.55 (`0x01a800c0`), copied by `0x0112154a`.
  Unicorn runs that initializer to build the record.
- **Where the map comes from (static).** ItemTRSData is one of the Lang.mpr script tables. The table manager
  `0x0115eceb` names it `ItemTRSData` (`0x01abd660`), and the item editor `0x00ae9c61` reloads it from
  `./Data/Lang.mpr`. Native read `Data/Local/itemtrsdata.bmd` instead, scaled by NATIVE-HUD-001's authored factor
  200. That file has 2,252 codes, while the map has 4,919. 2,667 codes, including wing 0x19ab (model 0x2491),
  fell back to the default record. For 2,066 of the shared codes the map's scale is exactly 220 × the file's
  (inference: the file is a stale export; the client never reads it).
- **Fit.** The item's scale is the record's scale × the GFx InventoryFrame handler's `+0x58`
  (`reconstructed/hud`, verified by NATIVE-HUD-001). RenderObjectScreen `0x016c2d82` hands `o->Scale` unchanged to
  the body scale (`0x017e63f4`). Nothing measures the model's bounds.
- **No clipping (static).** The per-window item pass `0x00abfcca` sets `glViewport(0, 0, W, H)` (`0x00abfe0f`)
  and draws every model under one window-wide orthographic projection. The image has a single `glScissor`
  call (slot `0x01a7c720`), `0x006124a7` in the GFx renderer's viewport method `0x00612340`. That method enables
  `GL_SCISSOR_TEST` (`0x00612485`) for the Scaleform display only. The other two `GL_SCISSOR_TEST` sites,
  `0x00add729` and `0x00c90bd9`, disable it. The direct-call closure of the item pass, the slot wrapper,
  RenderItem3D and RenderObjectScreen (5,761 functions) contains none of these sites, no stencil call and no
  `GL_CLIP_PLANE0` site. The frame's own display call (`0x00abfdd5`, virtual) runs inside
  `glPushAttrib(0xfffff)`/`glPopAttrib` (`0x00abfdc6`/`0x00abfdd8`), before the models. A model that is larger
  than its cells therefore overlaps the neighbouring cells in the original too.

### Wing 0x19ab

| | Native before (bmd: absent → default) | Original map (lang3/lang4) |
|---|---|---|
| Offset x, y | 0.5, 0.5 | 0.5, 0.44 |
| Rotation | -90, 0, 0 | 270, 0, 2 |
| Scale | 0.55 | 0.44 |

The wing is 20% smaller and sits higher in its cells. With the original's own record its left feathers
still reach past the left edge of the grid in column 0 (render below). That is the original's fit: no scissor,
no bounds scaling. Weapons absent from the file (e.g. 55 and 2612) were drawn edge-on at the default -90°; they
now get the map's rotations.

Across all 4,919 codes, the map's values differ from the old native source for 4,878: 4,333 draw larger
(2,083 by exactly 1.1 ×), 449 smaller, and the rest differ only in offset or rotation. 41 are unchanged.

## 3. Native implementation

- `scripts/live_lang_to_plain.py` writes `itemtrs.tsv` (code and six signed binary32 words) from ItemTRSData
  `0x06fbb624` (manager `+0xbc4`, map `+0x38`, record node `+0x14`) when the snapshot holds it.
- `native/core/mu_lang.c` loads it (`mu_lang_item_trs`: 1 with the record, 0 when absent, -1 without the table).
  The row loader now holds up to six values per key; the other tables keep their columns.
- `native/core/mu_hud.c`'s `mu_hud_item_trs` is the resolver. It returns the map record, or the default record for
  an absent code. Without the table it falls back to the old `itemtrsdata.bmd` × 200 stand-in. The GFx item pass
  (`native/world/world_gfx_game.c`) and `mu_hud_inventory_pass_at` (`mu-render ui inventory`) both call it.
  No renderchar body, executor or effect code changes.

## 4. Comparison

`scripts/validate_app_polish4.py` (row `validate_app_polish4`) maps lang3 at its original addresses
(`validate_lang.LangMachine`):

| Family | Cases | Mismatches |
|---|---:|---:|
| `trs_lookup`: `0x011204db` for every key and 357 absent codes vs `mu_lang_item_trs` over the exported TSV, six words bit for bit | 5,276 | 0 |
| `render_item3d`: slot wrapper `0x016c23d5` + RenderItem3D with the real map and the initializer's default record vs `mu_hud_item_trs` + reconstructed wrapper/RenderItem3D, every RenderObjectScreen argument and the angle | 5,207 | 0 |
| `window_name`: `0x012114c5` to CreateWindowExW, battle core off/on; native `MU_WINDOW_TITLE` | 2 | 0 |

The `render_item3d` family covers every map key RenderItem3D does not special-case, plus the absent codes. It
always includes 0x19ab, and draws inventory geometry at 1280 × 800 to 1920 × 1080 with frame scales 0.5–2.
Eight compiled or source mutants are caught: scale × factor, offset y from x, rotation order, a map miss that
uses itemtrsdata.bmd (the probe carries a synthetic bmd table for every code), an absent code returning the first row, a five-column load, the converter reading one word late, and
`MU_WINDOW_TITLE` "Mu".

Modelled, not client code: the GFx manager, hover and NewUI queries are synthetic, as in `validate_hud`'s item3d.
RenderObjectScreen and the overlay are recording boundaries. The window routine's imports return fixed values.

## 5. Tooling

- `native/tests/test_native_item_textures.py` puts its own folder on `sys.path`, so
  `python -m unittest native.tests.test_native_item_textures` from the repository root imports `native_fixtures`
  (as APP-POLISH-001 did for `test_native_data_manifest`).
- **The network guard under `nice`.** macOS removes `DYLD_*` variables when it executes a SIP-protected binary.
  `DYLD_INSERT_LIBRARIES=libmu-nonet.dylib nice -n 10 mu-client …` therefore runs without the guard: no report,
  and sockets are not refused. `scripts/guarded_run.py` sets the guard and `MU_NONET_REPORT` in the program's own
  environment and lowers the priority in the child (`os.nice` before exec, `--nice N`, default 10). It refuses a
  SIP-protected program between itself and the client. It fails (exit 3) when the guard's report is missing,
  because the library writes that report when it loads. The documented command:

  ```sh
  nice -n 10 tools/python/bin/python scripts/guarded_run.py --guard "<App>/Contents/Frameworks/libmu-nonet.dylib" \
      --report nonet.json [--strict] -- "<App>/Contents/MacOS/mu-client" <args>
  ```

  `test_native_app.PreviewApp.test_guard_stays_active_under_the_documented_nice_command` runs exactly that
  through `/usr/bin/nice`. It checks that the probe's socket is refused at niceness +10 and that the report is
  written. It also covers `--nice` and `--strict`, the refusal of a protected launcher, and a hardened-runtime
  program that never loads the guard (exit 3). With SIP on, it records the trap itself: the guard named in front
  of `/usr/bin/nice` never loads. The preview app's own launcher was never affected; it sets the variable for
  `mu-client` itself.

## Limits

- The original's battle-core and streaming title variants are not ported (no such modes).
- The inventory comparison stops at RenderObjectScreen's arguments. Model pixels are the existing native renderer.
  No live inventory capture compares the wing's pixels with the original client.
- The installed preview's `Native Data/lang` predates `itemtrs.tsv`. Until a refresh adds the file, the app keeps
  the old `itemtrsdata.bmd` stand-in.
- The codes RenderItem3D special-cases keep their existing reconstructed paths (validated by
  `validate_render_items`). The `render_item3d` family skips them; `trs_lookup` still covers their records.
- Indirect calls (virtual or function pointers) are not followed by the static closure in section 2.
