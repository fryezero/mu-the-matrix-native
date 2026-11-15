# MUUN-VISUAL-005

Verified authored-fixture subset on `codex/muun-visual-005`, with main `d3ec9950` integrated at
`78a336a5`. The merge steward owns integration. Offline/static/authored fixtures only. This lane
does not alter production selection, inventory, bonuses, damage, packets or authoritative feeds.

## What draws

The complete initial [386-row appearance census](../research/muun-appearance-census.csv) records
each exact model path, base-body request, available meshes/actions, prior admission and missing behavior.
It distinguishes 378 kind-0 and eight kind-1 rows. Base models load for 379 appearance rows from
canonical read-only game assets, with sixteen attachment records and no texture-load or attachment-bone
refusals. Six assets are absent and appearance 193 lacks its item binding. Frozen Native Data remains unchanged; it supplies converted
tables, while model BMDs come from the canonical game root. This is an adapter census, not 386 pixel proofs.

All four available bone-effect record branches are now admitted:

| Appearance | Model asset under Data/Item | New behavior | Retained consumer refusal |
|---|---|---|---|
| 375 | `illusionmuun.bmd` | Mesh-1 13-frame atlas, original colour, three particle requests along posed own bones 11/18 with normalized jitter | particle `0x8084/28` |
| 376 | `ragefightermuun.bmd` | Both mesh-2 rows keep their mesh and emit paired pulsing sprites at own bones 12/13/22/23; `0x80ba` draws | bitmap `0x810d` lacks a world binding |
| 377 | `dark_muun.bmd` | Mesh-4 record is effect-only; own bone 52 supplies rotating/pulsed `0x7ef7` glows and counted additional requests | bitmap `0x8003`, particle `0x7efa/3` |

The five special appearances now admit 29/30 record branches: 3/3, 3/4, 8/8, 10/10 and 5/5 for
356/357/375/376/377. Twenty-eight branches draw meshes and one emits only effects. The sole record
refusal in this group remains 357 `lalaUp.bmd` mesh 3. Across the full census, 551 extra rows are
admitted and nine unavailable mesh rows remain. Every emitted bone request is accounted as created or
refused. Missing/dummy/unresolved own bones are refused rather than borrowing another model's matrices.

The authored three-second remote clock now reaches main's existing `0x47a/0` model consumer. Main
already gained `0x47a/0,1` and the DarkLordSkill slot from RENDER-EFFECTS-031 while this lane was based
on 004. Integration retained that consumer unchanged and removed this lane's duplicate. New focused
original/native tests prove one live drawn transition model at 81 frames and expiry at 90 frames on GL
and software, with enabled/disabled pixel controls. Full read-only game assets supply
`Data/Skill/DarkLordSkill.bmd`; frozen Native Data lacks it. No asset refresh or copying was performed.

Two remaining 004 fixture gaps are covered. `MU_MUUN_REMOTE_BUFF_FIXTURE=9,0,1` supplies local byte,
remote byte and predicate for the mount buff fixture. It requires the existing mount and buff-18 flags.
The bytes must be 0..255 and the supplied predicate 0 or 1.
The original four raw-byte groups, 6/9, 7/10, 8/11 and 12/13, intentionally hide mismatches. Matching
9/6 draws and predicate zero bypasses the gate. No class/team or predicate meaning is inferred.
`MU_MUUN_RIDER_ACTION_FIXTURE=280` requires the existing rider fixture and an admitted seat interval.
Canonical player action 280 has positive keys, reaches the fifth interval and secondary action 4,
then draws and restores the hero pose. The eight-frame proof records eight restorations and zero
action/bone refusals. The default four-category cycle is unchanged. Invalid flag contexts and unavailable poses refuse.

[Original addresses, body hashes, supplied services and classification](../research/client-muun.md).

## Final checks

