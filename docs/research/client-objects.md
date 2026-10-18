# Static map objects: loader, model table and the `.obj` boundary (NATIVE-OBJECTS-001)

This milestone follows how the client turns `Data/World<n>/EncTerrain<n>.obj` into placed map objects (trees,
buildings, the character-select markers) and which model each object type loads. The loader, its record layout and
the per-world model table are reconstructed in C (`reconstructed/objects`) and compared with the client's own
instructions in Unicorn. The native module `native/core/mu_objects` loads and draws objects on the terrain
(`mu-terrain`, `mu-viewer --terrain`).

The installed `.obj` files still do not decode. The client's own loader instructions, run on them, return a map
number that OpenWorld rejects for all 84 files. Every in-scope explanation was checked and ruled out (section 3). The
transformation that makes these files readable therefore happens outside the captured `main.exe` game code, at the
protection boundary. Per scope it was not analysed.

The real placements were then read from a running client (section 6). With the owner's authorization, three short
sessions of a client this project started read the object list CreateObject had built from plain game memory. The
reads are read-only and use no hook. That gives the placements of World1 (Lorencia), World94 (character select),
World95 (login scene) and World142 (Tormenta Island), and the character-select marker 1. The native tools draw them
from local plaintext files.

Labels:

- **Verified**: actual client instructions ran in Unicorn on the pinned captures and matched the authored code.
- **Static**: a reading of decoded instructions that was not executed.
- **Boundary**: the code path leaves what this project may analyse.
- **Live (single run)**: read from the memory of a running client this project started, not instruction-compared.

## Identity

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Third section at `0x01ced000` (x86-linux-capture-04, runtime, same restored text) | `0571c519b1c4eaf97a143d2dd29bf2a3799e56b2f613cda0d084f4b857c1dc6f` |

| Routine (names are ours) | Bytes | SHA-256 (first 16 hex digits) |
|---|---:|---|
| object loader `0x016d9ac5` | 711 | `babafe52f3db3c15` |
| v12 rolling decoder `0x0098c5f2` | 194 | `d848bd43bfc35dcd` |
| record constructor `0x0180778f` | 153 | `67461893b5ed55c8` |
| OpenWorld's object call `0x01828cbf..0x01828d79` | 186 | `63c972a39296dc17` |
| object model pass `0x018392db..0x0184307c` | 40,353 | `7a86ca48279b8220` |
| AccessModel `0x018202b4` | 316 | `80384710c68ecf42` |

## 1. The loading chain (verified)

OpenWorld `0x0182876e` formats `Data\%s\EncTerrain%d.obj` (string `0x01aec490`, the world folder and its number)
and calls the object loader `0x016d9ac5` at `0x01828ce1`. If the returned value is neither the folder number nor
-1, OpenWorld shows "%s file corrupted." and abandons the world load (`0x01828cf0..0x01828d74`).

The loader:

1. `fopen(path, "rb")`; when that fails it shows "%s file not found." (MessageBoxA, SendMessageA) and returns -1.
2. `fseek` to the end, `ftell`, `fseek` back, then `malloc(size)` and one `fread(buffer, 1, size, f)`, `fclose`.
3. `0x0098c5f2(NULL, buffer, size)` (length query), `malloc`, then `0x0098c5f2(plain, buffer, size)`: one call
   over the whole file, so there is no chunking. The decoder holds its 16-byte key and initial value `0x5e` as
   immediates; it reads no data-section key.
4. Plaintext: `u8 version`, `u8 map number`, `i16 count` (also stored sign-extended in `0x0bdb5888`), then `count`
   records. Each record is built in a 0x38-byte local that the constructor `0x0180778f` initialises:

