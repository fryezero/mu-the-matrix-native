# RENDER-ITEMS-002Z

Branch `codex/render-items-002z`, based on `b7dfd2ed`; main `4480bf41` integrated at `f3c45e34` (earlier `4babc900` at `a9cc72d9`, `2b0b2716` at `bd417573`).
GPT-6.1 Sol, no subagents. Offline/static only. Research is
[part 40](../research/client-render-items.md#part-40-piecewise-colour-and-early-complete-bodies-render-items-002z).
The merge steward owns the full gate and merge.

## WIP

All 72 item-selected validator rows pass. The latest-main selector refreshes 22 rows at `f3c45e34`,
including four merge-only rows; all pass with zero failures, errors or skips. The rebuilt tree passes
in 12.82 s and the reduced private consumers pass 33/33 in 15.27 s. The final portable refresh passes 178 work items, 1,610 tests (1,306 passed / 304 skipped),
zero failures/errors, 518.82 s wrapper wall (445.7 s runner wall). Remaining: the genuine-main
default identity sweep. No ready entry has been written.

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
The initial native private selection is 160 work items, above the forty-item cap. This lane uses
**8d reduced** and runs the manual 6b consumers `test_native_renderchar` and `test_app_polish8` privately.

| Check | Result | Wall |
|---|---|---:|
| Complete pinned body extraction/table render | 1,461 rows, existing caps | 1,385.12 s |
| Complete owner-table regeneration | Pass | 10.10 s |
| Corrected portable renderchar suite | 133 tests, 104 passed / 29 private skips | 0.65 s |
| First integrated root build | Pass at `a9cc72d9` | 26.62 s |
| Early-body final instruction/compiled-mutant row at `bd417573` | 15,352 checks, zero mismatches; six mutants caught | 13.6 s |
| Cycle original comparisons and replacement threshold control | 6,936 checks, zero mismatches; threshold shift caught in five cases | 50.56 s |
| C-to-C admission delta versus genuine main `2b0b2716` | 216,448 states: 214,528 identical, 1,920 admissions on exactly fifteen types | 15.19 s |
| Full classifier export | 1,691 types / 798 shapes, exactly fifteen membership and nine shape changes | 118.03 s |
| Affected portable selection | 166/210 work items | 58.42 s |
| Final affected validator selection | 72/241 rows, one retained fallback, nine symbol-pruned rows | 69.37 s |
| Affected portable run at `9c541138` | 166 work items; 1,538 tests, 1,260 passed / 278 skipped, zero failures/errors | 433.24 s |
| Selected private validators | 72/72 passed, 1,043,690 recorded cases; per-row sources and times below | Per-row table below |
| Final portable refresh at `f3c45e34` | 178 work items, 1,610 tests; 1,306 passed / 304 skipped, zero failures/errors | 518.82 s |
| Latest integrated root build at `f3c45e34` | Pass, main `4480bf41` | 12.82 s |
| Latest private native consumers at `f3c45e34` | 33/33 passed, zero skips; 8d reduced | 15.27 s |
| Final item validator selection | 72/241 rows, unchanged set | 53.14 s |
| Latest-main validator selection since `4bb6348b` | 22/241 rows, including retained fallbacks | 64.47 s |
| Latest-main selected validator refresh at `f3c45e34` | 22/22 passed; 65,103 recorded cases plus gfx3's uncounted checks | 233.09 s |
| First integration portable refresh at `c7581b6c` | 173 work items, 1,793 tests; 1,471 passed / 322 skipped, zero failures/errors | 423.56 s |
| First integration private consumer refresh at `c7581b6c` | 33/33 passed, zero skips; 8d reduced | 14.03 s |
| Canonical private native consumers | 33/33 passed, zero skips; 8d reduced | 23.90 s |

Extraction/rendering wall excludes the cache's final save. These are finite recorded cases,
not a unique whole-client state count. The final affected validators are recorded below; only the default identity remains pending.

## Default identity provenance

Pending. Both sides will explicitly rebuild `native/build/mu-world`, with distinct SHA-256s,
default draw and fixed time on the 46 existing captures. No original-client pixel equivalence is claimed.

## Steward validators

The final item selector is exactly 72 rows, retaining `validate_movement` and pruning nine rows
with no changed symbol. The UI-main refresh selects 22 rows, including four merge-only rows.
The ready list is their **76-row union**, with all results covered below. Retained merge-selector
fallbacks (including the fixture IR guard) were run, not dropped.

Steward validators: validate_item_ranked,validate_item_continuation,validate_item_expansion,validate_item_clusters,validate_item_types,validate_fidelity,validate_meshdraw,validate_model_edge,validate_movement,validate_renderchar,validate_item_read_programs,validate_icarus_c2,validate_audio_callers,validate_item_gear,validate_item_next,validate_render_effects5,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_audio_domains,validate_audio_items,validate_item_coverage,validate_item_wings_next,validate_item_scalars,validate_item_chains,validate_item_carry,validate_item_quality,validate_item_product,validate_item_derived,validate_item_ownerfx,validate_item_predraw,validate_item_hiddenmesh,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_item_cloak,validate_armour_cloak,validate_render_effects22,validate_item_named,validate_npc_cloak,validate_render_effects23,validate_render_effects24,validate_render_effects27,validate_item_groups,validate_render_effects25,validate_actor_recipes,validate_item_helper_groups,validate_item_other_bodies,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_audio_objects,validate_render_effects28,validate_items_ui,validate_item_cycle,validate_item_direct_bodies,validate_audio_objects4,validate_actor_monsters,validate_app_polish7,validate_app_polish9,validate_gfx3,validate_map_polish

Use canonical private environment and `--private --no-mutants --cache --jobs 2`.
No steward mutants are requested. The 72 item rows total 1,043,690 recorded cases in overlapping
finite families. Carry ran at `3fed7878`; the other initial rows at `4bb6348b`. The merge refresh
updates eighteen of those results and adds four rows at `f3c45e34`, main through `4480bf41`.
The item generator, renderchar, record-math and pins inputs are unchanged across these main merges.
Per-row times are the runner's recorded `time.time` differences, including checkpoint pauses while
a row was active. Canonical regeneration was cold for carry and reused its original-side cache thereafter.
A dash means that row does not expose a case counter.

| Validator | Cases | Wall (s) | Tested source |
|---|---:|---:|---|
| `validate_item_ranked` | 17736 | 158.6 | `4bb6348b` |
| `validate_item_continuation` | 25772 | 212.1 | `4bb6348b` |
| `validate_item_expansion` | 52172 | 450.4 | `4bb6348b` |
| `validate_item_clusters` | 74292 | 530.2 | `4bb6348b` |
| `validate_item_types` | 135176 | 44.4 | `4bb6348b` |
| `validate_fidelity` | 991 | 70.1 | `4bb6348b` |
| `validate_meshdraw` | 14619 | 79.4 | `4bb6348b` |
| `validate_model_edge` | 954 | 159.6 | `4bb6348b` |
| `validate_movement` | 6614 | 84.5 | `f3c45e34` |
| `validate_renderchar` | 1706 | 38.7 | `4bb6348b` |
| `validate_item_read_programs` | 5352 | 18.7 | `4bb6348b` |
| `validate_icarus_c2` | 8400 | 12.7 | `4bb6348b` |
| `validate_audio_callers` | 5528 | 4.5 | `f3c45e34` |
| `validate_item_gear` | 25256 | 218.6 | `4bb6348b` |
| `validate_item_next` | 14992 | 273.1 | `4bb6348b` |
| `validate_render_effects5` | 1190 | 12.7 | `4bb6348b` |
| `validate_render_effects7` | 596 | 2.0 | `4bb6348b` |
| `validate_render_effects9` | 304 | 1.3 | `4bb6348b` |
| `validate_render_effects10` | 154 | 1.0 | `4bb6348b` |
| `validate_render_effects11` | 176 | 0.6 | `4bb6348b` |
| `validate_render_effects12` | 64 | 0.4 | `4bb6348b` |
| `validate_audio_domains` | 2544 | 25.9 | `f3c45e34` |
| `validate_audio_items` | 3000 | 2.5 | `f3c45e34` |
| `validate_item_coverage` | 31724 | 275.9 | `4bb6348b` |
| `validate_item_wings_next` | 33622 | 290.2 | `4bb6348b` |
| `validate_item_scalars` | 26274 | 250.0 | `4bb6348b` |
| `validate_item_chains` | 35406 | 358.8 | `4bb6348b` |
| `validate_item_carry` | 114388 | 2230.6 | `3fed7878` |
| `validate_item_quality` | 28080 | 268.4 | `4bb6348b` |
| `validate_item_product` | 2874 | 108.3 | `4bb6348b` |
| `validate_item_derived` | 36252 | 240.9 | `4bb6348b` |
| `validate_item_ownerfx` | 14964 | 164.8 | `4bb6348b` |
| `validate_item_predraw` | 42540 | 466.3 | `4bb6348b` |
| `validate_item_hiddenmesh` | 116281 | 592.8 | `4bb6348b` |
| `validate_app_polish1` | 752 | 18.5 | `f3c45e34` |
| `validate_app_polish2` | 1028 | 3.2 | `f3c45e34` |
| `validate_app_polish4` | 10485 | 37.3 | `f3c45e34` |
| `validate_render_effects13` | 180 | 0.4 | `4bb6348b` |
| `validate_render_effects14` | 660 | 1.8 | `4bb6348b` |
| `validate_render_effects15` | 509 | 1.4 | `4bb6348b` |
| `validate_render_effects16` | 424 | 2.2 | `f3c45e34` |
| `validate_worlds_fog` | 4044 | 8.9 | `f3c45e34` |
| `validate_render_effects17` | 618 | 8.4 | `f3c45e34` |
| `validate_item_callers` | 6013 | 1.6 | `4bb6348b` |
| `validate_inventory_fx` | 8017 | 11.0 | `4bb6348b` |
| `validate_render_effects18` | 540 | 1.2 | `4bb6348b` |
| `validate_render_effects19` | 400 | 1.1 | `4bb6348b` |
| `validate_render_effects20` | 148 | 0.2 | `4bb6348b` |
| `validate_render_effects21` | 267 | 0.3 | `4bb6348b` |
| `validate_item_cloak` | 5694 | 128.7 | `4bb6348b` |
| `validate_armour_cloak` | 4448 | 41.6 | `4bb6348b` |
| `validate_render_effects22` | 202 | 8.2 | `4bb6348b` |
| `validate_item_named` | 20057 | 220.6 | `4bb6348b` |
| `validate_npc_cloak` | 2619 | 56.8 | `4bb6348b` |
| `validate_render_effects23` | 1174 | 10.6 | `4bb6348b` |
| `validate_render_effects24` | 226 | 1.9 | `f3c45e34` |
| `validate_render_effects27` | 424 | 3.0 | `4bb6348b` |
| `validate_item_groups` | 4824 | 29.3 | `4bb6348b` |
| `validate_render_effects25` | 202 | 8.2 | `f3c45e34` |
| `validate_actor_recipes` | 1669 | 160.6 | `f3c45e34` |
| `validate_item_helper_groups` | 6432 | 37.5 | `4bb6348b` |
| `validate_item_other_bodies` | 24084 | 99.9 | `4bb6348b` |
| `validate_charsel_items` | 8817 | 6.8 | `4bb6348b` |
| `validate_render_effects26` | 348 | 9.6 | `f3c45e34` |
| `validate_actor_composites` | 1427 | 6.7 | `f3c45e34` |
| `validate_audio_objects` | 4000 | 2.3 | `f3c45e34` |
| `validate_render_effects28` | 630 | 1.4 | `4bb6348b` |
| `validate_items_ui` | 8517 | 9.7 | `4bb6348b` |
| `validate_item_cycle` | 6936 | 47.9 | `4bb6348b` |
| `validate_item_direct_bodies` | 15352 | 13.6 | `4bb6348b` |
| `validate_audio_objects4` | 10093 | 4.2 | `f3c45e34` |
| `validate_actor_monsters` | 1437 | 62.5 | `f3c45e34` |
| `validate_app_polish7` | 5120 | 1.9 | `f3c45e34` |
| `validate_app_polish9` | 4668 | 4.5 | `f3c45e34` |
| `validate_gfx3` | - | 5.4 | `f3c45e34` |
| `validate_map_polish` | 876 | 0.5 | `f3c45e34` |

## History and limits

The initial plain no-glow screen admits none of thirty candidates. Adding option/ancient states
reproduces the exact forty historical helper-count candidates, including ten tail-only mismatches
missed by the three-level diagnostic. All fourteen admissions belong to that cohort. Other multi-type
groups were screened largest first without admission. The ordinary-fit survey stopped partway and
is not claimed as a completed independent comparison of all other bodies; the broader early-body screen tests 118
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

The first main merge preserves both item validator additions and AUDIO-004's independent appended row.
Only the registry append conflicts; C sources merge cleanly. Main's compiled inputs are built and
all affected lane rows pass on the integrated branch. The final UI-main merge conflicts only in
the two status summaries; both lane entries are preserved. Its 22 selected rows pass separately.

These are finite instruction, draw-word, declared model-field, ordered request/refusal and scripted
random comparisons within declared contexts. Existing record, selected-item, buff, pose/bone,
invalid-context, absolute random/counter phase and consumer refusals remain. No pose/pixel or
whole-client equivalence is claimed. No original-client process, service, packet, protection,
character-power or installed-app work is involved.

All local reports, prototypes and render intermediates are disposable and will be removed at handoff,
with the worktree and build outputs. No new private input is needed by the next lane.

