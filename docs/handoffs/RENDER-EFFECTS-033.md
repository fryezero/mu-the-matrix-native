# RENDER-EFFECTS-033

PR-ready verified fixture subset. The steward owns the combined gate and merge.

Branch `codex/render-effects-033` starts from EFFECTS-032 `b8ef0051` and merges
main `6900914e` at `92adab2c`, including EFFECTS-031. Subsequent main integrations
are batch 115 `df57ab8b` at `63752052`, AUDIO-005 `8844d3e9` at `5ce2d9ce`,
INNER-005 `d3ec9950` at `ef6f7e20`, and UI-WINDOWS-005 `c5b9d5ca` at `6cd965c2`.
Final full proof and actual-asset fixtures use that combined production tree.
The integrated revision includes the EFFECTS-030 regression correction. Later
commits contain delivery docs only; no 033 production input changed.
No subagents or full lane gate. Heavy work uses nice 10, make at most four
jobs and two validator/test workers, with resource pauses.

## Skill audit and implemented boundary

The verified fixture boundary moves **11 P / 7 L / 11 M to 14 P / 6 L / 9 M**.
P is bounded primary presentation, L a visible subset, M missing primary
presentation. It is not a whole-client fidelity score or an eligibility claim.
Swell Life is a reassessment of the combined 031 consumers and 030 caller,
not a newly authored consumer in this lane.

| Skill | Before -> after | Current boundary |
|---|---|---|
| 0 ordinary attack | P -> P | Unchanged |
| 19 Falling Slash | P -> P | Unchanged |
| 20 Lunge | P -> P | Unchanged |
| 21 Uppercut | P -> P | Unchanged |
| 22 Cyclone | P -> P | Unchanged |
| 23 Slash | P -> P | Unchanged |
| 41 Twisting Slash | P -> P | Unchanged |
| 42 Anger Strike | P -> P | Unchanged |
| 43 Death Stab | L -> L | General equipment/link selection remains open |
| 44 Crescent Moon Slash | L -> L | End consumer 0x49e/0 remains refused |
| 18 Defense | L -> L | Finite pose; held-input renewal/release and shield body context unproved |
| 47 stale entry | M -> M | Always refused; no invented record |
| 48 Swell Life | M -> P | Combined bounded cast: 36 initial ribbons, 36 children and two ground effects; zero unsupported requests |
| 49 Fire Breath | M -> M | Primary 0x8001/0 and mount body/lifetime remain missing |
| 344 Blood Storm | M -> L | Parent and sword body work; downstream burst, particle and blur consumers remain counted refusals |
| 24 Triple Shot | P -> P | Unchanged bounded caller/context |
| 26 Heal | P -> P | Unchanged |
| 27 Greater Defense | L -> L | General equipment links and authoritative presence remain open |
| 28 Greater Damage | L -> L | Same bounded aura boundary |
| 30 Summon Goblin | M -> M | Ground supported; matching-name candidate 26 has a body/weapon plan on ACTORS-007; spawn/lifetime input unproved |
| 31 Summon Stone Golem | M -> M | Ground supported; matching-name candidate 32 has checked body; spawn/lifetime input unproved |
| 32 Summon Assassin | M -> M | Ground supported; candidate 21 has checked body; spawn/lifetime input unproved |
| 33 Summon Elite Yeti | M -> M | Ground supported; candidate 20 has checked body; spawn/lifetime input unproved |
| 34 Summon Dark Knight | M -> M | Ground supported; candidate 10 also lacks actor effect/sword-sprite services |
| 35 Summon Bali | M -> M | Ground supported; candidate 150 has checked body; spawn/lifetime input unproved |
| 36 Summon Soldier | M -> M | Ground supported; candidate 151 also lacks actor effect services |
| 51 Ice Arrow | L -> P | Existing arrow plus separately authored target ice; no freeze or damage input inferred |
| 52 Penetration | L -> P | Existing charge/arrow plus the owned child and four trails |
| 2044 Raining Arrow of Saturation | P -> P | Unchanged |

Explicit synthetic aliases 416/52 and 424/51 move L -> P outside those 29 rows.
All other aliases keep their prior refusal/inventory state. Candidate actor
names match the existing read-only language snapshot; that is not proof of a
skill spawn selector. Main's ACTORS-006 body plans are used only as read-only
census evidence, and no ground request is converted into actor creation.


The final full sample on integrated main c5b9d5ca passes 32,010 grouped checks
at 1,000 cases per pair, no mutants, in 71.666 s. The forty-five completed
controls are retained without repetition. Thirteen explicit DemoKnight /
DemoArcher asset scenes pass retirement, zero sent requests/hits/kills and
unchanged target HP. Blood Storm records 1,883 downstream refusals; other new
skill fixtures record zero. Each summon ground emits 63 ribbons across its
native life-20 schedule, with a sampled peak of 36 live joints; no actor is
created. Exact per-skill counts and final identity results are in the handoff.


## Consumers and native integration

Twelve new pairs: six effects, five joints and one particle. The inherited
EFFECTS-031 pairs, including reserved 0x47a, remain unchanged.

