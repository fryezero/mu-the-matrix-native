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
- Not read: the other ~80 tables (SkillRequire, Slide, BuffEffect, the quest strings and others); the
  EnchantEffect map at `+0x5c`; the skill record's inner containers at `+0x64` and `+0x6c`.
- GetSkillDistance's class and skill-tree bonuses are not ported. The map-name function's event and runtime
  branches are modelled as idle. World 115's name comes from runtime state.
- The character window's SetName labels (Level, Class, Exp, ...) and the skill tooltip body keep English
  stand-ins; their GlobalText numbers are not mapped.
- The inventory, character and chat label indices are static readings; menu indices are verified.
- A multi-item `--combat-script` casts nothing in mu-world (pre-existing script handling); single items work.
- A new client build moves the addresses; the read must then be repeated.
