# SESSION-SKILL-001

The skills domain owns the learned list, saved hotkeys, Master ranks and fourth-tree state in both
headless and GFx builds. The view submits select/save/cast/Master/fourth-tree intents. The former
skill demo now runs in `native/fixture/behaviors/skills.c` and `skills_model.c`; emitted C1/C2 frames
are the only skill-list/rank feed into the client session. Actors, players and skills share one fixture
session, with a standalone skills fixture when the other domains are disabled.

## Recovery and corrections

Resumed the existing branch after ENOSPC. Recovery checkpoint `53e9831` preserves the inherited
changes, then `ee26eb5` fixes queued-request flushing, verifies a genuinely detached world port, and
uses the same hero context for headless and GFx checks. A0 14 writes a sign-extended 32-bit value to
CharacterAttribute +0x34 through 0x00a00192. It is distinct from the progression counter at +0x30.
The inherited 16-bit write and +0x30 refresh were corrected and compared with the real instructions.
World unload clears view callbacks before the owning session closes; world load rebinds the replacement
book. Learned state survives view detachment and rebinding within the same session.

## Validation

The pre-integration full Mac gate passes: 1,473 tests, 180 expected private-input skips, fixture
suites, native viewer, read-only reader builds and publication audit. The final latest-main gate
is recorded below before merge.

- Historical base/server/Master reruns: 12,763 + 4,508 + 7,876 cases, zero mismatches;
  11/11 + 6/6 + 3/3 compiled mistakes caught. Fourth-tree rerun is recorded below.
- VERIFY-SESSION: 8/8 scenarios, 66 inbound frames, zero unbound/undecodable frames.
  Skills alone: 13 inbound frames covering nine bound routes, 11 expectations, three plaintext
  requests, zero unrecovered intents and one encrypted cast unsent. The other suites retain two
  unrecovered intents and five additional unsent frames.
- Real OpenGL/GFx synthetic-world drive: Skill Imprint opened, fixture learn/forget, Save handled,
  travel 0 to 1, replacement view rebound and another fixture learn accepted; 7 learned skills at
  completion. This checks runtime ownership; it is not a comparison against the live game.
  Representative first/final PNG SHA-256 values are recorded rather than claimed unchanged:
  `91abf6572f28ab23e0818b413579d60f0258d7139fe22a9383e65f80af7b38c0` and
  `d17874c6f54f4d1f98810ae16692d4900f073e6ebc84eb4af5aadef899c707bb`.
- New key serialization, plaintext save tail and Master-point write: 1,500 instruction comparisons,
  zero mismatches; all five compiled mistakes caught, including offset and sign extension.
- Seven focused session tests pass with the private instruction check enabled: learned-state lease
  violation detected, incomplete lists/keys preserve state, detached answers and book rebinding,
  fixture Master success, plaintext scenario and unsent encrypted cast, and headless skills.
- Original reconstructed skill sources remain unchanged. Pinned text SHA-256:
  `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
  image data: `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

## Limits and next work

This milestone uses only in-process loopback fixtures and plaintext C1/C2 frames. Encrypted casts are
journaled as unsent. Save comparison stops before keyed AddData; its 17-byte options suffix is passed
through, not reconstructed here. No dispatch generator, table walk, packet crypto, decode stage,
live game, stat editor or power features were used. Seed routing rows cite existing handler evidence.
7E 07 and fifth-tree bodies remain outside the existing verified scope. Equipment/buff/event context,
FormulaData and real server policy retain their earlier limits. Demo class tables still have process
lifetime until SESSION-GLOBALS-001. Session lifetime across world replacement belongs to SESSION-ACCOUNT;
this change preserves it across view detach/rebind, not across destruction of a fixture world session.

Local scratch, renders and build outputs will be deleted after merge. No new private inputs are retained.
