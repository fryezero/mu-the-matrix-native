# RENDER-WORLDS-KARUTAN: Karutan's class slots whole, and world 145's bone placements

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Text and
second-image-data captures pinned in `scripts/pins.py` (capture09/run10). Method:
- static disassembly of Karutan's two slots and the Aquila visual slot;
- a structural diff against Test Area 121's / Raklion's routine and the other class slots;
- compiled authored C compared with the original instructions under the strict Unicorn machine
  (`scripts/validate_worlds_karutan.py`, which reuses `validate_worlds_121.py`'s slot comparison;
  `scripts/validate_render_effects19.py`'s two 145 families);
- the October 22 live capture of Karutan (one view, read only).

Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **live** = from the
read-only October 22 capture, **inference** = reasoning.

Follows [RENDER-WORLDS-RAKLION](client-worlds-raklion.md) §6 ("Karutan's custom slot `0x00e14596` is in the same
bounded state") and [RENDER-EFFECTS-019](client-render-effects-019.md) §1 and §7 (world 145 left open).

## 1. The custom slot `0x00e14596` (verified)

Class world-80 (worlds 80/81, vtable `0x01aa9a4c`, slot 0x38), `thiscall(handler, object, model, index)`,
`ret 0xc`, 969 instructions.

| Address | What it does |
|---|---|
| `0x00e145b5..0x00e145ef` | World test: `0x00e18ae9` (current world `0x01cf15fc` is 0x50 or 0x51); else `0x009dad2c(world)` (0x66); else `0x009d3e63(world)` on the singleton `0x00c7dfcc` (0x67..0x6a). All false: answers 0, nothing drawn or written |
| `0x00e146ce` | Types 1, 3, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3e, 0x3f, 0x77: the after flag `+0xa = 1`, answers 1, nothing drawn |
| `0x00e146dc` | 0x42: frame `+0xd0` >= 19 (`0x01a82968`; `jb`, so NaN skips): `SetAction 0x012affa4(o, rand() % 10 == 0 ? 1 : 0)` (rand `0x01989721`); then the after flag; answers 1 |
| `0x00e14727` | 0x81: RenderBody(2, alpha, blend mesh, blend light, u, v, −1, −1); the body colour (model `+0x54`) saved in a vector (`0x0095ea8e`, element `0x00cfc922`); colour = `1.0 × w` with `w = 0x0185bdc4(−2.5, 0) × 0.3 + 0.7` (`0x01a7e6e0`, `0x01a7e918`); RenderMesh(1, 2, alpha, 1, light, u, v, 0x85bb); the colour restored; RenderMesh(1, 0x44, alpha, 1, light, u, v, −1); answers 1 |
| `0x00e149ac`, `0x00e14aa3`, `0x00e14b9a`, `0x00e14d49`, `0x00e14ff2` | Types 0x877, 0x87a, 0x87b, 0x87c, 0x87d (body and mesh draws with the bitmaps 0x80f2..0x80f8, some behind action 6). The world manager passes types 0..300 only, so these are never reached (as for 121's and Raklion's types > 300) |
| `0x00e1542d` | Every other type: answers 0 (the generic draw) |

- **The bitmap 0x85bb (static).** The class's slot 0x24 (`0x00e13a5c`) registers `Object144\sdsaferzone14B01_R.jpg`
  as 0x85bb (filter 0x2601, wrap 0x2900). The object loader's Karutan case (`0x018408e3`, entry 27 of the jump table
  `0x0184307f`) registers only 0x7f22 and 0x7f89. Kardamahal's slot 0x24 registers the same file under the same
  index (`0x00e0e891`).
- **What RENDER-WORLDS-A had.** `mu_karutan_defer` set the after flag for the ten flag types and for 0x42. 0x42's
  action choice and the whole 0x81 branch were missing (0x81 fell to the generic RenderBody), and the world test
  was the runtime's 80/81 only.

## 2. Diff against Test Area 121's / Raklion's routine (static)

Karutan's slot shares no code with 121's `0x00d58bd8` (1,972 instructions) or Raklion's `0x00e949f8` (1,994). So
there is no parameter row to add: the slot is ported as its own routine (`world_karutan_visual.c`). The differences:

| Element | Karutan `0x00e14596` | 121 `0x00d58bd8` / Raklion `0x00e949f8` |
|---|---|---|
| World test | `0x00e145b5..0x00e145ef`: 80, 81, 102, 103..106 | 121: none; Raklion `0x00e94a04`: `0x00ea233c` (57, 58) |
| Case set | 1, 3, 0x36..0x3a, 0x3e, 0x3f, 0x42, 0x77, 0x81 (+5 types > 300) | 6..12, 0x10, 0x11, 0x13..0x15, 0x2e, 0x35, 0x39, 0x44, 0x45, 0x47, 0x4c, 0x52, 0x53, 0x59, 0x5c |
| Action choice | 0x42 `0x00e146dc`: frame >= 19, `SetAction(rand() % 10 == 0)` | 0x10: frame >= 19, `SetAction(rand() % 2)`; 0x11: `rand() % 100` split at 90 |
| After flag | ten types and 0x42, no draw | 0x2e, 0x35, 0x4c, 0x59 (no draw); 0x53 and 0x5c after their first meshes |
| Per-vertex light, particles | none | types 6..12 (0.5), 28 CreateParticle sites in 0x13..0x15 |
| Colour pulse | 0x81 `0x00e147ec`: `0x0185bdc4(−2.5, 0)`, the 0x85bb mesh | none (0x44/0x45/0x47 pulse the blend light with `sin(T · 0.001)`) |
| Default | `0x00e1542d`: answers 0 | 121 `0x00d5c79c` answers 0; Raklion `0x00e9ef04` (types > 300) |

The same leaves: RenderBody `0x00966def`, RenderMesh `0x00966e4a`, SetAction `0x012affa4`, rand `0x01989721`, the
constant 19 `0x01a82968`. Karutan's 0x81 branch is the same sequence as Kardamahal's type 0xaa (`0x00e116b5`: body,
grey `wave(−2.5) × 0.3 + 0.7`, mesh 1 with 0x85bb, colour restored, mesh 1 with flags 0x44); the two are separate
copies, each compared with its own instructions.

## 3. The after slot `0x00e1543e` (verified)

502 instructions, world test `0x00e18ae9` (80, 81) only, `ret 0xc`, no answer.

| Types | Address | Draws |
|---|---|---|
| 1 | `0x00e154db` | meshes 1, 2, 3 (flags 2, blend mesh, blend light, u = v = 0), mesh 0 (flags 0x42) |
| 3, 0x38, 0x3e | `0x00e15601` | RenderBody(2, alpha, blend mesh, blend light, u, v, hidden `+0x68`, −1) |
| 0x36 | `0x00e15663` | mesh 0, flags 0x42, blend 0, light `(sin(T · 0.002) + 0.5) × 0.5 + 1` |
| 0x37, 0x39 | `0x00e156e8` | StreamMesh byte (model `+0x94`) = 0, mesh 0 (0x42, u, v = `(int)T % 10000 × 0.0001`), StreamMesh = 0xff (`0x00e1575e`) |
| 0x3a | `0x00e1576a` | mesh 0 (2), mesh 1 (0x42, blend 1, `p = (sin(T · 0.001) + 1) × 0.5`), mesh 3 (2), mesh 2 (0x42) |
| 0x3f | `0x00e158bf` | mesh 0 (0x42, blend 0), mesh 1 (2), mesh 2 (0x42, blend 2, p), mesh 3 (2) |
| 0x42 | `0x00e15a10` | mesh 0 (2), mesh 1 (0x42) |
| 0x77 | `0x00e15aa6` | mesh 0 (2), mesh 1 (0x42, blend 1, p) |

- **It runs.** The client's after pass `0x016d6949` lists 0x50 and 0x51 in its world test (`mu_world_after_gate`),
  so every object the custom slot flagged is drawn here.
- **What RENDER-WORLDS-A had.** `mu_karutan_after` drew the same meshes, but without the StreamMesh writes of
  0x37/0x39. The runtime stood in for them with a light-skip tweak (`light_skip_mesh = 0` after the draw). That
  tweak is now removed, and the class route carries the StreamMesh events as for every class slot.

## 4. World 145, Aquila's Temple (verified; no capture)

**The three unfollowed map-object records.** World 145 has 93 records in the decoded table (RENDER-EFFECTS-008's
`mapeffects.tsv`, read only). Three do not follow their bone:
- types 85 and 87: bone 1;
- type 146: bone 0.

The installed models have 2, 2 and 1 bones (`Data\Object146\Object86/88/147.bmd`, read with the native BMD
reader), so each bone exists in the object's pose. What the client does for them (`0x0129f671`, static, verified in
RENDER-EFFECTS-018/019):
- The bone comes from the shared pose buffer `0x06fce398 + 0x30 · bone`. The bone source `0x0129f12c` answers 0
  because a map object's `+0x318` is 0, and RenderObject has just filled the buffer with this object's pose.
