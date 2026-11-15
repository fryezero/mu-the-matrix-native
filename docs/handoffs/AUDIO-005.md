# AUDIO-005: scalar monster owners and ordered Kubera stops

Branch `codex/audio-005`, integrated with main `6900914e` through merge
`6c0f973a`. Offline pinned instructions and authored fixtures only. This is a
verified bounded subset, with fixture-loaded monster delivery. Ready for steward.

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

## Verification

The resume changes documentation only. Compiled C and validator inputs are
`4a438364e3b3c374cc89bc5499c6feb5368671f1`; identity was run at documentation
checkpoint `c30126a9`. Main was fetched again at finish on 2026-11-15 and remains
`6900914e`. Its existing merge commit `6c0f973a` retains both lanes' combat
additions and validator entries; a fresh merge reports up to date.

- Clean root build passes, **27.80 s**.
- Monster original comparison passes **38,315 cases**, all **245 sites**, zero
  mismatches/stops. This includes 32,759 whole-owner, 2,748 whole-dispatch and
  2,808 caller-tail cases. The final integrated unmutated row takes **22.4 s**.
  Prior changed-target controls caught **15/15 in 27.93 s**, then the added
  action-count guard caught **1/1 in 2.004 s**, for **16/16** total.
- Kubera full original move/native command order passes **1,000 cases**, all
  **six play/stop sites**, zero mismatches/stops, **1.5 s** integrated. The
  prior changed-target run caught **6/6 in 7.95 s**; eight prefilled-log
  controls plus its annotation-guard mutant pass in **4.60 s**, for **7/7**
  total. AL, OBJECT/action records, RNG and full normalized order remain compared.
- Post-build `--list-affected-since 8b3658bf` reproduces **82/242 validators**,
  including all **four symbol fallbacks**, in **87.17 s**. All **82 pass**,
  **1,067,729 cases/checks**, zero failures/errors/skips, **891.54 s** command
  wall. Optional mutants are disabled. Unused-symbol consumers are pruned by
  the selector; no selected fallback is dropped.
- Affected portable selection uses the same base: **178 work items**, including
  **167 native modules**, **51.824 s** selection. The owner's app-packaging
  exclusion removes `test_native_app.py`; **177 items** run in 12 suite groups.
  Result: **1,844 tests, 1,507 passed / 337 explicit skips**, zero failures/errors,
  **363.1 s** runner / **416.42 s** command wall including selection.
- **8d reduced:** 167 native modules exceed the 40-item cap. Canonical
  `private-env.sh` from repository root runs eleven audio modules, native audio
  and NPC consumers, changed particle/effect modules, the three changed world
  hosts and census controls. **105/105 tests pass**, comprising 103 native tests
  and two census tests, zero skips/failures/errors, **106.91 s** command wall.
  Fourteen duplicate original wrappers are omitted. One generically named
  unchanged NPC `test_validator` wrapper was mistakenly retained and reran its
  mutants; it passed. No AUDIO-005 optional mutants were repeated in this resume.
- Private coverage includes original provenance/order, independent readers,
  once-only caller gates, active-id suppression, mute/disabled draining, detached
  no replay, actual synthetic object delivery and equal audio-on/off world pixels.
  All 80 referenced type models are attempted through BY_MONSTER; the documented
  three absent files remain allowed refusals. All **211 distinct used ids** resolve
  and decode, with nonzero combined PCM. The pinned census controls pass **2/2**
  and preserve **546 unresolved**, including both refusal-only INNER-004 sites.
- Repository audit passes: **2,312 staged files, zero rejected, 17.76 s**.
- Source/spec self-review checks exact ownership/provenance, caller frame alias
  and ordering, unchanged visual state/RNG, borrowed-event lifetime, overflow,
  foreign commands and the added-lines-only shared-file scope. No independent
  reviewer, lane full gate, live fidelity or FMOD mixer parity is claimed.

### Default identity

A control binary uses exact main `6900914e` compiled inputs in this lane's own
worktree. Only the lane's existing source differences are temporarily replaced
with their main blobs; added lane-only headers remain unreferenced by main.
A finally block restores every lane source byte before production is built.
The main checkout is never edited or built in.

