# RENDER-WORLDS-INNER-005

Branch `codex/render-worlds-inner-005`, from main `6900914e`. Implementation by Codex,
GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## WIP

Done: classified every active Kalima/tower type; added Kalima 15/29/32 and tower 0/sequence producers.
Four original families pass 4,000 cases, zero mismatches/stops. All 37 compiled mutants are caught,
minimum 18 detections, zero stops. Private focused checks pass 13/13. All 75 affected validators pass,
1,136,043 reported cases plus WORLDS-O, zero failures/errors/skips, at code commit
`607adef64a6634141aa2da64f8ed6da96443d9de`. Portable checks pass 1,716 tests, 1,392 passed / 324 expected
skips, zero failures/errors. Packaging module `native/tests/test_native_app.py` is excluded. Private native
selection is 162 items, so **8d reduced** applies; the changed host and focused original/context modules
ran privately. No existing shared struct field, table size or constant changed.

Both world binaries were explicitly built in this lane's tree before/after source changes. Before SHA-256
`1a7b20b52387fb7010574d45db4a7e99415ee3b06c7110da28bdc2877c25e484`; after
`f55dd0a01cb079c2f25a27e09e17b3575bb5be32cc6f75f5727980a54d47187c`.
All 55 baseline views rendered successfully. The after renders are held by the resource guard. Main is
still `6900914e`; latest-main integration is a no-op. No lane-owned producer/adapter source changed after `607adef6`.

Left: render the prepared after manifests, run the paired analysis, inspect the affected images, finalize
status/PR/ready line and clean up. No full lane gate. No claim of completed render validation yet.

Next step, from this repo root with canonical private-env sourced: run the lane scratch `render.py after`
through `run.py` with MU_GFX_PUBLIC_DEMO=1, then `analyze_renders.py`. These local files are resume inputs
until PR-ready. Do not regenerate the successful before renders or repeat the completed mutants.

## Scope and limits

[Per-type classification, addresses and context](../research/client-worlds-inner.md).
Production uses fixed authored idle/null-water Kalima context and inactive tower context. Active hero,
water sampler, sequence and timer inputs are instruction-compared authored fixtures. No event controller,
water simulation or live fidelity is inferred. Missing bones and particle/effect consumers remain counted.
No consumers are added, and no installed app, packaging, README, item/actor/combat/UI work occurs.

## Check walls

| Check | Result | Wall s |
|---|---|---:|
| Root build | Pass | 11.18 |
| Four original families and 37 compiled mutants | 4,000 cases, all controls detected | 225.29 |
| Private focused modules | 13 tests, no skips | 6.45 |
| Affected validator selection | 75 rows including fallbacks | 88.59 |
| All affected validators | 75 pass | 853.25 |
| Portable selection, wrapper startup | 169 selected, no tests ran on missing log directory | 65.04 |
| Corrected portable run | 168 permitted work items, 1,716 tests | 385.80 |
| Initial repository audit | 2,303 files, zero rejected | 38.74 |
| Explicit before/after world builds | Pass | 14.59 / 0.20 |
| Baseline renders | 55 views | 87.67 |

One loop-count mutant anchor initially matched 10 and 100. It was narrowed and only unfinished variants
resumed. A local portable wrapper initially lacked its output directory; no test ran, and the saved
selection was reused after fixing it. No unresolved source/test failure remains. Resource waits are
excluded from walls. Final heavy commands use a conditional load/memory/disk guard; an early producer
compile began during a load spike before that conditional guard replaced the shell sequence.

## Steward validators

All rows below ran at `607adef64a6634141aa2da64f8ed6da96443d9de`, canonical private env, jobs 2,
cache on, no mutants. No steward mutants requested. The initial 75-row result predates the integration described below.

