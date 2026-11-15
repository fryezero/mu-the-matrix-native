# MUUN-VISUAL-004

Verified candidate on `codex/muun-visual-004`. Main `a95880c4` (AUDIO-004, ACTORS-005, INNER-004 and UI-WINDOWS-003) is integrated;
compiled source/checker checkpoint `76f42724`, registry integration `795ce3cf`, final Muun test edit `6270622e`. The merge steward owns
integration. Offline/static/authored fixtures only. No installed-app, live-client, protection, packet,
particle/effect consumer, actor/item, UI or README work was authored in this lane. Incoming actor/world
and alpha-reference/UI changes are from main.

## What draws

Eight kind-1 records, ids 16/17/100..105, now support a seated rider. Set `MU_MUUN_FIXTURE=<id>`,
`MU_MUUN_MOUNT_FIXTURE=1` and `MU_MUUN_RIDER_FIXTURE=1`. The existing posed `Bip01 Spine1` offset,
scaled once with the original +30 z, feeds the original five rider-action intervals and seat addition.
Missing/dummy/unresolved attachments remain refused. The fixture authors four unarmed categories over
25-step phases: owner actions 38/71/103/315 select secondary actions 0/2/2/0. The hero renderer's temporary
pose/position/action/frame changes are restored after every draw. Logical hero position, equipment and
stats are unchanged. Existing mount-only action cycling remains available without the rider flag.

`MU_MUUN_OWNER_KIND_FIXTURE=2` supplies the owner-kind-2 fade input: after existing FadeAlpha, subtract
0.1 from every nonzero alpha, including negative alpha, without clamping. `MU_MUUN_BUFF18_FIXTURE=1`
selects the local-owner buff-0x12 mode-10 pass: white light, flags 0x4040, alpha 0.5, Chrome02 0x7fcf,
original blend/light and UV multipliers 8/2. Both flags require the mount fixture. Missing texture is a refusal.

The complete bounded `0x009bfe13` producer emits model-pair colours and two requests from a supplied
posed-bone transform. Native routes 0x8081/1 or 0x8082/1 and 0x7ef7/19 through existing particle entry
points. Their consumers remain unavailable and every request is counted as refused. The authored remote
flag `MU_MUUN_REMOTE_FIXTURE=1` supplies period 3 seconds and delta 0.04; one expiry clears/resets the
clock and routes 0x47a to the existing effect entry point, which also counts its consumer refusal.

Five special appearances now draw 25 of their 30 extra mesh rows:

| Appearance | Model | Drawn / rows | Retained refusal |
|---|---|---:|---|
| 356 | 0x2b7a | 3 / 3 | none |
| 357 | 0x2b7b | 3 / 4 | mesh 3 absent from installed model (only meshes 0..2) |
| 375 | 0x2b8d | 7 / 8 | mesh 1 bone-effect branch |
| 376 | 0x2b8e | 8 / 10 | two mesh 2 bone-effect rows |
| 377 | 0x2b90 | 4 / 5 | mesh 4 bone-effect branch |

The 0x2b7a/b mesh-2 branch updates persistent OBJECT +0xc8 on each render using action/frame delta.
The 0x2b8e meshes 5/6 use their 13/15-frame atlas, including exact x86 invalid-clock conversion behavior.
Ordinary rows share the existing mesh adapter. The four bone-effect rows are classified at branch entry
and explicitly refused. Code 363 still refuses unavailable actions 3/4. No substitute meshes/actions are used.
[Original addresses, method and evidence boundaries](../research/client-muun.md).

## Final checks

