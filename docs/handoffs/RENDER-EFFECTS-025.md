# RENDER-EFFECTS-025

Branch `codex/render-effects-025`, from main `ff8e0543`. Main through `3732f82a` is integrated at
`0265ac46`; the final census-domain adjustment is `75e3a4b0`. Codex, GPT-6.1 Sol; no subagents.
Offline/static only. Research is [part 37](../research/client-render-items.md#part-37-missing-name-sprite-state-ferea-clouds-and-the-remaining-bow-pairs-render-effects-025).
The steward owns the full gate and merge. Installed Native Preview and Wine apps are untouched.

The lane's agent did the implementation and the checks listed below, then stopped at Codex's usage limit before
delivery. The orchestrator (Claude) merged main `e057d19e`, filled this handoff's two result tables from the
lane's recorded results, added the status lines and opened the PR. No source changed in that step.

## Result and original addresses

Ferea clouds/28 and two bow particle pairs now have native create/move/render consumers. Hammer14's exact
`up01` failure now follows the original sprite helper's -1 transform through an explicit separate record.
The original call has scale zero, so its restored request changes allocation/refusal counts without adding
visible area. No name trimming or substituted bone is used.

| Original operation | Address | Native behavior |
|---|---|---|
| Copy 32 authored bone-name bytes | `0x012b4276..0x012b4287`, memcpy `0x012b4282` | Preserve `up01 `, including its trailing space |
| Exact name search / fallback -1 | `0x012bd35a` / `0x012bd3b1` | Keep the exact-name failure |
| Bone sprite / unchecked matrix selection | `0x0150e746`, `0x0150e782..0x0150e78b` | Optional `item_before_transform` for exactly -1 |
| TransformPosition / sprite call | `0x012b6ef1` / `0x0150e7bf` | Same operations on the supplied twelve-word record |
| Hammer14 zero-scale push / call | `0x017d9a54..0x017d9a58` / `0x017d9a6e` | Preserve zero scale |
| Clouds `0x7f89/28` create / move | `0x015edeaf` / `0x0166200c` | Lifetime 300, quantized jitter/scale/rotation, clock-driven movement, alpha-modulated render light |
| Bow `0x8109/7` create / move | `0x015afd35` / `0x01618ab4` | Lifetime 10, saved scale, quantized velocity and random-axis damping |
| Bow `0x810a/9` create / move | `0x015b1605` / `0x0161acd9` | Lifetime 12, saved scale, half-life pulse and zero clamp |

The original -1 record starts at `0x06fce368`, before BoneTransform `0x06fce398`. Static references identify
process bookkeeping there, including a path-service pointer and tick word in matrix translation slots.
The native implementation never indexes before its pose allocation. `mu_renderchar_env.item_before_matrix`
supplies a separate record, zero by default. A fixture may supply another record or NULL. This ports the
operation on declared native state; the default is not a recovered original process record. Other negative
indices, oversized bones, unavailable ordinary poses and invalid dependent positions keep their refusals.

## Routed and refused census

The retained before captures use `ff8e0543`. The installed-item fixture covers the original 96 program
identities in twelve eight-wearer batches, sixteen consecutive draws each. Existing before captures were
reused when the reporting helper was repaired; they were not rendered again.

| Fixture | Before | After |
|---|---|---|
| 96-program pre-draw requests | 7,389 accepted / 28 refused | 7,416 accepted / 0 refused |
| Same fixture, unsupported particles | 12 | 0 |
| Eight maces, 61 draws, both clocks | 5,610 accepted / 61 refused | 5,671 accepted / 0 refused |
| Eight maces, sprite allocations / final submitted sprites | 5,063 / 83 | 5,124 / 84 |
| Closer Ferea, 41 draws, both clocks | 243 particles created / 14 unsupported | 257 / 0 |
| Closer Ferea, final submitted particles | 99 | 105 |
| Three bows, 61 draws, both clocks | 2,684 accepted / 43 refused; 0 created / 43 unsupported | 2,724 / 0; 40 / 0 |
| Three bows, final submitted particles | 0 | 10 |

The three bows are `0x1313`, `0x1317` and `0x1319`. Their two missing particle pairs account for five and
seven unsupported requests in the corresponding 16-draw census batches. New particle rand calls alter later
gated requests, so the before/after denominators are not equal and are not a replay of the same 43 requests.
Owner-effect refusals remain zero in the 96-program fixture. No new bitmap slot is required.

The proved static domain has 96 programs / 32 pairs, all supported, no unresolved bitmap expressions.
Main's RENDER-ITEMS-002X adds fourteen programs, making the full inventory 110 programs / 37 pairs, still with
no unresolved bitmap expressions. The validator freezes the 96 proved program identities and checks every
pair they request. It also reports the complete current inventory. Five later pairs remain refused:

| Pair | Later callers |
|---|---|
| `0x810a/12` | `0x0f1e`, `0x174a` |
| `0x81cf/1` | `0x2301`, `0x2302` |
| `0x810b/8` | `0x23a8`, `0x23a9` |
| `0x8500/2` | `0x23a8`, `0x23a9` |
| `0x8569/0` | `0x23a8`, `0x23a9` |

These are not counted as ported or included in the 96-program scene denominator. A future change within any
of the 96 proved programs still enters the assertions; later admissions remain visible in report metadata.

## Native renders and byte identity

All names are demo names, all renders use the software backend, and no live client is used. Affected-world
captures use clocks 0 and 123456. Mace and bow scenes use world 0 at tile 128,124; closer Ferea uses world 112
at tile 241,154. Every intermediate draw runs; only first/last PNGs are saved.

The final merged default sweep is 46 maps, 25 draws each, first/last PNGs, no draw_all. It compares the retained
baseline once: **91/92 PNGs and 92/92 OBJECT/light dumps are byte-identical**. Reports differ only at Ferea,
**45/46 identical after output/binary path normalization**. The only changed PNG is Ferea frame 24, 941 pixels,
bounding box `(56,0)-(636,170)`. Its counts change from five created / one unsupported / two drawn particles
to six / zero / three. Baseline map-render sum 58.43 s; final command 60.79 s.

Closer Ferea changes 6,623 / 6,626 pixels at the two clocks, bounds `(281,0)-(366,138)` and
`(281,0)-(367,138)`. New rand consumption also shifts later smoke/fire phases, so not every changed pixel is
attributed solely to the cloud. The native host separately proves positive cloud raster fragments.
The bow final frames change 1,137 / 1,141 pixels, bounds `(228,157)-(409,275)`. The cloud and bow comparisons,
default Ferea comparison and worn-mace frame were opened and inspected.

Both mace PNGs at both clocks are byte-identical, as expected for the restored zero-scale sprite.
The shipped control explicitly uses `native/world/lorencia-demo-players.txt`; its four saved PNGs are also
byte-identical. Its 1,584 accepted / zero refused pre-draw requests, 651 created / zero unsupported particles,
and final 230 particles / 36 sprites remain unchanged. The separate empty-player control is not called the
shipped demo.

## Checks

Every command runs from the repo root. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`, including the pinned inputs, `MU_SECTION3`, `MU_GAME_ROOT`,
`MU_NATIVE_DATA_DIR` and render libraries. Heavy commands use nice 10, make at most four jobs and runners two
workers. Load/memory guards caused cooldowns; no lane full gate was run.

| Check | Result | Wall |
|---|---|---:|
| Full focused proof (create/move/render, Hammer14 streams, native host, census) | 10,002 component comparisons, zero mismatches | 30.81 s |
| New registry row `validate_render_effects25` with compiled mutants | 202 comparisons, 24/24 mutants caught, zero stopped | 59.8 s |
| Private five-module run | 41 tests pass (three stale missing-name assertions corrected, rerun 0.660 s) | |
| First portable batch (after ACTORS-001/NEXT-GAPS main) | 1,652 tests: 1,371 pass, 280 skip, one new ctypes fixture failure, repaired and rerun (0.013 s) | 282.5 s |
| Merged portable delta | 1,464 tests: 1,223 pass, 241 skip, zero failures/errors | 422.6 s |
| Six-module private run | 45/45 | 115.2 s |
| Affected validators at compiled source `b63773a8` | 83/83 rows pass, 1,163,855 reported row checks, no mutants repeated | 2,220.41 s |
| After RENDER-ITEMS-002X main (`3732f82a`): portable delta, 147 items | 1,385 tests: 1,153 passed, 232 skipped, zero failures/errors | 314.2 s |
| After RENDER-ITEMS-002X main: reduced private renderer/effects25 | 27/27 | 18.2 s |
| Final default sweep (after RENDER-ITEMS-002X main) | 91/92 PNGs, 92/92 dumps, 45/46 path-normalized reports identical; only Ferea changes (941 pixels in frame 24) | 60.79 s |
| Affected merged scenes | complete | 15.93 s |

The 10,002 focused checks comprise 3,000 create, 3,000 move, 3,000 render, 1,000 complete Hammer14 streams,
one native adapter/raster check and one static census. Of these, 9,784 execute the original instructions;
216 directed zero-life movement checks exercise native head retirement, plus the two native/static checks.
The complete Hammer14 comparison includes exact-name failure, zero and arbitrary finite pre-bone records,
scale/origin, poses, counter values and hidden frames. It requires matching requests, draws and rand use,
with zero refused requests. No comparison tolerance is relaxed.

Initial failures were fixture expectations and reporting setup: three old missing-name refusal assertions,
one new ctypes pointer-slice assignment, and the synthetic raster's missing clear/camera setup. The corrected
tests and completed reruns are listed above. The initial small cloud comparison caught the missing alpha
multiplier, which was fixed before the full proof. The original arithmetic comparisons and 24 mutation targets
did not change after their completed runs. The late census change only declares its original domain and
reports later admissions; it does not mask any request from that domain.

**8d reduced:** selections exceed forty native items, including 142 after the final main merge. The private
passes cover this lane's changed modules, shared renderer/texture consumers and the actor module brought by
main, then the changed renderer and effects25 modules after RENDER-ITEMS-002X. Brief 6b review includes both
`mu_rc_owner_host` ctypes definitions, aggregate C initializers, `mu_renderchar_env` consumers and existing
missing-bone tests. No bitmap-table size changes. No mutants are requested from the steward; this lane's
24 changed-target mutants are complete.

## Steward validators

Steward validators: validate_item_ranked, validate_item_continuation, validate_item_expansion, validate_item_effects, validate_item_clusters, validate_item_types, validate_fidelity, validate_meshdraw, validate_model_edge, validate_movement, validate_particles, validate_renderchar, validate_viewport_monsters, validate_render_worlds_a, validate_icarus_c2, validate_worlds_e, validate_audio_callers, validate_item_gear, validate_audio_combat, validate_item_next, validate_render_effects, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_world_particle_consumers, validate_audio_domains, validate_audio_items, validate_worlds_l, validate_item_coverage, validate_item_wings_next, validate_item_scalars, validate_item_chains, validate_worlds_m, validate_worlds_after, validate_worlds_g3, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_item_carry, validate_item_quality, validate_item_product, validate_item_derived, validate_item_ownerfx, validate_item_predraw, validate_item_hiddenmesh, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_render_effects13, validate_render_effects14, validate_worlds_slots, validate_worlds_slots2, validate_worlds_slots3, validate_worlds_121, validate_worlds_raklion, validate_worlds_karutan, validate_render_effects15, validate_render_effects16, validate_worlds_fog, validate_render_effects17, validate_item_callers, validate_inventory_fx, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_item_cloak, validate_armour_cloak, validate_render_effects22, validate_item_named, validate_npc_cloak, validate_render_effects23, validate_render_effects24, validate_render_effects25, validate_actor_recipes

All 83 rows pass at compiled source `b63773a8` (table below; no mutants repeated; this lane's 24 changed-target
mutants are complete). Environment: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

Not finished by the lane: the 54-row validator delta after RENDER-ITEMS-002X main was interrupted when Codex
reached its usage limit (three rows had passed: `validate_item_groups`, `validate_item_hiddenmesh`,
`validate_item_carry`). Main has since also gained AUDIO-002G, RENDER-ACTORS-002 and CHARSEL-ITEMS-001
(`e057d19e`, merged here without conflicts). The merge steward therefore runs the whole affected selection once
on the combined tree; its result is in the steward log, batch 99.

| Validator | Checks | Wall s at `b63773a8` |
|---|---:|---:|
| `validate_actor_recipes` | 361 | 48.1 |
| `validate_app_polish1` | 752 | 17.0 |
| `validate_app_polish2` | 1,028 | 3.0 |
| `validate_app_polish4` | 10,485 | 28.9 |
| `validate_armour_cloak` | 4,448 | 64.3 |
| `validate_audio_callers` | 5,528 | 7.5 |
| `validate_audio_combat` | 19,548 | 46.9 |
| `validate_audio_domains` | 2,544 | 21.5 |
| `validate_audio_items` | 3,000 | 3.6 |
| `validate_fidelity` | 991 | 70.3 |
| `validate_icarus_c2` | 8,400 | 28.1 |
| `validate_inventory_fx` | 8,017 | 12.0 |
| `validate_item_callers` | 6,013 | 1.7 |
| `validate_item_carry` | 114,388 | 511.4 |
| `validate_item_chains` | 35,406 | 113.3 |
| `validate_item_cloak` | 5,694 | 198.6 |
| `validate_item_clusters` | 74,292 | 59.8 |
| `validate_item_continuation` | 25,772 | 44.3 |
| `validate_item_coverage` | 31,724 | 50.8 |
| `validate_item_derived` | 36,252 | 278.8 |
| `validate_item_effects` | 1,500 | 1.4 |
| `validate_item_expansion` | 52,172 | 58.7 |
| `validate_item_gear` | 25,256 | 99.5 |
| `validate_item_hiddenmesh` | 116,281 | 476.4 |
| `validate_item_named` | 20,057 | 4.4 |
| `validate_item_next` | 14,992 | 196.6 |
| `validate_item_ownerfx` | 14,964 | 194.2 |
| `validate_item_predraw` | 37,556 | 262.7 |
| `validate_item_product` | 2,874 | 61.6 |
| `validate_item_quality` | 28,080 | 227.5 |
| `validate_item_ranked` | 17,736 | 43.4 |
| `validate_item_scalars` | 26,274 | 63.3 |
| `validate_item_types` | 135,176 | 36.3 |
| `validate_item_wings_next` | 33,622 | 64.9 |
| `validate_meshdraw` | 14,619 | 76.4 |
| `validate_model_edge` | 954 | 183.0 |
| `validate_movement` | 6,614 | 80.3 |
| `validate_npc_cloak` | 2,619 | 43.3 |
| `validate_particles` | 407 | 1.3 |
| `validate_render_effects` | 660 | 1.0 |
| `validate_render_effects10` | 154 | 0.3 |
| `validate_render_effects11` | 176 | 0.3 |
| `validate_render_effects12` | 64 | 0.3 |
| `validate_render_effects13` | 180 | 0.5 |
| `validate_render_effects14` | 660 | 1.2 |
| `validate_render_effects15` | 509 | 1.3 |
| `validate_render_effects16` | 424 | 4.6 |
| `validate_render_effects17` | 618 | 9.8 |
| `validate_render_effects18` | 540 | 2.4 |
| `validate_render_effects19` | 400 | 1.4 |
| `validate_render_effects20` | 148 | 0.4 |
| `validate_render_effects21` | 267 | 0.5 |
| `validate_render_effects22` | 202 | 5.2 |
| `validate_render_effects23` | 1,174 | 8.1 |
| `validate_render_effects24` | 226 | 3.4 |
| `validate_render_effects25` | 202 | 9.0 |
| `validate_render_effects3` | 720 | 0.9 |
| `validate_render_effects4` | 1,920 | 5.4 |
| `validate_render_effects5` | 1,190 | 3.4 |
| `validate_render_effects6` | 1,000 | 1.0 |
| `validate_render_effects7` | 596 | 1.4 |
| `validate_render_effects9` | 304 | 0.8 |
| `validate_render_worlds_a` | 9,000 | 18.7 |
| `validate_renderchar` | 1,706 | 68.5 |
| `validate_viewport_monsters` | 1,963 | 13.4 |
| `validate_world_particle_consumers` | 900 | 0.6 |
| `validate_worlds_121` | 4,000 | 7.3 |
| `validate_worlds_after` | 13,424 | 10.2 |
| `validate_worlds_after2` | 32,216 | 20.4 |
| `validate_worlds_after3` | 10,212 | 7.7 |
| `validate_worlds_after4` | 9,181 | 12.8 |
| `validate_worlds_after5` | 6,000 | 11.4 |
| `validate_worlds_after6` | 7,300 | 66.2 |
| `validate_worlds_e` | 4,840 | 24.7 |
| `validate_worlds_fog` | 4,044 | 10.4 |
| `validate_worlds_g3` | 4,000 | 3.3 |
| `validate_worlds_karutan` | 3,000 | 5.9 |
| `validate_worlds_l` | 1,260 | 0.9 |
| `validate_worlds_m` | 1,080 | 1.0 |
| `validate_worlds_raklion` | 3,000 | 5.7 |
| `validate_worlds_slots` | 18,999 | 22.4 |
| `validate_worlds_slots2` | 33,000 | 39.6 |
| `validate_worlds_slots3` | 36,000 | 41.5 |

## Limits and next

- The zero native pre-bone record is compatibility state. Original adjacent process words, absolute RNG and
  counter phases, original poses and original-client pixels are not established by native before/after images.
- The 96-program scene uses installed assets and bounded fixture states. It is not a refusal census of every
  item, every counter phase or every world producer. The five later pairs above remain unsupported.
- Next, capture and rank the fourteen newly admitted programs' actual refused requests, then port the largest
  of the five listed pairs using the same original create/move/render and native raster checks. Do not enlarge
  Hammer14's zero-scale sprite to manufacture a visual gain or trim the authored name.
- No protection/anti-cheat analysis, live service/login/packet work, character-power feature or client-memory
  write was used. No installed app is replaced. Inputs are pinned captures, read-only Native Data and fixtures.

After the final push and single ready-prs entry, lane scratch/renders, build outputs, worktree and local branch
are removed. The remote branch remains for the steward. Shared validator cache, captures, private environment
and main's input/tool directories are retained. No new input needs to survive this lane's cleanup.

## Work log (lane checkpoints, in order)

Branch `codex/render-effects-025`, base main `ff8e0543`. Offline/static only. No live client,
installed app, launcher, network, server-state, protection-module work or memory writes.
No subagents. Research part 37 is planned, subject to checking main before the final push.

Done:
- Traced Hammer14's `up01` lookup and sprite helper. The loader copies the authored name,
  the lookup returns -1 for `up01 `, and the sprite helper still reads `BoneTransform - 0x30`.
  Added an explicit optional host transform for that separate record. Names stay exact;
  other negative and out-of-range bones retain their refusals.
- The native default supplies a separate zero record. Fixtures may supply all twelve words
  or NULL to retain the refusal. This ports the operation on explicit native state. It does
  not establish identity with the original process bookkeeping occupying that address.
- Ported clouds/28 create/move/render. The initial sample caught the missing alpha multiplier.
- Expanded the scene census to 96 admitted programs in twelve eight-wearer batches. The two
  remaining particle pairs are `0x8109/7` from `0x1313`/`0x1317`, and `0x810a/9` from `0x1319`.
  Added both consumers. They account for 12 unsupported requests in the bounded 16-draw fixture.
- Captured main's default 46-view sweep once, plus eight maces, closer Ferea and the Lorencia
  demo at clocks 0/123456. Local outputs are lane-owned under `native/{scratch,renders}/render-effects-025`
  in the shared tools directory. No proprietary inputs or rendered images are staged.

Checks so far:
- Baseline root build 42.73 s, explicit render targets 5.19 s.
- Implementation builds 12.50, 10.80 and 14.95 s after the initial aggregate initializer repair.
- First focused final-scope sample: 2,001 comparisons, zero mismatches, 8.406 s script.
  This is 600 create, 600 move, 600 render, 200 complete Hammer14 request streams and one native host.
- Initial two native module tests passed in 10.881 s, before adding the two bow pairs and
  the full native draw-adapter assertion. Those additions still need their final private run.

Left:
- Finish compiled mutants, registry row and final full focused sample.
- Finish the native adapter assertion and portable fallback/negative-domain test.
- Compare native after renders and finish the 96-program refusal census.
- Run post-build affected selectors, affected portable suites/private validators, 8d reduced and 6b consumers.
- Merge latest main, write research and final handoff/status/PR body, audit, push, PR, ready line, cleanup.

The steward owns the full gate and merge. No ready-prs entry exists for this lane at this checkpoint.

Checkpoint update: the full focused proof passes 10,002 component comparisons, zero mismatches,
30.81 s script / 30.87 s command. The new registry row passes 202 comparisons and 24/24 compiled
mutants, zero stopped, 59.8 s row / 59.89 s command. The private five-module run covers 41 tests:
38 initially pass, three stale missing-name assertions are corrected and all three pass on rerun
in 0.660 s. No production code changed for those expectation repairs. The expanded 96-program
scene changes 7,389 accepted / 28 refused to 7,416 / zero; unsupported particles 12 to zero.
The denominator changes because newly admitted particle rand calls affect later gated requests.
The eight-mace run changes 5,610 / 61 to 5,671 / zero, with 61 more sprite allocations and one
more sprite submitted at the final frame. Its final PNGs remain identical; no visible gain is
claimed for those cameras. Closer Ferea creates 257 particles / zero unsupported versus 243 / 14.
The two-clock final frames change 6,623 / 6,626 pixels.

Post-build selectors retain 80 validators, including meshdraw, model_edge and movement symbol
fallbacks. The portable selector exceeds the private 40-module cap; 8d is reduced to changed
native modules plus shared consumers. The affected batches and final identity sweep are next.

Merged main ACTORS-001 as `ba6c5bfd`, then NEXT-GAPS-001 as `00e84869`. Both appended validator
rows are retained. Merged root build passes in 12.93 s; render targets in 5.35 s; manifest checks
in 1.14 s. The combined range from ff8e0543 selects 83 validators, including actor_recipes,
audio_combat and viewport_monsters beyond the original 80. The merged portable delta selects
155 work items; its native selection still exceeds the 8d cap.

The first portable batch covers 1,652 tests: 1,371 pass, 280 skip, one new ctypes fixture fails.
The fixture wrote through a pointer slice without an end index; explicit element stores repair it.
That failed test passes in 0.013 s. No production behavior changed. Batch wall 282.5 s / 347.83 s
including selection. The native host now clears its raster, supplies identity view/projection
and asserts actual fragments in addition to the existing routing and adapter assertions; it
passes in 1.570 s. The original arithmetic comparators and compiled mutation targets are unchanged.

The merged portable delta passes 1,464 tests: 1,223 pass, 241 skip, no failures/errors, 422.6 s
runner / 504.28 s command. The six-module private run passes all 45 tests in 115.188 s runner /
115.28 s command. The 83-row affected validator batch is running. Main has since landed
RENDER-ITEMS-002X as `3732f82a`; merge and delta checks follow after the current batch finishes.
Research part 36 is now occupied on main; this lane retains part 37.

Static follow-up explains Hammer14's unchanged pixels. The original `up01` call at `0x017d9a6e`
pushes scale zero at `0x017d9a54..0x017d9a58`. The native restored request also has scale zero.
The refusal and allocation counts change; its visible area does not. No positive-size replacement
or name trimming is introduced.

The 83-row batch completes at compiled source `b63773a8`: all pass, 1,163,855 reported row checks,
2,220.41 s command / 4,240.3 s aggregate row wall. No mutants repeated. Main `3732f82a` is now
integrated, with both research parts 36/37 and both validator additions retained. Latest-main
build, selectors, delta checks and final identity sweep are pending.

Latest-main checkpoint: root build 10.23 s, render targets 3.35 s. The 147-item portable delta
passes 1,385 tests, 1,153 passed / 232 skipped / no failures or errors, 314.2 s runner / 365.67 s
command. The reduced private renderer/effects25 pass has 27 tests, all pass, 18.236 / 18.29 s.
Final default sweep: 91/92 PNGs, 92/92 dumps and 45/46 path-normalized reports identical; only
Ferea changes, 941 pixels in its frame 24. Sweep 60.79 s. Affected merged scenes complete in
15.93 s. The 54-row latest-main validator delta is running.

Main now has 110 programs / 37 particle pairs. This lane proves the retained 96 identities /
32 pairs, all supported. The report retains the full inventory, including five new unsupported
pairs from main: 0x810a/12, 0x81cf/1, 0x810b/8, 0x8500/2 and 0x8569/0. These are next work,
not additions claimed by this lane. The final handoff draft is prepared; final checks/PR/ready
entry/cleanup remain. No ready entry exists yet.
