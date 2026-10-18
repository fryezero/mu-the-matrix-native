# Client terrain: formats, tile rules and the native terrain mode (NATIVE-TERRAIN-001, TERRAIN-001)

This finding recovers how the client loads and draws a world's terrain, reconstructs those rules in C
(`reconstructed/terrain`), checks them against the client's own instructions, and adds a terrain mode to the
native viewer (`native/`). Static map objects are not drawn: the installed `EncTerrain*.obj` files do not
decode with the routine the captured loader calls (section 5).

## Identity and method

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Dispatch flag at `0x0bdd1cc8` (trig-state-15) | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |

Routines were found from the file-name strings (`Data\%s\EncTerrain%d.map` at `0x01aec34c` and its
neighbours) through `OpenWorld` `0x0182876e`. Byte counts and digests (first 16 hex digits) of the routines
read:

| Routine | Bytes | SHA-256 |
|---|---:|---|
| OpenWorld `0x0182876e` | 3305 | `41471ed5b0a73a91…` |
| tile bitmaps `0x01829457` | 2506 | `1ac6a024c3458ba1…` |
| map loader `0x016c991d` | 711 | `76e2d3c2c7a8f0f7…` |
| attribute loader `0x016c9da0` | 961 | `9a108b3e6011566f…` |
| object loader `0x016d9ac5` | 711 | `babafe52f3db3c15…` |
| 8-bit height `0x016c8391` / 24-bit height `0x016c8746` | 571 / 550 | `69d926e1f16cf4ec…` / `bf3926e781d5d4e0…` |
| light map `0x0185b243` | 546 | `3d7178c9bf54cf89…` |
| CreateTerrainNormal `0x016c8ab6`, FaceNormalize `0x00d01206` | 560, 707 | `b661e617b8de4625…`, `65ffdcf0493c3e4d…` |
| CreateTerrainLight `0x016c8ce6` | 490 | `9b5f9957185cd4c6…` |
| per-frame update `0x016ca4fa` | 1505 | `51047cfb12068b0d…` |
| RenderTerrain `0x016cd468` | 473 | `13ab21a1d5a1dc66…` |
| RenderTerrainTile `0x016ccda5` | 1731 | `331b9d1013b9ce7e…` |
| RenderTerrainFace `0x016cff65` | 6427 | `5606172700f4a42a…` |
| FaceTexture `0x016cfd4c`, RenderFace `0x016cf46c` | 537, 1646 | `0c65c4e0d4464765…`, `7cf63f00b1ce5362…` |

Names are ours. "Static reading" below means decoded instructions only; "compared" means the authored C was
run against the actual instructions in Unicorn (`scripts/validate_terrain.py`) and agreed bit for bit.

## 1. File formats (compared on every installed file)

World index `w` is the client global `[0x01cf15fc]`; its folder is `Data\World<w+1>` except for event-map
groups (`0x018308d6`: Blood Castle → 12, Chaos Castle → 19, Kalima → 25, `0x66` → 103, 82..90 → 83,
123..127 → 124). Lorencia is world 0 (World1). Twisted Karutan is world 142 (World143; the client names
`Object143\twistedKarutan_sand02.jpg`).

* **`EncTerrain<n>.map`** (`0x016c991d`). `"MAP\x01"` then a Modulus envelope decoded by `0x016ced37`, the
  routine BMD v14 uses (here decoded with `model-recovery/modulus.cpp`); without the prefix the v12 rolling
  cipher `0x0098c5f2`. Plaintext: version byte (ignored), map-number byte (returned and compared with the
  folder number), 64 KiB layer 1 → `0x0b735420`, 64 KiB layer 2 → `0x0b745420`, 64 KiB alpha bytes stored as
  `byte / 255.0f` → `0x0b755420`. The client reads 196,610 bytes without a length check.
* **`EncTerrain<n>.att`** (`0x016c9da0`). `"ATT\x01"` + Modulus, else v12; then the three-byte XOR
  `0x00976855`. Its key at `0x01cf0448` is outside the captured data; `FC CF AB` is inferred because every
  installed file then yields version 0, width 255, height 255 and the folder's map number. Length must be
  0x20004 (16-bit cells) or 0x10004 (8-bit cells), else −1. Cells are stored `& 0xfaff`; a bad header or a
  low byte ≥ 0x80 shows "file corrupted" (`0x016cef3f`) and returns −1.
