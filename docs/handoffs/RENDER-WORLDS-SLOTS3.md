# RENDER-WORLDS-SLOTS3

RENDER-WORLDS-SLOTS2's follow-ups: RenderObjectVisual's outer `rand() % 30` (`0x017f9797`) in the worlds without a
class, and Test Area 121's two slots.

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-slots3`, branch `claude/render-worlds-slots3`.
- Branched from #313's branch; merged origin/main `18ab0134` (#313..#316) as `f178b5a4`, then `71692108` (#317/#318,
  docs/images and the audit script only) as `19d2ca15`.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.
- Finding: [client-worlds-slots3.md](../research/client-worlds-slots3.md).

## Final state (PR-ready)

**Original (verified).** `0x017f9758` draws the outer rand for every object with a model in every world, before the
switch `0x017f97e2` (inline cases 0..4, 6, 8..17, 0x34, 0x37; default branch `0x017fcb5c` for the rest).

**Native now.**
- `mu_obj_visual_flicker(world, has_model)` answers for every world with a model except 4/7/8 (whose
  `mu_builtin_visual` draws it first).
- The object runtime draws it once (top of `handler_visual` and the non-primary branch) and keeps the value in
  `rt.visual_outer_rand`. `world_flames` and `icarus_cover` no longer draw it.
- The particle visual (`reconstructed/particles/visual.c`) reads `mu_pt_visual_host.outer_rand` instead of drawing
  from the particle generator; `mu_world_particles_object_visual` takes the value.

Per-world fixes: 0..3 and Tormenta 141 moved from the particle generator to the object generator; Icarus 10 the same
(`icarus_cover`); 37/40 moved to the top of the visual; every other classless world (6, 9, 11, 18, 24, 30, 31, 33, 34,
38, 39, 41, 42, 46, 51, 56, 65..68, 73, 74, 98, 102, …) gained the draw; 4/7/8 unchanged.

### Checks (final code; validators at `f178b5a4`, whose compiled inputs equal the head's)

| Check | Result | Wall |
|---|---|---|
| `validate_worlds_slots3` (mutants) | 36 families × 1,000 = 36,000 cases, 0 mismatches/stops; 22/22 mutants detected ("Kanturu flame 0x3b": 44) | 120.6 s |
| `validate_worlds_slots2.py --cases 1000 --mutations --only <16 rng families>` | 16,000 cases, 0 mismatches; 17/17 flicker mutants detected | 73.9 s |
| `validate_worlds_slots2` row, no mutants | 33 families, 33,000 cases, 0 mismatches | 19.1 s |
| `validate_particles` | 12 families, 407 cases, 0 mismatches (visual 39/39); visual negative controls caught | 0.8 s (cache) |
| `validate_worlds_after4`, no mutants | 9,181 cases, 0 mismatches | 9.4 s |
| `validate_render_effects16`, no mutants | 424 cases, 0 mismatches | 2.4 s |
| `run_test_suites.py reconstructed/objects reconstructed/particles` | 199 tests, 165 passed, 34 skipped (integration), 0 failures | 2.0 s |
| 45 native host modules (worlds_d..slots3, particles, icarus, render_light, map_effects, render_effects6, render_effects/9..16, anim, renderchar, effect, helpers, sprite_draw, inventory_skin, session_build), `MU_RECOVERY_INTEGRATION=1` | 44 OK; `test_render_effects11` 1 error, **pre-existing on main** (below) | 559 s |
| `audit_repository.py` | 0 rejected | 15 s |
| `make -j4` | pass | 15 s |

Validator selection: `--list-affected origin/main` selects ~70 rows through whole-library granularity
(`libclient_particles.dylib`, `reconstructed/objects`, `libmunative.a`). Dropped with evidence: the changed symbols
(`mu_obj_visual_flicker`, `mu_pt_object_visual`/`mu_pt_visual_host`, `mu_world_particles_object_visual`,
`visual_outer_rand`, `icarus_cover`) are referenced by no other script (`grep` over `scripts/`); the struct field
appended to `mu_pt_visual_host` changes no other function; the native rows (audio_*, session_party, app_polish1/4)
test audio, party adapters, the character shadow and UI, and app_polish1's source slices
(`mu_world_particles_character_shadow`, `apply_state`) are unchanged. Kept: slots2/3 (the predicate), particles
(VisualHost), worlds_after4 (the objects runtime), render_effects16 (compiles `mu_particles.c`).

**Pre-existing on main (not this lane):** `validate_render_effects11 --mutations` fails at mutant setup
("mark_abs: expected exactly one mutation site"): `reconstructed/combat/bow_fx.inc` has had three copies of
`t = 0.0f > t ? -t : t;` since #313 (RENDER-EFFECTS-016, `839497c2`). Identical on origin/main; the gate skips it
(`MU_RECOVERY_INTEGRATION=0`). Fix: anchor the mutant on more context.

**Fidelity** (default draw; final for this code): DATA-ACQ-002 32/32 byte-identical; October 22 tour 7/14 identical,
the 7 changed views explained by the RNG placement (control build reproduces "before" 14/14). Numbers in the finding
§4. Wall times before / after: DATA-ACQ-002 60 / 63 s, October 22 19 / 22 s, live clock 6/38/40/56 11 / 12 s.

## What's left

1. **Test Area 121's two slots** (custom `0x00d58bd8`, after `0x00d5a6cc`; slots stay 142/144). Needs: a slot event
   setting every mesh's per-vertex light (`0x06fd0918`, `MU_MODEL_LIGHTS`) after the transform and before the body
   draw; a port of the action pick `0x012affa4`; posed bones in the custom pass for 0x13..0x15 and CreateParticle to
   the existing consumer (refusals counted); the after slot (198 instructions). No capture, no warp. Outline in the
   finding §5.
2. **Devias 0x67's action pick `0x012affa4`** (the same routine): the Devias family compares those cases only up to
   the switch.
3. Unported inner draws after the outer one: the Kanturu hook `0x00e75089` past its flames (37/40), Blood Castle
   11..17/0x34 (`0x017fc023`), and occasional types in 9, 24, 30, 31, 33, 38, 39, 41, 42, 46, 51, 56, 98.
4. The `validate_render_effects11` mutant anchor above (RENDER-EFFECTS lanes).

Env for the validators:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_LANG_DIR=<mu-mac-tools>/native/scratch/render-worlds-after5/lang`.

Local files: none kept (scratch and renders deleted).
