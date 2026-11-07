# Session equipment records and demo outfits (APP-POLISH-008)

APP-POLISH-008 closes the two gaps APP-REFRESH-008 proof (d) found in the shipped offline demo. Labels:
**verified** = the original instructions ran under Unicorn and agreed with compiled native code; **static** = an
instruction reading that was not executed; **inference** = a conclusion from values. Inputs: the pinned restored
text at `0x00401000` (capture09) and second image section at `0x01a7c000` (run10) (`scripts/pins.py`).
[Handoff](../handoffs/APP-POLISH-008.md).

## 1. What the hero's equipment record holds

HERO-ITEMS-001 ([client-render-items.md part 21](client-render-items.md#part-21-the-heros-part-slots-from-its-equipment-hero-items-001))
verified SetCharacterClass `0x01394870`: it reads the hero's equipped ITEMs at CharacterMachine
`[0x01d1df18] + 0x1b58 + s·0x12c` and writes the CHARACTER part slots. Per ITEM it reads four things:

| ITEM field | Slot field | Read |
|---|---|---|
| `+0x10` code (group·512 + index, −1 empty) | type | code + `0xae6` |
| `+0x14` level word | level | `(word >> 3) & 15` |
| `+0x98` | option (hands and parts) | `0x00cd0995(item, 1)`: `+0x98 == 1` and code in 0..0x2c00 |
| `+0x3b` | ext (hands and parts) | the byte |

Wing and helper take only type and level.

An offline session therefore needs exactly these four values per worn item. `mu_he_item_of_record(code, level,
option, ext)` writes them as the client's reads expect: code, level << 3 (the word's other bits 0), `+0x98` = option,
`+0x3b` = ext, `+0x92` 0. This is not client code; the client gets the ITEM from the server.

**Round trip (verified).** `scripts/validate_hero_items.py` family `record`: 3,000 random equipments of session
records (each slot empty with p = 0.2, else group 0..15, index 0..511, level 0..15, option 0/1, ext 0..255), written
by the compiled helper. Then the original `0x01394870` runs on them under Unicorn. The client's 11 slots equal the C
`mu_he_set_character_class`, and they hold the session's fields: hands and parts (code + 0xae6, level, option, ext);
wing and helper (code + 0xae6, level, prior option/ext). 0 mismatches. Four mutants of the helper (level shift 4,
option + 1, ext & 0x33, code + 1) are caught 750/750 each.

## 2. The session format

`SLOT=FILE[@GROUP:INDEX[:LEVEL[:OPTION[:EXT]]]]` in the character list (handoff section 1). A file-only value keeps
HERO-ITEMS-001's rule: the file's first Item.bmd record at level 0. A file shared by several records gets the first
one: `CookriShortSword.bmd`'s first record is 0:65, the [Bound] variant `0x0b27`. The bundled demo now names 0:68
(`0x0b2a`) explicitly.

## 3. Demo outfits with pre-draw programs (inference from native runs)

Of the 26 RENDER-ITEMS-002R pre-draw types, the demo uses the ones the native world serves in full.

| Type | 0 refused at 140,130 and 128,124 |
|---|---|
| `0x0b2a`, `0x0b4c`, `0x0f1c`, `0x1748`, `0x230b`, `0x2311` | yes |
| `0x1316` | no: 1 refused at 128,124 (not used) |

Wings `0x2384`/`0x2385` stay refused (OBJECT-owned particles, RENDER-EFFECTS-020). The cloaks `0x2382`/`0x2394` draw
no cloak mesh (HERO-ITEMS-001 limit). The shipped Lorencia scene goes from no `item_pre_draw` line to players 98/0
and hero 8/0 at 140,130 (handoff section 3).

**Skill checks (static).** The weapon codes feed the skill usability check's kind test (`skill_canuse.c`, the
record's `+0xb4` rule). The Cookery Short Sword's kind byte is 0x51. All of the demo Dark Knight's skills have rules
0..2, and rule 2 lists 0x51, so Ironclad's skill bar is unchanged. The other characters keep their weapon codes.