| Consumer | Original boundary | Recovered behavior |
|---|---|---|
| Effect 0x7f84/3 | create 0x013c80a3; move 0x0143fbda | Ground emitter with initial lifetime 20, three JointEnergy01/3 children per step; exact default key -1 |
| Joint 0x7fd8/3 | Existing Energy01 dispatch | Same homing/lifetime as subtype 1, orange (L, .6L, .4L) palette |
| Effect 0x46c/0 | 0x013ca40b..0x013ca7ec; 0x01463c5e..0x0146409b | Owner live/position/angle, saved prior position, heading spin; four Flare02 trails, key 30, skill 0; sound 0x7a |
| Joint 0x7f79/0..3 | Flare02 dispatch | Caller width/radius, three substeps, owner heading/impact; 50-tail capacity, closing tail, fade and owner death |
| Effect 0x412/1,2 | 0x013d01f8..0x013d04e1; 0x0146bbb8..0x0146bfef | Target presence ID 0x39; action-dependent hidden-all flag; frame hold, fade, subtype-1 orbit/Fire03; source-light mutation |
| Particle 0x7f3e/10 | Fire03 uses Fire01 cases | Life 24, ordered velocity/rotation RNG, shrink .95, vertical gravity, four-frame strip and full GL stream |
| Effect 0x583/0 | 0x013f2b83; 0x014a18fc | Life 70, caster-owned 0x584, sound 0x2b0; ten jittered 0x585 requests and central 0x586 |
| Effect 0x584/0 | 0x013f2c53; 0x014a1b1c..0x014a2131 | Owner +0x3b must equal 1; life 36, .35 animation; bone-zero 0x4b7/1, 55 blur calls over eleven exact bones, brightness ramp |

Piercing.bmd and blood_storm_sword.bmd use the exact static loader paths.
Fire03 adds bitmap slot 96, before Fire06, growing the bitmap array 99 to 100.
The target-ice constructor's source-light mutation reaches the second request.
The parent arrow preserves sign-extended key, word8 -1 and self ownership;
the child creates all four trails with key 30. Native refreshes an arrow's
object view immediately after its move, before later owned effects read it.
The callback host and compiled controls cover this same-step lifetime boundary.

`MU_SKILL33_TARGET_ICE` is an explicit positive visual tick count up to 10,000,
default zero; invalid values disable it. It runs only the recovered optional
visual slice, deletes old subtype 1, creates 1/2 and owns a separate visual
presence expiry. It does not infer target freeze from an arrow or change actor
movement, HP or state. `MU_SKILL33_BLOOD_OWNER=1` supplies only the owner's
read-only +0x3b view; absent, zero and invalid values disable the sword body.

Blood Storm poses once at frame minus .35, then reuses that pose for all five
outer samples and eleven exact bones. The original loop's unused local frame
increments do not justify invented interpolated poses. Action 0 and the ten
constructor-reachable parent indices are the admitted subset. Downstream burst,
particle, bone-effect and blur requests remain counted refusals.

## Original proof

The final full sample at `6cd965c2` passes **32,010 checks**, 1,000 cases per
pair, no mismatches or original-machine stops, **71.666 s**. The registry keeps
a 200-case sample, **6,410 checks**. Ordered requests, records, RNG, owner/key/
default words, target caller, model/bitmap loaders, complete joint/particle GL
streams, Blood Storm pose/bones/blur arguments and native callbacks are checked.
The [research note](../research/client-render-effects-033.md) records original
routine boundaries, request-only exclusions and the initial eighteen-row audit.

Target SHA-256:
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Text: `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Data: `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

All **45 new compiled controls** are detected, zero original stops. Fourteen
completed before a harness-only target-ice argument-count error. Only the
remaining 31 resumed after the dispatcher correction. Execution walls are
44.426 + 73.402 s; no successful compiled control is repeated. The old Fire06
validator's three anchors had to preserve the new Fire03 labels. Its complete
424-check baseline and those **three changed controls** pass in 6.282 s.
These are 45 new plus three refreshed controls, not 48 new controls. No further
mutants are requested from the steward.

Animation, model/bone, terrain and presence service answers are authored
fixture inputs. This proves the stated instruction slices and native adapter
contracts, not original GPU appearance, full-client RNG phase, pool equivalence,
eligibility or authoritative state. Skill 47 and stale learned capacity stay
outside admission. Existing 030/032 validators retain per-skill and explicit
alias request comparisons, rather than admitting aliases by shared consumers.

## Native fixture proof

Thirteen read-only game-asset scenes use DemoKnight / DemoArcher, authored
DemoTarget at 122,120, or 124,120 for Penetration, caster at 120,120, 512x320,
100 frames saved every three, software backend and no audio/items/other players.
Each casts at frame 2 and stops at frame 3. There are **442 PNGs**. Target ice
uses 20 visual ticks for 51/424; only 344 supplies the Blood Storm owner flag.
All thirteen have zero sent / one unsent request, zero hits/kills, unchanged
target HP and empty effect, joint and particle pools at the final frame.
All active frames below were visually inspected. Each scene loads 31 effect models and all 39 combat bitmaps. Ground-only summon scenes do not create another actor.

