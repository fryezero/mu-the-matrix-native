# AUDIO-005: WIP — latest-main verification pending

Branch `codex/audio-005`, stacked on AUDIO-004 `30e4f275`, then integrated
with main after PR #388. Offline pinned instructions and authored fixtures only.
This is a bounded audio subset. **Not PR-ready.**

## Census

Reproduce with `scripts/audio_caller_census.py --report <local>`. The historical
1,980 denominator is a syntactic E8-target scan, not a whole-program CFG proof.
A sound id or nearby prologue supplies no delivery admission.

| Owner bucket | AUDIO-004 | AUDIO-005 |
|---|---:|---:|
| UI | 51 | 51 |
| Hero/shared actions | 43 | 43 |
| Skills/effect timelines | 272 | 338 |
| Monsters/NPC voices | 848 | 848 |
| World objects/ambient | 135 | 135 |
| Items | 15 | 15 |
| Events/progression | 4 | 4 |
| Unresolved owner | 612 | 546 |
| Total | 1,980 | 1,980 |

Classified owners rise **1,368 -> 1,434**. Exact class-use controller calls
identify 22 candidates in `0x01080169`, eight in `0x0108988b` and 36 in their
reviewed siblings. All 66 stay unwired: target, buff, request and timing contexts
are not supplied by an existing native owner. The census keeps unknown sound
ids, gates and native availability separate from semantic ownership.

Enumerated sound boundaries rise **162 -> 411**, through **245 monster play
sites and four Kubera play sites**. Kubera's two stop sites are separate because
the historical denominator counts SND_Play. Shared sites count once even when
several models or world aliases reach them. This is not a completion percentage;
monster actor delivery retains the fixture limit below.

## Wired and refused groups

| Owner | Sites | Disposition |
|---|---:|---|
| Complete class slot +0x70 methods | 245 play | 21 whole methods: 15 sounding and six silent. World-selected model/action/frame partitions, original arguments and AL results |
| Remaining class methods | 279 candidates | 19 owners refused as whole methods at their first unsupported field, service or operation |
| Kubera `0x00e19ed0` | Four play, two stop | Ordered stop 0x4f2 -> play 0x4f1 near; stop 0x4f1 -> play 0x4f2 far; both original type-47 sounds |
| Class-use controllers | 66 classified | No delivery admission; required owner context remains absent |
| Guardian handler-state sounds | Three earlier sites | Existing fixture limit retained; runtime state 0 is unchanged |
| Unresolved semantic owners | 546 candidates | Still unresolved, not a count of missing native sounds |

