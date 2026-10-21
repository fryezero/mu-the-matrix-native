# Fidelity pass: lights, item models, item labels (NATIVE-FIDELITY-001)

Merged milestones left gaps that this pass closes:

* NATIVE-LIGHT-001 ([client-model-light.md](client-model-light.md)) did not trace the hero's light, kept an
  approximate body light for the ambient creatures and did not check the lighting of the 3D item models drawn over
  the GFx windows.
* NATIVE-ITEMS-001 ([client-ground-items.md](client-ground-items.md)) did not wire the set-item prefix or the set
  tier into the labels, did not confirm the suffix spacing, and could not resolve the special item models.
* NATIVE-GFX-003 ([native-gfx3.md](native-gfx3.md)) centred armour models on their cells because the client's
  placement rule was not reconstructed.

Labels:

* **verified**: the client's instructions ran in Unicorn and matched the native code on every compared case;
* **static**: read from decoded instructions (or a headless Ghidra decompilation, scratch only), not executed;
* **inference**, **layer choice**: as in the earlier notes.

Inputs are the pinned restored text (`2bd5f2e9…3724`) and second image section (`c985e2e6…672f`). The Lang.mpr
families use NATIVE-LANG-001's live snapshot (`lang3.bin`, read 2026-10-18); nothing new was read from the game.

## 1. The hero's light (verified)