* **`TerrainHeight.OZB`**. Two loaders, chosen by `0x016c9868(w)`:
  * 8-bit `0x016c8391`: skips 4 bytes, reads `0x438 + 0x10000` bytes, heights are bytes at offset `0x438` of
    that block (file offset `0x43c`), rows in file order, `× 1.5f` (`× 3.0f` for world 55). The BMP header is
    never parsed. Its `bfOffBits` (`0x436`) is 2 bytes earlier, so the client's grid is the BMP pixel array
    shifted by two cells.
  * 24-bit `0x016c8746`: skips 4 + 14 + 40 bytes; per cell `b2 | b1 << 8 | b0 << 16`, converted through
    binary64, `+ -500.0f`.
  * The selector's literal checks name worlds 0x2a, 0x3f, 82..90, 100, 101, 110..112, 122..133. Otherwise a
    virtual call on a runtime world object (`0x00ea594b` → `0x00ea2713`) decides. NATIVE-TERRAIN-002 resolved
    it: only the handlers of worlds 134..145 answer 1 ([client-terrain-frame.md](client-terrain-frame.md));
    the viewer no longer uses the file length (World67 has a 24-bit file the client reads as 8-bit).
* **`TerrainLight.OZB`** (`0x0185b243` via `0x016cb561`): skips 4 bytes, reads the 14+40-byte headers,
  then `width × height` triples from file offset 58 in file order as `(R, G, B) / 255.0f` →
  `0x0bb75430`. **`TerrainLight_2.OZB`** (`0x016cb624`, World38 and World146 only) gives an additive offset
  `byte / 255 × 2 − 1` → `0x0bc35430` (zero when absent).
* **Tile bitmaps** (`0x01829457`, bitmap id `0x7630 + index`): 0..13 `TileGrass01/02`, `TileGround01..03`,
  `TileWater01`, `TileWood01`, `TileRock01..07` (`.jpg` → `.OZJ`), 14 `AlphaTile01.Tga`, 15..98
  `ExtTile01..84.jpg`, 115..198 `ExtTile01..84.tga`; grass `0x7694 + layer1` = `TileGrass01..05.tga`
  (worlds ≥ 141: `TileGrass01/02`, `TileGround01..03`, `TileWater01`, `TileWood01`, `TileRock01..07` `.tga`).
  Some worlds substitute `AlphaTile*` or `Object64\song_lava1.jpg`. The loader passes GL_NEAREST (`0x2600`)
  and GL_REPEAT (`0x2901`), GL_LINEAR only for `TileGrass01_R.jpg`. That is the static reading of its
  arguments; the texture manager that applies them was not traced.

**TERRAIN-001, the three rejected height images.** `World11`, `World19` and `World42` `TerrainHeight.OZB`
(66,620 bytes each) have inconsistent BMP headers (24-bit claim, zero prefix, wrong length). The client never
reads those headers. All three are 8-bit worlds, and the fixed-offset rule above reads 65,536 height bytes
from each. They are valid terrain inputs, not damaged files; their decoded heights went through the client's
own loop (section 4).

## 2. Derived grids (compared)

* **Normals** `0x016c8ab6`: per cell, FaceNormalize of `((x+1)·100, y·100, h(x+1,y))`,
  `((x+1)·100, (y+1)·100, h(x+1,y+1))`, `(x·100, (y+1)·100, h(x,y+1))` (repeat indexing `0x016d34db`).
  FaceNormalize forms the cross product in binary32, takes `(double)(float)sqrt((double)s)` and divides
  each component in binary64, leaving zero when the length is exactly 0.
* **Primary light** `0x016c8ce6`: `lum = clamp(n·L + 0.5, 0, 1)` with `L = (0.5, −0.5, 0.5)` (world 30:
  `(0.5, −1, 1)`), `primary = light map × lum` → `0x0bab5430`.
* **Per frame** `0x016ca4fa`: the frame light `0x0b9f5430` is the primary light over the visible box
  grown by 3 (dynamic lights are added later by other routines, not ported). The wave grid `0x0b634ea8` is
  `sin(x·5 + phase)·10` with `phase = ((int)t % 720000)·0.002` (alternate flag `[0x01ec3254]`:
  `% 36000 · 0.01`). It is `x·50` for worlds 8, 80/81, 110/111 and `×60` for 57/58. A second grid
  `0x0b674ea8` (scale 15, `% 36000 · 0.008`) exists for 80/81, 110/111, 141, 142 and 144. `t` is the
  wall-clock float `[0x06fce370]`.

