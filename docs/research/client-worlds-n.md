# Nixies Lake and Deep Dungeon primary handlers

RENDER-WORLDS-N, 2026-10-28. Reconstructs the create (+2c), move (+30) and visual (+34) slots of the
Nixies Lake class (world 113) and the five Deep Dungeon classes (worlds 116–120), all captured by
DATA-ACQ-002. Coverage advances from **33/144 to 52/144 primary methods and from 11/48 to 18/48 classes**,
with zero static-only entries and 92 missing. The 19 new entries are the 18 slots of the six classes plus
world 115's visual slot, which is the same entry `0x00d5cc9b` (world 115 itself has no capture; its create
`0x00d5cb99` and move `0x00d5cc16` stay missing).

Labels: **verified** = compared with the original instructions under Unicorn or with a live capture;
**static** = read from decoded instructions only; **inference** = neither.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, both pin-checked. The
validator report also hashes each instruction range below. These are restored Linux/Wine x86 instructions,
not native Windows evidence. No live client was started; the populations are DATA-ACQ-002's arrival captures.

| Family | Original half-open range | Cases |
|---|---|---:|
| Nixies create (with predicate `0x00e34404`) | `0x00e3441c..0x00e3473f` | 1,000 |
| Nixies move | `0x00e3473f..0x00e347a8` | 1,000 |
| Deep Dungeon 1–5 create | `0x00e3e34b..0x00e3e46d`, `0x00e3efe6..0x00e3f125`, `0x00e3fce8..0x00e3fe3c`, `0x00e409e8..0x00e40b38`, `0x00e41823..0x00e41a1f` | 5 × 1,000 |
| Deep Dungeon 1–5 move | `0x00e3e46d..0x00e3e94a`, `0x00e3f125..0x00e3f602`, `0x00e3fe3c..0x00e40319`, `0x00e40b38..0x00e41015`, `0x00e41a1f..0x00e41efc` | 5 × 1,000 |
| Shared visual (worlds 113, 115, 116–120) | `0x00d5cc9b..0x00d5cca8` | 1,000 |

## Verified methods

**Shared visual `0x00d5cc9b`** is `xor al, al; ret 8`: it returns false and requests nothing. No native visual
dispatch is added; the C function exists for the comparison.

**Nixies Lake create** returns false when the world global is not 113 or the object pointer is null, otherwise
true for every type. Range −400 for types 0–3, 7, 8, 10, 11, 23, 33, 34, 51, 52, 70, 71, 78, 80, 84, 85, 99, 102,
115, 118, 128, 130, 133, 146, 150, 157, 159. After-character flag `+0xa` for 20, 37–42, 44, 45, 53, 105, 107, 108,
114, 126, 139, 141. HiddenMesh −2 for 21, 113, 117, 119–123, 161. Type 106 gets both range −400 and the flag.
**Move** has the same predicate and null check; type 77 sets BlendMesh V (`+0xb0`) to
`(float)((int)WorldTime % 2000) * 0.0005` and returns true; every other type returns false.

**Deep Dungeon create** has no world predicate. The five classes run one template and differ only in the
range −400 list: 116 {6}; 117 {0, 1, 3, 50}; 118 {0, 3, 5, 6, 23, 50}; 119 {0, 5, 18, 35, 50}; 120 {0–7, 9–11, 14,
20–24, 30, 36, 37, 48, 50, 53}. All five then hide 39, 40, 51, 52 and 62–67 (HiddenMesh −2), register type 59
(`0x016d9f51(o, 1)`), and register type 60, set its box max to (40, 40, 160) and hide it. Handled types return
true, others false. 118–120 dispatch through jump tables; the type tables were read by executing the
original for every type −3..419 and are covered again by the random families.

