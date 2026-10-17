# Character assembly (NATIVE-CHAR-001)

This milestone adds a character mode to the native viewer ([`native/`](../../native/README.md)). The mode renders a player the way the client assembles one:

- the shared `Player.bmd` skeleton;
- the class body parts (helm, armor, pants, gloves, boots) for a class byte;
- weapons, a shield and a wing attached to Player bones through the client's keep-root path;
- the client's player animation actions.

The small client routines involved are reconstructed in C and compared with the actual instructions under Unicorn. That includes complete installed chains: `Player.bmd` pose, then parts and items. The surrounding render flow is a static reading. This is still a viewer, not a client.

## Identity

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Installed `Data/Player/Player.bmd` (v15, 60 bones, 390 actions, no meshes) | `f2f6f1a02ef44d301ea9921e006b5ec5e0a25bd83a77e9d899be38fcaeff5449` |

Bodies that were executed, pinned by `scripts/validate_character.py`:

| Routine | Range | SHA-256 |
|---|---|---|
| Rotation position (root setter), `ret 0xc` | `0x012b7019..0x012b70f2` | `29fece51…903e4e` |
| Transform position, `ret 0x10` | `0x012b6ef1..0x012b7019` | `54265467…88f9f0` |
| Skin index | `0x0139d6a2..0x0139d6da` | `4f90c1b6…0f32d1` |
| Class tier | `0x0139cb8a..0x0139cbe1` | `7d062901…51eee` |
| Tier-2 skip | `0x0139d89f..0x0139d8ea` | `295cb25d…bd1653` |
| Class nibble | `0x0095f5cc..0x0095f5d7` | `0ccb64b4…64df46` |
| Player/part loader prefix | `0x01830aa6..0x01830ee2` | `b95847b1…37c7b4b8` |

Bodies pinned for the static reading only (not executed):

- the character copy render `0x0139be7a..0x0139ca62`;
- part types `0x01395473`;
- AccessModel `0x018202b4`;
- character creation `0x0137d8a1`;
- owner bone `0x0129f12c`.

The full digests are in the validator.

## Recovered flow (static reading unless marked)

### Model loading

- **Player model.** `0x01830aa6` loads `Player.bmd` as model 0xa91 through AccessModel `0x018202b4(type, dir, name, index)`. It reports "Player.bmd file error" unless the model has no meshes and exactly 390 (0x186) actions. AccessModel builds the file name as `%s.bmd` (index -1), `%s0%d.bmd` (index below 10) or `%s%d.bmd`.
- **Part models (executed).** The loader then runs `i = 0..15` and loads five part types:

  | Part | Model type | File |
  |---|---|---|
  | Helm | `0x3700+i` | `HelmClass` + (i+1) |
  | Armor | `0x3750+i` | `ArmorClass` + (i+1) |
  | Pants | `0x37a0+i` | `PantClass` + (i+1) |
  | Gloves | `0x37f0+i` | `GloveClass` + (i+1) |
  | Boots | `0x3840+i` | `BootClass` + (i+1) |

  It repeats this at +0x10, +0x20, +0x30 and +0x40 for tiers 2 to 5, using the names `…Class2`, `…Class3`, `…Class4` and `…Class4` again. Tier 2 is skipped when `0x0139d89f` returns 1, for base classes 3, 4, 6 and 7.
- **Lookup.** Models live in a map keyed by type; `0x00966cc4` → `0x00eaa8cf(type)`.
- **Item files.** Item model files (type `0xae6 + group*512 + index`) are named by the runtime item table (`0x00cd558e`, "ItemModelFile does not exist"), not by code. The viewer therefore takes item files as explicit paths.

### Classes and part types (executed)

- A class byte holds the base class in its low nibble (`0x0095f5cc`, `& 0xf`) and evolution flags in its high nibble.
- The tier is 1 when the high nibble is zero. Otherwise it is 2 plus the index of the highest set bit (`0x0139cb8a`).
- The skin index is `base + 16*(tier-1)` as a byte (`0x0139d6a2`).
- `0x01395473` and the equipment decoder `0x01394870` give each body part the type `base + skin`. A filled inventory slot gives `0xae6 + item` instead.

### Character record (static)

| Offset | Field |
|---|---|
| `+0x12` | class byte |
| `+0x1c4` | BodyPart[6], 0x3fc bytes each; slots 1..5 are helm..boots |
| `+0x19ac` | Weapon[2] |
| `+0x21a4` | Wing |
| `+0x299c` | Helper |
| `+0x3254` | the object |

A part record holds:

- the int16 type at `+0`;
- level `+2`, option `+3`, extra option `+4`;
- link bone `+5`;
- action `+6`, prior action `+8`;
- frame `+0xc`, prior frame `+0x10`, speed `+0x14`;
- an object at `+0x24`.

Object fields:

| Offset | Field |
|---|---|
| `+0x5c` | type |
| `+0x2a` / `+0x2c` | action / prior action |
| `+0xa0` | scale |
| `+0xd0` / `+0xd4` | frame / prior frame |
| `+0xdc` | alpha |
| `+0x158` | position |
| `+0x164` | angles |
| `+0x170` | head angles |
| `+0x318` | own bone-matrix array |

Creation (`0x0137d8a1`) sets:

- scale 0.9 (`0x0137d9dd`);
- alpha 1, light enable 1, own-bone flag 1;
- every part type to -1.

For Player-type characters it sets weapon link bones **33** (Weapon[0], `0x0137f5d9`) and **42** (Weapon[1], `0x0137f5ec`). These are the `Player.bmd` bones "knife_gdf" (child of "Bip01 R Hand") and "hand_bofdgne01" (child of "Bip01 L Hand"). `0x0139db9a` gives the wing and carried weapons link bone **47**.

### Character copy render `0x0139be7a`

This is a compact character render (called from `0x00a49e9c` and others). The native assembly follows it:

1. **Player pose.** The Player model takes the object's action and is posed into the shared bone buffer `0x06fce398` with keep-root 0 and translate 0.
2. **Body parts.** For slots 5..0, each part model copies the object's light-enable and scale. It is skinned by the transform `0x012b5bde` against that shared buffer, with translate 1, vertex scale 0 and light arguments 0.4/0.8/0.2 (binary32 `0x01a7df0c`, `0x01a7df18`, `0x01a7df08`). Part models are never posed; they reuse the Player's matrices.
3. **Weapons 0 and 1.** For each:
   - the rotation position `0x012b7019` runs on the Player model with `0x06fce398 + link*0x30` (the shared buffer as it is at that moment) and vector (0,0,0);
   - the item's origin is the position plus the result;
   - the item is posed at frame 0 (prior 0, prior action 0, zero angles) with keep-root 1 and translate 1 into the same buffer;
   - it is then skinned with the same light arguments and drawn through `0x00966def`.
4. **Wing.** It follows the same steps with vector (0,0,15) and frame 2. Character subtypes 0x5bc and 0x5bd use (0,-10,-140).

### In-world render (static, consistent with the above)

The world render `0x01363260` uses the per-object path:

- **Skeleton.** `0x017edd1d` poses the Player with keep-root 0 into the object's own matrices when object `+0xd` is set. The translate argument is inverted from the caller's flag.
- **Body parts.** The body-part loop (slots 5..0, `0x0136a374`) calls RenderPartObject `0x017e63f4`. It transforms with the object's matrices (or `0x06fce398` when its global flag is set), the object's scale and position, translate on and the same light arguments. Its selection pass sets bone scale 1.2/1.4.
- **Weapons.** Weapons in hand go through `0x012bd910` with link 0. The generic path at `0x012c5b3c` runs the rotation position on the owner bone with (0,0,0), then a keep-root pose with translate 1 (`0x012c6478`), then the transform (`0x012c67fc`). It forces the item model's lighting flag to 0 (`0x012bdb19`) and draws through `0x0176ce74`.
- **Exceptions.** Items with table attributes 0x54, 0x59 or 0x72 take special branches. One of them uses offsets (∓6,-4,2) on bones 33/42. In safe zones `0x0139db9a` draws the weapons on the back with fixed per-type local matrices, and the hand loop is skipped (`0x0136b02e`).

The parts' math is the same as in the copy render: the same matrices, the same transform and the same arguments. The weapon path differs in that the Player bones stay in the object array instead of the shared buffer, and in the item lighting flag.

## Authored source

`reconstructed/model-codec/character.{c,h}`, built as `libcharacter` together with the skinning stack:

- `mu_rotation_position` and `mu_transform_position` over `mu_client_memory` views. They keep the original read order, store order and aliasing.
- `mu_character_class_tier`, `mu_character_skin_index`, `mu_character_skips_tier2`, `mu_character_part_type` and `mu_character_part_file`.

`native/core/mu_character.{c,h}` assembles a character from `mu_model` instances. They share one bone, root and quaternion storage, standing in for the client globals, so later poses overwrite earlier bones exactly as in `0x0139be7a`.

## Verification