All commands ran from the repo root. Heavy commands use nice 10, make at most four jobs, validators two
workers; resource probes pause new heavy jobs above load 14 or below 25% free memory. Private runs source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`. No lane full gate or hosted workflow ran.

| Check | Result | Wall |
|---|---|---:|
| Root builds | initial source, special-row, audio, actor/world and UI integration pass | 30.06 + 11.70 + 21.20 + 17.64 + 6.26 s |
| New rider original comparison and one-time mutants | 890 cases, zero mismatches; 22/22 mutants compile under `-Werror` and are caught | 9.61 s |
| New special original comparison and mutants | 452 cases: 419 full caller comparisons plus 33 explicit branch-entry refusal classifications; zero mismatches; 17/17 distinct compiled mutants caught | 6.77 s initial + 0.97 s focused retry |
| Focused private modules during integration | secondary 5/5, rider 5/5, special 3/3 pass | 5.87 + 33.75 + 16.03 s |
| Final pre-merge private Muun modules | 19/19 pass, zero skips; 28 audited records, eight riders, four action phases, renderer restoration, leases/refusals and GL/software controls | 60.40 s |
| Initial affected private validators at `8e992004` | 40/40 pass, 735,012 reported row cases, no skipped rows | 813.48 s including selection |
| Special-source affected refresh at `76f42724` | 36/36 pass, zero failures/errors/skips; five unchanged earlier rows retain their results | 628.46 s including selection |
| Initial affected portable batch | 168 items; 1,543 tests, 1,269 passed, 274 explicit skips, zero failures/errors | 460.08 s including selection |
| Special-source portable refresh | 163 items; 1,478 tests, 1,208 passed, 270 explicit skips, zero failures/errors | 434.60 s including selection |
| Pre-merge native proof | 35 GL PNGs, contact sheet inspected; eight riders, four actions, buff/fade and five special appearances | 24.12 s |
| Default before sweep (taken once) | 46 views, 640x400, no draw-all/live-time | approximately 23.02 + 63.98 s, local log spans |
| Pre-merge after sweep | 92/92 PNGs, 92/92 dumps, 46/46 normalized reports and 46/46 stderr logs identical | 19.89 + 48.40 s |
| AUDIO-004 validator refresh at `fed9a7a4` | 28/28 pass, zero failures/errors/skips | 567.78 s runner; 105.58 s preview selection |
| AUDIO-004 portable refresh | 169 items; 1,769 tests, 1,446 passed, 323 skipped, zero failures/errors | 443.64 s runner; 56.97 s preview selection |
| AUDIO-004 private Muun refresh | 19/19 pass, zero skips; binary hash unchanged by tests | 76.02 s |
| AUDIO-004 proof refresh | 35/35 PNGs and contact sheet equal the inspected pre-merge images | 17.36 s |
| AUDIO-004 after identity | all 230 required files plus 46 stderr logs identical | 20.30 + 55.93 s render; 0.22 s compare |
| Actor/world validator refresh at `88420149` | 32/32 pass, zero failures/errors/skips | 621.77 s runner; 134.32 s preview selection |
| Actor/world portable refresh at `6270622e` | 175 items; 1,794 tests, 1,465 passed, 329 skipped, zero failures/errors | 500.59 s runner; 125.10 s preview selection |
| Focused rider row at `6270622e` | 890 cases pass after test-boundary edit; optional mutants unchanged | 0.79 s |
| UI validator refresh at `8ee7eaa0` | 6/6 pass, zero failures/errors/skips; exact lane selection remains 43 rows | 69.45 s runner; 32.29 s preview selection |
| UI portable refresh at `8ee7eaa0` | 147 items; 1,511 tests, 1,209 passed, 302 skipped, zero failures/errors | 447.00 s runner; 74.72 s preview selection |
| Final reduced private Muun run at `c37e14d6` | 19/19 pass, zero skips, including the explicit unavailable-particles refusal control | 71.24 s |
| Final integrated native proof | 35/35 PNGs and contact sheet byte-identical to prior proof; all eight riders, four action phases, buff/fade and five special appearances | 17.48 s |
| Final integrated after sweep | 45 unaffected views byte-identical; only imported INNER-004 Kanturu 37 delta (two PNGs and one report) | 24.42 + 81.01 s |
| Final identity comparison | 90/92 PNGs, 92/92 dumps, 45/46 reports and 46/46 stderr logs identical; exact Kanturu pixel delta verified | 0.26 s |
| Explicit integrated world build checks | pass; identical current hash before/after private tests and proof, distinct from baseline | 0.40 + 0.42 s |
| Earlier selector previews | initial/special validator and portable lists | 27.46 + 28.77 + 84.79 + 81.06 s |
| Full lane validator previews | audio, actor/world and UI integrated selections | 46.36 + 39.58 + 54.25 s |
| Checkpoint repository audits | 2,271 and 2,275 staged files, zero rejected | 18.69 + 27.04 s |
| Final repository audit | 2,296 staged files, zero rejected; only these result numbers and PR prose updated afterward | 30.34 s |

**8d reduced:** the portable selections exceed the forty-native-item cap. This lane's changed/affected
`test_muun*.py` modules ran privately. These cover 15 appearance records, eight secondary records
and five special records. Counts from overlapping batches above are not distinct-test totals. No unchanged
optional mutant set was repeated; validators' built-in controls remain enabled where not switchable.

The special fade-speed mutant initially survived because all deterministic samples clamped to zero and
the small random mutant sample missed an unsaturated value. Two deterministic unsaturated cases were added
(450 to 452 total). Only that mutant was recompiled/retried and caught; the other sixteen were not repeated.
Appearance 357 initially failed a four-draw expectation. Inspection found three installed meshes, with
all relevant textures present; the test now asserts three draws and the explicit out-of-range mesh refusal.
The secondary private host's missing reconstructed data-library build dependency was also fixed. Its first
run failed in 5.535 s (unittest wall); the first special private run failed in 24.64 s. The successful
retries are included above.

The remote test requires one accounted created/refused result on the enabled route and adds an explicit
`--no-particles` control requiring one refusal and no pending request. This keeps consumer admission in the
effect lane rather than requiring that consumer to remain absent. Current full-route proof still records
zero created and one refused.

The 90-frame fixture draws/restores the rider exactly 90 times and selects all four owner actions. It
routes 180 secondary requests, all refused, and one remote 0x47a expiry, refused with no pending request.
The eight short rider proofs have no missing textures, invalid bones or action refusals. Local buff mode is
10 and the owner-kind-2 sample alpha is 0.55. The special proofs report 3/3/7/8/4 draws, 0/1/1/2/1 refusals,
and zero missing textures. These are native fixture proofs, not original-scene or live-motion equivalence.

## Default identity

Before main `b7dfd2ed`, SHA-256
`e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
Pre-merge Muun source SHA-256
`56bc0bd3be8f4a2c7fa18738e9d0aa3b3754b5c90a12bb192d052e011809e7f1`.
AUDIO-004 integrated binary SHA-256
`25024c17935ce37245cbf895bf84444e321deec2c361a0b120e38cd3cbe389a4`.
Final actor/world/UI integrated binary SHA-256
`da0b71f048b670e49f73e9f025bc9d332bd83087ec380483c97691717ea85401`.
The before and final executables differ. Explicit `nice -n 10 make -C native -j4 world` checks precede
sweeps; the final two checks took 0.40 and 0.42 s. The initial before-build command wall was not logged.