| Record offset | File field | Read when | Default |
|---|---|---|---|
| `+0x00` i16 | type (= model index) | always | 0 |
| `+0x04` f32×3 | position | always | 0 |
| `+0x10` f32×3 | angle (degrees) | always | 0 |
| `+0x28` f32 | scale | always | 1.0 |
| `+0x2c`, `+0x2d` u8 | two flags | version ≥ 1 | 1, 1 |
| `+0x2e` u8 | flag | version ≥ 2 | 1 |
| `+0x1c` f32×3 | light colour | version ≥ 3 | 0 |
| `+0x2f` u8 | hidden flag | version ≥ 4 | 0 |
| `+0x30`, `+0x34` f32 | two values | version ≥ 5 | 0.8, 0.2 |

   Records are therefore 30, 32, 33, 45, 46 or 54 bytes. The version byte is compared with `jl`, so 6..255 read
   like 5. Bytes `+0x02..+0x03` are never written. Each record goes to CreateObject `0x016d8538`.
5. It frees the buffer and returns the map number byte.

The client checks no length. A count larger than the file reads past the buffer, and a negative count reads nothing.
`mu_objects_parse` refuses a truncated plaintext (`MU_OBJECTS_TRUNCATED`); that is an authored choice.

**CreateObject `0x016d8538` (static).** It puts the object in sector `(int)(x/1600)·16 + (int)(y/1600)` and
returns 0 outside 0..15 in either axis. It allocates a 0x3d8-byte object and copies type → `+0x5c`, position →
`+0x158` and `+0x110`, angle → `+0x164`, light colour → `+0xec`, scale → `+0xa0`, the flags `+0x2c..+0x2e` →
`+5..+7`, the values `+0x30`/`+0x34` → `+0xe4`/`+0xe8`. A non-zero hidden flag sets `+0x68` to -2 (otherwise -1).
What those object fields do during the render was not traced.

**Second reader (static).** `0x00e22826`, a thiscall method with `ret 4`, formats `Data\World%d\EncTerrain%d.obj`
(`0x01aaa740`). It reads the file, runs the same two v12 calls and walks the same header. It reads 30-byte records,
plus two bytes only for version 1. It keeps only records inside a rectangle: its argument's tile box grown by 14 × 7
tiles, `(x ∓ 14 + 0.5)·100` and `(y ∓ 7 + 0.5)·100`. Kept records pass through a position conversion (`0x00e23366`)
before CreateObject. It looks like an import of another world's objects into a region. No other string in any
captured section names `.obj`; these are the only two readers.

## 2. Verification

`scripts/validate_objects.py` runs the loader body, the v12 decoder, the constructor, `memcpy` and `memset` as
client code. It models `fopen`/`fseek`/`ftell`/`fread`/`fclose`, `malloc`/`free` and `sprintf` over the file
bytes, points the two import slots at stubs, and replaces CreateObject with a recorder of the 0x38 bytes it
receives. Each case compares the decoded buffer, the return value, the count global and every record with
`reconstructed/objects` (pad bytes excluded). A pure-Python statement of the walk is also compared, and four planted
mistakes in it must be detected. Final local run:

| Check | Cases | Equal |
|---|---:|---:|
| synthetic v12 files, versions 0..7, counts 0..59 and negative, random field bytes | 1,002 | 1,002 (7,979 records) |
| missing file: return -1, MessageBoxA + SendMessageA, no records | 1 | 1 |
| planted mistakes (version off by one, flag defaults 0, light/hidden order, swapped `+0x30`/`+0x34`) | 4 | 4 detected |
| **installed `EncTerrain*.obj`**: client decode equals authored decode, return and count equal | 84 | 84 |
| … of which OpenWorld would accept (return value = folder number) | 84 | **0** |
| … of which the decoded header fits the file length | 84 | **0** |
| model pass, every world 0..199, types 0..299 | 60,000 | 60,000 |

## 3. The installed files (boundary)

All 84 installed `.obj` files carry the same timestamp, 23 Feb 2026 07:51:10. `main.exe` is 40 seconds older
(07:50:30). The `.map`/`.att` files carry dates from 2013 to 2026, mostly 2022. Every file length equals
`4 + count × size` for some record size. Across 84 files that cannot be chance, so whatever was applied preserves
length. The bytes have no period: plaintext of 30-byte records would autocorrelate at multiples of 30, and neither
the raw nor the v12-decoded bytes do (checked on World1 and World4). The first two bytes are a weak function of the map number (for example
worlds 140..143 start `8f 36`, `8e 37`, `8d 34`, `8c 35`). The transform differs per file and mixes little at the
start.

