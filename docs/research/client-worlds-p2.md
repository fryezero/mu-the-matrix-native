# Kanturu Underground and Ignis Volcano primary handlers

RENDER-WORLDS-P2, 2026-10-28. Reconstructs the create (+2c), move (+30) and visual (+34) slots of the
world-137 class (Kanturu Underground) and the world-138 class (Ignis Volcano), both captured by DATA-ACQ-002.
Coverage advances from **52/144 to 58/144 primary methods and from 18/48 to 20/48 classes** (0 static-only,
86 missing). None of the six methods is large (the Kanturu visual is 475 instructions), so all six are complete.

Labels: **verified** = compared with the original instructions under Unicorn or with a live capture;
**static** = read from decoded instructions only; **inference** = neither.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, both pin-checked. The
validator report also hashes each range below. These are restored Linux/Wine x86 instructions, not native
Windows evidence. No live client was started; the populations are DATA-ACQ-002's arrival captures.

| Family | Original half-open range | Cases |
|---|---|---:|
| Kanturu Underground create (predicate `0x00e0df03`) | `0x00e08cd8..0x00e08f8a` | 1,000 |
| Kanturu Underground move | `0x00e08f8a..0x00e092f4` | 1,000 |
| Kanturu Underground visual | `0x00e0a4bb..0x00e0ab2a` | 1,000 |
| Ignis Volcano create (predicate `0x00e0895c`) | `0x00e05afe..0x00e05d76` | 1,000 |
| Ignis Volcano move | `0x00e05d76..0x00e05f25` | 1,000 |
| Ignis Volcano visual | `0x00e07081..0x00e0709e` | 1,000 |

Each move range ends at the class's custom-render slot (`0x00e092f4`, `0x00e05f25`); each visual range ends at
its after-render slot (`0x00e0ab2a`, `0x00e0709e`).

## Verified methods

