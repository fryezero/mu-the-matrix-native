# MUUN-VISUAL-003

PR-ready verified subset on `codex/muun-visual-003`. Main `c35458a0` is integrated through merge
`5085c66b`; the source checkpoint is `dbd8328b`. The merge steward owns integration. Offline/static only.
No installed-app, live client, service, packet, protection, actor-lane, item-table, particle-consumer or
README edits were authored in this lane. Incoming UI/actor changes came from main.

## What draws

Eight kind-1 records, ids 16/17/100..105, now have a separate secondary-body fixture. Set
`MU_MUUN_FIXTURE=<id>` and `MU_MUUN_MOUNT_FIXTURE=1`. Without the second variable, the existing base-only
fixture remains. The second skeleton loads by its actual BMD header name, uses original scale and speed,
copies the owner's position/angles, and owns independent pose/bone/texture storage. An authored 25-step
cycle supplies owner actions 1/65/248, selecting secondary actions 0/2/4. It changes no hero action or stats.

The named `Bip01 Spine1` attachment offset is posed and exposed, scaled once with the original +30 z.
All eight installed skeletons resolve bone 4. Missing, dummy, unresolved and out-of-range bones are refused.
The secondary body shares the base slot's terminal owner key/generation/death lease. Selection mismatch,
hidden owner, buff 0x1a, mount predicate and frustum hiding suppress it. Ordinary fixture flags are explicit.

A fresh table join confirms the original fifteen appearances still have eight extra rows on five models;
the other ten have zero rows, not missing implementations. The kind-1 base companions additionally verify
nine existing ordinary mesh rows on ids 101/103/105, three each. All other kind-1 records have zero rows.
The existing ordinary adapter renders them without a production-code change to mesh-pass arithmetic.

The hero is not lifted or re-posed onto the mount. This is a secondary-body/attachment-offset subset,
not a complete mounted-rider appearance. [Addresses, method and limits](../research/client-muun.md).

## Final checks

Commands ran from the repo root, heavy jobs at nice 10, make at most four jobs and runners two workers.
Canonical private-env.sh supplies private inputs. One early probe/test batch started before its high-load
output was inspected; later launches use separate resource probes. No full lane gate or hosted workflow ran.

| Check | Result | Wall |
|---|---|---:|
| Root build | pass; initial final build and two main refreshes | 10.53 + 6.95 + 11.20 s |
| New secondary original comparison and one-time mutants | 873 cases, zero mismatches; 16/16 mutants compile under `-Werror` and are caught | 7.10 s |
| Final private Muun modules | 11/11 pass; all 23 audited records, exact named bone, 16 attachments, 17 mesh rows, poses, leases/refusals and GL/software controls | 19.48 s |
| Added kind-1 base mesh audit, included above | 24 installed original mesh-caller cases at three clocks, zero mismatches; reused command/shadow controls also pass, 385 total | included above |
| Final focused portable modules | 2 passed, 9 explicit private skips | 0.60 s |
| Affected private validators at `a03c51e0` | 30/30 pass, 703,901 reported row cases, zero skipped rows | 562.05 s including selection |
| UI-merge validator refresh at `448f947c` | 12/12 pass, zero skipped rows | 170.97 s including selection |
| Actor-merge validator refresh at `dbd8328b` | 26/26 pass, zero skipped rows; unrelated symbol-pruned rows not repeated | 342.46 s including selection |
| Original affected portable batch | 157 items; 1,437 tests, 1,186 passed, 251 skipped, zero failures/errors | 386.97 s including selection |
| UI-merge portable refresh | 138 items; 1,452 tests, 1,180 passed, 272 skipped, zero failures/errors | 281.33 s including selection |
| Actor-merge portable refresh | 165 items; 1,522 tests, 1,260 passed, 262 skipped, zero failures/errors | 500.20 s including selection |
| UI-merge private world refresh | 3/3 pass | 16.53 s |
| Final native proof | 32 GL PNGs, eight bodies at actions 0/2/4, zero texture/mesh/bone refusals; contact sheet inspected; all 32 equal the inspected pre-merge images | 10.51 s |
| Default before sweep | 46 views, no draw-all/live-time, 640x400 | 30.31 + 59.46 s |
| Final after sweep | 92/92 PNGs, 92/92 dumps and 46/46 normalized reports identical | 22.86 + 36.19 s |
| Repository audit | 2,236 staged files, zero rejected | 17.20 s |

**8d reduced:** original selection contains 152 native work items, above forty. Both direct Muun modules
ran privately, including the final installed-record comparison extension. Shared-symbol grep finds no
other native host using the changed Muun fields/functions. Subsequent main merges received their selected
portable/private validator refreshes, and the final private Muun modules cover the integrated world binary.
The final two test assertions and installed mesh sample extension passed in the focused runs above.
No unchanged mutant set was repeated. The ordinary-pass checker and arithmetic are unchanged.

Constructor comparison uses an already allocated OBJECT and named base-setup/model/pose services;
allocation is static-audited and native ownership is tested separately. Attachment comparison supplies
the named-bone zero-point service and verifies caller scaling/+30; it does not replace the existing verified
model transform. No full original-scene or live-motion equivalence is claimed.

## Default identity

