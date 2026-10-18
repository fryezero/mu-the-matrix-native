# Click-to-move: path finding and path following (NATIVE-PATH-001)

This finding recovers what the client does between a terrain click and the hero's walk:

* the path finder (search rules, node budget, heuristic, neighbour order, blocking attribute bits,
  tie-breaking and the behaviour on unreachable targets);
* how the resulting path is stored and followed (sub-targets, turning, the 40 ms position step and
  the walk/run speeds);
* where a new path is handed to the network layer. That boundary is recorded only; the network
  routine itself was not traced.

The rules are reconstructed in C under [`reconstructed/path`](../../reconstructed/path/README.md)
and compared bit for bit with the client's own instructions in Unicorn
(`scripts/validate_path.py`). The native module `native/core/mu_path.*` and the `mu-path` tool use
them.

Labels: **Verified** means the C port equals the client's instructions on every compared case.
**Static** means a reading of decoded instructions that was not executed. **Placeholder** means
native code that is not client behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09), 23,572,480 bytes | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10), 2,557,764 bytes | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Trig dispatch flag `0x0bdd1cc8` (value 1) | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |
| Neighbour table `0x01cf1640`, 64 bytes | `a8cc45492d67c784853284cd426fd5c48a994a55d124bd970c1da1e46616f8b5` |

The neighbour table lies in the third section (`0x01ced000`), which is packed in the file and was
not part of the restored captures. Its 64 bytes come from the unpacked third-section region of the
earlier experimental capture `evidence/x86-linux-capture-04/` (file offset `0x4640`). That capture
has no manifest, but its text region has the pinned restored-text digest above. No direct writer of the table
was found in the restored text. The validator pins it by digest; every routine body it executes is pinned
by start, length and SHA-256 (`ROUTINES` in the script and in its JSON report).

## 1. The path finder (verified)

**Object.** One finder object lives at `[0x06fce374]` (0x428 bytes, operator new at `0x008dd578`,
constructor `0x012b1855`). The intro scene calls `SetMapDimensions 0x012b281e(256, 256, 0x0b795420)`
once (`0x012b0e65` from `0x0185ae54`), so the finder works directly on TerrainWall. Its layout:

| Offset | Field |
|---|---|
| `+0/+4/+8` | width, height, cells (256, 256, 65,536) |
| `+0xc` | TerrainWall pointer (`uint16` per tile; the search can write it, see the siege flag) |
| `+0x10` | node count of the last built path |
| `+0x14`, `+0x208` | path X and Y, 500 bytes each, filled from the end |
| `+0x3fc/+0x3fe` | end tile (int16) |
| `+0x400` | mark byte per tile: 1 open, 2 closed, 4 target |
| `+0x404/+0x408` | touched index range (reset marker `0x743aa380` / -1) |
| `+0x40c/+0x410/+0x414` | cost, parent X, parent Y (int32 per tile, kept between searches) |
| `+0x418` | priority queue: `{vtable, count, root}` of an unbalanced binary search tree; nodes `{index, cost, left, right, parent}` (0x14 bytes) |

**PathFinding2 `0x012b0e85(sx, sy, tx, ty, PATH_t *, float distance, int level)`.**

1. A flag is computed from two subsystem predicates (`0x00db732d`, `0x00dabe97`) and a character's skill
   value in `0xa39..0xa3d` (static reading; a siege-type skill). The flag makes the distance-0 search clear
   TerrainWall at the target.
2. `FindPath(sx, sy, tx, ty, error_check 1, level, flag, distance, budget 500, mask 0x1e)`.
3. On failure: if the start or target tile has the safe-zone bit (1) and the target has no character
   bit (2), the level becomes 4. Then `FindPath(..., error_check 0, ...)`.
4. On success with more than one node: `PATH_t` (Character `+0x3194`) gets
   `{current 0, sub-target 0, count = min(nodes, 15), X[15], Y[15]}`, the first nodes from the start
   tile (the start tile itself is node 0). Otherwise the `PATH_t` is left unchanged and 0 is returned.

**FindPath `0x012b1c45`** (thiscall, 10 arguments) is a best-first search with these rules:

