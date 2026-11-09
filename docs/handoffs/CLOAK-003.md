# CLOAK-003

Branch/worktree `codex/cloak-003`, from `origin/main` `a55200e2` (#350). Offline/static only. No live client,
launcher, installed app, network or hosted workflow. No full gate in the lane, per TEST BUDGET.

Scope: CreateClothArmour `0x0135ea29`, the second OBJECT cloth list, its mesh passes, flare requests and second glow.
The separate NPC/monster constructor `0x01362755` remains outside this player/hero lane.

## Result

- `reconstructed/cloth/cloth.c` ports the armour constructor's class and equipment tests, grids, angle-matrix
  variant, wind parameters, UVs, alpha, collision spheres, mesh settings and both glows.
- Render `0x00fd8bc2` now queues type `0x40000000`'s flare sprites, retains its face/back-face condition, and runs
  the second glow `0x00fd9c61` and cumulative level passes `0x00fd97de`. RenderVertexMesh `0x00fd9223` uses grid
  coordinates divided by width/height, not normals. Level 7/9/11/13 passes need quality 1/2/3/4 respectively.
- Existing-list class-8 and upgraded class-3 release/restore paths and armour visibility `0x01362edc` are ported.
  Existing armour lists request a second MoveCloth each frame, except class 12. This is compared against the
  actual MoveCloth/RenderCloth calls, including the creation frame.
- `native/world/world_cloak.c` owns a second list per wearer. Fixture armour/pants/class/wing changes rebuild it;
  viewport generation and travel discard it. It steps both lists between saved frames, loads the original
  startup bitmaps lazily, queues flares into RenderSprites and draws armour with white light after wing cloths.
  The existing hero/player call sites already sit after body parts and before linked items. Item-body code and
  installed apps are untouched.
- Existing demo wearers receive the cloth automatically: Sunwing's default promoted mage armour, Shopkeep and
  Corvin's Dark Lord energy cloths; selecting Spellblade or Crownlord makes the hero's corresponding cloths.
  No demo equipment or gameplay values changed.

## Which armours

Types below are CHARACTER part model indices, not item codes. Base class is the low nibble; skin is the existing
class-tier helper. Set names for item pants come from the installed Item.bmd, while class-part names describe
skins rather than inventing a set label.

| Base class | Condition | Cloth |
|---|---|---|
| 0, Dark Wizard | armour `0x3760` | one 5x5 cloth, bone 17, bitmap `0x7948` |
| 3, Magic Gladiator | skin 3, or skin `0x33` with pants `0x37d3`, or skin `0x43` with pants `0x37e3` | default 10x10 robe on bone 19; upgraded 5x5 cloth on bone 17 |
| 4, Dark Lord | every armour; extra cloth for armour `0x3754`, `0x3774`, `0x3784`, `0x3794` | two energy cloths, bone 20; extra 5x5 cloth, bone 17 |
| 8, Rune Wizard | constructor makes the class default; existing-list path keeps/restores it only with pants `0x37a8..0x37e8` at stride `0x10` | one 5x5 cloth on bone 2 |
| 9, Slayer | every pants type, default bitmap for unlisted types | one 5x10 angle-matrix cloth on bone 3, with item level passes except class-part pants |
| 12, Lemuria Mage | pants `0x1de6` / `0x1de7`, Noble Pixie / Finesse (`9:256` / `9:257`) | two 10x10 halves, bone 2 |
| 15 | armour `0x375f`, `0x376f`, `0x377f`, `0x378f`, `0x379f`, with no wing and class index -1 | one 5x5 cloth on bone 18 |

Slayer's named pants: Red Wing `9:174`, Slayer A/B `175/186`, Demonic A/B/Bound `176/187/188`, Night Wing `177`,
Fidelity `178`, Trace `179`, Bloodangel `180`, Darkangel `181`, Holyangel `182`, Soul `183`, Blue Eye `184`,
Silverheart `185`, Manticore `232`, Brilliant `281`, Apocalypse `295`, Lightning `329`, Temple Guard `366`,
Imperial `421`. Darkangel and Blue Eye set the first glow; Temple Guard and Imperial set the second, level-9 glow.
Slayer class-part pants `0x37a9..0x37e9` bypass the mesh setter.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`, from the repository root. Heavy commands use
`nice -n 10`, `make -j4`, validators `--jobs 2`. Load/memory checks and pauses follow the brief.

| Check | Result | Wall |
|---|---|---:|
| Final `make -j4` | pass | 8.9 s |
| `validate_armour_cloak`, including mutants, code at `6b36fa07` | 4,448 cases, 0 mismatches, 0 stopped; 19/19 compiled mutants caught | 98.2 s |
| `run_test_suites.py --affected origin/main`, portable | 7 suites, 1,362 tests: 1,148 passed, 214 skipped, 0 failures/errors | 352.5 s including selection; 303.0 s tests |
| Private `test_native_armour_cloak` + `test_native_item_cloak`, root, private-env.sh | 20 tests OK, including native hero/player cadence and original comparisons | 15.7 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2`, at `ae8d7582` | 14/14 pass, 56,284 cases | 240.5 s including selection |
| `--list-affected origin/main`, after build | 14 rows, including 3 symbol fallbacks; 11 library consumers pruned | 49.9 s |
| Final repository audit | 2,106 files, 0 rejected | 17.6 s |
| Four documentation-consumer modules after status updates | 36 tests OK, 1 skipped | 8.2 s |

An earlier mutant run stopped because the transpose mutant left a loop index unused under `-Werror` (68.1 s).
The fixture was corrected and the complete run above passed. The product code did not change for that repair.
**8d reduced:** the native selection is 137 modules, above the 40-item cap. The private run above covers the
added armour module and the existing wing module that consumes the changed structs/sink. 6b review found no
other consumers of `mu_cloth`, `mu_cloth_globals`, `mu_cloth_sink` or the new armour API. World callers retain the
same signature. The portable affected run covers the other selected modules.

Only the new armour row's 19 mutants were required. The existing wing row's physics and first-glow mutant
anchors were not changed; it passed all 5,694 instruction comparisons without rerunning its 65 old mutants.

## Scenes, byte identity, renders

- Lorencia, soft 960x600, hero class 4 named Crownlord walking from 128,124 to 131,127; players Shade (Slayer,
  Temple Guard pants +13), Pixie (Noble Pixie pants) and Arcan (class 0x10). 61 frames, saved every 30:
  - before: no cloth report; after: 7 created, 727 steps, 21 draws, 0 gated;
  - frame 30 changes 4,072 pixels. The Dark Lord cape/energy cloths are visible; no stats or equipment changed;
  - final named renders took 1.03 / 1.06 s. A first internal pair used the tool's hardcoded default hero label;
    the name was replaced with Crownlord for the displayed proof, with the same 4,072-pixel change.
- Headless GL, hero Slayer named Shade, `--hero-item pants=Item/PantMale174_slayer.bmd@9:366:13`, angle 225,
  61 frames, saved every 60: 1 cloth, 121 steps, 2 draws; 55 pixels change in frame 60 (the narrow side strip).
  This exercises the level-13 mesh passes and second glow through the hero's equipment record. 1.24 / 0.87 s.
- One default-draw byte-identity sweep, no draw_all or live_time; baseline binaries saved from main `a55200e2`
  before editing, and the final branch binary:
  - October 22: 28/28 PNGs, 28/28 OBJECT/light dumps and 14/14 reports identical; 17.05 / 16.13 s.
  - DATA-ACQ-002: 64/64 PNGs, 64/64 dumps and 32/32 reports identical; 40.57 / 44.51 s.
  - Reports normalize only their output-directory path. No tour has an affected armour wearer in view.
- Installed-file check: all 44 added bitmap registrations resolve to wrapped files, 0 missing, 0.15 s. Actual
  software/GL draws above check the selected textures through the native upload path.

The window-only native crops were visually reviewed and the demo-name comparison displayed inline. Temporary
outputs under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/cloak-003/` are removed at cleanup.

## Limits

- NPC/monster constructor `0x01362755` has no new caller. No live comparison or original-client motion capture.
- Guild-war, duel and buff inputs remain at rest, as in CLOAK-002. Native fixture characters use sub-type 0 and scene 6.
- Native's wind/rand stream and posed Player bones are stand-ins, as in parts 25/27. Original instruction equality
  uses authored case bones and shared case rand state; it does not establish original-client pixel identity.
- Native rebuilds its armour list on fixture equipment changes. The original's existing-list routine updates only
  released entries and has count guards on classes 0/4; dynamic server equipment transitions are outside this lane.
- The EnchantEffect lookup is a supplied service in the instruction check. Native uses its existing Lang table,
  with the existing demo colour fallback when that table is unavailable. Imperial intentionally uses black mesh
  colour, the original's zero vector constructor, while its separate grey glow remains visible.
- The instruction cases keep equipment fixed across frames. Direct restoration after a part transition has static
  and portable coverage; it is not a server-equipment transition comparison.
- GL_QUADS become two triangles. Existing unsupported subtype models, class-specific poses and the original
  shared-process rand history remain the previous lanes' limits.

## Release

Steward validators: validate_armour_cloak, validate_audio_callers, validate_audio_domains, validate_audio_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_cloak, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_worlds_fog. All passed without mutants at `ae8d7582` (C code unchanged from `6b36fa07`);
`validate_armour_cloak` also passed its 19/19 new mutants at `6b36fa07`. No other row needs mutants.
Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Cases | Wall |
|---|---:|---:|
| `validate_armour_cloak` | 4,448 | 45.1 s |
| `validate_audio_callers` | 5,528 | 6.4 s |
| `validate_audio_domains` | 2,544 | 23.6 s |
| `validate_audio_items` | 3,000 | 4.3 s |
| `validate_icarus_c2` | 8,400 | 22.3 s |
| `validate_inventory_fx` | 8,017 | 7.2 s |
| `validate_item_callers` | 6,013 | 1.3 s |
| `validate_item_cloak` | 5,694 | 118.6 s |
| `validate_movement` | 6,614 | 53.0 s |
| `validate_render_effects16` | 424 | 3.2 s |
| `validate_render_effects17` | 618 | 6.8 s |
| `validate_render_effects18` | 540 | 1.4 s |
| `validate_render_effects19` | 400 | 0.9 s |
| `validate_worlds_fog` | 4,044 | 7.7 s |

Cleanup removes this lane's scratch, render and build outputs, worktree and local branch after the ready-prs line.
No new input needs to be kept. The remote branch remains for the steward.