| Skill | Effects created | Joints created | Peak effects | Peak joints | Refused | Inspected frame | PNG SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---|
| 344 | 2 | 0 | 2 | 0 | 1883 | 12 | `b875df4d1ab8c7861e20e5796b0c809fca16b7b1d3ffc64aad006dac9ff4334d` |
| 52 | 3 | 4 | 3 | 4 | 0 | 6 | `a48f19e20ef5ffb79a8b236f2eaf7d02a4d5ac5d273524ad75ad1269db7aed02` |
| 416 | 3 | 4 | 3 | 4 | 0 | 6 | `a48f19e20ef5ffb79a8b236f2eaf7d02a4d5ac5d273524ad75ad1269db7aed02` |
| 51 | 3 | 0 | 3 | 0 | 0 | 21 | `cafa9a8de1fd8ca0fb2bf1197f0c2574addec0c9b050afa0be068fc0b59f413c` |
| 424 | 3 | 0 | 3 | 0 | 0 | 21 | `cafa9a8de1fd8ca0fb2bf1197f0c2574addec0c9b050afa0be068fc0b59f413c` |
| 48 | 2 | 72 | 2 | 72 | 0 | 18 | `86faef62952a33bce4ad9c72e194d12e451450cfc1076fb73b1e810d51f54cc8` |
| 30 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |
| 31 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |
| 32 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |
| 33 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |
| 34 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |
| 35 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |
| 36 | 1 | 63 | 1 | 36 | 0 | 27 | `2e2e34b4213787160014b7f95ea52ffd8dbd589c67f7cd3658b9a7ec9f783300` |

Penetration/416 shows the short owned child and four trails at frame 6. Ice and
its orbit appear around the target by frame 21. Blood Storm shows the red sword
body but lacks the downstream burst/particle/blur. Swell Life's ring uses the
combined 030 caller and 031 consumers, with 36 initial ribbons plus 36 children.
Summon ground reaches 63 created ribbons and a sampled peak of 36, then retires;
the primary summon remains missing for all seven rows.

The first asset and identity captures omitted --hero-name and used the renderer's
hardcoded player label. They are discarded and excluded from final proof.
Only the corrected explicit-demo fixture set and identity pair count here.
The invalid identity attempt is not presented as a successful baseline. To
correct it without altering this branch or adding a worktree, the unchanged
`92adab2c` source was exported under lane scratch and freshly built. Its binary
hash exactly reproduces the initial baseline. No valid successful baseline is
repeated. The export preflight first used system Python without tar data-filter
support; it stopped before extraction and was rerun with the private Python.

## Default identity and binaries

Both valid versions run an explicit `make -C native -j4 world` immediately before
their sweep. Root make alone is insufficient. Before is `92adab2c`; after uses
combined production `6cd965c2`. Binary hashes are verified again after rendering.

- Before SHA-256: `ff56fde9144b9fbbb68af1a4f23ff352580815daf302766108fc65123e42b4b4`.
- After SHA-256: `8f815439409b831e53c72b1b8a9fe92c6e8afc197172fc7f2912b17dd981d270`.

Default world draw, explicit DemoKnight name, no draw_all/live_time, 640x400,
25 frames sampled at 0/24. One valid before sweep is 87.552 s, after 62.448 s.

| Dataset | PNGs identical | OBJECT/light dumps identical | Logs identical | Reports |
|---|---:|---:|---:|---|
| October 22, fourteen views | 28/28 | 28/28 | 14/14 | All fourteen have only the Fire03 bitmap insertion |
| DATA-ACQ-002, thirty-two views | 64/64 | 64/64 | 32/32 | All thirty-two have only the Fire03 bitmap insertion |

No view's pixels, OBJECT records or light grids change. Every report changes its
bitmap list from 99 to 100 through exactly one loaded entry at slot 96; the
remaining list is byte-for-byte equal after removing that one new entry.
All other report fields match after normalizing only the output-directory
prefix. The bitmap field is reported as a difference, not normalized away.
There are 230/276 raw files identical: 92 PNGs, 92 dumps and 46 logs. The 46
JSONL reports have output paths plus the stated bitmap metadata difference.
The skill callers are inactive in these default views. This is native identity,
not an original-client image-equivalence claim.

## Completed checks and test budget

Commands run from repository roots with canonical private-env. No full gate.
Selections retain all symbol fallbacks. After each main merge only its actual
incoming compiled-input selection runs again, without mutants; rows excluded
by that selection carry forward their last passing inputs. The latest current
lane selection has **86 rows**; all have passing coverage in the ledger below.
Counts in the ledger mix original comparisons and row-specific native controls.

