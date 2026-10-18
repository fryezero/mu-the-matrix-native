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
