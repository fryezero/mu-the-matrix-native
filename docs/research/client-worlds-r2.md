# Twisted Karutan, Kardamahal and Swamp of Destruction primary handlers

RENDER-WORLDS-R2, 2026-10-28. Reconstructs the create (+2c), move (+30) and visual (+34) slots of the world-142
class (Twisted Karutan), the world-143 class (Kardamahal Underground Temple) and the world-144 class (Swamp of
Destruction), the last three classes DATA-ACQ-002 captured. Coverage advances from **76/144 to 85/144 primary
methods and from 26/48 to 29/48 classes** (0 static-only, 59 missing) on its base `5fa43cd`. No method is large
(the Swamp visual is a 34-entry jump table over seventeen near-identical joint cases), so all nine are complete.

Labels: **verified** = compared with the original instructions under Unicorn or with a live capture;
**static** = read from decoded instructions only; **inference** = neither.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, both pin-checked. The
validator report also hashes each range below. These are restored Linux/Wine x86 instructions, not native
Windows evidence. No live client was started; the populations are DATA-ACQ-002's arrival captures.

| Family | Original half-open range | Body SHA-256 (prefix) | Cases |
|---|---|---|---:|
| Twisted Karutan create (predicate `0x00e6bd5a`, world 142) | `0x00e67546..0x00e6766a` | `cb15bf2d3967ce79` | 1,000 |
| Twisted Karutan move | `0x00e6766a..0x00e677a9` | `41b675ab9e578eed` | 1,000 |
| Twisted Karutan visual | `0x00e6841f..0x00e68c6a` | `1e6371b434f977d2` | 1,000 |
| Kardamahal create (predicate `0x00e136f3`, world 143) | `0x00e0ea04..0x00e0ed1c` | `5e1d27ef1405f2d7` | 1,000 |
| Kardamahal move | `0x00e0ed1c..0x00e0f4bc` | `354f2508e3246269` | 1,000 |
| Kardamahal visual | `0x00e117e8..0x00e118fd` | `8bd8b6fbec50bc0c` | 1,000 |
| Swamp of Destruction create (predicate `0x00e4bb8d`, world 144) | `0x00e46625..0x00e4696f` | `06a64966e5a264d6` | 1,000 |
| Swamp of Destruction move | `0x00e4696f..0x00e46a9f` | `ae93f43e4a1cd1e8` | 1,000 |
| Swamp of Destruction visual | `0x00e47bc2..0x00e48f1c` | `a94e19debfda09b2` | 1,000 |

Each move range ends at the class's custom-render or invisible-move slot; each visual range ends at its after-render
slot. The create ranges include their jump tables.

## Verified methods

All three creates and moves return false when the world predicate fails or the object is null; the visuals
return false for a null object or model.

**Twisted Karutan create.** After-character (`+0x0a`) = 1 for types 1, 3, 54–58, 62, 66, 119–125, 162, 163,
167–178, 197, 198 (types 163–198 through a 36-entry byte-indexed jump table). Returns true.

**Twisted Karutan move.** Type 160: `s = (rand % 4 + 3) · 0.1`, AddTerrainLight at the object's x/y, RGB
`(s, 0.6s, 0.2s)`, range 2, frame light. Returns true for every type.

