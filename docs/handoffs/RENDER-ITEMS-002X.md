# RENDER-ITEMS-002X

Branch `codex/render-items-002x`, from prerequisite main `54a53e1a` after #360. Main `ff8e0543` is merged at
`b4a95ec3`; actor main `a2ad8814` is merged at `31e03afb`; the later `9d6ce467` merge is docs-only.
Codex, GPT-6.1 Sol; no subagents. Research is [part 36](../research/client-render-items.md#part-36-carried-fields-alpha-products-and-no-glow-bodies-render-items-002x).
Offline/static only. No full lane gate. Installed Native Preview and Wine apps are untouched.

## Result

Bodies **1,404 -> 1,424 of 1,674**, leaving **250**. Skins stay 17/17; links stay eighteen targets/twenty-four types.
Fourteen of the 21 read-program candidates and six of the historical 54 helper-count types are admitted.
Recipe rows 1,385 -> 1,405. Both complete tables are generated from pinned instruction extraction:
`item_bodies.h` is 482,415 bytes and `item_owner_fx.h` is 262,949 bytes, below the audit limit. Public ABI,
scalar storage and operation caps are unchanged.

Read-program types: `0x0b29`, `0x0b52`, `0x0f1e`, `0x174a`, `0x2301`, `0x2302`, `0x23a8`, `0x23a9`,
`0x23ed`, `0x23ee`, `0x23fe`, `0x23ff`, `0x2403`, `0x2404`. Extended probes, nested-range random attribution
and, except the two swords, carried model fields preserve the exact binary32 scalar/product draw words.
All fourteen complete owned pre-programs also pass their ordered stream and random-consumption comparisons.

No-glow types: `0x232c..0x2330` and `0x26f5`. They bypass the ordinary level-glow helper chain, including fixture
records with kind B `0x26/0x5b`. The new validator explicitly enumerates kind A 0/6, all sixteen levels,
qualities 0/1/2/9 and both tail settings, with independent random sequences. Original inputs remain unmodified.

The survey export now uses `gen.ALL_TYPES`; a portable test compares exported membership with native
`mu_rc_item_special` over all 1,691 surveyed types. Exactly twenty memberships and nine shape totals change;
complete shapes 600 -> 609 of 798. Raw shapes, addresses, classifications and stopped states are unchanged.
A failed probe now clears derived-phase state, preventing a previous type's scalar width from leaking into a
later refusal. The portable regression fails before the fix and passes after it. Rejected helper prototypes
are removed; none of the four largest other groups screened adds a body. No comparison was relaxed.

## Checks

Every test/tool command runs from the repository root. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`, including `MU_SECTION3`, `MU_GAME_ROOT`, `MU_EVIDENCE_DIR`,
`MU_NATIVE_DATA_DIR` and the pinned inputs. Heavy commands use nice 10, make at most four jobs and validator
runners two workers. Load/memory/disk guards precede steps; load above 14 caused the required cooldowns.

| Check | Result | Wall |
|---|---|---:|
| Initial root build / world build | Pass | 28.71 / 4.06 s |
| Read-program screen | 14/21 pass, 292 body states each, zero mismatches | 353.33 s |
| Owned-program screen | 14 x 64 states, 896 total; exact draws/requests/refusals and random consumption | 6.58 s |
| No-glow screen | 6/23 pass, 292 body states each, zero mismatches | 50.60 s |
| Consecutive-helper experiments | No admissions; prototypes removed | 120.71 / 168.11 s |
| Largest other-group screen / corrected tail | No admissions; failed stale phase is fixed and types refuse normally | 210.20 / 13.16 s |
| Stale-phase regression before / after | Fails before, passes after | 0.10 / 0.08 s |
| Complete body and owner table generation | Pass; later validators reproduce both tables | 868.00 s |
| Root build after generation | Pass | 9.23 s |
| C-to-C against saved prerequisite-main library | 216,448 states, 213,888 identical; exactly twenty intended types change, 128 states each | 6.10 s |
| Full survey | 1,691 types / 798 shapes; only intended membership/totals change | 67.17 s |
| Targeted portable / export regression | 18 tests, 16 passed, two private skips / three tests passed, one private skip | 0.17 / 0.10 s |
| Resume root build / actor-merge build | Pass | 27.24 / 24.37 s |
| Corrected portable renderchar suite | 111 tests, 87 passed, 24 private skips | 1.32 s |
| Initial affected portable run | 145 items; 1,376 tests, 1,146 passed, 230 skips, zero failures/errors | 349.78 s including selection; 303.3 s runner wall |
| Initial canonical private renderer | 23/23 pass, zero skips | 7.95 s |
| Validator-fix portable renderchar suite | 111 tests, 87 passed, 24 private skips | 0.89 s |
| Post-merge affected portable run | 154 items; 1,464 tests, 1,223 passed, 241 skips, zero failures/errors | 387.00 s including selection; 320.9 s runner wall |
| Final canonical private renderer and actor modules | 27/27 pass, zero skips | 50.51 s |
| Final world build | Pass | 0.28 s |
| Final staged-source audit | 2,142 files, zero rejected | 28.68 s |

The initial interrupted run is superseded by these completed runs. No passing aggregate is attributed to the
owner-stopped run. Its stale refusal example now uses still-unadmitted `0x230d` instead of newly admitted `0x2301`.
Brief 6b review finds consumers of the changed type lists in the renderchar suite and `test_app_polish8`; both
are included in the completed portable selection. No existing struct layout or scalar cap changes.
**8d reduced:** initial 140 and post-merge 146 native work items exceed 40. The private passes cover the lane's
changed renderer module, then renderer plus the actor module added by main. Private instruction rows run via
the validator runner. The steward owns the full combined gate.

### Validator results and steward selection

Fifty unchanged rows pass at compiled source `b4a95ec3`: **884,297 row checks**, **2,172.67 s elapsed**,
4,343.5 s aggregate row wall. The fourteen-program pre-draw expansion passes **42,540 cases**, zero mismatches,
**49/49 mutants**, 391.7 s. Its manifest total was correct but two old family counts remained; they now state
19,856 body and 4,288 owned states. Saved-report recheck passes in 0.07 s without rebuilding mutants.

The first no-glow run passes 3,288 comparisons and catches both mutants but fails the declared 4,824 count,
24.5 s. Kind A had been sampled; the corrected loop enumerates 0/6. The corrected row passes **4,824 cases**
and **2/2 mutants**, 27.1 s at `31e03afb`. This targeted rerun follows the check change; expected totals and
comparison strictness are preserved. The 49 pre-draw mutants are not repeated.

After the actor merge, **21 rows / 96,078 comparisons** pass without mutants at **`31e03afb`**, **238.21 s**.
The since-merge selector retains movement, audio-combat and effects17 fallbacks and prunes ten unused-symbol
rows. Final PR selection is **53 rows / 932,022 row checks**, including the actor row. Its only fallback
is movement; nine unused-symbol rows are pruned. Selection walls: initial 42.32 s, merge 63.65 s, final 53.94 s.
The later main merge and final handoff changes are docs-only, so no compiled-input rerun follows them.

Initial walls below are at `b4a95ec3`, except pre-draw's completed run at `f2755712` and the corrected group row
at `31e03afb`. Merge walls are at `31e03afb`. All final rows pass. **No steward mutants requested**;
49 + 2 changed-row mutants are complete. Reuse rows whose inputs have not changed per TEST BUDGET 8.

| Steward validator | Cases | Initial s | Merge s | Lane mutants |
|---|---:|---:|---:|---|
| `validate_item_ranked` | 17,736 | 128.7 | - | - |
| `validate_item_continuation` | 25,772 | 171.7 | - | - |
| `validate_item_expansion` | 52,172 | 271.2 | - | - |
| `validate_item_clusters` | 74,292 | 322.1 | - | - |
| `validate_item_types` | 135,176 | 31.2 | - | - |
| `validate_fidelity` | 991 | 55.7 | - | - |
| `validate_meshdraw` | 14,619 | 58.7 | 53.7 | - |
| `validate_model_edge` | 954 | 117.2 | 114.0 | - |
| `validate_movement` | 6,614 | 54.2 | 56.8 | - |
| `validate_renderchar` | 1,706 | 58.2 | - | - |
| `validate_icarus_c2` | 8,400 | 27.0 | 19.5 | - |
| `validate_audio_callers` | 5,528 | 6.0 | 5.9 | - |
| `validate_item_gear` | 25,256 | 169.6 | - | - |
| `validate_item_next` | 14,992 | 194.6 | - | - |
| `validate_render_effects5` | 1,190 | 3.2 | - | - |
| `validate_render_effects7` | 596 | 1.2 | - | - |
| `validate_render_effects9` | 304 | 0.7 | - | - |
| `validate_render_effects10` | 154 | 0.3 | - | - |
| `validate_render_effects11` | 176 | 0.2 | - | - |
| `validate_render_effects12` | 64 | 0.2 | - | - |
| `validate_audio_domains` | 2,544 | 18.6 | 23.9 | - |
| `validate_audio_items` | 3,000 | 2.3 | 5.3 | - |
| `validate_item_coverage` | 31,724 | 177.9 | - | - |
| `validate_item_wings_next` | 33,622 | 193.9 | - | - |
| `validate_item_scalars` | 26,274 | 161.8 | - | - |
| `validate_item_chains` | 35,406 | 232.0 | - | - |
| `validate_item_carry` | 114,388 | 586.0 | - | - |
| `validate_item_quality` | 28,080 | 153.4 | - | - |
| `validate_item_product` | 2,874 | 57.8 | - | - |
| `validate_item_derived` | 36,252 | 257.4 | - | - |
| `validate_item_ownerfx` | 14,964 | 119.6 | - | - |
| `validate_item_predraw` | 42,540 | 391.7 | - | 49/49 |
| `validate_item_hiddenmesh` | 116,281 | 376.7 | - | - |
| `validate_render_effects13` | 180 | 0.4 | - | - |
| `validate_render_effects14` | 660 | 0.9 | - | - |
| `validate_render_effects15` | 509 | 0.6 | - | - |
| `validate_render_effects16` | 424 | 3.3 | 3.2 | - |
| `validate_render_effects17` | 618 | 7.2 | 7.4 | - |
| `validate_item_callers` | 6,013 | 1.2 | 1.7 | - |
| `validate_inventory_fx` | 8,017 | 6.6 | 7.3 | - |
| `validate_render_effects18` | 540 | 0.9 | 2.5 | - |
| `validate_render_effects19` | 400 | 0.8 | 1.6 | - |
| `validate_render_effects20` | 148 | 0.2 | - | - |
| `validate_render_effects21` | 267 | 0.3 | - | - |
| `validate_item_cloak` | 5,694 | 126.7 | - | - |
| `validate_armour_cloak` | 4,448 | 36.3 | - | - |
| `validate_render_effects22` | 202 | 4.9 | - | - |
| `validate_item_named` | 20,057 | 108.5 | - | - |
| `validate_npc_cloak` | 2,619 | 26.0 | - | - |
| `validate_render_effects23` | 1,174 | 7.0 | - | - |
| `validate_render_effects24` | 226 | 2.4 | 2.7 | - |
| `validate_item_groups` | 4,824 | 27.1 | - | 2/2 |
| `validate_actor_recipes` | 361 | - | 37.8 | - |

Steward validators: validate_item_ranked, validate_item_continuation, validate_item_expansion, validate_item_clusters, validate_item_types, validate_fidelity, validate_meshdraw, validate_model_edge, validate_movement, validate_renderchar, validate_icarus_c2, validate_audio_callers, validate_item_gear, validate_item_next, validate_render_effects5, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_audio_domains, validate_audio_items, validate_item_coverage, validate_item_wings_next, validate_item_scalars, validate_item_chains, validate_item_carry, validate_item_quality, validate_item_product, validate_item_derived, validate_item_ownerfx, validate_item_predraw, validate_item_hiddenmesh, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_item_callers, validate_inventory_fx, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_item_cloak, validate_armour_cloak, validate_render_effects22, validate_item_named, validate_npc_cloak, validate_render_effects23, validate_render_effects24, validate_item_groups, validate_actor_recipes.

### Merge-only rows

These are required by the late-main merge but are outside the final PR selection. All pass without mutants at
`31e03afb`. They do not expand the ready-prs validator list.

| Merge-only validator | Cases | Wall s |
|---|---:|---:|
| `validate_app_polish1` | 752 | 28.7 |
| `validate_app_polish2` | 1,028 | 3.8 |
| `validate_app_polish4` | 10,485 | 32.1 |
| `validate_audio_combat` | 19,548 | 45.1 |
| `validate_viewport_monsters` | 1,963 | 15.1 |
| `validate_worlds_fog` | 4,044 | 6.6 |

## Default-draw identity

The baseline was taken once from prerequisite main: 46 maps, 92 PNGs, 92 dumps and 46 reports, 62.18 s.
The single final sweep uses the retained hashes, current merged source, default draws and fixed time.
**92/92 PNGs, 92/92 dumps and 46/46 normalized reports are byte-identical**, 61.57 s. No changed hashes.
No draw_all or new live-time capture is used. The C-to-C item-library inputs did not change after `cdfbcb3f`,
so its completed comparison is reused; the final tour separately exercises the merged native renderer.

## Limits and next groups

- **250 bodies remain:** seven read-program candidates, 48 historical helper-count types and 195 others.
  The four largest other groups screened admit none. Continue with RENDER-ITEMS-002Y, preserving independent
  input-state and record comparisons; do not turn rejected count adjustments into admissions.
- Existing pose/bone/record/buff, selected-item, absolute process-random and process-counter limits remain.
  The fourteen owned streams compare harness requests, not native particle-pool creation counts.
- Host-free body paths use zero random values where there is no item host. Nonzero shared-stream consumption
  is established by the complete owned comparison. No new particle consumer, original pose or pixel equivalence
  is claimed. Unsupported bones, kinds and textures retain explicit refusals.
- No original-client process/memory access, protection analysis, live service/packet work or character-power
  work was used. Inputs are fixtures and pinned offline captures; no new private capture needs retention.

The final push and ready-prs entry precede cleanup. Lane scratch, renders, reports, build outputs, worktree and
local branch are removed; the remote branch remains for the steward. Shared caches, captures and main's
input/tool directories are retained. No lane-local input is needed by a later task. Ready for steward;
merge and installation belong to their lanes.
