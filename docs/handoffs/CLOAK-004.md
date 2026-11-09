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
| Merged build, main `127489e0` integrated as `29873d13` | pass | 10.8 s |
| Merge `--list-affected-since f0601116` | 48 rows, 1 symbol fallback, 9 unused library consumers pruned | 58.9 s |
| Merge-affected validators, `--no-mutants --cache --jobs 2` | 48/48 pass, 899,036 cases | 1,392.1 s |
| Portable `--affected-since f0601116`, merged tree | 6 suites, 1,352 tests: 1,132 passed, 220 skipped, 0 failures/errors | 375.8 s including selection; 315.8 s tests |
| Merged private `test_native_npc_cloak` + `test_native_renderchar`, root, private-env.sh | 26 tests OK | 12.0 s |
| Final-main build, main `c26bd0e8` integrated as `612e64b0` | pass | 10.4 s |
| Final-main `--list-affected-since 29873d13` | 53 rows; 32 unchanged rows pruned | 62.3 s |
| Final-main selected validators, no mutants | 53/53 pass | 269.5 s |
| Final-main portable `--affected-since 29873d13` | 9 suites, 1,632 tests: 1,360 passed, 272 skipped, 0 failures/errors | 331.1 s including selection; 280.3 s tests |
| Final-main reduced private modules | 56 tests OK, 0 skipped | 83.2 s |
| Final repository audit | 2,125 files, 0 rejected | 16.8 s |
| Final four documentation-consumer modules | 36 tests OK, 1 skipped | 7.7 s |
| Repository audit before the final main sync | 2,119 files, 0 rejected | 15.0 s |
| Four documentation-consumer modules, portable | 36 tests OK, 1 skipped | 6.8 s |
| Post-build `--list-affected origin/main` | 15 rows, including 2 symbol fallbacks, 11 library consumers pruned | 64.7 s |

The NPC total is 2,614 comparisons against executed instructions plus 5 native world-boundary controls against
Nightmare's statically read world-39 predicate and Eunice's world-121 vtable binding. Families: create 150, existing-list rejection 60, step 1,200,
render 1,200, model/scale 4 and world-boundary controls 5. Only the new NPC row needs mutants.
The original wing/armour physics and their mutant targets were not changed. The initial 16-mutant NPC run at
`8dd4f8ed` passed in 41.7 s; the final 17-mutant run adds the world-121 binding control. After the portable run,
only the new model-selector function changed, plus its validator and test module. The final private NPC run
covers that module's portable and private cases on the final source.

**8d reduced:** native/tests selections are 140 items initially, 138 after the first main merge and 143 after the final sync,
all above the 40-item cap.
The initial final private run uses `test_native_npc_cloak`; after the merge the changed modules are that module
and main's `test_native_renderchar`. Both run with private-env.sh from the repository root. The final-main private run covers
`test_native_npc_cloak`, `test_native_renderchar`, `test_native_particles`, `test_render_effects23`,
`test_followups`, `test_native_names` and `test_render_effects22`. 6b review found `MU_WORLD_PT_BITMAPS`
79 -> 93. The bitmap-end assertions of effects16/20/22/23 and the dynamic bitmap-ID assertions in the
worlds_l/worlds_m hosts pass in the portable native modules. Their unchanged mutant-heavy instruction unit
methods are excluded from the private rerun; the corresponding original-instruction rows passed via
`run_validators.py --no-mutants`.

The earlier private run also covers the unchanged wing and armour modules that exercise the shared renderer.
An initial travel assertion expected cumulative counts, 4 instead of 2; the runtime is replaced on travel.
The corrected test asserts destination world/travel count and the fresh runtime's creation, step and draw counts.
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

