# Monsters, NPCs and animation actions (NATIVE-ACTOR-001)

This milestone recovers how the client turns a monster or NPC into a model and
how it animates actors:

- which model file a monster type, server monster class or NPC index loads;
- per-type scale and equipment slots;
- the play speed and loop flag of every action;
- how the animation tick `0x012b4dd3` is driven per action;
- the Player action indices used for standing, walking and attacking.

The result feeds a native module (`native/core/mu_actor`) and
`mu-render actor`, which renders animated monsters and NPCs headlessly.

Every statement carries one of four labels:

- **verified**: authored C compared with the client's actual instructions under Unicorn;
- **extracted**: produced by running client code under Unicorn with stated stubs and assumptions, without an authored reimplementation to compare against;
- **static**: a reading of the instructions that was not executed;
- **inference**: a name or interpretation.

Names are investigator labels. The identity of the inputs is the same as in
[client-skinning.md](client-skinning.md): restored text capture09
(`2bd5f2e9…3724`) and second section run10 (`c985e2e6…672f`).
`scripts/validate_actors.py` pins the SHA-256 of every routine it executes or
reads, and refuses other text.

## Routines

| Routine | Address | Status |
|---|---|---|
| OpenMonsterModel(type), cdecl | `0x0180b0f4..0x0181f25c` | verified (action part) |
| SetActionSpeed / SetActionLoop (thiscall on model, checked) | `0x012bd437`, `0x012bd471` | run as client code inside the verified routines |
| GetAction (thiscall, checked) / ActionAt(index, action) | `0x012bcf9d`, `0x00eaaa44` | same |
| Model container getter / model lookup (index `0..0x3af6`, BMD `0xd0` bytes) | `0x00966cc4`, `0x00eaa8cf` | stubbed (static reading) |
| AccessModel(index, dir, name, number) | `0x018202b4` | stubbed; file-name rule static |
| Character animation step(character, object), cdecl | `0x013960d2..0x013966a8` | verified |
| SetAction(object, action), cdecl | `0x012affa4..0x012b001a` | verified |
| Unarmed player stop action(class byte) | `0x0139d6da..0x0139d89f` | verified |
| CreateMonster(class, x, y, key, …) with 16 map processors | `0x0137fbac..0x0138ce1c` | extracted |
| OpenNpc(model index) | `0x01808a40..0x0180ae1e` | extracted |
| Player loader, action-speed section | `0x018311c2..0x0183220e` | extracted |
| SetPlayerStop / walk chooser / SetPlayerAttack | `0x01391e55`, `0x0139002a`, `0x01392bde` | static |

Layouts (static, consistent with the existing reconstructions):

