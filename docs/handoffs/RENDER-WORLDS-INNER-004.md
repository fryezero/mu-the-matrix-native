# RENDER-WORLDS-INNER-004

Branch `codex/render-worlds-inner-004`, from main `b7dfd2ed` (#387). PR-ready verified subset.
Implementation and checks by Codex, GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## Scope and what draws now

Crywolf 30 and Barracks/Refuge 41/42 execute their complete bounded inline visual producers. Kalima
24..29/36 executes seven verified types, and tower 39 executes thirteen nonzero types. Existing consumers
now receive the supported glows, fire, smoke and particles; missing particle/joint/effect consumers stay
counted. These are visual-leaf results, not completion of each world's create/move/event behavior.

Kalima types 15/29/32 need hero/water helper context and remain refused before inner RNG or object writes.
Tower type 0 needs its singleton sequence context and remains refused. Crywolf's event byte and tower's
hidden byte are fixed authored zero in production, with 0/1/2/255 instruction coverage. Worlds 46/98 have
no entry in the pinned 48-class, 57-registration static factory; dynamic context remains unverified and
each loaded object receives one counted refusal. No authoritative event model is inferred.

Kanturu 37/40 type 0x60's extra RGBA mesh now carries GREATER 0 through the object adapter and scene driver
to software, immediate GL and batched GL. GL flushes pending primitives before each reference change.
The driver restores GREATER 0.25 after the draw; default draws issue no new reference call. The old RGBA
refusal is removed. This adds no particle/joint consumer. Owned sources are
`reconstructed/objects/world_inner4_visual.*`, the existing object adapter and the small renderer seam.
[Per-type calls, guards and boundaries](../research/client-worlds-inner.md).

## Checks

All test/tool commands ran from the repository root. Heavy jobs used `nice -n 10`, make at most -j4 and
validator jobs 2, with load/free-memory/disk checks and resource waits. Private tests sourced
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Waits are excluded from walls. No full lane gate.

| Check | Result | Wall |
|---|---|---:|
| Starting root build | Pass | 30.64 s |
| Explicit starting world build | Pass; before hash below | 4.00 s |
| Small original comparison | Eight families, 1,600 cases, zero mismatches/stops | 11.60 s |
| Full original comparison and compiled producer mutants, `e262633e` | 8,000 cases, zero mismatches/stops; 42/42 mutants detected, minimum two cases, zero stopped | 174.51 s combined |
| Alpha production scene host | 15 cases across software/immediate/batched GL, including restoration | 0.82 s |
| Four compiled alpha mutants | 4/4 detected, including missing batch barrier | 2.05 s |
| Root build after implementation | Pass | 10.00 s |
| Affected validators, `e262633e2895d8457d4423da7daa2f21d4e46276` | 89/89 pass; 1,080,348 reported cases plus WORLDS-O, which has no total; zero failures/errors/skips | 883.69 s including selection |
| Affected portable suites, `c19a8b9b` | 1,720 tests: 1,407 passed / 313 expected skips; zero failures/errors | 507.38 s including selection; 399.0 s runner |
| Private focused modules | 15/15 pass, no skips | 81.61 s |
| Explicit after-world build | Pass; distinct after hash below | 0.27 s |
| Before default tours and first authored layouts | Pass | 65.51 s |
| Before reference/default-clock and captured-clock views | Pass | 11.24 s |
| Before type-0x60 proofs | Pass | 2.53 s |
| After tours, references and initial proofs | 65 views pass | 116.59 s |
| Separate verified-type Kalima proof, before + after | 14 views pass | 12.97 s |
| Final render analysis, before elevated proof | Pass | 7.82 s |
| Elevated Kalima proof, before + after | 14 views pass | 12.67 s |
| Elevated-proof explicit world build / analysis | Pass; same after hash / scalar comparison | 0.28 s / 0.73 s |
| Final documentation consumers | 36 tests: 35 passed / one expected skip, zero failures/errors | 10.87 s |
| Final repository audit | 2,273 files, zero rejected | 25.20 s |
| Initial repository audit | 2,266 files, zero rejected | 19.96 s |

**8d reduced:** private native selection is 173 work items (72.17 s), above the 40-item cap. The changed
`test_native_worlds_inner`, new `test_native_worlds_inner4`, shared-symbol consumer
`test_native_item_textures` and producer `test_worlds_inner4` ran privately. Their 15 tests include 1,600
small original cases, static registry absence, missing models/bones, authored byte gates, hidden/scale
writes, explicit new joint refusals, installed texture survey and the alpha scene. The alpha fixture uses
0/32/63/64/255 alpha and default/zero/restored-default passes: zero stays rejected, low nonzero alpha draws
only at reference zero, GL immediate/batched images match exactly, all backends restore 0.25.

Portable selection retains 167 permitted work items. Only `native/tests/test_native_app.py` was excluded:
its setup builds/signs a temporary app bundle, and the owner's lane brief prohibits packaging this session.
No packaging occurred. This is an explicit limit of the portable run. All 89 validator rows, including
conservative fallbacks, were retained; selection alone took 72.16 s. The shared-symbol search covers the
appended draw-option/backend fields. No existing field, table size or constant changed.

The full comparison and first producer mutant completed in 11.52 s. The next mutant failed compilation
because removing its model gate made a parameter unused under -Werror. The mutation now retains a dummy
use; only the remaining 41 variants ran, 162.99 s. No completed baseline/mutant was repeated. Early fixture
and comparator failures (software matrices, particle pair/RNG ordering, positional backend initializers)
were fixed before the reported final checks. No unresolved check failure remains.

## Renders and fidelity

Both sweep binaries were explicitly built with `make -C native -j4 world`:

- Before: `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- After: `fb8ede43c07ea4906b5acff406734068cac3bceaea28dc1289522b752e38e998`.

The one default identity sweep uses the existing 14-view October tour and 32-view acquisition tour,
640x400, 25 steps, frames 0/24, without draw-all. It preserves 90/92 PNGs, 92/92 OBJECT/light dumps and
45/46 normalized reports. All **45 unaffected views are byte-identical**. Only Kanturu 37 changes:
7,686 last-frame pixels, mean absolute RGB delta 0.295926/255, from the restored extra RGBA mesh.
Reports exclude only output path keys `png` and `fidelity_dump`. Dump comparison is binary equality.

Affected references use 1722x1048 at default and captured clocks. Kanturu 37 changes 52,781 / 52,775
last-frame pixels, mean RGB deltas 0.287482 / 0.286576. Remain 38 and Kanturu 40 keep identical PNGs,
dumps and reports. **Remain's reference error stays 6.190 -> 6.190** at default and
**6.192 -> 6.192** at captured clock; share-off stays 0.0568 at both. The seam does not improve this
INNER-003 residual. Original reference processing produced scalar/object/light comparisons only; no
original-name image was copied into the proofs.

Authored grids use 1280x800, 25 steps, frames 0/24, draw-all, zero angles/scale 1, positions
`(12650 + column*150, 12750 + row*150, 223.5)`, hero tile 128,128. Kalima's seven aliases share folder 25.
They are authored contexts, not original placements or temporal fidelity acceptance. Final-frame totals:

| World | Types in initial grid | Particle created / draw requests | Sprites created / draw requests | Consumer refusals | Changed pixels / mean RGB delta |
|---|---|---:|---:|---:|---:|
| 24..29/36, each | 12,35..40 plus refused 15/29/32 | 50 / 50 | 25 / 1 | 66 | 0 / 0 |
| 30 | 0,0x29,0x34,0x36 | 13 / 13 | 0 / 0 | 50 | 2,463 / 0.007870 |
| 39 | 1,5,11,0x20,0x2e..0x32,0x34..0x36,0x4a,0 | 40 / 40 | 75 / 3 | 44 | 721,296 / 22.552438 |
| 41 | 2,3,5,6,0x3a..0x3c,0x55,0x58..0x5a,0x5c | 34 / 33 | 0 / 0 | 33 | 390,957 / 10.317991 |
| 42 | Same as 41 | 16 / 15 | 0 / 0 | 37 | 133,543 / 0.226203 |

Draw-request counts do not prove visible fragments. Kalima's initial and verified-types-only grids both
produce zero changed pixels; the water surface obscures the low grid. The latter removes the three
refused helper types, still loads all seven models, creates 50 particles/25 sprites and records 78 consumer
refusals per world. Its object writes differ, while PNGs remain identical. It is not a claimed visual gain.

A separate elevated proof uses only the seven verified types at **authored Z=500**, with the same X/Y,
angles, scale, tile and clock. All seven aliases change **46,966 last-frame pixels**, mean RGB delta
**2.235549/255**, and retain light-dump equality while object scale/hidden writes differ. The same
50 particles/25 sprites and 78 consumer refusals are recorded. The after image visibly contains the blue
Bone02 glow, blue plume and white spray. Elevation establishes a readable authored proof; it is not an
original-placement claim.

Initial grids load all 10 Kalima, four Crywolf and fourteen tower models. Barracks loads 9/12 models,
Refuge 8/12: three/four missing assets remain. Their existing create refusals are 12 per grid; move
refusals are 216/192. Crywolf retains four create and 96 move refusals; tower fourteen/336; each initial
Kalima grid ten/240. These are outside the visual-leaf scope. Tower also counts its refused type 0;
Kalima counts the three helper types once per prepared object/frame.

A separate real-model type-0x60 proof uses the captured Kanturu-37 object at
`(1684.456665,22354.09375,215.537598)`, hero tile 17,224. The newly admitted translucent pass changes
80,733 last-frame pixels, mean RGB delta 0.570070; dumps remain identical, visual refusals drop 25 -> 0.
World 40 has no captured type-0x60 object; the authored counterpart at 12850,12850,223.5 loads Object97
but changes zero pixels in this view. Its draw is no longer refused, without a claimed visible gain.

Proof commands set `MU_GFX_PUBLIC_DEMO=1` only on render subprocesses and `--hero-name Preview`.
Individual after images for 30/39/41/42 and the 37 alpha fixture were visually inspected. Kalima's low and elevated
verified-type images were inspected; the distinct results are recorded above. No new original
input/capture was acquired; no live client was used.

## Limits and next

| World / boundary | State and remaining dependency |
|---|---|
| Crywolf 30 | Complete bounded visual leaf `0x00d8e640..0x00d8ea2c`; event getter `0x00d8b3e3` reads `0x01ec8ee7`, fixed authored zero in production |
| Barracks/Refuge 41/42 | Complete shared visual leaf `0x00d5404b..0x00d54e48`; getter `0x00d53c8f`, tests `0x00d53d11` / `0x00d53d32`; no event authority |
| Kalima 24..29/36 | Seven types verified at `0x00def747`, guard `0x009b0418`; 15/29/32 need hero motion `0x00dfa988` and water getter `0x00deeb4e` |
| Tower 39 | Thirteen nonzero types verified at `0x00e84941`, guard `0x00e84513`; type 0 needs singleton +0x78 and nested `0x00e8d888` |
| 46/98 | Common `0x017fcb5c..0x017fccbc`; manager `0x00ea2dc1`, slot 0x34 at `0x00ea2eba`; absent from static factory `0x00ea488e..0x00ea5629`, dynamic coverage unverified |
| Missing consumers | Existing 0x801c/3,4,7; 0x7f89/7,10,26; 0x7f42/7; 0x802a/1; joints 0x7f7d/8,9,10 remain counted, owned by EFFECTS-031. Newly requested joints 0x7fd5/4, 0x7f7d/11, 0x7f7c/19 also remain counted |
| Sound | Kalima decimal types 37/38 sound boundary `0x00a6ac96(0x1d6,0,0)` is visual-only in the comparator; AUDIO-004 owns sound delivery |
| Fidelity | Authored inputs do not prove event behavior, original placement or original/native temporal equivalence; Remain residual is unchanged |

## Integration and cleanup

Latest `origin/main` is `b7dfd2ed`; merge is a no-op. The 89-row validator head is `e262633e`; only a stale
source comment and documentation changed afterward. Portable tests include that comment cleanup at
`c19a8b9b`. Checkpoints were committed/pushed with WIP handoffs throughout the lane. All final docs and
PR text precede the ready-prs entry. No pushes follow that entry; merge belongs to the steward.

No future input is retained. Lane-owned scratch, renders, build outputs, worktree and local branch are
removed after queuing; original captures, shared validator cache and the remote branch remain. Private
`tools/python`, `evidence` and `input` symlinks are never committed. No README, item/actor/combat/UI, installed
app or packaging changes.

## Steward validators

All rows below ran at `e262633e2895d8457d4423da7daa2f21d4e46276` with canonical private env, jobs 2, cache on and no mutants.
No steward mutants requested; the 42 producer and four alpha negatives are complete.

| Validator | Reported cases | Wall s |
|---|---:|---:|
| `validate_actor_composites` | 1427 | 6.5 |
| `validate_actor_recipes` | 1669 | 93.3 |
| `validate_app_polish1` | 752 | 28.8 |
| `validate_app_polish2` | 1028 | 4.0 |
| `validate_app_polish4` | 10485 | 40.3 |
| `validate_audio_callers` | 5528 | 6.9 |
| `validate_audio_domains` | 2544 | 28.9 |
| `validate_audio_items` | 3000 | 5.4 |
| `validate_audio_objects` | 4000 | 2.4 |
| `validate_charsel_items` | 8817 | 6.0 |
| `validate_charsel_world` | 1200 | 2.7 |
| `validate_icarus` | 5240 | 36.4 |
| `validate_icarus_c2` | 8400 | 22.9 |
| `validate_inventory_fx` | 8017 | 5.9 |
| `validate_item_callers` | 6013 | 1.0 |
| `validate_items_ui` | 8517 | 9.0 |
| `validate_login_world` | 1200 | 2.8 |
| `validate_meshdraw` | 14619 | 68.2 |
| `validate_model_edge` | 954 | 130.7 |
| `validate_model_light` | 1433 | 5.8 |
| `validate_movement` | 6614 | 51.5 |
| `validate_object_render` | 1984 | 2.6 |
| `validate_path` | 4719 | 28.0 |
| `validate_render_effects10` | 154 | 0.5 |
| `validate_render_effects11` | 176 | 0.4 |
| `validate_render_effects12` | 64 | 0.4 |
| `validate_render_effects13` | 180 | 1.0 |
| `validate_render_effects14` | 660 | 1.0 |
| `validate_render_effects15` | 509 | 0.6 |
| `validate_render_effects16` | 424 | 2.5 |
| `validate_render_effects17` | 618 | 5.7 |
| `validate_render_effects18` | 540 | 0.9 |
| `validate_render_effects19` | 400 | 0.7 |
| `validate_render_effects20` | 148 | 0.2 |
| `validate_render_effects21` | 267 | 0.2 |
| `validate_render_effects22` | 202 | 5.3 |
| `validate_render_effects23` | 1174 | 6.3 |
| `validate_render_effects24` | 226 | 1.9 |
| `validate_render_effects25` | 202 | 7.5 |
| `validate_render_effects26` | 348 | 7.7 |
| `validate_render_effects27` | 424 | 1.0 |
| `validate_render_effects28` | 630 | 1.4 |
| `validate_render_effects7` | 596 | 2.1 |
| `validate_render_effects9` | 304 | 1.1 |
| `validate_render_worlds_a` | 9000 | 12.7 |
| `validate_terrain` | 583500 | 430.9 |
| `validate_terrain_remaining` | 2147 | 4.4 |
| `validate_world_fidelity` | 200 | 0.2 |
| `validate_world_light_name` | 304 | 0.5 |
| `validate_world_tile_folder` | 5700 | 42.2 |
| `validate_worlds_121` | 4000 | 3.1 |
| `validate_worlds_after` | 13424 | 16.8 |
| `validate_worlds_after2` | 32216 | 38.4 |
| `validate_worlds_after3` | 10212 | 9.8 |
| `validate_worlds_after4` | 9181 | 15.7 |
| `validate_worlds_after5` | 6000 | 11.1 |
| `validate_worlds_after6` | 7300 | 78.4 |
| `validate_worlds_b` | 4000 | 3.5 |
| `validate_worlds_d` | 2400 | 4.2 |
| `validate_worlds_e` | 4840 | 18.1 |
| `validate_worlds_f` | 1818 | 0.5 |
| `validate_worlds_fog` | 4044 | 4.8 |
| `validate_worlds_g` | 6000 | 4.4 |
| `validate_worlds_g2` | 2657 | 6.2 |
| `validate_worlds_g3` | 4000 | 13.1 |
| `validate_worlds_h` | 6000 | 4.3 |
| `validate_worlds_i` | 6000 | 4.7 |
| `validate_worlds_inner` | 4000 | 2.1 |
| `validate_worlds_inner2` | 5000 | 2.6 |
| `validate_worlds_inner3` | 8000 | 4.7 |
| `validate_worlds_inner4` | 8000 | 4.4 |
| `validate_worlds_j` | 6000 | 4.6 |
| `validate_worlds_k` | 6000 | 5.8 |
| `validate_worlds_karutan` | 3000 | 2.8 |
| `validate_worlds_n` | 13000 | 9.9 |
| `validate_worlds_o` | not reported | 9.7 |
| `validate_worlds_p` | 10000 | 10.0 |
| `validate_worlds_p2` | 6000 | 5.2 |
| `validate_worlds_q` | 11000 | 13.5 |
| `validate_worlds_q2` | 4000 | 9.4 |
| `validate_worlds_r` | 12000 | 8.9 |
| `validate_worlds_r2` | 9000 | 7.6 |
| `validate_worlds_raklion` | 3000 | 2.4 |
| `validate_worlds_s` | 11000 | 10.2 |
| `validate_worlds_s2` | 10000 | 9.6 |
| `validate_worlds_s3` | 22000 | 15.7 |
| `validate_worlds_slots` | 18999 | 15.2 |
| `validate_worlds_slots2` | 33000 | 21.4 |
| `validate_worlds_slots3` | 36000 | 21.8 |

Steward validators: validate_actor_composites,validate_actor_recipes,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_charsel_items,validate_charsel_world,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_path,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects27,validate_render_effects28,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_terrain,validate_terrain_remaining,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3

Env: source `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the repo root. This supplies MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, native data, snapshots, language, graphics library and the original cache. Private inputs are read-only.
