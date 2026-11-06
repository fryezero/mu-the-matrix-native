# Imperial Guardian, Event square and Test Area primary handlers

RENDER-WORLDS-S3, 2026-11-06. Reconstructs the create (+2c), move (+30) and visual (+34) slots of the four
Imperial Guardian (Varka) classes (worlds 69, 70, 71, 72), Event square (world 114, not world 79's Loren Market
class) and Test Area (world 121). Coverage on base `83a21893` advances from **120/144 to 138/144 primary methods
and from 40/48 to 46/48 classes** (0 static-only, 6 missing: Nars 110 and the Arca War class 92/96/101/111, which
RENDER-WORLDS-S2 takes). With S2 merged (`317156ff`) the inventory reads 144/144 and 48/48.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from decoded
instructions only; **inference** = neither. None of these worlds has a live arrival capture and the installed object
files do not decode, so nothing here is a fidelity claim beyond the instruction comparison.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, both pin-checked.
Restored Linux/Wine x86 instructions, not native Windows evidence. No client was started.

Each create range ends at the class's move slot, each move at its visual slot and each visual at its custom-render
slot (half-open, capture09).

| Family | Original range | Body SHA-256 (prefix) | Cases | Mutants (weakest) |
|---|---|---|---:|---|
| ig69_create | `0x00dc6fab..0x00dc7136` | `9b0fa885742b83dc` | 1,000 | 2 (26) |
| ig70_create | `0x00dd3c76..0x00dd3e01` | `d4c4d7c863ef4f59` | 1,000 | 1 (55) |
| ig71_create | `0x00dd8d6d..0x00dd8ef8` | `ffe7a14829771753` | 1,000 | 2 (20) |
| ig72_create | `0x00dde9e0..0x00ddeb8a` | `b2bc9ded5886cc4b` | 1,000 | 2 (40) |
| ig69_move | `0x00dc7136..0x00dc73d0` | `3db36e7eaec7dd38` | 1,000 | 4 (11) |
| ig70_move | `0x00dd3e01..0x00dd4097` | `d82710cd1be9c8a4` | 1,000 | 4 (20) |
| ig71_move | `0x00dd8ef8..0x00dd9192` | `2f9272a6d132dff9` | 1,000 | 3 (26) |
| ig72_move | `0x00ddeb8a..0x00ddee5e` | `63ec9701d37c78c6` | 1,000 | 5 (7) |
| ig69_visual_bones / _frames / _emitters | `0x00dc73d0..0x00dc8b33` | `db11ffa9562f41b7` | 3 × 1,000 | 3 (137), 5 (4), 7 (15) |
| ig70_visual | `0x00dd4097..0x00dd57fa` | `3be979691ab4771e` | 1,000 | 3 (3) |
| ig71_visual | `0x00dd9192..0x00dda8f5` | `9d8ee54b40838757` | 1,000 | 3 (8) |
| ig72_visual_bones / _frames / _emitters | `0x00ddee5e..0x00de08df` | `14e096e810957a66` | 3 × 1,000 | 6 (12), 4 (4), 6 (9) |
| square_create | `0x00e1e989..0x00e1ea5c` | `ebc4aa39a4f46d87` | 1,000 | 1 (65) |
| square_move | `0x00e1ea5c..0x00e1ef15` | `d5d1a9ba13b9be36` | 1,000 | 2 (22) |
| square_visual | `0x00e1ef15..0x00e1f6ca` | `f6d9479360ebc70f` | 1,000 | 2 (29) |
| test_create | `0x00d585b0..0x00d58809` | `c607d2c2ffbbb96d` | 1,000 | 4 (44) |
| test_move | `0x00d58809..0x00d58888` | `56eb151de3988765` | 1,000 | 2 (41) |
| test_visual | `0x00d58888..0x00d58bd8` | `bdb17d82431072d8` | 1,000 | 4 (13) |

The two big visuals are each run as three families that sample one type group (bones 12/37/50/157, frame windows
20/51/64, emitters 79..86/129..132/158); every family executes the whole body and also samples the other types.

## Shared code (static, then verified per class)

The four Imperial Guardian classes are one source compiled four times. With branch targets made relative:

- **Create**: 69, 70 and 71 are byte-identical; 72 adds one case (type 10).
- **Move**: identical apart from the predicate call, the class's own static (`0x01ec9164`, `0x01ec9168`,
  `0x01ec916c`, `0x01ec9170`) and two deltas: class 70 lacks the `break` after its HiddenMesh case (those types also
  scroll the blend mesh), class 71's type-64 speed is 0.44 (others 0.64); class 72 adds the type-10 countdown.
- **Visual**: 69, 70 and 71 are identical apart from the predicate; 72 has the same type cases with other stack
  offsets, lacks case 51 and adds 157 and 158.
