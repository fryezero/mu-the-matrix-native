# Skills in the interface (NATIVE-SKILL-001/002)

This note covers how the client loads its skill table, how the bottom bar shows and selects skills, how a skill
tooltip is built, and how the Skill Imprint window (`SkillStampFrame`) puts skills on the bar. It also covers the
checks a cast passes before it is sent. The routines are restated in C in `reconstructed/skill`, compared with the
client's instructions under Unicorn (`scripts/validate_skill.py`), and played in the native client by
`native/core/mu_skill`, the GFx layer and `native/world/world_gfx_skill.c`.

Pinned inputs as in the other notes: restored text capture09 (`2bd5f2e9…3724`, VA `0x00401000`) and second
image section run10 (`c985e2e6…a0672f`). The Lang tables come from the langread snapshot `lang3.bin`
([client-lang-tables.md](client-lang-tables.md)). No client bytes, tables or captures are committed.

Labels:

- **Verified**: the client routine ran in Unicorn and its outputs equalled the C.
- **Static**: a reading of the instructions that was not executed.
- **Modelled**: an input or a boundary the validator supplies (a stub, a Python statement).
- **Live**: seen in a window capture of the real client.

## 1. The skill table loader (verified)

NATIVE-DATA-001 found no loader for `skill.bmd` (no checksum key, path or caller in the restored text). This
build reads its skills from `Skill(Kor).txt` inside `Data/Lang.mpr` instead. That table is object `0x06fbb138`
(table manager `0x06fbaa60` + `0x6d8`), loaded by `0x0115eceb` through the generic table loader `0x010d68e1`.

The generic loader's body jumps into the packed section, so it stays opaque. It hands each tokenised row to the
table's own row parser, which is slot 2 of the table's vtable `0x01ac1d7c`:

```
bool __thiscall SkillTable::ParseRow(int line, std::vector<std::string> *row)    0x01170ca5
```

The parser works like this:

- It returns 0 when the row has fewer than 52 columns (`0x34`).
- It reads 61 columns in a fixed order, so a row with 52 to 60 columns makes it read past the vector.
  `mu_skill_parse_row` rejects such a row instead.
- Integers go through `boost::lexical_cast<int>`: `0x00cd80e9` → try-parse `0x00cd8314`. That allows an
  optional sign, decimal digits only and the int range.
- Column 45 goes through `lexical_cast<bool>` (`0x010c2add` → `0x010c2ce2`): `0`/`1`, with leading zeros and an
  optional `+` (or `-` before 0).
- A failed cast throws. The catch logs the line (`0x010d7e03`) and the row is dropped.
- The name (column 1) is taken between a leading `"` and the last `"` (`0x010bb278`). Otherwise the record keeps
  its constructor's name, `"null"` (`0x0116dcb9`).
- The record (0xd0 bytes) is inserted with `std::map::insert` at `this+0x108`, so a repeated index keeps its first
  record.

Columns, record offsets and names:

| Column | Offset | Name | Evidence |
|---:|---|---|---|
| 0 | +0x04 | index (map key) | verified |
| 1 | +0x08 | name (std::string) | verified |
| 2..5 | +0x20..+0x2c | level, damage, mana, AG | GetSkillInformation `0x01696458` (verified, LANG-001); level is data |
| 6, 7 | +0x34, +0x38 | distance, delay (ms) | GetSkillDistance, StartSkillDelay (verified) |
| 8 | +0x44 | energy requirement | stat check `0x0109228f`, tooltip label GT `0x18c4` "Energy %d" (verified) |
| 9 | +0x3c | strength requirement | GT `0x18c1` "Strength %d" |
| 10 | +0x40 | agility requirement | GT `0x18c2` "Agility %d" |
| 11 | +0x48 | command requirement | GT `0x18c5` "Command %d" |
| 12 | +0x4c | vitality requirement | GT `0x18c3` "Health %d" |
| 13 | +0x50 | MasteryType (element 0..6) | tooltip element lines (verified) |
| 15, 16 | +0x58, +0x5c | SkillUseType, brand | icon sheet; GetSkillInformation |
| 18..20 | +0x64 map | keys 0x80, 0x40, 0x20 | static (meaning open) |
| 21..36 | +0x6c map | one value per class index 0..15 | static (class requirement; not in the snapshot) |
| 39 | +0x7c | master factor | GetSkillInformation reads its low byte |
| 43, 44 | +0x8c, +0x90 | Magic_Icon, type | icon draw; onSelectSkill's type 7 rule |
| 45 | +0x94 | bool | `0x0109260c`: special-item skill |
| 52, 53 | +0xb0, +0xb4 | transformation rule, required weapon kind | usability check `0x010918c7` (static) |
| 54..57 | +0xb8 vector | pairs, pushed when the first column is not -1 | verified |
| 58 | +0xc4 | elemental imprint bonus % | tooltip GT `0x12b5`/`0x12b6` (verified) |
| 59 | +0xc8 | column != 0 | verified |
| 60 | +0xcc | damage type | the bar's damageType (verified) |

Columns 14, 17, 37, 38, 40..42 and 46..51 keep layout names (`x54`, …). The column order puts energy before
strength. That is why NATIVE-LANG-001 found Poison's 140 at +0x44.

`scripts/live_lang_to_plain.py` now also writes `skills_ext.tsv` with the record fields that `skills.tsv` lacks.
It reads them from the same snapshot, so no new live read was needed. The two inner maps and the pair vector are
not in the snapshot.

## 2. The bar

The main movie's `SkillHotKeyPage` (`main.swf`) shows ten slots and a selected slot. It reports `onSelectSkill`
(clicks and the digit keys), `onSkillTooltip`/`offSkillTooltip` and `onOpenSkillWindow` (a click on the selected
slot). The game side is the main frame's handler.

- **Feed `0x00c58797`** (verified). The handler is called every frame from `0x00c712bf`. It compares the bar
  state at handler +0x1c..+0x30 with these sources:
  - the hero's elemental attribute (hero +0x3268);
  - the hotkey manager `0x01d1df5c` (+0 the selected skill, +0xc `std::map<slot, skill>`);
  - for each skill, usability = `0x010918c7` && `0x01096e55`.

  It sends `SetSkillSlot` only when something changed. The members, in order, are `Elemental`, `SelectSlot`
  (`0x00a0811a`: the slot holding the selected skill, else the first non-empty slot), `SelectUseSkill`,
  `SelectSkill`, `SelectSkill_damageType` (record +0xcc) and `arrSlots` [{slot, skill, isUse, damageType} × 10].
  `isUse` = false makes the movie show the grey icon. The client never calls `setSelectSkill`: the selection
  reaches the bar through this feed.
- **onSelectSkill `0x00c70f4b`** (static). The client does this:
  1. It takes the stamp manager's entry of the slot (`0x01096927`) and finds the entry's skill in the learned list
     (`0x01096951`: attributes +0x1e4 count, +0x1e6 u16 ids).
  2. If the hero is mounted (+0x38 set, +0x39 == 7), only skills of type 7 are allowed.
  3. It sets CurrentSkill (hero +0x32), and the hotkeys select it (`0x00a079d2` → `0x00a081eb`).
- **Delay** (verified):
  - StartSkillDelay `0x01696aca` takes the record's delay (+0x38). It subtracts `(int)(master value × 1000)`
    when the master-skill manager has one (`0x00bb1ea1`/`0x00bb1ed0`). The class skill tree's node can cancel the
    delay (value `0x3fb` == 1) or shorten it (minus value `0x3fa`).
  - It then sets the timer (attributes +0xccc, one i32 per learned entry) of every learned entry of that skill
    whose timer is 0, and sends `onUseSkillDelay({skill, delaytime})` to the bar.
  - Skills with base `0xdd`/`0xde` share their delay (`0x01696ca6`).
  - IsSkillReady `0x016969e9` refuses an entry whose delay is > 0 and whose timer is > 0.
  - The tick `0x01696e06` subtracts the frame time and stops at 0 (at most 929 entries).
