# RENDER-EFFECTS-035

WIP, not PR-ready. Branch `claude/render-effects-035` starts at main `bb86bbf7` (PR #406, steward
batch 120, EFFECTS-033 included). No subagents, no full lane gate.

## WIP

Done:
- First deliverable: the 37 catalogue rows are classified by step body, end bodies, receive slice,
  ordered requests, services and consumer availability. Tool `scripts/skill_catalogue_census.py`,
  tables `docs/research/skill-catalogue-classification.csv` and
  `docs/research/skill-catalogue-missing-consumers.csv` (39 ids, for the consumer lane), note
  `docs/research/client-render-effects-035.md`.
- Group sizes: A caster-frame 8, B bone-frame buff 3, C triple storm 6, D heal family 4,
  E existing end body 3, F arrows 4, G own step or end body 5, H mount context 2, I no receive
  case 2. 27 rows use the default step and both default ends.
- `mu_sfx_effect_kind_supported` exported from `reconstructed/combat/skill_fx.c` (read-only
  predicate used by the census).

Left:
- Request-side admission of the uniform groups (A, E, B, C, D in that order) in
  `reconstructed/combat/demo_skill_fx.c` with one verifier `scripts/validate_render_effects35.py`,
  compiled mutants, native adapter in `native/core/mu_combat.c`, fixture tests and renders.
- Second group: the general equipment-link selector for 43 Death Stab and auras 27/28.
- Research note, handoff, status lines, checks per TEST BUDGET, identity sweep, PR.

Next step: recover the group A and E slices under the strict machine (entry at the case body with
an authored frame, exits `0x0125c47c` / `0x01260e1d` stubbed as in `validate_render_effects32.py`)
and write the table-driven planner.