Commands ran from the repository root with the canonical private-env.sh where required. Heavy jobs use
nice 10, make at most four jobs and runners at most two workers. New heavy jobs wait above load 14 or
below 25% free memory. No full lane gate, hosted workflow or app-packaging module ran.

| Check | Result | Wall |
|---|---|---:|
| Root builds | implementation and main integrations pass | 12.21 + 12.55 + 20.16 + 13.72 + 22.62 + 20.08 s |
| New bone caller and controls | 221 cases, zero mismatches; 21/21 compiled controls caught, including one focused retry | 6.18 + 0.88 s |
| Transition consumer comparison and controls | 400 cases, zero mismatches; 7/7 compiled controls caught against main's retained consumer | 11.82 s |
| Remote visibility and fifth-seat comparison/controls | 417 cases, zero mismatches; 8 visibility plus 2 new boundary controls caught, no repeated successful controls | 39.96 + 3.82 s |
| Initial affected validators at abf4654f | 42/42 pass, 808,930 reported cases | 942.69 s |
| Final Muun/AUDIO source refresh at bee48677 | 74/74 pass, 1,203,243 reported cases, no failures/errors/skips | 1318.35 s |
| INNER-005 refresh at 6633aaf2 | 78/78 pass, 1,196,795 reported cases plus Worlds O without an aggregate count, no failures/errors/skips | 1320.55 s |
| Initial affected portable batch | 172 items, 1,509 tests, 1,215 passed / 294 expected skips, zero failures/errors | 416.33 s |
| Final Muun/AUDIO portable refresh | 182 items, 1,827 tests, 1,472 passed / 355 expected skips, zero failures/errors | 458.75 s |
| INNER portable refresh | 1,764 tests, 1,417 passed / 347 expected skips, zero failures/errors | 443.10 s |
| Private Muun runs before INNER integration | 25/25 then 29/29 pass, zero skips | 127.51 + 147.95 s |
| Final 8d reduced private refresh | 35/35 pass, zero skips: 29 Muun tests plus 6 incoming world host/helper checks | 122.52 s |
| Inspected native proof | 35 scene PNGs plus contact sheet, all pixel/counter controls; 356/357 inspected separately | 19.83 s |
| Final integrated proof replay | all 35 scene PNGs and contact sheet equal the inspected proof | 12.40 s |
| Explicit final world checks | world target checked before private/proof and before each final sweep; final hash stable | 0.22 + 0.21 + 0.24 s |
| First default after sweep and compare | 46 views, all renderer exits zero, imported EFFECTS-031 delta retained | 21.11 + 50.66 + 0.23 s |
| Final after-only sweep | 46 views, identical to the first after outputs, including every normalized report field | 14.90 + 43.45 s |
| Final identity/output analysis | raw image/dump and complete normalized-report comparison | 0.25 s |
| Validator selection previews | initial, final Muun/AUDIO and INNER refresh, all fallbacks retained | 37.48 + 51.72 + 90.14 s |
| Portable selection previews | initial, final Muun/AUDIO and INNER refresh; app packaging excluded | 116.07 + 94.33 + 76.22 s |
| Checkpoint audits | 2,315 / 2,315 / 2,338 / 2,340 staged files, zero rejected | 32.64 + 39.30 + 30.32 + 50.00 s |
| Final documentation policy check | 9 tests, 9 passed / 0 skipped, zero failures/errors | 0.78 s |
| Final repository audit | 2,354 staged files, zero rejected; final numeric/prose updates only afterward | 33.24 s |


**8d reduced:** the native selection exceeds forty work items. All seven affected Muun modules ran
privately, including the three new modules. The source-only portable run excludes only
`native/tests/test_native_app.py`. Optional compiled mutants ran only for new/changed checks and were
not repeated on unchanged targets. Built-in controls remain enabled where the registry has no switch.
Counts from overlapping runs are not distinct-test totals.

