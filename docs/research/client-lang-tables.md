# Lang.mpr tables read from the running client (NATIVE-LANG-001)

`Data\Lang.mpr` holds the client's game text and script tables: GlobalText (`Text(kor)`), the skill table, gates
and the move list, monster and NPC names, NPC dialog, the EnchantEffect colours and about 80 more.
NATIVE-DATA-001 verified its envelope (loader `0x00ffaeb8`, checksum key `0x12dc`). The zip entries inside need a
package password that sits behind the protection boundary. This milestone takes the same route the owner authorized
for object placements (NATIVE-OBJECTS-001/002):

1. Let the game's own code load Lang.mpr.
2. Read the plain tables it built out of our own client's memory, read-only, under the game lock.
3. Locate the tables only through main.exe's own consumers (the routines that read them).

The plaintexts are the server team's game text: they stay local and are never committed. Tests use synthetic
fixtures.

Labels:

- **Verified**: the client's own consumer ran in Unicorn over the live snapshot and agreed with the native module.
- **Static**: a reading of the instructions that was not executed.
- **Data**: inferred from values (for example, aligned with the installed `skill.bmd`).

## Boundary

Not done, and not needed: recovering the package password, decrypting Lang.mpr, or analysing `IGC.dll`, `RGS.dll`,
the packer or the table loader `0x010d68e1`. The loader is treated as opaque; it is only seen being *called*.
The reader copies plain memory that main.exe's code reads; it never writes, suspends, hooks or patches.

## Locating the tables (static, from consumers)

- **GlobalText.** `0x0095f027(index)` (thiscall, `this = 0x06fbab48`) calls `0x011753c3`. That routine finds
  `index` in the `std::map<int, record>` at `this+0x38`; on a miss it builds `"[Text] error index : %d"` into
  `this+0x48`. It returns the record's `std::string` at node `+0x1c`, and `0x008e7940` (`c_str`) gives the
  characters.
- **Skill table.** The skill lookup `0x00961620` (`this = 0x06fbb138`) uses the map at `this+0x108`. It returns
  the record (node `+0x14`), or the default record at `this+0x38` on a miss.
- **Table manager.** `0x0115eceb` is the startup routine that loads every Lang table. It passes `this+offset` and
  a wide script name to the table loader `0x010d68e1`. With GlobalText = `this+0xe8`, `this = 0x06fbaa60`. The
  76 table objects and their names are catalogued in `mac-play/diagnostics/langread.c`. The ones used here:

  | Table | Object | Map |
  |---|---|---|
  | Text(kor) | `0x06fbab48` | +0x38 |
  | Gate | `0x06fbabac` | +0x38 |
  | Slide(kor) | `0x06fbae00` | — |
  | Skill(Kor) | `0x06fbb138` | +0x108 |
  | SkillRequire | `0x06fbb248` | — |
  | Npcname(kor) | `0x06fbb664` | +0x38 |
  | Dialog(kor) | `0x06fbb6d0` | +0x38 |
  | RenderingData\EnchantEffect | `0x06fbb754` | +0x38 and +0x5c |
  | movereq(kor) | `0x06fbb84c` | +0x38, plus a vector at +0x40 |
  | MapSearchInfo | `0x06fbbf7c` | — |

  The developer "TableReLoader" handler `0x00aed820` reloads Skill(Kor) (`0x06fbb138`), SkillRequire
  (`0x06fbb248`) and MuunEffectInfo (`0x06fbb46c`) from `./Data/Lang.mpr` through the same loader. That confirms
  the pairing.
- **Map layout** (MSVC 2012+). The container holds a head pointer and a size. A node is `_Left +0`, `_Parent +4`,
  `_Right +8`, colour `+0xc`, `_Isnil +0xd`, key `+0x10`, value `+0x14`. The key compare is the signed `int` less
  `0x0096ba31`. `std::string` is 24 bytes: an inline buffer below capacity 16, size at `+0x10`, capacity at `+0x14`.

## Live read

The read followed GAME-LOCK.md: lock held 17:49:09–17:53:51 on 2026-10-18. Three client sessions ran in the
MuMatrix32 play bottle, about 64 s each. `mu-to-server.sh` brought each to the server list (no account login, no
character), and `langread` read the tables there; they are loaded before the server list. Each client was then
closed with taskkill (WM_CLOSE), and the launcher with its own X button (muinput click). Only clients this project
started were read.

`mac-play/diagnostics/langread.c` (macOS host tool, ad-hoc signed with the debugger entitlement) copies, through
`mach_vm_read_overwrite`:

- the manager range `0x06fbaa60..0x06fbcd80`;
- every map inside a table object: each node's header and value, up to the table object's size plus `0x14`;
- buffers the copied bytes point to, by shape: a `std::string`'s characters, and a `std::vector`'s elements,
  scanned once more for strings.

The first run hit the 512 MB cap of an over-eager chase (4 MB vector windows); the second deduplicated tree nodes
against chase copies. The third (`lang3.bin`, 5.3 MB) copied every node of all 91 maps:

| Map | Size |
|---|---:|
| GlobalText | 6,514 |
| Skill | 973 |
| Gate | 625 |
| movereq | 69 |
| Npcname | 905 |
| Dialog | 204 |
| EnchantEffect | 2,464 |

