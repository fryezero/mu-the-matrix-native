# HERO-ITEMS-002

Branch/worktree `claude/hero-items-002` from main `c5b9d5ca` (Claude Fable 5.2, effort high). Offline/static only:
no live client, launcher, network, protection or character-power work; no installed-app work.

## WIP (checkpoint 1)

Done:
- Static trace of SetCharacterClass `0x01394870`'s end: the castle-world weapon override `0x009dadf1` (with its
  clear `0x009dad3f`), SetCharacterScale `0x01394f6f` (head slot, six part floats `+0x288`, OBJECT scale `+0x32f4`)
  and RenderCharacter's body-part loop `0x0136a374..0x0136a8ef` (slots 5..0, `-1` skipped, slot 0 drawn like the
  others; class nibbles 4, 5 and 6 replace some part models).
- `reconstructed/hero-equipment`: `mu_he_castle_world`, `mu_he_castle_weapons`, `mu_he_castle_override`,
  `mu_he_class_scale`, `mu_he_character_scale`, `mu_he_set_character_class_world`, `mu_he_part_draw_type`,
  `mu_he_part_draws`.
- `scripts/validate_hero_items.py`: families `head_rows` (17 helms x 256 class bytes + controls), `castle`, `scale`,
  `part_loop`, `part_type`; 33 new mutants. Development run: 0 mismatches, 50/51 mutants (the missed one got
  directed rows afterwards; rerun pending).
- Native: `native/world/world_rt.c` loads the class head into item 0, swaps the hero's weapons and wing for the
  castle weapon in the worlds 18..23, 53, 97, and applies the class body scale and the part floats
  (`mu_character_params.part_scale`, new). Report line `hero_class`.

Left: final validator run with mutants, registry row counts (`scripts/validators.toml`), scene tests, fixture
renders, the default identity sweep, research part, status lines, PR.

Next step: run `scripts/validate_hero_items.py --mutations`, then add the private scene tests to
`native/tests/test_native_hero_items.py`.
