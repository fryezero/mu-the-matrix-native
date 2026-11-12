# MUUN-VISUAL-003

Work in progress on `codex/muun-visual-003`, from main `626abce1`. Offline/static only.
No installed-app, live client, service, packet, protection, actor, item table or particle-consumer edits.

## What draws

Focused comparisons and native tests pass; finish checks are pending. The explicit kind-1 mount fixture loads an independent secondary
skeleton for render-info ids 16/17/100..105. It uses the recovered model-header lookup, scales, action map,
speeds, owner position/angle and named-bone attachment offset. The existing fifteen attachment appearances
and their eight extra mesh rows are unchanged. The other ten appearances have no additional rows.

## WIP

Done: read both binding briefs and the 001/002 handoffs; created the assigned worktree; built the baseline;
re-audited installed mesh rows; traced secondary construction, action mapping, speed, render gates and
attachment; wrote the implementation, instruction comparator and native fixture tests.

Checked: new native target builds under `-Werror`, 4.63 s; private secondary module 4/4 tests, 16.73 s;
873 original cases, zero mismatches; 16/16 compiled mutants caught under `-Werror`, 7.10 s. All eight real
secondary skeletons have their named bone, actions 0/2/4 and zero missing textures. GL and software pixel
differences pass. Default before sweeps complete: fourteen views 30.31 s, thirty-two views 59.46 s.
The original comparison caught and corrected the initial WolfA run-speed error. Two validator-stub stack
cleanup errors were corrected before the successful run. Historical baseline manifests had stale paths;
those failed before rendering and were replaced with the current fourteen-view manifest.

Left: retained native proof renders, affected checks, after identity sweep, audit and final-main integration.
Shared-host load caused waits. One probe/test batch started before its high-load output was inspected; subsequent probes and heavy
launches are separate.

Next step: finish the running 157-item affected portable batch, then both Muun private modules, retained
proofs and the after identity sweep. No further unchanged mutant rerun.
The repository audit passes with 2,225 staged files, zero rejected, 16.35 s. Root build passes in 10.53 s.
All 30 affected private validators pass at `a03c51e0`, 562.05 s including selection, no skipped rows. Keep the 02:15 WIP and 02:30 stop deadlines.

## Limits and next

Hero rider placement, model-specific secondary effects, owner-kind-2 fade, buff-0x12 render mode and remote
transitions are not implemented. Production selection, inventory, bonuses, damage, commands and network
feeds remain excluded. No claim of complete kind-1 or full-scene equivalence.

## Checkpoints and cleanup

Local scratch and renders are under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-003`.
The first checkpoint is `a03c51e0`; its code is the frozen input of the successful 30-row validator batch.
This second WIP checkpoint changes documentation only. The 157-item portable batch is running; remaining
steps are the focused private regression, retained proofs, after sweep, final-main check and PR preparation.
Portable selection: 157 work items, 82.37 s. **8d reduced:** this exceeds forty; both direct Muun modules
will run privately, while all 157 portable items are retained. No future-lane input has been created.
Keep only needed resume inputs if stopped WIP; remove generated
outputs, worktree and local branch after the ready queue entry on successful delivery.


## Steward validators

Steward validators: validate_actor_recipes, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_objects, validate_charsel_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_muun_secondary, validate_path, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects28, validate_session_party, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_worlds_f

All rows pass at `a03c51e03eb5a42eb0708fc7ff3a34ba9ed4ad80`. No steward mutant rerun is needed;
the new row's sixteen mutants compiled and were caught once. The canonical private environment supplies
MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR and row-specific inputs.

| Validator | Reported cases | Wall |
|---|---:|---:|
| `validate_actor_recipes` | 1,669 | 123.6 s |
| `validate_audio_callers` | 5,528 | 4.8 s |
| `validate_audio_charsel` | 5,968 | 4.5 s |
| `validate_audio_combat` | 19,548 | 28.2 s |
| `validate_audio_domains` | 2,544 | 27.4 s |
| `validate_audio_items` | 3,000 | 4.7 s |
| `validate_audio_objects` | 4,000 | 3.7 s |
| `validate_charsel_items` | 8,817 | 7.8 s |
| `validate_icarus_c2` | 8,400 | 16.0 s |
| `validate_inventory_fx` | 8,017 | 10.6 s |
| `validate_item_callers` | 6,013 | 1.4 s |
| `validate_items_ui` | 8,517 | 15.7 s |
| `validate_meshdraw` | 14,619 | 61.0 s |
| `validate_model_edge` | 954 | 132.4 s |
| `validate_model_light` | 1,433 | 7.0 s |
| `validate_movement` | 6,614 | 62.6 s |
| `validate_muun_secondary` | 873 | 0.6 s |
| `validate_path` | 4,719 | 30.6 s |
| `validate_render_effects16` | 424 | 4.1 s |
| `validate_render_effects17` | 618 | 9.4 s |
| `validate_render_effects18` | 540 | 1.7 s |
| `validate_render_effects19` | 400 | 1.1 s |
| `validate_render_effects24` | 226 | 2.9 s |
| `validate_render_effects25` | 202 | 10.0 s |
| `validate_render_effects28` | 630 | 1.8 s |
| `validate_session_party` | 200 | 0.8 s |
| `validate_terrain` | 583,500 | 402.9 s |
| `validate_terrain_remaining` | 2,147 | 4.0 s |
| `validate_viewport_monsters` | 1,963 | 11.1 s |
| `validate_worlds_f` | 1,818 | 0.4 s |

Total reported row cases: 703,901.
