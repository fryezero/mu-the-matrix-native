# MUUN-VISUAL-001

PR-ready. Branch `codex/muun-visual-001`, from main `9d6ce467`, with main `4d92d77f` merged at `6c1b1621`.
Offline/static only; no original client, protection code, network work, installed-app change or proprietary data commits.

The dedicated reconstructed base slot and native fixture model/effect owner now draw an authored Muun beside
the demo hero. `MU_MUUN_FIXTURE=363` in `mu-world` selects an appearance record only. Its model, two attachments,
90 updates per attachment and eight drawn vertices are visible in the local 960x600 GL proof at Lorencia 128,124.
The body-only control uses an absent table; the existing verified effect consumer is unchanged.
[Addresses and scope](../research/client-muun.md).

Checked so far: 912 original instruction cases, zero mismatches; canonical private Muun host, 3 tests,
2.44 s, all 15 actual model codes and all 16 attachments, with exact matrices and ownership controls;
new world render test, 1 test, 2.63 s, visible model and attachment pixel difference. Latest full build 13.78 s,
GL world target 3.41 s (the subsequent frustum fix also compiled). One-time default baselines: October 22
22.60 s, DATA-ACQ-002 58.55 s, 640x400, no draw-all/live-time.

The lane's agent (Codex, GPT-6.1 Sol) did the implementation and the checks, then stopped at Codex's usage limit
during its mutant run. The orchestrator (Claude) made one validator fix (below), merged main `4d92d77f`
(`native/Makefile` and `scripts/validators.toml` conflicts: both sides kept), reran the mutant row, finished this
handoff, added the status lines and opened the PR.

## Final checks

| Check | Result | Wall |
|---|---|---:|
| `validate_muun_visual` with mutants, at `6c1b1621` | 912 original instruction cases, zero mismatches; 18/18 compiled mutants caught | 10.2 s |
| Affected portable suites (lane, at `c4ecfcfc`) | 1,638 tests: 1,367 passed, 271 skipped, zero failures/errors | 409.8 s |
| Affected private validators (lane, at `c4ecfcfc`) | 54/54 rows pass | 995.4 s |
| Private Muun host | 3 tests: all 15 model codes, all 16 attachments, exact matrices, ownership controls | 2.44 s |
| World render test | 1 test: visible model and attachment pixel difference | 2.63 s |

Validator fix: the `follow_height` mutant removed `+ info->offset[2]`, which left `mu_mv_follow`'s `info`
parameter unused, so the mutant did not compile under `-Werror` and the lane's first mutant run stopped with a
build error (no mutant result). The mutant now flips the offset's sign (`- info->offset[2]`): still a wrong
follow height, and it compiles and is caught. No production code changed.

The default identity sweep and the affected validators after the last main merge are the merge steward's
combined-tree run (steward log, batch 101), where the sweep's before and after binaries are both rebuilt.

**8d reduced:** the affected native selection exceeds 40 items; the private run covers this lane's Muun host,
its world render test and the shared renderer module.

## Steward validators

Steward validators: validate_item_effects, validate_meshdraw, validate_model_edge, validate_model_light, validate_mount_visuals, validate_helpers, validate_movement, validate_path, validate_pets, validate_raven, validate_viewport_monsters, validate_terrain_remaining, validate_icarus_c2, validate_worlds_f, validate_audio_callers, validate_audio_combat, validate_render_effects, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_world_particle_consumers, validate_audio_domains, validate_audio_items, validate_worlds_l, validate_session_party, validate_audio_charsel, validate_worlds_m, validate_render_effects13, validate_render_effects14, validate_worlds_slots3, validate_worlds_121, validate_worlds_raklion, validate_worlds_karutan, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_item_callers, validate_inventory_fx, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects22, validate_render_effects23, validate_render_effects24, validate_actor_recipes, validate_muun_visual, validate_terrain

These 54 rows pass at `c4ecfcfc` (995.4 s in total, without mutants). Only `validate_muun_visual` has
changed mutants; they pass 18/18 at `6c1b1621`. Environment: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

## Limits

Base body/pose/follow and fixture lifetime only. Auxiliary attack/command classes, additional model/mesh
passes and production Muun selection remain excluded. The fixture RNG has its own deterministic phase.
No original screenshot or live-motion equivalence is claimed. Missing, dummy and out-of-range bones remain refused.
