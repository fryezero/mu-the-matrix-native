# Aquila's Temple, Debenter, Boss Battle and world 115 primary handlers

RENDER-WORLDS-S, 2026-11-06. Reconstructs the create (+2c), move (+30) and visual (+34) slots of Aquila's Temple
(world 145) and Debenter (world 95), the three return-false slots of Boss Battle (world 139) and world 115's
create/move (the BaseMap defaults; its visual `0x00d5cc9b` was already verified by RENDER-WORLDS-N). Coverage on
base `5a91b98d` advances from **109/144 to 120/144 primary methods and from 37/48 to 40/48 classes** (0
static-only, 24 missing). The milestone brief quoted R2's 85/144 and 29/48; Q, R, P2, Q2 and later lanes had
already raised the count to 109/144 when this lane started, so "the 19 remaining classes" were 11 classes with no
primary method plus world 115's two default slots.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from decoded
instructions only; **inference** = neither. None of these worlds has a live arrival capture; nothing here is a
fidelity claim beyond the instruction comparison.

## Remaining classes, ranked by how a player reaches them

Map names come from the local map-name table (`0x016baaa6`, NATIVE-LANG-001 plaintext; inference for the
class-to-map pairing). Reachability is the DATA-ACQ-002 Warps window (live, 2026-10-28) and the local gate table.
Sizes are the half-open method ranges (bytes) on capture09.

| Rank | Class (worlds) | Map | How a player gets there | Create | Move | Visual | Status |
|---:|---|---|---|---:|---:|---:|---|
| 1 | 145 | Aquila's Temple | Warps row "Aquila's Temple", total level 1650 (gate 718) | 90 | 1,427 | 474 | **done here** |
| 2 | 95 | Debenter | field map, no Warps row on this server; in-map gates 436/437 (level 300) | 726 | 591 | 5,860 | **done here** |
| 3 | 110 | Nars | field map, no Warps row on this server | 1,400 | 1,151 | 8,395 | S2 |
| 4 | 92 (92, 96, 101, 111) | Arca War on Acheron/Debenter/Uruk/Nars | guild event | 172 | 87 | 430 | S2 (class state) |
| 5 | 69, 70, 71, 72 | Imperial Guardian (Varka) | event instance | 395–426 | 662–724 | 5,987–6,785 | later |
| 6 | 114 | Event square (not world 79's Event Square) | event | 211 | 1,209 | 1,973 | later |
| 7 | 139 | Boss Battle | instance | 13 | 13 | 13 | **done here** |
| 8 | 121 | Test Area | not offered | 601 | 127 | 848 | later |
| 9 | 115 | (no map name) | not offered | 13 | 13 | (13, verified) | **done here** |

The Arca class (`0x00d7bd7d`..) holds its base world in `this+0x1c` and forwards to that world's class slot through
the factory (`0x00ea594b`/`0x00ea4679`), with its own case for type 0x59b gated by `this+0x30` (static; a server
state). Debenter's predicate `0x00dbd14d` accepts world 96 for that reason.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, both pin-checked.
Restored Linux/Wine x86 instructions, not native Windows evidence. No client was started.

| Family | Original half-open range | Body SHA-256 (prefix) | Cases |
|---|---|---|---:|
| Aquila create | `0x00d75a6c..0x00d75ac6` | `924a868b7c1c8f94` | 1,000 |
| Aquila move | `0x00d75ac6..0x00d76059` | `d1de361747fdf608` | 1,000 |
| Aquila visual | `0x00d77b3e..0x00d77d18` | `b76a0678d724de7e` | 1,000 |
| Debenter create (predicate `0x00dbd14d`, worlds 95/96) | `0x00dbd210..0x00dbd4e6` | `e1a6ab614dfed762` | 1,000 |
| Debenter move | `0x00dbd4e6..0x00dbd735` | `770e7ebd9b9b7020` | 1,000 |
| Debenter visual (with its 8-entry jump table) | `0x00dbd735..0x00dbee19` | `b033e97d5ef5c930` | 1,000 |
| Boss Battle create / move | `0x00d9c180..0x00d9c18d` / `0x00d9c18d..0x00d9c19a` | `8fe906e7160a7e38` (both) | 1,000 each |
| Boss Battle visual | `0x00d9c1a7..0x00d9c1b4` | `ca989ca057a61837` | 1,000 |
| World 115 create / move (BaseMap defaults) | `0x00d5cb99..0x00d5cba6` / `0x00d5cc16..0x00d5cc23` | `8fe906e7160a7e38` (both) | 1,000 each |

Each move range ends at the class's custom-render slot, each visual at its after-render slot (Debenter's at its
custom-render slot `0x00dbee19`, after the jump table).

