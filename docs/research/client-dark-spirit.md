# The Dark Raven (Dark Spirit) and the Muun tables (NATIVE-HELPERS-002)

This finding answers how the pinned client creates, moves and draws a Dark Lord's Dark Raven (item 13,5, "Dark
Spirit"): which byte makes it, how it follows its owner, why it becomes a small soul in a safe zone, and how its
model is drawn. It joins that to the native world for the hero (a labelled demo option) and for the demo players. A
static survey of the Muun pets' data tables closes the note.

Labels:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case
  (`scripts/validate_raven.py`);
- **static**: a reading of the decoded instructions that was not executed;
- **demo**: native inputs that stand in for the server or the inventory;
- **viewer choice**: native behaviour that is not a client reading.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

The validator refuses other inputs and records the SHA-256 (first 16 hex digits) of the 16 bodies it names.

## Short answers

- **Not a bug, not a PetProcess pet.** The raven is a third helper system: a 0x3688-byte C++ object (`CSPetSystem`-like,
  vtable `0x01a7fac8`) per character at `c + 0x31f0`, with its own CHARACTER at `+0xc` and its OBJECT at `+0x3260`.
  `DeleteBug`'s type list names the slot type `0x24eb`, but no bug is ever created for it.
- **The pet byte** (verified). `0x00c92bea(c, byte)`: 0 none (`c + 0x31f8 = -1`, delete), 1 / 2 / 3 the Dark Raven
  (`c + 0x31f8 = 0x1a05`) with the level word `c + 0x3204` = 1 / 20 / 40, 10..13 the later raven items `0x28f8`,
  `0x28f9`, `0x28fa`, `0x2900` (class `0x009f0258`, vtable `0x01a7fae8`: not ported). For 2 and 3 the level goes to the
  pet (`+0x150`, `0x009ec097`). The player viewport handlers call it for class-4 characters (Dark Lords) with a record
  byte (`+0x16`, `+0x32`, `+0x34` in three record layouts; static).
- **Create** (verified). `0x00c92a29` deletes the old pet (`0x00c9321b`) and, for `0x1a05`, runs the constructor
  `0x009ecbdf`: the start point is the owner's bone `0x23` through `0x012b6d2a` (BodyScale · VectorTransform((0, 20,
  20)) + the owner's position), lifted by a mount's rider offset + 30 and by 30; its tile is the start point / 100
  (negative: the owner's tile, z = owner z + 250). Without the bone or the owner's model the pet starts on the owner's
  tile at terrain height + 300 (soul: + 250). CreatePetPointer `0x009ec0b0` sets the object (ObjectInit, scale 0.7,
  light 0.5, box (−60, −60, 0)..(50, 50, 150), position tile · 100 + 50 at terrain height, the safe flag from
  TerrainWall bit 0, velocity 1, `+0xc8` 13, blend mesh −1); the constructor then sets alpha 0.1 and the fade-in flag.
- **Two models.** In a safe zone (`c + 4`) the constructor picks model `0x748` (`Data/Item/Dark_Soul.bmd`, a
  two-mesh "soul"), elsewhere `0x411` (`Data/Skill/DarkSpirit.bmd`). The per-character move `0x00c930df` checks the
  model against the owner's safe state (`0x00c92e04`: soul models `0x748`, `0x750..0x752`; raven models `0x411`,
  `0x74d..0x74f`); a mismatch sets the fade-out flag, and a pet whose alpha reaches 0 is re-created with the right
  model.