- **Predicates**: `0x00dd38c5` (69), `0x00dd897d` (70) and `0x00dde62f` (71) test their own world; class 72's
  `0x00de5519` accepts 72, 73 and 74. The factory registers no class for 73 or 74 (coverage JSON), so only the test
  of type 157 (no request in 73/74) depends on it.

Event square's three slots are Loren Market's (RENDER-WORLDS-I): create byte-identical (no predicate), move and
visual identical except the predicate call (`0x00e20416`: world 114). Test Area shares nothing with them.

The C follows that structure: one `imperial_guardian.c` with a class argument, Loren Market's bodies split into a
world-free core with thin per-world wrappers (`loren_market.c`, every string its existing mutants target kept), and
`test_area.c`.

## Verified methods

**Imperial Guardian create** (no predicate, no null test): types 0x73 and 0x75 set `+0x60 = 100`; class 72 type 10
sets `+0x60 = rand % 50`; types 0x81..0x84 set angle z to `(float)((int)z % 360)` (cvttss2si, so NaN and huge values
become INT_MIN % 360 = −128), copy the angle to the head angle (`+0x170`) and the position to `+0x17c` as dwords;
true for those types, false otherwise.

**Imperial Guardian move**: the predicate, then a second alpha step `0x012af883` (MoveObject already stepped it before
calling slot 0x30), false when `0.01 > alpha` or the type has no model, then the speed `+0xbc` scaled by 2 (type 20),
3 (122..124) or 6 (128) — class 72 instead counts type 10's `+0x60` down and rewinds frame and prior frame while it
is positive — and the animation tick `0x012b4dd3(&frame, &prior frame, &prior action, speed, position, angle)` on the
model. After the tick: type 20 compares its frame with the class static S: `S − frame > 10 or frame > S` stores the
frame in S, otherwise the frame takes S (all type-20 objects of the class follow the one that leads); type 64 speed
0.64 (class 71: 0.44); type 0x24 speed 0.02; types 0x4f, 0x50, 0x52..0x56, 0x81..0x84 HiddenMesh −2 (class 70 then
also does 0x51's case); type 0x51 blend V += 0.015. True for those types, false otherwise.

**Imperial Guardian visual** (predicate; no null test of object or model; bones are TransformPosition of the shared
bone matrices `0x06fce398 + 0x30·k`, Translate 0):

| Type | Requests |
|---|---|
| 12 | `s = |sin((float)(T · 0.0008))| · 0.9 + 0.1`; bone 2 local (8, −3, −3) and bone 3 local (3, −3, −3.5): sprites 0x7f6b scale 0.5 (0.9, 0.1, 0.1) and scale `scale · 0.3 · s` (s, s, s) |
| 20 | frame in (5.4, 6.5): four joints 0x7fd5 subtype 5 from the position to itself, angle (`rand % 60 + 150`, 0, z + 180), scale 10, owned, then particle 0x7f25 subtype 0xb with the last angle and the object light; else frame in (15.4, 16.5): the same with angle z |
| 51 (not 72) | the first window of type 20 only |
| 37 | bone 1: sprite 0x7f78 scale `4 · scale`, light `0.7 · ((sin(T · 0.039) + 1) · 0.2 + 0.6)` |
| 50 | bones 2..7 local (0, 0, 5): two 0x8089 subtype 4 particles, angle (0, −1, 0), (0.05, 0.1, 0.3) × `0.6 · scale` and white × `0.3 · scale` |
| 64 | frame in (9.5, 11.5) or (23.5, 25.5): position + VectorRotate((0, 30, 0), AngleMatrix(0, 0, z + 90)); three owned 0x7f89 subtype 0x16 (0.04, 0.03, 0.02) |
| 79 | sprite 0x7ef7 scale `2 · scale` (1, 0.2, 0); then by `rand % 3` 0x8084 sub 0, 0x806e sub 4 or 0x8085 sub 0 (white) |
| 80 | sprite 0x7ef7 scale `8 · scale`, `s = (sin(T · 0.04) + 1) · 0.3 + 0.4`, light (0.1s, 0.1s, 0.5s) |
| 82 | particle 0x801e subtype 9 with an **uninitialized stack light** (static; zero here, see below) |
| 83 / 84 | 0x801c subtype 0xe always / 0x801b subtype 4 on `rand % 8 == 0` (white) |
| 85 | `(int)T % 200` in 0..1: `rand % 4 + 4` CreateEffect 0x7f42 subtype 6, no owner, light 0.5, word4 `(u16)(int)scale` |
| 86, 129, 130 | `rand % 6 == 0`: owned 0x7f89 subtype 0x15, (0.05, 0.02, 0.01), (0.01, 0.02, 0.05), (0.01, 0.05, 0.02) |
| 131 / 132 | `rand % 3 == 0`: 0x7f5a white subtype 0x16 not owned / twice subtype 0x3c owned, then owned 0x7f5a subtype 0x15 at `2 · scale` |
| 157 (72) | in 73/74 true without requests; else bones 22, 23, 25 local (4, 0, 0): five times 0x8089 subtype 3 (0.9, 0.5, 0) × `0.2 · scale` and (0.75, 0.3, 0) × `0.1 · scale`; bones 26, 24, 21: four owned 0x7f5a subtype 0x41 white, scale `(float)(scale · 0.1)` in double |
| 158 (72) | owned 0x7f5a subtype 0x40 with an **uninitialized stack light** (zero here) |

True for every listed type after the predicate, false otherwise.

**Event square**: Loren Market's create (types 50..53/59 light-enable 0; 67 registered, box (100, 100, 160),
HiddenMesh −2; 68 after-character; returns false) and its move and visual (RENDER-WORLDS-I) behind world 114.