| Check | Result | Command wall s |
|---|---|---:|
| Final integrated root build | pass | 0.401 |
| Grouped 033 controls | 6,410 equal; 45/45 compiled controls; zero original stops | 44.426 + 73.402 |
| Full 033 comparison, 1,000 per pair | 32,010 equal; no mutants | 71.666 |
| Refreshed EFFECTS-016 anchors | 424 checks and 3/3 changed controls pass | 6.282 |
| Focused new native fixtures | 5/5 pass | 5.826 |
| Initial affected private validators | 81/82 pass; remaining anchor preflight corrected above | 1,027.312 |
| Batch 115 incoming-input delta | 93/93 pass, no mutants | 3,554.113 |
| AUDIO-005 incoming-input delta | 73/73 pass, no mutants | 1,099.376 |
| INNER-005 incoming-input delta | 79/79 pass, no mutants | 1,237.713 |
| UI5 incoming-input delta | 12/12 pass, no mutants | 59.218 |
| Initial portable affected | 1,881 tests; one obsolete assertion, corrected below | 534.640 |
| Reduced private native, twelve modules | 59/60 initially pass; one intermediate assertion corrected below | 182.102 |
| Corrected EFFECTS-030 module, private | 6/6 pass, zero skips | 6.287 |
| UI5 portable delta | 1,411 tests, 1,112 pass / 299 expected skips, zero failures/errors | 418.074 |
| UI5 reduced private, five modules | 36 pass / 2 unchanged-mutant skips, zero failures/errors | 121.517 |
| Corrected actual-asset skill fixtures | 13 scenes, 442 PNGs; all retirement and no-damage assertions pass | 17.675 |
| Corrected baseline explicit world build | pass; reproduces original baseline SHA | 9.616 |
| Corrected final explicit world build | pass | 0.331 |
| Corrected baseline identity sweep | 46 views, 276 files | 87.552 |
| Corrected final identity sweep | 46 views; 92 PNGs / 92 dumps / 46 logs identical | 62.448 |
| Checkpoint 11 staged audit | 2,356 files, zero rejected | 28.908 |
| Final four documentation readers | 35 pass / 1 expected private skip, zero failures/errors | 9.276 |

The initial portable run's one failure is the obsolete 52/416 child-refusal
expectation. A temporary private-test edit also wrongly removed Blood Storm's
constructor particle refusal; that assertion is restored to one. The corrected
six-test module passes in private mode, and the later portable UI delta includes
030/032/033 and passes. No unresolved test failure remains. Failed exploratory
runs in the command ledger are not verification.

**8d reduced:** the initial private native selection is 181 work items, above
the forty-item cap. Twelve changed/added modules and changed-host readers run
with the canonical private environment: particles, 030/032/033, plain actors,
Muun riding/secondary/special/visual, AUDIO-005's two modules and INNER's host
reader. After the assertion correction all sixty unique tests are covered.
UI5 adds five changed modules: app_polish9, native_item_services, ui_indirect,
ui_windows4 and ui_windows5. Thirty-six pass; two unchanged mutation classes
are deliberately disabled. Portable private skips do not substitute for these
private runs. No unchanged mutation class is enabled.

**Packaging exclusion:** only `native/tests/test_native_app.py` is removed from
the portable affected work list. It is the only current test module referencing
codesign/build_native_app. The original portable selection has 182 work items;
UI5's incoming delta has 144. This is an owner-required task-local filter,
not a committed test change. No package, signing, install, installed-app journey,
Native Data refresh or README work occurs.

Documentation-reader module walls are 0.089 s for world_captures_2, 0.865 s
for repository_policy, 0.962 s for native_item_textures and 8.346 s for
native_data_manifest. The final publication audit and its wall are recorded
in the PR body; no source edits follow that audit.

## Steward validators

Canonical `private-env.sh` supplies MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT,
MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR, MU_LANG_DIR, snapshots and
row-specific paths. Run `scripts/run_validators.py --private --no-mutants --cache
--affected origin/main --jobs 2`; retain the current selection and fallbacks.
**No further mutants needed.** The exact queue/PR selection has 86 rows. The
162-row ledger also retains incoming-main-only checks. Each row records its
latest successful measured run and tested source commit. Later commits are
documentation or the stated legacy expectation correction only.

