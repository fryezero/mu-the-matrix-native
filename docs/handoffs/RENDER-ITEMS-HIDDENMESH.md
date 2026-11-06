# RENDER-ITEMS-HIDDENMESH

Base main `90e11d71`, branch `codex/render-items-hiddenmesh`. Codex GPT-6-Astra, xhigh; finished after a
provider stop by Claude Opus 5.5 (merge of main `742ef666`, remaining rows, audit, publication).
No live client, network/login work or protected-module work. No full gate in this lane.

## Cause and scope

The body generator probed OBJECT `+0x68` at zero except for six seeds. It therefore fitted zero constants where
client BODY hidden-mesh and MESH texture arguments copy that word. ItemObjectAttribute `0x016da00b` initializes
it to -1 at `0x016da0cc` and `0x016da12a`. RenderObjectScreen `0x016c2d82` calls that initializer at `0x016c32c1` and has no direct +0x68 writes;
ground item creation also calls it. TEX-003 identified 35 mesh texture call sites, including `0x01702deb`, `0x016ed79c`, `0x016e0a3a`
and `0x0170e146`. Bitmap zero is unregistered; texture -1 means each mesh's own bitmap.

The full generator run found 182 changed recipes: the 23 TEX-003 white types, plus 159 more readers. Of the
additional readers, 157 pass the word as BODY hidden mesh and two, `0x280c/0x280d`, use it as MESH texture but
have no installed item records. The owner explicitly expanded the lane to these readers, accepting intended
visibility changes in exchange for client fidelity. All use the existing source-35 mechanism, with no new
body code per type.

ItemObjectAttribute has six positive exceptions. Types `0x0b05`, `0x0eed`, `0x0f0b`, `0x1711`, `0x16f6` get 2;
`0x10f0` gets 1. The original stores are `0x016da7ae`, `0x016da7bd`, `0x016da7cc` and `0x016da7db`. The native
adapter preserves them through `mu_rc_item_hidden_mesh`. The first five bodies remain unimplemented. The
implemented `0x10f0` is compared at 0, -1 and its caller value 1. No whitelist of the 23 types is used.

## Implementation

- The generator varies HiddenMesh independently of render flags for every existing recipe. The generated
  recipes copy source 35. The large textual table diff includes deduplication/index shifts; 182 types change
  semantically, and all old zero-domain streams remain identical. All 485 changed phase-expanded argument
  cells are exactly constant zero to source 35, only BODY hidden and MESH texture fields.
- The executor admits 0 and -1, the exact ItemObjectAttribute exceptions, and the seeds' existing index domain.
- The shared native item adapter and bitmap-override probe use the same initializer value. This reaches the
  software inventory, GFx inventory, ground raster/GL, hero and other equipment consumers.
- The private texture survey now pins 13 hair-only white types, no unresolved override bitmaps, and zero white
  types with a wearer. No texture registrations or uploads change.
- A new private validator checks the initializer, all 182 reader streams, non-reading controls and posed rank-5
  controls. Existing validators' checks are untouched. The generator edit is one line, to avoid overlap with
  TEST-SPEED-001's cache work. No run_validators/affected tooling is edited.

## Survey and byte identity

