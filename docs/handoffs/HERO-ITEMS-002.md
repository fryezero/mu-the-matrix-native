# HERO-ITEMS-002

Branch/worktree `claude/hero-items-002` from main `c5b9d5ca`; main `c255e4dd` (batch 119) merged as `bf13802a`
(Claude Fable 5.2, effort high). Offline and static only: no live client, launcher, network, protection or
character-power work, no installed-app work, no hosted workflow. No full gate in the lane (test budget).

Scope: the end of SetCharacterClass `0x01394870` for the hero, which HERO-ITEMS-001 left stubbed.
[Finding](../research/client-render-items.md#part-42-the-heros-head-slot-castle-world-weapons-and-scale-writes-hero-items-002).

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

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the repository root, plus `MU_RECOVERY_INTEGRATION=1`
and `MU_EVIDENCE_DIR=$HOME/Documents/MTM/mu-the-matrix-native/evidence`. Heavy steps ran with `nice -n 10`,
`make -j4`, `--jobs 2`. Code commits: `513f989f` (last lane code change), `2c032a80` (main `bb86bbf7` merged; the
merge touched none of the lane's files). Later commits are docs.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` after the merge of `bb86bbf7` | pass | 17.8 s |
| `validate_hero_items` with mutants (`run_validators.py --private --cache --only`, at `513f989f`) | 52,904 cases, 0 mismatches: set_class 3,000, defaults 256, head 832, item_flag 3,000, record 3,000, head_rows 4,720, castle 8,120, scale 8,192, part_loop 4,376, part_type 17,408; 51/51 compiled mutants caught | 258.7 s |
| Head table inside head_rows | 17 listed helms × 256 class bytes: 4,352 rows, 4,352 head draws, 0 row mismatches; 23 control rows × 16: 368 rows, 0 head draws | (in the row above) |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` at `5a8d9baf` / `513f989f` (before the merge) | 35 rows pass, 346,645 cases | 921 s + 89 s |
| The same on the merged tree at `2c032a80` | 37 rows pass, 361,506 cases (the 35 plus `validate_actor_groups` and `validate_render_effects33` from batch 120) | 896 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, at `513f989f`; `native/tests/test_native_app.py` excluded: it builds and signs a bundle) | 7 suites, 183 work items, 1,604 tests, 1,278 passed, 326 skipped, 0 failures | 410.8 s |
| Private modules, 8d reduced, at `513f989f` and again at `2c032a80`: `test_native_hero_items` (Library, HeroScene, HeroClassScene), `test_app_polish8`, `test_native_world_predraw`, `test_native_character`, `test_inventory_fx`, `test_app_polish7`, `test_native_players` | 72 tests OK both times | 231.7 s / 261.6 s |
| `test_native_hero_items` + `tests.test_validators_manifest`, portable, at `2c032a80` | 41 tests OK (10 skipped) | 1.1 s |
| `scripts/audit_repository.py` | 2,372 files, 0 rejected | 28.8 s |

8d reduced: the affected selection is 183 work items (a `native/core` header change), above the 40-item cap, so
only the modules above ran with the private environment. `ClientComparison.test_original_instructions` was not
run through unittest; its validator ran once with mutants through `run_validators.py`.

## Default identity

`nice -n 10 make -C native -j4 world` ran in both trees before each sweep. Default draw (no draw_all, no
live_time), 640×400, 25 frames sampled at 0 and 24, through `scripts/fidelity_tour.py render`: the 14 October-22
views and the 32 DATA-ACQ-002 views.

| Sweep | Base `mu-world` SHA-256 | Lane `mu-world` SHA-256 | Result | Render wall (base / lane) |
|---|---|---|---|---:|
| Lane `513f989f` against main `c255e4dd` | `b6549bcdb452b518ae7026fdb912fb005a8a7788e90eb889daf16f6f403cb7a3` | `5681560999d3cc0b794a1dc7cf02c7b221a5def99fb62ae56d0de76156bdb1ff` | 92/92 PNG, 92/92 OBJECT/light dumps, 46/46 reports identical | 88.7 s / 113.3 s |
| Lane `2c032a80` against main `bb86bbf7` | `2ea6844104645bf8faa2a839c2c74a02d520d8e0ba749f5cee891b56343ce8ac` | `3efd6ee71a6dabc658d0d93efc72b0495ec28dfa6bd4c27522efa5187945cd23` | 92/92, 92/92, 46/46 identical | 118.1 s / 120.8 s |

No default view changes, and none should: every tour view uses the default hero, class byte `0x01` in class parts.
That hero wears no helm (head slot −1), its class scale is the creation default 0.9 with part floats 0, and none of
the 46 views is in a castle world (18..23, 53, 97). The hero changes only when one of the three inputs differs:
a listed helm, a castle world, or a class nibble of 2, 3, 4, 6, 11, 14 or 15.

## Fixture renders

Before | after crops of the hero (base tree | lane, `mu-walk` soft 1280×960, frame 4, 3× nearest; demo names only),
in `~/Documents/MTM/mu-mac-tools/native/renders/hero-items-002/`, 137–189 KB each:

- `head-bronze.png`: Dark Knight, Bronze Helm `0x18e6`: the open helm was hollow, now holds the class head;
- `head-elf.png`: Elf (class 2), Vine Helm `0x18f0`: the hero was headless, now has its head;
- `castle-knight.png`: world 18, worn Sword04 + Wing02 → Sword of Destruction in both hands, no wing;
- `castle-elf.png`: world 18, class 2, worn Bow02 → Great Reign Crossbow in the right hand;
- `scale-alchemist.png`: class nibble 14, body scale 0.9 → 0.8;
- `scale-class11.png`: class nibble 11, body scale 0.9 → 0.99 and the helm part float 0.95.

These are offline native renders of authored fixtures. No row of the helm table differed from the original, so the
crops are representatives; there is no live capture of these states.

## Release

Steward validators: validate_actor_composites, validate_actor_groups, validate_actor_monsters,
validate_actor_plain, validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4,
validate_audio_callers, validate_audio_domains, validate_audio_items, validate_audio_kubera,
validate_audio_monsters, validate_audio_monsters6, validate_audio_objects, validate_audio_objects4,
validate_charsel_items, validate_hero_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers,
validate_items_ui, validate_meshdraw, validate_model_edge, validate_movement, validate_render_effects16,
validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24,
validate_render_effects25, validate_render_effects26, validate_render_effects28, validate_render_effects31,
validate_render_effects33, validate_session_party, validate_worlds_fog. All 37 ran at `2c032a80` without mutants
(the `--affected origin/main` selection after `make`; kept by the symbol fallback: meshdraw, model_edge, movement,
render_effects17, render_effects25). Only `validate_hero_items` needs mutants; they ran once at `513f989f`, and
its inputs did not change in the merge.

| Row | Cases | Seconds | Row | Cases | Seconds |
|---|---:|---:|---|---:|---:|
| `validate_render_effects31` | 66,051 | 339.5 | `validate_audio_monsters6` | 55,392 | 70.3 |
| `validate_hero_items` | 52,904 | 32.4 | `validate_audio_monsters` | 38,315 | 23.0 |
| `validate_actor_plain` | 21,437 | 181.6 | `validate_meshdraw` | 14,619 | 65.4 |
| `validate_app_polish4` | 10,485 | 36.7 | `validate_audio_objects4` | 10,093 | 8.5 |
| `validate_charsel_items` | 8,817 | 9.6 | `validate_items_ui` | 8,517 | 14.2 |
| `validate_actor_groups` | 8,451 | 300.1 | `validate_icarus_c2` | 8,400 | 24.2 |
| `validate_inventory_fx` | 8,017 | 10.9 | `validate_movement` | 6,614 | 72.0 |
| `validate_render_effects33` | 6,410 | 26.2 | `validate_item_callers` | 6,013 | 1.9 |
| `validate_audio_callers` | 5,528 | 7.7 | `validate_worlds_fog` | 4,044 | 8.2 |
| `validate_audio_objects` | 4,000 | 5.5 | `validate_audio_items` | 3,000 | 4.6 |
| `validate_audio_domains` | 2,544 | 26.9 | `validate_actor_recipes` | 1,669 | 118.6 |
| `validate_actor_monsters` | 1,437 | 52.2 | `validate_actor_composites` | 1,427 | 12.9 |
| `validate_app_polish2` | 1,028 | 4.7 | `validate_audio_kubera` | 1,000 | 1.7 |
| `validate_model_edge` | 954 | 123.2 | `validate_app_polish1` | 752 | 25.9 |
| `validate_render_effects28` | 630 | 3.4 | `validate_render_effects17` | 618 | 9.5 |
| `validate_render_effects18` | 540 | 1.7 | `validate_render_effects16` | 424 | 5.4 |
| `validate_render_effects19` | 400 | 1.1 | `validate_render_effects26` | 348 | 14.7 |
| `validate_render_effects24` | 226 | 3.7 | `validate_render_effects25` | 202 | 12.0 |
| `validate_session_party` | 200 | 0.9 | | | |

`native/core/mu_character.h` gained one field (`part_scale`, zero by default) and `mu_character_update` passes it to
the part transform; that is why rows far from the hero are selected (brief 8b). No item table, generator,
`mu_renderchar.c`, actor, combat, consumer, world-object, UI or audio file is edited.

Cleanup removes `mu-mac-tools/native/scratch/hero-items-002/`, the base worktree
`~/Documents/MTM/worktrees/hero-items-002-base`, the build directories, the lane worktree and the local branch. The
six crops above stay. The remote branch stays for the steward. No new private input needs to be kept.