- **Class special cases `0x01096e55`** (verified). For class index 5, base skills 0xdf, 0xe0, 0xe1, 0x120, 0x80b and
  0x80c need buff 0x12d. For class index 1, base skill 0x5df needs 0x145.
- **Stat check `0x0109228f`** (verified). Every requirement must be met. For class index 1, when a skill asks for
  both strength and energy, either one is enough. The stats are u16 values at attributes +0x18a..+0x192.
- **Usability `0x010918c7`** is now reconstructed and verified, including its weapon, buff, world and item
  branches. Section 9 records the checks and the native host's input boundaries.

The cast path is the use controller `0x0107e99a` (static). It runs `0x0109274a`, `0x01091022`, `0x010918c7`,
target selection, the mana check below, IsSkillReady (`0x0107ef3a`) and then the attack request.

**Mana/AG check `0x01091692`** (verified):

- It reads GetSkillInformation's mana and AG for the skill. Skills 0x3a and 0x28 use 0x28's values, and 0x18b and
  0x188 use 0x188's; the AG of 0x28 and 0x188 is zeroed.
- Base skill 0x18 (Triple Shot) with buff 6 or 0x8f adds the byte at `[0x01d1df18]`+0x2ded to the mana.
- Buffs 0x125/0x127/0x128 add 250 mana; buffs 0x126/0x12a/0x12b add 2 AG.
- When mana is short, the client uses the first mana potion the inventory finder returns (`0x00b920bc` →
  `0x00960420`) and refuses this cast. A short AG also refuses it.

Mana does not grey the bar: the bar's `isUse` has no mana test.

## 3. The tooltip

**Main's onSkillTooltip `0x00c7070d`** (static) takes the stamp manager's entry of the skill (`0x01096aa7`). Its
fields are +0 base skill, +4 learned skill and +8 the imprint flag. The SkillInfoPopup handler (GfxMgr + `0x218`,
ctor `0x00c1ee29`) then shows it at (x + w/2, y) (`0x00c1ef6b`).

**Builder `0x0117da56`** (verified on all 592 installed SkillTooltipText records). `this` is the SkillTooltipText
table (loader `0x0117d758`: count, records XORed with FC CF AB, checksum `0xe2f1`, `map<u16, record*>` at +4,
first record of a skill wins). The builder fills the classic text list (TextList `0x10c76988`, 80 lines of 0xff
bytes, TextListColor `0x10c7b938`, TextBold `0x10c7ba78`), line by line:

1. The title is the record's name (colour +0x104), or GlobalText `0x4b0` for skill 60 with a weapon of kind 0x42.
   It is bold.
2. Then come the requirements of the base skill (`0x00bb1c32`), joined by GT `0x18c6` (" / ") with the last
   separator erased. The line is red (colour 2) when any stat is short, and a "  " line follows it.
3. Next comes "Mana %d / AG %d" (skipped when both are 0), then "Range %d / Cooldown: %.1f sec.". The cooldown is
   reduced by the class tree node or the master skill.
4. For types 0 and 7, "Basic Skill Damage %d" follows. Its value is the character machine's `0x00a01692` plus two
   option values and `[0x06fb4528]`. The line ends with "(+%dImprint)" (imprinted:
   `floor(level × imprint / 100)`), with "(Elemental Imprint Bonus %d%%)", or with nothing when the skill has no
   element.
5. Then comes the element line: GT `0x12b7`/`0x12a2..0x12a6`/`0x170a` when imprinted, else `0xe99..0xe9d`/`0x1709`.
6. The description and the third text follow, each when its condition holds (0 always, 1 learned, 2 not learned).
   Each comes after a "\n" line and goes through the wrap.

The value texts of skills 0x389, 0x38a and 0x82a use the formula manager (`0x0117b5eb`, modelled). The other
records add the master value when value_b is 0. The "related skills" call `0x00bb1f4a` passes its two words by
value, so it has no effect.

**Wrap `0x011ff794` → `0x01193941`** (verified with a modelled `GetTextExtentPointA`):

- The text is split at `#`, and each piece gets a leading space.
- The piece is then cut by width: a line keeps the characters whose prefix measures less than
  `width × [0x06fbcd94]`, where the width is 150 and `[0x06fbcd94]` is the client's screen rate (window width / 640).
- The text is measured with the unscaled interface font. A full wrap reports `max_lines + 1` lines.

The live capture confirms the screen rate. At 1722 pixels, Cyclone's description stays on one line. The native
book now passes the window width.

**Popup `0x00c1f2b0`** (verified):

- The title is line 0 and the body is lines 1..n-1, both through the HTML line builder `0x00ab4dc0` (NATIVE-HUD-001).
- A line starting with '\n' becomes `<BR>`.
- Both are converted to UTF-8, and then the client sends
  `SetInfoPopupSkillStamp("%d %d %d %d %s %s %d", x/rate, y/rate, w/rate, h/rate, title, body, 0)` and Open.

The builder starts with a call into a runtime module (`0x0117db7a` → `0x10b3efb0`, 72 NOP bytes), the same patch as
the item tooltip builder's header. It is opaque. Colour and bold entries the builder does not write keep their
old values in the client and are 0 natively.

## 4. The Skill Imprint window (`SkillStampFrame`)

- **Opening.** The U key in the client's key scan (`0x00efcea8`: `0x00ec53a7(0x55)` → GfxMgr + `0x214` → toggle
  `0x00aae767`) and main's onOpenSkillWindow open the window. The handler's ctor is `0x00c1f99c`, its vtable
  `0x01a995d0`.
- **Creation `0x00c1fb1b`.** It sends:
  - `InitText`(GT `0x1299` "Skill Imprint", `0x129c`, `0x129d`, `0x129e`, `0x129f`);
  - `InitButton`(`0x129a`, `0x129b`, `0xdaf` Save, `0xe5` Cancel);
  - `InitStampExplain`("%s\n %s" of `0x12a0`/`0x12a1` and of `0x12ae`/`0x12af`).
- **Open `0x00c2008b`.** It sets both pages to 1 and sends `UpdateSkillPage(page)`. The refresh `0x00c20ee4`
  sends `SetStampDamage("%d %s %s", elemental, …)`; without a pentagram that is GT `0x12ac`/`0x12ad`. Then the
  stamp manager rebuilds, and `SetSkillSlotSize`.
- **Slots.** The movie reports 20 slot positions (`requestSkillSlotInfo`) and their size. Slots 0..4 are the five
  bar slots of the shown select page (0: bar slots 1..5, 1: 6..10). Slots 5..19 are the learned list's page:
  15 per page, with learned index = (page − 1) × 15 + slot − 5 (`0x00c22588`). Pages are 1..⌈count/15⌉
  (`0x00c21b0b`, `0x00c21aa2`).
- **Drag.** `requestSkillSlotDragStart(i)` stores the source (+0x1fc). `requestSkillSlotDragEnd` makes the game
  invoke `CheckOverSlot`, and the movie answers `DragEndSlotIndex_Mouse(target)` (+0x200). The apply step
  `0x00c2226c` (static) then does one of these:
  - a bar slot onto a bar slot swaps the two (`0x01096e15`);
  - a learned slot onto a bar slot assigns the skill (`0x01096c42` takes it off its old slot, `0x01096d10` puts
    it on the new one);
  - a skill that is not learned gives GT `0x12bb`.

  The select page then follows the target.
- **Save and Cancel.** Save (`0x01096d2a`) sends the slots to the server and prints GT `0x12c1`. Cancel
  (`0x01096dd0`) restores the slots. Closing with changes asks for confirmation (GT `0x12ca..0x12cd`); the native
  layer restores the slots instead (layer choice).