| Validator | Cases | Wall s | Tested commit | Role |
|---|---:|---:|---|---|
| `validate_actor_composites` | 1427 | 8.5 | `9b3c8796` | PR |
| `validate_actor_monsters` | 1437 | 80.0 | `9b3c8796` | PR |
| `validate_actor_plain` | 21437 | 239.9 | `9b3c8796` | PR |
| `validate_actor_recipes` | 1669 | 123.7 | `9b3c8796` | PR |
| `validate_app_polish1` | 752 | 18.9 | `6cd965c2` | PR |
| `validate_app_polish2` | 1028 | 3.7 | `6cd965c2` | merge delta |
| `validate_app_polish4` | 10485 | 32.1 | `6cd965c2` | PR |
| `validate_app_polish7` | 5120 | 1.5 | `6cd965c2` | merge delta |
| `validate_app_polish9` | 4668 | 4.1 | `6cd965c2` | merge delta |
| `validate_armour_cloak` | 4448 | 48.3 | `63752052` | merge delta |
| `validate_audio_callers` | 5528 | 5.0 | `6cd965c2` | PR |
| `validate_audio_charsel` | 5968 | 3.5 | `264248c6` | merge delta |
| `validate_audio_combat` | 19548 | 35.3 | `264248c6` | PR |
| `validate_audio_domains` | 2544 | 28.9 | `6cd965c2` | PR |
| `validate_audio_events` | 70980 | 6.3 | `264248c6` | merge delta |
| `validate_audio_items` | 3000 | 2.6 | `6cd965c2` | PR |
| `validate_audio_kubera` | 1000 | 1.4 | `9b3c8796` | PR |
| `validate_audio_monsters` | 38315 | 22.4 | `9b3c8796` | PR |
| `validate_audio_music` | 4291 | 0.6 | `264248c6` | merge delta |
| `validate_audio_objects` | 4000 | 5.9 | `9b3c8796` | PR |
| `validate_audio_objects4` | 10093 | 6.4 | `9b3c8796` | PR |
| `validate_audio_ui` | 5803 | 28.0 | `264248c6` | merge delta |
| `validate_audio_voices` | 2182 | 0.2 | `264248c6` | merge delta |
| `validate_charsel_items` | 8817 | 6.9 | `9b3c8796` | PR |
| `validate_charsel_world` | 1200 | 4.2 | `9b3c8796` | merge delta |
| `validate_fidelity` | 991 | 95.3 | `63752052` | merge delta |
| `validate_gfx3` | - | 5.7 | `6cd965c2` | merge delta |
| `validate_helpers` | 8667 | 311.4 | `63752052` | merge delta |
| `validate_icarus` | 5240 | 68.5 | `9b3c8796` | PR |
| `validate_icarus_c2` | 8400 | 21.2 | `9b3c8796` | PR |
| `validate_inventory_fx` | 8017 | 6.6 | `9b3c8796` | PR |
| `validate_item_callers` | 6013 | 2.1 | `9b3c8796` | PR |
| `validate_item_carry` | 114388 | 552.7 | `63752052` | merge delta |
| `validate_item_chains` | 35406 | 181.9 | `63752052` | merge delta |
| `validate_item_cloak` | 5694 | 177.2 | `63752052` | merge delta |
| `validate_item_clusters` | 74292 | 120.6 | `63752052` | merge delta |
| `validate_item_continuation` | 25772 | 115.5 | `63752052` | merge delta |
| `validate_item_coverage` | 31724 | 106.1 | `63752052` | merge delta |
| `validate_item_cycle` | 6936 | 52.3 | `63752052` | merge delta |
| `validate_item_derived` | 36252 | 274.1 | `63752052` | merge delta |
| `validate_item_direct_bodies` | 15352 | 24.7 | `63752052` | merge delta |
| `validate_item_effects` | 1500 | 4.8 | `1359566c` | PR |
| `validate_item_expansion` | 52172 | 118.8 | `63752052` | merge delta |
| `validate_item_gear` | 25256 | 103.0 | `63752052` | merge delta |
| `validate_item_groups` | 4824 | 21.3 | `63752052` | merge delta |
| `validate_item_helper_groups` | 6432 | 29.9 | `63752052` | merge delta |
| `validate_item_hiddenmesh` | 116281 | 515.0 | `63752052` | merge delta |
| `validate_item_named` | 20057 | 3.3 | `63752052` | merge delta |
| `validate_item_next` | 14992 | 274.6 | `63752052` | merge delta |
| `validate_item_other_bodies` | 24084 | 105.4 | `63752052` | merge delta |
| `validate_item_ownerfx` | 14964 | 192.4 | `63752052` | merge delta |
| `validate_item_predraw` | 42540 | 371.8 | `63752052` | merge delta |
| `validate_item_product` | 2874 | 78.5 | `63752052` | merge delta |
| `validate_item_quality` | 28080 | 278.7 | `63752052` | merge delta |
| `validate_item_ranked` | 17736 | 113.8 | `63752052` | merge delta |
| `validate_item_read_programs` | 5352 | 26.6 | `63752052` | merge delta |
| `validate_item_scalars` | 26274 | 107.3 | `63752052` | merge delta |
| `validate_item_types` | 135176 | 51.8 | `63752052` | merge delta |
| `validate_item_wings_next` | 33622 | 115.9 | `63752052` | merge delta |
| `validate_items_ui` | 8517 | 9.5 | `9b3c8796` | PR |
| `validate_joints` | 180 | 9.2 | `1359566c` | PR |
| `validate_login_world` | 1200 | 4.5 | `9b3c8796` | merge delta |
| `validate_map_polish` | 876 | 0.5 | `6cd965c2` | merge delta |
| `validate_meshdraw` | 14619 | 82.6 | `9b3c8796` | PR |
| `validate_model_edge` | 954 | 177.5 | `9b3c8796` | PR |
| `validate_model_light` | 1433 | 5.1 | `9b3c8796` | PR |
| `validate_mount_visuals` | 8400 | 21.0 | `63752052` | merge delta |
| `validate_movement` | 6614 | 100.1 | `9b3c8796` | PR |
| `validate_muun_passes` | 1361 | 1.1 | `63752052` | merge delta |
| `validate_muun_riding` | 890 | 0.8 | `63752052` | merge delta |
| `validate_muun_secondary` | 873 | 0.5 | `63752052` | merge delta |
| `validate_muun_special` | 452 | 1.0 | `63752052` | merge delta |
| `validate_muun_visual` | 912 | 1.3 | `63752052` | merge delta |
| `validate_npc_cloak` | 2619 | 30.5 | `63752052` | merge delta |
| `validate_object_render` | 1984 | 5.8 | `9b3c8796` | merge delta |
| `validate_particles` | 407 | 1.3 | `1359566c` | PR |
| `validate_path` | 4719 | 28.7 | `264248c6` | merge delta |
| `validate_pets` | 1062 | 187.1 | `63752052` | merge delta |
| `validate_raven` | 4000 | 187.4 | `63752052` | merge delta |
| `validate_render_effects` | 660 | 1.5 | `1359566c` | PR |
| `validate_render_effects10` | 154 | 0.5 | `63752052` | PR |
| `validate_render_effects11` | 176 | 0.4 | `63752052` | PR |
| `validate_render_effects12` | 64 | 0.4 | `63752052` | PR |
| `validate_render_effects13` | 180 | 0.7 | `63752052` | PR |
| `validate_render_effects14` | 660 | 1.6 | `63752052` | PR |
| `validate_render_effects15` | 509 | 1.2 | `63752052` | PR |
| `validate_render_effects16` | 424 | 3.7 | `6cd965c2` | PR |
| `validate_render_effects17` | 618 | 7.2 | `9b3c8796` | PR |
| `validate_render_effects18` | 540 | 1.3 | `9b3c8796` | PR |
| `validate_render_effects19` | 400 | 1.0 | `9b3c8796` | PR |
| `validate_render_effects20` | 148 | 0.3 | `63752052` | PR |
| `validate_render_effects21` | 267 | 0.4 | `63752052` | PR |
| `validate_render_effects22` | 202 | 6.8 | `63752052` | PR |
| `validate_render_effects23` | 1174 | 8.6 | `63752052` | PR |
| `validate_render_effects24` | 226 | 3.2 | `9b3c8796` | PR |
| `validate_render_effects25` | 202 | 8.1 | `9b3c8796` | PR |
| `validate_render_effects26` | 348 | 9.0 | `9b3c8796` | PR |
| `validate_render_effects27` | 424 | 1.6 | `63752052` | PR |
| `validate_render_effects28` | 630 | 2.2 | `9b3c8796` | PR |
| `validate_render_effects3` | 720 | 1.3 | `1359566c` | PR |
| `validate_render_effects30` | 452 | 0.7 | `1359566c` | PR |
| `validate_render_effects31` | 66051 | 311.1 | `9b3c8796` | PR |
| `validate_render_effects32` | 1723 | 1.1 | `1359566c` | PR |
| `validate_render_effects33` | 6410 | 22.9 | `9b3c8796` | PR |
| `validate_render_effects4` | 1920 | 7.6 | `1359566c` | PR |
| `validate_render_effects5` | 1190 | 4.5 | `63752052` | PR |
| `validate_render_effects6` | 1000 | 1.8 | `1359566c` | PR |
| `validate_render_effects7` | 596 | 1.8 | `63752052` | PR |
| `validate_render_effects9` | 304 | 1.1 | `63752052` | PR |
| `validate_render_worlds_a` | 9000 | 12.9 | `9b3c8796` | PR |
| `validate_renderchar` | 1706 | 54.6 | `63752052` | merge delta |
| `validate_session_party` | 200 | 0.7 | `264248c6` | merge delta |
| `validate_skill_fx` | 660 | 1.4 | `1359566c` | PR |
| `validate_terrain` | 583500 | 474.6 | `9b3c8796` | PR |
| `validate_terrain_remaining` | 2147 | 5.2 | `9b3c8796` | PR |
| `validate_viewport_monsters` | 1963 | 10.3 | `264248c6` | merge delta |
| `validate_world_fidelity` | 200 | 0.2 | `9b3c8796` | merge delta |
| `validate_world_light_name` | 304 | 0.4 | `9b3c8796` | merge delta |
| `validate_world_particle_consumers` | 900 | 1.1 | `1359566c` | PR |
| `validate_world_tile_folder` | 5700 | 92.8 | `9b3c8796` | merge delta |
| `validate_worlds_121` | 4000 | 8.0 | `9b3c8796` | PR |
| `validate_worlds_after` | 13424 | 11.2 | `9b3c8796` | PR |
| `validate_worlds_after2` | 32216 | 34.1 | `9b3c8796` | PR |
| `validate_worlds_after3` | 10212 | 6.2 | `9b3c8796` | PR |
| `validate_worlds_after4` | 9181 | 9.9 | `9b3c8796` | PR |
| `validate_worlds_after5` | 6000 | 7.3 | `9b3c8796` | PR |
| `validate_worlds_after6` | 7300 | 91.9 | `9b3c8796` | PR |
| `validate_worlds_b` | 4000 | 3.7 | `9b3c8796` | merge delta |
| `validate_worlds_d` | 2400 | 5.7 | `9b3c8796` | PR |
| `validate_worlds_e` | 4840 | 13.0 | `9b3c8796` | PR |
| `validate_worlds_f` | 1818 | 0.5 | `9b3c8796` | PR |
| `validate_worlds_fog` | 4044 | 11.1 | `6cd965c2` | PR |
| `validate_worlds_g` | 6000 | 2.5 | `9b3c8796` | merge delta |
| `validate_worlds_g2` | 2657 | 7.0 | `9b3c8796` | merge delta |
| `validate_worlds_g3` | 4000 | 4.4 | `9b3c8796` | PR |
| `validate_worlds_h` | 6000 | 2.9 | `9b3c8796` | merge delta |
| `validate_worlds_i` | 6000 | 4.3 | `9b3c8796` | merge delta |
| `validate_worlds_inner` | 4000 | 4.0 | `9b3c8796` | PR |
| `validate_worlds_inner2` | 5000 | 6.5 | `9b3c8796` | PR |
| `validate_worlds_inner3` | 8000 | 6.4 | `9b3c8796` | PR |
| `validate_worlds_inner4` | 8000 | 7.6 | `9b3c8796` | PR |
| `validate_worlds_inner5` | 4000 | 8.7 | `9b3c8796` | PR |
| `validate_worlds_j` | 6000 | 4.6 | `9b3c8796` | merge delta |
| `validate_worlds_k` | 6000 | 7.1 | `9b3c8796` | merge delta |
| `validate_worlds_karutan` | 3000 | 4.7 | `9b3c8796` | PR |
| `validate_worlds_l` | 1260 | 1.6 | `1359566c` | PR |
| `validate_worlds_m` | 1080 | 1.6 | `1359566c` | PR |
| `validate_worlds_n` | 13000 | 11.7 | `9b3c8796` | merge delta |
| `validate_worlds_o` | - | 8.9 | `9b3c8796` | merge delta |
| `validate_worlds_p` | 10000 | 10.2 | `9b3c8796` | merge delta |
| `validate_worlds_p2` | 6000 | 7.2 | `9b3c8796` | merge delta |
| `validate_worlds_q` | 11000 | 7.6 | `9b3c8796` | merge delta |
| `validate_worlds_q2` | 4000 | 4.9 | `9b3c8796` | merge delta |
| `validate_worlds_r` | 12000 | 9.9 | `9b3c8796` | merge delta |
| `validate_worlds_r2` | 9000 | 4.4 | `9b3c8796` | merge delta |
| `validate_worlds_raklion` | 3000 | 4.0 | `9b3c8796` | PR |
| `validate_worlds_s` | 11000 | 5.2 | `9b3c8796` | merge delta |
| `validate_worlds_s2` | 10000 | 5.2 | `9b3c8796` | merge delta |
| `validate_worlds_s3` | 22000 | 16.8 | `9b3c8796` | merge delta |
| `validate_worlds_slots` | 18999 | 15.2 | `9b3c8796` | PR |
| `validate_worlds_slots2` | 33000 | 62.6 | `9b3c8796` | PR |
| `validate_worlds_slots3` | 36000 | 66.0 | `9b3c8796` | PR |