- **MovePet** `0x009ecfe9` (verified for AI 0, 1, 3). Fade in by 0.1 a step, fade out by 0.1 near the owner or by
  7.5 / distance farther; nothing more under the owner's buffs `0x3d`, `0xb2`, `0x118`. Object `+0x41` = the level
  byte. The pet-info request packet goes out once (`[0x01d1e028 + 8]`; offline it is never sent). The safe flag
  follows the owner's; both safe → AI 3. The animation tick runs at 0.4 (0.1 for a non-zero `+0x367c`); when it
  reports the end of an action, the AI picks the next one (0 → 1, 1 → 0, 3 → 1, 2 / 4 → 3).
  - **AI 0 / 1, fly**: unless the owner has buff `0x12`, a Spark03 (`0x7f26`, subtype 5, scale 0.8, light (0.3, 0.4,
    0.7)) at a random bone (rand % 0x42) of the pet; at 150 or more from the owner a turn toward it by rand % 15 + 5
    degrees; the move by the direction rotated by the angle; a band above the owner: 250 (350 for a Dark Horse /
    Divine Horse rider or world `0x37`; 340 with a band of 30 for the ride-state mounts) — below it the pitch drops by
    2 to −15 and a new heading comes 1 step in 10, above it + 100 the pitch rises by 2 to 15 (1 in 20), else 1 in 28;
    a new direction: far − (rand % 64 + 128)/10, near − (rand % 8 + 32)/10 with a heading turn of rand % 60, averaged
    with the old one, and a vertical part (rand % 64 − 32)/10 (the ride-state mounts: a narrower range); the AI is 0
    while the forward speed is below −12, else 1; while fading in the speed drops by 1.5.
  - **AI 3, sit**: the raven flies to the owner's bone `0x23` + (0, 20, 20) (scaled by the owner's scale, plus a
    mount's lift) with MoveHumming at a speed that grows by 1 a step and stops within 50; the soul model instead takes
    a fifth of the way to that point (plus 30) each step when within 500 (else it jumps there), bobbing by
    2.5 · |keys/2 − (frame − 3)| / (keys/2) with the owner's animation, writes the model's BodyOrigin and the parent
    matrix `0x078965ac`.
  - **AI 2 / 4 / 5** are the attacks the server's pet commands start (target character `+8`, effects `0x009ef9a5`):
    static, not ported (offline nothing starts them).
  - Last, the lost counter (`+0x6c`): it counts steps with the pet 200 below the owner or more than 640 away and puts
    the pet 250 above the owner after 90.
- **RenderPet** `0x009ef6d5` (verified): the hero's pet record `+0x10` (`0x0129dabe`) gives the level byte; frustum
  test (an invisible pet gets velocity 3, which the sit AI then uses); drawn for a Player owner or the models
  `0x411` / `0x748` (the soul at scale 0.3) with RenderObject(o, 0, 0, buff 0x12 ? 10 : 0, −1, −1). The hero's pet
  is drawn only with a pet record and outside the run-speed worlds; others outside those worlds.
- **The model passes** (verified, the render registry `0x01d1e010`): the raven `0x00a2eea5` draws mesh 3, then mesh 2
  below level 20, mesh 1 below 40, else mesh 0 plus a chrome pass of mesh 0 (flags `0x44`, colour (0.3, 0.6, 1)) and an
  overlay of mesh 3 (flags `0x42`, texture `0x7fa5`, light sin(WorldTime / 1000)); a shadow with BodyOrigin on the
  terrain under the pet (alpha 1, 0.2 in Atlans). The soul `0x00a55f03` turns by 2 degrees a frame, draws the body, a
  chrome mesh 0 (texture `0x7f1f`, colour (0.5, 0.1, 0.9)), mesh 1 twice (`0x42`, the second with the colour times
  the wave `0x0185bdc4(−4, 0)`), a flare sprite (0.6, 0.2, 0.9) and a particle `0x83b3` (subtype 0xb) near it.

## Routines

| Routine | Address | Status |
|---|---|---|
| pet byte | `0x00c92bea` | verified |
| create, delete | `0x00c92a29`, `0x00c9321b` | verified (delete: recorded stub) |
| constructor, CreatePetPointer | `0x009ecbdf`, `0x009ec0b0` | verified (ObjectInit and the CHARACTER constructor `0x0129d272` run as client code) |
| set AI, alpha step, animation | `0x009ec878`, `0x009ecb21`, `0x009ec7b7` | verified |
| MovePet | `0x009ecfe9` | verified for AI 0 / 1 / 3; AI 2 / 4 / 5 static |
| per-character move, model check | `0x00c930df`, `0x00c92e04` | verified |
| per-character render, RenderPet | `0x00c9314f`, `0x009ef6d5` | verified |
| render functors | `0x00a2eea5`, `0x00a55f03` | verified |
| pet commands, attack effects, pet HUD | `0x009ef817`, `0x009ef8df`, `0x009ef9a5`, `0x009efe29` | static |
| later raven class | `0x009f0258` (vtable `0x01a7fae8`) | not read |

The frame loop calls the move from MoveCharacter (`0x013b1ecc`) and the render from RenderCharacter (`0x01378b5f`).

## Validation

`scripts/validate_raven.py` runs the client routines in Unicorn (the machine of `scripts/validate_helpers.py`, an
`AND [mem], 0` / `OR [mem], −1` store not counted as an undefined read) and `libclient_raven` through ctypes with
Python host callbacks giving the same answers as the client-side stubs. Compared after every step: rand() state and
count, the modelled pet bytes (40 object fields, 11 pet fields), the owner's pet item and level word, the request
flag, the parent matrix and the ordered host-call log. Client code includes the constructors, ObjectInit, CreateAngle,
TurnAngle2, AngleMatrix, VectorRotate, MoveHumming, the composition `0x00cff83e`, sqrt and fabs; stubs are listed in
the script's header.

