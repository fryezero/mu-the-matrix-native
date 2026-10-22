# Helpers: the pets and mounts of a character (NATIVE-HELPERS-001)

This finding answers how the pinned client turns a character's helper item into the thing that follows or carries
it: which item becomes which model, how the Guardian Angel circles its owner, how a mount follows, animates, lifts and
poses its rider, and which effects they create. It joins that to the native world for the hero (a labelled demo option)
and for the other players of NATIVE-PLAYERS-001.

Labels:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case
  (`scripts/validate_helpers.py`);
- **extracted**: values read by executing the client's own methods (the mount class table);
- **static**: a reading of the decoded instructions that was not executed;
- **demo**: native inputs or choices that stand in for the server or the inventory.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

The validator refuses other inputs and records the SHA-256 (first 16 hex digits) of the 22 bodies it names.

## Short answers

- **Four helper systems.** This client keeps the old "bugs" for the Guardian Angel, a C++ mount manager (singleton
  `0x01d1dce0`, getter `0x009c104e`, one object per riding character in a `std::map` keyed by the character key
  `c + 0x3e`) for every ride item, a data-driven pet process (`0x00b990b0`, Demon, Spirit of Guardian, Rudolph, Panda,
  Skeleton ...: not reconstructed) and the Muun slot (decoded only, NATIVE-PLAYERS-001). The Imp is neither: it is a link
  item drawn by RenderCharacter.
