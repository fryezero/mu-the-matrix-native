# SPRITE-DRAW-001

The question was whether native sprites are created and counted as drawn but produce no pixels (RENDER-WORLDS-Q2
§5, Acheron). **They do produce pixels; there is no shared-path fault.** Acheron's six Spark04 sprites are outside
the view frustum at the DATA-ACQ-002 tile. [Finding, trace, measurements and limits](../research/client-sprite-draw.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/sprite-draw-001`, branch `claude/sprite-draw-001`, from
  origin/main `79a6b470`, then origin/main `10b1df13` (#271 RENDER-EFFECTS-008) and `8eb54978` (#272
  RENDER-WORLDS-Q2), both clean, sprite path untouched.
  Input links `tools/python` and `evidence` from the main checkout, never committed.
- **Repro (verified):** `native/tests/sprite_draw_host.c` (portable `test_native_sprite_draw.py`) draws one sprite
  ahead of the eye through `mu_world_particles_draw` in raster and in headless GL. It gets 676 lit px for each of
  blends 0/2/4, and 0 px at 1.5 vertical half-angles above the axis (Acheron's geometry). 5/5 planted mutants of the
  sink/bind/render path are caught.
- **Acheron (measured):** the quads reach GL at eye-space y/−z = 1.45–1.62 × tan(fov/2), above the top edge. Q2's
  probes each left the frame unchanged for that reason: depth-off alone changes nothing outside the frustum, and ×20
  alone reaches the top rows but sits behind the ground there. Live shows no glints there. `drawn_sprites` counts
  quads handed to the GL stream, not on-screen quads.
- **Sprites with pixels (measured):** these produce sprite pixels (pass on vs. sink-less):
  - 134 Ashen Aida: 12 in-frustum Spark03 quads, 10,128 px; image vs live 13.135 → 13.053.
  - 63 Vulcanus: 3 flare01 quads, 11,470 px; 1.863 → 1.841.
  - 79b Event Square: 6 Flare quads, 72,087 px; 3.817 → 3.604.
  - 144 Swamp of Destruction: 21 Shiny02 quads, 1,260 px, masked.
  - flareBlue 0x7fdd: `mu-render character`, armour 0x1c26, 7,710 px at frame 0.

  Every one of the 32 captures that has an in-frustum sprite quad has sprite pixels.
- **Hashes:** no change. No source in the draw path changed; only the host, its Make rule and the test are added.
- Shared lines: `native/Makefile` (one `sprite-draw-host` rule beside `inventory-skin-host`). No change to
  `mu_particles.c`, `sprites.c` or `gl_backend.c`. RENDER-ITEMS-002, INTEGRATION-GREEN-002 and RENDER-EFFECTS-007
  are unaffected.

## Checks

- Portable: `native/tests/test_native_sprite_draw.py` (1 test). RENDER-WORLDS-Q2 §5 now points here. `test_render_effects.py` + `test_native_particles.py`
  (15 tests, 5 skipped) pass.
- PR-ready gate, on the merge of origin/main `8eb54978` after `make -C native clean`:
  `nice -n 10 bash scripts/local-macos-ci.sh` passes.
  - **38 suites, 1,785 tests, 1,549 passed, 236 skipped, 0 failures/errors.**
  - Fixtures, native viewer and live readers pass; the audit covers 1,785 files with 0 rejected.
- Private (`run_validators.py --private --jobs 2`, `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT` = the installed
  client, `MU_SECTION3` = `main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin` for `validate_effects`):
  **12 pass, 0 fail.**

  | Validator | Cases | Mutants |
  |---|---:|---:|
  | `validate_particles` (incl. `sprite`/`sprite_create`/`sprite_render`) | 407 | 22 |
  | `validate_joints` | 180 | 9 |
  | `validate_world_particle_consumers` | 900 | 7 |
  | `validate_item_effects` | 1,500 | 3 |
  | `validate_render_effects` | 660 | 8 |
  | `validate_render_effects3` | 720 | 10 |
  | `validate_render_effects4` | 1,920 | 15 |
  | `validate_render_effects5` | 1,190 | 25 |
  | `validate_render_effects6` | 1,000 | 34 |
  | `validate_worlds_q` | 11,000 | 45 |
  | `validate_worlds_q2` | 4,000 | 50 |
  | `validate_effects` | pass | |

  Steward validators: validate_particles, validate_joints, validate_world_particle_consumers, validate_effects,
  validate_item_effects, validate_render_effects, validate_render_effects3, validate_render_effects4,
  validate_render_effects5, validate_render_effects6, validate_worlds_q, validate_worlds_q2 (env: MU_RECOVERY_INTEGRATION=1,
  MU_GAME_ROOT, MU_SECTION3=…/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin).

## Left

- The frustum test of 0x01692887 (the native marks every live sprite visible; only the alpha ramp depends on it).
- Owner binding of native sprites (RENDER-EFFECTS-005 limit), which is placement, not visibility.

No original client or launcher was started, and the DATA-ACQ-002 inputs were only read. The temporary trace switches
were local and removed. Renders and scratch (`renders/sprite-draw-001`, `scratch/sprite-draw-001`) are deleted at
handoff. No new local input needs retention.
