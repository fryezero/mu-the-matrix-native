# CLOAK-004

Branch/worktree `codex/cloak-004`, from `origin/main` `825c37b7`. Offline/static only. No live client,
launcher, installed app, network work or hosted workflow. No full gate in the lane, per TEST BUDGET.

Scope: NPC/monster cloth constructor `0x01362755`, its model selections and native actor callers.
The existing wing/armour cloth code supplies the physics, texture upload and software/GL renderer.

## Result

- `mu_cloth_npc_create` ports all six class-index cases, including the two Eunice halves, UV setters and
  opposite-side collision spheres. `mu_cloth_npc_cloths` rejects every other class.
- RenderCloth's sole direct call is `0x01363102`, after the player armour constructor declines. An existing
  NPC list makes the constructor return false. These actors get one MoveCloth per frame, with the creation
  frame's extra step, rather than the player armour's repeated second step.
- `world_cloak_actor_draw` uses each actor's own posed bones, body scale/origin, angle, action pair and alpha.
  Player-model actors draw cloth between body parts and linked items. Other actors draw it after their body.
  Actor slots survive between saved frames and are freed before an actor-cache replacement and at travel/unload.
  The original cloth gate and second-list white-light draw are reused.
- Death King class 55 can now use the existing player-model actor loader. Nightmare class 361 takes its
  world-39 processor's model/scale; Eunice Monster class 937 takes its world-121 create method's model/scale.
  Generic table values for those last two had been the world-0 fallback model `0x7a5`.
- Four cloth bitmap registrations use the original startup file names, filters and wraps. Item/particle sources
  and the shipped placement files are unchanged. Ordinary Lorencia, Devias and Noria NPC class IDs select no cloth.

## Which NPCs and monsters

Class index is CHARACTER `+0x146`, not the OBJECT model index. Names are the local exported `npcnames.tsv` lookup.
The names shown in rendered fixtures are authored demo labels.

| Class | Name | Model / type | Cloth |
|---|---|---|---|
| `55` / `0x37` | Death King | Player `0xa91`, scale 1.4 from the existing generic table | one bone-19 10x10 robe, origin 0,10,0; 55x140; bitmap `0x790d`; type `0x1001` |
| `361` / `0x169` | Nightmare | world 39: `0x81e`, monster type 121, `Monster122.bmd`, scale 1.6; other worlds keep the generic fallback | one bone-2 6x6 cloth, origin 0,0,0; 180x100; bitmap `0x7ff2`; type `0x1008`; no spheres |
| `937` / `0x3a9` | Eunice (Monster) | world 121: `0x95a`, monster type 437, `Monster438.bmd`, scale 0.9 | two bone-4 10x10 halves, origins +/-10,8,2; 200x120; bitmaps `0x84e6/0x84e7`; type `0x1005` |
| `939..941` / `0x3ab..0x3ad` | Eunice (Town / Entrance / Quest) | NPC `0xa8b`, `N_eunice.bmd`, scale 0.9 from the existing generic table | same two halves |

Death King spheres: (-10,-10,-10,r35,b17), (10,-10,-10,r35,b17), (0,-10,-40,r50,b19).
Eunice U scale is 0.5, V scale 1, U offset 0/1. The first half's spheres have x=-10, the second x=10,
with y=-5, z=-10/-30, radius 30/35, bone 3. Their origins use the opposite sign.

