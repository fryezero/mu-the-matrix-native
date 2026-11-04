# RENDER-EFFECTS-010

The pets' six particle kinds, arrows 0x615/0x617's particle kinds and dark glow meshes, RENDER-EFFECTS-007's arc and
ground arrow paths, and the most requested particle kinds of the other bows.
[Finding, addresses, measurements and limits](../research/client-render-effects-010.md).

Claude Opus 5.5 lane.

- Branch `claude/render-effects-010`, worktree `~/Documents/MTM/worktrees/render-effects-010`, from origin/main
  `5cb6fa6d`, merged with `1e247ae9` (#285 RENDER-WORLDS-AFTER5; it touches none of the files these checks build).
- Input links `tools/python`, `evidence` and `input` come from the main checkout and are never staged.
- No live game, network, item/stat or inventory operation.

## What landed, per scope item

1. **The six pet particle kinds: verified, drawn in the pet scenes.**
   - `reconstructed/particles/pet_kinds.inc`: Clud64 0x7ffd/0xb, firehik03 0x8085/1, firehik_mono 0x8086/4,
     0x8087/8, 0x8089/5. Impack01 0x7efa/1 shares 0x7efa/2's body in `world_owned_fx.inc` (it sets its blend state
     and draws no sprite, as the client).
   - The skeleton's flames follow their pet: `mu_world_pets` passes the pet as the particle owner
     (`MU_WH_PET_BASE` + key, answered by `mu_world_pets_object`).
   - Clud64's bitmap joins the world particle table.
   - Pet scenes: demon 18 → 0 unsupported, panda and PC panda 1 → 0, skeleton on a dying demo player 4 → 0.
2. **0x615's 0x8081..0x8083/8 and 0x617's 0x85fb/2 and 0x8450/4: verified** (`arrow_kinds.inc`, bitmaps
   lighting_mega01..03, aura_0316_mono, Wind_smoke). Bow 0x1329: 280 → 0; bow 0x132f: 56 → 0.
3. **The dark glow meshes: found and fixed.** RenderObject's draw hands 0x613..0x617 to render-registry functors
   (`0x00a4269f..0x00a43160`) that draw mesh by mesh with additive and chrome passes, their own colours and, for
   0x615, the elec_light strip 0x8551. Verified as `mu_sfx_arrow_render_passes` / `mu_sfx_arrow_tick_speed`
   (`arrow_fx.inc`); `mu_combat_draw_models` draws the passes. 0x613, 0x614 and 0x616 change with them.
4. **The 007 arrow paths.**
   - The arc skill 0x2d8: CreateEffect's branch for every arrow type and Arrow01's lobbed move: **verified**.
   - The ground test of 0x7e7/0x7fc/0x7fd (MoveEffect `0x014eca00`, the owner's +0x64 flag via
     `MU_SFX_CALL_OWNER_FLAG`): **verified**.
   - The native session fires none of these skills, so they are reached only by the validator.
   - Not done: 0x442 with a straight skill (client reads an unset stack vector), 0x45e's render extras (read
     statically, see the finding).
5. **The other bows' kinds: 8 of the most requested, verified** (`bow_kinds.inc`, 0x7fcd/1 in particles.c):
   0x7fcd/1, 0x7f73..0x7f75/0, 0x7f5a/0x86, 0x810a/0x24 and 0xe, 0x7f26/0x1e, with pin_star03 and flower1..3.
   33 bows: unsupported 1,561 → 553.

**Live read:** not taken (the spark bone stays RENDER-EFFECTS-009's stand-in; the glow-mesh question was settled
statically by the registry).

## Checks (wall times)

- `scripts/validate_render_effects10.py --cases 20 --mutations` (recorded, 63 s): **1,540** original-instruction
  cases, zero mismatches; **54/54** compiled mutants caught. Families: pets create/move/render 140 each, arrows 100
  each, bows 160 each, functor 100, arc_create 120, ground_move 120. Registered as `validate_render_effects10`
  (`--cases 2`: 154 cases, 54 mutants; runner 36–40 s). Owner test:
  `native/tests/test_render_effects10.py::ClientComparison.test_original_instructions_and_compiled_mutants`.
- Rerun without mutants, the rows whose comparisons go through the changed particle/combat code, all pass:
  validate_particles (407 cases, 0.8 s), validate_render_effects (0.7 s), 3 (0.7 s), 4 (4.6 s), 6 (1,000, 1.0 s),
  7 (596, 1.3 s), 9 (304, 0.8 s), validate_world_particle_consumers (0.6 s), validate_worlds_l (1,260, 0.8 s),
  validate_worlds_m (1,080, 0.8 s), validate_skill_fx (660, 0.7 s), validate_combat (496, 0.7 s), validate_pets
  (147 s). Earlier in the lane the same set plus effects, joints, helpers, raven, item_effects, map_effects ran with
  their mutants: all pass (render_effects6 after re-anchoring two mutants on world_owned_fx.inc).
