# Map-object box, mouse-over handlers and the inner-object census

RENDER-WORLDS-PICK-001, 2026-11-15. This continues [AFTER6](client-worlds-after6.md) §1 and §6 (the registry's
mouse-over tick handlers 4 and 6, which had no box and no mouse segment natively) and the "all-world census"
that [INNER-005](client-worlds-inner.md) left open. Target `main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; capture09 text and run10 data are pinned in
`scripts/pins.py`. Offline and static only: no live client, no event or server state.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from the
disassembly; **inference** = neither.

## 1. Where the box comes from (static, then verified)

The box OBJECT `+0x31c` is 12 binary32: StartPos, XAxis, YAxis, ZAxis.

**Initial value (static).** The object's constructor builds it at `0x0129e92b` (`0x00a5fb8b`, four vector
constructors) and the initialiser zeroes its start at `0x0129ef45` (`0x00cfcf7b` = zero vector). A map object
that has not been drawn yet holds an all-zero box.

**The write (static).** RenderObject's setup `0x017ec896` ends with BMD::Transform. Both call sites pass the
same three pointers:

| Site | Bones | Call |
|---|---|---|
| `0x017edc62..0x017edc95` | the object's own buffer (`0x0129f11a`) | `Transform(bones, o+0x128, o+0x134, o+0x31c, translate, 0, 0.4, +0xe4, +0xe8)` |
| `0x017edc9d..0x017edd08` | the shared buffer `0x06fce398` | the same |

- The call goes through the wrapper `0x00966ea5`, which adds the three output arrays (`0x078978a0`,
  `0x0812cce0`, `0x06fd0918`) and calls the transform `0x012b5bde` (`ret 0x30`).
- Before the call the setup copied the object's position `+0x158` into the model's body origin `+0x78`.
- `validate_object_render`'s render family already checks those three pointer arguments at the call.

**The box tail `0x012b6479..0x012b678a` (static, then verified).**

1. Bounds mode `0x0b437bfc` == 2: start = the running minimum of the transformed vertices, and X.x, Y.y, Z.z =
   maximum − minimum. The running bounds start at 999999 / −999999 (`0x012b5da3`) and take each stored vertex
   with `comiss; jbe` (`0x012b6164`): a NaN component changes neither bound.
2. Any other mode: start = the object's box minimum `+0x128` (a bit copy), and X.x, Y.y, Z.z = `+0x134` − `+0x128`.
3. Both: start += the body origin `+0x78`, then the six off-diagonal axis terms are written 0.

**The mode is 0 in the game (static).**
- The text holds nine references to `0x0b437bfc`: `0x012b5da5`, `0x012b6166`, `0x012b647b`, `0x016d67ee`,
  `0x016d67f7`, `0x017edf6b`, `0x017edf74`, `0x018001a0`, `0x01859873`. All nine are `cmp m32, imm8`. There is
  no store.
- The address lies past the initialised image data (`0x01a7c000..0x01cec744`), so it starts as zero.
- The validator recounts both facts on every run (`bounds_mode_references` in its report).
- The protection modules stay opaque and were not read; a write from there is not excluded by this.

**Consequence.** For a map object the box is axis-aligned: its start is box minimum + position, its axes are
the box extents. The object's angle and scale do not enter it. Mode 2 is the editor's branch; there they enter
only through the posed vertices. "Oriented" describes the storage layout, not the content the game writes.

The box minimum and maximum are CreateObject's: (−40, −40, 0)..(40, 40, 80) by default, with the per-type
values `reconstructed/objects` already carries (Lorencia 0 / 1: ±150 and 500; several worlds: height 160).

## 2. The segment test and the handlers (verified)

`0x018500bf(p1, p2, box by value)` and its six axis tests `0x01850d88` are unchanged from
[AFTER6](client-worlds-after6.md) §1; so are the handlers:

| Id | Handler | Reads |
|---|---|---|
| 4 | `0x00ce1947` | MousePosition `0x0bdc5984` → MouseTarget `0x0bdc5990` against `+0x31c` |
| 6 | `0x00ce1e4b` | the same, with the latch `+0x34` |

Two facts are new here, both from running the original:

- **A touching segment is over the box.** The axis test rejects only a strict gap (`lo_segment > hi`,
  `lo > hi_segment`). A segment that ends exactly on a face, runs along an edge line, passes through a corner
  or lies in a face plane is reported as over, except where another axis separates it (9 of 59 edge-line cases
  and 2 of 89 in-plane cases in the final run).
- **An unwritten box is always over.** With a zero start and zero axes all six projections are 0, so the test
  returns 1 for every segment, NaN ends included (68 of 68 cases). An object with a handler 4 or 6 row is
  therefore "under the mouse" until its first draw writes a real box.

## 3. Native port

| Piece | Where |
|---|---|
| The box write, the mode-2 bounds, the exported segment test | `reconstructed/objects/object_pick.{c,h}`; `mu_obj_segment_obb` wraps the registry's existing static test in `action_registry.c` |
| Binding in the runtime | `native/core/mu_objects_runtime.c` `write_obb`: called where `mu_obj_render`'s log holds the setup's Transform call, and in the after-character prepare |
| Mouse segment | `rt.mouse_start` / `rt.mouse_end` (borrowed pointers), set by `native/world/parts/objects.c` from the walk frame's `view.mouse_position` / `view.mouse_target`, read by `mu_objects_anim_tick` |
| Counter | `rt.obb_writes` |

- The write needs no pose: mode 0 reads only the object and the body origin. The runtime's draw inputs carry
  mode 0, as the client. A caller that asked for mode 2 would be refused and counted; none exists.
- The mouse segment is the one the walk frame computed last, as `in.camera` is for handler 8. Charsel, login and
  the terrain tool set no segment: their handlers 4 and 6 still count unsupported.
- The step-input struct is unchanged. Two pointers and one counter are appended to `mu_objects_runtime`.

**Which live rows use this: none.** The local MapObjectAnimationInfo table (143 rows in 10 worlds) uses
handlers 0, 1, 2, 5, 7 and 8. Nothing in a captured world changes. This closes a known adapter gap; it is not
a visible gain. The default identity sweep in the handoff confirms that.

## 4. Checks

`scripts/validate_worlds_pick.py --cases 1000 --mutations` (registered `validate_worlds_pick`, pins text, data,
feature09). The wrapper, the transform, the segment test, the tick and both handlers run as client code. Stubs
are the registry getter, GetModel and rand, as in AFTER5/6.

| Family | What runs as client code | Cases | Result |
|---|---|---:|---|
| `box` | `0x00966ea5` → `0x012b5bde` on a model of 0..2 meshes posed by the object's turn, scale and position; modes 0, 1, 3, −1, 0x102 and 2; NaN and infinite box values; NaN vertices | 1,000 | equal (mode 0: 562, other non-2: 192, mode 2: 246) |
| `segment` | `0x018500bf` + `0x01850d88` on a box the client wrote (or left unwritten), with hit, miss and boundary segments | 1,000 | equal |
| `pick` | the client's box write, then the tick `0x00ce4b5b` → handler 4 or 6 with the same segment classes | 1,000 | equal |

- **3,000 cases equal, 0 mismatches, 0 stops.** All OBJECT bytes are compared in `box` and `pick`, plus the
  tick's return value and the rand sequence in `pick`.
- In `box`, 968 of 1,000 objects are turned or scaled. All 754 non-2 cases equal "box + origin" computed
  apart from the port, and every case has zero off-diagonal terms.
- In mode 2 the native bounds are rebuilt from the positions the client's transform stored. Their skinning is
  `validate_skinning`'s subject. Mode 2 uses translate 0 (the static-object call), where the stored position
  is the bounded one.
- Boundary cases use integer-valued boxes, so every boundary coordinate is exact in binary32.
- **23/23 compiled mutants caught** (lowest count 23, none stopped): the origin add and its axis, the extent
  sign and source, the Z extent, an off-diagonal term, the minimum field, the box offset, the mode test, the
  mode-2 source, the bounds' start value, minimum, maximum and NaN handling, the segment's box offset, both
  boundary comparisons, the negative extent, the dropped box axis, the hover's box offset and end point,
  handler 4's leave branch and handler 6's latch.
- Three first-round mutants needed work before the single counted run: two did not compile under `-Werror`
  (an unused parameter), and `e >= 1` against `e > 0` is equivalent on integer-valued boxes; it was replaced by
  the negative-extent sign.

Portable tests:
- `reconstructed/objects/test_worlds_pick.py`: 7 synthetic tests (default and type boxes, turn and scale, stale
  axes, mode 2 with an empty and a NaN vertex list, hit / miss / boundary segments, the chain into handlers 4
  and 6 including the unwritten box), plus 1 private.
- `native/tests/test_native_worlds_pick.py` (`pick_host.c`): the production runtime with an authored
  `mapanim.tsv`. No segment: counted unsupported. After a draw: the box equals box + position for a turned,
  scaled object. A segment through the box switches the handler 4 row and one on the face plane keeps it; one
  unit outside returns it. Handler 6 latches. An undrawn object's zero box is over at once.

## 5. The all-world inner-object census

INNER-005 left "list, for every world's inner-object routine, each object type the original handles". The
census is [`world-inner-census.csv`](world-inner-census.csv), written by `scripts/world_inner_census.py`.
"Inner-object routine" is every routine RenderObjectVisual `0x017f9758` can reach for a map object:

| Group | Routines | Where |
|---|---:|---|
| RenderObjectVisual's own world cases | 1 | world jump table `0x017fccd0` (worlds 0..17) plus worlds 52 and 55 |
| Hooks of the common chain | 13 | `0x017fcb5c..0x017fccbc`, in call order, before the class manager |
| Visual slot +0x34 of the factory classes | 48 | reached through the manager `0x00ea2dc1` |

The custom-render (+0x38) and after-render (+0x3c) slots are other passes and are not in this census.

### Method (static, on the pinned text)

`world_inner_census.py` is an abstract interpreter. It runs a routine with a concrete world and a concrete
object type. Values derived from them stay concrete. Everything else (the model, rand, the clock, floats,
other globals) is unknown, and a branch on an unknown value explores both sides.

- **A case** is the code reached with type t that an unlisted type does not reach, provided it does something
  beyond choosing a path: a call, a float operation, or a write outside the frame. Types that only walk more of
  a switch table and land on the default are not cases.
- **Candidate types** come from the routine: every constant a type-derived value is compared with, its two
  neighbours, and every index of a jump or index table the type selects, until no new constant appears. Types
  between two neighbouring constants behave alike.
- **Worlds.** A hook is walked for worlds 0..160. Worlds whose unlisted type reaches the same code are one
  group, and the largest group is the hook's "not mine" answer unless it has cases too.
- **Followed calls:** the world-handler code region `0x00d50000..0x00eb0000` and small straight leaves (world
  tests, getters). **Recorded, not followed:** CreateParticle, CreateSprite, CreateJoint, CreateEffect,
  RenderMesh, RenderBody, PlayBuffer, AddTerrainLight, the terrain bitmap and the bone transform, with their
  immediate stack arguments. A request id chosen at run time prints as `?`.

The walk reproduces the tables earlier lanes read by hand: Kanturu 37/40, Blood Castle, Kalima, Crywolf, Land
of Trials, Aida, Kanturu Remain, the tower, Barracks/Refuge, Elbeland and Swamp of Calmness, type for type and
request for request.

### Native status

Three sources, no hand list:

1. **Consumer oracles**, called in the built libraries for each (kind, subtype) a case requests:
   `mu_pt_kind_supported` (particles), `mu_jt_kind_supported` (joints) and `skill_fx.c`'s `effect_supported`
   (effects, through a one-function shim).
2. **A native probe per (world, type)**: `mu-world` with one authored object of the type at the hero's tile,
   40 steps, every step drawn. Its own report gives the object runtime's refused draws and the pools' created
   and refused requests. The context is authored (position (12650, 12750, 500), idle hero, default clock); it
   is not a placement and not an event state.
3. **Source citation** as a fallback: a routine whose entry the reconstructed and native sources never name,
   and for which the probe shows nothing, has no native producer.

| Status | Rule |
|---|---|
| drawn | no refused draw, no refused request, and every requested consumer exists |
| partial | a consumer is missing (listed), or the probe counted refused draws or requests (counts listed) |
| refused | every draw is counted unsupported; or no native producer; or no model file for the type in the world's object folder; or the world could not be probed |

A world without terrain in the installed data cannot be probed. It borrows the probe of another world that
runs the same case, and the row says so. Worlds that share an object folder share one probe.

### Results

Walked at the merged lane commit with its own `mu-world` (SHA-256 in the handoff): **62 routines, 730 rows
(world x case), 941 (world, type) pairs.**

| Status | Pairs | Of which |
|---|---:|---|
| drawn | 420 | 64 rest on the source citation only (their case makes no request the probe can count) |
| partial | 213 | a missing consumer and / or refused requests in the probe |
| refused | 308 | 274 no native producer (chain hooks 1 and 6); 15 every draw refused; 13 no model file; 6 not probed |

| Routine | Entry | Worlds with cases | Cases | Drawn | Partial | Refused |
|---|---|---|---:|---:|---:|---:|
| RenderObjectVisual world case | `0x017f9758` | 0-4,6,8-17,52,55 | 33 | 46 | 8 | 2 |
| chain 1: 0x009db8b1 (Chaos Castle worlds) | `0x009db8b1` | 18-23,53,97 | 12 | 0 | 0 | 272 |
| chain 2: Kalima | `0x00def747` | 24-29,36 | 9 | 42 | 28 | 0 |
| chain 3: Crywolf | `0x00d8e640` | 30 | 6 | 4 | 2 | 0 |
| chain 4: Land of Trials | `0x00dfc095` | 31 | 3 | 3 | 0 | 0 |
| chain 5: Aida | `0x00d622dd` | 33,54 | 14 | 30 | 2 | 0 |
| chain 6: 0x00dac0a2 (world 34) | `0x00dac0a2` | 34 | 2 | 0 | 0 | 2 |
| chain 7: Kanturu | `0x00e75089` | 37,40 | 16 | 23 | 6 | 3 |
| chain 8: Kanturu Remain | `0x00e7df87` | 38 | 15 | 13 | 1 | 1 |
| chain 9: tower | `0x00e84941` | 39 | 14 | 8 | 6 | 0 |
| chain 10: Barracks / Refuge | `0x00d5404b` | 41-42 | 12 | 10 | 7 | 7 |
| chain 11: singleton 0x01ec9118 slot +0x34 | `0x00db7656` | 45-50,98-99 | 11 | 8 | 80 | 0 |
| chain 12: Elbeland | `0x00e3116a` | 51 | 9 | 7 | 1 | 1 |
| chain 13: Swamp of Calmness | `0x00e5f94b` | 56 | 11 | 8 | 3 | 0 |
| class world-121 (World 121 class) slot +0x34 | `0x00d58888` | 121 | 2 | 2 | 0 | 0 |
| class world-128 (World 128 class) slot +0x34 | `0x00d5d564` | 128 | 1 | 1 | 0 | 0 |
| class world-129 (World 129 class) slot +0x34 | `0x00d5f1f1` | 129 | 1 | 1 | 0 | 0 |
| class world-130 (World 130 class) slot +0x34 | `0x00d60948` | 130 | 1 | 1 | 0 | 0 |
| class world-91 (World 91 class) slot +0x34 | `0x00d6ae34` | 91 | 15 | 15 | 0 | 0 |
| class world-145 (Aquila's Temple) slot +0x34 | `0x00d77b3e` | 145 | 1 | 6 | 0 | 0 |
| class world-92 (World 92 class) slot +0x34 | `0x00d7be80` | 92,96,101,111 | 1 | 0 | 0 | 4 |
| class world-134 (Gray Aida) slot +0x34 | `0x00d84dd8` | 134 | 13 | 8 | 5 | 6 |
| class world-136 (Burning Kethotum) slot +0x34 | `0x00d97186` | 136 | 1 | 1 | 0 | 0 |
| class world-93 (CGMCharacterScene_Ex) slot +0x34 | `0x00daa9dd` | 93 | 11 | 11 | 0 | 0 |
| class world-95 (Debenter) slot +0x34 | `0x00dbd735` | 95 | 9 | 3 | 14 | 0 |
| class world-64 (Duel Arena) slot +0x34 | `0x00dc6790` | 64 | 2 | 2 | 0 | 0 |
| class world-69 (World 69 class) slot +0x34 | `0x00dc73d0` | 69 | 17 | 8 | 8 | 1 |
| class world-70 (World 70 class) slot +0x34 | `0x00dd4097` | 70 | 17 | 8 | 8 | 1 |
| class world-71 (World 71 class) slot +0x34 | `0x00dd9192` | 71 | 17 | 8 | 8 | 1 |
| class world-72 (World 72 class) slot +0x34 | `0x00ddee5e` | 72 | 18 | 5 | 8 | 5 |
| class world-112 (World 112 class) slot +0x34 | `0x00de6405` | 112 | 19 | 11 | 9 | 0 |
| class world-132 (Red Smoke Icarus) slot +0x34 | `0x00e00e97` | 132 | 2 | 5 | 0 | 1 |
| class world-137 (World 137 class) slot +0x34 | `0x00e0a4bb` | 137 | 4 | 12 | 0 | 0 |
| class world-143 (Kardamahal) slot +0x34 | `0x00e117e8` | 143 | 1 | 1 | 0 | 0 |
| class world-80 (Karutan) slot +0x34 | `0x00e13be4` | 80-81 | 7 | 14 | 0 | 0 |
| class world-123 (World 123 class) slot +0x34 | `0x00e1b5fb` | 123-127 | 1 | 5 | 0 | 0 |
| class world-114 (World 114 class) slot +0x34 | `0x00e1ef15` | 114 | 7 | 7 | 0 | 0 |
| class world-94 (CGMLogInScene_Ex) slot +0x34 | `0x00e24be1` | 94 | 3 | 3 | 0 | 0 |
| class world-110 (World 110 class) slot +0x34 | `0x00e26ae7` | 110 | 20 | 18 | 2 | 0 |
| class world-82 (World 82 class) slot +0x34 | `0x00e2c002` | 82 | 5 | 6 | 2 | 1 |
| class world-135 (Old Kethotum) slot +0x34 | `0x00e3c137` | 135 | 3 | 3 | 0 | 0 |
| class world-62 (Santa Village) slot +0x34 | `0x00e423d8` | 62 | 3 | 3 | 0 | 0 |
| class world-144 (Swamp of Destruction) slot +0x34 | `0x00e47bc2` | 144 | 1 | 2 | 0 | 0 |
| class world-141 (Tormenta Island) slot +0x34 | `0x00e4ef4b` | 141 | 12 | 12 | 0 | 0 |
| class world-122 (World 122 class) slot +0x34 | `0x00e5540e` | 122 | 2 | 2 | 0 | 0 |
| class world-142 (Twisted Karutan) slot +0x34 | `0x00e6841f` | 142 | 7 | 6 | 1 | 0 |
| class world-79 (Loren Market) slot +0x34 | `0x00e6c678` | 79 | 7 | 7 | 0 | 0 |
| class world-100 (Uruk Mountain) slot +0x34 | `0x00e6f3d5` | 100 | 14 | 13 | 1 | 0 |
| class world-63 (Vulcanus) slot +0x34 | `0x00e8ece1` | 63 | 7 | 4 | 3 | 0 |
| class world-57 (Raklion) slot +0x34 | `0x00e946a8` | 57-58 | 2 | 4 | 0 | 0 |

The routine names are the CSV's `routine` column. Twelve classes name no type in their visual slot: 113, 115..120 (all share the base `0x00d5cc9b`), 131, 133,
138, 139 and 140. Their rows would be empty, so they have none.

**Missing consumers.** 66 distinct (kind, subtype) pairs are requested by some case and have no native
consumer: 53 particle, 9 effect and 4 joint pairs. The 22 most requested, by (world, type) pairs; the CSV's
`missing` column has all of them per row:

| Missing consumer | (world, type) pairs | Worlds |
|---|---:|---|
| particle 0x7f89/15 | 32 | 45-50,98-99 |
| particle 0x7dec/0 | 16 | 45-50,98-99 |
| particle 0x7f89/21 | 12 | 69-72 |
| particle 0x7f89/6 | 10 | 11-17,41-42,52 |
| particle 0x8000/0 | 10 | 11-17,41-42,52 |
| particle 0x8000/1 | 10 | 11-17,41-42,52 |
| particle 0x8001/0 | 10 | 11-17,41-42,52 |
| particle 0x7dea/0 | 10 | 45-50,95,98-99,112 |
| particle 0x8022/0 | 8 | 45-50,98-99 |
| particle 0x8022/3 | 8 | 45-50,98-99 |
| effect 0x4cc/0 | 8 | 45-50,98-99 |
| effect 0x4cc/1 | 8 | 45-50,98-99 |
| particle 0x7f89/17 | 8 | 45-50,98-99 |
| particle 0x7f78/4 | 8 | 11-17,52 |
| particle 0x7f25/11 | 7 | 69-72 |
| particle 0x7ef7/6 | 7 | 24-29,36 |
| particle 0x801a/0 | 7 | 24-29,36 |
| particle 0x801b/0 | 7 | 24-29,36 |
| effect 0x193/3 | 5 | 33,37,40,54,134 |
| particle 0x7f89/24 | 5 | 95 |
| particle 0x7f89/22 | 4 | 69-72 |
| particle 0x801e/9 | 4 | 69-72 |

**The 15 pairs whose every draw is refused** (the runtime's own count, in the authored probe context):
Gray Aida 134 types 65, 66, 77, 78, 132, 133 (the scrolled mesh rows); classes 69..72 type 50 (bone particle
0x8089/4); Red Smoke Icarus 132 type 10; Elbeland 51 type 58 (the unwritten stack light INNER-002 refuses);
Kanturu 40 types 70, 105, 110.

### Findings for the next world lanes

1. **Chain hook 11 is the visual of worlds 45..50 and 98..99, and so the 46/98 handler.** It is a virtual call
   on a singleton, which the direct-call search of INNER-005 could not see. This lane ports its producer
   ([inner finding](client-worlds-inner.md), last section). Its rows moved from refused to 8 drawn and 80
   partial; what remains are the ten consumer pairs in the table above.
2. **Chain hook 1 `0x009db8b1` has no native producer: 272 pairs.** World test `0x009dacb8` (18..23, 53, 97,
   the Chaos Castle worlds). A 36-entry jump table on the type:
   - 0..3: with the object's word `+0x54` set and not hidden, the bone named `light` is transformed; while the
     counter `+0x6c` is 10 it requests a 0x7f7d/2 joint (scale rand % 10 + 60) and sound 0x9c + rand % 2; the
     counter then steps down, and below 5 the word clears;
   - 6..12: unless hidden, ten (6, 7, 8), five (9, 10, 11) or seven (12) owned 0x7f89 smokes of subtype
     0, 1, 2, 3, 4, 5, 7, then hidden −2;
   - 18..21, 24..29, 30..35: hidden −1 or −2 by the state byte `0x01cf0467`;
   - 4, 5, 13..17 and the tail of every case: hidden −2 when that byte is 2 or more and not 0xff.
   The state byte is event state. A port needs it as an authored input, as Crywolf's byte is.
3. **Chain hook 6 `0x00dac0a2` has no native producer: 2 pairs.** World test `0x00dabe97` (world 34). Type 41
   draws two 0x7f78 sprites from process counters (`0x01ec9108`, `0x01ec910c`) and the render counter
   `0x06fc9c90`; type 84 emits 0x7f5a/21 at rand % 3 == 0 when the byte `0x01ec90ae` is 1.
4. **World 55's own case `0x017fc71f`** names types 61 (shared with Dungeon's code), 84 and 89. The installed
   data has no terrain for it, so 84 and 89 are not probed.
5. **The world 92 class** (92, 96, 101, 111) names one type, 1435, and none of its four worlds has terrain in
   the installed data.

### Limits of the census

- The probe is one authored object for 40 draws. A rarely gated request (a clock window, rand % 50) may not
  fire; the `evidence` column says whether activity was `observed` or the row rests on the `source` citation.
  The consumer oracles do not depend on the probe.
- 83 pairs in worlds 45, 47..50, 54, 55 and 99 borrow another world's probe (no terrain in the installed
  data); the row names the world.
- 9 rows hit the walk's step limit (classes 69..72 type 85, class 82 type 4, class 92 type 1435): their
  request list may be incomplete. 27 rows carry a request id chosen at run time (`?`).
- Requests are the ten recorded engine entries. A case that only writes object fields shows no request.
- "Drawn" means the producer runs without a counted refusal and every requested consumer exists. It is not an
  image comparison, and it says nothing about placement, event state or the create and move slots (the
  `notes` column flags create / move refusals the probe counted).
- The statuses are a snapshot of this commit. Rerun the script after a consumer or producer lane.

Reproduce (private inputs, from the repo root, about 3 minutes for the walk and 11 for the probes):

```sh
. ~/Documents/MTM/mu-mac-tools/native/private-env.sh
nice -n 10 make -j4 && nice -n 10 make -C native -j4 world
tools/python/bin/python scripts/world_inner_census.py --json <scratch>/census-raw.json \
    --csv docs/research/world-inner-census.csv --summary <scratch>/census-summary.json
tools/python/bin/python scripts/world_inner_census.py --probe 00e75089,37   # one routine, one world
```


## 6. Limits

- No live row uses handlers 4 or 6, and no capture shows them. The end-to-end evidence is the chain family and
  the host test.
- The mouse segment is one frame old at the tick, like the camera position of handler 8. The client's exact
  order of MouseTarget's write and MoveObjects within a frame was not compared.
- The after-character prepare writes the box from the position without re-running the setup's alpha test for
  Chaos Castle worlds (that pass is an approximation of the setup already).
- The picking globals `0x0bdc58c8` / `0x0bdc58e4` remain outside native state.

[Handoff](../handoffs/RENDER-WORLDS-PICK-001.md).