**Kanturu Underground create.** Returns false when the world is not 137 (predicate `0x00e0df03`) or the object
is null. Otherwise clears `+0x07` (the record's dynamic-light flag), looks up the type's model
(`0x00966cc4` → `0x00eaa8cf`) and, when present, sets the PlaySpeed (`+4`) of every action record
(count `+0x26`, signed) to 0.3. HiddenMesh −2 for 40, 45–52, 54–56, 65–68, 106, 111, 114–117, 120–122.
Type 3 calls the register service `0x016d9f51(o, 0)` (argument 0, not 1 as in other classes). Types 125–127
set `+0x34 = rand % 30 + 20`. Range −300 for 0, 2, 9, 17, 18, 22, 25, 27, 28, 42, 57, 59, 60, 64, 76, 79, 81,
85, 92–96. Returns true for every type.

**Kanturu Underground move.** Same predicate and null check. Type 10: velocity 0.04, blend light
`sin(t · 0.0015) + 1` clamped to [0.1, 0.9]; type 38: blend light `min(sin(t · 0.001) + 1, 1)` (NaN → 1);
type 44: velocity 0.02. Types 125–127 run an action machine: no model → false; when
`frame ≥ (keys(action) − 1) − (PlaySpeed(action) + frame time 0x01cf103c)`, a counter `+0x30` and limit `+0x34`
step through actions 0 → 1 (limit 1) → 2 (limit 25) → 3 (limit 1) → 0 (limit `rand % 30 + 20`) via SetAction
`0x012affa4`; the counter increments every qualifying call; other actions do nothing; returns true. Other types
false.

**Kanturu Underground visual** (`o`, model). False for a null object or model. Types 54/120, 65/121, 66/122:
one `rand % 20 / 10 / 5`; on zero a CreateJoint `0x0153b02c(0x7f7d, p, p, angle, 14/15/12, owner o/0/0,
30·scale + rand % (int)(10·scale), −1, 0, 0, −1, 0, −1, 0)`; true. Types 8, 92–96: `s = (sin(t · 0.001) + 1) ·
0.5`; TransformPosition of bone 4 at local 0; CreateParticle `0x7f2b` (that point, angle, light (s, s, s),
subtype 0, scale 1.5); CreateSprite `0x7f26` (point, 10, light, owner o, rotation 0); then from/to points
`(x − 50 − rand%100, y − rand%50, z + 10)` and `(x + rand%80, y + rand%50, z + 10)` and, on `rand % 20 == 0`,
CreateJoint `0x7f7c` subtype 0x12, scale 40, no owner; true. Other types false.

**Ignis Volcano create.** Returns false off world 138 (predicate `0x00e0895c`) or for null. With a model, writes
velocity 0.16 once per action (`+0x26 > 0`). Range −800 for 0–11, 13, 16, 17, 29, 30, 46, 58, 59, 95, 153, 154,
157, 171, 173 (0–8 through a jump table whose nine entries all land there); 45 gets range −800 and the
after-character flag; 79 and 148 clear the model's StreamMesh byte `+0x94`; HiddenMesh −2 for 88, 126, 127, 136,
146, 147, 175, 176. Returns true.

**Ignis Volcano move.** Same predicate/null check. Type 88: `s = (rand % 4 + 3) · 0.1`, AddTerrainLight at the
object's x/y, RGB `(0.8s, 0.3s, 0.04s)`, range 3, frame light; true. Type 177: action 1 with frame < 8, or
action 3 with frame > 28, plays sound 0x570 owned by the object and returns true; otherwise false.

**Ignis Volcano visual** `0x00e07081` returns false on every path and requests nothing.

The six families compare AL, all 984 OBJECT bytes, the model header and an eight-record action table (and
StreamMesh byte), ordered recorded calls with their constant arguments asserted (register, AddTerrainLight
with the frame light, CreateParticle, CreateSprite with its `{1, 1, 1.0}` descriptor, CreateJoint with its
fixed tail, PlayBuffer, TransformPosition bone/local/out and the model ECX) and the final MSVC RNG. Predicates,
SetAction, the CRT sine wrapper, the vector helpers and the SEH frames execute as original code. Samples cover
signed type extremes, every type −1..130 (137) or −1..180 (138) plus random and directed types, worlds 0, 38,
136–140, null objects and models, action counts −3..8, actions 0–7, counters/limits around the transitions,
frames at and around each threshold and NaN, scales including ±1e10 and NaN, frame times and WorldTime samples
including ±0, 2^31-scale values and NaN.

**6,000 cases, zero mismatches or stops; 35/35 separately compiled planted mistakes are caught** (predicates,
flag clear, PlaySpeed value, hidden/range/flag/stream/register lists, the rand ranges, sine rates and clamps,
key arithmetic, action targets and limits, counter increment, bone index, particle scale, joint
modulus/subtype/owner, light divisor/range, sound thresholds and the visual return). Two first-draft clamp
mutants (`>=` ↔ `>` at the exact bound) were equivalent and were replaced by value mutants.

Excluded from execution, recorded as boundaries (static): `sin(±∞)` enters the CRT's errno path (finite huge
values and NaN are covered); a visual scale with `(int)(10·scale) == 0` divides by zero in the client (the C
refuses it); Ignis types 79/148 without a model write through a null pointer; Kanturu reads the current action's
record without a bound check (cases keep the action inside the table).

## Native consumption

`mu_obj_create`/`mu_obj_move` dispatch worlds 137 and 138 after the generic part. Kanturu's create emits a
PlaySpeed event with action `0xffffffff` (all actions); the runtime records it as "every action" so the action
machine can read it. Its `+0x34` rand uses a per-object MSVC seed (the client's global RNG phase is not
reproduced). Ignis's velocity write equals the generic 0.16 and is not repeated; its StreamMesh request has no
native consumer and is **refused and counted** in `create_unsupported` (11 objects at the arrival capture).

The client runs the animation tick before the world's move; the native log runs the tick after
`mu_obj_move` returns. So Kanturu's types 125–127 log `MU_KANTURU_UG_ACTION_STEP`, and the runtime calls
`mu_kanturu_ug_move` again after the tick with the loaded model's key counts, the creation PlaySpeed and the
render pass's 0.1 frame-time stand-in. Out-of-range actions or unset speeds are counted in `move_unsupported`.

The world-137 visual dispatch uses the posed object's bone 4 (`visual_bone`); without enough posed bones types
8/92–96 request nothing and count one `draw_unsupported`. Particles and sprites go to the existing consumers.
Joints go through the existing joint hook only when `mu_jt_kind_supported`; all four Kanturu kinds (`0x7f7d`
subtypes 12/14/15, `0x7f7c` subtype 0x12) are not modelled by the native pool, so they are **refused and
counted** in `draw_unsupported`. No shared particle/effect/joint hook source changed.