- **Icons.** The game draws the window's icons itself with `0x01097130` (verified):
  - The bitmap is chosen by SkillUseType: 0/1 → `0x7c40` newui_skill00 / `0x7c43` newui_non_skill00; 3/4 →
    `0x7e18` (+1 per 450 icons) new_Master_Icon / `0x7e1a` new_Master_Non_Icon; 7..9 → `0x7e1c`/`0x7e1d`
    4th_Skill_Icon (also needing `0x00c2a37a`); 14 → `0x7e22`/`0x7e23`.
  - The icon is the normal one only when the skill is learned and usable.
  - The cell is `Magic_Icon % 450` in a 25-wide grid of 20 × 28 texels on a 512-texel sheet; skills 0x78..0x7c use
    their own number as the cell.
  - Under it the legacy delay overlay `0x00f18574` draws a quad of colour (1, .5, .5, .5) over the remaining part.
    That colour is static, read from the parallel routine `0x01696f56`.

## 5. Validation

`scripts/validate_skill.py --snapshot lang3.bin --cases 500 --mutations` (Unicorn, local) gives:

| Family | Client routine | Cases | Mismatches |
|---|---|---:|---:|
| lexcast | `0x00cd8314`, `0x010c2ce2` | 872 | 0 |
| row | `0x01170ca5` + lookup `0x00961620` (incl. the catch path) | 500 | 0 |
| req | `0x0109228f` (every snapshot skill × 3) | 2,925 | 0 |
| mana | `0x01091692` (GetSkillInformation for real) | 977 | 0 |
| delay_start / ready / tick | `0x01696aca` (+ `0x01696ca6`), `0x016969e9`, `0x01696e06` | 500 / 484 / 500 | 0 |
| special | `0x01096e55` | 2,940 | 0 |
| feed | `0x00c58797` (three calls per case: change detection) | 500 | 0 |
| icon | `0x01097130` (RenderBitmap and the overlay call recorded) | 973 | 0 |
| wrap | `0x011ff794` / `0x01193941` | 500 | 0 |
| tooltip | `0x0117da56` over the 592 installed SkillTooltipText records | 592 | 0 |
| tiphtml | `0x00c1f2b0` (SetInfoPopupSkillStamp, the rectangle, Open) | 500 | 0 |

That is 12,763 cases, 0 mismatches. The run also planted 11 mistakes in `libclientskill` (`-DMU_SKILL_MUTATION=1..11`,
one per family) and all 11 were detected. The full report is in `evidence/native-skill/validate-500.json`.

Modelled:

- Import calls stop a case. The heap, the C++ locale (classic), the CRT per-thread data and `_mbclen` (single-byte
  text) are stand-ins.
- The client's `sprintf` is a Python statement of the conversions the tables use, the same set
  `mu_skill_format` restates.
- `GetTextExtentPointA` is a per-byte width table shared with the C.
- The managers each family names (master skills, class tree, buffs, inventory, GFx value objects) answer with case
  values. The runtime header call is a no-op.

Portable tests:

- `reconstructed/skill/test_skill.py` has 12 tests: independent statements of the casts, the column order, quotes
  and rejects, the stat, mana, delay, feed and icon rules, the tooltip lines, the wrap and the format.
- `native/tests/test_native_skill.py` runs the book over a synthetic Lang plaintext and a synthetic
  SkillTooltipText.bmd, and the layer on the stand-in libmugfx. Two private tests run the book on the installed
  tables and the validator.

## 6. Native client

- **`core/mu_skill`.** It builds the table from `MU_LANG_DIR` (`skills.tsv` + `skills_ext.tsv`) and the tooltip
  texts from `Data/Local/skilltooltiptext.bmd` (core/mu_data). It holds the hero's learned list, timers,
  CurrentSkill and hotkeys.
  - OFFLINE DEMO: class lists. The Blade Knight hero's bar has melee skills, Blood Storm (a master skill with a
    5 s delay) and wizard skills, one of which (Inferno, energy 724) is greyed.
  - It provides the feed, select, cast (stats, class cases, IsSkillReady, mana/AG, StartSkillDelay; the demo spends
    the mana/AG), the tooltip HTML and the icons.
- **GFx layer (`mu_gfx_layer_set_skill_host`).** It plays:
  - SetSkillSlot every logic step when the feed changes;
  - onSelectSkill → host;
  - onSkillTooltip → SkillInfoPopup.SetInfoPopupSkillStamp;
  - onUseSkillDelay;
  - U and onOpenSkillWindow → SkillStampFrame, with its creation/open invokes, slot rectangles, hover tooltips,
    drag through CheckOverSlot, Save/Cancel/close.
- **`world/world_gfx_skill.c`.** It draws the window icons from the client's skill sheets (the bitmap and cell of
  `0x01097130`) and the delay overlay.
- **`mu-world`/`mu-client --gfx --combat`.** A right click on a monster casts the bar's selected skill through the
  checks, then `mu_combat_cast` draws it (NATIVE-COMBAT-001/002). `--skill-script "F:select:SLOT F:cast:ACTOR
  F:open F:drag:FROM:TO F:over:SLOT F:save F:tip:SLOT"` drives it in headless GL runs. `MU_GFX_NO_SKILLS=1` turns
  the skill host off.

Renders and live captures stay local in `~/Documents/mu-mac-tools/native/renders/skill/`: `t1/` (the window),
`combat/` (casts, delay and grey icons on the bar, the tooltip) and `live/`.

**Live capture** (2026-10-21, game lock, about 105 s, Nighty on MTM-1, read-only: no movement or casts). It shows:

- the bar with the real skills and their imprint markers;
- the Skill Imprint window (U) with its learned page and five bar slots;
- a bar tooltip.

The structure matches the native window and tooltip. The tooltip confirms the wrap's screen rate and the imprinted
forms "(+224Imprint)" and "Imprint All Elements". The real window opens further from the corner than the movie's
authored position (8, 0). Section 9 explains and reproduces that placement.

## 7. Remaining gaps after NATIVE-SKILL-002

- The generic Lang loader and tokeniser remain opaque. The new `lang5.bin` read includes the skills' inner maps
  at +0x64/+0x6c; the pair vector is still absent.
- FormulaData execution is a modelled boundary. Native callers can provide `mu_skill_book_set_formula`; without
  one, level-zero formula values are 0. Demo learned values and next values are explicit server stand-ins.
- The 4th/5th tables and their dependent managers are not decoded or reconstructed. Their original windows are
  registered but have no invented nodes or item cards. Section 10 records the missing inputs.
- The full cast controller, authoritative equipment/buff/event/party feeds, cast answers, damage option bonuses,
  pentagram damage packets and the opaque tooltip header remain open. The preview uses labelled demo state.
- The client's measuring font (GlobalText[0], at the 640-unit height) is CoreText's version of that face.

## 8. The server's skill packets and the managers they feed (NATIVE-SKILL-002)

This build numbers its packets itself. The receive dispatcher `0x01287ead` sends opcode **0xA0** to the
sub-dispatch at `0x0128805c` (sub = packet[3] for a C1 head, packet[4] for C2). Its sub **0x20** is the skill list
(`0x0126176e`) and sub **0x03** the saved hotkeys (`0x0126f225`). Only game logic is restated here; the C3/C4
decryption and the login packets stay out. `reconstructed/skill/skill_list.c` holds the C, and
`scripts/validate_skill_server.py` runs the client's routines in Unicorn.

**The skill list `0x0126176e`** (verified). packet[5] is 0xFF (one skill removed), 0xFE (one skill added) or the
count of a full list. The entries are 4 bytes from offset 7, with the skill as a u16 at entry +1.

