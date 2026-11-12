# RENDER-WORLDS-INNER-003

Branch `codex/render-worlds-inner-003`, from merged main `fb747e42`, PR #378. PR-ready verified subset. Implementation and checks by Codex, GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## Scope and what draws now

Aida 33, Kanturu Remain 38, Land of Trials 31 and Devil Square 9 now execute their complete bounded inline
visual producers after the existing single outer RNG draw. Aida gains named tree glows, rotating Bone01 light,
smoke/particle/effect requests and scrolling meshes. Remain gains blue core glows, bone flares, existing /18
lightning and its particles/smoke. Trials gains the red lamp and detached rotating sprite. Devil Square's
three arm-emitter branches now deliver their supported particles.

The shared Aida guard also accepts 54. Its instruction and production-host cases pass, but local world-54
terrain assets are absent, so it has no rendered proof. Missing bones and absent consumers stay counted.
Owned implementation is `reconstructed/objects/world_inner3_visual.*` and the existing adapter in
`native/core/mu_objects_runtime.c`. Audio lines are preserved. No consumer, event model, actor/item table,
live client, installed app or README edit. [Addresses and per-type calls](../research/client-worlds-inner.md).

## Checks

Commands ran from the repository root with `nice -n 10`, make at most -j4 and validator jobs 2.
Private runs sourced `~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Resource waits are excluded from
check walls. No full lane gate.

| Check | Result | Wall |
|---|---|---:|
| Full original comparison, `5f8fbb98` | Eight families, 8,000 cases, zero mismatches/stops | Included below |
| Compiled mutants, once | 54/54 detected, minimum six detections, zero stopped mutants | 287.03 s |
| Affected validators, `3893d981` | 68/68 pass; 1,044,687 reported cases plus WORLDS-O, which has no total | 972.13 s |
| Affected portable suites | 1,661 tests, 1,373 passed / 288 expected skips; zero failures/errors | 496.46 s including selection; 417.2 s test wall |
| Private production host and producer module | 5/5 pass, no skips; includes 1,600 small original cases | 3.51 s |
| Private incoming ITEMS-UI module | 7/7 pass, no skips | 19.92 s |
| ITEMS-UI-integrated root build | Pass | 13.18 s |
| Explicit world build | Pass, distinct before/after hashes below | 6.11 s |
| Post-portable explicit world rebuild | Pass, same after hash | 0.20 s |
| Initial repository audit | 2,212 files, zero rejected | 19.32 s |
| Pre-ACTORS-004 audit | 2,226 files, zero rejected | 17.22 s |
| Documentation consumers | 36 tests, 35 passed / one expected skip | 7.77 s |
| Latest private items UI | 7/7 pass, no skips after UI2 | 15.66 s |
| Final documentation consumers | 36 tests, 35 passed / one expected skip | 7.28 s |
| Final post-actor audit | 2,233 files, zero rejected | 17.50 s |

**8d reduced:** the initial private native selection is 166 work items, above the 40-item cap. The changed production host
and new producer module ran privately. The incoming item-UI module also ran privately. No existing shared
struct field, table size or constant value changed. 6b's new exported names occur only in the new module/tests
and adapter. All 68 selected validator rows, including conservative compiler fallbacks, were retained.
Selection walls are 64.90 s validators and 59.20 s private native items.

The production host checks absent models before RNG, valid/short/missing bones, hidden smoke gates, word4
truncation and absent-hook refusal, owned and detached sprites, extra mesh/stream state, supported /18 joints
and explicit /8,9,10 refusals. Portable guards also cover wrong worlds, clock boundaries and log overflow.
The private item-UI test prints three existing missing-initializer warnings in its synthetic gfx host; no
failure or error occurs. The producer and mutant targets have not changed since `5f8fbb98`.

An early 3.93 s host run began during a load spike before its returned reading was inspected. A conditional
resource guard replaced that shell sequence. The final reported host run started at load 11.64 and 68% free
memory. This is shared-host validation, not a performance acceptance claim.

## Steward validators

Rows below ran at `3893d98115890c27b182c19584de18132fe425c6`. Later source integration is recorded below.
No steward mutants requested; all 54 new mutants are complete and their inputs are unchanged.

| Validator | Reported cases | Wall s |
|---|---:|---:|
| `validate_actor_recipes` | 1669 | 151.7 |
| `validate_audio_callers` | 5528 | 7.4 |
| `validate_audio_domains` | 2544 | 28.9 |
| `validate_audio_items` | 3000 | 4.9 |
| `validate_audio_objects` | 4000 | 6.5 |
| `validate_charsel_items` | 8817 | 18.3 |
| `validate_charsel_world` | 1200 | 2.3 |
| `validate_icarus` | 5240 | 33.6 |
| `validate_icarus_c2` | 8400 | 24.7 |
| `validate_inventory_fx` | 8017 | 12.0 |
| `validate_item_callers` | 6013 | 3.1 |
| `validate_items_ui` | 8517 | 19.9 |
| `validate_login_world` | 1200 | 2.3 |
| `validate_meshdraw` | 14619 | 108.5 |
| `validate_model_edge` | 954 | 175.6 |
| `validate_model_light` | 1433 | 7.3 |
| `validate_movement` | 6614 | 78.0 |
| `validate_object_render` | 1984 | 4.1 |
| `validate_render_effects16` | 424 | 6.3 |
| `validate_render_effects17` | 618 | 13.4 |
| `validate_render_effects18` | 540 | 1.4 |
| `validate_render_effects19` | 400 | 1.0 |
| `validate_render_effects24` | 226 | 3.3 |
| `validate_render_effects25` | 202 | 19.2 |
| `validate_render_effects28` | 630 | 3.2 |
| `validate_render_worlds_a` | 9000 | 14.0 |
| `validate_terrain` | 583500 | 430.5 |
| `validate_terrain_remaining` | 2147 | 4.0 |
| `validate_world_fidelity` | 200 | 0.2 |
| `validate_world_light_name` | 304 | 0.5 |
| `validate_world_tile_folder` | 5700 | 50.0 |
| `validate_worlds_121` | 4000 | 7.6 |
| `validate_worlds_after` | 13424 | 14.9 |
| `validate_worlds_after2` | 32216 | 32.8 |
| `validate_worlds_after3` | 10212 | 10.1 |
| `validate_worlds_after4` | 9181 | 17.5 |
| `validate_worlds_after5` | 6000 | 11.3 |
| `validate_worlds_after6` | 7300 | 82.5 |
| `validate_worlds_b` | 4000 | 4.7 |
| `validate_worlds_d` | 2400 | 4.3 |
| `validate_worlds_e` | 4840 | 17.5 |
| `validate_worlds_f` | 1818 | 0.5 |
| `validate_worlds_g` | 6000 | 4.6 |
| `validate_worlds_g2` | 2657 | 7.1 |
| `validate_worlds_g3` | 4000 | 5.7 |
| `validate_worlds_h` | 6000 | 5.4 |
| `validate_worlds_i` | 6000 | 4.7 |
| `validate_worlds_inner` | 4000 | 5.5 |
| `validate_worlds_inner2` | 5000 | 10.9 |
| `validate_worlds_inner3` | 8000 | 14.3 |
| `validate_worlds_j` | 6000 | 4.6 |
| `validate_worlds_k` | 6000 | 5.3 |
| `validate_worlds_karutan` | 3000 | 7.8 |
| `validate_worlds_n` | 13000 | 11.5 |
| `validate_worlds_o` | not reported | 8.1 |
| `validate_worlds_p` | 10000 | 13.0 |
| `validate_worlds_p2` | 6000 | 7.4 |
| `validate_worlds_q` | 11000 | 16.4 |
| `validate_worlds_q2` | 4000 | 8.2 |
| `validate_worlds_r` | 12000 | 12.5 |
| `validate_worlds_r2` | 9000 | 9.3 |
| `validate_worlds_raklion` | 3000 | 5.5 |
| `validate_worlds_s` | 11000 | 9.5 |
| `validate_worlds_s2` | 10000 | 11.9 |
| `validate_worlds_s3` | 22000 | 29.9 |
| `validate_worlds_slots` | 18999 | 22.9 |
| `validate_worlds_slots2` | 33000 | 43.6 |
| `validate_worlds_slots3` | 36000 | 45.8 |

Steward validators: validate_actor_composites,validate_actor_recipes,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_charsel_items,validate_charsel_world,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_effects28,validate_render_worlds_a,validate_terrain,validate_terrain_remaining,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

Env: canonical private-env supplies MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR, snapshot/lang
directories, graphics library and shared original cache. Inputs are read-only. tools/python, evidence and
input links are never committed.

## Renders and byte identity

Both binaries were explicitly built with `make -C native -j4 world` in this lane's own tree. The starting-main
binary was preserved before edits. The after binary was rebuilt again after portable tests. They differ:

- Before, `fb747e42`: `e41e2ec2e3e91e6d89e12c81865bdf1bcbde256fa4c3ef88c40380c7c0a249f8`.
- After ITEMS-UI integration: `7bf4a7e24a283e07e472ea09dff63989955876237a18ecfda2028004bad6114a`.

Every native image uses `--hero-name Preview` and `MU_GFX_PUBLIC_DEMO=1`. Original-reference comparison writes
scalar/object/light JSON only and produces no copy of an original-name PNG. Normalized reports omit only
output `png` and `fidelity_dump` paths. No scene data is removed for identity checks.

Default draw, no draw_all, 640x400, 25 frames sampled at 0/24:

| Dataset | PNG identity | OBJECT/light identity | Normalized reports | After wall |
|---|---|---|---|---:|
| October 22, 14 views | 28/28 | 28/28 | 13/14 | 14.52 s |
| DATA-ACQ-002, 32 views | 62/64 | 64/64 | 31/32 | 36.80 s |

Total 90/92 PNGs, 92/92 dumps and 44/46 reports are identical. All 44 unaffected views are byte-identical.
Only Kanturu Remain's PNGs change, with last-frame difference 9,312 pixels and mean absolute RGB 0.724443/255.
Aida's captured PNGs stay identical while its report gains sprites. The initial before default tours were
rendered once; their wall times were not recorded. They were not rerun to fill that timing gap.

Captured-clock affected views repeat the same identity pattern: Aida 2/2 PNGs and dumps identical;
Remain 0/2 PNGs and 2/2 dumps identical. Before / after walls: Aida 2.03 / 2.48 s, Remain 1.87 / 2.19 s.
Remain's captured-clock last frame changes 9,336 pixels, mean absolute RGB 0.745195/255.

The following fixed close-ups use captured placements at 1280x800 with draw_all, 25 steps. Counts are final
frame draws or cumulative creation as labelled. Both close-up OBJECT/light pairs stay identical.

| View | New native output | Last-frame difference | Before / after wall |
|---|---|---|---:|
| Aida tile 138,189 | 0 -> 3,300 created sprites, 132 drawn sprites, no visual refusals | 175,439 pixels; mean RGB 3.701978/255 | 1.23 / 1.93 s |
| Remain tile 111,90 | 75 particles created, 825 sprites created, nine particles and thirteen sprites drawn; four joints created and sixteen last-frame joint quads; 29 refused particle requests | 161,719 pixels; mean RGB 3.881443/255 | 1.04 / 1.43 s |

Trials and Devil Square have no original captured placement/image reference. Their proof layouts are authored,
version-0 plain records, zero angles, scale 1, hero tile 128,128, 1280x800, 25 steps with draw_all:

- Trials, folder 32: types 3/49/53 at 12850/12850/223.5, 13050/12850/223.5, 12850/13050/223.5.
  All three models load. 0 -> 75 created sprites, three drawn sprites; eight created/drawn particles and
  thirteen refused particle requests. Last frame changes 7,153 pixels, mean RGB 0.104046/255. Before / after
  0.82 / 1.09 s. Existing creation refusals remain three.
- Devil Square, folder 10: type 2 at 12850/12850/223.5. The model loads, 31 particles are created, 26 are drawn,
  zero particle/visual refusals. Last frame changes 820 pixels, mean RGB 0.022425/255. Before / after
  0.80 / 0.98 s. The existing create/move gap remains outside this producer.

Both fixture OBJECT/light pairs stay identical. The native glows, lamp and arm-particle outputs were visually
inspected. Aida has no original PNG. Against the full-resolution 1722x1048 original Remain image, default mean
absolute difference changes 6.121 -> 6.190 and share off 0.0562 -> 0.0568. At captured time it changes
6.121 -> 6.192 and 0.0562 -> 0.0568. These small increases remain recorded, not fitted away. Default render
walls 1.04 / 1.29 s, captured time 3.21 / 2.52 s. Scalar reference comparison walls are 0.26 / 0.26 s default,
0.26 / 0.28 s captured time.

Both affected worlds retain zero missing/extra objects: Aida matches all 4,135 with no near field differences;
Remain matches all 2,121, retaining seventeen hidden-mesh, thirteen after-character, six blend-light and six
velocity near differences. Its nine missing model files and unsupported create/move cases are unchanged.
No original/native temporal equivalence, whole-world fidelity or new original capture is claimed.

## Latest main integration

ITEMS-UI-001 main `626abce1` merged as `3893d981`. The appended validator conflict retained both independent
rows, and TOML parsing passed. The main-integrated 68-row validator and portable results above include it.
UI-WINDOWS-002 main `0ccd5f44` then merged cleanly as `1db14727be393c99711b3a98a84f73e5f587ecb1`.
Root/world builds pass in 7.07 / 4.17 s. The post-build overlap selector took 21.75 s and retained five rows,
including the movement fallback. All five pass without mutants in 78.30 s. The first incoming portable run completed 1,448 tests but reported one failure and one error, 334.40 s.
Its queue incorrectly exported MU_GFX_PUBLIC_DEMO=1 to tests. Two focused methods reproduce both failures
with that flag, 1.88 s, and pass with only the flag removed, 1.42 s. The queue now limits it to renders. The corrected integration run passes all 1,448 tests,
1,181 passed / 267 expected skips, zero failures/errors, 369.67 s including selection and 298.7 s test wall.
Both private UI modules pass 7/7 in 9.06 s. The final 54-view replay takes 90.22 s plus 0.29 s comparison:
all 108 PNGs, 108 OBJECT/light dumps and 54 normalized reports are byte-identical to the pre-UI2 after outputs.
Thus every before/after result and original-reference score above remains the final lane result. No production source change is needed for this environment correction.
UI2-integrated mu-world SHA-256: `fb59df136c01b9e582b7d31f10172760fb43fe4c86a9925afe4454f5785ab263`.
It is distinct from the before and pre-UI2 binaries. No object producer, adapter or mutant target changed in either integration.

| Overlapping validator at `1db14727` | Reported cases | Wall s |
|---|---:|---:|
| `validate_audio_callers` | 5528 | 5.9 |
| `validate_audio_domains` | 2544 | 23.7 |
| `validate_audio_items` | 3000 | 4.2 |
| `validate_movement` | 6614 | 52.2 |
| `validate_render_effects16` | 424 | 3.5 |


ACTORS-004 main `c35458a0` merged as `c8b8cd12dff2c22b1865a4cdf679a3ec4530a46a`, keeping both status entries.
Root/world builds pass in 13.35 / 3.92 s. Its selector took 64.90 s and retained eighteen overlapping rows,
including both fallbacks. All eighteen pass without mutants in 174.94 s. The affected portable run passes
1,518 tests, 1,261 passed / 257 expected skips, zero failures/errors, 459.97 s including selection and
400.7 s test wall. The new private actor module passes 3/3 without skips in 5.64 s. Its 54-view replay takes
77.28 s plus 0.26 s comparison: all 108 PNGs, 108 dumps and 54 normalized reports are identical to UI2.
The final binary is `1106199bf3a7529aef06891e31a2c423301294d7ef4f6c2e621f224a80b9a327`.
The world producer/adapter and mutant targets remain unchanged.

| Overlapping validator at `c8b8cd12` | Reported cases | Wall s |
|---|---:|---:|
| `validate_actor_recipes` | 1669 | 96.4 |
| `validate_audio_callers` | 5528 | 5.2 |
| `validate_audio_domains` | 2544 | 19.2 |
| `validate_audio_items` | 3000 | 2.7 |
| `validate_audio_objects` | 4000 | 2.8 |
| `validate_charsel_items` | 8817 | 7.9 |
| `validate_icarus_c2` | 8400 | 13.0 |
| `validate_inventory_fx` | 8017 | 6.8 |
| `validate_item_callers` | 6013 | 1.2 |
| `validate_items_ui` | 8517 | 9.2 |
| `validate_movement` | 6614 | 57.8 |
| `validate_render_effects16` | 424 | 3.1 |
| `validate_render_effects17` | 618 | 6.6 |
| `validate_render_effects18` | 540 | 1.0 |
| `validate_render_effects19` | 400 | 0.8 |
| `validate_render_effects24` | 226 | 2.6 |
| `validate_render_effects25` | 202 | 7.6 |
| `validate_render_effects28` | 630 | 2.6 |

Final own-range selection retains all original 68 rows and adds `validate_actor_composites`, which was newly
registered on main. It passes 1,427 reported checks without mutants in 6.8 s at `a9b5a8f9`, with compiled inputs unchanged from `c8b8cd12`.
The final steward list therefore contains 69 passing rows. No new actor mutants were run by this lane;
the incoming actor lane owns its ten compiled-mutant results. No existing row was pruned by final selection.

## Limits and next

- Missing bones and consumers remain counted. Particle kinds still absent are 0x801c/3,4,7, 0x7f89/7,10,26,
  0x7f42/7 and 0x802a/1. The producer now reaches these requests; this lane adds no consumer.
- Remain's 0x7f7d/8,9,10 joints remain refused. Missing keyed-effect hooks refuse even word4 zero. Effects
  absent from the existing pool remain that pool's refusals.
- World 54 has no local terrain assets or render proof. The alpha-reference seam for Kanturu type 0x60's
  GREATER 0 RGBA pass remains deferred.
- Remaining task worlds and entry points follow. Addresses are next inspection points, not claims that every
  branch needs new code. Event-dependent inputs must stay fixed authored fixtures.

| World | Entry / limitation |
|---|---|
| 24 | Kalima `0x00def747`, guard `0x009b0418`, also 25..29/36 |
| 30 | `0x00d8e640`, event byte getter `0x00d8b3e3`; authored input only |
| 39 | `0x00e84941`, guard `0x00e84513`; tower fixture input |
| 41/42 | `0x00d5404b`, getter `0x00d53c8f`, tests `0x00d53d11` / `0x00d53d32` |
| 46/98 | `0x017fcb5c..0x017fccbc`, manager `0x00ea2dc1`; no dedicated leaf identified |

A static reread confirms the common chain forwards to guarded leaves and then the manager. The manager
looks up a registered world handler and invokes slot 0x34. Complete registry/context coverage for 46/98
remains unverified. Do not invent a leaf or event model to close those rows.

## WIP checkpoint history and cleanup

- `5f8fbb98`: four producers and 1,600 small original cases; full checks/renders left, next full mutants and host.
- `c7d28d3d`: 8,000 cases, 54 mutants, private host and ITEMS-UI integration; affected checks/renders left.
- `b41083f2`: all 68 affected validators and 1,661 portable tests; render analysis, final integration/docs/PR left.
- `3cedc070`: all four render proofs and latest-main overlap checks; corrected integration test environment
  and final UI replay/docs/PR left. No object source changed.

- `ff036d7c`: completed UI integrations, render proofs, documentation consumers and the pre-actor audit;
  new ACTORS-004 integration left.

- `a9b5a8f9`: ACTORS-004 merge, eighteen passing overlaps, portable/private checks and replay complete;
  the newly selected actor validator and final audit/PR left.

Each checkpoint was committed and pushed with a WIP done/left/next section. No new private input needs
retention. Lane scratch/renders/builds are disposable and will be removed at handback, along with the worktree
and local branch. Canonical captures and original cache stay in place. The remote branch stays for the steward.