Production host `native/tests/worlds_p2_host.c` creates authored ten-object populations in both worlds through
`mu_objects_start` with a five-bone, four-action model and runs 200 steps plus the visual pass per world: flags,
tables, PlaySpeed, the clamps, the full 0–1–2–3 action cycle of type 125, one sprite and particle per frame for
type 8, refused joints, one type-88 light per step at the right x/y with range 3, the 0x570 sound and the
counted StreamMesh refusals. Portable tests check public dispatch, the deferred step, the visual with and
without bones and that zero/one/full log capacity leaves state and RNG unchanged.

## Saved-population regression and fidelity

Method of [captures 2](client-world-captures-2.md): `scripts/fidelity_tour.py run` at each arrival tile,
1722 × 1048, 25 steps, the same live object/globals/light/PNG captures and plaintexts, installed assets. "Before"
is this branch's base `35cab4a`; "after" is this lane. The before run reproduces the captures-2 numbers.

| Capture | Static field differences (objects, map) | Near hero | Drawn | Lights / particles / sprites | Frame light near hero | Image mean \|Δ\| / > 24 |
|---|---|---|---|---|---|---|
| Kanturu Underground 137 | range 6,028 → 0; velocity 11 → 3; blend light 11 → 14; hidden 24 → 24; after-character 20 → 20 | 141 → 42 | 334 → 404 | 0 / 0 / 0 → 0 / 16 / 16 | 0 → 0 | 5.899 / 0.0458 → 5.790 / 0.0450 |
| Ignis Volcano 138 | range 775 → 0; after-character 262 → 0 | 39 → 0 | 214 → 236 | 0 → 72 lights | 0.0216 → 0.0239 | 4.139 / 0.0368 → 4.139 / 0.0368 |

**Verified against live captures:** every range difference of both captures and every Ignis after-character
difference is gone (7,065 differences); zero missing/extra; primary light stays exactly equal; camera unchanged.

**Remaining, reported as measured:** Kanturu's 20 after-character and 24 hidden-mesh differences (types 10,
76, 93, 94, 96, 110 and 1, 2, 28 with mesh 1 hidden) are not written by these three slots; they belong to the
class's custom/after-render slots or the default hook chain (inference). Type 10's blend light is a WorldTime
phase effect: the live clock clamps it at 0.1 while the native step time gives 0.9 (before: the untouched 1.0);
three type-10 objects keep the live default velocity 0.16 because the client had not moved them yet. Ignis's
near-hero frame light rises slightly: the 72 new type-88 lights have the right range and colour ratios but a
different RNG/clock phase than the frame the client captured. Ignis's image is unchanged at three decimals;
Kanturu's improves slightly. Visual inspection of Kanturu: same layout; the pillar tops are brighter natively
(blend-light phase) and the live shot's cyan pylon flares are smaller natively.

**Existing scenes:** base and lane binaries give identical outputs for the October 22 fourteen-view tour
(**28/28 PNG, 14/14 OBJECT, 14/14 light**) and for the other 30 DATA-ACQ-002 captures (**60/60 PNG, 30/30
OBJECT, 30/30 light**).

## Follow-ups and limits

| Request | Status |
|---|---|
| Kanturu joints `0x7f7d` subtypes 12/14/15 and `0x7f7c` subtype 0x12 | Refused and counted; need joint kinds in `mu_jt_kind_supported` (RENDER-EFFECTS) |
| Ignis StreamMesh byte `+0x94` = 0 for types 79/148 | Refused and counted; needs a model StreamMesh consumer |
| Kanturu custom render `0x00e092f4` (large), after render `0x00e0ab2a`; Ignis custom `0x00e05f25` (large), after `0x00e0709e` | Outside the primary count; still missing; likely source of the Kanturu after-character/hidden-mesh differences |
| CreateObject/MoveObject default hook chain after a false return | Not modelled for these worlds |
| Frame time `0x01cf103c` | Native uses the render pass's 0.1 stand-in |

Each capture is one arrival frame: no particle/effect pools, RNG phase or emitter windows. No new live read
was taken.

Reproduce with `scripts/run_validators.py --private --only validate_worlds_p2`, `scripts/world_handler_coverage.py`,
`reconstructed/objects/test_worlds_p2.py`, `native/tests/test_native_worlds_p2.py` and the tour above. Checks and
gate are in the [handoff](../handoffs/RENDER-WORLDS-P2.md).