Bitmap startup calls: `0x0182c044`, `0x0183d611`, `0x01827fc5`, `0x01827fe5`:
`Player/Robe03.tga`, `Monster/nightmare_cloth.tga`, `NPC/eunice_cape_L.tga`, `NPC/eunice_cape_R.tga`.
All use clamp `0x2900`; the first two use nearest `0x2600`, Eunice uses linear `0x2601`.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`, from the repository root. Heavy commands use
`nice -n 10`, `make -j4`, validators `--jobs 2`. Resource checks precede heavy steps.

| Check | Result | Wall |
|---|---|---:|
| Final `make -j4`, after the world-121 model guard | pass | 9.8 s |
| Final `validate_npc_cloak`, including mutants, at `f0601116` | 2,619 cases, 0 mismatches, 0 stopped; 17/17 compiled mutants caught | 46.3 s |
| Initial private cloth modules, root with private-env.sh | 25 tests OK | 22.4 s |
| Portable affected suites at `fe3d7248` | 7 suites, 1,380 tests: 1,155 passed, 225 skipped, 0 failures/errors | 334.2 s including selection; 285.2 s tests |
| Final affected validators, no mutants, at `f0601116` | 15/15 pass, 58,903 cases | 217.2 s including selection |
| Final private `test_native_npc_cloak`, root, private-env.sh | 6 tests OK, including actual-model draw counts and travel reset | 9.5 s |
| `make -C native -j4 world` | pass | 4.4 s |
| Post-build `--list-affected origin/main` | 15 rows, including 2 symbol fallbacks, 11 library consumers pruned | 64.7 s |

The NPC total is 2,614 comparisons against executed instructions plus 5 native world-boundary controls against
Nightmare's statically read world-39 predicate and Eunice's world-121 vtable binding. Families: create 150, existing-list rejection 60, step 1,200,
render 1,200, model/scale 4 and world-boundary controls 5. Only the new NPC row needs mutants.
The original wing/armour physics and their mutant targets were not changed. The initial 16-mutant NPC run at
`8dd4f8ed` passed in 41.7 s; the final 17-mutant run adds the world-121 binding control. After the portable run,
only the new model-selector function changed, plus its validator and test module. The final private NPC run
covers that module's portable and private cases on the final source.

**8d reduced:** the affected portable selection lists 140 native/tests work items, above the 40-item cap.
The final private run uses the one added/changed module, `test_native_npc_cloak`, with private-env.sh from the root.
The earlier private run also covers the unchanged wing and armour modules that exercise the shared renderer.
6b review found no changed existing struct layout, table size or constant; the new APIs are consumed only by the
new module and the actor/cloth callers. The existing `test_world_parts` frame consumer is in the portable selection.

## Scenes, byte identity, renders

The baseline binaries were built once from main `825c37b7` before source edits.

- Native GL viewport renders, hero DemoKnight at 128,124, EuniceDemo class 939 at 129,125, direction 5,
  960x600, 61 frames, saved frames 0 and 60:
  - Lorencia: before 0.82 s, after 0.97 s; frame 60 changes 2,178 pixels.
  - Devias: 0.84 / 0.88 s, 1,924 pixels.
  - Noria: 0.88 / 0.87 s, 2,153 pixels.
  - Main prints no cloth report; each branch run creates 2 halves, steps them 122 times and draws 4 cloths
    across the two saved frames, 0 gated. All three pairs were visually reviewed and displayed inline as
    window-only native crops. Total six-run proof time 5.3 s.
- The private native scene places all six eligible classes plus an ordinary smith. It creates 10 cloths,
  draws 160 with every frame saved or 20 with only frames 0/15 saved; final images and step counts agree.
  Separate world-39 Nightmare and world-121 Eunice Monster scenes assert the actual model, scale and 2/4 draws.
  Ordinary smith scenes in worlds 0/2/3 create no cloth. Travel 0 -> 2 recreates Eunice's two halves and
  the fresh destination runtime reports created 2, steps 10, drawn 10 over its five frames.
- One default-draw byte-identity sweep, no draw_all/live_time, baseline versus `f0601116`:
  - October 22: 28/28 PNGs, 28/28 OBJECT/light dumps, 14/14 normalized reports identical; 18.01 / 18.25 s.
  - DATA-ACQ-002: 64/64, 64/64, 32/32 identical; 42.74 / 43.40 s.
  - Reports normalize only the output-directory prefix. Those captures have no eligible actor in view.

Temporary outputs live under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/cloak-004/` and are removed
at cleanup. No original-client screenshot or pixel equivalence is claimed.

## Limits

