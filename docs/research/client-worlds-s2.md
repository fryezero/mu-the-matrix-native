# Nars and the Arca War class primary handlers

RENDER-WORLDS-S2, 2026-11-06. Reconstructs the create (+2c), move (+30) and visual (+34) slots of Nars (world 110,
class `0x01aaa95c`) and of the Arca War class `0x01aa6154` (worlds 92, 96, 101 and 111: Arca War on Acheron,
Debenter, Uruk Mountain and Nars). Coverage on base `83a21893` advances from **120/144 to 126/144 primary methods
and from 40/48 to 42/48 classes** (0 static-only, 18 missing). These are ranks 3 and 4 of RENDER-WORLDS-S's list
([client-worlds-s.md](client-worlds-s.md#remaining-classes-ranked-by-how-a-player-reaches-them)).

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from decoded
instructions only; **inference** = neither. Neither world has a live arrival capture; nothing here is a fidelity
claim beyond the instruction comparison.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, both pin-checked.
Restored Linux/Wine x86 instructions, not native Windows evidence. No client was started.

| Family | Original half-open range | Body SHA-256 (prefix) | Cases |
|---|---|---|---:|
| Nars create (predicate `0x00e2602d`, worlds 110/111; its 10-entry jump table) | `0x00e260f0..0x00e26668` | `f6a339005d4d16e8` | 1,000 |
| Nars move | `0x00e26668..0x00e26ae7` | `17f7379df15179de` | 1,000 |
| Nars visual, fire types 4/116/134/146 | `0x00e26ae7..0x00e28bb2` | `fa5460d3e8c2587d` | 1,000 |
| Nars visual, glow types 11/133/85/87 | same body | same | 1,000 |
| Nars visual, emit types 10/14/15/29/30/39/59/66/79 | same body | same | 1,000 |
| Nars visual, orbit types 25/26/32 | same body | same | 1,000 |
| Arca base world `0x00d7b225` (with the class-list predicate `0x00d806b0`) | `0x00d7b225..0x00d7b24b` | `38453f7dff30d5cd` | 1,000 |
| Arca create | `0x00d7bd7d..0x00d7be29` | `22a93e02531d3f49` | 1,000 |
| Arca move | `0x00d7be29..0x00d7be80` | `d4854f589f977df4` | 1,000 |
| Arca visual | `0x00d7be80..0x00d7c02e` | `51f3033d1d9df898` | 1,000 |

The Nars visual ends at its custom-render slot `0x00e28bb2`. It is split into four families by type, as R2 split
the Swamp of Destruction table: each family draws two thirds of its cases from its own types and one third from
every type −1..160, signed extremes, 0x59b, 0x88a and random values, so every family also covers the others' paths.

## Verified methods: Nars

All three slots test the world (110 or 111) and nothing else: no null test of the object or the visual's model.

*Create* switches on the type through a compare tree and a 10-entry jump table (types 19..28):

| Types | Writes |
|---|---|
| 0 | `+0xcc` = −2800, scale 17, angle z 340, range −30000 |
| 6 | range −200, after-character 1 |
| 11, 12, 28 | range −200 |
| 8, 9 | range −800 |
| 10, 14, 15, 25, 26, 29, 30, 32, 39, 59, 66, 79, 146 | HiddenMesh −2 |
| 16, 21–24, 27 | after-character 1 |
| 17, 34–38, 142, 150 | range −400, after-character 1 |
| 19, 60, 64, 154 | range −400 |
| 85, 87 | `+0x64` = rand % 10 · 300 (their phase) |
| 134 | the type's model (no test): `+0x78` = position, `+0x74` = scale, Animation(bones, frame, prior frame, prior action, angle, head angle, 0, 1), TransformPosition(bone 4, zero, `+0x110`, 0) |

True for every type. *Move*: types 1 and 2 look up their action record **with** a null test (unlike Debenter);
at the end of the action (`frame ≥ keys − PlaySpeed`), `+0x64 ≤ 0` restarts the rest (`+0x64 = rand % 3 + 5`,
SetAction 0), otherwise SetAction 1 and `+0x64 − 1`. Types 4, 116 and 146 light their own x/y and type 134 the
x/y of `+0x110`, with `s = rand % 5 · 0.04` and RGB `(s + 0.8, s + 0.3, s + 0.2)`, range 1 (134: range 2).
Type 77 scrolls `+0xb0` by −0.015. True for every type.

*Visual* (true for every type after the world test):

| Types | Requests |
|---|---|
| 4, 116 | `k = scale · 0.4 · (rand % 5 + 13) · 0.1` before the bone read; bone 7: CreateEffect 0x413 (light 1, sub 10, **owner 0**, word4 `(uint16_t)(int)k`, float 0) and sprite 0x7ef7 scale `2 · scale` (1, 0.2, 0) |
| 146 | the same at the object position (no bone) |
| 134 | the glow pair of 11, then the fire of 4 at bone 3 |
| 11, 133 | `s = abs'(sin((float)(T · 0.0008))) · 0.6 + 0.1`; at bones 1 and 2: sprites 0x7f6b scale 0.4 (0.2 + s, 0.1, 0.1) and scale `scale · 0.3 · s` (s, s, s) |
| 85 | `s = sin((float)(trunc(T) % 3000) · 0.0010466667) · 0.1`; bone 4; 1 in 7 0x7efa sub 2 scale 0.25 (0.6, 1, 1); sprite 0x7ef7 scale `1.5 + s` (0.2, 0.65, 0.65); while `sin(T · 0.001 + (float)+0x64) − 0.5 > 0`, 0x7f26 sub 0xe scale 0.06 (0.3, 0.95, 0.95) with angle **(0, 0, 1)** |
| 87 | for k = 0..5, bone `{5, 6, 7, 11, 14, 15}[k]` (the client's table is `{6, 5, 6, 7, 11, 14, 15}` read from entry 1): `s = abs'(sin((float)((double)((float)+0x64 + T) · 0.0002 · k))) · 0.4`; sprites 0x7f26 scale 2 (1.3s, 1.3s, 1.9s) and scale 1.5 (0.15 ×3) |
| 10 | 1 in 12: owned 0x822a sub 0 (0.05 ×3) |
| 14, 79 | 1 in 8: 0x7f5a sub 0x45 (14: (0.78, 0, 1); 79: (0.9, 0.5, 0.5)), then owned 0x7f5a sub 0x15 scale ×2 with the object light |
| 15, 29, 39, 59, 66 | 1 in 6: owned 0x7f89 sub 0x19 with (0.05, 0.02, 0.01), (0.01, 0.02, 0.05), (0.06, 0.05, 0), (0.01, 0.03, 0), (0.03, 0, 0.04) |
| 30 | 1 in 3: owned 0x7f5a sub 0x45 (0.9, 0.2, 0.2) |
| 25, 26 | 1 in 5: `(0, rand % 100, 0)` rotated by AngleMatrix of `(0, 0, rand % 100)` (VectorRotate) plus the position; 25: 0x7fdd sub 3, 26: first sets the **object light** to (1, 0.5, 0.1), then 0x8184 sub 2; scale 1, object light, unowned |
| 32 | `s = (sin(T · 0.001) + 1) · 0.5 · 100`, `lo = 30 · ((int)x % 3 + 1)`, width 10 when `lo == 90`, else 40; when `lo ≤ s ≤ lo + width` (false for NaN), twenty owned 0x801b sub 7 (0.9, 0.2, 0.2) |

Type 25's and 26's `600` and `45` stores after the particle are dead (static). The 0x413 effect matches the
MU_R2_EFFECT layout; native requests go to the existing owned-effect consumer with owner −1.

## Verified methods: Arca War

The class keeps the worlds it is registered for in a vector at handler `+8` (92, 96, 101, 111; the predicate
`0x00d806b0` searches it). Slot `+0x20` (`0x00d7b65c`, world entry; static) sets `+0x1c` through `0x00d7b225`:
**world − 1 for a listed world, else −1**. So the base world is client state, not server state: Acheron (91),
Debenter (95), Uruk Mountain (100) and Nars (110). The class registry `0x00ea594b`/`0x00ea4679` returns that world's
handler, and the slot calls its vtable entry with the Arca world still current, so each base class runs its own
predicate on it (all four accept their Arca world: 91/92, 95/96, 100/101, 110/111).

The class's own types come from `0x00d7b373` of the world-92 class (`0x0095c652(92)` is a registry lookup and a
dynamic cast; the method ignores `this`): 0x88a..0x88e give 1..5, everything else 0. Type 0x59b is the other own
type.

- *Create*: not a listed world → false; `+0x1c == −1` → false; own type (0x88a..0x88e or 0x59b) → scale 0.85,
  true; otherwise the base class's create, true when its AL is non-zero.
- *Move*: not a listed world → false; otherwise the base class's move (no −1 test), true when its AL is non-zero.
- *Visual*: not a listed world → false; 0x59b → TransformPosition(bone 3, zero) then CreateEffect 0x413 at that
  point with the angle, light `+0x40 + 12 · stage`, subtype 10 when `stage < 4` else 11, owner 0 and float
  `scale · 1.0`, true; 0x88a..0x88e → true, nothing; otherwise the base class's visual (object, model).

`stage` is handler `+0x30`. Its writers `0x00d7ac66` and `0x00d7af0d` (static) take packet values: **server
state**. The port keeps it an explicit input (`mu_q_handler.arca_stage`) whose default is the constructor's 0
(`0x00d7a185` clears `+0x24..+0x3f`). The constructor's light table: stages 0 and 1 (1, 0.37, 0.66), 2 (0.58, 1,
0.86), 3 (0.08, 1, 0.86), 4 (0.6, 0.9, 0.95), 5 (0.88, 0.4, 0.86). The visual refuses (−1) a stage outside 0..5,
where the client would read past the six entries.

## Harness

The Nars families compare AL, all 984 OBJECT bytes, the model's `+0x74..+0x84` (scale and BodyOrigin, written
only by create type 134) and action table, ordered recorded calls with their constant arguments asserted
(AddTerrainLight with the frame light; CreateParticle owner/tail; CreateSprite with its `{1, 1, 1.0}`
descriptor; CreateEffect with `0, −1, 0, word4, 0, 0.0, −1, 0, 0`; Animation's eight arguments; TransformPosition
bone/local/Translate 0 and the model ECX) and the final MSVC RNG. Executed as original code: the predicate,
SetAction, the action lookup, the CRT sine wrapper, fabs, AngleMatrix, VectorRotate, the vector accessors and the
sprite descriptor. Samples cover every type −1..160 plus extremes and random types, worlds 0/92/109/110/111/112,
`+0x64` around 0 and multiples of 300, frames around the action end and NaN, scales including −0, NaN, 70000 and
1e6 (word4 overflow), positions with NaN/∞/3e9 x (type 32's `(int)x`), WorldTime including ±0, 2^31-scale values
and NaN, and seeds that open each 1-in-N branch in about 60 % of its directed cases. Recorded call counts at
1,000 cases: 12 creation poses, 230 move lights, 589 fire effects, 3,134 glow sprites, 1,180 orbit/band particles.

The Arca families run with a harness handler (the registered world vector, `+0x1c`, `+0x30` and the constructor's
light table) and a harness base handler whose vtable slots 0x2c/0x30/0x34 record the forward (slot, base world,
object, model) and return a sampled EAX (AL 0, 1, 0x80, 0xff or random under random high bytes). The C forward
callback returns the same AL. Samples: the four worlds and ten siblings, base = world − 1 in 75 % of cases,
otherwise −1, 0, the four bases or random values; stages 0..5; types 0x59b, 0x88a..0x88f, 0x59a/0x59c and every
type −1..160; model present or null for the non-0x59b visual. 511/800/569 forwards and 73 own effects at 1,000
cases each.

**10,000 cases, zero mismatches or stops; 72/72 separately compiled planted mistakes are caught** (1 to 1,000
cases each; weakest: type 85's rise threshold 0.4, 1; the stage-5 light, 8; the type-134 pose bone and
scale, the stage-3 subtype bound and light, 12). A first mutant (type 28 → 27 in the create) did not compile
(duplicate case) and was replaced by 28 → 31.

## Native consumption

- **Q inputs.** `mu_worlds_q_owns` now includes 110 (Nars) and 92, 96, 111 (Arca War on the Q classes). The Q
  dispatch (`worlds_q.c`) sends 92/96/111 to the Arca methods with a forward callback that runs Acheron's,
  Debenter's or Nars's slot with the Arca world; Acheron's visual runs without a model as its direct dispatch does,
  Debenter's and Nars's need one. `mu_worlds_q_visual_bones(world, type)` gives the runtime one bone bound for
  Acheron, Debenter, Nars and their Arca worlds (3 for 0x59b).
- **World 101** (Arca on Uruk Mountain) is outside the Q inputs: `object_render.c` gives create/move one block that
  forwards to `mu_uruk_create/move` with world 101, and the runtime's visual branch forwards to `mu_uruk_visual`
  (with the model, as world 100 does) and is in the primary-visual list.
- **Stage**: `mu_q_handler.arca_stage` (appended), 0 from the runtime's zeroed handler. No server state is read
  or invented.
- Refused and counted, never approximated: Nars create type 134 (`create_unsupported`: no model is posed at
  creation; `+0x110` keeps CreateObject's position, so its light sits at the object); Nars visual bone types
  without enough posed bones (`draw_unsupported`); Arca's 0x59b without a posed model. Arca's own types
  (0x59b, 0x88a..0x88e) are above the native 512-type model table, so natively they never have a model: their
  create scale applies, their 0x59b effect is always refused and counted.
- Effects use the existing consumers (Nars: owned-effect word4 hook with owner −1; Arca: the scaled CreateEffect
  hook). No shared particle, effect or joint hook source changed.

The production host `native/tests/worlds_s2_host.c` runs authored Nars populations on 110 and, through the
Arca class, on 111 (ten types, 200 steps): two flame lights per step at the right x/y and range, type 1's swings,
type 77's scroll, 19 sprites and two keyed effects per frame, particles, type 26's object light, three refusals
with five bones; a type-134 population (refused create, its light at the position); Arca's own types on all four
worlds (scale 0.85, one counted 0x59b refusal each); and forwarding on 96 (Debenter's type-50 light), 92
(Acheron's type-9 light) and 101 (Uruk's type-27 light and type-20 range). Portable tests check ownership, base
worlds, bone bounds, every create row, move lights, visual families, Arca own types and forwarding through all
four bases, the 0x59b effect per stage, and that zero/one/full log capacity leaves state and RNG unchanged.

## Smoke check and regression

The installed client has `World111/EncTerrain111.obj` (Nars), but installed object files do not decode with the
client's loader instructions and no live-read plaintext exists for Nars. Headless `mu-world --world 110 --tile
128,128`, 25 steps at 1722 × 1048: no crash, terrain and hero drawn, **zero objects**. World 111's own terrain
(`World112/EncTerrain112.map`) is not installed, so `mu-world` refuses that arrival before any object code runs.
The populated checks are the production host above.

Byte identity, base `83a21893` against this lane at the default draw: the October 22 fourteen-view tour **28/28
PNG, 14/14 OBJECT, 14/14 light identical**; all 32 DATA-ACQ-002 captures **64/64 frame PNG, 32/32 OBJECT, 32/32
light identical** (Acheron 91, the base of Arca 92, among them). No captured world's class changed.

## Next classes (static survey; not built)

Call counts from a linear scan of each slot up to its first return (static).

| Class | Slots (create / move / visual) | What a port needs |
|---|---|---|
| Imperial Guardian 69, 70, 71, 72 (four near-identical classes) | 113–124 / 157–176 / 1,600–1,792 instructions | The move calls the alpha step `0x012af883` and the animation tick `0x012b4dd3` itself (plus a per-class helper, `0x00dd38c5` and siblings), so the native generic move's tick must not run twice; the visuals each have ~20 CreateParticle, 7 CreateSprite, 4–6 TransformPosition, 2–3 **CreateJoint** (the existing joint consumer; no new hook), sine and AngleMatrix. The handler state `+0x14` (premove note in the runtime, an event stage) is server state: an input like Arca's stage. One C file with per-class tables; four validator families per slot |
| 114 (event square) | 57 / 344 / 530 | Create registers the object (`0x016d9f51`, the operable-object table already logged as MU_OBJ_CALL_REGISTER); the move poses the model (Animation + TransformPosition) and lights at bone points, as Kardamahal's deferred bone-light event does; the visual draws 6 particles and 4 sprites at bones |
| 121 (Test Area) | 181 / 37 / 244 | Create makes three CreateEffect calls at creation (a startup-effect path exists only for worlds 2/3/57/58); move is a sine through helper `0x00d5c7a9`; visual draws 8 particles. Not offered to players |

## Follow-ups and limits

| Request | Status |
|---|---|
| Nars create type 134 (pose at creation, bone 4 into `+0x110`) | Refused and counted; its move light uses the position |
| Nars visual bone types without posed bones | Refused and counted |
| Arca stage `+0x30` | Input, default 0; the packet handlers that set it are not ported (server state) |
| Arca own types 0x59b, 0x88a..0x88e | Above the native 512-type model table: scale applies, 0x59b's effect refused and counted |
| World 111 arrival | Terrain `World112` not installed; no native arrival |
| Custom render / after render / invisible move of 110 and the Arca class | Outside the primary count |
| Live population, RNG phase, image fidelity of 110 and the Arca worlds | No capture; Nars has no Warps row, Arca War is a guild event |

Reproduce with `scripts/run_validators.py --private --only validate_worlds_s2`, `scripts/world_handler_coverage.py`,
`reconstructed/objects/test_worlds_s2.py` and `native/tests/test_native_worlds_s2.py`. Checks are in the
[handoff](../handoffs/RENDER-WORLDS-S2.md).