* **Reset** (`0x012b2515`): clear the marks of the touched range only; end tile = (0, 0). A start tile
  with x = 0 or y = 0 is refused (checked after the reset).
* **Targets.** With distance 0, the target tile is the only target. With `error_check`, the search fails
  at once when `level <= TerrainWall[target]` (the whole 16-bit value) and the tile lacks the action bit
  0x20. A walkable tile with a high bit (for example 0x40) is therefore refused by the first search and
  reached by the second. With distance d > 0 (`0x012b2584`), every tile within d is a target:
  * the diamond `|i| + |j| <= (int)d`;
  * plus the outer tiles with `d > (float)sqrt(k² + i²)`, strictly.

  Indexes are `y * 256 + x` without an x range check. A target index outside the map is logged
  (`0x01206598`) and skipped. With `error_check`, only tiles with `level > TerrainWall` become targets.
* **Queue.** The start is pushed with cost 0. Each iteration pops the minimum (leftmost tree node,
  `0x012b240a`). Equal costs are inserted to the right, so ties pop in insertion order (first in,
  first out).
* **Budget.** At most 500 pops (the budget counts pops, not pushes).
* **Lazy cost.** When a tile is popped, its cost is recomputed: 0 for the first pop, otherwise the
  minimum over its closed neighbours of `cost[n] + 7` (diagonal) or `+ 5` (orthogonal). That neighbour
  becomes its parent. Then the tile is closed. A popped target ends the search.
* **Expansion.** The neighbours are taken in the table order (-1,-1), (0,-1), (1,-1), (-1,0), (1,0),
  (-1,1), (0,1), (1,1), inside 0..255 on both axes. A neighbour is pushed when:
  * it is not open yet;
  * `(TerrainWall & 0x1e) < level`. For the hero (level 2) this blocks character 0x02, no-move 0x04,
    no-ground 0x08 and water 0x10. Safe zone 0x01, action 0x20 and the height/camera bits do not block;
  * it is not a blocking-object tile (`0x0b7b5420[i] & 1`, set by `0x016d9f51`, cleared per world in
    OpenWorld), unless it is the target.

  Its priority is `heuristic(neighbour) + cost(current)`, the parent's cost and not parent + step. Its
  parent is the current tile.
* **Heuristic** (`0x012b1bcf`): `dx = |x - tx|, dy = |y - ty|`, `(3 * (5 * |dx - dy| + 7 * min(dx, dy) + 1)) / 4`.
* **Fallback.** Without `error_check`, every popped tile is compared by heuristic. When the queue empties
  or the budget runs out, the path to the popped tile with the smallest heuristic (first one on ties) is
  built.
* **BuildPath** (`0x012b21c6`, flag 0): it follows the parents from the end tile to the start, at most 500
  nodes. The trimming variant (flag 1, budgets above 500) is used only by the long-distance helper path
  `0x012b104c`. It was not ported.

**What this means for a click** (verified consequences):

* **Path length.** A path holds at most 15 nodes (14 steps). A click farther away walks the first 14
  steps and stops; the player clicks again.
* **Unreachable targets.** An enclosed or blocked target fails the first search. The second search walks
  to the explored tile that looks closest by the heuristic, within 500 pops. If even that has a single
  node, nothing happens.
* **Safe zones.** In a safe zone, a crowd that blocks the way is ignored on the second search (level 4):
  character tiles become passable.
* **Own tile.** The hero's own tile carries the character bit (MoveCharacters stamps every live
  character each step, `0x0137a7ce`). The start tile is never tested. Clicking another character's tile
  fails the first search; the second walks to the explored tile with the smallest heuristic, usually
  next to it.

## Paths to a target area: attack and talk range

The distance argument turns the search into "walk until within range". The target marking is
verified for any distance (section 1). The callers' range values are a static reading.

