# Map-object records off the sector list, and Test Area 121's particle kinds

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; pinned text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` (base `0x00401000`), image data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. This closes two placement gaps that recent
lanes left named: the map-object update's records that do not follow their bone ([018](client-render-effects-018.md)
§1, "found, not changed"), and the three particle kinds Test Area 121's custom slot asks for but the particle module
refused ([RENDER-WORLDS-121](client-worlds-121.md) §4, §7). No live client session was needed or taken.

Evidence labels: **verified** = equal to the client's instructions under Unicorn
(`scripts/validate_render_effects19.py`); **static** = read from the disassembly; **live** = from the existing
read-only DATA-ACQ-002 captures.

## 1. The map-object update's matrix (verified)

RenderObjects calls the OBJECT update `0x0129f671(dt)` after RenderObjectVisual for every visible object with a
non-empty effect list (`0x016d51f5`, `0x016d536b`; [008](client-render-effects-008.md) §4). For each record it
builds an external matrix from the record's bone and follow byte. [018](client-render-effects-018.md) §1
reconstructed the routine and verified it against the client (`muun_update`); this lane routes the map objects
through that reconstruction.

**Which path a map object takes.**

| Record | Client | Before this lane (native) |
|---|---|---|
| follow, bone ≥ 0 | `0x0129fd4f`: the bone transposed; placed by `0x00cf2679(position, 0, scale) ×` only when `0x012a0d29` fails | the bone, never placed |
| follow, bone −1 | `0x0129faee`, the OBJECT's world matrix | same (RENDER-EFFECTS-007) |
| follow, bone < −1 | uninitialised matrix | treated as bone −1 |
| no follow, bone ≥ 0 | scale diagonal, translation `0x012a0030`: the bone's translation, plus the position when `0x012a0d29` fails | scale diagonal at the OBJECT position |
| no follow, bone −1 | scale diagonal at the position | same |
| no follow, bone < −1 | scale diagonal, no translation | at the position |

- **The bone source** (`0x0129f12c`): a map object's `+0x318` is 0, so every bone comes from the shared pose buffer
  `0x06fce398 + 0x30·bone`. RenderObject has just filled it with this object's pose, which already holds the body
  origin and scale. So for a record off the bone, `0x012a0030` gives the bone's world position: the client does not
  place it at the object position.
- **The sector predicate** `0x012a0d29` (static, read at `0x012a0d34..0x012a0d56`): true when `+0x350` (previous)
  or `+0x354` (next) is set. CreateObject appends every map object to the tail of its sector's list, so the
  predicate fails exactly for an object **alone in its sector**. Then the bone's translation gets the position added
  a second time (`0x012a00da`, `0x00cfccae`), and a following record is multiplied by the position/scale matrix:
  both land far from the object. **Live:** across the 32 DATA-ACQ-002 captures, 124 of 149,735 objects have both
  links 0, and every one of them is the only object of its sector (0 exceptions both ways). Eight followed table
  records sit on such objects (122: 2, 133: 5, 144: 1). None of the 19 unfollowed records does.
- **The table's unfollowed records** (RENDER-EFFECTS-008's export, 758 entries): 19, in worlds 56 (4), 135 (3),
  136 (3), 140 (1), 143 (1), 144 (4) and 145 (3), bones 0, 1 and 29. In the captures they attach to 135: 1,
  136: 2, 140: 9, 143: 1, 144: 114, 56: 8 objects, all in sector lists.

**Native.** `reconstructed/objects/map_effects.c` adds `mu_map_effects_in_sector` (the predicate from the objects
runtime's sector lists: an object is out only when it is its sector's head and has no next) and
`mu_map_effect_matrix` (the OBJECT image's scale `+0xa0`, position `+0x158` and angle `+0x164`, no own bones, the
pose as the shared buffer, then 018's `mu_object_effect_matrix`). `o_ein_update` (`native/core/mu_particles.c`)
calls both. A bone ≥ 0 needs the pose: without it, or beyond the model's bones (the client would read another
object's or a stale pose), the record is refused and counted (`unposed`), now also off the bone. Following a bone
below −1 is refused too. The bone −1 matrices are the same formula as before, so those records are unchanged.

**Validation.** `map_update` runs the client's `0x0129f671` on a map OBJECT (`+0x318` = 0) whose links come from a
synthetic sector list of one to five objects, with the object at the head, middle or tail. Native derives the
predicate from the same list (`mu_obj_world`, shuffled indices so a next index can be 0) and builds each matrix from
the OBJECT bytes. Domain: follow 0, 1, 2 and 0xff; bones −7, −2, −1, 0, 1, 7, 20, 29, the last posed bone and random
ones. Compared: every scale and node update in order. Each case also checks the refusals: no pose, a bone beyond the
pose, and a follower below −1. The private `map_records` family runs every one of the 758 decoded entries' bone and
follow byte, once alone in a sector and once in a list.

## 2. Test Area 121's particle kinds (verified)

The custom slot `0x00d58bd8` makes 28 CreateParticle calls for types 0x13..0x15 ([121](client-worlds-121.md) §1).
Native served 0x801c/8 (four sites) and refused the other three kinds. Each is its own branch of its bitmap's
subtype chain in CreateParticle `0x015ae7b0` and MoveParticles' record body, after the shared code (the record's
common fields; MovePosition with the rotated velocity):

| Kind | Create | Move |
|---|---|---|
| WATERFALL5 0x801e/7 (13 sites) | `0x015f236c`: the drawn bitmap `+0x10` becomes WATERFALL4 0x801d when `rand() % 2 == 0`; life 30, rotation r%360, scale (r%50)·0.05 + argument, velocity (−(r%2+1), −(r%2+3), r%3+3) | `0x016684c6`: scale −0.005, rotation +1, position += velocity (unrotated, a second time), light ÷1.1; then 0x801e's gates `0x0166886e`: life < 8 light ÷1.2, else life > 20 light ×1.1 |
| WATERFALL3 0x801c/9 (3 sites) | the prefix `0x015f4466` shared by subtypes after 0x19 (rotation r%360, scale (r%10+10)·0.02), branch `0x015f496e`: life 30, upward speed r%5+2, scale (r%5+5)·0.05 + argument; the jitter `0x015f5079`: x, y ± (r%40 − 20), z + r%20 − 10 | `0x0166b810`: scale +0.005, vertical speed −2.5, light ÷1.1; no WATERFALL3 tail |
| WATERFALL2 0x801b/5 (8 sites) | the prefix shared with 0x801b/4 (`0x015f27cb..0x015f2daa`: life 30, rotation, scale (r%6+6)·0.1, speed −(r%3+3), light 0.25 in scene 5 else 0.4, jitter ±10/±10/±20), then `0x015f30e0`: life 40, rotation r%360, `+0x6c` r%2+2, scale (r%6+6)·0.1 + argument, velocity (−(r%2+2), −(r%2+2), r%2+1), jitter x, y + r%60 − 30, z + r%10 | `0x01668bc8` (tested before the other subtypes): scale +0.03, speed +0.1, x, y += velocity, z += (`+0x6c` + speed z), light ÷1.1 |

Constants (image data): 0.05 `0x01a7e6d4`, 0.02 `0x01a7ed88`, 0.6 `0x01a7e9a0`, 0.1 `0x01a7df04`, 0.25 `0x01a7e6dc`,
0.4 `0x01a7df0c`, 10/20/30 `0x01a7e4d0/d4/d8`, 0.005 `0x01a7e4c8`, 1.1 `0x01a889d0`, 1.2 `0x01a7e6e4`, 2.5
`0x01a7e9ec`, 0.03 `0x01a7ed90`. RenderParticles draws 0x801e and 0x801b through its default case `0x015ae2bf` and
0x801c through `0x015a0297`, the same as their other subtypes; the bitmap is `+0x10`.

**Native.** `reconstructed/particles/test_area_kinds.inc` (three hook lines in `particles.c`). The world's particle
bitmaps gain WATERFALL4 0x801d (startup LoadBitmap `0x01822aa5`, LINEAR/CLAMP; `MU_WORLD_PT_BITMAPS` 75 → 76), so
the half of 0x801e/7 that draws it is not dropped.

**Validation.** `ta_pt_create`, `ta_pt_move`, `ta_pt_render` run validate_particles' families for the three kinds.
Records are drawn with 0x801d or 0x801e, lifetimes sit around 0x801e's gates (7, 8, 20, 21), and the gravity
`+0x6c` is set.

## 3. Who else asks for these kinds (static)

A scan of all 3,642 CreateParticle (`0x0168fafd`) call sites by their pushed type and subtype finds the three kinds
in two places only. One is the 121 slot (28 sites with 0x801c/8). The other is **Raklion's custom slot `0x00e949f8`**
(worlds 57/58), a copy of it: 0x801e/7 at 13 sites (`0x00e94e8f..0x00e95923`), 0x801c/9 at 3, 0x801b/5 at 8
(`0x00e95979..0x00e95bd3`), with the same type tests (6..12, 0x10, …). The October 22 Raklion capture holds types
19/20/21 two, three and eight times. Natively Raklion's custom slot is ported only for types 83/92
(RENDER-WORLDS-A's first meshes), so no native world requests these kinds today, and none was refused outside 121.
Raklion's 0x13..0x15 branch is the next consumer, and this module now serves it.

## 4. Fidelity

`fidelity_tour.py`, default draw, `MU_LANG_DIR` = the canonical lang plus RENDER-EFFECTS-008's `mapeffects.tsv` (the
table loaded, so the change can show). Before = the main binary; after = this branch.

- **DATA-ACQ-002:** 31/32 byte-identical (PNG frames, OBJECT and light dumps). The one change, 136 Burning
  Kethotum, masked mean |Δ| against the live window: **6.534 → 6.444**. Its type-25 record (lighting02-yellow03,
  bone 29, not following) moves from the object position (z 184) to the bone (z 440), the crystal's top, where the
  live window shows the glow.
- **Why the other unfollowed captures do not move (measured with a temporary debug print).**
  - Bone 0 is the model origin, so its posed translation is the object position: 135 (0.0 units), 56 and 144
    (≤ 1 unit). No pixel changes.
  - 140 and 143: no unfollowed record is in view at the arrival tile.
  - 122, 133, 144: none of the alone-in-sector objects is in view, so the placement change does not show.
- **October 22 tour:** 14/14 byte-identical.
- **World 121** (no capture; demo layout of the 23 slot types, 20 with a model, `--objects-dir`, 25 frames):
  particles created **56 → 92**, refused **36 → 0**, object-runtime refusals 0 → 0. The WATERFALL spray of
  0x13..0x15 now shows around the pillars.

## 5. Limits

- World 145 (three unfollowed records) has no capture; its Aquila slot bone (`0x0129fd4f(6)`, RENDER-WORLDS-S) still
  assumes a sector list, so an Aquila object alone in its sector would differ (static; not seen in any capture).
- A record on a bone beyond the posed model, and a follower below −1, are refused and counted (the client reads a
  stale pose or an uninitialised matrix).
- Raklion's custom slot types 0x13..0x15 are not ported (§3). Since ported by [RENDER-WORLDS-RAKLION](client-worlds-raklion.md).
- No live reference for world 121.
