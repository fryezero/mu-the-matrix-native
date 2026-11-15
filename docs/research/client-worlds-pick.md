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

## 5. Limits

- No live row uses handlers 4 or 6, and no capture shows them. The end-to-end evidence is the chain family and
  the host test.
- The mouse segment is one frame old at the tick, like the camera position of handler 8. The client's exact
  order of MouseTarget's write and MoveObjects within a frame was not compared.
- The after-character prepare writes the box from the position without re-running the setup's alpha test for
  Chaos Castle worlds (that pass is an approximation of the setup already).
- The picking globals `0x0bdc58c8` / `0x0bdc58e4` remain outside native state.

[Handoff](../handoffs/RENDER-WORLDS-PICK-001.md).