* **Hero click.** The normal hero click uses distance 0 (`0x016ace20`).
* **Character target.** The branch at `0x016aab55..0x016aabd3` (a click on a character or NPC) computes a
  range. It starts at 1.0 and is overridden in this order:
  * 2.0 when the weapon in slot 0 (`[0x01d1df18]+0x1b68`) is in item group 3 (`0x600..0x7ff`);
  * 6.0 when `0x0139d994()` holds;
  * 7.0 for character class value 9 (`+0x146`);
  * 8.0 when `0x00cd6017(item, 0x54)` holds.

  The walk starts only when `|dx| + |dy| > (int)range` and the check `0x016a53b4` passes. The search is
  then `PathFinding2(..., range, 2)`.
* **Action handler.** The action-at-target handler `0x01697c17` (`+0x39` = 3, `0x01697cab`) uses the same
  values; there the class-9 rule comes after the item rule.
* **Special branch.** The special branch at `0x016aca06` uses 1.0.
* **Other non-zero callers.** Two more sites pass a variable range: `0x00957e89` passes an integer
  distance as float, and `0x0107f2eb` passes a record field `+0x18`.
* **Other callers.** The remaining 22 of the 28 call sites pass 0. The non-hero characters and some other
  callers pass level 4 directly or use it as their retry.

With distance d, each tile that is not blocked (with `error_check`, `level > TerrainWall`) and lies in
the diamond `|i| + |j| <= (int)d` or strictly inside the circle of radius d is a goal. With d = 1 that is
the target and its four orthogonal neighbours, so the hero stops beside the target and not on it. The
first goal popped ends the search.

## 2. Following the path (verified)

**MovePath `0x012b0846(character, turn)`** runs once per 40 ms logic step while the character moves:

* **Logical tile.** On the first sub-target of a node (`sub-target == 0`), the character tile
  (`+0x180/+0x184`) becomes the *next* node (`min(current + 1, count - 1)`). The logical tile therefore
  leads the drawn object.
* **Sub-targets.** The sub-target is a Catmull-Rom point of the tile centres `(X + 0.5) * 100` of the
  nodes `current - 1 .. current + 2` (indexes clamped). At t = 0.25, 0.5 and 0.75 the weights are
  (-0.0703125, 0.8671875, 0.2265625, -0.0234375), (-0.0625, 0.5625, 0.5625, -0.0625) and
  (-0.0234375, 0.2265625, 0.8671875, -0.0703125). At t = 1 it is the next centre. All sums are binary32
  in source order.
* **Advance.** When `(int)sqrtf(distance²) <= 30` (the object is within 30 units, about a third of a
  tile), the sub-target index advances. After the fourth sub-target the node advances.
* **Arrival.** Reaching node `count - 1` is the arrival: the tile is set, the object is snapped to the last
  centre, and 1 is returned.
* **Turning** (when `turn` is set and the walk has not arrived):
  * `CreateAngle 0x012aed9e(object, sub-target)` gives degrees with 0 = -y, 90 = +x, 180 = +y and 270 = -x.
    It uses `atan` through a float wrapper and binary32 π `0x40490fdb`;
  * the angle difference `0x012af218` is taken (absolute, wrapped);
  * at 45 degrees or more the object snaps to the target angle. Otherwise
    `TurnAngle 0x012aefff(current, target, difference / 2)` turns it halfway.

**MoveCharacterPosition `0x0137b351`** then moves the object:
`position += AngleMatrix(angle) * (0, -speed, 0)`. It uses `0x00cff32a` and `0x00d000ad` from
record-math. The height is then set from `RequestTerrainHeight 0x016cc9e2`, plus 90 in worlds 8/10/0x84
and 30 in some other cases (static). The object timer `+0xb4` grows by 0.15.

**Speed** (`CharacterMoveSpeed 0x013957b5`, static reading; the comparison feeds synthetic speeds):

* A player walks at 12 units per step while the run counter (Character `+0x24`) is below 40, and at 15
  after that. That is 3 or 3.75 tiles per second.
* The walk chooser `0x0139002a` advances the counter by one per moving step, up to 40, but only when
  equipment or buff conditions allow running: certain buffs, the wing check `0x0139fcbf`, or specific
  item states.
* SetPlayerStop `0x0138fe69` resets the counter (unless a mount predicate holds).
* Mounts and special items give 15 to 19, a few states 8 or 20, and slowing buffs multiply by 0.5 or
  0.33.