One bone child mutant initially survived because the deterministic corpus never entered its random
branch. The sample now enters it, and only that mutant was retried. The early remote integration test
also inspected a shutdown-only model counter after expiry. It now requires a separate 81-frame live
model run and a 90-frame expired run; its assertions still require the actual model draw and pixel delta.
The prior 24/25 batch in 120.20 s was a failure, followed by passing integrated runs. The initial
disabled-control assertion failed in the 15.12 s five-test run and its focused retry passed in 5.38 s.

## Default identity

Baseline 004 binary SHA-256:
`459bb5cf69db13136f43223c33aa63e078c06e893024878838a79d1ec48fd50f`.
Final binary SHA-256:
`56caf6dbe2881f7a3b9ebe65a4b85c762711dd27f027432210c87bb2654762e2`.
Both executables were explicitly rebuilt with `nice -n 10 make -C native -j4 world` before the
corresponding sweep. The baseline root build took 41.52 s and world/host build 8.00 s. The before
fourteen October plus thirty-two DATA-ACQ-002 views were taken once at 640x400, default draw, without
draw-all/live-time, using canonical private inputs and demo names. Their walls were 28.03 + 58.80 s.
No new live capture was made. PNGs and OBJECT/light dumps compare raw bytes; reports normalize only
output-directory prefixes and retain every field.