Checks against the client, as the task listed them:

| Question | Finding |
|---|---|
| A different key, version byte or chunking, as in the data tables? | No. One v12 call over the whole file; the key and initial value are immediates; there is no per-record unit. Every v12/XOR3 combination tested (XOR3 with each low-byte variant before or after v12, v12 twice, encoder direction, reversed order) gives chance-level headers (at most 3 of 84). |
| A decode path chosen by a header or version field? | No. Unlike the `.map`/`.att` loaders (`"MAP\x01"`/`"ATT\x01"` → Modulus), the object loader tests no prefix and calls v12 unconditionally. The version byte only selects the record size, after the decode. |
| A data-section key from the runtime capture? | No. v12 reads no global. The three-byte XOR key global `0x01cf0448` does hold `FC CF AB` in the runtime capture, which confirms the data-table finding, but the object path never reads it. |
| A different loader, found through the string xrefs? | No. The only two `.obj` strings lead to `0x016d9ac5` (OpenWorld) and `0x00e22826` (region import). Both use v12 the same way. |
| Hooks on the file path inside `main.exe`? | None found. The loader and the CRT `fopen`/`fread` path (`0x01988f83` → `0x01988d53`, `0x01989230` → `0x0198924d`) contain no jump into another module. The CRT's import slots hold the same values in run10 and capture-04, and capture-04's module map places them in kernel32 and ntdll. |

Run on the installed bytes, the client's own instructions refuse every file (section 2). The running client does
load these worlds, so the bytes `fread` returns at runtime differ from the bytes on disk, or the loader is replaced
at runtime. Neither happens in the captured `main.exe` code. Both captures were taken during initialisation, before
the launcher handshake. Code that `IGC.dll` (WinLicense-protected; it already hooks the frame driver, see
[client-frame-loop.md](client-frame-loop.md)) or the packer installs later, or a hook below the kernel32 import, is
consistent with what we see. **This is the boundary.** Per scope, `IGC.dll`, `RGS.dll`, the packer stub and the
temporary module the capture shows (`Temp\3a1f1109.dll`) were not analysed, and the byte statistics above were not
pursued as cryptanalysis.

## 4. The object model table (verified)

