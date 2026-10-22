# Skills in the interface (NATIVE-SKILL-001)

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
- **Usability `0x010918c7`** (static). It runs the stat check and then the use-type 2 buff rule (`0x016a500c`). It
  then checks the transformation rule (+0xb0 against `0x01092571`). Next comes the required weapon kind (+0xb4 1..0x12,
  equipped items' kind byte +0x251 through `0x00987982`), with skill-specific buff, world and item cases after that.
  Only the stat check and the class cases are reconstructed and verified. The weapon, buff, world and item branches
  are not, and the native bar counts them as met.

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
authored position (8, 0); the client's window placement on open is not reconstructed.

## 7. Gaps

- The generic Lang table loader, its tokeniser and the package password stay out of scope. The inner maps (+0x64
  ranks, +0x6c class requirements) and the pair vector are not in the snapshot, so class learnability is demo data.
- The usability check's weapon, buff, world and item branches; the use controller's other checks; the server's
  skill list, cast answers, mana/AG and the imprint (stamp) system: the stamp manager's entries, elemental imprints
  and the special-skill tab. The demo hero has no stamps.
- The character machine's skill damage (`0x00a01692`) is not reconstructed (the demo shows the record's damage),
  and neither are the master-skill tree and the 4th/5th trees (MasterSkillTree, SkillTree4th/5th windows).
- The window's open position; the stamp marker icon (`0x0109750c`, bitmap `0x7e26`); the opaque builder header.
- The client's measuring font (GlobalText[0], at the 640-unit height) is CoreText's version of that face.