- Not following: the matrix is the scale diagonal, with the translation `0x012a0030(bone)`: the bone's posed
  translation.
- When `0x012a0d29` fails, the position is added a second time. That happens when `+0x350` and `+0x354` are both
  0: the object is alone in its sector, since CreateObject appends every map object to its sector's list.

The other 90 records of 145 follow posed bones. None is on a bone beyond its model, and none follows a bone below −1.

Native: RENDER-EFFECTS-019's `o_ein_update` already runs every world's records through `mu_map_effect_matrix` with
the runtime's sector predicate, so 145's three records are served as the client places them, alone or in a list.
This lane adds the comparison for exactly these three (bone, follow, model bone count) records (`records_145`).

**The visual slot's `0x0129fd4f(6)`.** Aquila's visual slot `0x00d77b3e` asks `0x0129fd4f(6)` twice (`0x00d77c16`,
`0x00d77c69`) for types 136..140 and 142, and keeps the matrix's [12] and [13] in `+0x188` / `+0x18c`.
`0x0129fd4f` (static):
1. takes bone 6 of the shared pose through `0x0129f12c`;
2. transposes it into a column-major 4x4;
3. then, only when `0x012a0d29` fails (`0x0129ff2c`), multiplies it by `0x00cf2679(position, (0, 0, 0), scale)`
   (`0x0129ff9e`, `0x0129ffc1`), so the point lands about one object position further out.

