# RENDER-ACTORS-001

Branch `codex/render-actors-001`, based on main `5ef84dff`. Offline/static only. No live original client,
network/login/server-state/packet work, protection analysis, original-install tree, memory writes or installed app changes.

## Result and census

Death King 55 now has its original whole Skeleton01 body on Player bones, at scale 1.4, alongside its existing
weapon and CLOAK-004 cloth. Classes 14, 15, 16, 56 and 236 use the same recovered whole-body path. These six
have no five-piece armour recipe in the original branch. Their special render call is one textured body,
level/option/ext 0, flags 2. Eleven equipment rows use their extracted five-part body models and levels;
nine gain native admission, with 229 and 257 retained as existing-loader controls.

Of the 32 player-model rows in the class table, 15 actors change, 2 are unchanged controls, and 15 remain
unadmitted. This is the census of the bounded class table, not a claim that every virtual map processor,
world variant or transformed-player appearance is reconstructed. Shipped placements are unchanged.

Latest main `54a53e1a` was merged as `6c2ca37a`, preserving both lanes' status entries. The merged build passes
in 12.0 s. The post-build delta selector retains 56 rows in 63.9 s; their no-mutant run is in progress at this
checkpoint. The actor implementation and its compiled mutant targets are unchanged by that merge.

| Class | Result | Body recipe | Scale |
|---|---|---|---:|
| 14 | fixed | whole `0x422`, Skill/Skeleton01 | 0.95 |
| 15 | fixed | whole `0x423`, Skill/Skeleton02 | 1.1 |
| 16 | fixed | whole `0x424`, Skill/Skeleton03 | 1.2 |
| 34 | fixed | five parts `0x18e9..0x20e9`, +9 | 0.9 |
| 55 | fixed | whole `0x422`, Skill/Skeleton01 | 1.4 |
| 56 | fixed | whole `0x422`, Skill/Skeleton01 | 0.8 |
| 229 | unchanged control | five parts `0x18ef..0x20ef`, +7 | 0.9 |
| 236 | fixed | whole `0x423`, Skill/Skeleton02 | 1 |
| 247 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 249 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 257 | unchanged control | five parts `0x18fe..0x20fe`, +13 | 1 |
| 258 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 297 | fixed | five parts `0x18e7..0x20e7`, +9 | 0.9 |
| 371 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 372 | left | subtype `0x425`, kind/world/action hook unresolved | 0.95 |
| 373 | left | subtype `0x429`, kind/world/action hook unresolved | 0.95 |
| 374 | left | subtype `0x3ed`, kind/world/action hook unresolved | 0.85 |
| 375 | fixed | five parts `0x1904..0x2104`, +9 | 0.9 |
| 378 | left | subtype `0x3e9`, kind/world/action hook unresolved | 1 |
| 414 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 464 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 503 | left | subtype `0x541`, kind/world/action hook unresolved | 0.9 |
| 548 | left | subtype `0x552`, kind/world/action hook unresolved | 0.9 |
| 616 | left | subtype `0x5bb`, kind/world/action hook unresolved | 0.9 |
| 617 | left | subtype `0x5ba`, kind/world/action hook unresolved | 0.9 |
| 625 | left | subtype `0x5bc`, kind/world/action hook unresolved | 1.1 |
| 626 | left | subtype `0x5bd`, kind/world/action hook unresolved | 0.6 |
| 642 | left | subtype `0x5be`, kind/world/action hook unresolved | 0.9 |
| 646 | left | subtype `0x5bb`, kind/world/action hook unresolved | 0.9 |
| 706 | left | subtype `0x5bf`, kind/world/action hook unresolved | 0.9 |
| 806 | left | subtype `0x5c4`, kind/world/action hook unresolved | 1.1 |
| 807 | left | subtype `0x5c5`, kind/world/action hook unresolved | 0.9 |