Both targets explicitly run `nice -n 10 make -C native -j4 world`. Control build
**6.28 s**, production **6.74 s**. The distinct hashes are checked again after
rendering:

- Control: `1a7b20b52387fb7010574d45db4a7e99415ee3b06c7110da28bdc2877c25e484`.
- Production: `712a65ae036d2753293a4b577d60a07736b07ee048c5433c8db4b1973fb2dea8`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24,
demo name Preview. Only output-directory prefixes are normalized in JSONL;
every row/value is compared, with no removed scene fields. All control and
production renders exit 0.

| Dataset | PNG identity | OBJECT/light identity | Reports | Control / production wall seconds |
|---|---:|---:|---:|---:|
| October 22, 14 views | 28/28 | 28/28 | 14/14 | 16.71 / 16.46 |
| DATA-ACQ-002, 32 views | 64/64 | 64/64 | 32/32 | 43.84 / 49.27 |

Totals: **92/92 PNGs, 92/92 dumps and 46/46 reports identical**. The corrected
identity phase takes **140.33 s**, including both builds and comparison.
An initial launcher stopped before rendering because the October manifest used
obsolete tools paths, **132.49 s** including a 120-second load cooldown. Task-local
path normalization and preflight checks for all 46 entries fix the setup; no
input, expected image or scene field changes. The earlier pre-EFFECTS-031 sweep
is superseded by this current-main comparison. These are repeatability controls,
not original-client equivalence.

### Steward validators

The union is **108 rows**: **82 refreshed at `4a438364`**, plus **26 earlier
rows whose compiled inputs are unchanged** by the latest integration. Each
row below retains its actual tested commit and wall time. The resume's later
commits change documentation only. Use canonical
`~/Documents/MTM/mu-mac-tools/native/private-env.sh` from repository root.
No additional optional mutants are needed.

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_recipes,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_app_polish9,validate_audio_callers,validate_audio_charsel,validate_audio_combat,validate_audio_domains,validate_audio_events,validate_audio_items,validate_audio_kubera,validate_audio_monsters,validate_audio_music,validate_audio_objects,validate_audio_objects4,validate_audio_ui,validate_audio_voices,validate_charsel_items,validate_gfx3,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_effects,validate_items_ui,validate_joints,validate_map_polish,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_particles,validate_path,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects27,validate_render_effects28,validate_render_effects3,validate_render_effects30,validate_render_effects31,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_session_party,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_viewport_monsters,validate_world_light_name,validate_world_particle_consumers,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_j,validate_worlds_karutan,validate_worlds_l,validate_worlds_m,validate_worlds_q,validate_worlds_q2,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3