**Test Area** (no predicate, no null object test): *create* type 0x1a8 true; type 0x1ab three CreateEffect 0x1ab,
0x1ac, 0x1ad at (x, y − 40 / − 36 / − 20, z + 520), object angle and light, subtype 1, no owner; true; else false.
*Move* type 22 blend light = `sin(T · 0.001) + 1`; types 70 and 80 HiddenMesh −2; true; else the empty base method
`0x00d5c7a9` and false. *Visual* false without a model; types 70 (0.1, 0.4, 1) and 80 (0.7, 0.2, 0.1): by `rand % 3`
0x8086 sub 2, 0x8087 sub 6 or 0x8089 sub 2, then 0x8086 sub 2, none owned; true.

The families compare AL, all 984 OBJECT bytes, the four class statics, ordered recorded calls with their constant
arguments asserted (CreateParticle owner/tail; CreateSprite with its `{1, 1, 1.0}` descriptor and owner; CreateJoint's
fixed tail; CreateEffect's `-1, 0, word4, 0, 0.0, -1, 0, 0` and Test Area's offsets; the tick's six arguments and
model ECX; TransformPosition bone/local/Translate and ECX; Loren Market's Animation/TransformPosition/AddTerrainLight
service as in validate_worlds_i) and the final MSVC RNG. Executed as original code: the predicates, the alpha step,
AngleMatrix `0x00cff32a` with the CRT sine/cosine, VectorRotate `0x00d000ad`, the CRT sine wrapper, fabs
`0x0184f8ff`, the vector accessors, the sprite descriptor and Test Area's empty base call. Samples cover every listed
type plus signed extremes and random types, sibling worlds 0, 68..74, 79, 114, 121, alpha at the 0.01 gate (with
an equal target so the step keeps it) and NaN, frames at every window edge and NaN, class statics near the frame
(±10, 10.5, 10.9, 11, opposite zeros), angle z around the modulus, scale 0/−0/65535.9/70000/NaN, WorldTime at the
200-step clock edges, ±0, 2^31-scale and NaN, and seeds that open each 1-in-N branch in about 60 % of its cases.

**22,000 cases, zero mismatches or stops; 75/75 separately compiled planted mistakes are caught** (3 to 789 cases
each; weakest: the joint scale 12 in ig70_visual, 3; the second type-64 window bound, 4; the type-20 window bound in
class 72, 4). All 75 were compile-checked before the run; a first-draft mutant that removed class 72's create gate
did not compile (unused parameter) and was replaced by a value mutant. A first full run left three mutants
undetected (static lock bound 11, alpha `>=`, clock phase 2); the samples were made to reach them and the full run
repeated once.