## 3. Tile draw rules (compared)

RenderTerrain `0x016cd468` sets the opaque state, walks the visible box in 4×4 blocks (`0x016d2e8e`,
`0x016d2d81`, rows outer) and calls RenderTerrainTile for each tile. It then sets
`0x0184a990(1)` and repeats the walk as the grass pass when `[0x01cf15d8]` is set (cleared for
Chaos Castle and world 30) and the world is not 7, 128..130 or 94. Per tile (`xf = xi`, `yf = yi`):

* corners `(xi,yi)`, `(xi+1,yi)`, `(xi+1,yi+1)`, `(xi,yi+1)` at `100·x`, `100·y`, height; attribute bit
  0x40 replaces a corner height by `[0x01cf15dc]`; bit 0x08 skips the tile;
* **face texture**: layer 2 when all four alpha values ≥ 1 and attribute bit 0x4000 is clear, otherwise
  layer 1 (water, layer 5, scrolls: `u += ((int)t % 20000)/20000`, `v += (cos(t·0.0001)+1)·0.25`, wave
  amplitude 0.0015);
* **UVs** (FaceTexture `0x016cfd4c`): `64/width`, `64/height` per tile. The wave term of corners 2 and 3
  uses the indices of corners **1 and 0**, a client quirk; the "natural" indices fail the negative control;
* **RenderFace** `0x016cf46c`: state opaque (`0x0184a7f3`), or alpha (`0x0184a990(1)`) for tile 14 and a few
  world-specific tiles; `glBegin(GL_TRIANGLE_FAN)`, then per corner `glTexCoord2f`,
  `glColor3fv(frame light + light offset)` and `glVertex3fv`;
* **alpha layer** (`0x016cfb31`): when any alpha > 0 and layer 1 was drawn, layer 2 (unless 255) under the
  alpha state with `glColor4f(light, alpha)`;
* **grass** (pass 2, `0x016d1074..0x016d187f`): where every alpha ≤ 0, layer 1 < 99 and the grass bitmap
  exists, one `GL_QUADS` blade: corner 3 = corner 0 and corner 1 = corner 2 (the tile diagonal); corners 0
  and 1 are raised by twice the bitmap height, moved −50 in x and swayed in y by the wave (second wave in
  the worlds above). `u = xf·0.25 + column[yi & 255]` with `column = (rand() % 4)/4` from the map loader's
  CRT `rand()`.

Not reconstructed (the C reports the tile as unsupported and emits nothing more): per-world water/texture
animations (worlds 30, 34, 63, 82..90, 94, 100/101, 110..112, 122, 138, 140, 141), the additive animated
layer of worlds 7/128..130/133, the 0x4000 neighbour face at graphics option ≥ 4, the 0x2000 faces of
113/145, and Chaos Castle's random effects. Lorencia and Twisted Karutan use none of them.

## 4. Verification

`scripts/validate_terrain.py` maps the pinned sections, a GDT for SEH frames and the uncaptured globals.
It records GL imports at stub addresses (slot names from `scripts/client_frame_static.py`) and the three
state wrappers and the bind at their entries. Substituted, and labelled in its report: the texture-manager
lookups `0x00ebbec8`/`0x00c97ce3` (authored bitmap records), the singleton getter `0x00db747f`, CRT
`fseek`/`fread` in the light-map loop, `free`/`fclose`/the error box in the attribute tail, and the XOR key
bytes. Results of the final local run:

