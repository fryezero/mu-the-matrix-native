# RENDER-EFFECTS-026

WIP on `codex/render-effects-026`, initially from main `d4af71dd`, with main `fb747e42` (steward batch 104) integrated.
Codex GPT-6.1 Sol; no subagents. Offline/static only. The steward owns the full gate and merge.
Research: [part 39](../research/client-render-items.md#part-39-five-later-item-particle-consumers-render-effects-026).

## What draws

The five pairs left by EFFECTS-025 now have native create, move and render consumers:
`0x8500/2`, `0x810b/8`, `0x810a/12`, `0x81cf/1`, `0x8569/0`.
The two new native bitmap mappings are `Skill/wing_hetachi2.OZJ` and `Effect/Damage_ring_2.OZJ`.
The world bitmap table grows 95 to 97; prior slots 0..91 stay fixed and Fire06/rain remain at the tail.

The owner-point ring now follows all four authored points. Original caller `0x017cd01f` writes cr002 at
OBJECT `+0x218` every draw; `0x017cd025..0x017cd0f0` requests indices 0..3 on counter % 25 == 0.
The older generated table exported only the first nine point words. The consumer now exports the fourth
transform at the two frozen wing programs' r305/bone-register-r16 operation, stores twelve words in native
item-owner slots and routes index 3 at render time. Tables and generators are unchanged. Older particle
consumers retain their 0..2 bounds. The native adapter verifies pose refresh on ungated frames 24 and 26.

| Pair | Original create | Original move | Original render | Callers |
|---|---|---|---|---|
| `0x8500/2` | `0x0160d351` | `0x01685e1b` | `0x015a9b9a` | `0x23a8`, `0x23a9` |
| `0x810b/8` | `0x01601dca` | `0x0167be27` | `0x015a0fce` | `0x23a8`, `0x23a9` |
| `0x810a/12` | `0x015b1a73` | `0x0161b036` | `0x0159faca` | `0x0f1e`, `0x174a` |
| `0x81cf/1` | `0x0160baa3` | `0x01684277` | `0x015a5eec` | `0x2301`, `0x2302` |
| `0x8569/0` | `0x01610b2d` | `0x016896de` | `0x015aa1a0` | `0x23a8`, `0x23a9` |

The two loader calls are `0x01827a23` and `0x01825e21`, LINEAR/CLAMP, flags 1/0.
No authored scale or name is changed. Hammer14's zero-scale sprite is not enlarged.

## Routed, refused and unavailable

The static inventory freezes all 110 program identities / 37 particle pairs, all supported, with zero
unresolved bitmap expressions. Later additions stay visible in report metadata without enlarging this claim.
The installed fixture uses one declared item override per hero scene, each armour/wing in its corresponding
slot and other models in a weapon slot. It is a renderer fixture, not equipment eligibility. Every intermediate
frame draws; only first/last PNGs save. This differs from EFFECTS-025's eight-wearer fixture and its denominator.

| Scene | Before | After |
|---|---|---|
| 109 installed models, 16 consecutive draws each, pre requests | 13,151 accepted / 122 refused | 13,273 / 0 |
| Same scene, owner requests | 2,784 accepted / 0 refused | unchanged |
| Same scene, particles | 703 created / 122 unsupported | 825 / 0 |
| Same scene, last submitted particles summed across fixtures | 670 | 792 |
| Fourteen later programs, 61 draws each, clocks 0 and 123456, pre requests per clock | 10,223 accepted / 485 refused | 10,708 / 0 |
| Same later scene, particles per clock | 36 created / 485 unsupported | 521 / 0 |
| Same later scene, last submitted particles per clock | 14 | 223 |

The 110-row installed scene records one unavailable row, `0x1a78`: the exact Item.bmd model path
`Data/Item/HelmMale150_crusader.bmd ` includes a trailing space and is absent. No trimming or asset substitution
is used. The measured scene denominator is therefore 109 installed models, plus that unavailable row.
All fourteen later programs have installed models. Actual refused requests in their longer baseline rank:
`0x8500/2` 244, `0x810b/8` 122, `0x810a/12` 91, `0x8569/0` 16, `0x81cf/1` 12.
The sixteen-draw census does not reach the ring's 25-draw gate. The longer capture does.

## Render and identity evidence

Software backend, demo names only, 640x480 item scenes. Full scene: 209/218 saved PNGs byte-identical.
Each longer clock scene: 19/28 byte-identical. Only the six expected caller models change. Final-frame
pixel differences at clocks 0 / 123456 are: `0x0f1e` 1,054 / 1,059; `0x174a` 58 / 53;
`0x2301` and `0x2302` each 517 / 519; `0x23a8` and `0x23a9` each 2,209 / 2,234.
Spark, ring and wing before/after/difference images were opened and inspected. The five isolated synthetic
native raster controls also produce positive fragments with their created scale and alpha. Their empty
controls are explicitly synthetic, not original-client screenshots or a second main-binary capture.

The final default sweep has 46 views, 25 simulation frames each, default draw, first/last PNGs, no draw_all:
**92/92 PNGs and 92/92 OBJECT/light dumps are byte-identical.** Both binaries were explicitly built as
mu-world targets; hashes are distinct:

- Clean main baseline: `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
- Diagnostic main baseline for request scenes, only added refusal logging:
  `61f7bdaa1debca52f70691f1a3b21b2ffc3954bf5f033e785d4f31b8f8c055c4`.
- Particle-final after, both item scenes and the first after sweep: `52d3a94dac2ab14bcaa0a4d4b61a8fc97a94d097b27c735d500894a59fc548c9`.

Valid before captures were taken once and retained. Early provisional scenes that omitted intermediate draws
were discarded as evidence. Native image changes do not establish original GPU pixels, poses or process phase.

## Checks and test budget

All commands run from the repo root. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`, including pinned inputs, MU_SECTION3, game/data roots,
render libraries and the shared original-side cache. Heavy commands use nice 10, make at most four jobs,
validator workers two. Resource guards caused waits. No lane full gate runs.

| Check | Result | Wall seconds |
|---|---|---:|
| `validate_render_effects26.py --cases 1000` | 17,008 checks, zero mismatches | 48.020 command / 47.950 script |
| New registry row, `--cases 20 --mutations` | 348 checks, 37/37 compiled mutants caught, zero machine stops | 92.802 command / 92.6 row |
| Final root `make -j4` | pass | 12.407 |
| Explicit `make -C native -j4 world` before final sweep | pass | 5.441 |
| Private reduced modules | 43/43 tests pass, zero skips | 54.529 command / 54.392 tests |
| Portable `run_test_suites.py --affected origin/main` | 1,690 tests: 1,400 passed, 290 skipped, zero failures/errors | 353.122 command / 294.9 runner |
| Post-build validator selection | 86/223 rows | 75.721 |
| Post-build suite selection | 161/200 work items, 153 native modules | 60.758 |
| 109 installed-model baseline / final scene, 16 draws | census above | 105.831 / 170.874 |
| Later fourteen baseline / final scene, clock 0, 61 draws | census above | 23.247 / 28.556 |
| Later fourteen baseline / final scene, clock 123456, 61 draws | census above | 24.829 / 17.109 |
| Default 46-view sweep, before / after | 92/92 PNGs and 92/92 dumps byte-identical | 61.706 / 87.626 |
| Image/census/hash QA plus five native raster controls | pass | 2.500 |
| Affected private validators, no mutants, workers 2 | 86/86 rows pass, 1,166,680 cases, zero failures/errors/skips | 2,354.564 |
| Repository audit | 2,194 files, zero rejected (before final docs) | 24.805 |


The 17,008 focused checks contain 16,640 cases against original instructions: 5,000 create, 4,640 move,
5,000 render and 2,000 complete caller streams observing all twelve OBJECT point words. Another 360
checks cover native head retirement; five cover native pool/adapter/raster; two static loader-site checks
and one static inventory complete the count. No comparison tolerance is relaxed. Original instruction
identity is pinned by text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`
and data SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, plus flag/feature pins.

The 37 compiled mutants comprise 24 particle targets, ten native routing/bitmap/bounds targets and three
fourth-point caller targets. Each fourth-point mutant mismatches 69/80 caller streams; hidden streams
preserve state. All mutants are caught without an original-machine stop. The earlier 32-mutant run was
superseded after review found index 3 outside its observation domain. The first sample also caught the
spin word mapped to the wrong field; final code uses `+0x84`. These were corrected, not hidden by tolerances.

**8d reduced:** 153 native work items exceed the forty-item cap. The private pass covers nine modules,
43 tests with zero skips: changed/added effects26 and native particles, shared renderer, and the direct
bitmap/point consumers in effects16/20/22/23/24/25. Effects24's installed class runs too. The effects22
invalid-word control now uses 12; index 9 is intentionally valid. Legacy instruction families keep their
nine-word observation; the new coupled family explicitly requests all twelve.

## Steward validators

Steward validators: validate_item_ranked,validate_item_continuation,validate_item_expansion,validate_item_effects,validate_item_clusters,validate_item_types,validate_fidelity,validate_meshdraw,validate_model_edge,validate_movement,validate_particles,validate_renderchar,validate_render_worlds_a,validate_icarus_c2,validate_worlds_e,validate_audio_callers,validate_item_gear,validate_item_next,validate_render_effects,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_world_particle_consumers,validate_audio_domains,validate_audio_items,validate_worlds_l,validate_item_coverage,validate_item_wings_next,validate_item_scalars,validate_item_chains,validate_worlds_m,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_item_carry,validate_item_quality,validate_item_product,validate_item_derived,validate_item_ownerfx,validate_item_predraw,validate_item_hiddenmesh,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_item_cloak,validate_armour_cloak,validate_render_effects22,validate_item_named,validate_npc_cloak,validate_render_effects23,validate_render_effects24,validate_worlds_inner,validate_render_effects27,validate_item_groups,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_render_effects26,validate_worlds_inner2,validate_audio_objects,validate_render_effects28

Tested at `cd8d586faf97f2685246e514c63887ab1c2a5053`; the initial lane selection is 86/223 rows; the batch-103 selection is 87/225; latest selection is 89/227, including
movement's shell-object fallback. No steward mutant rerun is needed. New-row mutants passed at
`8d370d6ffc0725fd62cbccec2ded2fdf7d716efa`; later edits to its targets are comments only. The steward can
skip unchanged compiled inputs. The post-merge integration selection and second tested commit are recorded below.


| Validator | Cases | Wall seconds | Result |
|---|---:|---:|---|
| `validate_actor_recipes` | 1,300 | 133.6 | pass |
| `validate_app_polish1` | 752 | 20.5 | pass |
| `validate_app_polish2` | 1,028 | 4.9 | pass |
| `validate_app_polish4` | 10,485 | 46.6 | pass |
| `validate_armour_cloak` | 4,448 | 62.2 | pass |
| `validate_audio_callers` | 5,528 | 4.8 | pass |
| `validate_audio_domains` | 2,544 | 20.2 | pass |
| `validate_audio_items` | 3,000 | 3.4 | pass |
| `validate_charsel_items` | 8,817 | 9.9 | pass |
| `validate_fidelity` | 991 | 48.6 | pass |
| `validate_icarus_c2` | 8,400 | 16.2 | pass |
| `validate_inventory_fx` | 8,017 | 7.1 | pass |
| `validate_item_callers` | 6,013 | 1.2 | pass |
| `validate_item_carry` | 114,388 | 589.8 | pass |
| `validate_item_chains` | 35,406 | 108.8 | pass |
| `validate_item_cloak` | 5,694 | 170.6 | pass |
| `validate_item_clusters` | 74,292 | 49.0 | pass |
| `validate_item_continuation` | 25,772 | 52.9 | pass |
| `validate_item_coverage` | 31,724 | 85.6 | pass |
| `validate_item_derived` | 36,252 | 345.5 | pass |
| `validate_item_effects` | 1,500 | 0.9 | pass |
| `validate_item_expansion` | 52,172 | 48.2 | pass |
| `validate_item_gear` | 25,256 | 65.1 | pass |
| `validate_item_groups` | 4,824 | 38.2 | pass |
| `validate_item_hiddenmesh` | 116,281 | 531.9 | pass |
| `validate_item_named` | 20,057 | 4.7 | pass |
| `validate_item_next` | 14,992 | 203.6 | pass |
| `validate_item_ownerfx` | 14,964 | 195.3 | pass |
| `validate_item_predraw` | 42,540 | 429.4 | pass |
| `validate_item_product` | 2,874 | 82.4 | pass |
| `validate_item_quality` | 28,080 | 220.6 | pass |
| `validate_item_ranked` | 17,736 | 52.9 | pass |
| `validate_item_scalars` | 26,274 | 54.9 | pass |
| `validate_item_types` | 135,176 | 27.1 | pass |
| `validate_item_wings_next` | 33,622 | 60.8 | pass |
| `validate_meshdraw` | 14,619 | 51.1 | pass |
| `validate_model_edge` | 954 | 122.0 | pass |
| `validate_movement` | 6,614 | 62.3 | pass |
| `validate_npc_cloak` | 2,619 | 47.0 | pass |
| `validate_particles` | 407 | 1.8 | pass |
| `validate_render_effects` | 660 | 0.7 | pass |
| `validate_render_effects10` | 154 | 0.3 | pass |
| `validate_render_effects11` | 176 | 0.2 | pass |
| `validate_render_effects12` | 64 | 0.2 | pass |
| `validate_render_effects13` | 180 | 0.9 | pass |
| `validate_render_effects14` | 660 | 3.5 | pass |
| `validate_render_effects15` | 509 | 0.9 | pass |
| `validate_render_effects16` | 424 | 3.4 | pass |
| `validate_render_effects17` | 618 | 6.5 | pass |
| `validate_render_effects18` | 540 | 1.1 | pass |
| `validate_render_effects19` | 400 | 0.9 | pass |
| `validate_render_effects20` | 148 | 0.2 | pass |
| `validate_render_effects21` | 267 | 0.3 | pass |
| `validate_render_effects22` | 202 | 7.3 | pass |
| `validate_render_effects23` | 1,174 | 10.5 | pass |
| `validate_render_effects24` | 226 | 3.2 | pass |
| `validate_render_effects25` | 202 | 14.2 | pass |
| `validate_render_effects26` | 348 | 12.6 | pass |
| `validate_render_effects27` | 424 | 1.6 | pass |
| `validate_render_effects3` | 720 | 0.7 | pass |
| `validate_render_effects4` | 1,920 | 7.0 | pass |
| `validate_render_effects5` | 1,190 | 3.2 | pass |
| `validate_render_effects6` | 1,000 | 0.9 | pass |
| `validate_render_effects7` | 596 | 1.2 | pass |
| `validate_render_effects9` | 304 | 0.7 | pass |
| `validate_render_worlds_a` | 9,000 | 17.1 | pass |
| `validate_renderchar` | 1,706 | 45.9 | pass |
| `validate_world_particle_consumers` | 900 | 0.6 | pass |
| `validate_worlds_121` | 4,000 | 3.3 | pass |
| `validate_worlds_after` | 13,424 | 8.5 | pass |
| `validate_worlds_after2` | 32,216 | 29.4 | pass |
| `validate_worlds_after3` | 10,212 | 5.4 | pass |
| `validate_worlds_after4` | 9,181 | 9.7 | pass |
| `validate_worlds_after5` | 6,000 | 7.3 | pass |
| `validate_worlds_after6` | 7,300 | 48.1 | pass |
| `validate_worlds_e` | 4,840 | 14.9 | pass |
| `validate_worlds_fog` | 4,044 | 13.0 | pass |
| `validate_worlds_g3` | 4,000 | 3.2 | pass |
| `validate_worlds_inner` | 4,000 | 4.3 | pass |
| `validate_worlds_karutan` | 3,000 | 3.7 | pass |
| `validate_worlds_l` | 1,260 | 1.2 | pass |
| `validate_worlds_m` | 1,080 | 0.7 | pass |
| `validate_worlds_raklion` | 3,000 | 3.2 | pass |
| `validate_worlds_slots` | 18,999 | 25.8 | pass |
| `validate_worlds_slots2` | 33,000 | 21.6 | pass |
| `validate_worlds_slots3` | 36,000 | 22.1 | pass |


## UI-window main integration

Main `710ac816` changes UI windows/input and documentation. Merge `7f94e87d312d711fbf3e21631d25462d96a22bc9`
is clean. No particle/caller target or proof changed. The root build passes in 6.182 s, explicit world build
in 5.434 s. Post-build selection takes 31.043 s for 12/223 validator rows and 75.971 s for 134/201 suite work
items (129 native modules). Movement's shell-object fallback remains selected.

The portable delta command `run_test_suites.py --affected-since cd8d586f` passes 1,424 tests: 1,167 passed,
257 skipped, zero failures/errors, 459.368 s command / 376.4 s runner. The private delta is again **8d reduced**:
the nine original private modules plus upstream's new UI-windows module are selected explicitly.

Private delta: 46/46 tests pass, zero skips, 57.897 s command / 57.721 s tests.

The twelve selected post-merge validators pass 40,415 case checks, zero failures/errors/skips, 92.894 s command, at `5bf576d6c5e96d759b19c1a76b6b9b5689891997`. No mutants run again.

Post-merge validators: validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_gfx3,validate_map_polish,validate_movement,validate_render_effects16,validate_worlds_fog

| Validator | Cases | Wall seconds | Result |
|---|---:|---:|---|
| `validate_app_polish1` | 752 | 23.3 | pass |
| `validate_app_polish2` | 1,028 | 4.3 | pass |
| `validate_app_polish4` | 10,485 | 34.3 | pass |
| `validate_app_polish7` | 5,120 | 1.6 | pass |
| `validate_audio_callers` | 5,528 | 6.9 | pass |
| `validate_audio_domains` | 2,544 | 30.0 | pass |
| `validate_audio_items` | 3,000 | 4.5 | pass |
| `validate_gfx3` | 0 | 5.2 | pass |
| `validate_map_polish` | 876 | 0.7 | pass |
| `validate_movement` | 6,614 | 61.8 | pass |
| `validate_render_effects16` | 424 | 4.6 | pass |
| `validate_worlds_fog` | 4,044 | 8.3 | pass |

Before the final after-only default sweep, `make -C native -j4 world` passes in 0.338 s. The sweep passes in 79.611 s, with comparison in 0.240 s: **92/92 PNGs and 92/92 OBJECT/light dumps remain byte-identical** to the retained original baseline. No before capture is rerun. UI-merged world SHA-256 is `a3512931e8a49e3a68688c6a6ca9e6006f210d2b6fe43482544067d902b54f0e`, distinct from baseline `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`. The particle scene captures above retain their separately recorded binary hash.


## Batch 103 integration

Latest main `6b75fbda` adds actor, Muun and opt-in aura changes plus app-refresh documentation.
The registry conflict preserves both appended rows and upstream's actor expectations; this lane's final
registry diff is 17 added lines and zero deletions. No particle or fourth-point caller target changes.
The root/world builds pass in 15.278 / 7.564 s. Delta selection is 59/225 validator rows in 49.363 s and
165/202 suite work items in 118.776 s (153 native items, **8d reduced**). Fresh lane selection
is 87/225 rows in 113.683 s; the newly reached effects28 row is in
the delta batch. Every final lane row is covered by the initial or refreshed input checks.

Portable delta command: `run_test_suites.py --affected-since 5bf576d6`,
519.424 s command. Its exact result is:

`run_test_suites: 13 suites, 1773 tests, 1481 passed, 292 skipped, 0 failures, 0 errors; 0 failed suite(s); 416.7s wall, jobs=2`

The original nine private modules and direct shared-symbol consumers pass 43/43
tests with zero skips, 30.998 s command. The upstream UI-only private
module was already verified in the previous integration pass. No full lane gate or mutant rerun occurs.

All 59 delta validators pass 848,830 case checks, zero failures/errors/skips, in
882.643 s command, at `7a21ba0cae35c43701c411a20defa5c28aad5fa6`.

| Validator | Cases | Wall seconds | Result |
|---|---:|---:|---|
| `validate_actor_recipes` | 1,669 | 102.0 | pass |
| `validate_app_polish4` | 10,485 | 34.4 | pass |
| `validate_audio_callers` | 5,528 | 5.8 | pass |
| `validate_audio_charsel` | 5,968 | 3.2 | pass |
| `validate_audio_combat` | 19,548 | 20.4 | pass |
| `validate_audio_domains` | 2,544 | 25.4 | pass |
| `validate_audio_items` | 3,000 | 3.8 | pass |
| `validate_charsel_items` | 8,817 | 8.0 | pass |
| `validate_combat` | 496 | 0.7 | pass |
| `validate_icarus_c2` | 8,400 | 24.0 | pass |
| `validate_inventory_fx` | 8,017 | 7.7 | pass |
| `validate_item_callers` | 6,013 | 2.0 | pass |
| `validate_item_hiddenmesh` | 116,281 | 522.8 | pass |
| `validate_items` | 444 | 2.1 | pass |
| `validate_meshdraw` | 14,619 | 85.9 | pass |
| `validate_model_edge` | 954 | 174.8 | pass |
| `validate_model_light` | 1,433 | 4.5 | pass |
| `validate_movement` | 6,614 | 70.5 | pass |
| `validate_muun_passes` | 1,361 | 1.0 | pass |
| `validate_muun_visual` | 912 | 1.0 | pass |
| `validate_path` | 4,719 | 27.4 | pass |
| `validate_render_effects` | 660 | 1.0 | pass |
| `validate_render_effects10` | 154 | 0.8 | pass |
| `validate_render_effects11` | 176 | 0.5 | pass |
| `validate_render_effects12` | 64 | 0.5 | pass |
| `validate_render_effects13` | 180 | 0.5 | pass |
| `validate_render_effects14` | 660 | 1.9 | pass |
| `validate_render_effects15` | 509 | 0.9 | pass |
| `validate_render_effects16` | 424 | 3.8 | pass |
| `validate_render_effects17` | 618 | 8.6 | pass |
| `validate_render_effects18` | 540 | 2.3 | pass |
| `validate_render_effects19` | 400 | 0.9 | pass |
| `validate_render_effects20` | 148 | 0.3 | pass |
| `validate_render_effects21` | 267 | 0.6 | pass |
| `validate_render_effects22` | 202 | 6.4 | pass |
| `validate_render_effects23` | 1,174 | 10.9 | pass |
| `validate_render_effects24` | 226 | 2.7 | pass |
| `validate_render_effects25` | 202 | 10.6 | pass |
| `validate_render_effects26` | 348 | 12.2 | pass |
| `validate_render_effects27` | 424 | 2.4 | pass |
| `validate_render_effects28` | 630 | 1.6 | pass |
| `validate_render_effects3` | 720 | 1.0 | pass |
| `validate_render_effects4` | 1,920 | 6.8 | pass |
| `validate_render_effects5` | 1,190 | 5.6 | pass |
| `validate_render_effects6` | 1,000 | 1.6 | pass |
| `validate_render_effects7` | 596 | 1.8 | pass |
| `validate_render_effects9` | 304 | 1.0 | pass |
| `validate_session_party` | 200 | 0.7 | pass |
| `validate_skill_fx` | 660 | 0.7 | pass |
| `validate_terrain` | 583,500 | 447.6 | pass |
| `validate_terrain_remaining` | 2,147 | 4.6 | pass |
| `validate_viewport_monsters` | 1,963 | 10.7 | pass |
| `validate_world_particle_consumers` | 900 | 1.1 | pass |
| `validate_worlds_after6` | 7,300 | 70.3 | pass |
| `validate_worlds_d` | 2,400 | 3.7 | pass |
| `validate_worlds_f` | 1,818 | 0.5 | pass |
| `validate_worlds_fog` | 4,044 | 7.3 | pass |
| `validate_worlds_l` | 1,260 | 1.5 | pass |
| `validate_worlds_m` | 1,080 | 1.3 | pass |

The explicit world build immediately before the final after sweep passes in
0.282 s. The final default sweep takes
54.788 s; comparison takes 0.185 s.
**92/92 PNGs and 92/92 OBJECT/light dumps are byte-identical** to the retained original baseline.
Batch-103 world SHA-256: `fd290c2a2a7e02e26219c154bf0e8b40a695d3a090b08cd0bf6e0e8c6da8e393`; baseline:
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`. They are distinct. No before capture is rerun.

## Batch 104 integration and final default captures

Main `fb747e42` adds AUDIO-003 delivery and INNER-002's Elbeland/Swamp producers. Merge
`ac51b0dc0bc5e5b6e4a3af57230a622eca0ee45d` preserves all registry additions and expectations;
this lane still adds 17 registry lines and deletes zero. The five particle implementations and fourth-point
caller are unchanged. Root/world rebuilds pass in 14.629 /
5.384 s. Incoming selection takes
72.162 s for 67/227 rows; suite selection takes
73.872 s for 158/203 work items (151 native).
Final lane selection is 89/227 rows, 112.055 s.

Following the merge-check budget, the 37 overlapping/new lane rows below run again; the other
30 incoming rows reuse incoming-main evidence, since their compiled inputs are outside this
lane's diff. All 37 pass 276,735 reported cases with zero failures/errors/skips, in
436.190 s command, at `8b003afcd3003181cd822cba1435eab8a66a5680`.
No mutant target/check changed, so none is repeated.

| Validator | Reported cases | Wall seconds | Result |
|---|---:|---:|---|
| `validate_actor_recipes` | 1,669 | 103.4 | pass |
| `validate_audio_callers` | 5,528 | 6.0 | pass |
| `validate_audio_domains` | 2,544 | 27.2 | pass |
| `validate_audio_items` | 3,000 | 4.1 | pass |
| `validate_audio_objects` | 4,000 | 3.8 | pass |
| `validate_charsel_items` | 8,817 | 7.8 | pass |
| `validate_icarus_c2` | 8,400 | 22.8 | pass |
| `validate_inventory_fx` | 8,017 | 7.6 | pass |
| `validate_item_callers` | 6,013 | 1.2 | pass |
| `validate_meshdraw` | 14,619 | 97.5 | pass |
| `validate_model_edge` | 954 | 120.0 | pass |
| `validate_movement` | 6,614 | 76.4 | pass |
| `validate_render_effects16` | 424 | 3.7 | pass |
| `validate_render_effects17` | 618 | 7.8 | pass |
| `validate_render_effects18` | 540 | 1.3 | pass |
| `validate_render_effects19` | 400 | 1.0 | pass |
| `validate_render_effects24` | 226 | 3.0 | pass |
| `validate_render_effects25` | 202 | 9.5 | pass |
| `validate_render_effects26` | 348 | 9.4 | pass |
| `validate_render_effects28` | 630 | 1.9 | pass |
| `validate_render_worlds_a` | 9,000 | 14.9 | pass |
| `validate_worlds_121` | 4,000 | 5.9 | pass |
| `validate_worlds_after` | 13,424 | 14.7 | pass |
| `validate_worlds_after2` | 32,216 | 39.7 | pass |
| `validate_worlds_after3` | 10,212 | 10.0 | pass |
| `validate_worlds_after4` | 9,181 | 17.2 | pass |
| `validate_worlds_after5` | 6,000 | 12.4 | pass |
| `validate_worlds_after6` | 7,300 | 89.9 | pass |
| `validate_worlds_e` | 4,840 | 19.6 | pass |
| `validate_worlds_g3` | 4,000 | 5.4 | pass |
| `validate_worlds_inner` | 4,000 | 4.0 | pass |
| `validate_worlds_inner2` | 5,000 | 4.3 | pass |
| `validate_worlds_karutan` | 3,000 | 5.2 | pass |
| `validate_worlds_raklion` | 3,000 | 5.3 | pass |
| `validate_worlds_slots` | 18,999 | 33.3 | pass |
| `validate_worlds_slots2` | 33,000 | 37.3 | pass |
| `validate_worlds_slots3` | 36,000 | 37.1 | pass |

Portable delta, `run_test_suites.py --affected-since 7a21ba0c`,
455.088 s command:

`run_test_suites: 8 suites, 1653 tests, 1367 passed, 286 skipped, 0 failures, 0 errors; 0 failed suite(s); 386.4s wall, jobs=2`

**8d reduced:** the same nine changed/direct-consumer private modules pass 43/43,
zero skips, 37.266 s command. The shared-symbol scan finds no new
bitmap-count or owner-point consumer. The new audio/producer modules retain their incoming private proofs.

The explicit world build immediately before the final after sweep passes in
0.282 s. Capture takes 73.049 s;
comparison takes 0.262 s. No before capture is repeated.
Final world SHA-256: `090f76f0a1d54a78768347fe6f2ff045034f616de928ad6cbf212478370d0ac8`, distinct from the retained baseline
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.

Final default result: **91/92 PNGs and 90/92 OBJECT/light dumps identical**. All 44 unaffected views
are byte-identical. The only changed PNG is Elbeland's last frame, exactly 348 pixels, matching the
incoming INNER-002 result; both changed dumps are Elbeland's. Swamp PNGs/dumps remain identical.
Before batch 104, the lane's fully rebuilt particle/UI/actor/Muun/aura binary matched all 92 PNGs and 92
dumps as recorded above. The latest Elbeland difference belongs to the incoming producer, and is retained.
[Incoming capture domain and limits](RENDER-WORLDS-INNER-002.md#renders-and-byte-identity).

## Limits and next

This is the frozen inventory and bounded installed fixture, not a whole-client refusal census. Unknown or
stale native item owners, point indices outside 0..3 for the new ring, other owner classes and unavailable
poses remain outside the hosted domain. Native pools retain their caps and private RNG/counter phases.
The unavailable exact model path needs a separate asset-provenance resolution. New program admissions or
broader counter/owner contexts should extend the census rather than silently change its denominator.

No anti-cheat/protection analysis, live client, login/network/packet work, character-power feature or
client-memory writes occurred. This lane leaves actor files, item tables/generators, the README and installed applications untouched. The steward owns the combined gate and merge.

After the final push and single ready-prs entry, lane-owned scratch/renders and build outputs are removed,
then the worktree and local branch. Shared evidence, inputs, tools and validator cache remain. No new
private input is needed by a later lane.

## WIP, final UI integration

All batch-104 checks and the final capture comparison pass. Latest fetch brought ITEMS-UI-001,
main `626abce1`, merged cleanly. Its GFx source needs a final compiled-input overlap check. Particle
and point-consumer sources/checks are unchanged; no original baseline or completed mutant is repeated.
The ready result above describes the fully checked `fb747e42` inputs. Final publication waits for the
UI merge checks, updated status, staged audit, PR and ready entry. No ready-prs line exists.

## WIP checkpoint, 00:15 on 2026-11-12

Done: all 37 batch-104 overlap/new rows pass 276,735 reported cases, zero failures/errors/skips,
436.190 s. Final world rebuild is 0.282 s; after capture 73.049 s and comparison 0.262 s. Final result
against the retained original baseline is 91/92 PNGs / 90/92 dumps identical, with exactly the upstream
Elbeland last-frame 348 pixels and its two dumps changed. All 44 unaffected views are identical.
World SHA-256: `090f76f0a1d54a78768347fe6f2ff045034f616de928ad6cbf212478370d0ac8`.

Latest main `626abce1` (ITEMS-UI-001) merges cleanly at `b3f8495d8a531a7b9a52fe3842c214c1e75ab1b4`.
The only pending compiled input is incoming GFx UI code; particle/caller targets are unchanged. The
batch-105 build/selection controller is waiting for load > 14. The direct shared-symbol scan is unchanged.
The final status entries are prepared in the working tree, not yet staged for publication.

Left: complete the UI compiled-input overlap checks, final after-only replay, update the final handoff
for that merge, stage/audit, push/PR/link/ready entry/cleanup. Next step: inspect batch105-build-steps.json
and continue its controller; retain all completed proofs and baselines. finalize_104.py / final_audit.py
are prepared, and the former already generated the checked pre-UI result above. No ready-prs entry exists.
If still not PR-ready at 02:15, push WIP and stop by 02:30 as instructed.

## WIP checkpoint, 00:40 on 2026-11-12

Done: the ITEMS-UI-001 merge checks pass. Portable: 1,300 tests, 1,055 passed / 245 skipped, zero
failures/errors, 352.046 s command / 292.0 s runner. Private: 43/43, zero skips, 34.732 s. All seven
overlapping/new rows pass 21,793 reported cases, zero failures/errors/skips, 36.712 s. The final
UI1 replay takes 63.029 s / 0.334 s comparison and matches all 92 PNGs and 92 dumps from batch 104;
against the original baseline only the documented Elbeland difference remains. Binary SHA-256:
`4cc0912c77fc32a1b64998d99bd919ba802c3a9600851e22eb5e3b1699d8c4f3`.

Main then advanced to UI-WINDOWS-002 `0ccd5f44`, merged cleanly at
`56e469a548c69e3b79d6583f659b1c465829f5a4`. Only presentation/UI adapter code changes. Root/world builds
pass in 5.287 / 4.337 s; incoming validator selection is complete, 23.950 s. The port's particle/point
code and its consumers are unchanged. The new movie-count consumer is ui_windows2_host.c; its private
module plus the existing UI module are added to the nine port/shared modules for this final pass.

Left: final own selection, private modules, overlapping validators, explicit world build and after
replay/comparison; then finalize_105.py plus a final UI2 section, stage/audit, PR/link/ready entry/cleanup.
Incoming UI-only portable evidence is reused: the UI2 handoff records its passing portable and private
runs; this lane's full post-UI1 portable run above is complete. The final UI2 pass follows the merge
budget and covers the port's tests plus the changed shared movie-count consumer. No ready-prs line
exists. Next step: finish batch106_build.py and run batch106_checks.py. Cutoff remains 02:15 / 02:30.
