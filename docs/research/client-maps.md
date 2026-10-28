# Maps and travel: the map overlay, the Move window, gates, teleports (NATIVE-MAP-001)

Pinned inputs: restored text capture09 (`2bd5f2e9…3724`) at `0x00401000`, second image section run10
(`c985e2e6…a0672f`) at `0x01a7c000`, and the NATIVE-LANG-001 langread snapshot (`lang4.bin`, local) for the
GlobalText, Gate and movereq(kor) tables.

Labels:

- **Verified**: the client's instructions ran in Unicorn (`scripts/validate_map.py`) and equalled the C in
  `reconstructed/map`.
- **Static**: a reading of the instructions that was not run.
- **Live**: observed in the running client (our own session, game lock, 2026-10-22).
- **Demo**: a choice of the native offline server, not client or server data.

## Where the "minimap loader" is

NATIVE-DATA-001/002 found no loader for `Data/Local/minimap.bmd`. There is none to find in this build. The map overlay
is the GFx movie **hudMap** (a child of the base movie, `mcBottomHud`), toggled with **Tab** by the movie itself
(`HUD.hudMap.onKeyDown`, key 9 → `EventCall("showMap", b)`). Its data comes from three places:

| Data | Source | Evidence |
|---|---|---|
| World image | `./Data/Interface/GFx/Navimap/navimap%02d.ozp` with world + 1 (`LoadWorldMap 0x00c6b116`); the movie loads `NaviMap/<name>`; the files are 512 × 512 PNG behind a 4-byte copy of the PNG signature | static (the formatter needs the CRT locale machinery); 82 installed files, Navimap01 = Lorencia |
| NPC / portal markers | the **server**: opcode `0xE7` sub 3 (`0x0126d85c` → `0x00c6b550`) and sub 4 (`0x0123134b` → `0x00c6b5c5`, no name) | verified |
| Monster / user dots | opcode `0xE7` sub 5 (`0x01233c9b` → AddDetectedUnit `0x00c6b6c2`) | verified |
| Party icons | the party list (`0x00c6b2cc`: members on the hero's world, the hero skipped) | static |

`minimap.bmd` is a leftover, like `skill.bmd` (NATIVE-DATA-002).

## The overlay's game side (window object; methods in the vtable slots at `0x01a8651c` and `0x01a86538`)

- **OnCall `0x00c6aba6`** (verified). `showMap(b)`: when b is set, the blocked areas `0x00c6bc46` (world `0x72`
  three rectangles, world `0x73` always, world `0x4f` two rectangles; all but `0x73` print GlobalText `0x1076`) and a
  missing image (`+0x4e == 0` → the same notice) refuse it; else `+0x4c = b`, `setShowMap(b)` and the request **C1 E7
  01** (shown) / **C1 E7 02** (hidden). `baseMovie{hero, map}` keeps the movie values at `+0x20` / `+0x30`. `onLoad`
  calls InitData `0x00c6b89f`: `MaxPartyCount` 5 and ten key-help texts (GlobalText `0x106b..0x1075`, `0x106f`
  skipped).
- **Per frame `0x00c6af22`** (verified). While shown: the hero marker's `_rotation = 225 − angle.z` (sent when it
  changed, cached at `+0x48`); the map's `_x = −(x/100 · 2)`, `_y = −((256 − y/100) · 2)` from the hero position
  (cached at `+0x40`/`+0x44`; the comparisons are `ucomiss` with the NaN case sending).
- **Tile → map pixels**: `0x00c6ba5c` x·2, `0x00c6ba7d` (256 − y)·2 (verified through addUnit and the update).
- **Records** `0x00c6b550`: `[4]` key, `[5]` type (0 portal, 1 NPC; state 6 = Cursed Temple stone), `[6]` state,
  `[7]` 0 add / 1 remove / other ignored, `[8]`, `[9]` tile, `[10..]` name (verified).
- **Teleports** clear the overlay (`ClearWorldMap 0x00c6b292`, which also hides it), LoadWorld `0x0182876e` loads the
  next image.

Live (Lorencia 140,135): the overlay is the semi-transparent map centred on the hero with NPC and portal labels
("Dungeon Entrance") and the key help bottom right; the native GFx route draws the same movie
(`renders/map/live/02-tab-map.png` vs `renders/map/gfx/frame-0060.png`, local).

## The Move window (MoveCommand, "Warps Window")

