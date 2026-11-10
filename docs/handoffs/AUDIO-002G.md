# AUDIO-002G: legacy UI sound ownership and delivery

Branch `codex/audio-002g`, based on main `a2ad8814`, then main `9d6ce467`, which adds #364's
research only. This lane is offline and stops at PR-ready for the merge steward. No original client,
launcher, service, installed app or staged app is used or changed.

## Scope and addresses

[The discovery table](../research/client-audio.md#audio-002g-discovery-2026-11-09) is the first deliverable,
pushed in `34635986` before implementation. It maps CButton, credits, the existing scene-5 tick, login
Esc, the GFx input query and modal-key candidates, and records why unowned contexts remain silent.

| Original owner | Sound site | Result |
|---|---|---|
| CButton::Update `0x009867e3` | `0x0098689e` | Sound 25, null object, loop 0. Delivered in native shell server-select and legacy character-select buttons |
| CCreditWin next block `0x009d9eb2` | `0x009d9eed` | Sound 25 before finish. Provenance and immediate adapter verified with the existing offline controller; interactive shell credits remain absent |
| Scene-5 tick `0x01856e6c` | `0x01857064`, `0x01857163`, `0x018571e6` | Existing AUDIO-002E delivery retained |

CButton's accepted release sets click before playing, toggles check afterward, then clears the held
pointer. A held press, release outside, foreign held button, disabled/hidden/inactive button and
negative delta do not produce an accepted click. The containing window can refuse the later action
without cancelling the earlier sound. In particular, an unselected Connect is disabled while the
Delete button can click before its later refusal dialog. The native integration follows those gates.

`MU_UI_SOUND` keeps its original one-word id and operation number. Its borrowed data payload now
contains authored routine/site/object/loop provenance. Old drawing/recording sinks continue to see the
same call stream. The native adapter accepts only the two recovered site/owner pairs and null,
nonlooping calls. It never guesses a site from id 25 or a GFx callback name.

The callback is synchronous and borrowed. Each delivery object has its own sequence, advanced even
while detached, and a current logic-step tick. Server-select uses shell time divided by 40; character
buttons use their charsel step. Existing keyboard charsel cues retain their separate sequence and
handler. Global host log sequence preserves inter-controller order. No queued history is replayed on
attach/unmute; mute remains the existing Effect-group policy. `mu_charsel_ui_free` clears the callback.

## Wired and refused contexts

- Wired interactively: server-group/server buttons and the legacy character-select Create, Menu,
  Connect and Delete controls when their existing controller enables/accepts them.
- Credits: the reconstructed end-record event has provenance and a tested native delivery adapter.
  The standalone render tool retains its silent contract. The interactive shell has no credits window,
  credit-record owner or open/close lifecycle, so it has no newly invented credits route. The native
  test host honors HideWin and proves that subsequent window updates stay silent.
- Login Esc `0x01857529`: the native login/account panel is a placeholder; the exact original owning
  input/menu/credits context is absent. No generic Esc sound is added there.
- GFx query `0x00b49b97`, sound `0x00b49be4`: no new hook. Its movie/window/input gates are static,
  but the owning invocation/lifetime is not migrated. A new key listener could duplicate scene-5 audio.
- Legacy modal keys `0x009a336e`, `0x009a339c`, `0x009a3538`, `0x009a3642`: not substituted for the
  current GFx create/delete/caution controller. Those original modal owners remain unmigrated.
- GFx list callbacks/double click: no sound invented. The audited list callback and base dispatcher
  do not contain a direct sound call. This is not a proof that every transitive movie method is silent.
- Request/answer, event-domain inputs, remote magic/buff/pickup success, music-manager authority and
  the opaque frame gap remain outside this lane. There are no new event/answer routes or memory writes.

This adds delivery for one original interactive call site shared by several controls and provenance
for a second offline-controller site. Historical adapter totals are not a current whole-client census.

## Checks

All runtime/validator inputs were checked at `385c4e0c`.
The root build passed in **14.82 s** on the same runtime sources before the docs-only main merge.
Subsequent changes were tests, validator fixture setup and documentation, with no C/runtime changes.

- Affected portable run: **156 work items, 1,513 tests**, **408.82 s** command wall time, including
  selection; runner test wall time **336.6 s**. Initial result was 1,264 passed, 248 explicit skips
  and one stale AUDIO-002E shell expectation. The corrected six-test module passes in **4.82 s**, one
  expected private skip. Final combined result is **1,265 passed, 248 skipped, zero unresolved failures**.
  This was a targeted correction/rerun, not a second full portable run.
- The expectation now verifies the ordered Create click and quick Esc request: Create starts sound 25,
  and Esc is suppressed while that id remains active. The existing one-instance-per-id policy is
  preserved, not relaxed.
- **8d reduced**: the selection has 156 work items and exceeds the 40-item cap. From the repo root,
  source `~/Documents/MTM/mu-mac-tools/native/private-env.sh`, then run the new `test_audio_ui` module
  and the changed `test_audio_charsel` shell method. **9 tests, zero failures/skips, 31.98 s**. The
  unchanged charsel original validator's mutants were not rerun.
- `validate_audio_ui`: **5,803 cases, zero mismatches**, **18.6 s** without mutants. This comprises
  5,763 complete CButton updates and 40 credits sequences, including 3,000 credits frames, 66 button
  and 71 credits sound boundaries, and 952,836 credits state words. The original boundary independently
  supplies the sound site and arguments. The two body hashes are pinned in the validator.
- New-target mutants, run once: **10/10 caught**, **36.0 s** row wall, **36.14 s** command wall.
  Plants cover CButton site/enabled/release/held/order, credits site/gate, and cue id/object/loop.
- Native tests prove accepted release once despite held/repeated input, refused/hidden/disabled input,
  all four native charsel controls with an explicitly selected fixture, credits closure, detach/rebind,
  disabled delivery, Effect mute, callback cleanup and rejection of unlabelled/foreign requests.
  Five shell journeys retain equal audio-on/off PNG hashes. The existing installed sound 25 decodes
  to nonzero PCM through both recovered controller events, using read-only Native Data and no options writes.
- Affected validator runner: **26 passed, zero failures/errors/skips, 604.01 s** command wall including
  selection. All nine symbol fallback rows were retained. Only `validate_audio_ui` receives mutants;
  the other selected rows ran without their mutant switches.

Repository source/index audit: **2,144 files, zero rejected, 27.35 s**. A final staged
documentation audit runs before publication; its wall time is recorded in the PR.

### Steward validators

Tested commit **`385c4e0c`**. The final documentation commit does not change any compiled/validator input.
Use the canonical private environment above. All rows below passed without mutants. The new
`validate_audio_ui` row also passed its 10 mutants once at this same commit. Other rows need no mutants
for this lane. The scene row additionally runs its existing loading-screen checks.

Steward validators: validate_actor_recipes,validate_app_polish2,validate_app_polish4,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_audio_ui,validate_charsel_window,validate_hud,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_meshdraw,validate_model_edge,validate_movement,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_items,validate_scene,validate_ui,validate_ui_widgets,validate_world_order,validate_worlds_fog

| Validator | Cases | Wall seconds |
|---|---:|---:|
| `validate_actor_recipes` | 361 | 30.2 |
| `validate_app_polish2` | 1028 | 3.6 |
| `validate_app_polish4` | 10485 | 41.2 |
| `validate_audio_callers` | 5528 | 8.5 |
| `validate_audio_domains` | 2544 | 29.8 |
| `validate_audio_items` | 3000 | 4.0 |
| `validate_audio_ui` | 5803 | 18.6 |
| `validate_charsel_window` | 20 | 12.0 |
| `validate_hud` | 48 | 134.3 |
| `validate_icarus_c2` | 8400 | 39.3 |
| `validate_inventory_fx` | 8017 | 8.6 |
| `validate_item_callers` | 6013 | 1.5 |
| `validate_meshdraw` | 14619 | 80.3 |
| `validate_model_edge` | 954 | 167.3 |
| `validate_movement` | 6614 | 78.7 |
| `validate_render_effects16` | 424 | 4.6 |
| `validate_render_effects17` | 618 | 8.5 |
| `validate_render_effects18` | 540 | 1.5 |
| `validate_render_effects19` | 400 | 1.4 |
| `validate_render_effects24` | 226 | 2.7 |
| `validate_render_items` | 5512 | 2.6 |
| `validate_scene` | 225 routine cases | 1.4 |
| `validate_ui` | 794 | 212.9 |
| `validate_ui_widgets` | 630 | 105.7 |
| `validate_world_order` | 2400 | 9.3 |
| `validate_worlds_fog` | 4044 | 5.8 |

The 6b symbol review found the new sound payload/adapter in the two reconstructed UI callers,
`mu_charsel_ui`, shell delivery and the new native test host. Existing UI, shell and charsel audio
consumers are covered by the affected run and focused reruns. No shared session sound registration,
character renderer, actor, combat, item or world object routine changed. Standards/spec self-review
covered source provenance, callback lifetime, mute/no-replay, original gates/order and owned-path scope.
No independent review or full lane gate is claimed.


## Limits and next

Restore an actual offline login/credits owner before wiring its Esc/end sounds into the interactive
shell. Recover the GFx input-query caller and the legacy modal owners individually before adding
more sounds. A syntactic sound-id scan cannot establish those owners or their eligibility gates.
Original FMOD/native mixed-output parity and RNG phase remain unproved.

Local reports/build log are under `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002g/` and ignored
`verify-runs/` in this worktree. They are not future inputs. At PR-ready remove those outputs, builds,
worktree and local branch; retain the remote branch for the steward.
