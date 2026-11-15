# AUDIO-005: scalar monster owners and ordered Kubera stops

Branch `codex/audio-005`, stacked on AUDIO-004 `30e4f275`, then integrated
with main after PR #388. Offline pinned instructions and authored fixtures only.
This is a bounded audio subset. Final integration checks are still WIP.

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

No music selector or mixer change. Read-only decoded smoke covers the 211
distinct sound ids used here, with nonzero PCM. This establishes file availability and
native delivery, not FMOD mixer parity.

## Verification

Integrated build and all 70 private validators pass at
`e4d1ce478380c0acff4f3f5f1391de6d3293230a`. Portable refresh, reduced private
native tests, audit and the post-UI identity refresh remain pending. Source before
main integration was `1f5462e6`; integrations preserve AUDIO-005 source and checks.

- Monster original comparison: **38,315 cases**, all **245 sites**, zero
  mismatches/stops. Includes 32,759 complete-owner, 2,748 outer-dispatch and
  2,808 caller-tail cases. **15/15 compiled mutants caught, 27.93 s**.
  A later action-count guard has its own **1/1 mutant, 2.004 s**; the unchanged
  15 targets were not repeated. Total **16/16**.
- Kubera full move/native command comparison: **1,000 cases**, all six sites,
  zero mismatches/stops, **6/6 compiled mutants caught, 7.95 s**. Includes a
  source-order mutation, original OBJECT, AL, action records and RNG.
- Initial canonical private focused run: **14 tests**, zero skips/failures/errors,
  **22.10 s**. Final reduced run including the action-count control is pending.
- Before integration, affected portable: **171 work items**, 163 native modules,
  nine reported suite groups; **1,785 tests, 1,465 passed / 320 explicit skips,
  zero failures/errors**. **443.4 s** runner / **507.55 s** command wall.
  Main added actor, world and UI inputs; their affected refresh is pending.
- Checked source root build **13.96 s**; actor/world integration root build
  **23.08 s**. Latest UI integration root build **22.17 s**.
- All **70 affected validators pass**, **1,115,117 cases/checks**, zero
  failures/errors/skips, **906.06 s** command wall. Optional mutants are disabled;
  no unchanged optional mutant run or full lane gate is repeated.
- Integrated portable refresh at `cfdf3501`: **182 work items**, including
  **173 native modules**, ten reported groups, **1,859 tests: 1,515 passed /
  344 explicit skips, zero failures/errors**, **416.4 s** runner /
  **550.82 s** command wall. Post-build selection takes **120.30 s**.
- Source review found one annotation edge: type 47 could tag a prior log entry
  when its sound branch emitted nothing. The annotation is now tied to the
  exact action/frame sound gate. Root rebuild passes, **22.38 s**. Eight
  prefilled-log boundary controls and a compiled guard mutant are added; their
  run and affected refresh are pending. Earlier portable/source checks remain
  recorded at their exact commits. No unchanged optional mutant target is rerun.
- Repository audit and final self-review remain pending.

### Default identity

The first baseline against AUDIO-004 was retired when main gained intentional
world rendering changes. Its results are not used for final identity. A control
binary was built from exact main `4babc900` compiled inputs in this lane's own
worktree, with those inputs checked against git and the committed lane bytes
restored in a finally block. Main itself was never edited or built in.

Both control and production explicitly run `make -C native -j4 world`.
The control build takes **6.37 s**, production **11.64 s**. Distinct SHA-256s:

- Control, main `4babc900`:
  `88e2708626a818ce09721422b9ea8d52a373b8eaad4d77750d27376eeebe5d35`.
- Production before the UI merge, `51db4cbd`:
  `d0702324ea66063aa97db5d63e17c33ea47c7c381976b59c6f4519909a6b64d0`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24,
demo name Preview. Only output directory prefixes are normalized; every JSON
row/value is compared, with no removed scene fields. All 46 renders exit 0.