RenderCharacter `0x01363260` writes the light every body part is drawn with (character `+0x1b8`, the light argument
of each part's RenderPartObject) in the block `0x01367530..0x01367d85`:

```
base  = scene state 5 ? (0.4, 0.4, 0.4) : RequestTerrainLight 0x016cb08d(x, y)        # the frame light
light = base + object light (+0xec)
object type 0x7dc: light = (0.6, 0.6, 0.6)
else 0x0139bcdc(character +0x146): a red glow that fades (+0x3330) and spawns particles   # not ported
character == Hero [0x0a39d754]:
    L = (1, 1, 1); for the bits 0..3 of Hero +0x1a6 ([0x01d1df1c]):
        bit 0 L *= (0.9, 0.5, 0.5); bit 1 (0.5, 0.9, 0.5); bit 2 (0.9, 0.5, 0.5); bit 3 (0.9, 0.5, 0.5)
    light = scene state 5 ? (0.5, 0.5, 0.5) + object light : L
```

Hero `+0x1a6` is set bit by bit by a state packet handler (`0x012474bc`, the cases 0..3 of the packet's byte 3) and
cleared at `0x0121d81e`/`0x0124d365` (static). This is why the live read of NATIVE-LIGHT-001 saw (1, 1, 1) for the hero
and frame light + 0.2 for everyone else. Later branches of RenderCharacter overwrite the light for their own cases
(the class-1 world rule `0x0136a06b`, the PK colour from character `+0x1f` ≥ 6 at `0x0136ac25`, the slot loop); they
are not part of this function.

`reconstructed/renderchar` `mu_rc_character_light` reproduces the block (the glow branch is reported as
unsupported). `scripts/validate_renderchar.py --sections light` runs the client's whole RenderCharacter on a Player
character in the existing render harness, writes the case's object type at the block's entry (code hook at
`0x01367530`; other types take other paths before it), stubs RequestTerrainLight with the case value, and reads
character `+0x1b8` at `0x01367d85`. The native hero (`mu_walk_place`) uses it with no state bits: (1, 1, 1).
Monsters and NPCs already had the client's value: their body colour comes from RenderObject's body light, which
gives the same frame light + object light.

## 2. Ambient creatures' body light (verified)

RenderBoids/RenderFishs draw each body with RenderObject `0x016d4fe4(o, a1, 0, 0, -1, -1)`, whose setup calls the
body light `0x017ec3d8` (NATIVE-OBJECTS-002, verified): model `+0x50` = object `+5`, colour = (object `+7` ? frame
light : primary light) at the position, × 0.1 unless object `+6`, + object light. The OBJECT constructor
`0x0129e792` and ObjectInit `0x0129eb81` set `+6` = `+7` = 1 and `+0xe4`/`+0xe8` = 0.8/0.2, and no environment
routine writes `+6`/`+7` (a byte scan of `0x00c9e24a..0x00ca5000` finds seven writes of `+5` and none of `+6`/`+7`).
So:

| Creature | Lighting flag (+5) | Colour |
|---|---|---|
| bird, bat, crow, MoveFishs creatures | 1 | frame light + 0.5 |
| butterfly, Atlans shoal (`0x199`/`0x19a`) | 0 (one flat colour) | frame light + 1 |

with Transform's light terms 0.4 / 0.8 / 0.2. NATIVE-ENV-001 had drawn them with the object light alone and the
default terms 0.4/0.4/0.4. `mu_env_body_light` (reconstructed/environment) and `mu_env.c` now use the client's
rule; `mu_obj_terrain_light` gives the frame light.

`scripts/validate_fidelity.py --sections env_light`: the C environment module runs MoveBoids/MoveFishs in
Lorencia (water layer), Dungeon, Noria, Atlans and Lost Tower; for every live object the client's constructor and
ObjectInit run, the C object's modelled fields are written over it, and the client's body light runs with a random
frame-light grid.

## 3. The item models over the GFx windows: RenderObjectScreen (verified)

The per-window item pass `0x00abfcca` reaches RenderItem3D `0x016c154e` (NATIVE-HUD-001), which calls
RenderObjectScreen `0x016c2d82(model, level word, excellent, set bits, &position, select, held, a2c, a30, scale,
item +0x108, tick)`:

1. `level = (level word >> 3) & 15`; Item.bmd kind A `0xc`: the level word passed on is 0. Held: scale × 1.4.
   Select == 1: item angle `[1]` (`0x0b5e3c2c`) = time × 0.2.
2. **Pose model** (`0x0b5e3b24`): armour parts `0x18e6..0x22e5` and `0xace`/`0xacf`/`0xad0`/`0xae5` pose the
   **Player model `0xa91`**; type `0x26f2` by level 0/2 becomes `0x3890`/`0x3891` (also the drawn type). The compare
   at `0x016c2ed6` is a runtime-patched jump in the capture. Its leftover bytes `0b f2 26 00 00` are the tail of
   `81 3d 24 3b 5e 0b f2 26 00 00` (`cmp dword ptr [0x0b5e3b24], 0x26f2`), which the validator writes back
   (inference from the leftover bytes and RenderPartObject's own `0x26f2` rule at `0x017e645f`).
3. No pose model: return.
4. **The armour placement rule**: the pose model's height `+0x90`, used by the pose builder for a locked root:
   helms `0x18e6..0x1ae5` −160 (record type `+0x252` 4: −10 more; `0x193b..0x1940` +10; `0x1927`/`0x192c`: x +
   0.04), armours `0x1ae6..0x1ce5` −100 (type 4: −13; `0x1b3a..0x1b3f` +13; `0x1b40` −32), pants `0x1ce6..` −50,
   gloves `0x1ee6..` −70, boots 0; `0xace`/`0xacf`/`0xad0`/`0xae5` −100.
5. **InvenItemAnimation** (`0x06fbc830` = Lang.mpr's table manager `+0x1dd0`, lookup `0x0111d824`, its only
   reference): with a record and the item's animation state, the pose model's action `+0xa8` = record `+8`, Animation
   gets the state's frames, and the tick `0x012b4dd3` advances them at the record's speed `+0xc`. Otherwise action 0
   and frames 0. In this client the table has five codes (group 20, indices 114..118, action 0, speed 0.3); no armour.
   Animation runs with keep-root 0 and translate 0.
6. **The object**: a CHARACTER on the stack (`0x0129d272`), its object's type = the drawn type, ItemObjectAttribute,
   then `+5` (LightEnable) = 0, scale, position, light (1, 1, 1), and
   RenderPartObject(o, type, NULL, light, alpha, level word, excellent, set bits, 1, 1, 1, 0, 2, a2c, a30, 0).

**The lighting of the item models** (static, RenderPartObject `0x017e63f4`, whose RenderObjDraw part is verified by
NATIVE-RENDERCHAR-001): it copies object `+5` (cleared) into the model's lighting byte `+0x50`, so the mesh draw uses
one flat colour; it runs the body light `0x017ec3d8` (whose colour RenderObjDraw then replaces with the light argument
(1, 1, 1) for the body pass) and Transform with the constants 0.4/0.8/0.2. NATIVE-GFX-003's inference (lighting
cleared, light 1, terms 0.4/0.8/0.2) holds. No GL light or colour state of the pass changes this.

`reconstructed/hud` `mu_hud_object_screen` reproduces 1–6; `scripts/validate_fidelity.py --sections object_screen`
runs the client's routine (with the patch written back, the constructor, ItemObjectAttribute and the destructor
executed) and compares the pose model, height, action, Animation's arguments, the tick, the object's lighting byte,
scale, position, type and light, and RenderPartObject's sixteen arguments.

**Native.** `world/world_gfx_game.c` runs `mu_hud_object_screen` for every cell: armour parts are skinned against a
Player mannequin posed at the client's height and action (as RenderItems' armour on the ground), the InvenItemAnimation
codes animate when `MU_LANG_DIR` holds `invenanim.tsv`, `0x26f2` loads `Event02/03.bmd`. The NATIVE-GFX-003 stand-in
(centring the model on its cells) is gone.