Installed client, 1,691 types, 48 renderer states per type, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`:

| Measurement | Before | After |
|---|---:|---:|
| White types | 36 | 13 |
| White implemented types | 35 | 12 |
| White passes | 3,696 | 912 |
| Total passes | 615,986 | 625,182 |
| Missing override bitmaps | 23 | 0 |
| Types without an installed model | 47 | 47 |
| White types with a wearer | 23 | 0 |
| White passes with a wearer | 2,784 | 0 |

The 13 remaining types are TEX-002/003's unworn hair meshes, not missing item bitmaps. Body coverage stays
1,219/1,674, plus 17 skins. The survey reports 1,236 implemented types. All 4,758 mesh slots' pixel hashes,
filter and wrap are identical, with and without a wearer. Before was captured once from main in this lane's
worktree. C-to-C comparisons over 1,236 types and 32 states each give 39,552 identical old-domain streams;
with new caller defaults, exactly the 182 named types change. No unrelated type's stream changes. All 1,509 other survey rows remain identical; 170 reader rows change,
11 have no model, and 0x10f0 swaps meshes without changing its pass count.

TEX-003's full galleries intentionally change where they contain a reader. Removing those items gives exact
framebuffer identity at time 123456:

| Gallery | Removed reader | Unchanged framebuffer SHA-256 |
|---|---|---|
| Control 0,1,2,3,7,8 | none | `df03a29015909de199d353d327efd2b852f79f813bd5260d0358622313b14930` |
| 002K | code 7333, type 0x278b | `5cb6ea0dd87a2de134861747935636e00a5b0858dffe81c1fd92854f85b4ffce` |
| TEX-001 | code 32, type 0x0b06 | `8013c9eedcf2591305abbc580e94e72fc00356155e051ec43d4d57af935cd6e9` |
| 002M | code 3643, type 0x1921 | `f003f5fbf7ae557f3a7ba6ef3938e53bd7def551d649979fd73e04ed07d0db19` |
| 002N | code 6571, type 0x2491 | `fd0ebadc91fc416f6fff0f195d252a9ffb37bff4b7c6420f5ae8ec284f6f2bd4` |
| 002M at +13 | code 3643 | `f3a44989db5f7cd1740b0dc14d8685f2e4a5e01bab28bb78a19de2f65ee9efce` |
| 002N at +13 | code 6571 | `c2d7e67f1b97246c474ee9c2b4c0078e267c73c95660ec18300802dd6460083b` |

For the expanded scope's filtered galleries, a baseline executable was linked from the three main-source
objects and the unchanged native objects, without editing or building the main checkout.

Six window-only before/after PNG crops were inspected. The requested small review artifacts are retained in
`~/Documents/MTM/mu-mac-tools/native/review-artifacts/RENDER-ITEMS-HIDDENMESH/` as
`b1d.png`, `eee.png`, `151a.png`, `2537.png`, `afa.png`, `2491.png`, with before on the left. Full renders,
scratch and build products are removed. No client image is committed.

| Type | Evidence | Changed pixels |
|---|---|---:|
| 0x0b1d | White blade becomes textured | 184 |
| 0x0eee | Mesh 0 appears with its texture; triangles 290 to 403 | 255 |
| 0x151a | White staff section becomes textured | 72 |
| 0x2537 | White disc becomes textured; mesh 0 appears; triangles 483 to 625 | 170 |
| 0x0afa | Body mesh 0 completes the sword; triangles 129 to 184 | 325 |
| 0x2491 | Blue feather mesh 0 appears around the gold frame, 002N +13 gallery | 4,692 |

The 0x2491 result explains 002N's frame-only finding through the original instruction stream, without a live
client screenshot. Type 0x0ef2 has an identical +0 inventory image; its stream changes in other phases.

## Checks

`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
Pinned text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

| Check | Cases/result | Wall time |
|---|---|---:|
| Full recipe generation | Every admitted recipe rebuilt from pinned instructions | 633.41 s |
| Small comparison | 1,691 initializer + 368 affected + 2,545 additional + 208 generic controls + 418 rank-5; 0 mismatches | 12.12 s |
| `validate_item_hiddenmesh --cases 292 --mutations` | 116,281 comparisons, 0 mismatches; 6/6 mutants caught, none equivalent | 434.31 s |
| C-to-C old-domain and caller-default comparison | 39,552 unchanged old-domain streams; exactly 182 changed types with new defaults | 3.47 s |
| Baseline build | `nice -n 10 make -j4`, pass | 25.25 s |
| Changed-tree build | `nice -n 10 make -j4`, pass | 10.10 s |
| Baseline surveys and galleries | Captured once | 51.32 s |
| Changed surveys and galleries | 13/0 white types; 4,758 identical slots | 44.86 s |
| Expanded-scope filtered galleries | Six unchanged framebuffer hashes | 9.30 s |
| Manifest, repository-policy and capture-document modules | 28/28 tests pass | 1.06 s |
| Portable renderchar suite | 78 tests, 59 pass, 19 private skips | 0.31 s |
| Native item textures/renderchar/items/HUD/inventory skin/character modules | 43/43 tests pass, private installed checks enabled | 101.26 s |

