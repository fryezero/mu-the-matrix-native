# RENDER-WORLDS-INNER-003

Branch `codex/render-worlds-inner-003`, from merged main `fb747e42`, PR #378. Implementation by Codex,
GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## Scope and what draws now

Authored inline producers for Aida 33 and its shared world-54 guard, Kanturu Remain 38, Land of Trials 31
and Devil Square 9. Owned source is `reconstructed/objects/world_inner3_visual.*`, with the existing
`native/core/mu_objects_runtime.c` adapter. Existing audio lines are preserved. No new consumers or event model.

## WIP

- Done: All four producers pass 8,000 full original comparisons with no mismatches/stops. All 54 compiled
  mutants are caught, minimum six detections, zero stopped mutants, 287.03 s at `5f8fbb98`. The extended production
  host and producer module pass five private tests, 3.51 s. Main `626abce1` is integrated as `3893d981`, retaining
  both appended validator rows. Integrated root/world builds pass in 13.18 / 6.11 s. Producer inputs are unchanged. Original baseline binary explicitly built from `fb747e42`,
  SHA-256 `e41e2ec2e3e91e6d89e12c81865bdf1bcbde256fa4c3ef88c40380c7c0a249f8`.
  Both default captured tours rendered once with `--hero-name Preview` and `MU_GFX_PUBLIC_DEMO=1`.
- Left: Fidelity/identity evidence, private incoming-UI check, review, final docs/audit/PR/cleanup.
  All 68 affected validators pass, 1,044,687 reported cases plus WORLDS-O, 972.13 s. Portable checks pass
  1,661 tests, 1,373 passed / 288 expected skips, zero failures/errors, 496.46 s including selection.
- Next: wait for load at most 14 and free memory at least 25%, then run the queued affected selectors/checks and fidelity pass.
  Resume inputs and logs are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-003/`.
  The integrated mu-world is `7bf4a7e24a283e07e472ea09dff63989955876237a18ecfda2028004bad6114a`.
  The checkpoint has no PR-ready claim. Other worlds and the alpha-reference seam remain untouched.

## Limits and next

Remaining named task worlds are 24, 30, 39, 41, 42, 46 and 98. Entry points remain in
[the research table](../research/client-worlds-inner.md#remaining-inline-work).
Worlds 46/98 reach the common guarded chain `0x017fcb5c..0x017fccbc` and the manager at `0x00ea2dc1`.
A static reread confirms the manager looks up a registered world handler and invokes slot 0x34. It does not
identify a new dedicated 46/98 leaf. No complete absence claim is made. No new live capture or installed app change.

Remaining entry points, not newly verified implementations:

| World | Address / limitation |
|---|---|
| 24 | Kalima `0x00def747`, guard `0x009b0418`, also 25..29/36 |
| 30 | `0x00d8e640`, event byte getter `0x00d8b3e3`; authored input only |
| 39 | `0x00e84941`, guard `0x00e84513`; tower fixture input |
| 41/42 | `0x00d5404b`, getter `0x00d53c8f`, tests `0x00d53d11` / `0x00d53d32` |
| 46/98 | `0x017fcb5c..0x017fccbc` and manager `0x00ea2dc1`; no dedicated leaf identified |

World 54's terrain assets are absent locally. Its shared Aida guard has instruction and production-host
coverage; it has no rendered proof. The alpha-reference seam remains deferred.

## Completed checks at this checkpoint

All commands ran from the repository root, with `nice -n 10`, make at most -j4 and validator jobs 2.
Canonical private-env supplied private inputs. No full lane gate. Resource waits are excluded from check walls.

| Check | Result | Wall |
|---|---|---:|
| Full original comparisons at `5f8fbb98` | Eight families, 8,000 cases, zero mismatches/stops | Included in mutant run |
| Compiled mutants | 54/54 detected, minimum six detections, zero stopped mutants | 287.03 s |
| Extended private production host and producer module | 5/5 pass, no skips | 3.51 s |
| Main-integrated root build | Pass at `3893d981` | 13.18 s |
| Main-integrated explicit world build | Pass, binary differs from before | 6.11 s |
| Initial repository audit | 2,212 files, zero rejected | 19.32 s |
| Validator selection | All 68 selected rows retained, including fallbacks | 64.90 s |
| Private native selection | 166 work items, above the 40-item cap | 59.20 s |

**8d reduced:** the changed production host and new producer module ran privately. No shared struct fields,
table sizes or existing constant values changed. The new exported names occur in the new module/tests and
production adapter. All selected fallback validators remain in the queued run. Affected regression results are recorded below. Render results remain pending, so these are checkpoint
results, not a PR-ready declaration.

## Affected validator results

All 68 selected rows pass at `3893d98115890c27b182c19584de18132fe425c6`; later changes are documentation only.
Total runner wall 972.13 s, including affected selection. No steward mutants requested. The 54 new compiled
mutants completed at `5f8fbb98`; none of their compiled inputs changed in the main integration.

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

Steward validators: validate_actor_recipes,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_charsel_items,validate_charsel_world,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_effects28,validate_render_worlds_a,validate_terrain,validate_terrain_remaining,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

Env: canonical private-env supplies MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR, snapshot/lang
directories, graphics library and shared original cache. Inputs are read-only; tools/python, evidence and input
links are never committed. All selected fallback rows are retained.

Portable affected suites at the same source state: 1,661 tests, 1,373 passed / 288 expected skips, zero
failures/errors. Runner wall 496.46 s including selection, 417.2 s test wall, jobs 2. No full lane gate.
