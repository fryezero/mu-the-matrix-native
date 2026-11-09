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
| Checkpoint repository audit | 2,103 files, 0 rejected | final audit pending |

An earlier mutant run stopped because the transpose mutant left a loop index unused under `-Werror` (68.1 s).
The fixture was corrected and the complete run above passed. The product code did not change for that repair.
Affected checks, final audit and the tested commit will be filled before PR-ready.

## Scenes, byte identity, renders

Native before/after scenes and the single default byte-identity sweep are in progress. Outputs stay local under
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/cloak-003/` and are removed after review.

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
- GL_QUADS become two triangles. Existing unsupported subtype models, class-specific poses and the original
  shared-process rand history remain the previous lanes' limits.

## Release

Steward validators: pending affected selection after the final build. Only the new armour validator needs its new
mutants. Existing wing validator changes are ABI/field-view updates; its old physics/glow mutant targets are unchanged.

Cleanup will remove this lane's scratch, render and build outputs, worktree and local branch after the ready-prs line.
No new input needs to be kept. The remote branch remains for the steward.
