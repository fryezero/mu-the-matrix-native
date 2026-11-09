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
  part/link plan. Model lookup, strings and engine services are the existing named stubs; no opaque chain jump runs.
- `mu_actor_player_recipe` returns only the six recovered whole-body classes and rows with explicit body equipment.
  The native loader uses slot 0 for the whole mesh, preserves table levels/scales, and loads it on the same Player
  bone pose as the existing armour. Ordinary actors and the fifteen unresolved rows retain their prior route.
- The native host calls the production actor loader, poses each of the 17 covered actors, checks nonempty height
  bounds, exact loaded slot types/levels/scales, mesh counts and zero missing textures.

## Checks

Pending final checks. Commands run from the repository root with canonical private-env.sh, nice 10,
make at most four jobs and validator runners two. No full lane gate.

## Renders and byte identity

Pending final recorded totals. All native captures use DemoKnight and authored demo actor placements,
640x480, two frames, GL, world 0 at 128,124 with each actor at 129,125, direction 5.
The before control admits the same class rows but omits the whole-body slot. It is an instrumented control,
not an unmodified-main image for classes that main refuses. Death King, Marlon and Shadow Phantom Soldier
already load on main. Six skeleton pairs gain body pixels; the eleven equipment control pairs are identical.
The unchanged main binary is retained separately for the one default-draw capture sweep.

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

Steward validators: pending selection after build.

Cleanup removes lane outputs, build directories, worktree and local branch after the ready-prs line.
No new private input needs retention. The remote branch stays for the steward.