**Twisted Karutan visual.** Returns true for every type.
Type 72: `s = abs'((float)sin((float)(t · 0.0004))) · 0.4`, where `0x0184f8ff` is `0 > x ? −x : x` (it keeps
−0 and NaN, unlike `fabsf`). TransformPosition of bone 11 at local (20, 0, 0), then CreateSprite 0x7ef7 (scale
2, light (1.3s, 1.3s, 1.9s)) and 0x7f26 (scale 1.5, light 0.15); the same pair at bone 7 with scales 4 and 1.5.
Type 113: sprite 0x7ef7 at the object, scale 2·scale, light (1, 0.2, 0); then on `rand % 3` CreateParticle
0x8084 sub 0, 0x806e sub 4 or 0x8085 sub 0 (light 1, scale the object's). Type 114: on `rand % 3 == 0` particle
0x801c sub 0x10, light 0.2. Type 115: when HiddenMesh ≠ −2, twenty particles 0x7f89 sub 0x1d light 0.04 owned
by the object; HiddenMesh = −2 always. Type 116: on `rand % 8 == 0` particle 0x7f5a sub 0x45 light (0.5, 0.9,
0.5) and particle 0x7f5a sub 0x15 with the object's light, scale·2, owned. Type 118: HiddenMesh = −2. Type 196:
on `rand % 50 == 1` CreateEffect 0x199 (position, angle, light 0.1, sub 0, owner the object, info word4 =
`(uint16_t)(int)scale`).

**Kardamahal create.** Type 0: z = 64, after-character 1, `+0x06`, `+0x05`, `+0x0b` cleared. Types 4, 28, 114:
after-character 1. Types 34–47, 69, 106, 107, 109: `+0x07` (dynamic light) cleared. Range: 78 → −50, 110 → −230,
115 → −150, 124 → −100. HiddenMesh −2 for 161–167, 169, 171, 172 (164–172 through a nine-entry jump table);
168 gets HiddenMesh −2 and range −50; 170 nothing. Then types 34–47 compute `z = z − 0.0` (a no-op except that a
signalling NaN is quieted; kept with a `volatile` zero). Returns true.

**Kardamahal move.** Type 113: `s = (rand % 4 + 3) · 0.1 · 0.4 + 0.4`, light (s, 0.2s, 0.1s), range 3. Type 115:
model lookup (no model: true, no rand); `s = (rand % 4 + 3) · 0.1 · (1 − 0.4) + 0.4`; Animation(model, shared
bones, frame, prior frame, prior action, angle, head angle, 0, 1); for the names E002…E009 (eight std::strings)
the named-bone lookup `0x0129f18a(name, 1)`; for each bone found, zero-local TransformPosition and a light
(s, 0.2s, 0.1s) range 4 at its x/y. Types 126–130: the same s as 113, range 2, colours (0.74, 0.17, 0.62),
(1.2, 0.84, 0.53), (s, 0.2, 0.1)·s, (0.1, 0.41, 0.8), (0.12, 0.58, 0.32). Sounds (owner 0): 133 → 0x5a6; 146/149
in action 2 → 0x5a9; 150–152 → `rand % 2 == 0 ? 0x5a7 : 0x5a8`; 167 → 0x5a4; 169 → 0x5a5. Those types return
true; every other type returns false.

**Kardamahal visual.** Type 161: on `rand % 80 == 1` CreateEffect 0x195 with the object's light, sub 0, owner
the object, word4 `(uint16_t)(int)scale`. Returns true.

**Swamp of Destruction create.** Range −300 for 6, 13, 16, 18, 21, 23–28, 31, 33–39, 43, 54, 55, 57, 59, 66, 67,
73, 74, 77–79, 82, 90, 91, 94, 106, 107, 109–113, 116, 120–122, 125–127, 129–132, 140–142, 145–148, 153, 181,
183, 200 (127–148 through a 22-entry jump table); 32 and 64 get range −300 and after-character 1; 76
after-character 1. Returns true.

**Swamp of Destruction move.** Type 183: Kardamahal's 113 light, range 3. Returns true for every type.

**Swamp of Destruction visual.** Returns true for every type. Types 160–169 and 187–193 (34-entry jump table): on
`rand % 50 == 0` the object's light (`+0xec`) is overwritten, then CreateJoint 0x7f7d from the object to the
object (position, position, angle, owner the object, scale the object's). Colours/subtypes: 160/165 (0.93, 0.11,
0.14), 161/166 (0.17, 0.8, 0.3), 162/167 (0, 0.6, 0.9), 163/168 (0.7, 0.25, 0.6), 164 (1, 0.8, 0.3), 169
(1, 0.8, 0.4) with subtype 0x12 for 160–164 and 0x19 for 165–169; 187–193 light (1, 0.65, 0) with subtypes 0x1a,
0x10, 0x11, 0x18, 0x19, 0x12, 0x13. Type 185: on `rand % 200 == 0` a light (0.01, 0.25, 0.01) whose components
are each scaled in double by `(rand % 100) · 0.005 + 0.2`, then CreateEffect 0x199 sub 1, owner the object,
word4 `(uint16_t)(int)scale`.

The nine families compare AL, all 984 OBJECT bytes, ordered recorded calls with their constant arguments
asserted (AddTerrainLight with the frame light, PlayBuffer `(id, 0, 0)`, CreateParticle owner/tail, CreateSprite
with its `{1, 1, 1.0}` descriptor, CreateJoint with its fixed tail, CreateEffect with `-1, 0, word4, 0, 0.0, -1,
0, 0`, TransformPosition bone/local/out and the model ECX, Animation's eight arguments, the named-bone lookups
in order, the string-array destructor) and the final MSVC RNG. The predicates, the CRT sine wrapper, the
`0x0184f8ff` abs, the vector helpers, the sprite descriptor constructor and the SEH frames execute as original
code; rand, the services above, the std::string constructor `0x0094997e` and the EH vector destructor
`0x0191b937` are recording boundaries (the harness keeps each string's source pointer; the named-bone stub maps a
random subset of E002…E009 to bone indices). Samples cover every type −1..200 (142), −1..175 (143), −1..202
(144) plus signed extremes and random/directed types, worlds 0, 80, 141–145, null objects and models, actions
0–7, HiddenMesh −2/−1/0/3, scales including −0, NaN, ±1e10 and 65537.5 (word4 wrap), z = −0, +∞, quiet and
signalling NaNs for the Kardamahal subtraction, WorldTime including ±0, 2^31-scale values and NaN, and seeds
chosen so each 1-in-N branch opens in about 60 % of its directed cases.

**9,000 cases, zero mismatches or stops; 56/56 separately compiled planted mistakes are caught** (3 to 786
cases each; the weakest: Kardamahal 168's −50 range, 3; the −230 range and the skipped `z − 0.0`, 4). The
first draft's skipped-subtraction mutant was not caught because no sample combined a signalling NaN with types
34–47; those samples are now directed (every eighth case), so it is a real mutant. A first-draft mutant that
removed the visual's `has_model` use did not compile (unused parameter) and was replaced by a value mutant.

Excluded from execution, recorded as boundaries (static): `sin(±∞)` enters the CRT's errno path (finite huge
values and NaN are covered); the named-bone lookup's own scan of the model's bone names and its `+0x318` (own
bone buffer) branch are not executed; the std::string internals are not executed.

## Native consumption

`mu_obj_create`/`mu_obj_move` dispatch worlds 142–144 after the generic part (one block each in
`object_render.c`). The move runs after the generic animation tick in the event order, as in the client
(P's tick-order note); only Kardamahal 115 depends on it: its `MU_KARDAMAHAL_BONE_LIGHTS` event is resolved by the
runtime after the tick, posing the object's model with this object's origin and lighting each bone whose name is
E002…E009 (no pose or no model: refused and counted in `move_unsupported`). The client instead poses with the
model's current BodyOrigin (no origin write before its Animation call): the last object of that type it rendered
(inference; identical when one such object is in view).

The visual pass adds 142–144 to the primary-visual worlds: it consumes the outer RenderObjectVisual flicker rand
(the class slot is reached through `0x017f9758`'s default chain after it, as for Karutan and P), then calls the
class visual. Twisted Karutan type 72 uses the posed object's bones 11 and 7; without twelve posed bones it
requests nothing and counts one `draw_unsupported`. Sprites and particles go to the existing consumers with the
recorded owner. Swamp joints 0x7f7d subtypes 0x10–0x13/0x18–0x1a are native joint kinds (`mu_jt_kind_supported`)
and render; any unsupported kind would be refused and counted. The three CreateEffect requests (0x199 for 142 and
144, 0x195 for 143) carry info word4, which the existing effect hook cannot pass, and are not native effect
kinds: they are **refused and counted** in `draw_unsupported`. No shared particle/effect/joint hook source changed.

Production host `native/tests/worlds_r2_host.c` creates authored ten-object populations in all three worlds through
`mu_objects_start` with a thirteen-bone model whose bones 5 and 9 are named E002 and E005, and runs 200 steps plus
the visual pass per world: create flags/ranges/HiddenMesh/z, one type-160 light per step at the right x/y with
range 2 and colour ratios, type-72 bone sprites every frame and their counted refusal with eleven bones, the
one-time twenty-particle burst and HiddenMesh of 115, Kardamahal's four lights per step (113, both named bones of
115 with range 4, 128), its 0x5a6/0x5a9 sounds every step, counted effect refusals, and Swamp's type-183 light,
rendered joints with the object's scale and the object-light writes. Portable tests check public dispatch,
the 115 no-model path (no rand), visual requests/writes with and without bones and that zero/one/full log
capacity leaves state and RNG unchanged.

## Saved-population regression and fidelity

Method of [captures 2](client-world-captures-2.md): `scripts/fidelity_tour.py run` at each arrival tile,
1722 × 1048, 25 steps, the DATA-ACQ-002 live object/globals/light/PNG captures and plaintexts, installed assets.
"Before" is this branch's base `5fa43cd`; "after" is this lane. The before run reproduces the captures-2 numbers
(image 13.480, 10.912, 12.755).

| Capture | Static field differences, whole map (near hero) | Drawn | Object lights / particles | Frame light near hero | Image mean \|Δ\| / > 24 |
|---|---|---|---|---|---|
| Twisted Karutan 142 | after-character 1,345 (100) → 0; range 5,047 (215) and velocity 123 (3) unchanged | 587 → 587 | 0 / 0 → 72 / 8 | 0.0058 → 0.0000 | 13.480 / 0.1712 → 13.480 / 0.1712 |
| Kardamahal 143 | range 286 (9) → 0; after-character 176 (13) → 0; velocity 88 (0) unchanged | 570 → 570 | 0 → 120 lights | 0.0012 → 0.0001 | 10.912 / 0.0917 → 10.911 / 0.0917 |
| Swamp of Destruction 144 | range 5,767 (85) → 0; after-character 902 (14) → 0; velocity 1,563 (40) unchanged | 244 → 260 | 0 → 72 lights | 0.0316 → 0.0088 | 12.755 / 0.0237 → 12.376 / 0.0230 |

**Verified against live captures:** 8,476 static field differences go to zero (all after-character differences
of the three captures and all range differences of 143 and 144); zero missing/extra objects; primary light
stays exactly equal; camera unchanged. The near-hero frame light improves in all three (142 and 143 now within
1e-4 of the live grid); whole-map frame-light mean |Δ| moves 0.5206 → 0.5205, 0.5128 → 0.5127, 0.6324 → 0.6322.

**Remaining, reported as measured:** Twisted Karutan's 5,047 range differences (live −800 for types such as 17,
18, 62, 141; native the default −30) are not written by these three slots nor by the invisible-move slot
`0x00e673b4` (static: no `+0xc0` store in any of them); their writer is unresolved. The velocity differences
(142: types 12/107; 143: 88 objects; 144: 1,563, live 0.3/0.07 against the generic 0.16) are not written by
these slots either; they come from the generic move or the default hook chain (inference). Light colours/phases
are one RNG/clock frame and differ from the captured frame. Swamp's image improves (12.755 → 12.376; the −300
range draws sixteen more objects at the frame edges, visually confirmed); 142/143 images are unchanged at three
decimals.