Steward validators: validate_item_effects,validate_joints,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_particles,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_render_worlds_a,validate_icarus,validate_icarus_c2,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_audio_callers,validate_audio_combat,validate_render_effects,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_world_particle_consumers,validate_audio_domains,validate_audio_items,validate_worlds_l,validate_worlds_m,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_app_polish1,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_worlds_inner,validate_render_effects27,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_worlds_inner2,validate_audio_objects,validate_render_effects28,validate_render_effects30,validate_worlds_inner3,validate_items_ui,validate_render_effects31,validate_audio_objects4,validate_audio_monsters,validate_audio_kubera,validate_actor_monsters,validate_worlds_inner4,validate_worlds_inner5,validate_render_effects32,validate_actor_plain,validate_render_effects33

## Command wall ledger

Execution wall excludes the resource waits in the adjacent column. This also
records failed explorations, superseded invalid-label renders and checkpoints.
The initial invalid-label before sweep is 79.286 s and its binary already has
the exact corrected-before hash. Only the corrected identity pair counts as
final evidence. All successful compiled controls run once. Selection overhead
is explicit rather than hidden in validator execution times.

| Command | Wall s | Resource wait s | Exit |
|---|---:|---:|---:|
| `ice-particle-build` | 1.011 | 0 | 0 |
| `ice-particle-sample` | 11.024 | 90 | 0 |
| `native-focus` | 8.787 | 0 | 1 |
| `native-focus2` | 9.715 | 0 | 0 |
| `exact-call-build` | 1.444 | 0 | 0 |
| `exact-call-sample` | 29.943 | 0 | 1 |
| `native-root-build` | 19.560 | 60 | 0 |
| `exact-call-sample2` | 0.003 | 0 | 126 |
| `exact-call-sample2` | 26.182 | 0 | 1 |
| `blood-build` | 13.288 | 0 | 0 |
| `blood-sample` | 6.179 | 30 | 1 |
| `checkpoint2-audit` | 28.861 | 0 | 0 |
| `blood-sample2` | 12.066 | 0 | 1 |
| `blood-build2` | 13.435 | 0 | 0 |
| `blood-sample3` | 45.181 | 0 | 0 |
| `consumer-final-build` | 11.377 | 60 | 0 |
| `native-focus4` | 5.155 | 30 | 1 |
| `dispatch-sample` | 3.131 | 0 | 1 |
| `dispatch-sample2` | 6.461 | 0 | 0 |
| `native-focus5` | 8.892 | 0 | 1 |
| `lifecycle-build` | 11.773 | 120 | 0 |
| `native-focus6` | 5.826 | 30 | 0 |
| `full-sample` | 6.474 | 0 | 1 |
| `defaults-build` | 12.707 | 0 | 0 |
| `focused-final` | 44.426 | 30 | 1 |
| `focused-resume` | 73.402 | 0 | 0 |
| `checkpoint3-audit` | 19.055 | 0 | 0 |
| `selections` | 154.895 | 0 | 0 |
| `affected-validators` | 1027.312 | 0 | 1 |
| `effects16-refresh` | 6.282 | 0 | 0 |
| `checkpoint4-audit` | 41.241 | 0 | 0 |
| `merge115-build` | 16.676 | 0 | 0 |
| `merge115-audit` | 40.190 | 60 | 0 |
| `delta-selections` | 165.910 | 150 | 0 |
| `checkpoint5-audit` | 36.651 | 0 | 0 |
| `checkpoint6-audit` | 37.846 | 0 | 0 |
| `merge115-validators` | 3554.113 | 0 | 0 |
| `audio005-build` | 22.078 | 90 | 0 |
| `checkpoint7-audit` | 42.741 | 390 | 0 |
| `audio005-selections` | 147.676 | 330 | 0 |
| `audio005-validators` | 1099.376 | 0 | 0 |
| `inner005-build` | 20.570 | 0 | 0 |
| `checkpoint8-audit` | 36.545 | 0 | 0 |
| `inner005-selections` | 218.675 | 60 | 0 |
| `inner005-validators` | 1237.713 | 60 | 0 |
| `checkpoint9-audit` | 32.259 | 0 | 0 |
| `portable-affected` | 534.640 | 0 | 1 |
| `private-native` | 182.102 | 30 | 1 |
| `effects30-corrected` | 6.287 | 0 | 0 |
| `checkpoint10-audit` | 17.483 | 0 | 0 |
| `ui5-build` | 0.401 | 0 | 0 |
| `ui5-selections` | 111.612 | 0 | 0 |
| `ui5-audit` | 24.286 | 0 | 0 |
| `ui5-validators` | 59.218 | 0 | 0 |
| `ui5-portable` | 418.074 | 0 | 0 |
| `ui5-private` | 121.517 | 90 | 0 |
| `original-full` | 71.666 | 0 | 0 |
| `skill-fixtures` | 26.544 | 0 | 0 |
| `final-world-build` | 0.330 | 0 | 0 |
| `identity-after` | 73.176 | 0 | 0 |
| `skill-fixtures-demo` | 17.675 | 0 | 0 |
| `demo-before-world-build` | 9.616 | 0 | 0 |
| `identity-before-demo` | 87.552 | 0 | 0 |
| `demo-after-world-build` | 0.331 | 0 | 0 |
| `checkpoint11-audit` | 28.908 | 0 | 0 |
| `identity-after-demo` | 62.448 | 0 | 0 |
| `final-doc-readers` | 9.276 | 0 | 0 |