- Static and Unicorn evidence only. No live original-client motion or pixel comparison.
- The original gate's guild/duel/buff inputs remain at rest, as in CLOAK-002/003. Fixture actors use sub-type 0.
- Native uses its own wind/rand history and reconstructed posed bones. Instruction comparisons use identical
  authored bones and rand state on both sides. This does not establish original-client pixel equivalence.
- Class 937's dedicated create method is compared through model selection and scale. Its world-121 binding is
  static: the pinned data's vtable `0x01aa51fc + 0x48 = 0x01aa5244` points to `0x00d5a9d3`, and the existing
  factory census maps that vtable only to world 121. Virtual-manager lifecycle and trailing effects are not
  executed. Both model overrides retain their world conditions; other worlds use the generic table.
- Death King's pre-existing generic equipment table has only a weapon. This lane enables that actor loader and
  its robe; it does not reconstruct missing body-part or special monster render recipes.
- The lane adds no actors to the shipped placements. Eligible IDs supplied by existing fixture/session records get
  cloth automatically. The ordinary town smith, merchant, storage, guild and quest NPCs do not acquire capes.
- GL_QUADS become two triangles, as in the earlier cloak lanes. No protection code, server state, stats or packets
  are inspected or changed.

## Release

Steward validators: validate_armour_cloak, validate_audio_callers, validate_audio_domains, validate_audio_items,
validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_cloak, validate_movement,
validate_npc_cloak, validate_render_effects16, validate_render_effects17, validate_render_effects18,
validate_render_effects19, validate_worlds_fog. All 15 passed 58,903 cases without mutants at `f0601116`.
`validate_npc_cloak` also passed its 17/17 mutants on that source. No other row needs mutants.
Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

The earlier `fe3d7248` checkpoint changes only the new NPC UV assignment from an implicit integer condition to explicit
`i != 0`, avoiding the old armour mutant's text anchor. Before the later world-121 guard addition, compiling the whole cloth library at the validator's exact
O2 flags before and after produces byte-identical dylibs, SHA-256
`92a34a3f2b34fa39a9595efda9ead26e4335a81a9760a6ec06f8a1f02dc30bb8`. All 101 wing/armour/NPC mutant anchors
occur once. No existing validator or mutant target was edited.

| Validator | Cases | Wall |
|---|---:|---:|
| `validate_armour_cloak` | 4,448 | 36.5 s |
| `validate_audio_callers` | 5,528 | 5.1 s |
| `validate_audio_domains` | 2,544 | 20.4 s |
| `validate_audio_items` | 3,000 | 3.9 s |
| `validate_icarus_c2` | 8,400 | 13.7 s |
| `validate_inventory_fx` | 8,017 | 7.3 s |
| `validate_item_callers` | 6,013 | 1.1 s |
| `validate_item_cloak` | 5,694 | 121.5 s |
| `validate_movement` | 6,614 | 58.1 s |
| `validate_npc_cloak` | 2,619 | 24.9 s |
| `validate_render_effects16` | 424 | 2.6 s |
| `validate_render_effects17` | 618 | 7.4 s |
| `validate_render_effects18` | 540 | 0.9 s |
| `validate_render_effects19` | 400 | 0.8 s |
| `validate_worlds_fog` | 4,044 | 4.7 s |


Main `127489e0` was merged as `29873d13`, preserving both lanes' documentation and moving this finding to
Part 32. It brings RENDER-ITEMS-002V's six item bodies and random-colour arithmetic. Cloth and actor caller
sources are unchanged (`git diff f0601116..29873d13` over those paths is empty). The merged build passes in
10.8 s. `--list-affected-since f0601116`, after that build, selects 48 rows, including the movement fallback,
and prunes 9 unused library consumers, in 58.9 s. Those rows are checked separately without mutants.
The default sweep and viewport pairs above remain explicitly the `f0601116` proof, not a new original-client
comparison. The merge adds no cloth behavior or new fixture/model input to that proof.

Cleanup removes the lane's scratch, renders, build outputs, worktree and local branch after its ready-prs line.
No new input needs to be kept. The remote branch remains for the steward.
