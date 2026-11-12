# RENDER-WORLDS-INNER-002

Branch `codex/render-worlds-inner-002`, from main `d4af71dd`. WIP integration. Implementation and checks by Codex,
GPT-6.1 Sol, without subagents. Latest-main integration is recorded below. Merge belongs to the steward.

## WIP integration checkpoint

Done: object source and all 27 mutants are unchanged; 64 affected validators, portable suites, focused private
modules, demo-labelled native proofs and reference comparisons pass. Main `710ac816` (UI-WINDOWS-001) merged
cleanly as `2d9c56d1`. Root rebuild 5.39 s, mu-world rebuild 4.60 s. Five of this lane's validators overlap
its compiled inputs and passed again, 74.47 s. Full before/after evidence below is the pre-UI object-source run.

Left: portable integration selection, 133 work items, is running with no reported failure. Private UI module,
final main-integrated output identity, final audit and publication/cleanup remain. Status/plan edits are still
uncommitted drafts. No ready-prs line has been written.

Next: finish the foreground `integration.py` in this lane's scratch, then run `integrated-renders.py`.
Append exact integration results and final binary SHA here, remove this WIP section, finish audit, commit/push,
create/link PR, append ready-prs once, then push nothing more and clean up. Original 64-row reports are in
`verify-runs/lane-validators`; the five reruns are in `verify-runs/integration-validators`. No mutant rerun.
Owner stop contract: if not PR-ready by 02:15 on 2026-11-12, push WIP and stop by 02:30.
Local scratch is `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-002/`.

## Scope and what draws now

Elbeland 51 and Swamp of Calmness 56 now run their classless inline visual producers after the existing
outer RNG draw. Elbeland emits its particles, owned smoke, bone-5 glow, bone-0 orbit and six bone glows.
Swamp emits its paired flames, raised/owned smoke and the five existing 0x7f7d lightning subtypes.

The authored producer is `reconstructed/objects/world_inner2_visual.c`; the existing adapter in
`native/core/mu_objects_runtime.c` routes its calls. Missing bone transforms and missing consumers are counted.
Elbeland 0x3a needs an unwritten prior stack colour. Its complete producer is compared with authored input;
production refuses that request explicitly. The move handler normally hides 0x3c before the visual pass, so its
ten-smoke branch is verified with authored pre-hidden state, not claimed as an ordinary captured burst.

[Exact addresses, per-type calls and remaining entries](../research/client-worlds-inner.md).
No event-state model or new consumer is introduced. The shared alpha-reference seam remains deferred.

## Checks