Both binaries were explicitly checked with `make -C native -j4 world` before their sweeps. Before, main
`626abce1`, SHA-256 `0486f35e813b641f2500df6b0107515c33d3fb37d2cc3683005c8b91b08b10ef`.
Final after, with both main merges, SHA-256
`69f62bc81a96af599172574ddfbb3cd02abb6edc7c2850a75929b72c93a14963`.
They are different executables. All 230 compared files match. Only output-directory prefixes are normalized
in the 46 reports; PNGs and OBJECT/light dumps match raw bytes. The before baseline was taken once.
The first pre-merge after sweep also matched; incoming compiled world changes justified the final replay.
Historical manifests with stale paths failed before output and were replaced with the current paths.

## Steward validators

Steward validators: validate_actor_composites, validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_app_polish7, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_objects, validate_charsel_items, validate_gfx3, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_map_polish, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_muun_secondary, validate_path, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects28, validate_session_party, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_worlds_f, validate_worlds_fog

The table gives each row's most recent passing run, including conservative fallback rows. The three batch
snapshots above retain earlier counts. Muun production inputs equal `a03c51e0`; main's UI and actor inputs
are integrated. Only tests/docs were extended after `dbd8328b`, as covered by the final focused runs.
No mutants are needed in the steward run. Source `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from
the root for MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR and row-specific inputs.

| Validator | Reported cases | Wall | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 9.5 s | `dbd8328b` |
| `validate_actor_recipes` | 1,669 | 124.0 s | `dbd8328b` |
| `validate_app_polish1` | 752 | 30.9 s | `dbd8328b` |
| `validate_app_polish2` | 1,028 | 4.8 s | `dbd8328b` |
| `validate_app_polish4` | 10,485 | 38.0 s | `dbd8328b` |
| `validate_app_polish7` | 5,120 | 2.4 s | `448f947c` |
| `validate_audio_callers` | 5,528 | 7.0 s | `dbd8328b` |
| `validate_audio_charsel` | 5,968 | 4.5 s | `a03c51e0` |
| `validate_audio_combat` | 19,548 | 49.0 s | `dbd8328b` |
| `validate_audio_domains` | 2,544 | 34.7 s | `dbd8328b` |
| `validate_audio_items` | 3,000 | 7.0 s | `dbd8328b` |
| `validate_audio_objects` | 4,000 | 6.1 s | `dbd8328b` |
| `validate_charsel_items` | 8,817 | 10.5 s | `dbd8328b` |
| `validate_gfx3` | no aggregate reported | 7.8 s | `448f947c` |
| `validate_icarus_c2` | 8,400 | 30.4 s | `dbd8328b` |
| `validate_inventory_fx` | 8,017 | 10.4 s | `dbd8328b` |
| `validate_item_callers` | 6,013 | 1.6 s | `dbd8328b` |
| `validate_items_ui` | 8,517 | 17.8 s | `dbd8328b` |
| `validate_map_polish` | 876 | 1.0 s | `448f947c` |
| `validate_meshdraw` | 14,619 | 61.0 s | `a03c51e0` |
| `validate_model_edge` | 954 | 132.4 s | `a03c51e0` |
| `validate_model_light` | 1,433 | 7.0 s | `a03c51e0` |
| `validate_movement` | 6,614 | 71.3 s | `dbd8328b` |
| `validate_muun_secondary` | 873 | 0.8 s | `dbd8328b` |
| `validate_path` | 4,719 | 30.6 s | `a03c51e0` |
| `validate_render_effects16` | 424 | 4.7 s | `dbd8328b` |
| `validate_render_effects17` | 618 | 11.3 s | `dbd8328b` |
| `validate_render_effects18` | 540 | 2.3 s | `dbd8328b` |
| `validate_render_effects19` | 400 | 1.4 s | `dbd8328b` |
| `validate_render_effects24` | 226 | 3.6 s | `dbd8328b` |
| `validate_render_effects25` | 202 | 12.5 s | `dbd8328b` |
| `validate_render_effects28` | 630 | 3.5 s | `dbd8328b` |
| `validate_session_party` | 200 | 0.8 s | `a03c51e0` |
| `validate_terrain` | 583,500 | 402.9 s | `a03c51e0` |
| `validate_terrain_remaining` | 2,147 | 4.0 s | `a03c51e0` |
| `validate_viewport_monsters` | 1,963 | 13.8 s | `dbd8328b` |
| `validate_worlds_f` | 1,818 | 0.4 s | `a03c51e0` |
| `validate_worlds_fog` | 4,044 | 8.2 s | `dbd8328b` |


## Limits and next

Rider placement/action mutation, secondary model-specific `0x009bfe13` effects, owner-kind-2 fade and
buff-0x12 render mode are not implemented. The fixture uses ordinary owner flags. Remote transition clocks
and `0x47a` requests remain open; the native effect consumer does not admit that type, and this lane owns no
particle-consumer change. A follow-up needs that consumer and an authored clock before transition pixel proof.
The five special mesh models refused in 002 remain refused. Code 363 still refuses unavailable actions 3/4.
Production selection, inventory, bonuses, damage, packets and authoritative command/target feeds remain excluded.
No installed-app, full-scene/live equivalence or strict performance claim.

## Checkpoints and cleanup

WIP checkpoints were pushed at `a03c51e0`, `6434f2fe`, `7d8a5752` and `dbd8328b`, each recording done/left/next.
The final delivery replaces the WIP text with verified results. Scratch and renders use
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-003`. No future-lane input was created.
After the ready queue entry, no further push is permitted. Generated outputs, builds, worktree and local
branch are removed; the remote PR branch remains for the steward.