Each five-part range advances by `0x200` per slot. The exact nine-slot records, including weapons and wings,
remain in `reconstructed/actors/monster_class_table.h`; the new code does not regenerate or edit that table.

## Evidence and implementation

See [research section 7](../research/client-actors.md#7-player-model-actor-body-recipes-render-actors-001).
Inputs are pinned by `scripts/pins.py`: text `2bd5f2e9...3724`, image data `c985e2e6...672f`, plus the pinned
trig flag and feature word. The validator loads and checks their full SHA-256 values.

- Generic constructors `0x0138366a`, `0x01383791`, `0x0138383a`, `0x013842a4` set the six skeleton subtypes.
- Startup loop `0x01832c28..0x01832c5d` loads Skeleton01..03 from Data/Skill into `0x422..0x424`.
- RenderCharacter `0x01369f98..0x0136a00d`, and Golden Archer's town branch `0x01367d85..0x01367e23`, supply the whole body.
- The eleven equipment recipes execute the existing constructor/processor chain and RenderCharacter's idle
  part/link plan at action 1, with authored record kind 0 and option/ext 0. Model lookup, strings and engine services are the existing named stubs; no opaque chain jump runs.
- `mu_actor_player_recipe` returns only the six recovered whole-body classes and rows with explicit body equipment.
  The native loader uses slot 0 for the whole mesh, preserves table levels/scales, and loads it on the same Player
  bone pose as the existing armour. Ordinary actors and the fifteen unresolved rows retain their prior route.
- The native host calls the production actor loader, poses each of the 17 covered actors, checks nonempty height
  bounds, exact loaded slot types/levels/scales, mesh counts and zero missing textures.

## Checks

Commands run from the repository root with canonical private-env.sh, nice 10,
make at most four jobs and validator runners two. No full lane gate. Resource pauses followed high load.

| Check | Result | Wall |
|---|---|---:|
| Main baseline `make -j4` | pass | 26.1 s |
| Final `make -j4` | pass | 13.1 s |
| New validator, mutants once | 343 checks, 0 mismatches; 10/10 compiled mutants caught | 58.1 s |
| Post-build validator selection | 19 selected, 3 symbol fallbacks; 12 unused consumers pruned | 53.3 s |
| Affected private validators, no mutants, cached | 19/19 pass, 80,487 cases | 203.4 s including selection |
| Initial audit | 2,129 files, 0 rejected | 14.9 s |

The new validator totals 307 original-instruction or extracted-constructor comparisons, 17 actual native loads
and 19 authored exclusion controls. Its families are recipes 36, body hook 240, equipment plan 11,
RenderObjDraw body stream 36, startup loader 3 and native loads 17. This is not 343 original pixel comparisons.
The original render pipeline for equipment is unchanged, so only the new row runs compiled mutants.

**8d reduced:** the native/tests selection is 146 work items, above the 40-item cap. The private run covers the new native.tests.test_actor_recipes module only, with private-env.sh from the repository root. Portable affected suites and the private reduced run are pending. Brief 6b review found no changed existing
constant, struct layout or table size. The two new exported functions are consumed only by the new tests
and the actor loader; the unchanged actor/skin/cloth implementations retain their earlier coverage.
Static census cross-check: all 1,024 generic class keys give 31 immediate Player-model cases, all present in
this census. Class 297 is the additional recovered processor row. No protection boundary was followed.

## Renders and byte identity

All native captures use DemoKnight and authored demo actor placements,
640x480, two frames, GL, world 0 at 128,124 with each actor at 129,125, direction 5.
The before control admits the same class rows but omits the whole-body slot. It is an instrumented control,
not an unmodified-main image for classes that main refuses. Death King, Marlon and Shadow Phantom Soldier
already load on main. Six skeleton pairs gain body pixels; the eleven equipment control pairs are identical.
The unchanged main binary is retained separately for the one default-draw capture sweep.


| Skeleton class | Changed pixels, frame 1 | Before / after wall |
|---|---:|---:|
| 14 | 1,319 | 1.026 / 1.027 s |
| 15 | 3,222 | 0.817 / 0.804 s |
| 16 | 2,792 | 0.788 / 0.791 s |
| 55 | 3,278 | 0.791 / 0.791 s |
| 56 | 1,000 | 0.782 / 0.883 s |
| 236 | 2,695 | 0.812 / 1.092 s |

All 17 before/after pairs were visually inspected, including the eleven identical equipment controls. Total render wall 29.9 s. The review used native window contents and actor crops, not a desktop screenshot.

One default-draw byte-identity sweep at 640x400, without draw_all or live_time:
- October 22: 28/28 PNGs, 28/28 OBJECT/light dumps and 14/14 normalized reports identical; 14.75 / 14.13 s.
- DATA-ACQ-002: 64/64 PNGs, 64/64 OBJECT/light dumps and 32/32 normalized reports identical; 39.03 / 44.37 s.

Reports normalize only their output-directory prefix. The capture-sweep commands supply no new actor placements.

Screenshots, inputs and local reports are under
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/render-actors-001/`. They are removed at PR-ready cleanup.
No original screenshot, pixel equivalence or live motion comparison is claimed.

## Limits and next

- Fifteen later subtype rows remain unadmitted. Next recover their exact NPC/player kind gates, world/action
  predicates and special mesh/effect hooks. The generic class table's world-0, rand-0 and virtual-processor limits
  remain. Its transformation proxy rows are not assumed to be ordinary spawnable monsters.
- Native Player-model actors retain the existing generic pose and weapon-link path. The original idle link plans
  are compared, but this lane does not establish original-equivalent walking, carried-weapon transforms, shadows,
  buffs, guild/duel state or native fade alpha. Their existing item passes and armour owner effects remain in use.
- Native cloth uses CLOAK-004's own wind/rand history. No original-pixel or temporal equivalence claim.
- Character stats and power, live services and protection code remain outside the lane. Original class equipment
  is used only for appearance; fixtures supply all placement and motion.

## Release

Steward validators: validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_viewport_monsters, validate_worlds_fog.

All 19 rows pass at runtime source commit `55f7dcdc`; 3 retained symbol fallbacks are movement, audio_combat and render_effects17. The selector prunes 12 unchanged library consumers. Only validate_actor_recipes needs mutants, already passed 10/10. All other rows run with --no-mutants. Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Cases | Wall at `55f7dcdc` |
|---|---:|---:|
| `validate_actor_recipes` | 343 | 28.0 s |
| `validate_app_polish1` | 752 | 18.9 s |
| `validate_app_polish2` | 1,028 | 3.4 s |
| `validate_app_polish4` | 10,485 | 35.0 s |
| `validate_audio_callers` | 5,528 | 5.8 s |
| `validate_audio_combat` | 19,548 | 26.5 s |
| `validate_audio_domains` | 2,544 | 21.5 s |
| `validate_audio_items` | 3,000 | 3.0 s |
| `validate_icarus_c2` | 8,400 | 20.7 s |
| `validate_inventory_fx` | 8,017 | 7.0 s |
| `validate_item_callers` | 6,013 | 1.7 s |
| `validate_movement` | 6,614 | 63.1 s |
| `validate_render_effects16` | 424 | 3.8 s |
| `validate_render_effects17` | 618 | 7.7 s |
| `validate_render_effects18` | 540 | 1.2 s |
| `validate_render_effects19` | 400 | 0.9 s |
| `validate_render_effects24` | 226 | 2.5 s |
| `validate_viewport_monsters` | 1,963 | 20.9 s |
| `validate_worlds_fog` | 4,044 | 7.3 s |


Cleanup removes lane outputs, build directories, worktree and local branch after the ready-prs line.
No new private input needs retention. The remote branch stays for the steward.