The model pass `0x018392db` loads the world's object models. AccessModel `0x018202b4(index, folder,
name, number)` loads `folder + name + "0N.bmd"` for N < 10, `nameN.bmd` otherwise, `name.bmd` for -1 (formats
`0x01aef968`, `0x01aef994`, `0x01aef904`). The model index equals the object type (CreateObject stores the type in
`+0x5c`).

- **World 0 (Lorencia)** has its own case with named models from `Data\Object1\`: Tree01..13 → types 0..12,
  Grass01..08 → 20..27, Stone01..05 → 30..34, StoneStatue01..03 → 40..42, SteelStatue01 → 43, Tomb01..03 → 44..46,
  FireLight01..02 → 50..51, Bonfire01 → 52, DoungeonGate01 → 55, MerchantAnimal01..02 → 56..57,
  TreasureDrum01 → 58, TreasureChest01 → 59, Ship01 → 60, SteelWall01..03 → 65..67, SteelDoor01 → 68,
  StoneWall01..06 → 69..74, StoneMuWall01..04 → 75..78, Bridge01 → 80, Fence01..04 → 81..84, BridgeStone01 → 85,
  StreetLight01 → 90, Cannon01..03 → 91..93, Curtain01 → 95, Sign01..02 → 96..97, Carriage01..04 → 98..101,
  Straw01..02 → 102..103, Waterspout01 → 105, Well01..04 → 106..109, Hanging01 → 110, Stair01 → 111,
  House01..05 → 115..119, Tent01 → 120, HouseWall01..06 → 121..126, HouseEtc01..03 → 127..129,
  Light01..03 → 130..132, PoseBox01 → 133, Furniture01..07 → 140..146, Candle01 → 150, Beer01..03 → 151..153.
  That is 112 types; all 112 files are installed. It also loads Bird01 (402) and Fish01 (408), which are outside
  the type range.
- **Every other world** loads type t (0..299) from `Data\Object<f>\Object<t+1>.bmd`, where f is world + 1
  except for these event-map groups, chosen by leaf predicates executed as client code: 11..17 and 52 → 12;
  18..23, 53 and 97 → 19; 24..29 and 36 → 25; 45..50, 98 and 99 → 47; 82..90 → 83; 123..127 → 124;
  128..130 → 131; 131 → 132; 132 → 133. World 0x80 loads types 0x42..0x46 from Object129. Between the 83 and 124
  checks the client asks a runtime custom-map table (`0x0095c652(0x5c)` → `0x00d7b35d`/`0x00d7b225`). Its contents
  were not captured; the validator's dummy object answers "no" and the C does not model it.
- Character select (world 0x5d) is generic. Types 13..17 (the slot markers of the character-select finding,
  NATIVE-CHARSEL-001) are `Data\Object94\Object14..18.bmd`; 43 of the
  300 generic files exist in `Object94`.
- Many worlds also load extra models at index ≥ 300 (birds, fish, monster parts, effects) and create a few fixed
  objects directly (CreateObject from the pass itself, e.g. worlds 2, 3, 55, 57, 58). Those are not part of the
  `.obj` table and are not ported.

The validator records every AccessModel and OpenTexture call of the pass for worlds 0..199. Leaf callees (no call,
no indirect jump before their first `ret`) run as client code; this covers the world predicates. Other callees are
skipped and return a zero-filled dummy object: bitmap loads, singletons, the world manager `0x00ea594b` →
`0x00ea280c`, string helpers. Every (world, type) model file equals `mu_objects_model_file`.

## 5. Native module

`native/core/mu_objects.{h,c}`:

- **`mu_objects_load_installed`** decodes `EncTerrain<folder>.obj` like the client and applies OpenWorld's check.
  On the installed files it returns `MU_OBJECTS_FILE_REFUSED`.
- **`mu_objects_load_plain[_file]`** takes the plaintext the client sees after its decode, for when such bytes become
  available.
- **`mu_objects_gallery`** is a labelled demo layout. It puts one object of every model the world loads, in rows on
  the terrain.
- **`mu_objects_load_models`** and **`mu_objects_place`** load the BMD and textures per type. For each object they set
  origin, angles, body scale and light, then pose and skin through `mu_model` and return the model. The front end
  draws it through the mesh-draw port (`mu_scene_draw_model`).

`mu-world` and the character-select session can call the same functions; they were not changed here.

Viewer choices (not client readings):

- action 0 at frame 0 (no object animation);
- body light from the terrain primary light at the object's tile, white in the gallery;
- no sector culling;
- the hidden flag is ignored.

```sh
make -C reconstructed/objects && make -C native all viewer
native/build/mu-terrain objects "$MU_GAME_ROOT" --world 0                  # status 2: refused by the map check
native/build/mu-terrain objects "$MU_GAME_ROOT" --world 93 --objects gallery
native/build/mu-terrain render "$MU_GAME_ROOT" --world 0 --objects gallery --object-tile 150,100 \
    --object-columns 12 --object-spacing 450 --target 17525,12100 --distance 4800 --pitch 38 --yaw -65 \
    --width 1280 --height 800 --out lorencia-gallery.png
