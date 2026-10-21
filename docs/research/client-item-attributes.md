# Item attributes and table record layouts (NATIVE-DATA-002)

This milestone names the fields of the client's Item.bmd record and of the other tables decoded by NATIVE-DATA-001. Names come from tracing the game code that reads each field. Three client routines that derive values from the record are reconstructed in C (`reconstructed/data/item_attributes.c`). A layout catalog (`reconstructed/data/table_layouts.c`) gives `mu-data` named JSON output. Decoded game data is never committed. Identity of the binary and captures is as in [client-data-tables.md](client-data-tables.md).

Labels:

- **Verified**: client instructions ran in Unicorn on the pinned restored text, and the authored C or field accessor produced the same values.
- **Static**: a reading of client instructions that was not executed.
- **Data**: agreement with the decoded installed contents only (for example, a well-known item's stats).

Names are authored. They are not original symbols. Static names also rest on judgment about what a consumer does.

## Item record accessors (verified)

| Routine | Behavior |
|---|---|
| `0x00cd5d29` | Item-script manager lookup: code to record pointer (std::map, first record wins). |
| `0x00ccc591` / `0x00ccc51e` | Item object accessor: object +0x00 caches the record and +0x10 holds the code. `0x00ccc51e` binds it, or logs `Not Exist ItemScriptData`. |
| `0x00cd5de8` / `0x00cd5dba` | Kind A / kind B by code (0 when absent). |
| `0x00cd6017` | Code has kind B *k* (unsigned code <= 0x2c00). |
| `0x0095fc2e`, `0x00987982`, `0x0095fbeb` | Object predicates: kind A, kind B and type equal *k*. Each first requires 0 <= code <= 0x2c00. |
| `0x00cd0995` | Object options: (0) set/ancient bits `+0x3b & 0x33`; (1) excellent flag `+0x98 == 1`; (2) period flag `+0x92 == 1`. |

These lookups and predicates ran on all 4,881 installed codes, plus absent codes. Two scans found the field consumers (scratch tools): a dataflow scan of the 124 lookup and 667 accessor call sites, and a sweep for record displacements. The record comparator `0x011844d9` gave the declared member order. It compares 16 bytes at +0x291 and 7 bytes at +0x2a1, and also compares +0x252 and +0x2aa, which the constructor `0x01184277` does not zero. The constructor writes +0x2a9 twice; +0x2aa is the field it misses. It neither zeroes nor compares +0x2a8, +0x2b0 and +0x2b1, so these look like later additions.

## Item.bmd fields

Offsets are in the 708-byte record. Copy rows are verified: the ItemConvert prefix `0x00cce06c..0x00cce1a3` copies those fields into the item object, and the object values were compared with the native accessor.

| Offset | Width | Name | Evidence |
|---|---|---|---|
| +0x250 | 1 | `kind_a` (category) | Verified: getter and predicate. Data: 1 basic weapons, 3 shields/armor, 6 wings, 9 jewels. |
| +0x251 | 1 | `kind_b` (sub-category) | Verified: getter and predicates. Static: 0x2b pentagram (durability copied raw, required level +4/level, repair ban). Kinds 0x0c..0x73 are staff-like and use magic durability. |
| +0x252 | 1 | `type` (grade) | Verified: predicate. Static: type 7 gets the Chaos weapon damage constants (codes 0x406/0x806/0xa07); type 4 forces durability 255. Data: 2 socket, 5 bound, 6/8 archangel, 11/12 Temple Guard/Imperial. |
| +0x253 | 1 | `two_handed` | Verified copy (object +0x1a). Static: weapon pose `0x01392bde`. |
| +0x254 | 2 | `level` | Static: base of the excellent/set bonuses (level+30, level+25), requirement formulas and set lines. Data: Kris 6. |
| +0x256 | 1 | `slot` | Static: `0x00cd2386` maps it to an equipment index. Data: 0 right hand, 1 shield, 2..6 armor, 7 wings, 8 pet, 9 pendant, 10 ring, 0xff none. |
| +0x258 | 2 | `skill` | Static: `0x00ccc993` copies it to object +0x60 when option bit 0x80 is set. |
| +0x25a/+0x25b | 1/1 | `width`, `height` | Static: free-cell search `0x00be2a75` and item drawing. Data: Kris 1x2. |
| +0x25c/+0x25e | 2/2 | `damage_min`, `damage_max` | Verified copy (+0x1c/+0x1e). Static: ItemConvert level, excellent and set formulas. Data: Kris 6-11. |
| +0x260 | 1 | `defense_rate` | Verified copy (+0x20 as word). |
| +0x262/+0x264 | 2/2 | `defense`, `magic_defense` | Verified copy (+0x22/+0x24). |
| +0x266/+0x267 | 1/1 | `attack_speed`, `walk_speed` | Verified copy (+0x34/+0x36). Static: tooltip types 101/102 (`Attack speed: %d`, `Movement speed: %d`). |
| +0x268 | 1 | `durability` | Verified (max durability). |
| +0x26a | 2 | `set_defense_tier` | Static: argument of formula 1/72 for set-item defense. Data: 1/2 on Temple Guard/Imperial pieces. |
| +0x26c | 1 | `magic_durability` | Verified (max durability, staff-like kinds). |
| +0x270 | 4 | `magic_power` | Verified copy (+0x28). Static: tooltip type 11 (`Increases wizardry/curse/spirit... by %d%%`); set bonus (level+30)/60+2. |
| +0x274 | 4 | `combat_power` | Verified copy (+0x2c). Static: formula group 12, tooltip type 122 `Combat Power %d%%`. |
| +0x278 | 4 | `attack_success_rate` | Verified copy (+0x30). Static: tooltip type 21 `Attack Success Rate: %d`. |
| +0x27c..+0x286 | 2 each | `require_strength`, `_dexterity`, `_energy`, `_vitality`, `_command`, `_level` | Static: requirement routine `0x00ccf659` (object +4..+0xe). Each is 20 + base x (item level + 3 x level) x 3/100, with special cases: energy uses base x required level x 4/100 for some kinds, and a double-precision path applies at item level >= 220. |
| +0x288 | 1 | `value` | Static: price `0x0169320b` adds value x value x 10/12. |
| +0x28c | 4 | `zen` | Static: fixed price when nonzero. |
| +0x290 | 1 | `set_attribute` | Static: `0x009e08d0` picks set stat line 1..6 (text 0x3b6..0x3bb). |
| +0x291 | 16x1 | `require_class` | Static: `0x00b93a58` takes the minimum class stage for the class slot; the tooltip loop of 16. |
| +0x2a1 | 7x1 | `resistance` | Layout (comparator loop of 7). Data: element rings/pendants 1, GM ring 255. No reader found in the restored text. |
| +0x2a8 | 1 | `can_drop` | Static: predicate `0x016bd7c8`, used by the world click handler `0x016a9150`. Data: bound items 0, boxes opened by dropping 1. |
| +0x2a9 | 1 | `can_trade` | Static: `0x016bed45`. Data: bound 0. |
| +0x2aa | 1 | `can_personal_store` | Static: `0x016be0dc` (single caller `0x00c00b38`). Data: ribbon boxes trade but do not sell in a store. Of the flag names, this trade/store assignment is the least certain. |
| +0x2ab | 1 | `can_warehouse` | Verified: warehouse ban `0x016bec14`. Data: event tickets can only be stored. |
| +0x2ac | 1 | `can_sell` | Static: sell ban `0x016be839`, checked before the high-value warning in `0x00ad598b`. |
| +0x2ad | 1 | `high_value` | Static: `0x016bd959` (level > 6, excellent/set, pentagram +9, or this flag). It drives the red/orange sell confirmation lines. |
| +0x2ae | 1 | `can_repair` | Verified: repair ban `0x016be1d9`, also used by the price routine. Data: arrows and bolts 0. |
| +0x2af | 1 | `max_stack` | Static: stack counting adds object +0x38 when nonzero, else 1. Data: potions 255, elixirs 3. |
| +0x2b0 | 1 | `pc_room` | Static: price 0, sell ban exempt. Data: only `[PC]` items. |
| +0x2b1 | 1 | `evolved_pet` | Static: price 0. Data: four evolved pets. |
| +0x2b2/4/6 | 2 each | `stat_option_melee`, `_ranged`, `_magic` | Static: tooltip types 108..113 (melee/ranged/magic attack or defense increase) through the stat-option manager. Data: all zero in this install. |
| +0x2b8 | 1 | `pentagram_grade` | Static: index into the pentagram manager (`0x00fc69cc`); a pentagram with grade 0 gets required level +4/level. Data: `(I)` items 1. |
| +0x2b9/+0x2ba | 1/1 | `field_2b9`, `field_2ba` | Layout only (constructor/comparator). No reader in the restored text. |
| +0x2bc/+0x2be | 2/2 | `elemental_attack`, `elemental_defense_bonus` | Static: `0x00fc7598` modes 0/1 (+3/level, +4..+9 at +10..+15). Tooltip types 251/252. |
| +0x2c0 | 2 | `elemental_defense` | Static: tooltip type 20 `Elemental Defense: %d`. |

Data-only spans: +0x257 (nonzero only in 13 battle boxes) and the padding at +0x261, +0x269, +0x26d, +0x289, +0x2bb and +0x2c2.

## Reconstructed routines (verified)

- Maximum durability `0x00ccc5b0` (object +0x39):
  - Pentagrams (kind B 0x2b) copy `durability` unchanged.
  - Otherwise the base is `durability`, or `magic_durability` for kinds 0x0c/0x0d/0x0e/0x4e/0x54/0x59/0x5a/0x72/0x73.
  - Item level *L* adds *L* (1..4), 2*L*-4 (5..9), or 2*L*-4+(*L*-9)(*L*-8)/2 (10..15).
  - Codes 0x1a04/0x1a05/0x28f7..0x28fa/0x2900 give 255.
  - Set options or kind B 0x79 add 20; otherwise excellent adds 15.
  - Type 4 gives 255. The result is capped at 255.
  - The harmony/socket sub-object at +0xe0 is taken as empty. Its contribution (via `0x00cbc335`) is not modelled.
- Warehouse ban `0x016bec14`:
  - Banned if the item is a period item, if code 0x1a14 has level != 0, or if code 0x1c0b has level 13.
  - Allowed for code 0x1c15 at level 3.
  - Otherwise banned when `can_warehouse` is 0.
- Repair ban `0x016be1d9`:
  - Banned for pentagrams, and for period items that have expired.
  - Otherwise banned when `can_repair` is 0.

The validator `scripts/validate_item_fields.py` uses the real manager constructor, Item.bmd loader and container inserts, the item object constructor `0x00ccbaa2` and `0x00ccc51e`. It runs on every installed code and on 300 synthetic records (random bytes; forced staff/pentagram/0x79 kinds, type 4, special and out-of-range codes):

| Check | Installed | All |
|---|---|---|
| Getters and code predicate (kind A, kind B, has kind B) | 19,528 | 19,528 |
| Object predicates (kind A, kind B, type; true and false probes) | 29,286 | 31,086 |
| ItemConvert copies (11 fields) | 53,691 | 56,991 |
| Maximum durability (levels 0..15 x 4 option states) | 312,384 | 331,584 |
| Warehouse and repair bans (4 levels x 4 period/expired states) | 156,192 | 165,792 |

All 604,981 comparisons match. Pinned SHA-256 digests cover the 15 routine bodies used. A negative control fails 9,542 of 26,794 checks: a library with the set bonus changed to 21 and the repair flag inverted.

## Other tables

`mu-data layouts` lists the catalog with a per-field evidence class:

- `consumer`: a client reader was traced (static unless stated);
- `layout`: the offset and width come from a constructor, comparator or loader, and the meaning is open;
- `data`: from decoded contents only.

`mu-data dump` prints named fields for these tables and reports uncovered nonzero bytes as unnamed spans.

| Table (record) | Main evidence |
|---|---|
| itemtooltip (136) | Loader `0x00f0ada4` keys each record by section<<9 + index. Builder `0x00f0eb44`: `name_color`/`name_style`, `show_level` (`%s +%d`), `name_text` (-1 = item name), then 15 lines of {i16 text id, u8 color, u8 style}. The client's std::pair puts the record at +2, so the reads appear at +0x4e/+0x50/+0x51. |
| itemtooltiptext (260) | u16 id, text[256], i16 `type` at +0x102. `type` selects the case of the tooltip formatter `0x00f1098a`, which reads the item fields above (for example, 101 attack speed, 251/252 pentagram elements). |
| ItemSetType (10 per code) | `0x009de132` reads `set_index[4]` (u16) per item code. Its last word is unread. |
| ItemSetOption (468) | `0x009de132`: name, second name, `tier_option`/`tier_value` [6][2] for 2..7 equipped parts, two extra, ten full-set and ten more option/value pairs. `part_count` at +0xf0 is data only. |
| ItemSetOptionText (102) | Constructor `0x01184b4b`/comparator: u8 option, text[100], u8 at +0x65. |
| Excellent Common/Wing Option (120) | Constructor `0x011838bf`. Key is category<<8 + index (loader `0x00cd51fe`). `0x00cd0d49` computes the value: `value_type` 6 = value + 5/level, 100 = formula from FormulaData, otherwise the constant. `format` is passed to the text formatter. `0x00cd0743` tests the seven flags against equipment categories. |
| SocketItem (3x50x168) | Loader: the third group counts records with a nonzero 6-byte `combination` at +0xa0. The other names (element, option, name, value_type, value[20]) are data only. |
| JewelOfHarmonyOption (750x180 in one unit) | Data: option, name[60], min_level, level_value[14], zen[14]. The unit splits evenly. |
| ItemAddOption (0x2c00x16 in one unit) | Data: two option/value pairs, item index, time. |
| MonsterSkill (48) | The loader copies `skill[10]` and the last word to `0x0a381fd8` + monster x 0x2c. `0x01395f66` picks the attack action from the slot of the monster's current skill. |
| MasterSkillTreeData (24) | Copied to `0x01d22d70` + i x 0x18. `0x00bb0250` stops at the first zero `slot` and keeps records whose `class_mask` has the player's class bit. The other fields are data only. |
| SkillTooltipText (808) | Constructor `0x0118501e`. Renderer `0x0117da56`/`0x0117eab5`: name color, the description and third-line show conditions and colors, two value arguments, `value_is_float`, `value_cap`. |
| InfoTooltip(Text), StatOption(Text), helpdata, PlayGuide, MasterSkillTooltip, Quest header, RuudShopViewInfo, petdata, Muun tooltip/mesh/exchange | Names inferred from the decoded contents (ids, texts, URLs, arrays). |
| PentagramMixNeedSource (188) | Layout only, from constructor `0x01184d7c` (arrays of 5, 4 and 3). |

Not given layouts:

- Mix, pet, NPCDialogue, QuestProgress, MuRummy, MuunOption/AddOption/Info/RenderInfo and EvolutionMonsterBox: structure unclear from data, no consumer traced.
- QuestWords, MapCharacters, FormulaData and ServerList: already structured by their decoder.

## skill.bmd, minimap.bmd, movereq.bmd loaders (static)

The checksum routine `0x00976895` has 35 call sites, all direct calls; there are no jump thunks, absolute or indirect references. They belong to the 33 catalogued loaders that verify a checksum, plus `*.mapack` (`0x00975391`, key 0xb6fd) and `*.mab` (`0x0097db09`, key 0xe7ca). None pushes 0x5a18 (skill.bmd) or 0xce54 (minimap.bmd), and no `push imm32` of either key occurs anywhere in the restored text. The data section holds 73 `.bmd` string occurrences, but no path for skill, minimap or movereq (nor bonusexp, itemtrsdata and the other matched-only files). A script-reload command (`0x00aed820`) pairs `Skill(Kor)` and `SkillRequire` with `./Data/Lang.mpr`, so this build appears to read skill data from the package's text tables; skill.bmd may be a leftover. If these loaders exist, they are in code the capture does not restore, as are the startup callers of the other loaders. Lang.mpr's password and IGC.dll-loaded files stay out of scope.

## Native module and CLI

```sh
make -C native build/mu-data
native/build/mu-data item "$MU_GAME_ROOT/Data/Local/item.bmd" 0      # attributes, max durability by level/options, bans
native/build/mu-data dump "$MU_GAME_ROOT/Data/Local/itemtooltip.bmd" --out /tmp/tooltip.json
native/build/mu-data layouts
```

`mu_item` carries `mu_item_attributes`. `mu_item_max_durability_at()` gives the client value for any level and option state. Outputs belong in local temporary paths only.

## Reproduce

```sh
make -C reconstructed/data && make -C native build/mu-data
./tools/python/bin/python scripts/validate_item_fields.py --game-root "$MU_GAME_ROOT" --output /tmp/item-fields.json
MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=... python3 -m unittest tests.test_data_tables_private
```

Portable tests:

- `reconstructed/data/test_item_attributes.py`: an independent Python model of the three routines and the field offsets over synthetic records, plus catalog consistency;
- `native/tests/test_native_data.py`: named item dump, `item` and `layouts` commands, a synthetic tooltip text table and a split harmony unit.

## Limits and next steps

- Static names stay readings. Weakest: `can_personal_store` versus `can_trade`, `pc_room`, `evolved_pet`, `set_defense_tier`, and all `data`-class names outside Item.bmd.
- Not reconstructed:
  - the requirement routine `0x00ccf659` (many code and kind special cases, a double-precision path at item level >= 220);
  - the ItemConvert bonus formulas (they call the FormulaData evaluator `0x0117b5eb`);
  - the price routine `0x0169320b` (reconstructed and verified by NATIVE-LANG-002: `reconstructed/price`, see
    [client-lang-tables.md](client-lang-tables.md#3-item-prices-verified)).

  The first two are the next candidates. They need the formula evaluator modelled.
- The harmony/socket contribution to maximum durability is not modelled.
- Item object field names (+0x14 level/options, +0x38 durability/stack, +0x3b set bits, +0x92/+0x93 period, +0x98 excellent) come from the routines above and are not a full object layout.
