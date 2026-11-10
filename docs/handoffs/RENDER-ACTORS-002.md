# RENDER-ACTORS-002

PR-ready. Branch `codex/render-actors-002`, base `a2ad8814`, with main `807d757c` merged (`80bd0c7f`).
Offline/static only. No installed app, live client or data was changed.

The lane's agent (Codex, GPT-6.1 Sol) implemented and verified the work, then stopped at Codex's usage limit with
only the last two checks and the delivery left. The orchestrator (Claude) ran those two checks at `d43a7649`
(reduced private tests and the default identity sweep, below) and wrote this final form. No source changed after
`d43a7649`.

## Result

Nine later player-model actor subtypes now draw as whole bodies: classes 372, 373, 503, 548, 616, 646, 706, 806
and 807. All are kind 1, class byte 0, level zero, with empty equipment. Their subtype files come from the pinned
startup AccessModel calls. The actor loader reuses OpenTexture's name map and the Item/Texture retry for missing
body textures.

Of RENDER-ACTORS-001's 15 unresolved subtype rows, nine are admitted and six stay refused:

| Classes | State | Reason |
|---|---|---|
| 372, 373, 503, 548, 616, 646, 706, 806, 807 | admitted | whole-body recipe verified against the original |
| 374, 642 | refused | need companion construction and lifetime |
| 378 | refused | needs its appearance/effect branch |
| 625, 626 | refused | need action-dependent hooks |
| 617 | refused | startup model file unresolved |

Actors are placed by authored fixtures only. Nothing here infers ordinary spawnability or event state.

## Checks

| Check | Result | Wall |
|---|---|---:|
| Build at `d43a7649` | pass | 13.4 s |
| `validate_actor_recipes`, full comparison with body-file identity | 1,300 checks, zero mismatches | 100.3 s |
| Actor mutants (`0bbf0da6`) | 21/21 controls caught: 20 in the full run (327.4 s), the valid-file `body_file` control in a targeted rerun (121.6 s) | |
| Affected validators at `bf75f44c` | 21/21 rows, zero skips | 521.9 s |
| Validator delta after ITEMS-002X main (`9aee9cfa`) | 15 rows pass, six unchanged by symbol selection | 329.3 s |
| Validator delta after AUDIO-002G main (`80bd0c7f`) | 18 rows pass | 376.1 s |
| Portable affected suites after ITEMS-002X main | 1,464 tests: 1,224 passed, 240 skipped, zero failures | 530.2 s |
| Portable affected suites after AUDIO-002G main | 1,518 tests: 1,271 passed, 247 skipped, zero failures | 418.7 s |
| Private, **8d reduced** (`test_actor_recipes`, `test_native_renderchar`), at `d43a7649` | 27/27, zero skips | 56.7 s |
| Default identity sweep at `d43a7649` | 46 maps: 92 PNGs, 92 dumps and 46 reports byte-identical to the baseline | 67.0 s |

8d is reduced because the selection has 154 work items, including 146 native modules (cap 40).
No actor implementation or mutation target changed in either main merge.

## Renders and byte identity

Nine isolated GL demos pass and were visually inspected by the lane; each gains 1,098..3,299 pixels against an
empty, names-hidden scene (19.3 s). The default sweep is unchanged: no default scene places these actors.

## Steward validators

Steward validators: validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_meshdraw, validate_model_edge, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_viewport_monsters, validate_worlds_fog

The 18 rows in the table pass at `80bd0c7f` (compiled source unchanged at `d43a7649`). The other three,
`validate_app_polish1`, `validate_audio_combat` and `validate_viewport_monsters`, pass at `bf75f44c` and were not
selected again: they use no symbol that either main merge changed. Only `validate_actor_recipes` needs mutants,
verified at `0bbf0da6`. Environment: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Wall at `80bd0c7f` |
|---|---:|
| `validate_actor_recipes` | 100.3 s |
| `validate_model_edge` | 133.9 s |
| `validate_meshdraw` | 86.9 s |
| `validate_movement` | 69.7 s |
| `validate_app_polish4` | 43.1 s |
| `validate_audio_domains` | 32.1 s |
| `validate_icarus_c2` | 28.1 s |
| `validate_worlds_fog` | 10.5 s |
| `validate_inventory_fx` | 10.1 s |
| `validate_render_effects17` | 9.8 s |
| `validate_audio_callers` | 7.3 s |
| `validate_audio_items` | 5.1 s |
| `validate_render_effects16` | 5.0 s |
| `validate_app_polish2` | 4.3 s |
| `validate_render_effects24` | 4.2 s |
| `validate_render_effects18` | 1.8 s |
| `validate_item_callers` | 1.7 s |
| `validate_render_effects19` | 1.3 s |