The move manager is a lazily built singleton `[0x01d22d44]` (getter `0x00b2d5b2`, 0x40-byte object, ctor
`0x00d3b4cb`). Its vector at `+4` holds 0x18-byte entries built from the movereq(kor) table's key list:
`+0` key, `+4` record `+0x44`, `+8` list position, `+0xc` record `+0x48`, `+0x10` key, `+0x14` enabled, `+0x15` strife,
`+0x16` clicked. The key list is emptied after the build.

| Routine | What | Status |
|---|---|---|
| ctor `0x00d3b4cb` | one entry per key, in key-list order | verified |
| sort `0x00d3b325(order)` | MSVC `std::sort` (`_Sort 0x00d3c25a`) by `+8` / `+4` / `+0xc`; the keys tie, so the C ports the algorithm (median of nine, fat partition, insertion sort ≤ 32, heap fallback) | verified |
| strife flags `0x00bdbf82` | clears, then sets the listed keys by record id; three lists (`{0x2a}`, `{0x1c,0x1d,0x21,0x2a,0x2d}`, `{0x2a}`), chosen through a jump into a runtime-patched region | static; live MTM-1: only key 42 (Vulcanus) |
| availability `0x00bdc0c7` | level `0x00a00367` ≥ record `+0x38` and zen ≥ `+0x34` (× 50 when hero `+0x1f` > 4); then the name rules: GlobalText `0x37` (Icarus) needs wings, a flying helper or the flight state; prefix `0x25` (Atlans) always; `0x29d` (Kalima) the window's `+0x7c`; `0xa7e` refused when `0x01072a7f`; `0x3a`+k (k < 8) the two event checks; strife needs hero `+0x1e` | verified |
| rows `0x00bdd08d` | SetMoveMapList rows: orderIdx, strStrife (GlobalText `0xbab`), strMap, strLv, strZen (`_itoa`), btnChecked (favourites `+0x8c`, `0x00bdcaf3`), bDisabled, mapIdx; ClearFavorMap; AddMoveMapDataByMapIndex per favourite | verified |
| click `0x00bdc813` | refused unless enabled; `+0x16 = 1`; world 30/34/79 or key 24/44/48 stops the MU Helper (C1 BF 51 01 when it ran); closes three windows; the request **C1 0B 8E 02 key32 map16 FF** (`0x00b3b866`; the key is the server's 8E 01 value through the opaque `0x00cda52b`) | verified |
| InitFixtedText | GlobalText `0x3a5, 0xbac, 0x3a6, 0x3a7, 0x3a8, 0x1426, 0x1442, 0xd66, 0x3ea, 0x14dd, 0x14de, 0x14df` | static |

Live: the manager held 69 entries in record-id order (entry `+8` equals the record's id: key 1 Arena id 0, key 90
BattleGrounds id 1, …), which is the default list order on screen; every map was enabled for Nighty except Aquila's
Temple (needs 1,650, Nighty 400 + 1,200 master), so the level getter is the total level.

## Gates

There is a client-side entrance test, MoveHero's `0x016a4608` (verified for the gate, refusals and request): skipped
while LoadingWorld ≠ 0 or the hero is busy, and in worlds `0x2d..0x32`, `0x62..0x63`; then every Gate record in key
order with flag 1 on the current world whose rectangle holds the hero tile: below the entrance's minimum level →
LoadingWorld 50 and GlobalText 350 with `%d`; a target in world 10 / `0x84` (Icarus) without wings
(slot 7 kind 6), Uniria/Dinorant/Fenrir, a flying item or hero `+0x3230` → GlobalText 263; a target `0x24e` in
world `0x7a` opens a quest window (static); else, unless the request flag/3 s rule throttles it, the request
**C1 00 1C 00 gate16 00 00** (XORed bytes 3..7, sent with the C3 flag), LoadingWorld 9999999, and for world 30/31 the
MU Helper stop and `Data\Macro.txt`. The server teleports.

## The teleport answer (C3 1C, `0x0128136d`, static)

`[4]` number (0: same map), `[6]` world, `[8]` `[9]` tile, `[10]` direction. Position ((x + 0.5) · 100), angle
(dir − 1) · 45, height from the terrain (+90 in worlds 8/10/`0x84`, else +30, Dinorant aside). A different world:
ClearWorldMap, the current world, LoadWorld `0x0182876e` **synchronously inside the packet handler**, the chat notice
`"%s%s"` (map name, GlobalText 484 " - Welcome"), LoadingWorld = 30 (the render skips while ≥ 30; MoveHero counts it
down first). Live: a Lorencia → Noria warp shows no loading picture (frames 0.4 s apart), and both warps landed inside
the target gate's rectangle (Noria 172,114 in gate 27; Lorencia 137,127 in gate 17).

## Native

- `reconstructed/map` (`map.h`, `map_hud.c`, `map_move.c`, `map_gate.c`); `make -C reconstructed/map`, portable
  `reconstructed/map/test_map.py`.
- `native/core/mu_map.*`: the session (the move manager in record-id order, strife key 42, gates, LoadingWorld,
  favourites) and the **demo server**: a move or gate request lands on a random tile of the target gate's rectangle
  (the zen cost taken), the overlay's units are the world's entrance gates named "<map> Entrance" (demo text).
- **Travel API** (for NATIVE-QUEST-002's "Go Now" and scripts): `mu_map_travel_to(session, world, x, y)`,
  `mu_map_travel_move(session, key)`, and `mu_map_take_teleport` which mu-world polls every frame.
- `native/world/main.c` (mu-world, mu-walk, mu-client through `world_embed.c`; since WORLD-RT-001 `world/world_rt.c` and `world/parts/`): the gate test each logic step; a
  teleport to another world unloads and reloads with the existing loader (`load()`), keeps the clock, applies the
  character's equipment again, keeps the start world's demo files there only, and prints the notice.
  `--travel-script "F:move:KEY F:to:WORLD:X:Y F:rows F:sort:N F:click:ROW F:tab F:mwin F:mclick:ROW"`, `--no-map`.
- `native/world/world_gfx_map.c`: hudMap's game side over the GFx layer (InitData, LoadWorldMap, addUnit,
  showMap → setShowMap, the per-frame `_rotation` / `_x` / `_y`), MoveCommand (InitFixtedText, SetMoveMapList, sort,
  favourites, row click, View Map → onShowMap); M toggles the window (layer choice). `mu_gfx_layer` gained the
  MoveCommand movie and `mu_gfx_layer_set_map_hooks`; `gfxconvert.py` writes `NaviMap/navimapNN.ozp` as plain PNG.

## Verification

`scripts/validate_map.py --snapshot lang4.bin --cases 500 --mutations` (`tools/python`, captures under `evidence/`):
families hud_update, units, detected, show (+ InitData), move_build, move_sort (also synthetic vectors up to 300
entries with ties), availability, rows, click, gates (the snapshot's 625 gates): 5,001 cases (500 per family, 501 with InitData), 0 mismatches; 10 planted mistakes
(one per family) all detected. Portable: `reconstructed/map/test_map.py` (10), `native/tests/test_native_map.py`
(6 synthetic two-world travel cases + 1 private Lorencia → Noria → Lorencia). GFx route (local, real movies under
Ruffle): the Tab overlay, the Move window list (same rows as the live window), a row click travelling to Noria with
the new image and units (`renders/map/gfx/`, `renders/map/gfx-travel/`).

## Gaps

- The `navimap%02d` formatter, the teleport handler, InitFixtedText and the strife list choice are static readings.
- The demo overlay shows portals only (the real server also sends NPCs); party icons and the detector list are not
  fed; the Cursed Temple stones and the event world map (world `0x73`) are not played.
- The Move window opens where its movie asks (centred); the client places it on the left.
- mu-client's scene state keeps the join world after a travel (music and charsel return use it).
- The move key transform `0x00cda52b` and the network layer stay outside (the demo ignores the key).

## NATIVE-POLISH-001 map follow-ups

The pinned target and captures are unchanged. The restored text SHA-256 is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; the second section is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

The scene host now mirrors the loaded walk world's index and folder every frame, and retains the current
tile and direction per demo character when returning to character select. A synthetic two-world gate test
travels, returns to select and re-enters the destination. The home demo files retain their world association
across embed lifetimes; deleting a character clears its remembered join before that slot can be reused.
This is offline server persistence in memory.

The MoveCommand registration at `0x00ac66f8..0x00ac6722` pushes alignment **10**, not 9. The actual argument
slice runs in `validate_map_polish.py`; string-handle construction and registry insertion are modelled.
The native layer sends SetAlign 10 and SetWindowSize. `validate_gfx3.py --cases 20 --mutations` now compares
MoveCommand as well as the other two windows, 60 window cases, with all five existing mutants detected.

The demo server builds E7 sub-3 NPC records from the loaded world's NPC actors, using the client NPC-name
table with the demo label as fallback. `mu_map_unit_packet` remains the instruction-verified decoder. The
feed retains NPCs across showMap requests, clears them on world reload, and restores the home world's
actors when returning. Synthetic integration checks cover four NPCs plus one portal, an empty destination,
and return. A private GFx run shows 11 NPC markers plus five portals after Lorencia → Noria → Lorencia.
These are demo spawn positions. Party markers are a separate agent's scope.

`validate_map_polish.py --cases 500 --mutations` runs the actual teleport prefix
`0x0128136d..0x012818ac`, explicitly skips the height block `0x0128152c..0x012816f2`, and stops at the
zero-number branch `0x0128174b`, same-world branch `0x01281ca2`, or immediately after LoadWorld. It compares
tile, XY, angle, world/folder stores, and ClearWorldMap before LoadWorld. The LoadingWorld store at
`0x01281d28..0x01281d43` runs separately. The 500 packets yield **875 checks, zero mismatches**, and all
three planted mistakes fail, covering half-tile position, direction bias and number-zero world guard.
GFx, smart-pointer getters, cleanup helpers and LoadWorld are modelled. Height, later cleanup and effects
are not claimed verified. Number zero retains the current world; every numbered reply sets LoadingWorld
to 30, including replies whose world is unchanged. The demo receiver now follows both rules.

The unmodified `LoadWorldMap 0x00c6b116` reaches the real formatting wrapper `0x009d59cc` and stops on an
undefined read of C++ locale global `0x0bdcad64` at `0x018ed70a`. The existing snapshot does not include that
locale object or its facets. The complete formatter remains **static**. No guessed locale or replacement
formatter is counted as instruction verification. Reproduce with `validate_map.run_navimap` using the
pinned captures, LangMachine, install_common and the lang5 snapshot. It is intentionally outside the
default green validator families until its runtime inputs are available.

Local reports `map-polish.json`, `map-window.json`, `map-regression.json` and frames under `maps/` are in
`~/Documents/mu-mac-tools/native/renders/polish/`. Portable tests include re-entry and NPC map lifecycle.
The visually checked captures use the installed GFx library and `MU_GFX_SINGLE_BUFFER=1`, under
`maps-single/` and `maps-verified/`. The older skill2 library's buffered run did not display the overlays.

The existing map suite was rerun against its original `scratch/lang/live/lang4.bin`: **5,001 cases,
zero mismatches, all 10 mutants caught**. An initial run using skill2's newer lang5 snapshot produced
298 mismatches, concentrated in absent-key default move records and the consumers sorting those records.
That input is not interchangeable with the original snapshot. Its failed log remains local as
`scratch/polish/map-validator.log`; the passing original-input run is `map-validator-lang4.log`.
An isolated archive of pre-polish `62be84d` reproduced exactly **298/5,001** with that same lang5 input:
build 70, sort 31, availability 79, rows 48 and click 70. The failures therefore predate this follow-up;
the newer snapshot was unsupported by those families. Local report: `map-baseline-lang5.json`.
NATIVE-MAP-002 resolves that input mismatch below.

## Move default records (NATIVE-MAP-002)

The pinned text and image-section digests above are unchanged. The failure is a **validator input bug**.
The C algorithms already accept a caller-supplied default record; the validator returned NULL on a missing
key, selecting C's empty fallback while Unicorn read the snapshot's runtime default. The former API comment
incorrectly described that fallback as an always-zero client record.

There are two distinct local files called lang5.bin. Snapshot SHA-256 identities:

- `scratch/lang/live/lang4.bin`: `0461a408fd6b016def81043b43338d80d1851cec7bd7959ca8a2cf655dab9709`.
- `scratch/quest2/live/lang5.bin`: `2bd041e633122183514925fbbd0ae828972c358c728527ea1a9fc1752814b657`.
- `scratch/skill2/live/lang5.bin`: `59974e2e44ef80fb4e3551000f691837bc8f7e411dab28436aaa6bf676f5adf5`.

All three have the same 69 movereq keys and identical decoded records, including both strings and every
exported integer. Only skill2's capture reproduces the reported **298/5,001** failures. Its default at
`0x06fbb898`, table `0x06fbb84c + 0x4c`, has nonzero fields at record `+0x44/+0x48/+0x4c`;
those fields are zero in the other two snapshots. Default strings, level and cost agree. This is an
observed runtime-state difference, not evidence of changed map requirements or of why those words differ.

**Instruction evidence:** lookup `0x0113c3f5` takes the missing-key branch at `0x0113c431..0x0113c437`
and returns `this + 0x4c`. The record copy `0x00bde686` reads the sort fields at
`0x00bde704/0x00bde710`; constructor `0x00d3b593..0x00d3b5a2` places them in the move entry.
No instruction, captured field or failing comparison is patched or excluded.

| Family | Old failures on skill2 lang5 | Cause |
|---|---:|---|
| move_build | 70 | Randomly injected missing keys read nonzero default sort fields in Unicorn and zeros in C. |
| move_sort | 31 | Built managers inherit those unequal fields; their sorted order differs. Synthetic vector sorts agree. |
| availability | 79 | The comparison includes the whole built manager, retaining unequal fields and sometimes unequal pre-sort order before flags are assigned by position. |
| rows | 48 | SetMoveMapList sorts those managers; the default's sort fields change the position of its empty-name row. |
| click | 70 | The comparison includes the manager as well as effects; inherited fields/order differ, even when a click's effects agree. |

`Tables.lookup` now returns the full captured default for an absent key, including its strings, rather than
NULL. C retains its empty fallback for callers without a runtime default. The synthetic sparse-snapshot
regression uses independently authored nonzero strings, cost, level and sort fields, and checks missing-key
lookups, construction, sorting, availability, rows and click. Reports now include `snapshot_sha256` so two
same-named captures cannot be confused.

There is no changed live movereq data to migrate. The native session builds its selectable list from real
table keys only, so its Move window never uses this missing-key default during construction. Offline
`mu-walk`, using the same `mu_map` session and row builder as mu-world/mu-client, produced identical 69-row
lists in all three sort orders for all three exports, **621 rows**. The native map tests also pass with
skill2's current tables, including private Lorencia → Noria → Lorencia travel. No live client was launched.

Reproduce with the pinned text/data and `scripts/validate_map.py --snapshot PATH --cases 500 --mutations`.
Each of the three snapshots passes **5,001 cases, zero mismatches, all 10 planted mistakes detected**
with seed 1. Portable reconstructed map tests: **11 pass**. Native map tests: **9 pass**, including the
private travel check with skill2's current data.
Reports and logs stay local under `~/Documents/mu-mac-tools/native/renders/map2/` and `scratch/map2/`.
The pre-fix reports are `baseline-lang5.json` for quest2 and `baseline-skill2-lang5.json` for the failing input.
The navimap locale blocker and the earlier bounded teleport limitations remain unchanged.

## Session overlay records, SESSION-MAP-001a, 2026-10-28

[Implementation, checks and remaining scope](../handoffs/SESSION-MAP-001a.md).
The unchanged capture09 text and run10 data pins above back three additional handler families.
C1 E7/03 and /04 retain the documented marker offsets. C2 E7/05 reads a little-endian u16 count
at +7, then count five-byte records at +9: kind byte, x little-endian u16, y little-endian u16.
The loop at 0x01233cf8..0x01233d4e skips kind zero, zero-extends coordinates and passes the
compacted vector to 0x00c6b6c2. Keys index that compacted vector, not the packet rows. The handler
calls the show setter when the overlay is hidden. Routing remains MU_STATIC finding-backed
metadata; no dispatcher table was walked.

New comparisons execute 0x0126d85c, 0x0123134b and 0x01233c9b with the original GFx helper
instructions. Each family passes 500 cases, zero mismatches. Four compiled parser mutants
change marker key, zero-kind filtering, x high-byte handling and compacted key; all fail.
The window getter, vector insertion/copy, heap and GFx host are modeled. The show setter is not
part of these collection comparisons. Existing map families pass 5,001 cases and all ten mutants.

The native session now owns markers/dots. The plaintext fixture supplies synthetic portal/NPC
placements; the HUD replays retained records and detector arrays on revision or rebind. Empty
refresh clears stale dots explicitly, although the original helper emits no movie call for an
empty vector. Native count/name/head/capacity checks reject malformed data atomically. The actual
hudMap movie arrays verify add/update/remove, stale retention on malformed frames, empty refresh
and host rebind. Travel requests and placement remain in mu_map; the encrypted full milestone,
party feed and locale formatter limits above remain open. No live session was accessed.
