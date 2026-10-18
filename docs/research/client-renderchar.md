# In-world character and item render (NATIVE-RENDERCHAR-001)

This milestone recovers the client's world render of characters and their
items, which [native-character.md](native-character.md) had read statically:

- RenderCharacter `0x01363260` and the order of its calls;
- RenderPartObject `0x017e63f4` and the item render RenderObjDraw
  `0x0176ce74`, including the item level glow, excellent and ancient passes;
- the link render RenderLinkItem `0x012bd910` for weapons, wings and
  attachments, in the hand and in link (back-carry) mode;
- BackCarry `0x0139db9a`;
- the +15 armour attachments (`0x016d53a4`, models `class15_*`);
- the weapon link bones monsters get;
- where character shadows are drawn.

It closes the "live callers" gap of
[client-meshdraw-exec.md](client-meshdraw-exec.md): the flags, alpha, blend
arguments, texture overrides and model fields the game actually passes to the
mesh draw for items and characters.

The decisions are reconstructed in C (`reconstructed/renderchar`). They are
compared with the client's instructions executed under Unicorn
(`scripts/validate_renderchar.py`). `mu-render` draws them through the
mesh-draw port with `--world-render`.

Labels:

- **verified**: authored C compared with the executed client code;
- **extracted**: tables produced by executing client code, without an authored
  reimplementation of the code that produced them;
- **static**: a reading of the instructions that was not executed;
- **inference**: a name or interpretation.

The executed bodies are pinned by SHA-256 in the validator's report. The
inputs are the restored text capture09 (`2bd5f2e9…3724`), the second section
run10 (`c985e2e6…672f`), the trig dispatch flag and the math feature word, as
in [client-meshdraw-exec.md](client-meshdraw-exec.md).

## How the routines were executed

`scripts/renderchar_machine.py` runs client code on the pinned image. These
routines touch hundreds of engine globals, so the memory model differs from
the earlier validators:

- Case regions hold the models, the object, the character record and the item
  records.
- The image's uninitialised data (`0x01ced000..0x0c000000`) is zero on first
  touch. Every page touched is listed in the report. This is the state of a
  freshly loaded image.
- MSVC thread-safe statics construct themselves. The TLS init epoch starts at
  `INT_MIN`, as in the CRT. `_Init_thread_header`/`_footer` have
  single-thread replacements, malloc is a bump allocator, and free and atexit
  do nothing. So singletons such as the ancient set manager `0x01d1dcc0` are
  built by the client's own constructors.
- The item render registry `0x01ec8db0` gets an empty `std::map` (head node
  linked to itself).
- The engine services listed in the validator's `SERVICES` are replaced by
  recorders:
  - model container and lookup;
  - the default-buffer transform, body and mesh wrappers `0x00966ea5`,
    `0x00966def` and `0x00966e4a`, recorded with the model fields at each
    call;
  - item table find and kind predicates (`0x00cd5d29`, `0x00cd6017`,
    `0x00cd5fac`, `0x00cd5f41`), answered from the case records;
  - `rand` (returns 0);
  - effect creation;
  - the EnchantEffect lookups `0x010ffd7a`, `0x010ffd25` and `0x010ffddb`;
  - bitmap, model and texture loaders;
  - bitmap lookups, as misses;
  - OpenGL imports;
  - the two calls BackCarry makes outside the restored text (`0x10b223b0`,
    `0x10b22740`), recorded and treated as opaque.
- For whole-character runs, a few subsystems are skipped and recorded:
  - name and effect managers (`0x00ea3692`, `0x00ea3cae`, `0x00a0b4ba`,
    `0x0129f671`);
  - the character effect emitters `0x01362f24` and `0x01363098`, which draw
    GL sprites directly, not through the mesh draw;
  - sound `0x00a6ac96`;
  - the helper/pet pass `0x01378d9c`.

Static readings came from a headless Ghidra 12.1 decompilation of the raw image
(scratch, not committed) and from disassembly.

## 1. RenderCharacter call plan (verified)

For a Player character (model `0xa91`, object kind 1) the client calls, in this order:

1. **Shadow.** It sets object `+4` to 1, calls
   `RenderPartObject(object, 0xa92, NULL, light, alpha, 0, 0, 0, 0, 0, translate, 0, 2, -1, -1, 0)`,
   and then clears `+4` again. The shadow is drawn when the object alpha is at
   least 0.5, the character byte `+0xf` is 0, the world is not 10 or 0x84, and
   a world predicate `0x009b0418` is false. Monsters use their own model index
   (`0x01363ad2`).