Commands ran from the repository root with `nice -n 10`, at most `make -j4` and validator `--jobs 2`.
Private runs sourced `~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Resource waits are excluded from
individual check walls. No full lane gate.

| Check | Result | Wall |
|---|---|---:|
| Root `make -j4` | Pass | 30.06 s |
| New original call comparison | 5 families, 5,000 cases, zero mismatches/stops | included below |
| Compiled mutants | 27/27 detected, minimum 46 detections; each compiled once | 49.78 + 86.64 s |
| Affected validators, `a15ef265` | 64/64 pass; 1,023,171 reported cases plus worlds_o, which has no case total | 934.54 s |
| Affected portable suites | 1,634 tests: 1,355 passed, 279 expected skips, zero failures/errors | 427.26 s including selection; 356.5 s test wall |
| Private production host | 1/1 pass, no skips | 0.31 s |
| Private producer module | 4/4 pass, including 1,000 original cases, no skips | 0.90 s |
| After `make -C native -j4 world` | Pass; distinct binaries below | 3.81 s |
| Repository audit before first checkpoint | 0 rejected | 24.36 s |

The first mutant run passed all 5,000 baseline cases and eight compiled mutants, then setup rejected a
nonunique smoke-owner anchor. The anchor was narrowed and only the remaining nineteen mutants were compiled.
The final combined evidence has zero stopped mutants. The affected runner then replayed the full 5,000-case
row without mutants in 5.8 s. No producer or adapter source changed after `b05004c7`; `a15ef265` includes the
anchor correction. Later checkpoint commits change documentation only.

**8d reduced:** private native selection is 162 work items, above the 40-item cap. The changed production-host
module ran privately, along with the new producer module. 6b review found no shared struct field, table size or
constant change. New producer/refusal symbols occur only in the new producer/tests and this adapter. All 64
selected validator rows, including fallback rows, were retained. Selection walls: 58.67 s validators, 63.99 s
private native work items. The portable runner's own selection/execution is included in its wall above.

The synthetic host covers model absence before RNG, valid/short/missing bones, hidden-state persistence,
one-shot smoke, deferred 0x6e, supported joint owners and missing-consumer refusals, plus INNER-001's existing
mesh/alpha guards. An initial host assertion incorrectly expected the deferred 0x6e body in the first pass;
the host now tests its particle independently of that existing deferred-body return.

## Steward validators

Runs below are at `a15ef26545b483d9a9c5b42640cdab1bf7064bef`. No steward mutants requested; the 27 new
mutants are complete and the validated producer inputs are unchanged.

| Validator | Reported cases | Wall s |
|---|---:|---:|
| `validate_actor_recipes` | 1300 | 146.3 |
| `validate_audio_callers` | 5528 | 7.6 |
| `validate_audio_domains` | 2544 | 43.4 |
| `validate_audio_items` | 3000 | 4.4 |
| `validate_charsel_items` | 8817 | 14.8 |
| `validate_charsel_world` | 1200 | 3.7 |
| `validate_icarus` | 5240 | 47.7 |
| `validate_icarus_c2` | 8400 | 25.5 |
| `validate_inventory_fx` | 8017 | 21.9 |
| `validate_item_callers` | 6013 | 2.4 |
| `validate_login_world` | 1200 | 4.0 |
| `validate_meshdraw` | 14619 | 72.9 |
| `validate_model_edge` | 954 | 154.9 |
| `validate_model_light` | 1433 | 7.4 |
| `validate_movement` | 6614 | 70.5 |
| `validate_object_render` | 1984 | 3.9 |
| `validate_render_effects16` | 424 | 5.7 |
| `validate_render_effects17` | 618 | 19.6 |
| `validate_render_effects18` | 540 | 2.3 |
| `validate_render_effects19` | 400 | 1.3 |
| `validate_render_effects24` | 226 | 4.6 |
| `validate_render_effects25` | 202 | 14.8 |
| `validate_render_worlds_a` | 9000 | 18.1 |
| `validate_terrain` | 583500 | 432.7 |
| `validate_terrain_remaining` | 2147 | 5.9 |
| `validate_world_fidelity` | 200 | 0.3 |
| `validate_world_light_name` | 304 | 0.4 |
| `validate_world_tile_folder` | 5700 | 38.7 |
| `validate_worlds_121` | 4000 | 6.5 |
| `validate_worlds_after` | 13424 | 8.9 |
| `validate_worlds_after2` | 32216 | 18.8 |
| `validate_worlds_after3` | 10212 | 5.9 |
| `validate_worlds_after4` | 9181 | 9.6 |
| `validate_worlds_after5` | 6000 | 7.3 |
| `validate_worlds_after6` | 7300 | 54.1 |
| `validate_worlds_b` | 4000 | 3.6 |
| `validate_worlds_d` | 2400 | 3.8 |
| `validate_worlds_e` | 4840 | 25.3 |
| `validate_worlds_f` | 1818 | 0.6 |
| `validate_worlds_g` | 6000 | 5.7 |
| `validate_worlds_g2` | 2657 | 10.0 |
| `validate_worlds_g3` | 4000 | 3.2 |
| `validate_worlds_h` | 6000 | 5.7 |
| `validate_worlds_i` | 6000 | 9.2 |
| `validate_worlds_inner` | 4000 | 5.7 |
| `validate_worlds_inner2` | 5000 | 5.8 |
| `validate_worlds_j` | 6000 | 5.1 |
| `validate_worlds_k` | 6000 | 4.4 |
| `validate_worlds_karutan` | 3000 | 4.4 |
| `validate_worlds_n` | 13000 | 7.8 |
| `validate_worlds_o` | not reported | 5.7 |
| `validate_worlds_p` | 10000 | 9.6 |
| `validate_worlds_p2` | 6000 | 7.8 |
| `validate_worlds_q` | 11000 | 15.7 |
| `validate_worlds_q2` | 4000 | 4.8 |
| `validate_worlds_r` | 12000 | 8.4 |
| `validate_worlds_r2` | 9000 | 5.3 |
| `validate_worlds_raklion` | 3000 | 4.8 |
| `validate_worlds_s` | 11000 | 8.9 |
| `validate_worlds_s2` | 10000 | 9.1 |
| `validate_worlds_s3` | 22000 | 22.3 |
| `validate_worlds_slots` | 18999 | 21.0 |
| `validate_worlds_slots2` | 33000 | 43.8 |
| `validate_worlds_slots3` | 36000 | 44.1 |

Steward validators: validate_actor_recipes,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_charsel_items,validate_charsel_world,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_worlds_a,validate_terrain,validate_terrain_remaining,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

Env: canonical private-env supplies MU_RECOVERY_INTEGRATION, MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR,
MU_NATIVE_DATA_DIR, snapshot/lang directories, graphics library and shared original cache. Inputs are read-only;
the worktree's tools/python, evidence and input links are never committed.

## Renders and byte identity

Both binaries were explicitly built with `make -C native -j4 world` in this lane's tree, once with the
starting-main sources and then with the authored sources. They are distinct:

- Before, `d4af71dd`: `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
- After: `619be48504bcca387c1fd2b17d97ad1fb062a51ed52b56fff92d7442aaca7044`.

