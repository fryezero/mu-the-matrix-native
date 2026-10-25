# Live service contract (NET-CONTRACT-001)

What the native client may do against the live Mu The Matrix service, as answered by the owner and the server
operator. Recorded here so every live milestone cites one place. No credentials appear in this file or anywhere in
the repository.

## Answers (2026-10-24 and 2026-10-25)

| Question | Answer | Source |
|---|---|---|
| End state | The native client logs in to the live service like the Windows client; demo servers become test fixtures | Owner, 2026-10-24 |
| What a login needs | The account and password only; no launcher or IGC material | Operator, via the owner, 2026-10-25 |
| Native client | Allowed | Operator, 2026-10-25 |
| Recording sessions | The owner's sessions may be recorded (packets and live memory reads of a client the owner started) | Operator, 2026-10-25 |
| Automated play | Allowed, as much as development needs | Operator, 2026-10-25 |
| Concurrency | One client (original or native) logged in at a time | Operator, 2026-10-25 |
| Native Data for other users | Each user runs a guided capture on their own client (DATA-ACQ-002) | Owner, 2026-10-25 |
| Signing and notarization | Deferred | Owner, 2026-10-25 |

## Consequences for the design

- The login uses `mu_proof_not_required()`. Login-body fields the original fills from launcher or IGC material
  are sent empty (NET-ACCOUNT-001 tags them). LIVE-LOGIN-001 records how the service treats them.
- The protection boundary does not move. The launcher handshake on `localhost:55232`, IGC.dll and RGS.dll stay
  opaque. Nothing they produce is analysed, forged, recorded or replayed.
- The live transport takes the client lock before it connects (NET-LINK-001):
  - product builds: a single-instance lock, and a refusal while an original client is running;
  - agents and live tests: the shared game lock (`GAME-LOCK.md` in mu-mac-tools) with its `MU_LOCK_ID` owner
    check.
- A side-by-side comparison is two runs, one after the other.
- Live runs use the owner's dev account through `scripts/live_session.py` (LIVE-HARNESS-001).
  - The account name comes from local settings.
  - The password stays in the Keychain item `mu-the-matrix-dev`, read only inside the client process.
  - The password is never printed, logged, journaled, committed or put in screenshots.

## Still to observe

The first recording (CAPTURE-KIT-001) answers these. None needs a person:

- **Connect server.** The endpoint is unconfirmed. A second-hand note gives `mtm2112.muthematrix.com:44205`; the
  game server is MTM-1, which is a PvP server.
- **Heartbeats.** Does IGC.dll add traffic after the login? If the service disconnects a client that does not send
  it, that becomes a new question for the operator. It is not something to imitate.
- **Version check.** Does the service check the client version, and how does it answer the pinned build?