## Verified methods

**Aquila's Temple** has no world predicate in any slot. *Create*: null object → false; types 51, 99, 120, 143, 148
get range −150; true. *Move* (no null test: the original dereferences the object): after-character `+0x0a` =
`0.9 > alpha(+0xdc)` (false for NaN) for every type; type 152 then sets it to 1. Type 90: `s = (rand % 4 + 3) ·
0.1 · 0.4 + 0.4`, AddTerrainLight at the object's x/y, RGB `(0.1s, 0.41s, 0.8s)`, range 2. Types 136–140 and 142:
`s = (rand % 2 + 4) / 5`, `s = (1 − 0.6) · s + 0.6`, a light at **`+0x188` x/y** with RGB 136 `(s, 0.22s, 0.1s)`,
137 `(0.1s, 0.41s, 0.8s)`, 138 `(0.12s, 0.58s, 0.32s)`, 139 `(0.74s, 0.17s, 0.62s)`, 140 `(1.2s, 0.84s, 0.53s)`
(range 2) and 142 `(s, s, 0.6s)` (range 3). True for every type. *Visual*: null object or model → false; types
136–140 and 142 call `0x0129fd4f(6)` twice (bone 6 as a column-major 4×4) and store its `[12]`, `[13]` (the bone's
x/y) in `+0x188`, `+0x18c`; true. So each step's light uses the bone position of the previous frame's visual.

**Debenter** (all three slots test the world, 95 or 96, and nothing else: no null test of object or model).
*Create* switches on **OBJECT `+0x60`, not the type**: 9 looks the type's model up without a test, sets model
`+0x78` (BodyOrigin) to the position, runs Animation(bones, frame, prior frame, prior action, angle, head angle,
0, 0), TransformPosition with Translate = 1 of bones 23 and 22 (zero local) into `+0x188` and `+0x194`, then two
CreateJoint 0x7fd6 from the position to itself, subtypes 0x3c and 0x3d, owner the object, scale 40; 56–67 get
HiddenMesh −2. True. *Move*: types 9 and 11 copy their action record (`0x00eaaa44`, no test) and, when the frame
reached `keys − PlaySpeed`, either start a swing (`+0x64 ≤ 0`: `+0x64 = rand % 3 + 4`, SetAction 1) or rest
(SetAction 0, `+0x64 − 1`); type 50 lights its x/y with `s = |sin((float)(T · 0.001))| · 0.4 + 0.3`, RGB
`(0.2s, 0.3s, 0·s)`, range 2. *Visual*:

| Type | Requests |
|---|---|
| 9 | bones 23/22 → `+0x188`/`+0x194`; on `rand % 4 == 0` bone 8 + (0, 0, 20) jittered by `0x00d750fa` (±20 per axis, three rands), particles 0x7f5a sub 0x52 (0.5, 0.9, 0.5) and 0x7f5a sub 0xd with the object light, scale ×2, owned; at each stored point − (0, 0, 10): 0x8089 sub 9 (0.05, 0.6, 0.2) ×0.8 and white ×0.5 |
| 27, 31 | bone 1; `s = abs'(sin((float)(T · 0.0008))) · 0.6 + 0.1`; sprites 0x7f6b scale 0.4 (0.9, 0.1, 0.1) and scale `scale · 0.3 · s` (s, s, s) |
| 11 | `s = sin((float)(trunc(T) % 3000) · 0.0010466667) · 0.1`; bone 27 + (0, 0, 20); 1 in 10 the 0x7f5a pair (sub 0x53 ×0.5, sub 0xd ×2 owned); 1 in 7 0x7efa sub 2 scale 0.25 (0.6, 1, 1); sprite 0x7ef7 scale `1.5 + s` (0.2, 0.65, 0.65); in action 1 0x7f26 sub 0xe scale 0.06 (0.3, 0.95, 0.95) |
| 21 | `s = abs'(sin((float)(T · 0.0012))) · 0.5 + 0.3`, light (0.05s, 0.3s, 0.6s); sprites 0x8155 scale 1 at bones 2 and 3; at bone 4 0x7f5a sub 0x51, scale `(float)(rand % 5 · 0.03 + 0.2)` (double) |
| 56 | 1 in 10: position + (0, 0, 50), `s = (rand % 4 + 3) · 0.1`, 0x7f5a sub 0x21 (s, 0.6s, 0.2s) |
| 57 | 1 in 6: owned 0x7f89 sub 9 (0.02, 0.03, 0.02) |
| 58, 59, 60 | 1 in 5: `s = rand % 10 · 0.004 + 0.01` (59: + 0.02); owned 0x7f89 sub 0x18 with (0.2109375, 0.69140625, 0.5859375)·s (59: (0.29296875, 0.05859375, 0.05859375)·s); 60 adds (0.86328125, 0.47265625, 0.78515625)·s |
| 61, 66 | 1 in 5: `s = rand % 10 · 0.002 + 0.01`; owned 0x7f89 sub 0x18, 61 (1.2s ×3), 66 (0.12s, 0.12s, 0.6s) |
| 62 | `rand % 35 == 5`: `s = rand % 10 · 0.05 + 0.03`; owned 0x7dea sub 0 (s, s, s) |
| 63 | always 0x8089 sub 9 (0.05, 0.3, 0.5) and ×0.5 (0.39, 0.65, 0.39) |
| 64 | 1 in 10: 0x7f5a sub 0x53 (0.5, 0.9, 0.5) ×0.5 |
| 65 | `timeGetTime % 1024` drawn first, then `rand % 5 == 1` and phase < 30: CreateEffect 0x199 sub 0, owner the object, light 0.1, word4 `(uint16_t)(int)scale` |
| 67 | 1 in 2: owned `0x807e + rand % 3` sub 8 (0.4 ×3) ×0.6 |

