# RENDER-EFFECTS-006

The effect requests the world lanes N–R2 refused and counted are consumed. [Finding, addresses, limits](../research/client-render-effects-006.md).

- Claude Opus 5.5 lane. Branch `claude/render-effects-006`, worktree `~/Documents/MTM/worktrees/render-effects-006`, from
  origin/main `f4eba8a`, merged with `e725bb9` (RENDER-WORLDS-Q, R, R2, GATE-PAR-001) and the later main recorded
  below. Input links `tools/python` and `evidence` from the main checkout, never staged.
- Owned: `reconstructed/particles/world_owned_fx.inc`, `scripts/validate_render_effects6.py`,
  `native/tests/{render_effects6_host.c,test_native_render_effects6.py}`, this handoff and the finding.
- Minimal shared lines: the three kinds in `reconstructed/combat/skill_fx.{c,h}` (+ `field_cc`), `mu_jt_object.scale`
  in `reconstructed/joints/joints.h`; the kind/create/move/render dispatch lines in `reconstructed/particles/particles.c`;
  `effect_word4` and the four `ein_*` hooks in `native/core/mu_objects.h`, their uses in `mu_objects_runtime.c`
  (`owned_effect`, the two refusal loops, the per-frame update after RenderObjectVisual) and `mu_objects_worlds_p.c`
  (the 0xb5 request/attach); in `native/core/mu_particles.{c,h}` the hooks, owner scale, four effect models and the
  objects' EffectManager scene; `mu_effect_scene_template` / `mu_effect_scene_update_one` in `mu_effect_scene.{c,h}`;
  the scene's draw and an `"ein"` report line in `native/world/parts/particles.c`; validator harness: owner scale and
  `+0xcc` in `validate_skill_fx.py`, the sprite-less render record in `validate_particles.py`; Makefile/registry rows.

## Kinds consumed and refused counts (native host, 400 steps per world)

| Request | Worlds (types) | Before → after |
|---|---|---|
| CreateEffect 0x59a/3 | 91 (57), 122 (83), 135 (0xa5) | 3 → 0, 87 → 0 (with 176's 0x199), 135: pool-unsupported → 9 created |
| CreateEffect 0x199/0, /1 | 122 (176), 134 (0x46), 142 (196), 144 (185, /1) | 70 → 0, 7 → 0, 4 → 0 |
| CreateEffect 0x195/0 | 123 (161), 143 (161) | 5 → 0, 5 → 0 |
| Particles 0x7ef7/9, 0x7f25/15, 0x7efa/2, 0x7f26/14 | the effects above, 135 type 15 | particle module `unsupported` 0 |
| `.ein` x4 (EffectManager) | 136 (0xb5) | one refusal per step → 0; 4 instances attached once (files present); without files still refused each step |

## Checks

- `validate_render_effects6 --cases 200 --particle-cases 200 --mutations`: **1,000 instruction cases, zero mismatches,
  34/34 compiled mutants** (400/400 run: 2,000 cases, zero mismatches).
- Private validators rerun after the shared edits: validate_render_effects (002), 3, 4, 5, 6, validate_skill_fx,
  validate_particles, validate_combat, validate_joints, validate_world_particle_consumers, validate_worlds_m,
  validate_worlds_p, validate_icarus_c2, validate_item_effects, validate_render_worlds_a, validate_worlds_d,
  validate_worlds_l, validate_helpers, validate_pets, validate_charsel_world: all pass (one fix on the way:
  effects-002's mutant anchor `e->lifetime = 50;` became ambiguous; the shoal now writes it through a named constant).
- Native: `test_native_render_effects6` (portable host), and the P, Q, R, R2, N world hosts, `test_render_effects`,
  `test_native_effect`, `test_particles`, `test_skill_fx`, `test_world_parts` unchanged and passing.

## Frames (installed data, local, deleted)

World 136 at tile (104, 70): the four red effects burn on the ballista's bolt head (bone 20) while it glows
(frames 146, 243: 4,872 / 6,079 pixels from the scene pass), none at rest (frame 39).

The twelve DATA-ACQ-002 arrival tiles (91, 122, 123, 131–136, 142–144), 150 drawn steps each: effects/particles
unsupported 0 everywhere. Acheron: 4 sea leaves created and live, 960 particles (their sparks among them; the
leaves had drifted out of view by the last frame). Old Kethotum: 70 particles (type 15). Twisted Karutan: 435
particles. No requester of the consumed kinds is drawn at the other arrival tiles (0 created), and 136's
arrival does not show a 0xb5, so its frame there is unchanged; the ballista frames above come from tile (104, 70).

## Intended render changes

Worlds 91, 122, 123, 134, 135, 136, 142, 143, 144 now show the consumed effects (sea-leaf glints and sparks, the
shoals' flare trails, bats in Kubera, the ballista's fire); no other world's output changes.

## Remaining

Bone −1 attach (`0x0129faee`) and the per-map / Muun EffectManager tables (`0x0183067e`, `0x0114203d`; in 136 they
carry effects on types 123 and 160–166); Unicorn comparison of `0x0129f671`/`0x0129fd4f`; a live check of the
0xb5 effects (needs a capture with a 0xb5 in view and charging).

No original client or launcher was started. No service, wire, protection or item work. Only authored source,
synthetic fixtures and reviewed summaries are committed. Local outputs `native/scratch/render-effects-006` and
renders are deleted at cleanup; no new local input needs retention. DATA-ACQ-002 inputs were only read.