The final replay retains 91/92 PNGs, 92/92 OBJECT/light dumps and 46/46 stderr logs byte-identical
to the one baseline. All 46 normalized reports retain the imported bitmap-vector change from 97 to 99.
Only `38-kanturu-remain` frame 24 also changes, with 1,184 changed pixels and mean absolute RGB
delta 0.047787760/255. Its accepted/refused particles change 4/3 to 7/0, with the corresponding live,
maximum-live, RNG and drawn-particle fields preserved in the comparison. This matches the imported
[EFFECTS-031 default result](RENDER-EFFECTS-031.md#identity-and-fidelity). No report field is dropped.

The first after sweep at the Muun/AUDIO source took 21.11 + 50.66 s. After integrating INNER-005,
the required after-only refresh takes 14.90 + 43.45 s and matches all 276 first-after files exactly.
The 35 proof PNGs, contact sheet and all 32 raw scene reports/logs also match the inspected proof;
all reported proof counters match. These comparisons isolate the imported main delta from the
Muun fixtures. The intermediate binary was
`90991825c3fe21ee051c40ee66dfaca702a5bc49a5f3549523b8f9e6df1be52d`.
The final binary hash is unchanged by private tests, proof and both replays.


## Steward validators

Steward validators: validate_actor_composites, validate_actor_monsters, validate_actor_plain, validate_actor_recipes, validate_app_polish2, validate_app_polish4, validate_app_polish7, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_events, validate_audio_items, validate_audio_kubera, validate_audio_monsters, validate_audio_music, validate_audio_objects, validate_audio_objects4, validate_audio_ui, validate_audio_voices, validate_charsel_items, validate_charsel_world, validate_icarus, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_login_world, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_muun_bones, validate_muun_passes, validate_muun_riding, validate_muun_secondary, validate_muun_special, validate_muun_transition, validate_muun_visibility, validate_muun_visual, validate_object_render, validate_path, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects26, validate_render_effects28, validate_render_effects31, validate_render_worlds_a, validate_session_party, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_world_fidelity, validate_world_light_name, validate_world_tile_folder, validate_worlds_121, validate_worlds_after, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_worlds_b, validate_worlds_d, validate_worlds_e, validate_worlds_f, validate_worlds_fog, validate_worlds_g, validate_worlds_g2, validate_worlds_g3, validate_worlds_h, validate_worlds_i, validate_worlds_inner, validate_worlds_inner2, validate_worlds_inner3, validate_worlds_inner4, validate_worlds_inner5, validate_worlds_j, validate_worlds_k, validate_worlds_karutan, validate_worlds_n, validate_worlds_o, validate_worlds_p, validate_worlds_p2, validate_worlds_q, validate_worlds_q2, validate_worlds_r, validate_worlds_r2, validate_worlds_raklion, validate_worlds_s, validate_worlds_s2, validate_worlds_s3, validate_worlds_slots, validate_worlds_slots2, validate_worlds_slots3

All 99 latest row results pass, with 1,338,652 reported cases plus Worlds O, which reports success
without an aggregate case count. The table records the latest
passing run per row. Earlier rows carry forward only where the affected-since selector finds no changed
checked function. The two main integrations brought additional rows; none of their fallback selections
was dropped. Counts across overlapping batches above are not distinct-case totals.

No optional mutants are needed in the steward run. Source the canonical private-env.sh from the repo
root for MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR and row-specific inputs.

| Validator | Reported cases | Wall | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 16.1 s | `6633aaf2` |
| `validate_actor_monsters` | 1,437 | 73.0 s | `6633aaf2` |
| `validate_actor_plain` | 21,437 | 232.8 s | `6633aaf2` |
| `validate_actor_recipes` | 1,669 | 115.4 s | `6633aaf2` |
| `validate_app_polish2` | 1,028 | 5.3 s | `bee48677` |
| `validate_app_polish4` | 10,485 | 55.3 s | `bee48677` |
| `validate_app_polish7` | 5,120 | 2.5 s | `bee48677` |
| `validate_audio_callers` | 5,528 | 9.4 s | `6633aaf2` |
| `validate_audio_charsel` | 5,968 | 8.1 s | `bee48677` |
| `validate_audio_combat` | 19,548 | 52.8 s | `bee48677` |
| `validate_audio_domains` | 2,544 | 28.6 s | `6633aaf2` |
| `validate_audio_events` | 70,980 | 8.3 s | `bee48677` |
| `validate_audio_items` | 3,000 | 10.8 s | `6633aaf2` |
| `validate_audio_kubera` | 1,000 | 2.2 s | `6633aaf2` |
| `validate_audio_monsters` | 38,315 | 31.1 s | `6633aaf2` |
| `validate_audio_music` | 4,291 | 0.8 s | `bee48677` |
| `validate_audio_objects` | 4,000 | 7.1 s | `6633aaf2` |
| `validate_audio_objects4` | 10,093 | 13.8 s | `6633aaf2` |
| `validate_audio_ui` | 5,803 | 20.5 s | `bee48677` |
| `validate_audio_voices` | 2,182 | 0.2 s | `bee48677` |
| `validate_charsel_items` | 8,817 | 13.2 s | `6633aaf2` |
| `validate_charsel_world` | 1,200 | 3.2 s | `6633aaf2` |
| `validate_icarus` | 5,240 | 56.9 s | `6633aaf2` |
| `validate_icarus_c2` | 8,400 | 27.2 s | `6633aaf2` |
| `validate_inventory_fx` | 8,017 | 18.8 s | `6633aaf2` |
| `validate_item_callers` | 6,013 | 2.4 s | `6633aaf2` |
| `validate_items_ui` | 8,517 | 23.1 s | `6633aaf2` |
| `validate_login_world` | 1,200 | 3.3 s | `6633aaf2` |
| `validate_meshdraw` | 14,619 | 93.8 s | `6633aaf2` |
| `validate_model_edge` | 954 | 148.2 s | `6633aaf2` |
| `validate_model_light` | 1,433 | 11.3 s | `6633aaf2` |
| `validate_movement` | 6,614 | 83.0 s | `6633aaf2` |
| `validate_muun_bones` | 221 | 0.7 s | `bee48677` |
| `validate_muun_passes` | 1,361 | 1.2 s | `abf4654f` |
| `validate_muun_riding` | 890 | 0.7 s | `abf4654f` |
| `validate_muun_secondary` | 873 | 0.5 s | `abf4654f` |
| `validate_muun_special` | 452 | 0.7 s | `abf4654f` |
| `validate_muun_transition` | 400 | 1.1 s | `abf4654f` |
| `validate_muun_visibility` | 417 | 4.8 s | `bee48677` |
| `validate_muun_visual` | 912 | 1.4 s | `abf4654f` |
| `validate_object_render` | 1,984 | 4.5 s | `6633aaf2` |
| `validate_path` | 4,719 | 46.0 s | `bee48677` |
| `validate_render_effects16` | 424 | 7.1 s | `6633aaf2` |
| `validate_render_effects17` | 618 | 11.9 s | `6633aaf2` |
| `validate_render_effects18` | 540 | 2.4 s | `6633aaf2` |
| `validate_render_effects19` | 400 | 2.0 s | `6633aaf2` |
| `validate_render_effects24` | 226 | 4.1 s | `6633aaf2` |
| `validate_render_effects25` | 202 | 16.1 s | `6633aaf2` |
| `validate_render_effects26` | 348 | 16.9 s | `6633aaf2` |
| `validate_render_effects28` | 630 | 4.1 s | `6633aaf2` |
| `validate_render_effects31` | 66,051 | 286.0 s | `6633aaf2` |
| `validate_render_worlds_a` | 9,000 | 21.2 s | `6633aaf2` |
| `validate_session_party` | 200 | 1.2 s | `bee48677` |
| `validate_terrain` | 583,500 | 463.2 s | `6633aaf2` |
| `validate_terrain_remaining` | 2,147 | 17.2 s | `6633aaf2` |
| `validate_viewport_monsters` | 1,963 | 15.5 s | `bee48677` |
| `validate_world_fidelity` | 200 | 0.2 s | `6633aaf2` |
| `validate_world_light_name` | 304 | 0.5 s | `6633aaf2` |
| `validate_world_tile_folder` | 5,700 | 47.8 s | `6633aaf2` |
| `validate_worlds_121` | 4,000 | 12.6 s | `6633aaf2` |
| `validate_worlds_after` | 13,424 | 26.9 s | `6633aaf2` |
| `validate_worlds_after2` | 32,216 | 50.6 s | `6633aaf2` |
| `validate_worlds_after3` | 10,212 | 15.2 s | `6633aaf2` |
| `validate_worlds_after4` | 9,181 | 23.7 s | `6633aaf2` |
| `validate_worlds_after5` | 6,000 | 22.2 s | `6633aaf2` |
| `validate_worlds_after6` | 7,300 | 91.7 s | `6633aaf2` |
| `validate_worlds_b` | 4,000 | 7.3 s | `6633aaf2` |
| `validate_worlds_d` | 2,400 | 6.6 s | `6633aaf2` |
| `validate_worlds_e` | 4,840 | 29.2 s | `6633aaf2` |
| `validate_worlds_f` | 1,818 | 0.9 s | `6633aaf2` |
| `validate_worlds_fog` | 4,044 | 8.6 s | `bee48677` |
| `validate_worlds_g` | 6,000 | 9.3 s | `6633aaf2` |
| `validate_worlds_g2` | 2,657 | 9.0 s | `6633aaf2` |
| `validate_worlds_g3` | 4,000 | 8.7 s | `6633aaf2` |
| `validate_worlds_h` | 6,000 | 9.4 s | `6633aaf2` |
| `validate_worlds_i` | 6,000 | 8.1 s | `6633aaf2` |
| `validate_worlds_inner` | 4,000 | 7.4 s | `6633aaf2` |
| `validate_worlds_inner2` | 5,000 | 9.7 s | `6633aaf2` |
| `validate_worlds_inner3` | 8,000 | 19.7 s | `6633aaf2` |
| `validate_worlds_inner4` | 8,000 | 18.0 s | `6633aaf2` |
| `validate_worlds_inner5` | 4,000 | 7.4 s | `6633aaf2` |
| `validate_worlds_j` | 6,000 | 11.3 s | `6633aaf2` |
| `validate_worlds_k` | 6,000 | 7.6 s | `6633aaf2` |
| `validate_worlds_karutan` | 3,000 | 7.4 s | `6633aaf2` |
| `validate_worlds_n` | 13,000 | 14.2 s | `6633aaf2` |
| `validate_worlds_o` | not reported | 11.1 s | `6633aaf2` |
| `validate_worlds_p` | 10,000 | 14.1 s | `6633aaf2` |
| `validate_worlds_p2` | 6,000 | 7.6 s | `6633aaf2` |
| `validate_worlds_q` | 11,000 | 20.5 s | `6633aaf2` |
| `validate_worlds_q2` | 4,000 | 15.5 s | `6633aaf2` |
| `validate_worlds_r` | 12,000 | 14.2 s | `6633aaf2` |
| `validate_worlds_r2` | 9,000 | 13.9 s | `6633aaf2` |
| `validate_worlds_raklion` | 3,000 | 8.1 s | `6633aaf2` |
| `validate_worlds_s` | 11,000 | 16.8 s | `6633aaf2` |
| `validate_worlds_s2` | 10,000 | 14.7 s | `6633aaf2` |
| `validate_worlds_s3` | 22,000 | 34.3 s | `6633aaf2` |
| `validate_worlds_slots` | 18,999 | 30.2 s | `6633aaf2` |
| `validate_worlds_slots2` | 33,000 | 37.3 s | `6633aaf2` |
| `validate_worlds_slots3` | 36,000 | 37.7 s | `6633aaf2` |


## Limits and next

Unavailable meshes remain exact refusals: `king.bmd` mesh 1 at 276; `superpandaUp.bmd` mesh 1 at 292;
`poodle.bmd` meshes 1/2 at 305; `poodleUp.bmd` meshes 2/3 at 306; `lalaUp.bmd` mesh 3 at 357;
`Snowboarder.bmd` mesh 1 at 368; `SnowboarderUp.bmd` mesh 2 at 369. All paths are under `Data/Item`.
Code 363 `dandelionUp.bmd` has only actions 0..2, so 3/4 remain refused. The census lists every other
unavailable action. None is synthesized or remapped.

Six absent assets remain refused, exactly `shogunpet.bmd`, `shogunpet_evol.bmd`, `ninjapet.bmd`,
`ninjapet_evol.bmd`, `samouraipet.bmd`, `samouraipet_evol.bmd`, under `Data/Item`; 193 has no item-model
path binding. Secondary particles `0x8081/1`, `0x8082/1`, `0x7ef7/19`, bone particles `0x8084/28`,
`0x7efa/3`, and sprite bitmaps `0x810d`/`0x8003` keep counted refusals. Consumer files are unchanged by
this PR; the transition uses main's existing consumer. The transition proof uses full game assets,
not a claim about the frozen installed Preview's asset availability.

The fixture supplies deterministic random fractions/integers and pose/clock inputs. Comparisons supply
named bone transform, predicate/buff/owner lookup and CRT math services where documented; original
caller instructions and bounded consumers execute around them. Original global RNG/process phase,
periodic command clocks, target/rotation feeds and full original creation/render ordering remain outside
this subset. No full-scene, live-motion, installed-app or performance equivalence is claimed.

## Checkpoints and cleanup

Checkpoint pushes recorded done/left/next through implementation and main integrations. This handoff
supersedes their WIP sections. The compiled finish-line source is `78a336a5`. Later commits change
documentation and registry order; parsed validator entries and compiled sources stay the same.
The finish-line main base is `d3ec9950`; later main updates belong to the steward's combined-tree validation.
Scratch/renders used
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-005`. No future-lane input was created.
All documentation and final pushes precede the single ready-prs entry, with no push afterward. Own
scratch/renders, ignored builds/reports, worktree and local branch are removed at handoff; the remote
branch remains for the steward.