**Deep Dungeon move** is identical in all five classes and has no world predicate. Types 62–67 draw one
`rand`, `s = (float)(rand % 4 + 3) * 0.1`, and call AddTerrainLight at the object's x/y with range 3 into the
frame light. RGB factors: 62 (0.12, 0.58, 0.32), 63 (0.1, 0.41, 0.8), 64 (s itself, 0.6, 0.2), 65 (0.74, 0.17,
0.62), 66 (0.77, 0.74, 0.63), 67 (0.8, 0.3, 0.04). Types 22–24 set BlendMesh V to
`-(float)((int)WorldTime % 1000) * 0.001`, keeping −0.0. Types 41/42 return true with no change. Type 52 draws
one `rand`; at `rand % 3 == 0` it calls CreateEffect `0x013c0eaa(0x43a, position, angle, light, 0, 0, −1, 0,
(u16)(int)scale, 0, 0.0, −1, 0, 0)`; it returns true either way. Other types return false without a `rand`.

All thirteen families compare AL, all 984 OBJECT bytes, ordered recorded calls (register; AddTerrainLight with
the frame-light grid asserted; CreateEffect with its pointer and constant arguments asserted) and the final MSVC
RNG. The predicate, the client's vector helpers and its SEH frames execute as original code. Samples cover signed
type extremes, every type −1..164 (Nixies) or −1..71 (Deep Dungeon) plus random types, the world global varied
across 0 and 112–121, null objects (Nixies), directed handled move types, scale edge values for the effect key
(−1, 0, 65535.9, 65536, 70000, 1e10, NaN) and WorldTime including ±0, multiples of 1000/2000, ±2^31, ±infinity,
NaN and random values.

**13,000 cases, zero mismatches or stops; 29/29 separately compiled planted mistakes are caught** (world
predicate, each class's range list, register/box/hidden cases, default return, light range/factors/rand divisor,
scroll modulus/sign/rate, effect type/owner/gate, handled no-op types and the visual return). Original
instructions are never mutated.

## Native consumption

`mu_obj_create`/`mu_obj_move` dispatch worlds 113 and 116–120 to the new methods after the generic part, as for
the earlier classes; the generic move still runs exactly one animation tick. AddTerrainLight requests use the
existing frame-light consumer. The type-52 keyed CreateEffect is logged as `MU_DEEP_DUNGEON_KEYED_EFFECT` and
counted in `move_unsupported` instead of being forwarded: the shared effect hook fixes the key at 0xffff, and
effect type 0x43a has no native consumer. Hooks belong to RENDER-EFFECTS-004; no shared hook or particle source
changed.

Boundaries (static or inference, not executed): when a create slot returns false the original CreateObject
continues into its default hook chain (`0x00d8e18f`, `0x00dfbc3f`, `0x00d6200e`, …); each of those starts with
its own predicate call (static), and this lane neither models nor executes them for these worlds, as in the
earlier lanes. The same holds for MoveObject after a false move return.

The production host (`native/tests/worlds_n_host.c`) creates authored ten-object populations in worlds 113,
116–120 and sibling 112 through `mu_objects_start`, checks range/after-character/hidden/box/register results,
then runs 200 production steps per world: exactly one generic tick per object per step, two class lights per
Deep Dungeon step at the right x/y with range 3 and the original factor rounding, the type-22 and Nixies scrolls,
type-52 refusals counted (no particle or effect events), and no class activity in world 112. The portable tests
check public dispatch, the signed zero, the effect key and that zero/one/full log capacity leaves object state
and RNG unchanged.

## Saved-population regression and fidelity

Method of [captures 2](client-world-captures-2.md): `scripts/fidelity_tour.py run` at each DATA-ACQ-002 arrival
tile, 1722 × 1048, 25 steps, the same live object/globals/light/PNG captures and plaintexts, installed assets
from the free-runtime prefix. "Before" is this branch's base `d4b6a11`; "after" is this lane. The before run
reproduces every number in captures 2 exactly.