Steward validators: validate_app_polish1, validate_app_polish4, validate_armour_cloak, validate_audio_callers, validate_audio_domains, validate_audio_items, validate_fidelity, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_carry, validate_item_chains, validate_item_cloak, validate_item_clusters, validate_item_continuation, validate_item_coverage, validate_item_derived, validate_item_effects, validate_item_expansion, validate_item_gear, validate_item_hiddenmesh, validate_item_next, validate_item_ownerfx, validate_item_predraw, validate_item_product, validate_item_quality, validate_item_ranked, validate_item_scalars, validate_item_types, validate_item_wings_next, validate_meshdraw, validate_model_edge, validate_movement, validate_npc_cloak, validate_particles, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects22, validate_render_effects23, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_worlds_a, validate_renderchar, validate_world_particle_consumers, validate_worlds_121, validate_worlds_after, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_worlds_e, validate_worlds_fog, validate_worlds_g3, validate_worlds_karutan, validate_worlds_l, validate_worlds_m, validate_worlds_raklion, validate_worlds_slots, validate_worlds_slots2, validate_worlds_slots3.

All 76 required rows passed, 1,119,110 cases across each row's last pass.
The primary 15 passed at `f0601116`; after main `127489e0` was merged as `29873d13`, 48 selected rows passed
899,036 cases in 1,392.1 s. Main advanced during those checks: `c26bd0e8` was merged as `612e64b0`, retaining
both appended validator rows and moving CLOAK-004 to Part 33. The new delta selected 53 rows and pruned
32 unchanged rows, including the long item-body and all cloth rows. All 53 passed in 269.5 s.
The table gives each row's last tested source commit, so the steward can select only subsequent input changes.

`validate_npc_cloak` passed 17/17 compiled mutants at `f0601116`; cloth and actor caller sources are unchanged
by both main merges. No other row needs a mutant rerun. Row commands use `--no-mutants`; scripts with
built-in controls and no mutant switch retain those controls. Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

The earlier UV syntax repair (`fe3d7248`) produced byte-identical whole cloth libraries at validator O2 flags,
SHA-256 `92a34a3f2b34fa39a9595efda9ead26e4335a81a9760a6ec06f8a1f02dc30bb8`. All 101 old/new anchors occur
once. That syntax repair precedes the final world-121 guard and final instruction comparisons.