Initial image outputs missed the explicit demo-name argument and were replaced. The final replay uses
`--hero-name Preview` and `MU_GFX_PUBLIC_DEMO=1` for both binaries. Only this corrected replay is counted below.
Original names are not reproduced in comparison PNGs; comparison output contains scalar/object/light reports.

Default draw, no draw_all, 640x400, 25 frames sampled at 0/24:

| Dataset | PNG identity | OBJECT/light identity | Normalized reports | Before / after wall |
|---|---|---|---|---:|
| October 22, 14 views | 27/28 | 26/28 | 13/14 | 15.47 / 19.27 s |
| DATA-ACQ-002, 32 views | 64/64 | 64/64 | 31/32 | 37.22 / 52.35 s |

Total: 91/92 PNGs, 90/92 dumps, 44/46 normalized reports identical. All 44 unaffected views are byte-identical.
Only Elbeland's last PNG changes, 348 pixels and mean absolute RGB 0.001029/255; its OBJECT/light dump changes
with the new visual RNG phase. Swamp's captured PNGs/dumps stay identical, while its report records new calls.
Combined before / after default walls 52.68 / 71.62 s. The affected captured-clock views give the same
identity pattern; combined walls 5.18 / 11.68 s.

Original reference: Elbeland has no original PNG. Both worlds keep zero missing/extra objects and zero near
field differences in default and captured-clock comparisons. Swamp's original-resolution 1722x1048 image
scores stay 7.196 mean difference / 0.0096 share off at default time and 7.195 / 0.0095 at captured time.
These residual errors are not equivalence claims. Full-resolution before / after render walls are
1.29 / 1.16 s default and
2.54 / 2.27 s captured clock.

Two close-up proofs, 1280x800, fixed authored timing and seed, existing captured placements:

- Elbeland bone glows: last frame changes 209,743 pixels, mean absolute RGB 5.283443/255; before / after 1.43 / 1.52 s.
- Swamp lightning: last frame changes 1,377 pixels, mean absolute RGB 0.028063/255; before / after 1.42 / 1.28 s.

Elbeland tile 24,163, 25 frames, default two sampled draws: 0 -> 36 created sprites, 18 drawn sprites,
0 -> 40 created/drawn particles, four counted visual refusals. Swamp tile 130,120, 50 frames with draw_all:
0 -> 6 joints, 196 drawn joint quads, zero joint refusals; 109 created sprites, 15 refused particle requests.
Both close-up OBJECT/light dumps stay identical. The final demo-labelled native images were visually inspected.
No new original capture, event feed or original/native temporal equivalence is claimed.

## Limits and next

- Elbeland 0x3a's prior stack colour remains unavailable in production and counted as a refusal.
- Missing bones, absent particle kinds and absent consumer hooks retain counted refusals.
- Remaining task worlds: 9, 24, 30, 31, 33, 38, 39, 41, 42, 46, 98. Their entry addresses and event/dispatch
  caveats are in the research table. Worlds 46/98 have no dedicated leaf identified here; recheck the common
  chain and manager before adding code. The Elbeland 73/74 forwarding branch is outside this lane.
- Kanturu 0x60's extra RGBA pass still needs the coordinated renderer GREATER 0 alpha-reference seam.
- No new input needs retaining. Lane scratch/renders/builds are disposable and removed at handback; canonical
  captures and validator cache stay in place. Checkpoints with done/left/next were pushed throughout the run.