| Dataset | PNGs | OBJECT/light dumps | Reports | Control render wall |
|---|---:|---:|---:|---:|
| October 22, 14 views | 28/28 | 28/28 | 14/14 | 15.812 s |
| DATA-ACQ-002, 32 views | 64/64 | 64/64 | 32/32 | 47.262 s |

Control total **63.11 s**; pre-UI production **90.99 s**; comparison **0.21 s**.
All **92 PNGs, 92 dumps and 46 reports** are identical. Latest UI integration
requires a rebuilt production refresh against the preserved control. These are
repeatability controls, not original-client visual equivalence.

### Steward validators

All 70 post-build selected rows pass at
`e4d1ce478380c0acff4f3f5f1391de6d3293230a`, **906.06 s** command wall,
**1,115,117 cases/checks**, zero failures/errors/skips.
Selection takes **34.45 s** and retains the `validate_worlds_r2` symbol fallback;
21 changed-library rows use no changed symbol and are pruned. Shared-library
consumers under 6b/8b and the two incoming actor/world rows are retained.
Use canonical `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from repository
root. No optional mutants need repeating; no full lane gate ran.

Steward validators: validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_path,validate_terrain,validate_viewport_monsters,validate_terrain_remaining,validate_audio_events,validate_audio_music,validate_audio_voices,validate_worlds_b,validate_icarus_c2,validate_worlds_e,validate_worlds_f,validate_worlds_g,validate_audio_callers,validate_worlds_h,validate_audio_combat,validate_worlds_i,validate_audio_domains,validate_worlds_j,validate_audio_items,validate_session_party,validate_audio_charsel,validate_world_tile_folder,validate_world_light_name,validate_worlds_r2,validate_worlds_q,validate_worlds_q2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after6,validate_app_polish2,validate_app_polish7,validate_app_polish4,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_worlds_inner,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_audio_ui,validate_render_effects26,validate_actor_composites,validate_worlds_inner2,validate_audio_objects,validate_render_effects28,validate_worlds_inner3,validate_items_ui,validate_audio_objects4,validate_audio_monsters,validate_audio_kubera,validate_actor_monsters,validate_worlds_inner4

| Validator | Cases/checks | Wall seconds |
|---|---:|---:|
| `validate_actor_composites` | 1427 | 11.1 |
| `validate_actor_monsters` | 1437 | 43.9 |
| `validate_actor_recipes` | 1669 | 147.8 |
| `validate_app_polish2` | 1028 | 4.4 |
| `validate_app_polish4` | 10485 | 37.8 |
| `validate_app_polish7` | 5120 | 2.3 |
| `validate_audio_callers` | 5528 | 6.8 |
| `validate_audio_charsel` | 5968 | 4.1 |
| `validate_audio_combat` | 19548 | 42.5 |
| `validate_audio_domains` | 2544 | 27.0 |
| `validate_audio_events` | 70980 | 4.3 |
| `validate_audio_items` | 3000 | 4.1 |
| `validate_audio_kubera` | 1000 | 1.5 |
| `validate_audio_monsters` | 38315 | 27.3 |
| `validate_audio_music` | 4291 | 0.4 |
| `validate_audio_objects` | 4000 | 4.8 |
| `validate_audio_objects4` | 10093 | 8.2 |
| `validate_audio_ui` | 5803 | 33.8 |
| `validate_audio_voices` | 2182 | 0.1 |
| `validate_charsel_items` | 8817 | 12.7 |
| `validate_icarus_c2` | 8400 | 14.0 |
| `validate_inventory_fx` | 8017 | 12.4 |
| `validate_item_callers` | 6013 | 1.7 |
| `validate_items_ui` | 8517 | 15.5 |
| `validate_meshdraw` | 14619 | 73.8 |
| `validate_model_edge` | 954 | 162.4 |
| `validate_model_light` | 1433 | 7.0 |
| `validate_movement` | 6614 | 76.3 |
| `validate_path` | 4719 | 32.2 |
| `validate_render_effects16` | 424 | 5.7 |
| `validate_render_effects17` | 618 | 10.0 |
| `validate_render_effects18` | 540 | 1.7 |
| `validate_render_effects19` | 400 | 1.5 |
| `validate_render_effects24` | 226 | 4.4 |
| `validate_render_effects25` | 202 | 17.6 |
| `validate_render_effects26` | 348 | 14.6 |
| `validate_render_effects28` | 630 | 2.6 |
| `validate_session_party` | 200 | 1.2 |
| `validate_terrain` | 583500 | 396.0 |
| `validate_terrain_remaining` | 2147 | 3.7 |
| `validate_viewport_monsters` | 1963 | 7.2 |
| `validate_world_light_name` | 304 | 0.5 |
| `validate_world_tile_folder` | 5700 | 37.6 |
| `validate_worlds_121` | 4000 | 7.2 |
| `validate_worlds_after3` | 10212 | 9.9 |
| `validate_worlds_after4` | 9181 | 13.7 |
| `validate_worlds_after6` | 7300 | 67.1 |
| `validate_worlds_b` | 4000 | 2.2 |
| `validate_worlds_e` | 4840 | 14.8 |
| `validate_worlds_f` | 1818 | 0.4 |
| `validate_worlds_fog` | 4044 | 11.1 |
| `validate_worlds_g` | 6000 | 4.0 |
| `validate_worlds_h` | 6000 | 4.5 |
| `validate_worlds_i` | 6000 | 5.4 |
| `validate_worlds_inner` | 4000 | 5.1 |
| `validate_worlds_inner2` | 5000 | 7.4 |
| `validate_worlds_inner3` | 8000 | 10.4 |
| `validate_worlds_inner4` | 8000 | 8.0 |
| `validate_worlds_j` | 6000 | 4.8 |
| `validate_worlds_karutan` | 3000 | 5.0 |
| `validate_worlds_q` | 11000 | 17.7 |
| `validate_worlds_q2` | 4000 | 7.6 |
| `validate_worlds_r2` | 9000 | 7.1 |
| `validate_worlds_raklion` | 3000 | 5.8 |
| `validate_worlds_s` | 11000 | 10.2 |
| `validate_worlds_s2` | 10000 | 11.0 |
| `validate_worlds_s3` | 22000 | 25.2 |
| `validate_worlds_slots` | 18999 | 23.9 |
| `validate_worlds_slots2` | 33000 | 44.9 |
| `validate_worlds_slots3` | 36000 | 45.4 |


## Next

Recover the 19 refused slot owners (279 candidates) from their first unsupported
operation. Keep unknown services and fields explicit rather than admitting a
partial method. Recover remaining semantic owners among the 546 unresolved
candidates. Class-use delivery needs an existing, verified owner for its required
contexts. Later monster server-class construction belongs to the actor owner;
this lane supplies no synthetic production mapping. Guardian's three state-bound
sites retain their prior fixture limit.

## WIP checkpoints

Pushed checkpoints `9d619c70`, `7f9fa0e9`, `58d578ff`, `1f5462e6` and
`51db4cbd` and `e4d1ce47` preserve implementation and done/left/next notes. The first main
integration is `a1d94d8d`, the UI integration `c8440b0a`. Resource guards pause
new heavy work during shared-host load spikes, including values above 30.
No subagents, full lane gate, live client or installed-app work ran.

Done: complete source, original/mutant proofs, decoded smoke and default identity
before the UI merge, and all 70 integrated private validators. Left: portable
refresh, reduced private tests, final identity refresh, audit,
status lines and PR-ready queue. Next: finish the guarded affected suite refresh,
then document and publish. Task-local reports are resumable WIP
in `~/Documents/MTM/mu-mac-tools/native/scratch/audio-005/`.