The exact complete-owner table, source entries, registry aliases and refusals are
in [client-audio](../research/client-audio.md#audio-005-scalar-monster-owners-and-ordered-stops-2026-11-14).
`monster_audio_static.py` emits authored semantic partitions, not client bytes.
The verifier executes every original whole method, the complete outer dispatcher
and bounded shock/attack/death/walk caller tails; original return addresses
independently identify expected sound sites.

The shared dispatcher runs before the class slot, including its strict distance
>500 consume and special-model exclusions. Shock, attack and death discard that
dispatcher's result and continue to the shared voice. Native delivery preserves
both requests in that order. CHARACTER +0x3324 is OBJECT frame +0xd0, not an
independent marker. Combat requires actual frame zero plus the existing native
trigger latch. The separate cosmetic death latch retains once-only delivery
without changing animation or a replicated record. Walking refuses an actor
without action 2. Held original frame windows can request repeatedly; the
existing active-id policy controls playback rather than a new debounce.

The later models exist through the native BY_MONSTER loader; this lane does not
add their world-specific server-class construction or a spawn feed. The table
and direct actor-host delivery are therefore **fixture-bounded**. World hooks
operate only when a matching actor is already loaded. All 80 referenced type
models are attempted: 77 load, while missing files 0x90a..0x90c stay refused.
Effect alias 0x356 is not a native actor. Those aliases share sites with supported
models, so their refusal does not subtract whole sites from the 245 denominator.

Kubera's annotations preserve the existing event layout, count, OBJECT/action
records and complete normalized call order. An appended `MU_CUE_SOUND_STOP`
retains routine/site/id provenance without renumbering old kinds. Its reader
calls existing SND_Stop without loading an absent sound. The channel stops
immediately; the existing end callback remains deferred to System::update.
The exact world/routine/site/id/operation allowlist rejects foreign commands.

Independent cue cursors, muted/disabled draining and detached no-backlog behavior
are covered. Shared world/object/combat routines contain added sound-call lines
and includes only. No visual RNG, animation step, object/model field, server
state, event feed, pickup answer, transformed/buff input or new request route is
introduced. The virtualised interval 0x01854279..0x018542c2 remains excluded and
unfollowed.

## Music

No music selector or mixer change. All 211 distinct sound ids used here resolve and decode in the read-only
smoke; the combined rendered PCM is nonzero. This establishes file availability and
native delivery, not FMOD mixer parity.

## Verification through UI-WINDOWS-004

Last fully checked native C and validator source is
`8b3658bfb71589047584264e3eaff49cbfd0115f` after UI-WINDOWS-004; the census-only correction is
`2efa765c8a3660de002c65e22eed45db1eff7dbd`. The later RENDER-EFFECTS-031 merge is built but its affected checks are pending.
The 70-row table records each row's tested source. The checked binary and identity below precede that latest merge; they are not
verification of the new combined tree.

- Latest root build passes, **15.64 s** (earlier guard build **22.38 s**). Final explicit world build **0.20 s**.
- Monster original comparison: **38,315 cases**, all **245 sites**, zero
  mismatches/stops. Includes 32,759 complete-owner, 2,748 outer-dispatch and
  2,808 caller-tail cases. **15/15 compiled mutants, 27.93 s**, plus the later
  action-count guard's **1/1, 2.004 s**. Total **16/16**; unchanged targets
  were not repeated. Integrated unmutated results are in the table below.
- Kubera full original move/native order: **1,000 cases**, all six sites,
  zero mismatches/stops, **6/6 compiled mutants, 7.95 s**. Eight prefilled-log
  boundary controls and the new annotation-guard mutant pass in **4.60 s**.
  Total **7/7**. The controls preserve a prior borrowed event on silent,
  out-of-range and unordered-frame paths; valid branches annotate only their
  newly emitted event. OBJECT, AL, action records, RNG and all normalized
  original calls remain compared.
- After actor/world/UI integration, portable selection is **182 work items**,
  including **173 native modules**; **120.30 s** selection. The refresh at
  `cfdf3501` reports ten groups, **1,859 tests: 1,515 passed / 344 explicit
  skips, zero failures/errors**, **416.4 s** runner / **550.82 s** command wall.
  The subsequent annotation guard is covered by its dedicated controls,
  55-row affected refresh and final private native tests.
- **8d reduced**: 173 native modules exceed the 40-item cap. Canonical private
  execution from repository root passes **64 native tests**, zero native
  skips/failures/errors. The combined 66-test invocation takes **103.52 s**
  and exposes one census-only failure, corrected below. It includes both added
  modules and nine audio-consumer modules. Eight unchanged original-validator
  wrappers are omitted because the 70-row run already covers them; no optional
  mutants are repeated. Real rings/readers, once-only combat, active-id policy,
  mute/drain/detach, ordered stops, actual synthetic object callbacks and equal
  audio-on/off world pixels are covered. All 80 type models are attempted;
  77 load and the three expected missing files stay refused. All 211 used sound
  ids resolve/decode and the combined rendered PCM is nonzero.
- Final UI/NPC integration: **24/24 validators**, **175.09 s**, zero failures/errors/skips; selection **66.70 s**. Final affected portable: 180 work items / 174 native modules, 1,615 tests, 1,310 passed / 305 explicit skips, zero failures/errors; 47.796 s selection + 287.864 s run, 336.82 s command wall. Final private NPC/UI/audio/census consumers: 47/47, zero skips/failures/errors, 27.81 s. Four unchanged mutant/validator wrappers are omitted; optional mutants are not repeated.
- Census correction: INNER-004 names `0x00e8d888` only as a counted refusal.
  Treating that mention as an owner reference wrongly classified two sites.
  The reviewed non-owning reference is excluded, preserving **546 unresolved**;
  both sites now have explicit unresolved/native-absent controls. The original
  expectation was retained. Final census **2/2, zero skips/failures/errors**, included in the **47-test /
  27.81 s** private run. Only its test module consumes this Python change.
- All **70 affected validators** pass initially at `e4d1ce47`, **1,115,117
  cases/checks**, **906.06 s**. Post-guard selection from `cfdf3501` retains
  **55 rows**, including all ten fallback rows, and prunes 28 unused-symbol
  consumers. Those **55 pass** at `34f228d9`, **977,846 cases/checks**,
  **676.62 s**; selection **61.83 s**. Both runs have zero failures/errors/skips.
- Repository audit: **2,312 staged files, zero rejected, 15.12 s**.
  Source/spec self-review covers exact ownership/provenance, caller alias and
  order, unchanged visual state/RNG, overflow/foreign events, borrowed lifetime,
  once-only gates, cue cursors and added-lines scope. No independent reviewer
  or full lane gate is claimed.

### Default identity

A control binary was built from exact main `4babc900` compiled inputs in this
lane's own worktree. Git checks those inputs; a finally block restores every
committed lane byte. Main itself was never edited or built in. The earlier
AUDIO-004 baseline was retired after main's intentional renderer changes;
its results are not used here. The preserved control precedes the UI merge,
which is included in the final production binary.

Both control and production explicitly run `make -C native -j4 world`.
Control build **6.37 s**; final production build **0.20 s**.
Distinct SHA-256s, with production checked again after rendering:

- Control, main `4babc900`:
  `88e2708626a818ce09721422b9ea8d52a373b8eaad4d77750d27376eeebe5d35`.
- Checked production before RENDER-EFFECTS-031, native inputs `8b3658bf`:
  `45d9b390a39b69b05ce496155e5545557d160d6e90ed2a24c0f2497c10e2fbd5`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24,
demo name Preview. Only output directory prefixes are normalized; every JSON
row/value is compared with no removed scene fields. All 46 renders exit 0.

| Dataset | PNG identity | OBJECT/light identity | Reports | Control / production render wall |
|---|---:|---:|---:|---:|
| October 22, 14 views | 28/28 | 28/28 | 14/14 | 15.812 / 14.381 s |
| DATA-ACQ-002, 32 views | 64/64 | 64/64 | 32/32 | 47.262 / 33.807 s |

Totals: **92/92 PNGs, 92/92 dumps and 46/46 reports identical**.
Control command wall **63.11 s**, final production **48.22 s**;
comparison **0.158 s**. These are repeatability controls, not
original-client visual equivalence.

### Steward validators

Rows labeled `8b3658bf` were refreshed after UI-WINDOWS-004; `34f228d9` labels
the guard refresh and `e4d1ce47` the earlier unchanged inputs. The initial
post-build selection takes **34.45 s**, retains its `validate_worlds_r2`
fallback and prunes 21 unused-symbol consumers. All selected 6b/8b consumers
and every fallback are retained. The 55-row guard refresh adds no rows; the 24-row UI refresh adds four.
The final steward union has 74 rows, all passing at the source shown below.
Use canonical `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from repository
root. No further optional mutants are needed.

Steward validators: validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_path,validate_terrain,validate_viewport_monsters,validate_terrain_remaining,validate_audio_events,validate_audio_music,validate_audio_voices,validate_worlds_b,validate_icarus_c2,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_audio_callers,validate_worlds_h,validate_audio_combat,validate_worlds_i,validate_audio_domains,validate_worlds_j,validate_audio_items,validate_session_party,validate_audio_charsel,validate_world_tile_folder,validate_world_light_name,validate_worlds_r2,validate_worlds_q,validate_worlds_q2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after6,validate_app_polish2,validate_app_polish7,validate_app_polish4,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_worlds_inner,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_audio_ui,validate_render_effects26,validate_actor_composites,validate_worlds_inner2,validate_audio_objects,validate_render_effects28,validate_worlds_inner3,validate_items_ui,validate_audio_objects4,validate_audio_monsters,validate_audio_kubera,validate_actor_monsters,validate_worlds_inner4,validate_app_polish1,validate_app_polish9,validate_gfx3,validate_map_polish

| Validator | Cases/checks | Wall seconds | Tested source |
|---|---:|---:|---|
| `validate_actor_composites` | 1427 | 8.4 | `8b3658bf` |
| `validate_actor_monsters` | 1437 | 51.6 | `8b3658bf` |
| `validate_actor_recipes` | 1669 | 100.1 | `8b3658bf` |
| `validate_app_polish1` | 752 | 15.9 | `8b3658bf` |
| `validate_app_polish2` | 1028 | 3.1 | `8b3658bf` |
| `validate_app_polish4` | 10485 | 29.5 | `8b3658bf` |
| `validate_app_polish7` | 5120 | 1.5 | `8b3658bf` |
| `validate_app_polish9` | 4668 | 3.4 | `8b3658bf` |
| `validate_audio_callers` | 5528 | 4.6 | `8b3658bf` |
| `validate_audio_charsel` | 5968 | 4.1 | `e4d1ce47` |
| `validate_audio_combat` | 19548 | 42.5 | `e4d1ce47` |
| `validate_audio_domains` | 2544 | 19.4 | `8b3658bf` |
| `validate_audio_events` | 70980 | 4.3 | `e4d1ce47` |
| `validate_audio_items` | 3000 | 2.4 | `8b3658bf` |
| `validate_audio_kubera` | 1000 | 0.9 | `8b3658bf` |
| `validate_audio_monsters` | 38315 | 11.8 | `8b3658bf` |
| `validate_audio_music` | 4291 | 0.4 | `e4d1ce47` |
| `validate_audio_objects` | 4000 | 2.7 | `8b3658bf` |
| `validate_audio_objects4` | 10093 | 5.3 | `8b3658bf` |
| `validate_audio_ui` | 5803 | 33.8 | `e4d1ce47` |
| `validate_audio_voices` | 2182 | 0.1 | `e4d1ce47` |
| `validate_charsel_items` | 8817 | 7.5 | `34f228d9` |
| `validate_gfx3` | - | 4.4 | `8b3658bf` |
| `validate_icarus_c2` | 8400 | 17.8 | `34f228d9` |
| `validate_inventory_fx` | 8017 | 8.6 | `34f228d9` |
| `validate_item_callers` | 6013 | 1.9 | `34f228d9` |
| `validate_items_ui` | 8517 | 11.5 | `34f228d9` |
| `validate_map_polish` | 876 | 0.5 | `8b3658bf` |
| `validate_meshdraw` | 14619 | 52.7 | `34f228d9` |
| `validate_model_edge` | 954 | 118.1 | `34f228d9` |
| `validate_model_light` | 1433 | 4.5 | `34f228d9` |
| `validate_movement` | 6614 | 49.7 | `8b3658bf` |
| `validate_path` | 4719 | 32.2 | `e4d1ce47` |
| `validate_render_effects16` | 424 | 4.0 | `8b3658bf` |
| `validate_render_effects17` | 618 | 6.1 | `8b3658bf` |
| `validate_render_effects18` | 540 | 1.7 | `e4d1ce47` |
| `validate_render_effects19` | 400 | 1.5 | `e4d1ce47` |
| `validate_render_effects24` | 226 | 2.8 | `8b3658bf` |
| `validate_render_effects25` | 202 | 7.7 | `8b3658bf` |
| `validate_render_effects26` | 348 | 8.5 | `8b3658bf` |
| `validate_render_effects28` | 630 | 1.8 | `34f228d9` |
| `validate_session_party` | 200 | 1.2 | `e4d1ce47` |
| `validate_terrain` | 583500 | 361.5 | `34f228d9` |
| `validate_terrain_remaining` | 2147 | 3.9 | `34f228d9` |
| `validate_viewport_monsters` | 1963 | 7.2 | `e4d1ce47` |
| `validate_world_light_name` | 304 | 0.4 | `34f228d9` |
| `validate_world_tile_folder` | 5700 | 35.1 | `34f228d9` |
| `validate_worlds_121` | 4000 | 3.4 | `34f228d9` |
| `validate_worlds_after3` | 10212 | 7.8 | `34f228d9` |
| `validate_worlds_after4` | 9181 | 11.4 | `34f228d9` |
| `validate_worlds_after6` | 7300 | 48.0 | `34f228d9` |
| `validate_worlds_b` | 4000 | 3.7 | `34f228d9` |
| `validate_worlds_e` | 4840 | 16.6 | `34f228d9` |
| `validate_worlds_f` | 1818 | 0.5 | `34f228d9` |
| `validate_worlds_fog` | 4044 | 5.3 | `8b3658bf` |
| `validate_worlds_g` | 6000 | 4.6 | `34f228d9` |
| `validate_worlds_h` | 6000 | 3.7 | `34f228d9` |
| `validate_worlds_i` | 6000 | 4.2 | `34f228d9` |
| `validate_worlds_inner` | 4000 | 3.0 | `34f228d9` |
| `validate_worlds_inner2` | 5000 | 3.4 | `34f228d9` |
| `validate_worlds_inner3` | 8000 | 15.6 | `34f228d9` |
| `validate_worlds_inner4` | 8000 | 5.5 | `34f228d9` |
| `validate_worlds_j` | 6000 | 5.5 | `34f228d9` |
| `validate_worlds_karutan` | 3000 | 5.0 | `34f228d9` |
| `validate_worlds_q` | 11000 | 12.4 | `34f228d9` |
| `validate_worlds_q2` | 4000 | 6.2 | `34f228d9` |
| `validate_worlds_r2` | 9000 | 4.3 | `34f228d9` |
| `validate_worlds_raklion` | 3000 | 4.2 | `34f228d9` |
| `validate_worlds_s` | 11000 | 18.8 | `34f228d9` |
| `validate_worlds_s2` | 10000 | 8.0 | `34f228d9` |
| `validate_worlds_s3` | 22000 | 20.5 | `34f228d9` |
| `validate_worlds_slots` | 18999 | 19.9 | `34f228d9` |
| `validate_worlds_slots2` | 33000 | 23.3 | `34f228d9` |
| `validate_worlds_slots3` | 36000 | 25.1 | `34f228d9` |

## Next

Recover the 19 refused slot owners (279 candidates) from their first unsupported
operation. Keep unknown services and fields explicit rather than admitting a
partial method. Recover remaining semantic owners among the 546 unresolved
candidates. Class-use delivery needs an existing, verified owner for its required
contexts. Later monster server-class construction belongs to the actor owner;
this lane supplies no synthetic production mapping. Guardian's three state-bound
sites retain their prior fixture limit. The virtualised frame interval remains
excluded and unfollowed; event, pickup, transformed/buff and request inputs remain
outside this lane.

## Earlier WIP checkpoints

Pushed checkpoints `9d619c70`, `7f9fa0e9`, `58d578ff`, `1f5462e6`, `51db4cbd`,
`e4d1ce47`, `cfdf3501`, `34f228d9`, `7ad4e89b` and `2efa765c` preserve source and done/left/
next notes. Their earlier pending states are superseded by the scoped green results above.
Resource guards pause new heavy work during shared-host spikes, including loads
above 30. No subagents ran.

## WIP

**Done:** implemented the 245 fixture-bounded monster play sites, four Kubera
play/two stop sites, and 66 semantic classifications. Corrected borrowed-log
annotation and refusal-only census references. All 23 new compiled controls,
74 validator rows across the recorded commits, 64 native delivery tests and the
later 47 private consumers pass. Portable and rebuilt default identity results
above are green through `8b3658bf`. Documentation retains exact source commits,
limits and per-row wall times.

**Latest integration:** main advanced again at the final check to
`6900914e7f73ac9b36cad30893c7a5ffc4f2dc78` (RENDER-EFFECTS-031). It merges
cleanly at `6c0f973a2adcb448bf0ecb36fc67099831046aed`, including both sides of
combat additions and the validator append. Root build passes **11.96 s**.
Post-build selection takes **68.73 s** and retains **82/242 validators**.
Those 82 have **not run** on the new tree. Its portable/private refresh and
identity are also unchecked. The owner requires WIP pushed by 02:15 and no new
long check afterward; the lane stops without a ready-prs line.

**Left:** run the latest merge's selected validators without optional mutants,
affected portable suites and reduced private changed/consumer modules. Check
whether the new reconstruction references change the census; do not lower an
expectation without tracing the exact owner evidence. Rebuild the main control
at the pinned latest main and production world targets, record distinct SHA-256s,
and repeat the default comparison. The preserved earlier identity is historical,
not a claim for RENDER-EFFECTS-031's intentional visual additions. Finish final
status, PR description and audit, mark the draft ready, then append exactly one
ready-prs line. Push every update before that line and none afterward.

**Next step:** from this worktree root, source canonical
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`, build, then inspect
`--list-affected-since 8b3658bf` and run the selected rows with
`--private --no-mutants --cache --affected-since 8b3658bf --jobs 2`.
Use the same base for affected portable and 8d selection; apply the >40 reduced
cap and 6b consumers. No unchanged optional mutant target needs repeating.
The common brief still prohibits a full lane gate.

Pending validators: validate_item_effects,validate_joints,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_particles,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_render_worlds_a,validate_icarus,validate_icarus_c2,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_audio_callers,validate_audio_combat,validate_render_effects,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_world_particle_consumers,validate_audio_domains,validate_audio_items,validate_worlds_l,validate_worlds_m,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_app_polish1,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_worlds_inner,validate_render_effects27,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_worlds_inner2,validate_audio_objects,validate_render_effects28,validate_render_effects30,validate_worlds_inner3,validate_items_ui,validate_render_effects31,validate_audio_objects4,validate_audio_monsters,validate_audio_kubera,validate_actor_monsters,validate_worlds_inner4

Builds, reports, control binaries and task scratch are reproducible outputs,
not future inputs; they are removed at the deadline. The worktree and local
branch remain for WIP. Recreate ignored `tools/python`, `evidence` and `input`
symlinks from the main checkout if needed. Existing shared capture manifests
remain in `~/Documents/MTM/mu-mac-tools/native/scratch/fidelity2/` and
`scratch/data-acq-002/`. No new private capture needs retaining. No subagents,
live client work, installed-app changes, PR-ready claim or merge occurred.