| Validator | Reported cases | Wall s |
|---|---:|---:|
| `validate_actor_composites` | 1427 | 9.4 |
| `validate_actor_monsters` | 1437 | 34.5 |
| `validate_actor_recipes` | 1669 | 108.2 |
| `validate_audio_callers` | 5528 | 5.0 |
| `validate_audio_domains` | 2544 | 20.4 |
| `validate_audio_items` | 3000 | 2.8 |
| `validate_audio_objects` | 4000 | 5.0 |
| `validate_audio_objects4` | 10093 | 4.5 |
| `validate_charsel_items` | 8817 | 7.9 |
| `validate_charsel_world` | 1200 | 2.8 |
| `validate_icarus` | 5240 | 47.9 |
| `validate_icarus_c2` | 8400 | 13.9 |
| `validate_inventory_fx` | 8017 | 7.4 |
| `validate_item_callers` | 6013 | 1.3 |
| `validate_items_ui` | 8517 | 10.2 |
| `validate_login_world` | 1200 | 2.9 |
| `validate_meshdraw` | 14619 | 94.8 |
| `validate_model_edge` | 954 | 166.9 |
| `validate_model_light` | 1433 | 7.6 |
| `validate_movement` | 6614 | 69.2 |
| `validate_object_render` | 1984 | 4.3 |
| `validate_render_effects16` | 424 | 4.1 |
| `validate_render_effects17` | 618 | 8.0 |
| `validate_render_effects18` | 540 | 1.4 |
| `validate_render_effects19` | 400 | 1.0 |
| `validate_render_effects24` | 226 | 2.8 |
| `validate_render_effects25` | 202 | 11.7 |
| `validate_render_effects26` | 348 | 10.4 |
| `validate_render_effects28` | 630 | 2.2 |
| `validate_render_effects31` | 66051 | 198.0 |
| `validate_render_worlds_a` | 9000 | 14.5 |
| `validate_terrain` | 583500 | 332.8 |
| `validate_terrain_remaining` | 2147 | 5.2 |
| `validate_world_fidelity` | 200 | 0.4 |
| `validate_world_light_name` | 304 | 0.3 |
| `validate_world_tile_folder` | 5700 | 30.4 |
| `validate_worlds_121` | 4000 | 4.9 |
| `validate_worlds_after` | 13424 | 10.5 |
| `validate_worlds_after2` | 32216 | 20.6 |
| `validate_worlds_after3` | 10212 | 5.6 |
| `validate_worlds_after4` | 9181 | 9.7 |
| `validate_worlds_after5` | 6000 | 7.1 |
| `validate_worlds_after6` | 7300 | 53.2 |
| `validate_worlds_b` | 4000 | 2.2 |
| `validate_worlds_d` | 2400 | 2.7 |
| `validate_worlds_e` | 4840 | 12.6 |
| `validate_worlds_f` | 1818 | 0.4 |
| `validate_worlds_g` | 6000 | 2.4 |
| `validate_worlds_g2` | 2657 | 4.4 |
| `validate_worlds_g3` | 4000 | 3.3 |
| `validate_worlds_h` | 6000 | 2.4 |
| `validate_worlds_i` | 6000 | 2.7 |
| `validate_worlds_inner` | 4000 | 4.7 |
| `validate_worlds_inner2` | 5000 | 5.6 |
| `validate_worlds_inner3` | 8000 | 8.0 |
| `validate_worlds_inner4` | 8000 | 4.2 |
| `validate_worlds_inner5` | 4000 | 4.1 |
| `validate_worlds_j` | 6000 | 2.5 |
| `validate_worlds_k` | 6000 | 2.9 |
| `validate_worlds_karutan` | 3000 | 3.9 |
| `validate_worlds_n` | 13000 | 10.5 |
| `validate_worlds_o` | not reported | 5.3 |
| `validate_worlds_p` | 10000 | 7.1 |
| `validate_worlds_p2` | 6000 | 3.1 |
| `validate_worlds_q` | 11000 | 7.2 |
| `validate_worlds_q2` | 4000 | 4.4 |
| `validate_worlds_r` | 12000 | 8.8 |
| `validate_worlds_r2` | 9000 | 4.3 |
| `validate_worlds_raklion` | 3000 | 3.9 |
| `validate_worlds_s` | 11000 | 7.7 |
| `validate_worlds_s2` | 10000 | 6.4 |
| `validate_worlds_s3` | 22000 | 18.0 |
| `validate_worlds_slots` | 18999 | 17.1 |
| `validate_worlds_slots2` | 33000 | 30.1 |
| `validate_worlds_slots3` | 36000 | 30.6 |

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_recipes,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_audio_objects4,validate_charsel_items,validate_charsel_world,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects28,validate_render_effects31,validate_render_worlds_a,validate_terrain,validate_terrain_remaining,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_inner5,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