**Existing scenes:** base and lane binaries give identical outputs for the October 22 fourteen-view tour
(**28/28 PNG, 14/14 OBJECT, 14/14 light**; installed assets of the free-runtime prefix) and for the other 29
DATA-ACQ-002 captures (**58/58 PNG, 29/29 OBJECT, 29/29 light**).

## Follow-ups and limits

| Request | Status |
|---|---|
| CreateEffect 0x199 (142 type 196, 144 type 185) and 0x195 (143 type 161) with info word4 | Refused and counted; need effect kinds and a word4-carrying hook (RENDER-EFFECTS) |
| Kardamahal 115 named-bone lights | Native poses with the object's own origin; the client's model BodyOrigin is the last rendered instance (inference) |
| 142 range −800 writer; velocity differences in 142–144 | Not in these slots; unresolved |
| Custom render (142 `0x00e677a9`, 143 `0x00e0f4bc`, 144 `0x00e46e94`), after render (`0x00e68c6a`, `0x00e118fd`, `0x00e48f1c`), invisible move (`0x00e673b4`, `0x00e0e539`, `0x00e46a9f`) | Outside the primary count; still missing |
| CreateObject/MoveObject/RenderObjectVisual default hook chain around the class slot | Not modelled for these worlds |

Each capture is one arrival frame: no particle/effect pools, RNG phase or emitter windows. No new live read
was taken.

Reproduce with `scripts/run_validators.py --private --only validate_worlds_r2`, `scripts/world_handler_coverage.py`,
`reconstructed/objects/test_worlds_r2.py`, `native/tests/test_native_worlds_r2.py` and the tour above. Checks and
gate are in the [handoff](../handoffs/RENDER-WORLDS-R2.md).