**Uninitialized locals (static).** Types 82 and 158 pass a light vector the method never writes. The C passes zero
and the harness substitutes zero on the original side (as RENDER-WORLDS-S did for Debenter's TransformPosition local);
the client value is whatever the stack held.

## Native consumption

- `mu_obj_create` / `mu_obj_move` dispatch 114 and 121 after the generic part (one block each in `object_render.c`).
  Test Area's create effects use the create-effect layout of `object_render.c`; the runtime adds 121 to the worlds
  whose startup CreateEffect requests reach the existing effect hook at the first step (12 at most per world load).
- Imperial Guardian create and move run in the runtime's class pass, beside the Q worlds: create gets the objects
  RNG; move logs its own tick, the event loop applies it (`tick` and the action registry), then
  `mu_imperial_move_cases` runs on the ticked frame, as in the client. The class static is
  `mu_objects_runtime.imperial_frame` (zero at load; the client keeps its static for the process, so a second visit
  in one session can start from another value).
- The visual pass adds 69..72, 114 and 121 to the primary-visual worlds, with the outer RenderObjectVisual flicker rand
  first when the model is loaded (nothing without a model, as `0x017f9758` returns before the class slot). Imperial
  Guardian bone types without enough posed bones are refused and counted; the 0x7fd5 subtype-5 joints have no native
  kind (`mu_jt_kind_supported`) and are refused and counted; the 0x7f42 word4 effects go to the existing owned-effect
  consumer (refused and counted without a word4 hook). Event square's types 30/35 need bones 3/2 as Loren Market's.
- No shared particle/effect/joint hook source changed.

The production host `native/tests/worlds_s3_host.c` runs ten-object authored populations of 69, 70, 71, 72, 114 and
121 through `mu_objects_start`, 200 steps and the visual pass with a 28-bone model of two 30-key actions: Imperial
Guardian creation writes, two ticks per object per step (one for 121), type 20 holding the class static, hidden
types, the type-0x51 scroll, six sprites and at least thirteen particles per frame, zero joints with counted
refusals, refusals with two bones; class 72's countdown and type 157/158/50 particles; Event square stepping
byte-identically to the same population in world 79 (images and lights); Test Area's three startup effects, blend
light and hidden types, four particles per frame. Portable tests check public dispatch, the class deltas, predicates,
the visual requests with and without bones and that zero/one/full log capacity leaves state, RNG and the static
unchanged.

## Smoke check and regression

The installed client has `World70..73`, `World115` and `World122` (Data folder = world + 1); the object files are
encrypted as for 145/95/139, so no population exists. Headless `mu-world` arrivals at 69 (150,30), 70 (30,70),
71 (110,190), 72 (30,70), 114 (30,30) and 121 (110,30), 25 steps at 1722 × 1048: rc 0, terrain and hero drawn
(mean luminance 8–38), zero objects. These tiles come from a coarse brightness scan, not from gates.

Byte identity, base `83a21893` against this lane merged with S2 (`317156ff`) at the default draw: the October 22 fourteen-view tour **28/28 PNG,
14/14 OBJECT, 14/14 light identical**; all 32 DATA-ACQ-002 captures **64/64 frame PNG, 64/64 comparison PNG, 32/32
OBJECT, 32/32 light identical**. Loren Market (79) is captured and unchanged.

## Follow-ups and limits

| Request | Status |
|---|---|
| Joint 0x7fd5 subtype 5 (type 20/51) | Refused and counted: no native joint kind (RENDER-EFFECTS) |
| CreateEffect 0x7f42 word4 (type 85) | Existing owned-effect consumer; refused and counted without a word4 hook |
| Types 82/158 light | Zero (inference); uninitialized stack in the client |
| Class static of type 20 | Per loaded world natively, per process in the client |
| Test Area startup effects | Existing startup consumer, 12 requests per world load |
| Custom render / after render / invisible move | Outside the primary count: 69 `0x00dc8b33`/`0x00dc9f33`, 70 `0x00dd57fa`/`0x00dd5888`, 71 `0x00dda8f5`/`0x00dda93e`, 72 `0x00de08df`/`0x00de0ff6`, 114 `0x00e1f6ca`/`0x00e1f8ff`, 121 `0x00d58bd8`/`0x00d5a6cc`; invisible move is the base `0x00d5cbbc` for all six |
| Default hook chain | Not ported here: MoveObject's hooks before slot 0x30 (`0x00e7dd29`, `0x00e845d0`, `0x00d53c8f`/`0x00d53da7`) and after (`0x00e30b86`, `0x00e5f629`, `0x00ea594b`/`0x00ea2c2b`); RenderObjectVisual's chain before the class slot (`0x009db8b1`, `0x00def747`, `0x00d8e640`, `0x00dfc095`, `0x00d622dd`, `0x00dac0a2`, `0x00e75089`, ...) |
| Loren Market (79) outer flicker rand | The native 79 branch draws none, unlike the other primary-visual worlds and `0x017f9758`; left unchanged here (captured world, byte identity), worth a check by a later lane |
| Imperial Guardian handler state `+0x14` (pre-move slot, RENDER-WORLDS-AFTER2) | Still 0; the primary slots read no handler or server state |
| Live population, RNG phase, image fidelity of 69..72, 114, 121 | No capture; event instances need entry the live rules forbid |
| Nars (110), Arca War (92/96/101/111) | RENDER-WORLDS-S2 |

Reproduce with `scripts/run_validators.py --private --only validate_worlds_s3`, `scripts/world_handler_coverage.py`,
`reconstructed/objects/test_worlds_s3.py` and `native/tests/test_native_worlds_s3.py`. Checks are in the
[handoff](../handoffs/RENDER-WORLDS-S3.md).