| Validator | Cases | Wall | Tested commit |
|---|---:|---:|---|
| `validate_app_polish1` | 752 | 18.2 s | `612e64b0` |
| `validate_app_polish4` | 10,485 | 30.0 s | `612e64b0` |
| `validate_armour_cloak` | 4,448 | 41.5 s | `29873d13` |
| `validate_audio_callers` | 5,528 | 4.7 s | `612e64b0` |
| `validate_audio_domains` | 2,544 | 21.0 s | `612e64b0` |
| `validate_audio_items` | 3,000 | 2.5 s | `612e64b0` |
| `validate_fidelity` | 991 | 80.9 s | `29873d13` |
| `validate_icarus_c2` | 8,400 | 13.8 s | `612e64b0` |
| `validate_inventory_fx` | 8,017 | 6.4 s | `612e64b0` |
| `validate_item_callers` | 6,013 | 1.2 s | `612e64b0` |
| `validate_item_carry` | 114,388 | 399.0 s | `29873d13` |
| `validate_item_chains` | 35,406 | 103.5 s | `29873d13` |
| `validate_item_cloak` | 5,694 | 110.3 s | `29873d13` |
| `validate_item_clusters` | 74,292 | 48.4 s | `29873d13` |
| `validate_item_continuation` | 25,772 | 41.4 s | `29873d13` |
| `validate_item_coverage` | 31,724 | 40.0 s | `29873d13` |
| `validate_item_derived` | 36,252 | 167.4 s | `29873d13` |
| `validate_item_effects` | 1,500 | 1.3 s | `612e64b0` |
| `validate_item_expansion` | 52,172 | 46.0 s | `29873d13` |
| `validate_item_gear` | 25,256 | 67.2 s | `29873d13` |
| `validate_item_hiddenmesh` | 116,281 | 361.8 s | `29873d13` |
| `validate_item_next` | 14,992 | 167.3 s | `29873d13` |
| `validate_item_ownerfx` | 14,964 | 107.5 s | `29873d13` |
| `validate_item_predraw` | 36,196 | 222.1 s | `29873d13` |
| `validate_item_product` | 2,874 | 45.8 s | `29873d13` |
| `validate_item_quality` | 28,080 | 176.7 s | `29873d13` |
| `validate_item_ranked` | 17,736 | 40.7 s | `29873d13` |
| `validate_item_scalars` | 26,274 | 44.0 s | `29873d13` |
| `validate_item_types` | 135,176 | 39.5 s | `29873d13` |
| `validate_item_wings_next` | 33,622 | 45.9 s | `29873d13` |
| `validate_meshdraw` | 14,619 | 52.2 s | `612e64b0` |
| `validate_model_edge` | 954 | 103.9 s | `612e64b0` |
| `validate_movement` | 6,614 | 46.8 s | `612e64b0` |
| `validate_npc_cloak` | 2,619 | 27.7 s | `29873d13` |
| `validate_particles` | 407 | 1.2 s | `612e64b0` |
| `validate_render_effects` | 660 | 0.8 s | `612e64b0` |
| `validate_render_effects10` | 154 | 0.4 s | `612e64b0` |
| `validate_render_effects11` | 176 | 0.2 s | `612e64b0` |
| `validate_render_effects12` | 64 | 0.3 s | `612e64b0` |
| `validate_render_effects13` | 180 | 0.4 s | `612e64b0` |
| `validate_render_effects14` | 660 | 0.9 s | `612e64b0` |
| `validate_render_effects15` | 509 | 0.7 s | `612e64b0` |
| `validate_render_effects16` | 424 | 2.6 s | `612e64b0` |
| `validate_render_effects17` | 618 | 6.5 s | `612e64b0` |
| `validate_render_effects18` | 540 | 1.0 s | `612e64b0` |
| `validate_render_effects19` | 400 | 0.9 s | `612e64b0` |
| `validate_render_effects20` | 148 | 0.2 s | `612e64b0` |
| `validate_render_effects21` | 267 | 0.3 s | `612e64b0` |
| `validate_render_effects22` | 202 | 4.6 s | `612e64b0` |
| `validate_render_effects23` | 1,174 | 5.0 s | `612e64b0` |
| `validate_render_effects3` | 720 | 0.7 s | `612e64b0` |
| `validate_render_effects4` | 1,920 | 5.0 s | `612e64b0` |
| `validate_render_effects5` | 1,190 | 3.3 s | `612e64b0` |
| `validate_render_effects6` | 1,000 | 1.0 s | `612e64b0` |
| `validate_render_effects7` | 596 | 1.2 s | `612e64b0` |
| `validate_render_effects9` | 304 | 0.7 s | `612e64b0` |
| `validate_render_worlds_a` | 9,000 | 9.0 s | `612e64b0` |
| `validate_renderchar` | 1,706 | 44.2 s | `29873d13` |
| `validate_world_particle_consumers` | 900 | 0.6 s | `612e64b0` |
| `validate_worlds_121` | 4,000 | 3.4 s | `612e64b0` |
| `validate_worlds_after` | 13,424 | 9.4 s | `612e64b0` |
| `validate_worlds_after2` | 32,216 | 20.1 s | `612e64b0` |
| `validate_worlds_after3` | 10,212 | 6.1 s | `612e64b0` |
| `validate_worlds_after4` | 9,181 | 10.2 s | `612e64b0` |
| `validate_worlds_after5` | 6,000 | 7.8 s | `612e64b0` |
| `validate_worlds_after6` | 7,300 | 52.2 s | `612e64b0` |
| `validate_worlds_e` | 4,840 | 13.1 s | `612e64b0` |
| `validate_worlds_fog` | 4,044 | 4.4 s | `612e64b0` |
| `validate_worlds_g3` | 4,000 | 3.4 s | `612e64b0` |
| `validate_worlds_karutan` | 3,000 | 2.3 s | `612e64b0` |
| `validate_worlds_l` | 1,260 | 0.9 s | `612e64b0` |
| `validate_worlds_m` | 1,080 | 0.8 s | `612e64b0` |
| `validate_worlds_raklion` | 3,000 | 2.6 s | `612e64b0` |
| `validate_worlds_slots` | 18,999 | 11.7 s | `612e64b0` |
| `validate_worlds_slots2` | 33,000 | 20.1 s | `612e64b0` |
| `validate_worlds_slots3` | 36,000 | 20.5 s | `612e64b0` |

Cleanup removes the lane's scratch, renders, build outputs, worktree and local branch after its ready-prs line.
No new input needs to be kept. The remote branch remains for the steward.
