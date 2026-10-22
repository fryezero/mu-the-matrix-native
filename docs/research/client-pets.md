# The pet process: Demon, Spirit of Guardian, Rudolph, Panda, Unicorn, Skeleton (NATIVE-HELPERS-002)

NATIVE-HELPERS-001 ([client-helpers.md](client-helpers.md)) found four helper systems and left the third open: a
data-driven pet process behind the getter `0x00b990b0`, which ChangeCharacterExt and the inventory call for the pets of
group 13 that are neither the angel, the imp nor a mount. This finding reconstructs it: the pet table in
`Data\Local\petdata.bmd`, the pet object's creation, its two move types, its render and the per-pet visuals. It runs
in the native world for the hero (a labelled demo option) and for the demo players.

Labels:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case
  (`scripts/validate_pets.py`);
- **static**: a reading of the decoded instructions that was not executed;
- **demo**: native inputs or choices that stand in for the server or the inventory.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

| Routine (names are ours) | Range | SHA-256 (first 16) |
|---|---|---|
| petdata loader | `0x00eb0a7d..0x00eb0c52` | `87a30019620ec446` |
| checksum / BuxConvert | `0x00976895..0x0097694a` / `0x00976855..0x00976895` | `28a459883c3e577c` / `8d9eb0f5f201e5d8` |
| info map / lookup | `0x00eb0c52..0x00eb0cdb` / `0x00eb0cdb..0x00eb0d30` | `d11fa0852b5412f4` / `fee9c0f20ff23777` |
| CreatePet / DeletePet | `0x00eb0e78..0x00eb1015` / `0x00eb1015..0x00eb1203` | `57086b6f058a1e44` / `12c11544e36c8151` |
| UpdatePets / RenderPets | `0x00eb0d64..0x00eb0dee` / `0x00eb0dee..0x00eb0e78` | `d97e759b8cd46e02` / `02c88e37c391cf86` |
| PetObject::Create | `0x00eac071..0x00eac414` | `6de9c7dadf49dec8` |
| PetObject::Update / Render | `0x00eac414..0x00eac4e0` / `0x00eac4e0..0x00eac609` | `cf1956302b1998d8` / `0dccada4e2b67f89` |
| zen search / interval | `0x00eac65a..0x00eac81e` / `0x00eac81e..0x00eac84d` | `21a63bb6085eff00` / `a4ac5c9c50e3f2e5` |
| model tick / move | `0x00eac84d..0x00eac902` / `0x00eac902..0x00eaeacf` | `070760b937d2560d` / `9526b0fb77fed81f` |
| pick-up sound / visuals | `0x00eaeacf..0x00eaeaf8` / `0x00eaeaf8..0x00eb0847` | `3d411a5c334f5bfe` / `b248aa519f268734` |

## Short answers

- **The process** (static). `0x00b990b0` lazily constructs a 0x614-byte object (`0x00eb0990`): the pet table
  (32 records of 0x30 bytes at `+4`), a `std::map` of live pets at `+0x604` keyed by `c->key * 10000 + item code`, and
  an info map at `+0x60c` (item code → record). The frame loop calls UpdatePets `0x00eb0d64` in the logic tick and
  RenderPets `0x00eb0dee` in the render scene; both walk the live map in key order.
- **petdata.bmd** (verified). `Data\Local\petdata.bmd` holds 0x600 bytes of records and a dword checksum
  (`0x00976895`, key 0x3bb2: start `key << 9`; per dword XOR or add by parity, every 16 bytes fold
  `(key + sum) >> ((i/4) % 8 + 1)`). Each record is XOR-ed with the three-byte BuxCode `fc cf ab` (`0x01cf0448`,
  outside the captured section; declared with these bytes, which decode the installed file into the pet item
  indices). A missing or corrupted file shows a message box and leaves the table zero. Record: `+4` item index,
  `+0xa` the hero's equipment slot the collector checks (8), `+0xb` move type, `+0xc` range, `+0x10` follow flag,
  `+0x14` scale, `+0x18` BlendMesh, `+0x1c` five play speeds (by pet state, `0x00eb08c2`). The installed file has
  eight records: Demon `0x1a40` and Spirit of Guardian `0x1a41` (move type 0); Rudolph `0x1a43`, Panda `0x1a50`,
  Unicorn `0x1a6a`, Skeleton `0x1a7b`, PC Panda `0x1bd5`, PC Skeleton `0x1bd6` (move type 1).