native/build/mu-viewer --terrain "$MU_GAME_ROOT" --world 93 --objects gallery     # B toggles objects
native/build/mu-terrain render ROOT --world N --objects PLAIN_FILE          # decoded plaintext, same layout
```

Local renders, not committed, are in `~/Documents/mu-mac-tools/native/renders/objects/`:

- `lorencia-gallery-{gl,soft}.png`: all 112 Lorencia models;
- `world94-gallery-{gl,soft}.png`: the 43 character-select models.

Headless GL and the software rasterizer differ on 6.6 % of pixels by more than 8/255 (Lorencia gallery at
1280×800), in line with the terrain-only baseline.

Tests:

- `reconstructed/objects/test_objects.py` (portable): synthetic v12 files of every version, truncation, negative
  counts, the Lorencia table and the folder groups.
- `native/tests/test_native_objects.py` (portable): a synthetic world tree through `mu-terrain objects/render` and
  the headless viewer, covering records, model table, map check, plaintext input and gallery.
- Private (`MU_RECOVERY_INTEGRATION=1`): every installed file is refused; the World1/World94 galleries load
  112/43 models.
- `tests/test_objects_private.py` runs the Unicorn validator.

## 6. Placements read from the running client (live, single run)

**Authorization and rules.** The owner explicitly authorized a live read. It followed `GAME-LOCK.md`:

- the lock was held from 23:20 to 23:28 on 2026-10-17;
- three client sessions in the play bottle (MuMatrix32, same pinned `main.exe`, same `.obj` files as MuMatrixKit),
  each under 3 minutes and quit right after the read;
- only clients this project started were read;
- no character was moved: FryeZEN2 and Nighty only entered the world and quit; Nighty was the last character
  selected.

`IGC.dll`, `RGS.dll`, the packer and anti-cheat code were not analysed, patched or hooked.

**Method.** `mac-play/diagnostics/objread.c` is a macOS host tool. It is ad-hoc signed with the debugger
entitlement and uses `task_for_pid` and `mach_vm_read_overwrite`. It never writes and never suspends. It reads the
world index `[0x01cf15fc]`, the `.obj` count global `[0x0bdb5888]` and the 256 sector lists at `0x0bdb61f0`. In each
list the head is at `+4` and objects are linked through `+0x354`, as CreateObject builds them (section 1). For each
object it copies the 0x3d8 bytes. `scripts/live_objects_to_plain.py` maps the CreateObject fields back to a record:

- type `+0x5c`;
- position `+0x158` (equal to the start position `+0x110` for every object but the moved marker);
- angle `+0x164`, scale `+0xa0`;
- flags `+5..+7`, light `+0xec`, values `+0xe4`/`+0xe8`.

It writes a plaintext in the loader's layout, choosing the record version the installed file's length implies for
the count.

| Snapshot (when) | World | Count global | Objects in the sectors | Installed file length = 4 + count × size |
|---|---|---:|---:|---|
| login screen | 94 (World95) | 47 | 47 | 1,414 = 4 + 47 × 30 (version 0) |
| character select | 93 (World94) | 237 | 237 | 7,114 = 4 + 237 × 30 (version 0) |
| FryeZEN2 in Lorencia, 145,134 | 0 (World1) | 2,833 | 2,833 | 84,994 = 4 + 2,833 × 30 (version 0) |
| Nighty on Tormenta Island, 135,10 | 141 (World142) | 8,061 | 8,061 | 362,749 = 4 + 8,061 × 45 (version 3) |

In every world the number of linked objects equals the file's count, and the count fits the installed file's
length for exactly one version. That fits the reading that each record became exactly one object. It also suggests
that the transformation preserves the record layout once undone.

**Limits of the reconstruction.**

- Records come out in sector order, not file order.
- Fields the version does not carry are left out.
- Two records each in World94 and World95 hold NaN angles and scale at position (0, 0) (types 0 and 63).
  CreateObject accepted them, so they come from the file.
- A perf agent briefly swapped `opengl32.dll` in the play bottle during the first session (LOCK-INCIDENT-perf009).
  That affects drawing only; the counts above match the installed files, so the reads were not repeated.

**`+0x68 = -2`.** Whole types carry this value at runtime:

- Lorencia: PoseBox01 (133);
- World94: 14, 15, 39, 40, 54..56;
- World95: 38, 54;
- World142: 27 types (2,191 objects).

None of these files is version 4, so the value comes from the worlds' code, not from the hidden byte. The
character-select handler sets it for types 0x26..0x28, 0x36..0x39 (NATIVE-CHARSEL-001). The converter writes those
types to a sidecar `EncTerrain<n>.hidden`, and the native drawer skips them. This is a live reading. With them
skipped, the black slabs of Lorencia's invisible PoseBox objects and the stray cubes in the character-select scene
disappear, and the renders match the client's screenshots.

**Character-select markers (live).** `EncTerrain94.obj` holds only two marker objects:

- type 14 (marker 1) at **(13629.3008, 12338.5654, 164.4998)** (bits `4654f534 4640ca43 43247ff6`);
- type 15 (marker 2) at (−136.21, 17173.0, −1044.95), outside the map.

Types 13, 16 and 17 are absent. The earlier window-capture fit (13617, 12339, 169.5) was 12.3 units off in x. The
z difference is not visible, because the render forces 169.5. `mu_charsel_default_marker1` now holds the read
value. `mu-charsel --objects-dir DIR` takes the markers of a local `EncTerrain94.plain`.

**Native use.** All of these take local plaintexts (`EncTerrain<n>.plain` plus `.hidden` in one directory):

- `mu-world --objects-dir DIR` (objects within the visible box grown by 4 tiles);
- `mu-charsel --objects-dir DIR` (objects and markers);
- `mu-terrain`/`mu-viewer --terrain --objects FILE`.

```sh
make -C mac-play/diagnostics objread                       # macOS host tool
mac-play/diagnostics/build/objread <main.exe pid> snap.bin # client you started, under the lock
scripts/live_objects_to_plain.py snap.bin --installed "$MU_GAME_ROOT/Data/World1/EncTerrain1.obj" \
    --out LOCAL/EncTerrain1.plain                           # decoded game data: keep local
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 0 --tile 145,134 --objects-dir LOCAL
native/build/mu-charsel --game-root "$MU_GAME_ROOT" --objects-dir LOCAL
```

Local renders (not committed), in `~/Documents/mu-mac-tools/native/renders/objects/`:

- `lorencia-live-overview-gl.png`, `lorencia-live-town-{gl,soft}.png`;
- `mu-world-lorencia-145-134-live-objects-gl.png` (compare `live-reference/lorencia-145-134-client.png`);
- `charsel-live-objects-soft.png` (compare `live-reference/charsel-client.png`);
- `mu-world-world142-135-10-live-objects-gl.png`, `world95-login-live-gl.png`.

Lorencia's town has 2,780 of 2,833 objects drawn: the 53 PoseBox objects are skipped. Headless GL and software
differ on 2.7 % of pixels by more than 8/255.

Tests:

- portable: `native/tests/test_native_objects.py` `LiveSnapshotTests` builds synthetic snapshots and checks the
  converter, the version choice, the hidden sidecar, `mu-walk --objects-dir`, and markers and objects in
  `mu-charsel`;
- private: `LiveReadPrivateTests` (`MU_OBJECTS_PLAIN_DIR`) checks the local plaintexts against the installed
  files' lengths and model table.

## Reproduce

```sh
make -C reconstructed/objects
./tools/python/bin/python scripts/validate_objects.py --game-root "$MU_GAME_ROOT" --output /tmp/objects.json
MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=... python3 -m unittest tests.test_objects_private native.tests.test_native_objects
```

The validator's defaults read `evidence/x86-text-capture-09`, `evidence/image-data-run10` and
`evidence/x86-linux-capture-04` (`--text/--data/--section3` override).

## Unresolved and next steps

- **Placements.** Read live for World1, World94, World95 and World142 (section 6). Other worlds need a character
  standing in them; the account's characters were not moved to get them. The installed bytes themselves still
  decode only past the boundary.
- Object lighting, animation, sector visibility and the meaning of `+0x68 = -2` (HiddenMesh: the object is not
  drawn) are now reconstructed and compared: [client-objects-render.md](client-objects-render.md) (NATIVE-OBJECTS-002).
- RenderObjects (sector walk, object light, animation, the meaning of `+5..+7`, `+0x68`, `+0xe4`/`+0xe8`), the
  pass's extra models ≥ 300 and fixed CreateObject calls, the region importer `0x00e22826` and the custom-map
  folder table are not ported.