The shared-symbol scan covered `object_hidden`, `mu_rc_item_draws_context`, `mu_rc_item_draws`,
`mu_renderchar_draw_item` and `mu_item_textures_overrides`. Besides the renderchar suite, it selected native
modules `test_native_item_textures`, `test_native_renderchar`, `test_native_items`, `test_native_hud`,
`test_inventory_skin`, `test_native_character`, `test_native_actor`, `test_native_players`,
`test_native_helpers` and `test_native_combat`.

The full new row comprises 1,691 initializer cases, 13,432 affected-texture cases, 93,148 additional-reader
cases, 7,592 non-reading controls and 418 posed rank-5 controls. Every reader gets 292 states at 0 and -1;
0x10f0 also gets all 292 at 1. Legacy random services are held at zero as described under limits.
Mutant detections: hidden input zero 50,718; reject -1 56,940; default initializer zero 1,685; positive exception
zero 293; BODY hidden zero 96,005; texture zero 110,956. This is the only mutant run in the lane.

After merging main `9e93e6c9`, the native build passes in 15.18 s. The six native modules above plus
actor/player/helper/combat coverage pass 83/83 tests in 265.36 s elapsed, including a resource pause.
The process timer reports 158.52 s excluding that pause. The merged effects changes touch neither the
renderchar/model-codec/record-math sources nor this lane's generator/validator, so the full new row is not
repeated. The affected effects rows are rerun without mutants after the merge.

The app merges through main `2531746f` preserve these compiled renderchar inputs. The build passes in 0.45 s,
and the conflict-resolved registry passes 17 manifest tests in 0.66 s. Both sides of the status and registry
conflicts are retained. The inventory/ground skin module is rerun below for the merged `world_gfx.c` change.

After main `5a91b98d` (bow effects), the build passes in 17.81 s. The affected `test_native_combat` and
`test_inventory_skin` modules pass 19/19 tests in 23.47 s, after a 120 s resource wait. The two effects
validators are also rerun without mutants. The HiddenMesh module and manifest check pass 19 tests with one
private-wrapper skip in 0.81 s; its full original comparison is the 116,281-case row above.

