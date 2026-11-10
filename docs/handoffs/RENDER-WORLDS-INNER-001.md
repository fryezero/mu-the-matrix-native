# RENDER-WORLDS-INNER-001

Branch `codex/render-worlds-inner-001`, PR #365. Started at `ff8e0543`; integrated actor main `a2ad8814`,
docs `9d6ce467`, ITEMS-002X `3732f82a` and AUDIO-002G `807d757c`. Current code is `bff13a35`.
The final affected-world replay and repository audit are pending; no ready line has been written.

## Scope and what draws now

- Kanturu worlds 37/40, complete call producer `0x00e75089..0x00e760aa`: the existing flames, the clock-windowed
  0x193/3 effect request and hidden-mesh write, owned smoke/particle requests, bone flares, lightning requests,
  mesh 3's 0x42/Chrome01 passes and mesh 0's scrolling pass. The adapter serves existing consumers and RGB
  mesh passes, with explicit refusals below.
- Blood Castle worlds 11..17 and 52, inline switch `0x017fc023..0x017fc71f` reached through RenderObjectVisual
  `0x017f9758`: types 0x0b and 0x0d draw seven named-bone flares and one named-bone flare; 0x2a records the two
  RNG rolls, counter +0xb4 writes and particle requests. World 0x34 was intended, not object type 0x34, as the
  owner clarified. No event-state model is added.
- Extra meshes follow the existing base body through the first-pass list. Hidden objects can draw accepted
  inline meshes; refused meshes and StreamMesh-only events retain the hidden-object skip. Missing bones are
  refused, and the alpha guard checks the mesh's mapped texture slot.

[Research, exact per-type calls, provenance and limits](../research/client-worlds-inner.md).
Owned implementation: `reconstructed/objects/world_inner_visual.*` and `native/core/mu_objects_runtime.c`.
Makefile/registry edits add lines only. No item/effect/actor consumer, live-client or installed-app edits.

## Checks

Commands run from the repo root, with `nice -n 10`, at most `make -j4` and validator `--jobs 2`.
Resource waits are excluded from individual check walls. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Check | Result | Wall |
|---|---|---:|
| Full original call comparison | 4 families, 4,000 cases, zero mismatches/stops | 2.09 s |
| New validator mutants, once at `2145b9b7` | 4,000 cases, zero mismatches/stops; 33/33 compiled mutants detected, minimum eight detections | 156.03 s |
| Initial affected validators, `2145b9b7` | 61/61 pass; 1,008,213 reported cases; worlds_o's row has no case field | 685.61 s |
| Adapter guard fixes, `0e96c91a` | 14/14 selected rows pass, 623,786 cases | 466.33 s |
| ITEMS-002X integration, `36fcf252` | 15/15 overlapping rows pass, 58,258 cases | 156.87 s |
| AUDIO-002G integration, `bff13a35` | 15/15 overlapping rows pass, 58,258 cases | 239.10 s |
| Affected portable suites, `bc4c8f0b` | 1,598 tests, 1,328 passed / 270 skipped, zero failures/errors | 446.11 s including selection; 328.0 s test wall |
| Latest private native renderchar module | 24/24 passed, zero skips | 12.79 s |
| Latest private production worlds host | 1/1 passed, zero skips | 1.61 s |
| New object module with private env | 3/3 passed, including 800 original instruction cases | 0.51 s |
| Latest portable renderchar suite | 111 tests, 87 passed / 24 private skips | 0.63 s |
| Latest `make -j4` | Pass after audio merge | 16.99 s |

**8d reduced:** the full affected native selection exceeds 40 items, 143 measured before the later UI addition.
Only the lane's new host and the changed shared-renderchar native module are run privately. No full lane gate.
No shared struct/table size was changed by this lane; 6b's new symbols are confined to the producer, adapter and
new tests. Existing outer RNG/flame entry points are unchanged.

Two adapter negatives were reproduced before correction: hidden RGBA refusal bypassed the skip, 1.07 s, and
an assumed texture slot 0 missed mapped RGBA, 1.13 s. The expanded host covers both and accepted hidden RGB/Chrome
passes. The producer and all mutant targets have been unchanged since `2145b9b7`.

The initial late-main selection was too broad. Its 53 rows were corrected to the intersection of this lane's
61 current `--affected origin/main` rows with the merge changes, retaining all fallbacks: 15. The other 38
item-only rows reuse the incoming [ITEMS-002X evidence](RENDER-ITEMS-002X.md). `31e03afb..3732f82a` changes docs
only; the incoming compiled item sources are unchanged. The audio merge similarly selects 26 overall and 15
within this lane. Interrupted preliminary runs are not counted as passing evidence.

## Steward validators

Columns below are runs at `2145b9b7`, `0e96c91a`, `36fcf252`, and `bff13a35`, respectively. Blank cells mean the row
was pruned for that change. Counts are from each row's last run. No steward mutants requested; the new row's
33 mutants are complete and its producer inputs are unchanged. Other rows ran without mutants.