- **0xFF**: the first learned entry holding the skill becomes 0. The stamp manager forgets it (`0x010960a8`) and
  the hotkeys drop it (`0x00a07ebb`). When it was the last entry, the count shrinks to the last non-zero entry
  before it.
- **0xFE**: when the skill is not among the first 150 entries, it takes the first zero one. Then come the stamp
  manager's add (`0x01095f5c`), the hotkeys' add (`0x00a07c8a`, the listener `0x00c5ea96` and GfxMgr →
  `0x0095f986` → `0x00ba7366`), the count (when the entry is the count) and GfxMgr +0x1f8 → `0x00c26ad8`.
  CurrentSkill moves to the new entry when it pointed at the skill's brand (`0x00a002d4`): a master upgrade takes
  over the selection.
- **Full list**: the list (0x3a1 u16 entries) is cleared and gets the skills whose use type (+0x58) is not 3. Master
  passives stay out, but every skill reaches the stamp manager's add and the hotkeys' learned map (`0x00a07a11`,
  the listener `0x00c5e991`).
- **Then**, for all three: the stamp manager's imprint refresh (`0x010961b0`). CurrentSkill is reset when it is
  past the count, when the count is 1, or when its entry is 0, and it then skips empty entries and the skills
  0x43..0x48 (a byte that wraps). Last, the hotkeys select it (`0x00a079d2`).

**The saved hotkeys `0x0126f225`** (verified for its skill part). Ten big-endian u16 skills come from offset 4
(0xFFFF none). Skill 0x12a records its key in stamp +0xa8. Every other skill puts its stamp entry into the window
slot of its key (`0x01096cba`: key 0 is slot 9, key k slot k − 1). Then come Save (`0x01096d2a`) and the
CurrentSkill rule `0x01096f37`. That rule keeps CurrentSkill when a bar slot shows it. Otherwise it takes the
learned index of the first window slot. When there is none, it keeps CurrentSkill if the skill is usable
(`0x010918c7` && `0x01096e55`), else it takes the first special entry of brand 0x4b. The handler's other fields
(item hotkeys, options) are not read here. It ends with the bar's rebuild `0x00a08330`.

**The Skill Imprint (stamp) manager**, the static at `[0x01d1dbcc]` (getter `0x0095f861`):

| Offset | Content |
|---|---|
| +4 / +8 | the class byte it was built for (attributes +0x187), the hero's element |
| +0xc / +0x18 | `std::vector<entry*>`: the Basic Skill and Special Skill tabs; entry = {+0 base, +4 learned (0: not learned), +8 imprint} |
| +0x24 / +0x4c | entry*[10]: the window's slots and the bar's slots |
| +0x80 | the learned skills of the saved bar; +0xa8 the key of skill 0x12a (−1) |

- **Reset `0x01095c77`**: both slot arrays are cleared. For a new class byte (`0x01095ee9`), the basic tab is
  dropped and refilled (`0x01095d30`). That fill takes the class's skills of brand 0 with use type 0/4/8/14, in key
  order, without 0, 0x42 and 0x12a. Class indices 10..15 use `0x0109630b` instead: types 0/4, then 8/14. For the
  same class byte, the learned skills and imprints are cleared (`0x0109664d`, `0x0109658a`). The special tab is
  always rebuilt from the class's skills of brand 0x4b (`0x01096710`). "The class's" means the record's class map
  +0x6c holds the class index with a value above 0 (`0x01098644`).
- **Add `0x01095f5c`**: base = the master manager's base skill (`0x00bb1c32`, the end of the brand chain). The
  first basic entry of that base takes the skill, unless the skill already lies behind the entry's learned skill
  in the chain (`0x00bb1c10`). With no basic entry, the first special entry of the base takes it.
- **Remove `0x010960a8`**: the first entry of the base that holds exactly that skill gets 0.
- **Refresh `0x010961b0`**: imprint = the learned skill's element (+0x50) equals the hero's non-zero element, or
  is 6 (all elements).
- The bar slots, Save (`0x01096d2a`: the bar takes the window's slots, +0x80 their learned skills), Cancel
  (`0x01096dd0`), a slot's skill (`0x01096a19`/`0x01096a60`: learned, else base), find by skill (`0x01096aa7`:
  base or learned, basic tab first).