- **Item → model.** Helper items are group 13 (code `0x1a00 + index`, item model `0x24e6 + index`). ChangeCharacterExt
  (NATIVE-PLAYERS-001) writes the slot-10 type `0x24e6 + (e[4] & 3)` and creates the angel's bug for 0; the ride word
  `c + 0x322e` (viewport `+0x30`) and the ride state `c + 0x322c` go to the mount manager. The manager's kind
  `0x0106cc24` is 0, or 1 for items of kind B `0x4f`, or 2 when there is no item but a ride state (the three "Giant"
  transformations); the factory `0x0106cde5` maps the item (or the state) to one of 21 classes, each loading its own
  model from `Data\Skill\` (vtable `+0x38`): Uniria `0x1a02` → `0x417` Rider01, Dinorant `0x1a03` → `0x473` Rider02, Dark
  Horse `0x1a04` → `0x410` DarkHorse, Fenrir `0x1a25` → `0x4a9` red / `0x4a8` black / `0x4aa` blue / `0x4ab` gold by the
  state 0 / 1 / 2 / 4, and the later items (Ghost Horse `0x19d7`, Ice Dragon `0x19e3/4`, Pierce Lion `0x184b/c`, Shining
  Tail `0x1853/4`, Ur `0x185d/e`, Leviathan `0x1833/4`, Tauros `0x1835/6`, Divine Horse `0x28f7`).
- **The angel** (verified). CreateBug `0x00c9d8df` takes the first free of the 10 objects at `0x0bdc3220` (nothing in
  the run-speed worlds `0x009dacb8`, nothing for a non-Player owner unless it is the angel): scale 0.7, alpha 0 → 1,
  blend mesh 1, light 3, at the owner + (rand % 512 − 256, rand % 512 − 256, rand % 128 + 128). MoveBug `0x00c9d95a`
  fades in, makes four Spark02 (`0x7f25`, subtype 1) per step unless the owner has buff `0x12`, ticks the model at
  `+0xbc` 0.5, turns toward the owner by 20° when it is 150 or more away (CreateAngle / TurnAngle2), moves by its
  direction, wobbles ±8 in z, picks a new direction 1 step in 32 (fast when far, slow and a random heading when near)
  and climbs or sinks to stay between 100 and 200 above the owner. RenderBug `0x00c9e28a`: TestFrustrum2D, scale 1.2
  in scene 5 else 1, RenderObject(o, 0, 0, buff ? 10 : 0, −1, −1), then the flare `0x7ef7` sprite with light
  (0.5k, 0.8k, 0.6k), k = (rand % 30 + 70) / 100. In scene 6 outside worlds `0x52..0x5a` a bug whose owner is gone or
  not of kind 1 dies. DeleteBug `0x00c9ea70` kills the owner's angel, imp and dark-spirit bugs. The Imp's bug code
  (`0x24e7`) exists but no caller creates one.
- **A mount** (verified). The base move `0x0103d45a` copies the rider's position and angle, fades out by 0.1 while the
  rider fades (`+0x3a` 1 / 2), ticks the model with the class's play speed for its action (`0x0103dbf4`, 0.4 by
  default), recomputes the rider offset (vtable `+0x10`: TransformPosition of a named bone, e.g. Uniria "Bip01 Spine"
  + 20 z, Dinorant "Bip01 Spine1" + 50, Dark Horse + 30, Fenrir "sit_pos_0"; some later classes scale it by the object
  scale) and keeps a riding flag (rider live and `c + 0x31e8` clear). The class moves add dust on walk/run (Uniria
  and Dinorant: smoke `0x7f5a` in world 2 else `0x7f5b`, half of the steps), Fenrir's 1-in-3 dust or, in the flying
  worlds 10 / `0x84`, an effect `0x8012` and rand % 5 + 5 puffs at a bone at fixed frames, the Dark Horse's dust from
  "Bone03", its running/flying steps and its ring of joints `0x7f78` (`c + 0x328d`, cleared after). The action map
  `0x0103d931` turns the rider's action category (`0x0106c4b6`: 1..0x31, 0x32.., 0x4f.., 0x6f.., 0x89.., 0x133..,
  0x142.., 0x148..) into the mount's 0 stand, 2 walk, 3 run, 5 attack, 4 skill, 7 die; the Dinorant flies with
  actions 8..11 in worlds 8 / 10 / `0x84`, the Divine Horse plays an idle variant 1 now and then.
- **The rider** (verified). SetPlayerStop / SetPlayerWalk ask the manager (`0x0106bdb7`: riding) and then
  `0x0106c382(c, how)`: unarmed (or in a safe zone without a kind-B `0x5a` weapon) the actions 0x26 stand, 0x47 walk
  (run counter below 20), 0x67 run, 0x13b (the attack path); armed 0x27.. / 0x48.. / 0x68.. / 0x13c.. by the hands
  and the weapon kinds `0x59` / `0x5a` / `0x72` (`0x54` and class nibble 9 for the stand). Around the character
  render the frame loop calls `0x0106bcc5(1)` / `(0)`: while the rider's action is a ride action
  (`0x0103dc68`: 0x26..0x31, 0x47..0x4e, 0x67..0x6e, 0x118..0x132, 0x13b..0x141) its position is the mount's plus the
  offset, so it sits on the saddle.
- **Render** (verified). The loop `0x0106bc2b`: TestFrustrum2D on the mount OBJECT, RenderObject's setup + body
  `0x017ec896(o, 1, buff ? 10 : 0, 0)`; drawn → the shadow `0x0103d281` (EnableAlphaTest, glColor4f(0, 0, 0, 0.7 · alpha)
  or 0.2 in worlds 7 / `0x80..0x82`, none in 10 / `0x84` / `0x009b0418` worlds; RenderBodyShadow with `+0x4c`, Tauros 0,
  Leviathan the other shadow `0x012bc5ab`), the after-pass `0x017edf43`; the first drawn (or failed) frame puts the
  rider into the stand ride action.
- **The Imp** (static). BackCarry `0x0139db9a` draws slot type `0x24e7` in scene 5, or scene 6 without a pet item, with
  RenderLinkItem((20, 0, 20), c, &slot, ...) on link bone `0x22` at part speed 0.5, then a red flare (scale 1.5,
  (0.5k, 0, 0)) at the bone's (20, 0, 15); class nibble 6 with five listed staffs shifts both vectors.
- **Packets.** The equipment change is opcode `0x25` (`0x01228b60`, static: for helper items of kind A 5 / kind B 0x2e or
  kind A 0x14 it writes or clears `c + 0x322e` / `c + 0x322c`; a protection-patched site sits in it). Opcode `0x45`
  (`0x0122f1b6`) is the viewport of transformed players (CreateMonster with the record's class), not an equipment change.

## Routines

| Routine | Address | Status |
|---|---|---|
| CreateBug, CreateBugSub | `0x00c9d8df`, `0x00c9d42a` | verified |
| MoveBugs, MoveBug | `0x00c9e24a`, `0x00c9d95a` | verified (FadeAlpha, CreateAngle, TurnAngle2, AngleMatrix, VectorRotate run as client code) |
| RenderBugs, RenderBug | `0x00c9e4e3`, `0x00c9e28a` | verified |
| DeleteBug, the bug types | `0x00c9ea70`, `0x00ca211e` | verified |
| mount kind, descriptor, factory | `0x0106cc24`, `0x0106cc74`, `0x0106cde5` | verified (1,102 keys) |
| class model / play speeds / rider offset | vtable `+0x38`, `+8` + `0x0103dbf4`, `+0x10` | extracted and verified (21 classes, Fenrir's five states) |
| base move, class moves | `0x0103d45a`; `0x01064b6d`, `0x0104009b`, `0x0103f2a4`, `0x010438c1` | verified (other classes: base move only) |
| action map, category, mount SetAction | `0x0103d931`, `0x0106c4b6`, `0x0103d9eb` / `0x010401c6` / `0x010406cf` | verified |
| rider action | `0x0106c382`, `0x0103dd6b`, `0x0103ddde` | verified (mount classes 1..18) |
| rider lift | `0x0103da5c`, `0x0103dc68` | verified |
| render body / shadow / after-pass | `0x0103d6d5`, `0x0103d281`, `0x0103d830` | verified |
| manager set / reset / init | `0x0106b85d`, `0x0106ba49`, `0x0103cf7a` | static (the pose builder and the rider reset `0x013a763e` inside) |
| the Imp link | `0x0139ef04..0x0139f2d9` | static |
| equipment change (opcode 0x25) | `0x01228b60` | static (partial) |

## Validation

`scripts/validate_helpers.py` runs the routines in Unicorn (`scripts/actor_machine.py`: declared regions with a
defined-byte mask, every undefined or undeclared access stops a case) and the library `libclient_helpers` through
ctypes with Python host callbacks giving the same answers as the client-side stubs. Compared after every step: the
rand() state and count, the modelled OBJECT bytes, the mount object's fields, the rider's position and ring byte and
the ordered host-call log. The std::map of the speeds, the C++ constructors and the vtables run as client code; the
model container, the animation tick, SetAction, CreateParticle / CreateEffect / CreateJoint / CreateSprite,
RenderObject's halves, RenderBodyShadow, glColor4f, the buff lookup, the item and weapon predicates, the bone lookup
with TransformPosition (synthetic matrices), operator new and the std::string helpers are recording stubs.

Private run (`--bug-cases 1000 --cases 1000 --negative 60 --mutations`, about four minutes), report
`evidence/native-helpers/report-02.json`:

| Section | Cases | Result |
|---|---|---|
| bugs (create / move / render / delete sessions, 1..4 owners, fuzzed slots) | 1,000 sessions, 21,471 steps, 68,474 host calls | 0 mismatches, 22/22 branch probes |
| mount kind and factory | 1,102 keys (every ride item × states, no-item states, random items) | 0 mismatches |
| mount classes (model, speeds 0..15, rider bone and lift) | 21 classes, 25 class/state entries | 0 mismatches |
| mount moves + action map | 1,000 cases, 9,544 steps, 26,818 host calls | 0 mismatches, 9/9 probes |
| rider action, action category | 4,000 cases, 512 action words | 0 mismatches |
| mount render, lift | 1,000 cases, 5,962 steps (334 lift cases) | 0 mismatches |
| negative controls (buff, world, play speed) | 5 | 5 detected |
| planted mistakes (`-DMU_HP_MUTATION=1..6`) | 6 | 6 detected |

Portable: `reconstructed/helpers/test_helpers.py` (7 worked examples) and `native/tests/test_native_helpers.py`
(mu-walk on the synthetic world with synthetic helper models: the angel, a riding hero, the Imp, Fenrir gold, demo
players with their angel and Uniria, `--no-helpers`; one private Lorencia case).

## Native integration

- `native/core/mu_world_helpers` hosts the reconstructed routines: the models (Data/Item/helper01..02.bmd and the
  classes' Data/Skill files, loaded on first use), the host services (RequestTerrainHeight, the model tick, SetAction
  on helper objects and on the riders through mu_walk / mu_world_players, CreateParticle / CreateSprite / CreateEffect /
  CreateJoint through NATIVE-PARTICLE-001's module, the bone lookup by name on the model's last pose), the owners
  (index 0 the hero, 1 + i the demo players) and the draw (RenderObject's body light and passes, the blend mesh, the
  shadow through `mu_world_particles_shadow`, the Imp through NATIVE-RENDERCHAR-001's link path).
- mu_walk and mu_world_players ask the rider action through a hook in SetPlayerStop / SetPlayerWalk, keep the run
  counter while riding (`0x0106bdb7` / `0x0106bd76`), pass the ride word to CharacterMoveSpeed and add the lift to the
  model position.
- `mu-world --helper NAME|CODE [--helper-state N] [--no-helpers]`, `mu-client --helper ...` (DEMO: the hero's helper;
  the client fills it from the inventory, not reconstructed). The demo players file takes `pet=angel|imp`,
  `ride=CODE`, `ride_state=N`; `native/world/lorencia-demo-players.txt` gives Aeris an angel, Sunwing an imp, Kyra a
  Uniria, Mordred a Dinorant and Redhand a gold Fenrir.

Renders stay local under `~/Documents/mu-mac-tools/native/renders/helpers/` (`showcase/`, `t-*`, `players1/`, `model/`).

## Limits and next steps

- The data-driven pets of `0x00b990b0` (Demon, Spirit of Guardian, Rudolph, Panda, Skeleton, ...; petdata.bmd), the
  Dark Raven / Dark Spirit and the Muun pets are not reconstructed (the players' calls to them are counted only).
- The class moves of the 17 later mounts (their own dust and visuals) and the ride-state "Giant" transformations' own
  rider actions are not ported; their base move, model, speeds, offset, shadow and render are.
- The manager's set / init, the Imp block and the 0x25 packet are static readings; the after-pass `0x017edf43`
  (object visuals) of mounts is not drawn; particles and effects of kinds NATIVE-PARTICLE-001 does not port (Spark02
  subtype 1, smoke `0x7f5b`, effect `0x8012`, joint `0x7f78`) are created but not drawn.
- Next: the pet process (petdata.bmd and its behaviours), the 0x25 packet end to end through mu_world_players, the
  later mounts' visuals, a live capture of a rider and an angel in Lorencia for a side-by-side.