`scripts/live_lang_to_plain.py` walks the same trees offline and writes `globaltext.txt`, `skills.tsv`,
`gates.tsv`, `moves.tsv`, `npcnames.tsv`, `dialog.tsv`, `enchant.tsv` and `mapnames.tsv`. Text fields escape TAB,
LF, CR and backslash, and bytes outside printable ASCII become `\xHH`, so the client's bytes round-trip. All but
three strings are ASCII; three CP949 leftovers remain. Snapshot and plaintexts are local
(`~/Documents/mu-mac-tools/native/scratch/lang/`).

## Record layouts

Offsets are from the record, which is the map value after the 4-byte key.

**GlobalText**: `+0` byte, `+4` index (equal to the key in all 6,514 records), `+8` `std::string`. Verified with
`0x0095f027`.

**Skill(Kor)**, 0xd0 bytes. The default record spans `0x06fbb170..0x06fbb240`.

| Field | Offset | Evidence |
|---|---|---|
| skip byte | +0x00 | verified for the lookup; SkillInfo skips the record when set (NATIVE-GFX-003) |
| index | +0x04 | |
| Name | +0x08 | verified, GetSkillInformation |
| level | +0x20 | data: 492/538 equal `skill.bmd` u16 +32 |
| damage | +0x24 | static: getter `0x016969c2`; data 488/538 |
| mana | +0x28 | verified |
| AG | +0x2c | verified |
| distance | +0x34 | verified (base of GetSkillDistance) |
| Delay | +0x38 | verified (NATIVE-GFX-003 SkillInfo) |
| requirements | +0x3c..+0x4c | static: compared with character values by `0x010922..`; Poison has 140 at +0x44 (energy, data) |
| MasteryType | +0x50 | |
| SkillUseType | +0x58 | |
| brand | +0x5c | static: GetSkillInformation's mana branch |
| master factor byte | +0x7c | verified |
| Magic_Icon | +0x8c | |
| type | +0x90 | static, NATIVE-COMBAT-001 |

The maps or sets at +0x64 and +0x6c are not walked. GetSkillInformation `0x01696458` works like this (verified):

- For skills outside 300..929, mana = `+0x28` and AG = `+0x2c`.
- Inside that range, let `m` be the value of `0x00bb1d9d` (the master-skill level).
  - Mana uses `al = (+0x5c == 0 && m == 0) ? byte +0x7c : m`.
  - AG is `+0x2c` raw when `+0x58 == 4 && +0x5c == 0`; otherwise it uses `al = m`.
  - The scaled value is `round((float)v * (float)(al*0.005 + 1.0))`. Rounding is half away from zero through
    float, routine `0x00d01e8c`.
- The distance is `GetSkillDistance 0x01696630`: `(float)+0x34` plus class and skill-tree bonuses. The bonuses are
  not ported.

**Gate**, 0x34 bytes: `+8` flag, `+0xc` world, `+0x10..+0x1c` x1/y1/x2/y2, `+0x20` target, `+0x24` dir,
`+0x28`/`+0x2c` minimum/maximum level. The world is verified through the move window `0x00c6922a`, which reads
gate `+0xc`; the other names follow the classic Gate.txt column order (static).

**movereq**, 0x54 bytes:

| Field | Offset | Evidence |
|---|---|---|
| id | +0 | static: passed to `0x00b2d5b2` |
| name | +4 | `std::string` |
| server name | +0x1c | `std::string` |
| zen | +0x34 | |
| minimum level | +0x38 | |
| maximum level | +0x3c | |
| gate | +0x40 | verified: `0x00c6922a` looks it up in Gate |

`+0x44..+0x4c` are unnamed.

**Npcname**, 0x28 bytes: `+0` index, `+4` name (getter `0x011427c7`), `+0x1c` (`0x011427e0`), `+0x20`
(`0x011427f9`), `+0x24` byte (`0x01142812`). All verified.

**Dialog**: `+0` index, `+4` text.

**EnchantEffect**. The key is the item code (model index − `0xae6`, from the callers `0x016db934` and
`0x012bbc59`). The value is a `std::vector` of 16-byte entries `{int mesh; float r, g, b}`.

| Lookup | Returns |
|---|---|
| `0x010ffd7a(code)` | the first entry's colour, or the table's default at `+0x50` |
| `0x010ffddb(code, mesh)` | the first entry whose mesh is the argument or −1, else `+0x50` |
| `0x010ffd25(code)` | the vector, or an empty vector at `+0x44` |

The default colour is (1, 0.5, 0). The table has 2,464 codes and 3,807 entries. PartObjectColor `0x016db5eb` uses
`0x010ffd7a`; RenderLinkItem uses `0x010ffd25`; the character effect emitters use `0x010ffddb`. All verified. The
second map at `+0x5c` (38 entries with a vtable and strings) is not interpreted.

