# RENDER-EFFECTS-011

The combat/effect leftovers of RENDER-EFFECTS-010: the bows' remaining particle kinds and effects, RenderEffects'
0x45e case, the functor tick per drawn frame, effect 0x70c, and a live read of the spark bone.
[Finding, addresses, measurements and limits](../research/client-render-effects-011.md).

Claude Opus 5.5 lane.

- Branch `claude/render-effects-011`, worktree `~/Documents/MTM/worktrees/render-effects-011`, started on
  RENDER-EFFECTS-010's head `724ad10a` while #287 was in the steward's batch, then merged with origin/main
  `26b9ef07` (#287 merged, #288); MERGED_MAIN_NOTE.
- Input links `tools/python`, `evidence` and `input` come from the main checkout and are never staged.
- One live session (below); no network, item, stat or inventory operation.

## What landed, per scope item

1. **The 33 bows: unsupported 598 → 77** (this lane's scene; RENDER-EFFECTS-010 counted 553 with its own).
   - 16 particle kinds, **verified** (`reconstructed/particles/bow_kinds2.inc`): Flare 0x7f78/5, Smoke_line 0x83b3/1,
     Spark04 0x8155/2, smoke01 0x7f5a/0x18, 0x4e, 0x7a, firehik03 0x8085/0x11 (dies with its owner arrow),
     pin_star02_pupple 0x810c/0, Snow_Chip02_red 0x83b8/2, firehik01 0x8084/0x1e, flare_mono 0x8184/1,
     lighting_mega01..03 0x8081..0x8083/0, plus 0x45e's 0x7f5a/0x6d and 0x8108/3.
   - 7 effect kinds, **verified** (`reconstructed/combat/bow_fx.inc`): 0x477/3, /4 (m_Waves rings), 0x60b/0
     (Darkangel_effect), 0x611/0 (ringofpower), 0x45f/0, /1 (darkwing_hetachi feathers); their models load in the
     combat session only for the bow whose arrows ask for them.
   - Native plumbing: two world-particle bitmaps (0x810c, 0x83b8), the particle host's `owner_live` and `create`
     callbacks, and arrow-owned legacy particles (an arrow's "this effect" owner becomes its effect OBJECT at
     `MU_WORLD_FX_COMBAT_BASE`, answered by `mu_combat_object`).
   - Left: 14 joint kinds (66 requests) and effect 0x38b5/1 (11).
2. **0x45e's render-time extras, verified** (RenderEffects' case `0x01518f49`, `mu_sfx_arrow_render_extras`): a tick
   at twice the speed, the model drawn twice for the arrows' subtypes, 0x7f5a/0x6d and 0x8108/3 owned by the arrow
   each drawn frame; the decal 0x8002 is only for subtypes 3..7 (counted, never an arrow's). Bow 0x1304: 0 → 20
   particles.
3. **The functor tick** now runs in `mu_combat_draw_models`, once per drawn frame. Of the 33 bows only 0x1323,
   0x1329 and 0x132f change (frame 20); the other 30 bows and the other combat scenes are byte-identical.
4. **Effect 0x70c, verified** (create `0x0141a4c4` with its eight child effects, move `0x014d2131` with the +0xd8
   pulse); validator only, no native route fires the ground skills. The clearing site of the owner flag +0x64 was not
   found (CreateCharacter and its OBJECT initialisers write none; see the finding); the native keeps one flag per
   owner.
5. **Uruk's 0x806e/12** stays refused: it fires only with the Uruk weather input (off by default, no capture).
6. **Muun table**: not done (no native Muun owners).
7. **The spark bone, read live: 0** (`[[0x0a39d754] + 0x9c4d]`, Nighty in Lorencia). `MU_COMBAT_SPARK_BONE` keeps 0,
   now a live value instead of a stand-in.

## Live session (2026-11-04)

- Lock `~/Documents/MTM/mu-mac-tools/.game-lock` 14:16:48 → 14:19:32 (the other lock path absent, no client running
  before). The free-runtime client via DATA-ACQ-002's `login.sh` (copied to this lane's scratch, Keychain password
  never printed), logged in 14:18:26, `/move Lorencia` at entry (world 0 read back).
- Reads only (`live-readers/memread`): `[0x0a39d754]`, `[0x01cf15fc]`, 32 bytes at hero + 0x9c3d, the byte at
  hero + 0x9c4d twice (14:18:47, 14:19:00). No screenshots, no writes, no packets.
- Quit 14:19:11 (client and launcher closed). `LauncherOption.if` restored byte for byte from the rollback copy;
  `DisplayDeviceModeIndex` (rewritten to 4) set back to 2; the rest of `user.reg` differs only in timestamps.

## Checks (wall times)

CHECKS_PLACEHOLDER

## Hash and behaviour changes (intended)

- **World particle table** 72 → 74 bitmaps (`MU_WORLD_PT_BITMAPS`): pin_star02_pupple and Snow_Chip02_red, appended
  before the rain textures (the bitmaps list of every particle summary grows by two).
- **Combat**: bows 0x12fa, 0x12fc, 0x12fd, 0x12fe, 0x12ff, 0x1302, 0x1304, 0x1305, 0x130a, 0x130c, 0x130e, 0x131e,
  0x1320, 0x1323, 0x1326 draw the new kinds; 0x1323, 0x1329, 0x132f's arrows animate per drawn frame; 0x1304's
  render-time particles draw from the combat RNG, so its later frames follow the number of drawn frames (as the
  client's single rand()).
- **Combat summary**: new stat field `render_decals` (not printed).
- **Effect record** gains +0xd8 (`field_d8`), also in validate_skill_fx's field table.
- `worlds_m_host` takes 0x8184/3 as its absent kind (0x8184/1 is supported now).

## Integration notes (shared files, minimal hooks)

- `reconstructed/particles/particles.c`: one include, the kind/create/move/render hooks, 0x83b3/1's light.
  `particles.h`: two host callbacks appended (`owner_live`, `create`); `scripts/validate_particles.py` mirrors them.
- `reconstructed/combat/skill_fx.c`: one include and three hooks (supported, create, move); `skill_fx.h`: the +0xd8
  field and `mu_sfx_arrow_render_extras`; `arrow_fx.inc`: that function.
- `native/core/mu_combat.{c,h}`: four model slots (0x477, 0x60b, 0x611, 0x45f), the tick in the draw, the 0x45e
  draw, arrow-owned particles, `mu_combat_object`. `native/core/mu_particles.{c,h}`: two bitmaps, the combat object
  range, the host callbacks. `native/world/parts/combat.c`: the combat object hook.
- `scripts/validators.toml`: one row.

## Steward

STEWARD_PLACEHOLDER

## Remaining

- **The bows' joints** (66 requests, 14 kinds; traced, bodies listed in the finding's limits) and room in the combat
  bitmap table for their bitmaps.
- **Effect 0x38b5/1** (0x60f), drawn as a model above 0x7a4.
- 0x70c's child effects 0x703..0x706 and a native route that fires the ground skills; the +0x64 clearing site.
- Uruk's 0x806e/12 (needs a weather feed), the Muun table (needs Muun owners).
- 0x45e's model colour (+0x54 = 1) and the decal; a live comparison of the bows.

## Cleanup

CLEANUP_PLACEHOLDER

## WIP (stopped by owner, 2026-11-04 ~15:00)

- Done and verified: 16 particle kinds, 7 effect kinds, RenderEffects 0x45e, effect 0x70c; validate_render_effects11
  `--cases 20 --mutations`: 1,760 cases, 0 mismatches, 75/75 mutants (54 s). 29 affected rows rerun without mutants:
  all pass. Bows 598 → 77 vs main 90e11d71; 10 other combat/pet scenes and the 32 DATA-ACQ-002 tours byte-identical
  (frame reports differ only in paths and the bitmaps list). Spark bone read live: 0. Merged main 90e11d71.
- Next: rerun `run_validators.py --private --only validate_render_effects11` (interrupted), unit tests
  (test_render_effects11 passed earlier), audit; fill CHECKS/STEWARD/CLEANUP placeholders and MERGED_MAIN_NOTE; PR;
  ready-prs line; clean up (base worktree ~/Documents/MTM/worktrees/re011-base, renders/ and scratch/render-effects-011).