True after the world test. Types 11 and 21 pass an **uninitialized stack vector** as TransformPosition's local
(static); the C passes zero and the harness substitutes zero on the original side.

**Boss Battle** create/move/visual and world 115's create/move are `xor al, al` behind a frame: false, no request,
no write.

The eleven families compare AL, all 984 OBJECT bytes, the model's BodyOrigin and action table, ordered recorded
calls with their constant arguments asserted (AddTerrainLight with the frame light; CreateParticle owner/tail;
CreateSprite with its `{1, 1, 1.0}` descriptor; CreateJoint with its fixed tail; CreateEffect with `-1, 0, word4, 0,
0.0, -1, 0, 0`; TransformPosition bone/local/Translate and the model ECX; Animation's eight arguments; the bone
matrix's bone and ECX) and the final MSVC RNG. Executed as original code: the predicates, SetAction `0x012affa4`,
the action lookup, the jitter helper `0x00d750fa`, the CRT sine wrapper, fabs, `0x0184f8ff`, the vector and matrix
helpers, the sprite descriptor and the SEH frames. Recording boundaries: rand, the services above, the model
container, Animation, TransformPosition, `0x0129fd4f` and timeGetTime (a code hook at the import call). Samples
cover every type −1..159 (145), −1..79 (95), −1..39 (139/115) plus signed extremes and random types, the sibling
worlds 0, 94–97, 113–116, 138–140, 144, 145, `+0x60` keys around 9 and 56–67, alpha around 0.9 and NaN, scales
including −0, NaN and 70000 (word4), action tables of 0–8 records, WorldTime including ±0, 2^31-scale values and
NaN, timeGetTime phases 0/29/30/1023, and seeds that open each 1-in-N branch in about 60 % of its directed cases.
Not sampled (the original faults): null objects for Aquila's move and all Debenter slots, Debenter visual without a
model, Debenter create key 9 without a model, Debenter move of types 9/11 without an action record.

**11,000 cases, zero mismatches or stops; 61/61 separately compiled planted mistakes are caught** (1 to 1,000 cases
each; weakest: the effect phase bound `< 31`, 1; the `% 1024` modulus, 2; the 1-in-7 gate, 5). A first-draft
mutant that removed the Aquila visual's model test did not compile (unused parameter) and was replaced by a value
mutant.

## Native consumption

- `mu_obj_create`/`mu_obj_move` dispatch worlds 145, 139 and 115 after the generic part (one block each in
  `object_render.c`). Aquila's move writes the after-character flag every step and logs its lights with explicit
  x/y; the AddTerrainLight consumer is unchanged.
- Debenter runs on the RENDER-WORLDS-Q inputs: `mu_worlds_q_owns` now includes 95 and the Q dispatch calls the
  three Debenter methods (`worlds_q.c`; world 96 stays with the Arca class). The runtime's existing Q paths give it
  the type's action table, SetAction, the posed bones and the world clock. Three refusals are counted, never
  approximated: create key 9 (`create_unsupported`; it needs the model posed at creation), move types 9/11 without an
  action record (`move_unsupported`), visual bone types without enough posed bones (`draw_unsupported`,
  `mu_debenter_visual_bones`). The 0x199 word4 effect goes to the existing owned-effect consumer and is refused
  and counted when the host installs no word4 hook. The create's 0x7fd6 joints only occur in the refused key-9 path.
- Native construction leaves `+0x60` at 0, so no Debenter create case applies to installed placements
  (inference: the client constructor also clears it, `0x0129e792` static, not read live).
- The visual pass adds 145 to the primary-visual worlds: one outer flicker rand, then the class visual with bone 6
  of the posed model transposed as `0x0129fd4f` does for map objects in a sector (their `+0x350/+0x354` links are
  set, so no extra object matrix; the native pose already holds origin and scale). Without bone 6 the four bone
  types are counted in `draw_unsupported` and `+0x188` keeps its value. Lights before the first visual use the
  constructor's `+0x188` (zero natively).
- 139 and 115 are not added to the primary-visual worlds: their slots request nothing, and their visual pass is
  unchanged.
- No shared particle/effect/joint hook source changed.

The production host `native/tests/worlds_s_host.c` runs ten-object authored populations of 145, 95, 139 and 115
through `mu_objects_start`, 200 steps and the visual pass with a 28-bone, two-action model: Aquila ranges, five
lights per step (type 90 at its x/y, the bone types at bone 6's x/y once the visual has run), type 152's flag, the
stored bone point, and four counted refusals with six bones; Debenter's type-50 light, swings of type 9, seven
sprites and at least six particles per frame, the counted 0x199 refusals, the stored bone points, and refusals
with five bones; Boss Battle/115 steps with no light and no unsupported count. Portable tests check public
dispatch, the Aquila visual with and without a matrix, the Debenter Q dispatch (key-9 refusal, HiddenMesh, swing,
type-50 light, refused bone types) and that zero/one/full log capacity leaves state and RNG unchanged.

## Smoke check and regression

The installed client has `World146/EncTerrain146.obj`, `World96/EncTerrain96.obj` and
`World140/EncTerrain140.obj` (no object file for world 115), but the installed files do not decode with the
client's loader instructions (`mu_objects.h` BOUNDARY); placements come only from live-read plaintexts, and none
exists for these worlds. Headless `mu-world` arrivals at 145 (122,65; gate 718), 95 (19,104; gate 436) and 139
(128,111; gate 681), 25 steps at 1722 × 1048: no crash, terrain and hero drawn, **zero objects** (no population
to create). The populated checks are therefore the production host above.

Byte identity, base `5a91b98d` against this lane at the default draw: the October 22 fourteen-view tour **28/28
PNG, 14/14 OBJECT, 14/14 light identical**; all 32 DATA-ACQ-002 captures **64/64 frame PNG (plus 64/64 comparison
PNG), 32/32 OBJECT, 32/32 light identical**. No captured world's class changed; the Q dispatch change leaves
Acheron, Ferea, Swamp of Darkness and Kubera byte-identical.

## Follow-ups and limits

| Request | Status |
|---|---|
| Debenter create key 9 (pose at creation, bones 23/22, joints 0x7fd6 0x3c/0x3d) | Refused and counted; unreachable for installed placements while `+0x60` is 0 |
| Debenter 0x199 word4 effect (type 65) | Existing owned-effect consumer, else refused and counted |
| Debenter types 11/21 uninitialized TransformPosition local | Zero (inference); the client value depends on prior stack contents |
| Aquila `+0x188` before the first visual | Zero natively; the client constructor value is not read |
| Custom render / after render / invisible move of 145, 95, 139, 115 | Outside the primary count (145's custom/after: RENDER-WORLDS-AFTER3) |
| Nars (110), Arca War (92/96/101/111), Imperial Guardian (69–72), Event square (114), Test Area (121) | 24 primary methods still missing |
| Live population, RNG phase, image fidelity of 145/95/139/115 | No capture; Aquila needs level 1650, the others are not in the Warps window |

Reproduce with `scripts/run_validators.py --private --only validate_worlds_s`, `scripts/world_handler_coverage.py`,
`reconstructed/objects/test_worlds_s.py` and `native/tests/test_native_worlds_s.py`. Checks are in the
[handoff](../handoffs/RENDER-WORLDS-S.md).