**Other characters** (`0x013b852a`, static): when a character is not moving and its tile differs from
its server target `(+0x2d, +0x2e)`, the client runs PathFinding2 with level 2. In two event-world cases
it uses level 4 instead (`0x00e3068f`). It retries with 4. If both fail, it teleports the character to
the target centre. While moving, it uses the same MovePath and step. On arrival, the facing becomes
`(direction byte +0x22 - 1) * 45`.

## 3. The hero's click and the network boundary (static)

These are the click-entry gates from [client-camera-input.md](client-camera-input.md):

* the left button is pushed and Shift is not held;
* `RenderTerrain(1)` picks the terrain and the tile test hits;
* TargetX/Y are set to `(uint8_t)(CollisionPosition / 100)`.

After the gates, the normal branch of `MoveHero 0x016a9150` (from `0x016acce8`) does this:

1. If the hero is moving and its object is 2 or more tiles away from its logical tile
   (`(int)(position * 0.01f)` against `+0x180/+0x184`), the click is ignored. It is also ignored when the
   target equals the logical tile while moving.
2. `PathFinding2(tile, target, &Hero->Path, 0.0f, 2)` runs (`0x016ace20`).
3. **Boundary.** On success it calls `SendMove 0x016b5cd0(Hero, Object)` (`0x016ace39`), which hands the
   new `PATH_t` to the network layer. That routine was not traced. One observed store matters for movement:
   it sets the hero's moving flag (Character `+0x38` = 1, `0x016b6080`). MoveHero then clears `+0x39`.
4. The click marker effect is spawned at the collision point (`0x0142ec26(0x407)`).

A special branch (`0x016aca06`) targets a character with distance 1.0.

While the hero moves (`0x016a9a74..`), each logic step does the following:

1. Some buff or skill states stop the walk.
2. The walk chooser sets the walk or run action.
3. MovePath runs with turning.
4. If the walk has not arrived, MoveCharacterPosition moves the object.
5. On arrival, the client calls `0x016a8904`, SetPlayerStop and the action-at-target handler `0x01697c17`.

## Verification

`scripts/validate_path.py` maps the pinned text, the second section, the dispatch flag and the neighbour
table. It builds the finder with the client's own constructor and SetMapDimensions and calls the client
routines directly:

* PathFinding2 with everything below it;
* MovePath;
* the angle helpers and the heuristic and step cost;
* MoveCharacterPosition;
* the occupancy loop of MoveCharacters (run to `0x0137a814`).

**Replaced services.** These are CRT malloc/free/memset, the log writer, and the subsystem queries
outside the compared routines:

* the siege predicates;
* the character lookup;
* CharacterMoveSpeed and RequestTerrainHeight, which return synthetic values;
* two item and character predicates.

Each one is listed in `CLIENT_STUBS` with its reason.

**Harness choices.** Heap memory handed to the client is poison-filled. The finder's path arrays start
zeroed, and its touched range starts in the reset state: the client allocates the object uninitialised,
and every search resets before reading.

**What is compared after each search:**

* the return value and the `PATH_t` bytes;
* the finder's count, both 500-byte path arrays and the end tile;
* the touched range and the whole mark array;
* the cost of every closed tile and the parents of every opened tile;
* the tree (empty after the search);
* the whole TerrainWall.

Walks are compared after every 40 ms step. They cover the tile, the `PATH_t` and the position and angle
bits.

**Result at `--cases 1000 --mutations --worlds all`** (local run; the report is kept in
`~/Documents/mu-mac-tools/native/scratch/path/`):

**7,945 comparisons, 0 mismatches.** A second run, `--only installed --cases 4800 --seed 7`, added
3,100 comparisons with 0 mismatches.