The final replay preserves all 45 unaffected views: 90/92 PNGs, 92/92 OBJECT/light dumps, 45/46 normalized
JSONL reports and 46/46 stderr logs. Only `37-kanturu` changes, in two PNGs and its report. Its last frame
changes exactly 7,686 pixels with mean absolute RGB delta 0.295925781/255, matching the imported
[INNER-004 RGBA mesh result](RENDER-WORLDS-INNER-004.md). All differences remain in the comparison output;
no Kanturu report field was removed or normalized away. This lane's pre-main and audio-integrated
replays preserve all 230 required files plus 46 stderr logs.

The required fourteen October and thirty-two DATA-ACQ-002 before views were taken once, at 640x400,
without draw-all/live-time, using canonical private inputs and current input paths in local manifests.
Incoming compiled changes justified after-only replays; the actor/world and UI changes share the final
replay. Only output-directory prefixes are normalized in JSONL reports. PNGs and dumps compare raw bytes.
The first local comparator omitted `.jsonl` from its normalization suffixes and reported only path
prefixes; fixing that script passed without rerendering or changing the baseline. Five early exploratory
views were not part of the required 46-view comparison. No new live capture was made.

## Steward validators

Steward validators: validate_actor_composites, validate_actor_monsters, validate_actor_recipes, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_objects, validate_audio_objects4, validate_charsel_items, validate_helpers, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_meshdraw, validate_model_edge, validate_model_light, validate_mount_visuals, validate_movement, validate_muun_passes, validate_muun_riding, validate_muun_secondary, validate_muun_special, validate_muun_visual, validate_path, validate_pets, validate_raven, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects26, validate_render_effects28, validate_session_party, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_worlds_f, validate_worlds_fog

All 43 latest row results pass, totaling 746,994 reported cases. The table records the most recent
passing run of each row: 1 at `6270622e`, 6 at `76f42724`, 26 at `88420149`, 4 at `8e992004`, 6 at `8ee7eaa0`.
These older rows retain unchanged inputs through the integrated main. Muun C/checker sources have not
changed since `76f42724`; the remote integration test changed at `6270622e` and passed privately at
`c37e14d6`. The earlier batch counts above are overlapping snapshots, not a distinct-case sum.

No mutants are needed in the steward run. Source the canonical private-env.sh from the repository root
for MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR and row-specific inputs.