2. **Body parts.** Slots 5..0 (`0x0136a374`), for each part whose type is not -1:
   `RenderPartObject(object, type, part, character light +0x1b8, alpha, level<<3, option != 0, ext, 0, 0, translate, select, 2, -1, -1, 0)`.
   - Class 5 substitutes types for item groups 7..11, indices 10/11.
   - Class 6 maps types through the registry.
   - Monster classes for which `0x0139bcdc` is true pass render type 0x40042.
3. **+15 attachments** (`0x016d53a4`). This step runs only for parts at level 15:

   | Slot | Attachments (link bone, model, file) |
   |---|---|
   | helm | 20, `0xa9f` `class15_head` |
   | armor | 35, `0xa9b` `class15_bodyleft`; 26, `0xa9c` `class15_bodyright` |
   | pants | 3, `0xaa0` `class15_pantleft`; 10, `0xaa1` `class15_pantright` |
   | gloves | 36, `0xa99` `class15_armleft`; 27, `0xa9a` `class15_armright` |
   | boots | 4, `0xa9d` `class15_bootleft`; 11, `0xa9e` `class15_bootright` |

   Each attachment is drawn with `RenderLinkItem(0,0,0, c, part, model, 0, 0, link 1, 1, 0, 1)`.
   The part's link byte keeps the bone afterwards. Weapons at level 15 only
   spawn particles. The models are loaded at startup from `Data\Item\`
   (`0x0183243f..`).
4. **BackCarry** (`0x0139db9a`). Its zone flag is set when:
   - the safe-zone byte (character `+4`) is set and weapon 0 is not `0xb0f`; or
   - the action is in `0x148..0x167`.

   World predicates clear it. Weapons are then drawn on the back:
   - **Plain weapons** (types `0xae6..0x18e5` without kind B 0x0e, or a bow in
     slot 0) use `RenderLinkItem(0,0,15, …, link 1, translate, 0, right)` with
     link bone 47. The part animation is reset (action 0, frame 0, speed 0)
     and restored after the call. `right` is 1 for slot 0; kind B 10 forces 1
     and kind 8 forces 0.
   - **Kind B 0x59** uses (26,20,25) and bone 17.
   - **Kind B 0x5a** uses (26,20,25) and bone 33.
   - **Kind B 0x72** uses (26,20,25) and bone 42.
   - The crossbow list and `0x1100`/`0x151e`/`0xf30` set their own actions and
     speeds.

   **BackCarry returns the zone flag, not "carried"** (`0x0139f2d9`). Inside a
   safe zone the hand loop is therefore skipped even for weapons that were not
   drawn on the back.
5. **Wing.** `RenderLinkItem(0,0,15, c, wing, type, level, option, 0, translate, 0, 1)`
   draws the wing, with link bone 47. The speed comes from `0x0139fd02`:
   0.25 for normal actions and 1.0 for the flying actions `0x59..0x5f`, with
   per-type exceptions.
6. **Hand weapons** (`0x0136b4b7`). This step is skipped when the zone flag is set.

   Skipped weapons:
   - slot 0 during action 0x8f up to frame 4;
   - types `0x12ed`, `0x12f5` and `0x24eb`;
   - weapons with kind B 0x4b.

   The others are drawn with `RenderLinkItem(0,0,0, c, part, type, level, option, 0, translate, 0, 1)`
   after the part animation is set (§3).

The C plan `mu_rc_character_plan` reproduces this order and every argument,
including the part fields at each link call (link bone, action, speed, frame,
prior frame). Its domain:

- the Player model in a generic world (0);
- class nibbles other than 4, 5, 6 and 13;
- classic wings `0x22e6..0x22ec`;
- not action 0x8f.

Monsters (verified in single runs, §6) draw their body through RenderObject
`0x016d4fe4`, then the shadow, then their weapons through the same hand loop.

## 2. RenderPartObject and RenderObjDraw (verified)

**RenderPartObject `0x017e63f4`** copies fields from the object into the item model:

| Object field | Model field |
|---|---|
| scale `+0xa0` | `+0x74` |
| `+0xe` | `+0x51` |
| `+5` | `+0x50` |
| position | `+0x78` |
| hide-skin argument | `+0xa5` |

It then sets the bone scale `0x01cf104c` from `select`:

| `select` | Bone scale |
|---|---|
| 0 | 1 |
| 2 | 1.2 |
| 3 | 1.4 |
| 1 | the outline colours (0.1, 0.03, 0) / (0.7, 0.2, 0), or (0.02, 0.1, 0) / (0.16, 0.7, 0) for kind 4 |

Next it transforms with the object's bones `+0x318`, or the shared buffer for
global transform. The transform arguments are light 0.4/0.8/0.2, translate,
and the part's `+0xc4`. Finally it calls
`RenderObjDraw(object, type, light, alpha, itemlevel, option1, ext, select, rendertype, a14, a15, 3, a16)`.

**RenderLinkItem `0x012bd910`** draws the item through `RenderObjDraw` with
render type 2 (verified). It clears the item model's lighting flag `+0x50`
(`0x012bdb19`).

**RenderObjDraw.** The glow level is `(itemlevel >> 3) & 15`.

- It is 0 when the render type has bit 0x400.
- It is 9 when the item record's kind B is 0x26 or 0x5b.
- It is capped at `2q + 5` when the graphics option `q = [[0x01d22c7c]+0x2c] ≤ 4`
  (`0x0176dc78`).

With object `+4 == 1` it draws the shadow instead (§5).

For an item type with no type-specific branch, the passes are the ones below.
`L` is the character light, `p` a binary32 sine pulse, and `B(f, a)` the body
call `RenderBody(flags f, alpha a, object +0x74, +0xa8, +0xac, +0xb0, hidden -1, texture -1)`.

| Level | Passes (model fields written first) |
|---|---|
| 0..2 | +0x40 = 0, +0x44 = L, +0x54 = L; B(rendertype, alpha) |
| 3..4 | p = sin(t·0.004)·0.15 + 0.6; +0x54 = (p, 0.6p, 0.6p)·L, +0xca = 1 during the body, B(rendertype, alpha) |
| 5..6 | +0x54 = (0.5p, 0.7p, p)·L, +0xca = 1; B(rendertype, alpha) |
| 7..8 (q > 0) | +0x54 = 0.8L; B(rendertype); +0x40 = level; BodyColor2(0x44) |
| 9..10 (q > 1) | +0x54 = 0.9L; B(rendertype); +0x40 = level; BodyColor2(0x44), BodyColor2(0x48) |
| 11..12 (q > 2) | +0x54 = 0.9L; B(rendertype); +0x40 = level; BodyColor(0x240), BodyColor2(0x48), BodyColor2(0x44) |
| 13..15 (q > 3) | as 11..12 with BodyColor(0x1040) after 0x240 |

In those passes:

- **BodyColor2 `0x016dc148`** sets `+0x54` through PartObjectColor `0x016db5eb`
  and draws `B(flags, alpha)`. The colour is alpha × the EnchantEffect colour
  of the type. Kind B 0x26 gives (alpha, 0.5·alpha, 0) (orange); kind B 0x5b
  gives (0, 0.5·alpha, alpha) (blue).
- **BodyColor `0x016dec15`** scales `+0x54` by PartObjectColor2 `0x016dba54`.
  The factor is 1, except for armour indices listed in the C (×(1,0.5,0),
  ×(0,0.5,1) or white). It draws with alpha 1.
- Flag 0x100 of the render type is kept on the 0x44/0x48/0x240/0x1040 passes
  of levels 9 and up.

The table only lists passes. The draw modes come from the mesh-draw port:

| Flags | Mode |
|---|---|
| 0x44 | chrome + bright |
| 0x48 | metal + bright |
| 0x240 | chrome2 + bright |
| 0x1040 | chrome4 + bright |
| 0x42 | textured bright |
| 0x840 | chrome3 + bright |

**Tail `0x017e2c87`.** It does nothing when the quality is 0 or the object has buff 0x39, 0x12 or 0x41.

- **Excellent.** The pass is drawn when option1 is exactly 1, `a13 == 0`, the
  type is above `0xae5` (or `0xace`/`0xacf`/`0xad0`), and the record's kind A
  is not 6. It uses p = sin(t·0.002)·0.5 + 0.5, `+0x54 = (p, 0.3p, 1 − p)`
  and `B(0x42, 1.0)`. Excellent and ancient are exclusive.
- **Ancient.** The tier comes from `0x009e072d(ext)`: bit 1 gives 1, bit 2
  gives 2, 0x10 gives 3 and 0x20 gives 4. The pass needs an item record whose
  type `+0x252` is not 4. It is `BodyColor(0x840, alpha = sin(t·0.001)·0.5 + 0.4)`;
  armour groups 7..11 colour it through `0x01806042`.

**RenderPartObjectBody `0x016e036c`.** With `a14` and `a15` both not -1, the
body hides mesh `a14` and a single mesh pass draws it with texture `a15`.

**+15 attachments.** Models `0xa99..0xaa1` draw three passes on mesh 0
(`0x016fc8f1`):

- `(0x42, bml k − 0.1)`;
- `(0x42, bml k − 0.3, u = |sin(t·0.0005)|, texture 0x80d4)`;
- `(0x1002)`.

Here `k = 0.8 − |0.5·sin(t·0.0018)|`.

Type-specific branches exist for 1,674 of the 8,192 item types, plus 17 class
part types. They are classified by execution (§4) and refused by the library.

## 3. Part animation and link geometry (verified / extracted)

**Hand path.** The rotation position `0x012b7019` runs on the Player model
with the part's link bone and (x, y, z). The item origin is the object
position plus the result, the item angles are 0, and the item is ticked with
the part's speed. Then come the keep-root pose (translate 1), the transform,
and RenderObjDraw.

**Hand weapon animation.** The weapon's action and speed are set before the
link call (`0x0136b4b7..`):

| Weapon | Action | Speed |
|---|---|---|
| bow actions `0x7e..0x81`, `0x107` | 1 for crossbows, else 0 | Player action 0x7e |
| swords `0xae6..0xce5` | 0 | Player action 1 |
| `0xee8` | per action | per action |
| `0xeeb` | | 2 × Player action 1 |
| `0x14ec` | | 15 × Player action 1 |
| `0xb09` | frame-gated | |

A list of about 60 types has constant speeds. The remaining kinds:

- kind B 0x59: action 1 at 0.25, or action 2 at 0.4 during attacks;
- kind B 0x5a and 0x72: speed 0.1;
- anything else: speed 0 and frame 0.

**Link (back-carry) path.**

- The root matrix `0x078965ac` is `concat(owner bone[link], local)`, computed
  by the pose concat `0x00cff83e` (verified as `mu_pose_concat`). For some
  entries the local matrix itself is used without the bone.
- The origin is the object position.
- The local matrix comes from a chain of `AngleMatrix(angles) + translation`
  per type, kind B (0x0b, 0x4b, 0x54, 0x59, 0x5a, 0x72, 0x73, 0x7b) and right
  hand, from `0x012bdc0b` to `0x012c2ac3`. The left hand composes an extra
  rotation (145, 0, 275) + (0, 10, −30) in place. Because the output aliases
  the input, the result is not orthonormal.
- The chain is **extracted** (`back_matrices.h`): RenderLinkItem was executed
  for every weapon type of groups 0..6 and for the +15 attachments, each kind
  and both hands, once with identity bones and once with a general bone that
  decides concat versus absolute.
- The C composes the extracted local under the caller's bone.

**Monster weapon link bones (extracted).** The character create `0x0137d8a1`
assigns the weapon link bones per model index in its switch
`0x0137eefc..0x0137f5f4`, which was executed for model indices
`0x7a5..0xa91`. The result is `link_bones.h`: 749 model indices, 748 of them
written. The Player gets 33/42; monster 0x7a5 gets 42/33.

## 4. Verification

The numbers below are from single local private runs of `scripts/validate_renderchar.py`. They need the
restored client text, so CI does not run them. CI runs the portable worked examples
(`reconstructed/renderchar/test_renderchar.py`) and the native synthetic tests.

| Comparison | Cases | Matches |
|---|---:|---:|
| RenderObjDraw, random cases on generic types (all levels, option/ext bytes, render types, quality 0..9, alpha, light, object fields, time up to 2·10^6 ms, item records and kinds) | 16,150 compared (20,000 drawn, 3,850 outside the domain) | 16,150 |
| Classification: types whose stream differs in any of 11 configurations | 8,192 items + 512 part skins | 1,674 + 17 type-specific |
| Record-kind sweep (all 256 values of kind A, kind B and type on 32 generic types) | 768 values | mismatches only where the library refuses: kind A 0x1f, 0x22, 0x24..0x2b; kind B 0x27, 0x4b, 0x72; type 4, 8, 0x0b |
| Back-carry roots: client root vs `concat(bone, extracted local)` with random bones | 1,000 (sampled keys) + 45 (+15 attachments) | 1,000 + 45 |
| RenderCharacter plans (random classes, actions, safe zone, parts, levels, weapons including special types and kinds, wings) | 252 | 252 |
| Weapon link bones extracted | 749 model indices | 749 executed to the join |

**Negative controls.** On 300 matching cases, the C with one input changed
differs from the client in this many cases: level − 1 step (item level − 8):
89; time + 1000 ms: 184; quality − 1: 111; excellent flag flipped: 205.

**Run time.** The full items, kinds and classification run took 39 minutes on this Mac. The full
back-carry extraction (3,593 types × 9 kinds × 2 hands, two bones each) took
about 25 minutes. Reports are in the ignored scratch area
(`native/scratch/renderchar/reports`).

**Exactness.** Every float is compared as a bit pattern. The sine pulses use
the CRT sine `0x009681bd` rounded to binary32, as in the mesh-draw port. No
case disagreed.

**Domain.** The library refuses the following inputs:

- `select ≠ 0`, the outline passes;
- the shadow pass;
- `a13 = 1`;
- items whose record type is 4, 8 or 0x0b, or whose kind A/B is in the list above;
- the type-specific types.

The native viewer draws those with one plain textured pass and counts them.

## 5. Shadows (static, partly executed)

Character shadows are drawn in RenderCharacter (§1) through RenderPartObject
with object `+4 = 1`. RenderObjDraw then takes its shadow path
(`0x0176cfb2`):

- **Blend and colour.** In the worlds of predicate `0x016a88ae` it uses blend
  wrapper `0x0184a990` and `glColor4f(0, 0, 0, 0.2)`; otherwise blend off and
  `glColor3f(0, 0, 0)`.
- **Shadow body.** When the shadow is enabled (`0x009b0418`, world 10/0x84,
  object `+0x44` and the event-map checks), RenderBodyShadow `0x012bc07a`
  runs on the model with object `+0x74` and a mesh-hide value. That value is
  object `+0x68`; 2 for model `0x819`, 0 for `0x849`, and -1 when `0x01807c1f`
  holds.
- **Projection.** RenderBodyShadow projects the transformed vertices itself:
  `glBegin`, `glVertex3fv` per triangle, `glEnd`, with depth mask off, alpha
  test, and push/pop matrix. It does not use the mesh draw. It was not
  reconstructed; the native world mode draws no shadow.

## 6. Native module and tool

- `reconstructed/renderchar` builds `librenderchar`. It provides:
  - `mu_rc_item_draws` and `mu_rc_item_glow_level`;
  - `mu_rc_back_local` and `mu_rc_back_root`;
  - `mu_rc_character_plan`;
  - the generated tables `special_types.h`, `back_matrices.h` and `link_bones.h`.
- `native/core/mu_renderchar` draws an item's passes through `mu_scene`. It
  also attaches items to a host model by the hand path or by link mode.
- `mu_scene` gained two optional draw options, `mesh_plus_one` (the RenderMesh
  single-mesh entry) and `fields` (the model fields of a pass). Zero keeps the
  previous behaviour.
- `mu_character` gained two additive hooks:
  - `mu_character_set_carry`: a link-mode root for a weapon slot;
  - `params.world_items`: the world path clears the item lighting flag.

  The copy-render output and `chardump` are unchanged.
- `mu-render character … --world-render` draws the world passes. Its options:
  - `--item-level SLOT=L` (`all`, `helm`, …, `weapon0`, `weapon1`, `wing`);
  - `--excellent SLOT=1`, `--ancient SLOT=BITS`;
  - `--item-type SLOT=TYPE`, `--kind-a`, `--kind-b`, `--item-kind`;
  - `--quality Q`, `--world-time MS`;
  - `--glow-color R,G,B`;
  - `--safe-zone` (back carry);
  - `--attachments` (+15 models).
- `mu-render actor … --world-render --actor-weapon N=PATH` attaches monster weapons
  with the extracted link bones.

Viewer choices:

- **Item types without `--item-type`.** They come from the standard file names
  (Sword01 → `0xae6`, ArmorMale10 → group 8, …). The client takes them from
  its runtime item table; this mapping is an inference.
- **Armour textures.** They are retried from `Data/Player`.
- **The EnchantEffect colour.** It is a parameter, white by default (see the
  gaps).

## Local renders

These are in `~/Documents/mu-mac-tools/native/renders/renderchar/` and are not committed:

- `sheet-item-levels.png`: +0, 3, 5, 7, 9, 11, 13, 15 on a Dark Knight with
  the …Male10 set, Sword13 and Shield01. The red and blue pulses of +3/+5 and
  the chrome passes from +7 are visible. The glow colour is `0.4,0.6,1.0`.
- `sheet-excellent-ancient.png`: excellent over time, and ancient.
- `sheet-quality.png`: +15 at graphics quality 0..5, showing the level caps.
- `sheet-back-carry.png`: hand versus safe zone, and Axe, Spear, Staff and Bow
  on the back.
- `sheet-plus15.png`: +15 with and without the `class15_*` attachments.
- `sheet-live-reference.png`: the live capture of Nighty next to a native
  `--world-render` render of a comparable +15 set. The items differ; the comparison
  is qualitative. The live client also shows the shadow, which the native
  mode does not draw.
- `live/nighty-spawn-*.png`: window-only reference captures of the user's
  character in game (MuMatrixKit bottle, under 3 minutes, game lock held).
  They show the chrome glow of high-level armour.

## Not established (gaps)

- **EnchantEffect colours.** Levels 7 and up take their colour from the
  EnchantEffect table `0x06fbb754`. It is filled from a script in the
  localisation archive ("EnchantEffect File color Table Loading Error!"),
  which was not read. Its default entry (`+0x50`) and per-item entries are
  unknown, so native renders use a parameter. The live captures show a bluish
  white on Nighty's armour; no value was measured.
- **Type-specific branches.** The 1,674 item types and 17 part skins with
  their own branches are not reconstructed (wings, special weapons, and
  others), nor are record types 4, 8 and 0x0b. The validator lists them.
- **Shadows.** RenderBodyShadow `0x012bc07a` is not reconstructed.
- **Effects.** The character effect emitters, particles, the helper/pet pass
  and item effects (the large effect switch of RenderLinkItem after
  `0x012c6a8b`) are not rendered.
- **Unvalidated native draws.** Bitmap overrides such as `0x80d4` are not
  loaded natively (they draw as misses). A "hide" mesh of some armour shows in
  chrome passes. Whether the client hides it through a texture type was not
  checked.
- **Monsters.** Monster bodies go through RenderObject `0x016d4fe4`, which is
  not in this milestone. The monster weapon geometry follows the verified hand
  path with the extracted bones; it was not compared end to end on a monster
  model.
- **Engine state taken as zero.** Engine state that the runs take as zero or
  empty includes buffs, the mount manager, option singletons, world 0 and
  `rand() = 0`. Other worlds' map processors were not run.

## Reproduce

```sh
make -C reconstructed/renderchar && make -C native
E=evidence
./tools/python/bin/python scripts/validate_renderchar.py --text $E/x86-text-capture-09/client-text.bin \
  --data $E/image-data-run10/data-capture-10/client-image-data.bin \
  --flag $E/trig-state-15/captures/late/math-dispatch-flag.bin --feature $E/x86-math-capture-09/cpu-features.bin \
  --sections kinds,items --classify all --cases 20000 --emit-special reconstructed/renderchar/special_types.h \
  --output /new/items.json
#   then --classify parts --merge-special … for the part skins
./tools/python/bin/python scripts/validate_renderchar.py … --sections back --back-types weapons \
  --emit-back reconstructed/renderchar/back_matrices.h --back-checks 0     # then rebuild and:
./tools/python/bin/python scripts/validate_renderchar.py … --sections back,character --back-checks 1000 \
  --characters 300 --output /new/back-character.json
./tools/python/bin/python scripts/validate_renderchar.py … --sections linkbones --emit-link-bones reconstructed/renderchar/link_bones.h
native/build/mu-render character --game-root "$MU_GAME_ROOT" --class 1 --weapon 0 "$MU_GAME_ROOT/Data/Item/Sword13.bmd" \
  --world-render --item-level all=15 --attachments --world-time 900 --out /tmp/dk15.png
```
