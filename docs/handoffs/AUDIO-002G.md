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

Verification in progress. Final counts, wall times, tested commit and Steward validators will replace
this paragraph before the ready line. No full gate is run in the lane.

## Limits and next

Restore an actual offline login/credits owner before wiring its Esc/end sounds into the interactive
shell. Recover the GFx input-query caller and the legacy modal owners individually before adding
more sounds. A syntactic sound-id scan cannot establish those owners or their eligibility gates.
Original FMOD/native mixed-output parity and RNG phase remain unproved.

Local reports/build log are under `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002g/` and ignored
`verify-runs/` in this worktree. They are not future inputs. At PR-ready remove those outputs, builds,
worktree and local branch; retain the remote branch for the steward.
