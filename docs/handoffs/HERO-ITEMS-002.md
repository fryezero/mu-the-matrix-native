# HERO-ITEMS-002

Branch/worktree `claude/hero-items-002` from main `c5b9d5ca`; main `c255e4dd` (batch 119) merged as `bf13802a`
(Claude Fable 5.2, effort high). Offline and static only: no live client, launcher, network, protection or
character-power work, no installed-app work, no hosted workflow. No full gate in the lane (test budget).

Scope: the end of SetCharacterClass `0x01394870` for the hero, which HERO-ITEMS-001 left stubbed.
[Finding](../research/client-render-items.md#part-43-the-heros-head-slot-castle-world-weapons-and-scale-writes-hero-items-002).

## What draws now

| Item | Rows / worlds / branches | Native |
|---|---|---|
| Head slot | 17 helm types × 256 class bytes = 4,352 instruction rows; 14 of the 17 have an Item.bmd record in the installed data and a scene | The class head (`HelmClass` file of the class skin) loads into item 0 and draws as the last body part |
| Castle weapon override `0x009dadf1` | Worlds 18, 19, 20, 21, 22, 23, 53, 97 (`0x009dacb8`) | Both hands and the wing follow the slots: class nibbles 1, 3, 4, 6, 7, 9, 10, 13, 15 → Sword of Destruction `0x0af6` in both hands; 2 → Great Reign Crossbow `0x12f9` right; 0, 5, 8, 11, 12, 14 → Legendary Staff `0x14eb` right; wing none; level 0, option 0 |
| Scale writes of `0x01394f6f` | 8 writes classified; 5 implemented (castle part floats, castle scale 0.88/0.9, part floats with 0.95 for class nibble 11's helm, class scale table, head) | Body and wing scale, `mu_character_params.part_scale` (new, the part transform's vertex scale) |

Visible: a hero in a listed helm is no longer headless; in a Chaos Castle world the hero carries the class weapon
and no wing; heroes of class nibbles 2, 3, 4, 6, 11, 14, 15 take their class scale (0.88, 0.95, 0.92, 1.03, 0.99,
0.8, 1.1; among the demo characters Windleaf, Spellblade and Crownlord). The summary prints a `hero_class` row only
when one of these applies.

## Refusals and limits

- **Buff scale** (write 7): 1.1 under buff `0x1a8` or `0x1a9` reads the character's buff list, which is server
  state. Refused; both answers are 0 offline.
- **Scene 5 scale 1.7** (write 5) is the character select's branch and already lives there; never taken in the world.
- **Castle side effects not applied:** the three interface calls, `c + 0x16` = 0 (no native consumer) and the
  helper-slot clear (the hero's demo helper belongs to the helpers part).
- **Substituted part models** of class nibbles 4 (helm slot, `0x38f6 + d`), 5 (`0x36ce + index + 2 · group`) and 6
  (`0x36d4 + j + 4 · g`): the rule is verified against the loop, but the model files are in no recovered loader
  table, so the hero draws the item's own model.
- **Three helms without a record** in the installed Item.bmd (7:87..89, `0x193d..0x193f`): instruction rows only.
- **A class head the loader does not open** (the second tier of class nibbles 3, 4, 6, 7 has no part files): the
  head stays unloaded and `refused` counts it.
- **Other players** get the same two calls from ChangeCharacterExt; `mu_world_players.c` is not changed (still
  slots 1..8 at scale 0.9). Follow-up: call `mu_he_castle_override` / `mu_he_character_scale` there.
- Body-part loop domain: class nibble 6 with action `0xdd` (a second pass or `0x00d2d3f9`) is outside the comparison.
- Omitted as briefed: the stat machine `0x00a00fb7` and the hero-only `0x0137ad93`. Nothing reads character power.
