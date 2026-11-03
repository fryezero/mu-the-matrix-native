# RENDER-EFFECTS-007

The remaining skill, item and pet effect leftovers of RENDER-EFFECTS-004/005/006/008.
[Finding, addresses, behavior and limits](../research/client-render-effects-007.md).

Claude Opus 5.5 lane. Branch `claude/render-effects-007`, worktree `~/Documents/MTM/worktrees/render-effects-007`,
from origin/main `10b1df13`, merged with `7f18bf05` (SPRITE-DRAW-001 and the lanes before it). Input links
`tools/python` and `evidence` from the main checkout, never staged. No live game, network, item/stat or inventory
operation.

## What landed, per scope item

1. **Other bows' arrows: 30 of 32 verified.** The 32 arrow models: the shared CreateEffect body `0x013cb34d`, the
   separate bodies of 0x471/0x458, 0x459, 0x442, 0x474 and 0x5b0/0x5b1, and every MoveEffect case. Subtypes 0/2/0x63
   are covered, which are all that CreateArrow passes. Arrow01 0x43b also takes 0x63. The work is in
   `reconstructed/combat/arrow_fx.inc`. Render: RenderEffects' dispatch sends 27 types to the default RenderObject;
   0x471 makes the same call; 0x459 draws nothing; 0x45e's extras are not drawn. The 30 types run natively through
   `mu-walk --combat-bow 0xITEM`, and the native crossbow now fires ArrowSteel 0x43c.
   **Not done:** 0x615 and 0x617 stay refused, because their moves look up model bones by name.
2. **Bow 0x12f9's sparks: verified.** `mu_sfx_bow_sparks` covers the fifteen 0x7fd5 joints and Spark particles at the
   weapon bone. They are not called in the native session, which has no weapon-link bone table and no hero bone
   transform.
3. **Rank-5 group 9 (pants): verified to have no owner block.** The full RenderObjDraw runs the group-9 path for the
   seven rank-5 pants types with readable owner bones. It emits no owner particle or sprite and no rand() (280 cases;
   the armour control emits). So nothing goes into `rank5_owner.inc`. The pants' named-mesh body passes (textures
   0x84d9..0x84e0, the level-9 0x8239 overlays) are RENDER-ITEMS-002 part 13's executor work.
4. **Bone −1 attach: verified.** `mu_effect_object_world_matrix` reconstructs `0x0129faee` in `mu_effect_scene`.
   `.ein` records that follow bone −1 now update with the object's world matrix instead of counting as `unposed`.
5. **Rudolph and the pets: partly done (cosmetic only).** Rudolph's 0x3fa gold pieces (`Data\Monster\sulgold.bmd`)
   are in `pet_fx.inc`, and Rudolph's Shiny01 twinkle 0x7f66/7 is in particles.c; both are verified. The other six
   pet particle kinds are traced but not reconstructed (listed in the finding).

## Coverage

| Measure | Before | After |
|---|---|---|
| Skill primary routes / weighted | 20/23, 65/77 | 20/23, 65/77 (unchanged: Triple Shot was already P) |
| Bow arrow models with create/move | 1/33 (Arrow01) | 31/33 (0x615, 0x617 remain) |
| Bow 0x12f9 sparks | not reconstructed | verified routine (not called natively) |
| Rank-5 owner effects | 19/19 armour types, pants open | 19/19; pants verified to have none |
| EffectManager bone −1 | counted `unposed` | attached (world matrix) |
| Pet effects | 0x460/4 only | + 0x3fa/0; pet particle kinds 1/8 (0x7f66/7) |
| Native effect kinds (combat pool) | — | +30 arrow types, Arrow01/0x63, 0x3fa/0 |

## Checks

- `scripts/validate_render_effects7.py --cases 20 --mutations` (recorded run): **5,960** original-instruction cases,
  zero mismatches; **31/31** compiled mutants caught. Per family: CreateEffect 1,840, MoveEffect 1,840, sparks 400,
  pants owner 280, world matrix 400, Shiny01/7 create, move and render 400 each. Registered as
  `validate_render_effects7`; the gate run (`--cases 2`) gives 596 cases and 31/31. Its owner test is
  `native/tests/test_render_effects.py::RenderEffects.test_other_bows_arrows_original_instructions_and_compiled_mutants`.
- Private validators rerun on the merged tree, all passing:
  - validate_render_effects (002), 3, 4, 5, 6 and 7;
  - validate_skill_fx (its ctypes `Effect`/`Call` gained the appended fields), validate_particles, validate_combat,
    validate_joints, validate_world_particle_consumers and validate_map_effects;
  - before the merge, also validate_worlds_l, validate_worlds_m, validate_worlds_p, validate_helpers,
    validate_item_effects, validate_icarus_c2 and validate_pets (with `MU_GAME_ROOT`).
- Native tests (new):
  - `test_other_bows_arrows_session`: the crossbow fires three 0x43c with 0 unsupported. `--combat-bow 0x12fa` fires
    three LaceArrow 0x47f, and removing the model changes pixels.
  - `test_rudolph_gold_pieces_effect_pixels` (`pet_gold_host`): 8 created, live and drawn, with pixels; none drawn
    without the model.
  - `render_effects6_host`: bone −1 equals the world matrix byte for byte, counts as an update and is not `unposed`.
