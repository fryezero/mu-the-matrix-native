# SESSION-SOCIAL-001a

Party-only session migration, based on origin/main `3fd2daf`. No original client,
launcher, live service or dispatcher-table walk. [Finding](../research/client-social.md#session-social-001a).

## Implementation

- `session/domains/party*` owns the received party list, pending invitation key and
  invitation counter. Five finding-backed static seed rows bind 40/41/42/43/44.
  The unchanged reconstructed member parser supplies display percentages. Party
  handlers never write hero/remote-character stats or compute character power.
- List, clear and update validate the full frame before changing state. Empty
  lists/updates are valid. The native pending guard retains one key until answered,
  including unknown keys. Clear retains that key, as the original does. The guard
  against replacing an outstanding invitation is native UI policy.
- Invite, answer and leave intents call the original verified builders. Invite and
  answer preserve Send(1,0), journal their bytes as unsent and require NET-DECODE.
  Ordinary C1 opcode C3 is the leave/kick request, not an encrypted C3 envelope.
  It reaches only the explicitly supported dev plaintext loopback lane.
- `fixture/behaviors/party.c` owns synthetic membership, supplied bars, positions and
  demo timing. Explicit fixture commands supply invite/answer outcomes; this does
  not establish an encrypted round trip. The compatibility facade retains its own
  party session across world reloads, following the quest-facade pattern. The
  account lane still owns eventual login/selected-character lifetime.
- `mu_social` retains a read-only compatibility snapshot for existing HUD, nameplate
  and party-marker readers. In-view is a presentation projection. The real winParty
  adapter has its own cue cursor, independent of the facade's cursor. Rebinding
  refreshes current state and pending identity without replaying old notices.
  Marker ownership and all trade/mail/friend/room implementations remain outside
  this migration. World changes are a failure check and one final-close call.
- Allocations are confined to fixture/session/view opening and existing transport
  machinery. This lane adds no allocation in its party tick or GFx frame functions.

## Checks so far

- New production-adapter comparisons: **5,000 cases, zero mismatches, 5/5 compiled
  mutants caught**, 1,000 per family. List-envelope slice, full update name/count
  loop, clear receive, invitation receive and result receive. STL/string/GFx
  boundaries are modelled; the list's existing field/arithmetic slices remain
  covered by the unchanged social validator. No whole-container equivalence claim.
- Existing unchanged social families: **7,000 cases, zero mismatches, 10/10 compiled
  controls caught**. The unchanged round-2 run passes **29,700 cases, zero mismatches, 36/36 compiled controls caught**. Total instruction comparisons: **41,700**, zero mismatches; **51/51 compiled mutants/controls** detected.
- Four focused party tests pass with private input enabled. They cover every route,
  exact request bytes/encryption flags, malformed-frame atomicity, duplicate and
  unknown invitation identity, independent cursors, detached updates, reattachment,
  and unchanged hero stats. The fixture has six inbound frames, zero unbound or
  undecodable frames and two intentionally unsent requests.
- Existing three social regressions pass, including inventory/trade/messenger,
  stationary marker refresh, host rebinding and two-world membership retention.
  Input-router header regression was corrected; its 13 tests pass with one explicit
  private skip. Include audit and diff whitespace check pass. The registered validator passes with 200 cases and all five mutants, zero failures/errors/skips.
- Real ABI-3 Ruffle/native GL: 80 frames, three representative captures. Inspected
  winParty Hero/Aeris and Aeris's fixture-supplied 38/61 bars. Uses the existing
  manifest-bearing APP-REFRESH-001 Native Data and installed game assets. The old
  legacy Native Data path correctly refused its absent manifest. No owner data changed.
  No original-image fidelity score or new golden hash is claimed.
- Full release gate and final integration counts will be recorded before merge.

Temporary reports/renders are in the lane's external scratch/render directories.
They and build outputs will be deleted after merge; no new retained input is needed.
Only authored code, synthetic scenarios and reviewed summaries are committed.

## Remaining SESSION-SOCIAL-001

Trade, friends, messenger/mail session domains; inventory authority for trade;
complete friend/body route bindings; room-answer handler/ticket and text-key source;
chat-room connection/lifetime; account-owned session integration and live acceptance.
NET-DECODE remains required for party invite/answer sends. Static party route seeds
are not NET-DISPATCH verification. No crypto, decode or account/login code changed.