- **Models.** CreatePet's callers pass the model `0x24e6 + item index` (ChangeCharacterExt's extended pet codes
  `e[0xf] & 0xe0`: 0x20 Demon, 0x40 Spirit, 0x60 Skeleton, 0x80 Rudolph, NATIVE-PLAYERS-001). Item.bmd names the files:
  `demon.bmd`, `maria.bmd`, `xmas_deer.bmd`, `pandapet.bmd`, `pet_unicorn.bmd`, `skeletonpet.bmd` (the PC copies share
  the Panda and Skeleton files); their textures are in `Data\Item\texture\`. The render registry `0x01d1e010` has
  plain RenderBody functors for the Demon (`0x00a10c6d`) and the Spirit (`0x00a10cd0`).
- **Create** (verified). A PetObject (0x50 bytes) gets a 0x3d8-byte OBJECT (operator new + the OBJECT constructor; an
  existing live OBJECT refuses): GetTickCount at `+0x10`, owner `+4`, item `+0xc`, type, live, lighting 1, owner object,
  subtype, `+0x68` −1, BlendMesh then the record's, scale 0.7 then the record's, LifeTime 30, alpha 0 → 1, position =
  the owner's (the caller's), angle = the owner's, light (3, 3, 3), frames 0, speed 0.5; model `0x2561` (the Skeleton)
  sits 60 × owner scale further in y.
- **Update** (verified). Nothing without an OBJECT or owner; in scene 6 an owner that is dead or not of kind 1 kills
  the pet's OBJECT. Else FadeAlpha, the model tick with the speed of the previous step, the move with
  `elapsed = GetTickCount − created`, and PlayBuffer(0x1f) while the state is 2.
- **Move type 0, flying** (verified; Demon, Spirit). Speed = record speed[state]. z = owner z + 230 × owner scale.
  With `d²` the squared xy distance to the owner and `r` the range: `d² ≥ r⁴` puts the pet on the owner, 200 above it,
  with the owner's angle; else `d² ≥ r²` turns it toward the owner by 10°. It moves by its last direction (AngleMatrix,
  VectorRotate) and the new direction is (0, −ln(d²) × 1.8, 0) when `d² > r²`, else 0.
- **Move type 1, the collector** (verified; Rudolph, Panda, Unicorn, Skeleton). For the hero's pet: the hero's
  equipment entry of the record's slot must hold an item (`+0x10 ≥ 0`), its bytes `+0x92` and `+0x93` both 1 mean
  state 4 (follow only); else the zen search `0x00eac65a` takes the first visible zen (type `0x1c0f`) of the 1000
  ground items within 300 of the owner and state 0 becomes 1. Other owners' pets are always in state 4. Angles
  a1 = (elapsed % 4000) × 0.00157, a2 = (elapsed % 2000) × 0.00314. Height: owner z + 20 (Unicorn + 200 × scale,
  Skeleton + 50 × scale). Farther than 900 from the owner it jumps to owner + 50 (sin a1, cos a1) and resets to state 0.
  - state 0 / 4: follow the owner (follow flag) or circle it at 50 (a1); speed ln(d) × 2.3 beyond the range (50 when
    circling inside it); a range ≤ 80 turns 8° per step;
  - state 1: fly to the zen + 50 (sin a2, cos a2), turning 20°, speed ln(d) × 2.5 beyond 20; arrived (speed 0) or
    after 100 s → state 2;
  - state 2: turn 10° toward the zen; the target gone (or not zen, or the owner 300 away, or 3 s) → state 3; every
    second it sends the pick-up request (0xC1 packet with the item index, global `0x01cf1028` while one is pending) and
    forgets the target. The type test after that reads ground item −1: memory before the array (an input, 0 natively);
  - state 3: return to the owner + 50 (sin a1, cos a1), then state 0 once arrived or after 3 s.
- **Render** (verified). Only when the owner's `0x0129de01` slot is −1: TestFrustrum2D(x/100, y/100, −20) into `+0xb`,
  RenderObject(o, 0, 0, buff 0x12 ? 10 : 0, −1, −1), then the visuals with the elapsed time:
  - Demon: light (0.7k, 0.5k, 0.6k), k = sin((t % 25000) × 0.001256) + 0.4; at nine bones a lightmarks `0x8099` and a
    Flare `0x7f78` sprite, five Clud64 `0x7ffd` particles (subtype 0xb), a firehik03 `0x8085` particle and two more
    Flares;
  - Spirit of Guardian: poses itself, lightmarks sprites at bone 3, the effect `0x460` (subtype 4, scale 0.3) under
    bone 5, and eleven bone sprites (lightmarks, flare01, Flares pulsing with two sine phases);
  - Rudolph: a Shiny01 `0x7f66` particle (subtype 7) above it, the effect `0x3fa` in state 3, flareRed `0x7fe0` and
    flare01 sprites at bone 10 (larger while collecting), flare01 and Shiny02 at five bones;
  - Panda (and PC Panda): Impack01 `0x7efa` (subtype 1) on `rand % 3 == 0` at bone 7, two flare01 sprites at bone 4;
  - Skeleton (and PC Skeleton): eyes (lightning2 `0x7f37`) and flare01 at six bones from the model-space pose scaled
    by the object scale, and while its owner is not in the actions 1..0x31, 0x133..0x141, 0x148..0x185 one or two
    firehik_mono particles (`0x8086` / `0x8087` / `0x8089`, owner = the pet) and a Hole `0x8003` sprite;
  - Unicorn: none.
- **Delete** (static). DeletePet(c, item) finds the key; item −1 deletes the first of the owner's pets.
  ChangeCharacterExt passes the former **slot type** (`0x24e6 + w`), not the item code, so it only matches through −1
  (an empty slot): a remote player who switches pets keeps the former pet until its slot is emptied.

## Routines

| Routine | Address | Status |
|---|---|---|
| loader, checksum, BuxConvert | `0x00eb0a7d`, `0x00976895`, `0x00976855` | verified |
| info map, lookup, CreatePet, DeletePet, UpdatePets, RenderPets | `0x00eb0c52`, `0x00eb0cdb`, `0x00eb0e78`, `0x00eb1015`, `0x00eb0d64`, `0x00eb0dee` | static (std::map) |
| Create | `0x00eac071` | verified |
| Update, model tick, move, zen search, interval, pick-up sound | `0x00eac414`, `0x00eac84d`, `0x00eac902`, `0x00eac65a`, `0x00eac81e`, `0x00eaeacf` | verified |
| Render, visuals | `0x00eac4e0`, `0x00eaeaf8` | verified |

## Validation

`scripts/validate_pets.py` runs the routines in Unicorn (`scripts/actor_machine.py`: declared regions with a
defined-byte mask; every undefined or undeclared access stops a case) and `libclient_pets` through ctypes with Python
host callbacks giving the same answers as the client-side stubs. Compared after every step: the rand() state and count,
the pet's fields `+0x04..+0x40`, the modelled OBJECT bytes, the pending pick-up global and the ordered host-call log.
Client code: everything reached except rand(), GetTickCount / timeGetTime (scripted clocks), TestFrustrum2D, the model
container, the animation tick, RenderObject, the pose builder, CreateSprite / CreateParticle / CreateEffect, the buff
lookup, `0x0129de01`, the pet list helpers, PlayBuffer, the packet builder and the loader's file / CRT helpers.
FadeAlpha, CreateAngle, TurnAngle2, AngleMatrix, VectorRotate, TransformPosition, `0x012b6d2a` and the CRT
sin / cos / sqrt / log (identified by execution: `0x009681bd`, `0x009fa223`, `0x00961a07`, `0x00ad320c` = ln) run as
client code.

Private run (`--cases 1000 --negative 60 --mutations`, about five minutes), report
`evidence/native-pets/report-02.json`:

| Section | Cases | Result |
|---|---|---|
| petdata loader (installed file, 39 valid / 21 corrupted synthetic files, missing) | 62 | 0 mismatches (installed: 8 records) |
| sessions (Create, then 10..60 updates / renders with moving owners, zen on the ground, advancing clocks; all pets, both move types, the five collector states, fresh / reused / live OBJECTs) | 1,000 sessions, 28,280 steps, 45,962 host calls | 0 mismatches, 28/28 branch probes |
| negative controls (range, scene, zen type) | 3 | 3 detected |
| planted mistakes (`-DMU_PET_MUTATION=1..6`) | 6 | 6 detected |

Portable: `reconstructed/pets/test_pets.py` (7 worked examples) and `native/tests/test_native_pets.py` (mu-walk on the
synthetic world with synthetic pet models and a synthetic petdata.bmd; one private Lorencia case).

## Native integration

- `native/core/mu_world_pets` runs inside the helpers module (owners: 0 the hero, 1 + i the demo players; the models
  through the helpers' model table, which now also tries `Data/Item/texture/`): the installed petdata.bmd (DEMO
  records when it is absent), the hero's pet from `--helper demon|spirit|rudolph|panda|unicorn|skeleton` (DEMO: the
  client creates it from the inventory), the players' pets from ChangeCharacterExt's recorded CreatePet / DeletePet
  calls (`pet=demon|spirit|skeleton|rudolph|panda` in the players file), a 40 ms clock for GetTickCount /
  timeGetTime, UpdatePets in the logic step, RenderPets in the helpers' draw (RenderObject through the helpers' body
  draw, the pose builder on the native model, sprites / particles / effects through NATIVE-PARTICLE-001's module).
- The app's "Your helper (demo)" picker offers the six pets.

Renders stay local under `~/Documents/mu-mac-tools/native/renders/helpers2/pets/` (one folder per pet, `sheet.png`,
`players/`).

## Limits

- The ground items are not offered to the collectors (DEMO), so they never pick up zen natively; the pick-up request
  would be a network packet.
- The pets' sprite bitmaps lightmarks `0x8099`, Flare `0x7f78`, flareRed `0x7fe0`, Hole `0x8003` and the particle kinds
  Clud64 `0x7ffd`, firehik03 `0x8085`, Impack01 `0x7efa` / 1, Shiny01 `0x7f66` / 7, firehik_mono `0x8086..0x8089` and the
  effects `0x460` / `0x3fa` are created but not drawn until the particle module ports them.
- The rand() of the visuals is the module's own (the client shares one).
- The Unicorn has no extended code in ChangeCharacterExt's switch, so remote players never show it.
- The Dark Raven and the Muun pets are separate systems (not this process).