| Validator | Last reported cases | Initial s | Guard fixes s | Item merge s | Audio merge s |
|---|---:|---:|---:|---:|---:|
| `validate_charsel_world` | 1200 | 2.2 |  |  |  |
| `validate_login_world` | 1200 | 2.3 |  |  |  |
| `validate_meshdraw` | 14619 | 66.1 | 90.1 | 61.9 | 89.5 |
| `validate_model_edge` | 954 | 128.2 | 180.1 | 114.7 | 172.2 |
| `validate_model_light` | 1433 | 5.6 | 4.5 |  |  |
| `validate_movement` | 6614 | 56.2 | 84.1 | 45.7 | 74.3 |
| `validate_object_render` | 1984 | 2.7 |  |  |  |
| `validate_terrain` | 583500 | 393.0 | 466.2 |  |  |
| `validate_world_fidelity` | 200 | 0.2 |  |  |  |
| `validate_terrain_remaining` | 2147 | 3.8 | 3.9 |  |  |
| `validate_render_worlds_a` | 9000 | 9.6 |  |  |  |
| `validate_icarus` | 5240 | 38.3 |  |  |  |
| `validate_worlds_b` | 4000 | 2.1 |  |  |  |
| `validate_icarus_c2` | 8400 | 14.8 |  | 14.4 | 25.6 |
| `validate_worlds_d` | 2400 | 2.9 |  |  |  |
| `validate_worlds_e` | 4840 | 15.3 |  |  |  |
| `validate_worlds_f` | 1818 | 0.5 | 0.4 |  |  |
| `validate_worlds_g` | 6000 | 7.3 |  |  |  |
| `validate_audio_callers` | 5528 | 5.2 | 5.1 | 5.5 | 6.5 |
| `validate_worlds_h` | 6000 | 2.6 |  |  |  |
| `validate_worlds_i` | 6000 | 2.8 |  |  |  |
| `validate_audio_domains` | 2544 | 24.4 | 21.5 | 20.1 | 32.2 |
| `validate_worlds_j` | 6000 | 5.6 |  |  |  |
| `validate_worlds_k` | 6000 | 5.0 |  |  |  |
| `validate_audio_items` | 3000 | 4.4 | 2.5 | 2.4 | 5.7 |
| `validate_worlds_o` | not reported | 6.3 |  |  |  |
| `validate_worlds_n` | 13000 | 10.8 |  |  |  |
| `validate_worlds_p` | 10000 | 9.4 |  |  |  |
| `validate_worlds_r` | 12000 | 11.3 |  |  |  |
| `validate_world_tile_folder` | 5700 | 34.4 |  |  |  |
| `validate_worlds_g2` | 2657 | 6.6 |  |  |  |
| `validate_world_light_name` | 304 | 0.4 |  |  |  |
| `validate_worlds_p2` | 6000 | 4.9 |  |  |  |
| `validate_worlds_r2` | 9000 | 7.1 |  |  |  |
| `validate_worlds_q` | 11000 | 10.2 |  |  |  |
| `validate_worlds_q2` | 4000 | 5.5 |  |  |  |
| `validate_worlds_after` | 13424 | 13.7 |  |  |  |
| `validate_worlds_g3` | 4000 | 4.7 |  |  |  |
| `validate_worlds_after2` | 32216 | 35.8 |  |  |  |
| `validate_worlds_after3` | 10212 | 10.3 |  |  |  |
| `validate_worlds_after4` | 9181 | 15.2 |  |  |  |
| `validate_worlds_after5` | 6000 | 12.0 |  |  |  |
| `validate_worlds_after6` | 7300 | 59.0 |  |  |  |
| `validate_worlds_s` | 11000 | 5.7 |  |  |  |
| `validate_worlds_s2` | 10000 | 5.4 |  |  |  |
| `validate_worlds_s3` | 22000 | 13.8 |  |  |  |
| `validate_worlds_slots` | 18999 | 13.2 |  |  |  |
| `validate_worlds_slots2` | 33000 | 19.6 |  |  |  |
| `validate_worlds_slots3` | 36000 | 20.1 |  |  |  |
| `validate_worlds_121` | 4000 | 3.4 |  |  |  |
| `validate_worlds_raklion` | 3000 | 2.6 |  |  |  |
| `validate_worlds_karutan` | 3000 | 3.8 |  |  |  |
| `validate_render_effects16` | 424 | 3.4 | 2.6 | 2.4 | 3.6 |
| `validate_render_effects17` | 618 | 7.7 | 6.5 | 6.0 | 8.6 |
| `validate_item_callers` | 6013 | 1.7 |  | 1.3 | 1.8 |
| `validate_inventory_fx` | 8017 | 8.1 |  | 6.2 | 9.1 |
| `validate_render_effects18` | 540 | 1.0 |  | 0.9 | 1.6 |
| `validate_render_effects19` | 400 | 0.8 |  | 0.7 | 1.2 |
| `validate_render_effects24` | 226 | 2.3 | 2.3 | 2.0 | 3.1 |
| `validate_worlds_inner` | 4000 | 3.2 |  |  |  |
| `validate_actor_recipes` | 361 | 30.5 | 32.6 | 29.2 | 42.5 |