| Validator | Reported cases | Wall | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 12.5 s | `88420149` |
| `validate_actor_monsters` | 1,437 | 71.2 s | `88420149` |
| `validate_actor_recipes` | 1,669 | 93.8 s | `88420149` |
| `validate_audio_callers` | 5,528 | 8.6 s | `8ee7eaa0` |
| `validate_audio_charsel` | 5,968 | 6.4 s | `76f42724` |
| `validate_audio_combat` | 19,548 | 46.3 s | `88420149` |
| `validate_audio_domains` | 2,544 | 28.3 s | `8ee7eaa0` |
| `validate_audio_items` | 3,000 | 4.6 s | `8ee7eaa0` |
| `validate_audio_objects` | 4,000 | 4.4 s | `88420149` |
| `validate_audio_objects4` | 10,093 | 8.6 s | `88420149` |
| `validate_charsel_items` | 8,817 | 10.3 s | `88420149` |
| `validate_helpers` | 8,667 | 203.8 s | `8e992004` |
| `validate_icarus_c2` | 8,400 | 24.1 s | `88420149` |
| `validate_inventory_fx` | 8,017 | 10.5 s | `88420149` |
| `validate_item_callers` | 6,013 | 2.1 s | `88420149` |
| `validate_items_ui` | 8,517 | 18.0 s | `88420149` |
| `validate_meshdraw` | 14,619 | 59.7 s | `88420149` |
| `validate_model_edge` | 954 | 179.2 s | `88420149` |
| `validate_model_light` | 1,433 | 6.0 s | `88420149` |
| `validate_mount_visuals` | 8,400 | 6.1 s | `8e992004` |
| `validate_movement` | 6,614 | 69.3 s | `8ee7eaa0` |
| `validate_muun_passes` | 1,361 | 1.5 s | `76f42724` |
| `validate_muun_riding` | 890 | 0.7 s | `6270622e` |
| `validate_muun_secondary` | 873 | 0.7 s | `76f42724` |
| `validate_muun_special` | 452 | 0.9 s | `76f42724` |
| `validate_muun_visual` | 912 | 1.2 s | `76f42724` |
| `validate_path` | 4,719 | 47.4 s | `88420149` |
| `validate_pets` | 1,062 | 153.7 s | `8e992004` |
| `validate_raven` | 4,000 | 169.7 s | `8e992004` |
| `validate_render_effects16` | 424 | 4.1 s | `8ee7eaa0` |
| `validate_render_effects17` | 618 | 10.0 s | `88420149` |
| `validate_render_effects18` | 540 | 2.4 s | `88420149` |
| `validate_render_effects19` | 400 | 1.3 s | `88420149` |
| `validate_render_effects24` | 226 | 3.3 s | `88420149` |
| `validate_render_effects25` | 202 | 11.1 s | `88420149` |
| `validate_render_effects26` | 348 | 15.5 s | `88420149` |
| `validate_render_effects28` | 630 | 3.7 s | `88420149` |
| `validate_session_party` | 200 | 0.9 s | `76f42724` |
| `validate_terrain` | 583,500 | 460.1 s | `88420149` |
| `validate_terrain_remaining` | 2,147 | 5.0 s | `88420149` |
| `validate_viewport_monsters` | 1,963 | 13.9 s | `88420149` |
| `validate_worlds_f` | 1,818 | 0.6 s | `88420149` |
| `validate_worlds_fog` | 4,044 | 10.4 s | `8ee7eaa0` |

## Limits and next

Four bone-effect mesh rows remain refused, plus appearance 357's unavailable mesh 3. Code 363 and 357
have only actions 0..2; no actions 3/4 are synthesized. Secondary particle consumers 0x8081/1, 0x8082/1,
0x7ef7/19 and remote effect consumer 0x47a remain outside this lane and refused. The effect lane owns them.

The random-bone caller comparison supplies its transform service. Native uses a bounded deterministic
fixture bone phase and does not recreate original RangedRandom distribution or global RNG phase. The fixture
authors its initial ride pose and clock; comparisons verify the bounded seat/lift/counter/first-action
caller, not complete original creation/render ordering. Constructor/pose services retain earlier documented
bounds. Remote periodic command clocks, authoritative target/rotation feeds and remote buff visibility are
excluded. Production selection, inventory, bonuses, damage, packets and character-power work remain excluded.
No installed-app, full-scene/live equivalence or strict performance claim.

## Checkpoints and cleanup

Checkpoints `8e992004`, `59822bfc`, `b8a03b96`, `76f42724`, `6e7965eb`, `fed9a7a4`, `0feb53c7`, `88420149`, `6270622e`, `fdd355f4` and `c37e14d6` were pushed with
progress/remaining-work records. This final handoff supersedes the WIP text. Scratch/renders use
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-004`. No future-lane input was created.
All documentation and final pushes precede the ready-prs entry; no push follows it. Task scratch/renders,
ignored builds/reports, the worktree and local branch are removed; the remote branch remains for the steward.

## WIP: latest-main UI refresh

All results above pass through main `a95880c4`. While recording the final audit, main advanced to
`4480bf41` (UI-WINDOWS-004). No ready queue entry or PR exists.
Done: all Muun implementation, original comparisons/mutants, private controls, proof and exact incoming
Kanturu identity comparison; repository audit is green for the preceding integrated candidate.
Left: integrate the new UI source, refresh only affected checks, update final binary/proof/audit results,
then push, open PR, append the ready entry and clean up. Next: inspect/merge UI-WINDOWS-004 and build.