After main `742ef666` (TEST-SPEED-001 #297, APP-POLISH-003 #298), merge `f57e2b46`. The only code conflict
was `gen_item_bodies.sample`: this lane's `object_hidden` line is kept with #297's cached `_original` call; the
cache key covers the whole case, including `object_hidden`. Both sides of the status/handoff lines are kept.
The merge changes no `reconstructed/` source. It changes the item harness (`gen_item_bodies.py`,
`original_cache.py`, the continuation/ranked/clusters scripts), so all 13 rows that import it are rerun with
`run_validators.py --private --no-mutants --cache --jobs 2` at `f57e2b46`. `validate_item_hiddenmesh`,
`validate_item_types`, `validate_renderchar` and `validate_render_effects5/7` import none of those files, and their
build directories (`reconstructed/renderchar`, `model-codec`, `particles`, `combat`) are unchanged, so they are not
repeated (brief 6). Checks at `f57e2b46` (the PR head adds only this handoff text):

| Check | Result | Wall time | Load 1m |
|---|---|---:|---|
| `nice -n 10 make -j4` | pass | 9.90 s | 4.7 |
| `validate_item_continuation`, alone first (cold generator cache) | 25,772 cases, 0 mismatches | 631.2 s | 9.9 → 6.2 |
| Other 12 item rows, `--jobs 2` | 12 pass, 456,636 cases, 0 mismatches | 1,765.84 s | 6.0–12.2 |
| `run_test_suites.py --affected origin/main`, portable, `MU_GATE_JOBS=2` | 3 suites, 115 work items, 1,077 tests: 913 pass, 164 skip, 0 failures/errors | 231.8 s (263.5 s with selection) | 3.1 → 19.4 |
| Private `test_inventory_skin` + `test_native_item_textures` (merged `world_gfx.c`; 13-white survey pins) | 11/11 pass, no skips | 77.20 s | 7.4 |
| `audit_repository.py` | 1,885 staged files, 0 rejected | 24.23 s | 6.6 |
| Brief-6c doc modules after the `f57e2b46` handoff edit (`test_world_captures_2`, `test_repository_policy`; private `test_native_data_manifest`, `test_native_item_textures`) | 11/11 + 22/22 pass | 0.14 s + 61.67 s | 6–7 |

Generator cache: ten rows hit all 115,980 generator samples. Continuation (cold), clusters and gear rebuilt
91,272. Inference: the steward's batch 37 ran these rows on main at the same time, under a different harness key,
and the cache keeps one file per name, so the two versions evicted each other. The row results do not depend on
this; only the original side is cached. Reported for TEST-SPEED-002.

After main `83a21893` (TEST-SPEED-002 #299, RENDER-EFFECTS-013 #300, RENDER-WORLDS-S #301), merge `eed17e53`;
only the status/handoff lines conflicted (both kept). The merge changes no item harness file. It changes
`reconstructed/particles/particles.c` (Shiny01 subtype 3), `reconstructed/joints/` and two native core files, so the
rows building `particles` or `joints` and the affected unit suites are rerun at `eed17e53` (brief 6). The 11 item
rows without those directories, `validate_renderchar`, `validate_render_effects4`, `validate_fidelity` and
`validate_item_hiddenmesh` keep their `f57e2b46` results.

| Check at `eed17e53` | Result | Wall time | Load 1m |
|---|---|---:|---|
| `nice -n 10 make -j4` | pass | 20.33 s | 7.7 |
| `validate_item_types`, `item_gear`, `item_wings_next`, `item_effects`, `render_effects`, `render_effects3/5/7/9/10/11/12`, no mutants, `--cache --jobs 2` | 12 pass, 0 mismatches: 135,176 + 25,256 + 33,622 + 1,500 + 660 + 720 + 1,190 + 596 + 304 + 154 + 176 + 64 = 199,418 cases | 820.64 s (gear 763.7 s, wings_next 774.8 s, both cold; types 45.8 s; the rest ≤ 5.5 s) | 21.2 → 7.4 |
| `run_test_suites.py --affected origin/main`, portable, `MU_GATE_JOBS=2` | 3 suites, 117 work items, 1,091 tests: 926 pass, 165 skip, 0 failures/errors | 253.1 s (285.5 s with selection) | 5.3 → 14.0 |
| `audit_repository.py` | 1,905 staged files, 0 rejected | 23.99 s | 9.6 |
| Brief-6c doc modules after the final handoff edit | 11/11 + 22/22 pass | 0.21 s + 72.02 s | 13.1 |

The generator cache key changed with #299 (`85faf0df…` to `ca43a187…`): the key hashes the validator's whole Python
closure, which includes the runner tooling. Gear and wings_next therefore ran cold; correctness does not depend on it.

### Existing affected rows, without mutants

The first column of times is uncached, before the #297 merge; the second is the cached rerun at `f57e2b46` above.

| Validator | Cases per run | Before #297, s | `--cache` at `f57e2b46`, s | Result |
|---|---:|---|---:|---|
| `validate_item_ranked` | 17,736 | 802.16 | 99.1 | 0 mismatches |
| `validate_item_continuation` | 25,772 | 832.61 | 631.2 (cold) | 0 mismatches |
| `validate_item_expansion` | 52,172 | not run | 272.9 | 0 mismatches |
| `validate_item_clusters` | 74,292 | not run | 856.1 | 0 mismatches |
| `validate_item_types` | 135,176 | 32.82 | not affected | 0 mismatches |
| `validate_renderchar` | 1,706 | 48.38 | not affected | 0 mismatches |
| `validate_item_gear` | 25,256 | not run | 653.4 | 0 mismatches |
| `validate_item_next` | 14,992 | not run | 172.4 | 0 mismatches |
| `validate_render_effects5` | 1,190 | 4.16; 3.35; 3.80 | not affected | 0 mismatches |
| `validate_render_effects7` | 596 | 1.69; 1.15; 1.84 | not affected | 0 mismatches |
| `validate_item_coverage` | 31,724 | not run | 177.8 | 0 mismatches |
| `validate_item_wings_next` | 33,622 | not run | 199.4 | 0 mismatches |
| `validate_item_scalars` | 26,154 | not run | 155.1 | 0 mismatches |
| `validate_item_chains` | 35,346 | not run | 176.2 | 0 mismatches |
| `validate_item_carry` | 114,388 | 1122.18 | 467.6 | 0 mismatches |
| `validate_item_quality` | 28,080 | not run | 137.3 | 0 mismatches |
| `validate_item_product` | 2,874 | not run | 41.9 | 0 mismatches |

`run_validators.py --list-affected origin/main` selects 43 rows: the 17 above, `validate_item_hiddenmesh` and 25
more. Nine of those 25 reach `item_bodies.h` through `validate_renderchar.py` or `validate_item_clusters.py`; they are
cheap, so they were run at `f57e2b46` without mutants, `--cache --jobs 2`:

| Validator | Cases | Wall seconds | Result |
|---|---:|---:|---|
| `validate_item_effects` | 1,500 | 1.6 | pass |
| `validate_render_effects` | 660 | 1.3 | pass |
| `validate_render_effects3` | 720 | 1.1 | pass |
| `validate_render_effects4` | 1,920 | 6.3 | pass |
| `validate_render_effects9` | 304 | 0.9 | pass |
| `validate_render_effects10` | 154 | 0.5 | pass |
| `validate_render_effects11` | 176 | 0.4 | pass |
| `validate_render_effects12` | 64 | 0.4 | pass |
| `validate_fidelity` (`MU_LANG3_SNAPSHOT=$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang/live/lang3.bin`) | 991 | 51.7 | pass |

The other 16 (`validate_crypto`, `item_models`, `meshdraw`, `model_edge`, `model_light`, `npc_dialogue`, `protocol`,
`terrain`, `viewport_monsters`, `audio_callers`, `audio_combat`, `audio_domains`, `audio_items`, `audio_charsel`,
`worlds_after4`, `app_polish1`) reach this diff only through the shared native archive (`builds native`) or by naming
the `native/core/` directory. They do not call the item body executor or the item-texture override probe, so they
are not run in the lane.

## Changed types and reasons

In the BODY rows, old hidden mesh 0 excluded mesh 0. New -1 admits every mesh in that pass, including mesh 0.
Type 0x10f0 instead receives 1, admitting mesh 0 and excluding mesh 1. Other independent mesh/type/alpha tests
still apply. The table identifies the changed call arguments; availability and visibility in a particular frame
remain distinct. MESH rows replace unregistered bitmap 0 with each listed mesh's own texture.

| Type | Changed draw behavior | Installed model |
|---|---|---|
| 0x0afa | BODY shows mesh 0 | present |
| 0x0afb | BODY shows mesh 0 | present |
| 0x0b06 | BODY shows mesh 0 | present |
| 0x0b07 | BODY shows mesh 0 | present |
| 0x0b08 | BODY shows mesh 0 | present |
| 0x0b0e | BODY shows mesh 0 | absent |
| 0x0b18 | BODY shows mesh 0 | present |
| 0x0b1d | Own texture on meshes 1 | present |
| 0x0b1e | Own texture on meshes 0 | present |
| 0x0b1f | Own texture on meshes 0, 1, 2 | present |
| 0x0eee | Own texture on meshes 0; BODY shows mesh 0 | present |
| 0x0eef | BODY shows mesh 0 | present |
| 0x0ef1 | BODY shows mesh 0 | present |
| 0x0ef2 | BODY shows mesh 0 | present |
| 0x0ef3 | BODY shows mesh 0 | present |
| 0x0efb | BODY shows mesh 0 | absent |
| 0x0efe | BODY shows mesh 0 | present |
| 0x0f00 | Own texture on meshes 0 | present |
| 0x0f01 | Own texture on meshes 0, 2, 3 | present |
| 0x0f0e | Own texture on meshes 0, 1 | present |
| 0x10f0 | BODY shows mesh 0; hides mesh 1 | present |
| 0x10f6 | BODY shows mesh 0 | present |
| 0x10f7 | BODY shows mesh 0 | present |
| 0x10f8 | BODY shows mesh 0 | present |
| 0x1305 | Own texture on meshes 1 | present |
| 0x151a | Own texture on meshes 0 | present |
| 0x151b | Own texture on meshes 0, 1, 2, 3 | present |
| 0x151c | Own texture on meshes 0, 1 | present |
| 0x190d | BODY shows mesh 0 | present |
| 0x190e | BODY shows mesh 0 | present |
| 0x190f | BODY shows mesh 0 | present |
| 0x1910 | BODY shows mesh 0 | present |
| 0x1911 | BODY shows mesh 0 | present |
| 0x1912 | BODY shows mesh 0 | present |
| 0x1917 | BODY shows mesh 0 | present |
| 0x1918 | BODY shows mesh 0 | present |
| 0x191b | BODY shows mesh 0 | present |
| 0x1921 | BODY shows mesh 0 | present |
| 0x1922 | BODY shows mesh 0 | present |
| 0x1923 | BODY shows mesh 0 | present |
| 0x1938 | BODY shows mesh 0 | absent |
| 0x1939 | BODY shows mesh 0 | absent |
| 0x196d | BODY shows mesh 0 | present |
| 0x1af5 | BODY shows mesh 0 | present |
| 0x1b05 | BODY shows mesh 0 | present |
| 0x1b0a | BODY shows mesh 0 | present |
| 0x1b0d | BODY shows mesh 0 | present |
| 0x1b0e | BODY shows mesh 0 | present |
| 0x1b0f | BODY shows mesh 0 | present |
| 0x1b10 | BODY shows mesh 0 | present |
| 0x1b11 | BODY shows mesh 0 | present |
| 0x1b12 | BODY shows mesh 0 | present |
| 0x1b17 | BODY shows mesh 0 | present |
| 0x1b1b | BODY shows mesh 0 | present |
| 0x1b38 | BODY shows mesh 0 | absent |
| 0x1cf5 | BODY shows mesh 0 | present |
| 0x1d05 | BODY shows mesh 0 | present |
| 0x1d0a | BODY shows mesh 0 | present |
| 0x1d0d | BODY shows mesh 0 | present |
| 0x1d0e | BODY shows mesh 0 | present |
| 0x1d0f | BODY shows mesh 0 | present |
| 0x1d10 | BODY shows mesh 0 | present |
| 0x1d11 | BODY shows mesh 0 | present |
| 0x1d12 | BODY shows mesh 0 | present |
| 0x1d38 | BODY shows mesh 0 | absent |
| 0x1d7a | BODY shows mesh 0 | present |
| 0x1ef5 | BODY shows mesh 0 | present |
| 0x1f0a | BODY shows mesh 0 | present |
| 0x1f12 | BODY shows mesh 0 | present |
| 0x1f78 | BODY shows mesh 0 | absent |
| 0x1f79 | BODY shows mesh 0 | absent |
| 0x1f7a | BODY shows mesh 0 | present |
| 0x1f7b | BODY shows mesh 0 | present |
| 0x20f5 | BODY shows mesh 0 | present |
| 0x2178 | BODY shows mesh 0 | present |
| 0x2179 | BODY shows mesh 0 | present |
| 0x217a | BODY shows mesh 0 | present |
| 0x217b | BODY shows mesh 0 | present |
| 0x230a | Own texture on meshes 0, 1, 2 | present |
| 0x2310 | BODY shows mesh 0 | present |
| 0x2491 | BODY shows mesh 0 | present |
| 0x2495 | Own texture on meshes 0, 1, 2 | present |
| 0x2514 | BODY shows mesh 0 | present |
| 0x2515 | BODY shows mesh 0 | present |
| 0x2516 | BODY shows mesh 0 | present |
| 0x251c | BODY shows mesh 0 | present |
| 0x251d | BODY shows mesh 0 | present |
| 0x251e | BODY shows mesh 0 | present |
| 0x251f | BODY shows mesh 0 | present |
| 0x2520 | BODY shows mesh 0 | present |
| 0x2521 | BODY shows mesh 0 | present |
| 0x2522 | BODY shows mesh 0 | present |
| 0x2523 | BODY shows mesh 0 | present |
| 0x2524 | BODY shows mesh 0 | present |
| 0x2525 | BODY shows mesh 0 | present |
| 0x2526 | BODY shows mesh 0 | present |
| 0x2527 | BODY shows mesh 0 | present |
| 0x252b | Own texture on meshes 0, 1 | present |
| 0x252c | Own texture on meshes 0, 1 | present |
| 0x2537 | Own texture on meshes 0; BODY shows mesh 0 | present |
| 0x2538 | Own texture on meshes 1 | present |
| 0x2549 | BODY shows mesh 0 | present |
| 0x2553 | BODY shows mesh 0 | present |
| 0x2554 | BODY shows mesh 0 | present |
| 0x2555 | BODY shows mesh 0 | present |
| 0x2556 | BODY shows mesh 0 | present |
| 0x2557 | BODY shows mesh 0 | present |
| 0x2558 | BODY shows mesh 0 | present |
| 0x2559 | BODY shows mesh 0 | present |
| 0x255f | BODY shows mesh 0 | present |
| 0x2560 | BODY shows mesh 0 | present |
| 0x2566 | BODY shows mesh 0 | present |
| 0x2567 | BODY shows mesh 0 | present |
| 0x271b | BODY shows mesh 0 | present |
| 0x271c | BODY shows mesh 0 | present |
| 0x271d | BODY shows mesh 0 | present |
| 0x271e | BODY shows mesh 0 | present |
| 0x271f | BODY shows mesh 0 | present |
| 0x2720 | BODY shows mesh 0 | present |
| 0x2721 | BODY shows mesh 0 | present |
| 0x2722 | BODY shows mesh 0 | present |
| 0x2723 | BODY shows mesh 0 | present |
| 0x2724 | BODY shows mesh 0 | present |
| 0x2727 | BODY shows mesh 0 | present |
| 0x2728 | BODY shows mesh 0 | present |
| 0x2729 | BODY shows mesh 0 | present |
| 0x272a | BODY shows mesh 0 | present |
| 0x272e | BODY shows mesh 0 | present |
| 0x272f | BODY shows mesh 0 | present |
| 0x2730 | BODY shows mesh 0 | present |
| 0x2731 | BODY shows mesh 0 | present |
| 0x2732 | BODY shows mesh 0 | present |
| 0x2733 | BODY shows mesh 0 | present |
| 0x2734 | BODY shows mesh 0 | present |
| 0x2735 | BODY shows mesh 0 | present |
| 0x2736 | BODY shows mesh 0 | present |
| 0x2737 | BODY shows mesh 0 | present |
| 0x2738 | BODY shows mesh 0 | present |
| 0x2739 | BODY shows mesh 0 | present |
| 0x2742 | BODY shows mesh 0 | present |
| 0x2743 | BODY shows mesh 0 | present |
| 0x2745 | BODY shows mesh 0 | present |
| 0x2746 | BODY shows mesh 0 | present |
| 0x2747 | BODY shows mesh 0 | present |
| 0x2748 | BODY shows mesh 0 | present |
| 0x2756 | BODY shows mesh 0 | present |
| 0x2757 | BODY shows mesh 0 | present |
| 0x275e | BODY shows mesh 0 | present |
| 0x275f | BODY shows mesh 0 | present |
| 0x2760 | BODY shows mesh 0 | present |
| 0x278b | BODY shows mesh 0 | present |
| 0x278c | BODY shows mesh 0 | present |
| 0x278d | BODY shows mesh 0 | present |
| 0x278e | BODY shows mesh 0 | present |
| 0x27a3 | BODY shows mesh 0 | present |
| 0x280b | Own texture on meshes 0, 1, 2 | present |
| 0x280c | Own texture on meshes 0, 1, 2 | absent |
| 0x280d | Own texture on meshes 0, 1, 2 | absent |
| 0x280e | Own texture on meshes 0, 1, 2 | present |
| 0x2837 | Own texture on meshes 0, 1, 2 | present |
| 0x2838 | Own texture on meshes 0, 1, 2 | present |
| 0x2839 | Own texture on meshes 0, 1, 2 | present |
| 0x283a | Own texture on meshes 0, 1, 2 | present |
| 0x2894 | BODY shows mesh 0 | present |
| 0x28a0 | BODY shows mesh 0 | present |
| 0x28a1 | BODY shows mesh 0 | present |
| 0x28f9 | BODY shows mesh 0 | present |
| 0x28fa | BODY shows mesh 0 | present |
| 0x28fb | BODY shows mesh 0 | present |
| 0x28fc | BODY shows mesh 0 | present |
| 0x28fd | BODY shows mesh 0 | present |
| 0x28fe | BODY shows mesh 0 | present |
| 0x28ff | BODY shows mesh 0 | absent |
| 0x2900 | BODY shows mesh 0 | present |
| 0x2901 | BODY shows mesh 0 | present |
| 0x2904 | BODY shows mesh 0 | present |
| 0x2905 | BODY shows mesh 0 | present |
| 0x2906 | BODY shows mesh 0 | present |
| 0x2907 | BODY shows mesh 0 | present |
| 0x2908 | BODY shows mesh 0 | present |
| 0x2909 | BODY shows mesh 0 | present |
| 0x290a | BODY shows mesh 0 | present |

## Limits and follow-up

- These are bounded draw-stream comparisons, not whole-program proof. Legacy body helpers keep the existing
  zero-rand service used by the earlier body validators; this lane does not repair their unmodelled random
  consumption. Product and rank-5 controls still use their modelled random services. Other record, selection,
  shadow and owner-domain limits remain.
- Eleven changed types have no installed model/record, including the two extra texture readers. Their original
  streams are compared; no installed-image claim is made for them.
- The 455 unimplemented bodies remain. Among the next largest exact shape groups are four groups of seven
  armour types stopping at `0x0195a4e0` (shapes `e81796e9712001b9`, `c43d71d6f7d2df4b`, `4cb6573f00bf946a`,
  `88f3b1c0a4e45140`); two groups of seven armour types with body-owned particles/sprites (shapes
  `fafdfbafa28fb9c5`, `9db7617b9d5f6a18`); and seven pet/item bodies `0x26e6..0x26ec`, shape
  `0d172bcc007e72c6`. These are follow-up candidates from the existing survey, not new implementations.
- TEX-002's second `field_` bitmap and name-map history limits remain. Hair needs a wearer as before.

## Release

PR-ready at the head that carries this handoff, after main `83a21893`. Steward validators are listed in the PR
body; none needs mutants (the new row's six ran once, above). Cleanup removes this lane's scratch and build
products; the worktree stays until the steward merges, then the worktree and local branch are removed. Only the six small requested review PNGs are retained outside the render/scratch folders. The remote branch remains for the merge steward.
