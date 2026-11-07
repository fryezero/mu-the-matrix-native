# The hero's part slots from its equipment (HERO-ITEMS-001)

Platform-neutral C for the routine that writes the hero's CHARACTER part slots (the type, level, option and ext
bytes RenderCharacter and RenderLinkItem read) from the hero's own equipped items, the counterpart of the
players' ChangeCharacterExt in [../players](../players/README.md). Finding:
[docs/research/client-render-items.md part 21](../../docs/research/client-render-items.md#part-21-the-heros-part-slots-from-its-equipment-hero-items-001).

| Routine | Address | Function | Status |
|---|---|---|---|
| SetCharacterClass: CharacterMachine `[0x01d1df18] + 0x1b58 + s * 0x12c` -> slots `c + 0x1c4 + k * 0x3fc` | `0x01394870` | `mu_he_set_character_class` | verified (slot writes; its calls 0x009dadf1, 0x0137ad93, 0x00a00fb7 not reproduced) |
| the head slot from the helm type | `0x01394f6f` (to `0x013950ba`) | `mu_he_head_type` | verified |
| ITEM flag (mode 0: +0x3b & 0x33, 1: +0x98 == 1, 2: +0x92 == 1) | `0x00cd0995` | `mu_he_item_flag` | verified |
| APP-POLISH-008: an offline session's equipment record (code, level, option, ext) as ITEM fields | (not client code; the inverse of the reads above) | `mu_he_item_of_record` | verified round trip: the client's `0x01394870` reads the fields back into the slots |

`make` builds `libheroequipment` (with `../players/remote_players.c` for the slot record and the class skin
`0x0139d6a2`). Tests: `native/tests/test_native_hero_items.py` (portable worked examples; private Unicorn row
`validate_hero_items`, `scripts/validate_hero_items.py`).