- Gate on the merged tree: `nice -n 10 bash scripts/local-macos-ci.sh` passes.
  - 38 suites, 1,788 tests: 1,551 passed, 237 skipped, 0 failures.
  - Fixtures, native viewer and live readers ok; audit 1,790 staged files, 0 rejected.

## Native frames inspected (installed data, local, deleted at cleanup)

- **Setup.** `mu-walk --combat-weapon bow --combat-bow <item> --combat-script 2:skill:24:spider` at Lorencia
  182,128, frame 30, for 29 bows.
- **Every bow creates its arrows** (3 to 4 per fan; the fan follows CreateArrows' special-bow rules).
- **Arrows visible** in the inspected frames:
  - ArrowWing 0x443: glowing blue wings;
  - ArrowNature 0x441: cyan glow sprites;
  - ArrowBomb 0x442;
  - KCross 0x471: pink trails;
  - 0x45c: white flare01 sprites;
  - Carow 0x474: black heads;
  - 0x60a: blue sparkle sprites;
  - 0x60e: orange fire sprites;
  - arrow_mastery7s 0x612;
  - 0x614: sprites;
  - small steel/laser/V arrows: at the frame edge.
- **0x5b0/0x5b1** draw white quads, a texture-resolution issue of those models.
- **Sprites draw on current main** (SPRITE-DRAW-001 found the shared path intact), so none of these visuals waits on
  that lane.
- **Rudolph's gold pieces** (`pet_gold_host` on the installed sulgold.bmd): 8 drawn, 62 lit pixels in a 200×160
  top-down raster; gold coins scattered around the throw point.

## Hash and behavior changes (intended)

- **Crossbow.** The native crossbow and any `--combat-bow` now create their own arrow effect; it was counted
  unsupported before.
- **Arrow counts.** `stats.arrows` counts every reconstructed arrow type.
- **Arrow01 0x63.** CreateArrow's flag-2 Arrow01 (subtype 0x63) is created instead of refused.
- **Trail key.** The 0x46c trail's CreateEffect call now carries key 0xffff in `range`; the native combat host reads
  `range` only for Rageful Blow, so it draws nothing different.
- **Bone −1 records** (Ignis Volcano types 175/176 in the local effect table) now attach and draw.
- **sulgold.bmd** loads in every world's particle module (`MU_WORLD_FX_MODELS` 17 → 18). It draws only when 0x3fa is
  requested.
- **No existing hash pin changed:** the gate's pinned tests pass, and Arrow01, Fire Ball and Twisting Slash go
  through unchanged code paths (validate_skill_fx and validate_render_effects4 equal).

## Integration notes (shared files, minimal hooks)

- **`reconstructed/combat/skill_fx.c`:**
  - the arrow and pet hooks in effect_supported, CreateEffect and MoveEffect;
  - 0x459's motion in the second switch;
  - the two `.inc` includes;
  - `mu_sfx_arrow_type` exported (was static);
  - Arrow01's create body moved into `arrow_fx.inc`.
- **Appended struct fields:**
  - `skill_fx.h`: `mu_sfx_effect.field_188`, plus `mu_sfx_arrow_type`, `mu_sfx_is_arrow` and `mu_sfx_bow_sparks`;
  - `joints.h`: `mu_jt_call.arg7/arg8`;
  - `validate_skill_fx.py`: the matching ctypes fields.
- **`reconstructed/particles/particles.c`:** Shiny01 subtype 7 inside the existing Shiny01 cases.
- **`native/core`:**
  - `mu_combat.{c,h}`: `bow_item`, `MU_COMBAT_MODEL_BOW_ARROW` and `mu_combat_arrow_file`;
  - `mu_effect_scene.{c,h}`: the world matrix;
  - `mu_particles.{c,h}`: bone −1 in `o_ein_update`, and the 0x3fa model (`MU_WORLD_FX_MODELS` 18; on conflicts
    keep both sides and recount).
- **Other files:**
  - `native/world/world_tool.c`: `--combat-bow`;
  - `native/Makefile`: `pet-gold-host`;
  - `scripts/validators.toml`: one row.

## Remaining

- **Arrows 0x615/0x617:** they need a named-bone service.
- **Arrow paths left out:** the ground test of skills 0x7e7/0x7fc/0x7fd, the arc skill 0x2d8, and 0x442 with a
  straight skill.
- **0x45e's render-time particles and decal.**
- **The arrows' native joint and particle kinds:** create/move/render are verified as calls, but the native modules
  count them unsupported.
- **Sparks in the native session:** they need the weapon-link bone and a hero bone transform.
- **Six pet particle kinds** (Clud64, firehik03, Impack01/1, firehik_mono ×3).
- **The pants' named-mesh body passes** (RENDER-ITEMS-002 part 13).
- **A live comparison.**

## Cleanup

- Deleted after the PR: `renders/render-effects-007`, `scratch/render-effects-007`, `native/build`, this worktree
  and the local branch.
- No new local input needs to be kept.