## Limits and next lane

Blood Storm still refuses effect 0x585/0, 0x586/0, 0x4b7/1, particle 0x8145/1
and blur 0x814b. Other sword actions and parent scale indices outside 0..9 are
not admitted. Crescent end 0x49e/0 and Fire Breath 0x8001/0 remain absent.
Defense's held-input renewal/release and shield body are unproved; an arbitrary
held duration would fabricate behavior. General Death Stab equipment links and
greater-aura link/presence services remain outside the bounded fixtures.

Summon spawn selectors/lifetimes remain unproved. Read-only candidate bodies
are 30 -> 26, 31 -> 32, 32 -> 21, 33 -> 20, 34 -> 10, 35 -> 150, 36 -> 151.
These are matching-name actor-lane follow-ups, not an admitted skill-to-actor
mapping. Candidate 26 has its body/weapon group on ACTORS-007; 10 and 151 still
need effect services there. No actor producer or actor file is authored here.
Late pushed ITEMS-002AA / INNER-005 WIP inspection provides no extra small,
statically complete refused-consumer contract suitable for this lane.

Frozen Native Data still lacks exact names **DarkLordSkill.bmd, Flame01.OZJ,
water.OZJ**; those input-dependent rows stay refused. No refresh is attempted.
0x47a remains reserved to MUUN-VISUAL-005; this lane leaves its inherited consumer
unchanged. Eligibility, damage, mana, cooldowns, server keys, packet paths,
protection, live client state and owner apps are outside this fixture subset.
All incoming main actor/item/world/Muun/UI/audio producer changes are retained.
The lane authors only combat skill and particle/joint/effect consumer files,
necessary native adapters, their tests/validators and delivery documentation.

## Delivery

Ready for steward after PR publication and the single ready-prs entry. The
steward owns the combined gate and merge. Complete all documentation and pushes
before that entry, then push nothing more. Remove this lane's renders, scratch,
exported baseline source, ignored builds, worktree and local branch; retain the
remote PR branch. No new private input needs retaining. Cleanup paths are
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-033`, the matching
`renders/render-effects-033`, and `~/Documents/MTM/worktrees/render-effects-033`.