| Capture | Static field differences (objects) | Near hero | Objects drawn | Object lights | Frame light near hero | Image mean \|Δ\| / > 24 |
|---|---|---|---|---|---|---|
| Nixies Lake 113 | range 3,402 + after-character 436 → 0 | 169 → 0 | 299 → 308 | 0 → 0 | 0.0156 → 0.0156 | 7.001 / 0.0632 → 7.001 / 0.0632 |
| Deep Dungeon 1 116 | range 149 → 0 | 0 → 0 | 129 → 129 | 0 → 168 | 0.0205 → 0.0224 | 5.745 / 0.0626 → 5.570 / 0.0709 |
| Deep Dungeon 2 117 | range 1,421 → 0 | 57 → 0 | 132 → 150 | 0 → 144 | 0.0198 → 0.0088 | 4.453 / 0.0297 → 4.081 / 0.0271 |
| Deep Dungeon 3 118 | range 1,716 → 0 | 69 → 0 | 278 → 317 | 0 → 312 | 0.0238 → 0.0119 | 14.168 / 0.2082 → 13.475 / 0.2093 |
| Deep Dungeon 4 119 | range 1,105 → 0 | 27 → 0 | 91 → 103 | 0 → 144 | 0.0277 → 0.0214 | 10.017 / 0.1372 → 9.440 / 0.1498 |
| Deep Dungeon 5 120 | range 5,897 → 0 | 178 → 0 | 354 → 405 | 0 → 336 | 0.0371 → 0.0189 | 6.353 / 0.0532 → 6.665 / 0.0582 |

**Verified against live captures:** every static OBJECT field the tour compares now equals the live client
for all 28,687 objects of the six captures: the 13,690 range and 436 after-character differences are gone,
with zero missing/extra. Primary terrain light stays exactly equal (0). Camera and far plane are
unchanged.

**Image (mixed, reported as measured):** mean error falls in four Deep Dungeon captures (by 0.17–0.69) and rises
in Deep Dungeon 5 (+0.31); the share of pixels off by more than 24 rises in 116, 118, 119 and 120. Nixies Lake's
image is unchanged at three decimals. The near-hero frame-light error falls in four of five Deep Dungeon
captures. Visual inspection of Deep Dungeon 5: the new warm lights of types 62–67 now fall on the native
building blocks at the upper left, which the native world already draws untextured (pale grey before, orange
after); the live client shows textured walls and brazier fires there. The lights match the original method;
the remaining error belongs to the missing textures and brazier visuals, not to this lane's methods.
WorldTime and RNG phase differ between the two sides, so per-frame light strength is not compared.

**Existing scenes:** the October 22 fourteen-view tour (worlds 0/1/2/3/4/7/8/10/33/37/51/57/80, same captures,
camera and 25-step endpoint) rendered with the base and the lane binaries gives **28/28 PNG, 14/14 OBJECT and
14/14 light hashes identical**; the frame reports differ only in their output paths.

## Follow-ups and limits

| Request | Status |
|---|---|
| Deep Dungeon type 52 CreateEffect `0x43a`, key `(u16)(int)scale` | Refused and counted; needs a keyed-effect consumer (RENDER-EFFECTS) |
| World 115 create `0x00d5cb99` / move `0x00d5cc16` | Static: both `xor al, al; ret 4`; no capture, out of scope |
| CreateObject/MoveObject default hook chain after a false return | Not modelled for these worlds (static predicates) |
| Custom render `0x00e347a8`, after render `0x00e3628c` (113) and the shared `0x00d5cc8e`/`0x00d5cc60`/`0x00d5cbbc` slots | Outside the primary-method count; still missing |
| Untextured Deep Dungeon blocks and brazier fires | Native asset/visual gap, outside these methods |

Each capture is one arrival frame: no particle/effect pools, RNG phase or emitter windows. The image
numbers come from the Wine-track renderer's live shots. No new live read was taken.

Reproduce with `scripts/run_validators.py --private --only validate_worlds_n`, `scripts/world_handler_coverage.py`,
`reconstructed/objects/test_worlds_n.py`, `native/tests/test_native_worlds_n.py` and the tour above. The checks
and gate are in the [handoff](../handoffs/RENDER-WORLDS-N.md).