**The hotkey manager `0x01d1df5c`**: +0 the selected skill, +4 `std::map<int, std::string>` of the learned skills
(keyed by the record's index), +0xc `std::map<slot, skill>`.

- `0x00a08330` rebuilds the slot map from the stamp manager's bar slots (each slot's entry's learned skill).
- `0x00a081eb` selects a skill. It does nothing for 0 or the selected one. A skill not in the learned map, or one
  of use type 3, selects 0. Otherwise it notifies GfxMgr → `0x00995257` → `0x00b40380`.
- `0x00a07ebb`, the remove, calls select(0) for the selected skill. That does nothing, so the selection stays.

**The Skill Imprint window** (static, the routines behind it verified above): its learned page is the stamp
manager's tab (`0x00c22588` → `0x010968c6`). The page count is the tab's entries / 15 (`0x00c21b0b`). The tab
buttons set the handler's +0x8c. Save (`0x00c20db4`) runs `0x01096d2a`, `0x01096f37` and `0x00a08330`; Cancel
runs `0x01096dd0`. The stamp manager's reset runs in the window's `0x00c2008b`.

**Validation** (`scripts/validate_skill_server.py --snapshot lang3.bin --cases 500 --mutations`):

| Family | Client routines | Cases | Mismatches |
|---|---|---:|---:|
| list | `0x0126176e` with the stamp manager, the hotkey manager and `0x00bb1c32`/`0x00bb1c10` running for real | 300 | 0 |
| keys | `0x0126f225` to `0x0126f2fa` (keys, Save, `0x01096f37`), then `0x00a08330` | 500 | 0 |
| stamp | `0x01095c77` over synthetic Skill(Kor) maps with class maps, then `0x010961b0` | 500 | 0 |

Four planted mistakes (`-DMU_SKILL_MUTATION=12..15`) were all detected. Modelled: the GfxMgr windows the routines
notify, the hotkey listener `[0x01d22c60]`, the usability answer and the debug-log switch `0x0095fbdc`.

**Native client.** `core/mu_skill` keeps a stamp manager and a hotkey manager. The bar is the hotkey manager's
slot map. `mu_skill_book_receive` takes the packets. `core/mu_skill_demo.c` is the **offline demo server**: at
login it sends the class's skill list and saved bar; a script can send `learn:SKILL` / `forget:SKILL` (0xFE/0xFF);
`MU_SKILL_DEMO=FILE` replaces its table (`list CLASS SKILL...`, `keys CLASS K1..K9 K0`). The stamp manager's tabs
need the records' class maps. `live-readers/langread ... nested:0x6d8` copies them, and
`scripts/live_lang_to_plain.py` writes `skills_class.tsv`. Without that file, the demo's list stands in as the
class map. The window shows the tabs, edits the window slots and saves them to the bar.

## 9. Usability, damage, Imprint markers and window position

`skill_canuse.c` restates `0x010918c7`, its world predicate `0x00a9b235` and SkillRequire `0x01092213`.
The checks run in instruction order: use-type 2/siege, stats, transformation, weapon kind, rings, world,
skill-specific buffs/items, prerequisites, party, class-tree learning and the map-window rule. The 18 weapon
cases read the equipped item's kind byte through `0x00987982`; kinds 15/16 instead check the rendered weapon
model. Rings 13/10 at levels other than 2 and 13/68 block use. SkillRequire takes the base skill's record from
the map at `0x06fbb248+0x54`: +0x10 required skill, +0x14 master skill, +0x18 master level. The required skill
can appear directly or behind a learned skill's brand chain. These are verified outputs with the outside
managers answering explicit case values.

One static reading in the R2 scratch notes was wrong. For skill `0x82a`, instruction `0x01092042` jumps onward
when buff `0x1bb` is absent. A present buff blocks use. The initial broad run found one disagreement among
2,000 usability cases. Correcting the branch and adding all eight combinations of confusion-world membership,
the global flag and buff presence removes it. Mutant 20 reverses that branch and is detected.

`mu_skill_book_usable` now calls this routine and `0x01096e55`, so its result reaches the bar's `isUse`, window
icons and cast gate. The world host supplies the current world and demo buffs. Its equipped right-hand sword
is an explicit demo input, not a recovered equipment feed. `skillreq.tsv` supplies prerequisites, and the
Master manager supplies learned levels. Unprovided event/party/special-item/4th-tree answers retain the
documented defaults in `skill_canuse.h`; passing the native preview is not evidence for those live feeds.

Skill damage `0x00a01692` is in `master_tree.c` and is verified against the actual instructions. It walks the
brand chain, takes the base record's damage, or its master value/formula for use type 4, and adds each upgrade's
truncated master value only when its flag is 1. `mu_skill_book_tooltip_lines` now uses it. The same Master
manager supplies delay and tooltip value lookups. FormulaData remains an explicit modelled boundary.

The window's marker `0x0109750c` draws only learned, imprinted entries, using bitmap `0x7e26`,
`Interface/SkillStamp.tga`, a 128×32 sheet. UV is `(cw/128*(element-1), 0, cw/128, ch/32)`. The damage-type
icon `0x01097601` requires positive damage type and a learned skill and uses bitmap `0x8313`,
`Interface/DamageTypeIcon.tga`, 64×32. Its UV is `(21/64*(type-1), 0, 21/64, 23/32)`. Both routines are
verified. The native overlay uses the movie's `requestStampRelativePosition`, observed as `(16,-2)`, and draws
the 17×17 marker at that scaled offset. The damage icon sits at `(-6,5)` from the skill origin. Placement is a
static reading of `0x00c202d7`; the texture/visibility routines ran in Unicorn. The bar draws its own stamp and
damage-type clips from `SetSkillSlot`, as before.

The Imprint window is alignment 9, not a fixed corner window. The creator `0x00ac9edc` skips initial alignment,
but `0x00acb333` → `0x00ac09b2` → `0x00aae4ae` subsequently sends `SetWindowSize` to every window. Its
MUComponent prototype first captures the movie's authored 1024×768 stage. For an authored origin `(8,0)` and
size 327×639, the movie preserves its centre's screen fraction:

```
s = H < 700 ? 0.83 : 1
x = max(0, (8 + 327*s/2) * W/1024 - 327*s/2)
y = max(0, (639*s/2) * H/768 - 639*s/2)
```

These are static game-side and ActionScript readings, checked by running the original converted movie. Native
startup now advances that movie on its authored stage before setting the native viewport and sending the size.
At 1280×800 it reports `(50.85,13.30)`, the twip-rounded expected position. Opening preserves it, and dragging
still updates `requestWindowPos`. The earlier live 1722×1048 capture also agrees within its transparent art
margins. No new live game session was needed for this continuation.

## 10. MasterSkillTree, server answers and the later trees

The Master manager is the MasterSkillTree handler, constructor `0x00baf1ef`, GfxMgr +0x1f4. Its maps are
+0xb8 learned `{level,value,next,flag}`, +0xc0 movie-slot nodes, +0xc8 tooltips and +0xd0 movie positions.
The class switch `0x00baf92c` maps stage/base codes `0x20..0x4f` to a class mask and GlobalText IDs. The
native demo uses class byte `0x81`, whose tree code is `0x41`. The installed MasterSkillTreeData and
MasterSkillTooltip decode through the existing checked fixed-table codec, key `0x2bc1`, 2,048 records each.
No decoded records are committed.

The node record is 24 bytes: slot +0, class mask +2, group +4, point cost +5, maximum level +6, arrow +7,
prerequisites +8/+0xc, skill +0x10 and formula +0x14. The 808-byte tooltip has skill +0, mask +4, rank text
at +6 of length 64, description +0x46/256, cost +0x146/32, brand +0x166/64 and three requirement texts
+0x1a6/+0x226/+0x2a6 of 128 bytes each. `table_layouts.c` now names these consumer-verified fields and fixes
the former 256-byte cost-text span.

Build `0x00bb0250`/`0x00bb02fe` filters by mask and stops on zero or the first duplicate key. `0x00bb04ac`
sends arrows and the slot list. The movie reports `RequestPositionInfo(slot,x,y)` as floating JSON numbers.
`0x00bb03bc` stores them; `0x00bb0e2d` draws the icon sheets, greying unmet prerequisite/rank/brand/weapon
conditions. A click `0x00bb22e1` checks points, maximum level, prerequisites of level ≥10, the preceding rank,
the learned brand and the special-item answer. Confirmation ID `0x47` produces the decoded gameplay request
`C1 08 01 16 <u32 skill>`. These routines, the icon calls, tooltip `0x00bb1183` and damage routine ran in Unicorn.

The A0 10 handler `0x012863c5` clears learned/rank state and applies 16-byte entries from +0xc, count at +8.
It adds each entry's level to group spending. A0 14 `0x01285995` replaces the learned entry, updates the hero's
skill, stamp and hotkey managers, sets points to the server-supplied remainder and adds the node's cost to
group spending. The native receiver uses those exact handlers. The local demo server sends an A0 10 list at
login and A0 14 answers to requests. It starts with 100 Master points and synthetic learned values 25,30,…;
these are labelled demo answers, not recovered server formulas. The native confirmation is a second click on
the same node; Esc, close or clicking another node cancels the pending choice.

`world_gfx_tree.c` forwards the original movie callbacks, invokes and tooltip text through SkillInfoPopup,
and draws icons in the per-window GL pass. A toggles MasterSkillTree; CharacterInfoFrame's actual callbacks
are `onClickbtnMasterSkillTree`, `OnClick4thSkillTree`, `OnClick5thSkillTree`. Alignments are 0,0,3, and the
Master window uses 90% scale below 700 points. Renders checked at 1280×800 and 1024×640 show the original
frame, icons, rank text, tooltip and an accepted learn answer. Portable tests use synthetic tables to check
A0 10/A0 14, point updates, damage in the tooltip, the saved bar, weapon greying and those actual buttons.

The 4th/5th movies are registered and accept close/position callbacks, but gameplay remains unavailable. The
4th tree reads Lang.mpr's 4ThTreeData at `0x06fbb8ec`, 4ThTreeSkillTooltip at `0x06fbb930` and
4thTreeSideOption at `0x06fbbaec`. The 5th is an item/card system over ParticleSkill at `0x06fbc8bc`, its
manager and separate inventory/upgrade windows. They are not the Master BMD tables. The available lang5
snapshot exposes top-level maps of 16, 221 and 16 entries for the first, second and ParticleSkill respectively,
but no decoded group/node/card schema or validated nested-table exporter. No supported offline codec exports
these tables from Lang.mpr. Copying top-level map values into invented nodes would not reconstruct the client.
Next work needs scoped nested live reads, complete record parsers and Unicorn comparisons of the 7E/32 answers
and their managers. The empty movies explain the missing data in chat; they do not accept point/card actions.

Validation uses the same pinned inputs as section 1:

- restored text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
- second image SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`;
- local `scratch/skill2/live/lang5.bin`, including `nested:0x6d8` skill maps.

| Validator, `--cases 500 --mutations` | Family counts | Total | Mismatches | Planted mistakes caught |
|---|---|---:|---:|---:|
| `validate_skill_server.py` | list 500, keys 500, stamp 500, usability 2,008, world 500, marker/damage icon 500 | 4,508 | 0 | 6/6, mutants 12..15,19,20 |
| `validate_skill_tree.py` | class 256, build 120, accessors 4,000, click/answer/text/position/damage/tooltip/icons 500 each | 7,876 | 0 | 3/3, mutants 16..18 |

The tooltip family explicitly writes `__isa_available` at `0x0bdcb280` to 0. Unicorn mis-runs the CRT's
SSE4.2 `strstr`, so the client's scalar implementation is selected. The validators now clear client stubs
between families and mutation rounds: the earlier combined server run accidentally retained a packet family's
usability stub. Heap allocation, formatting, font measurement, FormulaData, GFx calls and outside-manager
answers remain modelled boundaries. NOP-filled gaps in A0 22/A0 60 and the opaque tooltip header are not claimed.

Reports remain local in `~/Documents/mu-mac-tools/native/scratch/skill2/`, renders in
`~/Documents/mu-mac-tools/native/renders/skill2/`: `master2-final/`, `master-small/`, `imprint-position/`.

## 11. Later tree input probes (NATIVE-POLISH-001)

`scripts/probe_later_skills.py` runs the original getters on `scratch/skill2/live/lang5.bin`, using the pinned
text/data above. It writes metadata only. The fourth tree is blocked on missing nested allocations:
`4ThTreeData` (`0x06fbb8ec`, map +0x3c) has 16 class entries, but all 16 calls to
`0x010b4406(class,0,0)` stop on absent memory. The first failure is a four-byte read at `0x14d7d4ac`,
instruction `0x0109982a`; other classes reach unmapped inner nodes through `0x0109ab5d`. Neither substituting
empty maps nor the default record would validate real groups/slots. The 221 tooltip lookups and 16
side-option lookups return, but that only verifies their top-level lookup, not every nested field/text.
Next capture needs the class group object and each nested tree allocation used by `0x01098e18`, together
with complete tooltip/side-option records. A fresh scoped live read must wait for the existing owner's client.

The fifth tree has more captured data than the prior top-level survey established. `ParticleSkill`
(`0x06fbc8bc`) map +0x38 holds 16 vectors with 24 records total; map +0x40 holds 21 vectors with 234
records. Both records are 0x24 bytes (`0x00b0f77a` divides the vector length by 0x24). Original getter
`0x010bce97` selects the first record whose words at +8 and +0xc form `word8 * 512 + wordC`;
`0x010bcf3a` selects by word +0x10, and `0x010bd07a` selects map +0x40 by word +0x18. Every captured
record was looked up: 282 checks, zero disagreements with those layouts; a wrong 0x20 stride differs in
229 checks. This probes pointers/selection, not full card semantics or manager behavior.

End-to-end fifth-tree manager execution is blocked by absent runtime state in this table-only snapshot:
the actual singleton getter `0x00abeb00` stops on undefined `0x01d22c04` at `0x00abeb71`. It does not contain
the learned card/slot inventory, its pointed item records, or GFx manager objects needed by the 41-slot
builder/callbacks. Maps +0x48/+0x5c/+0x64/+0x6c/+0x74 still need complete consumer-derived schemas;
the first two vector payloads being present is not a complete ParticleSkill decoder. The packet managers
`0x010a407d`, `0x010a4234`, `0x010a382a`, `0x010a42d6` and inventory/upgrade popups remain unreconstructed.
The first takes an opaque keyed packet transform before item insertion; this work did not enter that path.
Next work needs scoped manager/item snapshots and decoded gameplay inputs, then bounded consumer comparisons
before wiring the existing empty windows. This is an input limitation of this run, not proof those routines
are permanently unreachable. The later trees remain unavailable; no point/card actions were enabled.

Local report: `~/Documents/mu-mac-tools/native/renders/polish/later-skill-inputs.json`. The existing server
and Master suites were rerun: 4,508 + 7,876 cases, zero mismatches, all nine compiled mutants caught.
The base skill suite also passes: 12,763 cases, zero mismatches, 11/11 mutants caught.

## 12. The fourth tree (NATIVE-SKILL-003)

Section 11's blocker was the snapshot, not the client: 4ThTreeData keeps its records in maps nested three deep, and
the earlier langread copied only the top level. `langread graph:ADDR=BYTES,DEPTH[,OBJ]` now follows, breadth first
and bounded by depth and a 96 MiB budget per root, every `std::map` (all nodes, then each node's value), vector and
string it meets, and optionally any other pointer. A root may be a pointer path (`0x01d22c0c/0x1f8/0` is
`[[0x01d22c0c]+0x1f8]`, the SkillTree4th handler). It follows pointers only into memory that is currently
read+write, or into main.exe's uninitialised data. Under this Wine every region of the 32-bit space is backed by
the Wine reserve file, so file backing cannot separate heap from images. Module images (IGC.dll and RGS.dll
included) are mapped read+execute, though, and heap is read+write(+execute), so no module image is followed.
Readers never write, suspend or inject.

**Live capture** (2026-10-22, game lock, about 7.5 minutes, Nighty on MTM-1 in Lorencia; look only, no point,
card or item action). Nighty is an Ignition Knight, level 1600 in the character window (title bar: 400 + master
1200), with all three later buttons. The 4th tree showed "Skill Point: 0", every node at 0, the tabs Normal Skill
Upgrade and Debuff Explosion, and the side panels Skill Enhancement Passive Option and Debuff Enhancement Passive
Option. The 5th button opened Ability Enhancement Core (41 slots) and Ability Cards Book. Snapshots were taken in
the world (`s1_world.bin`), with the 4th tree open (`s2_tree4.bin`) and with the 5th tree open (`s3_tree5.bin`),
each with the table roots 0x06fbb8ec/0x06fbb930/0x06fbbaec/0x06fbc8bc (maps, vectors and strings, depth 8..10), the
fifth manager `0x01d22c04/0` and the six later windows' handlers (depth 3, pointers 0x100 bytes). They stay local
in `~/Documents/mu-mac-tools/native/scratch/skill3/live/`, together with the window-only shots in
`renders/skill3/live/`. A depth-7 pointer graph of the fifth windows reached the 256 MiB file limit through
Scaleform objects and was deleted.

With `s2_tree4.bin`, `probe_later_skills.py` now returns all 16 `0x010b4406` class lookups, the 221 tooltip and
16 side-option lookups, and the fifth manager getter `0x00abeb00`. That getter's object is a vtable and a vector of
six 12-byte entries (ctor `0x010a23ca`), not the card inventory, which lives in the SkillTree5th windows.

### The table (verified)

The loader `0x010b499f` reads rows. A one-column row other than `end` opens a class: the map at +0x3c gets a class
object {+0 class, +4 0, +8 map, +0x10 1}. Every other row goes to the row parser `0x010b4506` (vtable slot 8),
which works like this:

- It rejects rows with fewer than [+0x38] columns (22 in the snapshot) and rows of an unknown class.
- It reads 27 columns through `boost::lexical_cast<int>`; a failed cast takes the catch path and drops the row.
- It hands the 0x6c-byte record to `0x01098d4a`. The group map (+8, keyed by column 1) gets an empty group
  {+0 key, +4 rows, +8 map} when the group is new. The group keeps the first record of an index (column 0), and
  rows = max(index / 10 + 1).

Rows with 22..26 columns make the client read past the vector; `mu_t4_table_row` refuses them. The getter
`0x010b4406(class, group, index)` answers the record or the static default `0x06fba950`. Record fields, from their
consumers:

| Field | Meaning | Consumer |
|---|---|---|
| f[0], f[1] | index (slot), group | maps, `SetSkillSlots` Index |
| f[2] | type: 0 normal, 1, 2 (the group's tab becomes 2), 3 branch | `0x0109ee60`, SlotBG, click |
| f[3] | sibling set: nodes with the same value exclude each other | `0x0109f400`, `0x0109f4bf`, `0x0109f0a2` |
| f[4] | skill | node state, request |
| f[8..12], f[13..17] | child indices, link shown (file: five alternating pairs) | `0x0109fc9b`, `0x00c2b9c8` |
| f[18] | cost (points per level; a level at least this closes the siblings) | click, `0x0109f0a2`, links |
| f[19] | maximum level | click, MaxPoint |
| f[20] | level that opens the children | `0x0109fd1a`, `0x00c2632a` |
| f[21], f[22] | required skill and level (Master level for use types 3/4, else the hero must know it) | `0x0109f27c` |
| f[23..26] | two prerequisite skills of the same group and their levels | `0x0109f339`, `0x0109fddc` |
| +0x6c | byte set to 0 by the parser; a set byte hides the record | `0x0109ee60` |

f[5..7] are read (f[7] looks like the tooltip key) but have no consumer in these routines.
`scripts/live_lang_to_plain.py` now writes `tree4.tsv` (class rows, then each record's 27 columns in file order)
from such a snapshot.

### The window (verified)

The SkillTree4th handler (0xfc bytes, ctor `0x00c22e0b`, GfxMgr +0x1f8, getter `0x0095fb49`) has these fields:

- +0x78 class index, +0x7c points;
- +0x80/+0x84 the pending (group, index);
- +0x88 the current tab, +0x8c the current group;
- +0x90 map<group, group state>, +0xa0 map<skill, node> of the use-type-8 skills, +0xa8 map<tab, tab>;
- +0xb0 the side-option state, +0xec the branch popup flag, +0xf0 the branch choices.

`0x00c24024` builds the window when the 7E 02 list arrives:

- **Reset `0x00c23e5f`.**
- **Group states `0x0109ee60` (0x1c bytes).** Each node (0x48 bytes) gets the state {skill = f[4], level, value,
  next, available, open = 1} and is a leaf until linked. Index % 10 == 0 and type != 3 make a root, and a root
  whose requirement holds is available. A type-2 record makes the group's kind 2.
- **Links `0x0109fc40`.** Each root's children are linked recursively into std::lists (+0x38 parents, +0x40
  children).
- **Tabs.** The tab is the group's kind; each tab keeps {key, page, count, map<position, group>}.
- **Invokes.** RequestSlotUIInfo, then SetTabInfo `0x00c246b2`.

The level setter `0x0109f0a2` runs in this order:

1. It stores level, value and next.
2. At level ≥ f[18] the siblings close.
3. At level ≥ f[20] the learnable children open (`0x0109fd1a`).
4. Every node with prerequisites follows them (`0x0109fddc`).
5. A learned child of a branch closes the branch (`0x0109ffac`).

The other routines:

- **Branch cleanup `0x0109f6e1`.** It follows the first-child chain to a branch node and prunes the links shared
  with it.
- **Use-type-8 nodes `0x00c2a1b7`/`0x00c2a28b`.** Each collects its learned use-type-7 descendants and their
  truncated values in a map at node +0x2c (the enhancement values the bar's 4th icons ask for).
- **Page `0x00c23dc2`.** It sends SetCurrentPage [tab, page] and `0x00c24922` SetSkillSlots/SetSkillSlotLinkInfo:
  - SlotInfo {Index, CurrentPoint, MaxPoint, Type, SlotBG}. SlotBG is 2 for a sibling set, else 1/4/3/1 by type.
  - LinkInfo {From, To, LinkState 4 for a type-2 parent, else 2}. The array is sized nodes × 5; the unused
    entries stay undefined.
  - The refresh `0x00c26e11` → `0x00c25173` re-applies every node through `0x00c26224`/`0x00c2632a` and sends
    SetSkillPoint.
- **Click `0x00c25bda`.**
  - A branch sends VisibleSetBranchSkill and SetBranchSkillInfo with the children's explanations: GlobalText
    0x15db..0x15dd for skills 0x400..0x402, split at `#` by getline, joined with "\n".
  - Otherwise the checks run in this order: maximum level (GT 0xcfe), points < f[18] (GT 0x912), available and
    `0x0109f570` (GT 0xcff).
  - Then come the pending pair and the confirm box id 0x73: GT 0x6eb, "\n", then GT 0x143f with the cost.
- **Confirm answer (`0x00b3771c` case 0x73).** It takes the pending record and calls `0x00b3b703`, which sends
  C1 09 7E 01 <u8 group> <u16 skill> <u16 index>.
- **Answers (opcode 0x7E, dispatcher `0x01287ead`).**
  - 02 `0x0127f539`: points, build, 12-byte entries from +0xb, page 0, `0x00c2a1b7`.
  - 01 `0x0125051f`: result 1 means points, entry, links, `0x00c2a1b7`, the side panel and a branch refresh;
    4 and 7 are messages.
  - 03 `0x0127f679`: points.
  - 05, 06 and 07 drive the side options (still open).
- **Movie callbacks.** OnChangeTab `0x00c25b6c`, prev/next (current page ∓ 1), RequestSlotUIInfo(index, x, y, w,
  h) `0x00c2b3ec` (each group's node keeps the truncated rectangle).

**Window texts, tooltip, icons and side options (`tree4_ui.c`, `tree4_side.c`, verified):**

- **Texts.**
  - SetText `0x00c23175`: one object of GlobalText strings. PointResult is sprintf(GT 0x19f0, 0) and
    ExplainSelectDebuff goes through the HTML line `0x00ab4dc0`.
  - SetLevel `0x00c239c2`: GT 0x144c with level + master level.
- **Tooltip `0x00c29007`.** It fills the classic text list like the Master tooltip:
  - The lines are: name; GT 0x1428 level/maximum; the 4ThTreeSkillTooltip text with the level-0 FormulaData value
    (f[7], f[18]) or the learned value; the next-level block; requirements (GT 0xd01); cost (red when short);
    the first parent's opening level (GT 0x142a); the required skill (0x143b/0x1429); and the prerequisites
    (0x144a/0x1429).
  - The tooltip record is {skill, text, next text, kind −1/0/1, show next, no value}.
  - A branch node shows GT 0x1492/0x1493 (`0x00c2986a`), whose count includes one unwritten line.
- **Icons `0x00c2bb34`.** These are game-drawn 4th_Skill_Icon cells (bitmap 0x7e1c):
  - for the open nodes of the current group, at the movie's slot rectangles, white when available, else grey;
  - for the branch popup's choices (+0xc4);
  - for the side options, whose icon comes from f[19..21] by stage.
- **Side options** (4thTreeSideOption: per class eight 22-int records; categories of (index, group) slots).
  - SetSideOptionIndex `0x00c2436e`.
  - 7E 06 `0x012225fe`: the state `0x00c242b6` (eight 0x18-byte entries) and entries `0x00c2a9cd`. The client
    accepts index 8, one past the vector, which is not generated.
  - Per-category points `0x00c2a4bc`.
  - CreateSideOption `0x00c2aa33`: stage and lock from the category's points and the entry level, tooltipText
    through `0x00ab4dc0`/`0x0096fe90`, skillPoint, lockState, bgState.
  - The click `0x00c2a5ad` (messages, the confirm box 0x79, request C1 07 7E 05 <category> <slot> <level+1>) and
    the 7E 05 answer `0x012226ca`.
  - The side tooltip `0x00c29a29`.
  - The stat skills 0x472/0x477/0x4d9/0x4da open a stat panel (`0x00c26ed3`, with ChangeStat/UpgradeSideStat);
    that panel is not reconstructed.
- **Branch popup.** SelectBranchSkill `0x00c2b5f4` (the pending pair, confirm 0x73) and its positions.

`reconstructed/skill/tree4.c` restates all of this. Invokes are JSON argument lists (a GFx value invoke is
`[value]`, a formatted one `[a, b]`).

### Validation

`scripts/validate_skill_later.py --snapshot s2_tree4.bin --cases 300 --mutations` runs the client's routines
under Unicorn on the snapshot (one process per family with `--families X`, and `--mutations --mutants-only` for
the planted mistakes, run in parallel; `--progress N` prints a line every N cases with the slowest case). Each handler comes from its real constructor, and the client's own allocations are
read back. Results:

| Family | Client routines | Cases | Mismatches |
|---|---|---:|---:|
| table | `0x010b4406` over every snapshot record plus absent keys | 2,910 | 0 |
| row | `0x010b4506` into fresh tables (failed casts through the catch path, short rows, unknown classes, repeats) | 300 | 0 |
| build | `0x00c24024` per class, with random hero answers; invokes and the whole runtime state | 300 | 0 |
| list | 7E 02 `0x0127f539` with random entries (levels, propagation, links, page, refresh, `0x00c2a1b7`) | 300 | 0 |
| page | `0x00c25b6c`/`0x00c23dc2` on random states | 300 | 0 |
| click | `0x00c25bda` and the confirm answer (messages, confirm box, branch popup, request fields) | 300 | 0 |
| answer | 7E 01 `0x0125051f` (results 1/4/7) and 7E 03 `0x0127f679` | 300 | 0 |
| tooltip | `0x00c29007`/`0x00c2986a` (text list, colours, bold, headers, anchor) | 300 | 0 |
| text | SetText `0x00c23175`, SetLevel `0x00c239c2` | 300 | 0 |
| side | 7E 06/7E 05 with CreateSideOption and the side state | 300 | 0 |
| sideclick | `0x00c2a5ad` and the confirm answer 0x79 (request fields) | 300 | 0 |
| sidetip | `0x00c29a29` | 300 | 0 |
| icons | `0x00c2bb34` (RenderBitmap calls) | 300 | 0 |

That is 6,510 cases and 0 mismatches. Ten planted mistakes (`-DMU_SKILL_MUTATION=21..30`) were all
detected. Coverage per family (invokes, boxes, requests) is in the local report
`scratch/skill3/reports/par/*.json`.

Modelled pieces:

- **Calls and GFx.** Import calls stop a case. The heap is a stand-in. GFx is modelled: CreateObject and
  CreateArray on the movie, SetMember, SetElement and SetArraySize, Invoke `0x00aaf3ef` and the formatted
  `0x00aae7e0` with %d %u %s %b %f typed arguments.
- **Streams.** The ostringstream comes from validate_skill's StreamModel. The branch text's
  `operator<<(char)` `0x009443a1`, `getline` `0x00948afe` and the stream's bool `0x0096996a` are modelled.
- **Outside answers.** The hero's skill list `0x00a00287`, the Master level `0x00bb1d9d`, the side-option key
  `0x010b6f79` and the boxes are case answers. The popup and the character window are closed.
- **Speed.** The fast mode drops the per-page snapshot read hooks and the case-heap definedness checks (`--strict`
  keeps them).

Unknown classes (the static default class object) and learn answers for absent nodes (the client dereferences a
null node in `0x00c26c5c`) are not generated.

### Native client

`core/mu_skill_tree4` loads `MU_LANG_DIR/tree4.tsv`. It answers the window's Skill(Kor), hero and Master queries
from the skill book. `world/world_gfx_tree.c` plays SkillTree4th's callbacks:

- GenerateSkillTree {NumRows 10, NumLines 7} (the doubles `0x01a7e460`/`0x01a99f00`);
- the page, re-sent at the window's first draw (a layer choice: the movie's slot clips exist one frame after
  GenerateSkillTree);
- tabs, prev/next and RequestSlotUIInfo;
- a click, then a second click on the same node to confirm, as with the Master tree.

OFFLINE DEMO server: at login a 7E 02 list (every node of the class at level 0, demo points), and a C1 09 7E 01
request answered with 7E 01 (level + 1, points − cost; the value floats are demo stand-ins). To meet the class's
Master requirements, the demo also sends the hero's A0 10 list again with those Master nodes at the required level.
Renders in `~/Documents/mu-mac-tools/native/renders/skill3/` show the original frame, the slot grid and links of
the hero's class, the Debuff tab, and a learned point (Skill Point 30 → 29, slot 0 at 1).

The native window also shows the texts, the tooltips (slot and side), the icons, the side panel (a demo 7E 06 at
login; a side click and a second click spend a demo point) and the branch popup. `live_lang_to_plain.py`
writes `tree4_tips.tsv` and `tree4_side.tsv` next to `tree4.tsv`.

Not yet done:

- **Small pieces.** SetClassName/SetExp and the side stat panel (`0x00c26ed3`, ChangeStat/UpgradeSideStat).
- **Opaque paths.** 7E 07 sub 0 (`0x00c2b911`) is not reconstructed. Subs 1 and 2 jump into the packed region
  (`0x10b3aa90`/`0x10b3ab50`).
- **The fifth tree** was not started; the owner asked to stop after this milestone. The captures for it are
  local: `s3_tree5.bin` has the windows' handlers at depth 3, and the manager `0x01d22c04` is a vector of six
  12-byte entries. Its slots are fed by SetSlot/SetSlotState (`0x00c33d8d`, `0x00c3455d`); the cards are items
  (SkillTree5thInventory +0x29c, item insert through vtable +0x58); and opcode 0x32 subs 0/5/7/0x21 reach
  `0x010a42d6`/`0x010a407d`/`0x010a4234`/`0x010a382a`. Sub 5 passes the item through the opaque keyed transform
  `0x00b1055c`.


## 13. Session migration, SESSION-SKILL-001, 2026-10-28

The existing verified bodies in `reconstructed/skill` are unchanged. Session `skills_apply` binds
A0 20/03/10/14 and the evidenced 7E 01/02/03/05/06 answers. FE/FF remain variants of A0 20.
The skill book and fourth-tree manager now belong to the session rather than the GFx view. The world
steps them in headless builds too. View callbacks emit intents; frame handlers retain all replicated
learned-list, key, Master-rank and fourth-tree updates. Fixture policy moved out of core into
`native/fixture/skills_model.c`; its independent model emits replies through the fixture transport.

The new save-key builder compares only the ten serialized hotkeys at `0x0182ff60..0x0182ffdf`
and plaintext tail at `0x018304cc..0x0183052c` of `0x0182ff32`. The 17-byte settings suffix is
opaque caller input. Keyed AddData is a recorder stub, never executed. Existing Master/fourth-tree
builders and the combat cast builder retain their earlier instruction evidence.

A migration regression exposed a distinct attribute field: A0 14 at `0x01285995..0x012859b4`
sign-extends packet +6 and calls `0x00a00192`, which writes a dword at CharacterAttribute +0x34.
The skills context reads this same field, not progression's +0x30 counter. The new validator executes
the answer prefix and real setter and compares the entire attribute record with compiled authored C.
Together the new serialization/tail/attribute comparisons pass 1,500 cases with zero mismatches and
catch five compiled mistakes: key rotation, endian, opcode, attribute offset and sign extension.
Text/data pins are the existing captures recorded in the handoff. This is original-instruction
evidence for the bounded slices; it does not establish a keyed packet transform or server policy.

The synthetic `skills-state.scn` is discovered by VERIFY-SESSION with 13 inbound frames, all nine
skill routes exercised, zero unbound/undecodable frames, 11 expectations, three plaintext requests
and one encrypted cast journaled unsent. Separate tests verify successful fixture Master learn,
detached answers, rebinding without replacing learned state, lease audit rejection, incomplete
frames and headless ownership. [Final validation and limits](../handoffs/SESSION-SKILL-001.md).