| Validator | Cases/checks | Wall seconds | Tested source |
|---|---:|---:|---|
| `validate_actor_composites` | 1427 | 9.4 | `4a438364` |
| `validate_actor_monsters` | 1437 | 51.2 | `4a438364` |
| `validate_actor_recipes` | 1669 | 114.8 | `4a438364` |
| `validate_app_polish1` | 752 | 23.7 | `4a438364` |
| `validate_app_polish2` | 1028 | 3.1 | `8b3658bf` |
| `validate_app_polish4` | 10485 | 34.0 | `4a438364` |
| `validate_app_polish7` | 5120 | 1.5 | `8b3658bf` |
| `validate_app_polish9` | 4668 | 3.4 | `8b3658bf` |
| `validate_audio_callers` | 5528 | 5.7 | `4a438364` |
| `validate_audio_charsel` | 5968 | 4.1 | `e4d1ce47` |
| `validate_audio_combat` | 19548 | 19.9 | `4a438364` |
| `validate_audio_domains` | 2544 | 21.2 | `4a438364` |
| `validate_audio_events` | 70980 | 4.3 | `e4d1ce47` |
| `validate_audio_items` | 3000 | 3.4 | `4a438364` |
| `validate_audio_kubera` | 1000 | 1.5 | `4a438364` |
| `validate_audio_monsters` | 38315 | 22.4 | `4a438364` |
| `validate_audio_music` | 4291 | 0.4 | `e4d1ce47` |
| `validate_audio_objects` | 4000 | 4.5 | `4a438364` |
| `validate_audio_objects4` | 10093 | 9.4 | `4a438364` |
| `validate_audio_ui` | 5803 | 33.8 | `e4d1ce47` |
| `validate_audio_voices` | 2182 | 0.1 | `e4d1ce47` |
| `validate_charsel_items` | 8817 | 7.7 | `4a438364` |
| `validate_gfx3` | - | 4.4 | `8b3658bf` |
| `validate_icarus` | 5240 | 46.6 | `4a438364` |
| `validate_icarus_c2` | 8400 | 21.1 | `4a438364` |
| `validate_inventory_fx` | 8017 | 7.0 | `4a438364` |
| `validate_item_callers` | 6013 | 1.3 | `4a438364` |
| `validate_item_effects` | 1500 | 1.4 | `4a438364` |
| `validate_items_ui` | 8517 | 11.0 | `4a438364` |
| `validate_joints` | 180 | 2.4 | `4a438364` |
| `validate_map_polish` | 876 | 0.5 | `8b3658bf` |
| `validate_meshdraw` | 14619 | 59.6 | `4a438364` |
| `validate_model_edge` | 954 | 120.4 | `4a438364` |
| `validate_model_light` | 1433 | 5.0 | `4a438364` |
| `validate_movement` | 6614 | 57.2 | `4a438364` |
| `validate_particles` | 407 | 1.2 | `4a438364` |
| `validate_path` | 4719 | 32.2 | `e4d1ce47` |
| `validate_render_effects` | 660 | 0.8 | `4a438364` |
| `validate_render_effects10` | 154 | 0.3 | `4a438364` |
| `validate_render_effects11` | 176 | 0.2 | `4a438364` |
| `validate_render_effects12` | 64 | 0.3 | `4a438364` |
| `validate_render_effects13` | 180 | 0.7 | `4a438364` |
| `validate_render_effects14` | 660 | 1.5 | `4a438364` |
| `validate_render_effects15` | 509 | 0.8 | `4a438364` |
| `validate_render_effects16` | 424 | 3.7 | `4a438364` |
| `validate_render_effects17` | 618 | 7.3 | `4a438364` |
| `validate_render_effects18` | 540 | 1.4 | `4a438364` |
| `validate_render_effects19` | 400 | 1.0 | `4a438364` |
| `validate_render_effects20` | 148 | 0.3 | `4a438364` |
| `validate_render_effects21` | 267 | 0.3 | `4a438364` |
| `validate_render_effects22` | 202 | 6.5 | `4a438364` |
| `validate_render_effects23` | 1174 | 8.9 | `4a438364` |
| `validate_render_effects24` | 226 | 2.8 | `4a438364` |
| `validate_render_effects25` | 202 | 10.3 | `4a438364` |
| `validate_render_effects26` | 348 | 10.1 | `4a438364` |
| `validate_render_effects27` | 424 | 1.4 | `4a438364` |
| `validate_render_effects28` | 630 | 2.7 | `4a438364` |
| `validate_render_effects3` | 720 | 0.7 | `4a438364` |
| `validate_render_effects30` | 452 | 0.6 | `4a438364` |
| `validate_render_effects31` | 66051 | 234.6 | `4a438364` |
| `validate_render_effects4` | 1920 | 4.8 | `4a438364` |
| `validate_render_effects5` | 1190 | 3.5 | `4a438364` |
| `validate_render_effects6` | 1000 | 1.0 | `4a438364` |
| `validate_render_effects7` | 596 | 1.2 | `4a438364` |
| `validate_render_effects9` | 304 | 0.8 | `4a438364` |
| `validate_render_worlds_a` | 9000 | 13.1 | `4a438364` |
| `validate_session_party` | 200 | 1.2 | `e4d1ce47` |
| `validate_skill_fx` | 660 | 1.5 | `4a438364` |
| `validate_terrain` | 583500 | 383.4 | `4a438364` |
| `validate_terrain_remaining` | 2147 | 12.4 | `4a438364` |
| `validate_viewport_monsters` | 1963 | 7.2 | `e4d1ce47` |
| `validate_world_light_name` | 304 | 0.4 | `34f228d9` |
| `validate_world_particle_consumers` | 900 | 0.6 | `4a438364` |
| `validate_world_tile_folder` | 5700 | 35.1 | `34f228d9` |
| `validate_worlds_121` | 4000 | 4.8 | `4a438364` |
| `validate_worlds_after` | 13424 | 9.3 | `4a438364` |
| `validate_worlds_after2` | 32216 | 29.0 | `4a438364` |
| `validate_worlds_after3` | 10212 | 9.7 | `4a438364` |
| `validate_worlds_after4` | 9181 | 15.3 | `4a438364` |
| `validate_worlds_after5` | 6000 | 12.9 | `4a438364` |
| `validate_worlds_after6` | 7300 | 69.1 | `4a438364` |
| `validate_worlds_b` | 4000 | 3.7 | `34f228d9` |
| `validate_worlds_d` | 2400 | 3.6 | `4a438364` |
| `validate_worlds_e` | 4840 | 15.5 | `4a438364` |
| `validate_worlds_f` | 1818 | 0.6 | `4a438364` |
| `validate_worlds_fog` | 4044 | 7.9 | `4a438364` |
| `validate_worlds_g` | 6000 | 4.6 | `34f228d9` |
| `validate_worlds_g3` | 4000 | 4.9 | `4a438364` |
| `validate_worlds_h` | 6000 | 3.7 | `34f228d9` |
| `validate_worlds_i` | 6000 | 4.2 | `34f228d9` |
| `validate_worlds_inner` | 4000 | 3.8 | `4a438364` |
| `validate_worlds_inner2` | 5000 | 4.9 | `4a438364` |
| `validate_worlds_inner3` | 8000 | 9.4 | `4a438364` |
| `validate_worlds_inner4` | 8000 | 7.6 | `4a438364` |
| `validate_worlds_j` | 6000 | 5.5 | `34f228d9` |
| `validate_worlds_karutan` | 3000 | 2.9 | `4a438364` |
| `validate_worlds_l` | 1260 | 0.8 | `4a438364` |
| `validate_worlds_m` | 1080 | 0.8 | `4a438364` |
| `validate_worlds_q` | 11000 | 12.4 | `34f228d9` |
| `validate_worlds_q2` | 4000 | 6.2 | `34f228d9` |
| `validate_worlds_r2` | 9000 | 4.3 | `34f228d9` |
| `validate_worlds_raklion` | 3000 | 3.4 | `4a438364` |
| `validate_worlds_s` | 11000 | 18.8 | `34f228d9` |
| `validate_worlds_s2` | 10000 | 8.0 | `34f228d9` |
| `validate_worlds_s3` | 22000 | 20.5 | `34f228d9` |
| `validate_worlds_slots` | 18999 | 19.7 | `4a438364` |
| `validate_worlds_slots2` | 33000 | 33.2 | `4a438364` |
| `validate_worlds_slots3` | 36000 | 32.1 | `4a438364` |

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

PR #396 is still open at the final main check. Once RENDER-ACTORS-006 lands,
recheck classes refused only for absent native actor plans; do not convert its
550 body-plan additions into an audio admission without the whole sound owner
and dispatch proof. No new owner is admitted during this verification resume.

## Delivery

Pushed checkpoints `25946926` and `c30126a9` preserve this resume's done/left/next
state; earlier checkpoints remain in branch history. Their pending sections are
superseded by the final results above. Resource guards enforce 120-second
cooldowns at high load. No subagents ran.

All documentation and PR metadata are finished before the single ready-prs entry;
no push follows that entry. The steward owns merge and the combined gate.
Task-local reports, renders, control binaries and builds are reproducible outputs,
not future inputs. Remove them with this worktree and local branch; retain the
remote branch for the steward. Shared existing capture inputs remain in their
canonical tools directories. Ready for steward.