## 4. Item labels

### The set-item prefix (verified)

The name builder `0x017ea422` starts a plain item's text with `0x009953ef()->0x009e051c(item)` and then appends the
record name with `strcat` (static). The set manager (`[0x01d1dcc0]`, built by `0x009e00d8`) is filled at start-up by
`0x009e02a8` from local files, not from Lang.mpr:

* `Data\Local\ItemSetType.bmd` (`0x009ddde0`: 0x2c00 records of 10 bytes, four set words per code),
  `ItemSetOption.bmd` (`0x009ddf86`: 1000 records of 0x1d4 bytes: name `+0`, second name `+0x40`),
  `ItemSetOptionText.bmd` (`0x009df9ca`);
* `0x009de132`: every ItemSetOption record with a name becomes a set {index, name, second name}, kept in a
  `std::map<std::string, set *>` keyed by the name (a later set with the same name is dropped). For every code and
  word k ≠ 0, an entry {code, set bits (1, 2, 0x10, 0x20)[k]} joins the first set in map order with that index:
  its pair list when LegendaryItemSetType (Lang.mpr, `0x011289d6`) lists the code for that set (the first such
  entry creates the set's pairs from the legendary record, slots with set bits 0), else its entry list;
* `0x009debe4`: CashItemSetOption's sets (Lang.mpr) join the map with indices after the last ItemSetOption set, and
  its items join their sets with set bits 1.

The lookup `0x009e0551(code, item +0x3b)` walks the map in name order and returns the set's **second name** for an
entry with that code whose set bits equal `+0x3b & 0x33` (any set bits when the code's Item.bmd kind B is `0x79`), or
a pair slot with that code and those bits; else "". The label of an ancient helm is therefore
`"Warrior" + "Leather Helm" + " +5"` = **`WarriorLeather Helm +5`**: the client puts no space between the second name
and the item name (static reading of the builder's strncpy/strcat, the prefix itself verified). Two quirks follow
from the client's code and are reproduced: kind-B-`0x79` codes get the prefix for any set bits, and a legendary pair
slot that no ItemSetType word filled matches set bits 0.

`reconstructed/items/item_sets.{h,c}` builds the same sets from the installed files and the plaintext tables;
`native/core/mu_items.c` answers the name builder's prefix hook with it (also through NATIVE-NAMES-001's shared
label path, `core/mu_label`, since the text is the builder's).

`scripts/validate_fidelity.py --sections set_prefix` maps the Lang snapshot (validate_lang's machine, strict
definedness checks), runs the client's manager constructor and `0x009e02a8` with the CRT file functions serving the
installed files, then `0x009e0551` for every code with a set word, the legendary and cash codes and 200 others, under
several set-bit values. Modelled: `fopen`/`fread`/`fclose`, `operator new`/`malloc`/`free`, the Item.bmd record
lookup (a record with the installed kind B), the option-text formatter `0x009df67e` (its strings are never read by
the prefix: an empty string), the CRT feature words, the security cookie and the record key global (as
`validate_data_tables.py`).

### The set tier (verified lookup)

The builder's "set tier" branch (kind B `0x2b`, colour classes 0/0x12/0x13) reads **PentagramOption** (Lang.mpr
table `+0x3ec`, lookup `0x011447ac`, record `+0x24`, default record `+0x4c`), not a set table. The converter writes
`pentagram.tsv`; `mu_lang_pentagram_tier` answers it.

### The suffix spacing

GlobalText 176/177/178 are `+Skill`, `+Option`, `+Luck` (no leading space) in the installed strings, and the builder
appends them with `strcat` after `"%s +%d"`: `Short Sword +9+Skill+Option+Luck`. The native English stand-ins (no
Lang tables) now match that spacing.

### Special item models (verified)

The models outside Item.bmd's `code + 0xae6` range that CreateItem, RenderItems and RenderObjectScreen select are
loaded by the item-model loader `0x0183220e` with AccessModel `0x018202b4(model, folder, name, number)`; the file is
`folder + name + (number < 0 ? "" : number < 10 ? "0n" : "n") + ".bmd"`. Executing the loader gives 37 calls
(`special_models.h`, generated): Box of Luck `0x3894` MagicBox02 … `0x389a` MagicBox08, `0x3890`/`0x3891` Event02/03,
`0x38a2` LifeStoneItem, `0x38a5..0x38a7` p03box/obox02/blue01, the +15 attachments `0xa99..0xaa1`, and others. All
37 files are installed. The models `0x270f..0x2712` named in NATIVE-ITEMS-001 are `code + 0xae6` of codes
`0x1c29..0x1c2c` and resolve through Item.bmd (Gemstone, Jewel of Harmony, the refining stones). `mu_items.c` and
`world_gfx_game.c` load them through `mu_gi_special_model_file`; a drop of every Box of Luck level now draws its model
(`model_missing` 5 → 0 in the local render).

### EnchantEffect colours

Ground items already took the glow colour from NATIVE-LANG-001's EnchantEffect table: `mu_renderchar_default_env`
attaches `mu_lang_shared()` and the item draw asks `0x010ffd7a(type − 0xae6)` unless `--glow-color` overrides it. The
items' `glow_color` (0.4, 0.6, 1) is only the colour without the table. No change was needed.

## 5. Lang tables added to the converter

`scripts/live_lang_to_plain.py` writes four more plaintext tables from the same snapshot, located through their
consumers: `pentagram.tsv` (`0x011447ac`), `invenanim.tsv` (`0x0111d824`), `legendary.tsv` (`0x011288c7`) and
`cashsets.tsv` (the vectors `0x009debe4` reads). `native/core/mu_lang` loads them. They are the server team's data:
local only.

## Verification

Private runs (2026-10-21), `tools/python` with Unicorn:

| Section | Client routines | Cases | Equal | Negative control |
|---|---|---:|---:|---|
| renderchar `light` | RenderCharacter `0x01363260` (block `0x01367530..0x01367d85`) | 855 (+185 glow-branch cases refused) | 855 | hero without the state tints: 308 differ |
| `env_light` | constructor `0x0129e792`, ObjectInit, body light `0x017ec3d8`, RequestTerrainLight | 226 | 226 | the NATIVE-ENV-001 colour: 226 differ |
| `object_screen` | RenderObjectScreen `0x016c2d82` (+ constructor, ItemObjectAttribute) | 3,000 | 3,000 | armour height 0 (the stand-in): 1,397 differ |
| `special_models` | loader `0x0183220e`, AccessModel `0x018202b4` | 45 | 45 | 37 files installed |
| `lang_tables` | `0x011447ac`, `0x0111d824`, `0x011288c7` over the snapshot | 370 | 370 | |
| `set_prefix` | `0x009e00d8`, `0x009e02a8` (3 loaders, 2 builders), `0x009e0551` | 4,902 | 4,902 | kind B 0x79 rule left out: 156 differ |

9,398 cases in all, 0 mismatches. The set-prefix run covers 1,634 codes × 3 set-bit values (361 sets, 1,081 non-empty
answers, 234 through the kind B 0x79 rule); the creatures are birds, bats, butterflies, rats, Lorencia fish and the
Atlans swimmers. Reports: `evidence/native-fidelity/renderchar-light.json`, `evidence/native-fidelity/report-01.json` (ignored).

Tests: `native/tests/test_native_fidelity.py` (portable: the five C reconstructions on worked examples, mu_lang's new
tables, a mu-walk label run on a synthetic world with synthetic set tables; private: the validators above).

## Renders (local)

`~/Documents/mu-mac-tools/native/renders/fidelity/{before,after}/`: `inventory` (GFx inventory with item models),
`env-lorencia`, `env-noria` (birds and butterflies), `labels` (set prefix, suffixes), `special` (Box of Luck levels);
`env-*-before-after.png` side by side. `MU_LANG_DIR` was set for both sides. The GFx inventory now shows the helm,
armour and pants posed on the Player skeleton within their cells; the live equipment slots of NATIVE-HUD-001's
capture show armour parts filling their slots in the same way (a visual comparison only: no armour lies in the live
inventory grid, and no new live run was made).

## Not established

* The glow branch of the light block (`0x0139bcdc` classes) and the later per-case rewrites of the light (class-1
  world rule, PK colour) are not ported.
* The hero pointer during character select (which character is `[0x0a39d754]` in scene 5) is not traced; the
  character-select session keeps 0.4 + object light.
* RenderItem3D's 27 special codes (NATIVE-HUD-001) stay unreconstructed, so some special models still do not reach
  the inventory pass.
* The patched compare at `0x016c2ed6` is inferred from its leftover bytes.
* No live comparison of labels with set items (no safe spot with ancient drops).