**Map names**. The map-name function `0x016baaa6(world)` (caller: the top menu's `setMapName`, `0x0123d5dd`) is a
64-case chain over GlobalText. It returns `GlobalText[30 + world]` by default. A few cases depend on runtime state:

- the current world `0x01cf15fc`;
- the event singletons `0x1ec8eb8` and `0x1ec9118`;
- the predicate `0x009d3e63`;
- the hero position for world 79;
- world 115 takes its name from `0x00b9e03b`.

Running it in Unicorn with a GlobalText that returns its index gives `native/core/mu_lang_maps.h` (108 worlds that
differ from the default). The modelled state is: current world = the argument, no event, hero at zero.

## Native module

`native/core/mu_lang.{h,c}` loads the plaintext directory (`mu_lang_load`, or `mu_lang_shared()` from
`MU_LANG_DIR`). It answers GlobalText, the skill table and GetSkillInformation, gates, moves, NPC names, dialog, map
names and the two EnchantEffect lookups. The `mu-lang DIR …` tool queries it. Wiring:

| Consumer | With the tables (MU_LANG_DIR) | Without |
|---|---|---|
| GFx layer `mu_gfx_layer.c` (`cfg.text` provider) | InitMenuInfo keys and labels (GlobalText numbers verified by NATIVE-GFX-003); inventory InitText (handler `0x00b908e4`); character InitText (`0x00b3d161`); chat InitData; index-to-member pairs are static readings | stand-ins / "GlobalText N" |
| `world_gfx.c` (mu-world, mu-client) | skill table sent to ASData from Skill(Kor) (names, icons, delay, use type, mastery; skip byte honoured); top menu map name | skill.bmd inference, "Skill N", "World N" |
| `mu_combat.c` | skill range = distance `+0x34`; log line from GetSkillInformation; `skill_table` in the summary | demo 2/6 tiles |
| `mu_renderchar.c` | item colour `0x010ffd7a(type − 0xae6)`; `--glow-color` sets `glow_override` and wins | parameter (white) |
| `mu_charsel_ui.c` | tip GlobalText 0x6ae/0x6cb/0x6cc, warnings 0x1b4/0x1b5; `--tip` wins | the observed tip |
| `mu-render ui`, `client/shell.c` | login 454/455 (456 used only when it holds one `%s`), server window 0x235..0x237 | observed strings |

## Verification

`scripts/validate_lang.py` maps the snapshot at its original addresses in the Unicorn machine. Reads outside the
copied bytes stop a case; the only tolerance is the CRT string routines' aligned dword reads past a NUL. It runs
the client's consumers and compares them with `mu_lang.c` (built as a shared library) loading the converter's
plaintext. Run on `lang3.bin`: 0 mismatches.

| Family | Client routine | Cases |
|---|---|---:|
| text | `0x0095f027`, every key | 6,514 |
| skill_lookup | `0x00961620`, every key + 100 absent (default record) | 1,073 |
| skill_info | `0x01696458`, every skill × master level {0, random 1..40}; 555 skills in 300..929 | 1,946 |
| gate | `0x0110cbaf` (address + fields) | 625 |
| move | `0x0113c3f5` (address, strings, fields) | 69 |
| npc | `0x011427c7/e0/f9`, `0x01142812` | 905 |
| enchant_first | `0x010ffd7a`, every code + 200 absent | 2,664 |
| enchant_mesh | `0x010ffddb`, codes × meshes −1..9 | 29,304 |
| map_names | `0x016baaa6`, worlds 0..299, real GlobalText | 300 |
| map_table | the same routine with an index-returning GlobalText; regenerated header equals the committed one | 300 worlds |

Five planted mistakes in the plaintext are all detected: a text entry, a skill mana column, the EnchantEffect
default, the entry order of a multi-entry code, and a map-name text. The run takes about 15 s.

Modelled, not client code:

- imports (any import call stops a case);
- thread-safe local statics as already constructed: 114 TLS guards set to 0, TLS epoch maximal;
- the map-name state listed above;
- for skill_info, the class and master managers return dummies, `0x00bb1d9d` returns the case's level,
  `0x00c354b7` returns −1 and `0x00c2a236` returns 0.

Chase copies that land on the machine's own regions are skipped; none of them is table data, since all nodes sit
in `0x12..0x15xxxxxx`.

Tests: `native/tests/test_native_lang.py`.

- **Portable** (synthetic snapshot with inline and heap strings, vectors and balanced trees):
  - converter and loader, byte round-trip of escapes;
  - GetSkillInformation against an independent float32 statement;
  - map table and default, the EnchantEffect semantics;
  - malformed snapshots and lines;
  - the GFx labels through the test host's provider (`MU_GFX_HOST_TEXT`);
  - the login overlay (the table strings give the same image as the same strings given as options);
  - the charsel tip (the table equals `--tip`);
  - the world render (the table colour equals `--glow-color` with that colour);
  - combat: the log line and the distance-1 cast starting later than the demo range.
- **Private**:
  - table sizes with `MU_LANG_DIR`;
  - the validator with `MU_LANG_SNAPSHOT`.

## Renders (local)

Renders are in `~/Documents/mu-mac-tools/native/renders/lang/`:

- `world-hud-lang.png` vs `world-hud-placeholders.png` (mu-world `--gfx`, Tormenta Island): map name, character tabs
  and labels, EnchantEffect colours on the inventory models;
- `login-lang.png`, `login-placeholders.png`;
- `charsel-lang/` (tip line from GlobalText 0x6ae);
- `renderchar/sheet-enchant.png` (Dragon set red-orange (1, 0.2, 0) and Plate set blue at +9, each beside the
  white placeholder);
- `combat/skill*.json` (log lines such as `skill 9 Evil Spirit: mana 90, AG 0, distance 6`);
- `live/server-select.png` and `live/launcher.png` (window-only).

## Reproduce

```sh
make -C mac-play/diagnostics langread            # macOS host tool
mac-play/diagnostics/build/langread <main.exe pid> lang.bin   # client you started, under the lock, at the server list
scripts/live_lang_to_plain.py lang.bin --out LOCAL/lang       # decoded game text: keep local
MU_LANG_DIR=LOCAL/lang native/build/mu-lang LOCAL/lang summary
MU_LANG_DIR=LOCAL/lang native/build/mu-world --game-root "$MU_GAME_ROOT" --gfx MOVIES ...
python scripts/validate_lang.py --snapshot lang.bin --mutations [--write-maps]   # Unicorn + pinned captures
```

## Gaps

- Field names without consumer evidence: skill `+0x20` (level, data) and `+0x3c..+0x4c` (requirements); gate
  columns other than the world; movereq `+0`, `+0x44..+0x4c`; Npcname `+0x1c/+0x20/+0x24`.
- Not read here: the other tables (NATIVE-LANG-002 adds BuffEffect, CharacterInfoSetup, SkillRequire,
  MonsterSoulConversion and MUQuestString; its survey below lists all 74); the EnchantEffect map at `+0x5c`; the
  skill record's inner containers at `+0x64` and `+0x6c`.
- GetSkillDistance's class and skill-tree bonuses are not ported. The map-name function's event and runtime
  branches are modelled as idle. World 115's name comes from runtime state.
- The character window's SetName labels are not GlobalText: they come from CharacterInfoSetup (NATIVE-LANG-002).
  The skill tooltip body keeps its stand-in (its source is SkillTooltipText.bmd, see below).
- The inventory, character and chat label indices are static readings; menu indices are verified.
- A multi-item `--combat-script` cast nothing when its items were separated by spaces or commas; fixed by NATIVE-NPC-001.
- A new client build moves the addresses; the read must then be repeated.

# NATIVE-LANG-002: more tables, NPC dialogue text, item prices

NATIVE-LANG-002 reads five more tables from the same snapshot (`lang3.bin`; no new live read was needed), finds the
NPC dialogue text outside Lang.mpr, reconstructs the client's item price routines and surveys all tables. Labels
as above; "verified" means a Unicorn comparison with 0 mismatches.

## 1. New tables (verified)

| Table | Object, map | Client routines run in Unicorn | Plaintext |
|---|---|---|---|
| BuffEffect | `0x06fbb2a4`, +0x38 (437) | lookup `0x010de66f` (default +0x40 for a miss and for buff >= 0x1cb), by item `0x010de6d3`, getters `0x010de759` (+0x28), `0x010de7a3` (+0x40), `0x010de772`/`0x010de78a` (by item); the bufflist's addBuff `0x00c5f278`; the InfoPopup lines `0x01298a54` | `buffs.tsv` |
| CharacterInfoSetup | `0x06fbad18`, +0x38 (143) | lookup `0x010e5203` (default +0x44); the character window's row builder `0x00b3dedc` | `charinfo.tsv` |
| MonsterSoulConversion | `0x06fbbe1c`, +0x44 (5) | lookup `0x01135146` (ItemValue prices a listed code at 10000) | `soulconv.tsv` |
| SkillRequire | `0x06fbb248`, +0x54 (34) | static: `0x00abf829(group, index)` walks the map for the scroll item | `skillreq.tsv` |
| MUQuestString(kor) | `0x06fbbd9c`, +0x38 (1,975) | static: `0x00fe821e` hands the map to the quest window | `questtext.txt` |

**BuffEffect record** (0x44 bytes; data and consumers): `+0` index, `+4` group (buffs of a group replace each other,
`0x009584dc`), `+8`/`+0xc` the item that gives it (255 = none), `+0x10` name, `+0x28` type (addBuff: 1 = isDebuff,
2 = isCashBuff), `+0x2c` (`0x00c78d6b` skips 0), `+0x30`, `+0x34` `std::vector<std::string>` description,
`+0x40` value kind.

- **addBuff `0x00c5f278(buff)`** (the bufflist's GFx object): nothing for buff <= 0, >= 0x1cb or one of the hidden
  buffs of `0x00c5f53f` (0x53..0x55, 0x78, 0x19b..0x19f, 0x1be); else `BuffType`, `isDebuff`, `isCashBuff` and, for
  a non-debuff, `BuffDetailType` (group 0xf7 -> 1, 0xf6 -> 2, else 0), then `addBuff`. The movie draws the icon
  `icon_<BuffType>` from ImageData and calls back `onTooltip {BuffType, x, y}`.
- **InfoPopup lines `0x01298a54`** (the popup `0x00b8d4de`, from the bufflist's `onTooltip` `0x00c5efb4`): the name,
  a `"\n"` line, then: value kind 1 with a nonzero hero value (`0x01295d1c`) -> one line, the description lines
  joined (`0x01299f67`) used as the sprintf format of that value; value kind 2 -> nothing when the option
  singleton's predicate `0x010702e1` holds, else the joined format with its int (kind 0) or float (kind 1);
  otherwise the description lines. The popup paints the first line `0xffd8bc65` and the rest white through
  `0x0096fe90` (not reconstructed; the native popup uses the reconstructed InfoPopup assembly).

**CharacterInfoSetup record** (0xa4 bytes): `+0` id, `+4` label colour, `+8` label, `+0x20` value group, `+0x24`
`std::vector<int>` of 16 class flags, `+0x30` SetName type, `+0x34` sort, `+0x38` value colour, `+0x3c`/`+0x54`
prefix/suffix strings ("+", "%"), `+0x70`/`+0x88` two more strings, `+0xa0` button ("+" for the stats). The row
builder `0x00b3dedc` sends `ClearItems`, then for the hero's class index (`0x0095f5cc`: class & 0xf) every row
whose flag is set: types other than 2, 3, 5 at once in key order, the others collected in key order and ordered by
`std::sort` (`0x00b48089`, comparator `0x00b46e30`: sort less), each as
`SetName("%d %d %d %s %s %s %d", type, id, sort, line(label, colour), line("-", value colour), "", button)` with the
line builder `0x00ab4dc0`. The sort is MSVC's introsort (not stable above 32 rows): the native module ports it
and equals the client's order for all 16 class indices. These rows are the character window's labels (Class,
Level, Pts Remaining, Strength, * ATK Power, ...), which NATIVE-LANG-001 had looked for in GlobalText.

## 2. NPC dialogue text (verified): not a Lang table

NATIVE-NPC-001 inferred that NPCDialogue.bmd's text ids point into a Lang table. They do not: the dialogue manager
(`0x01ec9858`) has its own loaders, entered from code this capture does not restore (NATIVE-DATA-001 found them):

- `0x00fdcbb4` NPCDialogue.bmd: 88-byte records until a short read; key (NPC class << 16) + state; the value is the
  text id and ten (option text id, next) pairs; `std::map` insert at +4 (first record of a key kept);
- `0x00fdccc1` QuestProgress.bmd (41-byte records, map +0xc; not used by the dialogue window);
- `0x00fdcdc8` QuestWords.bmd: 6-byte header (u32 id, s16 length) and text, each unit decoded by `0x00976855`, the text
  read into one reused 0x500-byte buffer and taken to its first NUL; map +0x14.

Lookups: `0x00fdc9c1` text(id); `0x00fdca1b` state text; `0x00fdca92` option text; `0x00fdcb1f` option next (0 for NPC
0, -1 for an absent record or option). The window's choice `0x00be906d` shows the next state when it is <= 900 and
not -1 (`0x00be86de`), runs one of 20 server requests for 901..920 (packets C1 F6/F8; cases 902, 910, 915..920 also
close the window: static), else shows state 999. `reconstructed/npc/npc_dialogue.c` ports all of it; both files are
local and decoded by reconstructed/data, so no plaintext is needed.

`scripts/validate_npc_dialogue.py` runs the client's constructor and three loaders on the installed files (fopen,
fread and the heap modelled) and then its lookups and choice handler: text 2,986, state text 665, option text 6,650,
option next 6,650, choice 1,493 (26 server requests, 124 shown states, 1,343 state-999 fallbacks), 0 mismatches;
planted mistakes caught (a changed text, swapped option pairs, last-wins for a repeated key) and two positive controls
equal (first-wins, next 950 -> state 999); about 8 s.

## 3. Item prices (verified)

`reconstructed/price` ports ItemValue `0x0169320b..0x01696338` (`mu_item_price`) and ConvertRepairGold
`0x016b8d16` (`mu_item_repair_cost`, `mu_item_repair_price`). goldType 0 is the buy price (NpcShop's purchase
checks; the tooltip's GlobalText 0x654 "%s(%s)": the price with NpcShop's tax `+0xac` through `0x016b9103`, and the
plain price through `0x016b8b26`), 1 the sell price (the sell paths; GlobalText 0x3f; 1 when byte +4 of
`0x01d1dbd4` is set), 2 the repair base (`0x016c3cb5` and the repair-all sums, GlobalText 0xee). The routine reads
the record (fixed zen +0x28c, value +0x288, level, kinds), the object (level, durability or stack, excellent and set
bits, options, sockets with their seed spheres priced by a second ItemValue, harmony, period), the current world,
the sell flag, the socket manager, MonsterSoulConversion and the pet record; the header of
`reconstructed/price/item_price.h` lists them.

`scripts/validate_item_price.py` runs both routines for every installed Item.bmd code × 16 random object states ×
goldType 0/1/2 (world 0 or 0x5c, random flags) plus 2,000 synthetic records, and ConvertRepairGold on those values
and 20,000 random cases: ItemValue 236,288 cases (234,288 installed, 2,000 synthetic) and ConvertRepairGold 54,351
(34,351 from those values, 20,000 random), 0 mismatches, 5/5 planted mistakes in the C detected (258 s; every branch
counter reached, the seed-sphere recursion 20,302 times). **Inferred**: three compares of ItemValue's excellent-option switches are displaced by jumps out of the
restored image (`0x01694b6b -> 0x10b401b0`, `0x01694d5e -> 0x10b40050`, `0x01694e4b -> 0x10b40100`, an out-of-scope
module); the values left in the bytes behind them give the ladders 4/8/12/16 and 5/10/15/20, and the validator runs
the same reading there, so those three are checked for consistency only. The tooltip's buy line also sits after
such a jump (`0x00f0be4c -> 0x10b402a0`): its condition (shop item) is a static reading.

## 4. Native

- `native/core/mu_lang`: `mu_lang_buff_get/by_item/tooltip/addbuff`, `mu_lang_charinfo_get/rows`,
  `mu_lang_skillreq_item`, `mu_lang_soul_conversion`, `mu_lang_quest_text`; `mu-lang buff|charinfo|soul|quest`.
- The GFx layer: the bufflist channel (`mu_gfx_layer_add_buff`, addBuff after the movie's onLoad, onTooltip ->
  `cfg.buff_tooltip`), the character window's rows from CharacterInfoSetup (`mu_gfx_layer_set_char_rows`; the
  layer fills the hero values it has into Class, Level, Pts Remaining, the five stats and * ATK Power, "-"
  elsewhere, as the client's first SetName), npcdialogue's choice to the host (`cfg.dialog_choice`), the client's
  prices (`cfg.price_ex`) and the tooltip context (`cfg.tooltip_ex`: buy line on NpcShop items, sell line on
  inventory items while it is open).
- `world_gfx.c` (mu-world, mu-client): the dialogue manager from the game root (NPCDialogue.bmd + QuestWords.bmd) for
  the dialogue NPCs of ReceiveTalk (state 0 at open, the choice rule, requests logged and not played); ItemValue for
  the shop list, buying and selling (the object at full durability, no options: the native session has no server
  items); `--gfx-open "buffs=1:2:8"` lists demo buffs (labelled demo: no server) through the addBuff rule,
  `class=N` picks the character rows' class index (default 1).
- `mu-world --npc-script` verbs `tip:SLOT`, `tipinv:CELL`, `bufftip:BUFF` show tooltips headless.
- Plaintext directory (MU_LANG_DIR): the NATIVE-LANG-001 file names and formats are unchanged; new optional files
  `buffs.tsv`, `charinfo.tsv`, `skillreq.tsv`, `soulconv.tsv`, `questtext.txt` (same escapes; each optional).

## 5. Verification (Lang tables)

`scripts/validate_lang.py --snapshot lang3.bin --mutations` (about 40 s) adds:

| Family | Client routine | Cases |
|---|---|---:|
| buff | `0x010de66f`, every key + 63 absent / out of range | 500 |
| buff_item | `0x010de6d3`, every item code of the table + 50 absent | 171 |
| buff_getters | `0x010de759`, `0x010de7a3`, `0x010de772`, `0x010de78a` | 1,342 |
| buff_tooltip | `0x01298a54`, every buff × hero value {0, random}, value kind 2 × the option states | 892 |
| addbuff | `0x00c5f278`, buffs -2..0x1cf | 466 |
| soulconv | `0x01135146`, every code + 300 absent | 305 |
| charinfo | `0x010e5203`, every key + 40 absent | 183 |
| charinfo_rows | `0x00b3dedc`, class indices 0..15 (every SetName) | 16 |

0 mismatches; three more planted mistakes caught (a buff name, the order of two description lines, a row's sort).
Modelled: the client's sprintf `0x0098d0a9` (Python's printf conversions; the UCRT needs locale state this machine
does not hold), the ANSI -> UTF-8 conversion `0x00a99d93` (ASCII markers), the line builder `0x00ab4dc0` as a
marker (it is verified by NATIVE-HUD-001), the GFx object calls, the item cache `0x01298996`, the hero's buff value,
the option singleton, `__security_cookie` and the printf options word.

## 6. Survey of the 74 table objects

The startup routine `0x0115eceb` hands 74 objects of the manager `0x06fbaa60` to the table loader (with per-locale
script names; MUPassInfo/Mission/Reward/Buff/Shop share one object, ParticleSkill/Option/OptionText another).
"Consumer" is the most called routine with the object in ECX (`survey.py`, static); "Maps" the std::maps langread
copied into `lang3.bin` (offset: entries); tables without a map keep vectors or arrays that this snapshot did not
copy and need a wider read. "Status": **read** = converted, native and (except SkillRequire and MUQuestString)
verified; **map** = in the snapshot, layout open; **none** = not in the snapshot.

| Table | Object | Consumer | Maps | Status | Native need |
|---|---|---|---|---|---|
| EarringAttribute | `0x06fbaa60` | `0x010ed9f5` | +0x38: 16, +0x40: 8, +0x48: 15, +0x50: 8 | map | later: earring tooltips |
| EarringOptionText | `0x06fbaac0` | `0x010ee6a9` | +0x38: 31 | map | later: earring tooltips |
| PeriodExtendableItem(kor) | `0x06fbab00` | `0x011469a1` | — | none | no (cash-shop period items) |
| Text(kor) | `0x06fbab48` | `0x0095f027` | +0x38: 6,514 | read | yes: GlobalText (labels, map names, price lines) |
| Gate | `0x06fbabac` | `0x0110cbaf` | +0x38: 625 | read | yes: move window, gates |
| Credit | `0x06fbac20` | `0x010ea60c` | — | none | later: credits window (synthetic today) |
| Filter(kor) | `0x06fbac88` | `0x0110c9f2` | — | none | later: chat word filter |
| FilterName(kor) | `0x06fbacd0` | `0x0110cb45` | — | none | later: character-create name filter |
| CharacterInfoSetup | `0x06fbad18` | `0x010e5203` | +0x38: 143 | read | yes: character window rows (wired) |
| Slide(kor) | `0x06fbae00` | `0x011569bc` | — | none | later: notice slides |
| PentagramOption | `0x06fbae4c` | `0x011447ac` | +0x3c: 28, +0x44: 31 | read | yes: pentagram tier in item names (FIDELITY-001) |
| PentagramJewelOptionValue | `0x06fbaefc` | `0x011439c7` | — | none | later: pentagram tooltips |
| HuntingRecord | `0x06fbaf98` | `0x009616cc` | — | none | no (hunting record window) |
| ArcaBattleScript | `0x06fbb000` | `0x010c8a06` | +0x38: 13 | map | no (event) |
| ArcaBattleBootyMix | `0x06fbb068` | `0x010c7dc0` | — | none | no (event mix) |
| BonusExp | `0x06fbb0c8` | `0x010dd48d` | +0x38: 67 | map | no |
| Skill(Kor) | `0x06fbb138` | `0x00961620` | +0x9c: 0, +0xa4: 0, +0x108: 973 | read | yes: skills (wired) |
| SkillRequire | `0x06fbb248` | `0x00abf829` | +0x54: 34 | read | later: skill scroll tooltip (read, not wired) |
| BuffEffect | `0x06fbb2a4` | `0x010de66f` | +0x38: 437 | read | yes: bufflist and buff popup (wired) |
| AttributeVariation | `0x06fbb330` | `0x010d2013` | +0x38: 43, +0x40: 62, +0x94: 0 | map | later: elemental attributes |
| GuideQuest | `0x06fbb3d0` | `0x0111a0e6` | — | none | later: quest guide |
| GuideQuestString(kor) | `0x06fbb414` | `0x0111b8bf` | +0x50: 186 | map | later: quest guide text |
| MuunEffectInfo | `0x06fbb46c` | `0x00aed7c3` | +0x38: 16 | map | later: Muun pets |
| SocketItemUpgrade | `0x06fbb4ac` | `0x01157396` | +0x38: 117, +0x8c: 118 | map | later: socket tooltips/mix |
| SeedSphereUpgrade | `0x06fbb560` | `0x0115514f` | +0x38: 72 | map | later: socket tooltips/mix |
| MixSlotFrame | `0x06fbb5dc` | `0x01134eec` | +0x38: 46 | map | later: mix windows |
| ItemTRSData | `0x06fbb624` | `0x011204db` | +0x38: 4,919 | map | check: item display transforms (native uses itemtrsdata.bmd) |
| Npcname(kor) | `0x06fbb664` | `0x011427c7` | +0x38: 905 | read | yes: NPC/monster names (wired) |
| Dialog(kor) | `0x06fbb6d0` | `0x010eb205` | +0x38: 204 | read | later: NpcJobChangeQuest (demo dialogue fallback today) |
| RenderingData\EnchantEffect | `0x06fbb754` | `0x010ffddb` | +0x38: 2,464, +0x5c: 38, +0xa0: 0 | read | yes: item glow colours (wired) |
| LabyrinthOfDimensionInfo | `0x06fbb7fc` | `0x01124786` | +0x3c: 38 | map | no (event) |
| movereq(kor) | `0x06fbb84c` | `0x0113c3f5` | +0x38: 69 | read | yes: move window |
| 4ThTreeData | `0x06fbb8ec` | `0x010b4406` | +0x3c: 16 | map | later: 4th skill tree |
| 4ThTreeSkillTooltip | `0x06fbb930` | `0x010ba100` | +0x3c: 221 | map | later: 4th skill tree tooltips |
| ItemLevelTooltip | `0x06fbb9b0` | `0x0111e98b` | +0x38: 105 | map | later: item tooltip level lines |
| Event\EventFlag | `0x06fbba44` | `0x011072a2` | +0x38: 3 | map | no |
| MBoxShop(kor) | `0x06fbbaa4` | `0x011301ad` | — | none | no (cash shop) |
| 4thTreeSideOption | `0x06fbbaec` | `0x010b6ec4` | +0x3c: 16, +0x44: 2 | map | later: 4th skill tree |
| GradedOption | `0x06fbbb38` | `0x0110ddfb` | +0x38: 2 | map | later: item options |
| SpellStone | `0x06fbbba8` | — | — | none | no (no consumer in the restored text) |
| WingAttribute | `0x06fbbc50` | `0x011761cf` | +0x48: 1, +0x54: 8 | map | later: wing tooltips |
| ElementalMixList | `0x06fbbcc0` | `0x010fbe64` | — | none | no (mix) |
| MasteryItemBonusOption | `0x06fbbd18` | `0x0112f348` | +0x38: 18 | map | later: item tooltips |
| MUQuestString(kor) | `0x06fbbd9c` | `0x00fe821e` | +0x38: 1,975 | read | later: quest windows (read, not wired) |
| MUQuest | `0x06fbbddc` | `0x0113e6de` | +0x38: 484 | map | later: quest windows |
| MonsterSoulConversion | `0x06fbbe1c` | `0x011350f7` | +0x3c: 5, +0x44: 5, +0x4c: 27 | read | yes: ItemValue (wired) |
| MonsterSoulConversionDropInfo | `0x06fbbe70` | `0x011383e5` | +0x38: 5 | map | no |
| GuardianMix | `0x06fbbeb0` | `0x00cae7b0` | +0x38: 2, +0x40: 1, +0x48: 15, +0x5c: 55, +0x64: 2, +0x6c: 1 | map | no (mix) |
| GuardianTooltip | `0x06fbbf24` | `0x0111454d` | +0x38: 5, +0x40: 35, +0x48: 5, +0x50: 35 | map | no |
| MapSearchInfo | `0x06fbbf7c` | `0x0112de55` | — | none | later: world map search |
| JewelOfHarmonyOptionName | `0x06fbbfcc` | `0x011224c6` | +0x38: 44 | map | later: harmony tooltip lines |
| ErtelSetOption | `0x06fbc00c` | `0x00f160a6` | — | none | later: pentagram (errtel) tooltips |
| ErtelSetOptionText | `0x06fbc09c` | `0x00fcca1a` | — | none | later: pentagram (errtel) tooltips |
| ErtelSetOptionType | `0x06fbc0fc` | — | — | none | no (no consumer in the restored text) |
| ElementalUpgrade | `0x06fbc160` | `0x010fcfb5` | — | none | no (mix) |
| relationevent | `0x06fbc240` | `0x0114b765` | — | none | no (event) |
| EventMapSearchInfo | `0x06fbc3c8` | `0x01108192` | +0x6c: 10, +0xac: 0 | map | no (event) |
| ArtifactOption | `0x06fbc47c` | `0x010c9bde` | +0x38: 28, +0x40: 34 | map | later: artifact window |
| ArtifactSystem | `0x06fbc4c4` | `0x010cc691` | +0x38: 1, +0x40: 7, +0x48: 31, +0x50: 15, +0x58: 8 | map | later: artifact window |
| MUPassInfo | `0x06fbc524` | `0x0114f26d` | +0xc8: 5 | map | no (season pass) |
| RewardItemExchange | `0x06fbc704` | `0x01147c82` | — | none | no |
| CollectItemCount | `0x06fbc770` | `0x010e6156` | +0x38: 10 | map | no |
| MixExpectedResult | `0x06fbc7b0` | `0x01131281` | +0x38: 183 | map | no (mix) |
| MixExpectedResultTooltip | `0x06fbc7f0` | `0x011333d2` | +0x38: 13 | map | no (mix) |
| InvenItemAnimation | `0x06fbc830` | `0x0111d824` | +0x38: 5 | read | yes: GFx item models (FIDELITY-001) |
| WingCoreOption | `0x06fbc870` | `0x01177d56` | +0x3c: 1, +0x44: 10 | map | later: wing tooltips |
| ParticleSkill | `0x06fbc8bc` | `0x010bd33c` | +0x38: 16, +0x40: 21, +0x48: 2, +0x5c: 45, +0x64: 1, +0x6c: 3, +0x74: 3 | map | later: particle skill options |
| EventmapAndBossSetup | `0x06fbc9e4` | `0x0110545c` | +0x38: 3 | map | no (event) |
| ConfusionStoneMonsterSet | `0x06fbca28` | `0x010e6e74` | — | none | no |
| LegendaryWeaponSetOption | `0x06fbcaa0` | `0x01129c34` | — | none | later: set tooltips |
| LegendaryItemBonusOption | `0x06fbcb10` | `0x01126b79` | +0x38: 6, +0x60: 3, +0x68: 3 | map | later: set tooltips |
| LegendaryItemSetType | `0x06fbcba8` | `0x011289d6` | +0x38: 37, +0x40: 56 | read | yes: set-item prefix (FIDELITY-001) |
| CashItemSetOption | `0x06fbcc08` | `0x009e816c` | +0x5c: 78 | read | yes: set-item prefix (FIDELITY-001) |
| SpeedPlus | `0x06fbcc8c` | `0x0115ae18` | — | none | later: movement speed bonus |

## 7. Renders (local)

`~/Documents/mu-mac-tools/native/renders/lang2/`:

- `dialog/` (Sir Lesnar: state 0 "Are you here to join the Arca War?" with nine options, option 1 -> state 1 with
  "Go back.", back to state 0, option 2 -> request 908; frames 60, 80, 120);
- `shop/` (Hanzo the Blacksmith: the Kris's tooltip with "Purchasing price: 240(240)", buying it, the Blade +9's
  "Selling Price: 91,700" and the sale);
- `buffs/` (the bufflist with eight demo buffs, the Potion of Soul popup, the character window with
  CharacterInfoSetup's rows).

```sh
export MU_GFX_LIB=…/libmugfx.dylib MU_LANG_DIR=…/lang MU_GFX_SINGLE_BUFFER=1
native/build/mu-world --game-root "$MU_GAME_ROOT" --headless --backend gl --no-audio \
    --placement native/world/lorencia-demo-placement.txt --npc-demo native/world/lorencia-demo-npc.txt \
    --gfx MOVIES --tile 133,127 --npc-script "5:click:12 75:option:0 110:option:0 125:option:1" --frames 140 \
    --every 20 --out-dir DIR
# shop: --tile 138,123 --npc-script "5:click:smith 60:tip:0 90:buy:0 100:tipinv:0 115:sell:0"
# buffs: --gfx-open "character,buffs=1:2:8:11:29:35:55:320" --npc-script "40:bufftip:11"
scripts/validate_npc_dialogue.py --game-root "$MU_GAME_ROOT" --mutations
scripts/validate_item_price.py --game-root "$MU_GAME_ROOT" --mutations
```

## 8. Gaps

- The skill tooltip body is not a Lang table: the handler `0x00c7070d` builds it from SkillTooltipText.bmd and the
  master-skill tables (`0x00c1ef6b`, not reconstructed).
- Hero buff values (0x01295d1c), the option singleton of value kind 2, buff timers (SetInfoPopupBuffTimer with
  GlobalText 0x9e5/0x8fa..0x904) and bundles are not modelled offline; the bufflist shows demo buffs.
- The character window's values after the first SetName (SetCharacterInfo, TypeStat) are not reconstructed; the
  layer fills the values it has.
- Prices: the three displaced excellent-option compares are inferred; pet prices and socket seed tables are inputs
  the native session does not have (no pets, no sockets); NpcShop's tax is 0 offline.
- The dialogue's 21-wrapped-line option limit (0x00be8a9b) needs the client's font metrics; the quest-list mode
  (+0x1d04, texts 0x5dd/0x5de) and the server requests are not played.
- ItemTRSData exists in Lang.mpr (4,919 records); the native item rendering uses the local itemtrsdata.bmd: whether
  they differ is open.