- Model (BMD): `+0x24` mesh count, `+0x26` action count, `+0x30` action array, `+0x60` head bone, `+0xa8` current action.
- Action record (stride `0x10`): `+0` loop byte (the tick's stop flag), `+4` binary32 play speed, `+8` key count, `+0xa` lock flag.
- Object: `+0x2a` action, `+0x2c` prior action, `+0x5c` model index, `+0xa0` scale, `+0xd0`/`+0xd4` frame/prior frame, `+0x358` buff container.
- Character record: the object at `+0x3254`; slots at `+0x1c4 + k*0x3fc` (u16 model/item, u8 level); `k = 6, 7` are the weapons.

## 1. Monster type → model and action speeds (verified)

OpenMonsterModel(type) does the following:

1. It uses model index `type + 0x7a5`. It returns at once if the model already has actions or meshes.
2. It calls AccessModel(index, `"Data\Monster\"`, `"Monster"`, `type + 1`). AccessModel names the file `"<name>.bmd"` for number -1, `"<name>0<n>.bmd"` below 10 and `"<name><n>.bmd"` otherwise (static).
3. It returns if the model has no meshes. Otherwise it calls OpenTexture with `"Npc\"` for types `0x46..0x48` in the worlds of predicate `0x009dacb8` (`0x12..0x17`, `0x35`, `0x61`), with `"Object31\"` for type `0x4a` in world 30, and with `"Monster\"` otherwise.
4. Through the checked setters it sets the default speeds of actions 0..6 to 0.25, 0.2, 0.34, 0.33, 0.33, 0.5 and 0.55, and sets action 6 to loop.
5. For actions 0..5 it applies unchecked binary32 multiplies: x1.2 for type 3, x0.7 for types 5 and 25, x0.4 for types 37, 42 and 0x1ab.
6. Two switches follow, at `0x0180cd7c` and `0x01812e53`, with a rule between them: types 14, 31, 39 and 40 set action 1 to loop. The switch cases store constant speeds, loop bytes and model fields (the head bone `+0x60` in 41 cases, `+0x94` in one). They store through the action array without a bounds check, through the checked setters, or through GetAction/ActionAt pointers. On a model with too few actions, a GetAction/ActionAt pointer is null and the client faults.

**Reconstruction.** `scripts/actor_static.py` interprets the switch code statically, one type at a time, over a closed instruction subset (anything else is reported). It lifts 913 operations in 191 distinct blocks for types `0..0x258`; type + `0x7a5` stays below the first NPC model, `0x9fe`. These are generated into `reconstructed/actors/monster_open_table.h`. `mu_monster_open` (`reconstructed/actors/actors.c`) hand-codes steps 1..5 and runs the table. It does not reproduce the type-specific sound (`0x00a6ab76`), extra-bitmap (`0x0185baac`) and action-sound (`0x018329fa`) loads, or the sub-model loads for types 147, 226, 229..233, 245 and 289. Those loads are recorded by the validator only.

**Comparison.** The validator runs the client from the routine entry for every type `0..0x258`, with 12 actions and with 3 actions. It also covers 56 world/texture cases and the early returns (no meshes, negative mesh count, preloaded counts, 0 and 32 actions). Every model and action-array byte, and the AccessModel and OpenTexture calls of the opened model, must equal `mu_monster_open` and an independent Python model built from the lifter's operations rather than the C table.

- Result: **1276/1276 cases match**. In 29 of them the client faults through a null action pointer at exactly the operation where the C returns `MU_ACTOR_CLIENT_FAULT`, and the regions agree up to that point.
- Negative controls differ in this many cases: defaults stored without the bounds check, 596; scale rules skipped, 18; direct stores checked, 192.

The reader `0x012b3812` allocates the action array without initialising play speeds (static). Actions an opener leaves alone therefore have undefined speeds in the client. The native module gives them 0.25 and labels this as a viewer choice.

## 2. Action indices (inference from static use)

Monster actions follow from:

- the default-speed order;
- the die action's loop flag;
- SetPlayerAttack's monster branch, which uses actions 3, 4, 8 and 9;
- the "action 6" factors in §3.

The reading is: 0 idle, 1 idle 2, 2 walk, 3 attack 1, 4 attack 2, 5 hit, 6 die (it clamps on its last key), and 8/9 further attacks. Monster files use these indices and have no run action.

Player actions (Player.bmd must have exactly `0x186` actions; the loader checks this at `0x01830b39`, static):

| Pose | Weapon kind (from the item index range and item attributes) | Action |
|---|---|---|
| stand | none | verified helper `0x0139d6da`: class nibble 2 → 2, 7 → 5, 8 → 6, 14 → 6, 11 → 1; 5 → 3, 9 → 6, 12 → 2 (1 in the event worlds above); 10 → 1 or `0x1f` when rand()%20 == 0; 15 → 8 or 9; else 1 |
| stand | one-handed / two-handed / spear / staff / bow / crossbow | `0xb` (class 9: `0x1d`, class 15: `0x25`) / `0xc` / `0xe` / `0xb` (two-handed staff `0xe`) / `0xf` / `0x10` (static) |
| walk | none / one-handed / two-handed / spear / bow / crossbow | `0x32`, or `0x33` for female stand classes / `0x34` (`0x3f`, `0x46`) / `0x35` (class 10: `0x40`) / `0x37` (some spears `0x36`) / `0x38` / `0x39`; runs are `0x4f..0x66` (static) |
| attack | none / one-handed / two-handed / spear / bow / crossbow | `0x6f` (classes 7, 8, 9, 12, 14: `0x70`) / `0x71 + counter%2` / `0x75 + counter%3` / `0x7b + counter%3` / `0x7e` / `0x7f` (counter = character `+0x28`; static) |

Item groups are `0xae6 + 512*g`:

- swords, axes and maces below `0x10e6`;
- spears below `0x12e6`;
- bows and crossbows below `0x14e6` (attribute kind 8 or 9 through `0x0139d8f8`);
- staffs below `0x16e6`.

The two-handed byte is item attribute `+0x253` and the kind is `+0x251`. Both are runtime item data. Mounts, buffs, safe zones and special items add further branches, which are not reduced here.

## 3. Driving the tick (verified)

**SetAction** `0x012affa4` does nothing when:

- the model is missing;
- the action is at or beyond the action count (a signed compare, so negative actions pass);
- the action is already current.

Otherwise it stores the prior action and prior frame and sets the new action with frame 0. Result: **3000/3000 cases match**, and 1128 of them change state.

**Character animation step** `0x013960d2`:

1. The speed starts as `Actions[model+0xa8].speed` if the model has actions, otherwise 0. It is clamped to at least 0 (NaN is kept).
2. Per-action factors:
   - x1.5 for actions 3..4 when character byte `+0xe` is set;
   - /2 for actions `0x9c`/`0x11d` after frame 6;
   - /10 for action `0x92` after frame 5.5;
   - /8 or /2 for class 4, action `0xa7`, frames 1..3, depending on an equipped-item check;
   - /2 for action `0x9f`.
3. Per-model factors:
   - models `0x135..0x144` x2 or x1.5;
   - models `0x7e5`/`0x940` x4 on the die action after frame 6;
   - `0xa52` x0.5;
   - `0x7fc` /2 on die.
4. Any of buffs `0x3d`, `0x48`, `0xb2` or `0x118` returns 0 without ticking.
5. The tick runs on `&object+0xd0`, `+0xd4`, `+0x2c` with this speed.
6. When the loop ends, actions `0x184`, `0xd9` and `0x125` call `0x0138fe69` (stop). So does action `0x170` on a tile whose attribute (map `0x0b795420`, root-motion key offset /100) has bit 4.

The buff check, the item check and the stop call are stubs that record their arguments; the tick runs as client code. Result: **4442/4442 cases match** the C, which runs the reconstructed tick. The comparison covers the returned AL, the speed passed to the tick, every region byte and the service-call sequence. Every listed branch was reached (all 24 counted).

The callers (`0x013a763e`, `0x013a6e64`) give no evidence for the model's current action `+0xa8`. The world-object animation `0x017ff238` sets it from the object right before its tick, and the native module does the same (inference). One step per 40 ms logic step is the native choice; how often the client animates per logic step is still open (CLIENT-FRAME-001).

## 4. Server class → model, scale, slots (extracted)

CreateMonster first tries 16 map processors, then a generic switch. Each processor returns a character or 0.

The validator runs each processor directly, as client code, in chain order. The generic switch is entered mid-routine with its frame built. Stubs record the following:

- CreateCharacter `0x0137f6c2` (key, model, x, y, angle);
- the two openers, the name setter and the model lookup (a pool of 16-action models whose speeds start as a sentinel);
- `rand()` = 0.

The world is 0.

Assumptions:

- Four processors keep their state in uncaptured singletons and are treated as declining: the virtual map processor, `0x00d558c3`, `0x00a9c56b` and `0x00ea37d5`.
- Between processors, a 5-byte patch at `0x0137fe24` jumps outside the captured text. This is a protection boundary and was not analysed. The chain is assumed to continue past it.
- Character create `0x0137d8a1` (stubbed) stores scale 0.9, read statically at `0x0137d9dd`. Unwritten scales take that value.

Results:

- 949 of classes `0..0x3ff` extracted: 805 generic and 144 through processors.
- 75 stop on engine state the run does not model (hero pointer, item and singleton tables); they are listed in the report.
- A static jump-table reading of the CreateCharacter model immediate agrees for 789 generic classes and disagrees for 0 (16 are not immediates).
- Classes reaching the switch default become monster type 0 and are marked `MU_CLASS_DEFAULT`.
- 23 classes also write action speeds (mostly NPCs), and these are kept.

Generated as `reconstructed/actors/monster_class_table.h`. Examples:

- class 0 → monster 0 (Monster01), scale 0.8, weapon slot 6 = `0x0cec`;
- class 3 → monster 9 (Monster10), scale 0.4;
- class 14 → the Player model `0xa91` with parts (a player-model class);
- class 256 → NPC `0xa37`, `npc_mulyak`.

## 5. NPC files and Player speeds (extracted)

**OpenNpc.** Model indices `0x9fe..0xa90` were run with a 16-action model.

- 110 load their own file. AccessModel uses `"Data\Npc\"` plus a name and number, and part models (FemaleHead…) are loaded by their parent case.
- Every action gets 0.25 (the loop at `0x0180a9de`, static), followed by per-index speeds.
- 8 indices (`0xa56..0xa5d`) stop on uncaptured per-mesh model data at `+0x34`.

Generated as `npc_table.h`.

**Player speeds.** The loader is run from `0x018311c2`, after its part loads and a temporary object array, to its end. The stubs are the Player model getter `0x0142fc46` and the action getter `0x00d33153`, both over a declared `0x186`-action model. The hero attack-speed adjustment `0x0138d9cf` is recorded and skipped. The run yields 213 speeds and 10 loop flags, and sets head bone 20. Generated as `player_action_table.h`.

## 6. Native module

`native/core/mu_actor` does the following:

1. Resolves `--type CLASS`, `--monster TYPE` or `--npc INDEX` to the client file. Path components are matched without regard to case, because installed names are often lower case.
2. Lays the model out with `mu_model`.
3. Runs `mu_monster_open` over that client memory, then the NPC and class speeds.
4. Each 40 ms step runs the reconstructed SetAction and animation step (with the tick) on a client-layout object placed next to the model window.
5. Poses and skins with the existing reconstructions.

`mu-render actor` renders the first frame (`--out`), a frame strip (`--strip`) and an animated GIF (`--gif`, with a native GIF89a writer). `mu-render character --pose stand|walk|attack --weapon-kind K --time T` applies the extracted Player speeds and the pose mapping in §2 to the merged character path.

Checks:

- Portable (CI), with synthetic models under client file names: resolution, scales, speeds (including the type-3 rule), frames equal to an independent binary32 tick model, die clamp, strip and GIF geometry, deterministic hashes, refusals (`native/tests/test_native_actor.py`).
- Library worked examples and table integrity (`reconstructed/actors/test_actors.py`).
- Private, gated on `MU_RECOVERY_INTEGRATION=1`: the Unicorn comparison above, and installed renders with every texture found.

Local renders (not committed) are under `~/Documents/mu-mac-tools/native/renders/actors/`: Bull Fighter walk, Spider attack, Giant die, Smith idle, a class 256 NPC, and Dark Knight stand/walk/attack, with and without a sword.

## Not established

- **Weapons and attachments on monsters** are now attached by `mu-render actor --world-render --actor-weapon` with the link bones the character create assigns per model ([client-renderchar.md](client-renderchar.md)); before NATIVE-RENDERCHAR-001 they were not rendered. The class slots record item models, for example `0x0cec`. The monster render path that links them to bones (inside RenderCharacter `0x01363260`) was not traced.
- **Map-processor and engine-state assumptions.** The world-specific processors and the 75 classes that stop are not in the table. Neither are classes that other worlds or rand() values would route differently.
- **Player pose mapping is static only.** Run variants and mount, buff and special-item branches are not reduced. Item attribute data (two-handed flag, kind) is not loaded natively, so `--weapon-kind` is a caller choice. The hero attack speed is not applied.
- **Effects of the opener that are not reconstructed.** Sounds, extra textures and mesh-texture switches are recorded only. Model field `+0x94` and the head bone are written into client memory, but the native draw does not interpret them.
- **Native defaults.** 0.25 for client-undefined speeds, and the animation-step cadence.
- **17 reader-rejected v15 files** (for example `Monster151.bmd`) were rejected when this was written; since MODEL-EDGE the native loader reads them as the client does ([model-edge.md](model-edge.md)).

## Reproduce

```sh
make -C reconstructed/actors && make -C native
./tools/python/bin/python scripts/actor_static.py --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin --emit-c reconstructed/actors/monster_open_table.h
./tools/python/bin/python scripts/validate_actors.py --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin --output /new/local/actors.json \
  --emit-class-table reconstructed/actors/monster_class_table.h --emit-npc-table reconstructed/actors/npc_table.h \
  --emit-player-table reconstructed/actors/player_action_table.h
native/build/mu-render actor --game-root "$MU_GAME_ROOT" --type 0 --action 2 --time 1 --frames 12 \
  --strip /tmp/walk.png --gif /tmp/walk.gif
```

The full validator run takes about 17 s on this Mac. The ignored report, `evidence/native-actors/report-03.json` (SHA-256 `3a1aa0c8…f19a`), was produced in the actors worktree. It is a single private run; CI covers the synthetic checks only.


## 7. Player-model actor body recipes, RENDER-ACTORS-001

Offline/static evidence from the same pinned text and data as sections 1..5. No original process,
network, protection module, installed app or character-power input. The [handoff](../handoffs/RENDER-ACTORS-001.md)
contains the full census, validation and limits.

The earlier class extraction stubs CreateCharacter and reports only equipment that CreateMonster writes.
An empty five-part body is not evidence that those actors wear an unrecorded armour set. Six classes use
OBJECT +0x60 as a whole-body model instead:

| Classes | Whole model | Startup file | Constructor scale |
|---|---|---|---|
| 14 Skeleton | `0x422` | `Data/Skill/Skeleton01.bmd` | 0.95 |
| 55 Death King | `0x422` | same | 1.4 |
| 56 Death Bone | `0x422` | same | 0.8 |
| 15 Skeleton Archer | `0x423` | `Data/Skill/Skeleton02.bmd` | 1.1 |
| 236 Golden Archer | `0x423` | same | 1.0 |
| 16 Chief Skeleton Warrior | `0x424` | `Data/Skill/Skeleton03.bmd` | 1.2 |

Verified constructor writes come from the generic switch cases at `0x0138366a`, `0x01383791`,
`0x0138383a` and `0x013842a4`. The startup loop `0x01832c28..0x01832c5d` executes three
AccessModel calls with directory `Data\Skill\`, name `Skeleton`, numbers 1..3 and indices `0x422..0x424`.
The bounded loop validator stops at its exclusive end; it does not claim startup as a whole.

RenderCharacter's final skeleton branch `0x01369f98..0x0136a00d` calls RenderPartObject on this whole model,
using Player's shared posed bones, alpha OBJECT +0xdc, translate 1, flags 2, and level/option/ext zero.
Its town branch `0x01367d85..0x01367e23` uses character +0x144 shifted by 3 in world 0; Golden Archer's
constructor overwrites CreateCharacter's zero at `0x0137eed1` with 8 at `0x01384306`.
The reference now retains each constructor's +0x144 word, including the value 1 written for classes
15, 16 and 55. Their kind-2 route ignores it and passes zero. Golden Archer is kind 4, so its world-0
call passes 64 and its nonzero-world call passes zero. The former zero-filled reference fixture missed
this distinction; its old passing results did not verify the town +8 state.

Executed comparisons cover worlds 0, 2, 3 and 51, plus RenderObjDraw's exact generic stream at twelve
clocks for all three level-zero models and model `0x423` at +8. The +8 stream has the textured body
and the `0x44` glow pass. Native admits `0x422..0x424` to that generic stream and applies the stored
level only in world 0. These non-item models do not change the item-body census.
The actor's class-table weapon and Death King's CLOAK-004 robe remain separate attachments.

Eleven other rows have explicit helm/armour/pants/gloves/boots in the existing extracted equipment table.
Their body/linked-item call plans are compared against RenderCharacter at idle with authored record kind 0
and option/ext 0. Their actual
native models, levels, scales and textures are checked. Nine gain loader admission; Marlon 229 and Shadow
Phantom Soldier 257 are regression controls. The native bridge still uses its existing generic weapon pose
and link handling, so the original call-plan comparison does not establish every native attachment transform.

Fifteen later rows carry subtype models but no five-part equipment. Some names describe transformation rings.
They are listed as left in the census, rather than supplied with invented armour. The Player-kind render
branches of those subtypes are not a proof that an NPC-kind actor should use them. Their world/action/kind
conditions and special effects need a separate recovery before native admission.

## 8. Later subtype actors, RENDER-ACTORS-002

Work in progress on the same pinned text and image data. CreateCharacter stores
OBJECT kind 1 at `0x0137dbd7`; the later generic constructors retain that default,
class byte 0 and level zero. The existing extraction's zero-filled CreateCharacter
stub does not itself establish the inherited kind. A bounded original-instruction
comparison now checks that default store before applying the constructor writes.

Classes 372/373 construct subtypes `0x425`/`0x429` at
`0x013838fb`/`0x01383978`. RenderCharacter's kind-1 direct body branches begin at
`0x01368496`/`0x01368510`. Startup `0x01832c5d..0x01832c8f` loads
`Data/Skill/Skeleton03.bmd` into `0x425` and `Data/Skill/Jack.bmd` into `0x429`.
Subtype `0x425` intentionally shares Skeleton03 with `0x424`.

The same direct body path covers classes 503/548/616/646/706/806/807, with startup
files panda, trans_skeleton, panda_brown, Trans_Lilith, baseball_player and cheerleader
under Data/Item. Their textured body draws use the generic RenderObjDraw stream.
The original OpenTexture retry through Data/Item/Texture supplies the baseball and
cheerleader bitmaps. No equipment or transformed-player appearance is invented.

Classes 374/378 were traced first alongside 372/373 and remain refused. Subtype
`0x3ed` draws a body then constructs a companion through CHARACTER `+0x3248` at
`0x01368f57..0x0136903e`; subtype `0x3e9` enters the larger effect/appearance branch
`0x01369043..0x013699f8`. Subtype `0x5be`, class 642, has another companion at
`0x013689d4..0x01368b4b`. Robot subtypes `0x5bc`/`0x5bd`, classes 625/626,
enter the class/action-specific block `0x01368b4b..0x01368ed6`. Class 617's
`0x5ba` direct body branch is known, but its startup filename is not established.

The [handoff](../handoffs/RENDER-ACTORS-002.md) records current verification and limits.

## 9. The six refused rows, RENDER-ACTORS-003

Same pinned text/data as section 8. Offline/static only. The new constructor
fixtures are authored appearances, not a claim about spawnability or event state.
The admission delta is 625/626 only. The bounded table is now 28 admitted and four
refused out of 32, including the two pre-existing controls. See the full before
and after table and check results in [the handoff](../handoffs/RENDER-ACTORS-003.md).

### 625 and 626, verified fixture bodies

Their generic constructors set OBJECT `+0x60` to `0x5bc` and `0x5bd`, retain
CreateCharacter's kind 1 and class byte 0, and leave equipment empty. The bounded
default-store checks execute `0x0137dbd4..0x0137dbdb` and
`0x0137db50..0x0137db57`; the latter starts with a poisoned class byte `0x16`.
The fixture therefore does not infer class zero from a zero-filled stub. Startup's
AccessModel calls at `0x018330c0` and `0x018330f5` load `Data/Item/iron_robot.bmd`
and `Data/Item/iron_robot_gold.bmd`, respectively. The constructor scales are
1.1 and 0.6. The loader and RenderObjDraw stream comparisons check exact file
identity, meshes, texture completeness and the generic level-zero body pass.

RenderCharacter `0x01368b4b..0x01368ed6` tests the class nibble with
`0x0095f5cc`, which returns `class_byte & 15`. Its two class checks are sequential:

- Class 2, action `0xd1`: write the subtype into slot 0 and call `0x016d5eb3`
  twice, with the original 10/0.3 and 5/0.6 parameters and flags `0x42`.
  The subsequent class-6 check's else branch also draws the ordinary body.
- Class 2 at other actions draws an ordinary body at both checks.
- Class 6, action `0xdf`: write slot 0 and call `0x016d5eb3` once, with
  2.5/1/0, flags 2. There is no ordinary body call in that branch.
- Class 6, actions `0xdd`/`0xde`: with signed OBJECT `+0x364 < 0` or CHARACTER
  byte `+0x2c > 0`, draw through the slot pointer. Otherwise write slot 0 and
  call the item registry `0x00d2d3f9`.
- Every other class nibble, including both constructor fixtures, makes one
  ordinary body call at every tested action. No action-dependent call applies.

The bounded hook audit executes those instructions in 270 synthetic cases,
including evolved class bytes `0x12`/`0x16`, action neighbours, target and counter
controls. It records the hook services and slot writes. It does not implement
those transformed-player mesh/registry services. The admitted recipes continue
to construct only class-byte-0 actors. Whole RenderCharacter comparisons retain
kind/world/action refusal controls; a plain body is not supplied to transformed
class-2 or class-6 records by this API.

### 374 and 642, extracted creation, refused lifetime

The kind-1 branches at `0x01368ed6..0x01369043` and
`0x013689d4..0x01368b4b` first draw the subtype body. If CHARACTER `+0x3248` is
null, each allocates `0x3ec` bytes and calls constructor `0x009eb32a` with argument
2 equal to 20 and argument 3 zero. The six trailing float arguments are
`0,0,0,0,0,0` for model `0x3ee`, class 374, and `4,22,0,0,0,0` for model
`0x55c`, class 642. Getter `0x013bb3ee` returns the allocation plus four, the
embedded OBJECT. The caller writes that OBJECT's `+0xbc` to 0.25 or 0.3 and
`+0x34c` to the actor OBJECT. An existing allocation is retained without another
constructor call. Sixteen original-instruction controls check kind, allocation,
reuse, owner pointer and the exact binary32 factor.

Allocation and construction are named recording stubs in that audit. It does
not prove the companion's per-frame follow/pose/draw, owner loss, destruction or
slot reuse. Constructor `0x009eb32a` installs vtable `0x01a7fa7c`; its following
method `0x009eb5b2` starts from the owning CHARACTER and model state. These are
separate from the Muun base-slot module. Both actor rows remain refused until
that downstream behavior and native lifetime have been recovered and compared.

### 378, extracted appearance prefix, refused cloth branch

The kind-1 `0x3e9` branch at `0x01369043..0x013699f8` draws the body first.
Buff `0x12` skips the remaining appearance branch. Without it, the prefix emits
two `CreateEffect(0x7ef7)` requests, a `0x7f84` screen bitmap and two rotating
`0x8036` quads. The audit executes eight kind/buff controls and stops at
`0x013695b1`, before the cloth allocation. This is deliberately a prefix result.

The remaining original branch allocates two `0xe8` cloth objects, initializes
them through vtable slot `+8`, uses bitmap pairs `0x8034`/`0x8035`, and stores
the list/count in OBJECT `+0x48`/`+0x3e`. Its later cloth update/render and cleanup
call `0x0137aafe` are not recovered by this lane. A body-only admission would
omit those cloths and the aura, so class 378 remains refused. Buff, emitter,
screen-quad and cloth state must be treated together in the next implementation.

### 617, startup file still unresolved

Its generic constructor stores subtype `0x5ba` and its direct body branch is
known. The executed startup block `0x01833010..0x0183332f` registers the neighbouring
panda, robot and Lilith models but no `0x5ba`. A raw immediate search of the
pinned text likewise finds no `push 0x5ba` in startup; occurrences elsewhere
include sound identifiers and are not model-loader evidence. This is not proof
that no computed or manager-mediated loader exists. No filename has been tied
to this model index, and no similarly named file is substituted. Class 617 stays
refused. The missing proof is an AccessModel or equivalent registration that
connects `0x5ba` to an exact file, followed by an actual native load.

## 10. Secondary-model opener leads beyond the 32 rows

Research only, extracted in RENDER-ACTORS-003. Nine original OpenMonsterModel
runs at world 0 with 16-action synthetic model records complete in 0.05 s.
AccessModel, texture, sound and model lookup services are the same named stubs
as section 1. The extra AccessModel calls below are recorded before returning
from the original opener. They are not a native construction/lifetime proof.

| Monster type | Extra model indices and files | AccessModel call sites | Classes in the current extracted table |
|---|---|---|---|
| 147 | `0x507..0x50c`, `Data/Monster/icegiantpart_1..6.bmd` | `0x0180be7d`, `0x0180beb2`, `0x0180bee7`, `0x0180bf1c`, `0x0180bf51`, `0x0180bf86` | none recorded |
| 226 | `0x5af`, `Data/Monster/gnomedie.bmd` | `0x0180bfc0` | 595, 635 |
| 229 | `0x59f`, `Data/Monster/Monster230.bmd` | `0x0180c09f` | none recorded |
| 230 | `0x5a0`, `Data/Monster/Monster231.bmd` | `0x0180c139` | none recorded |
| 231 | `0x5a1`, `Data/Monster/Monster232.bmd` | `0x0180c1f3` | none recorded |
| 232 | `0x5a2`, `Data/Monster/Monster233.bmd` | `0x0180c28d` | none recorded |
| 233 | `0x5a3`, `Data/Monster/Monster234.bmd` | `0x0180c327` | none recorded |
| 245 | `0x5ae`, `Data/Monster/normusdie.bmd` | `0x0180c590` | none recorded |
| 289 | `0x605`, `Data/Effect/Magic_type02.bmd`; `0x603`, `Data/Effect/pgunbossspin.bmd` | `0x0180b9d9`, `0x0180ba2e` | none recorded |

The class column is a lookup in the existing world-0 constructor extraction,
with its section-4 assumptions. An absent row says nothing about ordinary
spawnability or another map processor. These nine openers and 15 secondary
loads are a bounded lead list, not a whole-client missing-model count. Next:
trace each extra model into its construction/action/render and ownership path
before adding a composite native actor. The native opener currently ports the
action rules but does not execute these secondary loads, as section 1 records.

## 11. Construction census and composite town NPCs, RENDER-ACTORS-004

The [class census](actor-construction-census.csv) enumerates all 1,024 class
selectors accepted by authored monster fixtures. It records the executed
constructor or unresolved processor, model, opener, construction category and
native status for each selector. This is a bounded construction census. It
retains section 4's world-0/rand-0 and declining-map-processor assumptions;
no server placements, spawnability or event state are inferred. The current
constructor recorder includes the class-257 joint service added after the old
section-4 extraction. It resolves 963 classes and leaves 61 original contexts
unresolved. The current class table likewise has 963 rows. The historical
949-row result in section 4 is not the current denominator.

"Correct bounded body plan" means the separately checked ACTORS-001..004 body
plan. "Incomplete/unverified special passes" includes generic body admissions
whose complete RenderCharacter special behavior has not been proved. A plain
construction path does not certify the absence of later special rendering.
Six of those 61 contexts have separate EffectManager recipes in
`effect_class_table.h`, which the native world loader resolves before the core
class table. Their native overrides are named in the CSV. "Refused" includes
the other 55 unresolved contexts, 13 no-opener classes, eight NPC indices without
recovered file registrations and four ACTORS-003 recipes.
These conservative categories prevent an opener inventory from becoming a
whole-client visual-equivalence claim.

| Native world body classification | Before ACTORS-004 | After |
|---|---:|---:|
| Checked bounded body plan | 28 | 33 |
| Incomplete or unverified special passes | 916 | 911 |
| Refused by the loader | 80 | 80 |
| Fixture selector contexts | 1,024 | 1,024 |

Repeated/default selectors remain in this denominator. It is not a count of
unique registered creatures. Construction tags overlap: 768 plain body paths,
144 equipment/part constructors, 56 special-appearance paths, 55 unresolved
construction paths, 44 startup/no-opener paths, nine secondary-model class
contexts, 14 extra-bitmap contexts, four auxiliary/action contexts, two
companions and two excluded transformed-player action hooks. The CSV and its
named sources define each category; these counts must not be summed.

`scripts/actor_census.py` also enumerates all 601 OpenMonsterModel selectors and
147 OpenNpc selectors in the [opener inventory](actor-opener-census.csv). Monster selectors complete with 16 synthetic actions.
Eight NPC selectors stop on undeclared per-mesh state, as section 5 records.
Secondary-model and sound/bitmap-loader counts describe calls to named services,
not decoded resources or implemented consumers. All inputs use the shared
`Pin.read` hashes identified above.

### The five-class composite group

OpenNpc's first three branches, starting at `0x01808ab5`, register the Female,
Man and Girl skeletons, then their interleaved two-variant part models. The
executed original loader records 22 secondary AccessModel calls. CreateMonster
selects these parts in the following authored fixture classes:

| Class | Skeleton | Selected part models, in original descending draw order |
|---|---|---|
| 230 | Man01, `0x9ff` | `0xa1d`, `0xa1c`, `0xa1a`, `0xa17` |
| 248 | Man01, `0x9ff` | `0xa1e`, `0xa1c`, `0xa1a`, `0xa18` |
| 250 | Man01, `0x9ff` | `0xa1d`, `0xa1b`, `0xa19`, `0xa17` |
| 253 | Girl01, `0xa00` | `0xa23`, `0xa21`, `0xa1f` |
| 255 | Female01, `0x9fe` | `0xa16`, `0xa12`, `0xa10`, `0xa0e` |

Each constructor retains default object kind 1 and class byte zero, scale 0.9,
level/option/ext zero. The constructor reference supplies CreateCharacter's proved default kind 1
and checks that the generic branch retains it. It does not assume town kind 4. The original RenderCharacter caller
executes from entry with authored alpha, frames, actions and world contexts.
RenderObject is a named base-body/pose recorder, and stateful world services
decline explicitly. The recorded part calls match the native recipe in order;
the generic RenderObjDraw stream for all 15 selected distinct models is compared
separately. This does not prove original temporal or pixel equivalence.

Native admission uses the existing `mu_character` shared-pose mechanism with
the corresponding NPC skeleton instead of Player. OpenNpc's recovered action
speeds remain on the normal `mu_actor` animation object. Its frame/prior state
feeds the composite skeleton; selected parts skin against those posed bones.
The native host requires a zero-mesh base, nonempty selected geometry, zero
missing textures, advancing matching animation frames and the requested alpha.
It checks actual selected filenames. Unselected global variants need no
per-instance load. The original root-only shadow call has no base meshes;
new composite parts do not inherit the Player armour shadow pass.

The five recipes are the largest class group in the audited secondary-opener
set. The demo placement source explicitly names Female/Man/Girl assembly as
missing. All three skeleton families use an authored world-0 town fixture here. No
canonical placement is added by this lane. The nine monster openers in
section 10 remain action/debris/effect leads. In the extracted class table only
type 226 has classes, 595 and 635; neither appears in the shipped demo placement.
Loading those extra models alone would not supply their missing behavior.

### Limits

Classes 374/642 still need companion lifetime, 378 needs cloth/aura and 617
needs an exact startup file. The five new NPCs do not relax those refusals.
Generic walking, head/weapon links, buff-driven appearance, fade/shadow parity,
world-specific override state and complete special-pass fidelity remain
separate from the proved constructor and part draw plans. The opener inventory
must not be used as a total count of complete native actors.

The composite admission is in the world actor loader. The standalone
`mu-render actor` command retains its earlier base-model-only behavior. Use
authored world fixtures for these five assembled NPCs.