| Family | Cases | Mismatches |
|---|---:|---:|
| PathFinding2, synthetic grids | 1,000 | 0 |
| PathFinding2, installed attribute maps (82 distinct maps; runs 1 and 2) | 492 + 2,460 | 0 |
| Walks along found installed paths, compared every step | 153 + 640 | 0 |
| MovePath, random states (including axis-aligned exact-angle cases) | 1,000 | 0 |
| Whole walks, synthetic paths (MovePath + MoveCharacterPosition, speeds 4.95..20) | 250 | 0 |
| CreateAngle, angle difference, TurnAngle (incl. ±0, ±inf, NaN, branch equalities) | 3 × 1,000 | 0 |
| Heuristic, step cost | 2 × 1,000 | 0 |
| Occupancy loop of MoveCharacters (whole map) | 50 | 0 |

Searches hit the 500-pop budget in both runs. In the main run, 1,210 of the 1,492 searches started a walk;
the second run started 1,891 walks from 2,460 searches. Mean path length was 9.1 to 9.9 nodes. The main run took
3 minutes on one core.

The synthetic grids are open ground, random walls at 10/25/40 % (every attribute bit), rooms with doors,
a maze, and a whole-map safe zone with dense characters. They add blocking objects and character
changes between searches, and use distances 0, 1, 1.5, 2, 2.9, 4 and the exact ring distances
5, √5, √8, √13, 3 and 0.5. Levels are 1, 2, 3, 4, 8 and 0x20, and some searches set the siege flag.
Starts can be on coordinate 0 or on blocked tiles, and targets can equal the start.