RENDER-WORLDS-S's runtime glue transposed the bone and never placed it. It now calls `mu_aquila_bone_matrix`
(`map_effects.c`): RENDER-EFFECTS-018's verified `0x0129fd4f` reconstruction, with bone 6, following, and the
runtime's sector predicate. Objects in a sector list get the same matrix as before. An object alone in its sector
now gets the client's placed point.

**When the lone-sector rule applies in 145.** Exactly for an object whose sector holds no other object. Which Aquila
objects those are depends on `EncTerrain146.obj`'s placements. The native does not decode that file (the protection
boundary; `mu-world --world 145` loads 0 objects), and no capture of 145 exists (it needs level 1650). The native
derives the predicate from its own sector lists, so the answer is correct for whatever placements it is given.

**Refusals that stay.**
- A record (or the visual's bone 6) without a pose holding that bone. The client reads `0x06fce398 + 0x30 · bone`,
  left by another object's or an older pose.
- Following a bone below −1. `0x0129f671` passes a matrix that `0x00a7497a` leaves uninitialised.

Both are refused and counted (`unposed`, `draw_unsupported`). Neither occurs among 145's 93 records.

## 5. Native

- `world_karutan_visual.c`:
  - `mu_slots_karutan_custom` / `mu_slots_karutan_after`: the two slots whole;
  - `mu_slots_karutan_bitmap` / `_bitmaps`: 0x85bb for type 0x81, in 80/81;
  - `mu_karutan_defer` and `mu_karutan_after` (the A pieces) are removed.
- `world_slots2_visual.c` maps 80/81 to class 80 in the SLOTS2 chain (custom, after, bitmaps).
- `world_after.c`: `mu_world_defer` and `mu_world_after_render` no longer take 0x50/0x51. `mu_world_after_enabled`
  keeps them for the pose's light-skip mesh, as it keeps Raklion's.
- `mu_objects_runtime.c`:
  - Karutan is a class-slot world (`mu_class_slots(80/81)`): the class custom render runs in the first pass, the
    class after render in `mu_objects_prepare_after`;
  - the 0x37/0x39 light-skip tweak is removed;
  - the 145 visual's bone 6 comes from `mu_aquila_bone_matrix`.
- `map_effects.c`: `mu_aquila_bone_matrix`.

## 6. Instruction comparison (verified)

`validate_worlds_karutan` runs `validate_worlds_121`'s slot family with Karutan's spec. The `Spec` now also takes the
case types, the action types and extra leaf stubs; 121's and Raklion's defaults are unchanged.
- `custom_karutan`: the custom slot against `mu_class_custom(80, …)`.
  - The first 301 cases sweep the types 0..300.
  - One case in five runs in another world: 79, 82, 0, 142, 143, 107 answer 0; 102..106 pass the test.
  - The singleton `0x00c7dfcc` is a leaf answering a dummy pointer. Its predicate `0x009d3e63`, the wave
    `0x0185bdc4`, the vector helpers and SetAction run as client code.
  - Compared: draws with the StreamMesh byte and colour, the answer, rand, the OBJECT and model fields, and the
    bitmaps the class names.
- `actions_karutan`: 0x42 only, frames at the frame-19 edge, and seeds whose first `rand() % 10` is 0, 1 or 9.
- `after_karutan`: the after slot against `mu_class_after(80, …)`.

`validate_render_effects19` gains two families:
- `records_145`: the three records, on poses of their models' bone counts, alone and in a list.
- `aquila_bone6`: the visual slot `0x00d77b3e`, with `0x0129fd4f`, `0x0129f12c` and `0x012a0d29` run as client code.
  - It is compared against `mu_map_effects_in_sector`, then `mu_aquila_bone_matrix`, then `mu_aquila_visual`.
  - Compared: the answer and `+0x188..+0x194`.
  - Each case also checks the refusals.

`validate_render_worlds_a`'s Karutan cases (`after_draw`, `flags`) call the class entry points. Counts are in the
[handoff](../handoffs/RENDER-WORLDS-KARUTAN.md#checks).

## 7. Fidelity against the October 22 capture (live)

One view of world 80, `80-karutan` (tile 125,123), from the 14-view tour. It was rendered with the default draw and
with the `live_time` clock. The live window PNG of that session no longer exists locally, so the comparison is the
OBJECT scoreboard and the light dumps.
- **Before → after: no change.** The native output is byte-identical before and after: PNG frames, OBJECT and light
  dumps, frame reports.
  - Live against native: 2,143 of 2,143 objects match, with 0 static-field differences, before and after.
  - The frame light near the hero: mean |Δ| 0.0148, the same before and after.
- **Why nothing moves (live).**
  - The capture holds six type 0x42 objects, 7,137 to 10,428 units from the hero, and one 0x81, 13,304 units away.
    All are beyond the camera's far plane (3,258), so RenderObject never draws them and the custom slot never runs
    on them. In live they sit at action 0, frame 0.
  - The flag types in view were already flagged by the A route, and live agrees.
  - So the newly ported branches (0x42's action choice, 0x81's pulsed mesh) and the StreamMesh writes have no
    object to act on at this tile.

## 8. Census

[RENDER-WORLDS-SLOTS](client-worlds-slots.md) §1 listed both Karutan slots as "V A", counted in 144/144. Before this
lane:
- the custom slot was compared only on its flag branches: 0x42's action choice and 0x81 were missing, and the
  world test was the runtime's;
- the after slot copy lacked the StreamMesh writes.

The JSON scope said "bounded"; the census line did not. The row now reads "V KARUTAN", whole. The number stays 144/144.

## 9. Limits

- The custom slot's types 0x877 and 0x87a..0x87d are unreachable (types > 300) and are not ported.
- World 145: no placements (EncTerrain146 does not decode natively), and no live capture. The lone-sector
  placements of the records and of bone 6 are compared under Unicorn only.
- At the October 22 Karutan tile no 0x42 or 0x81 object is in view, so the live capture cannot show the new
  branches. A future capture near one of them (for example the 0x42 group about 7,100 units from 125,123) could.
- A pose without the bone a record or bone 6 needs stays refused and counted (§4).