| Check | Cases | Bitwise equal |
|---|---:|---:|
| XOR `0x00976855` | 20 | 20 |
| FaceNormalize, synthetic incl. ±0/inf/NaN/huge | 400 | 371 (+29 where only the generated-NaN sign differs: x86 0xffc00000, arm64 0x7fc00000) |
| CreateTerrainNormal / CreateTerrainLight, synthetic grids | 3 / 6 | 3 / 6 |
| FaceTexture UVs / tile corners | 300 / 300 | 300 / 300 |
| per-tile GL streams, synthetic worlds 0, 1, 2, 3, 4, 8, 142, 80, 141, both passes | 2,700 | 2,432 (268 reported unsupported, none differing) |
| RenderTerrain through the grass pass, two boxes | 2 | 2 (4,081 and 2,482 calls) |
| frame update `0x016ca4fa`, 8 world/time/box sets | 8 | 8 (light copy, wave, wave2) |
| height / light-map / attribute / map loops, synthetic | 5 / 3 / 6 / 1 | all |
| installed: every 8-bit and 24-bit height file through the client loops | 55 + 27 | 55 + 27 |
| installed: every `TerrainLight*.OZB` | 87 | 87 |
| installed: every `.att` (including two `*_Server_64k.att` the client refuses by size) | 90 | 90 |
| installed: every `.map` layer/alpha tail | 82 | see `validate.log` (re-run pending at writing) |
| installed Lorencia and Twisted Karutan: normals, primary light | 2 + 2 | all |
| installed Lorencia and Twisted Karutan: every tile 0..254² in both passes | 130,050 each | all, none unsupported |

The native mode's corpus pass (`mu-terrain scan`) loads 82 of 83 world folders (World116 ships no `.map`).
Every map and attribute number equals its folder number: 72 Modulus maps, 10 v12 maps, 71 Modulus and 12
v12 attribute files. `native/tests/test_native_terrain.py` checks the library against the Python statements
of these rules and runs the tool on a synthetic world tree.

## 5. Static objects: blocked

The object loader `0x016d9ac5` decodes `EncTerrain<n>.obj` with `0x0098c5f2` and reads: version, map
number, int16 count, then per record int16 type, position, angle, scale and version-dependent extras (30,
32, 33, 45, 46 or 54 bytes). Every installed `.obj` length (dated Feb 2026, like `main.exe`) equals
`4 + count × size` for some version. Decoded with `0x0098c5f2`, however, none has a plausible header. The
bytes are high-entropy, and a constant keystream over the inner cipher does not fit either. The
transformation therefore happens outside the captured `main.exe` code path (possibly in the protection
DLLs' file layer, which is out of scope and was not analysed). The C parser handles the client layout
(synthetic files round-trip); `mu-terrain` reports `obj_status` 2 for all 82 installed files. Object
placement and `Object<n>\` models are not drawn.

## 6. Native terrain mode

`native/core/mu_terrain.c` loads a world (decryption, parsers, height/light rules, normals, primary light,
grass table with the MSVC `rand()` recurrence from seed 1, the client's real seed being unknown, and tile
bitmaps). It feeds RenderTerrain's stream to the software rasterizer (now with fan/quad assembly) or to
OpenGL:

```sh
make -C native && make -C native viewer
native/build/mu-terrain render "$MU_GAME_ROOT" --world 0 --out lorencia.png --pitch 60 --distance 32000
native/build/mu-viewer --terrain "$MU_GAME_ROOT" --world 142        # WASD/QE, drag, wheel, Space, G, O
```

Viewer choices, not client readings: state mapping of the wrappers to GL, alpha reference 0.25, LEQUAL, no
fog, white light map when the file is absent, every tile drawn (no frustum tests), `[0x01cf15dc]` = 0.
Headless GL agrees with the software renderer up to rasterization differences: 3.5 % (Lorencia) and 8 %
(Karutan) of pixels differ by more than 8/255 at 1280×800, mostly along nearest-sampled texel and grass
edges. The windowed view ran at about 13 fps with every tile drawn in immediate mode.

## Unresolved

NATIVE-TERRAIN-002 ([client-terrain-frame.md](client-terrain-frame.md)) resolved the 24-bit height choice and
ported dynamic lights, the world-specific tiles, decals and the frustum box; what remains of the list below is
noted there.

* `.obj` decoding (section 5), hence objects, their BMD models and object lighting.
* Runtime-object predicates: the 24-bit height choice for unlisted worlds, the event check `0x00db747f`
  in RenderFace, the graphics option `[[0x01d22c7c]+0x2c]` and the TerrainLight file name for 123..127.
* Dynamic lights added to `0x0b9f5430`, the special height `[0x01cf15dc]`, the CRT `rand()` seed, the client's
  alpha reference, fog and texture-manager behaviour for missing files.
* The unported world-specific branches listed in section 3, terrain decals `0x016cdd5f`, and the frustum box
  `0x016cbe7b`.
