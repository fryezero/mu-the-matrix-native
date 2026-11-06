# RENDER-WORLDS-AFTER6

The world/object leftovers of [AFTER5](RENDER-WORLDS-AFTER5.md) ("Remaining"), [SPRITE-DRAW-001](SPRITE-DRAW-001.md)
("Left") and [RENDER-EFFECTS-008](RENDER-EFFECTS-008.md) ("Left").
[Addresses, checks, fidelity and limits](../research/client-worlds-after6.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-after6`, branch
  `claude/render-worlds-after6`, from origin/main `1e247ae9`, merged with `32b7f34d`.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.

## What changed

1. **Tick handlers 4, 6 and 8 (verified).** `0x018500bf` is the segment-against-OBB test, not a hero box test:
   - 4 (`0x00ce1947`) and 6 (`0x00ce1e4b`) test the **mouse** segment `0x0bdc5984 → 0x0bdc5990` against the
     object's OBB `+0x31c`;
   - 8 (`0x00ce23ad`) tests **CameraPosition `0x0bdc5ab4` → the hero** against a coarse box, then against the
     six faces of the object's turned box. A hit sets alpha target `+0xd8` to 0.1, a miss 1.0.
   - All three are ported in `reconstructed/objects/action_registry.c` (the picking primitives restated there).
   - The world's object tick passes CameraPosition (`mu_objects_step_inputs.camera`).
2. **`0x01692887` (verified).** It has no frustum test: visible = 1 for every live sprite, which
   `mu_pt_sprites_mark_visible` already did. Only a comment changed (`particles.h`).
3. **Bone −1 following (`0x0129faee`)** has been on main since RENDER-EFFECTS-007 (`07cccda8`); nothing to do.
   **`0x0129f4cb`'s dt-0 update (verified)** now runs at the map-effects attach (`mu_world_particles_ein_prime`,
   `mu_effect_prime_matrix`).

**Shared lines:**
- `mu_objects.h`: one step-input field and one argument;
- `mu_objects_runtime.c`: one call;
- `mu_charsel.c`, `mu_login.c`, `mu_terrain.c`: one NULL initializer each;
- `world/parts/objects.c`: the camera;
- `mu_particles.{c,h}`: the prime and an owner helper;
- `mu_map_effects.{c,h}`: the prime op;
- `mu_effect_scene.{c,h}`: one function;
- `validate_worlds_after5.py`: its ctypes struct follows the new `mu_anim_inputs`;
- one validator row.

## Checks

Under the 2026-11-04 test budget: no lane gate. Env `MU_RECOVERY_INTEGRATION=1`,
`MU_SECTION3=<main-exe-study>/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`.

| Check | Result | Wall time |
|---|---|---|
| `validate_worlds_after6` families (`--cases 3000 --lang-dir`) | hover 3,000, camera 3,000, sprite_visible 300, prime 1,000, live_rows 600 (private): **7,900 equal, 0 stops** | 102 s |
| `validate_worlds_after6` mutants (once) | 25 in the full run; 5 that tied (equivalent: `e > 0` vs `>= 0`, `t > 0`, a redundant range axis, a degree constant, a degenerate-only guard) were replaced by non-equivalent ones and run alone: **30/30 caught**, lowest 14, none stopped | ~29 min + 297 s |
| `validate_worlds_after5` (no mutants, `--lang-dir`) | set_action 3,000 + tick 3,000 + live_rows 1,084 equal | 8 s |
| `validate_particles` (registered args, no mutants) | 407 cases in 12 families equal | 1 s |
| `validate_render_effects7` (no mutants) | 596 cases equal (world_matrix 40) | 1 s |
| Unit/host tests | `test_worlds_after6` 7 (+1 private), `test_worlds_after5` 8 (+1), `test_native_anim` 1, `test_native_map_effects` 1 (+1), `test_native_render_effects6`, manifest tests: 61 run, 26 private skipped, OK | 3 s (87 s with the private render_effects6 run) |
| Build | `make -j4` 25 s; `native` mu-world + hosts 6 s | |
| Audit | 1,848 staged files, 0 rejected | 15 s |
| Fidelity tours | base 53 / 126 / 77 s, lane 49 / 115 / 56 s (lang default / lang live_time / plain 32) | |

Steward validators: validate_worlds_after6 (mutants: yes, new), validate_worlds_after5, validate_particles,
validate_render_effects7 (no mutants).

## Inputs for later lanes (local, never commit)

None new. The tours used `scratch/render-worlds-after5/lang/mapanim.tsv` and
`scratch/render-effects-008/plain-s2-lorencia/mapeffects.tsv` (both kept by their lanes).

## Remaining

- Handlers 4 and 6 do not run natively, because map objects carry no OBB `+0x31c`. The next step is the render
  Transform's box write `0x012b5bde` for map objects, plus passing the walk frame's MouseTarget into the step.
  No live row uses them today.
- World 145 (the only handler 8 world) has no capture and no decoded `EncTerrain146` objects. A capture there
  needs walking, which the live rules forbid.
- AFTER5's other items stay as they were: the render-time light capture, and world 0x27's tower state (server).

## Cleanup

Deleted after the PR: `renders/render-worlds-after6`, `scratch/render-worlds-after6`, the base worktree
`worktrees/render-worlds-after6-base`, `native/build`, this worktree and the local branch.