Private run (`--cases 1000 --draw-cases 3000 --negative 60 --mutations`, about three minutes), report
`evidence/native-raven/report-01.json`:

| Section | Cases | Result |
|---|---|---|
| sessions (pet byte, create, move, render; 1..3 owners, owner changes, safe-zone switches, long chases) | 1,000 sessions, 39,093 steps (28,961 moves, 6,095 renders, 4,037 pet bytes), 112,628 host calls | 0 mismatches, 35/35 branch probes |
| draw (functors `0x00a2eea5` / `0x00a55f03`) | 3,000 (2,009 raven, 991 soul), 26,843 calls | 0 mismatches |
| negative control (world `0x37` planted) | 60 sessions | 21 disagree |
| planted mistakes (`-DMU_RV_MUTATION=1..4`) | 4 | 4 detected |

Portable: `reconstructed/raven/test_raven.py` (6 worked examples) and `native/tests/test_native_raven.py` (mu-walk on
the synthetic world with synthetic raven models: flight, the soul on a safe tile, a demo player, determinism; one
private Lorencia case).

## Native integration

- `native/core/mu_world_raven.*` hangs off `mu_world_helpers` (its owners, model table and draw target): the step
  after the helpers' step applies the pet byte, syncs the owners and runs `0x00c930df` per owner; the draw runs
  `0x00c9314f` and draws the functor's passes through the scene draw (per mesh, flags, colour), the flare and the
  shadow through NATIVE-PARTICLE-001.
- `mu-world` / `mu-client --helper dark-raven | dark-raven-20 | dark-raven-40` (DEMO: the server's pet byte 1 / 2 / 3);
  the players file takes `raven=1|2|3` (DEMO); `native/world/lorencia-demo-players.txt` gives Corvin, a Dark Lord on a
  Dark Horse, a level-40 raven. The Preview app's "Your helper" picker lists the three.
- Viewer choices: the sparkles use the pet's own bone in the world (the client transforms a bone of the pet's pose with
  the Player model's scale and origin); the overlay textures `0x7fa5` / `0x7f1f` are not loaded, so those passes are
  skipped; the soul's parent-matrix write and the model's `+0x84` angle are not used by the native draw; the pet-info
  packet is never sent (the flag starts set).

Renders stay local under `~/Documents/mu-mac-tools/native/renders/helpers2/raven/` (`t1` the soul in Lorencia town,
`t2` the level-40 raven in the field east of the town, `players1` the demo players with Corvin).

## The Muun pets (static survey)

The Muun system is a separate manager (getter `0x009c2aea`, object `0x01d1dce8`, a map keyed by character with three
slots each, "MainMuun", "SubMuun", "HeroMuun"); the frame loop calls its move `0x009b9913` (slot vtable `+0x10`, then
`0x009acf1f` and `0x009af2da`) and render `0x009b99fa` (vtable `+0x14`); ChangeCharacterExt clears a character's
slots with `0x009b9f1f(c, −1)`. Its tables (BuxConvert `fc cf ab` per record, a trailing checksum with key `0xe2f1`;
decoded locally only):

| File | Layout |
|---|---|
| `Data/Local/MuunInfo.bmd` | u32 count (386), 60-byte records of 15 ints: id, item code (`0x2000 + n`), kind, flags, a model number, ... the evolved item (−1 none), a value |
| `Data/Local/MuunRenderInfo.bmd` | u32 count (386), 0x264-byte records (loader `0x009b90d5`): id, item code (+0xae6 = item type), a model file name at +9 (`NULL` for none), an effect texture name at +0x123, then floats (scale, colours, speeds) |
| `Data/Local/MuunMeshInfo.bmd` | u32 count (560), 300-byte records (loader `0x009b9510`): the render-info id, a mesh index, a texture name at +8 (`*_render.JPG`, `*_effect.JPG`) |

The Muun models are the `Data/Item/*pet*.bmd` files. Neither the Muun objects' classes (the creation goes through the
server's Muun packets in `0x01219294`) nor their follow logic were read; they remain the next step.

## Limits and next steps

- AI 2 / 4 / 5 (attacks on the server's command), their effects and the pet HUD are static readings; the later raven
  items `0x28f8..0x2900` (class `0x009f0258`) are not read.
- The overlay textures `0x7fa5` and `0x7f1f` and the soul's particle `0x83b3` (unsupported kind) are not drawn.
- The Muun pets: the manager, the classes and the follow logic (tables surveyed above).