Steward validators: validate_charsel_world,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_terrain,validate_world_fidelity,validate_terrain_remaining,validate_render_worlds_a,validate_icarus,validate_worlds_b,validate_icarus_c2,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_audio_callers,validate_worlds_h,validate_worlds_i,validate_audio_domains,validate_worlds_j,validate_worlds_k,validate_audio_items,validate_worlds_o,validate_worlds_n,validate_worlds_p,validate_worlds_r,validate_world_tile_folder,validate_worlds_g2,validate_world_light_name,validate_worlds_p2,validate_worlds_r2,validate_worlds_q,validate_worlds_q2,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects16,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_worlds_inner,validate_actor_recipes.

Env: the canonical private-env script supplies MU_RECOVERY_INTEGRATION, MU_GAME_ROOT, MU_SECTION3,
MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR, snapshot/lang directories, graphics library and shared original cache.
All inputs are read-only and input links are never committed.

## Renders and byte identity

The before binary was built once from `ff8e0543`. Default draw only, no draw_all:

| Dataset | PNG identity | OBJECT/light dump identity | Before / after wall |
|---|---|---|---:|
| DATA-ACQ-002, 32 views | 64/64 identical | 64/64 identical | 66.85 / 56.15 s |
| October 22, 14 views | 26/28 identical; only world 37 changes | 28/28 identical | 20.39 / 23.27 s |
| World 40 captured clock | 2/2 identical | 2/2 identical | 2.52 / 2.47 s |
| World 37 captured clock | 0/2 identical, intended inline draws | 2/2 identical | 3.04 / 3.04 s |

Total default sweep: 90/92 PNGs and 92/92 dumps identical. The 44 unaffected views are all byte-identical.
World 37's last frame changes 2,087 pixels, mean absolute RGB 0.041796/255; at the captured clock, 2,095 pixels
and 0.040111/255. The native outputs were visually inspected. Captured world 40 has no new requests in this view.

Original-reference scores remain unchanged: world 40 image mean difference 3.985, share off 0.0426, 2,014 matched
objects, two missing dynamic objects and four near after-flag differences; world 37 3,964 matched objects and
three near after-flag differences. World 37's original PNG is unavailable. Comparison walls before / after:
world 40 0.90 / 0.95 s; world 37 0.29 / 0.28 s. No new live capture was taken.

Blood Castle uses an authored three-object layout, not client placement: version 0 plain records, map number 12;
types 11/13/42 at (12850,12850,50), (13200,12800,50), (12700,13200,50), zero angles and scale 1. Hero tile 128,128,
25 frames, 1280x800, FOV 39. All three models load; new visual refusal count 0. Drawn sprites 10 -> 18, created
sprites 20 -> 36 across two sampled draws; three new particle requests are refused. The candle glow is visible.
Last-frame difference: 5,851 pixels, mean absolute RGB 0.147890/255. The counter changes the OBJECT dump;
light dump stays identical. Before / after walls 1.36 / 1.47 s. Existing create/move refusals remain 3 / 72.

The one full default sweep was completed at `0e96c91a`; the final main-integrated affected-world replay is pending.
Local renders/reports are under the lane's own `~/Documents/MTM/mu-mac-tools/native/{renders,scratch}/render-worlds-inner-001/`.

## Limits and next

- Joint 0x7f7c/8 and missing particle/effect consumers remain counted refusals. Existing /18 lightning is served.
- The shared renderer fixes alpha reference at 0.25. Type 0x60's extra RGBA pass needs GREATER 0 and is refused;
  RGB is served. The base body remains drawable, and hidden refused objects stay skipped.
- Missing named/indexed bones refuse their requests. The clock window uses an authored WorldTime tick, not a
  captured independent process timeGetTime value. No server event state or ordinary spawnability is inferred.
- Blood Castle's create/move routines and the other classless worlds' inner draws remain outside this lane.
- Next: a coordinated renderer alpha-reference seam, the refused consumer kinds, then remaining classless hooks
  in 9/24/30/31/33/38/39/41/42/46/51/56/98. Keep those separate from item/actor/effect owners.

## Cleanup

No new private capture or input needs retention. The lane removes its disposable renders, scratch, build outputs,
worktree and local branch after its ready line; the remote PR branch stays for the steward. Installed apps,
owner clients and the shared original cache are untouched. Finish at PR-ready, merge belongs to the steward.