Env: source `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the repo root. Original inputs and Native Data are read-only.

## Main integration WIP

Pinned integration base `c7a6679db4ab24d2ee4af67ebeda9f903727f8f2` contains batch-115 ACTORS-006 #396,
EFFECTS-032 #394 and MUUN-004 #397. The world producer, adapter and production host are unchanged.
The append conflict preserves all five independent validator entries; repository-Python TOML parsing
passes all 245 rows. An intermediate local merge commit retained markers after system Python lacked
tomllib and the shell continued; correction `2fe33f74` removes them before this push. No marker remains.

Integration root build passes in 11.96 s. The 81.58 s post-build selection yields 76 final lane rows and
31 overlaps/new rows to replay, including the new actor-plain row. The replay is running at
`2fe33f744e5233aa201a90f797879b131189e005`; actor-plain, terrain, EFFECTS-031 and model-edge have passed.
No completed world-producer mutant repeats. Incoming native/core headers require the affected portable
and private modules, still pending. The pinned base is the integration cutoff for this lane.

Next: finish `integration-validators`, run prepared `portable_integration.py`, then private incoming
modules plus the world host, explicit world build and `render.py after` / `analyze_renders.py`. The
premerge ledger stores hashes/reports, so after outputs can be overwritten without duplicating renders.
Do not rerender the successful before baseline.

## Pre-integration render results

All 55 after views pass in 104.07 s; analysis takes 1.26 s. Default draws, no draw-all, 640x400,
25 steps sampled at 0/24: all 46 views, 92 PNGs, 92 OBJECT/light dumps and 46 normalized reports
are byte-identical. Normalization drops only png/fidelity_dump path keys. Full-resolution Remain
is 6.190 -> 6.190, share-off 0.0568 -> 0.0568.

Authored proofs, 1280x800, draw-all, 25 steps, hero tile 128,128, zero angles, scale 1, Z=500:
Kalima 15/29/32 at (12650+column*150,12750,500), folder 25 shared by all seven aliases; tower type 0
at (12650,12750,500), folder 40. All three Kalima models and the tower model load. Kalima aliases
all create 25 sprites and draw one last-frame sprite; context refusals 75 -> 0, three create / 72 move
refusals unchanged. Their frame-0/24 differences are 1,728 / 2,174 pixels, mean RGB 0.024714 / 0.090989.
The Bone02 glow is visible. Idle/null-water context writes Z=180 after the sprite request.

Tower's fixed inactive context changes hidden mesh to 0. Frame 0 is identical; frame 24 changes
220,412 pixels, mean RGB 6.547347. Context refusals 25 -> 0, one create / 24 move refusals unchanged.
This animation sample emits no puff and no new particle, joint or effect pixel gain is claimed.
The synthetic production host covers frame 6 and counted missing bone 34. All proof light dumps are
identical; OBJECT dumps differ through the intended position/hidden writes. Kalima frame 0 and tower
frame 24 were visually inspected. These are authored contexts, not original placements or event fidelity.

## Integration validation complete, final replay pending

All 31 selected integration validators pass at 2fe33f74 in 855.29 s, 778,723 reported cases, zero
failures/errors/skips. The final 76-row result consists of these 31 refreshed rows and 45 unchanged rows
from 607adef6. No new mutants run. Post-merge portable checks pass 1,898 tests, 1,554 passed / 344
expected skips, zero failures/errors, 520.47 s including selection, 404.2 s runner. There are 185 selected
work items and 184 permitted after excluding the same app-packaging module. The private native count is
170, so 8d reduced applies. Incoming actor-plain, skill32, Muun riding/special/secondary and the world
host pass all 25 private tests, no skips, in 289.36 s.

Remaining: the guard held the final explicit world target at load 16.42. After cooldown, run
`make -C native -j4 world`, save its SHA-256 into the prepared final-hashes JSON, replay `render.py after`
under the render-only public-demo environment, then run `final_analysis.py`. The saved 220-file hash
ledger / 55 reports allow overwrite of the old after outputs. `finalize_docs.py` is prepared but must
only run after the replay succeeds. Finish status lines, documentation consumers/audit, PR, ready line
and cleanup. No source/test failure remains, and no render is claimed for the integrated binary yet.