**Installed worlds.** Every world index whose folder loads through `mu-path att` (the native loader, same
rules as the client's `0x016c9da0`) was used, with duplicate maps removed. The searches start on
walkable tiles, with walkable or arbitrary targets up to 40 tiles away, at distances 0 and 1. Some
found paths are also walked.

**Mutation check.** Sixteen planted mistakes were all detected:

* LIFO ties;
* diagonal cost 5;
* a heuristic without +1;
* the classic A* priority;
* mask 0x1c;
* no safe-zone retry;
* a 14-node cap;
* `>=` in the distance ring;
* object blocks ignored;
* arrival radius `< 30`;
* t = 0.5 spline weights;
* turn snap only above 45;
* an exact-π reciprocal in CreateAngle;
* a strict TurnAngle wrap;
* parent replaced on equal cost and a wall test without the mask (both from the NATIVE-WORLD-001 validator).

The client's CRT `atan` (SSE2 path) and `sqrt` (x87) ran in the guest. Host libm agreed in every
compared CreateAngle and MovePath case; that is a property of these domains, not a proof.

**Tests.**

* **Portable** (`make test`): `reconstructed/path/test_client_path.py` (18 checks of rules and worked
  examples) and `native/tests/test_native_path.py` (synthetic maps through `mu-path`).
* **Private** (`MU_RECOVERY_INTEGRATION=1` with the capture variables): the instruction comparison at 80
  cases plus mutations, and the Lorencia dump, walk and render.

## Native module and tool

`native/core/mu_path.*` is self-contained (no client data, no network). `mu_pathing` holds a world's
TerrainWall copy, the blocking-object grid and the persistent finder. Allocate it on the heap: it is
about 1.2 MB with the finder's arrays. `mu_walker` is the hero:

* `mu_walker_click` applies the click rules above and PathFinding2. It counts the network hand-off in
  `sent` and does not perform it;
* `mu_walker_step` runs one 40 ms step: the run counter (placeholder condition `can_run`), MovePath with
  turning, then the position step at the player base speed;
* `mu_pathing_set_characters` reproduces the occupancy loop.

The height of the object is left to the caller.

```sh
make -C native
native/build/mu-path find   "$MU_GAME_ROOT" --world 0 --from 130,125 --to 137,131
native/build/mu-path render "$MU_GAME_ROOT" --world 0 --from 130,125 --to 160,140 --repath --out p.png
native/build/mu-path batch  "$MU_GAME_ROOT" --world 142 --count 4 --out-dir renders/
native/build/mu-path render --synthetic maze --seed 3 --from 5,5 --to 30,30 --out maze.png
native/build/mu-path att    "$MU_GAME_ROOT" --world 0 --out lorencia.att.u16
```

**The render.** The terrain is drawn top-down and orthographically through the terrain mode's software
rasterizer. On top of it:

* blocked tiles are tinted red, no-ground tiles dark, safe zones blue, and explored tiles yellow;
* the 15 client nodes are outlined in cyan, and the rest of the full BuildPath result in grey;
* every 40 ms position is an orange dot;
* the start is a green dot and the target a magenta cross.

`--repath` clicks the same target again when the walk stops short. That is a demo choice: the client
needs a new click from the player. Local renders (not committed) are under
`~/Documents/mu-mac-tools/native/renders/path/`.

## Reconciliation with NATIVE-WORLD-001

The native-world branch (`claude/native-world`, commit `a732f9b`, not yet in `origin/main`) also ports
the path finder (`reconstructed/movement/client_path.*`). Its follower ports MovePath, the angle helpers,
CharacterMoveSpeed and MoveCharacterPosition, compared in its own `scripts/validate_movement.py`. Both
ports read the neighbour table from the same capture.

**Cross-validation.** `scripts/validate_path.py --cross-library <its libclient_movement>` runs the other
port beside the client on every distance-0 search; it returns -1 for other distances. One run (1,000
synthetic and 940 installed searches, seed default) gave these results:

* this port: 0 mismatches against the client;
* the native-world port: 0 of 695 installed cases and **2 of 377 synthetic cases** different from the
  client.

The difference is the PathFinding2 retry rule. The client (`0x012b0f2c..0x012b0f7a`) raises the level to 4
only when `(start is safe || target is safe) && target has no character`. The other port raises it when
`start is safe || (target is safe && no character)`. So with a safe start and a character on the target,
it walks a different path. Example: start (98, 52) with wall 1, target (99, 47) with wall 3. The client
path has x = 98, 97, 98, 99, 98, 98 and the other port's x = 98, 98, 98, 99, 99, 99, both with
y = 52..47.

**Coverage.** Compared with the other port, this one also covers:

* the target-area branch `0x012b2584` (attack and talk range);
* the siege flag;
* refused zero coordinates, out-of-range target logging and arbitrary budgets.

It compares the finder's internal state (marks, costs, parents, touched range) after every search, and its
16 mutations target the search and follower rules.

**Done (after `claude/native-world` merged as #82).** `reconstructed/path` is the single path finder:

1. `reconstructed/movement/client_path.*` were removed. `native/core/mu_walk.c` calls `mu_path_finding2`
   from `reconstructed/path` (new `mu_walk_free` releases the finder arrays). The finder's neighbour order
   is a field (`directions`, NULL = the client table), so the world module keeps its table.
2. The other port's independent Python statement of FindPath moved to `reconstructed/path/test_client_path.py`.
   It runs on 60 random maps with four neighbour orders, with the retry rule corrected to the client's.
3. The path family of `scripts/validate_movement.py` (strict undefined-read machine, alternative neighbour
   tables, direct FindPath calls with limits 40/5 and mask 0xff, installed maps of worlds 0/2/3/142) now
   compares this library with the client. At `--cases 400 --mutations` its 400 path cases have 0 mismatches,
   and all of its mutations are detected. Its four path mutations now act on this source.
4. Its two mutations without an equivalent here (parent replaced on equal cost, wall test without the mask)
   were added to `scripts/validate_path.py`, which now detects 16 of 16.
5. The follower ports stay side by side: `reconstructed/movement` (used by `mu_walk`, with the speed
   predicates) and `mu_path_move` here (used by `mu_path`/`mu-path`). They have distinct symbols, and both
   equal the client on their compared cases.

## Unresolved

* **Static readings.** The siege-flag predicates, the speed rules beyond the player base, the run-counter
  conditions, the MoveHero gating and special-target branches, and the other-character branch are static
  readings only.
* **Not ported.** The height step after MoveCharacterPosition is not ported, and the native module uses
  the caller's terrain height.
* **Long-distance path.** The long-distance helper path is not reconstructed: `0x012b104c`, the
  `PATH_t` methods `0x0129c4d2..0x0129d4ca`, a budget of 300,000,000 and the trimming BuildPath variant.
* **Network.** SendMove and everything after it are outside this milestone.
* **Neighbour table.** The table comes from a manifest-less capture. A fresh restored capture of the
  third section would pin it properly.
