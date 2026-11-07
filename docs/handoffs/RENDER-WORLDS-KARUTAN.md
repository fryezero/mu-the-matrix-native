# RENDER-WORLDS-KARUTAN

Two world-slot leftovers:
- Karutan's (worlds 80/81) custom slot `0x00e14596` and after slot `0x00e1543e`, now ported whole as class slots
  (before, RENDER-WORLDS-A had ported only the flag branches and a copy of the after slot);
- world 145's (Aquila) bone placements that RENDER-EFFECTS-019 left open.

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-karutan`, branch
  `claude/render-worlds-karutan`.
  - Branched from `origin/claude/render-worlds-raklion` `6d4f6312` (#337: the shared 121 slot routine and the
    census corrections). #337 was not on main yet when the checks ran, so "before" and `--affected-since` use
    `6d4f6312`: main plus #337.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.
- Finding: [client-worlds-karutan.md](../research/client-worlds-karutan.md), with the branch table, the diff against
  121's routine, the 145 records, the live comparison and the limits.

## Karutan vs the shared routine (static, then verified)

Karutan's custom slot is its own code, not Test Area 121's or Raklion's: no aligned instruction run, a different
case set and a different world test. So it is ported as its own routine (`world_karutan_visual.c`), not as a row of
`ta_class`. The differences with addresses ([finding](../research/client-worlds-karutan.md) §2):

| Element | Karutan `0x00e14596` | 121 `0x00d58bd8` / Raklion `0x00e949f8` |
|---|---|---|
| World test | `0x00e18ae9` (80, 81), `0x009dad2c` (102), `0x00c7dfcc` → `0x009d3e63` (103..106) at `0x00e145b5..0x00e145ef` | none / `0x00ea233c` (57, 58) |
| After flags | 1, 3, 0x36..0x3a, 0x3e, 0x3f, 0x77 (`0x00e146ce`) and 0x42 | 0x2e, 0x35, 0x4c, 0x59, 0x53, 0x5c |
| Action choice | 0x42 `0x00e146dc`: frame >= 19, `SetAction(rand() % 10 == 0)` | 0x10 `rand() % 2`, 0x11 `rand() % 100` |
| Colour pulse | 0x81 `0x00e14727`: body, grey `0x0185bdc4(−2.5, 0) × 0.3 + 0.7`, mesh 1 with 0x85bb, colour restored, mesh 1 flags 0x44 | none |
| Per-vertex light, particles | none | 6..12, 28 CreateParticle sites |
| Types > 300 | 0x877, 0x87a..0x87d (unreachable) | 0x1a8..0x1ad, base types (unreachable) |

- Shared leaves only: RenderBody `0x00966def`, RenderMesh `0x00966e4a`, SetAction `0x012affa4`, rand `0x01989721`,
  the constant 19 `0x01a82968`.
- 0x81's branch is the same sequence as Kardamahal's 0xaa (`0x00e116b5`), in a separate copy. Its bitmap 0x85bb
  (`Object144\sdsaferzone14B01_R.jpg`, 0x2601/0x2900) is registered by the class's slot 0x24 `0x00e13a5c`.
- The after slot `0x00e1543e` (502 instructions, world test `0x00e18ae9`) draws ten types. It runs in 80/81: the
  after pass `0x016d6949` lists 0x50/0x51. RENDER-WORLDS-A's copy lacked 0x37/0x39's StreamMesh writes
  (`0x00e156eb`, `0x00e1575e`) and stood in for them with a runtime light-skip tweak. Both are replaced.

## What Karutan draws now

- The ten flag types and 0x42 are flagged by the class slot (as before) and drawn by the class after slot.
- 0x42 picks its next action from frame 19 (`rand() % 10 == 0` → 1, else 0) through the shared SetAction. Before,
  only its after flag was set.
- 0x81 draws its body, then mesh 1 pulsed grey with `Object144\sdsaferzone14B01_R.jpg` (now loaded as a slot bitmap
  in 80/81), then mesh 1 additive (flags 0x44). Before, it fell to the generic RenderBody: an unlit dark crystal.
- 0x37/0x39's after mesh carries the StreamMesh byte 0 / 0xff.
- The world test is the client's: the custom slot answers in 80, 81 and 102..106. Only 80/81 have the class.

## World 145 (Aquila): served and refused

- **The three unfollowed map-object records** (types 85, 87: bone 1; type 146: bone 0; models with 2, 2, 1 bones):
  - **served**, as RENDER-EFFECTS-019's general path already places them: the shared-pose bone translation
    `0x012a0030`, plus the position again when the object is alone in its sector (`0x012a0d29`);
  - now compared for exactly these records, alone and in a list (`records_145`).
- **The visual slot's `0x0129fd4f(6)`** (`0x00d77b3e` → `0x00d77c16`, `0x00d77c69`), now **served** with the lone-sector
  placement. An object alone in its sector gets bone 6 × `0x00cf2679(position, 0, scale)` (`0x0129ff2c..0x0129ffd9`).
  `mu_aquila_bone_matrix` reuses RENDER-EFFECTS-018's verified `0x0129fd4f`.
- **Refused, unchanged:**
  - a record, or bone 6, without a pose holding the bone: the client reads `0x06fce398 + 0x30 · bone`, a stale pose;
  - following a bone below −1: `0x0129f671` passes the matrix `0x00a7497a` leaves uninitialised.
  
  None of 145's 93 records falls in either case: all are on posed bones, none follows below −1.
- When the rule applies: an object whose sector holds no other object. 145's placements (`EncTerrain146.obj`) do not
  decode natively and there is no capture, so this is Unicorn-only. The native derives the predicate from its own
  sector lists.

## Shared lines (narrow seams)

- `reconstructed/objects/world_karutan_visual.c`:
  - added: `mu_slots_karutan_custom` / `_after` / `_bitmap` / `_bitmaps`;
  - removed: `mu_karutan_defer`, `mu_karutan_after`;
  - the local `wave` in `mu_karutan_visual` is renamed `w` (it shadowed the slot helper).
- `world_slots2_visual.c`: class 80 for 80/81 in the SLOTS2 chain (custom, after, bitmaps).
- `world_visual_slots.h`: four declarations.
- `world_after.c`: `mu_world_defer` / `mu_world_after_render` drop 0x50/0x51. `mu_world_after_enabled` keeps them
  (the pose's light-skip mesh, unchanged).
- `native/core/mu_objects_runtime.c`:
  - the 0x37/0x39 light-skip tweak in the A after branch is removed;
  - the 145 visual uses `mu_aquila_bone_matrix` with `mu_map_effects_in_sector`;
  - includes `map_effects.h`.
- `reconstructed/objects/map_effects.{c,h}`: `mu_aquila_bone_matrix`.
- Validators:
  - new `scripts/validate_worlds_karutan.py` and its `validators.toml` row;
  - `validate_worlds_121.py`'s `Spec` takes case types, action types and extra stubs (121's and Raklion's defaults
    unchanged, same cases);
  - `validate_render_worlds_a.py`'s Karutan cases (`after_draw`, `flags`) call the class entry points; its
    "Karutan scrolling period" mutant follows the code (`tmod(s,10000,`);
  - `validate_render_effects19.py` gains `records_145` and `aquila_bone6` and three mutants, and builds `aquila.c`
    into its map library. Its row: 6 families, 400 cases, 28 mutants.
- Tests:
  - new `reconstructed/objects/test_worlds_karutan.py` (portable, plus the private comparison);
  - `native/tests/test_render_effects19.py`: an Aquila bone-6 test, and the row counts;
  - 6b: `test_worlds_after2.test_classes` lists 80, 81.
- Docs:
  - the census row in `client-worlds-slots.md`;
  - the Karutan and Aquila entries in `world-handler-coverage.json`;
  - a pointer each in `client-world-fidelity.md`, `client-render-effects-019.md` and `client-worlds-raklion.md`.

## Checks

CHECKS

## Fidelity (Karutan vs live, October 22 capture)

FIDELITY

## Census

The slot census counted Karutan's custom `0x00e14596` and after `0x00e1543e` as "V A" in 144/144:
- the custom slot was compared only on its flag branches: 0x42's action choice and 0x81 were missing, and the world
  test was the runtime's;
- the after slot copy lacked the StreamMesh writes.

The row now reads "V KARUTAN" (whole), and the JSON scopes say so. Aquila's visual scope notes the lone-sector
placement. The count stays 144/144. The character and login scene rows (93, 94) still read "V A"; this lane did not
re-check their scope.

## What's left

- Karutan's types 0x877 and 0x87a..0x87d are unreachable (types > 300) and are not ported.
- No live image of the new Karutan branches: the October 22 tile has no 0x42 or 0x81 in view. The live window PNG
  is gone, too. A capture near the 0x42 group (about tile 49,169) or the 0x81 crystal (205,17) would show them.
- World 145 stays Unicorn-only: no decoded placements, no capture (it needs level 1650).
- Still open from 121: the particle visual's stale comment (`reconstructed/particles/visual.c` line 131).

LOCAL