- Unit tests for the changed code: test_render_effects10 (8 tests), test_render_effects9, test_native_particles,
  test_native_pets, test_render_effects, reconstructed/particles/test_particles (62 tests, 35 s); test_native_combat,
  test_native_helpers, test_native_joints, reconstructed/combat tests (OK, 19 s); their private variants with
  `MU_RECOVERY_INTEGRATION=1` (26 tests, 109 s).
- Audit: 1,828 staged files, 0 rejected (37 s). Build `make -j4` (12 s).
- Scenes (installed data): 33 bows + 10 combat + 9 pet scenes, base once (51 s) and branch (49 s).
- DATA-ACQ-002 tours, default draw, base once (56 s) and branch (55 s): 128 PNGs, 64 dumps, 33 JSON, 32 logs
  byte-identical; frame reports differ only in the particle `bitmaps` list.

## Hash and behaviour changes (intended)

- **World particle table** 62 → 72 bitmaps (`MU_WORLD_PT_BITMAPS`): Clud64, lighting_mega01..03, aura_0316_mono,
  Wind_smoke, pin_star03, flower1..3, appended before the rain textures. The `bitmaps` list of every particle summary
  grows; `test_native_particles` and `particle_consumers_host.c` follow.
- **Bows 0x1323, 0x1326, 0x1329, 0x132c, 0x132f** draw through the functor passes; bows 0x12ec, 0x12f3, 0x12f4,
  0x12fe, 0x130e, 0x1323, 0x132c draw their new particle kinds. The demon pet draws its clouds.
- **Arrows' frames** of 0x613..0x617 advance by the tick each step (they animate).
- `test_render_effects9`'s 0x617 test now expects no unsupported kinds.

## Integration notes (shared files, minimal hooks)

- `reconstructed/particles/particles.c`: three includes, the kind/create/move/render hooks, the Clud64 subtract
  state, 0x7fcd/1 (its own case split from smoke02/smoke05).
- `reconstructed/particles/world_owned_fx.inc`: 0x7efa/1 beside 0x7efa/2.
- `reconstructed/combat/skill_fx.{c,h}`: the ground test, Arrow01's lobbed move, `MU_SFX_CALL_OWNER_FLAG`, the
  appended `mu_sfx_mesh_pass` API. `arrow_fx.inc`: the arc create and the functors.
- `native/core/mu_combat.{c,h}`: the pass draw, the tick, the 0x8551 extra bitmap, the owner flag and TerrainWall
  answers. `mu_particles.{c,h}`: the bitmaps. `mu_world_pets.{c,h}`, `mu_world_helpers.{c,h}`: pet owners.
- Scripts: `validate_particles.py` gains `OWNED_KINDS`; `validate_render_effects7.py` no longer expects 0x2d8 to be
  refused; `validate_render_effects6.py` re-anchors two mutants; `validators.toml` one row.

## Steward

Steward validators: validate_render_effects10 (mutants: yes, its own), validate_render_effects9,
validate_render_effects7, validate_render_effects6, validate_render_effects4, validate_render_effects3,
validate_render_effects, validate_particles, validate_world_particle_consumers, validate_worlds_l, validate_worlds_m,
validate_skill_fx, validate_combat, validate_pets (the others without mutants).

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_SECTION3=…/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_GAME_ROOT` = the installed client (`…/MuTheMatrix/prefix/drive_c/MuTheMatrix`); `MU_OBJECTS_PLAIN_DIR` =
`native/scratch/objects/live/plain` for test_native_particles' installed-data test.

## Remaining

- **The spark bone** live read (`[[0x0a39d754] + 0x9c4d]`, hero in Lorencia).
- **0x45e's render extras** (particles 0x7f5a/0x6d, 0x8108/3; decal 0x8002 only for subtypes 3..7).
- **0x442 with a straight skill**; effect 0x70c of the ground skills; a native route that fires 0x2d8/0x7e7/0x7fc.
- **The bows' remaining 553 requests** (kinds listed in the finding's limits).
- A live comparison.

## Cleanup

- Deleted after the PR: `scratch/render-effects-010`, `renders/render-effects-010` except
  `renders/render-effects-010/keep` (three before/after PNGs) until the steward has the PR, the base worktree
  `worktrees/re010-base`, `native/build`, this worktree and the local branch.
- No new local input needs to be kept.