`scripts/validate_character.py` reuses the skinning, pose and bone-track validators' Unicorn machines. It uses the same boundaries: no stubs, any undefined or undeclared read stops a case, and callee-saved registers, ESP, DF, FPCW, MXCSR and x87 TOP are checked.

| Comparison | Cases | Matches |
|---|---:|---:|
| Rotation/transform position, synthetic, including aliased out/vector/matrix/root and null matrices | 384 | 384 |
| Skin index / tier / tier-2 skip, all class bytes (garbage upper argument bits) | 3 × 256 | all |
| Loader body-part loop `0x01830b79..0x01830ec9` (AccessModel replaced by a recorder; `0x0139d89f` runs as client code) | 380 calls | all types and names; 80/60/80/80/80 per tier |
| Installed Player poses (same action, blend, wrap, integer frame) | 4 | 4 |
| Installed class parts skinned against the actual Player matrices | 300 models | 300 (84,351 vertices, 95,310 normals) |
| Installed weapon/shield/staff/bow items: actual root setter on bone 33/42 → actual keep-root builder → actual transform | 267 | 267 (141,767 vertices) |
| Root-setter outputs in those chains | 267 | 267 |

The negative control is a rotation position without the body scale. It differs in 40 of 40 cases.

Report `evidence/native-char/character-full-02.json` (ignored), SHA-256 `bca220a3…94ae3b`. The authored library is `1764b49d…71499`. The run took 90 s on one core. An earlier identical run is kept as `character-full-01.json`.

Native golden data (`native/tests/test_native_character.py`, `character_reference.py`):

- **Reference.** An independent harness builds client memory through the validators' case builders. It runs the authored libraries and checks every pose and transform against the validators' Python models. Its layout and order of shared-buffer use differ from `mu_character.c`.
- **Portable (CI).** `mu-render chardump` is byte-identical in 18 cases: 2 synthetic characters × 3 item sets × 3 states. A character is a v15 Player with dummies, v10 parts, and v12 weapons and wing. The states cover ticks, blends, angles, head angles, scale, lighting off and wing scale.
  - Negative control: a reference with no keep-root differs.
  - Character renders are deterministic.
  - Headless GL agrees with the software renderer.
- **Private.** The installed `Player.bmd` was run with the class parts of classes 0x00, 0x01, 0x02, 0x11 and 0x23. Items: Sword01/Shield01, Staff01, Axe03/Shield05, Spear02 with Wing04, and Bow01 (left hand). The output is byte-identical to the reference. An installed DK render finds every texture.

## Local renders

These are in `~/Documents/mu-mac-tools/native/renders/char/` and are not committed:

- `dw-staff-a10.png`: Dark Wizard, action 10, staff;
- `dk-sword-shield-a4.png`: Dark Knight, action 4, sword and shield;
- `elf-bow-a8.png`: Elf, action 8, bow in the left hand;
- `bk-tier2-wing.png`: class 0x11 tier-2 parts, sword, Wing04, rendered with `--cull 0`;
- `dk-walk-ticks.png`: action 15 after 7 ticks;
- `armor-items.png`: item armour set HelmMale05..BootMale05 and Axe03;
- `contact-sheet.png`;
- `dw-gl.png`: headless GL, `--compare`: 3 pixels > 8/255;
- `viewer-window.png`: the windowed viewer; about 100 fps with vsync over 3 s.

## Not established (gaps)

- **Action names.** The stand action per weapon type (`SetPlayerStop`-style code) is untraced. Actions are chosen by index. The pattern 4 = sword stand, 8 = bow, 10 = staff fits the renders and a known MU enum ordering; that is an inference.
- **Weapons in hand in the world path.** Not implemented:
  - item lighting flag 0 and drawing through `0x0176ce74`;
  - per-part animation state, including the client's choice of weapon actions and speeds per character action;
  - the 0x54/0x59/0x72 attribute branches;
  - back-carried weapons in safe zones.

  The item table that maps item numbers to files is runtime data, so item files are given by path.
- **Body light and draw state.** The body light colour (`0x017ec3d8`, from terrain light) is a viewer constant of 1. Draw mode and state follow the viewer's static reading. Wings with alpha textures need `--cull 0` to look right, which reflects the unresolved cull state.
- **Head slot and accessories.** Body-part slot 0 (the head) and the helper, pets, cloaks and effects (the large per-item effect code in `0x012bd910`) are not rendered.
- **Not executed.** The render routines themselves (`0x0139be7a`, `0x01363260`, `0x012bd910`, `0x017e63f4`) were not run. Only the routines they call were compared.
