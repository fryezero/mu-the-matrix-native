# AUDIO-004: owner review and explicit object audio commands

Branch `codex/audio-004`, based on and integrated with main `b7dfd2ed`.
Offline/static only; pinned captures and authored fixtures. This is a verified
subset, not whole-client sound completion.

## Census

The reproducible inventory is `scripts/audio_caller_census.py --report <local>`.
It publishes addresses, authored classifications, source references, sound-id
status, gate disposition and native-owner status, without client bytes or asset
paths. [Method, exact site allowlist and gates](../research/client-audio.md#audio-004-owner-review-and-explicit-object-commands-2026-11-14).

| Owner bucket | AUDIO-003 | AUDIO-004 |
|---|---:|---:|
| UI | 20 | 51 |
| Hero/shared actions | 37 | 43 |
| Skills/effect timelines | 263 | 272 |
| Monsters/NPC voices | 781 | 848 |
| World objects/ambient | 111 | 135 |
| Items | 9 | 15 |
| Events/progression | 4 | 4 |
| Unresolved owner | 755 | 612 |
| Total | 1,980 | 1,980 |

Owner buckets rise 1,225 -> 1,368, through 143 additional classifications.
The denominator remains the historical syntactic E8-target scan, not a CFG
proof. A nearby prologue remains only a grouping aid. Existing exact owner
references and reviewed class vtable slots supply the new classifications;
a validator-stub-only reference was rejected. Unknown gates and ids stay
explicit. A bounded source reference does not establish a whole native owner.

Enumerated audio boundaries rise 129 -> 162: 113 earlier boundaries, 16 from
AUDIO-003 and 33 here. Shared original sites count once; repeated ids do not
collapse sites. Conditional fixture-owned boundaries retain their input limits.
No newly classified unknown is wired solely because its bucket is now known.

## Wired and refused groups

| Owner | New sites | Disposition |
|---|---:|---|
| Imperial Guardian pre-move | 4 | World-only 0x38f and three handler-state branches. The runtime retains state 0; the latter three are fixture-bound until an existing owner can supply known state. No event input is added |
| Karutan pre-move | 1 | Types 0x3a/0x42, 0x3db with OBJECT, worlds 80/81 |
| Swamp of Darkness pre-move | 5 | Existing random/action/tile gates; the two 0x4d2 sites retain distinct provenance |
| Old Kethotum | 9 | Near, swing and gate requests; the action-1/action-2 closing and action-0/action-3 opening sites remain distinct |
| Burning Kethotum | 12 | The common template, two 0x54b sites and the existing type-0xb5 cycle inputs |
| Ignis | 2 | Type 177, action 1/frame < 8 versus action 3/frame > 28; both 0x570 sites retain their original OBJECT |
| Class monster selectors | 0 | 48 classes, 40 distinct slot +0x70 entries and 524 candidates, none with a bounded native reference. Whole owners/dispatch remain absent; shared combat services are separate |
| Kubera play/stop sequences | 0 | Stop 0x4f2 -> play 0x4f1, or stop 0x4f1 -> play 0x4f2, require a separately compared stop command and ordered delivery |
| Unknown-owner remainder | 0 | 612 candidates, not a claim of 612 absent native sounds |

The exact 33-row routine/site/id/object/loop allowlist is
`reconstructed/audio/object_audio_sites.inc`. All loops are 0. The selected
request stores original routine/site/tag in unused event tail words 13..15;
the event ABI, count and normalized original arguments remain unchanged.
Kethotum annotations run before SetAction rewrites the distinguishing action.
Overflow cannot annotate an earlier event; existing provenance cannot be replaced.

The world callback borrows the event synchronously, validates the complete
command and forwards it through the independent session audio reader or the
immediate standalone host. Consuming a command skips the old id-only callback,
preventing duplicates. Disabled readers drain now; detached requests have no
backlog. The old AUDIO-003 mappings remain intact. SND_Play still ignores the
object and uses the Effect group; keys -3/-2 denote unkeyed OBJECT/NULL, never
pointers. No RNG, object/model/animation, visual or replicated-state field changes.

Held ambient gates intentionally request repeatedly. Existing SND active-id
suppression and the original owner transitions supply trigger behavior; no new
once-per-action filter removes later eligible requests.

The world/object runtime changes are added callback lines only, plus the new
callback field and include. Reconstructed owner changes are annotation lines
and includes only. No actor, item, UI controller or registration logic changes.

## Music

No selector or mixer changes. Static world/zone music retains its earlier
AUDIO-003 delivery and evidence. The new installed smoke covers sound IDs only.
No FMOD mixer parity is inferred from decoded PCM.

## Verification

Tested source and validator commit:
`06782ac403d6ac57f8ab5f578db707f53f92a5d5`. Runtime inputs are the same as
checkpoint `d22b1559`; the next source commit corrects the Swamp body end
after its last sound. All selected sites keep the same owner, gates and mutant
detections.
Checkpoint `29a8f8a5` and the finish commits change documentation only.

- Root build passes, **13.08 s**. Explicit final `make -C native -j4 world`
  passes, **0.20 s**. The initial root/world builds preceded lane edits.
- Original command comparison: **10,093 cases**, all **33 sites** reached,
  zero mismatches/stops. Ten existing complete owner families plus 93
  deterministic site/boundary cases retain AL where applicable, OBJECT/action
  records, normalized full call order and RNG. Original SND_Play return
  addresses/arguments independently supply expected commands.
- Compiled mutants ran once against the production inputs: **10/10 caught,
  65.52 s**. They cover tag loss, Ignis sites, pre-action gate context,
  closing/brazier/Swamp/Guardian sites, object, loop and id. The unchanged
  validators' mutants are not repeated. The final unmutated new row passes
  again in **5.2 s**.
- Affected portable run: **167 work items**, including **159 native modules**.
  Nine reported suite groups, **1,761 tests: 1,445 passed, 316 explicit skips,
  zero failures/errors**. Runner wall 386.7 s; **458.71 s** command wall
  including selection. The initial banner names 38 registered directories.
- **8d reduced**: 159 native modules exceed the 40-item cap. From repository
  root with canonical `private-env.sh`, the added native module passes
  **7/7, zero skips/failures, 7.70 s**. This covers exact cues, independent
  readers, active-id suppression, mute/disabled/detached no-replay behavior,
  pre-SetAction provenance, three actual synthetic world paths and equal
  audio-on/off frames. It also decodes **all 20 distinct new IDs** from
  read-only installed inputs with `--no-options`; all play requests resolve
  and mixed PCM is nonzero. No full private registry or lane full gate ran.
- The pinned census module passes **2/2, 1.50 s**, with explicit unknown-owner
  and new-boundary counts kept separate.
- All **77 affected validators pass**, zero failures/errors/skips,
  **1,149,289 cases/checks**, **800.21 s** command wall. Every selected fallback
  row remains. All run without optional mutants.
- Repository audit: **2,272 staged files, zero rejected, 20.39 s**.
  Source/spec self-review passed for exact provenance, unchanged gates/order,
  borrowed callback lifetime, overflow, mute/no-replay and added-lines scope.
  No independent reviewer, live fidelity or FMOD equivalence is claimed.

### Default identity

Both binaries were explicitly rebuilt as world targets and are distinct.
The starting-main binary was preserved before edits; the after hash is checked
again after rendering.

- Before, main `b7dfd2ed`:
  `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- After, the final compiled inputs:
  `348d832d38a5173906ff0a1e992f7a3b2d0b8ee5f86f6401b5a16b1db6958e46`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24.
All native renders use demo name Preview. Normalization changes only the output
directory prefix and compares every JSON row/value. No scene data is removed.

| Dataset | PNG identity | OBJECT/light identity | Reports | Before / after render wall |
|---|---:|---:|---:|---:|
| October 22, 14 views | 28/28 | 28/28 | 14/14 | 14.47 / 15.87 s |
| DATA-ACQ-002, 32 views | 64/64 | 64/64 | 32/32 | 46.45 / 59.14 s |

Totals: **92/92 PNGs, 92/92 dumps and 46/46 normalized reports identical**.
After sweep command wall **75.04 s**; byte/report comparison **0.21 s**.
These are repeatability controls, not original-client visual equivalence.

### Steward validators

The source and validator inputs were tested at
`06782ac403d6ac57f8ab5f578db707f53f92a5d5`. Source canonical
`~/Documents/MTM/mu-mac-tools/native/private-env.sh` from repository root.
No further mutants are needed. Post-build selection retained 77 rows and pruned
eight changed-library rows that use no changed symbol. The new callback field
reaches native object hosts; 6b/8b consumers and conservative fallbacks were kept.
The existing event record layout, capacity and normalized arguments did not change.

Steward validators: validate_charsel_world,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_terrain,validate_world_fidelity,validate_terrain_remaining,validate_render_worlds_a,validate_audio_events,validate_audio_music,validate_audio_voices,validate_icarus,validate_worlds_b,validate_icarus_c2,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_audio_callers,validate_worlds_h,validate_worlds_i,validate_audio_domains,validate_worlds_j,validate_worlds_k,validate_audio_items,validate_worlds_o,validate_worlds_n,validate_worlds_p,validate_worlds_r,validate_world_tile_folder,validate_worlds_g2,validate_world_light_name,validate_worlds_p2,validate_worlds_r2,validate_worlds_q,validate_worlds_q2,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_app_polish1,validate_app_polish4,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_worlds_inner,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_worlds_inner2,validate_audio_objects,validate_render_effects28,validate_worlds_inner3,validate_items_ui,validate_audio_objects4

| Validator | Cases/checks | Wall seconds |
|---|---:|---:|
| `validate_actor_composites` | 1427 | 8.6 |
| `validate_actor_recipes` | 1669 | 120.5 |
| `validate_app_polish1` | 752 | 17.9 |
| `validate_app_polish4` | 10485 | 30.2 |
| `validate_audio_callers` | 5528 | 6.8 |
| `validate_audio_domains` | 2544 | 27.9 |
| `validate_audio_events` | 70980 | 5.6 |
| `validate_audio_items` | 3000 | 4.2 |
| `validate_audio_music` | 4291 | 0.5 |
| `validate_audio_objects` | 4000 | 11.7 |
| `validate_audio_objects4` | 10093 | 5.2 |
| `validate_audio_voices` | 2182 | 0.1 |
| `validate_charsel_items` | 8817 | 7.5 |
| `validate_charsel_world` | 1200 | 2.0 |
| `validate_icarus` | 5240 | 40.5 |
| `validate_icarus_c2` | 8400 | 21.8 |
| `validate_inventory_fx` | 8017 | 7.0 |
| `validate_item_callers` | 6013 | 1.1 |
| `validate_items_ui` | 8517 | 19.0 |
| `validate_login_world` | 1200 | 2.0 |
| `validate_meshdraw` | 14619 | 55.0 |
| `validate_model_edge` | 954 | 123.2 |
| `validate_model_light` | 1433 | 7.1 |
| `validate_movement` | 6614 | 64.4 |
| `validate_object_render` | 1984 | 3.2 |
| `validate_render_effects16` | 424 | 3.1 |
| `validate_render_effects17` | 618 | 6.3 |
| `validate_render_effects18` | 540 | 0.9 |
| `validate_render_effects19` | 400 | 0.7 |
| `validate_render_effects24` | 226 | 2.1 |
| `validate_render_effects25` | 202 | 10.9 |
| `validate_render_effects26` | 348 | 9.3 |
| `validate_render_effects28` | 630 | 2.1 |
| `validate_render_worlds_a` | 9000 | 13.6 |
| `validate_terrain` | 583500 | 452.5 |
| `validate_terrain_remaining` | 2147 | 4.1 |
| `validate_world_fidelity` | 200 | 0.2 |
| `validate_world_light_name` | 304 | 0.4 |
| `validate_world_tile_folder` | 5700 | 58.6 |
| `validate_worlds_121` | 4000 | 3.4 |
| `validate_worlds_after` | 13424 | 12.1 |
| `validate_worlds_after2` | 32216 | 37.6 |
| `validate_worlds_after3` | 10212 | 11.2 |
| `validate_worlds_after4` | 9181 | 17.3 |
| `validate_worlds_after5` | 6000 | 20.9 |
| `validate_worlds_after6` | 7300 | 63.6 |
| `validate_worlds_b` | 4000 | 4.7 |
| `validate_worlds_d` | 2400 | 3.9 |
| `validate_worlds_e` | 4840 | 18.5 |
| `validate_worlds_f` | 1818 | 0.4 |
| `validate_worlds_fog` | 4044 | 6.0 |
| `validate_worlds_g` | 6000 | 4.0 |
| `validate_worlds_g2` | 2657 | 10.6 |
| `validate_worlds_g3` | 4000 | 4.7 |
| `validate_worlds_h` | 6000 | 3.9 |
| `validate_worlds_i` | 6000 | 4.0 |
| `validate_worlds_inner` | 4000 | 2.3 |
| `validate_worlds_inner2` | 5000 | 5.8 |
| `validate_worlds_inner3` | 8000 | 7.7 |
| `validate_worlds_j` | 6000 | 5.3 |
| `validate_worlds_k` | 6000 | 5.5 |
| `validate_worlds_karutan` | 3000 | 3.2 |
| `validate_worlds_n` | 13000 | 10.1 |
| `validate_worlds_o` | - | 7.0 |
| `validate_worlds_p` | 10000 | 10.0 |
| `validate_worlds_p2` | 6000 | 4.5 |
| `validate_worlds_q` | 11000 | 11.5 |
| `validate_worlds_q2` | 4000 | 6.4 |
| `validate_worlds_r` | 12000 | 13.1 |
| `validate_worlds_r2` | 9000 | 5.9 |
| `validate_worlds_raklion` | 3000 | 2.6 |
| `validate_worlds_s` | 11000 | 6.9 |
| `validate_worlds_s2` | 10000 | 5.9 |
| `validate_worlds_s3` | 22000 | 11.4 |
| `validate_worlds_slots` | 18999 | 12.4 |
| `validate_worlds_slots2` | 33000 | 22.8 |
| `validate_worlds_slots3` | 36000 | 22.6 |

## Next

Recover the 612 unresolved semantic owners, starting with the large
0x01080169/0x0108988b groups; do not turn prologue proximity or a literal id into
an admission. For monsters, recover a whole slot +0x70 owner and its native
dispatch before wiring it; the 524 candidates there differ from existing shared
hit/attack/death services. Kubera needs an explicit stop operation and original
stop/play ordering. Guardian's three state-bound sites retain their fixture limit.

No event feed, pickup answer, transformed/buff input, server state, new request
route or FMOD mixer parity is added. The virtualised frame interval
0x01854279..0x018542c2 remains excluded and unfollowed.

## WIP checkpoints, completed

`d22b1559` was pushed at the first checkpoint with done/left/next notes.
`29a8f8a5` was pushed at the next checkpoint with the portable results and
remaining private checks. Both WIP states are superseded by the green results
above. Resource guards paused new work during shared-host spikes; no extra
lane gate or unchanged optional mutant run was started.

Main was fetched again before finish and remains `b7dfd2ed`; no compiled-input
integration rerun is needed. At PR-ready all documentation/pushes precede the
single ready-prs line. Nothing is pushed afterward. Task-local scratch/identity
renders and ignored build reports are not future inputs. Remove them, the
worktree and local branch; retain the remote branch for the steward.