## Limits and next

- The six refused rows above need more than a plain body; do not admit them as plain bodies.
- Whole-client actor model coverage is still unknown; the census is ACTORS-001's bounded 32-row table.
- Next: companion construction/lifetime for 374 and 642, the appearance/effect branch for 378, action hooks for
  625/626, and 617's startup model file.

## Work log (lane checkpoints, in order)


Base `a2ad8814`, branch `codex/render-actors-002`. Offline/static only; no subagents.
Nine candidate kind-1, class-byte-0 whole-body recipes are implemented for classes
372, 373, 503, 548, 616, 646, 706, 806 and 807. All are level zero with empty equipment.
Their subtype files come from the pinned startup AccessModel calls. The actor loader
reuses OpenTexture's existing name-map and Item/Texture retry for missing body textures.

Done: binding brief and predecessor handoff read, baseline build and one-time default
scene hashes saved, portable census/recipe checks pass. The corrected private iteration
passes 565 checks in 56.0 s, including 32 native loads with zero missing body textures,
216 kind controls and six native refusals. Its small body-hook sample is 105 cases.
The first iteration's signed loader-number, event fixture and Item/Texture failures
are fixed. Final counts and mutants have not run.

The full affected private batch passes 21/21 rows, zero skips, in 521.9 s at
`bf75f44c`. Its actor row passes 1,300 checks in 145.3 s. Nine isolated GL demos
pass and were visually inspected; each gains 1,098..3,299 pixels against an empty,
names-hidden scene. Rendering takes 19.3 s. Latest main brought documentation only.

Left: portable affected suites, private native tests under the 8d cost cap,
final identity sweep, final self-review and PR-ready delivery.
No ready entry has been written.

Mutant audit: the first full run passed all 1,300 positive checks and caught 20/21
controls in 327.4 s. The valid-file `body_file` mutation escaped because the native
host only checked mesh presence. The host now reports the body file actually loaded,
and the comparison checks its exact startup-derived identity. The same wrong-but-valid
file mutation is retained for a targeted rerun; no production runtime code changed.
The portable recipe test also checks independent expected constructor model IDs.
The full positive recheck now passes 1,300 checks and catches the valid-file mutant
in 121.6 s at `0bbf0da6`. All 21 controls are therefore verified across the full
run and the targeted rerun. The other 20 controls were not repeated.

Latest main's ITEMS-002X tables are integrated as `9aee9cfa`. Rebuild passes in
15.7 s. Fresh selection still has 21 lane validators; the merge delta selects 15,
which pass without mutants in 329.3 s. The other six are unchanged by symbol-level
selection and retain their earlier result. Portable affected suites are running.
Selection has 154 work items including 146 native modules, so 8d is reduced.

Portable affected checks pass 1,464 tests: 1,224 passed, 240 skipped, zero failures
or errors, 530.2 s. Private 8d reduced passes all 27 tests in the actor recipe and
native renderchar modules, zero skips, 43.3 s.

The final integration point is AUDIO-002G main `807d757c`, merged as `80bd0c7f`.
Rebuild passes in 13.4 s. Fresh lane selection remains 21 rows; 18 changed-input
rows pass in 376.1 s, including the full actor comparison with file identity.
The final portable delta is running. No actor implementation or mutation target
changed in that merge.

Next: finish the portable run, the reduced private modules and the final sweep.
Six other rows stay refused: 374 and 642 need companion construction/lifetime;
378 needs its appearance/effect branch; 625/626 need action-dependent hooks; 617's
startup model file is unresolved. Do not admit these as plain bodies.

Local reports and baseline hashes are in
`~/Documents/MTM/mu-mac-tools/native/scratch/render-actors-002/`.
No installed app or data was changed. Temporary outputs are removed at PR-ready.
