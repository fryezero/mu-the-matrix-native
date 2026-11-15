# RENDER-ITEMS-002Z

Branch `codex/render-items-002z`, based on `b7dfd2ed`; main `4babc900` integrated at `a9cc72d9` (earlier `2b0b2716` at `bd417573`).
GPT-6.1 Sol, no subagents. Offline/static only. Research is
[part 40](../research/client-render-items.md#part-40-piecewise-colour-and-early-complete-bodies-render-items-002z).
The merge steward owns the full gate and merge.

## WIP

The focused admission checks below pass. The lane is not PR-ready: 70 of the initial 71 affected private validators and the genuine-main default identity sweep remain. The carry row passes, including canonical regeneration. The latest main is merged and its root build passes in 26.62 s; the selector is being refreshed.
Affected portable checks and 8d reduced pass. No ready entry has been written.

## Result

Bodies **1,465 -> 1,480 of 1,674**, leaving **194**, one read body and fourteen historical helper-count
bodies added. Skins remain 17/17; links remain eighteen targets/twenty-four types.
Remaining groups are **26 helper-count bodies and 168 others**. The
[194-row ledger](../research/item-body-refusals-002z.tsv) retains each type, group, source helper/draw
addresses, stopped fixture addresses and refusal reason. The denominator is unchanged.

`0x0b51` has an instruction-checked signed 6,000-tick piecewise scalar, including both colour
branches, their join and the following wave multiply. The fourteen early complete bodies are
`0x23f3`, `0x23fc`, `0x2493`, `0x24f7`, `0x24f8`, `0x271a`, `0x2725`, `0x27b8..0x27bb`,
`0x289f`, `0x28b0` and `0x28d7`. They preserve entry model fields, skip the ordinary glow/tail
chain and write back the final model fields. Three wings retain their exact-white whole-body
entry and part-selector-6 `(1, 0.1, 0.1)` mesh branch. Details and addresses are in part 40.

Complete pinned extraction emits 1,461 type rows and a 452,742-byte body header. The 24-scalar,
twelve-operation, sixteen-draw and 512-KiB audit limits are unchanged. The owner table is regenerated.
938 original exit probes establish the last-draw write-back; complete fitted rows are re-rendered
with exactly fourteen carry-bit changes. Final body-header SHA-256:
`1f6e3a9037bea129c41fde158b98ea1f213c71dff05c7f854aa87ddbedc310f5`.

The C-to-C sample changes exactly fifteen memberships, 128 states each, with no earlier change.
The classifier changes exactly fifteen memberships and nine shape totals, complete shapes
640 -> 649 of 798. Raw shapes, addresses, classifications and stopped-state summaries are unchanged.
The survey denominator 1,691 includes seventeen skins; the body denominator remains 1,674.

## Checks and environment

All tools/tests run from the repository root. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Heavy work uses nice 10, at most two validator
workers, and builds use `make -j2` after resource cooldowns exceeded twenty minutes. Memory remains
above the brief's floor. Cooldowns are outside the job timings. No full lane gate or hosted workflow ran.
The native private selection is 160 work items, above the forty-item cap. This lane uses
**8d reduced** and runs the manual 6b consumers `test_native_renderchar` and `test_app_polish8` privately.

| Check | Result | Wall |
|---|---|---:|
| Complete pinned body extraction/table render | 1,461 rows, existing caps | 1,385.12 s |
| Complete owner-table regeneration | Pass | 10.10 s |
| Corrected portable renderchar suite | 133 tests, 104 passed / 29 private skips | 0.65 s |
| Integrated root build | Pass, current merged C inputs | 26.29 s |
| Early-body final instruction/compiled-mutant row at `bd417573` | 15,352 checks, zero mismatches; six mutants caught | 13.6 s |
| Cycle original comparisons and replacement threshold control | 6,936 checks, zero mismatches; threshold shift caught in five cases | 50.56 s |
| C-to-C admission delta versus genuine main `2b0b2716` | 216,448 states: 214,528 identical, 1,920 admissions on exactly fifteen types | 15.19 s |
| Full classifier export | 1,691 types / 798 shapes, exactly fifteen membership and nine shape changes | 118.03 s |
| Affected portable selection | 166/210 work items | 58.42 s |
| Affected validator selection | 71/239 rows, one retained fallback, nine symbol-pruned rows | 52.70 s |
| Affected portable run at `9c541138` | 166 work items; 1,538 tests, 1,260 passed / 278 skipped, zero failures/errors | 433.24 s |
| Canonical private native consumers | 33/33 passed, zero skips; 8d reduced | 23.90 s |

Extraction/rendering wall excludes the cache's final save. These are finite recorded cases,
not a unique whole-client state count. The final affected checks are recorded below when complete.

## Default identity provenance

Pending. Both sides will explicitly rebuild `native/build/mu-world`, with distinct SHA-256s,
default draw and fixed time on the 46 existing captures. No original-client pixel equivalence is claimed.

## Steward validators

The exact selector list, including its retained `validate_movement` fallback, is:

Steward validators: validate_item_ranked,validate_item_continuation,validate_item_expansion,validate_item_clusters,validate_item_types,validate_fidelity,validate_meshdraw,validate_model_edge,validate_movement,validate_renderchar,validate_item_read_programs,validate_icarus_c2,validate_audio_callers,validate_item_gear,validate_item_next,validate_render_effects5,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_audio_domains,validate_audio_items,validate_item_coverage,validate_item_wings_next,validate_item_scalars,validate_item_chains,validate_item_carry,validate_item_quality,validate_item_product,validate_item_derived,validate_item_ownerfx,validate_item_predraw,validate_item_hiddenmesh,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_item_cloak,validate_armour_cloak,validate_render_effects22,validate_item_named,validate_npc_cloak,validate_render_effects23,validate_render_effects24,validate_render_effects27,validate_item_groups,validate_render_effects25,validate_actor_recipes,validate_item_helper_groups,validate_item_other_bodies,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_audio_objects,validate_render_effects28,validate_items_ui,validate_item_cycle,validate_item_direct_bodies,validate_audio_objects4

Use canonical private environment and `--private --no-mutants --cache --jobs 2`.
No steward mutants are requested. Per-row source commits, cases and wall times follow when the run completes.

## History and limits

The initial plain no-glow screen admits none of thirty candidates. Adding option/ancient states
reproduces the exact forty historical helper-count candidates, including ten tail-only mismatches
missed by the three-level diagnostic. All fourteen admissions belong to that cohort. All multi-type
other shapes and additional singleton hypotheses refuse; the broader early-body screen tests 118
clean candidates and adds only `0x2493` beyond the original thirteen, 488.39 s.
`0x23f4` and `0x2701` retain independent-state failures. `0x1710` and `0x10fd` stay excluded, and
the largest shield and armour candidates are still refused. No failed fit is promoted into an admission.

Directed white probes exposed a whole-body versus mesh entry that random non-white probes missed.
The fixed white/part-selector phases retain every earlier probe. A portable fixture's initial pure-red
expectation was corrected to the data constant `(1, 0.1, 0.1)` before admission checks.

The first cycle mutant aggregate fails solely because `<` versus `<=` at the half-period is
observationally equivalent for the captured continuous colour join. Six other compiled controls
are detected in that run. The equivalent control is discarded and replaced with a one-tick threshold
shift, which is detected. Only the replacement is compiled on the rerun; the six unchanged controls
are not repeated. Thus seven meaningful cycle controls and six early-body controls are caught.
The failed aggregate is not reported as a passing full mutant-row run. No tolerance, cap or runtime
branch is relaxed to kill a control. The final canonical validator retains all seven meaningful controls.

The main merge preserves both item validator additions and AUDIO-004's independent appended row.
Only the registry append conflicts; C sources merge cleanly. Main's compiled inputs are built and
all affected lane rows will run on the integrated branch.

These are finite instruction, draw-word, declared model-field, ordered request/refusal and scripted
random comparisons within declared contexts. Existing record, selected-item, buff, pose/bone,
invalid-context, absolute random/counter phase and consumer refusals remain. No pose/pixel or
whole-client equivalence is claimed. No original-client process, service, packet, protection,
character-power or installed-app work is involved.

All local reports, prototypes and render intermediates are disposable and will be removed at handoff,
with the worktree and build outputs. No new private input is needed by the next lane.


Checkpoint after the first affected-validator row: `validate_item_carry` passes 114,388 comparisons
and complete canonical table regeneration at `3fed7878`, 2,230.6 s. Its original cache was cold after
the final write-back metadata change. The wall includes a brief worker pause for the previous
audit/commit checkpoint. Later rows reuse that canonical cache. No checks or budgets were reduced.
Main through `4babc900` changes no renderchar, record-math, item generator or pins input, preserving
this row and the earlier focused proofs. Remaining rows will run on the integrated branch.
